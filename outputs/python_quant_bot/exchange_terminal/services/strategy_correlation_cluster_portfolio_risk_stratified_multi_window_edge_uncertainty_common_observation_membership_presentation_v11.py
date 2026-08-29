from __future__ import annotations

from copy import deepcopy
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_v10
    as presentation_v10,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_adapter_v10
    as adapter_v10,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-edge-"
    "uncertainty-common-observation-membership-presentation-v11"
)
VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-edge-"
    "uncertainty-common-observation-membership-presentation-v11-verification-v1"
)
STATIC_FINGERPRINT = (
    "20260823-stratified-multi-window-edge-uncertainty-common-observation-"
    "membership-presentation-v11-unmounted-lock-1"
)
PRESENTATION_V10_IMPLEMENTATION_SHA256 = (
    "85a317babc16b310b9c62639879a241b0bf206d33a4be460a8d98400fb71c22e"
)
ADAPTER_V10_IMPLEMENTATION_SHA256 = (
    "1f8a8e76d15012bc40bd2640924fa0b4a97a05159f1b648359db925e09bfcca6"
)
MEMBERSHIP_GATE_V2_IMPLEMENTATION_SHA256 = (
    "af73de5542f926d9c268fe52284cba090602321cf36af401872821724de83e38"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
AXIS_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")
PRESENTATION_BLOCKERS = (
    "PRESENTATION_V11_CONSUMER_NOT_REGISTERED",
    "HTTP_CANDIDATE_V11_NOT_DEFINED",
    "UI_NOT_MOUNTED",
    "CURRENT_ADMISSION_LOCKED",
)
PASS_STATUS = "PASS"
BLOCK_STATUS = "BLOCK"
UNKNOWN_STATUS = "UNKNOWN"

_VERIFY_PRESENTATION_V10 = (
    presentation_v10.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_v10
)
_VERIFY_ADAPTER_V10 = (
    adapter_v10.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_adapter_v10
)

_PRESENTATION_CONTEXT_KEYS = {
    "adapter_v9_document",
    "adapter_v9_verification_context",
    "presentation_v9_document",
    "presentation_v9_verification_context",
}
_ADAPTER_CONTEXT_KEYS = {
    "adapter_v9_document",
    "adapter_v9_verification_context",
    "membership_gate_v2_document",
    "membership_gate_v2_verification_context",
}


def _exact_keys(value: Any, expected: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == expected


def _authority() -> dict[str, bool]:
    return {
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


def _presentation_receipt_valid(receipt: Any, document: Any) -> bool:
    return (
        _exact_keys(
            receipt,
            {
                "blockers",
                "current_admission_allowed",
                "live_order_allowed",
                "paper_authorized",
                "presentation_consumer_activation_allowed",
                "presentation_v10_exactly_verified",
                "presentation_v10_hash",
                "runtime_gate_activation_allowed",
                "schema_version",
                "status",
                "writer_allowed",
            },
        )
        and receipt["schema_version"] == presentation_v10.VERIFICATION_SCHEMA_VERSION
        and receipt["presentation_v10_exactly_verified"] is True
        and receipt["presentation_v10_hash"] == document["presentation_v10_hash"]
        and receipt["status"] == PASS_STATUS
        and isinstance(receipt["blockers"], list)
        and all(isinstance(blocker, str) and blocker for blocker in receipt["blockers"])
        and all(
            receipt[key] is False
            for key in (
                "current_admission_allowed",
                "live_order_allowed",
                "paper_authorized",
                "presentation_consumer_activation_allowed",
                "runtime_gate_activation_allowed",
                "writer_allowed",
            )
        )
    )


def _adapter_receipt_valid(receipt: Any, document: Any) -> bool:
    return (
        _exact_keys(
            receipt,
            {
                "adapter_v10_exactly_verified",
                "adapter_v10_hash",
                "adapter_v10_status",
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
        and receipt["schema_version"] == adapter_v10.VERIFICATION_SCHEMA_VERSION
        and receipt["adapter_v10_exactly_verified"] is True
        and receipt["source_known"] is True
        and receipt["status"] == PASS_STATUS
        and receipt["adapter_v10_status"] in {PASS_STATUS, BLOCK_STATUS}
        and receipt["adapter_v10_status"] == document["status"]
        and receipt["adapter_v10_hash"] == document["adapter_v10_hash"]
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


def _facts(*, source_known: bool) -> dict[str, bool]:
    return {
        "adapter_v10_exactly_verified": source_known,
        "browser_review_performed": False,
        "common_observation_basis_projected": source_known,
        "cross_bindings_verified": source_known,
        "http_candidate_registered": False,
        "membership_commitment_only": True,
        "membership_summary_projected": source_known,
        "positions_embedded": False,
        "presentation_v10_exactly_verified": source_known,
        "profitability_proven": False,
        "provenance_declaration_only": True,
        "raw_observation_ids_embedded": False,
        "raw_samples_recomputed": False,
        "runtime_assets_accessed": False,
        "runtime_consumer_bound": False,
        "source_documents_embedded": False,
        "ui_mounted": False,
        "verification_contexts_embedded": False,
    }


def _policy() -> dict[str, bool]:
    return {
        "adapter_v10_block_overrides_presentation_v10_local_pass": True,
        "membership_commitment_is_not_raw_sample_verification": True,
        "outer_status_always_block": True,
        "risk_reduction_is_not_execution_authority": True,
    }


def _stages(*, source_known: bool, local_blocked: bool) -> list[dict[str, str]]:
    if source_known:
        gap_detail = (
            "LOCAL_RESEARCH_BLOCK_PRESENT"
            if local_blocked
            else "LOCAL_RESEARCH_CLEAR_GOVERNANCE_GAPS_REMAIN"
        )
        gap_state = "OPEN" if local_blocked else "CLEAR_WITH_GOVERNANCE_GAPS"
        source_detail = "EXACT_PRESENTATION_V10_AND_ADAPTER_V10"
        source_state = "KNOWN"
    else:
        gap_detail = "SOURCE_UNKNOWN"
        gap_state = "UNKNOWN"
        source_detail = "PRESENTATION_V11_SOURCE_UNKNOWN"
        source_state = "UNKNOWN"
    return [
        {"axis": "SOURCE", "detail": source_detail, "state": source_state},
        {"axis": "GAP", "detail": gap_detail, "state": gap_state},
        {
            "axis": "MATURITY",
            "detail": "UNMOUNTED_PRESENTATION_CANDIDATE_V11",
            "state": "CANDIDATE",
        },
        {
            "axis": "PERMISSION",
            "detail": "NO_EXECUTION_OR_ACTIVATION_PERMISSION",
            "state": "NONE",
        },
    ]


def _unknown_local_decision() -> dict[str, str]:
    return {
        "adapter_v10_decision": UNKNOWN_STATUS,
        "adapter_v10_status": UNKNOWN_STATUS,
        "adapter_v9_decision": UNKNOWN_STATUS,
        "adapter_v9_status": UNKNOWN_STATUS,
        "common_observation_basis_gate_v1_decision": UNKNOWN_STATUS,
        "common_observation_basis_gate_v1_status": UNKNOWN_STATUS,
        "common_observation_membership_gate_v2_decision": UNKNOWN_STATUS,
        "common_observation_membership_gate_v2_status": UNKNOWN_STATUS,
        "edge_gate_v1_decision": UNKNOWN_STATUS,
        "edge_gate_v1_status": UNKNOWN_STATUS,
        "joint_decision": UNKNOWN_STATUS,
        "joint_status": UNKNOWN_STATUS,
        "presentation_v10_joint_decision": UNKNOWN_STATUS,
        "presentation_v10_joint_status": UNKNOWN_STATUS,
    }


def _source_unknown() -> dict[str, Any]:
    return {
        "adapter_v10_hash": None,
        "adapter_v10_implementation_sha256": ADAPTER_V10_IMPLEMENTATION_SHA256,
        "adapter_v9_hash": None,
        "basis_evidence_hash": None,
        "basis_preregistration_hash": None,
        "cluster_partition_hash": None,
        "common_observation_basis_gate_v1_hash": None,
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
        "presentation_v10_hash": None,
        "presentation_v10_implementation_sha256": (
            PRESENTATION_V10_IMPLEMENTATION_SHA256
        ),
        "presentation_v9_hash": None,
        "state": "UNKNOWN",
        "strict_canonical_implementation_sha256": (
            STRICT_CANONICAL_IMPLEMENTATION_SHA256
        ),
        "trade_identity_hash": None,
    }


def _sealed_presentation(
    *,
    source_known: bool,
    local_blocked: bool,
    decision: str,
    gaps: dict[str, Any],
    local_decision: dict[str, str],
    source: dict[str, Any],
    risk_summary: Any,
    multi_window_summary: Any,
    edge_uncertainty_summary: Any,
    common_observation_summary: Any,
    membership_summary: Any,
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "authority": _authority(),
            "axis_order": list(AXIS_ORDER),
            "common_observation_summary": common_observation_summary,
            "decision": decision,
            "edge_uncertainty_summary": edge_uncertainty_summary,
            "facts": _facts(source_known=source_known),
            "gaps": gaps,
            "local_decision": local_decision,
            "membership_summary": membership_summary,
            "multi_window_summary": multi_window_summary,
            "policy": _policy(),
            "risk_summary": risk_summary,
            "schema_version": SCHEMA_VERSION,
            "source": source,
            "stages": _stages(
                source_known=source_known, local_blocked=local_blocked
            ),
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": BLOCK_STATUS,
        },
        "presentation_v11_hash",
    )


def _unknown() -> dict[str, Any]:
    return _sealed_presentation(
        source_known=False,
        local_blocked=True,
        decision="BLOCK_OUTER_PRESENTATION_V11_SOURCE_UNKNOWN",
        gaps={
            "adapter_v10_blocker_count": 0,
            "local_blocker_count": 0,
            "membership_gate_v2_blocker_count": 0,
            "presentation_blocker_count": len(PRESENTATION_BLOCKERS),
            "presentation_blockers": list(PRESENTATION_BLOCKERS),
            "presentation_v10_local_blocker_count": 0,
            "source_failure": "PRESENTATION_V11_SOURCE_UNKNOWN",
        },
        local_decision=_unknown_local_decision(),
        source=_source_unknown(),
        risk_summary=None,
        multi_window_summary=None,
        edge_uncertainty_summary=None,
        common_observation_summary=None,
        membership_summary=None,
    )


def _exact_context(
    presentation_v10_document: Any,
    adapter_v10_document: Any,
    *,
    presentation_v10_verification_context: Any,
    adapter_v10_verification_context: Any,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    if not _exact_keys(
        presentation_v10_verification_context, _PRESENTATION_CONTEXT_KEYS
    ):
        return None
    if not _exact_keys(adapter_v10_verification_context, _ADAPTER_CONTEXT_KEYS):
        return None
    try:
        presentation_receipt = _VERIFY_PRESENTATION_V10(
            presentation_v10_document,
            presentation_v10_verification_context["presentation_v9_document"],
            presentation_v10_verification_context["adapter_v9_document"],
            presentation_v9_verification_context=(
                presentation_v10_verification_context[
                    "presentation_v9_verification_context"
                ]
            ),
            adapter_v9_verification_context=presentation_v10_verification_context[
                "adapter_v9_verification_context"
            ],
        )
        adapter_receipt = _VERIFY_ADAPTER_V10(
            adapter_v10_document,
            adapter_v10_verification_context["adapter_v9_document"],
            adapter_v10_verification_context["membership_gate_v2_document"],
            adapter_v9_verification_context=adapter_v10_verification_context[
                "adapter_v9_verification_context"
            ],
            membership_gate_v2_verification_context=(
                adapter_v10_verification_context[
                    "membership_gate_v2_verification_context"
                ]
            ),
        )
        if not _presentation_receipt_valid(
            presentation_receipt, presentation_v10_document
        ):
            return None
        if not _adapter_receipt_valid(adapter_receipt, adapter_v10_document):
            return None
        presentation_source = presentation_v10_document["source"]
        adapter_source = adapter_v10_document["source"]
        presentation_common = presentation_v10_document[
            "common_observation_summary"
        ]
        adapter_summary = adapter_v10_document["summary"]
        membership_context = adapter_v10_verification_context[
            "membership_gate_v2_verification_context"
        ]
        membership_document = adapter_v10_verification_context[
            "membership_gate_v2_document"
        ]
        shared_adapter_document = strict_json_contract_equal(
            presentation_v10_verification_context["adapter_v9_document"],
            adapter_v10_verification_context["adapter_v9_document"],
        )
        cross_bound = (
            shared_adapter_document
            and presentation_source["adapter_v9_hash"]
            == adapter_source["adapter_v9_hash"]
            and presentation_source["basis_preregistration_hash"]
            == adapter_source["basis_preregistration_hash"]
            and presentation_source["basis_evidence_hash"]
            == adapter_source["basis_evidence_hash"]
            and presentation_source["common_observation_basis_gate_v1_hash"]
            == adapter_source["basis_gate_v1_hash"]
            and presentation_source["edge_gate_v1_hash"]
            == adapter_source["edge_gate_v1_hash"]
            and presentation_source["cluster_partition_hash"]
            == adapter_source["cluster_partition_hash"]
            and presentation_source["trade_identity_hash"]
            == adapter_source["trade_identity_hash"]
            and presentation_source["common_sample_set_hash"]
            == adapter_source["common_sample_set_hash"]
            == adapter_source["common_observation_membership_hash"]
            and presentation_common["common_sample_count"]
            == adapter_summary["common_sample_count"]
            and presentation_common["edge_pair_count"]
            == adapter_summary["edge_pair_count"]
            and presentation_common["pair_count_matching_common_sample_count"]
            == adapter_summary["pair_count_matching_common_sample_count"]
            and adapter_source["membership_gate_v2_hash"]
            == membership_document[
                "common_observation_membership_gate_v2_hash"
            ]
            and adapter_source["membership_preregistration_hash"]
            == membership_context["membership_preregistration"][
                "membership_preregistration_hash"
            ]
            and adapter_source["membership_evidence_hash"]
            == membership_context["membership_evidence"]["membership_evidence_hash"]
            and adapter_source["observation_identifier_scheme_hash"]
            == membership_context["membership_preregistration"][
                "observation_identifier_scheme_hash"
            ]
            == membership_context["membership_evidence"][
                "observation_identifier_scheme_hash"
            ]
            and adapter_source["common_observation_membership_hash"]
            == membership_document["source"][
                "common_observation_membership_hash"
            ]
        )
    except (KeyError, TypeError, ValueError):
        return None
    if not cross_bound:
        return None
    return presentation_receipt, adapter_receipt


def build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_v11(
    presentation_v10_document: Any,
    adapter_v10_document: Any,
    *,
    presentation_v10_verification_context: Any,
    adapter_v10_verification_context: Any,
) -> dict[str, Any]:
    receipts = _exact_context(
        presentation_v10_document,
        adapter_v10_document,
        presentation_v10_verification_context=(
            presentation_v10_verification_context
        ),
        adapter_v10_verification_context=adapter_v10_verification_context,
    )
    if receipts is None:
        return _unknown()

    presentation_local_status = presentation_v10_document["local_decision"][
        "joint_status"
    ]
    adapter_status = receipts[1]["adapter_v10_status"]
    membership_status = adapter_v10_document["component_states"][
        "common_observation_membership_gate_v2_status"
    ]
    local_blocked = (
        presentation_local_status == BLOCK_STATUS or adapter_status == BLOCK_STATUS
    )
    local_decision = {
        "adapter_v10_decision": adapter_v10_document["decision"],
        "adapter_v10_status": adapter_status,
        "adapter_v9_decision": adapter_v10_document["component_states"][
            "adapter_v9_decision"
        ],
        "adapter_v9_status": adapter_v10_document["component_states"][
            "adapter_v9_status"
        ],
        "common_observation_basis_gate_v1_decision": adapter_v10_document[
            "component_states"
        ]["common_observation_basis_gate_v1_decision"],
        "common_observation_basis_gate_v1_status": adapter_v10_document[
            "component_states"
        ]["common_observation_basis_gate_v1_status"],
        "common_observation_membership_gate_v2_decision": adapter_v10_document[
            "component_states"
        ]["common_observation_membership_gate_v2_decision"],
        "common_observation_membership_gate_v2_status": membership_status,
        "edge_gate_v1_decision": adapter_v10_document["component_states"][
            "edge_gate_v1_decision"
        ],
        "edge_gate_v1_status": adapter_v10_document["component_states"][
            "edge_gate_v1_status"
        ],
        "joint_decision": (
            "BLOCK_COMMON_OBSERVATION_MEMBERSHIP_LOCAL_RESEARCH_PRESENTATION_V11"
            if local_blocked
            else "PASS_COMMON_OBSERVATION_MEMBERSHIP_LOCAL_RESEARCH_PRESENTATION_V11"
        ),
        "joint_status": BLOCK_STATUS if local_blocked else PASS_STATUS,
        "presentation_v10_joint_decision": presentation_v10_document[
            "local_decision"
        ]["joint_decision"],
        "presentation_v10_joint_status": presentation_local_status,
    }
    gaps = {
        "adapter_v10_blocker_count": len(adapter_v10_document["blockers"]),
        "local_blocker_count": int(local_blocked),
        "membership_gate_v2_blocker_count": int(
            membership_status == BLOCK_STATUS
        ),
        "presentation_blocker_count": len(PRESENTATION_BLOCKERS),
        "presentation_blockers": list(PRESENTATION_BLOCKERS),
        "presentation_v10_local_blocker_count": presentation_v10_document[
            "gaps"
        ]["local_blocker_count"],
        "source_failure": None,
    }
    adapter_source = adapter_v10_document["source"]
    presentation_source = presentation_v10_document["source"]
    source = {
        "adapter_v10_hash": adapter_v10_document["adapter_v10_hash"],
        "adapter_v10_implementation_sha256": ADAPTER_V10_IMPLEMENTATION_SHA256,
        "adapter_v9_hash": adapter_source["adapter_v9_hash"],
        "basis_evidence_hash": adapter_source["basis_evidence_hash"],
        "basis_preregistration_hash": adapter_source["basis_preregistration_hash"],
        "cluster_partition_hash": adapter_source["cluster_partition_hash"],
        "common_observation_basis_gate_v1_hash": adapter_source[
            "basis_gate_v1_hash"
        ],
        "common_observation_membership_hash": adapter_source[
            "common_observation_membership_hash"
        ],
        "common_sample_set_hash": adapter_source["common_sample_set_hash"],
        "edge_evidence_hash": adapter_source["edge_evidence_hash"],
        "edge_gate_v1_hash": adapter_source["edge_gate_v1_hash"],
        "edge_preregistration_hash": adapter_source["edge_preregistration_hash"],
        "membership_evidence_hash": adapter_source["membership_evidence_hash"],
        "membership_gate_v2_hash": adapter_source["membership_gate_v2_hash"],
        "membership_gate_v2_implementation_sha256": (
            MEMBERSHIP_GATE_V2_IMPLEMENTATION_SHA256
        ),
        "membership_preregistration_hash": adapter_source[
            "membership_preregistration_hash"
        ],
        "observation_identifier_scheme_hash": adapter_source[
            "observation_identifier_scheme_hash"
        ],
        "presentation_v10_hash": presentation_v10_document[
            "presentation_v10_hash"
        ],
        "presentation_v10_implementation_sha256": (
            PRESENTATION_V10_IMPLEMENTATION_SHA256
        ),
        "presentation_v9_hash": presentation_source["presentation_v9_hash"],
        "state": "EXACT_PRESENTATION_V10_AND_ADAPTER_V10",
        "strict_canonical_implementation_sha256": (
            STRICT_CANONICAL_IMPLEMENTATION_SHA256
        ),
        "trade_identity_hash": adapter_source["trade_identity_hash"],
    }
    adapter_summary = adapter_v10_document["summary"]
    membership_summary = {
        "all_pair_membership_hashes_match_common": (
            adapter_summary["membership_hash_match_pair_count"]
            == adapter_summary["registered_membership_pair_count"]
        ),
        "all_pair_sample_counts_match_common": (
            adapter_summary["commitment_sample_count_match_pair_count"]
            == adapter_summary["registered_membership_pair_count"]
            and adapter_summary["edge_sample_count_match_pair_count"]
            == adapter_summary["registered_membership_pair_count"]
        ),
        "common_sample_count": adapter_summary["common_sample_count"],
        "edge_pair_count": adapter_summary["edge_pair_count"],
        "expected_common_sample_count": adapter_summary[
            "expected_common_sample_count"
        ],
        "membership_commitment_only": True,
        "membership_hash_match_pair_count": adapter_summary[
            "membership_hash_match_pair_count"
        ],
        "raw_observation_ids_embedded": False,
        "raw_samples_recomputed": False,
        "registered_pair_count": adapter_summary[
            "registered_membership_pair_count"
        ],
        "submitted_commitment_pair_count": adapter_summary[
            "submitted_commitment_pair_count"
        ],
    }
    return _sealed_presentation(
        source_known=True,
        local_blocked=local_blocked,
        decision="BLOCK_OUTER_PRESENTATION_V11_AUTHORITY_UNCHANGED",
        gaps=gaps,
        local_decision=local_decision,
        source=source,
        risk_summary=deepcopy(presentation_v10_document["risk_summary"]),
        multi_window_summary=deepcopy(
            presentation_v10_document["multi_window_summary"]
        ),
        edge_uncertainty_summary=deepcopy(
            presentation_v10_document["edge_uncertainty_summary"]
        ),
        common_observation_summary=deepcopy(
            presentation_v10_document["common_observation_summary"]
        ),
        membership_summary=membership_summary,
    )


def verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_v11(
    document: Any,
    presentation_v10_document: Any,
    adapter_v10_document: Any,
    *,
    presentation_v10_verification_context: Any,
    adapter_v10_verification_context: Any,
) -> dict[str, Any]:
    rebuilt = build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_v11(
        presentation_v10_document,
        adapter_v10_document,
        presentation_v10_verification_context=(
            presentation_v10_verification_context
        ),
        adapter_v10_verification_context=adapter_v10_verification_context,
    )
    exact = strict_json_contract_equal(document, rebuilt)
    source_known = exact and rebuilt["facts"]["cross_bindings_verified"] is True
    return {
        "blockers": [] if source_known else ["PRESENTATION_V11_EXACT_REBUILD_FAILED"],
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_consumer_activation_allowed": False,
        "presentation_v11_exactly_verified": source_known,
        "presentation_v11_hash": (
            rebuilt["presentation_v11_hash"] if source_known else None
        ),
        "runtime_gate_activation_allowed": False,
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": PASS_STATUS if source_known else BLOCK_STATUS,
        "writer_allowed": False,
    }
