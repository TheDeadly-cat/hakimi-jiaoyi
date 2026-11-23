"""Read-only, single-snapshot US stock/ETF execution estimate. Never creates an order."""
from datetime import datetime
from decimal import Decimal, InvalidOperation, localcontext
from hashlib import sha256
import json
import re


def _amount(value, label, *, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(label + "缺失或格式无效")
    try:
        amount = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError(label + "不是有效数字") from error
    if (not amount.is_finite() or not 0 <= amount <= 10**12 or
            (amount == 0 and not allow_zero) or amount.as_tuple().exponent < -12):
        raise ValueError(label + "超出支持范围")
    return amount


def _time(value):
    if not isinstance(value, str) or len(value) > 48:
        raise ValueError("缺少带时区的回放或接收时间")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("时间缺少时区")
    return parsed


def _show(value):
    return format(value, "f").rstrip("0").rstrip(".") if value.as_tuple().exponent < 0 else str(value)


def _levels(rows, side):
    if not isinstance(rows, list) or len(rows) > 10:
        raise ValueError("需要本机接口返回的一至十档盘口")
    levels = []
    for rank, row in enumerate(rows, 1):
        if not isinstance(row, dict) or type(row.get("level")) is not int or row["level"] != rank:
            raise ValueError("盘口缺档或档次不连续")
        price = _amount(row.get("price"), "档位价格")
        size = _amount(row.get("size"), "档位数量", allow_zero=True)
        if levels and ((side == "asks" and price <= levels[-1][0]) or
                       (side == "bids" and price >= levels[-1][0])):
            raise ValueError("盘口价格重复或顺序无效")
        levels.append((price, size))
    return levels


def preview_depth(payload):
    if not isinstance(payload, dict) or set(payload) != {"order", "as_of", "quote"}:
        raise ValueError("需要委托假设、回放时点和对应行情快照")
    order, quote = payload["order"], payload["quote"]
    if not isinstance(order, dict) or set(order) != {"symbol", "side", "quantity", "type", "limit_price"}:
        raise ValueError("委托假设字段无效")
    symbol, side, kind = order["symbol"], order["side"], order["type"]
    if (not isinstance(symbol, str) or not re.fullmatch(r"[A-Z]{1,6}(?:\.[A-Z])?", symbol)
            or side not in ("BUY", "SELL") or kind not in ("MARKET", "LIMIT")):
        raise ValueError("仅支持美股股票或 ETF 的买卖市价及限价假设")
    qty = _amount(order["quantity"], "委托股数")
    if kind == "MARKET" and order["limit_price"] is not None:
        raise ValueError("市价假设不能带限价")
    limit = _amount(order["limit_price"], "限价") if kind == "LIMIT" else None
    if (not isinstance(quote, dict) or quote.get("ok") is not True or quote.get("symbol") != symbol
            or quote.get("code") != "US."+symbol or quote.get("currency") != "USD"
            or quote.get("source") != "Futu OpenD / get_market_snapshot"):
        raise ValueError("快照与委托标的、市场或币种不匹配")
    as_of = _time(payload["as_of"])
    if _time(quote.get("receivedAt")) > as_of:
        raise ValueError("回放时尚未接收到该行情快照")
    book = quote.get("book")
    result = {"model": "displayed-depth-usd-v1", "symbol": symbol, "side": side, "order_type": kind,
              "limit_price": _show(limit) if limit is not None else None,
              "requested_quantity": _show(qty), "as_of": payload["as_of"],
              "basis": "SINGLE_SNAPSHOT_ALL_DISPLAYED_SIZE_ASSUMED_ACCESSIBLE",
              "input_source": "CALLER_SUPPLIED_OPEND_CAPTURE",
              "broker_queue_status": "NOT_OBSERVED", "market_impact_modeled": False,
              "status": "UNAVAILABLE", "estimated_quantity": None, "unpriced_quantity": None,
              "estimated_vwap": None, "estimated_notional_usd": None, "levels_used": [],
              "broker_fill_quantity": None, "broker_fee_usd": None, "execution_authorized": False}
    if not isinstance(book, dict) or book.get("status") != "AVAILABLE":
        return {**result, "reason": "没有可核对的深度盘口"}
    if _time(book.get("receivedAt")) > as_of:
        raise ValueError("回放时尚未接收到该盘口")
    if (book.get("source") != "Futu OpenD / get_order_book" or book.get("bookType") != "NORMAL"
            or type(book.get("invalidLevels")) is not int or book["invalidLevels"] != 0 or book.get("crossed") is not False):
        return {**result, "reason": "盘口来源、类型、档位或交叉状态不能核实"}
    bids, asks = _levels(book.get("bids"), "bids"), _levels(book.get("asks"), "asks")
    if bids and asks and bids[0][0] > asks[0][0]:
        return {**result, "reason": "交叉盘口无法用于估算"}
    levels = asks if side == "BUY" else bids
    if not levels:
        return {**result, "reason": "委托对手方没有档位"}
    result.update(book_received_at=book["receivedAt"], bid_time_raw=book.get("bidTimeRaw"),
                  ask_time_raw=book.get("askTimeRaw"), market_session=quote.get("marketSession"),
                  book_sha256=sha256(json.dumps(book, sort_keys=True, separators=(",",":"),
                                                allow_nan=False, ensure_ascii=False).encode()).hexdigest())
    with localcontext() as context:
        context.prec = 64
        remaining, notional = qty, Decimal(0)
        for rank, (price, size) in enumerate(levels, 1):
            if limit is not None and ((side == "BUY" and price > limit) or (side == "SELL" and price < limit)):
                break
            taken = min(size, remaining)
            if taken:
                notional += taken * price
                remaining -= taken
                result["levels_used"].append({"level": rank, "price": _show(price), "quantity": _show(taken)})
            if not remaining:
                break
        matched = qty - remaining
        return {**result, "status": "COVERED" if not remaining else ("PARTIAL_DEPTH" if matched else "NO_DISPLAYED_MATCH"),
                "estimated_quantity": _show(matched), "unpriced_quantity": _show(remaining),
                "estimated_notional_usd": _show(notional),
                "estimated_vwap": _show((notional / matched).quantize(Decimal("0.00000001"))) if matched else None}
