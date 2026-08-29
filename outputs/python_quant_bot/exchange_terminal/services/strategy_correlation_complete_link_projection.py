from __future__ import annotations

from typing import Any

try:
    from services.strict_canonical_json_hash import strict_json_contract_equal
except ModuleNotFoundError:
    from exchange_terminal.services.strict_canonical_json_hash import (
        strict_json_contract_equal,
    )

from exchange_terminal.services.strategy_correlation_cluster_complete_link import TOPOLOGY_RULE
from exchange_terminal.services.strategy_correlation_cluster_gate import (
    ABSOLUTE_PEARSON_THRESHOLD,
    MINIMUM_PAIR_OVERLAP,
)
from exchange_terminal.services.strategy_correlation_complete_link_protocol import (
    verify_strategy_correlation_complete_link_protocol_registration,
)


PUBLIC_SUMMARY_SCHEMA_VERSION = (
    "strategy-correlation-complete-link-migration-public-summary-v1"
)
PUBLIC_SUMMARY_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-complete-link-migration-public-summary-verification-v1"
)
STATIC_FINGERPRINT = "20260821-complete-link-migration-ledger-1"
MATURITY = "CONSUMER_ONLY"
PERMISSION = "RESEARCH_ONLY"


def _summary(*, observed: bool) -> dict[str, Any]:
    return {
        "schema_version": PUBLIC_SUMMARY_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "OBSERVED" if observed else "UNKNOWN",
        "source": "PROTOCOL_REGISTRATION_V4" if observed else "UNVERIFIED",
        "gap": "FORMAL_REGISTRY_AND_WRITER_PENDING" if observed else "SOURCE_UNVERIFIED",
        "gap_codes": (
            ["FORMAL_REGISTRY_NOT_BOUND", "SCHEMA17_WRITER_UNAVAILABLE"]
            if observed
            else ["SOURCE_UNVERIFIED"]
        ),
        "maturity": MATURITY if observed else "UNKNOWN",
        "permission": PERMISSION,
        "target_protocol_schema_version": "strategy-matrix-protocol-v6" if observed else None,
        "target_report_schema_version": 17 if observed else None,
        "topology_rule": TOPOLOGY_RULE if observed else None,
        "absolute_pearson_threshold": ABSOLUTE_PEARSON_THRESHOLD if observed else None,
        "minimum_pair_overlap": MINIMUM_PAIR_OVERLAP if observed else None,
        "schema17_consumer_available": True if observed else None,
        "formal_registry_bound": False,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "profitability_proven": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def build_strategy_correlation_complete_link_migration_public_summary(
    source_registration: Any,
) -> dict[str, Any]:
    verification = verify_strategy_correlation_complete_link_protocol_registration(
        source_registration
    )
    return _summary(observed=verification.get("status") == "PASS")


def verify_strategy_correlation_complete_link_migration_public_summary(
    document: Any,
    *,
    source_registration: Any,
) -> dict[str, Any]:
    expected = build_strategy_correlation_complete_link_migration_public_summary(
        source_registration
    )
    blockers = (
        []
        if type(document) is dict
        and strict_json_contract_equal(document, expected)
        else [
        "complete_link_migration_public_summary_contract_invalid"
        ]
    )
    return {
        "schema_version": PUBLIC_SUMMARY_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "profitability_proven": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
