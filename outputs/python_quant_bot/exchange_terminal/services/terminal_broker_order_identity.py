"""Read-only v3 order identity from a recorded, matched original submit ACK.

This is a local provenance binding, not broker authentication, fill evidence or
permission. It introduces no expiry and never reconciles or releases reserves.
Only the journal's replayed original event chain can construct the typed value.
"""
from copy import deepcopy
from dataclasses import dataclass
import json

from . import terminal_broker_execution_plan as contract

SCHEMA = "hakimi-acknowledged-order-identity-v1"
PROFILE_SCHEMA = "hakimi-broker-wire-profile-v3"
_TOKEN = object()
_SESSION_KEYS = ("profile_id", "client_id", "client_version", "quote_connection_id", "quote_user_id",
                 "trade_connection_id", "trade_user_id", "scope")


class AcknowledgedOrderError(ValueError):
    pass


def _require(condition, reason):
    if not condition:
        raise AcknowledgedOrderError(reason)


def _same(left, right):
    return contract.canonical_bytes(left) == contract.canonical_bytes(right)


def _sealed(value):
    _require(type(value) is dict and value.get("id") == contract.digest(
        {key: item for key, item in value.items() if key != "id"}), "acknowledged_order_identity_invalid")


def _opaque(value):
    _require(type(value) is str and 1 <= len(value) <= 128 and value.isascii()
             and all(32 < ord(char) < 127 for char in value), "acknowledged_order_opaque_id_required")
    return value


def _trade_session(session):
    return {"channel": "trade", "connection_id": str(session["trade_connection_id"]),
            "user_id": str(session["trade_user_id"]), "client_id": session["client_id"],
            "client_version": session["client_version"]}


def _session(session, profile):
    contract._fields(session, set(_SESSION_KEYS) | {"broker_order_id", "id"})
    _sealed(session)
    _require(session["profile_id"] == profile["id"] and session["scope"] == "OFFLINE_CODEC_BINDING_ONLY",
             "acknowledged_order_session_profile_changed")
    for key in ("quote_connection_id", "quote_user_id", "trade_connection_id", "trade_user_id"):
        contract._integer(session[key], 1, 2**64 - 1)
    contract._integer(session["client_version"], 1, 2**31 - 1)
    contract._text(session["client_id"], 64)
    _require(session["quote_user_id"] == session["trade_user_id"], "acknowledged_order_session_user_mismatch")


def _validate_value(profile, value):
    _sealed(profile)
    _require(profile.get("schema_version") == PROFILE_SCHEMA, "acknowledged_order_v3_profile_required")
    contract._fields(value, {"schema_version", "status", "broker_order_id", "profile_id", "base_plan_id",
        "account_scope_id", "intent_scope_id", "workspace_context", "order", "claim_request_id", "claim_receipt_id",
        "submit_operation_id", "submit_action_receipt_id", "submit_recorded_at", "ack_response_request_id",
        "ack_response_receipt_id", "ack_facts_id", "ack_received_at", "ack_recorded_at", "request_frame",
        "response_frame", "ack_outcome", "submit_observation_id", "submit_session_binding", "trade_session_observation",
        "test_only", "source_authenticated", "order_terminal_confirmed", "fees_final", "economic_acceptance", "permissions", "id"})
    _sealed(value)
    _opaque(value["broker_order_id"])
    _require(value["schema_version"] == SCHEMA and value["status"] == "ACKNOWLEDGED_IDENTITY_ONLY"
             and value["profile_id"] == profile["id"] and value["base_plan_id"] == profile["base_plan_id"]
             and value["account_scope_id"] == profile["deduplication"]["account_scope_id"]
             and value["intent_scope_id"] == profile["deduplication"]["intent_scope_id"]
             and value["workspace_context"] == profile["workspace_context"] and _same(value["order"], profile["order"]),
             "acknowledged_order_profile_scope_changed")
    for key in ("claim_receipt_id", "submit_action_receipt_id", "ack_response_receipt_id", "ack_facts_id", "submit_observation_id"):
        contract._hash(value[key])
    for key in ("claim_request_id", "submit_operation_id", "ack_response_request_id"):
        _require(type(value[key]) is str and contract.candidate.REQUEST.fullmatch(value[key]),
                 "acknowledged_order_original_operation_required")
    _require(contract._time(value["submit_recorded_at"]) <= contract._time(value["ack_received_at"])
             <= contract._time(value["ack_recorded_at"]), "acknowledged_order_original_time_invalid")
    for key in ("request_frame", "response_frame"):
        contract._fields(value[key], {"sha256", "bytes"})
        contract._hash(value[key]["sha256"])
        contract._integer(value[key]["bytes"], 45, profile["wire_bounds"]["max_frame_bytes"])
    outcome = value["ack_outcome"]
    contract._fields(outcome, {"status", "evidence_id", "sent_bytes", "possible_sent_bytes", "frame_bytes",
                               "broker_order_id", "write_attempted", "response_complete"})
    _require(outcome["status"] == "ACKNOWLEDGED" and outcome["evidence_id"] == value["ack_facts_id"]
             and outcome["broker_order_id"] == value["broker_order_id"] and outcome["write_attempted"] is True
             and outcome["response_complete"] is True and outcome["frame_bytes"] == value["request_frame"]["bytes"]
             and outcome["possible_sent_bytes"] == outcome["frame_bytes"], "acknowledged_order_complete_ack_required")
    contract._integer(outcome["sent_bytes"], 0, outcome["frame_bytes"])
    session = value["submit_session_binding"]
    _session(session, profile)
    _require(session["broker_order_id"] is None and _same(value["trade_session_observation"], _trade_session(session)),
             "acknowledged_order_original_submit_session_changed")
    _require(value["test_only"] is True and value["source_authenticated"] is False
             and value["order_terminal_confirmed"] is False and value["fees_final"] is None
             and value["economic_acceptance"] == "NOT_INFERRED" and _same(value["permissions"], dict(contract.PERMISSIONS)),
             "acknowledged_order_does_not_grant_authority")
    return deepcopy(value)


@dataclass(frozen=True, init=False, slots=True)
class VerifiedAcknowledgedOrder:
    _data: bytes

    def __init__(self, data, token):
        _require(token is _TOKEN and type(data) is bytes, "acknowledged_order_private_factory_required")
        object.__setattr__(self, "_data", data)

    def as_dict(self):
        return json.loads(self._data)


def validate_acknowledged_order(profile, identity, session_binding):
    """Match the current same session, without IO or renewing any time window."""
    from .terminal_broker_wire_profile import VerifiedWireProfile
    from ..adapters.futu_us_equity_simulate_wire_v2 import CodecSessionBinding
    _require(type(profile) is VerifiedWireProfile and type(identity) is VerifiedAcknowledgedOrder
             and type(session_binding) is CodecSessionBinding, "acknowledged_order_typed_inputs_required")
    try:
        current_profile = profile.as_dict()
        value = _validate_value(current_profile, identity.as_dict())
        current = session_binding.as_dict()
        _session(current, current_profile)
        _require(all(_same(current[key], value["submit_session_binding"][key]) for key in _SESSION_KEYS)
                 and current["broker_order_id"] in (None, value["broker_order_id"]),
                 "acknowledged_order_current_session_changed")
        return value
    except (contract.PlanError, KeyError, TypeError) as error:
        raise AcknowledgedOrderError("acknowledged_order_invalid:" + str(error)) from error


def _acknowledged_order_from_state(profile, state, receipts):
    """Private journal factory; inputs must be from its complete ordered replay."""
    from .terminal_broker_submit_observation import validate_archived_submit_observation
    try:
        _sealed(profile)
        if profile.get("schema_version") == "hakimi-broker-wire-profile-v2":
            return None
        _require(profile.get("schema_version") == PROFILE_SCHEMA, "acknowledged_order_v3_profile_required")
        intent = profile["deduplication"]["intent_scope_id"]
        claim = state["claims"].get(intent)
        if claim is None or not claim["submit_started"]:
            return None
        _require(claim["profile_id"] == profile["id"] and _same(claim["order"], profile["order"])
                 and _same(state["profiles"].get(profile["id"]), profile), "acknowledged_order_claim_scope_changed")
        submits = [(key, row) for key, row in state["actions"].items()
                   if row["intent_scope_id"] == intent and row["action"] == "trade_submit"]
        _require(len(submits) == 1, "acknowledged_order_unique_submit_required")
        operation_id, operation = submits[0]
        _require(operation["profile_id"] == profile["id"], "acknowledged_order_submit_profile_changed")
        acknowledgments = [row for row in state["response_facts"].values()
                           if row["request_id"] == operation_id and row["status"] == "ACK_SCOPE_MATCHED"]
        if not acknowledgments:
            return None
        outcome = operation["outcome"]
        _require(type(outcome) is dict and outcome["status"] == "ACKNOWLEDGED",
                 "acknowledged_order_conflicting_submit_outcome")
        selected = [row for row in acknowledgments if row["id"] == outcome["evidence_id"]]
        _require(len(selected) == 1, "acknowledged_order_recorded_ack_chain_required")
        evidence = selected[0]
        broker_id = _opaque(evidence["facts"]["broker_order_id"])
        _require(claim["broker_order_id"] == broker_id == outcome["broker_order_id"],
                 "acknowledged_order_claim_outcome_conflict")
        _require(not any(key != intent and row["broker_order_id"] == broker_id for key, row in state["claims"].items()),
                 "acknowledged_order_shared_ownership_conflict")
        submit = receipts.get(operation_id)
        _require(submit is not None and submit["kind"] == "ACTION" and submit["id"] == operation["receipt_id"]
                 and submit["payload"]["action"] == "trade_submit"
                 and _same(submit["payload"]["profile"], profile), "acknowledged_order_original_submit_required")
        claims = [event for event in receipts.values() if event["kind"] == "CLAIM"
                  and event["payload"]["profile"]["deduplication"]["intent_scope_id"] == intent]
        _require(len(claims) == 1 and _same(claims[0]["payload"]["profile"], profile),
                 "acknowledged_order_original_claim_required")
        claim_event = claims[0]
        bundle = submit["payload"]["submit_observation"]
        validate_archived_submit_observation(profile, bundle, now=contract._time(submit["at"]))
        _require(_same(bundle, claim["submit_observation"]) and _same(bundle, claim_event["payload"]["submit_observation"])
                 and submit["payload"]["authorization_id"] == claim["authorization_id"] == claim_event["payload"]["authorization_id"],
                 "acknowledged_order_original_claim_binding_changed")
        session = bundle["session_binding"]
        expected_frame = {"sha256": operation["frame_sha256"], "bytes": operation["frame_bytes"]}
        for row in acknowledgments:
            _sealed(row)
            _require(row["schema_version"] == "hakimi-broker-response-facts-v3" and row["action"] == "trade_submit"
                     and row["profile_id"] == profile["id"] and row["journal_receipt_id"] == submit["id"]
                     and row["intent_scope_id"] == intent and row["account_scope_id"] == profile["deduplication"]["account_scope_id"]
                     and row["base_plan_id"] == profile["base_plan_id"] and row["workspace_context"] == profile["workspace_context"]
                     and row["mode"] == profile["mode"] and type(row["ret_type"]) is int and row["ret_type"] == 0
                     and row["protocol"] == 2202 and _same(row["request_frame"], expected_frame)
                     and _same(row["session_observation"], _trade_session(session)),
                     "acknowledged_order_ack_scope_conflict")
            detail = row["facts"]
            _require(detail["broker_order_id"] == broker_id and detail["account_scope_matched"] is True
                     and detail["order_terminal_confirmed"] is False and detail["fees_final"] is None
                     and row["needs_reconciliation"] is False and row["diagnostics"] == []
                     and row["test_only"] is True and row["source_authenticated"] is False
                     and _same(row["permissions"], dict(contract.PERMISSIONS)), "acknowledged_order_ack_identity_conflict")
        records = [event for event in receipts.values() if event["kind"] == "VERIFIED_RESPONSE"
                   and event["payload"]["facts"]["id"] == evidence["id"]]
        _require(len(records) == 1 and _same(records[0]["payload"]["facts"], evidence)
                 and records[0]["result"]["disposition"] == "ACKNOWLEDGED",
                 "acknowledged_order_persisted_response_required")
        record = records[0]
        body = {"schema_version": SCHEMA, "status": "ACKNOWLEDGED_IDENTITY_ONLY", "broker_order_id": broker_id,
            "profile_id": profile["id"], "base_plan_id": profile["base_plan_id"],
            "account_scope_id": profile["deduplication"]["account_scope_id"], "intent_scope_id": intent,
            "workspace_context": profile["workspace_context"], "order": deepcopy(profile["order"]),
            "claim_request_id": claim_event["request_id"], "claim_receipt_id": claim_event["id"],
            "submit_operation_id": operation_id, "submit_action_receipt_id": submit["id"], "submit_recorded_at": submit["at"],
            "ack_response_request_id": record["request_id"], "ack_response_receipt_id": record["id"],
            "ack_facts_id": evidence["id"], "ack_received_at": evidence["received_at"], "ack_recorded_at": record["at"],
            "request_frame": deepcopy(evidence["request_frame"]), "response_frame": deepcopy(evidence["response_frame"]),
            "ack_outcome": deepcopy(outcome), "submit_observation_id": bundle["id"],
            "submit_session_binding": deepcopy(session), "trade_session_observation": deepcopy(evidence["session_observation"]),
            "test_only": True, "source_authenticated": False, "order_terminal_confirmed": False, "fees_final": None,
            "economic_acceptance": "NOT_INFERRED", "permissions": dict(contract.PERMISSIONS)}
        value = {**body, "id": contract.digest(body)}
        _validate_value(profile, value)
        return VerifiedAcknowledgedOrder(contract.canonical_bytes(value), _TOKEN)
    except (contract.PlanError, KeyError, TypeError) as error:
        raise AcknowledgedOrderError("acknowledged_order_journal_invalid:" + str(error)) from error
