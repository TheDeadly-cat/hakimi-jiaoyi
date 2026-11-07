"""Untrusted AI references: explicit data/rule identity, never engine inputs."""
from copy import deepcopy
from hashlib import sha256
import json
import math
import re


SCHEMA = "hakimi-ai-research-evidence-v1"


def _fields(value, allowed, required):
    if type(value) is not dict or set(value) - set(allowed) or set(required) - set(value):
        raise ValueError("terminal_ai_evidence_fields_invalid")


def _text(value, limit, *, empty=False):
    if type(value) is not str or len(value) > limit or (not empty and not value.strip()) or "\x00" in value:
        raise ValueError("terminal_ai_evidence_text_invalid")
    return value


def _integer(value, minimum=1):
    if type(value) is not int or not minimum <= value <= 8640000000000000:
        raise ValueError("terminal_ai_evidence_integer_invalid")
    return value


def _bar(value):
    text = str(value).strip().lower()
    return "1d" if text in {"1d", "1dutc", "day", "daily"} else text


def _strategy_context(value):
    """Validate recorded fields without inventing missing legacy identity."""
    _fields(value, {"engine_id", "strategy_id", "strategy_params"}, set())
    for field in ("engine_id", "strategy_id"):
        if field in value:
            _text(value[field], 150 if field == "engine_id" else 80)
    if "strategy_params" in value:
        params = value["strategy_params"]
        if type(params) is not dict or len(params) > 40:
            raise ValueError("terminal_ai_evidence_strategy_params_invalid")
        for key, item in params.items():
            if type(key) is not str or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", key):
                raise ValueError("terminal_ai_evidence_strategy_params_invalid")
            if type(item) is str:
                _text(item, 100)
            elif type(item) is bool:
                pass
            elif type(item) not in (int, float) or abs(item) > 9007199254740991 or not math.isfinite(item):
                raise ValueError("terminal_ai_evidence_strategy_params_invalid")
    return deepcopy(value)


def compare_ai_strategy(evidence, strategy_id=None, strategy_params=None, engine_id=None):
    """Compare explicit recorded values; absent fields are unknown, not defaults."""
    analysis = _strategy_context(evidence["strategy_context"]) if "strategy_context" in evidence else None
    task = _strategy_context({key: value for key, value in {
        "engine_id": engine_id, "strategy_id": strategy_id, "strategy_params": strategy_params,
    }.items() if value is not None})
    missing, differences = [], []
    comparisons = {}
    for field in ("engine_id", "strategy_id", "strategy_params"):
        for label, context in (("analysis", analysis), ("task", task)):
            if context is None or field not in context:
                missing.append(label + "." + field)
        if analysis is None or field not in analysis or field not in task:
            comparisons[field] = None
        elif field != "strategy_params":
            comparisons[field] = analysis[field] == task[field]
        else:
            left, right = analysis[field], task[field]
            incomplete = False
            for key in sorted(set(left) | set(right)):
                if key not in left or key not in right:
                    missing.append(("analysis" if key not in left else "task") + ".strategy_params." + key)
                    incomplete = True
                elif (type(left[key]) is bool) != (type(right[key]) is bool) or left[key] != right[key]:
                    differences.append(key)
            comparisons[field] = False if differences else None if incomplete else True
    status = "MISMATCH" if False in comparisons.values() else "UNKNOWN" if missing else "MATCH"
    return {"status": status, "analysis_context": analysis, "task_context": task,
            "engine_matches": comparisons["engine_id"], "strategy_matches": comparisons["strategy_id"],
            "parameters_match": comparisons["strategy_params"], "differing_parameters": differences,
            "missing_fields": missing}


def validate_ai_evidence(value, data):
    """Preserve a bounded client-supplied receipt without authenticating it."""
    fields = {"schema_version", "symbol", "bar", "session", "question", "generated_at",
              "input_identity", "providers"}
    _fields(value, fields | {"strategy_context"}, fields)
    if value["schema_version"] != SCHEMA:
        raise ValueError("terminal_ai_evidence_schema_invalid")
    if "strategy_context" in value:
        _strategy_context(value["strategy_context"])
    symbol = _text(value["symbol"], 40)
    if symbol != data["symbol"]:
        raise ValueError("terminal_ai_evidence_symbol_mismatch")
    if _bar(_text(value["bar"], 20)) != "1d" or _bar(data["bar"]) != "1d":
        raise ValueError("terminal_ai_evidence_requires_daily_context")
    _text(value["session"], 40)
    _text(value["question"], 900, empty=True)
    _integer(value["generated_at"])
    identity = value["input_identity"]
    identity_fields = {"rows_sha256", "row_count", "first_ts", "last_ts", "source", "price_basis", "snapshot_id"}
    _fields(identity, identity_fields, identity_fields - {"snapshot_id"})
    if type(identity["rows_sha256"]) is not str or not re.fullmatch(r"[0-9a-f]{64}", identity["rows_sha256"]):
        raise ValueError("terminal_ai_evidence_digest_invalid")
    count = _integer(identity["row_count"])
    if not 30 <= count <= 300:
        raise ValueError("terminal_ai_evidence_row_count_invalid")
    if _integer(identity["first_ts"]) > _integer(identity["last_ts"]):
        raise ValueError("terminal_ai_evidence_time_range_invalid")
    _text(identity["source"], 200)
    _text(identity["price_basis"], 100)
    if identity.get("snapshot_id") is not None:
        _text(identity["snapshot_id"], 160, empty=True)
    providers = value["providers"]
    if type(providers) is not list or not 1 <= len(providers) <= 2:
        raise ValueError("terminal_ai_evidence_providers_invalid")
    seen = set()
    for provider in providers:
        _fields(provider, {"provider", "model", "content", "summary"}, {"provider", "model", "content"})
        name = provider["provider"]
        if type(name) is not str or name not in {"deepseek", "openai"} or name in seen:
            raise ValueError("terminal_ai_evidence_provider_invalid")
        seen.add(name)
        _text(provider["model"], 120)
        _text(provider["content"], 16000)
        if "summary" in provider:
            _text(provider["summary"], 2000, empty=True)
    return deepcopy(value)


def ai_evidence_binding(evidence, data, strategy_id=None, strategy_params=None, engine_id=None):
    """Keep numerical data, explicit rule match and provenance as separate facts."""
    rows = [{"ts": int(row["ts_ms"]),
             **{key: float(row[key]) for key in ("open", "high", "low", "close", "volume")}}
            for row in data["rows"]]
    digest = sha256(json.dumps(rows, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
    identity = evidence["input_identity"]
    session = str(data["meta"].get("session") or "UNKNOWN")
    same_scope = (evidence["symbol"] == data["symbol"] and _bar(evidence["bar"]) == _bar(data["bar"])
                  and evidence["session"].lower() == session.lower())
    exact = (same_scope and identity["rows_sha256"] == digest and identity["row_count"] == len(rows)
             and identity["first_ts"] == rows[0]["ts"] and identity["last_ts"] == rows[-1]["ts"])
    return {
        "status": "SAME_NUMERIC_ROWS" if exact else "DIFFERENT_SNAPSHOT",
        "task_input_id": data["id"], "task_rows_sha256": digest,
        "ai_rows_sha256": identity["rows_sha256"], "task_row_count": len(rows),
        "task_session": session, "session_matches": evidence["session"].lower() == session.lower(),
        "strategy_binding": compare_ai_strategy(evidence, strategy_id, strategy_params, engine_id),
        "source_authenticated": False, "model_receipt_authenticated": False,
        "research_only": True, "parameter_selection_allowed": False, "order_allowed": False,
        "note": "仅作为客户端提供的研究文字依据；数值一致不代表来源或模型回执已认证，不更改策略参数或执行权限。",
    }
