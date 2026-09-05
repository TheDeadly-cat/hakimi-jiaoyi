from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

from .execution_authority import authority_violations as _authority_violations

from hakimi_research.candle_contract import candle_is_complete


PORTFOLIO_BACKTEST_REPLAY_DATASET_SCHEMA_VERSION = "portfolio-backtest-replay-dataset-v2"
PORTFOLIO_BACKTEST_REPLAY_BUNDLE_SCHEMA_VERSION = "portfolio-backtest-replay-bundle-v1"
PORTFOLIO_BACKTEST_REPLAY_RESULT_SCHEMA_VERSION = "portfolio-backtest-replay-result-v1"
DEFAULT_REPLAY_DATASET_FILE = "portfolio_backtest_inputs.json"
DEFAULT_REPLAY_DRIVER_FILE = "portfolio_backtest_replay_driver.py"
REPLAY_STAGES = ("validation", "test", "full")
SENSITIVE_FIELD_NAMES = {
    "access_key",
    "accesskey",
    "api_key",
    "apikey",
    "password",
    "secret",
    "secret_key",
    "secretkey",
    "token",
}
SENSITIVE_ENV_MARKERS = (
    "API_KEY",
    "APIKEY",
    "ACCESS_KEY",
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "OPENAI",
    "DEEPSEEK",
    "OKX",
    "ARK",
    "PROXY",
)


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def file_sha256(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def _write_canonical_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    temporary.replace(path)


def _safe_bundle_path(bundle_dir: Path, relative_path: str) -> Path:
    candidate = (bundle_dir / str(relative_path or "")).resolve()
    candidate.relative_to(bundle_dir.resolve())
    return candidate


def _sensitive_field_paths(payload: Any, *, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            child = f"{path}.{key}"
            if str(key).strip().lower() in SENSITIVE_FIELD_NAMES:
                findings.append(child)
            findings.extend(_sensitive_field_paths(value, path=child))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            findings.extend(_sensitive_field_paths(value, path=f"{path}[{index}]"))
    return findings


def _payload_inventory(payloads: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    inventory: dict[str, dict[str, Any]] = {}
    for symbol in sorted(payloads):
        payload = dict(payloads[symbol] or {})
        rows = [dict(row) for row in payload.get("rows") or [] if isinstance(row, dict)]
        dates = [str(row.get("date") or "")[:10] for row in rows]
        inventory[symbol] = {
            "row_count": len(rows),
            "first": dates[0] if dates else "",
            "last": dates[-1] if dates else "",
            "rows_hash": canonical_hash(rows),
            "payload_hash": canonical_hash(payload),
        }
    return inventory


def build_portfolio_backtest_replay_dataset(
    report: dict[str, Any],
    payloads: dict[str, dict[str, Any]],
    *,
    source_report_file: str,
    source_report_file_sha256: str,
) -> dict[str, Any]:
    from .portfolio_backtest import prepare_portfolio_dataset
    from .portfolio_evidence_bundle import (
        expand_portfolio_evidence_bundle,
        pack_portfolio_evidence_bundle,
    )

    report, report_bundle_audit = expand_portfolio_evidence_bundle(
        report,
        require_bundle=bool((report.get("spec") or {}).get("evidence_bundle_required") is True),
    )
    if report_bundle_audit.get("status") != "PASS":
        raise ValueError(
            "Research evidence bundle failed verification: "
            + ",".join(report_bundle_audit.get("blockers") or [])
        )

    manifest = dict(report.get("dataset_manifest") or {})
    expected_symbols = sorted(str(symbol).upper() for symbol in manifest.get("symbols") or [])
    clean_payloads = {
        str(symbol).upper(): deepcopy(dict(payload or {}))
        for symbol, payload in payloads.items()
    }
    if not expected_symbols or sorted(clean_payloads) != expected_symbols:
        raise ValueError("Replay payload symbol inventory does not match the research report")
    expected_rows = int(manifest.get("row_count") or 0)
    if expected_rows <= 0:
        raise ValueError("Research report has no replayable dataset rows")
    prepared = prepare_portfolio_dataset(
        clean_payloads,
        benchmark_symbol=str(manifest.get("benchmark_symbol") or ""),
        minimum_rows=expected_rows,
        universe_contract=dict(report.get("universe_contract") or {}),
    )
    rebuilt = dict(prepared.get("manifest") or {})
    if prepared.get("status") != "PASS":
        raise ValueError(f"Replay dataset gate failed: {rebuilt.get('blockers')}")
    if str(rebuilt.get("data_hash") or "") != str(manifest.get("data_hash") or ""):
        raise ValueError("Replay dataset hash does not match the research report")
    if str(rebuilt.get("manifest_hash") or "") != str(manifest.get("manifest_hash") or ""):
        raise ValueError("Replay dataset manifest hash does not match the research report")

    expected_results = {
        stage: {
            "run_hash": str(dict(report.get(stage) or {}).get("run_hash") or ""),
            "result_hash": canonical_hash(dict(report.get(stage) or {})),
        }
        for stage in REPLAY_STAGES
    }
    benchmark_results = {
        stage: canonical_hash(dict(report.get(stage) or {}))
        for stage in ("validation_benchmark", "test_benchmark")
    }
    payload = {
        "schema_version": PORTFOLIO_BACKTEST_REPLAY_DATASET_SCHEMA_VERSION,
        "status": "FROZEN",
        "source_report_file": str(source_report_file),
        "source_report_file_sha256": str(source_report_file_sha256),
        "strategy_schema_version": str(report.get("schema_version") or ""),
        "candidate_dataset_hash": str(manifest.get("data_hash") or ""),
        "candidate_dataset_manifest_hash": str(manifest.get("manifest_hash") or ""),
        "benchmark_symbol": str(manifest.get("benchmark_symbol") or ""),
        "symbols": expected_symbols,
        "symbol_count": len(expected_symbols),
        "row_count": expected_rows,
        "first": str(manifest.get("first") or ""),
        "last": str(manifest.get("last") or ""),
        "payload_inventory": _payload_inventory(clean_payloads),
        "payloads_hash": canonical_hash(clean_payloads),
        "payloads": clean_payloads,
        "expected_results": expected_results,
        "expected_benchmark_result_hashes": benchmark_results,
        "expected_cost_stress_hash": canonical_hash(list(report.get("cost_stress") or [])),
        "capture_policy": "LOCAL_PERSISTENT_CACHE_EXACT_HASH_MATCH_NO_NETWORK",
        "evidence_bundle_required": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    if _sensitive_field_paths(payload):
        raise ValueError("Replay dataset contains credential-like fields")
    if _authority_violations(payload):
        raise ValueError("Replay dataset contains execution authority")
    preview = pack_portfolio_evidence_bundle(payload)
    payload["evidence_bundle_required"] = "evidence_bundle" in preview
    payload["snapshot_hash"] = canonical_hash(payload)
    return pack_portfolio_evidence_bundle(payload)


def verify_portfolio_backtest_replay_dataset(
    snapshot: dict[str, Any],
    report: dict[str, Any],
    *,
    actual_source_report_sha256: str,
) -> dict[str, Any]:
    from .portfolio_evidence_bundle import expand_portfolio_evidence_bundle

    blockers: list[str] = []
    snapshot, snapshot_bundle_audit = expand_portfolio_evidence_bundle(
        snapshot,
        require_bundle=bool((snapshot or {}).get("evidence_bundle_required") is True),
    )
    if snapshot_bundle_audit.get("status") != "PASS":
        blockers.extend(
            f"replay_evidence_bundle:{item}"
            for item in snapshot_bundle_audit.get("blockers") or ["verification_failed"]
        )
    report, report_bundle_audit = expand_portfolio_evidence_bundle(
        report,
        require_bundle=bool((report.get("spec") or {}).get("evidence_bundle_required") is True),
    )
    if report_bundle_audit.get("status") != "PASS":
        blockers.extend(
            f"research_evidence_bundle:{item}"
            for item in report_bundle_audit.get("blockers") or ["verification_failed"]
        )
    clean = dict(snapshot or {})
    expected_snapshot_hash = str(clean.pop("snapshot_hash", "") or "")
    if snapshot.get("schema_version") != PORTFOLIO_BACKTEST_REPLAY_DATASET_SCHEMA_VERSION:
        blockers.append("replay_dataset_schema_invalid")
    if snapshot.get("status") != "FROZEN":
        blockers.append("replay_dataset_status_invalid")
    if not expected_snapshot_hash or canonical_hash(clean) != expected_snapshot_hash:
        blockers.append("replay_dataset_snapshot_hash_invalid")
    if str(snapshot.get("source_report_file_sha256") or "") != str(actual_source_report_sha256 or ""):
        blockers.append("replay_source_report_file_hash_mismatch")

    manifest = dict(report.get("dataset_manifest") or {})
    expected_symbols = sorted(str(symbol).upper() for symbol in manifest.get("symbols") or [])
    payloads = {
        str(symbol).upper(): dict(payload or {})
        for symbol, payload in dict(snapshot.get("payloads") or {}).items()
    }
    if list(snapshot.get("symbols") or []) != expected_symbols or sorted(payloads) != expected_symbols:
        blockers.append("replay_dataset_symbol_inventory_mismatch")
    if int(snapshot.get("symbol_count") or 0) != len(expected_symbols):
        blockers.append("replay_dataset_symbol_count_mismatch")
    for key in ("row_count",):
        if int(snapshot.get(key) or 0) != int(manifest.get(key) or 0):
            blockers.append(f"replay_dataset_{key}_mismatch")
    for key in ("first", "last", "benchmark_symbol", "candidate_dataset_hash"):
        report_key = "data_hash" if key == "candidate_dataset_hash" else key
        if str(snapshot.get(key) or "") != str(manifest.get(report_key) or ""):
            blockers.append(f"replay_dataset_{key}_mismatch")
    if str(snapshot.get("candidate_dataset_manifest_hash") or "") != str(manifest.get("manifest_hash") or ""):
        blockers.append("replay_dataset_manifest_hash_mismatch")
    if str(snapshot.get("strategy_schema_version") or "") != str(report.get("schema_version") or ""):
        blockers.append("replay_strategy_schema_mismatch")
    if str(snapshot.get("payloads_hash") or "") != canonical_hash(payloads):
        blockers.append("replay_payloads_hash_invalid")

    recorded_inventory = {
        str(symbol).upper(): dict(record or {})
        for symbol, record in dict(snapshot.get("payload_inventory") or {}).items()
    }
    actual_inventory = _payload_inventory(payloads)
    if recorded_inventory != actual_inventory:
        blockers.append("replay_payload_inventory_invalid")
    expected_row_count = int(manifest.get("row_count") or 0)
    expected_first = str(manifest.get("first") or "")
    expected_last = str(manifest.get("last") or "")
    for symbol in expected_symbols:
        record = actual_inventory.get(symbol) or {}
        if int(record.get("row_count") or 0) != expected_row_count:
            blockers.append(f"replay_symbol_row_count_mismatch:{symbol}")
        if str(record.get("first") or "") != expected_first:
            blockers.append(f"replay_symbol_first_date_mismatch:{symbol}")
        if str(record.get("last") or "") != expected_last:
            blockers.append(f"replay_symbol_last_date_mismatch:{symbol}")

    expected_results = dict(snapshot.get("expected_results") or {})
    for stage in REPLAY_STAGES:
        recorded = dict(expected_results.get(stage) or {})
        report_result = dict(report.get(stage) or {})
        if str(recorded.get("run_hash") or "") != str(report_result.get("run_hash") or ""):
            blockers.append(f"replay_expected_run_hash_mismatch:{stage}")
        if str(recorded.get("result_hash") or "") != canonical_hash(report_result):
            blockers.append(f"replay_expected_result_hash_mismatch:{stage}")
    expected_benchmarks = dict(snapshot.get("expected_benchmark_result_hashes") or {})
    for stage in ("validation_benchmark", "test_benchmark"):
        if str(expected_benchmarks.get(stage) or "") != canonical_hash(dict(report.get(stage) or {})):
            blockers.append(f"replay_expected_benchmark_hash_mismatch:{stage}")
    if str(snapshot.get("expected_cost_stress_hash") or "") != canonical_hash(list(report.get("cost_stress") or [])):
        blockers.append("replay_expected_cost_stress_hash_mismatch")
    if _sensitive_field_paths(snapshot):
        blockers.append("replay_dataset_contains_credential_fields")
    if _authority_violations(snapshot):
        blockers.append("replay_dataset_contains_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "snapshot_hash": expected_snapshot_hash,
        "dataset_hash": str(snapshot.get("candidate_dataset_hash") or ""),
        "symbol_count": len(expected_symbols),
        "row_count": int(snapshot.get("row_count") or 0),
        "evidence_bundle_verification": snapshot_bundle_audit,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def load_replay_payloads_from_local_cache(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    from exchange_terminal import server
    from exchange_terminal.market_data.stock_candles_io import read_stock_persistent_candle_cache
    from .portfolio_backtest import (
        prepare_attested_portfolio_dataset,
        slice_portfolio_payload_through_date,
    )
    from .portfolio_evidence_bundle import expand_portfolio_evidence_bundle

    report, report_bundle_audit = expand_portfolio_evidence_bundle(
        report,
        require_bundle=bool((report.get("spec") or {}).get("evidence_bundle_required") is True),
    )
    if report_bundle_audit.get("status") != "PASS":
        raise ValueError(
            "Research evidence bundle failed verification: "
            + ",".join(report_bundle_audit.get("blockers") or [])
        )

    manifest = dict(report.get("dataset_manifest") or {})
    symbols = [str(symbol).upper() for symbol in manifest.get("symbols") or []]
    benchmark = str(manifest.get("benchmark_symbol") or "").upper()
    cutoff = str(manifest.get("last") or "")[:10]
    required_rows = int(manifest.get("row_count") or 0)
    requested_limit = max(int(dict(report.get("spec") or {}).get("requested_history_limit") or 0), required_rows, 180)
    dataset_lineage_id = str(dict(report.get("spec") or {}).get("experiment_id") or "").strip()
    if not symbols or not benchmark or not cutoff or required_rows <= 0:
        raise ValueError("Research report has an invalid replay dataset contract")

    for symbol in symbols:
        cached = read_stock_persistent_candle_cache(symbol, requested_limit, "1d", "regular")
        rows = [
            dict(row)
            for row in dict(cached or {}).get("rows") or []
            if candle_is_complete(row, default_if_missing=False)
            and str(row.get("date") or "")[:10] <= cutoff
        ]
        if len(rows) < required_rows:
            raise ValueError(f"Local replay cache is incomplete for {symbol}: {len(rows)}<{required_rows}")

    raw = {
        symbol: slice_portfolio_payload_through_date(
            server.backtest_market_rows(symbol, requested_limit, dataset_lineage_id=dataset_lineage_id),
            cutoff,
            attest_backtest_rows=server.attest_stock_backtest_rows,
            dataset_lineage_id=dataset_lineage_id,
        )
        for symbol in symbols
    }
    prepared = prepare_attested_portfolio_dataset(
        raw,
        benchmark_symbol=benchmark,
        minimum_rows=required_rows,
        attest_backtest_rows=server.attest_stock_backtest_rows,
        dataset_lineage_id=dataset_lineage_id,
        universe_contract=dict(report.get("universe_contract") or {}),
    )
    rebuilt = dict(prepared.get("manifest") or {})
    if prepared.get("status") != "PASS":
        raise ValueError(f"Local replay dataset gate failed: {rebuilt.get('blockers')}")
    if str(rebuilt.get("data_hash") or "") != str(manifest.get("data_hash") or ""):
        raise ValueError("Local cache no longer reproduces the frozen dataset hash")
    if str(rebuilt.get("manifest_hash") or "") != str(manifest.get("manifest_hash") or ""):
        raise ValueError("Local cache no longer reproduces the frozen dataset manifest")
    return {
        str(symbol).upper(): deepcopy(dict(payload or {}))
        for symbol, payload in dict(prepared.get("payloads") or {}).items()
    }


def stage_portfolio_backtest_replay_bundle(
    bundle_dir: Path | str,
    *,
    source_report_path: Path | str,
    source_report_archive_path: str,
) -> dict[str, Any]:
    bundle = Path(bundle_dir).resolve()
    report_path = Path(source_report_path).resolve()
    report = _read_json(report_path)
    report_sha = file_sha256(report_path)
    payloads = load_replay_payloads_from_local_cache(report)
    snapshot = build_portfolio_backtest_replay_dataset(
        report,
        payloads,
        source_report_file=Path(source_report_archive_path).name,
        source_report_file_sha256=report_sha,
    )
    dataset_path = bundle / "datasets" / DEFAULT_REPLAY_DATASET_FILE
    _write_canonical_json(dataset_path, snapshot)
    driver_source = (
        bundle
        / "source"
        / "exchange_terminal"
        / "services"
        / DEFAULT_REPLAY_DRIVER_FILE
    )
    if not driver_source.is_file():
        raise FileNotFoundError(driver_source)
    driver_path = bundle / "replay" / DEFAULT_REPLAY_DRIVER_FILE
    driver_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(driver_source, driver_path)
    descriptor = {
        "schema_version": PORTFOLIO_BACKTEST_REPLAY_BUNDLE_SCHEMA_VERSION,
        "dataset_archive_path": dataset_path.relative_to(bundle).as_posix(),
        "dataset_file_sha256": file_sha256(dataset_path),
        "dataset_snapshot_hash": str(snapshot.get("snapshot_hash") or ""),
        "candidate_dataset_hash": str(snapshot.get("candidate_dataset_hash") or ""),
        "candidate_dataset_manifest_hash": str(snapshot.get("candidate_dataset_manifest_hash") or ""),
        "source_report_archive_path": str(source_report_archive_path),
        "source_report_file_sha256": report_sha,
        "driver_archive_path": driver_path.relative_to(bundle).as_posix(),
        "driver_file_sha256": file_sha256(driver_path),
        "source_archive_path": "source",
        "symbol_count": int(snapshot.get("symbol_count") or 0),
        "row_count": int(snapshot.get("row_count") or 0),
        "capture_policy": str(snapshot.get("capture_policy") or ""),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    rehearsal = run_isolated_portfolio_backtest_replay(bundle, descriptor)
    if rehearsal.get("status") != "PASS":
        raise ValueError(f"Isolated portfolio replay failed: {rehearsal.get('blockers')}")
    descriptor["replay_rehearsal"] = rehearsal
    descriptor["bundle_hash"] = canonical_hash(descriptor)
    return descriptor


def _sanitized_subprocess_environment() -> dict[str, str]:
    environment: dict[str, str] = {}
    for key, value in os.environ.items():
        upper = key.upper()
        if any(marker in upper for marker in SENSITIVE_ENV_MARKERS):
            continue
        environment[key] = value
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def run_isolated_portfolio_backtest_replay(
    bundle_dir: Path | str,
    descriptor: dict[str, Any],
    *,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    bundle = Path(bundle_dir).resolve()
    try:
        driver = _safe_bundle_path(bundle, str(descriptor.get("driver_archive_path") or ""))
        source_root = _safe_bundle_path(bundle, str(descriptor.get("source_archive_path") or ""))
        dataset = _safe_bundle_path(bundle, str(descriptor.get("dataset_archive_path") or ""))
        report = _safe_bundle_path(bundle, str(descriptor.get("source_report_archive_path") or ""))
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                str(driver),
                "--source-root",
                str(source_root),
                "--dataset",
                str(dataset),
                "--report",
                str(report),
            ],
            cwd=bundle,
            env=_sanitized_subprocess_environment(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(int(timeout_seconds), 1),
            check=False,
        )
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return {
            "schema_version": PORTFOLIO_BACKTEST_REPLAY_RESULT_SCHEMA_VERSION,
            "status": "BLOCK",
            "blockers": [f"isolated_replay_process_failed:{type(exc).__name__}"],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    if completed.returncode != 0:
        try:
            blocked_payload = json.loads(completed.stdout)
        except (TypeError, json.JSONDecodeError):
            blocked_payload = None
        if (
            isinstance(blocked_payload, dict)
            and blocked_payload.get("status") == "BLOCK"
            and isinstance(blocked_payload.get("blockers"), list)
        ):
            return blocked_payload
        return {
            "schema_version": PORTFOLIO_BACKTEST_REPLAY_RESULT_SCHEMA_VERSION,
            "status": "BLOCK",
            "blockers": [f"isolated_replay_exit_code:{completed.returncode}"],
            "stderr": completed.stderr[-1000:],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    try:
        payload = json.loads(completed.stdout)
    except (TypeError, json.JSONDecodeError):
        return {
            "schema_version": PORTFOLIO_BACKTEST_REPLAY_RESULT_SCHEMA_VERSION,
            "status": "BLOCK",
            "blockers": ["isolated_replay_output_invalid"],
            "stderr": completed.stderr[-1000:],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    if not isinstance(payload, dict):
        return {
            "schema_version": PORTFOLIO_BACKTEST_REPLAY_RESULT_SCHEMA_VERSION,
            "status": "BLOCK",
            "blockers": ["isolated_replay_output_not_object"],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    return payload


def verify_portfolio_backtest_replay_bundle(
    bundle_dir: Path | str,
    descriptor: dict[str, Any],
    *,
    perform_replay: bool = True,
) -> dict[str, Any]:
    bundle = Path(bundle_dir).resolve()
    blockers: list[str] = []
    clean_descriptor = dict(descriptor or {})
    expected_bundle_hash = str(clean_descriptor.pop("bundle_hash", "") or "")
    if descriptor.get("schema_version") != PORTFOLIO_BACKTEST_REPLAY_BUNDLE_SCHEMA_VERSION:
        blockers.append("replay_bundle_schema_invalid")
    if not expected_bundle_hash or canonical_hash(clean_descriptor) != expected_bundle_hash:
        blockers.append("replay_bundle_hash_invalid")
    try:
        dataset_path = _safe_bundle_path(bundle, str(descriptor.get("dataset_archive_path") or ""))
        report_path = _safe_bundle_path(bundle, str(descriptor.get("source_report_archive_path") or ""))
        driver_path = _safe_bundle_path(bundle, str(descriptor.get("driver_archive_path") or ""))
        for path, expected, label in (
            (dataset_path, descriptor.get("dataset_file_sha256"), "dataset"),
            (report_path, descriptor.get("source_report_file_sha256"), "source_report"),
            (driver_path, descriptor.get("driver_file_sha256"), "driver"),
        ):
            if not path.is_file() or file_sha256(path) != str(expected or ""):
                blockers.append(f"replay_{label}_file_hash_mismatch")
        snapshot = _read_json(dataset_path)
        report = _read_json(report_path)
        if str(snapshot.get("source_report_file") or "") != report_path.name:
            blockers.append("replay_source_report_filename_mismatch")
        dataset_verification = verify_portfolio_backtest_replay_dataset(
            snapshot,
            report,
            actual_source_report_sha256=file_sha256(report_path),
        )
        if dataset_verification.get("status") != "PASS":
            blockers.extend(dataset_verification.get("blockers") or [])
        if str(descriptor.get("dataset_snapshot_hash") or "") != str(snapshot.get("snapshot_hash") or ""):
            blockers.append("replay_dataset_snapshot_binding_mismatch")
        if str(descriptor.get("candidate_dataset_hash") or "") != str(snapshot.get("candidate_dataset_hash") or ""):
            blockers.append("replay_dataset_hash_binding_mismatch")
        if str(descriptor.get("candidate_dataset_manifest_hash") or "") != str(snapshot.get("candidate_dataset_manifest_hash") or ""):
            blockers.append("replay_dataset_manifest_binding_mismatch")
        if int(descriptor.get("symbol_count") or 0) != int(snapshot.get("symbol_count") or 0):
            blockers.append("replay_symbol_count_binding_mismatch")
        if int(descriptor.get("row_count") or 0) != int(snapshot.get("row_count") or 0):
            blockers.append("replay_row_count_binding_mismatch")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        blockers.append(f"replay_bundle_files_unavailable:{type(exc).__name__}")
        dataset_verification = {}

    replay: dict[str, Any] = {}
    if perform_replay and not blockers:
        replay = run_isolated_portfolio_backtest_replay(bundle, descriptor)
        if replay.get("status") != "PASS":
            blockers.extend(replay.get("blockers") or ["isolated_replay_blocked"])
        recorded = dict(descriptor.get("replay_rehearsal") or {})
        if str(replay.get("replay_hash") or "") != str(recorded.get("replay_hash") or ""):
            blockers.append("isolated_replay_rehearsal_hash_mismatch")
    if _authority_violations(descriptor):
        blockers.append("replay_bundle_contains_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "dataset_status": str(dataset_verification.get("status") or "BLOCK"),
        "replay_status": str(replay.get("status") or ("NOT_RUN" if not perform_replay else "BLOCK")),
        "replay_hash": str(replay.get("replay_hash") or ""),
        "dataset_hash": str(descriptor.get("candidate_dataset_hash") or ""),
        "symbol_count": int(descriptor.get("symbol_count") or 0),
        "row_count": int(descriptor.get("row_count") or 0),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
