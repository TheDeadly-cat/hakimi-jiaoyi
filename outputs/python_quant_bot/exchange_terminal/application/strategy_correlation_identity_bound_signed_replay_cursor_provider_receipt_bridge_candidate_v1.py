from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from enum import Enum
import hashlib
import json
import math
import re
from typing import Any

from exchange_terminal.application import (
    strategy_correlation_cluster_v9_position_derived_snapshot_replay_cursor_cas_binding_v1
    as replay_cursor_cas_binding,
)
from exchange_terminal.application import (
    strategy_correlation_identity_bound_position_derived_replay_cursor_cas_bridge_candidate_v1
    as identity_bound_cas_bridge,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_signed_receipt_v1
    as signed_provider_receipt,
)
from exchange_terminal.application.ports import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_v1
    as replay_cursor_provider,
)


SCHEMA_VERSION = (
    "strategy-correlation-identity-bound-signed-replay-cursor-provider-receipt-"
    "bridge-candidate-v1"
)
STATIC_FINGERPRINT = "20260825-identity-bound-signed-provider-receipt-bridge-candidate-1"
STATUS = "OBSERVED_IDENTITY_BOUND_LOCAL_SIGNED_PROVIDER_RECEIPT_CANDIDATE"
DECISION = (
    "LOCAL_SIGNATURE_AND_IDENTITY_BOUND_CAS_VERIFIED_"
    "EXTERNAL_PROVIDER_SOURCE_TRUTH_BLOCKED"
)
SIGNED_RECEIPT_DECISION = (
    "LOCAL_RECEIPT_SIGNATURE_VERIFIED_EXTERNAL_PROVIDER_SOURCE_TRUTH_BLOCKED"
)
CAS_ADVANCED_OUTCOME = "ADVANCED_IN_RETURNED_CURSOR"
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")

_IDENTITY_CONTEXT_KEYS = frozenset(
    {
        "identity_bound_result",
        "identity_bound_verification_context",
        "freshness_binding_result",
        "freshness_binding_verification_context",
        "replay_cursor_cas_binding_result",
        "attestation",
        "base_cursor",
        "observed_cursor",
        "expected_identity_bound_post_merge_hash",
        "expected_freshness_binding_hash",
        "expected_replay_cursor_cas_binding_hash",
        "request_nonce_hash",
        "expected_observed_cursor_hash",
    }
)

_SIGNED_RECEIPT_CONTEXT_KEYS = frozenset(
    {
        "signed_receipt_document",
        "receipt_claim_document",
        "registration_evidence_document",
        "signed_registration_document",
        "registration_claim_document",
        "preregistration_document",
        "public_key_spki_base64",
        "signature_base64",
        "expected_signed_receipt_hash",
        "expected_receipt_claim_hash",
        "expected_registration_evidence_hash",
        "registration_verification_kwargs",
    }
)


def _is_hash(value: Any) -> bool:
    return isinstance(value, str) and HASH_PATTERN.fullmatch(value) is not None


def _json_value(value: Any, *, depth: int = 0) -> Any:
    if depth > 24:
        raise TypeError("canonical value nesting is too deep")
    if isinstance(value, Enum):
        return _json_value(value.value, depth=depth + 1)
    if value is None or type(value) in {str, int, bool}:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise TypeError("non-finite numbers are forbidden")
        return value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _json_value(getattr(value, field.name), depth=depth + 1)
            for field in fields(value)
        }
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError("canonical object keys must be exact strings")
            normalized[key] = _json_value(item, depth=depth + 1)
        return normalized
    if isinstance(value, (list, tuple)):
        return [_json_value(item, depth=depth + 1) for item in value]
    raise TypeError(f"unsupported canonical value: {type(value).__name__}")


def _canonical_bytes(value: Any) -> bytes | None:
    try:
        normalized = _json_value(value)
        return json.dumps(
            normalized,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError):
        return None


def _digest(value: Any) -> str | None:
    payload = _canonical_bytes(value)
    if payload is None:
        return None
    return hashlib.sha256(payload).hexdigest()


def _strict_equal(left: Any, right: Any) -> bool:
    left_bytes = _canonical_bytes(left)
    right_bytes = _canonical_bytes(right)
    return left_bytes is not None and left_bytes == right_bytes


def _seal(core: Mapping[str, Any], hash_field: str) -> dict[str, Any] | None:
    if hash_field in core:
        return None
    digest = _digest(core)
    if digest is None:
        return None
    return {**dict(core), hash_field: digest}


def _authority_lock() -> dict[str, bool]:
    return {
        "provider_identity_verified": False,
        "provider_source_truth_verified": False,
        "provider_conformance_verified": False,
        "cursor_write_performed": False,
        "atomic_storage_commit_verified": False,
        "durable_commit_verified": False,
        "linearizable_read_verified": False,
        "replay_registry_persistence_verified": False,
        "runtime_consumer_bound": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "profitability_proven": False,
    }


def _authority_is_locked(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and bool(value)
        and all(type(item) is bool and item is False for item in value.values())
    )


def _command_hash_verifies(command: Any) -> bool:
    snapshot = _json_value(command)
    if not isinstance(snapshot, dict):
        return False
    command_hash = snapshot.pop("command_hash", None)
    return _is_hash(command_hash) and _digest(snapshot) == command_hash


def _verify_identity_bound_cas_bridge(
    document: Any,
    context: Any,
    replay_cursor_cas_binding_result: Any,
    *,
    expected_identity_bound_cas_bridge_hash: str,
    expected_replay_cursor_cas_binding_hash: str,
) -> bool:
    if not isinstance(context, Mapping) or set(context) != _IDENTITY_CONTEXT_KEYS:
        return False
    if not _strict_equal(
        context["replay_cursor_cas_binding_result"],
        replay_cursor_cas_binding_result,
    ):
        return False
    if context["expected_replay_cursor_cas_binding_hash"] != expected_replay_cursor_cas_binding_hash:
        return False
    try:
        return identity_bound_cas_bridge.verify_strategy_correlation_identity_bound_position_derived_replay_cursor_cas_bridge_candidate_v1(
            document,
            context["identity_bound_result"],
            context["identity_bound_verification_context"],
            context["freshness_binding_result"],
            context["freshness_binding_verification_context"],
            context["replay_cursor_cas_binding_result"],
            context["attestation"],
            context["base_cursor"],
            context["observed_cursor"],
            expected_identity_bound_cas_bridge_hash=expected_identity_bound_cas_bridge_hash,
            expected_identity_bound_post_merge_hash=context[
                "expected_identity_bound_post_merge_hash"
            ],
            expected_freshness_binding_hash=context["expected_freshness_binding_hash"],
            expected_replay_cursor_cas_binding_hash=expected_replay_cursor_cas_binding_hash,
            request_nonce_hash=context["request_nonce_hash"],
            expected_observed_cursor_hash=context["expected_observed_cursor_hash"],
        )
    except (KeyError, TypeError, ValueError):
        return False


def _verify_signed_provider_receipt(
    evidence_document: Any,
    context: Any,
    command: Any,
    provider_result: Any,
    *,
    expected_verification_evidence_hash: str,
) -> bool:
    if not isinstance(context, Mapping) or set(context) != _SIGNED_RECEIPT_CONTEXT_KEYS:
        return False
    try:
        return signed_provider_receipt.verify_signed_replay_cursor_provider_receipt_evidence_v1(
            evidence_document,
            context["signed_receipt_document"],
            context["receipt_claim_document"],
            command,
            provider_result,
            context["registration_evidence_document"],
            context["signed_registration_document"],
            context["registration_claim_document"],
            context["preregistration_document"],
            expected_verification_evidence_hash=expected_verification_evidence_hash,
            public_key_spki_base64=context["public_key_spki_base64"],
            signature_base64=context["signature_base64"],
            expected_signed_receipt_hash=context["expected_signed_receipt_hash"],
            expected_receipt_claim_hash=context["expected_receipt_claim_hash"],
            expected_registration_evidence_hash=context[
                "expected_registration_evidence_hash"
            ],
            registration_verification_kwargs=context[
                "registration_verification_kwargs"
            ],
        )
    except (KeyError, TypeError, ValueError):
        return False


def evaluate_strategy_correlation_identity_bound_signed_replay_cursor_provider_receipt_bridge_candidate_v1(
    identity_bound_cas_bridge_document: Any,
    identity_bound_cas_verification_context: Any,
    replay_cursor_cas_binding_result: Any,
    provider_command: Any,
    provider_result: Any,
    signed_receipt_evidence_document: Any,
    signed_receipt_verification_context: Any,
    *,
    expected_identity_bound_cas_bridge_hash: Any,
    expected_replay_cursor_cas_binding_hash: Any,
    expected_provider_command_hash: Any,
    expected_signed_receipt_verification_evidence_hash: Any,
) -> dict[str, Any] | None:
    expected_hashes = (
        expected_identity_bound_cas_bridge_hash,
        expected_replay_cursor_cas_binding_hash,
        expected_provider_command_hash,
        expected_signed_receipt_verification_evidence_hash,
    )
    if not all(_is_hash(value) for value in expected_hashes):
        return None
    if not isinstance(identity_bound_cas_bridge_document, Mapping):
        return None
    if not isinstance(signed_receipt_evidence_document, Mapping):
        return None
    if type(replay_cursor_cas_binding_result) is not replay_cursor_cas_binding.V9PositionDerivedSnapshotReplayCursorCasBindingResultV1:
        return None
    if type(provider_command) is not replay_cursor_provider.ReplayCursorCompareAndAdvanceCommandV1:
        return None
    if type(provider_result) is not replay_cursor_provider.ReplayCursorCompareAndAdvanceResultV1:
        return None
    if type(provider_result.outcome) is not replay_cursor_provider.ReplayCursorProviderOutcomeV1:
        return None
    if provider_result.outcome is not replay_cursor_provider.ReplayCursorProviderOutcomeV1.ADVANCED:
        return None
    if replay_cursor_cas_binding_result.outcome != CAS_ADVANCED_OUTCOME:
        return None
    if replay_cursor_cas_binding_result.returned_cursor_changed is not True:
        return None
    if replay_cursor_cas_binding_result.expected_cursor_hash != replay_cursor_cas_binding_result.observed_cursor_hash:
        return None
    if provider_result.observed_cursor_hash == provider_result.returned_cursor_hash:
        return None
    if not isinstance(provider_result.receipt_document, Mapping):
        return None
    if provider_command.command_hash != expected_provider_command_hash:
        return None
    if not _command_hash_verifies(provider_command):
        return None

    command_bindings = (
        provider_command.stream_id == replay_cursor_cas_binding_result.stream_id,
        provider_command.projection_preregistration_hash
        == replay_cursor_cas_binding_result.projection_preregistration_hash,
        provider_command.intent_hash == replay_cursor_cas_binding_result.intent_hash,
        provider_command.freshness_result_fingerprint_sha256
        == replay_cursor_cas_binding_result.freshness_result_fingerprint_sha256,
        provider_command.candidate_attestation_hash
        == replay_cursor_cas_binding_result.attestation_hash,
        provider_command.candidate_sequence
        == replay_cursor_cas_binding_result.candidate_sequence,
        provider_command.request_nonce_hash
        == replay_cursor_cas_binding_result.request_nonce_hash,
        provider_command.transition_receipt_hash
        == replay_cursor_cas_binding_result.receipt_hash,
        provider_command.base_cursor.cursor_hash
        == replay_cursor_cas_binding_result.expected_cursor_hash,
        provider_command.proposed_cursor.cursor_hash
        == replay_cursor_cas_binding_result.returned_cursor_hash,
        _strict_equal(
            provider_command.proposed_cursor,
            replay_cursor_cas_binding_result.returned_cursor,
        ),
    )
    result_bindings = (
        provider_result.command_hash == provider_command.command_hash,
        provider_result.intent_hash == provider_command.intent_hash,
        provider_result.observed_cursor_hash
        == replay_cursor_cas_binding_result.observed_cursor_hash,
        provider_result.returned_cursor_hash
        == replay_cursor_cas_binding_result.returned_cursor_hash,
        provider_result.observed_cursor_hash == provider_command.base_cursor.cursor_hash,
        provider_result.returned_cursor_hash == provider_command.proposed_cursor.cursor_hash,
    )
    if not all(command_bindings) or not all(result_bindings):
        return None

    locked_cas_fields = (
        "cursor_write_performed",
        "runtime_consumer_bound",
        "current_admission_allowed",
        "paper_authorized",
        "live_order_allowed",
        "profitability_proven",
    )
    if any(
        getattr(replay_cursor_cas_binding_result, field, None) is not False
        for field in locked_cas_fields
    ):
        return None
    if replay_cursor_cas_binding_result.source_binding_exactly_verified is not True:
        return None
    if replay_cursor_cas_binding_result.cas_intent_exactly_bound is not True:
        return None

    if not _verify_identity_bound_cas_bridge(
        identity_bound_cas_bridge_document,
        identity_bound_cas_verification_context,
        replay_cursor_cas_binding_result,
        expected_identity_bound_cas_bridge_hash=expected_identity_bound_cas_bridge_hash,
        expected_replay_cursor_cas_binding_hash=expected_replay_cursor_cas_binding_hash,
    ):
        return None
    if identity_bound_cas_bridge_document.get("identity_bound_cas_bridge_hash") != expected_identity_bound_cas_bridge_hash:
        return None
    source = identity_bound_cas_bridge_document.get("source")
    if not isinstance(source, Mapping):
        return None
    if source.get("replay_cursor_cas_binding_hash") != expected_replay_cursor_cas_binding_hash:
        return None
    if replay_cursor_cas_binding_result.binding_hash != expected_replay_cursor_cas_binding_hash:
        return None

    if signed_receipt_evidence_document.get("verification_evidence_hash") != expected_signed_receipt_verification_evidence_hash:
        return None
    if signed_receipt_evidence_document.get("status") != "PASS":
        return None
    if signed_receipt_evidence_document.get("decision") != SIGNED_RECEIPT_DECISION:
        return None
    if not _authority_is_locked(signed_receipt_evidence_document.get("authority")):
        return None
    if not _verify_signed_provider_receipt(
        signed_receipt_evidence_document,
        signed_receipt_verification_context,
        provider_command,
        provider_result,
        expected_verification_evidence_hash=expected_signed_receipt_verification_evidence_hash,
    ):
        return None

    provider_result_fingerprint = _digest(provider_result)
    provider_receipt_document_hash = _digest(provider_result.receipt_document)
    if provider_result_fingerprint is None or provider_receipt_document_hash is None:
        return None
    signed_context = signed_receipt_verification_context
    core = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": STATUS,
        "permission_state": "BLOCKED",
        "permission": "RESEARCH_ONLY_NO_ADMISSION",
        "decision": DECISION,
        "consumer_status": "UNMOUNTED_CANDIDATE",
        "source": {
            "identity_bound_cas_bridge_hash": expected_identity_bound_cas_bridge_hash,
            "replay_cursor_cas_binding_hash": expected_replay_cursor_cas_binding_hash,
            "provider_command_hash": provider_command.command_hash,
            "provider_result_fingerprint_sha256": provider_result_fingerprint,
            "provider_receipt_document_sha256": provider_receipt_document_hash,
            "signed_receipt_verification_evidence_hash": expected_signed_receipt_verification_evidence_hash,
            "signed_receipt_hash": signed_context["expected_signed_receipt_hash"],
            "receipt_claim_hash": signed_context["expected_receipt_claim_hash"],
            "registration_evidence_hash": signed_context[
                "expected_registration_evidence_hash"
            ],
            "stream_id": provider_command.stream_id,
            "projection_preregistration_hash": provider_command.projection_preregistration_hash,
            "intent_hash": provider_command.intent_hash,
            "attestation_hash": provider_command.candidate_attestation_hash,
            "request_nonce_hash": provider_command.request_nonce_hash,
            "observed_cursor_hash": provider_result.observed_cursor_hash,
            "returned_cursor_hash": provider_result.returned_cursor_hash,
        },
        "provider": {
            "outcome": provider_result.outcome.value,
            "registry_id": provider_result.registry_id,
            "registry_revision": provider_result.registry_revision,
        },
        "facts": {
            "identity_bound_cas_bridge_exactly_verified": True,
            "provider_command_exactly_cross_bound": True,
            "provider_result_exactly_cross_bound": True,
            "cas_to_provider_outcome_mapping_exactly_verified": True,
            "signed_receipt_exactly_verified": True,
            "local_receipt_signature_verified": True,
            "raw_receipt_exposed": False,
            "raw_cursor_exposed": False,
            "signature_material_exposed": False,
            "external_provider_identity_verified": False,
            "external_provider_source_truth_verified": False,
        },
        "blockers": [
            "EXTERNAL_PROVIDER_IDENTITY_UNVERIFIED",
            "EXTERNAL_PROVIDER_SOURCE_TRUTH_UNVERIFIED",
            "PROVIDER_CONFORMANCE_UNVERIFIED",
            "DURABLE_CURSOR_COMMIT_UNVERIFIED",
            "RUNTIME_CONSUMER_UNMOUNTED",
            "CURRENT_ADMISSION_BLOCKED",
        ],
        "decision_path": [
            {
                "stage": "SOURCE",
                "state": "LOCAL_SIGNATURE_VERIFIED_EXTERNAL_SOURCE_TRUTH_UNVERIFIED",
            },
            {
                "stage": "GAP",
                "state": "PROVIDER_CONFORMANCE_AND_DURABLE_COMMIT_UNVERIFIED",
            },
            {"stage": "MATURITY", "state": "UNMOUNTED_CANDIDATE"},
            {"stage": "PERMISSION", "state": "BLOCKED"},
        ],
        "authority": _authority_lock(),
    }
    return _seal(core, "identity_bound_signed_provider_receipt_bridge_hash")


def verify_strategy_correlation_identity_bound_signed_replay_cursor_provider_receipt_bridge_candidate_v1(
    document: Any,
    identity_bound_cas_bridge_document: Any,
    identity_bound_cas_verification_context: Any,
    replay_cursor_cas_binding_result: Any,
    provider_command: Any,
    provider_result: Any,
    signed_receipt_evidence_document: Any,
    signed_receipt_verification_context: Any,
    *,
    expected_identity_bound_signed_provider_receipt_bridge_hash: Any,
    expected_identity_bound_cas_bridge_hash: Any,
    expected_replay_cursor_cas_binding_hash: Any,
    expected_provider_command_hash: Any,
    expected_signed_receipt_verification_evidence_hash: Any,
) -> bool:
    if not _is_hash(expected_identity_bound_signed_provider_receipt_bridge_hash):
        return False
    evaluated = evaluate_strategy_correlation_identity_bound_signed_replay_cursor_provider_receipt_bridge_candidate_v1(
        identity_bound_cas_bridge_document,
        identity_bound_cas_verification_context,
        replay_cursor_cas_binding_result,
        provider_command,
        provider_result,
        signed_receipt_evidence_document,
        signed_receipt_verification_context,
        expected_identity_bound_cas_bridge_hash=expected_identity_bound_cas_bridge_hash,
        expected_replay_cursor_cas_binding_hash=expected_replay_cursor_cas_binding_hash,
        expected_provider_command_hash=expected_provider_command_hash,
        expected_signed_receipt_verification_evidence_hash=expected_signed_receipt_verification_evidence_hash,
    )
    return (
        evaluated is not None
        and evaluated.get("identity_bound_signed_provider_receipt_bridge_hash")
        == expected_identity_bound_signed_provider_receipt_bridge_hash
        and _strict_equal(document, evaluated)
    )
