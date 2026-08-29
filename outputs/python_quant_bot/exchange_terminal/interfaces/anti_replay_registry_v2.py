"""Compatibility shim for the canonical application-owned anti-replay V2 port."""

from exchange_terminal.application.ports.anti_replay_registry_v2 import (
    AntiReplayCompareAndConsumeCommandV2,
    AntiReplayCompareAndConsumeResultV2,
    AntiReplayRegistryOutcomeV1,
    AntiReplayRegistryPortV2,
    COMMAND_SCHEMA_VERSION,
    REQUEST_SCHEMA_VERSION,
    RESULT_SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    build_anti_replay_compare_and_consume_request_v2,
    build_anti_replay_consumption_key_v2,
    verify_anti_replay_compare_and_consume_request_v2,
)

__all__ = (
    "AntiReplayCompareAndConsumeCommandV2",
    "AntiReplayCompareAndConsumeResultV2",
    "AntiReplayRegistryOutcomeV1",
    "AntiReplayRegistryPortV2",
    "COMMAND_SCHEMA_VERSION",
    "REQUEST_SCHEMA_VERSION",
    "RESULT_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_anti_replay_compare_and_consume_request_v2",
    "build_anti_replay_consumption_key_v2",
    "verify_anti_replay_compare_and_consume_request_v2",
)
