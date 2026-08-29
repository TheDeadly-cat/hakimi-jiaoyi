"""Namespace-parameterized anti-replay registry port contract v2.

V1 remains intentionally bound to one portfolio-risk post-registration
namespace.  V2 is a compatible new surface for explicitly preregistered
namespaces; it does not provide a registry implementation or conformance proof.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Protocol, runtime_checkable

from exchange_terminal.application.ports.anti_replay_registry_v1 import (
    AntiReplayRegistryOutcomeV1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


COMMAND_SCHEMA_VERSION = "anti-replay-compare-and-consume-command-v2"
REQUEST_SCHEMA_VERSION = "anti-replay-compare-and-consume-request-v2"
RESULT_SCHEMA_VERSION = "anti-replay-compare-and-consume-result-v2"
STATIC_FINGERPRINT = "20260823-anti-replay-registry-port-v2-lock-1"

_HEX = frozenset("0123456789abcdef")
_REQUEST_FIELDS = frozenset(
    {
        "schema_version",
        "static_fingerprint",
        "anti_replay_namespace",
        "namespace_preregistration_hash",
        "anti_replay_scope_hash",
        "subject_hash",
        "challenge_hash",
        "consumption_key",
        "policy_hash",
        "request_context_hash",
        "actor_id_hash",
        "evidence_hash",
        "target_receipt_schema_version",
        "request_hash",
    }
)


def _is_hash(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in _HEX for character in value)
    )


def _require_hash(name: str, value: Any) -> str:
    if not _is_hash(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")
    return value


def _require_nonempty(name: str, value: Any, *, maximum: int = 256) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a trimmed non-empty string")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds maximum length {maximum}")
    return value


def build_anti_replay_consumption_key_v2(
    *, anti_replay_namespace: str, anti_replay_scope_hash: str
) -> str:
    """Bind a consumption key to one explicit namespace and scope."""

    namespace = _require_nonempty(
        "anti_replay_namespace", anti_replay_namespace, maximum=160
    )
    scope_hash = _require_hash("anti_replay_scope_hash", anti_replay_scope_hash)
    return strict_canonical_hash(
        {
            "anti_replay_namespace": namespace,
            "anti_replay_scope_hash": scope_hash,
        }
    )


def build_anti_replay_compare_and_consume_request_v2(
    *,
    anti_replay_namespace: str,
    namespace_preregistration_hash: str,
    anti_replay_scope_hash: str,
    subject_hash: str,
    challenge_hash: str,
    policy_hash: str,
    request_context_hash: str,
    actor_id_hash: str,
    evidence_hash: str,
    target_receipt_schema_version: str,
) -> dict[str, Any]:
    namespace = _require_nonempty(
        "anti_replay_namespace", anti_replay_namespace, maximum=160
    )
    scope_hash = _require_hash("anti_replay_scope_hash", anti_replay_scope_hash)
    document = {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "anti_replay_namespace": namespace,
        "namespace_preregistration_hash": _require_hash(
            "namespace_preregistration_hash", namespace_preregistration_hash
        ),
        "anti_replay_scope_hash": scope_hash,
        "subject_hash": _require_hash("subject_hash", subject_hash),
        "challenge_hash": _require_hash("challenge_hash", challenge_hash),
        "consumption_key": build_anti_replay_consumption_key_v2(
            anti_replay_namespace=namespace,
            anti_replay_scope_hash=scope_hash,
        ),
        "policy_hash": _require_hash("policy_hash", policy_hash),
        "request_context_hash": _require_hash(
            "request_context_hash", request_context_hash
        ),
        "actor_id_hash": _require_hash("actor_id_hash", actor_id_hash),
        "evidence_hash": _require_hash("evidence_hash", evidence_hash),
        "target_receipt_schema_version": _require_nonempty(
            "target_receipt_schema_version",
            target_receipt_schema_version,
            maximum=160,
        ),
    }
    return seal_strict_canonical_document(document, "request_hash")


def verify_anti_replay_compare_and_consume_request_v2(document: Any) -> bool:
    if not isinstance(document, Mapping) or frozenset(document) != _REQUEST_FIELDS:
        return False
    try:
        rebuilt = build_anti_replay_compare_and_consume_request_v2(
            anti_replay_namespace=document["anti_replay_namespace"],
            namespace_preregistration_hash=document[
                "namespace_preregistration_hash"
            ],
            anti_replay_scope_hash=document["anti_replay_scope_hash"],
            subject_hash=document["subject_hash"],
            challenge_hash=document["challenge_hash"],
            policy_hash=document["policy_hash"],
            request_context_hash=document["request_context_hash"],
            actor_id_hash=document["actor_id_hash"],
            evidence_hash=document["evidence_hash"],
            target_receipt_schema_version=document[
                "target_receipt_schema_version"
            ],
        )
    except (KeyError, TypeError, ValueError):
        return False
    return strict_json_contract_equal(dict(document), rebuilt)


@dataclass(frozen=True, slots=True)
class AntiReplayCompareAndConsumeCommandV2:
    anti_replay_namespace: str
    namespace_preregistration_hash: str
    anti_replay_scope_hash: str
    subject_hash: str
    challenge_hash: str
    consumption_key: str
    policy_hash: str
    request_context_hash: str
    actor_id_hash: str
    evidence_hash: str
    target_receipt_schema_version: str
    request_hash: str
    schema_version: str = COMMAND_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != COMMAND_SCHEMA_VERSION:
            raise ValueError("command schema version must match v2")
        namespace = _require_nonempty(
            "anti_replay_namespace", self.anti_replay_namespace, maximum=160
        )
        scope_hash = _require_hash(
            "anti_replay_scope_hash", self.anti_replay_scope_hash
        )
        for name in (
            "namespace_preregistration_hash",
            "subject_hash",
            "challenge_hash",
            "policy_hash",
            "request_context_hash",
            "actor_id_hash",
            "evidence_hash",
            "request_hash",
        ):
            _require_hash(name, getattr(self, name))
        _require_nonempty(
            "target_receipt_schema_version",
            self.target_receipt_schema_version,
            maximum=160,
        )
        expected_key = build_anti_replay_consumption_key_v2(
            anti_replay_namespace=namespace,
            anti_replay_scope_hash=scope_hash,
        )
        if self.consumption_key != expected_key:
            raise ValueError("consumption key does not bind namespace and scope")

    @classmethod
    def from_request_document(
        cls, document: Mapping[str, Any]
    ) -> "AntiReplayCompareAndConsumeCommandV2":
        if not verify_anti_replay_compare_and_consume_request_v2(document):
            raise ValueError("request document does not satisfy the exact v2 contract")
        return cls(
            anti_replay_namespace=document["anti_replay_namespace"],
            namespace_preregistration_hash=document[
                "namespace_preregistration_hash"
            ],
            anti_replay_scope_hash=document["anti_replay_scope_hash"],
            subject_hash=document["subject_hash"],
            challenge_hash=document["challenge_hash"],
            consumption_key=document["consumption_key"],
            policy_hash=document["policy_hash"],
            request_context_hash=document["request_context_hash"],
            actor_id_hash=document["actor_id_hash"],
            evidence_hash=document["evidence_hash"],
            target_receipt_schema_version=document[
                "target_receipt_schema_version"
            ],
            request_hash=document["request_hash"],
        )


@dataclass(frozen=True, slots=True)
class AntiReplayCompareAndConsumeResultV2:
    outcome: AntiReplayRegistryOutcomeV1
    anti_replay_namespace: str
    namespace_preregistration_hash: str
    request_hash: str
    consumption_key: str
    target_receipt_schema_version: str
    registry_id: str
    registry_revision: int
    receipt_document: Mapping[str, Any] | None = None
    schema_version: str = RESULT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != RESULT_SCHEMA_VERSION:
            raise ValueError("result schema version must match v2")
        if not isinstance(self.outcome, AntiReplayRegistryOutcomeV1):
            raise ValueError("outcome must be an AntiReplayRegistryOutcomeV1")
        _require_nonempty(
            "anti_replay_namespace", self.anti_replay_namespace, maximum=160
        )
        _require_nonempty("registry_id", self.registry_id, maximum=256)
        _require_nonempty(
            "target_receipt_schema_version",
            self.target_receipt_schema_version,
            maximum=160,
        )
        for name in (
            "namespace_preregistration_hash",
            "request_hash",
            "consumption_key",
        ):
            _require_hash(name, getattr(self, name))
        if (
            isinstance(self.registry_revision, bool)
            or not isinstance(self.registry_revision, int)
            or self.registry_revision < 0
        ):
            raise ValueError("registry_revision must be a non-negative integer")

        if self.outcome is AntiReplayRegistryOutcomeV1.CONSUMED:
            if not isinstance(self.receipt_document, Mapping):
                raise ValueError("CONSUMED requires a receipt document")
            required = {
                "schema_version": self.target_receipt_schema_version,
                "anti_replay_namespace": self.anti_replay_namespace,
                "namespace_preregistration_hash": self.namespace_preregistration_hash,
                "request_hash": self.request_hash,
                "consumption_key": self.consumption_key,
            }
            if any(
                self.receipt_document.get(name) != expected
                for name, expected in required.items()
            ):
                raise ValueError("receipt document does not bind the v2 result")
            frozen_receipt = MappingProxyType(deepcopy(dict(self.receipt_document)))
            object.__setattr__(self, "receipt_document", frozen_receipt)
        elif self.receipt_document is not None:
            raise ValueError("rejected outcomes must not include a receipt document")


@runtime_checkable
class AntiReplayRegistryPortV2(Protocol):
    def compare_and_consume(
        self, command: AntiReplayCompareAndConsumeCommandV2
    ) -> AntiReplayCompareAndConsumeResultV2:
        ...
