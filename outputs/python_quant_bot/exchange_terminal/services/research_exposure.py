from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any


RESEARCH_EXPOSURE_AUDIT_VERSION = "research-exposure-audit-v3"
PORTFOLIO_TEMPORAL_EXPOSURE_VERSION = "portfolio-temporal-exposure-v1"


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _read_report(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def prior_symbol_exposure(report_dir: Path | str) -> dict[str, list[dict[str, Any]]]:
    directory = Path(report_dir)
    exposure: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(directory.glob("strategy_research_*.json")):
        payload = _read_report(path)
        batch_spec = payload.get("batch_spec") if isinstance(payload.get("batch_spec"), dict) else {}
        selection = {str(item).upper() for item in batch_spec.get("selection_symbols") or []}
        holdout = {str(item).upper() for item in batch_spec.get("holdout_symbols") or []}
        tested = {str(cell.get("symbol") or "").upper() for cell in payload.get("test_cells") or []}
        holdout_loaded = {str(cell.get("symbol") or "").upper() for cell in payload.get("holdout_cells") or []}
        manifests = payload.get("dataset_manifest") if isinstance(payload.get("dataset_manifest"), list) else []
        for manifest in manifests:
            if not isinstance(manifest, dict):
                continue
            symbol = str(manifest.get("symbol") or "").upper()
            if not symbol:
                continue
            roles: list[str] = []
            if symbol in selection:
                roles.append("SELECTION_DEVELOPMENT")
            if symbol in tested:
                roles.append("SELECTION_TEST_EXPOSED")
            if symbol in holdout and symbol in holdout_loaded:
                roles.append("HOLDOUT_EXPOSED")
            exposure.setdefault(symbol, []).append({
                "report": str(path),
                "batch_run_hash": str(payload.get("batch_run_hash") or ""),
                "dataset_hash": str(manifest.get("data_hash") or ""),
                "first": str(manifest.get("first") or ""),
                "last": str(manifest.get("last") or ""),
                "roles": roles or ["DATASET_LOADED"],
            })
    for path in sorted(directory.glob("portfolio_research_*.json")):
        payload = _read_report(path)
        spec = payload.get("spec") if isinstance(payload.get("spec"), dict) else {}
        manifest = payload.get("dataset_manifest") if isinstance(payload.get("dataset_manifest"), dict) else {}
        benchmark = str(spec.get("benchmark_symbol") or "").upper()
        tradables = {str(item).upper() for item in spec.get("tradable_symbols") or []}
        symbols = {str(item).upper() for item in manifest.get("symbols") or []}
        for symbol in sorted(symbols):
            roles: list[str] = []
            if symbol == benchmark:
                roles.append("PORTFOLIO_BENCHMARK_EXPOSED")
            if symbol in tradables:
                roles.append("PORTFOLIO_DEVELOPMENT_EXPOSED")
            exposure.setdefault(symbol, []).append({
                "report": str(path),
                "batch_run_hash": str(payload.get("batch_run_hash") or ""),
                "dataset_hash": str(manifest.get("data_hash") or ""),
                "first": str(manifest.get("first") or ""),
                "last": str(manifest.get("last") or ""),
                "roles": roles or ["PORTFOLIO_DATASET_LOADED"],
            })
    for path in sorted(directory.glob("portfolio_holdout_*.json")):
        payload = _read_report(path)
        spec = payload.get("spec") if isinstance(payload.get("spec"), dict) else {}
        manifest = payload.get("dataset_manifest") if isinstance(payload.get("dataset_manifest"), dict) else {}
        benchmark = str(spec.get("benchmark_symbol") or "").upper()
        holdouts = {str(item).upper() for item in spec.get("holdout_symbols") or []}
        symbols = {str(item).upper() for item in manifest.get("symbols") or []}
        for symbol in sorted(symbols):
            roles: list[str] = []
            if symbol == benchmark:
                roles.append("PORTFOLIO_HOLDOUT_BENCHMARK_EXPOSED")
            if symbol in holdouts:
                roles.append("PORTFOLIO_CROSS_SECTIONAL_HOLDOUT_EXPOSED")
            exposure.setdefault(symbol, []).append({
                "report": str(path),
                "batch_run_hash": str(payload.get("batch_run_hash") or ""),
                "dataset_hash": str(manifest.get("data_hash") or ""),
                "first": str(manifest.get("first") or ""),
                "last": str(manifest.get("last") or ""),
                "roles": roles or ["PORTFOLIO_HOLDOUT_DATASET_LOADED"],
            })
    return exposure


def audit_blind_holdout_symbols(report_dir: Path | str, symbols: list[str]) -> dict[str, Any]:
    exposure = prior_symbol_exposure(report_dir)
    normalized = list(dict.fromkeys(str(symbol or "").upper() for symbol in symbols if str(symbol or "").strip()))
    exposed = {symbol: exposure[symbol] for symbol in normalized if exposure.get(symbol)}
    return {
        "version": RESEARCH_EXPOSURE_AUDIT_VERSION,
        "status": "PASS" if not exposed else "BLOCK",
        "symbols": normalized,
        "exposed_symbols": sorted(exposed),
        "evidence": exposed,
        "blockers": [f"prior_research_exposure:{symbol}" for symbol in sorted(exposed)],
    }


def _evaluation_window(payload: dict[str, Any], stage: str) -> tuple[str, str]:
    section = payload.get(stage) if isinstance(payload.get(stage), dict) else {}
    window = section.get("evaluation_window") if isinstance(section.get("evaluation_window"), dict) else {}
    return str(window.get("start") or "")[:10], str(window.get("end") or "")[:10]


def _windows_overlap(left_start: str, left_end: str, right_start: str, right_end: str) -> bool:
    try:
        left = (date.fromisoformat(left_start), date.fromisoformat(left_end))
        right = (date.fromisoformat(right_start), date.fromisoformat(right_end))
    except ValueError:
        return False
    return left[0] <= right[1] and right[0] <= left[1]


def audit_portfolio_temporal_exposure(
    report_dir: Path | str,
    *,
    start_date: str,
    end_date: str,
    symbols: list[str],
    exclude_paths: list[Path | str] | None = None,
) -> dict[str, Any]:
    clean_start = str(start_date or "")[:10]
    clean_end = str(end_date or "")[:10]
    normalized_symbols = sorted({str(symbol or "").upper() for symbol in symbols if str(symbol or "").strip()})
    blockers: list[str] = []
    try:
        if date.fromisoformat(clean_start) > date.fromisoformat(clean_end):
            blockers.append("temporal_window_reversed")
    except ValueError:
        blockers.append("temporal_window_invalid")
    if not normalized_symbols:
        blockers.append("temporal_symbols_missing")

    excluded = {Path(path).resolve() for path in (exclude_paths or [])}
    exposures: list[dict[str, Any]] = []
    directory = Path(report_dir)
    if not blockers:
        for path in sorted(directory.glob("portfolio_research_*.json")):
            if path.resolve() in excluded:
                continue
            payload = _read_report(path)
            spec = payload.get("spec") if isinstance(payload.get("spec"), dict) else {}
            manifest = payload.get("dataset_manifest") if isinstance(payload.get("dataset_manifest"), dict) else {}
            prior_symbols = {
                str(symbol or "").upper()
                for symbol in manifest.get("symbols") or [
                    spec.get("benchmark_symbol"),
                    *(spec.get("tradable_symbols") or []),
                ]
                if str(symbol or "").strip()
            }
            shared_symbols = sorted(set(normalized_symbols) & prior_symbols)
            if not shared_symbols:
                continue
            overlapping_stages: list[dict[str, str]] = []
            for stage in ("validation", "test", "full"):
                prior_start, prior_end = _evaluation_window(payload, stage)
                if _windows_overlap(clean_start, clean_end, prior_start, prior_end):
                    overlapping_stages.append({"stage": stage.upper(), "start": prior_start, "end": prior_end})
            if not overlapping_stages:
                continue
            test = payload.get("test") if isinstance(payload.get("test"), dict) else {}
            exposures.append({
                "report": str(path.resolve()),
                "batch_run_hash": str(payload.get("batch_run_hash") or ""),
                "dataset_hash": str(manifest.get("data_hash") or ""),
                "spec_hash": str(payload.get("spec_hash") or ""),
                "test_run_hash": str(test.get("run_hash") or ""),
                "shared_symbols": shared_symbols,
                "overlapping_stages": overlapping_stages,
            })

    if exposures:
        blockers.append(f"temporal_window_previously_exposed:{len(exposures)}")
    distinct_batch_hashes = sorted({item["batch_run_hash"] for item in exposures if item["batch_run_hash"]})
    distinct_test_run_hashes = sorted({item["test_run_hash"] for item in exposures if item["test_run_hash"]})
    payload = {
        "schema_version": PORTFOLIO_TEMPORAL_EXPOSURE_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "classification": "UNTOUCHED" if not exposures and not blockers else "EXPOSED" if exposures else "INVALID",
        "window": {"start": clean_start, "end": clean_end},
        "symbols": normalized_symbols,
        "prior_report_count": len(exposures),
        "distinct_batch_count": len(distinct_batch_hashes),
        "distinct_test_run_count": len(distinct_test_run_hashes),
        "fresh_holdout_eligible": not blockers,
        "blockers": blockers,
        "evidence": exposures,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["audit_hash"] = _canonical_hash(payload)
    return payload
