from __future__ import annotations

import argparse
from collections.abc import Mapping
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys
from typing import Any
import unicodedata


RESULT_SCHEMA_VERSION = "portfolio-backtest-replay-result-v1"
DATASET_SCHEMA_VERSION = "portfolio-backtest-replay-dataset-v2"
# Keep this standalone scanner equivalent to services.execution_authority. The
# replay driver is frozen into evidence archives and must not import runtime code.
_LOCALIZED_EXECUTION_AUTHORITY_FIELDS = frozenset({
    "可下单",
    "已授权",
    "实盘授权",
})
EXECUTION_AUTHORITY_FIELDS = frozenset({
    "armed",
    "automatic_paper_activation_allowed",
    "automated_paper_order_allowed",
    "binding_authorized",
    "can_execute",
    "can_trade",
    "direction_signal_allowed",
    "execution_allowed",
    "live_authorized",
    "live_order_allowed",
    "live_ready",
    "paper_authorized",
    "live_trading_allowed",
    "live_trading_enabled",
    "mission_authorized",
    "order_allowed",
    "paper_activation_allowed",
    "paper_armed",
    "paper_order_allowed",
    "paper_ready",
    "parameter_selection_allowed",
    "parameter_selection_authority",
    "performance_claim_allowed",
    "performance_claim_proven",
    "profitability_proven",
    "role_assignment_allowed",
    "runtime_mutations_allowed",
    "selection_allowed",
    "trade_allowed",
}) | _LOCALIZED_EXECUTION_AUTHORITY_FIELDS
EXECUTION_AUTHORITY_FIELD_KEYS = frozenset(
    "".join(
        character
        for character in unicodedata.normalize("NFKC", field).casefold()
        if character.isalnum()
    )
    for field in EXECUTION_AUTHORITY_FIELDS
)
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


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path.name}")
    return payload


def canonical_authority_key(value: Any) -> str:
    normalized = unicodedata.normalize("NFKC", str(value))
    return "".join(
        character for character in normalized.casefold() if character.isalnum()
    )


def authority_violations(payload: Any, *, path: str = "$") -> list[str]:
    violations: list[str] = []
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            child = f"{path}.{key}"
            if (
                canonical_authority_key(key) in EXECUTION_AUTHORITY_FIELD_KEYS
                and value is not False
            ):
                violations.append(child)
            violations.extend(authority_violations(value, path=child))
    elif isinstance(payload, (list, tuple)):
        for index, value in enumerate(payload):
            violations.extend(authority_violations(value, path=f"{path}[{index}]"))
    return violations


def install_offline_guards() -> tuple[list[str], list[str]]:
    import http.client
    import socket
    import sqlite3
    import urllib.request

    network_attempts: list[str] = []
    database_attempts: list[str] = []
    original_socket = socket.socket

    class OfflineSocket(original_socket):
        def connect(self, address: Any) -> None:
            network_attempts.append(f"socket.connect:{address!r}")
            raise RuntimeError("network access disabled during archived replay")

        def connect_ex(self, address: Any) -> int:
            network_attempts.append(f"socket.connect_ex:{address!r}")
            raise RuntimeError("network access disabled during archived replay")

    def blocked_network(*args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        network_attempts.append("network helper")
        raise RuntimeError("network access disabled during archived replay")

    def blocked_database(*args: Any, **kwargs: Any) -> Any:
        database_attempts.append(str(args[0]) if args else "sqlite.connect")
        del kwargs
        raise RuntimeError("database access disabled during archived replay")

    socket.socket = OfflineSocket
    socket.create_connection = blocked_network
    urllib.request.urlopen = blocked_network
    http.client.HTTPConnection.connect = blocked_network
    http.client.HTTPSConnection.connect = blocked_network
    sqlite3.connect = blocked_database
    sqlite3.dbapi2.connect = blocked_database
    return network_attempts, database_attempts


def benchmark_report(
    buy_and_hold_report: Any,
    payload: dict[str, Any],
    *,
    symbol: str,
    position_pct: float,
    evaluation_start_index: int,
) -> dict[str, Any]:
    report = buy_and_hold_report(
        rows=list(payload.get("rows") or []),
        symbol=symbol,
        source=f"{payload.get('source') or ''}:portfolio_benchmark",
        position_pct=position_pct,
        startup_candles=80,
        fee_rate=0.0005,
        slippage_bps=2.0,
        market="stock",
        evaluation_start_index=evaluation_start_index,
    )
    report["benchmark_run_hash"] = canonical_hash(report)
    return report


def stress_summary(report: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": str(scenario.get("label") or "UNDECLARED"),
        "fee_rate": float(scenario.get("fee_rate") or 0.0),
        "slippage_bps": float(scenario.get("slippage_bps") or 0.0),
        "ok": bool(report.get("ok")),
        "total_return_pct": report.get("total_return_pct"),
        "max_drawdown_pct": report.get("max_drawdown_pct"),
        "sharpe": report.get("sharpe"),
        "turnover": report.get("turnover"),
        "total_fees": report.get("total_fees"),
        "gap_block_count": report.get("gap_block_count"),
        "partial_fill_count": report.get("partial_fill_count"),
        "estimated_strategy_capacity": report.get("estimated_strategy_capacity"),
        "run_hash": report.get("run_hash", ""),
    }


def run_replay(source_root: Path, dataset_path: Path, report_path: Path) -> dict[str, Any]:
    source_root = source_root.resolve()
    dataset_path = dataset_path.resolve()
    report_path = report_path.resolve()
    sys.path.insert(0, str(source_root))
    network_attempts, database_attempts = install_offline_guards()
    from exchange_terminal.services import portfolio_backtest as backtest_module
    from exchange_terminal.services.portfolio_backtest import (
        prepare_portfolio_dataset,
        run_causal_relative_strength_backtest,
    )
    from exchange_terminal.services.portfolio_evidence_bundle import (
        expand_portfolio_evidence_bundle,
    )
    from exchange_terminal.services.strategy_benchmark import buy_and_hold_report

    module_path = Path(backtest_module.__file__).resolve()
    module_path.relative_to(source_root)

    snapshot_compact = read_json(dataset_path)
    report_compact = read_json(report_path)
    snapshot, snapshot_bundle_audit = expand_portfolio_evidence_bundle(
        snapshot_compact,
        require_bundle=snapshot_compact.get("evidence_bundle_required") is True,
    )
    report, report_bundle_audit = expand_portfolio_evidence_bundle(
        report_compact,
        require_bundle=bool((report_compact.get("spec") or {}).get("evidence_bundle_required") is True),
    )
    if snapshot_bundle_audit.get("status") != "PASS" or report_bundle_audit.get("status") != "PASS":
        raise ValueError(
            "Evidence bundle verification failed: "
            + ",".join(
                list(snapshot_bundle_audit.get("blockers") or [])
                + list(report_bundle_audit.get("blockers") or [])
            )
        )
    snapshot_without_hash = dict(snapshot)
    snapshot_hash = str(snapshot_without_hash.pop("snapshot_hash", "") or "")
    payloads = {
        str(symbol).upper(): dict(payload or {})
        for symbol, payload in dict(snapshot.get("payloads") or {}).items()
    }
    manifest = dict(report.get("dataset_manifest") or {})
    spec = dict(report.get("spec") or {})
    benchmark = str(manifest.get("benchmark_symbol") or "").upper()
    row_count = int(manifest.get("row_count") or 0)
    train_end = int(spec.get("train_end_index") or 0)
    validation_end = int(spec.get("validation_end_index") or 0)

    prepared = prepare_portfolio_dataset(
        payloads,
        benchmark_symbol=benchmark,
        minimum_rows=row_count,
        universe_contract=dict(report.get("universe_contract") or {}),
    )
    rebuilt_manifest = dict(prepared.get("manifest") or {})
    run_signature = inspect.signature(run_causal_relative_strength_backtest)
    full_run_spec = dict(dict(report.get("full") or {}).get("run_spec") or {})
    ignored = {"payloads", "evaluation_start_index", "universe_contract"}
    engine_settings = {
        key: value
        for key, value in full_run_spec.items()
        if key in run_signature.parameters and key not in ignored
    }
    engine_settings["universe_contract"] = dict(report.get("universe_contract") or {})
    validation_cutoff = str(spec.get("validation_cutoff") or "").strip()[:10]

    def event_date(item: dict[str, Any], *keys: str) -> str:
        return str(next((item.get(key) for key in keys if item.get(key)), "") or "").strip()[:10]

    def frozen_stage_payloads(
        stage: str,
        *,
        row_limit: int = 0,
        stage_cutoff: str = "",
    ) -> dict[str, dict[str, Any]]:
        stage_manifest = dict(dict(report.get(stage) or {}).get("dataset_manifest") or {})
        adjustments = dict(stage_manifest.get("adjustment_evidence") or {})
        revisions = dict(stage_manifest.get("data_revision_evidence") or {})
        expected_symbols = set(payloads)
        if set(adjustments) != expected_symbols or set(revisions) != expected_symbols:
            raise ValueError(f"frozen {stage} evidence is incomplete")
        frozen: dict[str, dict[str, Any]] = {}
        for symbol, payload in payloads.items():
            rows = [dict(row) for row in list(payload.get("rows") or [])]
            if row_limit > 0:
                rows = rows[:row_limit]
            cutoff = stage_cutoff or str((rows[-1] if rows else {}).get("date") or "")[:10]
            frozen[symbol] = {
                **payload,
                "rows": rows,
                "corporate_actions": [
                    dict(action)
                    for action in payload.get("corporate_actions") or []
                    if not row_limit or not cutoff or event_date(dict(action), "event_date", "date") <= cutoff
                ],
                "trading_status_events": [
                    dict(event)
                    for event in payload.get("trading_status_events") or []
                    if not row_limit or not cutoff or event_date(dict(event), "start_date", "event_date", "date") <= cutoff
                ],
                "adjustment_evidence": dict(adjustments[symbol] or {}),
                "data_revision_evidence": dict(revisions[symbol] or {}),
            }
        return frozen

    validation_payloads = frozen_stage_payloads(
        "validation",
        row_limit=validation_end,
        stage_cutoff=validation_cutoff,
    )
    test_payloads = frozen_stage_payloads("test")
    full_payloads = frozen_stage_payloads("full")
    actual_results = {
        "validation": run_causal_relative_strength_backtest(
            payloads=validation_payloads,
            evaluation_start_index=train_end,
            **engine_settings,
        ),
        "test": run_causal_relative_strength_backtest(
            payloads=test_payloads,
            evaluation_start_index=validation_end,
            **engine_settings,
        ),
        "full": run_causal_relative_strength_backtest(
            payloads=full_payloads,
            **engine_settings,
        ),
    }
    expected_results = dict(snapshot.get("expected_results") or {})
    result_records = {
        stage: {
            "expected_run_hash": str(dict(expected_results.get(stage) or {}).get("run_hash") or ""),
            "actual_run_hash": str(dict(actual_results.get(stage) or {}).get("run_hash") or ""),
            "expected_result_hash": str(dict(expected_results.get(stage) or {}).get("result_hash") or ""),
            "actual_result_hash": canonical_hash(dict(actual_results.get(stage) or {})),
        }
        for stage in ("validation", "test", "full")
    }

    validation_benchmark = benchmark_report(
        buy_and_hold_report,
        validation_payloads[benchmark],
        symbol=benchmark,
        position_pct=float(spec.get("gross_target_pct") or 0.0),
        evaluation_start_index=train_end,
    )
    test_benchmark = benchmark_report(
        buy_and_hold_report,
        payloads[benchmark],
        symbol=benchmark,
        position_pct=float(spec.get("gross_target_pct") or 0.0),
        evaluation_start_index=validation_end,
    )
    benchmark_records = {
        "validation_benchmark": {
            "expected_result_hash": str(
                dict(snapshot.get("expected_benchmark_result_hashes") or {}).get("validation_benchmark") or ""
            ),
            "actual_result_hash": canonical_hash(validation_benchmark),
        },
        "test_benchmark": {
            "expected_result_hash": str(
                dict(snapshot.get("expected_benchmark_result_hashes") or {}).get("test_benchmark") or ""
            ),
            "actual_result_hash": canonical_hash(test_benchmark),
        },
    }
    cost_stress: list[dict[str, Any]] = []
    for scenario in list(spec.get("cost_stress_contract") or []):
        settings = {
            **engine_settings,
            "fee_rate": float(dict(scenario or {}).get("fee_rate") or 0.0),
            "slippage_bps": float(dict(scenario or {}).get("slippage_bps") or 0.0),
        }
        stress = run_causal_relative_strength_backtest(
            payloads=payloads,
            evaluation_start_index=validation_end,
            **settings,
        )
        cost_stress.append(stress_summary(stress, dict(scenario or {})))

    checks = {
        "engine_loaded_from_archive": module_path.is_relative_to(source_root),
        "dataset_schema_matches": snapshot.get("schema_version") == DATASET_SCHEMA_VERSION,
        "dataset_snapshot_hash_matches": bool(snapshot_hash) and canonical_hash(snapshot_without_hash) == snapshot_hash,
        "source_report_file_hash_matches": file_sha256(report_path)
        == str(snapshot.get("source_report_file_sha256") or ""),
        "dataset_gate_passes": prepared.get("status") == "PASS",
        "dataset_hash_matches": str(rebuilt_manifest.get("data_hash") or "")
        == str(snapshot.get("candidate_dataset_hash") or ""),
        "dataset_manifest_hash_matches": str(rebuilt_manifest.get("manifest_hash") or "")
        == str(snapshot.get("candidate_dataset_manifest_hash") or ""),
        "validation_run_hash_matches": result_records["validation"]["actual_run_hash"]
        == result_records["validation"]["expected_run_hash"],
        "validation_result_hash_matches": result_records["validation"]["actual_result_hash"]
        == result_records["validation"]["expected_result_hash"],
        "test_run_hash_matches": result_records["test"]["actual_run_hash"]
        == result_records["test"]["expected_run_hash"],
        "test_result_hash_matches": result_records["test"]["actual_result_hash"]
        == result_records["test"]["expected_result_hash"],
        "full_run_hash_matches": result_records["full"]["actual_run_hash"]
        == result_records["full"]["expected_run_hash"],
        "full_result_hash_matches": result_records["full"]["actual_result_hash"]
        == result_records["full"]["expected_result_hash"],
        "validation_benchmark_hash_matches": benchmark_records["validation_benchmark"]["actual_result_hash"]
        == benchmark_records["validation_benchmark"]["expected_result_hash"],
        "test_benchmark_hash_matches": benchmark_records["test_benchmark"]["actual_result_hash"]
        == benchmark_records["test_benchmark"]["expected_result_hash"],
        "cost_stress_hash_matches": canonical_hash(cost_stress)
        == str(snapshot.get("expected_cost_stress_hash") or ""),
        "network_not_accessed": not network_attempts,
        "mutable_database_not_accessed": not database_attempts,
        "no_execution_authority": not authority_violations({"snapshot": snapshot, "results": actual_results}),
        "sensitive_environment_removed": not [
            key for key in os.environ if any(marker in key.upper() for marker in SENSITIVE_ENV_MARKERS)
        ],
    }
    blockers = [name for name, passed in checks.items() if not passed]
    payload = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "checks": checks,
        "blockers": blockers,
        "dataset_hash": str(rebuilt_manifest.get("data_hash") or ""),
        "dataset_manifest_hash": str(rebuilt_manifest.get("manifest_hash") or ""),
        "result_records": result_records,
        "benchmark_records": benchmark_records,
        "cost_stress_hash": canonical_hash(cost_stress),
        "engine_source_sha256": file_sha256(module_path),
        "network_access_attempt_count": len(network_attempts),
        "database_access_attempt_count": len(database_attempts),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["replay_hash"] = canonical_hash(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay one frozen portfolio backtest without network or database access.")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run_replay(args.source_root, args.dataset, args.report)
    except Exception as exc:
        result = {
            "schema_version": RESULT_SCHEMA_VERSION,
            "status": "BLOCK",
            "blockers": [f"isolated_replay_error:{type(exc).__name__}"],
            "error": str(exc)[:500],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        result["replay_hash"] = canonical_hash(result)
    print(json.dumps(result, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
