"""Negative evidence for already-protected strata rebuild verifiers."""

from copy import deepcopy
import unittest

from exchange_terminal.services.strict_canonical_json_hash import (
    strict_canonical_hash,
)
from exchange_terminal.services import strategy_correlation_preregistered_strata as prereg
from exchange_terminal.services import strategy_correlation_strata_protocol as protocol
from exchange_terminal.services import strategy_correlation_strata_registry as registry
from exchange_terminal.services import strategy_correlation_strata_global_independence as global_gate
from tests import test_strategy_correlation_preregistered_strata as prereg_fixtures
from tests import test_strategy_correlation_strata_protocol as protocol_fixtures
from tests import test_strategy_correlation_strata_registry as registry_fixtures
from tests import test_strategy_correlation_strata_global_independence as global_fixtures


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
        candidate[hash_field] = strict_canonical_hash(
            {
                key: value
                for key, value in candidate.items()
                if key != hash_field
            }
        )
    return candidate


class StrategyCorrelationStrataProtectedEqualityContractTests(
    unittest.TestCase
):
    def test_no_reseal_and_reseal_aliases_remain_blocked(self):
        prereg_fixture = (
            prereg_fixtures.StrategyCorrelationPreregisteredStrataTests()
        )
        source_pre, complete_link = prereg_fixture._base_fixture()
        dimensions = prereg_fixture._separate_strata(
            source_pre["symbols"]
        )
        registration = (
            prereg.build_strategy_correlation_strata_preregistration(
                source_pre,
                dimensions,
            )
        )
        strata_gate = prereg.evaluate_strategy_correlation_strata_gate(
            registration,
            complete_link,
            source_preregistration=source_pre,
        )

        _, protocol_source = (
            protocol_fixtures.StrategyCorrelationStrataProtocolTests()
            ._source_v6()
        )
        protocol_registration = (
            protocol.build_strategy_correlation_strata_protocol_registration(
                protocol_source
            )
        )

        registry_fixture = (
            registry_fixtures.StrategyCorrelationStrataRegistryTests()
        )
        registry_source, _, registry_registration, registry_asset = (
            registry_fixture._source()
        )
        registry_binding = registry_fixture._assessment(
            registry_source,
            registry_registration,
            registry_asset,
        )
        selection_cutoff = registry_binding["selection_cutoff_date"]
        expected_asset_hash = registry_asset["registry_asset_hash"]
        expected_source_hash = (
            registry_asset["classification_source"]["content_hash"]
        )

        global_fixture = (
            global_fixtures
            .StrategyCorrelationStrataGlobalIndependenceTests()
        )
        (
            global_source,
            global_registration,
            global_complete,
            global_strata_gate,
            global_document,
        ) = global_fixture._fixture(
            global_fixture._separate_dimension(3)
        )

        cases = [
            (
                registration,
                "registration_hash",
                lambda document: (
                    prereg
                    .verify_strategy_correlation_strata_preregistration(
                        document,
                        source_preregistration=source_pre,
                    )
                ),
            ),
            (
                strata_gate,
                "gate_hash",
                lambda document: prereg.verify_strategy_correlation_strata_gate(
                    document,
                    registration=registration,
                    complete_link_gate=complete_link,
                    source_preregistration=source_pre,
                ),
            ),
            (
                protocol_registration,
                "registration_hash",
                protocol.verify_strategy_correlation_strata_protocol_registration,
            ),
            (
                registry_asset,
                "registry_asset_hash",
                lambda document: registry.verify_strategy_correlation_strata_registry_asset(
                    document,
                    source_preregistration=registry_source,
                ),
            ),
            (
                registry_binding,
                "assessment_hash",
                lambda document: registry.verify_strategy_correlation_strata_registry_binding(
                    document,
                    registry_asset=registry_asset,
                    registration=registry_registration,
                    source_preregistration=registry_source,
                    selection_cutoff_date=selection_cutoff,
                    expected_registry_asset_hash=expected_asset_hash,
                    expected_classification_source_hash=expected_source_hash,
                ),
            ),
            (
                global_document,
                "gate_hash",
                lambda document: global_gate.verify_strategy_correlation_strata_global_independence_gate(
                    document,
                    registration=global_registration,
                    complete_link_gate=global_complete,
                    strata_gate=global_strata_gate,
                    source_preregistration=global_source,
                ),
            ),
        ]

        boolean_leaves = 0
        attacks = 0
        for document, hash_field, verifier in cases:
            self.assertEqual(verifier(document)["status"], "PASS")
            paths = list(_boolean_paths(document))
            boolean_leaves += len(paths)
            for reseal in (False, True):
                for path in paths:
                    verification = verifier(
                        _attack(
                            document,
                            path,
                            hash_field=hash_field,
                            reseal=reseal,
                        )
                    )
                    self.assertEqual(verification["status"], "BLOCK")
                    self.assertTrue(verification["blockers"])
                    attacks += 1

        self.assertEqual(boolean_leaves, 154)
        self.assertEqual(attacks, 308)


if __name__ == "__main__":
    unittest.main()
