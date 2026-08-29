from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import strict_sha256
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1 import (
    POSITIVE_STATE as SOURCE_POSITIVE_STATE,
    SCHEMA_VERSION as SOURCE_SCHEMA_VERSION,
    STATIC_FINGERPRINT as SOURCE_STATIC_FINGERPRINT,
    VERIFIED_BLOCKERS,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1,
)


SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-"
    "provider-identity-presentation-envelope-v1"
)
STATIC_FINGERPRINT = (
    "20260925-cross-lag-factor-calibration-long-horizon-"
    "provider-identity-presentation-envelope-1"
)
PRESENTATION_STATUS = "UNMOUNTED_CANDIDATE"
POSITIVE_DISPLAY_STATE = "CRYPTOGRAPHIC_PROOF_BOUND_EXTERNAL_TRUST_GAP"
AXIS_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")

_CONTEXT_KEYS = frozenset(
    {
        "expected_identity_assertion_hash",
        "expected_provider_identity_registration_hash",
        "identity_assertion_receipt",
        "provider_identity_registration_v1",
        "provider_identity_registration_verification_context",
    }
)


def _authority() -> dict[str, bool]:
    return {
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
        "provider_identity_admission_allowed": False,
    }


def _facts(*, source_verified: bool = False) -> dict[str, bool]:
    return {
        "cryptographic_identity_assertion_verified": source_verified,
        "external_identity_registry_authenticity_proven": False,
        "external_registration_time_verified": False,
        "provider_identity_verified": False,
        "replay_registry_checked": False,
        "result_available": False,
        "source_assertion_verification_verified": source_verified,
    }


def _safe_text(document: Any, key: str) -> str | None:
    if type(document) is not dict:
        return None
    value = document.get(key)
    return value if type(value) is str else None


def _safe_hash(document: Any, key: str) -> str | None:
    value = _safe_text(document, key)
    return value if strict_sha256(value) else None


def _safe_count(document: Any, key: str) -> int | None:
    if type(document) is not dict:
        return None
    value = document.get(key)
    return value if type(value) is int and type(value) is not bool and value >= 0 else None


def _source_state(document: Any) -> str:
    value = _safe_text(document, "source_state")
    return value if value in {"VERIFIED", "BLOCKED", "UNKNOWN"} else "UNKNOWN"


def _summary(source: Any) -> dict[str, Any]:
    return {
        "asserted_at_utc": _safe_text(source, "asserted_at_utc"),
        "assertion_id": _safe_text(source, "assertion_id"),
        "identity_registry_id": _safe_text(source, "identity_registry_id"),
        "identity_registry_snapshot_id": _safe_text(
            source, "identity_registry_snapshot_id"
        ),
        "membership_leaf_index": _safe_count(source, "membership_leaf_index"),
        "membership_proof_count": _safe_count(source, "membership_proof_count"),
        "membership_tree_size": _safe_count(source, "membership_tree_size"),
        "provider_id": _safe_text(source, "provider_id"),
        "provider_subject_id": _safe_text(source, "provider_subject_id"),
        "valid_until_utc": _safe_text(source, "valid_until_utc"),
    }


def _lineage(source: Any, expected_source_hash: Any) -> dict[str, str | None]:
    return {
        "assertion_content_sha256": _safe_hash(source, "assertion_content_sha256"),
        "assertion_hash": _safe_hash(source, "assertion_hash"),
        "identity_registry_snapshot_sha256": _safe_hash(
            source, "identity_registry_snapshot_sha256"
        ),
        "identity_registry_trust_root_sha256": _safe_hash(
            source, "identity_registry_trust_root_sha256"
        ),
        "membership_proof_hash": _safe_hash(source, "membership_proof_hash"),
        "provider_identity_document_sha256": _safe_hash(
            source, "provider_identity_document_sha256"
        ),
        "provider_receipt_trust_root_sha256": _safe_hash(
            source, "provider_receipt_trust_root_sha256"
        ),
        "source_provider_identity_registration_hash": _safe_hash(
            source, "source_provider_identity_registration_hash"
        ),
        "source_verification_hash": (
            expected_source_hash if strict_sha256(expected_source_hash) else None
        ),
    }


def _unknown_axes() -> list[dict[str, str]]:
    return [
        {
            "axis": axis,
            "detail": "The sealed source contract did not verify for presentation.",
            "headline": "Evidence unavailable",
            "signal": "UNKNOWN",
            "state": "UNKNOWN",
        }
        for axis in AXIS_ORDER
    ]


def _positive_axes() -> list[dict[str, str]]:
    return [
        {
            "axis": "SOURCE",
            "detail": (
                "Registry-key signature and frozen snapshot membership match "
                "the preregistered provider document."
            ),
            "headline": "Cryptographic assertion bound",
            "signal": "SIGNATURE + MEMBERSHIP",
            "state": "CRYPTOGRAPHIC_PROOF_BOUND",
        },
        {
            "axis": "GAP",
            "detail": (
                "External registry authority, external time, and append-only "
                "assertion replay remain unproven."
            ),
            "headline": "Trust root remains external",
            "signal": "ROOT / TIME / REPLAY",
            "state": "EXTERNAL_TRUST_TIME_REPLAY_UNPROVEN",
        },
        {
            "axis": "MATURITY",
            "detail": (
                "This is a detached research candidate, not an active provider "
                "identity consumer."
            ),
            "headline": "Verification candidate only",
            "signal": "UNMOUNTED CANDIDATE",
            "state": "DETACHED_CANDIDATE",
        },
        {
            "axis": "PERMISSION",
            "detail": (
                "Provider identity admission, evaluation, paper, and live "
                "authority remain locked."
            ),
            "headline": "No permission granted",
            "signal": "NO ADMISSION",
            "state": "LOCKED",
        },
    ]


def _unknown(reason: str, source: Any, expected_source_hash: Any) -> dict[str, Any]:
    document: dict[str, Any] = {
        "authority": _authority(),
        "axes": _unknown_axes(),
        "axis_order": list(AXIS_ORDER),
        "blockers": [reason],
        "display_state": "UNKNOWN",
        "facts": _facts(),
        "lineage": _lineage(source, expected_source_hash),
        "presentation_status": PRESENTATION_STATUS,
        "schema_version": SCHEMA_VERSION,
        "source_schema_version": _safe_text(source, "schema_version"),
        "source_state": _source_state(source),
        "source_static_fingerprint": _safe_text(source, "static_fingerprint"),
        "source_verification_state": _safe_text(
            source, "identity_assertion_verification_state"
        ),
        "static_fingerprint": STATIC_FINGERPRINT,
        "summary": _summary(source),
    }
    return seal_strict_canonical_document(document, "presentation_hash")


def build_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_presentation_envelope_v1(
    provider_identity_assertion_verification_v1: Any,
    provider_identity_assertion_verification_context: Any,
    *,
    expected_provider_identity_assertion_verification_hash: Any,
) -> dict[str, Any]:
    source = provider_identity_assertion_verification_v1
    expected_source_hash = expected_provider_identity_assertion_verification_hash
    if not strict_sha256(expected_source_hash):
        return _unknown("EXPECTED_SOURCE_VERIFICATION_HASH_INVALID", source, expected_source_hash)
    if type(source) is not dict or source.get("verification_hash") != expected_source_hash:
        return _unknown("SOURCE_VERIFICATION_HASH_MISMATCH", source, expected_source_hash)
    if source.get("schema_version") != SOURCE_SCHEMA_VERSION:
        return _unknown("SOURCE_VERIFICATION_SCHEMA_UNSUPPORTED", source, expected_source_hash)
    context = provider_identity_assertion_verification_context
    if type(context) is not dict or set(context) != _CONTEXT_KEYS:
        return _unknown("SOURCE_VERIFICATION_CONTEXT_INVALID", source, expected_source_hash)
    try:
        source_verified = (
            verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1(
                source,
                context["provider_identity_registration_v1"],
                context["provider_identity_registration_verification_context"],
                context["identity_assertion_receipt"],
                expected_provider_identity_registration_hash=context[
                    "expected_provider_identity_registration_hash"
                ],
                expected_identity_assertion_hash=context[
                    "expected_identity_assertion_hash"
                ],
            )
        )
    except Exception:
        source_verified = False
    if not source_verified:
        return _unknown("SOURCE_VERIFICATION_NOT_VERIFIED", source, expected_source_hash)
    if (
        source.get("static_fingerprint") != SOURCE_STATIC_FINGERPRINT
        or source.get("source_state") != "VERIFIED"
        or source.get("identity_assertion_verification_state") != SOURCE_POSITIVE_STATE
        or source.get("blockers") != list(VERIFIED_BLOCKERS)
    ):
        return _unknown("SOURCE_VERIFICATION_STATE_INVALID", source, expected_source_hash)
    source_facts = source.get("facts")
    source_authority = source.get("authority")
    if (
        type(source_facts) is not dict
        or source_facts.get("identity_registry_signature_verified") is not True
        or source_facts.get("snapshot_membership_verified") is not True
        or source_facts.get("external_identity_registry_authenticity_proven") is not False
        or source_facts.get("provider_identity_verified") is not False
        or source_facts.get("replay_registry_checked") is not False
        or type(source_authority) is not dict
        or source_authority.get("provider_identity_admission_allowed") is not False
        or source_authority.get("current_admission_allowed") is not False
    ):
        return _unknown("SOURCE_AUTHORITY_OR_FACTS_INVALID", source, expected_source_hash)

    lineage = _lineage(source, expected_source_hash)
    if not all(strict_sha256(value) for value in lineage.values()):
        return _unknown("SOURCE_LINEAGE_HASH_INVALID", source, expected_source_hash)
    summary = _summary(source)
    tree_size = summary["membership_tree_size"]
    leaf_index = summary["membership_leaf_index"]
    proof_count = summary["membership_proof_count"]
    if (
        type(tree_size) is not int
        or tree_size < 1
        or tree_size & (tree_size - 1)
        or type(leaf_index) is not int
        or leaf_index >= tree_size
        or proof_count != tree_size.bit_length() - 1
    ):
        return _unknown("SOURCE_MEMBERSHIP_AGGREGATES_INVALID", source, expected_source_hash)

    document: dict[str, Any] = {
        "authority": _authority(),
        "axes": _positive_axes(),
        "axis_order": list(AXIS_ORDER),
        "blockers": list(VERIFIED_BLOCKERS),
        "display_state": POSITIVE_DISPLAY_STATE,
        "facts": _facts(source_verified=True),
        "lineage": lineage,
        "presentation_status": PRESENTATION_STATUS,
        "schema_version": SCHEMA_VERSION,
        "source_schema_version": SOURCE_SCHEMA_VERSION,
        "source_state": "VERIFIED",
        "source_static_fingerprint": SOURCE_STATIC_FINGERPRINT,
        "source_verification_state": SOURCE_POSITIVE_STATE,
        "static_fingerprint": STATIC_FINGERPRINT,
        "summary": summary,
    }
    return seal_strict_canonical_document(document, "presentation_hash")


def verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_presentation_envelope_v1(
    document: Any,
    provider_identity_assertion_verification_v1: Any,
    provider_identity_assertion_verification_context: Any,
    *,
    expected_provider_identity_assertion_verification_hash: Any,
) -> bool:
    if type(document) is not dict:
        return False
    try:
        rebuilt = build_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_presentation_envelope_v1(
            provider_identity_assertion_verification_v1,
            provider_identity_assertion_verification_context,
            expected_provider_identity_assertion_verification_hash=(
                expected_provider_identity_assertion_verification_hash
            ),
        )
    except Exception:
        return False
    return strict_json_contract_equal(document, rebuilt)
