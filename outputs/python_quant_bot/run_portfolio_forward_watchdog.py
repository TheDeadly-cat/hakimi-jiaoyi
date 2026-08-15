from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any

from exchange_terminal.services.forward_artifact_io import (
    MAX_PORTFOLIO_FORWARD_CONTROL_ARTIFACT_BYTES,
    MAX_PORTFOLIO_FORWARD_STATUS_ARTIFACT_BYTES,
    read_forward_json_artifact,
)
from exchange_terminal.services.portfolio_forward import load_active_portfolio_candidate
from exchange_terminal.services.portfolio_forward_scheduler import (
    DEFAULT_SCHEDULER_STATUS_FILE,
    load_forward_scheduler_status,
)
from exchange_terminal.services.portfolio_forward_watchdog import (
    BACKUP_TASK_NAME,
    DEFAULT_WATCHDOG_ALERT_FILE,
    DEFAULT_WATCHDOG_STATUS_FILE,
    OBSERVATION_TASK_NAME,
    PERFORMANCE_TASK_NAME,
    build_portfolio_forward_watchdog_status,
    record_portfolio_forward_watchdog_status,
)
from exchange_terminal.services.portfolio_evidence_archive import (
    DEFAULT_ARCHIVE_DIRECTORY,
    DEFAULT_BACKUP_STATUS_FILE,
    verify_portfolio_backup_status,
    verify_portfolio_evidence_archive,
)
PROJECT_ROOT = Path(__file__).resolve().parent
RUNTIME_DIR = Path(os.environ.get("HAKIMI_RUNTIME_DIR") or PROJECT_ROOT / "runtime")
REPORT_DIR = RUNTIME_DIR / "reports"
MAX_PORTFOLIO_FORWARD_RUNNER_ARTIFACT_BYTES = MAX_PORTFOLIO_FORWARD_CONTROL_ARTIFACT_BYTES


def _read_json(
    path: Path,
    *,
    byte_limit: int = MAX_PORTFOLIO_FORWARD_RUNNER_ARTIFACT_BYTES,
) -> dict[str, Any]:
    try:
        artifact = read_forward_json_artifact(
            path,
            byte_limit=byte_limit,
            size_limit_blocker="portfolio_forward_runner_artifact_size_limit_exceeded",
        )
    except (MemoryError, OSError, RecursionError, UnicodeError, ValueError):
        return {}
    return dict(artifact.payload) if artifact.status == "PASS" else {}


def _probe_windows_tasks(task_names: tuple[str, ...], timeout_seconds: float = 10.0) -> dict[str, Any]:
    if os.name != "nt":
        return {"status": "BLOCK", "error": "windows_task_scheduler_unavailable", "tasks": {}}
    names = ",".join(f"'{name.replace("'", "''")}'" for name in task_names)
    script = f"""
$ErrorActionPreference = 'Stop'
$result = @{{}}
foreach ($name in @({names})) {{
  $task = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
  if (-not $task) {{
    $result[$name] = @{{ installed = $false; enabled = $false; state = 'Missing'; last_task_result = -1; last_run_at_ms = 0; next_run_at_ms = 0 }}
    continue
  }}
  $info = Get-ScheduledTaskInfo -TaskName $name
  $lastRun = if ($info.LastRunTime -and $info.LastRunTime.Year -gt 1900) {{ ([DateTimeOffset]$info.LastRunTime).ToUnixTimeMilliseconds() }} else {{ 0 }}
  $nextRun = if ($info.NextRunTime -and $info.NextRunTime.Year -gt 1900) {{ ([DateTimeOffset]$info.NextRunTime).ToUnixTimeMilliseconds() }} else {{ 0 }}
  $result[$name] = @{{
    installed = $true
    enabled = [bool]$task.Settings.Enabled
    state = [string]$task.State
    last_task_result = [int64]$info.LastTaskResult
    last_run_at_ms = [int64]$lastRun
    next_run_at_ms = [int64]$nextRun
  }}
}}
@{{ status = 'PASS'; tasks = $result }} | ConvertTo-Json -Compress -Depth 6
"""
    creation_flags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(float(timeout_seconds), 1.0),
            creationflags=creation_flags,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "BLOCK", "error": type(exc).__name__, "tasks": {}}
    if completed.returncode != 0:
        return {
            "status": "BLOCK",
            "error": str(completed.stderr or "task_probe_failed")[-500:],
            "tasks": {},
        }
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"status": "BLOCK", "error": "task_probe_output_invalid", "tasks": {}}
    return payload if isinstance(payload, dict) else {
        "status": "BLOCK",
        "error": "task_probe_output_not_object",
        "tasks": {},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the research-only portfolio forward task chain.")
    parser.add_argument(
        "--task-prefix",
        default=os.environ.get("HAKIMI_PORTFOLIO_TASK_PREFIX") or "HakimiTradeV2",
    )
    parser.add_argument("--task-probe-timeout", type=float, default=10.0)
    args = parser.parse_args()
    task_prefix = str(args.task_prefix or "").strip().rstrip("-")
    if not task_prefix or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-" for character in task_prefix):
        parser.error("--task-prefix must contain only letters, digits, dot, underscore, or hyphen")
    observation_task_name = f"{task_prefix}-PortfolioForwardObservation"
    performance_task_name = f"{task_prefix}-PortfolioForwardPerformance"
    backup_task_name = f"{task_prefix}-PortfolioForwardBackup"
    task_names = (observation_task_name, performance_task_name, backup_task_name)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    current_ms = time.time_ns() // 1_000_000
    active = load_active_portfolio_candidate(REPORT_DIR)
    candidate_hash = str((active.get("candidate") or {}).get("candidate_hash") or "")
    prefix = candidate_hash[:12] or "unknown"
    scheduler = load_forward_scheduler_status(
        REPORT_DIR / DEFAULT_SCHEDULER_STATUS_FILE,
        now_ms=current_ms,
    )
    observation = _read_json(
        REPORT_DIR / f"portfolio_forward_status_{prefix}.json",
        byte_limit=MAX_PORTFOLIO_FORWARD_STATUS_ARTIFACT_BYTES,
    )
    performance = _read_json(
        REPORT_DIR / f"portfolio_forward_performance_status_{prefix}.json",
        byte_limit=MAX_PORTFOLIO_FORWARD_STATUS_ARTIFACT_BYTES,
    )
    backup = _read_json(
        REPORT_DIR / DEFAULT_BACKUP_STATUS_FILE,
        byte_limit=MAX_PORTFOLIO_FORWARD_CONTROL_ARTIFACT_BYTES,
    )
    backup_verification = verify_portfolio_backup_status(backup)
    backup_archive_verification: dict[str, Any] = {
        "status": "BLOCK",
        "blockers": ["backup_archive_unavailable"],
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    if backup_verification.get("status") == "PASS" and backup.get("status") == "PASS":
        try:
            bundle = Path(str(backup.get("bundle_path") or "")).resolve()
            archive_root = (RUNTIME_DIR / "backups" / DEFAULT_ARCHIVE_DIRECTORY).resolve()
            bundle.relative_to(archive_root)
            backup_archive_verification = verify_portfolio_evidence_archive(bundle)
        except (OSError, RuntimeError, ValueError) as exc:
            backup_archive_verification = {
                "status": "BLOCK",
                "blockers": [f"backup_archive_verification_error:{type(exc).__name__}"],
                "paper_authorized": False,
                "live_order_allowed": False,
            }
    task_probe = _probe_windows_tasks(
        task_names,
        timeout_seconds=max(float(args.task_probe_timeout), 1.0),
    )
    payload = build_portfolio_forward_watchdog_status(
        now_ms=current_ms,
        active=active,
        scheduler=scheduler,
        observation=observation,
        performance=performance,
        backup=backup,
        backup_verification=backup_verification,
        backup_archive_verification=backup_archive_verification,
        task_probe=task_probe,
        observation_task_name=observation_task_name,
        performance_task_name=performance_task_name,
        backup_task_name=backup_task_name,
    )
    record_portfolio_forward_watchdog_status(
        status_path=REPORT_DIR / DEFAULT_WATCHDOG_STATUS_FILE,
        alert_path=REPORT_DIR / DEFAULT_WATCHDOG_ALERT_FILE,
        payload=payload,
    )
    try:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    except UnicodeEncodeError:
        print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0 if payload.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
