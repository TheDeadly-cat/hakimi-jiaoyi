from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.portfolio_universe import (
    build_membership_source_evidence,
    build_point_in_time_universe_contract,
    build_static_research_universe_contract,
    derive_universe_subset_contract,
    eligible_symbols_on,
    verify_universe_contract,
)


def canonical_hash(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def membership(
    symbol: str,
    effective_from: str,
    effective_to: str = "",
    *,
    authority: str = "OFFICIAL_INDEX_PROVIDER",
) -> dict[str, object]:
    evidence_ref = f"https://example.test/membership/{symbol}/{effective_from}"
    evidence = build_membership_source_evidence(
        symbol=symbol,
        effective_from=effective_from,
        effective_to=effective_to,
        source_authority=authority,
        source_name="Official Test Index",
        evidence_ref=evidence_ref,
        source_document_sha256=hashlib.sha256(f"document:{symbol}:{effective_from}".encode("utf-8")).hexdigest(),
        evidence_published_at="2023-12-01T00:00:00Z",
        retrieved_at="2023-12-02T00:00:00Z",
    )
    return {
        "symbol": symbol,
        "effective_from": effective_from,
        "effective_to": effective_to,
        "source_authority": authority,
        "source_name": "Official Test Index",
        "evidence_ref": evidence_ref,
        "evidence_sha256": evidence["evidence_sha256"],
        "evidence_published_at": "2023-12-01T00:00:00Z",
        "evidence_payload": evidence,
    }


def verified_contract() -> dict[str, object]:
    return build_point_in_time_universe_contract(
        benchmark_symbol="SPY",
        tradable_symbols=["AAA", "BBB"],
        declared_at="2024-01-01T00:00:00Z",
        selection_basis="OFFICIAL_TEST_INDEX",
        selection_rule_id="official-test-index-v1",
        coverage_start="2024-01-02",
        coverage_end="2024-12-31",
        membership_records=[
            membership("AAA", "2024-01-02", "2024-06-30"),
            membership("BBB", "2024-04-01"),
        ],
    )


class PortfolioUniverseTests(unittest.TestCase):
    def test_malformed_contract_types_fail_closed_without_raising(self) -> None:
        audit = verify_universe_contract({
            "blockers": 1,
            "tradable_symbols": 2,
            "membership_records": 3,
        })

        self.assertEqual(audit["status"], "BLOCK")
        self.assertIn("universe_declared_blockers_type_invalid", audit["blockers"])

    def test_static_watchlist_is_integrity_checked_but_not_historically_verified(self) -> None:
        contract = build_static_research_universe_contract(
            benchmark_symbol="SPY",
            tradable_symbols=["AAA", "BBB"],
            declared_at="2026-08-01T00:00:00Z",
            selection_basis="CURRENT_WATCHLIST",
        )

        audit = verify_universe_contract(contract)
        eligibility = eligible_symbols_on(contract, "2024-05-01", ["AAA", "BBB"])

        self.assertEqual(audit["status"], "PASS")
        self.assertFalse(audit["historical_membership_verified"])
        self.assertEqual(contract["survivorship_bias_status"], "UNCONTROLLED")
        self.assertEqual(eligibility["eligible_symbols"], ["AAA", "BBB"])

    def test_verified_contract_changes_eligibility_by_effective_date(self) -> None:
        contract = verified_contract()

        march = eligible_symbols_on(contract, "2024-03-01", ["AAA", "BBB"])
        may = eligible_symbols_on(contract, "2024-05-01", ["AAA", "BBB"])
        july = eligible_symbols_on(contract, "2024-07-01", ["AAA", "BBB"])

        self.assertEqual(contract["status"], "POINT_IN_TIME_VERIFIED")
        self.assertEqual(march["eligible_symbols"], ["AAA"])
        self.assertEqual(may["eligible_symbols"], ["AAA", "BBB"])
        self.assertEqual(july["eligible_symbols"], ["BBB"])
        self.assertTrue(july["historical_membership_verified"])

    def test_overlapping_or_non_authoritative_membership_blocks_verification(self) -> None:
        contract = build_point_in_time_universe_contract(
            benchmark_symbol="SPY",
            tradable_symbols=["AAA"],
            declared_at="2024-01-01T00:00:00Z",
            selection_basis="UNVERIFIED_LIST",
            selection_rule_id="test-v1",
            coverage_start="2024-01-02",
            coverage_end="2024-12-31",
            membership_records=[
                membership("AAA", "2024-01-02", "2024-08-01", authority="USER_EDITED_CSV"),
                membership("AAA", "2024-07-01"),
            ],
        )

        self.assertEqual(contract["status"], "BLOCK")
        self.assertTrue(any(item.startswith("membership_source_not_authoritative") for item in contract["blockers"]))
        self.assertTrue(any(item.startswith("membership_intervals_overlap") for item in contract["blockers"]))
        self.assertFalse(contract["historical_membership_verified"])

    def test_contract_and_membership_tampering_is_detected(self) -> None:
        contract = verified_contract()
        tampered = {**contract, "coverage_end": "2025-12-31"}

        audit = verify_universe_contract(tampered)

        self.assertEqual(audit["status"], "BLOCK")
        self.assertIn("universe_contract_hash_mismatch", audit["blockers"])
        self.assertFalse(audit["paper_authorized"])
        self.assertFalse(audit["live_order_allowed"])

    def test_resealed_non_authoritative_membership_is_rejected(self) -> None:
        contract = verified_contract()
        contract["membership_records"][0]["source_authority"] = "USER_EDITED_CSV"
        contract["membership_records"][0]["membership_id"] = canonical_hash({
            key: value
            for key, value in contract["membership_records"][0].items()
            if key != "membership_id"
        })
        contract["membership_hash"] = canonical_hash(contract["membership_records"])
        contract.pop("contract_hash")
        contract["contract_hash"] = canonical_hash(contract)

        audit = verify_universe_contract(contract)

        self.assertEqual(audit["status"], "BLOCK")
        self.assertTrue(any(
            item.startswith("universe_semantic_validation_failed:membership_source_not_authoritative")
            for item in audit["blockers"]
        ))

    def test_synthetic_membership_hash_without_source_payload_is_rejected(self) -> None:
        record = membership("AAA", "2024-01-02")
        record.pop("evidence_payload")
        record["evidence_sha256"] = "2" * 64

        contract = build_point_in_time_universe_contract(
            benchmark_symbol="SPY",
            tradable_symbols=["AAA"],
            declared_at="2024-01-01T00:00:00Z",
            selection_basis="CLAIMED_OFFICIAL_INDEX",
            selection_rule_id="fake-v1",
            coverage_start="2024-01-02",
            coverage_end="2024-01-02",
            membership_records=[record],
        )

        self.assertEqual(contract["status"], "BLOCK")
        self.assertTrue(any(
            item.startswith("membership_evidence_payload_missing")
            for item in contract["blockers"]
        ))

    def test_membership_evidence_published_after_effective_date_is_rejected(self) -> None:
        late = membership("AAA", "2024-01-02")
        late["evidence_published_at"] = "2024-01-03T00:00:00Z"

        contract = build_point_in_time_universe_contract(
            benchmark_symbol="SPY",
            tradable_symbols=["AAA"],
            declared_at="2024-01-01T00:00:00Z",
            selection_basis="OFFICIAL_TEST_INDEX",
            selection_rule_id="official-test-index-v1",
            coverage_start="2024-01-02",
            coverage_end="2024-12-31",
            membership_records=[late],
        )

        self.assertEqual(contract["status"], "BLOCK")
        self.assertTrue(any(
            item.startswith("membership_evidence_available_after_effective_date")
            for item in contract["blockers"]
        ))

    def test_resealed_string_membership_flag_is_rejected(self) -> None:
        contract = build_static_research_universe_contract(
            benchmark_symbol="SPY",
            tradable_symbols=["AAA", "BBB"],
            declared_at="2026-08-01T00:00:00Z",
            selection_basis="CURRENT_WATCHLIST",
        )
        contract["historical_membership_verified"] = "false"
        contract.pop("contract_hash")
        contract["contract_hash"] = canonical_hash(contract)

        audit = verify_universe_contract(contract)

        self.assertEqual(audit["status"], "BLOCK")
        self.assertIn("universe_historical_membership_flag_invalid", audit["blockers"])

    def test_requested_symbol_outside_contract_fails_closed(self) -> None:
        result = eligible_symbols_on(verified_contract(), "2024-05-01", ["AAA", "CCC"])

        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["eligible_symbols"], [])
        self.assertIn("requested_symbols_outside_universe:CCC", result["blockers"])

    def test_static_subset_derivation_preserves_parent_lineage(self) -> None:
        parent = build_static_research_universe_contract(
            benchmark_symbol="SPY",
            tradable_symbols=["AAA", "BBB", "CCC"],
            declared_at="2026-08-01T00:00:00Z",
            selection_basis="CURRENT_WATCHLIST",
        )

        child = derive_universe_subset_contract(
            parent,
            tradable_symbols=["AAA", "CCC"],
            derivation_purpose="ROBUSTNESS_ABLATION_WITHOUT_BBB",
        )

        self.assertEqual(verify_universe_contract(child)["status"], "PASS")
        self.assertEqual(child["tradable_symbols"], ["AAA", "CCC"])
        self.assertEqual(child["removed_symbols"], ["BBB"])
        self.assertEqual(child["parent_contract_hash"], parent["contract_hash"])
        self.assertFalse(child["historical_membership_verified"])

    def test_subset_derivation_rejects_symbol_not_in_parent(self) -> None:
        parent = build_static_research_universe_contract(
            benchmark_symbol="SPY",
            tradable_symbols=["AAA", "BBB"],
            declared_at="2026-08-01T00:00:00Z",
            selection_basis="CURRENT_WATCHLIST",
        )

        child = derive_universe_subset_contract(
            parent,
            tradable_symbols=["AAA", "CCC"],
            derivation_purpose="INVALID_EXPANSION",
        )

        self.assertEqual(child["status"], "BLOCK")
        self.assertIn("subset_symbols_outside_parent:CCC", child["blockers"])
        self.assertEqual(eligible_symbols_on(child, "2024-05-01", ["AAA"])["status"], "BLOCK")

    def test_subset_lineage_tampering_is_detected(self) -> None:
        parent = build_static_research_universe_contract(
            benchmark_symbol="SPY",
            tradable_symbols=["AAA", "BBB"],
            declared_at="2026-08-01T00:00:00Z",
            selection_basis="CURRENT_WATCHLIST",
        )
        child = derive_universe_subset_contract(
            parent,
            tradable_symbols=["AAA"],
            derivation_purpose="ROBUSTNESS_ABLATION_WITHOUT_BBB",
        )
        tampered = {**child, "removed_symbols": []}

        audit = verify_universe_contract(tampered)

        self.assertEqual(audit["status"], "BLOCK")
        self.assertIn("universe_contract_hash_mismatch", audit["blockers"])
        self.assertIn("universe_removed_symbols_mismatch", audit["blockers"])


if __name__ == "__main__":
    unittest.main()
