from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from pathlib import PureWindowsPath
import time
from typing import Any, Callable
import unicodedata

from .portfolio_admission import verify_internal_backtest_admission
from .backtest_return_quality import (
    BACKTEST_RETURN_QUALITY_V2_SCHEMA_VERSION,
    BACKTEST_RETURN_QUALITY_V3_SCHEMA_VERSION,
    PORTFOLIO_RESEARCH_SOURCE_ARTIFACT_FAMILY,
    PORTFOLIO_RETURN_QUALITY_SOURCE_IDENTITY_SCHEMA_VERSION,
    PORTFOLIO_RETURN_QUALITY_SOURCE_IDENTITY_V2_SCHEMA_VERSION,
    build_backtest_return_quality_projection,
)
from .portfolio_forward import load_active_portfolio_candidate
from .portfolio_forward_scheduler import (
    DEFAULT_SCHEDULER_STATUS_FILE,
    load_forward_scheduler_status,
)
from .portfolio_statistical_audit import (
    PORTFOLIO_STATISTICAL_AUDIT_SCHEMA_VERSION,
    statistical_audit_content as _statistical_audit_content,
    verify_portfolio_statistical_audit_semantics,
)
from .portfolio_forward_performance import (
    PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION,
)
from .portfolio_forward_statistical_audit import (
    PORTFOLIO_FORWARD_DECISION_POLICY,
    PORTFOLIO_FORWARD_DECISION_WINDOW_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_RISK_ACCEPTANCE_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_SERIES_EVIDENCE_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_STATISTICAL_CONTRACT_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_STATISTICAL_AUDIT_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_STATISTICAL_AUDIT_V2_SCHEMA_VERSION,
    first_joint_maturity_prefix,
    forward_statistical_audit_content,
    forward_statistical_audit_v2_content,
)
from .portfolio_evidence_bundle import expand_portfolio_evidence_bundle
from .portfolio_experiment import verify_experiment_completion_receipt
from .strict_json_artifact import parse_strict_json_object
from .execution_authority import (
    EXECUTION_AUTHORITY_FIELDS,
    EXECUTION_AUTHORITY_FIELD_KEYS,
    authority_violations,
)


PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION = "portfolio-internal-backtest-pack-v2"
PORTFOLIO_INTERNAL_BACKTEST_PACK_V3_SCHEMA_VERSION = "portfolio-internal-backtest-pack-v3"
PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION = "portfolio-internal-backtest-pack-v4"
PORTFOLIO_INTERNAL_BACKTEST_PACK_V5_SCHEMA_VERSION = "portfolio-internal-backtest-pack-v5"
PORTFOLIO_INTERNAL_BACKTEST_PACK_V6_SCHEMA_VERSION = "portfolio-internal-backtest-pack-v6"
CURRENT_PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION = (
    PORTFOLIO_INTERNAL_BACKTEST_PACK_V6_SCHEMA_VERSION
)
SUPPORTED_PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSIONS = {
    PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION,
    PORTFOLIO_INTERNAL_BACKTEST_PACK_V3_SCHEMA_VERSION,
    PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
    PORTFOLIO_INTERNAL_BACKTEST_PACK_V5_SCHEMA_VERSION,
    PORTFOLIO_INTERNAL_BACKTEST_PACK_V6_SCHEMA_VERSION,
}
PORTFOLIO_INTERNAL_FORWARD_EVIDENCE_SCHEMA_VERSION = "portfolio-internal-forward-evidence-v1"
PORTFOLIO_INTERNAL_FORWARD_EVIDENCE_V2_SCHEMA_VERSION = (
    "portfolio-internal-forward-evidence-v2"
)
CURRENT_PORTFOLIO_INTERNAL_FORWARD_EVIDENCE_SCHEMA_VERSION = (
    PORTFOLIO_INTERNAL_FORWARD_EVIDENCE_V2_SCHEMA_VERSION
)
_PORTFOLIO_FORWARD_V2_MAX_SAFE_INTEGER = 9_007_199_254_740_991
_PORTFOLIO_FORWARD_V2_COPIED_CONTRACT_FIELDS = (
    "method",
    "periods_per_year",
    "resample_count",
    "block_length",
    "confidence_level",
    "required_positive_probability",
    "required_selection_adjusted_probability",
    "selection_adjustment",
    "selection_trial_count",
)
_PORTFOLIO_FORWARD_V2_STAGE_CHECK_FIELDS = (
    "minimum_observations",
    "observed_compound_excess_positive",
    "observed_information_ratio_positive",
    "bootstrap_positive_probability",
    "bootstrap_information_ratio_probability",
    "selection_adjusted_probability",
    "selection_adjusted_information_ratio_probability",
    "compound_excess_interval_lower_positive",
    "information_ratio_interval_lower_positive",
)
PORTFOLIO_RETURN_QUALITY_SOURCE_EVIDENCE_SCHEMA_VERSION = (
    "portfolio-return-quality-source-evidence-v1"
)
PORTFOLIO_BACKTEST_RESULT_EVIDENCE_SCHEMA_VERSION = (
    "portfolio-backtest-result-evidence-v1"
)
PORTFOLIO_BACKTEST_RESULT_EVIDENCE_COLLECTION_SCHEMA_VERSION = (
    "portfolio-backtest-result-evidence-collection-v1"
)
PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_SCHEMA_VERSION = (
    "portfolio-research-source-document-v1"
)
MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES = 256 * 1024 * 1024
MAX_PORTFOLIO_STATISTICAL_AUDIT_BYTES = 16 * 1024 * 1024
MAX_PORTFOLIO_COMPACT_CANDIDATE_BYTES = 1 * 1024 * 1024
MAX_PORTFOLIO_COMPACT_REGISTRY_BYTES = 4 * 1024 * 1024
MAX_PORTFOLIO_INTERNAL_BACKTEST_PACK_BYTES = 32 * 1024 * 1024
MAX_PORTFOLIO_COST_STRESS_SCENARIOS = 64
MAX_PORTFOLIO_SOURCE_BLOCKERS = 128
PORTFOLIO_INTERNAL_BACKTEST_BUNDLE_BUILD_SCHEMA_VERSION = (
    "portfolio-internal-backtest-bundle-build-v1"
)
PORTFOLIO_RETURN_QUALITY_SOURCE_MANIFEST_SCHEMA_VERSION = (
    "portfolio-return-quality-source-manifest-v1"
)
PORTFOLIO_BACKTEST_RESULT_DIGEST_COLLECTION_SCHEMA_VERSION = (
    "portfolio-backtest-result-digest-collection-v1"
)
_DETACHED_RESEARCH_ROLE = "RESEARCH_REPORT"
_DETACHED_STATISTICAL_ROLE = "STATISTICAL_AUDIT"
_WINDOWS_FORBIDDEN_BASENAME_CHARACTERS = frozenset('<>:"/\\|?*')
_WINDOWS_RESERVED_BASENAMES = {
    "aux",
    "clock$",
    "con",
    "conin$",
    "conout$",
    "nul",
    "prn",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def _read_bounded_json_artifact(
    path: Path,
    *,
    maximum_bytes: int,
) -> tuple[dict[str, Any], bytes]:
    size = path.stat().st_size
    if size < 0 or size > maximum_bytes:
        raise ValueError("JSON artifact size limit exceeded")
    with path.open("rb") as handle:
        raw = handle.read(maximum_bytes + 1)
    if len(raw) != size or len(raw) > maximum_bytes:
        raise ValueError("JSON artifact size limit exceeded")
    payload = _strict_json_object(raw)
    return payload, raw


def artifact_record(path: Path) -> dict[str, Any]:
    return {
        "file": path.name,
        "file_sha256": file_sha256(path),
        "size": path.stat().st_size,
    }


def _verify_hash_field(payload: dict[str, Any], field: str) -> bool:
    expected = str(payload.get(field) or "")
    content = dict(payload)
    content.pop(field, None)
    return bool(expected) and canonical_hash(content) == expected


def research_batch_hash(report: dict[str, Any]) -> str:
    manifest = dict(report.get("dataset_manifest") or {})
    content = {
        "spec_hash": report.get("spec_hash", ""),
        "dataset_hash": manifest.get("data_hash", ""),
        "validation_run_hash": (report.get("validation") or {}).get("run_hash", ""),
        "validation_benchmark_run_hash": (
            report.get("validation_benchmark") or {}
        ).get("benchmark_run_hash", ""),
        "test_run_hash": (report.get("test") or {}).get("run_hash", ""),
        "test_benchmark_run_hash": (
            report.get("test_benchmark") or {}
        ).get("benchmark_run_hash", ""),
        "full_run_hash": (report.get("full") or {}).get("run_hash", ""),
        "causal_audit": report.get("causal_audit") or {},
        "correlation_matrix_hash": (report.get("correlation_matrix") or {}).get("matrix_hash", ""),
        "cost_stress_run_hashes": [
            item.get("run_hash", "") for item in list(report.get("cost_stress") or [])
        ],
        "execution_rehearsal_hash": (report.get("execution_rehearsal") or {}).get("report_hash", ""),
        "development_checks": report.get("development_checks") or {},
        "mechanism_status": report.get("mechanism_status", ""),
        "research_protocol_hash": (report.get("spec") or {}).get("research_protocol_hash", ""),
        "experiment_binding_hash": (report.get("experiment_governance") or {}).get("binding_hash", ""),
        "universe_contract_hash": (report.get("universe_contract") or {}).get("contract_hash", ""),
        "provider_governance_contract_hash": (
            report.get("provider_governance") or {}
        ).get("contract_hash", ""),
        "temporal_exposure_audit_hash": (report.get("temporal_exposure_audit") or {}).get("audit_hash", ""),
        "backtest_admission_hash": (report.get("backtest_admission") or {}).get("admission_hash", ""),
    }
    evidence_bundle = report.get("evidence_bundle")
    if isinstance(evidence_bundle, dict):
        content["evidence_bundle_hash"] = str(evidence_bundle.get("bundle_hash") or "")
    return canonical_hash(content)


_RETURN_QUALITY_RESEARCH_SOURCE_FIELDS = (
    "schema_version",
    "batch_run_hash",
    "spec_hash",
    "spec",
    "dataset_manifest",
    "frozen_candidate",
    "mechanism_status",
    "fresh_holdout_required",
    "forward_observation_required",
    "validation",
    "validation_benchmark",
    "validation_comparison",
    "test",
    "test_benchmark",
    "test_comparison",
    "full",
    "cost_stress",
    "development_checks",
    "causal_audit",
    "correlation_matrix",
    "execution_rehearsal",
    "experiment_governance",
    "universe_contract",
    "provider_governance",
    "temporal_exposure_audit",
    "backtest_admission",
    "evidence_bundle",
    "research_only",
    "paper_authorized",
    "live_order_allowed",
)
_RETURN_QUALITY_STATISTICAL_SOURCE_FIELDS = (
    "schema_version",
    "status",
    "conclusion",
    "blockers",
    "input_binding",
    "config",
    "stages",
    "checks",
    "generated_at",
    "audit_hash",
    "research_only",
    "paper_authorized",
    "live_order_allowed",
)
_RETURN_QUALITY_CANDIDATE_SOURCE_FIELDS = (
    "candidate_id",
    "candidate_hash",
    "research_report_hash",
    "spec",
    "spec_hash",
    "dataset_hash",
    "implementation",
    "research_governance",
    "research_only",
    "paper_authorized",
    "live_order_allowed",
)
_RETURN_QUALITY_REGISTRY_SOURCE_FIELDS = (
    "schema_version",
    "status",
    "candidate_file",
    "candidate_file_sha256",
    "candidate_hash",
    "dataset_hash",
    "experiment_completion_receipt_hash",
    "experiment_completion_receipt",
    "selection_policy",
    "research_only",
    "paper_authorized",
    "live_order_allowed",
    "registry_hash",
)
_RETURN_QUALITY_ARTIFACT_SOURCE_FIELDS = (
    "file",
    "file_sha256",
    "size",
)


def _whitelist_source(payload: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    projected = {field: deepcopy(payload.get(field)) for field in fields}
    for field in ("paper_authorized", "live_order_allowed"):
        if field in projected and projected[field] is None:
            projected[field] = False
    return projected


def _shallow_whitelist_source(
    payload: dict[str, Any],
    fields: tuple[str, ...],
) -> dict[str, Any]:
    """Borrow selected values for transient semantic checks without cloning trees."""

    projected = {field: payload.get(field) for field in fields}
    for field in ("paper_authorized", "live_order_allowed"):
        if field in projected and projected[field] is None:
            projected[field] = False
    return projected


def _is_sha256(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def _research_source_document(raw_text: str) -> dict[str, Any]:
    raw = raw_text.encode("utf-8")
    content = {
        "schema_version": PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_SCHEMA_VERSION,
        "encoding": "UTF-8_JSON_OBJECT_EXACT_BYTES_V1",
        "byte_length": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "payload": raw_text,
        "internal_verification_only": True,
        "public_projection_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {**content, "document_hash": canonical_hash(content)}


def _verify_research_source_document(document: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if document.get("schema_version") != PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_SCHEMA_VERSION:
        blockers.append("research_source_document_schema_invalid")
    if document.get("encoding") != "UTF-8_JSON_OBJECT_EXACT_BYTES_V1":
        blockers.append("research_source_document_encoding_invalid")
    if document.get("internal_verification_only") is not True:
        blockers.append("research_source_document_scope_invalid")
    if document.get("public_projection_allowed") is not False:
        blockers.append("research_source_document_public_projection_not_blocked")
    payload = document.get("payload")
    if not isinstance(payload, str):
        blockers.append("research_source_document_payload_invalid")
        raw = b""
    else:
        raw = payload.encode("utf-8")
    if len(raw) > MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES:
        blockers.append("research_source_document_size_limit_exceeded")
    if type(document.get("byte_length")) is not int or document.get("byte_length") != len(raw):
        blockers.append("research_source_document_byte_length_mismatch")
    computed_sha = hashlib.sha256(raw).hexdigest() if raw else ""
    if not computed_sha or str(document.get("sha256") or "") != computed_sha:
        blockers.append("research_source_document_sha256_invalid")
    content = dict(document)
    declared_hash = str(content.pop("document_hash", "") or "")
    if not declared_hash or canonical_hash(content) != declared_hash:
        blockers.append("research_source_document_hash_invalid")
    parsed: dict[str, Any] = {}
    if raw and len(raw) <= MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES:
        try:
            candidate = json.loads(raw.decode("utf-8"))
            if isinstance(candidate, dict):
                parsed = candidate
                if authority_violations(parsed):
                    blockers.append(
                        "research_source_document_parsed_contains_execution_authority"
                    )
            else:
                blockers.append("research_source_document_json_object_required")
        except (UnicodeDecodeError, json.JSONDecodeError):
            blockers.append("research_source_document_json_invalid")
    if authority_violations(document):
        blockers.append("research_source_document_contains_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "parsed": parsed,
        "sha256": computed_sha,
        "byte_length": len(raw),
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _return_quality_source_identity(
    *,
    candidate: dict[str, Any],
    research: dict[str, Any],
    statistical: dict[str, Any],
    research_artifact: dict[str, Any],
    registry: dict[str, Any],
    research_document: dict[str, Any],
    result_evidence: dict[str, Any],
) -> dict[str, Any]:
    spec = dict(research.get("spec") or {})
    candidate_implementation = dict(candidate.get("implementation") or {})
    binding = dict(statistical.get("input_binding") or {})
    content = {
        "schema_version": PORTFOLIO_RETURN_QUALITY_SOURCE_IDENTITY_SCHEMA_VERSION,
        "source_artifact_family": PORTFOLIO_RESEARCH_SOURCE_ARTIFACT_FAMILY,
        "strategy_schema7_preregistration_status": "NOT_APPLICABLE",
        "candidate_hash": str(candidate.get("candidate_hash") or ""),
        "candidate_research_report_hash": str(candidate.get("research_report_hash") or ""),
        "candidate_spec_hash": str(candidate.get("spec_hash") or ""),
        "research_batch_run_hash": str(research.get("batch_run_hash") or ""),
        "research_spec_hash": str(research.get("spec_hash") or ""),
        "research_generation": str(spec.get("research_generation") or ""),
        "research_protocol_hash": str(spec.get("research_protocol_hash") or ""),
        "implementation_fingerprint": str(candidate_implementation.get("fingerprint") or ""),
        "research_file_sha256": str(research_artifact.get("file_sha256") or ""),
        "statistical_audit_schema_version": str(statistical.get("schema_version") or ""),
        "statistical_audit_hash": str(statistical.get("audit_hash") or ""),
        "statistical_input_binding_hash": str(binding.get("binding_hash") or ""),
        "research_source_document_sha256": str(research_document.get("sha256") or ""),
        "backtest_result_evidence_hash": str(result_evidence.get("collection_hash") or ""),
        "experiment_completion_receipt_hash": str(
            registry.get("experiment_completion_receipt_hash") or ""
        ),
        "active_candidate_registry_hash": str(registry.get("registry_hash") or ""),
        "external_anchor_verified": False,
        "cryptographic_authenticity_proven": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {**content, "identity_hash": canonical_hash(content)}


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _equity_curve_metrics(stage: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    initial_cash = _finite_number(stage.get("initial_cash"))
    if initial_cash is None or initial_cash <= 0:
        blockers.append("initial_cash_invalid")
    curve = list(stage.get("equity_curve") or [])
    if not curve:
        return {
            "status": "BLOCK",
            "blockers": ["equity_curve_missing"],
        }
    equities: list[float] = []
    dates: list[str] = []
    for index, item in enumerate(curve):
        row = item if isinstance(item, dict) else {}
        date = str(row.get("date") or "")
        equity = _finite_number(row.get("equity"))
        if not date:
            blockers.append(f"equity_date_missing:{index}")
        if equity is None or equity <= 0:
            blockers.append(f"equity_value_invalid:{index}")
            continue
        dates.append(date)
        equities.append(equity)
    if len(equities) != len(curve):
        return {
            "status": "BLOCK",
            "blockers": list(dict.fromkeys(blockers)),
        }
    if dates != sorted(dates) or len(set(dates)) != len(dates):
        blockers.append("equity_dates_invalid")
    if initial_cash is None or initial_cash <= 0:
        return {
            "status": "BLOCK",
            "blockers": list(dict.fromkeys(blockers)),
        }
    total_return_pct = (equities[-1] / initial_cash - 1.0) * 100.0
    peak = initial_cash
    max_drawdown_pct = 0.0
    for equity in equities:
        peak = max(peak, equity)
        max_drawdown_pct = max(max_drawdown_pct, (peak - equity) / peak * 100.0)
    evaluation_window = dict(stage.get("evaluation_window") or {})
    evaluated_rows = evaluation_window.get("evaluated_rows")
    if type(evaluated_rows) is not int or evaluated_rows != len(curve):
        blockers.append("evaluation_window_row_count_mismatch")
    if str(evaluation_window.get("start") or "") != dates[0]:
        blockers.append("evaluation_window_start_mismatch")
    if str(evaluation_window.get("end") or "") != dates[-1]:
        blockers.append("evaluation_window_end_mismatch")
    declared_final_equity = _finite_number(stage.get("final_equity"))
    if declared_final_equity is not None and abs(declared_final_equity - equities[-1]) > 0.011:
        blockers.append("final_equity_mismatch")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "total_return_pct": round(total_return_pct, 4),
        "max_drawdown_pct": round(max_drawdown_pct, 4),
        "final_equity": round(equities[-1], 2),
        "observation_count": len(curve),
        "first_date": dates[0],
        "last_date": dates[-1],
    }


def _project_backtest_result_evidence(
    source: dict[str, Any],
    *,
    result_kind: str,
    result_id: str,
) -> dict[str, Any]:
    content = {
        "schema_version": PORTFOLIO_BACKTEST_RESULT_EVIDENCE_SCHEMA_VERSION,
        "result_kind": result_kind,
        "result_id": result_id,
        "source_result": deepcopy(source),
        "source_result_hash": canonical_hash(source),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {**content, "result_evidence_hash": canonical_hash(content)}


def _project_backtest_result_evidence_collection(
    research: dict[str, Any],
) -> dict[str, Any]:
    stages = {
        stage_name: _project_backtest_result_evidence(
            dict(research.get(stage_name) or {}),
            result_kind="STRATEGY_STAGE",
            result_id=stage_name.upper(),
        )
        for stage_name in ("validation", "test")
    }
    benchmarks = {
        stage_name: _project_backtest_result_evidence(
            dict(research.get(f"{stage_name}_benchmark") or {}),
            result_kind="BENCHMARK_STAGE",
            result_id=stage_name.upper(),
        )
        for stage_name in ("validation", "test")
    }
    cost_stress = [
        _project_backtest_result_evidence(
            dict(scenario or {}),
            result_kind="COST_STRESS",
            result_id=str(dict(scenario or {}).get("label") or f"SCENARIO_{index + 1}"),
        )
        for index, scenario in enumerate(list(research.get("cost_stress") or []))
    ]
    content = {
        "schema_version": PORTFOLIO_BACKTEST_RESULT_EVIDENCE_COLLECTION_SCHEMA_VERSION,
        "stages": stages,
        "benchmarks": benchmarks,
        "cost_stress": cost_stress,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {**content, "collection_hash": canonical_hash(content)}


def _verify_backtest_result_evidence(
    evidence: dict[str, Any],
    *,
    expected_source: dict[str, Any],
    result_kind: str,
    result_id: str,
) -> list[str]:
    blockers: list[str] = []
    expected = _project_backtest_result_evidence(
        expected_source,
        result_kind=result_kind,
        result_id=result_id,
    )
    if canonical_hash(evidence) != canonical_hash(expected):
        blockers.append("result_evidence_source_mismatch")
    content = dict(evidence)
    declared_hash = str(content.pop("result_evidence_hash", "") or "")
    if not declared_hash or canonical_hash(content) != declared_hash:
        blockers.append("result_evidence_hash_invalid")
    if evidence.get("schema_version") != PORTFOLIO_BACKTEST_RESULT_EVIDENCE_SCHEMA_VERSION:
        blockers.append("result_evidence_schema_invalid")
    if evidence.get("result_kind") != result_kind or evidence.get("result_id") != result_id:
        blockers.append("result_evidence_identity_mismatch")
    if str(evidence.get("source_result_hash") or "") != canonical_hash(expected_source):
        blockers.append("result_evidence_result_hash_invalid")
    if authority_violations(evidence):
        blockers.append("result_evidence_contains_execution_authority")
    return list(dict.fromkeys(blockers))


def _verify_backtest_result_evidence_collection(
    collection: dict[str, Any],
    research: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    expected = _project_backtest_result_evidence_collection(research)
    if canonical_hash(collection) != canonical_hash(expected):
        blockers.append("result_evidence_collection_source_mismatch")
    content = dict(collection)
    declared_hash = str(content.pop("collection_hash", "") or "")
    if not declared_hash or canonical_hash(content) != declared_hash:
        blockers.append("result_evidence_collection_hash_invalid")
    if collection.get("schema_version") != PORTFOLIO_BACKTEST_RESULT_EVIDENCE_COLLECTION_SCHEMA_VERSION:
        blockers.append("result_evidence_collection_schema_invalid")

    for stage_name in ("validation", "test"):
        source_stage = dict(research.get(stage_name) or {})
        stage_evidence = dict(dict(collection.get("stages") or {}).get(stage_name) or {})
        blockers.extend(
            f"{stage_name}:{item}"
            for item in _verify_backtest_result_evidence(
                stage_evidence,
                expected_source=source_stage,
                result_kind="STRATEGY_STAGE",
                result_id=stage_name.upper(),
            )
        )
        benchmark = dict(research.get(f"{stage_name}_benchmark") or {})
        benchmark_evidence = dict(
            dict(collection.get("benchmarks") or {}).get(stage_name) or {}
        )
        blockers.extend(
            f"{stage_name}_benchmark:{item}"
            for item in _verify_backtest_result_evidence(
                benchmark_evidence,
                expected_source=benchmark,
                result_kind="BENCHMARK_STAGE",
                result_id=stage_name.upper(),
            )
        )

    declared_cost = list(collection.get("cost_stress") or [])
    source_cost = list(research.get("cost_stress") or [])
    if len(declared_cost) != len(source_cost):
        blockers.append("cost_stress_result_evidence_count_mismatch")
    for index, raw_scenario in enumerate(source_cost):
        scenario = dict(raw_scenario or {})
        label = str(scenario.get("label") or f"SCENARIO_{index + 1}")
        scenario_evidence = dict(declared_cost[index] or {}) if index < len(declared_cost) else {}
        blockers.extend(
            f"cost_stress:{label}:{item}"
            for item in _verify_backtest_result_evidence(
                scenario_evidence,
                expected_source=scenario,
                result_kind="COST_STRESS",
                result_id=label,
            )
        )
    if authority_violations(collection):
        blockers.append("result_evidence_collection_contains_execution_authority")
    return list(dict.fromkeys(blockers))


def _v5_generated_result_evidence_blockers(
    research: dict[str, Any],
) -> list[str]:
    """Reproduce generated v4 result-evidence authority blockers without copies."""

    blockers: list[str] = []
    collection_contains_authority = False
    for stage_name in ("validation", "test"):
        stage = dict(research.get(stage_name) or {})
        if authority_violations(stage):
            blockers.append(f"{stage_name}:result_evidence_contains_execution_authority")
            collection_contains_authority = True
        benchmark = dict(research.get(f"{stage_name}_benchmark") or {})
        if authority_violations(benchmark):
            blockers.append(
                f"{stage_name}_benchmark:result_evidence_contains_execution_authority"
            )
            collection_contains_authority = True
    for index, raw_scenario in enumerate(list(research.get("cost_stress") or [])):
        scenario = dict(raw_scenario or {})
        if authority_violations(scenario):
            label = str(scenario.get("label") or f"SCENARIO_{index + 1}")
            blockers.append(
                f"cost_stress:{label}:result_evidence_contains_execution_authority"
            )
            collection_contains_authority = True
    if collection_contains_authority:
        blockers.append("result_evidence_collection_contains_execution_authority")
    return blockers


def _return_quality_source_semantics(
    source: dict[str, Any],
    *,
    research_document_verification: dict[str, Any] | None = None,
    expected_identity_override: dict[str, Any] | None = None,
    skip_generated_result_evidence_verification: bool = False,
    required_identity_hashes_override: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    candidate = dict(source.get("candidate") or {})
    research = dict(source.get("research") or {})
    statistical = dict(source.get("statistical") or {})
    research_artifact = dict(source.get("research_artifact") or {})
    registry = dict(source.get("active_candidate_registry") or {})
    receipt = dict(registry.get("experiment_completion_receipt") or {})
    research_document = dict(source.get("research_source_document") or {})
    result_evidence = dict(source.get("backtest_result_evidence") or {})
    identity = dict(source.get("source_identity") or {})
    blockers: list[str] = []

    if source.get("schema_version") != PORTFOLIO_RETURN_QUALITY_SOURCE_EVIDENCE_SCHEMA_VERSION:
        blockers.append("return_quality_source_schema_invalid")
    if source.get("research_only") is not True:
        blockers.append("return_quality_source_not_research_only")
    if authority_violations(source):
        blockers.append("return_quality_source_contains_execution_authority")

    verification_scope = dict(source.get("verification_scope") or {})
    expected_scope = {
        "semantic_consistency_with_same_embedded_artifact_identity": True,
        "external_anchor_verified": False,
        "cryptographic_authenticity_proven": False,
        "profitability_proven": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    if verification_scope != expected_scope:
        blockers.append("return_quality_source_verification_scope_invalid")

    document_verification = (
        research_document_verification
        if research_document_verification is not None
        else _verify_research_source_document(research_document)
    )
    if document_verification.get("status") != "PASS":
        blockers.extend(
            f"return_quality_source_document:{item}"
            for item in document_verification.get("blockers") or ["verification_blocked"]
        )
    parsed_research = dict(document_verification.get("parsed") or {})
    parsed_research_projection = (
        _shallow_whitelist_source(
            parsed_research,
            _RETURN_QUALITY_RESEARCH_SOURCE_FIELDS,
        )
        if research_document_verification is not None
        else _whitelist_source(
            parsed_research,
            _RETURN_QUALITY_RESEARCH_SOURCE_FIELDS,
        )
    )
    if canonical_hash(parsed_research_projection) != canonical_hash(research):
        blockers.append("return_quality_source_research_document_projection_mismatch")
    document_sha = str(document_verification.get("sha256") or "")
    if document_sha != str(research_artifact.get("file_sha256") or ""):
        blockers.append("return_quality_source_document_artifact_hash_mismatch")
    if int(document_verification.get("byte_length") or 0) != int(
        research_artifact.get("size") or 0
    ):
        blockers.append("return_quality_source_document_artifact_size_mismatch")

    registry_content = dict(registry)
    declared_registry_hash = str(registry_content.pop("registry_hash", "") or "")
    if not declared_registry_hash or canonical_hash(registry_content) != declared_registry_hash:
        blockers.append("return_quality_source_active_registry_hash_invalid")
    receipt_verification = verify_experiment_completion_receipt(receipt)
    if receipt_verification.get("status") != "PASS":
        blockers.extend(
            f"return_quality_source_completion_receipt:{item}"
            for item in receipt_verification.get("blockers") or ["verification_blocked"]
        )
    if str(registry.get("experiment_completion_receipt_hash") or "") != str(
        receipt.get("receipt_hash") or ""
    ):
        blockers.append("return_quality_source_registry_receipt_hash_mismatch")
    if str(registry.get("candidate_hash") or "") != str(candidate.get("candidate_hash") or ""):
        blockers.append("return_quality_source_registry_candidate_hash_mismatch")
    if str(registry.get("dataset_hash") or "") != str(candidate.get("dataset_hash") or ""):
        blockers.append("return_quality_source_registry_dataset_hash_mismatch")
    for field, expected in (
        ("candidate_hash", candidate.get("candidate_hash")),
        ("batch_run_hash", research.get("batch_run_hash")),
        ("dataset_hash", dict(research.get("dataset_manifest") or {}).get("data_hash")),
        ("report_file", research_artifact.get("file")),
        ("report_file_sha256", document_sha),
    ):
        if str(receipt.get(field) or "") != str(expected or ""):
            blockers.append(f"return_quality_source_completion_receipt_binding_mismatch:{field}")

    expected_identity = (
        expected_identity_override
        if expected_identity_override is not None
        else _return_quality_source_identity(
            candidate=candidate,
            research=research,
            statistical=statistical,
            research_artifact=research_artifact,
            registry=registry,
            research_document=research_document,
            result_evidence=result_evidence,
        )
    )
    if canonical_hash(identity) != canonical_hash(expected_identity):
        blockers.append("return_quality_source_identity_mismatch")
    identity_content = dict(identity)
    declared_identity_hash = str(identity_content.pop("identity_hash", "") or "")
    if not declared_identity_hash or canonical_hash(identity_content) != declared_identity_hash:
        blockers.append("return_quality_source_identity_hash_invalid")
    if identity.get("source_artifact_family") != PORTFOLIO_RESEARCH_SOURCE_ARTIFACT_FAMILY:
        blockers.append("return_quality_source_artifact_family_invalid")
    if identity.get("strategy_schema7_preregistration_status") != "NOT_APPLICABLE":
        blockers.append("return_quality_source_strategy_schema7_scope_invalid")
    spec = dict(research.get("spec") or {})
    if "hypothesis_preregistration" in spec or "hypothesis_preregistration_hash" in spec:
        blockers.append("return_quality_source_strategy_schema7_claim_forbidden")

    candidate_spec = dict(candidate.get("spec") or {})
    research_spec = dict(research.get("spec") or {})
    if not candidate_spec or canonical_hash(candidate_spec) != str(candidate.get("spec_hash") or ""):
        blockers.append("return_quality_source_candidate_spec_hash_invalid")
    if not research_spec or canonical_hash(research_spec) != str(research.get("spec_hash") or ""):
        blockers.append("return_quality_source_research_spec_hash_invalid")
    if canonical_hash(candidate_spec) != canonical_hash(research_spec):
        blockers.append("return_quality_source_candidate_research_spec_mismatch")
    if str(candidate.get("research_report_hash") or "") != str(research.get("batch_run_hash") or ""):
        blockers.append("return_quality_source_candidate_batch_mismatch")
    if str(candidate.get("dataset_hash") or "") != str(
        dict(research.get("dataset_manifest") or {}).get("data_hash") or ""
    ):
        blockers.append("return_quality_source_candidate_dataset_mismatch")
    if str(dict(research.get("frozen_candidate") or {}).get("candidate_hash") or "") != str(
        candidate.get("candidate_hash") or ""
    ):
        blockers.append("return_quality_source_frozen_candidate_mismatch")
    if research_batch_hash(research) != str(research.get("batch_run_hash") or ""):
        blockers.append("return_quality_source_research_batch_hash_invalid")

    result_evidence_blockers = (
        _v5_generated_result_evidence_blockers(research)
        if skip_generated_result_evidence_verification
        else _verify_backtest_result_evidence_collection(
            result_evidence,
            research,
        )
    )
    blockers.extend(
        f"return_quality_source_result_evidence:{item}"
        for item in result_evidence_blockers
    )

    for stage_name in ("validation", "test"):
        stage = dict(research.get(stage_name) or {})
        run_spec = dict(stage.get("run_spec") or {})
        if not run_spec or canonical_hash(run_spec) != str(stage.get("run_hash") or ""):
            blockers.append(f"return_quality_source_{stage_name}_run_hash_invalid")
        computed = _equity_curve_metrics(stage)
        blockers.extend(
            f"return_quality_source_{stage_name}_{item}"
            for item in computed.get("blockers") or []
        )
        declared_return = stage.get("total_return_pct")
        if (
            computed.get("total_return_pct") is not None
            and (
                isinstance(declared_return, bool)
                or not isinstance(declared_return, (int, float))
                or abs(float(declared_return) - float(computed["total_return_pct"])) > 0.00011
            )
        ):
            blockers.append(f"return_quality_source_{stage_name}_return_mismatch")
        declared_drawdown = stage.get("max_drawdown_pct")
        if (
            computed.get("max_drawdown_pct") is not None
            and (
                isinstance(declared_drawdown, bool)
                or not isinstance(declared_drawdown, (int, float))
                or abs(float(declared_drawdown) - float(computed["max_drawdown_pct"])) > 0.00011
            )
        ):
            blockers.append(f"return_quality_source_{stage_name}_drawdown_mismatch")
        benchmark = dict(research.get(f"{stage_name}_benchmark") or {})
        benchmark_content = dict(benchmark)
        benchmark_hash = str(benchmark_content.pop("benchmark_run_hash", "") or "")
        if not benchmark_hash or canonical_hash(benchmark_content) != benchmark_hash:
            blockers.append(f"return_quality_source_{stage_name}_benchmark_hash_invalid")
        benchmark_metrics = _equity_curve_metrics(benchmark)
        blockers.extend(
            f"return_quality_source_{stage_name}_benchmark_{item}"
            for item in benchmark_metrics.get("blockers") or []
        )
        for field in ("total_return_pct", "max_drawdown_pct"):
            declared = _finite_number(benchmark.get(field))
            computed_value = _finite_number(benchmark_metrics.get(field))
            if declared is None or computed_value is None or abs(declared - computed_value) > 0.00011:
                blockers.append(
                    f"return_quality_source_{stage_name}_benchmark_{field}_mismatch"
                )
        comparison = dict(research.get(f"{stage_name}_comparison") or {})
        strategy_return = _finite_number(computed.get("total_return_pct"))
        benchmark_return = _finite_number(benchmark_metrics.get("total_return_pct"))
        reported_excess = _finite_number(comparison.get("excess_return_pct"))
        if (
            strategy_return is None
            or benchmark_return is None
            or reported_excess is None
            or abs(reported_excess - (strategy_return - benchmark_return)) > 0.00011
        ):
            blockers.append(f"return_quality_source_{stage_name}_comparison_excess_mismatch")

    seen_cost_labels: set[str] = set()
    for index, raw_scenario in enumerate(list(research.get("cost_stress") or [])):
        scenario = dict(raw_scenario or {})
        label = str(scenario.get("label") or f"SCENARIO_{index + 1}")
        if label in seen_cost_labels:
            blockers.append(f"return_quality_source_cost_stress_duplicate:{label}")
        seen_cost_labels.add(label)
        run_spec = dict(scenario.get("run_spec") or {})
        if not run_spec or canonical_hash(run_spec) != str(scenario.get("run_hash") or ""):
            blockers.append(f"return_quality_source_cost_stress_run_hash_invalid:{label}")
        metrics = _equity_curve_metrics(scenario)
        blockers.extend(
            f"return_quality_source_cost_stress_{label}_{item}"
            for item in metrics.get("blockers") or []
        )
        for field in ("total_return_pct", "max_drawdown_pct"):
            declared = _finite_number(scenario.get(field))
            computed_value = _finite_number(metrics.get(field))
            if declared is None or computed_value is None or abs(declared - computed_value) > 0.00011:
                blockers.append(f"return_quality_source_cost_stress_{label}_{field}_mismatch")
        if scenario.get("ok") is not True:
            blockers.append(f"return_quality_source_cost_stress_not_ok:{label}")

    binding = dict(statistical.get("input_binding") or {})
    binding_content = dict(binding)
    binding_hash = str(binding_content.pop("binding_hash", "") or "")
    if not binding_hash or canonical_hash(binding_content) != binding_hash:
        blockers.append("return_quality_source_statistical_binding_hash_invalid")
    for field, expected in (
        ("candidate_hash", candidate.get("candidate_hash")),
        ("batch_run_hash", research.get("batch_run_hash")),
        ("dataset_hash", dict(research.get("dataset_manifest") or {}).get("data_hash")),
        ("spec_hash", research.get("spec_hash")),
        ("validation_run_hash", dict(research.get("validation") or {}).get("run_hash")),
        (
            "validation_benchmark_run_hash",
            dict(research.get("validation_benchmark") or {}).get("benchmark_run_hash"),
        ),
        ("test_run_hash", dict(research.get("test") or {}).get("run_hash")),
        (
            "test_benchmark_run_hash",
            dict(research.get("test_benchmark") or {}).get("benchmark_run_hash"),
        ),
    ):
        if str(binding.get(field) or "") != str(expected or ""):
            blockers.append(f"return_quality_source_statistical_binding_mismatch:{field}")
    if statistical.get("schema_version") != PORTFOLIO_STATISTICAL_AUDIT_SCHEMA_VERSION:
        blockers.append("return_quality_source_statistical_schema_invalid")
    if canonical_hash(statistical_audit_content(statistical)) != str(
        statistical.get("audit_hash") or ""
    ):
        blockers.append("return_quality_source_statistical_audit_hash_invalid")
    for stage_name in ("validation", "test"):
        stage = dict(dict(statistical.get("stages") or {}).get(stage_name) or {})
        if not _forward_stage_hash_valid(stage):
            blockers.append(f"return_quality_source_statistical_stage_hash_invalid:{stage_name}")
    statistical_semantics = verify_portfolio_statistical_audit_semantics(
        statistical,
        research,
    )
    if statistical_semantics.get("status") != "PASS":
        blockers.extend(
            f"return_quality_source_statistical_semantics:{item}"
            for item in statistical_semantics.get("blockers") or ["verification_blocked"]
        )

    required_identity_hashes = required_identity_hashes_override or (
        "candidate_hash",
        "candidate_research_report_hash",
        "candidate_spec_hash",
        "research_batch_run_hash",
        "research_spec_hash",
        "research_protocol_hash",
        "implementation_fingerprint",
        "research_file_sha256",
        "statistical_audit_hash",
        "statistical_input_binding_hash",
        "research_source_document_sha256",
        "backtest_result_evidence_hash",
        "experiment_completion_receipt_hash",
        "active_candidate_registry_hash",
    )
    for field in required_identity_hashes:
        if not _is_sha256(identity.get(field)):
            blockers.append(f"return_quality_source_identity_hash_invalid:{field}")
    if not str(identity.get("research_generation") or ""):
        blockers.append("return_quality_source_identity_missing:research_generation")

    return {
        "source_integrity_status": "PASS" if not blockers else "BLOCK",
        "source_blockers": list(dict.fromkeys(blockers)),
        "expected_identity": expected_identity,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _project_return_quality_source_evidence(
    *,
    candidate: dict[str, Any],
    research: dict[str, Any],
    statistical: dict[str, Any],
    research_artifact: dict[str, Any],
    registry: dict[str, Any],
    research_source_document: dict[str, Any],
) -> dict[str, Any]:
    result_evidence = _project_backtest_result_evidence_collection(research)
    content = {
        "schema_version": PORTFOLIO_RETURN_QUALITY_SOURCE_EVIDENCE_SCHEMA_VERSION,
        "candidate": _whitelist_source(candidate, _RETURN_QUALITY_CANDIDATE_SOURCE_FIELDS),
        "research": _whitelist_source(research, _RETURN_QUALITY_RESEARCH_SOURCE_FIELDS),
        "statistical": _whitelist_source(
            statistical,
            _RETURN_QUALITY_STATISTICAL_SOURCE_FIELDS,
        ),
        "research_artifact": _whitelist_source(
            research_artifact,
            _RETURN_QUALITY_ARTIFACT_SOURCE_FIELDS,
        ),
        "active_candidate_registry": _whitelist_source(
            registry,
            _RETURN_QUALITY_REGISTRY_SOURCE_FIELDS,
        ),
        "research_source_document": deepcopy(research_source_document),
        "backtest_result_evidence": result_evidence,
        "verification_scope": {
            "semantic_consistency_with_same_embedded_artifact_identity": True,
            "external_anchor_verified": False,
            "cryptographic_authenticity_proven": False,
            "profitability_proven": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    content["source_identity"] = _return_quality_source_identity(
        candidate=dict(content["candidate"]),
        research=dict(content["research"]),
        statistical=dict(content["statistical"]),
        research_artifact=dict(content["research_artifact"]),
        registry=dict(content["active_candidate_registry"]),
        research_document=dict(content["research_source_document"]),
        result_evidence=dict(content["backtest_result_evidence"]),
    )
    semantic = _return_quality_source_semantics(content)
    content["source_integrity_status"] = semantic["source_integrity_status"]
    content["blockers"] = semantic["source_blockers"]
    return {**content, "source_evidence_hash": canonical_hash(content)}


def _verify_return_quality_source_evidence(source: dict[str, Any]) -> dict[str, Any]:
    payload = dict(source or {})
    declared_hash = str(payload.pop("source_evidence_hash", "") or "")
    blockers: list[str] = []
    if not declared_hash or canonical_hash(payload) != declared_hash:
        blockers.append("return_quality_source_evidence_hash_invalid")
    semantic_content = dict(payload)
    declared_integrity = str(semantic_content.pop("source_integrity_status", "") or "")
    declared_blockers = list(semantic_content.pop("blockers", []) or [])
    semantic = _return_quality_source_semantics(semantic_content)
    if declared_integrity != semantic.get("source_integrity_status"):
        blockers.append("return_quality_source_integrity_status_inconsistent")
    if declared_blockers != list(semantic.get("source_blockers") or []):
        blockers.append("return_quality_source_blockers_inconsistent")
    return {
        **semantic,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "source_evidence_hash": declared_hash,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _exact_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _strict_canonical_hash(payload: Any) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _strict_json_object(raw: bytes) -> dict[str, Any]:
    # Only current v5 detached-source paths use this private boundary. Historical
    # v2-v4 pack objects are verified in memory and retain their byte/hash rules.
    return parse_strict_json_object(raw)


def _detached_basename_identity(value: Any) -> str | None:
    """Return one exact NFKC/casefold Windows identity for a detached member."""

    if not isinstance(value, str) or not value:
        return None
    normalized = unicodedata.normalize("NFKC", value)
    if normalized != value or value in {".", ".."} or value != value.rstrip(" ."):
        return None
    if any(character in _WINDOWS_FORBIDDEN_BASENAME_CHARACTERS for character in value):
        return None
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        return None
    windows_path = PureWindowsPath(value)
    if windows_path.is_absolute() or windows_path.drive or windows_path.root:
        return None
    if Path(value).name != value:
        return None
    if len(value.encode("utf-16-le")) // 2 > 255:
        return None
    identity = normalized.casefold()
    if identity.split(".", 1)[0] in _WINDOWS_RESERVED_BASENAMES:
        return None
    return identity


def _safe_detached_basename(value: Any) -> str:
    return value if _detached_basename_identity(value) is not None else ""


def _backtest_result_digest_collection(research: dict[str, Any]) -> dict[str, Any]:
    stages = {
        name: {"source_result_hash": _strict_canonical_hash(dict(research.get(name) or {}))}
        for name in ("validation", "test")
    }
    benchmarks = {
        name: {
            "source_result_hash": _strict_canonical_hash(
                dict(research.get(f"{name}_benchmark") or {})
            )
        }
        for name in ("validation", "test")
    }
    cost_stress = [
        {
            "result_id": str(dict(item or {}).get("label") or f"SCENARIO_{index + 1}"),
            "source_result_hash": _strict_canonical_hash(dict(item or {})),
        }
        for index, item in enumerate(list(research.get("cost_stress") or []))
    ]
    content = {
        "schema_version": PORTFOLIO_BACKTEST_RESULT_DIGEST_COLLECTION_SCHEMA_VERSION,
        "stages": stages,
        "benchmarks": benchmarks,
        "cost_stress": cost_stress,
    }
    return {**content, "collection_hash": _strict_canonical_hash(content)}


def _detached_source_bytes(
    evidence: dict[str, Any],
    key: str,
    payload: dict[str, Any],
) -> bytes:
    raw = evidence.get(key)
    if isinstance(raw, bytes):
        return raw
    if key == "research_raw_bytes":
        exact_payload = dict(evidence.get("research_source_document") or {}).get(
            "payload"
        )
        if isinstance(exact_payload, str):
            return exact_payload.encode("utf-8")
    return _exact_json_bytes(payload)


def _v5_research_document_verification(
    raw: bytes,
    *,
    parsed_from_raw: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Describe one exact detached research member without embedding its text."""

    blockers: list[str] = []
    parsed: dict[str, Any] = {}
    if parsed_from_raw is not None:
        parsed = parsed_from_raw
    else:
        try:
            parsed = _strict_json_object(raw)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            blockers.append("research_source_document_json_invalid")
    if parsed and authority_violations(parsed):
        blockers.append("research_source_document_parsed_contains_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "parsed": parsed,
        "sha256": hashlib.sha256(raw).hexdigest() if raw else "",
        "byte_length": len(raw),
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _v5_source_identity(
    *,
    candidate: dict[str, Any],
    research: dict[str, Any],
    statistical: dict[str, Any],
    research_artifact: dict[str, Any],
    registry: dict[str, Any],
    research_file_byte_length: int,
    research_canonical_object_hash: str,
    candidate_canonical_object_hash: str,
    statistical_canonical_object_hash: str,
    active_candidate_registry_canonical_object_hash: str,
    backtest_result_digest_collection_hash: str,
    detached_source_binding_hash: str,
) -> dict[str, Any]:
    """Build the compact v2 identity while preserving the historical field values."""

    legacy_identity = _return_quality_source_identity(
        candidate=candidate,
        research=research,
        statistical=statistical,
        research_artifact=research_artifact,
        registry=registry,
        research_document={"sha256": research_artifact.get("file_sha256")},
        result_evidence={
            "collection_hash": backtest_result_digest_collection_hash,
        },
    )
    identity_content = {
        key: value
        for key, value in legacy_identity.items()
        if key
        not in {
            "schema_version",
            "identity_hash",
            "research_source_document_sha256",
            "backtest_result_evidence_hash",
        }
    }
    identity_content.update(
        {
            "schema_version": PORTFOLIO_RETURN_QUALITY_SOURCE_IDENTITY_V2_SCHEMA_VERSION,
            "research_file_byte_length": research_file_byte_length,
            "research_canonical_object_hash": research_canonical_object_hash,
            "candidate_canonical_object_hash": candidate_canonical_object_hash,
            "statistical_canonical_object_hash": statistical_canonical_object_hash,
            "active_candidate_registry_canonical_object_hash": (
                active_candidate_registry_canonical_object_hash
            ),
            "backtest_result_digest_collection_hash": (
                backtest_result_digest_collection_hash
            ),
            "detached_source_binding_hash": detached_source_binding_hash,
        }
    )
    return {
        **identity_content,
        "identity_hash": _strict_canonical_hash(identity_content),
    }


_V5_REQUIRED_SOURCE_IDENTITY_HASHES = (
    "candidate_hash",
    "candidate_research_report_hash",
    "candidate_spec_hash",
    "research_batch_run_hash",
    "research_spec_hash",
    "research_protocol_hash",
    "implementation_fingerprint",
    "research_file_sha256",
    "statistical_audit_hash",
    "statistical_input_binding_hash",
    "experiment_completion_receipt_hash",
    "active_candidate_registry_hash",
    "research_canonical_object_hash",
    "candidate_canonical_object_hash",
    "statistical_canonical_object_hash",
    "active_candidate_registry_canonical_object_hash",
    "backtest_result_digest_collection_hash",
    "detached_source_binding_hash",
)


def _v5_normalized_source_semantics(
    *,
    candidate: dict[str, Any],
    candidate_projection: dict[str, Any],
    registry: dict[str, Any],
    registry_projection: dict[str, Any],
    research: dict[str, Any],
    statistical: dict[str, Any],
    research_raw: bytes,
    research_artifact: dict[str, Any],
    identity: dict[str, Any],
    parsed_research_from_raw: dict[str, Any] | None,
) -> dict[str, Any]:
    """Run the mature semantic assertions over borrowed v5 source objects."""

    research_projection = _shallow_whitelist_source(
        research,
        _RETURN_QUALITY_RESEARCH_SOURCE_FIELDS,
    )
    statistical_projection = _shallow_whitelist_source(
        statistical,
        _RETURN_QUALITY_STATISTICAL_SOURCE_FIELDS,
    )
    normalized_source = {
        "schema_version": PORTFOLIO_RETURN_QUALITY_SOURCE_EVIDENCE_SCHEMA_VERSION,
        "candidate": candidate_projection,
        "research": research_projection,
        "statistical": statistical_projection,
        "research_artifact": research_artifact,
        "active_candidate_registry": registry_projection,
        "research_source_document": {},
        "backtest_result_evidence": {},
        "source_identity": identity,
        "verification_scope": {
            "semantic_consistency_with_same_embedded_artifact_identity": True,
            "external_anchor_verified": False,
            "cryptographic_authenticity_proven": False,
            "profitability_proven": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    semantic = _return_quality_source_semantics(
        normalized_source,
        research_document_verification=_v5_research_document_verification(
            research_raw,
            parsed_from_raw=parsed_research_from_raw,
        ),
        expected_identity_override=identity,
        skip_generated_result_evidence_verification=True,
        required_identity_hashes_override=_V5_REQUIRED_SOURCE_IDENTITY_HASHES,
    )
    exact_authority_blockers = [
        f"detached_{name}_contains_execution_authority:{item}"
        for name, value in (("research", research), ("statistical", statistical))
        for item in authority_violations(value)
    ]
    if exact_authority_blockers:
        semantic["source_integrity_status"] = "BLOCK"
        semantic["source_blockers"] = list(
            dict.fromkeys(
                [
                    *list(semantic.get("source_blockers") or []),
                    *exact_authority_blockers,
                ]
            )
        )
    return semantic


def _build_v5_source_material(
    evidence: dict[str, Any],
    *,
    parsed_detached_sources: Mapping[str, dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    active = dict(evidence.get("active") or {})
    candidate = dict(active.get("candidate") or {})
    registry = dict(active.get("registry") or {})
    research = dict(evidence.get("research") or {})
    statistical = dict(evidence.get("statistical") or {})
    if parsed_detached_sources is not None:
        parsed_research = parsed_detached_sources.get(_DETACHED_RESEARCH_ROLE)
        parsed_statistical = parsed_detached_sources.get(_DETACHED_STATISTICAL_ROLE)
        if not isinstance(parsed_research, dict) or not isinstance(
            parsed_statistical,
            dict,
        ):
            raise ValueError("parsed detached source objects required")
        research = parsed_research
        statistical = parsed_statistical
    research_artifact = dict(evidence.get("research_artifact") or {})
    statistical_artifact = dict(evidence.get("statistical_artifact") or {})
    research_raw = _detached_source_bytes(evidence, "research_raw_bytes", research)
    statistical_raw = _detached_source_bytes(
        evidence,
        "statistical_raw_bytes",
        statistical,
    )
    if len(research_raw) > MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES:
        raise ValueError("research detached artifact size limit exceeded")
    if len(statistical_raw) > MAX_PORTFOLIO_STATISTICAL_AUDIT_BYTES:
        raise ValueError("statistical detached artifact size limit exceeded")
    raw_cost_stress = research.get("cost_stress")
    if raw_cost_stress is not None and not isinstance(raw_cost_stress, list):
        raise ValueError("cost stress list required")
    if len(raw_cost_stress or []) > MAX_PORTFOLIO_COST_STRESS_SCENARIOS:
        raise ValueError("cost stress scenario limit exceeded")
    candidate_projection = _whitelist_source(
        candidate,
        _RETURN_QUALITY_CANDIDATE_SOURCE_FIELDS,
    )
    registry_projection = _whitelist_source(
        registry,
        _RETURN_QUALITY_REGISTRY_SOURCE_FIELDS,
    )
    if len(_exact_json_bytes(candidate_projection)) > MAX_PORTFOLIO_COMPACT_CANDIDATE_BYTES:
        raise ValueError("compact candidate size limit exceeded")
    if len(_exact_json_bytes(registry_projection)) > MAX_PORTFOLIO_COMPACT_REGISTRY_BYTES:
        raise ValueError("compact registry size limit exceeded")
    if len(_exact_json_bytes(statistical)) > MAX_PORTFOLIO_STATISTICAL_AUDIT_BYTES:
        raise ValueError("statistical canonical size limit exceeded")
    research_file = str(research_artifact.get("file") or "research.json")
    statistical_file = str(
        statistical_artifact.get("file") or "portfolio_statistical_audit.json"
    )
    research_file_identity = _detached_basename_identity(research_file)
    statistical_file_identity = _detached_basename_identity(statistical_file)
    if research_file_identity is None or statistical_file_identity is None:
        raise ValueError("detached artifact basename required")
    if research_file_identity == statistical_file_identity:
        raise ValueError("detached artifact basename identity duplicate")

    research_sha256 = hashlib.sha256(research_raw).hexdigest()
    statistical_sha256 = hashlib.sha256(statistical_raw).hexdigest()
    research_canonical_object_hash = _strict_canonical_hash(research)
    statistical_canonical_object_hash = _strict_canonical_hash(statistical)
    candidate_canonical_object_hash = _strict_canonical_hash(candidate_projection)
    registry_canonical_object_hash = _strict_canonical_hash(registry_projection)
    digest_collection = _backtest_result_digest_collection(research)
    binding_content = {
        "research_file": research_file,
        "research_file_sha256": research_sha256,
        "research_file_byte_length": len(research_raw),
        "research_canonical_object_hash": research_canonical_object_hash,
        "statistical_file": statistical_file,
        "statistical_file_sha256": statistical_sha256,
        "statistical_file_byte_length": len(statistical_raw),
        "statistical_canonical_object_hash": statistical_canonical_object_hash,
        "candidate_canonical_object_hash": candidate_canonical_object_hash,
        "active_candidate_registry_canonical_object_hash": (
            registry_canonical_object_hash
        ),
        "backtest_result_digest_collection_hash": str(
            digest_collection.get("collection_hash") or ""
        ),
    }
    detached_binding_hash = _strict_canonical_hash(binding_content)
    normalized_research_artifact = {
        "file": research_file,
        "file_sha256": research_sha256,
        "size": len(research_raw),
    }
    identity = _v5_source_identity(
        candidate=candidate_projection,
        research=_shallow_whitelist_source(
            research,
            _RETURN_QUALITY_RESEARCH_SOURCE_FIELDS,
        ),
        statistical=_shallow_whitelist_source(
            statistical,
            _RETURN_QUALITY_STATISTICAL_SOURCE_FIELDS,
        ),
        research_artifact=normalized_research_artifact,
        registry=registry_projection,
        research_file_byte_length=len(research_raw),
        research_canonical_object_hash=research_canonical_object_hash,
        candidate_canonical_object_hash=candidate_canonical_object_hash,
        statistical_canonical_object_hash=statistical_canonical_object_hash,
        active_candidate_registry_canonical_object_hash=(
            registry_canonical_object_hash
        ),
        backtest_result_digest_collection_hash=str(
            digest_collection.get("collection_hash") or ""
        ),
        detached_source_binding_hash=detached_binding_hash,
    )
    source_verification = _v5_normalized_source_semantics(
        candidate=candidate,
        candidate_projection=candidate_projection,
        registry=registry,
        registry_projection=registry_projection,
        research=research,
        statistical=statistical,
        research_raw=research_raw,
        research_artifact=normalized_research_artifact,
        identity=identity,
        parsed_research_from_raw=(
            research if parsed_detached_sources is not None else None
        ),
    )
    source_integrity_pass = (
        source_verification.get("source_integrity_status") == "PASS"
    )
    all_source_blockers = list(
        dict.fromkeys(
            str(item)
            for item in list(source_verification.get("source_blockers") or [])
            if str(item)
        )
    )
    source_blocker_count = len(all_source_blockers)
    bounded_source_blockers = all_source_blockers[:MAX_PORTFOLIO_SOURCE_BLOCKERS]
    manifest_content = {
        "schema_version": PORTFOLIO_RETURN_QUALITY_SOURCE_MANIFEST_SCHEMA_VERSION,
        "research_report": {
            "role": _DETACHED_RESEARCH_ROLE,
            "file": research_file,
            "sha256": research_sha256,
            "byte_length": len(research_raw),
            "canonical_object_hash": research_canonical_object_hash,
        },
        "statistical_audit": {
            "role": _DETACHED_STATISTICAL_ROLE,
            "file": statistical_file,
            "sha256": statistical_sha256,
            "byte_length": len(statistical_raw),
            "canonical_object_hash": statistical_canonical_object_hash,
        },
        "candidate": candidate_projection,
        "active_candidate_registry": registry_projection,
        "backtest_result_digest_collection": digest_collection,
        "source_identity": identity,
        "detached_source_binding_hash": detached_binding_hash,
        "source_integrity_status": "PASS" if source_integrity_pass else "BLOCK",
        "source_blockers": bounded_source_blockers,
        "source_blocker_count": source_blocker_count,
        "source_blockers_truncated": (
            source_blocker_count > len(bounded_source_blockers)
        ),
        "verification_scope": {
            "semantic_consistency_with_detached_exact_source": True,
            "detached_source_required_for_full_verification": True,
            "external_anchor_verified": False,
            "cryptographic_authenticity_proven": False,
            "profitability_proven": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    manifest = {
        **manifest_content,
        "manifest_hash": _strict_canonical_hash(manifest_content),
    }
    quality = build_backtest_return_quality_projection(
        research,
        statistical,
        schema_version=BACKTEST_RETURN_QUALITY_V3_SCHEMA_VERSION,
        source_identity=identity,
        source_manifest_hash=str(manifest.get("manifest_hash") or ""),
        detached_source_binding_hash=detached_binding_hash,
        verified_source_integrity_status=("PASS" if source_integrity_pass else "BLOCK"),
        verified_source_integrity_blockers=bounded_source_blockers,
    )
    artifacts = [
        {
            "role": _DETACHED_RESEARCH_ROLE,
            "file": research_file,
            "sha256": research_sha256,
            "byte_length": len(research_raw),
            "raw_bytes": research_raw,
        },
        {
            "role": _DETACHED_STATISTICAL_ROLE,
            "file": statistical_file,
            "sha256": statistical_sha256,
            "byte_length": len(statistical_raw),
            "raw_bytes": statistical_raw,
        },
    ]
    return manifest, quality, artifacts


def verify_research_artifact(
    report: dict[str, Any],
    *,
    candidate: dict[str, Any],
    registry: dict[str, Any],
    artifact: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    require_bundle = bool((report.get("spec") or {}).get("evidence_bundle_required") is True)
    expanded_report, evidence_bundle_audit = expand_portfolio_evidence_bundle(
        report,
        require_bundle=require_bundle,
    )
    if evidence_bundle_audit.get("status") != "PASS":
        blockers.extend(
            f"research_evidence_bundle:{item}"
            for item in evidence_bundle_audit.get("blockers") or ["verification_failed"]
        )
    semantic_report = expanded_report if evidence_bundle_audit.get("status") == "PASS" else {}
    candidate_hash = str(candidate.get("candidate_hash") or "")
    manifest = dict(semantic_report.get("dataset_manifest") or {})
    receipt = dict(registry.get("experiment_completion_receipt") or {})
    if str((semantic_report.get("frozen_candidate") or {}).get("candidate_hash") or "") != candidate_hash:
        blockers.append("research_candidate_hash_mismatch")
    if str(candidate.get("research_report_hash") or "") != str(semantic_report.get("batch_run_hash") or ""):
        blockers.append("research_candidate_batch_hash_mismatch")
    if str(candidate.get("dataset_hash") or "") != str(manifest.get("data_hash") or ""):
        blockers.append("research_candidate_dataset_hash_mismatch")
    if canonical_hash(semantic_report.get("spec") or {}) != str(semantic_report.get("spec_hash") or ""):
        blockers.append("research_spec_hash_invalid")
    for stage in ("validation", "test"):
        benchmark = dict(semantic_report.get(f"{stage}_benchmark") or {})
        expected = str(benchmark.get("benchmark_run_hash") or "")
        benchmark.pop("benchmark_run_hash", None)
        if not expected or canonical_hash(benchmark) != expected:
            blockers.append(f"{stage}_benchmark_run_hash_invalid")
    if research_batch_hash(report) != str(semantic_report.get("batch_run_hash") or ""):
        blockers.append("research_batch_run_hash_invalid")
    if str(receipt.get("report_file") or "") != str(artifact.get("file") or ""):
        blockers.append("research_receipt_filename_mismatch")
    if str(receipt.get("report_file_sha256") or "") != str(artifact.get("file_sha256") or ""):
        blockers.append("research_receipt_file_hash_mismatch")
    if str(receipt.get("batch_run_hash") or "") != str(semantic_report.get("batch_run_hash") or ""):
        blockers.append("research_receipt_batch_hash_mismatch")
    admission = verify_internal_backtest_admission(dict(semantic_report.get("backtest_admission") or {}))
    if admission.get("status") != "PASS":
        blockers.extend(f"research_admission:{item}" for item in admission.get("blockers") or [])
    if manifest.get("status") != "PASS":
        blockers.append("research_dataset_not_passed")
    if (semantic_report.get("causal_audit") or {}).get("status") != "PASS":
        blockers.append("research_causal_audit_not_passed")
    if (semantic_report.get("correlation_matrix") or {}).get("status") != "PASS":
        blockers.append("research_correlation_audit_not_passed")
    if not all(bool(value) for value in dict(semantic_report.get("development_checks") or {}).values()):
        blockers.append("research_development_checks_not_passed")
    if authority_violations(semantic_report):
        blockers.append("research_contains_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "batch_run_hash": str(semantic_report.get("batch_run_hash") or ""),
        "evidence_bundle_verification": evidence_bundle_audit,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def execution_rehearsal_report_hash(report: dict[str, Any]) -> str:
    content = deepcopy(report)
    for key in (
        "report_hash",
        "generated_at",
        "source_research_report",
        "source_research_file_sha256",
        "active_candidate_registry",
        "active_candidate_hash",
        "source_evidence_bundle_verification",
        "artifact_hash",
    ):
        content.pop(key, None)
    for stage in dict(content.get("stages") or {}).values():
        if isinstance(stage, dict):
            stage.pop("generated_at", None)
    return canonical_hash(content)


def verify_execution_rehearsal_artifact(
    report: dict[str, Any],
    *,
    candidate_hash: str,
    research_batch_run_hash: str,
    research_file_sha256: str,
) -> dict[str, Any]:
    blockers: list[str] = []
    if report.get("status") != "PASS":
        blockers.append("execution_rehearsal_not_passed")
    if str(report.get("source_candidate_hash") or "") != candidate_hash:
        blockers.append("execution_rehearsal_candidate_mismatch")
    if str(report.get("source_batch_run_hash") or "") != research_batch_run_hash:
        blockers.append("execution_rehearsal_batch_mismatch")
    if str(report.get("source_research_file_sha256") or "") != research_file_sha256:
        blockers.append("execution_rehearsal_research_file_mismatch")
    active_hash = str(report.get("active_candidate_hash") or "")
    if active_hash and active_hash != candidate_hash:
        blockers.append("execution_rehearsal_active_candidate_mismatch")
    if execution_rehearsal_report_hash(report) != str(report.get("report_hash") or ""):
        blockers.append("execution_rehearsal_report_hash_invalid")
    if not _verify_hash_field(report, "artifact_hash"):
        blockers.append("execution_rehearsal_artifact_hash_invalid")
    checks = dict(report.get("checks") or {})
    if not checks or not all(bool(value) for value in checks.values()):
        blockers.append("execution_rehearsal_checks_not_passed")
    if not bool(report.get("isolated_in_memory")) or bool(report.get("network_accessed")):
        blockers.append("execution_rehearsal_not_isolated")
    if bool(report.get("production_runtime_mutated")):
        blockers.append("execution_rehearsal_mutated_runtime")
    if authority_violations(report):
        blockers.append("execution_rehearsal_contains_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "report_hash": str(report.get("report_hash") or ""),
        "artifact_hash": str(report.get("artifact_hash") or ""),
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def statistical_audit_content(report: dict[str, Any]) -> dict[str, Any]:
    return _statistical_audit_content(report)


def verify_statistical_audit_artifact(
    report: dict[str, Any],
    *,
    candidate_hash: str,
    research_batch_run_hash: str,
    research_file_sha256: str,
    research_report: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    binding = dict(report.get("input_binding") or {})
    if str(binding.get("candidate_hash") or "") != candidate_hash:
        blockers.append("statistical_audit_candidate_mismatch")
    if str(binding.get("batch_run_hash") or "") != research_batch_run_hash:
        blockers.append("statistical_audit_batch_mismatch")
    if str(report.get("active_candidate_hash") or "") != candidate_hash:
        blockers.append("statistical_audit_active_candidate_mismatch")
    if str(report.get("source_research_file_sha256") or "") != research_file_sha256:
        blockers.append("statistical_audit_research_file_mismatch")
    binding_without_hash = dict(binding)
    expected_binding_hash = str(binding_without_hash.pop("binding_hash", "") or "")
    if not expected_binding_hash or canonical_hash(binding_without_hash) != expected_binding_hash:
        blockers.append("statistical_audit_binding_hash_invalid")
    if canonical_hash(statistical_audit_content(report)) != str(report.get("audit_hash") or ""):
        blockers.append("statistical_audit_hash_invalid")
    if not _verify_hash_field(report, "artifact_hash"):
        blockers.append("statistical_audit_artifact_hash_invalid")
    checks = dict(report.get("checks") or {})
    if checks.get("input_authority_is_research_only") is not True:
        blockers.append("statistical_audit_source_authority_invalid")
    if checks.get("input_binding_complete") is not True:
        blockers.append("statistical_audit_input_binding_incomplete")
    if authority_violations(report):
        blockers.append("statistical_audit_contains_execution_authority")
    semantic_verification = verify_portfolio_statistical_audit_semantics(
        report,
        research_report,
    )
    if semantic_verification.get("status") != "PASS":
        blockers.extend(
            f"statistical_audit_semantics:{item}"
            for item in semantic_verification.get("blockers") or ["verification_blocked"]
        )
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "claim_status": str(report.get("status") or "BLOCK"),
        "conclusion": str(report.get("conclusion") or ""),
        "audit_hash": str(report.get("audit_hash") or ""),
        "artifact_hash": str(report.get("artifact_hash") or ""),
        "semantic_verification": semantic_verification,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _verify_forward_observation(payload: dict[str, Any], candidate_hash: str) -> dict[str, Any]:
    blockers: list[str] = []
    readiness = dict(payload.get("readiness") or {})
    if str(payload.get("candidate_hash") or "") != candidate_hash:
        blockers.append("forward_observation_candidate_mismatch")
    if str(readiness.get("candidate_hash") or "") != candidate_hash:
        blockers.append("forward_readiness_candidate_mismatch")
    if (readiness.get("ledger_audit") or {}).get("status") != "PASS":
        blockers.append("forward_observation_ledger_not_passed")
    critical = dict(readiness.get("critical_checks") or {})
    if not critical or not all(bool(value) for value in critical.values()):
        blockers.append("forward_observation_critical_checks_not_passed")
    if authority_violations(payload):
        blockers.append("forward_observation_contains_execution_authority")
    return {"status": "PASS" if not blockers else "BLOCK", "blockers": blockers}


def verify_forward_performance_artifact(
    payload: dict[str, Any],
    candidate_hash: str,
    statistical_audit: dict[str, Any],
    forward_observation: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    readiness = dict(payload.get("readiness") or {})
    performance = dict(payload.get("performance") or {})
    historical = dict(payload.get("historical_statistical_audit") or {})
    forward_audit = dict(((forward_observation.get("readiness") or {}).get("ledger_audit") or {}))
    performance_shadow_audit = dict(payload.get("shadow_audit") or {})
    if str(payload.get("candidate_hash") or "") != candidate_hash:
        blockers.append("forward_performance_candidate_mismatch")
    if str(performance.get("candidate_hash") or "") != candidate_hash:
        blockers.append("forward_performance_ledger_candidate_mismatch")
    if performance.get("status") != "PASS":
        blockers.append("forward_performance_ledger_not_passed")
    integrity = dict(readiness.get("integrity_checks") or {})
    if not integrity or not all(bool(value) for value in integrity.values()):
        blockers.append("forward_performance_integrity_checks_not_passed")
    if str(historical.get("audit_hash") or "") != str(statistical_audit.get("audit_hash") or ""):
        blockers.append("forward_performance_statistical_audit_mismatch")
    if str(historical.get("artifact_hash") or "") != str(statistical_audit.get("artifact_hash") or ""):
        blockers.append("forward_performance_statistical_artifact_mismatch")
    shadow_audit_hash = str(payload.get("shadow_audit_hash") or "")
    if not shadow_audit_hash or canonical_hash(performance_shadow_audit) != shadow_audit_hash:
        blockers.append("forward_performance_shadow_audit_hash_invalid")
    if not forward_audit or not performance_shadow_audit or canonical_hash(forward_audit) != canonical_hash(performance_shadow_audit):
        blockers.append("forward_performance_observation_snapshot_mismatch")
    if authority_violations(payload):
        blockers.append("forward_performance_contains_execution_authority")
    return {"status": "PASS" if not blockers else "BLOCK", "blockers": blockers}


def _latest_matching_report(
    report_dir: Path,
    pattern: str,
    predicate: Callable[[dict[str, Any]], bool],
    *,
    maximum_bytes: int = MAX_PORTFOLIO_STATISTICAL_AUDIT_BYTES,
) -> tuple[Path | None, dict[str, Any], bytes]:
    matches: list[tuple[int, str, Path, dict[str, Any], bytes]] = []
    for path in report_dir.glob(pattern):
        try:
            payload, raw = _read_bounded_json_artifact(
                path,
                maximum_bytes=maximum_bytes,
            )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            continue
        if predicate(payload):
            matches.append(
                (int(payload.get("generated_at") or 0), path.name, path, payload, raw)
            )
    if not matches:
        return None, {}, b""
    _generated_at, _name, path, payload, raw = max(
        matches,
        key=lambda item: (item[0], item[1]),
    )
    return path, payload, raw


def collect_internal_backtest_evidence(
    report_dir: Path | str,
    *,
    now_ms: int | None = None,
    include_legacy_research_source_document: bool = True,
) -> dict[str, Any]:
    directory = Path(report_dir).resolve()
    active = load_active_portfolio_candidate(directory)
    registry = dict(active.get("registry") or {})
    candidate = dict(active.get("candidate") or {})
    candidate_hash = str(candidate.get("candidate_hash") or "")
    receipt = dict(registry.get("experiment_completion_receipt") or {})
    research_name = str(receipt.get("report_file") or "")
    research_path = directory / research_name if research_name and Path(research_name).name == research_name else None
    research_raw = b""
    try:
        if research_path:
            research, research_raw = _read_bounded_json_artifact(
                research_path,
                maximum_bytes=MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES,
            )
            research_artifact = {
                "file": research_path.name,
                "file_sha256": hashlib.sha256(research_raw).hexdigest(),
                "size": len(research_raw),
            }
            research_source_document = (
                _research_source_document(research_raw.decode("utf-8"))
                if include_legacy_research_source_document
                else {}
            )
        else:
            research, research_artifact, research_source_document = {}, {}, {}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        research, research_artifact, research_source_document, research_raw = {}, {}, {}, b""
    research_file_hash = str(research_artifact.get("file_sha256") or "")
    batch_hash = str(research.get("batch_run_hash") or "")
    rehearsal_path, rehearsal, _rehearsal_raw = _latest_matching_report(
        directory,
        "portfolio_internal_execution_rehearsal_*.json",
        lambda payload: (
            str(payload.get("source_candidate_hash") or "") == candidate_hash
            and str(payload.get("source_batch_run_hash") or "") == batch_hash
            and str(payload.get("source_research_file_sha256") or "") == research_file_hash
        ),
    )
    statistical_path, statistical, statistical_raw = _latest_matching_report(
        directory,
        "portfolio_statistical_audit_*.json",
        lambda payload: (
            str(payload.get("active_candidate_hash") or "") == candidate_hash
            and str((payload.get("input_binding") or {}).get("batch_run_hash") or "") == batch_hash
            and str(payload.get("source_research_file_sha256") or "") == research_file_hash
        ),
    )
    prefix = candidate_hash[:12]
    forward_path = directory / f"portfolio_forward_status_{prefix}.json"
    performance_path = directory / f"portfolio_forward_performance_status_{prefix}.json"
    try:
        forward = read_json_object(forward_path)
        forward_artifact = artifact_record(forward_path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        forward, forward_artifact = {}, {}
    try:
        performance = read_json_object(performance_path)
        performance_artifact = artifact_record(performance_path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        performance, performance_artifact = {}, {}
    scheduler_path = directory / DEFAULT_SCHEDULER_STATUS_FILE
    scheduler = load_forward_scheduler_status(
        scheduler_path,
        now_ms=int(now_ms if now_ms is not None else time.time() * 1000),
    )
    return {
        "active": active,
        "research": research,
        "research_artifact": research_artifact,
        "research_source_document": research_source_document,
        "research_raw_bytes": research_raw if research else b"",
        "rehearsal": rehearsal,
        "rehearsal_artifact": artifact_record(rehearsal_path) if rehearsal_path else {},
        "statistical": statistical,
        "statistical_raw_bytes": statistical_raw,
        "statistical_artifact": artifact_record(statistical_path) if statistical_path else {},
        "forward": forward,
        "forward_artifact": forward_artifact,
        "performance": performance,
        "performance_artifact": performance_artifact,
        "scheduler": scheduler,
        "scheduler_artifact": artifact_record(scheduler_path) if scheduler_path.exists() else {},
    }


def _assemble_internal_backtest_pack_v2(
    evidence: dict[str, Any],
    *,
    generated_at: int,
) -> dict[str, Any]:
    active = dict(evidence.get("active") or {})
    registry = dict(active.get("registry") or {})
    candidate = dict(active.get("candidate") or {})
    robustness = dict(active.get("robustness") or {})
    research = dict(evidence.get("research") or {})
    rehearsal = dict(evidence.get("rehearsal") or {})
    statistical = dict(evidence.get("statistical") or {})
    forward = dict(evidence.get("forward") or {})
    performance = dict(evidence.get("performance") or {})
    scheduler = dict(evidence.get("scheduler") or {})
    candidate_hash = str(candidate.get("candidate_hash") or "")
    research_artifact = dict(evidence.get("research_artifact") or {})
    research_verification = verify_research_artifact(
        research,
        candidate=candidate,
        registry=registry,
        artifact=research_artifact,
    )
    rehearsal_verification = verify_execution_rehearsal_artifact(
        rehearsal,
        candidate_hash=candidate_hash,
        research_batch_run_hash=str(research.get("batch_run_hash") or ""),
        research_file_sha256=str(research_artifact.get("file_sha256") or ""),
    )
    statistical_verification = verify_statistical_audit_artifact(
        statistical,
        candidate_hash=candidate_hash,
        research_batch_run_hash=str(research.get("batch_run_hash") or ""),
        research_file_sha256=str(research_artifact.get("file_sha256") or ""),
        research_report=research,
    )
    forward_verification = _verify_forward_observation(forward, candidate_hash)
    performance_verification = verify_forward_performance_artifact(
        performance,
        candidate_hash,
        statistical,
        forward,
    )
    authority_sources = {
        "registry": registry,
        "candidate": candidate,
        "robustness": robustness,
        "research": research,
        "rehearsal": rehearsal,
        "statistical": statistical,
        "forward": forward,
        "performance": performance,
        "scheduler": scheduler,
    }
    execution_authority_violations = [
        f"{name}:{item}"
        for name, payload in authority_sources.items()
        for item in authority_violations(payload)
    ]
    checks = {
        "active_candidate_chain_pass": active.get("status") == "PASS",
        "candidate_fingerprint_pass": (active.get("candidate_verification") or {}).get("status") == "PASS",
        "experiment_artifacts_pass": (active.get("experiment_artifact_verification") or {}).get("status") == "PASS",
        "research_artifact_binding_pass": research_verification.get("status") == "PASS",
        "robustness_pass": (active.get("robustness_verification") or {}).get("status") == "PASS",
        "execution_rehearsal_pass": rehearsal_verification.get("status") == "PASS",
        "statistical_audit_integrity_pass": statistical_verification.get("status") == "PASS",
        "forward_observation_integrity_pass": forward_verification.get("status") == "PASS",
        "forward_performance_integrity_pass": performance_verification.get("status") == "PASS",
        "scheduler_health_pass": scheduler.get("health") == "PASS" and str(scheduler.get("candidate_hash") or "") == candidate_hash,
        "zero_execution_authority": not execution_authority_violations,
        "artifact_verification_only": True,
        "no_market_data_fetch": True,
        "no_parameter_search": True,
    }
    blocker_groups = {
        "active": list(active.get("blockers") or []),
        "research": list(research_verification.get("blockers") or []),
        "rehearsal": list(rehearsal_verification.get("blockers") or []),
        "statistical_integrity": list(statistical_verification.get("blockers") or []),
        "forward": list(forward_verification.get("blockers") or []),
        "performance": list(performance_verification.get("blockers") or []),
        "authority": execution_authority_violations,
    }
    blockers = [
        f"{group}:{item}"
        for group, values in blocker_groups.items()
        for item in values
    ]
    blockers.extend(f"check_failed:{key}" for key, passed in checks.items() if not passed)
    internal_ready = not blockers and all(checks.values())
    performance_readiness = dict(performance.get("readiness") or {})
    promotion_blockers = list(performance_readiness.get("blockers") or [])
    if statistical.get("status") != "PASS":
        promotion_blockers.append("historical_statistical_audit_pass")
    if not internal_ready:
        promotion_blockers.append("internal_backtest_evidence_ready")
    promotion_blockers = list(dict.fromkeys(promotion_blockers))
    manifest = dict(research.get("dataset_manifest") or {})
    payload = {
        "schema_version": PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION,
        "status": "INTERNAL_BACKTEST_EVIDENCE_READY" if internal_ready else "INTERNAL_BACKTEST_BLOCKED",
        "promotion_status": "PASS" if not promotion_blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "promotion_blockers": promotion_blockers,
        "generated_at": int(generated_at),
        "candidate": {
            "candidate_id": str(candidate.get("candidate_id") or ""),
            "candidate_hash": candidate_hash,
            "implementation_fingerprint": str((candidate.get("implementation") or {}).get("fingerprint") or ""),
            "dataset_hash": str(candidate.get("dataset_hash") or ""),
            "dataset_first": str(candidate.get("dataset_first") or ""),
            "dataset_last": str(candidate.get("dataset_last") or ""),
            "dataset_row_count": int(candidate.get("dataset_row_count") or 0),
            "activated_at": int(registry.get("activated_at") or 0),
        },
        "historical_backtest": {
            "batch_run_hash": str(research.get("batch_run_hash") or ""),
            "dataset_status": str(manifest.get("status") or ""),
            "validation": {
                "return_pct": (research.get("validation") or {}).get("total_return_pct"),
                "max_drawdown_pct": (research.get("validation") or {}).get("max_drawdown_pct"),
                "sharpe": (research.get("validation") or {}).get("sharpe"),
                "run_hash": (research.get("validation") or {}).get("run_hash", ""),
                "benchmark_run_hash": (
                    research.get("validation_benchmark") or {}
                ).get("benchmark_run_hash", ""),
            },
            "test": {
                "return_pct": (research.get("test") or {}).get("total_return_pct"),
                "max_drawdown_pct": (research.get("test") or {}).get("max_drawdown_pct"),
                "sharpe": (research.get("test") or {}).get("sharpe"),
                "run_hash": (research.get("test") or {}).get("run_hash", ""),
                "benchmark_run_hash": (
                    research.get("test_benchmark") or {}
                ).get("benchmark_run_hash", ""),
            },
        },
        "return_quality": build_backtest_return_quality_projection(research, statistical),
        "checks": checks,
        "verifications": {
            "candidate": active.get("candidate_verification") or {},
            "research": research_verification,
            "robustness": active.get("robustness_verification") or {},
            "execution_rehearsal": rehearsal_verification,
            "statistical_audit": statistical_verification,
            "forward_observation": forward_verification,
            "forward_performance": performance_verification,
        },
        "artifacts": {
            "candidate": {
                "file": str(registry.get("candidate_file") or ""),
                "file_sha256": str(registry.get("candidate_file_sha256") or ""),
            },
            "research": research_artifact,
            "robustness": {
                "file": str(registry.get("robustness_file") or ""),
                "file_sha256": str(registry.get("robustness_file_sha256") or ""),
                "robustness_hash": str(robustness.get("robustness_hash") or ""),
            },
            "execution_rehearsal": evidence.get("rehearsal_artifact") or {},
            "statistical_audit": evidence.get("statistical_artifact") or {},
            "forward_observation": evidence.get("forward_artifact") or {},
            "forward_performance": evidence.get("performance_artifact") or {},
            "scheduler": evidence.get("scheduler_artifact") or {},
        },
        "statistical_claim": {
            "status": str(statistical.get("status") or "BLOCK"),
            "conclusion": str(statistical.get("conclusion") or ""),
            "audit_hash": str(statistical.get("audit_hash") or ""),
        },
        "forward_progress": {
            "observations": int(((forward.get("readiness") or {}).get("progress") or {}).get("natural_observations") or 0),
            "required_observations": int(((forward.get("readiness") or {}).get("progress") or {}).get("required_natural_observations") or 0),
            "outcome_periods": int(((performance.get("performance") or {}).get("outcome_period_count") or 0)),
            "required_outcome_periods": int(((performance_readiness.get("progress") or {}).get("required_forward_outcomes") or 0)),
            "executed_rebalances": int(((performance_readiness.get("progress") or {}).get("executed_rebalances") or 0)),
            "required_executed_rebalances": int(((performance_readiness.get("progress") or {}).get("required_executed_rebalances") or 0)),
            "scheduler_health": str(scheduler.get("health") or "MISSING"),
        },
        "source_mode": "FROZEN_ARTIFACT_VERIFICATION_ONLY",
        "parameter_selection_allowed": False,
        "automatic_paper_activation_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    evidence_content = deepcopy(payload)
    evidence_content.pop("generated_at", None)
    payload["evidence_hash"] = canonical_hash(evidence_content)
    payload["pack_hash"] = canonical_hash(payload)
    return payload


def _content_hash_valid(payload: dict[str, Any], field: str) -> bool:
    expected = str(payload.get(field) or "")
    content = dict(payload)
    content.pop(field, None)
    return bool(expected) and canonical_hash(content) == expected


def _forward_stage_hash_valid(stage: dict[str, Any]) -> bool:
    if not stage:
        return True
    expected = str(stage.get("stage_hash") or "")
    content = dict(stage)
    content.pop("stage_hash", None)
    return bool(expected) and canonical_hash(content) == expected


def _forward_series_hash_valid(series: dict[str, Any]) -> bool:
    if series.get("schema_version") != PORTFOLIO_FORWARD_SERIES_EVIDENCE_SCHEMA_VERSION:
        return False
    expected = str(series.get("series_hash") or "")
    content = dict(series)
    content.pop("series_hash", None)
    return bool(expected) and canonical_hash(content) == expected


def _historical_statistical_source(
    statistical: dict[str, Any],
    statistical_verification: dict[str, Any],
) -> dict[str, Any]:
    config = deepcopy(dict(statistical.get("config") or {}))
    binding = deepcopy(dict(statistical.get("input_binding") or {}))
    semantic = dict(statistical_verification.get("semantic_verification") or {})
    return {
        "schema_version": str(statistical.get("schema_version") or ""),
        "claim_status": str(statistical.get("status") or "MISSING"),
        "conclusion": str(statistical.get("conclusion") or ""),
        "audit_hash": str(statistical.get("audit_hash") or ""),
        "artifact_hash": str(statistical.get("artifact_hash") or ""),
        "config": config,
        "config_hash": canonical_hash(config),
        "input_binding": binding,
        "input_binding_hash": canonical_hash(binding),
        "artifact_verification_status": str(statistical_verification.get("status") or "BLOCK"),
        "semantic_verification": {
            "status": str(semantic.get("status") or "BLOCK"),
            "claim_status": str(semantic.get("claim_status") or "BLOCK"),
            "expected_status": str(semantic.get("expected_status") or "BLOCK"),
            "expected_conclusion": str(semantic.get("expected_conclusion") or ""),
            "expected_audit_hash": str(semantic.get("expected_audit_hash") or ""),
            "recomputed_from_frozen_research": bool(
                semantic.get("recomputed_from_frozen_research")
            ),
        },
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _project_forward_promotion_evidence(
    *,
    candidate: dict[str, Any],
    statistical: dict[str, Any],
    statistical_verification: dict[str, Any],
    performance: dict[str, Any],
) -> dict[str, Any]:
    spec = deepcopy(dict(candidate.get("spec") or {}))
    performance_summary = deepcopy(dict(performance.get("performance") or {}))
    readiness = deepcopy(dict(performance.get("readiness") or {}))
    forward_audit = deepcopy(dict(performance.get("forward_statistical_audit") or {}))
    historical = _historical_statistical_source(statistical, statistical_verification)
    content = {
        "schema_version": PORTFOLIO_INTERNAL_FORWARD_EVIDENCE_SCHEMA_VERSION,
        "candidate": {
            "candidate_hash": str(candidate.get("candidate_hash") or ""),
            "declared_spec_hash": str(candidate.get("spec_hash") or ""),
            "computed_spec_hash": canonical_hash(spec),
            "spec": spec,
        },
        "historical_statistical_contract_source": historical,
        "performance_summary": performance_summary,
        "readiness": readiness,
        "forward_statistical_audit": forward_audit,
        "validation_scope": {
            "level": (
                "PACK_STRUCTURAL_AND_CONTENT_HASH_VALIDATION_OF_"
                "UPSTREAM_SEMANTIC_RECOMPUTATION_RECEIPT"
            ),
            "settlement_database_reloaded_by_pack": False,
            "settlement_chain_independently_replayed_by_pack": False,
            "full_forward_rows_hash_bound": True,
        },
        "profitability_proven": False,
        "performance_claim_proven": False,
        "parameter_selection_allowed": False,
        "automatic_paper_activation_allowed": False,
        "manual_review_required": True,
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    semantic = _evaluate_forward_promotion_evidence(content)
    content["source_integrity_status"] = str(semantic.get("source_integrity_status") or "BLOCK")
    content["forward_evidence_status"] = str(semantic.get("forward_evidence_status") or "BLOCK")
    content["blockers"] = list(semantic.get("evidence_blockers") or [])
    content["projection_hash"] = canonical_hash(content)
    return content


def _evaluate_forward_promotion_evidence(projection: dict[str, Any]) -> dict[str, Any]:
    payload = dict(projection or {})
    blockers: list[str] = []
    if payload.get("schema_version") != PORTFOLIO_INTERNAL_FORWARD_EVIDENCE_SCHEMA_VERSION:
        blockers.append("forward_evidence_schema_invalid")
    if authority_violations(payload):
        blockers.append("forward_evidence_contains_execution_authority")
    for field, expected in (
        ("profitability_proven", False),
        ("performance_claim_proven", False),
        ("parameter_selection_allowed", False),
        ("automatic_paper_activation_allowed", False),
        ("manual_review_required", True),
        ("research_only", True),
        ("observation_only", True),
        ("simulation_only", True),
        ("paper_authorized", False),
        ("live_order_allowed", False),
    ):
        if payload.get(field) is not expected:
            blockers.append(f"forward_evidence_scope_invalid:{field}")
    scope = dict(payload.get("validation_scope") or {})
    if scope.get("level") != (
        "PACK_STRUCTURAL_AND_CONTENT_HASH_VALIDATION_OF_"
        "UPSTREAM_SEMANTIC_RECOMPUTATION_RECEIPT"
    ):
        blockers.append("forward_evidence_validation_level_invalid")
    if scope.get("settlement_database_reloaded_by_pack") is not False:
        blockers.append("forward_evidence_database_replay_claim_invalid")
    if scope.get("settlement_chain_independently_replayed_by_pack") is not False:
        blockers.append("forward_evidence_chain_replay_claim_invalid")
    if scope.get("full_forward_rows_hash_bound") is not True:
        blockers.append("forward_evidence_rows_binding_scope_invalid")

    candidate = dict(payload.get("candidate") or {})
    spec = dict(candidate.get("spec") or {})
    computed_spec_hash = canonical_hash(spec)
    candidate_hash = str(candidate.get("candidate_hash") or "")
    if not candidate_hash:
        blockers.append("forward_evidence_candidate_hash_missing")
    if str(candidate.get("computed_spec_hash") or "") != computed_spec_hash:
        blockers.append("forward_evidence_computed_spec_hash_invalid")
    declared_spec_hash = str(candidate.get("declared_spec_hash") or "")
    if declared_spec_hash and declared_spec_hash != computed_spec_hash:
        blockers.append("forward_evidence_declared_spec_hash_mismatch")

    historical = dict(payload.get("historical_statistical_contract_source") or {})
    historical_config = dict(historical.get("config") or {})
    historical_binding = dict(historical.get("input_binding") or {})
    historical_semantic = dict(historical.get("semantic_verification") or {})
    if historical.get("schema_version") != PORTFOLIO_STATISTICAL_AUDIT_SCHEMA_VERSION:
        blockers.append("forward_evidence_historical_schema_invalid")
    if historical.get("claim_status") not in {"PASS", "BLOCK"}:
        blockers.append("forward_evidence_historical_claim_status_invalid")
    if historical.get("artifact_verification_status") != "PASS":
        blockers.append("forward_evidence_historical_artifact_not_verified")
    if historical_semantic.get("status") != "PASS":
        blockers.append("forward_evidence_historical_semantics_not_verified")
    if historical_semantic.get("recomputed_from_frozen_research") is not True:
        blockers.append("forward_evidence_historical_semantics_not_recomputed")
    if str(historical_semantic.get("expected_audit_hash") or "") != str(
        historical.get("audit_hash") or ""
    ):
        blockers.append("forward_evidence_historical_semantic_identity_mismatch")
    if canonical_hash(historical_config) != str(historical.get("config_hash") or ""):
        blockers.append("forward_evidence_historical_config_hash_invalid")
    if canonical_hash(historical_binding) != str(historical.get("input_binding_hash") or ""):
        blockers.append("forward_evidence_historical_input_binding_projection_hash_invalid")
    supplied_binding_hash = str(historical_binding.get("binding_hash") or "")
    binding_content = dict(historical_binding)
    binding_content.pop("binding_hash", None)
    if not supplied_binding_hash or canonical_hash(binding_content) != supplied_binding_hash:
        blockers.append("forward_evidence_historical_input_binding_hash_invalid")
    if str(historical_binding.get("candidate_hash") or "") != candidate_hash:
        blockers.append("forward_evidence_historical_candidate_mismatch")
    if str(historical_binding.get("spec_hash") or "") != computed_spec_hash:
        blockers.append("forward_evidence_historical_spec_mismatch")
    if not str(historical.get("audit_hash") or "") or not str(historical.get("artifact_hash") or ""):
        blockers.append("forward_evidence_historical_identity_missing")

    performance = dict(payload.get("performance_summary") or {})
    if performance.get("status") != "PASS":
        blockers.append("forward_evidence_performance_summary_not_passed")
    if str(performance.get("candidate_hash") or "") != candidate_hash:
        blockers.append("forward_evidence_performance_candidate_mismatch")

    audit = dict(payload.get("forward_statistical_audit") or {})
    audit_binding = dict(audit.get("input_binding") or {})
    audit_maturity = dict(audit.get("maturity") or {})
    series = dict(audit.get("series_evidence") or {})
    stage = dict(audit.get("stage") or {})
    if audit.get("schema_version") != PORTFOLIO_FORWARD_STATISTICAL_AUDIT_SCHEMA_VERSION:
        blockers.append("forward_evidence_audit_schema_invalid")
    if audit.get("verification_status") != "PASS":
        blockers.append("forward_evidence_audit_not_verified")
    if audit.get("semantic_recomputed") is not True:
        blockers.append("forward_evidence_audit_not_semantically_recomputed")
    if audit.get("verification_blockers"):
        blockers.append("forward_evidence_audit_verification_blockers_present")
    if canonical_hash(forward_statistical_audit_content(audit)) != str(audit.get("audit_hash") or ""):
        blockers.append("forward_evidence_audit_hash_invalid")
    if not _forward_series_hash_valid(series):
        blockers.append("forward_evidence_series_hash_invalid")
    if not _forward_stage_hash_valid(stage):
        blockers.append("forward_evidence_stage_hash_invalid")
    if audit_binding:
        supplied_audit_binding_hash = str(audit_binding.get("binding_hash") or "")
        audit_binding_content = dict(audit_binding)
        audit_binding_content.pop("binding_hash", None)
        if not supplied_audit_binding_hash or canonical_hash(audit_binding_content) != supplied_audit_binding_hash:
            blockers.append("forward_evidence_audit_binding_hash_invalid")
    else:
        blockers.append("forward_evidence_audit_binding_missing")
    if str(audit_binding.get("candidate_hash") or "") != candidate_hash:
        blockers.append("forward_evidence_audit_candidate_mismatch")
    if str(audit_binding.get("candidate_spec_hash") or "") != computed_spec_hash:
        blockers.append("forward_evidence_audit_spec_mismatch")
    if str(audit_binding.get("historical_statistical_audit_hash") or "") != str(
        historical.get("audit_hash") or ""
    ):
        blockers.append("forward_evidence_audit_historical_identity_mismatch")
    if str(audit_binding.get("historical_statistical_artifact_hash") or "") != str(
        historical.get("artifact_hash") or ""
    ):
        blockers.append("forward_evidence_audit_historical_artifact_mismatch")
    if str(audit_binding.get("historical_statistical_config_hash") or "") != str(
        historical.get("config_hash") or ""
    ):
        blockers.append("forward_evidence_audit_historical_config_mismatch")
    if str(audit_binding.get("historical_statistical_input_binding_hash") or "") != supplied_binding_hash:
        blockers.append("forward_evidence_audit_historical_binding_mismatch")
    if str(audit_binding.get("forward_series_hash") or "") != str(series.get("series_hash") or ""):
        blockers.append("forward_evidence_audit_series_mismatch")
    if str(audit_binding.get("latest_settlement_hash") or "") != str(
        performance.get("latest_settlement_hash") or ""
    ):
        blockers.append("forward_evidence_audit_latest_settlement_mismatch")
    for binding_field, performance_field in (
        ("settlement_count", "settlement_count"),
        ("outcome_period_count", "outcome_period_count"),
        ("rebalance_execution_count", "rebalance_execution_count"),
    ):
        if audit_binding.get(binding_field) != performance.get(performance_field):
            blockers.append(f"forward_evidence_audit_performance_count_mismatch:{binding_field}")
    if dict(audit.get("contract_comparison") or {}).get("status") != "PASS":
        blockers.append("forward_evidence_contract_comparison_not_passed")
    contract = dict(audit.get("statistical_contract") or {})
    contract_hash = str(contract.get("contract_hash") or "")
    contract_content = dict(contract)
    contract_content.pop("contract_hash", None)
    if not contract_hash or canonical_hash(contract_content) != contract_hash:
        blockers.append("forward_evidence_contract_hash_invalid")
    if str(audit_binding.get("statistical_contract_hash") or "") != contract_hash:
        blockers.append("forward_evidence_contract_binding_mismatch")
    if str(contract.get("source_historical_audit_hash") or "") != str(historical.get("audit_hash") or ""):
        blockers.append("forward_evidence_contract_historical_identity_mismatch")
    if str(contract.get("source_historical_artifact_hash") or "") != str(historical.get("artifact_hash") or ""):
        blockers.append("forward_evidence_contract_historical_artifact_mismatch")
    if str(contract.get("source_historical_claim_status") or "") != str(historical.get("claim_status") or ""):
        blockers.append("forward_evidence_contract_historical_claim_mismatch")

    readiness = dict(payload.get("readiness") or {})
    readiness_audit = dict(readiness.get("forward_statistical_audit") or {})
    if readiness.get("schema_version") != PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION:
        blockers.append("forward_evidence_readiness_schema_invalid")
    if authority_violations(readiness):
        blockers.append("forward_evidence_readiness_contains_execution_authority")
    if readiness.get("historical_statistical_claim_status") != historical.get("claim_status"):
        blockers.append("forward_evidence_readiness_historical_claim_mismatch")
    for field in ("schema_version", "status", "conclusion", "audit_hash", "verification_status"):
        if readiness_audit.get(field) != audit.get(field):
            blockers.append(f"forward_evidence_readiness_audit_mismatch:{field}")
    for field in ("maturity", "input_binding", "contract_comparison"):
        if canonical_hash(readiness_audit.get(field)) != canonical_hash(audit.get(field)):
            blockers.append(f"forward_evidence_readiness_audit_mismatch:{field}")
    integrity_checks = dict(readiness.get("integrity_checks") or {})
    if not integrity_checks or not all(value is True for value in integrity_checks.values()):
        blockers.append("forward_evidence_readiness_integrity_not_passed")

    outcomes = performance.get("outcome_period_count")
    rebalances = performance.get("rebalance_execution_count")
    required_outcomes = audit_maturity.get("required_forward_outcomes")
    required_rebalances = audit_maturity.get("required_executed_rebalances")
    numbers = (outcomes, rebalances, required_outcomes, required_rebalances)
    counts_valid = all(type(value) is int and value >= 0 for value in numbers)
    due = counts_valid and outcomes >= required_outcomes and rebalances >= required_rebalances
    maturity_matches = (
        counts_valid
        and audit_maturity.get("forward_outcomes") == outcomes
        and audit_maturity.get("executed_rebalances") == rebalances
        and audit_maturity.get("status") == ("DUE" if due else "NOT_DUE")
        and readiness.get("forward_statistical_audit_due_status") == ("DUE" if due else "NOT_DUE")
    )
    if not maturity_matches:
        blockers.append("forward_evidence_maturity_binding_invalid")

    claim_status = "BLOCK"
    evidence_blockers: list[str] = []
    if not blockers:
        if (
            not due
            and audit.get("status") == "NOT_DUE"
            and audit.get("conclusion") == "FORWARD_STATISTICAL_AUDIT_NOT_DUE"
            and not stage
            and readiness.get("status") == "COLLECTING"
            and readiness.get("promotion_status") == "BLOCK"
        ):
            claim_status = "COLLECTING"
            evidence_blockers.append("natural_forward_statistical_evidence_not_mature")
        elif (
            due
            and audit.get("status") == "PASS"
            and audit.get("conclusion") == "FORWARD_STATISTICAL_CONTRACT_PASS"
            and stage.get("status") == "PASS"
            and readiness.get("status") == "RESEARCH_REVIEW_READY"
            and readiness.get("promotion_status") == "REVIEW_REQUIRED"
        ):
            claim_status = "RESEARCH_REVIEW_READY"
        elif (
            due
            and audit.get("status") == "BLOCK"
            and audit.get("conclusion") == "FORWARD_STATISTICAL_CONTRACT_FAILED"
            and stage.get("status") == "BLOCK"
            and readiness.get("status") == "RESEARCH_REVIEW_BLOCKED"
            and readiness.get("promotion_status") == "BLOCK"
        ):
            claim_status = "RESEARCH_REVIEW_BLOCKED"
            evidence_blockers.append("natural_forward_statistical_evidence_not_passed")
        else:
            blockers.append("forward_evidence_state_contract_invalid")
    if blockers:
        claim_status = "BLOCK"
        evidence_blockers = ["natural_forward_statistical_evidence_integrity_blocked"]
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "source_integrity_status": "PASS" if not blockers else "BLOCK",
        "forward_evidence_status": claim_status,
        "evidence_blockers": evidence_blockers,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _verify_forward_promotion_evidence(projection: dict[str, Any]) -> dict[str, Any]:
    payload = dict(projection or {})
    expected_projection_hash = str(payload.get("projection_hash") or "")
    projection_content = dict(payload)
    projection_content.pop("projection_hash", None)
    hash_valid = bool(expected_projection_hash) and canonical_hash(projection_content) == expected_projection_hash
    semantic_content = dict(projection_content)
    declared_integrity = str(semantic_content.pop("source_integrity_status", "") or "")
    declared_status = str(semantic_content.pop("forward_evidence_status", "") or "")
    declared_blockers = list(semantic_content.pop("blockers", []) or [])
    semantic = _evaluate_forward_promotion_evidence(semantic_content)
    blockers: list[str] = []
    if not hash_valid:
        blockers.append("forward_evidence_projection_hash_invalid")
    if declared_integrity != semantic.get("source_integrity_status"):
        blockers.append("forward_evidence_source_integrity_status_inconsistent")
    if declared_status != semantic.get("forward_evidence_status"):
        blockers.append("forward_evidence_status_inconsistent")
    if declared_blockers != list(semantic.get("evidence_blockers") or []):
        blockers.append("forward_evidence_blockers_inconsistent")
    return {
        **semantic,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "source_blockers": list(semantic.get("blockers") or []),
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _v2_native_integer(value: Any, *, minimum: int = 0) -> int | None:
    if (
        type(value) is not int
        or value < minimum
        or value > _PORTFOLIO_FORWARD_V2_MAX_SAFE_INTEGER
    ):
        return None
    return value


def _v2_native_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        result = float(value)
    except (OverflowError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _v2_hash_field_valid(payload: dict[str, Any], field: str) -> bool:
    expected = str(payload.get(field) or "")
    content = dict(payload)
    content.pop(field, None)
    return bool(expected) and canonical_hash(content) == expected


def _v2_decision_series_hash(
    series: dict[str, Any],
    prefix: dict[str, Any],
) -> str:
    first_due_index = prefix.get("first_due_settlement_index")
    rows_value = series.get("rows")
    if (
        prefix.get("status") != "DUE"
        or type(first_due_index) is not int
        or not isinstance(rows_value, list)
        or first_due_index < 0
        or first_due_index >= len(rows_value)
    ):
        return ""
    rows = [deepcopy(dict(item)) for item in rows_value[: first_due_index + 1]]
    content = deepcopy(series)
    content.pop("series_hash", None)
    content.update({
        "settlement_count": len(rows),
        "outcome_period_count": max(len(rows) - 1, 0),
        "rebalance_execution_count": sum(
            int(item.get("rebalance_executed") is True) for item in rows
        ),
        "first_settlement_date": str(rows[0].get("date") or "") if rows else "",
        "last_settlement_date": str(rows[-1].get("date") or "") if rows else "",
        "first_settlement_hash": (
            str(rows[0].get("settlement_hash") or "") if rows else ""
        ),
        "latest_settlement_hash": (
            str(rows[-1].get("settlement_hash") or "") if rows else ""
        ),
        "ordered_settlement_hashes": [
            str(item.get("settlement_hash") or "") for item in rows
        ],
        "rows": rows,
    })
    return canonical_hash(content)


def _v2_nonfinite_number_present(payload: Any) -> bool:
    """Reject non-finite values anywhere in the self-contained v2 receipt."""

    stack = [payload]
    seen: set[int] = set()
    while stack:
        value = stack.pop()
        if isinstance(value, bool) or value is None or isinstance(value, (str, bytes)):
            continue
        if isinstance(value, float):
            if not math.isfinite(value):
                return True
            continue
        if isinstance(value, Mapping):
            identity = id(value)
            if identity in seen:
                continue
            seen.add(identity)
            stack.extend(value.values())
            continue
        if isinstance(value, (list, tuple)):
            identity = id(value)
            if identity in seen:
                continue
            seen.add(identity)
            stack.extend(value)
    return False


def _v2_expected_contract_comparison(
    *,
    historical_config: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    copied_fields = {
        field: {
            "historical": historical_config.get(field),
            "forward": contract.get(field),
            "matches": historical_config.get(field) == contract.get(field),
        }
        for field in _PORTFOLIO_FORWARD_V2_COPIED_CONTRACT_FIELDS
    }
    return {
        "status": (
            "PASS"
            if all(item["matches"] for item in copied_fields.values())
            else "BLOCK"
        ),
        "copied_fields": copied_fields,
        "allowed_difference": {
            "field": "minimum_observations",
            "historical": historical_config.get("minimum_observations"),
            "forward": contract.get("minimum_observations"),
            "reason": "FROZEN_CANDIDATE_FORWARD_MATURITY_FLOOR",
        },
        "other_differences_allowed": False,
    }


def _v2_stage_receipt_consistent(stage: dict[str, Any], *, due: bool) -> bool:
    if not due:
        return not stage
    checks = stage.get("checks")
    if not isinstance(checks, dict) or set(checks) != set(
        _PORTFOLIO_FORWARD_V2_STAGE_CHECK_FIELDS
    ):
        return False
    if not all(isinstance(value, bool) for value in checks.values()):
        return False
    expected_blockers = [
        name
        for name in _PORTFOLIO_FORWARD_V2_STAGE_CHECK_FIELDS
        if checks.get(name) is not True
    ]
    return (
        _forward_stage_hash_valid(stage)
        and list(stage.get("blockers") or []) == expected_blockers
        and stage.get("status") == ("PASS" if not expected_blockers else "BLOCK")
    )

def _project_forward_promotion_evidence_v2(
    *,
    candidate: dict[str, Any],
    statistical: dict[str, Any],
    statistical_verification: dict[str, Any],
    performance: dict[str, Any],
) -> dict[str, Any]:
    """Project the current frozen single-look forward evidence contract."""

    spec = deepcopy(dict(candidate.get("spec") or {}))
    performance_summary = deepcopy(dict(performance.get("performance") or {}))
    readiness = deepcopy(dict(performance.get("readiness") or {}))
    forward_audit = deepcopy(dict(performance.get("forward_statistical_audit") or {}))
    historical = _historical_statistical_source(statistical, statistical_verification)
    content = {
        "schema_version": PORTFOLIO_INTERNAL_FORWARD_EVIDENCE_V2_SCHEMA_VERSION,
        "candidate": {
            "candidate_hash": str(candidate.get("candidate_hash") or ""),
            "declared_spec_hash": str(candidate.get("spec_hash") or ""),
            "computed_spec_hash": canonical_hash(spec),
            "spec": spec,
        },
        "historical_statistical_contract_source": historical,
        "performance_summary": performance_summary,
        "readiness": readiness,
        "forward_statistical_audit": forward_audit,
        "validation_scope": {
            "level": (
                "PACK_STRUCTURAL_AND_CONTENT_HASH_VALIDATION_OF_"
                "UPSTREAM_SINGLE_LOOK_SEMANTIC_RECOMPUTATION_RECEIPT"
            ),
            "settlement_database_reloaded_by_pack": False,
            "settlement_chain_independently_replayed_by_pack": False,
            "full_forward_rows_hash_bound": True,
            "first_joint_maturity_prefix_hash_bound": True,
            "single_look_decision_hash_bound": True,
            "statistical_stage_hash_bound": True,
            "risk_acceptance_hash_bound": True,
            "later_settlements_descriptive_only": True,
        },
        "profitability_proven": False,
        "performance_claim_proven": False,
        "parameter_selection_allowed": False,
        "automatic_paper_activation_allowed": False,
        "manual_review_required": True,
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    semantic = _evaluate_forward_promotion_evidence_v2(content)
    content["source_integrity_status"] = str(
        semantic.get("source_integrity_status") or "BLOCK"
    )
    content["forward_evidence_status"] = str(
        semantic.get("forward_evidence_status") or "BLOCK"
    )
    content["blockers"] = list(semantic.get("evidence_blockers") or [])
    content["projection_hash"] = canonical_hash(content)
    return content


def _evaluate_forward_promotion_evidence_v2(
    projection: dict[str, Any],
) -> dict[str, Any]:
    payload = dict(projection or {})
    blockers: list[str] = []
    if _v2_nonfinite_number_present(payload):
        blockers.append("forward_evidence_v2_nonfinite_number")
    if payload.get("schema_version") != PORTFOLIO_INTERNAL_FORWARD_EVIDENCE_V2_SCHEMA_VERSION:
        blockers.append("forward_evidence_v2_schema_invalid")
    payload_authority_violations = authority_violations(payload)
    if payload_authority_violations:
        blockers.append("forward_evidence_v2_contains_execution_authority")
    for field, expected in (
        ("profitability_proven", False),
        ("performance_claim_proven", False),
        ("parameter_selection_allowed", False),
        ("automatic_paper_activation_allowed", False),
        ("manual_review_required", True),
        ("research_only", True),
        ("observation_only", True),
        ("simulation_only", True),
        ("paper_authorized", False),
        ("live_order_allowed", False),
    ):
        if payload.get(field) is not expected:
            blockers.append(f"forward_evidence_v2_scope_invalid:{field}")

    scope = dict(payload.get("validation_scope") or {})
    expected_scope = {
        "level": (
            "PACK_STRUCTURAL_AND_CONTENT_HASH_VALIDATION_OF_"
            "UPSTREAM_SINGLE_LOOK_SEMANTIC_RECOMPUTATION_RECEIPT"
        ),
        "settlement_database_reloaded_by_pack": False,
        "settlement_chain_independently_replayed_by_pack": False,
        "full_forward_rows_hash_bound": True,
        "first_joint_maturity_prefix_hash_bound": True,
        "single_look_decision_hash_bound": True,
        "statistical_stage_hash_bound": True,
        "risk_acceptance_hash_bound": True,
        "later_settlements_descriptive_only": True,
    }
    if scope != expected_scope:
        blockers.append("forward_evidence_v2_validation_scope_invalid")

    candidate = dict(payload.get("candidate") or {})
    spec = dict(candidate.get("spec") or {})
    computed_spec_hash = canonical_hash(spec)
    candidate_hash = str(candidate.get("candidate_hash") or "")
    if not candidate_hash:
        blockers.append("forward_evidence_v2_candidate_hash_missing")
    if str(candidate.get("computed_spec_hash") or "") != computed_spec_hash:
        blockers.append("forward_evidence_v2_computed_spec_hash_invalid")
    declared_spec_hash = str(candidate.get("declared_spec_hash") or "")
    if declared_spec_hash and declared_spec_hash != computed_spec_hash:
        blockers.append("forward_evidence_v2_declared_spec_hash_mismatch")

    historical = dict(payload.get("historical_statistical_contract_source") or {})
    historical_config = dict(historical.get("config") or {})
    historical_binding = dict(historical.get("input_binding") or {})
    historical_semantic = dict(historical.get("semantic_verification") or {})
    if historical.get("schema_version") != PORTFOLIO_STATISTICAL_AUDIT_SCHEMA_VERSION:
        blockers.append("forward_evidence_v2_historical_schema_invalid")
    if historical.get("claim_status") not in {"PASS", "BLOCK"}:
        blockers.append("forward_evidence_v2_historical_claim_status_invalid")
    if historical.get("artifact_verification_status") != "PASS":
        blockers.append("forward_evidence_v2_historical_artifact_not_verified")
    if historical_semantic.get("status") != "PASS":
        blockers.append("forward_evidence_v2_historical_semantics_not_verified")
    if historical_semantic.get("recomputed_from_frozen_research") is not True:
        blockers.append("forward_evidence_v2_historical_semantics_not_recomputed")
    if str(historical_semantic.get("expected_audit_hash") or "") != str(
        historical.get("audit_hash") or ""
    ):
        blockers.append("forward_evidence_v2_historical_semantic_identity_mismatch")
    if canonical_hash(historical_config) != str(historical.get("config_hash") or ""):
        blockers.append("forward_evidence_v2_historical_config_hash_invalid")
    if canonical_hash(historical_binding) != str(historical.get("input_binding_hash") or ""):
        blockers.append("forward_evidence_v2_historical_binding_projection_hash_invalid")
    historical_binding_hash = str(historical_binding.get("binding_hash") or "")
    historical_binding_content = dict(historical_binding)
    historical_binding_content.pop("binding_hash", None)
    if (
        not historical_binding_hash
        or canonical_hash(historical_binding_content) != historical_binding_hash
    ):
        blockers.append("forward_evidence_v2_historical_binding_hash_invalid")
    if str(historical_binding.get("candidate_hash") or "") != candidate_hash:
        blockers.append("forward_evidence_v2_historical_candidate_mismatch")
    if str(historical_binding.get("spec_hash") or "") != computed_spec_hash:
        blockers.append("forward_evidence_v2_historical_spec_mismatch")
    if not str(historical.get("audit_hash") or "") or not str(
        historical.get("artifact_hash") or ""
    ):
        blockers.append("forward_evidence_v2_historical_identity_missing")
    for field in (
        "periods_per_year",
        "resample_count",
        "block_length",
        "minimum_observations",
        "selection_trial_count",
    ):
        if _v2_native_integer(historical_config.get(field), minimum=1) is None:
            blockers.append(f"forward_evidence_v2_historical_safe_integer_invalid:{field}")
    for field in (
        "confidence_level",
        "required_positive_probability",
        "required_selection_adjusted_probability",
    ):
        probability = _v2_native_number(historical_config.get(field))
        if probability is None or probability < 0.5 or probability > 1.0:
            blockers.append(f"forward_evidence_v2_historical_probability_invalid:{field}")
    trial_count = spec.get("trial_count")
    if trial_count is None:
        trial_count = candidate.get("development_trial_count")
    if (
        _v2_native_integer(trial_count, minimum=1) is None
        or historical_config.get("selection_trial_count") != trial_count
    ):
        blockers.append("forward_evidence_v2_historical_trial_count_invalid")

    performance = dict(payload.get("performance_summary") or {})
    if performance.get("status") != "PASS":
        blockers.append("forward_evidence_v2_performance_summary_not_passed")
    if str(performance.get("candidate_hash") or "") != candidate_hash:
        blockers.append("forward_evidence_v2_performance_candidate_mismatch")
    performance_counts = {
        field: _v2_native_integer(performance.get(field))
        for field in (
            "settlement_count",
            "outcome_period_count",
            "rebalance_execution_count",
        )
    }
    if any(value is None for value in performance_counts.values()):
        blockers.append("forward_evidence_v2_performance_counts_invalid")
    if performance.get("execution_authority_violation_count") != 0:
        blockers.append("forward_evidence_v2_performance_authority_count_invalid")
    if list(performance.get("unsettled_observation_dates") or []):
        blockers.append("forward_evidence_v2_performance_unsettled_observations")

    audit = dict(payload.get("forward_statistical_audit") or {})
    audit_binding = dict(audit.get("input_binding") or {})
    audit_maturity = dict(audit.get("maturity") or {})
    contract = dict(audit.get("statistical_contract") or {})
    contract_comparison = dict(audit.get("contract_comparison") or {})
    series = dict(audit.get("series_evidence") or {})
    stage = dict(audit.get("stage") or {})
    decision = dict(audit.get("decision_window") or {})
    prefix = dict(decision.get("first_joint_maturity_prefix") or {})
    risk = dict(decision.get("risk_acceptance") or {})
    if audit.get("schema_version") != PORTFOLIO_FORWARD_STATISTICAL_AUDIT_V2_SCHEMA_VERSION:
        blockers.append("forward_evidence_v2_audit_schema_invalid")
    if _v2_native_integer(audit.get("generated_at"), minimum=1) is None:
        blockers.append("forward_evidence_v2_audit_generated_at_invalid")
    if audit.get("verification_status") != "PASS":
        blockers.append("forward_evidence_v2_audit_not_verified")
    if audit.get("semantic_recomputed") is not True:
        blockers.append("forward_evidence_v2_audit_not_semantically_recomputed")
    if audit.get("verification_blockers"):
        blockers.append("forward_evidence_v2_audit_verification_blockers_present")
    if canonical_hash(forward_statistical_audit_v2_content(audit)) != str(
        audit.get("audit_hash") or ""
    ):
        blockers.append("forward_evidence_v2_audit_hash_invalid")
    if not _forward_series_hash_valid(series):
        blockers.append("forward_evidence_v2_full_series_hash_invalid")
    if authority_violations(audit):
        blockers.append("forward_evidence_v2_audit_contains_execution_authority")
    series_rows_value = series.get("rows")
    series_rows = list(series_rows_value) if isinstance(series_rows_value, list) else []
    series_counts = {
        field: _v2_native_integer(series.get(field))
        for field in (
            "settlement_count",
            "outcome_period_count",
            "rebalance_execution_count",
        )
    }
    if not isinstance(series_rows_value, list):
        blockers.append("forward_evidence_v2_full_series_rows_invalid")
    if (
        series_counts["settlement_count"] != len(series_rows)
        or series_counts["outcome_period_count"] != max(len(series_rows) - 1, 0)
        or series_counts["rebalance_execution_count"]
        != sum(
            int(isinstance(item, dict) and item.get("rebalance_executed") is True)
            for item in series_rows
        )
    ):
        blockers.append("forward_evidence_v2_full_series_counts_invalid")
    if str(series.get("candidate_hash") or "") != candidate_hash:
        blockers.append("forward_evidence_v2_full_series_candidate_mismatch")
    ordered_hashes = [
        str(item.get("settlement_hash") or "")
        for item in series_rows
        if isinstance(item, dict)
    ]
    if list(series.get("ordered_settlement_hashes") or []) != ordered_hashes:
        blockers.append("forward_evidence_v2_full_series_ordered_hashes_invalid")
    if series_rows:
        first_row = dict(series_rows[0]) if isinstance(series_rows[0], dict) else {}
        last_row = dict(series_rows[-1]) if isinstance(series_rows[-1], dict) else {}
        if (
            str(series.get("first_settlement_date") or "")
            != str(first_row.get("date") or "")
            or str(series.get("last_settlement_date") or "")
            != str(last_row.get("date") or "")
            or str(series.get("first_settlement_hash") or "")
            != str(first_row.get("settlement_hash") or "")
            or str(series.get("latest_settlement_hash") or "")
            != str(last_row.get("settlement_hash") or "")
        ):
            blockers.append("forward_evidence_v2_full_series_endpoints_invalid")

    if not _v2_hash_field_valid(audit_binding, "binding_hash"):
        blockers.append("forward_evidence_v2_audit_binding_hash_invalid")
    if str(audit_binding.get("candidate_hash") or "") != candidate_hash:
        blockers.append("forward_evidence_v2_audit_candidate_mismatch")
    if str(audit_binding.get("candidate_spec_hash") or "") != computed_spec_hash:
        blockers.append("forward_evidence_v2_audit_spec_mismatch")
    if str(audit_binding.get("candidate_declared_spec_hash") or "") != declared_spec_hash:
        blockers.append("forward_evidence_v2_audit_declared_spec_mismatch")
    if str(audit_binding.get("historical_statistical_audit_hash") or "") != str(
        historical.get("audit_hash") or ""
    ):
        blockers.append("forward_evidence_v2_audit_historical_identity_mismatch")
    if str(audit_binding.get("historical_statistical_artifact_hash") or "") != str(
        historical.get("artifact_hash") or ""
    ):
        blockers.append("forward_evidence_v2_audit_historical_artifact_mismatch")
    if str(audit_binding.get("historical_statistical_config_hash") or "") != str(
        historical.get("config_hash") or ""
    ):
        blockers.append("forward_evidence_v2_audit_historical_config_mismatch")
    if str(audit_binding.get("historical_statistical_input_binding_hash") or "") != (
        historical_binding_hash
    ):
        blockers.append("forward_evidence_v2_audit_historical_binding_mismatch")
    if str(audit_binding.get("forward_series_hash") or "") != str(
        series.get("series_hash") or ""
    ):
        blockers.append("forward_evidence_v2_audit_full_series_mismatch")
    if str(audit_binding.get("ordered_settlement_hashes_hash") or "") != canonical_hash(
        list(series.get("ordered_settlement_hashes") or [])
    ):
        blockers.append("forward_evidence_v2_audit_ordered_hashes_mismatch")
    for field in (
        "settlement_count",
        "outcome_period_count",
        "rebalance_execution_count",
    ):
        if (
            audit_binding.get(field) != series.get(field)
            or audit_binding.get(field) != performance.get(field)
        ):
            blockers.append(f"forward_evidence_v2_full_series_count_mismatch:{field}")
    for binding_field, series_field in (
        ("first_settlement_date", "first_settlement_date"),
        ("last_settlement_date", "last_settlement_date"),
        ("first_settlement_hash", "first_settlement_hash"),
        ("latest_settlement_hash", "latest_settlement_hash"),
    ):
        if str(audit_binding.get(binding_field) or "") != str(
            series.get(series_field) or ""
        ):
            blockers.append(
                f"forward_evidence_v2_full_series_endpoint_mismatch:{binding_field}"
            )
    if str(audit_binding.get("latest_settlement_hash") or "") != str(
        performance.get("latest_settlement_hash") or ""
    ):
        blockers.append("forward_evidence_v2_performance_latest_settlement_mismatch")

    contract_hash = str(contract.get("contract_hash") or "")
    contract_content = dict(contract)
    contract_content.pop("contract_hash", None)
    if not contract_hash or canonical_hash(contract_content) != contract_hash:
        blockers.append("forward_evidence_v2_contract_hash_invalid")
    if contract_comparison.get("status") != "PASS":
        blockers.append("forward_evidence_v2_contract_comparison_not_passed")
    if str(audit_binding.get("statistical_contract_hash") or "") != contract_hash:
        blockers.append("forward_evidence_v2_contract_binding_mismatch")
    if str(contract.get("source_historical_audit_hash") or "") != str(
        historical.get("audit_hash") or ""
    ):
        blockers.append("forward_evidence_v2_contract_historical_identity_mismatch")
    if str(contract.get("source_historical_artifact_hash") or "") != str(
        historical.get("artifact_hash") or ""
    ):
        blockers.append("forward_evidence_v2_contract_historical_artifact_mismatch")
    if str(contract.get("source_historical_claim_status") or "") != str(
        historical.get("claim_status") or ""
    ):
        blockers.append("forward_evidence_v2_contract_historical_claim_mismatch")

    required_outcomes = _v2_native_integer(
        audit_maturity.get("required_forward_outcomes"), minimum=1
    )
    required_rebalances = _v2_native_integer(
        audit_maturity.get("required_executed_rebalances"), minimum=1
    )
    current_outcomes = performance_counts["outcome_period_count"]
    current_rebalances = performance_counts["rebalance_execution_count"]
    expected_contract_comparison = _v2_expected_contract_comparison(
        historical_config=historical_config,
        contract=contract,
    )
    if contract.get("schema_version") != PORTFOLIO_FORWARD_STATISTICAL_CONTRACT_SCHEMA_VERSION:
        blockers.append("forward_evidence_v2_contract_schema_invalid")
    for field in _PORTFOLIO_FORWARD_V2_COPIED_CONTRACT_FIELDS:
        if contract.get(field) != historical_config.get(field):
            blockers.append(f"forward_evidence_v2_contract_copied_field_mismatch:{field}")
    if contract.get("minimum_observations") != required_outcomes:
        blockers.append("forward_evidence_v2_contract_maturity_floor_mismatch")
    if contract_comparison != expected_contract_comparison:
        blockers.append("forward_evidence_v2_contract_comparison_receipt_invalid")
    counts_valid = all(
        value is not None
        for value in (
            required_outcomes,
            required_rebalances,
            current_outcomes,
            current_rebalances,
        )
    )
    due = bool(
        counts_valid
        and current_outcomes >= required_outcomes
        and current_rebalances >= required_rebalances
    )
    expected_maturity_status = "DUE" if due else "NOT_DUE"
    if (
        audit_maturity.get("status") != expected_maturity_status
        or audit_maturity.get("forward_outcomes") != current_outcomes
        or audit_maturity.get("executed_rebalances") != current_rebalances
        or audit_maturity.get("both_thresholds_required") is not True
        or audit_maturity.get("decision_policy") != PORTFOLIO_FORWARD_DECISION_POLICY
        or audit_maturity.get("remaining_forward_outcomes")
        != max((required_outcomes or 0) - (current_outcomes or 0), 0)
        or audit_maturity.get("remaining_executed_rebalances")
        != max((required_rebalances or 0) - (current_rebalances or 0), 0)
    ):
        blockers.append("forward_evidence_v2_maturity_binding_invalid")

    expected_prefix = first_joint_maturity_prefix(
        series,
        required_forward_outcomes=required_outcomes or 0,
        required_executed_rebalances=required_rebalances or 0,
    )
    if canonical_hash(prefix) != canonical_hash(expected_prefix):
        blockers.append("forward_evidence_v2_first_due_prefix_mismatch")
    if prefix.get("status") != expected_maturity_status:
        blockers.append("forward_evidence_v2_first_due_status_mismatch")
    for field in (
        "first_due_settlement_index",
        "first_due_settlement_date",
        "first_due_settlement_hash",
    ):
        if (
            audit_binding.get(field) != prefix.get(field)
            or audit_maturity.get(field) != prefix.get(field)
        ):
            blockers.append(f"forward_evidence_v2_first_due_binding_mismatch:{field}")

    if decision.get("schema_version") != PORTFOLIO_FORWARD_DECISION_WINDOW_SCHEMA_VERSION:
        blockers.append("forward_evidence_v2_decision_schema_invalid")
    if decision.get("policy") != PORTFOLIO_FORWARD_DECISION_POLICY:
        blockers.append("forward_evidence_v2_decision_policy_invalid")
    if not _v2_hash_field_valid(decision, "decision_hash"):
        blockers.append("forward_evidence_v2_decision_hash_invalid")
    if decision.get("later_settlements_used") is not False:
        blockers.append("forward_evidence_v2_tail_used_for_frozen_decision")
    if str(decision.get("candidate_hash") or "") != candidate_hash:
        blockers.append("forward_evidence_v2_decision_candidate_mismatch")
    if str(decision.get("candidate_spec_hash") or "") != computed_spec_hash:
        blockers.append("forward_evidence_v2_decision_spec_mismatch")
    if str(decision.get("candidate_declared_spec_hash") or "") != declared_spec_hash:
        blockers.append("forward_evidence_v2_decision_declared_spec_mismatch")
    if str(decision.get("statistical_contract_hash") or "") != contract_hash:
        blockers.append("forward_evidence_v2_decision_contract_mismatch")
    if str(decision.get("stage_hash") or "") != str(stage.get("stage_hash") or ""):
        blockers.append("forward_evidence_v2_decision_stage_mismatch")
    if str(audit_binding.get("decision_hash") or "") != str(
        decision.get("decision_hash") or ""
    ):
        blockers.append("forward_evidence_v2_audit_decision_mismatch")
    expected_decision_series_hash = _v2_decision_series_hash(series, expected_prefix)
    if str(decision.get("decision_series_hash") or "") != expected_decision_series_hash:
        blockers.append("forward_evidence_v2_decision_series_hash_invalid")
    if str(audit_binding.get("decision_series_hash") or "") != expected_decision_series_hash:
        blockers.append("forward_evidence_v2_audit_decision_series_mismatch")

    risk_hash = str(risk.get("risk_hash") or "")
    if risk.get("schema_version") != PORTFOLIO_FORWARD_RISK_ACCEPTANCE_SCHEMA_VERSION:
        blockers.append("forward_evidence_v2_risk_schema_invalid")
    if not _v2_hash_field_valid(risk, "risk_hash"):
        blockers.append("forward_evidence_v2_risk_hash_invalid")
    if (
        str(decision.get("risk_acceptance_hash") or "") != risk_hash
        or str(audit_binding.get("risk_acceptance_hash") or "") != risk_hash
    ):
        blockers.append("forward_evidence_v2_risk_binding_mismatch")
    if str(risk.get("decision_series_hash") or "") != expected_decision_series_hash:
        blockers.append("forward_evidence_v2_risk_decision_series_mismatch")
    if risk.get("method") != "PREFIX_STRATEGY_EQUITY_PEAK_TO_TROUGH_MAX_DRAWDOWN":
        blockers.append("forward_evidence_v2_risk_method_invalid")
    if risk.get("comparison") != "STRICTLY_BELOW":
        blockers.append("forward_evidence_v2_risk_comparison_invalid")
    if risk.get("threshold_field") != "validation_and_test_max_drawdown_below_pct":
        blockers.append("forward_evidence_v2_risk_threshold_field_invalid")
    risk_limit = _v2_native_number(risk.get("required_max_drawdown_below_pct"))
    risk_drawdown = _v2_native_number(risk.get("prefix_max_drawdown_pct"))
    risk_checks = dict(risk.get("checks") or {})
    risk_status = str(risk.get("status") or "")
    if risk_limit is None or risk_limit <= 0.0:
        blockers.append("forward_evidence_v2_risk_limit_invalid")
    if due:
        if (
            risk.get("prefix_settlement_count") != prefix.get("settlement_count")
            or risk.get("prefix_outcome_period_count")
            != prefix.get("outcome_period_count")
            or str(risk.get("prefix_first_due_settlement_hash") or "")
            != str(prefix.get("first_due_settlement_hash") or "")
        ):
            blockers.append("forward_evidence_v2_risk_prefix_binding_invalid")
        numeric_risk_pass = bool(
            risk_drawdown is not None
            and risk_limit is not None
            and risk_drawdown >= 0.0
            and risk_drawdown < risk_limit
        )
        if risk_status == "PASS":
            risk_semantics_pass = (
                numeric_risk_pass
                and not list(risk.get("blockers") or [])
                and risk_checks.get("frozen_drawdown_limit_valid") is True
                and risk_checks.get("prefix_strategy_equity_valid") is True
                and risk_checks.get("prefix_max_drawdown_strictly_below_limit") is True
            )
        elif risk_status == "BLOCK":
            risk_semantics_pass = (
                risk_drawdown is not None
                and risk_limit is not None
                and not numeric_risk_pass
                and list(risk.get("blockers") or [])
                == ["risk_acceptance_max_drawdown_not_below_limit"]
                and risk_checks.get("frozen_drawdown_limit_valid") is True
                and risk_checks.get("prefix_strategy_equity_valid") is True
                and risk_checks.get("prefix_max_drawdown_strictly_below_limit") is False
            )
        else:
            risk_semantics_pass = False
    else:
        risk_semantics_pass = (
            risk_status == "NOT_DUE"
            and risk.get("prefix_settlement_count") == 0
            and risk.get("prefix_outcome_period_count") == 0
            and str(risk.get("prefix_first_due_settlement_hash") or "") == ""
            and risk_drawdown is None
            and not list(risk.get("blockers") or [])
            and risk_checks.get("frozen_drawdown_limit_valid") is True
            and risk_checks.get("prefix_strategy_equity_valid") is False
            and risk_checks.get("prefix_max_drawdown_strictly_below_limit") is False
        )
    if not risk_semantics_pass:
        blockers.append("forward_evidence_v2_risk_semantics_invalid")

    if not _v2_stage_receipt_consistent(stage, due=due):
        blockers.append("forward_evidence_v2_stage_receipt_semantics_invalid")

    decision_status = str(decision.get("decision_status") or "")
    research_action = str(decision.get("research_action") or "")
    if due:
        stage_observations = _v2_native_integer(stage.get("observation_count"))
        if (
            not stage
            or stage.get("status") not in {"PASS", "BLOCK"}
            or not _forward_stage_hash_valid(stage)
            or stage_observations != prefix.get("outcome_period_count")
        ):
            blockers.append("forward_evidence_v2_frozen_stage_invalid")
        decision_pass = stage.get("status") == "PASS" and risk_status == "PASS"
        expected_decision_status = "PASS" if decision_pass else "BLOCK"
        expected_action = "REVIEW_REQUIRED" if decision_pass else "STOP_RESEARCH"
        expected_audit_status = "PASS" if decision_pass else "BLOCK"
        expected_conclusion = (
            "FORWARD_FIRST_JOINT_MATURITY_RESEARCH_ACCEPTANCE_PASS"
            if decision_pass
            else "FORWARD_FIRST_JOINT_MATURITY_RESEARCH_ACCEPTANCE_FAILED"
        )
        if (
            decision.get("status") != "FROZEN"
            or decision_status != expected_decision_status
            or research_action != expected_action
            or audit.get("status") != expected_audit_status
            or audit.get("conclusion") != expected_conclusion
        ):
            blockers.append("forward_evidence_v2_frozen_decision_semantics_invalid")
        if decision_pass and list(decision.get("blockers") or []):
            blockers.append("forward_evidence_v2_pass_decision_has_blockers")
        if not decision_pass and not list(decision.get("blockers") or []):
            blockers.append("forward_evidence_v2_block_decision_missing_blockers")
    else:
        decision_pass = False
        if stage:
            blockers.append("forward_evidence_v2_not_due_stage_present")
        if (
            decision.get("status") != "NOT_DUE"
            or decision_status != "NOT_DUE"
            or research_action != "COLLECT_MORE"
            or audit.get("status") != "NOT_DUE"
            or audit.get("conclusion") != "FORWARD_STATISTICAL_AUDIT_NOT_DUE"
        ):
            blockers.append("forward_evidence_v2_not_due_decision_semantics_invalid")

    expected_decision_blockers: list[str] = []
    if due and stage.get("status") == "BLOCK":
        expected_decision_blockers.extend(
            f"natural_forward_first_joint_maturity:{item}"
            for item in list(stage.get("blockers") or [])
            or ["statistical_stage_not_passed"]
        )
    if due and risk.get("status") == "BLOCK":
        expected_decision_blockers.extend(
            f"first_joint_maturity_risk:{item}"
            for item in list(risk.get("blockers") or [])
        )
    expected_decision_blockers = list(dict.fromkeys(expected_decision_blockers))
    if list(decision.get("blockers") or []) != expected_decision_blockers:
        blockers.append("forward_evidence_v2_decision_blockers_semantics_invalid")
    if list(audit.get("blockers") or []) != expected_decision_blockers:
        blockers.append("forward_evidence_v2_audit_blockers_semantics_invalid")

    historical_contract_verified = not any(
        str(item).startswith("forward_evidence_v2_historical")
        or str(item).startswith("forward_evidence_v2_contract")
        for item in blockers
    )
    prefix_integrity_pass = not any(
        "first_due" in str(item)
        or "decision_series" in str(item)
        or "prefix" in str(item)
        for item in blockers
        if str(item).startswith("forward_evidence_v2_")
    )
    expected_audit_checks = {
        "candidate_authority_is_research_only": not payload_authority_violations,
        "forward_threshold_contract_pass": (
            required_outcomes is not None and required_rebalances is not None
        ),
        "settlement_series_integrity_pass": not any(
            "full_series" in str(item) for item in blockers
        ),
        "historical_statistical_contract_verified": historical_contract_verified,
        "same_statistical_contract_except_forward_maturity_floor": (
            contract_comparison == expected_contract_comparison
            and contract_comparison.get("status") == "PASS"
        ),
        "maturity_requires_outcomes_and_rebalances": due,
        "first_joint_maturity_prefix_integrity_pass": prefix_integrity_pass,
        "single_statistical_look_uses_frozen_prefix_only": (
            decision.get("later_settlements_used") is False
        ),
        "natural_forward_statistical_stage_pass": (
            stage.get("status") == "PASS" if due else False
        ),
        "first_joint_maturity_risk_acceptance_pass": (
            risk.get("status") == "PASS" if due else False
        ),
        "first_joint_maturity_risk_acceptance_integrity_pass": risk_semantics_pass,
        "zero_execution_authority": not payload_authority_violations,
    }
    if dict(audit.get("checks") or {}) != expected_audit_checks:
        blockers.append("forward_evidence_v2_audit_checks_semantics_invalid")

    readiness = dict(payload.get("readiness") or {})
    readiness_audit = dict(readiness.get("forward_statistical_audit") or {})
    if readiness.get("schema_version") != PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION:
        blockers.append("forward_evidence_v2_readiness_schema_invalid")
    if authority_violations(readiness):
        blockers.append("forward_evidence_v2_readiness_contains_execution_authority")
    if readiness.get("historical_statistical_claim_status") != historical.get("claim_status"):
        blockers.append("forward_evidence_v2_readiness_historical_claim_mismatch")
    for field in (
        "schema_version",
        "status",
        "conclusion",
        "audit_hash",
        "verification_status",
        "evidence_scope",
    ):
        if readiness_audit.get(field) != audit.get(field):
            blockers.append(f"forward_evidence_v2_readiness_audit_mismatch:{field}")
    if list(readiness_audit.get("verification_blockers") or []) != list(
        audit.get("verification_blockers") or []
    ):
        blockers.append(
            "forward_evidence_v2_readiness_audit_mismatch:verification_blockers"
        )
    for field in (
        "maturity",
        "input_binding",
        "decision_window",
        "contract_comparison",
    ):
        if canonical_hash(readiness_audit.get(field)) != canonical_hash(audit.get(field)):
            blockers.append(f"forward_evidence_v2_readiness_audit_mismatch:{field}")
    if readiness.get("decision_policy") != PORTFOLIO_FORWARD_DECISION_POLICY:
        blockers.append("forward_evidence_v2_readiness_decision_policy_invalid")
    if readiness.get("decision_status") != decision_status:
        blockers.append("forward_evidence_v2_readiness_decision_status_mismatch")
    if readiness.get("research_action") != research_action:
        blockers.append("forward_evidence_v2_readiness_research_action_mismatch")
    if readiness.get("forward_statistical_audit_due_status") != expected_maturity_status:
        blockers.append("forward_evidence_v2_readiness_maturity_mismatch")
    readiness_checks = dict(readiness.get("integrity_checks") or {})
    if not readiness_checks or not all(value is True for value in readiness_checks.values()):
        blockers.append("forward_evidence_v2_readiness_integrity_not_passed")

    claim_status = "BLOCK"
    evidence_blockers: list[str] = []
    if not blockers:
        if not due:
            if (
                readiness.get("status") == "COLLECTING"
                and readiness.get("promotion_status") == "BLOCK"
            ):
                claim_status = "COLLECTING"
                evidence_blockers.append("natural_forward_single_look_not_mature")
            else:
                blockers.append("forward_evidence_v2_collecting_state_invalid")
        elif decision_pass:
            if (
                readiness.get("status") == "RESEARCH_REVIEW_READY"
                and readiness.get("promotion_status") == "REVIEW_REQUIRED"
            ):
                claim_status = "RESEARCH_REVIEW_READY"
            else:
                blockers.append("forward_evidence_v2_ready_state_invalid")
        else:
            if (
                readiness.get("status") == "RESEARCH_REVIEW_BLOCKED"
                and readiness.get("promotion_status") == "BLOCK"
            ):
                claim_status = "RESEARCH_REVIEW_BLOCKED"
                evidence_blockers.append("natural_forward_single_look_decision_blocked")
            else:
                blockers.append("forward_evidence_v2_blocked_state_invalid")
    if blockers:
        claim_status = "BLOCK"
        evidence_blockers = ["natural_forward_single_look_integrity_blocked"]
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "source_integrity_status": "PASS" if not blockers else "BLOCK",
        "forward_evidence_status": claim_status,
        "evidence_blockers": evidence_blockers,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _verify_forward_promotion_evidence_v2(
    projection: dict[str, Any],
) -> dict[str, Any]:
    payload = dict(projection or {})
    expected_projection_hash = str(payload.get("projection_hash") or "")
    projection_content = dict(payload)
    projection_content.pop("projection_hash", None)
    hash_valid = bool(expected_projection_hash) and (
        canonical_hash(projection_content) == expected_projection_hash
    )
    semantic_content = dict(projection_content)
    declared_integrity = str(semantic_content.pop("source_integrity_status", "") or "")
    declared_status = str(semantic_content.pop("forward_evidence_status", "") or "")
    declared_blockers = list(semantic_content.pop("blockers", []) or [])
    semantic = _evaluate_forward_promotion_evidence_v2(semantic_content)
    blockers: list[str] = []
    if not hash_valid:
        blockers.append("forward_evidence_v2_projection_hash_invalid")
    if declared_integrity != semantic.get("source_integrity_status"):
        blockers.append("forward_evidence_v2_source_integrity_status_inconsistent")
    if declared_status != semantic.get("forward_evidence_status"):
        blockers.append("forward_evidence_v2_status_inconsistent")
    if declared_blockers != list(semantic.get("evidence_blockers") or []):
        blockers.append("forward_evidence_v2_blockers_inconsistent")
    return {
        **semantic,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "source_blockers": list(semantic.get("blockers") or []),
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def project_internal_forward_evidence(
    *,
    candidate: dict[str, Any],
    statistical: dict[str, Any],
    statistical_verification: dict[str, Any],
    performance: dict[str, Any],
    schema_version: str = CURRENT_PORTFOLIO_INTERNAL_FORWARD_EVIDENCE_SCHEMA_VERSION,
) -> dict[str, Any]:
    """Pure versioned projection; v2 is current and v1 stays explicit legacy."""

    if schema_version == PORTFOLIO_INTERNAL_FORWARD_EVIDENCE_SCHEMA_VERSION:
        return _project_forward_promotion_evidence(
            candidate=candidate,
            statistical=statistical,
            statistical_verification=statistical_verification,
            performance=performance,
        )
    if schema_version == PORTFOLIO_INTERNAL_FORWARD_EVIDENCE_V2_SCHEMA_VERSION:
        return _project_forward_promotion_evidence_v2(
            candidate=candidate,
            statistical=statistical,
            statistical_verification=statistical_verification,
            performance=performance,
        )
    raise ValueError(f"unsupported internal forward evidence schema: {schema_version}")


def verify_internal_forward_evidence(projection: dict[str, Any]) -> dict[str, Any]:
    """Pure fail-closed verifier for a declared forward evidence version."""

    def blocked(blocker: str) -> dict[str, Any]:
        return {
            "status": "BLOCK",
            "blockers": [blocker],
            "source_blockers": [blocker],
            "source_integrity_status": "BLOCK",
            "forward_evidence_status": "BLOCK",
            "evidence_blockers": ["natural_forward_single_look_integrity_blocked"],
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    if not isinstance(projection, Mapping):
        return blocked("internal_forward_evidence_payload_not_object")
    try:
        schema_version = str(dict(projection).get("schema_version") or "")
        if schema_version == PORTFOLIO_INTERNAL_FORWARD_EVIDENCE_SCHEMA_VERSION:
            return _verify_forward_promotion_evidence(dict(projection))
        if schema_version == PORTFOLIO_INTERNAL_FORWARD_EVIDENCE_V2_SCHEMA_VERSION:
            return _verify_forward_promotion_evidence_v2(dict(projection))
        return blocked("internal_forward_evidence_schema_invalid")
    except MemoryError:
        return blocked("internal_forward_evidence_verification_memory_exhausted")
    except Exception:
        return blocked("internal_forward_evidence_verification_unexpected_error")


def _assemble_internal_backtest_pack_v3(
    evidence: dict[str, Any],
    *,
    generated_at: int,
) -> dict[str, Any]:
    legacy = _assemble_internal_backtest_pack_v2(evidence, generated_at=generated_at)
    payload = deepcopy(legacy)
    payload.pop("pack_hash", None)
    payload.pop("evidence_hash", None)
    payload["schema_version"] = PORTFOLIO_INTERNAL_BACKTEST_PACK_V3_SCHEMA_VERSION
    candidate = dict((evidence.get("active") or {}).get("candidate") or {})
    statistical = dict(evidence.get("statistical") or {})
    performance = dict(evidence.get("performance") or {})
    statistical_verification = dict((legacy.get("verifications") or {}).get("statistical_audit") or {})
    forward_projection = _project_forward_promotion_evidence(
        candidate=candidate,
        statistical=statistical,
        statistical_verification=statistical_verification,
        performance=performance,
    )
    forward_verification = _verify_forward_promotion_evidence(forward_projection)
    forward_status = str(forward_verification.get("forward_evidence_status") or "BLOCK")
    payload["candidate"]["spec"] = deepcopy(dict(candidate.get("spec") or {}))
    payload["candidate"]["declared_spec_hash"] = str(candidate.get("spec_hash") or "")
    payload["candidate"]["computed_spec_hash"] = canonical_hash(dict(candidate.get("spec") or {}))
    payload["forward_promotion_evidence"] = forward_projection
    payload["forward_evidence_status"] = forward_status
    payload["checks"]["forward_statistical_evidence_source_integrity_pass"] = (
        forward_verification.get("source_integrity_status") == "PASS"
    )
    if forward_verification.get("source_integrity_status") != "PASS":
        payload["blockers"].extend(
            f"forward_statistical_evidence:{item}"
            for item in forward_verification.get("source_blockers") or ["source_integrity_blocked"]
        )
    payload["blockers"] = list(dict.fromkeys(payload["blockers"]))
    internal_ready = bool(payload.get("checks")) and all(
        bool(value) for value in dict(payload.get("checks") or {}).values()
    ) and not payload["blockers"]
    payload["status"] = (
        "INTERNAL_BACKTEST_EVIDENCE_READY"
        if internal_ready
        else "INTERNAL_BACKTEST_BLOCKED"
    )

    # Readiness v2 blockers stay hash-bound and are semantically checked inside
    # the projection. V3 publishes only its versioned outcome, so legacy gate
    # names cannot silently become a second promotion policy.
    promotion_blockers = list(forward_verification.get("evidence_blockers") or [])
    if not internal_ready:
        promotion_blockers.append("internal_backtest_evidence_ready")
    payload["promotion_blockers"] = list(dict.fromkeys(promotion_blockers))
    ready_for_review = (
        internal_ready
        and forward_status == "RESEARCH_REVIEW_READY"
        and not payload["promotion_blockers"]
    )
    payload["promotion_status"] = "REVIEW_REQUIRED" if ready_for_review else "BLOCK"
    payload["manual_review_required"] = True
    payload["profitability_proven"] = False
    payload["performance_claim_proven"] = False
    payload["parameter_selection_allowed"] = False
    payload["automatic_paper_activation_allowed"] = False
    payload["research_only"] = True
    payload["paper_authorized"] = False
    payload["live_order_allowed"] = False
    evidence_content = deepcopy(payload)
    evidence_content.pop("generated_at", None)
    payload["evidence_hash"] = canonical_hash(evidence_content)
    payload["pack_hash"] = canonical_hash(payload)
    return payload


def _assemble_internal_backtest_pack_v4(
    evidence: dict[str, Any],
    *,
    generated_at: int,
) -> dict[str, Any]:
    payload = _assemble_internal_backtest_pack_v3(evidence, generated_at=generated_at)
    payload.pop("pack_hash", None)
    payload.pop("evidence_hash", None)
    payload["schema_version"] = PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION

    active = dict(evidence.get("active") or {})
    candidate = dict(active.get("candidate") or {})
    research = dict(evidence.get("research") or {})
    statistical = dict(evidence.get("statistical") or {})
    research_artifact = dict(evidence.get("research_artifact") or {})
    research_source_document = dict(evidence.get("research_source_document") or {})
    source_evidence = _project_return_quality_source_evidence(
        candidate=candidate,
        research=research,
        statistical=statistical,
        research_artifact=research_artifact,
        registry=dict(active.get("registry") or {}),
        research_source_document=research_source_document,
    )
    source_verification = _verify_return_quality_source_evidence(source_evidence)
    source_integrity_pass = (
        source_verification.get("status") == "PASS"
        and source_verification.get("source_integrity_status") == "PASS"
    )
    payload["candidate"]["research_report_hash"] = str(
        candidate.get("research_report_hash") or ""
    )
    payload["return_quality_source_evidence"] = source_evidence
    payload["return_quality"] = build_backtest_return_quality_projection(
        dict(source_evidence.get("research") or {}),
        dict(source_evidence.get("statistical") or {}),
        schema_version=BACKTEST_RETURN_QUALITY_V2_SCHEMA_VERSION,
        source_identity=dict(source_evidence.get("source_identity") or {}),
        source_evidence_hash=str(source_evidence.get("source_evidence_hash") or ""),
        verified_source_integrity_status=str(
            source_verification.get("source_integrity_status") or "BLOCK"
        ),
        verified_source_integrity_blockers=list(
            source_verification.get("source_blockers") or []
        ),
    )
    payload["checks"]["return_quality_source_integrity_pass"] = source_integrity_pass
    payload["blockers"] = [
        item
        for item in list(payload.get("blockers") or [])
        if not str(item).startswith("return_quality_source:")
    ]
    if not source_integrity_pass:
        payload["blockers"].extend(
            f"return_quality_source:{item}"
            for item in source_verification.get("source_blockers")
            or source_verification.get("blockers")
            or ["source_integrity_blocked"]
        )
    payload["blockers"] = list(dict.fromkeys(payload["blockers"]))
    internal_ready = bool(payload.get("checks")) and all(
        bool(value) for value in dict(payload.get("checks") or {}).values()
    ) and not payload["blockers"]
    payload["status"] = (
        "INTERNAL_BACKTEST_EVIDENCE_READY"
        if internal_ready
        else "INTERNAL_BACKTEST_BLOCKED"
    )
    promotion_blockers = [
        item
        for item in list(payload.get("promotion_blockers") or [])
        if item != "internal_backtest_evidence_ready"
    ]
    if not internal_ready:
        promotion_blockers.append("internal_backtest_evidence_ready")
    payload["promotion_blockers"] = list(dict.fromkeys(promotion_blockers))
    ready_for_review = (
        internal_ready
        and payload.get("forward_evidence_status") == "RESEARCH_REVIEW_READY"
        and not payload["promotion_blockers"]
    )
    payload["promotion_status"] = "REVIEW_REQUIRED" if ready_for_review else "BLOCK"
    evidence_content = deepcopy(payload)
    evidence_content.pop("generated_at", None)
    payload["evidence_hash"] = canonical_hash(evidence_content)
    payload["pack_hash"] = canonical_hash(payload)
    return payload


def _assemble_internal_backtest_pack_v5(
    evidence: dict[str, Any],
    *,
    generated_at: int,
    source_material: tuple[
        dict[str, Any],
        dict[str, Any],
        list[dict[str, Any]],
    ]
    | None = None,
) -> dict[str, Any]:
    payload = _assemble_internal_backtest_pack_v3(evidence, generated_at=generated_at)
    payload.pop("pack_hash", None)
    payload.pop("evidence_hash", None)
    payload["schema_version"] = PORTFOLIO_INTERNAL_BACKTEST_PACK_V5_SCHEMA_VERSION
    manifest, quality, _artifacts = source_material or _build_v5_source_material(evidence)
    candidate = dict((evidence.get("active") or {}).get("candidate") or {})
    payload["candidate"]["research_report_hash"] = str(
        candidate.get("research_report_hash") or ""
    )
    payload["return_quality_source_manifest"] = manifest
    payload["return_quality"] = quality
    source_integrity_pass = (
        manifest.get("source_integrity_status") == "PASS"
        and quality.get("source_integrity_status") == "PASS"
    )
    payload["checks"]["return_quality_source_integrity_pass"] = source_integrity_pass
    payload["blockers"] = [
        item
        for item in list(payload.get("blockers") or [])
        if not str(item).startswith("return_quality_source:")
    ]
    if not source_integrity_pass:
        payload["blockers"].extend(
            f"return_quality_source:{item}"
            for item in list(manifest.get("source_blockers") or [])
            or ["source_integrity_blocked"]
        )
    payload["blockers"] = list(dict.fromkeys(payload["blockers"]))
    internal_ready = bool(payload.get("checks")) and all(
        bool(value) for value in dict(payload.get("checks") or {}).values()
    ) and not payload["blockers"]
    payload["status"] = (
        "INTERNAL_BACKTEST_EVIDENCE_READY"
        if internal_ready
        else "INTERNAL_BACKTEST_BLOCKED"
    )
    promotion_blockers = [
        item
        for item in list(payload.get("promotion_blockers") or [])
        if item != "internal_backtest_evidence_ready"
    ]
    if not internal_ready:
        promotion_blockers.append("internal_backtest_evidence_ready")
    payload["promotion_blockers"] = list(dict.fromkeys(promotion_blockers))
    payload["promotion_status"] = (
        "REVIEW_REQUIRED"
        if internal_ready
        and payload.get("forward_evidence_status") == "RESEARCH_REVIEW_READY"
        and not payload["promotion_blockers"]
        else "BLOCK"
    )
    if len(_exact_json_bytes(payload)) > MAX_PORTFOLIO_INTERNAL_BACKTEST_PACK_BYTES:
        raise ValueError("compact internal backtest pack size limit exceeded")
    evidence_content = deepcopy(payload)
    evidence_content.pop("generated_at", None)
    payload["evidence_hash"] = canonical_hash(evidence_content)
    payload["pack_hash"] = canonical_hash(payload)
    return payload


def _assemble_internal_backtest_pack_v6(
    evidence: dict[str, Any],
    *,
    generated_at: int,
    source_material: tuple[
        dict[str, Any],
        dict[str, Any],
        list[dict[str, Any]],
    ]
    | None = None,
) -> dict[str, Any]:
    """Build the current compact pack with frozen single-look evidence."""

    payload = _assemble_internal_backtest_pack_v5(
        evidence,
        generated_at=generated_at,
        source_material=source_material,
    )
    payload.pop("pack_hash", None)
    payload.pop("evidence_hash", None)
    payload["schema_version"] = PORTFOLIO_INTERNAL_BACKTEST_PACK_V6_SCHEMA_VERSION
    active = dict(evidence.get("active") or {})
    candidate = dict(active.get("candidate") or {})
    statistical = dict(evidence.get("statistical") or {})
    performance = dict(evidence.get("performance") or {})
    statistical_verification = dict(
        (payload.get("verifications") or {}).get("statistical_audit") or {}
    )
    forward_projection = _project_forward_promotion_evidence_v2(
        candidate=candidate,
        statistical=statistical,
        statistical_verification=statistical_verification,
        performance=performance,
    )
    forward_verification = _verify_forward_promotion_evidence_v2(forward_projection)
    forward_status = str(
        forward_verification.get("forward_evidence_status") or "BLOCK"
    )
    payload["forward_promotion_evidence"] = forward_projection
    payload["forward_evidence_status"] = forward_status
    payload["checks"]["forward_statistical_evidence_source_integrity_pass"] = (
        forward_verification.get("source_integrity_status") == "PASS"
    )
    payload["blockers"] = [
        item
        for item in list(payload.get("blockers") or [])
        if not str(item).startswith("forward_statistical_evidence:")
    ]
    if forward_verification.get("source_integrity_status") != "PASS":
        payload["blockers"].extend(
            f"forward_statistical_evidence:{item}"
            for item in forward_verification.get("source_blockers")
            or ["source_integrity_blocked"]
        )
    payload["blockers"] = list(dict.fromkeys(payload["blockers"]))
    internal_ready = bool(payload.get("checks")) and all(
        bool(value) for value in dict(payload.get("checks") or {}).values()
    ) and not payload["blockers"]
    payload["status"] = (
        "INTERNAL_BACKTEST_EVIDENCE_READY"
        if internal_ready
        else "INTERNAL_BACKTEST_BLOCKED"
    )
    promotion_blockers = list(forward_verification.get("evidence_blockers") or [])
    if not internal_ready:
        promotion_blockers.append("internal_backtest_evidence_ready")
    payload["promotion_blockers"] = list(dict.fromkeys(promotion_blockers))
    payload["promotion_status"] = (
        "REVIEW_REQUIRED"
        if internal_ready
        and forward_status == "RESEARCH_REVIEW_READY"
        and not payload["promotion_blockers"]
        else "BLOCK"
    )
    if len(_exact_json_bytes(payload)) > MAX_PORTFOLIO_INTERNAL_BACKTEST_PACK_BYTES:
        raise ValueError("compact internal backtest pack size limit exceeded")
    evidence_content = deepcopy(payload)
    evidence_content.pop("generated_at", None)
    payload["evidence_hash"] = canonical_hash(evidence_content)
    payload["pack_hash"] = canonical_hash(payload)
    return payload


def assemble_internal_backtest_pack(
    evidence: dict[str, Any],
    *,
    generated_at: int,
    schema_version: str = CURRENT_PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION,
) -> dict[str, Any]:
    if schema_version == PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION:
        return _assemble_internal_backtest_pack_v2(evidence, generated_at=generated_at)
    if schema_version == PORTFOLIO_INTERNAL_BACKTEST_PACK_V3_SCHEMA_VERSION:
        return _assemble_internal_backtest_pack_v3(evidence, generated_at=generated_at)
    if schema_version == PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION:
        return _assemble_internal_backtest_pack_v4(evidence, generated_at=generated_at)
    if schema_version == PORTFOLIO_INTERNAL_BACKTEST_PACK_V5_SCHEMA_VERSION:
        return _assemble_internal_backtest_pack_v5(evidence, generated_at=generated_at)
    if schema_version == CURRENT_PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION:
        return _assemble_internal_backtest_pack_v6(evidence, generated_at=generated_at)
    raise ValueError(f"unsupported internal backtest pack schema: {schema_version}")


def build_internal_backtest_pack(
    report_dir: Path | str,
    *,
    generated_at: int | None = None,
    schema_version: str = CURRENT_PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION,
) -> dict[str, Any]:
    stamp = int(generated_at if generated_at is not None else time.time() * 1000)
    evidence = collect_internal_backtest_evidence(
        report_dir,
        now_ms=stamp,
        include_legacy_research_source_document=(
            schema_version
            not in {
                PORTFOLIO_INTERNAL_BACKTEST_PACK_V5_SCHEMA_VERSION,
                CURRENT_PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION,
            }
        ),
    )
    return assemble_internal_backtest_pack(
        evidence,
        generated_at=stamp,
        schema_version=schema_version,
    )


def _verify_internal_backtest_pack_hashes(pack: dict[str, Any]) -> tuple[list[str], str, str]:
    payload = dict(pack or {})
    expected_hash = str(payload.pop("pack_hash", "") or "")
    blockers: list[str] = []
    if not expected_hash or canonical_hash(payload) != expected_hash:
        blockers.append("backtest_pack_hash_invalid")
    expected_evidence_hash = str(payload.pop("evidence_hash", "") or "")
    evidence_payload = dict(payload)
    evidence_payload.pop("generated_at", None)
    if not expected_evidence_hash or canonical_hash(evidence_payload) != expected_evidence_hash:
        blockers.append("backtest_pack_evidence_hash_invalid")
    return blockers, expected_hash, expected_evidence_hash


_FORWARD_PROGRESS_INTEGER_FIELDS = (
    "observations",
    "required_observations",
    "outcome_periods",
    "required_outcome_periods",
    "executed_rebalances",
    "required_executed_rebalances",
)


def _verify_forward_progress_contract(pack: dict[str, Any]) -> list[str]:
    """Reject resealed progress values that were only valid after projection casts.

    The pack is a frozen artifact, so its published progress must already be a
    native, non-negative integer.  We intentionally leave a missing field
    compatible with older hand-built v2 fixtures; when the field is present,
    every published count is checked before status or promotion is trusted.
    """

    if "forward_progress" not in pack:
        return []
    progress = pack.get("forward_progress")
    if not isinstance(progress, dict):
        return ["backtest_pack_forward_progress_contract_invalid"]
    blockers: list[str] = []
    for field in _FORWARD_PROGRESS_INTEGER_FIELDS:
        value = progress.get(field)
        if type(value) is not int or value < 0:
            blockers.append(f"backtest_pack_forward_progress_type_invalid:{field}")
    scheduler_health = progress.get("scheduler_health")
    if not isinstance(scheduler_health, str) or not scheduler_health:
        blockers.append("backtest_pack_forward_progress_type_invalid:scheduler_health")
    return blockers


def _verify_internal_backtest_pack_v2(pack: dict[str, Any]) -> dict[str, Any]:
    blockers, expected_hash, expected_evidence_hash = _verify_internal_backtest_pack_hashes(pack)
    blockers.extend(_verify_forward_progress_contract(pack))
    if pack.get("schema_version") != PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION:
        blockers.append("backtest_pack_schema_invalid")
    checks = dict(pack.get("checks") or {})
    declared_blockers = list(pack.get("blockers") or [])
    expected_status = (
        "INTERNAL_BACKTEST_EVIDENCE_READY"
        if checks and all(bool(value) for value in checks.values()) and not declared_blockers
        else "INTERNAL_BACKTEST_BLOCKED"
    )
    if pack.get("status") != expected_status:
        blockers.append("backtest_pack_status_inconsistent")
    promotion_blockers = list(pack.get("promotion_blockers") or [])
    expected_promotion = (
        "PASS"
        if expected_status == "INTERNAL_BACKTEST_EVIDENCE_READY" and not promotion_blockers
        else "BLOCK"
    )
    if pack.get("promotion_status") != expected_promotion:
        blockers.append("backtest_pack_promotion_status_inconsistent")
    if str(pack.get("source_mode") or "") != "FROZEN_ARTIFACT_VERIFICATION_ONLY":
        blockers.append("backtest_pack_source_mode_invalid")
    if pack.get("parameter_selection_allowed") is not False:
        blockers.append("backtest_pack_parameter_selection_not_blocked")
    if pack.get("automatic_paper_activation_allowed") is not False:
        blockers.append("backtest_pack_automatic_activation_not_blocked")
    if pack.get("research_only") is not True:
        blockers.append("backtest_pack_not_research_only")
    if authority_violations(pack):
        blockers.append("backtest_pack_contains_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "expected_hash": expected_hash,
        "expected_evidence_hash": expected_evidence_hash,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _verify_internal_backtest_pack_v3_contract(
    pack: dict[str, Any],
    *,
    expected_schema_version: str,
    forward_verifier: Callable[[dict[str, Any]], dict[str, Any]] = (
        _verify_forward_promotion_evidence
    ),
) -> dict[str, Any]:
    blockers, expected_hash, expected_evidence_hash = _verify_internal_backtest_pack_hashes(pack)
    blockers.extend(_verify_forward_progress_contract(pack))
    if pack.get("schema_version") != expected_schema_version:
        blockers.append("backtest_pack_schema_invalid")
    checks = dict(pack.get("checks") or {})
    declared_blockers = list(pack.get("blockers") or [])
    expected_status = (
        "INTERNAL_BACKTEST_EVIDENCE_READY"
        if checks and all(bool(value) for value in checks.values()) and not declared_blockers
        else "INTERNAL_BACKTEST_BLOCKED"
    )
    if pack.get("status") != expected_status:
        blockers.append("backtest_pack_status_inconsistent")
    if pack.get("promotion_status") not in {"BLOCK", "REVIEW_REQUIRED"}:
        blockers.append("backtest_pack_v3_promotion_status_invalid")

    candidate = dict(pack.get("candidate") or {})
    candidate_spec = dict(candidate.get("spec") or {})
    computed_spec_hash = canonical_hash(candidate_spec)
    if str(candidate.get("computed_spec_hash") or "") != computed_spec_hash:
        blockers.append("backtest_pack_candidate_computed_spec_hash_invalid")
    declared_spec_hash = str(candidate.get("declared_spec_hash") or "")
    if declared_spec_hash and declared_spec_hash != computed_spec_hash:
        blockers.append("backtest_pack_candidate_declared_spec_hash_mismatch")

    forward_projection = dict(pack.get("forward_promotion_evidence") or {})
    projection_candidate = dict(forward_projection.get("candidate") or {})
    if str(candidate.get("candidate_hash") or "") != str(
        projection_candidate.get("candidate_hash") or ""
    ):
        blockers.append("backtest_pack_forward_candidate_hash_mismatch")
    if canonical_hash(candidate_spec) != canonical_hash(projection_candidate.get("spec") or {}):
        blockers.append("backtest_pack_forward_candidate_spec_mismatch")
    if str(candidate.get("computed_spec_hash") or "") != str(
        projection_candidate.get("computed_spec_hash") or ""
    ):
        blockers.append("backtest_pack_forward_candidate_spec_hash_mismatch")
    if str(candidate.get("declared_spec_hash") or "") != str(
        projection_candidate.get("declared_spec_hash") or ""
    ):
        blockers.append("backtest_pack_forward_candidate_declared_spec_hash_mismatch")
    forward_verification = forward_verifier(forward_projection)
    if forward_verification.get("status") != "PASS":
        blockers.extend(
            f"forward_promotion_evidence:{item}"
            for item in forward_verification.get("blockers") or ["verification_blocked"]
        )
    expected_forward_status = str(forward_verification.get("forward_evidence_status") or "BLOCK")
    if pack.get("forward_evidence_status") != expected_forward_status:
        blockers.append("backtest_pack_forward_evidence_status_inconsistent")
    expected_forward_integrity_check = forward_verification.get("source_integrity_status") == "PASS"
    if checks.get("forward_statistical_evidence_source_integrity_pass") is not expected_forward_integrity_check:
        blockers.append("backtest_pack_forward_integrity_check_inconsistent")
    expected_forward_pack_blockers = {
        f"forward_statistical_evidence:{item}"
        for item in forward_verification.get("source_blockers") or []
    }
    declared_forward_pack_blockers = {
        str(item)
        for item in declared_blockers
        if str(item).startswith("forward_statistical_evidence:")
    }
    if declared_forward_pack_blockers != expected_forward_pack_blockers:
        blockers.append("backtest_pack_forward_source_blockers_inconsistent")

    expected_promotion_blockers = list(forward_verification.get("evidence_blockers") or [])
    if expected_status != "INTERNAL_BACKTEST_EVIDENCE_READY":
        expected_promotion_blockers.append("internal_backtest_evidence_ready")
    expected_promotion_blockers = list(dict.fromkeys(expected_promotion_blockers))
    if list(pack.get("promotion_blockers") or []) != expected_promotion_blockers:
        blockers.append("backtest_pack_promotion_blockers_inconsistent")
    expected_promotion = (
        "REVIEW_REQUIRED"
        if expected_status == "INTERNAL_BACKTEST_EVIDENCE_READY"
        and expected_forward_status == "RESEARCH_REVIEW_READY"
        and not expected_promotion_blockers
        else "BLOCK"
    )
    if pack.get("promotion_status") != expected_promotion:
        blockers.append("backtest_pack_promotion_status_inconsistent")

    if str(pack.get("source_mode") or "") != "FROZEN_ARTIFACT_VERIFICATION_ONLY":
        blockers.append("backtest_pack_source_mode_invalid")
    for field, expected in (
        ("parameter_selection_allowed", False),
        ("automatic_paper_activation_allowed", False),
        ("profitability_proven", False),
        ("performance_claim_proven", False),
        ("manual_review_required", True),
        ("research_only", True),
        ("paper_authorized", False),
        ("live_order_allowed", False),
    ):
        if pack.get(field) is not expected:
            blockers.append(f"backtest_pack_v3_scope_invalid:{field}")
    if authority_violations(pack):
        blockers.append("backtest_pack_contains_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "expected_hash": expected_hash,
        "expected_evidence_hash": expected_evidence_hash,
        "forward_evidence_status": expected_forward_status,
        "promotion_status": expected_promotion,
        "profitability_proven": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _verify_internal_backtest_pack_v3(pack: dict[str, Any]) -> dict[str, Any]:
    return _verify_internal_backtest_pack_v3_contract(
        pack,
        expected_schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_V3_SCHEMA_VERSION,
    )


def _verify_internal_backtest_pack_v4(pack: dict[str, Any]) -> dict[str, Any]:
    base = _verify_internal_backtest_pack_v3_contract(
        pack,
        expected_schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
    )
    blockers = list(base.get("blockers") or [])
    checks = dict(pack.get("checks") or {})
    declared_blockers = list(pack.get("blockers") or [])
    source_evidence = dict(pack.get("return_quality_source_evidence") or {})
    source_verification = _verify_return_quality_source_evidence(source_evidence)
    if source_verification.get("status") != "PASS":
        blockers.extend(
            f"return_quality_source_evidence:{item}"
            for item in source_verification.get("blockers") or ["verification_blocked"]
        )
    source_integrity_pass = (
        source_verification.get("status") == "PASS"
        and source_verification.get("source_integrity_status") == "PASS"
    )
    if checks.get("return_quality_source_integrity_pass") is not source_integrity_pass:
        blockers.append("backtest_pack_return_quality_source_check_inconsistent")
    expected_source_pack_blockers = {
        f"return_quality_source:{item}"
        for item in source_verification.get("source_blockers") or []
    }
    declared_source_pack_blockers = {
        str(item)
        for item in declared_blockers
        if str(item).startswith("return_quality_source:")
    }
    if declared_source_pack_blockers != expected_source_pack_blockers:
        blockers.append("backtest_pack_return_quality_source_blockers_inconsistent")

    source_candidate = dict(source_evidence.get("candidate") or {})
    pack_candidate = dict(pack.get("candidate") or {})
    source_identity = dict(source_evidence.get("source_identity") or {})
    for field in ("candidate_hash", "research_report_hash"):
        pack_value = pack_candidate.get(field)
        if str(pack_value or "") != str(source_candidate.get(field) or ""):
            blockers.append(f"backtest_pack_return_quality_candidate_binding_mismatch:{field}")
    if canonical_hash(pack_candidate.get("spec") or {}) != canonical_hash(
        source_candidate.get("spec") or {}
    ):
        blockers.append("backtest_pack_return_quality_candidate_binding_mismatch:spec")
    if str(pack_candidate.get("declared_spec_hash") or "") != str(
        source_identity.get("candidate_spec_hash") or ""
    ):
        blockers.append("backtest_pack_return_quality_candidate_binding_mismatch:spec_hash")
    if str(pack_candidate.get("candidate_hash") or "") != str(
        source_identity.get("candidate_hash") or ""
    ):
        blockers.append("backtest_pack_return_quality_identity_candidate_mismatch")
    if str(pack_candidate.get("research_report_hash") or "") != str(
        source_identity.get("research_batch_run_hash") or ""
    ):
        blockers.append("backtest_pack_return_quality_identity_batch_mismatch")

    quality = dict(pack.get("return_quality") or {})
    expected_quality = build_backtest_return_quality_projection(
        dict(source_evidence.get("research") or {}),
        dict(source_evidence.get("statistical") or {}),
        schema_version=BACKTEST_RETURN_QUALITY_V2_SCHEMA_VERSION,
        source_identity=source_identity,
        source_evidence_hash=str(source_evidence.get("source_evidence_hash") or ""),
        verified_source_integrity_status=str(
            source_verification.get("source_integrity_status") or "BLOCK"
        ),
        verified_source_integrity_blockers=list(
            source_verification.get("source_blockers") or []
        ),
    )
    if quality.get("schema_version") != BACKTEST_RETURN_QUALITY_V2_SCHEMA_VERSION:
        blockers.append("backtest_pack_return_quality_schema_invalid")
    if canonical_hash(quality) != canonical_hash(expected_quality):
        blockers.append("backtest_pack_return_quality_semantic_mismatch")
    if authority_violations(quality):
        blockers.append("backtest_pack_return_quality_contains_execution_authority")

    return {
        **base,
        "status": "PASS" if not blockers else "BLOCK",
        "artifact_contract_status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "return_quality_source_integrity_status": source_verification.get(
            "source_integrity_status",
            "BLOCK",
        ),
        "return_quality_schema_version": quality.get("schema_version"),
        "profitability_proven": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _contains_v5_forbidden_large_field(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {
                "return_quality_source_evidence",
                "research_source_document",
                "source_result",
                "equity_curve",
            }:
                return True
            if _contains_v5_forbidden_large_field(child):
                return True
    elif isinstance(value, list):
        return any(_contains_v5_forbidden_large_field(item) for item in value)
    return False


def _verify_internal_backtest_pack_v5_structure(
    pack: dict[str, Any],
    *,
    expected_schema_version: str = PORTFOLIO_INTERNAL_BACKTEST_PACK_V5_SCHEMA_VERSION,
    forward_verifier: Callable[[dict[str, Any]], dict[str, Any]] = (
        _verify_forward_promotion_evidence
    ),
    compact_version_label: str = "v5",
) -> dict[str, Any]:
    base = _verify_internal_backtest_pack_v3_contract(
        pack,
        expected_schema_version=expected_schema_version,
        forward_verifier=forward_verifier,
    )
    blockers = list(base.get("blockers") or [])
    manifest_value = pack.get("return_quality_source_manifest")
    manifest = dict(manifest_value) if isinstance(manifest_value, Mapping) else {}
    if not isinstance(manifest_value, Mapping):
        blockers.append("backtest_pack_return_quality_source_manifest_not_object")
    manifest_content = dict(manifest)
    manifest_hash = str(manifest_content.pop("manifest_hash", "") or "")
    if (
        manifest.get("schema_version")
        != PORTFOLIO_RETURN_QUALITY_SOURCE_MANIFEST_SCHEMA_VERSION
    ):
        blockers.append("backtest_pack_return_quality_source_manifest_schema_invalid")
    try:
        manifest_hash_valid = bool(manifest_hash) and (
            _strict_canonical_hash(manifest_content) == manifest_hash
        )
    except (TypeError, ValueError, OverflowError, RecursionError):
        manifest_hash_valid = False
    if not manifest_hash_valid:
        blockers.append("backtest_pack_return_quality_source_manifest_hash_invalid")
    detached_file_identities: list[str] = []
    for field, role in (
        ("research_report", _DETACHED_RESEARCH_ROLE),
        ("statistical_audit", _DETACHED_STATISTICAL_ROLE),
    ):
        raw_record = manifest.get(field)
        record = dict(raw_record) if isinstance(raw_record, Mapping) else {}
        if not isinstance(raw_record, Mapping):
            blockers.append(f"backtest_pack_detached_artifact_record_invalid:{role}")
        identity = _detached_basename_identity(record.get("file"))
        if identity is None:
            blockers.append(f"backtest_pack_detached_artifact_basename_invalid:{role}")
        else:
            detached_file_identities.append(identity)
    if len(detached_file_identities) != len(set(detached_file_identities)):
        blockers.append("backtest_pack_detached_artifact_basename_identity_duplicate")
    if _contains_v5_forbidden_large_field(pack):
        blockers.append(
            f"backtest_pack_{compact_version_label}_embedded_large_source_forbidden"
        )
    try:
        if len(_exact_json_bytes(pack)) > MAX_PORTFOLIO_INTERNAL_BACKTEST_PACK_BYTES:
            blockers.append(f"backtest_pack_{compact_version_label}_size_limit_exceeded")
    except (TypeError, ValueError, OverflowError, RecursionError):
        blockers.append(f"backtest_pack_{compact_version_label}_not_canonical_json")
    if authority_violations(manifest):
        blockers.append("backtest_pack_return_quality_source_manifest_contains_execution_authority")
    quality = dict(pack.get("return_quality") or {})
    if quality.get("schema_version") != BACKTEST_RETURN_QUALITY_V3_SCHEMA_VERSION:
        blockers.append("backtest_pack_return_quality_schema_invalid")
    if str(quality.get("source_manifest_hash") or "") != manifest_hash:
        blockers.append("backtest_pack_return_quality_manifest_binding_mismatch")
    if str(quality.get("detached_source_binding_hash") or "") != str(
        manifest.get("detached_source_binding_hash") or ""
    ):
        blockers.append("backtest_pack_return_quality_detached_binding_mismatch")
    if authority_violations(quality):
        blockers.append("backtest_pack_return_quality_contains_execution_authority")
    return {
        **base,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "return_quality_schema_version": quality.get("schema_version"),
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _verify_internal_backtest_pack_v6_structure(
    pack: dict[str, Any],
) -> dict[str, Any]:
    return _verify_internal_backtest_pack_v5_structure(
        pack,
        expected_schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_V6_SCHEMA_VERSION,
        forward_verifier=_verify_forward_promotion_evidence_v2,
        compact_version_label="v6",
    )


def required_internal_backtest_bundle_members(
    pack: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    if not isinstance(pack, dict):
        return ()
    if str(pack.get("schema_version") or "") not in {
        PORTFOLIO_INTERNAL_BACKTEST_PACK_V5_SCHEMA_VERSION,
        CURRENT_PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION,
    }:
        return ()
    manifest_value = pack.get("return_quality_source_manifest")
    if not isinstance(manifest_value, Mapping):
        return ()
    manifest = dict(manifest_value)
    members: list[dict[str, Any]] = []
    for field, role in (
        ("research_report", _DETACHED_RESEARCH_ROLE),
        ("statistical_audit", _DETACHED_STATISTICAL_ROLE),
    ):
        item_value = manifest.get(field)
        if not isinstance(item_value, Mapping):
            return ()
        item = dict(item_value)
        members.append(
            {
                "role": role,
                "file": str(item.get("file") or ""),
                "sha256": str(item.get("sha256") or ""),
                "byte_length": item.get("byte_length"),
            }
        )
    return tuple(members)


def _parse_detached_bundle_artifacts(
    pack: dict[str, Any],
    detached_artifacts: Any,
) -> tuple[dict[str, tuple[dict[str, Any], bytes]], list[str]]:
    blockers: list[str] = []
    if not isinstance(detached_artifacts, (list, tuple)):
        return {}, ["detached_artifacts_invalid"]
    supplied: dict[str, dict[str, Any]] = {}
    supplied_file_identities: list[str] = []
    for raw_item in detached_artifacts:
        if not isinstance(raw_item, dict):
            blockers.append("detached_artifact_invalid")
            continue
        if set(raw_item) != {
            "role",
            "file",
            "sha256",
            "byte_length",
            "raw_bytes",
        }:
            blockers.append("detached_artifact_fields_invalid")
            continue
        role = str(raw_item.get("role") or "")
        if role not in {_DETACHED_RESEARCH_ROLE, _DETACHED_STATISTICAL_ROLE}:
            blockers.append("detached_artifact_role_invalid")
            continue
        if role in supplied:
            blockers.append(f"detached_artifact_duplicate:{role}")
            continue
        supplied[role] = raw_item
        file_identity = _detached_basename_identity(raw_item.get("file"))
        if file_identity is None:
            blockers.append(f"detached_artifact_basename_invalid:{role}")
        else:
            supplied_file_identities.append(file_identity)
    if len(supplied_file_identities) != len(set(supplied_file_identities)):
        blockers.append("detached_artifact_basename_identity_duplicate")
    parsed: dict[str, tuple[dict[str, Any], bytes]] = {}
    for required in required_internal_backtest_bundle_members(pack):
        role = str(required.get("role") or "")
        item = supplied.get(role)
        if item is None:
            blockers.append(f"detached_artifact_missing:{role}")
            continue
        raw = item.get("raw_bytes")
        if not isinstance(raw, bytes):
            blockers.append(f"detached_artifact_raw_bytes_invalid:{role}")
            continue
        limit = (
            MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES
            if role == _DETACHED_RESEARCH_ROLE
            else MAX_PORTFOLIO_STATISTICAL_AUDIT_BYTES
        )
        if len(raw) > limit:
            blockers.append(f"detached_artifact_size_limit_exceeded:{role}")
            continue
        file_name = item.get("file")
        if (
            _detached_basename_identity(file_name) is None
            or file_name != required.get("file")
        ):
            blockers.append(f"detached_artifact_file_mismatch:{role}")
        digest = hashlib.sha256(raw).hexdigest()
        if (
            item.get("byte_length") != len(raw)
            or required.get("byte_length") != len(raw)
        ):
            blockers.append(f"detached_artifact_byte_length_mismatch:{role}")
        if str(item.get("sha256") or "") != digest or str(
            required.get("sha256") or ""
        ) != digest:
            blockers.append(f"detached_artifact_sha256_mismatch:{role}")
        try:
            payload = _strict_json_object(raw)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            blockers.append(f"detached_artifact_json_invalid:{role}")
            continue
        parsed[role] = (payload, raw)
    if set(supplied) - {_DETACHED_RESEARCH_ROLE, _DETACHED_STATISTICAL_ROLE}:
        blockers.append("detached_artifact_unexpected")
    return parsed, list(dict.fromkeys(blockers))


def _verify_internal_backtest_bundle(
    pack: dict[str, Any],
    detached_artifacts: Any,
) -> dict[str, Any]:
    pack_schema = str(dict(pack or {}).get("schema_version") or "")
    if pack_schema == PORTFOLIO_INTERNAL_BACKTEST_PACK_V5_SCHEMA_VERSION:
        structure = _verify_internal_backtest_pack_v5_structure(dict(pack or {}))
    elif pack_schema == CURRENT_PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION:
        structure = _verify_internal_backtest_pack_v6_structure(dict(pack or {}))
    else:
        structure = {
            "status": "BLOCK",
            "artifact_contract_status": "BLOCK",
            "blockers": ["backtest_bundle_pack_schema_invalid"],
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    contract_blockers = list(structure.get("blockers") or [])
    parsed, artifact_blockers = _parse_detached_bundle_artifacts(
        dict(pack or {}),
        detached_artifacts,
    )
    contract_blockers.extend(artifact_blockers)
    source_blockers: list[str] = []
    source_integrity_status = "BLOCK"
    expected_quality: dict[str, Any] = {}
    if not artifact_blockers and len(parsed) == 2:
        manifest = dict(pack.get("return_quality_source_manifest") or {})
        research, research_raw = parsed[_DETACHED_RESEARCH_ROLE]
        statistical, statistical_raw = parsed[_DETACHED_STATISTICAL_ROLE]
        evidence = {
            "active": {
                "candidate": dict(manifest.get("candidate") or {}),
                "registry": dict(manifest.get("active_candidate_registry") or {}),
            },
            "research": research,
            "research_raw_bytes": research_raw,
            "research_artifact": {
                "file": dict(manifest.get("research_report") or {}).get("file"),
                "file_sha256": hashlib.sha256(research_raw).hexdigest(),
                "size": len(research_raw),
            },
            "statistical": statistical,
            "statistical_raw_bytes": statistical_raw,
            "statistical_artifact": {
                "file": dict(manifest.get("statistical_audit") or {}).get("file"),
                "file_sha256": hashlib.sha256(statistical_raw).hexdigest(),
                "size": len(statistical_raw),
            },
        }
        try:
            expected_manifest, expected_quality, _unused = _build_v5_source_material(
                evidence,
                parsed_detached_sources={
                    _DETACHED_RESEARCH_ROLE: research,
                    _DETACHED_STATISTICAL_ROLE: statistical,
                },
            )
            source_integrity_status = str(
                expected_manifest.get("source_integrity_status") or "BLOCK"
            )
            if expected_manifest.get("source_integrity_status") != "PASS":
                source_blockers.extend(
                    f"detached_source:{item}"
                    for item in list(expected_manifest.get("source_blockers") or [])
                    or ["source_integrity_blocked"]
                )
            if _strict_canonical_hash(manifest) != _strict_canonical_hash(expected_manifest):
                contract_blockers.append("detached_source_manifest_semantic_mismatch")
            if _strict_canonical_hash(dict(pack.get("return_quality") or {})) != _strict_canonical_hash(
                expected_quality
            ):
                contract_blockers.append("backtest_pack_return_quality_semantic_mismatch")
            pack_candidate = dict(pack.get("candidate") or {})
            expected_candidate = dict(manifest.get("candidate") or {})
            source_identity = dict(manifest.get("source_identity") or {})
            if str(pack_candidate.get("candidate_hash") or "") != str(
                expected_candidate.get("candidate_hash") or ""
            ):
                contract_blockers.append("backtest_pack_return_quality_candidate_binding_mismatch:candidate_hash")
            if str(pack_candidate.get("research_report_hash") or "") != str(
                expected_candidate.get("research_report_hash") or ""
            ):
                contract_blockers.append("backtest_pack_return_quality_candidate_binding_mismatch:research_report_hash")
            if _strict_canonical_hash(dict(pack_candidate.get("spec") or {})) != (
                _strict_canonical_hash(dict(expected_candidate.get("spec") or {}))
            ):
                contract_blockers.append("backtest_pack_return_quality_candidate_binding_mismatch:spec")
            if str(pack_candidate.get("declared_spec_hash") or "") != str(
                source_identity.get("candidate_spec_hash") or ""
            ):
                contract_blockers.append("backtest_pack_return_quality_candidate_binding_mismatch:spec_hash")
            if str(pack_candidate.get("candidate_hash") or "") != str(
                source_identity.get("candidate_hash") or ""
            ):
                contract_blockers.append("backtest_pack_return_quality_identity_candidate_mismatch")
            if str(pack_candidate.get("research_report_hash") or "") != str(
                source_identity.get("research_batch_run_hash") or ""
            ):
                contract_blockers.append("backtest_pack_return_quality_identity_batch_mismatch")
        except (TypeError, ValueError, OverflowError, RecursionError, UnicodeDecodeError):
            contract_blockers.append("detached_source_semantic_verification_failed")
    contract_blockers = list(dict.fromkeys(contract_blockers))
    source_blockers = list(dict.fromkeys(source_blockers))
    blockers = list(dict.fromkeys([*contract_blockers, *source_blockers]))
    quality = expected_quality if not blockers else {}
    return {
        **structure,
        "status": "PASS" if not blockers else "BLOCK",
        "artifact_contract_status": "PASS" if not contract_blockers else "BLOCK",
        "blockers": blockers,
        "return_quality_source_integrity_status": source_integrity_status,
        "return_quality": quality,
        "numeric_claims_available": bool(
            not blockers and quality.get("numeric_claims_available") is True
        ),
        "profitability_proven": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _blocked_internal_backtest_bundle_verification(blocker: str) -> dict[str, Any]:
    return {
        "status": "BLOCK",
        "artifact_contract_status": "BLOCK",
        "blockers": [blocker],
        "return_quality_source_integrity_status": "BLOCK",
        "return_quality": {},
        "numeric_claims_available": False,
        "profitability_proven": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def verify_internal_backtest_bundle(
    pack: dict[str, Any],
    detached_artifacts: Any,
) -> dict[str, Any]:
    if not isinstance(pack, dict):
        return _blocked_internal_backtest_bundle_verification(
            "backtest_bundle_pack_not_object"
        )
    try:
        return _verify_internal_backtest_bundle(pack, detached_artifacts)
    except MemoryError:
        return _blocked_internal_backtest_bundle_verification(
            "backtest_bundle_verification_memory_exhausted"
        )
    except Exception:
        return _blocked_internal_backtest_bundle_verification(
            "backtest_bundle_verification_unexpected_error"
        )


def build_internal_backtest_bundle(
    report_dir: Path | str,
    *,
    generated_at: int | None = None,
    schema_version: str = CURRENT_PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION,
) -> dict[str, Any]:
    if schema_version not in {
        PORTFOLIO_INTERNAL_BACKTEST_PACK_V5_SCHEMA_VERSION,
        CURRENT_PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION,
    }:
        raise ValueError(f"unsupported compact bundle schema: {schema_version}")
    stamp = int(generated_at if generated_at is not None else time.time() * 1000)
    evidence = collect_internal_backtest_evidence(
        report_dir,
        now_ms=stamp,
        include_legacy_research_source_document=False,
    )
    material = _build_v5_source_material(
        evidence,
        parsed_detached_sources={
            _DETACHED_RESEARCH_ROLE: dict(evidence.get("research") or {}),
            _DETACHED_STATISTICAL_ROLE: dict(evidence.get("statistical") or {}),
        },
    )
    if schema_version == CURRENT_PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION:
        pack = _assemble_internal_backtest_pack_v6(
            evidence,
            generated_at=stamp,
            source_material=material,
        )
    else:
        pack = _assemble_internal_backtest_pack_v5(
            evidence,
            generated_at=stamp,
            source_material=material,
        )
    return {
        "schema_version": PORTFOLIO_INTERNAL_BACKTEST_BUNDLE_BUILD_SCHEMA_VERSION,
        "pack": pack,
        "detached_artifacts": material[2],
    }


def verify_internal_backtest_pack(pack: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(pack, dict):
        return {
            "status": "BLOCK",
            "artifact_contract_status": "BLOCK",
            "blockers": ["backtest_pack_payload_not_object"],
            "numeric_claims_available": False,
            "profitability_proven": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    try:
        schema_version = str(pack.get("schema_version") or "")
        if schema_version == PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION:
            return _verify_internal_backtest_pack_v2(pack)
        if schema_version == PORTFOLIO_INTERNAL_BACKTEST_PACK_V3_SCHEMA_VERSION:
            return _verify_internal_backtest_pack_v3(pack)
        if schema_version == PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION:
            return _verify_internal_backtest_pack_v4(pack)
        if schema_version == PORTFOLIO_INTERNAL_BACKTEST_PACK_V5_SCHEMA_VERSION:
            result = _verify_internal_backtest_pack_v5_structure(pack)
            blockers = list(result.get("blockers") or [])
            blockers.append("detached_artifacts_required")
            return {
                **result,
                "status": "BLOCK",
                "artifact_contract_status": "BLOCK",
                "blockers": list(dict.fromkeys(blockers)),
                "numeric_claims_available": False,
                "profitability_proven": False,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        if schema_version == CURRENT_PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION:
            result = _verify_internal_backtest_pack_v6_structure(pack)
            blockers = list(result.get("blockers") or [])
            blockers.append("detached_artifacts_required")
            return {
                **result,
                "status": "BLOCK",
                "artifact_contract_status": "BLOCK",
                "blockers": list(dict.fromkeys(blockers)),
                "numeric_claims_available": False,
                "profitability_proven": False,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        blockers, expected_hash, expected_evidence_hash = _verify_internal_backtest_pack_hashes(pack)
        blockers.append("backtest_pack_schema_invalid")
        return {
            "status": "BLOCK",
            "blockers": list(dict.fromkeys(blockers)),
            "expected_hash": expected_hash,
            "expected_evidence_hash": expected_evidence_hash,
            "paper_authorized": False,
                "live_order_allowed": False,
            }
    except MemoryError:
        return {
            "status": "BLOCK",
            "artifact_contract_status": "BLOCK",
            "blockers": ["backtest_pack_verification_memory_exhausted"],
            "numeric_claims_available": False,
            "profitability_proven": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    except Exception:
        return {
            "status": "BLOCK",
            "artifact_contract_status": "BLOCK",
            "blockers": ["backtest_pack_verification_unexpected_error"],
            "numeric_claims_available": False,
            "profitability_proven": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
