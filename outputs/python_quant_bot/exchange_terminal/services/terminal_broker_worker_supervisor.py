"""Bounded parent-side supervision of one explicit, hash-bound worker process.

Only fresh synthetic test entrypoints can currently launch. Package identity
binding is available, but production admission intentionally has no factory.
This is not an OS sandbox, economic response verifier or dispatch authorization.
There are no SDK/socket imports, callbacks, retries or worker restarts.

The independent watchdog bounds the owned child's lifetime and pipe waits.
Filesystem identity reads, process creation and receipt storage are OS calls,
not untrusted callbacks we can forcibly interrupt. A timed-out finish returns
None; it must not be promoted to a completed receipt. Late process creation is
still killed by the launcher when its owned handle finally becomes available.
"""
from collections import deque
from dataclasses import dataclass
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
from threading import Condition, Event, Lock, Thread
import time

SCHEMA = "hakimi-broker-worker-message-v1"
PERMISSIONS = {name: False for name in (
    "external_connection_allowed", "query_allowed", "submit_allowed", "cancel_allowed",
    "unlock_allowed", "automatic_retry", "automatic_resume", "automatic_mode_fallback",
    "user_authorization_granted")}
_TOKEN = object()
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,119}\Z")
_HASH = re.compile(r"[a-f0-9]{64}\Z")


class SupervisorError(ValueError):
    pass


class ProductionAdmissionUnavailable(SupervisorError):
    pass


def _require(condition, code):
    if not condition:
        raise SupervisorError(code)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _plain_path(value, *, exists=True):
    path = Path(value)
    _require(path.is_absolute(), "absolute_path_required")
    _require(".." not in path.parts, "parent_path_escape")
    for item in reversed([path, *path.parents]):
        if not item.exists() and not item.is_symlink():
            continue
        info = item.lstat()
        _require(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
                 "reparse_path_refused")
    if exists:
        _require(path.exists(), "bound_path_missing")
    return path.resolve(strict=exists)


def _file_hash(path, maximum):
    path = _plain_path(path)
    before = path.stat()
    _require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and 0 < before.st_size <= maximum,
             "bound_file_invalid")
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    after = path.stat()
    _require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
             (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), "bound_file_changed_during_read")
    return digest.hexdigest()


@dataclass(frozen=True, slots=True, init=False)
class FreshOutputParent:
    path: Path
    identity: tuple

    def __init__(self, path, identity, token):
        _require(token is _TOKEN, "fresh_parent_factory_required")
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "identity", identity)


def create_output_parent(path):
    """Create exactly one new directory, with no recursion or existing adoption."""
    path = _plain_path(path, exists=False)
    _require(not path.exists(), "new_output_parent_required")
    path.mkdir()
    info = path.stat()
    return FreshOutputParent(path, (info.st_dev, info.st_ino), _TOKEN)


def _parent(anchor):
    _require(type(anchor) is FreshOutputParent, "typed_fresh_parent_required")
    path = _plain_path(anchor.path)
    info = path.stat()
    _require(path.is_dir() and (info.st_dev, info.st_ino) == anchor.identity, "output_parent_identity_changed")
    return path


@dataclass(frozen=True, slots=True)
class WorkerLimits:
    wall_seconds: float
    stop_seconds: float
    cleanup_seconds: float
    reply_seconds: float
    poll_seconds: float
    max_stdin_bytes: int
    max_stdout_bytes: int
    max_stderr_bytes: int
    max_evidence_bytes: int
    reserved_final_bytes: int
    max_stdin_messages: int
    max_stdout_messages: int
    max_stderr_records: int
    max_stdin_message_bytes: int
    max_stdout_message_bytes: int

    def __post_init__(self):
        for key, cap in (("wall_seconds", 180), ("stop_seconds", 1), ("cleanup_seconds", 5),
                         ("reply_seconds", 1), ("poll_seconds", 1)):
            value = getattr(self, key)
            _require(type(value) in (int, float) and math.isfinite(value) and 0 < value <= cap,
                     "time_limit_invalid:" + key)
        _require(self.cleanup_seconds >= self.stop_seconds, "cleanup_must_cover_stop_confirmation")
        for key, cap in (("max_stdin_bytes", 32768), ("max_stdout_bytes", 65536), ("max_stderr_bytes", 16384),
                         ("max_evidence_bytes", 131072), ("reserved_final_bytes", 32768),
                         ("max_stdin_messages", 50), ("max_stdout_messages", 50), ("max_stderr_records", 64),
                         ("max_stdin_message_bytes", 4096), ("max_stdout_message_bytes", 8192)):
            value = getattr(self, key)
            _require(type(value) is int and 0 < value <= cap, "byte_or_count_limit_invalid:" + key)
        _require(16384 <= self.reserved_final_bytes < self.max_evidence_bytes and
                 self.max_stdin_message_bytes <= self.max_stdin_bytes and
                 self.max_stdout_message_bytes <= self.max_stdout_bytes, "limits_inconsistent")


@dataclass(frozen=True, slots=True, init=False)
class TestWorkerSpec:
    interpreter: Path
    interpreter_sha256: str
    entrypoint: Path
    entrypoint_sha256: str
    fixture_parent: FreshOutputParent

    def __init__(self, interpreter, interpreter_sha256, entrypoint, entrypoint_sha256, fixture_parent, token):
        _require(token is _TOKEN, "test_spec_factory_required")
        for name, value in locals().copy().items():
            if name not in ("self", "token"):
                object.__setattr__(self, name, value)


def make_test_spec(*, interpreter, interpreter_sha256, entrypoint, entrypoint_sha256, fixture_parent):
    parent = _parent(fixture_parent)
    interpreter, entrypoint = _plain_path(interpreter), _plain_path(entrypoint)
    _require(entrypoint.is_relative_to(parent), "test_entrypoint_outside_fresh_fixture")
    _require(type(interpreter_sha256) is str and _HASH.fullmatch(interpreter_sha256) and
             type(entrypoint_sha256) is str and _HASH.fullmatch(entrypoint_sha256), "expected_hash_required")
    _require(_file_hash(interpreter, 64 * 1024 * 1024) == interpreter_sha256 and
             _file_hash(entrypoint, 256 * 1024) == entrypoint_sha256, "worker_identity_changed")
    return TestWorkerSpec(interpreter, interpreter_sha256, entrypoint, entrypoint_sha256, fixture_parent, _TOKEN)


@dataclass(frozen=True, slots=True, init=False)
class PackageWorkerSpec:
    package_root: Path
    manifest_sha256: str
    interpreter: Path
    entrypoint: Path
    interpreter_sha256: str
    entrypoint_sha256: str

    def __init__(self, values, token):
        _require(token is _TOKEN, "package_spec_factory_required")
        for name, value in values.items():
            object.__setattr__(self, name, value)


def bind_package_spec(*, package_root, manifest_sha256, interpreter_relative, entrypoint_relative):
    """Bind bytes only. Even a valid package spec cannot currently launch."""
    root = _plain_path(package_root)
    manifest_path = root / "terminal-manifest.json"
    _require(type(manifest_sha256) is str and _HASH.fullmatch(manifest_sha256), "expected_hash_required")
    _require(_file_hash(manifest_path, 8 * 1024 * 1024) == manifest_sha256, "package_manifest_changed")
    manifest = json.loads(manifest_path.read_bytes())
    paths = []
    for relative in (interpreter_relative, entrypoint_relative):
        _require(type(relative) is str and not Path(relative).is_absolute() and ".." not in Path(relative).parts,
                 "package_relative_path_required")
        path = _plain_path(root / relative)
        _require(path.is_relative_to(root), "package_path_escape")
        expected = manifest["files"].get(Path(relative).as_posix())
        _require(type(expected) is str and _HASH.fullmatch(expected), "package_entry_not_declared")
        _require(_file_hash(path, 64 * 1024 * 1024) == expected, "package_file_changed")
        paths.append((path, expected))
    return PackageWorkerSpec(dict(package_root=root, manifest_sha256=manifest_sha256,
        interpreter=paths[0][0], interpreter_sha256=paths[0][1], entrypoint=paths[1][0],
        entrypoint_sha256=paths[1][1]), _TOKEN)


def _unique_pairs(pairs):
    value = {}
    for key, item in pairs:
        _require(key not in value, "duplicate_json_key")
        value[key] = item
    return value


def _tree_bound(value, depth=0, count=None):
    count = [0] if count is None else count
    count[0] += 1
    _require(depth <= 8 and count[0] <= 1024, "json_structure_exceeded")
    if type(value) is dict:
        for key, item in value.items():
            _require(type(key) is str and len(key) <= 128, "json_key_invalid")
            _tree_bound(item, depth + 1, count)
    elif type(value) is list:
        for item in value:
            _tree_bound(item, depth + 1, count)
    elif type(value) is float:
        _require(math.isfinite(value), "json_nonfinite")
    else:
        _require(type(value) in (str, int, bool, type(None)), "json_value_invalid")


def _message(raw, run_id, request_id, sequence, kinds):
    value = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_unique_pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(SupervisorError("json_nonfinite")))
    _tree_bound(value)
    _require(type(value) is dict and set(value) == {"schema_version", "run_id", "request_id", "sequence", "kind", "payload"},
             "message_fields_invalid")
    _require(value["schema_version"] == SCHEMA and value["run_id"] == run_id and
             value["request_id"] == request_id, "message_identity_mismatch")
    _require(type(value["sequence"]) is int and value["sequence"] == sequence and value["kind"] in kinds and
             type(value["payload"]) is dict, "message_sequence_kind_or_payload_invalid")
    return value


def launch(spec, *, output_parent, run_dir, run_id, request_id, limits):
    if type(spec) is PackageWorkerSpec:
        raise ProductionAdmissionUnavailable("PRODUCTION_ADMISSION_UNAVAILABLE")
    _require(type(spec) is TestWorkerSpec and type(limits) is WorkerLimits, "typed_test_spec_and_limits_required")
    _require(type(run_id) is str and _IDENTIFIER.fullmatch(run_id) and
             type(request_id) is str and _IDENTIFIER.fullmatch(request_id), "worker_ids_invalid")
    parent = _parent(output_parent)
    run_dir = _plain_path(run_dir, exists=False)
    _require(run_dir.parent == parent and not run_dir.exists(), "fresh_direct_child_run_dir_required")
    _parent(spec.fixture_parent)
    _require(_file_hash(spec.interpreter, 64 * 1024 * 1024) == spec.interpreter_sha256 and
             _file_hash(spec.entrypoint, 256 * 1024) == spec.entrypoint_sha256, "worker_identity_changed")
    run_dir.mkdir()
    return WorkerHandle(spec, output_parent, run_dir, run_id, request_id, limits)


class WorkerHandle:
    def __init__(self, spec, output_parent, run_dir, run_id, request_id, limits):
        self.spec, self.output_parent, self.run_dir = spec, output_parent, run_dir
        self.run_id, self.request_id, self.limits = run_id, request_id, limits
        self._state = Condition(Lock())
        self._evidence_lock, self._reply_lock = Lock(), Lock()
        self._wake, self._finished = Event(), Event()
        self._started = time.monotonic()
        self._wall_deadline = self._started + limits.wall_seconds
        self._cleanup_deadline = self._stop_deadline = None
        self._process = None
        self._launcher_done = Event()
        self._readers_done = {name: Event() for name in ("stdout", "stderr")}
        self._writer_done = Event(); self._writer_done.set()
        self._messages = deque()
        self._counts = {"stdin": 0, "stdout": 0, "stderr": 0}
        self._seen = {"stdin": 0, "stdout": 0, "stderr": 0}
        self._retained = dict(self._seen)
        self._written = self._possible_written = 0
        self._reasons = []
        self._kill_attempted = self._ready = False
        self._result_reference = None
        self._result = None
        self._exit_code = None
        self._spawn_count = 0
        self._launch_attempted = False
        self._truncated = self._evidence_failed = False
        self._command = [str(spec.interpreter), "-I", "-S", "-B", "-u", "-X", "utf8", str(spec.entrypoint),
                         "--run-id", run_id, "--request-id", request_id]
        invocation = _json({"scope": "TEST_FIXTURE_ONLY", "production_admission": "UNAVAILABLE",
            "run_id": run_id, "request_id": request_id, "command": self._command,
            "interpreter_sha256": spec.interpreter_sha256, "entrypoint_sha256": spec.entrypoint_sha256,
            "limits": {key: getattr(limits, key) for key in limits.__dataclass_fields__},
            "permissions": PERMISSIONS, "shell": False, "windows_hidden": os.name == "nt"})
        _require(len(invocation) < limits.max_evidence_bytes - limits.reserved_final_bytes, "invocation_budget_exceeded")
        with (run_dir / "invocation.json").open("xb") as stream:
            stream.write(invocation)
        self._evidence_bytes = len(invocation)
        info = run_dir.stat()
        self._run_identity = (info.st_dev, info.st_ino)
        self._streams = {name: (run_dir / (name + ".bin")).open("xb", buffering=0) for name in self._seen}
        (run_dir / "temp").mkdir(); (run_dir / "profile").mkdir()
        self._threads = []
        self._thread(self._watchdog, "worker-deadline")
        self._thread(self._launch, "worker-launch")

    def _check_run(self):
        _parent(self.output_parent)
        path = _plain_path(self.run_dir)
        info = path.stat()
        _require(path.parent == self.output_parent.path and
                 (info.st_dev, info.st_ino) == self._run_identity, "run_directory_identity_changed")

    def _thread(self, target, name, *args):
        thread = Thread(target=target, args=args, name=name, daemon=True)
        self._threads.append(thread)
        thread.start()
        return thread

    def _abort(self, reason):
        with self._state:
            if reason not in self._reasons and len(self._reasons) < 8:
                self._reasons.append(reason)
            if self._cleanup_deadline is None:
                self._cleanup_deadline = time.monotonic() + self.limits.cleanup_seconds
            self._state.notify_all()
        self._wake.set()

    def _record(self, name, data):
        with self._evidence_lock:
            cap = getattr(self.limits, "max_" + name + "_bytes")
            self._seen[name] += len(data)
            room = min(cap - self._retained[name], self.limits.max_evidence_bytes -
                       self.limits.reserved_final_bytes - self._evidence_bytes)
            keep = data[:max(0, room)]
            if keep:
                self._streams[name].write(keep)
                self._retained[name] += len(keep)
                self._evidence_bytes += len(keep)
            if len(keep) != len(data):
                self._truncated = True
                raise SupervisorError(name + "_or_evidence_bytes_exceeded")

    def _launch(self):
        try:
            _parent(self.output_parent); _parent(self.spec.fixture_parent)
            self._check_run()
            _require(_file_hash(self.spec.entrypoint, 256 * 1024) == self.spec.entrypoint_sha256 and
                     _file_hash(self.spec.interpreter, 64 * 1024 * 1024) == self.spec.interpreter_sha256,
                     "worker_identity_changed")
            env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "SystemDrive") if key in os.environ}
            env.update(PATH=str(self.spec.interpreter.parent), TEMP=str(self.run_dir / "temp"), TMP=str(self.run_dir / "temp"),
                       HOME=str(self.run_dir / "profile"), USERPROFILE=str(self.run_dir / "profile"),
                       APPDATA=str(self.run_dir / "profile"), LOCALAPPDATA=str(self.run_dir / "profile"))
            with self._state:
                _require(not self._reasons and time.monotonic() < self._wall_deadline, "launch_already_stopped")
                self._launch_attempted = True
            process = subprocess.Popen(self._command, cwd=str(self.run_dir), env=env, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0, close_fds=True, shell=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0)
            with self._state:
                self._process = process
                self._spawn_count += 1
                late = self._result is not None
            if late:
                # Creation may finish after the launch deadline. A late handle
                # must never survive merely because no PID existed at timeout.
                process.kill()
                process.wait(timeout=self.limits.stop_seconds)
                for pipe in (process.stdin, process.stdout, process.stderr):
                    pipe.close()
                for event in self._readers_done.values():
                    event.set()
                return
            self._thread(self._read, "worker-stdout", "stdout", process.stdout)
            self._thread(self._read, "worker-stderr", "stderr", process.stderr)
        except Exception:
            self._abort("LAUNCH_OR_IDENTITY_FAILED")
        finally:
            self._launcher_done.set()
            self._wake.set()
            self._release_idle_handles()

    def _read(self, name, pipe):
        pending = bytearray()
        consumed = 0
        try:
            while True:
                data = os.read(pipe.fileno(), 4096)
                if not data:
                    if name == "stdout" and pending:
                        raise SupervisorError("partial_json_at_eof")
                    break
                self._record(name, data)
                if name == "stderr":
                    with self._state:
                        self._counts[name] += 1
                        _require(self._counts[name] <= self.limits.max_stderr_records, "stderr_records_exceeded")
                    continue
                pending.extend(data)
                while b"\n" in pending:
                    line, _, remainder = pending.partition(b"\n")
                    pending = bytearray(remainder)
                    _require(0 < len(line) + 1 <= self.limits.max_stdout_message_bytes, "stdout_message_bytes_exceeded")
                    with self._state:
                        _require(self._counts["stdout"] < self.limits.max_stdout_messages, "stdout_messages_exceeded")
                        value = _message(bytes(line), self.run_id, self.request_id, self._counts["stdout"] + 1,
                                         {"READY", "EVIDENCE", "RESULT"})
                        _require(self._result_reference is None, "message_after_result")
                        _require((not self._ready and value["kind"] == "READY") or
                                 (self._ready and value["kind"] != "READY"), "ready_sequence_invalid")
                        self._ready = True
                        self._counts["stdout"] += 1
                        if value["kind"] == "RESULT":
                            self._result_reference = {"file": "stdout.bin", "offset": consumed,
                                "bytes": len(line) + 1, "sha256": sha256(bytes(line) + b"\n").hexdigest(),
                                "sequence": value["sequence"]}
                        self._messages.append(value)
                        self._state.notify_all()
                    consumed += len(line) + 1
                _require(len(pending) < self.limits.max_stdout_message_bytes, "stdout_message_bytes_exceeded")
        except Exception as error:
            if not isinstance(error, SupervisorError):
                self._evidence_failed = True
            self._abort(str(error) if isinstance(error, SupervisorError) else "PIPE_OR_EVIDENCE_FAILED")
        finally:
            try:
                pipe.close()
            except Exception:
                pass
            self._readers_done[name].set()
            self._wake.set()
            self._release_idle_handles()

    def _release_idle_handles(self):
        """Release only settled resources; never repair a historical UNKNOWN.

        A writer may unblock after the cleanup receipt was frozen. Closing its
        now idle pipe is resource release, not another worker/kill/input attempt.
        """
        if (self._result is None or not self._launcher_done.is_set() or not self._writer_done.is_set() or
                not all(event.is_set() for event in self._readers_done.values()) or self._reply_lock.locked()):
            return
        try:
            if self._process is not None and self._process.poll() is None:
                return
            if not self._evidence_lock.acquire(blocking=False):
                return
            try:
                for stream in self._streams.values():
                    stream.close()
                if self._process is not None and self._process.stdin:
                    self._process.stdin.close()
            finally:
                self._evidence_lock.release()
        except Exception:
            # The prior cleanup result is immutable and remains unconfirmed.
            pass

    def stop(self):
        """Direct, short control path; no protocol queue or pipe lock is held."""
        with self._state:
            if self._result is not None:
                return
            if self._stop_deadline is None:
                self._stop_deadline = time.monotonic() + self.limits.stop_seconds
        self._abort("STOP_REQUESTED")

    def _watchdog(self):
        while True:
            now = time.monotonic()
            with self._state:
                process, reasons = self._process, bool(self._reasons)
            if now >= self._wall_deadline and not reasons:
                self._abort("WALL_DEADLINE")
                reasons = True
            if process is not None:
                if reasons and not self._kill_attempted:
                    self._kill_attempted = True
                    try:
                        process.kill()
                    except Exception:
                        self._abort("KILL_UNCONFIRMED")
                try:
                    code = process.poll()
                except Exception:
                    code = None
                    self._abort("PROCESS_STATUS_UNCONFIRMED")
                if code is not None:
                    self._exit_code = code
                    if self._cleanup_deadline is None:
                        self._cleanup_deadline = now + self.limits.cleanup_seconds
                if self._stop_deadline is not None and now >= self._stop_deadline and code is None:
                    self._abort("STOP_CONFIRMATION_TIMEOUT")
            readers_done = all(event.is_set() for event in self._readers_done.values())
            if self._launcher_done.is_set() and process is None:
                self._finalize(cleanup_confirmed=True)
                return
            if self._launcher_done.is_set() and self._exit_code is not None and readers_done and self._writer_done.is_set():
                self._finalize(cleanup_confirmed=True)
                return
            if self._cleanup_deadline is not None and now >= self._cleanup_deadline:
                self._abort("CLEANUP_TIMEOUT")
                self._finalize(cleanup_confirmed=False)
                return
            next_limit = min(self._wall_deadline, self._cleanup_deadline or math.inf,
                             self._stop_deadline or math.inf)
            self._wake.wait(max(0.001, min(0.02, next_limit - time.monotonic())))
            self._wake.clear()

    def poll_message(self, timeout):
        _require(type(timeout) in (int, float) and math.isfinite(timeout) and 0 <= timeout <= self.limits.poll_seconds,
                 "poll_timeout_invalid")
        deadline = time.monotonic() + timeout
        with self._state:
            while not self._messages and self._result is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self._state.wait(remaining)
            return self._messages.popleft() if self._messages else None

    def reply(self, message):
        raw = _json(message) + b"\n"
        _require(len(raw) <= self.limits.max_stdin_message_bytes, "stdin_message_bytes_exceeded")
        _require(self._reply_lock.acquire(blocking=False), "reply_busy_no_queue")
        completed = Event()
        receipt = {}
        try:
            with self._state:
                _require(self._ready and not self._reasons and self._result_reference is None and self._result is None,
                         "worker_not_accepting_input")
                _message(raw[:-1], self.run_id, self.request_id, self._counts["stdin"] + 1, {"INPUT", "STOP"})
                _require(self._counts["stdin"] < self.limits.max_stdin_messages, "stdin_messages_exceeded")
                self._counts["stdin"] += 1
            self._record("stdin", raw)  # Offered bytes are retained before writing; not claimed sent.
            self._writer_done.clear()
            deadline = min(self._wall_deadline, time.monotonic() + self.limits.reply_seconds)

            def write():
                offset = 0
                try:
                    while offset < len(raw):
                        with self._state:
                            _require(not self._reasons and time.monotonic() < deadline, "stdin_write_stopped")
                            self._possible_written += len(raw) - offset
                        amount = os.write(self._process.stdin.fileno(), raw[offset:])
                        _require(type(amount) is int and 0 < amount <= len(raw) - offset, "stdin_write_contract_invalid")
                        with self._state:
                            self._written += amount
                            self._possible_written -= len(raw) - offset - amount
                        offset += amount
                    receipt.update(status="STDIN_WRITTEN_NOT_DISPATCH_ACK", bytes_written=offset)
                except Exception:
                    self._abort("STDIN_WRITE_UNKNOWN")
                    receipt.update(status="UNKNOWN", bytes_written=offset)
                finally:
                    self._writer_done.set()
                    completed.set()
                    self._wake.set()
                    self._release_idle_handles()

            self._thread(write, "worker-stdin")
            if not completed.wait(max(0, deadline - time.monotonic())):
                self._abort("STDIN_WRITE_TIMEOUT")
                return {"status": "UNKNOWN", "request_id": self.request_id, "automatic_retry": False}
            return {**receipt, "request_id": self.request_id, "automatic_retry": False}
        except Exception:
            self._abort("STDIN_REPLY_REFUSED_OR_UNKNOWN")
            raise
        finally:
            self._reply_lock.release()
            self._release_idle_handles()

    def _finalize(self, *, cleanup_confirmed):
        try:
            _require(_file_hash(self.spec.entrypoint, 256 * 1024) == self.spec.entrypoint_sha256,
                     "entrypoint_changed_during_run")
        except Exception:
            self._abort("ENTRYPOINT_IDENTITY_UNCONFIRMED")
        with self._state:
            if self._result is not None:
                return
            if self._exit_code is None:
                self._reasons.append("EXIT_UNCONFIRMED")
            elif self._exit_code != 0 and "EXIT_NOT_ZERO" not in self._reasons:
                self._reasons.append("EXIT_NOT_ZERO")
            if self._result_reference is None:
                self._reasons.append("RESULT_MISSING")
            result = {"status": "UNKNOWN" if self._reasons else "PROTOCOL_RESULT_RECEIVED",
                "scope": "TEST_FIXTURE_ONLY", "production_admission": "UNAVAILABLE",
                "run_id": self.run_id, "request_id": self.request_id,
                "possible_dispatch_request_ids": [self.request_id] if self._launch_attempted else [],
                "possible_dispatch_is_not_proof_of_dispatch": True, "result_reference": self._result_reference,
                "exit_code": self._exit_code, "reasons": list(self._reasons), "spawn_count": self._spawn_count,
                "launch_attempted": self._launch_attempted, "launch_outcome_unconfirmed": not self._launcher_done.is_set(),
                "spawn_count_is_observed_at_receipt": True,
                "worker_pid": self._process.pid if self._process is not None else None,
                "restart_count": 0, "automatic_retry": False, "economic_acceptance": "NOT_INFERRED",
                "cleanup_confirmed": cleanup_confirmed, "messages": dict(self._counts),
                "bytes_seen": dict(self._seen), "bytes_retained": dict(self._retained),
                "stdin_bytes_written": self._written, "stdin_possible_bytes_written": self._possible_written,
                "streams_complete": cleanup_confirmed and not self._reasons and not self._truncated and not self._evidence_failed,
                "truncated": self._truncated, "evidence_complete": cleanup_confirmed and not self._truncated and not self._evidence_failed,
                "permissions": dict(PERMISSIONS), "elapsed_seconds": time.monotonic() - self._started}
            # The process decision is now sealed. stop() cannot race a finished
            # process into an already serialized success receipt. The separate
            # finished event still waits for the bounded-size receipt IO.
            self._result = result
            self._state.notify_all()
        # No reader or stdin lock is needed to decide UNKNOWN or kill the child.
        # Parent-owned receipt storage is bounded independently of pipe output.
        raw = _json(result)
        _require(len(raw) <= self.limits.reserved_final_bytes, "final_receipt_exceeded")
        try:
            self._check_run()
            with (self.run_dir / "result.json").open("xb") as stream:
                stream.write(raw)
            if cleanup_confirmed:
                for stream in self._streams.values():
                    stream.close()
                if self._process is not None and self._process.stdin:
                    self._process.stdin.close()
        except Exception:
            result.update(status="UNKNOWN", evidence_complete=False)
        with self._state:
            self._result = result
            self._state.notify_all()
        self._finished.set()

    def finish(self, timeout):
        """Return a persisted-result attempt, or None while finalization waits.

        None is not success, clean exit or proof that an original action was
        absent. The coordinator must retain its original request as unresolved.
        """
        _require(type(timeout) in (int, float) and math.isfinite(timeout) and
                 0 <= timeout <= self.limits.wall_seconds + self.limits.cleanup_seconds, "finish_timeout_invalid")
        if not self._finished.wait(timeout):
            return None
        with self._state:
            return json.loads(_json(self._result))

    def close(self):
        if not self._finished.is_set():
            self.stop()
        result = self.finish(self.limits.cleanup_seconds + min(self.limits.stop_seconds, self.limits.wall_seconds))
        self._release_idle_handles()
        return result
