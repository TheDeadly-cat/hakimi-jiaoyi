from __future__ import annotations

from copy import deepcopy
from typing import Any

from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_gate_v2 import (
    GATE_SCHEMA,
    STATIC_FINGERPRINT as GATE_STATIC_FINGERPRINT,
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import strict_sha256
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_invalid,
)


ENVELOPE_SCHEMA = (
    "strategy-correlation-cross-lag-factor-calibration-precommit-"
    "presentation-envelope-v1"
)
STATIC_FINGERPRINT = (
    "20260827-cross-lag-factor-calibration-precommit-presentation-envelope-1"
)
PRESENTATION_STATUS = "UNMOUNTED_CANDIDATE"


def _authority() -> dict[str, bool]:
    return {
        "beta_temporal_stability_proven": False,
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "external_precommit_timing_attested": False,
        "formal_residualization_registration_v2_issued": False,
        "future_evaluation_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_mounted": False,
        "profitability_claim_allowed": False,
        "source_semantics_replayed_in_browser": False,
    }


def _seal(document: dict[str, Any]) -> dict[str, Any]:
    return seal_strict_canonical_document(document, "envelope_hash")


def _closed(source_state: str, reason: str) -> dict[str, Any]:
    return _seal(
        {
            "schema_version": ENVELOPE_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "presentation_status": PRESENTATION_STATUS,
            "verification_state": "UNKNOWN",
            "envelope_reason": reason,
            "source_state": source_state,
            "source_schema_version": None,
            "source_static_fingerprint": None,
            "source_gate_hash": None,
            "source_precommit_gate_v1_hash": None,
            "source_stability_gate_hash": None,
            "source_replay_hash": None,
            "source_registration_hash": None,
            "source_calibration_observations_hash": None,
            "gate": None,
            "authority": _authority(),
        }
    )


def _verified(gate: dict[str, Any]) -> dict[str, Any]:
    authority = _authority()
    if strict_research_authority_invalid(authority):
        return _closed("INVALID", "H1_PRECOMMIT_GATE_INVALID")
    return _seal(
        {
            "schema_version": ENVELOPE_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "presentation_status": PRESENTATION_STATUS,
            "verification_state": "VERIFIED",
            "envelope_reason": "H1_PRECOMMIT_GATE_VERIFIED",
            "source_state": gate["source_state"],
            "source_schema_version": gate["schema_version"],
            "source_static_fingerprint": gate["static_fingerprint"],
            "source_gate_hash": gate["gate_hash"],
            "source_precommit_gate_v1_hash": gate[
                "source_precommit_gate_v1_hash"
            ],
            "source_stability_gate_hash": gate["source_stability_gate_hash"],
            "source_replay_hash": gate["source_replay_hash"],
            "source_registration_hash": gate["source_registration_hash"],
            "source_calibration_observations_hash": gate[
                "source_calibration_observations_hash"
            ],
            "gate": deepcopy(gate),
            "authority": authority,
        }
    )


def build_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope(
    gate: Any,
    precommit_gate_v1: Any,
    stability_gate: Any,
    precommit_declaration: Any,
    report: Any,
    replay: Any,
    residualization_registration: Any,
    calibration_observations: Any,
    *,
    expected_gate_hash: Any,
    expected_precommit_gate_v1_hash: Any,
    expected_stability_gate_hash: Any,
    expected_declaration_hash: Any,
    expected_report_hash: Any,
    expected_replay_hash: Any,
    expected_registration_hash: Any,
    expected_calibration_observations_hash: Any,
) -> dict[str, Any]:
    try:
        if gate is None:
            if type(expected_gate_hash) is not str or expected_gate_hash != "":
                return _closed("INVALID", "H1_PRECOMMIT_GATE_INVALID")
            return _closed("NOT_SUPPLIED", "H1_PRECOMMIT_GATE_NOT_SUPPLIED")

        if type(gate) is not dict or not strict_sha256(expected_gate_hash):
            return _closed("INVALID", "H1_PRECOMMIT_GATE_INVALID")
        if (
            gate.get("schema_version") != GATE_SCHEMA
            or gate.get("static_fingerprint") != GATE_STATIC_FINGERPRINT
        ):
            return _closed("UNSUPPORTED", "H1_PRECOMMIT_GATE_UNSUPPORTED")
        if gate.get("gate_hash") != expected_gate_hash:
            return _closed("INVALID", "H1_PRECOMMIT_GATE_INVALID")

        verified = verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v2(
            gate,
            precommit_gate_v1,
            stability_gate,
            precommit_declaration,
            report,
            replay,
            residualization_registration,
            calibration_observations,
            expected_precommit_gate_v1_hash=expected_precommit_gate_v1_hash,
            expected_stability_gate_hash=expected_stability_gate_hash,
            expected_declaration_hash=expected_declaration_hash,
            expected_report_hash=expected_report_hash,
            expected_replay_hash=expected_replay_hash,
            expected_registration_hash=expected_registration_hash,
            expected_calibration_observations_hash=(
                expected_calibration_observations_hash
            ),
        )
        if verified is not True:
            return _closed("INVALID", "H1_PRECOMMIT_GATE_INVALID")
        return _verified(gate)
    except (KeyError, TypeError, ValueError, ArithmeticError, OverflowError):
        return _closed("INVALID", "H1_PRECOMMIT_GATE_INVALID")


def verify_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope(
    document: Any,
    gate: Any,
    precommit_gate_v1: Any,
    stability_gate: Any,
    precommit_declaration: Any,
    report: Any,
    replay: Any,
    residualization_registration: Any,
    calibration_observations: Any,
    *,
    expected_gate_hash: Any,
    expected_precommit_gate_v1_hash: Any,
    expected_stability_gate_hash: Any,
    expected_declaration_hash: Any,
    expected_report_hash: Any,
    expected_replay_hash: Any,
    expected_registration_hash: Any,
    expected_calibration_observations_hash: Any,
) -> bool:
    try:
        rebuilt = build_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope(
            gate,
            precommit_gate_v1,
            stability_gate,
            precommit_declaration,
            report,
            replay,
            residualization_registration,
            calibration_observations,
            expected_gate_hash=expected_gate_hash,
            expected_precommit_gate_v1_hash=expected_precommit_gate_v1_hash,
            expected_stability_gate_hash=expected_stability_gate_hash,
            expected_declaration_hash=expected_declaration_hash,
            expected_report_hash=expected_report_hash,
            expected_replay_hash=expected_replay_hash,
            expected_registration_hash=expected_registration_hash,
            expected_calibration_observations_hash=(
                expected_calibration_observations_hash
            ),
        )
        return strict_json_contract_equal(document, rebuilt)
    except (KeyError, TypeError, ValueError, ArithmeticError, OverflowError):
        return False
