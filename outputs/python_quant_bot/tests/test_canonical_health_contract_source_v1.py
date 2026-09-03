from __future__ import annotations

import ast
import inspect
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from _canonical_source import activate_canonical_source

activate_canonical_source()

from exchange_terminal.application import health_contract as legacy
from exchange_terminal.interfaces.http import health as http_health
from hakimi_research import health_contract as canonical


class CanonicalHealthContractSourceV1Tests(unittest.TestCase):
    PUBLIC_NAMES = (
        "build_research_disabled_payload",
        "build_runtime_health_payload",
    )

    def test_callable_sources_are_the_root_package(self) -> None:
        expected = (
            REPOSITORY_ROOT / "src" / "hakimi_research" / "health_contract.py"
        ).resolve()
        for name in self.PUBLIC_NAMES:
            with self.subTest(name=name):
                actual = Path(inspect.getsourcefile(getattr(canonical, name)) or "").resolve()
                self.assertEqual(actual, expected)
                self.assertNotIn("outputs", actual.parts)

    def test_legacy_path_reexports_identical_objects(self) -> None:
        for name in self.PUBLIC_NAMES:
            with self.subTest(name=name):
                self.assertIs(getattr(legacy, name), getattr(canonical, name))

    def test_legacy_module_has_no_local_function_or_class_definitions(self) -> None:
        legacy_path = PROJECT_ROOT / "exchange_terminal" / "application" / "health_contract.py"
        tree = ast.parse(legacy_path.read_text(encoding="utf-8"))
        definitions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        ]
        self.assertEqual(definitions, [])

    def test_http_adapter_consumes_canonical_objects(self) -> None:
        self.assertIs(
            http_health.build_runtime_health_payload,
            canonical.build_runtime_health_payload,
        )
        self.assertIs(
            http_health.build_research_disabled_payload,
            canonical.build_research_disabled_payload,
        )

    def test_projection_cannot_inherit_execution_authority(self) -> None:
        payload = canonical.build_runtime_health_payload(
            {
                "status": "PASS",
                "time": 17,
                "product_mode": "TRADING",
                "research_only": False,
                "paper_allowed": True,
                "live_allowed": True,
                "capability": {"paper_allowed": True},
                "product_capability_catalog": {"paper_execution": "Supported"},
            },
            {"armed": True},
            read_only=False,
            runtime_mutations_allowed=True,
            live_trading_hard_block=True,
            guardian_worker_running=True,
        )
        self.assertFalse(payload["paper_authorized"])
        self.assertFalse(payload["binding_authorized"])
        self.assertFalse(payload["paper_order_allowed"])
        self.assertFalse(payload["automated_paper_order_allowed"])
        self.assertFalse(payload["live_order_allowed"])
        self.assertTrue(payload["live_trading_hard_block"])
        self.assertNotIn("product_mode", payload["runtime_build"])
        self.assertNotIn("paper_allowed", payload["runtime_build"])
        self.assertNotIn("live_allowed", payload["runtime_build"])
        self.assertEqual(
            payload["runtime_build"]["product_capability_catalog"],
            payload["product_capability_catalog"],
        )


if __name__ == "__main__":
    unittest.main()
