from __future__ import annotations

from copy import deepcopy
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_basis_gate_v1
    as basis_gate_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-preregistered-cross-cluster-edge-common-"
    "observation-membership-preregistration-v2"
)
EVIDENCE_SCHEMA_VERSION = (
    "strategy-correlation-cluster-preregistered-cross-cluster-edge-common-"
    "observation-membership-evidence-v2"
)
SCHEMA_VERSION = (
    "strategy-correlation-cluster-preregistered-cross-cluster-edge-common-"
    "observation-membership-gate-v2"
)
VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-preregistered-cross-cluster-edge-common-"
    "observation-membership-gate-v2-verification-v2"
)
STATIC_FINGERPRINT = (
    "20260823-preregistered-cross-cluster-edge-common-observation-membership-"
    "gate-v2-unmounted-lock-1"
)
BASIS_GATE_V1_IMPLEMENTATION_SHA256 = (
    "de56893e5413c182791761de2b15a5b3078275e6a587a624646dc7a2f38986f0"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
MEMBERSHIP_DIGEST_ALGORITHM = "SHA256_STRICT_CANONICAL_OBSERVATION_ID_SEQUENCE_V1"
MEMBERSHIP_ORDERING = "ASCENDING_UNIQUE_OBSERVATION_IDS_V1"
PASS_STATUS = "PASS"
BLOCK_STATUS = "BLOCK"
UNKNOWN_STATUS = "UNKNOWN"


class CommonObservationMembershipContractError(ValueError):
    pass


def _exact_keys(value: Any, expected: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == expected


def _is_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _is_sequence(value: Any) -> bool:
    return type(value) is int and value >= 0


def _is_positive_count(value: Any) -> bool:
    return type(value) is int and value > 0


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
    return strict_json_contract_equal(value, _authority())


def _sealed_document_valid(document: Any, hash_field: str) -> bool:
    if not isinstance(document, dict) or not _is_hash(document.get(hash_field)):
        return False
    try:
        unsigned = deepcopy(document)
        unsigned.pop(hash_field)
        rebuilt = seal_strict_canonical_document(unsigned, hash_field)
    except (KeyError, TypeError, ValueError):
        return False
    return strict_json_contract_equal(document, rebuilt)


def _pair_valid(pair: Any) -> bool:
    return (
        _exact_keys(pair, {"left_symbol", "right_symbol"})
        and isinstance(pair["left_symbol"], str)
        and isinstance(pair["right_symbol"], str)
        and bool(pair["left_symbol"])
        and pair["left_symbol"] < pair["right_symbol"]
    )


def _pair_commitment_valid(pair: Any) -> bool:
    return (
        _exact_keys(
            pair,
            {
                "left_symbol",
                "observation_membership_hash",
                "right_symbol",
                "sample_count",
            },
        )
        and isinstance(pair["left_symbol"], str)
        and isinstance(pair["right_symbol"], str)
        and bool(pair["left_symbol"])
        and pair["left_symbol"] < pair["right_symbol"]
        and _is_hash(pair["observation_membership_hash"])
        and _is_positive_count(pair["sample_count"])
    )


def _pair_keys(rows: list[dict[str, Any]]) -> list[tuple[str, str]]:
    return [(row["left_symbol"], row["right_symbol"]) for row in rows]


def _ordered_unique_pairs_valid(rows: Any, validator: Any) -> bool:
    if not isinstance(rows, list) or not rows or not all(validator(row) for row in rows):
        return False
    keys = _pair_keys(rows)
    return keys == sorted(keys) and len(keys) == len(set(keys))


def _preregistration_valid(document: Any) -> bool:
    return (
        _exact_keys(
            document,
            {
                "authority",
                "basis_preregistration_hash",
                "cluster_partition_hash",
                "edge_preregistration_hash",
                "expected_common_observation_membership_hash",
                "expected_common_sample_count",
                "membership_digest_algorithm",
                "membership_ordering",
                "membership_preregistration_hash",
                "observation_identifier_scheme_hash",
                "registered_pairs",
                "registration_sequence",
                "schema_version",
                "trade_identity_hash",
            },
        )
        and document["schema_version"] == PREREGISTRATION_SCHEMA_VERSION
        and _authority_valid(document["authority"])
        and all(
            _is_hash(document[key])
            for key in (
                "basis_preregistration_hash",
                "cluster_partition_hash",
                "edge_preregistration_hash",
                "expected_common_observation_membership_hash",
                "observation_identifier_scheme_hash",
                "trade_identity_hash",
            )
        )
        and _is_positive_count(document["expected_common_sample_count"])
        and document["membership_digest_algorithm"] == MEMBERSHIP_DIGEST_ALGORITHM
        and document["membership_ordering"] == MEMBERSHIP_ORDERING
        and _ordered_unique_pairs_valid(document["registered_pairs"], _pair_valid)
        and _is_sequence(document["registration_sequence"])
        and _sealed_document_valid(document, "membership_preregistration_hash")
    )


def _evidence_valid(document: Any) -> bool:
    return (
        _exact_keys(
            document,
            {
                "basis_evidence_hash",
                "basis_gate_v1_hash",
                "cluster_partition_hash",
                "common_observation_membership_hash",
                "common_sample_count",
                "edge_evidence_hash",
                "evidence_sequence",
                "membership_evidence_hash",
                "observation_identifier_scheme_hash",
                "pair_membership_commitments",
                "schema_version",
                "trade_identity_hash",
            },
        )
        and document["schema_version"] == EVIDENCE_SCHEMA_VERSION
        and all(
            _is_hash(document[key])
            for key in (
                "basis_evidence_hash",
                "basis_gate_v1_hash",
                "cluster_partition_hash",
                "common_observation_membership_hash",
                "edge_evidence_hash",
                "observation_identifier_scheme_hash",
                "trade_identity_hash",
            )
        )
        and _is_positive_count(document["common_sample_count"])
        and _ordered_unique_pairs_valid(
            document["pair_membership_commitments"], _pair_commitment_valid
        )
        and _is_sequence(document["evidence_sequence"])
        and _sealed_document_valid(document, "membership_evidence_hash")
    )


def build_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_membership_preregistration_v2(
    *,
    trade_identity_hash: Any,
    cluster_partition_hash: Any,
    basis_preregistration_hash: Any,
    edge_preregistration_hash: Any,
    observation_identifier_scheme_hash: Any,
    expected_common_observation_membership_hash: Any,
    expected_common_sample_count: Any,
    registered_pairs: Any,
    registration_sequence: Any,
) -> dict[str, Any]:
    document = {
        "authority": _authority(),
        "basis_preregistration_hash": basis_preregistration_hash,
        "cluster_partition_hash": cluster_partition_hash,
        "edge_preregistration_hash": edge_preregistration_hash,
        "expected_common_observation_membership_hash": (
            expected_common_observation_membership_hash
        ),
        "expected_common_sample_count": expected_common_sample_count,
        "membership_digest_algorithm": MEMBERSHIP_DIGEST_ALGORITHM,
        "membership_ordering": MEMBERSHIP_ORDERING,
        "observation_identifier_scheme_hash": observation_identifier_scheme_hash,
        "registered_pairs": deepcopy(registered_pairs),
        "registration_sequence": registration_sequence,
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "trade_identity_hash": trade_identity_hash,
    }
    try:
        sealed = seal_strict_canonical_document(document, "membership_preregistration_hash")
    except (TypeError, ValueError) as exc:
        raise CommonObservationMembershipContractError(str(exc)) from exc
    if not _preregistration_valid(sealed):
        raise CommonObservationMembershipContractError(
            "invalid common-observation membership preregistration-v2"
        )
    return sealed


def build_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_membership_evidence_v2(
    *,
    trade_identity_hash: Any,
    cluster_partition_hash: Any,
    basis_evidence_hash: Any,
    basis_gate_v1_hash: Any,
    edge_evidence_hash: Any,
    observation_identifier_scheme_hash: Any,
    common_observation_membership_hash: Any,
    common_sample_count: Any,
    pair_membership_commitments: Any,
    evidence_sequence: Any,
) -> dict[str, Any]:
    document = {
        "basis_evidence_hash": basis_evidence_hash,
        "basis_gate_v1_hash": basis_gate_v1_hash,
        "cluster_partition_hash": cluster_partition_hash,
        "common_observation_membership_hash": common_observation_membership_hash,
        "common_sample_count": common_sample_count,
        "edge_evidence_hash": edge_evidence_hash,
        "evidence_sequence": evidence_sequence,
        "observation_identifier_scheme_hash": observation_identifier_scheme_hash,
        "pair_membership_commitments": deepcopy(pair_membership_commitments),
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "trade_identity_hash": trade_identity_hash,
    }
    try:
        sealed = seal_strict_canonical_document(document, "membership_evidence_hash")
    except (TypeError, ValueError) as exc:
        raise CommonObservationMembershipContractError(str(exc)) from exc
    if not _evidence_valid(sealed):
        raise CommonObservationMembershipContractError(
            "invalid common-observation membership evidence-v2"
        )
    return sealed


def _policy() -> dict[str, Any]:
    return {
        "basis_gate_v1_block_action": "PRESERVE_BLOCK",
        "common_membership_hash_action": (
            "BLOCK_IF_NOT_EXACT_PREREGISTRATION_AND_PAIR_MATCH"
        ),
        "common_sample_count_action": (
            "BLOCK_IF_NOT_EXACT_PREREGISTRATION_AND_PAIR_MATCH"
        ),
        "membership_commitment_is_not_raw_sample_verification": True,
        "observation_identifier_scheme_binding": "EXACT_HASH_MATCH",
        "pair_set_action": "BLOCK_IF_NOT_EXACT_EDGE_EVIDENCE_SET",
        "risk_reduction_is_not_execution_authority": True,
    }


def _unknown_facts() -> dict[str, bool]:
    return {
        "all_pair_membership_hashes_match_common": False,
        "all_pair_sample_counts_match_common": False,
        "basis_gate_v1_exactly_verified": False,
        "expected_common_membership_hash_matched": False,
        "expected_common_sample_count_matched": False,
        "historical_market_data_accessed": False,
        "membership_commitment_is_not_raw_sample_verification": True,
        "membership_commitments_verified": False,
        "observation_identifier_scheme_cross_bound": False,
        "profitability_proven": False,
        "raw_observation_ids_embedded": False,
        "raw_samples_recomputed": False,
        "registered_pair_set_exactly_matched": False,
        "runtime_assets_accessed": False,
        "source_documents_embedded": False,
    }


def _source_unknown() -> dict[str, Any]:
    return {
        "basis_evidence_hash": None,
        "basis_gate_v1_hash": None,
        "basis_gate_v1_implementation_sha256": BASIS_GATE_V1_IMPLEMENTATION_SHA256,
        "basis_preregistration_hash": None,
        "cluster_partition_hash": None,
        "common_observation_membership_hash": None,
        "edge_evidence_hash": None,
        "edge_gate_v1_hash": None,
        "edge_preregistration_hash": None,
        "expected_common_observation_membership_hash": None,
        "membership_evidence_hash": None,
        "membership_preregistration_hash": None,
        "observation_identifier_scheme_hash": None,
        "strict_canonical_implementation_sha256": (
            STRICT_CANONICAL_IMPLEMENTATION_SHA256
        ),
        "trade_identity_hash": None,
    }


def _sealed_gate(
    *,
    status: str,
    decision: str,
    blockers: list[str],
    facts: dict[str, bool],
    source: dict[str, Any],
    summary: dict[str, int] | None,
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "authority": _authority(),
            "blockers": blockers,
            "decision": decision,
            "facts": facts,
            "policy": _policy(),
            "schema_version": SCHEMA_VERSION,
            "source": source,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": status,
            "summary": summary,
        },
        "common_observation_membership_gate_v2_hash",
    )


def _unknown(blocker: str = "COMMON_OBSERVATION_MEMBERSHIP_SOURCE_UNKNOWN") -> dict[str, Any]:
    return _sealed_gate(
        status=UNKNOWN_STATUS,
        decision="UNKNOWN_COMMON_OBSERVATION_MEMBERSHIP_COMMITMENTS",
        blockers=[blocker],
        facts=_unknown_facts(),
        source=_source_unknown(),
        summary=None,
    )


def _basis_receipt_valid(receipt: Any, basis_document: Any) -> bool:
    return (
        _exact_keys(
            receipt,
            {
                "blockers",
                "common_observation_basis_gate_v1_exactly_verified",
                "common_observation_basis_gate_v1_hash",
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
        and receipt["schema_version"] == basis_gate_v1.VERIFICATION_SCHEMA_VERSION
        and receipt["common_observation_basis_gate_v1_exactly_verified"] is True
        and receipt["source_known"] is True
        and receipt["status"] == PASS_STATUS
        and receipt["gate_status"] in {PASS_STATUS, BLOCK_STATUS}
        and receipt["gate_decision"] == basis_document["decision"]
        and receipt["common_observation_basis_gate_v1_hash"]
        == basis_document["common_observation_basis_gate_v1_hash"]
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
        and isinstance(receipt["blockers"], list)
        and all(isinstance(blocker, str) and blocker for blocker in receipt["blockers"])
    )


def _exact_context(
    membership_preregistration: Any,
    membership_evidence: Any,
    basis_gate_v1_document: Any,
    *,
    basis_preregistration: Any,
    basis_evidence: Any,
    edge_gate_v1_document: Any,
    edge_preregistration: Any,
    edge_evidence: Any,
    expected_membership_preregistration_hash: Any,
) -> dict[str, Any] | None:
    if (
        not _preregistration_valid(membership_preregistration)
        or not _evidence_valid(membership_evidence)
        or not _is_hash(expected_membership_preregistration_hash)
        or membership_preregistration["membership_preregistration_hash"]
        != expected_membership_preregistration_hash
    ):
        return None
    try:
        receipt = basis_gate_v1.verify_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_basis_gate_v1(
            basis_gate_v1_document,
            basis_preregistration,
            basis_evidence,
            edge_gate_v1_document,
            edge_preregistration=edge_preregistration,
            edge_evidence=edge_evidence,
            expected_preregistration_hash=basis_preregistration["preregistration_hash"],
        )
        if not _basis_receipt_valid(receipt, basis_gate_v1_document):
            return None
        structural_bindings = (
            membership_preregistration["trade_identity_hash"]
            == membership_evidence["trade_identity_hash"]
            == basis_preregistration["trade_identity_hash"]
            == basis_evidence["trade_identity_hash"]
            == edge_preregistration["trade_identity_hash"]
            == edge_evidence["trade_identity_hash"]
            and membership_preregistration["cluster_partition_hash"]
            == membership_evidence["cluster_partition_hash"]
            == basis_preregistration["cluster_partition_hash"]
            == basis_evidence["cluster_partition_hash"]
            == edge_preregistration["cluster_partition_hash"]
            and membership_preregistration["basis_preregistration_hash"]
            == basis_preregistration["preregistration_hash"]
            == basis_gate_v1_document["source"]["basis_preregistration_hash"]
            and membership_preregistration["edge_preregistration_hash"]
            == edge_preregistration["preregistration_hash"]
            == basis_preregistration["edge_preregistration_hash"]
            and membership_preregistration["registration_sequence"]
            == basis_preregistration["registration_sequence"]
            == edge_preregistration["registration_sequence"]
            and membership_evidence["basis_evidence_hash"]
            == basis_evidence["evidence_hash"]
            == basis_gate_v1_document["source"]["basis_evidence_hash"]
            and membership_evidence["basis_gate_v1_hash"]
            == basis_gate_v1_document["common_observation_basis_gate_v1_hash"]
            and membership_evidence["edge_evidence_hash"]
            == edge_evidence["evidence_hash"]
            == basis_evidence["edge_evidence_hash"]
            and membership_evidence["evidence_sequence"]
            == basis_evidence["evidence_sequence"]
            == edge_evidence["evidence_sequence"]
            and membership_preregistration["observation_identifier_scheme_hash"]
            == membership_evidence["observation_identifier_scheme_hash"]
            and membership_evidence["common_observation_membership_hash"]
            == basis_evidence["common_sample_set_hash"]
            and membership_evidence["common_sample_count"]
            == basis_evidence["common_sample_count"]
        )
    except (KeyError, TypeError, ValueError):
        return None
    if not structural_bindings:
        return None
    return {"basis_receipt": receipt}


def evaluate_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_membership_gate_v2(
    membership_preregistration: Any,
    membership_evidence: Any,
    basis_gate_v1_document: Any,
    *,
    basis_preregistration: Any,
    basis_evidence: Any,
    edge_gate_v1_document: Any,
    edge_preregistration: Any,
    edge_evidence: Any,
    expected_membership_preregistration_hash: Any,
) -> dict[str, Any]:
    context = _exact_context(
        membership_preregistration,
        membership_evidence,
        basis_gate_v1_document,
        basis_preregistration=basis_preregistration,
        basis_evidence=basis_evidence,
        edge_gate_v1_document=edge_gate_v1_document,
        edge_preregistration=edge_preregistration,
        edge_evidence=edge_evidence,
        expected_membership_preregistration_hash=(
            expected_membership_preregistration_hash
        ),
    )
    if context is None:
        return _unknown()

    try:
        registered_pairs = membership_preregistration["registered_pairs"]
        commitments = membership_evidence["pair_membership_commitments"]
        edge_pairs = edge_evidence["pairs"]
        registered_keys = _pair_keys(registered_pairs)
        commitment_keys = _pair_keys(commitments)
        edge_keys = _pair_keys(edge_pairs)
        pair_set_exact = registered_keys == commitment_keys == edge_keys
        common_membership_hash = membership_evidence[
            "common_observation_membership_hash"
        ]
        common_sample_count = membership_evidence["common_sample_count"]
        expected_hash_match = (
            common_membership_hash
            == membership_preregistration[
                "expected_common_observation_membership_hash"
            ]
        )
        expected_count_match = (
            common_sample_count
            == membership_preregistration["expected_common_sample_count"]
        )
        membership_match_count = sum(
            row["observation_membership_hash"] == common_membership_hash
            for row in commitments
        )
        commitment_sample_match_count = sum(
            row["sample_count"] == common_sample_count for row in commitments
        )
        edge_sample_match_count = 0
        if pair_set_exact:
            edge_sample_match_count = sum(
                commitment["sample_count"]
                == edge_pair["sample_count"]
                == common_sample_count
                for commitment, edge_pair in zip(commitments, edge_pairs, strict=True)
            )
        all_memberships_match = (
            pair_set_exact and membership_match_count == len(registered_pairs)
        )
        all_sample_counts_match = (
            pair_set_exact
            and commitment_sample_match_count == len(registered_pairs)
            and edge_sample_match_count == len(registered_pairs)
        )
        membership_commitments_verified = (
            pair_set_exact
            and expected_hash_match
            and expected_count_match
            and all_memberships_match
            and all_sample_counts_match
        )
    except (KeyError, TypeError, ValueError):
        return _unknown()

    blockers: list[str] = []
    if context["basis_receipt"]["gate_status"] == BLOCK_STATUS:
        blockers.append("COMMON_OBSERVATION_BASIS_GATE_V1_BLOCKED")
    if not pair_set_exact:
        blockers.append("REGISTERED_MEMBERSHIP_PAIR_SET_MISMATCH")
    if not expected_hash_match:
        blockers.append("PREREGISTERED_COMMON_MEMBERSHIP_HASH_MISMATCH")
    if not all_memberships_match:
        blockers.append("PAIR_MEMBERSHIP_COMMITMENT_MISMATCH")
    if not expected_count_match:
        blockers.append("PREREGISTERED_COMMON_SAMPLE_COUNT_MISMATCH")
    if not all_sample_counts_match:
        blockers.append("PAIR_MEMBERSHIP_SAMPLE_COUNT_MISMATCH")

    status = PASS_STATUS if not blockers else BLOCK_STATUS
    decision = (
        "PASS_COMMON_OBSERVATION_MEMBERSHIP_COMMITMENTS"
        if status == PASS_STATUS
        else "BLOCK_COMMON_OBSERVATION_MEMBERSHIP_COMMITMENTS"
    )
    facts = {
        "all_pair_membership_hashes_match_common": all_memberships_match,
        "all_pair_sample_counts_match_common": all_sample_counts_match,
        "basis_gate_v1_exactly_verified": True,
        "expected_common_membership_hash_matched": expected_hash_match,
        "expected_common_sample_count_matched": expected_count_match,
        "historical_market_data_accessed": False,
        "membership_commitment_is_not_raw_sample_verification": True,
        "membership_commitments_verified": membership_commitments_verified,
        "observation_identifier_scheme_cross_bound": True,
        "profitability_proven": False,
        "raw_observation_ids_embedded": False,
        "raw_samples_recomputed": False,
        "registered_pair_set_exactly_matched": pair_set_exact,
        "runtime_assets_accessed": False,
        "source_documents_embedded": False,
    }
    source = {
        "basis_evidence_hash": membership_evidence["basis_evidence_hash"],
        "basis_gate_v1_hash": membership_evidence["basis_gate_v1_hash"],
        "basis_gate_v1_implementation_sha256": BASIS_GATE_V1_IMPLEMENTATION_SHA256,
        "basis_preregistration_hash": membership_preregistration[
            "basis_preregistration_hash"
        ],
        "cluster_partition_hash": membership_preregistration[
            "cluster_partition_hash"
        ],
        "common_observation_membership_hash": common_membership_hash,
        "edge_evidence_hash": membership_evidence["edge_evidence_hash"],
        "edge_gate_v1_hash": basis_gate_v1_document["source"]["edge_gate_v1_hash"],
        "edge_preregistration_hash": membership_preregistration[
            "edge_preregistration_hash"
        ],
        "expected_common_observation_membership_hash": membership_preregistration[
            "expected_common_observation_membership_hash"
        ],
        "membership_evidence_hash": membership_evidence[
            "membership_evidence_hash"
        ],
        "membership_preregistration_hash": membership_preregistration[
            "membership_preregistration_hash"
        ],
        "observation_identifier_scheme_hash": membership_preregistration[
            "observation_identifier_scheme_hash"
        ],
        "strict_canonical_implementation_sha256": (
            STRICT_CANONICAL_IMPLEMENTATION_SHA256
        ),
        "trade_identity_hash": membership_preregistration["trade_identity_hash"],
    }
    summary = {
        "basis_common_sample_count": basis_evidence["common_sample_count"],
        "commitment_sample_count_match_pair_count": commitment_sample_match_count,
        "edge_pair_count": len(edge_pairs),
        "edge_sample_count_match_pair_count": edge_sample_match_count,
        "expected_common_sample_count": membership_preregistration[
            "expected_common_sample_count"
        ],
        "membership_hash_match_pair_count": membership_match_count,
        "registered_pair_count": len(registered_pairs),
        "submitted_commitment_pair_count": len(commitments),
    }
    return _sealed_gate(
        status=status,
        decision=decision,
        blockers=blockers,
        facts=facts,
        source=source,
        summary=summary,
    )


def verify_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_membership_gate_v2(
    document: Any,
    membership_preregistration: Any,
    membership_evidence: Any,
    basis_gate_v1_document: Any,
    *,
    basis_preregistration: Any,
    basis_evidence: Any,
    edge_gate_v1_document: Any,
    edge_preregistration: Any,
    edge_evidence: Any,
    expected_membership_preregistration_hash: Any,
) -> dict[str, Any]:
    rebuilt = evaluate_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_membership_gate_v2(
        membership_preregistration,
        membership_evidence,
        basis_gate_v1_document,
        basis_preregistration=basis_preregistration,
        basis_evidence=basis_evidence,
        edge_gate_v1_document=edge_gate_v1_document,
        edge_preregistration=edge_preregistration,
        edge_evidence=edge_evidence,
        expected_membership_preregistration_hash=(
            expected_membership_preregistration_hash
        ),
    )
    exact = strict_json_contract_equal(document, rebuilt)
    source_known = exact and rebuilt["status"] != UNKNOWN_STATUS
    if source_known:
        verification_status = PASS_STATUS
        gate_status = rebuilt["status"]
        gate_hash = rebuilt["common_observation_membership_gate_v2_hash"]
        decision = rebuilt["decision"]
        blockers = deepcopy(rebuilt["blockers"])
    else:
        verification_status = UNKNOWN_STATUS
        gate_status = UNKNOWN_STATUS
        gate_hash = None
        decision = "UNKNOWN_COMMON_OBSERVATION_MEMBERSHIP_COMMITMENTS"
        blockers = ["COMMON_OBSERVATION_MEMBERSHIP_GATE_V2_EXACT_REBUILD_FAILED"]
    return {
        "blockers": blockers,
        "common_observation_membership_gate_v2_exactly_verified": source_known,
        "common_observation_membership_gate_v2_hash": gate_hash,
        "current_admission_allowed": False,
        "gate_decision": decision,
        "gate_status": gate_status,
        "live_order_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "source_known": source_known,
        "status": verification_status,
        "writer_allowed": False,
    }
