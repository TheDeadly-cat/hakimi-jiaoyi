from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

from hakimi_research import http_contract
from exchange_terminal.services.http_contract import (
    ARCHIVED_PAPER_READ_ONLY_PATHS,
    MUTATION_PATHS,
    archived_execution_route_state,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = PROJECT_ROOT / "exchange_terminal" / "server.py"

ARCHIVED_PAPER_MUTATION_PATHS = frozenset({
    "/api/paper/arm",
    "/api/paper/condition/add",
    "/api/paper/condition/cancel",
    "/api/paper/evaluate",
    "/api/paper/manual-order",
    "/api/paper/reset",
    "/api/paper/stop",
})


class ArchivedExecutionHttpRouteGuardV1Tests(unittest.TestCase):
    def test_read_only_legacy_views_are_get_only(self) -> None:
        self.assertEqual(
            ARCHIVED_PAPER_READ_ONLY_PATHS,
            frozenset({
                "/api/paper/ledger",
                "/api/paper/orders/lifecycle",
                "/api/paper/portfolio",
                "/api/paper/snapshot",
            }),
        )
        for path in ARCHIVED_PAPER_READ_ONLY_PATHS:
            with self.subTest(path=path):
                self.assertEqual(
                    archived_execution_route_state("GET", path), "READ_ONLY"
                )
                self.assertEqual(
                    archived_execution_route_state("POST", path), "BLOCK"
                )

    def test_every_registered_paper_mutation_is_permanently_blocked(self) -> None:
        self.assertTrue(ARCHIVED_PAPER_MUTATION_PATHS.issubset(MUTATION_PATHS))
        for method in ("GET", "POST", "PUT", "DELETE"):
            for path in ARCHIVED_PAPER_MUTATION_PATHS:
                with self.subTest(method=method, path=path):
                    self.assertEqual(
                        archived_execution_route_state(method, path), "BLOCK"
                    )

    def test_unknown_paper_subpaths_fail_closed(self) -> None:
        for path in (
            "/api/paper/",
            "/api/paper/new-order",
            "/api/paper/snapshot/extra",
            "/api/paper/../paper/arm",
            "/api/paper/SNAPSHOT",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    archived_execution_route_state("GET", path), "BLOCK"
                )

    def test_unrelated_research_paths_are_not_intercepted(self) -> None:
        for path in ("/api/health", "/api/research/panel"):
            with self.subTest(path=path):
                self.assertEqual(
                    archived_execution_route_state("GET", path),
                    "NOT_APPLICABLE",
                )

    def test_exact_native_string_contract_rejects_aliases(self) -> None:
        class StrAlias(str):
            pass

        for method, path in (
            (StrAlias("GET"), "/api/paper/snapshot"),
            ("GET", StrAlias("/api/paper/snapshot")),
        ):
            with self.subTest(method=method, path=path):
                with self.assertRaises(TypeError):
                    archived_execution_route_state(method, path)  # type: ignore[arg-type]

    def test_catalog_drift_cannot_enable_archived_routes(self) -> None:
        class DriftedCatalog:
            def to_dict(self) -> dict[str, object]:
                return {"capabilities": {"paper_execution": "Supported"}}

        with patch.object(
            http_contract,
            "build_product_capability_catalog",
            return_value=DriftedCatalog(),
        ):
            self.assertEqual(
                archived_execution_route_state("GET", "/api/paper/snapshot"),
                "BLOCK",
            )
            self.assertEqual(
                archived_execution_route_state("POST", "/api/paper/arm"),
                "BLOCK",
            )

    def test_server_contains_no_legacy_paper_mutation_dispatch(self) -> None:
        source = SERVER_PATH.read_text(encoding="utf-8")
        guard_call = "archived_route_state = archived_execution_route_state("
        self.assertIn(guard_call, source)
        for path in sorted(ARCHIVED_PAPER_MUTATION_PATHS):
            branch = f'if path == "{path}":'
            self.assertNotIn(branch, source)
        self.assertNotIn('if path.startswith("/api/paper/")', source)


if __name__ == "__main__":
    unittest.main()
