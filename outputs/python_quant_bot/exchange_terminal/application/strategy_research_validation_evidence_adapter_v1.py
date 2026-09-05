from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

from exchange_terminal.services.strategy_research_search_lineage import (
    STRATEGY_RESEARCH_SEARCH_LINEAGE_SCHEMA_VERSION_V2,
    verify_strategy_research_search_lineage,
)
from exchange_terminal.services.strategy_research_evidence import (
    verify_strategy_research_report,
)
from hakimi_research.validation_evidence import (
    FORMAL_SEARCH_LINEAGE_PRODUCER_ID,
    build_validation_evidence,
)


_HASH_PATTERN = re.compile(r"[0-9a-f]{64}")


class StrategyResearchValidationEvidenceAdapterError(ValueError):
    """Raised when a formal search-lineage artifact cannot be bound exactly."""


def _fail(path: str, message: str) -> None:
    raise StrategyResearchValidationEvidenceAdapterError(f"{path}: {message}")


def _require_exact_native(value: Any, path: str) -> None:
    value_type = type(value)
    if value_type is dict:
        for key, item in value.items():
            if type(key) is not str:
                _fail(path, "object keys must be exact str values")
            _require_exact_native(item, f"{path}.{key}")
        return
    if value_type is list:
        for index, item in enumerate(value):
            _require_exact_native(item, f"{path}[{index}]")
        return
    if value_type in (str, int, bool) or value is None:
        return
    if value_type is float:
        if not math.isfinite(value):
            _fail(path, "float values must be finite")
        return
    _fail(path, f"unsupported non-native type {value_type.__name__}")


def _canonical_copy(value: Any, path: str) -> Any:
    _require_exact_native(value, path)
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return json.loads(payload)


def _canonical_sha256(value: Any, path: str) -> str:
    _require_exact_native(value, path)
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def _require_exact_str(value: Any, path: str) -> str:
    if type(value) is not str or not value:
        _fail(path, "must be a non-empty exact str")
    return value


def _require_exact_int(value: Any, path: str, *, minimum: int) -> int:
    if type(value) is not int or value < minimum:
        _fail(path, f"must be an exact int >= {minimum}")
    return value


def _require_hash(value: Any, path: str) -> str:
    if type(value) is not str or _HASH_PATTERN.fullmatch(value) is None:
        _fail(path, "must be a lowercase SHA-256 digest")
    return value


def _require_dict(value: Any, path: str) -> dict[str, Any]:
    if type(value) is not dict:
        _fail(path, "must be an exact dict")
    return value


def _require_list(value: Any, path: str) -> list[Any]:
    if type(value) is not list:
        _fail(path, "must be an exact list")
    return value


def _require_text_list(value: Any, path: str) -> list[str]:
    items = _require_list(value, path)
    texts = [_require_exact_str(item, f"{path}[{index}]") for index, item in enumerate(items)]
    if len(texts) != len(set(texts)):
        _fail(path, "must not contain duplicates")
    return sorted(texts)


def _records_for_variant(
    records: list[Any],
    *,
    variant_id: str,
    path: str,
) -> list[dict[str, Any]]:
    matched: list[dict[str, Any]] = []
    for index, item in enumerate(records):
        record = _require_dict(item, f"{path}[{index}]")
        record_variant_id = _require_exact_str(record.get("variant_id"), f"{path}[{index}].variant_id")
        if record_variant_id == variant_id:
            matched.append(record)
    return matched


def _cell_receipts(records: list[dict[str, Any]], path: str) -> list[dict[str, str]]:
    receipts: list[dict[str, str]] = []
    for index, record in enumerate(records):
        symbol = _require_exact_str(record.get("symbol"), f"{path}[{index}].symbol")
        run_hash = _require_hash(record.get("run_hash"), f"{path}[{index}].run_hash")
        receipts.append({"symbol": symbol, "run_hash": run_hash})
    receipts.sort(key=lambda item: (item["symbol"], item["run_hash"]))
    symbols = [item["symbol"] for item in receipts]
    if len(symbols) != len(set(symbols)):
        _fail(path, "must contain at most one cell per symbol")
    return receipts


def build_multiple_testing_ledger_from_verified_strategy_research_report(
    formal_report: dict[str, Any],
) -> dict[str, Any]:
    """Project exact per-variant receipts from an independently verified formal report."""

    report = _canonical_copy(formal_report, "formal_report")
    verification = verify_strategy_research_report(report)
    _require_exact_native(verification, "formal_report_verification")
    if type(verification) is not dict or verification.get("status") != "PASS":
        blockers = verification.get("blockers") if type(verification) is dict else None
        _fail("formal_report", f"formal report verification blocked: {blockers}")
    if report.get("research_only") is not True:
        _fail("formal_report.research_only", "must remain exact true")
    if report.get("paper_authorized") is not False:
        _fail("formal_report.paper_authorized", "must remain exact false")
    if report.get("live_order_allowed") is not False:
        _fail("formal_report.live_order_allowed", "must remain exact false")

    batch_run_hash = _require_hash(report.get("batch_run_hash"), "formal_report.batch_run_hash")
    batch_spec = _require_dict(report.get("batch_spec"), "formal_report.batch_spec")
    variants = _require_list(batch_spec.get("variants"), "formal_report.batch_spec.variants")
    if not variants:
        _fail("formal_report.batch_spec.variants", "must be non-empty")
    selection_cells = _require_list(report.get("selection_cells"), "formal_report.selection_cells")
    validation_rankings = _require_list(report.get("validation_rankings"), "formal_report.validation_rankings")
    frozen_candidates = _require_list(report.get("frozen_candidates"), "formal_report.frozen_candidates")
    test_cells = _require_list(report.get("test_cells"), "formal_report.test_cells")
    test_results = _require_list(report.get("test_results"), "formal_report.test_results")

    frozen_ids: list[str] = []
    for index, candidate in enumerate(frozen_candidates):
        candidate_record = _require_dict(candidate, f"formal_report.frozen_candidates[{index}]")
        frozen_ids.append(
            _require_exact_str(
                candidate_record.get("variant_id"),
                f"formal_report.frozen_candidates[{index}].variant_id",
            )
        )
    if len(frozen_ids) != 1:
        _fail("formal_report.frozen_candidates", "must contain exactly one preregistered frozen selection")
    selected_parameter_id = frozen_ids[0]

    projections: list[dict[str, Any]] = []
    seen_variant_ids: set[str] = set()
    for index, item in enumerate(variants):
        variant = _require_dict(item, f"formal_report.batch_spec.variants[{index}]")
        variant_id = _require_exact_str(variant.get("variant_id"), f"formal_report.batch_spec.variants[{index}].variant_id")
        if variant_id in seen_variant_ids:
            _fail("formal_report.batch_spec.variants", "variant_id values must be unique")
        seen_variant_ids.add(variant_id)
        param_hash = _require_hash(variant.get("param_hash"), f"formal_report.batch_spec.variants[{index}].param_hash")
        implementation_fingerprint = _require_exact_str(
            variant.get("implementation_fingerprint"),
            f"formal_report.batch_spec.variants[{index}].implementation_fingerprint",
        )

        variant_selection_cells = _records_for_variant(
            selection_cells,
            variant_id=variant_id,
            path="formal_report.selection_cells",
        )
        if not variant_selection_cells:
            _fail(f"formal_report.selection_cells:{variant_id}", "verified trial must retain selection cells")
        selection_receipts = _cell_receipts(
            variant_selection_cells,
            f"formal_report.selection_cells:{variant_id}",
        )

        rankings = _records_for_variant(
            validation_rankings,
            variant_id=variant_id,
            path="formal_report.validation_rankings",
        )
        if len(rankings) != 1:
            _fail(f"formal_report.validation_rankings:{variant_id}", "must contain exactly one aggregate ranking")
        ranking = rankings[0]
        decision_status = _require_exact_str(
            ranking.get("status"),
            f"formal_report.validation_rankings:{variant_id}.status",
        )
        decision_blockers = _require_text_list(
            ranking.get("blockers"),
            f"formal_report.validation_rankings:{variant_id}.blockers",
        )

        variant_test_cells = _records_for_variant(
            test_cells,
            variant_id=variant_id,
            path="formal_report.test_cells",
        )
        test_receipts = _cell_receipts(
            variant_test_cells,
            f"formal_report.test_cells:{variant_id}",
        )
        matching_test_results = _records_for_variant(
            test_results,
            variant_id=variant_id,
            path="formal_report.test_results",
        )
        if len(matching_test_results) > 1:
            _fail(f"formal_report.test_results:{variant_id}", "must contain at most one aggregate test result")

        projection = {
            "producer_report_sha256": batch_run_hash,
            "variant_id": variant_id,
            "param_hash": param_hash,
            "implementation_fingerprint": implementation_fingerprint,
            "selection_cell_receipts": selection_receipts,
            "validation_ranking_sha256": _canonical_sha256(
                ranking,
                f"formal_report.validation_rankings:{variant_id}",
            ),
            "frozen_for_test": variant_id in frozen_ids,
            "test_cell_receipts": test_receipts,
            "test_result_sha256": (
                _canonical_sha256(
                    matching_test_results[0],
                    f"formal_report.test_results:{variant_id}",
                )
                if matching_test_results
                else None
            ),
        }
        projections.append({
            "trial_id": variant_id,
            "status": "OBSERVED",
            "result_sha256": _canonical_sha256(projection, f"formal_trial_projection:{variant_id}"),
            "failure_code": None,
            "decision_status": decision_status,
            "decision_blockers": decision_blockers,
        })

    if selected_parameter_id not in seen_variant_ids:
        _fail("formal_report.frozen_candidates", "selected variant is absent from batch_spec.variants")
    projections.sort(key=lambda item: item["trial_id"])
    return {
        "preregistered_trial_ids": [item["trial_id"] for item in projections],
        "trial_outcomes": projections,
        "selected_parameter_id": selected_parameter_id,
        "selection_rule": "formal_frozen_candidate_from_verified_strategy_report_v1",
        "producer_report_sha256": batch_run_hash,
    }


def build_validation_evidence_from_formal_search_lineage(
    report: dict[str, Any],
    *,
    experiment_id: str,
    formal_search_lineage: dict[str, Any],
    distribution_evidence: dict[str, Any],
    expected_search_family_id: str,
    expected_current_trial_count: int,
    expected_prior_registrations: list[dict[str, Any]],
    walk_forward: dict[str, Any],
    parameter_stability: dict[str, Any],
    multiple_testing: dict[str, Any],
    market_regimes: dict[str, Any],
) -> dict[str, Any]:
    """Verify a v2 formal lineage and bind its count/history receipt to ADR0510."""

    lineage = _canonical_copy(formal_search_lineage, "formal_search_lineage")
    prior = _canonical_copy(expected_prior_registrations, "expected_prior_registrations")
    expected_family = _require_exact_str(expected_search_family_id, "expected_search_family_id")
    expected_count = _require_exact_int(expected_current_trial_count, "expected_current_trial_count", minimum=1)
    if type(prior) is not list:
        _fail("expected_prior_registrations", "must be an exact list")

    if type(multiple_testing) is not dict:
        _fail("multiple_testing", "must be an exact dict")
    preregistered_ids = multiple_testing.get("preregistered_trial_ids")
    if type(preregistered_ids) is not list:
        _fail("multiple_testing.preregistered_trial_ids", "must be an exact list")
    _require_exact_native(preregistered_ids, "multiple_testing.preregistered_trial_ids")
    if len(preregistered_ids) != expected_count:
        _fail(
            "multiple_testing.preregistered_trial_ids",
            "count must equal the verified formal current_trial_count",
        )

    verification = verify_strategy_research_search_lineage(
        lineage,
        expected_search_family_id=expected_family,
        expected_current_trial_count=expected_count,
        expected_prior_registrations=prior,
    )
    _require_exact_native(verification, "formal_verification")
    if type(verification) is not dict or verification.get("status") != "PASS":
        blockers = verification.get("blockers") if type(verification) is dict else None
        _fail("formal_search_lineage", f"formal verification blocked: {blockers}")

    schema_version = _require_exact_str(lineage.get("schema_version"), "formal_search_lineage.schema_version")
    if schema_version != STRATEGY_RESEARCH_SEARCH_LINEAGE_SCHEMA_VERSION_V2:
        _fail("formal_search_lineage.schema_version", "must be the registered v2 lineage schema")
    search_family_id = _require_exact_str(lineage.get("search_family_id"), "formal_search_lineage.search_family_id")
    if search_family_id != expected_family:
        _fail("formal_search_lineage.search_family_id", "does not match expected_search_family_id")
    current_count = _require_exact_int(lineage.get("current_trial_count"), "formal_search_lineage.current_trial_count", minimum=1)
    cumulative_count = _require_exact_int(lineage.get("cumulative_trial_count"), "formal_search_lineage.cumulative_trial_count", minimum=current_count)
    prior_count = _require_exact_int(lineage.get("prior_registration_count"), "formal_search_lineage.prior_registration_count", minimum=0)
    if current_count != expected_count or prior_count != len(prior):
        _fail("formal_search_lineage", "verified count fields do not match expected inputs")
    if lineage.get("parameter_selection_allowed") is not False:
        _fail("formal_search_lineage.parameter_selection_allowed", "must remain exact false")
    if lineage.get("live_order_allowed") is not False:
        _fail("formal_search_lineage.live_order_allowed", "must remain exact false")
    lineage_hash = _require_hash(lineage.get("lineage_hash"), "formal_search_lineage.lineage_hash")

    formal_binding = {
        "producer_id": FORMAL_SEARCH_LINEAGE_PRODUCER_ID,
        "producer_schema_version": schema_version,
        "artifact_sha256": _canonical_sha256(lineage, "formal_search_lineage"),
        "lineage_sha256": lineage_hash,
        "search_family_id": search_family_id,
        "current_trial_count": current_count,
        "cumulative_trial_count": cumulative_count,
        "prior_registration_count": prior_count,
    }
    return build_validation_evidence(
        report,
        experiment_id=experiment_id,
        formal_search_lineage=formal_binding,
        distribution_evidence=distribution_evidence,
        walk_forward=walk_forward,
        parameter_stability=parameter_stability,
        multiple_testing=multiple_testing,
        market_regimes=market_regimes,
    )


__all__ = [
    "StrategyResearchValidationEvidenceAdapterError",
    "build_multiple_testing_ledger_from_verified_strategy_research_report",
    "build_validation_evidence_from_formal_search_lineage",
]
