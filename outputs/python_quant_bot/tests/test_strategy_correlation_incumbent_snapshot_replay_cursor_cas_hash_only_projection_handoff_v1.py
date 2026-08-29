from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import unittest

from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_freshness_replay_gate_v1 as replay_gate,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_cas_transition_hash_only_projection_v1
    as readonly_projection,
)
from exchange_terminal.interfaces import (
    strategy_correlation_incumbent_snapshot_replay_cursor_cas_hash_only_projection_handoff_v1
    as handoff,
)
from tests import (
    test_strategy_correlation_incumbent_snapshot_replay_cursor_cas_transition_hash_only_projection_v1
    as projection_fixture_module,
)


ROOT = Path(__file__).resolve().parents[1]


def _reseal(document: dict[str, object]) -> dict[str, object]:
    mutated = copy.deepcopy(document)
    mutated.pop("readonly_projection_hash", None)
    encoded = json.dumps(
        mutated,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    mutated["readonly_projection_hash"] = hashlib.sha256(encoded).hexdigest()
    return mutated


def _node_canonical_json(value: object) -> str:
    script = r'''
let source = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", chunk => source += chunk);
process.stdin.on("end", () => {
  const sortValue = value => Array.isArray(value)
    ? value.map(sortValue)
    : value && typeof value === "object"
      ? Object.fromEntries(Object.keys(value).sort().map(key => [key, sortValue(value[key])]))
      : value;
  process.stdout.write(JSON.stringify(sortValue(JSON.parse(source))));
});
'''
    completed = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        input=json.dumps(value, ensure_ascii=True, separators=(",", ":")),
        text=True,
        capture_output=True,
        check=False,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr or completed.stdout)
    return completed.stdout


class IncumbentSnapshotReplayCursorCasHashOnlyProjectionHandoffV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        fixture = (
            projection_fixture_module.IncumbentSnapshotReplayCursorCasHashOnlyProjectionV1Tests
        )
        fixture.setUpClass()
        cls.fixture = fixture
        cls.base_cursor = fixture.base_cursor
        cls.attestation = fixture.attestation
        cls.freshness_result = fixture.freshness_result
        cls.fingerprint = fixture.fingerprint
        cls.intent = fixture.intent

    @classmethod
    def build(
        cls,
        *,
        observed_cursor=None,
        freshness_result=None,
        projection_document=None,
        expected_projection_hash=None,
    ):
        observed = observed_cursor or cls.base_cursor
        source_result = freshness_result or cls.freshness_result
        built = cls.fixture.build_projection(
            observed_cursor=observed,
            freshness_result=source_result,
        )
        source = built if projection_document is None else projection_document
        source_hash = (
            expected_projection_hash
            if expected_projection_hash is not None
            else source["readonly_projection_hash"]
            if type(source) is dict
            else "0" * 64
        )
        fingerprint = readonly_projection.cas.fingerprint_incumbent_snapshot_freshness_replay_result_v1(
            source_result
        )
        envelope = handoff.build_incumbent_snapshot_replay_cursor_cas_hash_only_projection_handoff_v1(
            source,
            cls.base_cursor,
            observed,
            cls.attestation,
            source_result,
            cls.intent,
            expected_readonly_projection_hash=source_hash,
            expected_intent_hash=cls.intent.intent_hash,
            expected_freshness_result_fingerprint_sha256=fingerprint,
            expected_attestation_hash=cls.attestation.attestation_hash,
            expected_base_cursor_hash=cls.base_cursor.cursor_hash,
            expected_observed_cursor_hash=observed.cursor_hash,
            expected_stream_id=cls.base_cursor.stream_id,
            expected_projection_preregistration_hash=(
                cls.base_cursor.projection_preregistration_hash
            ),
        )
        return envelope, source, observed, source_result

    @classmethod
    def verify(cls, envelope, source, observed, source_result) -> bool:
        fingerprint = readonly_projection.cas.fingerprint_incumbent_snapshot_freshness_replay_result_v1(
            source_result
        )
        return handoff.verify_incumbent_snapshot_replay_cursor_cas_hash_only_projection_handoff_v1(
            envelope,
            source,
            cls.base_cursor,
            observed,
            cls.attestation,
            source_result,
            cls.intent,
            expected_readonly_projection_hash=source["readonly_projection_hash"],
            expected_intent_hash=cls.intent.intent_hash,
            expected_freshness_result_fingerprint_sha256=fingerprint,
            expected_attestation_hash=cls.attestation.attestation_hash,
            expected_base_cursor_hash=cls.base_cursor.cursor_hash,
            expected_observed_cursor_hash=observed.cursor_hash,
            expected_stream_id=cls.base_cursor.stream_id,
            expected_projection_preregistration_hash=(
                cls.base_cursor.projection_preregistration_hash
            ),
        )

    def test_synthetic_advance_builds_exact_four_field_envelope(self) -> None:
        envelope, source, observed, source_result = self.build()
        self.assertEqual(
            tuple(envelope),
            (
                "schema_version",
                "verification_status",
                "expected_readonly_projection_hash",
                "projection",
            ),
        )
        self.assertEqual(envelope["projection"], source)
        self.assertTrue(self.verify(envelope, source, observed, source_result))

    def test_conflict_and_duplicate_statuses_cross_handoff_unchanged(self) -> None:
        conflict = self.fixture().conflict_cursor()
        duplicate = self.fixture.fixture.simulate(
            self.intent
        ).returned_cursor
        expected = (
            (conflict, readonly_projection.cas.OUTCOME_COMPARE_AND_SWAP_CONFLICT, "UNKNOWN"),
            (duplicate, readonly_projection.cas.OUTCOME_ALREADY_CONSUMED, "BLOCK"),
        )
        for observed, outcome, gate_status in expected:
            with self.subTest(outcome=outcome):
                envelope, source, _, _ = self.build(observed_cursor=observed)
                self.assertEqual(
                    envelope["projection"]["observation"]["outcome"],
                    outcome,
                )
                self.assertEqual(
                    envelope["projection"]["observation"]["gate_status"],
                    gate_status,
                )
                self.assertEqual(envelope["projection"], source)

    def test_wrong_projection_hash_produces_no_handoff(self) -> None:
        envelope, *_ = self.build(expected_projection_hash="0" * 64)
        self.assertIsNone(envelope)

    def test_resealed_authority_promotion_produces_no_handoff(self) -> None:
        source = self.fixture.build_projection()
        tampered = copy.deepcopy(source)
        tampered["authority"]["permission"] = True
        tampered["authority"]["atomic_storage_commit_verified"] = True
        tampered = _reseal(tampered)
        envelope, *_ = self.build(projection_document=tampered)
        self.assertIsNone(envelope)

    def test_resealed_js_unsafe_integer_produces_no_handoff(self) -> None:
        source = self.fixture.build_projection()
        tampered = copy.deepcopy(source)
        tampered["observation"]["candidate_sequence"] = 2**60
        tampered = _reseal(tampered)
        envelope, *_ = self.build(projection_document=tampered)
        self.assertIsNone(envelope)

    def test_exact_handoff_verifier_rejects_envelope_mutation(self) -> None:
        envelope, source, observed, source_result = self.build()
        attacked = copy.deepcopy(envelope)
        attacked["verification_status"] = "FORGED"
        self.assertFalse(self.verify(attacked, source, observed, source_result))
        attacked = copy.deepcopy(envelope)
        attacked["projection"]["authority"]["permission"] = True
        self.assertFalse(self.verify(attacked, source, observed, source_result))

    def test_handoff_is_deep_cloned_and_material_redaction_persists(self) -> None:
        envelope, source, _, _ = self.build()
        envelope["projection"]["consumer_status"] = "MUTATED"
        self.assertNotEqual(source["consumer_status"], "MUTATED")
        serialized = json.dumps(source, ensure_ascii=False, sort_keys=True)
        self.assertNotIn(self.base_cursor.stream_id, serialized)
        self.assertNotIn(self.intent.request_nonce_hash, serialized)
        for consumed_hash in self.base_cursor.consumed_attestation_hashes:
            self.assertNotIn(consumed_hash, serialized)

    def test_node_canonical_json_roundtrip_is_byte_exact(self) -> None:
        envelope, *_ = self.build()
        expected = json.dumps(
            envelope,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        self.assertEqual(_node_canonical_json(envelope), expected)

    def test_upstream_blocked_result_cannot_cross_handoff(self) -> None:
        blocked = replace(
            self.freshness_result,
            status=replay_gate.STATUS_BLOCKED_FRESHNESS_OR_REPLAY,
            blocker_codes=("SNAPSHOT_SEQUENCE_NOT_ABOVE_HIGH_WATER",),
        )
        envelope, *_ = self.build(freshness_result=blocked)
        self.assertIsNone(envelope)

    def test_production_bridge_has_no_io_runtime_or_node_dependency(self) -> None:
        public_names = tuple(
            name for name in dir(handoff) if not name.startswith("_")
        )
        forbidden_prefixes = ("mount_", "write_", "persist_", "publish_")
        self.assertFalse(
            any(name.startswith(forbidden_prefixes) for name in public_names)
        )
        source = Path(handoff.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "open(",
            "subprocess",
            "requests.",
            "urllib.",
            "socket.",
            "sqlite3",
            "register_route(",
            "write_current_pointer(",
            "node ",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
