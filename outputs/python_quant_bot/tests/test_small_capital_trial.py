from __future__ import annotations

import json
import hashlib
import sys
import unittest
from decimal import Decimal
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.small_capital_trial import build_small_capital_trial_plan
from exchange_terminal.services.instrument_rules import build_okx_public_spot_rules
from exchange_terminal.services.public_order_book import build_okx_public_order_book


NOW_MS = 1_000_100


def instrument_payload(
    tick_size: str = "0.1",
    lot_size: str = "0.00000001",
    minimum_size: str = "0.00001",
) -> dict[str, object]:
    return {
        "code": "0",
        "data": [{
            "instType": "SPOT",
            "instId": "BTC-USDT",
            "baseCcy": "BTC",
            "quoteCcy": "USDT",
            "state": "live",
            "tickSz": tick_size,
            "lotSz": lot_size,
            "minSz": minimum_size,
            "ctVal": "",
            "ctMult": "",
            "ctValCcy": "",
            "listTime": "1611907686000",
            "contTdSwTime": "",
            "expTime": "",
            "groupId": "12",
            "upcChg": [],
        }],
    }


def verified_instrument_rules(tick_size: str = "0.1") -> dict[str, object]:
    return build_okx_public_spot_rules(
        instrument_payload(tick_size),
        symbol="BTC-USDT",
        captured_at_ms=1_000_000,
    )


def verified_order_book(
    *,
    asks: list[list[str]] | None = None,
    bids: list[list[str]] | None = None,
) -> dict[str, object]:
    return build_okx_public_order_book(
        {
            "code": "0",
            "msg": "",
            "data": [{
                "asks": asks if asks is not None else [
                    ["100", "0.05", "0", "2"],
                    ["101", "0.06", "0", "3"],
                    ["102", "0.20", "0", "4"],
                ],
                "bids": bids if bids is not None else [
                    ["99", "0.20", "0", "5"],
                    ["98", "0.30", "0", "6"],
                ],
                "ts": "1000000",
                "seqId": 42,
            }],
        },
        symbol="BTC-USDT",
        observed_at_ms=NOW_MS,
    )


def safe_inputs() -> dict[str, object]:
    return {
        "runtime_read_only": True,
        "live_trading_hard_block": True,
        "symbol": "BTC-USDT",
        "current_time_ms": NOW_MS,
        "risk_snapshot": {
            "live_trading_hard_block": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "market_truth": {
            "schema_version": "market-data-truth-v1",
            "status": "READY",
            "mode": "REALTIME_READY",
            "symbol": "BTC-USDT",
            "evidence_scope": "FULL_SNAPSHOT",
            "snapshot_available": True,
            "snapshot_id": "market-snapshot-1",
            "observation_current": True,
            "max_observation_age_ms": 15_000,
            "realtime_ready": True,
            "read_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
            "execution_usable": False,
            "research_usable": True,
            "quote": {
                "reference_price": {
                    "status": "PASS",
                    "value": "99",
                    "kind": "LAST_TRADE_REFERENCE",
                    "source": "okx",
                    "timestamp_ms": 1_000_000,
                    "snapshot_id": "market-snapshot-1",
                    "in_memory_only": True,
                    "client_price_used": False,
                },
                "sizing_reference": {
                    "status": "PASS",
                    "value": "100",
                    "kind": "PUBLIC_BEST_ASK_REFERENCE",
                    "available_size": "1",
                    "size_basis": "BASE_CURRENCY",
                    "source": "okx",
                    "timestamp_ms": 1_000_000,
                    "snapshot_id": "market-snapshot-1",
                    "depth_levels": 1,
                    "is_executable_quote": False,
                    "in_memory_only": True,
                    "client_price_used": False,
                    "fallback_used": False,
                    "cache_regression": False,
                },
            },
        },
        "forward_validation": {
            "read_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
            "incremental_observation": {
                "latest_completed_bar": {"known": True},
            },
        },
    }


def verified_capabilities() -> dict[str, bool]:
    return {
        "dedicated_subaccount_verified": True,
        "restricted_api_key_verified": True,
        "ip_allowlist_verified": True,
        "withdrawal_disabled_verified": True,
        "signer_isolated_verified": True,
        "independent_circuit_breaker_verified": True,
        "manual_reset_verified": True,
        "reconciliation_verified": True,
    }


class SmallCapitalTrialPlanTests(unittest.TestCase):
    def test_missing_external_evidence_stays_non_executable(self) -> None:
        plan = build_small_capital_trial_plan(**safe_inputs())

        self.assertEqual(plan["schema_version"], "small-capital-planning-v3")
        self.assertEqual(plan["mode"], "PLAN_ONLY_NO_EXECUTION")
        self.assertEqual(plan["status"], "NEEDS_EVIDENCE")
        self.assertEqual(plan["budget"], {"currency": "USD", "min_usd": 100.0, "max_usd": 200.0})
        self.assertEqual(plan["guardrails"]["single_order_usd"], {"min": 10.0, "max": 20.0})
        self.assertEqual(plan["guardrails"]["daily_loss_usd"], {"min": 2.0, "max": 4.0})
        self.assertEqual(plan["fee_schedule"]["status"], "NOT_CHECKED")
        self.assertEqual(plan["instrument_rules"]["status"], "NOT_CHECKED")
        self.assertFalse(plan["execution_allowed"])
        self.assertEqual(
            plan["permissions"],
            {
                "planning_only": True,
                "runtime_mutations_allowed": False,
                "deposit_allowed": False,
                "order_submission_allowed": False,
                "execution_allowed": False,
                "paper_authorized": False,
                "live_order_allowed": False,
                "live_trading_hard_block": True,
            },
        )

    def test_verified_public_rules_bind_plan_hash_but_account_fee_stays_unverified(self) -> None:
        first = build_small_capital_trial_plan(
            **safe_inputs(),
            instrument_rules_evidence=verified_instrument_rules("0.1"),
            capabilities=verified_capabilities(),
        )
        second = build_small_capital_trial_plan(
            **safe_inputs(),
            instrument_rules_evidence=verified_instrument_rules("0.01"),
            capabilities=verified_capabilities(),
        )

        checks = {check["id"]: check for check in first["checks"]}
        self.assertEqual(first["status"], "NEEDS_EVIDENCE")
        self.assertEqual(checks["instrument_rules"]["status"], "PASS")
        self.assertEqual(checks["fee_evidence"]["status"], "NOT_CHECKED")
        self.assertEqual(first["instrument_rules"]["tick_size"], "0.1")
        self.assertEqual(first["instrument_rules"]["minimum_order_size"], "0.00001")
        self.assertFalse(first["instrument_rules"]["verification"]["minimum_cost_verified"])
        self.assertEqual(first["quantity_preview"]["status"], "PREVIEW_ONLY")
        self.assertEqual(first["quantity_preview"]["rows"][0]["quantity_floor"], "0.1")
        self.assertEqual(first["quantity_preview"]["rows"][1]["quantity_floor"], "0.2")
        self.assertEqual(first["quantity_preview"]["price_evidence"]["kind"], "PUBLIC_BEST_ASK_REFERENCE")
        self.assertEqual(first["quantity_preview"]["rows"][0]["risk_check_buffer_quote"], "0.5")
        self.assertEqual(first["quantity_preview"]["rows"][1]["planning_quote_availability"], "21")
        self.assertTrue(first["quantity_preview"]["rows"][0]["top_of_book_reference_covers_quantity"])
        self.assertFalse(first["quantity_preview"]["risk_check_buffer"]["fee_estimate"])
        self.assertFalse(first["quantity_preview"]["budget_basis"]["usd_equivalence_verified"])
        self.assertEqual(first["microstructure_truth"]["status"], "NOT_CHECKED")
        self.assertFalse(first["quantity_preview"]["rows"][0]["minimum_cost_checked"])
        self.assertFalse(first["quantity_preview"]["execution_allowed"])
        self.assertNotEqual(first["plan_hash"], second["plan_hash"])
        self.assertFalse(first["permissions"]["order_submission_allowed"])
        self.assertFalse(first["permissions"]["paper_authorized"])
        self.assertFalse(first["permissions"]["live_order_allowed"])

    def test_stock_symbol_keeps_public_okx_rules_not_applicable(self) -> None:
        inputs = safe_inputs()
        inputs["symbol"] = "AAPL"
        inputs["market_truth"] = {**inputs["market_truth"], "symbol": "AAPL"}
        plan = build_small_capital_trial_plan(
            **inputs,
            capabilities=verified_capabilities(),
        )

        checks = {check["id"]: check for check in plan["checks"]}
        self.assertEqual(plan["status"], "NEEDS_EVIDENCE")
        self.assertEqual(plan["instrument_rules"]["status"], "NOT_APPLICABLE")
        self.assertEqual(checks["instrument_rules"]["status"], "NOT_CHECKED")
        self.assertFalse(plan["execution_allowed"])
        self.assertFalse(plan["live_order_allowed"])

    def test_quantity_preview_floors_to_lot_without_rounding_up_to_minimum(self) -> None:
        rules = build_okx_public_spot_rules(
            instrument_payload(lot_size="0.001", minimum_size="0.001"),
            symbol="BTC-USDT",
            captured_at_ms=1_000_000,
        )
        inputs = safe_inputs()
        inputs["market_truth"] = {
            **inputs["market_truth"],
            "quote": {
                **inputs["market_truth"]["quote"],
                "sizing_reference": {
                    **inputs["market_truth"]["quote"]["sizing_reference"],
                    "value": "19000",
                },
            },
        }
        plan = build_small_capital_trial_plan(
            **inputs,
            instrument_rules_evidence=rules,
            capabilities=verified_capabilities(),
        )

        preview = plan["quantity_preview"]
        self.assertEqual(preview["status"], "BELOW_MIN_SIZE")
        self.assertEqual(preview["rows"][0]["quantity_floor"], "0")
        self.assertFalse(preview["rows"][0]["minimum_order_size_met"])
        self.assertEqual(preview["rows"][1]["quantity_floor"], "0.001")
        self.assertTrue(preview["rows"][1]["minimum_order_size_met"])
        self.assertTrue(all(row["within_quote_budget"] for row in preview["rows"]))
        self.assertTrue(all(row["executable"] is False for row in preview["rows"]))

    def test_quantity_preview_does_not_round_a_high_precision_boundary_up(self) -> None:
        rules = build_okx_public_spot_rules(
            instrument_payload(lot_size="1", minimum_size="1"),
            symbol="BTC-USDT",
            captured_at_ms=1_000_000,
        )
        inputs = safe_inputs()
        inputs["market_truth"] = {
            **inputs["market_truth"],
            "quote": {
                **inputs["market_truth"]["quote"],
                "sizing_reference": {
                    **inputs["market_truth"]["quote"]["sizing_reference"],
                    "value": "10.0000000000000000000000000001",
                },
            },
        }

        preview = build_small_capital_trial_plan(
            **inputs,
            instrument_rules_evidence=rules,
            capabilities=verified_capabilities(),
        )["quantity_preview"]

        self.assertEqual(preview["status"], "BELOW_MIN_SIZE")
        self.assertEqual(preview["rows"][0]["lot_steps"], "0")
        self.assertEqual(preview["rows"][0]["quantity_floor"], "0")
        self.assertEqual(preview["rows"][1]["lot_steps"], "1")
        for row in preview["rows"]:
            self.assertLessEqual(
                Decimal(row["reference_notional"]),
                Decimal(row["budget_quote_amount"]),
            )
            self.assertTrue(row["within_quote_budget"])

    def test_claimed_realtime_market_with_client_price_is_blocked(self) -> None:
        inputs = safe_inputs()
        inputs["market_truth"] = {
            **inputs["market_truth"],
            "quote": {
                **inputs["market_truth"]["quote"],
                "sizing_reference": {
                    **inputs["market_truth"]["quote"]["sizing_reference"],
                    "client_price_used": True,
                },
            },
        }
        plan = build_small_capital_trial_plan(
            **inputs,
            instrument_rules_evidence=verified_instrument_rules(),
            capabilities=verified_capabilities(),
        )

        self.assertEqual(plan["status"], "BLOCK")
        self.assertEqual(plan["quantity_preview"]["status"], "BLOCK")
        self.assertFalse(plan["quantity_preview"]["execution_allowed"])
        self.assertFalse(plan["paper_authorized"])
        self.assertFalse(plan["live_order_allowed"])

    def test_valid_last_without_public_best_ask_stays_needs_evidence(self) -> None:
        inputs = safe_inputs()
        inputs["market_truth"] = {
            **inputs["market_truth"],
            "quote": {
                **inputs["market_truth"]["quote"],
                "sizing_reference": {
                    **inputs["market_truth"]["quote"]["sizing_reference"],
                    "status": "NOT_CHECKED",
                    "value": "",
                    "available_size": "",
                },
            },
        }

        plan = build_small_capital_trial_plan(
            **inputs,
            instrument_rules_evidence=verified_instrument_rules(),
            capabilities=verified_capabilities(),
        )

        self.assertEqual(plan["quantity_preview"]["status"], "NEEDS_EVIDENCE")
        self.assertEqual(plan["quantity_preview"]["rows"], [])
        self.assertIn("public_best_ask_not_checked", plan["quantity_preview"]["blockers"])
        self.assertFalse(plan["execution_allowed"])

    def test_multi_level_depth_preview_reports_vwap_and_partial_coverage_without_execution(self) -> None:
        full = build_small_capital_trial_plan(
            **safe_inputs(),
            instrument_rules_evidence=verified_instrument_rules(),
            order_book_evidence=verified_order_book(),
            capabilities=verified_capabilities(),
        )
        thin = build_small_capital_trial_plan(
            **safe_inputs(),
            instrument_rules_evidence=verified_instrument_rules(),
            order_book_evidence=verified_order_book(asks=[
                ["100", "0.05", "0", "2"],
                ["101", "0.05", "0", "3"],
            ]),
            capabilities=verified_capabilities(),
        )

        full_checks = {check["id"]: check for check in full["checks"]}
        self.assertEqual(full_checks["order_book_depth"]["status"], "PASS")
        self.assertEqual(full["depth_impact_preview"]["status"], "DEPTH_PREVIEW_ONLY")
        self.assertEqual(full["microstructure_truth"]["status"], "OBSERVATION_ONLY")
        self.assertEqual(
            full["microstructure_truth"]["schema_version"],
            "public-order-book-microstructure-v2",
        )
        self.assertEqual(
            [row["band_bps"] for row in full["microstructure_truth"]["price_band_depth"]["rows"]],
            [5, 10, 25],
        )
        self.assertFalse(
            full["microstructure_truth"]["price_band_depth"]["complete_book_verified"]
        )
        self.assertEqual(full["microstructure_truth"]["evidence"]["comparison_level_count"], 2)
        self.assertEqual(
            full["microstructure_truth"]["evidence"]["book_hash"],
            full["public_order_book"]["book_hash"],
        )
        self.assertFalse(full["microstructure_truth"]["interpretation"]["signal_allowed"])
        self.assertEqual([row["levels_used"] for row in full["depth_impact_preview"]["rows"]], [2, 3])
        self.assertGreater(Decimal(full["depth_impact_preview"]["rows"][0]["impact_bps"]), 0)
        self.assertTrue(all(row["observed_depth_covers_budget"] for row in full["depth_impact_preview"]["rows"]))

        partial = thin["depth_impact_preview"]
        self.assertEqual(partial["status"], "VISIBLE_DEPTH_CAPACITY_LIMITED")
        self.assertTrue(partial["rows"][0]["observed_depth_covers_budget"])
        self.assertFalse(partial["rows"][1]["observed_depth_covers_budget"])
        self.assertGreater(Decimal(partial["rows"][1]["visible_depth_shortfall_quote"]), 0)
        self.assertEqual(
            Decimal(partial["rows"][1]["visible_depth_quote"])
            + Decimal(partial["rows"][1]["visible_depth_shortfall_quote"]),
            Decimal("20"),
        )
        serialized = json.dumps(thin, sort_keys=True)
        self.assertNotIn('"side"', serialized)
        self.assertNotIn('"order_type"', serialized)
        self.assertNotIn('"tgtCcy"', serialized)
        self.assertFalse(partial["execution_allowed"])
        self.assertFalse(partial["paper_authorized"])
        self.assertFalse(partial["live_order_allowed"])

        precision_rules = build_okx_public_spot_rules(
            instrument_payload(lot_size="0.0000000000000000000000001", minimum_size="0.0000000000000000000000001"),
            symbol="BTC-USDT",
            captured_at_ms=1_000_000,
        )
        precision = build_small_capital_trial_plan(
            **safe_inputs(),
            instrument_rules_evidence=precision_rules,
            order_book_evidence=verified_order_book(
                asks=[["3", "10", "0", "1"], ["4", "10", "0", "1"]],
                bids=[["2", "10", "0", "1"], ["1", "10", "0", "1"]],
            ),
            capabilities=verified_capabilities(),
        )["depth_impact_preview"]
        precision_row = precision["rows"][0]
        self.assertEqual(Decimal(precision_row["quantity_floor"]) % Decimal("0.0000000000000000000000001"), 0)
        self.assertLessEqual(Decimal(precision_row["visible_reference_cost"]), Decimal("10"))
        self.assertGreater(len(precision_row["quantity_floor"].split(".")[1]), 24)

    def test_authority_mismatch_blocks_but_never_grants_permissions(self) -> None:
        inputs = safe_inputs()
        inputs["runtime_read_only"] = False
        inputs["risk_snapshot"] = {
            "live_trading_hard_block": True,
            "paper_authorized": False,
            "live_order_allowed": True,
        }
        plan = build_small_capital_trial_plan(
            **inputs,
            capabilities=verified_capabilities(),
        )

        self.assertEqual(plan["status"], "BLOCK")
        self.assertTrue(plan["blockers"])
        self.assertFalse(plan["execution_allowed"])
        self.assertEqual(plan["permissions"]["live_trading_hard_block"], True)
        self.assertEqual(plan["permissions"]["order_submission_allowed"], False)

    def test_self_reported_rule_boolean_is_ignored_and_strict_capabilities_fail_closed(self) -> None:
        capabilities = verified_capabilities()
        capabilities["instrument_rules_verified"] = True
        capabilities["dedicated_subaccount_verified"] = 1  # type: ignore[assignment]
        first = build_small_capital_trial_plan(**safe_inputs(), capabilities=capabilities)
        second = build_small_capital_trial_plan(
            **safe_inputs(),
            capabilities=dict(reversed(list(capabilities.items()))),
        )

        checks = {check["id"]: check for check in first["checks"]}
        self.assertEqual(first["status"], "BLOCK")
        self.assertEqual(checks["instrument_rules"]["status"], "NOT_CHECKED")
        self.assertEqual(checks["security_isolation"]["status"], "INVALID")
        self.assertEqual(first["plan_hash"], second["plan_hash"])
        unhashed = dict(first)
        expected = unhashed.pop("plan_hash")
        actual = hashlib.sha256(
            json.dumps(unhashed, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
