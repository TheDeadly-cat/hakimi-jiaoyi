from __future__ import annotations

from collections.abc import Mapping
from typing import Any

try:
    from domain.contracts import MarketDataEnvelope, MarketDataSourceManifest
except ModuleNotFoundError:  # Package import path.
    from exchange_terminal.domain.contracts import (
        MarketDataEnvelope,
        MarketDataSourceManifest,
    )

try:
    from services.strict_canonical_json_hash import strict_canonical_hash
except ModuleNotFoundError:  # Package import path.
    from exchange_terminal.services.strict_canonical_json_hash import (
        strict_canonical_hash,
    )


ENVELOPE_SCHEMA_VERSION = "market-data-envelope-v1"
MANIFEST_SCHEMA_VERSION = "market-data-source-manifest-v1"
VERIFICATION_SCHEMA_VERSION = "market-data-envelope-verification-v1"
ENVELOPE_FIELD = "market_data_envelope"

_ENVELOPE_FIELDS = {
    "symbol",
    "timeframe",
    "rows",
    "source_manifest",
    "research_only",
    "paper_authorized",
    "live_order_allowed",
    "schema_version",
}
_MANIFEST_FIELDS = {
    "provider",
    "real_rows",
    "cache_rows",
    "synthetic_rows",
    "fallback",
    "complete",
    "dataset_hash",
    "schema_version",
}
_NON_REAL_SOURCE_MARKER_FRAGMENTS = (
    "backtest",
    "demo",
    "dummy",
    "fake",
    "fallback",
    "fixture",
    "generated",
    "mock",
    "paper",
    "placeholder",
    "random",
    "replay",
    "sample",
    "sandbox",
    "simulated",
    "simulation",
    "stub",
    "synthetic",
    "test",
    "unknown",
)
_SOURCE_MARKER_MAX_LENGTH = 256
_ENVELOPE_IDENTITY_MAX_LENGTH = 128


def _canonical_hash(value: Any) -> str:
    try:
        return strict_canonical_hash(value)
    except ValueError as exc:
        raise ValueError("market_data_envelope_non_canonical_rows") from exc


def _copy_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(row, Mapping) for row in value):
        raise ValueError("market_data_envelope_rows_invalid")
    return [dict(row) for row in value]


def _normalized_source_text(value: Any, *, default: str) -> str:
    if not isinstance(value, str):
        return default
    normalized = value.strip()
    if (
        not normalized
        or len(normalized) > _SOURCE_MARKER_MAX_LENGTH
        or any(
            ord(character) < 0x20
            or ord(character) in {0x7F, 0x2028, 0x2029}
            for character in normalized
        )
    ):
        return default
    return normalized


def _source_marker(row: Mapping[str, Any]) -> str:
    return _normalized_source_text(row.get("source"), default="").lower()


def _provider_marker(value: Any) -> str:
    return _normalized_source_text(value, default="unknown")


def _normalized_envelope_identity(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"market_data_envelope_{field}_invalid")
    normalized = value.strip()
    if (
        not normalized
        or len(normalized) > _ENVELOPE_IDENTITY_MAX_LENGTH
        or "|" in normalized
        or any(
            ord(character) < 0x20
            or ord(character) in {0x7F, 0x2028, 0x2029}
            for character in normalized
        )
    ):
        raise ValueError(f"market_data_envelope_{field}_invalid")
    return normalized


def _source_marker_is_non_real(marker: str) -> bool:
    return not marker or any(
        fragment in marker for fragment in _NON_REAL_SOURCE_MARKER_FRAGMENTS
    )


def _manifest_for(
    rows: list[dict[str, Any]],
    provider: str,
    *,
    dataset_hash: str | None = None,
) -> MarketDataSourceManifest:
    row_markers = [_source_marker(row) for row in rows]
    synthetic_rows = sum(_source_marker_is_non_real(marker) for marker in row_markers)
    cache_rows = sum(
        ("cache" in marker or "local" in marker)
        and not _source_marker_is_non_real(marker)
        for marker in row_markers
    )
    provider_marker = provider.strip().lower()
    source_marker_mismatch = any(
        marker != provider_marker for marker in row_markers
    )
    fallback = (
        synthetic_rows > 0
        or _source_marker_is_non_real(provider_marker)
        or source_marker_mismatch
    )
    return MarketDataSourceManifest(
        provider=provider,
        real_rows=len(rows) - synthetic_rows,
        cache_rows=cache_rows,
        synthetic_rows=synthetic_rows,
        fallback=fallback,
        complete=bool(rows) and all(row.get("complete") is True for row in rows),
        dataset_hash=dataset_hash if dataset_hash is not None else _canonical_hash(rows),
    )


def build_market_data_envelope(
    payload: Mapping[str, Any],
    *,
    symbol: str,
    timeframe: str,
) -> dict[str, Any]:
    rows = _copy_rows(payload.get("rows"))
    provider = _provider_marker(payload.get("source"))
    envelope = MarketDataEnvelope(
        symbol=_normalized_envelope_identity(symbol, field="symbol"),
        timeframe=_normalized_envelope_identity(timeframe, field="timeframe"),
        rows=rows,
        source_manifest=_manifest_for(rows, provider),
    )
    return envelope.to_dict()


def verify_market_data_envelope(
    envelope: Any,
    *,
    expected_symbol: str | None = None,
    expected_timeframe: str | None = None,
    expected_rows: Any = None,
    expected_provider: str | None = None,
) -> dict[str, Any]:
    blockers: set[str] = set()
    observed_hash: str | None = None
    if not isinstance(envelope, Mapping):
        blockers.add("market_data_envelope_not_object")
        envelope = {}
    if set(envelope) != _ENVELOPE_FIELDS:
        blockers.add("market_data_envelope_fields_invalid")
    if envelope.get("schema_version") != ENVELOPE_SCHEMA_VERSION:
        blockers.add("market_data_envelope_schema_invalid")
    if envelope.get("research_only") is not True:
        blockers.add("market_data_envelope_research_only_invalid")
    if envelope.get("paper_authorized") is not False:
        blockers.add("market_data_envelope_paper_authority_invalid")
    if envelope.get("live_order_allowed") is not False:
        blockers.add("market_data_envelope_live_authority_invalid")

    symbol = envelope.get("symbol")
    timeframe = envelope.get("timeframe")
    try:
        if _normalized_envelope_identity(symbol, field="symbol") != symbol:
            raise ValueError("market_data_envelope_symbol_invalid")
    except ValueError:
        blockers.add("market_data_envelope_symbol_invalid")
    try:
        if _normalized_envelope_identity(timeframe, field="timeframe") != timeframe:
            raise ValueError("market_data_envelope_timeframe_invalid")
    except ValueError:
        blockers.add("market_data_envelope_timeframe_invalid")
    if expected_symbol is not None and symbol != expected_symbol:
        blockers.add("market_data_envelope_symbol_mismatch")
    if expected_timeframe is not None and timeframe != expected_timeframe:
        blockers.add("market_data_envelope_timeframe_mismatch")

    rows: list[dict[str, Any]] | None = None
    try:
        rows = _copy_rows(envelope.get("rows"))
        observed_hash = _canonical_hash(rows)
    except ValueError as exc:
        blockers.add(str(exc))
    if expected_rows is not None:
        try:
            if rows != _copy_rows(expected_rows):
                blockers.add("market_data_envelope_payload_rows_mismatch")
        except ValueError:
            blockers.add("market_data_envelope_payload_rows_invalid")

    manifest = envelope.get("source_manifest")
    if not isinstance(manifest, Mapping):
        blockers.add("market_data_source_manifest_not_object")
        manifest = {}
    if set(manifest) != _MANIFEST_FIELDS:
        blockers.add("market_data_source_manifest_fields_invalid")
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        blockers.add("market_data_source_manifest_schema_invalid")
    provider = manifest.get("provider")
    if not isinstance(provider, str) or not provider.strip():
        blockers.add("market_data_source_manifest_provider_invalid")
    if expected_provider is not None and provider != expected_provider:
        blockers.add("market_data_source_manifest_provider_mismatch")
    for field in ("real_rows", "cache_rows", "synthetic_rows"):
        value = manifest.get(field)
        if type(value) is not int or value < 0:
            blockers.add(f"market_data_source_manifest_{field}_invalid")
    for field in ("fallback", "complete"):
        if type(manifest.get(field)) is not bool:
            blockers.add(f"market_data_source_manifest_{field}_invalid")
    if not isinstance(manifest.get("dataset_hash"), str):
        blockers.add("market_data_source_manifest_dataset_hash_invalid")

    if rows is not None and isinstance(provider, str) and provider.strip():
        expected_manifest = _manifest_for(
            rows,
            provider,
            dataset_hash=observed_hash,
        ).to_dict()
        for field in _MANIFEST_FIELDS:
            if manifest.get(field) != expected_manifest[field]:
                blockers.add(f"market_data_source_manifest_{field}_mismatch")
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": sorted(blockers),
        "dataset_hash": observed_hash,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def attach_market_data_envelope(
    payload: Mapping[str, Any],
    *,
    symbol: str,
    timeframe: str,
) -> dict[str, Any]:
    attached = dict(payload)
    attached[ENVELOPE_FIELD] = build_market_data_envelope(payload, symbol=symbol, timeframe=timeframe)
    return attached


def consume_market_data_envelope(
    payload: Mapping[str, Any],
    *,
    expected_symbol: str,
    expected_timeframe: str,
    required: bool,
    require_complete: bool,
) -> dict[str, Any]:
    consumed = dict(payload)
    envelope = consumed.get(ENVELOPE_FIELD)
    if envelope is None:
        if required:
            raise ValueError("market_data_envelope_required")
        return consumed
    provider = _provider_marker(payload.get("source"))
    verification = verify_market_data_envelope(
        envelope,
        expected_symbol=expected_symbol,
        expected_timeframe=expected_timeframe,
        expected_rows=payload.get("rows"),
        expected_provider=provider,
    )
    blockers = list(verification["blockers"])
    if payload.get("symbol") != expected_symbol:
        blockers.append("market_data_envelope_payload_symbol_mismatch")
    if require_complete and payload.get("ok") is not True:
        blockers.append("market_data_envelope_payload_ok_invalid")
    if require_complete and verification["status"] == "PASS":
        manifest = envelope["source_manifest"]
        if manifest["complete"] is not True:
            blockers.append("market_data_envelope_incomplete")
        if manifest["fallback"] is not False:
            blockers.append("market_data_envelope_fallback_not_allowed")
        if manifest["synthetic_rows"] != 0:
            blockers.append("market_data_envelope_synthetic_not_allowed")
        if manifest["provider"] == "unknown":
            blockers.append("market_data_envelope_provider_unknown")
    if blockers:
        raise ValueError("market_data_envelope_blocked:" + ",".join(sorted(set(blockers))))
    consumed.pop(ENVELOPE_FIELD, None)
    return consumed


def consume_market_data_payloads(
    payloads: Mapping[str, Mapping[str, Any]],
    *,
    expected_timeframe: str,
    required: bool,
    require_complete: bool,
) -> dict[str, dict[str, Any]]:
    return {
        symbol: consume_market_data_envelope(
            payload,
            expected_symbol=symbol,
            expected_timeframe=expected_timeframe,
            required=required,
            require_complete=require_complete,
        )
        for symbol, payload in payloads.items()
    }
