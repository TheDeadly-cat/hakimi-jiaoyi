from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from types import MappingProxyType
from typing import Any, Mapping, Protocol, runtime_checkable

from exchange_terminal.services.strict_canonical_json_hash import strict_canonical_hash


ANTI_REPLAY_NAMESPACE = (
    "portfolio-risk-downside-tail-post-registration-execution-receipt-v5"
)
CONSUMPTION_REQUEST_SCHEMA_VERSION = (
    "portfolio-risk-post-registration-anti-replay-consumption-request-v1"
)
COMPARE_AND_CONSUME_COMMAND_SCHEMA_VERSION = (
    "anti-replay-compare-and-consume-command-v1"
)
COMPARE_AND_CONSUME_RESULT_SCHEMA_VERSION = (
    "anti-replay-compare-and-consume-result-v1"
)
TARGET_CONSUMPTION_RECEIPT_SCHEMA_VERSION = (
    "portfolio-risk-post-registration-anti-replay-consumption-receipt-v1"
)

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REQUEST_STATIC_FINGERPRINT = (
    "20260823-post-registration-anti-replay-consumption-request-v1-lock-1"
)
_REQUEST_KEYS = frozenset(
    {
        "authority",
        "blockers",
        "decision",
        "facts",
        "request_hash",
        "schema_version",
        "source",
        "static_fingerprint",
        "status",
        "target",
    }
)
_REQUEST_SOURCE_KEYS = frozenset(
    {
        "anti_replay_namespace",
        "anti_replay_scope_hash",
        "attestation_hash",
        "challenge_hash",
        "consumption_key",
        "issuance_preregistration_hash",
        "policy_hash",
        "public_key_spki_sha256",
        "witness_id",
        "witness_verification_hash",
    }
)
_REQUEST_TARGET_KEYS = frozenset(
    {
        "consumption_receipt_schema_version",
        "post_registration_receipt_schema_version",
    }
)


def _is_hash(value: Any) -> bool:
    return isinstance(value, str) and _HASH_PATTERN.fullmatch(value) is not None


def _require_hash(name: str, value: Any) -> str:
    if not _is_hash(value):
        raise ValueError(f"{name} must be a lowercase sha256 hex digest")
    return value


def _require_nonempty(name: str, value: Any, *, maximum: int = 256) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ValueError(f"{name} must be a non-empty bounded string")
    return value


def _verify_request_document(document: Any) -> Mapping[str, Any]:
    if not isinstance(document, Mapping) or frozenset(document) != _REQUEST_KEYS:
        raise ValueError("consumption request-v1 has an inexact top-level shape")
    if not _is_hash(document.get("request_hash")):
        raise ValueError("consumption request-v1 hash is invalid")
    body = dict(document)
    request_hash = body.pop("request_hash")
    if strict_canonical_hash(body) != request_hash:
        raise ValueError("consumption request-v1 seal does not verify")
    if (
        document.get("schema_version") != CONSUMPTION_REQUEST_SCHEMA_VERSION
        or document.get("static_fingerprint") != _REQUEST_STATIC_FINGERPRINT
        or document.get("status") != "BLOCKED"
    ):
        raise ValueError("consumption request-v1 schema or blocked status drifted")
    source = document.get("source")
    target = document.get("target")
    authority = document.get("authority")
    facts = document.get("facts")
    if not isinstance(source, Mapping) or frozenset(source) != _REQUEST_SOURCE_KEYS:
        raise ValueError("consumption request-v1 source shape drifted")
    if not isinstance(target, Mapping) or frozenset(target) != _REQUEST_TARGET_KEYS:
        raise ValueError("consumption request-v1 target shape drifted")
    if not isinstance(authority, Mapping) or any(value is not False for value in authority.values()):
        raise ValueError("consumption request-v1 authority must remain locked")
    if not isinstance(facts, Mapping):
        raise ValueError("consumption request-v1 facts are invalid")
    false_facts = (
        "external_linearizability_verified",
        "external_registry_bound",
        "network_accessed",
        "post_registration_receipt_issued",
        "raw_nonce_embedded",
        "registry_identity_verified",
        "runtime_assets_accessed",
        "target_consumption_receipt_issued",
        "trusted_consumption_time_verified",
    )
    if any(facts.get(name) is not False for name in false_facts):
        raise ValueError("consumption request-v1 contains an unsupported claim")
    hash_fields = (
        "anti_replay_scope_hash",
        "attestation_hash",
        "challenge_hash",
        "consumption_key",
        "issuance_preregistration_hash",
        "policy_hash",
        "public_key_spki_sha256",
        "witness_verification_hash",
    )
    if any(not _is_hash(source.get(name)) for name in hash_fields):
        raise ValueError("consumption request-v1 source hash is invalid")
    if source.get("anti_replay_namespace") != ANTI_REPLAY_NAMESPACE:
        raise ValueError("consumption request-v1 namespace drifted")
    expected_key = strict_canonical_hash(
        {
            "anti_replay_namespace": source["anti_replay_namespace"],
            "anti_replay_scope_hash": source["anti_replay_scope_hash"],
        }
    )
    if source.get("consumption_key") != expected_key:
        raise ValueError("consumption request-v1 key does not bind namespace and scope")
    _require_nonempty("witness_id", source.get("witness_id"))
    if (
        target.get("consumption_receipt_schema_version")
        != TARGET_CONSUMPTION_RECEIPT_SCHEMA_VERSION
    ):
        raise ValueError("consumption request-v1 target receipt schema drifted")
    return document


class AntiReplayRegistryOutcomeV1(str, Enum):
    CONSUMED = "CONSUMED"
    DUPLICATE_REJECTED = "DUPLICATE_REJECTED"
    CONFLICT_REJECTED = "CONFLICT_REJECTED"


@dataclass(frozen=True, slots=True)
class AntiReplayCompareAndConsumeCommandV1:
    anti_replay_scope_hash: str
    attestation_hash: str
    challenge_hash: str
    consumption_key: str
    issuance_preregistration_hash: str
    policy_hash: str
    request_hash: str
    witness_id: str
    witness_verification_hash: str
    anti_replay_namespace: str = ANTI_REPLAY_NAMESPACE
    target_receipt_schema_version: str = TARGET_CONSUMPTION_RECEIPT_SCHEMA_VERSION
    schema_version: str = COMPARE_AND_CONSUME_COMMAND_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in (
            "anti_replay_scope_hash",
            "attestation_hash",
            "challenge_hash",
            "consumption_key",
            "issuance_preregistration_hash",
            "policy_hash",
            "request_hash",
            "witness_verification_hash",
        ):
            _require_hash(name, getattr(self, name))
        _require_nonempty("witness_id", self.witness_id)
        if self.anti_replay_namespace != ANTI_REPLAY_NAMESPACE:
            raise ValueError("anti-replay namespace must match the preregistered value")
        if self.target_receipt_schema_version != TARGET_CONSUMPTION_RECEIPT_SCHEMA_VERSION:
            raise ValueError("target receipt schema must match consumption receipt-v1")
        if self.schema_version != COMPARE_AND_CONSUME_COMMAND_SCHEMA_VERSION:
            raise ValueError("compare-and-consume command schema alias is forbidden")
        expected_key = strict_canonical_hash(
            {
                "anti_replay_namespace": self.anti_replay_namespace,
                "anti_replay_scope_hash": self.anti_replay_scope_hash,
            }
        )
        if self.consumption_key != expected_key:
            raise ValueError("consumption key does not bind namespace and scope")

    @classmethod
    def from_request_document(
        cls, document: Mapping[str, Any]
    ) -> "AntiReplayCompareAndConsumeCommandV1":
        verified = _verify_request_document(document)
        source = verified["source"]
        return cls(
            anti_replay_scope_hash=source["anti_replay_scope_hash"],
            attestation_hash=source["attestation_hash"],
            challenge_hash=source["challenge_hash"],
            consumption_key=source["consumption_key"],
            issuance_preregistration_hash=source["issuance_preregistration_hash"],
            policy_hash=source["policy_hash"],
            request_hash=verified["request_hash"],
            witness_id=source["witness_id"],
            witness_verification_hash=source["witness_verification_hash"],
        )


@dataclass(frozen=True, slots=True)
class AntiReplayCompareAndConsumeResultV1:
    outcome: AntiReplayRegistryOutcomeV1
    request_hash: str
    consumption_key: str
    registry_id: str
    registry_revision: int
    receipt_document: Mapping[str, Any] | None = None
    schema_version: str = COMPARE_AND_CONSUME_RESULT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, AntiReplayRegistryOutcomeV1):
            raise ValueError("result outcome must be an exact v1 enum value")
        _require_hash("request_hash", self.request_hash)
        _require_hash("consumption_key", self.consumption_key)
        _require_nonempty("registry_id", self.registry_id, maximum=128)
        if (
            isinstance(self.registry_revision, bool)
            or not isinstance(self.registry_revision, int)
            or self.registry_revision < 0
        ):
            raise ValueError("registry_revision must be a non-negative integer")
        if self.schema_version != COMPARE_AND_CONSUME_RESULT_SCHEMA_VERSION:
            raise ValueError("compare-and-consume result schema alias is forbidden")
        if self.receipt_document is not None:
            if not isinstance(self.receipt_document, Mapping):
                raise ValueError("receipt_document must be a mapping or None")
            object.__setattr__(
                self, "receipt_document", MappingProxyType(dict(self.receipt_document))
            )


@runtime_checkable
class AntiReplayRegistryPortV1(Protocol):
    @property
    def registry_id(self) -> str:
        ...

    def compare_and_consume(
        self, command: AntiReplayCompareAndConsumeCommandV1
    ) -> AntiReplayCompareAndConsumeResultV1:
        ...
