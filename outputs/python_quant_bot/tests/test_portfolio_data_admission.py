from __future__ import annotations

from datetime import date, datetime, timedelta
import hashlib
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.corporate_action_ledger import (
    build_adjustment_evidence,
    build_corporate_action_source_evidence,
    build_official_corporate_action_attestation,
)
from exchange_terminal.services.market_data_revision_ledger import (
    build_cross_source_evidence,
    build_market_data_snapshot,
)
from exchange_terminal.services.portfolio_backtest import portfolio_revision_evidence_hash
from exchange_terminal.services.portfolio_data_admission import (
    build_portfolio_data_admission_audit,
    canonical_hash,
    verify_portfolio_data_admission_audit,
)
from exchange_terminal.services.portfolio_universe import (
    build_membership_source_evidence,
    build_point_in_time_universe_contract,
    build_static_research_universe_contract,
)
from exchange_terminal.services.provider_governance import (
    build_provider_approval_receipt,
    build_provider_governance_contract,
    build_provider_review_record,
    build_unassessed_provider_governance_contract,
)


CANDIDATE_HASH = "c" * 64
DATASET_HASH = "d" * 64
REPORT_HASH = "e" * 64
GENERATED_AT = "2026-08-03T00:00:00Z"
GENERATED_AT_MS = int(datetime.fromisoformat(GENERATED_AT.replace("Z", "+00:00")).timestamp() * 1000)


def market_rows(*, stale_days: int = 0, count: int = 40) -> list[dict[str, object]]:
    first = date.today() - timedelta(days=stale_days + count - 1)
    return [
        {
            "date": (first + timedelta(days=index)).isoformat(),
            "open": 100.0 + index,
            "high": 101.0 + index,
            "low": 99.0 + index,
            "close": 100.5 + index,
            "volume": 1_000_000 + index,
            "complete": True,
        }
        for index in range(count)
    ]


def official_attestation(symbol: str) -> dict[str, object]:
    evidence_ref = f"https://example.test/corporate-actions/{symbol.lower()}"
    source = build_corporate_action_source_evidence(
        source_authority="OFFICIAL_EXCHANGE_FEED",
        source_name="Test Exchange Corporate Action Master",
        evidence_ref=evidence_ref,
        source_document_sha256=hashlib.sha256(f"{symbol}-official-actions-document".encode("utf-8")).hexdigest(),
        observed_at="2026-08-01T00:00:00Z",
        coverage_types=["SPLIT", "DIVIDEND", "SUSPENSION", "DELISTING"],
        record_count=0,
    )
    return build_official_corporate_action_attestation(
        source_authority="OFFICIAL_EXCHANGE_FEED",
        source_name="Test Exchange Corporate Action Master",
        evidence_ref=evidence_ref,
        evidence_sha256=str(source["evidence_sha256"]),
        observed_at="2026-08-01T00:00:00Z",
        coverage_types=["SPLIT", "DIVIDEND", "SUSPENSION", "DELISTING"],
        evidence_payload=source,
    )


def adjustment(symbol: str, *, official: bool = False) -> dict[str, object]:
    return build_adjustment_evidence(
        symbol=symbol,
        rows=market_rows(),
        source="futu",
        corporate_action_coverage="OFFICIAL_EXCHANGE_FEED" if official else "",
        corporate_action_attestation=official_attestation(symbol) if official else None,
    )


def revision(symbol: str, *, stale_days: int = 0) -> dict[str, object]:
    rows = market_rows(stale_days=stale_days)
    primary = build_market_data_snapshot(
        symbol=symbol,
        provider="futu",
        rows=rows,
        role="PROVIDER_OBSERVATION",
        adjustment_basis="FORWARD_ADJUSTED_QFQ",
    )
    secondary = build_market_data_snapshot(
        symbol=symbol,
        provider="yahoo_adjusted",
        rows=rows,
        role="PROVIDER_OBSERVATION",
        adjustment_basis="FORWARD_ADJUSTED_QFQ",
    )
    cross_source = build_cross_source_evidence(primary, secondary, required_overlap=30)
    if stale_days:
        cross_source["status"] = "REVIEW"
        cross_source["latest_overlap_gap_days"] = stale_days
        cross_source["warnings"] = [f"cross_source_recent_overlap_stale:{stale_days}d"]
        cross_source.pop("evidence_hash")
        cross_source["evidence_hash"] = canonical_hash(cross_source)
    payload = {
        "status": "PASS",
        "accepted_cache": {
            "status": "PASS",
            "blockers": [],
            "current": {"snapshot_hash": primary["snapshot_hash"]},
        },
        "backtest_dataset": {
            "status": "PASS",
            "blockers": [],
            "current": {"snapshot_hash": secondary["snapshot_hash"]},
        },
        "cross_source": [cross_source],
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["evidence_hash"] = portfolio_revision_evidence_hash(payload)
    return payload


def provider_review(provider: str) -> dict[str, object]:
    terms_ref = f"https://example.test/{provider}/terms"
    terms_sha256 = hashlib.sha256(f"{provider}-terms".encode("utf-8")).hexdigest()
    receipt = build_provider_approval_receipt(
        provider_id=provider,
        terms_ref=terms_ref,
        terms_sha256=terms_sha256,
        terms_version="2026-01",
        reviewed_at="2026-07-01T00:00:00Z",
        review_expires_at="2027-07-01T00:00:00Z",
        local_storage_status="ALLOWED",
        redistribution_status="PROHIBITED",
        quota_model="FIXED_WINDOW",
        request_limit=100,
        quota_window_seconds=60,
        retry_policy_id="bounded-exponential-v1",
        reviewer_id="test-compliance-reviewer",
    )
    return build_provider_review_record(
        provider_id=provider,
        terms_ref=terms_ref,
        terms_sha256=terms_sha256,
        terms_version="2026-01",
        reviewed_at="2026-07-01T00:00:00Z",
        review_expires_at="2027-07-01T00:00:00Z",
        local_storage_status="ALLOWED",
        redistribution_status="PROHIBITED",
        quota_model="FIXED_WINDOW",
        request_limit=100,
        quota_window_seconds=60,
        retry_policy_id="bounded-exponential-v1",
        reviewer_id="test-compliance-reviewer",
        approval_receipt=receipt,
        approval_receipt_sha256=str(receipt["receipt_hash"]),
        assessed_at=GENERATED_AT,
    )


def static_universe() -> dict[str, object]:
    return build_static_research_universe_contract(
        benchmark_symbol="SPY",
        tradable_symbols=["AAA", "BBB"],
        declared_at=GENERATED_AT,
        selection_basis="TEST_STATIC_WATCHLIST",
    )


def point_in_time_universe() -> dict[str, object]:
    records = []
    for symbol in ("AAA", "BBB"):
        evidence_ref = f"https://example.test/index/{symbol.lower()}"
        evidence = build_membership_source_evidence(
            symbol=symbol,
            effective_from="2025-01-02",
            effective_to="",
            source_authority="OFFICIAL_INDEX_PROVIDER",
            source_name="Official Test Index",
            evidence_ref=evidence_ref,
            source_document_sha256=hashlib.sha256(f"{symbol}-membership-document".encode("utf-8")).hexdigest(),
            evidence_published_at="2024-12-01T00:00:00Z",
            retrieved_at="2024-12-02T00:00:00Z",
        )
        records.append({
            "symbol": symbol,
            "effective_from": "2025-01-02",
            "effective_to": "",
            "source_authority": "OFFICIAL_INDEX_PROVIDER",
            "source_name": "Official Test Index",
            "evidence_ref": evidence_ref,
            "evidence_sha256": evidence["evidence_sha256"],
            "evidence_published_at": "2024-12-01T00:00:00Z",
            "evidence_payload": evidence,
        })
    return build_point_in_time_universe_contract(
        benchmark_symbol="SPY",
        tradable_symbols=["AAA", "BBB"],
        declared_at="2025-01-01T00:00:00Z",
        selection_basis="OFFICIAL_TEST_INDEX",
        selection_rule_id="official-test-index-v1",
        coverage_start="2025-01-02",
        coverage_end="2026-08-01",
        membership_records=records,
    )


def inputs() -> dict[str, object]:
    symbols = ["AAA", "BBB"]
    candidate = {
        "candidate_hash": CANDIDATE_HASH,
        "dataset_hash": DATASET_HASH,
        "dataset_symbols": symbols,
        "research_report_hash": REPORT_HASH,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    report = {
        "batch_run_hash": REPORT_HASH,
        "frozen_candidate": {"candidate_hash": CANDIDATE_HASH},
        "dataset_manifest": {
            "status": "PASS",
            "symbols": symbols,
            "data_hash": DATASET_HASH,
            "adjustment_evidence": {symbol: adjustment(symbol) for symbol in symbols},
            "data_revision_evidence": {symbol: revision(symbol) for symbol in symbols},
        },
        "universe_contract": static_universe(),
        "provider_governance": build_unassessed_provider_governance_contract(
            provider_ids=["futu", "yahoo"],
            generated_at=GENERATED_AT,
        ),
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {
        "generated_at": GENERATED_AT_MS,
        "active_status": "PASS",
        "candidate": candidate,
        "report": report,
        "candidate_file": "candidate.json",
        "candidate_file_sha256": "f" * 64,
        "report_file": "report.json",
        "report_file_sha256": "a" * 64,
        "expected_report_file_sha256": "a" * 64,
    }


class PortfolioDataAdmissionTests(unittest.TestCase):
    def test_malformed_audit_fails_closed_without_raising(self) -> None:
        audit = verify_portfolio_data_admission_audit([])

        self.assertEqual(audit["status"], "BLOCK")

    def test_research_ready_does_not_imply_paper_data_admission(self) -> None:
        payload = build_portfolio_data_admission_audit(**inputs())

        self.assertEqual(payload["status"], "AUDIT_COMPLETE")
        self.assertEqual(payload["internal_research_data_status"], "READY_WITH_LIMITATIONS")
        self.assertEqual(payload["paper_data_admission_status"], "BLOCK")
        self.assertEqual(payload["live_data_admission_status"], "BLOCK")
        self.assertIn("POINT_IN_TIME_UNIVERSE", payload["admission_blockers"])
        self.assertIn("OFFICIAL_CORPORATE_ACTION_MASTER", payload["admission_blockers"])
        self.assertEqual(verify_portfolio_data_admission_audit(payload)["status"], "PASS")

    def test_stale_cross_source_evidence_names_the_affected_symbol(self) -> None:
        values = inputs()
        values["report"]["dataset_manifest"]["data_revision_evidence"]["BBB"] = revision(
            "BBB",
            stale_days=30,
        )

        payload = build_portfolio_data_admission_audit(**values)
        requirement = next(
            item for item in payload["requirements"]
            if item["gate_id"] == "RECENT_INDEPENDENT_SOURCE_OVERLAP"
        )

        self.assertEqual(requirement["status"], "BLOCK")
        self.assertEqual(requirement["affected_symbols"], ["BBB"])

    def test_complete_verified_evidence_only_reaches_manual_review(self) -> None:
        values = inputs()
        report = values["report"]
        report["universe_contract"] = point_in_time_universe()
        report["provider_governance"] = build_provider_governance_contract(
            provider_ids=["futu", "yahoo"],
            reviews=[provider_review("futu"), provider_review("yahoo")],
            generated_at=GENERATED_AT,
        )
        report["dataset_manifest"]["adjustment_evidence"] = {
            symbol: adjustment(symbol, official=True)
            for symbol in ["AAA", "BBB"]
        }

        payload = build_portfolio_data_admission_audit(**values)

        self.assertEqual(payload["paper_data_admission_status"], "READY_FOR_MANUAL_REVIEW")
        self.assertEqual(verify_portfolio_data_admission_audit(payload)["status"], "PASS")
        self.assertFalse(payload["automatic_paper_activation_allowed"])
        self.assertFalse(payload["paper_authorized"])

    def test_bare_claims_cannot_elevate_paper_admission(self) -> None:
        values = inputs()
        report = values["report"]
        report["universe_contract"] = {
            "historical_membership_verified": True,
            "point_in_time_constituents": True,
            "survivorship_bias_status": "CONTROLLED_BY_POINT_IN_TIME_MEMBERSHIP",
        }
        report["provider_governance"] = {
            "license_review_status": "PASS",
            "rate_limit_policy_status": "PASS",
        }
        for evidence in report["dataset_manifest"]["adjustment_evidence"].values():
            evidence["corporate_action_coverage"] = "OFFICIAL_EXCHANGE_FEED"

        payload = build_portfolio_data_admission_audit(**values)

        self.assertEqual(payload["paper_data_admission_status"], "BLOCK")
        self.assertEqual(payload["internal_research_data_status"], "BLOCK")
        self.assertEqual(verify_portfolio_data_admission_audit(payload)["status"], "PASS")

    def test_resealed_admission_status_tampering_is_detected(self) -> None:
        payload = build_portfolio_data_admission_audit(**inputs())
        payload["paper_data_admission_status"] = "READY_FOR_MANUAL_REVIEW"
        payload.pop("audit_hash")
        payload["audit_hash"] = canonical_hash(payload)

        audit = verify_portfolio_data_admission_audit(payload)

        self.assertEqual(audit["status"], "BLOCK")
        self.assertIn("paper_data_admission_status_semantic_mismatch", audit["blockers"])

    def test_source_tampering_and_non_boolean_authority_block_audit(self) -> None:
        values = inputs()
        values["expected_report_file_sha256"] = "b" * 64
        values["report"]["paper_authorized"] = "false"

        payload = build_portfolio_data_admission_audit(**values)

        self.assertEqual(payload["status"], "AUDIT_BLOCKED")
        self.assertIn("research_file_hash_matches_receipt", payload["blockers"])
        self.assertTrue(any(item.startswith("execution_authority:") for item in payload["blockers"]))


if __name__ == "__main__":
    unittest.main()
