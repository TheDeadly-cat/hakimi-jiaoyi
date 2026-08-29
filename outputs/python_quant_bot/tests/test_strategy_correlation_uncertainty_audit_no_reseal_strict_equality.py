"""No-reseal strict equality contract for uncertainty audit verification."""

from copy import deepcopy
import unittest
from unittest.mock import patch

from exchange_terminal.services import strategy_correlation_uncertainty_audit
from tests import test_strategy_correlation_uncertainty_audit as audit_fixtures


def _boolean_paths(value, path=()):
    if type(value) is bool:
        yield path
    elif type(value) is dict:
        for key, child in value.items():
            yield from _boolean_paths(child, path + (key,))
    elif type(value) is list:
        for index, child in enumerate(value):
            yield from _boolean_paths(child, path + (index,))


def _replace_boolean_without_resealing(document, path):
    attacked = deepcopy(document)
    parent = attacked
    for part in path[:-1]:
        parent = parent[part]
    parent[path[-1]] = int(parent[path[-1]])
    return attacked


class StrategyCorrelationUncertaintyAuditNoResealStrictEqualityTests(
    unittest.TestCase
):
    def test_all_no_reseal_bool_int_aliases_are_blocked(self):
        fixture = audit_fixtures.StrategyCorrelationUncertaintyAuditTests()
        replay = fixture._replay(
            {
                "A": fixture._normal(1),
                "B": fixture._normal(2),
                "C": fixture._normal(3),
            },
            [
                {"cluster_id": "a", "members": ["A"]},
                {"cluster_id": "b", "members": ["B"]},
                {"cluster_id": "c", "members": ["C"]},
            ],
        )
        with patch.object(
            strategy_correlation_uncertainty_audit,
            "verify_correlation_matrix_replay",
            return_value={"status": "PASS", "blockers": []},
        ):
            document = (
                strategy_correlation_uncertainty_audit
                .build_strategy_correlation_uncertainty_audit(replay)
            )
            self.assertEqual(
                strategy_correlation_uncertainty_audit
                .verify_strategy_correlation_uncertainty_audit(document)[
                    "status"
                ],
                "PASS",
            )

            attacked = 0
            for path in _boolean_paths(document):
                candidate = _replace_boolean_without_resealing(
                    document,
                    path,
                )
                verification = (
                    strategy_correlation_uncertainty_audit
                    .verify_strategy_correlation_uncertainty_audit(candidate)
                )
                self.assertEqual(verification["status"], "BLOCK")
                self.assertTrue(verification["blockers"])
                attacked += 1

        self.assertEqual(attacked, 201)


if __name__ == "__main__":
    unittest.main()
