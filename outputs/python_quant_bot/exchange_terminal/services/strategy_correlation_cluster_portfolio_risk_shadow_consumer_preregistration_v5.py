"""Blocked shadow-consumer preregistration v5 with ADR0184/ADR0185 pins.

This module freezes successor implementation contracts. It deliberately accepts
no adapter, projection, DOM, browser, runtime, or trading evidence instance.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_adapter_v2 as adapter_v2_contract,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_projection_v2 as projection_v2_contract,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v4
    as preregistration_v4_contract,
)


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-shadow-consumer-preregistration-v5"
)
VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-shadow-consumer-preregistration-v5-verification-v1"
)
STATIC_FINGERPRINT = (
    "20260822-portfolio-risk-shadow-preregistration-v5-presentation-lock-1"
)
STATUS = "BLOCKED"
DECISION = (
    "SUCCESSOR_PREREGISTERED_ADR0184_ADR0185_CONTRACTS_PINNED_"
    "EVIDENCE_AND_UI_NOT_BOUND"
)

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_V4_CONTEXT_KEYS = {"preregistration_v3", "v3_verification_context"}
_NEW_IMPLEMENTATION_PINS = {
    "shadow_preregistration_v4": (
        "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v4.py",
        "ed767069e623b475f76e17d9188e2e543d878c30fe72d751b67962ebcc183c95",
    ),
    "portfolio_risk_adapter_v2": (
        "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_adapter_v2.py",
        "087e352819690066c5175ee19c4f49f729fe41f68ae14a589c454d9e4bb02e40",
    ),
    "portfolio_risk_projection_v2": (
        "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_projection_v2.py",
        "c4053b8730b7e5210b00ec2ac713152d9a4015f7728de5ae2e970b5025f98cac",
    ),
    "portfolio_risk_temporal_lattice_card_v2_js": (
        "exchange_terminal/static/evidence_portfolio_risk_temporal_lattice_card_v2.js",
        "d9cddae9e9bce501ada099ab21a5d7323c6d9ed33d789e2f60a8d87b363c0ae0",
    ),
    "portfolio_risk_temporal_lattice_card_v2_css": (
        "exchange_terminal/static/evidence_portfolio_risk_temporal_lattice_card_v2.css",
        "d71ed49d82cebecb4fb68d38789740aadac977a23b01d1ff4b15363f99c3bda3",
    ),
}


class ShadowConsumerPreregistrationV5ContractError(ValueError):
    """Raised when the immutable predecessor or a successor pin drifts."""


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ShadowConsumerPreregistrationV5ContractError(f"{label} must be a dict")
    return value


def _require_exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    result = _require_dict(value, label)
    if set(result) != expected:
        raise ShadowConsumerPreregistrationV5ContractError(
            f"{label} keys do not match schema"
        )
    return result


def _require_hash(value: Any, label: str) -> str:
    if type(value) is not str or _HASH_PATTERN.fullmatch(value) is None:
        raise ShadowConsumerPreregistrationV5ContractError(
            f"{label} must be lowercase sha256"
        )
    return value


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _seal(payload: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(payload)
    result["preregistration_hash"] = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    return result


def expected_shadow_consumer_implementation_sha256_v5() -> dict[str, str]:
    """Return the exact v4 chain plus ADR0184/ADR0185 presentation pins."""

    result = (
        preregistration_v4_contract.expected_shadow_consumer_implementation_sha256_v4()
    )
    result.update(
        {artifact_id: pin[1] for artifact_id, pin in _NEW_IMPLEMENTATION_PINS.items()}
    )
    return dict(sorted(result.items()))


def _verify_manifest(current_implementation_sha256: Any) -> dict[str, str]:
    supplied = _require_dict(
        current_implementation_sha256, "current_implementation_sha256"
    )
    expected = expected_shadow_consumer_implementation_sha256_v5()
    if set(supplied) != set(expected):
        raise ShadowConsumerPreregistrationV5ContractError(
            "implementation manifest must exactly match v5"
        )
    normalized: dict[str, str] = {}
    for artifact_id in sorted(expected):
        actual_hash = _require_hash(supplied[artifact_id], f"hash for {artifact_id}")
        if actual_hash != expected[artifact_id]:
            raise ShadowConsumerPreregistrationV5ContractError(
                f"implementation fingerprint drift for {artifact_id}"
            )
        normalized[artifact_id] = actual_hash
    return normalized


def _verify_v4_source(
    preregistration_v4: Any,
    v4_verification_context: Any,
    manifest: dict[str, str],
) -> dict[str, Any]:
    context = _require_exact_keys(
        v4_verification_context, _V4_CONTEXT_KEYS, "v4_verification_context"
    )
    v4_manifest_keys = set(
        preregistration_v4_contract.expected_shadow_consumer_implementation_sha256_v4()
    )
    v4_manifest = {key: manifest[key] for key in v4_manifest_keys}
    verification = preregistration_v4_contract.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v4(
        preregistration_v4,
        context["preregistration_v3"],
        context["v3_verification_context"],
        v4_manifest,
    )
    if (
        type(verification) is not dict
        or verification.get("status") != "PASS"
        or verification.get("preregistration_exactly_verified") is not True
        or verification.get("preregistration_status") != "BLOCKED"
    ):
        raise ShadowConsumerPreregistrationV5ContractError(
            "immutable v4 public re-verification failed"
        )
    source = _require_dict(preregistration_v4, "preregistration_v4")
    if (
        source.get("schema_version") != preregistration_v4_contract.SCHEMA_VERSION
        or source.get("static_fingerprint")
        != preregistration_v4_contract.STATIC_FINGERPRINT
        or source.get("status") != "BLOCKED"
    ):
        raise ShadowConsumerPreregistrationV5ContractError(
            "immutable v4 source state mismatch"
        )
    _require_hash(source.get("preregistration_hash"), "v4 preregistration_hash")
    closed = source.get("closed_local_blockers")
    if type(closed) is not list or len(closed) != 3:
        raise ShadowConsumerPreregistrationV5ContractError(
            "immutable v4 local closure count drifted"
        )
    capabilities = source.get("newly_pinned_local_capabilities")
    if type(capabilities) is not list or len(capabilities) != 2:
        raise ShadowConsumerPreregistrationV5ContractError(
            "immutable v4 capability pins drifted"
        )
    readiness_pin = capabilities[-1]
    if (
        readiness_pin.get("capability")
        != "PORTFOLIO_RISK_SHADOW_INPUT_READINESS_ENVELOPE_V3"
        or readiness_pin.get("contract_pinned") is not True
        or readiness_pin.get("evidence_bound") is not False
        or readiness_pin.get("consumer_executed") is not False
        or readiness_pin.get("external_authority_verified") is not False
    ):
        raise ShadowConsumerPreregistrationV5ContractError(
            "immutable v4 readiness pin drifted"
        )
    authority = _require_dict(source.get("authority"), "v4 authority")
    if authority.get("descriptive_only") is not True or any(
        value is not False
        for key, value in authority.items()
        if key != "descriptive_only"
    ):
        raise ShadowConsumerPreregistrationV5ContractError(
            "immutable v4 authority was inflated"
        )
    return source


def build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v5(
    preregistration_v4: Any,
    v4_verification_context: Any,
    current_implementation_sha256: Any,
) -> dict[str, Any]:
    """Pin ADR0184/ADR0185 without accepting their evidence instances."""

    manifest = _verify_manifest(current_implementation_sha256)
    source = _verify_v4_source(preregistration_v4, v4_verification_context, manifest)

    artifacts = copy.deepcopy(source["source"]["artifacts"])
    existing_ids = {item["artifact_id"] for item in artifacts}
    for artifact_id, (path, expected_hash) in _NEW_IMPLEMENTATION_PINS.items():
        if artifact_id not in existing_ids:
            artifacts.append(
                {
                    "artifact_id": artifact_id,
                    "path": path,
                    "expected_sha256": expected_hash,
                }
            )

    capabilities = copy.deepcopy(source["newly_pinned_local_capabilities"])
    capabilities.append(
        {
            "capability": (
                "PORTFOLIO_RISK_TEMPORAL_STABILITY_PUBLIC_PRESENTATION_V2"
            ),
            "pin": (
                "ADR0184_ADAPTER_V2_AND_ADR0185_PROJECTION_CARD_"
                "IMPLEMENTATIONS_PINNED_EVIDENCE_NOT_BOUND"
            ),
            "contract_pinned": True,
            "evidence_bound": False,
            "consumer_executed": False,
            "external_authority_verified": False,
        }
    )

    blockers = list(source["blockers"])
    for blocker in (
        "portfolio_risk_adapter_v2_evidence_not_bound",
        "portfolio_risk_adapter_v2_exact_hash_not_verified",
        "portfolio_risk_projection_v2_evidence_not_bound",
        "portfolio_risk_projection_v2_exact_hash_not_verified",
        "presentation_consumer_v2_not_registered",
        "temporal_lattice_card_v2_dom_not_reviewed",
        "browser_visual_review_not_performed",
        "presentation_http_contract_v2_not_versioned",
    ):
        if blocker not in blockers:
            blockers.append(blocker)

    facts = copy.deepcopy(source["facts"])
    facts.update(
        {
            "immutable_v4_exactly_verified": True,
            "portfolio_risk_adapter_v2_contract_pinned": True,
            "portfolio_risk_adapter_v2_evidence_bound": False,
            "portfolio_risk_adapter_v2_exactly_verified": False,
            "portfolio_risk_projection_v2_contract_pinned": True,
            "portfolio_risk_projection_v2_evidence_bound": False,
            "portfolio_risk_projection_v2_exactly_verified": False,
            "temporal_lattice_card_v2_javascript_pinned": True,
            "temporal_lattice_card_v2_stylesheet_pinned": True,
            "presentation_consumer_v2_registered": False,
            "presentation_http_contract_v2_versioned": False,
            "dom_contract_reviewed": False,
            "browser_visual_review_performed": False,
            "shadow_application_consumer_implemented": False,
            "shadow_consumer_executed": False,
            "risk_service_invoked": False,
            "runtime_assets_accessed": False,
            "server_route_registered": False,
            "ui_mounted": False,
        }
    )

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": STATUS,
        "decision": DECISION,
        "source": {
            "immutable_v4_exactly_verified": True,
            "immutable_v4_schema_version": source["schema_version"],
            "immutable_v4_preregistration_hash": source["preregistration_hash"],
            "immutable_v4_implementation_sha256": manifest[
                "shadow_preregistration_v4"
            ],
            "successor_manifest_contract_verified": True,
            "successor_implementation_fingerprints_match": True,
            "artifacts": artifacts,
        },
        "contract_pins": {
            "immutable_v4_schema_version": source["schema_version"],
            "immutable_v4_preregistration_hash": source["preregistration_hash"],
            "immutable_v4_contract_pins": copy.deepcopy(source["contract_pins"]),
            "adapter_v2_schema_version": adapter_v2_contract.SCHEMA_VERSION,
            "adapter_v2_static_fingerprint": adapter_v2_contract.STATIC_FINGERPRINT,
            "adapter_v2_implementation_sha256": manifest[
                "portfolio_risk_adapter_v2"
            ],
            "projection_v2_schema_version": (
                projection_v2_contract.PROJECTION_SCHEMA_VERSION
            ),
            "projection_v2_verification_schema_version": (
                projection_v2_contract.PROJECTION_VERIFICATION_SCHEMA_VERSION
            ),
            "projection_v2_static_fingerprint": (
                projection_v2_contract.STATIC_FINGERPRINT
            ),
            "projection_v2_implementation_sha256": manifest[
                "portfolio_risk_projection_v2"
            ],
            "temporal_lattice_card_v2_projection_schema_version": (
                projection_v2_contract.PROJECTION_SCHEMA_VERSION
            ),
            "temporal_lattice_card_v2_static_fingerprint": (
                projection_v2_contract.STATIC_FINGERPRINT
            ),
            "temporal_lattice_card_v2_global_name": (
                "HakimiPortfolioRiskTemporalLatticeCardV2"
            ),
            "temporal_lattice_card_v2_javascript_sha256": manifest[
                "portfolio_risk_temporal_lattice_card_v2_js"
            ],
            "temporal_lattice_card_v2_stylesheet_sha256": manifest[
                "portfolio_risk_temporal_lattice_card_v2_css"
            ],
            "presentation_binding_policy": (
                "EXACT_ADAPTER_V2_AND_PROJECTION_V2_PUBLIC_REVERIFICATION_"
                "PLUS_ISOLATED_DOM_REVIEW_REQUIRED_V1"
            ),
        },
        "required_shadow_input_schemas": copy.deepcopy(
            source["required_shadow_input_schemas"]
        ),
        "closed_local_blockers": copy.deepcopy(source["closed_local_blockers"]),
        "newly_pinned_local_capabilities": capabilities,
        "blocker_refinements": copy.deepcopy(source["blocker_refinements"]),
        "blockers": blockers,
        "facts": facts,
        "reuse_plan": copy.deepcopy(source["reuse_plan"]),
        "activation_order": [
            "BIND_AUTHENTICATED_PROVIDER_IDENTITY_KEY_CONTROL_AND_DATA_ISSUANCE",
            "SUPPLY_EXACT_ADR0176_REGISTRATION_CHECKPOINT_PROOFS_AND_AUDIT",
            "VERIFY_EXTERNAL_CONTENT_REPLAY_REGISTRY_AUTHORITY_AND_DURABLE_PUBLICATION",
            "AUTHENTICATE_EXTERNAL_TIME_AUTHORITY_FOR_FRESHNESS_REFERENCE",
            "SUPPLY_AND_EXACTLY_VERIFY_ADR0181_READINESS_ENVELOPE",
            "BIND_DURABLE_TRUSTED_CLOCK_NONCE_AND_REPLAY_ENFORCEMENT",
            "IMPLEMENT_ISOLATED_APPLICATION_SHADOW_CONSUMER_V5",
            "INDEPENDENTLY_REVIEW_SYNTHETIC_SHADOW_CALLS",
            "BIND_AND_EXACTLY_VERIFY_ADR0184_PORTFOLIO_RISK_ADAPTER_V2_EVIDENCE",
            "BIND_AND_EXACTLY_VERIFY_ADR0185_PUBLIC_PROJECTION_V2_EVIDENCE",
            "IMPLEMENT_UNREGISTERED_PRESENTATION_CONSUMER_FIXTURE_V2",
            "AUTHORIZE_ISOLATED_DOM_AND_BROWSER_VISUAL_REVIEW",
            "VERSION_RISK_SERVICE_INPUT_CONTRACT",
            "VERSION_PRESENTATION_HTTP_CONTRACT_BEFORE_MOUNT",
            "SEPARATELY_AUTHORIZE_CURRENT_SWITCH",
        ],
        "authority": copy.deepcopy(source["authority"]),
    }
    return _seal(payload)


def verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v5(
    document: Any,
    preregistration_v4: Any,
    v4_verification_context: Any,
    current_implementation_sha256: Any,
) -> dict[str, Any]:
    """Rebuild preregistration v5 and return a fail-closed result."""

    blockers: list[str] = []
    try:
        rebuilt = build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v5(
            preregistration_v4,
            v4_verification_context,
            current_implementation_sha256,
        )
        exactly_verified = type(document) is dict and document == rebuilt
        if not exactly_verified:
            blockers.append("PREREGISTRATION_V5_EXACT_REBUILD_MISMATCH")
    except (ShadowConsumerPreregistrationV5ContractError, ValueError, TypeError):
        exactly_verified = False
        blockers.append("PREREGISTRATION_V5_SOURCE_OR_MANIFEST_UNVERIFIED")

    authority = document.get("authority", {}) if type(document) is dict else {}
    authority_denied = (
        type(authority) is dict
        and authority.get("descriptive_only") is True
        and all(
            value is False
            for key, value in authority.items()
            if key != "descriptive_only"
        )
    )
    if not authority_denied:
        blockers.append("PREREGISTRATION_V5_AUTHORITY_NOT_FAIL_CLOSED")
    passed = exactly_verified and authority_denied
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if passed else "FAIL",
        "preregistration_exactly_verified": exactly_verified,
        "preregistration_status": (
            document.get("status") if type(document) is dict else None
        ),
        "blockers": blockers,
        "shadow_consumer_activation_allowed": False,
        "presentation_consumer_activation_allowed": False,
        "runtime_gate_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "DECISION",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "STATUS",
    "ShadowConsumerPreregistrationV5ContractError",
    "VERIFICATION_SCHEMA_VERSION",
    "build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v5",
    "expected_shadow_consumer_implementation_sha256_v5",
    "verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v5",
]
