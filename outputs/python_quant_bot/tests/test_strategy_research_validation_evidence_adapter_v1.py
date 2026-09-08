from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from _canonical_source import activate_canonical_source

activate_canonical_source()

from exchange_terminal.application.strategy_research_validation_evidence_adapter_v1 import (
    StrategyResearchValidationEvidenceAdapterError,
    build_validation_evidence_from_formal_search_lineage,
)
from exchange_terminal.services.strategy_research_search_lineage import (
    build_strategy_research_search_lineage,
    build_strategy_research_search_lineage_v2,
)
from hakimi_research.validation_evidence import verify_validation_evidence
from test_validation_evidence_report_v1 import REPORT, _components, _distribution_evidence


SEARCH_FAMILY_ID = "synthetic-formal-search-family-v1"


def _prior_registration() -> dict[str, object]:
    return {
        "registration_id": "prior-registration-v1",
        "protocol_hash": "a" * 64,
        "registered_event_hash": "b" * 64,
        "search_family_id": SEARCH_FAMILY_ID,
        "report_schema_version": 16,
        "lineage_mode": "BOUND",
        "current_trial_count": 3,
        "cumulative_trial_count": 3,
    }


def _lineage(*, prior: list[dict[str, object]] | None = None) -> dict[str, object]:
    return build_strategy_research_search_lineage_v2(
        search_family_id=SEARCH_FAMILY_ID,
        prior_registrations=[] if prior is None else prior,
        current_trial_count=3,
    )


def _adapt(
    *,
    lineage: dict[str, object] | None = None,
    prior: list[dict[str, object]] | None = None,
    mutate_components=None,
) -> dict[str, object]:
    expected_prior = [] if prior is None else prior
    walk, stability, multiplicity, regimes = _components()
    if mutate_components is not None:
        mutate_components(walk, stability, multiplicity, regimes)
    return build_validation_evidence_from_formal_search_lineage(
        REPORT,
        experiment_id="synthetic-formal-adapter-v1",
        formal_search_lineage=_lineage(prior=expected_prior) if lineage is None else lineage,
        distribution_evidence=_distribution_evidence(),
        expected_search_family_id=SEARCH_FAMILY_ID,
        expected_current_trial_count=3,
        expected_prior_registrations=expected_prior,
        walk_forward=walk,
        parameter_stability=stability,
        multiple_testing=multiplicity,
        market_regimes=regimes,
    )


class StrategyResearchValidationEvidenceAdapterV1Tests(unittest.TestCase):
    def test_verified_genesis_lineage_is_digest_bound_to_concrete_trial_ledger(self) -> None:
        evidence = _adapt()
        binding = evidence["formal_search_lineage"]
        self.assertEqual(binding["current_trial_count"], 3)
        self.assertEqual(binding["cumulative_trial_count"], 3)
        self.assertEqual(binding["prior_registration_count"], 0)
        self.assertEqual(len(binding["artifact_sha256"]), 64)
        summary = verify_validation_evidence(evidence, REPORT)
        self.assertEqual(summary["formal_search_lineage"]["state"], "OBSERVED")
        self.assertEqual(summary["permission"], "RESEARCH_ONLY")
        self.assertFalse(any(evidence["authority"].values()))

    def test_verified_prior_chain_preserves_cumulative_trial_count(self) -> None:
        prior = [_prior_registration()]
        evidence = _adapt(prior=prior)
        binding = evidence["formal_search_lineage"]
        self.assertEqual(binding["prior_registration_count"], 1)
        self.assertEqual(binding["current_trial_count"], 3)
        self.assertEqual(binding["cumulative_trial_count"], 6)

    def test_same_formal_artifact_produces_same_binding_and_evidence_digest(self) -> None:
        lineage = _lineage()
        first = _adapt(lineage=lineage)
        second = _adapt(lineage=deepcopy(lineage))
        self.assertEqual(first["formal_search_lineage"], second["formal_search_lineage"])
        self.assertEqual(first["evidence_sha256"], second["evidence_sha256"])

    def test_count_only_producer_cannot_cover_a_shorter_concrete_trial_ledger(self) -> None:
        def mutate(_walk, _stability, multiplicity, _regimes):
            multiplicity["preregistered_trial_ids"].pop()
            multiplicity["trial_outcomes"].pop()

        with self.assertRaisesRegex(
            StrategyResearchValidationEvidenceAdapterError,
            "count must equal the verified formal current_trial_count",
        ):
            _adapt(mutate_components=mutate)

    def test_tampered_formal_lineage_is_rejected_by_legacy_verifier(self) -> None:
        lineage = _lineage()
        lineage["cumulative_trial_count"] = 300
        with self.assertRaisesRegex(
            StrategyResearchValidationEvidenceAdapterError,
            "formal verification blocked",
        ):
            _adapt(lineage=lineage)

    def test_v1_lineage_is_not_aliased_as_v2_producer(self) -> None:
        lineage = build_strategy_research_search_lineage(
            search_family_id=SEARCH_FAMILY_ID,
            prior_registrations=[],
            current_trial_count=3,
        )
        with self.assertRaisesRegex(
            StrategyResearchValidationEvidenceAdapterError,
            "registered v2 lineage schema",
        ):
            _adapt(lineage=lineage)

    def test_exact_str_subclass_is_rejected_before_legacy_verification(self) -> None:
        class EvilStr(str):
            pass

        walk, stability, multiplicity, regimes = _components()
        with self.assertRaisesRegex(
            StrategyResearchValidationEvidenceAdapterError,
            "expected_search_family_id",
        ):
            build_validation_evidence_from_formal_search_lineage(
                REPORT,
                experiment_id="synthetic-formal-adapter-v1",
                formal_search_lineage=_lineage(),
                distribution_evidence=_distribution_evidence(),
                expected_search_family_id=EvilStr(SEARCH_FAMILY_ID),
                expected_current_trial_count=3,
                expected_prior_registrations=[],
                walk_forward=walk,
                parameter_stability=stability,
                multiple_testing=multiplicity,
                market_regimes=regimes,
            )


if __name__ == "__main__":
    unittest.main()
