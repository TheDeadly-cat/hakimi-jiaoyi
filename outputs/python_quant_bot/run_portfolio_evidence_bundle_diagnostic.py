from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time
from typing import Any

from exchange_terminal.services.portfolio_evidence_bundle import (
    expand_portfolio_evidence_bundle,
    pack_portfolio_evidence_bundle,
    verify_portfolio_evidence_bundle,
)


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _first_ref(compact: dict[str, Any]) -> dict[str, Any]:
    stack: list[Any] = [compact]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            if value.get("schema_version") == "market-data-snapshot-ref-v1":
                return value
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)
    return {}


def _cross_source_records(payload: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            if (
                "primary_snapshot_hash" in value
                and "secondary_snapshot_hash" in value
                and "primary_snapshot" in value
                and "secondary_snapshot" in value
            ):
                records.append(value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    return records


def _shared_alias_case(original: dict[str, Any]) -> dict[str, Any]:
    records = _cross_source_records(original)
    if not records:
        return {
            "case": "SHARED_CROSS_SOURCE_OBJECT_ALIAS",
            "status": "BLOCK",
            "blockers": ["cross_source_fixture_missing"],
        }
    shared = deepcopy(records[0])
    payload = {
        "first": {"cross_source": [shared]},
        "second": {"cross_source": [shared]},
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    try:
        compact = pack_portfolio_evidence_bundle(payload)
        expanded, audit = expand_portfolio_evidence_bundle(compact, require_bundle=True)
    except (TypeError, ValueError) as exc:
        return {
            "case": "SHARED_CROSS_SOURCE_OBJECT_ALIAS",
            "status": "BLOCK",
            "blockers": [f"shared_alias_pack_failed:{type(exc).__name__}:{exc}"],
        }
    bundle = dict(compact.get("evidence_bundle") or {})
    checks = {
        "bundle_verification_pass": audit.get("status") == "PASS",
        "expanded_semantics_equal": expanded == payload,
        "two_unique_snapshots": bundle.get("entry_count") == 2,
        "four_logical_references": bundle.get("reference_count") == 4,
    }
    return {
        "case": "SHARED_CROSS_SOURCE_OBJECT_ALIAS",
        "status": "PASS" if all(checks.values()) else "BLOCK",
        "checks": checks,
        "bundle_hash": bundle.get("bundle_hash"),
        "blockers": list(audit.get("blockers") or []),
    }


def _adversarial_cases(compact: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    tampered_payload = deepcopy(compact)
    bundle = dict(tampered_payload.get("evidence_bundle") or {})
    entries = bundle.get("entries") if isinstance(bundle.get("entries"), dict) else {}
    if entries:
        first_hash = next(iter(entries))
        entry = entries[first_hash]
        encoded = str(entry.get("payload") or "")
        entry["payload"] = encoded[:-1] + ("A" if encoded[-1:] != "A" else "B")
    payload_audit = verify_portfolio_evidence_bundle(tampered_payload, require_bundle=True)
    cases.append({
        "case": "COMPRESSED_PAYLOAD_TAMPER",
        "expected": "BLOCK",
        "observed": payload_audit.get("status"),
        "blockers": payload_audit.get("blockers"),
    })

    missing_entry = deepcopy(compact)
    bundle = dict(missing_entry.get("evidence_bundle") or {})
    entries = bundle.get("entries") if isinstance(bundle.get("entries"), dict) else {}
    if entries:
        entries.pop(next(iter(entries)))
    missing_audit = verify_portfolio_evidence_bundle(missing_entry, require_bundle=True)
    cases.append({
        "case": "REFERENCED_ENTRY_REMOVAL",
        "expected": "BLOCK",
        "observed": missing_audit.get("status"),
        "blockers": missing_audit.get("blockers"),
    })

    ref_tamper = deepcopy(compact)
    ref = _first_ref(ref_tamper)
    if ref:
        ref["row_count"] = int(ref.get("row_count") or 0) + 1
    ref_audit = verify_portfolio_evidence_bundle(ref_tamper, require_bundle=True)
    cases.append({
        "case": "SNAPSHOT_REF_METADATA_TAMPER",
        "expected": "BLOCK",
        "observed": ref_audit.get("status"),
        "blockers": ref_audit.get("blockers"),
    })
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure and adversarially verify content-addressed portfolio evidence packaging."
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source = args.source.resolve()
    output = args.output.resolve()
    original = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(original, dict):
        raise ValueError("Source report must be a JSON object")
    compact = pack_portfolio_evidence_bundle(original)
    expanded, bundle_audit = expand_portfolio_evidence_bundle(compact, require_bundle=True)
    original_pretty_bytes = len(json.dumps(original, ensure_ascii=False, indent=2).encode("utf-8"))
    compact_pretty_bytes = len(json.dumps(compact, ensure_ascii=False, indent=2).encode("utf-8"))
    cases = _adversarial_cases(compact)
    shared_alias_case = _shared_alias_case(original)
    semantic_equal = expanded == original
    reduction_pct = (
        round((1.0 - compact_pretty_bytes / original_pretty_bytes) * 100.0, 6)
        if original_pretty_bytes else 0.0
    )
    checks = {
        "bundle_verification_pass": bundle_audit.get("status") == "PASS",
        "expanded_semantics_exactly_equal": semantic_equal,
        "canonical_semantic_hash_equal": canonical_hash(expanded) == canonical_hash(original),
        "pretty_size_reduction_at_least_80_pct": reduction_pct >= 80.0,
        "all_adversarial_cases_blocked": all(
            item.get("observed") == item.get("expected") == "BLOCK" for item in cases
        ),
        "shared_cross_source_alias_supported": shared_alias_case.get("status") == "PASS",
        "no_parameter_selection": True,
        "no_execution_authority": True,
    }
    payload = {
        "schema_version": "portfolio-evidence-bundle-diagnostic-v1",
        "status": "PASS" if all(checks.values()) else "BLOCK",
        "generated_at": int(time.time() * 1000),
        "source_report": source.name,
        "source_report_file_sha256": file_sha256(source),
        "source_report_batch_hash": str(original.get("batch_run_hash") or ""),
        "source_pretty_bytes": original_pretty_bytes,
        "compact_pretty_bytes": compact_pretty_bytes,
        "reduction_pct": reduction_pct,
        "source_semantic_hash": canonical_hash(original),
        "expanded_semantic_hash": canonical_hash(expanded),
        "bundle_verification": bundle_audit,
        "checks": checks,
        "adversarial_cases": cases,
        "shared_alias_case": shared_alias_case,
        "parameter_selection_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["report_hash"] = canonical_hash(payload)
    atomic_write_json(output, payload)
    print(json.dumps({
        "status": payload["status"],
        "source_pretty_bytes": original_pretty_bytes,
        "compact_pretty_bytes": compact_pretty_bytes,
        "reduction_pct": reduction_pct,
        "bundle_hash": bundle_audit.get("bundle_hash"),
        "report_hash": payload["report_hash"],
        "output": str(output),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
