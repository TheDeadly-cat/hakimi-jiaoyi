from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
import re
from typing import Any
import unicodedata

from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_proposal_preflight_v1
    as legacy_preflight,
)


REGISTRY_SCHEMA_VERSION = (
    "strategy-correlation-instrument-identity-preregistration-v1"
)
SCHEMA_VERSION = (
    "strategy-correlation-history-covered-budget-universe-proposal-"
    "instrument-identity-binding-candidate-v2"
)
STATIC_FINGERPRINT = (
    "20260825-strategy-correlation-proposal-instrument-identity-binding-"
    "candidate-v2-synthetic-unmounted-permission-lock-1"
)
CONSUMER_STATUS = "UNMOUNTED_APPLICATION_PREFLIGHT_IDENTITY_BINDING_CANDIDATE"
REGISTRY_STATUS = "SYNTHETIC_PREREGISTERED_UNMOUNTED"
UNKNOWN_STATUS = "UNKNOWN_INSTRUMENT_IDENTITY_NOT_PREREGISTERED"

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_SYMBOL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,63}$")
_VENUE_RE = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,31}$")
_IDENTITY_RE = re.compile(r"^[A-Z0-9][A-Z0-9._:/-]{0,127}$")
_ENTRY_KEYS = {
    "alias_symbol",
    "budget_symbol",
    "canonical_instrument_id",
    "venue_id",
}
_SEALED_ENTRY_KEYS = _ENTRY_KEYS | {"alias_lookup_key"}


def _canonical_bytes(value: Any) -> bytes | None:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError):
        return None


def _digest(value: Any) -> str | None:
    encoded = _canonical_bytes(value)
    return hashlib.sha256(encoded).hexdigest() if encoded is not None else None


def _text_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _seal(core: Mapping[str, Any], hash_field: str) -> dict[str, Any] | None:
    payload = dict(core)
    digest = _digest(payload)
    if digest is None:
        return None
    payload[hash_field] = digest
    return payload


def _is_hash(value: Any) -> bool:
    return isinstance(value, str) and _HEX64_RE.fullmatch(value) is not None


def _normalized_alias_key(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = unicodedata.normalize("NFKC", value).strip()
    if _SYMBOL_RE.fullmatch(normalized) is None:
        return None
    return normalized.casefold()


def _normalized_venue(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = unicodedata.normalize("NFKC", value).strip().upper()
    return normalized if _VENUE_RE.fullmatch(normalized) is not None else None


def _authority_lock() -> dict[str, bool]:
    return {
        "consumer_registration_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "effective_budget_activation_allowed": False,
        "http_registration_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
        "proposal_admission_allowed": False,
        "readonly_projection_adapter_activation_allowed": False,
        "runtime_activation_allowed": False,
        "writer_allowed": False,
        "research_evidence_only": True,
    }


def build_strategy_correlation_instrument_identity_preregistration_v1(
    entries: Any,
) -> dict[str, Any] | None:
    if not isinstance(entries, list) or not entries:
        return None

    normalized_entries: list[dict[str, str]] = []
    alias_targets: dict[tuple[str, str], tuple[str, str]] = {}
    canonical_to_budget: dict[str, str] = {}
    budget_to_canonical: dict[str, str] = {}

    for raw_entry in entries:
        if not isinstance(raw_entry, Mapping) or set(raw_entry.keys()) != _ENTRY_KEYS:
            return None
        alias_symbol = raw_entry.get("alias_symbol")
        budget_symbol = raw_entry.get("budget_symbol")
        canonical_instrument_id = raw_entry.get("canonical_instrument_id")
        venue_id = raw_entry.get("venue_id")
        if not all(
            isinstance(value, str)
            for value in (
                alias_symbol,
                budget_symbol,
                canonical_instrument_id,
                venue_id,
            )
        ):
            return None

        alias_text = unicodedata.normalize("NFKC", alias_symbol).strip()
        alias_lookup_key = _normalized_alias_key(alias_symbol)
        normalized_venue = _normalized_venue(venue_id)
        if (
            alias_text != alias_symbol
            or alias_lookup_key is None
            or normalized_venue != venue_id
            or unicodedata.normalize("NFKC", budget_symbol) != budget_symbol
            or _SYMBOL_RE.fullmatch(budget_symbol) is None
            or unicodedata.normalize("NFKC", canonical_instrument_id)
            != canonical_instrument_id
            or canonical_instrument_id.upper() != canonical_instrument_id
            or _IDENTITY_RE.fullmatch(canonical_instrument_id) is None
        ):
            return None

        alias_key = (venue_id, alias_lookup_key)
        target = (budget_symbol, canonical_instrument_id)
        if alias_key in alias_targets:
            return None
        alias_targets[alias_key] = target

        existing_budget = canonical_to_budget.get(canonical_instrument_id)
        if existing_budget is not None and existing_budget != budget_symbol:
            return None
        canonical_to_budget[canonical_instrument_id] = budget_symbol

        existing_identity = budget_to_canonical.get(budget_symbol)
        if existing_identity is not None and existing_identity != canonical_instrument_id:
            return None
        budget_to_canonical[budget_symbol] = canonical_instrument_id

        normalized_entries.append({
            "alias_lookup_key": alias_lookup_key,
            "alias_symbol": alias_symbol,
            "budget_symbol": budget_symbol,
            "canonical_instrument_id": canonical_instrument_id,
            "venue_id": venue_id,
        })

    normalized_entries.sort(
        key=lambda entry: (
            entry["venue_id"],
            entry["alias_lookup_key"],
            entry["budget_symbol"],
            entry["canonical_instrument_id"],
        )
    )
    core = {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "consumer_status": CONSUMER_STATUS,
        "registered": False,
        "status": REGISTRY_STATUS,
        "identity_namespace": "SYNTHETIC_RESEARCH_ONLY",
        "entries": normalized_entries,
        "facts": {
            "alias_count": len(normalized_entries),
            "budget_symbol_count": len(budget_to_canonical),
            "canonical_instrument_count": len(canonical_to_budget),
            "canonical_instrument_to_budget_symbol_one_to_one": True,
            "collisions_allowed": False,
            "nfkc_casefold_alias_lookup": True,
            "synthetic_only": True,
            "venue_qualified": True,
        },
        "authority": _authority_lock(),
    }
    return _seal(core, "identity_preregistration_hash")


def verify_strategy_correlation_instrument_identity_preregistration_v1(
    document: Any,
    *,
    expected_identity_preregistration_hash: Any,
) -> bool:
    if not _is_hash(expected_identity_preregistration_hash):
        return False
    if not isinstance(document, Mapping):
        return False
    sealed_entries = document.get("entries")
    if not isinstance(sealed_entries, list):
        return False
    source_entries: list[dict[str, Any]] = []
    for sealed_entry in sealed_entries:
        if (
            not isinstance(sealed_entry, Mapping)
            or set(sealed_entry.keys()) != _SEALED_ENTRY_KEYS
        ):
            return False
        source_entries.append({
            "alias_symbol": sealed_entry.get("alias_symbol"),
            "budget_symbol": sealed_entry.get("budget_symbol"),
            "canonical_instrument_id": sealed_entry.get(
                "canonical_instrument_id"
            ),
            "venue_id": sealed_entry.get("venue_id"),
        })
    rebuilt = build_strategy_correlation_instrument_identity_preregistration_v1(
        source_entries
    )
    return (
        rebuilt is not None
        and rebuilt.get("identity_preregistration_hash")
        == expected_identity_preregistration_hash
        and document.get("identity_preregistration_hash")
        == expected_identity_preregistration_hash
        and dict(document) == rebuilt
    )


def _resolve_identity(
    registry: Mapping[str, Any],
    *,
    venue_id: str,
    alias_lookup_key: str,
) -> Mapping[str, Any] | None:
    entries = registry.get("entries")
    if not isinstance(entries, list):
        return None
    matches = [
        entry
        for entry in entries
        if isinstance(entry, Mapping)
        and entry.get("venue_id") == venue_id
        and entry.get("alias_lookup_key") == alias_lookup_key
    ]
    return matches[0] if len(matches) == 1 else None


def _deduplicated_blockers(values: list[Any]) -> list[str]:
    blockers: list[str] = []
    for value in values:
        if isinstance(value, str) and value not in blockers:
            blockers.append(value)
    return blockers


def evaluate_strategy_correlation_history_covered_budget_universe_proposal_instrument_identity_binding_candidate_v2(
    identity_preregistration: Any,
    projection_preregistration: Any,
    proposed_venue: Any,
    proposed_symbol: Any,
    *,
    expected_identity_preregistration_hash: Any,
    expected_projection_preregistration_hash: Any,
    projection_verification_context: Any,
) -> dict[str, Any] | None:
    alias_lookup_key = _normalized_alias_key(proposed_symbol)
    venue_id = _normalized_venue(proposed_venue)
    if (
        alias_lookup_key is None
        or venue_id is None
        or not isinstance(proposed_symbol, str)
        or not _is_hash(expected_projection_preregistration_hash)
        or not verify_strategy_correlation_instrument_identity_preregistration_v1(
            identity_preregistration,
            expected_identity_preregistration_hash=(
                expected_identity_preregistration_hash
            ),
        )
    ):
        return None

    entries = identity_preregistration.get("entries")
    if not isinstance(entries, list) or not entries:
        return None
    projection_probe = legacy_preflight.evaluate_strategy_correlation_history_covered_budget_universe_proposal_preflight_v1(
        projection_preregistration,
        entries[0].get("budget_symbol") if isinstance(entries[0], Mapping) else None,
        expected_projection_preregistration_hash=(
            expected_projection_preregistration_hash
        ),
        projection_verification_context=projection_verification_context,
    )
    if projection_probe is None:
        return None

    raw_symbol_hash = _text_digest(proposed_symbol)
    venue_hash = _text_digest(venue_id)
    alias_lookup_hash = _text_digest(alias_lookup_key)
    identity_entry = _resolve_identity(
        identity_preregistration,
        venue_id=venue_id,
        alias_lookup_key=alias_lookup_key,
    )

    if identity_entry is None:
        core = {
            "schema_version": SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "consumer_status": CONSUMER_STATUS,
            "registered": False,
            "status": UNKNOWN_STATUS,
            "reason_code": "VENUE_QUALIFIED_ALIAS_NOT_PREREGISTERED",
            "proposal": {
                "input_symbol_sha256": raw_symbol_hash,
                "normalized_alias_lookup_key_sha256": alias_lookup_hash,
                "venue_id_sha256": venue_hash,
                "canonical_instrument_id_sha256": None,
                "budget_symbol_sha256": None,
                "identity_entry_hash": None,
                "source_cluster_id_sha256": None,
                "source_cluster_members_hash": None,
            },
            "sources": {
                "identity_preregistration_hash": (
                    expected_identity_preregistration_hash
                ),
                "projection_preregistration_hash": (
                    expected_projection_preregistration_hash
                ),
                "projection_contract_probe_hash": projection_probe.get(
                    "preflight_hash"
                ),
                "legacy_preflight_hash": None,
            },
            "decision_path": {
                "source": "IDENTITY_REGISTRY_AND_PROJECTION_EXACTLY_VERIFIED",
                "gap": "VENUE_QUALIFIED_ALIAS_IDENTITY_NOT_PREREGISTERED",
                "maturity": "UNVERIFIED_INSTRUMENT_IDENTITY",
                "permission": "NOT_AUTHORIZED",
            },
            "facts": {
                "alias_preregistered": False,
                "canonical_budget_symbol_routed": False,
                "canonical_instrument_identity_bound": False,
                "projection_exactly_verified": True,
                "proposal_admission_allowed": False,
                "raw_identifiers_redacted": True,
                "synthetic_only": True,
            },
            "blockers": [
                "INSTRUMENT_IDENTITY_NOT_PREREGISTERED",
                "CANONICAL_BUDGET_CLUSTER_BINDING_UNAVAILABLE",
                "PROPOSAL_ADMISSION_NOT_ALLOWED",
                "IDENTITY_BINDING_CANDIDATE_UNMOUNTED",
                "PAPER_LIVE_UNAUTHORIZED",
            ],
            "authority": _authority_lock(),
        }
        return _seal(core, "identity_binding_hash")

    budget_symbol = identity_entry.get("budget_symbol")
    canonical_instrument_id = identity_entry.get("canonical_instrument_id")
    if not isinstance(budget_symbol, str) or not isinstance(
        canonical_instrument_id, str
    ):
        return None
    legacy = legacy_preflight.evaluate_strategy_correlation_history_covered_budget_universe_proposal_preflight_v1(
        projection_preregistration,
        budget_symbol,
        expected_projection_preregistration_hash=(
            expected_projection_preregistration_hash
        ),
        projection_verification_context=projection_verification_context,
    )
    if legacy is None:
        return None
    legacy_proposal = legacy.get("proposal")
    legacy_decision = legacy.get("decision_path")
    legacy_facts = legacy.get("facts")
    legacy_blockers = legacy.get("blockers")
    if not all(
        isinstance(value, Mapping)
        for value in (legacy_proposal, legacy_decision, legacy_facts)
    ) or not isinstance(legacy_blockers, list):
        return None

    core = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "consumer_status": CONSUMER_STATUS,
        "registered": False,
        "status": legacy.get("status"),
        "reason_code": "INSTRUMENT_IDENTITY_BOUND_TO_VERIFIED_BUDGET_SYMBOL",
        "legacy_reason_code": legacy.get("reason_code"),
        "proposal": {
            "input_symbol_sha256": raw_symbol_hash,
            "normalized_alias_lookup_key_sha256": alias_lookup_hash,
            "venue_id_sha256": venue_hash,
            "canonical_instrument_id_sha256": _text_digest(
                canonical_instrument_id
            ),
            "budget_symbol_sha256": _text_digest(budget_symbol),
            "identity_entry_hash": _digest(dict(identity_entry)),
            "source_cluster_id_sha256": legacy_proposal.get(
                "source_cluster_id_sha256"
            ),
            "source_cluster_members_hash": legacy_proposal.get(
                "source_cluster_members_hash"
            ),
        },
        "sources": {
            "identity_preregistration_hash": expected_identity_preregistration_hash,
            "projection_preregistration_hash": (
                expected_projection_preregistration_hash
            ),
            "projection_contract_probe_hash": projection_probe.get(
                "preflight_hash"
            ),
            "legacy_preflight_hash": legacy.get("preflight_hash"),
        },
        "decision_path": {
            "source": "IDENTITY_REGISTRY_AND_PROJECTION_EXACTLY_VERIFIED",
            "gap": legacy_decision.get("gap"),
            "maturity": legacy_decision.get("maturity"),
            "permission": "NOT_AUTHORIZED",
        },
        "facts": {
            "alias_preregistered": True,
            "canonical_budget_symbol_routed": True,
            "canonical_instrument_identity_bound": True,
            "excluded_universe_member": legacy_facts.get(
                "excluded_universe_member"
            ),
            "legacy_preflight_exactly_rebuilt": True,
            "projected_universe_member": legacy_facts.get(
                "projected_universe_member"
            ),
            "projection_exactly_verified": True,
            "proposal_admission_allowed": False,
            "raw_identifiers_redacted": True,
            "source_cluster_bound": (
                legacy_proposal.get("source_cluster_members_hash") is not None
            ),
            "synthetic_only": True,
        },
        "blockers": _deduplicated_blockers(
            list(legacy_blockers)
            + [
                "IDENTITY_BINDING_CANDIDATE_UNMOUNTED",
                "PROPOSAL_ADMISSION_NOT_ALLOWED",
                "PAPER_LIVE_UNAUTHORIZED",
            ]
        ),
        "authority": _authority_lock(),
    }
    return _seal(core, "identity_binding_hash")


def verify_strategy_correlation_history_covered_budget_universe_proposal_instrument_identity_binding_candidate_v2(
    document: Any,
    identity_preregistration: Any,
    projection_preregistration: Any,
    proposed_venue: Any,
    proposed_symbol: Any,
    *,
    expected_identity_binding_hash: Any,
    expected_identity_preregistration_hash: Any,
    expected_projection_preregistration_hash: Any,
    projection_verification_context: Any,
) -> bool:
    if not _is_hash(expected_identity_binding_hash):
        return False
    expected = evaluate_strategy_correlation_history_covered_budget_universe_proposal_instrument_identity_binding_candidate_v2(
        identity_preregistration,
        projection_preregistration,
        proposed_venue,
        proposed_symbol,
        expected_identity_preregistration_hash=(
            expected_identity_preregistration_hash
        ),
        expected_projection_preregistration_hash=(
            expected_projection_preregistration_hash
        ),
        projection_verification_context=projection_verification_context,
    )
    return (
        isinstance(document, Mapping)
        and expected is not None
        and expected.get("identity_binding_hash") == expected_identity_binding_hash
        and document.get("identity_binding_hash") == expected_identity_binding_hash
        and dict(document) == expected
    )
