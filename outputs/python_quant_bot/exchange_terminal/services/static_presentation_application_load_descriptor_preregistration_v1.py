"""Preregister the static presentation application load graph without applying it."""

from __future__ import annotations

import math
from typing import Any

from exchange_terminal.services.static_presentation_in_memory_delivery_adapter_registration_v1 import (
    REGISTRATION_ID as ADAPTER_REGISTRATION_ID,
    SCHEMA_VERSION as ADAPTER_REGISTRATION_SCHEMA_VERSION,
    STATIC_FINGERPRINT as ADAPTER_REGISTRATION_STATIC_FINGERPRINT,
    build_static_presentation_in_memory_delivery_adapter_registration_v1,
    verify_static_presentation_in_memory_delivery_adapter_registration_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = "static-presentation-application-load-descriptor-preregistration-v1"
BINDING_SCHEMA_VERSION = (
    "static-presentation-application-load-descriptor-binding-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260823-static-presentation-app-load-descriptor-v1-unapplied-lock-1"
)
STATUS = "BLOCKED"

ADAPTER_REGISTRATION_HASH = (
    "846308ab26fc4bed7e3bce16a3dafed0aa71fd640c303f500422d4dc35f8f5bd"
)
ADAPTER_REGISTRATION_IMPLEMENTATION_SHA256 = (
    "8ff006d5d37836310bbc40aabad8f822d9cf6169c22d6865f21e5d1ac176c908"
)
ADAPTER_REGISTRATION_TEST_SHA256 = (
    "f9f8098669e8b65d35ee1125881763b6ccd912dcc50fd87cc76412204e7b06fb"
)
ADR0293_SHA256 = (
    "39d5c7e3dc89ab3e1fdcba544c769377e440d42d13f4a3bd7ea59a3e78ad30e1"
)
HOST_INDEX_HTML_SHA256 = (
    "553b33b0c4ef4ffb3e2f49d6671fe011f687696b95a7f5ff069f51f57bd5cd13"
)
HOST_APP_JS_SHA256 = (
    "9bf55162aff8d7a233804557c91605c801b92f515b2835978c05e2d1f3ef9210"
)
PROTECTED_STYLESHEET_SHA256 = (
    "ee6a5ae746142e32df768fe3261746f66c2b1a902e38b85fa9c0ecc4ce7bdc2a"
)
STRICT_CANONICAL_JS_SHA256 = (
    "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39"
)
ADMISSION_RAIL_JS_SHA256 = (
    "10604c3ec6953310cbbdb6c213261e538041bab7e236ea10d6fd0311dc5e8e87"
)
ADMISSION_RAIL_CSS_SHA256 = (
    "ba0bf2eac9176d0e3dc98267b349c1928e465aaa07291620aa24ac4c18cab053"
)
DELIVERY_ADAPTER_JS_SHA256 = (
    "5271d1122ef712cf2be7a2955d906e5ff436b6ea8102438187a5b957cf10d0c7"
)

_AUTHORITY_KEYS = (
    "adapter_execution_allowed",
    "app_binding_allowed",
    "browser_execution_allowed",
    "current_admission_allowed",
    "dom_mount_allowed",
    "host_asset_write_allowed",
    "html_asset_binding_allowed",
    "live_order_allowed",
    "paper_authorized",
    "payload_delivery_allowed",
    "route_registration_allowed",
    "script_runtime_loading_allowed",
    "stylesheet_runtime_binding_allowed",
    "writer_allowed",
)


def _plain_json_snapshot(value: Any, active: set[int] | None = None) -> Any:
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("non-finite values are not permitted")
        return value
    if type(value) not in {dict, list}:
        raise TypeError("load descriptor documents require native JSON values")

    active = set() if active is None else active
    marker = id(value)
    if marker in active:
        raise ValueError("cyclic load descriptor documents are not permitted")
    active.add(marker)
    try:
        if type(value) is list:
            return [_plain_json_snapshot(item, active) for item in value]
        snapshot: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError("load descriptor keys must be strings")
            snapshot[key] = _plain_json_snapshot(item, active)
        return snapshot
    finally:
        active.remove(marker)


def _locked_authority() -> dict[str, bool]:
    return {key: False for key in _AUTHORITY_KEYS}


def _relative_load_order() -> dict[str, Any]:
    return {
        "relative_subset_only": True,
        "existing_unlisted_assets_preserved": True,
        "stylesheets": [
            {
                "path": "exchange_terminal/static/styles.css",
                "sha256": PROTECTED_STYLESHEET_SHA256,
                "state": "OBSERVED_UNCHANGED",
                "relation": "EXISTING_BASE",
            },
            {
                "path": (
                    "exchange_terminal/static/"
                    "evidence_portfolio_correlation_admission_rail_v1.css"
                ),
                "sha256": ADMISSION_RAIL_CSS_SHA256,
                "state": "PREREGISTERED_NOT_LOADED",
                "relation": "AFTER_PROTECTED_STYLESHEET",
            },
        ],
        "scripts": [
            {
                "path": "exchange_terminal/static/strict_canonical_json_v1.js",
                "sha256": STRICT_CANONICAL_JS_SHA256,
                "state": "PREREGISTERED_NOT_LOADED",
                "relation": "BEFORE_ADMISSION_RAIL",
            },
            {
                "path": (
                    "exchange_terminal/static/"
                    "evidence_portfolio_correlation_admission_rail_v1.js"
                ),
                "sha256": ADMISSION_RAIL_JS_SHA256,
                "state": "PREREGISTERED_NOT_LOADED",
                "relation": "AFTER_CANONICAL_BEFORE_DELIVERY_ADAPTER",
            },
            {
                "path": (
                    "exchange_terminal/static/"
                    "evidence_static_presentation_in_memory_delivery_v1.js"
                ),
                "sha256": DELIVERY_ADAPTER_JS_SHA256,
                "state": "PREREGISTERED_NOT_LOADED",
                "relation": "AFTER_ADMISSION_RAIL_BEFORE_APP",
            },
            {
                "path": "exchange_terminal/static/app.js",
                "sha256": HOST_APP_JS_SHA256,
                "state": "OBSERVED_UNCHANGED",
                "relation": "EXISTING_HOST_AFTER_DELIVERY_CANDIDATE",
            },
        ],
    }


def _assert_exact_adapter_registration() -> None:
    registration = (
        build_static_presentation_in_memory_delivery_adapter_registration_v1()
    )
    if (
        not verify_static_presentation_in_memory_delivery_adapter_registration_v1(
            registration
        )
        or registration.get("schema_version")
        != ADAPTER_REGISTRATION_SCHEMA_VERSION
        or registration.get("static_fingerprint")
        != ADAPTER_REGISTRATION_STATIC_FINGERPRINT
        or registration.get("registration_id") != ADAPTER_REGISTRATION_ID
        or registration.get("adapter_registration_hash")
        != ADAPTER_REGISTRATION_HASH
        or registration.get("status") != "BLOCKED"
        or any(value is not None for value in registration.get("host_plan", {}).values())
        or any(value is not False for value in registration.get("authority", {}).values())
    ):
        raise RuntimeError("delivery adapter registration is not exact")


def build_static_presentation_application_load_descriptor_preregistration_v1(
) -> dict[str, Any]:
    _assert_exact_adapter_registration()
    relative_load_order = _relative_load_order()
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": STATUS,
        "descriptor_state": (
            "HOST_AND_RELATIVE_LOAD_GRAPH_PINNED_CHANGES_NOT_APPLIED"
        ),
        "decision": (
            "EXACT_ADAPTER_REGISTRATION_HOST_ASSETS_AND_FUTURE_RELATIVE_LOAD_"
            "GRAPH_PINNED_HTML_APP_SLOT_BROWSER_MOUNT_CURRENT_AND_EXECUTION_UNBOUND"
        ),
        "source_contract": {
            "adapter_registration_schema_version": (
                ADAPTER_REGISTRATION_SCHEMA_VERSION
            ),
            "adapter_registration_static_fingerprint": (
                ADAPTER_REGISTRATION_STATIC_FINGERPRINT
            ),
            "adapter_registration_id": ADAPTER_REGISTRATION_ID,
            "adapter_registration_hash": ADAPTER_REGISTRATION_HASH,
            "adapter_registration_implementation_path": (
                "exchange_terminal/services/"
                "static_presentation_in_memory_delivery_adapter_registration_v1.py"
            ),
            "adapter_registration_implementation_sha256": (
                ADAPTER_REGISTRATION_IMPLEMENTATION_SHA256
            ),
            "adapter_registration_test_path": (
                "tests/"
                "test_static_presentation_in_memory_delivery_adapter_registration_v1.py"
            ),
            "adapter_registration_test_sha256": ADAPTER_REGISTRATION_TEST_SHA256,
            "adr_path": (
                "docs/adr/"
                "0293-static-presentation-in-memory-delivery-adapter-registration-v1.md"
            ),
            "adr_sha256": ADR0293_SHA256,
        },
        "host_contract": {
            "index_html": {
                "path": "exchange_terminal/static/index.html",
                "observed_sha256": HOST_INDEX_HTML_SHA256,
                "modified_by_descriptor": False,
            },
            "app_javascript": {
                "path": "exchange_terminal/static/app.js",
                "observed_sha256": HOST_APP_JS_SHA256,
                "modified_by_descriptor": False,
            },
            "protected_stylesheet": {
                "path": "exchange_terminal/static/styles.css",
                "observed_sha256": PROTECTED_STYLESHEET_SHA256,
                "modified_by_descriptor": False,
            },
            "interface_view": "research",
        },
        "relative_load_order": relative_load_order,
        "relative_load_order_hash": strict_canonical_hash(relative_load_order),
        "mount_contract": {
            "host_anchor_id": "researchDataQualityCards",
            "host_anchor_observed_in_pinned_source": True,
            "future_slot_id": "portfolioCorrelationAdmissionRailHost",
            "future_slot_observed_in_pinned_source": False,
            "insertion_relation": "AFTER_HOST_ANCHOR",
            "existing_research_view_reused": True,
            "delivery_adapter_registration_id": ADAPTER_REGISTRATION_ID,
            "delivery_adapter_registration_hash": ADAPTER_REGISTRATION_HASH,
            "delivery_adapter_browser_global": (
                "HakimiStaticPresentationInMemoryDeliveryV1"
            ),
            "admission_rail_browser_global": (
                "HakimiPortfolioCorrelationAdmissionRailV1"
            ),
            "future_app_flow": [
                "VERIFY_IN_MEMORY_ENVELOPE",
                "EXTRACT_EXACT_ADMISSION_CANDIDATE",
                "BUILD_NO_DOM_RECEIPT",
                "RENDER_NEUTRAL_ADMISSION_RAIL",
            ],
            "envelope_verify_function": (
                "verifyStaticPresentationInMemoryDeliveryEnvelopeV1"
            ),
            "candidate_extract_function": (
                "extractAdmissionCandidateFromEnvelopeV1"
            ),
            "receipt_build_function": (
                "buildStaticPresentationInMemoryDeliveryReceiptV1"
            ),
            "render_function": "renderPortfolioCorrelationAdmissionRailV1",
            "render_output_type": "ESCAPED_STATIC_HTML_STRING",
            "payload_endpoint": None,
            "endpoint_required": False,
            "new_route_required": False,
        },
        "planned_mutations": [
            {
                "id": "HTML_ISOLATED_STYLESHEET_TAG_INSERTION",
                "performed": False,
            },
            {
                "id": "HTML_DEPENDENCY_SCRIPT_TAG_INSERTION",
                "performed": False,
            },
            {
                "id": "HTML_HOST_SLOT_INSERTION",
                "performed": False,
            },
            {
                "id": "APP_IN_MEMORY_ENVELOPE_AND_RENDER_BINDING",
                "performed": False,
            },
        ],
        "activation_order": [
            "DELIVERY_ADAPTER_REGISTRATION_EXACT",
            "HOST_FINGERPRINTS_PINNED",
            "RELATIVE_LOAD_GRAPH_PREREGISTERED",
            "HTML_ASSET_TAG_PREREGISTRATION",
            "APP_IN_MEMORY_BINDING_PREREGISTRATION",
            "HOST_SLOT_PREREGISTRATION",
            "UNMOUNTED_RENDER_DESCRIPTOR_REVIEW",
            "BROWSER_VISUAL_REVIEW",
            "ROUTE_AND_MOUNT_BINDING",
            "CURRENT_AND_RUNTIME_ACTIVATION",
        ],
        "blockers": [
            "HTML_ASSET_TAG_APPLICATION_UNAUTHORIZED",
            "APP_IN_MEMORY_ENVELOPE_BINDING_ABSENT",
            "FUTURE_HOST_SLOT_ABSENT",
            "UNMOUNTED_RENDER_DESCRIPTOR_UNREVIEWED",
            "BROWSER_EXECUTION_NOT_AUTHORIZED",
            "VISUAL_REVIEW_NOT_PERFORMED",
            "UI_MOUNT_NOT_AUTHORIZED",
            "CURRENT_ADMISSION_LOCKED",
        ],
        "facts": {
            "adapter_registration_exactly_verified": True,
            "host_index_pinned": True,
            "host_app_pinned": True,
            "protected_stylesheet_pinned": True,
            "relative_load_graph_preregistered": True,
            "host_anchor_observed_in_pinned_source": True,
            "future_host_slot_preregistered": True,
            "delivery_adapter_preregistered": True,
            "payload_endpoint_required": False,
            "new_route_required": False,
            "html_assets_inserted": False,
            "host_slot_inserted": False,
            "app_binding_present": False,
            "adapter_execution_observed": False,
            "payload_delivery_observed": False,
            "route_registered": False,
            "browser_executed": False,
            "visually_reviewed": False,
            "ui_mounted": False,
            "current_activated": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "load_descriptor_hash")


def verify_static_presentation_application_load_descriptor_preregistration_v1(
    document: Any,
) -> bool:
    try:
        snapshot = _plain_json_snapshot(document)
        expected = (
            build_static_presentation_application_load_descriptor_preregistration_v1()
        )
    except Exception:
        return False
    return strict_json_contract_equal(snapshot, expected)


def _build_binding(
    *,
    status: str,
    binding_state: str,
    reason_code: str,
    load_descriptor_hash: str | None,
    adapter_registration_hash: str | None,
    relative_load_order_hash: str | None,
    descriptor_exact: bool,
    registration_exact: bool,
) -> dict[str, Any]:
    document = {
        "schema_version": BINDING_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "binding_state": binding_state,
        "reason_code": reason_code,
        "load_descriptor_hash": load_descriptor_hash,
        "adapter_registration_hash": adapter_registration_hash,
        "relative_load_order_hash": relative_load_order_hash,
        "host_index_html_sha256": HOST_INDEX_HTML_SHA256,
        "host_app_javascript_sha256": HOST_APP_JS_SHA256,
        "protected_stylesheet_sha256": PROTECTED_STYLESHEET_SHA256,
        "facts": {
            "load_descriptor_exactly_verified": descriptor_exact,
            "adapter_registration_exactly_verified": registration_exact,
            "host_hashes_bound": descriptor_exact,
            "relative_load_order_hash_bound": descriptor_exact,
            "raw_load_descriptor_embedded": False,
            "raw_adapter_registration_embedded": False,
            "raw_payload_embedded": False,
            "html_assets_inserted": False,
            "host_slot_inserted": False,
            "app_binding_present": False,
            "adapter_execution_observed": False,
            "payload_delivery_observed": False,
            "route_registered": False,
            "browser_executed": False,
            "visually_reviewed": False,
            "ui_mounted": False,
            "current_activated": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "load_descriptor_binding_hash")


def _unknown_binding(reason_code: str) -> dict[str, Any]:
    return _build_binding(
        status="UNKNOWN",
        binding_state="UNKNOWN",
        reason_code=reason_code,
        load_descriptor_hash=None,
        adapter_registration_hash=None,
        relative_load_order_hash=None,
        descriptor_exact=False,
        registration_exact=False,
    )


def build_static_presentation_application_load_descriptor_binding_candidate_v1(
    load_descriptor_document: Any,
    adapter_registration_document: Any,
) -> dict[str, Any]:
    try:
        descriptor = _plain_json_snapshot(load_descriptor_document)
    except Exception:
        return _unknown_binding("LOAD_DESCRIPTOR_SNAPSHOT_FAILED")
    if not verify_static_presentation_application_load_descriptor_preregistration_v1(
        descriptor
    ):
        return _unknown_binding("LOAD_DESCRIPTOR_NOT_EXACT")

    try:
        registration = _plain_json_snapshot(adapter_registration_document)
    except Exception:
        return _unknown_binding("ADAPTER_REGISTRATION_SNAPSHOT_FAILED")
    if (
        not verify_static_presentation_in_memory_delivery_adapter_registration_v1(
            registration
        )
        or registration.get("adapter_registration_hash")
        != ADAPTER_REGISTRATION_HASH
    ):
        return _unknown_binding("ADAPTER_REGISTRATION_NOT_EXACT")

    return _build_binding(
        status="BLOCKED",
        binding_state=(
            "LOAD_DESCRIPTOR_AND_ADAPTER_REGISTRATION_HASH_BOUND_HOST_UNMODIFIED"
        ),
        reason_code=(
            "EXACT_LOAD_GRAPH_AND_ADAPTER_REGISTRATION_HASH_BOUND_"
            "HTML_APP_SLOT_BROWSER_MOUNT_CURRENT_AND_EXECUTION_ABSENT"
        ),
        load_descriptor_hash=descriptor["load_descriptor_hash"],
        adapter_registration_hash=registration["adapter_registration_hash"],
        relative_load_order_hash=descriptor["relative_load_order_hash"],
        descriptor_exact=True,
        registration_exact=True,
    )


def verify_static_presentation_application_load_descriptor_binding_candidate_v1(
    document: Any,
    load_descriptor_document: Any,
    adapter_registration_document: Any,
) -> bool:
    try:
        snapshot = _plain_json_snapshot(document)
    except Exception:
        return False
    expected = (
        build_static_presentation_application_load_descriptor_binding_candidate_v1(
            load_descriptor_document,
            adapter_registration_document,
        )
    )
    return strict_json_contract_equal(snapshot, expected)


__all__ = [
    "ADAPTER_REGISTRATION_HASH",
    "BINDING_SCHEMA_VERSION",
    "HOST_APP_JS_SHA256",
    "HOST_INDEX_HTML_SHA256",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_static_presentation_application_load_descriptor_binding_candidate_v1",
    "build_static_presentation_application_load_descriptor_preregistration_v1",
    "verify_static_presentation_application_load_descriptor_binding_candidate_v1",
    "verify_static_presentation_application_load_descriptor_preregistration_v1",
]
