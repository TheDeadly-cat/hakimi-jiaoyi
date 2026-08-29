"""Consumer-first port for one-time genesis-admission replay reservation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
import re
from typing import Any, Protocol, runtime_checkable


RESERVATION_NAMESPACE = (
    "strategy-correlation-challenge-consumption-provider-"
    "genesis-admission-replay-reservation-v1"
)
RESERVE_ONCE_COMMAND_SCHEMA_VERSION = (
    "challenge-consumption-provider-genesis-replay-reserve-once-command-v1"
)
RESERVE_ONCE_RESULT_SCHEMA_VERSION = (
    "challenge-consumption-provider-genesis-replay-reserve-once-result-v1"
)
STATIC_FINGERPRINT = (
    "20260824-challenge-consumption-provider-genesis-replay-"
    "reservation-port-v1-lock-1"
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
    genesis_admission_replay_key_hash: str,
    threshold_admission_evidence_hash: str,
    expected_registry_head_hash: str,
    expected_provider_revision: int,
    request_id_hash: str,
    registry_namespace: str = RESERVATION_NAMESPACE,
    schema_version: str = RESERVE_ONCE_COMMAND_SCHEMA_VERSION,
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "static_fingerprint": STATIC_FINGERPRINT,
        "registry_namespace": registry_namespace,
        "genesis_admission_replay_key_hash": (
            genesis_admission_replay_key_hash
        ),
        "threshold_admission_evidence_hash": (
            threshold_admission_evidence_hash
        ),
        "expected_registry_head_hash": expected_registry_head_hash,
        "expected_provider_revision": expected_provider_revision,
        "request_id_hash": request_id_hash,
    }


@dataclass(frozen=True, slots=True)
class GenesisAdmissionReplayReserveOnceCommandV1:
    schema_version: str
    static_fingerprint: str
    registry_namespace: str
    genesis_admission_replay_key_hash: str
    threshold_admission_evidence_hash: str
    expected_registry_head_hash: str
    expected_provider_revision: int
    request_id_hash: str
    command_hash: str

    def __post_init__(self) -> None:
        if self.schema_version != RESERVE_ONCE_COMMAND_SCHEMA_VERSION:
            raise ValueError("command schema alias is forbidden")
        if self.static_fingerprint != STATIC_FINGERPRINT:
            raise ValueError("command fingerprint alias is forbidden")
        if self.registry_namespace != RESERVATION_NAMESPACE:
            raise ValueError("reservation namespace alias is forbidden")
        payload = _command_payload(
            genesis_admission_replay_key_hash=_require_hash(
                self.genesis_admission_replay_key_hash,
                "genesis_admission_replay_key_hash",
            ),
            threshold_admission_evidence_hash=_require_hash(
                self.threshold_admission_evidence_hash,
                "threshold_admission_evidence_hash",
            ),
            expected_registry_head_hash=_require_hash(
                self.expected_registry_head_hash,
                "expected_registry_head_hash",
            ),
            expected_provider_revision=_require_revision(
                self.expected_provider_revision,
                "expected_provider_revision",
            ),
            request_id_hash=_require_hash(
                self.request_id_hash, "request_id_hash"
            ),
        )
        expected = _hash_payload(payload)
        if _require_hash(self.command_hash, "command_hash") != expected:
            raise ValueError("command_hash mismatch")


def build_genesis_admission_replay_reserve_once_command_v1(
    *,
    genesis_admission_replay_key_hash: Any,
    threshold_admission_evidence_hash: Any,
    expected_registry_head_hash: Any,
    expected_provider_revision: Any,
    request_id_hash: Any,
) -> GenesisAdmissionReplayReserveOnceCommandV1:
    payload = _command_payload(
        genesis_admission_replay_key_hash=_require_hash(
            genesis_admission_replay_key_hash,
            "genesis_admission_replay_key_hash",
        ),
        threshold_admission_evidence_hash=_require_hash(
            threshold_admission_evidence_hash,
            "threshold_admission_evidence_hash",
        ),
        expected_registry_head_hash=_require_hash(
            expected_registry_head_hash,
            "expected_registry_head_hash",
        ),
        expected_provider_revision=_require_revision(
            expected_provider_revision, "expected_provider_revision"
        ),
        request_id_hash=_require_hash(request_id_hash, "request_id_hash"),
    )
    return GenesisAdmissionReplayReserveOnceCommandV1(
        **payload, command_hash=_hash_payload(payload)
    )


class GenesisAdmissionReplayReservationOutcomeV1(Enum):
    RESERVED = "RESERVED"
    ALREADY_RESERVED = "ALREADY_RESERVED"
    COMPARE_AND_SWAP_CONFLICT = "COMPARE_AND_SWAP_CONFLICT"
    BLOCKED = "BLOCKED"


def _derived_returned_head(
    command: GenesisAdmissionReplayReserveOnceCommandV1,
    observed_registry_head_hash: str,
    observed_provider_revision: int,
) -> str:
    return _hash_payload(
        {
            "domain": "GENESIS_ADMISSION_REPLAY_RESERVATION_HEAD_V1",
            "command_hash": command.command_hash,
            "observed_registry_head_hash": observed_registry_head_hash,
            "observed_provider_revision": observed_provider_revision,
        }
    )


def _derived_receipt(
    command: GenesisAdmissionReplayReserveOnceCommandV1,
    returned_registry_head_hash: str,
    returned_provider_revision: int,
) -> str:
    return _hash_payload(
        {
            "domain": "GENESIS_ADMISSION_REPLAY_RESERVATION_RECEIPT_V1",
            "command_hash": command.command_hash,
            "returned_registry_head_hash": returned_registry_head_hash,
            "returned_provider_revision": returned_provider_revision,
        }
    )


def _result_payload(
    *,
    command: GenesisAdmissionReplayReserveOnceCommandV1,
    outcome: GenesisAdmissionReplayReservationOutcomeV1,
    observed_registry_head_hash: str,
    observed_provider_revision: int,
    returned_registry_head_hash: str,
    returned_provider_revision: int,
    reservation_receipt_hash: str | None,
    duplicate_reservation_receipt_hash: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": RESERVE_ONCE_RESULT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "registry_namespace": RESERVATION_NAMESPACE,
        "command_hash": command.command_hash,
        "genesis_admission_replay_key_hash": (
            command.genesis_admission_replay_key_hash
        ),
        "outcome": outcome.value,
        "observed_registry_head_hash": observed_registry_head_hash,
        "observed_provider_revision": observed_provider_revision,
        "returned_registry_head_hash": returned_registry_head_hash,
        "returned_provider_revision": returned_provider_revision,
        "reservation_receipt_hash": reservation_receipt_hash,
        "duplicate_reservation_receipt_hash": (
            duplicate_reservation_receipt_hash
        ),
    }


@dataclass(frozen=True, slots=True)
class GenesisAdmissionReplayReserveOnceResultV1:
    schema_version: str
    static_fingerprint: str
    registry_namespace: str
    command_hash: str
    genesis_admission_replay_key_hash: str
    outcome: GenesisAdmissionReplayReservationOutcomeV1
    observed_registry_head_hash: str
    observed_provider_revision: int
    returned_registry_head_hash: str
    returned_provider_revision: int
    reservation_receipt_hash: str | None
    duplicate_reservation_receipt_hash: str | None
    result_hash: str

    def __post_init__(self) -> None:
        if self.schema_version != RESERVE_ONCE_RESULT_SCHEMA_VERSION:
            raise ValueError("result schema alias is forbidden")
        if self.static_fingerprint != STATIC_FINGERPRINT:
            raise ValueError("result fingerprint alias is forbidden")
        if self.registry_namespace != RESERVATION_NAMESPACE:
            raise ValueError("reservation namespace alias is forbidden")
        if not isinstance(
            self.outcome, GenesisAdmissionReplayReservationOutcomeV1
        ):
            raise ValueError("outcome must be the exact enum")
        for label, value in (
            ("command_hash", self.command_hash),
            (
                "genesis_admission_replay_key_hash",
                self.genesis_admission_replay_key_hash,
            ),
            ("observed_registry_head_hash", self.observed_registry_head_hash),
            ("returned_registry_head_hash", self.returned_registry_head_hash),
        ):
            _require_hash(value, label)
        _require_revision(
            self.observed_provider_revision, "observed_provider_revision"
        )
        _require_revision(
            self.returned_provider_revision, "returned_provider_revision"
        )
        if self.reservation_receipt_hash is not None:
            _require_hash(
                self.reservation_receipt_hash, "reservation_receipt_hash"
            )
        if self.duplicate_reservation_receipt_hash is not None:
            _require_hash(
                self.duplicate_reservation_receipt_hash,
                "duplicate_reservation_receipt_hash",
            )
        payload = {
            "schema_version": self.schema_version,
            "static_fingerprint": self.static_fingerprint,
            "registry_namespace": self.registry_namespace,
            "command_hash": self.command_hash,
            "genesis_admission_replay_key_hash": (
                self.genesis_admission_replay_key_hash
            ),
            "outcome": self.outcome.value,
            "observed_registry_head_hash": self.observed_registry_head_hash,
            "observed_provider_revision": self.observed_provider_revision,
            "returned_registry_head_hash": self.returned_registry_head_hash,
            "returned_provider_revision": self.returned_provider_revision,
            "reservation_receipt_hash": self.reservation_receipt_hash,
            "duplicate_reservation_receipt_hash": (
                self.duplicate_reservation_receipt_hash
            ),
        }
        if _require_hash(self.result_hash, "result_hash") != _hash_payload(payload):
            raise ValueError("result_hash mismatch")


def build_genesis_admission_replay_reserve_once_result_v1(
    command: GenesisAdmissionReplayReserveOnceCommandV1,
    *,
    outcome: GenesisAdmissionReplayReservationOutcomeV1,
    observed_registry_head_hash: Any,
    observed_provider_revision: Any,
    duplicate_reservation_receipt_hash: Any = None,
) -> GenesisAdmissionReplayReserveOnceResultV1:
    if not isinstance(command, GenesisAdmissionReplayReserveOnceCommandV1):
        raise ValueError("command must be exact reserve-once-command-v1")
    if not isinstance(outcome, GenesisAdmissionReplayReservationOutcomeV1):
        raise ValueError("outcome must be the exact enum")
    observed_head = _require_hash(
        observed_registry_head_hash, "observed_registry_head_hash"
    )
    observed_revision = _require_revision(
        observed_provider_revision, "observed_provider_revision"
    )
    state_matches = (
        observed_head == command.expected_registry_head_hash
        and observed_revision == command.expected_provider_revision
    )
    if outcome is GenesisAdmissionReplayReservationOutcomeV1.RESERVED:
        if not state_matches:
            raise ValueError("RESERVED requires matching expected state")
        returned_revision = observed_revision + 1
        returned_head = _derived_returned_head(
            command, observed_head, observed_revision
        )
        receipt = _derived_receipt(
            command, returned_head, returned_revision
        )
        duplicate = None
    elif outcome is GenesisAdmissionReplayReservationOutcomeV1.ALREADY_RESERVED:
        duplicate = _require_hash(
            duplicate_reservation_receipt_hash,
            "duplicate_reservation_receipt_hash",
        )
        returned_head = observed_head
        returned_revision = observed_revision
        receipt = None
    elif outcome is GenesisAdmissionReplayReservationOutcomeV1.COMPARE_AND_SWAP_CONFLICT:
        if state_matches:
            raise ValueError("conflict requires mismatched observed state")
        returned_head = observed_head
        returned_revision = observed_revision
        receipt = None
        duplicate = None
    else:
        returned_head = observed_head
        returned_revision = observed_revision
        receipt = None
        duplicate = None
    payload = _result_payload(
        command=command,
        outcome=outcome,
        observed_registry_head_hash=observed_head,
        observed_provider_revision=observed_revision,
        returned_registry_head_hash=returned_head,
        returned_provider_revision=returned_revision,
        reservation_receipt_hash=receipt,
        duplicate_reservation_receipt_hash=duplicate,
    )
    return GenesisAdmissionReplayReserveOnceResultV1(
        schema_version=payload["schema_version"],
        static_fingerprint=payload["static_fingerprint"],
        registry_namespace=payload["registry_namespace"],
        command_hash=payload["command_hash"],
        genesis_admission_replay_key_hash=payload[
            "genesis_admission_replay_key_hash"
        ],
        outcome=outcome,
        observed_registry_head_hash=payload[
            "observed_registry_head_hash"
        ],
        observed_provider_revision=payload["observed_provider_revision"],
        returned_registry_head_hash=payload[
            "returned_registry_head_hash"
        ],
        returned_provider_revision=payload["returned_provider_revision"],
        reservation_receipt_hash=payload["reservation_receipt_hash"],
        duplicate_reservation_receipt_hash=payload[
            "duplicate_reservation_receipt_hash"
        ],
        result_hash=_hash_payload(payload),
    )


def verify_genesis_admission_replay_reserve_once_result_v1(
    result: Any,
    command: GenesisAdmissionReplayReserveOnceCommandV1,
    *,
    expected_result_hash: Any,
) -> bool:
    try:
        return (
            isinstance(result, GenesisAdmissionReplayReserveOnceResultV1)
            and result.command_hash == command.command_hash
            and result.genesis_admission_replay_key_hash
            == command.genesis_admission_replay_key_hash
            and result.result_hash
            == _require_hash(expected_result_hash, "expected_result_hash")
        )
    except (TypeError, ValueError):
        return False


@runtime_checkable
class GenesisAdmissionReplayReservationPortV1(Protocol):
    def reserve_once(
        self, command: GenesisAdmissionReplayReserveOnceCommandV1
    ) -> GenesisAdmissionReplayReserveOnceResultV1: ...


__all__ = [
    "RESERVATION_NAMESPACE",
    "RESERVE_ONCE_COMMAND_SCHEMA_VERSION",
    "RESERVE_ONCE_RESULT_SCHEMA_VERSION",
    "GenesisAdmissionReplayReservationOutcomeV1",
    "GenesisAdmissionReplayReservationPortV1",
    "GenesisAdmissionReplayReserveOnceCommandV1",
    "GenesisAdmissionReplayReserveOnceResultV1",
    "build_genesis_admission_replay_reserve_once_command_v1",
    "build_genesis_admission_replay_reserve_once_result_v1",
    "verify_genesis_admission_replay_reserve_once_result_v1",
]
