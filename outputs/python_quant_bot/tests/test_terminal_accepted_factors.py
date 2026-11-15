"""Accepted teaching fixture + original rule, never provider or native fallback.

Only setup creates explicit fictional saved reports. Context/factor operations
are bracketed by full workspace byte inventories and forbidden run/network IO.
"""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from exchange_terminal.services.quant_workspace import _load_kernel, _verified_package_root, _VENDOR, ACCEPTED_SOURCE_SHA256
from exchange_terminal.services.terminal_research import TerminalResearchService
from exchange_terminal.services.terminal_teaching_flow import prepare_teaching_input, PARAMS
from exchange_terminal.services import terminal_accepted_factors as factors


def inventory(root):
    return {path.relative_to(root).as_posix(): sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*") if path.is_file()}


class _AcceptedFactorCases:
    @classmethod
    def setUpClass(cls):
        # A real fresh installed copy uses the existing build receipt contract;
        # no checkout/vendor bytes or VERIFIED statuses are patched.
        cls.installation = tempfile.TemporaryDirectory(prefix="accepted-factor-installed-")
        cls.addClassCleanup(cls.installation.cleanup)
        source = _verified_package_root(_VENDOR)
        vendor = Path(cls.installation.name).resolve() / "vendor" / "research"
        package = vendor / "hakimi_terminal_research"
        for name in json.loads((source / "runtime-files.json").read_bytes())["files"]:
            destination = package / name; destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / name, destination)
        cls.kernel = _load_kernel(vendor)
        from hakimi_terminal_research.source_identity import package_content_identity, BUILD_IDENTITY_FILENAME
        from hakimi_terminal_research.environment import build_runtime_provenance
        identity = package_content_identity(package)
        assert identity["content_sha256"] == ACCEPTED_SOURCE_SHA256
        (package / BUILD_IDENTITY_FILENAME).write_text(json.dumps(dict(schema_version="research-build-source-v1",
            **identity, git={"commit": "", "status": "UNKNOWN"},
            test_scope="TEMP_INSTALLED_ACCEPTED_FACTOR_FIXTURE_ONLY")), encoding="utf-8")
        runtime = build_runtime_provenance()
        assert runtime["source_identity"]["status"] == "BUILD_VERIFIED"
        assert runtime["environment_verified"]["status"] == "VERIFIED"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="accepted-factor-fictional-only-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.core = self.kernel.service(self.root / "workspace")
        self.service = TerminalResearchService(self.core, self.denied, lambda: [], self.denied, self.denied)
        self.addCleanup(self.service.close)
        patcher = patch("socket.socket.connect", side_effect=AssertionError("No provider/network"))
        patcher.start(); self.addCleanup(patcher.stop)
        prepared = prepare_teaching_input(self.service, {})
        original = self.core.read("inputs", prepared["input_id"])
        self.input = prepared
        from hakimi_terminal_research.documents import read_document
        snapshot = read_document(self.core._lookup("inputs", original["id"]))
        self.snapshot = snapshot
        task = self.core.mutate("create_task", dict(name="accepted-factor-fictional", title="教学双均线因子",
            strategy="price.dual_ma@1", snapshot_id=prepared["input_id"], params=deepcopy(PARAMS),
            initial_cash=100, score_end=snapshot["sessions"][-3]["date"]))
        # Real fixed-fixture accepted run, not a fabricated verifier envelope.
        result = self.core.mutate("run_task", {"task_id": task["id"]})
        self.reference = {"kind": "core_run", "id": result["id"]}
        self.report_directory = self.core._lookup("runs", result["id"])
        for target in ("hakimi_terminal_research.backtest.BacktestEngine.run",
                       "hakimi_terminal_research.offline_app.run_task"):
            blocked = patch(target, side_effect=AssertionError("Factor read must not run research"))
            blocked.start(); self.addCleanup(blocked.stop)

    @staticmethod
    def denied(*args, **kwargs):
        raise AssertionError("No native runner, market reader or provider")

    def context(self):
        return self.service.read("terminal_accepted_rule_context", json.dumps(self.reference))

    def read(self, context, position=False, **changes):
        payload = dict(reference=self.reference, context_id=context["context_id"],
                       position_context={"has_position": position})
        payload.update(changes)
        return self.service.read("terminal_accepted_factors", json.dumps(payload))

    def test_real_teaching_saved_context_factors_and_reopen_keep_every_original_byte(self):
        research = self.service.read("terminal_execution_research", json.dumps({"reference": self.reference}))
        before = inventory(self.core.workspace)
        context = self.context()
        self.assertEqual(context["engine_id"], "research.accepted-equity")
        self.assertEqual(context["strategy_id"], "price.dual_ma@1")
        self.assertEqual(context["strategy_params"], PARAMS)
        self.assertEqual(context["initial_cash"], 100)
        self.assertEqual(context["cutoff_session"], self.snapshot["sessions"][-3]["date"])
        self.assertGreater(context["snapshot_end"], context["cutoff_session"])
        self.assertEqual(len(self.reference["id"]), 24)
        self.assertEqual(len(context["report_id"]), 64); self.assertEqual(len(context["report_hash"]), 64)
        self.assertNotEqual(self.reference["id"], context["report_id"])
        flat, holding = self.read(context), self.read(context, True)
        for response in (flat, holding):
            self.assertTrue(response["read_only"]); self.assertEqual(response["new_economic_runs"], 0)
            self.assertEqual(response["row"]["schema_version"], factors.ROW_SCHEMA)
            self.assertEqual(response["row"]["factors"][0]["value"], 20)
            self.assertTrue(response["row"]["decision_matches_factors"])
            self.assertFalse(response["row"]["freshness"]["live_quote_verified"])
        self.assertEqual(self.read(context), flat)
        self.assertEqual(inventory(self.core.workspace), before)
        self.service.close()
        reopened = TerminalResearchService(self.kernel.service(self.core.workspace), self.denied, lambda: [], self.denied, self.denied)
        try:
            self.assertEqual(reopened.read("terminal_accepted_rule_context", json.dumps(self.reference)), context)
            self.assertEqual(reopened.read("terminal_accepted_factors", json.dumps(dict(reference=self.reference,
                context_id=context["context_id"], position_context={"has_position": False}))), flat)
        finally:
            reopened.close()
        self.assertEqual(inventory(self.core.workspace), before)
    def test_request_malformed_stale_or_client_supplied_context_is_refused_without_write(self):
        context = self.context(); before = inventory(self.core.workspace)
        for changes in ({"context_id": "0" * 64}, {"position_context": {}},
                        {"position_context": {"has_position": "false"}},
                        {"position_context": {"has_position": 0}},
                        {"reference": {"kind": "terminal_run", "id": context["report_hash"]}},
                        {"reference": {**self.reference, "path": "../report"}},
                        {"cutoff_session": self.snapshot["sessions"][-1]["date"]},
                        {"strategy_params": {"fast_window": 1}}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.read(context, **changes)
        duplicate = '{"reference":'+json.dumps(self.reference)+',"context_id":"'+context["context_id"]+'","context_id":"'+'0'*64+'","position_context":{"has_position":false}}'
        with self.assertRaisesRegex(ValueError, "duplicate_json_field"):
            self.service.read("terminal_accepted_factors", duplicate)
        self.assertEqual(inventory(self.core.workspace), before)

    def test_tampered_saved_report_is_refused_without_repair(self):
        context = self.context()
        path = self.report_directory / "report.json"
        value = json.loads(path.read_bytes()); value["spec"]["initial_cash"] = 999
        path.write_text(json.dumps(value), encoding="utf-8")
        before = inventory(self.core.workspace)
        with self.assertRaises(ValueError): self.read(context)
        self.assertEqual(inventory(self.core.workspace), before)

    def test_old_recorded_source_and_unsupported_strategy_do_not_borrow_native_factors(self):
        context = self.context(); before = inventory(self.core.workspace)
        original = factors.verified_saved_result(self.service, self.reference)
        for kind in ("source", "strategy"):
            modified = deepcopy(original)
            if kind == "source":
                modified["manifest"]["runtime"]["source_identity"]["content_sha256"] = "0" * 64
                reason = "recorded_source_changed"
            else:
                modified["manifest"]["task"]["strategy"] = "price.buy_and_hold@1"
                reason = "strategy_unsupported"
            with self.subTest(kind=kind), patch.object(factors, "verified_saved_result", return_value=modified), self.assertRaisesRegex(ValueError, reason):
                self.read(context)
        self.assertEqual(inventory(self.core.workspace), before)

    def test_loaded_rule_or_sma_substitution_is_refused_even_when_disk_is_unchanged(self):
        context = self.context(); before = inventory(self.core.workspace)
        from hakimi_terminal_research.strategies import templates
        from hakimi_terminal_research import indicators
        for target, name in ((templates.DualMovingAverageStrategy, "generate_signal"), (indicators, "sma")):
            with self.subTest(name=name), patch.object(target, name, lambda *args: None), self.assertRaisesRegex(ValueError, "loaded_rule"):
                self.read(context)
        self.assertEqual(inventory(self.core.workspace), before)

    def test_adapter_loaded_disk_change_refuses_derived_read(self):
        context = self.context()
        with patch.object(factors, "_ADAPTER_LOADED_SHA", "0" * 64), self.assertRaisesRegex(ValueError, "adapter_source_changed"):
            self.read(context)

    def test_original_signal_parity_buy_exit_hold_warmup_and_already_above_counterexample(self):
        context = self.context()
        source, strategy, indicators, models, snapshot_class = factors._rule_runtime(context["source_hash"])
        import pandas as pd
        cases = [("BUY", [10,10,10,8,8,14], False), ("EXIT", [10,10,10,12,12,6], True),
                 ("HOLD", [10,11,12,13,14,15], False), ("HOLD", [10,10,10,8,8,14], True),
                 ("HOLD", [10,10,10,12,12,6], False), ("HOLD", [10,11,12,13,14], False)]
        for expected, prices, holding in cases:
            frame = pd.DataFrame({"close": [float(price) for price in prices]})
            row = factors._explain_prefix(frame, context["strategy_params"], holding, context["cutoff_session"],
                strategy_class=strategy, indicators=indicators, models=models)
            original = strategy(deepcopy(context["strategy_params"])).generate_signal(frame,
                models.Portfolio(cash=0.0, position_qty=1.0 if holding else 0.0))
            with self.subTest(expected=expected, prices=prices, holding=holding):
                self.assertEqual(row["signal"], {"action": original.action.value, "reason": original.reason})
                self.assertEqual(row["signal"]["action"], expected)
                self.assertTrue(row["decision_matches_factors"])
                if len(prices) == 5:
                    self.assertEqual(row["status"], "INSUFFICIENT_HISTORY")
                    self.assertEqual(row["signal"]["reason"], "not enough data")
                    self.assertFalse(row["factors"][0]["passed"])
                    for factor in row["factors"][1:]:
                        for key in ("value", "threshold", "passed"): self.assertIsNone(factor[key])
                if prices == [10,11,12,13,14,15]:
                    self.assertFalse(row["factors"][1]["passed"])
                    self.assertTrue(row["factors"][2]["passed"])
                    self.assertEqual(row["signal"]["reason"], "no MA crossover")
        before = inventory(self.core.workspace)
        research = self.service.read("terminal_execution_research", json.dumps({"reference": self.reference}))
        flat, holding = self.read(context), self.read(context, True)
        original_frame = snapshot_class(self.snapshot).frame().iloc[:20]
        self.assertEqual(flat["row"]["factors"][2]["value"], float(indicators.sma(original_frame["close"], 2).iloc[-1]))
        self.assertEqual(inventory(self.core.workspace), before)
        # Optional cross-layer artifact comes from this already-required real
        # fixture. It never creates a second report just for UI validation.
        target = os.environ.get("HAKIMI_ACCEPTED_FACTOR_PROBE_PATH")
        if target:
            with Path(target).open("x", encoding="utf-8") as output:
                json.dump(dict(scope="SAME_REQUIRED_PARITY_FIXTURE_REAL_SAVED_REPORT_NO_EXTRA_RUN", reference=self.reference,
                    context=context, research=research, flat=flat, holding=holding, original_files_sha256=before),
                    output, ensure_ascii=False, indent=2)

    def test_disk_accepted_pin_change_is_rejected_and_test_copy_restored(self):
        context = self.context(); path = self.kernel.root / "indicators.py"; original = path.read_bytes()
        before = inventory(self.core.workspace)
        try:
            path.write_bytes(original + b"\n# explicit corruption of fresh installed test copy\n")
            with self.assertRaisesRegex(ValueError, "quant_runtime_source_identity_mismatch"):
                self.read(context)
        finally:
            path.write_bytes(original)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(inventory(self.core.workspace), before)


class AcceptedFactorTests(unittest.TestCase):
    def test_real_installed_accepted_factor_contracts(self):
        # Isolate accepted-module identities from earlier tests in a full gate.
        result = subprocess.run([sys.executable, "-B", "-m", "tests.test_terminal_accepted_factors", "--installed-child"],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, encoding="utf-8", timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        print(result.stdout + result.stderr, end="")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    if "--installed-child" in sys.argv:
        class InstalledAcceptedFactorTests(_AcceptedFactorCases, unittest.TestCase):
            pass
        names = [name for name in sys.argv[1:] if name != "--installed-child"]
        suite = (unittest.TestSuite(InstalledAcceptedFactorTests(name) for name in names) if names else
                 unittest.defaultTestLoader.loadTestsFromTestCase(InstalledAcceptedFactorTests))
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        raise SystemExit(not result.wasSuccessful())
    unittest.main()
