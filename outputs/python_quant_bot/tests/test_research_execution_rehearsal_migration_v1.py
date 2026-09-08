from __future__ import annotations

import hashlib
import inspect
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
QUANT_ROOT = REPO_ROOT / "outputs" / "python_quant_bot"
for search_root in (SRC_ROOT, QUANT_ROOT):
    if str(search_root) not in sys.path:
        sys.path.insert(0, str(search_root))

from hakimi_research import research_execution_rehearsal as rehearsal
from hakimi_research import research_order_lifecycle_contract as lifecycle


class _DictSubclass(dict):
    pass


class _StrSubclass(str):
    def encode(self, *args: object, **kwargs: object) -> bytes:
        raise AssertionError("subclass-controlled encode must never run")


class _IntSubclass(int):
    pass


class ResearchExecutionRehearsalMigrationV1Tests(unittest.TestCase):
    def test_archived_executor_is_byte_identical(self) -> None:
        path = REPO_ROOT / "archive" / "legacy_paper" / "adr0524_paper_executor.py"
        self.assertEqual(
            hashlib.sha256(path.read_bytes()).hexdigest(),
            "5bedf1cd7125f589a625578175aa6e32533c8bdef6dc22606659d9b0ff94eeb8",
        )

    def test_archived_contract_is_byte_identical(self) -> None:
        path = REPO_ROOT / "archive" / "legacy_paper" / "adr0524_paper_order_contract.py"
        self.assertEqual(
            hashlib.sha256(path.read_bytes()).hexdigest(),
            "848194ff681ea00a0c554dfe2bec52577a4f382606218828e5b432f4a761b34c",
        )

    def test_archived_identity_test_is_byte_identical(self) -> None:
        path = REPO_ROOT / "archive" / "legacy_paper" / "adr0524_test_paper_executor_risk_authorization_identity_v1.py"
        self.assertEqual(
            hashlib.sha256(path.read_bytes()).hexdigest(),
            "2e7eed00fda06a0d41d88f25ff1302321666c7131a37b30d8a81a34b93321254",
        )

    def test_formal_old_modules_and_test_are_absent(self) -> None:
        service_root = QUANT_ROOT / "exchange_terminal" / "services"
        self.assertFalse((service_root / "paper_executor.py").exists())
        self.assertFalse((service_root / "paper_order_contract.py").exists())
        self.assertFalse(
            (QUANT_ROOT / "tests" / "test_paper_executor_risk_authorization_identity_v1.py").exists()
        )

    def test_contract_is_explicitly_versioned(self) -> None:
        self.assertEqual(
            lifecycle.RESEARCH_ORDER_LIFECYCLE_CONTRACT_VERSION,
            "research-order-lifecycle-v1",
        )
        self.assertEqual(
            rehearsal.RESEARCH_EXECUTION_REHEARSAL_VERSION,
            "research-execution-rehearsal-v1",
        )

    def test_capabilities_are_permanently_false(self) -> None:
        for module in (rehearsal, lifecycle):
            self.assertFalse(module.ALLOW_PAPER)
            self.assertFalse(module.ALLOW_LIVE)
            self.assertFalse(module.ALLOW_ORDER_ENTRY)

    def test_snapshot_is_neutral_and_research_only(self) -> None:
        simulator = rehearsal.ResearchExecutionRehearsalSimulator(
            now_ms=lambda: 42,
            instance_nonce="fixture",
            account_id="fixture-account",
        )
        snapshot = simulator.snapshot()
        self.assertEqual(snapshot["mode"], "RESEARCH_REHEARSAL")
        self.assertIs(snapshot["research_only"], True)
        self.assertIs(snapshot["paper_allowed"], False)
        self.assertIs(snapshot["live_order_allowed"], False)
        self.assertIs(snapshot["order_entry_allowed"], False)

    def test_default_nonce_is_deterministic(self) -> None:
        first = rehearsal.ResearchExecutionRehearsalSimulator(
            now_ms=lambda: 42,
            account_id="fixture-account",
        )
        second = rehearsal.ResearchExecutionRehearsalSimulator(
            now_ms=lambda: 42,
            account_id="fixture-account",
        )
        self.assertEqual(first.instance_nonce, second.instance_nonce)

    def test_account_id_subclass_is_rejected_before_encode(self) -> None:
        with self.assertRaises(TypeError):
            rehearsal.ResearchExecutionRehearsalSimulator(
                now_ms=lambda: 42,
                account_id=_StrSubclass("fixture-account"),
            )

    def test_nonce_subclass_is_rejected_before_encode(self) -> None:
        with self.assertRaises(TypeError):
            rehearsal.ResearchExecutionRehearsalSimulator(
                now_ms=lambda: 42,
                account_id="fixture-account",
                instance_nonce=_StrSubclass("fixture"),
            )

    def test_symbol_subclass_is_rejected_before_string_methods(self) -> None:
        with self.assertRaises(TypeError):
            rehearsal.research_execution_report(
                _StrSubclass("AAPL"),
                "BUY",
                "MARKET",
                100.0,
                100.0,
            )

    def test_risk_dict_subclass_is_rejected(self) -> None:
        simulator = rehearsal.ResearchExecutionRehearsalSimulator(
            now_ms=lambda: 42,
            instance_nonce="fixture",
            account_id="fixture-account",
        )
        with self.assertRaises(TypeError):
            simulator.submit(
                symbol="AAPL",
                side="BUY",
                order_type="MARKET",
                mark_price=100.0,
                notional=100.0,
                risk_result=_DictSubclass(),
            )

    def test_nested_identifier_subclass_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            lifecycle.validate_research_rehearsal_lifecycle_order(
                {"order_id": _StrSubclass("alias")}
            )

    def test_integer_subclass_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            lifecycle.validate_research_rehearsal_lifecycle_order(
                {"quantity": _IntSubclass(1)}
            )

    def test_no_network_default_executes(self) -> None:
        report = rehearsal.research_execution_report(
            "AAPL",
            "BUY",
            "MARKET",
            100.0,
            100.0,
        )
        self.assertEqual(report["status"], "FILLED")

    def test_no_network_or_random_default_symbols_remain(self) -> None:
        source = inspect.getsource(rehearsal)
        for banned in (
            "read_okx_book_side",
            "funding_rate_for_symbol",
            "market_data.okx",
            "secrets.",
            "uuid.",
        ):
            self.assertNotIn(banned, source)

    def test_legacy_replay_names_are_explicitly_versioned(self) -> None:
        source = inspect.getsource(rehearsal)
        self.assertEqual(rehearsal.LEGACY_REPLAY_WIRE_SCHEMA, "paper-lifecycle-v1")
        self.assertIn('"paper_signal"', source)
        self.assertIn('"paper_order_transition"', source)


if __name__ == "__main__":
    unittest.main()
