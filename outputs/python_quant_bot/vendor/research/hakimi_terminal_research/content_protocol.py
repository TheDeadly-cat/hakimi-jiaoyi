"""Offline C/D specification predicates; not a backtest, order API, or approval UI.

The existing engine/ledger remains the required executor for any later economic
study. These functions verify timing, reviewed facts, and C == disabled D only.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def utc(value):
    stamp = datetime.fromisoformat(value.replace("Z","+00:00"))
    if stamp.tzinfo is None or stamp.utcoffset() != timedelta(0):
        raise ValueError("content_protocol_UTC_required")
    return stamp


def number(value):
    if type(value) is not str:
        raise ValueError("content_protocol_decimal_string_required")
    result = Decimal(value)
    if not result.is_finite() or result <= 0:
        raise ValueError("content_protocol_positive_finite_value_required")
    return result


def validate_approval(packet, receipt):
    core = {k:v for k,v in packet.items() if k != "packet_hash"}
    if packet.get("packet_hash") != digest(core):
        raise ValueError("content_packet_hash_mismatch")
    if receipt is None:
        return set()
    if (receipt.get("schema_version") != "human-field-review-v1" or receipt.get("packet_hash") != packet["packet_hash"]
            or receipt.get("decision") != "APPROVED_LISTED_FIELDS" or receipt.get("reviewer_kind") != "HUMAN_ATTESTATION"
            or not receipt.get("reviewer") or not receipt.get("source_user_confirmation")):
        raise ValueError("content_human_approval_identity_required")
    utc(receipt["reviewed_at"])
    allowed = {row["candidate_hash"] for row in packet["events"] if "facts" in row}
    hashes = receipt.get("approved_candidate_hashes")
    if type(hashes) is not list or len(hashes) != len(set(hashes)) or not set(hashes) <= allowed:
        raise ValueError("content_approval_unknown_or_duplicate_candidate")
    if receipt.get("approved_fields") != ["actual_revenue","diluted_eps","non_gaap_diluted_eps",
            "next_revenue_guidance_midpoint","next_revenue_guidance_half_range","first_public_at"]:
        raise ValueError("content_approval_field_scope_mismatch")
    return set(hashes)


def price_confirmation(*, release_at, decision_at, sessions, bars, availability_lag_seconds=120):
    if type(availability_lag_seconds) is not int or availability_lag_seconds != 120:
        raise ValueError("content_protocol_frozen_120_second_assumption_required")
    release, decision = utc(release_at), utc(decision_at)
    available = release + timedelta(seconds=availability_lag_seconds)
    hold = {"action":"HOLD","execution_at":None,"reason":"NO_AVAILABLE_PRICE_CONFIRMATION","order_allowed":False}
    if decision < available: return hold
    ordered_sessions = sorted(sessions,key=lambda row:utc(row["open_utc"]))
    if len({row["date"] for row in ordered_sessions}) != len(ordered_sessions):
        raise ValueError("content_protocol_duplicate_session")
    by_date = {row["date"]:row for row in ordered_sessions}
    if len({row["session"] for row in bars}) != len(bars):
        raise ValueError("content_protocol_duplicate_bar")
    known = []
    for row in bars:
        session = by_date[row["session"]]
        opening, closing, bar_available = utc(session["open_utc"]), utc(session["close_utc"]), utc(row["available_at"])
        if closing <= opening or bar_available < closing or type(row["completed"]) is not bool:
            raise ValueError("content_protocol_invalid_completed_bar_clock")
        close = number(row["close"])
        if row["completed"] and bar_available <= decision:
            known.append((session,close,bar_available))
    before = [row for row in known if utc(row[0]["close_utc"]) <= release]
    target_sessions = [row for row in ordered_sessions if utc(row["open_utc"]) >= available]
    if not before or not target_sessions: return hold
    # The FIRST full post-publication session is fixed, never the first profitable bar.
    target = target_sessions[0]
    matches = [row for row in known if row[0]["date"] == target["date"]]
    if not matches: return hold
    confirmed = matches[0]
    previous = max(before,key=lambda row:utc(row[0]["close_utc"]))
    following = [row for row in ordered_sessions if utc(row["open_utc"]) > confirmed[2]]
    if not following or decision != confirmed[2] or confirmed[1] <= previous[1]: return hold
    return {"action":"BUY","execution_at":following[0]["open_utc"],"reason":"FIRST_POST_RELEASE_CLOSE_ABOVE_PRE_RELEASE_CLOSE","order_allowed":False}


def content_condition(c_result, *, versions, decision_at, approved_hashes, enabled=True):
    if type(enabled) is not bool:
        raise ValueError("content_protocol_enabled_boolean_required")
    if not enabled or c_result["action"] != "BUY":
        return dict(c_result)
    decision = utc(decision_at)
    known = [row for row in versions if utc(row["first_public_at"]) + timedelta(seconds=120) <= decision
             and utc(row.get("version_public_at",row["first_public_at"])) + timedelta(seconds=120) <= decision]
    hold = {"action":"HOLD","execution_at":None,"reason":"CONTENT_UNKNOWN_OR_NOT_APPROVED","order_allowed":False}
    if not known: return hold
    ids = {row["event_id"] for row in known}
    if len(ids) != 1:
        raise ValueError("content_protocol_mixed_event_versions")
    ordered = sorted(known,key=lambda row:(utc(row.get("version_public_at",row["first_public_at"])),row["version"]))
    latest = ordered[-1]
    if len({row["version"] for row in ordered}) != len(ordered):
        raise ValueError("content_protocol_conflicting_versions")
    if latest["candidate_hash"] != digest({k:v for k,v in latest.items() if k != "candidate_hash"}):
        raise ValueError("content_candidate_identity_changed")
    if latest["candidate_hash"] not in approved_hashes: return hold
    facts = {row["name"]:row for row in latest["facts"]}
    actual, guidance = facts.get("actual_revenue"), facts.get("next_revenue_guidance_midpoint")
    if not actual or not guidance: return hold
    for fact in (actual,guidance):
        if fact["status"] not in {"UNCERTAIN","KNOWN"} or fact.get("reason") not in {None,"PENDING_HUMAN_SEMANTIC_REVIEW"}:
            return hold
        if fact["currency"] != "USD" or fact["unit"] != "CURRENCY": return hold
    quarter = latest["fiscal_quarter"]
    next_quarter = f'{int(quarter[:4])+(quarter[-1]=="4")}Q{int(quarter[-1])%4+1}'
    if (actual["fiscal_period"] != quarter or actual["basis"] != "GAAP"
            or guidance["fiscal_period"] != next_quarter or guidance["basis"] != "REVENUE_OUTLOOK"):
        return hold
    revenue = number(actual["value"])*number(actual["scale"])
    midpoint = number(guidance["value"])*number(guidance["scale"])
    if midpoint <= revenue:
        return {"action":"HOLD","execution_at":None,"reason":"REVIEWED_NEXT_QUARTER_GUIDANCE_NOT_ABOVE_HEADLINE_REVENUE","order_allowed":False}
    return dict(c_result)
