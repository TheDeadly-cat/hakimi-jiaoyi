from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.corporate_action_ledger import (
    CorporateActionLedger,
    build_adjustment_evidence as _build_adjustment_evidence,
    build_corporate_action_source_evidence,
    build_official_corporate_action_attestation,
    infer_adjustment_basis,
    parse_yahoo_corporate_actions,
    verify_adjustment_evidence,
)
from tests._stock_schedule_fixture import build_stock_schedule_fixture


def canonical_hash(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def make_rows(count: int = 40, *, split_index: int = -1) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    trading_date = date(2025, 1, 2)
    close = 100.0
    for index in range(count):
        while trading_date.weekday() >= 5:
            trading_date += timedelta(days=1)
        previous = close
        close = previous * (0.25 if index == split_index else 1.002)
        rows.append({
            "date": trading_date.isoformat(),
            "ts_ms": (trading_date - date(1970, 1, 1)).days * 86_400_000,
            "open": previous if index != split_index else close,
            "high": max(previous if index != split_index else close, close) * 1.01,
            "low": min(previous if index != split_index else close, close) * 0.99,
            "close": close,
            "volume": 1_000_000,
            "complete": True,
        })
        trading_date += timedelta(days=1)
    return rows


def build_adjustment_evidence(**kwargs: object) -> dict[str, object]:
    rows = kwargs.get("rows")
    source = kwargs.get("source", "futu")
    symbol = kwargs.get("symbol", "AAPL")
    if type(rows) is list and type(source) is str and type(symbol) is str:
        kwargs.setdefault(
            "schedule_attestation",
            build_stock_schedule_fixture(rows, symbol=symbol, source=source),
        )
    return _build_adjustment_evidence(**kwargs)  # type: ignore[arg-type,return-value]


def official_attestation() -> dict[str, object]:
    source = build_corporate_action_source_evidence(
        source_authority="OFFICIAL_EXCHANGE_FEED",
        source_name="Test Exchange Corporate Action Master",
        evidence_ref="https://example.test/corporate-actions/aapl",
        source_document_sha256=hashlib.sha256(b"official-aapl-corporate-action-document").hexdigest(),
        observed_at="2026-08-01T00:00:00Z",
        coverage_types=["SPLIT", "DIVIDEND", "SUSPENSION", "DELISTING"],
        record_count=0,
    )
    return build_official_corporate_action_attestation(
        source_authority="OFFICIAL_EXCHANGE_FEED",
        source_name="Test Exchange Corporate Action Master",
        evidence_ref="https://example.test/corporate-actions/aapl",
        evidence_sha256=str(source["evidence_sha256"]),
        observed_at="2026-08-01T00:00:00Z",
        coverage_types=["SPLIT", "DIVIDEND", "SUSPENSION", "DELISTING"],
        evidence_payload=source,
    )


class CorporateActionLedgerTests(unittest.TestCase):
    def test_malformed_adjustment_evidence_fails_closed_without_raising(self) -> None:
        audit = verify_adjustment_evidence([])

        self.assertEqual(audit["status"], "BLOCK")

    def test_futu_qfq_contract_is_backtest_eligible_without_a_scale_break(self) -> None:
        evidence = build_adjustment_evidence(
            symbol="AAPL",
            rows=make_rows(),
            source="futu",
            adjustment_basis="",
        )

        self.assertEqual(infer_adjustment_basis("futu"), "FORWARD_ADJUSTED_QFQ")
        self.assertEqual(evidence["status"], "PASS")
        self.assertTrue(evidence["backtest_eligible"])
        self.assertEqual(evidence["return_accounting"]["dividend_mode"], "EMBEDDED_IN_ADJUSTED_RETURN")
        self.assertTrue(evidence["return_accounting"]["double_count_protection"])
        self.assertFalse(evidence["automatic_price_rewrite"])
        self.assertFalse(evidence["paper_authorized"])
        self.assertEqual(verify_adjustment_evidence(evidence)["status"], "PASS")

    def test_official_coverage_string_without_attestation_is_blocked(self) -> None:
        evidence = build_adjustment_evidence(
            symbol="AAPL",
            rows=make_rows(),
            source="futu",
            corporate_action_coverage="OFFICIAL_EXCHANGE_FEED",
        )

        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn("official_corporate_action_attestation_missing_or_invalid", evidence["blockers"])
        self.assertEqual(verify_adjustment_evidence(evidence)["status"], "BLOCK")

    def test_verified_official_attestation_is_bound_to_adjustment_evidence(self) -> None:
        attestation = official_attestation()
        evidence = build_adjustment_evidence(
            symbol="AAPL",
            rows=make_rows(),
            source="futu",
            corporate_action_coverage="OFFICIAL_EXCHANGE_FEED",
            corporate_action_attestation=attestation,
        )

        audit = verify_adjustment_evidence(evidence)

        self.assertEqual(evidence["status"], "PASS")
        self.assertTrue(evidence["official_corporate_action_source_verified"])
        self.assertEqual(audit["status"], "PASS")
        self.assertTrue(audit["official_source_verified"])

    def test_resealed_non_official_attestation_cannot_claim_official_coverage(self) -> None:
        attestation = official_attestation()
        attestation["source_authority"] = "USER_EDITED_CSV"
        attestation.pop("attestation_hash")
        attestation["attestation_hash"] = canonical_hash(attestation)
        evidence = build_adjustment_evidence(
            symbol="AAPL",
            rows=make_rows(),
            source="futu",
            corporate_action_coverage="OFFICIAL_EXCHANGE_FEED",
            corporate_action_attestation=attestation,
        )

        self.assertEqual(evidence["status"], "BLOCK")
        self.assertEqual(verify_adjustment_evidence(evidence)["status"], "BLOCK")

    def test_synthetic_official_hash_without_source_payload_is_rejected(self) -> None:
        attestation = build_official_corporate_action_attestation(
            source_authority="OFFICIAL_EXCHANGE_FEED",
            source_name="Test Exchange Corporate Action Master",
            evidence_ref="https://example.test/corporate-actions/aapl",
            evidence_sha256="a" * 64,
            observed_at="2026-08-01T00:00:00Z",
            coverage_types=["SPLIT", "DIVIDEND", "SUSPENSION", "DELISTING"],
        )

        self.assertEqual(attestation["status"], "BLOCK")
        self.assertIn("corporate_action_source_evidence_payload_missing", attestation["blockers"])

    def test_unknown_adjustment_basis_is_not_backtest_eligible(self) -> None:
        evidence = build_adjustment_evidence(
            symbol="AAA",
            rows=make_rows(),
            source="mystery_provider",
        )

        self.assertEqual(evidence["status"], "REVIEW")
        self.assertFalse(evidence["backtest_eligible"])
        self.assertIn("adjustment_basis_unverified:UNKNOWN", evidence["blockers"])

    def test_adjusted_yahoo_total_return_contract_is_backtest_eligible(self) -> None:
        evidence = build_adjustment_evidence(
            symbol="AAPL",
            rows=make_rows(),
            source="yahoo_adjusted",
        )

        self.assertEqual(infer_adjustment_basis("yahoo_adjusted"), "FORWARD_ADJUSTED_TOTAL_RETURN")
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["return_accounting"]["dividend_mode"], "EMBEDDED_IN_ADJUSTED_RETURN")
        self.assertTrue(evidence["return_accounting"]["double_count_protection"])

    def test_matching_split_event_does_not_silently_rewrite_a_broken_series(self) -> None:
        rows = make_rows(split_index=10)
        split_date = str(rows[10]["date"])
        evidence = build_adjustment_evidence(
            symbol="AAA",
            rows=rows,
            source="futu",
            corporate_actions=[{
                "action_type": "SPLIT",
                "event_date": split_date,
                "numerator": 4,
                "denominator": 1,
                "ratio": 4,
                "provider": "yahoo",
            }],
        )

        self.assertEqual(evidence["status"], "BLOCK")
        self.assertTrue(evidence["matched_action"])
        self.assertFalse(evidence["backtest_eligible"])
        self.assertIn("price_scale_break_requires_uniform_adjustment", evidence["blockers"])

    def test_hfq_basis_is_not_cash_execution_eligible(self) -> None:
        evidence = build_adjustment_evidence(
            symbol="AAA",
            rows=make_rows(),
            source="futu",
            adjustment_basis="BACKWARD_ADJUSTED_HFQ",
        )

        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn("adjustment_basis_not_cash_executable:BACKWARD_ADJUSTED_HFQ", evidence["blockers"])

    def test_resealed_hfq_pass_cannot_bypass_cash_execution_semantics(self) -> None:
        evidence = build_adjustment_evidence(
            symbol="AAA",
            rows=make_rows(),
            source="futu",
            adjustment_basis="BACKWARD_ADJUSTED_HFQ",
        )
        evidence["status"] = "PASS"
        evidence["backtest_eligible"] = True
        evidence["blockers"] = []
        evidence.pop("evidence_hash")
        evidence["evidence_hash"] = canonical_hash(evidence)

        audit = verify_adjustment_evidence(evidence)

        self.assertEqual(audit["status"], "BLOCK")
        self.assertIn("adjustment_declared_blockers_semantic_mismatch", audit["blockers"])
        self.assertIn("adjustment_backtest_eligibility_mismatch", audit["blockers"])

    def test_explicit_accounting_requires_complete_action_coverage(self) -> None:
        evidence = build_adjustment_evidence(
            symbol="AAA",
            rows=make_rows(),
            source="test",
            adjustment_basis="SPLIT_ADJUSTED",
        )

        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn("corporate_action_coverage_incomplete:UNKNOWN", evidence["blockers"])

    def test_explicit_dividend_requires_pay_date(self) -> None:
        evidence = build_adjustment_evidence(
            symbol="AAA",
            rows=make_rows(),
            source="test",
            adjustment_basis="SPLIT_ADJUSTED",
            corporate_action_coverage="COMPLETE",
            corporate_actions=[{
                "action_type": "DIVIDEND",
                "event_date": "2025-02-14",
                "cash_amount": 0.25,
            }],
        )

        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn("dividend_pay_date_missing:2025-02-14", evidence["blockers"])

    def test_raw_series_accepts_a_declared_split_with_explicit_quantity_mode(self) -> None:
        rows = make_rows(split_index=10)
        evidence = build_adjustment_evidence(
            symbol="AAA",
            rows=rows,
            source="test",
            adjustment_basis="RAW_UNADJUSTED",
            corporate_action_coverage="COMPLETE",
            corporate_actions=[{
                "action_type": "SPLIT",
                "event_date": rows[10]["date"],
                "ratio": 4,
            }],
        )

        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["return_accounting"]["split_mode"], "EXPLICIT_QUANTITY_ADJUSTMENT")
        self.assertIn("raw_price_scale_break_accounted_by_declared_split", evidence["warnings"])

    def test_yahoo_events_are_normalized(self) -> None:
        actions = parse_yahoo_corporate_actions("AAPL", {
            "events": {
                "splits": {"split-1": {"date": 1_735_689_600, "numerator": 4, "denominator": 1, "splitRatio": "4:1"}},
                "dividends": {"div-1": {"date": 1_738_281_600, "amount": 0.25}},
            },
        })

        self.assertEqual([item["action_type"] for item in actions], ["SPLIT", "DIVIDEND"])
        self.assertEqual(actions[0]["ratio"], 4.0)
        self.assertTrue(all(item["action_id"] for item in actions))

    def test_sqlite_ledger_deduplicates_actions_and_keeps_evidence(self) -> None:
        clock = iter([1000, 2000])
        with tempfile.TemporaryDirectory() as temporary:
            ledger = CorporateActionLedger(Path(temporary) / "actions.sqlite", lambda: next(clock))
            action = {
                "action_type": "DIVIDEND",
                "event_date": "2025-02-14",
                "cash_amount": 0.25,
            }
            evidence = build_adjustment_evidence(symbol="AAPL", rows=make_rows(), source="futu")
            ledger.record(symbol="AAPL", provider="yahoo", actions=[action], evidence=evidence)
            ledger.record(symbol="AAPL", provider="yahoo", actions=[action], evidence=evidence)

            self.assertEqual(len(ledger.actions("AAPL")), 1)
            self.assertEqual(ledger.latest_evidence("AAPL")["evidence_hash"], evidence["evidence_hash"])
            self.assertEqual(ledger.summary()["action_count"], 1)


if __name__ == "__main__":
    unittest.main()
