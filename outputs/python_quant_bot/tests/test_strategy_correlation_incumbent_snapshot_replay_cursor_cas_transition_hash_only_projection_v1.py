from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
import unittest

from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_freshness_replay_gate_v1 as replay_gate,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_cas_transition_hash_only_projection_v1 as projection,
)
from tests import (
    test_strategy_correlation_incumbent_snapshot_replay_cursor_cas_transition_v1 as cas_fixture_module,
)


def _sha(character: str) -> str:
    return character * 64


def _different_hash(*excluded: str | None) -> str:
    for character in "0123456789abcdef":
        candidate = _sha(character)
        if candidate not in excluded:
            return candidate
    raise AssertionError("could not build distinct synthetic hash")


def _reseal(document: dict[str, object]) -> None:
    body = dict(document)
    body.pop("readonly_projection_hash", None)
    canonical = json.dumps(
        body,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    document["readonly_projection_hash"] = sha256(canonical).hexdigest()


def _nested_keys(value: object) -> set[str]:
    if type(value) is dict:
        keys = set(value)
        for nested in value.values():
            keys.update(_nested_keys(nested))
        return keys
    if type(value) in (list, tuple):
        keys: set[str] = set()
        for nested in value:
            keys.update(_nested_keys(nested))
        return keys
    return set()


class IncumbentSnapshotReplayCursorCasHashOnlyProjectionV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        fixture = (
            cas_fixture_module.IncumbentSnapshotReplayCursorCasTransitionV1Tests
        )
        fixture.setUpClass()
        cls.fixture = fixture
        cls.base_cursor = fixture.base_cursor
        cls.attestation = fixture.attestation
        cls.freshness_result = fixture.freshness_result
        cls.fingerprint = fixture.fingerprint
        cls.intent = fixture.build_intent()
        if cls.intent is None:
            raise AssertionError("CAS intent did not build")

    @classmethod
    def build_projection(cls, *, observed_cursor=None, freshness_result=None):
        observed = observed_cursor or cls.base_cursor
        source_result = freshness_result or cls.freshness_result
        fingerprint = (
            projection.cas.fingerprint_incumbent_snapshot_freshness_replay_result_v1(
                source_result
            )
        )
        return projection.build_incumbent_snapshot_replay_cursor_cas_hash_only_projection_v1(
            cls.base_cursor,
            observed,
            cls.attestation,
            source_result,
            cls.intent,
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

    @classmethod
    def verify(cls, document, *, observed_cursor=None, freshness_result=None):
        observed = observed_cursor or cls.base_cursor
        source_result = freshness_result or cls.freshness_result
        fingerprint = (
            projection.cas.fingerprint_incumbent_snapshot_freshness_replay_result_v1(
                source_result
            )
        )
        return projection.verify_incumbent_snapshot_replay_cursor_cas_hash_only_projection_v1(
            document,
            cls.base_cursor,
            observed,
            cls.attestation,
            source_result,
            cls.intent,
            expected_readonly_projection_hash=document.get(
                "readonly_projection_hash",
                _sha("0"),
            ),
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

    def conflict_cursor(self):
        other_hash = _different_hash(
            self.attestation.attestation_hash,
            self.base_cursor.high_water_attestation_hash,
        )
        return replay_gate.build_incumbent_snapshot_replay_cursor_v1(
            stream_id=self.base_cursor.stream_id,
            projection_preregistration_hash=(
                self.base_cursor.projection_preregistration_hash
            ),
            high_water_sequence=self.base_cursor.high_water_sequence,
            high_water_attestation_hash=(
                self.base_cursor.high_water_attestation_hash
            ),
            consumed_attestation_hashes=tuple(
                sorted(self.base_cursor.consumed_attestation_hashes + (other_hash,))
            ),
        )

    def test_exact_success_projection_stays_unknown_and_uncommitted(self) -> None:
        document = self.build_projection()
        self.assertEqual(
            document["observation"]["outcome"],
            projection.cas.OUTCOME_ADVANCED_IN_RETURNED_CURSOR,
        )
        self.assertEqual(
            document["observation"]["gate_status"],
            projection.cas.GATE_STATUS_UNKNOWN,
        )
        self.assertFalse(document["authority"]["permission"])
        self.assertFalse(
            document["authority"]["atomic_storage_commit_verified"]
        )
        self.assertFalse(document["authority"]["current_chain_activated"])

    def test_exact_verifier_recomputes_full_simulation(self) -> None:
        document = self.build_projection()
        self.assertTrue(self.verify(document))

    def test_projection_redacts_raw_cursor_and_nonce_material(self) -> None:
        document = self.build_projection()
        serialized = json.dumps(document, sort_keys=True)
        self.assertNotIn(self.base_cursor.stream_id, serialized)
        self.assertNotIn(self.intent.request_nonce_hash, serialized)
        for consumed_hash in self.base_cursor.consumed_attestation_hashes:
            self.assertNotIn(consumed_hash, serialized)
        document_keys = _nested_keys(document)
        for forbidden_key in (
            "consumed_attestation_hashes",
            "high_water_attestation_hash",
            "request_nonce_hash",
            "returned_cursor",
            "intent_document",
            "receipt_document",
            "raw_symbols",
            "holdings",
            "signature",
            "public_key",
        ):
            self.assertNotIn(forbidden_key, document_keys)

    def test_conflict_projection_is_unknown_and_cursor_unchanged(self) -> None:
        observed = self.conflict_cursor()
        document = self.build_projection(observed_cursor=observed)
        self.assertEqual(
            document["observation"]["outcome"],
            projection.cas.OUTCOME_COMPARE_AND_SWAP_CONFLICT,
        )
        self.assertEqual(
            document["observation"]["gate_status"],
            projection.cas.GATE_STATUS_UNKNOWN,
        )
        self.assertFalse(document["observation"]["returned_cursor_changed"])
        self.assertTrue(self.verify(document, observed_cursor=observed))

    def test_duplicate_projection_preserves_block(self) -> None:
        simulation = self.fixture.simulate(self.intent)
        observed = simulation.returned_cursor
        document = self.build_projection(observed_cursor=observed)
        self.assertEqual(
            document["observation"]["outcome"],
            projection.cas.OUTCOME_ALREADY_CONSUMED,
        )
        self.assertEqual(
            document["observation"]["gate_status"],
            projection.cas.GATE_STATUS_BLOCK,
        )
        self.assertTrue(self.verify(document, observed_cursor=observed))

    def test_resealed_authority_promotion_is_rejected(self) -> None:
        document = self.build_projection()
        attacked = deepcopy(document)
        attacked["observation"]["gate_status"] = "PASS"
        attacked["authority"]["permission"] = True
        attacked["authority"]["atomic_storage_commit_verified"] = True
        _reseal(attacked)
        self.assertFalse(self.verify(attacked))

    def test_resealed_raw_material_alias_is_rejected(self) -> None:
        document = self.build_projection()
        attacked = deepcopy(document)
        attacked["raw_cursor"] = {
            "stream_id": self.base_cursor.stream_id,
            "consumed": list(self.base_cursor.consumed_attestation_hashes),
        }
        _reseal(attacked)
        self.assertFalse(self.verify(attacked))

    def test_wrong_expected_hashes_fail_closed(self) -> None:
        document = self.build_projection()
        wrong = _different_hash(document["readonly_projection_hash"])
        self.assertFalse(
            projection.verify_incumbent_snapshot_replay_cursor_cas_hash_only_projection_v1(
                document,
                self.base_cursor,
                self.base_cursor,
                self.attestation,
                self.freshness_result,
                self.intent,
                expected_readonly_projection_hash=wrong,
                expected_intent_hash=self.intent.intent_hash,
                expected_freshness_result_fingerprint_sha256=self.fingerprint,
                expected_attestation_hash=self.attestation.attestation_hash,
                expected_base_cursor_hash=self.base_cursor.cursor_hash,
                expected_observed_cursor_hash=self.base_cursor.cursor_hash,
                expected_stream_id=self.base_cursor.stream_id,
                expected_projection_preregistration_hash=(
                    self.base_cursor.projection_preregistration_hash
                ),
            )
        )

    def test_resealed_upstream_candidate_promotion_cannot_rebuild(self) -> None:
        blocked = replace(
            self.freshness_result,
            status=replay_gate.STATUS_BLOCKED_FRESHNESS_OR_REPLAY,
            blocker_codes=("SNAPSHOT_SEQUENCE_NOT_ABOVE_HIGH_WATER",),
        )
        self.assertIsNone(self.build_projection(freshness_result=blocked))

    def test_projection_is_deterministic(self) -> None:
        first = self.build_projection()
        second = self.build_projection()
        self.assertEqual(first, second)

    def test_consumer_status_is_unmounted_and_neutral(self) -> None:
        document = self.build_projection()
        serialized = json.dumps(document, sort_keys=True)
        self.assertEqual(
            document["consumer_status"],
            projection.CONSUMER_STATUS,
        )
        self.assertNotIn("READY", serialized)
        self.assertNotIn("profit", serialized.lower())
        self.assertFalse(document["authority"]["paper_authorized"])
        self.assertFalse(document["authority"]["live_authorized"])

    def test_public_api_exposes_no_mount_or_write_operation(self) -> None:
        public_names = tuple(
            name for name in dir(projection) if not name.startswith("_")
        )
        forbidden_prefixes = ("mount_", "write_", "persist_", "publish_")
        self.assertFalse(
            any(name.startswith(forbidden_prefixes) for name in public_names)
        )


if __name__ == "__main__":
    unittest.main()
