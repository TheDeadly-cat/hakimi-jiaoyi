from __future__ import annotations

import argparse
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


APP_NAME = "哈基米交易 v2"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def wait_for_server(host: str, port: int, timeout_seconds: float = 12.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def run_terminal_server(host: str, port: int) -> None:
    root = project_root()
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "exchange_terminal"))
    from exchange_terminal import server as terminal_server

    previous_argv = sys.argv[:]
    try:
        sys.argv = [
            "hakimi_trade_server",
            "--host",
            host,
            "--port",
            str(port),
            "--no-browser",
        ]
        terminal_server.main()
    finally:
        sys.argv = previous_argv


def open_desktop_window(url: str) -> None:
    try:
        import webview  # type: ignore

        webview.create_window(APP_NAME, url, width=1440, height=930, min_size=(1180, 760))
        webview.start()
    except Exception:
        webbrowser.open(url)
        print(f"{APP_NAME} is running at {url}")
        print("Close this window to stop the desktop launcher.")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    url = f"http://{args.host}:{args.port}/"
    if not wait_for_server(args.host, args.port, timeout_seconds=0.6):
        thread = threading.Thread(target=run_terminal_server, args=(args.host, args.port), daemon=True)
        thread.start()
        if not wait_for_server(args.host, args.port):
            raise SystemExit(f"{APP_NAME} failed to start on {url}")
    open_desktop_window(url)


if __name__ == "__main__":
    main()
