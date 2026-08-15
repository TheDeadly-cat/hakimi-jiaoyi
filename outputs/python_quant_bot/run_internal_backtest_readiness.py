from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlopen

from exchange_terminal.services.internal_backtest_readiness import (
    build_readiness_report,
    verify_readiness_report,
)


def _get_json(url: str) -> dict[str, Any]:
    with urlopen(url, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object from {url}")
    return payload


ENGINEERING_EVIDENCE_SCHEMA = "hakimi-engineering-evidence-v2"


def _load_engineering_evidence(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != ENGINEERING_EVIDENCE_SCHEMA:
        raise ValueError(f"engineering evidence must use {ENGINEERING_EVIDENCE_SCHEMA}")
    rows = payload.get("engineering_checks")
    if not isinstance(rows, list) or not all(isinstance(item, dict) for item in rows):
        raise ValueError("engineering evidence must contain an engineering_checks array")
    normalized = dict(payload)
    normalized["engineering_checks"] = [dict(item) for item in rows]
    return normalized


def _runtime_instance_tuple(payload: dict[str, Any]) -> tuple[int, int, str]:
    build = payload.get("runtime_build") if isinstance(payload.get("runtime_build"), dict) else {}
    return (
        int(build.get("process_id") or 0),
        int(build.get("loaded_at") or 0),
        str(build.get("loaded_fingerprint") or ""),
    )


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Freeze a research-only readiness snapshot before designing the next blind backtest."
    )
    parser.add_argument("--runtime-dir", required=True)
    parser.add_argument("--service-url", required=True)
    parser.add_argument("--generation", required=True)
    parser.add_argument("--prior-report", required=True)
    parser.add_argument("--engineering-evidence", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    runtime_dir = Path(args.runtime_dir).resolve()
    reports_dir = (runtime_dir / "reports").resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)
    prior_report = Path(args.prior_report).resolve()
    evidence_path = Path(args.engineering_evidence).resolve()
    output = Path(args.output).resolve()
    try:
        prior_report.relative_to(reports_dir)
        evidence_path.relative_to(reports_dir)
        output.relative_to(reports_dir)
    except ValueError as exc:
        raise SystemExit("readiness inputs and output must remain inside runtime reports") from exc

    generation = str(args.generation or "").strip().upper()
    if generation in {"G49", "G50", "G51"}:
        raise SystemExit("a retired or falsified generation cannot be reused for readiness")
    parsed_url = urlparse(str(args.service_url))
    if (
        parsed_url.scheme != "http"
        or parsed_url.hostname not in {"127.0.0.1", "localhost"}
        or parsed_url.username is not None
        or parsed_url.password is not None
        or parsed_url.port is None
        or parsed_url.path not in {"", "/"}
        or parsed_url.query
        or parsed_url.fragment
    ):
        raise SystemExit("readiness service URL must be an unauthenticated loopback HTTP endpoint")
    try:
        evidence = _load_engineering_evidence(evidence_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"engineering evidence unavailable or invalid: {exc}") from exc

    base_url = f"http://{parsed_url.hostname}:{parsed_url.port}"
    health_before = _get_json(f"{base_url}/api/health")
    cache = _get_json(f"{base_url}/api/data/cache/status")
    health = _get_json(f"{base_url}/api/health")
    before_instance = _runtime_instance_tuple(health_before)
    after_instance = _runtime_instance_tuple(health)
    if (
        before_instance != after_instance
        or before_instance[0] <= 0
        or before_instance[1] <= 0
        or len(before_instance[2]) != 64
    ):
        raise SystemExit("readiness service instance changed or has an invalid runtime identity")
    generated_at = datetime.now(tz=timezone.utc).isoformat()
    report = build_readiness_report(
        generation=generation,
        generated_at=generated_at,
        service_origin=base_url,
        runtime_health=health,
        market_cache=cache,
        prior_matrix_report=prior_report,
        engineering_checks=list(evidence["engineering_checks"]),
    )
    verification = verify_readiness_report(report, verify_files=True)
    if verification.get("status") != "PASS":
        raise SystemExit(json.dumps({"error": "readiness_self_verification_blocked", "verification": verification}, ensure_ascii=False))
    if output.exists():
        raise SystemExit(f"readiness output already exists: {output}")
    _write_json_atomic(output, report)
    print(json.dumps({
        "status": report["status"],
        "verification": verification,
        "output": str(output),
        "readiness_hash": report["readiness_hash"],
        "service_origin": base_url,
        "formal_run_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
