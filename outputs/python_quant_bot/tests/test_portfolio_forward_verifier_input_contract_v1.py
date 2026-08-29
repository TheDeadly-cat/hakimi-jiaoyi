from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from exchange_terminal.services.portfolio_forward import (
    ACTIVE_CANDIDATE_VERIFIER_INPUT_CONTRACT_VERSION,
    activate_portfolio_candidate,
    verify_active_candidate_activation,
)
from tests.test_portfolio_forward import (
    active_registry,
    attested_clock,
    candidate,
    canonical_hash,
    experiment_completion_receipt,
    robustness,
)


def reseal(pointer: dict[str, object], mutate) -> dict[str, object]:
    changed = deepcopy(pointer)
    mutate(changed)
    changed.pop("registry_hash", None)
    changed["registry_hash"] = canonical_hash(changed)
    return changed


class PortfolioForwardVerifierInputContractV1Tests(unittest.TestCase):
    def test_non_object_registry_returns_structured_block(self) -> None:
        for registry in (None, "registry", ["registry"]):
            with self.subTest(registry=repr(registry)):
                result = verify_active_candidate_activation(registry)
                self.assertEqual(result["status"], "BLOCK")
                self.assertEqual(
                    result["blockers"],
                    ["active_candidate_registry_object_required"],
                )
                self.assertFalse(result["paper_authorized"])
                self.assertFalse(result["live_order_allowed"])

    def test_malformed_nested_objects_and_timestamp_block_without_exception(self) -> None:
        base = active_registry(1_020_000)
        cases = (
            (
                lambda item: item.__setitem__("activated_at", "not-an-integer"),
                "candidate_activated_at_invalid",
            ),
            (
                lambda item: item.__setitem__("activation_clock_attestation", "clock"),
                "activation_clock_attestation_object_required",
            ),
            (
                lambda item: item.__setitem__("experiment_completion_receipt", ["receipt"]),
                "experiment_completion_receipt_object_required",
            ),
        )
        for mutate, expected in cases:
            with self.subTest(expected=expected):
                result = verify_active_candidate_activation(reseal(base, mutate))
                self.assertEqual(result["status"], "BLOCK")
                self.assertIn(expected, result["blockers"])

    def test_valid_registry_retains_v3_semantics_and_exposes_input_contract(self) -> None:
        result = verify_active_candidate_activation(active_registry(1_020_000))

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(
            result["input_contract_version"],
            ACTIVE_CANDIDATE_VERIFIER_INPUT_CONTRACT_VERSION,
        )

    def test_activation_rejects_invalid_input_without_writing_registry(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "engine.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            frozen = candidate(source, generation="VERIFIER_INPUT_V1")
            candidate_path = root / "portfolio_candidate.json"
            candidate_path.write_text(json.dumps(frozen), encoding="utf-8")
            report_path = root / "portfolio_research.json"
            report_path.write_text(
                json.dumps({"batch_run_hash": frozen["research_report_hash"]}),
                encoding="utf-8",
            )
            robustness_path = root / "portfolio_robustness.json"
            robustness_path.write_text(
                json.dumps(robustness(str(frozen["candidate_hash"]))),
                encoding="utf-8",
            )
            valid = {
                "candidate_path": candidate_path,
                "robustness_path": robustness_path,
                "activated_at": 1_020_000,
                "activation_clock_attestation": attested_clock(1_020_000),
                "experiment_completion_receipt": experiment_completion_receipt(
                    frozen,
                    report_path=report_path,
                    candidate_path=candidate_path,
                ),
            }
            cases = (
                ({"activated_at": "bad"}, "activation_timestamp_invalid"),
                ({"activation_clock_attestation": "clock"}, "activation_clock_attestation_object_required"),
                ({"experiment_completion_receipt": ["receipt"]}, "experiment_completion_receipt_object_required"),
            )
            for index, (override, expected) in enumerate(cases):
                with self.subTest(expected=expected):
                    registry_path = root / f"active_{index}.json"
                    result = activate_portfolio_candidate(
                        **{**valid, **override, "registry_path": registry_path}
                    )
                    self.assertEqual(result["status"], "BLOCK")
                    self.assertIn(expected, result["blockers"])
                    self.assertFalse(registry_path.exists())


if __name__ == "__main__":
    unittest.main()
