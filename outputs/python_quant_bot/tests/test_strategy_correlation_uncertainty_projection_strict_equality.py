"""Strict JSON equality for the uncertainty public summary verifier."""

from copy import deepcopy
import unittest
from unittest.mock import patch

from exchange_terminal.services import strategy_correlation_uncertainty_audit
from exchange_terminal.services.strategy_correlation_uncertainty_projection import (
    build_strategy_correlation_uncertainty_public_summary,
    verify_strategy_correlation_uncertainty_public_summary,
)
from tests import test_strategy_correlation_uncertainty_audit as uncertainty_fixtures


def _boolean_paths(value, path=()):
    if type(value) is bool:
        yield path
    elif type(value) is dict:
        for key, child in value.items():
            yield from _boolean_paths(child, path + (key,))
    elif type(value) is list:
        for index, child in enumerate(value):
            yield from _boolean_paths(child, path + (index,))


def _replace_boolean_with_integer(document, path):
    attacked = deepcopy(document)
    parent = attacked
    for part in path[:-1]:
        parent = parent[part]
    parent[path[-1]] = int(parent[path[-1]])
    return attacked


class StrategyCorrelationUncertaintyProjectionStrictEqualityTests(
    unittest.TestCase
):
    def _assert_aliases_blocked(
        self,
        *,
        document,
        verifier,
        expected_boolean_leaves,
    ):
        self.assertEqual(verifier(document)["status"], "PASS")
        paths = list(_boolean_paths(document))
        self.assertEqual(len(paths), expected_boolean_leaves)
        for path in paths:
            with self.subTest(path=path):
                verification = verifier(
                    _replace_boolean_with_integer(document, path)
                )
                self.assertEqual(verification["status"], "BLOCK")
                self.assertTrue(verification["blockers"])

    def test_observed_summary_rejects_all_bool_int_aliases(self):
        fixture = (
            uncertainty_fixtures.StrategyCorrelationUncertaintyAuditTests()
        )
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
            source = (
                strategy_correlation_uncertainty_audit
                .build_strategy_correlation_uncertainty_audit(replay)
            )
            document = (
                build_strategy_correlation_uncertainty_public_summary(source)
            )
            self._assert_aliases_blocked(
                document=document,
                verifier=lambda candidate: (
                    verify_strategy_correlation_uncertainty_public_summary(
                        candidate,
                        source_audit=source,
                    )
                ),
                expected_boolean_leaves=9,
            )

    def test_unknown_summary_rejects_all_bool_int_aliases(self):
        document = build_strategy_correlation_uncertainty_public_summary(None)
        self.assertEqual(document["status"], "UNKNOWN")
        self._assert_aliases_blocked(
            document=document,
            verifier=lambda candidate: (
                verify_strategy_correlation_uncertainty_public_summary(
                    candidate,
                    source_audit=None,
                )
            ),
            expected_boolean_leaves=9,
        )


if __name__ == "__main__":
    unittest.main()
