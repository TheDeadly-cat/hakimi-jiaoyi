"""Strict JSON equality for the two preregistered-strata public projections."""

from copy import deepcopy
import unittest

from exchange_terminal.services.strategy_correlation_strata_projection import (
    build_strategy_correlation_strata_public_summary,
    verify_strategy_correlation_strata_public_summary,
)
from exchange_terminal.services.strategy_correlation_strata_protocol_projection import (
    build_strategy_correlation_strata_protocol_migration_public_summary,
    verify_strategy_correlation_strata_protocol_migration_public_summary,
)
from tests import test_strategy_correlation_strata_projection as projection_fixtures
from tests import (
    test_strategy_correlation_strata_protocol_projection as protocol_fixtures,
)


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
    old = parent[path[-1]]
    parent[path[-1]] = 1 if old else 0
    return attacked


class StrategyCorrelationStrataPublicProjectionStrictEqualityTests(
    unittest.TestCase
):
    def _assert_aliases_blocked(
        self,
        *,
        document,
        verifier,
        expected_boolean_leaves,
        expected_blocker,
    ):
        self.assertEqual(verifier(document)["status"], "PASS")
        paths = list(_boolean_paths(document))
        self.assertEqual(len(paths), expected_boolean_leaves)
        for path in paths:
            with self.subTest(path=path):
                attacked = _replace_boolean_with_integer(document, path)
                self.assertEqual(
                    verifier(attacked),
                    {
                        "status": "BLOCK",
                        "blockers": [expected_blocker],
                    },
                )

    def test_strata_summary_observed_and_unknown_reject_aliases(self):
        fixture = (
            projection_fixtures.StrategyCorrelationStrataProjectionTests()
        )
        source, registration, complete_link_gate, strata_gate = fixture._fixture()
        observed = build_strategy_correlation_strata_public_summary(
            registration,
            source_preregistration=source,
            source_gate=strata_gate,
            complete_link_gate=complete_link_gate,
        )
        self.assertEqual(observed["source"]["status"], "OBSERVED")
        self._assert_aliases_blocked(
            document=observed,
            verifier=lambda candidate: (
                verify_strategy_correlation_strata_public_summary(
                    candidate,
                    source_registration=registration,
                    source_preregistration=source,
                    source_gate=strata_gate,
                    complete_link_gate=complete_link_gate,
                )
            ),
            expected_boolean_leaves=12,
            expected_blocker="strata_public_summary_exact_rebuild_mismatch",
        )

        unknown = build_strategy_correlation_strata_public_summary(
            None,
            source_preregistration=None,
        )
        self.assertEqual(unknown["source"]["status"], "UNKNOWN")
        self._assert_aliases_blocked(
            document=unknown,
            verifier=lambda candidate: (
                verify_strategy_correlation_strata_public_summary(
                    candidate,
                    source_registration=None,
                    source_preregistration=None,
                )
            ),
            expected_boolean_leaves=12,
            expected_blocker="strata_public_summary_exact_rebuild_mismatch",
        )

    def test_protocol_summary_observed_and_unknown_reject_aliases(self):
        fixture = (
            protocol_fixtures.StrategyCorrelationStrataProtocolProjectionTests()
        )
        protocol_registration, _ = fixture._protocol()
        observed = (
            build_strategy_correlation_strata_protocol_migration_public_summary(
                protocol_registration
            )
        )
        self.assertEqual(observed["source"]["status"], "OBSERVED")
        self._assert_aliases_blocked(
            document=observed,
            verifier=lambda candidate: (
                verify_strategy_correlation_strata_protocol_migration_public_summary(
                    candidate,
                    source_protocol_registration=protocol_registration,
                )
            ),
            expected_boolean_leaves=13,
            expected_blocker=(
                "strata_protocol_public_summary_exact_rebuild_mismatch"
            ),
        )

        unknown = (
            build_strategy_correlation_strata_protocol_migration_public_summary(
                None
            )
        )
        self.assertEqual(unknown["source"]["status"], "UNKNOWN")
        self._assert_aliases_blocked(
            document=unknown,
            verifier=lambda candidate: (
                verify_strategy_correlation_strata_protocol_migration_public_summary(
                    candidate,
                    source_protocol_registration=None,
                )
            ),
            expected_boolean_leaves=13,
            expected_blocker=(
                "strata_protocol_public_summary_exact_rebuild_mismatch"
            ),
        )


if __name__ == "__main__":
    unittest.main()
