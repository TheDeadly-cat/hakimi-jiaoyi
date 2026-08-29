from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from exchange_terminal.services.portfolio_forward import (
    ACTIVE_CANDIDATE_REPLACEMENT_GATE_VERSION,
    activate_portfolio_candidate,
    load_active_portfolio_candidate,
)
from tests.test_portfolio_forward import (
    attested_clock,
    candidate,
    experiment_completion_receipt,
    robustness,
)


class PortfolioForwardActivationReplacementGateV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.source = self.root / "engine.py"
        self.source.write_text("VALUE = 1\n", encoding="utf-8")
        self.registry_path = self.root / "active_portfolio_candidate.json"
        self.first, self.first_kwargs = self._activation("FIRST_ACTIVE", 1_020_000)
        first_result = activate_portfolio_candidate(**self.first_kwargs)
        if first_result["status"] != "ACTIVATED":
            raise AssertionError(first_result)

    def _activation(self, generation: str, stamp: int):
        frozen = candidate(self.source, generation=generation)
        candidate_path = self.root / f"portfolio_candidate_{generation}.json"
        candidate_path.write_text(json.dumps(frozen), encoding="utf-8")
        report_path = self.root / f"portfolio_research_{generation}.json"
        report_path.write_text(
            json.dumps({"batch_run_hash": frozen["research_report_hash"]}),
            encoding="utf-8",
        )
        robustness_path = self.root / f"portfolio_robustness_{generation}.json"
        robustness_path.write_text(
            json.dumps(robustness(str(frozen["candidate_hash"]))),
            encoding="utf-8",
        )
        return frozen, {
            "candidate_path": candidate_path,
            "registry_path": self.registry_path,
            "robustness_path": robustness_path,
            "activated_at": stamp,
            "activation_clock_attestation": attested_clock(stamp),
            "experiment_completion_receipt": experiment_completion_receipt(
                frozen,
                report_path=report_path,
                candidate_path=candidate_path,
            ),
        }

    def test_new_activation_declares_replacement_gate(self) -> None:
        pointer = json.loads(self.registry_path.read_text(encoding="utf-8"))

        self.assertEqual(
            pointer["replacement_gate_version"],
            ACTIVE_CANDIDATE_REPLACEMENT_GATE_VERSION,
        )
        self.assertEqual(load_active_portfolio_candidate(self.root)["status"], "PASS")

    def test_different_candidate_requires_retirement_and_preserves_original(self) -> None:
        second, second_kwargs = self._activation("SECOND_ACTIVE", 1_030_000)

        result = activate_portfolio_candidate(**second_kwargs)
        loaded = load_active_portfolio_candidate(self.root)

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn(
            "active_candidate_replacement_requires_retirement",
            result["blockers"],
        )
        self.assertEqual(loaded["status"], "PASS")
        self.assertEqual(loaded["candidate"]["candidate_hash"], self.first["candidate_hash"])
        self.assertNotEqual(loaded["candidate"]["candidate_hash"], second["candidate_hash"])

    def test_exact_retry_is_idempotent_and_does_not_rewrite_registry(self) -> None:
        before = self.registry_path.read_bytes()

        result = activate_portfolio_candidate(**self.first_kwargs)

        self.assertEqual(result["status"], "ALREADY_ACTIVE")
        self.assertEqual(self.registry_path.read_bytes(), before)

    def test_invalid_existing_registry_is_never_overwritten(self) -> None:
        invalid = b'{"status":"BROKEN"}'
        self.registry_path.write_bytes(invalid)
        _, second_kwargs = self._activation("SECOND_ACTIVE", 1_030_000)

        result = activate_portfolio_candidate(**second_kwargs)

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn(
            "existing_active_candidate_registry_status_invalid",
            result["blockers"],
        )
        self.assertEqual(self.registry_path.read_bytes(), invalid)


if __name__ == "__main__":
    unittest.main()
