from __future__ import annotations

from copy import deepcopy
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_adapter_v9
    as adapter_v9,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_membership_gate_v2
    as membership_gate_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-edge-"
    "uncertainty-common-observation-membership-adapter-v10"
)
VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-edge-"
    "uncertainty-common-observation-membership-adapter-v10-verification-v1"
)
STATIC_FINGERPRINT = (
    "20260823-stratified-multi-window-edge-uncertainty-common-observation-"
    "membership-adapter-v10-unmounted-lock-1"
)
ADAPTER_V9_IMPLEMENTATION_SHA256 = (
    "9bad81d8b719ab20402a5970498848660a343dd9f386b32294c5da50da3cf517"
)
MEMBERSHIP_GATE_V2_IMPLEMENTATION_SHA256 = (
    "af73de5542f926d9c268fe52284cba090602321cf36af401872821724de83e38"
)
BASIS_GATE_V1_IMPLEMENTATION_SHA256 = (
    "de56893e5413c182791761de2b15a5b3078275e6a587a624646dc7a2f38986f0"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
PASS_STATUS = "PASS"
BLOCK_STATUS = "BLOCK"
UNKNOWN_STATUS = "UNKNOWN"

_VERIFY_ADAPTER_V9 = (
    adapter_v9.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_adapter_v9
)
_VERIFY_MEMBERSHIP_GATE_V2 = (
    membership_gate_v2.verify_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_membership_gate_v2
)

_ADAPTER_CONTEXT_KEYS = {
    "adapter_v8_document",
    "adapter_v8_verification_context",
    "basis_gate_v1_document",
    "common_observation_basis_gate_v1_verification_context",
}
_MEMBERSHIP_CONTEXT_KEYS = {
    "basis_evidence",
    "basis_gate_v1_document",
    "basis_preregistration",
    "edge_evidence",
    "edge_gate_v1_document",
    "edge_preregistration",
    "expected_membership_preregistration_hash",
    "membership_evidence",
    "membership_preregistration",
}


def _exact_keys(value: Any, expected: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == expected


def _is_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _authority() -> dict[str, bool]:
    return {
        "current_admission_allowed": False,
        "descriptive_only": True,
        "live_order_allowed": False,
        "local_research_adapter_only": True,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
    }


def _adapter_receipt_valid(receipt: Any, document: Any) -> bool:
    return (
        _exact_keys(
            receipt,
            {
                "adapter_v9_exactly_verified",
                "adapter_v9_hash",
                "adapter_v9_status",
                "blockers",
                "current_admission_allowed",
                "live_order_allowed",
                "paper_authorized",
                "runtime_gate_activation_allowed",
                "schema_version",
                "source_known",
                "status",
                "writer_allowed",
            },
        )
        and receipt["schema_version"] == adapter_v9.VERIFICATION_SCHEMA_VERSION
        and receipt["adapter_v9_exactly_verified"] is True
        and receipt["source_known"] is True
        and receipt["status"] == PASS_STATUS
        and receipt["adapter_v9_status"] in {PASS_STATUS, BLOCK_STATUS}
        and receipt["adapter_v9_status"] == document["status"]
        and receipt["adapter_v9_hash"] == document["adapter_v9_hash"]
        and isinstance(receipt["blockers"], list)
        and all(isinstance(blocker, str) and blocker for blocker in receipt["blockers"])
        and all(
            receipt[key] is False
            for key in (
                "current_admission_allowed",
                "live_order_allowed",
                "paper_authorized",
                "runtime_gate_activation_allowed",
                "writer_allowed",
            )
        )
    )


def _membership_receipt_valid(receipt: Any, document: Any) -> bool:
    return (
        _exact_keys(
            receipt,
            {
                "blockers",
                "common_observation_membership_gate_v2_exactly_verified",
                "common_observation_membership_gate_v2_hash",
                "current_admission_allowed",
                "gate_decision",
                "gate_status",
                "live_order_allowed",
                "paper_authorized",
                "runtime_gate_activation_allowed",
                "schema_version",
                "source_known",
                "status",
                "writer_allowed",
            },
        )
        and receipt["schema_version"] == membership_gate_v2.VERIFICATION_SCHEMA_VERSION
        and receipt[
            "common_observation_membership_gate_v2_exactly_verified"
        ] is True
        and receipt["source_known"] is True
        and receipt["status"] == PASS_STATUS
        and receipt["gate_status"] in {PASS_STATUS, BLOCK_STATUS}
        and receipt["gate_status"] == document["status"]
        and receipt["gate_decision"] == document["decision"]
        and receipt["common_observation_membership_gate_v2_hash"]
        == document["common_observation_membership_gate_v2_hash"]
        and isinstance(receipt["blockers"], list)
        and all(isinstance(blocker, str) and blocker for blocker in receipt["blockers"])
        and all(
            receipt[key] is False
            for key in (
                "current_admission_allowed",
                "live_order_allowed",
                "paper_authorized",
                "runtime_gate_activation_allowed",
                "writer_allowed",
            )
        )
    )


def _checks_unknown() -> dict[str, bool]:
    return {
        "adapter_v9_exactly_verified": False,
        "basis_evidence_hash_cross_bound": False,
        "basis_gate_document_cross_bound": False,
        "basis_preregistration_hash_cross_bound": False,
        "common_membership_hash_cross_bound": False,
        "edge_evidence_hash_cross_bound": False,
        "edge_gate_hash_cross_bound": False,
        "edge_preregistration_hash_cross_bound": False,
        "membership_gate_v2_exactly_verified": False,
        "membership_pair_count_cross_bound": False,
        "partition_hash_cross_bound": False,
        "trade_identity_cross_bound": False,
    }


def _component_states_unknown() -> dict[str, str]:
    return {
        "adapter_v9_decision": UNKNOWN_STATUS,
        "adapter_v9_status": UNKNOWN_STATUS,
        "common_observation_basis_gate_v1_decision": UNKNOWN_STATUS,
        "common_observation_basis_gate_v1_status": UNKNOWN_STATUS,
        "common_observation_membership_gate_v2_decision": UNKNOWN_STATUS,
        "common_observation_membership_gate_v2_status": UNKNOWN_STATUS,
        "edge_gate_v1_decision": UNKNOWN_STATUS,
        "edge_gate_v1_status": UNKNOWN_STATUS,
    }


def _facts(source_known: bool) -> dict[str, bool]:
    return {
        "joint_local_research_decision_made": source_known,
        "membership_commitment_only": True,
        "profitability_proven": False,
        "raw_observation_ids_embedded": False,
        "raw_samples_recomputed": False,
        "source_documents_embedded": False,
        "source_statuses_known": source_known,
        "verification_contexts_embedded": False,
    }


def _source_unknown() -> dict[str, Any]:
    return {
        "adapter_v9_hash": None,
        "adapter_v9_implementation_sha256": ADAPTER_V9_IMPLEMENTATION_SHA256,
        "basis_evidence_hash": None,
        "basis_gate_v1_hash": None,
        "basis_gate_v1_implementation_sha256": BASIS_GATE_V1_IMPLEMENTATION_SHA256,
        "basis_preregistration_hash": None,
        "cluster_partition_hash": None,
        "common_observation_membership_hash": None,
        "common_sample_set_hash": None,
        "edge_evidence_hash": None,
        "edge_gate_v1_hash": None,
        "edge_preregistration_hash": None,
        "membership_evidence_hash": None,
        "membership_gate_v2_hash": None,
        "membership_gate_v2_implementation_sha256": (
            MEMBERSHIP_GATE_V2_IMPLEMENTATION_SHA256
        ),
        "membership_preregistration_hash": None,
        "observation_identifier_scheme_hash": None,
        "source_documents_embedded": False,
        "strict_canonical_implementation_sha256": (
            STRICT_CANONICAL_IMPLEMENTATION_SHA256
        ),
        "trade_identity_hash": None,
        "verification_contexts_embedded": False,
    }


def _sealed_adapter(
    *,
    status: str,
    decision: str,
    blockers: list[str],
    checks: dict[str, bool],
    component_states: dict[str, str],
    source: dict[str, Any],
    summary: dict[str, int] | None,
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "authority": _authority(),
            "blockers": blockers,
            "checks": checks,
            "component_states": component_states,
            "decision": decision,
            "facts": _facts(status != UNKNOWN_STATUS),
            "schema_version": SCHEMA_VERSION,
            "source": source,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": status,
            "summary": summary,
        },
        "adapter_v10_hash",
    )


def _unknown() -> dict[str, Any]:
    return _sealed_adapter(
        status=UNKNOWN_STATUS,
        decision="UNKNOWN_STRATIFIED_MULTI_WINDOW_EDGE_MEMBERSHIP_ADAPTER_V10",
        blockers=["ADAPTER_V10_SOURCE_UNKNOWN"],
        checks=_checks_unknown(),
        component_states=_component_states_unknown(),
        source=_source_unknown(),
        summary=None,
    )


def _exact_context(
    adapter_v9_document: Any,
    membership_gate_v2_document: Any,
    *,
    adapter_v9_verification_context: Any,
    membership_gate_v2_verification_context: Any,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    if not _exact_keys(adapter_v9_verification_context, _ADAPTER_CONTEXT_KEYS):
        return None
    if not _exact_keys(
        membership_gate_v2_verification_context, _MEMBERSHIP_CONTEXT_KEYS
    ):
        return None
    try:
        adapter_receipt = _VERIFY_ADAPTER_V9(
            adapter_v9_document,
            adapter_v9_verification_context["adapter_v8_document"],
            adapter_v9_verification_context["basis_gate_v1_document"],
            adapter_v8_verification_context=adapter_v9_verification_context[
                "adapter_v8_verification_context"
            ],
            common_observation_basis_gate_v1_verification_context=(
                adapter_v9_verification_context[
                    "common_observation_basis_gate_v1_verification_context"
                ]
            ),
        )
        membership_receipt = _VERIFY_MEMBERSHIP_GATE_V2(
            membership_gate_v2_document,
            membership_gate_v2_verification_context["membership_preregistration"],
            membership_gate_v2_verification_context["membership_evidence"],
            membership_gate_v2_verification_context["basis_gate_v1_document"],
            basis_preregistration=membership_gate_v2_verification_context[
                "basis_preregistration"
            ],
            basis_evidence=membership_gate_v2_verification_context[
                "basis_evidence"
            ],
            edge_gate_v1_document=membership_gate_v2_verification_context[
                "edge_gate_v1_document"
            ],
            edge_preregistration=membership_gate_v2_verification_context[
                "edge_preregistration"
            ],
            edge_evidence=membership_gate_v2_verification_context["edge_evidence"],
            expected_membership_preregistration_hash=(
                membership_gate_v2_verification_context[
                    "expected_membership_preregistration_hash"
                ]
            ),
        )
        if not _adapter_receipt_valid(adapter_receipt, adapter_v9_document):
            return None
        if not _membership_receipt_valid(
            membership_receipt, membership_gate_v2_document
        ):
            return None
        adapter_source = adapter_v9_document["source"]
        membership_source = membership_gate_v2_document["source"]
        adapter_summary = adapter_v9_document["summary"]
        membership_summary = membership_gate_v2_document["summary"]
        shared_basis_document = strict_json_contract_equal(
            adapter_v9_verification_context["basis_gate_v1_document"],
            membership_gate_v2_verification_context["basis_gate_v1_document"],
        )
        cross_bound = (
            shared_basis_document
            and adapter_source["common_observation_basis_gate_v1_hash"]
            == membership_source["basis_gate_v1_hash"]
            and adapter_source["basis_preregistration_hash"]
            == membership_source["basis_preregistration_hash"]
            and adapter_source["basis_evidence_hash"]
            == membership_source["basis_evidence_hash"]
            and adapter_source["edge_preregistration_hash"]
            == membership_source["edge_preregistration_hash"]
            and adapter_source["edge_evidence_hash"]
            == membership_source["edge_evidence_hash"]
            and adapter_source["edge_gate_v1_hash"]
            == membership_source["edge_gate_v1_hash"]
            and adapter_source["cluster_partition_hash"]
            == membership_source["cluster_partition_hash"]
            and adapter_source["trade_identity_hash"]
            == membership_source["trade_identity_hash"]
            and adapter_source["common_sample_set_hash"]
            == membership_source["common_observation_membership_hash"]
            and adapter_summary["common_sample_count"]
            == membership_summary["basis_common_sample_count"]
            and adapter_summary["edge_pair_count"]
            == membership_summary["edge_pair_count"]
        )
    except (KeyError, TypeError, ValueError):
        return None
    if not cross_bound:
        return None
    return adapter_receipt, membership_receipt


def evaluate_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_adapter_v10(
    adapter_v9_document: Any,
    membership_gate_v2_document: Any,
    *,
    adapter_v9_verification_context: Any,
    membership_gate_v2_verification_context: Any,
) -> dict[str, Any]:
    receipts = _exact_context(
        adapter_v9_document,
        membership_gate_v2_document,
        adapter_v9_verification_context=adapter_v9_verification_context,
        membership_gate_v2_verification_context=(
            membership_gate_v2_verification_context
        ),
    )
    if receipts is None:
        return _unknown()

    adapter_status = receipts[0]["adapter_v9_status"]
    membership_status = receipts[1]["gate_status"]
    blockers: list[str] = []
    if adapter_status == BLOCK_STATUS:
        blockers.append("ADAPTER_V9_BLOCKED")
    if membership_status == BLOCK_STATUS:
        blockers.append("COMMON_OBSERVATION_MEMBERSHIP_GATE_V2_BLOCKED")
    status = PASS_STATUS if not blockers else BLOCK_STATUS
    decision = (
        "PASS_STRATIFIED_MULTI_WINDOW_EDGE_MEMBERSHIP_ADAPTER_V10"
        if status == PASS_STATUS
        else "BLOCK_STRATIFIED_MULTI_WINDOW_EDGE_MEMBERSHIP_ADAPTER_V10"
    )

    adapter_source = adapter_v9_document["source"]
    membership_source = membership_gate_v2_document["source"]
    adapter_summary = adapter_v9_document["summary"]
    membership_summary = membership_gate_v2_document["summary"]
    checks = {
        "adapter_v9_exactly_verified": True,
        "basis_evidence_hash_cross_bound": True,
        "basis_gate_document_cross_bound": True,
        "basis_preregistration_hash_cross_bound": True,
        "common_membership_hash_cross_bound": True,
        "edge_evidence_hash_cross_bound": True,
        "edge_gate_hash_cross_bound": True,
        "edge_preregistration_hash_cross_bound": True,
        "membership_gate_v2_exactly_verified": True,
        "membership_pair_count_cross_bound": True,
        "partition_hash_cross_bound": True,
        "trade_identity_cross_bound": True,
    }
    component_states = {
        "adapter_v9_decision": adapter_v9_document["decision"],
        "adapter_v9_status": adapter_status,
        "common_observation_basis_gate_v1_decision": adapter_v9_document[
            "component_states"
        ]["common_observation_basis_gate_v1_decision"],
        "common_observation_basis_gate_v1_status": adapter_v9_document[
            "component_states"
        ]["common_observation_basis_gate_v1_status"],
        "common_observation_membership_gate_v2_decision": (
            membership_gate_v2_document["decision"]
        ),
        "common_observation_membership_gate_v2_status": membership_status,
        "edge_gate_v1_decision": adapter_v9_document["component_states"][
            "edge_gate_v1_decision"
        ],
        "edge_gate_v1_status": adapter_v9_document["component_states"][
            "edge_gate_v1_status"
        ],
    }
    source = {
        "adapter_v9_hash": adapter_v9_document["adapter_v9_hash"],
        "adapter_v9_implementation_sha256": ADAPTER_V9_IMPLEMENTATION_SHA256,
        "basis_evidence_hash": adapter_source["basis_evidence_hash"],
        "basis_gate_v1_hash": adapter_source[
            "common_observation_basis_gate_v1_hash"
        ],
        "basis_gate_v1_implementation_sha256": BASIS_GATE_V1_IMPLEMENTATION_SHA256,
        "basis_preregistration_hash": adapter_source["basis_preregistration_hash"],
        "cluster_partition_hash": adapter_source["cluster_partition_hash"],
        "common_observation_membership_hash": membership_source[
            "common_observation_membership_hash"
        ],
        "common_sample_set_hash": adapter_source["common_sample_set_hash"],
        "edge_evidence_hash": adapter_source["edge_evidence_hash"],
        "edge_gate_v1_hash": adapter_source["edge_gate_v1_hash"],
        "edge_preregistration_hash": adapter_source["edge_preregistration_hash"],
        "membership_evidence_hash": membership_source["membership_evidence_hash"],
        "membership_gate_v2_hash": membership_gate_v2_document[
            "common_observation_membership_gate_v2_hash"
        ],
        "membership_gate_v2_implementation_sha256": (
            MEMBERSHIP_GATE_V2_IMPLEMENTATION_SHA256
        ),
        "membership_preregistration_hash": membership_source[
            "membership_preregistration_hash"
        ],
        "observation_identifier_scheme_hash": membership_source[
            "observation_identifier_scheme_hash"
        ],
        "source_documents_embedded": False,
        "strict_canonical_implementation_sha256": (
            STRICT_CANONICAL_IMPLEMENTATION_SHA256
        ),
        "trade_identity_hash": adapter_source["trade_identity_hash"],
        "verification_contexts_embedded": False,
    }
    summary = {
        "blocked_pair_count": adapter_summary["blocked_pair_count"],
        "commitment_sample_count_match_pair_count": membership_summary[
            "commitment_sample_count_match_pair_count"
        ],
        "common_sample_count": adapter_summary["common_sample_count"],
        "confidence_z_micros": adapter_summary["confidence_z_micros"],
        "correlation_floor_micros": adapter_summary["correlation_floor_micros"],
        "edge_pair_count": adapter_summary["edge_pair_count"],
        "edge_sample_count_match_pair_count": membership_summary[
            "edge_sample_count_match_pair_count"
        ],
        "edge_verified_pair_count": adapter_summary["edge_verified_pair_count"],
        "expected_common_sample_count": membership_summary[
            "expected_common_sample_count"
        ],
        "insufficient_sample_pair_count": adapter_summary[
            "insufficient_sample_pair_count"
        ],
        "maximum_confidence_upper_correlation_micros": adapter_summary[
            "maximum_confidence_upper_correlation_micros"
        ],
        "membership_hash_match_pair_count": membership_summary[
            "membership_hash_match_pair_count"
        ],
        "minimum_common_sample_count": adapter_summary[
            "minimum_common_sample_count"
        ],
        "observed_breach_pair_count": adapter_summary[
            "observed_breach_pair_count"
        ],
        "pair_count_matching_common_sample_count": adapter_summary[
            "pair_count_matching_common_sample_count"
        ],
        "registered_membership_pair_count": membership_summary[
            "registered_pair_count"
        ],
        "registered_window_count": adapter_summary["registered_window_count"],
        "submitted_commitment_pair_count": membership_summary[
            "submitted_commitment_pair_count"
        ],
        "uncertainty_overlap_pair_count": adapter_summary[
            "uncertainty_overlap_pair_count"
        ],
        "verified_window_count": adapter_summary["verified_window_count"],
    }
    return _sealed_adapter(
        status=status,
        decision=decision,
        blockers=blockers,
        checks=checks,
        component_states=component_states,
        source=source,
        summary=summary,
    )


def verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_adapter_v10(
    document: Any,
    adapter_v9_document: Any,
    membership_gate_v2_document: Any,
    *,
    adapter_v9_verification_context: Any,
    membership_gate_v2_verification_context: Any,
) -> dict[str, Any]:
    rebuilt = evaluate_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_adapter_v10(
        adapter_v9_document,
        membership_gate_v2_document,
        adapter_v9_verification_context=adapter_v9_verification_context,
        membership_gate_v2_verification_context=(
            membership_gate_v2_verification_context
        ),
    )
    exact = strict_json_contract_equal(document, rebuilt)
    source_known = exact and rebuilt["status"] != UNKNOWN_STATUS
    if source_known:
        verification_status = PASS_STATUS
        adapter_status = rebuilt["status"]
        adapter_hash = rebuilt["adapter_v10_hash"]
        blockers = deepcopy(rebuilt["blockers"])
    else:
        verification_status = UNKNOWN_STATUS
        adapter_status = UNKNOWN_STATUS
        adapter_hash = None
        blockers = ["ADAPTER_V10_EXACT_REBUILD_FAILED"]
    return {
        "adapter_v10_exactly_verified": source_known,
        "adapter_v10_hash": adapter_hash,
        "adapter_v10_status": adapter_status,
        "blockers": blockers,
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "source_known": source_known,
        "status": verification_status,
        "writer_allowed": False,
    }
