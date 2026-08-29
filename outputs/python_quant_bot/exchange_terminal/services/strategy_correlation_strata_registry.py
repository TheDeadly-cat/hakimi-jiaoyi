"""Candidate hierarchy registry asset and consumer-first binding assessment."""

from __future__ import annotations

from datetime import date, datetime
import re
from typing import Any

try:
    from services.strategy_correlation_preregistered_strata import (
        build_strategy_correlation_strata_preregistration,
        verify_strategy_correlation_strata_preregistration,
    )
    from services.strict_canonical_json_hash import strict_canonical_hash
    from services.strict_research_authority import (
        strict_research_authority_invalid,
    )
except ModuleNotFoundError:
    from exchange_terminal.services.strategy_correlation_preregistered_strata import (
        build_strategy_correlation_strata_preregistration,
        verify_strategy_correlation_strata_preregistration,
    )
    from exchange_terminal.services.strict_canonical_json_hash import (
        strict_canonical_hash,
    )
    from exchange_terminal.services.strict_research_authority import (
        strict_research_authority_invalid,
    )


REGISTRY_ASSET_SCHEMA = "strategy-correlation-strata-registry-asset-v1"
BINDING_ASSESSMENT_SCHEMA = (
    "strategy-correlation-strata-registry-binding-assessment-v1"
)
_HASH_PATTERN = re.compile(r"[0-9a-f]{64}")


def _verification(blockers: list[str]) -> dict[str, Any]:
    normalized = sorted(set(blockers))
    return {
        "status": "PASS" if not normalized else "BLOCK",
        "blockers": normalized,
    }


def _clean_identifier(value: Any, *, field: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(f"{field}_invalid")
    return value


def _clean_hash(value: Any, *, field: str) -> str:
    if type(value) is not str or _HASH_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field}_invalid")
    return value


def _clean_date(value: Any, *, field: str) -> date:
    if type(value) is not str:
        raise ValueError(f"{field}_invalid")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field}_invalid") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{field}_invalid")
    return parsed


def _clean_utc_timestamp(value: Any, *, field: str) -> datetime:
    if type(value) is not str:
        raise ValueError(f"{field}_invalid")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError(f"{field}_invalid") from exc
    return parsed


def _hash_without(document: dict[str, Any], hash_field: str) -> str:
    return strict_canonical_hash(
        {key: value for key, value in document.items() if key != hash_field}
    )


def build_strategy_correlation_strata_registry_asset(
    source_preregistration: Any,
    dimensions: Any,
    *,
    registry_id: Any,
    classification_source: Any,
    classification_source_version: Any,
    classification_source_hash: Any,
    effective_date: Any,
    frozen_at: Any,
) -> dict[str, Any]:
    normalized_registry_id = _clean_identifier(
        registry_id,
        field="registry_id",
    )
    normalized_source = _clean_identifier(
        classification_source,
        field="classification_source",
    )
    normalized_source_version = _clean_identifier(
        classification_source_version,
        field="classification_source_version",
    )
    normalized_source_hash = _clean_hash(
        classification_source_hash,
        field="classification_source_hash",
    )
    parsed_effective_date = _clean_date(
        effective_date,
        field="effective_date",
    )
    parsed_frozen_at = _clean_utc_timestamp(frozen_at, field="frozen_at")
    if parsed_effective_date > parsed_frozen_at.date():
        raise ValueError("registry_effective_date_after_freeze")
    registration = build_strategy_correlation_strata_preregistration(
        source_preregistration,
        dimensions,
    )
    document: dict[str, Any] = {
        "schema_version": REGISTRY_ASSET_SCHEMA,
        "status": "FROZEN_CANDIDATE",
        "registry_id": normalized_registry_id,
        "source_preregistration_hash": registration[
            "source_preregistration_hash"
        ],
        "dimensions": registration["dimensions"],
        "classification_source": {
            "name": normalized_source,
            "version": normalized_source_version,
            "content_hash": normalized_source_hash,
        },
        "effective_date": parsed_effective_date.isoformat(),
        "frozen_at": parsed_frozen_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "methodology": {
            "assignment_basis": "EXTERNAL_CLASSIFICATION_ONLY",
            "selection_returns_used": False,
            "post_selection_edits_allowed": False,
            "effective_before_selection_required": True,
        },
        "consumer_only": True,
        "writer_implemented": False,
        "formal_registry_activation_allowed": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": {
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    document["registry_asset_hash"] = _hash_without(
        document,
        "registry_asset_hash",
    )
    return document


def verify_strategy_correlation_strata_registry_asset(
    document: Any,
    *,
    source_preregistration: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        return _verification(["strata_registry_asset_contract_invalid"])
    if strict_research_authority_invalid(document):
        blockers.append("strata_registry_asset_authority_invalid")
    try:
        stored_hash = document.get("registry_asset_hash")
        if type(stored_hash) is not str or stored_hash != _hash_without(
            document,
            "registry_asset_hash",
        ):
            blockers.append("strata_registry_asset_hash_invalid")
    except (TypeError, ValueError):
        blockers.append("strata_registry_asset_hash_invalid")
    try:
        classification = document.get("classification_source")
        if type(classification) is not dict:
            raise ValueError("classification_source_invalid")
        expected = build_strategy_correlation_strata_registry_asset(
            source_preregistration,
            document.get("dimensions"),
            registry_id=document.get("registry_id"),
            classification_source=classification.get("name"),
            classification_source_version=classification.get("version"),
            classification_source_hash=classification.get("content_hash"),
            effective_date=document.get("effective_date"),
            frozen_at=document.get("frozen_at"),
        )
    except (MemoryError, RecursionError):
        raise
    except (KeyError, TypeError, ValueError):
        blockers.append("strata_registry_asset_rebuild_invalid")
    else:
        if document != expected:
            blockers.append("strata_registry_asset_exact_rebuild_mismatch")
    return _verification(blockers)


def assess_strategy_correlation_strata_registry_binding(
    registry_asset: Any,
    registration: Any,
    source_preregistration: Any,
    *,
    selection_cutoff_date: Any,
    expected_registry_asset_hash: Any,
    expected_classification_source_hash: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    registration_verified = False
    asset_verified = False
    asset_hash_bound = False
    source_hash_bound = False
    dimensions_bound = False
    classification_hash_bound = False
    effective_before_selection = False
    frozen_before_selection = False

    try:
        cutoff = _clean_date(
            selection_cutoff_date,
            field="selection_cutoff_date",
        )
    except ValueError:
        cutoff = None
        blockers.append("selection_cutoff_date_invalid")
    try:
        expected_asset_hash = _clean_hash(
            expected_registry_asset_hash,
            field="expected_registry_asset_hash",
        )
    except ValueError:
        expected_asset_hash = None
        blockers.append("expected_registry_asset_hash_invalid")
    try:
        expected_source_hash = _clean_hash(
            expected_classification_source_hash,
            field="expected_classification_source_hash",
        )
    except ValueError:
        expected_source_hash = None
        blockers.append("expected_classification_source_hash_invalid")

    registration_verification = (
        verify_strategy_correlation_strata_preregistration(
            registration,
            source_preregistration=source_preregistration,
        )
    )
    registration_verified = registration_verification.get("status") == "PASS"
    if not registration_verified:
        blockers.append("strata_registration_invalid")
    asset_verification = verify_strategy_correlation_strata_registry_asset(
        registry_asset,
        source_preregistration=source_preregistration,
    )
    asset_verified = asset_verification.get("status") == "PASS"
    if not asset_verified:
        blockers.append("strata_registry_asset_invalid")

    if type(registry_asset) is dict:
        asset_hash_bound = (
            expected_asset_hash is not None
            and registry_asset.get("registry_asset_hash")
            == expected_asset_hash
        )
        if not asset_hash_bound:
            blockers.append("registry_asset_hash_binding_invalid")
        classification = registry_asset.get("classification_source")
        classification_hash_bound = (
            type(classification) is dict
            and expected_source_hash is not None
            and classification.get("content_hash") == expected_source_hash
        )
        if not classification_hash_bound:
            blockers.append("classification_source_hash_binding_invalid")
        if type(registration) is dict:
            source_hash_bound = (
                registry_asset.get("source_preregistration_hash")
                == registration.get("source_preregistration_hash")
            )
            dimensions_bound = (
                registry_asset.get("dimensions")
                == registration.get("dimensions")
            )
        if not source_hash_bound:
            blockers.append("source_preregistration_binding_invalid")
        if not dimensions_bound:
            blockers.append("strata_dimensions_binding_invalid")
        if cutoff is not None:
            try:
                effective = _clean_date(
                    registry_asset.get("effective_date"),
                    field="effective_date",
                )
                frozen = _clean_utc_timestamp(
                    registry_asset.get("frozen_at"),
                    field="frozen_at",
                )
            except ValueError:
                blockers.append("registry_timing_invalid")
            else:
                effective_before_selection = effective < cutoff
                frozen_before_selection = frozen.date() < cutoff
                if not effective_before_selection:
                    blockers.append(
                        "registry_effective_date_not_before_selection"
                    )
                if not frozen_before_selection:
                    blockers.append("registry_not_frozen_before_selection")
    else:
        blockers.extend(
            [
                "registry_asset_hash_binding_invalid",
                "classification_source_hash_binding_invalid",
                "source_preregistration_binding_invalid",
                "strata_dimensions_binding_invalid",
            ]
        )

    blockers = sorted(set(blockers))
    status = "BOUND" if not blockers else "BLOCK"
    document: dict[str, Any] = {
        "schema_version": BINDING_ASSESSMENT_SCHEMA,
        "status": status,
        "blockers": blockers,
        "registry_id": (
            registry_asset.get("registry_id")
            if type(registry_asset) is dict
            and type(registry_asset.get("registry_id")) is str
            else None
        ),
        "selection_cutoff_date": (
            cutoff.isoformat() if cutoff is not None else None
        ),
        "facts": {
            "registration_independently_verified": registration_verified,
            "registry_asset_independently_verified": asset_verified,
            "registry_asset_hash_bound": asset_hash_bound,
            "classification_source_hash_bound": classification_hash_bound,
            "source_preregistration_bound": source_hash_bound,
            "strata_dimensions_bound": dimensions_bound,
            "effective_before_selection": effective_before_selection,
            "frozen_before_selection": frozen_before_selection,
        },
        "consumer_only": True,
        "writer_implemented": False,
        "formal_registry_activation_allowed": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": {
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    document["assessment_hash"] = _hash_without(
        document,
        "assessment_hash",
    )
    return document


def verify_strategy_correlation_strata_registry_binding(
    document: Any,
    *,
    registry_asset: Any,
    registration: Any,
    source_preregistration: Any,
    selection_cutoff_date: Any,
    expected_registry_asset_hash: Any,
    expected_classification_source_hash: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        return _verification(["strata_registry_binding_contract_invalid"])
    if strict_research_authority_invalid(document):
        blockers.append("strata_registry_binding_authority_invalid")
    try:
        stored_hash = document.get("assessment_hash")
        if type(stored_hash) is not str or stored_hash != _hash_without(
            document,
            "assessment_hash",
        ):
            blockers.append("strata_registry_binding_hash_invalid")
    except (TypeError, ValueError):
        blockers.append("strata_registry_binding_hash_invalid")
    expected = assess_strategy_correlation_strata_registry_binding(
        registry_asset,
        registration,
        source_preregistration,
        selection_cutoff_date=selection_cutoff_date,
        expected_registry_asset_hash=expected_registry_asset_hash,
        expected_classification_source_hash=(
            expected_classification_source_hash
        ),
    )
    if document != expected:
        blockers.append("strata_registry_binding_exact_rebuild_mismatch")
    return _verification(blockers)
