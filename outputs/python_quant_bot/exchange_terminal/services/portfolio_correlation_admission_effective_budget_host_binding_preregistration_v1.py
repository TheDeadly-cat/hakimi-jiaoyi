"""Host-binding preregistration for the isolated correlation inspection chain.

This module records candidate slots and exact predecessor hashes. It does not
import the host, register a provider or route, load assets, or mount a view.
"""

from __future__ import annotations

from typing import Any

from exchange_terminal.services.portfolio_correlation_admission_effective_budget_cross_runtime_consumer_parity_registration_v1 import (
    build_portfolio_correlation_admission_effective_budget_cross_runtime_consumer_parity_registration_v1 as build_parity_registration_v1,
    strict_canonical_hash,
    verify_portfolio_correlation_admission_effective_budget_cross_runtime_consumer_parity_registration_v1 as verify_parity_registration_v1,
)


SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-host-binding-"
    "preregistration-v1"
)
STATIC_FINGERPRINT = (
    "20260824-portfolio-correlation-admission-effective-budget-host-binding-"
    "preregistration-v1-unbound-lock-1"
)
PREREGISTRATION_ID = (
    "portfolio-correlation-admission-effective-budget-host-binding-candidates-v1"
)
STATUS = "BLOCKED"
REGISTRATION_STATE = "HOST_BINDING_CANDIDATES_PREREGISTERED_ALL_ACTIVE_SLOTS_NULL"

PARITY_REGISTRATION_HASH = (
    "5870b0bb4729b37a8638600c04fffdfbf45f5240f9c6f613cb3401431bffb394"
)
PARITY_MATRIX_HASH = (
    "5ca94940147858aff54a658568f61b453e19ee5ff6468d68c6657e8249a74a61"
)
CONSUMER_PAIR_HASH = (
    "e5aa8d8b0b1ee3ab24891b1323edcbafca72203dd265d218f82eaa8f3789b578"
)
ACCEPTANCE_CONTRACT_HASH = (
    "aa7fdfa58f5d27e2156767e1c3825712fa172e2c7207fd0ff4e05d628a80edad"
)
PREDECESSOR_HOST_PLAN_HASH = (
    "a977ace0fac1bb45272806a88889e810bf683c88451490e3b1b881ce43eeff93"
)
PREDECESSOR_AUTHORITY_HASH = (
    "d56b3bfead89a10583a2a2efc98729508d4a57b075bc5a99de7e1083d73e6fcd"
)
PREDECESSOR_ACTIVATION_ORDER_HASH = (
    "079e96f7afcfc37296faddfa0f66575a0fabf3ec26c2151ad0621af458086e25"
)
ACCEPTANCE_RECEIPT_HASH = (
    "40c9af419f810b36ee32fd6ed29b1967b6394427d4ad828b3e3374c171593807"
)
STATE_RECEIPTS_HASH = (
    "d62c0582ac3b212897f2c582846ce1bfc2a731e3dc444d1e6dcbda0eebf64380"
)
ACCEPTANCE_FACTS_HASH = (
    "0aa9dacc257237cd4f174296866d8b4eaa9f2b162444b984ef152ecb10f0dda2"
)

PARITY_IMPLEMENTATION_SHA256 = (
    "366d5850dbdbc0da5e2f7c870304dd4837ac28b38020a1fc35376720131c4e68"
)
PARITY_TEST_SHA256 = (
    "0dcf44997ebaf07b3923a4be19f2c80c07aab836e74652c8bb343474544c42b5"
)
PARITY_FIXTURE_SHA256 = (
    "761072df49eca0f8622da4f33ee8ecb0ad4bf4070f7d467906186b7788ec4b02"
)
ACCEPTANCE_IMPLEMENTATION_SHA256 = (
    "5d848c691ab3e7bbb5528a3bfe818dfc6ab428743f1c9680691a0968e82ad245"
)
ACCEPTANCE_TEST_SHA256 = (
    "f072cef4e6a2cdc9b1d205ec89df34e8db8940db2ca5b4d2edb3ffbbf2f002f6"
)
PARITY_ADR_SHA256 = (
    "c36d5f262be23b69ad31522b6bd9de713584cc8b51f798dd03c30f843b80cffb"
)

PYTHON_PROVIDER_SHA256 = (
    "ec7de6b7dfdd30d4c29d9156551fd62525516a48e52cfc2cd945acc7b959eeca"
)
STRICT_CANONICAL_JAVASCRIPT_SHA256 = (
    "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39"
)
DELIVERY_JAVASCRIPT_SHA256 = (
    "867f7a7016472101a3606f2af22ae7b63509cc2afb3d2dbfe8f7058da8e08be0"
)
BRIDGE_JAVASCRIPT_SHA256 = (
    "67f16fa7946aee1c552b85bbb9758c84149a5cf657b7af5f78dad5ed0f7149d7"
)
BRIDGE_STYLESHEET_SHA256 = (
    "741d618c1fbfb76d0205e3ae3c9bff0b8b9bfacfa7f7cee6eb0e40b8761b2fc8"
)
INSPECTION_CONSUMER_JAVASCRIPT_SHA256 = (
    "7ea19bbcf27a40657623f2f1a5b503e3b834939d4e08519a4455d95b3255b5e6"
)
PARITY_ACCEPTANCE_JAVASCRIPT_SHA256 = ACCEPTANCE_IMPLEMENTATION_SHA256
PROTECTED_STYLESHEET_SHA256 = (
    "ee6a5ae746142e32df768fe3261746f66c2b1a902e38b85fa9c0ecc4ce7bdc2a"
)

PYTHON_RESULT_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-hash-envelope-"
    "source-consumer-result-v1"
)
JAVASCRIPT_RESULT_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-inspection-consumer-result-v1"
)
ACCEPTANCE_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-cross-runtime-"
    "consumer-parity-acceptance-receipt-v1"
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
    predecessor = build_parity_registration_v1()
    if not verify_parity_registration_v1(predecessor):
        raise ValueError("ADR0313 parity registration did not verify exactly")
    exact = {
        "parity_registration_hash": PARITY_REGISTRATION_HASH,
        "parity_matrix_hash": PARITY_MATRIX_HASH,
        "consumer_pair_hash": CONSUMER_PAIR_HASH,
    }
    if any(predecessor.get(key) != value for key, value in exact.items()):
        raise ValueError("ADR0313 parity identity drifted")
    hashes = {
        "acceptance_contract": ACCEPTANCE_CONTRACT_HASH,
        "host_plan": PREDECESSOR_HOST_PLAN_HASH,
        "authority": PREDECESSOR_AUTHORITY_HASH,
        "activation_order": PREDECESSOR_ACTIVATION_ORDER_HASH,
        "consumer_contracts": CONSUMER_PAIR_HASH,
    }
    for key, expected in hashes.items():
        if strict_canonical_hash(predecessor.get(key)) != expected:
            raise ValueError(f"ADR0313 {key} drifted")
    if any(value is not None for value in predecessor["host_plan"].values()):
        raise ValueError("ADR0313 host plan is no longer unbound")
    if any(value is not False for value in predecessor["authority"].values()):
        raise ValueError("ADR0313 authority is no longer locked")
    return predecessor


def _javascript_assets() -> list[dict[str, Any]]:
    return [
        {
            "asset_id": "strict-canonical-json-v1",
            "path": "exchange_terminal/static/strict_canonical_json_v1.js",
            "sha256": STRICT_CANONICAL_JAVASCRIPT_SHA256,
            "role": "CANONICAL_HASH_DEPENDENCY",
            "script_binding": None,
        },
        {
            "asset_id": "correlation-delivery-adapter-v1",
            "path": (
                "exchange_terminal/static/"
                "evidence_portfolio_correlation_admission_effective_budget_"
                "in_memory_delivery_v1.js"
            ),
            "sha256": DELIVERY_JAVASCRIPT_SHA256,
            "role": "ENVELOPE_VERIFY_AND_EXTRACT",
            "script_binding": None,
        },
        {
            "asset_id": "correlation-bridge-v1",
            "path": (
                "exchange_terminal/static/"
                "evidence_portfolio_correlation_admission_effective_budget_"
                "bridge_v1.js"
            ),
            "sha256": BRIDGE_JAVASCRIPT_SHA256,
            "role": "UNMOUNTED_VIEW_MODEL_AND_MARKUP",
            "script_binding": None,
        },
        {
            "asset_id": "correlation-inspection-consumer-v1",
            "path": (
                "exchange_terminal/static/"
                "evidence_portfolio_correlation_admission_effective_budget_"
                "inspection_consumer_v1.js"
            ),
            "sha256": INSPECTION_CONSUMER_JAVASCRIPT_SHA256,
            "role": "PYTHON_RESULT_VERIFY_AND_PRESENT",
            "script_binding": None,
        },
        {
            "asset_id": "correlation-parity-acceptance-v1",
            "path": (
                "exchange_terminal/static/"
                "evidence_portfolio_correlation_admission_effective_budget_"
                "cross_runtime_consumer_parity_acceptance_v1.js"
            ),
            "sha256": PARITY_ACCEPTANCE_JAVASCRIPT_SHA256,
            "role": "THREE_STATE_PARITY_ACCEPTANCE",
            "script_binding": None,
        },
    ]


def build_portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1() -> dict[str, Any]:
    _build_exact_predecessor()
    assets = _javascript_assets()
    load_order = [asset["path"] for asset in assets]
    binding_candidates: dict[str, Any] = {
        "python_provider": {
            "contract_id": "correlation-hash-envelope-provider-v1",
            "module_path": (
                "exchange_terminal/services/"
                "portfolio_correlation_admission_effective_budget_hash_"
                "envelope_source_consumer_v1.py"
            ),
            "module_sha256": PYTHON_PROVIDER_SHA256,
            "callable": (
                "build_portfolio_correlation_admission_effective_budget_"
                "hash_envelope_source_consumer_v1"
            ),
            "input_mode": "INTERNAL_EXACT_SOURCE_CHAIN_ONLY",
            "output_schema_version": PYTHON_RESULT_SCHEMA_VERSION,
            "active_import": None,
            "provider_registration": None,
            "bound": False,
        },
        "http_projection": {
            "contract_id": "correlation-hash-envelope-readonly-projection-v1",
            "input_source": "INTERNAL_PROVIDER_RESULT_ONLY",
            "output_schema_version": PYTHON_RESULT_SCHEMA_VERSION,
            "raw_source_inputs_allowed": False,
            "handler": None,
            "route": None,
            "endpoint": None,
            "bound": False,
        },
        "javascript_assets": {
            "assets": assets,
            "asset_manifest_hash": strict_canonical_hash(assets),
            "load_order": load_order,
            "load_order_hash": strict_canonical_hash(load_order),
            "runtime_loader": None,
            "bound": False,
        },
        "stylesheet": {
            "isolated_path": (
                "exchange_terminal/static/"
                "evidence_portfolio_correlation_admission_effective_budget_"
                "bridge_v1.css"
            ),
            "isolated_sha256": BRIDGE_STYLESHEET_SHA256,
            "protected_stylesheet_path": "exchange_terminal/static/styles.css",
            "protected_stylesheet_sha256": PROTECTED_STYLESHEET_SHA256,
            "protected_stylesheet_mutation_allowed": False,
            "link_binding": None,
            "bound": False,
        },
        "mount": {
            "slot_contract_id": "correlation-inspection-bridge-slot-v1",
            "input_schema_version": JAVASCRIPT_RESULT_SCHEMA_VERSION,
            "selector": None,
            "mount_function": None,
            "browser_review_receipt": None,
            "bound": False,
        },
    }
    core: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "preregistration_id": PREREGISTRATION_ID,
        "status": STATUS,
        "registration_state": REGISTRATION_STATE,
        "predecessor_contract": {
            "parity_registration_hash": PARITY_REGISTRATION_HASH,
            "parity_matrix_hash": PARITY_MATRIX_HASH,
            "consumer_pair_hash": CONSUMER_PAIR_HASH,
            "acceptance_contract_hash": ACCEPTANCE_CONTRACT_HASH,
            "host_plan_hash": PREDECESSOR_HOST_PLAN_HASH,
            "authority_hash": PREDECESSOR_AUTHORITY_HASH,
            "activation_order_hash": PREDECESSOR_ACTIVATION_ORDER_HASH,
            "implementation_path": (
                "exchange_terminal/services/"
                "portfolio_correlation_admission_effective_budget_cross_"
                "runtime_consumer_parity_registration_v1.py"
            ),
            "implementation_sha256": PARITY_IMPLEMENTATION_SHA256,
            "test_path": (
                "tests/test_portfolio_correlation_admission_effective_budget_"
                "cross_runtime_consumer_parity_registration_v1.py"
            ),
            "test_sha256": PARITY_TEST_SHA256,
            "fixture_path": (
                "tests/fixtures/"
                "portfolio_correlation_admission_effective_budget_cross_"
                "runtime_consumer_parity_registration_v1.json"
            ),
            "fixture_sha256": PARITY_FIXTURE_SHA256,
            "acceptance_implementation_path": (
                "exchange_terminal/static/"
                "evidence_portfolio_correlation_admission_effective_budget_"
                "cross_runtime_consumer_parity_acceptance_v1.js"
            ),
            "acceptance_implementation_sha256": ACCEPTANCE_IMPLEMENTATION_SHA256,
            "acceptance_test_path": (
                "exchange_terminal/static/"
                "evidence_portfolio_correlation_admission_effective_budget_"
                "cross_runtime_consumer_parity_acceptance_v1.test.js"
            ),
            "acceptance_test_sha256": ACCEPTANCE_TEST_SHA256,
            "adr_path": (
                "docs/adr/0313-portfolio-correlation-admission-effective-"
                "budget-cross-runtime-consumer-parity-v1.md"
            ),
            "adr_sha256": PARITY_ADR_SHA256,
        },
        "required_acceptance": {
            "schema_version": ACCEPTANCE_SCHEMA_VERSION,
            "status": "EXACT",
            "acceptance_receipt_hash": ACCEPTANCE_RECEIPT_HASH,
            "state_receipts_hash": STATE_RECEIPTS_HASH,
            "facts_hash": ACCEPTANCE_FACTS_HASH,
            "receipt_binding": None,
            "verified_by_host": False,
        },
        "binding_candidates": binding_candidates,
        "binding_candidates_hash": strict_canonical_hash(binding_candidates),
        "active_host_plan": {
            "python_provider": None,
            "app_import": None,
            "http_handler": None,
            "route": None,
            "endpoint": None,
            "javascript_loader": None,
            "script_bindings": None,
            "stylesheet_link": None,
            "mount_selector": None,
            "browser_review_receipt": None,
        },
        "activation_order": [
            "VERIFY_EXACT_ADR0313_PARITY_REGISTRATION",
            "VERIFY_EXACT_ADR0313_ACCEPTANCE_RECEIPT",
            "VERIFY_ADR0314_HOST_BINDING_PREREGISTRATION",
            "UPDATE_STATIC_ASSET_REGISTRATION_IN_SEPARATE_VERSION",
            "IMPLEMENT_PYTHON_PROVIDER_BINDING_IN_SEPARATE_VERSION",
            "IMPLEMENT_READONLY_HTTP_PROJECTION_IN_SEPARATE_VERSION",
            "IMPLEMENT_JAVASCRIPT_HOST_LOADING_IN_SEPARATE_VERSION",
            "RUN_AUTHORIZED_BROWSER_REVIEW_BEFORE_ANY_MOUNT",
            "CONSIDER_CURRENT_ONLY_BY_SEPARATE_EXPLICIT_DECISION",
        ],
        "facts": {
            "parity_registration_exactly_verified": True,
            "acceptance_receipt_hash_pinned": True,
            "binding_candidates_preregistered": True,
            "python_provider_bound": False,
            "http_projection_bound": False,
            "javascript_assets_bound": False,
            "stylesheet_bound": False,
            "mount_slot_bound": False,
            "browser_executed": False,
            "dom_mounted": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "blockers": [
            "ADR0314_PREREGISTRATION_ONLY",
            "ADR0312_AND_ADR0313_STATIC_ASSET_REGISTRATION_UPDATE_REQUIRED",
            "PYTHON_PROVIDER_BINDING_NOT_IMPLEMENTED",
            "READONLY_HTTP_PROJECTION_NOT_IMPLEMENTED",
            "JAVASCRIPT_HOST_LOADING_NOT_IMPLEMENTED",
            "STYLESHEET_LINK_AND_MOUNT_SELECTOR_UNBOUND",
            "AUTHORIZED_BROWSER_REVIEW_NOT_RUN",
            "CURRENT_ACTIVATION_NOT_AUTHORIZED",
            "PAPER_AND_LIVE_PERMISSION_NOT_AUTHORIZED",
        ],
        "authority": {
            "acceptance_binding_allowed": False,
            "python_provider_binding_allowed": False,
            "app_import_allowed": False,
            "http_projection_binding_allowed": False,
            "route_registration_allowed": False,
            "endpoint_registration_allowed": False,
            "runtime_asset_loading_allowed": False,
            "html_script_binding_allowed": False,
            "stylesheet_link_binding_allowed": False,
            "browser_execution_allowed": False,
            "dom_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
            "writer_allowed": False,
        },
        "decision": (
            "EXACT_ADR0313_PARITY_AND_ACCEPTANCE_HASHES_PINNED_HOST_BINDING_"
            "CANDIDATES_PREREGISTERED_ALL_ACTIVE_BINDINGS_AND_AUTHORITY_NULL"
        ),
    }
    return {
        **core,
        "host_binding_preregistration_hash": strict_canonical_hash(core),
    }


def verify_portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1(
    document: Any,
) -> bool:
    if type(document) is not dict or not _is_native_json_tree(document):
        return False
    try:
        supplied_hash = document.get("host_binding_preregistration_hash")
        if type(supplied_hash) is not str:
            return False
        core = {
            key: value
            for key, value in document.items()
            if key != "host_binding_preregistration_hash"
        }
        if strict_canonical_hash(core) != supplied_hash:
            return False
        expected = build_portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1()
        return document == expected and strict_canonical_hash(document) == strict_canonical_hash(
            expected
        )
    except (KeyError, TypeError, ValueError, RuntimeError, RecursionError):
        return False
