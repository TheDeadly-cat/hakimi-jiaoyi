"""Explicit copies of verified historical inputs using existing operation receipts.

The old workspace is read only. The canonical Workbench owns the durable claim,
the content-addressed write and its completion record. Receipt reads never
construct a writer, retry an unknown copy, or claim the old source is current.
"""
from copy import deepcopy
from hashlib import sha256
import base64
import re
import stat

from hakimi_research.documents import canonical_bytes, digest, parse_document
from hakimi_research.equity_dataset import verify_equity_snapshot
from .terminal_workspace_history import _document, _guard_tree


ACTION = "terminal_import_history_input"
SCHEMA = "terminal-history-input-copy-v1"
ORIGIN_SCHEMA = "terminal-history-input-origin-v1"
OP = re.compile(r"history-copy-[A-Za-z0-9_-]{8,64}\Z")
ID = re.compile(r"[a-f0-9]{32}\Z")
HASH = re.compile(r"[a-f0-9]{64}\Z")
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_REQUESTS = 512
FIELDS = {"operation_id", "workspace_id", "input_id", "expected_file_sha256", "expected_snapshot_id",
          "confirmed_security", "acknowledge_source_limits"}
PERMISSIONS = dict(research_only=True, paper_allowed=False, live_allowed=False, order_allowed=False)


def _require(value, reason):
    if not value:
        raise ValueError("history_copy_" + reason)


class TerminalHistoryInputImport:
    def __init__(self, daily, history):
        self.daily, self.history = daily, history

    @staticmethod
    def _payload(payload):
        _require(type(payload) is dict and set(payload) == FIELDS, "exact_fields_required")
        _require(type(payload["operation_id"]) is str and OP.fullmatch(payload["operation_id"]), "operation_id_invalid")
        for field in ("workspace_id", "input_id"):
            _require(type(payload[field]) is str and ID.fullmatch(payload[field]), "opaque_source_id_required")
        for field in ("expected_file_sha256", "expected_snapshot_id"):
            _require(type(payload[field]) is str and HASH.fullmatch(payload[field]), "expected_hash_required")
        _require(type(payload["confirmed_security"]) is dict and payload["confirmed_security"], "security_confirmation_required")
        _require(payload["acknowledge_source_limits"] is True, "source_limits_confirmation_required")

    def _folder(self, operation_id):
        _require(type(operation_id) is str and OP.fullmatch(operation_id), "operation_id_invalid")
        return self.daily._path(self.daily.root / "operations" / operation_id)

    def _destination(self, raw, snapshot):
        return self.daily._path(self.daily.root / "data" / "snapshots" / snapshot["snapshot_id"] / (sha256(raw).hexdigest() + ".json"))

    def _target_guard(self, target, raw):
        target = self.daily._path(target)
        if target.exists():
            info = target.lstat()
            _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size == len(raw)
                     and target.read_bytes() == raw, "destination_collision")
        return target

    @staticmethod
    def _common(operation_id, status, request_hash=None):
        return dict(schema_version=SCHEMA, operation_id=operation_id, action=ACTION, status=status,
                    request_hash=request_hash, saved_input_id=None, saved_input=None,
                    receipt_scope="SAVED_OPERATION_FACT_NOT_CURRENT_SOURCE_VALIDATION",
                    current_source_rechecked=False, source_truth_verified=False,
                    new_economic_runs=0, automatic_retry=False, permissions=dict(PERMISSIONS))

    def _operation(self, operation_id):
        folder = self._folder(operation_id)
        request_path = folder / "request.json"
        if not request_path.exists():
            _require(not (folder / "result.json").exists(), "orphan_result")
            return None
        _guard_tree(self.daily.root, folder)
        record = _document(self.daily.root, request_path)
        request = record.get("request")
        _require(type(request) is dict and set(request) == {"action", "operation_id", "content_base64", "history_origin"}, "foreign_operation")
        _require(request["action"] == "import_input" and request["operation_id"] == operation_id
                 and record.get("request_hash") == digest(request), "operation_request_changed")
        origin = request["history_origin"]
        _require(type(origin) is dict and set(origin) == {"schema_version", "action", "payload", "request_hash", "source"}
                 and origin["schema_version"] == ORIGIN_SCHEMA and origin["action"] == ACTION, "origin_invalid")
        self._payload(origin["payload"])
        _require(origin["payload"]["operation_id"] == operation_id
                 and origin["request_hash"] == digest(dict(action=ACTION, payload=origin["payload"])), "origin_request_changed")
        encoded = request["content_base64"]
        _require(type(encoded) is str and len(encoded) <= 4 * ((MAX_INPUT_BYTES + 2) // 3), "bounded_original_required")
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError) as exc:
            raise ValueError("history_copy_original_encoding_invalid") from exc
        snapshot = verify_equity_snapshot(parse_document(raw))
        self._check_source(origin["payload"], raw, snapshot)
        source = origin["source"]
        _require(type(source) is dict and source == self._source_summary(origin["payload"], snapshot, len(raw)), "origin_source_changed")
        return folder, record, request, origin, raw, snapshot

    @staticmethod
    def _check_source(payload, raw, snapshot):
        _require(0 < len(raw) <= MAX_INPUT_BYTES, "input_too_large")
        _require(sha256(raw).hexdigest() == payload["expected_file_sha256"]
                 and snapshot["snapshot_id"] == payload["expected_snapshot_id"], "source_changed_read_again")
        _require(canonical_bytes(snapshot["security"]) == canonical_bytes(payload["confirmed_security"]), "security_changed")
        _require(snapshot["research_admission"]["allowed"] is True, "source_not_admitted")

    @staticmethod
    def _source_summary(payload, snapshot, byte_count):
        return dict(workspace_id=payload["workspace_id"], input_id=payload["input_id"],
                    file_sha256=payload["expected_file_sha256"], snapshot_id=payload["expected_snapshot_id"],
                    security=deepcopy(snapshot["security"]), coverage_start=snapshot["sessions"][0]["date"],
                    coverage_end=snapshot["sessions"][-1]["date"], sessions=len(snapshot["sessions"]),
                    byte_count=byte_count, evidence_kind=snapshot["evidence_kind"],
                    source_authentication=snapshot["source_authentication"], source_truth_verified=False)

    def receipt(self, operation_id):
        operation = self._operation(operation_id)
        if operation is None:
            return self._common(operation_id, "NOT_RECORDED")
        folder, request_record, request, origin, raw, snapshot = operation
        view = self._common(operation_id, "PENDING", origin["request_hash"])
        view.update(source=deepcopy(origin["source"]), request=deepcopy(origin["payload"]),
                    recorded_at=request_record.get("recorded_at"),
                    message="原请求尚无完整结果；只查询这个编号，不重复复制。")
        result_path = folder / "result.json"
        if not result_path.exists():
            return view
        result = _document(self.daily.root, result_path)
        _require(result.get("operation_id") == operation_id and type(result.get("ok")) is bool, "result_changed")
        if result["ok"] is False:
            _require(result.get("status") == "STOPPED", "result_changed")
            view.update(status="STOPPED", error=str(result.get("error", "复制未完成"))[:2000],
                        message="原复制请求已停止；不会在查询时重新执行。")
            return view
        saved = result.get("result")
        target = self._destination(raw, snapshot)
        _require(result.get("status") == "COMMITTED" and type(saved) is dict
                 and saved.get("input_id") == snapshot["snapshot_id"]
                 and saved.get("file_sha256") == sha256(raw).hexdigest()
                 and saved.get("original_bytes_retained") is True
                 and saved.get("ref") == target.relative_to(self.daily.root).as_posix(), "saved_result_identity_changed")
        identity = self.daily._id(target)
        view.update(status="COMPLETED", saved_input_id=identity, completed_at=result.get("recorded_at"),
                    message="复制保存已完成；原件未改写，尚未建立任务或运行研究。",
                    saved_input_verification="UNAVAILABLE")
        try:
            self._target_guard(target, raw)
            current_raw, current = self.daily.verified_input(identity)
            _require(current_raw == raw and current["snapshot_id"] == snapshot["snapshot_id"], "saved_input_changed")
            view.update(saved_input=self.daily._view("inputs", target), saved_input_verification="VERIFIED_CURRENT_TARGET")
        except (ValueError, OSError, TypeError, KeyError) as exc:
            view["saved_input_read_error"] = str(exc)[:2000]
            view["message"] = "原回执确认已保存，但当前副本未通过读取校验；保留保存事实，只读核对，不重复复制。"
        return view

    def read(self, operation_id=None):
        if operation_id is not None:
            return self.receipt(operation_id)
        root = self.daily._path(self.daily.root / "operations")
        if not root.is_dir():
            return dict(schema_version=SCHEMA, items=[], warnings=[], read_only=True, new_economic_runs=0,
                        limits=dict(input_bytes=MAX_INPUT_BYTES))
        folders = sorted(p for p in root.iterdir() if p.name.startswith("history-copy-"))
        _require(len(folders) <= MAX_REQUESTS, "request_inventory_limit")
        items, warnings = [], []
        for folder in folders:
            try:
                items.append(self.receipt(folder.name))
            except (ValueError, OSError, TypeError, KeyError) as exc:
                warnings.append(folder.name + ": " + str(exc)[:300])
        items.sort(key=lambda value: (value.get("recorded_at") or "", value["operation_id"]), reverse=True)
        return dict(schema_version=SCHEMA, items=items, warnings=warnings, read_only=True, new_economic_runs=0,
                    limits=dict(input_bytes=MAX_INPUT_BYTES))

    def mutate(self, payload):
        payload = deepcopy(payload)
        self._payload(payload)
        fingerprint = digest(dict(action=ACTION, payload=payload))
        with self.daily._lock:
            prior = self.receipt(payload["operation_id"])
            if prior["status"] != "NOT_RECORDED":
                _require(prior["request_hash"] == fingerprint, "operation_id_payload_conflict")
                # A completed copy may be read after its source is gone. Its
                # immutable receipt says what was saved, not what is there now.
                _require(prior["status"] == "COMPLETED", "outcome_query_only_no_retry")
                return prior
            _require(self.history is not None, "history_reader_unavailable")
            raw, snapshot, source = self.history.verified_input(payload["workspace_id"], payload["input_id"])
            self._check_source(payload, raw, snapshot)
            _require(source.get("available") is True and source.get("verification_status") == "VERIFIED_RECORD", "source_not_admitted")
            target = self._target_guard(self._destination(raw, snapshot), raw)
            origin = dict(schema_version=ORIGIN_SCHEMA, action=ACTION, payload=payload, request_hash=fingerprint,
                          source=self._source_summary(payload, snapshot, len(raw)))
            request = dict(action="import_input", operation_id=payload["operation_id"],
                           content_base64=base64.b64encode(raw).decode("ascii"), history_origin=origin)
            # This existing action includes all request fields in its durable
            # hash, claims before _retain, and never reruns a pending operation.
            self.daily._path(target)
            self.daily._ensure_writer().action(request)
            return self.receipt(payload["operation_id"])
