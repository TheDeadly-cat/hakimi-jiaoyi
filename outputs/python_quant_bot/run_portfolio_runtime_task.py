from __future__ import annotations

import argparse
import os
from pathlib import Path
import runpy
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
ALLOWED_TARGETS = {
    "run_portfolio_evidence_archive.py",
    "run_portfolio_forward_performance.py",
    "run_portfolio_forward_scheduler.py",
    "run_portfolio_forward_watchdog.py",
}


def resolve_target(name: str) -> Path:
    target_name = Path(str(name or "")).name
    if target_name != str(name or "") or target_name not in ALLOWED_TARGETS:
        raise ValueError("target_not_allowed")
    target = (PROJECT_ROOT / target_name).resolve()
    if target.parent != PROJECT_ROOT or not target.is_file():
        raise ValueError("target_unavailable")
    return target


def validate_task_prefix(value: str) -> str:
    prefix = str(value or "").strip().rstrip("-")
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-"
    if not prefix or len(prefix) > 64 or any(character not in allowed for character in prefix):
        raise ValueError("task_prefix_invalid")
    return prefix


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch one allowlisted portfolio task in an isolated runtime.")
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--task-prefix", default="HakimiTradeV2")
    parser.add_argument("--target", required=True)
    parser.add_argument("target_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    target = resolve_target(args.target)
    task_prefix = validate_task_prefix(args.task_prefix)
    runtime_dir = args.runtime_dir.resolve()
    runtime_dir.mkdir(parents=True, exist_ok=True)
    target_args = list(args.target_args)
    if target_args[:1] == ["--"]:
        target_args = target_args[1:]

    os.environ["HAKIMI_RUNTIME_DIR"] = str(runtime_dir)
    os.environ["HAKIMI_RUNTIME_READ_ONLY"] = "1"
    os.environ["LIVE_TRADING_HARD_BLOCK"] = "true"
    os.environ["HAKIMI_PORTFOLIO_TASK_PREFIX"] = task_prefix
    sys.argv = [str(target), *target_args]
    runpy.run_path(str(target), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
