from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time
from typing import Any
from urllib.parse import urlparse

from .strategy_matrix_evidence import (
    MATRIX_REPORT_SCHEMA_VERSION,
    canonical_hash,
    strategy_matrix_result_hash,
    strategy_matrix_run_hash,
    verify_matrix_research_governance,
)
from .validation_receipts import (
    build_controlled_input_manifest,
    build_toolchain_fingerprint,
    build_validation_action,
    canonical_json_bytes,
    load_validation_receipt,
    verify_validation_receipt,
)


INTERNAL_BACKTEST_READINESS_VERSION = "internal-backtest-readiness-v2"
READINESS_STATUS = "READY_FOR_PREREGISTRATION"
REQUIRED_ENGINEERING_CHECKS = (
    "python_full_suite",
    "python_compile",
    "frontend_syntax",
    "electron_contract",
    "history_concurrency",
    "browser_interaction",
    "read_only_mutation_probe",
)
ENGINEERING_EVIDENCE_TYPES = {
    "python_full_suite": "process_result",
    "python_compile": "process_result",
    "frontend_syntax": "process_result",
    "electron_contract": "process_result",
    "history_concurrency": "concurrency_result",
    "browser_interaction": "browser_result",
    "read_only_mutation_probe": "http_probe",
}
REUSABLE_ENGINEERING_CHECKS = (
    "python_full_suite",
    "python_compile",
    "frontend_syntax",
    "electron_contract",
    "history_concurrency",
)
RUNTIME_BOUND_ENGINEERING_CHECKS = (
    "browser_interaction",
    "read_only_mutation_probe",
)
RUNTIME_ENGINEERING_COMMANDS = {
    "browser_interaction": "browser:aapl-nvda-btc-usdt-current-instance",
    "read_only_mutation_probe": "POST /api/paper/arm",
}
RUNTIME_ENGINEERING_EVIDENCE_SCHEMA = "hakimi-runtime-engineering-evidence-v1"
RUNTIME_ENGINEERING_MAX_AGE_MS = 15 * 60 * 1000
NEXT_EXPERIMENT_REQUIREMENTS = (
    "freeze_research_question_and_primary_metrics",
    "freeze_strategy_set_parameters_costs_and_risk",
    "declare_selection_universe_and_untouched_confirmation_symbols",
    "pass_holdout_exposure_audit_before_market_data_load",
    "freeze_completed_candle_dataset_lineage_for_every_symbol",
    "register_one_single_use_protocol_before_formal_run",
    "stop_without_retest_when_no_candidate_passes_selection",
)
FORMAL_RUN_BLOCKERS = (
    "new_research_question_not_frozen",
    "new_selection_universe_not_frozen",
    "fresh_holdout_not_exposure_audited",
    "single_use_protocol_not_registered",
)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _sequence(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _valid_sha256(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def _positive_int(value: Any) -> int:
    if type(value) is not int or value <= 0:
        return 0
    return value


def _valid_loopback_origin(value: Any) -> bool:
    try:
        parsed = urlparse(str(value or "").strip())
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme == "http"
        and parsed.hostname in {"127.0.0.1", "localhost"}
        and port is not None
        and parsed.username is None
        and parsed.password is None
        and parsed.path in {"", "/"}
        and not parsed.params
        and not parsed.query
        and not parsed.fragment
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _created_at_ms(value: Any) -> int:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return int(parsed.timestamp() * 1000)
    except (TypeError, ValueError):
        return 0


def build_expected_engineering_actions() -> dict[str, dict[str, Any]]:
    project_root = Path(__file__).resolve().parents[2]
    electron_root = project_root.parent / "hakimi_trade_electron"
    node = shutil.which("node") or ""
    npm = shutil.which("npm.cmd") or shutil.which("npm") or ""
    manifest = build_controlled_input_manifest(project_root)
    toolchain = build_toolchain_fingerprint(
        node_executable=node,
        npm_executable=npm,
    )
    specs = {
        "python_full_suite": {
            "argv": [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            "cwd": project_root,
            "result_contract": "unittest",
            "minimum_tests": 750,
            "full_regression_included": True,
        },
        "python_compile": {
            "argv": [sys.executable, "-m", "py_compile", "exchange_terminal/server.py"],
            "cwd": project_root,
            "result_contract": "exit-zero",
            "minimum_tests": 0,
            "full_regression_included": False,
        },
        "frontend_syntax": {
            "argv": [node, "--check", "exchange_terminal/static/app.js"],
            "cwd": project_root,
            "result_contract": "exit-zero",
            "minimum_tests": 0,
            "full_regression_included": False,
        },
        "electron_contract": {
            "argv": [npm, "run", "check"],
            "cwd": electron_root,
            "result_contract": "exit-zero",
            "minimum_tests": 0,
            "full_regression_included": False,
        },
        "history_concurrency": {
            "argv": [
                sys.executable,
                "-m",
                "unittest",
                "-q",
                "tests.test_market_history_store.MarketHistoryStoreTests.test_concurrent_writes_are_serialized_and_complete",
            ],
            "cwd": project_root,
            "result_contract": "unittest",
            "minimum_tests": 1,
            "full_regression_included": False,
        },
    }
    return {
        check_id: build_validation_action(
            check_id=check_id,
            argv=spec["argv"],
            cwd=spec["cwd"],
            manifest=manifest,
            toolchain=toolchain,
            result_contract=str(spec["result_contract"]),
            minimum_tests=int(spec["minimum_tests"]),
            namespace="hakimi-readiness-engineering",
            full_regression_included=bool(spec["full_regression_included"]),
        )
        for check_id, spec in specs.items()
    }


def inspect_engineering_check(
    value: Any,
    *,
    verify_file: bool = False,
    expected_action: dict[str, Any] | None = None,
    runtime_binding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    item = _mapping(value)
    check_id = str(item.get("id") or "").strip()
    evidence_type = str(item.get("evidence_type") or "").strip()
    result = _mapping(item.get("result"))
    artifact_path = Path(str(item.get("artifact_path") or ""))
    artifact_sha256 = str(item.get("artifact_sha256") or "").strip().lower()
    blockers: list[str] = []

    expected_type = ENGINEERING_EVIDENCE_TYPES.get(check_id)
    if expected_type is None:
        blockers.append("engineering_check_id_invalid")
    elif evidence_type != expected_type:
        blockers.append("engineering_evidence_type_invalid")
    if not str(artifact_path) or not _valid_sha256(artifact_sha256):
        blockers.append("engineering_artifact_identity_invalid")
    artifact_payload: dict[str, Any] = {}
    if verify_file and not blockers:
        try:
            if _file_sha256(artifact_path) != artifact_sha256:
                blockers.append("engineering_artifact_hash_mismatch")
            loaded = json.loads(artifact_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                artifact_payload = loaded
            else:
                blockers.append("engineering_artifact_payload_invalid")
        except (OSError, json.JSONDecodeError):
            blockers.append("engineering_artifact_unavailable")

    receipt_verification: dict[str, Any] = {}
    if check_id in REUSABLE_ENGINEERING_CHECKS:
        receipt = _mapping(item.get("validation_receipt"))
        if item.get("reuse_allowed") is not True:
            blockers.append("engineering_reuse_policy_invalid")
        if item.get("execution") != "EXECUTED":
            blockers.append("engineering_readiness_requires_fresh_execution")
        if expected_action is None:
            blockers.append("engineering_expected_action_missing")
        receipt_verification = verify_validation_receipt(
            receipt,
            expected_action=expected_action,
        )
        if receipt_verification.get("status") != "PASS":
            blockers.extend(
                f"engineering_receipt:{blocker}"
                for blocker in _sequence(receipt_verification.get("blockers"))
            )
        if verify_file and artifact_payload and canonical_json_bytes(artifact_payload) != canonical_json_bytes(receipt):
            blockers.append("engineering_artifact_is_not_receipt")
        predicate = _mapping(receipt.get("predicate"))
        action = _mapping(predicate.get("action"))
        result = _mapping(predicate.get("result"))
        expected_command = _sequence(_mapping(expected_action).get("argv"))
        if _sequence(item.get("command")) != expected_command or _sequence(action.get("argv")) != expected_command:
            blockers.append("engineering_command_contract_invalid")
    elif check_id in RUNTIME_BOUND_ENGINEERING_CHECKS:
        if item.get("reuse_allowed") is not False:
            blockers.append("engineering_runtime_evidence_must_not_be_reused")
        if str(item.get("command") or "") != RUNTIME_ENGINEERING_COMMANDS.get(check_id):
            blockers.append("engineering_command_contract_invalid")
        expected_binding = dict(runtime_binding or {})
        observed_binding = _mapping(item.get("runtime_binding"))
        if not expected_binding or canonical_json_bytes(observed_binding) != canonical_json_bytes(expected_binding):
            blockers.append("engineering_runtime_binding_mismatch")
        observed_at_ms = item.get("observed_at_ms")
        loaded_at = int(expected_binding.get("loaded_at") or 0)
        now_ms = int(time.time() * 1000)
        if (
            type(observed_at_ms) is not int
            or observed_at_ms < loaded_at
            or observed_at_ms < now_ms - RUNTIME_ENGINEERING_MAX_AGE_MS
            or observed_at_ms > now_ms + 300_000
        ):
            blockers.append("engineering_runtime_observation_time_invalid")
        expected_artifact_payload = {
            "schema_version": RUNTIME_ENGINEERING_EVIDENCE_SCHEMA,
            "id": check_id,
            "command": RUNTIME_ENGINEERING_COMMANDS.get(check_id),
            "evidence_type": expected_type,
            "result": result,
            "runtime_binding": observed_binding,
            "observed_at_ms": observed_at_ms,
            "reuse_allowed": False,
        }
        if (
            verify_file
            and artifact_payload
            and canonical_json_bytes(artifact_payload) != canonical_json_bytes(expected_artifact_payload)
        ):
            blockers.append("engineering_runtime_artifact_payload_mismatch")
    elif expected_type is not None:
        blockers.append("engineering_check_reuse_class_invalid")

    if expected_type == "process_result" and check_id not in REUSABLE_ENGINEERING_CHECKS:
        if type(result.get("exit_code")) is not int or result.get("exit_code") != 0:
            blockers.append("engineering_process_failed")
    elif expected_type == "concurrency_result" and check_id not in REUSABLE_ENGINEERING_CHECKS:
        if result.get("passed") is not True or result.get("failure_count") != 0:
            blockers.append("engineering_concurrency_failed")
    elif expected_type == "browser_result":
        browser_contract = (
            result.get("console_error_count") == 0
            and result.get("aapl_roundtrip") is True
            and result.get("nvda_roundtrip") is True
            and result.get("btc_usdt_roundtrip") is True
            and result.get("candles_never_empty") is True
        )
        if not browser_contract:
            blockers.append("engineering_browser_contract_failed")
    elif expected_type == "http_probe":
        if result.get("http_status") != 423:
            blockers.append("engineering_read_only_probe_failed")

    normalized = dict(item)
    normalized.update({
        "id": check_id,
        "status": "PASS" if not blockers else "BLOCK",
        "evidence_type": evidence_type,
        "result": result,
        "artifact_path": str(artifact_path),
        "artifact_sha256": artifact_sha256,
        "reuse_allowed": item.get("reuse_allowed"),
        "runtime_binding": _mapping(item.get("runtime_binding")),
        "observed_at_ms": item.get("observed_at_ms"),
        "receipt_verification": receipt_verification,
        "blockers": list(dict.fromkeys(blockers)),
    })
    return normalized


def _embedded_hash_matches(payload: Any, field: str) -> bool:
    clean = _mapping(payload)
    expected = str(clean.pop(field, "") or "")
    return _valid_sha256(expected) and canonical_hash(clean) == expected


def inspect_prior_matrix_report(path: Path | str) -> dict[str, Any]:
    report_path = Path(path).resolve()
    blockers: list[str] = []
    try:
        raw = report_path.read_bytes()
        report = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "BLOCK",
            "path": str(report_path),
            "blockers": [f"prior_matrix_report_unreadable:{type(exc).__name__}"],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    if not isinstance(report, dict):
        report = {}
        blockers.append("prior_matrix_report_type_invalid")
    summary = _mapping(report.get("summary"))
    governance = _mapping(report.get("research_governance"))
    dataset_manifest = _sequence(report.get("dataset_manifest"))
    if report.get("schema_version") != MATRIX_REPORT_SCHEMA_VERSION:
        blockers.append("prior_matrix_report_schema_invalid")
    if canonical_hash(_mapping(report.get("batch_spec"))) != str(report.get("batch_spec_hash") or ""):
        blockers.append("prior_matrix_batch_hash_mismatch")
    if canonical_hash(dataset_manifest) != str(report.get("dataset_manifest_hash") or ""):
        blockers.append("prior_matrix_dataset_manifest_hash_mismatch")
    if not _embedded_hash_matches(report.get("dataset_snapshot"), "snapshot_hash"):
        blockers.append("prior_matrix_dataset_snapshot_hash_invalid")
    if strategy_matrix_result_hash(report) != str(report.get("matrix_result_hash") or ""):
        blockers.append("prior_matrix_result_hash_mismatch")
    if strategy_matrix_run_hash(report) != str(report.get("batch_run_hash") or ""):
        blockers.append("prior_matrix_run_hash_mismatch")
    governance_verification = verify_matrix_research_governance(
        governance,
        report_created_at_ms=_created_at_ms(report.get("created_at")),
        batch_spec_hash=str(report.get("batch_spec_hash") or ""),
        result_hash=str(report.get("matrix_result_hash") or ""),
        dataset_manifest_hash=str(report.get("dataset_manifest_hash") or ""),
    )
    if governance_verification.get("status") != "PASS":
        blockers.extend(
            f"prior_matrix_governance:{item}"
            for item in _sequence(governance_verification.get("blockers"))
        )
    expected_zero_fields = (
        "selection_passed",
        "confirmation_candidates",
        "confirmation_cells",
        "forward_candidates",
    )
    for field in expected_zero_fields:
        if summary.get(field) != 0:
            blockers.append(f"prior_matrix_not_zero_candidate:{field}")
    if summary.get("selection_cells") != 54:
        blockers.append("prior_matrix_selection_cell_count_unexpected")
    if summary.get("data_status") != "PASS" or summary.get("selection_gate_status") != "PASS":
        blockers.append("prior_matrix_engineering_gate_not_passed")
    if (
        governance.get("research_only") is not True
        or governance.get("paper_authorized") is not False
        or governance.get("live_order_allowed") is not False
        or summary.get("paper_authorized") is not False
        or summary.get("live_order_allowed") is not False
    ):
        blockers.append("prior_matrix_has_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "path": str(report_path),
        "file_size": len(raw),
        "file_sha256": hashlib.sha256(raw).hexdigest(),
        "registration_id": str(governance.get("registration_id") or ""),
        "protocol_hash": str(governance.get("protocol_hash") or ""),
        "batch_spec_hash": str(report.get("batch_spec_hash") or ""),
        "dataset_manifest_hash": str(report.get("dataset_manifest_hash") or ""),
        "dataset_snapshot_hash": str(_mapping(report.get("dataset_snapshot")).get("snapshot_hash") or ""),
        "matrix_result_hash": str(report.get("matrix_result_hash") or ""),
        "batch_run_hash": str(report.get("batch_run_hash") or ""),
        "selection_cells": int(summary.get("selection_cells") or 0),
        "selection_passed": int(summary.get("selection_passed") or 0),
        "confirmation_candidates": int(summary.get("confirmation_candidates") or 0),
        "forward_candidates": int(summary.get("forward_candidates") or 0),
        "conclusion": "NO_CANDIDATE_CONFIRMED" if not blockers else "PRIOR_EVIDENCE_BLOCKED",
        "governance_verification": governance_verification,
        "blockers": list(dict.fromkeys(blockers)),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def inspect_runtime_health(payload: Any) -> dict[str, Any]:
    health = _mapping(payload)
    build = _mapping(health.get("runtime_build"))
    blockers: list[str] = []
    process_id = _positive_int(build.get("process_id"))
    loaded_at = _positive_int(build.get("loaded_at"))
    source_count = _positive_int(build.get("loaded_source_count"))
    loaded_fingerprint = str(build.get("loaded_fingerprint") or "").strip().lower()
    disk_fingerprint = str(build.get("disk_fingerprint") or "").strip().lower()
    if health.get("ok") is not True:
        blockers.append("runtime_health_not_ok")
    if build.get("status") != "PASS" or _sequence(build.get("blockers")):
        blockers.append("runtime_build_not_pass")
    if process_id == 0:
        blockers.append("runtime_process_id_invalid")
    if loaded_at == 0 or loaded_at > int(time.time() * 1000) + 300_000:
        blockers.append("runtime_loaded_at_invalid")
    if source_count == 0:
        blockers.append("runtime_source_count_invalid")
    if not _valid_sha256(loaded_fingerprint) or not _valid_sha256(disk_fingerprint):
        blockers.append("runtime_source_fingerprint_invalid")
    elif loaded_fingerprint != disk_fingerprint:
        blockers.append("runtime_source_fingerprint_mismatch")
    if build.get("source_changed_after_start") is not False or build.get("restart_required") is not False:
        blockers.append("runtime_restart_required")
    expected = {
        "read_only": True,
        "runtime_mutations_allowed": False,
        "paper_authorized": False,
        "paper_armed": False,
        "live_trading_hard_block": True,
        "live_order_allowed": False,
    }
    for field, expected_value in expected.items():
        if health.get(field) is not expected_value:
            blockers.append(f"runtime_authority_invalid:{field}")
    if build.get("read_only") is not True:
        blockers.append("runtime_build_not_read_only")
    if build.get("paper_authorized") is not False or build.get("live_order_allowed") is not False:
        blockers.append("runtime_build_has_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "process_id": process_id,
        "loaded_at": loaded_at,
        "fingerprint": loaded_fingerprint,
        "source_count": source_count,
        "read_only": health.get("read_only") is True,
        "runtime_mutations_allowed": health.get("runtime_mutations_allowed") is True,
        "paper_authorized": False,
        "paper_armed": False,
        "live_trading_hard_block": health.get("live_trading_hard_block") is True,
        "live_order_allowed": False,
        "blockers": list(dict.fromkeys(blockers)),
    }


def inspect_market_cache(payload: Any) -> dict[str, Any]:
    cache = _mapping(payload)
    blockers: list[str] = []
    rows: list[dict[str, Any]] = []
    for item in _sequence(cache.get("rows")):
        row = _mapping(item)
        symbol = str(row.get("symbol") or "").upper()
        status = str(row.get("status") or "MISSING").upper()
        if not symbol or status not in {"READY", "PARTIAL", "MISSING", "BLOCK"}:
            blockers.append("market_cache_row_invalid")
            continue
        if row.get("paper_authorized") is not False or row.get("live_order_allowed") is not False:
            blockers.append(f"market_cache_has_execution_authority:{symbol}")
        rows.append({
            "symbol": symbol,
            "status": status,
            "rows": int(row.get("rows") or 0),
            "complete_rows": int(row.get("complete_rows") or 0),
            "incomplete_rows": int(row.get("incomplete_rows") or 0),
            "invalid_rows": int(row.get("invalid_rows") or 0),
            "first": str(row.get("first") or ""),
            "last": str(row.get("last") or ""),
            "source": str(row.get("source") or ""),
            "data_hash": str(row.get("data_hash") or ""),
        })
    rows.sort(key=lambda item: item["symbol"])
    by_symbol = {row["symbol"]: row for row in rows}
    btc = by_symbol.get("BTC-USDT", {})
    if cache.get("ok") is not True:
        blockers.append("market_cache_status_not_ok")
    if not rows:
        blockers.append("market_cache_status_empty")
    if any(row["status"] == "BLOCK" for row in rows):
        blockers.append("market_cache_contains_blocked_dataset")
    if (
        btc.get("status") != "READY"
        or int(btc.get("complete_rows") or 0) < 240
        or int(btc.get("invalid_rows") or 0) != 0
        or not _valid_sha256(btc.get("data_hash"))
    ):
        blockers.append("btc_history_not_research_ready")
    database_path = Path(str(cache.get("path") or "")).resolve() if cache.get("path") else None
    database_sha256 = ""
    if database_path:
        try:
            database_sha256 = _file_sha256(database_path)
        except OSError:
            blockers.append("market_cache_database_unreadable")
    return {
        "status": "READY_WITH_LIMITATIONS" if not blockers else "BLOCK",
        "summary": str(cache.get("summary") or ""),
        "database_path": str(database_path) if database_path else "",
        "database_sha256": database_sha256,
        "symbols": rows,
        "ready_symbols": [row["symbol"] for row in rows if row["status"] == "READY"],
        "missing_symbols": [row["symbol"] for row in rows if row["status"] == "MISSING"],
        "partial_symbols": [row["symbol"] for row in rows if row["status"] == "PARTIAL"],
        "blocked_symbols": [row["symbol"] for row in rows if row["status"] == "BLOCK"],
        "limitations": [
            "only_symbols_marked_ready_may_enter_a_future_preregistered_protocol",
            "missing_symbols_require_isolated_cache_backfill_before_protocol_freeze",
            "the_current_incomplete_daily_bar_must_not_enter_backtests",
        ],
        "blockers": list(dict.fromkeys(blockers)),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def build_readiness_report(
    *,
    generation: str,
    generated_at: str,
    service_origin: str,
    runtime_health: Any,
    market_cache: Any,
    prior_matrix_report: Path | str,
    engineering_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    runtime = inspect_runtime_health(runtime_health)
    market_data = inspect_market_cache(market_cache)
    prior_result = inspect_prior_matrix_report(prior_matrix_report)
    expected_actions = build_expected_engineering_actions()
    runtime_binding = {
        "process_id": int(runtime.get("process_id") or 0),
        "loaded_at": int(runtime.get("loaded_at") or 0),
        "loaded_fingerprint": str(runtime.get("fingerprint") or ""),
    }
    checks = [
        inspect_engineering_check(
            item,
            verify_file=True,
            expected_action=expected_actions.get(str(item.get("id") or "")),
            runtime_binding=runtime_binding,
        )
        for item in engineering_checks
        if isinstance(item, dict)
    ]
    check_by_id = {str(item.get("id") or ""): item for item in checks}
    foundational_blockers: list[str] = []
    check_ids = [str(item.get("id") or "") for item in checks]
    artifact_hashes = [str(item.get("artifact_sha256") or "") for item in checks]
    if len(check_ids) != len(set(check_ids)):
        foundational_blockers.append("engineering_check_id_duplicate")
    if len(artifact_hashes) != len(set(artifact_hashes)):
        foundational_blockers.append("engineering_artifact_reused_across_checks")
    if not _valid_loopback_origin(service_origin):
        foundational_blockers.append("service_origin_invalid")
    if runtime.get("status") != "PASS":
        foundational_blockers.append("runtime_not_ready")
    if market_data.get("status") == "BLOCK":
        foundational_blockers.append("market_data_not_ready")
    if prior_result.get("status") != "PASS":
        foundational_blockers.append("prior_matrix_evidence_not_ready")
    for check_id in REQUIRED_ENGINEERING_CHECKS:
        if _mapping(check_by_id.get(check_id)).get("status") != "PASS":
            foundational_blockers.append(f"engineering_check_not_pass:{check_id}")
    status = READINESS_STATUS if not foundational_blockers else "BLOCK"
    report: dict[str, Any] = {
        "schema_version": INTERNAL_BACKTEST_READINESS_VERSION,
        "generation": str(generation or "").strip(),
        "generated_at": str(generated_at or "").strip(),
        "service_origin": str(service_origin or "").strip(),
        "status": status,
        "scope": "INTERNAL_BACKTEST_PREREGISTRATION_PREPARATION_ONLY",
        "runtime": runtime,
        "market_data": market_data,
        "prior_blind_result": prior_result,
        "engineering_checks": checks,
        "engineering_receipt_set_hash": canonical_hash([
            {
                "id": item.get("id"),
                "artifact_sha256": item.get("artifact_sha256"),
                "receipt_hash": _mapping(item.get("receipt_verification")).get("receipt_hash"),
                "runtime_binding": item.get("runtime_binding"),
                "observed_at_ms": item.get("observed_at_ms"),
            }
            for item in checks
        ]),
        "foundational_blockers": list(dict.fromkeys(foundational_blockers)),
        "next_experiment": {
            "status": "BLOCKED_PENDING_PREREGISTRATION",
            "formal_run_allowed": False,
            "requirements": list(NEXT_EXPERIMENT_REQUIREMENTS),
            "formal_run_blockers": list(FORMAL_RUN_BLOCKERS),
            "g48_retest_allowed": False,
            "fresh_holdout_data_load_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "conclusion": (
            "ENGINEERING_READY_TO_DESIGN_AND_PREREGISTER_A_NEW_RESEARCH_EXPERIMENT"
            if status == READINESS_STATUS
            else "FOUNDATIONAL_READINESS_BLOCKED"
        ),
        "research_only": True,
        "paper_authorized": False,
        "paper_armed": False,
        "live_order_allowed": False,
    }
    report["readiness_hash"] = canonical_hash(report)
    return report


def verify_readiness_report(payload: Any, *, verify_files: bool = True) -> dict[str, Any]:
    report = _mapping(payload)
    blockers: list[str] = []
    clean = dict(report)
    expected_hash = str(clean.pop("readiness_hash", "") or "")
    if report.get("schema_version") != INTERNAL_BACKTEST_READINESS_VERSION:
        blockers.append("readiness_schema_invalid")
    if not _valid_sha256(expected_hash) or canonical_hash(clean) != expected_hash:
        blockers.append("readiness_hash_invalid")
    if not str(report.get("generation") or "") or not _created_at_ms(report.get("generated_at")):
        blockers.append("readiness_identity_invalid")
    service_origin = str(report.get("service_origin") or "")
    if not _valid_loopback_origin(service_origin):
        blockers.append("readiness_service_origin_invalid")
    if report.get("status") != READINESS_STATUS:
        blockers.append("readiness_status_not_ready_for_preregistration")
    if report.get("scope") != "INTERNAL_BACKTEST_PREREGISTRATION_PREPARATION_ONLY":
        blockers.append("readiness_scope_invalid")
    if _mapping(report.get("runtime")).get("status") != "PASS":
        blockers.append("readiness_runtime_not_pass")
    if _mapping(report.get("market_data")).get("status") != "READY_WITH_LIMITATIONS":
        blockers.append("readiness_market_data_not_ready_with_limitations")
    prior = _mapping(report.get("prior_blind_result"))
    if prior.get("status") != "PASS" or prior.get("conclusion") != "NO_CANDIDATE_CONFIRMED":
        blockers.append("readiness_prior_blind_result_invalid")
    if verify_files:
        prior_path = Path(str(prior.get("path") or ""))
        try:
            if _file_sha256(prior_path) != str(prior.get("file_sha256") or ""):
                blockers.append("readiness_prior_report_file_changed")
        except OSError:
            blockers.append("readiness_prior_report_file_unavailable")
        cache = _mapping(report.get("market_data"))
        cache_path = Path(str(cache.get("database_path") or ""))
        try:
            if _file_sha256(cache_path) != str(cache.get("database_sha256") or ""):
                blockers.append("readiness_market_cache_file_changed")
        except OSError:
            blockers.append("readiness_market_cache_file_unavailable")
    expected_actions = build_expected_engineering_actions()
    stored_runtime = _mapping(report.get("runtime"))
    runtime_binding = {
        "process_id": int(stored_runtime.get("process_id") or 0),
        "loaded_at": int(stored_runtime.get("loaded_at") or 0),
        "loaded_fingerprint": str(stored_runtime.get("fingerprint") or ""),
    }
    normalized_checks = [
        inspect_engineering_check(
            item,
            verify_file=verify_files,
            expected_action=expected_actions.get(str(item.get("id") or "")),
            runtime_binding=runtime_binding,
        )
        for item in _sequence(report.get("engineering_checks"))
        if isinstance(item, dict)
    ]
    check_ids = [str(item.get("id") or "") for item in normalized_checks]
    artifact_hashes = [str(item.get("artifact_sha256") or "") for item in normalized_checks]
    if len(check_ids) != len(set(check_ids)):
        blockers.append("readiness_engineering_check_id_duplicate")
    if len(artifact_hashes) != len(set(artifact_hashes)):
        blockers.append("readiness_engineering_artifact_reused")
    checks = {str(item.get("id") or ""): item for item in normalized_checks}
    receipt_set_hash = canonical_hash([
        {
            "id": item.get("id"),
            "artifact_sha256": item.get("artifact_sha256"),
            "receipt_hash": _mapping(item.get("receipt_verification")).get("receipt_hash"),
            "runtime_binding": item.get("runtime_binding"),
            "observed_at_ms": item.get("observed_at_ms"),
        }
        for item in normalized_checks
    ])
    if receipt_set_hash != str(report.get("engineering_receipt_set_hash") or ""):
        blockers.append("readiness_engineering_receipt_set_hash_invalid")
    for check_id in REQUIRED_ENGINEERING_CHECKS:
        if _mapping(checks.get(check_id)).get("status") != "PASS":
            blockers.append(f"readiness_engineering_check_not_pass:{check_id}")
    next_experiment = _mapping(report.get("next_experiment"))
    if (
        next_experiment.get("status") != "BLOCKED_PENDING_PREREGISTRATION"
        or next_experiment.get("formal_run_allowed") is not False
        or next_experiment.get("g48_retest_allowed") is not False
        or next_experiment.get("fresh_holdout_data_load_allowed") is not False
        or tuple(_sequence(next_experiment.get("requirements"))) != NEXT_EXPERIMENT_REQUIREMENTS
        or tuple(_sequence(next_experiment.get("formal_run_blockers"))) != FORMAL_RUN_BLOCKERS
    ):
        blockers.append("readiness_next_experiment_boundary_invalid")
    if _sequence(report.get("foundational_blockers")):
        blockers.append("readiness_foundational_blockers_present")
    if (
        report.get("research_only") is not True
        or report.get("paper_authorized") is not False
        or report.get("paper_armed") is not False
        or report.get("live_order_allowed") is not False
        or next_experiment.get("paper_authorized") is not False
        or next_experiment.get("live_order_allowed") is not False
    ):
        blockers.append("readiness_has_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "readiness_hash": expected_hash,
        "report_status": str(report.get("status") or ""),
        "formal_run_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
