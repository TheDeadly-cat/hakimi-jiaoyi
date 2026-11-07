"""Per-user, cross-workspace account stop control; never a dispatch permit.

The host supplies one fixed root at startup. A renderer cannot choose a root,
provider, domain or account; the service reads the selected saved configuration.
The Python trust boundary excludes arbitrary in-process code execution. No SDK,
credential, account query, order cancellation, worker or automatic recovery lives
here. Local candidate controls remain separate and must ALSO pass before IO.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import os
from pathlib import Path
import secrets
import sqlite3
import stat

from . import terminal_broker_execution_plan as contract

SCHEMA = "hakimi-broker-account-control-v1"
MAX_EVENTS, MAX_STORE_BYTES = 1000, 4 * 1024 * 1024
PERMISSIONS = dict(contract.PERMISSIONS)
_TOKEN = object()


class AccountControlError(ValueError):
    pass


def _require(value, reason):
    if not value:
        raise AccountControlError(reason)


def _safe(path):
    path = Path(path)
    _require(path.is_absolute() and ".." not in path.parts, "account_control_absolute_path_required")
    for item in (path, *path.parents):
        if os.path.lexists(item):
            info = item.lstat()
            _require(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
                     "account_control_reparse_path_rejected")
    return path.resolve()


@dataclass(frozen=True, init=False, slots=True)
class SharedBrokerRoot:
    path: Path
    domain: str
    root_id: str
    ancestor: Path
    ancestor_identity: tuple

    def __init__(self, values, token):
        _require(token is _TOKEN, "account_control_host_binding_required")
        for key, value in values.items():
            object.__setattr__(self, key, value)


def bind_host_root(path, *, program_root, record_domain):
    """Trusted startup/factory only. Resolves paths but creates no directories."""
    _require(record_domain in {"EXTERNAL_RECORD", "SYNTHETIC_TEST"}, "account_control_domain_required")
    root, program = _safe(path), _safe(program_root)
    _require(not root.is_relative_to(program) and root != program and
             (not root.exists() or root.is_dir()), "account_control_data_outside_program_required")
    ancestor = next(item for item in (root, *root.parents) if item.exists())
    info = ancestor.stat()
    _require(stat.S_ISDIR(info.st_mode), "account_control_directory_required")
    identity = sha256(("hakimi-broker-shared-root-v1\0" + os.path.normcase(str(root)) +
                       "\0" + record_domain).encode("utf-8")).hexdigest()
    return SharedBrokerRoot(dict(path=root, domain=record_domain, root_id=identity,
        ancestor=ancestor, ancestor_identity=(info.st_dev, info.st_ino)), _TOKEN)


def _anchor(root):
    _require(type(root) is SharedBrokerRoot, "account_control_typed_root_required")
    _require(_safe(root.path) == root.path, "account_control_root_changed")
    info = root.ancestor.stat()
    _require((info.st_dev, info.st_ino) == root.ancestor_identity, "account_control_ancestor_changed")
    return root.path


class AccountControl:
    """Journal/plan writer -> local control -> account barrier, always that order.

    stop() takes only this account's short transaction. Never hold the barrier
    while loading research, importing code, polling a process or awaiting IO.
    Future dispatch sessions must bind this revision and check it before EVERY
    connection/write, not merely when a plan was saved. Resume does not renew it.
    """
    def __init__(self, root, *, mode, account_id, clock=None):
        _anchor(root)
        _require(type(mode) is str and mode in contract.MODE_CONTRACTS and type(account_id) is str and account_id.isascii()
                 and account_id.isdecimal() and account_id[0] != "0" and 0 < int(account_id) < 2**64,
                 "account_control_explicit_scope_required")
        self.root, self.mode = root, mode
        self.account = {"provider": "FUTU", "mode": mode, "account_id": account_id}
        self.scope_id = contract.digest(self.account)
        self.path = root.path / "account-controls-v1" / root.domain / self.scope_id / "control.sqlite3"
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _meta(self):
        return {"schema_version": SCHEMA, "root_id": self.root.root_id, "record_domain": self.root.domain,
                "account": self.account, "account_scope_id": self.scope_id, "permissions": PERMISSIONS}

    def _check(self):
        _anchor(self.root)
        _safe(self.path)
        info = self.path.lstat()
        _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= MAX_STORE_BYTES,
                 "account_control_regular_bounded_store_required")
        for suffix in ("-wal", "-shm", "-journal"):
            _require(not os.path.lexists(str(self.path) + suffix), "account_control_pending_recovery_or_writer")
        with self.path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            _require((opened.st_dev, opened.st_ino) == (info.st_dev, info.st_ino), "account_control_file_replaced")
            header = stream.read(20)
        _require(header[:16] == b"SQLite format 3\x00" and header[18:20] == b"\x01\x01",
                 "account_control_delete_mode_required")

    def _create(self):
        _anchor(self.root); _safe(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        _anchor(self.root); _safe(self.path)
        temporary = self.path.with_name(".control-" + secrets.token_hex(8) + ".pending")
        connection = sqlite3.connect(str(temporary))
        try:
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("CREATE TABLE metadata(singleton INTEGER PRIMARY KEY CHECK(singleton=1), body BLOB NOT NULL, head INTEGER NOT NULL)")
            connection.execute("CREATE TABLE controls(revision INTEGER PRIMARY KEY, request_id TEXT UNIQUE NOT NULL, body BLOB NOT NULL)")
            connection.execute("INSERT INTO metadata VALUES(1,?,0)", (contract.canonical_bytes(self._meta()),))
            connection.commit()
        finally:
            connection.close()
        try:
            try:
                os.link(temporary, self.path)
            except FileExistsError:
                pass
        finally:
            temporary.unlink(missing_ok=True)

    @contextmanager
    def _database(self, write=False):
        _anchor(self.root); _safe(self.path)
        if not self.path.exists():
            if not write:
                yield None
                return
            self._create()
        self._check()
        connection = sqlite3.connect(str(self.path) if write else self.path.as_uri() + "?mode=ro",
                                     uri=not write, timeout=.25)
        try:
            connection.execute("PRAGMA trusted_schema=OFF")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield connection
            if write:
                connection.commit()
        finally:
            if connection.in_transaction:
                connection.rollback()
            connection.close()

    def _load(self, connection):
        if connection is None:
            return []
        metadata = connection.execute("SELECT singleton,body,head FROM metadata").fetchall()
        _require(len(metadata) == 1 and metadata[0][:2] == (1, contract.canonical_bytes(self._meta())),
                 "account_control_scope_or_root_changed")
        count, size = connection.execute("SELECT COUNT(*), COALESCE(SUM(LENGTH(body)),0) FROM controls").fetchone()
        _require(count <= MAX_EVENTS and size <= MAX_STORE_BYTES, "account_control_capacity_exceeded")
        records, previous = [], None
        for index, (revision, request_id, blob) in enumerate(connection.execute(
                "SELECT revision,request_id,body FROM controls ORDER BY revision"), 1):
            row = contract._json_document(blob, 8192)
            contract._fields(row, {"schema_version", "root_id", "record_domain", "account_scope_id", "revision",
                                   "previous_id", "request_id", "request_hash", "action", "payload", "at", "permissions", "id"})
            _require(contract.canonical_bytes(row) == blob and row.get("id") == contract.digest(
                {key: value for key, value in row.items() if key != "id"}), "account_control_record_changed")
            _require(row["schema_version"] == SCHEMA and row["account_scope_id"] == self.scope_id
                and row["record_domain"] == self.root.domain and row["root_id"] == self.root.root_id
                and type(row["revision"]) is int and revision == row["revision"] == index and request_id == row["request_id"]
                and row["previous_id"] == (previous["id"] if previous else None)
                and contract.canonical_bytes(row["permissions"]) == contract.canonical_bytes(PERMISSIONS),
                "account_control_chain_changed")
            _require(row["action"] in {"stop", "resume"} and row["request_hash"] == contract.digest(
                {"action": row["action"], "payload": row["payload"]}), "account_control_request_changed")
            self._payload(row["action"], row["payload"])
            _require(row["payload"]["request_id"] == request_id, "account_control_request_changed")
            if row["action"] == "resume":
                _require(previous is not None and previous["action"] == "stop"
                         and row["payload"]["expected_stop_receipt_id"] == previous["id"],
                         "account_control_resume_chain_changed")
            recorded_at = contract._time(row["at"])
            _require(previous is None or recorded_at >= contract._time(previous["at"]),
                     "account_control_clock_regressed")
            records.append(row); previous = row
        _require(metadata[0][2] == len(records), "account_control_head_changed")
        return records

    def _state(self, records):
        head = records[-1] if records else None
        return {"revision": len(records), "head_id": head["id"] if head else None,
                "stopped": bool(head and head["action"] == "stop"),
                "last_action": head["action"] if head else None,
                "dispatch_authorized": False, "automatic_resume": False}

    def _view(self, records, request_id=None, replayed=False):
        return {"schema_version": SCHEMA, "account": dict(self.account), "account_scope_id": self.scope_id,
                "record_domain": self.root.domain, "root_id": self.root.root_id, "service_available": True,
                "control": self._state(records),
                "receipt": next((row for row in records if row["request_id"] == request_id), None),
                "replayed": replayed, "broker_orders_cancelled": False, "permissions": dict(PERMISSIONS)}

    @staticmethod
    def _payload(action, payload):
        fields = {"request_id", "reason"} | ({"expected_stop_receipt_id"} if action == "resume" else set())
        contract._fields(payload, fields)
        _require(type(payload["request_id"]) is str and contract.candidate.REQUEST.fullmatch(payload["request_id"]),
                 "account_control_request_id_invalid")
        _require(type(payload["reason"]) is str and 1 <= len(payload["reason"].strip()) <= 200,
                 "account_control_reason_required")
        if action == "resume":
            contract._hash(payload["expected_stop_receipt_id"])

    def _change(self, action, payload):
        self._payload(action, payload)
        fingerprint = contract.digest({"action": action, "payload": payload})
        with self._database(write=True) as connection:
            records = self._load(connection)
            old = next((row for row in records if row["request_id"] == payload["request_id"]), None)
            if old is not None:
                _require(old["request_hash"] == fingerprint, "account_control_request_conflict")
                return self._view(records, payload["request_id"], replayed=True)
            _require(len(records) < MAX_EVENTS and (action != "resume" or len(records) + 1 < MAX_EVENTS),
                     "account_control_capacity_exceeded")
            head = records[-1] if records else None
            if action == "resume":
                _require(head is not None and head["action"] == "stop"
                         and payload["expected_stop_receipt_id"] == head["id"], "account_control_latest_stop_required")
            now = contract._now(self._clock())
            _require(head is None or now >= contract._time(head["at"]), "account_control_clock_regressed")
            row = {"schema_version": SCHEMA, "root_id": self.root.root_id, "record_domain": self.root.domain,
                "account_scope_id": self.scope_id, "revision": len(records) + 1,
                "previous_id": head["id"] if head else None, "request_id": payload["request_id"],
                "request_hash": fingerprint, "action": action, "payload": dict(payload),
                "at": now.isoformat(), "permissions": dict(PERMISSIONS)}
            row = {**row, "id": contract.digest(row)}
            blob = contract.canonical_bytes(row)
            _require(sum(len(contract.canonical_bytes(item)) for item in records) + len(blob) <= MAX_STORE_BYTES,
                     "account_control_capacity_exceeded")
            connection.execute("INSERT INTO controls VALUES(?,?,?)", (row["revision"], row["request_id"], blob))
            connection.execute("UPDATE metadata SET head=? WHERE singleton=1", (row["revision"],))
            result = self._view([*records, row], payload["request_id"])
        return result

    def stop(self, payload):
        return self._change("stop", payload)

    def resume(self, payload):
        return self._change("resume", payload)

    def read(self, request_id=None):
        if request_id is not None:
            _require(type(request_id) is str and contract.candidate.REQUEST.fullmatch(request_id),
                     "account_control_request_id_invalid")
        with self._database() as connection:
            return {**self._view(self._load(connection), request_id), "read_only": True}

    @contextmanager
    def barrier(self, expected_revision):
        _require(type(expected_revision) is int and 0 <= expected_revision <= MAX_EVENTS,
                 "account_control_revision_required")
        with self._database(write=True) as connection:
            current = self._state(self._load(connection))
            _require(not current["stopped"] and current["revision"] == expected_revision,
                     "account_control_changed_or_stopped")
            yield {"account_scope_id": self.scope_id, "control": current}
