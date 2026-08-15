from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from exchange_terminal.services.portfolio_forward import retire_active_portfolio_candidate
from exchange_terminal.services.trusted_clock import attest_utc_clock


PROJECT_ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Atomically retire the active research candidate against a frozen invalidation report."
    )
    default_runtime = Path(os.environ.get("HAKIMI_RUNTIME_DIR") or PROJECT_ROOT / "runtime")
    parser.add_argument("--report-dir", type=Path, default=default_runtime / "reports")
    parser.add_argument("--candidate-hash", required=True)
    parser.add_argument("--invalidation-report", type=Path, required=True)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()

    report_dir = args.report_dir.resolve()
    invalidation_path = args.invalidation_report.resolve()
    clock = attest_utc_clock(minimum_sources=1)
    retired_at = int(clock.get("attested_now_ms") or 0)
    result = retire_active_portfolio_candidate(
        registry_path=report_dir / "active_portfolio_candidate.json",
        expected_candidate_hash=str(args.candidate_hash),
        retired_at=retired_at,
        retirement_clock_attestation=clock,
        reason=str(args.reason),
        invalidation_path=invalidation_path,
    )
    print(json.dumps({
        "ok": result.get("ok"),
        "status": result.get("status"),
        "blockers": result.get("blockers"),
        "candidate_hash": str((result.get("registry") or {}).get("candidate_hash") or ""),
        "registry_path": result.get("registry_path"),
        "retirement_receipt_path": result.get("retirement_receipt_path"),
        "clock_status": clock.get("status"),
        "clock_quality": clock.get("quality"),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"RETIRED", "ALREADY_RETIRED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
