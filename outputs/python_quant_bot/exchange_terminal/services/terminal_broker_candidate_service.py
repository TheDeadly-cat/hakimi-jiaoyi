"""Offline, reviewable broker candidates. No SDK, client, socket or credential IO.

The root is a NEW candidate directory, never an old account or research store.
The trusted resolver uses terminal_saved_results.resolve_execution_research's
{binding, display, assumptions, owner_id} result, optionally wrapped with a
matching reference and other trusted presentation fields. COMPLETED is recorded
inside binding. Only the needed saved research fields are projected here.
The caller dispatches stop directly, outside a long-running job queue.
"""
from copy import deepcopy
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import stat
from threading import RLock


SCHEMA = "hakimi-broker-candidate-v2"
CONTROL_SCHEMA = "hakimi-broker-candidate-control-v1"
MODES = {"OFFICIAL_SIMULATION": "official-simulation", "LIVE_CANDIDATE": "live-candidate"}
PERMISSIONS = {"external_connection_allowed": False, "submit_allowed": False,
               "query_allowed": False, "cancel_allowed": False, "unlock_allowed": False,
               "adapter_installed": False, "automatic_resume": False, "automatic_retry": False}
FIELDS = {
    "account_id": "候选账户编号", "market": "市场", "asset_class": "资产类型（股票）", "asset_code": "证券代码", "currency": "币种",
    "max_quantity": "单笔数量上限", "max_notional": "单笔金额上限", "side": "买卖方向",
    "quantity": "本次数量", "limit_price": "本次限价", "time_in_force": "订单有效方式", "expires_at": "候选失效时间",
}
HASH = re.compile(r"[a-f0-9]{64}\Z")
REQUEST = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{7,119}\Z")
MAX_BYTES, MAX_RECORDS = 128 * 1024, 1000


class CandidateError(ValueError):
    pass


def _json(value):
    try:
        raw = json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()
    except (TypeError, ValueError) as error:
        raise CandidateError("finite_json_required") from error
    if len(raw) > MAX_BYTES:
        raise CandidateError("candidate_record_too_large")
    return raw


def _fields(value, allowed, required=()):
    if type(value) is not dict or set(value) - set(allowed) or set(required) - set(value):
        raise CandidateError("candidate_fields_invalid")


def _id(value):
    if type(value) is not str or not HASH.fullmatch(value):
        raise CandidateError("candidate_identity_invalid")
    return value


def _seal(value):
    return {**value, "id": sha256(_json(value)).hexdigest()}


def _timestamp(value):
    if type(value) is not str or len(value) > 40:
        raise CandidateError("candidate_expiry_invalid")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            raise ValueError()
        return result.astimezone(timezone.utc)
    except ValueError as error:
        raise CandidateError("candidate_expiry_invalid") from error


def _money(value):
    if type(value) is not str or not re.fullmatch(r"(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,8})?", value):
        raise CandidateError("positive_decimal_string_required")
    try:
        result = Decimal(value)
    except InvalidOperation as error:
        raise CandidateError("positive_decimal_string_required") from error
    if not 0 < result <= Decimal("1000000000000"):
        raise CandidateError("positive_bounded_amount_required")
    return result


def _reference(value):
    _fields(value, {"kind", "id"}, {"kind", "id"})
    length = {"terminal_run": 64, "core_run": 24}.get(value["kind"]) if type(value["kind"]) is str else None
    if length is None or type(value["id"]) is not str or not re.fullmatch(r"[a-f0-9]{%d}" % length, value["id"]):
        raise CandidateError("saved_research_reference_required")
    return deepcopy(value)


def _project_research(value, reference):
    reference = _reference(reference)
    if type(value) is not dict or "reference" in value and value["reference"] != reference:
        raise CandidateError("saved_research_reference_mismatch")
    binding = value.get("binding")
    required = {"schema_version", "status", "engine_id", "strategy_id", "strategy_params", "task_id", "task_version", "input_id", "report_id", "report_hash"}
    if (type(binding) is not dict or not required.issubset(binding)
            or binding.get("schema_version") != "hakimi-offline-research-binding-v1" or binding.get("status") != "COMPLETED"):
        raise CandidateError("verified_completed_research_required")
    selected = {key: deepcopy(binding[key]) for key in required | {"risk", "costs", "source_hash", "security_id"} if key in binding}
    for key in ("engine_id", "strategy_id", "task_id", "input_id", "report_id"):
        if type(selected[key]) is not str or not selected[key].strip() or len(selected[key]) > 200:
            raise CandidateError("saved_research_identity_invalid")
    if not (type(selected["task_version"]) is int and selected["task_version"] > 0
            or type(selected["task_version"]) is str and 0 < len(selected["task_version"].strip()) <= 200):
        raise CandidateError("saved_research_version_invalid")
    for key in ("report_hash", "source_hash"):
        if key in selected:
            _id(selected[key])
    for key in ("strategy_params", "risk", "costs"):
        if key in selected and (type(selected[key]) is not dict or any(type(name) is not str for name in selected[key])):
            raise CandidateError("saved_research_parameters_invalid")
    if reference["kind"] == "terminal_run" and (selected["report_id"] != reference["id"] or selected["report_hash"] != reference["id"]):
        raise CandidateError("saved_research_reference_mismatch")
    display = value.get("display", {})
    assumptions = value.get("assumptions", {})
    if type(display) is not dict or type(assumptions) is not dict:
        raise CandidateError("saved_research_projection_invalid")
    projected_display = {key: deepcopy(display[key]) for key in ("security_id", "symbol", "currency", "asset_class") if key in display}
    # Empty identity is missing, never an invitation to guess from a ticker.
    for key in list(projected_display):
        item = projected_display[key]
        if item is None or item == "":
            projected_display.pop(key)
        elif type(item) is not str or item != item.strip() or len(item) > 200:
            raise CandidateError("saved_research_display_invalid")
    if selected.get("security_id") in (None, ""):
        selected.pop("security_id", None)
    elif type(selected["security_id"]) is not str or selected["security_id"] != selected["security_id"].strip():
        raise CandidateError("saved_research_security_identity_invalid")
    result = {"reference": reference, "binding": selected, "display": projected_display,
              "assumptions": {key: deepcopy(assumptions[key]) for key in ("fill_model", "quantity_policy") if key in assumptions}}
    _json(result)
    return result


def _security_binding(config, research):
    missing, blockers = [], []
    if research is None:
        return {"status": "MISSING", "saved_security": {}, "account_verified": False, "asset_rules_verified": False}, missing, blockers
    display, binding = research["display"], research["binding"]
    for key, label in (("security_id", "保存研究的证券身份"), ("symbol", "保存研究的证券代码"),
                       ("currency", "保存研究的币种"), ("asset_class", "保存研究的资产类别")):
        if key not in display:
            missing.append({"field": "research.display." + key, "label": label})
    if "security_id" not in binding:
        missing.append({"field": "research.binding.security_id", "label": "研究绑定中的证券身份"})
    if display.get("security_id") and binding.get("security_id") and display["security_id"] != binding["security_id"]:
        blockers.append("RESEARCH_SECURITY_IDENTITY_MISMATCH")
    if "currency" in config and "currency" in display and config["currency"] != display["currency"]:
        blockers.append("RESEARCH_CURRENCY_MISMATCH")
    supported = display.get("asset_class") == "US_EQUITY" and display.get("currency") == "USD"
    if "asset_class" in display and "currency" in display and not supported:
        blockers.append("SAVED_RESEARCH_MARKET_MAPPING_UNSUPPORTED")
    if supported:
        if "market" in config and config["market"] != "US":
            blockers.append("RESEARCH_MARKET_MISMATCH")
        if "asset_code" in config and "symbol" in display and config["asset_code"] != "US." + display["symbol"]:
            blockers.append("RESEARCH_ASSET_CODE_MISMATCH")
    declared_fields = {"market", "asset_class", "asset_code", "currency"}
    matched = not blockers and not missing and supported and declared_fields.issubset(config)
    status = "MISMATCH_OR_UNSUPPORTED" if blockers else "MATCHED_SAVED_DECLARATION" if matched else "MISSING"
    return {"status": status, "saved_security": deepcopy(display), "account_verified": False,
            "asset_rules_verified": False, "broker_mapping_verified": False}, missing, blockers


class BrokerCandidateService:
    def __init__(self, root, *, research_resolver, verified_sdk_metadata=None, clock=None):
        if not callable(research_resolver):
            raise CandidateError("trusted_research_resolver_required")
        self.root = Path(root).expanduser().absolute()
        self._safe(self.root)
        self._resolver, self._clock = research_resolver, clock or (lambda: datetime.now(timezone.utc))
        self._lock = RLock()
        # This is trusted package-loader input, never a renderer request field.
        if verified_sdk_metadata is not None:
            _fields(verified_sdk_metadata, {"name", "version", "manifest_sha256"}, {"name", "version", "manifest_sha256"})
            if (verified_sdk_metadata["name"] != "futu-api" or type(verified_sdk_metadata["version"]) is not str
                    or not re.fullmatch(r"[0-9]+(?:\.[0-9]+){2}", verified_sdk_metadata["version"])):
                raise CandidateError("verified_package_metadata_invalid")
            _id(verified_sdk_metadata["manifest_sha256"])
        self._sdk = deepcopy(verified_sdk_metadata)

    def _safe(self, path):
        path = Path(path).absolute()
        if path != self.root and not path.is_relative_to(self.root):
            raise CandidateError("candidate_path_outside_root")
        for candidate in (path, *path.parents):
            try:
                info = candidate.lstat()
            except FileNotFoundError:
                continue
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
                raise CandidateError("candidate_reparse_path_rejected")
        return path

    def _mode(self, mode):
        if type(mode) is not str or mode not in MODES:
            raise CandidateError("explicit_candidate_mode_required")
        return self._safe(self.root / MODES[mode])

    def _now(self):
        value = self._clock()
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise CandidateError("aware_clock_required")
        return value.astimezone(timezone.utc)

    @contextmanager
    def _control(self, mode, *, write=False):
        """Cross-instance commit barrier. Never covers resolver/history scans.

        DELETE journaling and FULL sync keep a control transition atomic. Reads
        use SQLite mode=ro and never create a directory, DB, or receipt.
        """
        path = self._safe(self._mode(mode) / "control.sqlite3")
        if not write and not path.exists():
            yield None
            return
        if write:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                temporary = self._safe(path.with_name(".control." + secrets.token_hex(8) + ".pending"))
                try:
                    bootstrap = sqlite3.connect(str(temporary))
                    try:
                        bootstrap.execute("CREATE TABLE controls (sequence INTEGER PRIMARY KEY, "
                            "request_id TEXT UNIQUE NOT NULL, identity TEXT UNIQUE NOT NULL, body BLOB NOT NULL)")
                        bootstrap.commit()
                    finally:
                        bootstrap.close()
                    try:
                        os.link(temporary, path)
                    except FileExistsError:
                        pass  # Another writer published a complete DB first.
                finally:
                    temporary.unlink(missing_ok=True)
        connection = sqlite3.connect(str(path) if write else path.as_uri() + "?mode=ro",
                                     uri=not write, isolation_level=None, timeout=2)
        try:
            if write:
                connection.execute("PRAGMA synchronous=FULL")
                connection.execute("BEGIN IMMEDIATE")
            else:
                connection.execute("BEGIN")
            yield connection
            if write:
                connection.commit()
        except BaseException:
            if write:
                connection.rollback()
            raise
        finally:
            connection.close()

    def _control_row(self, mode, row):
        if row is None:
            return None
        sequence, request_id, identity, raw = row
        if type(raw) is not bytes or len(raw) > MAX_BYTES:
            raise CandidateError("candidate_control_record_size_invalid")
        value = json.loads(raw)
        if (type(value) is not dict or value.get("schema_version") != CONTROL_SCHEMA
                or set(value) != {"schema_version", "kind", "mode", "sequence", "previous_control_id", "request_id",
                                  "request_sha256", "action", "payload", "created_at", "result", "id"}
                or value.get("kind") != "controls" or type(value.get("sequence")) is not int
                or value.get("mode") != mode or value.get("sequence") != sequence
                or value.get("request_id") != request_id or value.get("id") != identity
                or _seal({k: v for k, v in value.items() if k != "id"}) != value
                or value.get("action") not in {"stop", "resume"}
                or type(request_id) is not str or not REQUEST.fullmatch(request_id)):
            raise CandidateError("candidate_control_record_changed")
        _timestamp(value["created_at"])
        if value["previous_control_id"] is not None:
            _id(value["previous_control_id"])
        payload = value.get("payload")
        required = {"mode", "request_id", "reason"} | ({"expected_stop_receipt_id"} if value["action"] == "resume" else set())
        _fields(payload, required, required)
        if (payload["mode"] != mode or payload["request_id"] != request_id
                or value.get("request_sha256") != sha256(_json({"action": value["action"], "payload": payload})).hexdigest()
                or type(payload["reason"]) is not str or not 1 <= len(payload["reason"].strip()) <= 200):
            raise CandidateError("candidate_control_request_changed")
        result = value.get("result")
        expected_status = "STOPPED" if value["action"] == "stop" else "OFFLINE_PREPARATION_RESUMED"
        if (type(result) is not dict or result.get("status") != expected_status or result.get("mode") != mode
                or _json(result.get("permissions")) != _json(PERMISSIONS)
                or result.get("new_intents_blocked") is not (value["action"] == "stop")
                or result.get("broker_orders_cancelled") is not False):
            raise CandidateError("candidate_control_permissions_changed")
        if value["action"] == "resume":
            _id(payload["expected_stop_receipt_id"])
            if result.get("resumed_stop_receipt_id") != payload["expected_stop_receipt_id"]:
                raise CandidateError("candidate_control_resume_binding_changed")
        return value

    def _head(self, mode, connection):
        if connection is None:
            return None
        rows = connection.execute("SELECT sequence,request_id,identity,body FROM controls ORDER BY sequence DESC LIMIT 2").fetchall()
        if not rows:
            return None
        head = self._control_row(mode, rows[0])
        count = connection.execute("SELECT COUNT(*) FROM controls").fetchone()[0]
        previous = self._control_row(mode, rows[1]) if len(rows) > 1 else None
        if (count > MAX_RECORDS or head["sequence"] != count
                or head.get("previous_control_id") != (previous["id"] if previous else None)
                or (previous and previous["sequence"] != head["sequence"] - 1)
                or (head["action"] == "resume" and (previous is None or previous["action"] != "stop"
                    or head["payload"]["expected_stop_receipt_id"] != previous["id"]))):
            raise CandidateError("candidate_control_history_changed")
        return head

    def _control_state(self, mode, connection):
        head = self._head(mode, connection)
        stopped = head is not None and head["action"] == "stop"
        return {"state": "STOPPED" if stopped else "OFFLINE_PREPARATION_ALLOWED",
                "new_intents_blocked": stopped, "revision": head["sequence"] if head else 0,
                "latest_control_receipt_id": head["id"] if head else None,
                "latest_stop_receipt_id": (head["id"] if stopped else head["payload"]["expected_stop_receipt_id"]) if head else None,
                "resume_allowed": bool(stopped and head["sequence"] + 1 < MAX_RECORDS),
                "permissions": dict(PERMISSIONS)}

    def _control_result(self, receipt):
        result = {**deepcopy(receipt["result"]), "control_receipt_id": receipt["id"]}
        if receipt["action"] == "stop":
            result["stop_receipt_id"] = receipt["id"]
        return result

    def _control_request(self, mode, request_id, connection):
        if connection is None:
            return None
        return self._control_row(mode, connection.execute(
            "SELECT sequence,request_id,identity,body FROM controls WHERE request_id=?", (request_id,)).fetchone())

    def _read(self, path, mode, kind):
        path = self._safe(path)
        with path.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise CandidateError("candidate_record_too_large")
        value = json.loads(raw)
        if (type(value) is not dict or value.get("schema_version") != SCHEMA or value.get("mode") != mode
                or value.get("kind") != kind or _seal({k: v for k, v in value.items() if k != "id"}) != value):
            raise CandidateError("candidate_saved_record_changed")
        expected = sha256(value["request_id"].encode()).hexdigest() if kind in {"receipts", "stops"} else value["id"]
        if path.stem != expected:
            raise CandidateError("candidate_saved_record_identity_mismatch")
        if kind == "configs":
            research = value.get("research")
            if research is None:
                if value.get("research_sha256") is not None:
                    raise CandidateError("candidate_saved_research_changed")
            else:
                projected = _project_research(research, research.get("reference"))
                if _json(projected) != _json(research) or sha256(_json(projected)).hexdigest() != value.get("research_sha256"):
                    raise CandidateError("candidate_saved_research_changed")
        elif kind == "intents":
            saved = self._saved(mode, value.get("config_id"))
            binding, missing, blockers = _security_binding(saved["config"], saved["research"])
            if (_json(value.get("permissions")) != _json(PERMISSIONS) or value.get("status") != "UNSENT_OFFLINE_PREVIEW"
                    or _json(value.get("terms")) != _json(saved["config"]) or value.get("research_sha256") != saved["research_sha256"]
                    or _json(value.get("security_binding")) != _json(binding) or missing or blockers
                    or binding["status"] != "MATCHED_SAVED_DECLARATION"):
                raise CandidateError("candidate_saved_intent_binding_changed")
        elif kind in {"receipts", "stops"}:
            if value.get("action") not in ({"stop"} if kind == "stops" else {"save", "prepare_intent"}):
                raise CandidateError("candidate_saved_receipt_action_changed")
            self._validate_result(mode, value["action"], value.get("result"))
        return value

    def _validate_result(self, mode, action, result):
        if (type(result) is not dict or result.get("mode") != mode
                or _json(result.get("permissions")) != _json(PERMISSIONS)):
            raise CandidateError("candidate_saved_receipt_permissions_changed")
        if action == "save":
            if result.get("status") != "SAVED_OFFLINE_CANDIDATE":
                raise CandidateError("candidate_saved_receipt_status_changed")
            self._saved(mode, result.get("config_id"))
        elif action == "prepare_intent":
            intent = result.get("intent")
            if type(intent) is not dict or result.get("status") != "UNSENT_OFFLINE_PREVIEW":
                raise CandidateError("candidate_saved_receipt_status_changed")
            saved = self._read(self._mode(mode) / "intents" / (_id(intent.get("id")) + ".json"), mode, "intents")
            if _json(saved) != _json(intent):
                raise CandidateError("candidate_saved_receipt_intent_changed")
        elif (result.get("status") != "STOPPED" or result.get("new_intents_blocked") is not True
                or result.get("broker_orders_cancelled") is not False):
            raise CandidateError("candidate_saved_stop_claim_changed")

    def _write(self, path, value):
        path, raw = self._safe(path), _json(value)
        if path.exists():
            if path.read_bytes() != raw:
                raise CandidateError("candidate_immutable_conflict")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._safe(path.with_name("." + path.name + "." + secrets.token_hex(8) + ".pending"))
        try:
            with temporary.open("xb") as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            try:
                os.link(temporary, path)
            except FileExistsError:
                if path.read_bytes() != raw:
                    raise CandidateError("candidate_immutable_conflict")
        finally:
            temporary.unlink(missing_ok=True)

    def _records(self, mode, kind):
        directory = self._safe(self._mode(mode) / kind)
        if not directory.exists():
            return []
        files = list(directory.glob("*.json"))
        if len(files) > MAX_RECORDS:
            raise CandidateError("candidate_capacity_exceeded")
        return [self._read(path, mode, kind) for path in sorted(files)]

    def _record_count(self, mode, kind):
        directory = self._safe(self._mode(mode) / kind)
        count = 0
        if directory.exists():
            for _ in directory.glob("*.json"):
                count += 1
                if count > MAX_RECORDS:
                    raise CandidateError("candidate_capacity_exceeded")
        return count

    def _publish(self, mode, kind, value):
        path = self._safe(self._mode(mode) / kind / (value["id"] + ".json"))
        if not path.exists() and self._record_count(mode, kind) >= MAX_RECORDS:
            raise CandidateError("candidate_capacity_exceeded")
        self._write(path, value)

    def _request(self, mode, action, payload, connection=None):
        request_id = payload.get("request_id")
        if type(request_id) is not str or not REQUEST.fullmatch(request_id):
            raise CandidateError("bounded_request_id_required")
        key = sha256(request_id.encode()).hexdigest()
        kind = "receipts"
        path = self._safe(self._mode(mode) / kind / (key + ".json"))
        if connection is None:
            with self._control(mode) as reader:
                conflict = self._control_request(mode, request_id, reader)
        else:
            conflict = self._control_request(mode, request_id, connection)
        if conflict is not None:
            raise CandidateError("request_id_payload_conflict")
        fingerprint = sha256(_json({"action": action, "payload": payload})).hexdigest()
        if path.exists():
            receipt = self._read(path, mode, kind)
            if receipt["request_id"] != request_id or receipt["request_sha256"] != fingerprint:
                raise CandidateError("request_id_payload_conflict")
            result = receipt["result"]
            if action == "save":
                saved = self._saved(mode, result["config_id"])
                reference = saved["research"]["reference"] if saved["research"] else None
                if _json(saved["config"]) != _json(payload["config"]) or reference != payload.get("research_reference"):
                    raise CandidateError("candidate_saved_receipt_request_changed")
            if action == "prepare_intent" and (result["intent"]["config_id"] != payload["config_id"] or result["intent"]["request_id"] != request_id):
                raise CandidateError("candidate_saved_receipt_request_changed")
            return path, fingerprint, deepcopy(receipt["result"])
        if self._record_count(mode, kind) >= MAX_RECORDS:
            raise CandidateError("candidate_capacity_exceeded")
        return path, fingerprint, None

    def _receipt(self, mode, action, payload, path, fingerprint, result):
        self._write(path, _seal({"schema_version": SCHEMA, "kind": "stops" if action == "stop" else "receipts", "mode": mode,
            "request_id": payload["request_id"], "request_sha256": fingerprint, "action": action,
            "created_at": self._now().isoformat(), "result": result}))
        return deepcopy(result)

    def _resolve(self, reference):
        reference = _reference(reference)
        value = self._resolver(deepcopy(reference))
        return _project_research(value, reference)

    def _configuration(self, value):
        _fields(value, FIELDS)
        value = deepcopy(value)
        for field, item in value.items():
            if item is None or item == "":
                raise CandidateError("omit_missing_fields_instead_of_empty_values")
            if field == "account_id" and (type(item) is not str or not re.fullmatch(r"[1-9][0-9]{0,19}", item) or int(item) >= 2**64):
                raise CandidateError("explicit_account_id_required")
            if field == "market" and (type(item) is not str or item not in {"US", "HK"}):
                raise CandidateError("candidate_market_not_supported")
            if field == "asset_class" and item != "EQUITY":
                raise CandidateError("candidate_equity_only")
            if field == "currency" and (type(item) is not str or item not in {"USD", "HKD"}):
                raise CandidateError("candidate_currency_not_supported")
            if field == "asset_code" and (type(item) is not str or not re.fullmatch(r"(?:US\.[A-Z][A-Z0-9.-]{0,19}|HK\.[0-9]{5})", item)):
                raise CandidateError("explicit_equity_code_required")
            if field in {"quantity", "max_quantity"} and (type(item) is not int or not 1 <= item <= 1000000):
                raise CandidateError("bounded_whole_share_quantity_required")
            if field in {"limit_price", "max_notional"}:
                _money(item)
            if field == "side" and (type(item) is not str or item not in {"BUY", "SELL"}):
                raise CandidateError("explicit_buy_or_sell_required")
            if field == "time_in_force" and item != "DAY":
                raise CandidateError("candidate_day_limit_order_only")
            if field == "expires_at":
                expiry = _timestamp(item)
                if (expiry - self._now()).total_seconds() > 86400:
                    raise CandidateError("candidate_expiry_must_be_within_24_hours")
        return value

    def _saved(self, mode, config_id):
        return self._read(self._mode(mode) / "configs" / (_id(config_id) + ".json"), mode, "configs")

    def _is_stopped(self, mode):
        with self._control(mode) as connection:
            return self._control_state(mode, connection)["new_intents_blocked"]

    def save(self, payload):
        payload = deepcopy(payload)
        _fields(payload, {"mode", "request_id", "config", "research_reference"}, {"mode", "request_id", "config"})
        mode = payload["mode"]; self._mode(mode)
        with self._lock:
            _, _, old = self._request(mode, "save", payload)
            if old is not None:
                return old
        config = self._configuration(payload["config"])
        research = self._resolve(payload["research_reference"]) if "research_reference" in payload else None
        saved = _seal({"schema_version": SCHEMA, "kind": "configs", "mode": mode, "config": config,
                       "research": research, "research_sha256": sha256(_json(research)).hexdigest() if research else None})
        with self._lock, self._control(mode, write=True) as connection:
            path, fingerprint, old = self._request(mode, "save", payload, connection)
            if old is not None:
                return old
            self._publish(mode, "configs", saved)
            result = {"status": "SAVED_OFFLINE_CANDIDATE", "mode": mode, "config_id": saved["id"], "permissions": dict(PERMISSIONS)}
            return self._receipt(mode, "save", payload, path, fingerprint, result)

    def check(self, mode, config_id, *, _control_state=None):
        with self._lock:
            saved = self._saved(mode, config_id)
            config = self._configuration(saved["config"])
            missing = [{"field": field, "label": label} for field, label in FIELDS.items() if field not in config]
            if saved["research"] is None:
                missing.append({"field": "research_reference", "label": "已完成且可核验的研究版本"})
            security_binding, security_missing, blockers = _security_binding(config, saved["research"])
            missing.extend(security_missing)
            stopped = _control_state["new_intents_blocked"] if _control_state is not None else self._is_stopped(mode)
            if stopped: blockers.append("CANDIDATE_STOPPED")
            if "expires_at" in config and _timestamp(config["expires_at"]) <= self._now(): blockers.append("CANDIDATE_EXPIRED")
            if all(k in config for k in ("market", "currency")) and {"US": "USD", "HK": "HKD"}[config["market"]] != config["currency"]:
                blockers.append("MARKET_CURRENCY_MISMATCH")
            if all(k in config for k in ("market", "asset_code")) and not config["asset_code"].startswith(config["market"] + "."):
                blockers.append("MARKET_ASSET_MISMATCH")
            if all(k in config for k in ("quantity", "max_quantity")) and config["quantity"] > config["max_quantity"]:
                blockers.append("QUANTITY_EXCEEDS_CANDIDATE_LIMIT")
            notional = _money(config["limit_price"]) * config["quantity"] if all(k in config for k in ("limit_price", "quantity")) else None
            if notional is not None and "max_notional" in config and notional > _money(config["max_notional"]):
                blockers.append("NOTIONAL_EXCEEDS_CANDIDATE_LIMIT")
            return {"mode": mode, "config_id": saved["id"], "status": "BLOCKED" if blockers else "MISSING" if missing else "OFFLINE_PREVIEW_ONLY",
                "missing": missing, "blockers": blockers, "order_notional_excluding_fees": str(notional) if notional is not None else None,
                "security_binding": security_binding,
                "fee_verified": False, "account_verified": False, "asset_rules_verified": False, "connected": False,
                "message": "仅检查本地候选；尚未连接券商，也未核对账户、持仓、交易权限或费用。", "permissions": dict(PERMISSIONS)}

    def prepare_intent(self, payload):
        payload = deepcopy(payload)
        _fields(payload, {"mode", "request_id", "config_id"}, {"mode", "request_id", "config_id"})
        mode = payload["mode"]; self._mode(mode)
        with self._control(mode) as connection:
            preparation_revision = self._control_state(mode, connection)["revision"]
        with self._lock:
            _, _, old = self._request(mode, "prepare_intent", payload)
            if old is not None: return old
            checked = self.check(mode, payload["config_id"])
            if checked["status"] != "OFFLINE_PREVIEW_ONLY": raise CandidateError("candidate_incomplete_expired_or_stopped")
            saved = self._saved(mode, payload["config_id"])
        try:
            research = self._resolve(saved["research"]["reference"])
        except CandidateError as error:
            raise CandidateError("saved_research_binding_changed") from error
        if sha256(_json(research)).hexdigest() != saved["research_sha256"]:
            raise CandidateError("saved_research_binding_changed")
        with self._lock, self._control(mode, write=True) as connection:
            path, fingerprint, old = self._request(mode, "prepare_intent", payload, connection)
            if old is not None: return old
            if self.check(mode, payload["config_id"])["status"] != "OFFLINE_PREVIEW_ONLY":
                raise CandidateError("candidate_incomplete_expired_or_stopped")
            if self._control_state(mode, connection)["revision"] != preparation_revision:
                raise CandidateError("candidate_control_changed_during_preparation")
            intent = _seal({"schema_version": SCHEMA, "kind": "intents", "mode": mode, "config_id": saved["id"],
                "request_id": payload["request_id"], "research_sha256": saved["research_sha256"], "terms": saved["config"],
                "security_binding": deepcopy(checked["security_binding"]),
                "status": "UNSENT_OFFLINE_PREVIEW", "permissions": dict(PERMISSIONS)})
            self._publish(mode, "intents", intent)
            result = {"status": "UNSENT_OFFLINE_PREVIEW", "mode": mode, "intent": intent, "permissions": dict(PERMISSIONS)}
            return self._receipt(mode, "prepare_intent", payload, path, fingerprint, result)

    def _change_control(self, action, payload):
        payload = deepcopy(payload)
        fields = {"mode", "request_id", "reason"} | ({"expected_stop_receipt_id"} if action == "resume" else set())
        _fields(payload, fields, fields)
        mode = payload["mode"]; self._mode(mode)
        if type(payload["reason"]) is not str or not 1 <= len(payload["reason"].strip()) <= 200:
            raise CandidateError("bounded_stop_reason_required")
        request_id = payload["request_id"]
        if type(request_id) is not str or not REQUEST.fullmatch(request_id):
            raise CandidateError("bounded_request_id_required")
        if action == "resume":
            _id(payload["expected_stop_receipt_id"])
        fingerprint = sha256(_json({"action": action, "payload": payload})).hexdigest()
        # Stop bypasses _lock, _records, the resolver, and any worker queue.
        # The DB barrier covers only final local publication by other writers.
        with self._control(mode, write=True) as connection:
            head = self._head(mode, connection)
            if (self._safe(self._mode(mode) / "receipts" / (sha256(request_id.encode()).hexdigest() + ".json"))).exists():
                raise CandidateError("request_id_payload_conflict")
            old = self._control_request(mode, request_id, connection)
            if old is not None:
                if old["request_sha256"] != fingerprint:
                    raise CandidateError("request_id_payload_conflict")
                return self._control_result(old)
            count = head["sequence"] if head else 0
            if count >= MAX_RECORDS or (action == "resume" and count + 1 >= MAX_RECORDS):
                # A resume always leaves one slot for the next durable stop.
                raise CandidateError("candidate_control_capacity_exceeded")
            if action == "resume" and (head is None or head["action"] != "stop"
                    or head["id"] != payload["expected_stop_receipt_id"]):
                raise CandidateError("candidate_latest_stop_confirmation_required")
            result = {"status": "STOPPED" if action == "stop" else "OFFLINE_PREPARATION_RESUMED", "mode": mode,
                "new_intents_blocked": action == "stop", "broker_orders_cancelled": False,
                "message": "已停止准备新意图；未连接券商，也未撤销券商挂单。" if action == "stop" else
                           "仅恢复离线准备；过期配置仍不可使用，未连接券商或恢复任何外部权限。",
                "permissions": dict(PERMISSIONS)}
            if action == "resume":
                result["resumed_stop_receipt_id"] = payload["expected_stop_receipt_id"]
            receipt = _seal({"schema_version": CONTROL_SCHEMA, "kind": "controls", "mode": mode,
                "sequence": count + 1, "previous_control_id": head["id"] if head else None,
                "request_id": request_id, "request_sha256": fingerprint, "action": action,
                "payload": payload, "created_at": self._now().isoformat(), "result": result})
            connection.execute("INSERT INTO controls(sequence,request_id,identity,body) VALUES(?,?,?,?)",
                (receipt["sequence"], request_id, receipt["id"], _json(receipt)))
        return self._control_result(receipt)

    def stop(self, payload):
        return self._change_control("stop", payload)

    def resume(self, payload):
        return self._change_control("resume", payload)

    def receipt(self, mode, request_id):
        self._mode(mode)
        if type(request_id) is not str or not REQUEST.fullmatch(request_id):
            raise CandidateError("bounded_request_id_required")
        with self._control(mode) as connection:
            self._head(mode, connection)
            control = self._control_request(mode, request_id, connection)
        path = self._safe(self._mode(mode) / "receipts" / (sha256(request_id.encode()).hexdigest() + ".json"))
        if control is not None and path.exists():
            raise CandidateError("request_id_payload_conflict")
        record = control or (self._read(path, mode, "receipts") if path.exists() else None)
        return {"status": "FOUND" if record else "NOT_RECORDED", "mode": mode, "request_id": request_id,
                "receipt": deepcopy(record), "read_only": True, "retry_allowed": False,
                "permissions": dict(PERMISSIONS)}

    def receipts(self, mode):
        with self._lock:
            rows = self._records(mode, "receipts")
            with self._control(mode) as connection:
                head = self._head(mode, connection)
                controls = [self._control_row(mode, row) for row in connection.execute(
                    "SELECT sequence,request_id,identity,body FROM controls ORDER BY sequence").fetchall()] if head else []
            previous = None
            for index, row in enumerate(controls):
                if (row["sequence"] != index + 1 or row["previous_control_id"] != (previous["id"] if previous else None)
                        or (row["action"] == "resume" and (previous is None or previous["action"] != "stop"
                            or row["payload"]["expected_stop_receipt_id"] != previous["id"]))):
                    raise CandidateError("candidate_control_history_changed")
                previous = row
            rows += controls
            return {"mode": mode, "items": sorted(rows, key=lambda r: (r["created_at"], r["id"])),
                    "read_only": True, "permissions": dict(PERMISSIONS)}

    def status(self):
        with self._lock:
            modes = []
            for mode in MODES:
                configs = self._records(mode, "configs")
                with self._control(mode) as connection:
                    control = self._control_state(mode, connection)
                modes.append({"mode": mode, "label": "富途官方模拟候选" if mode == "OFFICIAL_SIMULATION" else "实盘候选（未授权）",
                    "state": "STOPPED" if control["new_intents_blocked"] else "NOT_CONFIGURED" if not configs else "OFFLINE_CANDIDATE",
                    "control": control,
                    "configurations": [{"config_id": c["id"], "config": deepcopy(c["config"]),
                        "research_reference": deepcopy(c["research"]["reference"]) if c["research"] else None,
                        "research_binding_sha256": c["research_sha256"], "check": self.check(mode, c["id"], _control_state=control)} for c in configs],
                    "connected": False, "permissions": dict(PERMISSIONS)})
            return {"schema_version": SCHEMA, "modes": modes, "read_only": True, "connection_state": "NOT_CONNECTED",
                "sdk": {"package_metadata": deepcopy(self._sdk), "metadata_status": "VERIFIED_PACKAGE_METADATA" if self._sdk else "NOT_PROVIDED",
                        "official_docs_version": "10.12", "runtime_compatibility": "NOT_VERIFIED", "adapter_installed": False},
                "permissions": dict(PERMISSIONS), "message": "本地合成演练与券商候选相互独立；候选不会自动连接或提交。"}

    def read(self, resource, identity=None):
        if resource == "terminal_broker_status" and identity is None: return self.status()
        if resource == "terminal_broker_receipts": return self.receipts(identity)
        if resource == "terminal_broker_check":
            _fields(identity, {"mode", "config_id"}, {"mode", "config_id"})
            return self.check(identity["mode"], identity["config_id"])
        if resource == "terminal_broker_receipt":
            _fields(identity, {"mode", "request_id"}, {"mode", "request_id"})
            return self.receipt(identity["mode"], identity["request_id"])
        if resource == "terminal_broker_research":
            _fields(identity, {"reference"}, {"reference"})
            return {**self._resolve(identity["reference"]), "read_only": True, "permissions": dict(PERMISSIONS)}
        raise CandidateError("broker_candidate_read_not_found")

    def mutate(self, action, payload):
        handlers = {"terminal_broker_save_candidate": self.save, "terminal_broker_prepare_intent": self.prepare_intent,
                    "terminal_broker_stop": self.stop, "terminal_broker_resume": self.resume}
        if action == "terminal_broker_check_candidate":
            _fields(payload, {"mode", "config_id"}, {"mode", "config_id"})
            return self.check(payload["mode"], payload["config_id"])
        if action not in handlers: raise CandidateError("broker_candidate_action_not_found")
        return handlers[action](payload)
