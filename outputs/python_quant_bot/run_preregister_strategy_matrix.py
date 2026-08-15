from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path

from exchange_terminal import server
from exchange_terminal.services.implementation_manifest import build_implementation_manifest
from exchange_terminal.services.strategy_matrix_protocol import (
    StrategyMatrixRegistrationStore,
    audit_strategy_matrix_holdout_exposure,
    build_strategy_matrix_protocol,
    canonical_hash,
    verify_strategy_matrix_protocol,
)
from exchange_terminal.services.trusted_clock import attest_utc_clock
from run_internal_strategy_matrix import (
    DEFAULT_SELECTION_SYMBOLS,
    build_matrix_batch_spec,
    write_json_atomic,
)


DEFAULT_FRESH_CONFIRMATION_SYMBOLS = ["ANET", "MRVL"]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pre-register one content-addressed, research-only strategy matrix before holdout data load."
    )
    parser.add_argument("--selection-symbols", nargs="+", default=DEFAULT_SELECTION_SYMBOLS)
    parser.add_argument("--confirmation-symbols", nargs="+", default=DEFAULT_FRESH_CONFIRMATION_SYMBOLS)
    parser.add_argument("--strategies", nargs="+", required=True)
    parser.add_argument("--position-pct", type=float, default=20.0)
    parser.add_argument("--take-profit-pct", type=float, default=8.0)
    parser.add_argument("--stop-loss-pct", type=float, default=4.0)
    parser.add_argument("--fee-rate", type=float, default=0.0005)
    parser.add_argument("--slippage-bps", type=float, default=2.0)
    parser.add_argument("--limit", type=int, default=780)
    parser.add_argument("--max-confirmation-candidates", type=int, default=2)
    parser.add_argument("--research-generation", required=True)
    parser.add_argument("--registration-id", default="")
    parser.add_argument("--expires-hours", type=float, default=24.0)
    parser.add_argument("--registry", default="")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    if not math.isfinite(args.expires_hours) or not 0 < args.expires_hours <= 72:
        raise SystemExit("expires-hours must be in (0, 72]")
    try:
        batch_spec = build_matrix_batch_spec(
            selection_symbols=args.selection_symbols,
            confirmation_symbols=args.confirmation_symbols,
            strategies=args.strategies,
            position_pct=args.position_pct,
            take_profit_pct=args.take_profit_pct,
            stop_loss_pct=args.stop_loss_pct,
            fee_rate=args.fee_rate,
            slippage_bps=args.slippage_bps,
            limit=args.limit,
            max_confirmation_candidates=args.max_confirmation_candidates,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    runtime_dir = Path(server.RUNTIME_DIR).resolve()
    reports_dir = runtime_dir / "reports"
    registry_path = (
        Path(args.registry).resolve()
        if args.registry
        else runtime_dir / "strategy_matrix_registrations.sqlite3"
    )
    try:
        registry_path.relative_to(runtime_dir)
    except ValueError as exc:
        raise SystemExit("matrix registry must remain inside the active runtime") from exc
    exposure_audit = audit_strategy_matrix_holdout_exposure(
        reports_dir,
        runtime_dir,
        list(batch_spec["confirmation_symbols"]),
    )
    if exposure_audit.get("status") != "PASS":
        raise SystemExit(json.dumps({
            "error": "matrix_holdout_exposure_blocked",
            "exposure_audit": exposure_audit,
        }, ensure_ascii=False))

    runner_source = Path(__file__).with_name("run_internal_strategy_matrix.py")
    implementation_manifest = build_implementation_manifest([runner_source])
    clock = attest_utc_clock()
    registered_at_ms = int(clock.get("attested_now_ms") or 0)
    if registered_at_ms <= 0:
        raise SystemExit(json.dumps({
            "error": "matrix_registration_clock_blocked",
            "clock": clock,
        }, ensure_ascii=False))
    batch_hash = canonical_hash(batch_spec)
    registration_id = str(args.registration_id or "").strip() or (
        f"smx-{registered_at_ms}-{batch_hash[:12]}"
    )
    protocol = build_strategy_matrix_protocol(
        registration_id=registration_id,
        research_generation=args.research_generation,
        batch_spec=batch_spec,
        implementation_manifest=implementation_manifest,
        exposure_audit=exposure_audit,
        registration_clock_attestation=clock,
        expires_at_ms=registered_at_ms + int(args.expires_hours * 60 * 60 * 1000),
        registry_path=registry_path,
    )
    protocol_verification = verify_strategy_matrix_protocol(protocol)
    if protocol_verification.get("status") != "PASS":
        raise SystemExit(json.dumps({
            "error": "matrix_protocol_self_verification_blocked",
            "verification": protocol_verification,
        }, ensure_ascii=False))

    store = StrategyMatrixRegistrationStore(
        db_path=registry_path,
        read_only=server.RUNTIME_READ_ONLY,
    )
    registration = store.register(protocol)
    if not registration.get("ok") or registration.get("status") != "REGISTERED":
        raise SystemExit(json.dumps({
            "error": "matrix_protocol_registration_blocked",
            "registration": registration,
        }, ensure_ascii=False))
    output = (
        Path(args.output).resolve()
        if args.output
        else reports_dir / f"strategy_matrix_protocol_{registration_id}.json"
    )
    try:
        output.relative_to(reports_dir.resolve())
    except ValueError as exc:
        raise SystemExit("matrix protocol output must remain inside the runtime reports directory") from exc
    if output.exists():
        existing = json.loads(output.read_text(encoding="utf-8"))
        if canonical_hash(existing) != canonical_hash(protocol):
            raise SystemExit(f"protocol output already exists with different content: {output}")
    else:
        write_json_atomic(output, protocol)

    print(json.dumps({
        "status": "REGISTERED",
        "registration_id": registration_id,
        "protocol_hash": protocol["protocol_hash"],
        "batch_spec_hash": protocol["batch_spec_hash"],
        "implementation_fingerprint": protocol["implementation_fingerprint"],
        "registered_at": datetime.fromtimestamp(registered_at_ms / 1000, tz=timezone.utc).isoformat(),
        "expires_at": datetime.fromtimestamp(protocol["expires_at_ms"] / 1000, tz=timezone.utc).isoformat(),
        "registry": str(registry_path),
        "protocol": str(output),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
