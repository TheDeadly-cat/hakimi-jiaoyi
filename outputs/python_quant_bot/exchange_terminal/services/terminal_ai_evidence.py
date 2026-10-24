"""Untrusted AI research references: data identity only, never engine inputs."""
from copy import deepcopy
from hashlib import sha256
import json
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


def validate_ai_evidence(value, data):
    """Preserve a bounded client-supplied receipt without authenticating it."""
    fields = {"schema_version", "symbol", "bar", "session", "question", "generated_at",
              "input_identity", "providers"}
    _fields(value, fields, fields)
    if value["schema_version"] != SCHEMA:
        raise ValueError("terminal_ai_evidence_schema_invalid")
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


def ai_evidence_binding(evidence, data):
    """Compare numerical rows only; no source or model authenticity is inferred."""
    rows = [{"ts": int(row["ts_ms"]),
             **{key: float(row[key]) for key in ("open", "high", "low", "close", "volume")}}
            for row in data["rows"]]
    digest = sha256(json.dumps(rows, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
    identity = evidence["input_identity"]
    session = str(data["meta"].get("session") or "UNKNOWN")
    same_scope = _bar(evidence["bar"]) == _bar(data["bar"]) and evidence["session"].lower() == session.lower()
    exact = (same_scope and identity["rows_sha256"] == digest and identity["row_count"] == len(rows)
             and identity["first_ts"] == rows[0]["ts"] and identity["last_ts"] == rows[-1]["ts"])
    return {
        "status": "SAME_NUMERIC_ROWS" if exact else "DIFFERENT_SNAPSHOT",
        "task_input_id": data["id"], "task_rows_sha256": digest,
        "ai_rows_sha256": identity["rows_sha256"], "task_row_count": len(rows),
        "task_session": session, "session_matches": evidence["session"].lower() == session.lower(),
        "source_authenticated": False, "model_receipt_authenticated": False,
        "research_only": True, "parameter_selection_allowed": False, "order_allowed": False,
        "note": "仅作为客户端提供的研究文字依据；数值一致不代表来源或模型回执已认证，不更改策略参数或执行权限。",
    }
