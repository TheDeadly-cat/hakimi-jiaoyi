from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify() -> dict[str, Any]:
    dataset_path = ROOT / "dataset.csv"
    config_path = ROOT / "config.json"
    expected_path = ROOT / "expected_result.json"

    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    config = json.loads(config_path.read_text(encoding="utf-8"))
    with dataset_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    checks = {
        "dataset_sha256": _sha256(dataset_path) == expected["dataset_sha256"],
        "config_sha256": _sha256(config_path) == expected["config_sha256"],
        "data_rows": len(rows) == expected["data_rows"],
        "csv_provider": config.get("data", {}).get("provider") == "csv",
        "cache_disabled": config.get("data", {}).get("use_cache") is False,
        "backtest_only": config.get("mode") == "backtest",
        "no_performance_metrics": expected.get("performance_metrics_included") is False,
        "no_execution_authority": all(
            value is False for value in expected.get("authority", {}).values()
        ),
    }
    return {
        "contract_version": "deterministic-research-example-verifier-v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
    }


if __name__ == "__main__":
    result = verify()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
