"""Register the ADR0306 dual-runtime adapters without executing either one."""

from __future__ import annotations

import math
from typing import Any

from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1 as asset_registration_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-"
    "in-memory-delivery-adapter-registration-v1"
)
STATIC_FINGERPRINT = (
    "20260823-portfolio-correlation-admission-effective-budget-"
    "delivery-adapter-registration-v1-unbound-lock-1"
)
STATUS = "BLOCKED"
REGISTRATION_ID = (
    "portfolio-correlation-admission-effective-budget-delivery-adapters-v1"
)

PREDECESSOR_REGISTRATION_HASH = (
    "265a897bb11a9d2df873f23a3faf5dc21bc4f66bb93ef8d313994e35938d04c4"
)
PREDECESSOR_IMPLEMENTATION_SHA256 = (
    "41e2195e41c142dbaa750ebef5262eda40e4fee80f60a26e71dac89d33531a41"
)
PREDECESSOR_TEST_SHA256 = (
    "04c3b36199b70e2f8d9e0adafc3063d683b8a6166f7c071480fd5d32473e6328"
)
ADR0308_SHA256 = (
    "f49fb1e3ff9bd60489c33b91676ceb854cea06318990715bfdaea8c05fca815f"
)
PROTECTED_STYLESHEET_SHA256 = (
    "ee6a5ae746142e32df768fe3261746f66c2b1a902e38b85fa9c0ecc4ce7bdc2a"
)

PYTHON_ADAPTER_IMPLEMENTATION_SHA256 = (
    "9ada46b146fcecf48b96d9e5af1f4022ab23b4f0bbc5c1c39d59fb8d9a54d8db"
)
PYTHON_ADAPTER_TEST_SHA256 = (
    "d4b3e8a93aefe0eced326538d85ea49ffd8f6466098131a62a5b6bbb90716374"
)
JAVASCRIPT_ADAPTER_IMPLEMENTATION_SHA256 = (
    "867f7a7016472101a3606f2af22ae7b63509cc2afb3d2dbfe8f7058da8e08be0"
)
JAVASCRIPT_ADAPTER_TEST_SHA256 = (
    "ebf74408b34ec5ca1a2f539930289424684d0ec975b791f3577d3022f409425d"
)
STRICT_CANONICAL_JAVASCRIPT_SHA256 = (
    "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39"
)
ADR0306_SHA256 = (
    "2e545decd55a18425ac99a9d46b527127d4be0eb926f8c943087e52d6e347423"
)

ENVELOPE_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-"
    "in-memory-delivery-envelope-v1"
)
PAYLOAD_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-"
    "presentation-payload-v1"
)
RECEIPT_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-"
    "payload-extraction-receipt-v1"
)
ENVELOPE_STATIC_FINGERPRINT = (
    "20260823-portfolio-correlation-admission-effective-budget-"
    "in-memory-delivery-v1-lock-1"
)
JAVASCRIPT_GLOBAL = (
    "HakimiPortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryV1"
)
BRIDGE_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-bridge-v1"
)
BRIDGE_STATIC_FINGERPRINT = (
    "20260823-portfolio-correlation-admission-effective-budget-"
    "bridge-v1-unmounted-lock-1"
)
BRIDGE_GLOBAL = (
    "HakimiPortfolioCorrelationAdmissionEffectiveBudgetBridgeV1"
)

PYTHON_EXPORTS = (
    "SCHEMA_VERSION",
    "PAYLOAD_SCHEMA_VERSION",
    "RECEIPT_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "JAVASCRIPT_GLOBAL",
    "FUNCTION_EXPORTS",
    "build_portfolio_correlation_admission_effective_budget_in_memory_delivery_envelope_v1",
    "verify_portfolio_correlation_admission_effective_budget_in_memory_delivery_envelope_v1",
)
JAVASCRIPT_EXPORTS = (
    "ENVELOPE_SCHEMA_VERSION",
    "PAYLOAD_SCHEMA_VERSION",
    "RECEIPT_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "TIER_ORDER",
    "verifyPortfolioCorrelationAdmissionEffectiveBudgetPresentationPayloadV1",
    "verifyPortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryEnvelopeV1",
    "extractPortfolioCorrelationAdmissionEffectiveBudgetPresentationPayloadV1",
    "buildPortfolioCorrelationAdmissionEffectiveBudgetPayloadExtractionReceiptV1",
    "verifyPortfolioCorrelationAdmissionEffectiveBudgetPayloadExtractionReceiptV1",
)
RELATIVE_LOAD_ORDER = (
    "strict_canonical_json_v1.js",
    "evidence_portfolio_correlation_admission_effective_budget_in_memory_delivery_v1.js",
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


class _InvalidJsonDocument(ValueError):
    pass


def _plain_json_snapshot(
    value: Any,
    active: set[int] | None = None,
) -> Any:
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise _InvalidJsonDocument("non-finite numbers are not supported")
        return value
    if type(value) not in (dict, list):
        raise _InvalidJsonDocument("document must contain exact JSON types")
    if active is None:
        active = set()
    identity = id(value)
    if identity in active:
        raise _InvalidJsonDocument("cyclic documents are not supported")
    active.add(identity)
    try:
        if type(value) is list:
            return [_plain_json_snapshot(item, active) for item in value]
        snapshot: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise _InvalidJsonDocument("object keys must be exact strings")
            snapshot[key] = _plain_json_snapshot(item, active)
        return snapshot
    finally:
        active.remove(identity)


def _locked_authority() -> dict[str, bool]:
    return {key: False for key in _AUTHORITY_KEYS}


def _host_plan() -> dict[str, None]:
    return {key: None for key in _HOST_PLAN_KEYS}


def _direct_asset_manifest() -> list[dict[str, str]]:
    return sorted(
        [
            {
                "asset_id": "adr0306",
                "path": (
                    "docs/adr/"
                    "0306-portfolio-correlation-admission-effective-budget-"
                    "in-memory-delivery-v1.md"
                ),
                "role": "decision",
                "sha256": ADR0306_SHA256,
            },
            {
                "asset_id": "delivery_javascript_adapter",
                "path": (
                    "exchange_terminal/static/"
                    "evidence_portfolio_correlation_admission_effective_budget_"
                    "in_memory_delivery_v1.js"
                ),
                "role": "production",
                "sha256": JAVASCRIPT_ADAPTER_IMPLEMENTATION_SHA256,
            },
            {
                "asset_id": "delivery_javascript_test",
                "path": (
                    "exchange_terminal/static/"
                    "evidence_portfolio_correlation_admission_effective_budget_"
                    "in_memory_delivery_v1.test.js"
                ),
                "role": "verification",
                "sha256": JAVASCRIPT_ADAPTER_TEST_SHA256,
            },
            {
                "asset_id": "delivery_python_adapter",
                "path": (
                    "exchange_terminal/services/"
                    "portfolio_correlation_admission_effective_budget_"
                    "in_memory_delivery_v1.py"
                ),
                "role": "production",
                "sha256": PYTHON_ADAPTER_IMPLEMENTATION_SHA256,
            },
            {
                "asset_id": "delivery_python_test",
                "path": (
                    "tests/"
                    "test_portfolio_correlation_admission_effective_budget_"
                    "in_memory_delivery_v1.py"
                ),
                "role": "verification",
                "sha256": PYTHON_ADAPTER_TEST_SHA256,
            },
            {
                "asset_id": "strict_canonical_javascript",
                "path": "exchange_terminal/static/strict_canonical_json_v1.js",
                "role": "production_dependency",
                "sha256": STRICT_CANONICAL_JAVASCRIPT_SHA256,
            },
        ],
        key=lambda item: item["asset_id"],
    )


def _assert_exact_predecessor() -> dict[str, Any]:
    predecessor = (
        asset_registration_v1.build_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1()
    )
    if (
        not asset_registration_v1.verify_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1(
            predecessor
        )
        or predecessor.get("registration_hash")
        != PREDECESSOR_REGISTRATION_HASH
    ):
        raise ValueError("ADR0308 predecessor registration is not exact")
    return predecessor


def build_portfolio_correlation_admission_effective_budget_in_memory_delivery_adapter_registration_v1(
) -> dict[str, Any]:
    predecessor = _assert_exact_predecessor()
    asset_manifest = _direct_asset_manifest()
    registration = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": STATUS,
        "registration_id": REGISTRATION_ID,
        "registration_state": (
            "DUAL_RUNTIME_DELIVERY_ADAPTER_ASSETS_REGISTERED_UNBOUND"
        ),
        "decision": (
            "EXACT_ADR0308_PREDECESSOR_AND_DUAL_RUNTIME_ADAPTER_ASSETS_"
            "PINNED_APP_HTML_STYLESHEET_BROWSER_ROUTE_MOUNT_CURRENT_"
            "AND_EXECUTION_UNBOUND"
        ),
        "activation_order": [
            "PREDECESSOR_ASSET_REGISTRATION_EXACT",
            "DUAL_RUNTIME_ADAPTER_ASSET_HASHES_PINNED",
            "DELIVERY_ADAPTER_ASSET_REGISTRATION",
            "APP_IMPORT_PREREGISTRATION",
            "HTML_SCRIPT_AND_STYLESHEET_PREREGISTRATION",
            "UNMOUNTED_RENDER_DESCRIPTOR_REVIEW",
            "BROWSER_VISUAL_REVIEW",
            "ROUTE_AND_MOUNT_BINDING",
            "CURRENT_AND_RUNTIME_ACTIVATION",
        ],
        "predecessor_contract": {
            "schema_version": predecessor["schema_version"],
            "registration_id": predecessor["registration_id"],
            "registration_hash": predecessor["registration_hash"],
            "asset_manifest_hash": predecessor["asset_manifest_hash"],
            "implementation_path": (
                "exchange_terminal/services/"
                "portfolio_correlation_admission_effective_budget_bridge_"
                "asset_registration_v1.py"
            ),
            "implementation_sha256": PREDECESSOR_IMPLEMENTATION_SHA256,
            "test_path": (
                "tests/"
                "test_portfolio_correlation_admission_effective_budget_"
                "bridge_asset_registration_v1.py"
            ),
            "test_sha256": PREDECESSOR_TEST_SHA256,
            "adr_path": (
                "docs/adr/"
                "0308-portfolio-correlation-admission-effective-budget-"
                "bridge-asset-registration-v1.md"
            ),
            "adr_sha256": ADR0308_SHA256,
        },
        "asset_manifest": asset_manifest,
        "asset_manifest_hash": strict_canonical_hash(asset_manifest),
        "python_contract": {
            "implementation_path": (
                "exchange_terminal/services/"
                "portfolio_correlation_admission_effective_budget_"
                "in_memory_delivery_v1.py"
            ),
            "implementation_sha256": PYTHON_ADAPTER_IMPLEMENTATION_SHA256,
            "test_path": (
                "tests/"
                "test_portfolio_correlation_admission_effective_budget_"
                "in_memory_delivery_v1.py"
            ),
            "test_sha256": PYTHON_ADAPTER_TEST_SHA256,
            "schema_version": ENVELOPE_SCHEMA_VERSION,
            "payload_schema_version": PAYLOAD_SCHEMA_VERSION,
            "static_fingerprint": ENVELOPE_STATIC_FINGERPRINT,
            "builder": (
                "build_portfolio_correlation_admission_effective_budget_"
                "in_memory_delivery_envelope_v1"
            ),
            "verifier": (
                "verify_portfolio_correlation_admission_effective_budget_"
                "in_memory_delivery_envelope_v1"
            ),
            "exports": list(PYTHON_EXPORTS),
        },
        "javascript_contract": {
            "implementation_path": (
                "exchange_terminal/static/"
                "evidence_portfolio_correlation_admission_effective_budget_"
                "in_memory_delivery_v1.js"
            ),
            "implementation_sha256": JAVASCRIPT_ADAPTER_IMPLEMENTATION_SHA256,
            "test_path": (
                "exchange_terminal/static/"
                "evidence_portfolio_correlation_admission_effective_budget_"
                "in_memory_delivery_v1.test.js"
            ),
            "test_sha256": JAVASCRIPT_ADAPTER_TEST_SHA256,
            "strict_canonical_javascript_sha256": (
                STRICT_CANONICAL_JAVASCRIPT_SHA256
            ),
            "browser_global": JAVASCRIPT_GLOBAL,
            "module_format": "UMD_COMMONJS",
            "envelope_schema_version": ENVELOPE_SCHEMA_VERSION,
            "payload_schema_version": PAYLOAD_SCHEMA_VERSION,
            "receipt_schema_version": RECEIPT_SCHEMA_VERSION,
            "static_fingerprint": ENVELOPE_STATIC_FINGERPRINT,
            "exports": list(JAVASCRIPT_EXPORTS),
            "relative_load_order": list(RELATIVE_LOAD_ORDER),
        },
        "presentation_contract": {
            "bridge_schema_version": BRIDGE_SCHEMA_VERSION,
            "bridge_static_fingerprint": BRIDGE_STATIC_FINGERPRINT,
            "bridge_browser_global": BRIDGE_GLOBAL,
            "asset_registration_hash": PREDECESSOR_REGISTRATION_HASH,
            "stage_order": list(asset_registration_v1.STAGE_ORDER),
            "tier_order": list(asset_registration_v1.TIER_ORDER),
            "neutral_status_labels": {
                "pass": "LOCAL ALIGNMENT",
                "block": "LOCAL BLOCK",
                "unknown": "SOURCE UNKNOWN",
            },
            "ready_word_allowed": False,
            "raw_source_evidence_embedded": False,
            "protected_stylesheet_path": (
                "exchange_terminal/static/styles.css"
            ),
            "protected_stylesheet_sha256": PROTECTED_STYLESHEET_SHA256,
        },
        "transport_contract": {
            "mode": "IN_MEMORY_ARGUMENT_ONLY",
            "content_type": "application/json",
            "endpoint": None,
            "route": None,
            "host_slot": None,
        },
        "facts": {
            "predecessor_registration_exactly_verified": True,
            "predecessor_asset_manifest_transitively_pinned": True,
            "dual_runtime_adapter_assets_registered": True,
            "python_adapter_registered": True,
            "javascript_adapter_registered": True,
            "adapter_tests_pinned": True,
            "cross_runtime_schema_pinned": True,
            "relative_load_order_pinned": True,
            "delivery_attempted": False,
            "python_adapter_invoked": False,
            "javascript_adapter_runtime_loaded": False,
            "app_imported": False,
            "html_script_bound": False,
            "stylesheet_link_bound": False,
            "browser_executed": False,
            "route_registered": False,
            "dom_mounted": False,
            "current_activated": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
            "protected_stylesheet_pinned": True,
        },
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
        "host_plan": _host_plan(),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(
        registration,
        "adapter_registration_hash",
    )


def verify_portfolio_correlation_admission_effective_budget_in_memory_delivery_adapter_registration_v1(
    document: Any,
) -> bool:
    try:
        snapshot = _plain_json_snapshot(document)
        expected = build_portfolio_correlation_admission_effective_budget_in_memory_delivery_adapter_registration_v1()
    except (KeyError, TypeError, ValueError):
        return False
    return strict_json_contract_equal(snapshot, expected)
