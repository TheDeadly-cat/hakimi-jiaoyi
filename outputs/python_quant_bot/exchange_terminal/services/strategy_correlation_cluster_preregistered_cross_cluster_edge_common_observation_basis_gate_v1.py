"""Preregistered common-observation provenance gate for cross-cluster edges.

The gate does not recompute correlations or inspect raw samples. It binds an
observation-policy commitment and one realized common-sample-set commitment to
an exactly verified edge-uncertainty gate, and requires every pair summary to
declare the same common sample count. It is isolated, research-only, and grants
no runtime, writer, paper, live, or current authority.
"""

from __future__ import annotations

from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_gate_v1
    as edge_gate_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-preregistered-cross-cluster-edge-common-"
    "observation-basis-preregistration-v1"
)
EVIDENCE_SCHEMA_VERSION = (
    "strategy-correlation-cluster-preregistered-cross-cluster-edge-common-"
    "observation-basis-evidence-v1"
)
SCHEMA_VERSION = (
    "strategy-correlation-cluster-preregistered-cross-cluster-edge-common-"
    "observation-basis-gate-v1"
)
VERIFICATION_SCHEMA_VERSION = SCHEMA_VERSION + "-verification-v1"
STATIC_FINGERPRINT = (
    "20260823-preregistered-cross-cluster-edge-common-observation-basis-"
    "gate-v1-unmounted-lock-1"
)
EDGE_GATE_V1_IMPLEMENTATION_SHA256 = (
    "d01fcfc8391052da4a113dd739ff778029e16708cc794b489819881d7b995b2a"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
PASS_STATUS = "PASS"
BLOCK_STATUS = "BLOCK"
UNKNOWN_STATUS = "UNKNOWN"

_VERIFY_EDGE_GATE = (
    edge_gate_v1.verify_strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_gate_v1
)
_AUTHORITY_KEYS = {
    "current_admission_allowed",
    "descriptive_only",
    "live_order_allowed",
    "local_research_gate_only",
    "paper_authorized",
    "runtime_gate_activation_allowed",
    "writer_allowed",
}
_PREREGISTRATION_KEYS = {
    "authority",
    "cluster_partition_hash",
    "edge_preregistration_hash",
    "minimum_common_sample_count",
    "observation_policy_hash",
    "preregistration_hash",
    "registration_sequence",
    "schema_version",
    "trade_identity_hash",
}
_EVIDENCE_KEYS = {
    "cluster_partition_hash",
    "common_sample_count",
    "common_sample_set_hash",
    "edge_evidence_hash",
    "evidence_hash",
    "evidence_sequence",
    "observation_policy_hash",
    "schema_version",
    "trade_identity_hash",
}
_EDGE_RECEIPT_KEYS = {
    "blockers",
    "current_admission_allowed",
    "edge_uncertainty_gate_v1_exactly_verified",
    "edge_uncertainty_gate_v1_hash",
    "gate_decision",
    "gate_status",
    "live_order_allowed",
    "paper_authorized",
    "runtime_gate_activation_allowed",
    "schema_version",
    "source_known",
    "status",
    "writer_allowed",
}


class CommonObservationBasisContractError(ValueError):
    """Raised when a builder receives a malformed contract input."""


def _exact_keys(value: Any, expected: set[str]) -> bool:
    return type(value) is dict and set(value) == expected


def _is_hash(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_positive_int(value: Any) -> bool:
    return type(value) is int and not isinstance(value, bool) and value > 0


def _authority() -> dict[str, bool]:
    return {
        "current_admission_allowed": False,
        "descriptive_only": True,
        "live_order_allowed": False,
        "local_research_gate_only": True,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
    }


def _authority_valid(value: Any) -> bool:
    return (
        _exact_keys(value, _AUTHORITY_KEYS)
        and value == _authority()
    )


def _require_hash(name: str, value: Any) -> str:
    if not _is_hash(value):
        raise CommonObservationBasisContractError(f"{name} must be a lowercase SHA-256")
    return value


def _require_positive_int(name: str, value: Any) -> int:
    if not _is_positive_int(value):
        raise CommonObservationBasisContractError(f"{name} must be a positive integer")
    return value


def build_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_basis_preregistration_v1(
    *,
    trade_identity_hash: Any,
    cluster_partition_hash: Any,
    edge_preregistration_hash: Any,
    observation_policy_hash: Any,
    registration_sequence: Any,
    minimum_common_sample_count: Any,
) -> dict[str, Any]:
    """Seal the policy and edge-preregistration commitment before evidence."""
    document = {
        "authority": _authority(),
        "cluster_partition_hash": _require_hash(
            "cluster_partition_hash", cluster_partition_hash
        ),
        "edge_preregistration_hash": _require_hash(
            "edge_preregistration_hash", edge_preregistration_hash
        ),
        "minimum_common_sample_count": _require_positive_int(
            "minimum_common_sample_count", minimum_common_sample_count
        ),
        "observation_policy_hash": _require_hash(
            "observation_policy_hash", observation_policy_hash
        ),
        "registration_sequence": _require_positive_int(
            "registration_sequence", registration_sequence
        ),
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "trade_identity_hash": _require_hash(
            "trade_identity_hash", trade_identity_hash
        ),
    }
    return seal_strict_canonical_document(document, "preregistration_hash")


def build_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_basis_evidence_v1(
    *,
    trade_identity_hash: Any,
    cluster_partition_hash: Any,
    edge_evidence_hash: Any,
    observation_policy_hash: Any,
    common_sample_set_hash: Any,
    common_sample_count: Any,
    evidence_sequence: Any,
) -> dict[str, Any]:
    """Seal one realized common-sample commitment for all edge pairs."""
    document = {
        "cluster_partition_hash": _require_hash(
            "cluster_partition_hash", cluster_partition_hash
        ),
        "common_sample_count": _require_positive_int(
            "common_sample_count", common_sample_count
        ),
        "common_sample_set_hash": _require_hash(
            "common_sample_set_hash", common_sample_set_hash
        ),
        "edge_evidence_hash": _require_hash(
            "edge_evidence_hash", edge_evidence_hash
        ),
        "evidence_sequence": _require_positive_int(
            "evidence_sequence", evidence_sequence
        ),
        "observation_policy_hash": _require_hash(
            "observation_policy_hash", observation_policy_hash
        ),
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "trade_identity_hash": _require_hash(
            "trade_identity_hash", trade_identity_hash
        ),
    }
    return seal_strict_canonical_document(document, "evidence_hash")


def _preregistration_valid(value: Any) -> bool:
    if not _exact_keys(value, _PREREGISTRATION_KEYS):
        return False
    try:
        expected = build_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_basis_preregistration_v1(
            trade_identity_hash=value["trade_identity_hash"],
            cluster_partition_hash=value["cluster_partition_hash"],
            edge_preregistration_hash=value["edge_preregistration_hash"],
            observation_policy_hash=value["observation_policy_hash"],
            registration_sequence=value["registration_sequence"],
            minimum_common_sample_count=value["minimum_common_sample_count"],
        )
    except (KeyError, TypeError, CommonObservationBasisContractError):
        return False
    return strict_json_contract_equal(value, expected) and _authority_valid(value["authority"])


def _evidence_valid(value: Any) -> bool:
    if not _exact_keys(value, _EVIDENCE_KEYS):
        return False
    try:
        expected = build_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_basis_evidence_v1(
            trade_identity_hash=value["trade_identity_hash"],
            cluster_partition_hash=value["cluster_partition_hash"],
            edge_evidence_hash=value["edge_evidence_hash"],
            observation_policy_hash=value["observation_policy_hash"],
            common_sample_set_hash=value["common_sample_set_hash"],
            common_sample_count=value["common_sample_count"],
            evidence_sequence=value["evidence_sequence"],
        )
    except (KeyError, TypeError, CommonObservationBasisContractError):
        return False
    return strict_json_contract_equal(value, expected)


def _edge_receipt_valid(value: Any, document: Any) -> bool:
    if not _exact_keys(value, _EDGE_RECEIPT_KEYS) or type(document) is not dict:
        return False
    return (
        value["schema_version"] == edge_gate_v1.VERIFICATION_SCHEMA_VERSION
        and value["status"] == PASS_STATUS
        and value["blockers"] == []
        and value["edge_uncertainty_gate_v1_exactly_verified"] is True
        and value["edge_uncertainty_gate_v1_hash"]
        == document.get("edge_uncertainty_gate_v1_hash")
        and value["gate_status"] == document.get("status")
        and value["gate_decision"] == document.get("decision")
        and value["source_known"] is True
        and value["current_admission_allowed"] is False
        and value["live_order_allowed"] is False
        and value["paper_authorized"] is False
        and value["runtime_gate_activation_allowed"] is False
        and value["writer_allowed"] is False
    )


def _policy() -> dict[str, Any]:
    return {
        "common_sample_count_action": "BLOCK_IF_BELOW_PREREGISTERED_MINIMUM",
        "edge_gate_block_action": "PRESERVE_BLOCK",
        "observation_policy_binding": "EXACT_HASH_MATCH",
        "pair_sample_count_action": "BLOCK_IF_NOT_EQUAL_TO_COMMON_COUNT",
        "provenance_is_not_raw_sample_recomputation": True,
        "risk_reduction_is_not_execution_authority": True,
    }


def _unknown(reason: str) -> dict[str, Any]:
    document = {
        "authority": _authority(),
        "blockers": [reason],
        "decision": "UNKNOWN_COMMON_OBSERVATION_BASIS",
        "facts": {
            "all_pair_sample_counts_match": False,
            "common_sample_set_declared": False,
            "edge_gate_v1_exactly_verified": False,
            "historical_market_data_accessed": False,
            "observation_policy_cross_bound": False,
            "pair_sample_counts_checked": False,
            "profitability_proven": False,
            "provenance_declaration_only": True,
            "raw_samples_recomputed": False,
            "runtime_assets_accessed": False,
            "source_documents_embedded": False,
        },
        "policy": _policy(),
        "schema_version": SCHEMA_VERSION,
        "source": {
            "basis_evidence_hash": None,
            "basis_preregistration_hash": None,
            "cluster_partition_hash": None,
            "common_sample_set_hash": None,
            "edge_evidence_hash": None,
            "edge_gate_v1_hash": None,
            "edge_gate_v1_implementation_sha256": EDGE_GATE_V1_IMPLEMENTATION_SHA256,
            "edge_preregistration_hash": None,
            "observation_policy_hash": None,
            "strict_canonical_implementation_sha256": STRICT_CANONICAL_IMPLEMENTATION_SHA256,
            "trade_identity_hash": None,
        },
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": UNKNOWN_STATUS,
        "summary": None,
    }
    return seal_strict_canonical_document(
        document, "common_observation_basis_gate_v1_hash"
    )


def evaluate_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_basis_gate_v1(
    preregistration: Any,
    evidence: Any,
    edge_gate_v1_document: Any,
    *,
    edge_preregistration: Any,
    edge_evidence: Any,
    expected_preregistration_hash: Any,
) -> dict[str, Any]:
    """Evaluate exact provenance bindings without reading raw observations."""
    if not _preregistration_valid(preregistration) or not _evidence_valid(evidence):
        return _unknown("BASIS_PREREGISTRATION_OR_EVIDENCE_INVALID")
    if (
        not _is_hash(expected_preregistration_hash)
        or expected_preregistration_hash != preregistration["preregistration_hash"]
    ):
        return _unknown("EXPECTED_BASIS_PREREGISTRATION_HASH_MISMATCH")
    if type(edge_preregistration) is not dict or type(edge_evidence) is not dict:
        return _unknown("EDGE_VERIFICATION_CONTEXT_INVALID")
    try:
        edge_receipt = _VERIFY_EDGE_GATE(
            edge_gate_v1_document,
            edge_preregistration,
            edge_evidence,
            expected_preregistration_hash=edge_preregistration[
                "preregistration_hash"
            ],
        )
    except (KeyError, TypeError, ValueError):
        edge_receipt = None
    if not _edge_receipt_valid(edge_receipt, edge_gate_v1_document):
        return _unknown("EDGE_GATE_V1_EXACT_REBUILD_FAILED")

    try:
        edge_source = edge_gate_v1_document["source"]
        identity_bound = (
            preregistration["trade_identity_hash"]
            == evidence["trade_identity_hash"]
            == edge_preregistration["trade_identity_hash"]
            == edge_evidence["trade_identity_hash"]
            == edge_source["trade_identity_hash"]
        )
        partition_bound = (
            preregistration["cluster_partition_hash"]
            == evidence["cluster_partition_hash"]
            == edge_preregistration["cluster_partition_hash"]
            == edge_evidence["cluster_partition_hash"]
            == edge_source["cluster_partition_hash"]
        )
        edge_preregistration_bound = (
            preregistration["edge_preregistration_hash"]
            == edge_preregistration["preregistration_hash"]
            == edge_source["preregistration_hash"]
        )
        edge_evidence_bound = (
            evidence["edge_evidence_hash"]
            == edge_evidence["evidence_hash"]
            == edge_source["evidence_hash"]
        )
        policy_bound = (
            preregistration["observation_policy_hash"]
            == evidence["observation_policy_hash"]
        )
        sequence_bound = (
            preregistration["registration_sequence"]
            == edge_preregistration["registration_sequence"]
            and evidence["evidence_sequence"] == edge_evidence["evidence_sequence"]
            and evidence["evidence_sequence"]
            > preregistration["registration_sequence"]
        )
        edge_pairs = edge_evidence["pairs"]
        pair_counts = [pair["sample_count"] for pair in edge_pairs]
    except (KeyError, TypeError):
        return _unknown("EDGE_SOURCE_CONTRACT_INVALID")
    if not identity_bound:
        return _unknown("TRADE_IDENTITY_SPLICE")
    if not partition_bound:
        return _unknown("CLUSTER_PARTITION_SPLICE")
    if not edge_preregistration_bound:
        return _unknown("EDGE_PREREGISTRATION_HASH_SPLICE")
    if not edge_evidence_bound:
        return _unknown("EDGE_EVIDENCE_HASH_SPLICE")
    if not policy_bound:
        return _unknown("OBSERVATION_POLICY_HASH_SPLICE")
    if not sequence_bound:
        return _unknown("REGISTRATION_OR_EVIDENCE_SEQUENCE_SPLICE")
    if not pair_counts or not all(_is_positive_int(value) for value in pair_counts):
        return _unknown("EDGE_PAIR_SAMPLE_COUNTS_INVALID")

    common_count = evidence["common_sample_count"]
    matching_pair_count = sum(value == common_count for value in pair_counts)
    all_pair_counts_match = matching_pair_count == len(pair_counts)
    blockers: list[str] = []
    if edge_gate_v1_document["status"] == BLOCK_STATUS:
        blockers.append("EDGE_UNCERTAINTY_GATE_V1_BLOCKED")
    if common_count < preregistration["minimum_common_sample_count"]:
        blockers.append("COMMON_SAMPLE_COUNT_BELOW_PREREGISTERED_MINIMUM")
    if (
        preregistration["minimum_common_sample_count"]
        < edge_preregistration["minimum_sample_count"]
    ):
        blockers.append("COMMON_SAMPLE_MINIMUM_WEAKER_THAN_EDGE_MINIMUM")
    if not all_pair_counts_match:
        blockers.append("PAIR_SAMPLE_COUNTS_NOT_COMMON")

    status = BLOCK_STATUS if blockers else PASS_STATUS
    decision = (
        "BLOCK_COMMON_OBSERVATION_BASIS_PROVENANCE"
        if blockers
        else "PASS_COMMON_OBSERVATION_BASIS_PROVENANCE"
    )
    document = {
        "authority": _authority(),
        "blockers": blockers,
        "decision": decision,
        "facts": {
            "all_pair_sample_counts_match": all_pair_counts_match,
            "common_sample_set_declared": True,
            "edge_gate_v1_exactly_verified": True,
            "historical_market_data_accessed": False,
            "observation_policy_cross_bound": True,
            "pair_sample_counts_checked": True,
            "profitability_proven": False,
            "provenance_declaration_only": True,
            "raw_samples_recomputed": False,
            "runtime_assets_accessed": False,
            "source_documents_embedded": False,
        },
        "policy": _policy(),
        "schema_version": SCHEMA_VERSION,
        "source": {
            "basis_evidence_hash": evidence["evidence_hash"],
            "basis_preregistration_hash": preregistration["preregistration_hash"],
            "cluster_partition_hash": preregistration["cluster_partition_hash"],
            "common_sample_set_hash": evidence["common_sample_set_hash"],
            "edge_evidence_hash": evidence["edge_evidence_hash"],
            "edge_gate_v1_hash": edge_gate_v1_document[
                "edge_uncertainty_gate_v1_hash"
            ],
            "edge_gate_v1_implementation_sha256": EDGE_GATE_V1_IMPLEMENTATION_SHA256,
            "edge_preregistration_hash": preregistration[
                "edge_preregistration_hash"
            ],
            "observation_policy_hash": preregistration["observation_policy_hash"],
            "strict_canonical_implementation_sha256": STRICT_CANONICAL_IMPLEMENTATION_SHA256,
            "trade_identity_hash": preregistration["trade_identity_hash"],
        },
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "summary": {
            "common_sample_count": common_count,
            "edge_blocked_pair_count": edge_gate_v1_document["summary"][
                "blocked_pair_count"
            ],
            "edge_pair_count": len(pair_counts),
            "minimum_common_sample_count": preregistration[
                "minimum_common_sample_count"
            ],
            "pair_count_matching_common_sample_count": matching_pair_count,
            "verified_edge_pair_count": edge_gate_v1_document["summary"][
                "verified_pair_count"
            ],
        },
    }
    return seal_strict_canonical_document(
        document, "common_observation_basis_gate_v1_hash"
    )


def verify_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_basis_gate_v1(
    document: Any,
    preregistration: Any,
    evidence: Any,
    edge_gate_v1_document: Any,
    *,
    edge_preregistration: Any,
    edge_evidence: Any,
    expected_preregistration_hash: Any,
) -> dict[str, Any]:
    """Return a locked receipt for an exact evaluator rebuild."""
    try:
        expected = evaluate_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_basis_gate_v1(
            preregistration,
            evidence,
            edge_gate_v1_document,
            edge_preregistration=edge_preregistration,
            edge_evidence=edge_evidence,
            expected_preregistration_hash=expected_preregistration_hash,
        )
        exact = strict_json_contract_equal(document, expected)
    except (KeyError, TypeError, ValueError):
        expected = None
        exact = False
    known = bool(exact and expected and expected["status"] != UNKNOWN_STATUS)
    return {
        "blockers": [] if exact else ["COMMON_OBSERVATION_BASIS_EXACT_REBUILD_FAILED"],
        "common_observation_basis_gate_v1_exactly_verified": exact,
        "common_observation_basis_gate_v1_hash": (
            expected["common_observation_basis_gate_v1_hash"] if exact else None
        ),
        "current_admission_allowed": False,
        "gate_decision": expected["decision"] if exact else UNKNOWN_STATUS,
        "gate_status": expected["status"] if exact else UNKNOWN_STATUS,
        "live_order_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "source_known": known,
        "status": PASS_STATUS if exact else BLOCK_STATUS,
        "writer_allowed": False,
    }


__all__ = [
    "BLOCK_STATUS",
    "CommonObservationBasisContractError",
    "EDGE_GATE_V1_IMPLEMENTATION_SHA256",
    "EVIDENCE_SCHEMA_VERSION",
    "PASS_STATUS",
    "PREREGISTRATION_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "STRICT_CANONICAL_IMPLEMENTATION_SHA256",
    "UNKNOWN_STATUS",
    "VERIFICATION_SCHEMA_VERSION",
    "build_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_basis_evidence_v1",
    "build_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_basis_preregistration_v1",
    "evaluate_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_basis_gate_v1",
    "verify_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_basis_gate_v1",
]
