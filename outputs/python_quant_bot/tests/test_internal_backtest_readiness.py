from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.internal_backtest_readiness import (
    ENGINEERING_EVIDENCE_TYPES,
    REQUIRED_ENGINEERING_CHECKS,
    RUNTIME_ENGINEERING_COMMANDS,
    RUNTIME_ENGINEERING_EVIDENCE_SCHEMA,
    build_readiness_report,
    build_expected_engineering_actions,
    inspect_market_cache,
    inspect_runtime_health,
    verify_readiness_report,
)
from exchange_terminal.services.validation_receipts import create_validation_receipt


def health_payload() -> dict[str, object]:
    return {
        "ok": True,
        "read_only": True,
        "runtime_mutations_allowed": False,
        "paper_authorized": False,
        "paper_armed": False,
        "live_trading_hard_block": True,
        "live_order_allowed": False,
        "runtime_build": {
            "status": "PASS",
            "blockers": [],
            "process_id": 123,
            "loaded_at": 1_000_000,
            "loaded_fingerprint": "a" * 64,
            "disk_fingerprint": "a" * 64,
            "loaded_source_count": 87,
            "source_changed_after_start": False,
            "restart_required": False,
            "read_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }


class InternalBacktestReadinessTests(unittest.TestCase):
    def checks(self, root: Path) -> list[dict[str, object]]:
        actions = build_expected_engineering_actions()
        rows: list[dict[str, object]] = []
        for check_id, action in actions.items():
            contract = str(action.get("result_contract") or "")
            result: dict[str, object] = {
                "status": "PASS",
                "exit_code": 0,
                "duration_sec": 0.1,
                "stdout": {"digest": {"sha256": "1" * 64}, "size_bytes": 0},
                "stderr": {"digest": {"sha256": "2" * 64}, "size_bytes": 0},
                "safety": {
                    "mode": "READ_ONLY",
                    "runtime_mutations_allowed": False,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                },
            }
            if contract == "unittest":
                result.update({
                    "tests_run": 750 if check_id == "python_full_suite" else 1,
                    "failures": 0,
                    "errors": 0,
                })
            receipt = create_validation_receipt(
                action=action,
                result=result,
                started_at="2026-08-10T00:00:00+00:00",
                finished_at="2026-08-10T00:00:01+00:00",
            )
            artifact = root / f"{check_id}.receipt.json"
            artifact.write_text(json.dumps(receipt), encoding="utf-8")
            rows.append({
                "id": check_id,
                "status": "PASS",
                "command": list(action.get("argv") or []),
                "evidence_type": ENGINEERING_EVIDENCE_TYPES[check_id],
                "result": result,
                "artifact_path": str(artifact),
                "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                "validation_receipt": receipt,
                "reuse_allowed": True,
                "execution": "EXECUTED",
            })

        runtime_binding = {
            "process_id": 123,
            "loaded_at": 1_000_000,
            "loaded_fingerprint": "a" * 64,
        }
        runtime_results = {
            "browser_interaction": {
                "console_error_count": 0,
                "aapl_roundtrip": True,
                "nvda_roundtrip": True,
                "btc_usdt_roundtrip": True,
                "candles_never_empty": True,
            },
            "read_only_mutation_probe": {"http_status": 423},
        }
        observed_at_ms = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
        for check_id, result in runtime_results.items():
            artifact = root / f"{check_id}.json"
            row = {
                "id": check_id,
                "status": "PASS",
                "command": RUNTIME_ENGINEERING_COMMANDS[check_id],
                "evidence_type": ENGINEERING_EVIDENCE_TYPES[check_id],
                "result": result,
                "artifact_path": str(artifact),
                "reuse_allowed": False,
                "runtime_binding": runtime_binding,
                "observed_at_ms": observed_at_ms,
            }
            artifact_payload = {
                "schema_version": RUNTIME_ENGINEERING_EVIDENCE_SCHEMA,
                "id": check_id,
                "command": RUNTIME_ENGINEERING_COMMANDS[check_id],
                "evidence_type": ENGINEERING_EVIDENCE_TYPES[check_id],
                "result": result,
                "runtime_binding": runtime_binding,
                "observed_at_ms": observed_at_ms,
                "reuse_allowed": False,
            }
            artifact.write_text(json.dumps(artifact_payload), encoding="utf-8")
            row["artifact_sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
            rows.append(row)
        return rows

    def cache_payload(self, database: Path) -> dict[str, object]:
        database.write_bytes(b"sqlite-fixture")
        return {
            "ok": True,
            "path": str(database),
            "summary": "READY 1 / MISSING 1",
            "rows": [
                {
                    "symbol": "BTC-USDT",
                    "status": "READY",
                    "rows": 300,
                    "complete_rows": 299,
                    "incomplete_rows": 1,
                    "invalid_rows": 0,
                    "first": "2025-01-01",
                    "last": "2026-08-03",
                    "source": "okx",
                    "data_hash": "b" * 64,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                },
                {
                    "symbol": "ETH-USDT",
                    "status": "MISSING",
                    "rows": 0,
                    "complete_rows": 0,
                    "incomplete_rows": 0,
                    "invalid_rows": 0,
                    "source": "missing",
                    "data_hash": "c" * 64,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                },
            ],
        }

    def prior_evidence(self, report_path: Path) -> dict[str, object]:
        return {
            "status": "PASS",
            "path": str(report_path),
            "file_size": report_path.stat().st_size,
            "file_sha256": __import__("hashlib").sha256(report_path.read_bytes()).hexdigest(),
            "registration_id": "smx-test",
            "selection_cells": 54,
            "selection_passed": 0,
            "confirmation_candidates": 0,
            "forward_candidates": 0,
            "conclusion": "NO_CANDIDATE_CONFIRMED",
            "blockers": [],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def build_report(self, root: Path) -> tuple[dict[str, object], Path, Path]:
        prior_path = root / "prior.json"
        prior_path.write_text(json.dumps({"fixture": True}), encoding="utf-8")
        database = root / "cache.sqlite"
        with patch(
            "exchange_terminal.services.internal_backtest_readiness.inspect_prior_matrix_report",
            return_value=self.prior_evidence(prior_path),
        ):
            report = build_readiness_report(
                generation="G49_TEST",
                generated_at=datetime.now(tz=timezone.utc).isoformat(),
                service_origin="http://127.0.0.1:8765",
                runtime_health=health_payload(),
                market_cache=self.cache_payload(database),
                prior_matrix_report=prior_path,
                engineering_checks=self.checks(root),
            )
        return report, prior_path, database

    def test_runtime_requires_read_only_and_hard_live_block(self) -> None:
        self.assertEqual(inspect_runtime_health(health_payload())["status"], "PASS")

        writable = health_payload()
        writable["read_only"] = False
        result = inspect_runtime_health(writable)

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("runtime_authority_invalid:read_only", result["blockers"])

    def test_runtime_identity_and_service_origin_fail_closed(self) -> None:
        invalid_runtime = health_payload()
        invalid_runtime["runtime_build"]["process_id"] = "123"
        invalid_runtime["runtime_build"]["loaded_source_count"] = 0
        runtime_result = inspect_runtime_health(invalid_runtime)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prior_path = root / "prior.json"
            prior_path.write_text("{}", encoding="utf-8")
            database = root / "cache.sqlite"
            with patch(
                "exchange_terminal.services.internal_backtest_readiness.inspect_prior_matrix_report",
                return_value=self.prior_evidence(prior_path),
            ):
                report = build_readiness_report(
                    generation="G52_TEST",
                    generated_at=datetime.now(tz=timezone.utc).isoformat(),
                    service_origin="http://127.0.0.1:8765@evil.example/",
                    runtime_health=health_payload(),
                    market_cache=self.cache_payload(database),
                    prior_matrix_report=prior_path,
                    engineering_checks=self.checks(root),
                )

        self.assertEqual(runtime_result["status"], "BLOCK")
        self.assertIn("runtime_process_id_invalid", runtime_result["blockers"])
        self.assertIn("runtime_source_count_invalid", runtime_result["blockers"])
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("service_origin_invalid", report["foundational_blockers"])

    def test_market_cache_allows_missing_scope_but_rejects_invalid_btc(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = self.cache_payload(root / "cache.sqlite")
            self.assertEqual(inspect_market_cache(payload)["status"], "READY_WITH_LIMITATIONS")

            payload["rows"][0]["invalid_rows"] = 1
            result = inspect_market_cache(payload)

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("btc_history_not_research_ready", result["blockers"])

    def test_report_is_ready_only_for_preregistration_and_has_no_authority(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report, _, _ = self.build_report(Path(directory))

            verification = verify_readiness_report(report, verify_files=True)

        self.assertEqual(report["status"], "READY_FOR_PREREGISTRATION")
        self.assertEqual(report["next_experiment"]["formal_run_allowed"], False)
        self.assertEqual(report["paper_authorized"], False)
        self.assertEqual(report["live_order_allowed"], False)
        self.assertEqual(verification["status"], "PASS")

    def test_verifier_rejects_tampering_and_string_false_authority(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report, _, _ = self.build_report(Path(directory))
            tampered = deepcopy(report)
            tampered["next_experiment"]["formal_run_allowed"] = True
            authority = deepcopy(report)
            authority["paper_authorized"] = "false"

        self.assertEqual(verify_readiness_report(tampered)["status"], "BLOCK")
        self.assertEqual(verify_readiness_report(authority)["status"], "BLOCK")

    def test_missing_engineering_check_blocks_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prior_path = root / "prior.json"
            prior_path.write_text("{}", encoding="utf-8")
            database = root / "cache.sqlite"
            checks = self.checks(root)[:-1]
            with patch(
                "exchange_terminal.services.internal_backtest_readiness.inspect_prior_matrix_report",
                return_value=self.prior_evidence(prior_path),
            ):
                report = build_readiness_report(
                    generation="G49_TEST",
                    generated_at=datetime.now(tz=timezone.utc).isoformat(),
                    service_origin="http://127.0.0.1:8765",
                    runtime_health=health_payload(),
                    market_cache=self.cache_payload(database),
                    prior_matrix_report=prior_path,
                    engineering_checks=checks,
                )

        self.assertEqual(report["status"], "BLOCK")
        self.assertTrue(any("engineering_check_not_pass" in item for item in report["foundational_blockers"]))

    def test_claimed_pass_with_failed_or_unstructured_result_is_recomputed_as_block(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prior_path = root / "prior.json"
            prior_path.write_text("{}", encoding="utf-8")
            database = root / "cache.sqlite"
            checks = self.checks(root)
            checks[0]["status"] = "PASS"
            checks[0]["command"] = ["echo", "ok"]
            with patch(
                "exchange_terminal.services.internal_backtest_readiness.inspect_prior_matrix_report",
                return_value=self.prior_evidence(prior_path),
            ):
                report = build_readiness_report(
                    generation="G52_TEST",
                    generated_at=datetime.now(tz=timezone.utc).isoformat(),
                    service_origin="http://127.0.0.1:8765",
                    runtime_health=health_payload(),
                    market_cache=self.cache_payload(database),
                    prior_matrix_report=prior_path,
                    engineering_checks=checks,
                )

        self.assertEqual(report["status"], "BLOCK")
        failed = next(
            item for item in report["engineering_checks"]
            if item["id"] == "python_full_suite"
        )
        self.assertEqual(failed["status"], "BLOCK")
        self.assertIn("engineering_command_contract_invalid", failed["blockers"])

    def test_readiness_rejects_reused_or_unbound_runtime_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prior_path = root / "prior.json"
            prior_path.write_text("{}", encoding="utf-8")
            database = root / "cache.sqlite"
            checks = self.checks(root)
            checks[0]["execution"] = "REUSED"
            browser = next(item for item in checks if item["id"] == "browser_interaction")
            browser["observed_at_ms"] += 1
            with patch(
                "exchange_terminal.services.internal_backtest_readiness.inspect_prior_matrix_report",
                return_value=self.prior_evidence(prior_path),
            ):
                report = build_readiness_report(
                    generation="G52_TEST",
                    generated_at=datetime.now(tz=timezone.utc).isoformat(),
                    service_origin="http://127.0.0.1:8765",
                    runtime_health=health_payload(),
                    market_cache=self.cache_payload(database),
                    prior_matrix_report=prior_path,
                    engineering_checks=checks,
                )

        full_suite = next(item for item in report["engineering_checks"] if item["id"] == "python_full_suite")
        browser_result = next(item for item in report["engineering_checks"] if item["id"] == "browser_interaction")
        self.assertIn("engineering_readiness_requires_fresh_execution", full_suite["blockers"])
        self.assertIn("engineering_runtime_artifact_payload_mismatch", browser_result["blockers"])


if __name__ == "__main__":
    unittest.main()
