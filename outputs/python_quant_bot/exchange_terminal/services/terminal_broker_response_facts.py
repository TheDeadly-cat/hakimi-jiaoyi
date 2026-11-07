"""Pure scope-checked response facts, never external authentication/admission.

Only the trusted coordinator supplies the original ACTION from its journal and
the independently retained expected event ID. A self-sealed dictionary is not
source authentication. Both original frames are decoded again through the same
trusted codec. This version is permanently the plaintext OFFLINE codec profile;
it neither imports the SDK nor records a journal outcome or economic snapshot.
"""
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
import json
import math
from types import MappingProxyType

from ..adapters import futu_us_equity_simulate_wire_v2 as codec_contract
from ..adapters.futu_us_equity_simulate_wire_v2 import CodecError, SimulateCodec
from . import terminal_broker_execution_plan as contract
from . import terminal_broker_execution_journal as journal
from .terminal_broker_wire_profile import (
    VerifiedWireProfile, WireProfileError, SCHEMA_V3 as PROFILE_SCHEMA_V3, actions_for_profile,
)


SCHEMA = "hakimi-broker-response-facts-v2"
SCHEMA_V3 = "hakimi-broker-response-facts-v3"
SUPPORTED_ACTIONS = frozenset({"trade_submit", "trade_cancel", "trade_observe", "trade_accounts",
                               "trade_funds", "trade_positions", "trade_fees",
                               "quote_runtime", "quote_security", "quote_snapshot"})
QUOTE_ACTIONS = frozenset({"quote_runtime", "quote_security", "quote_snapshot"})
HANDSHAKE_ACTIONS = frozenset({"quote_init", "trade_init"})
QUOTE_ACTIONS_V3 = QUOTE_ACTIONS | {"quote_market_state"}
SUPPORTED_ACTIONS_V3 = SUPPORTED_ACTIONS | HANDSHAKE_ACTIONS | {"quote_market_state"}
# Pinned Trd_Common_pb2 OrderStatus. Labels describe the source enum only; they
# never establish fee finality, cash release, or exact cumulative fill notional.
ORDER_STATUS_NAMES = MappingProxyType({
    -1: "UNKNOWN", 0: "UNSUBMITTED", 1: "WAITING_SUBMIT", 2: "SUBMITTING",
    3: "SUBMIT_FAILED", 4: "TIME_OUT", 5: "SUBMITTED", 10: "FILLED_PART",
    11: "FILLED_ALL", 12: "CANCELLING_PART", 13: "CANCELLING_ALL",
    14: "CANCELLED_PART", 15: "CANCELLED_ALL", 21: "FAILED", 22: "DISABLED",
    23: "DELETED", 24: "FILL_CANCELLED",
})
_TOKEN = object()


class ResponseFactsError(ValueError):
    pass


def _require(condition, code):
    if not condition:
        raise ResponseFactsError(code)


def supported_actions_for_profile(profile_or_dict):
    """Keep legacy initialization behavior; v3 alone records handshake facts."""
    catalog = actions_for_profile(profile_or_dict)
    value = profile_or_dict.as_dict() if type(profile_or_dict) is VerifiedWireProfile else profile_or_dict
    supported = SUPPORTED_ACTIONS_V3 if value["schema_version"] == PROFILE_SCHEMA_V3 else SUPPORTED_ACTIONS
    return frozenset(action for action in supported if action in catalog)


def _missing(items, field, reason="NOT_PRESENT", required_for="scope_or_requested_fact"):
    row = {"field": field, "reason": reason, "required_for": required_for}
    if row not in items:
        items.append(row)


def _field(tree, name, path, missing, *, required=False):
    _require(type(tree) is dict, "response_message_shape_invalid")
    node = tree.get(name)
    if node is None or type(node) is dict and node.get("present") is False:
        if required:
            _missing(missing, path)
        return None
    _require(type(node) is dict and set(node) == {"present", "value"}
             and node["present"] is True and node["value"] is not None, "response_presence_invalid")
    return node["value"]


def _list(tree, name, path, missing):
    node = tree.get(name)
    if node is None:
        return []  # Protobuf repeated fields have no independent presence bit.
    _require(type(node) is dict and set(node) == {"present", "value"}
             and type(node["present"]) is bool and type(node["value"]) is list,
             "response_list_shape_invalid")
    _require(node["present"] == bool(node["value"]) and len(node["value"]) <= 1000,
             "response_list_presence_or_limit_invalid")
    return node["value"]


def _expect(tree, name, expected, path, missing, *, required=True):
    value = _field(tree, name, path, missing, required=required)
    if value is None:
        return not required
    _require(type(value) is type(expected) and value == expected, "response_scope_mismatch:" + path)
    return True


def _number(tree, name, path, missing, *, required=False):
    value = _field(tree, name, path, missing, required=required)
    if value is None:
        return None
    _require(type(value) in (int, float) and math.isfinite(value), "response_number_invalid:" + path)
    return format(Decimal(str(value)), "f")


def _uint(value, path):
    _require(type(value) is int and 0 < value < 2**64, "response_uint_invalid:" + path)
    return value


def _opaque(value):
    _require(type(value) is str and 1 <= len(value) <= 128 and value.isascii()
             and all(32 < ord(char) < 127 for char in value), "response_opaque_order_id_invalid")
    return value


def _header(s2c, profile, missing):
    header = _field(s2c, "header", "s2c.header", missing, required=True)
    if header is None:
        return False
    complete = True
    for key, expected in {"trdEnv": 0, "accID": int(profile["order"]["account_id"]), "trdMarket": 2}.items():
        complete = _expect(header, key, expected, "s2c.header." + key, missing) and complete
    return complete


def _action_event(event, expected_id, profile, request_frame, received_at):
    # No public pure journal event verifier exists. Reuse its exact canonical
    # seal/schema contract, without opening a journal or trusting a self-reported ID.
    contract._hash(expected_id)
    contract._fields(event, {"schema_version", "seq", "previous", "at", "kind", "payload",
                             "request_id", "request_hash", "result", "id"})
    _require(event["id"] == expected_id == contract.digest({k: v for k, v in event.items() if k != "id"}),
             "original_action_receipt_identity_mismatch")
    _require(event["schema_version"] == journal.SCHEMA and event["kind"] == "ACTION",
             "original_journal_action_required")
    contract._integer(event["seq"], 1, journal.MAX_EVENTS)
    contract._hash(event["previous"])
    journal.request(event["request_id"])
    payload, result = event["payload"], event["result"]
    fields = {"profile", "action", "operation_id", "frame_sha256", "frame_bytes", "authorization_id", "broker_order_id"}
    v3_submit = (profile["schema_version"] == PROFILE_SCHEMA_V3 and type(payload) is dict
                 and payload.get("action") == "trade_submit")
    contract._fields(payload, fields | {"submit_observation"} if v3_submit else fields)
    _require(contract.canonical_bytes(payload["profile"]) == contract.canonical_bytes(profile),
             "original_action_profile_changed")
    _require(payload["operation_id"] == event["request_id"], "original_action_request_mismatch")
    _require(event["request_hash"] == contract.digest({"kind": "ACTION", "payload": payload}),
             "original_action_request_hash_mismatch")
    action = payload["action"]
    _require(type(action) is str and action in supported_actions_for_profile(profile), "response_action_unsupported")
    contract._hash(payload["authorization_id"])
    _require(type(payload["frame_bytes"]) is int and payload["frame_bytes"] == len(request_frame)
             and payload["frame_sha256"] == sha256(request_frame).hexdigest(), "original_request_frame_changed")
    contract._fields(result, {"status", "operation_id", "action", "attempt_count", "dispatch_authorization_granted"})
    _require(result["status"] == "DISPATCH_INTENT" and result["operation_id"] == event["request_id"]
             and result["action"] == action and result["dispatch_authorization_granted"] is False,
             "original_action_result_invalid")
    contract._integer(result["attempt_count"], 1, profile["wire_bounds"]["actions"][action])
    at = contract._time(event["at"])
    _require(contract._time(profile["created_at"]) <= at < contract._time(profile["wire_bounds"]["valid_until"])
             and received_at >= at, "response_time_before_original_action")
    if v3_submit:
        # Replay the sealed admission at the original ACTION time. A late
        # response does not re-authorize dispatch or refresh the observations.
        from .terminal_broker_submit_observation import (
            SubmitObservationError, validate_archived_submit_observation,
        )
        try:
            validate_archived_submit_observation(profile, payload["submit_observation"], now=at)
        except SubmitObservationError as error:
            raise ResponseFactsError("original_submit_observation_invalid:" + str(error)) from error
    if action in ("trade_cancel", "trade_observe", "trade_fees"):
        _opaque(payload["broker_order_id"])
    else:
        _require(payload["broker_order_id"] is None, "unexpected_original_order_id")
    return action, payload


def _own_row(s2c, field, id_field, expected_id, missing):
    rows = _list(s2c, field, "s2c." + field, missing)
    if not rows:
        return None, "NOT_FOUND_UNCONFIRMED"
    _require(len(rows) == 1, "duplicate_or_foreign_order_rows")
    row = rows[0]
    identity = _field(row, id_field, "s2c." + field + "[]." + id_field, missing, required=True)
    if identity is None:
        return None, "INCOMPLETE_EVIDENCE"
    _require(_opaque(identity) == expected_id, "response_original_order_id_mismatch")
    return row, "READ_FACTS_MATCHED"


def _bind_request_order_id(codec, profile, action, frame, expected_id):
    """Bind journal ownership to the same exact decoded Request, not session lore.

    The codec currently exposes validation and FrameInfo, not a public request
    projection. Reuse its own pinned Request class and strict decoder here;
    no independent protobuf registry or SDK import is introduced.
    """
    if action not in ("trade_cancel", "trade_observe", "trade_fees"):
        return
    protocol = actions_for_profile(profile)[action][1]
    message = codec_contract._decode(codec._requests[protocol], frame[codec_contract.HEADER_BYTES:], request=True)
    c2s = codec_contract._tree(message)["c2s"]
    if action == "trade_cancel":
        ids = [c2s.get("orderIDEx")]
    elif action == "trade_observe":
        ids = c2s.get("filterConditions", {}).get("orderIDExList")
    else:
        ids = c2s.get("orderIdExList")
    _require(type(ids) is list and len(ids) == 1 and type(ids[0]) is str and ids[0] == expected_id,
             "original_action_request_order_id_mismatch")


def _scalar(tree, name, kind, path, missing, *, required=False):
    value = _field(tree, name, path, missing, required=required)
    if value is not None:
        _require(type(value) is kind, "response_scalar_invalid:" + path)
        if kind is int:
            _require(-(2**63) <= value < 2**64, "response_integer_out_of_range:" + path)
        if kind is str:
            _require(len(value) <= 256, "response_text_too_long:" + path)
    return value


def _quote_limitations(missing):
    for field, reason in (("currency", "NOT_PROVIDED_BY_QUOTE_RESPONSE"),
                          ("price_step", "PRICE_SPREAD_IS_NOT_ORDER_TICK_RULE"),
                          ("target_market_state", "SECURITY_MARKET_STATE_NOT_QUERIED"),
                          ("quote_rights", "QUOTE_RIGHTS_NOT_QUERIED")):
        _missing(missing, field, reason, "external_trading_eligibility")
    return {"currency": None, "expected_currency": "USD", "price_step": None,
            "target_market_state": None, "quote_permission_verified": False,
            "trading_eligibility_verified": False, "source_age_seconds": None,
            "freshness_verified": False}


def _quote_basic(s2c, list_name, profile, missing):
    rows = _list(s2c, list_name, "s2c." + list_name, missing)
    if not rows:
        return None, "NOT_FOUND_UNCONFIRMED"
    _require(len(rows) == 1, "duplicate_or_foreign_security_rows")
    path = "s2c." + list_name + "[].basic"
    basic = _field(rows[0], "basic", path, missing, required=True)
    if basic is None:
        return None, "INCOMPLETE_EVIDENCE"
    security = _field(basic, "security", path + ".security", missing, required=True)
    if security is None:
        return None, "INCOMPLETE_EVIDENCE"
    complete = True
    for key, expected in {"market": 11, "code": profile["order"]["asset_code"][3:]}.items():
        complete = _expect(security, key, expected, path + ".security." + key, missing) and complete
    return basic, "READ_FACTS_MATCHED" if complete else "INCOMPLETE_EVIDENCE"


def _project_quote(action, s2c, profile, missing):
    """Observed values only: login/state/lot/spread are not trading admission."""
    if action == "quote_market_state":
        facts = {"market_state_scope": "EXACT_TARGET_SECURITY", "currency": None,
            "expected_currency": "USD", "source_time": None,
            "source_time_scope": "NOT_PROVIDED_BY_MARKET_STATE", "source_age_seconds": None,
            "freshness_verified": False, "quote_permission_verified": False,
            "trading_eligibility_verified": False}
        for name, reason in (("currency", "NOT_PROVIDED_BY_MARKET_STATE"),
                             ("source_time", "NOT_PROVIDED_BY_MARKET_STATE"),
                             ("quote_rights", "QUOTE_RIGHTS_NOT_QUERIED")):
            _missing(missing, name, reason, "external_trading_eligibility")
        rows = _list(s2c, "marketInfoList", "s2c.marketInfoList", missing)
        if not rows:
            return "NOT_FOUND_UNCONFIRMED", facts, {}
        _require(len(rows) == 1, "duplicate_or_foreign_market_state_rows")
        row, path = rows[0], "s2c.marketInfoList[]."
        security = _field(row, "security", path + "security", missing, required=True)
        if security is None:
            return "INCOMPLETE_EVIDENCE", facts, {}
        complete = True
        for key, expected in {"market": 11, "code": profile["order"]["asset_code"][3:]}.items():
            complete = _expect(security, key, expected, path + "security." + key, missing) and complete
            facts[key] = _field(security, key, path + "security." + key, missing)
        state = _scalar(row, "marketState", int, path + "marketState", missing, required=True)
        if state is not None:
            _require(-(2**31) <= state < 2**31, "response_market_state_out_of_int32_range")
        name = _scalar(row, "name", str, path + "name", missing, required=True)
        facts.update(market_state_code=state, security_name=name)
        complete = complete and state is not None and name is not None
        # Enum 5 identifies the provider's continuous US session; this pure
        # response projection does not grant qualification or order permission.
        return "READ_FACTS_MATCHED" if complete else "INCOMPLETE_EVIDENCE", facts, {}
    if action == "quote_runtime":
        facts = {}
        for target, source, kind in (("market_us_code", "marketUS", int),
                ("quote_server_logged_in", "qotLogined", bool), ("trade_server_logged_in", "trdLogined", bool),
                ("server_version", "serverVer", int), ("server_build", "serverBuildNo", int),
                ("server_time_seconds", "time", int)):
            facts[target] = _scalar(s2c, source, kind, "s2c." + source, missing, required=True)
        complete = all(value is not None for value in facts.values())
        local = _number(s2c, "localTime", "s2c.localTime", missing)
        connection = _scalar(s2c, "connID", int, "s2c.connID", missing)
        if connection is not None:
            _uint(connection, "s2c.connID")
        program = _field(s2c, "programStatus", "s2c.programStatus", missing)
        program_type = None if program is None else _scalar(program, "type", int,
            "s2c.programStatus.type", missing, required=True)
        for key, value in (("s2c.localTime", local), ("s2c.connID", connection), ("s2c.programStatus", program)):
            if value is None:
                _missing(missing, key, required_for="runtime_observation")
        _missing(missing, "target_market_state", "GLOBAL_MARKET_US_IS_NASDAQ_NOT_TARGET_SECURITY", "external_trading_eligibility")
        _missing(missing, "quote_rights", "NOT_PROVIDED_BY_GET_GLOBAL_STATE", "external_trading_eligibility")
        facts.update(market_us_scope="NASDAQ_GLOBAL", local_time_seconds=local,
            quote_connection_id=str(connection) if connection is not None else None,
            quote_connection_scope_matched=None, program_status_code=program_type,
            server_time_scope="FUTU_SERVER_CURRENT_TIME_NOT_MARKET_SOURCE_TIME",
            local_time_scope="OPEND_MACHINE_TIME_IF_PRESENT_NO_FALLBACK",
            target_market_state=None, quote_permission_verified=False, trading_eligibility_verified=False,
            source_age_seconds=None, freshness_verified=False)
        return "READ_FACTS_MATCHED" if complete else "INCOMPLETE_EVIDENCE", facts, {}

    list_name = "staticInfoList" if action == "quote_security" else "snapshotList"
    basic, status = _quote_basic(s2c, list_name, profile, missing)
    facts = _quote_limitations(missing)
    if basic is None:
        return status, facts, {}
    path = "s2c." + list_name + "[].basic."
    facts.update(market=_field(_field(basic, "security", path + "security", missing), "market", path + "security.market", missing),
                 code=_field(_field(basic, "security", path + "security", missing), "code", path + "security.code", missing))
    type_field = "secType" if action == "quote_security" else "type"
    complete = _expect(basic, type_field, 3, path + type_field, missing) and status == "READ_FACTS_MATCHED"
    security_type = _scalar(basic, type_field, int, path + type_field, missing, required=True)
    lot = _scalar(basic, "lotSize", int, path + "lotSize", missing, required=True)
    if lot is not None:
        _require(lot > 0, "response_lot_size_invalid")
    facts.update(security_type=security_type, lot_size=lot, lot_is_complete_trading_rule=False)
    complete = complete and lot is not None
    if action == "quote_security":
        identity = _scalar(basic, "id", int, path + "id", missing, required=True)
        if identity is not None:
            _require(0 < identity < 2**63, "response_static_security_id_invalid")
        delisting = _scalar(basic, "delisting", bool, path + "delisting", missing)
        exchange = _scalar(basic, "exchType", int, path + "exchType", missing)
        for name, value in (("delisting", delisting), ("exchType", exchange)):
            if value is None:
                _missing(missing, path + name, required_for="security_status_observation")
        facts.update(static_security_id=str(identity) if identity is not None else None,
                     delisting=delisting, exchange_type=exchange)
        complete = complete and identity is not None
    else:
        suspend = _scalar(basic, "isSuspend", bool, path + "isSuspend", missing, required=True)
        current = _number(basic, "curPrice", path + "curPrice", missing, required=True)
        spread = _number(basic, "priceSpread", path + "priceSpread", missing, required=True)
        update = _scalar(basic, "updateTime", str, path + "updateTime", missing, required=True)
        if update == "":
            _missing(missing, path + "updateTime", "EMPTY_SOURCE_TIME", "current_price_source_time")
        timestamp = _number(basic, "updateTimestamp", path + "updateTimestamp", missing)
        security_status = _scalar(basic, "secStatus", int, path + "secStatus", missing)
        for name, value in (("updateTimestamp", timestamp), ("secStatus", security_status)):
            if value is None:
                _missing(missing, path + name, required_for="snapshot_observation")
        facts.update(is_suspended=suspend, current_price=current, price_spread=spread,
            price_spread_scope="ADJACENT_ASK_QUOTE_DIFFERENCE_NOT_ORDER_TICK",
            current_price_update_time=update, current_price_update_timestamp=timestamp,
            current_price_time_zone="America/New_York", source_time_scope="CURRENT_PRICE_ONLY",
            source_time_utc=None, source_time_normalized=False,
            ask_price=_number(basic, "askPrice", path + "askPrice", missing),
            bid_price=_number(basic, "bidPrice", path + "bidPrice", missing),
            security_status_code=security_status)
        # Retain finite zero/negative prices as observations, not usable prices;
        # this projection deliberately performs no clock, RTH or price-rule admission.
        facts["current_price_positive"] = current is not None and Decimal(current) > 0
        complete = complete and suspend is not None and current is not None and spread is not None and bool(update)
    return "READ_FACTS_MATCHED" if complete else "INCOMPLETE_EVIDENCE", facts, {}


def _project_handshake(s2c, missing):
    values = {}
    for target, source in (("connection_id", "connID"), ("user_id", "loginUserID"),
                           ("server_version", "serverVer"), ("keep_alive_interval_seconds", "keepAliveInterval")):
        value = _scalar(s2c, source, int, "s2c." + source, missing, required=True)
        if value is not None:
            if source in {"connID", "loginUserID"}:
                _uint(value, "s2c." + source)
                value = str(value)
            else:
                _require(0 < value < 2**31, "response_handshake_identity_scalar_invalid:" + source)
        values[target] = value
    complete = all(value is not None for value in values.values())
    return "HANDSHAKE_IDENTITY_MATCHED" if complete else "INCOMPLETE_EVIDENCE", values, {}


def _accepted_session_observation(codec, channel):
    binding = codec.accepted_session_binding(channel).as_dict()
    connection = _uint(binding[channel + "_connection_id"], "accepted_session.connection_id")
    user = _uint(binding[channel + "_user_id"], "accepted_session.user_id")
    return {"channel": channel, "connection_id": str(connection), "user_id": str(user),
            "client_id": binding["client_id"], "client_version": binding["client_version"]}


def _public_handshake_presence(presence):
    """The complete AES/key-bearing frame stays in private transport evidence."""
    result = {key: deepcopy(value) for key, value in presence.items() if key in {"retType", "errCode"}}
    s2c = presence.get("s2c")
    if s2c is not None:
        result["s2c"] = deepcopy(s2c)
        if s2c.get("present") is True:
            result["s2c"]["value"] = {key: deepcopy(value) for key, value in s2c["value"].items()
                if key in {"serverVer", "loginUserID", "connID", "keepAliveInterval"}}
    return result


def _project(action, s2c, profile, payload, missing, diagnostics):
    if action in HANDSHAKE_ACTIONS:
        return _project_handshake(s2c, missing)
    if action in QUOTE_ACTIONS_V3:
        return _project_quote(action, s2c, profile, missing)
    order = profile["order"]
    facts, derived = {}, {}
    header_ok = True if action == "trade_accounts" else _header(s2c, profile, missing)
    code = order["asset_code"][3:]
    if action in ("trade_submit", "trade_cancel"):
        identity = _field(s2c, "orderIDEx", "s2c.orderIDEx", missing, required=True)
        if identity is not None:
            identity = _opaque(identity)
            if action == "trade_cancel":
                _require(identity == payload["broker_order_id"], "response_original_order_id_mismatch")
        facts = {"broker_order_id": identity, "account_scope_matched": header_ok,
                 "order_terminal_confirmed": False, "fees_final": None}
        status = ("ACK_SCOPE_MATCHED" if action == "trade_submit" else "CANCEL_ACK_NOT_TERMINAL")
        return status if header_ok and identity is not None else "INCOMPLETE_EVIDENCE", facts, derived

    if action == "trade_observe":
        row, status = _own_row(s2c, "orderList", "orderIDEx", payload["broker_order_id"], missing)
        if row is None:
            return status if header_ok else "INCOMPLETE_EVIDENCE", facts, derived
        complete = header_ok
        for key, expected in {"code": code, "trdSide": {"BUY": 1, "SELL": 2}[order["side"]],
                              "orderType": 1, "secMarket": 2, "currency": 2}.items():
            complete = _expect(row, key, expected, "s2c.orderList[]." + key, missing) and complete
        for key, expected in {"trdMarket": 2, "timeInForce": 0, "fillOutsideRTH": False, "session": 1}.items():
            _expect(row, key, expected, "s2c.orderList[]." + key, missing, required=False)
        quantity = _number(row, "qty", "s2c.orderList[].qty", missing, required=True)
        price = _number(row, "price", "s2c.orderList[].price", missing, required=True)
        if quantity is not None:
            _require(Decimal(quantity) == order["quantity"], "response_order_quantity_mismatch")
        if price is not None:
            _require(Decimal(price) == Decimal(order["limit_price"]), "response_order_limit_price_mismatch")
        complete = complete and quantity is not None and price is not None
        fill_quantity = _number(row, "fillQty", "s2c.orderList[].fillQty", missing, required=True)
        fill_average = _number(row, "fillAvgPrice", "s2c.orderList[].fillAvgPrice", missing, required=True)
        status_code = _field(row, "orderStatus", "s2c.orderList[].orderStatus", missing, required=True)
        _require(status_code is None or type(status_code) is int, "response_order_status_invalid")
        if status_code is not None and status_code not in ORDER_STATUS_NAMES:
            _missing(missing, "s2c.orderList[].orderStatus", "UNRECOGNIZED_ENUM")
        if fill_quantity is not None:
            if Decimal(fill_quantity) < 0:
                diagnostics.append("NEGATIVE_CUMULATIVE_FILL_QUANTITY")
            if Decimal(fill_quantity) > order["quantity"]:
                diagnostics.append("CUMULATIVE_FILL_EXCEEDS_ORDER_QUANTITY")
        if fill_average is not None and Decimal(fill_average) < 0:
            diagnostics.append("NEGATIVE_FILL_AVERAGE_PRICE")
        if fill_quantity is not None and fill_average is not None and Decimal(fill_quantity) > 0:
            if Decimal(fill_average) == 0:
                diagnostics.append("ZERO_PRICE_FOR_POSITIVE_FILL")
            if ((order["side"] == "BUY" and Decimal(fill_average) > Decimal(order["limit_price"])) or
                    (order["side"] == "SELL" and Decimal(fill_average) < Decimal(order["limit_price"]))):
                diagnostics.append("REPORTED_FILL_AVERAGE_OUTSIDE_LIMIT")
        if fill_quantity is not None and fill_average is not None and not diagnostics:
            derived = {"fill_notional_estimate": format(Decimal(fill_quantity) * Decimal(fill_average), "f"),
                       "method": "SOURCE_FILL_QTY_TIMES_SOURCE_FILL_AVG_PRICE", "exact_notional": False}
        for field in ("filled_notional", "fees", "fees_final"):
            _missing(missing, field, "NOT_PROVIDED_BY_ORDER_LIST", "journal_economic_observation")
        facts = {"broker_order_id": payload["broker_order_id"],
                 "code": _field(row, "code", "s2c.orderList[].code", missing), "quantity": quantity,
                 "limit_price": price, "filled_quantity": fill_quantity, "fill_average_price": fill_average,
                 "filled_notional": None, "fees": None, "fees_final": None,
                 "broker_status_code": status_code, "broker_status_name": ORDER_STATUS_NAMES.get(status_code),
                 "update_time_raw": _field(row, "updateTime", "s2c.orderList[].updateTime", missing),
                 "update_timestamp_raw": _field(row, "updateTimestamp", "s2c.orderList[].updateTimestamp", missing)}
        return "READ_FACTS_MATCHED" if complete else "INCOMPLETE_EVIDENCE", facts, derived

    if action == "trade_accounts":
        rows = _list(s2c, "accList", "s2c.accList", missing)
        target, seen = None, set()
        for row in rows:
            identity = _field(row, "accID", "s2c.accList[].accID", missing, required=True)
            _uint(identity, "s2c.accList[].accID")
            _require(identity not in seen, "duplicate_account_rows")
            seen.add(identity)
            if identity == int(order["account_id"]):
                target = row
        if target is None:
            return "NOT_FOUND_UNCONFIRMED", {"target_account_id": None, "returned_account_count": len(rows)}, derived
        complete = _expect(target, "trdEnv", 0, "s2c.accList[target].trdEnv", missing)
        markets = _list(target, "trdMarketAuthList", "s2c.accList[target].trdMarketAuthList", missing)
        _require(all(type(value) is int for value in markets), "account_market_enum_invalid")
        _require(2 in markets, "target_account_us_market_not_present")
        facts = {"target_account_id": order["account_id"], "environment": "SIMULATE" if complete else None,
                 "us_market_listed": True, "returned_account_count": len(rows), "currency": None,
                 "security_firm_code": _field(target, "securityFirm", "securityFirm", missing),
                 "account_status_code": _field(target, "accStatus", "accStatus", missing),
                 "trading_permission_verified": False}
        _missing(missing, "currency", "NOT_PROVIDED_BY_ACCOUNT_LIST", "currency_evidence")
        return "READ_FACTS_MATCHED" if complete else "INCOMPLETE_EVIDENCE", facts, derived

    if action == "trade_funds":
        funds = _field(s2c, "funds", "s2c.funds", missing, required=True)
        if funds is None:
            return "INCOMPLETE_EVIDENCE", facts, derived
        complete = _expect(funds, "currency", 2, "s2c.funds.currency", missing) and header_ok
        facts = {key: _number(funds, source, "s2c.funds." + source, missing, required=True)
                 for key, source in {"cash": "cash", "available_funds": "availableFunds", "power": "power",
                                     "frozen_cash": "frozenCash"}.items()}
        facts.update(currency="USD" if complete else None, requested_currency="USD",
                     cash_available_for_reservation=None, financing_power_is_not_cash=True)
        return "READ_FACTS_MATCHED" if complete else "INCOMPLETE_EVIDENCE", facts, derived

    if action == "trade_positions":
        rows = _list(s2c, "positionList", "s2c.positionList", missing)
        if not rows:
            return "NOT_FOUND_UNCONFIRMED" if header_ok else "INCOMPLETE_EVIDENCE", {
                "broker_positions": [], "owner_positions": None, "owner_allocation_verified": False}, derived
        positions, ids, complete = [], set(), header_ok
        for row in rows:
            identity = _field(row, "positionID", "s2c.positionList[].positionID", missing, required=True)
            _uint(identity, "positionID")
            _require(identity not in ids, "duplicate_position_rows")
            ids.add(identity)
            for key, expected in {"code": code, "secMarket": 2, "currency": 2}.items():
                complete = _expect(row, key, expected, "s2c.positionList[]." + key, missing) and complete
            for key, expected in {"accID": int(order["account_id"]), "trdMarket": 2}.items():
                _expect(row, key, expected, "s2c.positionList[]." + key, missing, required=False)
            side = _field(row, "positionSide", "s2c.positionList[].positionSide", missing, required=True)
            _require(side is None or type(side) is int, "position_side_invalid")
            positions.append({"position_id": str(identity),
                "code": _field(row, "code", "s2c.positionList[].code", missing), "position_side_code": side,
                "quantity": _number(row, "qty", "s2c.positionList[].qty", missing, required=True),
                "can_sell_quantity": _number(row, "canSellQty", "s2c.positionList[].canSellQty", missing, required=True),
                "owner_scope_id": None})
        facts = {"broker_positions": positions, "owner_positions": None, "owner_allocation_verified": False}
        return "READ_FACTS_MATCHED" if complete else "INCOMPLETE_EVIDENCE", facts, derived

    row, status = _own_row(s2c, "orderFeeList", "orderIDEx", payload["broker_order_id"], missing)
    if row is None:
        return status if header_ok else "INCOMPLETE_EVIDENCE", facts, derived
    facts = {"broker_order_id": payload["broker_order_id"],
             "fee_amount": _number(row, "feeAmount", "s2c.orderFeeList[].feeAmount", missing, required=True),
             "currency": None, "requested_currency": "USD", "fees_final": None}
    _missing(missing, "currency", "NOT_PROVIDED_BY_ORDER_FEE", "fee_currency_evidence")
    _missing(missing, "fees_final", "NOT_PROVIDED_BY_ORDER_FEE", "journal_economic_observation")
    return "READ_FACTS_MATCHED" if header_ok else "INCOMPLETE_EVIDENCE", facts, derived


@dataclass(frozen=True, init=False, slots=True)
class VerifiedResponseFacts:
    """Identity/scope-checked OFFLINE facts, not an authenticated broker record."""
    _data: bytes

    def __init__(self, data, token):
        _require(token is _TOKEN and type(data) is bytes, "response_facts_private_factory_required")
        object.__setattr__(self, "_data", data)

    def as_dict(self):
        return json.loads(self._data)


def verify_response_facts(*, profile, codec, action_receipt, expected_action_receipt_id,
                          request_frame, response_frame, received_at):
    """Re-decode original frames and project only supported, present facts.

    Late responses remain observable after expiry; observation is no permission
    to send again. Received time is not a provider's source/update timestamp.
    """
    try:
        _require(type(profile) is VerifiedWireProfile and type(codec) is SimulateCodec,
                 "trusted_profile_and_codec_required")
        value = profile.as_dict()
        catalog = actions_for_profile(value)
        v3 = value["schema_version"] == PROFILE_SCHEMA_V3
        _require(value["mode"] == "OFFICIAL_SIMULATION" and
                 value["protocol_policy"]["production_transport_available"] is False,
                 "offline_simulate_response_only")
        received_at = contract._now(received_at)
        limit = value["wire_bounds"]["max_frame_bytes"]
        for frame in (request_frame, response_frame):
            _require(type(frame) is bytes and 44 < len(frame) <= limit, "bounded_original_frame_required")
        action, payload = _action_event(action_receipt, expected_action_receipt_id, value, request_frame, received_at)
        request_info = codec.validate_request(profile, action, request_frame)
        _bind_request_order_id(codec, value, action, request_frame, payload["broker_order_id"])
        response = codec.decode_response(profile, action, request_info.serial, response_frame)
        _require(type(response.ret_type) is int, "response_ret_type_invalid")
        presence, missing, diagnostics = response.fields(), [], []
        session_observation = None
        facts, derived, status = {}, {}, "API_ERROR_RESPONSE"
        if response.ret_type == 0:
            s2c = _field(presence, "s2c", "s2c", missing, required=True)
            if s2c is None:
                status = "INCOMPLETE_EVIDENCE"
            else:
                status, facts, derived = _project(action, s2c, value, payload, missing, diagnostics)
                if action == "quote_runtime" and facts["quote_connection_id"] is not None:
                    connection = codec.session_binding().as_dict()["quote_connection_id"]
                    _require(connection is not None and str(connection) == facts["quote_connection_id"],
                             "response_quote_connection_mismatch")
                    facts["quote_connection_scope_matched"] = True
        if v3:
            channel = catalog[action][0]
            if action not in HANDSHAKE_ACTIONS or status == "HANDSHAKE_IDENTITY_MATCHED":
                session_observation = _accepted_session_observation(codec, channel)
            if action in HANDSHAKE_ACTIONS:
                if status == "HANDSHAKE_IDENTITY_MATCHED":
                    _require(all(facts[key] == session_observation[key] for key in ("connection_id", "user_id")),
                             "response_handshake_accepted_session_mismatch")
                    facts.update(client_id=session_observation["client_id"], client_version=session_observation["client_version"])
                presence = _public_handshake_presence(presence)
        result = {
            "schema_version": SCHEMA_V3 if v3 else SCHEMA, "status": status, "profile_id": value["id"],
            "base_plan_id": value["base_plan_id"], "mode": value["mode"], "action": action,
            "protocol": catalog[action][1], "serial": request_info.serial,
            "journal_receipt_id": expected_action_receipt_id, "request_id": action_receipt["request_id"],
            "intent_scope_id": value["deduplication"]["intent_scope_id"],
            "account_scope_id": value["deduplication"]["account_scope_id"],
            "workspace_context": value["workspace_context"],
            "request_frame": {"sha256": sha256(request_frame).hexdigest(), "bytes": len(request_frame)},
            "response_frame": {"sha256": sha256(response_frame).hexdigest(), "bytes": len(response_frame)},
            "received_at": received_at.isoformat(),
            "received_after_profile_expiry": received_at >= contract._time(value["wire_bounds"]["valid_until"]),
            "ret_type": response.ret_type, "presence": presence, "facts": facts, "derived": derived,
            "missing": missing, "diagnostics": diagnostics, "needs_reconciliation": bool(diagnostics),
            "status_semantics": "SCOPE_AND_PRESENCE_ONLY", "test_only": True, "source_authenticated": False,
            "research_eligibility": deepcopy(value["research_eligibility"]),
            "journal_observation_ready": False, "reservation_ready": False,
            "received_at_is_source_update_time": False, "economic_acceptance": "NOT_INFERRED",
            "permissions": dict(contract.PERMISSIONS),
        }
        if v3:
            result["session_observation"] = session_observation
        sealed = {**result, "id": contract.digest(result)}
        return VerifiedResponseFacts(contract.canonical_bytes(sealed), _TOKEN)
    except (contract.PlanError, journal.JournalError, CodecError, WireProfileError) as error:
        raise ResponseFactsError("response_facts_invalid:" + str(error)) from error
