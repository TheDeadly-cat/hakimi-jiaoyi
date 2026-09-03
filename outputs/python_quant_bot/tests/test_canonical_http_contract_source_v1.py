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

from exchange_terminal import server
from exchange_terminal.services import http_contract as legacy
from hakimi_research import http_contract as canonical


class CanonicalHttpContractSourceV1Tests(unittest.TestCase):
    PUBLIC_NAMES = (
        "ARCHIVED_PAPER_READ_ONLY_PATHS",
        "LOCAL_CLIENT_HOSTS",
        "LOCAL_LOOPBACK_HOSTS",
        "MUTATION_PATHS",
        "POST_API_PATHS",
        "READABLE_MUTATION_PATHS",
        "allowed_web_origin",
        "archived_execution_route_state",
        "payload_to_query",
        "read_only_get_mutation_requested",
        "trusted_refresh_get_allowed",
    )

    def test_callable_source_is_the_root_package(self) -> None:
        expected = (
            REPOSITORY_ROOT / "src" / "hakimi_research" / "http_contract.py"
        ).resolve()
        actual = Path(
            inspect.getsourcefile(canonical.archived_execution_route_state) or ""
        ).resolve()
        self.assertEqual(actual, expected)
        self.assertNotIn("outputs", actual.parts)

    def test_legacy_path_reexports_identical_objects(self) -> None:
        for name in self.PUBLIC_NAMES:
            with self.subTest(name=name):
                self.assertIs(getattr(legacy, name), getattr(canonical, name))

    def test_legacy_module_has_no_local_function_or_class_definitions(self) -> None:
        legacy_path = PROJECT_ROOT / "exchange_terminal" / "services" / "http_contract.py"
        tree = ast.parse(legacy_path.read_text(encoding="utf-8"))
        definitions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        ]
        self.assertEqual(definitions, [])

    def test_existing_server_consumer_uses_the_canonical_classifier(self) -> None:
        self.assertIs(
            server.archived_execution_route_state,
            canonical.archived_execution_route_state,
        )


if __name__ == "__main__":
    unittest.main()
