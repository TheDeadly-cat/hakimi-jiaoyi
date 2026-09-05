from __future__ import annotations

import hashlib
import json
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.portfolio_paper_account import (
    PortfolioPaperLedger,
    build_target_order_preview,
)
from exchange_terminal.services.portfolio_paper_activation import (
    PAPER_ACTIVATION_SCOPE,
    build_paper_activation_receipt,
    verify_paper_activation_receipt,
)


CANDIDATE_HASH = "a" * 64


def canonical_hash(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def ready_context(candidate_hash: str = CANDIDATE_HASH) -> dict[str, object]:
    return {
        "status": "READY_FOR_FROZEN_EVALUATION",
        "candidate_hash": candidate_hash,
        "generated_at": 10_000,
        "active_candidate": {
            "status": "ACTIVE_RESEARCH_CANDIDATE",
            "candidate_hash": candidate_hash,
            "registry_hash": "b" * 64,
            "robustness_hash": "c" * 64,
            "experiment_completion_receipt_hash": "d" * 64,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "robustness_status": "ROBUSTNESS_PASS",
        "readiness": {
            "status": "READY_FOR_FROZEN_EVALUATION",
            "candidate_hash": candidate_hash,
            "critical_checks": {
                "candidate_verification_pass": True,
                "ledger_integrity_pass": True,
                "no_execution_authority": True,
            },
            "progress": {
                "natural_observations": 60,
                "required_natural_observations": 60,
                "externally_attested_observations": 60,
                "required_externally_attested_observations": 60,
                "planned_rebalances": 8,
                "required_planned_rebalances": 8,
            },
            "readiness_hash": "e" * 64,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "scheduler": {
            "status": "UP_TO_DATE",
            "health": "PASS",
            "status_hash": "f" * 64,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "experiment_registry": {
            "status": "PASS",
            "registry_audit": {"status": "PASS"},
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def paper_receipt(context: dict[str, object], *, account_id: str = "test") -> dict[str, object]:
    readiness = dict(context["readiness"])
    return build_paper_activation_receipt(
        account_id=account_id,
        forward_context=context,
        manual_approval={
            "approved": True,
            "scope": PAPER_ACTIVATION_SCOPE,
            "approver": "test-reviewer",
            "decision_id": "manual-decision-1",
            "approved_at": 10_001,
            "candidate_hash": context["candidate_hash"],
            "forward_readiness_hash": readiness["readiness_hash"],
        },
        initial_cash=100_000,
    )


def fill(fill_id: str, symbol: str, side: str, quantity: float, price: float, *, decision: str = "decision-1") -> dict[str, object]:
    return {
        "fill_id": fill_id,
        "idempotency_key": f"idem-{fill_id}",
        "decision_hash": decision,
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "price": price,
        "fee": 1.0,
    }


class PortfolioPaperAccountTests(unittest.TestCase):
    def make_ledger(self, path: Path, *, enabled: bool) -> PortfolioPaperLedger:
        counter = iter(range(1000, 10000))
        context = ready_context()
        ledger = PortfolioPaperLedger(
            db_path=path,
            now_ms=lambda: next(counter),
            account_id="test",
            authorization_provider=lambda: context,
        )
        state = ledger.initialize(100_000, simulation_enabled=False)
        if enabled:
            activation = ledger.activate_simulation(
                paper_receipt(context),
                expected_version=int(state["version"]),
            )
            self.assertEqual(activation["status"], "ACTIVATED")
        return ledger

    def test_disabled_runtime_cannot_apply_a_fill(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            ledger = self.make_ledger(Path(temporary) / "paper.sqlite", enabled=False)

            result = ledger.apply_fill(fill("f1", "AAPL", "BUY", 10, 100), expected_version=1)

            self.assertFalse(result["ok"])
            self.assertIn("portfolio_simulation_not_authorized", result["blockers"])
            self.assertEqual(ledger.summary()["status"], "DISABLED_PENDING_CANDIDATE")
            self.assertFalse(ledger.summary()["live_order_allowed"])

    def test_paper_activation_rejects_non_numeric_initial_cash_types(self) -> None:
        for invalid_cash in (True, "100000"):
            with self.subTest(invalid_cash=invalid_cash):
                context = ready_context()
                readiness = dict(context["readiness"])
                receipt = build_paper_activation_receipt(
                    account_id="test",
                    forward_context=context,
                    manual_approval={
                        "approved": True,
                        "scope": PAPER_ACTIVATION_SCOPE,
                        "approver": "test-reviewer",
                        "decision_id": "manual-decision-invalid-cash",
                        "approved_at": 10_001,
                        "candidate_hash": context["candidate_hash"],
                        "forward_readiness_hash": readiness["readiness_hash"],
                    },
                    initial_cash=invalid_cash,
                )

                self.assertEqual(receipt["status"], "BLOCK")
                self.assertIn("paper_initial_cash_not_positive", receipt["blockers"])
                self.assertFalse(receipt["paper_authorized"])

    def test_paper_activation_rejects_string_false_manual_approval(self) -> None:
        context = ready_context()
        readiness = dict(context["readiness"])
        receipt = build_paper_activation_receipt(
            account_id="test",
            forward_context=context,
            manual_approval={
                "approved": "false",
                "scope": PAPER_ACTIVATION_SCOPE,
                "approver": "test-reviewer",
                "decision_id": "manual-decision-string-false",
                "approved_at": 10_001,
                "candidate_hash": context["candidate_hash"],
                "forward_readiness_hash": readiness["readiness_hash"],
            },
            initial_cash=100_000,
        )

        self.assertEqual(receipt["status"], "BLOCK")
        self.assertIn("manual_paper_approval_missing", receipt["blockers"])
        self.assertIn("manual_paper_approval_type_invalid", receipt["blockers"])
        self.assertFalse(receipt["paper_authorized"])

    def test_paper_activation_rejects_non_boolean_critical_check(self) -> None:
        context = ready_context()
        context["readiness"]["critical_checks"]["candidate_verification_pass"] = "false"
        receipt = paper_receipt(context)

        self.assertEqual(receipt["status"], "BLOCK")
        self.assertIn("forward_critical_checks_not_passed", receipt["blockers"])
        self.assertIn("forward_critical_check_type_invalid", receipt["blockers"])
        self.assertFalse(receipt["paper_authorized"])

    def test_paper_activation_rejects_boolean_progress_counts(self) -> None:
        context = ready_context()
        context["readiness"]["progress"]["natural_observations"] = True
        context["readiness"]["progress"]["required_natural_observations"] = True
        receipt = paper_receipt(context)

        self.assertEqual(receipt["status"], "BLOCK")
        self.assertIn("forward_progress_type_invalid:natural_observations", receipt["blockers"])
        self.assertFalse(receipt["paper_authorized"])

    def test_paper_activation_rejects_float_progress_counts(self) -> None:
        context = ready_context()
        context["readiness"]["progress"]["natural_observations"] = 60.0
        receipt = paper_receipt(context)

        self.assertEqual(receipt["status"], "BLOCK")
        self.assertIn("forward_progress_type_invalid:natural_observations", receipt["blockers"])
        self.assertFalse(receipt["paper_authorized"])

    def test_resealed_paper_receipt_cannot_change_manual_binding(self) -> None:
        receipt = paper_receipt(ready_context())
        receipt["manual_approval"]["approved_at"] = 10_000.0
        receipt["manual_approval"]["candidate_hash"] = "b" * 64
        receipt.pop("receipt_hash")
        receipt["receipt_hash"] = canonical_hash(receipt)

        verification = verify_paper_activation_receipt(receipt)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("paper_activation_manual_approval_time_invalid", verification["blockers"])
        self.assertIn("paper_activation_manual_candidate_mismatch", verification["blockers"])

    def test_multi_symbol_fills_are_transactional_and_survive_restart(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "paper.sqlite"
            ledger = self.make_ledger(path, enabled=True)
            first = ledger.apply_fill(fill("f1", "AAPL", "BUY", 10, 100), expected_version=2)
            second = ledger.apply_fill(fill("f2", "NVDA", "BUY", 20, 50), expected_version=3)
            restarted = PortfolioPaperLedger(
                db_path=path,
                now_ms=lambda: 9000,
                account_id="test",
                authorization_provider=lambda: ready_context(),
            )
            snapshot = restarted.mark_to_market({"AAPL": 110, "NVDA": 45})

            self.assertEqual(first["status"], "APPLIED")
            self.assertEqual(second["status"], "APPLIED")
            self.assertEqual(snapshot["version"], 4)
            self.assertEqual({item["symbol"] for item in snapshot["positions"]}, {"AAPL", "NVDA"})
            self.assertAlmostEqual(snapshot["market_value"], 2000.0)
            self.assertEqual(restarted.summary()["fill_count"], 2)

    def test_idempotent_replay_is_safe_and_conflicting_reuse_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            ledger = self.make_ledger(Path(temporary) / "paper.sqlite", enabled=True)
            original = fill("f1", "AAPL", "BUY", 10, 100)
            applied = ledger.apply_fill(original, expected_version=2)
            replay = ledger.apply_fill(original, expected_version=2)
            conflict = ledger.apply_fill({**original, "quantity": 11}, expected_version=3)

            self.assertEqual(applied["status"], "APPLIED")
            self.assertEqual(replay["status"], "IDEMPOTENT_REPLAY")
            self.assertEqual(replay["state"]["version"], 3)
            self.assertFalse(conflict["ok"])
            self.assertIn("idempotency_conflict", conflict["blockers"])

    def test_stale_version_oversell_and_live_mode_are_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            ledger = self.make_ledger(Path(temporary) / "paper.sqlite", enabled=True)
            ledger.apply_fill(fill("f1", "AAPL", "BUY", 10, 100), expected_version=2)

            stale = ledger.apply_fill(fill("f2", "NVDA", "BUY", 1, 50), expected_version=2)
            oversell = ledger.apply_fill(fill("f3", "AAPL", "SELL", 11, 100), expected_version=3)
            live = ledger.apply_fill(fill("f4", "AAPL", "SELL", 1, 100), expected_version=3, mode="live")

            self.assertTrue(any(item.startswith("stale_account_version") for item in stale["blockers"]))
            self.assertIn("sell_quantity_exceeds_long_position", oversell["blockers"])
            self.assertIn("live_mode_permanently_blocked", live["blockers"])

    def test_boolean_fee_and_version_are_rejected_without_account_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            ledger = self.make_ledger(Path(temporary) / "paper.sqlite", enabled=True)
            invalid_fee = ledger.apply_fill(
                {**fill("f1", "AAPL", "BUY", 1, 100), "fee": True},
                expected_version=2,
            )
            invalid_version = ledger.apply_fill(
                fill("f2", "AAPL", "BUY", 1, 100),
                expected_version=True,  # type: ignore[arg-type]
            )

            self.assertIn("invalid_fill_numeric_contract", invalid_fee["blockers"])
            self.assertIn("invalid_expected_version", invalid_version["blockers"])
            self.assertEqual(ledger.summary()["fill_count"], 0)
            self.assertEqual(ledger.summary()["version"], 2)

    def test_direct_initialization_flag_cannot_enable_simulation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            ledger = PortfolioPaperLedger(
                db_path=Path(temporary) / "paper.sqlite",
                now_ms=lambda: 1000,
                account_id="test",
                authorization_provider=lambda: ready_context(),
            )

            state = ledger.initialize(100_000, simulation_enabled=True)
            result = ledger.apply_fill(fill("f1", "AAPL", "BUY", 1, 100), expected_version=1)

            self.assertFalse(state["simulation_enabled"])
            self.assertIn("direct_simulation_enable_forbidden", state["activation_blockers"])
            self.assertIn("portfolio_simulation_not_authorized", result["blockers"])

    def test_non_boolean_initialization_flag_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            ledger = PortfolioPaperLedger(
                db_path=Path(temporary) / "paper.sqlite",
                now_ms=lambda: 1000,
                account_id="test",
                authorization_provider=lambda: ready_context(),
            )

            state = ledger.initialize(100_000, simulation_enabled="false")  # type: ignore[arg-type]

            self.assertFalse(state["simulation_enabled"])
            self.assertIn("simulation_enabled_invalid_type", state["activation_blockers"])

    def test_persisted_string_simulation_flag_cannot_authorize_fills(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "paper.sqlite"
            ledger = self.make_ledger(path, enabled=True)
            state = ledger.load()
            state["simulation_enabled"] = "false"
            with closing(sqlite3.connect(path)) as connection:
                connection.execute(
                    "UPDATE portfolio_paper_accounts SET state_json = ? WHERE account_id = 'test'",
                    (json.dumps(state),),
                )
                connection.commit()

            result = ledger.apply_fill(fill("f1", "AAPL", "BUY", 1, 100), expected_version=2)
            snapshot = ledger.mark_to_market()

            self.assertFalse(result["ok"])
            self.assertIn("portfolio_simulation_not_authorized", result["blockers"])
            self.assertFalse(snapshot["simulation_enabled"])
            self.assertFalse(snapshot["paper_authorized"])

    def test_corrupt_authorized_numeric_state_suspends_simulation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "paper.sqlite"
            ledger = self.make_ledger(path, enabled=True)
            state = ledger.load()
            state["fees_paid"] = True
            with closing(sqlite3.connect(path)) as connection:
                connection.execute(
                    "UPDATE portfolio_paper_accounts SET state_json = ? WHERE account_id = 'test'",
                    (json.dumps(state),),
                )
                connection.commit()

            result = ledger.apply_fill(fill("f1", "AAPL", "BUY", 1, 100), expected_version=2)
            snapshot = ledger.mark_to_market()

            self.assertFalse(result["ok"])
            self.assertTrue(any("portfolio_state_numeric_invalid:fees_paid" in item for item in result["blockers"]))
            self.assertEqual(snapshot["status"], "SIMULATION_SUSPENDED")
            self.assertFalse(snapshot["paper_authorized"])

    def test_collecting_forward_context_cannot_create_an_activation_receipt(self) -> None:
        context = ready_context()
        context["status"] = "COLLECTING"
        context["readiness"] = {**dict(context["readiness"]), "status": "COLLECTING"}

        receipt = paper_receipt(context)

        self.assertEqual(receipt["status"], "BLOCK")
        self.assertIn("forward_readiness_not_complete", receipt["blockers"])
        self.assertFalse(receipt["paper_authorized"])

    def test_tampered_receipt_and_candidate_drift_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "paper.sqlite"
            context = ready_context()
            ledger = PortfolioPaperLedger(
                db_path=path,
                now_ms=iter(range(1000, 10000)).__next__,
                account_id="test",
                authorization_provider=lambda: context,
            )
            state = ledger.initialize(0)
            receipt = paper_receipt(context)
            tampered = {**receipt, "initial_cash": 200_000}

            blocked = ledger.activate_simulation(tampered, expected_version=int(state["version"]))
            activated = ledger.activate_simulation(receipt, expected_version=int(state["version"]))
            context["candidate_hash"] = "9" * 64
            context["readiness"] = {**dict(context["readiness"]), "candidate_hash": "9" * 64}
            context["active_candidate"] = {**dict(context["active_candidate"]), "candidate_hash": "9" * 64}
            fill_result = ledger.apply_fill(fill("f1", "AAPL", "BUY", 1, 100), expected_version=2)
            snapshot = ledger.summary()

            self.assertFalse(blocked["ok"])
            self.assertTrue(any("receipt_hash_mismatch" in item for item in blocked["blockers"]))
            self.assertEqual(activated["status"], "ACTIVATED")
            self.assertFalse(fill_result["ok"])
            self.assertTrue(any("current_identity_mismatch:candidate_hash" in item for item in fill_result["blockers"]))
            self.assertEqual(snapshot["status"], "SIMULATION_SUSPENDED")
            self.assertFalse(snapshot["paper_authorized"])

    def test_scheduler_staleness_suspends_an_activated_account(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = ready_context()
            ledger = PortfolioPaperLedger(
                db_path=Path(temporary) / "paper.sqlite",
                now_ms=iter(range(1000, 10000)).__next__,
                account_id="test",
                authorization_provider=lambda: context,
            )
            state = ledger.initialize(0)
            ledger.activate_simulation(paper_receipt(context), expected_version=int(state["version"]))
            context["scheduler"] = {**dict(context["scheduler"]), "status": "STALE", "health": "BLOCK"}

            result = ledger.apply_fill(fill("f1", "AAPL", "BUY", 1, 100), expected_version=2)
            snapshot = ledger.summary()

            self.assertFalse(result["ok"])
            self.assertTrue(any("forward_scheduler_not_healthy" in item for item in result["blockers"]))
            self.assertEqual(snapshot["status"], "SIMULATION_SUSPENDED")
            self.assertFalse(snapshot["simulation_enabled"])

    def test_corrupt_account_state_fails_closed_without_raising(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "paper.sqlite"
            ledger = PortfolioPaperLedger(db_path=path, now_ms=lambda: 1000, account_id="test")
            ledger.initialize(0)
            with closing(sqlite3.connect(path)) as connection:
                connection.execute(
                    "UPDATE portfolio_paper_accounts SET state_json = '{broken' WHERE account_id = 'test'"
                )
                connection.commit()

            state = ledger.load()
            result = ledger.apply_fill(fill("f1", "AAPL", "BUY", 1, 100), expected_version=1)

            self.assertEqual(state["status"], "BLOCK")
            self.assertIn("portfolio_paper_account_state_corrupt", state["blockers"])
            self.assertFalse(result["ok"])
            self.assertIn("portfolio_paper_account_state_corrupt", result["blockers"])

    def test_non_object_account_state_fails_closed_without_raising(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "paper.sqlite"
            ledger = PortfolioPaperLedger(db_path=path, now_ms=lambda: 1000, account_id="test")
            ledger.initialize(0)
            with closing(sqlite3.connect(path)) as connection:
                connection.execute(
                    "UPDATE portfolio_paper_accounts SET state_json = '[]' WHERE account_id = 'test'"
                )
                connection.commit()

            state = ledger.load()
            result = ledger.apply_fill(fill("f1", "AAPL", "BUY", 1, 100), expected_version=1)

            self.assertEqual(state["status"], "BLOCK")
            self.assertFalse(result["ok"])
            self.assertIn("portfolio_paper_account_state_corrupt", result["blockers"])

    def test_legacy_unbound_enabled_state_is_disabled_during_migration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "paper.sqlite"
            ledger = PortfolioPaperLedger(db_path=path, now_ms=lambda: 1000, account_id="test")
            state = ledger.initialize(100_000)
            state.update({"schema_version": "portfolio-paper-ledger-v1", "simulation_enabled": True})
            with closing(sqlite3.connect(path)) as connection:
                connection.execute(
                    "UPDATE portfolio_paper_accounts SET state_json = ? WHERE account_id = 'test'",
                    (json.dumps(state),),
                )
                connection.commit()

            migrated = PortfolioPaperLedger(db_path=path, now_ms=lambda: 2000, account_id="test").initialize(0)

            self.assertFalse(migrated["simulation_enabled"])
            self.assertFalse(migrated["paper_authorized"])
            self.assertIn("legacy_unbound_simulation_disabled", migrated["activation_blockers"])

    def test_valid_receipt_verification_is_content_addressed(self) -> None:
        receipt = paper_receipt(ready_context())

        audit = verify_paper_activation_receipt(receipt, expected_account_id="test")

        self.assertEqual(receipt["status"], "APPROVED_FOR_ISOLATED_PAPER")
        self.assertEqual(audit["status"], "PASS")
        self.assertTrue(audit["paper_authorized"])
        self.assertFalse(audit["live_order_allowed"])

    def test_target_preview_sells_before_buys_and_never_authorizes_execution(self) -> None:
        state = {
            "cash": 5_000,
            "positions": {
                "AAPL": {"symbol": "AAPL", "quantity": 50, "entry_price": 100, "last_price": 100},
            },
        }
        preview = build_target_order_preview(
            state=state,
            target_weights={"AAPL": 0.2, "NVDA": 0.5},
            prices={"AAPL": 100, "NVDA": 50},
            decision_hash="decision-1",
            maximum_gross_pct=70,
        )

        self.assertEqual(preview["status"], "PASS")
        self.assertEqual([item["side"] for item in preview["orders"]], ["SELL", "BUY"])
        self.assertFalse(preview["paper_authorized"])
        self.assertFalse(preview["live_order_allowed"])


if __name__ == "__main__":
    unittest.main()
