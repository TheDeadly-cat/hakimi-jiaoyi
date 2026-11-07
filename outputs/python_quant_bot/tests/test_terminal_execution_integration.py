"""New synthetic records through the actual terminal resolver and account adapter."""
from copy import deepcopy
from datetime import datetime, timezone
from email.message import Message
from hashlib import sha256
from io import BytesIO
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import quote

from tests import test_terminal_research as fixtures
from exchange_terminal.services import quant_workspace as quant
from exchange_terminal.services import terminal_saved_results as saved_readers


class TerminalExecutionIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.TerminalResearchTests("runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.service = self.fixture.service
        self.addCleanup(self.service.close)
        self.creation = dict(client_request_id="integration-create-0001", account_id="synthetic-integration", label="合成整合案例",
            evidence_kind="SYNTHETIC_TEST", initial_cash="1000", securities={"QA:SYNTH": {"symbol": "SYNTH", "tick_size": "0.01"}},
            rules=dict(max_order_notional="500", max_total_exposure="800", max_security_exposure="500", cash_floor="100",
                       fee_buffer="1", max_account_loss="200", quote_max_age_ms=60000))

    def prepare_research(self, identity=True):
        if identity:
            self.fixture.market["meta"].update(security_id="QA:SYNTH", currency="USD", asset_class="US_EQUITY")
            self.fixture.market["digest"] = fixtures.digest({key: value for key, value in self.fixture.market.items() if key != "digest"})
        task = self.fixture.task()
        run = self.fixture.run_task(task)
        return task, run, {"kind": "terminal_run", "id": run["id"]}

    def inventory_research(self):
        return {str(path): sha256(path.read_bytes()).hexdigest()
                for folder in ("terminal-inputs", "terminal-tasks", "terminal-runs")
                for path in (self.fixture.core.workspace / folder).rglob("*") if path.is_file()}

    def test_saved_native_run_binds_synthetic_plan_without_another_research_run(self):
        task, run, reference = self.prepare_research()
        before, runs = self.inventory_research(), self.fixture.runner.call_count
        view = self.service.read("terminal_execution_research", json.dumps({"reference": reference}))
        self.assertEqual(view["binding"]["report_hash"], run["id"])
        self.assertEqual(view["binding"]["security_id"], "QA:SYNTH")
        self.assertFalse((self.fixture.core.workspace / "offline-execution").exists())
        created = self.service.mutate("terminal_execution_create_account", deepcopy(self.creation))
        result = self.service.mutate("terminal_execution_create_plan", {
            "client_request_id": "integration-plan-0001", "account_id": self.creation["account_id"],
            "account_context": created["account_context"], "reference": reference, "stage": "SIMULATION"})
        plan = result["account"]["ledger"]["plans"][0]
        self.assertEqual(plan["research_binding"]["task_id"], task["id"])
        self.assertEqual(result["account"]["plan_links"][0]["owner_continuity"], "VERIFIED_TASK_FAMILY")
        self.assertEqual(result["account"]["ledger"]["orders"], [])
        self.assertTrue(result["account"]["permissions"]["local_simulation_allowed"])
        for name in ("paper_order_allowed", "live_order_allowed", "order_allowed", "broker_connection_allowed", "model_calls_allowed"):
            self.assertIs(result["account"]["permissions"][name], False)
        self.assertEqual(self.fixture.runner.call_count, runs)
        self.assertEqual(self.inventory_research(), before)

    def test_missing_security_keeps_saved_research_readable_but_blocks_plan(self):
        _, _, reference = self.prepare_research(identity=False)
        created = self.service.mutate("terminal_execution_create_account", deepcopy(self.creation))
        with self.assertRaises(ValueError):
            self.service.mutate("terminal_execution_create_plan", {
                "client_request_id": "integration-plan-0001", "account_id": self.creation["account_id"],
                "account_context": created["account_context"], "reference": reference, "stage": "SIMULATION"})
        self.assertEqual(self.service.read("terminal_execution_account", self.creation["account_id"])["ledger"]["plans"], [])
        self.assertEqual(self.service.read("terminal_runs", reference["id"])["status"], "COMPLETED")

    def test_initial_execution_inventory_is_lazy_and_does_not_dispatch_core(self):
        self.assertEqual(self.service.read("terminal_execution_accounts")["items"], [])
        self.assertFalse(self.fixture.core.workspace.exists())
        self.assertEqual(self.fixture.core.calls, [])
        self.fixture.runner.assert_not_called()

    def test_real_native_saved_result_explanation_through_authenticated_read_route(self):
        # One new explicitly synthetic run through the actual native engine.
        # Subsequent reads must neither call it again nor touch original bytes.
        from exchange_terminal.services.market_calendar import _exchange_sessions
        sessions = _exchange_sessions("XNYS", "2024-01-02", "2024-08-30")[0][:130]
        self.fixture.market["rows"] = [dict(date=row["date"],
            ts_ms=int(datetime.fromisoformat(row["date"]).replace(tzinfo=timezone.utc).timestamp()*1000),
            open=100+index, high=102+index, low=99+index, close=101+index, volume=100,
            complete=True, provisional=False, source="fixture-provider") for index, row in enumerate(sessions)]
        self.fixture.market["meta"]["evidence_kind"] = "SYNTHETIC_TEST"
        def actual_runner(**kwargs):
            return fixtures.run_causal_long_only_backtest(rows=kwargs["market_payload"]["rows"], symbol=kwargs["symbol"],
                source=kwargs["market_payload"]["source"], signal_fn=fixtures.build_strategy_signal_fn(kwargs["strategy_id"], kwargs["strategy_params"]),
                startup_candles=fixtures.strategy_startup_candles_for_params(kwargs["strategy_id"], kwargs["strategy_params"]),
                position_pct=kwargs["position_pct"], take_profit_pct=kwargs["take_profit_pct"], stop_loss_pct=kwargs["stop_loss_pct"],
                leverage=kwargs["leverage"], fee_rate=kwargs["fee_rate"], slippage_bps=kwargs["slippage_bps"], market="stock", timeframe="1D")
        self.fixture.runner.side_effect = actual_runner
        _, run, reference = self.prepare_research()
        self.assertEqual(run["status"], "COMPLETED", run.get("error"))
        self.assertEqual(self.fixture.runner.call_count, 1)
        self.fixture.runner.side_effect = AssertionError("saved read must not rerun research")
        self.fixture.reader.side_effect = AssertionError("saved read must not fetch source")
        created = self.service.mutate("terminal_execution_create_account", deepcopy(self.creation))
        context = dict(account_id=self.creation["account_id"], account_context=created["account_context"])
        plan = self.service.mutate("terminal_execution_create_plan", dict(client_request_id="explanation-plan-0001", **context, reference=reference, stage="SIMULATION"))
        plan_id = plan["receipt"]["outcome"]["plan_id"]
        now = 1000000
        accepted = self.service.mutate("terminal_execution_submit", dict(client_request_id="explanation-order-0001", **context,
            plan_id=plan_id, security_id="QA:SYNTH", side="BUY", quantity=4, limit_price="10", outcome="ACCEPTED",
            quote=dict(security_id="QA:SYNTH", price="10", as_of=now, observed_at=now, source_id="explicit-fictional-test", evidence_kind="SYNTHETIC_TEST"),
            signal_at=now-1000, execution_at=now, now_ms=now))
        order_id = accepted["receipt"]["outcome"]["order_id"]
        for suffix, state, qty, notional, fee in (("one", "PARTIAL", 2, "20", "0.2"), ("two", "FILLED", 4, "40", "0.4")):
            self.service.mutate("terminal_execution_observe", dict(client_request_id="explanation-observe-"+suffix, **context, now_ms=now+100,
                observation=dict(order_id=order_id, evidence_id="explicit-observation-"+suffix, state=state,
                                 cumulative_quantity=qty, cumulative_notional=notional, cumulative_fee=fee)))
        payload = dict(**context, plan_id=plan_id, reference=reference)
        store = self.service._execution_service._stores[context["account_id"]]["store"]
        before, ledger_before = self.inventory_research(), store.snapshot()

        # Exercise the real handler and authentication/allowlist without a
        # listener, socket, jobs initialization, or an installed native window.
        shell = quant.QuantWorkspace(self.fixture.root / "new-memory-shell")
        shell._kernel, shell._service = SimpleNamespace(), self.service
        self.addCleanup(shell.close)
        def request(body):
            headers = Message()
            headers["Host"] = "127.0.0.1:54999"
            headers["Origin"] = "http://127.0.0.1:54999"
            headers["X-Hakimi-Token"] = shell._token
            handler = SimpleNamespace(path="/api/quant/terminal_execution_explanation/"+quote(json.dumps(body), safe=""),
                command="GET", headers=headers, server=SimpleNamespace(server_address=("127.0.0.1", 54999)),
                client_address=("127.0.0.1", 12000), wfile=BytesIO(), send_header=lambda *_: None, end_headers=lambda: None)
            handler.send_response = lambda status: setattr(handler, "status", status)
            self.assertTrue(shell.handle(handler))
            return handler.status, json.loads(handler.wfile.getvalue())
        with patch.object(saved_readers, "verified_saved_result", wraps=saved_readers.verified_saved_result) as verifier, \
                patch.object(self.service._execution_service, "read_saved_result", wraps=self.service._execution_service.read_saved_result) as projection_reader, \
                patch.object(store, "snapshot", wraps=store.snapshot) as snapshot:
            status, response = request(payload)
        self.assertEqual(status, 200, response)
        # Resolver looks up the verifier by module name; the projection callback
        # already captured the original verifier during lazy service creation.
        self.assertEqual(verifier.call_count, 1)
        projection_reader.assert_called_once_with(reference)
        self.assertEqual(snapshot.call_count, 1)
        result = response["data"]
        self.assertEqual(result["status"], "BOUND_REPORT_CONTEXT_ONLY")
        self.assertEqual(result["scope"]["reference_report_hash"], run["id"])
        self.assertEqual(result["scope"]["ledger_revision"], ledger_before["revision"])
        rows = {row["id"]: row for group in result["groups"] for row in group["items"]}
        self.assertEqual(rows["recorded_fees"]["simulation"]["value"], "0.4")
        self.assertEqual(rows["slippage"]["research"]["unit"], "basis_points")
        self.assertIsNone(rows["fill_time"]["simulation"]["value"])
        self.assertIsNone(result["attribution"]["contributions"])
        self.assertEqual(result["account_context"], context["account_context"])
        self.assertIsNone(shell._jobs)
        self.assertFalse(shell.runtime_dir.exists())
        self.assertEqual(store.snapshot(), ledger_before)
        self.assertEqual(self.inventory_research(), before)
        self.assertEqual(self.fixture.runner.call_count, 1)

        # Damage only this new TEMP report after the positive read. Rejection
        # must retain the damaged evidence rather than repairing/recomputing it.
        report_path = self.fixture.core.workspace / "terminal-runs" / run["operation_id"] / "report.json"
        changed = json.loads(report_path.read_bytes()); changed["result"]["total_return_pct"] = 999
        report_path.write_text(json.dumps(changed), encoding="utf-8")
        damaged = self.inventory_research()
        status, rejected = request(payload)
        self.assertEqual(status, 400)
        self.assertFalse(rejected["ok"])
        self.assertEqual(self.inventory_research(), damaged)
        self.assertEqual(store.snapshot(), ledger_before)
        self.assertEqual(self.fixture.runner.call_count, 1)


if __name__ == "__main__":
    unittest.main()
