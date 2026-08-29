import copy
import itertools
import json
import unittest

from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    evaluate_correlation_cluster_gate_v2,
)
from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_cluster_preregistration,
    build_correlation_matrix_contract,
)
from exchange_terminal.services.strategy_correlation_preregistered_strata import (
    build_strategy_correlation_strata_preregistration,
    evaluate_strategy_correlation_strata_gate,
)
from exchange_terminal.services.strategy_correlation_strata_projection import (
    build_strategy_correlation_strata_public_summary,
    verify_strategy_correlation_strata_public_summary,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    strict_canonical_hash,
)


class StrategyCorrelationStrataProjectionTests(unittest.TestCase):
    def _fixture(self, *, shared_stratum=False, base_blocked=False):
        symbols = ("AAA", "BBB")
        preregistration = build_correlation_cluster_preregistration(
            [
                {"cluster_id": "cluster-aaa", "members": ["AAA"]},
                {"cluster_id": "cluster-bbb", "members": ["BBB"]},
            ]
        )
        matrix = build_correlation_matrix_contract(
            list(symbols),
            {pair: 0.10 for pair in itertools.combinations(symbols, 2)},
        )
        cells = [
            {
                "strategy_id": "strategy-1",
                "variant_id": "variant-1",
                "symbol": symbol,
                "lane": "RAW_EXCESS",
                "gate_status": (
                    "BLOCK" if base_blocked and symbol == "BBB" else "PASS"
                ),
            }
            for symbol in symbols
        ]
        complete_link_gate = evaluate_correlation_cluster_gate_v2(
            preregistration,
            matrix,
            cells,
            strategy_id="strategy-1",
            variant_id="variant-1",
            lane="RAW_EXCESS",
        )
        strata = (
            [
                {
                    "stratum_id": "shared-sector",
                    "cluster_ids": ["cluster-aaa", "cluster-bbb"],
                }
            ]
            if shared_stratum
            else [
                {
                    "stratum_id": "sector-a",
                    "cluster_ids": ["cluster-aaa"],
                },
                {
                    "stratum_id": "sector-b",
                    "cluster_ids": ["cluster-bbb"],
                },
            ]
        )
        registration = build_strategy_correlation_strata_preregistration(
            preregistration,
            [{"dimension_id": "sector", "strata": strata}],
        )
        gate = evaluate_strategy_correlation_strata_gate(
            registration,
            complete_link_gate,
            source_preregistration=preregistration,
        )
        return preregistration, registration, complete_link_gate, gate

    def test_registration_only_is_observed_without_inventing_gate_evidence(self):
        preregistration, registration, _, _ = self._fixture()
        summary = build_strategy_correlation_strata_public_summary(
            registration,
            source_preregistration=preregistration,
        )
        self.assertEqual(summary["source"]["status"], "OBSERVED")
        self.assertEqual(
            summary["source"]["gate_evidence_status"],
            "NOT_SUPPLIED",
        )
        self.assertEqual(
            summary["gap"]["status"],
            "GATE_EVIDENCE_NOT_SUPPLIED",
        )
        self.assertIsNone(summary["gap"]["blocked_dimension_count"])

    def test_passing_gate_projects_independence_without_authority(self):
        preregistration, registration, complete_link_gate, gate = self._fixture()
        summary = build_strategy_correlation_strata_public_summary(
            registration,
            source_preregistration=preregistration,
            source_gate=gate,
            complete_link_gate=complete_link_gate,
        )
        self.assertEqual(
            summary["gap"]["status"],
            "INDEPENDENCE_REQUIREMENTS_OBSERVED",
        )
        self.assertEqual(summary["gap"]["passing_dimension_count"], 1)
        self.assertEqual(summary["gap"]["blocked_dimension_count"], 0)
        self.assertEqual(summary["maturity"]["status"], "CONSUMER_ONLY")
        self.assertEqual(summary["permission"]["status"], "RESEARCH_ONLY")
        self.assertFalse(summary["permission"]["paper_authorized"])
        self.assertFalse(summary["permission"]["live_order_allowed"])

    def test_parent_stratum_block_is_neutral_and_count_only(self):
        preregistration, registration, complete_link_gate, gate = self._fixture(
            shared_stratum=True
        )
        summary = build_strategy_correlation_strata_public_summary(
            registration,
            source_preregistration=preregistration,
            source_gate=gate,
            complete_link_gate=complete_link_gate,
        )
        self.assertEqual(
            summary["gap"]["status"],
            "PARENT_STRATUM_CONCENTRATION_OBSERVED",
        )
        self.assertEqual(summary["gap"]["blocked_dimension_count"], 1)
        serialized = json.dumps(summary, sort_keys=True)
        for secret in (
            "AAA",
            "BBB",
            "cluster-aaa",
            "cluster-bbb",
            registration["registration_hash"],
            gate["gate_hash"],
        ):
            self.assertNotIn(secret, serialized)
        self.assertTrue(
            all(value is False for value in summary["redaction"].values())
        )

    def test_base_complete_link_block_is_distinguished(self):
        preregistration, registration, complete_link_gate, gate = self._fixture(
            base_blocked=True
        )
        summary = build_strategy_correlation_strata_public_summary(
            registration,
            source_preregistration=preregistration,
            source_gate=gate,
            complete_link_gate=complete_link_gate,
        )
        self.assertEqual(
            summary["gap"]["status"],
            "BASE_COMPLETE_LINK_BLOCK_OBSERVED",
        )

    def test_invalid_or_partial_sources_fail_closed_to_unknown(self):
        preregistration, registration, complete_link_gate, gate = self._fixture()
        tampered = copy.deepcopy(registration)
        tampered["cluster_ids"] = ["cluster-aaa"]
        tampered["registration_hash"] = strict_canonical_hash(
            {
                key: value
                for key, value in tampered.items()
                if key != "registration_hash"
            }
        )
        cases = [
            build_strategy_correlation_strata_public_summary(
                tampered,
                source_preregistration=preregistration,
            ),
            build_strategy_correlation_strata_public_summary(
                registration,
                source_preregistration=preregistration,
                source_gate=gate,
            ),
            build_strategy_correlation_strata_public_summary(
                registration,
                source_preregistration=preregistration,
                complete_link_gate=complete_link_gate,
            ),
        ]
        for summary in cases:
            with self.subTest(summary=summary):
                self.assertEqual(summary["source"]["status"], "UNKNOWN")
                self.assertEqual(summary["gap"]["status"], "UNKNOWN")
                self.assertFalse(summary["permission"]["paper_authorized"])
                self.assertFalse(summary["permission"]["live_order_allowed"])

    def test_resealed_authority_escalation_projects_unknown(self):
        preregistration, registration, complete_link_gate, gate = self._fixture()
        tampered = copy.deepcopy(gate)
        tampered["current_admission_allowed"] = True
        tampered["gate_hash"] = strict_canonical_hash(
            {
                key: value
                for key, value in tampered.items()
                if key != "gate_hash"
            }
        )
        summary = build_strategy_correlation_strata_public_summary(
            registration,
            source_preregistration=preregistration,
            source_gate=tampered,
            complete_link_gate=complete_link_gate,
        )
        self.assertEqual(summary["source"]["status"], "UNKNOWN")

    def test_verifier_exactly_rebuilds_public_summary(self):
        preregistration, registration, complete_link_gate, gate = self._fixture()
        summary = build_strategy_correlation_strata_public_summary(
            registration,
            source_preregistration=preregistration,
            source_gate=gate,
            complete_link_gate=complete_link_gate,
        )
        self.assertEqual(
            verify_strategy_correlation_strata_public_summary(
                summary,
                source_registration=registration,
                source_preregistration=preregistration,
                source_gate=gate,
                complete_link_gate=complete_link_gate,
            )["status"],
            "PASS",
        )
        tampered = copy.deepcopy(summary)
        tampered["permission"]["paper_authorized"] = True
        self.assertEqual(
            verify_strategy_correlation_strata_public_summary(
                tampered,
                source_registration=registration,
                source_preregistration=preregistration,
                source_gate=gate,
                complete_link_gate=complete_link_gate,
            )["status"],
            "BLOCK",
        )


if __name__ == "__main__":
    unittest.main()
