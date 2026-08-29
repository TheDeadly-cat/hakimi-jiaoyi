"""Consumer-first port for one-time replay-cursor registration challenges.

The production module defines exact immutable messages and a Protocol only. It
contains no provider implementation, lock, registry, persistence, or runtime
mount. External atomicity, durability, linearizability, and authority must be
proved by later independently versioned contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
import re
from typing import Any, Protocol, runtime_checkable


CHALLENGE_CONSUMPTION_NAMESPACE = (
    "strategy-correlation-incumbent-snapshot-replay-cursor-provider-registration-challenge-v1"
)
CONSUME_ONCE_COMMAND_SCHEMA_VERSION = (
    "incumbent-snapshot-replay-cursor-provider-registration-challenge-consume-once-command-v1"
)
CONSUME_ONCE_RESULT_SCHEMA_VERSION = (
    "incumbent-snapshot-replay-cursor-provider-registration-challenge-consume-once-result-v1"
)
STATIC_FINGERPRINT = (
    "20260824-replay-cursor-provider-registration-challenge-consumption-port-v1-lock-1"
)

_HASH = re.compile(r"^[0-9a-f]{64}$")


def _require_hash(value: Any, label: str) -> str:
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise ValueError(f"{label} must be lowercase sha256")
    return value


def _require_revision(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _hash_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return sha256(encoded).hexdigest()


def _command_payload(
    *,
    signed_challenge_hash: str,
    challenge_clock_binding_evidence_hash: str,
    registration_nonce_hash: str,
    expected_registry_head_hash: str,
    expected_provider_revision: int,
    request_id_hash: str,
    registry_namespace: str = CHALLENGE_CONSUMPTION_NAMESPACE,
    schema_version: str = CONSUME_ONCE_COMMAND_SCHEMA_VERSION,
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "static_fingerprint": STATIC_FINGERPRINT,
        "registry_namespace": registry_namespace,
        "signed_challenge_hash": signed_challenge_hash,
        "challenge_clock_binding_evidence_hash": (
            challenge_clock_binding_evidence_hash
        ),
        "registration_nonce_hash": registration_nonce_hash,
        "expected_registry_head_hash": expected_registry_head_hash,
        "expected_provider_revision": expected_provider_revision,
        "request_id_hash": request_id_hash,
    }


@dataclass(frozen=True, slots=True)
class ReplayCursorProviderRegistrationChallengeConsumeOnceCommandV1:
    signed_challenge_hash: str
    challenge_clock_binding_evidence_hash: str
    registration_nonce_hash: str
    expected_registry_head_hash: str
    expected_provider_revision: int
    request_id_hash: str
    command_hash: str
    registry_namespace: str = CHALLENGE_CONSUMPTION_NAMESPACE
    schema_version: str = CONSUME_ONCE_COMMAND_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for label in (
            "signed_challenge_hash",
            "challenge_clock_binding_evidence_hash",
            "registration_nonce_hash",
            "expected_registry_head_hash",
            "request_id_hash",
            "command_hash",
        ):
            _require_hash(getattr(self, label), label)
        _require_revision(self.expected_provider_revision, "expected_provider_revision")
        if self.registry_namespace != CHALLENGE_CONSUMPTION_NAMESPACE:
            raise ValueError("challenge-consumption namespace alias is forbidden")
        if self.schema_version != CONSUME_ONCE_COMMAND_SCHEMA_VERSION:
            raise ValueError("consume-once command schema alias is forbidden")
        bound_hashes = {
            self.signed_challenge_hash,
            self.challenge_clock_binding_evidence_hash,
            self.registration_nonce_hash,
            self.request_id_hash,
        }
        if len(bound_hashes) != 4:
            raise ValueError("challenge command role hashes must be distinct")
        expected = _hash_payload(
            _command_payload(
                signed_challenge_hash=self.signed_challenge_hash,
                challenge_clock_binding_evidence_hash=(
                    self.challenge_clock_binding_evidence_hash
                ),
                registration_nonce_hash=self.registration_nonce_hash,
                expected_registry_head_hash=self.expected_registry_head_hash,
                expected_provider_revision=self.expected_provider_revision,
                request_id_hash=self.request_id_hash,
                registry_namespace=self.registry_namespace,
                schema_version=self.schema_version,
            )
        )
        if self.command_hash != expected:
            raise ValueError("consume-once command hash does not verify")


def build_replay_cursor_provider_registration_challenge_consume_once_command_v1(
    *,
    signed_challenge_hash: Any,
    challenge_clock_binding_evidence_hash: Any,
    registration_nonce_hash: Any,
    expected_registry_head_hash: Any,
    expected_provider_revision: Any,
    request_id_hash: Any,
) -> ReplayCursorProviderRegistrationChallengeConsumeOnceCommandV1:
    payload = _command_payload(
        signed_challenge_hash=_require_hash(
            signed_challenge_hash, "signed_challenge_hash"
        ),
        challenge_clock_binding_evidence_hash=_require_hash(
            challenge_clock_binding_evidence_hash,
            "challenge_clock_binding_evidence_hash",
        ),
        registration_nonce_hash=_require_hash(
            registration_nonce_hash, "registration_nonce_hash"
        ),
        expected_registry_head_hash=_require_hash(
            expected_registry_head_hash, "expected_registry_head_hash"
        ),
        expected_provider_revision=_require_revision(
            expected_provider_revision, "expected_provider_revision"
        ),
        request_id_hash=_require_hash(request_id_hash, "request_id_hash"),
    )
    return ReplayCursorProviderRegistrationChallengeConsumeOnceCommandV1(
        signed_challenge_hash=payload["signed_challenge_hash"],
        challenge_clock_binding_evidence_hash=payload[
            "challenge_clock_binding_evidence_hash"
        ],
        registration_nonce_hash=payload["registration_nonce_hash"],
        expected_registry_head_hash=payload["expected_registry_head_hash"],
        expected_provider_revision=payload["expected_provider_revision"],
        request_id_hash=payload["request_id_hash"],
        command_hash=_hash_payload(payload),
    )


def verify_replay_cursor_provider_registration_challenge_consume_once_command_v1(
    command: Any,
    *,
    expected_command_hash: Any,
) -> bool:
    try:
        if type(command) is not ReplayCursorProviderRegistrationChallengeConsumeOnceCommandV1:
            return False
        rebuilt = build_replay_cursor_provider_registration_challenge_consume_once_command_v1(
            signed_challenge_hash=command.signed_challenge_hash,
            challenge_clock_binding_evidence_hash=(
                command.challenge_clock_binding_evidence_hash
            ),
            registration_nonce_hash=command.registration_nonce_hash,
            expected_registry_head_hash=command.expected_registry_head_hash,
            expected_provider_revision=command.expected_provider_revision,
            request_id_hash=command.request_id_hash,
        )
        return (
            command == rebuilt
            and _require_hash(expected_command_hash, "expected_command_hash")
            == rebuilt.command_hash
        )
    except (TypeError, ValueError):
        return False


class ChallengeConsumptionProviderOutcomeV1(str, Enum):
    CONSUMED = "CONSUMED"
    ALREADY_CONSUMED = "ALREADY_CONSUMED"
    COMPARE_AND_SWAP_CONFLICT = "COMPARE_AND_SWAP_CONFLICT"
    BLOCKED = "BLOCKED"


def derive_consumed_registry_head_v1(
    command: ReplayCursorProviderRegistrationChallengeConsumeOnceCommandV1,
) -> str:
    if not verify_replay_cursor_provider_registration_challenge_consume_once_command_v1(
        command, expected_command_hash=command.command_hash
    ):
        raise ValueError("command must be exact")
    return _hash_payload(
        {
            "schema_version": "challenge-consumption-registry-head-transition-v1",
            "registry_namespace": command.registry_namespace,
            "previous_registry_head_hash": command.expected_registry_head_hash,
            "previous_provider_revision": command.expected_provider_revision,
            "returned_provider_revision": command.expected_provider_revision + 1,
            "command_hash": command.command_hash,
            "signed_challenge_hash": command.signed_challenge_hash,
            "challenge_clock_binding_evidence_hash": (
                command.challenge_clock_binding_evidence_hash
            ),
        }
    )


def derive_challenge_consumption_receipt_hash_v1(
    command: ReplayCursorProviderRegistrationChallengeConsumeOnceCommandV1,
    *,
    returned_registry_head_hash: Any,
) -> str:
    returned = _require_hash(
        returned_registry_head_hash, "returned_registry_head_hash"
    )
    if returned != derive_consumed_registry_head_v1(command):
        raise ValueError("returned registry head is not the exact consumed transition")
    return _hash_payload(
        {
            "schema_version": "challenge-consumption-structural-receipt-v1",
            "command_hash": command.command_hash,
            "signed_challenge_hash": command.signed_challenge_hash,
            "returned_registry_head_hash": returned,
            "returned_provider_revision": command.expected_provider_revision + 1,
        }
    )


def _result_payload(
    *,
    outcome: ChallengeConsumptionProviderOutcomeV1,
    command_hash: str,
    signed_challenge_hash: str,
    observed_registry_head_hash: str,
    returned_registry_head_hash: str,
    observed_provider_revision: int,
    returned_provider_revision: int,
    consumption_receipt_hash: str | None,
    duplicate_consumption_receipt_hash: str | None,
    schema_version: str = CONSUME_ONCE_RESULT_SCHEMA_VERSION,
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "static_fingerprint": STATIC_FINGERPRINT,
        "outcome": outcome.value,
        "command_hash": command_hash,
        "signed_challenge_hash": signed_challenge_hash,
        "observed_registry_head_hash": observed_registry_head_hash,
        "returned_registry_head_hash": returned_registry_head_hash,
        "observed_provider_revision": observed_provider_revision,
        "returned_provider_revision": returned_provider_revision,
        "consumption_receipt_hash": consumption_receipt_hash,
        "duplicate_consumption_receipt_hash": duplicate_consumption_receipt_hash,
    }


@dataclass(frozen=True, slots=True)
class ReplayCursorProviderRegistrationChallengeConsumeOnceResultV1:
    outcome: ChallengeConsumptionProviderOutcomeV1
    command_hash: str
    signed_challenge_hash: str
    observed_registry_head_hash: str
    returned_registry_head_hash: str
    observed_provider_revision: int
    returned_provider_revision: int
    consumption_receipt_hash: str | None
    duplicate_consumption_receipt_hash: str | None
    result_hash: str
    schema_version: str = CONSUME_ONCE_RESULT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if type(self.outcome) is not ChallengeConsumptionProviderOutcomeV1:
            raise ValueError("outcome must be the exact v1 enum")
        for label in (
            "command_hash",
            "signed_challenge_hash",
            "observed_registry_head_hash",
            "returned_registry_head_hash",
            "result_hash",
        ):
            _require_hash(getattr(self, label), label)
        _require_revision(self.observed_provider_revision, "observed_provider_revision")
        _require_revision(self.returned_provider_revision, "returned_provider_revision")
        if self.consumption_receipt_hash is not None:
            _require_hash(self.consumption_receipt_hash, "consumption_receipt_hash")
        if self.duplicate_consumption_receipt_hash is not None:
            _require_hash(
                self.duplicate_consumption_receipt_hash,
                "duplicate_consumption_receipt_hash",
            )
        if self.schema_version != CONSUME_ONCE_RESULT_SCHEMA_VERSION:
            raise ValueError("consume-once result schema alias is forbidden")
        expected = _hash_payload(
            _result_payload(
                outcome=self.outcome,
                command_hash=self.command_hash,
                signed_challenge_hash=self.signed_challenge_hash,
                observed_registry_head_hash=self.observed_registry_head_hash,
                returned_registry_head_hash=self.returned_registry_head_hash,
                observed_provider_revision=self.observed_provider_revision,
                returned_provider_revision=self.returned_provider_revision,
                consumption_receipt_hash=self.consumption_receipt_hash,
                duplicate_consumption_receipt_hash=(
                    self.duplicate_consumption_receipt_hash
                ),
                schema_version=self.schema_version,
            )
        )
        if self.result_hash != expected:
            raise ValueError("consume-once result hash does not verify")


def build_replay_cursor_provider_registration_challenge_consume_once_result_v1(
    command: Any,
    *,
    outcome: Any,
    observed_registry_head_hash: Any,
    observed_provider_revision: Any,
    duplicate_consumption_receipt_hash: Any = None,
) -> ReplayCursorProviderRegistrationChallengeConsumeOnceResultV1:
    if not verify_replay_cursor_provider_registration_challenge_consume_once_command_v1(
        command, expected_command_hash=getattr(command, "command_hash", None)
    ):
        raise ValueError("command must be exact")
    if type(outcome) is not ChallengeConsumptionProviderOutcomeV1:
        raise ValueError("outcome must be the exact v1 enum")
    observed_head = _require_hash(
        observed_registry_head_hash, "observed_registry_head_hash"
    )
    observed_revision = _require_revision(
        observed_provider_revision, "observed_provider_revision"
    )
    returned_head = observed_head
    returned_revision = observed_revision
    consumption_receipt = None
    duplicate_receipt = None

    if outcome is ChallengeConsumptionProviderOutcomeV1.CONSUMED:
        if (
            observed_head != command.expected_registry_head_hash
            or observed_revision != command.expected_provider_revision
            or duplicate_consumption_receipt_hash is not None
        ):
            raise ValueError("consumed outcome does not match expected registry state")
        returned_head = derive_consumed_registry_head_v1(command)
        returned_revision = observed_revision + 1
        consumption_receipt = derive_challenge_consumption_receipt_hash_v1(
            command, returned_registry_head_hash=returned_head
        )
    elif outcome is ChallengeConsumptionProviderOutcomeV1.ALREADY_CONSUMED:
        duplicate_receipt = _require_hash(
            duplicate_consumption_receipt_hash,
            "duplicate_consumption_receipt_hash",
        )
    elif outcome is ChallengeConsumptionProviderOutcomeV1.COMPARE_AND_SWAP_CONFLICT:
        if (
            observed_head == command.expected_registry_head_hash
            and observed_revision == command.expected_provider_revision
        ):
            raise ValueError("conflict outcome requires observed state drift")
        if duplicate_consumption_receipt_hash is not None:
            raise ValueError("conflict outcome cannot carry a duplicate receipt")
    elif outcome is ChallengeConsumptionProviderOutcomeV1.BLOCKED:
        if duplicate_consumption_receipt_hash is not None:
            raise ValueError("blocked outcome cannot carry a duplicate receipt")

    payload = _result_payload(
        outcome=outcome,
        command_hash=command.command_hash,
        signed_challenge_hash=command.signed_challenge_hash,
        observed_registry_head_hash=observed_head,
        returned_registry_head_hash=returned_head,
        observed_provider_revision=observed_revision,
        returned_provider_revision=returned_revision,
        consumption_receipt_hash=consumption_receipt,
        duplicate_consumption_receipt_hash=duplicate_receipt,
    )
    return ReplayCursorProviderRegistrationChallengeConsumeOnceResultV1(
        outcome=outcome,
        command_hash=command.command_hash,
        signed_challenge_hash=command.signed_challenge_hash,
        observed_registry_head_hash=observed_head,
        returned_registry_head_hash=returned_head,
        observed_provider_revision=observed_revision,
        returned_provider_revision=returned_revision,
        consumption_receipt_hash=consumption_receipt,
        duplicate_consumption_receipt_hash=duplicate_receipt,
        result_hash=_hash_payload(payload),
    )


def verify_replay_cursor_provider_registration_challenge_consume_once_result_v1(
    result: Any,
    command: Any,
    *,
    expected_result_hash: Any,
) -> bool:
    try:
        if type(result) is not ReplayCursorProviderRegistrationChallengeConsumeOnceResultV1:
            return False
        rebuilt = build_replay_cursor_provider_registration_challenge_consume_once_result_v1(
            command,
            outcome=result.outcome,
            observed_registry_head_hash=result.observed_registry_head_hash,
            observed_provider_revision=result.observed_provider_revision,
            duplicate_consumption_receipt_hash=(
                result.duplicate_consumption_receipt_hash
            ),
        )
        return (
            result == rebuilt
            and _require_hash(expected_result_hash, "expected_result_hash")
            == rebuilt.result_hash
        )
    except (TypeError, ValueError):
        return False


@runtime_checkable
class ReplayCursorProviderRegistrationChallengeConsumptionPortV1(Protocol):
    def consume_once(
        self,
        command: ReplayCursorProviderRegistrationChallengeConsumeOnceCommandV1,
    ) -> ReplayCursorProviderRegistrationChallengeConsumeOnceResultV1: ...


__all__ = [
    "CHALLENGE_CONSUMPTION_NAMESPACE",
    "CONSUME_ONCE_COMMAND_SCHEMA_VERSION",
    "CONSUME_ONCE_RESULT_SCHEMA_VERSION",
    "ChallengeConsumptionProviderOutcomeV1",
    "ReplayCursorProviderRegistrationChallengeConsumeOnceCommandV1",
    "ReplayCursorProviderRegistrationChallengeConsumeOnceResultV1",
    "ReplayCursorProviderRegistrationChallengeConsumptionPortV1",
    "build_replay_cursor_provider_registration_challenge_consume_once_command_v1",
    "build_replay_cursor_provider_registration_challenge_consume_once_result_v1",
    "derive_challenge_consumption_receipt_hash_v1",
    "derive_consumed_registry_head_v1",
    "verify_replay_cursor_provider_registration_challenge_consume_once_command_v1",
    "verify_replay_cursor_provider_registration_challenge_consume_once_result_v1",
]
