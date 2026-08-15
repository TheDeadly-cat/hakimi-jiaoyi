from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.orchestrator import DiscussionOrchestrator
from backend.providers.base import ProviderResponse
from backend.providers.openai_provider import _http_error_text
from backend.store import StudioStore


class FakeProvider:
    provider_id = "openai"

    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def status(self) -> dict[str, object]:
        return {"id": "openai", "configured": True}

    def generate(self, *, instructions: str, input_text: str, model: str = "") -> ProviderResponse:
        self.calls.append({"instructions": instructions, "input_text": input_text, "model": model})
        return ProviderResponse(
            ok=True,
            provider="openai",
            model=model or "fake-model",
            content=f"第 {len(self.calls)} 位成员发言，并回应前序观点。",
        )


class FakeRegistry:
    def __init__(self, provider: FakeProvider) -> None:
        self.provider = provider

    def get(self, _provider_id: str) -> FakeProvider:
        return self.provider


class FailingProvider(FakeProvider):
    def generate(self, *, instructions: str, input_text: str, model: str = "") -> ProviderResponse:
        return ProviderResponse(ok=False, provider="openai", model=model, error="测试配额不足")


class OrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = StudioStore(Path(self.temp_dir.name) / "studio.sqlite3")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_members_speak_in_order_and_read_prior_ai_message(self) -> None:
        provider = FakeProvider()
        orchestrator = DiscussionOrchestrator(self.store, FakeRegistry(provider))

        events = list(orchestrator.run_round("room_plan", "讨论一个可落地的新方案"))

        messages = [event for event in events if event["type"] == "message"]
        self.assertEqual(len(messages), 4)
        self.assertEqual([event["order"] for event in messages], [1, 2, 3, 4])
        self.assertIn("第 1 位成员发言", provider.calls[1]["input_text"])
        self.assertIn("战略主持人", provider.calls[1]["instructions"])
        self.assertEqual(events[-1]["type"], "round_completed")
        self.assertEqual(events[-1]["status"], "COMPLETED")

    def test_room_and_identity_changes_are_persistent(self) -> None:
        created = self.store.create_room("新项目", "研究目标", "project_research")
        member = created["members"][0]

        updated = self.store.update_member(created["room"]["id"], member["id"], {
            **member,
            "name": "需求审查员",
            "identity": "检查真实需求",
            "instructions": "寻找伪需求和缺失用户证据。",
        })
        reloaded = self.store.room_snapshot(created["room"]["id"])

        self.assertEqual(updated["name"], "需求审查员")
        self.assertEqual(reloaded["members"][0]["identity"], "检查真实需求")

    def test_openai_quota_error_is_user_readable(self) -> None:
        raw = '{"error":{"message":"quota details","code":"insufficient_quota"}}'
        self.assertEqual(_http_error_text(raw, 429), "OpenAI 配额不足，请检查该项目的余额或账单设置。")

    def test_closed_stream_marks_round_cancelled(self) -> None:
        orchestrator = DiscussionOrchestrator(self.store, FakeRegistry(FakeProvider()))
        events = orchestrator.run_round("room_plan", "先暂停这一轮")

        self.assertEqual(next(events)["type"], "round_started")
        events.close()

        snapshot = self.store.room_snapshot("room_plan")
        self.assertEqual(snapshot["latest_round"]["status"], "CANCELLED")

    def test_provider_failures_are_persisted_as_system_events(self) -> None:
        orchestrator = DiscussionOrchestrator(self.store, FakeRegistry(FailingProvider()))
        member_id = self.store.room_snapshot("room_plan")["members"][0]["id"]

        events = list(orchestrator.run_round("room_plan", "验证失败证据链", [member_id]))
        snapshot = self.store.room_snapshot("room_plan")
        system_messages = [message for message in snapshot["messages"] if message["sender_type"] == "system"]

        self.assertEqual(events[-1]["status"], "PARTIAL")
        self.assertEqual(len(system_messages), 1)
        self.assertIn("未完成发言：测试配额不足", system_messages[0]["content"])


if __name__ == "__main__":
    unittest.main()
