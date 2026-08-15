from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.portfolio_backtest import (
    prepare_portfolio_dataset,
    run_causal_relative_strength_backtest,
)
from exchange_terminal.services.portfolio_backtest_replay import (
    DEFAULT_REPLAY_DRIVER_FILE,
    build_portfolio_backtest_replay_dataset,
    canonical_hash,
    file_sha256,
    run_isolated_portfolio_backtest_replay,
    stage_portfolio_backtest_replay_bundle,
    verify_portfolio_backtest_replay_dataset,
)
from exchange_terminal.services import portfolio_backtest_replay as replay_module
from exchange_terminal.services.portfolio_universe import build_static_research_universe_contract
from exchange_terminal.services.strategy_benchmark import buy_and_hold_report


def make_rows(count: int, drift: float) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    trading_date = date(2024, 1, 2)
    close = 100.0
    for index in range(count):
        while trading_date.weekday() >= 5:
            trading_date += timedelta(days=1)
        previous = close
        close = previous * (1.0 + drift + (0.001 if index % 2 == 0 else -0.001))
        rows.append({
            "date": trading_date.isoformat(),
            "ts_ms": (trading_date - date(1970, 1, 1)).days * 86_400_000,
            "open": previous,
            "high": max(previous, close) * 1.01,
            "low": min(previous, close) * 0.99,
            "close": close,
            "volume": 2_000_000.0,
            "complete": True,
        })
        trading_date += timedelta(days=1)
    return rows


def benchmark(payload: dict[str, object], start_index: int) -> dict[str, object]:
    result = buy_and_hold_report(
        rows=list(payload.get("rows") or []),
        symbol="SPY",
        source=f"{payload.get('source') or ''}:portfolio_benchmark",
        position_pct=60.0,
        startup_candles=80,
        fee_rate=0.0005,
        slippage_bps=2.0,
        market="stock",
        evaluation_start_index=start_index,
    )
    result["benchmark_run_hash"] = canonical_hash(result)
    return result


def revision_evidence(symbol: str, snapshot_hash: str) -> dict[str, object]:
    return {
        "status": "PASS",
        "accepted_cache": {
            "status": "PASS",
            "current": {"snapshot_hash": f"accepted-{symbol.lower()}"},
        },
        "backtest_dataset": {
            "status": "PASS",
            "current": {"snapshot_hash": snapshot_hash},
        },
    }


def replay_fixture() -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    raw_payloads = {
        "SPY": {"source": "test", "rows": make_rows(300, 0.0015)},
        "AAA": {"source": "test", "rows": make_rows(300, 0.0030)},
        "BBB": {"source": "test", "rows": make_rows(300, 0.0020)},
    }
    contract = build_static_research_universe_contract(
        benchmark_symbol="SPY",
        tradable_symbols=["AAA", "BBB"],
        declared_at="2024-01-01T00:00:00Z",
        selection_basis="EXPLICIT_TEST_FIXTURE",
    )
    initial = prepare_portfolio_dataset(
        raw_payloads,
        benchmark_symbol="SPY",
        minimum_rows=180,
        universe_contract=contract,
    )
    if initial.get("status") != "PASS":
        raise AssertionError(initial.get("manifest"))
    payloads = {
        symbol: {
            **raw_payloads[symbol],
            "rows": list(initial["rows"][symbol]),
            "data_revision_evidence": revision_evidence(symbol, f"full-{symbol.lower()}"),
        }
        for symbol in initial["manifest"]["symbols"]
    }
    prepared = prepare_portfolio_dataset(
        payloads,
        benchmark_symbol="SPY",
        minimum_rows=int(initial["manifest"]["row_count"]),
        universe_contract=contract,
    )
    if prepared.get("status") != "PASS":
        raise AssertionError(prepared.get("manifest"))
    manifest = dict(prepared["manifest"])
    row_count = int(manifest["row_count"])
    train_end = int(row_count * 0.5)
    validation_end = int(row_count * 0.75)
    settings = {
        "benchmark_symbol": "SPY",
        "tradable_symbols": ["AAA", "BBB"],
        "clusters": {"AAA": "A", "BBB": "B"},
        "lookback": 60,
        "top_n": 1,
        "rank_buffer": 0,
        "gross_target_pct": 60.0,
        "universe_contract": contract,
    }
    validation_payloads = {
        symbol: {
            **payload,
            "rows": list(payload.get("rows") or [])[:validation_end],
            "data_revision_evidence": revision_evidence(symbol, f"validation-{symbol.lower()}"),
        }
        for symbol, payload in payloads.items()
    }
    validation = run_causal_relative_strength_backtest(
        payloads=validation_payloads,
        evaluation_start_index=train_end,
        **settings,
    )
    test = run_causal_relative_strength_backtest(
        payloads=payloads,
        evaluation_start_index=validation_end,
        **settings,
    )
    full = run_causal_relative_strength_backtest(payloads=payloads, **settings)
    report = {
        "schema_version": str(full.get("schema_version") or ""),
        "spec": {
            "requested_history_limit": row_count,
            "train_end_index": train_end,
            "validation_end_index": validation_end,
            "validation_cutoff": str(validation_payloads["SPY"]["rows"][-1]["date"]),
            "gross_target_pct": 60.0,
            "cost_stress_contract": [],
        },
        "dataset_manifest": manifest,
        "validation": validation,
        "test": test,
        "full": full,
        "validation_benchmark": benchmark(validation_payloads["SPY"], train_end),
        "test_benchmark": benchmark(payloads["SPY"], validation_end),
        "cost_stress": [],
        "universe_contract": contract,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return report, payloads


class PortfolioBacktestReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report, cls.payloads = replay_fixture()

    def test_snapshot_round_trip_binds_every_symbol_payload(self) -> None:
        report_sha = "a" * 64
        snapshot = build_portfolio_backtest_replay_dataset(
            self.report,
            self.payloads,
            source_report_file="research.json",
            source_report_file_sha256=report_sha,
        )

        verification = verify_portfolio_backtest_replay_dataset(
            snapshot,
            self.report,
            actual_source_report_sha256=report_sha,
        )
        tampered = json.loads(json.dumps(snapshot))
        tampered["payloads"]["AAA"]["rows"][0]["close"] += 1.0
        tampered_verification = verify_portfolio_backtest_replay_dataset(
            tampered,
            self.report,
            actual_source_report_sha256=report_sha,
        )

        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(snapshot["symbol_count"], 3)
        self.assertGreater(snapshot["row_count"], 180)
        self.assertEqual(tampered_verification["status"], "BLOCK")
        self.assertIn("replay_dataset_snapshot_hash_invalid", tampered_verification["blockers"])

    def test_resealed_snapshot_with_authority_alias_is_blocked(self) -> None:
        report_sha = "a" * 64
        snapshot = build_portfolio_backtest_replay_dataset(
            self.report,
            self.payloads,
            source_report_file="research.json",
            source_report_file_sha256=report_sha,
        )
        snapshot["nested_alias_probe"] = {"CAN_TRADE": True}
        snapshot.pop("snapshot_hash", None)
        snapshot["snapshot_hash"] = canonical_hash(snapshot)

        verification = verify_portfolio_backtest_replay_dataset(
            snapshot,
            self.report,
            actual_source_report_sha256=report_sha,
        )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "replay_dataset_contains_execution_authority",
            verification["blockers"],
        )

    def test_nonzero_replay_process_preserves_valid_semantic_blockers(self) -> None:
        blocked = {
            "schema_version": "portfolio-backtest-replay-result-v1",
            "status": "BLOCK",
            "blockers": ["full_result_hash_matches"],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        blocked["replay_hash"] = canonical_hash(blocked)
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            for relative in ("replay/driver.py", "source/.keep", "datasets/input.json", "reports/report.json"):
                path = bundle / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}", encoding="utf-8")
            with mock.patch.object(
                replay_module.subprocess,
                "run",
                return_value=replay_module.subprocess.CompletedProcess(
                    args=[],
                    returncode=2,
                    stdout=json.dumps(blocked),
                    stderr="",
                ),
            ):
                result = run_isolated_portfolio_backtest_replay(
                    bundle,
                    {
                        "driver_archive_path": "replay/driver.py",
                        "source_archive_path": "source",
                        "dataset_archive_path": "datasets/input.json",
                        "source_report_archive_path": "reports/report.json",
                    },
                )

        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["blockers"], ["full_result_hash_matches"])

    def test_replay_bundle_copies_driver_from_frozen_source_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            frozen_driver = (
                bundle
                / "source"
                / "exchange_terminal"
                / "services"
                / DEFAULT_REPLAY_DRIVER_FILE
            )
            frozen_driver.parent.mkdir(parents=True)
            frozen_driver.write_text("FROZEN DRIVER", encoding="utf-8")
            report_path = bundle / "reports" / "research.json"
            report_path.parent.mkdir(parents=True)
            report_path.write_text("{}", encoding="utf-8")
            snapshot = {
                "snapshot_hash": "snapshot",
                "candidate_dataset_hash": "dataset",
                "candidate_dataset_manifest_hash": "manifest",
                "symbol_count": 1,
                "row_count": 1,
                "capture_policy": "TEST",
            }
            with (
                mock.patch.object(replay_module, "load_replay_payloads_from_local_cache", return_value={}),
                mock.patch.object(replay_module, "build_portfolio_backtest_replay_dataset", return_value=snapshot),
                mock.patch.object(
                    replay_module,
                    "run_isolated_portfolio_backtest_replay",
                    return_value={"status": "PASS", "blockers": [], "replay_hash": "replay"},
                ),
            ):
                descriptor = stage_portfolio_backtest_replay_bundle(
                    bundle,
                    source_report_path=report_path,
                    source_report_archive_path="reports/research.json",
                )

            archived_driver = bundle / descriptor["driver_archive_path"]
            archived_driver_text = archived_driver.read_text(encoding="utf-8")
            archived_driver_sha256 = file_sha256(archived_driver)

        self.assertEqual(archived_driver_text, "FROZEN DRIVER")
        self.assertEqual(descriptor["driver_file_sha256"], archived_driver_sha256)

    def test_isolated_driver_reproduces_results_without_network_or_database(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            source_root = bundle / "source"
            shutil.copytree(
                PROJECT_ROOT / "exchange_terminal",
                source_root / "exchange_terminal",
                ignore=shutil.ignore_patterns("__pycache__", "static"),
            )
            report_path = bundle / "reports" / "research.json"
            report_path.parent.mkdir(parents=True)
            report_path.write_text(json.dumps(self.report, ensure_ascii=True), encoding="utf-8")
            snapshot = build_portfolio_backtest_replay_dataset(
                self.report,
                self.payloads,
                source_report_file=report_path.name,
                source_report_file_sha256=file_sha256(report_path),
            )
            dataset_path = bundle / "datasets" / "inputs.json"
            dataset_path.parent.mkdir(parents=True)
            dataset_path.write_text(
                json.dumps(snapshot, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
                encoding="utf-8",
            )
            driver_path = bundle / "replay" / DEFAULT_REPLAY_DRIVER_FILE
            driver_path.parent.mkdir(parents=True)
            shutil.copy2(
                PROJECT_ROOT / "exchange_terminal" / "services" / DEFAULT_REPLAY_DRIVER_FILE,
                driver_path,
            )
            descriptor = {
                "driver_archive_path": driver_path.relative_to(bundle).as_posix(),
                "source_archive_path": source_root.relative_to(bundle).as_posix(),
                "dataset_archive_path": dataset_path.relative_to(bundle).as_posix(),
                "source_report_archive_path": report_path.relative_to(bundle).as_posix(),
            }

            result = run_isolated_portfolio_backtest_replay(bundle, descriptor)
            generated_bytecode_directories = list(source_root.rglob("__pycache__"))

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["network_access_attempt_count"], 0)
        self.assertEqual(result["database_access_attempt_count"], 0)
        self.assertEqual(generated_bytecode_directories, [])
        self.assertTrue(result["checks"]["full_result_hash_matches"])
        self.assertTrue(result["checks"]["test_result_hash_matches"])

    def test_isolated_driver_uses_frozen_stage_evidence_after_revision_metadata_changes(self) -> None:
        drifted_payloads = json.loads(json.dumps(self.payloads))
        for symbol, payload in drifted_payloads.items():
            evidence = dict(payload.get("data_revision_evidence") or {})
            for role in ("accepted_cache", "backtest_dataset"):
                item = dict(evidence.get(role) or {})
                current = dict(item.get("current") or {})
                item.update({
                    "classification": "UNCHANGED",
                    "previous": {
                        "schema_version": "market-data-revision-ledger-v6",
                        "snapshot_hash": str(current.get("snapshot_hash") or ""),
                    },
                    "previous_snapshot_hash": str(current.get("snapshot_hash") or ""),
                    "event_hash": f"later-{role}-{symbol.lower()}",
                    "warnings": [],
                })
                evidence[role] = item
            payload["data_revision_evidence"] = evidence

        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            source_root = bundle / "source"
            shutil.copytree(
                PROJECT_ROOT / "exchange_terminal",
                source_root / "exchange_terminal",
                ignore=shutil.ignore_patterns("__pycache__", "static"),
            )
            report_path = bundle / "reports" / "research.json"
            report_path.parent.mkdir(parents=True)
            report_path.write_text(json.dumps(self.report, ensure_ascii=True), encoding="utf-8")
            snapshot = build_portfolio_backtest_replay_dataset(
                self.report,
                drifted_payloads,
                source_report_file=report_path.name,
                source_report_file_sha256=file_sha256(report_path),
            )
            dataset_path = bundle / "datasets" / "inputs.json"
            dataset_path.parent.mkdir(parents=True)
            dataset_path.write_text(
                json.dumps(snapshot, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
                encoding="utf-8",
            )
            driver_path = bundle / "replay" / DEFAULT_REPLAY_DRIVER_FILE
            driver_path.parent.mkdir(parents=True)
            shutil.copy2(
                PROJECT_ROOT / "exchange_terminal" / "services" / DEFAULT_REPLAY_DRIVER_FILE,
                driver_path,
            )
            descriptor = {
                "driver_archive_path": driver_path.relative_to(bundle).as_posix(),
                "source_archive_path": source_root.relative_to(bundle).as_posix(),
                "dataset_archive_path": dataset_path.relative_to(bundle).as_posix(),
                "source_report_archive_path": report_path.relative_to(bundle).as_posix(),
            }

            result = run_isolated_portfolio_backtest_replay(bundle, descriptor)

        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["checks"]["validation_result_hash_matches"])
        self.assertTrue(result["checks"]["test_result_hash_matches"])
        self.assertTrue(result["checks"]["full_result_hash_matches"])


if __name__ == "__main__":
    unittest.main()
