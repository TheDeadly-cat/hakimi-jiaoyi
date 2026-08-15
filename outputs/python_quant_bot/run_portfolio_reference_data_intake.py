from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any

from exchange_terminal.services.portfolio_evidence_bundle import expand_portfolio_evidence_bundle
from exchange_terminal.services.portfolio_forward import load_active_portfolio_candidate
from portfolio_reference_data import (
    ReferenceDataStore,
    build_intake_template,
    build_reference_data_pack_from_manifest,
    verify_reference_data_pack,
)


PROJECT_ROOT = Path(__file__).resolve().parent
RUNTIME_DIR = Path(os.environ.get("HAKIMI_RUNTIME_DIR") or PROJECT_ROOT / "runtime").resolve()
REPORT_DIR = RUNTIME_DIR / "reports"
REFERENCE_DATA_DIR = RUNTIME_DIR / "reference_data"
DEFAULT_DB = REFERENCE_DATA_DIR / "portfolio_reference_data.sqlite"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _safe_name(value: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "_", str(value or "").lower()).strip("_") or "reference_data"


def _active_report() -> tuple[dict[str, Any], dict[str, Any], str]:
    active = load_active_portfolio_candidate(REPORT_DIR)
    registry = dict(active.get("registry") or {})
    receipt = dict(registry.get("experiment_completion_receipt") or {})
    report_name = str(receipt.get("report_file") or "")
    if Path(report_name).name != report_name or not report_name:
        raise RuntimeError("Active candidate report name is invalid.")
    report, bundle_audit = expand_portfolio_evidence_bundle(
        _read_json(REPORT_DIR / report_name),
        require_bundle=True,
    )
    if bundle_audit.get("status") != "PASS":
        raise RuntimeError(f"Active report evidence bundle is invalid: {bundle_audit.get('blockers')}")
    return active, report, report_name


def initialize_template(output: Path) -> int:
    active, report, report_name = _active_report()
    candidate = dict(active.get("candidate") or {})
    universe = dict(report.get("universe_contract") or {})
    calendar = dict((report.get("dataset_manifest") or {}).get("market_calendar") or {})
    template = build_intake_template(
        candidate_hash=str(candidate.get("candidate_hash") or ""),
        benchmark_symbol=str(universe.get("benchmark_symbol") or ""),
        tradable_symbols=list(universe.get("tradable_symbols") or []),
        coverage_start=str(calendar.get("start") or ""),
        coverage_end=str(calendar.get("end") or ""),
        prepared_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    template["candidate_binding"] = {
        "candidate_hash": str(candidate.get("candidate_hash") or ""),
        "research_generation": str((candidate.get("spec") or {}).get("research_generation") or ""),
        "research_report": report_name,
        "dataset_hash": str(candidate.get("dataset_hash") or ""),
    }
    _atomic_write_json(output, template)
    print(json.dumps({
        "ok": True,
        "status": "INTAKE_TEMPLATE_CREATED",
        "artifact": str(output),
        "candidate_hash": candidate.get("candidate_hash"),
        "symbol_count": len(template["universe"]["tradable_symbols"]) + 1,
        "coverage_start": template["universe"]["coverage_start"],
        "coverage_end": template["universe"]["coverage_end"],
        "manual_source_identity_review_required": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }, ensure_ascii=False, indent=2))
    return 0


def import_manifest(manifest: Path, output: Path | None, db_path: Path, no_store: bool) -> int:
    pack = build_reference_data_pack_from_manifest(manifest)
    audit = verify_reference_data_pack(pack, source_root=manifest.parent)
    target = output or REPORT_DIR / f"portfolio_reference_data_{_safe_name(pack.get('package_id', ''))}.json"
    _atomic_write_json(target, pack)
    store_result: dict[str, Any] = {"status": "NOT_REQUESTED", "ok": True}
    if not no_store and pack.get("status") == "PASS" and audit.get("status") == "PASS":
        store_result = ReferenceDataStore(db_path).import_pack(pack, source_root=manifest.parent)
    ok = pack.get("status") == "PASS" and audit.get("status") == "PASS" and store_result.get("ok") is True
    all_blockers = list(dict.fromkeys([*(pack.get("blockers") or []), *(audit.get("blockers") or [])]))
    primary_blockers = [
        item for item in pack.get("blockers") or []
        if str(item).startswith("reference_data_")
    ]
    if (pack.get("universe_contract") or {}).get("status") != "POINT_IN_TIME_VERIFIED":
        primary_blockers.append("point_in_time_membership_contract_incomplete")
    missing_symbols = list((pack.get("coverage_summary") or {}).get("missing_symbols") or [])
    if missing_symbols:
        primary_blockers.append(f"corporate_action_coverage_missing:{','.join(missing_symbols)}")
    primary_blockers = list(dict.fromkeys(primary_blockers))
    print(json.dumps({
        "ok": ok,
        "status": pack.get("status"),
        "admission_status": pack.get("admission_status"),
        "pack_hash": pack.get("pack_hash"),
        "verification_status": audit.get("status"),
        "blocker_count": len(all_blockers),
        "primary_blockers": primary_blockers,
        "blockers_artifact_contains_full_detail": bool(all_blockers),
        "coverage_summary": pack.get("coverage_summary"),
        "store": store_result,
        "artifact": str(target),
        "manual_source_identity_review_required": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 2


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare and import content-addressed point-in-time universe and corporate-action evidence."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    init_parser = subparsers.add_parser("init", help="Create an incomplete intake template bound to the active candidate.")
    init_parser.add_argument("--output", type=Path, default=REFERENCE_DATA_DIR / "active_reference_data_intake.json")
    import_parser = subparsers.add_parser("import", help="Verify and import a completed local evidence package.")
    import_parser.add_argument("--manifest", type=Path, required=True)
    import_parser.add_argument("--output", type=Path)
    import_parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    import_parser.add_argument("--no-store", action="store_true")
    status_parser = subparsers.add_parser("status", help="Show the local reference-data store inventory.")
    status_parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    if args.command == "init":
        return initialize_template(args.output.resolve())
    if args.command == "import":
        return import_manifest(
            args.manifest.resolve(),
            args.output.resolve() if args.output else None,
            args.db.resolve(),
            bool(args.no_store),
        )
    print(json.dumps(ReferenceDataStore(args.db.resolve()).summary(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
