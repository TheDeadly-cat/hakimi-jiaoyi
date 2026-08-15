from __future__ import annotations

import hashlib
import json
from typing import Any

from .research_symbol_market import research_market_for_symbol


STRATEGY_SELECTION_ALIGNMENT_INPUT_SCHEMA_VERSION = (
    "strategy-selection-alignment-input-v1"
)
_COMPLETION_FIELDS = ("complete", "confirm", "confirmed", "provisional")


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def alignment_row_projection(row: dict[str, Any] | Any) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValueError("strategy_selection_alignment_row_invalid")
    projected = {"date": row.get("date")}
    for field in _COMPLETION_FIELDS:
        if field in row:
            projected[field] = row.get(field)
    return projected


def build_strategy_selection_alignment_input_snapshot(
    payloads: dict[str, dict[str, Any]] | Any,
    manifests: list[dict[str, Any]] | Any,
) -> dict[str, Any]:
    if not isinstance(payloads, dict):
        raise ValueError("strategy_selection_alignment_payloads_invalid")
    if not isinstance(manifests, list) or not all(
        isinstance(item, dict) for item in manifests
    ):
        raise ValueError("strategy_selection_alignment_manifests_invalid")
    manifest_by_symbol = {
        str(item.get("symbol") or "").strip().upper(): dict(item)
        for item in manifests
        if str(item.get("role") or "") == "SELECTION"
        and str(item.get("symbol") or "").strip()
    }
    if len(manifest_by_symbol) != len(manifests):
        raise ValueError("strategy_selection_alignment_manifest_identity_invalid")
    datasets: list[dict[str, Any]] = []
    for raw_symbol in sorted(payloads):
        symbol = str(raw_symbol or "").strip().upper()
        payload = payloads[raw_symbol]
        if not symbol or not isinstance(payload, dict):
            raise ValueError("strategy_selection_alignment_payload_identity_invalid")
        rows = payload.get("rows")
        manifest = manifest_by_symbol.get(symbol)
        if not isinstance(rows, list) or manifest is None:
            raise ValueError("strategy_selection_alignment_payload_binding_missing")
        if str(manifest.get("source") or "") != str(payload.get("source") or ""):
            raise ValueError("strategy_selection_alignment_source_mismatch")
        projected_rows = [alignment_row_projection(item) for item in rows]
        datasets.append({
            "role": "SELECTION",
            "symbol": symbol,
            "market": research_market_for_symbol(symbol),
            "timeframe": "1D",
            "source": str(payload.get("source") or ""),
            "alignment_rows": projected_rows,
            "manifest_hash": _canonical_hash(manifest),
        })
    if set(manifest_by_symbol) != {
        str(item.get("symbol") or "") for item in datasets
    }:
        raise ValueError("strategy_selection_alignment_manifest_coverage_invalid")
    content = {
        "schema_version": STRATEGY_SELECTION_ALIGNMENT_INPUT_SCHEMA_VERSION,
        "datasets": datasets,
        "dataset_count": len(datasets),
        "row_count": sum(len(item["alignment_rows"]) for item in datasets),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {**content, "input_hash": _canonical_hash(content)}


def verify_strategy_selection_alignment_input_snapshot(
    snapshot: dict[str, Any] | Any,
    *,
    expected_symbols: set[str],
    manifests: list[dict[str, Any]],
) -> dict[str, Any]:
    blockers: list[str] = []
    if not isinstance(snapshot, dict):
        return {
            "status": "BLOCK",
            "blockers": ["strategy_selection_alignment_input_missing"],
            "payloads": {},
        }
    datasets = snapshot.get("datasets")
    if not isinstance(datasets, list) or not all(
        isinstance(item, dict) for item in datasets
    ):
        return {
            "status": "BLOCK",
            "blockers": ["strategy_selection_alignment_input_datasets_invalid"],
            "payloads": {},
        }
    manifest_by_symbol = {
        str(item.get("symbol") or "").strip().upper(): dict(item)
        for item in manifests
        if isinstance(item, dict)
        and str(item.get("role") or "") == "SELECTION"
        and str(item.get("symbol") or "").strip()
    }
    if len(manifest_by_symbol) != len(manifests):
        blockers.append("strategy_selection_manifest_identity_invalid")
    payloads: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for item in datasets:
        symbol = str(item.get("symbol") or "").strip().upper()
        rows = item.get("alignment_rows")
        if not symbol or symbol in seen:
            blockers.append("strategy_selection_alignment_input_symbol_invalid")
            continue
        seen.add(symbol)
        try:
            expected_market = research_market_for_symbol(symbol)
        except ValueError:
            expected_market = ""
        if (
            item.get("role") != "SELECTION"
            or item.get("timeframe") != "1D"
            or not expected_market
            or item.get("market") != expected_market
            or not isinstance(rows, list)
            or not all(isinstance(row, dict) for row in rows)
        ):
            blockers.append(
                f"strategy_selection_alignment_input_dataset_invalid:{symbol}"
            )
            continue
        manifest = manifest_by_symbol.get(symbol)
        if manifest is None or item.get("manifest_hash") != _canonical_hash(manifest):
            blockers.append(
                f"strategy_selection_alignment_input_manifest_mismatch:{symbol}"
            )
        elif str(item.get("source") or "") != str(manifest.get("source") or ""):
            blockers.append(
                f"strategy_selection_alignment_input_source_mismatch:{symbol}"
            )
        payloads[symbol] = {
            "source": str(item.get("source") or ""),
            "rows": [dict(row) for row in rows],
        }
    normalized_expected = {
        str(symbol or "").strip().upper() for symbol in expected_symbols
    }
    if seen != normalized_expected or set(manifest_by_symbol) != normalized_expected:
        blockers.append("strategy_selection_alignment_input_coverage_mismatch")
    try:
        expected = build_strategy_selection_alignment_input_snapshot(
            payloads,
            list(manifest_by_symbol.values()),
        )
    except (TypeError, ValueError):
        expected = {}
        blockers.append("strategy_selection_alignment_input_rebuild_failed")
    if snapshot != expected:
        blockers.append("strategy_selection_alignment_input_semantic_mismatch")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "payloads": payloads if not blockers else {},
    }


__all__ = [
    "STRATEGY_SELECTION_ALIGNMENT_INPUT_SCHEMA_VERSION",
    "alignment_row_projection",
    "build_strategy_selection_alignment_input_snapshot",
    "verify_strategy_selection_alignment_input_snapshot",
]
