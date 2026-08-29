"""Fixed asset-registration wrapper for the ADR0305-ADR0307 bridge chain."""

from __future__ import annotations

from typing import Any

from exchange_terminal.services.static_presentation_asset_registration_v1 import (
    build_static_presentation_asset_registration_v1,
    verify_static_presentation_asset_registration_v1,
)


REGISTRATION_ID = (
    "portfolio-correlation-admission-effective-budget-bridge-v1"
)
GENERIC_REGISTRATION_IMPLEMENTATION_SHA256 = (
    "d833b998c2791a1b6c471108a74d770e1bebcb5957d8175373f2848b1cff8a90"
)
PROTECTED_STYLESHEET_SHA256 = (
    "ee6a5ae746142e32df768fe3261746f66c2b1a902e38b85fa9c0ecc4ce7bdc2a"
)
EXPECTED_REGISTRATION_HASH = (
    "265a897bb11a9d2df873f23a3faf5dc21bc4f66bb93ef8d313994e35938d04c4"
)
EXPECTED_SPEC_HASH = (
    "386556f5910ccc0e4c73c673f3e0c9a449fffae6992663aa61779a52504c3d6d"
)
EXPECTED_ASSET_MANIFEST_HASH = (
    "7212b36934cdb5a9ebc0b9f7a8515e7b4ca995f821330bfbb990d0ea3f35499f"
)

STAGE_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")
TIER_ORDER = (
    "INPUT_SNAPSHOT",
    "ADMISSION_V2_EXACT",
    "EFFECTIVE_BUDGET_V3_EXACT",
    "CROSS_SOURCE_BINDING",
    "ADMISSION_V2_DECISION",
    "EFFECTIVE_BUDGET_V3_DECISION",
    "PERMISSION",
)
COMMONJS_EXPORTS = (
    "BRIDGE_SCHEMA_VERSION",
    "BRIDGE_STATIC_FINGERPRINT",
    "STAGE_ORDER",
    "TIER_ORDER",
    "buildPortfolioCorrelationAdmissionEffectiveBudgetBridgeViewModelV1",
    "renderPortfolioCorrelationAdmissionEffectiveBudgetBridgeV1",
)
SCRIPT_LOAD_ORDER = (
    "strict_canonical_javascript",
    "binding_delivery_javascript",
    "binding_bridge_javascript",
)


def _asset(
    asset_id: str,
    path: str,
    sha256: str,
    role: str,
) -> dict[str, str]:
    return {
        "asset_id": asset_id,
        "path": path,
        "sha256": sha256,
        "role": role,
    }


def expected_portfolio_correlation_admission_effective_budget_bridge_asset_spec_v1(
) -> dict[str, Any]:
    return {
        "registration_id": REGISTRATION_ID,
        "source_contract": {
            "schema_version": (
                "portfolio-correlation-admission-effective-budget-binding-v1"
            ),
            "implementation_path": (
                "exchange_terminal/services/"
                "portfolio_correlation_admission_effective_budget_binding_v1.py"
            ),
            "implementation_sha256": (
                "7263b07df309ad3c2a4c79313e62ff8912c567ee0cf6a2ee9abdc336ce6bd9e9"
            ),
            "test_path": (
                "tests/"
                "test_portfolio_correlation_admission_effective_budget_binding_v1.py"
            ),
            "test_sha256": (
                "4d0b2e41b22b378df9b0e22bae9894ce8b62ff4c75743b8772a24881c33df00d"
            ),
            "adr_path": (
                "docs/adr/"
                "0305-portfolio-correlation-admission-effective-budget-binding-v1.md"
            ),
            "adr_sha256": (
                "f9d1488fd1e437a17c54cc47b3a4dd9a02084f725a88c83cb0920dabc3c9467a"
            ),
        },
        "assets": [
            _asset(
                "strict_canonical_javascript",
                "exchange_terminal/static/strict_canonical_json_v1.js",
                "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39",
                "production_dependency",
            ),
            _asset(
                "binding_delivery_python",
                (
                    "exchange_terminal/services/"
                    "portfolio_correlation_admission_effective_budget_"
                    "in_memory_delivery_v1.py"
                ),
                "9ada46b146fcecf48b96d9e5af1f4022ab23b4f0bbc5c1c39d59fb8d9a54d8db",
                "production",
            ),
            _asset(
                "binding_delivery_python_test",
                (
                    "tests/"
                    "test_portfolio_correlation_admission_effective_budget_"
                    "in_memory_delivery_v1.py"
                ),
                "d4b3e8a93aefe0eced326538d85ea49ffd8f6466098131a62a5b6bbb90716374",
                "verification",
            ),
            _asset(
                "binding_delivery_javascript",
                (
                    "exchange_terminal/static/"
                    "evidence_portfolio_correlation_admission_effective_budget_"
                    "in_memory_delivery_v1.js"
                ),
                "867f7a7016472101a3606f2af22ae7b63509cc2afb3d2dbfe8f7058da8e08be0",
                "production",
            ),
            _asset(
                "binding_delivery_node_test",
                (
                    "exchange_terminal/static/"
                    "evidence_portfolio_correlation_admission_effective_budget_"
                    "in_memory_delivery_v1.test.js"
                ),
                "ebf74408b34ec5ca1a2f539930289424684d0ec975b791f3577d3022f409425d",
                "verification",
            ),
            _asset(
                "adr0306",
                (
                    "docs/adr/"
                    "0306-portfolio-correlation-admission-effective-budget-"
                    "in-memory-delivery-v1.md"
                ),
                "2e545decd55a18425ac99a9d46b527127d4be0eb926f8c943087e52d6e347423",
                "decision",
            ),
            _asset(
                "binding_bridge_javascript",
                (
                    "exchange_terminal/static/"
                    "evidence_portfolio_correlation_admission_effective_budget_"
                    "bridge_v1.js"
                ),
                "67f16fa7946aee1c552b85bbb9758c84149a5cf657b7af5f78dad5ed0f7149d7",
                "production",
            ),
            _asset(
                "binding_bridge_stylesheet",
                (
                    "exchange_terminal/static/"
                    "evidence_portfolio_correlation_admission_effective_budget_"
                    "bridge_v1.css"
                ),
                "741d618c1fbfb76d0205e3ae3c9bff0b8b9bfacfa7f7cee6eb0e40b8761b2fc8",
                "presentation",
            ),
            _asset(
                "binding_bridge_node_test",
                (
                    "exchange_terminal/static/"
                    "evidence_portfolio_correlation_admission_effective_budget_"
                    "bridge_v1.test.js"
                ),
                "16de3ec284fa66e250e632c299ac8548be33ea1ec7a9fd02982881e938f72596",
                "verification",
            ),
            _asset(
                "adr0307",
                (
                    "docs/adr/"
                    "0307-portfolio-correlation-admission-effective-budget-"
                    "bridge-v1.md"
                ),
                "b889ef8cc0225ecaf870524a7e1a30b711a0186217922f5a5423e8a24c43224c",
                "decision",
            ),
        ],
        "consumer_contract": {
            "schema_version": (
                "portfolio-correlation-admission-effective-budget-bridge-v1"
            ),
            "static_fingerprint": (
                "20260823-portfolio-correlation-admission-effective-budget-"
                "bridge-v1-unmounted-lock-1"
            ),
            "browser_global": (
                "HakimiPortfolioCorrelationAdmissionEffectiveBudgetBridgeV1"
            ),
            "javascript_asset_id": "binding_bridge_javascript",
            "stylesheet_asset_id": "binding_bridge_stylesheet",
            "test_asset_id": "binding_bridge_node_test",
            "adr_asset_id": "adr0307",
            "expected_commonjs_exports": list(COMMONJS_EXPORTS),
            "script_load_order": list(SCRIPT_LOAD_ORDER),
            "stage_order": list(STAGE_ORDER),
            "tier_order": list(TIER_ORDER),
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
        "host_plan": {
            "app_importer": None,
            "html_script": None,
            "stylesheet_link": None,
            "mount_slot": None,
            "route": None,
            "browser_review_receipt": None,
        },
    }


def build_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1(
) -> dict[str, Any]:
    return build_static_presentation_asset_registration_v1(
        expected_portfolio_correlation_admission_effective_budget_bridge_asset_spec_v1()
    )


def verify_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1(
    document: Any,
) -> bool:
    return verify_static_presentation_asset_registration_v1(
        document,
        expected_portfolio_correlation_admission_effective_budget_bridge_asset_spec_v1(),
    )
