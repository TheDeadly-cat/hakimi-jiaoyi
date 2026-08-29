from __future__ import annotations

from typing import Any

from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_effective_bet_budget_binding_v1
    as budget_contract,
)
from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_lineage_history_coverage_gate_v1
    as history_contract,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import strict_sha256


PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-persisted-checkpoint-history-coverage-effective-"
    "budget-provenance-binding-preregistration-v1"
)
EVALUATION_SCHEMA_VERSION = (
    "strategy-correlation-persisted-checkpoint-history-coverage-effective-"
    "budget-provenance-binding-evaluation-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-persisted-checkpoint-history-coverage-"
    "effective-budget-provenance-binding-v1-synthetic-unmounted-dual-pin-lock-1"
)
IDENTITY_RELATIONSHIP_POLICY = (
    "EXACT_DUAL_SOURCE_PIN_NO_SEMANTIC_IDENTITY_EQUIVALENCE_CLAIM"
)
ACTIVATION_SEQUENCE = (
    "VERIFY_PROVENANCE_PREREGISTRATION",
    "VERIFY_BOUNDED_HISTORY_COVERAGE",
    "SHORT_CIRCUIT_NON_POSITIVE_HISTORY",
    "VERIFY_UNCERTAINTY_EFFECTIVE_BUDGET_BINDING",
    "PRESERVE_SOURCE_BUDGET_STATUS_WITH_AUTHORITY_LOCK",
)
BINDING_CONTRACT_HASH = strict_canonical_hash(
    {
        "activation_sequence": list(ACTIVATION_SEQUENCE),
        "evaluation_schema_version": EVALUATION_SCHEMA_VERSION,
        "history_gate_contract_hash": history_contract.GATE_CONTRACT_HASH,
        "identity_relationship_policy": IDENTITY_RELATIONSHIP_POLICY,
        "preregistration_schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "source_budget_binding_contract_hash": budget_contract.BINDING_CONTRACT_HASH,
        "static_fingerprint": STATIC_FINGERPRINT,
    }
)

_BUDGET_PREREGISTRATION_CONTEXT_KEYS = frozenset(
    {
        "budget_preregistration_verification_context",
        "geometry_budget_binding_preregistration",
        "uncertainty_preregistration",
        "uncertainty_preregistration_verification_context",
    }
)
_PREREGISTRATION_VERIFICATION_CONTEXT_KEYS = frozenset(
    {
        "budget_binding_preregistration_verification_context",
        "history_coverage_registration",
        "history_coverage_registration_receipt",
        "uncertainty_budget_binding_preregistration",
    }
)
_HISTORY_GATE_CONTEXT_KEYS = frozenset(
    {
        "expected_gate_hash",
        "lineage_items",
        "registration",
        "registration_receipt",
    }
)
_BUDGET_EVALUATION_CONTEXT_KEYS = frozenset(
    {
        "budget_evaluation_verification_context",
        "expected_evaluation_hash",
        "expected_preregistration_hash",
        "geometry_budget_binding_evaluation",
        "uncertainty_budget_binding_preregistration",
        "uncertainty_gate_document",
        "uncertainty_gate_verification_context",
    }
)

_VERIFY_HISTORY_COVERAGE = (
    history_contract.verify_strategy_correlation_persisted_checkpoint_history_coverage_gate_v1
)
_VERIFY_BUDGET_BINDING_EVALUATION = (
    budget_contract.verify_strategy_correlation_uncertainty_multi_window_effective_bet_budget_binding_evaluation_v1
)


def _authority() -> dict[str, bool]:
    return {
        "research_evidence_only": True,
        "semantic_identity_equivalence_claim_allowed": False,
        "effective_budget_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "http_registration_allowed": False,
        "runtime_activation_allowed": False,
        "writer_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "profitability_claim_allowed": False,
    }


def _facts(
    *,
    preregistration_verified: bool = False,
    history_verified: bool = False,
    history_positive: bool = False,
    budget_attempted: bool = False,
    budget_verified: bool = False,
) -> dict[str, bool]:
    return {
        "provenance_preregistration_exactly_verified": preregistration_verified,
        "history_coverage_exactly_verified": history_verified,
        "preregistered_bounded_history_coverage_positive": history_positive,
        "budget_verification_attempted": budget_attempted,
        "uncertainty_effective_budget_binding_exactly_verified": budget_verified,
        "dual_source_hashes_exactly_pinned": preregistration_verified,
        "semantic_study_identity_equivalence_verified": False,
        "effective_budget_activation_allowed": False,
        "raw_lineage_items_embedded": False,
        "raw_window_audits_embedded": False,
        "raw_budget_document_embedded": False,
        "runtime_consumer_bound": False,
        "runtime_mutations_performed": False,
        "synthetic_only": True,
        "mounted": False,
        "current_activated": False,
        "profitability_proven": False,
    }


def _safe(document: Any, key: str) -> Any:
    return document.get(key) if type(document) is dict else None


def _verify_budget_preregistration(
    document: Any,
    context: Any,
) -> bool:
    if type(document) is not dict or type(context) is not dict:
        return False
    if set(context) != _BUDGET_PREREGISTRATION_CONTEXT_KEYS:
        return False
    try:
        return bool(
            budget_contract.verify_strategy_correlation_uncertainty_multi_window_effective_bet_budget_binding_preregistration_v1(
                document,
                context["uncertainty_preregistration"],
                context["geometry_budget_binding_preregistration"],
                expected_preregistration_hash=document.get("preregistration_hash"),
                uncertainty_preregistration_verification_context=context[
                    "uncertainty_preregistration_verification_context"
                ],
                budget_preregistration_verification_context=context[
                    "budget_preregistration_verification_context"
                ],
            )
        )
    except Exception:
        return False


def build_strategy_correlation_persisted_checkpoint_history_coverage_effective_budget_provenance_binding_preregistration_v1(
    history_coverage_registration: Any,
    history_coverage_registration_receipt: Any,
    uncertainty_budget_binding_preregistration: Any,
    *,
    budget_binding_preregistration_verification_context: Any,
) -> dict[str, Any] | None:
    if (
        type(history_coverage_registration) is not dict
        or type(history_coverage_registration_receipt) is not dict
        or type(uncertainty_budget_binding_preregistration) is not dict
    ):
        return None
    try:
        history_registration_verified = history_contract.verify_strategy_correlation_persisted_checkpoint_history_coverage_registration_v1(
            history_coverage_registration_receipt,
            registration=history_coverage_registration,
        )
    except Exception:
        history_registration_verified = False
    if not history_registration_verified or not _verify_budget_preregistration(
        uncertainty_budget_binding_preregistration,
        budget_binding_preregistration_verification_context,
    ):
        return None

    document: dict[str, Any] = {
        "activation_sequence": list(ACTIVATION_SEQUENCE),
        "authority": _authority(),
        "binding_contract_hash": BINDING_CONTRACT_HASH,
        "blockers": [
            "SEMANTIC_STUDY_IDENTITY_EQUIVALENCE_NOT_VERIFIED",
            "EFFECTIVE_BUDGET_ACTIVATION_NOT_ALLOWED",
            "RUNTIME_CONSUMER_NOT_REGISTERED",
        ],
        "budget_binding_contract_hash": uncertainty_budget_binding_preregistration[
            "binding_contract_hash"
        ],
        "budget_binding_preregistration_hash": uncertainty_budget_binding_preregistration[
            "preregistration_hash"
        ],
        "budget_cluster_partition_hash": uncertainty_budget_binding_preregistration[
            "shared_cluster_partition_hash"
        ],
        "budget_symbol_order_hash": uncertainty_budget_binding_preregistration[
            "shared_symbol_order_hash"
        ],
        "budget_window_order_hash": uncertainty_budget_binding_preregistration[
            "window_order_hash"
        ],
        "facts": {
            "source_preregistrations_exactly_verified": True,
            "dual_source_hashes_exactly_pinned": True,
            "semantic_study_identity_equivalence_verified": False,
            "runtime_consumer_bound": False,
            "synthetic_only": True,
            "mounted": False,
        },
        "history_coverage_gate_contract_hash": history_contract.GATE_CONTRACT_HASH,
        "history_coverage_registration_receipt_hash": history_coverage_registration_receipt[
            "registration_receipt_hash"
        ],
        "history_id": history_coverage_registration["history_id"],
        "history_study_identity_hash": history_coverage_registration[
            "expected_study_identity_hash"
        ],
        "history_window_order_hash": history_coverage_registration[
            "expected_window_order_hash"
        ],
        "identity_relationship_policy": IDENTITY_RELATIONSHIP_POLICY,
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "source_window_order_hashes_equal": (
            history_coverage_registration["expected_window_order_hash"]
            == uncertainty_budget_binding_preregistration["window_order_hash"]
        ),
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PREREGISTERED",
    }
    return seal_strict_canonical_document(document, "preregistration_hash")


def verify_strategy_correlation_persisted_checkpoint_history_coverage_effective_budget_provenance_binding_preregistration_v1(
    document: Any,
    history_coverage_registration: Any,
    history_coverage_registration_receipt: Any,
    uncertainty_budget_binding_preregistration: Any,
    *,
    expected_preregistration_hash: Any,
    budget_binding_preregistration_verification_context: Any,
) -> bool:
    if (
        type(document) is not dict
        or not strict_sha256(expected_preregistration_hash)
        or document.get("preregistration_hash") != expected_preregistration_hash
    ):
        return False
    expected = build_strategy_correlation_persisted_checkpoint_history_coverage_effective_budget_provenance_binding_preregistration_v1(
        history_coverage_registration,
        history_coverage_registration_receipt,
        uncertainty_budget_binding_preregistration,
        budget_binding_preregistration_verification_context=(
            budget_binding_preregistration_verification_context
        ),
    )
    return expected is not None and strict_json_contract_equal(document, expected)


def _evaluation(
    preregistration: Any,
    history_gate: Any,
    budget_evaluation: Any,
    *,
    status: str,
    reason_code: str,
    preregistration_verified: bool,
    history_verified: bool,
    history_positive: bool,
    budget_attempted: bool,
    budget_verified: bool,
) -> dict[str, Any]:
    history_summary = _safe(history_gate, "summary")
    history_source = _safe(history_gate, "source")
    document: dict[str, Any] = {
        "authority": _authority(),
        "binding_contract_hash": BINDING_CONTRACT_HASH,
        "blockers": [
            "SEMANTIC_STUDY_IDENTITY_EQUIVALENCE_NOT_VERIFIED",
            "EFFECTIVE_BUDGET_ACTIVATION_NOT_ALLOWED",
            "RUNTIME_CONSUMER_NOT_REGISTERED",
        ],
        "budget_binding_evaluation_hash": _safe(
            budget_evaluation, "evaluation_hash"
        ),
        "budget_binding_status": _safe(budget_evaluation, "status"),
        "effective_budget_decision": _safe(
            budget_evaluation, "effective_budget_decision"
        ),
        "effective_budget_status": _safe(
            budget_evaluation, "effective_budget_status"
        ),
        "effective_budget_v3_hash": _safe(
            budget_evaluation, "effective_budget_v3_hash"
        ),
        "facts": _facts(
            preregistration_verified=preregistration_verified,
            history_verified=history_verified,
            history_positive=history_positive,
            budget_attempted=budget_attempted,
            budget_verified=budget_verified,
        ),
        "history_coverage_gate_hash": _safe(history_gate, "gate_hash"),
        "history_coverage_status": _safe(history_gate, "status"),
        "identity_relationship_policy": IDENTITY_RELATIONSHIP_POLICY,
        "preregistration_hash": _safe(preregistration, "preregistration_hash"),
        "reason_code": reason_code,
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "source": {
            "budget_binding_preregistration_hash": _safe(
                preregistration, "budget_binding_preregistration_hash"
            ),
            "history_coverage_registration_receipt_hash": _safe(
                preregistration, "history_coverage_registration_receipt_hash"
            ),
            "history_id": (
                history_source.get("history_id")
                if type(history_source) is dict
                else None
            ),
            "history_study_identity_hash": (
                history_source.get("study_identity_hash")
                if type(history_source) is dict
                else None
            ),
            "history_window_order_hash": (
                history_source.get("window_order_hash")
                if type(history_source) is dict
                else None
            ),
        },
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "summary": {
            "history_anchor_checkpoint_tree_size": (
                history_summary.get("anchor_checkpoint_tree_size")
                if type(history_summary) is dict
                else None
            ),
            "history_final_checkpoint_tree_size": (
                history_summary.get("final_checkpoint_tree_size")
                if type(history_summary) is dict
                else None
            ),
            "history_verified_segment_count": (
                history_summary.get("verified_segment_count")
                if type(history_summary) is dict
                else None
            ),
        },
        "trace": list(ACTIVATION_SEQUENCE),
    }
    return seal_strict_canonical_document(document, "evaluation_hash")


def evaluate_strategy_correlation_persisted_checkpoint_history_coverage_effective_budget_provenance_binding_v1(
    preregistration: Any,
    history_coverage_gate: Any,
    uncertainty_effective_budget_binding_evaluation: Any,
    *,
    expected_preregistration_hash: Any,
    preregistration_verification_context: Any,
    history_gate_verification_context: Any,
    budget_evaluation_verification_context: Any,
) -> dict[str, Any]:
    preregistration_context = preregistration_verification_context
    if (
        type(preregistration_context) is not dict
        or set(preregistration_context)
        != _PREREGISTRATION_VERIFICATION_CONTEXT_KEYS
    ):
        return _evaluation(
            preregistration,
            history_coverage_gate,
            uncertainty_effective_budget_binding_evaluation,
            status="UNKNOWN",
            reason_code="PREREGISTRATION_VERIFICATION_CONTEXT_INVALID",
            preregistration_verified=False,
            history_verified=False,
            history_positive=False,
            budget_attempted=False,
            budget_verified=False,
        )
    try:
        preregistration_verified = verify_strategy_correlation_persisted_checkpoint_history_coverage_effective_budget_provenance_binding_preregistration_v1(
            preregistration,
            preregistration_context["history_coverage_registration"],
            preregistration_context[
                "history_coverage_registration_receipt"
            ],
            preregistration_context[
                "uncertainty_budget_binding_preregistration"
            ],
            expected_preregistration_hash=expected_preregistration_hash,
            budget_binding_preregistration_verification_context=preregistration_context[
                "budget_binding_preregistration_verification_context"
            ],
        )
    except Exception:
        preregistration_verified = False
    if not preregistration_verified:
        return _evaluation(
            preregistration,
            history_coverage_gate,
            uncertainty_effective_budget_binding_evaluation,
            status="UNKNOWN",
            reason_code="PROVENANCE_PREREGISTRATION_NOT_VERIFIED",
            preregistration_verified=False,
            history_verified=False,
            history_positive=False,
            budget_attempted=False,
            budget_verified=False,
        )

    history_context = history_gate_verification_context
    if type(history_context) is not dict or set(history_context) != _HISTORY_GATE_CONTEXT_KEYS:
        history_verified = False
    else:
        try:
            history_verified = bool(
                _VERIFY_HISTORY_COVERAGE(
                    history_coverage_gate,
                    registration=history_context["registration"],
                    registration_receipt=history_context[
                        "registration_receipt"
                    ],
                    lineage_items=history_context["lineage_items"],
                    expected_gate_hash=history_context["expected_gate_hash"],
                )
            )
        except Exception:
            history_verified = False
    if not history_verified:
        return _evaluation(
            preregistration,
            history_coverage_gate,
            uncertainty_effective_budget_binding_evaluation,
            status="UNKNOWN",
            reason_code="HISTORY_COVERAGE_NOT_VERIFIED",
            preregistration_verified=True,
            history_verified=False,
            history_positive=False,
            budget_attempted=False,
            budget_verified=False,
        )

    history_positive = (
        _safe(history_coverage_gate, "status") == "PASS"
        and _safe(history_coverage_gate, "reason_code")
        == "PASS_PREREGISTERED_BOUNDED_PERSISTED_CHECKPOINT_HISTORY_COVERAGE"
        and _safe(history_coverage_gate, "facts").get(
            "preregistered_bounded_history_prefix_verified"
        )
        is True
    )
    if not history_positive:
        return _evaluation(
            preregistration,
            history_coverage_gate,
            uncertainty_effective_budget_binding_evaluation,
            status="BLOCK",
            reason_code="BOUNDED_HISTORY_COVERAGE_NOT_POSITIVE",
            preregistration_verified=True,
            history_verified=True,
            history_positive=False,
            budget_attempted=False,
            budget_verified=False,
        )

    budget_context = budget_evaluation_verification_context
    if (
        type(budget_context) is not dict
        or set(budget_context) != _BUDGET_EVALUATION_CONTEXT_KEYS
    ):
        budget_verified = False
    else:
        try:
            budget_verified = bool(
                _VERIFY_BUDGET_BINDING_EVALUATION(
                    uncertainty_effective_budget_binding_evaluation,
                    budget_context[
                        "uncertainty_budget_binding_preregistration"
                    ],
                    budget_context["uncertainty_gate_document"],
                    budget_context["geometry_budget_binding_evaluation"],
                    expected_evaluation_hash=budget_context[
                        "expected_evaluation_hash"
                    ],
                    expected_preregistration_hash=budget_context[
                        "expected_preregistration_hash"
                    ],
                    uncertainty_gate_verification_context=budget_context[
                        "uncertainty_gate_verification_context"
                    ],
                    budget_evaluation_verification_context=budget_context[
                        "budget_evaluation_verification_context"
                    ],
                )
            )
        except Exception:
            budget_verified = False
    if not budget_verified:
        return _evaluation(
            preregistration,
            history_coverage_gate,
            uncertainty_effective_budget_binding_evaluation,
            status="UNKNOWN",
            reason_code="UNCERTAINTY_EFFECTIVE_BUDGET_BINDING_NOT_VERIFIED",
            preregistration_verified=True,
            history_verified=True,
            history_positive=True,
            budget_attempted=True,
            budget_verified=False,
        )

    source_status = _safe(
        uncertainty_effective_budget_binding_evaluation, "status"
    )
    if source_status == "PASS":
        status = "PASS"
        reason = (
            "BOUNDED_HISTORY_AND_EFFECTIVE_BUDGET_PROVENANCE_BOUND_"
            "IDENTITY_EQUIVALENCE_UNPROVEN"
        )
    elif source_status == "BLOCK":
        status = "BLOCK"
        reason = "VERIFIED_EFFECTIVE_BUDGET_BINDING_BLOCK_PRESERVED"
    else:
        status = "UNKNOWN"
        reason = "VERIFIED_EFFECTIVE_BUDGET_BINDING_STATE_UNSUPPORTED"
    return _evaluation(
        preregistration,
        history_coverage_gate,
        uncertainty_effective_budget_binding_evaluation,
        status=status,
        reason_code=reason,
        preregistration_verified=True,
        history_verified=True,
        history_positive=True,
        budget_attempted=True,
        budget_verified=True,
    )


def verify_strategy_correlation_persisted_checkpoint_history_coverage_effective_budget_provenance_binding_v1(
    document: Any,
    preregistration: Any,
    history_coverage_gate: Any,
    uncertainty_effective_budget_binding_evaluation: Any,
    *,
    expected_evaluation_hash: Any,
    expected_preregistration_hash: Any,
    preregistration_verification_context: Any,
    history_gate_verification_context: Any,
    budget_evaluation_verification_context: Any,
) -> bool:
    if (
        type(document) is not dict
        or not strict_sha256(expected_evaluation_hash)
        or document.get("evaluation_hash") != expected_evaluation_hash
    ):
        return False
    try:
        expected = evaluate_strategy_correlation_persisted_checkpoint_history_coverage_effective_budget_provenance_binding_v1(
            preregistration,
            history_coverage_gate,
            uncertainty_effective_budget_binding_evaluation,
            expected_preregistration_hash=expected_preregistration_hash,
            preregistration_verification_context=preregistration_verification_context,
            history_gate_verification_context=history_gate_verification_context,
            budget_evaluation_verification_context=budget_evaluation_verification_context,
        )
    except Exception:
        return False
    return strict_json_contract_equal(document, expected)


__all__ = [
    "ACTIVATION_SEQUENCE",
    "BINDING_CONTRACT_HASH",
    "EVALUATION_SCHEMA_VERSION",
    "IDENTITY_RELATIONSHIP_POLICY",
    "PREREGISTRATION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_persisted_checkpoint_history_coverage_effective_budget_provenance_binding_preregistration_v1",
    "evaluate_strategy_correlation_persisted_checkpoint_history_coverage_effective_budget_provenance_binding_v1",
    "verify_strategy_correlation_persisted_checkpoint_history_coverage_effective_budget_provenance_binding_preregistration_v1",
    "verify_strategy_correlation_persisted_checkpoint_history_coverage_effective_budget_provenance_binding_v1",
]
