from __future__ import annotations

from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import call, patch

from exchange_terminal import server
from exchange_terminal.services.forward_artifact_io import (
    MAX_PORTFOLIO_FORWARD_CONTROL_ARTIFACT_BYTES,
    MAX_PORTFOLIO_FORWARD_STATUS_ARTIFACT_BYTES,
)
from exchange_terminal.services.portfolio_forward_projection import (
    PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_SCHEMA_VERSION,
)
from exchange_terminal.services.portfolio_forward_statistical_maturity import (
    PORTFOLIO_FORWARD_STATISTICAL_MATURITY_SCHEMA_VERSION,
)
from exchange_terminal.services.portfolio_shadow import seal_forward_status_artifact
from tests.test_portfolio_forward_statistical_maturity import (
    local_source_receipts,
    maturity_bundle,
    synthetic_single_look_stage,
    v3_maturity_bundle,
)


class PortfolioForwardServerMaturityTests(unittest.TestCase):
    def test_server_reuses_shared_forward_artifact_budgets(self) -> None:
        self.assertEqual(
            server.MAX_PORTFOLIO_FORWARD_STATUS_ARTIFACT_BYTES,
            MAX_PORTFOLIO_FORWARD_STATUS_ARTIFACT_BYTES,
        )
        self.assertEqual(
            server.MAX_PORTFOLIO_FORWARD_RECEIPT_ARTIFACT_BYTES,
            MAX_PORTFOLIO_FORWARD_CONTROL_ARTIFACT_BYTES,
        )

    def common_patches(
        self,
        *,
        runtime_dir: Path,
        candidate: dict[str, object],
        reader_side_effect: list[dict[str, object]],
    ) -> ExitStack:
        stack = ExitStack()
        reads = list(reader_side_effect)
        if len(reads) == 2:
            reads.extend([
                {"read_status": "MISSING", "payload": {}},
                {"read_status": "MISSING", "payload": {}},
            ])
        stack.enter_context(patch.object(server, "RUNTIME_DIR", runtime_dir))
        stack.enter_context(patch.object(server, "now_ms", return_value=300))
        stack.enter_context(
            patch.object(
                server,
                "load_forward_scheduler_status",
                return_value={"health": "UP_TO_DATE"},
            )
        )
        stack.enter_context(
            patch.object(
                server,
                "load_active_portfolio_candidate",
                return_value={
                    "status": "PASS",
                    "candidate": candidate,
                    "registry": {},
                    "robustness": {"status": "PASS"},
                },
            )
        )
        stack.enter_context(
            patch.object(
                server,
                "read_optional_portfolio_forward_status_artifact",
                side_effect=reads,
            )
        )
        stack.enter_context(
            patch.object(
                server.PORTFOLIO_EXPERIMENTS,
                "summary",
                return_value={
                    "status": "PASS",
                    "experiments": [],
                    "paper_authorized": False,
                    "live_order_allowed": False,
                },
            )
        )
        stack.enter_context(
            patch(
                "exchange_terminal.services.portfolio_forward_projection.build_forward_observation_dashboard",
                return_value={
                    "schema_version": "portfolio-forward-dashboard-v4",
                    "status": "UP_TO_DATE",
                    "read_only": True,
                    "observation_only": True,
                    "simulation_only": True,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                },
            )
        )
        return stack

    def test_single_bounded_reader_distinguishes_missing_and_unreadable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            missing = server.read_optional_portfolio_forward_status_artifact(
                root / "missing.json"
            )
            invalid_path = root / "invalid.json"
            invalid_path.write_bytes(b'{"duplicate":1,"duplicate":2}')
            invalid = server.read_optional_portfolio_forward_status_artifact(invalid_path)
            valid_path = root / "valid.json"
            valid_path.write_bytes(b'{"status":"PASS"}')
            valid = server.read_optional_portfolio_forward_status_artifact(valid_path)

        self.assertEqual(missing, {"read_status": "MISSING", "payload": {}})
        self.assertEqual(invalid, {"read_status": "UNREADABLE", "payload": {}})
        self.assertEqual(valid, {"read_status": "READABLE", "payload": {"status": "PASS"}})

    def test_reader_maps_read_and_parse_memory_errors_to_unreadable(self) -> None:
        artifact = Path("C:/synthetic/forward.json")
        with patch.object(server, "read_bounded_artifact", side_effect=MemoryError):
            read_failure = server.read_optional_portfolio_forward_status_artifact(artifact)
        with patch.object(server, "read_bounded_artifact", return_value=b"{}"), patch.object(
            server,
            "parse_strict_json_object",
            side_effect=MemoryError,
        ):
            parse_failure = server.read_optional_portfolio_forward_status_artifact(artifact)

        expected = {"read_status": "UNREADABLE", "payload": {}}
        self.assertEqual(read_failure, expected)
        self.assertEqual(parse_failure, expected)

    def test_exact_paths_are_read_before_observer_missing_early_return(self) -> None:
        candidate, _observer, performance = maturity_bundle("COLLECTING")
        performance.update({
            "ledger_path": "C:/private/performance.sqlite",
            "shadow_ledger_path": "C:/private/shadow.sqlite",
            "status_artifact": "C:/private/performance.json",
            "records": [{"private": "record"}],
        })
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir)
            with self.common_patches(
                runtime_dir=runtime_dir,
                candidate=candidate,
                reader_side_effect=[
                    {"read_status": "MISSING", "payload": {}},
                    {"read_status": "READABLE", "payload": performance},
                ],
            ):
                result = server.portfolio_forward_status_snapshot()
                reader = server.read_optional_portfolio_forward_status_artifact

            prefix = str(candidate["candidate_hash"])[:12]
            self.assertEqual(
                reader.call_args_list,
                [
                    call(
                        runtime_dir / "reports" / f"portfolio_forward_status_{prefix}.json",
                        byte_limit=server.MAX_PORTFOLIO_FORWARD_STATUS_ARTIFACT_BYTES,
                    ),
                    call(
                        runtime_dir
                        / "reports"
                        / f"portfolio_forward_performance_status_{prefix}.json",
                        byte_limit=server.MAX_PORTFOLIO_FORWARD_STATUS_ARTIFACT_BYTES,
                    ),
                    call(
                        runtime_dir / "reports" / server.DEFAULT_BACKUP_STATUS_FILE,
                        byte_limit=server.MAX_PORTFOLIO_FORWARD_RECEIPT_ARTIFACT_BYTES,
                    ),
                    call(
                        runtime_dir / "reports" / server.DEFAULT_WATCHDOG_STATUS_FILE,
                        byte_limit=server.MAX_PORTFOLIO_FORWARD_RECEIPT_ARTIFACT_BYTES,
                    ),
                ],
            )

        self.assertEqual(result["status"], "WAITING_FOR_FIRST_OBSERVATION")
        self.assertEqual(result["incremental_observation"]["status"], "UP_TO_DATE")
        self.assertEqual(
            result["incremental_observation"]["statistical_maturity"]["status"],
            "BLOCK",
        )

    def test_blocked_active_candidate_never_constructs_or_reads_artifact_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            server,
            "RUNTIME_DIR",
            Path(temp_dir),
        ), patch.object(
            server,
            "now_ms",
            return_value=300,
        ), patch.object(
            server,
            "load_forward_scheduler_status",
            return_value={"health": "UP_TO_DATE"},
        ), patch.object(
            server,
            "load_active_portfolio_candidate",
            return_value={
                "status": "BLOCK",
                "blockers": ["active_candidate_invalid"],
                "registry": {"candidate_hash": "unverified"},
            },
        ), patch.object(
            server,
            "read_optional_portfolio_forward_status_artifact",
        ) as reader, patch.object(
            server.PORTFOLIO_EXPERIMENTS,
            "summary",
            return_value={"status": "PASS", "experiments": []},
        ):
            result = server.portfolio_forward_status_snapshot()

        reader.assert_not_called()
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(
            result["incremental_observation"]["statistical_maturity"]["status"],
            "BLOCK",
        )

    def test_missing_performance_does_not_rewrite_operational_state(self) -> None:
        candidate, observer, _performance = maturity_bundle("COLLECTING")
        observer["readiness"]["status"] = "READY_FOR_FROZEN_EVALUATION"
        observer = seal_forward_status_artifact(observer)
        for read_status in ("MISSING", "UNREADABLE"):
            with self.subTest(read_status=read_status), tempfile.TemporaryDirectory() as temp_dir:
                with self.common_patches(
                    runtime_dir=Path(temp_dir),
                    candidate=candidate,
                    reader_side_effect=[
                        {"read_status": "READABLE", "payload": observer},
                        {"read_status": read_status, "payload": {}},
                    ],
                ), patch.object(
                    server,
                    "build_forward_observer_artifact_evidence",
                    return_value={"status": "PASS", "blockers": []},
                ), patch.object(
                    server,
                    "verify_latest_forward_observation_receipt",
                    return_value={"status": "PASS", "receipt": {}},
                ), patch.object(
                    server,
                    "verify_forward_observation_change",
                    return_value={"status": "PASS", "change": {}},
                ):
                    result = server.portfolio_forward_status_snapshot()

                self.assertEqual(result["status"], "READY_FOR_FROZEN_EVALUATION")
                self.assertEqual(result["incremental_observation"]["status"], "UP_TO_DATE")
                self.assertEqual(
                    result["incremental_observation"]["statistical_maturity"]["status"],
                    "BLOCK",
                )

    def test_valid_performance_projects_only_the_public_maturity_whitelist(self) -> None:
        candidate, observer, performance = v3_maturity_bundle(
            stage_status="PASS",
            strategy_equities=[100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0],
        )
        performance.update({
            "ledger_path": "C:/private/performance.sqlite",
            "shadow_ledger_path": "C:/private/shadow.sqlite",
            "status_artifact": "C:/private/performance.json",
            "records": [{"private": "record"}],
        })
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.common_patches(
                runtime_dir=Path(temp_dir),
                candidate=candidate,
                reader_side_effect=[
                    {"read_status": "READABLE", "payload": observer},
                    {"read_status": "READABLE", "payload": performance},
                ],
            ), patch.object(
                server,
                "build_forward_observer_artifact_evidence",
                return_value={"status": "PASS", "blockers": []},
            ), patch.object(
                server,
                "verify_latest_forward_observation_receipt",
                return_value={"status": "PASS", "receipt": {}},
            ), patch.object(
                server,
                "verify_forward_observation_change",
                return_value={"status": "PASS", "change": {}},
            ), patch(
                "exchange_terminal.services.portfolio_forward_statistical_maturity."
                "audit_paired_equity_curve_stage",
                side_effect=synthetic_single_look_stage(status="PASS"),
            ):
                result = server.portfolio_forward_status_snapshot()

        maturity = result["incremental_observation"]["statistical_maturity"]
        self.assertEqual(
            result["incremental_observation"]["schema_version"],
            PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_SCHEMA_VERSION,
        )
        self.assertEqual(
            maturity["schema_version"],
            PORTFOLIO_FORWARD_STATISTICAL_MATURITY_SCHEMA_VERSION,
        )
        self.assertEqual(maturity["status"], "REVIEW_REQUIRED")
        serialized = json.dumps(result, ensure_ascii=True, sort_keys=True)
        for forbidden in (
            "C:/private/performance.sqlite",
            "C:/private/shadow.sqlite",
            "C:/private/performance.json",
            '"records"',
            '"status_artifact"',
        ):
            self.assertNotIn(forbidden, serialized)

    def test_raw_receipts_bind_without_sqlite_or_archive_replay(self) -> None:
        candidate, observer, performance = v3_maturity_bundle(
            stage_status="PASS",
            strategy_equities=[100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0],
        )
        backup, watchdog = local_source_receipts(candidate, observer, performance)
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.common_patches(
                runtime_dir=Path(temp_dir),
                candidate=candidate,
                reader_side_effect=[
                    {"read_status": "READABLE", "payload": observer},
                    {"read_status": "READABLE", "payload": performance},
                    {"read_status": "READABLE", "payload": backup},
                    {"read_status": "READABLE", "payload": watchdog},
                ],
            ), patch.object(
                server,
                "build_forward_observer_artifact_evidence",
                return_value={"status": "PASS", "blockers": []},
            ), patch.object(
                server,
                "verify_latest_forward_observation_receipt",
                return_value={"status": "PASS", "receipt": {}},
            ), patch.object(
                server,
                "verify_forward_observation_change",
                return_value={"status": "PASS", "change": {}},
            ), patch(
                "exchange_terminal.services.portfolio_forward_statistical_maturity."
                "audit_paired_equity_curve_stage",
                side_effect=synthetic_single_look_stage(status="PASS"),
            ), patch.object(
                server.sqlite3,
                "connect",
            ) as sqlite_connect, patch(
                "exchange_terminal.services.portfolio_evidence_archive."
                "verify_portfolio_evidence_archive"
            ) as archive_verifier:
                result = server.portfolio_forward_status_snapshot()

        sqlite_connect.assert_not_called()
        archive_verifier.assert_not_called()
        maturity = result["incremental_observation"]["statistical_maturity"]
        self.assertEqual(maturity["status"], "REVIEW_REQUIRED")
        self.assertEqual(maturity["source_binding"]["status"], "FULL")
        self.assertEqual(result["incremental_observation"]["status"], "UP_TO_DATE")


if __name__ == "__main__":
    unittest.main()
