from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import strict_sha256
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_preregistration_v1 import (
    EVALUATED_LAGS,
    MAXIMUM_EVALUATED_LAG,
    MINIMUM_PAIRS_AT_MAXIMUM_LAG,
    MINIMUM_ROWS_PER_FOLD,
    PROTOCOL_ID as SOURCE_PROTOCOL_ID,
    SCHEMA_VERSION as SOURCE_SCHEMA_VERSION,
    STATIC_FINGERPRINT as SOURCE_STATIC_FINGERPRINT,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_preregistration_v1,
)


SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-"
    "observation-protocol-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260917-cross-lag-factor-calibration-long-horizon-observation-protocol-1"
)
PROTOCOL_ID = "FUTURE_FACTOR_RESIDUAL_ORDER_LONG_HORIZON_OBSERVATION_V1"
OBSERVATION_BATCH_SCHEMA = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-"
    "observation-batch-candidate-v1"
)
EXTERNAL_ATTESTATION_SCHEMA = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-"
    "external-time-attestation-candidate-v1"
)
ANCHOR_ADAPTER_INTERFACE = "EXTERNAL_APPEND_ONLY_TIME_ATTESTATION_VERIFIER_V1"
REQUIRED_ATTESTATION_STATE = "VERIFIED_EXTERNAL_ATTESTATION"
MISSING_EXTERNAL_ATTESTATION_POLICY = "UNKNOWN"
UNSUPPORTED_ANCHOR_ADAPTER_POLICY = "UNKNOWN"
SELF_ATTESTED_ANCHOR_POLICY = "BLOCK"

REQUIRED_BATCH_BINDINGS = (
    "preregistration_hash",
    "future_evaluation_id",
    "source_report_consumer_v7_hash",
    "identity_order_hash",
    "factor_source_hash",
    "fold_order_hash",
    "first_observation_date",
    "last_observation_date",
    "observation_batch_hash",
)
REQUIRED_ATTESTATION_BINDINGS = (
    "source_external_time_anchor_reference_hash",
    "observation_batch_hash",
    "provider_id",
    "provider_receipt_id",
    "provider_timestamp_utc",
    "adapter_id",
    "adapter_static_fingerprint",
    "trust_root_sha256",
    "receipt_content_sha256",
    "signature_sha256",
    "attestation_hash",
)
REQUIRED_TIME_RULES = (
    "FIRST_OBSERVATION_ON_OR_AFTER_EVALUATION_NOT_BEFORE_DATE",
    "STRICTLY_INCREASING_UNIQUE_OBSERVATION_DATES_WITHIN_FOLD",
    "PROVIDER_TIMESTAMP_ON_OR_AFTER_LAST_OBSERVATION_DATE",
    "PROVIDER_TIMESTAMP_MUST_BE_EXTERNALLY_VERIFIED",
    "NO_CALLER_CLOCK_OR_SELF_ATTESTATION_AS_AUTHORITY",
)

_SOURCE_CONTEXT_KEYS = frozenset(
    {
        "beta_stability_gate",
        "calibration_observations",
        "evaluation_not_before_date",
        "expected_beta_stability_gate_hash",
        "expected_calibration_observations_hash",
        "expected_declaration_hash",
        "expected_omnibus_gate_v1_hash",
        "expected_precommit_gate_v1_hash",
        "expected_precommit_gate_v2_hash",
        "expected_precommit_gate_v3_hash",
        "expected_precommit_gate_v4_hash",
        "expected_precommit_gate_v5_hash",
        "expected_precommit_gate_v6_hash",
        "expected_precommit_gate_v7_hash",
        "expected_registration_hash",
        "expected_replay_hash",
        "expected_report_consumer_v5_hash",
        "expected_report_consumer_v6_hash",
        "expected_report_consumer_v7_hash",
        "expected_report_hash",
        "expected_residual_energy_gate_hash",
        "expected_residual_order_gate_v1_hash",
        "expected_residual_order_gate_v2_hash",
        "expected_residual_order_gate_v3_hash",
        "omnibus_gate_v1",
        "precommit_declaration",
        "precommit_gate_v1",
        "precommit_gate_v2",
        "precommit_gate_v3",
        "precommit_gate_v4",
        "precommit_gate_v5",
        "precommit_gate_v6",
        "precommit_gate_v7",
        "preregistered_at_utc",
        "replay",
        "report",
        "report_consumer_v5",
        "report_consumer_v6",
        "report_consumer_v7",
        "residual_energy_gate",
        "residual_order_gate_v1",
        "residual_order_gate_v2",
        "residual_order_gate_v3",
        "residualization_registration",
    }
)


def _authority() -> dict[str, bool]:
    return {
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "external_time_anchor_verified": False,
        "future_evaluation_allowed": False,
        "future_observation_collection_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
    }


def _facts(*, source_verified: bool = False, protocol_pinned: bool = False) -> dict[str, bool]:
    return {
        "evaluation_activated": False,
        "external_attestation_present": False,
        "external_authenticity_proven": False,
        "external_time_anchor_verified": False,
        "observation_batch_present": False,
        "observation_protocol_pinned": protocol_pinned,
        "observations_collected": False,
        "result_available": False,
        "source_preregistration_verified": source_verified,
    }


def _source_state(document: Any) -> str:
    if type(document) is not dict:
        return "UNKNOWN"
    value = document.get("source_state")
    return value if value in {"VERIFIED", "BLOCKED", "UNKNOWN"} else "UNKNOWN"


def _source_text(document: Any, key: str) -> str | None:
    if type(document) is not dict:
        return None
    value = document.get(key)
    return value if type(value) is str else None


def _unknown(
    reason: str,
    source: Any,
    *,
    expected_preregistration_hash: Any = None,
    source_verified: bool = False,
) -> dict[str, Any]:
    source_hash = (
        expected_preregistration_hash
        if strict_sha256(expected_preregistration_hash)
        else None
    )
    document: dict[str, Any] = {
        "anchor_adapter_interface": ANCHOR_ADAPTER_INTERFACE,
        "authority": _authority(),
        "blockers": [reason],
        "evaluated_lags": [],
        "evaluation_not_before_date": None,
        "external_attestation_schema": EXTERNAL_ATTESTATION_SCHEMA,
        "facts": _facts(source_verified=source_verified),
        "future_evaluation_id": None,
        "maximum_evaluated_lag": None,
        "minimum_pairs_at_maximum_lag": None,
        "minimum_rows_per_fold": None,
        "missing_external_attestation_policy": MISSING_EXTERNAL_ATTESTATION_POLICY,
        "observation_batch_schema": OBSERVATION_BATCH_SCHEMA,
        "protocol_id": PROTOCOL_ID,
        "protocol_state": "UNKNOWN",
        "required_attestation_bindings": [],
        "required_attestation_state": REQUIRED_ATTESTATION_STATE,
        "required_batch_bindings": [],
        "required_time_rules": [],
        "schema_version": SCHEMA_VERSION,
        "self_attested_anchor_policy": SELF_ATTESTED_ANCHOR_POLICY,
        "source_evaluation_status": _source_text(source, "evaluation_status"),
        "source_external_time_anchor_reference_hash": _source_text(
            source, "source_external_time_anchor_reference_hash"
        ),
        "source_preregistration_hash": source_hash,
        "source_preregistration_schema": _source_text(source, "schema_version"),
        "source_report_consumer_v7_hash": _source_text(
            source, "source_report_consumer_v7_hash"
        ),
        "source_state": _source_state(source),
        "static_fingerprint": STATIC_FINGERPRINT,
        "unsupported_anchor_adapter_policy": UNSUPPORTED_ANCHOR_ADAPTER_POLICY,
    }
    return seal_strict_canonical_document(document, "protocol_hash")


def build_strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_protocol_v1(
    long_horizon_preregistration: Any,
    source_verification_context: Any,
    *,
    expected_preregistration_hash: Any,
) -> dict[str, Any]:
    source = long_horizon_preregistration
    if not strict_sha256(expected_preregistration_hash):
        return _unknown(
            "EXPECTED_PREREGISTRATION_HASH_INVALID",
            source,
            expected_preregistration_hash=expected_preregistration_hash,
        )
    if type(source) is not dict:
        return _unknown(
            "SOURCE_PREREGISTRATION_NOT_OBJECT",
            source,
            expected_preregistration_hash=expected_preregistration_hash,
        )
    if source.get("preregistration_hash") != expected_preregistration_hash:
        return _unknown(
            "SOURCE_PREREGISTRATION_HASH_MISMATCH",
            source,
            expected_preregistration_hash=expected_preregistration_hash,
        )
    if source.get("schema_version") != SOURCE_SCHEMA_VERSION:
        return _unknown(
            "SOURCE_PREREGISTRATION_SCHEMA_UNSUPPORTED",
            source,
            expected_preregistration_hash=expected_preregistration_hash,
        )
    if type(source_verification_context) is not dict:
        return _unknown(
            "SOURCE_VERIFICATION_CONTEXT_NOT_OBJECT",
            source,
            expected_preregistration_hash=expected_preregistration_hash,
        )
    if set(source_verification_context) != _SOURCE_CONTEXT_KEYS:
        return _unknown(
            "SOURCE_VERIFICATION_CONTEXT_FIELDS_INVALID",
            source,
            expected_preregistration_hash=expected_preregistration_hash,
        )
    try:
        source_verified = (
            verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_preregistration_v1(
                source,
                **dict(source_verification_context),
            )
        )
    except Exception:
        source_verified = False
    if not source_verified:
        return _unknown(
            "SOURCE_PREREGISTRATION_NOT_VERIFIED",
            source,
            expected_preregistration_hash=expected_preregistration_hash,
        )
    if (
        source.get("static_fingerprint") != SOURCE_STATIC_FINGERPRINT
        or source.get("protocol_id") != SOURCE_PROTOCOL_ID
    ):
        return _unknown(
            "SOURCE_PREREGISTRATION_IDENTITY_INVALID",
            source,
            expected_preregistration_hash=expected_preregistration_hash,
            source_verified=True,
        )
    if (
        source.get("source_state") != "VERIFIED"
        or source.get("preregistration_state") != "DECLARED_NOT_EVALUATED"
        or source.get("evaluation_status") != "NOT_EVALUATED"
    ):
        return _unknown(
            "SOURCE_PREREGISTRATION_NOT_DECLARED",
            source,
            expected_preregistration_hash=expected_preregistration_hash,
            source_verified=True,
        )
    if (
        not strict_sha256(source.get("source_external_time_anchor_reference_hash"))
        or not strict_sha256(source.get("source_report_consumer_v7_hash"))
    ):
        return _unknown(
            "SOURCE_BINDINGS_INVALID",
            source,
            expected_preregistration_hash=expected_preregistration_hash,
            source_verified=True,
        )

    document: dict[str, Any] = {
        "anchor_adapter_interface": ANCHOR_ADAPTER_INTERFACE,
        "authority": _authority(),
        "blockers": [
            "FUTURE_OBSERVATION_BATCH_NOT_OBSERVED",
            "EXTERNAL_TIME_ATTESTATION_NOT_OBSERVED",
            "LONG_HORIZON_EVALUATION_NOT_ACTIVATED",
        ],
        "evaluated_lags": list(EVALUATED_LAGS),
        "evaluation_not_before_date": source.get("evaluation_not_before_date"),
        "external_attestation_schema": EXTERNAL_ATTESTATION_SCHEMA,
        "facts": _facts(source_verified=True, protocol_pinned=True),
        "future_evaluation_id": source.get("future_evaluation_id"),
        "maximum_evaluated_lag": MAXIMUM_EVALUATED_LAG,
        "minimum_pairs_at_maximum_lag": MINIMUM_PAIRS_AT_MAXIMUM_LAG,
        "minimum_rows_per_fold": MINIMUM_ROWS_PER_FOLD,
        "missing_external_attestation_policy": MISSING_EXTERNAL_ATTESTATION_POLICY,
        "observation_batch_schema": OBSERVATION_BATCH_SCHEMA,
        "protocol_id": PROTOCOL_ID,
        "protocol_state": "PROTOCOL_DECLARED_NO_OBSERVATIONS",
        "required_attestation_bindings": list(REQUIRED_ATTESTATION_BINDINGS),
        "required_attestation_state": REQUIRED_ATTESTATION_STATE,
        "required_batch_bindings": list(REQUIRED_BATCH_BINDINGS),
        "required_time_rules": list(REQUIRED_TIME_RULES),
        "schema_version": SCHEMA_VERSION,
        "self_attested_anchor_policy": SELF_ATTESTED_ANCHOR_POLICY,
        "source_evaluation_status": source.get("evaluation_status"),
        "source_external_time_anchor_reference_hash": source.get(
            "source_external_time_anchor_reference_hash"
        ),
        "source_preregistration_hash": expected_preregistration_hash,
        "source_preregistration_schema": SOURCE_SCHEMA_VERSION,
        "source_report_consumer_v7_hash": source.get(
            "source_report_consumer_v7_hash"
        ),
        "source_state": "VERIFIED",
        "static_fingerprint": STATIC_FINGERPRINT,
        "unsupported_anchor_adapter_policy": UNSUPPORTED_ANCHOR_ADAPTER_POLICY,
    }
    return seal_strict_canonical_document(document, "protocol_hash")


def verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_protocol_v1(
    document: Any,
    long_horizon_preregistration: Any,
    source_verification_context: Any,
    *,
    expected_preregistration_hash: Any,
) -> bool:
    try:
        if type(document) is not dict:
            return False
        expected = build_strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_protocol_v1(
            long_horizon_preregistration,
            source_verification_context,
            expected_preregistration_hash=expected_preregistration_hash,
        )
        return strict_json_contract_equal(document, expected)
    except Exception:
        return False
