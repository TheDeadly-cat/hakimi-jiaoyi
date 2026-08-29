from __future__ import annotations

from typing import Any

from exchange_terminal.application import (
    anti_replay_registry_identity_preregistration_v1 as identity_v1,
)
from exchange_terminal.application import (
    anti_replay_registry_organization_identity_evidence_bundle_evaluation_v1
    as evaluation_v1,
)
from exchange_terminal.application import (
    anti_replay_registry_organization_identity_intake_preregistration_v1
    as intake_v1,
)
from exchange_terminal.application.ports.registry_organization_identity_v1 import (
    RegistryOrganizationIdentityEvidenceKindV1,
    RegistryOrganizationIdentityEvidenceReferenceV1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "anti-replay-registry-organization-identity-evidence-bundle-"
    "python-verification-envelope-v1"
)
STATIC_FINGERPRINT = (
    "20260823-registry-organization-identity-bundle-python-envelope-v1-lock-1"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-exact-rebuild-v1"
IDENTITY_PREREGISTRATION_IMPLEMENTATION_SHA256 = (
    "d21e6864245ccb054329160ca49b2c5b725d6b86c262f0f0728c018b8c5d035f"
)
INTAKE_PREREGISTRATION_IMPLEMENTATION_SHA256 = (
    "3d9ce854b1e3f9bc29ce654d189be3c975796d9a4f5a7c7e72ade715f816ef56"
)
EVIDENCE_REFERENCE_IMPLEMENTATION_SHA256 = (
    "df294b21bae439b96b86220a2be55ed5bf3305c9f32aaefb98c18e5d3b00b59f"
)
BUNDLE_EVALUATION_IMPLEMENTATION_SHA256 = (
    "fec30c1e6433db5ea67c7e2a222e3c74cfd7fac8757461f579ccc7ee6d6fa055"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
SIGNED_ARTIFACT_CANDIDATE_IMPLEMENTATION_SHA256 = (
    "3f31febbc017d57cee6dd666751f83f2796fd60257aab0d211156e70b47cfecc"
)
TARGET_SIGNED_ARTIFACT_VERIFICATION_SCHEMA_VERSION = (
    "registry-organization-identity-signed-artifact-"
    "verification-candidate-v1"
)
TARGET_SIGNED_ARTIFACT_EXACT_VERIFICATION_SCHEMA_VERSION = (
    "registry-organization-identity-signed-artifact-exact-rebuild-v1"
)
TARGET_SIGNED_ARTIFACT_AGGREGATION_SCHEMA_VERSION = (
    "registry-organization-identity-signed-artifact-"
    "bundle-aggregation-candidate-v1"
)

_UNDERLYING_AUTHORITY = {
    "current_admission_allowed": False,
    "live_order_allowed": False,
    "paper_authorized": False,
    "presentation_mount_allowed": False,
    "registry_identity_admission_allowed": False,
    "runtime_gate_activation_allowed": False,
    "writer_allowed": False,
}
_AUTHORITY = {
    **_UNDERLYING_AUTHORITY,
    "evidence_bundle_admission_allowed": False,
    "signed_artifact_aggregation_activation_allowed": False,
}


def _is_hash(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _sealed_exact(document: Any, hash_field: str) -> bool:
    if not isinstance(document, dict) or not _is_hash(document.get(hash_field)):
        return False
    try:
        expected = seal_strict_canonical_document(document, hash_field)
    except (TypeError, ValueError):
        return False
    return strict_json_contract_equal(document, expected)


def _verify_identity(
    document: Any,
    *,
    registry_id: Any,
    operator_identity_claim: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
    adapter_protocol_version: Any,
) -> dict[str, Any]:
    try:
        return identity_v1.verify_anti_replay_registry_identity_preregistration_v1(
            document,
            registry_id=registry_id,
            operator_identity_claim=operator_identity_claim,
            public_key_spki_sha256=public_key_spki_sha256,
            trust_domain=trust_domain,
            adapter_protocol_version=adapter_protocol_version,
        )
    except (KeyError, TypeError, ValueError):
        return {"status": "BLOCK", "preregistration_status": "UNKNOWN"}


def _verify_intake(
    document: Any,
    identity_document: Any,
    *,
    registry_id: Any,
    operator_identity_claim: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
    adapter_protocol_version: Any,
) -> dict[str, Any]:
    try:
        return intake_v1.verify_anti_replay_registry_organization_identity_intake_preregistration_v1(
            document,
            identity_document,
            registry_id=registry_id,
            operator_identity_claim=operator_identity_claim,
            public_key_spki_sha256=public_key_spki_sha256,
            trust_domain=trust_domain,
            adapter_protocol_version=adapter_protocol_version,
        )
    except (KeyError, TypeError, ValueError):
        return {"status": "BLOCK", "intake_status": "UNKNOWN"}


def _verify_evaluation(
    document: Any,
    intake_document: Any,
    identity_document: Any,
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
        return evaluation_v1.verify_anti_replay_registry_organization_identity_evidence_bundle_evaluation_v1(
            document,
            intake_document,
            identity_document,
            evidence_references,
            reference_time_ms,
            registry_id=registry_id,
            operator_identity_claim=operator_identity_claim,
            public_key_spki_sha256=public_key_spki_sha256,
            trust_domain=trust_domain,
            adapter_protocol_version=adapter_protocol_version,
        )
    except (KeyError, TypeError, ValueError):
        return {
            "status": "BLOCK",
            "evaluation_status": "UNKNOWN",
            "local_bundle_status": "UNKNOWN",
        }


def _reference_rows(
    evidence_references: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]] | None:
    if not isinstance(evidence_references, (list, tuple)):
        return None
    if not all(
        isinstance(reference, RegistryOrganizationIdentityEvidenceReferenceV1)
        for reference in evidence_references
    ):
        return None
    by_kind = {reference.kind: reference for reference in evidence_references}
    if (
        len(evidence_references)
        != len(RegistryOrganizationIdentityEvidenceKindV1)
        or set(by_kind) != set(RegistryOrganizationIdentityEvidenceKindV1)
    ):
        return None
    full_rows: list[dict[str, Any]] = []
    evaluation_rows: list[dict[str, Any]] = []
    for kind in RegistryOrganizationIdentityEvidenceKindV1:
        reference = by_kind[kind]
        common = {
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
        evaluation_rows.append(common)
        full_rows.append({**common, "schema_version": reference.schema_version})
    return full_rows, evaluation_rows


def build_anti_replay_registry_organization_identity_evidence_bundle_verification_envelope_v1(
    evaluation_document: Any,
    intake_preregistration_document: Any,
    identity_preregistration_document: Any,
    evidence_references: Any,
    reference_time_ms: Any,
    *,
    registry_id: Any,
    operator_identity_claim: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
    adapter_protocol_version: Any = identity_v1.ADAPTER_PROTOCOL_VERSION,
) -> dict[str, Any]:
    identity_verification = _verify_identity(
        identity_preregistration_document,
        registry_id=registry_id,
        operator_identity_claim=operator_identity_claim,
        public_key_spki_sha256=public_key_spki_sha256,
        trust_domain=trust_domain,
        adapter_protocol_version=adapter_protocol_version,
    )
    intake_verification = _verify_intake(
        intake_preregistration_document,
        identity_preregistration_document,
        registry_id=registry_id,
        operator_identity_claim=operator_identity_claim,
        public_key_spki_sha256=public_key_spki_sha256,
        trust_domain=trust_domain,
        adapter_protocol_version=adapter_protocol_version,
    )
    evaluation_verification = _verify_evaluation(
        evaluation_document,
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

    identity_exact = bool(
        identity_verification.get("status") == "PASS"
        and identity_verification.get("preregistration_status") == "BLOCKED"
        and identity_verification.get("preregistration_document_exactly_rebuilt")
        is True
    )
    intake_exact = bool(
        intake_verification.get("status") == "PASS"
        and intake_verification.get("intake_status") == "BLOCKED"
        and intake_verification.get("intake_document_exactly_rebuilt") is True
    )
    evaluation_sealed = _sealed_exact(evaluation_document, "evaluation_hash")
    evaluation_identity_exact = bool(
        isinstance(evaluation_document, dict)
        and evaluation_document.get("schema_version")
        == evaluation_v1.SCHEMA_VERSION
        and evaluation_document.get("static_fingerprint")
        == evaluation_v1.STATIC_FINGERPRINT
        and evaluation_document.get("status") == "BLOCKED"
        and evaluation_document.get("local_bundle_status")
        == evaluation_v1.LOCAL_PASS_STATUS
    )
    evaluation_public_exact = bool(
        evaluation_verification.get("status") == "PASS"
        and evaluation_verification.get("evaluation_status") == "BLOCKED"
        and evaluation_verification.get("evaluation_document_exactly_rebuilt")
        is True
        and evaluation_verification.get("local_bundle_status")
        == evaluation_v1.LOCAL_PASS_STATUS
    )

    identity_source = (
        identity_preregistration_document.get("identity", {})
        if isinstance(identity_preregistration_document, dict)
        else {}
    )
    intake_source = (
        intake_preregistration_document.get("source", {})
        if isinstance(intake_preregistration_document, dict)
        else {}
    )
    intake_identity = (
        intake_preregistration_document.get("identity", {})
        if isinstance(intake_preregistration_document, dict)
        else {}
    )
    evaluation_source = (
        evaluation_document.get("source", {})
        if isinstance(evaluation_document, dict)
        else {}
    )
    evaluation_identity = (
        evaluation_document.get("identity", {})
        if isinstance(evaluation_document, dict)
        else {}
    )
    evaluation_facts = (
        evaluation_document.get("facts", {})
        if isinstance(evaluation_document, dict)
        else {}
    )

    identity_hash_bound = bool(
        identity_exact
        and intake_exact
        and intake_source.get("identity_preregistration_hash")
        == identity_preregistration_document.get("preregistration_hash")
    )
    intake_hash_bound = bool(
        intake_exact
        and evaluation_source.get("intake_preregistration_hash")
        == intake_preregistration_document.get("intake_preregistration_hash")
        and evaluation_source.get("intake_preregistration_schema_version")
        == intake_v1.SCHEMA_VERSION
    )
    rows = _reference_rows(evidence_references)
    full_reference_rows = rows[0] if rows is not None else []
    expected_evaluation_rows = rows[1] if rows is not None else []
    evaluation_reference_rows = (
        evaluation_document.get("references", [])
        if isinstance(evaluation_document, dict)
        else []
    )
    reference_set_exact = bool(
        rows is not None
        and len(full_reference_rows)
        == len(RegistryOrganizationIdentityEvidenceKindV1)
        and strict_json_contract_equal(
            evaluation_reference_rows,
            expected_evaluation_rows,
        )
    )
    reference_time_exact = bool(
        isinstance(reference_time_ms, int)
        and not isinstance(reference_time_ms, bool)
        and reference_time_ms >= 0
        and isinstance(evaluation_document, dict)
        and evaluation_document.get("reference_time_ms") == reference_time_ms
        and evaluation_facts.get("reference_time_explicit") is True
    )
    identity_binding_exact = bool(
        identity_exact
        and intake_exact
        and identity_source.get("registry_id") == registry_id
        and identity_source.get("public_key_spki_sha256")
        == public_key_spki_sha256
        and identity_source.get("trust_domain") == trust_domain
        and intake_identity.get("registry_id") == registry_id
        and intake_identity.get("public_key_spki_sha256")
        == public_key_spki_sha256
        and intake_identity.get("trust_domain") == trust_domain
        and evaluation_identity
        == {
            "public_key_spki_sha256": public_key_spki_sha256,
            "registry_id": registry_id,
            "trust_domain": trust_domain,
        }
    )
    unverified_boundaries_exact = bool(
        evaluation_facts.get("evidence_payloads_observed") is False
        and evaluation_facts.get("evidence_signatures_verified") is False
        and evaluation_facts.get("external_source_trust_verified") is False
        and evaluation_facts.get("revocation_content_verified") is False
        and evaluation_facts.get("registry_organization_identity_verified")
        is False
        and evaluation_verification.get("evidence_payloads_observed") is False
        and evaluation_verification.get("evidence_signatures_verified") is False
        and evaluation_verification.get("external_source_trust_verified")
        is False
        and evaluation_verification.get(
            "registry_organization_identity_verified"
        )
        is False
    )
    authority_locked = bool(
        isinstance(evaluation_document, dict)
        and strict_json_contract_equal(
            evaluation_document.get("authority"),
            _UNDERLYING_AUTHORITY,
        )
    )

    checks = [
        {
            "blocking": True,
            "name": "identity_preregistration_v1_exact",
            "ok": identity_exact,
        },
        {
            "blocking": True,
            "name": "organization_identity_intake_v1_exact",
            "ok": intake_exact,
        },
        {
            "blocking": True,
            "name": "bundle_evaluation_v1_strict_canonical_seal_exact",
            "ok": evaluation_sealed,
        },
        {
            "blocking": True,
            "name": "bundle_evaluation_v1_identity_and_local_pass_exact",
            "ok": evaluation_identity_exact,
        },
        {
            "blocking": True,
            "name": "bundle_evaluation_v1_public_exact_verifier_pass",
            "ok": evaluation_public_exact,
        },
        {
            "blocking": True,
            "name": "identity_preregistration_hash_edge_exact",
            "ok": identity_hash_bound,
        },
        {
            "blocking": True,
            "name": "intake_preregistration_hash_edge_exact",
            "ok": intake_hash_bound,
        },
        {
            "blocking": True,
            "name": "six_reference_set_and_order_exact",
            "ok": reference_set_exact,
        },
        {
            "blocking": True,
            "name": "explicit_reference_time_exact",
            "ok": reference_time_exact,
        },
        {
            "blocking": True,
            "name": "registry_subject_identity_binding_exact",
            "ok": identity_binding_exact,
        },
        {
            "blocking": True,
            "name": "signature_source_revocation_and_identity_remain_unverified",
            "ok": unverified_boundaries_exact,
        },
        {
            "blocking": True,
            "name": "bundle_evaluation_authority_locked",
            "ok": authority_locked,
        },
    ]
    blockers = [
        f"BUNDLE_PYTHON_ENVELOPE_CHECK_FAILED:{check['name']}"
        for check in checks
        if check["ok"] is not True
    ]
    passed = not blockers
    reference_set_sha256 = (
        strict_canonical_hash({"references": full_reference_rows})
        if reference_set_exact
        else None
    )
    operator_claim_hash = (
        intake_identity.get("operator_identity_claim_hash")
        if intake_exact
        and _is_hash(intake_identity.get("operator_identity_claim_hash"))
        else None
    )
    return seal_strict_canonical_document(
        {
            "authority": dict(_AUTHORITY),
            "blockers": blockers,
            "checks": checks,
            "decision": (
                "BLOCKED_BUNDLE_EVALUATION_V1_EXACTLY_VERIFIED_FOR_"
                "CROSS_RUNTIME_SIGNED_ARTIFACT_CONSUMER"
                if passed
                else "BUNDLE_EVALUATION_V1_PYTHON_VERIFICATION_ENVELOPE_BLOCKED"
            ),
            "facts": {
                "browser_visual_review_performed": False,
                "cross_runtime_summary_envelope_built": True,
                "evidence_payloads_observed": False,
                "evidence_references_embedded": False,
                "evidence_signatures_verified": False,
                "evaluation_document_embedded": False,
                "external_source_trust_verified": False,
                "identity_preregistration_document_embedded": False,
                "independent_source_observation_verified": False,
                "intake_preregistration_document_embedded": False,
                "local_python_verification_execution_observed": True,
                "local_structure_binding_freshness_verified": (
                    evaluation_public_exact
                ),
                "network_accessed": False,
                "node_process_executed": False,
                "operator_identity_claim_embedded": False,
                "profitability_proven": False,
                "registry_organization_identity_verified": False,
                "revocation_content_verified": False,
                "runtime_assets_accessed": False,
                "signed_artifact_candidate_executed": False,
                "signed_artifact_verification_documents_embedded": False,
                "signer_role_identity_verified": False,
                "underlying_evaluation_remains_blocked": (
                    evaluation_identity_exact
                ),
            },
            "schema_version": SCHEMA_VERSION,
            "source": {
                "bundle_evaluation_hash": (
                    evaluation_document.get("evaluation_hash")
                    if evaluation_sealed
                    else None
                ),
                "bundle_evaluation_implementation_sha256": (
                    BUNDLE_EVALUATION_IMPLEMENTATION_SHA256
                ),
                "bundle_evaluation_schema_version": (
                    evaluation_v1.SCHEMA_VERSION
                    if evaluation_identity_exact
                    else "UNKNOWN"
                ),
                "bundle_evaluation_static_fingerprint": (
                    evaluation_v1.STATIC_FINGERPRINT
                    if evaluation_identity_exact
                    else "UNKNOWN"
                ),
                "evidence_reference_count": (
                    len(full_reference_rows) if reference_set_exact else 0
                ),
                "evidence_reference_implementation_sha256": (
                    EVIDENCE_REFERENCE_IMPLEMENTATION_SHA256
                ),
                "evidence_reference_set_sha256": reference_set_sha256,
                "identity_preregistration_hash": (
                    identity_preregistration_document.get(
                        "preregistration_hash"
                    )
                    if identity_exact
                    else None
                ),
                "identity_preregistration_implementation_sha256": (
                    IDENTITY_PREREGISTRATION_IMPLEMENTATION_SHA256
                ),
                "intake_preregistration_hash": (
                    intake_preregistration_document.get(
                        "intake_preregistration_hash"
                    )
                    if intake_exact
                    else None
                ),
                "intake_preregistration_implementation_sha256": (
                    INTAKE_PREREGISTRATION_IMPLEMENTATION_SHA256
                ),
                "operator_identity_claim_hash": operator_claim_hash,
                "public_key_spki_sha256": (
                    public_key_spki_sha256 if identity_binding_exact else None
                ),
                "reference_time_ms": (
                    reference_time_ms if reference_time_exact else None
                ),
                "registry_id": registry_id if identity_binding_exact else "UNKNOWN",
                "strict_canonical_implementation_sha256": (
                    STRICT_CANONICAL_IMPLEMENTATION_SHA256
                ),
                "trust_domain": (
                    trust_domain if identity_binding_exact else "UNKNOWN"
                ),
                "verification_environment": "PYTHON_CONTRACT_PROCESS",
            },
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": "PASS" if passed else "BLOCK",
            "target_contracts": {
                "signed_artifact_aggregation_schema_version": (
                    TARGET_SIGNED_ARTIFACT_AGGREGATION_SCHEMA_VERSION
                ),
                "signed_artifact_candidate_implementation_sha256": (
                    SIGNED_ARTIFACT_CANDIDATE_IMPLEMENTATION_SHA256
                ),
                "signed_artifact_exact_verification_schema_version": (
                    TARGET_SIGNED_ARTIFACT_EXACT_VERIFICATION_SCHEMA_VERSION
                ),
                "signed_artifact_verification_schema_version": (
                    TARGET_SIGNED_ARTIFACT_VERIFICATION_SCHEMA_VERSION
                ),
            },
            "verification": {
                "bundle_evaluation_document_exactly_rebuilt": (
                    evaluation_verification.get(
                        "evaluation_document_exactly_rebuilt",
                        False,
                    )
                    is True
                ),
                "bundle_evaluation_status": evaluation_verification.get(
                    "evaluation_status",
                    "UNKNOWN",
                ),
                "bundle_local_status": evaluation_verification.get(
                    "local_bundle_status",
                    "UNKNOWN",
                ),
                "bundle_public_verifier_status": (
                    evaluation_verification.get("status", "BLOCK")
                ),
                "evidence_reference_count": (
                    len(full_reference_rows) if reference_set_exact else 0
                ),
                "identity_preregistration_status": (
                    identity_verification.get(
                        "preregistration_status",
                        "UNKNOWN",
                    )
                ),
                "intake_preregistration_status": intake_verification.get(
                    "intake_status",
                    "UNKNOWN",
                ),
                "reference_set_exact": reference_set_exact,
                "reference_time_exact": reference_time_exact,
            },
        },
        "envelope_hash",
    )


def verify_anti_replay_registry_organization_identity_evidence_bundle_verification_envelope_v1(
    document: Any,
    evaluation_document: Any,
    intake_preregistration_document: Any,
    identity_preregistration_document: Any,
    evidence_references: Any,
    reference_time_ms: Any,
    *,
    registry_id: Any,
    operator_identity_claim: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
    adapter_protocol_version: Any = identity_v1.ADAPTER_PROTOCOL_VERSION,
) -> dict[str, Any]:
    try:
        expected = build_anti_replay_registry_organization_identity_evidence_bundle_verification_envelope_v1(
            evaluation_document,
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
        sealed = _sealed_exact(document, "envelope_hash")
        exact = sealed and strict_json_contract_equal(document, expected)
    except (KeyError, TypeError, ValueError):
        expected = None
        sealed = False
        exact = False
    accepted = bool(
        exact and expected is not None and expected.get("status") == "PASS"
    )
    return {
        "blockers": (
            []
            if accepted
            else [
                (
                    "BUNDLE_PYTHON_VERIFICATION_ENVELOPE_PASS_REQUIRED"
                    if exact
                    else "BUNDLE_PYTHON_VERIFICATION_ENVELOPE_EXACT_REBUILD"
                )
            ]
        ),
        "bundle_evaluation_status": (
            expected.get("verification", {}).get(
                "bundle_evaluation_status",
                "UNKNOWN",
            )
            if exact and expected is not None
            else "UNKNOWN"
        ),
        "bundle_local_status": (
            expected.get("verification", {}).get(
                "bundle_local_status",
                "UNKNOWN",
            )
            if exact and expected is not None
            else "UNKNOWN"
        ),
        "current_admission_allowed": False,
        "envelope_exactly_rebuilt": exact,
        "envelope_hash": (
            expected.get("envelope_hash") if accepted and expected else None
        ),
        "envelope_seal_verified": sealed,
        "envelope_status": (
            expected.get("status")
            if exact and expected is not None
            else "UNKNOWN"
        ),
        "evidence_bundle_admission_allowed": False,
        "evidence_payloads_observed": False,
        "evidence_signatures_verified": False,
        "external_source_trust_verified": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_mount_allowed": False,
        "registry_identity_admission_allowed": False,
        "registry_organization_identity_verified": False,
        "revocation_content_verified": False,
        "runtime_gate_activation_allowed": False,
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "signed_artifact_aggregation_activation_allowed": False,
        "signer_role_identity_verified": False,
        "status": "PASS" if accepted else "BLOCK",
        "writer_allowed": False,
    }
