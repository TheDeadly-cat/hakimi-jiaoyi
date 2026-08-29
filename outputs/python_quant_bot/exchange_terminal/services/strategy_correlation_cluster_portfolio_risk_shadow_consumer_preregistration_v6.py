"""Immutable shadow-consumer preregistration v6 for ADR0187-ADR0190 pins."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v1
    as lineage_v1,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v2
    as lineage_v2,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_adapter_v3 as adapter_v3,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_projection_v3 as projection_v3,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v5
    as preregistration_v5,
)


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-shadow-consumer-"
    "preregistration-v6"
)
STATIC_FINGERPRINT = (
    "20260822-portfolio-risk-shadow-preregistration-v6-"
    "freshness-presentation-lock-1"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
STATUS = "BLOCKED"
DECISION = (
    "SUCCESSOR_PREREGISTERED_ADR0187_TO_ADR0190_CONTRACTS_PINNED_"
    "EVIDENCE_DOM_BROWSER_AND_ACTIVATION_NOT_BOUND"
)
V5_VERIFICATION_CONTEXT_KEYS = frozenset(
    {
        "preregistration_v4",
        "v4_verification_context",
        "v5_implementation_sha256",
    }
)

_EXPECTED_IMPLEMENTATION_SHA256 = {
    "adapter_v1": "e3154743d7fb74a79d600b948f84c53a2a8666b13b0fc1cd00e9eca5590e8cee",
    "calendar_provider_composition_v1": "922e626c72c3eb6be64a7a7d07ea0339655318eacac44a5121370cf8e11b1197",
    "dataset_content_attestation_v1": "91dcad9660f379c47c2e912bda5032cbabc72dc5af8c42ece2ea3bede19bc654",
    "dataset_content_issuance_replay_gate_v1": "9832b2c8375bc814107cd1769264667c362b1eb1b9eda3533abb1f373c25371e",
    "dataset_key_lifecycle_gate_v1": "c779ef769383935dec7b9a9a81ea896ccf505144e0ce1bec46f39fc840c19369",
    "dataset_key_lifecycle_replay_gate_v1": "a34bdc06efe5c68e38955a4c7698c53587257f1cdd13482afd70f14a872a1c27",
    "dual_source_receipt_v1": "728f6230e00eddd40eca137d5c736d83537e516f7568d4bbc24dd90f8ae4f612",
    "legacy_matrix_derivation_binding_v1": "144ec7b141dd96362c7f58bafd745243945b9afa2e0774ef7e95b03586235890",
    "legacy_portfolio_risk_v1": "a97042a0265cc6bc552c8a818feadfd26e917b7eb75e36f9d4b8ca924717af19",
    "legacy_shadow_service_v1": "c7e6010e8fa6eaa0e6b1ba081c80cced224a55100804aec57ac28376837a3111",
    "native_cutoff_manifest_v1": "cc79e280d7e4d25e33c66bfa65b577fbe924a1e5008e81fbcd53cea2f5c11a1c",
    "portfolio_risk_adapter_v2": "087e352819690066c5175ee19c4f49f729fe41f68ae14a589c454d9e4bb02e40",
    "portfolio_risk_projection_v2": "c4053b8730b7e5210b00ec2ac713152d9a4015f7728de5ae2e970b5025f98cac",
    "portfolio_risk_temporal_lattice_card_v2_css": "d71ed49d82cebecb4fb68d38789740aadac977a23b01d1ff4b15363f99c3bda3",
    "portfolio_risk_temporal_lattice_card_v2_js": "d9cddae9e9bce501ada099ab21a5d7323c6d9ed33d789e2f60a8d87b363c0ae0",
    "projection_v1": "46e45b030edd45d2b9f145924c6d673df4e59ab5c960c693236987b6dd1dd084",
    "risk_service": "6dc4ca89e61ae5907129f8307166a1ae84afd85b74924ee2b0f82106d7681244",
    "session_freshness_v1": "2bacefd4b3649ccbba8e254a0e8f8c176d08e458744f74dc19145fb6d5363299",
    "shadow_input_readiness_envelope_v1": "4bd1743df7e359636a96338b1d6fafdfcf406e9441af8380b60fcc59a55c8671",
    "shadow_input_readiness_envelope_v2": "92d9848682fe68b8ca55b82be8cff46665593e6c6c68d963d04f60f811da60c6",
    "shadow_input_readiness_envelope_v3": "f76b454730d4da9430129c50f9fc4bb81894f7ee66ce440c493d4ecce273a584",
    "shadow_preregistration_v1": "105ec897334bbf181f677c6cdcf88ae95cb6942dc408877a3437589ff28666d6",
    "shadow_preregistration_v2": "e4ab1097ae47d11bde2674976abe521d7f335f662b5c8c1f8786ad7eb41a653a",
    "shadow_preregistration_v3": "ecd0affef70ac6461deabab8b0c00db94265eb175bf87c0c066deaa1d051bd36",
    "shadow_preregistration_v4": "ed767069e623b475f76e17d9188e2e543d878c30fe72d751b67962ebcc183c95",
    "trusted_clock_authority_v3": "9a12682fb00dee3d6851ac62d4a37de0c66992e3f57d8e9715e23712d25a8c62",
    "shadow_preregistration_v5": "eca0023fa6b674ad3a1fe17178922bb9b6829d12abf52be69e1c63fbba0c7aa7",
    "portfolio_risk_adapter_v2_session_freshness_lineage_binding_v1": "5d5ae9d445c3bbc519b63f3eed424a98ee4e2f5b39d28e03aec5901491e2fbc5",
    "portfolio_risk_adapter_v2_session_freshness_lineage_binding_v2": "3853c5b1e22dfb2c5c0429203503de9fe70650872ebe8bbfecbde19df69eac28",
    "portfolio_risk_adapter_v3": "fc9faaf1c4366593e004b4c8e798f5cefafaaf985687c3f7bf7a44fd6e663fe7",
    "portfolio_risk_projection_v3": "a983593e70f7dfd707c4933e41422335ccb7825f84c1c689339518e47186f1bf",
    "portfolio_risk_freshness_gate_card_v3_js": "0999f934aafe7bcb193e99bfe36362dbc2a91f2015c7d131ce7fb3b252e36f29",
    "portfolio_risk_freshness_gate_card_v3_css": "a3ee5f96e6c73aee7211c8f54474a84cbf02b515dcb8fee384dfaebfbd8f2ba8",
}

_NEW_ARTIFACTS = (
    (
        "shadow_preregistration_v5",
        "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v5.py",
    ),
    (
        "portfolio_risk_adapter_v2_session_freshness_lineage_binding_v1",
        "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v1.py",
    ),
    (
        "portfolio_risk_adapter_v2_session_freshness_lineage_binding_v2",
        "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v2.py",
    ),
    (
        "portfolio_risk_adapter_v3",
        "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_adapter_v3.py",
    ),
    (
        "portfolio_risk_projection_v3",
        "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_projection_v3.py",
    ),
    (
        "portfolio_risk_freshness_gate_card_v3_js",
        "exchange_terminal/static/evidence_portfolio_risk_freshness_gate_card_v3.js",
    ),
    (
        "portfolio_risk_freshness_gate_card_v3_css",
        "exchange_terminal/static/evidence_portfolio_risk_freshness_gate_card_v3.css",
    ),
)

_NEW_BLOCKERS = (
    "adapter_v2_freshness_lineage_v2_evidence_not_bound",
    "portfolio_risk_adapter_v3_evidence_not_bound",
    "portfolio_risk_projection_v3_evidence_not_bound",
    "freshness_gate_card_v3_dom_not_reviewed",
    "browser_visual_review_v3_not_performed",
    "presentation_http_contract_v3_not_versioned",
)


def _dict(value: Any) -> dict[str, Any]:
    return value if type(value) is dict else {}


def _list(value: Any) -> list[Any]:
    return value if type(value) is list else []


def _strict_sha256(value: Any) -> str | None:
    if type(value) is not str or len(value) != 64:
        return None
    if any(char not in "0123456789abcdef" for char in value):
        return None
    return value


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def expected_shadow_consumer_implementation_sha256_v6() -> dict[str, str]:
    return dict(_EXPECTED_IMPLEMENTATION_SHA256)


def _exact_v5_context(value: Any) -> dict[str, Any] | None:
    if type(value) is not dict or set(value) != V5_VERIFICATION_CONTEXT_KEYS:
        return None
    return value


def _verify_v5(document: Any, context: dict[str, Any] | None) -> dict[str, Any]:
    if context is None:
        return {}
    try:
        return preregistration_v5.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v5(
            document,
            context["preregistration_v4"],
            context["v4_verification_context"],
            context["v5_implementation_sha256"],
        )
    except Exception:
        return {}


def _authority_locked(value: Any) -> bool:
    authority = _dict(value)
    return bool(authority) and all(
        authority.get(key) is False
        for key in (
            "current_admission_allowed",
            "current_pointer_written",
            "formal_registry_activation_allowed",
            "live_order_allowed",
            "migration_allowed",
            "paper_authorized",
            "runtime_gate_activation_allowed",
            "shadow_consumer_activation_allowed",
            "writer_allowed",
        )
    )


def build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v6(
    preregistration_v5_document: Any,
    v5_verification_context: Any,
    current_implementation_sha256: Any,
) -> dict[str, Any]:
    context = _exact_v5_context(v5_verification_context)
    predecessor = _dict(preregistration_v5_document)
    receipt = _verify_v5(preregistration_v5_document, context)
    predecessor_exact = bool(
        context is not None
        and receipt.get("status") == "PASS"
        and receipt.get("preregistration_exactly_verified") is True
        and receipt.get("preregistration_status") == "BLOCKED"
        and predecessor.get("schema_version") == preregistration_v5.SCHEMA_VERSION
        and predecessor.get("static_fingerprint")
        == preregistration_v5.STATIC_FINGERPRINT
        and predecessor.get("status") == preregistration_v5.STATUS
        and _strict_sha256(predecessor.get("preregistration_hash"))
        and _authority_locked(predecessor.get("authority"))
        and all(
            receipt.get(key) is False
            for key in (
                "current_admission_allowed",
                "live_order_allowed",
                "paper_authorized",
                "presentation_consumer_activation_allowed",
                "runtime_gate_activation_allowed",
                "shadow_consumer_activation_allowed",
            )
        )
    )
    manifest_exact = bool(
        type(current_implementation_sha256) is dict
        and current_implementation_sha256 == _EXPECTED_IMPLEMENTATION_SHA256
    )
    inputs_valid = predecessor_exact and manifest_exact

    predecessor_blockers = (
        copy.deepcopy(_list(predecessor.get("blockers")))
        if predecessor_exact
        else []
    )
    blockers = predecessor_blockers + list(_NEW_BLOCKERS)
    if not predecessor_exact:
        blockers.insert(0, "immutable_v5_exact_verification_failed")
    if not manifest_exact:
        blockers.insert(0, "successor_implementation_manifest_mismatch")

    predecessor_order = (
        copy.deepcopy(_list(predecessor.get("activation_order")))
        if predecessor_exact
        else []
    )
    current_step = "SEPARATELY_AUTHORIZE_CURRENT_SWITCH"
    if predecessor_order and predecessor_order[-1] == current_step:
        predecessor_order = predecessor_order[:-1]
    activation_order = predecessor_order + [
        "BIND_AND_EXACTLY_VERIFY_ADR0188_LINEAGE_V2_EVIDENCE",
        "BIND_AND_EXACTLY_VERIFY_ADR0189_ADAPTER_V3_EVIDENCE",
        "BIND_AND_EXACTLY_VERIFY_ADR0190_PROJECTION_V3_EVIDENCE",
        "REGISTER_UNMOUNTED_PRESENTATION_CONSUMER_FIXTURE_V3",
        "AUTHORIZE_ISOLATED_DOM_AND_BROWSER_VISUAL_REVIEW_V3",
        "VERSION_PRESENTATION_HTTP_CONTRACT_V3_BEFORE_MOUNT",
        current_step,
    ]

    new_artifacts = [
        {
            "artifact_id": artifact_id,
            "path": path,
            "expected_sha256": _EXPECTED_IMPLEMENTATION_SHA256[artifact_id],
        }
        for artifact_id, path in _NEW_ARTIFACTS
    ]
    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": STATUS,
        "decision": DECISION if inputs_valid else "PREREGISTRATION_INPUT_INVALID_FAIL_CLOSED",
        "source": {
            "immutable_v5_schema_version": (
                predecessor.get("schema_version") if predecessor_exact else "UNKNOWN"
            ),
            "immutable_v5_preregistration_hash": (
                predecessor.get("preregistration_hash") if predecessor_exact else None
            ),
            "immutable_v5_implementation_sha256": (
                _EXPECTED_IMPLEMENTATION_SHA256["shadow_preregistration_v5"]
            ),
            "immutable_v5_exactly_verified": predecessor_exact,
            "successor_manifest_contract_verified": manifest_exact,
            "successor_implementation_fingerprints_match": manifest_exact,
            "total_implementation_pin_count": len(_EXPECTED_IMPLEMENTATION_SHA256),
            "new_artifacts": new_artifacts,
        },
        "contract_pins": {
            "immutable_v5_schema_version": preregistration_v5.SCHEMA_VERSION,
            "immutable_v5_static_fingerprint": preregistration_v5.STATIC_FINGERPRINT,
            "immutable_v5_preregistration_hash": (
                predecessor.get("preregistration_hash") if predecessor_exact else None
            ),
            "immutable_v5_contract_pins": (
                copy.deepcopy(_dict(predecessor.get("contract_pins")))
                if predecessor_exact
                else {}
            ),
            "lineage_binding_v1_schema_version": lineage_v1.BINDING_SCHEMA_VERSION,
            "lineage_binding_v1_static_fingerprint": lineage_v1.STATIC_FINGERPRINT,
            "lineage_binding_v1_implementation_sha256": _EXPECTED_IMPLEMENTATION_SHA256[
                "portfolio_risk_adapter_v2_session_freshness_lineage_binding_v1"
            ],
            "lineage_binding_v2_schema_version": lineage_v2.BINDING_SCHEMA_VERSION,
            "lineage_binding_v2_static_fingerprint": lineage_v2.STATIC_FINGERPRINT,
            "lineage_binding_v2_implementation_sha256": _EXPECTED_IMPLEMENTATION_SHA256[
                "portfolio_risk_adapter_v2_session_freshness_lineage_binding_v2"
            ],
            "adapter_v3_schema_version": adapter_v3.SCHEMA_VERSION,
            "adapter_v3_static_fingerprint": adapter_v3.STATIC_FINGERPRINT,
            "adapter_v3_verification_schema_version": adapter_v3.VERIFICATION_SCHEMA_VERSION,
            "adapter_v3_implementation_sha256": _EXPECTED_IMPLEMENTATION_SHA256[
                "portfolio_risk_adapter_v3"
            ],
            "projection_v3_schema_version": projection_v3.SCHEMA_VERSION,
            "projection_v3_static_fingerprint": projection_v3.STATIC_FINGERPRINT,
            "projection_v3_verification_schema_version": projection_v3.VERIFICATION_SCHEMA_VERSION,
            "projection_v3_implementation_sha256": _EXPECTED_IMPLEMENTATION_SHA256[
                "portfolio_risk_projection_v3"
            ],
            "freshness_gate_card_v3_global_name": (
                "HakimiPortfolioRiskFreshnessGateCardV3"
            ),
            "freshness_gate_card_v3_schema_version": (
                "portfolio-risk-freshness-gate-card-v3"
            ),
            "freshness_gate_card_v3_static_fingerprint": (
                "20260822-portfolio-risk-freshness-gate-card-lock-1"
            ),
            "freshness_gate_card_v3_projection_schema_version": (
                projection_v3.SCHEMA_VERSION
            ),
            "freshness_gate_card_v3_javascript_sha256": (
                _EXPECTED_IMPLEMENTATION_SHA256[
                    "portfolio_risk_freshness_gate_card_v3_js"
                ]
            ),
            "freshness_gate_card_v3_stylesheet_sha256": (
                _EXPECTED_IMPLEMENTATION_SHA256[
                    "portfolio_risk_freshness_gate_card_v3_css"
                ]
            ),
            "presentation_binding_policy": (
                "EXACT_LINEAGE_V2_ADAPTER_V3_AND_PROJECTION_V3_PUBLIC_"
                "REVERIFICATION_PLUS_ISOLATED_DOM_REVIEW_REQUIRED_V1"
            ),
        },
        "required_shadow_input_schemas": (
            copy.deepcopy(_list(predecessor.get("required_shadow_input_schemas")))
            if predecessor_exact
            else []
        ),
        "closed_local_blockers": (
            copy.deepcopy(_list(predecessor.get("closed_local_blockers")))
            if predecessor_exact
            else []
        ),
        "blocker_refinements": (
            copy.deepcopy(_list(predecessor.get("blocker_refinements")))
            if predecessor_exact
            else []
        )
        + [
            {
                "source_blocker": "presentation_consumer_v2_not_registered",
                "source_blocker_closed": False,
                "local_contract_state": (
                    "ADR0190_PROJECTION_AND_UNMOUNTED_CARD_PINNED_"
                    "NO_DOM_BROWSER_OR_HTTP_EVIDENCE_BOUND"
                ),
                "remaining_requirements": [
                    "portfolio_risk_projection_v3_evidence_not_bound",
                    "freshness_gate_card_v3_dom_not_reviewed",
                    "browser_visual_review_v3_not_performed",
                    "presentation_http_contract_v3_not_versioned",
                ],
            }
        ],
        "newly_pinned_local_capabilities": [
            {
                "capability": "ADAPTER_V2_SESSION_FRESHNESS_LINEAGE_V2",
                "contract_pinned": manifest_exact,
                "evidence_bound": False,
                "consumer_executed": False,
                "external_authority_verified": False,
                "pin": "ADR0187_ADR0188_IMPLEMENTATIONS_AND_SCHEMAS_PINNED",
            },
            {
                "capability": "PORTFOLIO_RISK_JOINT_LOCAL_DECISION_V3",
                "contract_pinned": manifest_exact,
                "evidence_bound": False,
                "consumer_executed": False,
                "external_authority_verified": False,
                "pin": "ADR0189_ADAPTER_V3_IMPLEMENTATION_AND_SCHEMA_PINNED",
            },
            {
                "capability": "PORTFOLIO_RISK_FRESHNESS_PUBLIC_PRESENTATION_V3",
                "contract_pinned": manifest_exact,
                "evidence_bound": False,
                "consumer_executed": False,
                "external_authority_verified": False,
                "pin": "ADR0190_PROJECTION_CARD_AND_STYLESHEET_PINNED",
            },
        ],
        "reuse_plan": (
            copy.deepcopy(_list(predecessor.get("reuse_plan")))
            if predecessor_exact
            else []
        )
        + [
            {
                "capability": "PORTFOLIO_RISK_ADAPTER_FRESHNESS_LINEAGE",
                "decision": "REUSE_ADR0188_EXACT_LINEAGE_CONTRACT_EVIDENCE_NOT_BOUND",
            },
            {
                "capability": "PORTFOLIO_RISK_PRESENTATION_V3",
                "decision": "REUSE_ADR0190_DETACHED_PROJECTION_AND_CARD_NO_MOUNT",
            },
        ],
        "blockers": blockers,
        "activation_order": activation_order,
        "facts": {
            "immutable_v5_exactly_verified": predecessor_exact,
            "required_shadow_input_count": (
                len(_list(predecessor.get("required_shadow_input_schemas")))
                if predecessor_exact
                else 0
            ),
            "closed_local_blocker_count": (
                len(_list(predecessor.get("closed_local_blockers")))
                if predecessor_exact
                else 0
            ),
            "implementation_pin_count": len(_EXPECTED_IMPLEMENTATION_SHA256),
            "new_implementation_pin_count": len(_NEW_ARTIFACTS),
            "lineage_v1_contract_pinned": manifest_exact,
            "lineage_v2_contract_pinned": manifest_exact,
            "adapter_v3_contract_pinned": manifest_exact,
            "projection_v3_contract_pinned": manifest_exact,
            "freshness_gate_card_v3_javascript_pinned": manifest_exact,
            "freshness_gate_card_v3_stylesheet_pinned": manifest_exact,
            "lineage_v2_evidence_bound": False,
            "adapter_v3_evidence_bound": False,
            "adapter_v3_exactly_verified": False,
            "projection_v3_evidence_bound": False,
            "projection_v3_exactly_verified": False,
            "presentation_consumer_v3_registered": False,
            "dom_contract_v3_reviewed": False,
            "browser_visual_review_v3_performed": False,
            "presentation_http_contract_v3_versioned": False,
            "profitability_proven": False,
            "risk_service_invoked": False,
            "runtime_assets_accessed": False,
            "runtime_consumer_bound": False,
            "server_route_registered": False,
            "shadow_consumer_executed": False,
            "ui_mounted": False,
        },
        "authority": {
            "descriptive_only": True,
            "current_admission_allowed": False,
            "current_pointer_written": False,
            "formal_registry_activation_allowed": False,
            "live_order_allowed": False,
            "migration_allowed": False,
            "paper_authorized": False,
            "presentation_consumer_activation_allowed": False,
            "runtime_gate_activation_allowed": False,
            "shadow_consumer_activation_allowed": False,
            "writer_allowed": False,
        },
    }
    document["preregistration_hash"] = _canonical_hash(document)
    return document


def verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v6(
    document: Any,
    preregistration_v5_document: Any,
    v5_verification_context: Any,
    current_implementation_sha256: Any,
) -> dict[str, Any]:
    expected = build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v6(
        preregistration_v5_document,
        v5_verification_context,
        current_implementation_sha256,
    )
    exact = bool(type(document) is dict and document == expected)
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "preregistration_exactly_verified": exact,
        "preregistration_status": expected.get("status") if exact else "UNKNOWN",
        "blockers": [] if exact else ["preregistration_v6_exact_rebuild"],
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_consumer_activation_allowed": False,
        "runtime_gate_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
        "writer_allowed": False,
    }


__all__ = [
    "DECISION",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "STATUS",
    "V5_VERIFICATION_CONTEXT_KEYS",
    "VERIFICATION_SCHEMA_VERSION",
    "build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v6",
    "expected_shadow_consumer_implementation_sha256_v6",
    "verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v6",
]
