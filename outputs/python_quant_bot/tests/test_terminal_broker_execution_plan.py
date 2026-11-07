"""Offline plan contract only: fictional US declarations, no SDK or external IO.

Package bytes below are explicitly synthetic capability fixtures, not a claim
that the application currently ships or has tested a broker adapter.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from exchange_terminal.services import terminal_broker_candidate_service as candidate
from exchange_terminal.services import terminal_broker_execution_plan as plan_module
from exchange_terminal.services import terminal_saved_results as saved_results


SIM, REAL = "OFFICIAL_SIMULATION", "LIVE_CANDIDATE"
NOW = datetime(2026, 10, 30, 8, tzinfo=timezone.utc)
REF = {"kind": "terminal_run", "id": "a" * 64}
RESOLUTION = {
    "binding": {"schema_version": "hakimi-offline-research-binding-v1", "status": "COMPLETED",
                "engine_id": "terminal.native-qa", "strategy_id": "dual_ma", "strategy_params": {"fast": 5, "slow": 20},
                "task_id": "b" * 64, "task_version": 1, "input_id": "c" * 64,
                "report_id": REF["id"], "report_hash": REF["id"], "security_id": "FICTIONAL:TSLA",
                "risk": {"stop_loss_pct": 8}, "costs": {"fee_rate": 0.001, "slippage_bps": 5}},
    "display": {"security_id": "FICTIONAL:TSLA", "symbol": "TSLA", "currency": "USD", "asset_class": "US_EQUITY"},
    "assumptions": {"fill_model": "NEXT_BAR_OPEN", "quantity_policy": "WHOLE_SHARES"},
    "owner_id": "family:" + "e" * 32,
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def seal(value):
    body = {k: deepcopy(v) for k, v in value.items() if k != "id"}
    return {**body, "id": sha256(canonical(body)).hexdigest()}


def with_recorded_source(resolution):
    result = deepcopy(resolution)
    binding = result["binding"]
    anchors = {"reference": deepcopy(REF), **{key: binding[key] for key in ("task_id", "input_id", "report_hash", "engine_id")}}
    files = {name: str(index) * 64 for index, name in enumerate(
        ("backtest_engine.py", "strategy_signals.py", "market_calendar.py", "indicator_math.py"), 1)}
    result["recorded_source_identity"] = seal({"schema_version": saved_results.RECORDED_SOURCE_SCHEMA, **anchors,
        "source_files": files, "fingerprint": "d" * 64, "digest_rule": saved_results.SOURCE_DIGEST_RULE,
        "content_sha256": sha256(canonical(files)).hexdigest()})
    facts = [{"path": "report.input_summary.meta.evidence_kind", "value": "SYNTHETIC_TEST"}]
    result["recorded_evidence_classification"] = seal({"schema_version": saved_results.RECORDED_EVIDENCE_SCHEMA, **anchors,
        "facts": facts, "decision": saved_results._recorded_evidence_decision(facts)})
    return result


RESOLUTION = with_recorded_source(RESOLUTION)


def config():
    return {"account_id": "900000000000001", "market": "US", "asset_class": "EQUITY", "asset_code": "US.TSLA",
            "currency": "USD", "max_quantity": 4, "max_notional": "100.00", "side": "BUY", "quantity": 3,
            "limit_price": "20.00000001", "time_in_force": "DAY", "expires_at": (NOW + timedelta(hours=1)).isoformat()}


def bounds():
    return {"valid_until": (NOW + timedelta(minutes=15)).isoformat(), "calls": dict(plan_module.CALL_LIMITS),
            "wall_timeout_seconds": 180, "call_timeout_seconds": 15, "cleanup_timeout_seconds": 5,
            "max_output_bytes": 128 * 1024, "max_observation_records": 50, "max_evidence_age_seconds": 30,
            "max_total_fees": "2.00", "endpoint": {"host": "127.0.0.1", "port": 11111}}


def control(mode=SIM):
    return {"mode": mode, "control": {"state": "OFFLINE_PREPARATION_ALLOWED", "new_intents_blocked": False,
            "revision": 0, "latest_control_receipt_id": None, "latest_stop_receipt_id": None,
            "resume_allowed": False, "permissions": dict(candidate.PERMISSIONS)}}


def records(mode=SIM, terms=None, resolution=None, reference=None):
    resolution = deepcopy(resolution or RESOLUTION)
    terms = deepcopy(terms or config())
    research = candidate._project_research(resolution, reference or REF)
    saved = seal({"schema_version": candidate.SCHEMA, "kind": "configs", "mode": mode, "config": terms,
                  "research": research, "research_sha256": sha256(canonical(research)).hexdigest()})
    security, _, _ = candidate._security_binding(terms, research)
    intent = seal({"schema_version": candidate.SCHEMA, "kind": "intents", "mode": mode, "config_id": saved["id"],
                   "request_id": "fictional-intent-0001", "research_sha256": saved["research_sha256"], "terms": terms,
                   "security_binding": security, "status": "UNSENT_OFFLINE_PREVIEW", "permissions": dict(candidate.PERMISSIONS)})
    return saved, intent


def runtime_inputs(mode=SIM, adapter=True, sdk=True):
    entry = "components/terminal/exchange_terminal/adapters/fixture_" + ("simulate" if mode == SIM else "real") + ".py"
    descriptor_path = "components/terminal/fixture-capability.json"
    descriptor = {
        "schema_version": plan_module.ADAPTER_SCHEMA, "adapter_id": "FICTIONAL_OFFLINE_FIXTURE",
        "mode": mode, "sdk_environment": plan_module.MODE_CONTRACTS[mode][0],
        "contract_id": plan_module.MODE_CONTRACTS[mode][1], "sdk_name": "futu-api", "sdk_version": "10.7.6708",
        "market": "US", "asset_class": "EQUITY", "currency": "USD", "security_mapping": "EXACT_SAVED_US_SYMBOL_V1",
        "quantity_policy": "WHOLE_SHARES", "order_type": "LIMIT", "time_in_force": "DAY", "sides": ["BUY", "SELL"],
        "entrypoint": {"path": entry, "function": "build_scoped_transport"},
        "source_files": {entry: sha256(b"# Fictional source; never imported or executed.\n").hexdigest()},
    }
    files = {"components/terminal/fixture.txt": sha256(b"synthetic").hexdigest()}
    if sdk:
        files.update({plan_module.SDK_ROOT + "futu/__init__.py": sha256(b"# synthetic SDK bytes").hexdigest(),
                      plan_module.SDK_ROOT + "futu_api-10.7.6708.dist-info/METADATA": sha256(b"synthetic SDK metadata").hexdigest()})
    if adapter:
        files.update(descriptor["source_files"])
        files[descriptor_path] = sha256(canonical(descriptor)).hexdigest()
    manifest = {"schema_version": "hakimi-original-terminal-v1", "bundle_id": "f" * 64, "version": "0.0.0.synthetic",
                "source_provenance": {"development_probe": False, "git": {"commit": "1" * 40, "status": "CLEAN"}},
                "files": files, "dependency_wheels": [{"name": "futu-api", "version": "10.7.6708",
                    "filename": "futu_api-10.7.6708-py3-none-any.whl", "sha256": "2" * 64}] if sdk else []}
    return {"manifest_bytes": canonical(manifest), "expected_manifest_sha256": sha256(canonical(manifest)).hexdigest(),
            "observed_file_sha256": deepcopy(files), "mode": mode,
            "adapter_path": descriptor_path if adapter else None,
            "adapter_descriptor_bytes": canonical(descriptor) if adapter else None}


def change_manifest(arguments, change):
    manifest = json.loads(arguments["manifest_bytes"])
    change(manifest)
    arguments["manifest_bytes"] = canonical(manifest)
    arguments["expected_manifest_sha256"] = sha256(arguments["manifest_bytes"]).hexdigest()


def change_descriptor(arguments, change):
    descriptor = json.loads(arguments["adapter_descriptor_bytes"])
    change(descriptor)
    arguments["adapter_descriptor_bytes"] = canonical(descriptor)
    changed_hash = sha256(arguments["adapter_descriptor_bytes"]).hexdigest()
    change_manifest(arguments, lambda m: m["files"].update({arguments["adapter_path"]: changed_hash}))
    arguments["observed_file_sha256"][arguments["adapter_path"]] = changed_hash


class ExecutionPlanTests(unittest.TestCase):
    def setUp(self):
        for target in ("socket.socket.connect", "subprocess.Popen"):
            blocker = patch(target, side_effect=AssertionError("No external action in plan tests"))
            blocker.start(); self.addCleanup(blocker.stop)
        self.saved, self.intent = records()
        self.resolution = deepcopy(RESOLUTION)
        self.runtime = plan_module.verify_runtime_identity(**runtime_inputs())
        self.control, self.bounds = control(), bounds()

    def arguments(self, **changes):
        result = {"candidate_config": self.saved, "candidate_intent": self.intent, "research_resolution": self.resolution,
                  "runtime_identity": self.runtime, "control": self.control, "bounds": self.bounds, "now": NOW}
        result.update(changes)
        return result

    def prepare(self, **changes):
        return plan_module.prepare_acceptance_plan(**self.arguments(**changes))

    def validate(self, plan, **changes):
        args = self.arguments(**changes); args.pop("bounds")
        return plan_module.validate_acceptance_plan(plan, **args)

    def test_actual_candidate_service_records_are_consumed_without_changes_or_io(self):
        with tempfile.TemporaryDirectory(prefix="new-fictional-execution-plan-") as directory:
            root = Path(directory) / "new-candidate"
            service = candidate.BrokerCandidateService(root, research_resolver=lambda _: deepcopy(RESOLUTION), clock=lambda: NOW)
            saved_result = service.save({"mode": SIM, "request_id": "fictional-save-0001", "config": config(), "research_reference": REF})
            intent_result = service.prepare_intent({"mode": SIM, "request_id": "fictional-intent-0001", "config_id": saved_result["config_id"]})
            self.saved = service._saved(SIM, saved_result["config_id"])
            self.intent = intent_result["intent"]
            self.control = {"mode": SIM, "control": service.status()["modes"][0]["control"]}
            inventory = lambda: {str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mtime_ns) for p in root.rglob("*") if p.is_file()}
            before = inventory()
            with patch("builtins.open", side_effect=AssertionError("Plan must not open files")):
                value = self.prepare()
                result = self.validate(value)
            self.assertEqual(before, inventory())
            self.assertEqual(value["candidate_intent"], intent_result["intent"])
            self.assertEqual(result["journal_key"], "broker-execution-v1/official-simulation/" + value["id"])
            self.assertFalse(any(result["permissions"].values()))

    def test_complete_plan_freezes_exact_scope_and_never_grants_permission(self):
        before = canonical({"saved": self.saved, "intent": self.intent, "resolution": self.resolution,
                            "control": self.control, "bounds": self.bounds})
        plan = self.prepare()
        self.assertEqual(plan, self.prepare())
        self.assertEqual(plan["order"]["asset_code"], "US.TSLA")
        self.assertEqual(plan["order"]["order_notional"], "60.00000003")
        self.assertEqual(plan["order"]["maximum_cash_debit"], "62.00000003")
        self.assertIsNone(plan["order"]["actual_fees"])
        self.assertEqual(plan["status"], "OFFLINE_ONLY_SYNTHETIC_RESEARCH")
        self.assertFalse(plan["research_eligibility"]["external_research_eligible"])
        self.assertTrue(plan["research_eligibility"]["admission_cannot_override_synthetic"])
        self.assertEqual(plan["bounds"], self.bounds)
        self.assertEqual(plan["runtime"], self.runtime.as_dict())
        self.assertEqual(plan["research"]["resolution"]["binding"], self.resolution["binding"])
        self.assertTrue(all(row["status"] == "NOT_PROVIDED" and row["evidence_ref"] is None for row in plan["missing_evidence"]))
        self.assertFalse(any(plan["permissions"].values()))
        self.assertEqual(before, canonical({"saved": self.saved, "intent": self.intent, "resolution": self.resolution,
                                          "control": self.control, "bounds": self.bounds}))

    def test_any_exact_current_us_symbol_is_supported_without_amd_restriction(self):
        for symbol in ("AAPL", "BRK.B", "NDAQ", "QADEMO"):
            with self.subTest(symbol=symbol):
                resolution = deepcopy(RESOLUTION)
                resolution["display"].update(symbol=symbol, security_id="FICTIONAL:" + symbol)
                resolution["binding"]["security_id"] = "FICTIONAL:" + symbol
                terms = config(); terms["asset_code"] = "US." + symbol
                saved, intent = records(terms=terms, resolution=resolution)
                plan = self.prepare(candidate_config=saved, candidate_intent=intent, research_resolution=resolution)
                self.assertEqual(plan["order"]["asset_code"], "US." + symbol)
                self.assertIn("BROKER_SECURITY_RULES", [row["code"] for row in plan["missing_evidence"]])

    def test_sell_needs_owner_holdings_and_never_assumes_short_or_cash_proceeds(self):
        terms = config(); terms["side"] = "SELL"
        saved, intent = records(terms=terms)
        plan = self.prepare(candidate_config=saved, candidate_intent=intent)
        self.assertIsNone(plan["order"]["maximum_cash_debit"])
        self.assertIn("BROKER_OWNER_HOLDINGS", [row["code"] for row in plan["missing_evidence"]])
        self.assertFalse(plan["worker_contract"]["short_selling"])

    def test_simulate_real_contracts_cannot_be_swapped_or_automatically_downgraded(self):
        saved, intent = records(mode=REAL)
        with self.assertRaisesRegex(plan_module.PlanError, "runtime_mode_mismatch"):
            self.prepare(candidate_config=saved, candidate_intent=intent, control=control(REAL))
        real_runtime = plan_module.verify_runtime_identity(**runtime_inputs(mode=REAL))
        plan = self.prepare(candidate_config=saved, candidate_intent=intent, runtime_identity=real_runtime, control=control(REAL))
        self.assertEqual(plan["sdk_environment"], "REAL")
        self.assertNotEqual(plan["contract_id"], self.prepare()["contract_id"])
        self.assertNotEqual(plan["research"]["owner_scope_id"], self.prepare()["research"]["owner_scope_id"])
        self.assertIn("REAL_FUNDS_AUTHORIZATION", [row["code"] for row in plan["missing_evidence"]])
        self.assertFalse(any(plan["permissions"].values()))
        args = runtime_inputs(mode=REAL)
        change_descriptor(args, lambda d: d.update(sdk_environment="SIMULATE"))
        with self.assertRaisesRegex(plan_module.PlanError, "adapter_mode_or_capability_mismatch"):
            plan_module.verify_runtime_identity(**args)

    def test_sdk_and_adapter_absence_remain_gaps_not_installed_or_authorized(self):
        for sdk in (False, True):
            with self.subTest(sdk=sdk):
                runtime = plan_module.verify_runtime_identity(**runtime_inputs(sdk=sdk, adapter=False))
                plan = self.prepare(runtime_identity=runtime)
                self.assertEqual(plan["status"], "BLOCKED_CAPABILITY")
                self.assertIn("APPLICATION_ADAPTER_NOT_PACKAGED", plan["capability_gaps"])
                self.assertEqual("SDK_NOT_PACKAGED" in plan["capability_gaps"], not sdk)
                self.assertIsNone(plan["runtime"]["adapter"])
        with self.assertRaisesRegex(plan_module.PlanError, "trusted_runtime_identity_required"):
            self.prepare(runtime_identity=self.runtime.as_dict())

    def test_runtime_identity_checks_actual_manifest_sdk_and_adapter_hashes(self):
        for mutation, error in (
            (lambda a: a.update(expected_manifest_sha256="0" * 64), "manifest_hash_mismatch"),
            (lambda a: a["observed_file_sha256"].update({plan_module.SDK_ROOT + "futu/__init__.py": "0" * 64}), "installed_file_hash_mismatch"),
            (lambda a: a.update(adapter_descriptor_bytes=a["adapter_descriptor_bytes"] + b" "), "descriptor_hash_mismatch"),
            (lambda a: a["observed_file_sha256"].pop(json.loads(a["adapter_descriptor_bytes"])["entrypoint"]["path"]), "installed_file_hash_mismatch"),
            (lambda a: change_manifest(a, lambda m: m["source_provenance"]["git"].update(status="DIRTY")), "clean_package_source_required"),
            (lambda a: change_descriptor(a, lambda d: d.update(sdk_version="10.12")), "capability_mismatch"),
            (lambda a: change_descriptor(a, lambda d: d.update(side="BUY")), "fields_invalid"),
        ):
            with self.subTest(error=error):
                args = runtime_inputs(); mutation(args)
                with self.assertRaisesRegex(plan_module.PlanError, error):
                    plan_module.verify_runtime_identity(**args)

    def test_package_paths_and_old_tools_cannot_be_used_as_new_adapter(self):
        for path in ("../tools/futu_simulation_adapter.py", "C:/old/profile.py", "tools/futu_simulation_adapter.py"):
            args = runtime_inputs()
            change_descriptor(args, lambda d: d["entrypoint"].update(path=path))
            with self.subTest(path=path), self.assertRaises(plan_module.PlanError):
                plan_module.verify_runtime_identity(**args)
        args = runtime_inputs()
        change_manifest(args, lambda m: m["files"].update({"COMPONENTS/terminal/fixture.txt": "1" * 64}))
        with self.assertRaisesRegex(plan_module.PlanError, "case_aliased"):
            plan_module.verify_runtime_identity(**args)

    def test_candidate_original_seals_terms_and_no_authorization_assertion(self):
        altered = deepcopy(self.saved); altered["config"]["quantity"] = 4
        with self.assertRaisesRegex(plan_module.PlanError, "sealed_identity_mismatch"):
            self.prepare(candidate_config=altered)
        with self.assertRaisesRegex(plan_module.PlanError, "candidate_intent_identity_mismatch"):
            self.prepare(candidate_config=seal(altered))
        altered = deepcopy(self.intent); altered["terms"]["side"] = "SELL"
        with self.assertRaisesRegex(plan_module.PlanError, "intent_terms_mismatch"):
            self.prepare(candidate_intent=seal(altered))
        altered = deepcopy(self.intent); altered["permissions"]["submit_allowed"] = True
        with self.assertRaisesRegex(plan_module.PlanError, "unsent_candidate_required"):
            self.prepare(candidate_intent=seal(altered))
        altered = deepcopy(self.saved); altered["user_authorized"] = True
        with self.assertRaisesRegex(plan_module.PlanError, "fields_invalid"):
            self.prepare(candidate_config=seal(altered))

    def test_full_research_identity_and_security_must_match_current_resolution(self):
        cases = [("binding", "strategy_params", {"fast": 6, "slow": 20}), ("binding", "source_hash", "9" * 64),
                 ("binding", "task_id", "8" * 64), ("binding", "input_id", "7" * 64),
                 ("binding", "engine_id", "different-engine"), ("binding", "risk", {"stop_loss_pct": 3}),
                 ("binding", "costs", {"fee_rate": 0}), ("binding", "report_id", "6" * 64),
                 ("display", "symbol", "AMD"), ("binding", "security_id", "OTHER")]
        for group, field, value in cases:
            with self.subTest(field=field):
                resolution = deepcopy(RESOLUTION); resolution[group][field] = value
                with self.assertRaises(plan_module.PlanError):
                    self.prepare(research_resolution=resolution)
        resolution = deepcopy(RESOLUTION); resolution.pop("recorded_source_identity")
        saved, intent = records(resolution=resolution)
        with self.assertRaisesRegex(plan_module.PlanError, "recorded_native_source_identity_required"):
            self.prepare(candidate_config=saved, candidate_intent=intent, research_resolution=resolution)

    def test_native_recorded_sidecar_checks_every_anchor_digest_and_immutable_fingerprint(self):
        for key, value in (("reference", {"kind": "terminal_run", "id": "0" * 64}), ("task_id", "1" * 64),
                           ("input_id", "2" * 64), ("report_hash", "3" * 64), ("engine_id", "other.engine"),
                           ("digest_rule", "CURRENT_SOURCE"), ("content_sha256", "4" * 64), ("fingerprint", None)):
            with self.subTest(key=key):
                resolution = deepcopy(RESOLUTION); resolution["recorded_source_identity"][key] = value
                resolution["recorded_source_identity"] = seal(resolution["recorded_source_identity"])
                with self.assertRaises(plan_module.PlanError): self.prepare(research_resolution=resolution)
        existing = self.prepare()
        resolution = deepcopy(RESOLUTION); resolution["recorded_source_identity"]["fingerprint"] = "5" * 64
        resolution["recorded_source_identity"] = seal(resolution["recorded_source_identity"])
        with self.assertRaisesRegex(plan_module.PlanError, "identity_changed"):
            self.validate(existing, research_resolution=resolution)

    def test_core_retains_original_source_hash_and_missing_classification_is_unknown(self):
        reference = {"kind": "core_run", "id": "a" * 24}
        resolution = {key: deepcopy(RESOLUTION[key]) for key in ("binding", "owner_id", "display", "assumptions")}
        resolution["binding"].update(engine_id="research.accepted-equity", source_hash="d" * 64)
        resolution["owner_id"] = "task:" + resolution["binding"]["task_id"]
        saved, intent = records(resolution=resolution, reference=reference)
        plan = self.prepare(candidate_config=saved, candidate_intent=intent, research_resolution=resolution)
        self.assertEqual(plan["research"]["recorded_source"], {"kind": "CORE_SAVED_CONTENT_HASH", "content_sha256": "d" * 64})
        self.assertEqual(plan["research_eligibility"]["status"], "UNKNOWN")
        self.assertIsNone(plan["research_eligibility"]["external_research_eligible"])
        self.assertTrue(plan["research_eligibility"]["external_admission_required"])

    def test_known_synthetic_cannot_be_promoted_by_resealing_generic_evidence_decision(self):
        for mode in (SIM, REAL):
            saved, intent = records(mode=mode)
            plan = self.prepare(candidate_config=saved, candidate_intent=intent, control=control(mode),
                                runtime_identity=plan_module.verify_runtime_identity(**runtime_inputs(mode=mode)))
            self.assertEqual(plan["status"], "OFFLINE_ONLY_SYNTHETIC_RESEARCH")
            self.assertFalse(plan["research_eligibility"]["external_research_eligible"])
        resolution = deepcopy(RESOLUTION)
        resolution["recorded_evidence_classification"]["decision"].update(status="ADMITTED", external_research_eligible=True, offline_only=False)
        resolution["recorded_evidence_classification"] = seal(resolution["recorded_evidence_classification"])
        with self.assertRaisesRegex(plan_module.PlanError, "evidence_decision_mismatch"):
            self.prepare(research_resolution=resolution)
        resolution = deepcopy(RESOLUTION)
        resolution["recorded_evidence_classification"]["reference"]["id"] = "0" * 64
        resolution["recorded_evidence_classification"] = seal(resolution["recorded_evidence_classification"])
        with self.assertRaisesRegex(plan_module.PlanError, "recorded_research_identity_mismatch"):
            self.prepare(research_resolution=resolution)

    def test_actual_native_resolver_opt_in_accepts_old_candidate_without_runner_or_source_fallback(self):
        from tests.test_terminal_saved_results import create_synthetic_native_saved_fixture
        fixture, task, report = create_synthetic_native_saved_fixture(self)
        reference = {"kind": "terminal_run", "id": report["id"]}
        resolver = lambda selected: saved_results.resolve_execution_research(fixture.service, selected)
        broker = candidate.BrokerCandidateService(fixture.root / "new-broker-candidates", research_resolver=resolver, clock=lambda: NOW)
        terms = config(); terms["asset_code"] = "US.SYNTH"
        saved = broker.save({"mode": SIM, "request_id": "native-qa-save-0001", "config": terms, "research_reference": reference})
        intent = broker.prepare_intent({"mode": SIM, "request_id": "native-qa-intent-0001", "config_id": saved["config_id"]})["intent"]
        original = broker._saved(SIM, saved["config_id"])
        self.assertNotIn("source_hash", original["research"]["binding"])
        inventory = lambda: {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in fixture.root.rglob("*") if p.is_file()}
        before = inventory()
        with patch("exchange_terminal.services.terminal_research._engine_source_identity", side_effect=AssertionError("No current code fallback")), \
             patch.object(fixture.service, "fingerprint", side_effect=AssertionError("No fingerprint recompute")):
            resolution = saved_results.resolve_execution_research(fixture.service, reference, include_recorded_source=True)
            self.assertEqual(candidate._project_research(resolution, reference), original["research"])
            plan = self.prepare(candidate_config=original, candidate_intent=intent, research_resolution=resolution)
            self.assertTrue(self.validate(plan, candidate_config=original, candidate_intent=intent, research_resolution=resolution)["identity_matches"])
        self.assertEqual(plan["research"]["recorded_source"]["record"]["source_files"], task["engine_source_identity"])
        self.assertEqual(plan["research_eligibility"]["status"], "SYNTHETIC_OFFLINE_ONLY")
        self.assertEqual(inventory(), before)
        fixture.runner.assert_not_called()

    def test_owner_is_trusted_family_or_immutable_task_and_scoped_to_account(self):
        first = self.prepare()
        resolution = deepcopy(RESOLUTION); resolution["owner_id"] = "task:" + resolution["binding"]["task_id"]
        fallback = self.prepare(research_resolution=resolution)
        self.assertNotEqual(first["research"]["owner_scope_id"], fallback["research"]["owner_scope_id"])
        resolution["owner_id"] = "my-client-selected-owner"
        with self.assertRaisesRegex(plan_module.PlanError, "verified_research_owner_required"):
            self.prepare(research_resolution=resolution)
        terms = config(); terms["account_id"] = "900000000000002"
        saved, intent = records(terms=terms)
        second = self.prepare(candidate_config=saved, candidate_intent=intent)
        self.assertNotEqual(first["research"]["owner_scope_id"], second["research"]["owner_scope_id"])

    def test_full_candidate_types_market_quantity_price_and_expiry_fail_closed(self):
        for field, value in (("quantity", True), ("quantity", 5), ("max_quantity", 0), ("max_notional", "1"),
                             ("account_id", 900000000000001), ("account_id", str(2**64)), ("limit_price", 20.0),
                             ("limit_price", "NaN"), ("limit_price", "0"), ("limit_price", "1.000000001"),
                             ("market", "HK"), ("currency", "HKD"), ("asset_code", "US.AMD"),
                             ("side", "SHORT"), ("time_in_force", "GTC"), ("expires_at", NOW.isoformat())):
            with self.subTest(field=field, value=value):
                terms = config(); terms[field] = value
                saved, intent = records(terms=terms)
                with self.assertRaises(plan_module.PlanError):
                    self.prepare(candidate_config=saved, candidate_intent=intent)
        for field in config():
            with self.subTest(missing=field):
                terms = config(); terms.pop(field)
                saved, intent = records(terms=terms)
                with self.assertRaises(plan_module.PlanError):
                    self.prepare(candidate_config=saved, candidate_intent=intent)

    def test_bounds_all_explicit_and_no_extra_calls_rounding_or_unbounded_output(self):
        for field, value in (("wall_timeout_seconds", 181), ("call_timeout_seconds", 31), ("cleanup_timeout_seconds", 6),
                             ("max_output_bytes", 131073), ("max_observation_records", 101), ("max_evidence_age_seconds", 61),
                             ("max_total_fees", 2.0), ("max_total_fees", "0.000000001"), ("valid_until", NOW.isoformat()),
                             ("valid_until", (NOW + timedelta(hours=2)).isoformat()),
                             ("endpoint", {"host": "remote.invalid", "port": 11111})):
            with self.subTest(field=field):
                changed = bounds(); changed[field] = value
                with self.assertRaises(plan_module.PlanError): self.prepare(bounds=changed)
        for action in plan_module.CALL_LIMITS:
            with self.subTest(action=action):
                changed = bounds(); changed["calls"][action] += 1
                with self.assertRaises(plan_module.PlanError): self.prepare(bounds=changed)
        for field in bounds():
            changed = bounds(); changed.pop(field)
            with self.subTest(missing=field), self.assertRaises(plan_module.PlanError): self.prepare(bounds=changed)
        changed = bounds(); changed["max_total_fees"] = "0"; changed["calls"]["cancel"] = 0
        plan = self.prepare(bounds=changed)
        self.assertIsNone(plan["order"]["actual_fees"])
        self.assertNotIn("cancel", plan["worker_contract"]["allowed_actions"])

    def test_revalidation_rejects_stop_resume_drift_source_change_owner_change_and_expiry(self):
        plan = self.prepare()
        self.assertTrue(self.validate(plan)["identity_matches"])
        stopped = control(); stopped["control"].update(state="STOPPED", new_intents_blocked=True, revision=1,
                                                      latest_control_receipt_id="3" * 64, latest_stop_receipt_id="3" * 64, resume_allowed=True)
        with self.assertRaisesRegex(plan_module.PlanError, "control_blocks"):
            self.validate(plan, control=stopped)
        resumed = control(); resumed["control"].update(revision=2, latest_control_receipt_id="4" * 64, latest_stop_receipt_id="3" * 64)
        with self.assertRaisesRegex(plan_module.PlanError, "plan_or_current_identity_changed"):
            self.validate(plan, control=resumed)
        renewed = self.prepare(control=resumed)
        self.assertNotEqual(renewed["id"], plan["id"])
        self.assertEqual(renewed["deduplication"], plan["deduplication"])
        args = runtime_inputs(); change_manifest(args, lambda m: m["source_provenance"]["git"].update(commit="5" * 40))
        with self.assertRaisesRegex(plan_module.PlanError, "plan_or_current_identity_changed"):
            self.validate(plan, runtime_identity=plan_module.verify_runtime_identity(**args))
        resolution = deepcopy(RESOLUTION); resolution["owner_id"] = "family:" + "6" * 32
        with self.assertRaisesRegex(plan_module.PlanError, "plan_or_current_identity_changed"):
            self.validate(plan, research_resolution=resolution)
        with self.assertRaises(plan_module.PlanError): self.validate(plan, now=NOW + timedelta(minutes=15))
        with self.assertRaisesRegex(plan_module.PlanError, "clock_before_plan"):
            self.validate(plan, now=NOW - timedelta(seconds=1))

    def test_plan_content_and_canonical_identity_cannot_drift_even_if_resealed(self):
        plan = self.prepare()
        for field in ("permissions", "worker_contract", "recovery_contract"):
            changed = deepcopy(plan); changed[field] = {}
            with self.subTest(field=field), self.assertRaisesRegex(plan_module.PlanError, "identity_changed"):
                self.validate(seal(changed))
        changed = deepcopy(plan); changed["id"] = "0" * 64
        with self.assertRaisesRegex(plan_module.PlanError, "identity_changed"): self.validate(changed)
        self.assertFalse(plan["recovery_contract"]["resubmit"])
        self.assertEqual(plan["recovery_contract"]["not_found"], "NOT_PROOF_OF_UNSENT")
        self.assertFalse(plan["recovery_contract"]["legacy_profile_or_journal_reuse"])
        self.assertEqual(plan["worker_contract"]["counts_scope"], "ENTIRE_PLAN_ACROSS_WORKERS_AND_RESTARTS")
        self.assertEqual(plan["worker_contract"]["outputs_scope"], "ALL_WORKER_OUTPUT_AND_RAW_EVIDENCE_BYTES")

    def test_new_plan_cannot_reset_original_intent_claim_and_accounts_are_independent(self):
        first = self.prepare()
        later = self.prepare(now=NOW + timedelta(seconds=1))
        self.assertNotEqual(first["id"], later["id"])
        self.assertEqual(first["deduplication"], later["deduplication"])
        self.assertTrue(later["deduplication"]["new_plan_must_not_reset_submit_claim"])
        terms = config(); terms["account_id"] = "900000000000002"
        saved, intent = records(terms=terms)
        other = self.prepare(candidate_config=saved, candidate_intent=intent)
        self.assertNotEqual(other["deduplication"]["account_scope_id"], first["deduplication"]["account_scope_id"])
        missing = {row["code"]: row for row in first["missing_evidence"]}
        self.assertEqual(missing["SDK_ADAPTER_COMPATIBILITY"]["required_before"], "BEFORE_CONNECTION")
        self.assertEqual(missing["OPEND_PROTOCOL_COMPATIBILITY"]["required_before"], "BEFORE_SUBMIT")

    def test_manifest_ambiguity_and_descriptor_unsupported_side_reject(self):
        args = runtime_inputs()
        change_manifest(args, lambda m: m.update(dependency_wheels=[]))
        with self.assertRaisesRegex(plan_module.PlanError, "sdk_files_without_dependency_identity"):
            plan_module.verify_runtime_identity(**args)
        args = runtime_inputs()
        change_manifest(args, lambda m: m["dependency_wheels"].append(deepcopy(m["dependency_wheels"][0])))
        with self.assertRaisesRegex(plan_module.PlanError, "ambiguous_sdk_dependency"):
            plan_module.verify_runtime_identity(**args)
        args = runtime_inputs()
        change_descriptor(args, lambda d: d.update(sides=["SELL"]))
        with self.assertRaisesRegex(plan_module.PlanError, "adapter_side_unsupported"):
            self.prepare(runtime_identity=plan_module.verify_runtime_identity(**args))

    def test_canonical_non_ascii_order_and_types_have_exact_identity(self):
        self.assertEqual(plan_module.canonical_bytes({"z": "明确核对", "a": 1}), b'{"a":1,"z":"\\u660e\\u786e\\u6838\\u5bf9"}')
        self.assertNotEqual(plan_module.digest({"x": 1}), plan_module.digest({"x": True}))
        for value in ({1: "integer-key"}, {"x": float("nan")}, {"x": float("inf")}, {"x": {1, 2}}):
            with self.subTest(value=str(value)), self.assertRaises(plan_module.PlanError): plan_module.canonical_bytes(value)
        projection = self.runtime.as_dict(); projection["permissions"]["submit_allowed"] = True
        self.assertFalse(self.runtime.as_dict()["permissions"]["submit_allowed"])
        with self.assertRaises(plan_module.PlanError): plan_module.VerifiedRuntimeIdentity(b"{}", object())


if __name__ == "__main__":
    unittest.main()
