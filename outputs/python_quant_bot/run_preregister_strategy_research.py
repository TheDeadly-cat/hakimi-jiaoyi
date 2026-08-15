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
    verify_strategy_research_canonical_registry_path,
)
from exchange_terminal.services.strategy_hypothesis_preregistration import (
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3,
    load_strategy_hypothesis_preregistration,
    verify_strategy_hypothesis_preregistration,
)
from exchange_terminal.services.strategy_research import (
    parameter_variant_trial_count,
)
from exchange_terminal.services.strategy_research_evidence import (
    STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION,
    STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION,
)
from exchange_terminal.services.strategy_research_protocol_artifact import (
    load_strategy_research_protocol_artifact,
    plan_strategy_research_protocol_artifact,
    publish_strategy_research_protocol_artifact_no_clobber,
    verify_bound_strategy_research_protocol_artifact,
)
from exchange_terminal.services.trusted_clock import attest_utc_clock
from run_internal_strategy_research import (
    DEFAULT_SELECTION_SYMBOLS,
    build_research_batch_spec,
)


DEFAULT_FRESH_HOLDOUT_SYMBOLS = ["ON", "MCHP"]


def verify_reusable_strategy_research_protocol(
    protocol: dict[str, object] | object,
    *,
    registration_id: str,
    research_generation: str,
    batch_spec: dict[str, object],
    registry_path: Path,
    implementation_manifest: dict[str, object],
    artifact_binding: dict[str, object],
    verification_at_ms: int,
) -> dict[str, object]:
    payload = dict(protocol) if isinstance(protocol, dict) else {}
    blockers: list[str] = []
    verification = verify_strategy_matrix_protocol(
        payload,
        verification_at_ms=verification_at_ms,
        enforce_not_expired=True,
    )
    blockers.extend(
        f"research_protocol_recovery:{item}"
        for item in verification.get("blockers") or []
    )
    if str(payload.get("registration_id") or "") != str(registration_id or "").strip():
        blockers.append("research_protocol_recovery_registration_id_mismatch")
    if str(payload.get("research_generation") or "") != str(research_generation or "").strip():
        blockers.append("research_protocol_recovery_generation_mismatch")
    frozen_batch = payload.get("batch_spec") if isinstance(payload.get("batch_spec"), dict) else {}
    if (
        str(payload.get("batch_spec_hash") or "") != canonical_hash(batch_spec)
        or canonical_hash(frozen_batch) != canonical_hash(batch_spec)
        or frozen_batch != batch_spec
    ):
        blockers.append("research_protocol_recovery_batch_spec_mismatch")
    frozen_hypothesis = frozen_batch.get("hypothesis_preregistration")
    requested_hypothesis = batch_spec.get("hypothesis_preregistration")
    if (
        frozen_hypothesis != requested_hypothesis
        or str(frozen_batch.get("hypothesis_preregistration_hash") or "")
        != str(batch_spec.get("hypothesis_preregistration_hash") or "")
    ):
        blockers.append("research_protocol_recovery_hypothesis_mismatch")
    if str(Path(str(payload.get("registry_path") or "")).resolve()) != str(registry_path.resolve()):
        blockers.append("research_protocol_recovery_registry_mismatch")
    if str(payload.get("implementation_fingerprint") or "") != str(
        implementation_manifest.get("fingerprint") or ""
    ):
        blockers.append("research_protocol_recovery_implementation_mismatch")
    if payload.get("implementation_manifest") != implementation_manifest:
        blockers.append("research_protocol_recovery_implementation_manifest_mismatch")
    if payload.get("protocol_artifact") != artifact_binding:
        blockers.append("research_protocol_recovery_artifact_binding_mismatch")
    artifact_verification = verify_bound_strategy_research_protocol_artifact(payload)
    blockers.extend(
        f"research_protocol_recovery_artifact:{item}"
        for item in artifact_verification.get("blockers") or []
    )
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "protocol": payload if not blockers else None,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pre-register one single-use nested strategy research run before any holdout data load."
    )
    parser.add_argument("--selection-symbols", nargs="+", default=DEFAULT_SELECTION_SYMBOLS)
    parser.add_argument("--holdout-symbols", nargs="+", default=DEFAULT_FRESH_HOLDOUT_SYMBOLS)
    parser.add_argument("--strategies", nargs="+", required=True)
    parser.add_argument("--position-pct", type=float, default=20.0)
    parser.add_argument("--take-profit-pct", type=float, default=8.0)
    parser.add_argument("--stop-loss-pct", type=float, default=4.0)
    parser.add_argument("--fee-rate", type=float, default=0.0005)
    parser.add_argument("--slippage-bps", type=float, default=2.0)
    parser.add_argument("--limit", type=int, default=780)
    parser.add_argument("--max-test-candidates", type=int, default=2)
    parser.add_argument("--research-generation", required=True)
    parser.add_argument("--hypothesis-file", required=True)
    parser.add_argument("--registration-id", default="")
    parser.add_argument("--expires-hours", type=float, default=24.0)
    parser.add_argument("--registry", default="")
    parser.add_argument("--output", default="")
    parser.add_argument(
        "--report-schema-version",
        type=int,
        choices=(
            STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION,
            STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION,
        ),
        default=STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION,
        help=(
            "New blind-once preregistrations default to formal schema 14; "
            "schema 13 remains available explicitly."
        ),
    )
    args = parser.parse_args()

    if not math.isfinite(args.expires_hours) or not 0 < args.expires_hours <= 72:
        raise SystemExit("expires-hours must be in (0, 72]")
    report_schema_version = int(args.report_schema_version)
    runtime_dir = Path(server.RUNTIME_DIR).resolve()
    reports_dir = (runtime_dir / "reports").resolve()
    raw_registry_path = (
        Path(args.registry)
        if args.registry
        else runtime_dir / "strategy_research_registrations.sqlite3"
    )
    if report_schema_version == STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION:
        canonical_preflight = verify_strategy_research_canonical_registry_path(
            raw_registry_path,
            active_runtime_root=runtime_dir,
        )
        if canonical_preflight.get("status") != "PASS":
            raise SystemExit(json.dumps({
                "error": "research_registry_canonical_preflight_blocked",
                "status": "BLOCK",
                "blockers": list(
                    canonical_preflight.get("blockers")
                    or ["strategy_research_registry_path_noncanonical"]
                ),
                "holdout_data_loaded": False,
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }, ensure_ascii=False))
        registry_path = Path(
            str(canonical_preflight.get("canonical_registry_path") or "")
        )
    else:
        registry_path = raw_registry_path.resolve()
        try:
            registry_path.relative_to(runtime_dir)
        except ValueError as exc:
            raise SystemExit(
                "research registry must remain inside the active runtime"
            ) from exc

    normalized_strategies = list(dict.fromkeys(
        str(strategy or "").strip().lower()
        for strategy in args.strategies
        if str(strategy or "").strip()
    ))
    try:
        hypothesis_preregistration = load_strategy_hypothesis_preregistration(
            args.hypothesis_file,
            project_root=Path(__file__).resolve().parent,
        )
        hypothesis_verification = verify_strategy_hypothesis_preregistration(
            hypothesis_preregistration,
            expected_strategy_ids=normalized_strategies,
            expected_research_generation=str(args.research_generation).strip(),
            expected_schema_version=(
                STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3
                if report_schema_version
                == STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION
                else STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2
            ),
        )
        if hypothesis_verification.get("status") != "PASS":
            raise ValueError(
                "strategy_hypothesis_preregistration_invalid:"
                + ",".join(
                    str(item)
                    for item in hypothesis_verification.get("blockers") or []
                )
            )
        current_trial_count = parameter_variant_trial_count(
            normalized_strategies
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    registration_seed = {
        "report_schema_version": report_schema_version,
        "research_generation": str(args.research_generation).strip(),
        "hypothesis_hash": str(
            hypothesis_preregistration.get("hypothesis_hash") or ""
        ),
        "selection_symbols": list(args.selection_symbols),
        "holdout_symbols": list(args.holdout_symbols),
        "strategies": normalized_strategies,
        "position_pct": args.position_pct,
        "take_profit_pct": args.take_profit_pct,
        "stop_loss_pct": args.stop_loss_pct,
        "fee_rate": args.fee_rate,
        "slippage_bps": args.slippage_bps,
        "limit": args.limit,
        "max_test_candidates": args.max_test_candidates,
    }
    explicit_registration_id = str(args.registration_id or "").strip()
    registration_id = explicit_registration_id or (
        f"sresearch-{canonical_hash(registration_seed)[:24]}"
    )
    artifact_plan = plan_strategy_research_protocol_artifact(
        reports_dir,
        registration_id=registration_id,
        registry_path=registry_path,
        requested_output=args.output,
    )
    if artifact_plan.get("status") != "PASS":
        raise SystemExit(json.dumps({
            "error": "research_protocol_output_blocked",
            "blockers": list(artifact_plan.get("blockers") or []),
        }, ensure_ascii=False))
    output = Path(artifact_plan["output_path"])
    if server.RUNTIME_READ_ONLY:
        raise SystemExit(json.dumps({
            "error": "research_protocol_read_only_blocked",
            "blockers": [
                "runtime_read_only_prevents_protocol_artifact_and_registration"
            ],
        }, ensure_ascii=False))

    loaded_existing: dict[str, object] | None = None
    if output.exists():
        loaded = load_strategy_research_protocol_artifact(output)
        if loaded.get("status") != "PASS":
            raise SystemExit(json.dumps({
                "error": "research_protocol_recovery_blocked",
                "blockers": list(loaded.get("blockers") or []),
            }, ensure_ascii=False))
        loaded_existing = dict(loaded.get("protocol") or {})

    store: StrategyMatrixRegistrationStore | None = None
    search_lineage: dict[str, object] | None = None
    if report_schema_version == STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION:
        store = StrategyMatrixRegistrationStore(
            db_path=registry_path,
            read_only=server.RUNTIME_READ_ONLY,
            canonical_runtime_root=runtime_dir,
        )
        if loaded_existing is not None:
            frozen_batch = dict(loaded_existing.get("batch_spec") or {})
            search_lineage = dict(frozen_batch.get("search_lineage") or {})
        else:
            lineage_plan = store.derive_search_lineage(
                search_family_id=str(
                    hypothesis_preregistration.get("search_family_id") or ""
                ),
                current_trial_count=current_trial_count,
            )
            if lineage_plan.get("status") != "PASS":
                raise SystemExit(json.dumps({
                    "error": "research_search_lineage_derivation_blocked",
                    "status": "BLOCK",
                    "blockers": list(
                        lineage_plan.get("blockers")
                        or ["strategy_search_lineage_derivation_blocked"]
                    ),
                    "holdout_data_loaded": False,
                    "research_only": True,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }, ensure_ascii=False))
            search_lineage = dict(lineage_plan.get("lineage") or {})

    try:
        batch_spec = build_research_batch_spec(
            selection_symbols=args.selection_symbols,
            holdout_symbols=args.holdout_symbols,
            strategies=args.strategies,
            position_pct=args.position_pct,
            take_profit_pct=args.take_profit_pct,
            stop_loss_pct=args.stop_loss_pct,
            fee_rate=args.fee_rate,
            slippage_bps=args.slippage_bps,
            limit=args.limit,
            max_test_candidates=args.max_test_candidates,
            research_generation=args.research_generation,
            selection_test_policy="BLIND_ONCE",
            hypothesis_preregistration=hypothesis_preregistration,
            search_lineage=search_lineage,
            report_schema_version=report_schema_version,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    exposure_audit = audit_strategy_matrix_holdout_exposure(
        reports_dir,
        runtime_dir,
        list(batch_spec["confirmation_symbols"]),
    )
    if exposure_audit.get("status") != "PASS":
        raise SystemExit(json.dumps({
            "error": "research_holdout_exposure_blocked",
            "exposure_audit": exposure_audit,
        }, ensure_ascii=False))

    runner_source = Path(__file__).with_name("run_internal_strategy_research.py")
    implementation_manifest = build_implementation_manifest([runner_source])
    clock = attest_utc_clock()
    registered_at_ms = int(clock.get("attested_now_ms") or 0)
    if registered_at_ms <= 0:
        raise SystemExit(json.dumps({
            "error": "research_registration_clock_blocked",
            "clock": clock,
        }, ensure_ascii=False))

    artifact_binding = dict(artifact_plan["artifact_binding"])
    if loaded_existing is not None:
        recovery = verify_reusable_strategy_research_protocol(
            loaded_existing,
            registration_id=registration_id,
            research_generation=args.research_generation,
            batch_spec=batch_spec,
            registry_path=registry_path,
            implementation_manifest=implementation_manifest,
            artifact_binding=artifact_binding,
            verification_at_ms=registered_at_ms,
        )
        if recovery.get("status") != "PASS":
            raise SystemExit(json.dumps({
                "error": "research_protocol_recovery_blocked",
                "blockers": list(recovery.get("blockers") or []),
            }, ensure_ascii=False))
        protocol = dict(recovery["protocol"])
    else:
        protocol = build_strategy_matrix_protocol(
            registration_id=registration_id,
            research_generation=args.research_generation,
            batch_spec=batch_spec,
            implementation_manifest=implementation_manifest,
            exposure_audit=exposure_audit,
            registration_clock_attestation=clock,
            expires_at_ms=registered_at_ms + int(args.expires_hours * 60 * 60 * 1000),
            registry_path=registry_path,
            protocol_artifact=artifact_binding,
        )
        protocol_verification = verify_strategy_matrix_protocol(protocol)
        if protocol_verification.get("status") != "PASS":
            raise SystemExit(json.dumps({
                "error": "research_protocol_self_verification_blocked",
                "verification": protocol_verification,
            }, ensure_ascii=False))
        publication = publish_strategy_research_protocol_artifact_no_clobber(output, protocol)
        if publication.get("status") not in {"PUBLISHED", "EXISTING_IDENTICAL"}:
            raise SystemExit(json.dumps({
                "error": "research_protocol_artifact_publish_blocked",
                "blockers": list(publication.get("blockers") or []),
            }, ensure_ascii=False))

    if store is None:
        store = StrategyMatrixRegistrationStore(
            db_path=registry_path,
            read_only=server.RUNTIME_READ_ONLY,
        )
    registration = store.register(protocol)
    if not registration.get("ok") or registration.get("status") != "REGISTERED":
        raise SystemExit(json.dumps({
            "error": "research_protocol_registration_blocked",
            "registration": registration,
        }, ensure_ascii=False))
    post_registration_artifact = verify_bound_strategy_research_protocol_artifact(protocol)
    if post_registration_artifact.get("status") != "PASS":
        raise SystemExit(json.dumps({
            "error": "research_protocol_post_registration_artifact_blocked",
            "blockers": list(post_registration_artifact.get("blockers") or []),
            "claim_will_fail_closed": True,
        }, ensure_ascii=False))

    registered_at_ms = int(protocol.get("registered_at_ms") or 0)
    print(json.dumps({
        "status": "REGISTERED",
        "registration_id": str(protocol.get("registration_id") or ""),
        "protocol_hash": protocol["protocol_hash"],
        "batch_spec_hash": protocol["batch_spec_hash"],
        "hypothesis_id": hypothesis_preregistration["hypothesis_id"],
        "hypothesis_hash": hypothesis_preregistration["hypothesis_hash"],
        "search_family_id": str(
            hypothesis_preregistration.get("search_family_id") or ""
        ),
        "current_trial_count": (
            search_lineage.get("current_trial_count")
            if isinstance(search_lineage, dict)
            else len(batch_spec.get("variants") or [])
        ),
        "cumulative_trial_count": (
            search_lineage.get("cumulative_trial_count")
            if isinstance(search_lineage, dict)
            else len(batch_spec.get("variants") or [])
        ),
        "report_schema_version": report_schema_version,
        "implementation_fingerprint": protocol["implementation_fingerprint"],
        "registered_at": datetime.fromtimestamp(registered_at_ms / 1000, tz=timezone.utc).isoformat(),
        "expires_at": datetime.fromtimestamp(protocol["expires_at_ms"] / 1000, tz=timezone.utc).isoformat(),
        "registry": str(registry_path),
        "protocol": str(output),
        "holdout_data_loaded": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
