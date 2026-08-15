from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from exchange_terminal.services.market_data_revision_ledger import (
    MarketDataRevisionLedger,
    build_cross_source_evidence,
    build_market_data_snapshot,
    compare_market_data_snapshots,
    verify_cross_source_evidence,
    verify_market_data_snapshot,
)


def canonical_hash(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def make_rows(count: int = 140, scale: float = 1.0) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    price = 100.0
    for index in range(count):
        price *= 1.0 + ((index % 9) - 4) * 0.001
        rows.append({
            "date": f"2025-{1 + index // 28:02d}-{1 + index % 28:02d}",
            "open": price * 0.998 * scale,
            "high": price * 1.006 * scale,
            "low": price * 0.994 * scale,
            "close": price * scale,
            "volume": 1_000_000 + index * 100,
            "complete": True,
        })
    return rows


class MarketDataRevisionLedgerTests(unittest.TestCase):
    def test_malformed_cross_source_evidence_fails_closed_without_raising(self) -> None:
        audit = verify_cross_source_evidence([])

        self.assertEqual(audit["status"], "BLOCK")

    def snapshot(
        self,
        rows,
        *,
        provider="futu",
        role="ACCEPTED_CACHE",
        corporate_actions_hash="",
        through_date="",
        lineage_id="",
    ):
        return build_market_data_snapshot(
            symbol="AAPL",
            provider=provider,
            rows=rows,
            role=role,
            adjustment_basis="FORWARD_ADJUSTED_QFQ",
            corporate_actions_hash=corporate_actions_hash,
            through_date=through_date,
            lineage_id=lineage_id,
        )

    def test_backtest_windows_with_different_starts_use_distinct_scopes(self) -> None:
        rows = make_rows(40)
        through_date = str(rows[-1]["date"])
        clock = iter((1000, 2000, 3000))
        with tempfile.TemporaryDirectory() as temporary:
            ledger = MarketDataRevisionLedger(Path(temporary) / "revisions.sqlite", lambda: next(clock))
            full = ledger.record_snapshot(self.snapshot(
                rows,
                role="BACKTEST_DATASET",
                through_date=through_date,
            ))
            shorter = ledger.record_snapshot(self.snapshot(
                rows[5:],
                role="BACKTEST_DATASET",
                through_date=through_date,
            ))
            replay = ledger.record_snapshot(self.snapshot(
                rows[5:],
                role="BACKTEST_DATASET",
                through_date=through_date,
            ))

        self.assertEqual(full["status"], "PASS")
        self.assertEqual(shorter["status"], "PASS")
        self.assertNotEqual(full["scope_key"], shorter["scope_key"])
        self.assertEqual(replay["classification"], "UNCHANGED")

    def test_same_backtest_window_uses_distinct_experiment_lineages(self) -> None:
        rows = make_rows(40)
        through_date = str(rows[-1]["date"])
        with tempfile.TemporaryDirectory() as temporary:
            ledger = MarketDataRevisionLedger(Path(temporary) / "revisions.sqlite", lambda: 1000)
            first = ledger.record_snapshot(self.snapshot(
                rows,
                role="BACKTEST_DATASET",
                through_date=through_date,
                lineage_id="experiment-a",
            ))
            second = ledger.record_snapshot(self.snapshot(
                rows,
                role="BACKTEST_DATASET",
                through_date=through_date,
                lineage_id="experiment-b",
            ))

        self.assertEqual(first["status"], "PASS")
        self.assertEqual(second["status"], "PASS")
        self.assertNotEqual(first["scope_key"], second["scope_key"])

    def test_append_only_snapshot_passes(self) -> None:
        previous = self.snapshot(make_rows(40))
        current = self.snapshot(make_rows(41))

        evidence = compare_market_data_snapshots(previous, current)

        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["classification"], "APPEND_ONLY")
        self.assertEqual(evidence["added_date_count"], 1)

    def test_completed_historical_price_revision_blocks_accepted_cache(self) -> None:
        rows = make_rows(40)
        revised = [dict(row) for row in rows]
        revised[10]["close"] = float(revised[10]["close"]) * 0.9

        evidence = compare_market_data_snapshots(self.snapshot(rows), self.snapshot(revised))

        self.assertEqual(evidence["status"], "BLOCK")
        self.assertEqual(evidence["classification"], "HISTORICAL_PRICE_REVISION")
        self.assertIn("completed_prices_revised:1", evidence["blockers"])

    def test_uniform_provider_rebase_requires_review_but_does_not_authorize_cache_rewrite(self) -> None:
        previous = self.snapshot(make_rows(40), role="PROVIDER_OBSERVATION")
        current = self.snapshot(make_rows(40, scale=0.75), role="PROVIDER_OBSERVATION")

        evidence = compare_market_data_snapshots(previous, current)

        self.assertEqual(evidence["status"], "REVIEW")
        self.assertEqual(evidence["classification"], "UNIFORM_PRICE_REBASE")
        self.assertAlmostEqual(evidence["uniform_price_scale"], 0.75, places=7)

    def test_sub_tolerance_provider_rounding_drift_passes_with_explicit_classification(self) -> None:
        rows = make_rows(40)
        rounded = [dict(row) for row in rows]
        for row in rounded:
            row["close"] = float(row["close"]) + 0.0001

        evidence = compare_market_data_snapshots(
            self.snapshot(rows, role="PROVIDER_OBSERVATION"),
            self.snapshot(rounded, role="PROVIDER_OBSERVATION"),
        )

        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["classification"], "IMMATERIAL_NUMERIC_DRIFT")
        self.assertEqual(evidence["material_price_changed_date_count"], 0)

    def test_sub_tolerance_adjusted_volume_drift_passes(self) -> None:
        rows = make_rows(40)
        drifted = [dict(row) for row in rows]
        for row in drifted:
            row["volume"] = float(row["volume"]) * 1.0000002

        evidence = compare_market_data_snapshots(
            self.snapshot(rows, role="PROVIDER_OBSERVATION"),
            self.snapshot(drifted, role="PROVIDER_OBSERVATION"),
        )

        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["classification"], "IMMATERIAL_NUMERIC_DRIFT")
        self.assertEqual(evidence["volume_changed_date_count"], 0)
        self.assertEqual(evidence["raw_volume_changed_date_count"], 40)
        self.assertIn("sub_tolerance_volume_quantization_drift:40", evidence["warnings"])

    def test_material_provider_volume_revision_requires_review(self) -> None:
        rows = make_rows(40)
        revised = [dict(row) for row in rows]
        revised[10]["volume"] = float(revised[10]["volume"]) * 1.02

        evidence = compare_market_data_snapshots(
            self.snapshot(rows, role="PROVIDER_OBSERVATION"),
            self.snapshot(revised, role="PROVIDER_OBSERVATION"),
        )

        self.assertEqual(evidence["status"], "REVIEW")
        self.assertEqual(evidence["classification"], "HISTORICAL_VOLUME_REVISION")
        self.assertEqual(evidence["volume_changed_date_count"], 1)
        self.assertIn("provider_volumes_revised:1", evidence["warnings"])

    def test_schema_only_snapshot_migration_does_not_block_frozen_rows(self) -> None:
        previous = self.snapshot(make_rows(40))
        previous["schema_version"] = "market-data-revision-ledger-v1"
        previous["snapshot_hash"] = "old-schema-hash"
        current = self.snapshot(make_rows(40))

        evidence = compare_market_data_snapshots(previous, current)

        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["classification"], "SCHEMA_MIGRATION")

    def test_adjusted_cache_metadata_backfill_does_not_block_identical_rows(self) -> None:
        rows = make_rows(40)
        previous = self.snapshot(rows)
        current = self.snapshot(rows, corporate_actions_hash="verified-actions-hash")

        evidence = compare_market_data_snapshots(previous, current)

        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["classification"], "CONTRACT_METADATA_ENRICHMENT")
        self.assertIn("corporate_actions_hash_backfilled_without_row_change", evidence["warnings"])

    def test_adjusted_corporate_action_metadata_revision_requires_review_not_block(self) -> None:
        rows = make_rows(40)
        previous = self.snapshot(rows, corporate_actions_hash="old-actions-hash")
        current = self.snapshot(rows, corporate_actions_hash="new-actions-hash")

        evidence = compare_market_data_snapshots(previous, current)

        self.assertEqual(evidence["status"], "REVIEW")
        self.assertEqual(evidence["classification"], "ADJUSTED_METADATA_REVISION")
        self.assertIn("adjusted_rows_unchanged_but_corporate_actions_evidence_revised", evidence["warnings"])

    def test_independent_scaled_sources_pass_return_consistency(self) -> None:
        primary = self.snapshot(make_rows(), provider="futu", role="PROVIDER_OBSERVATION")
        secondary = self.snapshot(make_rows(scale=0.5), provider="yahoo_adjusted", role="PROVIDER_OBSERVATION")

        evidence = build_cross_source_evidence(primary, secondary, required_overlap=120)

        self.assertEqual(evidence["status"], "PASS")
        self.assertTrue(evidence["independent_provider_families"])
        self.assertEqual(evidence["overlap_count"], 140)
        self.assertEqual(evidence["direction_agreement"], 1.0)
        self.assertEqual(verify_cross_source_evidence(evidence)["status"], "PASS")
        self.assertEqual(verify_market_data_snapshot(evidence["primary_snapshot"])["status"], "PASS")

    def test_fabricated_cross_source_metrics_without_snapshot_content_are_rejected(self) -> None:
        evidence = {
            "schema_version": "market-data-revision-ledger-v6",
            "symbol": "FAKE",
            "status": "PASS",
            "primary_provider": "futu",
            "secondary_provider": "yahoo",
            "primary_snapshot_hash": "0" * 64,
            "secondary_snapshot_hash": "1" * 64,
            "independent_provider_families": True,
            "required_overlap": 120,
            "overlap_count": 120,
            "overlap_first": "2024-01-01",
            "overlap_last": "2024-06-30",
            "latest_overlap_gap_days": 0,
            "median_abs_return_difference": 0.0,
            "p95_abs_return_difference": 0.0,
            "p99_abs_return_difference": 0.0,
            "direction_agreement": 1.0,
            "price_ratio_dispersion": 0.0,
            "blockers": [],
            "warnings": [],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        evidence["evidence_hash"] = canonical_hash(evidence)

        audit = verify_cross_source_evidence(evidence)

        self.assertEqual(audit["status"], "BLOCK")
        self.assertIn("cross_source_snapshot_content_missing", audit["blockers"])

    def test_resealed_cross_source_snapshot_tampering_is_recomputed(self) -> None:
        primary = self.snapshot(make_rows(), provider="futu", role="PROVIDER_OBSERVATION")
        secondary = self.snapshot(make_rows(scale=0.5), provider="yahoo_adjusted", role="PROVIDER_OBSERVATION")
        evidence = build_cross_source_evidence(primary, secondary, required_overlap=120)
        evidence["primary_snapshot"]["rows"][0]["close"] *= 10
        evidence.pop("evidence_hash")
        evidence["evidence_hash"] = canonical_hash(evidence)

        audit = verify_cross_source_evidence(evidence)

        self.assertEqual(audit["status"], "BLOCK")
        self.assertTrue(any("primary_snapshot" in item for item in audit["blockers"]))

    def test_resealed_contradictory_cross_source_pass_is_rejected(self) -> None:
        primary = self.snapshot(make_rows(), provider="futu", role="PROVIDER_OBSERVATION")
        secondary = self.snapshot(make_rows(scale=0.5), provider="yahoo_adjusted", role="PROVIDER_OBSERVATION")
        evidence = build_cross_source_evidence(primary, secondary, required_overlap=120)
        evidence["p95_abs_return_difference"] = 0.5
        evidence.pop("evidence_hash")
        evidence["evidence_hash"] = canonical_hash(evidence)

        audit = verify_cross_source_evidence(evidence)

        self.assertEqual(audit["status"], "BLOCK")
        self.assertIn("cross_source_status_semantic_mismatch", audit["blockers"])

    def test_boolean_cross_source_count_is_rejected(self) -> None:
        primary = self.snapshot(make_rows(), provider="futu", role="PROVIDER_OBSERVATION")
        secondary = self.snapshot(make_rows(scale=0.5), provider="yahoo_adjusted", role="PROVIDER_OBSERVATION")
        evidence = build_cross_source_evidence(primary, secondary, required_overlap=120)
        evidence["overlap_count"] = True
        evidence.pop("evidence_hash")
        evidence["evidence_hash"] = canonical_hash(evidence)

        audit = verify_cross_source_evidence(evidence)

        self.assertEqual(audit["status"], "BLOCK")
        self.assertIn("cross_source_overlap_count_invalid", audit["blockers"])

    def test_same_provider_family_is_not_independent(self) -> None:
        primary = self.snapshot(make_rows(), provider="yahoo", role="PROVIDER_OBSERVATION")
        secondary = self.snapshot(make_rows(), provider="yahoo_adjusted", role="PROVIDER_OBSERVATION")

        evidence = build_cross_source_evidence(primary, secondary)

        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn("cross_source_not_independent:yahoo", evidence["blockers"])

    def test_latest_revision_review_is_visible_in_summary(self) -> None:
        rows = make_rows(40)
        clock = iter((1000, 2000))
        with tempfile.TemporaryDirectory() as temporary:
            ledger = MarketDataRevisionLedger(Path(temporary) / "revisions.sqlite", lambda: next(clock))
            ledger.record_snapshot(self.snapshot(rows, corporate_actions_hash="old-actions-hash"))
            reviewed = ledger.record_snapshot(self.snapshot(rows, corporate_actions_hash="new-actions-hash"))

            summary = ledger.summary()

            self.assertEqual(reviewed["status"], "REVIEW")
            self.assertEqual(summary["status"], "REVIEW")
            self.assertEqual(summary["latest_revision_review_count"], 1)
            self.assertEqual(summary["unresolved_blocking_revision_count"], 0)

    def test_latest_snapshot_returns_full_rows_and_ledger_state(self) -> None:
        rows = make_rows(40)
        with tempfile.TemporaryDirectory() as temporary:
            ledger = MarketDataRevisionLedger(Path(temporary) / "revisions.sqlite", lambda: 1000)
            recorded = ledger.record_snapshot(self.snapshot(rows, provider="futu", role="PROVIDER_OBSERVATION"))

            latest = ledger.latest_snapshot(
                symbol="AAPL",
                provider="futu_cache",
                role="PROVIDER_OBSERVATION",
                interval="1d",
                session="regular",
            )
            by_hash = ledger.snapshot_by_hash(latest["snapshot"]["snapshot_hash"])

        self.assertEqual(latest["scope_key"], recorded["scope_key"])
        self.assertEqual(latest["state_status"], "PASS")
        self.assertEqual(latest["snapshot"]["rows"], build_market_data_snapshot(
            symbol="AAPL",
            provider="futu",
            rows=rows,
            interval="1d",
            session="regular",
            role="PROVIDER_OBSERVATION",
            adjustment_basis="FORWARD_ADJUSTED_QFQ",
        )["rows"])
        self.assertEqual(latest["snapshot"]["row_count"], 40)
        self.assertEqual(by_hash, latest["snapshot"])

    def test_blocking_revision_remains_unresolved_after_identical_replay(self) -> None:
        rows = make_rows(40)
        revised = [dict(row) for row in rows]
        revised[5]["close"] = float(revised[5]["close"]) * 1.1
        clock = iter((1000, 2000, 3000))
        with tempfile.TemporaryDirectory() as temporary:
            ledger = MarketDataRevisionLedger(Path(temporary) / "revisions.sqlite", lambda: next(clock))
            self.assertEqual(ledger.record_snapshot(self.snapshot(rows))["status"], "PASS")
            blocked = ledger.record_snapshot(self.snapshot(revised))
            self.assertEqual(blocked["status"], "BLOCK")
            replay = ledger.record_snapshot(self.snapshot(revised))
            summary = ledger.summary()

            self.assertEqual(replay["status"], "BLOCK")
            self.assertIn("prior_unresolved_historical_revision", replay["blockers"])
            self.assertEqual(replay["blocking_event_hash"], blocked["event_hash"])
            self.assertEqual(summary["unresolved_blocking_revision_count"], 1)
            self.assertEqual(len(summary["unresolved_blocking_revisions"]), 1)
            self.assertEqual(
                summary["unresolved_blocking_revisions"][0]["blocking_event_hash"],
                blocked["event_hash"],
            )

    def test_blocking_revision_requires_exact_explicit_resolution(self) -> None:
        rows = make_rows(40)
        revised = [dict(row) for row in rows]
        revised[5]["close"] = float(revised[5]["close"]) * 1.1
        clock = iter((1000, 2000, 3000))
        with tempfile.TemporaryDirectory() as temporary:
            ledger = MarketDataRevisionLedger(Path(temporary) / "revisions.sqlite", lambda: next(clock))
            ledger.record_snapshot(self.snapshot(rows))
            blocked = ledger.record_snapshot(self.snapshot(revised))

            resolution = ledger.resolve_blocking_revision(
                scope_key=blocked["scope_key"],
                event_hash=blocked["event_hash"],
                reason="verified fixture correction",
            )

            self.assertTrue(resolution["resolution_hash"])
            self.assertEqual(ledger.summary()["unresolved_blocking_revision_count"], 0)
            self.assertEqual(ledger.summary()["resolution_count"], 1)

    def test_unresolved_block_cannot_be_cleared_by_later_pass_classification(self) -> None:
        rows = make_rows(40)
        revised = [dict(row) for row in rows]
        revised[5]["close"] = float(revised[5]["close"]) * 1.1
        clock = iter((1000, 2000, 3000))
        with tempfile.TemporaryDirectory() as temporary:
            ledger = MarketDataRevisionLedger(Path(temporary) / "revisions.sqlite", lambda: next(clock))
            ledger.record_snapshot(self.snapshot(rows))
            blocked = ledger.record_snapshot(self.snapshot(revised))
            migrated = self.snapshot(revised)
            migrated["schema_version"] = "market-data-revision-ledger-v-next"
            migrated["snapshot_hash"] = "schema-migration-after-block"

            replay = ledger.record_snapshot(migrated)

            self.assertEqual(replay["classification"], "SCHEMA_MIGRATION")
            self.assertEqual(replay["status"], "BLOCK")
            self.assertEqual(replay["blocking_event_hash"], blocked["event_hash"])
            self.assertEqual(ledger.summary()["unresolved_blocking_revision_count"], 1)

    def test_later_block_cannot_replace_original_unresolved_event(self) -> None:
        rows = make_rows(40)
        revised = [dict(row) for row in rows]
        revised[5]["close"] = float(revised[5]["close"]) * 1.1
        clock = iter((1000, 2000, 3000))
        with tempfile.TemporaryDirectory() as temporary:
            ledger = MarketDataRevisionLedger(Path(temporary) / "revisions.sqlite", lambda: next(clock))
            ledger.record_snapshot(self.snapshot(rows))
            original_block = ledger.record_snapshot(self.snapshot(revised))
            later_block = ledger.record_snapshot(self.snapshot(revised[1:]))

            summary = ledger.summary()

        self.assertEqual(later_block["status"], "BLOCK")
        self.assertIn("completed_rows_removed:1", later_block["blockers"])
        self.assertEqual(later_block["blocking_event_hash"], original_block["event_hash"])
        self.assertEqual(
            summary["unresolved_blocking_revisions"][0]["blocking_event_hash"],
            original_block["event_hash"],
        )

    def test_resolving_root_advances_to_later_intrinsic_block(self) -> None:
        rows = make_rows(40)
        revised = [dict(row) for row in rows]
        revised[5]["close"] = float(revised[5]["close"]) * 1.1
        clock = iter((1000, 2000, 3000, 4000, 5000))
        with tempfile.TemporaryDirectory() as temporary:
            ledger = MarketDataRevisionLedger(Path(temporary) / "revisions.sqlite", lambda: next(clock))
            ledger.record_snapshot(self.snapshot(rows))
            original_block = ledger.record_snapshot(self.snapshot(revised))
            later_block = ledger.record_snapshot(self.snapshot(revised[1:]))

            first_resolution = ledger.resolve_blocking_revision(
                scope_key=original_block["scope_key"],
                event_hash=original_block["event_hash"],
                reason="accept first fixture revision",
            )
            after_first = ledger.summary()
            second_resolution = ledger.resolve_blocking_revision(
                scope_key=original_block["scope_key"],
                event_hash=later_block["event_hash"],
                reason="accept later fixture truncation",
            )
            after_second = ledger.summary()

        self.assertEqual(first_resolution["post_resolution_status"], "BLOCK")
        self.assertEqual(first_resolution["next_blocking_event_hash"], later_block["event_hash"])
        self.assertEqual(after_first["unresolved_blocking_revision_count"], 1)
        self.assertEqual(
            after_first["unresolved_blocking_revisions"][0]["blocking_event_hash"],
            later_block["event_hash"],
        )
        self.assertEqual(second_resolution["post_resolution_status"], "PASS")
        self.assertEqual(after_second["unresolved_blocking_revision_count"], 0)

    def test_reopen_reconciles_latent_unresolved_intrinsic_block(self) -> None:
        rows = make_rows(40)
        revised = [dict(row) for row in rows]
        revised[5]["close"] = float(revised[5]["close"]) * 1.1
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "revisions.sqlite"
            ledger = MarketDataRevisionLedger(path, lambda: 1000)
            ledger.record_snapshot(self.snapshot(rows))
            blocked = ledger.record_snapshot(self.snapshot(revised))
            with closing(sqlite3.connect(path)) as connection:
                connection.execute(
                    """
                    UPDATE market_data_latest_snapshots
                    SET state_status = 'PASS', blocking_event_hash = ''
                    WHERE scope_key = ?
                    """,
                    (blocked["scope_key"],),
                )
                connection.commit()

            reopened = MarketDataRevisionLedger(path, lambda: 2000)
            summary = reopened.summary()

        self.assertEqual(summary["status"], "BLOCK")
        self.assertEqual(summary["unresolved_blocking_revision_count"], 1)
        self.assertEqual(
            summary["unresolved_blocking_revisions"][0]["blocking_event_hash"],
            blocked["event_hash"],
        )

    def test_reopen_reclassifies_legacy_metadata_enrichment(self) -> None:
        rows = make_rows(40)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "revisions.sqlite"
            ledger = MarketDataRevisionLedger(path, lambda: 1000)
            ledger.record_snapshot(self.snapshot(rows, corporate_actions_hash=""))
            enriched = ledger.record_snapshot(self.snapshot(rows, corporate_actions_hash="actions-hash"))
            with closing(sqlite3.connect(path)) as connection:
                payload = json.loads(connection.execute(
                    "SELECT payload_json FROM market_data_revision_events WHERE event_hash = ?",
                    (enriched["event_hash"],),
                ).fetchone()[0])
                payload.pop("intrinsic_status", None)
                payload.update({
                    "schema_version": "market-data-revision-ledger-v3",
                    "classification": "CONTRACT_REVISION",
                    "status": "BLOCK",
                    "blockers": ["snapshot_contract_changed_without_row_change"],
                })
                connection.execute(
                    """
                    UPDATE market_data_revision_events
                    SET classification = 'CONTRACT_REVISION', status = 'BLOCK', payload_json = ?
                    WHERE event_hash = ?
                    """,
                    (json.dumps(payload), enriched["event_hash"]),
                )
                connection.execute(
                    """
                    UPDATE market_data_latest_snapshots
                    SET state_status = 'BLOCK', blocking_event_hash = ?
                    WHERE scope_key = ?
                    """,
                    (enriched["event_hash"], enriched["scope_key"]),
                )
                connection.commit()

            reopened = MarketDataRevisionLedger(path, lambda: 2000)
            summary = reopened.summary()

        self.assertEqual(summary["status"], "PASS")
        self.assertEqual(summary["unresolved_blocking_revision_count"], 0)


if __name__ == "__main__":
    unittest.main()
