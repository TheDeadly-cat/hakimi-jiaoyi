"""Frozen US margin paper-trading fee rules, Futu help topic 814, sections 13–14.

These model a single hypothetical order filled once. The help page does not
specify transaction-level rounding, applicability dates, or how to arbitrate an
order minimum above the percentage cap. We apply the cap last, retain unrounded
components and round their sum once per order. No real-account tariff is implied.
"""
from decimal import Decimal, ROUND_HALF_UP

PRESET = "FUTU_US_MARGIN_SIM_20261124"
SOURCE = "https://support.futunn.com/topic814?from_platform=1&lang=zh-cn"
CENT = Decimal("0.01")


def paper_order_fees(asset, side, count, price):
    """Return (USD total, unrounded fee components) for shares or 100-share contracts."""
    if (asset not in ("STOCK", "OPTION") or side not in ("buy", "sell")
            or type(count) is not int or count <= 0 or not isinstance(price, Decimal)
            or not price.is_finite() or price <= 0):
        raise ValueError("模拟费用的品类、买卖方向、成交单位或价格无效")
    if asset == "STOCK":
        notional = count * price
        cap = notional * Decimal(".005")
        parts = {
            "commission": min(cap, max(Decimal(".99"), count * Decimal(".0049"))),
            "platform": min(cap, max(Decimal("1"), count * Decimal(".005"))),
            "settlement": count * Decimal(".003"),
        }
        if side == "sell":
            parts["regulatory"] = max(CENT, notional * Decimal(".000008"))
            parts["trading_activity"] = min(Decimal("8.30"), max(CENT, count * Decimal(".000166")))
    else:
        notional = price * 100 * count
        commission = Decimal(".65") if price > Decimal(".10") else Decimal(".15")
        parts = {"commission": max(Decimal("1.99"), commission * count),
                 "platform": Decimal(".30") * count, "options_regulatory": Decimal(".02915") * count}
        if side == "sell":
            parts["regulatory"] = max(CENT, notional * Decimal(".0000229"))
            parts["trading_activity"] = max(CENT, count * Decimal(".00279"))
    return sum(parts.values()).quantize(CENT, rounding=ROUND_HALF_UP), parts


def paper_basis(asset, buy_count, buy_price, sell_price=None):
    """Persist exact decimal components so saved hypothetical results can be audited."""
    _, buy = paper_order_fees(asset, "buy", buy_count, buy_price)
    sell = paper_order_fees(asset, "sell", buy_count, sell_price)[1] if sell_price is not None else None
    return {
        "basis": PRESET, "source": SOURCE, "source_section": 13 if asset == "STOCK" else 14,
        "source_observed_date": "2026-11-24", "historical_applicability_verified": False,
        "assumed_fills_per_order": 1, "rounding_assumption": "HALF_UP_CENT_ON_ORDER_TOTAL",
        "buy_components_raw_usd": {k: str(v) for k, v in buy.items()},
        "sell_components_raw_usd": {k: str(v) for k, v in sell.items()} if sell is not None else None,
        "exit_fee_status": "ASSUMED_SELL_ORDER" if sell is not None else "NO_CLOSING_ORDER_MODELED",
        "actual_fees_usd": None,
    }
