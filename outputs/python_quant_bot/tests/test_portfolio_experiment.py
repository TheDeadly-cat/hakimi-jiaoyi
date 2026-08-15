from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.portfolio_experiment import (
    PortfolioExperimentRegistry,
    verify_completion_against_candidate,
    verify_experiment_completion_receipt,
)
from exchange_terminal.services.trusted_clock import build_trusted_clock_attestation


def canonical_hash(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def attested_clock(stamp: int) -> dict[str, object]:
    evidence = {
        "source": "TEST_CLOCK",
        "endpoint": "https://clock.test/time",
        "status": "PASS",
        "error": "",
        "requested_at_ms": stamp - 5,
        "received_at_ms": stamp + 5,
        "round_trip_ms": 10,
        "midpoint_local_ms": stamp,
        "server_time_ms": stamp,
        "offset_ms": 0,
    }
    evidence["evidence_hash"] = canonical_hash(evidence)
    return build_trusted_clock_attestation(local_now_ms=stamp, provider_evidence=[evidence])


def research_protocol(label: str = "BASE") -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "portfolio-research-protocol-v1",
        "research_generation": f"PORTFOLIO_G12_{label}",
        "hypothesis": "Frozen weekly relative-strength protocol",
        "benchmark_symbol": "SPY",
        "tradable_symbols": ["AAPL", "NVDA"],
        "cutoff": "2026-07-30",
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["protocol_hash"] = canonical_hash(payload)
    return payload


def write_artifacts(root: Path, binding: dict[str, object]) -> tuple[Path, Path, dict[str, object]]:
    report: dict[str, object] = {
        "batch_run_hash": "batch-hash",
        "dataset_manifest": {"data_hash": "dataset-hash"},
        "experiment_governance": binding,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    candidate: dict[str, object] = {
        "candidate_hash": "candidate-hash",
        "research_report_hash": "batch-hash",
        "dataset_hash": "dataset-hash",
        "research_governance": {"experiment_binding": binding},
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    report_path = root / "portfolio_research_test.json"
    candidate_path = root / "portfolio_candidate_test.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
    return report_path, candidate_path, candidate


class PortfolioExperimentRegistryTests(unittest.TestCase):
    def test_registered_experiment_completes_with_auditable_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "engine.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            registry = PortfolioExperimentRegistry(db_path=root / "experiments.sqlite3")
            registered = registry.register(
                protocol=research_protocol(),
                source_files=[source],
                clock_attestation=attested_clock(10_000),
            )
            claimed = registry.claim(
                experiment_id=str(registered["experiment_id"]),
                protocol=research_protocol(),
                source_files=[source],
                clock_attestation=attested_clock(11_000),
            )
            report_path, candidate_path, candidate = write_artifacts(root, claimed["binding"])
            completed = registry.complete(
                experiment_id=str(registered["experiment_id"]),
                report_path=report_path,
                candidate_path=candidate_path,
                clock_attestation=attested_clock(12_000),
            )
            audit = registry.audit()
            summary = registry.summary()

        self.assertEqual(registered["status"], "REGISTERED")
        self.assertEqual(claimed["status"], "CLAIMED")
        self.assertEqual(completed["status"], "COMPLETED")
        self.assertEqual(verify_experiment_completion_receipt(completed["receipt"])["status"], "PASS")
        self.assertEqual(verify_completion_against_candidate(completed["receipt"], candidate)["status"], "PASS")
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(summary["counts"], {"COMPLETED": 1})
        self.assertEqual(summary["experiments"][0]["experiment_id"], registered["experiment_id"])
        self.assertFalse(completed["paper_authorized"])
        self.assertFalse(completed["live_order_allowed"])

    def test_protocol_drift_is_blocked_before_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "engine.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            registry = PortfolioExperimentRegistry(db_path=root / "experiments.sqlite3")
            registered = registry.register(
                protocol=research_protocol("BASE"),
                source_files=[source],
                clock_attestation=attested_clock(20_000),
            )

            result = registry.claim(
                experiment_id=str(registered["experiment_id"]),
                protocol=research_protocol("CHANGED"),
                source_files=[source],
                clock_attestation=attested_clock(21_000),
            )

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("experiment_protocol_drift", result["blockers"])

    def test_source_drift_is_blocked_before_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "engine.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            registry = PortfolioExperimentRegistry(db_path=root / "experiments.sqlite3")
            registered = registry.register(
                protocol=research_protocol(),
                source_files=[source],
                clock_attestation=attested_clock(30_000),
            )
            source.write_text("VALUE = 2\n", encoding="utf-8")

            result = registry.claim(
                experiment_id=str(registered["experiment_id"]),
                protocol=research_protocol(),
                source_files=[source],
                clock_attestation=attested_clock(31_000),
            )

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("experiment_implementation_drift", result["blockers"])

    def test_imported_source_drift_is_blocked_before_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = root / "engine_pkg"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            helper = package / "helper.py"
            source = package / "engine.py"
            helper.write_text("VALUE = 1\n", encoding="utf-8")
            source.write_text("from .helper import VALUE\n", encoding="utf-8")
            registry = PortfolioExperimentRegistry(db_path=root / "experiments.sqlite3")
            registered = registry.register(
                protocol=research_protocol(),
                source_files=[source],
                clock_attestation=attested_clock(32_000),
            )
            helper.write_text("VALUE = 2\n", encoding="utf-8")

            result = registry.claim(
                experiment_id=str(registered["experiment_id"]),
                protocol=research_protocol(),
                source_files=[source],
                clock_attestation=attested_clock(33_000),
            )

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("experiment_implementation_drift", result["blockers"])

    def test_unparseable_source_is_blocked_without_crashing_registration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "engine.py"
            source.write_text("def broken(:\n", encoding="utf-8")
            registry = PortfolioExperimentRegistry(db_path=root / "experiments.sqlite3")

            result = registry.register(
                protocol=research_protocol(),
                source_files=[source],
                clock_attestation=attested_clock(34_000),
            )

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("registration_source_unavailable:ValueError", result["blockers"])

    def test_experiment_can_only_be_claimed_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "engine.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            registry = PortfolioExperimentRegistry(db_path=root / "experiments.sqlite3")
            protocol = research_protocol()
            registered = registry.register(
                protocol=protocol,
                source_files=[source],
                clock_attestation=attested_clock(40_000),
            )
            first = registry.claim(
                experiment_id=str(registered["experiment_id"]),
                protocol=protocol,
                source_files=[source],
                clock_attestation=attested_clock(41_000),
            )
            second = registry.claim(
                experiment_id=str(registered["experiment_id"]),
                protocol=protocol,
                source_files=[source],
                clock_attestation=attested_clock(42_000),
            )

        self.assertEqual(first["status"], "CLAIMED")
        self.assertEqual(second["status"], "BLOCK")
        self.assertIn("experiment_not_claimable:RUNNING", second["blockers"])

    def test_concurrent_claim_has_a_single_winner(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "engine.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            registry = PortfolioExperimentRegistry(db_path=root / "experiments.sqlite3")
            protocol = research_protocol()
            registered = registry.register(
                protocol=protocol,
                source_files=[source],
                clock_attestation=attested_clock(50_000),
            )

            def claim() -> dict[str, object]:
                return registry.claim(
                    experiment_id=str(registered["experiment_id"]),
                    protocol=protocol,
                    source_files=[source],
                    clock_attestation=attested_clock(51_000),
                )

            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(lambda _: claim(), range(2)))

        self.assertEqual(sum(result["status"] == "CLAIMED" for result in results), 1)
        self.assertEqual(sum(result["status"] == "BLOCK" for result in results), 1)

    def test_event_chain_tampering_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "engine.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            db_path = root / "experiments.sqlite3"
            registry = PortfolioExperimentRegistry(db_path=db_path)
            registered = registry.register(
                protocol=research_protocol(),
                source_files=[source],
                clock_attestation=attested_clock(60_000),
            )
            connection = sqlite3.connect(db_path)
            try:
                connection.execute(
                    "UPDATE portfolio_experiment_events SET payload_json = '{}' WHERE seq = 1"
                )
                connection.commit()
            finally:
                connection.close()

            audit = registry.audit()
            record = registry.get(str(registered["experiment_id"]))
            summary = registry.summary()

        self.assertEqual(audit["status"], "BLOCK")
        self.assertTrue(any("event_hash_mismatch" in item for item in audit["blockers"]))
        self.assertEqual(record["status"], "BLOCK")
        self.assertFalse(record["ok"])
        self.assertEqual(summary["status"], "BLOCK")

    def test_corrupt_registry_json_fails_closed_without_crashing_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "engine.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            db_path = root / "experiments.sqlite3"
            registry = PortfolioExperimentRegistry(db_path=db_path)
            registered = registry.register(
                protocol=research_protocol(),
                source_files=[source],
                clock_attestation=attested_clock(65_000),
            )
            connection = sqlite3.connect(db_path)
            try:
                connection.execute(
                    "UPDATE portfolio_experiments SET intent_json = '{' WHERE experiment_id = ?",
                    (str(registered["experiment_id"]),),
                )
                connection.commit()
            finally:
                connection.close()

            record = registry.get(str(registered["experiment_id"]))
            summary = registry.summary()

        self.assertEqual(record["status"], "BLOCK")
        self.assertEqual(record["intent"], {})
        self.assertEqual(summary["status"], "BLOCK")
        self.assertEqual(summary["experiments"][0]["research_generation"], "")

    def test_artifact_tampering_is_detected_after_completion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "engine.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            registry = PortfolioExperimentRegistry(db_path=root / "experiments.sqlite3")
            protocol = research_protocol()
            registered = registry.register(
                protocol=protocol,
                source_files=[source],
                clock_attestation=attested_clock(70_000),
            )
            claimed = registry.claim(
                experiment_id=str(registered["experiment_id"]),
                protocol=protocol,
                source_files=[source],
                clock_attestation=attested_clock(71_000),
            )
            report_path, candidate_path, _ = write_artifacts(root, claimed["binding"])
            completed = registry.complete(
                experiment_id=str(registered["experiment_id"]),
                report_path=report_path,
                candidate_path=candidate_path,
                clock_attestation=attested_clock(72_000),
            )
            report_path.write_text("{}", encoding="utf-8")

            audit = registry.audit()

        self.assertEqual(completed["status"], "COMPLETED")
        self.assertEqual(audit["status"], "BLOCK")
        self.assertTrue(any("report_artifact_hash_mismatch" in item for item in audit["blockers"]))

    def test_protocol_with_execution_authority_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "engine.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            registry = PortfolioExperimentRegistry(db_path=root / "experiments.sqlite3")
            protocol = research_protocol()
            protocol["paper_authorized"] = True
            protocol.pop("protocol_hash")
            protocol["protocol_hash"] = canonical_hash(protocol)

            result = registry.register(
                protocol=protocol,
                source_files=[source],
                clock_attestation=attested_clock(80_000),
            )

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("protocol_has_execution_authority", result["blockers"])

    def test_resealed_string_false_protocol_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "engine.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            registry = PortfolioExperimentRegistry(db_path=root / "experiments.sqlite3")
            protocol = research_protocol()
            protocol["research_only"] = "false"
            protocol.pop("protocol_hash")
            protocol["protocol_hash"] = canonical_hash(protocol)

            result = registry.register(
                protocol=protocol,
                source_files=[source],
                clock_attestation=attested_clock(81_000),
            )

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("protocol_must_be_research_only", result["blockers"])


if __name__ == "__main__":
    unittest.main()
