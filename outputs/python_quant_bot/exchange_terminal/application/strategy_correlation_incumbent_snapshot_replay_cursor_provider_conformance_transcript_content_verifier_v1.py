"""Local transcript content verification for ADR0481."""

from __future__ import annotations

import base64
from copy import deepcopy
from hashlib import sha256
import re
from typing import Any, Mapping

from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_conformance_plan_v1
    as conformance_plan,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_conformance_transcript_binding_v1
    as transcript_binding,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


CONTENT_BUNDLE_SCHEMA_VERSION = (
    "incumbent-snapshot-replay-cursor-provider-conformance-transcript-content-bundle-v1"
)
CONTENT_VERIFICATION_EVIDENCE_SCHEMA_VERSION = (
    "incumbent-snapshot-replay-cursor-provider-conformance-transcript-content-verification-evidence-v1"
)
STATIC_FINGERPRINT = (
    "20260825-replay-cursor-provider-transcript-content-v1-lock-1"
)
CONTENT_ENCODING = "base64url-no-padding"
MAX_CASE_COMPONENT_BYTES = 1 * 1024 * 1024
MAX_BUNDLE_TOTAL_BYTES = 16 * 1024 * 1024

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_B64URL_PATTERN = re.compile(r"^[A-Za-z0-9_-]*$")
_PAYLOAD_KEYS = frozenset(
    {
        "case_id",
        "transcript_artifact_base64url",
        "command_trace_base64url",
        "result_trace_base64url",
        "stdout_base64url",
        "stderr_base64url",
    }
)
_COMPONENTS = (
    ("transcript_artifact_base64url", "transcript_artifact_sha256"),
    ("command_trace_base64url", "command_trace_sha256"),
    ("result_trace_base64url", "result_trace_sha256"),
    ("stdout_base64url", "stdout_sha256"),
    ("stderr_base64url", "stderr_sha256"),
)
_PERMANENT_BLOCKERS = (
    "EXTERNAL_ARTIFACT_RETRIEVAL_UNVERIFIED",
    "PUBLIC_ARTIFACT_AVAILABILITY_UNVERIFIED",
    "EXTERNAL_PERSISTENCE_UNVERIFIED",
    "RUNNER_AND_ENVIRONMENT_SOURCE_TRUTH_UNVERIFIED",
    "OBSERVER_TEST_EXECUTION_SOURCE_TRUTH_UNVERIFIED",
    "EXTERNAL_PROVIDER_CONFORMANCE_UNVERIFIED",
    "CURRENT_ACTIVATION_UNAUTHORIZED",
)


def _is_hash(value: Any) -> bool:
    return type(value) is str and _HASH_PATTERN.fullmatch(value) is not None


def _require_hash(name: str, value: Any) -> str:
    if not _is_hash(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")
    return value


def _sealed_document_exact(document: Any, hash_field: str) -> bool:
    if type(document) is not dict or not _is_hash(document.get(hash_field)):
        return False
    body = deepcopy(document)
    expected_hash = body.pop(hash_field)
    rebuilt = seal_strict_canonical_document(body, hash_field)
    return (
        rebuilt[hash_field] == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )


def _decode_canonical_payload(name: str, value: Any) -> bytes:
    if (
        type(value) is not str
        or _B64URL_PATTERN.fullmatch(value) is None
        or "=" in value
    ):
        raise ValueError(f"{name} must be canonical base64url without padding")
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is not valid base64url") from exc
    canonical = base64.urlsafe_b64encode(decoded).decode("ascii").rstrip("=")
    if canonical != value:
        raise ValueError(f"{name} is not canonically encoded")
    if len(decoded) > MAX_CASE_COMPONENT_BYTES:
        raise ValueError(f"{name} exceeds the per-component byte limit")
    return decoded


def _validate_manifest_structure(
    transcript_manifest_document: Any,
    *,
    expected_transcript_manifest_hash: Any,
) -> tuple[str, list[Mapping[str, Any]]]:
    expected_hash = _require_hash(
        "expected_transcript_manifest_hash",
        expected_transcript_manifest_hash,
    )
    if (
        type(transcript_manifest_document) is not dict
        or transcript_manifest_document.get("schema_version")
        != transcript_binding.TRANSCRIPT_MANIFEST_SCHEMA_VERSION
        or transcript_manifest_document.get("transcript_manifest_hash")
        != expected_hash
        or not _sealed_document_exact(
            transcript_manifest_document, "transcript_manifest_hash"
        )
    ):
        raise ValueError("transcript manifest structure is not exact")
    observer_id = transcript_manifest_document.get("observer_id")
    manifest_rows = transcript_manifest_document.get("case_transcripts")
    if (
        type(observer_id) is not str
        or not observer_id
        or not isinstance(manifest_rows, list)
        or len(manifest_rows) != len(conformance_plan.EXPECTED_CASE_IDS)
        or not all(isinstance(row, Mapping) for row in manifest_rows)
    ):
        raise ValueError("transcript manifest identity or case rows are invalid")
    return observer_id, manifest_rows


def build_replay_cursor_provider_conformance_transcript_content_bundle_v1(
    transcript_manifest_document: Any,
    *,
    case_payload_rows: Any,
    expected_transcript_manifest_hash: Any,
) -> dict[str, Any]:
    observer_id, manifest_rows = _validate_manifest_structure(
        transcript_manifest_document,
        expected_transcript_manifest_hash=expected_transcript_manifest_hash,
    )
    if (
        type(case_payload_rows) is not list
        or len(case_payload_rows) != len(conformance_plan.EXPECTED_CASE_IDS)
    ):
        raise ValueError("content bundle must include every case")
    normalized_rows: list[dict[str, str]] = []
    total_bytes = 0
    component_count = 0
    for expected_case_id, payload_row, manifest_row in zip(
        conformance_plan.EXPECTED_CASE_IDS,
        case_payload_rows,
        manifest_rows,
        strict=True,
    ):
        if (
            type(payload_row) is not dict
            or frozenset(payload_row) != _PAYLOAD_KEYS
            or payload_row["case_id"] != expected_case_id
            or manifest_row.get("case_id") != expected_case_id
        ):
            raise ValueError("content bundle case order or shape drifted")
        normalized = {"case_id": expected_case_id}
        for payload_field, manifest_hash_field in _COMPONENTS:
            decoded = _decode_canonical_payload(
                payload_field, payload_row[payload_field]
            )
            if sha256(decoded).hexdigest() != manifest_row.get(
                manifest_hash_field
            ):
                raise ValueError(
                    f"{payload_field} does not match the manifest content hash"
                )
            total_bytes += len(decoded)
            component_count += 1
            if total_bytes > MAX_BUNDLE_TOTAL_BYTES:
                raise ValueError("content bundle exceeds the total byte limit")
            normalized[payload_field] = payload_row[payload_field]
        normalized_rows.append(normalized)
    body = {
        "schema_version": CONTENT_BUNDLE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "LOCAL_CONTENT_VERIFIED",
        "admission_status": "BLOCKED",
        "observer_id": observer_id,
        "source": {
            "transcript_manifest_hash": expected_transcript_manifest_hash,
            "content_encoding": CONTENT_ENCODING,
        },
        "case_payloads": normalized_rows,
        "summary": {
            "case_count": len(normalized_rows),
            "component_count": component_count,
            "total_payload_bytes": total_bytes,
            "per_component_byte_limit": MAX_CASE_COMPONENT_BYTES,
            "bundle_total_byte_limit": MAX_BUNDLE_TOTAL_BYTES,
            "all_component_hashes_verified": True,
        },
        "facts": {
            "local_payload_bytes_supplied": True,
            "local_component_hashes_verified": True,
            "local_component_sizes_bounded": True,
            "external_artifact_retrieval_verified": False,
            "public_artifact_availability_verified": False,
            "external_persistence_verified": False,
            "provider_called_by_builder": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
            "runtime_mutations_performed": False,
            "execution_verified": False,
            "profitability_proven": False,
        },
        "authority": {
            "descriptive_only": True,
            "artifact_availability_trust_allowed": False,
            "provider_conformance_trust_allowed": False,
            "provider_activation_allowed": False,
            "current_admission_allowed": False,
            "runtime_gate_activation_allowed": False,
            "writer_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
            "trading_allowed": False,
        },
    }
    return seal_strict_canonical_document(body, "content_bundle_hash")


def verify_replay_cursor_provider_conformance_transcript_content_bundle_v1(
    content_bundle_document: Any,
    transcript_manifest_document: Any,
    *,
    expected_content_bundle_hash: Any,
) -> bool:
    if type(content_bundle_document) is not dict or not _is_hash(
        expected_content_bundle_hash
    ):
        return False
    source = content_bundle_document.get("source")
    rows = content_bundle_document.get("case_payloads")
    if not isinstance(source, Mapping) or not isinstance(rows, list):
        return False
    try:
        expected = build_replay_cursor_provider_conformance_transcript_content_bundle_v1(
            transcript_manifest_document,
            case_payload_rows=rows,
            expected_transcript_manifest_hash=source[
                "transcript_manifest_hash"
            ],
        )
    except (KeyError, TypeError, ValueError):
        return False
    return (
        expected["content_bundle_hash"] == expected_content_bundle_hash
        and strict_json_contract_equal(content_bundle_document, expected)
    )


def evaluate_replay_cursor_provider_conformance_transcript_content_v1(
    content_bundle_documents: Any,
    transcript_binding_document: Any,
    transcript_manifest_documents: Any,
    quorum_evidence_document: Any,
    signed_report_documents: Any,
    plan_document: Any,
    provider_preregistration_document: Any,
    signed_receipt_evidence_document: Any,
    *,
    expected_transcript_binding_hash: Any,
    transcript_binding_verify_kwargs: Any,
) -> dict[str, Any]:
    upstream_binding_exact = False
    if (
        type(transcript_binding_verify_kwargs) is dict
        and "expected_transcript_binding_hash"
        not in transcript_binding_verify_kwargs
    ):
        try:
            upstream_binding_exact = transcript_binding.verify_replay_cursor_provider_conformance_transcript_binding_v1(
                transcript_binding_document,
                transcript_manifest_documents,
                quorum_evidence_document,
                signed_report_documents,
                plan_document,
                provider_preregistration_document,
                signed_receipt_evidence_document,
                expected_transcript_binding_hash=(
                    expected_transcript_binding_hash
                ),
                **dict(transcript_binding_verify_kwargs),
            )
        except (KeyError, TypeError, ValueError):
            upstream_binding_exact = False
    if (
        not isinstance(transcript_binding_document, Mapping)
        or transcript_binding_document.get("status") != "PASS"
        or transcript_binding_document.get("admission_status") != "BLOCKED"
    ):
        upstream_binding_exact = False

    manifests = (
        transcript_manifest_documents
        if type(transcript_manifest_documents) is list
        else []
    )
    manifest_by_observer = {
        row.get("observer_id"): row
        for row in manifests
        if isinstance(row, Mapping) and type(row.get("observer_id")) is str
    }
    expected_ids = (
        transcript_binding_document.get("binding_summary", {}).get(
            "bound_observer_ids", []
        )
        if isinstance(transcript_binding_document, Mapping)
        else []
    )
    bundles = content_bundle_documents if type(content_bundle_documents) is list else []
    bundle_results: list[dict[str, Any]] = []
    seen_ids: list[str] = []
    total_verified_bytes = 0
    for bundle in bundles:
        observer_id = (
            bundle.get("observer_id") if isinstance(bundle, Mapping) else None
        )
        bundle_hash = (
            bundle.get("content_bundle_hash")
            if isinstance(bundle, Mapping)
            else None
        )
        exact = False
        manifest = manifest_by_observer.get(observer_id)
        if upstream_binding_exact and manifest is not None:
            exact = verify_replay_cursor_provider_conformance_transcript_content_bundle_v1(
                bundle,
                manifest,
                expected_content_bundle_hash=bundle_hash,
            )
        row_pass = exact and observer_id in expected_ids
        verified_bytes = (
            bundle.get("summary", {}).get("total_payload_bytes", 0)
            if row_pass and isinstance(bundle, Mapping)
            else 0
        )
        if type(verified_bytes) is int:
            total_verified_bytes += verified_bytes
        if type(observer_id) is str:
            seen_ids.append(observer_id)
        bundle_results.append(
            {
                "observer_id": observer_id,
                "content_bundle_hash": (
                    bundle_hash if _is_hash(bundle_hash) else None
                ),
                "bundle_exact": exact,
                "observer_in_bound_manifest_set": observer_id in expected_ids,
                "verified_payload_bytes": verified_bytes,
                "status": "PASS" if row_pass else "BLOCK",
            }
        )
    bundle_results.sort(
        key=lambda row: (
            str(row["observer_id"]), str(row["content_bundle_hash"])
        )
    )
    duplicate_observer_ids = len(seen_ids) != len(set(seen_ids))
    verified_ids = sorted(
        row["observer_id"]
        for row in bundle_results
        if row["status"] == "PASS"
    )
    expected_ids = sorted(expected_ids) if type(expected_ids) is list else []
    all_bound_content_verified = (
        upstream_binding_exact
        and not duplicate_observer_ids
        and verified_ids == expected_ids
        and len(verified_ids) >= 2
    )
    dynamic_blockers: list[str] = []
    if not upstream_binding_exact:
        dynamic_blockers.append("UPSTREAM_TRANSCRIPT_BINDING_NOT_EXACT")
    if duplicate_observer_ids:
        dynamic_blockers.append("DUPLICATE_CONTENT_BUNDLE_OBSERVER_ID")
    if verified_ids != expected_ids or len(verified_ids) < 2:
        dynamic_blockers.append("BOUND_OBSERVER_CONTENT_BUNDLE_SET_INCOMPLETE")
    body = {
        "schema_version": CONTENT_VERIFICATION_EVIDENCE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if all_bound_content_verified else "BLOCK",
        "admission_status": "BLOCKED",
        "content_status": (
            "LOCAL_TRANSCRIPT_COMPONENT_BYTES_HASH_VERIFIED"
            if all_bound_content_verified
            else "UNKNOWN"
        ),
        "decision": (
            "LOCAL_CONTENT_HASH_AND_SIZE_VERIFIED_EXTERNAL_AVAILABILITY_BLOCKED"
            if all_bound_content_verified
            else "TRANSCRIPT_CONTENT_UNKNOWN_OR_INVALID"
        ),
        "blockers": dynamic_blockers + list(_PERMANENT_BLOCKERS),
        "bundle_results": bundle_results,
        "verification_summary": {
            "bound_observer_ids": expected_ids,
            "content_verified_observer_ids": verified_ids,
            "duplicate_observer_ids": duplicate_observer_ids,
            "total_locally_verified_payload_bytes": total_verified_bytes,
            "all_bound_content_verified": all_bound_content_verified,
        },
        "facts": {
            "upstream_transcript_binding_exact": upstream_binding_exact,
            "all_bound_content_bundles_exact": all_bound_content_verified,
            "local_component_hashes_verified": all_bound_content_verified,
            "local_component_sizes_bounded": all_bound_content_verified,
            "external_artifact_retrieval_verified": False,
            "public_artifact_availability_verified": False,
            "external_persistence_verified": False,
            "runner_implementation_verified": False,
            "environment_manifest_verified": False,
            "observer_test_execution_source_truth_verified": False,
            "external_provider_conformance_verified": False,
            "provider_called_by_evaluator": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
            "runtime_mutations_performed": False,
            "execution_verified": False,
            "profitability_proven": False,
        },
        "source": {
            "transcript_binding_hash": (
                expected_transcript_binding_hash
                if _is_hash(expected_transcript_binding_hash)
                else None
            ),
            "content_encoding": CONTENT_ENCODING,
        },
        "authority": {
            "descriptive_only": True,
            "artifact_availability_trust_allowed": False,
            "provider_conformance_trust_allowed": False,
            "provider_activation_allowed": False,
            "current_admission_allowed": False,
            "runtime_gate_activation_allowed": False,
            "writer_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
            "trading_allowed": False,
        },
        "redaction": {
            "raw_transcript_artifacts_embedded": False,
            "raw_command_or_result_traces_embedded": False,
            "raw_stdout_or_stderr_embedded": False,
            "raw_content_bundles_embedded": False,
            "raw_runtime_state_embedded": False,
        },
        "limitations": [
            "Local verification proves only that caller-supplied bytes match the hashes and bounds committed by ADR0480.",
            "It does not prove external retrieval, public availability, persistence, runner/environment provenance, observer execution, or provider conformance.",
            "No current, runtime, writer, paper, live, execution, profitability, or trading authority is granted.",
        ],
    }
    return seal_strict_canonical_document(body, "content_verification_hash")


def verify_replay_cursor_provider_conformance_transcript_content_v1(
    evidence_document: Any,
    content_bundle_documents: Any,
    transcript_binding_document: Any,
    transcript_manifest_documents: Any,
    quorum_evidence_document: Any,
    signed_report_documents: Any,
    plan_document: Any,
    provider_preregistration_document: Any,
    signed_receipt_evidence_document: Any,
    *,
    expected_content_verification_hash: Any,
    **evaluation_kwargs: Any,
) -> bool:
    if not _is_hash(expected_content_verification_hash):
        return False
    expected = evaluate_replay_cursor_provider_conformance_transcript_content_v1(
        content_bundle_documents,
        transcript_binding_document,
        transcript_manifest_documents,
        quorum_evidence_document,
        signed_report_documents,
        plan_document,
        provider_preregistration_document,
        signed_receipt_evidence_document,
        **evaluation_kwargs,
    )
    return (
        expected["content_verification_hash"]
        == expected_content_verification_hash
        and strict_json_contract_equal(evidence_document, expected)
    )


__all__ = [
    "CONTENT_BUNDLE_SCHEMA_VERSION",
    "CONTENT_ENCODING",
    "CONTENT_VERIFICATION_EVIDENCE_SCHEMA_VERSION",
    "MAX_BUNDLE_TOTAL_BYTES",
    "MAX_CASE_COMPONENT_BYTES",
    "STATIC_FINGERPRINT",
    "build_replay_cursor_provider_conformance_transcript_content_bundle_v1",
    "evaluate_replay_cursor_provider_conformance_transcript_content_v1",
    "verify_replay_cursor_provider_conformance_transcript_content_bundle_v1",
    "verify_replay_cursor_provider_conformance_transcript_content_v1",
]
