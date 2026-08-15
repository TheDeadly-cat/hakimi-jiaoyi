from __future__ import annotations

import json
import mimetypes
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .config import FRONTEND_DIST, HOST, PORT
from .orchestrator import ORCHESTRATOR
from .providers.registry import PROVIDERS
from .store import STORE


def json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


class StudioRequestHandler(BaseHTTPRequestHandler):
    server_version = "AICollaborationStudio/0.1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._cors_headers()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path == "/api/health":
            self._send_json({
                "ok": True,
                "service": "AI 共创室",
                "providers": PROVIDERS.status(),
            })
            return
        if parsed.path == "/api/bootstrap":
            payload = STORE.bootstrap((query.get("room") or [""])[0])
            self._send_json({**payload, "providers": PROVIDERS.status(), "ok": True})
            return
        room_match = re.fullmatch(r"/api/rooms/([^/]+)", parsed.path)
        if room_match:
            room = STORE.room_snapshot(room_match.group(1))
            if not room:
                self._send_json({"ok": False, "error": "房间不存在"}, HTTPStatus.NOT_FOUND)
                return
            self._send_json({"ok": True, **room, "providers": PROVIDERS.status()})
            return
        self._serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        payload = self._read_json()
        if payload is None:
            return
        if parsed.path == "/api/rooms":
            room = STORE.create_room(
                str(payload.get("title") or ""),
                str(payload.get("objective") or ""),
                str(payload.get("domain") or "open_collaboration"),
            )
            self._send_json({"ok": True, **room}, HTTPStatus.CREATED)
            return
        message_match = re.fullmatch(r"/api/rooms/([^/]+)/messages", parsed.path)
        if message_match:
            content = str(payload.get("content") or "").strip()
            if not content:
                self._send_json({"ok": False, "error": "消息不能为空"}, HTTPStatus.BAD_REQUEST)
                return
            message = STORE.add_message(
                message_match.group(1),
                sender_type="user",
                sender_id="user",
                sender_name="我",
                content=content,
            )
            self._send_json({"ok": True, "message": message}, HTTPStatus.CREATED)
            return
        round_match = re.fullmatch(r"/api/rooms/([^/]+)/rounds/stream", parsed.path)
        if round_match:
            self._stream_round(
                round_match.group(1),
                str(payload.get("objective") or payload.get("content") or ""),
                payload.get("member_ids") if isinstance(payload.get("member_ids"), list) else None,
            )
            return
        self._send_json({"ok": False, "error": "接口不存在"}, HTTPStatus.NOT_FOUND)

    def do_PATCH(self) -> None:
        parsed = urlparse(self.path)
        payload = self._read_json()
        if payload is None:
            return
        member_match = re.fullmatch(r"/api/rooms/([^/]+)/members/([^/]+)", parsed.path)
        if member_match:
            member = STORE.update_member(member_match.group(1), member_match.group(2), payload)
            if not member:
                self._send_json({"ok": False, "error": "成员不存在"}, HTTPStatus.NOT_FOUND)
                return
            self._send_json({"ok": True, "member": member})
            return
        self._send_json({"ok": False, "error": "接口不存在"}, HTTPStatus.NOT_FOUND)

    def _stream_round(self, room_id: str, objective: str, member_ids: list[str] | None) -> None:
        self.send_response(HTTPStatus.OK)
        self._cors_headers()
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-transform")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        try:
            for event in ORCHESTRATOR.run_round(room_id, objective, member_ids):
                self.wfile.write(json_bytes(event) + b"\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as exc:
            try:
                self.wfile.write(json_bytes({"type": "error", "error": str(exc)}) + b"\n")
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                return

    def _read_json(self) -> dict[str, Any] | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > 128_000:
            self._send_json({"ok": False, "error": "请求内容为空或过大"}, HTTPStatus.BAD_REQUEST)
            return None
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self._send_json({"ok": False, "error": "JSON 格式无效"}, HTTPStatus.BAD_REQUEST)
            return None
        if not isinstance(payload, dict):
            self._send_json({"ok": False, "error": "请求必须是 JSON 对象"}, HTTPStatus.BAD_REQUEST)
            return None
        return payload

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json_bytes(payload)
        self.send_response(status)
        self._cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors_headers(self) -> None:
        origin = self.headers.get("Origin", "")
        if origin.startswith("http://127.0.0.1:") or origin.startswith("http://localhost:"):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

    def _serve_static(self, request_path: str) -> None:
        if not FRONTEND_DIST.is_dir():
            self._send_json({"ok": False, "error": "前端尚未构建，请先运行 npm.cmd run build"}, HTTPStatus.SERVICE_UNAVAILABLE)
            return
        relative = request_path.lstrip("/") or "index.html"
        candidate = (FRONTEND_DIST / relative).resolve()
        if FRONTEND_DIST.resolve() not in candidate.parents and candidate != FRONTEND_DIST.resolve():
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not candidate.is_file():
            candidate = FRONTEND_DIST / "index.html"
        body = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8" if content_type.startswith("text/") else content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache" if candidate.name == "index.html" else "public, max-age=31536000, immutable")
        self.end_headers()
        self.wfile.write(body)


def run_server(host: str = HOST, port: int = PORT) -> None:
    server = ThreadingHTTPServer((host, port), StudioRequestHandler)
    print(f"AI 共创室运行于 http://{host}:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

