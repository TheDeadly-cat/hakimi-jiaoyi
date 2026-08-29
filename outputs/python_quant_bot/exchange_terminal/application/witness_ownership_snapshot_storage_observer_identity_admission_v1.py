"""Dual-source observer identity admission candidate for storage evidence.

The module validates local canonical structure and Ed25519 signatures from the
two trust roots preregistered by ADR0419.  It performs no external source call
and therefore never marks external identity or source truth as verified.
"""

from __future__ import annotations

from hashlib import sha256
import re
from typing import Any

from cryptography.exceptions import InvalidSignature

from exchange_terminal.application import (
    witness_ownership_key_revocation_snapshot_storage_evidence_quorum_v1 as storage_evidence,
)
from exchange_terminal.application import (
    witness_ownership_state_provider_identity_source_adapter_preregistration_v1 as identity_source,
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


CLAIM_SCHEMA_VERSION = (
    "witness-ownership-snapshot-storage-observer-identity-claim-v1"
)
DUAL_SIGNED_ASSERTION_SCHEMA_VERSION = (
    "witness-ownership-snapshot-storage-observer-dual-signed-identity-assertion-v1"
)
ADMISSION_EVALUATION_SCHEMA_VERSION = (
    "witness-ownership-snapshot-storage-observer-identity-admission-evaluation-v1"
)
STATIC_FINGERPRINT = (
    "20260824-witness-ownership-snapshot-storage-observer-identity-"
    "admission-v1-lock-1"
)

IDENTITY_REGISTRY_SIGNATURE_DOMAIN = (
    "hakimi.strategy-correlation.witness-ownership.storage-observer."
    "identity-registry.v1"
)
REVOCATION_SOURCE_SIGNATURE_DOMAIN = (
    "hakimi.strategy-correlation.witness-ownership.storage-observer."
    "revocation-source.v1"
)
ADMISSION_SCOPE = "ISOLATED_STORAGE_EVIDENCE_OBSERVER_ONLY"
IDENTITY_STATUS_ACTIVE = "ACTIVE"
REVOCATION_STATUS_NOT_REVOKED = "NOT_REVOKED"

EXPECTED_OBSERVER_COUNT = 3
STATUS_DUAL_SIGNED_ADMISSION_CANDIDATE = (
    "DUAL_SIGNED_OBSERVER_IDENTITY_ASSERTIONS_STRUCTURALLY_ADMISSIBLE_"
    "EXTERNAL_SOURCE_TRUTH_UNPROVEN"
)
STATUS_BLOCK = "BLOCK"
GATE_STATUS_UNKNOWN = "UNKNOWN"
GATE_STATUS_BLOCK = "BLOCK"
PERMISSION_STATE = "RESEARCH_ONLY"

IDENTITY_SOURCE_PREREGISTRATION_IMPLEMENTATION_SHA256 = (
    "d087684a6a7e64bd2acf6e213144083ad30e5b88bf091f9f56edb942465f4374"
)
STORAGE_EVIDENCE_QUORUM_IMPLEMENTATION_SHA256 = (
    "7111362ca0c1fa914bf6ea65a358347e6889e2f63184a520f5cdf0cdc37665a3"
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _is_sha256(value: Any) -> bool:
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


def _is_exact_observer_registration(document: Any) -> bool:
    if type(document) is not dict:
        return False
    try:
        expected = storage_evidence.build_witness_ownership_snapshot_storage_observer_registration_v1(
            observer_id=document["observer_id"],
            trust_domain=document["trust_domain"],
            public_key_spki_sha256=document["public_key_spki_sha256"],
        )
    except KeyError:
        return False
    return bool(expected) and strict_json_contract_equal(document, expected)


def build_witness_ownership_storage_observer_identity_claim_v1(
    identity_source_preregistration_document: Any,
    observer_registration_document: Any,
    *,
    claim_nonce_hash: Any,
    expected_identity_source_preregistration_hash: Any,
    identity_source_preregistration_kwargs: Any,
) -> dict[str, Any]:
    if type(identity_source_preregistration_kwargs) is not dict:
        return {}
    if not identity_source.verify_witness_ownership_provider_identity_source_adapter_preregistration_v1(
        identity_source_preregistration_document,
        **identity_source_preregistration_kwargs,
    ):
        return {}
    if not _is_exact_observer_registration(observer_registration_document):
        return {}
    if (
        not _is_sha256(claim_nonce_hash)
        or not _is_sha256(expected_identity_source_preregistration_hash)
        or expected_identity_source_preregistration_hash
        != identity_source_preregistration_document["adapter_preregistration_hash"]
    ):
        return {}
    document = {
        "schema_version": CLAIM_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "admission_scope": ADMISSION_SCOPE,
        "identity_source_adapter_preregistration_hash": (
            identity_source_preregistration_document[
                "adapter_preregistration_hash"
            ]
        ),
        "identity_registry_snapshot_sha256": (
            identity_source_preregistration_document["identity_registry_source"][
                "registry_snapshot_sha256"
            ]
        ),
        "revocation_source_snapshot_sha256": (
            identity_source_preregistration_document[
                "revocation_authority_source"
            ]["source_snapshot_sha256"]
        ),
        "observer_registration_hash": observer_registration_document[
            "observer_registration_hash"
        ],
        "observer_id": observer_registration_document["observer_id"],
        "observer_trust_domain": observer_registration_document["trust_domain"],
        "observer_public_key_spki_sha256": observer_registration_document[
            "public_key_spki_sha256"
        ],
        "identity_status": IDENTITY_STATUS_ACTIVE,
        "revocation_status": REVOCATION_STATUS_NOT_REVOKED,
        "claim_nonce_hash": claim_nonce_hash,
    }
    return seal_strict_canonical_document(document, "observer_identity_claim_hash")


def _is_exact_claim(
    document: Any,
    identity_source_preregistration_document: Any,
    observer_registration_document: Any,
    *,
    identity_source_preregistration_kwargs: Any,
) -> bool:
    if type(document) is not dict:
        return False
    try:
        expected = build_witness_ownership_storage_observer_identity_claim_v1(
            identity_source_preregistration_document,
            observer_registration_document,
            claim_nonce_hash=document["claim_nonce_hash"],
            expected_identity_source_preregistration_hash=(
                identity_source_preregistration_document[
                    "adapter_preregistration_hash"
                ]
            ),
            identity_source_preregistration_kwargs=(
                identity_source_preregistration_kwargs
            ),
        )
    except KeyError:
        return False
    return bool(expected) and strict_json_contract_equal(document, expected)


def build_witness_ownership_storage_observer_identity_signature_message_hash_v1(
    claim_document: Any,
    identity_source_preregistration_document: Any,
    observer_registration_document: Any,
    *,
    signature_domain: Any,
    identity_source_preregistration_kwargs: Any,
) -> str:
    if signature_domain not in {
        IDENTITY_REGISTRY_SIGNATURE_DOMAIN,
        REVOCATION_SOURCE_SIGNATURE_DOMAIN,
    }:
        return ""
    if not _is_exact_claim(
        claim_document,
        identity_source_preregistration_document,
        observer_registration_document,
        identity_source_preregistration_kwargs=(
            identity_source_preregistration_kwargs
        ),
    ):
        return ""
    source_snapshot_hash = (
        claim_document["identity_registry_snapshot_sha256"]
        if signature_domain == IDENTITY_REGISTRY_SIGNATURE_DOMAIN
        else claim_document["revocation_source_snapshot_sha256"]
    )
    return strict_canonical_hash(
        {
            "signature_domain": signature_domain,
            "dual_signed_assertion_schema_version": (
                DUAL_SIGNED_ASSERTION_SCHEMA_VERSION
            ),
            "observer_identity_claim_hash": claim_document[
                "observer_identity_claim_hash"
            ],
            "source_snapshot_sha256": source_snapshot_hash,
        }
    )


def _verify_signature(
    *,
    public_key_spki_base64: Any,
    signature_base64: Any,
    expected_spki_sha256: str,
    message_hash: str,
) -> bool:
    try:
        spki = decode_canonical_base64_v1(
            public_key_spki_base64,
            "source_public_key_spki_base64",
        )
        signature = decode_canonical_base64_v1(
            signature_base64,
            "source_signature_base64",
        )
        if sha256(spki).hexdigest() != expected_spki_sha256:
            return False
        public_key = load_canonical_ed25519_public_key_v1(spki)
        public_key.verify(signature, bytes.fromhex(message_hash))
    except (InvalidSignature, TypeError, ValueError, UnicodeError):
        return False
    return True


def build_dual_signed_witness_ownership_storage_observer_identity_assertion_v1(
    claim_document: Any,
    identity_source_preregistration_document: Any,
    observer_registration_document: Any,
    *,
    identity_registry_public_key_spki_base64: Any,
    identity_registry_signature_base64: Any,
    revocation_source_public_key_spki_base64: Any,
    revocation_source_signature_base64: Any,
    identity_source_preregistration_kwargs: Any,
) -> dict[str, Any]:
    if not _is_exact_claim(
        claim_document,
        identity_source_preregistration_document,
        observer_registration_document,
        identity_source_preregistration_kwargs=(
            identity_source_preregistration_kwargs
        ),
    ):
        return {}
    identity_message_hash = build_witness_ownership_storage_observer_identity_signature_message_hash_v1(
        claim_document,
        identity_source_preregistration_document,
        observer_registration_document,
        signature_domain=IDENTITY_REGISTRY_SIGNATURE_DOMAIN,
        identity_source_preregistration_kwargs=(
            identity_source_preregistration_kwargs
        ),
    )
    revocation_message_hash = build_witness_ownership_storage_observer_identity_signature_message_hash_v1(
        claim_document,
        identity_source_preregistration_document,
        observer_registration_document,
        signature_domain=REVOCATION_SOURCE_SIGNATURE_DOMAIN,
        identity_source_preregistration_kwargs=(
            identity_source_preregistration_kwargs
        ),
    )
    identity_source_document = identity_source_preregistration_document
    if not _verify_signature(
        public_key_spki_base64=identity_registry_public_key_spki_base64,
        signature_base64=identity_registry_signature_base64,
        expected_spki_sha256=identity_source_document["identity_registry_source"][
            "registry_trust_root_sha256"
        ],
        message_hash=identity_message_hash,
    ):
        return {}
    if not _verify_signature(
        public_key_spki_base64=revocation_source_public_key_spki_base64,
        signature_base64=revocation_source_signature_base64,
        expected_spki_sha256=identity_source_document[
            "revocation_authority_source"
        ]["source_trust_root_sha256"],
        message_hash=revocation_message_hash,
    ):
        return {}
    document = {
        "schema_version": DUAL_SIGNED_ASSERTION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "claim_document": claim_document,
        "identity_registry_signature_domain": (
            IDENTITY_REGISTRY_SIGNATURE_DOMAIN
        ),
        "identity_registry_public_key_spki_base64": (
            identity_registry_public_key_spki_base64
        ),
        "identity_registry_signature_base64": identity_registry_signature_base64,
        "identity_registry_signature_message_hash": identity_message_hash,
        "revocation_source_signature_domain": REVOCATION_SOURCE_SIGNATURE_DOMAIN,
        "revocation_source_public_key_spki_base64": (
            revocation_source_public_key_spki_base64
        ),
        "revocation_source_signature_base64": revocation_source_signature_base64,
        "revocation_source_signature_message_hash": revocation_message_hash,
    }
    return seal_strict_canonical_document(
        document,
        "dual_signed_observer_identity_assertion_hash",
    )


def _build_evaluation(
    identity_source_preregistration_document: dict[str, Any],
    *,
    status: str,
    gate_status: str,
    blocker_codes: tuple[str, ...],
    covered_observer_count: int,
    assertion_hashes: list[str],
    verified: bool,
) -> dict[str, Any]:
    assertion_bundle_hash = (
        strict_canonical_hash(
            {"dual_signed_observer_identity_assertion_hashes": sorted(assertion_hashes)}
        )
        if assertion_hashes
        else None
    )
    document = {
        "schema_version": ADMISSION_EVALUATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "gate_status": gate_status,
        "blocker_codes": list(blocker_codes),
        "admission_scope": ADMISSION_SCOPE,
        "identity_source_adapter_preregistration_hash": (
            identity_source_preregistration_document[
                "adapter_preregistration_hash"
            ]
        ),
        "identity_source_preregistration_implementation_sha256": (
            IDENTITY_SOURCE_PREREGISTRATION_IMPLEMENTATION_SHA256
        ),
        "storage_evidence_quorum_implementation_sha256": (
            STORAGE_EVIDENCE_QUORUM_IMPLEMENTATION_SHA256
        ),
        "expected_observer_count": EXPECTED_OBSERVER_COUNT,
        "covered_observer_count": covered_observer_count,
        "assertion_bundle_hash": assertion_bundle_hash,
        "identity_registry_signatures_verified": verified,
        "revocation_source_signatures_verified": verified,
        "observer_registration_coverage_verified": verified,
        "observer_structural_independence_verified": verified,
        "isolated_evidence_observer_admission_candidate": verified,
        "external_observer_identity_verified": False,
        "external_source_truth_verified": False,
        "external_persistence_independently_verified": False,
        "permission_state": PERMISSION_STATE,
        "permission": False,
        "paper_authorized": False,
        "live_authorized": False,
        "snapshot_publication_authorized": False,
        "current_chain_activated": False,
    }
    return seal_strict_canonical_document(document, "observer_admission_evaluation_hash")


def evaluate_witness_ownership_storage_observer_identity_admission_v1(
    dual_signed_assertion_documents: Any,
    identity_source_preregistration_document: Any,
    observer_registration_documents: Any,
    *,
    identity_source_preregistration_kwargs: Any,
) -> dict[str, Any]:
    if type(identity_source_preregistration_kwargs) is not dict:
        return {}
    if not identity_source.verify_witness_ownership_provider_identity_source_adapter_preregistration_v1(
        identity_source_preregistration_document,
        **identity_source_preregistration_kwargs,
    ):
        return {}
    if (
        type(observer_registration_documents) is not list
        or len(observer_registration_documents) != EXPECTED_OBSERVER_COUNT
        or not all(
            _is_exact_observer_registration(item)
            for item in observer_registration_documents
        )
    ):
        return _build_evaluation(
            identity_source_preregistration_document,
            status=STATUS_BLOCK,
            gate_status=GATE_STATUS_BLOCK,
            blocker_codes=("observer_registration_set_invalid",),
            covered_observer_count=0,
            assertion_hashes=[],
            verified=False,
        )
    observer_by_id = {
        item["observer_id"]: item for item in observer_registration_documents
    }
    if (
        len(observer_by_id) != EXPECTED_OBSERVER_COUNT
        or len({item["trust_domain"] for item in observer_registration_documents})
        != EXPECTED_OBSERVER_COUNT
        or len(
            {
                item["public_key_spki_sha256"]
                for item in observer_registration_documents
            }
        )
        != EXPECTED_OBSERVER_COUNT
    ):
        return _build_evaluation(
            identity_source_preregistration_document,
            status=STATUS_BLOCK,
            gate_status=GATE_STATUS_BLOCK,
            blocker_codes=("observer_structural_independence_invalid",),
            covered_observer_count=0,
            assertion_hashes=[],
            verified=False,
        )
    if (
        type(dual_signed_assertion_documents) is not list
        or len(dual_signed_assertion_documents) != EXPECTED_OBSERVER_COUNT
    ):
        return _build_evaluation(
            identity_source_preregistration_document,
            status=STATUS_BLOCK,
            gate_status=GATE_STATUS_BLOCK,
            blocker_codes=("observer_assertion_cardinality_invalid",),
            covered_observer_count=0,
            assertion_hashes=[],
            verified=False,
        )

    covered_ids: set[str] = set()
    assertion_hashes: list[str] = []
    claim_nonces: list[str] = []
    for signed_document in dual_signed_assertion_documents:
        if type(signed_document) is not dict:
            blocker = "dual_signed_observer_identity_assertion_invalid"
            break
        claim = signed_document.get("claim_document")
        observer_id = claim.get("observer_id") if type(claim) is dict else None
        observer_registration = observer_by_id.get(observer_id)
        if observer_registration is None:
            blocker = "dual_signed_observer_identity_assertion_invalid"
            break
        rebuilt = build_dual_signed_witness_ownership_storage_observer_identity_assertion_v1(
            claim,
            identity_source_preregistration_document,
            observer_registration,
            identity_registry_public_key_spki_base64=signed_document.get(
                "identity_registry_public_key_spki_base64"
            ),
            identity_registry_signature_base64=signed_document.get(
                "identity_registry_signature_base64"
            ),
            revocation_source_public_key_spki_base64=signed_document.get(
                "revocation_source_public_key_spki_base64"
            ),
            revocation_source_signature_base64=signed_document.get(
                "revocation_source_signature_base64"
            ),
            identity_source_preregistration_kwargs=(
                identity_source_preregistration_kwargs
            ),
        )
        if not rebuilt or not strict_json_contract_equal(signed_document, rebuilt):
            blocker = "dual_signed_observer_identity_assertion_invalid"
            break
        covered_ids.add(observer_id)
        assertion_hashes.append(
            signed_document["dual_signed_observer_identity_assertion_hash"]
        )
        claim_nonces.append(claim["claim_nonce_hash"])
    else:
        blocker = ""

    if blocker:
        return _build_evaluation(
            identity_source_preregistration_document,
            status=STATUS_BLOCK,
            gate_status=GATE_STATUS_BLOCK,
            blocker_codes=(blocker,),
            covered_observer_count=len(covered_ids),
            assertion_hashes=assertion_hashes,
            verified=False,
        )
    if len(set(assertion_hashes)) != len(assertion_hashes):
        blocker = "dual_signed_observer_identity_assertion_replay_detected"
    elif len(set(claim_nonces)) != len(claim_nonces):
        blocker = "observer_identity_claim_nonce_replay_detected"
    elif covered_ids != set(observer_by_id):
        blocker = "observer_identity_assertion_coverage_invalid"
    else:
        blocker = ""
    if blocker:
        return _build_evaluation(
            identity_source_preregistration_document,
            status=STATUS_BLOCK,
            gate_status=GATE_STATUS_BLOCK,
            blocker_codes=(blocker,),
            covered_observer_count=len(covered_ids),
            assertion_hashes=assertion_hashes,
            verified=False,
        )
    return _build_evaluation(
        identity_source_preregistration_document,
        status=STATUS_DUAL_SIGNED_ADMISSION_CANDIDATE,
        gate_status=GATE_STATUS_UNKNOWN,
        blocker_codes=(),
        covered_observer_count=len(covered_ids),
        assertion_hashes=assertion_hashes,
        verified=True,
    )


def verify_witness_ownership_storage_observer_identity_admission_v1(
    document: Any,
    dual_signed_assertion_documents: Any,
    identity_source_preregistration_document: Any,
    observer_registration_documents: Any,
    *,
    expected_observer_admission_evaluation_hash: Any,
    identity_source_preregistration_kwargs: Any,
) -> bool:
    if not _is_sha256(expected_observer_admission_evaluation_hash):
        return False
    expected = evaluate_witness_ownership_storage_observer_identity_admission_v1(
        dual_signed_assertion_documents,
        identity_source_preregistration_document,
        observer_registration_documents,
        identity_source_preregistration_kwargs=(
            identity_source_preregistration_kwargs
        ),
    )
    return (
        bool(expected)
        and expected.get("observer_admission_evaluation_hash")
        == expected_observer_admission_evaluation_hash
        and strict_json_contract_equal(document, expected)
    )


__all__ = [
    "ADMISSION_EVALUATION_SCHEMA_VERSION",
    "ADMISSION_SCOPE",
    "CLAIM_SCHEMA_VERSION",
    "DUAL_SIGNED_ASSERTION_SCHEMA_VERSION",
    "EXPECTED_OBSERVER_COUNT",
    "GATE_STATUS_BLOCK",
    "GATE_STATUS_UNKNOWN",
    "IDENTITY_REGISTRY_SIGNATURE_DOMAIN",
    "IDENTITY_STATUS_ACTIVE",
    "PERMISSION_STATE",
    "REVOCATION_SOURCE_SIGNATURE_DOMAIN",
    "REVOCATION_STATUS_NOT_REVOKED",
    "STATIC_FINGERPRINT",
    "STATUS_BLOCK",
    "STATUS_DUAL_SIGNED_ADMISSION_CANDIDATE",
    "build_dual_signed_witness_ownership_storage_observer_identity_assertion_v1",
    "build_witness_ownership_storage_observer_identity_claim_v1",
    "build_witness_ownership_storage_observer_identity_signature_message_hash_v1",
    "evaluate_witness_ownership_storage_observer_identity_admission_v1",
    "verify_witness_ownership_storage_observer_identity_admission_v1",
]
