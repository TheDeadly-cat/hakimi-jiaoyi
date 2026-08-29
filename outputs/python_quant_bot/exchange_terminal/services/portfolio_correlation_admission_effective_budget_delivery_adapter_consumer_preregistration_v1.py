"""Fail-closed consumer preregistration for the dual-runtime delivery adapters.

This module records exact future consumer obligations before any host binding.
It does not import a host, execute an adapter, mount presentation code, or grant
paper/live authority.
"""

from __future__ import annotations

from typing import Any

from exchange_terminal.services.portfolio_correlation_admission_effective_budget_in_memory_delivery_adapter_registration_v1 import (
    build_portfolio_correlation_admission_effective_budget_in_memory_delivery_adapter_registration_v1 as build_adapter_registration_v1,
    strict_canonical_hash,
    verify_portfolio_correlation_admission_effective_budget_in_memory_delivery_adapter_registration_v1 as verify_adapter_registration_v1,
)


SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-delivery-"
    "adapter-consumer-preregistration-v1"
)
STATIC_FINGERPRINT = (
    "20260823-portfolio-correlation-admission-effective-budget-delivery-"
    "adapter-consumer-preregistration-v1-unbound-lock-1"
)
PREREGISTRATION_ID = (
    "portfolio-correlation-admission-effective-budget-dual-runtime-consumers-v1"
)
STATUS = "BLOCKED"
REGISTRATION_STATE = "DUAL_RUNTIME_CONSUMERS_PREREGISTERED_HOST_UNBOUND"

PREDECESSOR_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-in-memory-delivery-"
    "adapter-registration-v1"
)
PREDECESSOR_STATIC_FINGERPRINT = (
    "20260823-portfolio-correlation-admission-effective-budget-delivery-"
    "adapter-registration-v1-unbound-lock-1"
)
PREDECESSOR_REGISTRATION_ID = (
    "portfolio-correlation-admission-effective-budget-delivery-adapters-v1"
)
PREDECESSOR_REGISTRATION_STATE = (
    "DUAL_RUNTIME_DELIVERY_ADAPTER_ASSETS_REGISTERED_UNBOUND"
)
PREDECESSOR_REGISTRATION_HASH = (
    "4c6eb60d842611d2babaf072527fe93d2a68f67bc6a7c2658b80fd1b9f07f4cb"
)
PREDECESSOR_ASSET_MANIFEST_HASH = (
    "d5d4e3c829f99ba840cc945d11a8c8cec90386baa1ea2e7a0f6333e8d6d6c058"
)
PREDECESSOR_IMPLEMENTATION_SHA256 = (
    "07253de9e513b719f945ec16ba3ed242495e44ff1a80bc028bbb526a9f2b806b"
)
PREDECESSOR_TEST_SHA256 = (
    "734f9426aaf06cb88e756bfdbd7d7201202d2a626ea73c542962625eda6bf231"
)
PREDECESSOR_ADR_SHA256 = (
    "fcc0d9965ce242448fa848a870687fc56e563215877c0185462189cd6e40b18a"
)

PYTHON_CONTRACT_HASH = (
    "484dc34f1736c8f0cbb08f7a6d560b65af064400fe53831bf5215541d669df6f"
)
JAVASCRIPT_CONTRACT_HASH = (
    "3831fc0e8c9610536d3420226ac0c80d501dddb367633c11de954e724fb8816e"
)
PRESENTATION_CONTRACT_HASH = (
    "d8c0462d451543b58ea8d25c2454347dd9129266020f371e47e9cc2d57a2e632"
)
TRANSPORT_CONTRACT_HASH = (
    "5c5b7a00984408d3ce03e6f23a3a33e339fbdc457b77fc59cc317acd4f341b62"
)
PREDECESSOR_AUTHORITY_HASH = (
    "c934ee41b56e2b1b53c4aacbe4f6a57749d195df4ba73a0fd4d7c43593847a80"
)
PREDECESSOR_ACTIVATION_ORDER_HASH = (
    "1ecc3a80c36f740853fa4120d490e56b6001dc97d10d11472590ba3bdd62caa9"
)
PREDECESSOR_HOST_PLAN_HASH = (
    "3f32db5e9329a64752580f3dd3a6c0c084ca0d6870ca9fcac27e165e8689a690"
)

PYTHON_CONSUMER_ID = (
    "portfolio-correlation-admission-effective-budget-hash-envelope-source-v1"
)
JAVASCRIPT_CONSUMER_ID = (
    "portfolio-correlation-admission-effective-budget-inspection-bridge-v1"
)


def _is_native_json_tree(value: Any, active: set[int] | None = None) -> bool:
    value_type = type(value)
    if value_type in (str, int, bool, type(None)):
        return True
    if value_type not in (list, dict):
        return False

    if active is None:
        active = set()
    identity = id(value)
    if identity in active:
        return False
    active.add(identity)
    try:
        if value_type is list:
            return all(_is_native_json_tree(item, active) for item in value)
        return all(
            type(key) is str and _is_native_json_tree(item, active)
            for key, item in value.items()
        )
    finally:
        active.remove(identity)


def _build_exact_predecessor() -> dict[str, Any]:
    predecessor = build_adapter_registration_v1()
    if not verify_adapter_registration_v1(predecessor):
        raise ValueError("ADR0309 adapter registration did not verify exactly")

    exact_fields = {
        "schema_version": PREDECESSOR_SCHEMA_VERSION,
        "static_fingerprint": PREDECESSOR_STATIC_FINGERPRINT,
        "registration_id": PREDECESSOR_REGISTRATION_ID,
        "registration_state": PREDECESSOR_REGISTRATION_STATE,
        "status": STATUS,
        "asset_manifest_hash": PREDECESSOR_ASSET_MANIFEST_HASH,
        "adapter_registration_hash": PREDECESSOR_REGISTRATION_HASH,
    }
    if any(predecessor.get(key) != value for key, value in exact_fields.items()):
        raise ValueError("ADR0309 adapter registration identity drifted")

    exact_hashes = {
        "python_contract": PYTHON_CONTRACT_HASH,
        "javascript_contract": JAVASCRIPT_CONTRACT_HASH,
        "presentation_contract": PRESENTATION_CONTRACT_HASH,
        "transport_contract": TRANSPORT_CONTRACT_HASH,
        "authority": PREDECESSOR_AUTHORITY_HASH,
        "activation_order": PREDECESSOR_ACTIVATION_ORDER_HASH,
        "host_plan": PREDECESSOR_HOST_PLAN_HASH,
    }
    for key, expected_hash in exact_hashes.items():
        if strict_canonical_hash(predecessor.get(key)) != expected_hash:
            raise ValueError(f"ADR0309 {key} contract drifted")

    host_plan = predecessor["host_plan"]
    authority = predecessor["authority"]
    if type(host_plan) is not dict or any(value is not None for value in host_plan.values()):
        raise ValueError("ADR0309 host plan is no longer unbound")
    if type(authority) is not dict or any(value is not False for value in authority.values()):
        raise ValueError("ADR0309 authority is no longer fully locked")
    return predecessor


def _build_python_consumer(predecessor: dict[str, Any]) -> dict[str, Any]:
    contract = predecessor["python_contract"]
    return {
        "consumer_id": PYTHON_CONSUMER_ID,
        "runtime": "PYTHON",
        "role": "HASH_ONLY_IN_MEMORY_ENVELOPE_SOURCE",
        "accepted_adapter_registration_hash": PREDECESSOR_REGISTRATION_HASH,
        "required_contract_hash": PYTHON_CONTRACT_HASH,
        "required_transport_contract_hash": TRANSPORT_CONTRACT_HASH,
        "required_schema_version": contract["schema_version"],
        "required_static_fingerprint": contract["static_fingerprint"],
        "required_payload_schema_version": contract["payload_schema_version"],
        "required_builder": contract["builder"],
        "required_verifier": contract["verifier"],
        "required_exports": list(contract["exports"]),
        "input_boundary": (
            "EXACT_ADMISSION_V2_EFFECTIVE_BUDGET_V3_BINDING_DOCUMENT_ONLY"
        ),
        "output_boundary": "HASH_ONLY_IN_MEMORY_ENVELOPE_ONLY",
        "implementation_binding": None,
        "payload_source_provider": None,
        "host_slot": None,
        "contract_preregistered": True,
        "implementation_bound": False,
        "execution_allowed": False,
        "route_allowed": False,
        "writer_allowed": False,
    }


def _build_javascript_consumer(predecessor: dict[str, Any]) -> dict[str, Any]:
    contract = predecessor["javascript_contract"]
    presentation = predecessor["presentation_contract"]
    return {
        "consumer_id": JAVASCRIPT_CONSUMER_ID,
        "runtime": "JAVASCRIPT",
        "role": "VERIFY_EXTRACT_AND_BUILD_UNMOUNTED_INSPECTION_BRIDGE",
        "accepted_adapter_registration_hash": PREDECESSOR_REGISTRATION_HASH,
        "required_contract_hash": JAVASCRIPT_CONTRACT_HASH,
        "required_presentation_contract_hash": PRESENTATION_CONTRACT_HASH,
        "required_transport_contract_hash": TRANSPORT_CONTRACT_HASH,
        "required_envelope_schema_version": contract["envelope_schema_version"],
        "required_payload_schema_version": contract["payload_schema_version"],
        "required_receipt_schema_version": contract["receipt_schema_version"],
        "required_static_fingerprint": contract["static_fingerprint"],
        "required_browser_globals": [
            contract["browser_global"],
            presentation["bridge_browser_global"],
        ],
        "required_exports": list(contract["exports"]),
        "required_relative_load_order": list(contract["relative_load_order"]),
        "required_stage_order": list(presentation["stage_order"]),
        "input_boundary": "VERIFIED_IN_MEMORY_ENVELOPE_ARGUMENT_ONLY",
        "output_boundary": "UNMOUNTED_NEUTRAL_MARKUP_STRING_ONLY",
        "module_binding": None,
        "html_script_binding": None,
        "stylesheet_link_binding": None,
        "mount_slot": None,
        "contract_preregistered": True,
        "implementation_bound": False,
        "browser_execution_allowed": False,
        "dom_mount_allowed": False,
        "runtime_asset_loading_allowed": False,
    }


def build_portfolio_correlation_admission_effective_budget_delivery_adapter_consumer_preregistration_v1() -> dict[str, Any]:
    """Build the exact, sealed, host-unbound consumer preregistration."""

    predecessor = _build_exact_predecessor()
    core: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "preregistration_id": PREREGISTRATION_ID,
        "status": STATUS,
        "registration_state": REGISTRATION_STATE,
        "predecessor_contract": {
            "schema_version": PREDECESSOR_SCHEMA_VERSION,
            "static_fingerprint": PREDECESSOR_STATIC_FINGERPRINT,
            "registration_id": PREDECESSOR_REGISTRATION_ID,
            "registration_state": PREDECESSOR_REGISTRATION_STATE,
            "registration_hash": PREDECESSOR_REGISTRATION_HASH,
            "asset_manifest_hash": PREDECESSOR_ASSET_MANIFEST_HASH,
            "implementation_path": (
                "exchange_terminal/services/"
                "portfolio_correlation_admission_effective_budget_in_memory_"
                "delivery_adapter_registration_v1.py"
            ),
            "implementation_sha256": PREDECESSOR_IMPLEMENTATION_SHA256,
            "test_path": (
                "tests/test_portfolio_correlation_admission_effective_budget_"
                "in_memory_delivery_adapter_registration_v1.py"
            ),
            "test_sha256": PREDECESSOR_TEST_SHA256,
            "adr_path": (
                "docs/adr/0309-portfolio-correlation-admission-effective-"
                "budget-in-memory-delivery-adapter-registration-v1.md"
            ),
            "adr_sha256": PREDECESSOR_ADR_SHA256,
            "python_contract_hash": PYTHON_CONTRACT_HASH,
            "javascript_contract_hash": JAVASCRIPT_CONTRACT_HASH,
            "presentation_contract_hash": PRESENTATION_CONTRACT_HASH,
            "transport_contract_hash": TRANSPORT_CONTRACT_HASH,
            "authority_hash": PREDECESSOR_AUTHORITY_HASH,
            "activation_order_hash": PREDECESSOR_ACTIVATION_ORDER_HASH,
            "host_plan_hash": PREDECESSOR_HOST_PLAN_HASH,
        },
        "consumer_contracts": [
            _build_python_consumer(predecessor),
            _build_javascript_consumer(predecessor),
        ],
        "acceptance_gates": {
            "exact_adapter_registration": "EXACT",
            "python_consumer_contract": "PREREGISTERED",
            "javascript_consumer_contract": "PREREGISTERED",
            "python_consumer_implementation": "UNBOUND",
            "javascript_consumer_implementation": "UNBOUND",
            "host_binding": "UNBOUND",
            "browser_review": "NOT_RUN",
            "current_activation": "UNAUTHORIZED",
            "paper_permission": "UNAUTHORIZED",
            "live_permission": "UNAUTHORIZED",
        },
        "host_plan": {
            "python_consumer_module": None,
            "payload_source_provider": None,
            "app_importer": None,
            "route": None,
            "endpoint": None,
            "javascript_consumer_module": None,
            "html_script": None,
            "stylesheet_link": None,
            "mount_slot": None,
            "browser_review_receipt": None,
        },
        "activation_order": [
            "VERIFY_EXACT_ADR0309_ADAPTER_REGISTRATION",
            "VERIFY_ADR0310_CONSUMER_PREREGISTRATION",
            "IMPLEMENT_PYTHON_HASH_ONLY_SOURCE_IN_SEPARATE_VERSION",
            "VALIDATE_PYTHON_CONSUMER_WITH_SYNTHETIC_INPUTS",
            "IMPLEMENT_JAVASCRIPT_INSPECTION_CONSUMER_IN_SEPARATE_VERSION",
            "VALIDATE_JAVASCRIPT_CONSUMER_WITH_SYNTHETIC_ENVELOPES",
            "DECLARE_HOST_BINDINGS_IN_SEPARATE_VERSION",
            "RUN_AUTHORIZED_BROWSER_REVIEW_BEFORE_ANY_MOUNT",
            "CONSIDER_CURRENT_ONLY_BY_SEPARATE_EXPLICIT_DECISION",
        ],
        "facts": {
            "predecessor_exactly_verified": True,
            "predecessor_source_pins_declared": True,
            "subcontracts_hash_pinned": True,
            "consumer_contracts_preregistered": True,
            "python_consumer_implemented": False,
            "javascript_consumer_implemented": False,
            "host_bindings_declared": False,
            "adapter_executed": False,
            "browser_executed": False,
            "dom_mounted": False,
            "runtime_mutations_performed": False,
            "current_activated": False,
            "profitability_proven": False,
        },
        "blockers": [
            "PYTHON_CONSUMER_IMPLEMENTATION_UNBOUND",
            "JAVASCRIPT_CONSUMER_IMPLEMENTATION_UNBOUND",
            "PAYLOAD_SOURCE_PROVIDER_UNBOUND",
            "HOST_IMPORT_ROUTE_AND_ENDPOINT_UNBOUND",
            "HTML_STYLESHEET_AND_MOUNT_SLOT_UNBOUND",
            "AUTHORIZED_BROWSER_REVIEW_NOT_RUN",
            "CURRENT_ACTIVATION_NOT_AUTHORIZED",
            "PAPER_AND_LIVE_PERMISSION_NOT_AUTHORIZED",
        ],
        "authority": {
            "consumer_implementation_allowed": False,
            "consumer_execution_allowed": False,
            "adapter_execution_allowed": False,
            "payload_provider_binding_allowed": False,
            "app_import_allowed": False,
            "route_registration_allowed": False,
            "endpoint_registration_allowed": False,
            "html_script_binding_allowed": False,
            "stylesheet_link_binding_allowed": False,
            "runtime_asset_loading_allowed": False,
            "browser_execution_allowed": False,
            "dom_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
            "writer_allowed": False,
        },
        "decision": (
            "EXACT_ADR0309_ADAPTER_REGISTRATION_AND_TWO_CONSUMER_CONTRACTS_"
            "PREREGISTERED_PYTHON_JAVASCRIPT_HOST_ROUTE_BROWSER_MOUNT_CURRENT_"
            "PAPER_LIVE_AND_EXECUTION_UNBOUND"
        ),
    }
    return {
        **core,
        "consumer_preregistration_hash": strict_canonical_hash(core),
    }


def verify_portfolio_correlation_admission_effective_budget_delivery_adapter_consumer_preregistration_v1(
    document: Any,
) -> bool:
    """Return True only for the exact canonical ADR0310 preregistration."""

    if type(document) is not dict or not _is_native_json_tree(document):
        return False
    try:
        supplied_hash = document.get("consumer_preregistration_hash")
        if type(supplied_hash) is not str:
            return False
        core = {
            key: value
            for key, value in document.items()
            if key != "consumer_preregistration_hash"
        }
        if strict_canonical_hash(core) != supplied_hash:
            return False
        expected = (
            build_portfolio_correlation_admission_effective_budget_delivery_adapter_consumer_preregistration_v1()
        )
        return document == expected and strict_canonical_hash(document) == strict_canonical_hash(
            expected
        )
    except (KeyError, TypeError, ValueError, RuntimeError, RecursionError):
        return False
