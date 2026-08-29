from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_adapter_v6_presentation_envelope_v1 as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
import tests.test_strategy_correlation_cluster_portfolio_risk_adapter_v6 as adapter_v6_support


class AdapterV6PresentationEnvelopeV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.v6_case = adapter_v6_support.PortfolioRiskAdapterV6Tests(
            "test_tail_clear_and_adapter_v5_pass_allow_research_pass"
        )
        self.v6_case.setUp()
        self.addCleanup(self.v6_case.doCleanups)
        self.adapter_v5 = copy.deepcopy(self.v6_case.adapter_v5)
        self.adapter_context = copy.deepcopy(self.v6_case.adapter_context)
        self.registration, self.evaluation, self.tail_context = (
            self.v6_case._tail(coupled=False)
        )
        self.adapter_v6 = self.v6_case._evaluate(
            adapter_v5_document=self.adapter_v5,
            adapter_context=self.adapter_context,
            registration=self.registration,
            evaluation=self.evaluation,
            tail_context=self.tail_context,
        )
        self.envelope = self._build()

    def _verify_adapter_v6_boundary(
        self,
        document: object,
        adapter_v5_document: object,
        downside_tail_registration: object,
        downside_tail_evaluation: object,
        *,
        adapter_v5_verification_context: object,
        downside_tail_verification_context: object,
    ) -> dict:
        try:
            expected = self.v6_case._evaluate(
                adapter_v5_document=adapter_v5_document,
                adapter_context=adapter_v5_verification_context,
                registration=downside_tail_registration,
                evaluation=downside_tail_evaluation,
                tail_context=downside_tail_verification_context,
            )
            exact = strict_json_contract_equal(document, expected)
        except (KeyError, MemoryError, TypeError, ValueError):
            exact = False
        return {
            "schema_version": subject.adapter_v6.VERIFICATION_SCHEMA_VERSION,
            "status": "PASS" if exact else "BLOCK",
            "adapter_v6_exactly_rebuilt": exact,
            "adapter_v6_status": (
                document.get("status")
                if exact and type(document) is dict
                else "UNKNOWN"
            ),
            "adapter_v6_hash": (
                document.get("adapter_v6_hash")
                if exact and type(document) is dict
                else None
            ),
            "blockers": [] if exact else ["adapter_v6_exact_rebuild"],
            "risk_reduction_joint_exemption_verified": False,
            "current_admission_allowed": False,
            "live_order_allowed": False,
            "paper_authorized": False,
            "runtime_gate_activation_allowed": False,
            "writer_allowed": False,
        }

    def _build(
        self,
        *,
        adapter_v6_document: dict | None = None,
        adapter_v5_document: dict | None = None,
        registration: dict | None = None,
        evaluation: dict | None = None,
        expected_hash: str | None = None,
        adapter_context: dict | None = None,
        tail_context: dict | None = None,
    ) -> dict:
        adapter_v6_document = (
            self.adapter_v6
            if adapter_v6_document is None
            else adapter_v6_document
        )
        adapter_v5_document = (
            self.adapter_v5
            if adapter_v5_document is None
            else adapter_v5_document
        )
        registration = (
            self.registration if registration is None else registration
        )
        evaluation = self.evaluation if evaluation is None else evaluation
        expected_hash = (
            adapter_v6_document.get("adapter_v6_hash")
            if expected_hash is None and type(adapter_v6_document) is dict
            else expected_hash
        )
        adapter_context = (
            self.adapter_context
            if adapter_context is None
            else adapter_context
        )
        tail_context = (
            self.tail_context if tail_context is None else tail_context
        )
        with patch.object(
            subject.adapter_v6,
            "verify_strategy_correlation_cluster_portfolio_risk_adapter_v6",
            side_effect=self._verify_adapter_v6_boundary,
        ):
            return subject.build_strategy_correlation_cluster_portfolio_risk_adapter_v6_presentation_envelope_v1(
                copy.deepcopy(adapter_v6_document),
                copy.deepcopy(adapter_v5_document),
                copy.deepcopy(registration),
                copy.deepcopy(evaluation),
                expected_adapter_v6_hash=expected_hash,
                adapter_v5_verification_context=copy.deepcopy(
                    adapter_context
                ),
                downside_tail_verification_context=copy.deepcopy(
                    tail_context
                ),
            )

    def _verify(self, envelope: dict) -> dict:
        with patch.object(
            subject.adapter_v6,
            "verify_strategy_correlation_cluster_portfolio_risk_adapter_v6",
            side_effect=self._verify_adapter_v6_boundary,
        ):
            return subject.verify_strategy_correlation_cluster_portfolio_risk_adapter_v6_presentation_envelope_v1(
                copy.deepcopy(envelope),
                copy.deepcopy(self.adapter_v6),
                copy.deepcopy(self.adapter_v5),
                copy.deepcopy(self.registration),
                copy.deepcopy(self.evaluation),
                expected_adapter_v6_hash=self.adapter_v6["adapter_v6_hash"],
                adapter_v5_verification_context=copy.deepcopy(
                    self.adapter_context
                ),
                downside_tail_verification_context=copy.deepcopy(
                    self.tail_context
                ),
            )

    def _source_bundle(
        self,
        *,
        coupled: bool,
    ) -> tuple[dict, dict, dict, dict]:
        registration, evaluation, context = self.v6_case._tail(
            coupled=coupled
        )
        document = self.v6_case._evaluate(
            registration=registration,
            evaluation=evaluation,
            tail_context=context,
        )
        return document, registration, evaluation, context

    def test_exact_clear_local_gate_remains_neutral_and_unauthorized(self) -> None:
        self.assertEqual(self.adapter_v6["status"], "PASS")
        self.assertEqual(self.envelope["status"], "BLOCK")
        self.assertEqual(self.envelope["source"]["state"], "OBSERVED")
        self.assertEqual(self.envelope["local_decision"]["status"], "PASS")
        self.assertEqual(
            self.envelope["stages"][1]["state"],
            "CLEAR_WITH_GOVERNANCE_GAPS",
        )
        self.assertEqual(
            self.envelope["stages"][3]["state"], "UNAUTHORIZED"
        )

    def test_exact_tail_block_is_visible_and_overrides_local_clear(self) -> None:
        document, registration, evaluation, context = self._source_bundle(
            coupled=True
        )
        envelope = self._build(
            adapter_v6_document=document,
            registration=registration,
            evaluation=evaluation,
            expected_hash=document["adapter_v6_hash"],
            tail_context=context,
        )
        self.assertEqual(
            envelope["local_decision"]["decision"],
            "BLOCK_DOWNSIDE_TAIL_COUPLING",
        )
        self.assertEqual(
            envelope["local_decision"]["downside_tail_gate_decision"],
            "BLOCK",
        )
        self.assertEqual(envelope["stages"][1]["state"], "BLOCKED")

    def test_exact_adapter_v6_unknown_source_remains_distinct(self) -> None:
        registration, evaluation, context = self.v6_case._tail(
            observations=[]
        )
        document = self.v6_case._evaluate(
            registration=registration,
            evaluation=evaluation,
            tail_context=context,
        )
        envelope = self._build(
            adapter_v6_document=document,
            registration=registration,
            evaluation=evaluation,
            expected_hash=document["adapter_v6_hash"],
            tail_context=context,
        )
        self.assertTrue(envelope["facts"]["adapter_v6_exactly_verified"])
        self.assertFalse(
            envelope["facts"]["joint_local_research_source_known"]
        )
        self.assertEqual(envelope["source"]["state"], "UNKNOWN")
        self.assertEqual(envelope["local_decision"]["status"], "UNKNOWN")

    def test_wrong_expected_adapter_hash_projects_unknown(self) -> None:
        envelope = self._build(expected_hash="f" * 64)
        self.assertEqual(envelope["decision"], "UNKNOWN_SOURCE")
        self.assertFalse(envelope["facts"]["adapter_v6_exactly_verified"])
        self.assertIsNone(envelope["source"]["adapter_v6_hash"])

    def test_resealed_adapter_authority_promotion_projects_unknown(self) -> None:
        altered = copy.deepcopy(self.adapter_v6)
        altered["authority"]["paper_authorized"] = True
        altered = seal_strict_canonical_document(altered, "adapter_v6_hash")
        envelope = self._build(
            adapter_v6_document=altered,
            expected_hash=altered["adapter_v6_hash"],
        )
        self.assertEqual(envelope["decision"], "UNKNOWN_SOURCE")

    def test_verification_context_symbol_splice_projects_unknown(self) -> None:
        context = copy.deepcopy(self.adapter_context)
        context["adapter_v4_verification_context"][
            "weighted_budget_v2_verification_context"
        ]["positions"][0]["symbol"] = "X"
        envelope = self._build(adapter_context=context)
        self.assertEqual(envelope["source"]["state"], "UNKNOWN")
        self.assertFalse(envelope["facts"]["adapter_v6_exactly_verified"])

    def test_exact_verifier_accepts_rebuild_and_rejects_resealed_tamper(
        self,
    ) -> None:
        receipt = self._verify(self.envelope)
        self.assertEqual(receipt["status"], "PASS")
        altered = copy.deepcopy(self.envelope)
        altered["authority"]["current_admission_allowed"] = True
        altered = seal_strict_canonical_document(altered, "envelope_hash")
        receipt = self._verify(altered)
        self.assertEqual(receipt["status"], "BLOCK")

    def test_output_is_summary_only(self) -> None:
        encoded = json.dumps(self.envelope, sort_keys=True)
        for forbidden in (
            '"aligned_observations"',
            '"pair_results"',
            '"positions"',
            '"stratum_by_identity"',
            '"returns"',
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(self.envelope["facts"]["source_documents_embedded"])
        self.assertFalse(
            self.envelope["facts"]["verification_contexts_embedded"]
        )

    def test_untrusted_input_text_is_not_reflected(self) -> None:
        envelope = self._build(
            adapter_v6_document={"secret": "DO-NOT-REFLECT"},
            expected_hash="f" * 64,
        )
        self.assertNotIn("DO-NOT-REFLECT", json.dumps(envelope, sort_keys=True))

    def test_axis_order_is_source_gap_maturity_permission(self) -> None:
        self.assertEqual(self.envelope["axis_order"], list(subject.AXIS_ORDER))
        self.assertEqual(
            [stage["axis"] for stage in self.envelope["stages"]],
            list(subject.AXIS_ORDER),
        )

    def test_risk_reduction_exemption_is_not_presented_as_implemented(
        self,
    ) -> None:
        self.assertFalse(
            self.envelope["policy"][
                "risk_reduction_joint_exemption_implemented"
            ]
        )
        self.assertFalse(
            self.envelope["facts"][
                "risk_reduction_joint_exemption_implemented"
            ]
        )

    def test_dependency_pins_match_current_sources(self) -> None:
        root = Path(__file__).resolve().parents[1]
        paths = {
            root
            / "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_adapter_v6.py": subject.ADAPTER_V6_IMPLEMENTATION_SHA256,
            root
            / "exchange_terminal/services/strict_canonical_json_hash.py": subject.STRICT_CANONICAL_IMPLEMENTATION_SHA256,
        }
        for path, expected in paths.items():
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(), expected
            )

    def test_api_has_no_raw_metric_runtime_route_or_browser_inputs(self) -> None:
        signatures = (
            inspect.signature(
                subject.build_strategy_correlation_cluster_portfolio_risk_adapter_v6_presentation_envelope_v1
            ),
            inspect.signature(
                subject.verify_strategy_correlation_cluster_portfolio_risk_adapter_v6_presentation_envelope_v1
            ),
        )
        for signature in signatures:
            rendered = str(signature).lower()
            for forbidden in (
                "aligned_observations",
                "tail_overlap",
                "p_value",
                "runtime_order",
                "route",
                "browser",
                "selector",
                "mount",
            ):
                self.assertNotIn(forbidden, rendered)

    def test_authority_profitability_and_ui_mount_remain_closed(self) -> None:
        authority = self.envelope["authority"]
        self.assertTrue(authority["research_only"])
        self.assertTrue(authority["presentation_only"])
        self.assertTrue(authority["descriptive_only"])
        self.assertTrue(
            all(
                value is False
                for key, value in authority.items()
                if key
                not in {"research_only", "presentation_only", "descriptive_only"}
            )
        )
        self.assertFalse(self.envelope["facts"]["profitability_proven"])
        self.assertFalse(self.envelope["facts"]["ui_mounted"])
        self.assertNotIn("READY", json.dumps(self.envelope, sort_keys=True))

    def test_projection_is_deterministic_under_deepcopy(self) -> None:
        self.assertEqual(self.envelope, self._build())


if __name__ == "__main__":
    unittest.main()
