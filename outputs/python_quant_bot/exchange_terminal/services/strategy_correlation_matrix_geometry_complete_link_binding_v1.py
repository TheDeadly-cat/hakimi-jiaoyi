"""Unmounted binding from exact matrix geometry evidence to complete-link consumers.

This module is deliberately research-only and side-effect free.  It does not
mount a route, register a writer, or grant admission.  Its only positive result
means that the exact geometry artifact and the existing complete-link consumer
documents were reproduced and verified for the same synthetic input snapshot.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from hmac import compare_digest
import json
from typing import Any

from exchange_terminal.services import strategy_correlation_cluster_complete_link as _complete_link
from exchange_terminal.services import strategy_correlation_cluster_gate as _cluster_contract
from exchange_terminal.services import strategy_correlation_matrix_geometry_gate_v1 as _geometry


SCHEMA_VERSION = "strategy-correlation-matrix-geometry-complete-link-binding-contract-v1"
PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-complete-link-binding-preregistration-v1"
)
EVALUATION_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-complete-link-binding-evaluation-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-matrix-geometry-complete-link-binding-v1-unmounted-lock-3"
)

GEOMETRY_PROVIDER_MODULE = (
    "exchange_terminal.services.strategy_correlation_matrix_geometry_gate_v1"
)
GEOMETRY_PROVIDER_SOURCE_SHA256 = (
    "f2f4ac9b9989e925440ce4fd4a46174f3ea3d5d96e1fe9fe81d9808b29829e30"
)
COMPLETE_LINK_CONSUMER_MODULE = (
    "exchange_terminal.services.strategy_correlation_cluster_complete_link"
)
COMPLETE_LINK_CONSUMER_SOURCE_SHA256 = (
    "a44851d07ce6757f11763f8f76f5036129ab0a718094a9cb1b46886781885be8"
)
CLUSTER_CONTRACT_MODULE = (
    "exchange_terminal.services.strategy_correlation_cluster_gate"
)
CLUSTER_CONTRACT_SOURCE_SHA256 = (
    "90cfa45aa05b3fd3d915221ece7e7c5ef4634a334ac3099080f60133b56b62b3"
)

ACTIVATION_SEQUENCE = (
    "VERIFY_EXACT_MATRIX_CONTRACT",
    "VERIFY_EXACT_GEOMETRY_PREREGISTRATION",
    "VERIFY_EXACT_GEOMETRY_GATE_FOR_SAME_MATRIX",
    "EVALUATE_COMPLETE_LINK_GATE_V2_WITH_OWNED_AUDIT",
    "VERIFY_EMBEDDED_COMPLETE_LINK_AUDIT",
    "VERIFY_COMPLETE_LINK_GATE_V2",
)
RESEARCH_ONLY_LANES = ("RAW_EXCESS", "research")

# Capture the reviewed consumer implementation before any call-site replacement.
# The public module attribute remains the candidate invocation seam; this pinned
# callable is used only for an independent, exact reconstruction of its output.
_PINNED_COMPLETE_LINK_GATE_EVALUATOR = (
    _complete_link.evaluate_correlation_cluster_gate_v2
)


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return sha256(payload).hexdigest()


def _canonical_external_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def _is_exact_hash(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _safe_hash(document: Any, field: str) -> str | None:
    if not isinstance(document, dict):
        return None
    value = document.get(field)
    return value if _is_exact_hash(value) else None


def _external_self_hash_is_exact(document: Any, field: str) -> bool:
    stored_hash = _safe_hash(document, field)
    if stored_hash is None:
        return False
    unsigned = deepcopy(document)
    unsigned.pop(field, None)
    return compare_digest(_canonical_external_hash(unsigned), stored_hash)


def _permissions() -> dict[str, bool]:
    return {
        "research_evidence_only": True,
        "current_admission": False,
        "writer_activation": False,
        "paper": False,
        "live": False,
    }


_CONTRACT_MANIFEST = {
    "schema_version": SCHEMA_VERSION,
    "static_fingerprint": STATIC_FINGERPRINT,
    "activation_sequence": list(ACTIVATION_SEQUENCE),
    "geometry": {
        "module": GEOMETRY_PROVIDER_MODULE,
        "source_sha256": GEOMETRY_PROVIDER_SOURCE_SHA256,
        "gate_contract_hash": _geometry.GATE_CONTRACT_HASH,
        "preregistration_schema_version": _geometry.PREREGISTRATION_SCHEMA_VERSION,
        "gate_schema_version": _geometry.GATE_SCHEMA_VERSION,
        "verifier": "verify_strategy_correlation_matrix_geometry_gate_v1",
    },
    "consumer": {
        "module": COMPLETE_LINK_CONSUMER_MODULE,
        "source_sha256": COMPLETE_LINK_CONSUMER_SOURCE_SHA256,
        "audit_schema_version": _complete_link.AUDIT_SCHEMA_VERSION,
        "gate_schema_version": _complete_link.GATE_SCHEMA_VERSION,
        "evaluator": "evaluate_correlation_cluster_gate_v2",
        "exact_rebuilder": (
            "evaluate_correlation_cluster_gate_v2@binding_module_import"
        ),
        "audit_verifier": "verify_correlation_cluster_complete_link_audit",
        "gate_verifier": "verify_correlation_cluster_gate_v2",
        "audit_ownership": "COMPLETE_LINK_GATE_V2_OWNS_SINGLE_AUDIT_BUILD",
        "research_only_lanes": list(RESEARCH_ONLY_LANES),
    },
    "cluster_contract": {
        "module": CLUSTER_CONTRACT_MODULE,
        "source_sha256": CLUSTER_CONTRACT_SOURCE_SHA256,
        "preregistration_schema_version": _cluster_contract.PREREGISTRATION_SCHEMA_VERSION,
        "matrix_schema_version": _cluster_contract.CORRELATION_MATRIX_SCHEMA_VERSION,
    },
    "authority": {
        "mounted": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "paper_allowed": False,
        "live_allowed": False,
    },
}
BINDING_CONTRACT_HASH = _canonical_hash(_CONTRACT_MANIFEST)


def _verification_passed(document: Any) -> bool:
    return isinstance(document, dict) and document.get("status") == "PASS"


def _cluster_preregistration_is_exact(
    document: Any,
    *,
    expected_preregistration_hash: Any,
) -> bool:
    if not _is_exact_hash(expected_preregistration_hash):
        return False
    if _safe_hash(document, "preregistration_hash") != expected_preregistration_hash:
        return False
    try:
        verification = _cluster_contract.verify_correlation_cluster_preregistration(document)
    except Exception:
        return False
    return _verification_passed(verification)


def _geometry_preregistration_metadata_is_bound(
    document: Any,
    *,
    expected_preregistration_hash: Any,
) -> bool:
    return bool(
        isinstance(document, dict)
        and _is_exact_hash(expected_preregistration_hash)
        and _safe_hash(document, "preregistration_hash") == expected_preregistration_hash
        and document.get("schema_version") == _geometry.PREREGISTRATION_SCHEMA_VERSION
        and document.get("status") == "PREREGISTERED_UNMOUNTED"
        and document.get("static_fingerprint") == _geometry.STATIC_FINGERPRINT
        and document.get("gate_contract_hash") == _geometry.GATE_CONTRACT_HASH
    )


def build_strategy_correlation_matrix_geometry_complete_link_binding_preregistration_v1(
    geometry_preregistration: Any,
    cluster_preregistration: Any,
    *,
    expected_geometry_preregistration_hash: Any,
    expected_cluster_preregistration_hash: Any,
) -> dict[str, Any] | None:
    """Bind exact producer and consumer preregistration identities without mounting."""

    if not _geometry_preregistration_metadata_is_bound(
        geometry_preregistration,
        expected_preregistration_hash=expected_geometry_preregistration_hash,
    ):
        return None
    if not _cluster_preregistration_is_exact(
        cluster_preregistration,
        expected_preregistration_hash=expected_cluster_preregistration_hash,
    ):
        return None

    document: dict[str, Any] = {
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "status": "PREREGISTERED_UNMOUNTED",
        "static_fingerprint": STATIC_FINGERPRINT,
        "binding_contract_hash": BINDING_CONTRACT_HASH,
        "geometry_preregistration_hash": expected_geometry_preregistration_hash,
        "geometry_gate_contract_hash": _geometry.GATE_CONTRACT_HASH,
        "cluster_preregistration_hash": expected_cluster_preregistration_hash,
        "activation_sequence": list(ACTIVATION_SEQUENCE),
        "consumer_audit_ownership": "COMPLETE_LINK_GATE_V2_OWNS_SINGLE_AUDIT_BUILD",
        "source_bindings": {
            "geometry_provider": {
                "module": GEOMETRY_PROVIDER_MODULE,
                "source_sha256": GEOMETRY_PROVIDER_SOURCE_SHA256,
            },
            "complete_link_consumer": {
                "module": COMPLETE_LINK_CONSUMER_MODULE,
                "source_sha256": COMPLETE_LINK_CONSUMER_SOURCE_SHA256,
            },
            "cluster_contract": {
                "module": CLUSTER_CONTRACT_MODULE,
                "source_sha256": CLUSTER_CONTRACT_SOURCE_SHA256,
            },
        },
        "mounted": False,
        "synthetic_only": True,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": _permissions(),
    }
    document["preregistration_hash"] = _canonical_hash(document)
    return document


def verify_strategy_correlation_matrix_geometry_complete_link_binding_preregistration_v1(
    document: Any,
    geometry_preregistration: Any,
    cluster_preregistration: Any,
    *,
    expected_binding_preregistration_hash: Any,
    expected_geometry_preregistration_hash: Any,
    expected_cluster_preregistration_hash: Any,
) -> bool:
    """Rebuild and compare the full preregistration; never trust its own hash alone."""

    if not _is_exact_hash(expected_binding_preregistration_hash):
        return False
    try:
        expected = (
            build_strategy_correlation_matrix_geometry_complete_link_binding_preregistration_v1(
                geometry_preregistration,
                cluster_preregistration,
                expected_geometry_preregistration_hash=(
                    expected_geometry_preregistration_hash
                ),
                expected_cluster_preregistration_hash=expected_cluster_preregistration_hash,
            )
        )
    except Exception:
        return False
    return bool(
        isinstance(document, dict)
        and expected is not None
        and _safe_hash(document, "preregistration_hash")
        == expected_binding_preregistration_hash
        and compare_digest(
            expected["preregistration_hash"],
            expected_binding_preregistration_hash,
        )
        and document == expected
    )


def _matrix_symbols(correlation_matrix: Any) -> list[str] | None:
    if not isinstance(correlation_matrix, dict):
        return None
    symbols = correlation_matrix.get("symbols")
    if not isinstance(symbols, list) or not symbols or len(symbols) > _geometry.MAXIMUM_DIMENSION:
        return None
    if any(
        not isinstance(symbol, str)
        or not symbol
        or symbol.strip() != symbol
        for symbol in symbols
    ):
        return None
    if len(set(symbols)) != len(symbols):
        return None
    return list(symbols)


def _identity_is_valid(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and value.strip() == value


def _evaluation_document(
    *,
    status: str,
    reason_code: str,
    binding_preregistration: Any,
    geometry_preregistration: Any,
    geometry_gate_document: Any,
    cluster_preregistration: Any,
    correlation_matrix: Any,
    trace: list[str],
    consumer_invocation_attempted: bool = False,
    audit_verified: bool = False,
    gate_verified: bool = False,
    trusted_audit: dict[str, Any] | None = None,
    trusted_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "status": status,
        "reason_code": reason_code,
        "static_fingerprint": STATIC_FINGERPRINT,
        "binding_contract_hash": BINDING_CONTRACT_HASH,
        "binding_preregistration_hash": _safe_hash(
            binding_preregistration, "preregistration_hash"
        ),
        "geometry_preregistration_hash": _safe_hash(
            geometry_preregistration, "preregistration_hash"
        ),
        "geometry_gate_hash": _safe_hash(geometry_gate_document, "gate_hash"),
        "cluster_preregistration_hash": _safe_hash(
            cluster_preregistration, "preregistration_hash"
        ),
        "matrix_hash": _safe_hash(correlation_matrix, "matrix_hash"),
        "activation_sequence": list(ACTIVATION_SEQUENCE),
        "trace": list(trace),
        "consumer_invocation_attempted": consumer_invocation_attempted,
        "embedded_complete_link_audit_verified": audit_verified,
        "complete_link_gate_verified": gate_verified,
        "complete_link_audit_status": (
            trusted_audit.get("status") if trusted_audit is not None else None
        ),
        "complete_link_gate_status": (
            trusted_gate.get("status") if trusted_gate is not None else None
        ),
        "complete_link_audit": deepcopy(trusted_audit),
        "complete_link_gate": deepcopy(trusted_gate),
        "mounted": False,
        "synthetic_only": True,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": _permissions(),
    }
    document["evaluation_hash"] = _canonical_hash(document)
    return document


def evaluate_strategy_correlation_matrix_geometry_complete_link_binding_v1(
    binding_preregistration: Any,
    geometry_preregistration: Any,
    geometry_gate_document: Any,
    cluster_preregistration: Any,
    correlation_matrix: Any,
    selection_cells: Any,
    *,
    expected_binding_preregistration_hash: Any,
    expected_geometry_preregistration_hash: Any,
    expected_cluster_preregistration_hash: Any,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
) -> dict[str, Any]:
    """Verify geometry first, then run the existing complete-link gate consumer."""

    trace: list[str] = []
    common = {
        "binding_preregistration": binding_preregistration,
        "geometry_preregistration": geometry_preregistration,
        "geometry_gate_document": geometry_gate_document,
        "cluster_preregistration": cluster_preregistration,
        "correlation_matrix": correlation_matrix,
        "trace": trace,
    }

    if not verify_strategy_correlation_matrix_geometry_complete_link_binding_preregistration_v1(
        binding_preregistration,
        geometry_preregistration,
        cluster_preregistration,
        expected_binding_preregistration_hash=expected_binding_preregistration_hash,
        expected_geometry_preregistration_hash=expected_geometry_preregistration_hash,
        expected_cluster_preregistration_hash=expected_cluster_preregistration_hash,
    ):
        return _evaluation_document(
            status="UNKNOWN",
            reason_code="BINDING_PREREGISTRATION_INVALID",
            **common,
        )

    symbols = _matrix_symbols(correlation_matrix)
    if symbols is None:
        return _evaluation_document(
            status="UNKNOWN",
            reason_code="CORRELATION_MATRIX_SYMBOLS_INVALID",
            **common,
        )
    try:
        matrix_verification = _cluster_contract.verify_correlation_matrix_contract(
            correlation_matrix,
            expected_symbols=symbols,
        )
    except Exception:
        matrix_verification = None
    if not _verification_passed(matrix_verification):
        return _evaluation_document(
            status="UNKNOWN",
            reason_code="CORRELATION_MATRIX_CONTRACT_INVALID",
            **common,
        )
    trace.append("EXACT_MATRIX_CONTRACT_VERIFIED")

    try:
        geometry_preregistration_valid = (
            _geometry.verify_strategy_correlation_matrix_geometry_preregistration_v1(
                geometry_preregistration,
                expected_symbols=symbols,
                expected_preregistration_hash=expected_geometry_preregistration_hash,
            )
        )
    except Exception:
        geometry_preregistration_valid = False
    if not geometry_preregistration_valid:
        return _evaluation_document(
            status="UNKNOWN",
            reason_code="GEOMETRY_PREREGISTRATION_INVALID_FOR_MATRIX",
            **common,
        )
    trace.append("EXACT_GEOMETRY_PREREGISTRATION_VERIFIED")

    if geometry_gate_document is None:
        return _evaluation_document(
            status="UNKNOWN",
            reason_code="GEOMETRY_GATE_EVIDENCE_MISSING",
            **common,
        )
    try:
        geometry_gate_valid = (
            _geometry.verify_strategy_correlation_matrix_geometry_gate_v1(
                geometry_gate_document,
                geometry_preregistration,
                correlation_matrix,
                expected_preregistration_hash=expected_geometry_preregistration_hash,
            )
        )
    except Exception:
        geometry_gate_valid = False
    if not geometry_gate_valid:
        return _evaluation_document(
            status="UNKNOWN",
            reason_code="GEOMETRY_GATE_EVIDENCE_INVALID_FOR_MATRIX",
            **common,
        )
    trace.append("EXACT_GEOMETRY_GATE_VERIFIED")

    if geometry_gate_document.get("status") != "PASS":
        return _evaluation_document(
            status=(
                "BLOCK" if geometry_gate_document.get("status") == "BLOCK" else "UNKNOWN"
            ),
            reason_code="GEOMETRY_GATE_DID_NOT_PASS",
            **common,
        )
    trace.append("GEOMETRY_GATE_PASS_CONFIRMED")

    if not _identity_is_valid(strategy_id) or not _identity_is_valid(variant_id):
        return _evaluation_document(
            status="UNKNOWN",
            reason_code="CONSUMER_IDENTITY_INVALID",
            **common,
        )
    if lane not in RESEARCH_ONLY_LANES:
        return _evaluation_document(
            status="BLOCK",
            reason_code="NON_RESEARCH_LANE_REJECTED",
            **common,
        )

    trace.append("COMPLETE_LINK_GATE_V2_INVOCATION_ATTEMPTED")
    try:
        gate_document = _complete_link.evaluate_correlation_cluster_gate_v2(
            cluster_preregistration,
            correlation_matrix,
            selection_cells,
            strategy_id=strategy_id,
            variant_id=variant_id,
            lane=lane,
        )
    except Exception:
        return _evaluation_document(
            status="UNKNOWN",
            reason_code="COMPLETE_LINK_CONSUMER_EXCEPTION",
            consumer_invocation_attempted=True,
            **common,
        )
    if not isinstance(gate_document, dict):
        return _evaluation_document(
            status="UNKNOWN",
            reason_code="COMPLETE_LINK_GATE_DOCUMENT_INVALID",
            consumer_invocation_attempted=True,
            **common,
        )

    audit_document = gate_document.get("complete_link_audit")
    try:
        expected_gate_document = _PINNED_COMPLETE_LINK_GATE_EVALUATOR(
            cluster_preregistration,
            correlation_matrix,
            selection_cells,
            strategy_id=strategy_id,
            variant_id=variant_id,
            lane=lane,
        )
    except Exception:
        return _evaluation_document(
            status="UNKNOWN",
            reason_code="COMPLETE_LINK_EXACT_REBUILD_EXCEPTION",
            consumer_invocation_attempted=True,
            **common,
        )
    expected_audit_document = (
        expected_gate_document.get("complete_link_audit")
        if isinstance(expected_gate_document, dict)
        else None
    )
    if (
        not _external_self_hash_is_exact(audit_document, "audit_hash")
        or audit_document != expected_audit_document
    ):
        return _evaluation_document(
            status="UNKNOWN",
            reason_code="EMBEDDED_COMPLETE_LINK_AUDIT_INVALID",
            consumer_invocation_attempted=True,
            **common,
        )
    try:
        audit_verification = _complete_link.verify_correlation_cluster_complete_link_audit(
            audit_document,
            preregistration=cluster_preregistration,
            correlation_matrix=correlation_matrix,
        )
    except Exception:
        audit_verification = None
    if not _verification_passed(audit_verification):
        return _evaluation_document(
            status="UNKNOWN",
            reason_code="EMBEDDED_COMPLETE_LINK_AUDIT_INVALID",
            consumer_invocation_attempted=True,
            **common,
        )
    trace.append("EMBEDDED_COMPLETE_LINK_AUDIT_VERIFIED")

    if (
        not _external_self_hash_is_exact(gate_document, "gate_hash")
        or gate_document != expected_gate_document
    ):
        return _evaluation_document(
            status="UNKNOWN",
            reason_code="COMPLETE_LINK_GATE_DOCUMENT_INVALID",
            consumer_invocation_attempted=True,
            audit_verified=True,
            trusted_audit=audit_document,
            **common,
        )

    try:
        gate_verification = _complete_link.verify_correlation_cluster_gate_v2(
            gate_document,
            preregistration=cluster_preregistration,
            correlation_matrix=correlation_matrix,
            selection_cells=selection_cells,
            strategy_id=strategy_id,
            variant_id=variant_id,
            lane=lane,
        )
    except Exception:
        gate_verification = None
    if not _verification_passed(gate_verification):
        return _evaluation_document(
            status="UNKNOWN",
            reason_code="COMPLETE_LINK_GATE_DOCUMENT_INVALID",
            consumer_invocation_attempted=True,
            audit_verified=True,
            trusted_audit=audit_document,
            **common,
        )
    trace.append("COMPLETE_LINK_GATE_V2_VERIFIED")

    if (
        audit_document.get("current_admission_allowed") is not False
        or audit_document.get("current_writer_activation_allowed") is not False
        or gate_document.get("current_admission_allowed") is not False
        or gate_document.get("current_writer_activation_allowed") is not False
    ):
        return _evaluation_document(
            status="UNKNOWN",
            reason_code="CONSUMER_AUTHORITY_ESCALATION_REJECTED",
            consumer_invocation_attempted=True,
            audit_verified=True,
            gate_verified=True,
            trusted_audit=audit_document,
            **common,
        )

    return _evaluation_document(
        status="PASS",
        reason_code="GEOMETRY_AND_COMPLETE_LINK_CONSUMER_VERIFIED",
        consumer_invocation_attempted=True,
        audit_verified=True,
        gate_verified=True,
        trusted_audit=audit_document,
        trusted_gate=gate_document,
        **common,
    )


def verify_strategy_correlation_matrix_geometry_complete_link_binding_evaluation_v1(
    document: Any,
    binding_preregistration: Any,
    geometry_preregistration: Any,
    geometry_gate_document: Any,
    cluster_preregistration: Any,
    correlation_matrix: Any,
    selection_cells: Any,
    *,
    expected_evaluation_hash: Any,
    expected_binding_preregistration_hash: Any,
    expected_geometry_preregistration_hash: Any,
    expected_cluster_preregistration_hash: Any,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
) -> bool:
    """Re-evaluate the pure chain and compare the complete output exactly."""

    if not _is_exact_hash(expected_evaluation_hash):
        return False
    try:
        expected = evaluate_strategy_correlation_matrix_geometry_complete_link_binding_v1(
            binding_preregistration,
            geometry_preregistration,
            geometry_gate_document,
            cluster_preregistration,
            correlation_matrix,
            selection_cells,
            expected_binding_preregistration_hash=expected_binding_preregistration_hash,
            expected_geometry_preregistration_hash=(
                expected_geometry_preregistration_hash
            ),
            expected_cluster_preregistration_hash=expected_cluster_preregistration_hash,
            strategy_id=strategy_id,
            variant_id=variant_id,
            lane=lane,
        )
    except Exception:
        return False
    return bool(
        isinstance(document, dict)
        and _safe_hash(document, "evaluation_hash") == expected_evaluation_hash
        and compare_digest(expected["evaluation_hash"], expected_evaluation_hash)
        and document == expected
    )
