from __future__ import annotations

from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.portfolio_evidence_archive import (
    PORTFOLIO_BACKUP_STATUS_SCHEMA_VERSION,
    PORTFOLIO_BACKUP_STATUS_V1_SCHEMA_VERSION,
    backup_sqlite_database,
    build_portfolio_backup_status,
    canonical_hash,
    file_sha256,
    record_portfolio_backup_status,
    verify_portfolio_backup_status,
)
from exchange_terminal.services import portfolio_evidence_archive
from exchange_terminal.services.portfolio_forward_statistical_audit import _forward_series_evidence
from exchange_terminal.services.portfolio_forward_local_source_anchor import (
    PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_FIELDS,
    PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_TRUST_SCOPE,
    build_portfolio_forward_local_source_anchor,
    portfolio_local_source_projection_hashes,
    verify_portfolio_forward_local_source_anchor,
)
from exchange_terminal.services.portfolio_forward_local_source_receipt import (
    PORTFOLIO_BACKUP_STATUS_V2_FIELDS,
)


class PortfolioEvidenceArchiveTests(unittest.TestCase):
    _SQLITE_METADATA = {
        "quick_check": ["ok"],
        "journal_mode": "delete",
        "tables": [],
        "row_counts": {},
    }

    def test_archive_filename_uses_shared_windows_safe_identity(self) -> None:
        for name in (
            "research.json",
            "portfolio_statistical_audit.json",
            "evidence bundle.json",
        ):
            with self.subTest(valid=name):
                self.assertEqual(portfolio_evidence_archive._safe_filename(name), name)

        for name in (
            "CON.json",
            "conin$.json",
            "research.json. ",
            "ｒesearch.json",  # NFKC alias of ASCII "r".
        ):
            with self.subTest(invalid=name), self.assertRaises(ValueError):
                portfolio_evidence_archive._safe_filename(name)

    def _database_snapshots(self, root: Path) -> list[dict[str, object]]:
        database_root = root / "databases"
        database_root.mkdir(parents=True, exist_ok=True)
        snapshots: list[dict[str, object]] = []
        for name in portfolio_evidence_archive.CRITICAL_DATABASES:
            path = database_root / name
            path.write_bytes(f"synthetic:{name}".encode("utf-8"))
            snapshots.append(
                {
                    "source_name": name,
                    "archive_path": f"databases/{name}",
                    "size": path.stat().st_size,
                    "sha256": file_sha256(path),
                    **self._SQLITE_METADATA,
                }
            )
        return snapshots

    def _write_v3_archive(self, root: Path) -> tuple[dict[str, object], tuple[dict[str, object], ...]]:
        candidate_hash = "c" * 64
        pack = {
            "schema_version": "portfolio-internal-backtest-pack-v5",
            "status": "INTERNAL_BACKTEST_EVIDENCE_READY",
            "promotion_status": "BLOCK",
            "pack_hash": "a" * 64,
            "evidence_hash": "b" * 64,
            "candidate": {"candidate_hash": candidate_hash},
            "artifacts": {},
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        research_raw = b'{"kind":"research","value":1}'
        statistical_raw = b'{"kind":"statistical","value":1}'
        required = (
            {
                "role": "RESEARCH_REPORT",
                "file": "research.json",
                "sha256": hashlib.sha256(research_raw).hexdigest(),
                "byte_length": len(research_raw),
            },
            {
                "role": "STATISTICAL_AUDIT",
                "file": "statistical.json",
                "sha256": hashlib.sha256(statistical_raw).hexdigest(),
                "byte_length": len(statistical_raw),
            },
        )
        detached = [
            {**required[0], "raw_bytes": research_raw},
            {**required[1], "raw_bytes": statistical_raw},
        ]
        with patch.object(
            portfolio_evidence_archive,
            "verify_internal_backtest_bundle",
            return_value={"status": "PASS", "blockers": []},
        ):
            descriptor, members = portfolio_evidence_archive._build_archive_backtest_bundle(
                pack,
                detached,
            )
        reports = root / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        for name, raw in members.items():
            (reports / name).write_bytes(raw)
        (root / "datasets").mkdir(parents=True, exist_ok=True)
        (root / "datasets" / "replay.json").write_bytes(b"{}")
        (root / "replay").mkdir(parents=True, exist_ok=True)
        (root / "replay" / "driver.py").write_text("# synthetic\n", encoding="utf-8")
        database_snapshots = self._database_snapshots(root)
        rehearsal = {
            "status": "PASS",
            "candidate_hash": candidate_hash,
            "rehearsal_hash": "synthetic-rehearsal",
        }
        manifest = {
            "schema_version": portfolio_evidence_archive.PORTFOLIO_EVIDENCE_ARCHIVE_SCHEMA_VERSION,
            "status": "ARCHIVE_READY",
            "generated_at": 123,
            "candidate_hash": candidate_hash,
            "backtest_bundle": descriptor,
            "database_snapshots": database_snapshots,
            "source_file_count": 0,
            "backtest_replay": {
                "dataset_archive_path": "datasets/replay.json",
                "driver_archive_path": "replay/driver.py",
                "source_report_archive_path": "reports/research.json",
            },
            "file_entries": portfolio_evidence_archive._file_entries(root),
            "restore_rehearsal": rehearsal,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        manifest["manifest_hash"] = canonical_hash(manifest)
        portfolio_evidence_archive._atomic_write_json(root / "manifest.json", manifest)
        return rehearsal, required

    def _verify_synthetic_v3(
        self,
        root: Path,
        rehearsal: dict[str, object],
        required: tuple[dict[str, object], ...],
    ) -> dict[str, object]:
        with (
            patch.object(
                portfolio_evidence_archive,
                "required_internal_backtest_bundle_members",
                return_value=required,
            ),
            patch.object(
                portfolio_evidence_archive,
                "verify_internal_backtest_bundle",
                return_value={"status": "PASS", "blockers": []},
            ),
            patch.object(
                portfolio_evidence_archive,
                "_pack_artifact_verification",
                return_value={"status": "PASS", "blockers": []},
            ),
            patch.object(
                portfolio_evidence_archive,
                "_restore_rehearsal",
                return_value=rehearsal,
            ),
            patch.object(
                portfolio_evidence_archive,
                "_sqlite_metadata",
                return_value=self._SQLITE_METADATA,
            ),
            patch.object(
                portfolio_evidence_archive,
                "verify_portfolio_backtest_replay_bundle",
                return_value={"status": "PASS", "blockers": []},
            ),
        ):
            return portfolio_evidence_archive.verify_portfolio_evidence_archive(root)

    def _reseal_archive_inventory(self, root: Path) -> None:
        manifest = portfolio_evidence_archive._read_json(root / "manifest.json")
        manifest["file_entries"] = portfolio_evidence_archive._file_entries(root)
        manifest.pop("manifest_hash", None)
        manifest["manifest_hash"] = canonical_hash(manifest)
        portfolio_evidence_archive._atomic_write_json(root / "manifest.json", manifest)

    def _reseal_inner_backtest_bundle(self, root: Path) -> None:
        manifest = portfolio_evidence_archive._read_json(root / "manifest.json")
        descriptor = dict(manifest["backtest_bundle"])
        immutable_manifest = dict(descriptor["manifest"])
        members: dict[str, bytes] = {}
        roles: dict[str, str] = {}
        for item in list(immutable_manifest.get("members") or []):
            record = dict(item or {})
            name = str(record["file"])
            members[name] = (root / "reports" / name).read_bytes()
            roles[name] = str(record["role"])
        descriptor["manifest"] = portfolio_evidence_archive.build_content_addressed_bundle_manifest(
            members,
            member_roles=roles,
            bindings=dict(immutable_manifest.get("bindings") or {}),
            manifest_file=portfolio_evidence_archive.PORTFOLIO_ARCHIVE_BACKTEST_BUNDLE_MANIFEST_FILE,
            max_member_count=3,
            max_member_bytes=portfolio_evidence_archive.MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES,
            max_total_bytes=portfolio_evidence_archive.MAX_PORTFOLIO_ARCHIVE_BACKTEST_BUNDLE_BYTES,
        )
        manifest["backtest_bundle"] = descriptor
        manifest["file_entries"] = portfolio_evidence_archive._file_entries(root)
        manifest.pop("manifest_hash", None)
        manifest["manifest_hash"] = canonical_hash(manifest)
        portfolio_evidence_archive._atomic_write_json(root / "manifest.json", manifest)

    def _write_legacy_archive(self, root: Path, schema_version: str) -> dict[str, object]:
        candidate_hash = "d" * 64
        pack = {
            "schema_version": "legacy-pack-schema",
            "status": "INTERNAL_BACKTEST_EVIDENCE_READY",
            "promotion_status": "BLOCK",
            "pack_hash": "legacy-pack-hash",
            "evidence_hash": "legacy-evidence-hash",
            "candidate": {"candidate_hash": candidate_hash},
            "artifacts": {},
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        reports = root / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        portfolio_evidence_archive._atomic_write_json(reports / "legacy-pack.json", pack)
        database_snapshots = self._database_snapshots(root)
        rehearsal = {
            "status": "PASS",
            "candidate_hash": candidate_hash,
            "rehearsal_hash": f"legacy-rehearsal:{schema_version}",
        }
        manifest: dict[str, object] = {
            "schema_version": schema_version,
            "status": "ARCHIVE_READY",
            "generated_at": 123,
            "candidate_hash": candidate_hash,
            "backtest_pack": {
                "archive_path": "reports/legacy-pack.json",
                "status": pack["status"],
                "promotion_status": pack["promotion_status"],
                "pack_hash": pack["pack_hash"],
                "evidence_hash": pack["evidence_hash"],
            },
            "database_snapshots": database_snapshots,
            "source_file_count": 0,
            "restore_rehearsal": rehearsal,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        if schema_version == portfolio_evidence_archive.PORTFOLIO_EVIDENCE_ARCHIVE_V2_SCHEMA_VERSION:
            (reports / "research.json").write_bytes(b"{}")
            (root / "datasets").mkdir(parents=True, exist_ok=True)
            (root / "datasets" / "replay.json").write_bytes(b"{}")
            (root / "replay").mkdir(parents=True, exist_ok=True)
            (root / "replay" / "driver.py").write_text("# legacy\n", encoding="utf-8")
            manifest["backtest_replay"] = {
                "dataset_archive_path": "datasets/replay.json",
                "driver_archive_path": "replay/driver.py",
                "source_report_archive_path": "reports/research.json",
            }
        manifest["file_entries"] = portfolio_evidence_archive._file_entries(root)
        manifest["manifest_hash"] = canonical_hash(manifest)
        portfolio_evidence_archive._atomic_write_json(root / "manifest.json", manifest)
        return rehearsal

    @staticmethod
    def _anchor_fixture() -> dict[str, object]:
        candidate_hash = "c" * 64
        dates = ("2026-08-03", "2026-08-04")
        observation_hashes = tuple(
            hashlib.sha256(f"observation:{value}".encode("utf-8")).hexdigest()
            for value in dates
        )
        change_hashes = tuple(
            hashlib.sha256(f"change:{value}".encode("utf-8")).hexdigest()
            for value in dates
        )
        settlement_hashes = tuple(
            hashlib.sha256(f"settlement:{value}".encode("utf-8")).hexdigest()
            for value in dates
        )
        observer_projection = [
            {
                "signal_date": value,
                "observation_hash": observation_hashes[index],
                "change_projection_hash": change_hashes[index],
            }
            for index, value in enumerate(dates)
        ]
        settlement_projection = [
            {
                "date": dates[0],
                "settlement_type": "BASELINE",
                "settlement_hash": settlement_hashes[0],
                "previous_settlement_hash": "",
                "strategy_equity": 100_000.0,
                "benchmark_equity": 100_000.0,
                "strategy_daily_return_pct": 0.0,
                "benchmark_daily_return_pct": 0.0,
                "rebalance_executed": False,
            },
            {
                "date": dates[1],
                "settlement_type": "DAILY_CLOSE",
                "settlement_hash": settlement_hashes[1],
                "previous_settlement_hash": settlement_hashes[0],
                "strategy_equity": 101_000.0,
                "benchmark_equity": 100_500.0,
                "strategy_daily_return_pct": 1.0,
                "benchmark_daily_return_pct": 0.5,
                "rebalance_executed": True,
            },
        ]
        observations: dict[str, dict[str, object]] = {}
        settlements: list[dict[str, object]] = []
        for index, value in enumerate(dates):
            dataset_hash = hashlib.sha256(f"dataset:{value}".encode("utf-8")).hexdigest()
            decision_hash = hashlib.sha256(f"decision:{value}".encode("utf-8")).hexdigest()
            capture_hash = hashlib.sha256(f"capture:{value}".encode("utf-8")).hexdigest()
            clock_hash = hashlib.sha256(f"clock:{value}".encode("utf-8")).hexdigest()
            risk_hash = hashlib.sha256(f"risk:{value}".encode("utf-8")).hexdigest()
            state_hash = hashlib.sha256(f"state:{value}".encode("utf-8")).hexdigest()
            observed_at = 100 + index
            observation = {
                "candidate_hash": candidate_hash,
                "signal_date": value,
                "dataset_hash": dataset_hash,
                "observation_hash": observation_hashes[index],
                "decision_hash": decision_hash,
                "capture_contract_hash": capture_hash,
                "capture_contract": {"clock_attestation_hash": clock_hash},
                "risk_snapshot_hash": risk_hash,
                "risk_gate_status": "PASS",
                "forward_state_contract_hash": state_hash,
                "observed_at": observed_at,
            }
            current = {
                "candidate_hash": candidate_hash,
                "signal_date": value,
                "dataset_hash": dataset_hash,
                "observation_hash": observation_hashes[index],
                "decision_hash": decision_hash,
                "capture_contract_hash": capture_hash,
                "clock_attestation_hash": clock_hash,
                "risk_snapshot_hash": risk_hash,
                "risk_gate_status": "PASS",
                "forward_state_contract_hash": state_hash,
                "observed_at": observed_at,
            }
            projection = settlement_projection[index]
            observations[value] = observation
            settlements.append({
                "candidate_hash": candidate_hash,
                "settlement_date": value,
                "settlement_type": projection["settlement_type"],
                "settlement_hash": projection["settlement_hash"],
                "previous_settlement_hash": projection["previous_settlement_hash"],
                "strategy": {
                    "equity": projection["strategy_equity"],
                    "daily_return_pct": projection["strategy_daily_return_pct"],
                },
                "benchmark": {
                    "equity": projection["benchmark_equity"],
                    "daily_return_pct": projection["benchmark_daily_return_pct"],
                },
                "decision_execution": {
                    "execute": projection["rebalance_executed"],
                    "reason": "relative_strength_rebalance" if index else "baseline",
                    "status": "EXECUTED" if index else "BASELINE_AWAITING_NEXT_OPEN",
                },
                "observation_evidence": {"current": current},
            })
        shadow_audit = {
            "status": "PASS",
            "candidate_hash": candidate_hash,
            "observation_count": len(dates),
            "valid_observation_count": len(dates),
            "observation_chain_count": len(dates),
            "first_signal_date": dates[0],
            "last_signal_date": dates[-1],
            "observation_chain": observer_projection,
            "integrity_violations": [],
        }
        performance_summary = {
            "status": "PASS",
            "candidate_hash": candidate_hash,
            "settlement_count": len(dates),
            "first_settlement_date": dates[0],
            "last_settlement_date": dates[-1],
            "unsettled_observation_dates": [],
            "unexpected_settlement_dates": [],
            "observation_hash_mismatch_dates": [],
            "integrity_violations": [],
        }
        return {
            "candidate_hash": candidate_hash,
            "observer_projection": observer_projection,
            "settlement_projection": settlement_projection,
            "observations": observations,
            "settlements": settlements,
            "shadow_audit": shadow_audit,
            "performance_summary": performance_summary,
        }

    def _backup_result(self, generated_at: int) -> dict[str, object]:
        fixture = self._anchor_fixture()
        anchor = build_portfolio_forward_local_source_anchor(
            candidate_hash=str(fixture["candidate_hash"]),
            archive_manifest_hash="a" * 64,
            archive_generated_at=generated_at,
            observer_projection=fixture["observer_projection"],
            settlement_projection=fixture["settlement_projection"],
            shadow_database_sha256="b" * 64,
            performance_database_sha256="d" * 64,
        )
        return {
            "status": "ARCHIVED",
            "candidate_hash": str(fixture["candidate_hash"]),
            "bundle_path": "C:/synthetic/archive",
            "manifest_hash": "a" * 64,
            "pack_hash": "e" * 64,
            "verification": {
                "status": "PASS",
                "blockers": [],
                "local_source_anchor": anchor,
            },
        }

    def test_v3_archive_verifies_exact_backtest_bundle_and_reuses_research(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rehearsal, required = self._write_v3_archive(root)
            result = self._verify_synthetic_v3(root, rehearsal, required)
            manifest = portfolio_evidence_archive._read_json(root / "manifest.json")
            bundle_manifest = dict(manifest["backtest_bundle"]["manifest"])
            members = list(bundle_manifest.get("members") or [])
            research_members = [item for item in members if item.get("role") == "RESEARCH_REPORT"]

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(members), 3)
        self.assertEqual(len(research_members), 1)
        self.assertEqual(bundle_manifest["bindings"]["candidate_hash"], "c" * 64)
        self.assertEqual(bundle_manifest["bindings"]["pack_hash"], "a" * 64)
        self.assertEqual(bundle_manifest["bindings"]["evidence_hash"], "b" * 64)
        self.assertEqual(
            portfolio_evidence_archive.verify_content_addressed_bundle_manifest(
                bundle_manifest,
                manifest_file=portfolio_evidence_archive.PORTFOLIO_ARCHIVE_BACKTEST_BUNDLE_MANIFEST_FILE,
                max_member_count=3,
                max_member_bytes=portfolio_evidence_archive.MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES,
                max_total_bytes=portfolio_evidence_archive.MAX_PORTFOLIO_ARCHIVE_BACKTEST_BUNDLE_BYTES,
            )["status"],
            "PASS",
        )
        self.assertEqual(
            manifest["backtest_replay"]["source_report_archive_path"],
            f"reports/{research_members[0]['file']}",
        )
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])
        self.assertEqual(result["local_source_anchor"]["status"], "NOT_AVAILABLE")
        self.assertEqual(
            result["local_source_anchor"]["reason"],
            "CROSS_ARTIFACT_CHAIN_NOT_AVAILABLE",
        )
        self.assertEqual(
            verify_portfolio_forward_local_source_anchor(result["local_source_anchor"])["status"],
            "PASS",
        )

    def test_local_source_anchor_projection_is_api_rebuildable_and_exact(self) -> None:
        fixture = self._anchor_fixture()
        series_evidence, _series_blockers = _forward_series_evidence(
            candidate={"candidate_hash": fixture["candidate_hash"]},
            settlements=list(fixture["settlements"]),
        )
        projections = portfolio_local_source_projection_hashes(
            observer_projection=fixture["observer_projection"],
            settlement_projection=fixture["settlement_projection"],
        )
        anchor = build_portfolio_forward_local_source_anchor(
            candidate_hash=str(fixture["candidate_hash"]),
            archive_manifest_hash="a" * 64,
            archive_generated_at=123,
            observer_projection=fixture["observer_projection"],
            settlement_projection=fixture["settlement_projection"],
            shadow_database_sha256="b" * 64,
            performance_database_sha256="d" * 64,
        )

        self.assertEqual(series_evidence["rows"], fixture["settlement_projection"])
        self.assertEqual(set(anchor), PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_FIELDS)
        self.assertEqual(anchor["schema_version"], PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_SCHEMA_VERSION)
        self.assertEqual(anchor["status"], "VERIFIED")
        self.assertEqual(anchor["trust_scope"], PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_TRUST_SCOPE)
        self.assertEqual(anchor["observer_projection_hash"], projections["observer_projection_hash"])
        self.assertEqual(anchor["settlement_projection_hash"], projections["settlement_projection_hash"])
        self.assertEqual(anchor["cross_binding_hash"], projections["cross_binding_hash"])
        self.assertEqual(anchor["observation_count"], 2)
        self.assertEqual(anchor["settlement_count"], 2)
        self.assertTrue(anchor["research_only"])
        self.assertTrue(anchor["observation_only"])
        self.assertTrue(anchor["simulation_only"])
        self.assertFalse(anchor["external_authenticity_proven"])
        self.assertFalse(anchor["profitability_proven"])
        self.assertFalse(anchor["paper_authorized"])
        self.assertFalse(anchor["live_order_allowed"])
        self.assertEqual(verify_portfolio_forward_local_source_anchor(anchor)["status"], "PASS")

        extra = dict(anchor)
        extra["paperAuthorized"] = True
        extra.pop("anchor_hash")
        extra["anchor_hash"] = canonical_hash(extra)
        extra_verification = verify_portfolio_forward_local_source_anchor(extra)
        self.assertEqual(extra_verification["status"], "BLOCK")
        self.assertIn("local_source_anchor_fields_invalid", extra_verification["blockers"])
        self.assertIn(
            "local_source_anchor_contains_execution_authority",
            extra_verification["blockers"],
        )
        oversized = dict(anchor)
        oversized["observation_count"] = 1025
        oversized["settlement_count"] = 1025
        oversized.pop("anchor_hash")
        oversized["anchor_hash"] = canonical_hash(oversized)
        self.assertIn(
            "local_source_anchor_count_invalid",
            verify_portfolio_forward_local_source_anchor(oversized)["blockers"],
        )

        numeric_hash = dict(anchor)
        numeric_hash["candidate_hash"] = int("1" * 64)
        numeric_hash.pop("anchor_hash")
        numeric_hash["anchor_hash"] = canonical_hash(numeric_hash)
        self.assertIn(
            "local_source_anchor_candidate_hash_invalid",
            verify_portfolio_forward_local_source_anchor(numeric_hash)["blockers"],
        )

        zero_timestamp = dict(anchor)
        zero_timestamp["archive_generated_at"] = 0
        zero_timestamp.pop("anchor_hash")
        zero_timestamp["anchor_hash"] = canonical_hash(zero_timestamp)
        self.assertIn(
            "local_source_anchor_generated_at_invalid",
            verify_portfolio_forward_local_source_anchor(zero_timestamp)["blockers"],
        )

    def test_v3_archive_emits_verified_anchor_only_after_deep_cross_binding(self) -> None:
        fixture = self._anchor_fixture()
        material = portfolio_evidence_archive._local_source_anchor_material(
            candidate_hash=str(fixture["candidate_hash"]),
            observations=dict(fixture["observations"]),
            settlements=list(fixture["settlements"]),
            shadow_audit=dict(fixture["shadow_audit"]),
            performance_summary=dict(fixture["performance_summary"]),
        )
        self.assertEqual(
            material,
            {
                "observer_projection": fixture["observer_projection"],
                "settlement_projection": fixture["settlement_projection"],
            },
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rehearsal, required = self._write_v3_archive(root)
            manifest = portfolio_evidence_archive._read_json(root / "manifest.json")
            database_snapshots = {
                item["source_name"]: item for item in manifest["database_snapshots"]
            }
            material = dict(material)
            material["database_sha256"] = {
                name: str(record["sha256"])
                for name, record in database_snapshots.items()
                if name in {
                    "portfolio_shadow.sqlite",
                    "portfolio_forward_performance.sqlite",
                }
            }
            fresh_rehearsal = dict(rehearsal)
            fresh_rehearsal[portfolio_evidence_archive._LOCAL_SOURCE_ANCHOR_MATERIAL_FIELD] = material
            result = self._verify_synthetic_v3(root, fresh_rehearsal, required)

        self.assertEqual(result["status"], "PASS")
        anchor = result["local_source_anchor"]
        self.assertEqual(anchor["status"], "VERIFIED")
        self.assertEqual(anchor["candidate_hash"], fixture["candidate_hash"])
        self.assertEqual(anchor["archive_manifest_hash"], result["manifest_hash"])
        self.assertEqual(anchor["archive_generated_at"], 123)
        self.assertEqual(
            anchor["shadow_database_sha256"],
            database_snapshots["portfolio_shadow.sqlite"]["sha256"],
        )
        self.assertEqual(
            anchor["performance_database_sha256"],
            database_snapshots["portfolio_forward_performance.sqlite"]["sha256"],
        )
        self.assertEqual(verify_portfolio_forward_local_source_anchor(anchor)["status"], "PASS")

    def test_deep_cross_binding_rejects_resealed_observation_identity_drift(self) -> None:
        fixture = self._anchor_fixture()
        settlements = list(fixture["settlements"])
        settlements[1] = json.loads(json.dumps(settlements[1]))
        settlements[1]["observation_evidence"]["current"]["decision_hash"] = "f" * 64

        material = portfolio_evidence_archive._local_source_anchor_material(
            candidate_hash=str(fixture["candidate_hash"]),
            observations=dict(fixture["observations"]),
            settlements=settlements,
            shadow_audit=dict(fixture["shadow_audit"]),
            performance_summary=dict(fixture["performance_summary"]),
        )

        self.assertEqual(material, {})

    def test_deep_cross_binding_rejects_authority_aliases_in_archived_ledgers(self) -> None:
        fixture = self._anchor_fixture()
        cases = (
            ("observation", "canTrade"),
            ("settlement", "Paper_Authorized"),
            ("settlement", "可-下单"),
        )
        for target, field in cases:
            with self.subTest(target=target, field=field):
                observations = json.loads(json.dumps(fixture["observations"]))
                settlements = json.loads(json.dumps(fixture["settlements"]))
                if target == "observation":
                    observations[sorted(observations)[0]][field] = True
                else:
                    settlements[0][field] = True
                material = portfolio_evidence_archive._local_source_anchor_material(
                    candidate_hash=str(fixture["candidate_hash"]),
                    observations=observations,
                    settlements=settlements,
                    shadow_audit=dict(fixture["shadow_audit"]),
                    performance_summary=dict(fixture["performance_summary"]),
                )
                self.assertEqual(material, {})

    def test_restore_rehearsal_blocks_database_copy_drift_before_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reports = root / "reports"
            databases = root / "databases"
            reports.mkdir(parents=True)
            databases.mkdir(parents=True)
            portfolio_evidence_archive._atomic_write_json(
                reports / "forward.json",
                {"readiness": {"ledger_audit": {}}},
            )
            portfolio_evidence_archive._atomic_write_json(
                reports / "performance.json",
                {"shadow_audit": {}, "performance": {}},
            )
            expected: dict[str, str] = {}
            for name in (
                "portfolio_shadow.sqlite",
                "portfolio_forward_performance.sqlite",
            ):
                path = databases / name
                path.write_bytes(f"verified:{name}".encode("utf-8"))
                expected[name] = file_sha256(path)

            def drift_copy(_source: Path, destination: Path) -> Path:
                target = Path(destination)
                target.write_bytes(b"changed-after-inventory")
                return target

            pack = {
                "artifacts": {
                    "forward_observation": {"file": "forward.json"},
                    "forward_performance": {"file": "performance.json"},
                }
            }
            with (
                patch.object(
                    portfolio_evidence_archive,
                    "_candidate_archive_verification",
                    return_value={
                        "status": "PASS",
                        "candidate_hash": "c" * 64,
                        "source_file_count": 1,
                    },
                ),
                patch.object(
                    portfolio_evidence_archive,
                    "verify_internal_backtest_pack",
                    return_value={"status": "PASS", "blockers": []},
                ),
                patch.object(
                    portfolio_evidence_archive,
                    "_pack_artifact_verification",
                    return_value={"status": "PASS", "blockers": []},
                ),
                patch.object(
                    portfolio_evidence_archive.shutil,
                    "copy2",
                    side_effect=drift_copy,
                ),
                self.assertRaisesRegex(
                    ValueError,
                    "restore_database_hash_mismatch:portfolio_shadow.sqlite",
                ),
            ):
                portfolio_evidence_archive._restore_rehearsal(
                    root,
                    pack,
                    expected_database_sha256=expected,
                )

    def test_restore_rehearsal_blocks_database_drift_after_ledger_reads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reports = root / "reports"
            databases = root / "databases"
            reports.mkdir(parents=True)
            databases.mkdir(parents=True)
            portfolio_evidence_archive._atomic_write_json(
                reports / "forward.json",
                {"readiness": {"ledger_audit": {}}},
            )
            portfolio_evidence_archive._atomic_write_json(
                reports / "performance.json",
                {"shadow_audit": {}, "performance": {}},
            )
            expected: dict[str, str] = {}
            for name in (
                "portfolio_shadow.sqlite",
                "portfolio_forward_performance.sqlite",
            ):
                path = databases / name
                path.write_bytes(f"verified:{name}".encode("utf-8"))
                expected[name] = file_sha256(path)

            pack = {
                "artifacts": {
                    "forward_observation": {"file": "forward.json"},
                    "forward_performance": {"file": "performance.json"},
                }
            }
            shadow = unittest.mock.MagicMock()
            shadow.observation_dates.return_value = []
            shadow.audit.return_value = {"status": "PASS", "candidate_hash": "c" * 64}
            performance = unittest.mock.MagicMock()
            performance.summary.return_value = {
                "status": "PASS",
                "candidate_hash": "c" * 64,
                "settlement_count": 0,
                "outcome_period_count": 0,
            }
            performance.settlements.return_value = []
            with (
                patch.object(
                    portfolio_evidence_archive,
                    "_candidate_archive_verification",
                    return_value={
                        "status": "PASS",
                        "candidate_hash": "c" * 64,
                        "source_file_count": 1,
                    },
                ),
                patch.object(
                    portfolio_evidence_archive,
                    "verify_internal_backtest_pack",
                    return_value={"status": "PASS", "blockers": []},
                ),
                patch.object(
                    portfolio_evidence_archive,
                    "_pack_artifact_verification",
                    return_value={"status": "PASS", "blockers": []},
                ),
                patch.object(
                    portfolio_evidence_archive,
                    "PortfolioShadowLedger",
                    return_value=shadow,
                ),
                patch.object(
                    portfolio_evidence_archive,
                    "_ArchiveProjectionPerformanceLedger",
                    return_value=performance,
                ),
                patch.object(
                    portfolio_evidence_archive,
                    "file_sha256",
                    side_effect=(
                        expected["portfolio_shadow.sqlite"],
                        expected["portfolio_forward_performance.sqlite"],
                        "f" * 64,
                        expected["portfolio_forward_performance.sqlite"],
                    ),
                ),
                self.assertRaisesRegex(
                    ValueError,
                    "restore_database_post_read_hash_mismatch:portfolio_shadow.sqlite",
                ),
            ):
                portfolio_evidence_archive._restore_rehearsal(
                    root,
                    pack,
                    expected_database_sha256=expected,
                )

    def test_v3_archive_blocks_resealed_detached_source_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rehearsal, required = self._write_v3_archive(root)
            (root / "reports" / "research.json").write_bytes(b'{"kind":"research","value":2}')
            self._reseal_archive_inventory(root)
            result = self._verify_synthetic_v3(root, rehearsal, required)

        self.assertEqual(result["status"], "BLOCK")
        self.assertNotIn("local_source_anchor", result)
        self.assertIn(
            "archive_backtest_bundle_member_hash_mismatch:RESEARCH_REPORT",
            result["blockers"],
        )

    def test_v3_archive_blocks_resealed_missing_detached_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rehearsal, required = self._write_v3_archive(root)
            (root / "reports" / "statistical.json").unlink()
            self._reseal_archive_inventory(root)
            result = self._verify_synthetic_v3(root, rehearsal, required)

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn(
            "archive_backtest_bundle_member_missing:STATISTICAL_AUDIT",
            result["blockers"],
        )

    def test_v3_archive_blocks_resealed_duplicate_key_detached_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rehearsal, required = self._write_v3_archive(root)
            (root / "reports" / "research.json").write_bytes(
                b'{"kind":"research","kind":"ambiguous"}'
            )
            self._reseal_inner_backtest_bundle(root)
            result = self._verify_synthetic_v3(root, rehearsal, required)

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn(
            "archive_backtest_bundle_member_json_invalid:RESEARCH_REPORT",
            result["blockers"],
        )

    def test_archive_strict_json_rejects_nonfinite_and_excessive_nesting(self) -> None:
        invalid_members = (
            b'{"value":NaN}',
            b'{"value":Infinity}',
            b'{"value":1e999}',
            (b'{"value":' + (b"[" * 1500) + b"0" + (b"]" * 1500) + b"}"),
        )
        for raw in invalid_members:
            with self.subTest(prefix=raw[:24]), self.assertRaises(ValueError):
                portfolio_evidence_archive._strict_json_object(raw)

    def test_v3_archive_blocks_duplicate_key_outer_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_v3_archive(root)
            manifest_path = root / "manifest.json"
            raw = manifest_path.read_text(encoding="utf-8")
            manifest_path.write_text(
                raw.replace(
                    '"status": "ARCHIVE_READY",',
                    '"status": "ARCHIVE_READY",\n  "status": "BLOCK",',
                    1,
                ),
                encoding="utf-8",
            )
            result = portfolio_evidence_archive.verify_portfolio_evidence_archive(root)

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("archive_manifest_unavailable:ValueError", result["blockers"])

    def test_public_archive_verifier_fails_closed_on_memory_exhaustion(self) -> None:
        with patch.object(
            portfolio_evidence_archive,
            "_read_strict_bounded_json",
            side_effect=MemoryError("private-path-must-not-escape"),
        ):
            result = portfolio_evidence_archive.verify_portfolio_evidence_archive(
                "C:/private/archive"
            )

        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["blockers"], ["archive_verification_memory_exhausted"])
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])
        self.assertNotIn("private", json.dumps(result, sort_keys=True))

    def test_v3_archive_member_loader_uses_role_specific_bounded_reads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _rehearsal, required = self._write_v3_archive(root)
            descriptor = portfolio_evidence_archive._read_json(root / "manifest.json")[
                "backtest_bundle"
            ]
            with (
                patch.object(
                    portfolio_evidence_archive,
                    "required_internal_backtest_bundle_members",
                    return_value=required,
                ),
                patch.object(
                    portfolio_evidence_archive,
                    "verify_internal_backtest_bundle",
                    return_value={"status": "PASS", "blockers": []},
                ),
                patch.object(
                    portfolio_evidence_archive,
                    "read_bounded_artifact",
                    wraps=portfolio_evidence_archive.read_bounded_artifact,
                ) as bounded_read,
            ):
                result = portfolio_evidence_archive._load_archived_backtest_bundle(
                    root,
                    descriptor,
                )

        self.assertEqual(result["status"], "PASS")
        limits = sorted(call.kwargs["byte_limit"] for call in bounded_read.call_args_list)
        self.assertEqual(
            limits,
            sorted(
                [
                    portfolio_evidence_archive.MAX_PORTFOLIO_INTERNAL_BACKTEST_PACK_BYTES,
                    portfolio_evidence_archive.MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES,
                    portfolio_evidence_archive.MAX_PORTFOLIO_STATISTICAL_AUDIT_BYTES,
                ]
            ),
        )

    def test_v3_archive_member_loader_blocks_symlink_member(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _rehearsal, _required = self._write_v3_archive(root)
            descriptor = portfolio_evidence_archive._read_json(root / "manifest.json")[
                "backtest_bundle"
            ]
            research = root / "reports" / "research.json"
            target = root / "reports" / "research-target.json"
            target.write_bytes(research.read_bytes())
            research.unlink()
            try:
                os.symlink(target, research)
            except OSError as exc:
                self.skipTest(f"symlink creation unavailable: {type(exc).__name__}")
            result = portfolio_evidence_archive._load_archived_backtest_bundle(
                root,
                descriptor,
            )

        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(
            any(
                blocker.startswith(
                    "archive_backtest_bundle_member_read_blocked:RESEARCH_REPORT:"
                )
                for blocker in result["blockers"]
            )
        )

    def test_legacy_v1_and_v2_archive_verification_paths_remain_supported(self) -> None:
        for schema_version, replay_status in (
            (
                portfolio_evidence_archive.PORTFOLIO_EVIDENCE_ARCHIVE_V1_SCHEMA_VERSION,
                "NOT_REQUIRED_FOR_V1",
            ),
            (
                portfolio_evidence_archive.PORTFOLIO_EVIDENCE_ARCHIVE_V2_SCHEMA_VERSION,
                "PASS",
            ),
        ):
            with self.subTest(schema_version=schema_version), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                rehearsal = self._write_legacy_archive(root, schema_version)
                with (
                    patch.object(
                        portfolio_evidence_archive,
                        "verify_internal_backtest_pack",
                        return_value={"status": "PASS", "blockers": []},
                    ),
                    patch.object(
                        portfolio_evidence_archive,
                        "_pack_artifact_verification",
                        return_value={"status": "PASS", "blockers": []},
                    ),
                    patch.object(
                        portfolio_evidence_archive,
                        "_restore_rehearsal",
                        return_value=rehearsal,
                    ),
                    patch.object(
                        portfolio_evidence_archive,
                        "_sqlite_metadata",
                        return_value=self._SQLITE_METADATA,
                    ),
                    patch.object(
                        portfolio_evidence_archive,
                        "verify_portfolio_backtest_replay_bundle",
                        return_value={"status": "PASS", "blockers": []},
                    ),
                ):
                    result = portfolio_evidence_archive.verify_portfolio_evidence_archive(root)

                self.assertEqual(result["status"], "PASS")
                self.assertEqual(result["backtest_replay_status"], replay_status)
                self.assertEqual(result["local_source_anchor"]["status"], "NOT_AVAILABLE")
                self.assertEqual(
                    result["local_source_anchor"]["reason"],
                    "ARCHIVE_SCHEMA_NOT_SUPPORTED",
                )

    def test_online_backup_captures_committed_wal_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.sqlite"
            destination = root / "backup.sqlite"
            connection = sqlite3.connect(source)
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("CREATE TABLE evidence(id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
            connection.execute("INSERT INTO evidence(value) VALUES('captured')")
            connection.commit()

            result = backup_sqlite_database(source, destination)
            with closing(sqlite3.connect(destination)) as restored:
                values = restored.execute("SELECT value FROM evidence").fetchall()
            connection.close()
            destination_hash = file_sha256(destination)
            destination_sidecars = [Path(f"{destination}{suffix}").exists() for suffix in ("-wal", "-shm")]

        self.assertEqual(values, [("captured",)])
        self.assertEqual(result["quick_check"], ["ok"])
        self.assertEqual(result["journal_mode"].lower(), "delete")
        self.assertEqual(result["row_counts"], {"evidence": 1})
        self.assertEqual(result["sha256"], destination_hash)
        self.assertEqual(destination_sidecars, [False, False])

    def test_backup_status_is_hashed_and_has_no_execution_authority(self) -> None:
        result = self._backup_result(100)
        status = build_portfolio_backup_status(generated_at=100, result=result)

        self.assertEqual(status["status"], "PASS")
        self.assertEqual(status["schema_version"], PORTFOLIO_BACKUP_STATUS_SCHEMA_VERSION)
        self.assertEqual(set(status), PORTFOLIO_BACKUP_STATUS_V2_FIELDS)
        self.assertEqual(status["local_source_anchor"]["status"], "VERIFIED")
        self.assertFalse(status["paper_authorized"])
        self.assertFalse(status["live_order_allowed"])
        self.assertEqual(verify_portfolio_backup_status(status)["status"], "PASS")

        tampered = dict(status)
        tampered["bundle_path"] = "different"
        self.assertEqual(verify_portfolio_backup_status(tampered)["status"], "BLOCK")

    def test_resealed_backup_status_with_authority_alias_is_blocked(self) -> None:
        status = build_portfolio_backup_status(
            generated_at=100,
            result=self._backup_result(100),
        )
        status["nested_alias_probe"] = {"paperAuthorized": True}
        status.pop("status_hash", None)
        status["status_hash"] = canonical_hash(status)

        verification = verify_portfolio_backup_status(status)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("backup_status_contains_execution_authority", verification["blockers"])

    def test_signed_but_semantically_inconsistent_backup_status_is_blocked(self) -> None:
        status = build_portfolio_backup_status(generated_at=100, error=RuntimeError("capture failed"))
        status["status"] = "PASS"
        status["severity"] = "INFO"
        status["status_hash"] = canonical_hash({key: value for key, value in status.items() if key != "status_hash"})

        verification = verify_portfolio_backup_status(status)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("backup_status_semantics_inconsistent", verification["blockers"])

    def test_backup_v1_verifier_remains_frozen_compatible(self) -> None:
        legacy = {
            "schema_version": PORTFOLIO_BACKUP_STATUS_V1_SCHEMA_VERSION,
            "status": "PASS",
            "severity": "INFO",
            "generated_at": 100,
            "candidate_hash": "legacy-candidate",
            "bundle_path": "legacy-bundle",
            "manifest_hash": "legacy-manifest",
            "pack_hash": "legacy-pack",
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
        legacy["status_hash"] = canonical_hash(legacy)

        verification = verify_portfolio_backup_status(legacy)

        self.assertEqual(verification["status"], "PASS")

    def test_backup_v1_malformed_blockers_fail_closed_without_exception(self) -> None:
        legacy = {
            "schema_version": PORTFOLIO_BACKUP_STATUS_V1_SCHEMA_VERSION,
            "status": "BLOCK",
            "severity": "CRITICAL",
            "generated_at": 100,
            "candidate_hash": "legacy-candidate",
            "bundle_path": "legacy-bundle",
            "manifest_hash": "legacy-manifest",
            "pack_hash": "legacy-pack",
            "verification_status": "PASS",
            "blockers": 1,
            "error_type": "",
            "error": "",
            "backup_only": True,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
            "alert_condition_hash": "legacy-condition",
        }
        legacy["status_hash"] = canonical_hash(legacy)

        verification = verify_portfolio_backup_status(legacy)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("backup_status_blockers_invalid", verification["blockers"])

    def test_backup_public_verifier_bounds_malformed_nesting_and_memory_failure(self) -> None:
        nested: dict[str, object] = {
            "schema_version": PORTFOLIO_BACKUP_STATUS_SCHEMA_VERSION,
        }
        cursor = nested
        for _ in range(40):
            child: dict[str, object] = {}
            cursor["nested"] = child
            cursor = child

        self.assertEqual(
            verify_portfolio_backup_status(None)["blockers"],
            ["backup_status_not_object"],
        )
        self.assertEqual(
            verify_portfolio_backup_status(nested)["blockers"],
            ["backup_status_structure_invalid"],
        )
        with patch(
            "exchange_terminal.services.portfolio_forward_local_source_receipt.local_receipt_json_shape_valid",
            side_effect=MemoryError("private-path-must-not-escape"),
        ):
            exhausted = verify_portfolio_backup_status({
                "schema_version": PORTFOLIO_BACKUP_STATUS_SCHEMA_VERSION,
            })
        self.assertEqual(
            exhausted["blockers"],
            ["backup_status_verification_memory_exhausted"],
        )

    def test_backup_v2_zero_chain_is_exact_not_available_not_fake_verified(self) -> None:
        result = self._backup_result(100)
        result["verification"].pop("local_source_anchor")

        status = build_portfolio_backup_status(generated_at=100, result=result)

        self.assertEqual(status["status"], "PASS")
        self.assertEqual(status["local_source_anchor"]["status"], "NOT_AVAILABLE")
        self.assertEqual(status["local_source_anchor"]["observation_count"], 0)
        self.assertEqual(status["local_source_anchor"]["settlement_count"], 0)
        self.assertEqual(verify_portfolio_backup_status(status)["status"], "PASS")

    def test_backup_v2_candidate_manifest_and_time_binding_cannot_be_resealed_to_pass(self) -> None:
        status = build_portfolio_backup_status(
            generated_at=100,
            result=self._backup_result(100),
        )
        attacks: list[tuple[str, dict[str, object]]] = []
        for field, value in (
            ("candidate_hash", "f" * 64),
            ("manifest_hash", "9" * 64),
        ):
            payload = json.loads(json.dumps(status))
            payload[field] = value
            payload["status_hash"] = canonical_hash({
                key: item for key, item in payload.items() if key != "status_hash"
            })
            attacks.append((field, payload))
        timestamp = json.loads(json.dumps(status))
        timestamp["local_source_anchor"]["archive_generated_at"] = 99
        timestamp["local_source_anchor"].pop("anchor_hash")
        timestamp["local_source_anchor"]["anchor_hash"] = canonical_hash(
            timestamp["local_source_anchor"]
        )
        timestamp["status_hash"] = canonical_hash({
            key: item for key, item in timestamp.items() if key != "status_hash"
        })
        attacks.append(("archive_generated_at", timestamp))

        for name, payload in attacks:
            with self.subTest(name=name):
                verification = verify_portfolio_backup_status(payload)
                self.assertEqual(verification["status"], "BLOCK")
                self.assertIn(
                    "backup_status_semantics_inconsistent",
                    verification["blockers"],
                )

    def test_backup_v2_exact_fields_reject_resealed_extension(self) -> None:
        status = build_portfolio_backup_status(
            generated_at=100,
            result=self._backup_result(100),
        )
        status["external_authenticity_proven"] = True
        status["status_hash"] = canonical_hash({
            key: value for key, value in status.items() if key != "status_hash"
        })

        verification = verify_portfolio_backup_status(status)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("backup_status_fields_invalid", verification["blockers"])

    def test_full_capture_retries_after_transient_failure(self) -> None:
        expected = {"status": "ARCHIVED", "verification": {"status": "PASS"}}
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(
                portfolio_evidence_archive,
                "_create_portfolio_evidence_archive_once",
                side_effect=[ValueError("snapshot race"), expected],
            ) as capture:
                result = portfolio_evidence_archive.create_portfolio_evidence_archive(
                    Path(temporary) / "runtime",
                    generated_at=100,
                    max_attempts=2,
                )

        self.assertEqual(result, expected)
        self.assertEqual(capture.call_count, 2)
        self.assertEqual(capture.call_args_list[1].kwargs["capture_attempt"], 2)

    def test_failed_backup_alert_is_deduplicated_and_recovery_is_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            status_path = root / "status.json"
            alert_path = root / "alerts.jsonl"
            failed = build_portfolio_backup_status(generated_at=100, error=RuntimeError("capture failed"))
            record_portfolio_backup_status(status_path=status_path, alert_path=alert_path, payload=failed)
            record_portfolio_backup_status(status_path=status_path, alert_path=alert_path, payload=failed)
            passed = build_portfolio_backup_status(
                generated_at=200,
                result=self._backup_result(200),
            )
            record_portfolio_backup_status(status_path=status_path, alert_path=alert_path, payload=passed)
            alerts = [json.loads(line) for line in alert_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(len(alerts), 2)
        self.assertEqual(alerts[0]["event_type"], "PORTFOLIO_FORWARD_BACKUP_ALERT")
        self.assertEqual(alerts[1]["event_type"], "PORTFOLIO_FORWARD_BACKUP_RECOVERY")
        self.assertEqual(canonical_hash({k: v for k, v in passed.items() if k != "status_hash"}), passed["status_hash"])

    def test_unverified_previous_backup_status_cannot_suppress_a_real_alert(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            status_path = root / "status.json"
            alert_path = root / "alerts.jsonl"
            failed = build_portfolio_backup_status(
                generated_at=100,
                error=RuntimeError("capture failed"),
            )
            forged_previous = json.loads(json.dumps(failed))
            forged_previous["status_hash"] = "0" * 64
            status_path.write_text(json.dumps(forged_previous), encoding="utf-8")

            record_portfolio_backup_status(
                status_path=status_path,
                alert_path=alert_path,
                payload=failed,
            )
            alerts = [
                json.loads(line)
                for line in alert_path.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(len(alerts), 1)
        self.assertEqual(
            alerts[0]["event_type"],
            "PORTFOLIO_FORWARD_BACKUP_ALERT",
        )

    def test_verified_legacy_previous_backup_still_deduplicates_the_same_block(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            status_path = root / "status.json"
            alert_path = root / "alerts.jsonl"
            failed = build_portfolio_backup_status(
                generated_at=100,
                error=RuntimeError("capture failed"),
            )
            legacy_previous = {
                "schema_version": PORTFOLIO_BACKUP_STATUS_V1_SCHEMA_VERSION,
                "status": "BLOCK",
                "severity": "CRITICAL",
                "generated_at": 100,
                "candidate_hash": "",
                "bundle_path": "",
                "manifest_hash": "",
                "pack_hash": "",
                "verification_status": "BLOCK",
                "blockers": ["backup_capture_failed:RuntimeError"],
                "error_type": "RuntimeError",
                "error": "capture failed",
                "backup_only": True,
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
                "alert_condition_hash": failed["alert_condition_hash"],
            }
            legacy_previous["status_hash"] = canonical_hash(legacy_previous)
            self.assertEqual(
                verify_portfolio_backup_status(legacy_previous)["status"],
                "PASS",
            )
            status_path.write_text(json.dumps(legacy_previous), encoding="utf-8")

            record_portfolio_backup_status(
                status_path=status_path,
                alert_path=alert_path,
                payload=failed,
            )
            alert_exists = alert_path.exists()

        self.assertFalse(alert_exists)


if __name__ == "__main__":
    unittest.main()
