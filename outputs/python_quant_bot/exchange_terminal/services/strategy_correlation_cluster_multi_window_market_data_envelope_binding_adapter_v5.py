"""Bind canonical market-data envelopes to the raw-recompute lineage adapter.

The adapter verifies research-only per-symbol envelopes, aligns one completed
daily close grid, derives returns, and exact-verifies adapter-v4. Provider names
are structurally bound but are not treated as authenticated identities.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import hmac
import math
import re
from typing import Any

from exchange_terminal.application.market_data_envelope import (
    ENVELOPE_FIELD,
    consume_market_data_envelope,
    verify_market_data_envelope,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_multi_window_return_panel_lineage_adapter_v4
    as lineage_v4,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-multi-window-market-data-envelope-"
    "binding-preregistration-v5"
)
ADAPTER_SCHEMA_VERSION = (
    "strategy-correlation-cluster-multi-window-market-data-envelope-"
    "binding-adapter-v5"
)
PREREGISTRATION_VERIFICATION_SCHEMA_VERSION = (
    f"{PREREGISTRATION_SCHEMA_VERSION}-verification-v1"
)
ADAPTER_VERIFICATION_SCHEMA_VERSION = f"{ADAPTER_SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = (
    "20260825-correlation-cluster-multi-window-market-data-envelope-"
    "binding-v5-lock-1"
)
ENVELOPE_TIMEFRAME = "1D"
RETURN_TIMEFRAME = "1d"
RETURN_DECIMALS = 15
MAXIMUM_CLOSE_ROW_COUNT = lineage_v4.MAXIMUM_PANEL_ROWS + 1

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_BINDING_KEYS = {
    "symbol",
    "provider",
    "dataset_hash",
    "row_count",
    "real_rows",
    "cache_rows",
    "synthetic_rows",
    "fallback",
    "complete",
    "first_ts_ms",
    "last_ts_ms",
}


class MarketDataEnvelopeBindingContractError(ValueError):
    """Raised when envelope rows cannot produce one canonical return panel."""


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "writer_allowed": False,
        "runtime_gate_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _verification(schema_version: str, blockers: list[str], **facts: Any) -> dict[str, Any]:
    unique = sorted(set(blockers))
    return {
        "schema_version": schema_version,
        "status": "BLOCK" if unique else "PASS",
        "blockers": unique,
        **facts,
        "authority": _authority(),
    }


def _is_hash(value: Any) -> bool:
    return type(value) is str and _HASH_RE.fullmatch(value) is not None


def _same_hash(left: Any, right: Any) -> bool:
    return _is_hash(left) and _is_hash(right) and hmac.compare_digest(left, right)


def _symbol(value: Any) -> str:
    if type(value) is not str or not value.strip():
        raise MarketDataEnvelopeBindingContractError("symbol is invalid")
    return value.strip().upper()


def _close(value: Any) -> float:
    if (
        type(value) not in {int, float}
        or not math.isfinite(float(value))
        or float(value) <= 0
    ):
        raise MarketDataEnvelopeBindingContractError(
            "close must be a positive finite native number"
        )
    return float(value)


def _return(left: float, right: float) -> float:
    value = round(right / left - 1.0, RETURN_DECIMALS)
    if not math.isfinite(value):
        raise MarketDataEnvelopeBindingContractError("derived return is not finite")
    return 0.0 if value == 0.0 else value


def _utc_date(ts_ms: int) -> str:
    try:
        return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).date().isoformat()
    except (OSError, OverflowError, ValueError) as exc:
        raise MarketDataEnvelopeBindingContractError("ts_ms is out of range") from exc


def _verified_payloads(
    payloads: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if type(payloads) is not dict or len(payloads) < 2:
        raise MarketDataEnvelopeBindingContractError(
            "at least two native payloads are required"
        )
    clean_symbols = sorted(_symbol(symbol) for symbol in payloads)
    if len(set(clean_symbols)) != len(clean_symbols) or set(payloads) != set(clean_symbols):
        raise MarketDataEnvelopeBindingContractError(
            "payload symbols must be canonical and unique"
        )
    closes_by_symbol: dict[str, list[float]] = {}
    timestamps_by_symbol: dict[str, list[int]] = {}
    bindings: list[dict[str, Any]] = []
    for symbol in clean_symbols:
        payload = payloads[symbol]
        if type(payload) is not dict:
            raise MarketDataEnvelopeBindingContractError("payload is not a native object")
        provider = payload.get("source")
        if (
            type(provider) is not str
            or not provider.strip()
            or provider.strip().lower() == "unknown"
        ):
            raise MarketDataEnvelopeBindingContractError("provider is invalid")
        envelope = payload.get(ENVELOPE_FIELD)
        receipt = verify_market_data_envelope(
            envelope,
            expected_symbol=symbol,
            expected_timeframe=ENVELOPE_TIMEFRAME,
            expected_rows=payload.get("rows"),
            expected_provider=provider,
        )
        if receipt["status"] != "PASS":
            raise MarketDataEnvelopeBindingContractError(
                "market data envelope exact verification failed"
            )
        try:
            consumed = consume_market_data_envelope(
                payload,
                expected_symbol=symbol,
                expected_timeframe=ENVELOPE_TIMEFRAME,
                required=True,
                require_complete=True,
            )
        except ValueError as exc:
            raise MarketDataEnvelopeBindingContractError(
                "market data envelope complete-source gate blocked"
            ) from exc
        if consumed.get("symbol") != symbol or consumed.get("ok") is not True:
            raise MarketDataEnvelopeBindingContractError(
                "market data payload identity is invalid"
            )
        rows = consumed.get("rows")
        if (
            type(rows) is not list
            or len(rows) < 2
            or len(rows) > MAXIMUM_CLOSE_ROW_COUNT
        ):
            raise MarketDataEnvelopeBindingContractError(
                "close rows must be a bounded list with at least two rows"
            )
        timestamps: list[int] = []
        closes: list[float] = []
        previous_ts = -1
        for row in rows:
            if type(row) is not dict:
                raise MarketDataEnvelopeBindingContractError("close row is invalid")
            ts_ms = row.get("ts_ms")
            if (
                type(ts_ms) is not int
                or isinstance(ts_ms, bool)
                or ts_ms <= previous_ts
                or row.get("complete") is not True
                or row.get("source") != provider
            ):
                raise MarketDataEnvelopeBindingContractError(
                    "close row timestamp, completeness, or source is invalid"
                )
            timestamps.append(ts_ms)
            closes.append(_close(row.get("close")))
            previous_ts = ts_ms
        manifest = envelope["source_manifest"]
        bindings.append(
            {
                "symbol": symbol,
                "provider": provider,
                "dataset_hash": receipt["dataset_hash"],
                "row_count": len(rows),
                "real_rows": manifest["real_rows"],
                "cache_rows": manifest["cache_rows"],
                "synthetic_rows": manifest["synthetic_rows"],
                "fallback": manifest["fallback"],
                "complete": manifest["complete"],
                "first_ts_ms": timestamps[0],
                "last_ts_ms": timestamps[-1],
            }
        )
        timestamps_by_symbol[symbol] = timestamps
        closes_by_symbol[symbol] = closes
    timestamp_grids = {tuple(values) for values in timestamps_by_symbol.values()}
    if len(timestamp_grids) != 1:
        raise MarketDataEnvelopeBindingContractError(
            "all symbols must share one exact timestamp grid"
        )
    timestamps = list(next(iter(timestamp_grids)))
    dates = [_utc_date(ts_ms) for ts_ms in timestamps]
    if len(set(dates)) != len(dates) or dates != sorted(dates):
        raise MarketDataEnvelopeBindingContractError(
            "1D rows must map to one strictly increasing UTC date per row"
        )
    return_rows = []
    for index in range(1, len(timestamps)):
        return_rows.append(
            {
                "date": dates[index],
                "returns": {
                    symbol: _return(
                        closes_by_symbol[symbol][index - 1],
                        closes_by_symbol[symbol][index],
                    )
                    for symbol in clean_symbols
                },
            }
        )
    panel = lineage_v4.build_common_return_panel_v1(
        symbols=clean_symbols,
        rows=return_rows,
        timeframe=RETURN_TIMEFRAME,
        cutoff_date=return_rows[-1]["date"],
    )
    return panel, bindings


def derive_common_return_panel_from_market_data_envelopes_v5(
    payloads: Any,
) -> dict[str, Any]:
    panel, _ = _verified_payloads(payloads)
    return panel


def market_data_envelope_source_bindings_v5(
    payloads: Any,
) -> list[dict[str, Any]]:
    _, bindings = _verified_payloads(payloads)
    return copy.deepcopy(bindings)


def _validate_source_bindings(value: Any) -> list[dict[str, Any]]:
    if type(value) is not list or len(value) < 2:
        raise MarketDataEnvelopeBindingContractError(
            "source bindings must contain at least two symbols"
        )
    normalized: list[dict[str, Any]] = []
    symbols: set[str] = set()
    for item in value:
        if type(item) is not dict or set(item) != _SOURCE_BINDING_KEYS:
            raise MarketDataEnvelopeBindingContractError(
                "source binding shape is invalid"
            )
        symbol = _symbol(item["symbol"])
        provider = item["provider"]
        if (
            item["symbol"] != symbol
            or symbol in symbols
            or type(provider) is not str
            or not provider.strip()
            or provider.strip().lower() == "unknown"
            or not _is_hash(item["dataset_hash"])
            or type(item["row_count"]) is not int
            or isinstance(item["row_count"], bool)
            or item["row_count"] < 2
            or item["row_count"] > MAXIMUM_CLOSE_ROW_COUNT
            or type(item["real_rows"]) is not int
            or item["real_rows"] != item["row_count"]
            or type(item["cache_rows"]) is not int
            or item["cache_rows"] < 0
            or item["cache_rows"] > item["row_count"]
            or type(item["synthetic_rows"]) is not int
            or item["synthetic_rows"] != 0
            or item["fallback"] is not False
            or item["complete"] is not True
            or type(item["first_ts_ms"]) is not int
            or isinstance(item["first_ts_ms"], bool)
            or type(item["last_ts_ms"]) is not int
            or isinstance(item["last_ts_ms"], bool)
            or item["first_ts_ms"] >= item["last_ts_ms"]
        ):
            raise MarketDataEnvelopeBindingContractError(
                "source binding values are invalid"
            )
        symbols.add(symbol)
        normalized.append(copy.deepcopy(item))
    normalized.sort(key=lambda item: item["symbol"])
    if normalized != value:
        raise MarketDataEnvelopeBindingContractError(
            "source bindings must be sorted canonically"
        )
    first_values = {item["first_ts_ms"] for item in normalized}
    last_values = {item["last_ts_ms"] for item in normalized}
    row_counts = {item["row_count"] for item in normalized}
    if len(first_values) != 1 or len(last_values) != 1 or len(row_counts) != 1:
        raise MarketDataEnvelopeBindingContractError(
            "source bindings must declare one common observation grid"
        )
    return normalized


def build_market_data_envelope_binding_preregistration_v5(
    source_bindings: Any,
    *,
    expected_panel_hash: Any,
    expected_lineage_preregistration_v4_hash: Any,
) -> dict[str, Any]:
    bindings = _validate_source_bindings(source_bindings)
    if not _is_hash(expected_panel_hash) or not _is_hash(
        expected_lineage_preregistration_v4_hash
    ):
        raise MarketDataEnvelopeBindingContractError(
            "panel or lineage hash is invalid"
        )
    body = {
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PREREGISTERED_RESEARCH_ONLY",
        "envelope_schema_version": "market-data-envelope-v1",
        "envelope_timeframe": ENVELOPE_TIMEFRAME,
        "return_timeframe": RETURN_TIMEFRAME,
        "return_derivation": "SIMPLE_CLOSE_TO_CLOSE_RETURN",
        "return_decimals": RETURN_DECIMALS,
        "expected_panel_hash": expected_panel_hash,
        "expected_lineage_preregistration_v4_hash": (
            expected_lineage_preregistration_v4_hash
        ),
        "source_bindings": bindings,
        "facts": {
            "provider_identity_structurally_bound": True,
            "provider_identity_authenticated": False,
            "preregistration_chronology_independently_proven": False,
            "raw_rows_embedded": False,
            "current_activated": False,
        },
        "authority": _authority(),
    }
    return seal_strict_canonical_document(
        body,
        "binding_preregistration_v5_hash",
    )


def verify_market_data_envelope_binding_preregistration_v5(
    document: Any,
    *,
    expected_binding_preregistration_v5_hash: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        return _verification(
            PREREGISTRATION_VERIFICATION_SCHEMA_VERSION,
            ["market_data_binding_preregistration_object_required"],
            binding_preregistration_v5_hash=None,
        )
    if not _same_hash(
        document.get("binding_preregistration_v5_hash"),
        expected_binding_preregistration_v5_hash,
    ):
        blockers.append("market_data_binding_preregistration_hash_mismatch")
    try:
        rebuilt = build_market_data_envelope_binding_preregistration_v5(
            document.get("source_bindings"),
            expected_panel_hash=document.get("expected_panel_hash"),
            expected_lineage_preregistration_v4_hash=document.get(
                "expected_lineage_preregistration_v4_hash"
            ),
        )
        if not strict_json_contract_equal(document, rebuilt):
            blockers.append("market_data_binding_preregistration_contract_invalid")
    except Exception:
        blockers.append("market_data_binding_preregistration_contract_invalid")
    return _verification(
        PREREGISTRATION_VERIFICATION_SCHEMA_VERSION,
        blockers,
        binding_preregistration_v5_hash=(
            document.get("binding_preregistration_v5_hash")
            if not blockers
            else None
        ),
    )


def _seal_adapter(document: dict[str, Any]) -> dict[str, Any]:
    return seal_strict_canonical_document(document, "adapter_v5_hash")


def evaluate_market_data_envelope_binding_adapter_v5(
    binding_preregistration: Any,
    market_data_payloads: Any,
    lineage_preregistration: Any,
    consumer_preregistration: Any,
    source_preregistrations: Any,
    lineage_adapter_document: Any,
    consumer_document: Any,
    window_inputs: Any,
    *,
    expected_binding_preregistration_v5_hash: Any,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema_version": ADAPTER_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "UNKNOWN",
        "decision": "BLOCK_MARKET_DATA_ENVELOPE_BINDING_UNVERIFIED",
        "binding_preregistration_v5_hash": None,
        "panel_hash": None,
        "lineage_adapter_v4_hash": None,
        "first_blocking_tier": "MARKET_SOURCE",
        "tiers": [],
        "blockers": [],
        "source_summaries": [],
        "summary": None,
        "facts": {
            "market_data_envelopes_exactly_verified": False,
            "close_grid_exactly_aligned": False,
            "return_panel_derived_from_envelopes": False,
            "lineage_adapter_v4_exactly_verified": False,
            "provider_identity_structurally_bound": False,
            "provider_identity_authenticated": False,
            "raw_rows_embedded": False,
            "current_activated": False,
            "runtime_sources_accessed": False,
            "profitability_proven": False,
        },
        "authority": _authority(),
    }
    blockers: list[str] = []
    preregistration_receipt = verify_market_data_envelope_binding_preregistration_v5(
        binding_preregistration,
        expected_binding_preregistration_v5_hash=(
            expected_binding_preregistration_v5_hash
        ),
    )
    if preregistration_receipt["status"] != "PASS":
        blockers.append("market_data_binding_preregistration_invalid")
    try:
        panel, source_bindings = _verified_payloads(market_data_payloads)
    except Exception:
        panel, source_bindings = {}, []
        blockers.append("market_data_envelope_source_invalid")
    if not blockers:
        if (
            source_bindings != binding_preregistration["source_bindings"]
            or not _same_hash(
                panel.get("panel_hash"),
                binding_preregistration["expected_panel_hash"],
            )
            or not _same_hash(
                lineage_preregistration.get("lineage_preregistration_v4_hash")
                if type(lineage_preregistration) is dict
                else None,
                binding_preregistration[
                    "expected_lineage_preregistration_v4_hash"
                ],
            )
            or not _same_hash(
                lineage_preregistration.get("expected_panel_hash")
                if type(lineage_preregistration) is dict
                else None,
                panel["panel_hash"],
            )
        ):
            blockers.append("market_data_envelope_binding_mismatch")
    lineage_receipt = lineage_v4.verify_multi_window_return_panel_lineage_adapter_v4(
        lineage_adapter_document,
        lineage_preregistration,
        consumer_preregistration,
        source_preregistrations,
        panel,
        consumer_document,
        window_inputs,
        expected_lineage_preregistration_v4_hash=(
            binding_preregistration.get(
                "expected_lineage_preregistration_v4_hash"
            )
            if type(binding_preregistration) is dict
            else None
        ),
        strategy_id=strategy_id,
        variant_id=variant_id,
        lane=lane,
    )
    if (
        lineage_receipt.get("status") != "PASS"
        or lineage_receipt.get("adapter_status") not in {"PASS", "BLOCK"}
    ):
        blockers.append("return_panel_lineage_adapter_v4_exact_verification_failed")
    if blockers:
        base["blockers"] = sorted(set(blockers))
        base["tiers"] = [
            {"tier_id": "MARKET_SOURCE", "status": "BLOCK", "blockers": base["blockers"]},
            {"tier_id": "RETURN_PANEL_LINEAGE", "status": "NOT_EVALUATED", "blockers": []},
        ]
        return _seal_adapter(base)

    base["binding_preregistration_v5_hash"] = binding_preregistration[
        "binding_preregistration_v5_hash"
    ]
    base["panel_hash"] = panel["panel_hash"]
    base["lineage_adapter_v4_hash"] = lineage_adapter_document["adapter_v4_hash"]
    base["source_summaries"] = copy.deepcopy(source_bindings)
    base["summary"] = {
        "source_symbol_count": len(source_bindings),
        "common_close_row_count": source_bindings[0]["row_count"],
        "derived_return_row_count": panel["row_count"],
        "cutoff_date": panel["cutoff_date"],
        "lineage_adapter_status": lineage_receipt["adapter_status"],
        "conservative_effective_independent_ticket_count": (
            lineage_adapter_document["summary"][
                "conservative_effective_independent_ticket_count"
            ]
        ),
    }
    base["facts"].update(
        {
            "market_data_envelopes_exactly_verified": True,
            "close_grid_exactly_aligned": True,
            "return_panel_derived_from_envelopes": True,
            "lineage_adapter_v4_exactly_verified": True,
            "provider_identity_structurally_bound": True,
        }
    )
    lineage_blocked = lineage_receipt["adapter_status"] == "BLOCK"
    base.update(
        {
            "status": "BLOCK" if lineage_blocked else "PASS",
            "decision": (
                "BLOCK_MARKET_DATA_ENVELOPE_LINEAGE_ADAPTER_V5"
                if lineage_blocked
                else "PASS_MARKET_DATA_ENVELOPE_BINDING_RESEARCH_ADAPTER_V5"
            ),
            "first_blocking_tier": (
                "RETURN_PANEL_LINEAGE" if lineage_blocked else None
            ),
            "blockers": ["lineage_adapter_v4_blocked"] if lineage_blocked else [],
            "tiers": [
                {"tier_id": "MARKET_SOURCE", "status": "PASS", "blockers": []},
                {
                    "tier_id": "RETURN_PANEL_LINEAGE",
                    "status": "BLOCK" if lineage_blocked else "PASS",
                    "blockers": ["lineage_adapter_v4_blocked"] if lineage_blocked else [],
                },
            ],
        }
    )
    return _seal_adapter(base)


def verify_market_data_envelope_binding_adapter_v5(
    document: Any,
    binding_preregistration: Any,
    market_data_payloads: Any,
    lineage_preregistration: Any,
    consumer_preregistration: Any,
    source_preregistrations: Any,
    lineage_adapter_document: Any,
    consumer_document: Any,
    window_inputs: Any,
    *,
    expected_binding_preregistration_v5_hash: Any,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
) -> dict[str, Any]:
    try:
        expected = evaluate_market_data_envelope_binding_adapter_v5(
            binding_preregistration,
            market_data_payloads,
            lineage_preregistration,
            consumer_preregistration,
            source_preregistrations,
            lineage_adapter_document,
            consumer_document,
            window_inputs,
            expected_binding_preregistration_v5_hash=(
                expected_binding_preregistration_v5_hash
            ),
            strategy_id=strategy_id,
            variant_id=variant_id,
            lane=lane,
        )
        exact = type(document) is dict and strict_json_contract_equal(document, expected)
    except Exception:
        expected = {}
        exact = False
    return _verification(
        ADAPTER_VERIFICATION_SCHEMA_VERSION,
        [] if exact else ["market_data_envelope_binding_adapter_v5_contract_invalid"],
        adapter_status=expected.get("status") if exact else "UNKNOWN",
        adapter_decision=expected.get("decision") if exact else "UNKNOWN",
        adapter_v5_hash=expected.get("adapter_v5_hash") if exact else None,
    )


__all__ = [
    "ADAPTER_SCHEMA_VERSION",
    "MarketDataEnvelopeBindingContractError",
    "PREREGISTRATION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_market_data_envelope_binding_preregistration_v5",
    "derive_common_return_panel_from_market_data_envelopes_v5",
    "evaluate_market_data_envelope_binding_adapter_v5",
    "market_data_envelope_source_bindings_v5",
    "verify_market_data_envelope_binding_adapter_v5",
    "verify_market_data_envelope_binding_preregistration_v5",
]
