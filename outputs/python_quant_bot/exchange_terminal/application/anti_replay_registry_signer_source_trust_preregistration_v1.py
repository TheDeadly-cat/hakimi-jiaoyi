from __future__ import annotations

from typing import Any

from exchange_terminal.application import (
    anti_replay_registry_identity_preregistration_v1 as identity_v1,
)
from exchange_terminal.application import (
    anti_replay_registry_organization_identity_intake_preregistration_v1 as intake_v1,
)
from exchange_terminal.application.ports.registry_organization_identity_v1 import (
    RegistryOrganizationIdentityEvidenceKindV1,
    expected_signer_role_v1,
)
from exchange_terminal.application.ports.registry_signer_source_trust_v1 import (
    SOURCE_TRUST_RECORD_SCHEMA_VERSION,
    SOURCE_TRUST_SOURCE_PORT_VERSION,
    expected_source_trust_authority_role_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = "anti-replay-registry-signer-source-trust-preregistration-v1"
STATIC_FINGERPRINT = "20260823-registry-signer-source-trust-v1-lock-1"
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-exact-rebuild-v1"
STATUS = "BLOCKED"
DECISION = (
    "SIGNER_SOURCE_TRUST_REQUIREMENTS_PREREGISTERED_RECORDS_UNOBSERVED_"
    "AND_EXTERNAL_AUTHORITY_UNPROVEN"
)
IDENTITY_PREREGISTRATION_IMPLEMENTATION_SHA256 = (
    "d21e6864245ccb054329160ca49b2c5b725d6b86c262f0f0728c018b8c5d035f"
)
ORGANIZATION_IDENTITY_REFERENCE_IMPLEMENTATION_SHA256 = (
    "df294b21bae439b96b86220a2be55ed5bf3305c9f32aaefb98c18e5d3b00b59f"
)
INTAKE_PREREGISTRATION_IMPLEMENTATION_SHA256 = (
    "3d9ce854b1e3f9bc29ce654d189be3c975796d9a4f5a7c7e72ade715f816ef56"
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


def _locked_authority() -> dict[str, bool]:
    return {key: False for key in _AUTHORITY_KEYS}


def _requirements() -> list[dict[str, Any]]:
    rows = []
    for kind in RegistryOrganizationIdentityEvidenceKindV1:
        rows.append(
            {
                "authority_namespace_precommitment_required": True,
                "authority_public_key_hash_required": True,
                "authority_role": expected_source_trust_authority_role_v1(kind),
                "authority_statement_hash_required": True,
                "evidence_kind": kind.value,
                "evidence_signer_public_key_hash_required": True,
                "independent_trust_anchor_required": True,
                "policy_id_and_version_required": True,
                "revocation_snapshot_hash_required": True,
                "signer_role": expected_signer_role_v1(kind),
                "source_adapter_id_and_implementation_hash_required": True,
                "source_trust_record_schema_version": (
                    SOURCE_TRUST_RECORD_SCHEMA_VERSION
                ),
                "state": "UNOBSERVED",
            }
        )
    return rows


def expected_registry_signer_source_trust_requirements_v1() -> list[dict[str, Any]]:
    return _requirements()


def build_anti_replay_registry_signer_source_trust_preregistration_v1(
    intake_preregistration_document: Any,
    identity_preregistration_document: Any,
    *,
    registry_id: Any,
    operator_identity_claim: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
    adapter_protocol_version: Any = identity_v1.ADAPTER_PROTOCOL_VERSION,
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

    requirements = expected_registry_signer_source_trust_requirements_v1()
    authority_roles = [row["authority_role"] for row in requirements]
    signer_roles = [row["signer_role"] for row in requirements]
    return seal_strict_canonical_document(
        {
            "authority": _locked_authority(),
            "blockers": [
                f"SOURCE_TRUST_RECORD_UNOBSERVED:{row['evidence_kind']}"
                for row in requirements
            ]
            + [
                "SOURCE_ADAPTERS_UNSELECTED",
                "TRUST_ANCHORS_UNSELECTED",
                "EXTERNAL_AUTHORITY_REGISTRIES_UNSELECTED",
                "AUTHORITY_REVOCATION_UNVERIFIED",
                "SIGNER_ROLE_IDENTITY_UNVERIFIED",
                "EXTERNAL_SOURCE_TRUST_UNVERIFIED",
                "REGISTRY_ORGANIZATION_IDENTITY_UNVERIFIED",
            ],
            "decision": DECISION,
            "facts": {
                "authority_revocation_verified": False,
                "external_authority_registry_count": 0,
                "external_source_trust_verified": False,
                "external_sources_invoked": False,
                "intake_preregistration_exact": True,
                "network_accessed": False,
                "registry_organization_identity_verified": False,
                "runtime_assets_accessed": False,
                "signer_role_identity_verified": False,
                "source_adapter_count": 0,
                "source_trust_record_count": 0,
                "source_trust_requirements_preregistered": True,
                "trust_anchor_count": 0,
            },
            "identity": {
                "operator_identity_claim_hash": intake_preregistration_document[
                    "identity"
                ]["operator_identity_claim_hash"],
                "public_key_spki_sha256": public_key_spki_sha256,
                "registry_id": registry_id,
                "trust_domain": trust_domain,
            },
            "requirements": requirements,
            "separation_policy": {
                "authority_key_must_differ_from_subject_and_evidence_signer_keys": (
                    True
                ),
                "authority_namespace_must_differ_from_subject_namespace": True,
                "caller_supplied_trust_boolean_forbidden": True,
                "distinct_authority_role_count": len(authority_roles),
                "distinct_signer_role_count": len(signer_roles),
                "local_signature_pass_is_not_source_trust": True,
                "namespace_and_key_difference_is_not_governance_proof": True,
                "source_adapter_and_trust_anchor_require_separate_authorization": (
                    True
                ),
                "source_record_self_attestation_forbidden": True,
            },
            "schema_version": SCHEMA_VERSION,
            "source": {
                "identity_preregistration_hash": identity_preregistration_document[
                    "preregistration_hash"
                ],
                "identity_preregistration_implementation_sha256": (
                    IDENTITY_PREREGISTRATION_IMPLEMENTATION_SHA256
                ),
                "intake_preregistration_hash": intake_preregistration_document[
                    "intake_preregistration_hash"
                ],
                "intake_preregistration_implementation_sha256": (
                    INTAKE_PREREGISTRATION_IMPLEMENTATION_SHA256
                ),
                "organization_identity_reference_implementation_sha256": (
                    ORGANIZATION_IDENTITY_REFERENCE_IMPLEMENTATION_SHA256
                ),
                "source_trust_record_schema_version": (
                    SOURCE_TRUST_RECORD_SCHEMA_VERSION
                ),
                "source_trust_source_port_version": SOURCE_TRUST_SOURCE_PORT_VERSION,
            },
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": STATUS,
        },
        "source_trust_preregistration_hash",
    )


def verify_anti_replay_registry_signer_source_trust_preregistration_v1(
    document: Any,
    intake_preregistration_document: Any,
    identity_preregistration_document: Any,
    *,
    registry_id: Any,
    operator_identity_claim: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
    adapter_protocol_version: Any = identity_v1.ADAPTER_PROTOCOL_VERSION,
) -> dict[str, Any]:
    try:
        expected = build_anti_replay_registry_signer_source_trust_preregistration_v1(
            intake_preregistration_document,
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
        "blockers": []
        if exact
        else ["SIGNER_SOURCE_TRUST_PREREGISTRATION_EXACT_REBUILD"],
        "current_admission_allowed": False,
        "external_source_trust_verified": False,
        "external_sources_invoked": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "registry_organization_identity_verified": False,
        "runtime_gate_activation_allowed": False,
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "signer_role_identity_verified": False,
        "source_trust_preregistration_hash": (
            expected["source_trust_preregistration_hash"]
            if exact and expected is not None
            else None
        ),
        "source_trust_record_count": 0,
        "source_trust_status": "BLOCKED" if exact else "UNKNOWN",
        "status": "PASS" if exact else "BLOCK",
        "writer_allowed": False,
    }
