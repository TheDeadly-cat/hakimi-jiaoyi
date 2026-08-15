from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time

from exchange_terminal.services.portfolio_evidence_archive import (
    DEFAULT_ARCHIVE_DIRECTORY,
    DEFAULT_BACKUP_ALERT_FILE,
    DEFAULT_BACKUP_STATUS_FILE,
    build_portfolio_backup_status,
    create_portfolio_evidence_archive,
    record_portfolio_backup_status,
)


PROJECT_ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Create and restore-verify a self-contained portfolio evidence archive.")
    default_runtime = Path(os.environ.get("HAKIMI_RUNTIME_DIR") or PROJECT_ROOT / "runtime")
    parser.add_argument("--runtime-dir", type=Path, default=default_runtime)
    parser.add_argument("--archive-root", type=Path)
    parser.add_argument("--max-attempts", type=int, default=3)
    args = parser.parse_args()
    runtime = args.runtime_dir.resolve()
    report_dir = runtime / "reports"
    archive_root = args.archive_root.resolve() if args.archive_root else runtime / "backups" / DEFAULT_ARCHIVE_DIRECTORY
    generated_at = time.time_ns() // 1_000_000
    result: dict[str, object] = {}
    error: Exception | None = None
    try:
        result = create_portfolio_evidence_archive(
            runtime,
            archive_root=archive_root,
            generated_at=generated_at,
            max_attempts=max(int(args.max_attempts), 1),
        )
    except Exception as exc:
        error = exc
    status = build_portfolio_backup_status(generated_at=generated_at, result=result, error=error)
    record_portfolio_backup_status(
        status_path=report_dir / DEFAULT_BACKUP_STATUS_FILE,
        alert_path=report_dir / DEFAULT_BACKUP_ALERT_FILE,
        payload=status,
    )
    summary = {
        "ok": status.get("status") == "PASS",
        "status": status.get("status"),
        "candidate_hash": status.get("candidate_hash"),
        "bundle_path": status.get("bundle_path"),
        "manifest_hash": status.get("manifest_hash"),
        "pack_hash": status.get("pack_hash"),
        "verification_status": status.get("verification_status"),
        "local_source_anchor_status": str(
            dict(status.get("local_source_anchor") or {}).get("status")
            or "NOT_AVAILABLE"
        ),
        "blockers": status.get("blockers"),
        "error_type": status.get("error_type"),
        "error": status.get("error"),
        "backup_only": True,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
