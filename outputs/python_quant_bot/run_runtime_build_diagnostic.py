from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from typing import Any

from exchange_terminal import server
from exchange_terminal.services.runtime_build import RuntimeBuildGuard


PROJECT_ROOT = Path(__file__).resolve().parent
ELECTRON_ROOT = PROJECT_ROOT.parent / "hakimi_trade_electron"


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _file_record(path: Path) -> dict[str, Any]:
    content = path.read_bytes()
    return {
        "path": path.relative_to(PROJECT_ROOT.parent).as_posix(),
        "sha256": hashlib.sha256(content).hexdigest(),
        "size": len(content),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the local backend runtime-build and desktop restart contract.")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "runtime" / "reports" / "runtime_build_diagnostic.json",
    )
    args = parser.parse_args()

    current = server.RUNTIME_BUILD_GUARD.snapshot(force=True)
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        source = project / "exchange_terminal"
        source.mkdir()
        target = source / "server.py"
        target.write_text("VERSION = 1\n", encoding="utf-8")
        guard = RuntimeBuildGuard(project_root=project, source_roots=[source], cache_ttl_ms=0)
        target.write_text("VERSION = 2\n", encoding="utf-8")
        drift = guard.snapshot(force=True)

    node = shutil.which("node")
    electron_test_path = ELECTRON_ROOT / "backend-runtime-contract.test.js"
    electron_result = subprocess.run(
        [str(node), str(electron_test_path)],
        cwd=ELECTRON_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    ) if node and electron_test_path.is_file() else None
    files = [
        PROJECT_ROOT / "exchange_terminal" / "server.py",
        PROJECT_ROOT / "exchange_terminal" / "services" / "runtime_build.py",
        ELECTRON_ROOT / "main.js",
        ELECTRON_ROOT / "backend-runtime-contract.js",
        ELECTRON_ROOT / "backend-runtime-contract.test.js",
    ]
    file_records = [_file_record(path) for path in files if path.is_file()]
    checks = {
        "runtime_loaded_matches_disk": current.get("status") == "PASS" and current.get("restart_required") is False,
        "runtime_source_drift_is_detected": (
            drift.get("status") == "RESTART_REQUIRED"
            and drift.get("restart_required") is True
            and "runtime_source_tree_changed_after_start" in list(drift.get("blockers") or [])
        ),
        "runtime_has_zero_execution_authority": (
            current.get("paper_authorized") is False
            and current.get("live_order_allowed") is False
            and drift.get("paper_authorized") is False
            and drift.get("live_order_allowed") is False
        ),
        "electron_contract_tests_pass": bool(electron_result and electron_result.returncode == 0),
        "contract_files_complete": len(file_records) == len(files),
    }
    content = {
        "schema_version": "hakimi-runtime-build-diagnostic-v1",
        "status": "PASS" if all(checks.values()) else "BLOCK",
        "checks": checks,
        "runtime_build": current,
        "drift_probe": drift,
        "electron_test": {
            "status": "PASS" if electron_result and electron_result.returncode == 0 else "BLOCK",
            "return_code": int(electron_result.returncode) if electron_result else None,
            "stdout": str(electron_result.stdout or "").strip() if electron_result else "",
            "stderr": str(electron_result.stderr or "").strip() if electron_result else "node or test file unavailable",
        },
        "files": file_records,
        "read_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    report = {
        **content,
        "generated_at": int(time.time() * 1000),
        "report_hash": _canonical_hash(content),
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "report_hash": report["report_hash"],
        "output": str(output),
        "checks": checks,
        "paper_authorized": False,
        "live_order_allowed": False,
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
