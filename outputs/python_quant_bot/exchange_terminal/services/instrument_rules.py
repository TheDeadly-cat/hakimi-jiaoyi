from __future__ import annotations

import copy
import hashlib
import json
import re
import threading
from decimal import Decimal, InvalidOperation
from typing import Any, Callable


SCHEMA_VERSION = "public-instrument-rules-v1"
MODE = "PUBLIC_READ_ONLY"
PROVIDER = "OKX_PUBLIC_API"
ENDPOINT = "/api/v5/public/instruments"
DEFAULT_MAX_AGE_MS = 300_000
_SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,20}-[A-Z0-9]{2,20}$")
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_RULE_PARAMS = {"tickSz", "lotSz", "minSz", "maxLmtSz", "maxMktSz"}


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _native_int(value: Any) -> int | None:
    if type(value) is not int or value < 0:
        return None
    return value


def _canonical_symbol(value: Any) -> str:
    text = str(value or "").strip().upper()
    return text if _SYMBOL_RE.fullmatch(text) else ""


def _positive_decimal(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if not text:
        return ""
    try:
        decimal_value = Decimal(text)
    except InvalidOperation:
        return ""
    if not decimal_value.is_finite() or decimal_value <= 0:
        return ""
    normalized = format(decimal_value, "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized


def _optional_nonnegative_decimal(value: Any) -> str:
    if value is None or value == "":
        return ""
    if not isinstance(value, str):
        return ""
    try:
        decimal_value = Decimal(value.strip())
    except InvalidOperation:
        return ""
    if not decimal_value.is_finite() or decimal_value < 0:
        return ""
    normalized = format(decimal_value, "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized or "0"


def _timestamp_text(value: Any) -> str:
    text = str(value or "").strip()
    return text if text.isdigit() and int(text) >= 0 else ""


def _safe_contract(
    *,
    symbol: str,
    status: str,
    captured_at_ms: int,
    max_age_ms: int,
    blockers: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": MODE,
        "status": status,
        "symbol": symbol,
        "asset_type": "crypto" if _canonical_symbol(symbol) else "not_applicable",
        "venue": "OKX",
        "instrument_type": "SPOT",
        "instrument_state": "",
        "tick_size": "",
        "lot_size": "",
        "minimum_order_size": "",
        "minimum_cost": None,
        "size_unit": "",
        "price_unit": "",
        "upcoming_changes": [],
        "source": {
            "provider": PROVIDER,
            "endpoint": ENDPOINT,
            "captured_at_ms": captured_at_ms,
            "max_age_ms": max_age_ms,
        },
        "verification": {
            "venue_rules_verified": False,
            "account_tradeability_verified": False,
            "account_fee_verified": False,
            "minimum_cost_verified": False,
        },
        "rules_hash": "",
        "snapshot_hash": "",
        "hash_verified": False,
        "current": False,
        "public_only": True,
        "credentials_used": False,
        "read_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
        "blockers": list(blockers or []),
    }


def public_instrument_rules_placeholder(
    symbol: Any,
    *,
    captured_at_ms: Any = 0,
    status: str | None = None,
    blocker: str | None = None,
) -> dict[str, Any]:
    clean_symbol = _canonical_symbol(symbol)
    captured = _native_int(captured_at_ms) or 0
    resolved_status = status or ("NOT_CHECKED" if clean_symbol else "NOT_APPLICABLE")
    resolved_blocker = blocker or (
        "instrument_rules_missing" if clean_symbol else "spot_symbol_not_applicable"
    )
    return _safe_contract(
        symbol=clean_symbol or str(symbol or "").strip().upper(),
        status=resolved_status,
        captured_at_ms=captured,
        max_age_ms=DEFAULT_MAX_AGE_MS,
        blockers=[resolved_blocker],
    )


def _normalized_upcoming_changes(value: Any) -> tuple[list[dict[str, str]], list[str]]:
    if value is None or value == "":
        return [], []
    if not isinstance(value, list):
        return [], ["upcoming_changes_contract_invalid"]
    rows: list[dict[str, str]] = []
    blockers: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            blockers.append("upcoming_change_item_invalid")
            continue
        param = str(item.get("param") or "").strip()
        new_value = str(item.get("newValue") or "").strip()
        effective_at_ms = _timestamp_text(item.get("effTime"))
        if param not in _RULE_PARAMS or not new_value or not effective_at_ms:
            blockers.append("upcoming_change_fields_invalid")
            continue
        rows.append({
            "param": param,
            "new_value": new_value,
            "effective_at_ms": effective_at_ms,
        })
    rows.sort(key=lambda row: (row["effective_at_ms"], row["param"], row["new_value"]))
    return rows, blockers


def _rule_content(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": snapshot.get("schema_version"),
        "mode": snapshot.get("mode"),
        "venue": snapshot.get("venue"),
        "symbol": snapshot.get("symbol"),
        "instrument_type": snapshot.get("instrument_type"),
        "instrument_state": snapshot.get("instrument_state"),
        "tick_size": snapshot.get("tick_size"),
        "lot_size": snapshot.get("lot_size"),
        "minimum_order_size": snapshot.get("minimum_order_size"),
        "minimum_cost": snapshot.get("minimum_cost"),
        "size_unit": snapshot.get("size_unit"),
        "price_unit": snapshot.get("price_unit"),
        "ccxt_symbol": snapshot.get("ccxt_symbol"),
        "fee_group_id": snapshot.get("fee_group_id"),
        "list_time_ms": snapshot.get("list_time_ms"),
        "continuous_from_ms": snapshot.get("continuous_from_ms"),
        "offline_at_ms": snapshot.get("offline_at_ms"),
        "max_limit_size": snapshot.get("max_limit_size"),
        "max_market_size": snapshot.get("max_market_size"),
        "upcoming_changes": snapshot.get("upcoming_changes"),
        "public_only": snapshot.get("public_only"),
        "credentials_used": snapshot.get("credentials_used"),
        "read_only": snapshot.get("read_only"),
        "paper_authorized": snapshot.get("paper_authorized"),
        "live_order_allowed": snapshot.get("live_order_allowed"),
        "verification": snapshot.get("verification"),
    }


def _snapshot_seal(snapshot: dict[str, Any]) -> str:
    source = snapshot.get("source") if isinstance(snapshot.get("source"), dict) else {}
    return _canonical_hash({
        "rules_hash": snapshot.get("rules_hash"),
        "provider": source.get("provider"),
        "endpoint": source.get("endpoint"),
        "captured_at_ms": source.get("captured_at_ms"),
        "max_age_ms": source.get("max_age_ms"),
    })


def build_okx_public_spot_rules(
    payload: Any,
    *,
    symbol: Any,
    captured_at_ms: Any,
    max_age_ms: Any = DEFAULT_MAX_AGE_MS,
) -> dict[str, Any]:
    clean_symbol = _canonical_symbol(symbol)
    captured = _native_int(captured_at_ms)
    max_age = _native_int(max_age_ms)
    if not clean_symbol:
        return _safe_contract(
            symbol=str(symbol or "").strip().upper(),
            status="NOT_APPLICABLE",
            captured_at_ms=captured or 0,
            max_age_ms=max_age or DEFAULT_MAX_AGE_MS,
            blockers=["spot_symbol_not_applicable"],
        )
    if captured is None or captured <= 0 or max_age is None or max_age <= 0:
        return _safe_contract(
            symbol=clean_symbol,
            status="BLOCK",
            captured_at_ms=captured or 0,
            max_age_ms=max_age or DEFAULT_MAX_AGE_MS,
            blockers=["capture_time_contract_invalid"],
        )
    if not isinstance(payload, dict) or str(payload.get("code") or "") != "0":
        return _safe_contract(
            symbol=clean_symbol,
            status="BLOCK",
            captured_at_ms=captured,
            max_age_ms=max_age,
            blockers=["okx_public_response_invalid"],
        )
    data = payload.get("data")
    if not isinstance(data, list):
        return _safe_contract(
            symbol=clean_symbol,
            status="BLOCK",
            captured_at_ms=captured,
            max_age_ms=max_age,
            blockers=["okx_public_data_contract_invalid"],
        )
    matches = [
        item for item in data
        if isinstance(item, dict) and str(item.get("instId") or "").strip().upper() == clean_symbol
    ]
    if not matches:
        return _safe_contract(
            symbol=clean_symbol,
            status="NOT_FOUND",
            captured_at_ms=captured,
            max_age_ms=max_age,
            blockers=["instrument_not_found"],
        )
    if len(matches) != 1:
        return _safe_contract(
            symbol=clean_symbol,
            status="BLOCK",
            captured_at_ms=captured,
            max_age_ms=max_age,
            blockers=["instrument_identity_ambiguous"],
        )
    row = matches[0]
    blockers: list[str] = []
    inst_type = str(row.get("instType") or "").strip().upper()
    state = str(row.get("state") or "").strip().lower()
    base_ccy = str(row.get("baseCcy") or "").strip().upper()
    quote_ccy = str(row.get("quoteCcy") or "").strip().upper()
    symbol_parts = clean_symbol.split("-", 1)
    if inst_type != "SPOT":
        blockers.append("instrument_type_mismatch")
    if base_ccy != symbol_parts[0] or quote_ccy != symbol_parts[1]:
        blockers.append("instrument_currency_identity_mismatch")
    if state != "live":
        blockers.append("instrument_not_live")
    tick_size = _positive_decimal(row.get("tickSz"))
    lot_size = _positive_decimal(row.get("lotSz"))
    minimum_order_size = _positive_decimal(row.get("minSz"))
    if not tick_size:
        blockers.append("tick_size_invalid")
    if not lot_size:
        blockers.append("lot_size_invalid")
    if not minimum_order_size:
        blockers.append("minimum_order_size_invalid")
    if any(str(row.get(key) or "").strip() for key in ("ctVal", "ctMult", "ctValCcy")):
        blockers.append("spot_derivative_fields_present")
    upcoming_changes, upcoming_blockers = _normalized_upcoming_changes(row.get("upcChg"))
    blockers.extend(upcoming_blockers)

    status = "BLOCK" if blockers else "REVIEW" if upcoming_changes else "VERIFIED"
    snapshot = _safe_contract(
        symbol=clean_symbol,
        status=status,
        captured_at_ms=captured,
        max_age_ms=max_age,
        blockers=blockers or (["upcoming_rule_change_requires_refresh"] if upcoming_changes else []),
    )
    snapshot.update({
        "instrument_state": state,
        "tick_size": tick_size,
        "lot_size": lot_size,
        "minimum_order_size": minimum_order_size,
        "size_unit": base_ccy,
        "price_unit": quote_ccy,
        "ccxt_symbol": f"{base_ccy}/{quote_ccy}" if base_ccy and quote_ccy else "",
        "fee_group_id": str(row.get("groupId") or "").strip(),
        "list_time_ms": _timestamp_text(row.get("listTime")),
        "continuous_from_ms": _timestamp_text(row.get("contTdSwTime")) or _timestamp_text(row.get("listTime")),
        "offline_at_ms": _timestamp_text(row.get("expTime")) or None,
        "max_limit_size": _optional_nonnegative_decimal(row.get("maxLmtSz")),
        "max_market_size": _optional_nonnegative_decimal(row.get("maxMktSz")),
        "upcoming_changes": upcoming_changes,
        "current": status == "VERIFIED",
        "verification": {
            "venue_rules_verified": status == "VERIFIED",
            "account_tradeability_verified": False,
            "account_fee_verified": False,
            "minimum_cost_verified": False,
        },
    })
    snapshot["rules_hash"] = _canonical_hash(_rule_content(snapshot))
    snapshot["snapshot_hash"] = _snapshot_seal(snapshot)
    snapshot["hash_verified"] = True
    return snapshot


def verify_public_instrument_rules(
    snapshot: Any,
    *,
    expected_symbol: Any,
    now_ms: Any,
) -> dict[str, Any]:
    clean_symbol = _canonical_symbol(expected_symbol)
    blockers: list[str] = []
    if not isinstance(snapshot, dict):
        return {"status": "NOT_CHECKED", "blockers": ["instrument_rules_missing"], "rules": {}}
    rules = copy.deepcopy(snapshot)
    expected_text = str(expected_symbol or "").strip().upper()
    if not clean_symbol:
        safe_not_applicable = (
            rules.get("schema_version") == SCHEMA_VERSION
            and rules.get("mode") == MODE
            and rules.get("status") == "NOT_APPLICABLE"
            and rules.get("symbol") == expected_text
            and rules.get("public_only") is True
            and rules.get("credentials_used") is False
            and rules.get("read_only") is True
            and rules.get("paper_authorized") is False
            and rules.get("live_order_allowed") is False
        )
        return {
            "status": "NOT_CHECKED" if safe_not_applicable else "BLOCK",
            "blockers": ["instrument_rules_not_applicable"] if safe_not_applicable else ["instrument_rules_not_applicable_contract_invalid"],
            "rules": rules,
        }
    source = rules.get("source") if isinstance(rules.get("source"), dict) else {}
    if rules.get("status") in {"NOT_CHECKED", "NOT_FOUND", "UNAVAILABLE"}:
        safe_unverified = (
            rules.get("schema_version") == SCHEMA_VERSION
            and rules.get("mode") == MODE
            and rules.get("symbol") == clean_symbol
            and rules.get("public_only") is True
            and rules.get("credentials_used") is False
            and rules.get("read_only") is True
            and rules.get("paper_authorized") is False
            and rules.get("live_order_allowed") is False
            and rules.get("verification") == {
                "venue_rules_verified": False,
                "account_tradeability_verified": False,
                "account_fee_verified": False,
                "minimum_cost_verified": False,
            }
        )
        return {
            "status": "NOT_CHECKED" if safe_unverified else "BLOCK",
            "blockers": list(rules.get("blockers") or ["instrument_rules_not_checked"]),
            "rules": rules,
        }
    captured = _native_int(source.get("captured_at_ms"))
    max_age = _native_int(source.get("max_age_ms"))
    current_time = _native_int(now_ms)
    if rules.get("schema_version") != SCHEMA_VERSION or rules.get("mode") != MODE:
        blockers.append("instrument_rules_schema_invalid")
    if not clean_symbol or rules.get("symbol") != clean_symbol:
        blockers.append("instrument_rules_symbol_mismatch")
    if rules.get("venue") != "OKX" or rules.get("instrument_type") != "SPOT":
        blockers.append("instrument_rules_scope_invalid")
    if rules.get("instrument_state") != "live":
        blockers.append("instrument_rules_state_invalid")
    if source.get("provider") != PROVIDER or source.get("endpoint") != ENDPOINT:
        blockers.append("instrument_rules_source_invalid")
    if captured is None or captured <= 0 or max_age is None or max_age <= 0 or current_time is None:
        blockers.append("instrument_rules_time_invalid")
        age_ms = None
    else:
        age_ms = current_time - captured
        if age_ms < -5_000:
            blockers.append("instrument_rules_from_future")
        elif age_ms > max_age:
            blockers.append("instrument_rules_stale")
    if any(rules.get(field) is not expected for field, expected in (
        ("public_only", True),
        ("credentials_used", False),
        ("read_only", True),
        ("paper_authorized", False),
        ("live_order_allowed", False),
    )):
        blockers.append("instrument_rules_authority_invalid")
    verification = rules.get("verification") if isinstance(rules.get("verification"), dict) else {}
    if verification != {
        "venue_rules_verified": True,
        "account_tradeability_verified": False,
        "account_fee_verified": False,
        "minimum_cost_verified": False,
    }:
        blockers.append("instrument_rules_verification_invalid")
    if not all(_positive_decimal(rules.get(field)) for field in (
        "tick_size", "lot_size", "minimum_order_size"
    )):
        blockers.append("instrument_rules_decimal_invalid")
    if rules.get("minimum_cost") is not None:
        blockers.append("minimum_cost_must_remain_unknown")
    if rules.get("upcoming_changes") != []:
        blockers.append("instrument_rules_upcoming_change")
    expected_rules_hash = _canonical_hash(_rule_content(rules))
    if not _HASH_RE.fullmatch(str(rules.get("rules_hash") or "")) or rules.get("rules_hash") != expected_rules_hash:
        blockers.append("instrument_rules_hash_invalid")
    expected_snapshot_hash = _snapshot_seal(rules)
    if not _HASH_RE.fullmatch(str(rules.get("snapshot_hash") or "")) or rules.get("snapshot_hash") != expected_snapshot_hash:
        blockers.append("instrument_snapshot_hash_invalid")
    if rules.get("hash_verified") is not True:
        blockers.append("instrument_rules_hash_flag_invalid")
    if rules.get("status") != "VERIFIED" or rules.get("current") is not True:
        blockers.append("instrument_rules_not_verified")

    if not blockers:
        status = "PASS"
    elif set(blockers).issubset({"instrument_rules_stale", "instrument_rules_not_verified"}):
        status = "NOT_CHECKED"
    elif rules.get("status") in {"NOT_FOUND", "NOT_APPLICABLE", "UNAVAILABLE", "STALE", "REVIEW"} and not any(
        blocker.endswith(("invalid", "mismatch")) for blocker in blockers
    ):
        status = "NOT_CHECKED"
    else:
        status = "BLOCK"
    rules["age_ms"] = age_ms
    return {"status": status, "blockers": list(dict.fromkeys(blockers)), "rules": rules}


class PublicInstrumentRuleService:
    def __init__(
        self,
        *,
        fetch_payload: Callable[[str, dict[str, str]], dict[str, Any]],
        now_ms: Callable[[], int],
        max_age_ms: int = DEFAULT_MAX_AGE_MS,
        max_cache_entries: int = 128,
    ) -> None:
        self.fetch_payload = fetch_payload
        self.now_ms = now_ms
        self.max_age_ms = max(int(max_age_ms), 1)
        self.max_cache_entries = max(int(max_cache_entries), 1)
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._inflight: dict[str, dict[str, Any]] = {}

    def _view(self, snapshot: dict[str, Any], now: int, *, cached: bool) -> dict[str, Any]:
        view = copy.deepcopy(snapshot)
        source = view.get("source") if isinstance(view.get("source"), dict) else {}
        captured = _native_int(source.get("captured_at_ms")) or 0
        age = max(now - captured, 0) if captured else None
        view["cache_age_ms"] = age
        view["cached"] = cached
        view["current"] = view.get("status") == "VERIFIED" and age is not None and age <= self.max_age_ms
        if view.get("status") == "VERIFIED" and not view["current"]:
            view["status"] = "STALE"
        return view

    def _remember(self, symbol: str, snapshot: dict[str, Any]) -> None:
        with self._lock:
            self._cache[symbol] = copy.deepcopy(snapshot)
            if len(self._cache) <= self.max_cache_entries:
                return
            ordered = sorted(
                self._cache.items(),
                key=lambda item: int(((item[1].get("source") or {}).get("captured_at_ms") or 0)),
            )
            for key, _value in ordered[: len(self._cache) - self.max_cache_entries]:
                self._cache.pop(key, None)

    def snapshot(self, symbol: Any, *, force: bool = False) -> dict[str, Any]:
        clean_symbol = _canonical_symbol(symbol)
        now = _native_int(self.now_ms()) or 0
        if not clean_symbol:
            return _safe_contract(
                symbol=str(symbol or "").strip().upper(),
                status="NOT_APPLICABLE",
                captured_at_ms=now,
                max_age_ms=self.max_age_ms,
                blockers=["spot_symbol_not_applicable"],
            )
        with self._lock:
            cached_snapshot = copy.deepcopy(self._cache.get(clean_symbol))
        if cached_snapshot and not force:
            cached_view = self._view(cached_snapshot, now, cached=True)
            if cached_view.get("current") is True:
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
            if cached_snapshot and not force:
                cached_view = self._view(cached_snapshot, now, cached=True)
                if cached_view.get("current") is True:
                    result = cached_view
            if result is None:
                try:
                    payload = self.fetch_payload(ENDPOINT, {"instType": "SPOT", "instId": clean_symbol})
                except Exception as exc:
                    if cached_snapshot:
                        stale = self._view(cached_snapshot, now, cached=True)
                        stale["status"] = "STALE"
                        stale["current"] = False
                        stale["refresh_error"] = str(exc)[:240]
                        stale["blockers"] = list(dict.fromkeys([
                            *list(stale.get("blockers") or []),
                            "public_rules_refresh_failed",
                        ]))
                        result = stale
                    else:
                        unavailable = _safe_contract(
                            symbol=clean_symbol,
                            status="UNAVAILABLE",
                            captured_at_ms=now,
                            max_age_ms=self.max_age_ms,
                            blockers=["public_rules_refresh_failed"],
                        )
                        unavailable["refresh_error"] = str(exc)[:240]
                        result = unavailable
                else:
                    snapshot = build_okx_public_spot_rules(
                        payload,
                        symbol=clean_symbol,
                        captured_at_ms=now,
                        max_age_ms=self.max_age_ms,
                    )
                    if snapshot.get("status") == "VERIFIED":
                        self._remember(clean_symbol, snapshot)
                    result = self._view(snapshot, now, cached=False)
        except Exception as exc:
            result = _safe_contract(
                symbol=clean_symbol,
                status="BLOCK",
                captured_at_ms=now,
                max_age_ms=self.max_age_ms,
                blockers=["public_rules_internal_failure"],
            )
            result["refresh_error"] = str(exc)[:240]
        finally:
            if result is None:
                result = _safe_contract(
                    symbol=clean_symbol,
                    status="BLOCK",
                    captured_at_ms=now,
                    max_age_ms=self.max_age_ms,
                    blockers=["public_rules_internal_failure"],
                )
            with self._lock:
                entry["result"] = copy.deepcopy(result)
                if self._inflight.get(clean_symbol) is entry:
                    self._inflight.pop(clean_symbol, None)
                entry["event"].set()
        return copy.deepcopy(result)


__all__ = [
    "DEFAULT_MAX_AGE_MS",
    "PublicInstrumentRuleService",
    "build_okx_public_spot_rules",
    "public_instrument_rules_placeholder",
    "verify_public_instrument_rules",
]
