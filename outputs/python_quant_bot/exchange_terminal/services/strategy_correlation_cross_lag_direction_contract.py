from __future__ import annotations

from typing import Any

from .strategy_correlation_cross_lag_gate import (
    EVALUATION_SCHEMA,
    LAGS,
    STATIC_FINGERPRINT as GATE_STATIC_FINGERPRINT,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


CONTRACT_SCHEMA = "strategy-correlation-cross-lag-direction-contract-v1"
STATIC_FINGERPRINT = "20260821-cross-lag-direction-contract-1"
INDEX_RELATION = "RIGHT_INDEX_EQUALS_LEFT_INDEX_PLUS_LAG"
LAG_DIRECTION_CONVENTION = "POSITIVE_LAG_MEANS_RIGHT_IDENTITY_FOLLOWS_LEFT_IDENTITY"
TIME_AXIS = "ASCENDING_OBSERVATION_INDEX"

_LOCKED_AUTHORITY = {
    "descriptive_only": True,
    "formal_preregistration_bound": False,
    "sequence_order_attested": False,
    "strata_timing_attested": False,
    "independence_proven": False,
    "count_as_independent_allowed": False,
    "candidate_binding_activation_allowed": False,
    "formal_registry_activation_allowed": False,
    "formal_registry_written": False,
    "current_admission_allowed": False,
    "current_writer_activation_allowed": False,
    "current_pointer_written": False,
    "paper_authorized": False,
    "live_order_allowed": False,
    "profitability_claim_allowed": False,
}


def build_strategy_correlation_cross_lag_direction_contract() -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema_version": CONTRACT_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "contract_state": "FROZEN_INTERPRETATION_CANDIDATE",
            "source_gate_schema": EVALUATION_SCHEMA,
            "source_gate_static_fingerprint": GATE_STATIC_FINGERPRINT,
            "lag_family": list(LAGS),
            "zero_lag_included": False,
            "time_axis": TIME_AXIS,
            "index_relation": INDEX_RELATION,
            "lag_direction_convention": LAG_DIRECTION_CONVENTION,
            "example": {
                "lag": 1,
                "relation": "RIGHT_T_EQUALS_LEFT_T_MINUS_1",
                "interpretation": "RIGHT_FOLLOWS_LEFT_BY_ONE_OBSERVATION",
            },
            "permission_state": "LOCKED",
            "authority": dict(_LOCKED_AUTHORITY),
        },
        "contract_hash",
    )


def verify_strategy_correlation_cross_lag_direction_contract(document: Any) -> bool:
    if not isinstance(document, dict):
        return False
    return strict_json_contract_equal(
        document,
        build_strategy_correlation_cross_lag_direction_contract(),
    )
