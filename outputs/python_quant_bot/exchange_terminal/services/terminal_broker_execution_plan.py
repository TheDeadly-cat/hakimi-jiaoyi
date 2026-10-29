"""Pure, versioned input contract for a future bounded broker acceptance worker.

This module performs no IO and imports no broker SDK. Its inputs must be loaded
by the trusted service: original sealed candidate records, a fresh verified
research resolution, current mode control, and package-loader observations.
Hashes establish exact identity, not provenance by themselves. In particular,
the expected manifest hash and observed file hashes MUST NOT come from a client.

A plan is never authorization, an account check, a broker security mapping, or
an execution receipt. Neither SIMULATE nor REAL becomes executable here. The
future journal/worker must separately admit scoped authorization and evidence,
then atomically enforce the frozen budgets and control-generation barriers.
"""
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
import re

from . import terminal_broker_candidate_service as candidate
from .terminal_saved_results import (RECORDED_SOURCE_SCHEMA, RECORDED_EVIDENCE_SCHEMA,
                                     SOURCE_DIGEST_RULE, _recorded_evidence_decision)


SCHEMA = "hakimi-broker-execution-plan-v1"
RUNTIME_SCHEMA = "hakimi-broker-runtime-identity-v1"
ADAPTER_SCHEMA = "hakimi-broker-adapter-capability-v1"
MODE_CONTRACTS = {
    "OFFICIAL_SIMULATION": ("SIMULATE", "hakimi-futu-us-equity-simulate-v1"),
    "LIVE_CANDIDATE": ("REAL", "hakimi-futu-us-equity-real-v1"),
}
PERMISSIONS = {name: False for name in (
    "external_connection_allowed", "query_allowed", "submit_allowed",
    "cancel_allowed", "unlock_allowed", "automatic_retry", "automatic_resume",
    "automatic_mode_fallback", "user_authorization_granted",
)}
CALL_LIMITS = {"connect": 1, "runtime_read": 1, "account_read": 1, "position_read": 1,
               "security_read": 1, "quote_read": 1, "fee_read": 1,
               "submit": 1, "observe": 5, "cancel": 1, "unlock": 0}
SDK_ROOT = "runtime/python/Lib/site-packages/"
MAX_DOCUMENT_BYTES = 256 * 1024
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
_TOKEN = object()


class PlanError(ValueError):
    """A plan input is incomplete, inconsistent, expired, or outside v1 bounds."""


def _require(condition, message):
    if not condition:
        raise PlanError(message)


def _fields(value, names):
    _require(type(value) is dict and set(value) == set(names), "fields_invalid")


def canonical_bytes(value):
    """ASCII, sorted, compact JSON; booleans and numbers retain distinct types."""
    def check(item, depth=0):
        _require(depth <= 32, "document_depth_exceeded")
        if type(item) is dict:
            _require(all(type(k) is str for k in item), "json_string_keys_required")
            for child in item.values():
                check(child, depth + 1)
        elif type(item) is list:
            for child in item:
                check(child, depth + 1)
        else:
            _require(type(item) in (str, int, float, bool, type(None)), "json_value_invalid")
    check(value)
    try:
        data = json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True,
                          separators=(",", ":")).encode("ascii")
    except (ValueError, OverflowError, UnicodeError) as exc:
        raise PlanError("json_value_invalid") from exc
    _require(len(data) <= MAX_DOCUMENT_BYTES, "document_size_exceeded")
    return data


def digest(value):
    return sha256(canonical_bytes(value)).hexdigest()


def _hash(value, size=64):
    _require(type(value) is str and re.fullmatch(r"[a-f0-9]{%d}" % size, value) is not None,
             "identity_hash_invalid")
    return value


def _text(value, maximum=200):
    _require(type(value) is str and 0 < len(value) <= maximum and value == value.strip()
             and value.isprintable(), "identity_text_invalid")
    return value


def _seal(value):
    return {**value, "id": digest(value)}


def _sealed(value, fields):
    _fields(value, set(fields) | {"id"})
    _require(len(canonical_bytes(value)) <= candidate.MAX_BYTES, "candidate_record_size_exceeded")
    _hash(value["id"])
    _require(value["id"] == digest({k: v for k, v in value.items() if k != "id"}),
             "sealed_identity_mismatch")


def _time(value):
    _text(value, 40)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise PlanError("timestamp_invalid") from exc
    _require(parsed.tzinfo is not None and parsed.utcoffset() is not None,
             "timestamp_timezone_required")
    return parsed.astimezone(timezone.utc)


def _now(value):
    _require(type(value) is datetime and value.tzinfo is not None
             and value.utcoffset() is not None, "trusted_aware_clock_required")
    return value.astimezone(timezone.utc)


def _integer(value, minimum, maximum):
    _require(type(value) is int and minimum <= value <= maximum, "integer_bound_invalid")


def _money(value, *, allow_zero=False):
    _require(type(value) is str and re.fullmatch(r"(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,8})?", value)
             is not None, "decimal_money_string_required")
    amount = Decimal(value)
    _require((amount >= 0 if allow_zero else amount > 0) and amount <= Decimal("1000000000000"),
             "positive_money_bound_required")
    return amount


def _path(value):
    # Package paths are logical POSIX paths, never client filesystem paths.
    _text(value, 400)
    _require(not value.startswith("/") and "\\" not in value and ":" not in value
             and all(part not in ("", ".", "..") and not part.endswith((" ", "."))
                     for part in value.split("/")), "package_relative_path_required")
    return value


def _json_document(data, limit):
    _require(type(data) is bytes and 0 < len(data) <= limit, "bounded_document_bytes_required")
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, "duplicate_json_key")
            result[key] = value
        return result
    try:
        result = json.loads(data, object_pairs_hook=pairs,
                            parse_constant=lambda _: (_ for _ in ()).throw(PlanError("nonfinite_json")))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise PlanError("document_json_invalid") from exc
    _require(type(result) is dict, "document_object_required")
    return result


@dataclass(frozen=True, init=False)
class VerifiedRuntimeIdentity:
    """Immutable loader result, deliberately not a renderer-supplied dictionary."""
    _data: bytes

    def __init__(self, data, token):
        _require(token is _TOKEN, "trusted_runtime_factory_required")
        object.__setattr__(self, "_data", data)

    def as_dict(self):
        return json.loads(self._data)


def verify_runtime_identity(*, manifest_bytes, expected_manifest_sha256,
                            observed_file_sha256, mode, adapter_path=None,
                            adapter_descriptor_bytes=None):
    """Validate package/SDK/adapter identity from a trusted package loader.

    The loader verifies the package independently and supplies hashes of current
    installed bytes. All SDK files in this manifest and every descriptor-declared
    adapter file must match those observations. No files are opened here. SDK
    absence or adapter absence is a truthful capability gap, never a fallback.
    """
    _require(type(mode) is str and mode in MODE_CONTRACTS, "mode_contract_required")
    _hash(expected_manifest_sha256)
    _require(type(manifest_bytes) is bytes and 0 < len(manifest_bytes) <= MAX_MANIFEST_BYTES,
             "bounded_document_bytes_required")
    _require(sha256(manifest_bytes).hexdigest() == expected_manifest_sha256,
             "package_manifest_hash_mismatch")
    manifest = _json_document(manifest_bytes, MAX_MANIFEST_BYTES)
    _require(manifest.get("schema_version") == "hakimi-original-terminal-v1", "package_schema_unsupported")
    _hash(manifest.get("bundle_id")); _text(manifest.get("version"))
    provenance = manifest.get("source_provenance", {})
    _require(type(provenance) is dict and provenance.get("development_probe") is False,
             "production_package_provenance_required")
    source = provenance.get("git", {})
    _require(type(source) is dict and source.get("status") == "CLEAN", "clean_package_source_required")
    _hash(source.get("commit"), 40)
    files = manifest.get("files")
    _require(type(files) is dict and 0 < len(files) <= 50000, "package_file_inventory_required")
    _require(type(observed_file_sha256) is dict and len(observed_file_sha256) <= 50000,
             "loader_observations_required")
    seen_paths = set()
    for path, expected in files.items():
        _path(path); _hash(expected)
        _require(path.casefold() not in seen_paths, "case_aliased_package_path")
        seen_paths.add(path.casefold())

    def observed(path):
        _require(path in files and observed_file_sha256.get(path) == files[path],
                 "installed_file_hash_mismatch:" + path)
        return files[path]

    wheels = manifest.get("dependency_wheels")
    _require(type(wheels) is list and len(wheels) <= 1000 and all(type(row) is dict for row in wheels),
             "package_dependencies_invalid")
    sdk_rows = [row for row in wheels if row.get("name") == "futu-api"]
    _require(len(sdk_rows) <= 1, "ambiguous_sdk_dependency")
    _require(bool(sdk_rows) or not any(path.startswith(SDK_ROOT + "futu/") for path in files),
             "sdk_files_without_dependency_identity")
    sdk = None
    if sdk_rows:
        wheel = sdk_rows[0]
        version = _text(wheel.get("version"), 80)
        _require(re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}", version) is not None, "sdk_version_invalid")
        _hash(wheel.get("sha256")); _text(wheel.get("filename"), 200)
        _require(wheel["filename"] == "futu_api-" + version + "-py3-none-any.whl", "sdk_wheel_identity_mismatch")
        prefixes = (SDK_ROOT + "futu/", SDK_ROOT + "futu_api-" + version + ".dist-info/")
        sdk_files = {path: observed(path) for path in files if path.startswith(prefixes)}
        _require(prefixes[0] + "__init__.py" in sdk_files and prefixes[1] + "METADATA" in sdk_files,
                 "installed_sdk_inventory_incomplete")
        sdk = {"name": "futu-api", "version": version, "wheel_sha256": wheel["sha256"],
               "installed_files_sha256": digest(sdk_files), "installed_file_count": len(sdk_files),
               "runtime_compatibility": "NOT_VERIFIED"}

    adapter = None
    _require((adapter_path is None) == (adapter_descriptor_bytes is None), "adapter_descriptor_pair_required")
    if adapter_path is not None:
        _require(sdk is not None, "adapter_sdk_missing")
        _path(adapter_path)
        _require(type(adapter_descriptor_bytes) is bytes and
                 sha256(adapter_descriptor_bytes).hexdigest() == observed(adapter_path), "adapter_descriptor_hash_mismatch")
        descriptor = _json_document(adapter_descriptor_bytes, MAX_DOCUMENT_BYTES)
        _fields(descriptor, {"schema_version", "adapter_id", "contract_id", "mode", "sdk_environment",
                            "sdk_name", "sdk_version", "market", "asset_class", "currency", "security_mapping",
                            "quantity_policy", "order_type", "time_in_force", "sides", "entrypoint", "source_files"})
        _require(descriptor["schema_version"] == ADAPTER_SCHEMA, "adapter_schema_unsupported")
        _text(descriptor["adapter_id"])
        environment, contract = MODE_CONTRACTS[mode]
        fixed = {"mode": mode, "sdk_environment": environment, "contract_id": contract,
                 "sdk_name": "futu-api", "sdk_version": sdk["version"], "market": "US", "asset_class": "EQUITY",
                 "currency": "USD", "security_mapping": "EXACT_SAVED_US_SYMBOL_V1", "quantity_policy": "WHOLE_SHARES",
                 "order_type": "LIMIT", "time_in_force": "DAY"}
        _require(all(descriptor[k] == v for k, v in fixed.items()), "adapter_mode_or_capability_mismatch")
        _require(type(descriptor["sides"]) is list and descriptor["sides"] in (["BUY"], ["SELL"], ["BUY", "SELL"]),
                 "adapter_sides_invalid")
        _fields(descriptor["entrypoint"], {"path", "function"})
        entry = _path(descriptor["entrypoint"]["path"])
        _require(entry.startswith("components/terminal/exchange_terminal/") and entry.endswith(".py"),
                 "new_application_adapter_entrypoint_required")
        _require(type(descriptor["entrypoint"]["function"]) is str and
                 re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,79}", descriptor["entrypoint"]["function"]) is not None,
                 "adapter_entry_function_invalid")
        source_files = descriptor["source_files"]
        _require(type(source_files) is dict and 0 < len(source_files) <= 100 and entry in source_files,
                 "adapter_sources_required")
        for path, expected in source_files.items():
            _path(path); _hash(expected)
            _require(path.startswith("components/terminal/exchange_terminal/") and expected == observed(path),
                     "adapter_source_identity_mismatch")
        adapter = {"descriptor_path": adapter_path, "descriptor_sha256": observed(adapter_path),
                   "capabilities": descriptor, "runtime_compatibility": "NOT_VERIFIED"}
    value = _seal({"schema_version": RUNTIME_SCHEMA, "mode": mode,
                   "package": {"manifest_sha256": expected_manifest_sha256, "bundle_id": manifest["bundle_id"],
                               "version": manifest["version"], "source_commit": source["commit"]},
                   "sdk": sdk, "adapter": adapter, "permissions": dict(PERMISSIONS)})
    return VerifiedRuntimeIdentity(canonical_bytes(value), _TOKEN)


def _control(value, mode):
    _fields(value, {"mode", "control"})
    _require(value["mode"] == mode, "control_mode_mismatch")
    control = value["control"]
    _fields(control, {"state", "new_intents_blocked", "revision", "latest_control_receipt_id",
                      "latest_stop_receipt_id", "resume_allowed", "permissions"})
    _require(canonical_bytes(control["permissions"]) == canonical_bytes(candidate.PERMISSIONS), "control_permissions_invalid")
    _integer(control["revision"], 0, 1000)
    _require(control["state"] == "OFFLINE_PREPARATION_ALLOWED" and control["new_intents_blocked"] is False
             and control["resume_allowed"] is False, "current_control_blocks_preparation")
    if control["revision"] == 0:
        _require(control["latest_control_receipt_id"] is None and control["latest_stop_receipt_id"] is None,
                 "control_genesis_invalid")
    else:
        _hash(control["latest_control_receipt_id"]); _hash(control["latest_stop_receipt_id"])
        _require(control["revision"] >= 2 and control["latest_control_receipt_id"] != control["latest_stop_receipt_id"],
                 "control_resume_identity_invalid")
    return deepcopy(value)


def _terms(config, now):
    _fields(config, candidate.FIELDS)
    account = config["account_id"]
    _require(type(account) is str and re.fullmatch(r"[1-9][0-9]{0,19}", account) is not None
             and int(account) < 2**64, "explicit_account_string_required")
    _require(config["market"] == "US" and config["asset_class"] == "EQUITY" and config["currency"] == "USD",
             "current_us_equity_contract_required")
    _require(type(config["asset_code"]) is str and re.fullmatch(r"US\.[A-Z][A-Z0-9.-]{0,19}", config["asset_code"])
             is not None, "exact_us_security_required")
    _require(type(config["side"]) is str and config["side"] in ("BUY", "SELL") and config["time_in_force"] == "DAY",
             "explicit_day_limit_side_required")
    _integer(config["quantity"], 1, 1000000); _integer(config["max_quantity"], 1, 1000000)
    notional = _money(config["limit_price"]) * config["quantity"]
    _require(config["quantity"] <= config["max_quantity"] and notional <= _money(config["max_notional"]),
             "candidate_order_limit_exceeded")
    expires = _time(config["expires_at"])
    _require(0 < (expires - now).total_seconds() <= 86400, "candidate_expired_or_unbounded")
    return expires, format(notional, "f")


def _bounds(value, now, expiry):
    _fields(value, {"valid_until", "calls", "wall_timeout_seconds", "call_timeout_seconds", "cleanup_timeout_seconds",
                    "max_output_bytes", "max_observation_records", "max_evidence_age_seconds", "max_total_fees", "endpoint"})
    _fields(value["endpoint"], {"host", "port"})
    _require(value["endpoint"]["host"] == "127.0.0.1", "local_opend_endpoint_required")
    _integer(value["endpoint"]["port"], 1, 65535)
    until = _time(value["valid_until"])
    _require(now < until <= expiry, "plan_expiry_outside_candidate")
    _fields(value["calls"], CALL_LIMITS)
    for action, maximum in CALL_LIMITS.items():
        minimum = 0 if action in ("cancel", "unlock") else 1
        _integer(value["calls"][action], minimum, maximum)
    _integer(value["wall_timeout_seconds"], 1, 180)
    _integer(value["call_timeout_seconds"], 1, min(30, value["wall_timeout_seconds"]))
    _integer(value["cleanup_timeout_seconds"], 1, 5)
    _integer(value["max_output_bytes"], 1, 128 * 1024)
    _integer(value["max_observation_records"], 1, 100)
    _integer(value["max_evidence_age_seconds"], 1, 60)
    # This is an explicit fee ceiling, never an assertion of zero/known actual fees.
    _money(value["max_total_fees"], allow_zero=True)
    _require((until - now).total_seconds() >= value["wall_timeout_seconds"] + value["cleanup_timeout_seconds"],
             "worker_budget_exceeds_remaining_lifetime")
    return deepcopy(value)


def _recorded_research_sidecars(current, resolution):
    binding = current["binding"]
    anchors = {"reference": current["reference"], **{key: binding[key]
               for key in ("task_id", "input_id", "report_hash", "engine_id")}}

    def anchored(record, fields, schema):
        _sealed(record, {"schema_version", *anchors, *fields})
        _require(record["schema_version"] == schema and all(canonical_bytes(record[key]) == canonical_bytes(value)
                 for key, value in anchors.items()), "recorded_research_identity_mismatch")

    if current["reference"]["kind"] == "terminal_run":
        source = resolution.get("recorded_source_identity")
        _require(type(source) is dict, "recorded_native_source_identity_required")
        anchored(source, {"source_files", "fingerprint", "digest_rule", "content_sha256"}, RECORDED_SOURCE_SCHEMA)
        files = source["source_files"]
        _require(type(files) is dict and 0 < len(files) <= 32, "recorded_source_files_required")
        for name, value in files.items():
            _require(type(name) is str and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,79}\.py", name) is not None,
                     "recorded_source_file_name_invalid")
            _hash(value)
        _hash(source["fingerprint"])
        _require(source["digest_rule"] == SOURCE_DIGEST_RULE and source["content_sha256"] == digest(files),
                 "recorded_source_digest_mismatch")
        if "source_hash" in binding:
            _require(binding["source_hash"] == source["content_sha256"], "recorded_source_hash_conflict")
        source = {"kind": "NATIVE_SAVED_SOURCE_MAP", "record": deepcopy(source)}
    else:
        # The core verifier already binds this retained content hash. Do not
        # reinterpret it as a native map or replace it with today's source.
        source = {"kind": "CORE_SAVED_CONTENT_HASH", "content_sha256": _hash(binding.get("source_hash"))}
    classification = resolution.get("recorded_evidence_classification")
    if classification is not None:
        anchored(classification, {"facts", "decision"}, RECORDED_EVIDENCE_SCHEMA)
        facts = classification["facts"]
        _require(type(facts) is list and len(facts) <= 64, "recorded_evidence_facts_invalid")
        for fact in facts:
            _fields(fact, {"path", "value"}); _text(fact["path"], 200)
        decision = _recorded_evidence_decision(facts)
        _require(canonical_bytes(classification["decision"]) == canonical_bytes(decision),
                 "recorded_evidence_decision_mismatch")
    else:
        decision = _recorded_evidence_decision([])
    return source, deepcopy(classification), decision


def prepare_acceptance_plan(*, candidate_config, candidate_intent, research_resolution,
                            runtime_identity, control, bounds, now):
    """Return a sealed offline contract. There is intentionally no authorize/execute API."""
    now = _now(now)
    _sealed(candidate_config, {"schema_version", "kind", "mode", "config", "research", "research_sha256"})
    _sealed(candidate_intent, {"schema_version", "kind", "mode", "config_id", "request_id", "research_sha256",
                               "terms", "security_binding", "status", "permissions"})
    mode = candidate_config["mode"]
    _require(type(mode) is str and mode in MODE_CONTRACTS, "mode_contract_required")
    _require(candidate_config["schema_version"] == candidate.SCHEMA and candidate_config["kind"] == "configs"
             and candidate_intent["schema_version"] == candidate.SCHEMA and candidate_intent["kind"] == "intents",
             "candidate_schema_or_kind_invalid")
    _require(candidate_intent["mode"] == mode and candidate_intent["config_id"] == candidate_config["id"],
             "candidate_intent_identity_mismatch")
    _require(type(candidate_intent["request_id"]) is str and
             re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{7,119}", candidate_intent["request_id"]) is not None,
             "original_intent_request_required")
    _require(candidate_intent["status"] == "UNSENT_OFFLINE_PREVIEW" and
             canonical_bytes(candidate_intent["permissions"]) == canonical_bytes(candidate.PERMISSIONS),
             "unsent_candidate_required")
    terms = candidate_config["config"]
    _require(canonical_bytes(terms) == canonical_bytes(candidate_intent["terms"]), "intent_terms_mismatch")
    expiry, notional = _terms(terms, now)
    saved_research = candidate_config["research"]
    _require(type(saved_research) is dict and "reference" in saved_research, "saved_research_required")
    try:
        current = candidate._project_research(research_resolution, saved_research["reference"])
        security, missing, blockers = candidate._security_binding(terms, current)
    except candidate.CandidateError as exc:
        raise PlanError(str(exc)) from exc
    _require(not missing and not blockers and security["status"] == "MATCHED_SAVED_DECLARATION",
             "saved_security_binding_missing_or_mismatched")
    _require(canonical_bytes(current) == canonical_bytes(saved_research) and
             candidate_config["research_sha256"] == candidate_intent["research_sha256"] == digest(current),
             "verified_research_changed")
    _require(canonical_bytes(security) == canonical_bytes(candidate_intent["security_binding"]),
             "intent_security_declaration_mismatch")
    # Native source maps are a separate opt-in projection. Adding a source_hash
    # to its historical binding would invalidate existing candidate identities.
    source_identity, classification, eligibility = _recorded_research_sidecars(current, research_resolution)
    owner = research_resolution.get("owner_id")
    _text(owner)
    _require((owner.startswith("family:") and re.fullmatch(r"family:[a-f0-9]{32}", owner) is not None)
             or owner == "task:" + current["binding"]["task_id"], "verified_research_owner_required")
    _require(type(runtime_identity) is VerifiedRuntimeIdentity, "trusted_runtime_identity_required")
    runtime = runtime_identity.as_dict()
    _require(runtime["mode"] == mode, "runtime_mode_mismatch")
    frozen_control = _control(control, mode)
    frozen_bounds = _bounds(bounds, now, expiry)
    capability_gaps = []
    if runtime["sdk"] is None:
        capability_gaps.append("SDK_NOT_PACKAGED")
    if runtime["adapter"] is None:
        capability_gaps.append("APPLICATION_ADAPTER_NOT_PACKAGED")
    elif terms["side"] not in runtime["adapter"]["capabilities"]["sides"]:
        raise PlanError("adapter_side_unsupported")
    environment, contract = MODE_CONTRACTS[mode]
    owner_scope = {"mode": mode, "account_id": terms["account_id"],
                   "engine_id": current["binding"]["engine_id"], "owner_id": owner}
    account_scope = {"provider": "FUTU", "mode": mode, "account_id": terms["account_id"]}
    intent_scope = {**account_scope, "candidate_intent_id": candidate_intent["id"]}
    evidence = [
        ("SDK_ADAPTER_COMPATIBILITY", "已安装 SDK 与本应用适配器的离线合同兼容性", "BEFORE_CONNECTION"),
        ("EXPLICIT_SCOPED_AUTHORIZATION", "本计划各外部阶段的独立明确授权", "BEFORE_CONNECTION"),
        ("RESEARCH_EXTERNAL_ADMISSION", "该保存研究输入的独立外部使用资格；合成/QA资料不可升级", "BEFORE_SUBMIT"),
        ("OPEND_PROTOCOL_COMPATIBILITY", "经单独授权连接后读取的实际 OpenD 版本及协议兼容性", "BEFORE_SUBMIT"),
        ("BROKER_ACCOUNT_ENVIRONMENT", "券商实际账户、模式和交易权限", "BEFORE_SUBMIT"),
        ("BROKER_SECURITY_RULES", "实际证券映射、整股/价格步长和交易状态", "BEFORE_SUBMIT"),
        ("FRESH_MARKET_QUOTE", "带来源和时间的有效报价及限价核对", "BEFORE_SUBMIT"),
        ("BROKER_FEES", "费用规则、币种和有界费用估计，缺失不能补零", "BEFORE_SUBMIT"),
        ("SHARED_ACCOUNT_RESERVATIONS", "同账户未完成意图占用与去重，不能复用额度", "BEFORE_SUBMIT"),
        ("BROKER_CASH" if terms["side"] == "BUY" else "BROKER_OWNER_HOLDINGS",
         "实际可用资金及费用占用" if terms["side"] == "BUY" else "归属本研究策略的实际可卖持仓及已占用数量",
         "BEFORE_SUBMIT"),
    ]
    if mode == "LIVE_CANDIDATE":
        evidence.append(("REAL_FUNDS_AUTHORIZATION", "真实资金与指定 REAL 账户的单独授权，模拟许可不可替代", "BEFORE_CONNECTION"))
        evidence.append(("REAL_ACCOUNT_UNLOCK_STATE", "实际账户解锁与交易许可状态；此计划不执行解锁", "BEFORE_SUBMIT"))
    call_actions = [action for action, count in frozen_bounds["calls"].items() if count]
    return _seal({
        "schema_version": SCHEMA, "status": "BLOCKED_CAPABILITY" if capability_gaps else
        "OFFLINE_ONLY_SYNTHETIC_RESEARCH" if eligibility["offline_only"] else "OFFLINE_PLAN_REQUIRES_EVIDENCE",
        "created_at": now.isoformat(), "mode": mode, "sdk_environment": environment, "contract_id": contract,
        "candidate_config": deepcopy(candidate_config), "candidate_intent": deepcopy(candidate_intent),
        "research": {"resolution": current, "owner": owner_scope, "owner_scope_id": digest(owner_scope),
                     "recorded_source": source_identity, "recorded_classification": classification},
        "research_eligibility": eligibility,
        "runtime": runtime, "control": frozen_control, "bounds": frozen_bounds,
        "deduplication": {"account_scope_id": digest(account_scope), "intent_scope_id": digest(intent_scope),
                          "scope": "ORIGINAL_INTENT_ACROSS_ALL_PLANS_AND_RESTARTS",
                          "new_plan_must_not_reset_submit_claim": True},
        "order": {**deepcopy(terms), "order_type": "LIMIT", "security_id": current["display"]["security_id"],
                  "order_notional": notional, "notional_excludes_fees": True,
                  "maximum_cash_debit": format(Decimal(notional) + Decimal(bounds["max_total_fees"]), "f")
                  if terms["side"] == "BUY" else None, "actual_fees": None},
        "capability_gaps": capability_gaps,
        "missing_evidence": [{"code": code, "description": description, "required_before": barrier,
                              "status": "NOT_PROVIDED", "evidence_ref": None} for code, description, barrier in evidence],
        "worker_contract": {"allowed_actions": call_actions, "counts_scope": "ENTIRE_PLAN_ACROSS_WORKERS_AND_RESTARTS",
                            "submit_claim_scope": "ORIGINAL_INTENT_ACROSS_ALL_PLANS_AND_RESTARTS",
                            "deadline_scope": "PLAN_AND_WORKER_WALL_CLOCK", "outputs_scope": "ALL_WORKER_OUTPUT_AND_RAW_EVIDENCE_BYTES",
                            "barriers": ["BEFORE_CONNECTION", "BEFORE_CLAIM", "BEFORE_SUBMIT", "BEFORE_CANCEL"],
                            "control_revision_must_equal": frozen_control["control"]["revision"],
                            "mode_fallback": False, "short_selling": False,
                            "cancel_requires_exact_own_broker_order": True,
                            "authorization_required_for_every_external_action": True},
        "recovery_contract": {"unknown": "QUERY_ORIGINAL_ID_ONLY", "not_found": "NOT_PROOF_OF_UNSENT",
                              "resubmit": False, "restart": "RECONCILE_THEN_EXPLICIT_RESUME",
                              "fills": "CUMULATIVE_PER_ORIGINAL_ORDER_NO_DOUBLE_COUNT",
                              "cancel_ack": "NOT_A_TERMINAL_CANCELLATION", "stop": "BLOCK_NEW_CALLS_NOT_CANCEL_IN_FLIGHT",
                              "new_journal_required": True, "legacy_profile_or_journal_reuse": False},
        "permissions": dict(PERMISSIONS),
    })


def validate_acceptance_plan(plan, *, candidate_config, candidate_intent, research_resolution,
                             runtime_identity, control, now):
    """Recheck exact inputs before future journal use; this grants no permission.

    A sealed plan is immutable. Stop/resume, source, account, research, bounds or
    capability changes require a new explicit plan. A successful return is still
    OFFLINE and cannot replace atomic claim/dispatch barriers in the worker.
    """
    _require(type(plan) is dict and plan.get("schema_version") == SCHEMA, "plan_schema_invalid")
    expected = prepare_acceptance_plan(candidate_config=candidate_config, candidate_intent=candidate_intent,
                                       research_resolution=research_resolution, runtime_identity=runtime_identity,
                                       control=control, bounds=plan.get("bounds"), now=_time(plan.get("created_at")))
    _require(canonical_bytes(plan) == canonical_bytes(expected), "plan_or_current_identity_changed")
    current_time = _now(now)
    _require(current_time >= _time(plan["created_at"]), "clock_before_plan")
    _bounds(plan["bounds"], current_time, _time(plan["order"]["expires_at"]))
    return {"plan_id": plan["id"], "status": plan["status"], "identity_matches": True,
            "journal_key": "broker-execution-v1/" + candidate.MODES[plan["mode"]] + "/" + plan["id"],
            "permissions": dict(PERMISSIONS)}
