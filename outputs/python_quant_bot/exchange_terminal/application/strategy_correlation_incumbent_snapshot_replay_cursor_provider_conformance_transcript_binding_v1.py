"""Signed-report to transcript-manifest binding for ADR0480."""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any, Mapping

from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_conformance_evidence_v1
    as conformance_evidence,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_conformance_plan_v1
    as conformance_plan,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


CASE_TRANSCRIPT_EVIDENCE_SCHEMA_VERSION = (
    "incumbent-snapshot-replay-cursor-provider-conformance-case-transcript-evidence-v1"
)
TRANSCRIPT_MANIFEST_SCHEMA_VERSION = (
    "incumbent-snapshot-replay-cursor-provider-conformance-transcript-manifest-v1"
)
TRANSCRIPT_BINDING_EVIDENCE_SCHEMA_VERSION = (
    "incumbent-snapshot-replay-cursor-provider-conformance-transcript-binding-evidence-v1"
)
STATIC_FINGERPRINT = (
    "20260825-replay-cursor-provider-transcript-binding-v1-lock-1"
)

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_]{2,127}$")
_CASE_TRANSCRIPT_KEYS = frozenset(
    {
        "case_id",
        "status",
        "transcript_artifact_sha256",
        "command_trace_sha256",
        "result_trace_sha256",
        "stdout_sha256",
        "stderr_sha256",
        "attempt_count",
    }
)
_PERMANENT_BLOCKERS = (
    "TRANSCRIPT_ARTIFACT_RETRIEVABILITY_UNVERIFIED",
    "RUNNER_IMPLEMENTATION_SOURCE_TRUTH_UNVERIFIED",
    "ENVIRONMENT_MANIFEST_SOURCE_TRUTH_UNVERIFIED",
    "OBSERVER_TEST_EXECUTION_SOURCE_TRUTH_UNVERIFIED",
    "OBSERVER_IDENTITY_AND_INDEPENDENCE_UNVERIFIED",
    "EXTERNAL_PROVIDER_CONFORMANCE_UNVERIFIED",
    "CURRENT_ACTIVATION_UNAUTHORIZED",
)


def _is_hash(value: Any) -> bool:
    return type(value) is str and _HASH_PATTERN.fullmatch(value) is not None


def _require_hash(name: str, value: Any) -> str:
    if not _is_hash(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")
    return value


def _require_case_id(value: Any) -> str:
    if type(value) is not str or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        raise ValueError("case_id must be a bounded uppercase identifier")
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


def build_replay_cursor_provider_conformance_case_transcript_evidence_hash_v1(
    *,
    case_id: Any,
    status: Any,
    run_context_hash: Any,
    runner_implementation_sha256: Any,
    environment_manifest_sha256: Any,
    transcript_artifact_sha256: Any,
    command_trace_sha256: Any,
    result_trace_sha256: Any,
    stdout_sha256: Any,
    stderr_sha256: Any,
    attempt_count: Any,
) -> str:
    case = _require_case_id(case_id)
    if status not in ("PASS", "FAIL"):
        raise ValueError("case transcript status must be PASS or FAIL")
    if type(attempt_count) is not int or attempt_count < 1:
        raise ValueError("attempt_count must be a positive integer")
    return strict_canonical_hash(
        {
            "schema_version": CASE_TRANSCRIPT_EVIDENCE_SCHEMA_VERSION,
            "case_id": case,
            "status": status,
            "run_context_hash": _require_hash(
                "run_context_hash", run_context_hash
            ),
            "runner_implementation_sha256": _require_hash(
                "runner_implementation_sha256",
                runner_implementation_sha256,
            ),
            "environment_manifest_sha256": _require_hash(
                "environment_manifest_sha256",
                environment_manifest_sha256,
            ),
            "transcript_artifact_sha256": _require_hash(
                "transcript_artifact_sha256",
                transcript_artifact_sha256,
            ),
            "command_trace_sha256": _require_hash(
                "command_trace_sha256", command_trace_sha256
            ),
            "result_trace_sha256": _require_hash(
                "result_trace_sha256", result_trace_sha256
            ),
            "stdout_sha256": _require_hash(
                "stdout_sha256", stdout_sha256
            ),
            "stderr_sha256": _require_hash(
                "stderr_sha256", stderr_sha256
            ),
            "attempt_count": attempt_count,
        }
    )


def _validate_signed_report_structure(
    signed_observer_report_document: Any,
    plan_document: Any,
    signed_receipt_evidence_document: Any,
    *,
    expected_signed_observer_report_hash: Any,
) -> Mapping[str, Any]:
    expected_hash = _require_hash(
        "expected_signed_observer_report_hash",
        expected_signed_observer_report_hash,
    )
    if (
        type(signed_observer_report_document) is not dict
        or type(plan_document) is not dict
        or type(signed_receipt_evidence_document) is not dict
        or signed_observer_report_document.get("schema_version")
        != conformance_evidence.SIGNED_OBSERVER_REPORT_SCHEMA_VERSION
        or signed_observer_report_document.get("signed_observer_report_hash")
        != expected_hash
        or not _sealed_document_exact(
            signed_observer_report_document,
            "signed_observer_report_hash",
        )
    ):
        raise ValueError("signed observer report structure is not exact")
    report = signed_observer_report_document.get("observer_report")
    if not isinstance(report, Mapping):
        raise ValueError("embedded observer report is missing")
    source = report.get("source")
    observer = report.get("observer")
    if (
        not isinstance(source, Mapping)
        or not isinstance(observer, Mapping)
        or report.get("schema_version")
        != conformance_evidence.OBSERVER_REPORT_SCHEMA_VERSION
        or signed_observer_report_document.get("observer_id")
        != observer.get("observer_id")
        or signed_observer_report_document.get("observer_report_hash")
        != report.get("observer_report_hash")
        or source.get("conformance_plan_hash")
        != plan_document.get("conformance_plan_hash")
        or source.get("signed_receipt_evidence_hash")
        != signed_receipt_evidence_document.get(
            "verification_evidence_hash"
        )
    ):
        raise ValueError("signed observer report source binding drifted")
    return report


def _normalize_case_transcripts(
    case_transcript_rows: Any,
    report: Mapping[str, Any],
    *,
    runner_implementation_sha256: str,
    environment_manifest_sha256: str,
) -> list[dict[str, Any]]:
    report_cases = report.get("cases")
    source = report.get("source")
    if (
        type(case_transcript_rows) is not list
        or not isinstance(report_cases, list)
        or len(case_transcript_rows) != len(conformance_plan.EXPECTED_CASE_IDS)
        or len(report_cases) != len(conformance_plan.EXPECTED_CASE_IDS)
        or not isinstance(source, Mapping)
    ):
        raise ValueError("transcript manifest case count is not exact")
    run_context_hash = _require_hash(
        "run_context_hash", source.get("run_context_hash")
    )
    normalized: list[dict[str, Any]] = []
    for expected_case_id, transcript_row, report_row in zip(
        conformance_plan.EXPECTED_CASE_IDS,
        case_transcript_rows,
        report_cases,
        strict=True,
    ):
        if (
            type(transcript_row) is not dict
            or frozenset(transcript_row) != _CASE_TRANSCRIPT_KEYS
            or not isinstance(report_row, Mapping)
            or transcript_row["case_id"] != expected_case_id
            or report_row.get("case_id") != expected_case_id
            or transcript_row["status"] != report_row.get("status")
        ):
            raise ValueError("case transcript/report order or status drifted")
        computed_hash = (
            build_replay_cursor_provider_conformance_case_transcript_evidence_hash_v1(
                case_id=transcript_row["case_id"],
                status=transcript_row["status"],
                run_context_hash=run_context_hash,
                runner_implementation_sha256=(
                    runner_implementation_sha256
                ),
                environment_manifest_sha256=(
                    environment_manifest_sha256
                ),
                transcript_artifact_sha256=transcript_row[
                    "transcript_artifact_sha256"
                ],
                command_trace_sha256=transcript_row[
                    "command_trace_sha256"
                ],
                result_trace_sha256=transcript_row[
                    "result_trace_sha256"
                ],
                stdout_sha256=transcript_row["stdout_sha256"],
                stderr_sha256=transcript_row["stderr_sha256"],
                attempt_count=transcript_row["attempt_count"],
            )
        )
        if computed_hash != report_row.get("evidence_hash"):
            raise ValueError(
                "case transcript descriptor does not match signed evidence hash"
            )
        normalized.append(
            {
                "case_id": expected_case_id,
                "status": transcript_row["status"],
                "report_evidence_hash": computed_hash,
                "transcript_artifact_sha256": transcript_row[
                    "transcript_artifact_sha256"
                ],
                "command_trace_sha256": transcript_row[
                    "command_trace_sha256"
                ],
                "result_trace_sha256": transcript_row[
                    "result_trace_sha256"
                ],
                "stdout_sha256": transcript_row["stdout_sha256"],
                "stderr_sha256": transcript_row["stderr_sha256"],
                "attempt_count": transcript_row["attempt_count"],
            }
        )
    return normalized


def build_replay_cursor_provider_conformance_transcript_manifest_v1(
    signed_observer_report_document: Any,
    plan_document: Any,
    signed_receipt_evidence_document: Any,
    *,
    runner_implementation_sha256: Any,
    environment_manifest_sha256: Any,
    case_transcript_rows: Any,
    expected_signed_observer_report_hash: Any,
) -> dict[str, Any]:
    report = _validate_signed_report_structure(
        signed_observer_report_document,
        plan_document,
        signed_receipt_evidence_document,
        expected_signed_observer_report_hash=(
            expected_signed_observer_report_hash
        ),
    )
    runner_hash = _require_hash(
        "runner_implementation_sha256", runner_implementation_sha256
    )
    environment_hash = _require_hash(
        "environment_manifest_sha256", environment_manifest_sha256
    )
    rows = _normalize_case_transcripts(
        case_transcript_rows,
        report,
        runner_implementation_sha256=runner_hash,
        environment_manifest_sha256=environment_hash,
    )
    body = {
        "schema_version": TRANSCRIPT_MANIFEST_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "STRUCTURALLY_BOUND",
        "admission_status": "BLOCKED",
        "decision": (
            "SIGNED_REPORT_CASE_HASHES_BOUND_TO_COMPLETE_TRANSCRIPT_"
            "DESCRIPTORS_EXECUTION_SOURCE_TRUTH_UNVERIFIED"
        ),
        "observer_id": report["observer"]["observer_id"],
        "source": {
            "signed_observer_report_hash": (
                expected_signed_observer_report_hash
            ),
            "observer_report_hash": report["observer_report_hash"],
            "conformance_plan_hash": report["source"][
                "conformance_plan_hash"
            ],
            "signed_receipt_evidence_hash": report["source"][
                "signed_receipt_evidence_hash"
            ],
            "run_context_hash": report["source"]["run_context_hash"],
            "runner_implementation_sha256": runner_hash,
            "environment_manifest_sha256": environment_hash,
        },
        "case_transcripts": rows,
        "summary": {
            "required_case_count": len(rows),
            "bound_case_count": len(rows),
            "all_report_evidence_hashes_bound": True,
        },
        "facts": {
            "signed_report_structure_exact": True,
            "all_case_transcript_descriptors_complete": True,
            "all_report_evidence_hashes_bound": True,
            "transcript_artifacts_retrieved": False,
            "transcript_artifact_content_verified": False,
            "runner_implementation_verified": False,
            "environment_manifest_verified": False,
            "observer_test_execution_source_truth_verified": False,
            "provider_called_by_builder": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
            "runtime_mutations_performed": False,
            "execution_verified": False,
            "profitability_proven": False,
        },
        "authority": {
            "descriptive_only": True,
            "transcript_trust_allowed": False,
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
    return seal_strict_canonical_document(body, "transcript_manifest_hash")


def verify_replay_cursor_provider_conformance_transcript_manifest_v1(
    manifest_document: Any,
    signed_observer_report_document: Any,
    plan_document: Any,
    signed_receipt_evidence_document: Any,
    *,
    expected_transcript_manifest_hash: Any,
) -> bool:
    if type(manifest_document) is not dict or not _is_hash(
        expected_transcript_manifest_hash
    ):
        return False
    source = manifest_document.get("source")
    rows = manifest_document.get("case_transcripts")
    if not isinstance(source, Mapping) or not isinstance(rows, list):
        return False
    raw_rows = [
        {
            "case_id": row.get("case_id"),
            "status": row.get("status"),
            "transcript_artifact_sha256": row.get(
                "transcript_artifact_sha256"
            ),
            "command_trace_sha256": row.get("command_trace_sha256"),
            "result_trace_sha256": row.get("result_trace_sha256"),
            "stdout_sha256": row.get("stdout_sha256"),
            "stderr_sha256": row.get("stderr_sha256"),
            "attempt_count": row.get("attempt_count"),
        }
        for row in rows
        if isinstance(row, Mapping)
    ]
    try:
        expected = build_replay_cursor_provider_conformance_transcript_manifest_v1(
            signed_observer_report_document,
            plan_document,
            signed_receipt_evidence_document,
            runner_implementation_sha256=source[
                "runner_implementation_sha256"
            ],
            environment_manifest_sha256=source[
                "environment_manifest_sha256"
            ],
            case_transcript_rows=raw_rows,
            expected_signed_observer_report_hash=source[
                "signed_observer_report_hash"
            ],
        )
    except (KeyError, TypeError, ValueError):
        return False
    return (
        expected["transcript_manifest_hash"]
        == expected_transcript_manifest_hash
        and strict_json_contract_equal(manifest_document, expected)
    )


def evaluate_replay_cursor_provider_conformance_transcript_binding_v1(
    transcript_manifest_documents: Any,
    quorum_evidence_document: Any,
    signed_report_documents: Any,
    plan_document: Any,
    provider_preregistration_document: Any,
    signed_receipt_evidence_document: Any,
    *,
    expected_quorum_evidence_hash: Any,
    quorum_verify_kwargs: Any,
) -> dict[str, Any]:
    upstream_quorum_exact = False
    if (
        type(quorum_verify_kwargs) is dict
        and "expected_quorum_evidence_hash" not in quorum_verify_kwargs
    ):
        try:
            upstream_quorum_exact = conformance_evidence.verify_replay_cursor_provider_conformance_observer_quorum_v1(
                quorum_evidence_document,
                signed_report_documents,
                plan_document,
                provider_preregistration_document,
                signed_receipt_evidence_document,
                expected_quorum_evidence_hash=(
                    expected_quorum_evidence_hash
                ),
                **dict(quorum_verify_kwargs),
            )
        except (KeyError, TypeError, ValueError):
            upstream_quorum_exact = False
    if (
        not isinstance(quorum_evidence_document, Mapping)
        or quorum_evidence_document.get("status") != "PASS"
        or quorum_evidence_document.get("admission_status") != "BLOCKED"
    ):
        upstream_quorum_exact = False

    signed_rows = signed_report_documents if type(signed_report_documents) is list else []
    signed_by_observer = {
        row.get("observer_id"): row
        for row in signed_rows
        if isinstance(row, Mapping) and type(row.get("observer_id")) is str
    }
    passing_ids = (
        quorum_evidence_document.get("quorum_summary", {}).get(
            "passing_observer_ids", []
        )
        if isinstance(quorum_evidence_document, Mapping)
        else []
    )
    manifests = (
        transcript_manifest_documents
        if type(transcript_manifest_documents) is list
        else []
    )
    manifest_results: list[dict[str, Any]] = []
    seen_ids: list[str] = []
    for manifest in manifests:
        observer_id = (
            manifest.get("observer_id")
            if isinstance(manifest, Mapping)
            else None
        )
        manifest_hash = (
            manifest.get("transcript_manifest_hash")
            if isinstance(manifest, Mapping)
            else None
        )
        exact = False
        signed_report = signed_by_observer.get(observer_id)
        if upstream_quorum_exact and signed_report is not None:
            exact = verify_replay_cursor_provider_conformance_transcript_manifest_v1(
                manifest,
                signed_report,
                plan_document,
                signed_receipt_evidence_document,
                expected_transcript_manifest_hash=manifest_hash,
            )
        row_pass = exact and observer_id in passing_ids
        if type(observer_id) is str:
            seen_ids.append(observer_id)
        manifest_results.append(
            {
                "observer_id": observer_id,
                "transcript_manifest_hash": (
                    manifest_hash if _is_hash(manifest_hash) else None
                ),
                "manifest_exact": exact,
                "observer_in_passing_quorum": observer_id in passing_ids,
                "status": "PASS" if row_pass else "BLOCK",
            }
        )
    manifest_results.sort(
        key=lambda row: (
            str(row["observer_id"]),
            str(row["transcript_manifest_hash"]),
        )
    )
    duplicate_observer_ids = len(seen_ids) != len(set(seen_ids))
    bound_ids = sorted(
        row["observer_id"]
        for row in manifest_results
        if row["status"] == "PASS"
    )
    expected_ids = sorted(passing_ids) if type(passing_ids) is list else []
    all_passing_reports_bound = (
        upstream_quorum_exact
        and not duplicate_observer_ids
        and bound_ids == expected_ids
        and len(bound_ids) >= 2
    )
    dynamic_blockers: list[str] = []
    if not upstream_quorum_exact:
        dynamic_blockers.append("UPSTREAM_OBSERVER_QUORUM_NOT_EXACT")
    if duplicate_observer_ids:
        dynamic_blockers.append("DUPLICATE_TRANSCRIPT_MANIFEST_OBSERVER_ID")
    if bound_ids != expected_ids or len(bound_ids) < 2:
        dynamic_blockers.append("PASSING_OBSERVER_TRANSCRIPT_MANIFEST_SET_INCOMPLETE")
    body = {
        "schema_version": TRANSCRIPT_BINDING_EVIDENCE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if all_passing_reports_bound else "BLOCK",
        "admission_status": "BLOCKED",
        "transcript_status": (
            "SIGNED_REPORT_CASE_HASHES_STRUCTURALLY_BOUND_LOCAL_ONLY"
            if all_passing_reports_bound
            else "UNKNOWN"
        ),
        "decision": (
            "COMPLETE_TRANSCRIPT_MANIFEST_HASH_BINDING_VERIFIED_"
            "EXECUTION_SOURCE_TRUTH_BLOCKED"
            if all_passing_reports_bound
            else "TRANSCRIPT_MANIFEST_BINDING_UNKNOWN_OR_INVALID"
        ),
        "blockers": dynamic_blockers + list(_PERMANENT_BLOCKERS),
        "manifest_results": manifest_results,
        "binding_summary": {
            "passing_observer_ids": expected_ids,
            "bound_observer_ids": bound_ids,
            "duplicate_observer_ids": duplicate_observer_ids,
            "all_passing_reports_bound": all_passing_reports_bound,
        },
        "facts": {
            "upstream_observer_quorum_exact": upstream_quorum_exact,
            "all_passing_reports_have_exact_transcript_manifests": (
                all_passing_reports_bound
            ),
            "all_case_transcript_evidence_hashes_bound": (
                all_passing_reports_bound
            ),
            "transcript_artifacts_retrieved": False,
            "transcript_artifact_content_verified": False,
            "runner_implementation_verified": False,
            "environment_manifest_verified": False,
            "observer_test_execution_source_truth_verified": False,
            "observer_identities_verified": False,
            "observer_independence_source_truth_verified": False,
            "external_provider_conformance_verified": False,
            "atomic_compare_and_advance_verified": False,
            "durable_commit_verified": False,
            "linearizable_read_after_write_verified": False,
            "rollback_resistance_verified": False,
            "provider_called_by_evaluator": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
            "runtime_mutations_performed": False,
            "execution_verified": False,
            "profitability_proven": False,
        },
        "source": {
            "quorum_evidence_hash": (
                expected_quorum_evidence_hash
                if _is_hash(expected_quorum_evidence_hash)
                else None
            ),
            "conformance_plan_hash": (
                plan_document.get("conformance_plan_hash")
                if isinstance(plan_document, Mapping)
                else None
            ),
            "signed_receipt_evidence_hash": (
                signed_receipt_evidence_document.get(
                    "verification_evidence_hash"
                )
                if isinstance(signed_receipt_evidence_document, Mapping)
                else None
            ),
        },
        "authority": {
            "descriptive_only": True,
            "transcript_trust_allowed": False,
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
            "raw_observer_public_keys_redacted": True,
            "raw_observer_signatures_redacted": True,
            "raw_runtime_state_embedded": False,
        },
        "limitations": [
            "The binding proves only that signed report evidence hashes commit to complete transcript descriptors.",
            "It does not retrieve artifacts or prove runner, environment, observer identity, independence, test execution, provider conformance, atomicity, durability, linearizability, or rollback resistance.",
            "No current, runtime, writer, paper, live, execution, profitability, or trading authority is granted.",
        ],
    }
    return seal_strict_canonical_document(body, "transcript_binding_hash")


def verify_replay_cursor_provider_conformance_transcript_binding_v1(
    binding_document: Any,
    transcript_manifest_documents: Any,
    quorum_evidence_document: Any,
    signed_report_documents: Any,
    plan_document: Any,
    provider_preregistration_document: Any,
    signed_receipt_evidence_document: Any,
    *,
    expected_transcript_binding_hash: Any,
    **evaluation_kwargs: Any,
) -> bool:
    if not _is_hash(expected_transcript_binding_hash):
        return False
    expected = evaluate_replay_cursor_provider_conformance_transcript_binding_v1(
        transcript_manifest_documents,
        quorum_evidence_document,
        signed_report_documents,
        plan_document,
        provider_preregistration_document,
        signed_receipt_evidence_document,
        **evaluation_kwargs,
    )
    return (
        expected["transcript_binding_hash"]
        == expected_transcript_binding_hash
        and strict_json_contract_equal(binding_document, expected)
    )


__all__ = [
    "CASE_TRANSCRIPT_EVIDENCE_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "TRANSCRIPT_BINDING_EVIDENCE_SCHEMA_VERSION",
    "TRANSCRIPT_MANIFEST_SCHEMA_VERSION",
    "build_replay_cursor_provider_conformance_case_transcript_evidence_hash_v1",
    "build_replay_cursor_provider_conformance_transcript_manifest_v1",
    "evaluate_replay_cursor_provider_conformance_transcript_binding_v1",
    "verify_replay_cursor_provider_conformance_transcript_binding_v1",
    "verify_replay_cursor_provider_conformance_transcript_manifest_v1",
]
