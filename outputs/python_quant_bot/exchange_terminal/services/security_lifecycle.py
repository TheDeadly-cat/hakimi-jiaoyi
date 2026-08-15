from __future__ import annotations

import hashlib
import json
import math
from datetime import date
from typing import Any

from .market_calendar import session_timestamp_ms


SECURITY_LIFECYCLE_SCHEMA_VERSION = "security-lifecycle-contract-v2"
NON_TRADABLE_STATUSES = {"SUSPENDED", "HALTED", "DELISTED"}


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _positive(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return parsed if math.isfinite(parsed) and parsed > 0 else 0.0


def _zero(value: Any) -> bool:
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return False
    return math.isfinite(parsed) and parsed == 0.0


def _valid_sha256(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def _date(value: Any) -> str:
    text = str(value or "").strip()[:10]
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return ""


def normalize_security_lifecycle_events(
    symbol: str,
    events: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    clean_symbol = str(symbol or "").strip().upper()
    normalized: list[dict[str, Any]] = []
    for raw in events or []:
        if not isinstance(raw, dict):
            continue
        status = str(raw.get("status") or raw.get("event_type") or raw.get("type") or "").strip().upper()
        if status not in NON_TRADABLE_STATUSES:
            continue
        start_date = _date(raw.get("start_date") or raw.get("event_date") or raw.get("date"))
        if not clean_symbol or not start_date:
            continue
        end_date = _date(raw.get("end_date"))
        if status == "DELISTED":
            end_date = ""
        event = {
            "symbol": clean_symbol,
            "status": status,
            "start_date": start_date,
            "end_date": end_date,
            "cash_settlement_price": round(_positive(raw.get("cash_settlement_price") or raw.get("settlement_price")), 8),
            "provider": str(raw.get("provider") or "").strip().lower(),
            "provider_event_id": str(raw.get("provider_event_id") or raw.get("id") or ""),
            "reason": str(raw.get("reason") or ""),
        }
        event["event_hash"] = _canonical_hash(event)
        normalized.append(event)
    return sorted(
        {item["event_hash"]: item for item in normalized}.values(),
        key=lambda item: (item["start_date"], item["status"], item["event_hash"]),
    )


def _event_on(events: list[dict[str, Any]], session_date: str) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for event in events:
        start = str(event.get("start_date") or "")
        end = str(event.get("end_date") or "")
        if session_date < start:
            continue
        if event.get("status") == "DELISTED" or not end or session_date <= end:
            matches.append(event)
    if not matches:
        return {}
    priority = {"DELISTED": 3, "SUSPENDED": 2, "HALTED": 1}
    return max(matches, key=lambda item: (priority.get(str(item.get("status")), 0), str(item.get("start_date"))))


def align_security_to_market_calendar(
    *,
    symbol: str,
    rows_by_date: dict[str, dict[str, Any]],
    expected_dates: list[str],
    lifecycle_events: list[dict[str, Any]] | None = None,
    universe_membership_start: str = "",
    universe_contract_hash: str = "",
) -> dict[str, Any]:
    clean_symbol = str(symbol or "").strip().upper()
    events = normalize_security_lifecycle_events(clean_symbol, lifecycle_events)
    expected = [str(item) for item in expected_dates]
    expected_set = set(expected)
    unexpected_dates = sorted(set(rows_by_date).difference(expected_set))
    blockers: list[str] = []
    warnings: list[str] = []
    membership_start = _date(universe_membership_start)
    membership_contract_hash = str(universe_contract_hash or "").strip().lower()
    if universe_membership_start and not membership_start:
        blockers.append("universe_membership_start_invalid")
    if membership_start and not _valid_sha256(membership_contract_hash):
        blockers.append("universe_membership_contract_hash_invalid")
    if unexpected_dates:
        blockers.append(f"non_session_dates_present:{len(unexpected_dates)}")

    aligned: list[dict[str, Any]] = []
    missing_dates: list[str] = []
    filled_nontradable_dates: list[str] = []
    filled_outside_universe_dates: list[str] = []
    previous: dict[str, Any] = {}
    delisting_settled = False
    for session_date in expected:
        row = dict(rows_by_date.get(session_date) or {})
        event = _event_on(events, session_date)
        status = str(event.get("status") or "TRADABLE")
        if row:
            outside_universe_marker = (
                str(row.get("trading_status") or "").upper() == "OUTSIDE_UNIVERSE"
                or str(row.get("valuation_basis") or "") == "NO_POSITION_OUTSIDE_UNIVERSE_SENTINEL"
            )
            if membership_start and session_date < membership_start and outside_universe_marker:
                replayed_outside_universe = (
                    row.get("tradable") is False
                    and row.get("valuation_only") is True
                    and str(row.get("trading_status") or "").upper() == "OUTSIDE_UNIVERSE"
                    and str(row.get("valuation_basis") or "") == "NO_POSITION_OUTSIDE_UNIVERSE_SENTINEL"
                    and str(row.get("lifecycle_event_hash") or "").lower() == membership_contract_hash
                    and all(_positive(row.get(key)) == 1.0 for key in ("open", "high", "low", "close"))
                    and _zero(row.get("volume"))
                    and row.get("mandatory_cash_settlement") is False
                )
                if not replayed_outside_universe:
                    blockers.append(f"outside_universe_sentinel_invalid:{session_date}")
                row.update({
                    "tradable": False,
                    "trading_status": "OUTSIDE_UNIVERSE",
                    "calendar_session": True,
                    "valuation_only": True,
                    "valuation_basis": "NO_POSITION_OUTSIDE_UNIVERSE_SENTINEL",
                    "mandatory_cash_settlement": False,
                    "lifecycle_event_hash": membership_contract_hash,
                })
                missing_dates.append(session_date)
                filled_nontradable_dates.append(session_date)
                filled_outside_universe_dates.append(session_date)
                aligned.append(row)
                continue
            if status in NON_TRADABLE_STATUSES:
                is_replayed_valuation = (
                    bool(row.get("valuation_only"))
                    and not bool(row.get("tradable", True))
                    and str(row.get("trading_status") or "").upper() == status
                    and str(row.get("lifecycle_event_hash") or "") == str(event.get("event_hash") or "")
                )
                if not is_replayed_valuation:
                    blockers.append(f"status_event_conflicts_with_price_row:{session_date}:{status}")
                else:
                    missing_dates.append(session_date)
                    filled_nontradable_dates.append(session_date)
            row.update({
                "tradable": status == "TRADABLE",
                "trading_status": status,
                "calendar_session": True,
                "valuation_only": bool(row.get("valuation_only")) if status in NON_TRADABLE_STATUSES else False,
                "valuation_basis": str(row.get("valuation_basis") or "") if status in NON_TRADABLE_STATUSES else "",
                "mandatory_cash_settlement": (
                    bool(row.get("mandatory_cash_settlement")) if status == "DELISTED" else False
                ),
                "lifecycle_event_hash": str(event.get("event_hash") or "") if event else "",
            })
            previous = row
            aligned.append(row)
            continue

        missing_dates.append(session_date)
        if membership_start and session_date < membership_start:
            synthetic = {
                "date": session_date,
                "ts_ms": session_timestamp_ms(session_date),
                "open": 1.0,
                "high": 1.0,
                "low": 1.0,
                "close": 1.0,
                "volume": 0.0,
                "complete": True,
                "tradable": False,
                "trading_status": "OUTSIDE_UNIVERSE",
                "calendar_session": True,
                "valuation_only": True,
                "valuation_basis": "NO_POSITION_OUTSIDE_UNIVERSE_SENTINEL",
                "mandatory_cash_settlement": False,
                "lifecycle_event_hash": membership_contract_hash,
            }
            aligned.append(synthetic)
            filled_nontradable_dates.append(session_date)
            filled_outside_universe_dates.append(session_date)
            continue
        if not event:
            continue
        if status in {"SUSPENDED", "HALTED"}:
            if not previous:
                blockers.append(f"nontradable_gap_without_prior_price:{session_date}:{status}")
                continue
            price = _positive(previous.get("close"))
            synthetic = {
                "date": session_date,
                "ts_ms": session_timestamp_ms(session_date),
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": 0.0,
                "complete": True,
                "tradable": False,
                "trading_status": status,
                "calendar_session": True,
                "valuation_only": True,
                "valuation_basis": "CARRY_FORWARD_LAST_CLOSE",
                "mandatory_cash_settlement": False,
                "lifecycle_event_hash": event.get("event_hash", ""),
            }
            aligned.append(synthetic)
            previous = synthetic
            filled_nontradable_dates.append(session_date)
            continue
        if status == "DELISTED":
            settlement_price = _positive(event.get("cash_settlement_price"))
            if settlement_price <= 0:
                blockers.append(f"delisting_settlement_price_missing:{session_date}")
                continue
            synthetic = {
                "date": session_date,
                "ts_ms": session_timestamp_ms(session_date),
                "open": settlement_price,
                "high": settlement_price,
                "low": settlement_price,
                "close": settlement_price,
                "volume": 0.0,
                "complete": True,
                "tradable": False,
                "trading_status": status,
                "calendar_session": True,
                "valuation_only": True,
                "valuation_basis": "DELISTING_CASH_SETTLEMENT",
                "mandatory_cash_settlement": not delisting_settled,
                "lifecycle_event_hash": event.get("event_hash", ""),
            }
            aligned.append(synthetic)
            previous = synthetic
            delisting_settled = True
            filled_nontradable_dates.append(session_date)

    unresolved = sorted(set(missing_dates).difference(filled_nontradable_dates))
    if unresolved:
        blockers.append(f"unverified_missing_sessions:{len(unresolved)}")
    if filled_nontradable_dates:
        warnings.append(f"declared_nontradable_sessions_carried:{len(filled_nontradable_dates)}")
    if filled_outside_universe_dates:
        warnings.append(f"outside_universe_sessions_filled:{len(filled_outside_universe_dates)}")
    if len(aligned) != len(expected):
        blockers.append(f"aligned_session_count:{len(aligned)}!={len(expected)}")
    payload = {
        "schema_version": SECURITY_LIFECYCLE_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "warnings": warnings,
        "symbol": clean_symbol,
        "events": events,
        "event_hash": _canonical_hash(events),
        "universe_membership_start": membership_start,
        "universe_contract_hash": membership_contract_hash,
        "expected_session_count": len(expected),
        "aligned_session_count": len(aligned),
        "missing_dates": missing_dates,
        "unresolved_missing_dates": unresolved,
        "unexpected_dates": unexpected_dates,
        "filled_nontradable_dates": filled_nontradable_dates,
        "filled_outside_universe_dates": filled_outside_universe_dates,
        "outside_universe_session_count": len(filled_outside_universe_dates),
        "tradable_session_count": sum(1 for item in aligned if item.get("tradable")),
        "nontradable_session_count": sum(1 for item in aligned if not item.get("tradable")),
        "rows": aligned,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["contract_hash"] = _canonical_hash({key: value for key, value in payload.items() if key != "rows"})
    return payload
