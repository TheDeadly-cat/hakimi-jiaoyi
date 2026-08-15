from __future__ import annotations

import hashlib
import json
import re
from typing import Any


STRATEGY_RESEARCH_SEARCH_LINEAGE_SCHEMA_VERSION = (
    "strategy-research-search-lineage-v1"
)
STRATEGY_RESEARCH_PRIOR_TRIALS_SCHEMA_VERSION = (
    "strategy-research-prior-trials-v1"
)
STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION = 14
STRATEGY_RESEARCH_REGISTRY_ANCHOR_SCHEMA_VERSION = (
    "strategy-research-registry-anchor-v1"
)

_SEARCH_FAMILY_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def normalize_search_family_id(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("strategy_search_family_id_type_invalid")
    clean = value.strip().lower()
    if not _SEARCH_FAMILY_ID.fullmatch(clean):
        raise ValueError("strategy_search_family_id_invalid")
    return clean


def _positive_int(value: Any, error: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(error)
    return value


def _prior_registration(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("strategy_search_prior_registration_type_invalid")
    expected_fields = {
        "registration_id",
        "protocol_hash",
        "registered_event_hash",
        "search_family_id",
        "report_schema_version",
        "lineage_mode",
        "current_trial_count",
        "cumulative_trial_count",
    }
    if set(value) != expected_fields:
        raise ValueError("strategy_search_prior_registration_shape_invalid")
    registration_id = value.get("registration_id")
    if not isinstance(registration_id, str) or not registration_id.strip():
        raise ValueError("strategy_search_prior_registration_id_invalid")
    protocol_hash = str(value.get("protocol_hash") or "").lower()
    event_hash = str(value.get("registered_event_hash") or "").lower()
    if not _SHA256.fullmatch(protocol_hash):
        raise ValueError("strategy_search_prior_protocol_hash_invalid")
    if not _SHA256.fullmatch(event_hash):
        raise ValueError("strategy_search_prior_event_hash_invalid")
    lineage_mode = value.get("lineage_mode")
    if lineage_mode not in {"BOUND", "LEGACY_UNSCOPED"}:
        raise ValueError("strategy_search_prior_lineage_mode_invalid")
    raw_family_id = value.get("search_family_id")
    if lineage_mode == "BOUND":
        search_family_id: str | None = normalize_search_family_id(raw_family_id)
    elif raw_family_id is not None:
        raise ValueError("strategy_search_prior_legacy_family_invalid")
    else:
        search_family_id = None
    report_schema_version = value.get("report_schema_version")
    if (
        isinstance(report_schema_version, bool)
        or not isinstance(report_schema_version, int)
        or not 3 <= report_schema_version <= STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION
    ):
        raise ValueError("strategy_search_prior_report_schema_invalid")
    current_trials = _positive_int(
        value.get("current_trial_count"),
        "strategy_search_prior_current_trial_count_invalid",
    )
    cumulative_trials = _positive_int(
        value.get("cumulative_trial_count"),
        "strategy_search_prior_cumulative_trial_count_invalid",
    )
    return {
        "registration_id": registration_id.strip(),
        "protocol_hash": protocol_hash,
        "registered_event_hash": event_hash,
        "search_family_id": search_family_id,
        "report_schema_version": report_schema_version,
        "lineage_mode": lineage_mode,
        "current_trial_count": current_trials,
        "cumulative_trial_count": cumulative_trials,
    }


def build_strategy_research_search_lineage(
    *,
    search_family_id: Any,
    prior_registrations: list[dict[str, Any]] | Any,
    current_trial_count: Any,
) -> dict[str, Any]:
    """Build the exact pre-selection cumulative-search snapshot for one run.

    ``prior_registrations`` is intentionally supplied by the registration
    ledger, not by a completed research report. The registry re-derives this
    snapshot under its write transaction before accepting a protocol.
    """

    family_id = normalize_search_family_id(search_family_id)
    current_trials = _positive_int(
        current_trial_count,
        "strategy_search_current_trial_count_invalid",
    )
    if not isinstance(prior_registrations, list):
        raise ValueError("strategy_search_prior_registrations_invalid")
    prior = [_prior_registration(item) for item in prior_registrations]
    registration_ids = [item["registration_id"] for item in prior]
    protocol_hashes = [item["protocol_hash"] for item in prior]
    event_hashes = [item["registered_event_hash"] for item in prior]
    if (
        len(set(registration_ids)) != len(registration_ids)
        or len(set(protocol_hashes)) != len(protocol_hashes)
        or len(set(event_hashes)) != len(event_hashes)
    ):
        raise ValueError("strategy_search_prior_registration_duplicate")

    running_total = 0
    for item in prior:
        running_total += item["current_trial_count"]
        if item["cumulative_trial_count"] != running_total:
            raise ValueError("strategy_search_prior_cumulative_chain_invalid")

    prior_trials_content = {
        "schema_version": STRATEGY_RESEARCH_PRIOR_TRIALS_SCHEMA_VERSION,
        "scope": "GLOBAL_REGISTERED_STRATEGY_RESEARCH",
        "registrations": prior,
    }
    parent = prior[-1] if prior else None
    content = {
        "schema_version": STRATEGY_RESEARCH_SEARCH_LINEAGE_SCHEMA_VERSION,
        "status": "PREREGISTERED",
        "search_family_id": family_id,
        "trial_count_scope": "GLOBAL_REGISTERED_STRATEGY_RESEARCH",
        "parent_registration_id": (
            parent["registration_id"] if parent is not None else None
        ),
        "parent_registration_hash": (
            parent["protocol_hash"] if parent is not None else None
        ),
        "parent_registry_event_hash": (
            parent["registered_event_hash"] if parent is not None else None
        ),
        "prior_registration_count": len(prior),
        "prior_trial_count": running_total,
        "current_trial_count": current_trials,
        "cumulative_trial_count": running_total + current_trials,
        "prior_trials_hash": canonical_hash(prior_trials_content),
        "derived_before_selection": True,
        "selection_result_fields_used": [],
        "descriptive_only": True,
        "profitability_proven": False,
        "parameter_selection_allowed": False,
        "automatic_paper_activation_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {**content, "lineage_hash": canonical_hash(content)}


def verify_strategy_research_search_lineage(
    payload: dict[str, Any] | Any,
    *,
    expected_search_family_id: str | None = None,
    expected_current_trial_count: int | None = None,
    expected_prior_registrations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    if not isinstance(payload, dict):
        return {
            "status": "BLOCK",
            "blockers": ["strategy_search_lineage_type_invalid"],
            "lineage_hash": "",
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    family_id = payload.get("search_family_id")
    current_trials = payload.get("current_trial_count")
    try:
        normalized_family = normalize_search_family_id(family_id)
        normalized_current = _positive_int(
            current_trials,
            "strategy_search_current_trial_count_invalid",
        )
    except ValueError as exc:
        blockers.append(str(exc))
        normalized_family = ""
        normalized_current = 0

    if expected_search_family_id is not None:
        try:
            expected_family = normalize_search_family_id(expected_search_family_id)
        except ValueError as exc:
            blockers.append(str(exc))
            expected_family = ""
        if normalized_family != expected_family:
            blockers.append("strategy_search_family_binding_mismatch")
    if expected_current_trial_count is not None and (
        isinstance(expected_current_trial_count, bool)
        or not isinstance(expected_current_trial_count, int)
        or normalized_current != expected_current_trial_count
    ):
        blockers.append("strategy_search_current_trial_count_mismatch")

    if expected_prior_registrations is not None and normalized_family and normalized_current:
        try:
            expected = build_strategy_research_search_lineage(
                search_family_id=normalized_family,
                prior_registrations=expected_prior_registrations,
                current_trial_count=normalized_current,
            )
        except ValueError as exc:
            blockers.append(str(exc))
            expected = {}
        if expected and payload != expected:
            blockers.append("strategy_search_registry_lineage_mismatch")
    else:
        expected_fields = {
            "schema_version",
            "status",
            "search_family_id",
            "trial_count_scope",
            "parent_registration_id",
            "parent_registration_hash",
            "parent_registry_event_hash",
            "prior_registration_count",
            "prior_trial_count",
            "current_trial_count",
            "cumulative_trial_count",
            "prior_trials_hash",
            "derived_before_selection",
            "selection_result_fields_used",
            "descriptive_only",
            "profitability_proven",
            "parameter_selection_allowed",
            "automatic_paper_activation_allowed",
            "research_only",
            "paper_authorized",
            "live_order_allowed",
            "lineage_hash",
        }
        if set(payload) != expected_fields:
            blockers.append("strategy_search_lineage_shape_invalid")
        content = {key: value for key, value in payload.items() if key != "lineage_hash"}
        if (
            payload.get("schema_version")
            != STRATEGY_RESEARCH_SEARCH_LINEAGE_SCHEMA_VERSION
            or payload.get("status") != "PREREGISTERED"
            or payload.get("trial_count_scope")
            != "GLOBAL_REGISTERED_STRATEGY_RESEARCH"
            or payload.get("derived_before_selection") is not True
            or payload.get("selection_result_fields_used") != []
        ):
            blockers.append("strategy_search_lineage_policy_invalid")
        prior_count = payload.get("prior_registration_count")
        prior_trials = payload.get("prior_trial_count")
        cumulative = payload.get("cumulative_trial_count")
        if (
            isinstance(prior_count, bool)
            or not isinstance(prior_count, int)
            or prior_count < 0
            or isinstance(prior_trials, bool)
            or not isinstance(prior_trials, int)
            or prior_trials < 0
            or isinstance(cumulative, bool)
            or not isinstance(cumulative, int)
            or cumulative != prior_trials + normalized_current
        ):
            blockers.append("strategy_search_lineage_count_invalid")
        parent_fields = (
            payload.get("parent_registration_id"),
            payload.get("parent_registration_hash"),
            payload.get("parent_registry_event_hash"),
        )
        if prior_count == 0:
            if parent_fields != (None, None, None) or prior_trials != 0:
                blockers.append("strategy_search_lineage_genesis_invalid")
        elif (
            not isinstance(parent_fields[0], str)
            or not parent_fields[0].strip()
            or not isinstance(parent_fields[1], str)
            or not _SHA256.fullmatch(parent_fields[1])
            or not isinstance(parent_fields[2], str)
            or not _SHA256.fullmatch(parent_fields[2])
        ):
            blockers.append("strategy_search_lineage_parent_invalid")
        if not _SHA256.fullmatch(str(payload.get("prior_trials_hash") or "")):
            blockers.append("strategy_search_prior_trials_hash_invalid")
        if str(payload.get("lineage_hash") or "") != canonical_hash(content):
            blockers.append("strategy_search_lineage_hash_invalid")
        if (
            payload.get("descriptive_only") is not True
            or payload.get("profitability_proven") is not False
            or payload.get("parameter_selection_allowed") is not False
            or payload.get("automatic_paper_activation_allowed") is not False
            or payload.get("research_only") is not True
            or payload.get("paper_authorized") is not False
            or payload.get("live_order_allowed") is not False
        ):
            blockers.append("strategy_search_lineage_authority_invalid")

    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "lineage_hash": str(payload.get("lineage_hash") or ""),
        "cumulative_trial_count": (
            payload.get("cumulative_trial_count")
            if isinstance(payload.get("cumulative_trial_count"), int)
            and not isinstance(payload.get("cumulative_trial_count"), bool)
            else None
        ),
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def build_strategy_research_registry_anchor(
    *,
    registration_id: Any,
    protocol_hash: Any,
    registered_event_hash: Any,
    registry_audit_tail_event_hash: Any,
    active_runtime_root: Any,
    canonical_registry_path: Any,
    search_lineage: dict[str, Any] | Any,
) -> dict[str, Any]:
    """Bind a registered lineage to the registry audit completed before data load."""

    clean_registration_id = str(registration_id or "").strip()
    clean_protocol_hash = str(protocol_hash or "").strip().lower()
    clean_registered_event_hash = str(registered_event_hash or "").strip().lower()
    clean_tail_hash = str(registry_audit_tail_event_hash or "").strip().lower()
    clean_runtime_root = str(active_runtime_root or "").strip()
    clean_registry_path = str(canonical_registry_path or "").strip()
    if not clean_registration_id:
        raise ValueError("strategy_search_registry_anchor_registration_id_invalid")
    if not _SHA256.fullmatch(clean_protocol_hash):
        raise ValueError("strategy_search_registry_anchor_protocol_hash_invalid")
    if not _SHA256.fullmatch(clean_registered_event_hash):
        raise ValueError("strategy_search_registry_anchor_event_hash_invalid")
    if not _SHA256.fullmatch(clean_tail_hash):
        raise ValueError("strategy_search_registry_anchor_tail_hash_invalid")
    if not clean_runtime_root or not clean_registry_path:
        raise ValueError("strategy_search_registry_anchor_path_invalid")
    lineage_verification = verify_strategy_research_search_lineage(search_lineage)
    if lineage_verification.get("status") != "PASS":
        raise ValueError(
            "strategy_search_registry_anchor_lineage_invalid:"
            + ",".join(
                str(item) for item in lineage_verification.get("blockers") or []
            )
        )
    lineage = dict(search_lineage)
    content = {
        "schema_version": STRATEGY_RESEARCH_REGISTRY_ANCHOR_SCHEMA_VERSION,
        "status": "REGISTRY_VERIFIED_BEFORE_SELECTION",
        "registration_id": clean_registration_id,
        "protocol_hash": clean_protocol_hash,
        "registered_event_hash": clean_registered_event_hash,
        "registry_audit_tail_event_hash": clean_tail_hash,
        "active_runtime_root": clean_runtime_root,
        "canonical_registry_path": clean_registry_path,
        "lineage_hash": str(lineage.get("lineage_hash") or ""),
        "trial_count_scope": str(lineage.get("trial_count_scope") or ""),
        "current_trial_count": lineage.get("current_trial_count"),
        "cumulative_trial_count": lineage.get("cumulative_trial_count"),
        "registry_audited_at_registration": True,
        "registry_audited_before_selection": True,
        "selection_result_fields_used": [],
        "descriptive_only": True,
        "profitability_proven": False,
        "parameter_selection_allowed": False,
        "automatic_paper_activation_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {**content, "anchor_hash": canonical_hash(content)}


def verify_strategy_research_registry_anchor(
    payload: dict[str, Any] | Any,
    *,
    search_lineage: dict[str, Any] | Any,
    expected_registration_id: str | None = None,
    expected_protocol_hash: str | None = None,
    expected_active_runtime_root: str | None = None,
    expected_canonical_registry_path: str | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    if not isinstance(payload, dict):
        return {
            "status": "BLOCK",
            "blockers": ["strategy_search_registry_anchor_type_invalid"],
            "anchor_hash": "",
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    lineage_verification = verify_strategy_research_search_lineage(search_lineage)
    if lineage_verification.get("status") != "PASS":
        blockers.extend(
            f"strategy_search_registry_anchor_lineage:{item}"
            for item in lineage_verification.get("blockers") or []
        )
    lineage = dict(search_lineage) if isinstance(search_lineage, dict) else {}
    expected_fields = {
        "schema_version",
        "status",
        "registration_id",
        "protocol_hash",
        "registered_event_hash",
        "registry_audit_tail_event_hash",
        "active_runtime_root",
        "canonical_registry_path",
        "lineage_hash",
        "trial_count_scope",
        "current_trial_count",
        "cumulative_trial_count",
        "registry_audited_at_registration",
        "registry_audited_before_selection",
        "selection_result_fields_used",
        "descriptive_only",
        "profitability_proven",
        "parameter_selection_allowed",
        "automatic_paper_activation_allowed",
        "research_only",
        "paper_authorized",
        "live_order_allowed",
        "anchor_hash",
    }
    if set(payload) != expected_fields:
        blockers.append("strategy_search_registry_anchor_shape_invalid")
    content = {key: value for key, value in payload.items() if key != "anchor_hash"}
    if (
        payload.get("schema_version")
        != STRATEGY_RESEARCH_REGISTRY_ANCHOR_SCHEMA_VERSION
        or payload.get("status") != "REGISTRY_VERIFIED_BEFORE_SELECTION"
        or payload.get("registry_audited_at_registration") is not True
        or payload.get("registry_audited_before_selection") is not True
        or payload.get("selection_result_fields_used") != []
    ):
        blockers.append("strategy_search_registry_anchor_policy_invalid")
    if (
        not str(payload.get("active_runtime_root") or "").strip()
        or not str(payload.get("canonical_registry_path") or "").strip()
    ):
        blockers.append("strategy_search_registry_anchor_path_invalid")
    for field in (
        "protocol_hash",
        "registered_event_hash",
        "registry_audit_tail_event_hash",
        "lineage_hash",
        "anchor_hash",
    ):
        if not _SHA256.fullmatch(str(payload.get(field) or "")):
            blockers.append(f"strategy_search_registry_anchor_hash_invalid:{field}")
    if str(payload.get("anchor_hash") or "") != canonical_hash(content):
        blockers.append("strategy_search_registry_anchor_hash_mismatch")
    if (
        str(payload.get("lineage_hash") or "")
        != str(lineage.get("lineage_hash") or "")
        or payload.get("trial_count_scope") != lineage.get("trial_count_scope")
        or payload.get("current_trial_count") != lineage.get("current_trial_count")
        or payload.get("cumulative_trial_count")
        != lineage.get("cumulative_trial_count")
    ):
        blockers.append("strategy_search_registry_anchor_lineage_binding_mismatch")
    if expected_registration_id is not None and str(
        payload.get("registration_id") or ""
    ) != str(expected_registration_id or "").strip():
        blockers.append("strategy_search_registry_anchor_registration_mismatch")
    if expected_protocol_hash is not None and str(
        payload.get("protocol_hash") or ""
    ) != str(expected_protocol_hash or "").strip().lower():
        blockers.append("strategy_search_registry_anchor_protocol_mismatch")
    if expected_active_runtime_root is not None and str(
        payload.get("active_runtime_root") or ""
    ) != str(expected_active_runtime_root or "").strip():
        blockers.append("strategy_search_registry_anchor_runtime_root_mismatch")
    if expected_canonical_registry_path is not None and str(
        payload.get("canonical_registry_path") or ""
    ) != str(expected_canonical_registry_path or "").strip():
        blockers.append("strategy_search_registry_anchor_registry_path_mismatch")
    if (
        payload.get("descriptive_only") is not True
        or payload.get("profitability_proven") is not False
        or payload.get("parameter_selection_allowed") is not False
        or payload.get("automatic_paper_activation_allowed") is not False
        or payload.get("research_only") is not True
        or payload.get("paper_authorized") is not False
        or payload.get("live_order_allowed") is not False
    ):
        blockers.append("strategy_search_registry_anchor_authority_invalid")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "anchor_hash": str(payload.get("anchor_hash") or ""),
        "cumulative_trial_count": (
            payload.get("cumulative_trial_count")
            if isinstance(payload.get("cumulative_trial_count"), int)
            and not isinstance(payload.get("cumulative_trial_count"), bool)
            else None
        ),
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "STRATEGY_RESEARCH_REGISTRY_ANCHOR_SCHEMA_VERSION",
    "STRATEGY_RESEARCH_PRIOR_TRIALS_SCHEMA_VERSION",
    "STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION",
    "STRATEGY_RESEARCH_SEARCH_LINEAGE_SCHEMA_VERSION",
    "build_strategy_research_search_lineage",
    "build_strategy_research_registry_anchor",
    "canonical_hash",
    "normalize_search_family_id",
    "verify_strategy_research_search_lineage",
    "verify_strategy_research_registry_anchor",
]
