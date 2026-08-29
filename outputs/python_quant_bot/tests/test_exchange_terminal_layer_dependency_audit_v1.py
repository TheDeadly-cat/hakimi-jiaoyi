from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
import unittest

from exchange_terminal.services import (
    exchange_terminal_layer_dependency_audit_v1 as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class NonNativeSources(dict):
    pass


def _current_layer_sources() -> dict[str, str]:
    sources: dict[str, str] = {}
    root = PROJECT_ROOT / "exchange_terminal"
    for layer in subject.LAYERS:
        for path in sorted((root / layer).glob("*.py")):
            module = f"exchange_terminal.{layer}.{path.stem}"
            sources[module] = path.read_text(encoding="utf-8")
    return sources


def _clean_sources() -> dict[str, str]:
    return {
        "exchange_terminal.domain.model": "VALUE = 1\n",
        "exchange_terminal.application.use_case": (
            "from exchange_terminal.domain import model\n"
        ),
        "exchange_terminal.infrastructure.repository": (
            "from exchange_terminal.application import use_case\n"
        ),
        "exchange_terminal.interfaces.http_handoff_v1": (
            "from exchange_terminal.application import use_case\n"
        ),
    }


class ExchangeTerminalLayerDependencyAuditV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.sources = _current_layer_sources()
        self.audit = subject.evaluate_exchange_terminal_layer_dependency_audit_v1(
            self.sources
        )

    def test_current_tree_is_partial_layering_not_complete_architecture(self) -> None:
        self.assertEqual(self.audit["status"], subject.STATUS_BLOCKED)
        self.assertEqual(
            self.audit["decision"], "LAYER_ROLE_SEPARATION_REQUIRED"
        )
        self.assertFalse(self.audit["facts"]["architecture_migration_complete"])

    def test_current_tree_has_bidirectional_application_interfaces_package_edges(self) -> None:
        counts = self.audit["cross_layer_edge_counts"]
        self.assertGreater(counts["application->interfaces"], 0)
        self.assertGreater(counts["interfaces->application"], 0)
        self.assertIn(
            "APPLICATION_INTERFACES", self.audit["bidirectional_layer_pairs"]
        )
        self.assertTrue(
            self.audit["role_observation"]["interfaces_package_role_mixed"]
        )

    def test_current_tree_has_no_module_cycle_and_clean_domain_infrastructure_direction(self) -> None:
        self.assertEqual(self.audit["module_cycles"], [])
        self.assertFalse(self.audit["facts"]["module_cycle_detected"])
        self.assertTrue(self.audit["facts"]["domain_inward_only"])
        self.assertTrue(
            self.audit["facts"]["application_infrastructure_separated"]
        )

    def test_current_tree_module_inventory_is_exact_for_scoped_layers(self) -> None:
        self.assertEqual(
            self.audit["module_counts"],
            {
                "domain": 2,
                "application": 82,
                "infrastructure": 1,
                "interfaces": 15,
            },
        )
        self.assertRegex(self.audit["source_set_hash"], r"^[0-9a-f]{64}$")


    def test_current_tree_exposes_minimum_consumer_first_cleanup_slice(self) -> None:
        self.assertEqual(
            self.audit["minimum_cleanup_slice"],
            list(subject.MINIMUM_PORT_DELIVERY_CLEANUP_SLICE),
        )
        self.assertEqual(
            self.audit["minimum_cleanup_slice"][0],
            "CLASSIFY_INTERFACES_MODULES_AS_PORT_DELIVERY_OR_SUPPORT",
        )
        self.assertEqual(
            self.audit["minimum_cleanup_slice"][-1],
            "REMOVE_SHIMS_ONLY_AFTER_CONSUMER_MIGRATION",
        )

    def test_clean_inward_dependency_graph_conforms(self) -> None:
        audit = subject.evaluate_exchange_terminal_layer_dependency_audit_v1(
            _clean_sources()
        )
        self.assertEqual(audit["status"], subject.STATUS_CONFORMING)
        self.assertEqual(audit["violations"], [])
        self.assertTrue(audit["facts"]["architecture_migration_complete"])
        self.assertEqual(audit["bidirectional_layer_pairs"], [])

    def test_bidirectional_package_roles_block_without_a_module_cycle(self) -> None:
        sources = _clean_sources()
        sources["exchange_terminal.application.port_user"] = (
            "from exchange_terminal.interfaces import state_port\n"
        )
        sources["exchange_terminal.interfaces.state_port"] = (
            "from exchange_terminal.application import use_case\n"
        )
        audit = subject.evaluate_exchange_terminal_layer_dependency_audit_v1(
            sources
        )
        self.assertEqual(audit["status"], subject.STATUS_BLOCKED)
        self.assertEqual(audit["module_cycles"], [])
        self.assertIn(
            "INTERFACES_PACKAGE_MIXES_PORT_AND_DELIVERY_ROLES",
            audit["violations"],
        )

    def test_cross_layer_module_cycle_is_explicitly_blocked(self) -> None:
        sources = _clean_sources()
        sources["exchange_terminal.application.use_case"] = (
            "from exchange_terminal.interfaces import http_handoff_v1\n"
        )
        audit = subject.evaluate_exchange_terminal_layer_dependency_audit_v1(
            sources
        )
        self.assertEqual(audit["status"], subject.STATUS_BLOCKED)
        self.assertTrue(audit["facts"]["module_cycle_detected"])
        self.assertIn("CROSS_LAYER_MODULE_CYCLE_DETECTED", audit["violations"])

    def test_domain_application_infrastructure_direction_violations_block(self) -> None:
        domain_outward = _clean_sources()
        domain_outward["exchange_terminal.domain.model"] = (
            "from exchange_terminal.application import use_case\n"
        )
        app_infra = _clean_sources()
        app_infra["exchange_terminal.application.use_case"] = (
            "from exchange_terminal.infrastructure import repository\n"
        )
        self.assertIn(
            "DOMAIN_DEPENDS_ON_OUTER_LAYER",
            subject.evaluate_exchange_terminal_layer_dependency_audit_v1(
                domain_outward
            )["violations"],
        )
        self.assertIn(
            "APPLICATION_DEPENDS_ON_INFRASTRUCTURE",
            subject.evaluate_exchange_terminal_layer_dependency_audit_v1(
                app_infra
            )["violations"],
        )

    def test_dynamic_import_is_blocked_as_unaudited(self) -> None:
        sources = _clean_sources()
        sources["exchange_terminal.application.use_case"] = (
            'import importlib\nimportlib.import_module("exchange_terminal.domain.model")\n'
        )
        audit = subject.evaluate_exchange_terminal_layer_dependency_audit_v1(
            sources
        )
        self.assertEqual(audit["status"], subject.STATUS_BLOCKED)
        self.assertIn("DYNAMIC_IMPORT_PRESENT_UNAUDITED", audit["violations"])
        self.assertFalse(audit["facts"]["dynamic_imports_absent"])

    def test_invalid_non_native_and_syntax_error_inputs_are_unknown(self) -> None:
        non_native = subject.evaluate_exchange_terminal_layer_dependency_audit_v1(
            NonNativeSources(_clean_sources())
        )
        syntax_error = _clean_sources()
        syntax_error["exchange_terminal.domain.model"] = "def broken(:\n"
        broken = subject.evaluate_exchange_terminal_layer_dependency_audit_v1(
            syntax_error
        )
        self.assertEqual(non_native["status"], "UNKNOWN")
        self.assertEqual(broken["status"], "UNKNOWN")
        self.assertFalse(non_native["facts"]["native_source_mapping_verified"])
        self.assertFalse(broken["facts"]["all_modules_ast_parsed"])

    def test_exact_verifier_rejects_resealed_completion_promotion(self) -> None:
        self.assertTrue(
            subject.verify_exchange_terminal_layer_dependency_audit_v1(
                self.audit, self.sources
            )
        )
        promoted = deepcopy(self.audit)
        promoted["facts"]["architecture_migration_complete"] = True
        promoted["authority"]["architecture_migration_complete_allowed"] = True
        promoted.pop("layer_dependency_audit_hash")
        promoted = seal_strict_canonical_document(
            promoted, "layer_dependency_audit_hash"
        )
        self.assertFalse(
            subject.verify_exchange_terminal_layer_dependency_audit_v1(
                promoted, self.sources
            )
        )

    def test_audit_is_bounded_deterministic_and_embeds_no_source(self) -> None:
        second = subject.evaluate_exchange_terminal_layer_dependency_audit_v1(
            self.sources
        )
        self.assertEqual(self.audit, second)
        serialized = json.dumps(self.audit, sort_keys=True)
        self.assertFalse(self.audit["facts"]["raw_source_embedded"])
        self.assertNotIn("from exchange_terminal", serialized)
        self.assertNotIn("def ", serialized)
        self.assertTrue(
            all(value is False for value in self.audit["authority"].values())
        )

    def test_audit_contains_no_promotional_or_trading_claim(self) -> None:
        serialized = json.dumps(self.audit, sort_keys=True)
        forbidden = re.compile(
            r"\b(?:READY|PROFIT|RETURN|BUY|SELL)\b", re.IGNORECASE
        )
        self.assertIsNone(forbidden.search(serialized))


if __name__ == "__main__":
    unittest.main()
