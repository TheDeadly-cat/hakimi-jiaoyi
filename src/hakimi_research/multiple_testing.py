"""Fail-closed multiple-testing lineage without unsupported corrections."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from hakimi_research.experiment_manifest import (
    canonical_payload_hash,
    verify_reproducible_experiment_manifest,
)


MULTIPLE_TESTING_POLICY_VERSION = "multiple-testing-lineage-policy-v2"
MULTIPLE_TESTING_LEDGER_SCHEMA_VERSION = "multiple-testing-ledger-v2"
MULTIPLE_TESTING_AUTHORITY_LOCK = {
    "parameter_selection": False,
    "ranking": False,
    "profitability_proof": False,
    "paper": False,
    "live": False,
    "order": False,
}

_HASH_PATTERN = re.compile(r"[0-9a-f]{64}")


def multiple_testing_policy_spec() -> dict[str, Any]:
    """Return a fresh policy that requires lineage before correction claims."""

    return {
        "policy_version": MULTIPLE_TESTING_POLICY_VERSION,
        "trial_definition": "UNIQUE_PREREGISTERED_PARAMETER_CELL",
        "trial_family_source": "PARAMETER_STABILITY_MATRIX",
        "observation_roles": ["VALIDATION", "FROZEN_TEST"],
        "expected_trial_count": 21,
        "expected_observation_count": 42,
        "required_corrections": [
            "DEFLATED_SHARPE_RATIO",
            "PROBABILITY_OF_BACKTEST_OVERFITTING",
            "BLOCK_BOOTSTRAP_CONFIDENCE_INTERVAL",
        ],
        "all_observations_must_be_retained": True,
        "selected_trial_id": None,
        "parameter_selection_allowed": False,
        "ranking_allowed": False,
    }


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _hash_value(value: Any, *, field: str) -> str:
    if type(value) is not str or _HASH_PATTERN.fullmatch(value) is None:
        raise ValueError(f"multiple_testing_{field}_invalid")
    return value


def build_multiple_testing_ledger(
    parameter_contract: dict[str, Any],
    stability_runs: list[dict[str, Any]],
    stability_summary: dict[str, Any],
    walk_forward_contract: dict[str, Any],
    walk_forward_summary: dict[str, Any],
    *,
    observation_provenance_receipts: dict[str, str],
) -> dict[str, Any]:
    """Bind all observed trials and state why corrections are not estimable."""

    if (
        type(parameter_contract) is not dict
        or type(stability_runs) is not list
        or type(stability_summary) is not dict
        or type(walk_forward_contract) is not dict
        or type(walk_forward_summary) is not dict
        or type(observation_provenance_receipts) is not dict
    ):
        raise ValueError("multiple_testing_input_type_invalid")
    policy = multiple_testing_policy_spec()
    cells = parameter_contract.get("cells")
    if type(cells) is not list or len(cells) != policy["expected_trial_count"]:
        raise ValueError("multiple_testing_trial_family_invalid")
    cell_ids = [item.get("cell_id") if type(item) is dict else None for item in cells]
    if any(type(item) is not str for item in cell_ids) or len(set(cell_ids)) != len(cell_ids):
        raise ValueError("multiple_testing_trial_ids_invalid")
    method = parameter_contract.get("method")
    if type(method) is not dict:
        raise ValueError("multiple_testing_trial_method_invalid")
    method_spec_hash = _hash_value(method.get("spec_hash"), field="method_spec_hash")
    expected_matrix_hash = _canonical_hash({
        "method_spec_hash": method_spec_hash,
        "cells": cells,
    })
    if parameter_contract.get("matrix_hash") != expected_matrix_hash:
        raise ValueError("multiple_testing_trial_matrix_hash_invalid")
    if (
        stability_summary.get("selected_cell_id") is not None
        or stability_summary.get("parameter_selection_performed") is not False
        or stability_summary.get("ranking_performed") is not False
    ):
        raise ValueError("multiple_testing_selection_state_invalid")
    stability_summary_core = {
        key: value
        for key, value in stability_summary.items()
        if key != "summary_hash"
    }
    walk_forward_summary_core = {
        key: value
        for key, value in walk_forward_summary.items()
        if key != "summary_hash"
    }
    if (
        stability_summary.get("summary_hash") != _canonical_hash(stability_summary_core)
        or walk_forward_summary.get("summary_hash")
        != _canonical_hash(walk_forward_summary_core)
    ):
        raise ValueError("multiple_testing_upstream_summary_hash_invalid")
    expected = {
        (role, cell_id)
        for role in policy["observation_roles"]
        for cell_id in cell_ids
    }
    observations: list[dict[str, Any]] = []
    observed: set[tuple[str, str]] = set()
    for record in stability_runs:
        if (
            type(record) is not dict
            or type(record.get("result")) is not dict
            or type(record.get("experiment_manifest")) is not dict
        ):
            raise ValueError("multiple_testing_observation_invalid")
        identity = (record.get("role"), record.get("cell_id"))
        if identity in observed or identity not in expected:
            raise ValueError("multiple_testing_observation_identity_invalid")
        observed.add(identity)
        reproducibility = record["result"].get("reproducibility")
        manifest = record["experiment_manifest"]
        ranking_gate = manifest.get("ranking_gate")
        if (
            type(reproducibility) is not dict
            or type(ranking_gate) is not dict
            or ranking_gate.get("input_allowed") is not False
            or manifest.get("evaluation_role") != "UNCLASSIFIED"
            or type(manifest.get("experiment_id")) is not str
            or not manifest.get("experiment_id")
            or record.get("params_hash") != reproducibility.get("param_hash")
            or manifest.get("source_run_hash") != reproducibility.get("run_hash")
            or not verify_reproducible_experiment_manifest(manifest, record["result"])
        ):
            raise ValueError("multiple_testing_observation_authority_invalid")
        observations.append({
            "role": record["role"],
            "cell_id": record["cell_id"],
            "params_hash": _hash_value(record.get("params_hash"), field="params_hash"),
            "run_hash": _hash_value(reproducibility.get("run_hash"), field="run_hash"),
            "result_hash": _hash_value(manifest.get("result_hash"), field="result_hash"),
            "experiment_id": manifest.get("experiment_id"),
            "provenance_receipt_hash": _hash_value(
                observation_provenance_receipts.get(
                    canonical_payload_hash(record)
                ),
                field="provenance_receipt_hash",
            ),
            "ranking_input": False,
        })
    if observed != expected or len(observations) != policy["expected_observation_count"]:
        raise ValueError("multiple_testing_observation_matrix_incomplete")
    expected_record_hashes = {
        canonical_payload_hash(record)
        for record in stability_runs
    }
    if set(observation_provenance_receipts) != expected_record_hashes:
        raise ValueError("multiple_testing_provenance_receipt_matrix_invalid")
    observations.sort(
        key=lambda item: (
            policy["observation_roles"].index(item["role"]),
            cell_ids.index(item["cell_id"]),
        )
    )
    folds = walk_forward_contract.get("schedule", {}).get("folds")
    if type(folds) is not list or [item.get("fold_id") for item in folds] != ["WF01", "WF02"]:
        raise ValueError("multiple_testing_walk_forward_lineage_invalid")
    if walk_forward_summary.get("ranking_performed") is not False:
        raise ValueError("multiple_testing_walk_forward_ranking_invalid")
    corrections = [
        {
            "correction_id": "DEFLATED_SHARPE_RATIO",
            "status": "NOT_ESTIMABLE",
            "value": None,
            "blockers": [
                "RETURN_HISTORY_TOO_SHORT",
                "SYNTHETIC_SINGLE_DATASET_ONLY",
                "NO_INDEPENDENT_TRIAL_DISTRIBUTION",
            ],
        },
        {
            "correction_id": "PROBABILITY_OF_BACKTEST_OVERFITTING",
            "status": "NOT_ESTIMABLE",
            "value": None,
            "blockers": [
                "INSUFFICIENT_INDEPENDENT_FOLDS",
                "NO_TRAIN_SELECTION_TEST_MATRIX",
                "PARAMETER_SELECTION_NOT_PERFORMED",
            ],
        },
        {
            "correction_id": "BLOCK_BOOTSTRAP_CONFIDENCE_INTERVAL",
            "status": "NOT_COMPUTED",
            "value": None,
            "blockers": [
                "ACTIVE_RETURN_HISTORY_TOO_SHORT",
                "BLOCK_LENGTH_NOT_PREREGISTERED",
            ],
        },
    ]
    core = {
        "schema_version": MULTIPLE_TESTING_LEDGER_SCHEMA_VERSION,
        "policy_version": MULTIPLE_TESTING_POLICY_VERSION,
        "policy_spec_hash": _canonical_hash(policy),
        "family": {
            "family_id": "DUAL_MA_PARAMETER_STABILITY_V1",
            "family_hash": expected_matrix_hash,
            "trial_count": len(cells),
            "trial_ids": list(cell_ids),
            "all_trials_retained": True,
        },
        "observations": observations,
        "observation_count": len(observations),
        "validation_observation_count": sum(
            item["role"] == "VALIDATION" for item in observations
        ),
        "synthetic_frozen_observation_count": sum(
            item["role"] == "FROZEN_TEST" for item in observations
        ),
        "formal_frozen_consumption_count": None,
        "single_consumption_proven": False,
        "external_preregistration_receipt_present": False,
        "rule_change_tracking_status": "UNKNOWN_NO_EXTERNAL_PREREGISTRATION_RECEIPT",
        "walk_forward_fold_count": len(folds),
        "walk_forward_fold_ids": [item["fold_id"] for item in folds],
        "all_observed_results_retained": True,
        "failure_classification": "NOT_DEFINED_NO_RESULTS_DROPPED",
        "selected_trial_id": None,
        "parameter_selection_performed": False,
        "ranking_performed": False,
        "corrections": corrections,
        "ledger_status": "RECORDED_WITH_UNESTIMABLE_CORRECTIONS",
        "authority": dict(MULTIPLE_TESTING_AUTHORITY_LOCK),
        "stability_summary_hash": _hash_value(
            stability_summary.get("summary_hash"),
            field="stability_summary_hash",
        ),
        "walk_forward_summary_hash": _hash_value(
            walk_forward_summary.get("summary_hash"),
            field="walk_forward_summary_hash",
        ),
    }
    return {
        **core,
        "ledger_hash": _canonical_hash(core),
    }


__all__ = [
    "MULTIPLE_TESTING_AUTHORITY_LOCK",
    "MULTIPLE_TESTING_LEDGER_SCHEMA_VERSION",
    "MULTIPLE_TESTING_POLICY_VERSION",
    "build_multiple_testing_ledger",
    "multiple_testing_policy_spec",
]
