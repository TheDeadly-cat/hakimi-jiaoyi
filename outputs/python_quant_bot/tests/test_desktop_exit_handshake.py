from __future__ import annotations

import ast

import csv

from email.message import Message

import io

import os

from pathlib import Path

import secrets

import shutil

import sqlite3

import tempfile

from types import SimpleNamespace

from typing import Any

import unittest

from unittest.mock import Mock, patch

SERVER = Path(__file__).resolve().parents[1] / "exchange_terminal" / "server.py"
TREE = ast.parse(SERVER.read_text(encoding="utf-8-sig"))
HANDLER = next(node for node in TREE.body if isinstance(node, ast.ClassDef) and node.name == "ExchangeTerminalHandler")
EXIT_METHOD = next(node for node in HANDLER.body if isinstance(node, ast.FunctionDef) and node.name == "prepare_desktop_exit")

class DesktopExitBoundaryTests(unittest.TestCase):
    def request(self, *, address="127.0.0.1", headers=(), pending=False):
        token = "test-only-private-control-token"
        host = ("[" + address + "]" if ":" in address else address) + ":8765"
        supplied = {name.lower() for name, _ in headers}
        message = Message()
        standard = [("Host", host), ("Origin", "http://" + host),
                    ("X-Hakimi-Desktop-Control", token), ("Sec-Fetch-Site", "same-origin"),
                    ("Content-Type", "application/json"), ("Content-Length", "2")]
        for key, value in [*(item for item in standard if item[0].lower() not in supplied), *headers]:
            message[key] = value
        target = SimpleNamespace(server=SimpleNamespace(server_address=(address, 8765), server_port=8765, shutdown=Mock()),
                                 headers=message, rfile=io.BytesIO(b"{}"), connection=Mock())
        close = Mock(return_value=not pending)
        thread = Mock()
        responses = []
        namespace = {"os": os, "secrets": secrets, "QUANT_WORKSPACE": SimpleNamespace(close=close),
                     "threading": SimpleNamespace(Thread=thread),
                     "json_response": lambda handler, body, status=200: responses.append((status, body))}
        exec(compile(ast.Module(body=[EXIT_METHOD], type_ignores=[]), str(SERVER), "exec"), namespace)
        with patch.dict(os.environ, {"HAKIMI_DESKTOP_CONTROL_TOKEN": token}):
            namespace["prepare_desktop_exit"](target)
        return responses[-1], close, thread, target

    def test_ipv4_and_ipv6_require_the_actual_bound_authority(self):
        for address in ("127.0.0.1", "::1"):
            with self.subTest(address=address):
                response, close, thread, _ = self.request(address=address)
                self.assertEqual(response[0], 200)
                close.assert_called_once()
                thread.return_value.start.assert_called_once()
        response, close, _, _ = self.request(address="::1", headers=[("Host", "127.0.0.1:8765")])
        self.assertEqual(response[0], 403)
        close.assert_not_called()

    def test_duplicate_fetch_site_is_rejected_before_body_or_close(self):
        response, close, thread, handler = self.request(headers=[("Sec-Fetch-Site", "same-origin"), ("Sec-Fetch-Site", "cross-site")])
        self.assertEqual(response[0], 403)
        self.assertEqual(handler.rfile.tell(), 0)
        close.assert_not_called()
        thread.assert_not_called()

    def test_duplicate_or_non_json_content_type_is_rejected(self):
        for headers in ([('Content-Type', 'application/json'), ('Content-Type', 'application/json')],
                        [('Content-Type', 'text/plain')], [('Content-Type', '')]):
            with self.subTest(headers=headers):
                response, close, thread, handler = self.request(headers=headers)
                self.assertEqual(response[0], 400)
                self.assertEqual(handler.rfile.tell(), 0)
                close.assert_not_called()
                thread.assert_not_called()

    def test_live_quant_operation_prevents_shutdown(self):
        response, close, thread, _ = self.request(pending=True)
        self.assertEqual(response[0], 409)
        close.assert_called_once()
        thread.assert_not_called()
