"""Necessary v3 observations from the original journal, never trading authority.

The private factory consumes replayed journal state. Public validation is pure:
it checks a frozen bundle at write barriers without opening the journal there.
Receipt age is measured from original query ACTIONs, not response reprojection.
Policy-v1 requires observed quote login, common-stock identity, explicit normal
status, no delisting/suspension, matching positive lots, a positive observed
price and target continuous-session state. These are not price/quantity rules,
market-source freshness, currency/fee qualification or external authorization.
"""
from copy import deepcopy
from dataclasses import dataclass
from datetime import timedelta
import json

from . import terminal_broker_execution_plan as contract

SCHEMA = "hakimi-broker-submit-observation-v1"
PROFILE_SCHEMA = "hakimi-broker-wire-profile-v3"
FACTS_SCHEMA = "hakimi-broker-response-facts-v3"
HANDSHAKES = ("quote_init", "trade_init")
QUERIES = ("quote_runtime", "quote_security", "quote_snapshot", "quote_market_state")
_TOKEN = object()


class SubmitObservationError(ValueError):
    pass


def _require(condition, reason):
    if not condition:
        raise SubmitObservationError(reason)


def _sealed(value):
    _require(type(value) is dict and value.get("id") == contract.digest(
        {key: item for key, item in value.items() if key != "id"}), "submit_observation_identity_invalid")


def _profile(value):
    _sealed(value)
    _require(value.get("schema_version") == PROFILE_SCHEMA, "submit_observation_v3_profile_required")
    age = value["wire_bounds"]["max_evidence_age_seconds"]
    contract._integer(age, 1, 30)
    expected = {"schema_version": "hakimi-submit-observation-policy-v1", "market_scope": "US_COMMON_STOCK",
        "required_handshakes": list(HANDSHAKES), "required_actions": list(QUERIES), "allowed_market_states": [5],
        "age_basis": "ORIGINAL_ACTION_QUERY_WINDOW", "max_evidence_age_seconds": age}
    _require(value.get("submit_observation_policy") == expected, "submit_observation_policy_changed")
    _require(value["permissions"] == dict(contract.PERMISSIONS), "submit_observation_permissions_changed")
    return value


def _session(value, profile):
    _sealed(value)
    _require(value["profile_id"] == profile["id"] and value["scope"] == "OFFLINE_CODEC_BINDING_ONLY",
             "submit_observation_session_profile_changed")
    for key in ("quote_connection_id", "quote_user_id", "trade_connection_id", "trade_user_id"):
        contract._integer(value[key], 1, 2**64 - 1)
    _require(value["quote_user_id"] == value["trade_user_id"], "submit_observation_session_user_mismatch")
    contract._integer(value["client_version"], 1, 2**31 - 1)
    contract._text(value["client_id"], 64)
    return value


def _session_observation(session, channel):
    return {"channel": channel, "connection_id": str(session[channel + "_connection_id"]),
            "user_id": str(session[channel + "_user_id"]), "client_id": session["client_id"],
            "client_version": session["client_version"]}


def _security(profile):
    return {"security_id": profile["order"]["security_id"], "asset_code": profile["order"]["asset_code"],
            "market": 11, "code": profile["order"]["asset_code"][3:]}


def _references(profile, state, session, now):
    from .terminal_broker_wire_profile import actions_for_profile
    catalog = actions_for_profile(profile)
    _require(state["profiles"].get(profile["id"]) == profile, "submit_observation_original_profile_required")
    references = []
    static_lot = None
    for action in HANDSHAKES + QUERIES:
        operations = [(key, row) for key, row in state["actions"].items()
                      if row["profile_id"] == profile["id"] and row["action"] == action]
        _require(len(operations) == 1, "submit_observation_unique_action_required:" + action)
        operation_id, operation = operations[0]
        candidates = [row for row in state["response_facts"].values()
                      if row["profile_id"] == profile["id"] and row["action"] == action]
        _require(len(candidates) == 1, "submit_observation_unique_facts_required:" + action)
        evidence = candidates[0]
        _sealed(evidence)
        channel, protocol = catalog[action]
        _require(evidence["schema_version"] == FACTS_SCHEMA and evidence["request_id"] == operation_id
                 and evidence["journal_receipt_id"] == operation["receipt_id"]
                 and evidence["intent_scope_id"] == profile["deduplication"]["intent_scope_id"]
                 and evidence["account_scope_id"] == profile["deduplication"]["account_scope_id"]
                 and evidence["base_plan_id"] == profile["base_plan_id"] and evidence["protocol"] == protocol
                 and evidence["mode"] == profile["mode"] and evidence["workspace_context"] == profile["workspace_context"],
                 "submit_observation_original_scope_changed:" + action)
        _require(evidence["request_frame"] == {"sha256": operation["frame_sha256"], "bytes": operation["frame_bytes"]},
                 "submit_observation_original_frame_changed:" + action)
        expected_status = "HANDSHAKE_IDENTITY_MATCHED" if action in HANDSHAKES else "READ_FACTS_MATCHED"
        _require(evidence["status"] == expected_status and type(evidence["ret_type"]) is int
                 and evidence["ret_type"] == 0 and evidence["needs_reconciliation"] is False,
                 "submit_observation_facts_not_matched:" + action)
        _require(evidence.get("session_observation") == _session_observation(session, channel),
                 "submit_observation_handshake_session_changed:" + action)
        _require(evidence["test_only"] is True and evidence["source_authenticated"] is False
                 and evidence["permissions"] == dict(contract.PERMISSIONS)
                 and evidence["journal_observation_ready"] is False and evidence["reservation_ready"] is False,
                 "submit_observation_source_boundary_changed")
        started, received = contract._time(operation["recorded_at"]), contract._time(evidence["received_at"])
        _require(contract._time(profile["created_at"]) <= started <= received <= now
                 and started < contract._time(profile["wire_bounds"]["valid_until"]),
                 "submit_observation_original_time_invalid:" + action)
        if action in QUERIES:
            _require((now - started).total_seconds() < profile["wire_bounds"]["max_evidence_age_seconds"],
                     "submit_observation_query_window_expired:" + action)
        facts = evidence["facts"]
        if action == "quote_runtime":
            _require(facts.get("quote_server_logged_in") is True, "submit_observation_quote_login_required")
        elif action in ("quote_security", "quote_snapshot", "quote_market_state"):
            _require(type(facts.get("market")) is int and facts["market"] == 11
                     and facts.get("code") == profile["order"]["asset_code"][3:],
                     "submit_observation_security_changed")
            if action in ("quote_security", "quote_snapshot"):
                _require(type(facts.get("security_type")) is int and facts["security_type"] == 3,
                         "submit_observation_common_stock_required")
            if action == "quote_security":
                _require(facts.get("delisting") is False, "submit_observation_delisting_unknown_or_true")
                static_lot = facts.get("lot_size")
                _require(type(static_lot) is int and static_lot > 0, "submit_observation_positive_lot_required")
            elif action == "quote_snapshot":
                _require(facts.get("is_suspended") is False and type(facts.get("security_status_code")) is int
                         and facts["security_status_code"] == 1, "submit_observation_security_status_not_normal")
                _require(type(facts.get("lot_size")) is int and facts["lot_size"] == static_lot,
                         "submit_observation_lot_mismatch")
                _require(facts.get("current_price_positive") is True, "submit_observation_positive_price_required")
            else:
                _require(type(facts.get("market_state_code")) is int and facts["market_state_code"] == 5,
                         "submit_observation_target_market_not_continuous")
        references.append({"action": action, "operation_id": operation_id,
            "journal_receipt_id": operation["receipt_id"], "facts_id": evidence["id"],
            "action_recorded_at": operation["recorded_at"], "received_at": evidence["received_at"],
            "protocol": protocol, "serial": evidence["serial"],
            "request_frame": deepcopy(evidence["request_frame"]), "response_frame": deepcopy(evidence["response_frame"]),
            "session_observation": deepcopy(evidence["session_observation"])})
    return references


@dataclass(frozen=True, init=False, slots=True)
class VerifiedSubmitObservation:
    _data: bytes

    def __init__(self, data, token):
        _require(token is _TOKEN and type(data) is bytes, "submit_observation_private_factory_required")
        object.__setattr__(self, "_data", data)

    def as_dict(self):
        return json.loads(self._data)


def validate_archived_submit_observation(profile_dict, observation_dict, *, now):
    """Pure replay check at the archived CLAIM/ACTION time, not response time."""
    try:
        profile = _profile(profile_dict)
        value = observation_dict
        contract._fields(value, {"schema_version", "status", "profile_id", "account_scope_id", "intent_scope_id",
            "security", "policy", "session_binding", "evidence", "prepared_at", "expires_at", "source_age_seconds",
            "freshness_verified", "source_authenticated", "fees_known", "trading_authorization_granted", "permissions", "id"})
        _sealed(value)
        _require(value["schema_version"] == SCHEMA and value["status"] == "NECESSARY_OBSERVATIONS_MATCHED"
                 and value["profile_id"] == profile["id"]
                 and value["account_scope_id"] == profile["deduplication"]["account_scope_id"]
                 and value["intent_scope_id"] == profile["deduplication"]["intent_scope_id"]
                 and value["security"] == _security(profile) and value["policy"] == profile["submit_observation_policy"],
                 "submit_observation_profile_scope_changed")
        session = _session(value["session_binding"], profile)
        _require(value["source_age_seconds"] is None and value["freshness_verified"] is False
                 and value["source_authenticated"] is False and value["fees_known"] is False
                 and value["trading_authorization_granted"] is False and value["permissions"] == dict(contract.PERMISSIONS),
                 "submit_observation_does_not_grant_authority")
        now = contract._now(now)
        prepared = contract._time(value["prepared_at"])
        profile_end = contract._time(profile["wire_bounds"]["valid_until"])
        _require(contract._time(profile["created_at"]) <= prepared <= now < profile_end,
                 "submit_observation_profile_expired_or_clock_invalid")
        refs = value["evidence"]
        _require(type(refs) is list and len(refs) == 6
                 and [row["action"] for row in refs] == list(HANDSHAKES + QUERIES),
                 "submit_observation_exact_evidence_required")
        from .terminal_broker_wire_profile import actions_for_profile
        catalog = actions_for_profile(profile)
        expiry = profile_end
        for row in refs:
            contract._fields(row, {"action", "operation_id", "journal_receipt_id", "facts_id", "action_recorded_at",
                "received_at", "protocol", "serial", "request_frame", "response_frame", "session_observation"})
            for key in ("journal_receipt_id", "facts_id"):
                contract._hash(row[key])
            _require(type(row["operation_id"]) is str and contract.candidate.REQUEST.fullmatch(row["operation_id"]),
                     "submit_observation_operation_id_invalid")
            channel, protocol = catalog[row["action"]]
            _require(type(row["protocol"]) is int and row["protocol"] == protocol
                     and row["session_observation"] == _session_observation(session, channel),
                     "submit_observation_evidence_scope_changed")
            contract._integer(row["serial"], 1, 2**32 - 1)
            for key in ("request_frame", "response_frame"):
                contract._fields(row[key], {"sha256", "bytes"})
                contract._hash(row[key]["sha256"])
                contract._integer(row[key]["bytes"], 45, profile["wire_bounds"]["max_frame_bytes"])
            started, received = contract._time(row["action_recorded_at"]), contract._time(row["received_at"])
            _require(contract._time(profile["created_at"]) <= started <= received <= prepared,
                     "submit_observation_evidence_time_invalid")
            if row["action"] in QUERIES:
                expiry = min(expiry, started + timedelta(seconds=profile["wire_bounds"]["max_evidence_age_seconds"]))
        _require(contract._time(value["expires_at"]) == expiry and now < expiry,
                 "submit_observation_query_window_expired")
        return deepcopy(value)
    except (contract.PlanError, KeyError, TypeError, IndexError) as error:
        raise SubmitObservationError("submit_observation_invalid:" + str(error)) from error


def validate_submit_observation(profile, observation, session_binding, now):
    from .terminal_broker_wire_profile import VerifiedWireProfile
    from ..adapters.futu_us_equity_simulate_wire_v2 import CodecSessionBinding
    _require(type(profile) is VerifiedWireProfile and type(observation) is VerifiedSubmitObservation
             and type(session_binding) is CodecSessionBinding, "submit_observation_typed_inputs_required")
    value = validate_archived_submit_observation(profile.as_dict(), observation.as_dict(), now=now)
    _require(value["session_binding"] == session_binding.as_dict(), "submit_observation_current_session_changed")
    return value


def _prepare_submit_observation(profile, state, session_binding, *, now):
    from .terminal_broker_wire_profile import VerifiedWireProfile
    from ..adapters.futu_us_equity_simulate_wire_v2 import CodecSessionBinding
    _require(type(profile) is VerifiedWireProfile and type(session_binding) is CodecSessionBinding,
             "submit_observation_typed_inputs_required")
    current, now = _profile(profile.as_dict()), contract._now(now)
    session = _session(session_binding.as_dict(), current)
    refs = _references(current, state, session, now)
    expiry = min([contract._time(current["wire_bounds"]["valid_until"])] + [
        contract._time(row["action_recorded_at"]) + timedelta(seconds=current["wire_bounds"]["max_evidence_age_seconds"])
        for row in refs if row["action"] in QUERIES])
    body = {"schema_version": SCHEMA, "status": "NECESSARY_OBSERVATIONS_MATCHED", "profile_id": current["id"],
        "account_scope_id": current["deduplication"]["account_scope_id"],
        "intent_scope_id": current["deduplication"]["intent_scope_id"], "security": _security(current),
        "policy": deepcopy(current["submit_observation_policy"]), "session_binding": session, "evidence": refs,
        "prepared_at": now.isoformat(), "expires_at": expiry.isoformat(), "source_age_seconds": None,
        "freshness_verified": False, "source_authenticated": False, "fees_known": False,
        "trading_authorization_granted": False, "permissions": dict(contract.PERMISSIONS)}
    value = {**body, "id": contract.digest(body)}
    validate_archived_submit_observation(current, value, now=now)
    return VerifiedSubmitObservation(contract.canonical_bytes(value), _TOKEN)


def _validate_stored_submit_observation(profile, observation, state, *, now):
    value = validate_archived_submit_observation(profile, observation, now=now)
    refs = _references(profile, state, value["session_binding"], contract._now(now))
    _require(refs == value["evidence"], "submit_observation_original_evidence_changed")
    return value


def _restore_submit_observation(profile, observation, *, recorded_at):
    """Journal-only restoration after its complete original event chain replay."""
    value = validate_archived_submit_observation(profile, observation, now=recorded_at)
    return VerifiedSubmitObservation(contract.canonical_bytes(value), _TOKEN)
