from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from exchange_terminal.application import (
    provider_identity_artifact_transparency_presentation_envelope_v1 as subject,
)
from tests import test_provider_identity_artifact_transparency_availability_v1 as source_test


DIRECT_VERIFIER = (
    "verify_provider_identity_artifact_transparency_availability_evaluation_v1"
)
ANCESTOR_VERIFIER = (
    "verify_provider_identity_witness_conformance_key_governance_evaluation_v1"
)


def _fixture() -> dict[str, object]:
    source_fixture = source_test._fixture()
    source_inputs = source_test._inputs(source_fixture)
    ancestor = subject.source_contract.source_contract.source_contract
    with patch.object(ancestor, ANCESTOR_VERIFIER, return_value=True):
        source_evaluation = subject.source_contract.evaluate_provider_identity_artifact_transparency_availability_v1(
            **source_inputs
        )
    return {
        "source_evaluation": source_evaluation,
        "source_inputs": source_inputs,
        "expected_hash": source_evaluation["receipt_hash"],
    }


def _build(
    fixture: dict[str, object],
    *,
    ancestor_ok: bool = True,
    direct_source_ok: bool | None = None,
) -> dict[str, object]:
    if direct_source_ok is None:
        target = subject.source_contract.source_contract.source_contract
        name = ANCESTOR_VERIFIER
        value = ancestor_ok
    else:
        target = subject.source_contract
        name = DIRECT_VERIFIER
        value = direct_source_ok
    with patch.object(target, name, return_value=value):
        return subject.build_provider_identity_artifact_transparency_presentation_envelope_v1(
            fixture["source_evaluation"],
            fixture["source_inputs"],
            expected_source_evaluation_hash=fixture["expected_hash"],
        )


def _verify(fixture: dict[str, object], document: object) -> bool:
    ancestor = subject.source_contract.source_contract.source_contract
    with patch.object(ancestor, ANCESTOR_VERIFIER, return_value=True):
        return subject.verify_provider_identity_artifact_transparency_presentation_envelope_v1(
            document,
            fixture["source_evaluation"],
            fixture["source_inputs"],
            expected_source_evaluation_hash=fixture["expected_hash"],
        )


class ProviderIdentityArtifactTransparencyPresentationEnvelopeV1Tests(
    unittest.TestCase
):
    def test_complete_source_builds_locked_four_axis_envelope(self) -> None:
        result = _build(_fixture())
        self.assertEqual(result["display_state"], subject.POSITIVE_DISPLAY_STATE)
        self.assertEqual(result["axis_order"], list(subject.AXIS_ORDER))
        self.assertEqual(result["summary"]["artifact_count"], 4)
        self.assertEqual(result["summary"]["observer_count"], 2)
        self.assertEqual(result["summary"]["verified_inclusion_count"], 4)
        self.assertEqual(result["summary"]["signed_retrieval_claim_count"], 8)
        self.assertFalse(result["authority"]["paper_authorized"])
        self.assertFalse(result["authority"]["live_order_allowed"])

    def test_envelope_is_deterministic(self) -> None:
        fixture = _fixture()
        self.assertEqual(_build(fixture), _build(fixture))

    def test_verifier_accepts_exact_output(self) -> None:
        fixture = _fixture()
        self.assertTrue(_verify(fixture, _build(fixture)))

    def test_verifier_rejects_tampering(self) -> None:
        fixture = _fixture()
        result = _build(fixture)
        result["summary"]["artifact_count"] += 1
        self.assertFalse(_verify(fixture, result))

    def test_expected_hash_is_strict(self) -> None:
        fixture = _fixture()
        fixture["expected_hash"] = "not-a-hash"
        self.assertEqual(_build(fixture)["blockers"], ["EXPECTED_SOURCE_EVALUATION_HASH_INVALID"])

    def test_source_hash_is_bound(self) -> None:
        fixture = _fixture()
        fixture["expected_hash"] = "0" * 64
        self.assertEqual(_build(fixture)["blockers"], ["SOURCE_EVALUATION_HASH_MISMATCH"])

    def test_source_inputs_are_required(self) -> None:
        fixture = _fixture()
        fixture["source_inputs"] = None
        self.assertEqual(_build(fixture)["blockers"], ["SOURCE_EVALUATION_INPUTS_INVALID"])

    def test_real_source_verifier_is_required(self) -> None:
        self.assertEqual(
            _build(_fixture(), ancestor_ok=False)["blockers"],
            ["SOURCE_EVALUATION_UNVERIFIED"],
        )

    def test_source_status_is_required(self) -> None:
        fixture = _fixture()
        fixture["source_evaluation"]["status"] = "UNKNOWN"
        self.assertEqual(
            _build(fixture, direct_source_ok=True)["blockers"],
            ["SOURCE_EVALUATION_STATUS_INVALID"],
        )

    def test_source_contract_identity_is_bound(self) -> None:
        fixture = _fixture()
        fixture["source_evaluation"]["static_fingerprint"] = "other"
        self.assertEqual(
            _build(fixture, direct_source_ok=True)["blockers"],
            ["SOURCE_CONTRACT_IDENTITY_INVALID"],
        )

    def test_source_evidence_shape_is_exact(self) -> None:
        fixture = _fixture()
        fixture["source_evaluation"]["evidence"]["extra"] = True
        self.assertEqual(
            _build(fixture, direct_source_ok=True)["blockers"],
            ["SOURCE_EVIDENCE_SHAPE_INVALID"],
        )

    def test_source_hash_fields_are_strict(self) -> None:
        fixture = _fixture()
        fixture["source_evaluation"]["evidence"]["artifact_catalog_root_hash"] = "A" * 64
        self.assertEqual(
            _build(fixture, direct_source_ok=True)["blockers"],
            ["SOURCE_EVIDENCE_HASH_INVALID"],
        )

    def test_bool_is_not_an_integer(self) -> None:
        fixture = _fixture()
        fixture["source_evaluation"]["evidence"]["artifact_count"] = True
        self.assertEqual(
            _build(fixture, direct_source_ok=True)["blockers"],
            ["SOURCE_EVIDENCE_INTEGER_INVALID"],
        )

    def test_checkpoint_must_cover_artifact_scope(self) -> None:
        fixture = _fixture()
        fixture["source_evaluation"]["evidence"]["checkpoint_tree_size"] = 1
        self.assertEqual(
            _build(fixture, direct_source_ok=True)["blockers"],
            ["SOURCE_CHECKPOINT_SCOPE_INVALID"],
        )

    def test_observer_receipts_must_be_distinct(self) -> None:
        fixture = _fixture()
        evidence = fixture["source_evaluation"]["evidence"]
        evidence["observer_b_receipt_hash"] = evidence["observer_a_receipt_hash"]
        self.assertEqual(
            _build(fixture, direct_source_ok=True)["blockers"],
            ["SOURCE_OBSERVER_RECEIPTS_NOT_DISTINCT"],
        )

    def test_positive_source_facts_are_required(self) -> None:
        fixture = _fixture()
        fixture["source_evaluation"]["facts"]["dual_observer_result_agreement_verified"] = False
        self.assertEqual(
            _build(fixture, direct_source_ok=True)["blockers"],
            ["SOURCE_POSITIVE_FACTS_INCOMPLETE"],
        )

    def test_external_fact_promotion_is_rejected(self) -> None:
        fixture = _fixture()
        fixture["source_evaluation"]["facts"]["public_artifact_availability_verified"] = True
        self.assertEqual(
            _build(fixture, direct_source_ok=True)["blockers"],
            ["SOURCE_EXTERNAL_FACT_PROMOTION_REJECTED"],
        )

    def test_source_authority_promotion_is_rejected(self) -> None:
        fixture = _fixture()
        fixture["source_evaluation"]["authority"]["paper_allowed"] = True
        self.assertEqual(
            _build(fixture, direct_source_ok=True)["blockers"],
            ["SOURCE_AUTHORITY_PROMOTION_REJECTED"],
        )

    def test_unknown_output_does_not_expose_evidence(self) -> None:
        result = _build(_fixture(), ancestor_ok=False)
        self.assertEqual(result["display_state"], "UNKNOWN")
        self.assertTrue(all(value is None for value in result["summary"].values()))
        self.assertTrue(all(value is None for value in result["lineage"].values()))
        self.assertTrue(all(value is False for value in result["facts"].values()))

    def test_projection_excludes_payloads_urls_keys_and_signatures(self) -> None:
        result = _build(_fixture())
        text = repr(result).lower()
        for forbidden in ("content_base64url", "https://", "public_key", "signature"):
            self.assertNotIn(forbidden, text)
        self.assertNotIn("ready", text)

    def test_source_hash_is_projected_in_lineage(self) -> None:
        fixture = _fixture()
        result = _build(fixture)
        self.assertEqual(
            result["lineage"]["source_evaluation_receipt_hash"],
            fixture["source_evaluation"]["receipt_hash"],
        )


if __name__ == "__main__":
    unittest.main()
