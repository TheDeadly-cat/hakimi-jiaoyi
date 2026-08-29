from __future__ import annotations

from typing import Any

from .portfolio_risk import (
    PORTFOLIO_RISK_SCHEMA_VERSION,
    build_correlation_matrix,
)
from .strategy_correlation_common_support_calendar_provider_composition_v1 import (
    SCHEMA_VERSION as CALENDAR_PROVIDER_COMPOSITION_SCHEMA_VERSION,
    verify_correlation_common_support_calendar_provider_composition_v1,
)
from .strategy_correlation_common_support_derivation_receipt_v1 import (
    RECEIPT_SCHEMA_VERSION as DERIVATION_RECEIPT_SCHEMA_VERSION,
    verify_correlation_common_support_derivation_receipt_v1,
)
from .strategy_correlation_provider_dataset_content_attestation_v1 import (
    SCHEMA_VERSION as DATASET_CONTENT_ATTESTATION_SCHEMA_VERSION,
    verify_provider_dataset_content_attestation_v1,
)
from .strategy_correlation_return_replay import (
    COMPLETED_PRICE_INPUT_SCHEMA_VERSION,
    CORRELATION_MATRIX_REPLAY_SCHEMA_VERSION,
    verify_correlation_completed_price_input,
    verify_correlation_matrix_replay,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


BINDING_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-"
    "legacy-matrix-derivation-binding-v1"
)
BINDING_VERIFICATION_SCHEMA_VERSION = f"{BINDING_SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = "20260822-legacy-matrix-signed-input-binding-lock-1"

_COMPOSITION_CONTEXT_KEYS = {
    "calendar_session_verification",
    "calendar_verification_bundle",
    "derivation_receipt",
    "matrix_replay",
    "provider_identity_verification",
    "provider_verification_bundle",
}


def _dict(value: Any) -> dict[str, Any]:
    return value if type(value) is dict else {}


def _list(value: Any) -> list[Any]:
    return value if type(value) is list else []


def _text_or_none(value: Any) -> str | None:
    return value if type(value) is str else None


def _research_authority() -> dict[str, bool]:
    return {
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "formal_registry_activation_allowed": False,
        "live_order_allowed": False,
        "migration_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
        "writer_allowed": False,
    }


def _check(name: str, ok: bool, pass_message: str, block_message: str) -> dict[str, Any]:
    return {
        "name": name,
        "ok": ok,
        "blocking": True,
        "message": pass_message if ok else block_message,
    }


def _legacy_payloads_from_completed_input(
    completed_price_input: Any,
) -> dict[str, dict[str, Any]] | None:
    datasets = _list(_dict(completed_price_input).get("datasets"))
    if len(datasets) < 2:
        return None
    payloads: dict[str, dict[str, Any]] = {}
    for item in datasets:
        if type(item) is not dict:
            return None
        symbol = item.get("symbol")
        price_rows = item.get("price_rows")
        if (
            type(symbol) is not str
            or not symbol.strip()
            or symbol != symbol.strip().upper()
            or type(price_rows) is not list
            or symbol in payloads
        ):
            return None
        payloads[symbol] = {"rows": price_rows}
    if list(payloads) != sorted(payloads):
        return None
    return payloads


def _verify_composition(
    composition_document: Any,
    composition_context: Any,
) -> bool:
    if (
        type(composition_document) is not dict
        or composition_document.get("schema_version")
        != CALENDAR_PROVIDER_COMPOSITION_SCHEMA_VERSION
        or type(composition_context) is not dict
        or set(composition_context) != _COMPOSITION_CONTEXT_KEYS
    ):
        return False
    try:
        verification = (
            verify_correlation_common_support_calendar_provider_composition_v1(
                composition_document,
                composition_context["derivation_receipt"],
                composition_context["matrix_replay"],
                composition_context["calendar_session_verification"],
                composition_context["calendar_verification_bundle"],
                composition_context["provider_identity_verification"],
                composition_context["provider_verification_bundle"],
            )
        )
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError):
        return False
    return bool(
        type(verification) is dict
        and verification.get("status") == "PASS"
        and not _list(verification.get("blockers"))
    )


def _verify_signed_content_claim(
    dataset_attestation_verification: Any,
    composition_document: Any,
    composition_context: Any,
    dataset_attestation_registration: Any,
    provider_dataset_public_key_base64: Any,
    dataset_attestation_receipt: Any,
    *,
    expected_registration_hash: Any,
    expected_attestation_hash: Any,
) -> bool:
    try:
        return (
            verify_provider_dataset_content_attestation_v1(
                dataset_attestation_verification,
                composition_document,
                composition_context,
                dataset_attestation_registration,
                provider_dataset_public_key_base64,
                dataset_attestation_receipt,
                expected_registration_hash=expected_registration_hash,
                expected_attestation_hash=expected_attestation_hash,
            )
            is True
        )
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError):
        return False


def _signed_claim_facts_valid(dataset_attestation_verification: Any) -> bool:
    document = _dict(dataset_attestation_verification)
    facts = _dict(document.get("facts"))
    return bool(
        document.get("schema_version") == DATASET_CONTENT_ATTESTATION_SCHEMA_VERSION
        and document.get("source_state") == "VERIFIED"
        and facts.get("source_composition_verified") is True
        and facts.get("provider_dataset_key_registration_verified") is True
        and facts.get("provider_dataset_signature_verified") is True
        and facts.get("provider_dataset_content_claim_verified") is True
        and facts.get("all_dataset_hashes_bound") is True
        and facts.get("receipt_structure_verified") is True
        and facts.get("receipt_content_hash_verified") is True
    )


def _external_trust_not_promoted(dataset_attestation_verification: Any) -> bool:
    document = _dict(dataset_attestation_verification)
    facts = _dict(document.get("facts"))
    authority = _dict(document.get("authority"))
    permissions = _dict(document.get("permissions"))
    return bool(
        facts.get("external_provider_dataset_key_control_verified") is False
        and facts.get("external_provider_data_issuance_verified") is False
        and facts.get("replay_registry_checked") is False
        and facts.get("observation_admission_allowed") is False
        and facts.get("profitability_verified") is False
        and authority.get("current_admission_allowed") is False
        and authority.get("live_order_allowed") is False
        and authority.get("observation_admission_allowed") is False
        and authority.get("paper_authorized") is False
        and authority.get("profitability_claim_allowed") is False
        and permissions.get("live_order_allowed") is False
        and permissions.get("paper_authorized") is False
    )


def build_strategy_correlation_cluster_portfolio_risk_legacy_matrix_derivation_binding_v1(
    legacy_correlation_matrix: Any,
    completed_price_input: Any,
    matrix_replay: Any,
    derivation_receipt: Any,
    composition_document: Any,
    composition_context: Any,
    dataset_attestation_verification: Any,
    dataset_attestation_registration: Any,
    provider_dataset_public_key_base64: Any,
    dataset_attestation_receipt: Any,
    *,
    expected_registration_hash: Any,
    expected_attestation_hash: Any,
) -> dict[str, Any]:
    replay_document = _dict(matrix_replay)
    preregistration = _dict(replay_document.get("preregistration"))

    completed_verification: dict[str, Any] = {}
    try:
        candidate = verify_correlation_completed_price_input(
            completed_price_input,
            preregistration=preregistration,
        )
        if type(candidate) is dict:
            completed_verification = candidate
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError):
        completed_verification = {}
    completed_ok = bool(
        _dict(completed_price_input).get("schema_version")
        == COMPLETED_PRICE_INPUT_SCHEMA_VERSION
        and completed_verification.get("status") == "PASS"
        and not _list(completed_verification.get("blockers"))
    )

    replay_verification: dict[str, Any] = {}
    try:
        candidate = verify_correlation_matrix_replay(matrix_replay)
        if type(candidate) is dict:
            replay_verification = candidate
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError):
        replay_verification = {}
    replay_ok = bool(
        replay_document.get("schema_version") == CORRELATION_MATRIX_REPLAY_SCHEMA_VERSION
        and replay_document.get("status") == "PASS"
        and replay_verification.get("status") == "PASS"
        and not _list(replay_verification.get("blockers"))
        and strict_json_contract_equal(
            replay_document.get("completed_price_input"),
            completed_price_input,
        )
    )

    derivation_verification: dict[str, Any] = {}
    try:
        candidate = verify_correlation_common_support_derivation_receipt_v1(
            derivation_receipt,
            matrix_replay=matrix_replay,
        )
        if type(candidate) is dict:
            derivation_verification = candidate
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError):
        derivation_verification = {}
    derivation_ok = bool(
        _dict(derivation_receipt).get("schema_version")
        == DERIVATION_RECEIPT_SCHEMA_VERSION
        and _dict(derivation_receipt).get("status") == "PASS"
        and derivation_verification.get("status") == "PASS"
        and not _list(derivation_verification.get("blockers"))
    )

    composition_ok = _verify_composition(composition_document, composition_context)
    signed_content_exact = _verify_signed_content_claim(
        dataset_attestation_verification,
        composition_document,
        composition_context,
        dataset_attestation_registration,
        provider_dataset_public_key_base64,
        dataset_attestation_receipt,
        expected_registration_hash=expected_registration_hash,
        expected_attestation_hash=expected_attestation_hash,
    )
    signed_content_claim_ok = bool(
        signed_content_exact
        and _signed_claim_facts_valid(dataset_attestation_verification)
    )
    external_trust_lock_ok = _external_trust_not_promoted(
        dataset_attestation_verification
    )

    completed_document = _dict(completed_price_input)
    derivation_document = _dict(derivation_receipt)
    composition = _dict(composition_document)
    attestation = _dict(dataset_attestation_verification)
    completed_hash = completed_document.get("input_hash")
    replay_hash = replay_document.get("replay_hash")
    derivation_hash = derivation_document.get("receipt_hash")
    composition_hash = composition.get("composition_hash")
    hash_lineage_ok = bool(
        type(completed_hash) is str
        and _dict(replay_document.get("completed_price_input")).get("input_hash")
        == completed_hash
        and derivation_document.get("source_completed_price_input_hash")
        == completed_hash
        and composition.get("source_completed_price_input_hash") == completed_hash
        and type(replay_hash) is str
        and derivation_document.get("source_matrix_replay_hash") == replay_hash
        and composition.get("source_matrix_replay_hash") == replay_hash
        and type(derivation_hash) is str
        and composition.get("source_derivation_receipt_hash") == derivation_hash
        and type(composition_hash) is str
        and attestation.get("source_composition_hash") == composition_hash
    )

    legacy_payloads = _legacy_payloads_from_completed_input(completed_price_input)
    lookback = preregistration.get("lookback_observations")
    minimum_overlap = preregistration.get("minimum_pair_overlap")
    rebuilt_legacy: dict[str, Any] = {}
    if (
        completed_ok
        and legacy_payloads is not None
        and type(lookback) is int
        and type(minimum_overlap) is int
    ):
        try:
            candidate = build_correlation_matrix(
                legacy_payloads,
                lookback=lookback,
                minimum_overlap=minimum_overlap,
            )
            if type(candidate) is dict:
                rebuilt_legacy = candidate
        except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError):
            rebuilt_legacy = {}
    legacy_exact = bool(
        rebuilt_legacy.get("schema_version") == PORTFOLIO_RISK_SCHEMA_VERSION
        and rebuilt_legacy.get("status") == "PASS"
        and strict_json_contract_equal(legacy_correlation_matrix, rebuilt_legacy)
    )

    checks = [
        _check(
            "completed_price_input_exact",
            completed_ok,
            "Frozen completed-price input verifies against preregistration.",
            "Frozen completed-price input is invalid or unverifiable.",
        ),
        _check(
            "matrix_replay_exact",
            replay_ok,
            "Matrix replay exactly embeds the frozen completed-price input.",
            "Matrix replay is invalid or binds a different completed-price input.",
        ),
        _check(
            "common_support_derivation_exact",
            derivation_ok,
            "Common-support derivation receipt matches the matrix replay.",
            "Common-support derivation receipt is invalid or mismatched.",
        ),
        _check(
            "calendar_provider_composition_exact",
            composition_ok,
            "Calendar/provider composition matches its full verification context.",
            "Calendar/provider composition is invalid or mismatched.",
        ),
        _check(
            "signed_dataset_content_claim_exact",
            signed_content_claim_ok,
            "Registered dataset key signature binds the composition content claim.",
            "Dataset content signature claim is invalid or mismatched.",
        ),
        _check(
            "completed_price_hash_lineage",
            hash_lineage_ok,
            "Completed-price hash is continuous through replay, derivation, composition, and attestation.",
            "Completed-price hash lineage is broken or incomplete.",
        ),
        _check(
            "legacy_matrix_exact_rebuild",
            legacy_exact,
            "Legacy correlation matrix exactly rebuilds from the frozen completed-price rows.",
            "Legacy correlation matrix differs from deterministic rebuild.",
        ),
        _check(
            "external_trust_not_promoted",
            external_trust_lock_ok,
            "External provider trust, replay, admission, and profitability remain unproven.",
            "An external-trust or authority field was promoted.",
        ),
    ]
    blockers = [item["name"] for item in checks if item["ok"] is not True]
    status = "PASS" if not blockers else "BLOCK"
    legacy_document = _dict(legacy_correlation_matrix)
    legacy_symbols = legacy_document.get("symbols")
    document: dict[str, Any] = {
        "schema_version": BINDING_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "decision": (
            "LEGACY_MATRIX_BOUND_TO_SIGNED_CONTENT_CLAIM_EXTERNAL_TRUST_UNPROVEN"
            if status == "PASS"
            else "BLOCKED_LEGACY_MATRIX_DERIVATION_BINDING"
        ),
        "source": {
            "completed_price_input_hash": (
                _text_or_none(completed_hash) if hash_lineage_ok else None
            ),
            "matrix_replay_hash": (
                _text_or_none(replay_hash) if replay_ok else None
            ),
            "derivation_receipt_hash": (
                _text_or_none(derivation_hash) if derivation_ok else None
            ),
            "composition_hash": (
                _text_or_none(composition_hash) if composition_ok else None
            ),
            "dataset_attestation_verification_hash": (
                _text_or_none(attestation.get("verification_hash"))
                if signed_content_claim_ok
                else None
            ),
            "legacy_matrix_hash": (
                _text_or_none(legacy_document.get("matrix_hash"))
                if legacy_exact
                else None
            ),
            "preregistration_hash": (
                _text_or_none(preregistration.get("preregistration_hash"))
                if replay_ok
                else None
            ),
            "provider_id_hash": (
                _text_or_none(attestation.get("provider_id_hash"))
                if signed_content_claim_ok
                else None
            ),
            "provider_dataset_public_key_sha256": (
                _text_or_none(attestation.get("provider_dataset_public_key_sha256"))
                if signed_content_claim_ok
                else None
            ),
        },
        "portfolio_matrix": {
            "cutoff_date": (
                _text_or_none(completed_document.get("cutoff_date"))
                if completed_ok
                else None
            ),
            "dataset_count": (
                completed_document.get("dataset_count")
                if type(completed_document.get("dataset_count")) is int
                and completed_ok
                else None
            ),
            "symbols": legacy_symbols if type(legacy_symbols) is list and legacy_exact else [],
            "lookback_observations": lookback if type(lookback) is int and replay_ok else None,
            "minimum_pair_overlap": (
                minimum_overlap if type(minimum_overlap) is int and replay_ok else None
            ),
        },
        "checks": checks,
        "blockers": blockers,
        "facts": {
            "legacy_matrix_deterministically_rebuilt": legacy_exact,
            "signed_dataset_content_claim_verified": signed_content_claim_ok,
            "external_provider_dataset_key_control_verified": False,
            "external_provider_data_issuance_verified": False,
            "provider_replay_registry_checked": False,
            "observation_admission_allowed": False,
            "profitability_verified": False,
            "completed_price_rows_embedded": False,
            "matrix_replay_embedded": False,
            "composition_embedded": False,
            "attestation_receipt_embedded": False,
            "runtime_assets_accessed": False,
            "runtime_consumer_bound": False,
        },
        "authority": _research_authority(),
    }
    return seal_strict_canonical_document(document, "binding_hash")


def verify_strategy_correlation_cluster_portfolio_risk_legacy_matrix_derivation_binding_v1(
    document: Any,
    legacy_correlation_matrix: Any,
    completed_price_input: Any,
    matrix_replay: Any,
    derivation_receipt: Any,
    composition_document: Any,
    composition_context: Any,
    dataset_attestation_verification: Any,
    dataset_attestation_registration: Any,
    provider_dataset_public_key_base64: Any,
    dataset_attestation_receipt: Any,
    *,
    expected_registration_hash: Any,
    expected_attestation_hash: Any,
) -> dict[str, Any]:
    expected = build_strategy_correlation_cluster_portfolio_risk_legacy_matrix_derivation_binding_v1(
        legacy_correlation_matrix,
        completed_price_input,
        matrix_replay,
        derivation_receipt,
        composition_document,
        composition_context,
        dataset_attestation_verification,
        dataset_attestation_registration,
        provider_dataset_public_key_base64,
        dataset_attestation_receipt,
        expected_registration_hash=expected_registration_hash,
        expected_attestation_hash=expected_attestation_hash,
    )
    exact = strict_json_contract_equal(document, expected)
    return {
        "schema_version": BINDING_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "blockers": [] if exact else ["legacy_matrix_binding_exact_rebuild_mismatch"],
        "binding_decision": expected["decision"] if exact else "UNKNOWN",
        "binding_exactly_verified": exact,
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
    }


__all__ = [
    "BINDING_SCHEMA_VERSION",
    "BINDING_VERIFICATION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_cluster_portfolio_risk_legacy_matrix_derivation_binding_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_legacy_matrix_derivation_binding_v1",
]
