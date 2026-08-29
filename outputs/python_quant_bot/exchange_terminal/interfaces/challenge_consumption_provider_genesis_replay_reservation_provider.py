"""Compatibility shim for the canonical application-owned replay reservation port."""

from exchange_terminal.application.ports.challenge_consumption_provider_genesis_replay_reservation_provider_v1 import (
    GenesisAdmissionReplayReservationOutcomeV1,
    GenesisAdmissionReplayReservationPortV1,
    GenesisAdmissionReplayReserveOnceCommandV1,
    GenesisAdmissionReplayReserveOnceResultV1,
    RESERVATION_NAMESPACE,
    RESERVE_ONCE_COMMAND_SCHEMA_VERSION,
    RESERVE_ONCE_RESULT_SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    build_genesis_admission_replay_reserve_once_command_v1,
    build_genesis_admission_replay_reserve_once_result_v1,
    verify_genesis_admission_replay_reserve_once_result_v1,
)

__all__ = (
    "GenesisAdmissionReplayReservationOutcomeV1",
    "GenesisAdmissionReplayReservationPortV1",
    "GenesisAdmissionReplayReserveOnceCommandV1",
    "GenesisAdmissionReplayReserveOnceResultV1",
    "RESERVATION_NAMESPACE",
    "RESERVE_ONCE_COMMAND_SCHEMA_VERSION",
    "RESERVE_ONCE_RESULT_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_genesis_admission_replay_reserve_once_command_v1",
    "build_genesis_admission_replay_reserve_once_result_v1",
    "verify_genesis_admission_replay_reserve_once_result_v1",
)
