"""Reusable fail-closed registration for isolated presentation assets."""

from __future__ import annotations

import math
import re
from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = "static-presentation-asset-registration-v1"
STATIC_FINGERPRINT = (
    "20260823-static-presentation-asset-registration-v1-unbound-lock-1"
)
STATUS = "BLOCKED"
PORTFOLIO_CORRELATION_ADMISSION_RAIL_REGISTRATION_ID = (
    "portfolio-correlation-admission-rail-v1"
)

_STAGE_ORDER = ["SOURCE", "GAP", "MATURITY", "PERMISSION"]
_ALLOWED_ASSET_ROLES = {
    "decision",
    "presentation",
    "production",
    "production_dependency",
    "verification",
}
_BLOCKED_PATH_SEGMENTS = {
    ".env",
    "cache",
    "caches",
    "database",
    "db",
    "logs",
    "runtime",
    "secrets",
}
_AUTHORITY_KEYS = (
    "app_import_allowed",
    "browser_execution_allowed",
    "current_admission_allowed",
    "html_script_binding_allowed",
    "live_order_allowed",
    "paper_authorized",
    "route_registration_allowed",
    "runtime_asset_loading_allowed",
    "stylesheet_link_binding_allowed",
    "ui_mount_allowed",
    "writer_allowed",
)
_HOST_PLAN_KEYS = (
    "app_importer",
    "browser_review_receipt",
    "html_script",
    "mount_slot",
    "route",
    "stylesheet_link",
)
_TOP_LEVEL_SPEC_KEYS = {
    "assets",
    "consumer_contract",
    "host_plan",
    "registration_id",
    "source_contract",
}
_SOURCE_CONTRACT_KEYS = {
    "adr_path",
    "adr_sha256",
    "implementation_path",
    "implementation_sha256",
    "schema_version",
    "test_path",
    "test_sha256",
}
_CONSUMER_CONTRACT_KEYS = {
    "adr_asset_id",
    "browser_global",
    "expected_commonjs_exports",
    "javascript_asset_id",
    "neutral_status_labels",
    "protected_stylesheet_path",
    "protected_stylesheet_sha256",
    "raw_source_evidence_embedded",
    "ready_word_allowed",
    "schema_version",
    "script_load_order",
    "stage_order",
    "static_fingerprint",
    "stylesheet_asset_id",
    "test_asset_id",
    "tier_order",
}
_ASSET_KEYS = {"asset_id", "path", "role", "sha256"}


def _plain_json_snapshot(value: Any, active: set[int] | None = None) -> Any:
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("non-finite values are not permitted")
        return value
    if type(value) not in {dict, list}:
        raise TypeError("registration specs require native JSON values")

    active = set() if active is None else active
    marker = id(value)
    if marker in active:
        raise ValueError("cyclic registration specs are not permitted")
    active.add(marker)
    try:
        if type(value) is list:
            return [_plain_json_snapshot(item, active) for item in value]
        result: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError("registration spec keys must be strings")
            result[key] = _plain_json_snapshot(item, active)
        return result
    finally:
        active.remove(marker)


def _exact_keys(value: Any, expected: set[str]) -> bool:
    return type(value) is dict and set(value) == expected


def _is_hash(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _clean_identifier(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", value)
    ):
        raise ValueError(f"{label} must be a stable identifier")
    return value


def _clean_stable_token(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", value)
    ):
        raise ValueError(f"{label} must be a stable token")
    return value


def _safe_relative_path(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or "\\" in value
        or value.startswith("/")
        or ":" in value
    ):
        raise ValueError(f"{label} must be a safe relative source path")
    parts = value.split("/")
    if (
        parts[0] not in {"docs", "exchange_terminal", "tests"}
        or any(
            not part
            or part in {".", ".."}
            or part.casefold() in _BLOCKED_PATH_SEGMENTS
            for part in parts
        )
    ):
        raise ValueError(f"{label} leaves the explicit source boundary")
    return value


def _clean_hash(value: Any, label: str) -> str:
    if not _is_hash(value):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _clean_string_list(value: Any, label: str) -> list[str]:
    if type(value) is not list or not value:
        raise ValueError(f"{label} must be a non-empty list")
    cleaned = [_clean_identifier(item, label) for item in value]
    if len(set(cleaned)) != len(cleaned):
        raise ValueError(f"{label} must not contain duplicates")
    return cleaned


def _validate_source_contract(value: Any) -> dict[str, Any]:
    if not _exact_keys(value, _SOURCE_CONTRACT_KEYS):
        raise ValueError("source contract keys are not exact")
    result = dict(value)
    result["schema_version"] = _clean_identifier(
        result["schema_version"],
        "source schema version",
    )
    for path_key, hash_key, suffix in (
        ("implementation_path", "implementation_sha256", ".py"),
        ("test_path", "test_sha256", ".py"),
        ("adr_path", "adr_sha256", ".md"),
    ):
        result[path_key] = _safe_relative_path(result[path_key], path_key)
        if not result[path_key].endswith(suffix):
            raise ValueError(f"{path_key} has an unexpected file type")
        result[hash_key] = _clean_hash(result[hash_key], hash_key)
    return result


def _validate_assets(value: Any) -> list[dict[str, str]]:
    if type(value) is not list or len(value) < 4:
        raise ValueError("at least four presentation assets are required")
    rows: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for item in value:
        if not _exact_keys(item, _ASSET_KEYS):
            raise ValueError("asset row keys are not exact")
        asset_id = _clean_identifier(item["asset_id"], "asset_id")
        path = _safe_relative_path(item["path"], "asset path")
        role = item["role"]
        digest = _clean_hash(item["sha256"], "asset sha256")
        if type(role) is not str or role not in _ALLOWED_ASSET_ROLES:
            raise ValueError("asset role is not allowed")
        if asset_id in seen_ids or path in seen_paths:
            raise ValueError("asset ids and paths must be unique")
        seen_ids.add(asset_id)
        seen_paths.add(path)
        rows.append({
            "asset_id": asset_id,
            "path": path,
            "role": role,
            "sha256": digest,
        })
    return sorted(rows, key=lambda row: row["asset_id"])


def _validate_consumer_contract(
    value: Any,
    assets: list[dict[str, str]],
) -> dict[str, Any]:
    if not _exact_keys(value, _CONSUMER_CONTRACT_KEYS):
        raise ValueError("consumer contract keys are not exact")
    result = dict(value)
    result["schema_version"] = _clean_identifier(
        result["schema_version"],
        "consumer schema version",
    )
    result["static_fingerprint"] = _clean_stable_token(
        result["static_fingerprint"],
        "consumer static fingerprint",
    )
    if (
        type(result["browser_global"]) is not str
        or not re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", result["browser_global"])
    ):
        raise ValueError("browser global is not a JavaScript identifier")
    result["expected_commonjs_exports"] = _clean_string_list(
        result["expected_commonjs_exports"],
        "CommonJS exports",
    )
    result["script_load_order"] = _clean_string_list(
        result["script_load_order"],
        "script load order",
    )
    if result["stage_order"] != _STAGE_ORDER:
        raise ValueError("stage order must remain SOURCE GAP MATURITY PERMISSION")
    result["stage_order"] = list(_STAGE_ORDER)
    result["tier_order"] = _clean_string_list(result["tier_order"], "tier order")
    if (
        not _exact_keys(
            result["neutral_status_labels"],
            {"block", "pass", "unknown"},
        )
        or any(
            type(label) is not str
            or not label
            or "READY" in label.upper()
            for label in result["neutral_status_labels"].values()
        )
    ):
        raise ValueError("neutral status labels are not exact")
    if result["ready_word_allowed"] is not False:
        raise ValueError("READY wording must remain disallowed")
    if result["raw_source_evidence_embedded"] is not False:
        raise ValueError("raw source evidence must remain excluded")
    result["protected_stylesheet_path"] = _safe_relative_path(
        result["protected_stylesheet_path"],
        "protected stylesheet path",
    )
    result["protected_stylesheet_sha256"] = _clean_hash(
        result["protected_stylesheet_sha256"],
        "protected stylesheet sha256",
    )

    assets_by_id = {row["asset_id"]: row for row in assets}
    for reference_key in (
        "adr_asset_id",
        "javascript_asset_id",
        "stylesheet_asset_id",
        "test_asset_id",
    ):
        asset_id = _clean_identifier(result[reference_key], reference_key)
        if asset_id not in assets_by_id:
            raise ValueError(f"{reference_key} does not reference a pinned asset")
    if any(asset_id not in assets_by_id for asset_id in result["script_load_order"]):
        raise ValueError("script load order references an unknown asset")
    if result["javascript_asset_id"] not in result["script_load_order"]:
        raise ValueError("script load order omits the presentation JavaScript")
    if not assets_by_id[result["javascript_asset_id"]]["path"].endswith(".js"):
        raise ValueError("presentation JavaScript asset has the wrong file type")
    if not assets_by_id[result["stylesheet_asset_id"]]["path"].endswith(".css"):
        raise ValueError("presentation stylesheet asset has the wrong file type")
    if not assets_by_id[result["test_asset_id"]]["path"].endswith(".test.js"):
        raise ValueError("presentation test asset has the wrong file type")
    if not assets_by_id[result["adr_asset_id"]]["path"].endswith(".md"):
        raise ValueError("presentation ADR asset has the wrong file type")
    return result


def _normalize_spec(spec: Any) -> dict[str, Any]:
    snapshot = _plain_json_snapshot(spec)
    if not _exact_keys(snapshot, _TOP_LEVEL_SPEC_KEYS):
        raise ValueError("registration spec keys are not exact")
    registration_id = _clean_identifier(
        snapshot["registration_id"],
        "registration_id",
    )
    assets = _validate_assets(snapshot["assets"])
    source_contract = _validate_source_contract(snapshot["source_contract"])
    consumer_contract = _validate_consumer_contract(
        snapshot["consumer_contract"],
        assets,
    )
    host_plan = snapshot["host_plan"]
    if (
        not _exact_keys(host_plan, set(_HOST_PLAN_KEYS))
        or any(host_plan[key] is not None for key in _HOST_PLAN_KEYS)
    ):
        raise ValueError("host plan must remain exact and fully unbound")
    return {
        "registration_id": registration_id,
        "source_contract": source_contract,
        "consumer_contract": consumer_contract,
        "assets": assets,
        "host_plan": {key: None for key in _HOST_PLAN_KEYS},
    }


def _locked_authority() -> dict[str, bool]:
    return {key: False for key in _AUTHORITY_KEYS}


def build_static_presentation_asset_registration_v1(spec: Any) -> dict[str, Any]:
    normalized = _normalize_spec(spec)
    assets = normalized["assets"]
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "registration_id": normalized["registration_id"],
        "status": STATUS,
        "registration_state": "STATIC_PRESENTATION_ASSETS_REGISTERED_UNBOUND",
        "decision": (
            "STATIC_PRESENTATION_ASSETS_PINNED_HOST_BROWSER_ROUTE_MOUNT_"
            "CURRENT_AND_EXECUTION_UNBOUND"
        ),
        "spec_hash": strict_canonical_hash(normalized),
        "asset_manifest_hash": strict_canonical_hash(assets),
        "source_contract": normalized["source_contract"],
        "consumer_contract": normalized["consumer_contract"],
        "asset_manifest": assets,
        "host_plan": normalized["host_plan"],
        "activation_order": [
            "SOURCE_CONTRACT_PINNING",
            "STATIC_ASSET_PINNING",
            "CROSS_RUNTIME_DELIVERY_REGISTRATION",
            "APP_IMPORT_PREREGISTRATION",
            "HTML_SCRIPT_AND_STYLESHEET_PREREGISTRATION",
            "UNMOUNTED_RENDER_DESCRIPTOR_REVIEW",
            "BROWSER_VISUAL_REVIEW",
            "ROUTE_AND_MOUNT_BINDING",
            "CURRENT_AND_RUNTIME_ACTIVATION",
        ],
        "blockers": [
            "CROSS_RUNTIME_DELIVERY_UNREGISTERED",
            "APP_IMPORTER_UNBOUND",
            "HTML_SCRIPT_UNBOUND",
            "STYLESHEET_LINK_UNBOUND",
            "RENDER_DESCRIPTOR_UNREVIEWED",
            "BROWSER_VISUAL_REVIEW_NOT_PERFORMED",
            "ROUTE_UNBOUND",
            "MOUNT_SLOT_UNBOUND",
            "CURRENT_ADMISSION_LOCKED",
        ],
        "facts": {
            "source_contract_pinned": True,
            "asset_manifest_pinned": True,
            "commonjs_exports_pinned": True,
            "browser_global_pinned": True,
            "script_load_order_pinned": True,
            "neutral_stage_order_pinned": True,
            "tier_order_pinned": True,
            "isolated_stylesheet_registered": True,
            "protected_stylesheet_pinned": True,
            "ready_word_allowed": False,
            "raw_source_evidence_embedded": False,
            "app_imported": False,
            "html_script_bound": False,
            "stylesheet_runtime_loaded": False,
            "route_registered": False,
            "browser_executed": False,
            "browser_visual_review_performed": False,
            "ui_mounted": False,
            "current_activated": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "registration_hash")


def verify_static_presentation_asset_registration_v1(
    document: Any,
    spec: Any,
) -> bool:
    try:
        snapshot = _plain_json_snapshot(document)
        expected = build_static_presentation_asset_registration_v1(spec)
    except Exception:
        return False
    return strict_json_contract_equal(snapshot, expected)


def expected_portfolio_correlation_admission_rail_spec_v1() -> dict[str, Any]:
    return _plain_json_snapshot({
        "registration_id": PORTFOLIO_CORRELATION_ADMISSION_RAIL_REGISTRATION_ID,
        "source_contract": {
            "schema_version": "portfolio-correlation-admission-v1",
            "implementation_path": (
                "exchange_terminal/services/portfolio_correlation_admission_v1.py"
            ),
            "implementation_sha256": (
                "d279356f1d2d55e3a8ccd02524faa4245afc357ffe91b5820ae1cc772fa75002"
            ),
            "test_path": "tests/test_portfolio_correlation_admission_v1.py",
            "test_sha256": (
                "d0c3a07bb6e50502acdf15a55020459763cb9f7007503f46bb4e9b527ee4c97a"
            ),
            "adr_path": "docs/adr/0289-portfolio-correlation-admission-v1.md",
            "adr_sha256": (
                "a51da6ec286dcc172d7e8ab04bfd2cc2366e3a1ceadefb9169a9f5d15a5c8964"
            ),
        },
        "consumer_contract": {
            "schema_version": "portfolio-correlation-admission-rail-v1",
            "static_fingerprint": (
                "20260823-portfolio-correlation-admission-rail-v1-unmounted-lock-1"
            ),
            "browser_global": "HakimiPortfolioCorrelationAdmissionRailV1",
            "expected_commonjs_exports": [
                "ADMISSION_SCHEMA_VERSION",
                "RAIL_SCHEMA_VERSION",
                "RAIL_STATIC_FINGERPRINT",
                "STAGE_ORDER",
                "TIER_ORDER",
                "verifyPortfolioCorrelationAdmissionV1",
                "buildPortfolioCorrelationAdmissionRailViewModelV1",
                "renderPortfolioCorrelationAdmissionRailV1",
            ],
            "script_load_order": [
                "strict_canonical_javascript",
                "admission_rail_javascript",
            ],
            "stage_order": list(_STAGE_ORDER),
            "tier_order": [
                "INPUT_IDENTITY",
                "BASE_ADMISSION",
                "CORRELATION_PREREGISTRATION",
                "CORRELATION_MATRIX",
                "COMPLETE_LINK",
                "STRATA_PREREGISTRATION",
                "STRATA_GATE",
                "PERMISSION",
            ],
            "javascript_asset_id": "admission_rail_javascript",
            "stylesheet_asset_id": "admission_rail_stylesheet",
            "test_asset_id": "admission_rail_node_test",
            "adr_asset_id": "adr0290",
            "neutral_status_labels": {
                "pass": "LOCAL CLEAR",
                "block": "LOCAL BLOCK",
                "unknown": "SOURCE UNKNOWN",
            },
            "ready_word_allowed": False,
            "raw_source_evidence_embedded": False,
            "protected_stylesheet_path": "exchange_terminal/static/styles.css",
            "protected_stylesheet_sha256": (
                "ee6a5ae746142e32df768fe3261746f66c2b1a902e38b85fa9c0ecc4ce7bdc2a"
            ),
        },
        "assets": [
            {
                "asset_id": "admission_rail_javascript",
                "path": (
                    "exchange_terminal/static/"
                    "evidence_portfolio_correlation_admission_rail_v1.js"
                ),
                "role": "production",
                "sha256": (
                    "10604c3ec6953310cbbdb6c213261e538041bab7e236ea10d6fd0311dc5e8e87"
                ),
            },
            {
                "asset_id": "admission_rail_node_test",
                "path": (
                    "exchange_terminal/static/"
                    "evidence_portfolio_correlation_admission_rail_v1.test.js"
                ),
                "role": "verification",
                "sha256": (
                    "7d0ddc43cefd9c98babb16083fb982a1cac114440f056c0e717eea24d55fe374"
                ),
            },
            {
                "asset_id": "admission_rail_stylesheet",
                "path": (
                    "exchange_terminal/static/"
                    "evidence_portfolio_correlation_admission_rail_v1.css"
                ),
                "role": "presentation",
                "sha256": (
                    "ba0bf2eac9176d0e3dc98267b349c1928e465aaa07291620aa24ac4c18cab053"
                ),
            },
            {
                "asset_id": "adr0290",
                "path": "docs/adr/0290-portfolio-correlation-admission-rail-v1.md",
                "role": "decision",
                "sha256": (
                    "05f696add1a30bb5be5ed2d71e0efafdfaabbb4345a8b43cd5d8ea9c17188e4e"
                ),
            },
            {
                "asset_id": "strict_canonical_javascript",
                "path": "exchange_terminal/static/strict_canonical_json_v1.js",
                "role": "production_dependency",
                "sha256": (
                    "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39"
                ),
            },
        ],
        "host_plan": {key: None for key in _HOST_PLAN_KEYS},
    })


def build_portfolio_correlation_admission_rail_asset_registration_v1(
) -> dict[str, Any]:
    return build_static_presentation_asset_registration_v1(
        expected_portfolio_correlation_admission_rail_spec_v1()
    )


def verify_portfolio_correlation_admission_rail_asset_registration_v1(
    document: Any,
) -> bool:
    return verify_static_presentation_asset_registration_v1(
        document,
        expected_portfolio_correlation_admission_rail_spec_v1(),
    )


__all__ = [
    "PORTFOLIO_CORRELATION_ADMISSION_RAIL_REGISTRATION_ID",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_portfolio_correlation_admission_rail_asset_registration_v1",
    "build_static_presentation_asset_registration_v1",
    "expected_portfolio_correlation_admission_rail_spec_v1",
    "verify_portfolio_correlation_admission_rail_asset_registration_v1",
    "verify_static_presentation_asset_registration_v1",
]
