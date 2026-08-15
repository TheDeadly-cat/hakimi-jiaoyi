from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import run_portfolio_forward_watchdog as watchdog_runner

from exchange_terminal.services.portfolio_forward_watchdog import (
    BACKUP_TASK_NAME,
    OBSERVATION_TASK_NAME,
    PERFORMANCE_TASK_NAME,
    PORTFOLIO_FORWARD_WATCHDOG_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_WATCHDOG_V2_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_WATCHDOG_V3_ARCHIVE_FACT_FIELDS,
    PORTFOLIO_FORWARD_WATCHDOG_V3_CHECK_FIELDS,
    PORTFOLIO_FORWARD_WATCHDOG_V3_FIELDS,
    PORTFOLIO_FORWARD_WATCHDOG_V3_SOURCE_FACT_FIELDS,
    build_portfolio_forward_watchdog_status,
    canonical_hash,
    record_portfolio_forward_watchdog_status,
    verify_portfolio_forward_watchdog_status,
)
from exchange_terminal.services.portfolio_evidence_archive import (
    build_portfolio_backup_status,
    verify_portfolio_backup_status,
)
from exchange_terminal.services.portfolio_forward_local_source_anchor import (
    build_portfolio_forward_local_source_anchor,
    build_portfolio_forward_local_source_anchor_not_available,
)
from exchange_terminal.services.portfolio_forward_local_source_receipt import (
    PORTFOLIO_BACKUP_STATUS_SCHEMA_VERSION,
    PORTFOLIO_BACKUP_STATUS_V1_SCHEMA_VERSION,
)


NOW_MS = 10_000_000
CANDIDATE_HASH = "c" * 64
MANIFEST_HASH = "a" * 64
PACK_HASH = "b" * 64


def verified_anchor(*, generated_at: int = NOW_MS - 30_000, database_hash: str = "d") -> dict[str, object]:
    return build_portfolio_forward_local_source_anchor(
        candidate_hash=CANDIDATE_HASH,
        archive_manifest_hash=MANIFEST_HASH,
        archive_generated_at=generated_at,
        observer_projection=[{
            "signal_date": "2026-08-14",
            "observation_hash": "1" * 64,
            "change_projection_hash": "2" * 64,
        }],
        settlement_projection=[{
            "date": "2026-08-14",
            "settlement_type": "BASELINE",
            "settlement_hash": "3" * 64,
            "previous_settlement_hash": "",
            "strategy_equity": 100_000.0,
            "benchmark_equity": 100_000.0,
            "strategy_daily_return_pct": 0.0,
            "benchmark_daily_return_pct": 0.0,
            "rebalance_executed": False,
        }],
        shadow_database_sha256=database_hash * 64,
        performance_database_sha256="e" * 64,
    )


def install_anchor(
    values: dict[str, object],
    anchor: dict[str, object],
    *,
    generated_at: int = NOW_MS - 30_000,
) -> None:
    backup = build_portfolio_backup_status(
        generated_at=generated_at,
        result={
            "status": "ARCHIVED",
            "candidate_hash": CANDIDATE_HASH,
            "bundle_path": "C:/synthetic/archive",
            "manifest_hash": MANIFEST_HASH,
            "pack_hash": PACK_HASH,
            "verification": {
                "status": "PASS",
                "blockers": [],
                "local_source_anchor": anchor,
            },
        },
    )
    values["backup"] = backup
    values["backup_verification"] = verify_portfolio_backup_status(backup)
    values["backup_archive_verification"] = {
        "status": "PASS",
        "blockers": [],
        "candidate_hash": CANDIDATE_HASH,
        "manifest_hash": MANIFEST_HASH,
        "local_source_anchor": anchor,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def legacy_backup() -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": PORTFOLIO_BACKUP_STATUS_V1_SCHEMA_VERSION,
        "status": "PASS",
        "severity": "INFO",
        "generated_at": NOW_MS - 30_000,
        "candidate_hash": CANDIDATE_HASH,
        "bundle_path": "C:/synthetic/legacy-archive",
        "manifest_hash": MANIFEST_HASH,
        "pack_hash": PACK_HASH,
        "verification_status": "PASS",
        "blockers": [],
        "error_type": "",
        "error": "",
        "backup_only": True,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
        "alert_condition_hash": "legacy-condition",
    }
    payload["status_hash"] = canonical_hash(payload)
    return payload


def fixtures() -> dict[str, object]:
    audit = {"status": "PASS", "valid_observation_count": 0}
    active = {
        "status": "PASS",
        "registry": {
            "candidate_hash": CANDIDATE_HASH,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "candidate": {
            "candidate_hash": CANDIDATE_HASH,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    scheduler = {
        "status": "UP_TO_DATE",
        "health": "PASS",
        "status_age_ms": 30_000,
        "candidate_hash": CANDIDATE_HASH,
        "scheduled_invocation": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    observation = {
        "status": "FORWARD_OBSERVATIONS_UPDATED",
        "candidate_hash": CANDIDATE_HASH,
        "readiness": {
            "status": "COLLECTING",
            "critical_checks": {"candidate_pass": True, "ledger_pass": True},
            "ledger_audit": audit,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    performance = {
        "status": "COLLECTING",
        "generated_at": NOW_MS - 30_000,
        "candidate_hash": CANDIDATE_HASH,
        "scheduled_invocation": True,
        "shadow_audit": audit,
        "shadow_audit_hash": canonical_hash(audit),
        "performance": {"status": "PASS", "candidate_hash": CANDIDATE_HASH},
        "readiness": {
            "status": "COLLECTING",
            "integrity_checks": {"ledger_pass": True, "snapshot_pass": True},
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    anchor = build_portfolio_forward_local_source_anchor_not_available(
        reason="CROSS_ARTIFACT_CHAIN_NOT_AVAILABLE",
        candidate_hash=CANDIDATE_HASH,
        archive_manifest_hash=MANIFEST_HASH,
        archive_generated_at=NOW_MS - 30_000,
    )
    backup = build_portfolio_backup_status(
        generated_at=NOW_MS - 30_000,
        result={
            "status": "ARCHIVED",
            "candidate_hash": CANDIDATE_HASH,
            "bundle_path": "C:/synthetic/archive",
            "manifest_hash": MANIFEST_HASH,
            "pack_hash": PACK_HASH,
            "verification": {
                "status": "PASS",
                "blockers": [],
                "local_source_anchor": anchor,
            },
        },
    )
    backup_verification = verify_portfolio_backup_status(backup)
    backup_archive_verification = {
        "status": "PASS",
        "blockers": [],
        "candidate_hash": CANDIDATE_HASH,
        "manifest_hash": MANIFEST_HASH,
        "local_source_anchor": anchor,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    task = {
        "installed": True,
        "enabled": True,
        "state": "Ready",
        "last_task_result": 0,
        "last_run_at_ms": NOW_MS - 30_000,
        "next_run_at_ms": NOW_MS + 60_000,
    }
    task_probe = {
        "status": "PASS",
        "tasks": {
            OBSERVATION_TASK_NAME: dict(task),
            PERFORMANCE_TASK_NAME: dict(task),
            BACKUP_TASK_NAME: dict(task),
        },
    }
    return {
        "active": active,
        "scheduler": scheduler,
        "observation": observation,
        "performance": performance,
        "backup": backup,
        "backup_verification": backup_verification,
        "backup_archive_verification": backup_archive_verification,
        "task_probe": task_probe,
    }


class PortfolioForwardWatchdogTests(unittest.TestCase):
    def build(self, values: dict[str, object], **options: object) -> dict[str, object]:
        return build_portfolio_forward_watchdog_status(now_ms=NOW_MS, **values, **options)

    def test_runner_bounded_reader_accepts_one_valid_object(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "status.json"
            path.write_bytes(b'{"status":"PASS","count":1}')

            payload = watchdog_runner._read_json(path)

        self.assertEqual(payload, {"status": "PASS", "count": 1})

    def test_runner_bounded_reader_rejects_deep_duplicate_and_nonfinite_json(self) -> None:
        deeply_nested = (b'{"nested":' * 140) + b"0" + (b"}" * 140)
        cases = {
            "deep": deeply_nested,
            "duplicate": b'{"status":"PASS","status":"BLOCK"}',
            "nonfinite": b'{"value":NaN}',
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, raw in cases.items():
                with self.subTest(name=name):
                    path = root / f"{name}.json"
                    path.write_bytes(raw)
                    self.assertEqual(watchdog_runner._read_json(path), {})

    def test_runner_bounded_reader_rejects_oversize_and_links(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            oversized = root / "oversized.json"
            oversized.write_bytes(
                b'{"value":"'
                + (b"x" * watchdog_runner.MAX_PORTFOLIO_FORWARD_RUNNER_ARTIFACT_BYTES)
                + b'"}'
            )
            self.assertEqual(watchdog_runner._read_json(oversized), {})

            target = root / "target.json"
            target.write_bytes(b'{"status":"PASS"}')
            link = root / "linked.json"
            try:
                link.symlink_to(target)
            except OSError:
                self.skipTest("symlink creation is unavailable in this environment")
            self.assertEqual(watchdog_runner._read_json(link), {})

    def test_runner_bounded_reader_contains_memory_and_recursion_failures(self) -> None:
        path = Path("private-path-must-not-escape.json")
        with patch.object(
            watchdog_runner,
            "read_forward_json_artifact",
            side_effect=MemoryError("private-path-must-not-escape"),
        ):
            self.assertEqual(watchdog_runner._read_json(path), {})
        with patch.object(
            watchdog_runner,
            "read_forward_json_artifact",
            side_effect=RecursionError("private-path-must-not-escape"),
        ):
            self.assertEqual(watchdog_runner._read_json(path), {})

    def test_runner_assigns_status_and_control_budgets_by_artifact_role(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(watchdog_runner, "REPORT_DIR", root / "reports"), patch.object(
                watchdog_runner,
                "RUNTIME_DIR",
                root,
            ), patch.object(
                watchdog_runner,
                "load_active_portfolio_candidate",
                return_value={"candidate": {"candidate_hash": CANDIDATE_HASH}},
            ), patch.object(
                watchdog_runner,
                "load_forward_scheduler_status",
                return_value={},
            ), patch.object(
                watchdog_runner,
                "_read_json",
                return_value={},
            ) as read_json, patch.object(
                watchdog_runner,
                "verify_portfolio_backup_status",
                return_value={"status": "BLOCK"},
            ), patch.object(
                watchdog_runner,
                "_probe_windows_tasks",
                return_value={"status": "BLOCK", "tasks": {}},
            ), patch.object(
                watchdog_runner,
                "build_portfolio_forward_watchdog_status",
                return_value={"status": "BLOCK"},
            ), patch.object(
                watchdog_runner,
                "record_portfolio_forward_watchdog_status",
            ), patch.object(
                sys,
                "argv",
                ["run_portfolio_forward_watchdog.py"],
            ), redirect_stdout(StringIO()):
                code = watchdog_runner.main()

        self.assertEqual(code, 2)
        self.assertEqual(
            [call.kwargs["byte_limit"] for call in read_json.call_args_list],
            [
                watchdog_runner.MAX_PORTFOLIO_FORWARD_STATUS_ARTIFACT_BYTES,
                watchdog_runner.MAX_PORTFOLIO_FORWARD_STATUS_ARTIFACT_BYTES,
                watchdog_runner.MAX_PORTFOLIO_FORWARD_CONTROL_ARTIFACT_BYTES,
            ],
        )

    def test_healthy_forward_runtime_passes_without_execution_authority(self) -> None:
        payload = self.build(fixtures())

        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["schema_version"], PORTFOLIO_FORWARD_WATCHDOG_SCHEMA_VERSION)
        self.assertEqual(set(payload), PORTFOLIO_FORWARD_WATCHDOG_V3_FIELDS)
        self.assertEqual(set(payload["checks"]), PORTFOLIO_FORWARD_WATCHDOG_V3_CHECK_FIELDS)
        self.assertEqual(
            set(payload["source_facts"]),
            PORTFOLIO_FORWARD_WATCHDOG_V3_SOURCE_FACT_FIELDS,
        )
        self.assertEqual(
            set(payload["source_facts"]["backup_archive_verification"]),
            PORTFOLIO_FORWARD_WATCHDOG_V3_ARCHIVE_FACT_FIELDS,
        )
        self.assertEqual(payload["local_source_anchor_status"], "NOT_AVAILABLE")
        self.assertEqual(payload["verified_source_anchor"]["status"], "NOT_AVAILABLE")
        self.assertEqual(payload["blockers"], [])
        self.assertFalse(payload["paper_authorized"])
        self.assertFalse(payload["live_order_allowed"])
        self.assertEqual(verify_portfolio_forward_watchdog_status(payload)["status"], "PASS")

    def test_verified_anchor_is_carried_only_after_exact_independent_match(self) -> None:
        values = fixtures()
        anchor = verified_anchor()
        install_anchor(values, anchor)

        payload = self.build(values)

        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["local_source_anchor_status"], "VERIFIED")
        self.assertEqual(payload["verified_source_anchor"], anchor)
        self.assertEqual(payload["backup_schema_version"], PORTFOLIO_BACKUP_STATUS_SCHEMA_VERSION)
        self.assertEqual(payload["backup_status_hash"], values["backup"]["status_hash"])
        self.assertEqual(verify_portfolio_forward_watchdog_status(payload)["status"], "PASS")

    def test_legacy_backup_remains_valid_but_never_claims_anchor(self) -> None:
        values = fixtures()
        backup = legacy_backup()
        values["backup"] = backup
        values["backup_verification"] = verify_portfolio_backup_status(backup)
        values["backup_archive_verification"]["local_source_anchor"] = verified_anchor()

        payload = self.build(values)

        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["backup_schema_version"], PORTFOLIO_BACKUP_STATUS_V1_SCHEMA_VERSION)
        self.assertEqual(payload["local_source_anchor_status"], "NOT_AVAILABLE")
        self.assertEqual(payload["verified_source_anchor"]["status"], "NOT_AVAILABLE")
        self.assertEqual(verify_portfolio_forward_watchdog_status(payload)["status"], "PASS")

    def test_watchdog_v2_verifier_remains_frozen_compatible(self) -> None:
        legacy = {
            "schema_version": PORTFOLIO_FORWARD_WATCHDOG_V2_SCHEMA_VERSION,
            "status": "PASS",
            "checks": {"legacy_check": True},
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        legacy["status_hash"] = canonical_hash(legacy)

        verification = verify_portfolio_forward_watchdog_status(legacy)

        self.assertEqual(verification["status"], "PASS")

    def test_watchdog_v2_malformed_checks_fail_closed_without_exception(self) -> None:
        legacy = {
            "schema_version": PORTFOLIO_FORWARD_WATCHDOG_V2_SCHEMA_VERSION,
            "status": "BLOCK",
            "checks": 1,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        legacy["status_hash"] = canonical_hash(legacy)

        verification = verify_portfolio_forward_watchdog_status(legacy)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("watchdog_checks_invalid", verification["blockers"])

    def test_watchdog_public_verifier_bounds_malformed_nesting_and_memory_failure(self) -> None:
        nested: dict[str, object] = {
            "schema_version": PORTFOLIO_FORWARD_WATCHDOG_SCHEMA_VERSION,
        }
        cursor = nested
        for _ in range(40):
            child: dict[str, object] = {}
            cursor["nested"] = child
            cursor = child

        self.assertEqual(
            verify_portfolio_forward_watchdog_status(None)["blockers"],
            ["watchdog_status_not_object"],
        )
        self.assertEqual(
            verify_portfolio_forward_watchdog_status(nested)["blockers"],
            ["watchdog_status_structure_invalid"],
        )
        with patch(
            "exchange_terminal.services.portfolio_forward_watchdog.local_receipt_json_shape_valid",
            side_effect=MemoryError("private-path-must-not-escape"),
        ):
            exhausted = verify_portfolio_forward_watchdog_status({
                "schema_version": PORTFOLIO_FORWARD_WATCHDOG_SCHEMA_VERSION,
            })
        self.assertEqual(
            exhausted["blockers"],
            ["watchdog_verification_memory_exhausted"],
        )

    def test_disabled_task_and_nonzero_result_are_blocked(self) -> None:
        values = fixtures()
        task = values["task_probe"]["tasks"][PERFORMANCE_TASK_NAME]
        task["enabled"] = False
        task["last_task_result"] = 6

        payload = self.build(values)

        self.assertEqual(payload["status"], "BLOCK")
        self.assertIn("performance_task_pass", payload["blockers"])

    def test_custom_task_namespace_is_verified_without_default_task_aliases(self) -> None:
        values = fixtures()
        custom_observation = "HakimiTradeV2-G45-PortfolioForwardObservation"
        custom_performance = "HakimiTradeV2-G45-PortfolioForwardPerformance"
        custom_backup = "HakimiTradeV2-G45-PortfolioForwardBackup"
        defaults = values["task_probe"]["tasks"]
        values["task_probe"]["tasks"] = {
            custom_observation: defaults[OBSERVATION_TASK_NAME],
            custom_performance: defaults[PERFORMANCE_TASK_NAME],
            custom_backup: defaults[BACKUP_TASK_NAME],
        }

        payload = self.build(
            values,
            observation_task_name=custom_observation,
            performance_task_name=custom_performance,
            backup_task_name=custom_backup,
        )

        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["task_names"]["observation"], custom_observation)
        self.assertEqual(set(payload["tasks"]), {custom_observation, custom_performance, custom_backup})

    def test_stale_performance_status_and_snapshot_drift_are_blocked(self) -> None:
        values = fixtures()
        values["performance"]["generated_at"] = 1
        values["performance"]["shadow_audit"] = {"status": "PASS", "valid_observation_count": 1}

        payload = self.build(values)

        self.assertIn("performance_status_fresh", payload["blockers"])
        self.assertIn("forward_snapshot_hash_valid", payload["blockers"])
        self.assertIn("forward_snapshot_matches", payload["blockers"])

    def test_stale_backup_and_failed_archive_verification_are_blocked(self) -> None:
        values = fixtures()
        values["backup"]["generated_at"] = NOW_MS - 120_000
        values["backup_archive_verification"] = {
            "status": "BLOCK",
            "blockers": ["archive_file_hash_mismatch"],
            "candidate_hash": CANDIDATE_HASH,
            "manifest_hash": "manifest-g22",
        }

        payload = self.build(values, backup_stale_after_ms=60_000)

        self.assertIn("backup_status_fresh", payload["blockers"])
        self.assertIn("backup_archive_verification_pass", payload["blockers"])

    def test_independently_verified_anchor_mismatch_is_a_valid_contradiction_block(self) -> None:
        values = fixtures()
        install_anchor(values, verified_anchor(database_hash="d"))
        values["backup_archive_verification"]["local_source_anchor"] = verified_anchor(
            database_hash="f"
        )

        payload = self.build(values)

        self.assertEqual(payload["status"], "BLOCK")
        self.assertEqual(payload["local_source_anchor_status"], "CONTRADICTION")
        self.assertEqual(payload["verified_source_anchor"]["status"], "NOT_AVAILABLE")
        self.assertFalse(payload["checks"]["local_source_anchor_consistent"])
        self.assertIn("local_source_anchor_consistent", payload["blockers"])
        self.assertEqual(verify_portfolio_forward_watchdog_status(payload)["status"], "PASS")

    def test_candidate_manifest_and_future_time_drift_are_explicit_blocks(self) -> None:
        for name in ("candidate", "manifest", "future"):
            with self.subTest(name=name):
                values = fixtures()
                if name == "candidate":
                    values["backup_archive_verification"]["candidate_hash"] = "f" * 64
                elif name == "manifest":
                    values["backup_archive_verification"]["manifest_hash"] = "f" * 64
                else:
                    future_at = NOW_MS + 6 * 60 * 1000
                    anchor = build_portfolio_forward_local_source_anchor_not_available(
                        reason="CROSS_ARTIFACT_CHAIN_NOT_AVAILABLE",
                        candidate_hash=CANDIDATE_HASH,
                        archive_manifest_hash=MANIFEST_HASH,
                        archive_generated_at=future_at,
                    )
                    install_anchor(values, anchor, generated_at=future_at)

                payload = self.build(values)

                self.assertEqual(payload["status"], "BLOCK")
                expected = {
                    "candidate": "backup_archive_candidate_matches",
                    "manifest": "backup_archive_manifest_matches",
                    "future": "backup_timestamp_not_future",
                }[name]
                self.assertIn(expected, payload["blockers"])
                self.assertEqual(
                    verify_portfolio_forward_watchdog_status(payload)["status"],
                    "PASS",
                )

    def test_resealed_verified_anchor_candidate_cannot_pass_v3_verifier(self) -> None:
        values = fixtures()
        install_anchor(values, verified_anchor())
        payload = self.build(values)
        forged = deepcopy(payload)
        forged_anchor = forged["verified_source_anchor"]
        forged_anchor["candidate_hash"] = "f" * 64
        forged_anchor.pop("anchor_hash")
        forged_anchor["anchor_hash"] = canonical_hash(forged_anchor)
        alert_condition = {
            "status": forged["status"],
            "candidate_hash": forged["candidate_hash"],
            "blockers": forged["blockers"],
            "task_checks": forged["task_checks"],
            "local_source_anchor_status": forged["local_source_anchor_status"],
            "verified_source_anchor_hash": forged_anchor["anchor_hash"],
        }
        forged["alert_condition_hash"] = canonical_hash(alert_condition)
        forged.pop("status_hash")
        forged["status_hash"] = canonical_hash(forged)

        verification = verify_portfolio_forward_watchdog_status(forged)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "watchdog_verified_source_anchor_binding_invalid",
            verification["blockers"],
        )

    def test_v3_exact_fields_and_alert_condition_resist_coherent_reseal(self) -> None:
        payload = self.build(fixtures())
        extra = deepcopy(payload)
        extra["paper-authorized"] = True
        extra.pop("status_hash")
        extra["status_hash"] = canonical_hash(extra)
        alert = deepcopy(payload)
        alert["alert_condition_hash"] = "f" * 64
        alert.pop("status_hash")
        alert["status_hash"] = canonical_hash(alert)

        extra_verification = verify_portfolio_forward_watchdog_status(extra)
        alert_verification = verify_portfolio_forward_watchdog_status(alert)

        self.assertEqual(extra_verification["status"], "BLOCK")
        self.assertIn("watchdog_fields_invalid", extra_verification["blockers"])
        self.assertIn("watchdog_contains_execution_authority", extra_verification["blockers"])
        self.assertEqual(alert_verification["status"], "BLOCK")
        self.assertIn(
            "watchdog_alert_condition_hash_invalid",
            alert_verification["blockers"],
        )

    def test_v3_rebuilds_embedded_check_evidence_after_coherent_reseal(self) -> None:
        forged = deepcopy(self.build(fixtures()))
        backup_task_name = forged["task_names"]["backup"]
        forged["candidate_hash"] = ""
        forged["tasks"][backup_task_name]["enabled"] = False
        forged["backup_status"] = "BLOCK"
        forged["backup_archive_status"] = "BLOCK"
        forged["backup_manifest_hash"] = ""
        forged["status_ages_ms"]["backup"] = 999_999_999_999
        forged["alert_condition_hash"] = canonical_hash({
            "status": forged["status"],
            "candidate_hash": forged["candidate_hash"],
            "blockers": forged["blockers"],
            "task_checks": forged["task_checks"],
            "local_source_anchor_status": forged["local_source_anchor_status"],
            "verified_source_anchor_hash": forged["verified_source_anchor"]["anchor_hash"],
            "source_facts_hash": canonical_hash(forged["source_facts"]),
        })
        forged.pop("status_hash")
        forged["status_hash"] = canonical_hash(forged)

        verification = verify_portfolio_forward_watchdog_status(forged)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("watchdog_projection_inconsistent:task_checks", verification["blockers"])
        self.assertIn("watchdog_projection_inconsistent:candidate_hash", verification["blockers"])
        self.assertIn(
            "watchdog_projection_inconsistent:backup_archive_status",
            verification["blockers"],
        )

    def test_v3_rebuilds_every_check_from_source_facts_table(self) -> None:
        payload = self.build(fixtures())
        self.assertTrue(all(payload["checks"].values()))

        for name in sorted(PORTFOLIO_FORWARD_WATCHDOG_V3_CHECK_FIELDS):
            with self.subTest(check=name):
                forged = deepcopy(payload)
                forged["checks"][name] = False
                forged["status"] = "BLOCK"
                forged["severity"] = "CRITICAL"
                forged["blockers"] = [name]
                forged["alert_condition_hash"] = canonical_hash({
                    "status": forged["status"],
                    "candidate_hash": forged["candidate_hash"],
                    "blockers": forged["blockers"],
                    "task_checks": forged["task_checks"],
                    "local_source_anchor_status": forged["local_source_anchor_status"],
                    "verified_source_anchor_hash": forged["verified_source_anchor"]["anchor_hash"],
                    "source_facts_hash": canonical_hash(forged["source_facts"]),
                })
                forged.pop("status_hash")
                forged["status_hash"] = canonical_hash(forged)

                verification = verify_portfolio_forward_watchdog_status(forged)

                self.assertEqual(verification["status"], "BLOCK")
                self.assertIn(
                    f"watchdog_check_semantics_inconsistent:{name}",
                    verification["blockers"],
                )

    def test_non_boolean_authority_value_is_blocked(self) -> None:
        values = fixtures()
        values["performance"]["paper_authorized"] = "false"

        payload = self.build(values)

        self.assertIn("no_execution_authority", payload["blockers"])
        self.assertTrue(any(item.startswith("execution_authority:") for item in payload["blockers"]))

    def test_canonical_authority_aliases_block_builder_without_mutating_inputs(self) -> None:
        for alias in ("paper-authorized", "LiveOrderAllowed", "可下单"):
            with self.subTest(alias=alias):
                values = fixtures()
                values["performance"]["nested_alias"] = {alias: True}
                original = deepcopy(values)

                payload = self.build(values)

                self.assertEqual(values, original)
                self.assertEqual(payload["status"], "BLOCK")
                self.assertFalse(payload["checks"]["no_execution_authority"])
                self.assertIn(
                    f"execution_authority:$.performance.nested_alias.{alias}",
                    payload["blockers"],
                )

    def test_coherently_resealed_authority_aliases_fail_verification(self) -> None:
        for alias in ("paper-authorized", "LiveOrderAllowed", "可下单"):
            with self.subTest(alias=alias):
                payload = self.build(fixtures())
                payload["nested_alias"] = {alias: True}
                payload.pop("status_hash")
                payload["status_hash"] = canonical_hash(payload)
                original = deepcopy(payload)

                audit = verify_portfolio_forward_watchdog_status(payload)

                self.assertEqual(payload, original)
                self.assertEqual(audit["status"], "BLOCK")
                self.assertIn("watchdog_contains_execution_authority", audit["blockers"])

    def test_native_false_authority_aliases_remain_valid_and_inputs_are_unchanged(self) -> None:
        values = fixtures()
        values["performance"]["nested_alias"] = {
            "paper-authorized": False,
            "LiveOrderAllowed": False,
            "可下单": False,
        }
        original = deepcopy(values)

        payload = self.build(values)

        self.assertEqual(values, original)
        self.assertEqual(payload["status"], "PASS")
        self.assertTrue(payload["checks"]["no_execution_authority"])
        self.assertEqual(verify_portfolio_forward_watchdog_status(payload)["status"], "PASS")

    def test_identical_block_alert_is_deduplicated_and_recovery_is_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            status_path = Path(temporary) / "status.json"
            alert_path = Path(temporary) / "alerts.jsonl"
            values = fixtures()
            values["task_probe"]["tasks"][OBSERVATION_TASK_NAME]["enabled"] = False
            blocked = self.build(values)
            record_portfolio_forward_watchdog_status(
                status_path=status_path,
                alert_path=alert_path,
                payload=blocked,
            )
            record_portfolio_forward_watchdog_status(
                status_path=status_path,
                alert_path=alert_path,
                payload=blocked,
            )
            passed = self.build(fixtures())
            record_portfolio_forward_watchdog_status(
                status_path=status_path,
                alert_path=alert_path,
                payload=passed,
            )
            alerts = [json.loads(line) for line in alert_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(len(alerts), 2)
        self.assertEqual(alerts[0]["event_type"], "PORTFOLIO_FORWARD_WATCHDOG_ALERT")
        self.assertEqual(alerts[1]["event_type"], "PORTFOLIO_FORWARD_WATCHDOG_RECOVERY")

    def test_unverified_previous_status_cannot_suppress_a_real_block_alert(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            status_path = Path(temporary) / "status.json"
            alert_path = Path(temporary) / "alerts.jsonl"
            values = fixtures()
            values["task_probe"]["tasks"][OBSERVATION_TASK_NAME]["enabled"] = False
            blocked = self.build(values)
            forged_previous = deepcopy(blocked)
            forged_previous["status_hash"] = "0" * 64
            status_path.write_text(json.dumps(forged_previous), encoding="utf-8")

            record_portfolio_forward_watchdog_status(
                status_path=status_path,
                alert_path=alert_path,
                payload=blocked,
            )
            alerts = [
                json.loads(line)
                for line in alert_path.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(len(alerts), 1)
        self.assertEqual(
            alerts[0]["event_type"],
            "PORTFOLIO_FORWARD_WATCHDOG_ALERT",
        )

    def test_verified_legacy_previous_status_still_deduplicates_the_same_block(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            status_path = Path(temporary) / "status.json"
            alert_path = Path(temporary) / "alerts.jsonl"
            values = fixtures()
            values["task_probe"]["tasks"][OBSERVATION_TASK_NAME]["enabled"] = False
            blocked = self.build(values)
            legacy_previous = {
                "schema_version": PORTFOLIO_FORWARD_WATCHDOG_V2_SCHEMA_VERSION,
                "status": "BLOCK",
                "checks": {"legacy_check": False},
                "alert_condition_hash": blocked["alert_condition_hash"],
                "paper_authorized": False,
                "live_order_allowed": False,
            }
            legacy_previous["status_hash"] = canonical_hash(legacy_previous)
            self.assertEqual(
                verify_portfolio_forward_watchdog_status(legacy_previous)["status"],
                "PASS",
            )
            status_path.write_text(json.dumps(legacy_previous), encoding="utf-8")

            record_portfolio_forward_watchdog_status(
                status_path=status_path,
                alert_path=alert_path,
                payload=blocked,
            )
            alert_exists = alert_path.exists()

        self.assertFalse(alert_exists)


if __name__ == "__main__":
    unittest.main()
