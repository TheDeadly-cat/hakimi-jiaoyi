"""Static registration candidate for the unmounted freshness presentation."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_projection_v3 as projection_v3,
)


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-consumer-"
    "registration-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260822-portfolio-risk-presentation-consumer-registration-lock-1"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
STATUS = "BLOCKED"
DECISION = (
    "UNMOUNTED_PRESENTATION_CONSUMER_REGISTRATION_CANDIDATE_BUILT_"
    "EVIDENCE_DOM_BROWSER_HTTP_AND_ACTIVATION_NOT_BOUND"
)
STAGE_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")

_EXPECTED_IMPLEMENTATION_SHA256 = {
    "portfolio_risk_projection_v3": (
        "a983593e70f7dfd707c4933e41422335ccb7825f84c1c689339518e47186f1bf"
    ),
    "portfolio_risk_freshness_gate_card_v3_js": (
        "0999f934aafe7bcb193e99bfe36362dbc2a91f2015c7d131ce7fb3b252e36f29"
    ),
    "portfolio_risk_freshness_gate_card_v3_css": (
        "a3ee5f96e6c73aee7211c8f54474a84cbf02b515dcb8fee384dfaebfbd8f2ba8"
    ),
    "portfolio_risk_freshness_gate_consumer_fixture_v3_js": (
        "6e9c1da54ed9ee6e8d5ba70d1473d920c67b0c0534bb9110cafb604518430b0d"
    ),
}

_ARTIFACT_PATHS = {
    "portfolio_risk_projection_v3": (
        "exchange_terminal/services/"
        "strategy_correlation_cluster_portfolio_risk_projection_v3.py"
    ),
    "portfolio_risk_freshness_gate_card_v3_js": (
        "exchange_terminal/static/"
        "evidence_portfolio_risk_freshness_gate_card_v3.js"
    ),
    "portfolio_risk_freshness_gate_card_v3_css": (
        "exchange_terminal/static/"
        "evidence_portfolio_risk_freshness_gate_card_v3.css"
    ),
    "portfolio_risk_freshness_gate_consumer_fixture_v3_js": (
        "exchange_terminal/static/"
        "evidence_portfolio_risk_freshness_gate_consumer_fixture_v3.js"
    ),
}

_BLOCKERS = (
    "projection_v3_evidence_not_bound",
    "consumer_fixture_v3_execution_evidence_not_bound",
    "isolated_dom_contract_review_not_performed",
    "browser_visual_review_not_performed",
    "presentation_http_contract_not_versioned",
    "presentation_consumer_registration_activation_unauthorized",
    "presentation_mount_unauthorized",
    "current_switch_unauthorized",
)


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def expected_presentation_consumer_implementation_sha256_v1() -> dict[str, str]:
    return dict(_EXPECTED_IMPLEMENTATION_SHA256)


def build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v1(
    current_implementation_sha256: Any,
) -> dict[str, Any]:
    manifest_exact = bool(
        type(current_implementation_sha256) is dict
        and current_implementation_sha256 == _EXPECTED_IMPLEMENTATION_SHA256
    )
    blockers = list(_BLOCKERS)
    if not manifest_exact:
        blockers.insert(0, "implementation_manifest_mismatch")

    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": STATUS,
        "decision": DECISION if manifest_exact else "REGISTRATION_INPUT_INVALID_FAIL_CLOSED",
        "source": {
            "implementation_manifest_contract_verified": manifest_exact,
            "implementation_fingerprints_match": manifest_exact,
            "implementation_pin_count": len(_EXPECTED_IMPLEMENTATION_SHA256),
            "artifacts": [
                {
                    "artifact_id": artifact_id,
                    "path": _ARTIFACT_PATHS[artifact_id],
                    "expected_sha256": expected_sha256,
                }
                for artifact_id, expected_sha256 in sorted(
                    _EXPECTED_IMPLEMENTATION_SHA256.items()
                )
            ],
        },
        "contract_pins": {
            "projection_schema_version": projection_v3.SCHEMA_VERSION,
            "projection_static_fingerprint": projection_v3.STATIC_FINGERPRINT,
            "projection_verification_schema_version": (
                projection_v3.VERIFICATION_SCHEMA_VERSION
            ),
            "projection_implementation_sha256": _EXPECTED_IMPLEMENTATION_SHA256[
                "portfolio_risk_projection_v3"
            ],
            "card_schema_version": "portfolio-risk-freshness-gate-card-v3",
            "card_static_fingerprint": (
                "20260822-portfolio-risk-freshness-gate-card-lock-1"
            ),
            "card_global_name": "HakimiPortfolioRiskFreshnessGateCardV3",
            "card_javascript_sha256": _EXPECTED_IMPLEMENTATION_SHA256[
                "portfolio_risk_freshness_gate_card_v3_js"
            ],
            "card_stylesheet_sha256": _EXPECTED_IMPLEMENTATION_SHA256[
                "portfolio_risk_freshness_gate_card_v3_css"
            ],
            "consumer_fixture_schema_version": (
                "portfolio-risk-freshness-presentation-consumer-fixture-v3"
            ),
            "consumer_fixture_static_fingerprint": (
                "20260822-portfolio-risk-freshness-consumer-fixture-lock-1"
            ),
            "consumer_fixture_global_name": (
                "HakimiPortfolioRiskFreshnessGateConsumerFixtureV3"
            ),
            "consumer_fixture_javascript_sha256": _EXPECTED_IMPLEMENTATION_SHA256[
                "portfolio_risk_freshness_gate_consumer_fixture_v3_js"
            ],
            "stage_order": list(STAGE_ORDER),
            "composition_policy": (
                "EXACT_PROJECTION_V3_TO_STRICT_CARD_V3_TO_DEEP_FROZEN_"
                "UNMOUNTED_DESCRIPTOR_V1"
            ),
            "mount_policy": "NO_DOM_TARGET_NO_SELECTOR_NO_MOUNT_API_V1",
            "permission_policy": "ALWAYS_UNAUTHORIZED_V1",
        },
        "consumer": {
            "consumer_id": "portfolio-risk-freshness-gate-v3",
            "input_schema_version": projection_v3.SCHEMA_VERSION,
            "output_schema_version": (
                "portfolio-risk-freshness-presentation-consumer-fixture-v3"
            ),
            "stage_order": list(STAGE_ORDER),
            "registration_state": "CANDIDATE_ONLY",
            "execution_mode": "UNMOUNTED_RENDER_DESCRIPTOR_ONLY",
            "dom_target": None,
            "selector": None,
        },
        "blockers": blockers,
        "activation_order": [
            "BIND_AND_EXACTLY_VERIFY_PROJECTION_V3_EVIDENCE",
            "EXECUTE_FIXTURE_V3_WITH_SYNTHETIC_PROJECTION_MATRIX",
            "INDEPENDENTLY_REVIEW_FIXTURE_V3_RENDER_DESCRIPTOR",
            "AUTHORIZE_ISOLATED_DOM_CONTRACT_REVIEW",
            "AUTHORIZE_BROWSER_VISUAL_REVIEW",
            "VERSION_PRESENTATION_HTTP_CONTRACT_BEFORE_MOUNT",
            "SEPARATELY_AUTHORIZE_PRESENTATION_CONSUMER_REGISTRATION",
            "SEPARATELY_AUTHORIZE_PRESENTATION_MOUNT",
            "SEPARATELY_AUTHORIZE_CURRENT_SWITCH",
        ],
        "facts": {
            "registration_candidate_built": manifest_exact,
            "registration_activated": False,
            "projection_contract_pinned": manifest_exact,
            "card_javascript_pinned": manifest_exact,
            "card_stylesheet_pinned": manifest_exact,
            "consumer_fixture_javascript_pinned": manifest_exact,
            "projection_evidence_bound": False,
            "consumer_fixture_executed": False,
            "render_descriptor_reviewed": False,
            "dom_contract_reviewed": False,
            "browser_visual_review_performed": False,
            "presentation_http_contract_versioned": False,
            "profitability_proven": False,
            "runtime_assets_accessed": False,
            "runtime_consumer_bound": False,
            "server_route_registered": False,
            "ui_mounted": False,
        },
        "authority": {
            "descriptive_only": True,
            "current_admission_allowed": False,
            "current_pointer_written": False,
            "live_order_allowed": False,
            "migration_allowed": False,
            "paper_authorized": False,
            "presentation_consumer_activation_allowed": False,
            "presentation_mount_allowed": False,
            "runtime_gate_activation_allowed": False,
            "shadow_consumer_activation_allowed": False,
            "writer_allowed": False,
        },
    }
    document["registration_hash"] = _canonical_hash(document)
    return document


def verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v1(
    document: Any,
    current_implementation_sha256: Any,
) -> dict[str, Any]:
    expected = build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v1(
        current_implementation_sha256
    )
    exact = bool(type(document) is dict and document == expected)
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "registration_exactly_verified": exact,
        "registration_status": expected.get("status") if exact else "UNKNOWN",
        "registration_activated": False,
        "blockers": [] if exact else ["registration_v1_exact_rebuild"],
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_consumer_activation_allowed": False,
        "presentation_mount_allowed": False,
        "runtime_gate_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
        "writer_allowed": False,
    }


__all__ = [
    "DECISION",
    "SCHEMA_VERSION",
    "STAGE_ORDER",
    "STATIC_FINGERPRINT",
    "STATUS",
    "VERIFICATION_SCHEMA_VERSION",
    "build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v1",
    "expected_presentation_consumer_implementation_sha256_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v1",
]
