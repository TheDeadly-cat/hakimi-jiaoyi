from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from contextlib import closing
from pathlib import Path
from typing import Any

from .config import DATABASE_PATH, OPENAI_MODEL


def now_ms() -> int:
    return int(time.time() * 1000)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


DEFAULT_MEMBERS = [
    {
        "name": "战略主持人",
        "identity": "主持人与目标守门人",
        "instructions": "先澄清目标和评价标准，组织分歧，推动大家形成下一步，不要替其他成员包办全部工作。",
        "avatar_color": "#2563eb",
    },
    {
        "name": "事实研究员",
        "identity": "事实、证据与假设核验",
        "instructions": "区分事实、推断和未知信息，指出需要补充的证据，不编造来源。",
        "avatar_color": "#16835f",
    },
    {
        "name": "反方审查员",
        "identity": "反证、失败路径与风险",
        "instructions": "优先寻找反证、隐含假设和失败路径；批评必须具体并给出修正方向。",
        "avatar_color": "#c44545",
    },
    {
        "name": "方案架构师",
        "identity": "结构设计与落地路径",
        "instructions": "把讨论转成清晰结构、方案选项和可执行步骤，同时保留尚未解决的分歧。",
        "avatar_color": "#7c5ac7",
    },
]


class StudioStore:
    def __init__(self, path: Path = DATABASE_PATH) -> None:
        self.path = path
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=20)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        with self._lock, closing(self._connect()) as connection, connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS rooms (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    objective TEXT NOT NULL DEFAULT '',
                    domain TEXT NOT NULL DEFAULT 'open_collaboration',
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS members (
                    id TEXT PRIMARY KEY,
                    room_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    identity TEXT NOT NULL DEFAULT '',
                    instructions TEXT NOT NULL DEFAULT '',
                    provider TEXT NOT NULL DEFAULT 'openai',
                    model TEXT NOT NULL DEFAULT '',
                    position INTEGER NOT NULL DEFAULT 0,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    avatar_color TEXT NOT NULL DEFAULT '#2563eb',
                    created_at INTEGER NOT NULL,
                    FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS rounds (
                    id TEXT PRIMARY KEY,
                    room_id TEXT NOT NULL,
                    objective TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'RUNNING',
                    created_at INTEGER NOT NULL,
                    completed_at INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    room_id TEXT NOT NULL,
                    round_id TEXT NOT NULL DEFAULT '',
                    sender_type TEXT NOT NULL,
                    sender_id TEXT NOT NULL DEFAULT '',
                    sender_name TEXT NOT NULL,
                    identity TEXT NOT NULL DEFAULT '',
                    provider TEXT NOT NULL DEFAULT '',
                    model TEXT NOT NULL DEFAULT '',
                    content TEXT NOT NULL,
                    reply_to TEXT NOT NULL DEFAULT '',
                    created_at INTEGER NOT NULL,
                    FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_members_room_position ON members(room_id, position);
                CREATE INDEX IF NOT EXISTS idx_messages_room_time ON messages(room_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_rounds_room_time ON rounds(room_id, created_at DESC);
                """
            )
            room_count = connection.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
            if room_count == 0:
                self._seed(connection)

    def _seed(self, connection: sqlite3.Connection) -> None:
        timestamp = now_ms()
        rooms = [
            ("room_plan", "方案共创会", "提出三个方向不同的方案框架，明确各自优势、风险和落地条件。", "open_collaboration"),
            ("room_sports", "体育赛事研究", "从数据、战术和不确定性出发研究赛事，不代替用户做投注决定。", "sports_research"),
            ("room_project", "项目可行性讨论", "核验需求、资源、商业约束与失败路径。", "project_research"),
            ("room_market", "股票观察组", "整理事实、结构、反证和观察条件，不执行交易。", "market_research"),
        ]
        connection.executemany(
            "INSERT INTO rooms(id,title,objective,domain,created_at,updated_at) VALUES(?,?,?,?,?,?)",
            [(room_id, title, objective, domain, timestamp, timestamp) for room_id, title, objective, domain in rooms],
        )
        for room_id, *_rest in rooms:
            self._insert_default_members(connection, room_id, timestamp)
        seed_messages = [
            ("user", "user", "我", "", "", "", "结合我们之前的讨论，提出三个方向不同的方案框架，并说明各自的核心优势与主要风险。", ""),
            ("ai", "seed_host", "战略主持人", "主持人与目标守门人", "openai", OPENAI_MODEL, "我先把评价维度固定下来：目标契合度、资源可行性、落地速度和长期价值。接下来每个方向都应使用同一组维度比较。", "我"),
            ("ai", "seed_researcher", "事实研究员", "事实、证据与假设核验", "openai", OPENAI_MODEL, "补充一个约束：当前缺少真实用户样本和资源上限。任何方案结论都要标注哪些是事实、哪些只是待验证假设。", "战略主持人"),
            ("ai", "seed_critic", "反方审查员", "反证、失败路径与风险", "openai", OPENAI_MODEL, "我同意先统一评价维度，但反对过早收敛。至少保留一个低成本方案作为基线，否则容易把复杂度误当成价值。", "事实研究员"),
        ]
        for index, row in enumerate(seed_messages):
            sender_type, sender_id, name, identity, provider, model, content, reply_to = row
            connection.execute(
                """INSERT INTO messages(
                    id,room_id,round_id,sender_type,sender_id,sender_name,identity,provider,model,content,reply_to,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (new_id("msg"), "room_plan", "", sender_type, sender_id, name, identity, provider, model, content, reply_to, timestamp + index),
            )

    def _insert_default_members(self, connection: sqlite3.Connection, room_id: str, timestamp: int | None = None) -> None:
        created_at = timestamp or now_ms()
        for position, member in enumerate(DEFAULT_MEMBERS, start=1):
            connection.execute(
                """INSERT INTO members(
                    id,room_id,name,identity,instructions,provider,model,position,enabled,avatar_color,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    new_id("member"), room_id, member["name"], member["identity"], member["instructions"],
                    "openai", OPENAI_MODEL, position, 1, member["avatar_color"], created_at,
                ),
            )

    def list_rooms(self) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT r.*,
                       (SELECT COUNT(*) FROM members m WHERE m.room_id=r.id AND m.enabled=1) AS member_count,
                       (SELECT MAX(created_at) FROM messages x WHERE x.room_id=r.id) AS last_message_at
                FROM rooms r
                ORDER BY COALESCE(last_message_at, r.updated_at) DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def room_snapshot(self, room_id: str) -> dict[str, Any] | None:
        with closing(self._connect()) as connection:
            room = connection.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()
            if not room:
                return None
            members = connection.execute(
                "SELECT * FROM members WHERE room_id=? ORDER BY position, created_at",
                (room_id,),
            ).fetchall()
            messages = connection.execute(
                """SELECT * FROM (
                    SELECT * FROM messages WHERE room_id=? ORDER BY created_at DESC LIMIT 120
                ) ORDER BY created_at""",
                (room_id,),
            ).fetchall()
            latest_round = connection.execute(
                "SELECT * FROM rounds WHERE room_id=? ORDER BY created_at DESC LIMIT 1",
                (room_id,),
            ).fetchone()
        return {
            "room": dict(room),
            "members": [self._member_dict(row) for row in members],
            "messages": [dict(row) for row in messages],
            "latest_round": dict(latest_round) if latest_round else None,
        }

    def bootstrap(self, room_id: str = "") -> dict[str, Any]:
        rooms = self.list_rooms()
        active_id = room_id if any(row["id"] == room_id for row in rooms) else (rooms[0]["id"] if rooms else "")
        return {
            "rooms": rooms,
            "active": self.room_snapshot(active_id) if active_id else None,
        }

    def create_room(self, title: str, objective: str, domain: str = "open_collaboration") -> dict[str, Any]:
        room_id = new_id("room")
        timestamp = now_ms()
        with self._lock, closing(self._connect()) as connection, connection:
            connection.execute(
                "INSERT INTO rooms(id,title,objective,domain,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                (room_id, title.strip()[:80] or "未命名房间", objective.strip()[:2000], domain.strip()[:60], timestamp, timestamp),
            )
            self._insert_default_members(connection, room_id, timestamp)
        return self.room_snapshot(room_id) or {}

    def update_member(self, room_id: str, member_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        allowed = {
            "name": str(payload.get("name") or "").strip()[:40],
            "identity": str(payload.get("identity") or "").strip()[:120],
            "instructions": str(payload.get("instructions") or "").strip()[:3000],
            "provider": str(payload.get("provider") or "openai").strip().lower()[:40],
            "model": str(payload.get("model") or "").strip()[:100],
            "enabled": 1 if payload.get("enabled", True) else 0,
        }
        with self._lock, closing(self._connect()) as connection, connection:
            connection.execute(
                """UPDATE members SET name=?,identity=?,instructions=?,provider=?,model=?,enabled=?
                   WHERE id=? AND room_id=?""",
                (*allowed.values(), member_id, room_id),
            )
            row = connection.execute("SELECT * FROM members WHERE id=? AND room_id=?", (member_id, room_id)).fetchone()
        return self._member_dict(row) if row else None

    def add_message(
        self,
        room_id: str,
        *,
        sender_type: str,
        sender_name: str,
        content: str,
        sender_id: str = "",
        identity: str = "",
        provider: str = "",
        model: str = "",
        reply_to: str = "",
        round_id: str = "",
    ) -> dict[str, Any]:
        message = {
            "id": new_id("msg"),
            "room_id": room_id,
            "round_id": round_id,
            "sender_type": sender_type,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "identity": identity,
            "provider": provider,
            "model": model,
            "content": content.strip()[:30000],
            "reply_to": reply_to,
            "created_at": now_ms(),
        }
        with self._lock, closing(self._connect()) as connection, connection:
            connection.execute(
                """INSERT INTO messages(
                    id,room_id,round_id,sender_type,sender_id,sender_name,identity,provider,model,content,reply_to,created_at
                ) VALUES(:id,:room_id,:round_id,:sender_type,:sender_id,:sender_name,:identity,:provider,:model,:content,:reply_to,:created_at)""",
                message,
            )
            connection.execute("UPDATE rooms SET updated_at=? WHERE id=?", (message["created_at"], room_id))
        return message

    def recent_messages(self, room_id: str, limit: int = 32) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """SELECT * FROM (
                    SELECT * FROM messages WHERE room_id=? ORDER BY created_at DESC LIMIT ?
                ) ORDER BY created_at""",
                (room_id, max(1, min(limit, 80))),
            ).fetchall()
        return [dict(row) for row in rows]

    def enabled_members(self, room_id: str, member_ids: list[str] | None = None) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM members WHERE room_id=? AND enabled=1 ORDER BY position, created_at",
                (room_id,),
            ).fetchall()
        members = [self._member_dict(row) for row in rows]
        if member_ids:
            wanted = set(member_ids)
            members = [member for member in members if member["id"] in wanted]
        return members

    def create_round(self, room_id: str, objective: str) -> dict[str, Any]:
        round_row = {
            "id": new_id("round"),
            "room_id": room_id,
            "objective": objective.strip()[:4000],
            "status": "RUNNING",
            "created_at": now_ms(),
            "completed_at": 0,
        }
        with self._lock, closing(self._connect()) as connection, connection:
            connection.execute(
                "INSERT INTO rounds(id,room_id,objective,status,created_at,completed_at) VALUES(:id,:room_id,:objective,:status,:created_at,:completed_at)",
                round_row,
            )
        return round_row

    def complete_round(self, round_id: str, status: str = "COMPLETED") -> None:
        with self._lock, closing(self._connect()) as connection, connection:
            connection.execute(
                "UPDATE rounds SET status=?,completed_at=? WHERE id=?",
                (status, now_ms(), round_id),
            )

    @staticmethod
    def _member_dict(row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        data["enabled"] = bool(data.get("enabled"))
        return data


STORE = StudioStore()
