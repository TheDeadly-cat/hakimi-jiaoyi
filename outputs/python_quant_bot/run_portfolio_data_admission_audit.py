from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any

from exchange_terminal.services.portfolio_data_admission import (
    build_portfolio_data_admission_audit,
    verify_portfolio_data_admission_audit,
)
from exchange_terminal.services.portfolio_forward import load_active_portfolio_candidate


PROJECT_ROOT = Path(__file__).resolve().parent
RUNTIME_DIR = Path(os.environ.get("HAKIMI_RUNTIME_DIR") or PROJECT_ROOT / "runtime").resolve()
REPORT_DIR = RUNTIME_DIR / "reports"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a read-only data admission audit for the active portfolio candidate.")
    parser.add_argument("--report-dir", type=Path, default=REPORT_DIR)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report_dir = args.report_dir.resolve()
    active = load_active_portfolio_candidate(report_dir)
    registry = dict(active.get("registry") or {})
    candidate = dict(active.get("candidate") or {})
    receipt = dict(registry.get("experiment_completion_receipt") or {})
    report_name = str(receipt.get("report_file") or "")
    candidate_name = str(registry.get("candidate_file") or "")
    if Path(report_name).name != report_name or Path(candidate_name).name != candidate_name:
        raise SystemExit("Active candidate artifact names are invalid.")
    report_path = (report_dir / report_name).resolve()
    candidate_path = (report_dir / candidate_name).resolve()
    report = _read_json(report_path)
    generation = re.sub(
        r"[^a-z0-9_-]+",
        "_",
        str((candidate.get("spec") or {}).get("research_generation") or "active").lower(),
    ).strip("_") or "active"
    output_path = args.output.resolve() if args.output else report_dir / f"portfolio_data_admission_{generation}.json"
    payload = build_portfolio_data_admission_audit(
        generated_at=time.time_ns() // 1_000_000,
        active_status=str(active.get("status") or "BLOCK"),
        candidate=candidate,
        report=report,
        candidate_file=candidate_name,
        candidate_file_sha256=_file_sha256(candidate_path),
        report_file=report_name,
        report_file_sha256=_file_sha256(report_path),
        expected_report_file_sha256=str(receipt.get("report_file_sha256") or ""),
    )
    verification = verify_portfolio_data_admission_audit(payload)
    _atomic_write_json(output_path, payload)
    summary = {
        "ok": verification.get("status") == "PASS" and payload.get("status") == "AUDIT_COMPLETE",
        "status": payload.get("status"),
        "candidate_hash": payload.get("candidate_hash"),
        "internal_research_data_status": payload.get("internal_research_data_status"),
        "paper_data_admission_status": payload.get("paper_data_admission_status"),
        "live_data_admission_status": payload.get("live_data_admission_status"),
        "coverage_summary": payload.get("coverage_summary"),
        "admission_blockers": payload.get("admission_blockers"),
        "audit_hash": payload.get("audit_hash"),
        "verification_status": verification.get("status"),
        "artifact": str(output_path),
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
