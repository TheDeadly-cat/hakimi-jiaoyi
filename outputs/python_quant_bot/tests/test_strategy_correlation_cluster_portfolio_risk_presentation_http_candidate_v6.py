from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.interfaces.http import (
    strategy_correlation_cluster_portfolio_risk_presentation_candidate_v6 as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
import tests.test_strategy_correlation_cluster_portfolio_risk_adapter_v6_presentation_envelope_v1 as envelope_test_support


class PresentationHttpCandidateV6Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.envelope_case = (
            envelope_test_support.AdapterV6PresentationEnvelopeV1Tests(
                "test_exact_clear_local_gate_remains_neutral_and_unauthorized"
            )
        )
        self.envelope_case.setUp()
        self.addCleanup(self.envelope_case.doCleanups)
        self.envelope = copy.deepcopy(self.envelope_case.envelope)
        self.context = self._context(
            self.envelope_case.adapter_v6,
            self.envelope_case.registration,
            self.envelope_case.evaluation,
            self.envelope_case.tail_context,
        )
        self.request = self._request(self.envelope)
        self.response = self._build()

    def _context(
        self,
        adapter_v6_document: dict,
        registration: dict,
        evaluation: dict,
        tail_context: dict,
    ) -> dict:
        return {
            "adapter_v6_document": copy.deepcopy(adapter_v6_document),
            "adapter_v5_document": copy.deepcopy(
                self.envelope_case.adapter_v5
            ),
            "downside_tail_registration": copy.deepcopy(registration),
            "downside_tail_evaluation": copy.deepcopy(evaluation),
            "expected_adapter_v6_hash": adapter_v6_document[
                "adapter_v6_hash"
            ],
            "adapter_v5_verification_context": copy.deepcopy(
                self.envelope_case.adapter_context
            ),
            "downside_tail_verification_context": copy.deepcopy(
                tail_context
            ),
        }

    @staticmethod
    def _request(envelope: dict) -> dict:
        return {
            "schema_version": subject.REQUEST_SCHEMA_VERSION,
            "adapter_v6_presentation_envelope_v1_document": copy.deepcopy(
                envelope
            ),
            "expected_presentation_envelope_hash": envelope[
                "envelope_hash"
            ],
        }

    def _verify_envelope_boundary(self, *args, **kwargs) -> dict:
        with patch.object(
            subject.envelope_v1.adapter_v6,
            "verify_strategy_correlation_cluster_portfolio_risk_adapter_v6",
            side_effect=(
                self.envelope_case._verify_adapter_v6_boundary
            ),
        ):
            return subject.envelope_v1.verify_strategy_correlation_cluster_portfolio_risk_adapter_v6_presentation_envelope_v1(
                *args,
                **kwargs,
            )

    def _build(
        self,
        request: dict | None = None,
        context: dict | None = None,
    ) -> dict:
        with patch.object(
            subject,
            "_VERIFY_ENVELOPE",
            side_effect=self._verify_envelope_boundary,
        ):
            return subject.build_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v6(
                copy.deepcopy(self.request if request is None else request),
                envelope_verification_context=copy.deepcopy(
                    self.context if context is None else context
                ),
            )

    def _verify(self, document: dict) -> bool:
        with patch.object(
            subject,
            "_VERIFY_ENVELOPE",
            side_effect=self._verify_envelope_boundary,
        ):
            return subject.verify_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v6(
                copy.deepcopy(document),
                copy.deepcopy(self.request),
                envelope_verification_context=copy.deepcopy(self.context),
            )

    def _bundle(
        self,
        *,
        coupled: bool = False,
        observations: list[dict[str, object]] | None = None,
    ) -> tuple[dict, dict]:
        registration, evaluation, tail_context = (
            self.envelope_case.v6_case._tail(
                coupled=coupled,
                observations=observations,
            )
        )
        adapter_v6_document = self.envelope_case.v6_case._evaluate(
            registration=registration,
            evaluation=evaluation,
            tail_context=tail_context,
        )
        envelope = self.envelope_case._build(
            adapter_v6_document=adapter_v6_document,
            registration=registration,
            evaluation=evaluation,
            expected_hash=adapter_v6_document["adapter_v6_hash"],
            tail_context=tail_context,
        )
        return self._request(envelope), self._context(
            adapter_v6_document,
            registration,
            evaluation,
            tail_context,
        )

    def test_exact_local_clear_is_known_blocked_without_permission(self) -> None:
        self.assertEqual(self.response["state"], "KNOWN_BLOCKED")
        self.assertEqual(
            self.response["interface_status"], "UNREGISTERED_CANDIDATE"
        )
        self.assertEqual(
            self.response["payload"]["summary"]["local_status"], "PASS"
        )
        self.assertEqual(
            self.response["payload"]["stages"][3]["state"],
            "UNAUTHORIZED",
        )
        self.assertIn(
            "HTTP_CANDIDATE_V6_UNREGISTERED", self.response["blockers"]
        )

    def test_exact_tail_block_remains_visible(self) -> None:
        request, context = self._bundle(coupled=True)
        response = self._build(request, context)
        self.assertEqual(response["state"], "KNOWN_BLOCKED")
        self.assertEqual(
            response["payload"]["summary"]["local_decision"],
            "BLOCK_DOWNSIDE_TAIL_COUPLING",
        )
        self.assertEqual(response["payload"]["stages"][1]["state"], "BLOCKED")
        self.assertIn("LOCAL_RESEARCH_GATE_BLOCKED", response["blockers"])

    def test_exact_unknown_envelope_is_known_fail_closed(self) -> None:
        request, context = self._bundle(observations=[])
        response = self._build(request, context)
        self.assertEqual(response["state"], "KNOWN_BLOCKED")
        self.assertEqual(
            response["payload"]["summary"]["source_state"], "UNKNOWN"
        )
        self.assertFalse(
            response["facts"]["joint_local_research_source_known"]
        )
        self.assertIn(
            "JOINT_LOCAL_RESEARCH_SOURCE_UNKNOWN", response["blockers"]
        )

    def test_request_contract_is_exact_and_fail_closed(self) -> None:
        for key in tuple(self.request):
            malformed = copy.deepcopy(self.request)
            malformed.pop(key)
            self.assertEqual(self._build(malformed)["state"], "UNKNOWN")
        extra = copy.deepcopy(self.request)
        extra["local_status"] = "PASS"
        self.assertEqual(self._build(extra)["state"], "UNKNOWN")
        alias = copy.deepcopy(self.request)
        alias["adapter_v6_presentation_envelope_v1_document"] = "PASS"
        self.assertEqual(self._build(alias)["state"], "UNKNOWN")

    def test_verification_context_is_exact_and_fail_closed(self) -> None:
        for key in tuple(self.context):
            malformed = copy.deepcopy(self.context)
            malformed.pop(key)
            self.assertEqual(self._build(context=malformed)["state"], "UNKNOWN")
        extra = copy.deepcopy(self.context)
        extra["source_verified"] = True
        self.assertEqual(self._build(context=extra)["state"], "UNKNOWN")

    def test_expected_envelope_hash_mismatch_projects_unknown(self) -> None:
        request = copy.deepcopy(self.request)
        request["expected_presentation_envelope_hash"] = "f" * 64
        response = self._build(request)
        self.assertEqual(response["state"], "UNKNOWN")
        self.assertEqual(response["payload"], None)

    def test_resealed_envelope_authority_promotion_projects_unknown(self) -> None:
        altered = copy.deepcopy(self.envelope)
        altered["authority"]["current_admission_allowed"] = True
        altered = seal_strict_canonical_document(altered, "envelope_hash")
        request = self._request(altered)
        response = self._build(request)
        self.assertEqual(response["state"], "UNKNOWN")

    def test_verifier_leak_and_exception_fail_closed(self) -> None:
        receipt = self._verify_envelope_boundary(
            self.envelope,
            self.context["adapter_v6_document"],
            self.context["adapter_v5_document"],
            self.context["downside_tail_registration"],
            self.context["downside_tail_evaluation"],
            expected_adapter_v6_hash=self.context[
                "expected_adapter_v6_hash"
            ],
            adapter_v5_verification_context=self.context[
                "adapter_v5_verification_context"
            ],
            downside_tail_verification_context=self.context[
                "downside_tail_verification_context"
            ],
        )
        leaked = copy.deepcopy(receipt)
        leaked["current_admission_allowed"] = True
        leaked = seal_strict_canonical_document(leaked, "verification_hash")
        with patch.object(subject, "_VERIFY_ENVELOPE", return_value=leaked):
            response = subject.build_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v6(
                copy.deepcopy(self.request),
                envelope_verification_context=copy.deepcopy(self.context),
            )
        self.assertEqual(response["state"], "UNKNOWN")
        with patch.object(
            subject,
            "_VERIFY_ENVELOPE",
            side_effect=RuntimeError("synthetic"),
        ):
            response = subject.build_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v6(
                copy.deepcopy(self.request),
                envelope_verification_context=copy.deepcopy(self.context),
            )
        self.assertEqual(response["state"], "UNKNOWN")

    def test_response_does_not_embed_requests_contexts_or_raw_rows(self) -> None:
        encoded = json.dumps(self.response, sort_keys=True)
        for forbidden in (
            "adapter_v6_presentation_envelope_v1_document",
            "adapter_v6_document",
            "adapter_v5_document",
            "downside_tail_registration",
            "downside_tail_evaluation",
            "adapter_v5_verification_context",
            "downside_tail_verification_context",
            '"aligned_observations"',
            '"positions"',
            '"returns"',
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(
            self.response["lineage"]["request_documents_embedded"]
        )

    def test_build_is_deterministic_and_does_not_mutate_inputs(self) -> None:
        request = copy.deepcopy(self.request)
        context = copy.deepcopy(self.context)
        snapshot = copy.deepcopy((request, context))
        first = self._build(request, context)
        second = self._build(request, context)
        self.assertEqual(first, second)
        self.assertEqual((request, context), snapshot)

    def test_transport_and_authority_remain_locked(self) -> None:
        self.assertFalse(self.response["transport"]["registered"])
        self.assertFalse(self.response["transport"]["externally_callable"])
        self.assertIsNone(self.response["transport"]["method"])
        self.assertIsNone(self.response["transport"]["route"])
        self.assertTrue(self.response["authority"]["descriptive_only"])
        self.assertTrue(
            all(
                value is False
                for key, value in self.response["authority"].items()
                if key != "descriptive_only"
            )
        )

    def test_exact_verifier_accepts_rebuild_and_rejects_tamper(self) -> None:
        self.assertTrue(self._verify(self.response))
        altered = copy.deepcopy(self.response)
        altered["payload"]["authority"]["paper_authorized"] = True
        altered = seal_strict_canonical_document(altered, "response_hash")
        self.assertFalse(self._verify(altered))

    def test_dependency_pins_match_current_sources(self) -> None:
        root = Path(__file__).resolve().parents[1]
        paths = {
            root
            / "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_adapter_v6_presentation_envelope_v1.py": subject.ENVELOPE_V1_IMPLEMENTATION_SHA256,
            root
            / "exchange_terminal/services/strict_canonical_json_hash.py": subject.STRICT_CANONICAL_IMPLEMENTATION_SHA256,
        }
        for path, expected in paths.items():
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(), expected
            )

    def test_api_has_no_route_runtime_browser_or_precomputed_inputs(self) -> None:
        signatures = (
            inspect.signature(
                subject.build_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v6
            ),
            inspect.signature(
                subject.verify_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v6
            ),
        )
        for signature in signatures:
            rendered = str(signature).lower()
            for forbidden in (
                "route",
                "runtime",
                "browser",
                "cache",
                "order",
                "paper",
                "live",
                "aligned_observations",
                "tail_overlap",
                "p_value",
                "local_status",
            ):
                self.assertNotIn(forbidden, rendered)

    def test_neutral_axes_replace_not_implemented_lifecycle_gap(self) -> None:
        payload = self.response["payload"]
        self.assertEqual(payload["axis_order"], list(subject.AXIS_ORDER))
        self.assertEqual(
            [stage["axis"] for stage in payload["stages"]],
            list(subject.AXIS_ORDER),
        )
        encoded = json.dumps(self.response, sort_keys=True)
        self.assertNotIn("HTTP_CANDIDATE_V6_NOT_IMPLEMENTED", encoded)
        self.assertNotIn("READY", encoded)
        self.assertFalse(self.response["facts"]["profitability_proven"])


if __name__ == "__main__":
    unittest.main()
