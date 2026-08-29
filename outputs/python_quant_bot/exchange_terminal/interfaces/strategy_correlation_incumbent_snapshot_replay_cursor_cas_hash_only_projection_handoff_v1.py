"""Exact ADR0381 handoff for a future unmounted JavaScript consumer."""

from __future__ import annotations

import json
import re
from typing import Any, Final, Mapping

from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_freshness_replay_gate_v1 as replay_gate,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_cas_transition_hash_only_projection_v1
    as readonly_projection,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_cas_transition_v1 as cas,
)


HANDOFF_SCHEMA_VERSION: Final = (
    "incumbent-snapshot-replay-cursor-cas-hash-only-projection-"
    "verification-handoff-v1"
)
VERIFICATION_STATUS: Final = (
    "EXACTLY_VERIFIED_INCUMBENT_SNAPSHOT_REPLAY_CURSOR_CAS_"
    "HASH_ONLY_PROJECTION_V1"
)
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_JS_MAX_SAFE_INTEGER = 9_007_199_254_740_991


def _is_hash(value: object) -> bool:
    return type(value) is str and _HEX64_RE.fullmatch(value) is not None


def _is_js_safe_json_value(value: object) -> bool:
    if value is None or type(value) in (str, bool):
        return True
    if type(value) is int:
        return -_JS_MAX_SAFE_INTEGER <= value <= _JS_MAX_SAFE_INTEGER
    if type(value) is list:
        return all(_is_js_safe_json_value(item) for item in value)
    if type(value) is dict:
        return all(
            type(key) is str and _is_js_safe_json_value(item)
            for key, item in value.items()
        )
    return False


def _json_safe_clone(value: object) -> object | None:
    try:
        encoded = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        cloned = json.loads(encoded)
    except (TypeError, ValueError, UnicodeEncodeError, json.JSONDecodeError):
        return None
    return cloned if _is_js_safe_json_value(cloned) else None


def build_incumbent_snapshot_replay_cursor_cas_hash_only_projection_handoff_v1(
    readonly_projection_document: Any,
    base_cursor: replay_gate.IncumbentSnapshotReplayCursorV1,
    observed_cursor: replay_gate.IncumbentSnapshotReplayCursorV1,
    attestation: replay_gate.IncumbentSnapshotSequenceAttestationV1,
    freshness_result: replay_gate.IncumbentSnapshotFreshnessReplayResultV1,
    intent: cas.IncumbentSnapshotReplayCursorCasTransitionIntentV1,
    *,
    expected_readonly_projection_hash: Any,
    expected_intent_hash: Any,
    expected_freshness_result_fingerprint_sha256: Any,
    expected_attestation_hash: Any,
    expected_base_cursor_hash: Any,
    expected_observed_cursor_hash: Any,
    expected_stream_id: Any,
    expected_projection_preregistration_hash: Any,
) -> dict[str, Any] | None:
    if (
        not isinstance(readonly_projection_document, Mapping)
        or not _is_hash(expected_readonly_projection_hash)
    ):
        return None
    try:
        verified = readonly_projection.verify_incumbent_snapshot_replay_cursor_cas_hash_only_projection_v1(
            readonly_projection_document,
            base_cursor,
            observed_cursor,
            attestation,
            freshness_result,
            intent,
            expected_readonly_projection_hash=(
                expected_readonly_projection_hash
            ),
            expected_intent_hash=expected_intent_hash,
            expected_freshness_result_fingerprint_sha256=(
                expected_freshness_result_fingerprint_sha256
            ),
            expected_attestation_hash=expected_attestation_hash,
            expected_base_cursor_hash=expected_base_cursor_hash,
            expected_observed_cursor_hash=expected_observed_cursor_hash,
            expected_stream_id=expected_stream_id,
            expected_projection_preregistration_hash=(
                expected_projection_preregistration_hash
            ),
        )
    except (KeyError, TypeError, ValueError):
        return None
    if not verified:
        return None

    cloned = _json_safe_clone(dict(readonly_projection_document))
    if type(cloned) is not dict:
        return None
    return {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "verification_status": VERIFICATION_STATUS,
        "expected_readonly_projection_hash": expected_readonly_projection_hash,
        "projection": cloned,
    }


def verify_incumbent_snapshot_replay_cursor_cas_hash_only_projection_handoff_v1(
    envelope: Any,
    readonly_projection_document: Any,
    base_cursor: replay_gate.IncumbentSnapshotReplayCursorV1,
    observed_cursor: replay_gate.IncumbentSnapshotReplayCursorV1,
    attestation: replay_gate.IncumbentSnapshotSequenceAttestationV1,
    freshness_result: replay_gate.IncumbentSnapshotFreshnessReplayResultV1,
    intent: cas.IncumbentSnapshotReplayCursorCasTransitionIntentV1,
    *,
    expected_readonly_projection_hash: Any,
    expected_intent_hash: Any,
    expected_freshness_result_fingerprint_sha256: Any,
    expected_attestation_hash: Any,
    expected_base_cursor_hash: Any,
    expected_observed_cursor_hash: Any,
    expected_stream_id: Any,
    expected_projection_preregistration_hash: Any,
) -> bool:
    expected = (
        build_incumbent_snapshot_replay_cursor_cas_hash_only_projection_handoff_v1(
            readonly_projection_document,
            base_cursor,
            observed_cursor,
            attestation,
            freshness_result,
            intent,
            expected_readonly_projection_hash=(
                expected_readonly_projection_hash
            ),
            expected_intent_hash=expected_intent_hash,
            expected_freshness_result_fingerprint_sha256=(
                expected_freshness_result_fingerprint_sha256
            ),
            expected_attestation_hash=expected_attestation_hash,
            expected_base_cursor_hash=expected_base_cursor_hash,
            expected_observed_cursor_hash=expected_observed_cursor_hash,
            expected_stream_id=expected_stream_id,
            expected_projection_preregistration_hash=(
                expected_projection_preregistration_hash
            ),
        )
    )
    return (
        isinstance(envelope, Mapping)
        and expected is not None
        and dict(envelope) == expected
    )


__all__ = [
    "HANDOFF_SCHEMA_VERSION",
    "VERIFICATION_STATUS",
    "build_incumbent_snapshot_replay_cursor_cas_hash_only_projection_handoff_v1",
    "verify_incumbent_snapshot_replay_cursor_cas_hash_only_projection_handoff_v1",
]
