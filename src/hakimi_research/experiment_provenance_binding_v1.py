from __future__ import annotations

import math
import re
from typing import Any

from hakimi_research.experiment_manifest import (
    SCHEMA_VERSION as SOURCE_MANIFEST_SCHEMA_VERSION,
    canonical_payload_hash,
    verify_reproducible_experiment_manifest,
)


MANIFEST_V2_SCHEMA_VERSION = "reproducible-experiment-manifest-v2"
PROVENANCE_BINDING_VERSION = "experiment-provenance-binding-v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_ROLES = frozenset({"UNCLASSIFIED", "TRAIN", "VALIDATION", "FROZEN_TEST"})
_RANKING_ROLES = frozenset({"VALIDATION", "FROZEN_TEST"})
_CONTEXT_FIELDS = frozenset({
    "git_commit_sha",
    "git_worktree_clean",
    "dependency_lock_hash",
    "dependency_lock_fully_pinned",
    "dependency_lock_name",
    "random_seed",
    "runtime_version",
})
_IDENTITY_FIELDS = frozenset({
    "experiment_id",
    "strategy_name",
    "strategy_version",
    "symbol",
    "timeframe",
    "fee_rate",
    "slippage_pct",
    "evaluation_role",
    "evaluation_protocol_hash",
    "evaluation_protocol_verified",
})
_REPRODUCIBILITY_FIELDS = frozenset({
    "run_hash",
    "config_hash",
    "data_hash",
    "data_start",
    "data_end",
    "strategy_version",
    "random_seed",
})
_ENVELOPE_FIELDS = frozenset({
    "schema_version",
    "binding_version",
    "source_manifest_schema_version",
    "source_manifest_hash",
    "source_experiment_id",
    "result_hash",
    "reproducibility_hash",
    "context_hash",
    "identity_hash",
    "status",
    "classification",
    "blockers",
    "ranking_gate",
    "research_only",
    "parameter_selection_allowed",
    "paper_authorized",
    "live_order_allowed",
    "order_entry_allowed",
    "result_is_profitability_proof",
    "manifest_hash",
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


def _require_exact_document(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict or not _is_exact_native_json(value):
        raise ValueError(f"{label}_exact_native_document_required")
    return value


def _valid_hash(value: Any) -> bool:
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


def _valid_text(value: Any) -> bool:
    return type(value) is str and bool(value) and value == value.strip()


def _validate_reproducibility(value: dict[str, Any]) -> None:
    if not _REPRODUCIBILITY_FIELDS.issubset(value):
        raise ValueError("provenance_reproducibility_fields_invalid")
    for field in ("run_hash", "config_hash", "data_hash"):
        if not _valid_hash(value.get(field)):
            raise ValueError(f"provenance_reproducibility_{field}_invalid")
    for field in ("data_start", "data_end", "strategy_version"):
        if not _valid_text(value.get(field)):
            raise ValueError(f"provenance_reproducibility_{field}_invalid")
    if type(value.get("random_seed")) is not int:
        raise ValueError("provenance_reproducibility_random_seed_invalid")


def _validate_context(value: dict[str, Any]) -> None:
    if set(value) != _CONTEXT_FIELDS:
        raise ValueError("provenance_context_fields_invalid")
    if (
        type(value.get("git_commit_sha")) is not str
        or _GIT_SHA_RE.fullmatch(value["git_commit_sha"]) is None
    ):
        raise ValueError("provenance_context_git_commit_sha_invalid")
    if type(value.get("git_worktree_clean")) is not bool:
        raise ValueError("provenance_context_git_worktree_clean_invalid")
    if not _valid_hash(value.get("dependency_lock_hash")):
        raise ValueError("provenance_context_dependency_lock_hash_invalid")
    if type(value.get("dependency_lock_fully_pinned")) is not bool:
        raise ValueError("provenance_context_dependency_lock_fully_pinned_invalid")
    for field in ("dependency_lock_name", "runtime_version"):
        if not _valid_text(value.get(field)):
            raise ValueError(f"provenance_context_{field}_invalid")
    if type(value.get("random_seed")) is not int:
        raise ValueError("provenance_context_random_seed_invalid")


def _validate_identity(value: dict[str, Any]) -> None:
    if set(value) != _IDENTITY_FIELDS:
        raise ValueError("provenance_identity_fields_invalid")
    for field in (
        "experiment_id",
        "strategy_name",
        "strategy_version",
        "symbol",
        "timeframe",
    ):
        if not _valid_text(value.get(field)):
            raise ValueError(f"provenance_identity_{field}_invalid")
    for field in ("fee_rate", "slippage_pct"):
        item = value.get(field)
        if type(item) not in {int, float} or not math.isfinite(float(item)) or item < 0:
            raise ValueError(f"provenance_identity_{field}_invalid")
    role = value.get("evaluation_role")
    if role not in _ROLES:
        raise ValueError("provenance_identity_evaluation_role_invalid")
    protocol_hash = value.get("evaluation_protocol_hash")
    protocol_verified = value.get("evaluation_protocol_verified")
    if type(protocol_verified) is not bool:
        raise ValueError("provenance_identity_protocol_verified_invalid")
    if protocol_verified is True:
        if not _valid_hash(protocol_hash):
            raise ValueError("provenance_identity_protocol_invalid")
    elif protocol_hash != "":
        raise ValueError("provenance_identity_unverified_protocol_invalid")
    if role in _RANKING_ROLES and protocol_verified is not True:
        raise ValueError("provenance_identity_ranking_protocol_required")


def _model(rate: int | float) -> dict[str, str]:
    return {"kind": "proportional", "rate": format(float(rate), ".17g")}


def _binding_blockers(
    source_manifest: dict[str, Any],
    result_payload: dict[str, Any],
    expected_reproducibility: dict[str, Any],
    expected_context: dict[str, Any],
    expected_identity: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if not verify_reproducible_experiment_manifest(source_manifest, result_payload):
        blockers.append("source_manifest_verification_failed")
    observed_reproducibility = result_payload.get("reproducibility")
    if type(observed_reproducibility) is not dict:
        blockers.append("result_reproducibility_missing")
    elif observed_reproducibility != expected_reproducibility:
        blockers.append("result_reproducibility_mismatch")
    reproducibility_map = {
        "source_run_hash": "run_hash",
        "config_hash": "config_hash",
        "dataset_hash": "data_hash",
        "start_time": "data_start",
        "end_time": "data_end",
        "strategy_version": "strategy_version",
        "random_seed": "random_seed",
    }
    for manifest_field, reproducibility_field in reproducibility_map.items():
        if source_manifest.get(manifest_field) != expected_reproducibility.get(
            reproducibility_field
        ):
            blockers.append(f"manifest_{manifest_field}_reproducibility_mismatch")
    for field in _CONTEXT_FIELDS:
        if source_manifest.get(field) != expected_context.get(field):
            blockers.append(f"manifest_{field}_context_mismatch")
    identity_map = {
        "experiment_id": "experiment_id",
        "strategy_name": "strategy_name",
        "strategy_version": "strategy_version",
        "symbol": "symbol",
        "timeframe": "timeframe",
        "evaluation_role": "evaluation_role",
        "evaluation_protocol_hash": "evaluation_protocol_hash",
        "evaluation_protocol_verified": "evaluation_protocol_verified",
    }
    for manifest_field, identity_field in identity_map.items():
        if source_manifest.get(manifest_field) != expected_identity.get(identity_field):
            blockers.append(f"manifest_{manifest_field}_identity_mismatch")
    if source_manifest.get("fee_model") != _model(expected_identity["fee_rate"]):
        blockers.append("manifest_fee_model_identity_mismatch")
    if source_manifest.get("slippage_model") != _model(
        expected_identity["slippage_pct"]
    ):
        blockers.append("manifest_slippage_model_identity_mismatch")
    return sorted(set(blockers))


def build_reproducible_experiment_manifest_v2(
    *,
    source_manifest: dict[str, Any],
    result_payload: dict[str, Any],
    expected_reproducibility: dict[str, Any],
    expected_context: dict[str, Any],
    expected_identity: dict[str, Any],
) -> dict[str, Any]:
    source = _require_exact_document(source_manifest, "source_manifest")
    result = _require_exact_document(result_payload, "result_payload")
    reproducibility = _require_exact_document(
        expected_reproducibility,
        "expected_reproducibility",
    )
    context = _require_exact_document(expected_context, "expected_context")
    identity = _require_exact_document(expected_identity, "expected_identity")
    _validate_reproducibility(reproducibility)
    _validate_context(context)
    _validate_identity(identity)
    blockers = _binding_blockers(
        source,
        result,
        reproducibility,
        context,
        identity,
    )
    source_ranking = source.get("ranking_gate")
    source_ranking_blockers = (
        list(source_ranking.get("blockers") or [])
        if type(source_ranking) is dict
        and type(source_ranking.get("blockers")) is list
        else ["source_ranking_gate_invalid"]
    )
    ranking_blockers = sorted(set([*blockers, *source_ranking_blockers]))
    ranking_allowed = (
        not ranking_blockers
        and type(source_ranking) is dict
        and source_ranking.get("input_allowed") is True
    )
    core: dict[str, Any] = {
        "schema_version": MANIFEST_V2_SCHEMA_VERSION,
        "binding_version": PROVENANCE_BINDING_VERSION,
        "source_manifest_schema_version": source.get("schema_version", ""),
        "source_manifest_hash": source.get("manifest_hash", ""),
        "source_experiment_id": source.get("experiment_id", ""),
        "result_hash": canonical_payload_hash(result),
        "reproducibility_hash": canonical_payload_hash(reproducibility),
        "context_hash": canonical_payload_hash(context),
        "identity_hash": canonical_payload_hash(identity),
        "status": "PASS" if not blockers else "BLOCK",
        "classification": (
            "PROVENANCE_BOUND" if not blockers else "PROVENANCE_REJECTED"
        ),
        "blockers": blockers,
        "ranking_gate": {
            "status": "PASS" if ranking_allowed else "BLOCK",
            "input_allowed": ranking_allowed,
            "blockers": ranking_blockers,
        },
        "research_only": True,
        "parameter_selection_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "order_entry_allowed": False,
        "result_is_profitability_proof": False,
    }
    return {**core, "manifest_hash": canonical_payload_hash(core)}


def verify_reproducible_experiment_manifest_v2(
    envelope: Any,
    *,
    source_manifest: Any,
    result_payload: Any,
    expected_reproducibility: Any,
    expected_context: Any,
    expected_identity: Any,
) -> bool:
    if (
        type(envelope) is not dict
        or not _is_exact_native_json(envelope)
        or set(envelope) != _ENVELOPE_FIELDS
    ):
        return False
    try:
        expected = build_reproducible_experiment_manifest_v2(
            source_manifest=source_manifest,
            result_payload=result_payload,
            expected_reproducibility=expected_reproducibility,
            expected_context=expected_context,
            expected_identity=expected_identity,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return expected["status"] == "PASS" and envelope == expected


__all__ = [
    "MANIFEST_V2_SCHEMA_VERSION",
    "PROVENANCE_BINDING_VERSION",
    "SOURCE_MANIFEST_SCHEMA_VERSION",
    "build_reproducible_experiment_manifest_v2",
    "verify_reproducible_experiment_manifest_v2",
]
