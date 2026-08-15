from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction
from typing import Any

from .instrument_rules import (
    public_instrument_rules_placeholder,
    verify_public_instrument_rules,
)
from .public_order_book import (
    build_public_order_book_microstructure,
    public_order_book_placeholder,
    verify_public_order_book,
)


SCHEMA = "small-capital-planning-v3"
MODE = "PLAN_ONLY_NO_EXECUTION"
QUANTITY_PREVIEW_SCHEMA = "small-capital-quantity-preview-v2"
QUANTITY_PREVIEW_MODE = "GROSS_QUOTE_TO_BASE_ESTIMATE_ONLY"
OKX_MARKET_RISK_CHECK_BUFFER_RATE = Decimal("0.05")
DEPTH_PREVIEW_SCHEMA = "small-capital-order-book-impact-v1"
DEPTH_PREVIEW_MODE = "VISIBLE_ASK_DEPTH_REFERENCE_ONLY"


def _canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _positive_decimal(value: Any) -> Decimal | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or len(text) > 128 or "e" in text.lower():
        return None
    try:
        parsed = Decimal(text)
    except InvalidOperation:
        return None
    return parsed if parsed.is_finite() and parsed > 0 else None


def _floor_decimal_ratio(numerator: Decimal, denominator: Decimal) -> int:
    numerator_value, numerator_scale = numerator.as_integer_ratio()
    denominator_value, denominator_scale = denominator.as_integer_ratio()
    return (numerator_value * denominator_scale) // (numerator_scale * denominator_value)


def _ceil_decimal_ratio(numerator: Decimal, denominator: Decimal) -> int:
    numerator_value, numerator_scale = numerator.as_integer_ratio()
    denominator_value, denominator_scale = denominator.as_integer_ratio()
    top = numerator_value * denominator_scale
    bottom = numerator_scale * denominator_value
    return (top + bottom - 1) // bottom


def _floor_decimal_over_product(
    numerator: Decimal,
    first_denominator: Decimal,
    second_denominator: Decimal,
) -> int:
    numerator_value, numerator_scale = numerator.as_integer_ratio()
    first_value, first_scale = first_denominator.as_integer_ratio()
    second_value, second_scale = second_denominator.as_integer_ratio()
    top = numerator_value * first_scale * second_scale
    bottom = numerator_scale * first_value * second_value
    return top // bottom


def _decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _fraction(value: Decimal) -> Fraction:
    numerator, denominator = value.as_integer_ratio()
    return Fraction(numerator, denominator)


def _fraction_text(value: Fraction, *, places: int = 24) -> str:
    with localcontext() as context:
        context.prec = max(places + 40, 96)
        decimal_value = Decimal(value.numerator) / Decimal(value.denominator)
        quantum = Decimal(1).scaleb(-places)
        if decimal_value.as_tuple().exponent < -places:
            decimal_value = decimal_value.quantize(quantum)
    return _decimal_text(decimal_value)


def _finite_fraction_text(value: Fraction) -> str:
    numerator = value.numerator
    denominator = value.denominator
    twos = 0
    fives = 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    if denominator != 1:
        raise ArithmeticError("fraction_is_not_a_finite_decimal")
    places = max(twos, fives)
    scaled = numerator * (2 ** (places - twos)) * (5 ** (places - fives))
    sign = "-" if scaled < 0 else ""
    digits = str(abs(scaled)).rjust(places + 1, "0")
    if places == 0:
        return f"{sign}{digits}"
    return f"{sign}{digits[:-places]}.{digits[-places:]}".rstrip("0").rstrip(".")


def _depth_preview_base(*, symbol: str, status: str, blockers: list[str]) -> dict[str, Any]:
    return {
        "schema_version": DEPTH_PREVIEW_SCHEMA,
        "mode": DEPTH_PREVIEW_MODE,
        "status": status,
        "symbol": symbol,
        "budget_basis": {
            "amounts": ["10", "20"],
            "currency": "USDT",
            "usd_equivalence_verified": False,
        },
        "evidence": {
            "book_snapshot_id": "",
            "book_hash": "",
            "book_contract_hash": "",
            "source": "",
            "endpoint": "",
            "exchange_timestamp_ms": 0,
            "observed_at_ms": 0,
            "depth_requested": 0,
            "observed_ask_levels": 0,
            "liquidity_scope": "STANDARD_BOOK_NON_RPI",
            "checksum_policy": "NOT_APPLICABLE",
            "complete_book_verified": False,
            "same_snapshot_as_ticker": False,
            "is_executable_quote": False,
            "hash_verified": False,
        },
        "rule_binding": {
            "rules_hash": "",
            "snapshot_hash": "",
            "lot_size": "",
            "minimum_order_size": "",
            "base_currency": "",
            "quote_currency": "",
        },
        "display_precision": {
            "quantity_price_cost": "EXACT_FINITE_DECIMAL",
            "coverage_ratio_places": 12,
            "vwap_places": 12,
            "impact_bps_places": 8,
        },
        "rows": [],
        "unknowns": {
            "complete_order_book": "NOT_CHECKED",
            "rpi_access": "NOT_CHECKED",
            "hidden_liquidity": "NOT_CHECKED",
            "queue_position": "NOT_CHECKED",
            "account_balance": "NOT_CHECKED",
            "account_fee": "NOT_CHECKED",
            "slippage": "NOT_CHECKED",
            "minimum_cost": "NOT_CHECKED",
            "arrival_latency": "NOT_CHECKED",
            "actual_fill": "NOT_CHECKED",
            "usd_usdt_conversion": "NOT_CHECKED",
        },
        "permissions": {
            "planning_only": True,
            "order_submission_allowed": False,
            "execution_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "execution_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "blockers": list(dict.fromkeys(blockers)),
    }


def _finalize_depth_preview(preview: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(preview)
    sealed["preview_hash"] = _canonical_hash(sealed)
    sealed["hash_verified"] = True
    return sealed


def build_small_capital_depth_preview(
    *,
    symbol: str,
    market_truth: dict[str, Any],
    instrument_rules: dict[str, Any],
    instrument_status: str,
    order_book: dict[str, Any],
    order_book_status: str,
) -> dict[str, Any]:
    if instrument_rules.get("status") == "NOT_APPLICABLE" or order_book.get("status") == "NOT_APPLICABLE":
        return _finalize_depth_preview(_depth_preview_base(
            symbol=symbol,
            status="NOT_APPLICABLE",
            blockers=["public_spot_depth_not_applicable"],
        ))
    if instrument_status == "BLOCK" or order_book_status == "BLOCK":
        return _finalize_depth_preview(_depth_preview_base(
            symbol=symbol,
            status="BLOCK",
            blockers=["public_order_book_contract_blocked"],
        ))
    if instrument_status != "PASS" or order_book_status != "PASS" or market_truth.get("research_usable") is not True:
        return _finalize_depth_preview(_depth_preview_base(
            symbol=symbol,
            status="NOT_CHECKED",
            blockers=["public_order_book_not_verified"],
        ))

    asks = order_book.get("asks") if isinstance(order_book.get("asks"), list) else []
    lot_size = _positive_decimal(instrument_rules.get("lot_size"))
    minimum_size = _positive_decimal(instrument_rules.get("minimum_order_size"))
    if (
        order_book.get("symbol") != symbol
        or order_book.get("status") != "VERIFIED"
        or order_book.get("planning_usable") is not True
        or order_book.get("liquidity_scope") != "STANDARD_BOOK_NON_RPI"
        or order_book.get("checksum_policy") != "NOT_APPLICABLE"
        or order_book.get("contract_hash_verified") is not True
        or order_book.get("complete_book_verified") is not False
        or order_book.get("is_executable_quote") is not False
        or len(asks) < 2
        or lot_size is None
        or minimum_size is None
        or instrument_rules.get("size_unit") != symbol.rsplit("-", 1)[0]
        or instrument_rules.get("price_unit") != "USDT"
    ):
        return _finalize_depth_preview(_depth_preview_base(
            symbol=symbol,
            status="BLOCK",
            blockers=["public_order_book_binding_invalid"],
        ))

    try:
        ask_levels = [
            (_fraction(_positive_decimal(row.get("price")) or Decimal(0)),
             _fraction(_positive_decimal(row.get("size")) or Decimal(0)))
            for row in asks
        ]
        if any(price <= 0 or size <= 0 for price, size in ask_levels):
            raise ArithmeticError("public_order_book_level_invalid")
        lot_fraction = _fraction(lot_size)
        minimum_fraction = _fraction(minimum_size)
        best_ask = ask_levels[0][0]
        rows: list[dict[str, Any]] = []
        all_minimum_met = True
        all_budgets_covered = True
        for budget_text in ("10", "20"):
            budget = Fraction(int(budget_text), 1)
            remaining_quote = budget
            visible_base = Fraction(0, 1)
            visible_quote = Fraction(0, 1)
            visible_levels_used = 0
            last_visible_price = best_ask
            for price, size in ask_levels:
                level_quote = price * size
                take_quote = min(remaining_quote, level_quote)
                if take_quote <= 0:
                    break
                visible_base += take_quote / price
                visible_quote += take_quote
                remaining_quote -= take_quote
                visible_levels_used += 1
                last_visible_price = price
                if remaining_quote == 0:
                    break
            lot_steps = (visible_base / lot_fraction).numerator // (visible_base / lot_fraction).denominator
            quantity_floor = Fraction(lot_steps, 1) * lot_fraction
            remaining_base = quantity_floor
            reference_cost = Fraction(0, 1)
            levels_used = 0
            last_consumed_price = best_ask
            for price, size in ask_levels:
                take_base = min(remaining_base, size)
                if take_base <= 0:
                    break
                reference_cost += take_base * price
                remaining_base -= take_base
                levels_used += 1
                last_consumed_price = price
                if remaining_base == 0:
                    break
            depth_covers_budget = remaining_quote == 0
            minimum_met = quantity_floor >= minimum_fraction
            within_budget = reference_cost <= budget and remaining_base == 0
            if lot_steps < 0 or not within_budget:
                raise ArithmeticError("public_order_book_depth_postcondition_failed")
            vwap = reference_cost / quantity_floor if quantity_floor > 0 else Fraction(0, 1)
            impact_bps = (vwap / best_ask - 1) * 10_000 if vwap > 0 else Fraction(0, 1)
            coverage_ratio = visible_quote / budget
            unallocated_after_lot = budget - reference_cost
            all_minimum_met = all_minimum_met and minimum_met
            all_budgets_covered = all_budgets_covered and depth_covers_budget
            rows.append({
                "budget_quote_amount": budget_text,
                "quantity_floor": _finite_fraction_text(quantity_floor),
                "quantity_unit": str(instrument_rules.get("size_unit") or ""),
                "lot_steps": str(lot_steps),
                "visible_reference_cost": _finite_fraction_text(reference_cost),
                "visible_depth_quote": _finite_fraction_text(visible_quote),
                "visible_depth_shortfall_quote": _finite_fraction_text(remaining_quote),
                "unallocated_after_lot_floor": _finite_fraction_text(unallocated_after_lot),
                "coverage_ratio": _fraction_text(coverage_ratio, places=12),
                "visible_vwap_reference": _fraction_text(vwap, places=12) if vwap > 0 else "",
                "best_ask_reference": _finite_fraction_text(best_ask),
                "last_consumed_price": _finite_fraction_text(last_consumed_price),
                "impact_bps": _fraction_text(impact_bps, places=8),
                "levels_used": levels_used,
                "visible_levels_scanned": visible_levels_used,
                "observed_depth_covers_budget": depth_covers_budget,
                "minimum_order_size_met": minimum_met,
                "within_quote_budget": within_budget,
                "fees_included": False,
                "account_balance_checked": False,
                "complete_book_verified": False,
                "executable": False,
            })
    except (ArithmeticError, InvalidOperation, ZeroDivisionError, ValueError):
        return _finalize_depth_preview(_depth_preview_base(
            symbol=symbol,
            status="BLOCK",
            blockers=["public_order_book_depth_calculation_invalid"],
        ))

    status = (
        "BELOW_MIN_SIZE"
        if not all_minimum_met
        else "VISIBLE_DEPTH_CAPACITY_LIMITED"
        if not all_budgets_covered
        else "DEPTH_PREVIEW_ONLY"
    )
    preview = _depth_preview_base(
        symbol=symbol,
        status=status,
        blockers=(
            ["one_or_more_depth_tiers_below_public_minimum_size"]
            if not all_minimum_met
            else ["visible_order_book_does_not_cover_all_budgets"]
            if not all_budgets_covered
            else []
        ),
    )
    source = order_book.get("source") if isinstance(order_book.get("source"), dict) else {}
    preview["evidence"] = {
        "book_snapshot_id": str(order_book.get("snapshot_id") or ""),
        "book_hash": str(order_book.get("book_hash") or ""),
        "book_contract_hash": str(order_book.get("contract_hash") or ""),
        "source": str(source.get("provider") or ""),
        "endpoint": str(source.get("endpoint") or ""),
        "exchange_timestamp_ms": int(order_book.get("exchange_timestamp_ms") or 0),
        "observed_at_ms": int(order_book.get("observed_at_ms") or 0),
        "depth_requested": int(order_book.get("depth_requested") or 0),
        "observed_ask_levels": len(asks),
        "liquidity_scope": str(order_book.get("liquidity_scope") or ""),
        "checksum_policy": str(order_book.get("checksum_policy") or ""),
        "complete_book_verified": False,
        "same_snapshot_as_ticker": False,
        "is_executable_quote": False,
        "hash_verified": order_book.get("hash_verified") is True,
    }
    preview["rule_binding"] = {
        "rules_hash": str(instrument_rules.get("rules_hash") or ""),
        "snapshot_hash": str(instrument_rules.get("snapshot_hash") or ""),
        "lot_size": str(instrument_rules.get("lot_size") or ""),
        "minimum_order_size": str(instrument_rules.get("minimum_order_size") or ""),
        "base_currency": str(instrument_rules.get("size_unit") or ""),
        "quote_currency": str(instrument_rules.get("price_unit") or ""),
    }
    preview["rows"] = rows
    return _finalize_depth_preview(preview)


def _quantity_preview_base(
    *,
    symbol: str,
    status: str,
    blockers: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": QUANTITY_PREVIEW_SCHEMA,
        "mode": QUANTITY_PREVIEW_MODE,
        "status": status,
        "symbol": symbol,
        "budget_basis": {
            "amounts": ["10", "20"],
            "currency": "USDT",
            "usd_equivalence_verified": False,
            "display_relation": "REFERENCE_ONLY",
        },
        "price_evidence": {
            "value": "",
            "kind": "PUBLIC_BEST_ASK_REFERENCE",
            "available_size": "",
            "size_basis": "BASE_CURRENCY",
            "source": "",
            "timestamp_ms": 0,
            "snapshot_id": "",
            "depth_levels": 1,
            "is_executable_quote": False,
            "in_memory_only": True,
            "client_price_used": False,
            "fallback_used": False,
            "cache_regression": False,
        },
        "rule_binding": {
            "rules_hash": "",
            "snapshot_hash": "",
            "lot_size": "",
            "minimum_order_size": "",
            "effective_minimum_order_size": "",
            "minimum_cost": None,
            "base_currency": "",
            "quote_currency": "",
        },
        "rows": [],
        "quantization": {
            "mode": "FLOOR_TO_PUBLIC_LOT",
            "sizing_unit": "BASE_CURRENCY_ESTIMATE",
            "venue_auto_rounding_assumed": False,
            "price_tick_used": False,
            "order_parameters_generated": False,
            "side_inferred": False,
            "tgt_ccy_generated": False,
        },
        "risk_check_buffer": {
            "status": "ILLUSTRATIVE_ONLY",
            "rate": "0.05",
            "currency": "USDT",
            "basis": "REQUESTED_QUOTE_SPEND",
            "scenario": "HYPOTHETICAL_OKX_SPOT_MARKET_BUY_QUOTE_SPEND",
            "semantics": "TEMP_RISK_CHECK_BUFFER_NOT_FEE",
            "account_balance_checked": False,
            "fee_estimate": False,
            "slippage_estimate": False,
            "order_intent_created": False,
            "order_parameters_generated": False,
        },
        "unknowns": {
            "account_fee": "NOT_CHECKED",
            "slippage": "NOT_CHECKED",
            "minimum_cost": "NOT_CHECKED",
            "account_balance": "NOT_CHECKED",
            "usd_usdt_conversion": "NOT_CHECKED",
            "spread_and_side": "NOT_CHECKED",
            "fill_price": "NOT_CHECKED",
            "order_book_depth": "NOT_CHECKED",
            "venue_slippage_policy": "NOT_CHECKED",
        },
        "permissions": {
            "planning_only": True,
            "order_submission_allowed": False,
            "execution_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "execution_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "blockers": list(dict.fromkeys(blockers)),
    }


def _finalize_quantity_preview(preview: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(preview)
    sealed["preview_hash"] = _canonical_hash(sealed)
    sealed["hash_verified"] = True
    return sealed


def build_small_capital_quantity_preview(
    *,
    symbol: str,
    market_truth: dict[str, Any],
    instrument_rules: dict[str, Any],
    instrument_status: str,
    current_time_ms: Any,
) -> dict[str, Any]:
    """Estimate base quantity from fixed 10/20 USDT best-ask tiers without creating an order."""

    rules_status = str(instrument_rules.get("status") or "")
    if rules_status == "NOT_APPLICABLE":
        return _finalize_quantity_preview(_quantity_preview_base(
            symbol=symbol,
            status="NOT_APPLICABLE",
            blockers=["public_spot_rules_not_applicable"],
        ))
    if instrument_status == "BLOCK":
        return _finalize_quantity_preview(_quantity_preview_base(
            symbol=symbol,
            status="BLOCK",
            blockers=["instrument_rules_contract_blocked"],
        ))

    reference = _mapping(_mapping(market_truth.get("quote")).get("sizing_reference"))
    current_time = current_time_ms if type(current_time_ms) is int else None
    timestamp_ms = reference.get("timestamp_ms") if type(reference.get("timestamp_ms")) is int else None
    max_age_ms = market_truth.get("max_observation_age_ms") if type(market_truth.get("max_observation_age_ms")) is int else None
    snapshot_id = str(market_truth.get("snapshot_id") or "")
    source = str(reference.get("source") or "")
    price = _positive_decimal(reference.get("value"))
    available_size = _positive_decimal(reference.get("available_size"))
    if (
        reference.get("status") == "BLOCK"
        or reference.get("fallback_used") is True
        or reference.get("cache_regression") is True
    ):
        return _finalize_quantity_preview(_quantity_preview_base(
            symbol=symbol,
            status="BLOCK",
            blockers=["public_best_ask_conflict"],
        ))
    if reference.get("status") == "NOT_CHECKED":
        normalized_missing_reference = bool(
            reference.get("value") == ""
            and reference.get("available_size") == ""
            and reference.get("kind") == "PUBLIC_BEST_ASK_REFERENCE"
            and reference.get("size_basis") == "BASE_CURRENCY"
            and reference.get("depth_levels") == 1
            and reference.get("is_executable_quote") is False
            and reference.get("in_memory_only") is True
            and reference.get("client_price_used") is False
            and reference.get("fallback_used") is False
            and reference.get("cache_regression") is False
        )
        return _finalize_quantity_preview(_quantity_preview_base(
            symbol=symbol,
            status="NEEDS_EVIDENCE" if normalized_missing_reference else "BLOCK",
            blockers=[
                "public_best_ask_not_checked"
                if normalized_missing_reference
                else "public_best_ask_contract_invalid"
            ],
        ))
    if reference.get("status") != "PASS":
        return _finalize_quantity_preview(_quantity_preview_base(
            symbol=symbol,
            status="BLOCK",
            blockers=["public_best_ask_contract_invalid"],
        ))
    if instrument_status != "PASS":
        return _finalize_quantity_preview(_quantity_preview_base(
            symbol=symbol,
            status="NEEDS_EVIDENCE",
            blockers=["instrument_rules_not_verified"],
        ))
    reference_contract_valid = bool(
        market_truth.get("schema_version") == "market-data-truth-v1"
        and str(market_truth.get("symbol") or "").strip().upper() == symbol
        and market_truth.get("status") == "READY"
        and market_truth.get("mode") == "REALTIME_READY"
        and market_truth.get("evidence_scope") == "FULL_SNAPSHOT"
        and market_truth.get("snapshot_available") is True
        and market_truth.get("observation_current") is True
        and market_truth.get("realtime_ready") is True
        and market_truth.get("execution_usable") is False
        and reference.get("status") == "PASS"
        and reference.get("kind") == "PUBLIC_BEST_ASK_REFERENCE"
        and reference.get("size_basis") == "BASE_CURRENCY"
        and reference.get("depth_levels") == 1
        and reference.get("is_executable_quote") is False
        and reference.get("in_memory_only") is True
        and reference.get("client_price_used") is False
        and reference.get("fallback_used") is False
        and reference.get("cache_regression") is False
        and price is not None
        and available_size is not None
        and source
        and timestamp_ms is not None
        and timestamp_ms > 0
        and snapshot_id
        and reference.get("snapshot_id") == snapshot_id
        and current_time is not None
        and current_time > 0
        and max_age_ms is not None
        and max_age_ms > 0
        and -5_000 <= current_time - timestamp_ms <= max_age_ms
    )
    lot_size = _positive_decimal(instrument_rules.get("lot_size"))
    minimum_order_size = _positive_decimal(instrument_rules.get("minimum_order_size"))
    rule_contract_valid = bool(
        instrument_rules.get("symbol") == symbol
        and instrument_rules.get("instrument_type") == "SPOT"
        and instrument_rules.get("instrument_state") == "live"
        and instrument_rules.get("current") is True
        and instrument_rules.get("minimum_cost") is None
        and instrument_rules.get("hash_verified") is True
        and lot_size is not None
        and minimum_order_size is not None
        and str(instrument_rules.get("size_unit") or "")
        and instrument_rules.get("price_unit") == "USDT"
        and str(instrument_rules.get("rules_hash") or "")
        and str(instrument_rules.get("snapshot_hash") or "")
    )
    if not reference_contract_valid or not rule_contract_valid:
        return _finalize_quantity_preview(_quantity_preview_base(
            symbol=symbol,
            status="BLOCK",
            blockers=[
                *([] if reference_contract_valid else ["reference_price_contract_invalid"]),
                *([] if rule_contract_valid else ["instrument_rule_binding_invalid"]),
            ],
        ))

    try:
        effective_minimum_steps = _ceil_decimal_ratio(minimum_order_size, lot_size)
        rows: list[dict[str, Any]] = []
        every_minimum_met = True
        every_top_of_book_reference_covers = True
        display_precision = max(
            64,
            len(price.as_tuple().digits) + len(lot_size.as_tuple().digits) + 32,
        )
        # Inputs are capped at 128 non-exponent characters. 1024 digits keeps
        # all derived products/subtractions exact; the lot-step floor itself is
        # computed from integer ratios and never depends on Decimal context.
        with localcontext() as calculation_context:
            calculation_context.prec = 1024
            effective_minimum = Decimal(effective_minimum_steps) * lot_size
            for budget_text in ("10", "20"):
                budget = Decimal(budget_text)
                lot_steps_int = _floor_decimal_over_product(budget, price, lot_size)
                quantity_floor = Decimal(lot_steps_int) * lot_size
                reference_notional = quantity_floor * price
                unallocated = budget - reference_notional
                risk_check_buffer_quote = budget * OKX_MARKET_RISK_CHECK_BUFFER_RATE
                planning_quote_availability = budget + risk_check_buffer_quote
                with localcontext() as display_context:
                    display_context.prec = display_precision
                    raw_quantity = budget / price
                minimum_met = lot_steps_int >= effective_minimum_steps
                lot_aligned = quantity_floor == Decimal(lot_steps_int) * lot_size
                within_budget = reference_notional <= budget and unallocated >= 0
                top_of_book_reference_covers = quantity_floor <= available_size
                if lot_steps_int < 0 or not lot_aligned or not within_budget:
                    raise ArithmeticError("quantity_preview_postcondition_failed")
                every_minimum_met = every_minimum_met and minimum_met
                every_top_of_book_reference_covers = (
                    every_top_of_book_reference_covers and top_of_book_reference_covers
                )
                rows.append({
                    "budget_quote_amount": budget_text,
                    "raw_quantity": _decimal_text(raw_quantity),
                    "lot_steps": str(lot_steps_int),
                    "quantity_floor": _decimal_text(quantity_floor),
                    "quantity_unit": str(instrument_rules.get("size_unit") or ""),
                    "reference_notional": _decimal_text(reference_notional),
                    "notional_currency": "USDT",
                    "unallocated_before_costs": _decimal_text(unallocated),
                    "risk_check_buffer_quote": _decimal_text(risk_check_buffer_quote),
                    "planning_quote_availability": _decimal_text(planning_quote_availability),
                    "best_ask_size_reference": _decimal_text(available_size),
                    "top_of_book_reference_covers_quantity": top_of_book_reference_covers,
                    "top_of_book_depth_verified": False,
                    "lot_aligned": lot_aligned,
                    "within_quote_budget": within_budget,
                    "minimum_order_size_met": minimum_met,
                    "minimum_cost_checked": False,
                    "fees_included": False,
                    "slippage_included": False,
                    "executable": False,
                })
    except (ArithmeticError, ValueError):
        return _finalize_quantity_preview(_quantity_preview_base(
            symbol=symbol,
            status="BLOCK",
            blockers=["quantity_preview_decimal_postcondition_failed"],
        ))

    preview_status = (
        "BELOW_MIN_SIZE"
        if not every_minimum_met
        else "TOP_OF_BOOK_LIMITED"
        if not every_top_of_book_reference_covers
        else "PREVIEW_ONLY"
    )
    preview = _quantity_preview_base(
        symbol=symbol,
        status=preview_status,
        blockers=(
            ["one_or_more_reference_tiers_below_public_minimum_size"]
            if not every_minimum_met
            else ["one_or_more_tiers_exceed_current_best_ask_size"]
            if not every_top_of_book_reference_covers
            else []
        ),
    )
    preview["price_evidence"] = {
        "value": _decimal_text(price),
        "kind": "PUBLIC_BEST_ASK_REFERENCE",
        "available_size": _decimal_text(available_size),
        "size_basis": "BASE_CURRENCY",
        "source": source,
        "timestamp_ms": timestamp_ms,
        "snapshot_id": snapshot_id,
        "depth_levels": 1,
        "is_executable_quote": False,
        "in_memory_only": True,
        "client_price_used": False,
        "fallback_used": False,
        "cache_regression": False,
    }
    preview["rule_binding"] = {
        "rules_hash": str(instrument_rules.get("rules_hash") or ""),
        "snapshot_hash": str(instrument_rules.get("snapshot_hash") or ""),
        "lot_size": _decimal_text(lot_size),
        "minimum_order_size": _decimal_text(minimum_order_size),
        "effective_minimum_order_size": _decimal_text(effective_minimum),
        "minimum_cost": None,
        "base_currency": str(instrument_rules.get("size_unit") or ""),
        "quote_currency": "USDT",
    }
    preview["rows"] = rows
    return _finalize_quantity_preview(preview)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _strict_evidence(mapping: dict[str, Any], key: str) -> tuple[str, bool]:
    if key not in mapping:
        return "NOT_CHECKED", False
    value = mapping.get(key)
    if type(value) is not bool:
        return "INVALID", False
    return ("PASS", True) if value is True else ("NOT_CHECKED", False)


def _group_check(
    capabilities: dict[str, Any],
    *,
    check_id: str,
    keys: tuple[str, ...],
    pass_detail: str,
    missing_detail: str,
) -> dict[str, str]:
    statuses = {key: _strict_evidence(capabilities, key)[0] for key in keys}
    if any(status == "INVALID" for status in statuses.values()):
        invalid = ", ".join(key for key, status in statuses.items() if status == "INVALID")
        return {
            "id": check_id,
            "status": "INVALID",
            "detail": f"Strict boolean evidence required: {invalid}.",
        }
    if all(status == "PASS" for status in statuses.values()):
        return {"id": check_id, "status": "PASS", "detail": pass_detail}
    return {"id": check_id, "status": "NOT_CHECKED", "detail": missing_detail}


def _authority_contract(
    value: Any,
    *,
    label: str,
    expected: dict[str, bool],
) -> tuple[list[str], list[str]]:
    mapping = _mapping(value)
    if not mapping:
        return [], [f"{label}.{key}" for key in expected]

    errors: list[str] = []
    missing: list[str] = []
    for key, expected_value in expected.items():
        if key not in mapping:
            missing.append(f"{label}.{key}")
            continue
        actual = mapping.get(key)
        if type(actual) is not bool:
            errors.append(f"{label}.{key}:expected_native_bool")
        elif actual is not expected_value:
            errors.append(f"{label}.{key}:permission_boundary_mismatch")
    return errors, missing


def build_small_capital_trial_plan(
    *,
    runtime_read_only: Any,
    live_trading_hard_block: Any,
    risk_snapshot: Any,
    market_truth: Any,
    forward_validation: Any,
    symbol: Any = "",
    instrument_rules_evidence: Any = None,
    order_book_evidence: Any = None,
    current_time_ms: Any = None,
    capabilities: Any = None,
) -> dict[str, Any]:
    """Build an execution-free readiness plan for an illustrative USD 100-200 trial.

    The function has no I/O, never accepts credentials or order instructions, and
    cannot grant paper or live authority. Evidence flags must be native ``bool``
    values; integers and truthy strings are deliberately rejected.
    """

    market = _mapping(market_truth)
    forward = _mapping(forward_validation)
    capability_map = _mapping(capabilities)
    requested_symbol = str(symbol or market.get("symbol") or "").strip().upper()
    market_symbol = str(market.get("symbol") or "").strip().upper()

    boundary_errors: list[str] = []
    boundary_missing: list[str] = []
    if runtime_read_only is not True:
        boundary_errors.append("runtime_read_only:must_be_native_true")
    if live_trading_hard_block is not True:
        boundary_errors.append("live_trading_hard_block:must_be_native_true")
    if requested_symbol and market_symbol and requested_symbol != market_symbol:
        boundary_errors.append("market_truth.symbol:requested_symbol_mismatch")

    for value, label, expected in (
        (
            risk_snapshot,
            "risk_snapshot",
            {
                "live_trading_hard_block": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            },
        ),
        (
            market_truth,
            "market_truth",
            {
                "read_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
                "execution_usable": False,
            },
        ),
        (
            forward_validation,
            "forward_validation",
            {
                "read_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            },
        ),
    ):
        errors, missing = _authority_contract(value, label=label, expected=expected)
        boundary_errors.extend(errors)
        boundary_missing.extend(missing)

    permission_status = (
        "BLOCK" if boundary_errors else "NOT_CHECKED" if boundary_missing else "PASS"
    )
    permission_detail = (
        "A read-only or hard-lock authority boundary is invalid."
        if boundary_errors
        else "Authority fields are missing and must be verified."
        if boundary_missing
        else "Read-only, paper-disabled, and live-disabled boundaries are verified."
    )

    market_evidence_status, market_evidence_ok = _strict_evidence(
        market, "research_usable"
    )
    if permission_status == "BLOCK" and any(
        item.startswith("market_truth.") for item in boundary_errors
    ):
        market_evidence_status = "BLOCK"
        market_evidence_ok = False
    market_check = {
        "id": "market_evidence",
        "status": market_evidence_status,
        "detail": (
            "Current quote/source/timeframe/candle evidence is research-usable."
            if market_evidence_ok
            else "Current quote/source/timeframe/candle evidence is not verified."
        ),
    }

    incremental = _mapping(forward.get("incremental_observation"))
    latest_bar = _mapping(incremental.get("latest_completed_bar"))
    forward_evidence_status, forward_evidence_ok = _strict_evidence(latest_bar, "known")
    if permission_status == "BLOCK" and any(
        item.startswith("forward_validation.") for item in boundary_errors
    ):
        forward_evidence_status = "BLOCK"
        forward_evidence_ok = False
    forward_check = {
        "id": "forward_evidence",
        "status": forward_evidence_status,
        "detail": (
            "A naturally completed forward-observation bar is verified."
            if forward_evidence_ok
            else "Natural forward-observation evidence is not verified."
        ),
    }

    # OKX account fee rates require a private, account-specific Read request.
    # This public-only planning stage cannot truthfully verify them.
    fee_status, fee_ok = "NOT_CHECKED", False
    fee_check = {
        "id": "fee_evidence",
        "status": fee_status,
        "detail": "Account-specific maker/taker fees remain NOT_CHECKED; public defaults are not accepted.",
    }
    raw_instrument_rules = (
        instrument_rules_evidence
        if isinstance(instrument_rules_evidence, dict)
        else public_instrument_rules_placeholder(
            requested_symbol,
            captured_at_ms=current_time_ms if type(current_time_ms) is int else 0,
        )
    )
    instrument_verification = verify_public_instrument_rules(
        raw_instrument_rules,
        expected_symbol=requested_symbol,
        now_ms=current_time_ms,
    )
    instrument_status = str(instrument_verification.get("status") or "BLOCK")
    instrument_ok = instrument_status == "PASS"
    instrument_output = dict(instrument_verification.get("rules") or {})
    for transient_key in ("age_ms", "cache_age_ms", "cached", "refresh_error"):
        instrument_output.pop(transient_key, None)
    instrument_check = {
        "id": "instrument_rules",
        "status": instrument_status,
        "detail": (
            "Current tick, lot, and minimum-size rules have independent evidence."
            if instrument_ok
            else "Current public SPOT tick, lot, and minimum-amount rules are not verified."
        ),
    }
    raw_order_book = (
        order_book_evidence
        if isinstance(order_book_evidence, dict)
        else public_order_book_placeholder(
            requested_symbol,
            observed_at_ms=current_time_ms if type(current_time_ms) is int else 0,
        )
    )
    order_book_verification = verify_public_order_book(
        raw_order_book,
        expected_symbol=requested_symbol,
        now_ms=current_time_ms,
    )
    order_book_status = str(order_book_verification.get("status") or "BLOCK")
    order_book_output = dict(order_book_verification.get("order_book") or {})
    for transient_key in ("age_ms", "cache_age_ms", "cached", "refresh_error"):
        order_book_output.pop(transient_key, None)
    order_book_check = {
        "id": "order_book_depth",
        "status": order_book_status,
        "detail": (
            "Current public multi-level ask depth has verified structure, time, identity, and hash evidence."
            if order_book_status == "PASS"
            else "Current public multi-level order-book evidence is not verified."
        ),
    }
    quantity_preview = build_small_capital_quantity_preview(
        symbol=requested_symbol,
        market_truth=market,
        instrument_rules=instrument_output,
        instrument_status=instrument_status,
        current_time_ms=current_time_ms,
    )
    depth_impact_preview = build_small_capital_depth_preview(
        symbol=requested_symbol,
        market_truth=market,
        instrument_rules=instrument_output,
        instrument_status=instrument_status,
        order_book=order_book_output,
        order_book_status=order_book_status,
    )
    microstructure_truth = build_public_order_book_microstructure(
        order_book_output,
        expected_symbol=requested_symbol,
        now_ms=current_time_ms,
    )
    if quantity_preview.get("status") == "BLOCK" and market_evidence_ok and instrument_ok:
        market_check["status"] = "BLOCK"
        market_check["detail"] = "Trusted in-memory reference-price contract is inconsistent."
    if depth_impact_preview.get("status") == "BLOCK" and market_evidence_ok and instrument_ok:
        order_book_check["status"] = "BLOCK"
        order_book_check["detail"] = "Public multi-level order-book evidence or its calculation contract is inconsistent."
    if microstructure_truth.get("status") == "BLOCK" and order_book_status == "PASS":
        order_book_check["status"] = "BLOCK"
        order_book_check["detail"] = "Public two-sided microstructure evidence is inconsistent."
    security_check = _group_check(
        capability_map,
        check_id="security_isolation",
        keys=(
            "dedicated_subaccount_verified",
            "restricted_api_key_verified",
            "ip_allowlist_verified",
            "withdrawal_disabled_verified",
            "signer_isolated_verified",
        ),
        pass_detail="Subaccount, restricted key, IP, withdrawal, and signer isolation are verified.",
        missing_detail="Subaccount and key-isolation evidence is incomplete.",
    )
    circuit_check = _group_check(
        capability_map,
        check_id="circuit_breaker_reconciliation",
        keys=(
            "independent_circuit_breaker_verified",
            "manual_reset_verified",
            "reconciliation_verified",
        ),
        pass_detail="Independent halt, manual reset, and reconciliation evidence are verified.",
        missing_detail="Independent halt, manual reset, or reconciliation evidence is incomplete.",
    )

    checks: list[dict[str, str]] = [
        {
            "id": "permission_boundary",
            "status": permission_status,
            "detail": permission_detail,
        },
        market_check,
        forward_check,
        fee_check,
        instrument_check,
        order_book_check,
        security_check,
        circuit_check,
    ]

    invalid_checks = [
        check["id"] for check in checks if check["status"] in {"BLOCK", "INVALID"}
    ]
    if boundary_errors or invalid_checks:
        status = "BLOCK"
        next_action = "Restore and re-verify the invalid read-only planning evidence; do not execute orders."
    elif any(check["status"] != "PASS" for check in checks):
        status = "NEEDS_EVIDENCE"
        first_missing = next(check["id"] for check in checks if check["status"] != "PASS")
        next_action = f"Verify {first_missing} with current, non-secret evidence; do not execute orders."
    else:
        status = "PLANNING_ONLY"
        next_action = "Planning evidence is complete; keep this artifact execution-free."

    # These are absolute examples derived only from the fixed USD 100-200 band.
    # They are not venue rules, expected returns, or an execution authorization.
    plan: dict[str, Any] = {
        "schema_version": SCHEMA,
        "mode": MODE,
        "status": status,
        "illustrative_not_investment_advice": True,
        "budget": {
            "currency": "USD",
            "min_usd": 100.0,
            "max_usd": 200.0,
        },
        "scope": {
            "symbol": requested_symbol,
            "asset_class": "SPOT_ONLY",
            "leverage": 1,
            "margin_allowed": False,
            "derivatives_allowed": False,
        },
        "guardrails": {
            "reserve_pct": 20.0,
            "reserve_usd": {"min": 20.0, "max": 40.0},
            "max_deployed_pct": 80.0,
            "max_deployed_usd": {"min": 80.0, "max": 160.0},
            "single_order_pct": 10.0,
            "single_order_usd": {"min": 10.0, "max": 20.0},
            "daily_gross_pct": 40.0,
            "daily_gross_usd": {"min": 40.0, "max": 80.0},
            "daily_loss_pct": 2.0,
            "daily_loss_usd": {"min": 2.0, "max": 4.0},
            "drawdown_halt_pct": 5.0,
            "drawdown_halt_usd": {"min": 5.0, "max": 10.0},
            "max_open_positions": 2,
            "max_orders_24h": 4,
            "consecutive_losses_halt": 2,
            "cooldown_hours": 24,
        },
        "fee_schedule": {
            "status": "NOT_CHECKED",
            "account_specific": True,
            "public_default_accepted": False,
            "maker_fee": None,
            "taker_fee": None,
        },
        "instrument_rules": instrument_output,
        "public_order_book": order_book_output,
        "microstructure_truth": microstructure_truth,
        "quantity_preview": quantity_preview,
        "depth_impact_preview": depth_impact_preview,
        "permissions": {
            "planning_only": True,
            "runtime_mutations_allowed": False,
            "deposit_allowed": False,
            "order_submission_allowed": False,
            "execution_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
            "live_trading_hard_block": True,
        },
        "execution_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "checks": checks,
        "missing_evidence": [
            check["id"] for check in checks if check["status"] not in {"PASS", "BLOCK"}
        ],
        "blockers": list(dict.fromkeys([
            *boundary_errors,
            *list(instrument_verification.get("blockers") or []),
            *list(order_book_verification.get("blockers") or []),
            *list(microstructure_truth.get("blockers") or []),
            *list(quantity_preview.get("blockers") or []),
            *list(depth_impact_preview.get("blockers") or []),
            *[f"check_invalid:{check_id}" for check_id in invalid_checks],
        ])),
        "next_action": next_action,
    }
    plan["plan_hash"] = _canonical_hash(plan)
    return plan


__all__ = [
    "build_small_capital_depth_preview",
    "build_small_capital_quantity_preview",
    "build_small_capital_trial_plan",
]
