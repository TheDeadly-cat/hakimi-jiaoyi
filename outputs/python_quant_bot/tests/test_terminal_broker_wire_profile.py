"""Pure synthetic wire profiles: no market run, SDK import, socket or old DB.

The declared pinned wheel digest below is a typed package fixture. Its tiny
synthetic file inventory is deliberately not actual installed SDK evidence.
"""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import timedelta
import unittest
from unittest.mock import patch

from exchange_terminal.services import terminal_broker_execution_plan as original
from exchange_terminal.services import terminal_broker_wire_profile as wire
from tests.test_terminal_broker_execution_plan import (
    NOW, SIM, REAL, RESOLUTION, bounds, canonical, change_manifest, config,
    control, records, runtime_inputs, seal,
)


def wire_bounds():
    return {
        "valid_until": (NOW + timedelta(minutes=10)).isoformat(),
        "endpoint": {"host": "127.0.0.1", "port": 11111},
        "actions": dict(wire.PROTOCOL_LIMITS), "wall_timeout_seconds": 180,
        "connect_timeout_seconds": 15, "handshake_timeout_seconds": 15,
        "rpc_timeout_seconds": 15, "cleanup_timeout_seconds": 5,
        "max_frame_bytes": 64 * 1024, "max_wire_bytes": 96 * 1024,
        "max_output_bytes": 128 * 1024, "reserved_final_output_bytes": 16 * 1024,
        "max_observation_records": 50, "max_evidence_age_seconds": 30,
        "max_total_fees": "1.50",
    }


def runtime(mode=SIM, *, adapter=False, sdk=True, version=None, wheel_hash=None):
    args = runtime_inputs(mode=mode, adapter=adapter, sdk=sdk)
    if sdk:
        def change(manifest):
            row = manifest["dependency_wheels"][0]
            row["sha256"] = wheel_hash or wire.PINNED_WHEEL_SHA256
            if version:
                old_version = row["version"]
                row.update(version=version, filename="futu_api-" + version + "-py3-none-any.whl")
                for name in list(manifest["files"]):
                    if "futu_api-" + old_version + ".dist-info/" in name:
                        replacement = name.replace(old_version, version)
                        manifest["files"][replacement] = manifest["files"].pop(name)
                        args["observed_file_sha256"][replacement] = args["observed_file_sha256"].pop(name)
        change_manifest(args, change)
    return original.verify_runtime_identity(**args)


def fixture(mode=SIM, *, resolution=None, reference=None, terms=None, runtime_value=None):
    resolution = deepcopy(resolution if resolution is not None else RESOLUTION)
    saved, intent = records(mode=mode, terms=terms, resolution=resolution, reference=reference)
    current_runtime = runtime_value if runtime_value is not None else runtime(mode)
    current_control = control(mode)
    base = original.prepare_acceptance_plan(
        candidate_config=saved, candidate_intent=intent, research_resolution=resolution,
        runtime_identity=current_runtime, control=current_control, bounds=bounds(), now=NOW)
    return {"base_plan": base, "candidate_config": saved, "candidate_intent": intent,
            "research_resolution": resolution, "runtime_identity": current_runtime,
            "control": current_control, "workspace_context": "7" * 64,
            "wire_bounds": wire_bounds(), "now": NOW}


def validate(value, args, *, expected_profile_id=None, **changes):
    args = {key: item for key, item in args.items() if key != "wire_bounds"}
    args.update(changes)
    # Test-only convenience for known fixture identities; production callers
    # must take this ID from the trusted store/request/permit, not received JSON.
    if expected_profile_id is None:
        expected_profile_id = value.as_dict()["id"] if type(value) is wire.VerifiedWireProfile else value["id"]
    return wire.validate_wire_profile(value, expected_profile_id=expected_profile_id, **args)


class WireProfileTests(unittest.TestCase):
    def setUp(self):
        self.args = fixture()
        for target in ("builtins.open", "socket.socket.connect", "subprocess.Popen"):
            blocker = patch(target, side_effect=AssertionError("Pure profile must not perform IO"))
            blocker.start()
            self.addCleanup(blocker.stop)

    def test_exact_original_bindings_and_explicit_wire_budget_remain_offline(self):
        value = wire.prepare_wire_profile(**self.args).as_dict()
        self.assertEqual(value["schema_version"], wire.SCHEMA)
        self.assertEqual(value["status"], "OFFLINE_PROFILE_ONLY")
        self.assertEqual(value["base_plan_id"], self.args["base_plan"]["id"])
        self.assertEqual(value["wire_bounds"], self.args["wire_bounds"])
        for key in ("candidate_config", "candidate_intent", "runtime", "order", "research",
                    "research_eligibility", "deduplication", "control"):
            self.assertEqual(value[key], self.args["base_plan"][key])
        self.assertEqual(value["permissions"], dict(original.PERMISSIONS))
        self.assertFalse(any(value["permissions"].values()))
        self.assertFalse(value["budget_readiness"]["execution_ready"])
        self.assertEqual(value["id"], original.digest({k: v for k, v in value.items() if k != "id"}))

    def test_profile_is_immutable_and_returned_data_cannot_mutate_it(self):
        profile = wire.prepare_wire_profile(**self.args)
        before = profile.as_dict()
        with self.assertRaises(FrozenInstanceError):
            profile._data = b"{}"
        with self.assertRaisesRegex(wire.WireProfileError, "private_factory"):
            wire.VerifiedWireProfile(b"{}", object())
        exported = profile.as_dict()
        exported["permissions"]["submit_allowed"] = True
        exported["wire_bounds"]["actions"]["trade_submit"] = 100
        self.assertEqual(profile.as_dict(), before)

    def test_action_catalog_is_fixed_and_ordinary_rpc_budget_is_fourteen(self):
        self.assertEqual(set(wire.WIRE_ACTIONS), set(wire.PROTOCOL_LIMITS))
        self.assertEqual(wire.WIRE_ACTIONS["trade_submit"], ("trade", 2202))
        self.assertEqual(wire.WIRE_ACTIONS["quote_init"], ("quote", 1001))
        self.assertEqual(wire.WIRE_ACTIONS["trade_init"], ("trade", 1001))
        total = sum(limit for name, limit in wire.PROTOCOL_LIMITS.items()
                    if wire.WIRE_ACTIONS[name][1] not in (None, 1001))
        self.assertEqual(total, 14)
        with self.assertRaises(TypeError):
            wire.PROTOCOL_LIMITS["trade_submit"] = 2
        with self.assertRaises(TypeError):
            wire.WIRE_ACTIONS["trade_submit"] = ("quote", 2202)

    def test_protocol_policy_is_fixed_test_only_and_cannot_be_promoted(self):
        value = wire.prepare_wire_profile(**self.args).as_dict()
        self.assertEqual(value["protocol_policy"], {
            "format": "PROTOBUF", "proto_fmt": 0, "proto_ver": 0, "header_bytes": 44,
            "encryption_policy": "PLAINTEXT_OFFLINE_CODEC_TEST", "recv_notify": False,
            "production_transport_available": False})
        self.assertNotIn("client_id", value["protocol_policy"])
        for change in ({"proto_fmt": 1}, {"proto_ver": 1}, {"header_bytes": 45},
                       {"recv_notify": True}, {"production_transport_available": True},
                       {"encryption_policy": "PRODUCTION_PLAINTEXT"}, {"client_id": "from-environment"}):
            altered = deepcopy(value)
            altered["protocol_policy"].update(change)
            with self.subTest(change=change), self.assertRaises(wire.WireProfileError):
                validate(seal(altered), self.args)

    def test_every_budget_must_be_explicit_without_copying_v1_calls(self):
        for key in wire.WIRE_BOUND_FIELDS:
            with self.subTest(missing=key):
                args = deepcopy(self.args)
                del args["wire_bounds"][key]
                with self.assertRaises(wire.WireProfileError):
                    wire.prepare_wire_profile(**args)
        args = dict(self.args, wire_bounds=deepcopy(self.args["base_plan"]["bounds"]))
        with self.assertRaises(wire.WireProfileError):
            wire.prepare_wire_profile(**args)
        self.assertEqual(self.args["base_plan"]["bounds"]["calls"]["connect"], 1)
        value = wire.prepare_wire_profile(**self.args).as_dict()
        self.assertEqual(value["wire_bounds"]["actions"]["quote_connect"], 1)
        self.assertEqual(value["wire_bounds"]["actions"]["trade_connect"], 1)

    def test_zero_actions_are_retained_and_report_missing_budget_stages(self):
        self.args["wire_bounds"]["actions"] = {key: 0 for key in wire.WIRE_ACTIONS}
        value = wire.prepare_wire_profile(**self.args).as_dict()
        self.assertEqual(value["wire_bounds"]["actions"], self.args["wire_bounds"]["actions"])
        for stage in value["budget_readiness"]["stages"].values():
            self.assertFalse(stage["budget_complete"])
            self.assertTrue(stage["missing_actions"])
        self.assertFalse(value["budget_readiness"]["execution_ready"])

    def test_connection_and_handshake_must_be_paired_but_missing_preflight_is_a_gap(self):
        for channel in ("quote", "trade"):
            args = deepcopy(self.args)
            args["wire_bounds"]["actions"][channel + "_connect"] = 0
            with self.assertRaisesRegex(wire.WireProfileError, "connection_handshake"):
                wire.prepare_wire_profile(**args)
        self.args["wire_bounds"]["actions"].update(quote_connect=0, quote_init=0, trade_funds=0)
        value = wire.prepare_wire_profile(**self.args).as_dict()
        missing = value["budget_readiness"]["stages"]["submit"]["missing_actions"]
        self.assertIn("quote_connect", missing)
        self.assertIn("trade_funds", missing)
        self.assertFalse(value["budget_readiness"]["stages"]["submit"]["budget_complete"])

    def test_action_bool_unknown_missing_and_extra_protocols_are_rejected(self):
        for key, replacement in [("trade_submit", True), ("trade_observe", 6),
                                 ("trade_observe", 1.0), ("trade_submit", -1),
                                 *[(key, 1) for key, limit in wire.PROTOCOL_LIMITS.items() if limit == 0]]:
            with self.subTest(key=key, value=replacement):
                args = deepcopy(self.args)
                args["wire_bounds"]["actions"][key] = replacement
                with self.assertRaises(wire.WireProfileError):
                    wire.prepare_wire_profile(**args)
        for mutation in (lambda a: a.pop("trade_fees"), lambda a: a.update(extra_rpc=1)):
            args = deepcopy(self.args)
            mutation(args["wire_bounds"]["actions"])
            with self.assertRaises(wire.WireProfileError):
                wire.prepare_wire_profile(**args)

    def test_all_integer_bounds_reject_bool_and_zero(self):
        keys = wire.WIRE_BOUND_FIELDS - {"valid_until", "endpoint", "actions", "max_total_fees"}
        for key in keys:
            for value in (True, False, 0, 1.5, "15"):
                with self.subTest(key=key, value=value):
                    args = deepcopy(self.args)
                    args["wire_bounds"][key] = value
                    with self.assertRaises(wire.WireProfileError):
                        wire.prepare_wire_profile(**args)

    def test_time_and_byte_limits_have_finite_caps_and_reserve_summary_space(self):
        cases = {"wall_timeout_seconds": 181, "connect_timeout_seconds": 16,
                 "handshake_timeout_seconds": 16, "rpc_timeout_seconds": 16,
                 "cleanup_timeout_seconds": 6, "max_frame_bytes": 65537,
                 "max_wire_bytes": 98305, "max_output_bytes": 131073,
                 "reserved_final_output_bytes": 16383, "max_observation_records": 51,
                 "max_evidence_age_seconds": 31}
        for key, value in cases.items():
            with self.subTest(key=key):
                args = deepcopy(self.args)
                args["wire_bounds"][key] = value
                with self.assertRaises(wire.WireProfileError):
                    wire.prepare_wire_profile(**args)
        for updates in ({"max_wire_bytes": 100}, {"max_output_bytes": 98304},
                        {"wall_timeout_seconds": 10}, {"reserved_final_output_bytes": 131072}):
            args = deepcopy(self.args)
            args["wire_bounds"].update(updates)
            with self.assertRaises(wire.WireProfileError):
                wire.prepare_wire_profile(**args)

    def test_fee_is_an_explicit_decimal_ceiling_never_known_actual_fee(self):
        for value in ("0", "0.00", "1.23456789", "2.00"):
            self.args["wire_bounds"]["max_total_fees"] = value
            profile = wire.prepare_wire_profile(**self.args).as_dict()
            self.assertEqual(profile["wire_bounds"]["max_total_fees"], value)
            self.assertIsNone(profile["wire_contract"]["actual_fees"])
            self.assertIsNone(profile["wire_contract"]["price_step"])
        for value in (0, False, 1.5, "", "-1", "NaN", "1e0", "01", "1.123456789", "2.00000001"):
            with self.subTest(value=value):
                self.args["wire_bounds"]["max_total_fees"] = value
                with self.assertRaises(wire.WireProfileError):
                    wire.prepare_wire_profile(**self.args)

    def test_wire_expiry_narrows_base_and_keeps_aware_original_representation(self):
        raw = "2026-10-30T16:10:00+08:00"
        self.args["wire_bounds"]["valid_until"] = raw
        self.assertEqual(wire.prepare_wire_profile(**self.args).as_dict()["wire_bounds"]["valid_until"], raw)
        for expiry in ((NOW + timedelta(minutes=16)).isoformat(), (NOW + timedelta(seconds=184)).isoformat(),
                       NOW.isoformat(), "2026-10-30T08:10:00", "not-a-date"):
            with self.subTest(expiry=expiry):
                self.args["wire_bounds"]["valid_until"] = expiry
                with self.assertRaises(wire.WireProfileError):
                    wire.prepare_wire_profile(**self.args)
        with self.assertRaises(wire.WireProfileError):
            wire.prepare_wire_profile(**dict(fixture(), now=NOW.replace(tzinfo=None)))

    def test_endpoint_must_match_the_original_literal_local_endpoint(self):
        for endpoint in ({"host": "localhost", "port": 11111}, {"host": "127.0.0.1", "port": 11112},
                         {"host": "127.0.0.1", "port": True}, {"host": "127.0.0.1", "port": "11111"},
                         {"host": "127.0.0.1", "port": 11111, "timeout": 15}):
            with self.subTest(endpoint=endpoint):
                self.args["wire_bounds"]["endpoint"] = endpoint
                with self.assertRaises(wire.WireProfileError):
                    wire.prepare_wire_profile(**self.args)

    def test_exact_pinned_sdk_is_required_even_when_v1_accepts_other_package_identities(self):
        for current_runtime in (runtime(sdk=False), runtime(version="10.7.6709"), runtime(wheel_hash="2" * 64)):
            args = fixture(runtime_value=current_runtime)
            with self.assertRaisesRegex(wire.WireProfileError, "pinned_sdk"):
                wire.prepare_wire_profile(**args)
        args = dict(self.args, runtime_identity=self.args["runtime_identity"].as_dict())
        with self.assertRaisesRegex(wire.WireProfileError, "trusted_runtime"):
            wire.prepare_wire_profile(**args)

    def test_v1_adapter_identity_never_establishes_wire_v2_or_journal_support(self):
        args = fixture(runtime_value=runtime(adapter=True))
        value = wire.prepare_wire_profile(**args).as_dict()
        self.assertIsNotNone(value["runtime"]["adapter"])
        self.assertEqual(value["capability_gaps"], ["WIRE_V2_ADAPTER_NOT_VERIFIED",
            "CROSS_WORKSPACE_JOURNAL_NOT_AVAILABLE", "SCOPED_AUTHORIZATION_NOT_PROVIDED"])
        self.assertTrue(value["wire_contract"]["v1_adapter_identity_is_not_v2_support"])
        self.assertFalse(value["budget_readiness"]["execution_ready"])

    def test_workspaces_do_not_split_account_money_or_original_intent_claim(self):
        first = wire.prepare_wire_profile(**self.args).as_dict()
        args = dict(self.args, workspace_context="8" * 64)
        second = wire.prepare_wire_profile(**args).as_dict()
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(first["deduplication"], second["deduplication"])
        self.assertEqual(first["research"]["owner_scope_id"], second["research"]["owner_scope_id"])
        self.assertEqual(first["wire_contract"]["account_scope"], "PROVIDER_MODE_ACCOUNT_ACROSS_WORKSPACES")
        with self.assertRaises(wire.WireProfileError):
            validate(first, args)
        for value in (True, "x", "a" * 24, "A" * 64):
            with self.assertRaises(wire.WireProfileError):
                wire.prepare_wire_profile(**dict(self.args, workspace_context=value))

    def test_simulate_and_real_are_distinct_scopes_without_mode_fallback(self):
        sim = wire.prepare_wire_profile(**self.args).as_dict()
        real_args = fixture(REAL)
        real = wire.prepare_wire_profile(**real_args).as_dict()
        self.assertEqual((sim["sdk_environment"], real["sdk_environment"]), ("SIMULATE", "REAL"))
        self.assertNotEqual(sim["contract_id"], real["contract_id"])
        self.assertNotEqual(sim["deduplication"]["account_scope_id"], real["deduplication"]["account_scope_id"])
        self.assertFalse(real["permissions"]["automatic_mode_fallback"])
        with self.assertRaises(wire.WireProfileError):
            validate(sim, real_args)

    def test_original_config_intent_research_control_and_package_changes_are_rejected(self):
        changes = [
            ("candidate_config", lambda value: value["config"].update(quantity=1)),
            ("candidate_intent", lambda value: value.update(request_id="different-intent-0001")),
            ("research_resolution", lambda value: value["binding"].update(task_version=2)),
            ("control", lambda value: value["control"].update(new_intents_blocked=True)),
            ("base_plan", lambda value: value["order"].update(asset_code="US.OTHER")),
        ]
        profile = wire.prepare_wire_profile(**self.args)
        for key, mutate in changes:
            with self.subTest(key=key):
                args = deepcopy(self.args)
                mutate(args[key])
                with self.assertRaises(wire.WireProfileError):
                    wire.prepare_wire_profile(**args)
                with self.assertRaises(wire.WireProfileError):
                    validate(profile, args)
        changed_runtime = runtime(adapter=True)
        with self.assertRaisesRegex(wire.WireProfileError, "identity_changed"):
            validate(profile, dict(self.args, runtime_identity=changed_runtime))

    def test_serialized_profile_requires_exact_recomputation_even_after_resealing(self):
        value = wire.prepare_wire_profile(**self.args).as_dict()
        self.assertEqual(validate(value, self.args).as_dict(), value)
        mutations = [lambda v: v.update(status="READY"), lambda v: v.update(base_plan_id="0" * 64),
                     lambda v: v["permissions"].update(submit_allowed=True),
                     lambda v: v["capability_gaps"].clear(),
                     lambda v: v["deduplication"].update(account_scope_id="0" * 64),
                     lambda v: v.update(execution_authorized=True)]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                changed = deepcopy(value)
                mutate(changed)
                with self.assertRaises(wire.WireProfileError):
                    validate(seal(changed), self.args)

    def test_explicit_expected_id_rejects_resealed_legal_budget_replacement(self):
        first = wire.prepare_wire_profile(**self.args)
        trusted_id = first.as_dict()["id"]
        modified = deepcopy(self.args)
        modified["wire_bounds"]["max_total_fees"] = "0.50"
        second = wire.prepare_wire_profile(**modified)
        self.assertNotEqual(trusted_id, second.as_dict()["id"])
        for supplied in (second, second.as_dict()):
            with self.assertRaisesRegex(wire.WireProfileError, "expected_profile_id_mismatch"):
                validate(supplied, self.args, expected_profile_id=trusted_id)
        self.assertEqual(validate(first, self.args, expected_profile_id=trusted_id).as_dict(), first.as_dict())
        arguments = {key: value for key, value in self.args.items() if key != "wire_bounds"}
        with self.assertRaises(TypeError):
            wire.validate_wire_profile(first, **arguments)
        with self.assertRaises(wire.WireProfileError):
            wire.validate_wire_profile(first, expected_profile_id=True, **arguments)

    def test_validation_rechecks_current_lifetime_and_clock_without_rewriting_creation(self):
        value = wire.prepare_wire_profile(**self.args)
        valid = validate(value, self.args, now=NOW + timedelta(minutes=1)).as_dict()
        self.assertEqual(valid, value.as_dict())
        for now in (NOW - timedelta(seconds=1), NOW + timedelta(minutes=8), NOW + timedelta(minutes=16)):
            with self.subTest(now=now), self.assertRaises(wire.WireProfileError):
                validate(value, self.args, now=now)

    def test_synthetic_is_never_upgraded_by_general_evidence_or_new_wire_budget(self):
        value = wire.prepare_wire_profile(**self.args).as_dict()
        self.assertTrue(value["research_eligibility"]["offline_only"])
        self.assertFalse(value["research_eligibility"]["external_research_eligible"])
        self.assertTrue(value["research_eligibility"]["admission_cannot_override_synthetic"])
        changed = deepcopy(value)
        changed["research_eligibility"].update(offline_only=False, external_research_eligible=True)
        changed["missing_evidence"] = []
        with self.assertRaises(wire.WireProfileError):
            validate(seal(changed), self.args)
        args = deepcopy(self.args)
        args["research_resolution"]["recorded_evidence_classification"]["decision"].update(external_research_eligible=True)
        args["research_resolution"]["recorded_evidence_classification"] = seal(args["research_resolution"]["recorded_evidence_classification"])
        with self.assertRaises(wire.WireProfileError):
            wire.prepare_wire_profile(**args)

    def test_core_source_hash_and_unknown_classification_are_preserved_without_fabrication(self):
        reference = {"kind": "core_run", "id": "a" * 24}
        resolution = {key: deepcopy(RESOLUTION[key]) for key in ("binding", "owner_id", "display", "assumptions")}
        resolution["binding"].update(engine_id="research.accepted-equity", source_hash="d" * 64)
        resolution["owner_id"] = "task:" + resolution["binding"]["task_id"]
        args = fixture(resolution=resolution, reference=reference)
        value = wire.prepare_wire_profile(**args).as_dict()
        self.assertEqual(value["research"]["recorded_source"], {"kind": "CORE_SAVED_CONTENT_HASH", "content_sha256": "d" * 64})
        self.assertIsNone(value["research_eligibility"]["external_research_eligible"])
        self.assertEqual(value["research_eligibility"]["status"], "UNKNOWN")
        self.assertIsNone(value["wire_contract"]["actual_fees"])
        self.assertTrue(value["wire_contract"]["query_roundtrip_is_not_market_source_time"])

    def test_original_v1_and_all_input_bytes_remain_unchanged(self):
        serializable = {key: value for key, value in self.args.items() if key not in ("runtime_identity", "now")}
        before = canonical(serializable)
        runtime_before = self.args["runtime_identity"].as_dict()
        with patch.object(original, "validate_acceptance_plan", wraps=original.validate_acceptance_plan) as verifier:
            value = wire.prepare_wire_profile(**self.args)
            validate(value, self.args)
            self.assertEqual(verifier.call_count, 3)
        self.assertEqual(canonical(serializable), before)
        self.assertEqual(self.args["runtime_identity"].as_dict(), runtime_before)
        original.validate_acceptance_plan(self.args["base_plan"], **{
            key: self.args[key] for key in ("candidate_config", "candidate_intent", "research_resolution",
                                          "runtime_identity", "control", "now")})
        self.assertEqual(self.args["base_plan"]["schema_version"], "hakimi-broker-execution-plan-v1")
        self.assertNotIn("wire_bounds", self.args["base_plan"])


if __name__ == "__main__":
    unittest.main()
