from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_projection_v6 as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
import tests.test_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_v6 as candidate_test_support


class PortfolioRiskProjectionV6Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.candidate_case = candidate_test_support.PresentationHttpCandidateV6Tests(
            "test_exact_local_clear_is_known_blocked_without_permission"
        )
        self.candidate_case.setUp()
        self.addCleanup(self.candidate_case.doCleanups)
        self.candidate = copy.deepcopy(self.candidate_case.response)
        self.context = {
            "request_payload": copy.deepcopy(self.candidate_case.request),
            "envelope_verification_context": copy.deepcopy(
                self.candidate_case.context
            ),
        }
        self.projection = self._project()

    def _verify_candidate_boundary(self, *args, **kwargs) -> bool:
        with patch.object(
            subject.candidate_v6,
            "_VERIFY_ENVELOPE",
            side_effect=self.candidate_case._verify_envelope_boundary,
        ):
            return subject.candidate_v6.verify_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v6(
                *args,
                **kwargs,
            )

    def _project(
        self,
        document: dict | None = None,
        context: dict | None = None,
    ) -> dict:
        with patch.object(
            subject,
            "_VERIFY_CANDIDATE",
            side_effect=self._verify_candidate_boundary,
        ):
            return subject.project_strategy_correlation_cluster_portfolio_risk_projection_v6(
                copy.deepcopy(self.candidate if document is None else document),
                presentation_candidate_v6_verification_context=copy.deepcopy(
                    self.context if context is None else context
                ),
            )

    def _verify(self, projection: dict) -> dict:
        with patch.object(
            subject,
            "_VERIFY_CANDIDATE",
            side_effect=self._verify_candidate_boundary,
        ):
            return subject.verify_strategy_correlation_cluster_portfolio_risk_projection_v6(
                copy.deepcopy(projection),
                copy.deepcopy(self.candidate),
                presentation_candidate_v6_verification_context=copy.deepcopy(
                    self.context
                ),
            )

    def _bundle(
        self,
        *,
        coupled: bool = False,
        observations: list[dict[str, object]] | None = None,
    ) -> tuple[dict, dict]:
        request, envelope_context = self.candidate_case._bundle(
            coupled=coupled,
            observations=observations,
        )
        candidate = self.candidate_case._build(request, envelope_context)
        return candidate, {
            "request_payload": request,
            "envelope_verification_context": envelope_context,
        }

    def test_exact_local_clear_projects_blocked_frontend_authority(self) -> None:
        self.assertEqual(self.projection["status"], "BLOCK")
        self.assertEqual(self.projection["source"]["state"], "OBSERVED")
        self.assertEqual(self.projection["local_decision"]["status"], "PASS")
        self.assertEqual(
            self.projection["stages"][3]["state"], "UNAUTHORIZED"
        )
        self.assertTrue(self.projection["facts"]["candidate_v6_exactly_verified"])

    def test_exact_tail_block_remains_visible(self) -> None:
        candidate, context = self._bundle(coupled=True)
        projection = self._project(candidate, context)
        self.assertEqual(
            projection["local_decision"]["decision"],
            "BLOCK_DOWNSIDE_TAIL_COUPLING",
        )
        self.assertEqual(
            projection["local_decision"]["downside_tail_gate_decision"],
            "BLOCK",
        )
        self.assertEqual(projection["stages"][1]["state"], "BLOCKED")

    def test_exact_unknown_joint_source_is_not_unverified_candidate(self) -> None:
        candidate, context = self._bundle(observations=[])
        projection = self._project(candidate, context)
        self.assertEqual(
            projection["decision"],
            "EXACT_HTTP_CANDIDATE_V6_PROJECTED_AUTHORITY_UNCHANGED",
        )
        self.assertEqual(projection["source"]["state"], "UNKNOWN")
        self.assertTrue(projection["facts"]["candidate_v6_exactly_verified"])
        self.assertFalse(
            projection["facts"]["joint_local_research_source_known"]
        )

    def test_context_shape_error_projects_unknown(self) -> None:
        for key in tuple(self.context):
            malformed = copy.deepcopy(self.context)
            malformed.pop(key)
            projection = self._project(context=malformed)
            self.assertEqual(projection["decision"], "UNKNOWN_SOURCE")
        extra = copy.deepcopy(self.context)
        extra["candidate_verified"] = True
        self.assertEqual(self._project(context=extra)["decision"], "UNKNOWN_SOURCE")

    def test_candidate_request_hash_mismatch_projects_unknown(self) -> None:
        context = copy.deepcopy(self.context)
        context["request_payload"][
            "expected_presentation_envelope_hash"
        ] = "f" * 64
        projection = self._project(context=context)
        self.assertEqual(projection["source"]["state"], "UNKNOWN")
        self.assertFalse(projection["facts"]["candidate_v6_exactly_verified"])

    def test_resealed_candidate_authority_promotion_projects_unknown(self) -> None:
        altered = copy.deepcopy(self.candidate)
        altered["authority"]["current_admission_allowed"] = True
        altered = seal_strict_canonical_document(altered, "response_hash")
        projection = self._project(altered)
        self.assertEqual(projection["decision"], "UNKNOWN_SOURCE")

    def test_candidate_verifier_false_and_exception_project_unknown(self) -> None:
        with patch.object(subject, "_VERIFY_CANDIDATE", return_value=False):
            projection = subject.project_strategy_correlation_cluster_portfolio_risk_projection_v6(
                copy.deepcopy(self.candidate),
                presentation_candidate_v6_verification_context=copy.deepcopy(
                    self.context
                ),
            )
        self.assertEqual(projection["decision"], "UNKNOWN_SOURCE")
        with patch.object(
            subject,
            "_VERIFY_CANDIDATE",
            side_effect=RuntimeError("synthetic"),
        ):
            projection = subject.project_strategy_correlation_cluster_portfolio_risk_projection_v6(
                copy.deepcopy(self.candidate),
                presentation_candidate_v6_verification_context=copy.deepcopy(
                    self.context
                ),
            )
        self.assertEqual(projection["decision"], "UNKNOWN_SOURCE")

    def test_untrusted_candidate_text_is_not_reflected(self) -> None:
        projection = self._project({"secret": "DO-NOT-REFLECT"})
        self.assertNotIn(
            "DO-NOT-REFLECT", json.dumps(projection, sort_keys=True)
        )

    def test_projection_is_summary_only(self) -> None:
        encoded = json.dumps(self.projection, sort_keys=True)
        for forbidden in (
            "request_payload",
            "envelope_verification_context",
            "adapter_v6_document",
            "adapter_v5_document",
            "downside_tail_registration",
            "downside_tail_evaluation",
            '"positions"',
            '"aligned_observations"',
            '"returns"',
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(self.projection["facts"]["source_document_embedded"])

    def test_projection_is_deterministic(self) -> None:
        self.assertEqual(self.projection, self._project())

    def test_exact_verifier_accepts_rebuild_and_rejects_tamper(self) -> None:
        receipt = self._verify(self.projection)
        self.assertEqual(receipt["status"], "PASS")
        altered = copy.deepcopy(self.projection)
        altered["authority"]["presentation_mount_allowed"] = True
        altered = seal_strict_canonical_document(altered, "projection_hash")
        receipt = self._verify(altered)
        self.assertEqual(receipt["status"], "BLOCK")

    def test_dependency_pins_match_current_sources(self) -> None:
        root = Path(__file__).resolve().parents[1]
        paths = {
            root
            / "exchange_terminal/interfaces/http/strategy_correlation_cluster_portfolio_risk_presentation_candidate_v6.py": subject.CANDIDATE_V6_IMPLEMENTATION_SHA256,
            root
            / "exchange_terminal/services/strict_canonical_json_hash.py": subject.STRICT_CANONICAL_IMPLEMENTATION_SHA256,
        }
        for path, expected in paths.items():
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(), expected
            )

    def test_api_has_no_runtime_route_browser_or_precomputed_inputs(self) -> None:
        signatures = (
            inspect.signature(
                subject.project_strategy_correlation_cluster_portfolio_risk_projection_v6
            ),
            inspect.signature(
                subject.verify_strategy_correlation_cluster_portfolio_risk_projection_v6
            ),
        )
        for signature in signatures:
            rendered = str(signature).lower()
            for forbidden in (
                "runtime",
                "route",
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

    def test_axes_and_lifecycle_wording_are_neutral(self) -> None:
        self.assertEqual(self.projection["axis_order"], list(subject.AXIS_ORDER))
        self.assertEqual(
            [stage["axis"] for stage in self.projection["stages"]],
            list(subject.AXIS_ORDER),
        )
        encoded = json.dumps(self.projection, sort_keys=True)
        self.assertNotIn("HTTP_CANDIDATE_V6_NOT_IMPLEMENTED", encoded)
        self.assertNotIn("READY", encoded)

    def test_authority_profitability_and_ui_mount_remain_closed(self) -> None:
        authority = self.projection["authority"]
        self.assertTrue(authority["research_only"])
        self.assertTrue(authority["presentation_only"])
        self.assertTrue(authority["frontend_projection_only"])
        self.assertTrue(
            all(
                value is False
                for key, value in authority.items()
                if key
                not in {
                    "research_only",
                    "presentation_only",
                    "frontend_projection_only",
                }
            )
        )
        self.assertFalse(self.projection["facts"]["profitability_proven"])
        self.assertFalse(self.projection["facts"]["ui_mounted"])


if __name__ == "__main__":
    unittest.main()
