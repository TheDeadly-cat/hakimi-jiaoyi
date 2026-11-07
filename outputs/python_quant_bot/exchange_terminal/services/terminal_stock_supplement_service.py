"""Retained-byte supplement reviews, explicit saves, and read-only receipts.

No provider, SDK, task or runner is called here. A pending save is never retried:
the canonical write and this store's receipt are separate durable operations.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import date, datetime, timezone
from hashlib import sha256
import base64
import os
from pathlib import Path
import re
import secrets
import sqlite3
import stat

from hakimi_research.documents import canonical_bytes, digest, parse_document
from .terminal_workspace_history import _no_links, _safe


SCHEMA = "terminal-stock-supplement-view-v2"
STORE_SCHEMA = "terminal-stock-supplement-store-v2"
PREFIX = "terminal_daily_"
FORMAT = "futu-retained-sdk-v1"
KEYS = ("security_request", "security_response", "actions_request", "actions_response")
ORIGINALS = ("check.json", "request-started.json", "source-original.bin", "calendar.json")
FILE_BYTES, TOTAL_BYTES = 1048576, 4194304
MAX_ORIGINAL_BYTES, MAX_BLOB, MAX_STORE = 32 * 1048576, 64 * 1048576, 160 * 1048576
MAX_RECORDS = 128
PERMISSIONS = dict(research_only=True, order_allowed=False, live_allowed=False, paper_allowed=False)
OP = re.compile(r"[A-Za-z0-9_-]{8,80}\Z")
SID = re.compile(r"supplement-[a-f0-9]{64}\Z")
HASH = re.compile(r"[a-f0-9]{64}\Z")
TABLES = {
    "metadata": "CREATE TABLE metadata(singleton INTEGER PRIMARY KEY CHECK(singleton=1), body BLOB NOT NULL)",
    "reviews": "CREATE TABLE reviews(id TEXT PRIMARY KEY, body BLOB NOT NULL)",
    "requests": "CREATE TABLE requests(id TEXT PRIMARY KEY, body BLOB NOT NULL)",
    "claims": "CREATE TABLE claims(review_id TEXT PRIMARY KEY, operation_id TEXT UNIQUE NOT NULL, input_id TEXT NOT NULL)",
}


def _require(value, reason):
    if not value:
        raise ValueError("supplement_" + reason)


def _fields(value, fields):
    _require(type(value) is dict and set(value) == set(fields), "exact_fields_required")


def _seal(value):
    return dict(value, record_hash=digest(value))


def _document(blob):
    _require(type(blob) is bytes and len(blob) <= MAX_BLOB, "bounded_record_required")
    value = parse_document(blob)
    _require(canonical_bytes(value) == blob and value.get("record_hash") == digest(
        {k: v for k, v in value.items() if k != "record_hash"}), "record_changed")
    return value


def _public(value):
    """Retain hashes and sizes, never return the embedded originals over GET."""
    if type(value) is list:
        return [_public(item) for item in value]
    if type(value) is dict:
        result = {key: _public(item) for key, item in value.items() if key != "raw_base64"}
        if "raw_base64" in value:
            result["bytes"] = len(base64.b64decode(value["raw_base64"], validate=True))
        return result
    return value


class TerminalStockSupplementService:
    def __init__(self, daily):
        self.daily, self.workspace = daily, daily.workspace
        self.root = _safe(self.workspace, self.workspace / "daily-supplements-v2")
        self.path = self.root / "store.sqlite3"
        self.ancestor = next(p for p in (self.workspace, *self.workspace.parents) if p.exists())
        info = self.ancestor.stat()
        self.anchor_identity = (info.st_dev, info.st_ino)

    def _anchor(self):
        _no_links(self.workspace)
        _safe(self.workspace, self.path)
        info = self.ancestor.stat()
        _require((info.st_dev, info.st_ino) == self.anchor_identity, "workspace_replaced")

    def _meta(self):
        return canonical_bytes(dict(schema_version=STORE_SCHEMA,
            workspace=os.path.normcase(str(self.workspace)), daily_root=os.path.normcase(str(self.daily.root))))

    def _check_file(self):
        self._anchor()
        info = self.path.lstat()
        _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= MAX_STORE,
                 "regular_bounded_store_required")
        for suffix in ("-wal", "-shm", "-journal"):
            _require(not os.path.lexists(str(self.path) + suffix), "pending_recovery_or_writer")
        with self.path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            _require((opened.st_dev, opened.st_ino) == (info.st_dev, info.st_ino), "store_replaced")
            header = stream.read(20)
        _require(header[:16] == b"SQLite format 3\0" and header[18:20] == b"\1\1", "delete_mode_required")

    def _create(self):
        self._anchor()
        self.root.mkdir(parents=True, exist_ok=True)
        self._anchor()
        temporary = self.root / (".store-" + secrets.token_hex(12) + ".pending")
        connection = sqlite3.connect(str(temporary))
        try:
            connection.execute("PRAGMA synchronous=FULL")
            for sql in TABLES.values():
                connection.execute(sql)
            connection.execute("INSERT INTO metadata VALUES(1,?)", (self._meta(),))
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

    @staticmethod
    def _commit(connection):
        connection.commit()

    @contextmanager
    def _database(self, write=False):
        self._anchor()
        if not self.path.exists():
            if not write:
                yield None
                return
            self._create()
        self._check_file()
        connection = sqlite3.connect(self.path.as_uri() + ("?mode=rw" if write else "?mode=ro"), uri=True, timeout=1)
        try:
            connection.execute("PRAGMA trusted_schema=OFF")
            if write:
                connection.execute("PRAGMA synchronous=FULL")
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            schema = dict(connection.execute("SELECT name,sql FROM sqlite_master WHERE type='table'"))
            _require(schema == TABLES and not connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type IN ('trigger','view')").fetchone(), "foreign_schema")
            _require(connection.execute("SELECT singleton,body FROM metadata").fetchall() == [(1, self._meta())],
                     "workspace_or_schema_changed")
            self._capacity(connection)
            yield connection
            if write:
                self._capacity(connection)
                self._commit(connection)
        finally:
            if connection.in_transaction:
                connection.rollback()
            connection.close()

    @staticmethod
    def _capacity(connection):
        size = 0
        for table in ("reviews", "requests"):
            count, amount = connection.execute(f"SELECT COUNT(*),COALESCE(SUM(LENGTH(body)),0) FROM {table}").fetchone()
            _require(count <= MAX_RECORDS, "record_capacity_exceeded")
            size += amount
        _require(size <= MAX_STORE // 2, "byte_capacity_exceeded")

    def _original(self, identity, expected=None):
        directory = self.daily._lookup("intakes", identity)
        artifacts = {}
        for name in ORIGINALS:
            path = self.daily._path(directory / name)
            info = path.lstat()
            _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and 0 < info.st_size <= MAX_ORIGINAL_BYTES,
                     "original_regular_bounded_file_required")
            artifacts[name] = path.read_bytes()
        _require(sum(map(len, artifacts.values())) <= MAX_ORIGINAL_BYTES, "original_bytes_limit")
        checked = parse_document(artifacts["check.json"])
        _require(checked.get("schema_version") == "workbench-stock-intake-v1"
            and checked.get("check_hash") == digest({k: v for k, v in checked.items() if k != "check_hash"})
            and checked.get("intake_id") == directory.name and checked.get("status") == "BLOCKED"
            and checked.get("can_save") is False and checked.get("reason") == "SOURCE_CORPORATE_ACTION_COVERAGE_UNKNOWN"
            and checked.get("source_truth_verified") is False, "original_blocked_check_required")
        _fields(checked.get("artifacts"), ORIGINALS[1:])
        for name, expected_hash in checked["artifacts"].items():
            _require(sha256(artifacts[name]).hexdigest() == expected_hash, "original_artifact_changed")
        _require(expected is None or expected == checked["check_hash"], "original_check_changed")
        for key in ("coverage_start", "coverage_end"):
            _require(date.fromisoformat(checked[key]).isoformat() == checked[key], "original_window_invalid")
        return artifacts, checked

    @staticmethod
    def _context(identity, checked):
        return dict(schema_version=SCHEMA, original_intake_id=identity, original_check_hash=checked["check_hash"],
            security=deepcopy(checked["security"]), window=dict(start=checked["coverage_start"], end=checked["coverage_end"]),
            permissions=dict(PERMISSIONS), source_truth_verified=False, read_only=True)

    def context(self, identity):
        _, checked = self._original(identity)
        titles = ("证券查询请求", "证券查询响应", "公司行为查询请求", "公司行为查询响应")
        filenames = ("01-security.started.private.json", "01-security.response.private.json",
                     "02-actions.started.private.json", "02-actions.response.private.json")
        return dict(self._context(identity, checked), supported_formats=[dict(id=FORMAT,
            title="本机已保存的富途 SDK 查询原件", required_artifacts=[dict(key=k, title=t, filename=f)
                for k, t, f in zip(KEYS, titles, filenames)])], limits=dict(file_bytes=FILE_BYTES, total_bytes=TOTAL_BYTES))

    @staticmethod
    def _payload(action, payload):
        fields = {"operation_id", "intake_id", "expected_check_hash", "source_format", "artifacts"} if action == "check_supplement" else {
            "operation_id", "supplement_id", "expected_check_hash", "confirmed_security", "acknowledge_source_limits"}
        _fields(payload, fields)
        _require(type(payload["operation_id"]) is str and OP.fullmatch(payload["operation_id"]), "operation_id_invalid")
        _require(type(payload["expected_check_hash"]) is str and HASH.fullmatch(payload["expected_check_hash"]), "check_hash_invalid")
        if action == "check_supplement":
            _require(payload["source_format"] == FORMAT, "source_format_not_supported")
            _fields(payload["artifacts"], KEYS)
            total = 0
            for raw in payload["artifacts"].values():
                _require(type(raw) is str and 0 < len(raw) <= ((FILE_BYTES + 2) // 3) * 4, "artifact_size_invalid")
                decoded = base64.b64decode(raw, validate=True)
                _require(0 < len(decoded) <= FILE_BYTES and base64.b64encode(decoded).decode("ascii") == raw,
                         "canonical_base64_required")
                total += len(decoded)
            _require(total <= TOTAL_BYTES, "artifacts_total_limit")
        else:
            _require(type(payload["supplement_id"]) is str and SID.fullmatch(payload["supplement_id"]), "review_id_invalid")
            _require(type(payload["confirmed_security"]) is dict and payload["acknowledge_source_limits"] is True,
                     "explicit_security_and_source_limits_required")

    def _request(self, connection, identity, fingerprint=None):
        row = connection.execute("SELECT body FROM requests WHERE id=?", (identity,)).fetchone() if connection else None
        if row is None:
            return None
        record = _document(row[0])
        _require(record["operation_id"] == identity and record["action"] in {PREFIX + "check_supplement", PREFIX + "save_supplement"}
            and record["request_hash"] == digest(dict(action=record["action"], payload=record["payload"]))
            and record["status"] in {"PENDING", "COMPLETED"}
            and ((record["result"] is None) == (record["status"] == "PENDING")), "request_record_changed")
        _require(fingerprint is None or fingerprint == record["request_hash"], "operation_payload_conflict")
        return record

    def _review(self, connection, identity):
        _require(type(identity) is str and SID.fullmatch(identity), "review_id_invalid")
        row = connection.execute("SELECT body FROM reviews WHERE id=?", (identity,)).fetchone() if connection else None
        _require(row is not None, "review_not_found")
        record = _document(row[0])
        core = {k: v for k, v in record.items() if k not in {"id", "record_hash"}}
        checked = record["review"]
        _require(record["id"] == identity == "supplement-" + digest(core)
            and checked["check_hash"] == digest({k: v for k, v in checked.items() if k != "check_hash"}), "review_identity_changed")
        return record

    def _view(self, connection, record):
        checked = record["review"]
        binding = checked["binding"]
        context = dict(schema_version=SCHEMA, original_intake_id=record["original_intake_id"],
            original_check_hash=binding["original_check_hash"], security=deepcopy(binding["security"]),
            window=dict(start=binding["coverage_start"], end=binding["coverage_end"]),
            permissions=dict(PERMISSIONS), source_truth_verified=False, read_only=True)
        result = dict(context, id=record["id"], status=checked["status"], can_save=checked["can_save"],
            check_hash=checked["check_hash"], reason=checked["reason"], times=deepcopy(checked["times"]),
            saved_input_id=None, saved_input=None, diagnostic=dict(summary="固定区间补证检查已保存；来源完整性和截至时点仍未知。",
                action="核对证券及来源限制后明确另存新输入。" if checked["can_save"] else "请查看原件诊断；不能保存此补证输入。",
                details=_public(checked)))
        claim = connection.execute("SELECT operation_id FROM claims WHERE review_id=?", (record["id"],)).fetchone() if connection else None
        if claim:
            request = self._request(connection, claim[0])
            _require(request is not None, "save_claim_request_missing")
            if request["status"] == "COMPLETED":
                return deepcopy(request["result"])
            result.update(status="UNKNOWN", can_save=False, reason="SAVE_PENDING_QUERY_ORIGINAL_REQUEST_ONLY")
            result["diagnostic"]["action"] = "只查询原保存请求回执；不重复另存，也不自动补写。"
        return result

    def read(self, kind, identity=None):
        if kind == "supplement_context":
            return self.context(identity)
        if kind == "supplement_requests":
            _require(type(identity) is str and OP.fullmatch(identity), "operation_id_invalid")
            with self._database() as connection:
                record = self._request(connection, identity)
                return dict(operation_id=identity, status=record["status"] if record else "NOT_RECORDED",
                    action=record["action"] if record else None, request_hash=record["request_hash"] if record else None,
                    result=deepcopy(record["result"]) if record else None, read_only=True)
        _require(kind == "supplements", "unknown_resource")
        with self._database() as connection:
            if identity is not None:
                return self._view(connection, self._review(connection, identity))
            ids = [row[0] for row in connection.execute("SELECT id FROM reviews ORDER BY id")] if connection else []
            return dict(items=[self._view(connection, self._review(connection, key)) for key in ids], read_only=True)

    def input_lineage(self, identity):
        with self._database() as connection:
            rows = connection.execute("SELECT operation_id FROM claims WHERE input_id=?", (identity,)).fetchall() if connection else []
            for row in rows:
                request = self._request(connection, row[0])
                if request and request["status"] == "COMPLETED":
                    return deepcopy(request["result"]["saved_input"]["supplement_lineage"])
        return None

    def mutate(self, action, payload):
        _require(action in {"check_supplement", "save_supplement"}, "unknown_action")
        payload = deepcopy(payload)
        self._payload(action, payload)
        fingerprint = digest(dict(action=PREFIX + action, payload=payload))
        with self._database() as connection:
            old = self._request(connection, payload["operation_id"], fingerprint)
            if old:
                _require(old["status"] == "COMPLETED", "pending_query_only_no_retry")
                return deepcopy(old["result"])
        request = dict(operation_id=payload["operation_id"], action=PREFIX + action, payload=payload,
                       request_hash=fingerprint, status="PENDING", result=None)
        return self._check(payload, request) if action == "check_supplement" else self._save(payload, request)

    def _check(self, payload, request):
        from hakimi_research.stock_intake_futu_supplement import review_futu_supplement
        originals, _ = self._original(payload["intake_id"], payload["expected_check_hash"])
        # Reconstruct the same four source slots independently of client/store
        # key order; the pure policy also canonicalizes its derived lineage.
        artifacts = {key: base64.b64decode(payload["artifacts"][key], validate=True) for key in KEYS}
        now = self.daily.clock() if self.daily.clock else datetime.now(timezone.utc)
        _require(isinstance(now, datetime) and now.tzinfo is not None, "trusted_clock_timezone_required")
        checked = review_futu_supplement(originals, artifacts, checked_at=now.astimezone(timezone.utc).isoformat())
        core = dict(original_intake_id=payload["intake_id"], review=checked)
        record = _seal(dict(core, id="supplement-" + digest(core)))
        with self._database(write=True) as connection:
            old = self._request(connection, payload["operation_id"], request["request_hash"])
            if old:
                _require(old["status"] == "COMPLETED", "pending_query_only_no_retry")
                return deepcopy(old["result"])
            existing = connection.execute("SELECT body FROM reviews WHERE id=?", (record["id"],)).fetchone()
            _require(existing is None or existing[0] == canonical_bytes(record), "review_collision")
            connection.execute("INSERT OR IGNORE INTO reviews VALUES(?,?)", (record["id"], canonical_bytes(record)))
            result = self._view(connection, record)
            request.update(status="COMPLETED", result=result)
            connection.execute("INSERT INTO requests VALUES(?,?)", (payload["operation_id"], canonical_bytes(_seal(request))))
        return result

    def _save(self, payload, request):
        from hakimi_research.stock_intake_futu_supplement import build_futu_supplement
        from hakimi_research.input_workflow import _retain
        with self._database() as connection:
            record = self._review(connection, payload["supplement_id"])
            _require(not connection.execute("SELECT 1 FROM claims WHERE review_id=?", (record["id"],)).fetchone(),
                     "review_already_claimed_no_retry")
        checked = record["review"]
        originals, _ = self._original(record["original_intake_id"], checked["binding"]["original_check_hash"])
        for name, raw in originals.items():
            _require(base64.b64decode(checked["retained_originals"][name]["raw_base64"], validate=True) == raw,
                     "original_bytes_changed_since_review")
        artifacts = {key: base64.b64decode(checked["reader_diagnostic"]["retained_artifacts"][key]["raw_base64"], validate=True)
                     for key in KEYS}
        built = build_futu_supplement(originals, artifacts, checked_at=checked["times"]["supplement_checked_at"],
            expected_check_hash=payload["expected_check_hash"], confirmed_security=payload["confirmed_security"],
            acknowledge_source_limits=payload["acknowledge_source_limits"])
        _require(built["check"] == checked, "saved_review_changed")
        raw = canonical_bytes(built["snapshot"])
        target = self.daily._path(self.daily.root / "data" / "snapshots" / built["snapshot"]["snapshot_id"] / (sha256(raw).hexdigest() + ".json"))
        if target.exists():
            _require(target.stat().st_nlink == 1 and target.read_bytes() == raw, "input_collision")
        input_id = self.daily._id(target)
        with self._database(write=True) as connection:
            old = self._request(connection, payload["operation_id"], request["request_hash"])
            if old:
                _require(old["status"] == "COMPLETED", "pending_query_only_no_retry")
                return deepcopy(old["result"])
            _require(not connection.execute("SELECT 1 FROM claims WHERE review_id=?", (record["id"],)).fetchone(),
                     "review_already_claimed_no_retry")
            connection.execute("INSERT INTO claims VALUES(?,?,?)", (record["id"], payload["operation_id"], input_id))
            connection.execute("INSERT INTO requests VALUES(?,?)", (payload["operation_id"], canonical_bytes(_seal(request))))
        # Any interruption from here leaves PENDING. Neither GET nor replay calls
        # _retain again, including when the immutable write already succeeded.
        self.daily._path(target)
        retained = _retain(self.daily.root, raw)
        _require(Path(retained["path"]) == target, "retained_path_changed")
        saved = self.daily._view("inputs", target)
        lineage = dict(original_intake_id=record["original_intake_id"], original_check_hash=checked["binding"]["original_check_hash"],
            supplement_id=record["id"], supplement_check_hash=checked["check_hash"],
            snapshot_id=built["snapshot"]["snapshot_id"], input_id=input_id, source_truth_verified=False)
        saved["supplement_lineage"] = lineage
        result = self._view(None, record)
        result.update(can_save=False, saved_input_id=input_id, saved_input=saved,
            reason="SUPPLEMENT_INPUT_SAVED_NO_TASK_OR_RUN",
            saved_input_view_scope="SAVED_COMPLETION_RECEIPT_NOT_CURRENT_REVALIDATION")
        result["diagnostic"].update(summary="新输入已另存；原检查不变，未创建任务或运行研究。来源完整性和截至时点仍未知。",
            action="可从已保存行情只读找回并核验输入；此处是保存时回执，创建任务和运行仍须分别明确操作。")
        with self._database(write=True) as connection:
            pending = self._request(connection, payload["operation_id"], request["request_hash"])
            _require(pending is not None and pending["status"] == "PENDING", "save_receipt_changed")
            request.update(status="COMPLETED", result=result)
            connection.execute("UPDATE requests SET body=? WHERE id=?", (canonical_bytes(_seal(request)), payload["operation_id"]))
        return result
