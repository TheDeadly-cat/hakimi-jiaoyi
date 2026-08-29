from __future__ import annotations

from datetime import date
import re
from typing import Any

from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_report_consumer import (
    verify_strategy_correlation_cross_lag_factor_calibration_consumer_receipt,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import (
    strict_iso_date,
    strict_sha256,
    strict_utc_second_timestamp,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_invalid,
)


PRECOMMIT_SCHEMA = (
    "strategy-correlation-cross-lag-factor-calibration-precommit-declaration-candidate-v1"
)
PRECOMMIT_STATIC_FINGERPRINT = (
    "20260824-cross-lag-factor-calibration-precommit-declaration-1"
)
GATE_SCHEMA = (
    "strategy-correlation-cross-lag-factor-calibration-precommit-gate-candidate-v1"
)
STATIC_FINGERPRINT = "20260824-cross-lag-factor-calibration-precommit-gate-1"
PROTOCOL_ID = "FUTURE_FACTOR_RESIDUALIZATION_EVALUATION_V2"

_DECLARATION_KEYS = frozenset(
    {
        "schema_version",
        "static_fingerprint",
        "protocol_id",
        "future_evaluation_id",
        "source_report_hash",
        "source_replay_hash",
        "source_registration_hash",
        "source_calibration_observations_hash",
        "registered_beta_ledger_hash",
        "replayed_beta_ledger_hash",
        "calibration_cutoff_date",
        "selection_cutoff_date",
        "precommit_declared_at_utc",
        "evaluation_not_before_date",
        "external_time_anchor_reference_hash",
        "declaration_hash",
    }
)
_EVALUATION_ID = re.compile(r"^[A-Z0-9][A-Z0-9._:-]{7,63}$")


def _authority() -> dict[str, bool]:
    return {
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "external_precommit_timing_attested": False,
        "formal_residualization_registration_v2_issued": False,
        "future_evaluation_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
    }


def _unknown_facts() -> dict[str, bool]:
    return {
        "beta_replay_matches_registration": False,
        "declaration_verified": False,
        "external_time_anchor_verified": False,
        "formal_residualization_registration_v2_issued": False,
        "future_evaluation_activated": False,
        "hash_chain_bound": False,
        "local_precommit_binding_complete": False,
        "precommit_before_evaluation_declared": False,
        "source_report_verified": False,
    }


def _seal(document: dict[str, Any]) -> dict[str, Any]:
    return seal_strict_canonical_document(document, "gate_hash")


def _unknown(reason: str, source_state: str) -> dict[str, Any]:
    return _seal(
        {
            "schema_version": GATE_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "source_state": source_state,
            "gate_decision": "UNKNOWN",
            "gate_reason": reason,
            "protocol_id": None,
            "future_evaluation_id": None,
            "precommit_declared_at_utc": None,
            "evaluation_not_before_date": None,
            "external_time_anchor_reference_hash": None,
            "source_declaration_hash": None,
            "source_report_hash": None,
            "source_replay_hash": None,
            "source_registration_hash": None,
            "source_calibration_observations_hash": None,
            "registered_beta_ledger_hash": None,
            "replayed_beta_ledger_hash": None,
            "facts": _unknown_facts(),
            "blockers": [reason],
            "authority": _authority(),
        }
    )


def _strict_precommit_declaration(document: Any) -> bool:
    try:
        if type(document) is not dict or frozenset(document) != _DECLARATION_KEYS:
            return False
        if (
            document["schema_version"] != PRECOMMIT_SCHEMA
            or document["static_fingerprint"] != PRECOMMIT_STATIC_FINGERPRINT
            or document["protocol_id"] != PROTOCOL_ID
        ):
            return False
        evaluation_id = document["future_evaluation_id"]
        if type(evaluation_id) is not str or _EVALUATION_ID.fullmatch(evaluation_id) is None:
            return False
        hash_fields = (
            "source_report_hash",
            "source_replay_hash",
            "source_registration_hash",
            "source_calibration_observations_hash",
            "registered_beta_ledger_hash",
            "replayed_beta_ledger_hash",
            "external_time_anchor_reference_hash",
            "declaration_hash",
        )
        if not all(strict_sha256(document[field]) for field in hash_fields):
            return False
        date_fields = (
            "calibration_cutoff_date",
            "selection_cutoff_date",
            "evaluation_not_before_date",
        )
        if not all(strict_iso_date(document[field]) for field in date_fields):
            return False
        if not strict_utc_second_timestamp(document["precommit_declared_at_utc"]):
            return False
        calibration_cutoff = date.fromisoformat(document["calibration_cutoff_date"])
        selection_cutoff = date.fromisoformat(document["selection_cutoff_date"])
        precommit_date = date.fromisoformat(document["precommit_declared_at_utc"][:10])
        evaluation_not_before = date.fromisoformat(
            document["evaluation_not_before_date"]
        )
        if not (
            calibration_cutoff
            < precommit_date
            < selection_cutoff
            <= evaluation_not_before
        ):
            return False
        rebuilt = seal_strict_canonical_document(document, "declaration_hash")
        return strict_json_contract_equal(document, rebuilt)
    except (KeyError, TypeError, ValueError, OverflowError):
        return False


def _observed(
    declaration: dict[str, Any], report: dict[str, Any]
) -> dict[str, Any]:
    matched = report["report_state"] == "OBSERVED_CALIBRATION_MATCH"
    blocked = report["report_state"] == "OBSERVED_CALIBRATION_BLOCK"
    if not (matched or blocked):
        return _unknown("G1_REPORT_NOT_OBSERVED_FOR_PRECOMMIT", "INVALID")

    if matched:
        decision = "BOUND_LOCAL_ONLY"
        reason = "FUTURE_EVALUATION_HASH_CHAIN_BOUND_EXTERNAL_TIME_UNVERIFIED"
    else:
        decision = "BLOCK"
        reason = "CALIBRATION_REPLAY_BLOCKS_FUTURE_EVALUATION"

    blockers = [
        *report["blockers"],
        *( ["FUTURE_EVALUATION_PRECOMMIT_BLOCKED"] if blocked else [] ),
        "EXTERNAL_PRECOMMIT_TIME_ANCHOR_UNVERIFIED",
        "FORMAL_RESIDUALIZATION_REGISTRATION_V2_NOT_ISSUED",
        "FUTURE_EVALUATION_NOT_ACTIVATED",
    ]
    authority = _authority()
    if strict_research_authority_invalid(authority):
        return _unknown("PRECOMMIT_GATE_INTERNAL_AUTHORITY_INVALID", "INVALID")
    return _seal(
        {
            "schema_version": GATE_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "source_state": "OBSERVED",
            "gate_decision": decision,
            "gate_reason": reason,
            "protocol_id": declaration["protocol_id"],
            "future_evaluation_id": declaration["future_evaluation_id"],
            "precommit_declared_at_utc": declaration[
                "precommit_declared_at_utc"
            ],
            "evaluation_not_before_date": declaration[
                "evaluation_not_before_date"
            ],
            "external_time_anchor_reference_hash": declaration[
                "external_time_anchor_reference_hash"
            ],
            "source_declaration_hash": declaration["declaration_hash"],
            "source_report_hash": report["verification_hash"],
            "source_replay_hash": report["source_replay_hash"],
            "source_registration_hash": report["source_registration_hash"],
            "source_calibration_observations_hash": report[
                "source_calibration_observations_hash"
            ],
            "registered_beta_ledger_hash": report[
                "source_registered_beta_ledger_hash"
            ],
            "replayed_beta_ledger_hash": report[
                "source_replayed_beta_ledger_hash"
            ],
            "facts": {
                "beta_replay_matches_registration": report["facts"][
                    "beta_replay_matches_registration"
                ],
                "declaration_verified": True,
                "external_time_anchor_verified": False,
                "formal_residualization_registration_v2_issued": False,
                "future_evaluation_activated": False,
                "hash_chain_bound": True,
                "local_precommit_binding_complete": True,
                "precommit_before_evaluation_declared": True,
                "source_report_verified": True,
            },
            "blockers": blockers,
            "authority": authority,
        }
    )


def evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate(
    precommit_declaration: Any,
    report: Any,
    replay: Any,
    residualization_registration: Any,
    calibration_observations: Any,
    *,
    expected_declaration_hash: Any,
    expected_report_hash: Any,
    expected_replay_hash: Any,
    expected_registration_hash: Any,
    expected_calibration_observations_hash: Any,
) -> dict[str, Any]:
    try:
        if precommit_declaration is None:
            if type(expected_declaration_hash) is not str or expected_declaration_hash != "":
                return _unknown("PRECOMMIT_DECLARATION_INVALID", "INVALID")
            return _unknown("PRECOMMIT_DECLARATION_MISSING", "MISSING")
        if type(precommit_declaration) is not dict:
            return _unknown("PRECOMMIT_DECLARATION_INVALID", "INVALID")
        if (
            precommit_declaration.get("schema_version") != PRECOMMIT_SCHEMA
            or precommit_declaration.get("static_fingerprint")
            != PRECOMMIT_STATIC_FINGERPRINT
        ):
            return _unknown("PRECOMMIT_DECLARATION_UNSUPPORTED", "UNSUPPORTED")
        if (
            not strict_sha256(expected_declaration_hash)
            or precommit_declaration.get("declaration_hash")
            != expected_declaration_hash
            or not _strict_precommit_declaration(precommit_declaration)
        ):
            return _unknown("PRECOMMIT_DECLARATION_INVALID", "INVALID")
        if (
            type(report) is not dict
            or report.get("verification_hash") != expected_report_hash
        ):
            return _unknown("G1_REPORT_INVALID_FOR_PRECOMMIT", "INVALID")
        verified = (
            verify_strategy_correlation_cross_lag_factor_calibration_consumer_receipt(
                report,
                replay,
                residualization_registration=residualization_registration,
                calibration_observations=calibration_observations,
                expected_registration_hash=expected_registration_hash,
                expected_calibration_observations_hash=(
                    expected_calibration_observations_hash
                ),
                expected_replay_hash=expected_replay_hash,
            )
        )
        if verified is not True:
            return _unknown("G1_REPORT_INVALID_FOR_PRECOMMIT", "INVALID")

        bindings = {
            "source_report_hash": report["verification_hash"],
            "source_replay_hash": report["source_replay_hash"],
            "source_registration_hash": report["source_registration_hash"],
            "source_calibration_observations_hash": report[
                "source_calibration_observations_hash"
            ],
            "registered_beta_ledger_hash": report[
                "source_registered_beta_ledger_hash"
            ],
            "replayed_beta_ledger_hash": report[
                "source_replayed_beta_ledger_hash"
            ],
            "calibration_cutoff_date": report["calibration_summary"][
                "calibration_cutoff_date"
            ],
            "selection_cutoff_date": report["calibration_summary"][
                "selection_cutoff_date"
            ],
        }
        if any(precommit_declaration[key] != value for key, value in bindings.items()):
            return _unknown("PRECOMMIT_SOURCE_BINDING_INVALID", "INVALID")
        return _observed(precommit_declaration, report)
    except (KeyError, TypeError, ValueError, ArithmeticError, OverflowError):
        return _unknown("PRECOMMIT_DECLARATION_INVALID", "INVALID")


def verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate(
    document: Any,
    precommit_declaration: Any,
    report: Any,
    replay: Any,
    residualization_registration: Any,
    calibration_observations: Any,
    *,
    expected_declaration_hash: Any,
    expected_report_hash: Any,
    expected_replay_hash: Any,
    expected_registration_hash: Any,
    expected_calibration_observations_hash: Any,
) -> bool:
    try:
        rebuilt = evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate(
            precommit_declaration,
            report,
            replay,
            residualization_registration,
            calibration_observations,
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
