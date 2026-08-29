from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from exchange_terminal.services.portfolio_forward import (
    ACTIVE_CANDIDATE_DATASET_BINDING_VERSION,
    activate_portfolio_candidate,
    load_active_portfolio_candidate,
    verify_active_candidate_activation,
)
from tests.test_portfolio_forward import (
    attested_clock,
    candidate,
    canonical_hash,
    experiment_completion_receipt,
    robustness,
)


class PortfolioForwardDatasetBindingV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        source = self.root / "engine.py"
        source.write_text("VALUE = 1\n", encoding="utf-8")
        self.candidate_path = self.root / "portfolio_candidate.json"
        self.candidate = candidate(source, generation="DATASET_BINDING_V1")
        self.candidate_path.write_text(json.dumps(self.candidate), encoding="utf-8")
        research_path = self.root / "portfolio_research.json"
        research_path.write_text(
            json.dumps({"batch_run_hash": self.candidate["research_report_hash"]}),
            encoding="utf-8",
        )
        robustness_path = self.root / "portfolio_robustness.json"
        robustness_path.write_text(
            json.dumps(robustness(str(self.candidate["candidate_hash"]))),
            encoding="utf-8",
        )
        self.registry_path = self.root / "active_portfolio_candidate.json"
        activated = activate_portfolio_candidate(
            candidate_path=self.candidate_path,
            registry_path=self.registry_path,
            robustness_path=robustness_path,
            activated_at=1_020_000,
            activation_clock_attestation=attested_clock(1_020_000),
            experiment_completion_receipt=experiment_completion_receipt(
                self.candidate,
                report_path=research_path,
                candidate_path=self.candidate_path,
            ),
        )
        if activated["status"] != "ACTIVATED":
            raise AssertionError(activated)

    def _reseal(self, mutate) -> dict[str, object]:
        pointer = json.loads(self.registry_path.read_text(encoding="utf-8"))
        mutate(pointer)
        pointer.pop("registry_hash", None)
        pointer["registry_hash"] = canonical_hash(pointer)
        self.registry_path.write_text(json.dumps(pointer), encoding="utf-8")
        return pointer

    def test_new_activation_declares_dataset_binding_and_loads(self) -> None:
        pointer = json.loads(self.registry_path.read_text(encoding="utf-8"))
        loaded = load_active_portfolio_candidate(self.root)

        self.assertEqual(
            pointer["dataset_binding_version"],
            ACTIVE_CANDIDATE_DATASET_BINDING_VERSION,
        )
        self.assertEqual(loaded["status"], "PASS")

    def test_resealed_dataset_hash_mismatch_is_blocked(self) -> None:
        self._reseal(
            lambda pointer: pointer.__setitem__(
                "dataset_hash",
                "coherently-resealed-dataset",
            )
        )

        loaded = load_active_portfolio_candidate(self.root)

        self.assertEqual(loaded["status"], "BLOCK")
        self.assertIn("active_candidate_dataset_hash_mismatch", loaded["blockers"])

    def test_resealed_dataset_last_mismatch_is_blocked(self) -> None:
        self._reseal(
            lambda pointer: pointer.__setitem__("dataset_last", "2099-12-31")
        )

        loaded = load_active_portfolio_candidate(self.root)

        self.assertEqual(loaded["status"], "BLOCK")
        self.assertIn("active_candidate_dataset_last_mismatch", loaded["blockers"])

    def test_matching_legacy_v3_pointer_without_subcontract_remains_readable(self) -> None:
        pointer = self._reseal(
            lambda item: item.pop("dataset_binding_version", None)
        )

        activation = verify_active_candidate_activation(pointer)
        loaded = load_active_portfolio_candidate(self.root)

        self.assertEqual(activation["status"], "PASS")
        self.assertEqual(activation["dataset_binding_version"], "")
        self.assertEqual(loaded["status"], "PASS")

    def test_unknown_dataset_binding_version_is_blocked(self) -> None:
        pointer = self._reseal(
            lambda item: item.__setitem__("dataset_binding_version", "unknown-v9")
        )

        activation = verify_active_candidate_activation(pointer)
        loaded = load_active_portfolio_candidate(self.root)

        self.assertEqual(activation["status"], "BLOCK")
        self.assertIn(
            "active_candidate_dataset_binding_version_invalid",
            activation["blockers"],
        )
        self.assertEqual(loaded["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
