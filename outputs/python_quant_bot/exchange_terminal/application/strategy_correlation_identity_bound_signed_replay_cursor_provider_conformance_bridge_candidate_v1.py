from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from exchange_terminal.application import (
    strategy_correlation_identity_bound_signed_replay_cursor_provider_receipt_bridge_candidate_v1
    as identity_bound_signed_receipt_bridge,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_conformance_evidence_v1
    as provider_conformance,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-identity-bound-signed-replay-cursor-provider-"
    "conformance-bridge-candidate-v1"
)
STATIC_FINGERPRINT = "20260825-identity-bound-signed-provider-conformance-bridge-1"
STATUS = "OBSERVED_IDENTITY_BOUND_LOCAL_OBSERVER_QUORUM_CANDIDATE"
DECISION = (
    "LOCAL_RECEIPT_AND_OBSERVER_SIGNATURES_VERIFIED_"
    "EXTERNAL_PROVIDER_CONFORMANCE_BLOCKED"
)
CONFORMANCE_DECISION = (
    "LOCAL_OBSERVER_SIGNATURE_QUORUM_VERIFIED_"
    "EXTERNAL_EXECUTION_AND_PROVIDER_CONFORMANCE_BLOCKED"
)
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")

_IDENTITY_BRIDGE_CONTEXT_KEYS = frozenset(
    {
        "identity_bound_cas_bridge_document",
        "identity_bound_cas_verification_context",
        "replay_cursor_cas_binding_result",
        "provider_command",
        "provider_result",
        "signed_receipt_evidence_document",
        "signed_receipt_verification_context",
        "expected_identity_bound_cas_bridge_hash",
        "expected_replay_cursor_cas_binding_hash",
        "expected_provider_command_hash",
        "expected_signed_receipt_verification_evidence_hash",
    }
)

_CONFORMANCE_CONTEXT_KEYS = frozenset(
    {
        "signed_report_documents",
        "plan_document",
        "provider_preregistration_document",
        "signed_receipt_evidence_document",
        "observer_registrations",
        "provider_preregistration_kwargs",
        "signed_receipt_verify_args",
        "signed_receipt_verify_kwargs",
        "expected_signed_receipt_evidence_hash",
    }
)


def _is_hash(value: Any) -> bool:
    return isinstance(value, str) and HASH_PATTERN.fullmatch(value) is not None


def _strict_equal(left: Any, right: Any) -> bool:
    try:
        return strict_json_contract_equal(left, right)
    except (TypeError, ValueError, RecursionError):
        return False


def _digest(value: Any) -> str | None:
    try:
        digest = strict_canonical_hash(value)
    except (TypeError, ValueError, RecursionError):
        return None
    return digest if _is_hash(digest) else None


def _seal(core: Mapping[str, Any], hash_field: str) -> dict[str, Any] | None:
    try:
        sealed = seal_strict_canonical_document(core, hash_field)
    except (TypeError, ValueError, RecursionError):
        return None
    return sealed if isinstance(sealed, dict) and _is_hash(sealed.get(hash_field)) else None


def _all_false_authority(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and bool(value)
        and all(type(item) is bool and item is False for item in value.values())
    )


def _conformance_authority_is_local_only(value: Any) -> bool:
    if not isinstance(value, Mapping) or value.get("descriptive_only") is not True:
        return False
    return all(
        type(item) is bool and (item is True if key == "descriptive_only" else item is False)
        for key, item in value.items()
    )


def _authority_lock() -> dict[str, bool]:
    return {
        "observer_identity_verified": False,
        "observer_independence_verified": False,
        "observer_test_execution_source_truth_verified": False,
        "external_provider_identity_verified": False,
        "external_provider_source_truth_verified": False,
        "external_provider_conformance_verified": False,
        "provider_activation_allowed": False,
        "cursor_write_performed": False,
        "durable_commit_verified": False,
        "runtime_consumer_bound": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "profitability_proven": False,
    }


def _verify_identity_bridge(
    document: Any,
    context: Any,
    *,
    expected_identity_bridge_hash: str,
    expected_signed_receipt_evidence_hash: str,
) -> bool:
    if not isinstance(context, Mapping) or set(context) != _IDENTITY_BRIDGE_CONTEXT_KEYS:
        return False
    if context["expected_signed_receipt_verification_evidence_hash"] != expected_signed_receipt_evidence_hash:
        return False
    try:
        return identity_bound_signed_receipt_bridge.verify_strategy_correlation_identity_bound_signed_replay_cursor_provider_receipt_bridge_candidate_v1(
            document,
            context["identity_bound_cas_bridge_document"],
            context["identity_bound_cas_verification_context"],
            context["replay_cursor_cas_binding_result"],
            context["provider_command"],
            context["provider_result"],
            context["signed_receipt_evidence_document"],
            context["signed_receipt_verification_context"],
            expected_identity_bound_signed_provider_receipt_bridge_hash=expected_identity_bridge_hash,
            expected_identity_bound_cas_bridge_hash=context[
                "expected_identity_bound_cas_bridge_hash"
            ],
            expected_replay_cursor_cas_binding_hash=context[
                "expected_replay_cursor_cas_binding_hash"
            ],
            expected_provider_command_hash=context["expected_provider_command_hash"],
            expected_signed_receipt_verification_evidence_hash=expected_signed_receipt_evidence_hash,
        )
    except (KeyError, TypeError, ValueError):
        return False


def _verify_conformance_quorum(
    evidence_document: Any,
    context: Any,
    *,
    expected_quorum_evidence_hash: str,
    expected_signed_receipt_evidence_hash: str,
) -> bool:
    if not isinstance(context, Mapping) or set(context) != _CONFORMANCE_CONTEXT_KEYS:
        return False
    if context["expected_signed_receipt_evidence_hash"] != expected_signed_receipt_evidence_hash:
        return False
    try:
        return provider_conformance.verify_replay_cursor_provider_conformance_observer_quorum_v1(
            evidence_document,
            context["signed_report_documents"],
            context["plan_document"],
            context["provider_preregistration_document"],
            context["signed_receipt_evidence_document"],
            expected_quorum_evidence_hash=expected_quorum_evidence_hash,
            observer_registrations=context["observer_registrations"],
            provider_preregistration_kwargs=context[
                "provider_preregistration_kwargs"
            ],
            signed_receipt_verify_args=context["signed_receipt_verify_args"],
            signed_receipt_verify_kwargs=context["signed_receipt_verify_kwargs"],
            expected_signed_receipt_evidence_hash=expected_signed_receipt_evidence_hash,
        )
    except (KeyError, TypeError, ValueError):
        return False


def evaluate_strategy_correlation_identity_bound_signed_replay_cursor_provider_conformance_bridge_candidate_v1(
    identity_bound_signed_receipt_bridge_document: Any,
    identity_bound_signed_receipt_bridge_verification_context: Any,
    conformance_quorum_evidence_document: Any,
    conformance_quorum_verification_context: Any,
    *,
    expected_identity_bound_signed_receipt_bridge_hash: Any,
    expected_conformance_quorum_evidence_hash: Any,
    expected_signed_receipt_evidence_hash: Any,
    expected_conformance_plan_hash: Any,
    expected_provider_preregistration_hash: Any,
) -> dict[str, Any] | None:
    expected_hashes = (
        expected_identity_bound_signed_receipt_bridge_hash,
        expected_conformance_quorum_evidence_hash,
        expected_signed_receipt_evidence_hash,
        expected_conformance_plan_hash,
        expected_provider_preregistration_hash,
    )
    if not all(_is_hash(value) for value in expected_hashes):
        return None
    if not isinstance(identity_bound_signed_receipt_bridge_document, Mapping):
        return None
    if not isinstance(conformance_quorum_evidence_document, Mapping):
        return None
    if not isinstance(identity_bound_signed_receipt_bridge_verification_context, Mapping):
        return None
    if not isinstance(conformance_quorum_verification_context, Mapping):
        return None

    identity_source = identity_bound_signed_receipt_bridge_document.get("source")
    identity_provider = identity_bound_signed_receipt_bridge_document.get("provider")
    identity_facts = identity_bound_signed_receipt_bridge_document.get("facts")
    conformance_source = conformance_quorum_evidence_document.get("source")
    conformance_facts = conformance_quorum_evidence_document.get("facts")
    if not all(
        isinstance(value, Mapping)
        for value in (
            identity_source,
            identity_provider,
            identity_facts,
            conformance_source,
            conformance_facts,
        )
    ):
        return None

    if identity_bound_signed_receipt_bridge_document.get(
        "identity_bound_signed_provider_receipt_bridge_hash"
    ) != expected_identity_bound_signed_receipt_bridge_hash:
        return None
    if conformance_quorum_evidence_document.get("quorum_evidence_hash") != expected_conformance_quorum_evidence_hash:
        return None
    if identity_source.get("signed_receipt_verification_evidence_hash") != expected_signed_receipt_evidence_hash:
        return None
    if conformance_source.get("signed_receipt_evidence_hash") != expected_signed_receipt_evidence_hash:
        return None
    if conformance_source.get("conformance_plan_hash") != expected_conformance_plan_hash:
        return None
    if conformance_source.get("provider_preregistration_hash") != expected_provider_preregistration_hash:
        return None

    identity_receipt_evidence = identity_bound_signed_receipt_bridge_verification_context.get(
        "signed_receipt_evidence_document"
    )
    conformance_receipt_evidence = conformance_quorum_verification_context.get(
        "signed_receipt_evidence_document"
    )
    if not _strict_equal(identity_receipt_evidence, conformance_receipt_evidence):
        return None
    if not isinstance(identity_receipt_evidence, Mapping):
        return None
    if identity_receipt_evidence.get("verification_evidence_hash") != expected_signed_receipt_evidence_hash:
        return None

    plan_document = conformance_quorum_verification_context.get("plan_document")
    preregistration_document = conformance_quorum_verification_context.get(
        "provider_preregistration_document"
    )
    preregistration_kwargs = conformance_quorum_verification_context.get(
        "provider_preregistration_kwargs"
    )
    if not all(
        isinstance(value, Mapping)
        for value in (plan_document, preregistration_document, preregistration_kwargs)
    ):
        return None
    if plan_document.get("conformance_plan_hash") != expected_conformance_plan_hash:
        return None
    if preregistration_document.get("preregistration_hash") != expected_provider_preregistration_hash:
        return None
    preregistration_identity = preregistration_document.get("identity")
    if not isinstance(preregistration_identity, Mapping):
        return None
    registry_id = identity_provider.get("registry_id")
    if not isinstance(registry_id, str) or not registry_id:
        return None
    if preregistration_identity.get("registry_id") != registry_id:
        return None
    if preregistration_kwargs.get("registry_id") != registry_id:
        return None

    if identity_bound_signed_receipt_bridge_document.get("status") != identity_bound_signed_receipt_bridge.STATUS:
        return None
    if identity_bound_signed_receipt_bridge_document.get("permission_state") != "BLOCKED":
        return None
    if identity_bound_signed_receipt_bridge_document.get("consumer_status") != "UNMOUNTED_CANDIDATE":
        return None
    if not _all_false_authority(identity_bound_signed_receipt_bridge_document.get("authority")):
        return None
    if identity_facts.get("signed_receipt_exactly_verified") is not True:
        return None
    if identity_facts.get("external_provider_source_truth_verified") is not False:
        return None

    if conformance_quorum_evidence_document.get("status") != "PASS":
        return None
    if conformance_quorum_evidence_document.get("decision") != CONFORMANCE_DECISION:
        return None
    if conformance_quorum_evidence_document.get("admission_status") != "BLOCKED":
        return None
    if not _conformance_authority_is_local_only(
        conformance_quorum_evidence_document.get("authority")
    ):
        return None
    required_true_facts = (
        "signed_observer_report_quorum_verified",
        "upstream_signed_receipt_evidence_exact",
        "all_required_case_results_claimed_by_quorum",
    )
    required_false_facts = (
        "execution_verified",
        "external_provider_conformance_verified",
        "observer_identities_verified",
        "observer_independence_source_truth_verified",
        "observer_test_execution_source_truth_verified",
        "provider_called_by_evaluator",
        "provider_endpoint_verified",
        "provider_implementation_verified",
        "atomic_compare_and_advance_verified",
        "durable_commit_verified",
        "linearizable_read_after_write_verified",
        "restart_recovery_verified",
        "rollback_resistance_verified",
        "profitability_proven",
    )
    if any(conformance_facts.get(key) is not True for key in required_true_facts):
        return None
    if any(conformance_facts.get(key) is not False for key in required_false_facts):
        return None

    if not _verify_identity_bridge(
        identity_bound_signed_receipt_bridge_document,
        identity_bound_signed_receipt_bridge_verification_context,
        expected_identity_bridge_hash=expected_identity_bound_signed_receipt_bridge_hash,
        expected_signed_receipt_evidence_hash=expected_signed_receipt_evidence_hash,
    ):
        return None
    if not _verify_conformance_quorum(
        conformance_quorum_evidence_document,
        conformance_quorum_verification_context,
        expected_quorum_evidence_hash=expected_conformance_quorum_evidence_hash,
        expected_signed_receipt_evidence_hash=expected_signed_receipt_evidence_hash,
    ):
        return None

    observer_quorum_fingerprint = _digest(
        {
            "observer_results": conformance_quorum_evidence_document.get(
                "observer_results"
            ),
            "quorum_summary": conformance_quorum_evidence_document.get(
                "quorum_summary"
            ),
        }
    )
    signed_reports = conformance_quorum_verification_context.get(
        "signed_report_documents"
    )
    if observer_quorum_fingerprint is None or not isinstance(signed_reports, (list, tuple)):
        return None

    core = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": STATUS,
        "permission_state": "BLOCKED",
        "permission": "RESEARCH_ONLY_NO_ADMISSION",
        "decision": DECISION,
        "consumer_status": "UNMOUNTED_CANDIDATE",
        "source": {
            "identity_bound_signed_receipt_bridge_hash": expected_identity_bound_signed_receipt_bridge_hash,
            "conformance_quorum_evidence_hash": expected_conformance_quorum_evidence_hash,
            "signed_receipt_evidence_hash": expected_signed_receipt_evidence_hash,
            "conformance_plan_hash": expected_conformance_plan_hash,
            "provider_preregistration_hash": expected_provider_preregistration_hash,
            "replay_cursor_cas_binding_hash": identity_source.get(
                "replay_cursor_cas_binding_hash"
            ),
            "provider_command_hash": identity_source.get("provider_command_hash"),
            "observer_quorum_fingerprint_sha256": observer_quorum_fingerprint,
        },
        "provider": {
            "registry_id": registry_id,
            "registry_revision": identity_provider.get("registry_revision"),
            "outcome": identity_provider.get("outcome"),
        },
        "quorum": {
            "signed_report_count": len(signed_reports),
            "claim_scope": "LOCAL_OBSERVER_SIGNATURE_QUORUM_ONLY",
            "all_required_cases_claimed_passed": True,
            "observer_identity_source_truth_verified": False,
            "observer_execution_source_truth_verified": False,
        },
        "facts": {
            "identity_bound_signed_receipt_bridge_exactly_verified": True,
            "signed_receipt_evidence_cross_bound": True,
            "provider_registration_cross_bound": True,
            "conformance_plan_exactly_bound": True,
            "local_observer_signature_quorum_exactly_verified": True,
            "all_required_case_results_claimed_by_quorum": True,
            "provider_called_by_bridge": False,
            "provider_execution_verified": False,
            "external_provider_conformance_verified": False,
            "observer_identity_verified": False,
            "observer_independence_verified": False,
            "observer_test_execution_source_truth_verified": False,
            "raw_observer_reports_exposed": False,
            "observer_key_or_signature_material_exposed": False,
        },
        "blockers": [
            "OBSERVER_IDENTITY_SOURCE_TRUTH_UNVERIFIED",
            "OBSERVER_INDEPENDENCE_SOURCE_TRUTH_UNVERIFIED",
            "OBSERVER_TEST_EXECUTION_SOURCE_TRUTH_UNVERIFIED",
            "EXTERNAL_PROVIDER_EXECUTION_UNVERIFIED",
            "EXTERNAL_PROVIDER_CONFORMANCE_UNVERIFIED",
            "DURABLE_COMMIT_UNVERIFIED",
            "RUNTIME_CONSUMER_UNMOUNTED",
            "CURRENT_ADMISSION_BLOCKED",
        ],
        "decision_path": [
            {
                "stage": "SOURCE",
                "state": "LOCAL_RECEIPT_AND_OBSERVER_SIGNATURES_VERIFIED",
            },
            {
                "stage": "GAP",
                "state": "EXTERNAL_EXECUTION_AND_OBSERVER_SOURCE_TRUTH_UNVERIFIED",
            },
            {"stage": "MATURITY", "state": "UNMOUNTED_LOCAL_QUORUM_CANDIDATE"},
            {"stage": "PERMISSION", "state": "BLOCKED"},
        ],
        "authority": _authority_lock(),
    }
    return _seal(core, "identity_bound_signed_provider_conformance_bridge_hash")


def verify_strategy_correlation_identity_bound_signed_replay_cursor_provider_conformance_bridge_candidate_v1(
    document: Any,
    identity_bound_signed_receipt_bridge_document: Any,
    identity_bound_signed_receipt_bridge_verification_context: Any,
    conformance_quorum_evidence_document: Any,
    conformance_quorum_verification_context: Any,
    *,
    expected_identity_bound_signed_provider_conformance_bridge_hash: Any,
    expected_identity_bound_signed_receipt_bridge_hash: Any,
    expected_conformance_quorum_evidence_hash: Any,
    expected_signed_receipt_evidence_hash: Any,
    expected_conformance_plan_hash: Any,
    expected_provider_preregistration_hash: Any,
) -> bool:
    if not _is_hash(expected_identity_bound_signed_provider_conformance_bridge_hash):
        return False
    evaluated = evaluate_strategy_correlation_identity_bound_signed_replay_cursor_provider_conformance_bridge_candidate_v1(
        identity_bound_signed_receipt_bridge_document,
        identity_bound_signed_receipt_bridge_verification_context,
        conformance_quorum_evidence_document,
        conformance_quorum_verification_context,
        expected_identity_bound_signed_receipt_bridge_hash=expected_identity_bound_signed_receipt_bridge_hash,
        expected_conformance_quorum_evidence_hash=expected_conformance_quorum_evidence_hash,
        expected_signed_receipt_evidence_hash=expected_signed_receipt_evidence_hash,
        expected_conformance_plan_hash=expected_conformance_plan_hash,
        expected_provider_preregistration_hash=expected_provider_preregistration_hash,
    )
    return (
        evaluated is not None
        and evaluated.get("identity_bound_signed_provider_conformance_bridge_hash")
        == expected_identity_bound_signed_provider_conformance_bridge_hash
        and _strict_equal(document, evaluated)
    )
