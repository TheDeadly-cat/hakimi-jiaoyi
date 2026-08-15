from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any

from .strategy_research_search_lineage import normalize_search_family_id


STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-hypothesis-preregistration-v1"
)
STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2 = (
    "strategy-hypothesis-preregistration-v2"
)
STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3 = (
    "strategy-hypothesis-preregistration-v3"
)
STRATEGY_HYPOTHESIS_PREREGISTRATION_REPORT_SCHEMA_VERSION = 7
STRATEGY_HYPOTHESIS_PREREGISTRATION_SUMMARY_SCHEMA_VERSION = (
    "strategy-hypothesis-preregistration-summary-v1"
)

# This list is frozen into the v1 contract. A future retirement set must use a
# new contract schema so historical reports do not drift with current globals.
FALSIFIED_STRATEGY_IDS_V1 = ("trend_pullback", "squeeze_breakout")

_HYPOTHESIS_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")
_STRATEGY_ID = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_MECHANISM_CONDITION_ID = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
_DRAFT_FIELDS = frozenset({
    "schema_version",
    "hypothesis_id",
    "research_generation",
    "search_family_id",
    "strategy_ids",
    "mechanism_family",
    "hypothesis_statement",
    "novelty_statement",
    "mechanism_specific_failure_conditions",
    "hypothesis_hash",
})
_MAX_DRAFT_BYTES = 64 * 1024

MECHANISM_FAILURE_METRICS_V2 = frozenset({
    "validation_adjusted_score",
    "median_validation_return_pct",
    "median_validation_excess_return_pct",
    "validation_worst_drawdown_pct",
    "validation_trade_count",
    "minimum_stressed_return_pct",
    "minimum_positive_fold_count",
})
MECHANISM_FAILURE_OPERATORS_V2 = frozenset({"LT", "LTE", "GT", "GTE"})
MECHANISM_FAILURE_EVIDENCE_STAGE_V2 = "DEVELOPMENT_SELECTION"
MECHANISM_FAILURE_REQUIRED_ACTION_V2 = "BLOCK_RESEARCH"

_STANDARD_FAILURE_CONDITIONS = (
    {
        "condition_id": "parameter_plateau_absent",
        "evidence_stage": "DEVELOPMENT_SELECTION",
        "required_action": "BLOCK_RESEARCH",
    },
    {
        "condition_id": "cost_break_even_lost",
        "evidence_stage": "DEVELOPMENT_SELECTION",
        "required_action": "BLOCK_RESEARCH",
    },
    {
        "condition_id": "fixed_parameter_time_slice_instability",
        "evidence_stage": "DEVELOPMENT_SELECTION",
        "required_action": "BLOCK_RESEARCH",
    },
    {
        "condition_id": "fresh_single_use_holdout_failure",
        "evidence_stage": "PREREGISTERED_BLIND_SINGLE_USE",
        "required_action": "RETIRE_OR_NEW_REGISTRATION",
    },
    {
        "condition_id": "natural_forward_statistical_failure",
        "evidence_stage": "NATURAL_FORWARD_MATURITY",
        "required_action": "RETIRE_HYPOTHESIS",
    },
    {
        "condition_id": "implementation_or_data_identity_drift",
        "evidence_stage": "ANY",
        "required_action": "NEW_REGISTRATION_REQUIRED",
    },
)


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _text(value: Any, field: str, *, minimum: int, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"strategy_hypothesis_field_type_invalid:{field}")
    clean = " ".join(value.strip().split())
    if not minimum <= len(clean) <= maximum:
        raise ValueError(f"strategy_hypothesis_field_length_invalid:{field}")
    return clean


def _strategy_ids(value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError("strategy_hypothesis_strategy_ids_invalid")
    normalized: list[str] = []
    for raw in value:
        if not isinstance(raw, str):
            raise ValueError("strategy_hypothesis_strategy_id_type_invalid")
        strategy_id = raw.strip().lower()
        if not _STRATEGY_ID.fullmatch(strategy_id):
            raise ValueError("strategy_hypothesis_strategy_id_invalid")
        if strategy_id not in normalized:
            normalized.append(strategy_id)
    falsified = sorted(set(normalized) & set(FALSIFIED_STRATEGY_IDS_V1))
    if falsified:
        raise ValueError(
            "strategy_hypothesis_reuses_falsified_strategy_id:" + ",".join(falsified)
        )
    return normalized


def _failure_conditions(value: Any) -> list[str]:
    if not isinstance(value, list) or not 1 <= len(value) <= 8:
        raise ValueError("strategy_hypothesis_failure_conditions_invalid")
    conditions = [
        _text(item, "mechanism_specific_failure_conditions", minimum=12, maximum=240)
        for item in value
    ]
    if len(set(conditions)) != len(conditions):
        raise ValueError("strategy_hypothesis_failure_conditions_duplicate")
    return conditions


def _structured_failure_conditions(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not 1 <= len(value) <= 8:
        raise ValueError("strategy_hypothesis_mechanism_conditions_invalid")
    conditions: list[dict[str, Any]] = []
    condition_ids: list[str] = []
    required_fields = {
        "condition_id",
        "evidence_stage",
        "metric",
        "operator",
        "threshold",
        "required_action",
    }
    for raw in value:
        if not isinstance(raw, dict) or set(raw) != required_fields:
            raise ValueError("strategy_hypothesis_mechanism_condition_shape_invalid")
        condition_id = str(raw.get("condition_id") or "").strip().lower()
        if not _MECHANISM_CONDITION_ID.fullmatch(condition_id):
            raise ValueError("strategy_hypothesis_mechanism_condition_id_invalid")
        if condition_id in condition_ids:
            raise ValueError("strategy_hypothesis_mechanism_condition_id_duplicate")
        if condition_id in {
            str(item["condition_id"]) for item in _STANDARD_FAILURE_CONDITIONS
        }:
            raise ValueError("strategy_hypothesis_mechanism_condition_id_reserved")
        evidence_stage = str(raw.get("evidence_stage") or "").strip().upper()
        if evidence_stage != MECHANISM_FAILURE_EVIDENCE_STAGE_V2:
            raise ValueError("strategy_hypothesis_mechanism_evidence_stage_invalid")
        metric = str(raw.get("metric") or "").strip()
        if metric not in MECHANISM_FAILURE_METRICS_V2:
            raise ValueError("strategy_hypothesis_mechanism_metric_invalid")
        operator = str(raw.get("operator") or "").strip().upper()
        if operator not in MECHANISM_FAILURE_OPERATORS_V2:
            raise ValueError("strategy_hypothesis_mechanism_operator_invalid")
        threshold = raw.get("threshold")
        if (
            isinstance(threshold, bool)
            or not isinstance(threshold, (int, float))
            or not math.isfinite(float(threshold))
        ):
            raise ValueError("strategy_hypothesis_mechanism_threshold_invalid")
        required_action = str(raw.get("required_action") or "").strip().upper()
        if required_action != MECHANISM_FAILURE_REQUIRED_ACTION_V2:
            raise ValueError("strategy_hypothesis_mechanism_required_action_invalid")
        condition_ids.append(condition_id)
        conditions.append({
            "condition_id": condition_id,
            "evidence_stage": evidence_stage,
            "metric": metric,
            "operator": operator,
            "threshold": float(threshold),
            "required_action": required_action,
        })
    return conditions


def build_strategy_hypothesis_preregistration(draft: dict[str, Any] | Any) -> dict[str, Any]:
    """Normalize and seal a strategy hypothesis before any market-data load.

    The caller authors only mechanism-specific text. Robustness, holdout,
    natural-forward, and authority boundaries are fixed by this schema and
    cannot be weakened by the draft.
    """

    if not isinstance(draft, dict):
        raise ValueError("strategy_hypothesis_draft_type_invalid")
    unknown = sorted(set(draft) - _DRAFT_FIELDS)
    if unknown:
        raise ValueError("strategy_hypothesis_unknown_fields:" + ",".join(unknown))
    schema_version = draft.get("schema_version")
    if schema_version not in {
        STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION,
        STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2,
        STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3,
    }:
        raise ValueError("strategy_hypothesis_schema_invalid")
    hypothesis_id = _text(draft.get("hypothesis_id"), "hypothesis_id", minimum=3, maximum=96)
    if not _HYPOTHESIS_ID.fullmatch(hypothesis_id):
        raise ValueError("strategy_hypothesis_id_invalid")
    research_generation = _text(
        draft.get("research_generation"),
        "research_generation",
        minimum=2,
        maximum=96,
    )
    if schema_version == STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3:
        search_family_id: str | None = normalize_search_family_id(
            draft.get("search_family_id")
        )
    elif "search_family_id" in draft:
        raise ValueError("legacy_strategy_hypothesis_has_search_family")
    else:
        search_family_id = None
    strategy_ids = _strategy_ids(draft.get("strategy_ids"))
    mechanism_family = _text(
        draft.get("mechanism_family"),
        "mechanism_family",
        minimum=3,
        maximum=96,
    )
    hypothesis_statement = _text(
        draft.get("hypothesis_statement"),
        "hypothesis_statement",
        minimum=24,
        maximum=480,
    )
    novelty_statement = _text(
        draft.get("novelty_statement"),
        "novelty_statement",
        minimum=24,
        maximum=480,
    )
    mechanism_failures = (
        _structured_failure_conditions(
            draft.get("mechanism_specific_failure_conditions")
        )
        if schema_version in {
            STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2,
            STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3,
        }
        else _failure_conditions(
            draft.get("mechanism_specific_failure_conditions")
        )
    )

    content = {
        "schema_version": schema_version,
        "hypothesis_id": hypothesis_id,
        "research_generation": research_generation,
        "strategy_ids": strategy_ids,
        "mechanism": {
            "family": mechanism_family,
            "hypothesis_statement": hypothesis_statement,
            "novelty_statement": novelty_statement,
        },
        "parameter_robustness_contract": {
            "topology_basis": "FROZEN_VARIANT_SEQUENCE_ADJACENCY",
            "numeric_parameter_distance_claimed": False,
            "optimizer_allowed": False,
            "parameter_selection_from_projection_allowed": False,
        },
        "cost_and_time_contract": {
            "cost_stress_required": True,
            "stressed_return_must_remain_positive": True,
            "chronological_evaluation_mode": "FIXED_PARAMETER_CHRONOLOGICAL_SLICES",
            "parameters_refit_per_fold": False,
            "walk_forward_optimization_claim_allowed": False,
        },
        "holdout_and_forward_contract": {
            "fresh_single_use_holdout_required": True,
            "minimum_natural_forward_outcomes": 60,
            "minimum_executed_rebalances": 8,
            "statistical_contract_recheck_required_at_maturity": True,
            "historical_backtest_can_substitute_natural_forward": False,
        },
        "falsified_ancestry_contract": {
            "falsified_strategy_ids": list(FALSIFIED_STRATEGY_IDS_V1),
            "reuses_falsified_strategy_id": False,
            "retunes_falsified_mechanism": False,
            "material_mechanism_change_requires_new_strategy_id": True,
            "material_mechanism_change_requires_new_registration": True,
        },
        "failure_contract": {
            "mechanism_specific_conditions": mechanism_failures,
            "standard_conditions": [dict(item) for item in _STANDARD_FAILURE_CONDITIONS],
        },
        "descriptive_only": True,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "automatic_paper_activation_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    if search_family_id is not None:
        content["search_family_id"] = search_family_id
    return {**content, "hypothesis_hash": _canonical_hash(content)}


def verify_strategy_hypothesis_preregistration(
    payload: dict[str, Any] | Any,
    *,
    expected_strategy_ids: list[str] | None = None,
    expected_research_generation: str | None = None,
    expected_schema_version: str | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    if not isinstance(payload, dict):
        return {
            "status": "BLOCK",
            "blockers": ["strategy_hypothesis_type_invalid"],
            "hypothesis_hash": "",
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    mechanism = payload.get("mechanism") if isinstance(payload.get("mechanism"), dict) else {}
    failure = payload.get("failure_contract") if isinstance(payload.get("failure_contract"), dict) else {}
    draft = {
        "schema_version": payload.get("schema_version"),
        "hypothesis_id": payload.get("hypothesis_id"),
        "research_generation": payload.get("research_generation"),
        "strategy_ids": payload.get("strategy_ids"),
        "mechanism_family": mechanism.get("family"),
        "hypothesis_statement": mechanism.get("hypothesis_statement"),
        "novelty_statement": mechanism.get("novelty_statement"),
        "mechanism_specific_failure_conditions": failure.get(
            "mechanism_specific_conditions"
        ),
    }
    if (
        payload.get("schema_version")
        == STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3
    ):
        draft["search_family_id"] = payload.get("search_family_id")
    try:
        expected = build_strategy_hypothesis_preregistration(draft)
    except (TypeError, ValueError) as exc:
        blockers.append(str(exc) or "strategy_hypothesis_content_invalid")
        expected = {}
    if expected and payload != expected:
        blockers.append("strategy_hypothesis_semantic_or_hash_mismatch")
    if (
        expected_schema_version is not None
        and payload.get("schema_version") != expected_schema_version
    ):
        blockers.append("strategy_hypothesis_schema_binding_mismatch")
    if expected_strategy_ids is not None:
        normalized_expected = [
            str(item or "").strip().lower() for item in expected_strategy_ids
            if str(item or "").strip()
        ]
        if payload.get("strategy_ids") != list(dict.fromkeys(normalized_expected)):
            blockers.append("strategy_hypothesis_strategy_binding_mismatch")
    if expected_research_generation is not None and payload.get("research_generation") != str(
        expected_research_generation or ""
    ).strip():
        blockers.append("strategy_hypothesis_generation_binding_mismatch")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "hypothesis_hash": str(payload.get("hypothesis_hash") or ""),
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def load_strategy_hypothesis_preregistration(
    source_path: Path | str,
    *,
    project_root: Path | str,
) -> dict[str, Any]:
    """Safely load a small project-owned JSON draft and return its sealed form."""

    root = Path(project_root).resolve()
    candidate = Path(source_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    if resolved != root and not resolved.is_relative_to(root):
        raise ValueError("strategy_hypothesis_path_outside_project")
    relative = resolved.relative_to(root)
    directory_parts = [part.lower() for part in relative.parts[:-1]]
    if any(part.startswith("runtime") for part in directory_parts):
        raise ValueError("strategy_hypothesis_runtime_path_forbidden")
    if any(part in {".git", ".agents", ".codex"} for part in directory_parts):
        raise ValueError("strategy_hypothesis_hidden_control_path_forbidden")
    basename = resolved.name.lower()
    if basename.startswith(".env") or basename == "config.local.json":
        raise ValueError("strategy_hypothesis_protected_file_forbidden")
    if resolved.suffix.lower() != ".json":
        raise ValueError("strategy_hypothesis_file_type_invalid")
    try:
        size = resolved.stat().st_size
    except OSError as exc:
        raise ValueError("strategy_hypothesis_file_unavailable") from exc
    if not 0 < size <= _MAX_DRAFT_BYTES:
        raise ValueError("strategy_hypothesis_file_size_invalid")
    try:
        raw = resolved.read_bytes()
        draft = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("strategy_hypothesis_file_invalid") from exc
    return build_strategy_hypothesis_preregistration(draft)


__all__ = [
    "FALSIFIED_STRATEGY_IDS_V1",
    "MECHANISM_FAILURE_EVIDENCE_STAGE_V2",
    "MECHANISM_FAILURE_METRICS_V2",
    "MECHANISM_FAILURE_OPERATORS_V2",
    "MECHANISM_FAILURE_REQUIRED_ACTION_V2",
    "STRATEGY_HYPOTHESIS_PREREGISTRATION_REPORT_SCHEMA_VERSION",
    "STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION",
    "STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2",
    "STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3",
    "STRATEGY_HYPOTHESIS_PREREGISTRATION_SUMMARY_SCHEMA_VERSION",
    "build_strategy_hypothesis_preregistration",
    "load_strategy_hypothesis_preregistration",
    "verify_strategy_hypothesis_preregistration",
]
