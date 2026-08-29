from __future__ import annotations

import copy
from hashlib import sha256
import json
from pathlib import Path
import unittest

from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_binding_v1 as binding_v1,
)
from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_in_memory_delivery_v1 as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import (
    test_portfolio_correlation_admission_effective_budget_binding_v1 as binding_tests,
)


ROOT = Path(__file__).resolve().parents[1]


class _DictSubclass(dict):
    pass


class PortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.fixture = (
            binding_tests.PortfolioCorrelationAdmissionEffectiveBudgetBindingV1Tests()
        )
        self.fixture.setUp()
        self.binding = self.fixture.binding
        self.envelope = self._delivery(self.binding)

        self.concentrated_inputs = copy.deepcopy(self.fixture.inputs)
        self.concentrated_inputs["positions"] = [
            {"symbol": "A", "notional": 5000, "direction": "LONG"}
        ]
        self.concentrated_inputs["proposed_symbol"] = "B"
        self.concentrated_inputs["proposed_notional"] = 5000
        self.concentrated_inputs["max_cluster_gross_pct"] = 45.0
        self.blocked_budget = self.fixture._build_budget(
            self.concentrated_inputs
        )
        self.blocked_binding = self.fixture._build_binding(
            budget=self.blocked_budget,
            inputs=self.concentrated_inputs,
        )
        self.blocked_envelope = self._delivery(
            self.blocked_binding,
            budget=self.blocked_budget,
            inputs=self.concentrated_inputs,
        )
        self.unknown_envelope = self._delivery({})

    def _delivery(
        self,
        binding: object,
        *,
        budget: object | None = None,
        inputs: dict | None = None,
    ) -> dict:
        clean_budget = self.fixture.budget if budget is None else budget
        clean_inputs = self.fixture.inputs if inputs is None else inputs
        evidence = self.fixture.evidence
        return subject.build_portfolio_correlation_admission_effective_budget_in_memory_delivery_envelope_v1(
            binding,
            self.fixture.admission,
            clean_budget,
            evidence["report_document"],
            evidence["correlation_preregistration_document"],
            evidence["correlation_matrix_document"],
            evidence["selection_cells_document"],
            self.fixture.budget_case.audit,
            evidence["complete_link_gate_document"],
            evidence["strata_preregistration_document"],
            evidence["strata_gate_document"],
            strategy_id=evidence["strategy_id"],
            variant_id=evidence["variant_id"],
            lane=evidence["lane"],
            **clean_inputs,
        )

    def _verify(
        self,
        document: object,
        binding: object | None = None,
        *,
        budget: object | None = None,
        inputs: dict | None = None,
    ) -> bool:
        clean_binding = self.binding if binding is None else binding
        clean_budget = self.fixture.budget if budget is None else budget
        clean_inputs = self.fixture.inputs if inputs is None else inputs
        evidence = self.fixture.evidence
        return subject.verify_portfolio_correlation_admission_effective_budget_in_memory_delivery_envelope_v1(
            document,
            clean_binding,
            self.fixture.admission,
            clean_budget,
            evidence["report_document"],
            evidence["correlation_preregistration_document"],
            evidence["correlation_matrix_document"],
            evidence["selection_cells_document"],
            self.fixture.budget_case.audit,
            evidence["complete_link_gate_document"],
            evidence["strata_preregistration_document"],
            evidence["strata_gate_document"],
            strategy_id=evidence["strategy_id"],
            variant_id=evidence["variant_id"],
            lane=evidence["lane"],
            **clean_inputs,
        )

    def test_exact_pass_binding_builds_known_envelope(self) -> None:
        self.assertEqual(self.envelope["status"], "KNOWN")
        self.assertEqual(self.envelope["delivery_state"], "EXACT_IN_MEMORY")
        self.assertEqual(
            self.envelope["presentation_payload"]["binding_status"],
            "PASS",
        )
        self.assertTrue(self._verify(self.envelope))

    def test_exact_block_binding_remains_known_and_blocked(self) -> None:
        payload = self.blocked_envelope["presentation_payload"]
        self.assertEqual(self.blocked_envelope["status"], "KNOWN")
        self.assertEqual(payload["binding_status"], "BLOCK")
        self.assertEqual(
            payload["first_blocking_tier"],
            "EFFECTIVE_BUDGET_V3_DECISION",
        )
        self.assertTrue(
            self._verify(
                self.blocked_envelope,
                self.blocked_binding,
                budget=self.blocked_budget,
                inputs=self.concentrated_inputs,
            )
        )

    def test_malformed_binding_builds_canonical_unknown(self) -> None:
        self.assertEqual(self.unknown_envelope["status"], "UNKNOWN")
        self.assertEqual(self.unknown_envelope["delivery_state"], "UNKNOWN")
        self.assertIsNone(self.unknown_envelope["presentation_payload"])
        self.assertEqual(
            self.unknown_envelope["reason_code"],
            "BINDING_UNKNOWN",
        )
        self.assertTrue(self._verify(self.unknown_envelope, {}))

    def test_non_native_binding_container_is_unknown(self) -> None:
        envelope = self._delivery(_DictSubclass(self.binding))
        self.assertEqual(envelope["status"], "UNKNOWN")
        self.assertEqual(envelope["reason_code"], "BINDING_UNKNOWN")

    def test_resealed_binding_authority_drift_is_unknown(self) -> None:
        binding = copy.deepcopy(self.binding)
        binding["authority"]["live_order_allowed"] = True
        binding = seal_strict_canonical_document(binding, "binding_hash")
        envelope = self._delivery(binding)
        self.assertEqual(envelope["status"], "UNKNOWN")
        self.assertEqual(envelope["reason_code"], "BINDING_UNKNOWN")

    def test_payload_and_envelope_are_summary_only(self) -> None:
        encoded = json.dumps(self.envelope, sort_keys=True)
        for forbidden in (
            '"positions":',
            '"symbol":',
            '"notional":',
            "synthetic-strategy",
            "synthetic-variant",
            "selection_cells",
            "cluster_exposures",
        ):
            self.assertNotIn(forbidden, encoded)
        payload = self.envelope["presentation_payload"]
        self.assertTrue(payload["facts"]["hash_only_projection"])
        self.assertFalse(payload["facts"]["source_documents_embedded"])
        self.assertEqual(len(payload["source"]), 12)

    def test_builder_is_deterministic_and_does_not_mutate_inputs(self) -> None:
        before = copy.deepcopy(
            (
                self.binding,
                self.fixture.admission,
                self.fixture.budget,
                self.fixture.evidence,
                self.fixture.inputs,
            )
        )
        repeated = self._delivery(self.binding)
        self.assertEqual(repeated, self.envelope)
        self.assertEqual(
            (
                self.binding,
                self.fixture.admission,
                self.fixture.budget,
                self.fixture.evidence,
                self.fixture.inputs,
            ),
            before,
        )

    def test_payload_hash_is_bound_into_envelope_provenance(self) -> None:
        payload = self.envelope["presentation_payload"]
        self.assertEqual(
            self.envelope["provenance"]["presentation_payload_hash"],
            payload["presentation_payload_hash"],
        )
        self.assertEqual(
            self.envelope["provenance"]["binding_hash"],
            payload["source"]["binding_hash"],
        )
        self.assertEqual(
            self.envelope["provenance"]["admission_v2_hash"],
            payload["source"]["admission_v2_hash"],
        )
        self.assertEqual(
            self.envelope["provenance"]["effective_budget_v3_hash"],
            payload["source"]["effective_budget_v3_hash"],
        )

    def test_resealed_payload_promotion_fails_exact_verification(self) -> None:
        envelope = copy.deepcopy(self.envelope)
        payload = envelope["presentation_payload"]
        payload["permissions"]["paper_authorized"] = True
        payload = seal_strict_canonical_document(
            payload,
            "presentation_payload_hash",
        )
        envelope["presentation_payload"] = payload
        envelope["provenance"]["presentation_payload_hash"] = payload[
            "presentation_payload_hash"
        ]
        envelope = seal_strict_canonical_document(
            envelope,
            "delivery_envelope_hash",
        )
        self.assertFalse(self._verify(envelope))

    def test_resealed_envelope_authority_promotion_fails(self) -> None:
        envelope = copy.deepcopy(self.envelope)
        envelope["authority"]["browser_execution_allowed"] = True
        envelope = seal_strict_canonical_document(
            envelope,
            "delivery_envelope_hash",
        )
        self.assertFalse(self._verify(envelope))

    def test_permission_and_runtime_locks_remain_false(self) -> None:
        for document in (
            self.envelope,
            self.blocked_envelope,
            self.unknown_envelope,
        ):
            self.assertTrue(document["authority"]["descriptive_only"])
            for key, value in document["authority"].items():
                if key != "descriptive_only":
                    self.assertFalse(value)
            self.assertFalse(document["facts"]["runtime_mutations_performed"])
            self.assertFalse(document["facts"]["profitability_proven"])

    def test_binding_implementation_pin_matches_current_source(self) -> None:
        path = (
            ROOT
            / "exchange_terminal/services/"
            "portfolio_correlation_admission_effective_budget_binding_v1.py"
        )
        self.assertEqual(
            sha256(path.read_bytes()).hexdigest(),
            subject.BINDING_IMPLEMENTATION_SHA256,
        )


if __name__ == "__main__":
    unittest.main()
