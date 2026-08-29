"""Domain-specific provider port for an ADR0380 replay-cursor transition.

This module defines immutable boundary documents and a structural protocol. It
contains no provider implementation, registry, lock, storage, or runtime mount.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
import re
from types import MappingProxyType
from typing import Any, Mapping, Protocol, runtime_checkable

from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_freshness_replay_gate_v1 as replay_gate,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_cas_transition_v1 as cas,
)


COMPARE_AND_ADVANCE_COMMAND_SCHEMA_VERSION = (
    "incumbent-snapshot-replay-cursor-compare-and-advance-command-v1"
)
COMPARE_AND_ADVANCE_RESULT_SCHEMA_VERSION = (
    "incumbent-snapshot-replay-cursor-compare-and-advance-result-v1"
)

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _is_hash(value: Any) -> bool:
    return type(value) is str and _HASH_PATTERN.fullmatch(value) is not None


def _require_hash(name: str, value: Any) -> str:
    if not _is_hash(value):
        raise ValueError(f"{name} must be a lowercase sha256 hex digest")
    return value


def _require_token(name: str, value: Any, *, maximum: int = 160) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty normalized string")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds its length bound")
    try:
        value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{name} must be ASCII") from exc
    return value


def _hash_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return sha256(canonical).hexdigest()


def _cursor_payload(
    cursor: replay_gate.IncumbentSnapshotReplayCursorV1,
) -> dict[str, Any]:
    return {
        "cursor_version": cursor.cursor_version,
        "stream_id": cursor.stream_id,
        "projection_preregistration_hash": (
            cursor.projection_preregistration_hash
        ),
        "high_water_sequence": cursor.high_water_sequence,
        "high_water_attestation_hash": cursor.high_water_attestation_hash,
        "consumed_attestation_hashes": list(cursor.consumed_attestation_hashes),
        "cursor_hash": cursor.cursor_hash,
    }


def _is_exact_cursor(value: Any) -> bool:
    if type(value) is not replay_gate.IncumbentSnapshotReplayCursorV1:
        return False
    rebuilt = replay_gate.build_incumbent_snapshot_replay_cursor_v1(
        stream_id=value.stream_id,
        projection_preregistration_hash=value.projection_preregistration_hash,
        high_water_sequence=value.high_water_sequence,
        high_water_attestation_hash=value.high_water_attestation_hash,
        consumed_attestation_hashes=value.consumed_attestation_hashes,
    )
    return rebuilt == value


def _command_payload(
    *,
    stream_id: str,
    projection_preregistration_hash: str,
    intent_hash: str,
    freshness_result_fingerprint_sha256: str,
    candidate_attestation_hash: str,
    candidate_sequence: int,
    request_nonce_hash: str,
    transition_receipt_hash: str,
    base_cursor: replay_gate.IncumbentSnapshotReplayCursorV1,
    proposed_cursor: replay_gate.IncumbentSnapshotReplayCursorV1,
) -> dict[str, Any]:
    return {
        "schema_version": COMPARE_AND_ADVANCE_COMMAND_SCHEMA_VERSION,
        "stream_id": stream_id,
        "projection_preregistration_hash": projection_preregistration_hash,
        "intent_hash": intent_hash,
        "freshness_result_fingerprint_sha256": (
            freshness_result_fingerprint_sha256
        ),
        "candidate_attestation_hash": candidate_attestation_hash,
        "candidate_sequence": candidate_sequence,
        "request_nonce_hash": request_nonce_hash,
        "transition_receipt_hash": transition_receipt_hash,
        "base_cursor": _cursor_payload(base_cursor),
        "proposed_cursor": _cursor_payload(proposed_cursor),
    }


@dataclass(frozen=True, slots=True)
class ReplayCursorCompareAndAdvanceCommandV1:
    stream_id: str
    projection_preregistration_hash: str
    intent_hash: str
    freshness_result_fingerprint_sha256: str
    candidate_attestation_hash: str
    candidate_sequence: int
    request_nonce_hash: str
    transition_receipt_hash: str
    base_cursor: replay_gate.IncumbentSnapshotReplayCursorV1
    proposed_cursor: replay_gate.IncumbentSnapshotReplayCursorV1
    command_hash: str
    schema_version: str = COMPARE_AND_ADVANCE_COMMAND_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_token("stream_id", self.stream_id)
        for name in (
            "projection_preregistration_hash",
            "intent_hash",
            "freshness_result_fingerprint_sha256",
            "candidate_attestation_hash",
            "request_nonce_hash",
            "transition_receipt_hash",
            "command_hash",
        ):
            _require_hash(name, getattr(self, name))
        if (
            type(self.candidate_sequence) is not int
            or self.candidate_sequence < 0
        ):
            raise ValueError("candidate_sequence must be a non-negative integer")
        if self.schema_version != COMPARE_AND_ADVANCE_COMMAND_SCHEMA_VERSION:
            raise ValueError("compare-and-advance command schema alias is forbidden")
        if not _is_exact_cursor(self.base_cursor) or not _is_exact_cursor(
            self.proposed_cursor
        ):
            raise ValueError("command cursors must be exact replay-cursor-v1 values")
        if (
            self.stream_id != self.base_cursor.stream_id
            or self.stream_id != self.proposed_cursor.stream_id
            or self.projection_preregistration_hash
            != self.base_cursor.projection_preregistration_hash
            or self.projection_preregistration_hash
            != self.proposed_cursor.projection_preregistration_hash
        ):
            raise ValueError("command stream or projection binding drifted")
        if (
            self.candidate_sequence <= self.base_cursor.high_water_sequence
            or self.proposed_cursor.high_water_sequence
            != self.candidate_sequence
            or self.proposed_cursor.high_water_attestation_hash
            != self.candidate_attestation_hash
        ):
            raise ValueError("command cursor sequence transition is invalid")
        expected_consumed = tuple(
            sorted(
                set(self.base_cursor.consumed_attestation_hashes)
                | {self.candidate_attestation_hash}
            )
        )
        if self.proposed_cursor.consumed_attestation_hashes != expected_consumed:
            raise ValueError("proposed cursor consumed set is not the exact union")
        expected_hash = _hash_payload(
            _command_payload(
                stream_id=self.stream_id,
                projection_preregistration_hash=(
                    self.projection_preregistration_hash
                ),
                intent_hash=self.intent_hash,
                freshness_result_fingerprint_sha256=(
                    self.freshness_result_fingerprint_sha256
                ),
                candidate_attestation_hash=self.candidate_attestation_hash,
                candidate_sequence=self.candidate_sequence,
                request_nonce_hash=self.request_nonce_hash,
                transition_receipt_hash=self.transition_receipt_hash,
                base_cursor=self.base_cursor,
                proposed_cursor=self.proposed_cursor,
            )
        )
        if self.command_hash != expected_hash:
            raise ValueError("compare-and-advance command hash does not verify")


def build_replay_cursor_compare_and_advance_command_v1(
    base_cursor: replay_gate.IncumbentSnapshotReplayCursorV1,
    attestation: replay_gate.IncumbentSnapshotSequenceAttestationV1,
    freshness_result: replay_gate.IncumbentSnapshotFreshnessReplayResultV1,
    intent: cas.IncumbentSnapshotReplayCursorCasTransitionIntentV1,
    *,
    expected_intent_hash: Any,
    expected_freshness_result_fingerprint_sha256: Any,
    expected_attestation_hash: Any,
    expected_base_cursor_hash: Any,
    expected_stream_id: Any,
    expected_projection_preregistration_hash: Any,
) -> ReplayCursorCompareAndAdvanceCommandV1 | None:
    try:
        simulation = cas.simulate_incumbent_snapshot_replay_cursor_cas_transition_v1(
            base_cursor,
            base_cursor,
            attestation,
            freshness_result,
            intent,
            expected_intent_hash=expected_intent_hash,
            expected_freshness_result_fingerprint_sha256=(
                expected_freshness_result_fingerprint_sha256
            ),
            expected_attestation_hash=expected_attestation_hash,
            expected_base_cursor_hash=expected_base_cursor_hash,
            expected_observed_cursor_hash=expected_base_cursor_hash,
            expected_stream_id=expected_stream_id,
            expected_projection_preregistration_hash=(
                expected_projection_preregistration_hash
            ),
        )
    except (TypeError, ValueError):
        return None
    if simulation is None:
        return None
    receipt = simulation.receipt
    if (
        receipt.outcome != cas.OUTCOME_ADVANCED_IN_RETURNED_CURSOR
        or receipt.gate_status != cas.GATE_STATUS_UNKNOWN
        or receipt.returned_cursor_changed is not True
        or receipt.input_cursor_mutation_performed is not False
        or receipt.atomic_storage_commit_verified is not False
        or receipt.durable_commit_verified is not False
        or receipt.linearizable_read_verified is not False
        or receipt.permission is not False
    ):
        return None

    payload = _command_payload(
        stream_id=base_cursor.stream_id,
        projection_preregistration_hash=(
            base_cursor.projection_preregistration_hash
        ),
        intent_hash=intent.intent_hash,
        freshness_result_fingerprint_sha256=(
            intent.freshness_result_fingerprint_sha256
        ),
        candidate_attestation_hash=intent.candidate_attestation_hash,
        candidate_sequence=intent.candidate_sequence,
        request_nonce_hash=intent.request_nonce_hash,
        transition_receipt_hash=receipt.receipt_hash,
        base_cursor=base_cursor,
        proposed_cursor=simulation.returned_cursor,
    )
    try:
        return ReplayCursorCompareAndAdvanceCommandV1(
            stream_id=base_cursor.stream_id,
            projection_preregistration_hash=(
                base_cursor.projection_preregistration_hash
            ),
            intent_hash=intent.intent_hash,
            freshness_result_fingerprint_sha256=(
                intent.freshness_result_fingerprint_sha256
            ),
            candidate_attestation_hash=intent.candidate_attestation_hash,
            candidate_sequence=intent.candidate_sequence,
            request_nonce_hash=intent.request_nonce_hash,
            transition_receipt_hash=receipt.receipt_hash,
            base_cursor=base_cursor,
            proposed_cursor=simulation.returned_cursor,
            command_hash=_hash_payload(payload),
        )
    except (TypeError, ValueError):
        return None


class ReplayCursorProviderOutcomeV1(str, Enum):
    ADVANCED = "ADVANCED"
    DUPLICATE_REJECTED = "DUPLICATE_REJECTED"
    CONFLICT_REJECTED = "CONFLICT_REJECTED"


@dataclass(frozen=True, slots=True)
class ReplayCursorCompareAndAdvanceResultV1:
    outcome: ReplayCursorProviderOutcomeV1
    command_hash: str
    intent_hash: str
    registry_id: str
    registry_revision: int
    observed_cursor_hash: str
    returned_cursor_hash: str
    receipt_document: Mapping[str, Any] | None = None
    schema_version: str = COMPARE_AND_ADVANCE_RESULT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, ReplayCursorProviderOutcomeV1):
            raise ValueError("result outcome must be an exact provider enum value")
        for name in (
            "command_hash",
            "intent_hash",
            "observed_cursor_hash",
            "returned_cursor_hash",
        ):
            _require_hash(name, getattr(self, name))
        _require_token("registry_id", self.registry_id, maximum=128)
        if (
            type(self.registry_revision) is not int
            or self.registry_revision < 0
        ):
            raise ValueError("registry_revision must be a non-negative integer")
        if self.schema_version != COMPARE_AND_ADVANCE_RESULT_SCHEMA_VERSION:
            raise ValueError("compare-and-advance result schema alias is forbidden")
        if (
            self.outcome is ReplayCursorProviderOutcomeV1.ADVANCED
            and self.returned_cursor_hash == self.observed_cursor_hash
        ):
            raise ValueError("ADVANCED must return a different cursor hash")
        if (
            self.outcome is not ReplayCursorProviderOutcomeV1.ADVANCED
            and self.returned_cursor_hash != self.observed_cursor_hash
        ):
            raise ValueError("rejected outcomes must return the observed cursor")
        if self.receipt_document is not None:
            if not isinstance(self.receipt_document, Mapping):
                raise ValueError("receipt_document must be a mapping or None")
            object.__setattr__(
                self,
                "receipt_document",
                MappingProxyType(dict(self.receipt_document)),
            )


@runtime_checkable
class ReplayCursorProviderPortV1(Protocol):
    @property
    def registry_id(self) -> str:
        ...

    def compare_and_advance(
        self,
        command: ReplayCursorCompareAndAdvanceCommandV1,
    ) -> ReplayCursorCompareAndAdvanceResultV1:
        ...


__all__ = [
    "COMPARE_AND_ADVANCE_COMMAND_SCHEMA_VERSION",
    "COMPARE_AND_ADVANCE_RESULT_SCHEMA_VERSION",
    "ReplayCursorCompareAndAdvanceCommandV1",
    "ReplayCursorCompareAndAdvanceResultV1",
    "ReplayCursorProviderOutcomeV1",
    "ReplayCursorProviderPortV1",
    "build_replay_cursor_compare_and_advance_command_v1",
]
