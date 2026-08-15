from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services import portfolio_backtest_campaign as campaign


def sealed_replay_result(*, status: str = "PASS", blockers: list[str] | None = None) -> dict[str, object]:
    passed = status == "PASS"
    payload: dict[str, object] = {
        "schema_version": "portfolio-backtest-replay-result-v1",
        "status": status,
        "checks": {
            "full_result_hash_matches": passed,
            "network_not_accessed": True,
            "mutable_database_not_accessed": True,
        },
        "blockers": list(blockers or []),
        "dataset_hash": "dataset-hash",
        "network_access_attempt_count": 0,
        "database_access_attempt_count": 0,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["replay_hash"] = campaign.canonical_hash(payload)
    return payload


def make_bundle(root: Path) -> Path:
    bundle = root / "archive"
    report_dir = bundle / "reports"
    report_dir.mkdir(parents=True)
    pack = {
        "schema_version": "portfolio-internal-backtest-pack-v2",
        "status": "INTERNAL_BACKTEST_EVIDENCE_READY",
        "promotion_status": "BLOCK",
        "candidate": {
            "candidate_hash": "candidate-hash",
            "dataset_hash": "dataset-hash",
        },
        "historical_backtest": {"test_return_pct": 1.0},
        "statistical_claim": {"status": "BLOCK"},
        "forward_progress": {"observations": 0},
        "promotion_blockers": ["minimum_forward_outcomes"],
        "checks": {"artifact_verification_only": True},
        "evidence_hash": "evidence-hash",
        "pack_hash": "pack-hash",
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    pack_path = report_dir / "pack.json"
    pack_path.write_text(json.dumps(pack), encoding="utf-8")
    replay = sealed_replay_result()
    manifest = {
        "schema_version": "portfolio-evidence-archive-v2",
        "status": "ARCHIVE_READY",
        "bundle_id": "test-bundle",
        "candidate_hash": "candidate-hash",
        "backtest_pack": {"archive_path": "reports/pack.json"},
        "backtest_replay": {
            "schema_version": "portfolio-backtest-replay-bundle-v1",
            "bundle_hash": "bundle-hash",
            "dataset_snapshot_hash": "snapshot-hash",
            "candidate_dataset_hash": "dataset-hash",
            "replay_rehearsal": replay,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    manifest["manifest_hash"] = campaign.canonical_hash(manifest)
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return bundle


def archive_verification() -> dict[str, object]:
    return {
        "status": "PASS",
        "blockers": [],
        "candidate_hash": "candidate-hash",
        "manifest_hash": "manifest-hash",
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def write_contract(root: Path, contract: dict[str, object]) -> Path:
    path = root / "campaign-contract.json"
    path.write_text(json.dumps(contract), encoding="utf-8")
    return path


class PortfolioBacktestCampaignTests(unittest.TestCase):
    def test_resealed_contract_with_authority_alias_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = make_bundle(Path(temporary))
            contract = campaign.build_internal_backtest_campaign_contract(
                bundle,
                declared_at=100,
                repetitions=3,
                timeout_seconds=5,
            )
            contract["nested_alias_probe"] = {"Paper_Authorized": True}
            contract.pop("contract_hash", None)
            contract["contract_hash"] = campaign.canonical_hash(contract)

            verification = campaign.verify_internal_backtest_campaign_contract(
                contract,
                bundle,
            )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "campaign_contract_contains_execution_authority",
            verification["blockers"],
        )

    def test_campaign_requires_external_preregistered_contract_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = make_bundle(Path(temporary))
            contract = campaign.build_internal_backtest_campaign_contract(
                bundle,
                declared_at=100,
                repetitions=3,
                timeout_seconds=5,
            )

            with self.assertRaises(FileNotFoundError):
                campaign.run_internal_backtest_campaign(
                    bundle,
                    contract,
                    generated_at=200,
                    contract_file_path=Path(temporary) / "missing-contract.json",
                )

    def test_fixed_replay_campaign_is_deterministic_and_adds_no_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = make_bundle(Path(temporary))
            contract = campaign.build_internal_backtest_campaign_contract(
                bundle,
                declared_at=100,
                repetitions=3,
                timeout_seconds=5,
            )
            contract_path = write_contract(Path(temporary), contract)
            with (
                patch.object(campaign.evidence_archive_module, "verify_portfolio_evidence_archive", return_value=archive_verification()),
                patch.object(campaign.replay_module, "run_isolated_portfolio_backtest_replay", return_value=sealed_replay_result()),
            ):
                report = campaign.run_internal_backtest_campaign(
                    bundle,
                    contract,
                    generated_at=200,
                    contract_file_path=contract_path,
                )
                verification = campaign.verify_internal_backtest_campaign_report(
                    report,
                    bundle,
                    rerun_replays=True,
                )

        self.assertEqual(report["status"], campaign.CAMPAIGN_PASS_STATUS)
        self.assertEqual(report["metrics"]["completed_repetitions"], 3)
        self.assertEqual(report["metrics"]["unique_replay_hash_count"], 1)
        self.assertEqual(report["metrics"]["independent_sample_increment"], 0)
        self.assertEqual(report["metrics"]["forward_observation_increment"], 0)
        self.assertFalse(report["paper_authorized"])
        self.assertFalse(report["live_order_allowed"])
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["rerun_replay_count"], 3)

    def test_resealed_pass_claim_cannot_hide_failed_replay(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = make_bundle(Path(temporary))
            contract = campaign.build_internal_backtest_campaign_contract(
                bundle,
                declared_at=100,
                repetitions=3,
                timeout_seconds=5,
            )
            contract_path = write_contract(Path(temporary), contract)
            failed = sealed_replay_result(status="BLOCK", blockers=["engine_mismatch"])
            with (
                patch.object(campaign.evidence_archive_module, "verify_portfolio_evidence_archive", return_value=archive_verification()),
                patch.object(campaign.replay_module, "run_isolated_portfolio_backtest_replay", return_value=failed),
            ):
                report = campaign.run_internal_backtest_campaign(
                    bundle,
                    contract,
                    generated_at=200,
                    contract_file_path=contract_path,
                )
                forged = deepcopy(report)
                forged["status"] = campaign.CAMPAIGN_PASS_STATUS
                forged["conclusion"] = "REPRODUCIBILITY_PASS_NOT_PROMOTION_EVIDENCE"
                forged["blockers"] = []
                forged["checks"] = {key: True for key in forged["checks"]}
                forged.pop("campaign_hash", None)
                forged["campaign_hash"] = campaign.canonical_hash(forged)
                verification = campaign.verify_internal_backtest_campaign_report(
                    forged,
                    bundle,
                    rerun_replays=False,
                )

        self.assertEqual(report["status"], campaign.CAMPAIGN_BLOCK_STATUS)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("campaign_report_checks_semantics_mismatch", verification["blockers"])
        self.assertIn("campaign_report_status_semantics_mismatch", verification["blockers"])

    def test_resealed_replay_result_cannot_upgrade_campaign_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = make_bundle(Path(temporary))
            contract = campaign.build_internal_backtest_campaign_contract(
                bundle,
                declared_at=100,
                repetitions=3,
                timeout_seconds=5,
            )
            contract_path = write_contract(Path(temporary), contract)
            original = sealed_replay_result()
            with (
                patch.object(campaign.evidence_archive_module, "verify_portfolio_evidence_archive", return_value=archive_verification()),
                patch.object(campaign.replay_module, "run_isolated_portfolio_backtest_replay", return_value=original),
            ):
                report = campaign.run_internal_backtest_campaign(
                    bundle,
                    contract,
                    generated_at=200,
                    contract_file_path=contract_path,
                )
            forged = deepcopy(report)
            changed = dict(forged["run_records"][0]["result"])
            changed["dataset_manifest_hash"] = "forged-but-resealed"
            changed.pop("replay_hash", None)
            changed["replay_hash"] = campaign.canonical_hash(changed)
            forged["run_records"][0] = campaign._build_run_record(
                1,
                changed,
                forged["run_records"][0]["duration_ms"],
            )
            forged["metrics"] = campaign._campaign_metrics(forged["run_records"], requested=3)
            forged["checks"]["replay_hash_matches_archived_rehearsal"] = False
            forged["checks"]["replay_hash_deterministic_across_processes"] = False
            forged["blockers"] = campaign._outcome_blockers(forged["checks"], forged["run_records"])
            forged["status"] = campaign.CAMPAIGN_BLOCK_STATUS
            forged["conclusion"] = "REPRODUCIBILITY_BLOCKED"
            forged.pop("campaign_hash", None)
            forged["campaign_hash"] = campaign.canonical_hash(forged)
            with (
                patch.object(campaign.evidence_archive_module, "verify_portfolio_evidence_archive", return_value=archive_verification()),
                patch.object(campaign.replay_module, "run_isolated_portfolio_backtest_replay", return_value=original),
            ):
                verification = campaign.verify_internal_backtest_campaign_report(
                    forged,
                    bundle,
                    rerun_replays=True,
                )

        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["claim_status"], campaign.CAMPAIGN_BLOCK_STATUS)
        self.assertEqual(verification["rerun_replay_count"], 0)

    def test_campaign_detects_archive_mutation_during_replay(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = make_bundle(Path(temporary))
            contract = campaign.build_internal_backtest_campaign_contract(
                bundle,
                declared_at=100,
                repetitions=3,
                timeout_seconds=5,
            )
            contract_path = write_contract(Path(temporary), contract)
            calls = 0

            def mutating_replay(*args: object, **kwargs: object) -> dict[str, object]:
                nonlocal calls
                del args, kwargs
                calls += 1
                if calls == 1:
                    (bundle / "unexpected.txt").write_text("mutation", encoding="utf-8")
                return sealed_replay_result()

            with (
                patch.object(campaign.evidence_archive_module, "verify_portfolio_evidence_archive", return_value=archive_verification()),
                patch.object(campaign.replay_module, "run_isolated_portfolio_backtest_replay", side_effect=mutating_replay),
            ):
                report = campaign.run_internal_backtest_campaign(
                    bundle,
                    contract,
                    generated_at=200,
                    contract_file_path=contract_path,
                )

        self.assertEqual(report["status"], campaign.CAMPAIGN_BLOCK_STATUS)
        self.assertFalse(report["checks"]["archive_inventory_unchanged"])
        self.assertEqual(calls, 3)
        self.assertIn(
            "campaign_check_failed:archive_inventory_unchanged",
            report["blockers"],
        )


if __name__ == "__main__":
    unittest.main()
