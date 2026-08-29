from __future__ import annotations

from typing import Any

from exchange_terminal.application import (
    anti_replay_registry_identity_preregistration_v1 as identity_preregistration_v1,
)
from exchange_terminal.application.ports.registry_organization_identity_v1 import (
    RegistryOrganizationIdentityEvidenceKindV1,
    expected_evidence_schema_v1,
    expected_signer_role_v1,
)
from exchange_terminal.services import (
    provider_identity_artifact_transparency_availability_v1 as transparency_v1,
)
from exchange_terminal.services import (
    provider_identity_auditor_provenance_suite_reproducibility_v1 as provenance_v1,
)
from exchange_terminal.services import (
    provider_identity_witness_conformance_key_governance_v1 as governance_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "anti-replay-registry-organization-identity-evidence-intake-"
    "preregistration-v1"
)
STATIC_FINGERPRINT = (
    "20260823-registry-organization-identity-evidence-intake-v1-lock-1"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-exact-rebuild-v1"
STATUS = "BLOCKED"
DECISION = (
    "ORGANIZATION_IDENTITY_EVIDENCE_REQUIREMENTS_PREREGISTERED_"
    "REFERENCES_UNOBSERVED_AND_EXTERNAL_TRUST_UNPROVEN"
)
IDENTITY_PREREGISTRATION_IMPLEMENTATION_SHA256 = (
    "d21e6864245ccb054329160ca49b2c5b725d6b86c262f0f0728c018b8c5d035f"
)
KEY_GOVERNANCE_IMPLEMENTATION_SHA256 = (
    "8f5db9a2c03a8de3294266c1613190c05f98265783c1021cfe1915b81723e75f"
)
AUDITOR_PROVENANCE_IMPLEMENTATION_SHA256 = (
    "03cd4626500df807d5557bd1261530ffae4ef70920705d31c15580e4fd4452cc"
)
ARTIFACT_TRANSPARENCY_IMPLEMENTATION_SHA256 = (
    "a09d300c0af3c436902dbfa3a981bd1874fe799afe164b3f3e09f5236bde4b04"
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
_FRESHNESS_MAX_AGE_MS = {
    RegistryOrganizationIdentityEvidenceKindV1.ORGANIZATION_REGISTRY_ATTESTATION: 30
    * 24
    * 60
    * 60
    * 1000,
    RegistryOrganizationIdentityEvidenceKindV1.DOMAIN_CONTROL_ATTESTATION: 7
    * 24
    * 60
    * 60
    * 1000,
    RegistryOrganizationIdentityEvidenceKindV1.KEY_GOVERNANCE_EVALUATION: 30
    * 24
    * 60
    * 60
    * 1000,
    RegistryOrganizationIdentityEvidenceKindV1.AUDITOR_PROVENANCE_EVALUATION: 30
    * 24
    * 60
    * 60
    * 1000,
    RegistryOrganizationIdentityEvidenceKindV1.ARTIFACT_TRANSPARENCY_EVALUATION: 24
    * 60
    * 60
    * 1000,
    RegistryOrganizationIdentityEvidenceKindV1.REVOCATION_STATUS_RECEIPT: 24
    * 60
    * 60
    * 1000,
}


def _locked_authority() -> dict[str, bool]:
    return {key: False for key in _AUTHORITY_KEYS}


def _requirements() -> list[dict[str, Any]]:
    rows = []
    for kind in RegistryOrganizationIdentityEvidenceKindV1:
        rows.append(
            {
                "artifact_hash_required": True,
                "evidence_kind": kind.value,
                "evidence_schema_version": expected_evidence_schema_v1(kind),
                "freshness_max_age_ms": _FRESHNESS_MAX_AGE_MS[kind],
                "independent_signature_required": True,
                "public_key_hash_binding_required": True,
                "registry_id_binding_required": True,
                "signer_role": expected_signer_role_v1(kind),
                "state": "UNOBSERVED",
            }
        )
    return rows


def expected_organization_identity_evidence_requirements_v1() -> list[dict[str, Any]]:
    return _requirements()


def build_anti_replay_registry_organization_identity_intake_preregistration_v1(
    identity_preregistration_document: Any,
    *,
    registry_id: Any,
    operator_identity_claim: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
    adapter_protocol_version: Any = (
        identity_preregistration_v1.ADAPTER_PROTOCOL_VERSION
    ),
) -> dict[str, Any]:
    identity_exact = identity_preregistration_v1.verify_anti_replay_registry_identity_preregistration_v1(
        identity_preregistration_document,
        registry_id=registry_id,
        operator_identity_claim=operator_identity_claim,
        public_key_spki_sha256=public_key_spki_sha256,
        trust_domain=trust_domain,
        adapter_protocol_version=adapter_protocol_version,
    )
    if identity_exact["status"] != "PASS":
        raise ValueError("registry identity preregistration-v1 is not exact")
    requirements = expected_organization_identity_evidence_requirements_v1()
    roles = [row["signer_role"] for row in requirements]
    return seal_strict_canonical_document(
        {
            "authority": _locked_authority(),
            "blockers": [
                f"EVIDENCE_UNOBSERVED:{row['evidence_kind']}"
                for row in requirements
            ]
            + [
                "DISTINCT_EXTERNAL_SIGNER_KEYS_UNVERIFIED",
                "REFERENCE_TIME_UNBOUND",
                "REVOCATION_STATUS_UNVERIFIED",
                "REGISTRY_ORGANIZATION_IDENTITY_UNVERIFIED",
            ],
            "decision": DECISION,
            "facts": {
                "distinct_external_signer_keys_verified": False,
                "evidence_reference_count": 0,
                "evidence_requirements_preregistered": True,
                "evidence_signatures_verified": False,
                "external_sources_invoked": False,
                "identity_preregistration_exact": True,
                "network_accessed": False,
                "reference_time_bound": False,
                "registry_organization_identity_verified": False,
                "revocation_status_verified": False,
                "runtime_assets_accessed": False,
            },
            "identity": {
                "operator_identity_claim_hash": strict_canonical_hash(
                    identity_preregistration_document["identity"][
                        "operator_identity_claim"
                    ]
                ),
                "public_key_spki_sha256": public_key_spki_sha256,
                "registry_id": registry_id,
                "trust_domain": trust_domain,
            },
            "requirements": requirements,
            "role_separation": {
                "all_signer_roles_distinct": True,
                "required_distinct_signer_role_count": len(roles),
                "roles": roles,
                "same_signing_key_across_roles_forbidden": True,
                "self_attestation_forbidden": True,
            },
            "schema_version": SCHEMA_VERSION,
            "source": {
                "artifact_transparency_contract": (
                    transparency_v1.EVALUATION_SCHEMA
                ),
                "artifact_transparency_implementation_sha256": (
                    ARTIFACT_TRANSPARENCY_IMPLEMENTATION_SHA256
                ),
                "auditor_provenance_contract": provenance_v1.EVALUATION_SCHEMA,
                "auditor_provenance_implementation_sha256": (
                    AUDITOR_PROVENANCE_IMPLEMENTATION_SHA256
                ),
                "identity_preregistration_hash": identity_preregistration_document[
                    "preregistration_hash"
                ],
                "identity_preregistration_implementation_sha256": (
                    IDENTITY_PREREGISTRATION_IMPLEMENTATION_SHA256
                ),
                "key_governance_contract": governance_v1.EVALUATION_SCHEMA,
                "key_governance_implementation_sha256": (
                    KEY_GOVERNANCE_IMPLEMENTATION_SHA256
                ),
            },
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": STATUS,
        },
        "intake_preregistration_hash",
    )


def verify_anti_replay_registry_organization_identity_intake_preregistration_v1(
    document: Any,
    identity_preregistration_document: Any,
    *,
    registry_id: Any,
    operator_identity_claim: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
    adapter_protocol_version: Any = (
        identity_preregistration_v1.ADAPTER_PROTOCOL_VERSION
    ),
) -> dict[str, Any]:
    try:
        expected = build_anti_replay_registry_organization_identity_intake_preregistration_v1(
            identity_preregistration_document,
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
    return {
        "blockers": [] if exact else ["ORGANIZATION_IDENTITY_INTAKE_PREREGISTRATION_EXACT_REBUILD"],
        "current_admission_allowed": False,
        "evidence_reference_count": 0,
        "external_sources_invoked": False,
        "intake_document_exactly_rebuilt": exact,
        "intake_preregistration_hash": (
            expected["intake_preregistration_hash"]
            if exact and expected is not None
            else None
        ),
        "intake_status": "BLOCKED" if exact else "UNKNOWN",
        "live_order_allowed": False,
        "paper_authorized": False,
        "registry_organization_identity_verified": False,
        "runtime_gate_activation_allowed": False,
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "writer_allowed": False,
    }
