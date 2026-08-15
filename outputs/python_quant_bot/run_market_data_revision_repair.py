from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from exchange_terminal import config
from exchange_terminal.market_data.stock_candles_io import MARKET_DATA_REVISION_LEDGER
from exchange_terminal.services.market_data_revision_ledger import build_cross_source_evidence


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Restore verified provider snapshots and explicitly resolve revision blockers."
    )
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--primary-snapshot", required=True)
    parser.add_argument("--secondary-snapshot", required=True)
    parser.add_argument("--primary-event", default="")
    parser.add_argument("--secondary-event", default="")
    parser.add_argument("--reason", required=True)
    parser.add_argument("--invalidation-artifact", default="")
    parser.add_argument("--output", default="")
    return parser.parse_args()


def public_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in snapshot.items() if key != "rows"}


def validate_snapshot(snapshot: dict[str, Any], symbol: str, expected_family: str) -> None:
    if not snapshot:
        raise ValueError(f"{expected_family}_snapshot_missing")
    if str(snapshot.get("symbol") or "").upper() != symbol:
        raise ValueError(f"{expected_family}_snapshot_symbol_mismatch")
    if str(snapshot.get("provider_family") or "").lower() != expected_family:
        raise ValueError(f"{expected_family}_snapshot_provider_mismatch")
    if str(snapshot.get("role") or "").upper() != "PROVIDER_OBSERVATION":
        raise ValueError(f"{expected_family}_snapshot_role_mismatch")
    if int(snapshot.get("row_count") or 0) < 120:
        raise ValueError(f"{expected_family}_snapshot_rows_insufficient")
    if str(snapshot.get("snapshot_hash") or "") != canonical_hash({
        key: value for key, value in snapshot.items() if key not in {"rows", "snapshot_hash"}
    }):
        raise ValueError(f"{expected_family}_snapshot_hash_mismatch")


def resolve_if_blocked(
    restore: dict[str, Any],
    *,
    event_hash: str,
    reason: str,
    source_label: str,
) -> dict[str, Any]:
    expected_event = str(event_hash or "").strip()
    observed_event = str(restore.get("blocking_event_hash") or "").strip()
    if expected_event:
        if observed_event != expected_event:
            raise ValueError(f"{source_label}_blocking_event_mismatch")
        return MARKET_DATA_REVISION_LEDGER.resolve_blocking_revision(
            scope_key=str(restore.get("scope_key") or ""),
            event_hash=expected_event,
            reason=reason,
        )
    if str(restore.get("status") or "") == "BLOCK" or observed_event:
        raise ValueError(f"{source_label}_blocking_event_required")
    return {
        "schema_version": "market-data-revision-resolution-not-required-v1",
        "status": "NOT_REQUIRED",
        "scope_key": str(restore.get("scope_key") or ""),
        "event_hash": "",
        "reason": "source_scope_not_blocked",
        "resolution_hash": "",
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def main() -> int:
    args = parse_args()
    symbol = str(args.symbol or "").strip().upper()
    reason = str(args.reason or "").strip()
    if not reason:
        raise ValueError("revision_repair_reason_required")

    primary = MARKET_DATA_REVISION_LEDGER.snapshot_by_hash(args.primary_snapshot)
    secondary = MARKET_DATA_REVISION_LEDGER.snapshot_by_hash(args.secondary_snapshot)
    validate_snapshot(primary, symbol, "futu")
    validate_snapshot(secondary, symbol, "yahoo")
    cross_source = build_cross_source_evidence(primary, secondary, required_overlap=120)
    if str(cross_source.get("status") or "") != "PASS":
        raise ValueError("cross_source_verification_not_pass")

    before = MARKET_DATA_REVISION_LEDGER.summary(symbol)
    primary_restore = MARKET_DATA_REVISION_LEDGER.record_snapshot(primary)
    secondary_restore = MARKET_DATA_REVISION_LEDGER.record_snapshot(secondary)
    primary_resolution = resolve_if_blocked(
        primary_restore,
        event_hash=str(args.primary_event or ""),
        reason=reason,
        source_label="primary",
    )
    secondary_resolution = resolve_if_blocked(
        secondary_restore,
        event_hash=str(args.secondary_event or ""),
        reason=reason,
        source_label="secondary",
    )
    cross_source = MARKET_DATA_REVISION_LEDGER.record_cross_source(cross_source)
    after = MARKET_DATA_REVISION_LEDGER.summary(symbol)
    restored_scopes = {
        str(primary_restore.get("scope_key") or ""),
        str(secondary_restore.get("scope_key") or ""),
    }
    unresolved = [
        dict(item)
        for item in after.get("unresolved_blocking_revisions") or []
        if isinstance(item, dict)
    ]
    target_scope_blockers = [
        item for item in unresolved
        if str(item.get("scope_key") or "") in restored_scopes
    ]
    unrelated_scope_blockers = [
        item for item in unresolved
        if str(item.get("scope_key") or "") not in restored_scopes
    ]
    status = "PASS" if (
        not target_scope_blockers
        and str(cross_source.get("status") or "") == "PASS"
    ) else "BLOCK"
    report = {
        "schema_version": "market-data-revision-repair-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "status": status,
        "reason": reason,
        "invalidation_artifact": str(args.invalidation_artifact or ""),
        "snapshots": {
            "primary": public_snapshot(primary),
            "secondary": public_snapshot(secondary),
        },
        "restore_evidence": {
            "primary": primary_restore,
            "secondary": secondary_restore,
        },
        "cross_source": cross_source,
        "resolutions": {
            "primary": primary_resolution,
            "secondary": secondary_resolution,
        },
        "target_scope_blockers": target_scope_blockers,
        "unrelated_scope_blockers": unrelated_scope_blockers,
        "warnings": [
            f"unrelated_blocking_revision_scopes_remain:{len(unrelated_scope_blockers)}"
        ] if unrelated_scope_blockers else [],
        "before": before,
        "after": after,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    report["report_hash"] = canonical_hash({key: value for key, value in report.items() if key != "created_at"})
    output = Path(args.output) if args.output else (
        Path(config.RUNTIME_DIR)
        / "reports"
        / f"market_data_revision_repair_{symbol.lower()}_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": status,
        "symbol": symbol,
        "report_hash": report["report_hash"],
        "output": str(output),
        "primary_resolution_hash": primary_resolution["resolution_hash"],
        "secondary_resolution_hash": secondary_resolution["resolution_hash"],
        "cross_source_evidence_hash": cross_source["evidence_hash"],
        "live_order_allowed": False,
    }, ensure_ascii=False, indent=2))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
