"""Unregistered HTTP candidate for the exact membership presentation-v11.

This module is deliberately not mounted by any HTTP server.  It projects only
bounded aggregate facts from a verified presentation-v11 document and keeps
current, paper, and live authority permanently false.
"""

from __future__ import annotations

import copy
import math
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_v11
    as _presentation_v11,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


REQUEST_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-edge-"
    "uncertainty-common-observation-membership-presentation-http-candidate-request-v11"
)
RESPONSE_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-edge-"
    "uncertainty-common-observation-membership-presentation-http-candidate-response-v11"
)
PAYLOAD_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-edge-"
    "uncertainty-common-observation-membership-presentation-http-payload-v11"
)
PRESENTATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-edge-"
    "uncertainty-common-observation-membership-presentation-v11"
)
PRESENTATION_VERIFICATION_SCHEMA_VERSION = f"{PRESENTATION_SCHEMA_VERSION}-verification-v1"
PRESENTATION_STATIC_FINGERPRINT = (
    "20260823-stratified-multi-window-edge-uncertainty-common-observation-"
    "membership-presentation-v11-unmounted-lock-1"
)
STATIC_CONTRACT_VERSION = (
    "20260823-stratified-multi-window-edge-uncertainty-common-observation-"
    "membership-presentation-http-candidate-v11-unmounted-lock-4"
)
PRESENTATION_V11_IMPLEMENTATION_HASH = (
    "09f2b57264f84bcd9db26e9cf8a2d3bc0baf8ddfc1f2e66a28f101dbbe666d3f"
)
STRICT_CANONICAL_IMPLEMENTATION_HASH = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)

INTERFACE_STATE = "UNREGISTERED_CANDIDATE"
KNOWN_STATE = "KNOWN_BLOCKED"
UNKNOWN_STATE = "UNKNOWN"
LOCKED_AUTHORITY = {
    "current_admission_allowed": False,
    "current_pointer_written": False,
    "formal_registry_activation_allowed": False,
    "http_route_registration_allowed": False,
    "live_order_allowed": False,
    "paper_authorized": False,
    "presentation_consumer_activation_allowed": False,
    "runtime_gate_activation_allowed": False,
    "ui_mount_allowed": False,
    "writer_allowed": False,
}
_SOURCE_LOCKED_AUTHORITY = {
    "current_admission_allowed": False,
    "current_pointer_written": False,
    "descriptive_only": True,
    "formal_registry_activation_allowed": False,
    "http_candidate_creation_allowed": False,
    "live_order_allowed": False,
    "paper_authorized": False,
    "presentation_consumer_activation_allowed": False,
    "presentation_only": True,
    "research_only": True,
    "runtime_gate_activation_allowed": False,
    "writer_allowed": False,
}
BASE_BLOCKERS = (
    "HTTP_CANDIDATE_V11_UNREGISTERED",
    "PRESENTATION_V11_CONSUMER_NOT_REGISTERED",
    "CURRENT_ADMISSION_LOCKED",
    "UI_NOT_MOUNTED",
)
PRESENTATION_GOVERNANCE_BLOCKERS = (
    "PRESENTATION_V11_CONSUMER_NOT_REGISTERED",
    "HTTP_CANDIDATE_V11_NOT_DEFINED",
    "UI_NOT_MOUNTED",
    "CURRENT_ADMISSION_LOCKED",
)
UNKNOWN_BLOCKER = "PRESENTATION_V11_UNKNOWN"

_REQUEST_KEYS = {
    "schema_version",
    "expected_presentation_v11_hash",
    "stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_v11_document",
}
_CONTEXT_KEYS = {
    "presentation_v10_document",
    "adapter_v10_document",
    "presentation_v10_verification_context",
    "adapter_v10_verification_context",
}
_RECEIPT_KEYS = {
    "blockers",
    "current_admission_allowed",
    "live_order_allowed",
    "paper_authorized",
    "presentation_consumer_activation_allowed",
    "presentation_v11_exactly_verified",
    "presentation_v11_hash",
    "runtime_gate_activation_allowed",
    "schema_version",
    "status",
    "writer_allowed",
}
_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_SENSITIVE_KEY_FRAGMENTS = (
    "raw_",
    "observation_id",
    "sample",
    "price",
    "return_series",
    "timestamp",
    "ticker",
    "symbol",
    "asset_id",
    "pair_commitment",
    "member_ids",
    "document",
    "context",
    "receipt",
)
_SENSITIVE_EXACT_KEYS = {"members"}
_SAFE_TEXT_KEY_FRAGMENTS = (
    "status",
    "decision",
    "state",
    "mode",
    "method",
    "basis",
    "window",
    "tier",
    "reason",
    "field",
    "source",
    "gap",
    "axis",
    "detail",
)
_SUMMARY_ALIASES = {
    "risk": ("portfolio_risk_summary", "risk_budget_summary", "risk_summary"),
    "multi_window": ("multi_window_summary", "multi_window_risk_summary"),
    "edge_uncertainty": ("edge_uncertainty_summary", "edge_summary"),
    "common_observation": (
        "common_observation_summary",
        "common_observation_basis_summary",
    ),
    "membership": (
        "common_observation_membership_summary",
        "membership_summary",
    ),
}
_SUMMARY_TOKENS = {
    "risk": ("risk", "summary"),
    "multi_window": ("multi", "window", "summary"),
    "edge_uncertainty": ("edge", "uncertainty", "summary"),
    "common_observation": ("common", "observation", "summary"),
    "membership": ("membership", "summary"),
}

_VERIFY_PRESENTATION = getattr(
    _presentation_v11,
    "verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_"
    "edge_uncertainty_common_observation_membership_presentation_v11",
)


def _is_plain_mapping(value: Any) -> bool:
    return type(value) is dict


def _sealed(value: dict[str, Any]) -> dict[str, Any]:
    return seal_strict_canonical_document(copy.deepcopy(value), "source_hash")


def _canonical_number(value: float) -> str | None:
    if not math.isfinite(value):
        return None
    try:
        decimal = Decimal(str(value))
    except InvalidOperation:
        return None
    rendered = format(decimal, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return "0" if rendered in {"-0", ""} else rendered


def _sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return lowered in _SENSITIVE_EXACT_KEYS or any(
        fragment in lowered for fragment in _SENSITIVE_KEY_FRAGMENTS
    )


def _bounded_aggregate(value: Any, *, key: str = "", depth: int = 0) -> Any:
    """Return a deterministic aggregate-only projection with strict bounds."""
    if depth > 4 or _sensitive_key(key):
        return None
    if value is None or isinstance(value, bool) or type(value) is int:
        return value
    if type(value) is float:
        return _canonical_number(value)
    if isinstance(value, str):
        if len(value) > 128:
            return None
        lowered = key.lower()
        if any(fragment in lowered for fragment in _SAFE_TEXT_KEY_FRAGMENTS):
            return value
        return None
    if _is_plain_mapping(value):
        result: dict[str, Any] = {}
        for child_key in sorted(value)[:32]:
            if not isinstance(child_key, str):
                continue
            child = _bounded_aggregate(value[child_key], key=child_key, depth=depth + 1)
            if child is not None:
                result[child_key] = child
        return result
    if isinstance(value, (list, tuple)) and len(value) <= 16:
        items = [
            _bounded_aggregate(item, key=key, depth=depth + 1)
            for item in value
            if item is None or isinstance(item, (bool, int, float))
        ]
        return [item for item in items if item is not None]
    return None


def _walk_named_mappings(root: Mapping[str, Any]) -> list[tuple[str, Mapping[str, Any]]]:
    queue: list[tuple[int, Mapping[str, Any]]] = [(0, root)]
    found: list[tuple[str, Mapping[str, Any]]] = []
    visited = 0
    while queue and visited < 256:
        depth, current = queue.pop(0)
        visited += 1
        for key, value in current.items():
            if isinstance(key, str) and _is_plain_mapping(value):
                found.append((key, value))
                if depth < 3 and not _sensitive_key(key):
                    queue.append((depth + 1, value))
    return found


def _find_summary(
    document: Mapping[str, Any],
    name: str,
) -> Mapping[str, Any] | None:
    aliases = _SUMMARY_ALIASES[name]
    candidates = _walk_named_mappings(document)
    for key, value in candidates:
        if key in aliases:
            return value
    tokens = _SUMMARY_TOKENS[name]
    for key, value in candidates:
        lowered = key.lower()
        if all(token in lowered for token in tokens):
            if name == "common_observation" and "membership" in lowered:
                continue
            return value
    return None


def _all_summaries(document: Mapping[str, Any]) -> dict[str, Mapping[str, Any]] | None:
    summaries: dict[str, Mapping[str, Any]] = {}
    for name in _SUMMARY_ALIASES:
        summary = _find_summary(document, name)
        if summary is None:
            return None
        summaries[name] = summary
    return summaries


def _has_true_authority(value: Any, *, depth: int = 0) -> bool:
    if depth > 6:
        return True
    if _is_plain_mapping(value):
        for key, item in value.items():
            if not isinstance(key, str):
                return True
            lowered = key.lower()
            protected = (
                lowered.endswith("_authorized")
                or lowered.endswith("_allowed")
                or lowered.endswith("_registered")
                or lowered.endswith("_written")
                or lowered.endswith("_mounted")
                or lowered in {"runtime_mutations", "writer_side_effects"}
            )
            if protected and item is not False:
                return True
            if _has_true_authority(item, depth=depth + 1):
                return True
        return False
    if isinstance(value, (list, tuple)):
        return any(_has_true_authority(item, depth=depth + 1) for item in value)
    return False


def _valid_presentation_document(document: Any, expected_hash: Any) -> bool:
    if not _is_plain_mapping(document) or not isinstance(expected_hash, str):
        return False
    if not _HASH_PATTERN.fullmatch(expected_hash):
        return False
    if document.get("schema_version") != PRESENTATION_SCHEMA_VERSION:
        return False
    if document.get("presentation_v11_hash") != expected_hash:
        return False
    if document.get("status") != "BLOCK":
        return False
    if document.get("static_fingerprint") != PRESENTATION_STATIC_FINGERPRINT:
        return False
    authority = document.get("authority")
    if not _is_plain_mapping(authority) or set(authority) != set(_SOURCE_LOCKED_AUTHORITY):
        return False
    for key, expected in _SOURCE_LOCKED_AUTHORITY.items():
        if authority.get(key) is not expected:
            return False
    if _has_true_authority(document):
        return False
    if not _is_plain_mapping(document.get("facts")):
        return False
    gaps = document.get("gaps")
    if not _is_plain_mapping(gaps):
        return False
    if gaps.get("presentation_blocker_count") != len(PRESENTATION_GOVERNANCE_BLOCKERS):
        return False
    if gaps.get("presentation_blockers") != list(PRESENTATION_GOVERNANCE_BLOCKERS):
        return False
    stages = document.get("stages")
    if not isinstance(stages, list) or len(stages) != 4:
        return False
    if any(not _is_plain_mapping(stage) for stage in stages):
        return False
    if [stage.get("axis") for stage in stages] != ["SOURCE", "GAP", "MATURITY", "PERMISSION"]:
        return False
    if "local_decision" not in document:
        return False
    return _all_summaries(document) is not None


def _valid_request(request_payload: Any) -> bool:
    return (
        _is_plain_mapping(request_payload)
        and set(request_payload) == _REQUEST_KEYS
        and request_payload.get("schema_version") == REQUEST_SCHEMA_VERSION
    )


def _valid_context(context: Any) -> bool:
    return (
        _is_plain_mapping(context)
        and set(context) == _CONTEXT_KEYS
        and all(_is_plain_mapping(context[key]) for key in _CONTEXT_KEYS)
    )


def _valid_receipt(receipt: Any, expected_hash: str) -> bool:
    return (
        _is_plain_mapping(receipt)
        and set(receipt) == _RECEIPT_KEYS
        and receipt.get("schema_version") == PRESENTATION_VERIFICATION_SCHEMA_VERSION
        and receipt.get("status") == "PASS"
        and receipt.get("blockers") == []
        and receipt.get("presentation_v11_exactly_verified") is True
        and receipt.get("presentation_v11_hash") == expected_hash
        and receipt.get("presentation_consumer_activation_allowed") is False
        and receipt.get("current_admission_allowed") is False
        and receipt.get("paper_authorized") is False
        and receipt.get("live_order_allowed") is False
        and receipt.get("runtime_gate_activation_allowed") is False
        and receipt.get("writer_allowed") is False
    )


def _sanitized_gaps(
    document: Mapping[str, Any], current_blockers: list[str]
) -> dict[str, Any]:
    gaps = document.get("gaps")
    if not _is_plain_mapping(gaps):
        return {}
    projected = _bounded_aggregate(gaps, key="gaps")
    if not _is_plain_mapping(projected):
        return {}
    projected["presentation_blockers"] = list(PRESENTATION_GOVERNANCE_BLOCKERS)
    return {
        "source_snapshot": {
            "schema_version": PRESENTATION_SCHEMA_VERSION,
            "static_fingerprint": PRESENTATION_STATIC_FINGERPRINT,
            "presentation_v11_hash": document["presentation_v11_hash"],
            "gaps": projected,
        },
        "candidate_current": {
            "static_contract_version": STATIC_CONTRACT_VERSION,
            "interface": INTERFACE_STATE,
            "state": KNOWN_STATE,
            "blocker_count": len(current_blockers),
            "blockers": list(current_blockers),
        },
        "interpretation": "SOURCE_SNAPSHOT_IS_NOT_CURRENT_CANDIDATE_STATE",
    }


def _source_hashes(document: Mapping[str, Any], expected_hash: str) -> dict[str, str]:
    result = {
        "presentation_v11_hash": expected_hash,
        "presentation_v11_implementation_hash": PRESENTATION_V11_IMPLEMENTATION_HASH,
        "strict_canonical_implementation_hash": STRICT_CANONICAL_IMPLEMENTATION_HASH,
    }
    source = document.get("source")
    if not _is_plain_mapping(source):
        return result
    allowed_tokens = (
        "presentation_v10",
        "adapter_v10",
        "membership_gate_v2",
        "preregistration",
        "evidence",
        "scheme",
        "strict_canonical",
    )
    for key in sorted(source):
        value = source[key]
        if (
            isinstance(key, str)
            and (key.endswith("_hash") or key.endswith("_sha256"))
            and any(token in key for token in allowed_tokens)
            and isinstance(value, str)
            and _HASH_PATTERN.fullmatch(value)
        ):
            result[key] = value
    return result


def _summary_is_blocked(summary: Mapping[str, Any]) -> bool:
    queue: list[Any] = [summary]
    visited = 0
    while queue and visited < 128:
        current = queue.pop(0)
        visited += 1
        if _is_plain_mapping(current):
            for key, value in current.items():
                if isinstance(key, str) and "status" in key.lower() and value == "BLOCK":
                    return True
                if _is_plain_mapping(value) or isinstance(value, (list, tuple)):
                    queue.append(value)
        elif isinstance(current, (list, tuple)):
            queue.extend(current[:32])
    return False


def _known_payload(
    document: Mapping[str, Any],
    expected_hash: str,
    summaries: Mapping[str, Mapping[str, Any]],
    current_blockers: list[str],
) -> dict[str, Any]:
    projected_summaries = {
        name: _bounded_aggregate(summary, key=f"{name}_summary") or {}
        for name, summary in summaries.items()
    }
    source_stages = document["stages"]
    source_stage_document = next(
        (stage for stage in source_stages if stage.get("axis") == "SOURCE"), {}
    )
    gap_stage_document = next(
        (stage for stage in source_stages if stage.get("axis") == "GAP"), {}
    )
    source_stage = _bounded_aggregate(source_stage_document, key="source") or {}
    gap_stage = _bounded_aggregate(gap_stage_document, key="gap") or {}
    source_facts = _bounded_aggregate(document["facts"], key="facts") or {}
    facts = dict(source_facts) if _is_plain_mapping(source_facts) else {}
    facts.update(
        {
            "presentation_v11_exact": True,
            "membership_commitment_only": True,
            "raw_observation_identifiers_exposed": False,
            "raw_observation_ids_embedded": False,
            "raw_observation_samples_recomputed": False,
            "raw_samples_recomputed": False,
            "http_candidate_registered": False,
            "gap_scopes_explicit": True,
            "source_gap_snapshot_current": False,
            "ui_mounted": False,
        }
    )
    payload = {
        "schema_version": PAYLOAD_SCHEMA_VERSION,
        "decision": "EXACT_PRESENTATION_V11_PROJECTED_AUTHORITY_UNCHANGED",
        "status": "BLOCK",
        "authority": copy.deepcopy(LOCKED_AUTHORITY),
        "aggregate_summaries": projected_summaries,
        "local_decision": _bounded_aggregate(
            document["local_decision"], key="local_decision"
        ),
        "source_hashes": _source_hashes(document, expected_hash),
        "facts": facts,
        "gaps": _sanitized_gaps(document, current_blockers),
        "stages": {
            "source": source_stage,
            "gap": {
                "source_snapshot": gap_stage,
                "candidate_current": {
                    "state": "UNREGISTERED_CANDIDATE",
                    "status": "BLOCK",
                },
            },
            "maturity": {
                "state": "UNMOUNTED_HTTP_CANDIDATE_V11",
                "status": "CANDIDATE_ONLY",
            },
            "permission": {
                "state": "NO_ROUTE_MOUNT_CURRENT_PAPER_OR_LIVE_AUTHORITY",
                "status": "UNAUTHORIZED",
            },
        },
    }
    return _sealed(payload)


def _response(
    *,
    state: str,
    expected_hash: str | None,
    payload: Mapping[str, Any] | None,
    blockers: list[str],
    source_static_contract_version: str | None,
) -> dict[str, Any]:
    response = {
        "schema_version": RESPONSE_SCHEMA_VERSION,
        "static_contract_version": STATIC_CONTRACT_VERSION,
        "status": "BLOCK" if state == KNOWN_STATE else "UNKNOWN",
        "state": state,
        "interface": INTERFACE_STATE,
        "authority": copy.deepcopy(LOCKED_AUTHORITY),
        "blockers": blockers,
        "lineage": {
            "presentation_v11_schema_version": PRESENTATION_SCHEMA_VERSION,
            "presentation_v11_static_fingerprint": source_static_contract_version,
            "presentation_v11_hash": expected_hash,
            "presentation_v11_implementation_hash": PRESENTATION_V11_IMPLEMENTATION_HASH,
            "strict_canonical_implementation_hash": STRICT_CANONICAL_IMPLEMENTATION_HASH,
        },
        "payload": copy.deepcopy(payload),
    }
    return _sealed(response)


def _unknown_response(expected_hash: Any = None) -> dict[str, Any]:
    safe_hash = expected_hash if isinstance(expected_hash, str) and _HASH_PATTERN.fullmatch(expected_hash) else None
    return _response(
        state=UNKNOWN_STATE,
        expected_hash=safe_hash,
        payload=None,
        blockers=[*BASE_BLOCKERS, UNKNOWN_BLOCKER],
        source_static_contract_version=None,
    )


def build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_http_candidate_response_v11(
    request_payload: Mapping[str, Any],
    *,
    presentation_verification_context: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a fail-closed, unregistered candidate response."""
    request_copy = copy.deepcopy(request_payload)
    context_copy = copy.deepcopy(presentation_verification_context)
    expected_hash = request_copy.get("expected_presentation_v11_hash") if _is_plain_mapping(request_copy) else None
    if not _valid_request(request_copy) or not _valid_context(context_copy):
        return _unknown_response(expected_hash)
    document = request_copy[
        "stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_v11_document"
    ]
    if not _valid_presentation_document(document, expected_hash):
        return _unknown_response(expected_hash)
    try:
        receipt = _VERIFY_PRESENTATION(
            document,
            presentation_v10_document=context_copy["presentation_v10_document"],
            adapter_v10_document=context_copy["adapter_v10_document"],
            presentation_v10_verification_context=context_copy[
                "presentation_v10_verification_context"
            ],
            adapter_v10_verification_context=context_copy[
                "adapter_v10_verification_context"
            ],
        )
    except Exception:
        return _unknown_response(expected_hash)
    if not _valid_receipt(receipt, expected_hash):
        return _unknown_response(expected_hash)
    summaries = _all_summaries(document)
    if summaries is None:
        return _unknown_response(expected_hash)
    blockers = list(BASE_BLOCKERS)
    local_decision = document["local_decision"]
    if (
        local_decision.get("joint_status") == "BLOCK"
        or local_decision.get("presentation_v10_joint_status") == "BLOCK"
    ):
        blockers.append("PRESENTATION_V11_LOCAL_BLOCK")
    if local_decision.get("adapter_v10_status") == "BLOCK":
        blockers.append("ADAPTER_V10_BLOCK")
    if (
        local_decision.get("common_observation_membership_gate_v2_status") == "BLOCK"
        or summaries["membership"].get("all_pair_membership_hashes_match_common")
        is not True
        or _summary_is_blocked(summaries["membership"])
    ):
        blockers.append("COMMON_OBSERVATION_MEMBERSHIP_BLOCK")
    payload = _known_payload(document, expected_hash, summaries, blockers)
    return _response(
        state=KNOWN_STATE,
        expected_hash=expected_hash,
        payload=payload,
        blockers=blockers,
        source_static_contract_version=document["static_fingerprint"],
    )


def verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_http_candidate_response_v11(
    response: Mapping[str, Any],
    request_payload: Mapping[str, Any],
    *,
    presentation_verification_context: Mapping[str, Any],
) -> bool:
    """Verify by exact deterministic rebuild; no compatibility path is accepted."""
    if not _is_plain_mapping(response):
        return False
    try:
        rebuilt = build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_http_candidate_response_v11(
            request_payload,
            presentation_verification_context=presentation_verification_context,
        )
    except Exception:
        return False
    return strict_json_contract_equal(response, rebuilt)


__all__ = [
    "INTERFACE_STATE",
    "KNOWN_STATE",
    "PAYLOAD_SCHEMA_VERSION",
    "PRESENTATION_GOVERNANCE_BLOCKERS",
    "PRESENTATION_SCHEMA_VERSION",
    "PRESENTATION_STATIC_FINGERPRINT",
    "PRESENTATION_V11_IMPLEMENTATION_HASH",
    "PRESENTATION_VERIFICATION_SCHEMA_VERSION",
    "REQUEST_SCHEMA_VERSION",
    "RESPONSE_SCHEMA_VERSION",
    "STATIC_CONTRACT_VERSION",
    "UNKNOWN_STATE",
    "build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_http_candidate_response_v11",
    "verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_http_candidate_response_v11",
]
