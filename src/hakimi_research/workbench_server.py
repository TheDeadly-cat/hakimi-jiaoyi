"""Loopback-only HTTP presentation for explicit local research operations."""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import json
import os
from pathlib import Path
import secrets
from urllib.parse import parse_qs, urlsplit

from .documents import parse_document
from .workbench_service import Workbench

MAX_REQUEST = 100 * 1024 * 1024


def create_server(workspace, port=0):
    service, token = Workbench(workspace), secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass  # URLs, local paths, and session tokens do not enter logs.

        def _headers(self, status, content_type, length):
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(length))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy',
                "default-src 'none'; script-src 'nonce-" + token + "'; style-src 'unsafe-inline'; "
                "connect-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
            self.end_headers()

        def _json(self, status, value):
            raw = json.dumps(value, ensure_ascii=False, allow_nan=False, default=str).encode('utf-8')
            self._headers(status, 'application/json; charset=utf-8', len(raw))
            self.wfile.write(raw)

        def _boundary(self, *, api=False):
            origin = 'http://127.0.0.1:' + str(self.server.server_port)
            if self.headers.get('Host') != origin.split('://', 1)[1]:
                raise ValueError('local_host_required')
            if self.headers.get('Origin') not in (None, origin):
                raise ValueError('same_origin_required')
            if self.headers.get('Sec-Fetch-Site') not in (None, 'none', 'same-origin'):
                raise ValueError('cross_site_request_refused')
            if api and not secrets.compare_digest(self.headers.get('X-Hakimi-Token', ''), token):
                raise ValueError('session_token_required')

        def do_GET(self):
            try:
                parsed = urlsplit(self.path)
                self._boundary(api=parsed.path.startswith('/api/'))
                if parsed.path == '/':
                    raw = files('hakimi_research').joinpath('resources/workbench.html').read_text(encoding='utf-8')
                    raw = raw.replace('__SESSION_TOKEN__', token).replace('<script>', '<script nonce="' + token + '">').encode('utf-8')
                    self._headers(200, 'text/html; charset=utf-8', len(raw))
                    self.wfile.write(raw)
                    return
                args = parse_qs(parsed.query)
                if parsed.path == '/api/state':
                    result = service.state()
                elif parsed.path == '/api/run':
                    result = service.run_view(args['ref'][0])
                elif parsed.path == '/api/account':
                    result = service.account_view(args['ref'][0])
                elif parsed.path == '/api/watch':
                    result = service.watch_view(args['ref'][0])
                else:
                    self._json(404, dict(ok=False, error='not_found'))
                    return
                self._json(200, result)
            except (ValueError, OSError, KeyError, TypeError) as exc:
                self._json(400, dict(ok=False, error=str(exc)))

        def do_POST(self):
            try:
                self._boundary(api=True)
                if self.path != '/api/action' or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    raise ValueError('json_action_required')
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= MAX_REQUEST or self.headers.get('Transfer-Encoding'):
                    raise ValueError('request_length_invalid')
                self.connection.settimeout(30)
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError('request_body_incomplete')
                result = service.action(parse_document(raw, maximum_bytes=MAX_REQUEST))
                self._json(200, dict(ok=True, result=result))
            except (ValueError, OSError, KeyError, TypeError) as exc:
                self._json(400, dict(ok=False, error=str(exc), automatic_retry=False))

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = False
    server.workbench = service
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description='哈基米交易：正式研究工作台（无账户/订单连接）')
    parser.add_argument('--workspace', type=Path, default=Path.home() / '.hakimi-trade-workbench')
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--open-browser', action='store_true')
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error('port must be 0..65535')
    server = create_server(args.workspace, args.port)
    url = 'http://127.0.0.1:' + str(server.server_port) + '/'
    print(json.dumps(dict(url=url, port=server.server_port, pid=os.getpid(), parent_pid=os.getppid(),
                         engine='hakimi_research')), flush=True)
    if args.open_browser:
        import webbrowser
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.workbench.close()
        server.server_close()


if __name__ == '__main__':
    main()
