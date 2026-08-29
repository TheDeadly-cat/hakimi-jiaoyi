"""Redacted protocol-v7 and registry-binding migration projection."""

from __future__ import annotations

from typing import Any

from exchange_terminal.services.strategy_correlation_strata_protocol import (
    verify_strategy_correlation_strata_protocol_registration,
)
from exchange_terminal.services.strategy_correlation_strata_registry import (
    verify_strategy_correlation_strata_registry_binding,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    strict_json_contract_equal,
)


PUBLIC_SUMMARY_SCHEMA = (
    "strategy-correlation-strata-protocol-migration-public-summary-v1"
)
STATIC_FINGERPRINT = "20260821-strata-protocol-v7-migration-seal-1"


def _permission() -> dict[str, Any]:
    return {
        "status": "RESEARCH_ONLY",
        "descriptive_only": True,
        "profitability_claim_allowed": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "formal_registry_activation_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _redaction() -> dict[str, bool]:
    return {
        "symbol_identities_exposed": False,
        "cluster_identities_exposed": False,
        "registry_identity_exposed": False,
        "artifact_hashes_exposed": False,
        "classification_source_exposed": False,
        "selection_cutoff_exposed": False,
    }


def _unknown_summary() -> dict[str, Any]:
    return {
        "schema_version": PUBLIC_SUMMARY_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "source": {
            "status": "UNKNOWN",
            "protocol_target": None,
            "report_target": None,
            "report18_consumer_status": "UNKNOWN",
            "registry_candidate_contract_status": "UNKNOWN",
        },
        "gap": {
            "status": "UNKNOWN",
            "registry_evidence_status": "UNKNOWN",
            "registry_binding_status": None,
        },
        "maturity": {
            "status": "UNKNOWN",
            "formal_registry": "UNKNOWN",
            "writer": "NOT_IMPLEMENTED",
            "current": "NOT_ACTIVATED",
            "writer_prerequisite_count": None,
        },
        "permission": _permission(),
        "redaction": _redaction(),
    }


def build_strategy_correlation_strata_protocol_migration_public_summary(
    source_protocol_registration: Any,
    *,
    registry_binding: Any = None,
    registry_asset: Any = None,
    strata_registration: Any = None,
    source_preregistration: Any = None,
    selection_cutoff_date: Any = None,
    expected_registry_asset_hash: Any = None,
    expected_classification_source_hash: Any = None,
) -> dict[str, Any]:
    try:
        protocol_verification = (
            verify_strategy_correlation_strata_protocol_registration(
                source_protocol_registration
            )
        )
        if protocol_verification.get("status") != "PASS":
            return _unknown_summary()
        if type(source_protocol_registration) is not dict:
            return _unknown_summary()
        policy = source_protocol_registration.get("strata_policy")
        if type(policy) is not dict:
            return _unknown_summary()
        prerequisites = policy.get("writer_activation_prerequisites")
        if type(prerequisites) is not list:
            return _unknown_summary()

        registry_inputs = [
            registry_binding,
            registry_asset,
            strata_registration,
            source_preregistration,
            selection_cutoff_date,
            expected_registry_asset_hash,
            expected_classification_source_hash,
        ]
        registry_supplied = any(value is not None for value in registry_inputs)
        registry_complete = all(value is not None for value in registry_inputs)
        if registry_supplied and not registry_complete:
            return _unknown_summary()

        gap_status = "REAL_REGISTRY_ASSET_NOT_SUPPLIED"
        registry_evidence_status = "NOT_SUPPLIED"
        registry_binding_status = None
        maturity_status = "PROTOCOL_PREREGISTERED"
        if registry_complete:
            if (
                type(source_preregistration) is not dict
                or source_preregistration.get("preregistration_hash")
                != source_protocol_registration.get(
                    "cluster_preregistration_hash"
                )
            ):
                return _unknown_summary()
            binding_verification = (
                verify_strategy_correlation_strata_registry_binding(
                    registry_binding,
                    registry_asset=registry_asset,
                    registration=strata_registration,
                    source_preregistration=source_preregistration,
                    selection_cutoff_date=selection_cutoff_date,
                    expected_registry_asset_hash=expected_registry_asset_hash,
                    expected_classification_source_hash=(
                        expected_classification_source_hash
                    ),
                )
            )
            if binding_verification.get("status") != "PASS":
                return _unknown_summary()
            if type(registry_binding) is not dict:
                return _unknown_summary()
            registry_binding_status = registry_binding.get("status")
            if registry_binding_status not in {"BOUND", "BLOCK"}:
                return _unknown_summary()
            registry_evidence_status = "OBSERVED"
            if registry_binding_status == "BOUND":
                gap_status = "FORMAL_PERSISTENCE_AND_WRITER_PENDING"
                maturity_status = "REGISTRY_BOUND_CANDIDATE"
            else:
                gap_status = "REGISTRY_BINDING_BLOCK_OBSERVED"

        return {
            "schema_version": PUBLIC_SUMMARY_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "source": {
                "status": "OBSERVED",
                "protocol_target": "PROTOCOL_V7",
                "report_target": "REPORT18",
                "report18_consumer_status": "AVAILABLE",
                "registry_candidate_contract_status": "AVAILABLE",
            },
            "gap": {
                "status": gap_status,
                "registry_evidence_status": registry_evidence_status,
                "registry_binding_status": registry_binding_status,
            },
            "maturity": {
                "status": maturity_status,
                "formal_registry": "PENDING",
                "writer": "NOT_IMPLEMENTED",
                "current": "NOT_ACTIVATED",
                "writer_prerequisite_count": len(prerequisites),
            },
            "permission": _permission(),
            "redaction": _redaction(),
        }
    except (MemoryError, RecursionError):
        raise
    except (KeyError, TypeError, ValueError):
        return _unknown_summary()


def verify_strategy_correlation_strata_protocol_migration_public_summary(
    document: Any,
    *,
    source_protocol_registration: Any,
    registry_binding: Any = None,
    registry_asset: Any = None,
    strata_registration: Any = None,
    source_preregistration: Any = None,
    selection_cutoff_date: Any = None,
    expected_registry_asset_hash: Any = None,
    expected_classification_source_hash: Any = None,
) -> dict[str, Any]:
    expected = (
        build_strategy_correlation_strata_protocol_migration_public_summary(
            source_protocol_registration,
            registry_binding=registry_binding,
            registry_asset=registry_asset,
            strata_registration=strata_registration,
            source_preregistration=source_preregistration,
            selection_cutoff_date=selection_cutoff_date,
            expected_registry_asset_hash=expected_registry_asset_hash,
            expected_classification_source_hash=(
                expected_classification_source_hash
            ),
        )
    )
    blockers: list[str] = []
    if type(document) is not dict:
        blockers.append("strata_protocol_public_summary_contract_invalid")
    elif not strict_json_contract_equal(document, expected):
        blockers.append(
            "strata_protocol_public_summary_exact_rebuild_mismatch"
        )
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
    }
