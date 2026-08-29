from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from exchange_terminal.application import (
    strategy_correlation_identity_bound_signed_replay_cursor_provider_conformance_bridge_candidate_v1
    as identity_bound_conformance_bridge,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_conformance_transcript_content_verifier_v1
    as transcript_content,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-identity-bound-signed-replay-cursor-provider-"
    "transcript-content-bridge-candidate-v1"
)
STATIC_FINGERPRINT = "20260825-identity-bound-provider-transcript-content-bridge-1"
STATUS = "OBSERVED_IDENTITY_BOUND_LOCAL_TRANSCRIPT_CONTENT_CANDIDATE"
DECISION = (
    "LOCAL_TRANSCRIPT_HASH_AND_SIZE_CHAIN_VERIFIED_"
    "EXTERNAL_AVAILABILITY_AND_EXECUTION_BLOCKED"
)
CONTENT_DECISION = "LOCAL_CONTENT_HASH_AND_SIZE_VERIFIED_EXTERNAL_AVAILABILITY_BLOCKED"
BINDING_DECISION = (
    "COMPLETE_TRANSCRIPT_MANIFEST_HASH_BINDING_VERIFIED_"
    "EXECUTION_SOURCE_TRUTH_BLOCKED"
)
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")

_IDENTITY_CONFORMANCE_CONTEXT_KEYS = frozenset(
    {
        "identity_bound_signed_receipt_bridge_document",
        "identity_bound_signed_receipt_bridge_verification_context",
        "conformance_quorum_evidence_document",
        "conformance_quorum_verification_context",
        "expected_identity_bound_signed_receipt_bridge_hash",
        "expected_conformance_quorum_evidence_hash",
        "expected_signed_receipt_evidence_hash",
        "expected_conformance_plan_hash",
        "expected_provider_preregistration_hash",
    }
)

_CONTENT_CONTEXT_KEYS = frozenset(
    {
        "content_bundle_documents",
        "transcript_binding_document",
        "transcript_manifest_documents",
        "quorum_evidence_document",
        "signed_report_documents",
        "plan_document",
        "provider_preregistration_document",
        "signed_receipt_evidence_document",
        "expected_transcript_binding_hash",
        "transcript_binding_verify_kwargs",
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


def _descriptive_authority_is_locked(value: Any) -> bool:
    if not isinstance(value, Mapping) or value.get("descriptive_only") is not True:
        return False
    return all(
        type(item) is bool and (item is True if key == "descriptive_only" else item is False)
        for key, item in value.items()
    )


def _authority_lock() -> dict[str, bool]:
    return {
        "transcript_artifact_available": False,
        "transcript_artifact_retrieved": False,
        "transcript_source_truth_verified": False,
        "runner_implementation_verified": False,
        "environment_manifest_verified": False,
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


def _verify_identity_conformance_bridge(
    document: Any,
    context: Any,
    *,
    expected_bridge_hash: str,
    expected_quorum_hash: str,
    expected_receipt_hash: str,
    expected_plan_hash: str,
    expected_preregistration_hash: str,
) -> bool:
    if not isinstance(context, Mapping) or set(context) != _IDENTITY_CONFORMANCE_CONTEXT_KEYS:
        return False
    if context["expected_conformance_quorum_evidence_hash"] != expected_quorum_hash:
        return False
    if context["expected_signed_receipt_evidence_hash"] != expected_receipt_hash:
        return False
    if context["expected_conformance_plan_hash"] != expected_plan_hash:
        return False
    if context["expected_provider_preregistration_hash"] != expected_preregistration_hash:
        return False
    try:
        return identity_bound_conformance_bridge.verify_strategy_correlation_identity_bound_signed_replay_cursor_provider_conformance_bridge_candidate_v1(
            document,
            context["identity_bound_signed_receipt_bridge_document"],
            context["identity_bound_signed_receipt_bridge_verification_context"],
            context["conformance_quorum_evidence_document"],
            context["conformance_quorum_verification_context"],
            expected_identity_bound_signed_provider_conformance_bridge_hash=expected_bridge_hash,
            expected_identity_bound_signed_receipt_bridge_hash=context[
                "expected_identity_bound_signed_receipt_bridge_hash"
            ],
            expected_conformance_quorum_evidence_hash=expected_quorum_hash,
            expected_signed_receipt_evidence_hash=expected_receipt_hash,
            expected_conformance_plan_hash=expected_plan_hash,
            expected_provider_preregistration_hash=expected_preregistration_hash,
        )
    except (KeyError, TypeError, ValueError):
        return False


def _verify_content_evidence(
    document: Any,
    context: Any,
    *,
    expected_content_hash: str,
    expected_binding_hash: str,
) -> bool:
    if not isinstance(context, Mapping) or set(context) != _CONTENT_CONTEXT_KEYS:
        return False
    if context["expected_transcript_binding_hash"] != expected_binding_hash:
        return False
    try:
        return transcript_content.verify_replay_cursor_provider_conformance_transcript_content_v1(
            document,
            context["content_bundle_documents"],
            context["transcript_binding_document"],
            context["transcript_manifest_documents"],
            context["quorum_evidence_document"],
            context["signed_report_documents"],
            context["plan_document"],
            context["provider_preregistration_document"],
            context["signed_receipt_evidence_document"],
            expected_content_verification_hash=expected_content_hash,
            expected_transcript_binding_hash=expected_binding_hash,
            transcript_binding_verify_kwargs=context[
                "transcript_binding_verify_kwargs"
            ],
        )
    except (KeyError, TypeError, ValueError):
        return False


def evaluate_strategy_correlation_identity_bound_signed_replay_cursor_provider_transcript_content_bridge_candidate_v1(
    identity_bound_conformance_bridge_document: Any,
    identity_bound_conformance_bridge_verification_context: Any,
    transcript_content_evidence_document: Any,
    transcript_content_verification_context: Any,
    *,
    expected_identity_bound_conformance_bridge_hash: Any,
    expected_content_verification_hash: Any,
    expected_transcript_binding_hash: Any,
    expected_conformance_quorum_evidence_hash: Any,
    expected_signed_receipt_evidence_hash: Any,
    expected_conformance_plan_hash: Any,
    expected_provider_preregistration_hash: Any,
) -> dict[str, Any] | None:
    expected_hashes = (
        expected_identity_bound_conformance_bridge_hash,
        expected_content_verification_hash,
        expected_transcript_binding_hash,
        expected_conformance_quorum_evidence_hash,
        expected_signed_receipt_evidence_hash,
        expected_conformance_plan_hash,
        expected_provider_preregistration_hash,
    )
    if not all(_is_hash(value) for value in expected_hashes):
        return None
    if not isinstance(identity_bound_conformance_bridge_document, Mapping):
        return None
    if not isinstance(identity_bound_conformance_bridge_verification_context, Mapping):
        return None
    if not isinstance(transcript_content_evidence_document, Mapping):
        return None
    if not isinstance(transcript_content_verification_context, Mapping):
        return None

    identity_source = identity_bound_conformance_bridge_document.get("source")
    identity_provider = identity_bound_conformance_bridge_document.get("provider")
    identity_facts = identity_bound_conformance_bridge_document.get("facts")
    content_source = transcript_content_evidence_document.get("source")
    content_facts = transcript_content_evidence_document.get("facts")
    binding_document = transcript_content_verification_context.get(
        "transcript_binding_document"
    )
    if not all(
        isinstance(value, Mapping)
        for value in (
            identity_source,
            identity_provider,
            identity_facts,
            content_source,
            content_facts,
            binding_document,
        )
    ):
        return None
    binding_source = binding_document.get("source")
    binding_facts = binding_document.get("facts")
    if not isinstance(binding_source, Mapping) or not isinstance(binding_facts, Mapping):
        return None

    if identity_bound_conformance_bridge_document.get(
        "identity_bound_signed_provider_conformance_bridge_hash"
    ) != expected_identity_bound_conformance_bridge_hash:
        return None
    if transcript_content_evidence_document.get("content_verification_hash") != expected_content_verification_hash:
        return None
    if content_source.get("transcript_binding_hash") != expected_transcript_binding_hash:
        return None
    if binding_document.get("transcript_binding_hash") != expected_transcript_binding_hash:
        return None

    identity_expected = {
        "conformance_quorum_evidence_hash": expected_conformance_quorum_evidence_hash,
        "signed_receipt_evidence_hash": expected_signed_receipt_evidence_hash,
        "conformance_plan_hash": expected_conformance_plan_hash,
        "provider_preregistration_hash": expected_provider_preregistration_hash,
    }
    if any(identity_source.get(key) != value for key, value in identity_expected.items()):
        return None
    binding_expected = {
        "quorum_evidence_hash": expected_conformance_quorum_evidence_hash,
        "signed_receipt_evidence_hash": expected_signed_receipt_evidence_hash,
        "conformance_plan_hash": expected_conformance_plan_hash,
    }
    if any(binding_source.get(key) != value for key, value in binding_expected.items()):
        return None

    identity_conformance_context = identity_bound_conformance_bridge_verification_context.get(
        "conformance_quorum_verification_context"
    )
    if not isinstance(identity_conformance_context, Mapping):
        return None
    shared_pairs = (
        (
            identity_bound_conformance_bridge_verification_context.get(
                "conformance_quorum_evidence_document"
            ),
            transcript_content_verification_context.get("quorum_evidence_document"),
        ),
        (
            identity_conformance_context.get("signed_report_documents"),
            transcript_content_verification_context.get("signed_report_documents"),
        ),
        (
            identity_conformance_context.get("plan_document"),
            transcript_content_verification_context.get("plan_document"),
        ),
        (
            identity_conformance_context.get("provider_preregistration_document"),
            transcript_content_verification_context.get(
                "provider_preregistration_document"
            ),
        ),
        (
            identity_conformance_context.get("signed_receipt_evidence_document"),
            transcript_content_verification_context.get(
                "signed_receipt_evidence_document"
            ),
        ),
    )
    if any(not _strict_equal(left, right) for left, right in shared_pairs):
        return None

    plan_document = transcript_content_verification_context.get("plan_document")
    preregistration_document = transcript_content_verification_context.get(
        "provider_preregistration_document"
    )
    receipt_evidence = transcript_content_verification_context.get(
        "signed_receipt_evidence_document"
    )
    quorum_evidence = transcript_content_verification_context.get(
        "quorum_evidence_document"
    )
    if not all(
        isinstance(value, Mapping)
        for value in (
            plan_document,
            preregistration_document,
            receipt_evidence,
            quorum_evidence,
        )
    ):
        return None
    if plan_document.get("conformance_plan_hash") != expected_conformance_plan_hash:
        return None
    if preregistration_document.get("preregistration_hash") != expected_provider_preregistration_hash:
        return None
    if receipt_evidence.get("verification_evidence_hash") != expected_signed_receipt_evidence_hash:
        return None
    if quorum_evidence.get("quorum_evidence_hash") != expected_conformance_quorum_evidence_hash:
        return None
    preregistration_identity = preregistration_document.get("identity")
    if not isinstance(preregistration_identity, Mapping):
        return None
    if preregistration_identity.get("registry_id") != identity_provider.get("registry_id"):
        return None

    if identity_bound_conformance_bridge_document.get("status") != identity_bound_conformance_bridge.STATUS:
        return None
    if identity_bound_conformance_bridge_document.get("permission_state") != "BLOCKED":
        return None
    if identity_bound_conformance_bridge_document.get("consumer_status") != "UNMOUNTED_CANDIDATE":
        return None
    if not _all_false_authority(identity_bound_conformance_bridge_document.get("authority")):
        return None
    if identity_facts.get("local_observer_signature_quorum_exactly_verified") is not True:
        return None
    if identity_facts.get("external_provider_conformance_verified") is not False:
        return None

    if binding_document.get("status") != "PASS":
        return None
    if binding_document.get("decision") != BINDING_DECISION:
        return None
    if binding_document.get("admission_status") != "BLOCKED":
        return None
    if not _descriptive_authority_is_locked(binding_document.get("authority")):
        return None
    if binding_facts.get("all_case_transcript_evidence_hashes_bound") is not True:
        return None
    if binding_facts.get("all_passing_reports_have_exact_transcript_manifests") is not True:
        return None
    for key in (
        "transcript_artifacts_retrieved",
        "transcript_artifact_content_verified",
        "runner_implementation_verified",
        "environment_manifest_verified",
        "observer_test_execution_source_truth_verified",
        "external_provider_conformance_verified",
        "execution_verified",
        "durable_commit_verified",
        "profitability_proven",
    ):
        if binding_facts.get(key) is not False:
            return None

    if transcript_content_evidence_document.get("status") != "PASS":
        return None
    if transcript_content_evidence_document.get("decision") != CONTENT_DECISION:
        return None
    if transcript_content_evidence_document.get("admission_status") != "BLOCKED":
        return None
    if not _descriptive_authority_is_locked(
        transcript_content_evidence_document.get("authority")
    ):
        return None
    for key in (
        "all_bound_content_bundles_exact",
        "local_component_hashes_verified",
        "local_component_sizes_bounded",
        "upstream_transcript_binding_exact",
    ):
        if content_facts.get(key) is not True:
            return None
    for key in (
        "external_artifact_retrieval_verified",
        "public_artifact_availability_verified",
        "external_persistence_verified",
        "runner_implementation_verified",
        "environment_manifest_verified",
        "observer_test_execution_source_truth_verified",
        "external_provider_conformance_verified",
        "execution_verified",
        "provider_called_by_evaluator",
        "profitability_proven",
    ):
        if content_facts.get(key) is not False:
            return None

    if not _verify_identity_conformance_bridge(
        identity_bound_conformance_bridge_document,
        identity_bound_conformance_bridge_verification_context,
        expected_bridge_hash=expected_identity_bound_conformance_bridge_hash,
        expected_quorum_hash=expected_conformance_quorum_evidence_hash,
        expected_receipt_hash=expected_signed_receipt_evidence_hash,
        expected_plan_hash=expected_conformance_plan_hash,
        expected_preregistration_hash=expected_provider_preregistration_hash,
    ):
        return None
    if not _verify_content_evidence(
        transcript_content_evidence_document,
        transcript_content_verification_context,
        expected_content_hash=expected_content_verification_hash,
        expected_binding_hash=expected_transcript_binding_hash,
    ):
        return None

    manifests = transcript_content_verification_context.get(
        "transcript_manifest_documents"
    )
    bundles = transcript_content_verification_context.get("content_bundle_documents")
    if not isinstance(manifests, (list, tuple)) or not isinstance(bundles, (list, tuple)):
        return None
    transcript_set_fingerprint = _digest(
        {
            "manifest_hashes": sorted(
                item.get("transcript_manifest_hash")
                for item in manifests
                if isinstance(item, Mapping)
            ),
            "content_bundle_hashes": sorted(
                item.get("content_bundle_hash")
                for item in bundles
                if isinstance(item, Mapping)
            ),
        }
    )
    if transcript_set_fingerprint is None:
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
            "identity_bound_conformance_bridge_hash": expected_identity_bound_conformance_bridge_hash,
            "content_verification_hash": expected_content_verification_hash,
            "transcript_binding_hash": expected_transcript_binding_hash,
            "conformance_quorum_evidence_hash": expected_conformance_quorum_evidence_hash,
            "signed_receipt_evidence_hash": expected_signed_receipt_evidence_hash,
            "conformance_plan_hash": expected_conformance_plan_hash,
            "provider_preregistration_hash": expected_provider_preregistration_hash,
            "replay_cursor_cas_binding_hash": identity_source.get(
                "replay_cursor_cas_binding_hash"
            ),
            "provider_command_hash": identity_source.get("provider_command_hash"),
            "transcript_set_fingerprint_sha256": transcript_set_fingerprint,
        },
        "provider": {
            "registry_id": identity_provider.get("registry_id"),
            "registry_revision": identity_provider.get("registry_revision"),
            "outcome": identity_provider.get("outcome"),
        },
        "transcript": {
            "manifest_count": len(manifests),
            "content_bundle_count": len(bundles),
            "content_encoding": content_source.get("content_encoding"),
            "claim_scope": "LOCAL_CALLER_SUPPLIED_CONTENT_HASH_AND_SIZE_ONLY",
        },
        "facts": {
            "identity_bound_conformance_bridge_exactly_verified": True,
            "quorum_reports_cross_bound": True,
            "transcript_manifest_preimages_exactly_bound": True,
            "local_content_hashes_and_sizes_exactly_verified": True,
            "provider_called_by_bridge": False,
            "external_artifact_retrieval_verified": False,
            "public_artifact_availability_verified": False,
            "runner_implementation_verified": False,
            "environment_manifest_verified": False,
            "observer_test_execution_source_truth_verified": False,
            "external_provider_conformance_verified": False,
            "raw_transcript_content_exposed": False,
            "raw_manifest_or_bundle_exposed": False,
        },
        "blockers": [
            "EXTERNAL_ARTIFACT_RETRIEVAL_UNVERIFIED",
            "PUBLIC_ARTIFACT_AVAILABILITY_UNVERIFIED",
            "RUNNER_IMPLEMENTATION_PROVENANCE_UNVERIFIED",
            "ENVIRONMENT_MANIFEST_PROVENANCE_UNVERIFIED",
            "OBSERVER_TEST_EXECUTION_SOURCE_TRUTH_UNVERIFIED",
            "EXTERNAL_PROVIDER_EXECUTION_UNVERIFIED",
            "EXTERNAL_PROVIDER_CONFORMANCE_UNVERIFIED",
            "RUNTIME_CONSUMER_UNMOUNTED",
            "CURRENT_ADMISSION_BLOCKED",
        ],
        "decision_path": [
            {
                "stage": "SOURCE",
                "state": "CALLER_SUPPLIED_CONTENT_HASH_AND_SIZE_VERIFIED",
            },
            {
                "stage": "GAP",
                "state": "EXTERNAL_RETRIEVAL_PROVENANCE_AND_EXECUTION_UNVERIFIED",
            },
            {"stage": "MATURITY", "state": "UNMOUNTED_LOCAL_CONTENT_CANDIDATE"},
            {"stage": "PERMISSION", "state": "BLOCKED"},
        ],
        "authority": _authority_lock(),
    }
    return _seal(core, "identity_bound_provider_transcript_content_bridge_hash")


def verify_strategy_correlation_identity_bound_signed_replay_cursor_provider_transcript_content_bridge_candidate_v1(
    document: Any,
    identity_bound_conformance_bridge_document: Any,
    identity_bound_conformance_bridge_verification_context: Any,
    transcript_content_evidence_document: Any,
    transcript_content_verification_context: Any,
    *,
    expected_identity_bound_provider_transcript_content_bridge_hash: Any,
    expected_identity_bound_conformance_bridge_hash: Any,
    expected_content_verification_hash: Any,
    expected_transcript_binding_hash: Any,
    expected_conformance_quorum_evidence_hash: Any,
    expected_signed_receipt_evidence_hash: Any,
    expected_conformance_plan_hash: Any,
    expected_provider_preregistration_hash: Any,
) -> bool:
    if not _is_hash(expected_identity_bound_provider_transcript_content_bridge_hash):
        return False
    evaluated = evaluate_strategy_correlation_identity_bound_signed_replay_cursor_provider_transcript_content_bridge_candidate_v1(
        identity_bound_conformance_bridge_document,
        identity_bound_conformance_bridge_verification_context,
        transcript_content_evidence_document,
        transcript_content_verification_context,
        expected_identity_bound_conformance_bridge_hash=expected_identity_bound_conformance_bridge_hash,
        expected_content_verification_hash=expected_content_verification_hash,
        expected_transcript_binding_hash=expected_transcript_binding_hash,
        expected_conformance_quorum_evidence_hash=expected_conformance_quorum_evidence_hash,
        expected_signed_receipt_evidence_hash=expected_signed_receipt_evidence_hash,
        expected_conformance_plan_hash=expected_conformance_plan_hash,
        expected_provider_preregistration_hash=expected_provider_preregistration_hash,
    )
    return (
        evaluated is not None
        and evaluated.get("identity_bound_provider_transcript_content_bridge_hash")
        == expected_identity_bound_provider_transcript_content_bridge_hash
        and _strict_equal(document, evaluated)
    )
