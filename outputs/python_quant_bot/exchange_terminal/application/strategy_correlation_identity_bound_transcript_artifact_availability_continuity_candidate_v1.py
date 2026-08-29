from __future__ import annotations

import copy
import hashlib
import re
from collections.abc import Mapping, Sequence
from typing import Any

from cryptography.exceptions import InvalidSignature

from exchange_terminal.application.strategy_correlation_identity_bound_transcript_artifact_availability_receipt_candidate_v1 import (
    build_strategy_correlation_transcript_artifact_retrieval_receipt_set_hash_v1,
    verify_signed_strategy_correlation_transcript_artifact_publication_receipt_v1,
    verify_strategy_correlation_identity_bound_transcript_artifact_availability_receipt_candidate_v1,
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


STATIC_FINGERPRINT = "20260825-transcript-artifact-availability-continuity-candidate-1"
STATUS = "OBSERVED_PREREGISTERED_THREE_EPOCH_LOCAL_RETRIEVAL_CONTINUITY_CANDIDATE"
DECISION = "LOCAL_THREE_EPOCH_RETRIEVAL_CONTINUITY_VERIFIED_EXTERNAL_DURABILITY_UNPROVEN"

CONTINUITY_SCHEDULE_SCHEMA_VERSION = (
    "strategy-correlation-transcript-artifact-availability-continuity-schedule-v1"
)
SIGNED_CONTINUITY_SCHEDULE_SCHEMA_VERSION = (
    "signed-strategy-correlation-transcript-artifact-availability-continuity-schedule-v1"
)
EPOCH_OBSERVATION_SCHEMA_VERSION = (
    "strategy-correlation-transcript-artifact-availability-epoch-observation-v1"
)
CONTINUITY_EVIDENCE_SCHEMA_VERSION = (
    "strategy-correlation-identity-bound-transcript-artifact-availability-continuity-evidence-v1"
)

SCHEDULE_STATUS = "PREREGISTERED_THREE_EPOCH_LOCAL_RETRIEVAL_CONTINUITY_SCHEDULE"
SCHEDULE_DECISION = "SIGNED_LOGICAL_EPOCH_PLAN_ONLY_NO_EXTERNAL_TIME_TRUTH"
SIGNED_SCHEDULE_STATUS = "SIGNED_PREREGISTERED_THREE_EPOCH_LOCAL_RETRIEVAL_CONTINUITY_SCHEDULE"
OBSERVATION_STATUS = "OBSERVED_LOCAL_SCHEDULED_EPOCH_RETRIEVAL_CLAIMS"

SIGNATURE_ALGORITHM = "ED25519"
SIGNATURE_MESSAGE_FORMAT = "RAW_32_BYTE_SHA256_DIGEST"
SIGNATURE_DOMAIN = "STRATEGY_CORRELATION_ARTIFACT_AVAILABILITY_CONTINUITY_SCHEDULE_V1"
EPOCH_COUNT = 3
ARTIFACT_COUNT = 2
RETRIEVER_COUNT = 2
RECEIPTS_PER_EPOCH = ARTIFACT_COUNT * RETRIEVER_COUNT

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")

_AVAILABILITY_CONTEXT_KEYS = frozenset(
    {
        "identity_bound_transcript_content_bridge_document",
        "identity_bound_transcript_content_bridge_verification_context",
        "availability_registration_document",
        "signed_publication_receipt_document",
        "signed_retrieval_receipt_documents",
        "expected_identity_bound_transcript_content_bridge_hash",
        "expected_availability_registration_hash",
        "expected_signed_publication_receipt_hash",
        "expected_retrieval_receipt_set_hash",
    }
)

_EPOCH_INPUT_KEYS = frozenset(
    {"epoch_id", "ordinal", "slot_commitment_hash", "challenge_rows"}
)
_CHALLENGE_ROW_KEYS = frozenset(
    {"artifact_id", "retriever_id", "challenge_nonce_hash"}
)
_EPOCH_EVIDENCE_ROW_KEYS = frozenset(
    {
        "epoch_observation_document",
        "availability_receipt_evidence_document",
        "availability_receipt_verification_context",
        "expected_availability_receipt_evidence_hash",
    }
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _is_hash(value: Any) -> bool:
    return isinstance(value, str) and _HASH_RE.fullmatch(value) is not None


def _is_id(value: Any) -> bool:
    return isinstance(value, str) and _ID_RE.fullmatch(value) is not None


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _exact_keys(value: Any, expected: frozenset[str]) -> bool:
    return isinstance(value, Mapping) and frozenset(value.keys()) == expected


def _sealed_hash_valid(document: Any, hash_field: str, expected_hash: Any) -> bool:
    if not isinstance(document, Mapping) or not _is_hash(expected_hash):
        return False
    if document.get(hash_field) != expected_hash:
        return False
    payload = copy.deepcopy(dict(document))
    payload.pop(hash_field, None)
    try:
        return strict_canonical_hash(payload) == expected_hash
    except (TypeError, ValueError):
        return False


def _authority() -> dict[str, bool]:
    return {
        "current_admission_allowed": False,
        "external_artifact_durability_verified": False,
        "external_persistence_verified": False,
        "external_time_truth_verified": False,
        "live_order_allowed": False,
        "network_retrieval_verified": False,
        "paper_authorized": False,
        "profitability_proven": False,
        "provider_activation_allowed": False,
        "public_artifact_availability_verified": False,
        "publisher_identity_verified": False,
        "retriever_identities_verified": False,
        "retriever_independence_verified": False,
        "runtime_consumer_bound": False,
    }


def _permission() -> dict[str, str]:
    return {"paper": "UNAUTHORIZED", "live": "UNAUTHORIZED"}


def _schedule_policy() -> dict[str, Any]:
    return {
        "epoch_count": EPOCH_COUNT,
        "artifact_count": ARTIFACT_COUNT,
        "retriever_count": RETRIEVER_COUNT,
        "receipts_per_epoch": RECEIPTS_PER_EPOCH,
        "epoch_basis": "PREREGISTERED_LOGICAL_SLOT_COMMITMENT_NO_EXTERNAL_TIME_TRUTH",
        "challenge_scope": "UNIQUE_HASH_COMMITMENT_PER_ARTIFACT_RETRIEVER_EPOCH",
        "continuity_chain": "PREVIOUS_EPOCH_DESCRIPTOR_HASH_AND_PREVIOUS_OBSERVATION_HASH",
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "signature_domain": SIGNATURE_DOMAIN,
    }


def _schedule_genesis_hash(
    availability_registration_hash: str,
    signed_publication_receipt_hash: str,
) -> str:
    return strict_canonical_hash(
        {
            "schema_version": "strategy-correlation-artifact-availability-continuity-schedule-genesis-v1",
            "availability_registration_hash": availability_registration_hash,
            "signed_publication_receipt_hash": signed_publication_receipt_hash,
        }
    )


def build_strategy_correlation_transcript_artifact_availability_continuity_genesis_hash_v1(
    signed_continuity_schedule_hash: Any,
) -> str:
    _require(_is_hash(signed_continuity_schedule_hash), "invalid signed continuity schedule hash")
    return strict_canonical_hash(
        {
            "schema_version": "strategy-correlation-artifact-availability-continuity-observation-genesis-v1",
            "signed_continuity_schedule_hash": signed_continuity_schedule_hash,
        }
    )


def _availability_shape(
    registration_document: Any,
    signed_publication_receipt_document: Any,
    *,
    expected_availability_registration_hash: Any,
    expected_signed_publication_receipt_hash: Any,
) -> tuple[dict[str, Any], list[str], list[str]]:
    _require(
        _sealed_hash_valid(
            registration_document,
            "availability_registration_hash",
            expected_availability_registration_hash,
        ),
        "invalid availability registration",
    )
    _require(
        verify_signed_strategy_correlation_transcript_artifact_publication_receipt_v1(
            signed_publication_receipt_document,
            registration_document,
            expected_signed_publication_receipt_hash=expected_signed_publication_receipt_hash,
        ),
        "invalid signed publication receipt",
    )
    publisher = registration_document.get("publisher")
    artifacts = registration_document.get("artifacts")
    retrievers = registration_document.get("retrievers")
    _require(isinstance(publisher, Mapping), "missing publisher registration")
    _require(_is_sequence(artifacts) and len(artifacts) == ARTIFACT_COUNT, "invalid artifact catalog")
    _require(_is_sequence(retrievers) and len(retrievers) == RETRIEVER_COUNT, "invalid retriever catalog")
    artifact_ids = sorted(item.get("artifact_id") for item in artifacts if isinstance(item, Mapping))
    retriever_ids = sorted(item.get("retriever_id") for item in retrievers if isinstance(item, Mapping))
    _require(len(artifact_ids) == ARTIFACT_COUNT and all(_is_id(item) for item in artifact_ids), "invalid artifact ids")
    _require(len(retriever_ids) == RETRIEVER_COUNT and all(_is_id(item) for item in retriever_ids), "invalid retriever ids")
    _require(len(set(artifact_ids)) == ARTIFACT_COUNT, "duplicate artifact ids")
    _require(len(set(retriever_ids)) == RETRIEVER_COUNT, "duplicate retriever ids")
    _require(
        signed_publication_receipt_document.get("source", {}).get("availability_registration_hash")
        == expected_availability_registration_hash,
        "publication registration source drift",
    )
    return copy.deepcopy(dict(publisher)), artifact_ids, retriever_ids


def _build_epoch_descriptors(
    epoch_rows: Any,
    *,
    artifact_ids: list[str],
    retriever_ids: list[str],
    schedule_genesis_hash: str,
) -> list[dict[str, Any]]:
    _require(_is_sequence(epoch_rows) and len(epoch_rows) == EPOCH_COUNT, "exactly three epoch rows required")
    expected_pairs = {(artifact_id, retriever_id) for artifact_id in artifact_ids for retriever_id in retriever_ids}
    global_challenges: set[str] = set()
    slot_commitments: set[str] = set()
    epoch_ids: set[str] = set()
    previous_descriptor_hash = schedule_genesis_hash
    descriptors: list[dict[str, Any]] = []

    for expected_ordinal, raw_epoch in enumerate(epoch_rows, start=1):
        _require(_exact_keys(raw_epoch, _EPOCH_INPUT_KEYS), "invalid epoch row shape")
        epoch_id = raw_epoch["epoch_id"]
        ordinal = raw_epoch["ordinal"]
        slot_commitment_hash = raw_epoch["slot_commitment_hash"]
        challenge_rows = raw_epoch["challenge_rows"]
        _require(_is_id(epoch_id) and epoch_id not in epoch_ids, "invalid or duplicate epoch id")
        _require(type(ordinal) is int and ordinal == expected_ordinal, "epoch ordinals must be contiguous")
        _require(_is_hash(slot_commitment_hash) and slot_commitment_hash not in slot_commitments, "invalid or duplicate slot commitment")
        _require(_is_sequence(challenge_rows) and len(challenge_rows) == RECEIPTS_PER_EPOCH, "invalid challenge count")

        normalized_challenges: list[dict[str, str]] = []
        pairs: set[tuple[str, str]] = set()
        for raw_challenge in challenge_rows:
            _require(_exact_keys(raw_challenge, _CHALLENGE_ROW_KEYS), "invalid challenge row shape")
            artifact_id = raw_challenge["artifact_id"]
            retriever_id = raw_challenge["retriever_id"]
            challenge_nonce_hash = raw_challenge["challenge_nonce_hash"]
            pair = (artifact_id, retriever_id)
            _require(pair in expected_pairs and pair not in pairs, "invalid or duplicate artifact/retriever pair")
            _require(_is_hash(challenge_nonce_hash), "invalid challenge nonce hash")
            _require(challenge_nonce_hash not in global_challenges, "challenge nonce replay across epochs")
            pairs.add(pair)
            global_challenges.add(challenge_nonce_hash)
            normalized_challenges.append(
                {
                    "artifact_id": artifact_id,
                    "retriever_id": retriever_id,
                    "challenge_nonce_hash": challenge_nonce_hash,
                }
            )
        _require(pairs == expected_pairs, "challenge rows do not cover exact Cartesian product")
        normalized_challenges.sort(key=lambda item: (item["artifact_id"], item["retriever_id"]))
        challenge_set_hash = strict_canonical_hash(
            {
                "schema_version": "strategy-correlation-artifact-availability-epoch-challenge-set-v1",
                "epoch_id": epoch_id,
                "challenge_rows": normalized_challenges,
            }
        )
        descriptor = seal_strict_canonical_document(
            {
                "schema_version": "strategy-correlation-artifact-availability-continuity-epoch-descriptor-v1",
                "epoch_id": epoch_id,
                "ordinal": ordinal,
                "slot_commitment_hash": slot_commitment_hash,
                "previous_epoch_descriptor_hash": previous_descriptor_hash,
                "challenge_set_hash": challenge_set_hash,
                "challenge_rows": normalized_challenges,
            },
            "epoch_descriptor_hash",
        )
        descriptors.append(descriptor)
        previous_descriptor_hash = descriptor["epoch_descriptor_hash"]
        epoch_ids.add(epoch_id)
        slot_commitments.add(slot_commitment_hash)
    return descriptors


def build_strategy_correlation_transcript_artifact_availability_continuity_schedule_v1(
    availability_registration_document: Any,
    signed_publication_receipt_document: Any,
    *,
    expected_availability_registration_hash: Any,
    expected_signed_publication_receipt_hash: Any,
    epoch_rows: Any,
) -> dict[str, Any]:
    publisher, artifact_ids, retriever_ids = _availability_shape(
        availability_registration_document,
        signed_publication_receipt_document,
        expected_availability_registration_hash=expected_availability_registration_hash,
        expected_signed_publication_receipt_hash=expected_signed_publication_receipt_hash,
    )
    descriptors = _build_epoch_descriptors(
        epoch_rows,
        artifact_ids=artifact_ids,
        retriever_ids=retriever_ids,
        schedule_genesis_hash=_schedule_genesis_hash(
            expected_availability_registration_hash,
            expected_signed_publication_receipt_hash,
        ),
    )
    return seal_strict_canonical_document(
        {
            "schema_version": CONTINUITY_SCHEDULE_SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": SCHEDULE_STATUS,
            "decision": SCHEDULE_DECISION,
            "source": {
                "availability_registration_hash": expected_availability_registration_hash,
                "signed_publication_receipt_hash": expected_signed_publication_receipt_hash,
            },
            "publisher": publisher,
            "policy": _schedule_policy(),
            "epochs": descriptors,
            "permission_state": "BLOCKED",
            "authority": _authority(),
        },
        "continuity_schedule_hash",
    )


def _validate_continuity_schedule(
    document: Any,
    availability_registration_document: Any,
    signed_publication_receipt_document: Any,
    *,
    expected_continuity_schedule_hash: Any,
) -> None:
    expected_keys = frozenset(
        {
            "schema_version",
            "static_fingerprint",
            "status",
            "decision",
            "source",
            "publisher",
            "policy",
            "epochs",
            "permission_state",
            "authority",
            "continuity_schedule_hash",
        }
    )
    _require(_exact_keys(document, expected_keys), "invalid continuity schedule shape")
    _require(_sealed_hash_valid(document, "continuity_schedule_hash", expected_continuity_schedule_hash), "invalid continuity schedule hash")
    source = document["source"]
    _require(
        _exact_keys(source, frozenset({"availability_registration_hash", "signed_publication_receipt_hash"})),
        "invalid schedule source",
    )
    publisher, artifact_ids, retriever_ids = _availability_shape(
        availability_registration_document,
        signed_publication_receipt_document,
        expected_availability_registration_hash=source["availability_registration_hash"],
        expected_signed_publication_receipt_hash=source["signed_publication_receipt_hash"],
    )
    _require(document["schema_version"] == CONTINUITY_SCHEDULE_SCHEMA_VERSION, "schedule schema drift")
    _require(document["static_fingerprint"] == STATIC_FINGERPRINT, "schedule fingerprint drift")
    _require(document["status"] == SCHEDULE_STATUS and document["decision"] == SCHEDULE_DECISION, "schedule status drift")
    _require(strict_json_contract_equal(document["publisher"], publisher), "schedule publisher drift")
    _require(strict_json_contract_equal(document["policy"], _schedule_policy()), "schedule policy drift")
    _require(document["permission_state"] == "BLOCKED", "schedule permission drift")
    _require(strict_json_contract_equal(document["authority"], _authority()), "schedule authority drift")

    raw_epochs = document["epochs"]
    _require(_is_sequence(raw_epochs) and len(raw_epochs) == EPOCH_COUNT, "invalid schedule epoch count")
    input_rows: list[dict[str, Any]] = []
    for raw_epoch in raw_epochs:
        _require(
            _exact_keys(
                raw_epoch,
                frozenset(
                    {
                        "schema_version",
                        "epoch_id",
                        "ordinal",
                        "slot_commitment_hash",
                        "previous_epoch_descriptor_hash",
                        "challenge_set_hash",
                        "challenge_rows",
                        "epoch_descriptor_hash",
                    }
                ),
            ),
            "invalid epoch descriptor shape",
        )
        input_rows.append(
            {
                "epoch_id": raw_epoch["epoch_id"],
                "ordinal": raw_epoch["ordinal"],
                "slot_commitment_hash": raw_epoch["slot_commitment_hash"],
                "challenge_rows": copy.deepcopy(raw_epoch["challenge_rows"]),
            }
        )
    expected_epochs = _build_epoch_descriptors(
        input_rows,
        artifact_ids=artifact_ids,
        retriever_ids=retriever_ids,
        schedule_genesis_hash=_schedule_genesis_hash(
            source["availability_registration_hash"],
            source["signed_publication_receipt_hash"],
        ),
    )
    _require(strict_json_contract_equal(raw_epochs, expected_epochs), "epoch descriptor chain drift")


def verify_strategy_correlation_transcript_artifact_availability_continuity_schedule_v1(
    document: Any,
    availability_registration_document: Any,
    signed_publication_receipt_document: Any,
    *,
    expected_continuity_schedule_hash: Any,
) -> bool:
    try:
        _validate_continuity_schedule(
            document,
            availability_registration_document,
            signed_publication_receipt_document,
            expected_continuity_schedule_hash=expected_continuity_schedule_hash,
        )
        return True
    except (KeyError, TypeError, ValueError):
        return False


def _verify_ed25519_hash_signature(
    *,
    public_key_spki_base64: Any,
    signature_base64: Any,
    expected_public_key_spki_sha256: Any,
    message_hash: Any,
) -> None:
    _require(_is_hash(expected_public_key_spki_sha256), "invalid expected public key hash")
    _require(_is_hash(message_hash), "invalid signature message hash")
    spki_bytes = decode_canonical_base64_v1(public_key_spki_base64, "public_key_spki_base64")
    signature = decode_canonical_base64_v1(signature_base64, "signature_base64")
    _require(len(signature) == 64, "invalid Ed25519 signature length")
    _require(hashlib.sha256(spki_bytes).hexdigest() == expected_public_key_spki_sha256, "public key hash drift")
    public_key = load_canonical_ed25519_public_key_v1(spki_bytes)
    try:
        public_key.verify(signature, bytes.fromhex(message_hash))
    except InvalidSignature as exc:
        raise ValueError("invalid Ed25519 signature") from exc


def build_signed_strategy_correlation_transcript_artifact_availability_continuity_schedule_v1(
    continuity_schedule_document: Any,
    availability_registration_document: Any,
    signed_publication_receipt_document: Any,
    *,
    public_key_spki_base64: Any,
    signature_base64: Any,
    expected_continuity_schedule_hash: Any,
) -> dict[str, Any]:
    _validate_continuity_schedule(
        continuity_schedule_document,
        availability_registration_document,
        signed_publication_receipt_document,
        expected_continuity_schedule_hash=expected_continuity_schedule_hash,
    )
    expected_public_key_hash = continuity_schedule_document["publisher"].get("public_key_spki_sha256")
    _verify_ed25519_hash_signature(
        public_key_spki_base64=public_key_spki_base64,
        signature_base64=signature_base64,
        expected_public_key_spki_sha256=expected_public_key_hash,
        message_hash=expected_continuity_schedule_hash,
    )
    return seal_strict_canonical_document(
        {
            "schema_version": SIGNED_CONTINUITY_SCHEDULE_SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": SIGNED_SCHEDULE_STATUS,
            "signature_algorithm": SIGNATURE_ALGORITHM,
            "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
            "signature_domain": SIGNATURE_DOMAIN,
            "continuity_schedule": copy.deepcopy(dict(continuity_schedule_document)),
            "public_key_spki_base64": public_key_spki_base64,
            "public_key_spki_sha256": expected_public_key_hash,
            "signature_base64": signature_base64,
            "source": {"continuity_schedule_hash": expected_continuity_schedule_hash},
            "permission_state": "BLOCKED",
            "authority": _authority(),
        },
        "signed_continuity_schedule_hash",
    )


def verify_signed_strategy_correlation_transcript_artifact_availability_continuity_schedule_v1(
    document: Any,
    availability_registration_document: Any,
    signed_publication_receipt_document: Any,
    *,
    expected_signed_continuity_schedule_hash: Any,
    expected_continuity_schedule_hash: Any,
) -> bool:
    expected_keys = frozenset(
        {
            "schema_version",
            "static_fingerprint",
            "status",
            "signature_algorithm",
            "signature_message_format",
            "signature_domain",
            "continuity_schedule",
            "public_key_spki_base64",
            "public_key_spki_sha256",
            "signature_base64",
            "source",
            "permission_state",
            "authority",
            "signed_continuity_schedule_hash",
        }
    )
    try:
        _require(_exact_keys(document, expected_keys), "invalid signed schedule shape")
        _require(
            _sealed_hash_valid(
                document,
                "signed_continuity_schedule_hash",
                expected_signed_continuity_schedule_hash,
            ),
            "invalid signed schedule hash",
        )
        expected = build_signed_strategy_correlation_transcript_artifact_availability_continuity_schedule_v1(
            document["continuity_schedule"],
            availability_registration_document,
            signed_publication_receipt_document,
            public_key_spki_base64=document["public_key_spki_base64"],
            signature_base64=document["signature_base64"],
            expected_continuity_schedule_hash=expected_continuity_schedule_hash,
        )
        return strict_json_contract_equal(document, expected)
    except (KeyError, TypeError, ValueError):
        return False


def _verify_availability_evidence(
    document: Any,
    context: Any,
    *,
    expected_availability_receipt_evidence_hash: Any,
) -> bool:
    if not _exact_keys(context, _AVAILABILITY_CONTEXT_KEYS):
        return False
    if not _is_hash(expected_availability_receipt_evidence_hash):
        return False
    if not isinstance(document, Mapping) or document.get("availability_receipt_evidence_hash") != expected_availability_receipt_evidence_hash:
        return False
    try:
        return verify_strategy_correlation_identity_bound_transcript_artifact_availability_receipt_candidate_v1(
            document,
            context["identity_bound_transcript_content_bridge_document"],
            context["identity_bound_transcript_content_bridge_verification_context"],
            context["availability_registration_document"],
            context["signed_publication_receipt_document"],
            context["signed_retrieval_receipt_documents"],
            expected_availability_receipt_evidence_hash=expected_availability_receipt_evidence_hash,
            expected_identity_bound_transcript_content_bridge_hash=context[
                "expected_identity_bound_transcript_content_bridge_hash"
            ],
            expected_availability_registration_hash=context["expected_availability_registration_hash"],
            expected_signed_publication_receipt_hash=context["expected_signed_publication_receipt_hash"],
            expected_retrieval_receipt_set_hash=context["expected_retrieval_receipt_set_hash"],
        )
    except (KeyError, TypeError, ValueError):
        return False


def _receipt_projection(
    signed_retrieval_receipt_documents: Any,
) -> tuple[list[dict[str, str]], list[str]]:
    _require(
        _is_sequence(signed_retrieval_receipt_documents)
        and len(signed_retrieval_receipt_documents) == RECEIPTS_PER_EPOCH,
        "exactly four signed retrieval receipts required",
    )
    rows: list[dict[str, str]] = []
    receipt_hashes: list[str] = []
    pairs: set[tuple[str, str]] = set()
    challenges: set[str] = set()
    for receipt in signed_retrieval_receipt_documents:
        _require(isinstance(receipt, Mapping), "invalid retrieval receipt")
        receipt_hash = receipt.get("signed_retrieval_receipt_hash")
        claim = receipt.get("retrieval_claim")
        _require(_is_hash(receipt_hash) and isinstance(claim, Mapping), "invalid retrieval receipt shape")
        source = claim.get("source")
        artifact = claim.get("artifact")
        retriever = claim.get("retriever")
        retrieval = claim.get("retrieval")
        _require(
            isinstance(source, Mapping)
            and isinstance(artifact, Mapping)
            and isinstance(retriever, Mapping)
            and isinstance(retrieval, Mapping),
            "invalid retrieval claim shape",
        )
        artifact_id = artifact.get("artifact_id")
        retriever_id = retriever.get("retriever_id")
        challenge_nonce_hash = source.get("challenge_nonce_hash")
        pair = (artifact_id, retriever_id)
        _require(_is_id(artifact_id) and _is_id(retriever_id), "invalid retrieval claim identity")
        _require(pair not in pairs, "duplicate retrieval pair")
        _require(_is_hash(challenge_nonce_hash) and challenge_nonce_hash not in challenges, "invalid or duplicate challenge")
        pairs.add(pair)
        challenges.add(challenge_nonce_hash)
        receipt_hashes.append(receipt_hash)
        rows.append(
            {
                "artifact_id": artifact_id,
                "retriever_id": retriever_id,
                "challenge_nonce_hash": challenge_nonce_hash,
            }
        )
    _require(len(set(receipt_hashes)) == RECEIPTS_PER_EPOCH, "duplicate signed retrieval receipt")
    rows.sort(key=lambda item: (item["artifact_id"], item["retriever_id"]))
    receipt_hashes.sort()
    return rows, receipt_hashes


def build_strategy_correlation_transcript_artifact_availability_epoch_observation_v1(
    signed_continuity_schedule_document: Any,
    availability_receipt_evidence_document: Any,
    availability_receipt_verification_context: Any,
    *,
    epoch_id: Any,
    previous_epoch_observation_hash: Any,
    expected_signed_continuity_schedule_hash: Any,
    expected_continuity_schedule_hash: Any,
    expected_availability_receipt_evidence_hash: Any,
) -> dict[str, Any]:
    _require(_exact_keys(availability_receipt_verification_context, _AVAILABILITY_CONTEXT_KEYS), "invalid availability context")
    registration = availability_receipt_verification_context["availability_registration_document"]
    publication = availability_receipt_verification_context["signed_publication_receipt_document"]
    _require(
        verify_signed_strategy_correlation_transcript_artifact_availability_continuity_schedule_v1(
            signed_continuity_schedule_document,
            registration,
            publication,
            expected_signed_continuity_schedule_hash=expected_signed_continuity_schedule_hash,
            expected_continuity_schedule_hash=expected_continuity_schedule_hash,
        ),
        "invalid signed continuity schedule",
    )
    _require(
        _verify_availability_evidence(
            availability_receipt_evidence_document,
            availability_receipt_verification_context,
            expected_availability_receipt_evidence_hash=expected_availability_receipt_evidence_hash,
        ),
        "invalid availability receipt evidence",
    )
    schedule = signed_continuity_schedule_document["continuity_schedule"]
    descriptors = [item for item in schedule["epochs"] if item.get("epoch_id") == epoch_id]
    _require(len(descriptors) == 1, "epoch id is not preregistered exactly once")
    descriptor = descriptors[0]
    receipt_rows, receipt_hashes = _receipt_projection(
        availability_receipt_verification_context["signed_retrieval_receipt_documents"]
    )
    _require(strict_json_contract_equal(receipt_rows, descriptor["challenge_rows"]), "retrieval challenges do not match schedule")
    computed_receipt_set_hash = build_strategy_correlation_transcript_artifact_retrieval_receipt_set_hash_v1(
        availability_receipt_verification_context["signed_retrieval_receipt_documents"]
    )
    expected_receipt_set_hash = availability_receipt_verification_context["expected_retrieval_receipt_set_hash"]
    _require(computed_receipt_set_hash == expected_receipt_set_hash, "retrieval receipt set hash drift")
    _require(
        availability_receipt_evidence_document.get("source", {}).get("retrieval_receipt_set_hash")
        == expected_receipt_set_hash,
        "availability evidence receipt set drift",
    )
    _require(_is_hash(previous_epoch_observation_hash), "invalid previous observation hash")
    return seal_strict_canonical_document(
        {
            "schema_version": EPOCH_OBSERVATION_SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": OBSERVATION_STATUS,
            "source": {
                "signed_continuity_schedule_hash": expected_signed_continuity_schedule_hash,
                "continuity_schedule_hash": expected_continuity_schedule_hash,
                "availability_receipt_evidence_hash": expected_availability_receipt_evidence_hash,
                "retrieval_receipt_set_hash": expected_receipt_set_hash,
                "previous_epoch_observation_hash": previous_epoch_observation_hash,
            },
            "epoch": {
                "epoch_id": descriptor["epoch_id"],
                "ordinal": descriptor["ordinal"],
                "epoch_descriptor_hash": descriptor["epoch_descriptor_hash"],
                "slot_commitment_hash": descriptor["slot_commitment_hash"],
                "challenge_set_hash": descriptor["challenge_set_hash"],
            },
            "receipt_hash_set_hash": strict_canonical_hash(
                {
                    "schema_version": "strategy-correlation-artifact-availability-epoch-receipt-hash-set-v1",
                    "signed_retrieval_receipt_hashes": receipt_hashes,
                }
            ),
            "facts": {
                "availability_receipt_evidence_exactly_verified": True,
                "scheduled_challenge_set_exactly_matched": True,
                "signed_retrieval_receipt_set_exactly_bound": True,
                "external_time_truth_verified": False,
                "external_artifact_durability_verified": False,
                "public_artifact_availability_verified": False,
            },
            "permission_state": "BLOCKED",
            "authority": _authority(),
        },
        "epoch_observation_hash",
    )


def verify_strategy_correlation_transcript_artifact_availability_epoch_observation_v1(
    document: Any,
    signed_continuity_schedule_document: Any,
    availability_receipt_evidence_document: Any,
    availability_receipt_verification_context: Any,
    *,
    expected_epoch_observation_hash: Any,
    expected_signed_continuity_schedule_hash: Any,
    expected_continuity_schedule_hash: Any,
    expected_availability_receipt_evidence_hash: Any,
) -> bool:
    expected_keys = frozenset(
        {
            "schema_version",
            "static_fingerprint",
            "status",
            "source",
            "epoch",
            "receipt_hash_set_hash",
            "facts",
            "permission_state",
            "authority",
            "epoch_observation_hash",
        }
    )
    try:
        _require(_exact_keys(document, expected_keys), "invalid epoch observation shape")
        _require(_sealed_hash_valid(document, "epoch_observation_hash", expected_epoch_observation_hash), "invalid epoch observation hash")
        expected = build_strategy_correlation_transcript_artifact_availability_epoch_observation_v1(
            signed_continuity_schedule_document,
            availability_receipt_evidence_document,
            availability_receipt_verification_context,
            epoch_id=document["epoch"]["epoch_id"],
            previous_epoch_observation_hash=document["source"]["previous_epoch_observation_hash"],
            expected_signed_continuity_schedule_hash=expected_signed_continuity_schedule_hash,
            expected_continuity_schedule_hash=expected_continuity_schedule_hash,
            expected_availability_receipt_evidence_hash=expected_availability_receipt_evidence_hash,
        )
        return strict_json_contract_equal(document, expected)
    except (KeyError, TypeError, ValueError):
        return False


def _contexts_share_fixed_upstream(first: Mapping[str, Any], current: Mapping[str, Any]) -> bool:
    varying = {"signed_retrieval_receipt_documents", "expected_retrieval_receipt_set_hash"}
    for key in _AVAILABILITY_CONTEXT_KEYS - varying:
        if not strict_json_contract_equal(first[key], current[key]):
            return False
    return True


def evaluate_strategy_correlation_identity_bound_transcript_artifact_availability_continuity_candidate_v1(
    signed_continuity_schedule_document: Any,
    epoch_evidence_rows: Any,
    *,
    expected_signed_continuity_schedule_hash: Any,
    expected_continuity_schedule_hash: Any,
    expected_final_epoch_observation_hash: Any,
) -> dict[str, Any] | None:
    try:
        _require(_is_sequence(epoch_evidence_rows) and len(epoch_evidence_rows) == EPOCH_COUNT, "exactly three epoch evidence rows required")
        _require(all(_exact_keys(row, _EPOCH_EVIDENCE_ROW_KEYS) for row in epoch_evidence_rows), "invalid epoch evidence row shape")
        first_context = epoch_evidence_rows[0]["availability_receipt_verification_context"]
        _require(_exact_keys(first_context, _AVAILABILITY_CONTEXT_KEYS), "invalid first availability context")
        registration = first_context["availability_registration_document"]
        publication = first_context["signed_publication_receipt_document"]
        _require(
            verify_signed_strategy_correlation_transcript_artifact_availability_continuity_schedule_v1(
                signed_continuity_schedule_document,
                registration,
                publication,
                expected_signed_continuity_schedule_hash=expected_signed_continuity_schedule_hash,
                expected_continuity_schedule_hash=expected_continuity_schedule_hash,
            ),
            "invalid signed continuity schedule",
        )
        schedule = signed_continuity_schedule_document["continuity_schedule"]
        descriptors = schedule["epochs"]
        previous_observation_hash = build_strategy_correlation_transcript_artifact_availability_continuity_genesis_hash_v1(
            expected_signed_continuity_schedule_hash
        )
        global_challenges: set[str] = set()
        global_receipts: set[str] = set()
        observation_hashes: list[str] = []
        availability_evidence_hashes: list[str] = []

        for index, row in enumerate(epoch_evidence_rows):
            observation = row["epoch_observation_document"]
            evidence = row["availability_receipt_evidence_document"]
            context = row["availability_receipt_verification_context"]
            expected_evidence_hash = row["expected_availability_receipt_evidence_hash"]
            _require(_exact_keys(context, _AVAILABILITY_CONTEXT_KEYS), "invalid availability context")
            _require(_contexts_share_fixed_upstream(first_context, context), "fixed upstream context drift across epochs")
            _require(isinstance(observation, Mapping), "invalid epoch observation")
            descriptor = descriptors[index]
            _require(observation.get("epoch", {}).get("epoch_id") == descriptor["epoch_id"], "epoch order drift")
            _require(observation.get("epoch", {}).get("ordinal") == descriptor["ordinal"], "epoch ordinal drift")
            _require(
                observation.get("source", {}).get("previous_epoch_observation_hash") == previous_observation_hash,
                "observation hash chain drift",
            )
            _require(
                observation.get("source", {}).get("availability_receipt_evidence_hash") == expected_evidence_hash,
                "observation evidence source drift",
            )
            receipt_rows, receipt_hashes = _receipt_projection(context["signed_retrieval_receipt_documents"])
            _require(strict_json_contract_equal(receipt_rows, descriptor["challenge_rows"]), "scheduled challenge drift")
            epoch_challenges = {item["challenge_nonce_hash"] for item in receipt_rows}
            _require(global_challenges.isdisjoint(epoch_challenges), "challenge replay across epochs")
            _require(global_receipts.isdisjoint(receipt_hashes), "retrieval receipt replay across epochs")
            _require(
                verify_strategy_correlation_transcript_artifact_availability_epoch_observation_v1(
                    observation,
                    signed_continuity_schedule_document,
                    evidence,
                    context,
                    expected_epoch_observation_hash=observation.get("epoch_observation_hash"),
                    expected_signed_continuity_schedule_hash=expected_signed_continuity_schedule_hash,
                    expected_continuity_schedule_hash=expected_continuity_schedule_hash,
                    expected_availability_receipt_evidence_hash=expected_evidence_hash,
                ),
                "invalid epoch observation",
            )
            global_challenges.update(epoch_challenges)
            global_receipts.update(receipt_hashes)
            previous_observation_hash = observation["epoch_observation_hash"]
            observation_hashes.append(previous_observation_hash)
            availability_evidence_hashes.append(expected_evidence_hash)

        _require(previous_observation_hash == expected_final_epoch_observation_hash, "final observation hash drift")
        _require(len(global_challenges) == EPOCH_COUNT * RECEIPTS_PER_EPOCH, "global challenge count drift")
        _require(len(global_receipts) == EPOCH_COUNT * RECEIPTS_PER_EPOCH, "global receipt count drift")
        result = seal_strict_canonical_document(
            {
                "schema_version": CONTINUITY_EVIDENCE_SCHEMA_VERSION,
                "static_fingerprint": STATIC_FINGERPRINT,
                "status": STATUS,
                "decision": DECISION,
                "source": {
                    "availability_registration_hash": schedule["source"]["availability_registration_hash"],
                    "signed_publication_receipt_hash": schedule["source"]["signed_publication_receipt_hash"],
                    "continuity_schedule_hash": expected_continuity_schedule_hash,
                    "signed_continuity_schedule_hash": expected_signed_continuity_schedule_hash,
                    "final_epoch_observation_hash": expected_final_epoch_observation_hash,
                },
                "continuity": {
                    "epoch_count": EPOCH_COUNT,
                    "artifact_count": ARTIFACT_COUNT,
                    "retriever_count": RETRIEVER_COUNT,
                    "signed_retrieval_claim_count": EPOCH_COUNT * RECEIPTS_PER_EPOCH,
                    "availability_receipt_evidence_hashes": availability_evidence_hashes,
                    "epoch_observation_hashes": observation_hashes,
                },
                "facts": {
                    "signed_preregistered_schedule_exactly_verified": True,
                    "three_logical_epochs_exactly_verified": True,
                    "artifact_retriever_cartesian_product_per_epoch_exactly_verified": True,
                    "challenge_nonce_hashes_globally_unique": True,
                    "signed_retrieval_receipt_hashes_globally_unique": True,
                    "previous_epoch_observation_hash_chain_exactly_verified": True,
                    "local_multi_epoch_retrieval_continuity_claim_verified": True,
                    "external_time_truth_verified": False,
                    "external_artifact_durability_verified": False,
                    "external_persistence_verified": False,
                    "network_retrieval_verified": False,
                    "public_artifact_availability_verified": False,
                    "publisher_identity_verified": False,
                    "retriever_identities_verified": False,
                    "retriever_independence_verified": False,
                    "raw_schedule_or_challenge_rows_exposed": False,
                    "raw_public_key_signature_or_receipt_exposed": False,
                },
                "blockers": [
                    "NO_EXTERNAL_TIME_AUTHORITY",
                    "NO_EXTERNAL_PUBLICATION_OBSERVATION",
                    "NO_NETWORK_RETRIEVAL_OBSERVATION",
                    "NO_EXTERNAL_DURABILITY_OR_PERSISTENCE_EVIDENCE",
                    "NO_PUBLISHER_IDENTITY_PROOF",
                    "NO_RETRIEVER_IDENTITY_OR_INDEPENDENCE_PROOF",
                    "RUNTIME_CONSUMER_NOT_BOUND",
                    "CURRENT_SELECTOR_UNCHANGED",
                    "PAPER_AND_LIVE_UNAUTHORIZED",
                    "PROFITABILITY_NOT_PROVEN",
                ],
                "decision_path": [
                    "SOURCE: SIGNED_PREREGISTERED_LOGICAL_EPOCH_PLAN_AND_LOCAL_RETRIEVAL_RECEIPTS",
                    "GAP: EXTERNAL_TIME_PUBLICATION_RETRIEVAL_DURABILITY_AND_INDEPENDENCE_UNPROVEN",
                    "MATURITY: UNMOUNTED_SYNTHETIC_CONTINUITY_CANDIDATE",
                    "PERMISSION: BLOCKED",
                ],
                "consumer_status": "UNMOUNTED_CANDIDATE",
                "permission_state": "BLOCKED",
                "permission": _permission(),
                "authority": _authority(),
            },
            "continuity_evidence_hash",
        )
        return result
    except (KeyError, TypeError, ValueError):
        return None


def verify_strategy_correlation_identity_bound_transcript_artifact_availability_continuity_candidate_v1(
    document: Any,
    signed_continuity_schedule_document: Any,
    epoch_evidence_rows: Any,
    *,
    expected_continuity_evidence_hash: Any,
    expected_signed_continuity_schedule_hash: Any,
    expected_continuity_schedule_hash: Any,
    expected_final_epoch_observation_hash: Any,
) -> bool:
    expected_keys = frozenset(
        {
            "schema_version",
            "static_fingerprint",
            "status",
            "decision",
            "source",
            "continuity",
            "facts",
            "blockers",
            "decision_path",
            "consumer_status",
            "permission_state",
            "permission",
            "authority",
            "continuity_evidence_hash",
        }
    )
    try:
        _require(_exact_keys(document, expected_keys), "invalid continuity evidence shape")
        _require(_sealed_hash_valid(document, "continuity_evidence_hash", expected_continuity_evidence_hash), "invalid continuity evidence hash")
        expected = evaluate_strategy_correlation_identity_bound_transcript_artifact_availability_continuity_candidate_v1(
            signed_continuity_schedule_document,
            epoch_evidence_rows,
            expected_signed_continuity_schedule_hash=expected_signed_continuity_schedule_hash,
            expected_continuity_schedule_hash=expected_continuity_schedule_hash,
            expected_final_epoch_observation_hash=expected_final_epoch_observation_hash,
        )
        return expected is not None and strict_json_contract_equal(document, expected)
    except (KeyError, TypeError, ValueError):
        return False
