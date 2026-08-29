from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.portfolio_correlation_admission_v1 import (
    build_portfolio_correlation_admission_v1,
)
from exchange_terminal.services.static_presentation_asset_registration_v1 import (
    build_portfolio_correlation_admission_rail_asset_registration_v1,
)
from exchange_terminal.services.static_presentation_in_memory_delivery_v1 import (
    build_portfolio_correlation_admission_rail_in_memory_delivery_envelope_v1,
    verify_portfolio_correlation_admission_rail_in_memory_delivery_envelope_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import test_portfolio_correlation_admission_v1 as portfolio_admission_tests


class NonNativeMapping(dict):
    pass


class StaticPresentationInMemoryDeliveryV1Tests(unittest.TestCase):
    def _fixture(self, correlation: float = 0.10) -> dict:
        producer = portfolio_admission_tests.PortfolioCorrelationAdmissionV1Tests(
            methodName="runTest"
        )
        evidence = producer._evidence(correlation=correlation)
        admission = build_portfolio_correlation_admission_v1(**evidence)
        return {
            "registration_document": (
                build_portfolio_correlation_admission_rail_asset_registration_v1()
            ),
            "admission_document": admission,
            **evidence,
        }

    def _build(self, fixture: dict) -> dict:
        return build_portfolio_correlation_admission_rail_in_memory_delivery_envelope_v1(
            **fixture
        )

    def _verify(self, envelope: dict, fixture: dict) -> bool:
        return verify_portfolio_correlation_admission_rail_in_memory_delivery_envelope_v1(
            envelope,
            **fixture,
        )

    def test_exact_local_pass_candidate_is_enveloped_but_host_blocked(self) -> None:
        fixture = self._fixture()
        envelope = self._build(fixture)
        self.assertEqual(envelope["status"], "BLOCKED")
        self.assertEqual(envelope["source_status"], "PASS")
        self.assertEqual(envelope["payload"], fixture["admission_document"])
        self.assertTrue(self._verify(envelope, fixture))

    def test_exact_high_correlation_block_is_still_deliverable(self) -> None:
        fixture = self._fixture(correlation=0.90)
        envelope = self._build(fixture)
        self.assertEqual(envelope["status"], "BLOCKED")
        self.assertEqual(envelope["source_status"], "BLOCK")
        self.assertEqual(
            envelope["payload"]["first_blocking_tier"],
            "COMPLETE_LINK",
        )
        self.assertTrue(self._verify(envelope, fixture))

    def test_registration_tamper_returns_unknown(self) -> None:
        fixture = self._fixture()
        tampered = copy.deepcopy(fixture["registration_document"])
        tampered["authority"]["paper_authorized"] = True
        tampered.pop("registration_hash")
        fixture["registration_document"] = seal_strict_canonical_document(
            tampered,
            "registration_hash",
        )
        envelope = self._build(fixture)
        self.assertEqual(envelope["status"], "UNKNOWN")
        self.assertEqual(envelope["reason_code"], "ASSET_REGISTRATION_NOT_EXACT")
        self.assertIsNone(envelope["payload"])

    def test_admission_tamper_returns_unknown(self) -> None:
        fixture = self._fixture()
        tampered = copy.deepcopy(fixture["admission_document"])
        tampered["permissions"]["live_order_allowed"] = True
        tampered.pop("correlation_admission_hash")
        fixture["admission_document"] = seal_strict_canonical_document(
            tampered,
            "correlation_admission_hash",
        )
        envelope = self._build(fixture)
        self.assertEqual(envelope["status"], "UNKNOWN")
        self.assertEqual(envelope["reason_code"], "ADMISSION_CANDIDATE_NOT_EXACT")

    def test_source_context_drift_returns_unknown(self) -> None:
        fixture = self._fixture()
        fixture["strategy_id"] = "strategy-forged"
        envelope = self._build(fixture)
        self.assertEqual(envelope["status"], "UNKNOWN")
        self.assertEqual(envelope["reason_code"], "ADMISSION_CANDIDATE_NOT_EXACT")

    def test_non_native_mapping_fails_snapshot_boundary(self) -> None:
        fixture = self._fixture()
        fixture["admission_document"] = NonNativeMapping(
            fixture["admission_document"]
        )
        envelope = self._build(fixture)
        self.assertEqual(envelope["status"], "UNKNOWN")
        self.assertEqual(envelope["reason_code"], "DELIVERY_INPUT_SNAPSHOT_FAILED")

    def test_builder_is_deterministic_and_does_not_mutate_inputs(self) -> None:
        fixture = self._fixture()
        before = copy.deepcopy(fixture)
        first = self._build(fixture)
        second = self._build(fixture)
        self.assertEqual(first, second)
        self.assertEqual(fixture, before)

    def test_only_admission_candidate_is_embedded(self) -> None:
        fixture = self._fixture()
        envelope = self._build(fixture)
        self.assertTrue(envelope["facts"]["admission_candidate_embedded"])
        self.assertFalse(envelope["facts"]["raw_source_report_embedded"])
        self.assertFalse(envelope["facts"]["raw_correlation_evidence_embedded"])
        self.assertNotIn("report_document", envelope)
        self.assertNotIn("correlation_matrix_document", envelope)

    def test_transport_has_no_endpoint_route_or_host_slot(self) -> None:
        envelope = self._build(self._fixture())
        self.assertEqual(envelope["transport"]["mode"], "IN_MEMORY_ARGUMENT_ONLY")
        self.assertIsNone(envelope["transport"]["endpoint"])
        self.assertIsNone(envelope["transport"]["route"])
        self.assertIsNone(envelope["transport"]["host_slot"])

    def test_all_execution_and_trading_authority_remains_locked(self) -> None:
        envelope = self._build(self._fixture())
        self.assertTrue(all(value is False for value in envelope["authority"].values()))
        self.assertFalse(envelope["facts"]["delivery_attempted"])
        self.assertFalse(envelope["facts"]["browser_executed"])
        self.assertFalse(envelope["facts"]["dom_mounted"])
        self.assertFalse(envelope["facts"]["runtime_mutations_performed"])

    def test_resealed_envelope_promotion_fails_exact_verifier(self) -> None:
        fixture = self._fixture()
        envelope = self._build(fixture)
        promoted = copy.deepcopy(envelope)
        promoted["facts"]["browser_executed"] = True
        promoted.pop("envelope_hash")
        promoted = seal_strict_canonical_document(promoted, "envelope_hash")
        self.assertFalse(self._verify(promoted, fixture))

    def test_unknown_envelope_can_verify_as_exact_fail_closed_result(self) -> None:
        fixture = self._fixture()
        fixture["admission_document"] = {}
        envelope = self._build(fixture)
        self.assertEqual(envelope["status"], "UNKNOWN")
        self.assertTrue(self._verify(envelope, fixture))


if __name__ == "__main__":
    unittest.main()
