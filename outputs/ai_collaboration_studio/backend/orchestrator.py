from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

from .providers.registry import PROVIDERS, ProviderRegistry
from .store import STORE, StudioStore


DOMAIN_RULES = {
    "sports_research": "这是体育研究房间。必须说明信息缺口和不确定性，不得承诺赛果，不得替用户下注或执行资金动作。",
    "market_research": "这是市场研究房间。只能整理证据、反证和观察条件，不得执行交易或要求绕过风控。",
    "project_research": "这是项目研究房间。必须区分事实、假设和待验证事项，并关注资源、成本和失败路径。",
    "open_collaboration": "这是开放共创房间。要提出不同方案并帮助形成下一步，但不要为了达成一致而掩盖真实分歧。",
}


class DiscussionOrchestrator:
    def __init__(self, store: StudioStore = STORE, providers: ProviderRegistry = PROVIDERS) -> None:
        self.store = store
        self.providers = providers

    def run_round(
        self,
        room_id: str,
        objective: str,
        member_ids: list[str] | None = None,
    ) -> Iterator[dict[str, Any]]:
        snapshot = self.store.room_snapshot(room_id)
        if not snapshot:
            yield {"type": "error", "error": "房间不存在"}
            return
        room = snapshot["room"]
        clean_objective = objective.strip() or room.get("objective") or "继续当前讨论并给出下一步。"
        members = self.store.enabled_members(room_id, member_ids)
        if not members:
            yield {"type": "error", "error": "当前房间没有启用的 AI 成员"}
            return

        round_row = self.store.create_round(room_id, clean_objective)
        user_message = self.store.add_message(
            room_id,
            sender_type="user",
            sender_id="user",
            sender_name="我",
            content=clean_objective,
            round_id=round_row["id"],
        )
        round_started_delivered = False
        try:
            yield {
                "type": "round_started",
                "round": round_row,
                "user_message": user_message,
                "members": [self._public_member(member) for member in members],
            }
            round_started_delivered = True
        finally:
            if not round_started_delivered:
                self.store.complete_round(round_row["id"], "CANCELLED")

        failures = 0
        previous_name = "我"
        finalized = False
        try:
            for order, member in enumerate(members, start=1):
                public_member = self._public_member(member)
                yield {"type": "speaker_started", "order": order, "member": public_member}
                started = time.perf_counter()
                provider = self.providers.get(member.get("provider", "openai"))
                if not provider:
                    failures += 1
                    error = f"模型适配器 {member.get('provider')} 尚未接入"
                    failure_message = self._failure_message(room_id, round_row["id"], member, error)
                    yield {
                        "type": "speaker_failed",
                        "order": order,
                        "member": public_member,
                        "error": error,
                        "message": failure_message,
                    }
                    continue

                transcript = self.store.recent_messages(room_id, 36)
                try:
                    response = provider.generate(
                        instructions=self._instructions(room, member, previous_name),
                        input_text=self._input_text(room, clean_objective, transcript),
                        model=str(member.get("model") or ""),
                    )
                except Exception as exc:
                    failures += 1
                    error = f"模型调用异常：{exc}"
                    failure_message = self._failure_message(room_id, round_row["id"], member, error)
                    yield {
                        "type": "speaker_failed",
                        "order": order,
                        "member": public_member,
                        "error": error,
                        "message": failure_message,
                        "elapsed_ms": int((time.perf_counter() - started) * 1000),
                    }
                    continue

                elapsed_ms = int((time.perf_counter() - started) * 1000)
                if not response.ok:
                    failures += 1
                    error = response.error or "模型调用失败"
                    failure_message = self._failure_message(room_id, round_row["id"], member, error)
                    yield {
                        "type": "speaker_failed",
                        "order": order,
                        "member": public_member,
                        "error": error,
                        "message": failure_message,
                        "elapsed_ms": elapsed_ms,
                    }
                    continue

                message = self.store.add_message(
                    room_id,
                    sender_type="ai",
                    sender_id=member["id"],
                    sender_name=member["name"],
                    identity=member.get("identity", ""),
                    provider=response.provider,
                    model=response.model,
                    content=response.content,
                    reply_to=previous_name,
                    round_id=round_row["id"],
                )
                previous_name = member["name"]
                yield {
                    "type": "message",
                    "order": order,
                    "member": public_member,
                    "message": message,
                    "usage": response.usage,
                    "elapsed_ms": elapsed_ms,
                }

            final_status = "PARTIAL" if failures else "COMPLETED"
            self.store.complete_round(round_row["id"], final_status)
            finalized = True
            yield {
                "type": "round_completed",
                "round_id": round_row["id"],
                "status": final_status,
                "failures": failures,
                "completed": len(members) - failures,
            }
        finally:
            if not finalized:
                self.store.complete_round(round_row["id"], "CANCELLED")

    def _instructions(self, room: dict[str, Any], member: dict[str, Any], previous_name: str) -> str:
        domain_rule = DOMAIN_RULES.get(room.get("domain"), DOMAIN_RULES["open_collaboration"])
        return (
            f"你正在 AI 共创室的群聊中，以「{member['name']}」身份发言。\n"
            f"身份：{member.get('identity') or '协作成员'}。\n"
            f"职责与边界：{member.get('instructions') or '基于上下文提供清晰、有根据的观点。'}\n"
            f"{domain_rule}\n"
            "你不是总结接口，也不是独立报告生成器。你的输出会直接作为一条群聊消息显示。"
            f"如果前序发言存在，第一段要自然回应或质疑「{previous_name}」，不要假装没有读过。"
            "明确区分已知事实、合理推断和待验证信息。允许不同意，但必须说明原因和修正方向。"
            "直接输出中文正文，2到5段，不要输出JSON，不要使用Markdown标题，不要重复自己的身份介绍。"
        )

    @staticmethod
    def _input_text(room: dict[str, Any], objective: str, transcript: list[dict[str, Any]]) -> str:
        lines = []
        for message in transcript:
            sender = message.get("sender_name") or "未知成员"
            identity = message.get("identity") or ""
            label = f"{sender}（{identity}）" if identity else sender
            lines.append(f"[{label}] {message.get('content', '')}")
        transcript_text = "\n\n".join(lines)[-18000:]
        return (
            f"房间：{room.get('title')}\n"
            f"长期目标：{room.get('objective')}\n"
            f"本轮目标：{objective}\n\n"
            f"群聊记录：\n{transcript_text}\n\n"
            "现在轮到你发言。请推进讨论，并给出至少一个具体的下一步或需要核验的问题。"
        )

    @staticmethod
    def _public_member(member: dict[str, Any]) -> dict[str, Any]:
        return {
            key: member.get(key)
            for key in ["id", "name", "identity", "provider", "model", "position", "enabled", "avatar_color"]
        }

    def _failure_message(
        self,
        room_id: str,
        round_id: str,
        member: dict[str, Any],
        error: str,
    ) -> dict[str, Any]:
        return self.store.add_message(
            room_id,
            sender_type="system",
            sender_id=member["id"],
            sender_name="系统",
            identity="轮次状态",
            content=f"{member['name']} 未完成发言：{error}",
            round_id=round_id,
        )


ORCHESTRATOR = DiscussionOrchestrator()
