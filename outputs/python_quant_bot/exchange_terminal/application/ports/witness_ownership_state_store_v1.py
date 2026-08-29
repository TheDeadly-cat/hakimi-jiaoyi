"""Atomic witness-ownership state provider port for ADR0412.

The port deliberately combines claim consumption and state advancement in one
operation.  Splitting those actions across two providers would create a crash
window in which a claim is consumed without advancing the ownership state.

This module contains contracts only.  It does not implement storage, locks,
network I/O, provider identity, receipt signatures, durability, linearizable
reads, rollback resistance, runtime mounting, or trading authority.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
import re
from types import MappingProxyType
from typing import Any, Mapping, Protocol, runtime_checkable

from exchange_terminal.application.ports.anti_replay_registry_v2 import (
    build_anti_replay_consumption_key_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


WITNESS_OWNERSHIP_NAMESPACE = (
    "strategy-correlation-cluster-witness-ownership-state-v1"
)
COMMAND_SCHEMA_VERSION = (
    "witness-ownership-state-compare-consume-and-advance-command-v1"
)
RESULT_SCHEMA_VERSION = (
    "witness-ownership-state-compare-consume-and-advance-result-v1"
)
RECEIPT_CLAIM_SCHEMA_VERSION = (
    "witness-ownership-state-provider-receipt-claim-v1"
)
STATIC_FINGERPRINT = (
    "20260824-witness-ownership-atomic-state-provider-port-v1-lock-1"
)

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _require_hash(name: str, value: Any) -> str:
    if type(value) is not str or _HASH_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")
    return value


def _require_token(name: str, value: Any, *, maximum: int = 160) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(f"{name} must be a normalized non-empty string")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds its length bound")
    try:
        value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{name} must be ASCII") from exc
    return value


def _require_revision(name: str, value: Any) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _command_body(
    *,
    namespace_preregistration_hash: str,
    ownership_claim_hash: str,
    ownership_evidence_hash: str,
    expected_state_hash: str,
    proposed_state_hash: str,
    expected_registry_revision: int,
    request_nonce_hash: str,
    consumption_key: str,
) -> dict[str, Any]:
    return {
        "schema_version": COMMAND_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "namespace": WITNESS_OWNERSHIP_NAMESPACE,
        "namespace_preregistration_hash": namespace_preregistration_hash,
        "ownership_claim_hash": ownership_claim_hash,
        "ownership_evidence_hash": ownership_evidence_hash,
        "expected_state_hash": expected_state_hash,
        "proposed_state_hash": proposed_state_hash,
        "expected_registry_revision": expected_registry_revision,
        "request_nonce_hash": request_nonce_hash,
        "consumption_key": consumption_key,
    }


def build_witness_ownership_consumption_key_v1(
    *,
    namespace_preregistration_hash: Any,
    ownership_claim_hash: Any,
) -> str:
    preregistration_hash = _require_hash(
        "namespace_preregistration_hash", namespace_preregistration_hash
    )
    claim_hash = _require_hash("ownership_claim_hash", ownership_claim_hash)
    scope_hash = strict_canonical_hash(
        {
            "namespace_preregistration_hash": preregistration_hash,
            "ownership_claim_hash": claim_hash,
        }
    )
    return build_anti_replay_consumption_key_v2(
        anti_replay_namespace=WITNESS_OWNERSHIP_NAMESPACE,
        anti_replay_scope_hash=scope_hash,
    )


@dataclass(frozen=True, slots=True)
class WitnessOwnershipCompareConsumeAndAdvanceCommandV1:
    namespace_preregistration_hash: str
    ownership_claim_hash: str
    ownership_evidence_hash: str
    expected_state_hash: str
    proposed_state_hash: str
    expected_registry_revision: int
    request_nonce_hash: str
    consumption_key: str
    command_hash: str
    namespace: str = WITNESS_OWNERSHIP_NAMESPACE
    schema_version: str = COMMAND_SCHEMA_VERSION
    static_fingerprint: str = STATIC_FINGERPRINT

    def __post_init__(self) -> None:
        if self.namespace != WITNESS_OWNERSHIP_NAMESPACE:
            raise ValueError("witness ownership namespace alias is forbidden")
        if self.schema_version != COMMAND_SCHEMA_VERSION:
            raise ValueError("command schema alias is forbidden")
        if self.static_fingerprint != STATIC_FINGERPRINT:
            raise ValueError("command static fingerprint drifted")
        for name in (
            "namespace_preregistration_hash",
            "ownership_claim_hash",
            "ownership_evidence_hash",
            "expected_state_hash",
            "proposed_state_hash",
            "request_nonce_hash",
            "consumption_key",
            "command_hash",
        ):
            _require_hash(name, getattr(self, name))
        _require_revision(
            "expected_registry_revision", self.expected_registry_revision
        )
        if self.expected_state_hash == self.proposed_state_hash:
            raise ValueError("proposed ownership state must advance")
        expected_key = build_witness_ownership_consumption_key_v1(
            namespace_preregistration_hash=(
                self.namespace_preregistration_hash
            ),
            ownership_claim_hash=self.ownership_claim_hash,
        )
        if self.consumption_key != expected_key:
            raise ValueError("consumption key does not bind claim and namespace")
        body = _command_body(
            namespace_preregistration_hash=(
                self.namespace_preregistration_hash
            ),
            ownership_claim_hash=self.ownership_claim_hash,
            ownership_evidence_hash=self.ownership_evidence_hash,
            expected_state_hash=self.expected_state_hash,
            proposed_state_hash=self.proposed_state_hash,
            expected_registry_revision=self.expected_registry_revision,
            request_nonce_hash=self.request_nonce_hash,
            consumption_key=self.consumption_key,
        )
        if self.command_hash != strict_canonical_hash(body):
            raise ValueError("command hash does not verify")


def build_witness_ownership_compare_consume_and_advance_command_v1(
    *,
    namespace_preregistration_hash: Any,
    ownership_claim_hash: Any,
    ownership_evidence_hash: Any,
    expected_state_hash: Any,
    proposed_state_hash: Any,
    expected_registry_revision: Any,
    request_nonce_hash: Any,
) -> WitnessOwnershipCompareConsumeAndAdvanceCommandV1:
    preregistration_hash = _require_hash(
        "namespace_preregistration_hash", namespace_preregistration_hash
    )
    claim_hash = _require_hash("ownership_claim_hash", ownership_claim_hash)
    evidence_hash = _require_hash(
        "ownership_evidence_hash", ownership_evidence_hash
    )
    base_hash = _require_hash("expected_state_hash", expected_state_hash)
    next_hash = _require_hash("proposed_state_hash", proposed_state_hash)
    revision = _require_revision(
        "expected_registry_revision", expected_registry_revision
    )
    nonce_hash = _require_hash("request_nonce_hash", request_nonce_hash)
    consumption_key = build_witness_ownership_consumption_key_v1(
        namespace_preregistration_hash=preregistration_hash,
        ownership_claim_hash=claim_hash,
    )
    body = _command_body(
        namespace_preregistration_hash=preregistration_hash,
        ownership_claim_hash=claim_hash,
        ownership_evidence_hash=evidence_hash,
        expected_state_hash=base_hash,
        proposed_state_hash=next_hash,
        expected_registry_revision=revision,
        request_nonce_hash=nonce_hash,
        consumption_key=consumption_key,
    )
    return WitnessOwnershipCompareConsumeAndAdvanceCommandV1(
        namespace_preregistration_hash=preregistration_hash,
        ownership_claim_hash=claim_hash,
        ownership_evidence_hash=evidence_hash,
        expected_state_hash=base_hash,
        proposed_state_hash=next_hash,
        expected_registry_revision=revision,
        request_nonce_hash=nonce_hash,
        consumption_key=consumption_key,
        command_hash=strict_canonical_hash(body),
    )


class WitnessOwnershipProviderOutcomeV1(str, Enum):
    ADVANCED = "ADVANCED"
    DUPLICATE_REJECTED = "DUPLICATE_REJECTED"
    CONFLICT_REJECTED = "CONFLICT_REJECTED"


def build_witness_ownership_state_provider_receipt_claim_v1(
    command: WitnessOwnershipCompareConsumeAndAdvanceCommandV1,
    *,
    registry_id: Any,
    observed_registry_revision: Any,
    returned_registry_revision: Any,
    observed_state_hash: Any,
    returned_state_hash: Any,
) -> dict[str, Any]:
    if type(command) is not WitnessOwnershipCompareConsumeAndAdvanceCommandV1:
        raise ValueError("receipt claim requires an exact ownership command")
    registry = _require_token("registry_id", registry_id, maximum=128)
    observed_revision = _require_revision(
        "observed_registry_revision", observed_registry_revision
    )
    returned_revision = _require_revision(
        "returned_registry_revision", returned_registry_revision
    )
    observed_hash = _require_hash("observed_state_hash", observed_state_hash)
    returned_hash = _require_hash("returned_state_hash", returned_state_hash)
    if (
        observed_revision != command.expected_registry_revision
        or returned_revision != observed_revision + 1
        or observed_hash != command.expected_state_hash
        or returned_hash != command.proposed_state_hash
    ):
        raise ValueError("ADVANCED receipt claim does not bind the exact CAS")
    body = {
        "schema_version": RECEIPT_CLAIM_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "namespace": WITNESS_OWNERSHIP_NAMESPACE,
        "namespace_preregistration_hash": (
            command.namespace_preregistration_hash
        ),
        "registry_id": registry,
        "command_hash": command.command_hash,
        "consumption_key": command.consumption_key,
        "ownership_claim_hash": command.ownership_claim_hash,
        "ownership_evidence_hash": command.ownership_evidence_hash,
        "observed_registry_revision": observed_revision,
        "returned_registry_revision": returned_revision,
        "observed_state_hash": observed_hash,
        "returned_state_hash": returned_hash,
        "outcome": WitnessOwnershipProviderOutcomeV1.ADVANCED.value,
        "provider_claims": {
            "atomic_compare_consume_and_advance_claimed": True,
            "durable_commit_claimed": True,
            "linearizable_read_after_write_claimed": True,
            "rollback_resistance_claimed": True,
        },
        "verification_limits": {
            "claims_independently_verified": False,
            "provider_identity_verified": False,
            "receipt_signature_verified": False,
        },
    }
    return seal_strict_canonical_document(body, "receipt_claim_hash")


@dataclass(frozen=True, slots=True)
class WitnessOwnershipCompareConsumeAndAdvanceResultV1:
    outcome: WitnessOwnershipProviderOutcomeV1
    command_hash: str
    consumption_key: str
    registry_id: str
    observed_registry_revision: int
    returned_registry_revision: int
    observed_state_hash: str
    returned_state_hash: str
    receipt_document: Mapping[str, Any] | None = None
    schema_version: str = RESULT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if type(self.outcome) is not WitnessOwnershipProviderOutcomeV1:
            raise ValueError("result outcome must be an exact v1 enum")
        if self.schema_version != RESULT_SCHEMA_VERSION:
            raise ValueError("result schema alias is forbidden")
        for name in (
            "command_hash",
            "consumption_key",
            "observed_state_hash",
            "returned_state_hash",
        ):
            _require_hash(name, getattr(self, name))
        _require_token("registry_id", self.registry_id, maximum=128)
        _require_revision(
            "observed_registry_revision", self.observed_registry_revision
        )
        _require_revision(
            "returned_registry_revision", self.returned_registry_revision
        )
        if self.outcome is WitnessOwnershipProviderOutcomeV1.ADVANCED:
            if (
                self.returned_registry_revision
                != self.observed_registry_revision + 1
                or self.returned_state_hash == self.observed_state_hash
                or not isinstance(self.receipt_document, Mapping)
            ):
                raise ValueError("ADVANCED result transition is invalid")
            object.__setattr__(
                self,
                "receipt_document",
                MappingProxyType(deepcopy(dict(self.receipt_document))),
            )
        elif (
            self.returned_registry_revision != self.observed_registry_revision
            or self.returned_state_hash != self.observed_state_hash
            or self.receipt_document is not None
        ):
            raise ValueError("rejected result must leave provider state unchanged")


def build_witness_ownership_compare_consume_and_advance_result_v1(
    command: WitnessOwnershipCompareConsumeAndAdvanceCommandV1,
    *,
    outcome: WitnessOwnershipProviderOutcomeV1,
    registry_id: Any,
    observed_registry_revision: Any,
    observed_state_hash: Any,
) -> WitnessOwnershipCompareConsumeAndAdvanceResultV1:
    if type(command) is not WitnessOwnershipCompareConsumeAndAdvanceCommandV1:
        raise ValueError("result builder requires an exact ownership command")
    if type(outcome) is not WitnessOwnershipProviderOutcomeV1:
        raise ValueError("outcome must be an exact v1 enum")
    registry = _require_token("registry_id", registry_id, maximum=128)
    observed_revision = _require_revision(
        "observed_registry_revision", observed_registry_revision
    )
    observed_hash = _require_hash("observed_state_hash", observed_state_hash)
    if outcome is WitnessOwnershipProviderOutcomeV1.ADVANCED:
        if (
            observed_revision != command.expected_registry_revision
            or observed_hash != command.expected_state_hash
        ):
            raise ValueError("ADVANCED result must match command CAS baseline")
        returned_revision = observed_revision + 1
        returned_hash = command.proposed_state_hash
        receipt = build_witness_ownership_state_provider_receipt_claim_v1(
            command,
            registry_id=registry,
            observed_registry_revision=observed_revision,
            returned_registry_revision=returned_revision,
            observed_state_hash=observed_hash,
            returned_state_hash=returned_hash,
        )
    else:
        returned_revision = observed_revision
        returned_hash = observed_hash
        receipt = None
    return WitnessOwnershipCompareConsumeAndAdvanceResultV1(
        outcome=outcome,
        command_hash=command.command_hash,
        consumption_key=command.consumption_key,
        registry_id=registry,
        observed_registry_revision=observed_revision,
        returned_registry_revision=returned_revision,
        observed_state_hash=observed_hash,
        returned_state_hash=returned_hash,
        receipt_document=receipt,
    )


def verify_witness_ownership_compare_consume_and_advance_result_v1(
    result: Any,
    command: Any,
    *,
    expected_registry_id: Any,
) -> bool:
    if (
        type(result) is not WitnessOwnershipCompareConsumeAndAdvanceResultV1
        or type(command) is not WitnessOwnershipCompareConsumeAndAdvanceCommandV1
    ):
        return False
    try:
        registry = _require_token(
            "expected_registry_id", expected_registry_id, maximum=128
        )
        rebuilt = build_witness_ownership_compare_consume_and_advance_result_v1(
            command,
            outcome=result.outcome,
            registry_id=result.registry_id,
            observed_registry_revision=result.observed_registry_revision,
            observed_state_hash=result.observed_state_hash,
        )
    except (TypeError, ValueError):
        return False
    if (
        result.registry_id != registry
        or result.command_hash != command.command_hash
        or result.consumption_key != command.consumption_key
        or result != rebuilt
    ):
        return False
    if result.outcome is WitnessOwnershipProviderOutcomeV1.ADVANCED:
        return (
            result.observed_registry_revision
            == command.expected_registry_revision
            and result.returned_registry_revision
            == command.expected_registry_revision + 1
            and result.observed_state_hash == command.expected_state_hash
            and result.returned_state_hash == command.proposed_state_hash
            and isinstance(result.receipt_document, Mapping)
            and strict_json_contract_equal(
                dict(result.receipt_document),
                build_witness_ownership_state_provider_receipt_claim_v1(
                    command,
                    registry_id=result.registry_id,
                    observed_registry_revision=(
                        result.observed_registry_revision
                    ),
                    returned_registry_revision=(
                        result.returned_registry_revision
                    ),
                    observed_state_hash=result.observed_state_hash,
                    returned_state_hash=result.returned_state_hash,
                ),
            )
        )
    return True


@runtime_checkable
class WitnessOwnershipStateProviderPortV1(Protocol):
    @property
    def registry_id(self) -> str:
        ...

    def compare_consume_and_advance(
        self,
        command: WitnessOwnershipCompareConsumeAndAdvanceCommandV1,
    ) -> WitnessOwnershipCompareConsumeAndAdvanceResultV1:
        ...


__all__ = [
    "COMMAND_SCHEMA_VERSION",
    "RECEIPT_CLAIM_SCHEMA_VERSION",
    "RESULT_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "WITNESS_OWNERSHIP_NAMESPACE",
    "WitnessOwnershipCompareConsumeAndAdvanceCommandV1",
    "WitnessOwnershipCompareConsumeAndAdvanceResultV1",
    "WitnessOwnershipProviderOutcomeV1",
    "WitnessOwnershipStateProviderPortV1",
    "build_witness_ownership_compare_consume_and_advance_command_v1",
    "build_witness_ownership_compare_consume_and_advance_result_v1",
    "build_witness_ownership_consumption_key_v1",
    "build_witness_ownership_state_provider_receipt_claim_v1",
    "verify_witness_ownership_compare_consume_and_advance_result_v1",
]
