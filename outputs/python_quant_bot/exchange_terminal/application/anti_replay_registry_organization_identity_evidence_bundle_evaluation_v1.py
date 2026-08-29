from __future__ import annotations

from typing import Any, Iterable

from exchange_terminal.application import (
    anti_replay_registry_organization_identity_intake_preregistration_v1 as intake_v1,
)
from exchange_terminal.application.ports.registry_organization_identity_v1 import (
    RegistryOrganizationIdentityEvidenceKindV1,
    RegistryOrganizationIdentityEvidenceReferenceV1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "anti-replay-registry-organization-identity-evidence-bundle-"
    "evaluation-v1"
)
STATIC_FINGERPRINT = (
    "20260823-registry-organization-identity-evidence-bundle-evaluation-v1-lock-1"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-exact-rebuild-v1"
STATUS = "BLOCKED"
LOCAL_PASS_STATUS = "STRUCTURE_BINDING_AND_FRESHNESS_PASS"
LOCAL_BLOCK_STATUS = "BLOCK"
DECISION_PASS = (
    "SYNTHETIC_REFERENCE_STRUCTURE_BINDING_AND_FRESHNESS_PASS_"
    "SIGNATURE_SOURCE_TRUST_REVOCATION_AND_IDENTITY_UNVERIFIED"
)
DECISION_BLOCK = (
    "SYNTHETIC_REFERENCE_STRUCTURE_BINDING_OR_FRESHNESS_BLOCKED_"
    "ORGANIZATION_IDENTITY_UNVERIFIED"
)

_AUTHORITY_KEYS = (
    "current_admission_allowed",
    "live_order_allowed",
    "paper_authorized",
    "presentation_mount_allowed",
    "registry_identity_admission_allowed",
    "runtime_gate_activation_allowed",
    "writer_allowed",
)
_REMAINING_BLOCKERS = (
    "EVIDENCE_PAYLOADS_UNOBSERVED",
    "EVIDENCE_SIGNATURES_UNVERIFIED",
    "EXTERNAL_SOURCE_TRUST_UNPROVEN",
    "REVOCATION_CONTENT_UNVERIFIED",
    "REGISTRY_ORGANIZATION_IDENTITY_UNVERIFIED",
)


def _locked_authority() -> dict[str, bool]:
    return {key: False for key in _AUTHORITY_KEYS}


def _validate_reference_time(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("reference_time_ms must be a non-negative integer")
    return value


def _normalize_references(
    references: Any,
) -> tuple[RegistryOrganizationIdentityEvidenceReferenceV1, ...]:
    if not isinstance(references, (list, tuple)):
        raise ValueError("evidence references must be a list or tuple")
    if not all(
        isinstance(reference, RegistryOrganizationIdentityEvidenceReferenceV1)
        for reference in references
    ):
        raise ValueError("every evidence reference must be an exact v1 value")
    by_kind = {reference.kind: reference for reference in references}
    if len(references) != len(RegistryOrganizationIdentityEvidenceKindV1):
        raise ValueError("exactly six evidence references are required")
    if set(by_kind) != set(RegistryOrganizationIdentityEvidenceKindV1):
        raise ValueError("one exact reference per evidence kind is required")
    return tuple(by_kind[kind] for kind in RegistryOrganizationIdentityEvidenceKindV1)


def _reference_row(
    reference: RegistryOrganizationIdentityEvidenceReferenceV1,
) -> dict[str, Any]:
    return {
        "artifact_sha256": reference.artifact_sha256,
        "evidence_kind": reference.kind.value,
        "evidence_schema_version": reference.evidence_schema_version,
        "expires_at_ms": reference.expires_at_ms,
        "issued_at_ms": reference.issued_at_ms,
        "signature_algorithm": reference.signature_algorithm,
        "signer_public_key_spki_sha256": (
            reference.signer_public_key_spki_sha256
        ),
        "signer_role": reference.signer_role,
        "subject_public_key_spki_sha256": (
            reference.subject_public_key_spki_sha256
        ),
        "subject_registry_id": reference.subject_registry_id,
    }


def evaluate_anti_replay_registry_organization_identity_evidence_bundle_v1(
    intake_preregistration_document: Any,
    identity_preregistration_document: Any,
    evidence_references: Any,
    reference_time_ms: Any,
    *,
    registry_id: Any,
    operator_identity_claim: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
    adapter_protocol_version: Any,
) -> dict[str, Any]:
    intake_exact = intake_v1.verify_anti_replay_registry_organization_identity_intake_preregistration_v1(
        intake_preregistration_document,
        identity_preregistration_document,
        registry_id=registry_id,
        operator_identity_claim=operator_identity_claim,
        public_key_spki_sha256=public_key_spki_sha256,
        trust_domain=trust_domain,
        adapter_protocol_version=adapter_protocol_version,
    )
    if intake_exact["status"] != "PASS":
        raise ValueError("organization identity intake preregistration-v1 is not exact")
    references = _normalize_references(evidence_references)
    reference_time_ms = _validate_reference_time(reference_time_ms)
    requirements = {
        row["evidence_kind"]: row
        for row in intake_v1.expected_organization_identity_evidence_requirements_v1()
    }
    registry_binding = all(
        reference.subject_registry_id == registry_id for reference in references
    )
    public_key_binding = all(
        reference.subject_public_key_spki_sha256 == public_key_spki_sha256
        for reference in references
    )
    roles = [reference.signer_role for reference in references]
    signer_keys = [
        reference.signer_public_key_spki_sha256 for reference in references
    ]
    artifact_hashes = [reference.artifact_sha256 for reference in references]
    signer_roles_distinct = len(set(roles)) == len(roles)
    signer_keys_distinct = len(set(signer_keys)) == len(signer_keys)
    artifact_hashes_distinct = len(set(artifact_hashes)) == len(artifact_hashes)
    freshness = []
    for reference in references:
        maximum_age = requirements[reference.kind.value]["freshness_max_age_ms"]
        freshness.append(
            reference.issued_at_ms <= reference_time_ms < reference.expires_at_ms
            and reference_time_ms - reference.issued_at_ms <= maximum_age
            and reference.expires_at_ms - reference.issued_at_ms <= maximum_age
        )
    all_references_fresh = all(freshness)
    checks = [
        {
            "blocking": True,
            "name": "subject_registry_id_binding_exact",
            "ok": registry_binding,
        },
        {
            "blocking": True,
            "name": "subject_public_key_hash_binding_exact",
            "ok": public_key_binding,
        },
        {
            "blocking": True,
            "name": "signer_roles_distinct",
            "ok": signer_roles_distinct,
        },
        {
            "blocking": True,
            "name": "signer_public_keys_distinct",
            "ok": signer_keys_distinct,
        },
        {
            "blocking": True,
            "name": "artifact_hashes_distinct",
            "ok": artifact_hashes_distinct,
        },
        {
            "blocking": True,
            "name": "all_references_fresh_at_explicit_reference_time",
            "ok": all_references_fresh,
        },
    ]
    local_pass = all(check["ok"] for check in checks)
    local_blockers = [
        f"LOCAL_EVIDENCE_BUNDLE_CHECK_FAILED:{check['name']}"
        for check in checks
        if not check["ok"]
    ]
    return seal_strict_canonical_document(
        {
            "authority": _locked_authority(),
            "blockers": local_blockers + list(_REMAINING_BLOCKERS),
            "checks": checks,
            "decision": DECISION_PASS if local_pass else DECISION_BLOCK,
            "facts": {
                "all_evidence_kinds_present": True,
                "all_references_fresh": all_references_fresh,
                "artifact_hashes_distinct": artifact_hashes_distinct,
                "evidence_payloads_observed": False,
                "evidence_reference_count": len(references),
                "evidence_signatures_verified": False,
                "external_source_trust_verified": False,
                "reference_time_explicit": True,
                "registry_organization_identity_verified": False,
                "revocation_content_verified": False,
                "signer_public_keys_distinct": signer_keys_distinct,
                "signer_roles_distinct": signer_roles_distinct,
                "subject_public_key_hash_bound": public_key_binding,
                "subject_registry_id_bound": registry_binding,
            },
            "identity": {
                "public_key_spki_sha256": public_key_spki_sha256,
                "registry_id": registry_id,
                "trust_domain": trust_domain,
            },
            "local_bundle_status": (
                LOCAL_PASS_STATUS if local_pass else LOCAL_BLOCK_STATUS
            ),
            "reference_time_ms": reference_time_ms,
            "references": [_reference_row(reference) for reference in references],
            "schema_version": SCHEMA_VERSION,
            "source": {
                "intake_preregistration_hash": intake_preregistration_document[
                    "intake_preregistration_hash"
                ],
                "intake_preregistration_schema_version": intake_v1.SCHEMA_VERSION,
                "reference_schema_version": (
                    "registry-organization-identity-evidence-reference-v1"
                ),
            },
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": STATUS,
        },
        "evaluation_hash",
    )


def verify_anti_replay_registry_organization_identity_evidence_bundle_evaluation_v1(
    document: Any,
    intake_preregistration_document: Any,
    identity_preregistration_document: Any,
    evidence_references: Any,
    reference_time_ms: Any,
    *,
    registry_id: Any,
    operator_identity_claim: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
    adapter_protocol_version: Any,
) -> dict[str, Any]:
    try:
        expected = evaluate_anti_replay_registry_organization_identity_evidence_bundle_v1(
            intake_preregistration_document,
            identity_preregistration_document,
            evidence_references,
            reference_time_ms,
            registry_id=registry_id,
            operator_identity_claim=operator_identity_claim,
            public_key_spki_sha256=public_key_spki_sha256,
            trust_domain=trust_domain,
            adapter_protocol_version=adapter_protocol_version,
        )
        exact = strict_json_contract_equal(document, expected)
    except (KeyError, TypeError, ValueError):
        exact = False
        expected = None
    local_pass = bool(
        exact and expected is not None and expected["local_bundle_status"] == LOCAL_PASS_STATUS
    )
    return {
        "blockers": (
            []
            if local_pass
            else [
                "ORGANIZATION_IDENTITY_EVIDENCE_BUNDLE_LOCAL_PASS_REQUIRED"
                if exact
                else "ORGANIZATION_IDENTITY_EVIDENCE_BUNDLE_EXACT_REBUILD"
            ]
        ),
        "current_admission_allowed": False,
        "evaluation_document_exactly_rebuilt": exact,
        "evaluation_status": "BLOCKED" if exact else "UNKNOWN",
        "evidence_payloads_observed": False,
        "evidence_signatures_verified": False,
        "external_source_trust_verified": False,
        "live_order_allowed": False,
        "local_bundle_status": (
            expected["local_bundle_status"] if exact and expected is not None else "UNKNOWN"
        ),
        "paper_authorized": False,
        "registry_organization_identity_verified": False,
        "runtime_gate_activation_allowed": False,
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if local_pass else "BLOCK",
        "writer_allowed": False,
    }
