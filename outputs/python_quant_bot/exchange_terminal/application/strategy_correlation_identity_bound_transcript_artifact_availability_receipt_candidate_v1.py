from __future__ import annotations

from collections.abc import Mapping
import base64
import hashlib
import re
from typing import Any

from cryptography.exceptions import InvalidSignature

from exchange_terminal.application import (
    strategy_correlation_identity_bound_signed_replay_cursor_provider_transcript_content_bridge_candidate_v1
    as identity_bound_transcript_content_bridge,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_ed25519_public_contract_v1 import (
    decode_canonical_base64_v1,
    load_canonical_ed25519_public_key_v1,
)


REGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-transcript-artifact-availability-registration-v1"
)
PUBLICATION_CLAIM_SCHEMA_VERSION = (
    "strategy-correlation-transcript-artifact-publication-claim-v1"
)
SIGNED_PUBLICATION_RECEIPT_SCHEMA_VERSION = (
    "strategy-correlation-transcript-artifact-signed-publication-receipt-v1"
)
RETRIEVAL_CLAIM_SCHEMA_VERSION = (
    "strategy-correlation-transcript-artifact-retrieval-claim-v1"
)
SIGNED_RETRIEVAL_RECEIPT_SCHEMA_VERSION = (
    "strategy-correlation-transcript-artifact-signed-retrieval-receipt-v1"
)
RETRIEVAL_RECEIPT_SET_SCHEMA_VERSION = (
    "strategy-correlation-transcript-artifact-retrieval-receipt-set-v1"
)
EVIDENCE_SCHEMA_VERSION = (
    "strategy-correlation-identity-bound-transcript-artifact-availability-"
    "receipt-candidate-v1"
)
STATIC_FINGERPRINT = "20260825-transcript-artifact-availability-receipt-candidate-1"
SIGNATURE_ALGORITHM = "ED25519"
SIGNATURE_MESSAGE_FORMAT = "STRICT_CANONICAL_CLAIM_HASH_BYTES_V1"
PUBLICATION_SIGNATURE_DOMAIN = (
    "hakimi.strategy-correlation.transcript-artifact.publication.v1"
)
RETRIEVAL_SIGNATURE_DOMAIN = (
    "hakimi.strategy-correlation.transcript-artifact.retrieval.v1"
)
RETRIEVAL_METHOD = "independent-content-addressed-fetch-claim-v1"
LOCATOR_POLICY = "sha256-redacted-immutable-locator-v1"
REQUIRED_RETRIEVERS_PER_ARTIFACT = 2
STATUS = "OBSERVED_LOCAL_SIGNED_PUBLICATION_DUAL_RETRIEVAL_CLAIMS_CANDIDATE"
DECISION = (
    "LOCAL_PUBLICATION_AND_DUAL_RETRIEVAL_SIGNATURES_VERIFIED_"
    "EXTERNAL_AVAILABILITY_UNPROVEN"
)
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$")

_UPSTREAM_CONTEXT_KEYS = frozenset(
    {
        "identity_bound_conformance_bridge_document",
        "identity_bound_conformance_bridge_verification_context",
        "transcript_content_evidence_document",
        "transcript_content_verification_context",
        "expected_identity_bound_conformance_bridge_hash",
        "expected_content_verification_hash",
        "expected_transcript_binding_hash",
        "expected_conformance_quorum_evidence_hash",
        "expected_signed_receipt_evidence_hash",
        "expected_conformance_plan_hash",
        "expected_provider_preregistration_hash",
    }
)


def _is_hash(value: Any) -> bool:
    return type(value) is str and HASH_PATTERN.fullmatch(value) is not None


def _require_hash(name: str, value: Any) -> str:
    if not _is_hash(value):
        raise ValueError(f"{name} must be a lowercase sha256 hex digest")
    return value


def _require_token(name: str, value: Any) -> str:
    if type(value) is not str or TOKEN_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{name} must be a bounded exact token")
    return value


def _strict_equal(left: Any, right: Any) -> bool:
    try:
        return strict_json_contract_equal(left, right)
    except (TypeError, ValueError, RecursionError):
        return False


def _digest(value: Any) -> str:
    digest = strict_canonical_hash(value)
    return _require_hash("canonical hash", digest)


def _seal(core: Mapping[str, Any], hash_field: str) -> dict[str, Any]:
    sealed = seal_strict_canonical_document(core, hash_field)
    if not isinstance(sealed, dict) or not _is_hash(sealed.get(hash_field)):
        raise ValueError(f"failed to seal {hash_field}")
    return sealed


def _sealed_document_verifies(document: Any, hash_field: str) -> bool:
    if not isinstance(document, Mapping) or not _is_hash(document.get(hash_field)):
        return False
    core = dict(document)
    core.pop(hash_field, None)
    try:
        return _strict_equal(document, _seal(core, hash_field))
    except (TypeError, ValueError, RecursionError):
        return False


def _authority_lock() -> dict[str, bool]:
    return {
        "publisher_identity_verified": False,
        "publisher_external_operation_verified": False,
        "retriever_identities_verified": False,
        "retriever_independence_verified": False,
        "network_retrieval_verified": False,
        "public_artifact_availability_verified": False,
        "external_persistence_verified": False,
        "external_time_truth_verified": False,
        "external_provider_conformance_verified": False,
        "provider_activation_allowed": False,
        "runtime_consumer_bound": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "profitability_proven": False,
    }


def _normalize_role_registration(value: Any, *, role: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{role} registration must be a mapping")
    id_field = "publisher_id" if role == "publisher" else "retriever_id"
    expected = {
        id_field,
        "organization_claim_hash",
        "trust_domain",
        "public_key_spki_sha256",
    }
    if set(value) != expected:
        raise ValueError(f"{role} registration keys are not exact")
    return {
        id_field: _require_token(id_field, value[id_field]),
        "organization_claim_hash": _require_hash(
            "organization_claim_hash", value["organization_claim_hash"]
        ),
        "trust_domain": _require_token("trust_domain", value["trust_domain"]),
        "public_key_spki_sha256": _require_hash(
            "public_key_spki_sha256", value["public_key_spki_sha256"]
        ),
    }


def _verify_upstream(
    document: Any,
    context: Any,
    *,
    expected_bridge_hash: str,
) -> bool:
    if not isinstance(context, Mapping) or set(context) != _UPSTREAM_CONTEXT_KEYS:
        return False
    if context.get("expected_identity_bound_conformance_bridge_hash") is None:
        return False
    try:
        return identity_bound_transcript_content_bridge.verify_strategy_correlation_identity_bound_signed_replay_cursor_provider_transcript_content_bridge_candidate_v1(
            document,
            context["identity_bound_conformance_bridge_document"],
            context["identity_bound_conformance_bridge_verification_context"],
            context["transcript_content_evidence_document"],
            context["transcript_content_verification_context"],
            expected_identity_bound_provider_transcript_content_bridge_hash=expected_bridge_hash,
            expected_identity_bound_conformance_bridge_hash=context[
                "expected_identity_bound_conformance_bridge_hash"
            ],
            expected_content_verification_hash=context[
                "expected_content_verification_hash"
            ],
            expected_transcript_binding_hash=context[
                "expected_transcript_binding_hash"
            ],
            expected_conformance_quorum_evidence_hash=context[
                "expected_conformance_quorum_evidence_hash"
            ],
            expected_signed_receipt_evidence_hash=context[
                "expected_signed_receipt_evidence_hash"
            ],
            expected_conformance_plan_hash=context[
                "expected_conformance_plan_hash"
            ],
            expected_provider_preregistration_hash=context[
                "expected_provider_preregistration_hash"
            ],
        )
    except (KeyError, TypeError, ValueError):
        return False


def _reserved_role_key_hashes(context: Mapping[str, Any]) -> tuple[str, ...]:
    content_context = context.get("transcript_content_verification_context")
    identity_context = context.get(
        "identity_bound_conformance_bridge_verification_context"
    )
    if not isinstance(content_context, Mapping) or not isinstance(identity_context, Mapping):
        raise ValueError("upstream verification contexts are incomplete")
    preregistration = content_context.get("provider_preregistration_document")
    conformance_context = identity_context.get(
        "conformance_quorum_verification_context"
    )
    if not isinstance(preregistration, Mapping) or not isinstance(conformance_context, Mapping):
        raise ValueError("provider or observer context is incomplete")
    provider_identity = preregistration.get("identity")
    observer_registrations = conformance_context.get("observer_registrations")
    if not isinstance(provider_identity, Mapping) or not isinstance(
        observer_registrations, (list, tuple)
    ):
        raise ValueError("provider or observer registrations are incomplete")
    hashes = [
        _require_hash(
            "provider public key hash", provider_identity.get("public_key_spki_sha256")
        )
    ]
    for row in observer_registrations:
        if not isinstance(row, Mapping):
            raise ValueError("observer registration must be a mapping")
        hashes.append(
            _require_hash(
                "observer public key hash", row.get("public_key_spki_sha256")
            )
        )
    if len(hashes) != len(set(hashes)):
        raise ValueError("upstream provider and observer key hashes are not distinct")
    return tuple(sorted(hashes))


def _derive_artifacts(
    upstream_document: Mapping[str, Any],
    context: Mapping[str, Any],
    artifact_locator_rows: Any,
) -> list[dict[str, Any]]:
    content_context = context.get("transcript_content_verification_context")
    if not isinstance(content_context, Mapping):
        raise ValueError("content verification context is incomplete")
    bundles = content_context.get("content_bundle_documents")
    manifests = content_context.get("transcript_manifest_documents")
    if not isinstance(bundles, (list, tuple)) or not isinstance(
        manifests, (list, tuple)
    ):
        raise ValueError("content bundles or manifests are incomplete")
    if not isinstance(artifact_locator_rows, (list, tuple)):
        raise ValueError("artifact locator rows must be a sequence")
    if len(bundles) != len(manifests) or len(bundles) != len(artifact_locator_rows):
        raise ValueError("artifact locator cardinality does not match content bundles")
    transcript_summary = upstream_document.get("transcript")
    if not isinstance(transcript_summary, Mapping):
        raise ValueError("upstream transcript summary is missing")
    if transcript_summary.get("manifest_count") != len(manifests):
        raise ValueError("upstream manifest count drifted")
    if transcript_summary.get("content_bundle_count") != len(bundles):
        raise ValueError("upstream content bundle count drifted")

    manifest_by_observer: dict[str, Mapping[str, Any]] = {}
    bundle_by_observer: dict[str, Mapping[str, Any]] = {}
    locator_by_observer: dict[str, Mapping[str, Any]] = {}
    for manifest in manifests:
        if not isinstance(manifest, Mapping):
            raise ValueError("manifest must be a mapping")
        observer_id = _require_token("manifest observer_id", manifest.get("observer_id"))
        if observer_id in manifest_by_observer:
            raise ValueError("duplicate manifest observer_id")
        manifest_by_observer[observer_id] = manifest
    for bundle in bundles:
        if not isinstance(bundle, Mapping):
            raise ValueError("content bundle must be a mapping")
        observer_id = _require_token("bundle observer_id", bundle.get("observer_id"))
        if observer_id in bundle_by_observer:
            raise ValueError("duplicate bundle observer_id")
        bundle_by_observer[observer_id] = bundle
    for row in artifact_locator_rows:
        if not isinstance(row, Mapping) or set(row) != {
            "observer_id",
            "locator_commitment_hash",
            "immutable_version_hash",
        }:
            raise ValueError("artifact locator row keys are not exact")
        observer_id = _require_token("locator observer_id", row["observer_id"])
        if observer_id in locator_by_observer:
            raise ValueError("duplicate locator observer_id")
        locator_by_observer[observer_id] = row
    if not (
        set(manifest_by_observer)
        == set(bundle_by_observer)
        == set(locator_by_observer)
    ):
        raise ValueError("manifest, bundle, and locator observer sets differ")

    artifacts: list[dict[str, Any]] = []
    for observer_id in sorted(bundle_by_observer):
        bundle = bundle_by_observer[observer_id]
        manifest = manifest_by_observer[observer_id]
        locator = locator_by_observer[observer_id]
        source = bundle.get("source")
        summary = bundle.get("summary")
        facts = bundle.get("facts")
        if not isinstance(source, Mapping) or not isinstance(summary, Mapping) or not isinstance(
            facts, Mapping
        ):
            raise ValueError("content bundle metadata is incomplete")
        manifest_hash = _require_hash(
            "transcript manifest hash", manifest.get("transcript_manifest_hash")
        )
        if source.get("transcript_manifest_hash") != manifest_hash:
            raise ValueError("content bundle manifest binding drifted")
        content_bundle_hash = _require_hash(
            "content bundle hash", bundle.get("content_bundle_hash")
        )
        total_payload_bytes = summary.get("total_payload_bytes")
        if (
            type(total_payload_bytes) is not int
            or total_payload_bytes <= 0
            or total_payload_bytes > 16_777_216
        ):
            raise ValueError("content bundle total payload bytes are invalid")
        if facts.get("local_component_hashes_verified") is not True:
            raise ValueError("content bundle hashes are not locally verified")
        if facts.get("local_component_sizes_bounded") is not True:
            raise ValueError("content bundle sizes are not locally bounded")
        artifacts.append(
            {
                "artifact_id": f"transcript-content-bundle:{observer_id}",
                "observer_id": observer_id,
                "transcript_manifest_hash": manifest_hash,
                "content_bundle_hash": content_bundle_hash,
                "total_payload_bytes": total_payload_bytes,
                "locator_commitment_hash": _require_hash(
                    "locator_commitment_hash", locator["locator_commitment_hash"]
                ),
                "immutable_version_hash": _require_hash(
                    "immutable_version_hash", locator["immutable_version_hash"]
                ),
            }
        )
    return artifacts


def build_strategy_correlation_transcript_artifact_availability_registration_v1(
    identity_bound_transcript_content_bridge_document: Any,
    identity_bound_transcript_content_bridge_verification_context: Any,
    *,
    expected_identity_bound_transcript_content_bridge_hash: Any,
    artifact_locator_rows: Any,
    publisher_registration: Any,
    retriever_registrations: Any,
) -> dict[str, Any]:
    expected_bridge_hash = _require_hash(
        "expected identity-bound transcript content bridge hash",
        expected_identity_bound_transcript_content_bridge_hash,
    )
    if not isinstance(identity_bound_transcript_content_bridge_document, Mapping):
        raise ValueError("identity-bound transcript content bridge must be a mapping")
    if identity_bound_transcript_content_bridge_document.get(
        "identity_bound_provider_transcript_content_bridge_hash"
    ) != expected_bridge_hash:
        raise ValueError("identity-bound transcript content bridge hash drifted")
    publisher = _normalize_role_registration(publisher_registration, role="publisher")
    if not isinstance(retriever_registrations, (list, tuple)) or len(
        retriever_registrations
    ) != REQUIRED_RETRIEVERS_PER_ARTIFACT:
        raise ValueError("exactly two retriever registrations are required")
    retrievers = [
        _normalize_role_registration(row, role="retriever")
        for row in retriever_registrations
    ]
    retriever_ids = [row["retriever_id"] for row in retrievers]
    role_key_hashes = [
        publisher["public_key_spki_sha256"],
        *(row["public_key_spki_sha256"] for row in retrievers),
    ]
    organizations = [
        publisher["organization_claim_hash"],
        *(row["organization_claim_hash"] for row in retrievers),
    ]
    trust_domains = [
        publisher["trust_domain"],
        *(row["trust_domain"] for row in retrievers),
    ]
    if len(retriever_ids) != len(set(retriever_ids)):
        raise ValueError("retriever ids must be unique")
    if len(role_key_hashes) != len(set(role_key_hashes)):
        raise ValueError("publisher and retriever key hashes must be unique")
    if len(organizations) != len(set(organizations)):
        raise ValueError("publisher and retriever organizations must be unique")
    if len(trust_domains) != len(set(trust_domains)):
        raise ValueError("publisher and retriever trust domains must be unique")
    if not isinstance(identity_bound_transcript_content_bridge_verification_context, Mapping):
        raise ValueError("identity-bound transcript content context must be a mapping")
    reserved_key_hashes = _reserved_role_key_hashes(
        identity_bound_transcript_content_bridge_verification_context
    )
    if set(role_key_hashes).intersection(reserved_key_hashes):
        raise ValueError("availability role key collides with provider or observer key")
    artifacts = _derive_artifacts(
        identity_bound_transcript_content_bridge_document,
        identity_bound_transcript_content_bridge_verification_context,
        artifact_locator_rows,
    )
    if not _verify_upstream(
        identity_bound_transcript_content_bridge_document,
        identity_bound_transcript_content_bridge_verification_context,
        expected_bridge_hash=expected_bridge_hash,
    ):
        raise ValueError("identity-bound transcript content bridge is not exact")
    source = identity_bound_transcript_content_bridge_document.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("identity-bound transcript source is incomplete")
    core = {
        "schema_version": REGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PREREGISTERED_UNMOUNTED",
        "permission_state": "BLOCKED",
        "decision": (
            "PUBLICATION_AND_DUAL_RETRIEVAL_ROLES_PREREGISTERED_"
            "EXTERNAL_OPERATIONS_UNVERIFIED"
        ),
        "source": {
            "identity_bound_transcript_content_bridge_hash": expected_bridge_hash,
            "content_verification_hash": source.get("content_verification_hash"),
            "transcript_binding_hash": source.get("transcript_binding_hash"),
            "provider_preregistration_hash": source.get(
                "provider_preregistration_hash"
            ),
        },
        "policy": {
            "locator_policy": LOCATOR_POLICY,
            "retrieval_method": RETRIEVAL_METHOD,
            "required_retrievers_per_artifact": REQUIRED_RETRIEVERS_PER_ARTIFACT,
            "signature_algorithm": SIGNATURE_ALGORITHM,
            "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        },
        "publisher": publisher,
        "retrievers": sorted(retrievers, key=lambda row: row["retriever_id"]),
        "artifacts": artifacts,
        "role_separation": {
            "availability_role_count": len(role_key_hashes),
            "reserved_role_key_count": len(reserved_key_hashes),
            "reserved_role_key_set_hash": _digest(list(reserved_key_hashes)),
            "all_registered_key_hashes_structurally_distinct": True,
            "external_identity_or_independence_verified": False,
        },
        "authority": _authority_lock(),
    }
    return _seal(core, "availability_registration_hash")


def verify_strategy_correlation_transcript_artifact_availability_registration_v1(
    document: Any,
    identity_bound_transcript_content_bridge_document: Any,
    identity_bound_transcript_content_bridge_verification_context: Any,
    *,
    expected_availability_registration_hash: Any,
    expected_identity_bound_transcript_content_bridge_hash: Any,
) -> bool:
    if not isinstance(document, Mapping):
        return False
    if document.get("availability_registration_hash") != expected_availability_registration_hash:
        return False
    artifacts = document.get("artifacts")
    if not isinstance(artifacts, list):
        return False
    locator_rows = [
        {
            "observer_id": row.get("observer_id"),
            "locator_commitment_hash": row.get("locator_commitment_hash"),
            "immutable_version_hash": row.get("immutable_version_hash"),
        }
        for row in artifacts
        if isinstance(row, Mapping)
    ]
    try:
        rebuilt = build_strategy_correlation_transcript_artifact_availability_registration_v1(
            identity_bound_transcript_content_bridge_document,
            identity_bound_transcript_content_bridge_verification_context,
            expected_identity_bound_transcript_content_bridge_hash=expected_identity_bound_transcript_content_bridge_hash,
            artifact_locator_rows=locator_rows,
            publisher_registration=document.get("publisher"),
            retriever_registrations=document.get("retrievers"),
        )
    except (KeyError, TypeError, ValueError, RecursionError):
        return False
    return _strict_equal(document, rebuilt)


def build_strategy_correlation_transcript_artifact_publication_claim_v1(
    registration_document: Any,
    *,
    expected_availability_registration_hash: Any,
    publication_nonce_hash: Any,
) -> dict[str, Any]:
    expected_registration_hash = _require_hash(
        "expected availability registration hash",
        expected_availability_registration_hash,
    )
    nonce_hash = _require_hash("publication_nonce_hash", publication_nonce_hash)
    if not _sealed_document_verifies(
        registration_document, "availability_registration_hash"
    ):
        raise ValueError("availability registration seal does not verify")
    if registration_document.get("availability_registration_hash") != expected_registration_hash:
        raise ValueError("availability registration hash drifted")
    core = {
        "schema_version": PUBLICATION_CLAIM_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PUBLICATION_CLAIMED_LOCAL_SIGNATURE_PENDING",
        "source": {
            "availability_registration_hash": expected_registration_hash,
            "identity_bound_transcript_content_bridge_hash": registration_document[
                "source"
            ]["identity_bound_transcript_content_bridge_hash"],
            "publication_nonce_hash": nonce_hash,
        },
        "signature_domain": PUBLICATION_SIGNATURE_DOMAIN,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "publisher": registration_document["publisher"],
        "artifacts": registration_document["artifacts"],
        "claim": {
            "publication_operation_claimed": True,
            "external_publication_operation_verified": False,
            "public_visibility_verified": False,
            "external_persistence_verified": False,
        },
        "authority": _authority_lock(),
    }
    return _seal(core, "publication_claim_hash")


def _public_key_hash(public_key_spki_base64: Any) -> tuple[bytes, str]:
    spki_bytes = decode_canonical_base64_v1(
        public_key_spki_base64, "public_key_spki_base64"
    )
    return spki_bytes, hashlib.sha256(spki_bytes).hexdigest()


def _verify_signature(
    *,
    public_key_spki_base64: Any,
    signature_base64: Any,
    claim_hash: str,
    expected_public_key_hash: str,
) -> bool:
    try:
        spki_bytes, key_hash = _public_key_hash(public_key_spki_base64)
        if key_hash != expected_public_key_hash:
            return False
        signature = decode_canonical_base64_v1(signature_base64, "signature_base64")
        public_key = load_canonical_ed25519_public_key_v1(spki_bytes)
        public_key.verify(signature, bytes.fromhex(claim_hash))
        return True
    except (InvalidSignature, TypeError, ValueError):
        return False


def build_signed_strategy_correlation_transcript_artifact_publication_receipt_v1(
    publication_claim_document: Any,
    registration_document: Any,
    *,
    public_key_spki_base64: Any,
    signature_base64: Any,
    expected_publication_claim_hash: Any,
    expected_availability_registration_hash: Any,
) -> dict[str, Any]:
    claim_hash = _require_hash(
        "expected publication claim hash", expected_publication_claim_hash
    )
    registration_hash = _require_hash(
        "expected availability registration hash",
        expected_availability_registration_hash,
    )
    if not isinstance(publication_claim_document, Mapping):
        raise ValueError("publication claim must be a mapping")
    if publication_claim_document.get("publication_claim_hash") != claim_hash:
        raise ValueError("publication claim hash drifted")
    source = publication_claim_document.get("source")
    if not isinstance(source, Mapping) or source.get(
        "availability_registration_hash"
    ) != registration_hash:
        raise ValueError("publication claim registration binding drifted")
    rebuilt_claim = build_strategy_correlation_transcript_artifact_publication_claim_v1(
        registration_document,
        expected_availability_registration_hash=registration_hash,
        publication_nonce_hash=source.get("publication_nonce_hash"),
    )
    if not _strict_equal(publication_claim_document, rebuilt_claim):
        raise ValueError("publication claim is not exact")
    publisher = registration_document.get("publisher")
    if not isinstance(publisher, Mapping):
        raise ValueError("publisher registration is missing")
    spki_bytes, key_hash = _public_key_hash(public_key_spki_base64)
    if key_hash != publisher.get("public_key_spki_sha256"):
        raise ValueError("publisher public key hash drifted")
    if not _verify_signature(
        public_key_spki_base64=public_key_spki_base64,
        signature_base64=signature_base64,
        claim_hash=claim_hash,
        expected_public_key_hash=key_hash,
    ):
        raise ValueError("publisher signature does not verify")
    core = {
        "schema_version": SIGNED_PUBLICATION_RECEIPT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "SIGNED_PUBLICATION_CLAIM_LOCAL_ONLY",
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signature_domain": PUBLICATION_SIGNATURE_DOMAIN,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "public_key_spki_base64": base64.b64encode(spki_bytes).decode("ascii"),
        "public_key_spki_sha256": key_hash,
        "signature_base64": signature_base64,
        "publication_claim": publication_claim_document,
        "source": {
            "availability_registration_hash": registration_hash,
            "publication_claim_hash": claim_hash,
        },
        "authority": _authority_lock(),
    }
    return _seal(core, "signed_publication_receipt_hash")


def verify_signed_strategy_correlation_transcript_artifact_publication_receipt_v1(
    document: Any,
    registration_document: Any,
    *,
    expected_signed_publication_receipt_hash: Any,
) -> bool:
    if not isinstance(document, Mapping):
        return False
    if document.get("signed_publication_receipt_hash") != expected_signed_publication_receipt_hash:
        return False
    claim = document.get("publication_claim")
    if not isinstance(claim, Mapping):
        return False
    try:
        rebuilt = build_signed_strategy_correlation_transcript_artifact_publication_receipt_v1(
            claim,
            registration_document,
            public_key_spki_base64=document.get("public_key_spki_base64"),
            signature_base64=document.get("signature_base64"),
            expected_publication_claim_hash=claim.get("publication_claim_hash"),
            expected_availability_registration_hash=registration_document.get(
                "availability_registration_hash"
            ),
        )
    except (KeyError, TypeError, ValueError, RecursionError):
        return False
    return _strict_equal(document, rebuilt)


def build_strategy_correlation_transcript_artifact_retrieval_claim_v1(
    registration_document: Any,
    signed_publication_receipt_document: Any,
    *,
    retriever_id: Any,
    artifact_id: Any,
    challenge_nonce_hash: Any,
    retrieved_content_bundle_hash: Any,
    retrieved_total_payload_bytes: Any,
    expected_availability_registration_hash: Any,
    expected_signed_publication_receipt_hash: Any,
) -> dict[str, Any]:
    registration_hash = _require_hash(
        "expected availability registration hash",
        expected_availability_registration_hash,
    )
    publication_receipt_hash = _require_hash(
        "expected signed publication receipt hash",
        expected_signed_publication_receipt_hash,
    )
    selected_retriever_id = _require_token("retriever_id", retriever_id)
    selected_artifact_id = _require_token("artifact_id", artifact_id)
    challenge_hash = _require_hash("challenge_nonce_hash", challenge_nonce_hash)
    retrieved_hash = _require_hash(
        "retrieved_content_bundle_hash", retrieved_content_bundle_hash
    )
    if type(retrieved_total_payload_bytes) is not int or retrieved_total_payload_bytes <= 0:
        raise ValueError("retrieved_total_payload_bytes must be a positive integer")
    if not _sealed_document_verifies(
        registration_document, "availability_registration_hash"
    ) or registration_document.get("availability_registration_hash") != registration_hash:
        raise ValueError("availability registration is not exact")
    if not verify_signed_strategy_correlation_transcript_artifact_publication_receipt_v1(
        signed_publication_receipt_document,
        registration_document,
        expected_signed_publication_receipt_hash=publication_receipt_hash,
    ):
        raise ValueError("signed publication receipt is not exact")
    retrievers = registration_document.get("retrievers")
    artifacts = registration_document.get("artifacts")
    if not isinstance(retrievers, list) or not isinstance(artifacts, list):
        raise ValueError("registration retrievers or artifacts are missing")
    retriever = next(
        (
            row
            for row in retrievers
            if isinstance(row, Mapping)
            and row.get("retriever_id") == selected_retriever_id
        ),
        None,
    )
    artifact = next(
        (
            row
            for row in artifacts
            if isinstance(row, Mapping) and row.get("artifact_id") == selected_artifact_id
        ),
        None,
    )
    if not isinstance(retriever, Mapping) or not isinstance(artifact, Mapping):
        raise ValueError("retriever or artifact is not preregistered")
    if artifact.get("content_bundle_hash") != retrieved_hash:
        raise ValueError("retrieved content bundle hash drifted")
    if artifact.get("total_payload_bytes") != retrieved_total_payload_bytes:
        raise ValueError("retrieved payload byte count drifted")
    core = {
        "schema_version": RETRIEVAL_CLAIM_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "RETRIEVAL_CLAIMED_LOCAL_SIGNATURE_PENDING",
        "signature_domain": RETRIEVAL_SIGNATURE_DOMAIN,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "source": {
            "availability_registration_hash": registration_hash,
            "signed_publication_receipt_hash": publication_receipt_hash,
            "challenge_nonce_hash": challenge_hash,
        },
        "retriever": retriever,
        "artifact": artifact,
        "retrieval": {
            "retrieval_method": RETRIEVAL_METHOD,
            "retrieved_content_bundle_hash": retrieved_hash,
            "retrieved_total_payload_bytes": retrieved_total_payload_bytes,
            "retrieval_operation_claimed": True,
            "actual_network_retrieval_verified": False,
            "external_source_truth_verified": False,
        },
        "authority": _authority_lock(),
    }
    return _seal(core, "retrieval_claim_hash")


def build_signed_strategy_correlation_transcript_artifact_retrieval_receipt_v1(
    retrieval_claim_document: Any,
    registration_document: Any,
    signed_publication_receipt_document: Any,
    *,
    public_key_spki_base64: Any,
    signature_base64: Any,
    expected_retrieval_claim_hash: Any,
    expected_availability_registration_hash: Any,
    expected_signed_publication_receipt_hash: Any,
) -> dict[str, Any]:
    claim_hash = _require_hash(
        "expected retrieval claim hash", expected_retrieval_claim_hash
    )
    if not isinstance(retrieval_claim_document, Mapping):
        raise ValueError("retrieval claim must be a mapping")
    if retrieval_claim_document.get("retrieval_claim_hash") != claim_hash:
        raise ValueError("retrieval claim hash drifted")
    retriever = retrieval_claim_document.get("retriever")
    artifact = retrieval_claim_document.get("artifact")
    retrieval = retrieval_claim_document.get("retrieval")
    source = retrieval_claim_document.get("source")
    if not all(
        isinstance(value, Mapping)
        for value in (retriever, artifact, retrieval, source)
    ):
        raise ValueError("retrieval claim metadata is incomplete")
    rebuilt_claim = build_strategy_correlation_transcript_artifact_retrieval_claim_v1(
        registration_document,
        signed_publication_receipt_document,
        retriever_id=retriever.get("retriever_id"),
        artifact_id=artifact.get("artifact_id"),
        challenge_nonce_hash=source.get("challenge_nonce_hash"),
        retrieved_content_bundle_hash=retrieval.get(
            "retrieved_content_bundle_hash"
        ),
        retrieved_total_payload_bytes=retrieval.get(
            "retrieved_total_payload_bytes"
        ),
        expected_availability_registration_hash=expected_availability_registration_hash,
        expected_signed_publication_receipt_hash=expected_signed_publication_receipt_hash,
    )
    if not _strict_equal(retrieval_claim_document, rebuilt_claim):
        raise ValueError("retrieval claim is not exact")
    spki_bytes, key_hash = _public_key_hash(public_key_spki_base64)
    if key_hash != retriever.get("public_key_spki_sha256"):
        raise ValueError("retriever public key hash drifted")
    if not _verify_signature(
        public_key_spki_base64=public_key_spki_base64,
        signature_base64=signature_base64,
        claim_hash=claim_hash,
        expected_public_key_hash=key_hash,
    ):
        raise ValueError("retriever signature does not verify")
    core = {
        "schema_version": SIGNED_RETRIEVAL_RECEIPT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "SIGNED_RETRIEVAL_CLAIM_LOCAL_ONLY",
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signature_domain": RETRIEVAL_SIGNATURE_DOMAIN,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "public_key_spki_base64": base64.b64encode(spki_bytes).decode("ascii"),
        "public_key_spki_sha256": key_hash,
        "signature_base64": signature_base64,
        "retrieval_claim": retrieval_claim_document,
        "source": {
            "availability_registration_hash": expected_availability_registration_hash,
            "signed_publication_receipt_hash": expected_signed_publication_receipt_hash,
            "retrieval_claim_hash": claim_hash,
        },
        "authority": _authority_lock(),
    }
    return _seal(core, "signed_retrieval_receipt_hash")


def verify_signed_strategy_correlation_transcript_artifact_retrieval_receipt_v1(
    document: Any,
    registration_document: Any,
    signed_publication_receipt_document: Any,
    *,
    expected_signed_retrieval_receipt_hash: Any,
) -> bool:
    if not isinstance(document, Mapping):
        return False
    if document.get("signed_retrieval_receipt_hash") != expected_signed_retrieval_receipt_hash:
        return False
    claim = document.get("retrieval_claim")
    if not isinstance(claim, Mapping):
        return False
    try:
        rebuilt = build_signed_strategy_correlation_transcript_artifact_retrieval_receipt_v1(
            claim,
            registration_document,
            signed_publication_receipt_document,
            public_key_spki_base64=document.get("public_key_spki_base64"),
            signature_base64=document.get("signature_base64"),
            expected_retrieval_claim_hash=claim.get("retrieval_claim_hash"),
            expected_availability_registration_hash=registration_document.get(
                "availability_registration_hash"
            ),
            expected_signed_publication_receipt_hash=signed_publication_receipt_document.get(
                "signed_publication_receipt_hash"
            ),
        )
    except (KeyError, TypeError, ValueError, RecursionError):
        return False
    return _strict_equal(document, rebuilt)


def build_strategy_correlation_transcript_artifact_retrieval_receipt_set_hash_v1(
    signed_retrieval_receipt_documents: Any,
) -> str:
    if not isinstance(signed_retrieval_receipt_documents, (list, tuple)):
        raise ValueError("signed retrieval receipts must be a sequence")
    hashes = []
    for document in signed_retrieval_receipt_documents:
        if not isinstance(document, Mapping):
            raise ValueError("signed retrieval receipt must be a mapping")
        hashes.append(
            _require_hash(
                "signed retrieval receipt hash",
                document.get("signed_retrieval_receipt_hash"),
            )
        )
    if len(hashes) != len(set(hashes)):
        raise ValueError("signed retrieval receipt hashes must be unique")
    return _digest(
        {
            "schema_version": RETRIEVAL_RECEIPT_SET_SCHEMA_VERSION,
            "receipt_hashes": sorted(hashes),
        }
    )


def evaluate_strategy_correlation_identity_bound_transcript_artifact_availability_receipt_candidate_v1(
    identity_bound_transcript_content_bridge_document: Any,
    identity_bound_transcript_content_bridge_verification_context: Any,
    availability_registration_document: Any,
    signed_publication_receipt_document: Any,
    signed_retrieval_receipt_documents: Any,
    *,
    expected_identity_bound_transcript_content_bridge_hash: Any,
    expected_availability_registration_hash: Any,
    expected_signed_publication_receipt_hash: Any,
    expected_retrieval_receipt_set_hash: Any,
) -> dict[str, Any] | None:
    expected_hashes = (
        expected_identity_bound_transcript_content_bridge_hash,
        expected_availability_registration_hash,
        expected_signed_publication_receipt_hash,
        expected_retrieval_receipt_set_hash,
    )
    if not all(_is_hash(value) for value in expected_hashes):
        return None
    if not isinstance(availability_registration_document, Mapping):
        return None
    if not isinstance(signed_publication_receipt_document, Mapping):
        return None
    if not isinstance(signed_retrieval_receipt_documents, (list, tuple)):
        return None
    artifacts = availability_registration_document.get("artifacts")
    retrievers = availability_registration_document.get("retrievers")
    if not isinstance(artifacts, list) or not isinstance(retrievers, list):
        return None
    expected_receipt_count = len(artifacts) * REQUIRED_RETRIEVERS_PER_ARTIFACT
    if len(retrievers) != REQUIRED_RETRIEVERS_PER_ARTIFACT:
        return None
    if len(signed_retrieval_receipt_documents) != expected_receipt_count:
        return None
    try:
        actual_set_hash = build_strategy_correlation_transcript_artifact_retrieval_receipt_set_hash_v1(
            signed_retrieval_receipt_documents
        )
    except (TypeError, ValueError, RecursionError):
        return None
    if actual_set_hash != expected_retrieval_receipt_set_hash:
        return None
    if signed_publication_receipt_document.get(
        "signed_publication_receipt_hash"
    ) != expected_signed_publication_receipt_hash:
        return None
    if not verify_signed_strategy_correlation_transcript_artifact_publication_receipt_v1(
        signed_publication_receipt_document,
        availability_registration_document,
        expected_signed_publication_receipt_hash=expected_signed_publication_receipt_hash,
    ):
        return None

    observed_pairs: set[tuple[str, str]] = set()
    challenges: set[str] = set()
    receipt_hashes: list[str] = []
    for document in signed_retrieval_receipt_documents:
        receipt_hash = document.get("signed_retrieval_receipt_hash")
        if not verify_signed_strategy_correlation_transcript_artifact_retrieval_receipt_v1(
            document,
            availability_registration_document,
            signed_publication_receipt_document,
            expected_signed_retrieval_receipt_hash=receipt_hash,
        ):
            return None
        claim = document.get("retrieval_claim")
        retriever = claim.get("retriever") if isinstance(claim, Mapping) else None
        artifact = claim.get("artifact") if isinstance(claim, Mapping) else None
        source = claim.get("source") if isinstance(claim, Mapping) else None
        if not all(
            isinstance(value, Mapping) for value in (retriever, artifact, source)
        ):
            return None
        pair = (retriever.get("retriever_id"), artifact.get("artifact_id"))
        challenge = source.get("challenge_nonce_hash")
        if pair in observed_pairs or not _is_hash(challenge) or challenge in challenges:
            return None
        observed_pairs.add(pair)
        challenges.add(challenge)
        receipt_hashes.append(receipt_hash)
    expected_pairs = {
        (retriever["retriever_id"], artifact["artifact_id"])
        for retriever in retrievers
        for artifact in artifacts
    }
    if observed_pairs != expected_pairs:
        return None

    if not verify_strategy_correlation_transcript_artifact_availability_registration_v1(
        availability_registration_document,
        identity_bound_transcript_content_bridge_document,
        identity_bound_transcript_content_bridge_verification_context,
        expected_availability_registration_hash=expected_availability_registration_hash,
        expected_identity_bound_transcript_content_bridge_hash=expected_identity_bound_transcript_content_bridge_hash,
    ):
        return None
    if availability_registration_document.get(
        "availability_registration_hash"
    ) != expected_availability_registration_hash:
        return None
    if not isinstance(identity_bound_transcript_content_bridge_document, Mapping):
        return None
    upstream_source = identity_bound_transcript_content_bridge_document.get("source")
    provider = identity_bound_transcript_content_bridge_document.get("provider")
    if not isinstance(upstream_source, Mapping) or not isinstance(provider, Mapping):
        return None

    core = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": STATUS,
        "permission_state": "BLOCKED",
        "permission": "RESEARCH_ONLY_NO_ADMISSION",
        "decision": DECISION,
        "consumer_status": "UNMOUNTED_CANDIDATE",
        "source": {
            "identity_bound_transcript_content_bridge_hash": expected_identity_bound_transcript_content_bridge_hash,
            "availability_registration_hash": expected_availability_registration_hash,
            "signed_publication_receipt_hash": expected_signed_publication_receipt_hash,
            "retrieval_receipt_set_hash": expected_retrieval_receipt_set_hash,
            "content_verification_hash": upstream_source.get(
                "content_verification_hash"
            ),
            "transcript_binding_hash": upstream_source.get(
                "transcript_binding_hash"
            ),
            "provider_preregistration_hash": upstream_source.get(
                "provider_preregistration_hash"
            ),
        },
        "provider": {
            "registry_id": provider.get("registry_id"),
            "registry_revision": provider.get("registry_revision"),
            "outcome": provider.get("outcome"),
        },
        "availability": {
            "artifact_count": len(artifacts),
            "publisher_signature_count": 1,
            "retriever_count": len(retrievers),
            "signed_retrieval_claim_count": len(receipt_hashes),
            "required_retrievers_per_artifact": REQUIRED_RETRIEVERS_PER_ARTIFACT,
            "claim_scope": "LOCAL_SIGNATURES_OVER_PUBLICATION_AND_RETRIEVAL_CLAIMS_ONLY",
        },
        "facts": {
            "upstream_transcript_content_bridge_exactly_verified": True,
            "artifact_catalog_exactly_bound": True,
            "publisher_signature_exactly_verified": True,
            "dual_retriever_signatures_per_artifact_exactly_verified": True,
            "registered_role_key_hashes_structurally_distinct": True,
            "publisher_identity_verified": False,
            "retriever_identities_verified": False,
            "retriever_independence_verified": False,
            "publisher_external_operation_verified": False,
            "actual_network_retrieval_verified": False,
            "public_artifact_availability_verified": False,
            "external_persistence_verified": False,
            "external_provider_conformance_verified": False,
            "raw_locator_exposed": False,
            "raw_public_key_or_signature_exposed": False,
            "raw_artifact_content_exposed": False,
        },
        "blockers": [
            "PUBLISHER_IDENTITY_SOURCE_TRUTH_UNVERIFIED",
            "PUBLISHER_EXTERNAL_OPERATION_UNVERIFIED",
            "RETRIEVER_IDENTITY_SOURCE_TRUTH_UNVERIFIED",
            "RETRIEVER_INDEPENDENCE_SOURCE_TRUTH_UNVERIFIED",
            "ACTUAL_NETWORK_RETRIEVAL_UNVERIFIED",
            "PUBLIC_ARTIFACT_AVAILABILITY_UNVERIFIED",
            "EXTERNAL_PERSISTENCE_UNVERIFIED",
            "EXTERNAL_PROVIDER_CONFORMANCE_UNVERIFIED",
            "RUNTIME_CONSUMER_UNMOUNTED",
            "CURRENT_ADMISSION_BLOCKED",
        ],
        "decision_path": [
            {
                "stage": "SOURCE",
                "state": "LOCAL_PUBLICATION_AND_DUAL_RETRIEVAL_SIGNATURES_VERIFIED",
            },
            {
                "stage": "GAP",
                "state": "EXTERNAL_IDENTITIES_OPERATIONS_AND_AVAILABILITY_UNVERIFIED",
            },
            {"stage": "MATURITY", "state": "UNMOUNTED_LOCAL_CLAIM_CANDIDATE"},
            {"stage": "PERMISSION", "state": "BLOCKED"},
        ],
        "authority": _authority_lock(),
    }
    return _seal(core, "availability_receipt_evidence_hash")


def verify_strategy_correlation_identity_bound_transcript_artifact_availability_receipt_candidate_v1(
    document: Any,
    identity_bound_transcript_content_bridge_document: Any,
    identity_bound_transcript_content_bridge_verification_context: Any,
    availability_registration_document: Any,
    signed_publication_receipt_document: Any,
    signed_retrieval_receipt_documents: Any,
    *,
    expected_availability_receipt_evidence_hash: Any,
    expected_identity_bound_transcript_content_bridge_hash: Any,
    expected_availability_registration_hash: Any,
    expected_signed_publication_receipt_hash: Any,
    expected_retrieval_receipt_set_hash: Any,
) -> bool:
    if not _is_hash(expected_availability_receipt_evidence_hash):
        return False
    evaluated = evaluate_strategy_correlation_identity_bound_transcript_artifact_availability_receipt_candidate_v1(
        identity_bound_transcript_content_bridge_document,
        identity_bound_transcript_content_bridge_verification_context,
        availability_registration_document,
        signed_publication_receipt_document,
        signed_retrieval_receipt_documents,
        expected_identity_bound_transcript_content_bridge_hash=expected_identity_bound_transcript_content_bridge_hash,
        expected_availability_registration_hash=expected_availability_registration_hash,
        expected_signed_publication_receipt_hash=expected_signed_publication_receipt_hash,
        expected_retrieval_receipt_set_hash=expected_retrieval_receipt_set_hash,
    )
    return (
        evaluated is not None
        and evaluated.get("availability_receipt_evidence_hash")
        == expected_availability_receipt_evidence_hash
        and _strict_equal(document, evaluated)
    )
