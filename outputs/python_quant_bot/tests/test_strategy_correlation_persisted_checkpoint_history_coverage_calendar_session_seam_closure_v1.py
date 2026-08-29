from __future__ import annotations

import base64
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import Mock, patch

from exchange_terminal.services import (
    strategy_correlation_common_support_calendar_provider_composition_v1 as composition_contract,
)
from exchange_terminal.services import (
    strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1
    as calendar_contract,
)
from exchange_terminal.services import (
    strategy_correlation_provider_dataset_content_attestation_v1 as attestation_contract,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import (
    test_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1
    as calendar_fixture_module,
)
from tests import (
    test_strategy_correlation_persisted_checkpoint_history_coverage_correlation_replay_seam_closure_v1
    as adr0359_fixture,
)
from tests import (
    test_strategy_correlation_persisted_checkpoint_history_coverage_real_source_integration_v1
    as adr0358_fixture,
)
from tests import (
    test_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_binding_gate_v1
    as provider_binding_fixture_module,
)
from tests import (
    test_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_lineage_gate_v1
    as lineage_fixture_module,
)


FIXTURE_FINGERPRINT = (
    "20260824-strategy-correlation-persisted-checkpoint-history-coverage-"
    "calendar-session-seam-closure-v1"
)
CALENDAR_VERIFY_ATTRIBUTE = (
    "verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_"
    "calendar_session_verifier_v1"
)
CALENDAR_PATCH_TARGET = next(
    target
    for target in adr0359_fixture.REMAINING_PATCH_TARGETS
    if "calendar_session_verifier" in target
)
PROVIDER_PATCH_TARGET = next(
    target
    for target in adr0359_fixture.REMAINING_PATCH_TARGETS
    if "provider_identity_assertion_verifier" in target
)
SECOND_WINDOW_DAY_OFFSET = 80


def _calendar_verification_args(
    bundle: dict[str, object],
) -> tuple[object, object, object, object, object]:
    return (
        bundle["calendar_registration_v1"],
        bundle["calendar_registration_verification_context"],
        bundle["batch_verification_v1"],
        bundle["batch_verification_context"],
        bundle["observation_batch"],
    )


def _calendar_verifies(
    verifier: object,
    document: dict[str, object],
    bundle: dict[str, object],
) -> bool:
    return bool(
        verifier(
            document,
            *_calendar_verification_args(bundle),
            expected_calendar_registration_hash=bundle[
                "expected_calendar_registration_hash"
            ],
            expected_batch_verification_hash=bundle[
                "expected_batch_verification_hash"
            ],
        )
    )


def _remove_calendar_patch(fixture: unittest.TestCase) -> dict[str, object]:
    provider_fixture = fixture.binding.persistence.source.source.source.source
    matches: list[tuple[object, object]] = []
    for entry in list(provider_fixture._cleanups):
        callback = entry[0]
        patcher = getattr(callback, "__self__", None)
        if getattr(patcher, "attribute", None) == CALENDAR_VERIFY_ATTRIBUTE:
            matches.append((entry, patcher))
    if len(matches) != 1:
        raise AssertionError("expected exactly one calendar-session verifier patch")

    entry, patcher = matches[0]
    original = patcher.temp_original
    patcher.stop()
    provider_fixture._cleanups.remove(entry)
    active = getattr(calendar_contract, CALENDAR_VERIFY_ATTRIBUTE)
    if active is not original or isinstance(active, Mock):
        raise AssertionError("calendar-session verifier remained mocked")

    remaining = tuple(
        sorted(
            adr0359_fixture._patch_target_name(
                getattr(cleanup[0], "__self__", None)
            )
            for cleanup in provider_fixture._cleanups
            if getattr(
                getattr(cleanup[0], "__self__", None), "attribute", None
            )
        )
    )
    if remaining != (PROVIDER_PATCH_TARGET,):
        raise AssertionError("remaining upstream fixture seam drifted")
    return {
        "removed_patch_target": CALENDAR_PATCH_TARGET,
        "remaining_patch_targets": remaining,
        "calendar_verifier_is_original": True,
    }


@contextmanager
def one_seam_three_segment_fixture_v1():
    calendar_case = (
        calendar_fixture_module.StrategyCorrelationCrossLagFactorCalibrationLongHorizonCalendarSessionVerifierV1Tests()
    )
    calendar_case.setUp()
    lineage_case: unittest.TestCase | None = None
    calendar_records: list[dict[str, object]] = []
    scaffold_call_count = 0

    provider_fixture_class = (
        provider_binding_fixture_module.StrategyCorrelationUncertaintyMultiWindowObservationMembershipProviderAttestationBindingGateV1Tests
    )
    original_provider_window = provider_fixture_class._provider_window
    original_provider_context = provider_fixture_class._context
    original_calendar_verifier = getattr(
        calendar_contract, CALENDAR_VERIFY_ATTRIBUTE
    )

    def build_calendar_material(
        day_offset: int,
    ) -> tuple[dict[str, object], dict[str, object]]:
        rows = deepcopy(calendar_case.batch["rows"])
        for row in rows:
            row["observation_date"] = (
                datetime.fromisoformat(row["observation_date"]).date()
                + timedelta(days=day_offset)
            ).isoformat()
        batch = calendar_case.case._batch(rows=rows)
        last_observation = datetime.fromisoformat(
            batch["last_observation_date"]
        ).replace(tzinfo=timezone.utc)
        provider_timestamp = (
            last_observation + timedelta(days=1, seconds=1)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        receipt = calendar_case.case.case._receipt(
            provider_timestamp_utc=provider_timestamp,
            observation_batch_hash=batch["observation_batch_hash"],
            batch_first_observation_date=batch["first_observation_date"],
            batch_last_observation_date=batch["last_observation_date"],
        )
        signature_verification = calendar_case.case.case._build(
            receipt=receipt,
            expected_attestation_hash=receipt["attestation_hash"],
        )
        signature_context = deepcopy(calendar_case.case.signature_context)
        signature_context["attestation_receipt"] = receipt
        signature_context["expected_attestation_hash"] = receipt[
            "attestation_hash"
        ]
        batch_verification = calendar_case.case._build(
            batch=batch,
            signature_verification=signature_verification,
            signature_context=signature_context,
            expected_signature_hash=signature_verification["verification_hash"],
            expected_batch_hash=batch["observation_batch_hash"],
        )
        calendar_registration = calendar_case._calendar_registration(
            identity_calendar_ids=["24/7", "24/7"],
            factor_calendar_id="24/7",
        )
        calendar_context = calendar_case._calendar_context(
            identity_calendar_ids=["24/7", "24/7"],
            factor_calendar_id="24/7",
        )
        batch_context = calendar_case._batch_context(
            batch=batch,
            signature_verification=signature_verification,
            signature_context=signature_context,
        )
        document = calendar_case._build(
            calendar_registration=calendar_registration,
            calendar_context=calendar_context,
            batch_verification=batch_verification,
            batch_context=batch_context,
            batch=batch,
        )
        bundle = {
            "calendar_registration_v1": calendar_registration,
            "calendar_registration_verification_context": calendar_context,
            "batch_verification_v1": batch_verification,
            "batch_verification_context": batch_context,
            "observation_batch": batch,
            "expected_calendar_registration_hash": calendar_registration[
                "calendar_registration_hash"
            ],
            "expected_batch_verification_hash": batch_verification[
                "verification_hash"
            ],
        }
        return document, bundle

    def provider_window_with_calendar_evidence(
        self: unittest.TestCase,
        *,
        day_offset: int,
        data_hash_suffix: str,
        dataset_private_key: object,
    ) -> dict[str, object]:
        nonlocal scaffold_call_count
        with patch.object(
            calendar_contract,
            CALENDAR_VERIFY_ATTRIBUTE,
            return_value=True,
        ) as scaffold_verifier:
            provider_window = original_provider_window(
                self,
                day_offset=day_offset,
                data_hash_suffix=data_hash_suffix,
                dataset_private_key=dataset_private_key,
            )
        scaffold_call_count += scaffold_verifier.call_count

        calendar_document, calendar_bundle = build_calendar_material(day_offset)
        if not _calendar_verifies(
            original_calendar_verifier,
            calendar_document,
            calendar_bundle,
        ):
            raise AssertionError("original calendar verifier rejected rebuilt evidence")

        provider_document = deepcopy(
            provider_window["composition_context"][
                "provider_identity_verification"
            ]
        )
        provider_document["future_evaluation_id"] = calendar_document[
            "future_evaluation_id"
        ]
        provider_document = seal_strict_canonical_document(
            provider_document,
            "verification_hash",
        )
        composition_context = {
            "derivation_receipt": provider_window["composition_context"][
                "derivation_receipt"
            ],
            "matrix_replay": provider_window["composition_context"][
                "matrix_replay"
            ],
            "calendar_session_verification": calendar_document,
            "calendar_verification_bundle": calendar_bundle,
            "provider_identity_verification": provider_document,
            "provider_verification_bundle": provider_window[
                "composition_context"
            ]["provider_verification_bundle"],
        }
        old_registration = provider_window["registration"]
        with patch.object(
            calendar_contract,
            CALENDAR_VERIFY_ATTRIBUTE,
            original_calendar_verifier,
        ):
            composition_document = composition_contract.build_correlation_common_support_calendar_provider_composition_v1(
                composition_context["derivation_receipt"],
                composition_context["matrix_replay"],
                calendar_document,
                calendar_bundle,
                provider_document,
                composition_context["provider_verification_bundle"],
            )
            registration = attestation_contract.build_provider_dataset_content_attestation_registration_v1(
                composition_document,
                composition_context,
                provider_dataset_key_id=old_registration[
                    "provider_dataset_key_id"
                ],
                provider_dataset_public_key_base64=provider_window[
                    "dataset_public_key_base64"
                ],
                declared_at_utc=old_registration["declared_at_utc"],
                valid_from_utc=old_registration["valid_from_utc"],
                valid_until_utc=old_registration["valid_until_utc"],
            )
            unsigned_receipt = attestation_contract.build_unsigned_provider_dataset_content_attestation_v1(
                registration,
                composition_document,
                issued_at_utc=provider_window["attestation_receipt"][
                    "issued_at_utc"
                ],
            )
            signature = dataset_private_key.sign(
                bytes.fromhex(unsigned_receipt["receipt_content_sha256"])
            )
            attestation_receipt = attestation_contract.assemble_provider_dataset_content_attestation_receipt_v1(
                unsigned_receipt,
                base64.b64encode(signature).decode("ascii"),
            )
            verification_document = attestation_contract.evaluate_provider_dataset_content_attestation_v1(
                composition_document,
                composition_context,
                registration,
                provider_window["dataset_public_key_base64"],
                attestation_receipt,
                expected_registration_hash=registration["registration_hash"],
                expected_attestation_hash=attestation_receipt[
                    "attestation_hash"
                ],
            )

        provider_window.update(
            composition_document=composition_document,
            composition_context=composition_context,
            registration=registration,
            attestation_receipt=attestation_receipt,
            verification_document=verification_document,
        )
        calendar_records.append(
            {
                "day_offset": day_offset,
                "document": deepcopy(calendar_document),
                "bundle": deepcopy(calendar_bundle),
                "composition_hash": composition_document["composition_hash"],
            }
        )
        return provider_window

    def provider_context_with_bounded_calendar(
        self: unittest.TestCase,
        *,
        second_day_offset: int = 365,
        membership_overrides: dict[int, list[str]] | None = None,
        price_grid_overrides: dict[int, str] | None = None,
    ) -> dict[str, object]:
        return original_provider_context(
            self,
            second_day_offset=(
                SECOND_WINDOW_DAY_OFFSET
                if second_day_offset == 365
                else second_day_offset
            ),
            membership_overrides=membership_overrides,
            price_grid_overrides=price_grid_overrides,
        )

    try:
        with patch.object(
            provider_fixture_class,
            "_provider_window",
            provider_window_with_calendar_evidence,
        ), patch.object(
            provider_fixture_class,
            "_context",
            provider_context_with_bounded_calendar,
        ):
            lineage_case = lineage_fixture_module.StrategyCorrelationUncertaintyMultiWindowObservationMembershipProviderAttestationLifecycleReplayCheckpointPersistenceLineageGateV1Tests()
            lineage_case.setUp()
            correlation_evidence = (
                adr0359_fixture._remove_redundant_correlation_replay_patch(
                    lineage_case
                )
            )
            calendar_evidence = _remove_calendar_patch(lineage_case)

            segment_three = deepcopy(lineage_case.previous_segment)
            gate_three = lineage_case._evaluate(segment_three, None)
            context_four = lineage_case._extended_context()
            segment_four = lineage_case._segment_for_context(
                context_four,
                previous_asset_hash=segment_three["persistence_inputs"][
                    "expected_asset_hash"
                ],
            )
            gate_four = lineage_case._evaluate(segment_four, segment_three)
            context_five = adr0358_fixture._build_tree_five_context(
                lineage_case,
                context_four,
            )
            segment_five, gate_five = adr0358_fixture._build_tree_five_segment(
                lineage_case,
                context_five,
                segment_four,
            )
            lineage_items = [
                {
                    "gate_document": gate_three,
                    "current_segment": segment_three,
                    "previous_segment": None,
                    "expected_gate_hash": gate_three["gate_hash"],
                },
                {
                    "gate_document": gate_four,
                    "current_segment": segment_four,
                    "previous_segment": segment_three,
                    "expected_gate_hash": gate_four["gate_hash"],
                },
                {
                    "gate_document": gate_five,
                    "current_segment": segment_five,
                    "previous_segment": segment_four,
                    "expected_gate_hash": gate_five["gate_hash"],
                },
            ]
            registration = adr0359_fixture._coverage_registration(
                segment_three,
                gate_three,
            )
            registration_receipt = adr0359_fixture.coverage_contract.build_strategy_correlation_persisted_checkpoint_history_coverage_registration_v1(
                registration
            )
            coverage_gate = adr0359_fixture.coverage_contract.evaluate_strategy_correlation_persisted_checkpoint_history_coverage_gate_v1(
                registration=registration,
                registration_receipt=registration_receipt,
                lineage_items=lineage_items,
            )
            yield {
                "fixture_fingerprint": FIXTURE_FINGERPRINT,
                "calendar_records": calendar_records,
                "scaffold_call_count": scaffold_call_count,
                "correlation_evidence": correlation_evidence,
                "calendar_evidence": calendar_evidence,
                "calendar_verifier_is_original": (
                    getattr(calendar_contract, CALENDAR_VERIFY_ATTRIBUTE)
                    is original_calendar_verifier
                    and not isinstance(
                        getattr(calendar_contract, CALENDAR_VERIFY_ATTRIBUTE),
                        Mock,
                    )
                ),
                "remaining_patch_targets": calendar_evidence[
                    "remaining_patch_targets"
                ],
                "lineage_items": lineage_items,
                "registration": registration,
                "registration_receipt": registration_receipt,
                "coverage_gate": coverage_gate,
            }
    finally:
        if lineage_case is not None:
            lineage_case.doCleanups()
        calendar_case.doCleanups()


class StrategyCorrelationPersistedCheckpointHistoryCoverageCalendarSessionSeamClosureV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_context = one_seam_three_segment_fixture_v1()
        cls.material = cls.fixture_context.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.fixture_context.__exit__(None, None, None)

    def test_calendar_documents_reverify_with_original_verifier(self) -> None:
        records = self.material["calendar_records"]
        self.assertEqual(len(records), 2)
        for record in records:
            self.assertTrue(
                _calendar_verifies(
                    getattr(calendar_contract, CALENDAR_VERIFY_ATTRIBUTE),
                    record["document"],
                    record["bundle"],
                )
            )
            self.assertEqual(record["document"]["source_state"], "VERIFIED")
            self.assertTrue(record["bundle"]["calendar_registration_v1"])
            self.assertTrue(record["bundle"]["batch_verification_v1"])

    def test_calendar_verifier_is_original_and_only_provider_seam_remains(
        self,
    ) -> None:
        self.assertTrue(self.material["calendar_verifier_is_original"])
        self.assertEqual(
            self.material["calendar_evidence"]["removed_patch_target"],
            CALENDAR_PATCH_TARGET,
        )
        self.assertEqual(
            self.material["remaining_patch_targets"],
            (PROVIDER_PATCH_TARGET,),
        )
        self.assertTrue(
            self.material["correlation_evidence"][
                "correlation_replay_verifier_is_original"
            ]
        )

    def test_preregistered_eighty_day_non_overlap_is_preserved(self) -> None:
        records = self.material["calendar_records"]
        self.assertEqual({record["day_offset"] for record in records}, {0, 80})
        self.assertEqual(
            sum(record["day_offset"] == 0 for record in records),
            sum(record["day_offset"] == 80 for record in records),
        )
        base = next(record for record in records if record["day_offset"] == 0)
        shifted = next(
            record for record in records if record["day_offset"] == 80
        )
        self.assertEqual(base["document"]["row_count"], 80)
        self.assertEqual(shifted["document"]["row_count"], 80)
        self.assertLess(
            base["document"]["last_observation_date"],
            shifted["document"]["first_observation_date"],
        )

    def test_scaffold_is_not_calendar_authority(self) -> None:
        self.assertGreaterEqual(
            self.material["scaffold_call_count"],
            len(self.material["calendar_records"]),
        )
        self.assertTrue(self.material["calendar_verifier_is_original"])
        for record in self.material["calendar_records"]:
            self.assertTrue(record["composition_hash"])

    def test_three_lineage_gates_and_coverage_pass_but_stay_locked(self) -> None:
        gates = [item["gate_document"] for item in self.material["lineage_items"]]
        self.assertEqual([gate["status"] for gate in gates], ["PASS"] * 3)
        self.assertEqual(self.material["coverage_gate"]["status"], "PASS")
        for gate in [*gates, self.material["coverage_gate"]]:
            self.assertFalse(gate["authority"]["paper_authorized"])
            self.assertFalse(gate["authority"]["live_order_allowed"])
            self.assertFalse(gate["authority"]["profitability_claim_allowed"])

    def test_empty_calendar_sources_are_rejected(self) -> None:
        record = self.material["calendar_records"][0]
        bundle = deepcopy(record["bundle"])
        bundle["calendar_registration_v1"] = {}
        self.assertFalse(
            _calendar_verifies(
                getattr(calendar_contract, CALENDAR_VERIFY_ATTRIBUTE),
                record["document"],
                bundle,
            )
        )

    def test_resealed_calendar_authority_promotion_is_rejected(self) -> None:
        record = self.material["calendar_records"][0]
        promoted = deepcopy(record["document"])
        promoted["authority"]["paper_authorized"] = True
        promoted = seal_strict_canonical_document(promoted, "verification_hash")
        self.assertFalse(
            _calendar_verifies(
                getattr(calendar_contract, CALENDAR_VERIFY_ATTRIBUTE),
                promoted,
                record["bundle"],
            )
        )

    def test_missing_middle_segment_is_unknown_and_locked(self) -> None:
        gate = adr0359_fixture.coverage_contract.evaluate_strategy_correlation_persisted_checkpoint_history_coverage_gate_v1(
            registration=self.material["registration"],
            registration_receipt=self.material["registration_receipt"],
            lineage_items=[
                deepcopy(self.material["lineage_items"][0]),
                deepcopy(self.material["lineage_items"][2]),
            ],
        )
        self.assertEqual(gate["status"], "UNKNOWN")
        self.assertFalse(gate["authority"]["paper_authorized"])
        self.assertFalse(gate["authority"]["live_order_allowed"])
        self.assertFalse(gate["authority"]["profitability_claim_allowed"])


if __name__ == "__main__":
    unittest.main()
