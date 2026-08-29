from __future__ import annotations

import copy
import inspect
import unittest

from exchange_terminal.services import strategy_correlation_cluster_complete_link as core
from exchange_terminal.services import strategy_correlation_complete_link_projection
from exchange_terminal.services import strategy_correlation_complete_link_protocol
from exchange_terminal.services import strategy_correlation_complete_link_registry_binding
from exchange_terminal.services import strategy_correlation_complete_link_report_consumer
from tests import test_strategy_correlation_cluster_complete_link as core_tests


_FAMILY_MODULES = (
    core,
    strategy_correlation_complete_link_projection,
    strategy_correlation_complete_link_protocol,
    strategy_correlation_complete_link_registry_binding,
    strategy_correlation_complete_link_report_consumer,
)


def _boolean_paths(value, prefix=()):
    if type(value) is bool:
        yield prefix, value
    elif type(value) is dict:
        for key, child in value.items():
            yield from _boolean_paths(child, prefix + (key,))
    elif type(value) is list:
        for index, child in enumerate(value):
            yield from _boolean_paths(child, prefix + (index,))


def _replace_path(document, path, value) -> None:
    target = document
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value


class StrategyCorrelationCompleteLinkStrictEqualityTests(unittest.TestCase):
    def setUp(self) -> None:
        fixture = core_tests.StrategyCorrelationClusterCompleteLinkTests
        self.preregistration = fixture._preregistration()
        self.matrix = fixture._matrix(ac=0.80)
        self.cells = fixture._cells()
        self.gate_kwargs = {
            "preregistration": self.preregistration,
            "correlation_matrix": self.matrix,
            "selection_cells": self.cells,
            "strategy_id": "strategy-strict-equality",
            "variant_id": "variant-strict-equality",
            "lane": "RAW_EXCESS",
        }
        self.gate = core.evaluate_correlation_cluster_gate_v2(**self.gate_kwargs)
        self.audit = core.build_correlation_cluster_complete_link_audit(
            self.preregistration,
            self.matrix,
        )

    def test_untampered_gate_and_audit_still_verify(self) -> None:
        self.assertEqual(
            core.verify_correlation_cluster_gate_v2(
                self.gate,
                **self.gate_kwargs,
            )["status"],
            "PASS",
        )
        self.assertEqual(
            core.verify_correlation_cluster_complete_link_audit(
                self.audit,
                preregistration=self.preregistration,
                correlation_matrix=self.matrix,
            )["status"],
            "PASS",
        )

    def test_every_gate_boolean_integer_alias_is_blocked_without_reseal(self) -> None:
        paths = list(_boolean_paths(self.gate))
        self.assertEqual(len(paths), 15)

        for path, original in paths:
            with self.subTest(path=path, original=original):
                tampered = copy.deepcopy(self.gate)
                _replace_path(tampered, path, int(original))
                verification = core.verify_correlation_cluster_gate_v2(
                    tampered,
                    **self.gate_kwargs,
                )
                self.assertEqual(verification["status"], "BLOCK")

    def test_every_audit_boolean_integer_alias_is_blocked_without_reseal(self) -> None:
        paths = list(_boolean_paths(self.audit))
        self.assertEqual(len(paths), 5)

        for path, original in paths:
            with self.subTest(path=path, original=original):
                tampered = copy.deepcopy(self.audit)
                _replace_path(tampered, path, int(original))
                verification = core.verify_correlation_cluster_complete_link_audit(
                    tampered,
                    preregistration=self.preregistration,
                    correlation_matrix=self.matrix,
                )
                self.assertEqual(verification["status"], "BLOCK")

    def test_all_complete_link_verifiers_remove_python_equality_bypass(self) -> None:
        for module in _FAMILY_MODULES:
            with self.subTest(module=module.__name__):
                source = inspect.getsource(module)
                self.assertIn("strict_json_contract_equal", source)
                self.assertNotIn("document == expected", source)
                self.assertNotIn("document != expected", source)


if __name__ == "__main__":
    unittest.main()
