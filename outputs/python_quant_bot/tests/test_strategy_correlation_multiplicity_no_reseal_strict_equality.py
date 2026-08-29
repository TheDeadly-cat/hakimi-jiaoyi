"""Type-strict replay contracts for multiplicity audit and registration."""

from copy import deepcopy
from datetime import date, timedelta
import random
import unittest
from unittest.mock import patch

from exchange_terminal.services.canonical_json_hash import canonical_hash
from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_cluster_preregistration,
)
from exchange_terminal.services import strategy_correlation_multiplicity_audit as audit
from exchange_terminal.services import (
    strategy_correlation_multiplicity_registration as registration,
)
from exchange_terminal.services.strategy_correlation_protocol_binding import (
    build_strategy_correlation_protocol_registration_v2,
)
from exchange_terminal.services import strategy_correlation_uncertainty_audit as uncertainty


def _boolean_paths(value, path=()):
    if type(value) is bool:
        yield path
    elif type(value) is dict:
        for key, child in value.items():
            yield from _boolean_paths(child, path + (key,))
    elif type(value) is list:
        for index, child in enumerate(value):
            yield from _boolean_paths(child, path + (index,))


def _attack(document, path, *, hash_field, reseal):
    candidate = deepcopy(document)
    parent = candidate
    for part in path[:-1]:
        parent = parent[part]
    parent[path[-1]] = int(parent[path[-1]])
    if reseal:
        candidate[hash_field] = canonical_hash({
            key: value
            for key, value in candidate.items()
            if key != hash_field
        })
    return candidate


class StrategyCorrelationMultiplicityNoResealStrictEqualityTests(
    unittest.TestCase
):
    @staticmethod
    def _normal(seed):
        generator = random.Random(seed)
        return [generator.gauss(0.0, 1.0) for _ in range(60)]

    @staticmethod
    def _price_rows(signal):
        rows = []
        price = 100.0
        start = date(2026, 1, 1)
        rows.append({"date": start.isoformat(), "close": price, "complete": True})
        for index, value in enumerate(signal, start=1):
            price *= 1.0 + value * 0.005
            rows.append({
                "date": (start + timedelta(days=index)).isoformat(),
                "close": price,
                "complete": True,
            })
        return rows

    def _chain(self):
        preregistration = build_correlation_cluster_preregistration([
            {"cluster_id": "equity-tech", "members": ["AAPL", "MSFT"]},
            {"cluster_id": "defensive", "members": ["GLD", "TLT"]},
            {"cluster_id": "crypto", "members": ["BTC-USDT"]},
        ])
        protocol_registration = (
            build_strategy_correlation_protocol_registration_v2(
                preregistration,
                cutoff_date="2026-03-02",
                selection_alignment_input_hash="a" * 64,
                evaluations=[
                    {
                        "strategy_id": "dual_ma",
                        "variant_id": "fixed-v1",
                        "lane": "RAW_EXCESS",
                    },
                    {
                        "strategy_id": "dual_ma",
                        "variant_id": "fixed-v1",
                        "lane": "RISK_ADJUSTED",
                    },
                ],
            )
        )
        family_registration = (
            registration
            .build_strategy_correlation_multiplicity_family_registration(
                protocol_registration
            )
        )
        symbols = list(preregistration["symbols"])
        series = {
            symbol: self._normal(index + 1)
            for index, symbol in enumerate(symbols)
        }
        replay = {
            "schema_version": "strategy-correlation-matrix-replay-v1",
            "status": "PASS",
            "replay_hash": "r" * 64,
            "preregistration": deepcopy(preregistration),
            "completed_price_input": {
                "datasets": [
                    {
                        "symbol": symbol,
                        "price_rows": self._price_rows(series[symbol]),
                    }
                    for symbol in symbols
                ],
            },
        }
        uncertainty_audit = uncertainty.build_strategy_correlation_uncertainty_audit(
            replay
        )
        multiplicity_audit = audit.build_strategy_correlation_multiplicity_audit(
            uncertainty_audit
        )
        binding_assessment = (
            registration.assess_strategy_correlation_multiplicity_binding(
                family_registration,
                multiplicity_audit,
            )
        )
        return family_registration, multiplicity_audit, binding_assessment

    def test_actual_upstream_chain_blocks_all_bool_int_aliases(self):
        replay_verification = {"status": "PASS", "blockers": []}
        with patch.object(
            uncertainty,
            "verify_correlation_matrix_replay",
            return_value=replay_verification,
        ):
            family_registration, multiplicity_audit, binding_assessment = (
                self._chain()
            )
            cases = [
                (
                    "multiplicity_audit",
                    multiplicity_audit,
                    "audit_hash",
                    audit.verify_strategy_correlation_multiplicity_audit,
                    350,
                ),
                (
                    "family_registration",
                    family_registration,
                    "family_registration_hash",
                    registration.verify_strategy_correlation_multiplicity_family_registration,
                    32,
                ),
                (
                    "binding_assessment",
                    binding_assessment,
                    "assessment_hash",
                    lambda document: (
                        registration
                        .verify_strategy_correlation_multiplicity_binding_assessment(
                            document,
                            family_registration=family_registration,
                            multiplicity_audit=multiplicity_audit,
                        )
                    ),
                    11,
                ),
            ]

            boolean_leaves = 0
            attacks = 0
            for name, document, hash_field, verifier, expected_leaves in cases:
                self.assertEqual(verifier(document)["status"], "PASS")
                paths = list(_boolean_paths(document))
                self.assertEqual(len(paths), expected_leaves, name)
                boolean_leaves += len(paths)
                for reseal in (False, True):
                    for path in paths:
                        with self.subTest(
                            document=name,
                            mode="reseal" if reseal else "no_reseal",
                            path=path,
                        ):
                            verification = verifier(_attack(
                                document,
                                path,
                                hash_field=hash_field,
                                reseal=reseal,
                            ))
                            self.assertEqual(verification["status"], "BLOCK")
                            self.assertTrue(verification["blockers"])
                        attacks += 1

            self.assertEqual(boolean_leaves, 393)
            self.assertEqual(attacks, 786)


if __name__ == "__main__":
    unittest.main()
