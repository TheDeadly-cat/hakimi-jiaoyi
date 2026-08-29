from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import unittest
from unittest.mock import Mock, _patch, patch

from exchange_terminal.services import (
    strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1
    as provider_contract,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import (
    test_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1
    as provider_fixture_module,
)
from tests import (
    test_strategy_correlation_persisted_checkpoint_history_coverage_calendar_session_seam_closure_v1
    as adr0360_fixture,
)
from tests import (
    test_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_binding_gate_v1
    as provider_binding_fixture_module,
)


FIXTURE_FINGERPRINT = (
    "20260824-strategy-correlation-persisted-checkpoint-history-coverage-"
    "provider-identity-seam-closure-v1"
)
PROVIDER_VERIFY_ATTRIBUTE = (
    "verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_"
    "provider_identity_assertion_verifier_v1"
)
PROVIDER_PATCH_TARGET = adr0360_fixture.PROVIDER_PATCH_TARGET


def _provider_verifies(
    verifier: object,
    document: dict[str, object],
    bundle: dict[str, object],
) -> bool:
    return bool(
        verifier(
            document,
            bundle["provider_identity_registration_v1"],
            bundle["provider_identity_registration_verification_context"],
            bundle["identity_assertion_receipt"],
            expected_provider_identity_registration_hash=bundle[
                "expected_provider_identity_registration_hash"
            ],
            expected_identity_assertion_hash=bundle[
                "expected_identity_assertion_hash"
            ],
        )
    )


def _provider_contexts(value: object) -> list[dict[str, object]]:
    contexts: list[dict[str, object]] = []

    def visit(current: object) -> None:
        if isinstance(current, dict):
            if {
                "provider_identity_verification",
                "provider_verification_bundle",
            }.issubset(current):
                contexts.append(current)
            for child in current.values():
                visit(child)
        elif isinstance(current, (list, tuple)):
            for child in current:
                visit(child)

    visit(value)
    return contexts


@contextmanager
def zero_seam_three_segment_fixture_v1():
    provider_case = provider_fixture_module.StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityAssertionVerifierV1Tests()
    provider_case.setUp()
    provider_document = provider_case._build()
    provider_bundle = {
        "provider_identity_registration_v1": provider_case.registration,
        "provider_identity_registration_verification_context": (
            provider_case.registration_context
        ),
        "identity_assertion_receipt": provider_case.receipt,
        "expected_provider_identity_registration_hash": provider_case.registration[
            "registration_hash"
        ],
        "expected_identity_assertion_hash": provider_case.receipt[
            "assertion_hash"
        ],
    }
    original_provider_verifier = getattr(
        provider_contract,
        PROVIDER_VERIFY_ATTRIBUTE,
    )
    provider_fixture_class = provider_binding_fixture_module.StrategyCorrelationUncertaintyMultiWindowObservationMembershipProviderAttestationBindingGateV1Tests
    original_provider_window = provider_fixture_class._provider_window
    source_context: object | None = None

    def provider_window_with_complete_identity_source(
        self: unittest.TestCase,
        *,
        day_offset: int,
        data_hash_suffix: str,
        dataset_private_key: object,
    ) -> dict[str, object]:
        provider_window = original_provider_window(
            self,
            day_offset=day_offset,
            data_hash_suffix=data_hash_suffix,
            dataset_private_key=dataset_private_key,
        )
        provider_window["composition_context"][
            "provider_identity_verification"
        ] = deepcopy(provider_document)
        provider_window["composition_context"][
            "provider_verification_bundle"
        ] = deepcopy(provider_bundle)
        return provider_window

    try:
        with patch.object(
            provider_fixture_class,
            "_provider_window",
            provider_window_with_complete_identity_source,
        ):
            source_context = adr0360_fixture.one_seam_three_segment_fixture_v1()
            material = source_context.__enter__()
            matches = [
                patcher
                for patcher in list(_patch._active_patches)
                if patcher.attribute == PROVIDER_VERIFY_ATTRIBUTE
            ]
            if len(matches) != 1:
                raise AssertionError(
                    "expected exactly one provider-identity verifier patch"
                )
            provider_patcher = matches[0]
            mocked_verifier = getattr(provider_contract, PROVIDER_VERIFY_ATTRIBUTE)
            if not isinstance(mocked_verifier, Mock):
                raise AssertionError("provider-identity verifier patch is not a mock")
            captured_calls = list(mocked_verifier.call_args_list)
            captured_original_results = [
                bool(original_provider_verifier(*call.args, **call.kwargs))
                for call in captured_calls
            ]
            provider_patcher.stop()
            active_provider_verifier = getattr(
                provider_contract,
                PROVIDER_VERIFY_ATTRIBUTE,
            )
            if (
                active_provider_verifier is not original_provider_verifier
                or isinstance(active_provider_verifier, Mock)
            ):
                raise AssertionError("provider-identity verifier remained mocked")

            contexts = _provider_contexts(material["lineage_items"])
            unique_sources: dict[
                tuple[str, str], tuple[dict[str, object], dict[str, object]]
            ] = {}
            for context in contexts:
                document = context["provider_identity_verification"]
                bundle = context["provider_verification_bundle"]
                unique_sources[
                    (
                        document["verification_hash"],
                        bundle["expected_identity_assertion_hash"],
                    )
                ] = (document, bundle)
            if not unique_sources:
                raise AssertionError("final provider-identity sources were not found")
            if not all(
                _provider_verifies(
                    original_provider_verifier,
                    document,
                    bundle,
                )
                for document, bundle in unique_sources.values()
            ):
                raise AssertionError(
                    "final provider-identity source failed original verification"
                )

            coverage_contract = adr0360_fixture.adr0359_fixture.coverage_contract
            coverage_reverified = coverage_contract.verify_strategy_correlation_persisted_checkpoint_history_coverage_gate_v1(
                material["coverage_gate"],
                registration=material["registration"],
                registration_receipt=material["registration_receipt"],
                lineage_items=material["lineage_items"],
                expected_gate_hash=material["coverage_gate"]["gate_hash"],
            )
            if not coverage_reverified:
                raise AssertionError(
                    "coverage failed after provider-identity seam removal"
                )

            active_fixture_targets = tuple(
                sorted(
                    patcher.attribute
                    for patcher in _patch._active_patches
                    if getattr(patcher, "attribute", None)
                    in {
                        adr0360_fixture.CALENDAR_VERIFY_ATTRIBUTE,
                        PROVIDER_VERIFY_ATTRIBUTE,
                    }
                )
            )
            yield {
                **material,
                "fixture_fingerprint": FIXTURE_FINGERPRINT,
                "provider_records": [
                    {
                        "document": deepcopy(document),
                        "bundle": deepcopy(bundle),
                    }
                    for document, bundle in unique_sources.values()
                ],
                "captured_call_count": len(captured_calls),
                "captured_original_pass_count": sum(
                    captured_original_results
                ),
                "captured_original_fail_count": sum(
                    not result for result in captured_original_results
                ),
                "provider_verifier_is_original": True,
                "removed_patch_target": PROVIDER_PATCH_TARGET,
                "remaining_patch_targets": active_fixture_targets,
                "coverage_reverified_after_seam_removal": coverage_reverified,
            }
    finally:
        if source_context is not None:
            source_context.__exit__(None, None, None)
        provider_case.doCleanups()


class StrategyCorrelationPersistedCheckpointHistoryCoverageProviderIdentitySeamClosureV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_context = zero_seam_three_segment_fixture_v1()
        cls.material = cls.fixture_context.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.fixture_context.__exit__(None, None, None)

    def test_provider_verifier_is_original_and_no_fixture_seams_remain(
        self,
    ) -> None:
        self.assertTrue(self.material["provider_verifier_is_original"])
        self.assertEqual(
            self.material["removed_patch_target"],
            PROVIDER_PATCH_TARGET,
        )
        self.assertEqual(self.material["remaining_patch_targets"], ())
        self.assertIs(
            getattr(provider_contract, PROVIDER_VERIFY_ATTRIBUTE),
            provider_contract.verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1,
        )

    def test_legacy_scaffold_failures_are_fully_accounted(self) -> None:
        self.assertGreater(self.material["captured_call_count"], 0)
        self.assertGreater(self.material["captured_original_pass_count"], 0)
        self.assertEqual(
            self.material["captured_original_fail_count"],
            self.material["scaffold_call_count"],
        )
        self.assertEqual(
            self.material["captured_original_pass_count"]
            + self.material["captured_original_fail_count"],
            self.material["captured_call_count"],
        )

    def test_final_provider_sources_reverify_with_original_verifier(self) -> None:
        records = self.material["provider_records"]
        self.assertGreaterEqual(len(records), 1)
        for record in records:
            self.assertTrue(
                _provider_verifies(
                    getattr(provider_contract, PROVIDER_VERIFY_ATTRIBUTE),
                    record["document"],
                    record["bundle"],
                )
            )
            self.assertEqual(record["document"]["source_state"], "VERIFIED")
            self.assertTrue(
                record["document"][
                    "identity_assertion_verification_state"
                ].startswith("IDENTITY_ASSERTION_SIGNATURE_AND_MEMBERSHIP_VERIFIED")
            )

    def test_final_provider_output_redacts_crypto_material(self) -> None:
        forbidden = {
            "identity_assertion_receipt",
            "membership_proof",
            "registry_public_key_base64",
            "registry_signature_base64",
            "sibling_sha256",
        }
        for record in self.material["provider_records"]:
            self.assertTrue(forbidden.isdisjoint(record["document"]))
            self.assertEqual(record["document"]["membership_proof_count"], 2)

    def test_coverage_reverifies_and_authority_stays_locked(self) -> None:
        self.assertTrue(
            self.material["coverage_reverified_after_seam_removal"]
        )
        self.assertEqual(self.material["coverage_gate"]["status"], "PASS")
        gates = [
            item["gate_document"] for item in self.material["lineage_items"]
        ]
        self.assertEqual([gate["status"] for gate in gates], ["PASS"] * 3)
        for gate in [*gates, self.material["coverage_gate"]]:
            self.assertFalse(gate["authority"]["paper_authorized"])
            self.assertFalse(gate["authority"]["live_order_allowed"])
            self.assertFalse(gate["authority"]["profitability_claim_allowed"])

    def test_empty_provider_registration_is_rejected(self) -> None:
        record = self.material["provider_records"][0]
        bundle = deepcopy(record["bundle"])
        bundle["provider_identity_registration_v1"] = {}
        self.assertFalse(
            _provider_verifies(
                getattr(provider_contract, PROVIDER_VERIFY_ATTRIBUTE),
                record["document"],
                bundle,
            )
        )

    def test_resealed_provider_authority_promotion_is_rejected(self) -> None:
        record = self.material["provider_records"][0]
        promoted = deepcopy(record["document"])
        promoted["authority"]["paper_authorized"] = True
        promoted = seal_strict_canonical_document(promoted, "verification_hash")
        self.assertFalse(
            _provider_verifies(
                getattr(provider_contract, PROVIDER_VERIFY_ATTRIBUTE),
                promoted,
                record["bundle"],
            )
        )

    def test_missing_middle_segment_is_unknown_and_locked(self) -> None:
        coverage_contract = adr0360_fixture.adr0359_fixture.coverage_contract
        gate = coverage_contract.evaluate_strategy_correlation_persisted_checkpoint_history_coverage_gate_v1(
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
