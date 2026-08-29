"""No-reseal strict equality for correlation protocol binding assessment."""

from copy import deepcopy
import unittest
from unittest.mock import patch

from exchange_terminal.services import strategy_correlation_protocol_binding
from tests import test_strategy_correlation_protocol_binding as binding_fixtures


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


class StrategyCorrelationProtocolBindingNoResealStrictEqualityTests(
    unittest.TestCase
):
    def test_all_no_reseal_bool_int_aliases_are_blocked(self):
        fixture = binding_fixtures.StrategyCorrelationProtocolBindingTests()
        fixture.setUp()
        gate = fixture._synthetic_gate()
        protocol = fixture._synthetic_protocol()

        with patch.object(
            strategy_correlation_protocol_binding,
            "verify_replayed_correlation_cluster_gate",
            return_value={"status": "PASS", "blockers": []},
        ), patch.object(
            strategy_correlation_protocol_binding,
            "verify_strategy_matrix_protocol",
            return_value={"status": "PASS", "blockers": []},
        ):
            document = (
                strategy_correlation_protocol_binding
                .assess_strategy_correlation_protocol_binding(
                    protocol,
                    fixture.registration,
                    gate,
                )
            )

            def verify(candidate):
                return (
                    strategy_correlation_protocol_binding
                    .verify_strategy_correlation_protocol_binding_assessment(
                        candidate,
                        protocol=protocol,
                        registration=fixture.registration,
                        replayed_gate=gate,
                    )
                )

            self.assertEqual(verify(document)["status"], "PASS")
            attacked = 0
            for path in _boolean_paths(document):
                verification = verify(
                    _replace_boolean_without_resealing(document, path)
                )
                self.assertEqual(verification["status"], "BLOCK")
                self.assertTrue(verification["blockers"])
                attacked += 1

        self.assertEqual(attacked, 19)


if __name__ == "__main__":
    unittest.main()
