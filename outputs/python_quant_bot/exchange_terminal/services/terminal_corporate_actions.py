"""Independent v1 split accounting; never an admission path to an old runner.

All functions are pure. Source traceability is not source authentication. Only
ordinary declared splits are supported; cash dividends are diagnostic-only.
Exact rational strings preserve fractional research shares and unit prices.
"""
from copy import deepcopy
from datetime import date, datetime, timezone
from fractions import Fraction
from hashlib import sha256
import json
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


ACTION_SCHEMA = "hakimi-corporate-action-v1"
STATE_SCHEMA = "hakimi-action-accounting-state-v1"
RECEIPT_SCHEMA = "hakimi-action-accounting-receipt-v1"
ENGINE_ID = "terminal.split-accounting-v1"
NUMERIC_POLICY = "EXACT_RATIONAL_STRINGS_V1"
QUANTITY_POLICY = "FRACTIONAL_RESEARCH_NO_CASH_IN_LIEU"
MAX_ACTIONS = 256
_PERMISSIONS = {"research_only": True, "old_runner_admission_allowed": False,
                "paper_allowed": False, "live_allowed": False, "order_allowed": False}
_SOURCE_FIELDS = {"provider", "reference", "retrieved_at", "security_id", "currency",
                  "raw_event_id", "raw_json", "raw_sha256"}
_BASE_FIELDS = {"schema_version", "action_id", "action_type", "security_id", "currency",
                "effective_session", "evidence_kind", "source"}


class CorporateActionError(ValueError):
    pass


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _hash(value):
    return sha256(_json(value).encode("utf-8")).hexdigest()


def _text(value, maximum=200):
    if type(value) is not str or not value.strip() or len(value) > maximum or "\0" in value:
        raise CorporateActionError("action_text_invalid")
    return value


def _day(value):
    if type(value) is not str or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        raise CorporateActionError("action_session_date_required")
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError()
    except ValueError as exc:
        raise CorporateActionError("action_session_date_invalid") from exc
    return value


def _calendar(value):
    if type(value) is not dict or set(value) != {"timezone", "sessions"}:
        raise CorporateActionError("explicit_action_calendar_required")
    try:
        zone = ZoneInfo(_text(value["timezone"], 80))
    except ZoneInfoNotFoundError as exc:
        raise CorporateActionError("action_calendar_timezone_unavailable") from exc
    sessions = value["sessions"]
    if type(sessions) is not list or not 2 <= len(sessions) <= 10000:
        raise CorporateActionError("action_calendar_sessions_invalid")
    days = [_day(item) for item in sessions]
    if days != sorted(set(days)):
        raise CorporateActionError("action_calendar_sessions_not_strictly_ordered")
    return days, zone


def _rational(value, *, positive=False):
    if type(value) is not str or len(value) > 2048 or re.fullmatch(r"(?:0|[1-9]\d*)(?:\.\d+|/[1-9]\d*)?", value) is None:
        raise CorporateActionError("nonnegative_exact_rational_string_required")
    try:
        number = Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise CorporateActionError("action_rational_invalid") from exc
    if positive and number <= 0:
        raise CorporateActionError("positive_action_value_required")
    return number


def _format(value):
    result = str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"
    if len(result) > 2048:
        raise CorporateActionError("action_exact_numeric_capacity_exceeded")
    return result


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise CorporateActionError("action_source_duplicate_json_key")
        result[key] = value
    return result


def _source(action, zone):
    source = action.get("source")
    if type(source) is not dict or set(source) != _SOURCE_FIELDS:
        raise CorporateActionError("complete_action_source_fields_required")
    for field in _SOURCE_FIELDS - {"raw_json"}:
        _text(source[field], 2000 if field == "reference" else 200)
    if source["security_id"] != action.get("security_id") or source["currency"] != action.get("currency"):
        raise CorporateActionError("action_source_security_or_currency_conflict")
    if type(source["raw_json"]) is not str or len(source["raw_json"].encode("utf-8")) > 16384:
        raise CorporateActionError("action_source_raw_json_size_invalid")
    if (re.fullmatch(r"[0-9a-f]{64}", source["raw_sha256"]) is None
            or sha256(source["raw_json"].encode("utf-8")).hexdigest() != source["raw_sha256"]):
        raise CorporateActionError("action_source_bytes_hash_mismatch")
    try:
        retrieved = datetime.fromisoformat(source["retrieved_at"].replace("Z", "+00:00"))
        if retrieved.tzinfo is None:
            raise ValueError()
        event = json.loads(source["raw_json"], object_pairs_hook=_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")))
    except (ValueError, TypeError) as exc:
        raise CorporateActionError("action_source_time_or_json_invalid") from exc
    if type(event) is not dict or type(event.get("date")) is not int or not 0 < event["date"] <= 253402300799:
        raise CorporateActionError("source_effective_timestamp_required")
    try:
        effective = datetime.fromtimestamp(event["date"], timezone.utc).astimezone(zone).date().isoformat()
    except (ValueError, OverflowError, OSError) as exc:
        raise CorporateActionError("source_effective_timestamp_invalid") from exc
    if effective != action.get("effective_session"):
        raise CorporateActionError("source_effective_session_conflict")
    return event


def inspect_action(action, calendar):
    """Return SUPPORTED or UNSUPPORTED without inventing absent source facts."""
    reasons, event = [], None
    try:
        sessions, zone = _calendar(calendar)
        if type(action) is not dict or _BASE_FIELDS - set(action):
            raise CorporateActionError("corporate_action_fields_missing")
        if action["schema_version"] != ACTION_SCHEMA:
            raise CorporateActionError("corporate_action_schema_unsupported")
        for key in ("action_id", "security_id", "action_type"):
            _text(action[key])
        if type(action["currency"]) is not str or re.fullmatch(r"[A-Z]{3}", action["currency"]) is None:
            raise CorporateActionError("explicit_action_currency_required")
        if action["evidence_kind"] not in {"SYNTHETIC_TEST", "IMPORTED_UNVERIFIED"}:
            raise CorporateActionError("action_evidence_kind_invalid")
        if _day(action["effective_session"]) not in sessions:
            raise CorporateActionError("action_effective_session_not_in_declared_calendar")
        event = _source(action, zone)
        if action["action_type"] == "SPLIT":
            if set(action) != _BASE_FIELDS | {"numerator", "denominator", "distribution_conditions"}:
                raise CorporateActionError("split_has_missing_or_unsupported_distribution_fields")
            if action["distribution_conditions"] != "NONE_DECLARED":
                raise CorporateActionError("special_distribution_or_cash_in_lieu_unsupported")
            if set(event) - {"date", "numerator", "denominator", "splitRatio"}:
                raise CorporateActionError("source_split_special_or_unknown_fields_unsupported")
            for key in ("numerator", "denominator"):
                if type(action[key]) is not int or not 0 < action[key] <= 1000000:
                    raise CorporateActionError("split_positive_integer_ratio_required")
                if type(event.get(key)) is not int or event[key] != action[key]:
                    raise CorporateActionError("source_split_ratio_missing_or_conflicting")
            if "splitRatio" in event:
                if type(event["splitRatio"]) is not str or re.fullmatch(r"[1-9]\d*:[1-9]\d*", event["splitRatio"]) is None:
                    raise CorporateActionError("source_split_ratio_text_invalid")
                left, right = map(int, event["splitRatio"].split(":"))
                if Fraction(left, right) != Fraction(action["numerator"], action["denominator"]):
                    raise CorporateActionError("source_split_ratio_text_conflict")
        elif action["action_type"] == "CASH_DIVIDEND":
            reasons.append("CASH_DIVIDEND_ACCOUNTING_UNSUPPORTED_IN_V1")
            for key in ("entitlement_rule", "ex_session", "payment_session", "payment_source", "amount_per_share"):
                if action.get(key) in (None, "", {}):
                    reasons.append("DIVIDEND_NOT_RECORDED:" + key)
            reasons.extend(("DIVIDEND_ENTITLEMENT_NOT_AUTOMATICALLY_INFERRED", "DIVIDEND_RECEIVABLE_AND_PAYMENT_NOT_IMPLEMENTED"))
        else:
            reasons.append("CORPORATE_ACTION_TYPE_UNSUPPORTED:" + action["action_type"])
    except (CorporateActionError, TypeError, ValueError) as exc:
        reasons.append(str(exc))
        if type(action) is dict and action.get("action_type") == "CASH_DIVIDEND":
            reasons.append("CASH_DIVIDEND_ACCOUNTING_UNSUPPORTED_IN_V1")
    if type(action) is dict and action.get("action_type") == "CASH_DIVIDEND":
        for key in ("entitlement_rule", "ex_session", "payment_session", "payment_source", "amount_per_share", "currency"):
            if action.get(key) in (None, "", {}):
                reasons.append("DIVIDEND_NOT_RECORDED:" + key)
        if action.get("amount_per_share") is not None:
            try:
                _rational(action["amount_per_share"], positive=True)
            except CorporateActionError:
                reasons.append("DIVIDEND_AMOUNT_NOT_SUPPORTED")
    try:
        action_hash = _hash(action) if type(action) is dict else None
    except (TypeError, ValueError):
        action_hash = None
        reasons.append("action_document_not_finite_json")
    supported = not reasons
    return {"schema_version": "hakimi-corporate-action-inspection-v1", "status": "SUPPORTED" if supported else "UNSUPPORTED",
            "action_id": action.get("action_id") if type(action) is dict else None,
            "action_hash": action_hash,
            "reasons": list(dict.fromkeys(reasons)), "accounting_policy": "ORDINARY_SPLIT_ONLY_V1" if supported else None,
            "source_authenticated": False, "real_source_acceptance": "PENDING",
            "permissions": dict(_PERMISSIONS)}


def _seal(state):
    body = {key: value for key, value in state.items() if key != "state_hash"}
    return {**body, "state_hash": _hash(body)}


def _history(rows, sessions):
    if type(rows) is not list or len(rows) > 10000:
        raise CorporateActionError("action_indicator_history_invalid")
    previous = None
    for row in rows:
        if type(row) is not dict or set(row) != {"session", "open", "high", "low", "close", "volume"}:
            raise CorporateActionError("action_indicator_row_fields_invalid")
        day = _day(row["session"])
        if day not in sessions or previous is not None and day <= previous:
            raise CorporateActionError("action_indicator_chronology_invalid")
        values = {key: _rational(row[key], positive=key != "volume") for key in ("open", "high", "low", "close", "volume")}
        if values["high"] < max(values["open"], values["close"], values["low"]) or values["low"] > min(values["open"], values["close"]):
            raise CorporateActionError("action_indicator_ohlc_invalid")
        previous = day
    return deepcopy(rows)


def new_action_state(*, owner_id, security_id, currency, calendar, as_of_session, cash, quantity,
                     unit_cost, indicator_history, entry_fees="0", stop_price=None, target_price=None):
    sessions, _ = _calendar(calendar)
    if _day(as_of_session) not in sessions:
        raise CorporateActionError("initial_action_session_not_in_calendar")
    _text(owner_id); _text(security_id)
    if type(currency) is not str or re.fullmatch(r"[A-Z]{3}", currency) is None:
        raise CorporateActionError("explicit_action_currency_required")
    position = {"owner_id": owner_id, "security_id": security_id,
                "quantity": _format(_rational(quantity)), "unit_cost": _format(_rational(unit_cost)),
                "entry_fees": _format(_rational(entry_fees)),
                "stop_price": None if stop_price is None else _format(_rational(stop_price, positive=True)),
                "target_price": None if target_price is None else _format(_rational(target_price, positive=True))}
    if _rational(quantity) > 0 and _rational(unit_cost) <= 0:
        raise CorporateActionError("held_position_positive_unit_cost_required")
    if _rational(quantity) == 0 and (_rational(unit_cost) or _rational(entry_fees) or stop_price is not None or target_price is not None):
        raise CorporateActionError("flat_position_cost_and_protection_must_be_empty")
    return _seal({"schema_version": STATE_SCHEMA, "engine_id": ENGINE_ID, "numeric_policy": NUMERIC_POLICY,
        "quantity_policy": QUANTITY_POLICY, "currency": currency, "calendar": deepcopy(calendar),
        "initial_session": as_of_session, "as_of_session": as_of_session, "cash": _format(_rational(cash)),
        "position": position, "raw_indicator_history": _history(indicator_history, sessions),
        "known_actions": {}, "applied_events": [], "source_authenticated": False,
        "real_source_acceptance": "PENDING", "permissions": dict(_PERMISSIONS),
        "information_policy": "EFFECTIVE_SESSION_ACCOUNTING_ONLY_NOT_PUBLICATION_KNOWLEDGE"})


def _state(value):
    if type(value) is not dict or value.get("schema_version") != STATE_SCHEMA or value.get("engine_id") != ENGINE_ID:
        raise CorporateActionError("independent_action_state_required_old_runner_state_rejected")
    if value.get("state_hash") != _seal(value)["state_hash"]:
        raise CorporateActionError("action_state_hash_mismatch")
    if value.get("quantity_policy") != QUANTITY_POLICY or value.get("numeric_policy") != NUMERIC_POLICY or value.get("permissions") != _PERMISSIONS:
        raise CorporateActionError("action_state_policy_mismatch")
    if value.get("source_authenticated") is not False or value.get("real_source_acceptance") != "PENDING":
        raise CorporateActionError("action_source_acceptance_must_remain_pending")
    sessions, _ = _calendar(value["calendar"])
    if value["as_of_session"] not in sessions or value["initial_session"] not in sessions:
        raise CorporateActionError("action_state_session_invalid")
    _rational(value["cash"])
    position = value["position"]
    for key in ("quantity", "unit_cost", "entry_fees"):
        _rational(position[key])
    for key in ("stop_price", "target_price"):
        if position[key] is not None:
            _rational(position[key], positive=True)
    _history(value["raw_indicator_history"], sessions)
    if type(value["known_actions"]) is not dict or len(value["known_actions"]) > MAX_ACTIONS or type(value["applied_events"]) is not list:
        raise CorporateActionError("action_state_event_inventory_invalid")
    seen = set()
    for event in value["applied_events"]:
        identity = event["action_id"]
        action = value["known_actions"].get(identity)
        if identity in seen or action is None or _hash(action) != event["action_hash"] or action["effective_session"] != event["effective_session"]:
            raise CorporateActionError("action_state_applied_event_binding_conflict")
        if event["effective_session"] > value["as_of_session"] or inspect_action(action, value["calendar"])["status"] != "SUPPORTED":
            raise CorporateActionError("action_state_future_or_unsupported_applied_event")
        if (event["numerator"], event["denominator"]) != (action["numerator"], action["denominator"]):
            raise CorporateActionError("action_state_applied_ratio_conflict")
        seen.add(identity)
    for identity, action in value["known_actions"].items():
        if (action.get("action_id") != identity or action.get("security_id") != position["security_id"]
                or action.get("currency") != value["currency"]):
            raise CorporateActionError("action_state_known_event_identity_conflict")
        if action["effective_session"] <= value["as_of_session"] and identity not in seen:
            raise CorporateActionError("action_state_unprocessed_historical_event")
    return sessions


def advance_action_session(state, actions, session):
    """Advance exactly one declared trading day; repeated event IDs never reapply."""
    sessions = _state(state)
    current = sessions.index(state["as_of_session"])
    if current + 1 >= len(sessions) or session != sessions[current + 1]:
        raise CorporateActionError("action_session_must_advance_one_declared_trading_day")
    if type(actions) is not list or len(actions) > MAX_ACTIONS:
        raise CorporateActionError("action_batch_invalid")
    next_state = deepcopy(state)
    replayed, due = [], []
    applied = {event["action_id"]: event for event in next_state["applied_events"]}
    for action in actions:
        if type(action) is not dict:
            raise CorporateActionError("corporate_action_object_required")
        identity = _text(action.get("action_id"))
        _text(action.get("action_type"), 80)
        day = _day(action.get("effective_session"))
        if day not in sessions:
            raise CorporateActionError("action_effective_session_not_in_declared_calendar")
        if action.get("security_id") != state["position"]["security_id"] or action.get("currency") != state["currency"]:
            raise CorporateActionError("action_account_security_or_currency_conflict")
        previous = next_state["known_actions"].get(identity)
        if previous is not None and _hash(previous) != _hash(action):
            raise CorporateActionError("action_identity_content_conflict")
        next_state["known_actions"][identity] = deepcopy(action)
        if identity in applied:
            replayed.append(identity)
    if len(next_state["known_actions"]) > MAX_ACTIONS:
        raise CorporateActionError("action_state_event_capacity_exceeded")
    source_keys, split_days = {}, {}
    for identity, action in next_state["known_actions"].items():
        source = action.get("source")
        if (type(source) is dict and type(source.get("provider")) is str and source["provider"]
                and type(source.get("raw_event_id")) is str and source["raw_event_id"]):
            source_key = (source["provider"], action["security_id"], action.get("action_type"), source["raw_event_id"])
            if source_key in source_keys and source_keys[source_key] != identity:
                raise CorporateActionError("source_event_registered_under_multiple_action_ids")
            source_keys[source_key] = identity
        if action.get("action_type") == "SPLIT":
            day = action["effective_session"]
            if day in split_days and split_days[day] != identity:
                raise CorporateActionError("multiple_split_events_same_session_unsupported")
            split_days[day] = identity
    for identity, action in next_state["known_actions"].items():
        if identity in applied:
            continue
        if action["effective_session"] <= state["as_of_session"]:
            raise CorporateActionError("unprocessed_historical_action:" + identity)
        if action["effective_session"] > session:
            continue
        inspected = inspect_action(action, state["calendar"])
        if inspected["status"] != "SUPPORTED":
            raise CorporateActionError("unsupported_due_corporate_action:" + identity + ":" + ";".join(inspected["reasons"]))
        due.append(action)
    # All due actions pass before any detached position is adjusted.
    position = next_state["position"]
    before_cost = _rational(position["quantity"]) * _rational(position["unit_cost"])
    changes = []
    for action in sorted(due, key=lambda item: item["action_id"]):
        before = deepcopy(position)
        ratio = Fraction(action["numerator"], action["denominator"])
        position["quantity"] = _format(_rational(position["quantity"]) * ratio)
        for key in ("unit_cost", "stop_price", "target_price"):
            if position[key] is not None:
                position[key] = _format(_rational(position[key]) / ratio)
        event = {"action_id": action["action_id"], "action_hash": _hash(action), "effective_session": session,
                 "numerator": action["numerator"], "denominator": action["denominator"]}
        next_state["applied_events"].append(event)
        changes.append({**event, "position_before": before, "position_after": deepcopy(position)})
    after_cost = _rational(position["quantity"]) * _rational(position["unit_cost"])
    if before_cost != after_cost or next_state["cash"] != state["cash"] or position["entry_fees"] != state["position"]["entry_fees"]:
        raise CorporateActionError("split_accounting_conservation_failure")
    next_state["as_of_session"] = session
    next_state = _seal(next_state)
    receipt = {"schema_version": RECEIPT_SCHEMA, "engine_id": ENGINE_ID,
        "from_session": state["as_of_session"], "to_session": session,
        "previous_state_hash": state["state_hash"], "state_hash": next_state["state_hash"],
        "applied": changes, "replayed_action_ids": sorted(set(replayed)),
        "cash_unchanged": True, "entry_fees_unchanged": True, "cost_basis_before": _format(before_cost), "cost_basis_after": _format(after_cost),
        "source_authenticated": False, "real_source_acceptance": "PENDING",
        "permissions": dict(_PERMISSIONS), "new_economic_runs": 0, "external_calls": 0}
    return {"state": next_state, "receipt": {**receipt, "receipt_hash": _hash(receipt)}}


def indicator_history_as_of(state, cutoff):
    """Return a derived split-adjusted view; retain raw rows and exclude future effects."""
    sessions = _state(state)
    if _day(cutoff) not in sessions or cutoff > state["as_of_session"]:
        raise CorporateActionError("indicator_cutoff_must_be_an_already_processed_session")
    rows = []
    for raw in state["raw_indicator_history"]:
        if raw["session"] > cutoff:
            continue
        factor = Fraction(1)
        for event in state["applied_events"]:
            if raw["session"] < event["effective_session"] <= cutoff:
                factor *= Fraction(event["numerator"], event["denominator"])
        row = deepcopy(raw)
        for key in ("open", "high", "low", "close"):
            row[key] = _format(_rational(raw[key]) / factor)
        row["volume"] = _format(_rational(raw["volume"]) * factor)
        row["split_factor"] = _format(factor)
        rows.append(row)
    return {"schema_version": "hakimi-split-indicator-view-v1", "as_of_session": cutoff,
            "numeric_policy": NUMERIC_POLICY, "rows": rows, "raw_history_unchanged": True,
            "future_events_applied": False, "source_authenticated": False, "real_source_acceptance": "PENDING"}
