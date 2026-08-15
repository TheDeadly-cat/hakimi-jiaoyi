from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import sys
import time
from typing import Any

from . import portfolio_backtest_replay as replay_module
from . import portfolio_evidence_archive as evidence_archive_module
from .implementation_manifest import (
    build_implementation_manifest,
    verify_implementation_manifest,
)
from .execution_authority import authority_violations as _authority_violations


PORTFOLIO_BACKTEST_CAMPAIGN_CONTRACT_SCHEMA_VERSION = (
    "portfolio-internal-backtest-campaign-contract-v1"
)
PORTFOLIO_BACKTEST_CAMPAIGN_REPORT_SCHEMA_VERSION = (
    "portfolio-internal-backtest-campaign-report-v1"
)
CAMPAIGN_PASS_STATUS = "INTERNAL_BACKTEST_CAMPAIGN_PASS"
CAMPAIGN_BLOCK_STATUS = "INTERNAL_BACKTEST_CAMPAIGN_BLOCK"
MIN_CAMPAIGN_REPETITIONS = 3
MAX_CAMPAIGN_REPETITIONS = 20
CAMPAIGN_LIMITATIONS = [
    "Repeated deterministic replay validates reproducibility, not profitability.",
    "Repeated replay of one frozen dataset creates no independent sample or forward observation.",
    "This campaign cannot tune parameters, activate paper trading, or authorize live orders.",
]


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


def _safe_bundle_path(bundle_dir: Path, relative_path: str) -> Path:
    candidate = (bundle_dir / str(relative_path or "")).resolve()
    candidate.relative_to(bundle_dir.resolve())
    return candidate


def _bundle_inventory(bundle_dir: Path) -> list[dict[str, Any]]:
    bundle = bundle_dir.resolve()
    records: list[dict[str, Any]] = []
    for path in sorted(bundle.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file():
            continue
        resolved = path.resolve()
        resolved.relative_to(bundle)
        records.append({
            "path": path.relative_to(bundle).as_posix(),
            "size": path.stat().st_size,
            "sha256": file_sha256(path),
        })
    return records


def _load_bundle_context(bundle_dir: Path | str) -> dict[str, Any]:
    bundle = Path(bundle_dir).resolve()
    manifest_path = bundle / "manifest.json"
    manifest = _read_json(manifest_path)
    pack_binding = dict(manifest.get("backtest_pack") or {})
    pack_path = _safe_bundle_path(bundle, str(pack_binding.get("archive_path") or ""))
    pack = _read_json(pack_path)
    replay = dict(manifest.get("backtest_replay") or {})
    if not replay:
        raise ValueError("Evidence archive has no isolated replay descriptor")
    return {
        "bundle": bundle,
        "manifest_path": manifest_path,
        "manifest": manifest,
        "manifest_file_sha256": file_sha256(manifest_path),
        "pack_path": pack_path,
        "pack": pack,
        "pack_file_sha256": file_sha256(pack_path),
        "replay": replay,
    }


def _archive_binding(context: dict[str, Any]) -> dict[str, Any]:
    bundle = Path(context["bundle"])
    manifest = dict(context["manifest"])
    pack = dict(context["pack"])
    replay = dict(context["replay"])
    rehearsal = dict(replay.get("replay_rehearsal") or {})
    return {
        "bundle_name": bundle.name,
        "archive_schema_version": str(manifest.get("schema_version") or ""),
        "archive_manifest_file_sha256": str(context["manifest_file_sha256"]),
        "archive_manifest_hash": str(manifest.get("manifest_hash") or ""),
        "candidate_hash": str(manifest.get("candidate_hash") or ""),
        "backtest_pack_archive_path": str(
            dict(manifest.get("backtest_pack") or {}).get("archive_path") or ""
        ),
        "backtest_pack_file_sha256": str(context["pack_file_sha256"]),
        "backtest_pack_hash": str(pack.get("pack_hash") or ""),
        "backtest_evidence_hash": str(pack.get("evidence_hash") or ""),
        "replay_bundle_hash": str(replay.get("bundle_hash") or ""),
        "replay_dataset_snapshot_hash": str(replay.get("dataset_snapshot_hash") or ""),
        "candidate_dataset_hash": str(replay.get("candidate_dataset_hash") or ""),
        "expected_replay_hash": str(rehearsal.get("replay_hash") or ""),
    }


def _runtime_fingerprint() -> dict[str, Any]:
    executable = Path(sys.executable).resolve()
    return {
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
        "python_executable_name": executable.name,
        "python_executable_sha256": file_sha256(executable),
        "isolated_process_per_repetition": True,
    }


def _controller_implementation() -> dict[str, Any]:
    project_root = Path(__file__).resolve().parents[2]
    files = [
        project_root / "run_internal_backtest_campaign.py",
        Path(__file__).resolve(),
        Path(replay_module.__file__).resolve(),
        Path(evidence_archive_module.__file__).resolve(),
    ]
    return build_implementation_manifest(files)


def build_internal_backtest_campaign_contract(
    bundle_dir: Path | str,
    *,
    declared_at: int,
    repetitions: int = MIN_CAMPAIGN_REPETITIONS,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    repeat_count = int(repetitions)
    timeout = int(timeout_seconds)
    if not MIN_CAMPAIGN_REPETITIONS <= repeat_count <= MAX_CAMPAIGN_REPETITIONS:
        raise ValueError(
            f"repetitions must be between {MIN_CAMPAIGN_REPETITIONS} and "
            f"{MAX_CAMPAIGN_REPETITIONS}"
        )
    if not 1 <= timeout <= 600:
        raise ValueError("timeout_seconds must be between 1 and 600")
    context = _load_bundle_context(bundle_dir)
    manifest = dict(context["manifest"])
    pack = dict(context["pack"])
    replay = dict(context["replay"])
    if manifest.get("status") != "ARCHIVE_READY":
        raise ValueError("Evidence archive is not ready")
    if pack.get("status") != "INTERNAL_BACKTEST_EVIDENCE_READY":
        raise ValueError("Internal backtest pack is not ready")
    if not str(dict(replay.get("replay_rehearsal") or {}).get("replay_hash") or ""):
        raise ValueError("Evidence archive has no successful replay rehearsal binding")
    if _authority_violations({"manifest": manifest, "pack": pack, "replay": replay}):
        raise ValueError("Evidence archive contains execution authority")

    binding = _archive_binding(context)
    timestamp = int(declared_at)
    contract = {
        "schema_version": PORTFOLIO_BACKTEST_CAMPAIGN_CONTRACT_SCHEMA_VERSION,
        "status": "PREREGISTERED",
        "campaign_id": f"ibc-{timestamp}-{binding['candidate_hash'][:12]}",
        "declared_at_local_ms": timestamp,
        "time_policy": "LOCAL_OPERATIONAL_TIMESTAMP_NOT_PROMOTION_EVIDENCE",
        "archive_binding": binding,
        "controller_implementation": _controller_implementation(),
        "execution_contract": {
            "repetitions": repeat_count,
            "timeout_seconds_per_repetition": timeout,
            "process_policy": "FRESH_PYTHON_ISOLATED_MODE_PROCESS_PER_REPETITION",
            "source_policy": "ARCHIVED_SOURCE_ONLY",
            "dataset_policy": "FROZEN_ARCHIVED_DATASET_ONLY",
            "network_access_allowed": False,
            "mutable_database_access_allowed": False,
            "market_data_fetch_allowed": False,
            "parameter_search_allowed": False,
            "early_stop_on_failure_allowed": False,
        },
        "evidence_accounting": {
            "development_trial_increment": 0,
            "independent_sample_increment": 0,
            "forward_observation_increment": 0,
            "forward_outcome_increment": 0,
            "promotion_evidence_allowed": False,
        },
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    contract["contract_hash"] = canonical_hash(contract)
    return contract


def verify_internal_backtest_campaign_contract(
    contract: dict[str, Any],
    bundle_dir: Path | str,
) -> dict[str, Any]:
    blockers: list[str] = []
    clean = dict(contract or {})
    expected_hash = str(clean.pop("contract_hash", "") or "")
    if contract.get("schema_version") != PORTFOLIO_BACKTEST_CAMPAIGN_CONTRACT_SCHEMA_VERSION:
        blockers.append("campaign_contract_schema_invalid")
    if contract.get("status") != "PREREGISTERED":
        blockers.append("campaign_contract_status_invalid")
    if not expected_hash or canonical_hash(clean) != expected_hash:
        blockers.append("campaign_contract_hash_invalid")
    try:
        context = _load_bundle_context(bundle_dir)
        actual_binding = _archive_binding(context)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        blockers.append(f"campaign_archive_binding_unavailable:{type(exc).__name__}")
        actual_binding = {}
    if dict(contract.get("archive_binding") or {}) != actual_binding:
        blockers.append("campaign_archive_binding_mismatch")
    controller_verification = verify_implementation_manifest(
        dict(contract.get("controller_implementation") or {})
    )
    if controller_verification.get("status") != "PASS":
        blockers.extend(
            f"campaign_controller:{item}"
            for item in controller_verification.get("blockers") or ["verification_blocked"]
        )

    execution = dict(contract.get("execution_contract") or {})
    repetitions = int(execution.get("repetitions") or 0)
    timeout = int(execution.get("timeout_seconds_per_repetition") or 0)
    if not MIN_CAMPAIGN_REPETITIONS <= repetitions <= MAX_CAMPAIGN_REPETITIONS:
        blockers.append("campaign_repetition_contract_invalid")
    if not 1 <= timeout <= 600:
        blockers.append("campaign_timeout_contract_invalid")
    expected_execution_flags = {
        "network_access_allowed": False,
        "mutable_database_access_allowed": False,
        "market_data_fetch_allowed": False,
        "parameter_search_allowed": False,
        "early_stop_on_failure_allowed": False,
    }
    for key, expected in expected_execution_flags.items():
        if execution.get(key) is not expected:
            blockers.append(f"campaign_execution_contract_invalid:{key}")
    if execution.get("process_policy") != "FRESH_PYTHON_ISOLATED_MODE_PROCESS_PER_REPETITION":
        blockers.append("campaign_process_policy_invalid")
    if execution.get("source_policy") != "ARCHIVED_SOURCE_ONLY":
        blockers.append("campaign_source_policy_invalid")
    if execution.get("dataset_policy") != "FROZEN_ARCHIVED_DATASET_ONLY":
        blockers.append("campaign_dataset_policy_invalid")

    accounting = dict(contract.get("evidence_accounting") or {})
    for key in (
        "development_trial_increment",
        "independent_sample_increment",
        "forward_observation_increment",
        "forward_outcome_increment",
    ):
        if accounting.get(key) != 0:
            blockers.append(f"campaign_evidence_accounting_invalid:{key}")
    if accounting.get("promotion_evidence_allowed") is not False:
        blockers.append("campaign_promotion_evidence_invalid")
    if contract.get("research_only") is not True:
        blockers.append("campaign_contract_research_only_missing")
    if _authority_violations(contract):
        blockers.append("campaign_contract_contains_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "contract_hash": expected_hash,
        "candidate_hash": str(actual_binding.get("candidate_hash") or ""),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _replay_result_hash_valid(result: dict[str, Any]) -> bool:
    clean = dict(result or {})
    expected = str(clean.pop("replay_hash", "") or "")
    return bool(expected) and canonical_hash(clean) == expected


def _safe_replay(
    bundle: Path,
    descriptor: dict[str, Any],
    *,
    timeout_seconds: int,
) -> dict[str, Any]:
    try:
        result = replay_module.run_isolated_portfolio_backtest_replay(
            bundle,
            descriptor,
            timeout_seconds=timeout_seconds,
        )
    except Exception as exc:
        result = {
            "schema_version": "portfolio-backtest-replay-result-v1",
            "status": "BLOCK",
            "blockers": [f"campaign_replay_exception:{type(exc).__name__}"],
            "error": str(exc)[:500],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    if not isinstance(result, dict):
        result = {
            "schema_version": "portfolio-backtest-replay-result-v1",
            "status": "BLOCK",
            "blockers": ["campaign_replay_result_not_object"],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    if not result.get("replay_hash"):
        result["replay_hash"] = canonical_hash(result)
    return result


def _build_run_record(sequence: int, result: dict[str, Any], duration_ms: int) -> dict[str, Any]:
    checks = dict(result.get("checks") or {})
    record = {
        "sequence": int(sequence),
        "duration_ms": max(int(duration_ms), 0),
        "status": str(result.get("status") or "BLOCK"),
        "replay_hash": str(result.get("replay_hash") or ""),
        "result_hash": canonical_hash(result),
        "dataset_hash": str(result.get("dataset_hash") or ""),
        "check_count": len(checks),
        "passed_check_count": sum(value is True for value in checks.values()),
        "network_access_attempt_count": int(result.get("network_access_attempt_count") or 0),
        "database_access_attempt_count": int(result.get("database_access_attempt_count") or 0),
        "blockers": list(result.get("blockers") or []),
        "result": result,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    record["record_hash"] = canonical_hash(record)
    return record


def _verify_run_record(record: dict[str, Any], *, expected_sequence: int) -> list[str]:
    blockers: list[str] = []
    clean = dict(record or {})
    expected_record_hash = str(clean.pop("record_hash", "") or "")
    result = dict(record.get("result") or {})
    checks = dict(result.get("checks") or {})
    if int(record.get("sequence") or 0) != expected_sequence:
        blockers.append(f"campaign_run_sequence_invalid:{expected_sequence}")
    if not expected_record_hash or canonical_hash(clean) != expected_record_hash:
        blockers.append(f"campaign_run_record_hash_invalid:{expected_sequence}")
    if str(record.get("result_hash") or "") != canonical_hash(result):
        blockers.append(f"campaign_run_result_hash_invalid:{expected_sequence}")
    if not _replay_result_hash_valid(result):
        blockers.append(f"campaign_replay_hash_invalid:{expected_sequence}")
    if str(record.get("replay_hash") or "") != str(result.get("replay_hash") or ""):
        blockers.append(f"campaign_run_replay_hash_binding_invalid:{expected_sequence}")
    if str(record.get("status") or "") != str(result.get("status") or ""):
        blockers.append(f"campaign_run_status_binding_invalid:{expected_sequence}")
    if str(record.get("dataset_hash") or "") != str(result.get("dataset_hash") or ""):
        blockers.append(f"campaign_run_dataset_binding_invalid:{expected_sequence}")
    if int(record.get("check_count") or 0) != len(checks):
        blockers.append(f"campaign_run_check_count_invalid:{expected_sequence}")
    if int(record.get("passed_check_count") or 0) != sum(value is True for value in checks.values()):
        blockers.append(f"campaign_run_pass_count_invalid:{expected_sequence}")
    if list(record.get("blockers") or []) != list(result.get("blockers") or []):
        blockers.append(f"campaign_run_blocker_binding_invalid:{expected_sequence}")
    if _authority_violations(record):
        blockers.append(f"campaign_run_contains_execution_authority:{expected_sequence}")
    return blockers


def _campaign_metrics(records: list[dict[str, Any]], *, requested: int) -> dict[str, Any]:
    durations = [max(int(record.get("duration_ms") or 0), 0) for record in records]
    hashes = [str(record.get("replay_hash") or "") for record in records]
    unique_hashes = sorted(set(value for value in hashes if value))
    return {
        "requested_repetitions": int(requested),
        "completed_repetitions": len(records),
        "passed_repetitions": sum(record.get("status") == "PASS" for record in records),
        "unique_replay_hash_count": len(unique_hashes),
        "deterministic_replay_hash": unique_hashes[0] if len(unique_hashes) == 1 else "",
        "total_duration_ms": sum(durations),
        "average_duration_ms": round(sum(durations) / len(durations), 3) if durations else 0.0,
        "maximum_duration_ms": max(durations, default=0),
        "network_access_attempt_count": sum(
            int(record.get("network_access_attempt_count") or 0) for record in records
        ),
        "database_access_attempt_count": sum(
            int(record.get("database_access_attempt_count") or 0) for record in records
        ),
        "development_trial_increment": 0,
        "independent_sample_increment": 0,
        "forward_observation_increment": 0,
        "forward_outcome_increment": 0,
    }


def _evidence_summary(context: dict[str, Any]) -> dict[str, Any]:
    pack = dict(context.get("pack") or {})
    return {
        "candidate": dict(pack.get("candidate") or {}),
        "pack_status": str(pack.get("status") or ""),
        "promotion_status": str(pack.get("promotion_status") or ""),
        "historical_backtest": dict(pack.get("historical_backtest") or {}),
        "statistical_claim": dict(pack.get("statistical_claim") or {}),
        "forward_progress": dict(pack.get("forward_progress") or {}),
        "promotion_blockers": list(pack.get("promotion_blockers") or []),
        "pack_checks": dict(pack.get("checks") or {}),
    }


def _campaign_checks(
    *,
    contract_verification: dict[str, Any],
    archive_verification: dict[str, Any],
    contract: dict[str, Any],
    context: dict[str, Any],
    records: list[dict[str, Any]],
    inventory_before: list[dict[str, Any]],
    inventory_after: list[dict[str, Any]],
) -> dict[str, bool]:
    execution = dict(contract.get("execution_contract") or {})
    accounting = dict(contract.get("evidence_accounting") or {})
    requested = int(execution.get("repetitions") or 0)
    replay = dict(context.get("replay") or {})
    expected_replay_hash = str(dict(replay.get("replay_rehearsal") or {}).get("replay_hash") or "")
    expected_dataset_hash = str(replay.get("candidate_dataset_hash") or "")
    replay_hashes = [str(record.get("replay_hash") or "") for record in records]
    return {
        "contract_integrity_pass": contract_verification.get("status") == "PASS",
        "archive_integrity_pass": archive_verification.get("status") == "PASS",
        "backtest_pack_read_only_ready": (
            dict(context.get("pack") or {}).get("status") == "INTERNAL_BACKTEST_EVIDENCE_READY"
        ),
        "fixed_repetition_count_completed": len(records) == requested,
        "all_replays_pass": bool(records) and all(record.get("status") == "PASS" for record in records),
        "all_replay_records_self_verified": bool(records) and all(
            not _verify_run_record(record, expected_sequence=index)
            for index, record in enumerate(records, start=1)
        ),
        "replay_hash_matches_archived_rehearsal": bool(records) and all(
            value == expected_replay_hash for value in replay_hashes
        ),
        "replay_hash_deterministic_across_processes": (
            bool(records) and len(set(replay_hashes)) == 1 and bool(replay_hashes[0])
        ),
        "dataset_binding_matches": bool(records) and all(
            str(record.get("dataset_hash") or "") == expected_dataset_hash for record in records
        ),
        "network_not_accessed": bool(records) and all(
            int(record.get("network_access_attempt_count") or 0) == 0 for record in records
        ),
        "mutable_database_not_accessed": bool(records) and all(
            int(record.get("database_access_attempt_count") or 0) == 0 for record in records
        ),
        "archive_inventory_unchanged": inventory_before == inventory_after,
        "parameter_search_not_allowed": execution.get("parameter_search_allowed") is False,
        "market_data_fetch_not_allowed": execution.get("market_data_fetch_allowed") is False,
        "repeated_replays_not_counted_as_new_evidence": (
            accounting.get("development_trial_increment") == 0
            and accounting.get("independent_sample_increment") == 0
            and accounting.get("forward_observation_increment") == 0
            and accounting.get("forward_outcome_increment") == 0
            and accounting.get("promotion_evidence_allowed") is False
        ),
        "zero_execution_authority": not _authority_violations(
            {"contract": contract, "archive_verification": archive_verification, "records": records}
        ),
    }


def _outcome_blockers(checks: dict[str, bool], records: list[dict[str, Any]]) -> list[str]:
    blockers = [f"campaign_check_failed:{name}" for name, passed in checks.items() if not passed]
    for record in records:
        sequence = int(record.get("sequence") or 0)
        blockers.extend(
            f"campaign_replay_{sequence}:{item}"
            for item in list(record.get("blockers") or [])
        )
    return list(dict.fromkeys(blockers))


def run_internal_backtest_campaign(
    bundle_dir: Path | str,
    contract: dict[str, Any],
    *,
    generated_at: int | None = None,
    contract_file_path: Path | str,
) -> dict[str, Any]:
    bundle = Path(bundle_dir).resolve()
    contract_path = Path(contract_file_path).resolve()
    if contract_path == bundle or contract_path.is_relative_to(bundle):
        raise ValueError("Campaign contract must be stored outside the immutable evidence archive")
    artifact_contract = _read_json(contract_path)
    if artifact_contract != contract:
        raise ValueError("Campaign contract file does not match the preregistered contract")
    contract_artifact = {
        "path": str(contract_path),
        "file_sha256": file_sha256(contract_path),
        "contract_hash": str(contract.get("contract_hash") or ""),
    }
    contract_verification = verify_internal_backtest_campaign_contract(contract, bundle)
    context = _load_bundle_context(bundle)
    inventory_before = _bundle_inventory(bundle)
    archive_started = time.perf_counter()
    try:
        archive_verification = evidence_archive_module.verify_portfolio_evidence_archive(bundle)
    except Exception as exc:
        archive_verification = {
            "status": "BLOCK",
            "blockers": [f"campaign_archive_verification_exception:{type(exc).__name__}"],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    archive_verification_duration_ms = round((time.perf_counter() - archive_started) * 1000)

    execution = dict(contract.get("execution_contract") or {})
    repetitions = int(execution.get("repetitions") or 0)
    timeout_seconds = int(execution.get("timeout_seconds_per_repetition") or 0)
    records: list[dict[str, Any]] = []
    if contract_verification.get("status") == "PASS" and archive_verification.get("status") == "PASS":
        for sequence in range(1, repetitions + 1):
            started = time.perf_counter()
            result = _safe_replay(
                bundle,
                dict(context["replay"]),
                timeout_seconds=timeout_seconds,
            )
            duration_ms = round((time.perf_counter() - started) * 1000)
            records.append(_build_run_record(sequence, result, duration_ms))
    inventory_after = _bundle_inventory(bundle)
    checks = _campaign_checks(
        contract_verification=contract_verification,
        archive_verification=archive_verification,
        contract=contract,
        context=context,
        records=records,
        inventory_before=inventory_before,
        inventory_after=inventory_after,
    )
    blockers = _outcome_blockers(checks, records)
    status = CAMPAIGN_PASS_STATUS if not blockers else CAMPAIGN_BLOCK_STATUS
    timestamp = int(generated_at if generated_at is not None else time.time_ns() // 1_000_000)
    report = {
        "schema_version": PORTFOLIO_BACKTEST_CAMPAIGN_REPORT_SCHEMA_VERSION,
        "status": status,
        "conclusion": (
            "REPRODUCIBILITY_PASS_NOT_PROMOTION_EVIDENCE"
            if status == CAMPAIGN_PASS_STATUS
            else "REPRODUCIBILITY_BLOCKED"
        ),
        "blockers": blockers,
        "generated_at_local_ms": timestamp,
        "campaign_id": str(contract.get("campaign_id") or ""),
        "contract_hash": str(contract.get("contract_hash") or ""),
        "contract": contract,
        "contract_artifact": contract_artifact,
        "archive_binding": _archive_binding(context),
        "archive_verification": archive_verification,
        "archive_verification_duration_ms": archive_verification_duration_ms,
        "runtime_fingerprint": _runtime_fingerprint(),
        "evidence_summary": _evidence_summary(context),
        "inventory_before": inventory_before,
        "inventory_before_hash": canonical_hash(inventory_before),
        "inventory_after": inventory_after,
        "inventory_after_hash": canonical_hash(inventory_after),
        "run_records": records,
        "metrics": _campaign_metrics(records, requested=repetitions),
        "checks": checks,
        "limitations": CAMPAIGN_LIMITATIONS,
        "evidence_accounting": dict(contract.get("evidence_accounting") or {}),
        "promotion_status": "BLOCK",
        "automatic_paper_activation_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    report["campaign_hash"] = canonical_hash(report)
    return report


def verify_internal_backtest_campaign_report(
    report: dict[str, Any],
    bundle_dir: Path | str,
    *,
    rerun_replays: bool = True,
) -> dict[str, Any]:
    integrity_blockers: list[str] = []
    clean = dict(report or {})
    expected_campaign_hash = str(clean.pop("campaign_hash", "") or "")
    if report.get("schema_version") != PORTFOLIO_BACKTEST_CAMPAIGN_REPORT_SCHEMA_VERSION:
        integrity_blockers.append("campaign_report_schema_invalid")
    if not expected_campaign_hash or canonical_hash(clean) != expected_campaign_hash:
        integrity_blockers.append("campaign_report_hash_invalid")
    bundle = Path(bundle_dir).resolve()
    contract = dict(report.get("contract") or {})
    contract_verification = verify_internal_backtest_campaign_contract(contract, bundle)
    if contract_verification.get("status") != "PASS":
        integrity_blockers.extend(
            f"campaign_contract:{item}"
            for item in contract_verification.get("blockers") or ["verification_blocked"]
        )
    if str(report.get("contract_hash") or "") != str(contract.get("contract_hash") or ""):
        integrity_blockers.append("campaign_report_contract_hash_mismatch")
    if str(report.get("campaign_id") or "") != str(contract.get("campaign_id") or ""):
        integrity_blockers.append("campaign_report_id_mismatch")

    contract_artifact = dict(report.get("contract_artifact") or {})
    if not contract_artifact:
        integrity_blockers.append("campaign_contract_file_binding_missing")
    else:
        try:
            contract_path = Path(str(contract_artifact.get("path") or "")).resolve()
            artifact_contract = _read_json(contract_path)
            if file_sha256(contract_path) != str(contract_artifact.get("file_sha256") or ""):
                integrity_blockers.append("campaign_contract_file_hash_mismatch")
            if artifact_contract != contract:
                integrity_blockers.append("campaign_contract_file_content_mismatch")
            if str(contract_artifact.get("contract_hash") or "") != str(contract.get("contract_hash") or ""):
                integrity_blockers.append("campaign_contract_file_binding_mismatch")
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            integrity_blockers.append(f"campaign_contract_file_unavailable:{type(exc).__name__}")

    try:
        context = _load_bundle_context(bundle)
        current_inventory = _bundle_inventory(bundle)
        current_archive_verification = evidence_archive_module.verify_portfolio_evidence_archive(bundle)
    except Exception as exc:
        integrity_blockers.append(f"campaign_current_archive_unavailable:{type(exc).__name__}")
        context = {}
        current_inventory = []
        current_archive_verification = {
            "status": "BLOCK",
            "blockers": [f"campaign_current_archive_exception:{type(exc).__name__}"],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    if context and dict(report.get("archive_binding") or {}) != _archive_binding(context):
        integrity_blockers.append("campaign_report_archive_binding_mismatch")
    if context and dict(report.get("evidence_summary") or {}) != _evidence_summary(context):
        integrity_blockers.append("campaign_report_evidence_summary_mismatch")
    if dict(report.get("archive_verification") or {}) != current_archive_verification:
        integrity_blockers.append("campaign_report_archive_verification_mismatch")

    inventory_before = list(report.get("inventory_before") or [])
    inventory_after = list(report.get("inventory_after") or [])
    if str(report.get("inventory_before_hash") or "") != canonical_hash(inventory_before):
        integrity_blockers.append("campaign_inventory_before_hash_invalid")
    if str(report.get("inventory_after_hash") or "") != canonical_hash(inventory_after):
        integrity_blockers.append("campaign_inventory_after_hash_invalid")
    if current_inventory != inventory_after:
        integrity_blockers.append("campaign_archive_changed_after_report")

    records = [dict(item or {}) for item in list(report.get("run_records") or [])]
    for index, record in enumerate(records, start=1):
        integrity_blockers.extend(_verify_run_record(record, expected_sequence=index))
    expected_checks = _campaign_checks(
        contract_verification=contract_verification,
        archive_verification=current_archive_verification,
        contract=contract,
        context=context,
        records=records,
        inventory_before=inventory_before,
        inventory_after=inventory_after,
    ) if context else {}
    if dict(report.get("checks") or {}) != expected_checks:
        integrity_blockers.append("campaign_report_checks_semantics_mismatch")
    requested = int(dict(contract.get("execution_contract") or {}).get("repetitions") or 0)
    if dict(report.get("metrics") or {}) != _campaign_metrics(records, requested=requested):
        integrity_blockers.append("campaign_report_metrics_semantics_mismatch")
    if dict(report.get("runtime_fingerprint") or {}) != _runtime_fingerprint():
        integrity_blockers.append("campaign_report_runtime_fingerprint_mismatch")
    if list(report.get("limitations") or []) != CAMPAIGN_LIMITATIONS:
        integrity_blockers.append("campaign_report_limitations_mismatch")
    expected_outcome_blockers = _outcome_blockers(expected_checks, records) if expected_checks else []
    if list(report.get("blockers") or []) != expected_outcome_blockers:
        integrity_blockers.append("campaign_report_blockers_semantics_mismatch")
    expected_status = CAMPAIGN_PASS_STATUS if not expected_outcome_blockers else CAMPAIGN_BLOCK_STATUS
    if report.get("status") != expected_status:
        integrity_blockers.append("campaign_report_status_semantics_mismatch")
    expected_conclusion = (
        "REPRODUCIBILITY_PASS_NOT_PROMOTION_EVIDENCE"
        if expected_status == CAMPAIGN_PASS_STATUS
        else "REPRODUCIBILITY_BLOCKED"
    )
    if report.get("conclusion") != expected_conclusion:
        integrity_blockers.append("campaign_report_conclusion_semantics_mismatch")
    if dict(report.get("evidence_accounting") or {}) != dict(contract.get("evidence_accounting") or {}):
        integrity_blockers.append("campaign_report_evidence_accounting_mismatch")
    if report.get("promotion_status") != "BLOCK":
        integrity_blockers.append("campaign_report_promotion_status_invalid")
    if report.get("research_only") is not True or _authority_violations(report):
        integrity_blockers.append("campaign_report_contains_execution_authority")

    rerun_results: list[dict[str, Any]] = []
    if (
        rerun_replays
        and context
        and not integrity_blockers
        and report.get("status") == CAMPAIGN_PASS_STATUS
    ):
        timeout_seconds = int(
            dict(contract.get("execution_contract") or {}).get("timeout_seconds_per_repetition") or 0
        )
        for record in records:
            result = _safe_replay(
                bundle,
                dict(context["replay"]),
                timeout_seconds=timeout_seconds,
            )
            rerun_results.append(result)
            if result.get("status") != "PASS":
                integrity_blockers.append("campaign_verifier_replay_blocked")
            if str(result.get("replay_hash") or "") != str(record.get("replay_hash") or ""):
                integrity_blockers.append("campaign_verifier_replay_hash_mismatch")
            if canonical_hash(result) != str(record.get("result_hash") or ""):
                integrity_blockers.append("campaign_verifier_replay_result_mismatch")
        if _bundle_inventory(bundle) != current_inventory:
            integrity_blockers.append("campaign_verifier_modified_archive")

    return {
        "status": "PASS" if not integrity_blockers else "BLOCK",
        "blockers": list(dict.fromkeys(integrity_blockers)),
        "claim_status": str(report.get("status") or CAMPAIGN_BLOCK_STATUS),
        "conclusion": str(report.get("conclusion") or ""),
        "campaign_hash": expected_campaign_hash,
        "contract_hash": str(contract.get("contract_hash") or ""),
        "candidate_hash": str(dict(report.get("archive_binding") or {}).get("candidate_hash") or ""),
        "rerun_replay_count": len(rerun_results),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
