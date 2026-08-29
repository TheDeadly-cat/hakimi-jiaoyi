from __future__ import annotations

import hashlib
import json
from typing import Any

from . import (
    strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v1 as readiness_v1_contract,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_adapter_v1 as adapter_contract,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_dual_source_receipt_v1 as dual_source_contract,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_legacy_matrix_derivation_binding_v1 as legacy_binding_contract,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1 as native_cutoff_contract,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_session_freshness_v1 as freshness_contract,
)
from exchange_terminal.services.execution_authority import authority_violations


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-"
    "shadow-input-readiness-envelope-v2"
)
STATIC_FINGERPRINT = (
    "20260822-portfolio-risk-shadow-input-readiness-envelope-2"
)
STATUS = "UNKNOWN"
POSITIVE_SOURCE_STATE = "LOCAL_INPUT_SET_VERIFIED"
UNKNOWN_SOURCE_STATE = "UNKNOWN"
POSITIVE_GAP_STATE = "EXTERNAL_TRUST_AND_RUNTIME_CONSUMER_UNPROVEN"
UNKNOWN_GAP_STATE = "SOURCE_CONTRACT_UNVERIFIED"
POSITIVE_MATURITY_STATE = "LOCAL_INPUT_SET_VERIFIED_EXTERNAL_TRUST_UNPROVEN"
UNKNOWN_MATURITY_STATE = "UNKNOWN"
PERMISSION_STATE = "DENIED"

_READINESS_V1_CONTEXT_KEYS = {
    "preregistration_v3",
    "content_issuance_replay_verification",
    "preregistration_verification_context",
    "content_issuance_replay_verification_context",
}
_PORTFOLIO_INPUT_KEYS = {
    "dual_source_receipt",
    "portfolio_risk_adapter",
    "legacy_matrix_derivation_binding",
    "native_cutoff_manifest",
    "session_freshness_registration",
    "session_freshness_evaluation",
}
_PORTFOLIO_CONTEXT_KEYS = set(_PORTFOLIO_INPUT_KEYS)
_PERMISSIONS = {
    "paper_authorized": False,
    "live_order_allowed": False,
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _authority_invalid(value: Any) -> bool:
    try:
        return bool(authority_violations(value))
    except (MemoryError, RecursionError, TypeError, ValueError):
        return True


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "shadow_consumer_execution_allowed": False,
        "risk_service_invocation_allowed": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "profitability_claim_allowed": False,
    }


def _facts() -> dict[str, bool]:
    return {
        "readiness_v1_verified": False,
        "dual_source_receipt_verified": False,
        "portfolio_risk_adapter_verified": False,
        "legacy_matrix_derivation_binding_verified": False,
        "native_cutoff_manifest_verified": False,
        "session_freshness_registration_verified": False,
        "session_freshness_evaluation_verified": False,
        "shared_dataset_attestation_lineage_verified": False,
        "shared_composition_lineage_verified": False,
        "shared_symbol_universe_verified": False,
        "shared_observation_cutoff_verified": False,
        "shared_legacy_payload_verified": False,
        "shared_cluster_payload_verified": False,
        "shared_freshness_registration_lineage_verified": False,
        "local_required_input_set_verified": False,
        "external_provider_key_control_verified": False,
        "external_provider_data_issuance_verified": False,
        "external_content_replay_registry_authority_verified": False,
        "external_occurrence_auditor_authority_verified": False,
        "durable_content_checkpoint_publication_verified": False,
        "external_time_authority_authenticated": False,
        "runtime_consumption_replay_enforcement_verified": False,
        "future_replay_absence_verified": False,
        "shadow_consumer_executed": False,
        "risk_service_invoked": False,
        "ui_mounted": False,
        "profitability_verified": False,
    }


def _sealed(
    *,
    source_state: str,
    gap_state: str,
    maturity_state: str,
    input_inventory: list[dict[str, Any]],
    source_lineage: dict[str, Any],
    gate_outcomes: dict[str, Any],
    facts: dict[str, bool],
    blockers: list[str],
) -> dict[str, Any]:
    body = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": STATUS,
        "source_state": source_state,
        "gap_state": gap_state,
        "maturity_state": maturity_state,
        "permission_state": PERMISSION_STATE,
        "axes": {
            "source": source_state,
            "gap": gap_state,
            "maturity": maturity_state,
            "permission": PERMISSION_STATE,
        },
        "summary": {
            "required_input_count": len(input_inventory),
            "verified_input_count": sum(
                entry["state"] == "VERIFIED"
                for entry in input_inventory
            ),
            "not_supplied_input_count": sum(
                entry["state"] == "NOT_SUPPLIED"
                for entry in input_inventory
            ),
            "unverified_input_count": sum(
                entry["state"] == "UNVERIFIED"
                for entry in input_inventory
            ),
        },
        "input_inventory": input_inventory,
        "source_lineage": source_lineage,
        "gate_outcomes": gate_outcomes,
        "facts": facts,
        "blockers": blockers,
        "authority": _authority(),
        "permissions": dict(_PERMISSIONS),
    }
    return {**body, "envelope_hash": _sha256(body)}


def _empty_lineage() -> dict[str, None]:
    return {
        "readiness_v1_envelope_hash": None,
        "future_evaluation_id_hash": None,
        "source_attestation_hash": None,
        "dual_source_receipt_hash": None,
        "portfolio_risk_adapter_hash": None,
        "legacy_matrix_derivation_binding_hash": None,
        "native_cutoff_manifest_hash": None,
        "session_freshness_registration_hash": None,
        "session_freshness_evaluation_hash": None,
    }


def _unknown(reason: str) -> dict[str, Any]:
    return _sealed(
        source_state=UNKNOWN_SOURCE_STATE,
        gap_state=UNKNOWN_GAP_STATE,
        maturity_state=UNKNOWN_MATURITY_STATE,
        input_inventory=[],
        source_lineage=_empty_lineage(),
        gate_outcomes={},
        facts=_facts(),
        blockers=[
            reason,
            "local_input_set_unverified",
            "shadow_consumer_not_executed",
            "risk_service_not_invoked",
            "current_admission_denied",
        ],
    )


def _verification_pass(
    result: Any,
    expected_schema: str,
) -> bool:
    return (
        type(result) is dict
        and result.get("schema_version") == expected_schema
        and result.get("status") == "PASS"
        and result.get("blockers") == []
        and result.get("current_admission_allowed", False) is False
        and result.get("paper_authorized", False) is False
        and result.get("live_order_allowed", False) is False
    )


def _source_documents_match(
    readiness_v1: dict[str, Any],
    readiness_v1_verification_context: dict[str, Any],
    portfolio_inputs: dict[str, Any],
    portfolio_verification_contexts: dict[str, Any],
) -> bool:
    dual_context = portfolio_verification_contexts["dual_source_receipt"]
    adapter_context = portfolio_verification_contexts[
        "portfolio_risk_adapter"
    ]
    binding_context = portfolio_verification_contexts[
        "legacy_matrix_derivation_binding"
    ]
    native_context = portfolio_verification_contexts[
        "native_cutoff_manifest"
    ]
    freshness_registration_context = portfolio_verification_contexts[
        "session_freshness_registration"
    ]
    freshness_evaluation_context = portfolio_verification_contexts[
        "session_freshness_evaluation"
    ]
    replay_context = readiness_v1_verification_context[
        "content_issuance_replay_verification_context"
    ]
    if not all(
        type(value) is dict
        for value in (
            dual_context,
            adapter_context,
            binding_context,
            native_context,
            freshness_registration_context,
            freshness_evaluation_context,
            replay_context,
        )
    ):
        return False
    shared_source_keys = (
        "completed_price_input",
        "matrix_replay",
        "derivation_receipt",
        "composition_document",
        "composition_context",
    )
    try:
        return (
            dual_context["legacy_payload"]
            == binding_context["legacy_correlation_matrix"]
            and dual_context["cluster_payload"]
            == adapter_context["cluster_correlation_matrix"]
            and dual_context["expected_symbols"]
            == dual_context["legacy_payload"]["symbols"]
            == dual_context["cluster_payload"]["symbols"]
            and dual_context["expected_observation_cutoff_utc"]
            == native_context["expected_observation_cutoff_utc"]
            and adapter_context["legacy_correlations"]["pairs"]
            == dual_context["legacy_payload"]["pairs"]
            and all(
                binding_context[key] == native_context[key]
                for key in shared_source_keys
            )
            and binding_context["dataset_attestation_verification"]
            == replay_context["attestation_document"]
            and binding_context["dataset_attestation_registration"]
            == replay_context["attestation_context"]["registration"]
            and binding_context["provider_dataset_public_key_base64"]
            == replay_context["attestation_context"][
                "provider_dataset_public_key_base64"
            ]
            and binding_context["dataset_attestation_receipt"]
            == replay_context["attestation_context"]["attestation_receipt"]
            and native_context["composition_document"][
                "future_evaluation_id_hash"
            ]
            == readiness_v1["source_lineage"]["future_evaluation_id_hash"]
            and freshness_registration_context["native_cutoff_manifest"]
            == portfolio_inputs["native_cutoff_manifest"]
            and freshness_evaluation_context["registration"]
            == portfolio_inputs["session_freshness_registration"]
            and freshness_evaluation_context["registration_inputs"]
            == freshness_registration_context
        )
    except (KeyError, TypeError):
        return False


def build_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v2(
    readiness_v1: Any,
    portfolio_inputs: Any,
    *,
    readiness_v1_verification_context: Any,
    portfolio_verification_contexts: Any,
) -> dict[str, Any]:
    if (
        type(readiness_v1_verification_context) is not dict
        or set(readiness_v1_verification_context)
        != _READINESS_V1_CONTEXT_KEYS
        or type(portfolio_inputs) is not dict
        or set(portfolio_inputs) != _PORTFOLIO_INPUT_KEYS
        or type(portfolio_verification_contexts) is not dict
        or set(portfolio_verification_contexts) != _PORTFOLIO_CONTEXT_KEYS
        or not all(
            type(value) is dict
            for value in portfolio_verification_contexts.values()
        )
        or _authority_invalid(
            [
                readiness_v1,
                portfolio_inputs,
                readiness_v1_verification_context,
                portfolio_verification_contexts,
            ]
        )
    ):
        return _unknown("SOURCE_CONTEXT_INVALID")
    try:
        readiness_verified = readiness_v1_contract.verify_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v1(
            readiness_v1,
            **readiness_v1_verification_context,
        )
        dual_verification = dual_source_contract.verify_strategy_correlation_cluster_portfolio_risk_dual_source_receipt_v1(
            portfolio_inputs["dual_source_receipt"],
            **portfolio_verification_contexts["dual_source_receipt"],
        )
        adapter_verification = adapter_contract.verify_strategy_correlation_cluster_portfolio_risk_adapter_v1(
            portfolio_inputs["portfolio_risk_adapter"],
            **portfolio_verification_contexts["portfolio_risk_adapter"],
        )
        binding_verification = legacy_binding_contract.verify_strategy_correlation_cluster_portfolio_risk_legacy_matrix_derivation_binding_v1(
            portfolio_inputs["legacy_matrix_derivation_binding"],
            **portfolio_verification_contexts[
                "legacy_matrix_derivation_binding"
            ],
        )
        native_verification = native_cutoff_contract.verify_strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1(
            portfolio_inputs["native_cutoff_manifest"],
            **portfolio_verification_contexts["native_cutoff_manifest"],
        )
        freshness_registration_verified = freshness_contract.verify_strategy_correlation_cluster_portfolio_risk_session_freshness_policy_registration_v1(
            portfolio_inputs["session_freshness_registration"],
            **portfolio_verification_contexts[
                "session_freshness_registration"
            ],
        )
        freshness_evaluation_verified = freshness_contract.verify_strategy_correlation_cluster_portfolio_risk_session_freshness_evaluation_v1(
            portfolio_inputs["session_freshness_evaluation"],
            **portfolio_verification_contexts[
                "session_freshness_evaluation"
            ],
        )
    except Exception:
        return _unknown("SOURCE_VERIFIER_ERROR")
    if (
        readiness_verified is not True
        or not _verification_pass(
            dual_verification,
            dual_source_contract.DUAL_SOURCE_RECEIPT_VERIFICATION_SCHEMA_VERSION,
        )
        or not _verification_pass(
            adapter_verification,
            adapter_contract.ADAPTER_VERIFICATION_SCHEMA_VERSION,
        )
        or not _verification_pass(
            binding_verification,
            legacy_binding_contract.BINDING_VERIFICATION_SCHEMA_VERSION,
        )
        or not _verification_pass(
            native_verification,
            native_cutoff_contract.MANIFEST_VERIFICATION_SCHEMA_VERSION,
        )
        or freshness_registration_verified is not True
        or freshness_evaluation_verified is not True
    ):
        return _unknown("SOURCE_CONTRACT_UNVERIFIED")

    dual_document = portfolio_inputs["dual_source_receipt"]
    adapter_document = portfolio_inputs["portfolio_risk_adapter"]
    binding_document = portfolio_inputs[
        "legacy_matrix_derivation_binding"
    ]
    native_document = portfolio_inputs["native_cutoff_manifest"]
    freshness_registration = portfolio_inputs[
        "session_freshness_registration"
    ]
    freshness_evaluation = portfolio_inputs[
        "session_freshness_evaluation"
    ]
    if (
        type(readiness_v1) is not dict
        or readiness_v1.get("schema_version")
        != readiness_v1_contract.SCHEMA_VERSION
        or readiness_v1.get("static_fingerprint")
        != readiness_v1_contract.STATIC_FINGERPRINT
        or readiness_v1.get("status") != "UNKNOWN"
        or readiness_v1.get("source_state")
        != readiness_v1_contract.POSITIVE_SOURCE_STATE
        or readiness_v1.get("permission_state") != "DENIED"
        or readiness_v1.get("summary", {}).get("verified_input_count") != 7
        or readiness_v1.get("summary", {}).get(
            "not_supplied_input_count"
        )
        != 6
        or type(dual_document) is not dict
        or dual_document.get("schema_version")
        != dual_source_contract.DUAL_SOURCE_RECEIPT_SCHEMA_VERSION
        or dual_document.get("status") != "PASS"
        or dual_document.get("decision")
        != "DUAL_SOURCE_PROVIDER_ASSERTIONS_ALIGNED"
        or type(adapter_document) is not dict
        or adapter_document.get("schema_version")
        != adapter_contract.ADAPTER_SCHEMA_VERSION
        or adapter_document.get("status") != "PASS"
        or adapter_document.get("decision")
        != "WITHIN_RESEARCH_RISK_BUDGET"
        or type(binding_document) is not dict
        or binding_document.get("schema_version")
        != legacy_binding_contract.BINDING_SCHEMA_VERSION
        or binding_document.get("status") != "PASS"
        or binding_document.get("decision")
        != "LEGACY_MATRIX_BOUND_TO_SIGNED_CONTENT_CLAIM_EXTERNAL_TRUST_UNPROVEN"
        or type(native_document) is not dict
        or native_document.get("schema_version")
        != native_cutoff_contract.MANIFEST_SCHEMA_VERSION
        or native_document.get("status") != "PASS"
        or native_document.get("decision")
        != "NATIVE_SESSION_LABEL_CUTOFF_VERIFIED_NOT_FRESHNESS"
        or type(freshness_registration) is not dict
        or freshness_registration.get("schema_version")
        != freshness_contract.REGISTRATION_SCHEMA_VERSION
        or freshness_registration.get("status") != "REGISTERED"
        or type(freshness_evaluation) is not dict
        or freshness_evaluation.get("schema_version")
        != freshness_contract.EVALUATION_SCHEMA_VERSION
        or freshness_evaluation.get("status") != "PASS"
        or freshness_evaluation.get("decision")
        != "SESSION_LAG_WITHIN_PREREGISTERED_POLICY_EXTERNAL_TIME_AUTHORITY_UNPROVEN"
        or not _source_documents_match(
            readiness_v1,
            readiness_v1_verification_context,
            portfolio_inputs,
            portfolio_verification_contexts,
        )
    ):
        return _unknown("SOURCE_CONTRACT_MISMATCH")

    inventory = []
    for entry in readiness_v1["input_inventory"]:
        if (
            type(entry) is not dict
            or set(entry) != {"input", "schema_version", "state"}
            or entry.get("state") not in {"VERIFIED", "NOT_SUPPLIED"}
        ):
            return _unknown("READINESS_V1_INVENTORY_INVALID")
        inventory.append(
            {
                "input": entry["input"],
                "schema_version": entry["schema_version"],
                "state": "VERIFIED",
            }
        )
    if len(inventory) != 13:
        return _unknown("READINESS_V1_INVENTORY_INVALID")

    facts = _facts()
    facts.update(
        {
            "readiness_v1_verified": True,
            "dual_source_receipt_verified": True,
            "portfolio_risk_adapter_verified": True,
            "legacy_matrix_derivation_binding_verified": True,
            "native_cutoff_manifest_verified": True,
            "session_freshness_registration_verified": True,
            "session_freshness_evaluation_verified": True,
            "shared_dataset_attestation_lineage_verified": True,
            "shared_composition_lineage_verified": True,
            "shared_symbol_universe_verified": True,
            "shared_observation_cutoff_verified": True,
            "shared_legacy_payload_verified": True,
            "shared_cluster_payload_verified": True,
            "shared_freshness_registration_lineage_verified": True,
            "local_required_input_set_verified": True,
        }
    )
    return _sealed(
        source_state=POSITIVE_SOURCE_STATE,
        gap_state=POSITIVE_GAP_STATE,
        maturity_state=POSITIVE_MATURITY_STATE,
        input_inventory=inventory,
        source_lineage={
            "readiness_v1_envelope_hash": readiness_v1["envelope_hash"],
            "future_evaluation_id_hash": readiness_v1["source_lineage"][
                "future_evaluation_id_hash"
            ],
            "source_attestation_hash": readiness_v1["source_lineage"][
                "source_attestation_hash"
            ],
            "dual_source_receipt_hash": dual_document["receipt_hash"],
            "portfolio_risk_adapter_hash": adapter_document["adapter_hash"],
            "legacy_matrix_derivation_binding_hash": binding_document[
                "binding_hash"
            ],
            "native_cutoff_manifest_hash": native_document["manifest_hash"],
            "session_freshness_registration_hash": (
                freshness_registration["registration_hash"]
            ),
            "session_freshness_evaluation_hash": freshness_evaluation[
                "evaluation_hash"
            ],
        },
        gate_outcomes={
            "dual_source_receipt": {
                "status": dual_document["status"],
                "decision": dual_document["decision"],
                "receipt_hash": dual_document["receipt_hash"],
            },
            "portfolio_risk_adapter": {
                "status": adapter_document["status"],
                "decision": adapter_document["decision"],
                "adapter_hash": adapter_document["adapter_hash"],
            },
            "legacy_matrix_derivation_binding": {
                "status": binding_document["status"],
                "decision": binding_document["decision"],
                "binding_hash": binding_document["binding_hash"],
            },
            "native_cutoff_manifest": {
                "status": native_document["status"],
                "decision": native_document["decision"],
                "manifest_hash": native_document["manifest_hash"],
            },
            "session_freshness_registration": {
                "status": freshness_registration["status"],
                "registration_state": freshness_registration[
                    "registration_state"
                ],
                "registration_hash": freshness_registration[
                    "registration_hash"
                ],
            },
            "session_freshness_evaluation": {
                "status": freshness_evaluation["status"],
                "decision": freshness_evaluation["decision"],
                "evaluation_hash": freshness_evaluation["evaluation_hash"],
            },
        },
        facts=facts,
        blockers=[
            "external_provider_key_control_unproven",
            "external_provider_data_issuance_unproven",
            "external_content_replay_registry_authority_unproven",
            "external_occurrence_auditor_authority_unproven",
            "durable_content_checkpoint_publication_unproven",
            "external_time_authority_unauthenticated",
            "runtime_consumption_replay_enforcement_missing",
            "future_replay_absence_unproven",
            "shadow_consumer_not_executed",
            "risk_service_input_not_versioned",
            "risk_service_not_invoked",
            "independent_shadow_review_missing",
            "current_admission_denied",
        ],
    )


def verify_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v2(
    document: Any,
    readiness_v1: Any,
    portfolio_inputs: Any,
    *,
    readiness_v1_verification_context: Any,
    portfolio_verification_contexts: Any,
) -> bool:
    if type(document) is not dict or _authority_invalid(document):
        return False
    try:
        rebuilt = build_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v2(
            readiness_v1,
            portfolio_inputs,
            readiness_v1_verification_context=(
                readiness_v1_verification_context
            ),
            portfolio_verification_contexts=(
                portfolio_verification_contexts
            ),
        )
    except Exception:
        return False
    return document == rebuilt
