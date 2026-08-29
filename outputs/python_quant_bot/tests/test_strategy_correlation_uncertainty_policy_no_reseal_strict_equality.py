"""Type-strict no-reseal contract for the uncertainty policy verifier."""

from copy import deepcopy
import unittest

from exchange_terminal.services.canonical_json_hash import canonical_hash
from exchange_terminal.services.strategy_correlation_uncertainty_audit import (
    build_strategy_correlation_uncertainty_policy,
    verify_strategy_correlation_uncertainty_policy,
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


def _attack(document, path, *, reseal):
    candidate = deepcopy(document)
    parent = candidate
    for part in path[:-1]:
        parent = parent[part]
    parent[path[-1]] = int(parent[path[-1]])
    if reseal:
        candidate["policy_hash"] = canonical_hash({
            key: value
            for key, value in candidate.items()
            if key != "policy_hash"
        })
    return candidate


class StrategyCorrelationUncertaintyPolicyNoResealStrictEqualityTests(
    unittest.TestCase
):
    def test_all_bool_int_aliases_are_blocked(self):
        policy = build_strategy_correlation_uncertainty_policy()
        self.assertEqual(
            verify_strategy_correlation_uncertainty_policy(policy)["status"],
            "PASS",
        )
        paths = list(_boolean_paths(policy))
        self.assertEqual(
            [".".join(map(str, path)) for path in paths],
            [
                "descriptive_only",
                "requires_new_report_schema",
                "current_writer_activation_allowed",
                "current_admission_allowed",
                "permissions.paper_authorized",
                "permissions.live_order_allowed",
            ],
        )

        attacks = 0
        for reseal in (False, True):
            for path in paths:
                with self.subTest(
                    mode="reseal" if reseal else "no_reseal",
                    path=path,
                ):
                    verification = verify_strategy_correlation_uncertainty_policy(
                        _attack(policy, path, reseal=reseal)
                    )
                    self.assertEqual(verification["status"], "BLOCK")
                    self.assertIn(
                        "strategy_correlation_uncertainty_policy_contract_mismatch",
                        verification["blockers"],
                    )
                attacks += 1

        self.assertEqual(len(paths), 6)
        self.assertEqual(attacks, 12)


if __name__ == "__main__":
    unittest.main()
