"""Compatibility for research-json-report-v1 and research-json-report-bundle-v2.

Protocol validation is retained from commit 4fb6d191. Persistence shares the
current atomic publisher; these schemas remain separate from MVP run reports.
"""

from __future__ import annotations

import json
import hashlib
import math
from pathlib import Path
import re
from typing import Any


RESEARCH_JSON_REPORT_SCHEMA_VERSION = "research-json-report-v1"
RESEARCH_JSON_REPORT_BUNDLE_SCHEMA_VERSION = "research-json-report-bundle-v2"
RESEARCH_JSON_REPORT_BUNDLE_TRUST_MODEL = (
    "SELF_CONTAINED_REQUIRES_EXTERNAL_ARTIFACT_HASH"
)

_ARTIFACT_ID_PATTERN = re.compile(r"(?:hexp-[0-9a-f]{20}|[0-9a-f]{64})")
_PREFIX_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,159}")
_MAX_JSON_DEPTH = 64
_BUNDLE_IDENTITY_FIELDS = frozenset({
    "artifact_id",
    "prefix",
    "report_schema_version",
    "filename",
})
_BUNDLE_FIELDS = frozenset({
    "schema_version",
    "trust_model",
    "external_artifact_hash_required",
    "artifact_identity",
    "report_payload",
    "provenance_receipt",
    "research_only",
    "ranking_allowed",
    "paper_authorized",
    "live_order_allowed",
    "order_entry_allowed",
    "result_is_profitability_proof",
    "bundle_hash",
})


def _require_native_json(
    value: Any,
    *,
    depth: int = 0,
    active_containers: set[int] | None = None,
) -> None:
    value_type = type(value)
    if value_type in (type(None), bool, int, str):
        return
    if value_type is float:
        if not math.isfinite(value):
            raise ValueError("report payload contains a non-finite float")
        return
    if value_type not in (list, dict):
        raise ValueError("report payload must contain exact native JSON types")
    if depth >= _MAX_JSON_DEPTH:
        raise ValueError("report payload exceeds the maximum JSON depth")

    active = active_containers if active_containers is not None else set()
    identity = id(value)
    if identity in active:
        raise ValueError("report payload contains a reference cycle")
    active.add(identity)
    try:
        if value_type is list:
            for item in value:
                _require_native_json(
                    item,
                    depth=depth + 1,
                    active_containers=active,
                )
            return
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError("report payload object keys must be exact strings")
            _require_native_json(
                item,
                depth=depth + 1,
                active_containers=active,
            )
    finally:
        active.remove(identity)


def _validate_directory(directory: str) -> Path:
    if type(directory) is not str or not directory or directory != directory.strip():
        raise ValueError("report directory must be an exact non-empty string")
    if "\x00" in directory:
        raise ValueError("report directory contains a null byte")
    return Path(directory)


def _validate_prefix(prefix: str) -> str:
    if type(prefix) is not str or _PREFIX_PATTERN.fullmatch(prefix) is None:
        raise ValueError("report prefix is invalid")
    return prefix


def _validate_artifact_id(artifact_id: str) -> str:
    if type(artifact_id) is not str or _ARTIFACT_ID_PATTERN.fullmatch(artifact_id) is None:
        raise ValueError("report artifact_id must be a canonical experiment identity")
    return artifact_id


def render_json_report(payload: dict[str, Any]) -> str:
    """Return canonical UTF-8-compatible JSON without mutating the payload."""

    if type(payload) is not dict:
        raise ValueError("report payload must be an exact dictionary")
    _require_native_json(payload)
    rendered = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        indent=2,
    ) + "\n"
    rendered.encode("utf-8")
    return rendered


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _self_hash_matches(document: Any, hash_field: str) -> bool:
    return (
        type(document) is dict
        and type(document.get(hash_field)) is str
        and document[hash_field]
        == _canonical_hash({
            key: value
            for key, value in document.items()
            if key != hash_field
        })
    )


def build_json_report_bundle_v2(
    report_payload: dict[str, Any],
    provenance_receipt: dict[str, Any],
    *,
    artifact_identity: dict[str, Any],
) -> dict[str, Any]:
    if type(report_payload) is not dict:
        raise ValueError("report bundle payload must be an exact dictionary")
    if type(provenance_receipt) is not dict:
        raise ValueError("report bundle receipt must be an exact dictionary")
    if type(artifact_identity) is not dict:
        raise ValueError("report bundle identity must be an exact dictionary")
    _require_native_json(report_payload)
    _require_native_json(provenance_receipt)
    _require_native_json(artifact_identity)
    if set(artifact_identity) != _BUNDLE_IDENTITY_FIELDS:
        raise ValueError("report bundle identity fields are invalid")
    artifact_id = _validate_artifact_id(artifact_identity["artifact_id"])
    prefix = _validate_prefix(artifact_identity["prefix"])
    expected_filename = f"{prefix}_{artifact_id}.json"
    if (
        artifact_identity["report_schema_version"]
        != RESEARCH_JSON_REPORT_SCHEMA_VERSION
        or artifact_identity["filename"] != expected_filename
    ):
        raise ValueError("report bundle identity is inconsistent")
    manifest = report_payload.get("experiment_manifest")
    result_payload = {
        key: value
        for key, value in report_payload.items()
        if key != "experiment_manifest"
    }
    binding = provenance_receipt.get("provenance_binding")
    if (
        type(manifest) is not dict
        or type(binding) is not dict
        or manifest.get("experiment_id") != artifact_id
        or provenance_receipt.get("consumer_kind") != "CLI_REPORT_BUNDLE"
        or provenance_receipt.get("status") != "PASS"
        or provenance_receipt.get("consumer_record_hash")
        != _canonical_hash(report_payload)
        or provenance_receipt.get("consumer_identity_hash")
        != _canonical_hash(artifact_identity)
        or provenance_receipt.get("source_manifest_hash")
        != manifest.get("manifest_hash")
        or provenance_receipt.get("result_hash")
        != _canonical_hash(result_payload)
        or binding.get("source_manifest_hash") != manifest.get("manifest_hash")
        or binding.get("result_hash") != _canonical_hash(result_payload)
        or not _self_hash_matches(binding, "manifest_hash")
        or not _self_hash_matches(provenance_receipt, "receipt_hash")
        or provenance_receipt.get("runtime_write_performed") is not False
        or provenance_receipt.get("paper_authorized") is not False
        or provenance_receipt.get("live_order_allowed") is not False
        or provenance_receipt.get("order_entry_allowed") is not False
        or provenance_receipt.get("result_is_profitability_proof") is not False
    ):
        raise ValueError("report bundle provenance receipt is invalid")
    core = {
        "schema_version": RESEARCH_JSON_REPORT_BUNDLE_SCHEMA_VERSION,
        "trust_model": RESEARCH_JSON_REPORT_BUNDLE_TRUST_MODEL,
        "external_artifact_hash_required": True,
        "artifact_identity": dict(artifact_identity),
        "report_payload": report_payload,
        "provenance_receipt": provenance_receipt,
        "research_only": True,
        "ranking_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "order_entry_allowed": False,
        "result_is_profitability_proof": False,
    }
    return {**core, "bundle_hash": _canonical_hash(core)}


def verify_json_report_bundle_v2(bundle: Any) -> bool:
    if type(bundle) is not dict:
        return False
    try:
        _require_native_json(bundle)
        if set(bundle) != _BUNDLE_FIELDS:
            return False
        expected = build_json_report_bundle_v2(
            bundle["report_payload"],
            bundle["provenance_receipt"],
            artifact_identity=bundle["artifact_identity"],
        )
    except (KeyError, TypeError, ValueError):
        return False
    return bundle == expected


def plan_json_report_path(directory: str, prefix: str, artifact_id: str) -> Path:
    """Validate report identity and return its deterministic destination path."""

    root = _validate_directory(directory)
    safe_prefix = _validate_prefix(prefix)
    digest = _validate_artifact_id(artifact_id)
    return root / f"{safe_prefix}_{digest}.json"


def save_json_report(
    payload: dict[str, Any],
    directory: str,
    prefix: str,
    *,
    artifact_id: str = "",
) -> str:
    """Keep the legacy report contract with atomic, no-replace persistence."""
    rendered = render_json_report(payload)
    report_path = plan_json_report_path(directory, prefix, artifact_id)
    from hakimi_research.reporting import _save_encoded_report
    return _save_encoded_report(rendered.encode("utf-8"), report_path)


def save_json_report_bundle_v2(
    bundle: dict[str, Any],
    directory: str,
) -> str:
    """Validate the unchanged v2 envelope before publishing complete bytes."""
    if not verify_json_report_bundle_v2(bundle):
        raise ValueError("report bundle verification failed")
    identity = bundle["artifact_identity"]
    rendered = render_json_report(bundle)
    report_path = plan_json_report_path(
        directory,
        identity["prefix"],
        identity["artifact_id"],
    )
    from hakimi_research.reporting import _save_encoded_report
    return _save_encoded_report(rendered.encode("utf-8"), report_path)


__all__ = [
    "RESEARCH_JSON_REPORT_BUNDLE_SCHEMA_VERSION",
    "RESEARCH_JSON_REPORT_BUNDLE_TRUST_MODEL",
    "RESEARCH_JSON_REPORT_SCHEMA_VERSION",
    "build_json_report_bundle_v2",
    "plan_json_report_path",
    "render_json_report",
    "save_json_report",
    "save_json_report_bundle_v2",
    "verify_json_report_bundle_v2",
]
