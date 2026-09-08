from __future__ import annotations

from copy import deepcopy
import hashlib
from importlib import metadata
from pathlib import Path
import platform
import re
from typing import Any

from examples.build_synthetic_strategy_benchmark_report_v9 import (
    plan_synthetic_strategy_benchmark_report_v9,
    verify_synthetic_strategy_benchmark_report_v9,
)
from hakimi_research.trial_return_matrix import (
    TrialReturnMatrixError,
    canonical_trial_return_matrix_sha256,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-benchmark-research-lock-audit-plan-v1"
BUNDLE_SCHEMA_VERSION = "synthetic-strategy-benchmark-research-lock-audit-bundle-v1"
RECEIPT_SCHEMA_VERSION = "synthetic-strategy-benchmark-research-lock-audit-receipt-v1"
LOCK_SCHEMA_VERSION = "benchmark-research-lock-v1"
STATUS = "BLOCK"
MATURITY = "SYNTHETIC_BENCHMARK_RESEARCH_LOCK_AND_SOURCE_ENVELOPE_WITH_GAPS"
EVIDENCE_STATE = "OBSERVED_WITH_GAPS"
SOURCE_LOGICAL_RUN_COUNT = 204

_AUTHORITY = {
    "blind_test_complete": False,
    "formal_inference_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}
_REPLACED_GAPS = {
    "DEPENDENCY_LOCK_HASH_GAP",
    "DEPENDENCY_LOCK_NOT_FULLY_PINNED",
}
_LOCK_GAPS = [
    "BENCHMARK_LOCK_PLATFORM_SPECIFIC",
    "DEPENDENCY_ARTIFACT_HASH_GAP",
    "FULL_APPLICATION_DEPENDENCY_LOCK_GAP",
    "INSTALLED_ENVIRONMENT_MATCH_NOT_FRESH_INSTALL_PROOF",
]
_EXPECTED_HEADERS = {
    "scope": "deterministic-synthetic-strategy-benchmark-v9",
    "closure_policy": "CURRENT_MARKERS_NO_EXTRAS",
    "python_implementation": "CPython",
    "python_version": "3.14.6",
    "platform_system": "Windows",
    "platform_release": "11",
    "platform_machine": "AMD64",
    "artifact_hashes": "ABSENT",
    "full_application_scope": "FALSE",
}
_EXPECTED_PINS = [
    {"name": "numpy", "version": "2.4.6"},
    {"name": "packaging", "version": "26.2"},
    {"name": "pandas", "version": "3.0.3"},
    {"name": "pyarrow", "version": "24.0.0"},
    {"name": "python-dateutil", "version": "2.9.0.post0"},
    {"name": "six", "version": "1.17.0"},
    {"name": "tzdata", "version": "2026.2"},
]
_LOCK_PATH = "outputs/python_quant_bot/requirements-benchmark-v9.lock"
_SOURCE_PATHS = [
    "outputs/python_quant_bot/examples/build_synthetic_strategy_benchmark_report_v1.py",
    "outputs/python_quant_bot/examples/build_synthetic_strategy_benchmark_report_v2.py",
    "outputs/python_quant_bot/examples/build_synthetic_strategy_benchmark_report_v3.py",
    "outputs/python_quant_bot/examples/build_synthetic_strategy_benchmark_report_v4.py",
    "outputs/python_quant_bot/examples/build_synthetic_strategy_benchmark_report_v5.py",
    "outputs/python_quant_bot/examples/build_synthetic_strategy_benchmark_report_v6.py",
    "outputs/python_quant_bot/examples/build_synthetic_strategy_benchmark_report_v7.py",
    "outputs/python_quant_bot/examples/build_synthetic_strategy_benchmark_report_v8.py",
    "outputs/python_quant_bot/examples/build_synthetic_strategy_benchmark_report_v9.py",
    "outputs/python_quant_bot/examples/build_synthetic_strategy_benchmark_report_v10.py",
    "outputs/python_quant_bot/exchange_terminal/__init__.py",
    "outputs/python_quant_bot/exchange_terminal/application/__init__.py",
    "outputs/python_quant_bot/exchange_terminal/application/strategy_family_inventory_adapter_v1.py",
    "outputs/python_quant_bot/exchange_terminal/application/synthetic_strategy_benchmark_controls_v1.py",
    "outputs/python_quant_bot/exchange_terminal/application/synthetic_strategy_benchmark_research_lock_audit_v1.py",
    "outputs/python_quant_bot/exchange_terminal/application/synthetic_strategy_bootstrap_validation_v1.py",
    "outputs/python_quant_bot/exchange_terminal/application/synthetic_strategy_cscv_pbo_tie_bounds_v1.py",
    "outputs/python_quant_bot/exchange_terminal/application/synthetic_strategy_cscv_pbo_validation_v1.py",
    "outputs/python_quant_bot/exchange_terminal/application/synthetic_strategy_deflated_sharpe_validation_v1.py",
    "outputs/python_quant_bot/exchange_terminal/application/synthetic_strategy_high_volatility_validation_v1.py",
    "outputs/python_quant_bot/exchange_terminal/application/synthetic_strategy_market_regime_validation_v1.py",
    "outputs/python_quant_bot/exchange_terminal/application/synthetic_strategy_report_bundle_v1.py",
    "outputs/python_quant_bot/exchange_terminal/application/synthetic_strategy_reproducibility_provenance_gap_audit_v1.py",
    "outputs/python_quant_bot/exchange_terminal/application/synthetic_strategy_return_contribution_concentration_v1.py",
    "outputs/python_quant_bot/exchange_terminal/application/synthetic_strategy_robustness_evidence_v1.py",
    "outputs/python_quant_bot/exchange_terminal/application/synthetic_strategy_trial_return_matrix_v1.py",
    "outputs/python_quant_bot/quant_bot/__init__.py",
    "outputs/python_quant_bot/quant_bot/backtest.py",
    "outputs/python_quant_bot/quant_bot/config.py",
    "outputs/python_quant_bot/quant_bot/execution.py",
    "outputs/python_quant_bot/quant_bot/experiment_manifest.py",
    "outputs/python_quant_bot/quant_bot/indicators.py",
    "outputs/python_quant_bot/quant_bot/models.py",
    "outputs/python_quant_bot/quant_bot/risk.py",
    "outputs/python_quant_bot/quant_bot/strategies/__init__.py",
    "outputs/python_quant_bot/quant_bot/strategies/base.py",
    "outputs/python_quant_bot/quant_bot/strategies/templates.py",
    "src/hakimi_research/__init__.py",
    "src/hakimi_research/bootstrap_confidence_evidence.py",
    "src/hakimi_research/synthetic_strategy_bootstrap_validation.py",
    "src/hakimi_research/cscv_pbo_diagnostic.py",
    "src/hakimi_research/cscv_pbo_tie_bounds.py",
    "src/hakimi_research/synthetic_strategy_cscv_pbo_validation.py",
    "src/hakimi_research/synthetic_strategy_cscv_pbo_tie_bounds.py",
    "src/hakimi_research/deflated_sharpe_diagnostic.py",
    "src/hakimi_research/synthetic_strategy_deflated_sharpe_validation.py",
    "src/hakimi_research/distribution_evidence.py",
    "src/hakimi_research/frozen_evaluation.py",
    "src/hakimi_research/market_regime_evidence.py",
    "src/hakimi_research/product_capabilities.py",
    "src/hakimi_research/return_contribution_concentration.py",
    "src/hakimi_research/source_layout.py",
    "src/hakimi_research/strategy_family_inventory.py",
    "src/hakimi_research/synthetic_strategy_report_bundle.py",
    "src/hakimi_research/synthetic_strategy_robustness_evidence.py",
    "src/hakimi_research/synthetic_strategy_trial_return_matrix.py",
    "src/hakimi_research/synthetic_benchmark_controls.py",
    "src/hakimi_research/trial_return_matrix.py",
    "src/hakimi_research/validation_evidence.py",
]


class SyntheticStrategyBenchmarkResearchLockAuditError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise SyntheticStrategyBenchmarkResearchLockAuditError(
        f"{path}: {message}"
    )


def _repo_root() -> Path:
    root = Path(__file__).resolve().parents[4]
    if not (root / "outputs" / "python_quant_bot").is_dir():
        _fail("source_root", "repository layout mismatch")
    return root


def _seal(record: dict[str, Any], field: str) -> dict[str, Any]:
    if field in record:
        _fail(field, "duplicate seal field")
    record[field] = canonical_trial_return_matrix_sha256(record)
    return record


def _require_canonical(value: Any, path: str) -> None:
    try:
        canonical_trial_return_matrix_sha256(value)
    except TrialReturnMatrixError as exc:
        _fail(path, str(exc))


def _file_record(root: Path, relative_path: str) -> dict[str, Any]:
    if type(relative_path) is not str or not relative_path:
        _fail("source_path", "must be an exact non-empty str")
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        _fail(relative_path, "must remain inside repository root")
    if not path.is_file():
        _fail(relative_path, "required source file is missing")
    payload = path.read_bytes()
    return {
        "path": relative_path,
        "byte_count": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _source_manifest() -> dict[str, Any]:
    if len(_SOURCE_PATHS) != len(set(_SOURCE_PATHS)):
        _fail("source_paths", "must be unique")
    root = _repo_root()
    files = [_file_record(root, path) for path in _SOURCE_PATHS]
    manifest = {
        "schema_version": "benchmark-v9-source-envelope-v1",
        "scope": "V9_RUNTIME_IMPORT_CLOSURE_PLUS_AUDIT_AND_V10_CONSUMER",
        "root_module": "examples.build_synthetic_strategy_benchmark_report_v9",
        "module_file_count": len(files),
        "files": files,
    }
    return _seal(manifest, "source_manifest_sha256")


def _parse_lock() -> dict[str, Any]:
    root = _repo_root()
    file_record = _file_record(root, _LOCK_PATH)
    path = root / _LOCK_PATH
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeError as exc:
        _fail("dependency_lock", f"must be UTF-8:{exc}")
    lines = text.splitlines()
    if not lines or lines[0] != f"# {LOCK_SCHEMA_VERSION}":
        _fail("dependency_lock.schema_version", "header mismatch")
    headers: dict[str, str] = {}
    pins: list[dict[str, str]] = []
    pin_pattern = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s]+)$")
    for index, line in enumerate(lines[1:], start=2):
        if not line:
            _fail(f"dependency_lock.line[{index}]", "blank lines are forbidden")
        if line.startswith("# "):
            body = line[2:]
            if "=" not in body:
                _fail(f"dependency_lock.line[{index}]", "comment shape mismatch")
            key, value = body.split("=", 1)
            if not key or not value or key in headers:
                _fail(f"dependency_lock.line[{index}]", "header mismatch")
            headers[key] = value
            continue
        match = pin_pattern.fullmatch(line)
        if match is None:
            _fail(f"dependency_lock.line[{index}]", "must be an exact == pin")
        pins.append({"name": match.group(1), "version": match.group(2)})
    if headers != _EXPECTED_HEADERS:
        _fail("dependency_lock.headers", "platform or scope drifted")
    if pins != _EXPECTED_PINS:
        _fail("dependency_lock.pins", "exact pin set or order drifted")
    lock = {
        "schema_version": LOCK_SCHEMA_VERSION,
        "path": _LOCK_PATH,
        "byte_count": file_record["byte_count"],
        "dependency_lock_sha256": file_record["sha256"],
        "headers": headers,
        "pins": pins,
        "exact_pin_count": len(pins),
        "all_requirements_exactly_version_pinned": True,
        "artifact_hashes_present": False,
        "full_application_scope": False,
    }
    return _seal(lock, "lock_manifest_sha256")


def _gaps() -> list[str]:
    source_gaps = plan_synthetic_strategy_benchmark_report_v9()["gaps"]
    retained = [gap for gap in source_gaps if gap not in _REPLACED_GAPS]
    return sorted(set(retained).union(_LOCK_GAPS))


def _platform_identity() -> dict[str, str]:
    return {
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "platform_system": platform.system(),
        "platform_release": platform.release(),
        "platform_machine": platform.machine(),
    }


def _expected_platform_identity() -> dict[str, str]:
    return {
        key: _EXPECTED_HEADERS[key]
        for key in (
            "python_implementation",
            "python_version",
            "platform_system",
            "platform_release",
            "platform_machine",
        )
    }


def _installed_resolution(lock_manifest: dict[str, Any]) -> dict[str, Any]:
    records = []
    for pin in lock_manifest["pins"]:
        name = pin["name"]
        try:
            installed = metadata.version(name)
        except metadata.PackageNotFoundError:
            installed = None
        records.append(
            {
                "name": name,
                "locked_version": pin["version"],
                "installed_version": installed,
                "exact_match": installed == pin["version"],
            }
        )
    resolution = {
        "schema_version": "benchmark-research-installed-resolution-v1",
        "record_count": len(records),
        "records": records,
        "exact_match_count": sum(item["exact_match"] for item in records),
        "missing_distribution_count": sum(
            item["installed_version"] is None for item in records
        ),
        "mismatch_count": sum(not item["exact_match"] for item in records),
        "all_locked_versions_installed_exactly": all(
            item["exact_match"] for item in records
        ),
    }
    return _seal(resolution, "installed_resolution_sha256")


def plan_synthetic_strategy_benchmark_research_lock_audit_v1() -> dict[str, Any]:
    source_plan = plan_synthetic_strategy_benchmark_report_v9()
    source_manifest = _source_manifest()
    lock_manifest = _parse_lock()
    plan = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "data_source": "LOCAL_SOURCE_LOCK_AND_INSTALLED_METADATA_READ_ONLY",
        "source_report_plan_sha256": source_plan["plan_sha256"],
        "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "planned_run_count": 0,
        "executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "planned_analysis_count": 1,
        "executed_analysis_count": 0,
        "requires_prebuilt_v9_report": True,
        "requires_exact_execute_true": True,
        "source_manifest": source_manifest,
        "lock_manifest": lock_manifest,
        "expected_platform_identity": _expected_platform_identity(),
        "benchmark_lock_scope_complete": True,
        "full_application_lock_scope_complete": False,
        "dependency_artifact_hashes_present": False,
        "runtime_mutations": False,
        "gaps": _gaps(),
        "authority": deepcopy(_AUTHORITY),
    }
    return _seal(plan, "plan_sha256")


def _compose_audit(
    source_report_v9: dict[str, Any], plan: dict[str, Any]
) -> dict[str, Any]:
    platform_identity = _platform_identity()
    if platform_identity != plan["expected_platform_identity"]:
        _fail("platform_identity", "does not match the platform-scoped lock")
    resolution = _installed_resolution(plan["lock_manifest"])
    if not resolution["all_locked_versions_installed_exactly"]:
        _fail("installed_resolution", "locked versions are missing or mismatched")
    bundle = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "evidence_state": EVIDENCE_STATE,
        "status": STATUS,
        "maturity": MATURITY,
        "plan": deepcopy(plan),
        "source_report_v9_sha256": source_report_v9["report_sha256"],
        "source_report_v9_plan_sha256": source_report_v9["plan"][
            "plan_sha256"
        ],
        "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "source_manifest": deepcopy(plan["source_manifest"]),
        "dependency_lock_manifest": deepcopy(plan["lock_manifest"]),
        "dependency_lock_sha256": plan["lock_manifest"][
            "dependency_lock_sha256"
        ],
        "platform_identity": platform_identity,
        "installed_resolution": resolution,
        "benchmark_lock_fully_version_pinned": True,
        "dependency_artifact_hashes_present": False,
        "full_application_lock_covered": False,
        "planned_run_count": 0,
        "executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "executed_analysis_count": 1,
        "runtime_mutations": False,
        "computed_diagnostics": [
            "V9_RUNTIME_IMPORT_SOURCE_ENVELOPE_SHA256",
            "BENCHMARK_RESEARCH_LOCK_SHA256",
            "EXACT_INSTALLED_VERSION_MATCH",
            "PLATFORM_IDENTITY_MATCH",
        ],
        "gaps": list(plan["gaps"]),
        "authority": deepcopy(_AUTHORITY),
    }
    return _seal(bundle, "bundle_sha256")


def build_synthetic_strategy_benchmark_research_lock_audit_v1(
    source_report_v9: dict[str, Any], *, execute: bool = False
) -> dict[str, Any]:
    if type(execute) is not bool or execute is not True:
        raise SyntheticStrategyBenchmarkResearchLockAuditError(
            "audit requires exact execute=True; inspect the plan first"
        )
    try:
        verify_synthetic_strategy_benchmark_report_v9(source_report_v9)
    except Exception as exc:
        _fail("source_report_v9", f"verification failed:{type(exc).__name__}:{exc}")
    plan = plan_synthetic_strategy_benchmark_research_lock_audit_v1()
    return _compose_audit(source_report_v9, plan)


def verify_synthetic_strategy_benchmark_research_lock_audit_v1(
    bundle: dict[str, Any], source_report_v9: dict[str, Any]
) -> dict[str, Any]:
    if type(bundle) is not dict:
        _fail("bundle", "must be an exact dict")
    _require_canonical(bundle, "bundle")
    try:
        verify_synthetic_strategy_benchmark_report_v9(source_report_v9)
    except Exception as exc:
        _fail("source_report_v9", f"verification failed:{type(exc).__name__}:{exc}")
    plan = plan_synthetic_strategy_benchmark_research_lock_audit_v1()
    expected = _compose_audit(source_report_v9, plan)
    if bundle != expected:
        _fail("bundle", "must match deterministic source, lock, and environment audit")
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "state": EVIDENCE_STATE,
        "status": STATUS,
        "maturity": MATURITY,
        "bundle_sha256": bundle["bundle_sha256"],
        "source_report_v9_sha256": bundle["source_report_v9_sha256"],
        "source_manifest_sha256": bundle["source_manifest"][
            "source_manifest_sha256"
        ],
        "source_module_file_count": bundle["source_manifest"][
            "module_file_count"
        ],
        "dependency_lock_sha256": bundle["dependency_lock_sha256"],
        "exact_pin_count": bundle["dependency_lock_manifest"][
            "exact_pin_count"
        ],
        "installed_exact_match_count": bundle["installed_resolution"][
            "exact_match_count"
        ],
        "benchmark_lock_fully_version_pinned": True,
        "dependency_artifact_hashes_present": False,
        "full_application_lock_covered": False,
        "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "executed_analysis_count": 1,
        "runtime_mutations": False,
        "gaps": list(bundle["gaps"]),
        "authority": deepcopy(_AUTHORITY),
    }


def replay_synthetic_strategy_benchmark_research_lock_audit_v1(
    bundle: dict[str, Any], source_report_v9: dict[str, Any]
) -> dict[str, Any]:
    receipt = verify_synthetic_strategy_benchmark_research_lock_audit_v1(
        bundle, source_report_v9
    )
    replayed = build_synthetic_strategy_benchmark_research_lock_audit_v1(
        source_report_v9, execute=True
    )
    if replayed != bundle:
        _fail("replay", "deterministic audit mismatch")
    output = dict(receipt)
    output["replay_status"] = "EXACT_MATCH"
    return output


def render_synthetic_strategy_benchmark_research_lock_audit_markdown_v1(
    bundle: dict[str, Any], source_report_v9: dict[str, Any]
) -> str:
    receipt = verify_synthetic_strategy_benchmark_research_lock_audit_v1(
        bundle, source_report_v9
    )
    markdown = "\n".join(
        [
            "# Synthetic Benchmark Research Lock Audit v1",
            "",
            "## SOURCE",
            "- LOCAL_SOURCE_LOCK_AND_INSTALLED_METADATA_READ_ONLY",
            f"- Bound source files: {receipt['source_module_file_count']}",
            f"- Exact benchmark lock pins: {receipt['exact_pin_count']}",
            f"- Exact installed matches: {receipt['installed_exact_match_count']}",
            "- Additional backtest runs: 0",
            "",
            "## GAP",
            *[f"- {gap}" for gap in receipt["gaps"]],
            "",
            "## MATURITY",
            f"- {receipt['maturity']}",
            "- The benchmark scope is version pinned for one declared platform.",
            "- Package artifact hashes and a full-application lock remain absent.",
            "- Installed-version matching is not a fresh-install reproduction proof.",
            "",
            "## PERMISSION",
            f"- Status: {receipt['status']}",
            "- Formal inference authority: false",
            "- Profitability proof: false",
            "- Paper, live, and order-entry authorization: false",
            "",
            f"Dependency lock SHA-256: `{receipt['dependency_lock_sha256']}`",
            f"Source manifest SHA-256: `{receipt['source_manifest_sha256']}`",
        ]
    )
    for forbidden in ("READY", "SIGNIFICANT", "ACCEPT STRATEGY"):
        if forbidden in markdown:
            _fail("renderer", f"neutral token violation:{forbidden}")
    return markdown
