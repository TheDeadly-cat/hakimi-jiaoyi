"""Unmounted veto for pseudo multi-window correlation evidence.

ADR0345 verifies distinct window labels and distinct uncertainty-audit hashes,
but those facts do not establish distinct observation memberships. This gate
exactly rebuilds ADR0345, binds one ordered common-observation commitment to
each verified window, and rejects excessive cross-window overlap. It consumes
only caller-supplied synthetic observation identifiers and never reads market
or runtime assets.
"""

from __future__ import annotations

from copy import deepcopy
from hmac import compare_digest
from itertools import combinations
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_cluster_gate_v1
    as multi_window_gate_v1,
)
from exchange_terminal.services.strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_membership_gate_v2 import (
    MEMBERSHIP_DIGEST_ALGORITHM,
    MEMBERSHIP_ORDERING,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid import (
    AUDIT_SCHEMA_VERSION as DATE_GRID_AUDIT_SCHEMA_VERSION,
    DATE_GRID_RULE,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-multi-window-observation-overlap-"
    "preregistration-v1"
)
EVIDENCE_SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-multi-window-observation-overlap-"
    "evidence-v1"
)
GATE_SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-multi-window-observation-overlap-gate-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-uncertainty-multi-window-observation-"
    "overlap-gate-v1-synthetic-unmounted-veto-lock-1"
)
MULTI_WINDOW_GATE_V1_IMPLEMENTATION_SHA256 = (
    "4c64530efa76730404b7441ecdb9dab9ee914c156116296eea21a54c47a5f9e2"
)
BASIS_POINTS = 10_000
MAXIMUM_PAIRWISE_JACCARD_OVERLAP_BPS = 5_000
MINIMUM_UNIQUE_OBSERVATION_CONTRIBUTION_BPS = 2_500
MINIMUM_OBSERVATIONS_PER_WINDOW = 2
MAXIMUM_OBSERVATIONS_PER_WINDOW = 4_096
ACTIVATION_SEQUENCE = (
    "VERIFY_EXACT_ADR0345_PREREGISTRATION",
    "PREREGISTER_FIXED_OVERLAP_POLICY_BEFORE_EVIDENCE",
    "BIND_ONE_COMMON_OBSERVATION_MEMBERSHIP_TO_EACH_WINDOW",
    "VERIFY_EXACT_ADR0345_GATE_AND_WINDOW_AUDIT_ORDER",
    "MATCH_MEMBERSHIP_COUNTS_TO_VERIFIED_UNCERTAINTY_AUDITS",
    "REBUILD_ASCENDING_UNIQUE_MEMBERSHIP_DIGESTS",
    "COMPUTE_PAIRWISE_JACCARD_OVERLAP_WITH_CEILING_ROUNDING",
    "COMPUTE_PER_WINDOW_UNIQUE_CONTRIBUTION_WITH_FLOOR_ROUNDING",
    "VETO_PSEUDO_MULTI_WINDOW_EVIDENCE_BEFORE_EFFECTIVE_BUDGET",
    "BIND_TRUSTED_MEMBERSHIP_ISSUER_BEFORE_ANY_ACTIVATION",
)

_BASE_ACTIVATION_BLOCKERS = (
    "UNMOUNTED_CANDIDATE",
    "NO_RUNTIME_CONSUMER_BOUND",
    "OBSERVATION_MEMBERSHIP_ISSUER_BINDING_UNPROVEN",
    "NO_MARKET_RUNTIME_EVIDENCE",
    "PAPER_LIVE_UNAUTHORIZED",
)
_AUTHORITY = {
    "research_evidence_only": True,
    "current_admission_allowed": False,
    "effective_budget_activation_allowed": False,
    "http_registration_allowed": False,
    "runtime_activation_allowed": False,
    "writer_allowed": False,
    "paper_authorized": False,
    "live_order_allowed": False,
}
_PREREGISTRATION_FIELDS = frozenset(
    {
        "activation_sequence",
        "authority",
        "cluster_partition_hash",
        "date_grid_audit_schema_version",
        "date_grid_rule",
        "expected_window_count",
        "expected_windows",
        "gate_contract_hash",
        "maximum_pairwise_jaccard_overlap_bps",
        "membership_digest_algorithm",
        "membership_ordering",
        "minimum_unique_observation_contribution_bps",
        "multi_window_gate_v1_implementation_sha256",
        "multi_window_preregistration_hash",
        "observation_identifier_scheme_hash",
        "preregistration_hash",
        "registration_sequence",
        "schema_version",
        "static_fingerprint",
        "status",
        "study_identity_hash",
        "window_order_hash",
    }
)
_EVIDENCE_FIELDS = frozenset(
    {
        "evidence_hash",
        "evidence_sequence",
        "multi_window_preregistration_hash",
        "observation_identifier_scheme_hash",
        "overlap_preregistration_hash",
        "schema_version",
        "static_fingerprint",
        "study_identity_hash",
        "window_observations",
        "window_order_hash",
    }
)
_WINDOW_SOURCE_FIELDS = frozenset(
    {
        "common_observation_membership_gate_v2_hash",
        "common_observation_membership_hash",
        "common_price_date_grid_hash",
        "common_sample_count",
        "date_grid_audit_hash",
        "observation_ids",
        "uncertainty_audit_hash",
        "window_id",
    }
)


def _exact_hash(value: Any) -> bool:
    return bool(
        type(value) is str
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _positive_int(value: Any) -> bool:
    return type(value) is int and not isinstance(value, bool) and value > 0


def _valid_windows(value: Any) -> bool:
    return bool(
        type(value) is list
        and multi_window_gate_v1.MINIMUM_WINDOWS
        <= len(value)
        <= multi_window_gate_v1.MAXIMUM_WINDOWS
        and all(
            type(window_id) is str
            and window_id
            and window_id == window_id.strip()
            for window_id in value
        )
        and len(value) == len(set(value))
    )


def _valid_observation_ids(value: Any) -> bool:
    return bool(
        type(value) is list
        and MINIMUM_OBSERVATIONS_PER_WINDOW
        <= len(value)
        <= MAXIMUM_OBSERVATIONS_PER_WINDOW
        and all(
            type(observation_id) is str
            and observation_id
            and observation_id == observation_id.strip()
            for observation_id in value
        )
        and value == sorted(value)
        and len(value) == len(set(value))
    )


def _sealed_document_valid(document: Any, hash_field: str) -> bool:
    if type(document) is not dict or not _exact_hash(document.get(hash_field)):
        return False
    try:
        unsigned = deepcopy(document)
        unsigned.pop(hash_field)
        rebuilt = seal_strict_canonical_document(unsigned, hash_field)
    except (KeyError, TypeError, ValueError):
        return False
    return strict_json_contract_equal(document, rebuilt)


def _upstream_preregistration_valid(document: Any, expected_hash: Any) -> bool:
    if type(document) is not dict or not _exact_hash(expected_hash):
        return False
    try:
        return multi_window_gate_v1.verify_strategy_correlation_uncertainty_multi_window_cluster_preregistration_v1(
            document,
            expected_symbols=document.get("expected_symbols"),
            expected_clusters=document.get("expected_clusters"),
            expected_windows=document.get("expected_windows"),
            expected_preregistration_hash=expected_hash,
        )
    except (KeyError, TypeError, ValueError):
        return False


_CONTRACT_MANIFEST = {
    "schema_version": GATE_SCHEMA_VERSION,
    "static_fingerprint": STATIC_FINGERPRINT,
    "upstream_multi_window_gate": {
        "schema_version": multi_window_gate_v1.GATE_SCHEMA_VERSION,
        "preregistration_schema_version": (
            multi_window_gate_v1.PREREGISTRATION_SCHEMA_VERSION
        ),
        "implementation_sha256": MULTI_WINDOW_GATE_V1_IMPLEMENTATION_SHA256,
        "exact_rebuild_required": True,
    },
    "common_observation_membership": {
        "digest_algorithm": MEMBERSHIP_DIGEST_ALGORITHM,
        "ordering": MEMBERSHIP_ORDERING,
        "source_issuer_exact_binding_required_before_activation": True,
    },
    "temporal_date_grid": {
        "audit_schema_version": DATE_GRID_AUDIT_SCHEMA_VERSION,
        "date_grid_rule": DATE_GRID_RULE,
        "hash_is_provenance_binding_only": True,
    },
    "fixed_policy": {
        "maximum_pairwise_jaccard_overlap_bps": (
            MAXIMUM_PAIRWISE_JACCARD_OVERLAP_BPS
        ),
        "minimum_unique_observation_contribution_bps": (
            MINIMUM_UNIQUE_OBSERVATION_CONTRIBUTION_BPS
        ),
        "pairwise_rounding": "CEILING",
        "unique_contribution_rounding": "FLOOR",
        "exact_duplicate_action": "BLOCK",
        "upstream_block_action": "PRESERVE_BLOCK",
    },
    "activation_sequence": list(ACTIVATION_SEQUENCE),
}
GATE_CONTRACT_HASH = strict_canonical_hash(_CONTRACT_MANIFEST)


def build_strategy_correlation_uncertainty_multi_window_observation_overlap_preregistration_v1(
    multi_window_preregistration: Any,
    *,
    study_identity_hash: Any,
    observation_identifier_scheme_hash: Any,
    registration_sequence: Any,
) -> dict[str, Any] | None:
    """Seal the fixed overlap policy before any observation membership."""
    if (
        type(multi_window_preregistration) is not dict
        or not _exact_hash(study_identity_hash)
        or not _exact_hash(observation_identifier_scheme_hash)
        or not _positive_int(registration_sequence)
    ):
        return None
    upstream_hash = multi_window_preregistration.get("preregistration_hash")
    if not _upstream_preregistration_valid(
        multi_window_preregistration,
        upstream_hash,
    ):
        return None
    windows = multi_window_preregistration["expected_windows"]
    document = {
        "activation_sequence": list(ACTIVATION_SEQUENCE),
        "authority": deepcopy(_AUTHORITY),
        "cluster_partition_hash": multi_window_preregistration[
            "cluster_partition_hash"
        ],
        "date_grid_audit_schema_version": DATE_GRID_AUDIT_SCHEMA_VERSION,
        "date_grid_rule": DATE_GRID_RULE,
        "expected_window_count": len(windows),
        "expected_windows": deepcopy(windows),
        "gate_contract_hash": GATE_CONTRACT_HASH,
        "maximum_pairwise_jaccard_overlap_bps": (
            MAXIMUM_PAIRWISE_JACCARD_OVERLAP_BPS
        ),
        "membership_digest_algorithm": MEMBERSHIP_DIGEST_ALGORITHM,
        "membership_ordering": MEMBERSHIP_ORDERING,
        "minimum_unique_observation_contribution_bps": (
            MINIMUM_UNIQUE_OBSERVATION_CONTRIBUTION_BPS
        ),
        "multi_window_gate_v1_implementation_sha256": (
            MULTI_WINDOW_GATE_V1_IMPLEMENTATION_SHA256
        ),
        "multi_window_preregistration_hash": upstream_hash,
        "observation_identifier_scheme_hash": observation_identifier_scheme_hash,
        "registration_sequence": registration_sequence,
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PREREGISTERED_UNMOUNTED",
        "study_identity_hash": study_identity_hash,
        "window_order_hash": strict_canonical_hash(windows),
    }
    return seal_strict_canonical_document(document, "preregistration_hash")


def _preregistration_valid(document: Any) -> bool:
    return bool(
        type(document) is dict
        and frozenset(document) == _PREREGISTRATION_FIELDS
        and document.get("schema_version") == PREREGISTRATION_SCHEMA_VERSION
        and document.get("static_fingerprint") == STATIC_FINGERPRINT
        and document.get("status") == "PREREGISTERED_UNMOUNTED"
        and document.get("gate_contract_hash") == GATE_CONTRACT_HASH
        and document.get("authority") == _AUTHORITY
        and document.get("date_grid_audit_schema_version")
        == DATE_GRID_AUDIT_SCHEMA_VERSION
        and document.get("date_grid_rule") == DATE_GRID_RULE
        and document.get("membership_digest_algorithm")
        == MEMBERSHIP_DIGEST_ALGORITHM
        and document.get("membership_ordering") == MEMBERSHIP_ORDERING
        and document.get("maximum_pairwise_jaccard_overlap_bps")
        == MAXIMUM_PAIRWISE_JACCARD_OVERLAP_BPS
        and document.get("minimum_unique_observation_contribution_bps")
        == MINIMUM_UNIQUE_OBSERVATION_CONTRIBUTION_BPS
        and document.get("multi_window_gate_v1_implementation_sha256")
        == MULTI_WINDOW_GATE_V1_IMPLEMENTATION_SHA256
        and _exact_hash(document.get("study_identity_hash"))
        and _exact_hash(document.get("observation_identifier_scheme_hash"))
        and _exact_hash(document.get("cluster_partition_hash"))
        and _exact_hash(document.get("multi_window_preregistration_hash"))
        and _positive_int(document.get("registration_sequence"))
        and _valid_windows(document.get("expected_windows"))
        and document.get("expected_window_count")
        == len(document.get("expected_windows", []))
        and document.get("window_order_hash")
        == strict_canonical_hash(document.get("expected_windows"))
        and document.get("activation_sequence") == list(ACTIVATION_SEQUENCE)
        and _sealed_document_valid(document, "preregistration_hash")
    )


def _window_source_valid(row: Any) -> bool:
    if type(row) is not dict or frozenset(row) != _WINDOW_SOURCE_FIELDS:
        return False
    observation_ids = row.get("observation_ids")
    if (
        type(row.get("window_id")) is not str
        or not row["window_id"]
        or row["window_id"] != row["window_id"].strip()
        or not all(
            _exact_hash(row.get(field))
            for field in (
                "common_observation_membership_gate_v2_hash",
                "common_observation_membership_hash",
                "common_price_date_grid_hash",
                "date_grid_audit_hash",
                "uncertainty_audit_hash",
            )
        )
        or not _valid_observation_ids(observation_ids)
        or row.get("common_sample_count") != len(observation_ids)
    ):
        return False
    return row["common_observation_membership_hash"] == strict_canonical_hash(
        observation_ids
    )


def build_strategy_correlation_uncertainty_multi_window_observation_overlap_evidence_v1(
    preregistration: Any,
    window_observations: Any,
    *,
    evidence_sequence: Any,
) -> dict[str, Any] | None:
    """Seal ascending common-observation memberships for each window."""
    if (
        not _preregistration_valid(preregistration)
        or not _positive_int(evidence_sequence)
        or evidence_sequence <= preregistration["registration_sequence"]
        or type(window_observations) is not list
        or len(window_observations) != preregistration["expected_window_count"]
        or not all(_window_source_valid(row) for row in window_observations)
        or [row["window_id"] for row in window_observations]
        != preregistration["expected_windows"]
    ):
        return None
    document = {
        "evidence_sequence": evidence_sequence,
        "multi_window_preregistration_hash": preregistration[
            "multi_window_preregistration_hash"
        ],
        "observation_identifier_scheme_hash": preregistration[
            "observation_identifier_scheme_hash"
        ],
        "overlap_preregistration_hash": preregistration[
            "preregistration_hash"
        ],
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "study_identity_hash": preregistration["study_identity_hash"],
        "window_observations": deepcopy(window_observations),
        "window_order_hash": preregistration["window_order_hash"],
    }
    return seal_strict_canonical_document(document, "evidence_hash")


def _evidence_valid(document: Any) -> bool:
    return bool(
        type(document) is dict
        and frozenset(document) == _EVIDENCE_FIELDS
        and document.get("schema_version") == EVIDENCE_SCHEMA_VERSION
        and document.get("static_fingerprint") == STATIC_FINGERPRINT
        and _positive_int(document.get("evidence_sequence"))
        and all(
            _exact_hash(document.get(field))
            for field in (
                "multi_window_preregistration_hash",
                "observation_identifier_scheme_hash",
                "overlap_preregistration_hash",
                "study_identity_hash",
                "window_order_hash",
            )
        )
        and type(document.get("window_observations")) is list
        and all(
            _window_source_valid(row)
            for row in document.get("window_observations", [])
        )
        and _sealed_document_valid(document, "evidence_hash")
    )


def _overlap_bps_ceiling(intersection_count: int, union_count: int) -> int:
    return (
        intersection_count * BASIS_POINTS + union_count - 1
    ) // union_count


def _unique_bps_floor(unique_count: int, observation_count: int) -> int:
    return unique_count * BASIS_POINTS // observation_count


def _unknown(reason: str) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "activation_blockers": list(_BASE_ACTIVATION_BLOCKERS),
            "authority": deepcopy(_AUTHORITY),
            "facts": {
                "all_window_memberships_hash_rebuilt": False,
                "all_windows_exactly_bound": False,
                "common_observation_membership_contract_reused": True,
                "current_activated": False,
                "date_grid_audits_exactly_verified": False,
                "date_grid_contract_reused": True,
                "independence_units_claimed": False,
                "market_runtime_evidence_used": False,
                "membership_issuer_exactly_verified": False,
                "overlap_policy_evaluated": False,
                "profitability_proven": False,
                "pseudo_multi_window_evidence_present": False,
                "raw_observation_ids_consumed": False,
                "raw_observation_ids_embedded_in_gate_output": False,
                "runtime_mutations_performed": False,
                "synthetic_only": True,
                "upstream_multi_window_gate_exactly_verified": False,
            },
            "gate_blockers": [reason],
            "gate_contract_hash": GATE_CONTRACT_HASH,
            "pairwise_overlap_assessments": [],
            "reason_code": "UNKNOWN_OBSERVATION_OVERLAP_EVIDENCE",
            "schema_version": GATE_SCHEMA_VERSION,
            "source": {
                "evidence_hash": None,
                "multi_window_gate_hash": None,
                "multi_window_gate_v1_implementation_sha256": (
                    MULTI_WINDOW_GATE_V1_IMPLEMENTATION_SHA256
                ),
                "multi_window_preregistration_hash": None,
                "observation_identifier_scheme_hash": None,
                "overlap_preregistration_hash": None,
                "study_identity_hash": None,
                "window_order_hash": None,
            },
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": "UNKNOWN",
            "summary": None,
            "window_assessments": [],
        },
        "gate_hash",
    )


def _audit_common_observation_count(window_input: Any) -> int | None:
    if type(window_input) is not dict:
        return None
    audit = window_input.get("uncertainty_audit")
    pairs = audit.get("pairs") if type(audit) is dict else None
    if type(pairs) is not list or not pairs:
        return None
    counts = [
        pair.get("overlap_observations") if type(pair) is dict else None
        for pair in pairs
    ]
    if not all(_positive_int(count) for count in counts) or len(set(counts)) != 1:
        return None
    return counts[0]


def evaluate_strategy_correlation_uncertainty_multi_window_observation_overlap_gate_v1(
    preregistration: Any,
    evidence: Any,
    multi_window_gate_document: Any,
    multi_window_preregistration: Any,
    window_audits: Any,
    *,
    expected_preregistration_hash: Any,
    expected_evidence_hash: Any,
    expected_multi_window_gate_hash: Any,
    expected_multi_window_preregistration_hash: Any,
    expected_window_audit_hashes: Any,
) -> dict[str, Any]:
    """Apply a fail-closed overlap veto after an exact ADR0345 rebuild."""
    if (
        not _preregistration_valid(preregistration)
        or not _evidence_valid(evidence)
        or not _exact_hash(expected_preregistration_hash)
        or not _exact_hash(expected_evidence_hash)
        or preregistration["preregistration_hash"]
        != expected_preregistration_hash
        or evidence["evidence_hash"] != expected_evidence_hash
    ):
        return _unknown("OVERLAP_PREREGISTRATION_OR_EVIDENCE_INVALID")
    if (
        evidence["overlap_preregistration_hash"]
        != preregistration["preregistration_hash"]
        or evidence["study_identity_hash"] != preregistration["study_identity_hash"]
        or evidence["observation_identifier_scheme_hash"]
        != preregistration["observation_identifier_scheme_hash"]
        or evidence["window_order_hash"] != preregistration["window_order_hash"]
        or evidence["multi_window_preregistration_hash"]
        != preregistration["multi_window_preregistration_hash"]
        or evidence["evidence_sequence"]
        <= preregistration["registration_sequence"]
    ):
        return _unknown("OVERLAP_EVIDENCE_PREREGISTRATION_SPLICE")
    if (
        not _exact_hash(expected_multi_window_preregistration_hash)
        or preregistration["multi_window_preregistration_hash"]
        != expected_multi_window_preregistration_hash
        or not _upstream_preregistration_valid(
            multi_window_preregistration,
            expected_multi_window_preregistration_hash,
        )
    ):
        return _unknown("ADR0345_PREREGISTRATION_EXACT_REBUILD_FAILED")
    try:
        upstream_bound = (
            multi_window_preregistration["cluster_partition_hash"]
            == preregistration["cluster_partition_hash"]
            and multi_window_preregistration["window_order_hash"]
            == preregistration["window_order_hash"]
            and multi_window_preregistration["expected_windows"]
            == preregistration["expected_windows"]
        )
    except (KeyError, TypeError):
        upstream_bound = False
    if not upstream_bound:
        return _unknown("ADR0345_PREREGISTRATION_BINDING_SPLICE")
    try:
        upstream_exact = multi_window_gate_v1.verify_strategy_correlation_uncertainty_multi_window_cluster_gate_v1(
            multi_window_gate_document,
            multi_window_preregistration,
            window_audits,
            expected_gate_hash=expected_multi_window_gate_hash,
            expected_preregistration_hash=(
                expected_multi_window_preregistration_hash
            ),
            expected_window_audit_hashes=expected_window_audit_hashes,
        )
    except (KeyError, TypeError, ValueError):
        upstream_exact = False
    if not upstream_exact:
        return _unknown("ADR0345_GATE_EXACT_REBUILD_FAILED")
    if (
        type(multi_window_gate_document) is not dict
        or multi_window_gate_document.get("status") not in {"PASS", "BLOCK"}
        or multi_window_gate_document.get("facts", {}).get(
            "all_windows_exactly_verified"
        )
        is not True
    ):
        return _unknown("ADR0345_GATE_STATUS_NOT_DECISION_KNOWN")

    windows = preregistration["expected_windows"]
    rows = evidence["window_observations"]
    receipts = multi_window_gate_document.get("window_receipts")
    if (
        type(window_audits) is not list
        or type(expected_window_audit_hashes) is not list
        or type(receipts) is not list
        or len(window_audits) != len(windows)
        or len(expected_window_audit_hashes) != len(windows)
        or len(receipts) != len(windows)
        or len(rows) != len(windows)
        or any(not _exact_hash(value) for value in expected_window_audit_hashes)
        or len(set(expected_window_audit_hashes)) != len(windows)
    ):
        return _unknown("WINDOW_SOURCE_SET_NOT_EXACT")

    observation_sets: list[set[str]] = []
    for index, window_id in enumerate(windows):
        row = rows[index]
        receipt = receipts[index]
        window_input = window_audits[index]
        expected_audit_hash = expected_window_audit_hashes[index]
        audit = (
            window_input.get("uncertainty_audit")
            if type(window_input) is dict
            else None
        )
        common_count = _audit_common_observation_count(window_input)
        if (
            row["window_id"] != window_id
            or type(receipt) is not dict
            or receipt.get("window_id") != window_id
            or type(window_input) is not dict
            or window_input.get("window_id") != window_id
            or type(audit) is not dict
            or receipt.get("audit_hash") != expected_audit_hash
            or audit.get("audit_hash") != expected_audit_hash
            or row["uncertainty_audit_hash"] != expected_audit_hash
            or common_count is None
            or row["common_sample_count"] != common_count
        ):
            return _unknown("WINDOW_MEMBERSHIP_TO_AUDIT_BINDING_FAILED")
        observation_sets.append(set(row["observation_ids"]))

    pairwise: list[dict[str, Any]] = []
    policy_blockers: list[str] = []
    for left_index, right_index in combinations(range(len(windows)), 2):
        left_set = observation_sets[left_index]
        right_set = observation_sets[right_index]
        intersection_count = len(left_set & right_set)
        union_count = len(left_set | right_set)
        overlap_bps = _overlap_bps_ceiling(intersection_count, union_count)
        exact_duplicate = left_set == right_set
        exceeds_maximum = overlap_bps > MAXIMUM_PAIRWISE_JACCARD_OVERLAP_BPS
        left_window = windows[left_index]
        right_window = windows[right_index]
        pairwise.append(
            {
                "exact_duplicate_membership": exact_duplicate,
                "intersection_count": intersection_count,
                "jaccard_overlap_bps_ceiling": overlap_bps,
                "left_window_id": left_window,
                "overlap_exceeds_maximum": exceeds_maximum,
                "right_window_id": right_window,
                "union_count": union_count,
            }
        )
        if exact_duplicate:
            policy_blockers.append(
                "EXACT_DUPLICATE_OBSERVATION_MEMBERSHIP:"
                f"{left_window}:{right_window}"
            )
        if exceeds_maximum:
            policy_blockers.append(
                "PAIRWISE_JACCARD_OVERLAP_EXCEEDS_MAXIMUM:"
                f"{left_window}:{right_window}"
            )

    window_assessments: list[dict[str, Any]] = []
    for index, window_id in enumerate(windows):
        other_ids: set[str] = set()
        for other_index, other_set in enumerate(observation_sets):
            if other_index != index:
                other_ids.update(other_set)
        unique_count = len(observation_sets[index] - other_ids)
        observation_count = len(observation_sets[index])
        unique_bps = _unique_bps_floor(unique_count, observation_count)
        below_minimum = (
            unique_bps < MINIMUM_UNIQUE_OBSERVATION_CONTRIBUTION_BPS
        )
        row = rows[index]
        window_assessments.append(
            {
                "common_observation_membership_gate_v2_hash": row[
                    "common_observation_membership_gate_v2_hash"
                ],
                "common_observation_membership_hash": row[
                    "common_observation_membership_hash"
                ],
                "common_price_date_grid_hash": row[
                    "common_price_date_grid_hash"
                ],
                "date_grid_audit_hash": row["date_grid_audit_hash"],
                "observation_count": observation_count,
                "uncertainty_audit_hash": row["uncertainty_audit_hash"],
                "unique_contribution_below_minimum": below_minimum,
                "unique_observation_contribution_bps_floor": unique_bps,
                "unique_observation_count": unique_count,
                "window_id": window_id,
            }
        )
        if below_minimum:
            policy_blockers.append(
                "UNIQUE_OBSERVATION_CONTRIBUTION_BELOW_MINIMUM:"
                f"{window_id}"
            )

    source_reuse_checks = (
        ("date_grid_audit_hash", "DATE_GRID_AUDIT_HASH_REUSED"),
        (
            "common_observation_membership_gate_v2_hash",
            "COMMON_OBSERVATION_MEMBERSHIP_GATE_V2_HASH_REUSED",
        ),
    )
    for field, blocker in source_reuse_checks:
        values = [row[field] for row in rows]
        if len(set(values)) != len(values):
            policy_blockers.append(blocker)

    blockers: list[str] = []
    upstream_status = multi_window_gate_document["status"]
    if upstream_status == "BLOCK":
        blockers.append("UPSTREAM_MULTI_WINDOW_CLUSTER_GATE_BLOCKED")
    blockers.extend(policy_blockers)
    status = "PASS" if not blockers else "BLOCK"
    pseudo_evidence = bool(policy_blockers)
    if status == "PASS":
        reason_code = "PASS_OBSERVATION_WINDOWS_SUFFICIENTLY_DISTINCT"
    elif pseudo_evidence:
        reason_code = "BLOCK_PSEUDO_MULTI_WINDOW_EVIDENCE"
    else:
        reason_code = "BLOCK_UPSTREAM_MULTI_WINDOW_CLUSTER_GATE"
    max_overlap = max(
        assessment["jaccard_overlap_bps_ceiling"] for assessment in pairwise
    )
    min_unique = min(
        assessment["unique_observation_contribution_bps_floor"]
        for assessment in window_assessments
    )
    document = {
        "activation_blockers": list(_BASE_ACTIVATION_BLOCKERS),
        "authority": deepcopy(_AUTHORITY),
        "facts": {
            "all_window_memberships_hash_rebuilt": True,
            "all_windows_exactly_bound": True,
            "common_observation_membership_contract_reused": True,
            "current_activated": False,
            "date_grid_audits_exactly_verified": False,
            "date_grid_contract_reused": True,
            "independence_units_claimed": False,
            "market_runtime_evidence_used": False,
            "membership_issuer_exactly_verified": False,
            "overlap_policy_evaluated": True,
            "profitability_proven": False,
            "pseudo_multi_window_evidence_present": pseudo_evidence,
            "raw_observation_ids_consumed": True,
            "raw_observation_ids_embedded_in_gate_output": False,
            "runtime_mutations_performed": False,
            "synthetic_only": True,
            "upstream_multi_window_gate_exactly_verified": True,
        },
        "gate_blockers": blockers,
        "gate_contract_hash": GATE_CONTRACT_HASH,
        "pairwise_overlap_assessments": pairwise,
        "reason_code": reason_code,
        "schema_version": GATE_SCHEMA_VERSION,
        "source": {
            "evidence_hash": evidence["evidence_hash"],
            "multi_window_gate_hash": multi_window_gate_document["gate_hash"],
            "multi_window_gate_v1_implementation_sha256": (
                MULTI_WINDOW_GATE_V1_IMPLEMENTATION_SHA256
            ),
            "multi_window_preregistration_hash": (
                expected_multi_window_preregistration_hash
            ),
            "observation_identifier_scheme_hash": preregistration[
                "observation_identifier_scheme_hash"
            ],
            "overlap_preregistration_hash": preregistration[
                "preregistration_hash"
            ],
            "study_identity_hash": preregistration["study_identity_hash"],
            "window_order_hash": preregistration["window_order_hash"],
        },
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "summary": {
            "exact_duplicate_pair_count": sum(
                assessment["exact_duplicate_membership"]
                for assessment in pairwise
            ),
            "maximum_observed_pairwise_jaccard_overlap_bps_ceiling": (
                max_overlap
            ),
            "maximum_pairwise_jaccard_overlap_bps": (
                MAXIMUM_PAIRWISE_JACCARD_OVERLAP_BPS
            ),
            "minimum_observed_unique_contribution_bps_floor": min_unique,
            "minimum_unique_observation_contribution_bps": (
                MINIMUM_UNIQUE_OBSERVATION_CONTRIBUTION_BPS
            ),
            "pairwise_assessment_count": len(pairwise),
            "upstream_multi_window_gate_status": upstream_status,
            "window_count": len(windows),
        },
        "window_assessments": window_assessments,
    }
    return seal_strict_canonical_document(document, "gate_hash")


def verify_strategy_correlation_uncertainty_multi_window_observation_overlap_gate_v1(
    document: Any,
    preregistration: Any,
    evidence: Any,
    multi_window_gate_document: Any,
    multi_window_preregistration: Any,
    window_audits: Any,
    *,
    expected_gate_hash: Any,
    expected_preregistration_hash: Any,
    expected_evidence_hash: Any,
    expected_multi_window_gate_hash: Any,
    expected_multi_window_preregistration_hash: Any,
    expected_window_audit_hashes: Any,
) -> bool:
    if type(document) is not dict or not _exact_hash(expected_gate_hash):
        return False
    try:
        expected = evaluate_strategy_correlation_uncertainty_multi_window_observation_overlap_gate_v1(
            preregistration,
            evidence,
            multi_window_gate_document,
            multi_window_preregistration,
            window_audits,
            expected_preregistration_hash=expected_preregistration_hash,
            expected_evidence_hash=expected_evidence_hash,
            expected_multi_window_gate_hash=expected_multi_window_gate_hash,
            expected_multi_window_preregistration_hash=(
                expected_multi_window_preregistration_hash
            ),
            expected_window_audit_hashes=expected_window_audit_hashes,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return bool(
        strict_json_contract_equal(document, expected)
        and document.get("gate_hash") == expected_gate_hash
        and compare_digest(expected["gate_hash"], expected_gate_hash)
    )


__all__ = [
    "ACTIVATION_SEQUENCE",
    "BASIS_POINTS",
    "EVIDENCE_SCHEMA_VERSION",
    "GATE_CONTRACT_HASH",
    "GATE_SCHEMA_VERSION",
    "MAXIMUM_OBSERVATIONS_PER_WINDOW",
    "MAXIMUM_PAIRWISE_JACCARD_OVERLAP_BPS",
    "MINIMUM_OBSERVATIONS_PER_WINDOW",
    "MINIMUM_UNIQUE_OBSERVATION_CONTRIBUTION_BPS",
    "MULTI_WINDOW_GATE_V1_IMPLEMENTATION_SHA256",
    "PREREGISTRATION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_uncertainty_multi_window_observation_overlap_evidence_v1",
    "build_strategy_correlation_uncertainty_multi_window_observation_overlap_preregistration_v1",
    "evaluate_strategy_correlation_uncertainty_multi_window_observation_overlap_gate_v1",
    "verify_strategy_correlation_uncertainty_multi_window_observation_overlap_gate_v1",
]
