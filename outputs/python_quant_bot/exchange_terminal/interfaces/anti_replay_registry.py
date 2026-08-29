"""Compatibility shim for the application-owned anti-replay registry port."""

from __future__ import annotations

from exchange_terminal.application.ports.anti_replay_registry_v1 import (
    ANTI_REPLAY_NAMESPACE,
    COMPARE_AND_CONSUME_COMMAND_SCHEMA_VERSION,
    COMPARE_AND_CONSUME_RESULT_SCHEMA_VERSION,
    CONSUMPTION_REQUEST_SCHEMA_VERSION,
    TARGET_CONSUMPTION_RECEIPT_SCHEMA_VERSION,
    AntiReplayCompareAndConsumeCommandV1,
    AntiReplayCompareAndConsumeResultV1,
    AntiReplayRegistryOutcomeV1,
    AntiReplayRegistryPortV1,
)


COMPATIBILITY_SHIM_SCHEMA_VERSION = (
    "anti-replay-registry-interface-compatibility-shim-v1"
)
CANONICAL_PORT_MODULE = (
    "exchange_terminal.application.ports.anti_replay_registry_v1"
)
CANONICAL_PORT_IMPLEMENTATION_SHA256 = (
    "5eed523c3665e687c6d2f202afcea5cc93bcdee3ef4ee942a7d4f76364f380a0"
)

__all__ = (
    "ANTI_REPLAY_NAMESPACE",
    "CANONICAL_PORT_IMPLEMENTATION_SHA256",
    "CANONICAL_PORT_MODULE",
    "COMPARE_AND_CONSUME_COMMAND_SCHEMA_VERSION",
    "COMPARE_AND_CONSUME_RESULT_SCHEMA_VERSION",
    "COMPATIBILITY_SHIM_SCHEMA_VERSION",
    "CONSUMPTION_REQUEST_SCHEMA_VERSION",
    "TARGET_CONSUMPTION_RECEIPT_SCHEMA_VERSION",
    "AntiReplayCompareAndConsumeCommandV1",
    "AntiReplayCompareAndConsumeResultV1",
    "AntiReplayRegistryOutcomeV1",
    "AntiReplayRegistryPortV1",
)