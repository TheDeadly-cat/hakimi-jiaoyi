from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from exchange_terminal.services.portfolio_candidate import (
    PORTFOLIO_CANDIDATE_SCHEMA_VERSION,
    PORTFOLIO_CANDIDATE_SELF_CONSISTENCY_VERSION,
    build_frozen_portfolio_candidate,
    verify_frozen_portfolio_candidate,
)
from tests.test_portfolio_candidate import promising_report


def canonical_hash(payload: object) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def reseal(candidate: dict[str, object], mutate) -> dict[str, object]:
    changed = deepcopy(candidate)
    mutate(changed)
    payload = deepcopy(changed)
    payload.pop("candidate_hash", None)
    changed["candidate_hash"] = canonical_hash(payload)
    return changed


class PortfolioCandidateSelfConsistencyV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.source = self.root / "strategy_source.py"
        self.source.write_text("VALUE = 1\n", encoding="utf-8")
        report = promising_report(self.root, [self.source])
        self.report = report
        self.candidate = build_frozen_portfolio_candidate(
            report,
            source_files=[self.source],
        )

    def test_baseline_candidate_uses_v7_self_consistency_contract(self) -> None:
        verification = verify_frozen_portfolio_candidate(self.candidate)

        self.assertEqual(PORTFOLIO_CANDIDATE_SCHEMA_VERSION, "frozen-portfolio-candidate-v7")
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(
            verification["self_consistency_version"],
            PORTFOLIO_CANDIDATE_SELF_CONSISTENCY_VERSION,
        )

    def test_resealed_invalid_universe_is_blocked(self) -> None:
        attacked = reseal(
            self.candidate,
            lambda item: item["research_governance"].__setitem__(
                "universe_contract",
                {},
            ),
        )

        verification = verify_frozen_portfolio_candidate(attacked)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertTrue(
            any(
                blocker.startswith("candidate_universe_contract:")
                for blocker in verification["blockers"]
            )
        )

    def test_resealed_invalid_temporal_audit_hash_is_blocked(self) -> None:
        attacked = reseal(
            self.candidate,
            lambda item: item["research_governance"]["temporal_exposure_audit"].__setitem__(
                "audit_hash",
                "invalid",
            ),
        )

        verification = verify_frozen_portfolio_candidate(attacked)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "candidate_temporal_exposure_audit_hash_invalid",
            verification["blockers"],
        )

    def test_resealed_candidate_id_mismatch_is_blocked(self) -> None:
        attacked = reseal(
            self.candidate,
            lambda item: item.__setitem__("candidate_id", "DIFFERENT_CANDIDATE"),
        )

        verification = verify_frozen_portfolio_candidate(attacked)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("candidate_id_spec_mismatch", verification["blockers"])

    def test_empty_report_hash_blocks_build_and_resealed_candidate(self) -> None:
        report = deepcopy(self.report)
        report["batch_run_hash"] = ""
        built = build_frozen_portfolio_candidate(report, source_files=[self.source])
        attacked = reseal(
            self.candidate,
            lambda item: item.__setitem__("research_report_hash", ""),
        )

        self.assertEqual(built["status"], "BLOCK")
        self.assertIn(
            "candidate_anchor_invalid:research_report_hash",
            built["blockers"],
        )
        verification = verify_frozen_portfolio_candidate(attacked)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "candidate_anchor_invalid:research_report_hash",
            verification["blockers"],
        )

    def test_non_object_candidate_fails_closed_without_exception(self) -> None:
        for candidate in (None, "candidate", ["candidate"]):
            with self.subTest(candidate=repr(candidate)):
                verification = verify_frozen_portfolio_candidate(candidate)
                self.assertEqual(verification["status"], "BLOCK")
                self.assertEqual(
                    verification["blockers"],
                    ["candidate_object_required"],
                )
                self.assertFalse(verification["paper_authorized"])
                self.assertFalse(verification["live_order_allowed"])


if __name__ == "__main__":
    unittest.main()
