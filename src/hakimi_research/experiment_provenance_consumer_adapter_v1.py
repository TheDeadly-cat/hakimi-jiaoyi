from __future__ import annotations

import math
import re
from typing import Any, Callable

from hakimi_research.experiment_manifest import canonical_payload_hash
from hakimi_research.experiment_provenance_binding_v1 import (
    build_reproducible_experiment_manifest_v2,
)
from hakimi_research.reporting import RESEARCH_JSON_REPORT_SCHEMA_VERSION


CONSUMER_ADAPTER_VERSION = "experiment-provenance-consumer-adapter-v1"
FROZEN_RUN_CONSUMER = "FROZEN_RUN"
MULTIPLE_TESTING_OBSERVATION_CONSUMER = "MULTIPLE_TESTING_OBSERVATION"
CLI_REPORT_BUNDLE_CONSUMER = "CLI_REPORT_BUNDLE"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REPORT_ARTIFACT_ID_RE = re.compile(r"^(?:hexp-[0-9a-f]{20}|[0-9a-f]{64})$")
_REPORT_PREFIX_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$")
_FROZEN_BASE_RECORD_IDENTITY_FIELDS = frozenset({
    "run_kind",
    "role",
    "scenario_id",
    "fee_rate",
    "slippage_pct",
    "strategy_name",
    "strategy_version",
})
_FROZEN_RESULT_FIELDS = frozenset({"result", "experiment_manifest"})
_FROZEN_RUN_RECORD_FIELDS = {
    "REGISTERED_STRATEGY": (
        _FROZEN_BASE_RECORD_IDENTITY_FIELDS
        | _FROZEN_RESULT_FIELDS
    ),
    "REGISTERED_EXECUTION_ADVERSITY": (
        _FROZEN_BASE_RECORD_IDENTITY_FIELDS
        | _FROZEN_RESULT_FIELDS
        | frozenset({
            "source_scenario_id",
            "source_result_hash",
            "scenario_policy_hash",
            "scenario_metadata",
            "observation_status",
            "source_result_delta",
            "source_input_dataset_hash",
            "stressed_input_dataset_hash",
            "unmodelled_gaps",
        })
    ),
    "REGISTERED_LIQUIDITY_CAPACITY_PROBE": (
        _FROZEN_BASE_RECORD_IDENTITY_FIELDS
        | _FROZEN_RESULT_FIELDS
        | frozenset({
            "source_scenario_id",
            "source_benchmark_id",
            "source_result_hash",
            "scenario_policy_hash",
            "source_result_delta",
            "source_input_dataset_hash",
            "stressed_input_dataset_hash",
            "liquidity_capacity_summary",
            "unmodelled_gaps",
        })
    ),
    "FIXED_BENCHMARK": (
        _FROZEN_BASE_RECORD_IDENTITY_FIELDS
        | _FROZEN_RESULT_FIELDS
        | frozenset({
            "benchmark_id",
            "benchmark_spec_hash",
            "benchmark_params",
        })
    ),
    "PREREGISTERED_VOLATILITY_TARGET_BENCHMARK": (
        _FROZEN_BASE_RECORD_IDENTITY_FIELDS
        | _FROZEN_RESULT_FIELDS
        | frozenset({
            "benchmark_id",
            "method_spec_hash",
            "calibration",
            "benchmark_params",
        })
    ),
    "FIXED_PARAMETER_WALK_FORWARD": (
        _FROZEN_BASE_RECORD_IDENTITY_FIELDS
        | _FROZEN_RESULT_FIELDS
        | frozenset({
            "fold_id",
            "method_spec_hash",
            "schedule_hash",
            "calibration_window",
            "purge_window",
            "evaluation_window",
        })
    ),
    "PARAMETER_STABILITY_OBSERVATION": (
        _FROZEN_BASE_RECORD_IDENTITY_FIELDS
        | _FROZEN_RESULT_FIELDS
        | frozenset({
            "cell_id",
            "segment",
            "is_center",
            "axes",
            "params",
            "params_hash",
            "cell_hash",
            "method_spec_hash",
            "matrix_hash",
        })
    ),
}
_FROZEN_RUN_IDENTITY_FIELDS = {
    run_kind: fields - _FROZEN_RESULT_FIELDS
    for run_kind, fields in _FROZEN_RUN_RECORD_FIELDS.items()
}
_MULTIPLE_TESTING_RECORD_FIELDS = _FROZEN_RUN_RECORD_FIELDS[
    "PARAMETER_STABILITY_OBSERVATION"
]
_MULTIPLE_TESTING_IDENTITY_FIELDS = _FROZEN_RUN_IDENTITY_FIELDS[
    "PARAMETER_STABILITY_OBSERVATION"
]
_CLI_ARTIFACT_IDENTITY_FIELDS = frozenset({
    "artifact_id",
    "prefix",
    "report_schema_version",
    "filename",
})
_RECEIPT_FIELDS = frozenset({
    "schema_version",
    "consumer_kind",
    "consumer_record_hash",
    "consumer_identity_hash",
    "source_manifest_hash",
    "result_hash",
    "provenance_binding",
    "status",
    "classification",
    "blockers",
    "candidate_ranking_gate",
    "candidate_only",
    "current_activation",
    "fixture_rebuild_performed",
    "runtime_write_performed",
    "research_only",
    "paper_authorized",
    "live_order_allowed",
    "order_entry_allowed",
    "result_is_profitability_proof",
    "receipt_hash",
})


def _is_exact_native_json(value: Any) -> bool:
    if value is None or type(value) in {bool, int, str}:
        return True
    if type(value) is float:
        return math.isfinite(value)
    if type(value) is list:
        return all(_is_exact_native_json(item) for item in value)
    if type(value) is dict:
        return all(
            type(key) is str and _is_exact_native_json(item)
            for key, item in value.items()
        )
    return False


def _document(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict or not _is_exact_native_json(value):
        raise ValueError(f"provenance_adapter_{label}_exact_native_required")
    return value


def _identity(
    value: Any,
    fields: frozenset[str],
    label: str,
) -> dict[str, Any]:
    document = _document(value, label)
    if set(document) != fields:
        raise ValueError(f"provenance_adapter_{label}_fields_invalid")
    return document


def _native_number(value: Any) -> bool:
    return type(value) in {int, float} and math.isfinite(float(value))


def _record_identity_blockers(
    record: dict[str, Any],
    expected: dict[str, Any],
    *,
    numeric_fields: frozenset[str] = frozenset(),
) -> list[str]:
    blockers: list[str] = []
    for field, expected_value in expected.items():
        observed = record.get(field)
        if field in numeric_fields:
            if (
                not _native_number(observed)
                or not _native_number(expected_value)
                or type(observed) is not type(expected_value)
                or observed != expected_value
            ):
                blockers.append(f"consumer_record_{field}_mismatch")
        elif (
            type(observed) is not type(expected_value)
            or observed != expected_value
        ):
            blockers.append(f"consumer_record_{field}_mismatch")
    return blockers


def _receipt(
    *,
    consumer_kind: str,
    consumer_record: dict[str, Any],
    consumer_identity: dict[str, Any],
    provenance_binding: dict[str, Any],
    blockers: list[str],
) -> dict[str, Any]:
    all_blockers = sorted(set([
        *blockers,
        *list(provenance_binding.get("blockers") or []),
    ]))
    binding_ranking = provenance_binding.get("ranking_gate")
    candidate_ranking = (
        dict(binding_ranking)
        if type(binding_ranking) is dict
        else {
            "status": "BLOCK",
            "input_allowed": False,
            "blockers": ["provenance_binding_ranking_gate_invalid"],
        }
    )
    if all_blockers:
        candidate_ranking = {
            "status": "BLOCK",
            "input_allowed": False,
            "blockers": sorted(set([
                *all_blockers,
                *list(candidate_ranking.get("blockers") or []),
            ])),
        }
    passed = provenance_binding.get("status") == "PASS" and not all_blockers
    core = {
        "schema_version": CONSUMER_ADAPTER_VERSION,
        "consumer_kind": consumer_kind,
        "consumer_record_hash": canonical_payload_hash(consumer_record),
        "consumer_identity_hash": canonical_payload_hash(consumer_identity),
        "source_manifest_hash": provenance_binding.get("source_manifest_hash", ""),
        "result_hash": provenance_binding.get("result_hash", ""),
        "provenance_binding": provenance_binding,
        "status": "PASS" if passed else "BLOCK",
        "classification": (
            "CANDIDATE_CONSUMER_BOUND"
            if passed
            else "CANDIDATE_CONSUMER_REJECTED"
        ),
        "blockers": all_blockers,
        "candidate_ranking_gate": candidate_ranking,
        "candidate_only": True,
        "current_activation": False,
        "fixture_rebuild_performed": False,
        "runtime_write_performed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
        "order_entry_allowed": False,
        "result_is_profitability_proof": False,
    }
    return {**core, "receipt_hash": canonical_payload_hash(core)}


def _binding(
    *,
    source_manifest: dict[str, Any],
    result_payload: dict[str, Any],
    expected_reproducibility: dict[str, Any],
    expected_context: dict[str, Any],
    expected_manifest_identity: dict[str, Any],
) -> dict[str, Any]:
    return build_reproducible_experiment_manifest_v2(
        source_manifest=source_manifest,
        result_payload=result_payload,
        expected_reproducibility=expected_reproducibility,
        expected_context=expected_context,
        expected_identity=expected_manifest_identity,
    )


def build_frozen_run_provenance_candidate(
    record: dict[str, Any],
    *,
    expected_reproducibility: dict[str, Any],
    expected_context: dict[str, Any],
    expected_manifest_identity: dict[str, Any],
    expected_record_identity: dict[str, Any],
) -> dict[str, Any]:
    expected_reproducibility = _document(
        expected_reproducibility, "expected_reproducibility"
    )
    expected_context = _document(expected_context, "expected_context")
    expected_manifest_identity = _document(
        expected_manifest_identity, "expected_manifest_identity"
    )
    source_record = _document(record, "frozen_record")
    expected_identity_document = _document(
        expected_record_identity,
        "frozen_record_identity",
    )
    expected_run_kind = expected_identity_document.get("run_kind")
    if (
        type(expected_run_kind) is not str
        or expected_run_kind not in _FROZEN_RUN_IDENTITY_FIELDS
    ):
        raise ValueError("provenance_adapter_frozen_run_kind_invalid")
    record_identity = _identity(
        expected_identity_document,
        _FROZEN_RUN_IDENTITY_FIELDS[expected_run_kind],
        "frozen_record_identity",
    )
    if set(source_record) != _FROZEN_RUN_RECORD_FIELDS[expected_run_kind]:
        raise ValueError("provenance_adapter_frozen_record_fields_invalid")
    result = _document(source_record.get("result"), "frozen_result")
    manifest = _document(
        source_record.get("experiment_manifest"),
        "frozen_source_manifest",
    )
    blockers = _record_identity_blockers(
        source_record,
        record_identity,
        numeric_fields=frozenset({"fee_rate", "slippage_pct"}),
    )
    binding = _binding(
        source_manifest=manifest,
        result_payload=result,
        expected_reproducibility=expected_reproducibility,
        expected_context=expected_context,
        expected_manifest_identity=expected_manifest_identity,
    )
    return _receipt(
        consumer_kind=FROZEN_RUN_CONSUMER,
        consumer_record=source_record,
        consumer_identity=record_identity,
        provenance_binding=binding,
        blockers=blockers,
    )


def build_multiple_testing_observation_provenance_candidate(
    record: dict[str, Any],
    *,
    expected_reproducibility: dict[str, Any],
    expected_context: dict[str, Any],
    expected_manifest_identity: dict[str, Any],
    expected_observation_identity: dict[str, Any],
) -> dict[str, Any]:
    expected_reproducibility = _document(
        expected_reproducibility, "expected_reproducibility"
    )
    expected_context = _document(expected_context, "expected_context")
    expected_manifest_identity = _document(
        expected_manifest_identity, "expected_manifest_identity"
    )
    source_record = _document(record, "multiple_testing_record")
    observation_identity = _identity(
        expected_observation_identity,
        _MULTIPLE_TESTING_IDENTITY_FIELDS,
        "multiple_testing_identity",
    )
    if set(source_record) != _MULTIPLE_TESTING_RECORD_FIELDS:
        raise ValueError("provenance_adapter_multiple_testing_record_fields_invalid")
    result = _document(source_record.get("result"), "multiple_testing_result")
    manifest = _document(
        source_record.get("experiment_manifest"),
        "multiple_testing_source_manifest",
    )
    blockers = _record_identity_blockers(source_record, observation_identity)
    if observation_identity["run_kind"] != "PARAMETER_STABILITY_OBSERVATION":
        blockers.append("consumer_observation_run_kind_invalid")
    if expected_reproducibility.get("param_hash") != observation_identity["params_hash"]:
        blockers.append("consumer_params_hash_reproducibility_mismatch")
    if canonical_payload_hash(observation_identity["params"]) != observation_identity[
        "params_hash"
    ]:
        blockers.append("consumer_params_hash_payload_mismatch")
    if (
        type(observation_identity["params_hash"]) is not str
        or _SHA256_RE.fullmatch(observation_identity["params_hash"]) is None
    ):
        blockers.append("consumer_params_hash_invalid")
    binding = _binding(
        source_manifest=manifest,
        result_payload=result,
        expected_reproducibility=expected_reproducibility,
        expected_context=expected_context,
        expected_manifest_identity=expected_manifest_identity,
    )
    return _receipt(
        consumer_kind=MULTIPLE_TESTING_OBSERVATION_CONSUMER,
        consumer_record=source_record,
        consumer_identity=observation_identity,
        provenance_binding=binding,
        blockers=blockers,
    )


def build_cli_report_provenance_bundle_candidate(
    report_payload: dict[str, Any],
    *,
    expected_reproducibility: dict[str, Any],
    expected_context: dict[str, Any],
    expected_manifest_identity: dict[str, Any],
    expected_artifact_identity: dict[str, Any],
) -> dict[str, Any]:
    expected_reproducibility = _document(
        expected_reproducibility, "expected_reproducibility"
    )
    expected_context = _document(expected_context, "expected_context")
    expected_manifest_identity = _document(
        expected_manifest_identity, "expected_manifest_identity"
    )
    report = _document(report_payload, "cli_report")
    artifact_identity = _identity(
        expected_artifact_identity,
        _CLI_ARTIFACT_IDENTITY_FIELDS,
        "cli_artifact_identity",
    )
    if (
        type(artifact_identity["artifact_id"]) is not str
        or _REPORT_ARTIFACT_ID_RE.fullmatch(artifact_identity["artifact_id"]) is None
    ):
        raise ValueError("provenance_adapter_cli_artifact_id_invalid")
    if (
        type(artifact_identity["prefix"]) is not str
        or _REPORT_PREFIX_RE.fullmatch(artifact_identity["prefix"]) is None
    ):
        raise ValueError("provenance_adapter_cli_prefix_invalid")
    if type(artifact_identity["report_schema_version"]) is not str:
        raise ValueError("provenance_adapter_cli_report_schema_version_invalid")
    if type(artifact_identity["filename"]) is not str:
        raise ValueError("provenance_adapter_cli_filename_invalid")
    manifest = _document(
        report.get("experiment_manifest"),
        "cli_source_manifest",
    )
    result = {
        key: value for key, value in report.items() if key != "experiment_manifest"
    }
    blockers: list[str] = []
    expected_prefix = "backtest_{}_{}".format(
        expected_manifest_identity.get("strategy_name"),
        expected_manifest_identity.get("symbol"),
    )
    expected_filename = "{}_{}.json".format(
        artifact_identity["prefix"],
        artifact_identity["artifact_id"],
    )
    if artifact_identity["artifact_id"] != expected_manifest_identity.get(
        "experiment_id"
    ):
        blockers.append("cli_artifact_id_manifest_identity_mismatch")
    if artifact_identity["artifact_id"] != manifest.get("experiment_id"):
        blockers.append("cli_artifact_id_source_manifest_mismatch")
    if artifact_identity["prefix"] != expected_prefix:
        blockers.append("cli_prefix_manifest_identity_mismatch")
    if (
        artifact_identity["report_schema_version"]
        != RESEARCH_JSON_REPORT_SCHEMA_VERSION
    ):
        blockers.append("cli_report_schema_version_mismatch")
    if artifact_identity["filename"] != expected_filename:
        blockers.append("cli_filename_identity_mismatch")
    binding = _binding(
        source_manifest=manifest,
        result_payload=result,
        expected_reproducibility=expected_reproducibility,
        expected_context=expected_context,
        expected_manifest_identity=expected_manifest_identity,
    )
    return _receipt(
        consumer_kind=CLI_REPORT_BUNDLE_CONSUMER,
        consumer_record=report,
        consumer_identity=artifact_identity,
        provenance_binding=binding,
        blockers=blockers,
    )


def _verify(
    receipt: Any,
    builder: Callable[..., dict[str, Any]],
    *args: Any,
    **kwargs: Any,
) -> bool:
    if (
        type(receipt) is not dict
        or not _is_exact_native_json(receipt)
        or set(receipt) != _RECEIPT_FIELDS
    ):
        return False
    try:
        expected = builder(*args, **kwargs)
    except (KeyError, TypeError, ValueError):
        return False
    return expected["status"] == "PASS" and receipt == expected


def verify_frozen_run_provenance_candidate(
    receipt: Any,
    record: Any,
    **expectations: Any,
) -> bool:
    return _verify(
        receipt,
        build_frozen_run_provenance_candidate,
        record,
        **expectations,
    )


def verify_multiple_testing_observation_provenance_candidate(
    receipt: Any,
    record: Any,
    **expectations: Any,
) -> bool:
    return _verify(
        receipt,
        build_multiple_testing_observation_provenance_candidate,
        record,
        **expectations,
    )


def verify_cli_report_provenance_bundle_candidate(
    receipt: Any,
    report_payload: Any,
    **expectations: Any,
) -> bool:
    return _verify(
        receipt,
        build_cli_report_provenance_bundle_candidate,
        report_payload,
        **expectations,
    )


__all__ = [
    "CLI_REPORT_BUNDLE_CONSUMER",
    "CONSUMER_ADAPTER_VERSION",
    "FROZEN_RUN_CONSUMER",
    "MULTIPLE_TESTING_OBSERVATION_CONSUMER",
    "build_cli_report_provenance_bundle_candidate",
    "build_frozen_run_provenance_candidate",
    "build_multiple_testing_observation_provenance_candidate",
    "verify_cli_report_provenance_bundle_candidate",
    "verify_frozen_run_provenance_candidate",
    "verify_multiple_testing_observation_provenance_candidate",
]
