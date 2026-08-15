from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time

from exchange_terminal.services.portfolio_backtest_campaign import (
    build_internal_backtest_campaign_contract,
    run_internal_backtest_campaign,
    verify_internal_backtest_campaign_report,
)
from exchange_terminal.services.portfolio_evidence_archive import verify_portfolio_backup_status


PROJECT_ROOT = Path(__file__).resolve().parent


def create_json_once(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, indent=2))
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def resolve_active_archive(runtime_dir: Path, explicit_archive: Path | None) -> Path:
    report_dir = runtime_dir / "reports"
    active_path = report_dir / "active_portfolio_candidate.json"
    active = json.loads(active_path.read_text(encoding="utf-8"))
    active_candidate_hash = str(active.get("candidate_hash") or "")
    if explicit_archive is not None:
        bundle = explicit_archive.resolve()
    else:
        status_path = report_dir / "portfolio_forward_backup_status.json"
        status = json.loads(status_path.read_text(encoding="utf-8"))
        verification = verify_portfolio_backup_status(status)
        if verification.get("status") != "PASS":
            raise ValueError(f"Latest evidence backup status is blocked: {verification.get('blockers')}")
        bundle = Path(str(status.get("bundle_path") or "")).resolve()
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    if str(manifest.get("candidate_hash") or "") != active_candidate_hash:
        raise ValueError("Evidence archive does not belong to the active frozen candidate")
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preregister and run a fixed-count, read-only deterministic replay campaign against "
            "the active portfolio evidence archive. No market fetch, parameter search, paper order, "
            "or live order is permitted."
        )
    )
    default_runtime = Path(os.environ.get("HAKIMI_RUNTIME_DIR") or PROJECT_ROOT / "runtime")
    parser.add_argument("--runtime-dir", type=Path, default=default_runtime)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--contract-output", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    runtime_dir = args.runtime_dir.resolve()
    report_dir = runtime_dir / "reports"
    bundle = resolve_active_archive(runtime_dir, args.archive)
    declared_at = time.time_ns() // 1_000_000
    stamp = f"{time.strftime('%Y%m%d_%H%M%S')}_{declared_at}"
    contract_path = (
        args.contract_output.resolve()
        if args.contract_output
        else report_dir / f"internal_portfolio_backtest_campaign_contract_{stamp}.json"
    )
    report_path = (
        args.output.resolve()
        if args.output
        else report_dir / f"internal_portfolio_backtest_campaign_{stamp}.json"
    )
    contract = build_internal_backtest_campaign_contract(
        bundle,
        declared_at=declared_at,
        repetitions=args.repetitions,
        timeout_seconds=args.timeout_seconds,
    )
    create_json_once(contract_path, contract)
    report = run_internal_backtest_campaign(
        bundle,
        contract,
        generated_at=time.time_ns() // 1_000_000,
        contract_file_path=contract_path,
    )
    verification = verify_internal_backtest_campaign_report(
        report,
        bundle,
        rerun_replays=True,
    )
    create_json_once(report_path, report)
    print(json.dumps({
        "status": report.get("status"),
        "conclusion": report.get("conclusion"),
        "campaign_id": report.get("campaign_id"),
        "campaign_hash": report.get("campaign_hash"),
        "contract_hash": report.get("contract_hash"),
        "candidate_hash": (report.get("archive_binding") or {}).get("candidate_hash"),
        "metrics": report.get("metrics"),
        "blockers": report.get("blockers"),
        "verification_status": verification.get("status"),
        "verification_blockers": verification.get("blockers"),
        "verifier_replay_count": verification.get("rerun_replay_count"),
        "contract_output": str(contract_path),
        "output": str(report_path),
        "promotion_status": "BLOCK",
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }, ensure_ascii=False, indent=2))
    return 0 if report.get("status") == "INTERNAL_BACKTEST_CAMPAIGN_PASS" and verification.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
