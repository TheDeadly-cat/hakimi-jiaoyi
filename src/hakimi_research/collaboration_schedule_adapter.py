"""Offline, provenance-limited bridge from a Studio result to a schedule input.

The Studio result transports identities and hashes, not source bytes or trading
authority. This adapter never creates an event, changes a task, or runs a model.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any

from .documents import digest, parse_document
from .equity_event_context import SCHEMA_VERSION as EVENT_CONTEXT_VERSION, schedule_view, verify_event_context


RESULT_VERSION = "collaboration_result_v1"
RESULT_SCHEMA_SHA256 = "045303bb4bb5c52a135a6f7de25f29c8dce2f01e1be6dd24945e8685f547bd1c"
RESEARCH_PROFILE_SCHEMA_SHA256 = "b98fb471f5b3b4fc9f03dc0592cc8d36296446561b3f4da212984d97684640a5"
CONFIRMATION_VERSION = "quant-schedule-input-confirmation-v1"
RECEIPT_VERSION = "quant-schedule-input-assessment-v1"
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_UTC = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?Z\Z")
_RESULT_FIELDS = {
    "version", "schema_sha256", "result_id", "invocation_binding", "studio_binding",
    "workflow_kind", "result_profile", "domain_context", "source_manifest",
    "evidence_manifest", "profile", "independent_review", "user_boundary",
    "profile_schema_sha256", "profile_sha256", "safety", "result_sha256",
}
_CONFIRMATION_FIELDS = {
    "version", "decision", "actor", "confirmed_at", "reason", "result_sha256",
    "context_file_sha256", "security_id",
}
_SAFETY = {
    "advisory_only": True,
    "execution_capability": "none",
    "live_trading_allowed": False,
    "betting_allowed": False,
    "external_write_authorized": False,
    "can_autonomously_decide": False,
    "can_replace_user_decision": False,
    "user_final_decision_required": True,
}


def _studio_hash(value: Any) -> str:
    """Studio's UTF-8 canonical hash, distinct from our ASCII-escaped digest."""
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sha(value: Any) -> bool:
    return type(value) is str and _HEX.fullmatch(value) is not None


def _object(value: Any, fields: set[str]) -> bool:
    return type(value) is dict and set(value) == fields


def _utc(value: Any) -> bool:
    if type(value) is not str or _UTC.fullmatch(value) is None:
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return False
    return True


def _result_identity(result: dict) -> list[str]:
    reasons = []
    if not _object(result, _RESULT_FIELDS) or result.get("version") != RESULT_VERSION:
        return ["RESULT_SHAPE_OR_VERSION_INVALID"]
    if result["schema_sha256"] != RESULT_SCHEMA_SHA256 or result["profile_schema_sha256"] != RESEARCH_PROFILE_SCHEMA_SHA256:
        reasons.append("RESULT_SCHEMA_NOT_PINNED")
    if result["workflow_kind"] != "research" or result["result_profile"] != "research_report_v1":
        reasons.append("RESULT_PROFILE_NOT_SCHEDULE_RESEARCH")
    if result["safety"] != _SAFETY:
        reasons.append("RESULT_EXECUTION_SAFETY_INVALID")
    if not _sha(result["result_sha256"]) or not _sha(result["profile_sha256"]):
        reasons.append("RESULT_SHA_SHAPE_INVALID")
    else:
        if _studio_hash(result["profile"]) != result["profile_sha256"]:
            reasons.append("RESULT_PROFILE_HASH_MISMATCH")
        without_sha = {key: value for key, value in result.items() if key != "result_sha256"}
        if _studio_hash(without_sha) != result["result_sha256"]:
            reasons.append("RESULT_HASH_MISMATCH")
        without_identity = {key: value for key, value in without_sha.items() if key != "result_id"}
        if result["result_id"] != "result_" + _studio_hash(without_identity)[:32]:
            reasons.append("RESULT_ID_MISMATCH")
    invocation, domain = result["invocation_binding"], result["domain_context"]
    if type(invocation) is not dict or type(domain) is not dict:
        return reasons + ["RESULT_SOURCE_BINDING_INVALID"]
    if (domain.get("schema_version") != EVENT_CONTEXT_VERSION or not _sha(domain.get("schema_sha256"))
            or not _sha(domain.get("payload_sha256"))):
        reasons.append("DOMAIN_CONTEXT_DECLARATION_INVALID")
    sources = result["source_manifest"]
    if type(sources) is not list:
        return reasons + ["RESULT_SOURCE_BINDING_INVALID"]
    project = [row for row in sources if type(row) is dict and row.get("source_kind") == "project_source"]
    contexts = [row for row in sources if type(row) is dict and row.get("source_kind") == "domain_context"]
    if (len(project) != 1 or len(contexts) != 1
            or project[0].get("record_id") != invocation.get("source_item_id")
            or project[0].get("record_revision") != invocation.get("source_revision")
            or not _sha(project[0].get("record_sha256"))
            or project[0].get("provenance") != "caller_supplied"
            or project[0].get("trust_state") != "hash_bound_only"
            or contexts[0].get("record_revision") != EVENT_CONTEXT_VERSION
            or contexts[0].get("record_sha256") != domain.get("payload_sha256")
            or contexts[0].get("provenance") != "caller_supplied"
            or contexts[0].get("trust_state") != "hash_bound_only"):
        reasons.append("RESULT_SOURCE_BINDING_INVALID")
    review, boundary = result["independent_review"], result["user_boundary"]
    if type(review) is not dict or review.get("status") not in {"not_run", "passed"}:
        reasons.append("RESEARCH_REVIEW_CONCERN_OR_INVALID")
    if type(boundary) is not dict or (boundary.get("status") == "recorded"
                                      and boundary.get("outcome") in {"rejected", "deferred"}):
        reasons.append("RESEARCH_USER_BOUNDARY_REJECTED_OR_INVALID")
    return reasons


def assess_schedule_import(
    result_raw: bytes,
    context_raw: bytes | None,
    confirmation_raw: bytes | None,
    *,
    expected_security_id: str,
) -> dict:
    """Return a sealed assessment; even READY does not bind a task or grant orders.

    The confirmation is a caller-declared human record, not authenticated by this
    pure function. The ordinary input-check and task-version flow remains required.
    """
    reasons: list[str] = []
    result = context = confirmation = None
    result_file_hash = hashlib.sha256(result_raw).hexdigest() if type(result_raw) is bytes else None
    context_file_hash = hashlib.sha256(context_raw).hexdigest() if type(context_raw) is bytes else None
    confirmation_file_hash = hashlib.sha256(confirmation_raw).hexdigest() if type(confirmation_raw) is bytes else None
    if type(expected_security_id) is not str or not expected_security_id.strip() or expected_security_id != expected_security_id.strip():
        reasons.append("EXPECTED_SECURITY_ID_INVALID")
    try:
        result = parse_document(result_raw, maximum_bytes=2 * 1024 * 1024)
        reasons.extend(_result_identity(result))
    except (ValueError, UnicodeDecodeError, TypeError, KeyError, OverflowError):
        reasons.append("RESULT_JSON_INVALID")
    try:
        context = verify_event_context(parse_document(context_raw, maximum_bytes=32 * 1024 * 1024))
        if context["security_id"] != expected_security_id:
            reasons.append("EVENT_SECURITY_MISMATCH")
        if any(event["source"]["kind"] == "SYNTHETIC_FIXTURE" for event in context["events"]):
            reasons.append("SYNTHETIC_EVENT_NOT_ADMISSIBLE")
        if not any(schedule_view(event)["status"] == "ANNOUNCED" and event["availability"]["pit_admissible"]
                   for event in context["events"]):
            reasons.append("NO_PIT_ADMISSIBLE_ANNOUNCED_SCHEDULE")
    except (ValueError, UnicodeDecodeError, TypeError, KeyError, OverflowError):
        reasons.append("EVENT_CONTEXT_INVALID_OR_MISSING")
    if result is not None and context_file_hash and type(result.get("domain_context")) is dict:
        if result["domain_context"].get("payload_sha256") != context_file_hash:
            reasons.append("EVENT_CONTEXT_BYTES_NOT_BOUND_TO_RESULT")
    if confirmation_raw is None:
        reasons.append("MANUAL_CONFIRMATION_REQUIRED")
    else:
        try:
            confirmation = parse_document(confirmation_raw, maximum_bytes=16 * 1024)
            if (not _object(confirmation, _CONFIRMATION_FIELDS)
                    or confirmation["version"] != CONFIRMATION_VERSION
                    or confirmation["decision"] not in {"ACCEPT_FOR_INPUT_CHECK", "REJECT"}
                    or type(confirmation["actor"]) is not str or not confirmation["actor"].strip()
                    or type(confirmation["reason"]) is not str or not confirmation["reason"].strip()
                    or not _utc(confirmation["confirmed_at"])):
                reasons.append("MANUAL_CONFIRMATION_INVALID")
            else:
                if confirmation["decision"] == "REJECT":
                    reasons.append("MANUAL_REJECTION")
                if (result is None or confirmation["result_sha256"] != result.get("result_sha256")
                        or confirmation["context_file_sha256"] != context_file_hash
                        or confirmation["security_id"] != expected_security_id):
                    reasons.append("MANUAL_CONFIRMATION_BINDING_MISMATCH")
        except (ValueError, UnicodeDecodeError, TypeError, KeyError):
            reasons.append("MANUAL_CONFIRMATION_INVALID")
    event_versions = []
    if context is not None:
        event_versions = [{
            "event_id": event["event_id"], "version": event["version"], "event_hash": event["event_hash"],
            "prior_version_hash": event["prior_version_hash"], "source_url": event["source"]["url"],
            "raw_content_sha256": event["raw"]["content_sha256"],
            "first_public_at": event["first_public_at"], "version_public_at": event["version_public_at"],
            "publication_clock_status": event["publication_clock"]["status"],
            "available_at": event["availability"]["available_at"],
            "available_at_kind": event["availability"]["available_at_kind"],
            "pit_admissible": event["availability"]["pit_admissible"],
            "schedule_status": schedule_view(event)["status"],
            "scheduled_date": schedule_view(event)["date"],
            "time_precision": schedule_view(event)["time_precision"],
        } for event in context["events"]]
    body = {
        "schema_version": RECEIPT_VERSION,
        "status": "READY_FOR_EXPLICIT_INPUT_CHECK" if not reasons else "REJECTED",
        "reasons": list(dict.fromkeys(reasons)),
        "research_result_id": result.get("result_id") if result else None,
        "research_result_sha256": result.get("result_sha256") if result else None,
        "research_result_file_sha256": result_file_hash,
        "research_source_item_id": (result.get("invocation_binding") or {}).get("source_item_id") if result and type(result.get("invocation_binding")) is dict else None,
        "research_source_revision": (result.get("invocation_binding") or {}).get("source_revision") if result and type(result.get("invocation_binding")) is dict else None,
        "research_user_boundary": result.get("user_boundary") if result else None,
        "research_independent_review_status": (result.get("independent_review") or {}).get("status") if result and type(result.get("independent_review")) is dict else None,
        "result_validation_scope": "PINNED_IDENTITY_AND_REQUIRED_BINDINGS_ONLY",
        "source_authentication": "NOT_INDEPENDENTLY_VERIFIED",
        "domain_schema_sha256_verified": False,
        "security_id": context.get("security_id") if context else expected_security_id,
        "context_hash": context.get("context_hash") if context else None,
        "context_file_sha256": context_file_hash,
        "event_versions": event_versions,
        "confirmation_file_sha256": confirmation_file_hash,
        "confirmation_declaration": confirmation if confirmation and _object(confirmation, _CONFIRMATION_FIELDS) else None,
        "human_identity_authenticated": False,
        "task_bound": False,
        "parameters_changed": False,
        "new_economic_runs": 0,
        "order_allowed": False,
    }
    return {**body, "assessment_hash": digest(body)}
