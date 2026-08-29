"""Consumer-only candidate receipt for expected-gate-hash timing evidence."""

from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import (
    strict_locked_fields,
    strict_nonempty_string,
    strict_sha256,
    strict_utc_second_timestamp,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_invalid,
)


ANCHOR_PAYLOAD_SCHEMA_VERSION = (
    "strategy-correlation-expected-gate-hash-anchor-payload-v1"
)
RECEIPT_SCHEMA_VERSION = (
    "strategy-correlation-expected-gate-hash-timing-receipt-candidate-v1"
)
VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-expected-gate-hash-timing-receipt-candidate-"
    "verification-v1"
)

STABILITY_GATE_STAGE = "CLUSTER_STABILITY_REPORT20"
TEMPORAL_GATE_STAGE = "CLUSTER_TEMPORAL_STABILITY_REPORT21"
SUPPORTED_GATE_STAGES = (STABILITY_GATE_STAGE, TEMPORAL_GATE_STAGE)
STATUS_CANDIDATE_RECEIPT = "CANDIDATE_RECEIPT"

AUTHORITY_GAPS = (
    "EXTERNAL_ANCHOR_AUTHENTICITY_NOT_VERIFIED",
    "IMMUTABLE_PERSISTENCE_NOT_VERIFIED",
    "ANCHOR_UNIQUENESS_NOT_VERIFIED",
    "ANCHOR_FRESHNESS_NOT_VERIFIED",
    "ROLLBACK_RESISTANCE_NOT_VERIFIED",
)

_IDENTITY_FIELDS = ("strategy_id", "variant_id", "lane")
_SOURCE_FIELDS = (
    "source_uncertainty_audit",
    "correlation_matrix",
    "selection_cells",
)
_STABILITY_BINDING_FIELDS = frozenset(
    (*_IDENTITY_FIELDS, *_SOURCE_FIELDS, "expected_stability_gate_hash")
)
_TEMPORAL_BINDING_FIELDS = frozenset(
    (*_IDENTITY_FIELDS, *_SOURCE_FIELDS, "expected_temporal_stability_gate_hash")
)
_LOCK_FIELDS = (
    "anchor_receipt_verifier_implemented",
    "external_anchor_authenticity_verified",
    "immutable_persistence_verified",
    "anchor_uniqueness_verified",
    "anchor_freshness_verified",
    "rollback_resistance_verified",
    "timing_authority_verified",
    "preregistration_authority_verified",
    "formal_registry_bound",
    "formal_registry_activation_allowed",
    "writer_implemented",
    "current_writer_activation_allowed",
    "current_admission_allowed",
)


def _permissions() -> dict[str, bool]:
    return {
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _strict_token(value: Any) -> bool:
    return strict_nonempty_string(value) and value == value.strip()


def _identity(value: Any) -> tuple[str, str, str] | None:
    if type(value) is not dict:
        return None
    identity = tuple(value.get(field) for field in _IDENTITY_FIELDS)
    if not all(_strict_token(item) for item in identity):
        return None
    return identity


def _binding_commitments(
    gate_stage: Any,
    bindings: Any,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]] | None:
    if gate_stage == STABILITY_GATE_STAGE:
        required_fields = _STABILITY_BINDING_FIELDS
        gate_hash_field = "expected_stability_gate_hash"
    elif gate_stage == TEMPORAL_GATE_STAGE:
        required_fields = _TEMPORAL_BINDING_FIELDS
        gate_hash_field = "expected_temporal_stability_gate_hash"
    else:
        return None
    if type(bindings) is not list or not bindings:
        return None

    indexed: dict[
        tuple[str, str, str],
        tuple[dict[str, str], dict[str, str]],
    ] = {}
    for binding in bindings:
        identity = _identity(binding)
        if (
            identity is None
            or type(binding) is not dict
            or frozenset(binding) != required_fields
            or type(binding.get("source_uncertainty_audit")) is not dict
            or type(binding.get("correlation_matrix")) is not dict
            or type(binding.get("selection_cells")) is not list
            or not strict_sha256(binding.get(gate_hash_field))
            or identity in indexed
        ):
            return None
        try:
            source_link = {
                "strategy_id": identity[0],
                "variant_id": identity[1],
                "lane": identity[2],
                "source_uncertainty_audit_hash": strict_canonical_hash(
                    binding["source_uncertainty_audit"]
                ),
                "correlation_matrix_hash": strict_canonical_hash(
                    binding["correlation_matrix"]
                ),
                "selection_cells_hash": strict_canonical_hash(
                    binding["selection_cells"]
                ),
            }
        except (TypeError, ValueError):
            return None
        gate_commitment = {
            "strategy_id": identity[0],
            "variant_id": identity[1],
            "lane": identity[2],
            "expected_gate_hash": binding[gate_hash_field],
        }
        indexed[identity] = (source_link, gate_commitment)

    identities: list[dict[str, str]] = []
    source_links: list[dict[str, str]] = []
    gate_commitments: list[dict[str, str]] = []
    for identity in sorted(indexed):
        identities.append(
            {
                "strategy_id": identity[0],
                "variant_id": identity[1],
                "lane": identity[2],
            }
        )
        source_link, gate_commitment = indexed[identity]
        source_links.append(source_link)
        gate_commitments.append(gate_commitment)
    return identities, source_links, gate_commitments


def _verification_result(
    blockers: list[str],
    *,
    gate_stage: Any,
    identity_count: int,
) -> dict[str, Any]:
    unique_blockers = list(dict.fromkeys(blockers))
    passed = not unique_blockers
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if passed else "BLOCK",
        "decision": "BLOCK",
        "blockers": unique_blockers,
        "authority_gaps": list(AUTHORITY_GAPS),
        "gate_stage": (
            gate_stage if gate_stage in SUPPORTED_GATE_STAGES else "UNKNOWN"
        ),
        "identity_count": identity_count,
        "candidate_receipt_verified": passed,
        "source_linkage_bound": passed,
        "expected_gate_commitment_bound": passed,
        "chronology_contract_verified": passed,
        "external_anchor_receipt_hash_bound": passed,
        "candidate_only": True,
        "consumer_only": True,
        "receipt_producer_implemented": False,
        "anchor_receipt_verifier_implemented": False,
        "external_anchor_authenticity_verified": False,
        "immutable_persistence_verified": False,
        "anchor_uniqueness_verified": False,
        "anchor_freshness_verified": False,
        "rollback_resistance_verified": False,
        "timing_authority_verified": False,
        "preregistration_authority_verified": False,
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "writer_implemented": False,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "permissions": _permissions(),
    }


def verify_strategy_correlation_expected_gate_hash_timing_receipt_candidate(
    document: Any,
    *,
    gate_stage: Any,
    expected_gate_bindings: Any,
    expected_receipt_id: Any,
    expected_anchor_provider: Any,
    expected_anchor_namespace: Any,
    expected_anchor_id: Any,
    expected_declared_at: Any,
    expected_anchored_at: Any,
    expected_evidence_not_before: Any,
    expected_base_artifact_hash: Any,
    expected_protocol_registration_hash: Any,
    expected_identity_set_hash: Any,
    expected_source_linkage_hash: Any,
    expected_gate_commitment_hash: Any,
    expected_external_anchor_receipt_hash: Any,
    expected_candidate_receipt_hash: Any,
) -> dict[str, Any]:
    """Verify a candidate receipt without granting timing or trading authority."""

    blockers: list[str] = []
    receipt = document if type(document) is dict else {}
    if type(document) is not dict:
        blockers.append("RECEIPT_NOT_OBJECT")
    if gate_stage not in SUPPORTED_GATE_STAGES:
        blockers.append("GATE_STAGE_INVALID")
    for name, value in (
        ("RECEIPT_ID", expected_receipt_id),
        ("ANCHOR_PROVIDER", expected_anchor_provider),
        ("ANCHOR_NAMESPACE", expected_anchor_namespace),
        ("ANCHOR_ID", expected_anchor_id),
    ):
        if not _strict_token(value):
            blockers.append(f"{name}_INVALID")
    for name, value in (
        ("DECLARED_AT", expected_declared_at),
        ("ANCHORED_AT", expected_anchored_at),
        ("EVIDENCE_NOT_BEFORE", expected_evidence_not_before),
    ):
        if not strict_utc_second_timestamp(value):
            blockers.append(f"{name}_INVALID")
    for name, value in (
        ("BASE_ARTIFACT_HASH", expected_base_artifact_hash),
        ("PROTOCOL_REGISTRATION_HASH", expected_protocol_registration_hash),
        ("IDENTITY_SET_HASH", expected_identity_set_hash),
        ("SOURCE_LINKAGE_HASH", expected_source_linkage_hash),
        ("GATE_COMMITMENT_HASH", expected_gate_commitment_hash),
        ("EXTERNAL_ANCHOR_RECEIPT_HASH", expected_external_anchor_receipt_hash),
        ("CANDIDATE_RECEIPT_HASH", expected_candidate_receipt_hash),
    ):
        if not strict_sha256(value):
            blockers.append(f"{name}_INVALID")

    commitments = _binding_commitments(gate_stage, expected_gate_bindings)
    identity_count = 0
    if commitments is None:
        blockers.append("GATE_BINDINGS_INVALID")
        identities: list[dict[str, str]] = []
        source_links: list[dict[str, str]] = []
        gate_commitments: list[dict[str, str]] = []
    else:
        identities, source_links, gate_commitments = commitments
        identity_count = len(identities)

    try:
        identity_set_hash = strict_canonical_hash(identities)
        source_linkage_hash = strict_canonical_hash(source_links)
        gate_commitment_hash = strict_canonical_hash(gate_commitments)
    except (TypeError, ValueError):
        blockers.append("COMMITMENT_HASHING_FAILED")
        identity_set_hash = ""
        source_linkage_hash = ""
        gate_commitment_hash = ""
    if identity_set_hash != expected_identity_set_hash:
        blockers.append("IDENTITY_SET_HASH_MISMATCH")
    if source_linkage_hash != expected_source_linkage_hash:
        blockers.append("SOURCE_LINKAGE_HASH_MISMATCH")
    if gate_commitment_hash != expected_gate_commitment_hash:
        blockers.append("GATE_COMMITMENT_HASH_MISMATCH")

    timestamps_valid = all(
        strict_utc_second_timestamp(value)
        for value in (
            expected_declared_at,
            expected_anchored_at,
            expected_evidence_not_before,
        )
    )
    if timestamps_valid:
        if expected_declared_at > expected_anchored_at:
            blockers.append("DECLARATION_AFTER_ANCHOR")
        if expected_declared_at >= expected_evidence_not_before:
            blockers.append("DECLARATION_NOT_BEFORE_EVIDENCE")
        if expected_anchored_at >= expected_evidence_not_before:
            blockers.append("ANCHOR_NOT_BEFORE_EVIDENCE")

    try:
        anchor_payload = {
            "schema_version": ANCHOR_PAYLOAD_SCHEMA_VERSION,
            "gate_stage": gate_stage,
            "receipt_id": expected_receipt_id,
            "anchor_provider": expected_anchor_provider,
            "anchor_namespace": expected_anchor_namespace,
            "declared_at": expected_declared_at,
            "evidence_not_before": expected_evidence_not_before,
            "base_artifact_hash": expected_base_artifact_hash,
            "protocol_registration_hash": expected_protocol_registration_hash,
            "identity_set_hash": identity_set_hash,
            "source_linkage_hash": source_linkage_hash,
            "expected_gate_commitment_hash": gate_commitment_hash,
        }
        anchor_payload_hash = strict_canonical_hash(anchor_payload)
        expected = {
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "status": STATUS_CANDIDATE_RECEIPT,
            "decision": "BLOCK",
            "gate_stage": gate_stage,
            "receipt_id": expected_receipt_id,
            "declaration": {
                "declared_at": expected_declared_at,
                "evidence_not_before": expected_evidence_not_before,
                "base_artifact_hash": expected_base_artifact_hash,
                "protocol_registration_hash": expected_protocol_registration_hash,
                "identity_set_hash": identity_set_hash,
                "source_linkage_hash": source_linkage_hash,
                "expected_gate_commitment_hash": gate_commitment_hash,
            },
            "external_anchor": {
                "provider": expected_anchor_provider,
                "namespace": expected_anchor_namespace,
                "anchor_id": expected_anchor_id,
                "anchored_at": expected_anchored_at,
                "anchor_payload_hash": anchor_payload_hash,
                "external_anchor_receipt_hash": (
                    expected_external_anchor_receipt_hash
                ),
            },
            "identity_count": identity_count,
            "authority_gaps": list(AUTHORITY_GAPS),
            "candidate_only": True,
            "consumer_only": True,
            "external_assets_embedded": False,
            "requires_external_anchor_adapter": True,
            "receipt_producer_implemented": False,
            "anchor_receipt_verifier_implemented": False,
            "external_anchor_authenticity_verified": False,
            "immutable_persistence_verified": False,
            "anchor_uniqueness_verified": False,
            "anchor_freshness_verified": False,
            "rollback_resistance_verified": False,
            "timing_authority_verified": False,
            "preregistration_authority_verified": False,
            "formal_registry_bound": False,
            "formal_registry_activation_allowed": False,
            "writer_implemented": False,
            "current_writer_activation_allowed": False,
            "current_admission_allowed": False,
            "permissions": _permissions(),
        }
        expected = seal_strict_canonical_document(expected, "receipt_hash")
    except (TypeError, ValueError):
        expected = None
        blockers.append("RECEIPT_REBUILD_FAILED")

    if expected is not None:
        if not strict_json_contract_equal(receipt, expected):
            blockers.append("RECEIPT_REBUILD_MISMATCH")
        if expected["receipt_hash"] != expected_candidate_receipt_hash:
            blockers.append("CANDIDATE_RECEIPT_HASH_MISMATCH")
    if type(document) is dict and strict_research_authority_invalid(document):
        blockers.append("RESEARCH_AUTHORITY_INVALID")
    if type(document) is dict and not strict_locked_fields(document, _LOCK_FIELDS):
        blockers.append("RECEIPT_AUTHORITY_NOT_LOCKED")

    return _verification_result(
        blockers,
        gate_stage=gate_stage,
        identity_count=identity_count,
    )


__all__ = [
    "ANCHOR_PAYLOAD_SCHEMA_VERSION",
    "AUTHORITY_GAPS",
    "RECEIPT_SCHEMA_VERSION",
    "STABILITY_GATE_STAGE",
    "STATUS_CANDIDATE_RECEIPT",
    "SUPPORTED_GATE_STAGES",
    "TEMPORAL_GATE_STAGE",
    "VERIFICATION_SCHEMA_VERSION",
    "verify_strategy_correlation_expected_gate_hash_timing_receipt_candidate",
]
