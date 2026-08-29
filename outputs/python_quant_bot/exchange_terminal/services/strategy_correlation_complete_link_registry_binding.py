from __future__ import annotations

import re
from typing import Any

try:
    from services.strict_canonical_json_hash import strict_json_contract_equal
except ModuleNotFoundError:
    from exchange_terminal.services.strict_canonical_json_hash import (
        strict_json_contract_equal,
    )

from exchange_terminal.services.strategy_correlation_complete_link_protocol import (
    verify_strategy_correlation_complete_link_protocol_registration,
)
from exchange_terminal.services.strategy_research_search_lineage import (
    STRATEGY_RESEARCH_SEARCH_LINEAGE_SCHEMA_VERSION_V2,
    verify_strategy_research_registry_anchor,
    verify_strategy_research_search_lineage,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    strict_canonical_hash,
)


ASSESSMENT_SCHEMA_VERSION = (
    "strategy-correlation-complete-link-registry-binding-assessment-v1"
)
VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-complete-link-registry-binding-verification-v1"
)

_PERMISSIONS = {
    "paper_authorized": False,
    "live_order_allowed": False,
}


def _sha256(value: Any) -> str:
    return strict_canonical_hash(value)


def _seal(payload: dict[str, Any]) -> dict[str, Any]:
    return {**payload, "assessment_hash": _sha256(payload)}


def _valid_hash(value: Any) -> bool:
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _identity(value: Any) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError("registry_binding_identity_invalid")
    return value


def _verification(blockers: list[str]) -> dict[str, Any]:
    unique = sorted(set(blockers))
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if not unique else "BLOCK",
        "blockers": unique,
        "writer_available": False,
        "writer_activation_allowed": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }


def assess_strategy_correlation_complete_link_registry_binding(
    registration: Any,
    registry_anchor: Any,
    search_lineage: Any,
    *,
    expected_registration_id: str,
    expected_active_runtime_root: str,
    expected_canonical_registry_path: str,
    expected_registry_asset_hash: str,
) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        registration_id = _identity(expected_registration_id)
        active_runtime_root = _identity(expected_active_runtime_root)
        canonical_registry_path = _identity(expected_canonical_registry_path)
    except ValueError as exc:
        registration_id = ""
        active_runtime_root = ""
        canonical_registry_path = ""
        blockers.append(str(exc))
    if not _valid_hash(expected_registry_asset_hash):
        blockers.append("registry_asset_hash_invalid")

    registration_verification = (
        verify_strategy_correlation_complete_link_protocol_registration(registration)
    )
    if registration_verification.get("status") != "PASS":
        blockers.append("complete_link_protocol_registration_invalid")
    registration_hash = (
        str(registration.get("registration_hash") or "")
        if type(registration) is dict
        else ""
    )

    lineage_verification = verify_strategy_research_search_lineage(search_lineage)
    if (
        lineage_verification.get("status") != "PASS"
        or type(search_lineage) is not dict
        or search_lineage.get("schema_version")
        != STRATEGY_RESEARCH_SEARCH_LINEAGE_SCHEMA_VERSION_V2
    ):
        blockers.append("strategy_search_lineage_v2_invalid")

    try:
        anchor_verification = verify_strategy_research_registry_anchor(
            registry_anchor,
            search_lineage=search_lineage,
            expected_registration_id=registration_id,
            expected_protocol_hash=registration_hash,
            expected_active_runtime_root=active_runtime_root,
            expected_canonical_registry_path=canonical_registry_path,
        )
    except (KeyError, TypeError, ValueError):
        anchor_verification = {"status": "BLOCK", "blockers": []}
    if anchor_verification.get("status") != "PASS":
        blockers.append("strategy_registry_anchor_invalid")

    status = "PASS" if not blockers else "BLOCK"
    payload = {
        "schema_version": ASSESSMENT_SCHEMA_VERSION,
        "status": status,
        "blockers": sorted(set(blockers)),
        "registration_hash": registration_hash,
        "registration_id": registration_id,
        "registry_anchor_hash": (
            str(registry_anchor.get("anchor_hash") or "")
            if type(registry_anchor) is dict
            else ""
        ),
        "search_lineage_hash": (
            str(search_lineage.get("lineage_hash") or "")
            if type(search_lineage) is dict
            else ""
        ),
        "registry_asset_hash": (
            expected_registry_asset_hash
            if _valid_hash(expected_registry_asset_hash)
            else ""
        ),
        "active_runtime_root": active_runtime_root,
        "canonical_registry_path": canonical_registry_path,
        "registry_anchor_contract_verified": status == "PASS",
        "registry_asset_fingerprint_bound": status == "PASS",
        "external_registry_asset_read_performed_by_assessor": False,
        "requires_caller_independent_registry_asset_hash": True,
        "writer_available": False,
        "writer_activation_allowed": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    return _seal(payload)


def verify_strategy_correlation_complete_link_registry_binding(
    document: Any,
    *,
    registration: Any,
    registry_anchor: Any,
    search_lineage: Any,
    expected_registration_id: str,
    expected_active_runtime_root: str,
    expected_canonical_registry_path: str,
    expected_registry_asset_hash: str,
) -> dict[str, Any]:
    try:
        expected = assess_strategy_correlation_complete_link_registry_binding(
            registration,
            registry_anchor,
            search_lineage,
            expected_registration_id=expected_registration_id,
            expected_active_runtime_root=expected_active_runtime_root,
            expected_canonical_registry_path=expected_canonical_registry_path,
            expected_registry_asset_hash=expected_registry_asset_hash,
        )
    except (KeyError, TypeError, ValueError):
        return _verification(["complete_link_registry_binding_source_invalid"])
    blockers = (
        []
        if type(document) is dict
        and strict_json_contract_equal(document, expected)
        else [
        "complete_link_registry_binding_contract_invalid"
        ]
    )
    return _verification(blockers)
