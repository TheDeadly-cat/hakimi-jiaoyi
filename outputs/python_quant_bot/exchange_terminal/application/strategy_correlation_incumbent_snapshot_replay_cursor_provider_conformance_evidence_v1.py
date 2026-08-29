"""Signed independent-observer replay-cursor conformance claims for ADR0479."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import re
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature

from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_conformance_plan_v1
    as conformance_plan,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_signed_receipt_v1
    as signed_receipt,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_ed25519_public_contract_v1 import (
    decode_canonical_base64_v1,
    load_canonical_ed25519_public_key_v1,
)


OBSERVER_REPORT_SCHEMA_VERSION = (
    "incumbent-snapshot-replay-cursor-provider-conformance-observer-report-v1"
)
SIGNED_OBSERVER_REPORT_SCHEMA_VERSION = (
    "incumbent-snapshot-replay-cursor-provider-conformance-signed-observer-report-v1"
)
QUORUM_EVIDENCE_SCHEMA_VERSION = (
    "incumbent-snapshot-replay-cursor-provider-conformance-observer-quorum-evidence-v1"
)
STATIC_FINGERPRINT = (
    "20260825-replay-cursor-provider-observer-quorum-v1-lock-1"
)
SIGNATURE_ALGORITHM = "ED25519"
SIGNATURE_MESSAGE_FORMAT = (
    "STRICT_CANONICAL_DOMAIN_SEPARATED_SHA256_DIGEST_BYTES_V1"
)
SIGNATURE_DOMAIN = (
    "hakimi.strategy-correlation.incumbent-snapshot.replay-cursor."
    "provider-conformance-observer.v1"
)

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")
_CASE_KEYS = frozenset({"case_id", "status", "evidence_hash"})
_PERMANENT_BLOCKERS = (
    "OBSERVER_IDENTITIES_UNVERIFIED",
    "OBSERVER_KEY_CONTROL_CONTINUITY_UNVERIFIED",
    "OBSERVER_INDEPENDENCE_SOURCE_TRUTH_UNVERIFIED",
    "OBSERVER_TEST_EXECUTION_SOURCE_TRUTH_UNVERIFIED",
    "PROVIDER_ENDPOINT_AND_IMPLEMENTATION_UNVERIFIED",
    "EXTERNAL_PROVIDER_CONFORMANCE_UNVERIFIED",
    "ATOMICITY_DURABILITY_LINEARIZABILITY_AND_ROLLBACK_UNVERIFIED",
    "CURRENT_ACTIVATION_UNAUTHORIZED",
)


def _is_hash(value: Any) -> bool:
    return type(value) is str and _HASH_PATTERN.fullmatch(value) is not None


def _require_hash(name: str, value: Any) -> str:
    if not _is_hash(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")
    return value


def _require_identifier(name: str, value: Any) -> str:
    if type(value) is not str or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{name} must be a bounded lowercase identifier")
    return value


def _decode_public_key(value: Any):
    if type(value) is not str or not value:
        raise ValueError("public_key_spki_base64 must be non-empty")
    spki_bytes = decode_canonical_base64_v1(
        value, "public_key_spki_base64"
    )
    return spki_bytes, load_canonical_ed25519_public_key_v1(spki_bytes)


def _decode_signature(value: Any) -> bytes:
    if type(value) is not str or not value:
        raise ValueError("signature_base64 must be non-empty")
    signature = decode_canonical_base64_v1(value, "signature_base64")
    if len(signature) != 64:
        raise ValueError("Ed25519 signature must be exactly 64 bytes")
    return signature


def _validate_upstreams(
    plan_document: Any,
    provider_preregistration_document: Any,
    signed_receipt_evidence_document: Any,
    *,
    observer_registrations: Any,
    provider_preregistration_kwargs: Any,
    signed_receipt_verify_args: Any,
    signed_receipt_verify_kwargs: Any,
    expected_signed_receipt_evidence_hash: Any,
) -> None:
    evidence_hash = _require_hash(
        "expected_signed_receipt_evidence_hash",
        expected_signed_receipt_evidence_hash,
    )
    if (
        type(plan_document) is not dict
        or type(provider_preregistration_document) is not dict
        or type(signed_receipt_evidence_document) is not dict
        or type(observer_registrations) is not list
        or type(provider_preregistration_kwargs) is not dict
        or type(signed_receipt_verify_args) is not tuple
        or type(signed_receipt_verify_kwargs) is not dict
        or "expected_verification_evidence_hash"
        in signed_receipt_verify_kwargs
    ):
        raise ValueError("conformance upstream context has an inexact type")
    if not conformance_plan.verify_replay_cursor_provider_conformance_plan_v1(
        plan_document,
        provider_preregistration_document,
        observer_registrations=observer_registrations,
        **dict(provider_preregistration_kwargs),
    ):
        raise ValueError("conformance plan is not exact")
    if not signed_receipt.verify_signed_replay_cursor_provider_receipt_evidence_v1(
        signed_receipt_evidence_document,
        *signed_receipt_verify_args,
        expected_verification_evidence_hash=evidence_hash,
        **dict(signed_receipt_verify_kwargs),
    ):
        raise ValueError("signed provider receipt evidence is not exact")
    facts = signed_receipt_evidence_document.get("facts", {})
    if (
        signed_receipt_evidence_document.get("status") != "PASS"
        or signed_receipt_evidence_document.get("admission_status")
        != "BLOCKED"
        or facts.get("provider_registered") is not False
        or facts.get("actual_provider_invocation_verified") is not False
        or facts.get("durable_commit_verified") is not False
        or facts.get("linearizable_read_after_write_verified") is not False
    ):
        raise ValueError("signed receipt upstream status drifted")


def _normalize_case_rows(case_rows: Any) -> list[dict[str, str]]:
    if type(case_rows) is not list or len(case_rows) != len(
        conformance_plan.EXPECTED_CASE_IDS
    ):
        raise ValueError("observer report must include every preregistered case")
    normalized: list[dict[str, str]] = []
    for expected_case_id, row in zip(
        conformance_plan.EXPECTED_CASE_IDS, case_rows, strict=True
    ):
        if type(row) is not dict or frozenset(row) != _CASE_KEYS:
            raise ValueError("observer case row shape is not exact")
        if row["case_id"] != expected_case_id:
            raise ValueError("observer case order or identity drifted")
        if row["status"] not in ("PASS", "FAIL"):
            raise ValueError("observer case status must be PASS or FAIL")
        normalized.append(
            {
                "case_id": expected_case_id,
                "status": row["status"],
                "evidence_hash": _require_hash(
                    "evidence_hash", row["evidence_hash"]
                ),
            }
        )
    return normalized


def build_replay_cursor_provider_conformance_observer_report_v1(
    plan_document: Any,
    provider_preregistration_document: Any,
    signed_receipt_evidence_document: Any,
    *,
    observer_id: Any,
    run_context_hash: Any,
    case_rows: Any,
    observer_registrations: Any,
    provider_preregistration_kwargs: Any,
    signed_receipt_verify_args: Any,
    signed_receipt_verify_kwargs: Any,
    expected_signed_receipt_evidence_hash: Any,
) -> dict[str, Any]:
    _validate_upstreams(
        plan_document,
        provider_preregistration_document,
        signed_receipt_evidence_document,
        observer_registrations=observer_registrations,
        provider_preregistration_kwargs=provider_preregistration_kwargs,
        signed_receipt_verify_args=signed_receipt_verify_args,
        signed_receipt_verify_kwargs=signed_receipt_verify_kwargs,
        expected_signed_receipt_evidence_hash=(
            expected_signed_receipt_evidence_hash
        ),
    )
    observer = _require_identifier("observer_id", observer_id)
    context_hash = _require_hash("run_context_hash", run_context_hash)
    registrations = {
        row["observer_id"]: row for row in plan_document["observers"]
    }
    if observer not in registrations:
        raise ValueError("observer is not preregistered")
    cases = _normalize_case_rows(case_rows)
    all_passed = all(row["status"] == "PASS" for row in cases)
    body = {
        "schema_version": OBSERVER_REPORT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "CLAIMED_PASS" if all_passed else "CLAIMED_FAIL",
        "observer": deepcopy(registrations[observer]),
        "source": {
            "conformance_plan_hash": plan_document[
                "conformance_plan_hash"
            ],
            "provider_preregistration_hash": (
                provider_preregistration_document["preregistration_hash"]
            ),
            "signed_receipt_evidence_hash": (
                expected_signed_receipt_evidence_hash
            ),
            "run_context_hash": context_hash,
        },
        "cases": cases,
        "summary": {
            "required_case_count": len(cases),
            "claimed_passed_case_count": sum(
                row["status"] == "PASS" for row in cases
            ),
            "all_required_cases_claimed_passed": all_passed,
        },
        "facts": {
            "report_structure_complete": True,
            "observer_signature_verified": False,
            "observer_identity_verified": False,
            "observer_independence_verified": False,
            "test_execution_source_truth_verified": False,
            "provider_conformance_verified": False,
            "provider_called_by_builder": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "authority": {
            "descriptive_only": True,
            "observer_report_trust_allowed": False,
            "provider_conformance_trust_allowed": False,
            "current_admission_allowed": False,
            "runtime_gate_activation_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
            "trading_allowed": False,
        },
    }
    return seal_strict_canonical_document(body, "observer_report_hash")


def verify_replay_cursor_provider_conformance_observer_report_v1(
    report_document: Any,
    plan_document: Any,
    provider_preregistration_document: Any,
    signed_receipt_evidence_document: Any,
    **build_kwargs: Any,
) -> bool:
    if type(report_document) is not dict:
        return False
    try:
        expected = build_replay_cursor_provider_conformance_observer_report_v1(
            plan_document,
            provider_preregistration_document,
            signed_receipt_evidence_document,
            observer_id=report_document["observer"]["observer_id"],
            run_context_hash=report_document["source"]["run_context_hash"],
            case_rows=report_document["cases"],
            **build_kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return strict_json_contract_equal(report_document, expected)


def build_replay_cursor_provider_conformance_observer_signature_message_hash_v1(
    report_document: Any,
    plan_document: Any,
    signed_receipt_evidence_document: Any,
) -> str:
    if (
        type(report_document) is not dict
        or type(plan_document) is not dict
        or type(signed_receipt_evidence_document) is not dict
        or not _is_hash(report_document.get("observer_report_hash"))
        or not _is_hash(plan_document.get("conformance_plan_hash"))
        or not _is_hash(
            signed_receipt_evidence_document.get(
                "verification_evidence_hash"
            )
        )
    ):
        raise ValueError("observer signature message inputs are invalid")
    return strict_canonical_hash(
        {
            "signature_domain": SIGNATURE_DOMAIN,
            "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
            "observer_id": report_document["observer"]["observer_id"],
            "observer_report_hash": report_document["observer_report_hash"],
            "conformance_plan_hash": plan_document["conformance_plan_hash"],
            "signed_receipt_evidence_hash": (
                signed_receipt_evidence_document[
                    "verification_evidence_hash"
                ]
            ),
            "run_context_hash": report_document["source"][
                "run_context_hash"
            ],
        }
    )


def build_signed_replay_cursor_provider_conformance_observer_report_v1(
    report_document: Any,
    plan_document: Any,
    provider_preregistration_document: Any,
    signed_receipt_evidence_document: Any,
    *,
    public_key_spki_base64: Any,
    signature_base64: Any,
    report_verify_kwargs: Any,
) -> dict[str, Any]:
    if type(report_verify_kwargs) is not dict:
        raise ValueError("report_verify_kwargs must be an exact dict")
    if not verify_replay_cursor_provider_conformance_observer_report_v1(
        report_document,
        plan_document,
        provider_preregistration_document,
        signed_receipt_evidence_document,
        **dict(report_verify_kwargs),
    ):
        raise ValueError("observer report is not exact")
    spki_bytes, _ = _decode_public_key(public_key_spki_base64)
    _decode_signature(signature_base64)
    message_hash = (
        build_replay_cursor_provider_conformance_observer_signature_message_hash_v1(
            report_document,
            plan_document,
            signed_receipt_evidence_document,
        )
    )
    body = {
        "schema_version": SIGNED_OBSERVER_REPORT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "SIGNED_REPORT_CANDIDATE",
        "observer_id": report_document["observer"]["observer_id"],
        "observer_report": deepcopy(report_document),
        "observer_report_hash": report_document["observer_report_hash"],
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signature_domain": SIGNATURE_DOMAIN,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "signature_message_hash": message_hash,
        "public_key_spki_base64": public_key_spki_base64,
        "public_key_spki_sha256": sha256(spki_bytes).hexdigest(),
        "signature_base64": signature_base64,
        "authority": {
            "observer_report_trust_allowed": False,
            "provider_conformance_trust_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
            "trading_allowed": False,
        },
    }
    return seal_strict_canonical_document(
        body, "signed_observer_report_hash"
    )


def evaluate_replay_cursor_provider_conformance_observer_quorum_v1(
    signed_report_documents: Any,
    plan_document: Any,
    provider_preregistration_document: Any,
    signed_receipt_evidence_document: Any,
    *,
    observer_registrations: Any,
    provider_preregistration_kwargs: Any,
    signed_receipt_verify_args: Any,
    signed_receipt_verify_kwargs: Any,
    expected_signed_receipt_evidence_hash: Any,
) -> dict[str, Any]:
    upstream_exact = True
    try:
        _validate_upstreams(
            plan_document,
            provider_preregistration_document,
            signed_receipt_evidence_document,
            observer_registrations=observer_registrations,
            provider_preregistration_kwargs=provider_preregistration_kwargs,
            signed_receipt_verify_args=signed_receipt_verify_args,
            signed_receipt_verify_kwargs=signed_receipt_verify_kwargs,
            expected_signed_receipt_evidence_hash=(
                expected_signed_receipt_evidence_hash
            ),
        )
    except (KeyError, TypeError, ValueError):
        upstream_exact = False

    registrations = (
        {row["observer_id"]: row for row in plan_document.get("observers", [])}
        if isinstance(plan_document, Mapping)
        else {}
    )
    rows = signed_report_documents if type(signed_report_documents) is list else []
    observer_results: list[dict[str, Any]] = []
    seen_ids: list[str] = []
    for signed_document in rows:
        observer_id = (
            signed_document.get("observer_id")
            if isinstance(signed_document, Mapping)
            else None
        )
        report_exact = False
        signed_document_exact = False
        key_hash_matches = False
        signature_verified = False
        all_cases_claimed_passed = False
        signed_report_hash = None
        try:
            if not upstream_exact or type(signed_document) is not dict:
                raise ValueError("signed observer upstream is not exact")
            report = signed_document["observer_report"]
            report_verify_kwargs = {
                "observer_registrations": observer_registrations,
                "provider_preregistration_kwargs": (
                    provider_preregistration_kwargs
                ),
                "signed_receipt_verify_args": signed_receipt_verify_args,
                "signed_receipt_verify_kwargs": (
                    signed_receipt_verify_kwargs
                ),
                "expected_signed_receipt_evidence_hash": (
                    expected_signed_receipt_evidence_hash
                ),
            }
            report_exact = (
                verify_replay_cursor_provider_conformance_observer_report_v1(
                    report,
                    plan_document,
                    provider_preregistration_document,
                    signed_receipt_evidence_document,
                    **report_verify_kwargs,
                )
            )
            expected_signed = (
                build_signed_replay_cursor_provider_conformance_observer_report_v1(
                    report,
                    plan_document,
                    provider_preregistration_document,
                    signed_receipt_evidence_document,
                    public_key_spki_base64=signed_document[
                        "public_key_spki_base64"
                    ],
                    signature_base64=signed_document["signature_base64"],
                    report_verify_kwargs=report_verify_kwargs,
                )
            )
            signed_report_hash = expected_signed[
                "signed_observer_report_hash"
            ]
            signed_document_exact = strict_json_contract_equal(
                signed_document, expected_signed
            )
            spki_bytes, public_key = _decode_public_key(
                signed_document["public_key_spki_base64"]
            )
            signature = _decode_signature(
                signed_document["signature_base64"]
            )
            registration = registrations[observer_id]
            key_hash_matches = (
                sha256(spki_bytes).hexdigest()
                == registration["public_key_spki_sha256"]
            )
            try:
                public_key.verify(
                    signature,
                    bytes.fromhex(expected_signed["signature_message_hash"]),
                )
                signature_verified = True
            except (InvalidSignature, ValueError):
                signature_verified = False
            all_cases_claimed_passed = (
                report.get("summary", {}).get(
                    "all_required_cases_claimed_passed"
                )
                is True
            )
        except (KeyError, TypeError, ValueError):
            pass
        row_pass = all(
            (
                upstream_exact,
                report_exact,
                signed_document_exact,
                key_hash_matches,
                signature_verified,
                all_cases_claimed_passed,
            )
        )
        if type(observer_id) is str:
            seen_ids.append(observer_id)
        observer_results.append(
            {
                "observer_id": observer_id,
                "signed_observer_report_hash": signed_report_hash,
                "report_exact": report_exact,
                "signed_document_exact": signed_document_exact,
                "key_hash_matches_preregistration": key_hash_matches,
                "signature_verified": signature_verified,
                "all_cases_claimed_passed": all_cases_claimed_passed,
                "status": "PASS" if row_pass else "BLOCK",
            }
        )
    observer_results.sort(
        key=lambda row: (
            str(row["observer_id"]),
            str(row["signed_observer_report_hash"]),
        )
    )
    duplicate_observer_ids = len(seen_ids) != len(set(seen_ids))
    passing_ids = sorted(
        {
            row["observer_id"]
            for row in observer_results
            if row["status"] == "PASS" and type(row["observer_id"]) is str
        }
    )
    row_count_valid = len(rows) in (2, 3)
    local_quorum_verified = (
        upstream_exact
        and row_count_valid
        and not duplicate_observer_ids
        and len(passing_ids) >= 2
    )
    dynamic_blockers: list[str] = []
    if not upstream_exact:
        dynamic_blockers.append("UPSTREAM_PLAN_OR_SIGNED_RECEIPT_NOT_EXACT")
    if not row_count_valid:
        dynamic_blockers.append("OBSERVER_REPORT_COUNT_NOT_TWO_OR_THREE")
    if duplicate_observer_ids:
        dynamic_blockers.append("DUPLICATE_OBSERVER_ID")
    if len(passing_ids) < 2:
        dynamic_blockers.append("OBSERVER_SIGNATURE_QUORUM_NOT_MET")
    body = {
        "schema_version": QUORUM_EVIDENCE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if local_quorum_verified else "BLOCK",
        "admission_status": "BLOCKED",
        "conformance_status": (
            "SIGNED_OBSERVER_CLAIM_QUORUM_LOCAL_ONLY"
            if local_quorum_verified
            else "UNKNOWN"
        ),
        "decision": (
            "LOCAL_OBSERVER_SIGNATURE_QUORUM_VERIFIED_EXTERNAL_EXECUTION_"
            "AND_PROVIDER_CONFORMANCE_BLOCKED"
            if local_quorum_verified
            else "OBSERVER_QUORUM_UNKNOWN_OR_INVALID"
        ),
        "blockers": dynamic_blockers + list(_PERMANENT_BLOCKERS),
        "observer_results": observer_results,
        "quorum_summary": {
            "provided_report_count": len(rows),
            "required_signature_quorum": 2,
            "passing_observer_ids": passing_ids,
            "duplicate_observer_ids": duplicate_observer_ids,
            "local_signature_quorum_verified": local_quorum_verified,
        },
        "facts": {
            "upstream_signed_receipt_evidence_exact": upstream_exact,
            "signed_observer_report_quorum_verified": (
                local_quorum_verified
            ),
            "all_required_case_results_claimed_by_quorum": (
                local_quorum_verified
            ),
            "observer_identities_verified": False,
            "observer_key_control_continuity_verified": False,
            "observer_independence_source_truth_verified": False,
            "observer_test_execution_source_truth_verified": False,
            "provider_endpoint_verified": False,
            "provider_implementation_verified": False,
            "external_provider_conformance_verified": False,
            "atomic_compare_and_advance_verified": False,
            "durable_commit_verified": False,
            "linearizable_read_after_write_verified": False,
            "rollback_resistance_verified": False,
            "restart_recovery_verified": False,
            "provider_called_by_evaluator": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
            "runtime_mutations_performed": False,
            "execution_verified": False,
            "profitability_proven": False,
        },
        "source": {
            "conformance_plan_hash": (
                plan_document.get("conformance_plan_hash")
                if isinstance(plan_document, Mapping)
                else None
            ),
            "provider_preregistration_hash": (
                provider_preregistration_document.get(
                    "preregistration_hash"
                )
                if isinstance(provider_preregistration_document, Mapping)
                else None
            ),
            "signed_receipt_evidence_hash": (
                expected_signed_receipt_evidence_hash
                if _is_hash(expected_signed_receipt_evidence_hash)
                else None
            ),
        },
        "authority": {
            "descriptive_only": True,
            "observer_report_trust_allowed": False,
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
            "raw_observer_public_keys_redacted": True,
            "raw_observer_signatures_redacted": True,
            "raw_case_evidence_redacted": True,
            "raw_provider_receipt_redacted": True,
            "raw_runtime_state_embedded": False,
        },
        "limitations": [
            "A local quorum verifies only signatures over structurally exact observer claims.",
            "It does not verify observer identity, independence, test execution, provider endpoint, implementation, conformance, atomicity, durability, linearizability, rollback resistance, or restart recovery.",
            "No current, runtime, writer, paper, live, execution, profitability, or trading authority is granted.",
        ],
    }
    return seal_strict_canonical_document(body, "quorum_evidence_hash")


def verify_replay_cursor_provider_conformance_observer_quorum_v1(
    evidence_document: Any,
    signed_report_documents: Any,
    plan_document: Any,
    provider_preregistration_document: Any,
    signed_receipt_evidence_document: Any,
    *,
    expected_quorum_evidence_hash: Any,
    **evaluation_kwargs: Any,
) -> bool:
    if not _is_hash(expected_quorum_evidence_hash):
        return False
    expected = evaluate_replay_cursor_provider_conformance_observer_quorum_v1(
        signed_report_documents,
        plan_document,
        provider_preregistration_document,
        signed_receipt_evidence_document,
        **evaluation_kwargs,
    )
    return (
        expected["quorum_evidence_hash"]
        == expected_quorum_evidence_hash
        and strict_json_contract_equal(evidence_document, expected)
    )


__all__ = [
    "OBSERVER_REPORT_SCHEMA_VERSION",
    "QUORUM_EVIDENCE_SCHEMA_VERSION",
    "SIGNATURE_ALGORITHM",
    "SIGNATURE_DOMAIN",
    "SIGNATURE_MESSAGE_FORMAT",
    "SIGNED_OBSERVER_REPORT_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_replay_cursor_provider_conformance_observer_report_v1",
    "build_replay_cursor_provider_conformance_observer_signature_message_hash_v1",
    "build_signed_replay_cursor_provider_conformance_observer_report_v1",
    "evaluate_replay_cursor_provider_conformance_observer_quorum_v1",
    "verify_replay_cursor_provider_conformance_observer_quorum_v1",
    "verify_replay_cursor_provider_conformance_observer_report_v1",
]
