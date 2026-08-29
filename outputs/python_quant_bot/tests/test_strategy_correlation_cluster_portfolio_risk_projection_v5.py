from __future__ import annotations

import copy
import hashlib
import inspect
import json
import pathlib
import unittest
from unittest import mock

import exchange_terminal.interfaces.http.strategy_correlation_cluster_portfolio_risk_presentation_candidate_v5 as candidate_source
import exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_projection_v5 as subject
import tests.test_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_v5 as candidate_test_support
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


class PortfolioRiskProjectionV5Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.candidate_case = candidate_test_support.PresentationHttpCandidateV5Tests(
            "test_valid_composition_projects_known_blocked_candidate"
        )
        self.candidate_case.setUp()
        self.addCleanup(self.candidate_case.doCleanups)
        self.candidate_document = self.candidate_case._build()
        self.context = {
            "request_payload": copy.deepcopy(self.candidate_case.request),
            "v4_verification_context": copy.deepcopy(
                self.candidate_case.v4_case.context
            ),
            "adapter_v5_verification_context": copy.deepcopy(
                self.candidate_case.adapter_context
            ),
        }
        self.projection = self._project()

    def _project(
        self, document: dict | None = None, context: dict | None = None
    ) -> dict:
        return subject.project_strategy_correlation_cluster_portfolio_risk_projection_v5(
            copy.deepcopy(
                self.candidate_document if document is None else document
            ),
            presentation_candidate_v5_verification_context=copy.deepcopy(
                self.context if context is None else context
            ),
        )

    def _verify(self, projection: dict) -> dict:
        return subject.verify_strategy_correlation_cluster_portfolio_risk_projection_v5(
            copy.deepcopy(projection),
            copy.deepcopy(self.candidate_document),
            presentation_candidate_v5_verification_context=copy.deepcopy(
                self.context
            ),
        )

    def _blocked_candidate(self) -> tuple[dict, dict]:
        adapter_document, adapter_context = self.candidate_case._adapter_bundle(
            adapter_status="BLOCK"
        )
        request = copy.deepcopy(self.candidate_case.request)
        request["portfolio_risk_adapter_v5_document"] = adapter_document
        document = self.candidate_case._build(
            request=request, adapter_context=adapter_context
        )
        context = {
            "request_payload": request,
            "v4_verification_context": copy.deepcopy(
                self.candidate_case.v4_case.context
            ),
            "adapter_v5_verification_context": adapter_context,
        }
        return document, context

    def test_exact_candidate_projects_known_blocked_summary(self) -> None:
        self.assertEqual(self.projection["status"], "BLOCK")
        self.assertEqual(
            self.projection["decision"],
            "EXACT_HTTP_CANDIDATE_V5_PROJECTED_KNOWN_BLOCKED_AUTHORITY_UNCHANGED",
        )
        self.assertTrue(self.projection["source"]["candidate_v5_exactly_verified"])
        self.assertEqual(self.projection["source"]["candidate_state"], "KNOWN_BLOCKED")
        self.assertTrue(self._verify(self.projection)["projection_exactly_verified"])

    def test_adapter_block_is_preserved_as_joint_risk_gap(self) -> None:
        document, context = self._blocked_candidate()
        projection = self._project(document, context)
        self.assertEqual(projection["status"], "BLOCK")
        self.assertEqual(projection["local_decision"]["status"], "BLOCK")
        self.assertFalse(projection["local_decision"]["joint_risk_gate_passed"])
        self.assertEqual(
            projection["joint_risk"]["assessment"],
            "LOCAL_JOINT_RESEARCH_GATE_BLOCKED",
        )
        self.assertEqual(projection["stages"][1]["state"], "PRESENT")
        self.assertEqual(projection["stages"][3]["state"], "UNAUTHORIZED")

    def test_projection_uses_neutral_four_stage_order(self) -> None:
        self.assertEqual(
            [stage["key"] for stage in self.projection["stages"]],
            ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
        )
        self.assertEqual(self.projection["stages"][0]["state"], "VERIFIED")
        self.assertEqual(self.projection["stages"][3]["state"], "UNAUTHORIZED")

    def test_projection_preserves_calibrated_gap_counts_and_hash_lineage(self) -> None:
        summary = self.candidate_document["payload"]["summary"]
        self.assertEqual(
            self.projection["gaps"]["remaining_blocker_count"],
            summary["remaining_blocker_count"],
        )
        self.assertEqual(
            self.projection["gaps"]["remaining_blockers"],
            summary["remaining_blockers"],
        )
        self.assertEqual(
            self.projection["source"]["candidate_v5_response_hash"],
            self.candidate_document["response_hash"],
        )
        self.assertEqual(
            self.projection["source"]["portfolio_risk_adapter_v5_hash"],
            self.candidate_document["payload"]["source"]["joint_portfolio_risk"][
                "adapter_v5_hash"
            ],
        )

    def test_context_missing_extra_and_scalar_alias_fail_closed(self) -> None:
        for key in tuple(self.context):
            malformed = copy.deepcopy(self.context)
            malformed.pop(key)
            self.assertEqual(self._project(context=malformed)["decision"], "UNKNOWN_SOURCE")
        extra = copy.deepcopy(self.context)
        extra["candidate_verified"] = True
        self.assertEqual(self._project(context=extra)["decision"], "UNKNOWN_SOURCE")
        for alias in (True, False, "PASS", 1):
            self.assertEqual(
                subject.project_strategy_correlation_cluster_portfolio_risk_projection_v5(
                    copy.deepcopy(self.candidate_document),
                    presentation_candidate_v5_verification_context=alias,
                )["decision"],
                "UNKNOWN_SOURCE",
            )

    def test_resealed_source_fact_and_authority_promotions_project_unknown(self) -> None:
        fact_promoted = copy.deepcopy(self.candidate_document)
        fact_promoted["facts"]["runtime_mutations_performed"] = True
        fact_promoted = seal_strict_canonical_document(fact_promoted, "response_hash")
        self.assertEqual(self._project(fact_promoted)["decision"], "UNKNOWN_SOURCE")

        authority_promoted = copy.deepcopy(self.candidate_document)
        authority_promoted["authority"]["presentation_mount_allowed"] = True
        authority_promoted = seal_strict_canonical_document(
            authority_promoted, "response_hash"
        )
        with mock.patch.object(subject, "_VERIFY_CANDIDATE_V5", return_value=True):
            self.assertEqual(
                self._project(authority_promoted)["decision"], "UNKNOWN_SOURCE"
            )

    def test_verifier_false_non_bool_and_exception_fail_closed(self) -> None:
        for value in (False, 1, "PASS", None):
            with mock.patch.object(subject, "_VERIFY_CANDIDATE_V5", return_value=value):
                self.assertEqual(self._project()["decision"], "UNKNOWN_SOURCE")
        with mock.patch.object(
            subject, "_VERIFY_CANDIDATE_V5", side_effect=RuntimeError("x")
        ):
            self.assertEqual(self._project()["decision"], "UNKNOWN_SOURCE")

    def test_projection_is_summary_only_and_does_not_echo_inputs(self) -> None:
        def keys(value: object) -> set[str]:
            if isinstance(value, dict):
                found = set(value)
                for item in value.values():
                    found.update(keys(item))
                return found
            if isinstance(value, list):
                found: set[str] = set()
                for item in value:
                    found.update(keys(item))
                return found
            return set()

        forbidden = {
            "request_payload",
            "v4_verification_context",
            "adapter_v5_verification_context",
            "portfolio_risk_adapter_v5_document",
            "adapter_v4_document",
            "stability_gate_document",
            "positions",
            "correlation_matrix",
        }
        self.assertTrue(forbidden.isdisjoint(keys(self.projection)))
        self.assertFalse(self.projection["facts"]["source_document_embedded"])
        self.assertFalse(self.projection["facts"]["verification_context_embedded"])

    def test_projection_is_deterministic_and_does_not_mutate_inputs(self) -> None:
        document = copy.deepcopy(self.candidate_document)
        context = copy.deepcopy(self.context)
        snapshot = copy.deepcopy((document, context))
        self.assertEqual(self._project(document, context), self._project(document, context))
        self.assertEqual((document, context), snapshot)

    def test_exact_verifier_rejects_resealed_stage_and_authority_tamper(self) -> None:
        self.assertEqual(self._verify(self.projection)["status"], "PASS")
        for path in (("stages", 1, "state"), ("authority", "paper_authorized")):
            tampered = copy.deepcopy(self.projection)
            if path[0] == "stages":
                tampered[path[0]][path[1]][path[2]] = "NONE"
            else:
                tampered[path[0]][path[1]] = True
            tampered = seal_strict_canonical_document(tampered, "projection_hash")
            self.assertEqual(self._verify(tampered)["status"], "BLOCK")

    def test_projection_authority_profitability_runtime_and_ui_remain_locked(self) -> None:
        self.assertTrue(self.projection["authority"]["research_only"])
        self.assertTrue(self.projection["authority"]["presentation_only"])
        for key, value in self.projection["authority"].items():
            if key not in {"research_only", "presentation_only"}:
                self.assertFalse(value)
        self.assertFalse(self.projection["facts"]["profitability_proven"])
        self.assertFalse(self.projection["facts"]["runtime_consumer_bound"])
        self.assertFalse(self.projection["facts"]["ui_mounted"])

    def test_dependency_pins_match_current_source_files(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        paths = {
            subject.CANDIDATE_V5_IMPLEMENTATION_SHA256: pathlib.Path(
                candidate_source.__file__
            ),
            subject.STRICT_CANONICAL_IMPLEMENTATION_SHA256: (
                root / "exchange_terminal/services/strict_canonical_json_hash.py"
            ),
        }
        for expected, path in paths.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)

    def test_api_has_no_runtime_route_dom_browser_or_precomputed_inputs(self) -> None:
        signatures = (
            inspect.signature(
                subject.project_strategy_correlation_cluster_portfolio_risk_projection_v5
            ),
            inspect.signature(
                subject.verify_strategy_correlation_cluster_portfolio_risk_projection_v5
            ),
        )
        forbidden = (
            "runtime",
            "route",
            "dom",
            "browser",
            "selector",
            "mount",
            "paper",
            "live",
            "joint_risk_gate_passed",
        )
        for signature in signatures:
            rendered = str(signature).lower()
            for token in forbidden:
                self.assertNotIn(token, rendered)

    def test_no_ready_or_profitability_claim(self) -> None:
        serialized = json.dumps(self.projection, sort_keys=True)
        self.assertNotIn("READY", serialized)
        self.assertFalse(self.projection["facts"]["profitability_proven"])
        self.assertEqual(self.projection["stages"][3]["state"], "UNAUTHORIZED")


if __name__ == "__main__":
    unittest.main()
