"""Unmounted geometry-bound consumer for effective bet budget v3.

The binding composes the exact ADR0330 geometry-to-complete-link evaluation with
the existing preregistered-strata and effective-budget v3 contracts.  It is a
pure, synthetic evidence producer and grants no admission or trading authority.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from hmac import compare_digest
import json
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v3 as _budget_v3,
)
from exchange_terminal.services import (
    strategy_correlation_matrix_geometry_complete_link_binding_v1 as _geometry_binding,
)
from exchange_terminal.services import strategy_correlation_preregistered_strata as _strata


SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-effective-bet-budget-binding-contract-v1"
)
PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-effective-bet-budget-binding-preregistration-v1"
)
EVALUATION_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-effective-bet-budget-binding-evaluation-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-matrix-geometry-effective-bet-budget-binding-v1-unmounted-lock-1"
)

GEOMETRY_BINDING_MODULE = (
    "exchange_terminal.services.strategy_correlation_matrix_geometry_complete_link_binding_v1"
)
EFFECTIVE_BUDGET_MODULE = (
    "exchange_terminal.services.strategy_correlation_cluster_effective_bet_budget_v3"
)
EFFECTIVE_BUDGET_IMPLEMENTATION_SHA256 = (
    "bece44fe40c02242c879d1dead5cc11d2ce00edfc91c8d78a5b29962516c002d"
)
STRATA_MODULE = "exchange_terminal.services.strategy_correlation_preregistered_strata"
STRATA_IMPLEMENTATION_SHA256 = (
    "0758bd054adc2c98b51bf027cb5deea25e3620f555fd3369cdaf799c964adbb8"
)

ACTIVATION_SEQUENCE = (
    "VERIFY_EXACT_GEOMETRY_COMPLETE_LINK_BINDING_EVALUATION",
    "VERIFY_EXACT_PREREGISTERED_STRATA_GATE",
    "EVALUATE_EFFECTIVE_BET_BUDGET_V3",
    "REBUILD_EFFECTIVE_BET_BUDGET_V3_WITH_PINNED_EVALUATOR",
    "VERIFY_EFFECTIVE_BET_BUDGET_V3",
)

_PINNED_BUDGET_EVALUATOR = (
    _budget_v3.evaluate_strategy_correlation_cluster_effective_bet_budget_v3
)


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return sha256(payload).hexdigest()


def _canonical_external_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def _is_exact_hash(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _safe_hash(document: Any, field: str) -> str | None:
    if not isinstance(document, dict):
        return None
    value = document.get(field)
    return value if _is_exact_hash(value) else None


def _external_self_hash_is_exact(document: Any, field: str) -> bool:
    stored_hash = _safe_hash(document, field)
    if stored_hash is None:
        return False
    unsigned = deepcopy(document)
    unsigned.pop(field, None)
    return compare_digest(_canonical_external_hash(unsigned), stored_hash)


def _verification_passed(document: Any) -> bool:
    return isinstance(document, dict) and document.get("status") == "PASS"


def _permissions() -> dict[str, bool]:
    return {
        "research_evidence_only": True,
        "current_admission": False,
        "writer_activation": False,
        "paper": False,
        "live": False,
    }


_CONTRACT_MANIFEST = {
    "schema_version": SCHEMA_VERSION,
    "static_fingerprint": STATIC_FINGERPRINT,
    "activation_sequence": list(ACTIVATION_SEQUENCE),
    "geometry_complete_link_binding": {
        "module": GEOMETRY_BINDING_MODULE,
        "contract_hash": _geometry_binding.BINDING_CONTRACT_HASH,
        "static_fingerprint": _geometry_binding.STATIC_FINGERPRINT,
        "evaluation_schema_version": _geometry_binding.EVALUATION_SCHEMA_VERSION,
        "research_only_lanes": list(_geometry_binding.RESEARCH_ONLY_LANES),
    },
    "effective_budget": {
        "module": EFFECTIVE_BUDGET_MODULE,
        "source_sha256": EFFECTIVE_BUDGET_IMPLEMENTATION_SHA256,
        "schema_version": _budget_v3.BUDGET_SCHEMA_VERSION,
        "static_fingerprint": _budget_v3.STATIC_FINGERPRINT,
        "candidate_evaluator": (
            "evaluate_strategy_correlation_cluster_effective_bet_budget_v3"
        ),
        "exact_rebuilder": (
            "evaluate_strategy_correlation_cluster_effective_bet_budget_v3@binding_module_import"
        ),
        "verifier": "verify_strategy_correlation_cluster_effective_bet_budget_v3",
    },
    "strata": {
        "module": STRATA_MODULE,
        "source_sha256": STRATA_IMPLEMENTATION_SHA256,
        "registration_schema": _strata.REGISTRATION_SCHEMA,
        "gate_schema": _strata.GATE_SCHEMA,
    },
    "authority": {
        "mounted": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "paper_allowed": False,
        "live_allowed": False,
    },
}
BINDING_CONTRACT_HASH = _canonical_hash(_CONTRACT_MANIFEST)


def _strata_registration_is_exact(
    document: Any,
    source_preregistration: Any,
    *,
    expected_registration_hash: Any,
) -> bool:
    if not _is_exact_hash(expected_registration_hash):
        return False
    if _safe_hash(document, "registration_hash") != expected_registration_hash:
        return False
    try:
        verification = _strata.verify_strategy_correlation_strata_preregistration(
            document,
            source_preregistration=source_preregistration,
        )
    except Exception:
        return False
    return _verification_passed(verification)


def build_strategy_correlation_matrix_geometry_effective_bet_budget_binding_preregistration_v1(
    geometry_complete_link_binding_preregistration: Any,
    geometry_preregistration: Any,
    cluster_preregistration: Any,
    strata_registration: Any,
    *,
    expected_geometry_complete_link_binding_preregistration_hash: Any,
    expected_geometry_preregistration_hash: Any,
    expected_cluster_preregistration_hash: Any,
    expected_strata_registration_hash: Any,
) -> dict[str, Any] | None:
    """Preregister exact upstream and strata identities without activating a consumer."""

    try:
        upstream_valid = _geometry_binding.verify_strategy_correlation_matrix_geometry_complete_link_binding_preregistration_v1(
            geometry_complete_link_binding_preregistration,
            geometry_preregistration,
            cluster_preregistration,
            expected_binding_preregistration_hash=(
                expected_geometry_complete_link_binding_preregistration_hash
            ),
            expected_geometry_preregistration_hash=expected_geometry_preregistration_hash,
            expected_cluster_preregistration_hash=expected_cluster_preregistration_hash,
        )
    except Exception:
        upstream_valid = False
    if not upstream_valid:
        return None
    if not _strata_registration_is_exact(
        strata_registration,
        cluster_preregistration,
        expected_registration_hash=expected_strata_registration_hash,
    ):
        return None

    document: dict[str, Any] = {
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "status": "PREREGISTERED_UNMOUNTED",
        "static_fingerprint": STATIC_FINGERPRINT,
        "binding_contract_hash": BINDING_CONTRACT_HASH,
        "geometry_complete_link_binding_contract_hash": (
            _geometry_binding.BINDING_CONTRACT_HASH
        ),
        "geometry_complete_link_binding_preregistration_hash": (
            expected_geometry_complete_link_binding_preregistration_hash
        ),
        "geometry_preregistration_hash": expected_geometry_preregistration_hash,
        "cluster_preregistration_hash": expected_cluster_preregistration_hash,
        "strata_registration_hash": expected_strata_registration_hash,
        "activation_sequence": list(ACTIVATION_SEQUENCE),
        "source_bindings": {
            "geometry_complete_link_binding": {
                "module": GEOMETRY_BINDING_MODULE,
                "contract_hash": _geometry_binding.BINDING_CONTRACT_HASH,
                "static_fingerprint": _geometry_binding.STATIC_FINGERPRINT,
            },
            "effective_budget_v3": {
                "module": EFFECTIVE_BUDGET_MODULE,
                "source_sha256": EFFECTIVE_BUDGET_IMPLEMENTATION_SHA256,
            },
            "preregistered_strata": {
                "module": STRATA_MODULE,
                "source_sha256": STRATA_IMPLEMENTATION_SHA256,
            },
        },
        "mounted": False,
        "synthetic_only": True,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": _permissions(),
    }
    document["preregistration_hash"] = _canonical_hash(document)
    return document


def verify_strategy_correlation_matrix_geometry_effective_bet_budget_binding_preregistration_v1(
    document: Any,
    geometry_complete_link_binding_preregistration: Any,
    geometry_preregistration: Any,
    cluster_preregistration: Any,
    strata_registration: Any,
    *,
    expected_budget_binding_preregistration_hash: Any,
    expected_geometry_complete_link_binding_preregistration_hash: Any,
    expected_geometry_preregistration_hash: Any,
    expected_cluster_preregistration_hash: Any,
    expected_strata_registration_hash: Any,
) -> bool:
    if not _is_exact_hash(expected_budget_binding_preregistration_hash):
        return False
    try:
        expected = build_strategy_correlation_matrix_geometry_effective_bet_budget_binding_preregistration_v1(
            geometry_complete_link_binding_preregistration,
            geometry_preregistration,
            cluster_preregistration,
            strata_registration,
            expected_geometry_complete_link_binding_preregistration_hash=(
                expected_geometry_complete_link_binding_preregistration_hash
            ),
            expected_geometry_preregistration_hash=expected_geometry_preregistration_hash,
            expected_cluster_preregistration_hash=expected_cluster_preregistration_hash,
            expected_strata_registration_hash=expected_strata_registration_hash,
        )
    except Exception:
        return False
    return bool(
        isinstance(document, dict)
        and expected is not None
        and _safe_hash(document, "preregistration_hash")
        == expected_budget_binding_preregistration_hash
        and compare_digest(
            expected["preregistration_hash"],
            expected_budget_binding_preregistration_hash,
        )
        and document == expected
    )


def _result(
    *,
    status: str,
    reason_code: str,
    budget_binding_preregistration: Any,
    geometry_complete_link_binding_evaluation: Any,
    strata_registration: Any,
    strata_gate: Any,
    trace: list[str],
    budget_consumer_invocation_attempted: bool = False,
    budget_document_verified: bool = False,
    trusted_budget: dict[str, Any] | None = None,
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "status": status,
        "reason_code": reason_code,
        "static_fingerprint": STATIC_FINGERPRINT,
        "binding_contract_hash": BINDING_CONTRACT_HASH,
        "budget_binding_preregistration_hash": _safe_hash(
            budget_binding_preregistration, "preregistration_hash"
        ),
        "geometry_complete_link_binding_evaluation_hash": _safe_hash(
            geometry_complete_link_binding_evaluation, "evaluation_hash"
        ),
        "strata_registration_hash": _safe_hash(
            strata_registration, "registration_hash"
        ),
        "strata_gate_hash": _safe_hash(strata_gate, "gate_hash"),
        "activation_sequence": list(ACTIVATION_SEQUENCE),
        "trace": list(trace),
        "budget_consumer_invocation_attempted": (
            budget_consumer_invocation_attempted
        ),
        "budget_document_verified": budget_document_verified,
        "effective_budget_status": (
            trusted_budget.get("status") if trusted_budget is not None else None
        ),
        "effective_budget_decision": (
            trusted_budget.get("decision") if trusted_budget is not None else None
        ),
        "effective_budget_document": deepcopy(trusted_budget),
        "mounted": False,
        "synthetic_only": True,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": _permissions(),
    }
    document["evaluation_hash"] = _canonical_hash(document)
    return document


def _budget_authority_is_locked(document: Any) -> bool:
    if not isinstance(document, dict):
        return False
    authority = document.get("authority")
    if not isinstance(authority, dict):
        return False
    false_fields = (
        "current_admission_allowed",
        "current_pointer_written",
        "live_order_allowed",
        "migration_allowed",
        "paper_authorized",
        "runtime_gate_activation_allowed",
        "writer_allowed",
    )
    return all(authority.get(field) is False for field in false_fields)


def evaluate_strategy_correlation_matrix_geometry_effective_bet_budget_binding_v1(
    budget_binding_preregistration: Any,
    geometry_complete_link_binding_preregistration: Any,
    geometry_preregistration: Any,
    geometry_gate_document: Any,
    geometry_complete_link_binding_evaluation: Any,
    cluster_preregistration: Any,
    correlation_matrix: Any,
    selection_cells: Any,
    strata_registration: Any,
    strata_gate: Any,
    *,
    expected_budget_binding_preregistration_hash: Any,
    expected_geometry_complete_link_binding_preregistration_hash: Any,
    expected_geometry_preregistration_hash: Any,
    expected_cluster_preregistration_hash: Any,
    expected_strata_registration_hash: Any,
    expected_geometry_complete_link_binding_evaluation_hash: Any,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
    equity: Any,
    positions: Any,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any = "LONG",
    max_cluster_gross_pct: Any = 45.0,
    risk_increasing: Any = True,
) -> dict[str, Any]:
    trace: list[str] = []
    common = {
        "budget_binding_preregistration": budget_binding_preregistration,
        "geometry_complete_link_binding_evaluation": (
            geometry_complete_link_binding_evaluation
        ),
        "strata_registration": strata_registration,
        "strata_gate": strata_gate,
        "trace": trace,
    }

    if not verify_strategy_correlation_matrix_geometry_effective_bet_budget_binding_preregistration_v1(
        budget_binding_preregistration,
        geometry_complete_link_binding_preregistration,
        geometry_preregistration,
        cluster_preregistration,
        strata_registration,
        expected_budget_binding_preregistration_hash=(
            expected_budget_binding_preregistration_hash
        ),
        expected_geometry_complete_link_binding_preregistration_hash=(
            expected_geometry_complete_link_binding_preregistration_hash
        ),
        expected_geometry_preregistration_hash=expected_geometry_preregistration_hash,
        expected_cluster_preregistration_hash=expected_cluster_preregistration_hash,
        expected_strata_registration_hash=expected_strata_registration_hash,
    ):
        return _result(
            status="UNKNOWN",
            reason_code="BUDGET_BINDING_PREREGISTRATION_INVALID",
            **common,
        )

    if not _is_exact_hash(
        expected_geometry_complete_link_binding_evaluation_hash
    ):
        upstream_valid = False
    else:
        try:
            upstream_valid = _geometry_binding.verify_strategy_correlation_matrix_geometry_complete_link_binding_evaluation_v1(
                geometry_complete_link_binding_evaluation,
                geometry_complete_link_binding_preregistration,
                geometry_preregistration,
                geometry_gate_document,
                cluster_preregistration,
                correlation_matrix,
                selection_cells,
                expected_evaluation_hash=(
                    expected_geometry_complete_link_binding_evaluation_hash
                ),
                expected_binding_preregistration_hash=(
                    expected_geometry_complete_link_binding_preregistration_hash
                ),
                expected_geometry_preregistration_hash=(
                    expected_geometry_preregistration_hash
                ),
                expected_cluster_preregistration_hash=(
                    expected_cluster_preregistration_hash
                ),
                strategy_id=strategy_id,
                variant_id=variant_id,
                lane=lane,
            )
        except Exception:
            upstream_valid = False
    if not upstream_valid:
        return _result(
            status="UNKNOWN",
            reason_code="GEOMETRY_COMPLETE_LINK_EVALUATION_INVALID",
            **common,
        )
    trace.append("GEOMETRY_COMPLETE_LINK_BINDING_EVALUATION_VERIFIED")

    if geometry_complete_link_binding_evaluation.get("status") != "PASS":
        return _result(
            status=(
                "BLOCK"
                if geometry_complete_link_binding_evaluation.get("status") == "BLOCK"
                else "UNKNOWN"
            ),
            reason_code="GEOMETRY_COMPLETE_LINK_EVALUATION_DID_NOT_PASS",
            **common,
        )

    complete_link_audit = geometry_complete_link_binding_evaluation.get(
        "complete_link_audit"
    )
    complete_link_gate = geometry_complete_link_binding_evaluation.get(
        "complete_link_gate"
    )
    if not isinstance(complete_link_audit, dict) or not isinstance(
        complete_link_gate, dict
    ):
        return _result(
            status="UNKNOWN",
            reason_code="GEOMETRY_COMPLETE_LINK_DOCUMENTS_MISSING",
            **common,
        )

    try:
        strata_gate_verification = _strata.verify_strategy_correlation_strata_gate(
            strata_gate,
            registration=strata_registration,
            complete_link_gate=complete_link_gate,
            source_preregistration=cluster_preregistration,
        )
    except Exception:
        strata_gate_verification = None
    if not _verification_passed(strata_gate_verification):
        return _result(
            status="UNKNOWN",
            reason_code="PREREGISTERED_STRATA_GATE_INVALID",
            **common,
        )
    trace.append("PREREGISTERED_STRATA_GATE_VERIFIED")

    budget_kwargs = {
        "strata_registration": strata_registration,
        "strata_gate": strata_gate,
        "complete_link_gate": complete_link_gate,
        "equity": equity,
        "positions": positions,
        "proposed_symbol": proposed_symbol,
        "proposed_notional": proposed_notional,
        "proposed_direction": proposed_direction,
        "max_cluster_gross_pct": max_cluster_gross_pct,
        "risk_increasing": risk_increasing,
    }
    trace.append("EFFECTIVE_BET_BUDGET_V3_INVOCATION_ATTEMPTED")
    try:
        budget_document = (
            _budget_v3.evaluate_strategy_correlation_cluster_effective_bet_budget_v3(
                cluster_preregistration,
                correlation_matrix,
                complete_link_audit,
                **budget_kwargs,
            )
        )
    except Exception:
        return _result(
            status="UNKNOWN",
            reason_code="EFFECTIVE_BET_BUDGET_CONSUMER_EXCEPTION",
            budget_consumer_invocation_attempted=True,
            **common,
        )
    if not isinstance(budget_document, dict):
        return _result(
            status="UNKNOWN",
            reason_code="EFFECTIVE_BET_BUDGET_DOCUMENT_INVALID",
            budget_consumer_invocation_attempted=True,
            **common,
        )

    try:
        expected_budget_document = _PINNED_BUDGET_EVALUATOR(
            cluster_preregistration,
            correlation_matrix,
            complete_link_audit,
            **budget_kwargs,
        )
    except Exception:
        return _result(
            status="UNKNOWN",
            reason_code="EFFECTIVE_BET_BUDGET_EXACT_REBUILD_EXCEPTION",
            budget_consumer_invocation_attempted=True,
            **common,
        )
    if (
        not _external_self_hash_is_exact(budget_document, "budget_v3_hash")
        or budget_document != expected_budget_document
    ):
        return _result(
            status="UNKNOWN",
            reason_code="EFFECTIVE_BET_BUDGET_DOCUMENT_INVALID",
            budget_consumer_invocation_attempted=True,
            **common,
        )

    try:
        budget_verification = (
            _budget_v3.verify_strategy_correlation_cluster_effective_bet_budget_v3(
                budget_document,
                cluster_preregistration,
                correlation_matrix,
                complete_link_audit,
                **budget_kwargs,
            )
        )
    except Exception:
        budget_verification = None
    if not _verification_passed(budget_verification):
        return _result(
            status="UNKNOWN",
            reason_code="EFFECTIVE_BET_BUDGET_VERIFICATION_FAILED",
            budget_consumer_invocation_attempted=True,
            **common,
        )
    trace.append("EFFECTIVE_BET_BUDGET_V3_VERIFIED")

    if not _budget_authority_is_locked(budget_document):
        return _result(
            status="UNKNOWN",
            reason_code="EFFECTIVE_BET_BUDGET_AUTHORITY_ESCALATION_REJECTED",
            budget_consumer_invocation_attempted=True,
            **common,
        )

    return _result(
        status="PASS",
        reason_code="GEOMETRY_BOUND_EFFECTIVE_BET_BUDGET_VERIFIED",
        budget_consumer_invocation_attempted=True,
        budget_document_verified=True,
        trusted_budget=budget_document,
        **common,
    )


def verify_strategy_correlation_matrix_geometry_effective_bet_budget_binding_evaluation_v1(
    document: Any,
    budget_binding_preregistration: Any,
    geometry_complete_link_binding_preregistration: Any,
    geometry_preregistration: Any,
    geometry_gate_document: Any,
    geometry_complete_link_binding_evaluation: Any,
    cluster_preregistration: Any,
    correlation_matrix: Any,
    selection_cells: Any,
    strata_registration: Any,
    strata_gate: Any,
    *,
    expected_evaluation_hash: Any,
    expected_budget_binding_preregistration_hash: Any,
    expected_geometry_complete_link_binding_preregistration_hash: Any,
    expected_geometry_preregistration_hash: Any,
    expected_cluster_preregistration_hash: Any,
    expected_strata_registration_hash: Any,
    expected_geometry_complete_link_binding_evaluation_hash: Any,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
    equity: Any,
    positions: Any,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any = "LONG",
    max_cluster_gross_pct: Any = 45.0,
    risk_increasing: Any = True,
) -> bool:
    if not _is_exact_hash(expected_evaluation_hash):
        return False
    try:
        expected = evaluate_strategy_correlation_matrix_geometry_effective_bet_budget_binding_v1(
            budget_binding_preregistration,
            geometry_complete_link_binding_preregistration,
            geometry_preregistration,
            geometry_gate_document,
            geometry_complete_link_binding_evaluation,
            cluster_preregistration,
            correlation_matrix,
            selection_cells,
            strata_registration,
            strata_gate,
            expected_budget_binding_preregistration_hash=(
                expected_budget_binding_preregistration_hash
            ),
            expected_geometry_complete_link_binding_preregistration_hash=(
                expected_geometry_complete_link_binding_preregistration_hash
            ),
            expected_geometry_preregistration_hash=expected_geometry_preregistration_hash,
            expected_cluster_preregistration_hash=expected_cluster_preregistration_hash,
            expected_strata_registration_hash=expected_strata_registration_hash,
            expected_geometry_complete_link_binding_evaluation_hash=(
                expected_geometry_complete_link_binding_evaluation_hash
            ),
            strategy_id=strategy_id,
            variant_id=variant_id,
            lane=lane,
            equity=equity,
            positions=positions,
            proposed_symbol=proposed_symbol,
            proposed_notional=proposed_notional,
            proposed_direction=proposed_direction,
            max_cluster_gross_pct=max_cluster_gross_pct,
            risk_increasing=risk_increasing,
        )
    except Exception:
        return False
    return bool(
        isinstance(document, dict)
        and _safe_hash(document, "evaluation_hash") == expected_evaluation_hash
        and compare_digest(expected["evaluation_hash"], expected_evaluation_hash)
        and document == expected
    )
