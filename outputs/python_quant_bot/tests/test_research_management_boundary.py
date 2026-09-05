from __future__ import annotations

import ast
import os
import time
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import urllib.parse

from exchange_terminal.services.http_contract import (
    MUTATION_PATHS, POST_API_PATHS, RETIRED_MANAGEMENT_PATHS,
    archived_execution_route_state,
)

SERVER_PATH = Path(__file__).resolve().parents[1] / "exchange_terminal" / "server.py"


class ResearchManagementBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SERVER_PATH.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.handler = next(node for node in cls.tree.body if isinstance(node, ast.ClassDef) and node.name == "ExchangeTerminalHandler")

    def handler_method(self, name, responses, **dependencies):
        method = next(node for node in self.handler.body if isinstance(node, ast.FunctionDef) and node.name == name)
        module = ast.Module(body=[method], type_ignores=[])
        namespace = {
            "RETIRED_MANAGEMENT_PATHS": RETIRED_MANAGEMENT_PATHS,
            "archived_execution_route_state": archived_execution_route_state,
            "MUTATION_PATHS": MUTATION_PATHS, "POST_API_PATHS": POST_API_PATHS,
            "block_non_loopback_client": lambda _handler: False,
            "json_response": lambda _handler, body, status=200: responses.append((body, status)),
            "urllib": urllib, "Any": object,
            **dependencies,
        }
        exec(compile(module, str(SERVER_PATH), "exec"), namespace)
        return namespace[name]

    def test_retired_handlers_are_not_registered_in_either_post_collection(self):
        self.assertFalse(RETIRED_MANAGEMENT_PATHS & MUTATION_PATHS)
        self.assertFalse(RETIRED_MANAGEMENT_PATHS & POST_API_PATHS)
        self.assertNotIn("/api/futu/status", RETIRED_MANAGEMENT_PATHS)
        self.assertNotIn("/api/ai/runtime-keys/status", RETIRED_MANAGEMENT_PATHS)

    def test_actual_get_post_and_internal_dispatch_reject_before_side_effects(self):
        for path in RETIRED_MANAGEMENT_PATHS:
            for name in ("do_GET", "do_POST", "handle_api"):
                with self.subTest(path=path, method=name):
                    responses = []
                    method = self.handler_method(name, responses)
                    body = Mock()
                    handler = SimpleNamespace(path=path, rfile=body)
                    if name == "handle_api":
                        method(handler, path, {})
                    else:
                        method(handler)
                    self.assertEqual(responses, [({"ok": False, "error": "not found"}, 404)])
                    body.read.assert_not_called()

    def test_remaining_post_mutations_stop_before_request_body_in_readonly_mode(self):
        responses = []
        method = self.handler_method("do_POST", responses, RUNTIME_READ_ONLY=True)
        body = Mock()
        method(SimpleNamespace(path="/api/strategy/pipeline", rfile=body))
        self.assertEqual(responses[0][1], 423)
        self.assertFalse(responses[0][0]["paper_authorized"])
        body.read.assert_not_called()

    def test_default_runtime_is_read_only_and_bad_flags_cannot_enable_writes(self):
        node = next(node for node in self.tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "RUNTIME_READ_ONLY" for target in node.targets))
        for flag in (None, "", "1", "true", "unexpected"):
            with self.subTest(flag=flag), patch.dict(os.environ, {}, clear=True):
                if flag is not None:
                    os.environ["HAKIMI_RUNTIME_READ_ONLY"] = flag
                namespace = {"os": os}
                exec(compile(ast.Module(body=[node], type_ignores=[]), str(SERVER_PATH), "exec"), namespace)
                self.assertTrue(namespace["RUNTIME_READ_ONLY"])

    def test_readonly_health_and_status_dispatch_preserves_status_consumers(self):
        for route, function_name in (
            ("/api/health", "build_health_response_from_runtime"),
            ("/api/futu/status", "futu_status_snapshot"),
            ("/api/ai/runtime-keys/status", "runtime_ai_key_status"),
        ):
            with self.subTest(route=route):
                responses = []
                reader = Mock(return_value={"ok": True, "status": "fixture"})
                method = self.handler_method("handle_api", responses, **{
                    function_name: reader, "RUNTIME_READ_ONLY": True,
                    "LIVE_TRADING_HARD_BLOCK": True, "time": time,
                    "RUNTIME_BUILD_GUARD": SimpleNamespace(snapshot=lambda: {}),
                    "PAPER_ACCOUNT": SimpleNamespace(snapshot=lambda _price: {}),
                    "GUARDIAN_SERVICE": SimpleNamespace(thread=None),
                })
                method(SimpleNamespace(), route, {})
                self.assertEqual(responses, [({"ok": True, "status": "fixture"}, 200)])
                reader.assert_called_once()
        self.assertIn("guardian_started = not RUNTIME_READ_ONLY", self.source)
        self.assertIn("runtime_mutations_allowed=not RUNTIME_READ_ONLY", self.source)


if __name__ == "__main__":
    unittest.main()
