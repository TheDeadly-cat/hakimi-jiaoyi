from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import unittest

from exchange_terminal.application import (
    witness_ownership_key_revocation_snapshot_isolated_storage_harness_v1 as harness,
)
from exchange_terminal.application import (
    witness_ownership_key_revocation_snapshot_storage_adapter_preregistration_v1 as storage_preregistration,
)


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


class _SyntheticDriver:
    def __init__(
        self,
        *,
        block_at: int | None = None,
        exception_at: int | None = None,
        malformed_at: int | None = None,
        duplicate_transcript_at: int | None = None,
        duplicate_artifact_at: int | None = None,
    ) -> None:
        self.block_at = block_at
        self.exception_at = exception_at
        self.malformed_at = malformed_at
        self.duplicate_transcript_at = duplicate_transcript_at
        self.duplicate_artifact_at = duplicate_artifact_at
        self.calls = []

    def execute_scenario(self, command):
        self.calls.append(command)
        call_number = len(self.calls)
        if self.exception_at == call_number:
            raise RuntimeError("synthetic driver exception")
        if self.malformed_at == call_number:
            return {"outcome": "PASS"}
        transcript_label = (
            "transcript-1"
            if self.duplicate_transcript_at == call_number
            else f"transcript-{call_number}"
        )
        artifact_label = (
            "artifact-1"
            if self.duplicate_artifact_at == call_number
            else f"artifact-{call_number}"
        )
        return harness.build_witness_ownership_snapshot_storage_harness_scenario_result_v1(
            command,
            outcome=(
                harness.OUTCOME_BLOCK
                if self.block_at == call_number
                else harness.OUTCOME_PASS
            ),
            transcript_hash=_hash(transcript_label),
            observed_artifact_hash=_hash(artifact_label),
            runtime_mutations_outside_isolated_domain_claimed=False,
            paper_or_live_operation_claimed=False,
            automatic_retry_or_reissue_claimed=False,
        )


class WitnessOwnershipIsolatedStorageHarnessV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.storage_kwargs = {
            "identity_source_adapter_preregistration_hash": _hash(
                "identity-source-preregistration"
            ),
            "target_stream_id": "witness-provider-key-revocations",
            "storage_adapter_id": "snapshot-storage-adapter-01",
            "storage_adapter_static_fingerprint": (
                "synthetic-snapshot-storage-adapter-v1"
            ),
            "storage_adapter_implementation_sha256": _hash(
                "storage-adapter-implementation"
            ),
            "storage_backend_kind": storage_preregistration.STORAGE_BACKEND_LOCAL_FILESYSTEM,
            "storage_domain_id_hash": _hash("storage-domain-id"),
            "content_namespace_id_hash": _hash("content-namespace-id"),
            "head_namespace_id_hash": _hash("head-namespace-id"),
            "durability_protocol_version": "synthetic-durability-protocol-v1",
            "crash_recovery_protocol_version": (
                "synthetic-crash-recovery-protocol-v1"
            ),
            "concurrency_control_protocol_version": (
                "synthetic-concurrency-control-protocol-v1"
            ),
        }
        self.storage_document = storage_preregistration.build_witness_ownership_key_revocation_snapshot_storage_adapter_preregistration_v1(
            **self.storage_kwargs
        )
        self.plan_kwargs = {
            "driver_id": "synthetic-isolated-driver-01",
            "driver_implementation_sha256": _hash("driver-implementation"),
            "isolated_domain_id_hash": _hash("isolated-domain"),
            "plan_nonce_hash": _hash("plan-nonce"),
            "storage_preregistration_kwargs": self.storage_kwargs,
        }
        self.plan = harness.build_witness_ownership_snapshot_isolated_storage_harness_plan_v1(
            self.storage_document,
            **self.plan_kwargs,
        )
        self.run_nonce_hash = _hash("harness-run-nonce")

    def _run(self, driver):
        return harness.run_witness_ownership_snapshot_isolated_storage_harness_v1(
            driver,
            self.plan,
            self.storage_document,
            harness_run_nonce_hash=self.run_nonce_hash,
            expected_harness_plan_hash=self.plan["harness_plan_hash"],
            plan_build_kwargs=self.plan_kwargs,
            storage_preregistration_kwargs=self.storage_kwargs,
        )

    def test_plan_is_deterministic_and_content_addressed(self) -> None:
        rebuilt = harness.build_witness_ownership_snapshot_isolated_storage_harness_plan_v1(
            self.storage_document,
            **self.plan_kwargs,
        )
        self.assertEqual(self.plan, rebuilt)
        self.assertRegex(self.plan["harness_plan_hash"], r"^[0-9a-f]{64}$")

    def test_plan_maps_fourteen_requirements_to_thirteen_driver_calls(self) -> None:
        self.assertEqual(self.plan["expected_scenario_count"], 14)
        self.assertEqual(self.plan["expected_driver_scenario_count"], 13)
        self.assertEqual(self.plan["expected_observer_handoff_count"], 1)

    def test_independent_observer_requirement_is_never_driver_executable(self) -> None:
        rows = [
            row
            for row in self.plan["scenarios"]
            if row["requirement_id"] == harness.OBSERVER_ONLY_REQUIREMENT_ID
        ]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["execution_mode"], harness.EXECUTION_MODE_OBSERVER_ONLY)

    def test_plan_verifier_accepts_exact_rebuild(self) -> None:
        self.assertTrue(
            harness.verify_witness_ownership_snapshot_isolated_storage_harness_plan_v1(
                self.plan,
                self.storage_document,
                **self.plan_kwargs,
            )
        )

    def test_success_calls_each_driver_scenario_once(self) -> None:
        driver = _SyntheticDriver()
        bundle = self._run(driver)
        self.assertEqual(len(driver.calls), 13)
        self.assertEqual(len({command.scenario_id for command in driver.calls}), 13)
        self.assertEqual(
            bundle["evaluation"]["status"],
            harness.STATUS_DRIVER_SCENARIOS_COMPLETE,
        )
        self.assertEqual(bundle["evaluation"]["driver_calls_per_scenario_maximum"], 1)

    def test_success_builds_observer_handoff_without_observer_claim(self) -> None:
        bundle = self._run(_SyntheticDriver())
        evaluation = bundle["evaluation"]
        self.assertTrue(evaluation["observer_handoff_descriptor_built"])
        self.assertRegex(evaluation["observer_handoff_hash"], r"^[0-9a-f]{64}$")
        self.assertFalse(evaluation["external_observer_identity_verified"])

    def test_success_keeps_runtime_persistence_and_authority_unverified(self) -> None:
        evaluation = self._run(_SyntheticDriver())["evaluation"]
        self.assertFalse(evaluation["driver_runtime_execution_verified"])
        self.assertFalse(
            evaluation["isolated_domain_confinement_independently_verified"]
        )
        self.assertFalse(evaluation["external_persistence_independently_verified"])
        self.assertFalse(evaluation["permission"])
        self.assertFalse(evaluation["paper_authorized"])
        self.assertFalse(evaluation["live_authorized"])
        self.assertFalse(evaluation["current_chain_activated"])

    def test_driver_block_stops_without_retry(self) -> None:
        driver = _SyntheticDriver(block_at=4)
        bundle = self._run(driver)
        self.assertEqual(len(driver.calls), 4)
        self.assertEqual(
            bundle["evaluation"]["blocker_codes"],
            ["harness_scenario_outcome_not_pass"],
        )

    def test_driver_exception_stops_without_retry(self) -> None:
        driver = _SyntheticDriver(exception_at=3)
        bundle = self._run(driver)
        self.assertEqual(len(driver.calls), 3)
        self.assertEqual(bundle["runner_failure_code"], "DRIVER_EXCEPTION")
        self.assertEqual(
            bundle["evaluation"]["blocker_codes"],
            ["harness_driver_exception"],
        )

    def test_malformed_driver_result_stops_without_retry(self) -> None:
        driver = _SyntheticDriver(malformed_at=5)
        bundle = self._run(driver)
        self.assertEqual(len(driver.calls), 5)
        self.assertEqual(bundle["runner_failure_code"], "DRIVER_RESULT_INVALID")
        self.assertEqual(
            bundle["evaluation"]["blocker_codes"],
            ["harness_driver_result_invalid"],
        )

    def test_duplicate_transcript_is_rejected(self) -> None:
        bundle = self._run(_SyntheticDriver(duplicate_transcript_at=2))
        self.assertEqual(
            bundle["evaluation"]["blocker_codes"],
            ["harness_transcript_replay_detected"],
        )

    def test_duplicate_observed_artifact_is_rejected(self) -> None:
        bundle = self._run(_SyntheticDriver(duplicate_artifact_at=2))
        self.assertEqual(
            bundle["evaluation"]["blocker_codes"],
            ["harness_observed_artifact_replay_detected"],
        )

    def test_observer_only_scenario_cannot_build_driver_command(self) -> None:
        observer_row = next(
            row
            for row in self.plan["scenarios"]
            if row["execution_mode"] == harness.EXECUTION_MODE_OBSERVER_ONLY
        )
        command = harness.build_witness_ownership_snapshot_storage_harness_scenario_command_v1(
            self.plan,
            self.storage_document,
            scenario_id=observer_row["scenario_id"],
            harness_run_nonce_hash=self.run_nonce_hash,
            plan_build_kwargs=self.plan_kwargs,
            storage_preregistration_kwargs=self.storage_kwargs,
        )
        self.assertIsNone(command)

    def test_result_builder_rejects_unsafe_mutation_claim(self) -> None:
        row = next(
            row
            for row in self.plan["scenarios"]
            if row["execution_mode"] == harness.EXECUTION_MODE_DRIVER
        )
        command = harness.build_witness_ownership_snapshot_storage_harness_scenario_command_v1(
            self.plan,
            self.storage_document,
            scenario_id=row["scenario_id"],
            harness_run_nonce_hash=self.run_nonce_hash,
            plan_build_kwargs=self.plan_kwargs,
            storage_preregistration_kwargs=self.storage_kwargs,
        )
        result = harness.build_witness_ownership_snapshot_storage_harness_scenario_result_v1(
            command,
            outcome=harness.OUTCOME_PASS,
            transcript_hash=_hash("transcript"),
            observed_artifact_hash=_hash("artifact"),
            runtime_mutations_outside_isolated_domain_claimed=True,
            paper_or_live_operation_claimed=False,
            automatic_retry_or_reissue_claimed=False,
        )
        self.assertIsNone(result)

    def test_wrong_expected_plan_hash_prevents_driver_calls(self) -> None:
        driver = _SyntheticDriver()
        result = harness.run_witness_ownership_snapshot_isolated_storage_harness_v1(
            driver,
            self.plan,
            self.storage_document,
            harness_run_nonce_hash=self.run_nonce_hash,
            expected_harness_plan_hash=_hash("wrong-plan"),
            plan_build_kwargs=self.plan_kwargs,
            storage_preregistration_kwargs=self.storage_kwargs,
        )
        self.assertEqual(result, {})
        self.assertEqual(driver.calls, [])

    def test_execution_bundle_verifier_accepts_exact_bundle(self) -> None:
        bundle = self._run(_SyntheticDriver())
        self.assertTrue(
            harness.verify_witness_ownership_snapshot_storage_harness_execution_bundle_v1(
                bundle,
                self.plan,
                self.storage_document,
                expected_harness_execution_bundle_hash=bundle[
                    "harness_execution_bundle_hash"
                ],
                plan_build_kwargs=self.plan_kwargs,
                storage_preregistration_kwargs=self.storage_kwargs,
            )
        )

    def test_execution_bundle_verifier_rejects_authority_escalation(self) -> None:
        bundle = self._run(_SyntheticDriver())
        tampered = deepcopy(bundle)
        tampered["evaluation"]["permission"] = True
        self.assertFalse(
            harness.verify_witness_ownership_snapshot_storage_harness_execution_bundle_v1(
                tampered,
                self.plan,
                self.storage_document,
                expected_harness_execution_bundle_hash=bundle[
                    "harness_execution_bundle_hash"
                ],
                plan_build_kwargs=self.plan_kwargs,
                storage_preregistration_kwargs=self.storage_kwargs,
            )
        )

    def test_run_nonce_changes_commands_and_bundle(self) -> None:
        first = self._run(_SyntheticDriver())
        second = harness.run_witness_ownership_snapshot_isolated_storage_harness_v1(
            _SyntheticDriver(),
            self.plan,
            self.storage_document,
            harness_run_nonce_hash=_hash("harness-run-nonce-2"),
            expected_harness_plan_hash=self.plan["harness_plan_hash"],
            plan_build_kwargs=self.plan_kwargs,
            storage_preregistration_kwargs=self.storage_kwargs,
        )
        self.assertNotEqual(
            first["harness_execution_bundle_hash"],
            second["harness_execution_bundle_hash"],
        )

    def test_plan_rejects_duplicate_semantic_hashes(self) -> None:
        kwargs = dict(self.plan_kwargs)
        kwargs["plan_nonce_hash"] = kwargs["isolated_domain_id_hash"]
        plan = harness.build_witness_ownership_snapshot_isolated_storage_harness_plan_v1(
            self.storage_document,
            **kwargs,
        )
        self.assertEqual(plan, {})

    def test_serialized_plan_and_bundle_exclude_runtime_locator_material(self) -> None:
        serialized = json.dumps(
            {"plan": self.plan, "bundle": self._run(_SyntheticDriver())},
            sort_keys=True,
        )
        self.assertNotIn("storage_path", serialized)
        self.assertNotIn("connection_string", serialized)
        self.assertNotIn("credential", serialized)
        self.assertNotIn("secret", serialized)
        self.assertNotIn("paper_authorized\": true", serialized)
        self.assertNotIn("live_authorized\": true", serialized)


if __name__ == "__main__":
    unittest.main()
