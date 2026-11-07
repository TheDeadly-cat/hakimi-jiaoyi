"""Pure v2 wire budget; no SDK import, transport, authorization or journal.

The v1 plan remains an immutable original. Its validator proves all original
bindings, while every v2 wire allowance must be supplied explicitly. A profile
never upgrades the v1 adapter identity into v2 transport support. Workspace
identity is provenance only: account and original-intent scopes remain global
across workspaces. Python factory tokens are a trusted-code boundary, not a
defence against arbitrary code running inside this process.
"""
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
import json
from types import MappingProxyType

from . import terminal_broker_execution_plan as original


SCHEMA = "hakimi-broker-wire-profile-v2"
SCHEMA_V3 = "hakimi-broker-wire-profile-v3"
PINNED_SDK_NAME = "futu-api"
PINNED_SDK_VERSION = "10.7.6708"
PINNED_WHEEL_SHA256 = "a3bc7609fc7b60c0ca3cd2971bc8b81819338d3c88ad25d1bd3f647d781554b5"
MODE_CONTRACTS = MappingProxyType({
    "OFFICIAL_SIMULATION": ("SIMULATE", "hakimi-futu-us-equity-simulate-wire-v2"),
    "LIVE_CANDIDATE": ("REAL", "hakimi-futu-us-equity-real-wire-v2"),
})
MODE_CONTRACTS_V3 = MappingProxyType({
    "OFFICIAL_SIMULATION": ("SIMULATE", "hakimi-futu-us-equity-simulate-wire-v3"),
    "LIVE_CANDIDATE": ("REAL", "hakimi-futu-us-equity-real-wire-v3"),
})
PERMISSIONS = MappingProxyType(dict(original.PERMISSIONS))
PROTOCOL_POLICY = MappingProxyType({
    # Pinned constant.py:257-274 and utils.py MESSAGE_HEAD_FMT. Client ID/version
    # belong to a separate sealed CodecSessionBinding, never old SysConfig/env.
    "format": "PROTOBUF", "proto_fmt": 0, "proto_ver": 0, "header_bytes": 44,
    "encryption_policy": "PLAINTEXT_OFFLINE_CODEC_TEST", "recv_notify": False,
    "production_transport_available": False,
})

# Pinned wheel futu/common/constant.py:24-85. None denotes a transport/policy
# event, never a wildcard permitting arbitrary protocol IDs.
WIRE_ACTIONS = MappingProxyType({
    "quote_connect": ("quote", None), "trade_connect": ("trade", None),
    "quote_init": ("quote", 1001), "trade_init": ("trade", 1001),
    "quote_runtime": ("quote", 1002), "trade_accounts": ("trade", 2001),
    "trade_funds": ("trade", 2101), "trade_positions": ("trade", 2102),
    "quote_security": ("quote", 3202), "quote_snapshot": ("quote", 3203),
    "trade_submit": ("trade", 2202), "trade_observe": ("trade", 2201),
    "trade_cancel": ("trade", 2205), "trade_fees": ("trade", 2225),
    "quote_heartbeat": ("quote", 1004), "trade_heartbeat": ("trade", 1004),
    "trade_unlock": ("trade", 2005), "trade_subscribe": ("trade", 2008),
    "quote_subscribe": ("quote", 3001), "quote_push_registration": ("quote", 3002),
    "quote_reconnect": ("quote", None), "trade_reconnect": ("trade", None),
    "push_acceptance": ("any", None), "unknown_protocol": ("any", None),
    "application_retry": ("any", None),
})
PROTOCOL_LIMITS = MappingProxyType({
    "quote_connect": 1, "trade_connect": 1, "quote_init": 1, "trade_init": 1,
    "quote_runtime": 1, "trade_accounts": 1, "trade_funds": 1, "trade_positions": 1,
    "quote_security": 1, "quote_snapshot": 1, "trade_submit": 1, "trade_observe": 5,
    "trade_cancel": 1, "trade_fees": 1,
    "quote_heartbeat": 0, "trade_heartbeat": 0, "trade_unlock": 0, "trade_subscribe": 0,
    "quote_subscribe": 0, "quote_push_registration": 0, "quote_reconnect": 0,
    "trade_reconnect": 0, "push_acceptance": 0, "unknown_protocol": 0, "application_retry": 0,
})
WIRE_ACTIONS_V3 = MappingProxyType({**WIRE_ACTIONS, "quote_market_state": ("quote", 3223)})
PROTOCOL_LIMITS_V3 = MappingProxyType({**PROTOCOL_LIMITS, "quote_market_state": 1})
WIRE_BOUND_FIELDS = frozenset({
    "valid_until", "endpoint", "actions", "wall_timeout_seconds", "connect_timeout_seconds",
    "handshake_timeout_seconds", "rpc_timeout_seconds", "cleanup_timeout_seconds",
    "max_frame_bytes", "max_wire_bytes", "max_output_bytes", "reserved_final_output_bytes",
    "max_observation_records", "max_evidence_age_seconds", "max_total_fees",
})
_TOKEN = object()


class WireProfileError(ValueError):
    """An explicit wire budget or one of its original bindings is invalid."""


def _require(condition, code):
    if not condition:
        raise WireProfileError(code)


def _integer(value, minimum, maximum):
    _require(type(value) is int and minimum <= value <= maximum, "wire_integer_bound_invalid")


def _validate_original(base_plan, *, candidate_config, candidate_intent,
                       research_resolution, runtime_identity, control, now):
    try:
        return original.validate_acceptance_plan(
            base_plan, candidate_config=candidate_config, candidate_intent=candidate_intent,
            research_resolution=research_resolution, runtime_identity=runtime_identity,
            control=control, now=now)
    except original.PlanError as error:
        raise WireProfileError("base_plan_binding_invalid:" + str(error)) from error


def _catalogs(schema):
    _require(type(schema) is str and schema in (SCHEMA, SCHEMA_V3), "wire_profile_schema_invalid")
    return ((WIRE_ACTIONS, PROTOCOL_LIMITS, MODE_CONTRACTS) if schema == SCHEMA else
            (WIRE_ACTIONS_V3, PROTOCOL_LIMITS_V3, MODE_CONTRACTS_V3))


def actions_for_profile(profile_or_dict):
    """Select an explicit version's immutable catalog, never grant admission."""
    value = profile_or_dict.as_dict() if type(profile_or_dict) is VerifiedWireProfile else profile_or_dict
    _require(type(value) is dict, "wire_profile_schema_invalid")
    return _catalogs(value.get("schema_version"))[0]


def _bounds(value, base_plan, now, *, schema=SCHEMA):
    actions, limits, _ = _catalogs(schema)
    original._fields(value, WIRE_BOUND_FIELDS)
    original._fields(value["endpoint"], {"host", "port"})
    _require(value["endpoint"]["host"] == "127.0.0.1", "wire_local_endpoint_required")
    _integer(value["endpoint"]["port"], 1, 65535)
    _require(original.canonical_bytes(value["endpoint"]) ==
             original.canonical_bytes(base_plan["bounds"]["endpoint"]), "wire_endpoint_changed")
    original._fields(value["actions"], actions)
    for action, limit in limits.items():
        _integer(value["actions"][action], 0, limit)
    for channel in ("quote", "trade"):
        _require(value["actions"][channel + "_connect"] == value["actions"][channel + "_init"],
                 "wire_connection_handshake_budget_mismatch:" + channel)

    _integer(value["wall_timeout_seconds"], 1, 180)
    for name in ("connect_timeout_seconds", "handshake_timeout_seconds", "rpc_timeout_seconds"):
        _integer(value[name], 1, min(15, value["wall_timeout_seconds"]))
    _integer(value["cleanup_timeout_seconds"], 1, 5)
    _integer(value["max_frame_bytes"], PROTOCOL_POLICY["header_bytes"] + 1, 64 * 1024)
    _integer(value["max_wire_bytes"], 1, 96 * 1024)
    _integer(value["max_output_bytes"], 1, 128 * 1024)
    _integer(value["reserved_final_output_bytes"], 16 * 1024, 128 * 1024)
    _require(value["max_frame_bytes"] <= value["max_wire_bytes"] and
             value["max_wire_bytes"] + value["reserved_final_output_bytes"] <= value["max_output_bytes"],
             "wire_byte_budgets_inconsistent")
    _integer(value["max_observation_records"], 1, 50)
    _integer(value["max_evidence_age_seconds"], 1, 30)
    fee = original._money(value["max_total_fees"], allow_zero=True)
    _require(fee <= Decimal(base_plan["bounds"]["max_total_fees"]), "wire_fee_ceiling_exceeds_base")
    until = original._time(value["valid_until"])
    _require(now < until <= original._time(base_plan["bounds"]["valid_until"]),
             "wire_expiry_outside_base")
    _require((until - now).total_seconds() >= value["wall_timeout_seconds"] + value["cleanup_timeout_seconds"],
             "wire_budget_exceeds_remaining_lifetime")
    return deepcopy(value)


def _budget_readiness(actions, *, schema=SCHEMA):
    """Describe disabled budget stages; this is never execution admission."""
    requirements = {
        "quote_preflight": ("quote_connect", "quote_init", "quote_runtime", "quote_security", "quote_snapshot"),
        "trade_preflight": ("trade_connect", "trade_init", "trade_accounts", "trade_funds", "trade_positions"),
        "submit": ("quote_connect", "quote_init", "quote_runtime", "quote_security", "quote_snapshot",
                   "trade_connect", "trade_init", "trade_accounts", "trade_funds", "trade_positions", "trade_submit"),
        "observe": ("trade_connect", "trade_init", "trade_observe"),
        "cancel": ("trade_connect", "trade_init", "trade_cancel"),
        "actual_fees": ("trade_connect", "trade_init", "trade_fees"),
    }
    _catalogs(schema)
    if schema == SCHEMA_V3:
        for name in ("quote_preflight", "submit"):
            requirements[name] += ("quote_market_state",)
    stages = {name: {"budget_complete": all(actions[key] > 0 for key in keys),
                     "missing_actions": [key for key in keys if actions[key] == 0]}
              for name, keys in requirements.items()}
    return {"execution_ready": False, "stages": stages,
            "evidence_verified": False, "authorization_granted": False,
            "order_id_required_for": ["observe", "cancel", "actual_fees"]}


@dataclass(frozen=True, init=False, slots=True)
class VerifiedWireProfile:
    """Immutable identity-checked OFFLINE bytes, not an execution permission."""
    _data: bytes

    def __init__(self, data, token):
        _require(token is _TOKEN and type(data) is bytes, "wire_private_factory_required")
        object.__setattr__(self, "_data", data)

    def as_dict(self):
        return json.loads(self._data)


def prepare_wire_profile(*, base_plan, candidate_config, candidate_intent,
                         research_resolution, runtime_identity, control,
                         workspace_context, wire_bounds, now):
    """Bind a new explicitly supplied budget to exact v1 originals, without IO."""
    return _prepare_wire_profile(base_plan=base_plan, candidate_config=candidate_config,
        candidate_intent=candidate_intent, research_resolution=research_resolution,
        runtime_identity=runtime_identity, control=control, workspace_context=workspace_context,
        wire_bounds=wire_bounds, now=now, schema=SCHEMA)


def prepare_wire_profile_v3(*, base_plan, candidate_config, candidate_intent,
                            research_resolution, runtime_identity, control,
                            workspace_context, wire_bounds, now):
    """Seal explicit v3 observation requirements; no v2 upgrade or authority."""
    return _prepare_wire_profile(base_plan=base_plan, candidate_config=candidate_config,
        candidate_intent=candidate_intent, research_resolution=research_resolution,
        runtime_identity=runtime_identity, control=control, workspace_context=workspace_context,
        wire_bounds=wire_bounds, now=now, schema=SCHEMA_V3)


def _prepare_wire_profile(*, base_plan, candidate_config, candidate_intent,
                          research_resolution, runtime_identity, control,
                          workspace_context, wire_bounds, now, schema):
    try:
        _, _, mode_contracts = _catalogs(schema)
        now = original._now(now)
        original._hash(workspace_context)
        _validate_original(base_plan, candidate_config=candidate_config, candidate_intent=candidate_intent,
                           research_resolution=research_resolution, runtime_identity=runtime_identity,
                           control=control, now=now)
        runtime = runtime_identity.as_dict()
        sdk = runtime["sdk"]
        _require(type(sdk) is dict and sdk.get("name") == PINNED_SDK_NAME and
                 sdk.get("version") == PINNED_SDK_VERSION and sdk.get("wheel_sha256") == PINNED_WHEEL_SHA256,
                 "wire_pinned_sdk_identity_required")
        frozen_bounds = _bounds(wire_bounds, base_plan, now, schema=schema)
        mode = base_plan["mode"]
        environment, contract = mode_contracts[mode]
        # v1 validates these exact provider/mode/account scopes. Workspace is
        # deliberately absent; another workspace cannot reset money or claims.
        profile = {
            "schema_version": schema, "status": "OFFLINE_PROFILE_ONLY", "created_at": now.isoformat(),
            "mode": mode, "sdk_environment": environment, "contract_id": contract,
            "workspace_context": workspace_context, "base_plan_id": base_plan["id"],
            **{key: deepcopy(base_plan[key]) for key in (
                "candidate_config", "candidate_intent", "runtime", "order", "research",
                "research_eligibility", "deduplication", "control")},
            "wire_bounds": frozen_bounds,
            "protocol_policy": dict(PROTOCOL_POLICY),
            "budget_readiness": _budget_readiness(frozen_bounds["actions"], schema=schema),
            "capability_gaps": ["WIRE_V2_ADAPTER_NOT_VERIFIED", "CROSS_WORKSPACE_JOURNAL_NOT_AVAILABLE",
                                "SCOPED_AUTHORIZATION_NOT_PROVIDED"],
            "missing_evidence": deepcopy(base_plan["missing_evidence"]),
            "wire_contract": {
                "sdk_contexts_allowed": False, "max_in_flight_per_channel": 1, "max_queued_frames": 0,
                "recv_notify": False, "unsolicited_frames": "COUNT_BYTES_REJECT_CLOSE",
                "counts_scope": "ENTIRE_PROFILE_ACROSS_WORKERS_AND_RESTARTS",
                "account_scope": "PROVIDER_MODE_ACCOUNT_ACROSS_WORKSPACES",
                "intent_scope": "ORIGINAL_INTENT_ACROSS_PLANS_PROFILES_WORKSPACES_AND_RESTARTS",
                "workspace_context_is_provenance_only": True,
                "dispatch": "DURABLE_INTENT_THEN_EVERY_ACTUAL_WRITE_BARRIER",
                "partial_write": "SAME_FRAME_NO_RESUBMIT_UNKNOWN_ON_INTERRUPTION",
                "actual_fees": None, "price_step": None,
                "source_time": "MISSING_REMAINS_UNKNOWN",
                "query_roundtrip_is_not_market_source_time": True,
                "v1_adapter_identity_is_not_v2_support": True,
            },
            "permissions": dict(PERMISSIONS),
        }
        if schema == SCHEMA_V3:
            profile["submit_observation_policy"] = {
                "schema_version": "hakimi-submit-observation-policy-v1",
                "market_scope": "US_COMMON_STOCK",
                "required_handshakes": ["quote_init", "trade_init"],
                "required_actions": ["quote_runtime", "quote_security", "quote_snapshot", "quote_market_state"],
                # Locked 10.7.6708 QotMarketState_Afternoon=5. The policy is
                # a necessary US common-stock observation, not full eligibility.
                "allowed_market_states": [5], "age_basis": "ORIGINAL_ACTION_QUERY_WINDOW",
                "max_evidence_age_seconds": frozen_bounds["max_evidence_age_seconds"],
            }
        sealed = {**profile, "id": original.digest(profile)}
        return VerifiedWireProfile(original.canonical_bytes(sealed), _TOKEN)
    except original.PlanError as error:
        raise WireProfileError("wire_profile_invalid:" + str(error)) from error


def validate_wire_profile(profile, *, expected_profile_id, base_plan, candidate_config, candidate_intent,
                          research_resolution, runtime_identity, control,
                          workspace_context, now):
    """Rebuild the exact stored identity and check remaining lifetime; no IO.

    The expected ID comes from the trusted store, original request or permit,
    never from the supplied dictionary itself. Both typed and serialized inputs
    require it. Re-sealing a legal budget change creates a new identity, not a
    substitute for the stored profile. The return remains OFFLINE_PROFILE_ONLY.
    """
    try:
        value = profile.as_dict() if type(profile) is VerifiedWireProfile else profile
        actions_for_profile(value)
        schema = value["schema_version"]
        original._hash(expected_profile_id)
        _require(value.get("id") == expected_profile_id, "wire_expected_profile_id_mismatch")
        current_time = original._now(now)
        created = original._time(value.get("created_at"))
        _require(current_time >= created, "wire_clock_before_profile")
        bindings = dict(base_plan=base_plan, candidate_config=candidate_config, candidate_intent=candidate_intent,
                        research_resolution=research_resolution, runtime_identity=runtime_identity,
                        control=control, workspace_context=workspace_context)
        prepare = prepare_wire_profile if schema == SCHEMA else prepare_wire_profile_v3
        expected = prepare(**bindings, wire_bounds=value.get("wire_bounds"), now=created)
        _require(original.canonical_bytes(value) == expected._data, "wire_profile_or_binding_changed")
        _validate_original(base_plan, candidate_config=candidate_config, candidate_intent=candidate_intent,
                           research_resolution=research_resolution, runtime_identity=runtime_identity,
                           control=control, now=current_time)
        _bounds(value["wire_bounds"], base_plan, current_time, schema=schema)
        return expected
    except original.PlanError as error:
        raise WireProfileError("wire_profile_invalid:" + str(error)) from error
