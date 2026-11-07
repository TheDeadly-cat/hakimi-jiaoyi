"""Reviewed test bootstrap: current source + read-only r7 runtime, never production."""
from hashlib import sha256
import importlib.abc
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from urllib.parse import unquote, urlparse


def bootstrap(spec_path, *, endpoint=None, case_root=None):
    started = time.monotonic()
    spec_path = Path(spec_path).resolve(strict=True)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    source, package, output = (Path(spec[key]).resolve(strict=True)
                               for key in ("source", "package", "output_root"))
    assert sys.flags.isolated and sys.flags.no_site and sys.flags.ignore_environment and sys.flags.dont_write_bytecode
    assert Path(sys.executable).resolve() == package / "runtime/python/python.exe"
    initial_path = list(sys.path)
    assert all(value and Path(value).is_absolute() and Path(value).is_relative_to(package) for value in initial_path)
    assert sha256(Path(__file__).read_bytes()).hexdigest() == spec["bootstrap_sha256"]
    manifest_path = package / "terminal-manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    assert sha256(manifest_bytes).hexdigest() == spec["manifest_sha256"]
    manifest = json.loads(manifest_bytes)
    assert manifest["source_provenance"]["git"] == {"commit": spec["package_source_commit"], "status": "CLEAN"}
    assert manifest["bundle_id"] == spec["package_bundle_id"]
    child = endpoint is not None
    if child:
        assert type(endpoint) is dict and endpoint["host"] == "127.0.0.1"
        assert type(endpoint["port"]) is int and endpoint["port"] != 11111 and 1 <= endpoint["port"] <= 65535
        allowed_endpoint = (endpoint["host"], endpoint["port"])
        roots = (Path(case_root).resolve(strict=True), Path.cwd().resolve(strict=True))
        assert all(path.is_relative_to(output) for path in roots)
    else:
        allowed_endpoint, roots = None, (output,)
    checked_source, checked_package = {}, {}
    counters = dict(socket_connect=0, socket_bind=0, dns_denied=0, external_endpoint_denied=0,
                    futu_import_denied=0, subprocess=0, database=0, writes=0)
    stages, registered_commands, launched_commands = [], {}, []
    stage_path = (Path.cwd() if child else output) / "bootstrap-phases.jsonl"

    def stage(label):
        value = dict(stage=label, seconds=time.monotonic() - started)
        stages.append(value)
        with stage_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(value) + "\n")

    def authorize_child_command(worker_spec, run_id, request_id, run_directory):
        assert not child
        assert worker_spec.interpreter == package / "runtime/python/python.exe"
        assert worker_spec.entrypoint.is_relative_to(output)
        assert sha256(worker_spec.entrypoint.read_bytes()).hexdigest() == worker_spec.entrypoint_sha256
        run_directory = Path(run_directory).resolve()
        assert run_directory.is_relative_to(output)
        command = [str(worker_spec.interpreter), "-I", "-S", "-B", "-u", "-X", "utf8",
                   str(worker_spec.entrypoint), "--run-id", run_id, "--request-id", request_id]
        # Windows' audit event exposes this exact command line string, not the
        # original argv list. No POSIX parsing or prefix allowance is used.
        key = subprocess.list2cmdline(command) if os.name == "nt" else tuple(command)
        assert key not in registered_commands
        expected_env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "SystemDrive") if key in os.environ}
        expected_env.update(PATH=str(worker_spec.interpreter.parent), TEMP=str(run_directory / "temp"),
            TMP=str(run_directory / "temp"), HOME=str(run_directory / "profile"), USERPROFILE=str(run_directory / "profile"),
            APPDATA=str(run_directory / "profile"), LOCALAPPDATA=str(run_directory / "profile"))
        registered_commands[key] = dict(command=command, entrypoint_sha256=worker_spec.entrypoint_sha256,
                                       cwd=str(run_directory), environment=expected_env)

    def inside(path, roots):
        return any(path == root or path.is_relative_to(root) for root in roots)

    def verify_file(path):
        path = Path(path).resolve()
        if not path.is_file():
            path = next((parent for parent in path.parents if parent.suffix == ".zip" and parent.is_file()), None)
            assert path is not None, "unverified module container"
        if path.is_relative_to(package):
            relative = path.relative_to(package).as_posix()
            expected = manifest["files"][relative]
            target = checked_package
        elif path.is_relative_to(source):
            relative = path.relative_to(source).as_posix()
            expected = spec["source_sha256"][relative]
            target = checked_source
        elif path.is_relative_to(output):
            # Owned wrapper bytes are separately bound by original TestWorkerSpec.
            return
        else:
            assert path == Path(__file__).resolve() or path == Path(spec["controller"]).resolve()
            expected = spec["bootstrap_sha256"] if path == Path(__file__).resolve() else spec["controller_sha256"]
            relative, target = str(path), checked_source
        actual = sha256(path.read_bytes()).hexdigest()
        assert actual == expected, "loaded source identity changed: " + str(path)
        target[relative] = actual

    class SourceLoader(importlib.machinery.SourceFileLoader):
        def get_code(self, fullname):
            verify_file(self.path)
            return compile(Path(self.path).read_bytes(), self.path, "exec", dont_inherit=True)

    class SourceFinder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname == "futu" or fullname.startswith("futu."):
                counters["futu_import_denied"] += 1
                raise AssertionError("SDK top-level import forbidden")
            found = importlib.machinery.PathFinder.find_spec(fullname, path)
            if found is None or found.origin in (None, "built-in", "frozen"):
                return found
            verify_file(found.origin)
            if str(found.origin).endswith(".py") and Path(found.origin).is_file():
                found.loader = SourceLoader(fullname, found.origin)
            return found

    def audit(event, args):
        if event in {"socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyaddr", "socket.getnameinfo"}:
            counters["dns_denied"] += 1
            raise AssertionError("No DNS in actual submit-market probe")
        if event == "socket.connect":
            address = args[1]
            if not child or address != allowed_endpoint:
                counters["external_endpoint_denied"] += 1
                raise AssertionError("Only this test's owned listener endpoint")
            counters["socket_connect"] += 1
        if event == "socket.bind":
            assert not child and args[1] == ("127.0.0.1", 0), "Only parent-owned dynamic listener"
            counters["socket_bind"] += 1
        if event == "subprocess.Popen":
            assert not child, "No child subprocess"
            command = args[1]
            key = command if type(command) is str else tuple(command)
            assert key in registered_commands, "Process command differs from the exact bound TestWorkerSpec"
            bound = registered_commands.pop(key)
            assert args[0] is None or Path(args[0]).resolve() == package / "runtime/python/python.exe"
            assert Path(args[2]).resolve() == Path(bound["cwd"])
            assert args[3] == bound["environment"], "Process environment differs from original supervisor contract"
            launched_commands.append({key: value for key, value in bound.items() if key != "environment"})
            launched_commands[-1]["environment_scope"] = "EXACT_ORIGINAL_SUPERVISOR_FRESH_DATA_AND_PRIVATE_PATH"
            counters["subprocess"] += 1
        if event == "sqlite3.connect":
            database = str(args[0])
            if database.startswith("file:"):
                database = unquote(urlparse(database).path)
                if len(database) > 3 and database[0] == "/" and database[2] == ":":
                    database = database[1:]
            assert inside(Path(database).resolve(), roots), "Database outside fresh test roots"
            counters["database"] += 1
        if event == "open" and len(args) >= 3 and isinstance(args[0], (str, bytes)):
            path = Path(os.fsdecode(args[0])).resolve()
            if args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                assert inside(path, roots), "Write outside fresh test roots: " + str(path)
                counters["writes"] += 1
            else:
                assert (path.is_relative_to(package) or path.is_relative_to(output) or
                    (path.is_relative_to(source) and path.relative_to(source).as_posix() in spec["source_sha256"]) or
                    path in (Path(__file__).resolve(), Path(spec["controller"]).resolve(), spec_path)), "Unapproved read: " + str(path)
        if event in {"os.remove", "os.rmdir", "os.mkdir"} and args and isinstance(args[0], (str, bytes)):
            assert inside(Path(os.fsdecode(args[0])).resolve(), roots), "Mutation outside fresh test roots"
        if event in {"os.rename", "os.replace"}:
            assert all(inside(Path(os.fsdecode(path)).resolve(), roots) for path in args[:2])

    sys.addaudithook(audit)
    stage("manifest_and_guards_ready")
    sys.meta_path.insert(0, SourceFinder())
    if child:
        def deny_thread(*args, **kwargs):
            raise AssertionError("No background thread in actual submit-market worker")
        threading.Thread.start = deny_thread
    sys.path[:0] = [str(source / "outputs/python_quant_bot"), str(source / "src"),
                    str(package / "runtime/python/Lib/site-packages")]
    from exchange_terminal.services import terminal_broker_execution_plan as plan
    from exchange_terminal.services import terminal_broker_package_loader as package_loader
    from exchange_terminal.adapters import futu_verified_protobuf_loader as loader
    # Reuse the real bounded package membership/hash contract. No package
    # bootstrap anchor or production worker admission is installed here.
    names = package_loader._related_files(package, manifest) | package_loader.CONTRACT_FILES
    observed = {}
    for name in sorted(names):
        raw = package_loader._read(package, name)
        observed[name] = sha256(raw).hexdigest()
        assert observed[name] == manifest["files"][name]
    runtime = plan.verify_runtime_identity(manifest_bytes=manifest_bytes,
        expected_manifest_sha256=spec["manifest_sha256"], observed_file_sha256=observed,
        mode="OFFICIAL_SIMULATION")
    stage("actual_package_identity_checked")
    # The real protobuf finder intentionally refuses unknown application/site
    # imports instead of falling through. Preload this finite declared test
    # closure under the hash-checking finder, with protobuf/SDK still cold.
    # Do not patch the real finder or add an import fallback after it is active.
    import tests.test_terminal_broker_submit_market_worker
    import exchange_terminal.services.terminal_broker_worker_entrypoint
    assert not any(name == "google" or name.startswith("google.") or name == "futu" or
                   name.startswith("futu.") or name.endswith("_pb2") for name in sys.modules)
    preloaded_application = sorted(name for name, module in sys.modules.items()
        if isinstance(getattr(module, "__file__", None), str) and
        Path(module.__file__).is_relative_to(source))
    stage("application_closure_preloaded_protobuf_cold")
    sys.path[:] = initial_path
    bindings = loader.load_verified_protobuf(package_root=package,
        expected_manifest_sha256=spec["manifest_sha256"], runtime_identity=runtime,
        profile_schema="hakimi-broker-wire-profile-v3")
    assert bindings.verify_current()["package"] == runtime.as_dict()["package"]
    stage("actual_verified_bindings_ready")
    sys.path[:0] = [str(source / "outputs/python_quant_bot"), str(source / "src"),
                    str(package / "runtime/python/Lib/site-packages")]

    def proof():
        metadata = bindings.verify_current()
        for module in tuple(sys.modules.values()):
            location = getattr(module, "__file__", None)
            if isinstance(location, str) and not location.startswith("<"):
                verify_file(location)
        assert not any(name == "futu" or name.startswith("futu.") for name in sys.modules)
        assert sha256(manifest_path.read_bytes()).hexdigest() == spec["manifest_sha256"]
        return dict(scope="R7_PRIVATE_RUNTIME_PLUS_HASHED_CURRENT_SOURCE_TEST_ASSEMBLY",
            production_package_bootstrap_acceptance=False, r7_contains_current_source=False,
            private_flags=dict(isolated=sys.flags.isolated, no_site=sys.flags.no_site,
                ignore_environment=sys.flags.ignore_environment, dont_write_bytecode=sys.flags.dont_write_bytecode),
            package_source_commit=spec["package_source_commit"], manifest_sha256=spec["manifest_sha256"],
            runtime_identity=runtime.as_dict(), protobuf_bindings=metadata,
            preloaded_application_modules=preloaded_application,
            loaded_current_source_sha256=dict(checked_source), loaded_package_sha256=dict(checked_package),
            guard_counters=dict(counters), allowed_endpoint=endpoint, source_authenticated=False,
            bootstrap_stages=list(stages), exact_test_commands_launched=list(launched_commands),
            synthetic_values=True, order_operations_allowed="SYNTHETIC_OWNED_PEER_ONLY",
            cash_snapshots_allowed="EXPLICIT_INDEPENDENT_SYNTHETIC_FIXTURE_ONLY")

    proof.authorize_child_command = authorize_child_command
    proof.stage = stage
    return runtime, bindings, proof
