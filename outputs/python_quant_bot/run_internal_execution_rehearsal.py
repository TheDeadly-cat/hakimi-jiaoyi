from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

_ADR0524_REPO_ROOT = Path(__file__).resolve().parents[2]
_ADR0524_SRC_ROOT = _ADR0524_REPO_ROOT / "src"
if str(_ADR0524_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_ADR0524_SRC_ROOT))

from exchange_terminal.services.portfolio_execution_rehearsal import (
    run_research_report_execution_rehearsal,
)
from exchange_terminal.services.portfolio_active_research_source import (
    load_active_portfolio_research_source,
)
from exchange_terminal.services.portfolio_evidence_bundle import (
    expand_portfolio_evidence_bundle,
)


PROJECT_ROOT = Path(__file__).resolve().parent


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


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run an isolated historical execution-chain rehearsal for the active research candidate."
    )
    default_runtime = Path(os.environ.get("HAKIMI_RUNTIME_DIR") or PROJECT_ROOT / "runtime")
    parser.add_argument("--report-dir", type=Path, default=default_runtime / "reports")
    parser.add_argument("--research-report", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report_dir = args.report_dir.resolve()
    if args.research_report:
        source_path = args.research_report.resolve()
        source = _read_json(source_path)
        registry: dict[str, Any] = {}
        source_file_sha256 = _file_sha256(source_path)
    else:
        active_source = load_active_portfolio_research_source(report_dir)
        if active_source.get("status") != "PASS":
            print(json.dumps({
                "status": "BLOCK",
                "blockers": list(active_source.get("blockers") or ["active_research_source_blocked"]),
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }, ensure_ascii=False))
            return 2
        source_path = Path(str(active_source["report_path"]))
        source = dict(active_source["report"])
        registry = dict(active_source["registry"])
        source_file_sha256 = str(active_source["report_file_sha256"])
    source, evidence_bundle_audit = expand_portfolio_evidence_bundle(
        source,
        require_bundle=bool((source.get("spec") or {}).get("evidence_bundle_required") is True),
    )
    if evidence_bundle_audit.get("status") != "PASS":
        print(json.dumps({
            "status": "BLOCK",
            "blockers": [
                f"research_evidence_bundle:{item}"
                for item in evidence_bundle_audit.get("blockers") or ["verification_failed"]
            ],
            "paper_authorized": False,
            "live_order_allowed": False,
        }, ensure_ascii=False))
        return 2
    generated_at = int(time.time() * 1000)
    result = run_research_report_execution_rehearsal(source, generated_at=generated_at)
    result.update({
        "source_research_report": str(source_path),
        "source_research_file_sha256": source_file_sha256,
        "active_candidate_registry": str(report_dir / "active_portfolio_candidate.json") if registry else "",
        "active_candidate_hash": str(registry.get("candidate_hash") or ""),
        "source_evidence_bundle_verification": evidence_bundle_audit,
    })
    result["artifact_hash"] = _canonical_hash(result)
    output = args.output.resolve() if args.output else (
        report_dir / time.strftime("portfolio_internal_execution_rehearsal_%Y%m%d_%H%M%S.json")
    )
    if output == source_path:
        raise ValueError("Output cannot overwrite the source research report.")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": result.get("status"),
        "output": str(output),
        "artifact_hash": result.get("artifact_hash"),
        "stage_summary": result.get("stage_summary"),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }, ensure_ascii=False))
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
