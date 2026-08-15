from __future__ import annotations

import copy
import hashlib
import json
import re
import threading
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from typing import Any, Callable


SCHEMA_VERSION = "okx-public-order-book-planning-v1"
MODE = "PUBLIC_READ_ONLY_PLANNING"
PROVIDER = "OKX_PUBLIC_API"
ENDPOINT = "/api/v5/market/books"
DEFAULT_DEPTH = 20
DEFAULT_MAX_AGE_MS = 5_000
DEFAULT_MIN_REFRESH_MS = 1_000
MICROSTRUCTURE_SCHEMA_VERSION = "public-order-book-microstructure-v2"
MICROSTRUCTURE_MODE = "PUBLIC_READ_ONLY_OBSERVATION"
MICROSTRUCTURE_RATIO_PLACES = 12
MICROSTRUCTURE_SPREAD_BPS_PLACES = 8
MICROSTRUCTURE_PRICE_BANDS_BPS = (5, 10, 25)
_SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,20}-[A-Z0-9]{2,20}$")
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonical_symbol(value: Any) -> str:
    text = str(value or "").strip().upper()
    return text if _SYMBOL_RE.fullmatch(text) else ""


def _native_int(value: Any) -> int | None:
    return value if type(value) is int and value >= 0 else None


def _timestamp_ms(value: Any) -> int | None:
    text = str(value or "").strip()
    return int(text) if text.isdigit() and int(text) > 0 else None


def _positive_decimal_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if not text or len(text) > 128 or "e" in text.lower():
        return ""
    try:
        parsed = Decimal(text)
    except InvalidOperation:
        return ""
    if not parsed.is_finite() or parsed <= 0:
        return ""
    normalized = format(parsed, "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized


def _fraction(value: str) -> Fraction:
    return Fraction(Decimal(value))


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


def _scaled_fraction(value: Fraction, *, places: int) -> int:
    scale = 10 ** places
    quotient, remainder = divmod(value.numerator * scale, value.denominator)
    doubled = remainder * 2
    if doubled > value.denominator or (doubled == value.denominator and quotient % 2):
        quotient += 1
    return quotient


def _scaled_decimal_text(value: int, *, places: int) -> str:
    sign = "-" if value < 0 else ""
    digits = str(abs(value)).rjust(places + 1, "0")
    if places == 0:
        return f"{sign}{digits}"
    return f"{sign}{digits[:-places]}.{digits[-places:]}".rstrip("0").rstrip(".")


def _rounded_fraction_text(value: Fraction, *, places: int) -> str:
    return _scaled_decimal_text(_scaled_fraction(value, places=places), places=places)


def _contract_content(book: dict[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in book.items()
        if key not in {
            "contract_hash",
            "contract_hash_verified",
            "age_ms",
            "cache_age_ms",
            "cached",
            "refresh_error",
        }
    }


def _seal_contract(book: dict[str, Any]) -> dict[str, Any]:
    book["contract_hash"] = _canonical_hash(_contract_content(book))
    book["contract_hash_verified"] = True
    return book


def _safe_contract(
    *,
    symbol: str,
    status: str,
    observed_at_ms: int,
    max_age_ms: int,
    blockers: list[str],
) -> dict[str, Any]:
    return _seal_contract({
        "schema_version": SCHEMA_VERSION,
        "mode": MODE,
        "status": status,
        "symbol": symbol,
        "venue": "OKX",
        "instrument_type": "SPOT",
        "book_half_used": "ASKS",
        "liquidity_scope": "STANDARD_BOOK_NON_RPI",
        "checksum": None,
        "checksum_policy": "NOT_APPLICABLE",
        "exchange_timestamp_ms": 0,
        "sequence_id": 0,
        "observed_at_ms": observed_at_ms,
        "max_age_ms": max_age_ms,
        "snapshot_id": "",
        "depth_requested": DEFAULT_DEPTH,
        "bids": [],
        "asks": [],
        "source": {
            "provider": PROVIDER,
            "endpoint": ENDPOINT,
            "public": True,
            "credentials_used": False,
        },
        "validation": {
            "timestamp_current": False,
            "bids_descending": False,
            "asks_ascending": False,
            "uncrossed": False,
            "cache_regression": False,
            "sequence_status": "UNAVAILABLE",
        },
        "book_hash": "",
        "hash_verified": False,
        "current": False,
        "planning_usable": False,
        "complete_book_verified": False,
        "is_executable_quote": False,
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
        "contract_hash": "",
        "contract_hash_verified": False,
    })


def public_order_book_placeholder(
    symbol: Any,
    *,
    observed_at_ms: Any = 0,
    status: str | None = None,
    blocker: str | None = None,
) -> dict[str, Any]:
    clean_symbol = _canonical_symbol(symbol)
    observed = _native_int(observed_at_ms) or 0
    return _safe_contract(
        symbol=clean_symbol or str(symbol or "").strip().upper(),
        status=status or ("NOT_CHECKED" if clean_symbol else "NOT_APPLICABLE"),
        observed_at_ms=observed,
        max_age_ms=DEFAULT_MAX_AGE_MS,
        blockers=[blocker or ("public_order_book_missing" if clean_symbol else "spot_symbol_not_applicable")],
    )


def _normalize_levels(value: Any, *, side: str, depth: int) -> tuple[list[dict[str, Any]], list[str]]:
    if not isinstance(value, list):
        return [], [f"{side}_levels_contract_invalid"]
    rows: list[dict[str, Any]] = []
    blockers: list[str] = []
    for index, raw in enumerate(value[:depth], start=1):
        if not isinstance(raw, (list, tuple)) or len(raw) < 2:
            blockers.append(f"{side}_level_shape_invalid")
            continue
        price = _positive_decimal_text(raw[0])
        size = _positive_decimal_text(raw[1])
        order_count = str(raw[3]).strip() if len(raw) > 3 else ""
        if not price or not size or (order_count and not order_count.isdigit()):
            blockers.append(f"{side}_level_decimal_invalid")
            continue
        rows.append({
            "level": index,
            "price": price,
            "size": size,
            "order_count": order_count,
        })
    if len(rows) != min(len(value), depth):
        blockers.append(f"{side}_levels_incomplete")
    return rows, list(dict.fromkeys(blockers))


def _ordered(rows: list[dict[str, Any]], *, ascending: bool) -> bool:
    prices = [Decimal(row["price"]) for row in rows]
    pairs = zip(prices, prices[1:])
    return all(left < right if ascending else left > right for left, right in pairs)


def _book_content(book: dict[str, Any]) -> dict[str, Any]:
    source = book.get("source") if isinstance(book.get("source"), dict) else {}
    return {
        "schema_version": book.get("schema_version"),
        "mode": book.get("mode"),
        "symbol": book.get("symbol"),
        "venue": book.get("venue"),
        "instrument_type": book.get("instrument_type"),
        "book_half_used": book.get("book_half_used"),
        "liquidity_scope": book.get("liquidity_scope"),
        "checksum": book.get("checksum"),
        "checksum_policy": book.get("checksum_policy"),
        "exchange_timestamp_ms": book.get("exchange_timestamp_ms"),
        "sequence_id": book.get("sequence_id"),
        "depth_requested": book.get("depth_requested"),
        "bids": book.get("bids"),
        "asks": book.get("asks"),
        "source": {
            "provider": source.get("provider"),
            "endpoint": source.get("endpoint"),
            "public": source.get("public"),
            "credentials_used": source.get("credentials_used"),
        },
    }


def build_okx_public_order_book(
    payload: Any,
    *,
    symbol: Any,
    observed_at_ms: Any,
    max_age_ms: int = DEFAULT_MAX_AGE_MS,
    depth: int = DEFAULT_DEPTH,
) -> dict[str, Any]:
    clean_symbol = _canonical_symbol(symbol)
    observed = _native_int(observed_at_ms) or 0
    clean_age = max(int(max_age_ms), 1)
    # This contract intentionally fixes the public snapshot at 20 levels.
    # Caller input must never widen the evidence scope or make validation throw.
    clean_depth = DEFAULT_DEPTH
    if not clean_symbol:
        return _safe_contract(
            symbol=str(symbol or "").strip().upper(),
            status="NOT_APPLICABLE",
            observed_at_ms=observed,
            max_age_ms=clean_age,
            blockers=["spot_symbol_not_applicable"],
        )
    if not isinstance(payload, dict) or payload.get("code") != "0":
        return _safe_contract(
            symbol=clean_symbol,
            status="BLOCK",
            observed_at_ms=observed,
            max_age_ms=clean_age,
            blockers=["public_order_book_response_invalid"],
        )
    data = payload.get("data")
    if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
        return _safe_contract(
            symbol=clean_symbol,
            status="NOT_CHECKED" if data == [] else "BLOCK",
            observed_at_ms=observed,
            max_age_ms=clean_age,
            blockers=["public_order_book_empty" if data == [] else "public_order_book_data_invalid"],
        )
    row = data[0]
    asks, ask_blockers = _normalize_levels(row.get("asks"), side="asks", depth=clean_depth)
    bids, bid_blockers = _normalize_levels(row.get("bids"), side="bids", depth=clean_depth)
    exchange_timestamp = _timestamp_ms(row.get("ts"))
    sequence_id = _native_int(row.get("seqId"))
    blockers = [*ask_blockers, *bid_blockers]
    if exchange_timestamp is None:
        blockers.append("public_order_book_timestamp_invalid")
    if sequence_id is None:
        blockers.append("public_order_book_sequence_invalid")
    asks_ascending = bool(asks) and _ordered(asks, ascending=True)
    bids_descending = bool(bids) and _ordered(bids, ascending=False)
    if asks and not asks_ascending:
        blockers.append("public_order_book_asks_not_ascending")
    if bids and not bids_descending:
        blockers.append("public_order_book_bids_not_descending")
    uncrossed = bool(asks and bids and Decimal(bids[0]["price"]) <= Decimal(asks[0]["price"]))
    if asks and bids and not uncrossed:
        blockers.append("public_order_book_crossed")
    if not asks or not bids:
        blockers.append("public_order_book_side_empty")

    structural_blockers = [
        blocker for blocker in blockers
        if blocker != "public_order_book_side_empty"
    ]
    if structural_blockers:
        status = "BLOCK"
    elif not asks or not bids:
        return _safe_contract(
            symbol=clean_symbol,
            status="NOT_CHECKED",
            observed_at_ms=observed,
            max_age_ms=clean_age,
            blockers=blockers,
        )
    elif len(asks) < 2:
        status = "NOT_CHECKED"
        blockers.append("public_order_book_depth_insufficient")
    else:
        age_ms = observed - int(exchange_timestamp or 0)
        if age_ms < -5_000:
            status = "BLOCK"
            blockers.append("public_order_book_from_future")
        elif age_ms > clean_age:
            status = "STALE"
            blockers.append("public_order_book_stale")
        else:
            status = "VERIFIED"

    book = _safe_contract(
        symbol=clean_symbol,
        status=status,
        observed_at_ms=observed,
        max_age_ms=clean_age,
        blockers=blockers,
    )
    book.update({
        "exchange_timestamp_ms": int(exchange_timestamp or 0),
        "sequence_id": int(sequence_id or 0),
        "observed_at_ms": observed,
        "depth_requested": clean_depth,
        "bids": bids,
        "asks": asks,
        "validation": {
            "timestamp_current": status == "VERIFIED",
            "bids_descending": bids_descending,
            "asks_ascending": asks_ascending,
            "uncrossed": uncrossed,
            "cache_regression": False,
            "sequence_status": "SNAPSHOT_ONLY",
        },
        "current": status == "VERIFIED",
        "planning_usable": status == "VERIFIED",
    })
    if exchange_timestamp and sequence_id is not None and asks and bids:
        book["book_hash"] = _canonical_hash(_book_content(book))
        book["snapshot_id"] = f"{clean_symbol}:{exchange_timestamp}:{sequence_id}:{book['book_hash'][:12]}"
        book["hash_verified"] = True
    return _seal_contract(book)


def _verify_normalized_levels(value: Any, *, side: str, ascending: bool) -> tuple[bool, list[str]]:
    if not isinstance(value, list) or not value:
        return False, [f"{side}_levels_missing"]
    if len(value) > DEFAULT_DEPTH:
        return False, [f"{side}_levels_exceed_contract"]
    rows: list[dict[str, Any]] = []
    blockers: list[str] = []
    for index, row in enumerate(value, start=1):
        if not isinstance(row, dict) or set(row) != {"level", "price", "size", "order_count"}:
            blockers.append(f"{side}_level_contract_invalid")
            continue
        price = _positive_decimal_text(row.get("price"))
        size = _positive_decimal_text(row.get("size"))
        if (
            row.get("level") != index
            or not price
            or not size
            or row.get("price") != price
            or row.get("size") != size
        ):
            blockers.append(f"{side}_level_value_invalid")
            continue
        order_count = row.get("order_count")
        if not isinstance(order_count, str) or (order_count and not order_count.isdigit()):
            blockers.append(f"{side}_order_count_invalid")
            continue
        rows.append(row)
    if len(rows) != len(value) or not _ordered(rows, ascending=ascending):
        blockers.append(f"{side}_ordering_invalid")
    return not blockers, list(dict.fromkeys(blockers))


def verify_public_order_book(
    value: Any,
    *,
    expected_symbol: Any,
    now_ms: Any,
) -> dict[str, Any]:
    book = copy.deepcopy(value) if isinstance(value, dict) else {}
    expected = _canonical_symbol(expected_symbol)
    expected_text = str(expected_symbol or "").strip().upper()
    if not book:
        return {"status": "NOT_CHECKED", "blockers": ["public_order_book_missing"], "order_book": {}}
    if book.get("status") == "NOT_APPLICABLE" and not expected:
        source = book.get("source") if isinstance(book.get("source"), dict) else {}
        permissions = book.get("permissions") if isinstance(book.get("permissions"), dict) else {}
        validation = book.get("validation") if isinstance(book.get("validation"), dict) else {}
        contract_valid = bool(
            _HASH_RE.fullmatch(str(book.get("contract_hash") or ""))
            and book.get("contract_hash") == _canonical_hash(_contract_content(book))
            and book.get("contract_hash_verified") is True
            and book.get("schema_version") == SCHEMA_VERSION
            and book.get("mode") == MODE
            and book.get("symbol") == expected_text
            and book.get("venue") == "OKX"
            and book.get("instrument_type") == "SPOT"
            and book.get("book_half_used") == "ASKS"
            and book.get("liquidity_scope") == "STANDARD_BOOK_NON_RPI"
            and book.get("checksum") is None
            and book.get("checksum_policy") == "NOT_APPLICABLE"
            and book.get("depth_requested") == DEFAULT_DEPTH
            and book.get("exchange_timestamp_ms") == 0
            and book.get("sequence_id") == 0
            and book.get("snapshot_id") == ""
            and book.get("bids") == []
            and book.get("asks") == []
            and source == {
                "provider": PROVIDER,
                "endpoint": ENDPOINT,
                "public": True,
                "credentials_used": False,
            }
            and validation == {
                "timestamp_current": False,
                "bids_descending": False,
                "asks_ascending": False,
                "uncrossed": False,
                "cache_regression": False,
                "sequence_status": "UNAVAILABLE",
            }
            and book.get("book_hash") == ""
            and book.get("hash_verified") is False
            and book.get("current") is False
            and book.get("planning_usable") is False
            and book.get("complete_book_verified") is False
            and book.get("is_executable_quote") is False
            and permissions == {
                "planning_only": True,
                "order_submission_allowed": False,
                "execution_allowed": False,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
            and book.get("execution_allowed") is False
            and book.get("paper_authorized") is False
            and book.get("live_order_allowed") is False
            and isinstance(book.get("blockers"), list)
            and bool(book.get("blockers"))
        )
        return {
            "status": "NOT_CHECKED" if contract_valid else "BLOCK",
            "blockers": [
                "public_order_book_not_applicable"
                if contract_valid
                else "public_order_book_not_applicable_contract_invalid"
            ],
            "order_book": book,
        }
    blockers: list[str] = []
    if book.get("schema_version") != SCHEMA_VERSION or book.get("mode") != MODE:
        blockers.append("public_order_book_schema_invalid")
    if book.get("symbol") != expected or not expected:
        blockers.append("public_order_book_symbol_mismatch")
    if (
        book.get("venue") != "OKX"
        or book.get("instrument_type") != "SPOT"
        or book.get("book_half_used") != "ASKS"
        or book.get("liquidity_scope") != "STANDARD_BOOK_NON_RPI"
        or book.get("checksum") is not None
        or book.get("checksum_policy") != "NOT_APPLICABLE"
        or book.get("depth_requested") != DEFAULT_DEPTH
        or book.get("complete_book_verified") is not False
        or book.get("is_executable_quote") is not False
    ):
        blockers.append("public_order_book_scope_invalid")
    source = book.get("source") if isinstance(book.get("source"), dict) else {}
    if source != {
        "provider": PROVIDER,
        "endpoint": ENDPOINT,
        "public": True,
        "credentials_used": False,
    }:
        blockers.append("public_order_book_source_invalid")
    permissions = book.get("permissions") if isinstance(book.get("permissions"), dict) else {}
    if permissions != {
        "planning_only": True,
        "order_submission_allowed": False,
        "execution_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    } or any(book.get(key) is not False for key in ("execution_allowed", "paper_authorized", "live_order_allowed")):
        blockers.append("public_order_book_authority_invalid")
    expected_contract_hash = _canonical_hash(_contract_content(book))
    if (
        not _HASH_RE.fullmatch(str(book.get("contract_hash") or ""))
        or book.get("contract_hash") != expected_contract_hash
        or book.get("contract_hash_verified") is not True
    ):
        blockers.append("public_order_book_contract_hash_invalid")
    safe_empty = bool(
        book.get("status") in {"NOT_CHECKED", "UNAVAILABLE"}
        and book.get("bids") == []
        and book.get("asks") == []
        and book.get("exchange_timestamp_ms") == 0
        and book.get("sequence_id") == 0
        and book.get("snapshot_id") == ""
        and book.get("book_hash") == ""
        and book.get("hash_verified") is False
        and book.get("current") is False
        and book.get("planning_usable") is False
        and book.get("complete_book_verified") is False
        and book.get("is_executable_quote") is False
    )
    if safe_empty and not blockers:
        return {
            "status": "NOT_CHECKED",
            "blockers": list(book.get("blockers") or ["public_order_book_missing"]),
            "order_book": book,
        }
    asks_valid, ask_blockers = _verify_normalized_levels(book.get("asks"), side="asks", ascending=True)
    bids_valid, bid_blockers = _verify_normalized_levels(book.get("bids"), side="bids", ascending=False)
    blockers.extend(ask_blockers)
    blockers.extend(bid_blockers)
    asks = book.get("asks") if asks_valid else []
    bids = book.get("bids") if bids_valid else []
    if asks and bids and Decimal(bids[0]["price"]) > Decimal(asks[0]["price"]):
        blockers.append("public_order_book_crossed")
    exchange_timestamp = _native_int(book.get("exchange_timestamp_ms"))
    sequence_id = _native_int(book.get("sequence_id"))
    observed = _native_int(book.get("observed_at_ms"))
    current_time = _native_int(now_ms)
    max_age = _native_int(book.get("max_age_ms"))
    if not exchange_timestamp or sequence_id is None or observed is None or current_time is None or not max_age:
        blockers.append("public_order_book_time_invalid")
    else:
        age = current_time - exchange_timestamp
        if age < -5_000:
            blockers.append("public_order_book_from_future")
        elif age > max_age:
            blockers.append("public_order_book_stale")
    expected_hash = _canonical_hash(_book_content(book))
    if not _HASH_RE.fullmatch(str(book.get("book_hash") or "")) or book.get("book_hash") != expected_hash or book.get("hash_verified") is not True:
        blockers.append("public_order_book_hash_invalid")
    validation = book.get("validation") if isinstance(book.get("validation"), dict) else {}
    if set(validation) != {
        "timestamp_current", "bids_descending", "asks_ascending", "uncrossed",
        "cache_regression", "sequence_status",
    }:
        blockers.append("public_order_book_validation_invalid")
    if validation.get("cache_regression") is True:
        blockers.append("public_order_book_cache_regression")
    if validation.get("sequence_status") not in {"SNAPSHOT_ONLY", "MONOTONIC_OR_EQUAL", "EPOCH_UNPROVEN"}:
        blockers.append("public_order_book_sequence_status_invalid")
    if book.get("status") == "VERIFIED" and (
        validation.get("timestamp_current") is not True
        or validation.get("bids_descending") is not True
        or validation.get("asks_ascending") is not True
        or validation.get("uncrossed") is not True
        or book.get("current") is not True
        or book.get("planning_usable") is not True
        or list(book.get("blockers") or [])
    ):
        blockers.append("public_order_book_verified_state_invalid")
    expected_snapshot_id = (
        f"{expected}:{exchange_timestamp}:{sequence_id}:{expected_hash[:12]}"
        if expected and exchange_timestamp and sequence_id is not None
        else ""
    )
    if book.get("snapshot_id") != expected_snapshot_id:
        blockers.append("public_order_book_snapshot_id_invalid")
    if book.get("status") == "BLOCK":
        blockers.append("public_order_book_blocked")
    status = "PASS" if not blockers and book.get("status") == "VERIFIED" and len(asks) >= 2 else "BLOCK"
    if status == "BLOCK" and book.get("status") in {"NOT_CHECKED", "STALE", "UNAVAILABLE"} and not any(
        blocker.endswith(("invalid", "mismatch", "crossed", "regression", "blocked"))
        for blocker in blockers
    ):
        status = "NOT_CHECKED"
    book["age_ms"] = current_time - exchange_timestamp if current_time is not None and exchange_timestamp else None
    return {"status": status, "blockers": list(dict.fromkeys(blockers)), "order_book": book}


def _microstructure_content(value: dict[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(item)
        for key, item in value.items()
        if key not in {"microstructure_hash", "hash_verified"}
    }


def _seal_microstructure(value: dict[str, Any]) -> dict[str, Any]:
    value["microstructure_hash"] = _canonical_hash(_microstructure_content(value))
    value["hash_verified"] = True
    return value


def _safe_microstructure(
    *,
    symbol: str,
    status: str,
    blockers: list[str],
) -> dict[str, Any]:
    return _seal_microstructure({
        "schema_version": MICROSTRUCTURE_SCHEMA_VERSION,
        "mode": MICROSTRUCTURE_MODE,
        "status": status,
        "symbol": symbol,
        "venue": "OKX",
        "instrument_type": "SPOT",
        "book_sides_observed": "NONE",
        "liquidity_scope": "STANDARD_BOOK_NON_RPI",
        "evidence": {
            "book_snapshot_id": "",
            "book_hash": "",
            "book_contract_hash": "",
            "source_provider": PROVIDER,
            "source_endpoint": ENDPOINT,
            "exchange_timestamp_ms": 0,
            "observed_at_ms": 0,
            "evaluated_at_ms": 0,
            "max_age_ms": DEFAULT_MAX_AGE_MS,
            "depth_requested": DEFAULT_DEPTH,
            "observed_bid_levels": 0,
            "observed_ask_levels": 0,
            "comparison_level_count": 0,
            "sequence_status": "UNAVAILABLE",
            "sequence_continuity": "NOT_PROVABLE_REST",
            "checksum_policy": "NOT_APPLICABLE",
        },
        "top_of_book": {
            "best_bid": "",
            "best_ask": "",
            "mid_price": "",
            "spread_quote": "",
            "spread_bps": "",
            "spread_bps_basis": "MID_PRICE",
            "spread_bps_places": MICROSTRUCTURE_SPREAD_BPS_PLACES,
            "spread_bps_rounding": "HALF_EVEN",
        },
        "visible_depth": {
            "basis": "QUOTE_NOTIONAL",
            "bid_base_total": "",
            "ask_base_total": "",
            "bid_quote_notional": "",
            "ask_quote_notional": "",
            "total_quote_notional": "",
            "bid_share": "",
            "ask_share": "",
            "bid_to_ask_quote_ratio": "",
            "share_places": MICROSTRUCTURE_RATIO_PLACES,
            "ratio_places": MICROSTRUCTURE_RATIO_PLACES,
            "ratio_rounding": "HALF_EVEN",
            "complete_book_verified": False,
        },
        "price_band_depth": {
            "basis": "SYMMETRIC_MID_PRICE_BPS",
            "bands_bps": list(MICROSTRUCTURE_PRICE_BANDS_BPS),
            "boundary_inclusive": True,
            "reference_mid_price": "",
            "coverage_rule": "VISIBLE_PREFIX_REACHES_BAND_BOUNDARY",
            "quote_notional_semantics": "VISIBLE_LOWER_BOUND_WHEN_BOUNDARY_NOT_COVERED",
            "rows": [],
            "complete_book_verified": False,
        },
        "interpretation": {
            "descriptive_only": True,
            "signal_allowed": False,
            "direction_inferred": False,
            "trade_flow_inferred": False,
            "spoofing_checked": False,
        },
        "unknowns": {
            "complete_order_book": "NOT_CHECKED",
            "rpi_access": "NOT_CHECKED",
            "hidden_liquidity": "NOT_CHECKED",
            "queue_position": "NOT_CHECKED",
            "cancellations_after_snapshot": "NOT_CHECKED",
            "execution_probability": "NOT_CHECKED",
            "future_direction": "NOT_CHECKED",
        },
        "permissions": {
            "planning_only": True,
            "order_submission_allowed": False,
            "execution_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "read_only": True,
        "execution_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "blockers": list(dict.fromkeys(blockers)),
        "microstructure_hash": "",
        "hash_verified": False,
    })


def build_public_order_book_microstructure(
    order_book: Any,
    *,
    expected_symbol: Any,
    now_ms: Any,
) -> dict[str, Any]:
    """Derive descriptive two-sided L2 facts without creating a trading signal."""

    verification = verify_public_order_book(
        order_book,
        expected_symbol=expected_symbol,
        now_ms=now_ms,
    )
    book = verification.get("order_book") if isinstance(verification.get("order_book"), dict) else {}
    symbol = str(book.get("symbol") or expected_symbol or "").strip().upper()
    verification_status = str(verification.get("status") or "BLOCK")
    if verification_status == "BLOCK":
        return _safe_microstructure(
            symbol=symbol,
            status="BLOCK",
            blockers=list(verification.get("blockers") or ["public_order_book_contract_blocked"]),
        )
    if book.get("status") == "NOT_APPLICABLE" and verification_status == "NOT_CHECKED":
        return _safe_microstructure(
            symbol=symbol,
            status="NOT_APPLICABLE",
            blockers=["public_microstructure_not_applicable"],
        )
    if verification_status != "PASS":
        return _safe_microstructure(
            symbol=symbol,
            status="NOT_CHECKED",
            blockers=list(verification.get("blockers") or ["public_order_book_not_verified"]),
        )

    try:
        bids = list(book.get("bids") or [])
        asks = list(book.get("asks") or [])
        if not bids or not asks:
            raise ArithmeticError("public_microstructure_side_empty")
        comparison_level_count = min(len(bids), len(asks))
        comparison_bids = bids[:comparison_level_count]
        comparison_asks = asks[:comparison_level_count]
        best_bid = _fraction(bids[0]["price"])
        best_ask = _fraction(asks[0]["price"])
        if best_bid > best_ask:
            raise ArithmeticError("public_microstructure_crossed")
        midpoint = (best_bid + best_ask) / 2
        spread = best_ask - best_bid
        bid_base_total = sum((_fraction(row["size"]) for row in comparison_bids), Fraction(0, 1))
        ask_base_total = sum((_fraction(row["size"]) for row in comparison_asks), Fraction(0, 1))
        bid_quote_total = sum(
            (_fraction(row["price"]) * _fraction(row["size"]) for row in comparison_bids),
            Fraction(0, 1),
        )
        ask_quote_total = sum(
            (_fraction(row["price"]) * _fraction(row["size"]) for row in comparison_asks),
            Fraction(0, 1),
        )
        total_quote = bid_quote_total + ask_quote_total
        if midpoint <= 0 or bid_quote_total <= 0 or ask_quote_total <= 0 or total_quote <= 0:
            raise ArithmeticError("public_microstructure_total_invalid")
        bid_share_scaled = _scaled_fraction(
            bid_quote_total / total_quote,
            places=MICROSTRUCTURE_RATIO_PLACES,
        )
        share_scale = 10 ** MICROSTRUCTURE_RATIO_PLACES
        bid_share_scaled = max(0, min(share_scale, bid_share_scaled))
        ask_share_scaled = share_scale - bid_share_scaled
        price_band_rows: list[dict[str, Any]] = []
        for band_bps in MICROSTRUCTURE_PRICE_BANDS_BPS:
            band_fraction = Fraction(band_bps, 10_000)
            bid_floor = midpoint * (Fraction(1, 1) - band_fraction)
            ask_ceiling = midpoint * (Fraction(1, 1) + band_fraction)
            band_bids = [
                row for row in bids
                if _fraction(row["price"]) >= bid_floor
            ]
            band_asks = [
                row for row in asks
                if _fraction(row["price"]) <= ask_ceiling
            ]
            visible_bid_base = sum(
                (_fraction(row["size"]) for row in band_bids),
                Fraction(0, 1),
            )
            visible_ask_base = sum(
                (_fraction(row["size"]) for row in band_asks),
                Fraction(0, 1),
            )
            visible_bid_quote = sum(
                (_fraction(row["price"]) * _fraction(row["size"]) for row in band_bids),
                Fraction(0, 1),
            )
            visible_ask_quote = sum(
                (_fraction(row["price"]) * _fraction(row["size"]) for row in band_asks),
                Fraction(0, 1),
            )
            bid_boundary_covered = _fraction(bids[-1]["price"]) <= bid_floor
            ask_boundary_covered = _fraction(asks[-1]["price"]) >= ask_ceiling
            price_band_rows.append({
                "band_bps": band_bps,
                "bid_floor_price": _finite_fraction_text(bid_floor),
                "ask_ceiling_price": _finite_fraction_text(ask_ceiling),
                "visible_bid_levels": len(band_bids),
                "visible_ask_levels": len(band_asks),
                "visible_bid_base_total": _finite_fraction_text(visible_bid_base),
                "visible_ask_base_total": _finite_fraction_text(visible_ask_base),
                "visible_bid_quote_notional": _finite_fraction_text(visible_bid_quote),
                "visible_ask_quote_notional": _finite_fraction_text(visible_ask_quote),
                "bid_band_boundary_covered": bid_boundary_covered,
                "ask_band_boundary_covered": ask_boundary_covered,
                "two_sided_band_boundary_covered": (
                    bid_boundary_covered and ask_boundary_covered
                ),
            })
    except (ArithmeticError, InvalidOperation, KeyError, TypeError, ValueError, ZeroDivisionError):
        return _safe_microstructure(
            symbol=symbol,
            status="BLOCK",
            blockers=["public_microstructure_calculation_invalid"],
        )

    source = book.get("source") if isinstance(book.get("source"), dict) else {}
    validation = book.get("validation") if isinstance(book.get("validation"), dict) else {}
    value = _safe_microstructure(symbol=symbol, status="OBSERVATION_ONLY", blockers=[])
    value.update({
        "book_sides_observed": "BIDS_AND_ASKS",
        "evidence": {
            "book_snapshot_id": str(book.get("snapshot_id") or ""),
            "book_hash": str(book.get("book_hash") or ""),
            "book_contract_hash": str(book.get("contract_hash") or ""),
            "source_provider": str(source.get("provider") or ""),
            "source_endpoint": str(source.get("endpoint") or ""),
            "exchange_timestamp_ms": int(book.get("exchange_timestamp_ms") or 0),
            "observed_at_ms": int(book.get("observed_at_ms") or 0),
            "evaluated_at_ms": int(now_ms) if type(now_ms) is int else 0,
            "max_age_ms": int(book.get("max_age_ms") or 0),
            "depth_requested": int(book.get("depth_requested") or 0),
            "observed_bid_levels": len(bids),
            "observed_ask_levels": len(asks),
            "comparison_level_count": comparison_level_count,
            "sequence_status": str(validation.get("sequence_status") or ""),
            "sequence_continuity": "NOT_PROVABLE_REST",
            "checksum_policy": str(book.get("checksum_policy") or ""),
        },
        "top_of_book": {
            "best_bid": _finite_fraction_text(best_bid),
            "best_ask": _finite_fraction_text(best_ask),
            "mid_price": _finite_fraction_text(midpoint),
            "spread_quote": _finite_fraction_text(spread),
            "spread_bps": _rounded_fraction_text(
                spread / midpoint * 10_000,
                places=MICROSTRUCTURE_SPREAD_BPS_PLACES,
            ),
            "spread_bps_basis": "MID_PRICE",
            "spread_bps_places": MICROSTRUCTURE_SPREAD_BPS_PLACES,
            "spread_bps_rounding": "HALF_EVEN",
        },
        "visible_depth": {
            "basis": "QUOTE_NOTIONAL",
            "bid_base_total": _finite_fraction_text(bid_base_total),
            "ask_base_total": _finite_fraction_text(ask_base_total),
            "bid_quote_notional": _finite_fraction_text(bid_quote_total),
            "ask_quote_notional": _finite_fraction_text(ask_quote_total),
            "total_quote_notional": _finite_fraction_text(total_quote),
            "bid_share": _scaled_decimal_text(
                bid_share_scaled,
                places=MICROSTRUCTURE_RATIO_PLACES,
            ),
            "ask_share": _scaled_decimal_text(
                ask_share_scaled,
                places=MICROSTRUCTURE_RATIO_PLACES,
            ),
            "bid_to_ask_quote_ratio": _rounded_fraction_text(
                bid_quote_total / ask_quote_total,
                places=MICROSTRUCTURE_RATIO_PLACES,
            ),
            "share_places": MICROSTRUCTURE_RATIO_PLACES,
            "ratio_places": MICROSTRUCTURE_RATIO_PLACES,
            "ratio_rounding": "HALF_EVEN",
            "complete_book_verified": False,
        },
        "price_band_depth": {
            "basis": "SYMMETRIC_MID_PRICE_BPS",
            "bands_bps": list(MICROSTRUCTURE_PRICE_BANDS_BPS),
            "boundary_inclusive": True,
            "reference_mid_price": _finite_fraction_text(midpoint),
            "coverage_rule": "VISIBLE_PREFIX_REACHES_BAND_BOUNDARY",
            "quote_notional_semantics": "VISIBLE_LOWER_BOUND_WHEN_BOUNDARY_NOT_COVERED",
            "rows": price_band_rows,
            "complete_book_verified": False,
        },
    })
    return _seal_microstructure(value)


def legacy_okx_order_book_payload(book: dict[str, Any]) -> dict[str, Any]:
    if book.get("status") != "VERIFIED" or book.get("current") is not True:
        return {"code": "51000", "msg": "public order book unavailable", "data": []}
    def raw_rows(rows: list[dict[str, Any]]) -> list[list[str]]:
        return [[row["price"], row["size"], "0", row["order_count"]] for row in rows]
    return {
        "code": "0",
        "msg": "",
        "data": [{
            "asks": raw_rows(list(book.get("asks") or [])),
            "bids": raw_rows(list(book.get("bids") or [])),
            "ts": str(book.get("exchange_timestamp_ms") or ""),
            "seqId": int(book.get("sequence_id") or 0),
        }],
    }


class PublicOrderBookService:
    def __init__(
        self,
        *,
        fetch_payload: Callable[[str, dict[str, str]], dict[str, Any]],
        now_ms: Callable[[], int],
        max_age_ms: int = DEFAULT_MAX_AGE_MS,
        min_refresh_interval_ms: int = DEFAULT_MIN_REFRESH_MS,
        max_cache_entries: int = 64,
    ) -> None:
        self.fetch_payload = fetch_payload
        self.now_ms = now_ms
        self.max_age_ms = max(int(max_age_ms), 1)
        self.min_refresh_interval_ms = max(int(min_refresh_interval_ms), 1)
        self.max_cache_entries = max(int(max_cache_entries), 1)
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._inflight: dict[str, dict[str, Any]] = {}

    def _view(self, snapshot: dict[str, Any], now: int, *, cached: bool) -> dict[str, Any]:
        view = copy.deepcopy(snapshot)
        timestamp = _native_int(view.get("exchange_timestamp_ms")) or 0
        age = now - timestamp if timestamp else None
        view["cache_age_ms"] = max(now - int(view.get("observed_at_ms") or 0), 0)
        view["age_ms"] = age
        view["cached"] = cached
        view["current"] = bool(
            view.get("status") == "VERIFIED"
            and age is not None
            and -5_000 <= age <= self.max_age_ms
        )
        view["planning_usable"] = view["current"]
        if view.get("status") == "VERIFIED" and not view["current"]:
            view["status"] = "STALE"
            view["blockers"] = list(dict.fromkeys([*list(view.get("blockers") or []), "public_order_book_stale"]))
        return _seal_contract(view)

    def _remember(self, symbol: str, snapshot: dict[str, Any]) -> None:
        self._cache[symbol] = copy.deepcopy(snapshot)
        if len(self._cache) <= self.max_cache_entries:
            return
        ordered = sorted(self._cache.items(), key=lambda item: int(item[1].get("observed_at_ms") or 0))
        for key, _value in ordered[: len(self._cache) - self.max_cache_entries]:
            self._cache.pop(key, None)

    def snapshot(self, symbol: Any, *, force: bool = False) -> dict[str, Any]:
        clean_symbol = _canonical_symbol(symbol)
        now = _native_int(self.now_ms()) or 0
        if not clean_symbol:
            return public_order_book_placeholder(symbol, observed_at_ms=now)
        with self._lock:
            cached_snapshot = copy.deepcopy(self._cache.get(clean_symbol))
        if cached_snapshot:
            cached_view = self._view(cached_snapshot, now, cached=True)
            cache_age = int(cached_view.get("cache_age_ms") or 0)
            if cached_view.get("current") is True and (not force or cache_age < self.min_refresh_interval_ms):
                return cached_view

        with self._lock:
            existing = self._inflight.get(clean_symbol)
            if existing is None:
                entry: dict[str, Any] = {"event": threading.Event(), "result": None}
                self._inflight[clean_symbol] = entry
                leader = True
            else:
                entry = existing
                leader = False
        if not leader:
            entry["event"].wait()
            return copy.deepcopy(entry["result"])

        result: dict[str, Any] | None = None
        try:
            with self._lock:
                cached_snapshot = copy.deepcopy(self._cache.get(clean_symbol))
            try:
                payload = self.fetch_payload(ENDPOINT, {"instId": clean_symbol, "sz": str(DEFAULT_DEPTH)})
            except Exception as exc:
                if cached_snapshot:
                    result = self._view(cached_snapshot, now, cached=True)
                    result["status"] = "STALE"
                    result["current"] = False
                    result["planning_usable"] = False
                    result["refresh_error"] = str(exc)[:240]
                    result["blockers"] = list(dict.fromkeys([*list(result.get("blockers") or []), "public_order_book_refresh_failed"]))
                else:
                    result = public_order_book_placeholder(
                        clean_symbol,
                        observed_at_ms=now,
                        status="UNAVAILABLE",
                        blocker="public_order_book_refresh_failed",
                    )
                    result["refresh_error"] = str(exc)[:240]
            else:
                fresh = build_okx_public_order_book(
                    payload,
                    symbol=clean_symbol,
                    observed_at_ms=now,
                    max_age_ms=self.max_age_ms,
                )
                if cached_snapshot and fresh.get("status") == "VERIFIED":
                    old_timestamp = _native_int(cached_snapshot.get("exchange_timestamp_ms")) or 0
                    new_timestamp = _native_int(fresh.get("exchange_timestamp_ms")) or 0
                    old_sequence = _native_int(cached_snapshot.get("sequence_id")) or 0
                    new_sequence = _native_int(fresh.get("sequence_id")) or 0
                    if new_timestamp < old_timestamp:
                        result = self._view(cached_snapshot, now, cached=True)
                        result["status"] = "BLOCK"
                        result["current"] = False
                        result["planning_usable"] = False
                        result["validation"] = {**dict(result.get("validation") or {}), "cache_regression": True}
                        result["blockers"] = list(dict.fromkeys([*list(result.get("blockers") or []), "public_order_book_cache_regression"]))
                    elif new_timestamp == old_timestamp:
                        if fresh.get("book_hash") == cached_snapshot.get("book_hash"):
                            result = self._view(cached_snapshot, now, cached=True)
                        else:
                            result = self._view(cached_snapshot, now, cached=True)
                            result["status"] = "BLOCK"
                            result["current"] = False
                            result["planning_usable"] = False
                            result["blockers"] = list(dict.fromkeys([*list(result.get("blockers") or []), "public_order_book_same_timestamp_conflict"]))
                    elif new_sequence < old_sequence:
                        fresh["validation"] = {
                            **dict(fresh.get("validation") or {}),
                            "sequence_status": "EPOCH_UNPROVEN",
                        }
                    else:
                        fresh["validation"] = {
                            **dict(fresh.get("validation") or {}),
                            "sequence_status": "MONOTONIC_OR_EQUAL",
                        }
                if result is None:
                    fresh = _seal_contract(fresh)
                    result = self._view(fresh, now, cached=False)
                    if fresh.get("status") == "VERIFIED":
                        with self._lock:
                            self._remember(clean_symbol, fresh)
        except Exception as exc:
            result = public_order_book_placeholder(
                clean_symbol,
                observed_at_ms=now,
                status="BLOCK",
                blocker="public_order_book_internal_failure",
            )
            result["refresh_error"] = str(exc)[:240]
        finally:
            if result is None:
                result = public_order_book_placeholder(
                    clean_symbol,
                    observed_at_ms=now,
                    status="BLOCK",
                    blocker="public_order_book_internal_failure",
                )
            result = _seal_contract(result)
            with self._lock:
                entry["result"] = copy.deepcopy(result)
                if self._inflight.get(clean_symbol) is entry:
                    self._inflight.pop(clean_symbol, None)
                entry["event"].set()
        return copy.deepcopy(result)


__all__ = [
    "DEFAULT_DEPTH",
    "DEFAULT_MAX_AGE_MS",
    "MICROSTRUCTURE_MODE",
    "MICROSTRUCTURE_SCHEMA_VERSION",
    "PublicOrderBookService",
    "build_okx_public_order_book",
    "build_public_order_book_microstructure",
    "legacy_okx_order_book_payload",
    "public_order_book_placeholder",
    "verify_public_order_book",
]
