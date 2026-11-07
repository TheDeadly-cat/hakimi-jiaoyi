"""Offline provider switch and DeepSeek transport tests; never read real env keys."""
from __future__ import annotations

import ast
from copy import deepcopy
import io
import json
from types import SimpleNamespace
import threading
import unittest
import urllib.error

from tests import test_market_ai_request_flow as market_tests

TREE, SERVER, base_namespace = market_tests.TREE, market_tests.SERVER, market_tests.namespace
from exchange_terminal.services.market_ai_projection import build_market_ai_projection


NAMES = {"runtime_secret", "runtime_ai_key_status", "deepseek_status", "openai_status", "deepseek_chat"}
FUNCTIONS = [node for node in TREE.body if isinstance(node, ast.FunctionDef) and node.name in NAMES]


def namespace(selected="deepseek", *, thinking=False):
    scope, transport = base_namespace()
    environment = {
        "HAKIMI_AI_PROVIDER": selected,
        "OPENAI_API_KEY": "test-openai-placeholder",
        "GPT_API_KEY": "test-gpt-placeholder",
        "DEEPSEEK_API_KEY": "test-deepseek-placeholder",
    }
    reads = []
    def getenv(name, default=None):
        reads.append(name)
        return environment.get(name, default)
    scope.update({
        "os": SimpleNamespace(getenv=getenv),
        "RUNTIME_AI_KEYS": {"OPENAI_API_KEY": "test-runtime-openai-placeholder"},
        "RUNTIME_AI_KEYS_LOCK": threading.RLock(),
        "DEEPSEEK_MODEL": "deepseek-v4-pro",
        "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
        "DEEPSEEK_THINKING_ENABLED": thinking,
    })
    exec(compile(ast.Module(body=FUNCTIONS, type_ignores=[]), str(SERVER), "exec"), scope)
    return scope, transport, environment, reads


def response(content="Public market explanation.", *, reason=None, finish="stop"):
    return io.BytesIO(json.dumps({
        "model": "deepseek-v4-pro",
        "choices": [{"message": {"content": content, "reasoning_content": reason}, "finish_reason": finish}],
        "usage": {"completion_tokens": 6},
    }).encode())


class DeepSeekTransportTests(unittest.TestCase):
    def test_http_errors_are_single_attempt_even_with_thinking_and_never_echo_body(self):
        for status in (400, 401, 402, 403, 422, 429, 500, 503):
            for thinking in (False, True):
                with self.subTest(status=status, thinking=thinking):
                    scope, transport, _, _ = namespace(thinking=thinking)
                    body = io.BytesIO(b'{"error":{"message":"sk-private-provider-body"}}')
                    transport.urlopen.side_effect = urllib.error.HTTPError(
                        "https://api.deepseek.com/chat/completions", status,
                        "sk-private-exception", {}, body,
                    )
                    result = scope["deepseek_chat"]([], "test")
                    self.assertFalse(result["ok"])
                    self.assertEqual(transport.urlopen.call_count, 1)
                    self.assertEqual(result["request_attempts"], 1)
                    self.assertFalse(result["automatic_retry"])
                    self.assertFalse(result["compatibility_retried"])
                    self.assertEqual(result["http_status"], status)
                    self.assertNotIn("sk-", json.dumps(result))
                    self.assertTrue(body.closed)
                    if status == 402:
                        self.assertIn("余额不足", result["error"])
                    if status == 429:
                        self.assertIn("速率限制", result["error"])

    def test_network_failure_and_invalid_json_fail_safely_without_retry(self):
        for failure in (TimeoutError("sk-private-timeout"), io.BytesIO(b"sk-private-invalid-json")):
            scope, transport, _, _ = namespace()
            transport.urlopen.side_effect = failure if isinstance(failure, Exception) else None
            transport.urlopen.return_value = failure
            result = scope["deepseek_chat"]([], "test")
            self.assertFalse(result["ok"])
            self.assertEqual(transport.urlopen.call_count, 1)
            self.assertNotIn("sk-", json.dumps(result))

    def test_missing_malformed_empty_and_reasoning_only_responses_are_not_success(self):
        cases = [None, [], {}, {"choices": []}, {"choices": [None]},
                 {"choices": [{"message": None}]},
                 {"choices": [{"message": {"content": {"text": "unexpected"}}}]},
                 {"choices": [{"message": {"content": None, "reasoning_content": "private-thought"}}]},
                 {"choices": [{"message": {"content": "   "}}]},
                 {"choices": [{"message": {"refusal": "private-refusal"}, "finish_reason": "stop"}]}]
        for payload in cases:
            scope, transport, _, _ = namespace()
            transport.urlopen.side_effect = None
            transport.urlopen.return_value = io.BytesIO(json.dumps(payload).encode())
            result = scope["deepseek_chat"]([], "test")
            self.assertFalse(result["ok"])
            self.assertEqual(result["request_attempts"], 1)
            self.assertNotIn("private-thought", json.dumps(result))
            self.assertNotIn("private-refusal", json.dumps(result))
            self.assertNotIn("reasoning", result)

    def test_truncated_final_content_remains_incomplete_and_does_not_expose_thinking(self):
        scope, transport, _, _ = namespace(thinking=True)
        transport.urlopen.side_effect = None
        transport.urlopen.return_value = response('{"summary":"partial"}', reason="private-thought", finish="length")
        result = scope["deepseek_chat"]([], "test")
        self.assertFalse(result["ok"])
        self.assertTrue(result["incomplete"])
        self.assertEqual(result["completion_status"], "incomplete")
        self.assertEqual(result["content"], '{"summary":"partial"}')
        self.assertIsNone(result["json"])
        self.assertNotIn("private-thought", json.dumps(result))
        self.assertEqual(transport.urlopen.call_count, 1)

    def test_final_plain_text_is_usable_and_disabled_thinking_is_not_requested(self):
        scope, transport, _, _ = namespace(thinking=False)
        transport.urlopen.side_effect = None
        transport.urlopen.return_value = response(reason="private-thought")
        result = scope["deepseek_chat"]([], "test")
        self.assertTrue(result["ok"])
        self.assertEqual(result["content"], "Public market explanation.")
        self.assertIsNone(result["json"])
        self.assertFalse(result["thinking_requested"])
        self.assertTrue(result["thinking_used"])
        self.assertNotIn("private-thought", json.dumps(result))
        self.assertNotIn("reasoning_content", result)
        sent = json.loads(transport.urlopen.call_args.args[0].data)
        self.assertEqual(sent["model"], "deepseek-v4-pro")
        self.assertEqual(sent["thinking"], {"type": "disabled"})
        self.assertNotIn("reasoning_effort", sent)


    def test_enabled_thinking_is_explicit_and_only_enabled_mode_sends_effort(self):
        scope, transport, _, _ = namespace(thinking=True)
        transport.urlopen.side_effect = None
        transport.urlopen.return_value = response(reason="private-thought")
        result = scope["deepseek_chat"]([], "test")
        self.assertTrue(result["ok"])
        self.assertEqual(transport.urlopen.call_count, 1)
        sent = json.loads(transport.urlopen.call_args.args[0].data)
        self.assertEqual(sent["thinking"], {"type": "enabled"})
        self.assertEqual(sent["reasoning_effort"], "high")
        self.assertNotIn("private-thought", json.dumps(result))


class ProviderSelectionTests(unittest.TestCase):
    def test_disabled_provider_cannot_read_or_use_preserved_env_or_runtime_keys(self):
        scope, transport, environment, reads = namespace("deepseek")
        before_env = deepcopy(environment)
        before_runtime = deepcopy(scope["RUNTIME_AI_KEYS"])
        for names in (("OPENAI_API_KEY",), ("GPT_API_KEY",), ("OPENAI_API_KEY", "GPT_API_KEY")):
            active, value, source = scope["runtime_secret"](*names)
            self.assertEqual(value, "")
            self.assertEqual(source, "disabled")
        result = scope["openai_chat"]([], "legacy-path")
        self.assertEqual(result["request_attempts"], 0)
        self.assertFalse(result["enabled"])
        self.assertIn("未启用", result["error"])
        transport.urlopen.assert_not_called()
        self.assertNotIn("OPENAI_API_KEY", reads)
        self.assertNotIn("GPT_API_KEY", reads)
        self.assertEqual(environment, before_env)
        self.assertEqual(scope["RUNTIME_AI_KEYS"], before_runtime)
        status = scope["runtime_ai_key_status"]()
        rows = {row["id"]: row for row in status["rows"]}
        self.assertFalse(rows["openai"]["enabled"])
        self.assertFalse(rows["openai"]["configured"])
        self.assertEqual(rows["openai"]["source"], "disabled")
        self.assertTrue(rows["deepseek"]["enabled"])
        self.assertTrue(rows["deepseek"]["configured"])
        self.assertNotIn("placeholder", json.dumps(status))

    def test_default_deepseek_runs_once_and_keeps_openai_explicitly_disabled(self):
        scope, transport, _, _ = namespace("deepseek")
        transport.urlopen.side_effect = None
        transport.urlopen.return_value = response()
        result = build_market_ai_projection(scope["market_dual_ai_analysis"](market_tests.MarketAiSnapshotTests().payload()))
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"]["analysis"], "complete")
        self.assertEqual(result["status"]["providers_requested"], ["deepseek"])
        self.assertEqual(result["status"]["providers_completed"], ["deepseek"])
        self.assertEqual(transport.urlopen.call_count, 1)
        self.assertEqual(transport.urlopen.call_args.args[0].full_url, "https://api.deepseek.com/chat/completions")
        self.assertEqual(result["gpt"]["reason"], "disabled")
        self.assertFalse(result["gpt"]["enabled"])
        self.assertEqual(result["gpt"]["request_attempts"], 0)
        self.assertEqual(result["deepseek"]["request_attempts"], 1)

    def test_explicit_legacy_provider_argument_does_not_bypass_disable_gate(self):
        scope, transport, _, _ = namespace("deepseek")
        result = scope["market_dual_ai_analysis"](market_tests.MarketAiSnapshotTests().payload(), providers=("openai",))
        self.assertFalse(result["ok"])
        self.assertEqual(result["gpt"]["reason"], "disabled")
        transport.urlopen.assert_not_called()

    def test_reverse_selection_disables_deepseek_without_removing_its_configuration(self):
        scope, transport, environment, _ = namespace("openai")
        before = deepcopy(environment)
        result = scope["deepseek_chat"]([], "legacy-deepseek")
        self.assertFalse(result["enabled"])
        self.assertEqual(result["request_attempts"], 0)
        transport.urlopen.assert_not_called()
        transport.urlopen.side_effect = None
        transport.urlopen.return_value = response()
        result = scope["market_dual_ai_analysis"](market_tests.MarketAiSnapshotTests().payload())
        self.assertEqual(result["status"]["providers_completed"], ["openai"])
        self.assertEqual(result["deepseek"]["reason"], "disabled")
        self.assertEqual(transport.urlopen.call_count, 1)
        self.assertEqual(environment, before)


if __name__ == "__main__":
    unittest.main()
