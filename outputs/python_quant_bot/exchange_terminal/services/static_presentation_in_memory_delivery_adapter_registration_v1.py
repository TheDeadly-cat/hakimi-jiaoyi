"""Register the static presentation delivery adapters without activating them."""

from __future__ import annotations

import math
from typing import Any

from exchange_terminal.services.static_presentation_asset_registration_v1 import (
    PORTFOLIO_CORRELATION_ADMISSION_RAIL_REGISTRATION_ID,
    SCHEMA_VERSION as BASE_REGISTRATION_SCHEMA_VERSION,
    build_portfolio_correlation_admission_rail_asset_registration_v1,
    verify_portfolio_correlation_admission_rail_asset_registration_v1,
)
from exchange_terminal.services.static_presentation_in_memory_delivery_v1 import (
    CONSUMER_SCHEMA_VERSION,
    REGISTRATION_HASH as DELIVERY_BASE_REGISTRATION_HASH,
    SCHEMA_VERSION as DELIVERY_ENVELOPE_SCHEMA_VERSION,
    STATIC_FINGERPRINT as DELIVERY_ENVELOPE_STATIC_FINGERPRINT,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = "static-presentation-in-memory-delivery-adapter-registration-v1"
STATIC_FINGERPRINT = (
    "20260823-static-presentation-delivery-adapter-registration-v1-unbound-lock-1"
)
REGISTRATION_ID = "portfolio-correlation-admission-rail-delivery-adapters-v1"
STATUS = "BLOCKED"

BASE_ASSET_REGISTRATION_HASH = (
    "e5512d1d84ce9a2d3e3a23955b9d089c8c454d3cad93ac49f2c78bbf288459a1"
)
BASE_REGISTRATION_IMPLEMENTATION_SHA256 = (
    "d833b998c2791a1b6c471108a74d770e1bebcb5957d8175373f2848b1cff8a90"
)
BASE_REGISTRATION_TEST_SHA256 = (
    "3f65fed021b6cfc420ed2e13b379b8bf75ca1a6c04fd56ed3b4bb3771addec5e"
)
ADR0291_SHA256 = (
    "e9bbf22cfd120b344cf54ba1f8047030975085a8e362598fe8ddf04f48fb5109"
)
PYTHON_ADAPTER_IMPLEMENTATION_SHA256 = (
    "013476c91e3c63e05aeca13eeb3cb22f11842d0894ce0c0c9007e308121dcfa1"
)
PYTHON_ADAPTER_TEST_SHA256 = (
    "1eb0606c739eb6f3ee203617eb324bff6d22d3900103e38b685f23aa55e28ea0"
)
JAVASCRIPT_ADAPTER_IMPLEMENTATION_SHA256 = (
    "5271d1122ef712cf2be7a2955d906e5ff436b6ea8102438187a5b957cf10d0c7"
)
JAVASCRIPT_ADAPTER_TEST_SHA256 = (
    "d2f5e54c2ece98d884a1f2d8e882db401781c6869966f8ba9b1309bac92880f6"
)
ADR0292_SHA256 = (
    "bc035eb8c232db1afc2b2d3c4d799a7f7315e42abdf29c299ae8bff20d6ccb09"
)
PROTECTED_STYLESHEET_SHA256 = (
    "ee6a5ae746142e32df768fe3261746f66c2b1a902e38b85fa9c0ecc4ce7bdc2a"
)

_STAGE_ORDER = ["SOURCE", "GAP", "MATURITY", "PERMISSION"]
_HOST_PLAN_KEYS = (
    "app_importer",
    "browser_review_receipt",
    "endpoint",
    "html_script",
    "mount_slot",
    "payload_source_provider",
    "route",
    "stylesheet_link",
)
_AUTHORITY_KEYS = (
    "adapter_execution_allowed",
    "app_import_allowed",
    "browser_execution_allowed",
    "current_admission_allowed",
    "dom_mount_allowed",
    "endpoint_registration_allowed",
    "html_script_binding_allowed",
    "live_order_allowed",
    "paper_authorized",
    "route_registration_allowed",
    "runtime_asset_loading_allowed",
    "stylesheet_link_binding_allowed",
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
        raise TypeError("registration documents require native JSON values")

    active = set() if active is None else active
    marker = id(value)
    if marker in active:
        raise ValueError("cyclic registration documents are not permitted")
    active.add(marker)
    try:
        if type(value) is list:
            return [_plain_json_snapshot(item, active) for item in value]
        snapshot: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError("registration document keys must be strings")
            snapshot[key] = _plain_json_snapshot(item, active)
        return snapshot
    finally:
        active.remove(marker)


def _direct_asset_manifest() -> list[dict[str, str]]:
    rows = [
        {
            "asset_id": "adr0292",
            "path": "docs/adr/0292-static-presentation-in-memory-delivery-v1.md",
            "role": "decision",
            "sha256": ADR0292_SHA256,
        },
        {
            "asset_id": "delivery_javascript_adapter",
            "path": (
                "exchange_terminal/static/"
                "evidence_static_presentation_in_memory_delivery_v1.js"
            ),
            "role": "production",
            "sha256": JAVASCRIPT_ADAPTER_IMPLEMENTATION_SHA256,
        },
        {
            "asset_id": "delivery_javascript_test",
            "path": (
                "exchange_terminal/static/"
                "evidence_static_presentation_in_memory_delivery_v1.test.js"
            ),
            "role": "verification",
            "sha256": JAVASCRIPT_ADAPTER_TEST_SHA256,
        },
        {
            "asset_id": "delivery_python_adapter",
            "path": (
                "exchange_terminal/services/"
                "static_presentation_in_memory_delivery_v1.py"
            ),
            "role": "production",
            "sha256": PYTHON_ADAPTER_IMPLEMENTATION_SHA256,
        },
        {
            "asset_id": "delivery_python_test",
            "path": "tests/test_static_presentation_in_memory_delivery_v1.py",
            "role": "verification",
            "sha256": PYTHON_ADAPTER_TEST_SHA256,
        },
    ]
    return sorted(rows, key=lambda row: row["asset_id"])


def _locked_authority() -> dict[str, bool]:
    return {key: False for key in _AUTHORITY_KEYS}


def _assert_exact_predecessor() -> None:
    predecessor = (
        build_portfolio_correlation_admission_rail_asset_registration_v1()
    )
    if (
        not verify_portfolio_correlation_admission_rail_asset_registration_v1(
            predecessor
        )
        or predecessor.get("schema_version") != BASE_REGISTRATION_SCHEMA_VERSION
        or predecessor.get("registration_id")
        != PORTFOLIO_CORRELATION_ADMISSION_RAIL_REGISTRATION_ID
        or predecessor.get("registration_hash") != BASE_ASSET_REGISTRATION_HASH
        or predecessor.get("status") != "BLOCKED"
        or any(value is not None for value in predecessor.get("host_plan", {}).values())
        or DELIVERY_BASE_REGISTRATION_HASH != BASE_ASSET_REGISTRATION_HASH
    ):
        raise RuntimeError("base static asset registration is not exact")


def build_static_presentation_in_memory_delivery_adapter_registration_v1(
) -> dict[str, Any]:
    _assert_exact_predecessor()
    asset_manifest = _direct_asset_manifest()
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "registration_id": REGISTRATION_ID,
        "status": STATUS,
        "registration_state": (
            "DUAL_RUNTIME_DELIVERY_ADAPTER_ASSETS_REGISTERED_UNBOUND"
        ),
        "decision": (
            "EXACT_PREDECESSOR_AND_DUAL_RUNTIME_ADAPTER_ASSETS_PINNED_"
            "APP_HTML_STYLESHEET_BROWSER_ROUTE_MOUNT_CURRENT_AND_EXECUTION_UNBOUND"
        ),
        "predecessor_contract": {
            "schema_version": BASE_REGISTRATION_SCHEMA_VERSION,
            "registration_id": (
                PORTFOLIO_CORRELATION_ADMISSION_RAIL_REGISTRATION_ID
            ),
            "registration_hash": BASE_ASSET_REGISTRATION_HASH,
            "implementation_path": (
                "exchange_terminal/services/"
                "static_presentation_asset_registration_v1.py"
            ),
            "implementation_sha256": BASE_REGISTRATION_IMPLEMENTATION_SHA256,
            "test_path": "tests/test_static_presentation_asset_registration_v1.py",
            "test_sha256": BASE_REGISTRATION_TEST_SHA256,
            "adr_path": "docs/adr/0291-static-presentation-asset-registration-v1.md",
            "adr_sha256": ADR0291_SHA256,
        },
        "transport_contract": {
            "mode": "IN_MEMORY_ARGUMENT_ONLY",
            "content_type": "application/json",
            "endpoint": None,
            "route": None,
            "host_slot": None,
        },
        "python_contract": {
            "schema_version": DELIVERY_ENVELOPE_SCHEMA_VERSION,
            "static_fingerprint": DELIVERY_ENVELOPE_STATIC_FINGERPRINT,
            "base_registration_hash": BASE_ASSET_REGISTRATION_HASH,
            "exports": [
                "CONSUMER_SCHEMA_VERSION",
                "REGISTRATION_HASH",
                "SCHEMA_VERSION",
                "STATIC_FINGERPRINT",
                "build_portfolio_correlation_admission_rail_in_memory_delivery_envelope_v1",
                "verify_portfolio_correlation_admission_rail_in_memory_delivery_envelope_v1",
            ],
            "builder": (
                "build_portfolio_correlation_admission_rail_"
                "in_memory_delivery_envelope_v1"
            ),
            "verifier": (
                "verify_portfolio_correlation_admission_rail_"
                "in_memory_delivery_envelope_v1"
            ),
        },
        "javascript_contract": {
            "module_format": "UMD_COMMONJS",
            "browser_global": "HakimiStaticPresentationInMemoryDeliveryV1",
            "envelope_schema_version": DELIVERY_ENVELOPE_SCHEMA_VERSION,
            "envelope_static_fingerprint": DELIVERY_ENVELOPE_STATIC_FINGERPRINT,
            "receipt_schema_version": (
                "static-presentation-in-memory-delivery-receipt-v1"
            ),
            "receipt_static_fingerprint": (
                "20260823-static-presentation-in-memory-delivery-"
                "receipt-v1-no-dom-lock-1"
            ),
            "base_registration_hash": BASE_ASSET_REGISTRATION_HASH,
            "exports": [
                "RECEIPT_SCHEMA_VERSION",
                "RECEIPT_STATIC_FINGERPRINT",
                "REGISTRATION_HASH",
                "SCHEMA_VERSION",
                "STATIC_FINGERPRINT",
                "buildStaticPresentationInMemoryDeliveryReceiptV1",
                "extractAdmissionCandidateFromEnvelopeV1",
                "verifyStaticPresentationInMemoryDeliveryEnvelopeV1",
                "verifyStaticPresentationInMemoryDeliveryReceiptV1",
            ],
            "relative_load_order": [
                "strict_canonical_json_v1.js",
                "evidence_portfolio_correlation_admission_rail_v1.js",
                "evidence_static_presentation_in_memory_delivery_v1.js",
            ],
        },
        "presentation_contract": {
            "consumer_schema_version": CONSUMER_SCHEMA_VERSION,
            "stage_order": list(_STAGE_ORDER),
            "neutral_status_labels": {
                "pass": "LOCAL CLEAR",
                "block": "LOCAL BLOCK",
                "unknown": "SOURCE UNKNOWN",
            },
            "ready_word_allowed": False,
            "raw_source_evidence_embedded": False,
            "protected_stylesheet_path": "exchange_terminal/static/styles.css",
            "protected_stylesheet_sha256": PROTECTED_STYLESHEET_SHA256,
        },
        "asset_manifest": asset_manifest,
        "asset_manifest_hash": strict_canonical_hash(asset_manifest),
        "host_plan": {key: None for key in _HOST_PLAN_KEYS},
        "activation_order": [
            "PREDECESSOR_STATIC_ASSET_REGISTRATION_EXACT",
            "DUAL_RUNTIME_ADAPTER_ASSET_HASHES_PINNED",
            "DELIVERY_ADAPTER_ASSET_REGISTRATION",
            "APP_IMPORT_PREREGISTRATION",
            "HTML_SCRIPT_AND_STYLESHEET_PREREGISTRATION",
            "UNMOUNTED_RENDER_DESCRIPTOR_REVIEW",
            "BROWSER_VISUAL_REVIEW",
            "ROUTE_AND_MOUNT_BINDING",
            "CURRENT_AND_RUNTIME_ACTIVATION",
        ],
        "blockers": [
            "APP_IMPORT_PREREGISTRATION_ABSENT",
            "HTML_SCRIPT_PREREGISTRATION_ABSENT",
            "STYLESHEET_LINK_PREREGISTRATION_ABSENT",
            "UNMOUNTED_RENDER_DESCRIPTOR_UNREVIEWED",
            "BROWSER_VISUAL_REVIEW_NOT_PERFORMED",
            "ROUTE_UNBOUND",
            "MOUNT_SLOT_UNBOUND",
            "CURRENT_ADMISSION_LOCKED",
        ],
        "facts": {
            "predecessor_registration_exactly_verified": True,
            "predecessor_asset_manifest_transitively_pinned": True,
            "dual_runtime_adapter_assets_registered": True,
            "python_adapter_registered": True,
            "javascript_adapter_registered": True,
            "adapter_tests_pinned": True,
            "cross_runtime_schema_pinned": True,
            "relative_load_order_pinned": True,
            "protected_stylesheet_pinned": True,
            "delivery_attempted": False,
            "python_adapter_invoked": False,
            "javascript_adapter_runtime_loaded": False,
            "app_imported": False,
            "html_script_bound": False,
            "stylesheet_link_bound": False,
            "route_registered": False,
            "browser_executed": False,
            "dom_mounted": False,
            "current_activated": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "adapter_registration_hash")


def verify_static_presentation_in_memory_delivery_adapter_registration_v1(
    document: Any,
) -> bool:
    try:
        snapshot = _plain_json_snapshot(document)
        expected = (
            build_static_presentation_in_memory_delivery_adapter_registration_v1()
        )
    except Exception:
        return False
    return strict_json_contract_equal(snapshot, expected)


__all__ = [
    "BASE_ASSET_REGISTRATION_HASH",
    "JAVASCRIPT_ADAPTER_IMPLEMENTATION_SHA256",
    "JAVASCRIPT_ADAPTER_TEST_SHA256",
    "PYTHON_ADAPTER_IMPLEMENTATION_SHA256",
    "PYTHON_ADAPTER_TEST_SHA256",
    "REGISTRATION_ID",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_static_presentation_in_memory_delivery_adapter_registration_v1",
    "verify_static_presentation_in_memory_delivery_adapter_registration_v1",
]
