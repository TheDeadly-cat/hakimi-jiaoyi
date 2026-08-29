from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .strategy_correlation_cluster_multi_window_market_data_envelope_binding_adapter_v5 import (
    ADAPTER_SCHEMA_VERSION as ADAPTER_V5_SCHEMA_VERSION,
    derive_common_return_panel_from_market_data_envelopes_v5,
    market_data_envelope_source_bindings_v5,
    verify_market_data_envelope_binding_adapter_v5,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from .strict_governance_primitives import strict_sha256


PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-multi-window-market-data-common-cutoff-"
    "preregistration-v6"
)
GATE_SCHEMA_VERSION = (
    "strategy-correlation-cluster-multi-window-market-data-common-cutoff-gate-v6"
)
GATE_VERIFICATION_SCHEMA_VERSION = f"{GATE_SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = (
    "20260825-correlation-cluster-multi-window-common-cutoff-v6-lock-1"
)
POLICY_ID = "CORRELATION_CLUSTER_MULTI_WINDOW_COMMON_NATIVE_CUTOFF_V1"
CUTOFF_SEMANTICS = (
    "LAST_COMPLETED_ENVELOPE_ROW_TS_MS_NOT_FRESHNESS_SESSION_CLOSE_OR_INGESTION"
)
REQUIRED_WINDOW_LENGTHS = (20, 60, 120)

_V5_CONTEXT_KEYS = frozenset(
    {
        "binding_preregistration",
        "market_data_payloads",
        "lineage_preregistration",
        "consumer_preregistration",
        "source_preregistrations",
        "lineage_adapter_document",
        "consumer_document",
        "window_inputs",
        "expected_binding_preregistration_v5_hash",
        "strategy_id",
        "variant_id",
        "lane",
    }
)


class MarketDataCommonCutoffContractError(ValueError):
    pass


def _dict(value: Any) -> dict[str, Any]:
    return value if type(value) is dict else {}


def _list(value: Any) -> list[Any]:
    return value if type(value) is list else []


def _utc_date_from_ms(value: Any) -> str | None:
    if type(value) is not int or value <= 0:
        return None
    try:
        return datetime.fromtimestamp(value / 1000, timezone.utc).date().isoformat()
    except (OSError, OverflowError, ValueError):
        return None


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "writer_allowed": False,
        "runtime_gate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "formal_registry_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _check(name: str, ok: bool, passed: str, failed: str) -> dict[str, Any]:
    return {
        "name": name,
        "ok": bool(ok),
        "blocking": True,
        "detail": passed if ok else failed,
    }


def _validated_symbols(value: Any) -> list[str]:
    if (
        type(value) is not list
        or len(value) < 2
        or any(
            type(item) is not str
            or not item
            or item != item.strip().upper()
            for item in value
        )
        or value != sorted(set(value))
    ):
        raise MarketDataCommonCutoffContractError("expected_symbols_invalid")
    return list(value)


def _validated_provider_bindings(
    value: Any,
    symbols: list[str],
) -> list[dict[str, str]]:
    if type(value) is not list or len(value) != len(symbols):
        raise MarketDataCommonCutoffContractError(
            "expected_provider_bindings_invalid"
        )
    bindings: list[dict[str, str]] = []
    for item in value:
        if type(item) is not dict or set(item) != {"symbol", "provider"}:
            raise MarketDataCommonCutoffContractError(
                "expected_provider_binding_shape_invalid"
            )
        symbol = item.get("symbol")
        provider = item.get("provider")
        if (
            type(symbol) is not str
            or symbol != symbol.strip().upper()
            or not symbol
            or type(provider) is not str
            or provider != provider.strip()
            or not provider
            or provider.lower() == "unknown"
        ):
            raise MarketDataCommonCutoffContractError(
                "expected_provider_binding_value_invalid"
            )
        bindings.append({"symbol": symbol, "provider": provider})
    if [item["symbol"] for item in bindings] != symbols:
        raise MarketDataCommonCutoffContractError(
            "expected_provider_binding_symbol_set_invalid"
        )
    return bindings


def build_market_data_common_cutoff_preregistration_v6(
    *,
    expected_symbols: Any,
    expected_provider_bindings: Any,
    expected_timeframe: Any,
    expected_observation_cutoff_ts_ms: Any,
    expected_close_row_count: Any,
    expected_return_row_count: Any,
    required_window_lengths: Any,
) -> dict[str, Any]:
    symbols = _validated_symbols(expected_symbols)
    provider_bindings = _validated_provider_bindings(
        expected_provider_bindings,
        symbols,
    )
    if (
        type(expected_timeframe) is not str
        or not expected_timeframe
        or expected_timeframe != expected_timeframe.strip().upper()
    ):
        raise MarketDataCommonCutoffContractError("expected_timeframe_invalid")
    if (
        type(expected_observation_cutoff_ts_ms) is not int
        or expected_observation_cutoff_ts_ms <= 0
        or _utc_date_from_ms(expected_observation_cutoff_ts_ms) is None
    ):
        raise MarketDataCommonCutoffContractError(
            "expected_observation_cutoff_ts_ms_invalid"
        )
    if (
        type(expected_close_row_count) is not int
        or type(expected_return_row_count) is not int
        or expected_close_row_count < max(REQUIRED_WINDOW_LENGTHS) + 1
        or expected_return_row_count != expected_close_row_count - 1
    ):
        raise MarketDataCommonCutoffContractError("expected_row_counts_invalid")
    if (
        type(required_window_lengths) is not list
        or required_window_lengths != list(REQUIRED_WINDOW_LENGTHS)
    ):
        raise MarketDataCommonCutoffContractError(
            "required_window_lengths_invalid"
        )

    document = {
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PREREGISTERED_RESEARCH_ONLY",
        "policy_id": POLICY_ID,
        "cutoff_semantics": CUTOFF_SEMANTICS,
        "expected": {
            "symbols": symbols,
            "provider_bindings": provider_bindings,
            "timeframe": expected_timeframe,
            "observation_cutoff_ts_ms": expected_observation_cutoff_ts_ms,
            "observation_cutoff_utc_date": _utc_date_from_ms(
                expected_observation_cutoff_ts_ms
            ),
            "close_row_count": expected_close_row_count,
            "return_row_count": expected_return_row_count,
            "required_window_lengths": list(REQUIRED_WINDOW_LENGTHS),
        },
        "facts": {
            "common_cutoff_policy_defined": True,
            "common_cutoff_evaluated": False,
            "cutoff_declared_independently_from_gate_evaluation": True,
            "external_preregistration_time_authenticated": False,
            "freshness_policy_defined": False,
            "provider_identity_authenticated": False,
            "provider_dataset_content_attested": False,
            "runtime_consumer_bound": False,
        },
        "authority": _authority(),
    }
    return seal_strict_canonical_document(
        document,
        "common_cutoff_preregistration_v6_hash",
    )


def verify_market_data_common_cutoff_preregistration_v6(
    document: Any,
    *,
    expected_common_cutoff_preregistration_v6_hash: Any,
) -> dict[str, Any]:
    exact = False
    if (
        type(document) is dict
        and strict_sha256(expected_common_cutoff_preregistration_v6_hash)
        and document.get("common_cutoff_preregistration_v6_hash")
        == expected_common_cutoff_preregistration_v6_hash
    ):
        try:
            expected = _dict(document.get("expected"))
            rebuilt = build_market_data_common_cutoff_preregistration_v6(
                expected_symbols=expected.get("symbols"),
                expected_provider_bindings=expected.get("provider_bindings"),
                expected_timeframe=expected.get("timeframe"),
                expected_observation_cutoff_ts_ms=expected.get(
                    "observation_cutoff_ts_ms"
                ),
                expected_close_row_count=expected.get("close_row_count"),
                expected_return_row_count=expected.get("return_row_count"),
                required_window_lengths=expected.get("required_window_lengths"),
            )
            exact = strict_json_contract_equal(document, rebuilt)
        except (
            AttributeError,
            KeyError,
            TypeError,
            ValueError,
            OverflowError,
        ):
            exact = False
    return {
        "schema_version": f"{PREREGISTRATION_SCHEMA_VERSION}-verification-v1",
        "status": "PASS" if exact else "BLOCK",
        "blockers": [] if exact else ["common_cutoff_preregistration_mismatch"],
        "preregistration_exactly_verified": exact,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _verify_adapter_v5(document: Any, context: Any) -> tuple[bool, dict[str, Any]]:
    if (
        type(document) is not dict
        or document.get("schema_version") != ADAPTER_V5_SCHEMA_VERSION
        or document.get("status") != "PASS"
        or type(context) is not dict
        or set(context) != _V5_CONTEXT_KEYS
    ):
        return False, {}
    try:
        verification = verify_market_data_envelope_binding_adapter_v5(
            document,
            context["binding_preregistration"],
            context["market_data_payloads"],
            context["lineage_preregistration"],
            context["consumer_preregistration"],
            context["source_preregistrations"],
            context["lineage_adapter_document"],
            context["consumer_document"],
            context["window_inputs"],
            expected_binding_preregistration_v5_hash=context[
                "expected_binding_preregistration_v5_hash"
            ],
            strategy_id=context["strategy_id"],
            variant_id=context["variant_id"],
            lane=context["lane"],
        )
    except (
        ArithmeticError,
        AttributeError,
        IndexError,
        KeyError,
        TypeError,
        ValueError,
        OverflowError,
    ):
        return False, {}
    exact = bool(
        type(verification) is dict
        and verification.get("status") == "PASS"
        and not _list(verification.get("blockers"))
    )
    return exact, verification if exact else {}


def evaluate_market_data_common_cutoff_gate_v6(
    preregistration: Any,
    adapter_v5_document: Any,
    adapter_v5_context: Any,
    *,
    expected_common_cutoff_preregistration_v6_hash: Any,
) -> dict[str, Any]:
    preregistration_verification = (
        verify_market_data_common_cutoff_preregistration_v6(
            preregistration,
            expected_common_cutoff_preregistration_v6_hash=(
                expected_common_cutoff_preregistration_v6_hash
            ),
        )
    )
    preregistration_ok = preregistration_verification.get("status") == "PASS"
    adapter_v5_ok, _ = _verify_adapter_v5(
        adapter_v5_document,
        adapter_v5_context,
    )

    expected = _dict(_dict(preregistration).get("expected"))
    symbols = _list(expected.get("symbols")) if preregistration_ok else []
    expected_provider_bindings = (
        _list(expected.get("provider_bindings")) if preregistration_ok else []
    )
    expected_timeframe = expected.get("timeframe") if preregistration_ok else None
    expected_cutoff = (
        expected.get("observation_cutoff_ts_ms") if preregistration_ok else None
    )
    expected_close_rows = (
        expected.get("close_row_count") if preregistration_ok else None
    )
    expected_return_rows = (
        expected.get("return_row_count") if preregistration_ok else None
    )
    required_windows = (
        _list(expected.get("required_window_lengths"))
        if preregistration_ok
        else []
    )

    payloads: dict[str, Any] = {}
    source_bindings: list[dict[str, Any]] = []
    panel: dict[str, Any] = {}
    if adapter_v5_ok:
        payloads = _dict(_dict(adapter_v5_context).get("market_data_payloads"))
        try:
            source_bindings = market_data_envelope_source_bindings_v5(payloads)
            panel = derive_common_return_panel_from_market_data_envelopes_v5(
                payloads
            )
        except (
            ArithmeticError,
            AttributeError,
            IndexError,
            KeyError,
            TypeError,
            ValueError,
            OverflowError,
        ):
            source_bindings = []
            panel = {}

    symbol_set_ok = bool(
        preregistration_ok
        and adapter_v5_ok
        and set(payloads) == set(symbols)
        and len(payloads) == len(symbols)
    )
    binding_by_symbol = {
        item.get("symbol"): item
        for item in source_bindings
        if type(item) is dict and type(item.get("symbol")) is str
    }
    expected_provider_by_symbol = {
        item.get("symbol"): item.get("provider")
        for item in expected_provider_bindings
        if type(item) is dict
    }

    source_binding_ok = bool(
        symbol_set_ok
        and len(binding_by_symbol) == len(symbols)
        and strict_json_contract_equal(
            _dict(adapter_v5_document).get("source_summaries"),
            source_bindings,
        )
    )
    provider_binding_ok = source_binding_ok
    timeframe_ok = symbol_set_ok
    close_row_count_ok = symbol_set_ok
    completed_rows_ok = symbol_set_ok
    timestamp_order_ok = symbol_set_ok
    grids: list[list[int]] = []
    dataset_summaries: list[dict[str, Any]] = []

    if symbol_set_ok:
        for symbol in symbols:
            payload = _dict(payloads.get(symbol))
            envelope = _dict(payload.get("market_data_envelope"))
            rows = _list(payload.get("rows"))
            binding = _dict(binding_by_symbol.get(symbol))
            provider = binding.get("provider")
            timestamps: list[int] = []
            rows_valid = len(rows) == expected_close_rows
            rows_complete = rows_valid
            for row in rows:
                if (
                    type(row) is not dict
                    or type(row.get("ts_ms")) is not int
                    or row.get("ts_ms") <= 0
                ):
                    rows_valid = False
                    rows_complete = False
                    continue
                timestamps.append(row["ts_ms"])
                if row.get("complete") is not True:
                    rows_complete = False
            order_valid = bool(
                rows_valid
                and timestamps == sorted(timestamps)
                and len(set(timestamps)) == len(timestamps)
            )
            provider_binding_ok = bool(
                provider_binding_ok
                and provider == expected_provider_by_symbol.get(symbol)
                and strict_sha256(binding.get("dataset_hash"))
                and binding.get("row_count") == expected_close_rows
            )
            timeframe_ok = bool(
                timeframe_ok and envelope.get("timeframe") == expected_timeframe
            )
            close_row_count_ok = bool(close_row_count_ok and rows_valid)
            completed_rows_ok = bool(completed_rows_ok and rows_complete)
            timestamp_order_ok = bool(timestamp_order_ok and order_valid)
            if order_valid:
                grids.append(timestamps)
                dataset_summaries.append(
                    {
                        "symbol": symbol,
                        "provider": provider,
                        "dataset_hash": binding.get("dataset_hash"),
                        "close_row_count": len(timestamps),
                        "first_ts_ms": timestamps[0],
                        "last_ts_ms": timestamps[-1],
                    }
                )

    common_grid: list[int] = []
    common_grid_ok = bool(
        timestamp_order_ok
        and len(grids) == len(symbols)
        and grids
        and all(grid == grids[0] for grid in grids[1:])
    )
    if common_grid_ok:
        common_grid = grids[0]
    common_cutoff_ok = bool(
        common_grid_ok
        and common_grid[-1] == expected_cutoff
        and _utc_date_from_ms(common_grid[-1])
        == expected.get("observation_cutoff_utc_date")
    )
    return_capacity_ok = bool(
        preregistration_ok
        and expected_return_rows == expected_close_rows - 1
        and required_windows == list(REQUIRED_WINDOW_LENGTHS)
        and max(required_windows) <= expected_return_rows
    )
    panel_ok = bool(
        adapter_v5_ok
        and panel.get("status") == "PASS"
        and panel.get("row_count") == expected_return_rows
        and type(panel.get("timeframe")) is str
        and type(expected_timeframe) is str
        and panel.get("timeframe").upper() == expected_timeframe
        and panel.get("cutoff_date")
        == expected.get("observation_cutoff_utc_date")
        and panel.get("symbols") == symbols
        and strict_sha256(panel.get("panel_hash"))
        and panel.get("panel_hash")
        == _dict(adapter_v5_document).get("panel_hash")
        == _dict(_dict(adapter_v5_context).get("binding_preregistration")).get(
            "expected_panel_hash"
        )
    )

    checks = [
        _check(
            "common_cutoff_preregistration_exact",
            preregistration_ok,
            "Common cutoff preregistration exactly verifies.",
            "Common cutoff preregistration is invalid or mismatched.",
        ),
        _check(
            "adapter_v5_exact",
            adapter_v5_ok,
            "Market-data envelope binding adapter v5 exactly verifies.",
            "Market-data envelope binding adapter v5 is invalid or mismatched.",
        ),
        _check(
            "symbol_set_exact",
            symbol_set_ok,
            "Envelope symbols exactly match preregistration.",
            "Envelope symbols differ from preregistration.",
        ),
        _check(
            "source_binding_exact",
            source_binding_ok,
            "Adapter source summaries exactly match recomputed bindings.",
            "Adapter source summaries cannot be exactly recomputed.",
        ),
        _check(
            "provider_binding_exact",
            provider_binding_ok,
            "Providers exactly match preregistered symbol bindings.",
            "Provider bindings differ from preregistration.",
        ),
        _check(
            "envelope_timeframe_exact",
            timeframe_ok,
            "Every envelope uses the preregistered timeframe.",
            "Envelope timeframe differs from preregistration.",
        ),
        _check(
            "completed_close_row_count_exact",
            close_row_count_ok and completed_rows_ok,
            "Every symbol has the exact completed close-row count.",
            "Close-row count or completion state is invalid.",
        ),
        _check(
            "common_timestamp_grid_exact",
            common_grid_ok,
            "Every symbol has the same strictly increasing timestamp grid.",
            "Timestamp grids are invalid or differ across symbols.",
        ),
        _check(
            "common_native_cutoff_exact",
            common_cutoff_ok,
            "Every symbol ends at the independently preregistered cutoff.",
            "Last completed timestamp differs from preregistered cutoff.",
        ),
        _check(
            "return_panel_cutoff_exact",
            panel_ok and return_capacity_ok,
            "Derived return panel preserves cutoff and 20/60/120 capacity.",
            "Return panel cutoff, row count, or window capacity is invalid.",
        ),
    ]
    blockers = [item["name"] for item in checks if item["ok"] is not True]
    status = "PASS" if not blockers else "UNKNOWN"
    observed_cutoff = common_grid[-1] if common_grid else None
    document = {
        "schema_version": GATE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "decision": (
            "PASS_COMMON_NATIVE_CUTOFF_BOUND_RESEARCH_GATE_V6"
            if status == "PASS"
            else "UNKNOWN_COMMON_NATIVE_CUTOFF_UNVERIFIED"
        ),
        "source": {
            "common_cutoff_preregistration_v6_hash": (
                _dict(preregistration).get(
                    "common_cutoff_preregistration_v6_hash"
                )
                if preregistration_ok
                else None
            ),
            "adapter_v5_hash": (
                _dict(adapter_v5_document).get("adapter_v5_hash")
                if adapter_v5_ok
                else None
            ),
            "binding_preregistration_v5_hash": (
                _dict(adapter_v5_document).get(
                    "binding_preregistration_v5_hash"
                )
                if adapter_v5_ok
                else None
            ),
            "lineage_adapter_v4_hash": (
                _dict(adapter_v5_document).get("lineage_adapter_v4_hash")
                if adapter_v5_ok
                else None
            ),
            "panel_hash": panel.get("panel_hash") if panel_ok else None,
        },
        "cutoff": {
            "expected_observation_cutoff_ts_ms": (
                expected_cutoff if preregistration_ok else None
            ),
            "observed_common_cutoff_ts_ms": observed_cutoff,
            "expected_observation_cutoff_utc_date": (
                expected.get("observation_cutoff_utc_date")
                if preregistration_ok
                else None
            ),
            "observed_common_cutoff_utc_date": _utc_date_from_ms(
                observed_cutoff
            ),
            "cutoff_semantics": CUTOFF_SEMANTICS,
            "timeframe": expected_timeframe,
            "close_row_count": expected_close_rows,
            "return_row_count": expected_return_rows,
            "required_window_lengths": required_windows,
            "common_timestamp_grid_hash": (
                strict_canonical_hash(common_grid) if common_grid else None
            ),
        },
        "datasets": dataset_summaries,
        "checks": checks,
        "blockers": blockers,
        "facts": {
            "common_cutoff_preregistered": preregistration_ok,
            "adapter_v5_exactly_verified": adapter_v5_ok,
            "common_timestamp_grid_recomputed": common_grid_ok,
            "all_rows_complete": completed_rows_ok,
            "provider_bindings_match_preregistration": provider_binding_ok,
            "common_native_cutoff_matches_preregistration": common_cutoff_ok,
            "return_panel_cutoff_recomputed": panel_ok,
            "freshness_policy_defined": False,
            "freshness_evaluated": False,
            "external_preregistration_time_authenticated": False,
            "provider_identity_authenticated": False,
            "provider_dataset_content_attested": False,
            "raw_rows_embedded": False,
            "runtime_assets_accessed": False,
            "runtime_consumer_bound": False,
        },
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "common_cutoff_gate_v6_hash")


def verify_market_data_common_cutoff_gate_v6(
    document: Any,
    preregistration: Any,
    adapter_v5_document: Any,
    adapter_v5_context: Any,
    *,
    expected_common_cutoff_preregistration_v6_hash: Any,
) -> dict[str, Any]:
    expected = evaluate_market_data_common_cutoff_gate_v6(
        preregistration,
        adapter_v5_document,
        adapter_v5_context,
        expected_common_cutoff_preregistration_v6_hash=(
            expected_common_cutoff_preregistration_v6_hash
        ),
    )
    exact = strict_json_contract_equal(document, expected)
    return {
        "schema_version": GATE_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "blockers": [] if exact else ["common_cutoff_gate_exact_rebuild_mismatch"],
        "gate_decision": expected["decision"] if exact else "UNKNOWN",
        "gate_exactly_verified": exact,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "CUTOFF_SEMANTICS",
    "GATE_SCHEMA_VERSION",
    "GATE_VERIFICATION_SCHEMA_VERSION",
    "MarketDataCommonCutoffContractError",
    "POLICY_ID",
    "PREREGISTRATION_SCHEMA_VERSION",
    "REQUIRED_WINDOW_LENGTHS",
    "STATIC_FINGERPRINT",
    "build_market_data_common_cutoff_preregistration_v6",
    "evaluate_market_data_common_cutoff_gate_v6",
    "verify_market_data_common_cutoff_gate_v6",
    "verify_market_data_common_cutoff_preregistration_v6",
]
