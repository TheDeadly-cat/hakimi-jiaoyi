from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import unittest

from tests import (
    test_strategy_correlation_incumbent_snapshot_replay_cursor_cas_hash_only_projection_handoff_v1
    as handoff_fixture_module,
)


ROOT = Path(__file__).resolve().parents[1]
PRESENTER = (
    ROOT
    / "exchange_terminal"
    / "static"
    / "evidence_incumbent_snapshot_replay_cursor_cas_hash_only_projection_v1.js"
)


def _present(envelope: object) -> dict[str, object]:
    script = r'''
const presenter = require(process.argv[1]);
let source = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", chunk => source += chunk);
process.stdin.on("end", () => {
  const envelope = JSON.parse(source);
  const model = presenter.deriveReplayCursorCasViewModelV1(envelope);
  const markup = presenter.renderReplayCursorCasHashOnlyProjectionV1(envelope);
  process.stdout.write(JSON.stringify({
    accepted: model.verificationAccepted,
    outcome: model.rawOutcome,
    gateStatus: model.rawGateStatus,
    label: model.statusLabel,
    stages: model.stages.map(item => item.key),
    sequences: model.sequences.map(item => item.value),
    markup,
  }));
});
'''
    completed = subprocess.run(
        ["node", "-e", script, str(PRESENTER)],
        cwd=ROOT,
        input=json.dumps(envelope, ensure_ascii=True, separators=(",", ":")),
        text=True,
        capture_output=True,
        check=False,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr or completed.stdout)
    return json.loads(completed.stdout)


class IncumbentSnapshotReplayCursorCasProjectionPresenterHandoffV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        fixture = (
            handoff_fixture_module.IncumbentSnapshotReplayCursorCasHashOnlyProjectionHandoffV1Tests
        )
        fixture.setUpClass()
        cls.fixture = fixture

    def test_python_synthetic_advance_is_node_unknown_observation(self) -> None:
        envelope, *_ = self.fixture.build()
        output = _present(envelope)
        self.assertTrue(output["accepted"])
        self.assertEqual(output["outcome"], "ADVANCED_IN_RETURNED_CURSOR")
        self.assertEqual(output["gateStatus"], "UNKNOWN")
        self.assertEqual(output["label"], "合成游标观察")
        self.assertEqual(
            output["stages"],
            ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
        )

    def test_python_conflict_and_duplicate_keep_exact_node_status(self) -> None:
        projection_fixture = self.fixture.fixture
        conflict = projection_fixture().conflict_cursor()
        duplicate = projection_fixture.fixture.simulate(
            self.fixture.intent
        ).returned_cursor
        cases = (
            (conflict, "COMPARE_AND_SWAP_CONFLICT", "UNKNOWN", "并发竞争未闭合"),
            (duplicate, "ALREADY_CONSUMED", "BLOCK", "回放阻断"),
        )
        for observed, outcome, status, label in cases:
            with self.subTest(outcome=outcome):
                envelope, *_ = self.fixture.build(observed_cursor=observed)
                output = _present(envelope)
                self.assertTrue(output["accepted"])
                self.assertEqual(output["outcome"], outcome)
                self.assertEqual(output["gateStatus"], status)
                self.assertEqual(output["label"], label)

    def test_mutated_python_envelope_fails_fixed_unknown_without_reflection(self) -> None:
        envelope, *_ = self.fixture.build()
        attacked = copy.deepcopy(envelope)
        attacked["projection"]["authority"]["permission"] = True
        attacked["projection"]["consumer_status"] = (
            "<img src=x onerror=alert(1)>"
        )
        output = _present(attacked)
        self.assertFalse(output["accepted"])
        self.assertEqual(output["outcome"], "UNKNOWN")
        self.assertEqual(output["label"], "未核验")
        self.assertNotIn("onerror", output["markup"])
        self.assertNotIn("<img", output["markup"])

    def test_node_model_does_not_recover_redacted_python_material(self) -> None:
        envelope, *_ = self.fixture.build()
        output = _present(envelope)
        serialized = json.dumps(output, ensure_ascii=False, sort_keys=True)
        self.assertNotIn(self.fixture.base_cursor.stream_id, serialized)
        self.assertNotIn(self.fixture.intent.request_nonce_hash, serialized)
        for consumed_hash in self.fixture.base_cursor.consumed_attestation_hashes:
            self.assertNotIn(consumed_hash, serialized)
        self.assertNotIn("READY", serialized.upper())


if __name__ == "__main__":
    unittest.main()
