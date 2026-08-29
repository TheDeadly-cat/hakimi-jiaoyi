from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import unittest
from unittest.mock import patch

from exchange_terminal.services import strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_lineage_history_coverage_gate_v1 as subject
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


SOURCE_VERIFIER = (
    "verify_strategy_correlation_uncertainty_multi_window_observation_membership_"
    "provider_attestation_lifecycle_replay_checkpoint_persistence_lineage_gate_v1"
)
STUDY_HASH = hashlib.sha256(b"synthetic-study-v1").hexdigest()
WINDOW_HASH = hashlib.sha256(b"synthetic-window-order-v1").hexdigest()
PERSISTENCE_BINDING_SHA = (
    "7dcdca13d6d658dc9963d5cc5f4dea47575d42305831dfbe301a4db6ee90e522"
)
CONFIGURATION = {
    "mode": "supplied-receipts-only",
    "provider_id": "synthetic-persistence-provider-v1",
}


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _registration(items: list[dict[str, object]]) -> dict[str, object]:
    anchor_gate = items[0]["gate_document"]
    anchor_source = anchor_gate["source"]
    return {
        "schema_version": subject.REGISTRATION_SCHEMA_VERSION,
        "history_id": "synthetic-history-window-v1",
        "source_gate_schema_version": subject.source_contract.SCHEMA_VERSION,
        "source_gate_static_fingerprint": subject.source_contract.STATIC_FINGERPRINT,
        "source_gate_implementation_sha256": subject.SOURCE_IMPLEMENTATION_SHA256,
        "anchor_gate_hash": anchor_gate["gate_hash"],
        "anchor_asset_hash": anchor_source["current_asset_hash"],
        "expected_study_identity_hash": STUDY_HASH,
        "expected_window_order_hash": WINDOW_HASH,
        "expected_replay_registry_id": "MULTI-WINDOW-LIFECYCLE-REPLAY-REGISTRY-01",
        "expected_replay_registry_namespace": "STRATEGY-CORRELATION.MULTI-WINDOW-LIFECYCLE.V1",
        "expected_persistence_configuration_hash": subject.canonical_value_sha256_v1(
            CONFIGURATION
        ),
        "anchor_checkpoint_tree_size": 3,
        "final_checkpoint_tree_size": 5,
        "expected_segment_count": 3,
        "checkpoint_tree_step": 1,
        "registered_at_utc": "2026-08-24T02:50:00Z",
        "future_coverage_not_before_utc": "2026-08-24T02:55:00Z",
        "future_coverage_not_after_utc": "2026-08-24T04:00:00Z",
        "max_future_asset_time_gap_seconds": 1200,
        "checkpoint_sequence_policy": subject.CHECKPOINT_SEQUENCE_POLICY,
        "segment_sequence_policy": subject.SEGMENT_SEQUENCE_POLICY,
        "asset_handoff_policy": subject.ASSET_HANDOFF_POLICY,
        "identity_stability_policy": subject.IDENTITY_STABILITY_POLICY,
        "time_policy": subject.TIME_POLICY,
    }


def _items() -> list[dict[str, object]]:
    values: list[dict[str, object]] = []
    previous_segment: dict[str, object] | None = None
    previous_asset_hash: str | None = None
    times = (
        "2026-08-24T02:45:00Z",
        "2026-08-24T03:00:00Z",
        "2026-08-24T03:10:00Z",
    )
    for offset, asset_time in enumerate(times):
        tree_size = 3 + offset
        asset_hash = _hash(f"asset-{tree_size}")
        gate_hash = _hash(f"gate-{tree_size}")
        checkpoint_asset = {
            "asset_hash": asset_hash,
            "asset_created_at_utc": asset_time,
            "previous_persisted_asset_hash": previous_asset_hash,
            "source_checkpoint_root_hash": _hash(f"root-{tree_size}"),
            "source_replay_registry_id": "MULTI-WINDOW-LIFECYCLE-REPLAY-REGISTRY-01",
            "source_replay_registry_namespace": "STRATEGY-CORRELATION.MULTI-WINDOW-LIFECYCLE.V1",
        }
        current_segment = {
            "persistence_inputs": {
                "checkpoint_asset": checkpoint_asset,
                "expected_asset_hash": asset_hash,
                "persistence_configuration": deepcopy(CONFIGURATION),
            }
        }
        gate_document = {
            "schema_version": subject.source_contract.SCHEMA_VERSION,
            "static_fingerprint": subject.source_contract.STATIC_FINGERPRINT,
            "status": "PASS",
            "reason_code": subject.SOURCE_PASS_REASON,
            "lineage_mode": (
                "REGISTERED_SOURCE_PIN"
                if offset == 0
                else "PREVIOUS_PERSISTED_ASSET"
            ),
            "gate_hash": gate_hash,
            "facts": {
                "complete_persisted_checkpoint_history_verified": False,
                "runtime_mutations_performed": False,
                "synthetic_only": True,
            },
            "source": {
                "current_asset_hash": asset_hash,
                "previous_asset_hash": previous_asset_hash,
                "study_identity_hash": STUDY_HASH,
                "window_order_hash": WINDOW_HASH,
                "persistence_binding_v1_implementation_sha256": PERSISTENCE_BINDING_SHA,
            },
            "summary": {
                "current_checkpoint_tree_size": tree_size,
                "previous_checkpoint_tree_size": 1 if offset == 0 else tree_size - 1,
            },
            "authority": {
                "candidate_activation_allowed": False,
                "paper_authorized": False,
                "live_order_allowed": False,
            },
        }
        values.append(
            {
                "gate_document": gate_document,
                "current_segment": current_segment,
                "previous_segment": deepcopy(previous_segment),
                "expected_gate_hash": gate_hash,
            }
        )
        previous_segment = deepcopy(current_segment)
        previous_asset_hash = asset_hash
    return values


def _fixture() -> dict[str, object]:
    items = _items()
    registration = _registration(items)
    receipt = subject.build_strategy_correlation_persisted_checkpoint_history_coverage_registration_v1(
        registration
    )
    return {
        "registration": registration,
        "registration_receipt": receipt,
        "lineage_items": items,
    }


def _evaluate(fixture: dict[str, object], *, source_verified: bool = True):
    with patch.object(
        subject.source_contract,
        SOURCE_VERIFIER,
        return_value=source_verified,
    ) as verifier:
        result = subject.evaluate_strategy_correlation_persisted_checkpoint_history_coverage_gate_v1(
            registration=fixture["registration"],
            registration_receipt=fixture["registration_receipt"],
            lineage_items=fixture["lineage_items"],
        )
    return result, verifier


class StrategyCorrelationPersistedCheckpointHistoryCoverageGateV1Tests(
    unittest.TestCase
):
    def test_registration_accepts_exact_future_window(self) -> None:
        fixture = _fixture()
        self.assertEqual(
            fixture["registration_receipt"]["status"], subject.REGISTERED_STATUS
        )
        self.assertTrue(
            subject.verify_strategy_correlation_persisted_checkpoint_history_coverage_registration_v1(
                fixture["registration_receipt"],
                registration=fixture["registration"],
            )
        )

    def test_registration_rejects_extra_field(self) -> None:
        fixture = _fixture()
        fixture["registration"]["extra"] = True
        receipt = subject.build_strategy_correlation_persisted_checkpoint_history_coverage_registration_v1(
            fixture["registration"]
        )
        self.assertEqual(receipt["reason_code"], "registration_fields_invalid")

    def test_registration_requires_at_least_three_segments(self) -> None:
        fixture = _fixture()
        fixture["registration"]["expected_segment_count"] = 2
        fixture["registration"]["final_checkpoint_tree_size"] = 4
        receipt = subject.build_strategy_correlation_persisted_checkpoint_history_coverage_registration_v1(
            fixture["registration"]
        )
        self.assertEqual(
            receipt["reason_code"], "registration_expected_segment_count_invalid"
        )

    def test_registration_rejects_bool_int_alias(self) -> None:
        fixture = _fixture()
        fixture["registration"]["anchor_checkpoint_tree_size"] = True
        receipt = subject.build_strategy_correlation_persisted_checkpoint_history_coverage_registration_v1(
            fixture["registration"]
        )
        self.assertEqual(
            receipt["reason_code"],
            "registration_anchor_checkpoint_tree_size_invalid",
        )

    def test_registration_count_must_match_tree_range(self) -> None:
        fixture = _fixture()
        fixture["registration"]["final_checkpoint_tree_size"] = 6
        receipt = subject.build_strategy_correlation_persisted_checkpoint_history_coverage_registration_v1(
            fixture["registration"]
        )
        self.assertEqual(
            receipt["reason_code"], "registration_segment_count_range_mismatch"
        )

    def test_registration_must_precede_future_window(self) -> None:
        fixture = _fixture()
        fixture["registration"]["registered_at_utc"] = "2026-08-24T03:00:00Z"
        fixture["registration"]["future_coverage_not_before_utc"] = (
            "2026-08-24T03:00:00Z"
        )
        receipt = subject.build_strategy_correlation_persisted_checkpoint_history_coverage_registration_v1(
            fixture["registration"]
        )
        self.assertEqual(
            receipt["reason_code"], "registration_future_coverage_time_order_invalid"
        )

    def test_three_segment_registered_prefix_passes_without_authority(self) -> None:
        result, verifier = _evaluate(_fixture())
        self.assertEqual(result["status"], subject.PASS_STATUS)
        self.assertEqual(result["reason_code"], subject.PASS_REASON)
        self.assertEqual(result["summary"]["verified_segment_count"], 3)
        self.assertTrue(result["facts"]["preregistered_history_window_complete"])
        self.assertTrue(result["facts"]["asset_hash_chain_exact"])
        self.assertTrue(result["facts"]["bounded_history_prefix_only"])
        self.assertFalse(
            result["facts"]["complete_persisted_checkpoint_history_verified"]
        )
        self.assertTrue(all(value is False for value in result["authority"].values()))
        self.assertEqual(verifier.call_count, 3)

    def test_source_lineage_gates_are_reverified(self) -> None:
        result, verifier = _evaluate(_fixture(), source_verified=False)
        self.assertEqual(
            result["reason_code"], "UNKNOWN_ITEM_0_SOURCE_LINEAGE_GATE_UNVERIFIED"
        )
        self.assertEqual(verifier.call_count, 1)

    def test_batch_count_must_match_registration(self) -> None:
        fixture = _fixture()
        fixture["lineage_items"].pop()
        result, _ = _evaluate(fixture)
        self.assertEqual(result["reason_code"], "UNKNOWN_LINEAGE_ITEM_COUNT_MISMATCH")

    def test_registered_anchor_is_exact(self) -> None:
        fixture = _fixture()
        fixture["registration"]["anchor_asset_hash"] = _hash("other-anchor")
        fixture["registration_receipt"] = subject.build_strategy_correlation_persisted_checkpoint_history_coverage_registration_v1(
            fixture["registration"]
        )
        result, _ = _evaluate(fixture)
        self.assertEqual(
            result["reason_code"], "UNKNOWN_REGISTERED_ANCHOR_ASSET_HASH_MISMATCH"
        )

    def test_anchor_must_predate_registration(self) -> None:
        fixture = _fixture()
        fixture["lineage_items"][0]["current_segment"]["persistence_inputs"][
            "checkpoint_asset"
        ]["asset_created_at_utc"] = "2026-08-24T02:51:00Z"
        result, _ = _evaluate(fixture)
        self.assertEqual(
            result["reason_code"], "UNKNOWN_REGISTERED_ANCHOR_CREATED_AFTER_REGISTRATION"
        )

    def test_segment_handoff_must_be_exact(self) -> None:
        fixture = _fixture()
        fixture["lineage_items"][1]["previous_segment"]["drift"] = True
        result, _ = _evaluate(fixture)
        self.assertEqual(result["reason_code"], "UNKNOWN_SEGMENT_HANDOFF_MISMATCH")

    def test_previous_asset_hash_handoff_must_be_exact(self) -> None:
        fixture = _fixture()
        fixture["lineage_items"][2]["gate_document"]["source"][
            "previous_asset_hash"
        ] = _hash("wrong-previous")
        result, _ = _evaluate(fixture)
        self.assertEqual(result["reason_code"], "UNKNOWN_ASSET_HASH_HANDOFF_MISMATCH")

    def test_checkpoint_tree_sequence_cannot_skip(self) -> None:
        fixture = _fixture()
        fixture["lineage_items"][1]["gate_document"]["summary"][
            "current_checkpoint_tree_size"
        ] = 5
        result, _ = _evaluate(fixture)
        self.assertEqual(
            result["reason_code"],
            "UNKNOWN_ITEM_1_CHECKPOINT_TREE_SEQUENCE_MISMATCH",
        )

    def test_future_asset_must_stay_in_registered_window(self) -> None:
        fixture = _fixture()
        fixture["lineage_items"][2]["current_segment"]["persistence_inputs"][
            "checkpoint_asset"
        ]["asset_created_at_utc"] = "2026-08-24T04:01:00Z"
        result, _ = _evaluate(fixture)
        self.assertEqual(
            result["reason_code"],
            "UNKNOWN_ITEM_2_OUTSIDE_PREREGISTERED_FUTURE_WINDOW",
        )

    def test_future_asset_gap_is_preregistered(self) -> None:
        fixture = _fixture()
        fixture["registration"]["max_future_asset_time_gap_seconds"] = 300
        fixture["registration_receipt"] = subject.build_strategy_correlation_persisted_checkpoint_history_coverage_registration_v1(
            fixture["registration"]
        )
        result, _ = _evaluate(fixture)
        self.assertEqual(
            result["reason_code"], "UNKNOWN_ASSET_TIME_GAP_EXCEEDS_REGISTRATION"
        )

    def test_registered_identity_drift_is_unknown(self) -> None:
        fixture = _fixture()
        fixture["lineage_items"][1]["gate_document"]["source"][
            "study_identity_hash"
        ] = _hash("other-study")
        result, _ = _evaluate(fixture)
        self.assertEqual(result["reason_code"], "UNKNOWN_ITEM_1_STUDY_IDENTITY_DRIFT")

    def test_persistence_configuration_drift_is_unknown(self) -> None:
        fixture = _fixture()
        fixture["lineage_items"][1]["current_segment"]["persistence_inputs"][
            "persistence_configuration"
        ]["provider_id"] = "other-provider-v1"
        result, _ = _evaluate(fixture)
        self.assertEqual(
            result["reason_code"],
            "UNKNOWN_ITEM_1_PERSISTENCE_CONFIGURATION_DRIFT",
        )

    def test_gate_and_asset_hashes_cannot_be_reused(self) -> None:
        fixture = _fixture()
        fixture["lineage_items"][2]["expected_gate_hash"] = fixture[
            "lineage_items"
        ][1]["expected_gate_hash"]
        fixture["lineage_items"][2]["gate_document"]["gate_hash"] = fixture[
            "lineage_items"
        ][1]["gate_document"]["gate_hash"]
        result, _ = _evaluate(fixture)
        self.assertEqual(result["reason_code"], "UNKNOWN_SOURCE_GATE_HASH_REUSED")

    def test_source_truth_and_authority_cannot_be_promoted(self) -> None:
        fixture = _fixture()
        fixture["lineage_items"][1]["gate_document"]["facts"][
            "complete_persisted_checkpoint_history_verified"
        ] = True
        result, _ = _evaluate(fixture)
        self.assertEqual(
            result["reason_code"],
            "UNKNOWN_ITEM_1_SOURCE_COMPLETE_HISTORY_MUST_REMAIN_FALSE",
        )
        fixture = _fixture()
        fixture["lineage_items"][1]["gate_document"]["authority"][
            "paper_authorized"
        ] = True
        result, _ = _evaluate(fixture)
        self.assertEqual(
            result["reason_code"], "UNKNOWN_ITEM_1_SOURCE_AUTHORITY_NOT_NEGATIVE"
        )

    def test_gate_verifier_rejects_resealed_authority_promotion(self) -> None:
        fixture = _fixture()
        result, _ = _evaluate(fixture)
        tampered = deepcopy(result)
        tampered["authority"]["candidate_activation_allowed"] = True
        tampered.pop("gate_hash")
        tampered = seal_strict_canonical_document(tampered, "gate_hash")
        with patch.object(subject.source_contract, SOURCE_VERIFIER, return_value=True):
            self.assertTrue(
                subject.verify_strategy_correlation_persisted_checkpoint_history_coverage_gate_v1(
                    result,
                    registration=fixture["registration"],
                    registration_receipt=fixture["registration_receipt"],
                    lineage_items=fixture["lineage_items"],
                    expected_gate_hash=result["gate_hash"],
                )
            )
            self.assertFalse(
                subject.verify_strategy_correlation_persisted_checkpoint_history_coverage_gate_v1(
                    tampered,
                    registration=fixture["registration"],
                    registration_receipt=fixture["registration_receipt"],
                    lineage_items=fixture["lineage_items"],
                    expected_gate_hash=tampered["gate_hash"],
                )
            )

    def test_unknown_is_redacted_and_fail_closed(self) -> None:
        result = subject.evaluate_strategy_correlation_persisted_checkpoint_history_coverage_gate_v1(
            registration=None,
            registration_receipt=None,
            lineage_items=None,
        )
        self.assertEqual(result["status"], subject.UNKNOWN_STATUS)
        self.assertTrue(all(value is False for value in result["authority"].values()))
        serialized = json.dumps(result, sort_keys=True)
        self.assertNotIn('"lineage_items":', serialized)
        self.assertNotIn('"current_segment":', serialized)
        self.assertNotIn('"checkpoint_asset":', serialized)


if __name__ == "__main__":
    unittest.main()
