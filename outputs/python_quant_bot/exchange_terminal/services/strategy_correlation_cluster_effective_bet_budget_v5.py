"""Signed portfolio-snapshot consumer for effective correlation budgets."""

from __future__ import annotations

import base64
import binascii
import copy
import math
import re
from hashlib import sha256
from typing import Any

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v4 as budget_v4,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


PROVIDER_PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-portfolio-snapshot-provider-preregistration-v1"
)
SNAPSHOT_CLAIM_SCHEMA_VERSION = (
    "strategy-correlation-portfolio-snapshot-claim-v1"
)
SIGNED_SNAPSHOT_SCHEMA_VERSION = (
    "strategy-correlation-portfolio-signed-snapshot-v1"
)
SNAPSHOT_EVIDENCE_SCHEMA_VERSION = (
    "strategy-correlation-portfolio-snapshot-signature-evidence-v1"
)
BUDGET_SCHEMA_VERSION = "strategy-correlation-cluster-effective-bet-budget-v5"
BUDGET_VERIFICATION_SCHEMA_VERSION = f"{BUDGET_SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = (
    "20260824-signed-portfolio-snapshot-effective-budget-v5-synthetic-lock-1"
)
V4_IMPLEMENTATION_SHA256 = (
    "f32239e4d3c2c5a015044ad2e5f8522b093b45746056f0656437cc92b23955f2"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
SIGNATURE_ALGORITHM = "ED25519"
SIGNATURE_DOMAIN = (
    "hakimi.strategy-correlation.portfolio-snapshot-source.v1"
)
SIGNATURE_MESSAGE_FORMAT = "RAW_SHA256_DIGEST_BYTES_V1"

_HASH = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")
_MAX_UNIX_MS = 253_402_300_799_999


class SignedPortfolioSnapshotBudgetError(ValueError):
    pass


def _require_hash(value: Any, label: str) -> str:
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise SignedPortfolioSnapshotBudgetError(
            f"{label} must be lowercase sha256"
        )
    return value


def _require_identifier(value: Any, label: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise SignedPortfolioSnapshotBudgetError(
            f"{label} must be a strict identifier"
        )
    return value


def _require_int(
    value: Any,
    label: str,
    *,
    maximum: int | None = None,
) -> int:
    if type(value) is not int or value < 0:
        raise SignedPortfolioSnapshotBudgetError(
            f"{label} must be a non-negative integer"
        )
    if maximum is not None and value > maximum:
        raise SignedPortfolioSnapshotBudgetError(f"{label} exceeds maximum")
    return value


def _number(value: Any, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SignedPortfolioSnapshotBudgetError("numeric value is invalid")
    clean = float(value)
    if not math.isfinite(clean):
        raise SignedPortfolioSnapshotBudgetError("numeric value is non-finite")
    if positive and clean <= 0.0:
        raise SignedPortfolioSnapshotBudgetError(
            "numeric value must be positive"
        )
    if not positive and clean < 0.0:
        raise SignedPortfolioSnapshotBudgetError(
            "numeric value must be non-negative"
        )
    return round(clean, 8)


def _normalize_positions(value: Any) -> list[dict[str, Any]]:
    if type(value) is not list:
        raise SignedPortfolioSnapshotBudgetError("positions must be a list")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in value:
        if (
            type(row) is not dict
            or set(row) != {"symbol", "notional", "direction"}
        ):
            raise SignedPortfolioSnapshotBudgetError(
                "position schema is not exact"
            )
        symbol = (
            row["symbol"].strip().upper()
            if type(row["symbol"]) is str
            else ""
        )
        direction = (
            row["direction"].strip().upper()
            if type(row["direction"]) is str
            else ""
        )
        notional = _number(row["notional"], positive=True)
        if not symbol or direction not in {"LONG", "SHORT"}:
            raise SignedPortfolioSnapshotBudgetError("position is invalid")
        if symbol in seen:
            raise SignedPortfolioSnapshotBudgetError(
                "position symbols must be unique"
            )
        seen.add(symbol)
        normalized.append(
            {
                "symbol": symbol,
                "notional": notional,
                "direction": direction,
            }
        )
    return sorted(normalized, key=lambda row: row["symbol"])


def _decode_base64(
    value: Any,
    label: str,
    *,
    expected_length: int | None = None,
) -> bytes:
    if type(value) is not str or not value:
        raise SignedPortfolioSnapshotBudgetError(
            f"{label} must be canonical base64"
        )
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise SignedPortfolioSnapshotBudgetError(
            f"{label} must be canonical base64"
        ) from exc
    if base64.b64encode(decoded).decode("ascii") != value:
        raise SignedPortfolioSnapshotBudgetError(
            f"{label} must be canonical base64"
        )
    if expected_length is not None and len(decoded) != expected_length:
        raise SignedPortfolioSnapshotBudgetError(
            f"{label} length mismatch"
        )
    return decoded


def _load_ed25519_spki(value: Any) -> tuple[Ed25519PublicKey, bytes]:
    der = _decode_base64(value, "public_key_spki_base64")
    try:
        key = serialization.load_der_public_key(der)
    except (TypeError, ValueError, UnsupportedAlgorithm) as exc:
        raise SignedPortfolioSnapshotBudgetError(
            "public key must be canonical Ed25519 DER-SPKI"
        ) from exc
    if not isinstance(key, Ed25519PublicKey):
        raise SignedPortfolioSnapshotBudgetError(
            "public key must be Ed25519"
        )
    canonical = key.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    if canonical != der:
        raise SignedPortfolioSnapshotBudgetError(
            "public key DER-SPKI is not canonical"
        )
    return key, der


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "snapshot_source_trust_allowed": False,
        "runtime_gate_activation_allowed": False,
        "migration_allowed": False,
        "writer_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def build_portfolio_snapshot_provider_preregistration_v1(
    *,
    provider_id: Any,
    key_id: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
    account_scope_hash: Any,
    implementation_claim_sha256: Any,
) -> dict[str, Any]:
    identity = {
        "provider_id": _require_identifier(provider_id, "provider_id"),
        "key_id": _require_identifier(key_id, "key_id"),
        "public_key_spki_sha256": _require_hash(
            public_key_spki_sha256, "public_key_spki_sha256"
        ),
        "trust_domain": _require_identifier(trust_domain, "trust_domain"),
        "account_scope_hash": _require_hash(
            account_scope_hash, "account_scope_hash"
        ),
        "implementation_claim_sha256": _require_hash(
            implementation_claim_sha256,
            "implementation_claim_sha256",
        ),
    }
    document = {
        "schema_version": PROVIDER_PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "PORTFOLIO_SNAPSHOT_PROVIDER_PREREGISTERED_IDENTITY_KEY_"
            "IMPLEMENTATION_SOURCE_TRUTH_AND_CONTINUITY_UNVERIFIED"
        ),
        "identity": identity,
        "facts": {
            "local_preregistration_complete": True,
            "identity_fields_preregistered": True,
            "public_key_hash_preregistered": True,
            "account_scope_preregistered": True,
            "implementation_claim_preregistered": True,
            "provider_identity_verified": False,
            "provider_key_possession_verified": False,
            "provider_implementation_verified": False,
            "snapshot_source_truth_verified": False,
            "snapshot_sequence_continuity_verified": False,
            "snapshot_freshness_verified": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "authority": _authority(),
        "blockers": [
            "SNAPSHOT_PROVIDER_IDENTITY_UNVERIFIED",
            "SNAPSHOT_PROVIDER_KEY_POSSESSION_UNVERIFIED",
            "SNAPSHOT_PROVIDER_IMPLEMENTATION_UNVERIFIED",
            "SNAPSHOT_SOURCE_TRUTH_UNVERIFIED",
            "SNAPSHOT_SEQUENCE_CONTINUITY_UNVERIFIED",
            "SNAPSHOT_FRESHNESS_UNVERIFIED",
            "CURRENT_ACTIVATION_UNAUTHORIZED",
        ],
    }
    return seal_strict_canonical_document(
        document, "provider_preregistration_hash"
    )


def verify_portfolio_snapshot_provider_preregistration_v1(
    document: Any, **kwargs: Any
) -> bool:
    try:
        return document == build_portfolio_snapshot_provider_preregistration_v1(
            **kwargs
        )
    except (TypeError, SignedPortfolioSnapshotBudgetError):
        return False


def _exact_provider_preregistration(
    document: Any, kwargs: Any
) -> dict[str, Any]:
    if type(kwargs) is not dict:
        raise SignedPortfolioSnapshotBudgetError(
            "provider_preregistration_kwargs must be a dict"
        )
    try:
        expected = build_portfolio_snapshot_provider_preregistration_v1(
            **copy.deepcopy(kwargs)
        )
    except (TypeError, SignedPortfolioSnapshotBudgetError) as exc:
        raise SignedPortfolioSnapshotBudgetError(
            "provider preregistration kwargs are invalid"
        ) from exc
    if document != expected:
        raise SignedPortfolioSnapshotBudgetError(
            "provider preregistration is not exact"
        )
    return expected


def build_portfolio_snapshot_claim_v1(
    provider_preregistration_document: Any,
    *,
    provider_preregistration_kwargs: Any,
    snapshot_id_hash: Any,
    snapshot_sequence: Any,
    observed_at_unix_ms: Any,
    equity: Any,
    positions: Any,
) -> dict[str, Any]:
    provider = _exact_provider_preregistration(
        provider_preregistration_document,
        provider_preregistration_kwargs,
    )
    snapshot_id = _require_hash(snapshot_id_hash, "snapshot_id_hash")
    sequence = _require_int(snapshot_sequence, "snapshot_sequence")
    observed = _require_int(
        observed_at_unix_ms,
        "observed_at_unix_ms",
        maximum=_MAX_UNIX_MS,
    )
    clean_equity = _number(equity, positive=True)
    clean_positions = _normalize_positions(positions)
    gross = round(
        sum(row["notional"] for row in clean_positions), 8
    )
    document = {
        "schema_version": SNAPSHOT_CLAIM_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "PORTFOLIO_SNAPSHOT_CLAIM_UNSIGNED_SOURCE_IDENTITY_TRUTH_"
            "CONTINUITY_AND_FRESHNESS_UNVERIFIED"
        ),
        "source": {
            "provider_preregistration_hash": provider[
                "provider_preregistration_hash"
            ],
            "provider_id": provider["identity"]["provider_id"],
            "key_id": provider["identity"]["key_id"],
            "account_scope_hash": provider["identity"][
                "account_scope_hash"
            ],
        },
        "snapshot": {
            "snapshot_id_hash": snapshot_id,
            "snapshot_sequence": sequence,
            "observed_at_unix_ms": observed,
            "equity": clean_equity,
            "positions": clean_positions,
            "position_count": len(clean_positions),
            "portfolio_gross_notional": gross,
        },
        "signature_contract": {
            "algorithm": SIGNATURE_ALGORITHM,
            "domain": SIGNATURE_DOMAIN,
            "message_format": SIGNATURE_MESSAGE_FORMAT,
        },
        "facts": {
            "provider_preregistration_exact": True,
            "snapshot_shape_exact": True,
            "position_symbols_unique": True,
            "snapshot_signature_verified": False,
            "provider_identity_verified": False,
            "provider_implementation_verified": False,
            "snapshot_source_truth_verified": False,
            "snapshot_sequence_continuity_verified": False,
            "snapshot_freshness_verified": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "authority": _authority(),
        "blockers": [
            "SNAPSHOT_SIGNATURE_UNVERIFIED",
            "SNAPSHOT_PROVIDER_IDENTITY_UNVERIFIED",
            "SNAPSHOT_PROVIDER_IMPLEMENTATION_UNVERIFIED",
            "SNAPSHOT_SOURCE_TRUTH_UNVERIFIED",
            "SNAPSHOT_SEQUENCE_CONTINUITY_UNVERIFIED",
            "SNAPSHOT_FRESHNESS_UNVERIFIED",
            "CURRENT_ACTIVATION_UNAUTHORIZED",
        ],
    }
    return seal_strict_canonical_document(document, "snapshot_claim_hash")


def verify_portfolio_snapshot_claim_v1(
    document: Any,
    provider_preregistration_document: Any,
    *,
    expected_snapshot_claim_hash: Any,
    **build_kwargs: Any,
) -> bool:
    try:
        expected = build_portfolio_snapshot_claim_v1(
            provider_preregistration_document, **build_kwargs
        )
        return (
            document == expected
            and _require_hash(
                expected_snapshot_claim_hash,
                "expected_snapshot_claim_hash",
            )
            == expected["snapshot_claim_hash"]
        )
    except (TypeError, SignedPortfolioSnapshotBudgetError):
        return False


def _exact_snapshot_claim(
    claim_document: Any,
    provider_preregistration_document: Any,
    expected_claim_hash: Any,
    claim_build_kwargs: Any,
) -> dict[str, Any]:
    if type(claim_build_kwargs) is not dict:
        raise SignedPortfolioSnapshotBudgetError(
            "claim_build_kwargs must be a dict"
        )
    try:
        expected = build_portfolio_snapshot_claim_v1(
            provider_preregistration_document,
            **copy.deepcopy(claim_build_kwargs),
        )
    except (TypeError, SignedPortfolioSnapshotBudgetError) as exc:
        raise SignedPortfolioSnapshotBudgetError(
            "snapshot claim kwargs are invalid"
        ) from exc
    claim_hash = _require_hash(
        expected_claim_hash, "expected_snapshot_claim_hash"
    )
    if (
        claim_document != expected
        or claim_hash != expected["snapshot_claim_hash"]
    ):
        raise SignedPortfolioSnapshotBudgetError(
            "snapshot claim is not exact"
        )
    return expected


def build_signed_portfolio_snapshot_v1(
    claim_document: Any,
    provider_preregistration_document: Any,
    *,
    public_key_spki_base64: Any,
    signature_base64: Any,
    expected_snapshot_claim_hash: Any,
    claim_build_kwargs: Any,
) -> dict[str, Any]:
    claim = _exact_snapshot_claim(
        claim_document,
        provider_preregistration_document,
        expected_snapshot_claim_hash,
        claim_build_kwargs,
    )
    _, der = _load_ed25519_spki(public_key_spki_base64)
    signature = _decode_base64(
        signature_base64, "signature_base64", expected_length=64
    )
    document = {
        "schema_version": SIGNED_SNAPSHOT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "CANDIDATE",
        "snapshot_claim_hash": claim["snapshot_claim_hash"],
        "provider_preregistration_hash": provider_preregistration_document[
            "provider_preregistration_hash"
        ],
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signature_domain": SIGNATURE_DOMAIN,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "public_key_spki_base64": public_key_spki_base64,
        "public_key_spki_sha256": sha256(der).hexdigest(),
        "signature_base64": signature_base64,
        "signature_sha256": sha256(signature).hexdigest(),
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "signed_snapshot_hash")


def _safe_hash(value: Any) -> str | None:
    return value if type(value) is str and _HASH.fullmatch(value) else None


def evaluate_signed_portfolio_snapshot_v1(
    signed_snapshot_document: Any,
    claim_document: Any,
    provider_preregistration_document: Any,
    *,
    public_key_spki_base64: Any,
    signature_base64: Any,
    expected_snapshot_claim_hash: Any,
    expected_signed_snapshot_hash: Any,
    claim_build_kwargs: Any,
) -> dict[str, Any]:
    claim_exact = False
    signed_exact = False
    key_hash_matches = False
    cryptographic_signature_verified = False
    key_hash = None
    provider_hash = None
    snapshot_id_hash = None
    snapshot_sequence = None
    observed_at_unix_ms = None
    equity = None
    position_count = None
    portfolio_gross_notional = None
    try:
        claim = _exact_snapshot_claim(
            claim_document,
            provider_preregistration_document,
            expected_snapshot_claim_hash,
            claim_build_kwargs,
        )
        claim_exact = True
        key, der = _load_ed25519_spki(public_key_spki_base64)
        signature = _decode_base64(
            signature_base64, "signature_base64", expected_length=64
        )
        key_hash = sha256(der).hexdigest()
        provider = _exact_provider_preregistration(
            provider_preregistration_document,
            claim_build_kwargs.get("provider_preregistration_kwargs"),
        )
        provider_hash = provider["provider_preregistration_hash"]
        key_hash_matches = (
            key_hash == provider["identity"]["public_key_spki_sha256"]
        )
        try:
            key.verify(
                signature,
                bytes.fromhex(claim["snapshot_claim_hash"]),
            )
            cryptographic_signature_verified = True
        except InvalidSignature:
            cryptographic_signature_verified = False
        expected_signed = build_signed_portfolio_snapshot_v1(
            claim_document,
            provider_preregistration_document,
            public_key_spki_base64=public_key_spki_base64,
            signature_base64=signature_base64,
            expected_snapshot_claim_hash=claim["snapshot_claim_hash"],
            claim_build_kwargs=claim_build_kwargs,
        )
        signed_exact = (
            signed_snapshot_document == expected_signed
            and _require_hash(
                expected_signed_snapshot_hash,
                "expected_signed_snapshot_hash",
            )
            == expected_signed["signed_snapshot_hash"]
        )
        snapshot = claim["snapshot"]
        snapshot_id_hash = snapshot["snapshot_id_hash"]
        snapshot_sequence = snapshot["snapshot_sequence"]
        observed_at_unix_ms = snapshot["observed_at_unix_ms"]
        equity = snapshot["equity"]
        position_count = snapshot["position_count"]
        portfolio_gross_notional = snapshot[
            "portfolio_gross_notional"
        ]
    except (KeyError, TypeError, ValueError):
        pass

    local_signature_verified = (
        claim_exact
        and signed_exact
        and key_hash_matches
        and cryptographic_signature_verified
    )
    evidence = {
        "schema_version": SNAPSHOT_EVIDENCE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if local_signature_verified else "BLOCK",
        "decision": (
            "PREREGISTERED_SNAPSHOT_PROVIDER_KEY_SIGNATURE_OBSERVED_"
            "SOURCE_TRUTH_CONTINUITY_AND_FRESHNESS_UNVERIFIED"
            if local_signature_verified
            else "SIGNED_PORTFOLIO_SNAPSHOT_UNKNOWN_OR_INVALID"
        ),
        "source": {
            "provider_preregistration_hash": _safe_hash(provider_hash),
            "snapshot_claim_hash": _safe_hash(
                expected_snapshot_claim_hash
            ),
            "signed_snapshot_hash": _safe_hash(
                expected_signed_snapshot_hash
            ),
            "provider_public_key_spki_sha256": _safe_hash(key_hash),
            "snapshot_id_hash": _safe_hash(snapshot_id_hash),
        },
        "snapshot_summary": {
            "snapshot_sequence": snapshot_sequence,
            "observed_at_unix_ms": observed_at_unix_ms,
            "equity": equity,
            "position_count": position_count,
            "portfolio_gross_notional": portfolio_gross_notional,
        },
        "facts": {
            "snapshot_claim_exact": claim_exact,
            "signed_snapshot_document_exact": signed_exact,
            "key_hash_matches_preregistration": key_hash_matches,
            "cryptographic_signature_verified": (
                cryptographic_signature_verified
            ),
            "preregistered_provider_key_signature_verified": (
                local_signature_verified
            ),
            "provider_identity_verified": False,
            "provider_implementation_verified": False,
            "snapshot_source_truth_verified": False,
            "snapshot_sequence_continuity_verified": False,
            "snapshot_freshness_verified": False,
            "raw_positions_redacted": True,
            "raw_public_key_redacted": True,
            "raw_signature_redacted": True,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "limitations": [
            "SNAPSHOT_PROVIDER_IDENTITY_UNVERIFIED",
            "SNAPSHOT_PROVIDER_IMPLEMENTATION_UNVERIFIED",
            "SNAPSHOT_SOURCE_TRUTH_UNVERIFIED",
            "SNAPSHOT_SEQUENCE_CONTINUITY_UNVERIFIED",
            "SNAPSHOT_FRESHNESS_UNVERIFIED",
            "CURRENT_ACTIVATION_UNAUTHORIZED",
        ],
        "authority": _authority(),
    }
    return seal_strict_canonical_document(
        evidence, "snapshot_evidence_hash"
    )


def verify_signed_portfolio_snapshot_evidence_v1(
    evidence_document: Any,
    *args: Any,
    expected_snapshot_evidence_hash: Any,
    **kwargs: Any,
) -> bool:
    try:
        expected = evaluate_signed_portfolio_snapshot_v1(
            *args, **kwargs
        )
        return (
            evidence_document == expected
            and _require_hash(
                expected_snapshot_evidence_hash,
                "expected_snapshot_evidence_hash",
            )
            == expected["snapshot_evidence_hash"]
        )
    except (TypeError, SignedPortfolioSnapshotBudgetError):
        return False


def evaluate_strategy_correlation_cluster_effective_bet_budget_v5(
    snapshot_evidence_document: Any,
    signed_snapshot_document: Any,
    snapshot_claim_document: Any,
    provider_preregistration_document: Any,
    correlation_preregistration: Any,
    correlation_matrix: Any,
    complete_link_audit: Any,
    *,
    expected_snapshot_evidence_hash: Any,
    snapshot_evaluation_kwargs: Any,
    strata_registration: Any = None,
    strata_gate: Any = None,
    complete_link_gate: Any = None,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any = "LONG",
    max_cluster_gross_pct: Any = budget_v4.budget_v3.budget_v1.DEFAULT_MAX_CLUSTER_GROSS_PCT,
    risk_increasing: Any = True,
    positions_after: Any = None,
    risk_reduction_transition: Any = None,
) -> dict[str, Any]:
    snapshot_exact = False
    snapshot_signature_verified = False
    v4_exact = False
    v4_document: dict[str, Any] = {}
    blockers: list[str] = []
    if type(snapshot_evaluation_kwargs) is not dict:
        blockers.append("snapshot_evaluation_kwargs_invalid")
    else:
        try:
            kwargs = copy.deepcopy(snapshot_evaluation_kwargs)
            expected_snapshot_evidence = (
                evaluate_signed_portfolio_snapshot_v1(
                    signed_snapshot_document,
                    snapshot_claim_document,
                    provider_preregistration_document,
                    **kwargs,
                )
            )
            snapshot_hash = _require_hash(
                expected_snapshot_evidence_hash,
                "expected_snapshot_evidence_hash",
            )
            snapshot_exact = bool(
                snapshot_evidence_document == expected_snapshot_evidence
                and snapshot_hash
                == expected_snapshot_evidence["snapshot_evidence_hash"]
            )
            snapshot_signature_verified = bool(
                snapshot_exact
                and expected_snapshot_evidence["status"] == "PASS"
                and expected_snapshot_evidence["facts"][
                    "preregistered_provider_key_signature_verified"
                ]
                is True
            )
        except (KeyError, TypeError, ValueError):
            snapshot_exact = False
            snapshot_signature_verified = False
    if not snapshot_exact:
        blockers.append("signed_portfolio_snapshot_evidence_not_exact")
    elif not snapshot_signature_verified:
        blockers.append("snapshot_provider_key_signature_unverified")

    if snapshot_signature_verified:
        try:
            snapshot = snapshot_claim_document["snapshot"]
            v4_document = (
                budget_v4.evaluate_strategy_correlation_cluster_effective_bet_budget_v4(
                    correlation_preregistration,
                    correlation_matrix,
                    complete_link_audit,
                    strata_registration=strata_registration,
                    strata_gate=strata_gate,
                    complete_link_gate=complete_link_gate,
                    equity=snapshot["equity"],
                    positions=snapshot["positions"],
                    proposed_symbol=proposed_symbol,
                    proposed_notional=proposed_notional,
                    proposed_direction=proposed_direction,
                    max_cluster_gross_pct=max_cluster_gross_pct,
                    risk_increasing=risk_increasing,
                    positions_after=positions_after,
                    risk_reduction_transition=risk_reduction_transition,
                )
            )
            v4_receipt = (
                budget_v4.verify_strategy_correlation_cluster_effective_bet_budget_v4(
                    v4_document,
                    correlation_preregistration,
                    correlation_matrix,
                    complete_link_audit,
                    strata_registration=strata_registration,
                    strata_gate=strata_gate,
                    complete_link_gate=complete_link_gate,
                    equity=snapshot["equity"],
                    positions=snapshot["positions"],
                    proposed_symbol=proposed_symbol,
                    proposed_notional=proposed_notional,
                    proposed_direction=proposed_direction,
                    max_cluster_gross_pct=max_cluster_gross_pct,
                    risk_increasing=risk_increasing,
                    positions_after=positions_after,
                    risk_reduction_transition=risk_reduction_transition,
                )
            )
            v4_exact = bool(
                v4_receipt.get("status") == "PASS"
                and type(v4_document.get("budget_v4_hash")) is str
            )
        except (KeyError, TypeError, ValueError):
            v4_exact = False
    if not v4_exact:
        blockers.append("effective_budget_v4_not_exact")
    elif v4_document.get("status") != "PASS":
        blockers.append("effective_budget_v4_decision_blocked")

    blockers = sorted(set(blockers))
    status = "PASS" if not blockers else "BLOCK"
    snapshot_summary = (
        snapshot_evidence_document.get("snapshot_summary", {})
        if type(snapshot_evidence_document) is dict
        else {}
    )
    return seal_strict_canonical_document(
        {
            "schema_version": BUDGET_SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": status,
            "decision": (
                "PASS_SIGNED_PORTFOLIO_SNAPSHOT_BOUND_EFFECTIVE_BUDGET_"
                "SOURCE_TRUTH_CONTINUITY_AND_FRESHNESS_UNVERIFIED"
                if status == "PASS"
                else "BLOCK"
            ),
            "admission_status": "BLOCKED",
            "source": {
                "provider_preregistration_hash": _safe_hash(
                    provider_preregistration_document.get(
                        "provider_preregistration_hash"
                    )
                    if type(provider_preregistration_document) is dict
                    else None
                ),
                "snapshot_claim_hash": _safe_hash(
                    snapshot_claim_document.get("snapshot_claim_hash")
                    if type(snapshot_claim_document) is dict
                    else None
                ),
                "signed_snapshot_hash": _safe_hash(
                    signed_snapshot_document.get("signed_snapshot_hash")
                    if type(signed_snapshot_document) is dict
                    else None
                ),
                "snapshot_evidence_hash": _safe_hash(
                    expected_snapshot_evidence_hash
                ),
                "v4_budget_hash": _safe_hash(
                    v4_document.get("budget_v4_hash")
                ),
                "v4_implementation_sha256": V4_IMPLEMENTATION_SHA256,
                "precomputed_predecessor_result_accepted": False,
            },
            "snapshot_summary": {
                "snapshot_id_hash": _safe_hash(
                    snapshot_evidence_document.get("source", {}).get(
                        "snapshot_id_hash"
                    )
                    if type(snapshot_evidence_document) is dict
                    and type(snapshot_evidence_document.get("source")) is dict
                    else None
                ),
                "snapshot_sequence": snapshot_summary.get(
                    "snapshot_sequence"
                ),
                "observed_at_unix_ms": snapshot_summary.get(
                    "observed_at_unix_ms"
                ),
                "equity": snapshot_summary.get("equity"),
                "position_count": snapshot_summary.get("position_count"),
                "portfolio_gross_notional": snapshot_summary.get(
                    "portfolio_gross_notional"
                ),
            },
            "budget_summary": {
                "v4_status": v4_document.get("status"),
                "v4_decision": v4_document.get("decision"),
                "risk_increasing": v4_document.get("facts", {}).get(
                    "risk_increasing"
                )
                if type(v4_document.get("facts")) is dict
                else None,
                "verified_risk_reduction": v4_document.get(
                    "facts", {}
                ).get("risk_reduction_derived_from_position_transition")
                if type(v4_document.get("facts")) is dict
                else None,
            },
            "checks": {
                "snapshot_evidence_exact": snapshot_exact,
                "snapshot_provider_key_signature_verified": (
                    snapshot_signature_verified
                ),
                "v4_budget_exactly_rebuilt": v4_exact,
                "v4_budget_decision_pass": (
                    v4_document.get("status") == "PASS"
                ),
                "snapshot_inputs_used_exclusively": (
                    snapshot_signature_verified and v4_exact
                ),
            },
            "facts": {
                "signed_snapshot_bound_to_budget": status == "PASS",
                "caller_equity_input_accepted": False,
                "caller_positions_input_accepted": False,
                "raw_positions_embedded": False,
                "snapshot_provider_identity_verified": False,
                "snapshot_provider_implementation_verified": False,
                "snapshot_source_truth_verified": False,
                "snapshot_sequence_continuity_verified": False,
                "snapshot_freshness_verified": False,
                "execution_verified": False,
                "profitability_proven": False,
                "runtime_assets_accessed": False,
                "runtime_gate_integrated": False,
            },
            "limitations": [
                "SNAPSHOT_PROVIDER_IDENTITY_UNVERIFIED",
                "SNAPSHOT_PROVIDER_IMPLEMENTATION_UNVERIFIED",
                "SNAPSHOT_SOURCE_TRUTH_UNVERIFIED",
                "SNAPSHOT_SEQUENCE_CONTINUITY_UNVERIFIED",
                "SNAPSHOT_FRESHNESS_UNVERIFIED",
                "EXECUTION_UNVERIFIED",
                "CURRENT_ACTIVATION_UNAUTHORIZED",
            ],
            "blockers": blockers,
            "authority": _authority(),
        },
        "budget_v5_hash",
    )


def verify_strategy_correlation_cluster_effective_bet_budget_v5(
    document: Any,
    *args: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    try:
        expected = (
            evaluate_strategy_correlation_cluster_effective_bet_budget_v5(
                *args, **kwargs
            )
        )
        exact = strict_json_contract_equal(document, expected)
    except (KeyError, TypeError, ValueError):
        exact = False
        expected = None
    return {
        "schema_version": BUDGET_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "budget_decision": expected["decision"] if exact else "UNKNOWN",
        "budget_v5_hash": expected["budget_v5_hash"] if exact else None,
        "runtime_gate_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "writer_allowed": False,
    }


__all__ = [
    "BUDGET_SCHEMA_VERSION",
    "BUDGET_VERIFICATION_SCHEMA_VERSION",
    "PROVIDER_PREREGISTRATION_SCHEMA_VERSION",
    "SIGNED_SNAPSHOT_SCHEMA_VERSION",
    "SNAPSHOT_CLAIM_SCHEMA_VERSION",
    "SNAPSHOT_EVIDENCE_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "SignedPortfolioSnapshotBudgetError",
    "build_portfolio_snapshot_claim_v1",
    "build_portfolio_snapshot_provider_preregistration_v1",
    "build_signed_portfolio_snapshot_v1",
    "evaluate_signed_portfolio_snapshot_v1",
    "evaluate_strategy_correlation_cluster_effective_bet_budget_v5",
    "verify_portfolio_snapshot_claim_v1",
    "verify_portfolio_snapshot_provider_preregistration_v1",
    "verify_signed_portfolio_snapshot_evidence_v1",
    "verify_strategy_correlation_cluster_effective_bet_budget_v5",
]
