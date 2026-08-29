"""Compatibility shim for the canonical challenge-consumption application port."""

from exchange_terminal.application.ports.strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider_v1 import (
    CHALLENGE_CONSUMPTION_NAMESPACE,
    CONSUME_ONCE_COMMAND_SCHEMA_VERSION,
    CONSUME_ONCE_RESULT_SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    ChallengeConsumptionProviderOutcomeV1,
    ReplayCursorProviderRegistrationChallengeConsumeOnceCommandV1,
    ReplayCursorProviderRegistrationChallengeConsumeOnceResultV1,
    ReplayCursorProviderRegistrationChallengeConsumptionPortV1,
    build_replay_cursor_provider_registration_challenge_consume_once_command_v1,
    build_replay_cursor_provider_registration_challenge_consume_once_result_v1,
    derive_challenge_consumption_receipt_hash_v1,
    derive_consumed_registry_head_v1,
    verify_replay_cursor_provider_registration_challenge_consume_once_command_v1,
    verify_replay_cursor_provider_registration_challenge_consume_once_result_v1,
)

__all__ = (
    "CHALLENGE_CONSUMPTION_NAMESPACE",
    "CONSUME_ONCE_COMMAND_SCHEMA_VERSION",
    "CONSUME_ONCE_RESULT_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
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
)
