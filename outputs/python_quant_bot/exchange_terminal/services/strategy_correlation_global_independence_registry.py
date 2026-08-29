"""Candidate registry contracts for protocol-v8 global-independence policy.

These pure contracts create and assess an in-memory candidate only. They do not
create a formal registry, persist assets, or activate a report writer/current.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import re
from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_violations,
)
from exchange_terminal.services.strategy_correlation_global_independence_protocol import (
    GLOBAL_INDEPENDENCE_AUDIT_SCHEMA_VERSION,
    GLOBAL_INDEPENDENCE_GATE_SCHEMA_VERSION,
    POLICY_SCHEMA_VERSION,
    REGISTRATION_SCHEMA_VERSION,
    TARGET_EXTENSION_SCHEMA_VERSION,
    TARGET_EXTENSION_VERIFICATION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
    verify_strategy_correlation_global_independence_protocol_registration,
)


REGISTRY_ASSET_SCHEMA_VERSION = (
    "strategy-correlation-global-independence-registry-asset-v1"
)
REGISTRY_ASSET_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-global-independence-registry-asset-v1-verification-v1"
)
BINDING_ASSESSMENT_SCHEMA_VERSION = (
    "strategy-correlation-global-independence-registry-binding-assessment-v1"
)
BINDING_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-global-independence-registry-binding-assessment-v1-verification-v1"
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_PERMISSIONS = {"paper_authorized": False, "live_order_allowed": False}


def _is_sha256(value: Any) -> bool:
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


def _is_nonempty_text(value: Any) -> bool:
    return type(value) is str and bool(value.strip()) and value == value.strip()


def _parse_date(value: Any) -> date | None:
    if type(value) is not str:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def _parse_utc_timestamp(value: Any) -> datetime | None:
    if type(value) is not str or not value.endswith("Z"):
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None
    expected = parsed.astimezone(timezone.utc).isoformat(timespec="seconds")
    expected = expected.replace("+00:00", "Z")
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed) or expected != value:
        return None
    return parsed


def build_strategy_correlation_global_independence_registry_asset(
    protocol_registration: Any,
    *,
    registry_id: Any,
    registry_source: Any,
    registry_source_version: Any,
    registry_source_hash: Any,
    effective_date: Any,
    frozen_at: Any,
) -> dict[str, Any]:
    """Build a frozen candidate asset from independently verified protocol-v8."""

    if type(protocol_registration) is not dict:
        raise ValueError("protocol_v8_registration_invalid")
    protocol_verification = (
        verify_strategy_correlation_global_independence_protocol_registration(
            protocol_registration
        )
    )
    if protocol_verification.get("status") != "PASS":
        raise ValueError("protocol_v8_registration_invalid")
    if strict_research_authority_violations(protocol_registration):
        raise ValueError("protocol_v8_authority_invalid")
    if not all(
        _is_nonempty_text(value)
        for value in (registry_id, registry_source, registry_source_version)
    ):
        raise ValueError("registry_metadata_invalid")
    if not _is_sha256(registry_source_hash):
        raise ValueError("registry_source_hash_invalid")
    effective = _parse_date(effective_date)
    frozen = _parse_utc_timestamp(frozen_at)
    if effective is None or frozen is None or effective > frozen.date():
        raise ValueError("registry_dates_invalid")

    asset = {
        "schema_version": REGISTRY_ASSET_SCHEMA_VERSION,
        "registry_id": registry_id,
        "registry_source": {
            "name": registry_source,
            "version": registry_source_version,
            "content_hash": registry_source_hash,
        },
        "protocol_registration_schema_version": REGISTRATION_SCHEMA_VERSION,
        "protocol_registration_hash": protocol_registration["registration_hash"],
        "global_independence_policy_schema_version": POLICY_SCHEMA_VERSION,
        "global_independence_policy_hash": protocol_registration[
            "global_independence_policy_hash"
        ],
        "source_strata_registry_asset_schema_version": protocol_registration[
            "registry_asset_schema_version"
        ],
        "source_strata_registry_binding_schema_version": protocol_registration[
            "registry_binding_schema_version"
        ],
        "target_extension_schema_version": TARGET_EXTENSION_SCHEMA_VERSION,
        "target_extension_verification_schema_version": (
            TARGET_EXTENSION_VERIFICATION_SCHEMA_VERSION
        ),
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "global_independence_audit_schema_version": (
            GLOBAL_INDEPENDENCE_AUDIT_SCHEMA_VERSION
        ),
        "global_independence_gate_schema_version": (
            GLOBAL_INDEPENDENCE_GATE_SCHEMA_VERSION
        ),
        "effective_date": effective_date,
        "frozen_at": frozen_at,
        "methodology": {
            "binding_scope": "PROTOCOL_V8_AND_GLOBAL_INDEPENDENCE_POLICY_ONLY",
            "evidence_results_used": False,
            "selection_returns_used": False,
            "post_freeze_edits_allowed": False,
            "effective_before_evidence_required": True,
            "exact_policy_binding_required": True,
        },
        "status": "FROZEN_CANDIDATE",
        "candidate_only": True,
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "writer_implemented": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    return seal_strict_canonical_document(asset, "registry_asset_hash")


def _asset_verification(status: str, blockers: list[str]) -> dict[str, Any]:
    return {
        "schema_version": REGISTRY_ASSET_VERIFICATION_SCHEMA_VERSION,
        "status": status,
        "blockers": list(dict.fromkeys(blockers)),
        "candidate_only": True,
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "writer_implemented": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }


def verify_strategy_correlation_global_independence_registry_asset(
    document: Any,
    *,
    protocol_registration: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        return _asset_verification("BLOCK", ["registry_asset_invalid"])
    if strict_research_authority_violations(document):
        blockers.append("research_authority_violation")
    registry_source = document.get("registry_source")
    if type(registry_source) is not dict:
        blockers.append("registry_source_invalid")
        expected = None
    else:
        try:
            expected = build_strategy_correlation_global_independence_registry_asset(
                protocol_registration,
                registry_id=document.get("registry_id"),
                registry_source=registry_source.get("name"),
                registry_source_version=registry_source.get("version"),
                registry_source_hash=registry_source.get("content_hash"),
                effective_date=document.get("effective_date"),
                frozen_at=document.get("frozen_at"),
            )
        except (KeyError, TypeError, ValueError):
            blockers.append("registry_asset_source_invalid")
            expected = None
    if expected is not None and not strict_json_contract_equal(document, expected):
        blockers.append("registry_asset_contract_invalid")
    return _asset_verification("PASS" if not blockers else "BLOCK", blockers)


def assess_strategy_correlation_global_independence_registry_binding(
    registry_asset: Any,
    protocol_registration: Any,
    *,
    evidence_cutoff_date: Any,
    expected_registry_asset_hash: Any,
    expected_registry_source_hash: Any,
    expected_protocol_registration_hash: Any,
    expected_global_independence_policy_hash: Any,
) -> dict[str, Any]:
    protocol_verification = (
        verify_strategy_correlation_global_independence_protocol_registration(
            protocol_registration
        )
        if type(protocol_registration) is dict
        else {"status": "BLOCK"}
    )
    asset_verification = (
        verify_strategy_correlation_global_independence_registry_asset(
            registry_asset,
            protocol_registration=protocol_registration,
        )
        if type(registry_asset) is dict
        else {"status": "BLOCK"}
    )
    cutoff = _parse_date(evidence_cutoff_date)
    effective = (
        _parse_date(registry_asset.get("effective_date"))
        if type(registry_asset) is dict
        else None
    )
    frozen = (
        _parse_utc_timestamp(registry_asset.get("frozen_at"))
        if type(registry_asset) is dict
        else None
    )
    source = (
        registry_asset.get("registry_source")
        if type(registry_asset) is dict
        else None
    )
    facts = {
        "protocol_registration_independently_verified": (
            protocol_verification.get("status") == "PASS"
        ),
        "registry_asset_independently_verified": (
            asset_verification.get("status") == "PASS"
        ),
        "registry_asset_hash_bound": (
            _is_sha256(expected_registry_asset_hash)
            and type(registry_asset) is dict
            and registry_asset.get("registry_asset_hash")
            == expected_registry_asset_hash
        ),
        "registry_source_hash_bound": (
            _is_sha256(expected_registry_source_hash)
            and type(source) is dict
            and source.get("content_hash") == expected_registry_source_hash
        ),
        "protocol_registration_hash_bound": (
            _is_sha256(expected_protocol_registration_hash)
            and type(registry_asset) is dict
            and type(protocol_registration) is dict
            and registry_asset.get("protocol_registration_hash")
            == expected_protocol_registration_hash
            == protocol_registration.get("registration_hash")
        ),
        "global_independence_policy_hash_bound": (
            _is_sha256(expected_global_independence_policy_hash)
            and type(registry_asset) is dict
            and type(protocol_registration) is dict
            and registry_asset.get("global_independence_policy_hash")
            == expected_global_independence_policy_hash
            == protocol_registration.get("global_independence_policy_hash")
        ),
        "effective_before_evidence": (
            cutoff is not None and effective is not None and effective < cutoff
        ),
        "frozen_before_evidence": (
            cutoff is not None and frozen is not None and frozen.date() < cutoff
        ),
        "report19_contract_bound": (
            type(registry_asset) is dict
            and registry_asset.get("target_protocol_schema_version")
            == TARGET_PROTOCOL_SCHEMA_VERSION
            and registry_asset.get("target_report_schema_version")
            == TARGET_REPORT_SCHEMA_VERSION
            and registry_asset.get("target_extension_schema_version")
            == TARGET_EXTENSION_SCHEMA_VERSION
        ),
        "global_gate_v2_contract_bound": (
            type(registry_asset) is dict
            and registry_asset.get("global_independence_gate_schema_version")
            == GLOBAL_INDEPENDENCE_GATE_SCHEMA_VERSION
            and registry_asset.get("global_independence_audit_schema_version")
            == GLOBAL_INDEPENDENCE_AUDIT_SCHEMA_VERSION
        ),
        "candidate_only_asserted": (
            type(registry_asset) is dict
            and type(registry_asset.get("candidate_only")) is bool
            and registry_asset.get("candidate_only") is True
        ),
        "formal_registry_unbound_asserted": (
            type(registry_asset) is dict
            and type(registry_asset.get("formal_registry_bound")) is bool
            and registry_asset.get("formal_registry_bound") is False
        ),
    }
    blockers = [name for name, passed in facts.items() if not passed]
    status = "CANDIDATE_BOUND" if not blockers else "BLOCK"
    assessment = {
        "schema_version": BINDING_ASSESSMENT_SCHEMA_VERSION,
        "registry_id": (
            registry_asset.get("registry_id")
            if type(registry_asset) is dict
            and type(registry_asset.get("registry_id")) is str
            else None
        ),
        "evidence_cutoff_date": (
            evidence_cutoff_date if type(evidence_cutoff_date) is str else None
        ),
        "facts": facts,
        "blockers": blockers,
        "status": status,
        "candidate_bound": status == "CANDIDATE_BOUND",
        "candidate_only": True,
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "writer_implemented": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    return seal_strict_canonical_document(assessment, "assessment_hash")


def verify_strategy_correlation_global_independence_registry_binding(
    document: Any,
    *,
    registry_asset: Any,
    protocol_registration: Any,
    evidence_cutoff_date: Any,
    expected_registry_asset_hash: Any,
    expected_registry_source_hash: Any,
    expected_protocol_registration_hash: Any,
    expected_global_independence_policy_hash: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        blockers.append("registry_binding_invalid")
    else:
        if strict_research_authority_violations(document):
            blockers.append("research_authority_violation")
        expected = assess_strategy_correlation_global_independence_registry_binding(
            registry_asset,
            protocol_registration,
            evidence_cutoff_date=evidence_cutoff_date,
            expected_registry_asset_hash=expected_registry_asset_hash,
            expected_registry_source_hash=expected_registry_source_hash,
            expected_protocol_registration_hash=expected_protocol_registration_hash,
            expected_global_independence_policy_hash=(
                expected_global_independence_policy_hash
            ),
        )
        if not strict_json_contract_equal(document, expected):
            blockers.append("registry_binding_contract_invalid")
    status = "PASS" if not blockers else "BLOCK"
    return {
        "schema_version": BINDING_VERIFICATION_SCHEMA_VERSION,
        "status": status,
        "blockers": list(dict.fromkeys(blockers)),
        "candidate_bound": (
            status == "PASS" and document.get("status") == "CANDIDATE_BOUND"
        ),
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "writer_implemented": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }


__all__ = [
    "BINDING_ASSESSMENT_SCHEMA_VERSION",
    "BINDING_VERIFICATION_SCHEMA_VERSION",
    "REGISTRY_ASSET_SCHEMA_VERSION",
    "REGISTRY_ASSET_VERIFICATION_SCHEMA_VERSION",
    "assess_strategy_correlation_global_independence_registry_binding",
    "build_strategy_correlation_global_independence_registry_asset",
    "verify_strategy_correlation_global_independence_registry_asset",
    "verify_strategy_correlation_global_independence_registry_binding",
]
