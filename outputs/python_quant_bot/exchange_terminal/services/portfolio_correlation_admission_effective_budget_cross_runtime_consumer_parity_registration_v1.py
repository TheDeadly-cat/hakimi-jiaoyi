"""Exact cross-runtime parity registration for isolated correlation consumers."""

from __future__ import annotations

from typing import Any

from exchange_terminal.services.portfolio_correlation_admission_effective_budget_delivery_adapter_consumer_preregistration_v1 import (
    strict_canonical_hash,
    verify_portfolio_correlation_admission_effective_budget_delivery_adapter_consumer_preregistration_v1 as verify_consumer_preregistration_v1,
)


SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-cross-runtime-"
    "consumer-parity-registration-v1"
)
STATIC_FINGERPRINT = (
    "20260824-portfolio-correlation-admission-effective-budget-cross-runtime-"
    "consumer-parity-registration-v1-unbound-lock-1"
)
REGISTRATION_ID = (
    "portfolio-correlation-admission-effective-budget-cross-runtime-consumer-parity-v1"
)
STATUS = "BLOCKED"
REGISTRATION_STATE = "THREE_STATE_CROSS_RUNTIME_CONSUMER_PARITY_REGISTERED_UNBOUND"

CONSUMER_PREREGISTRATION_HASH = (
    "4cc6352fb4083d8589d656481ecfd8fe3a33d6bba44bac6383ce2ca1f6d72987"
)
PYTHON_CONSUMER_CONTRACT_HASH = (
    "fd402270f5c03c5225201f9df8768859b398cc1912658a0880f367ff7afc882a"
)
JAVASCRIPT_CONSUMER_CONTRACT_HASH = (
    "1966892253b987f98ae8e8814692ec6f94387d2f9191ca7416447802382bbb8f"
)

PYTHON_CONSUMER_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-hash-envelope-"
    "source-consumer-result-v1"
)
PYTHON_CONSUMER_STATIC_FINGERPRINT = (
    "20260824-portfolio-correlation-admission-effective-budget-hash-envelope-"
    "source-consumer-v1-isolated-lock-1"
)
PYTHON_CONSUMER_ID = (
    "portfolio-correlation-admission-effective-budget-hash-envelope-source-v1"
)
PYTHON_CONSUMER_IMPLEMENTATION_SHA256 = (
    "ec7de6b7dfdd30d4c29d9156551fd62525516a48e52cfc2cd945acc7b959eeca"
)
PYTHON_CONSUMER_TEST_SHA256 = (
    "3ff87343beccd2f22d95be20e989886fbde6539a29d81a4730d56ab552addc92"
)
PYTHON_CONSUMER_ADR_SHA256 = (
    "06f2385cd3a302c5311f6685afb917e81f184ccaec79fca228a19dad86a23558"
)

JAVASCRIPT_CONSUMER_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-inspection-consumer-result-v1"
)
JAVASCRIPT_CONSUMER_STATIC_FINGERPRINT = (
    "20260824-portfolio-correlation-admission-effective-budget-inspection-"
    "consumer-v1-isolated-lock-1"
)
JAVASCRIPT_CONSUMER_ID = (
    "portfolio-correlation-admission-effective-budget-inspection-bridge-v1"
)
JAVASCRIPT_CONSUMER_GLOBAL = (
    "HakimiPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1"
)
JAVASCRIPT_CONSUMER_IMPLEMENTATION_SHA256 = (
    "7ea19bbcf27a40657623f2f1a5b503e3b834939d4e08519a4455d95b3255b5e6"
)
JAVASCRIPT_CONSUMER_TEST_SHA256 = (
    "2fa4f1b2f9abc044e483ca66f3fd3decce10287d18646353b9b7e72b28df680f"
)
JAVASCRIPT_CONSUMER_FIXTURE_SHA256 = (
    "b25be196152f370101bc43cf61e065308761d3070c4edb4656ffd00ad287dbe7"
)
JAVASCRIPT_CONSUMER_FIXTURE_CANONICAL_HASH = (
    "3cc4e1a759ef01fe4b8e5441250e307ee0fad9d0b6023608987c50e97da9ea0b"
)
JAVASCRIPT_CONSUMER_ADR_SHA256 = (
    "e4ab75bf5ac2579843668ec97bfa9cf22ea01e8b63e36f1fb577ce5f6763a718"
)

ACCEPTANCE_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-cross-runtime-"
    "consumer-parity-acceptance-receipt-v1"
)
ACCEPTANCE_STATIC_FINGERPRINT = (
    "20260824-portfolio-correlation-admission-effective-budget-cross-runtime-"
    "consumer-parity-acceptance-v1-unbound-lock-1"
)
ACCEPTANCE_BROWSER_GLOBAL = (
    "HakimiPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1"
)

STATUS_MAPPING_HASH = (
    "f0332296b3370e75810d172cbc261b13327e25f8b77f0d7f9c83d80df7bd3014"
)
STATE_ORDER = ("KNOWN", "UNKNOWN", "BLOCKED")


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


def _python_consumer_contract() -> dict[str, Any]:
    return {
        "consumer_id": PYTHON_CONSUMER_ID,
        "runtime": "PYTHON",
        "role": "HASH_ONLY_IN_MEMORY_ENVELOPE_SOURCE",
        "schema_version": PYTHON_CONSUMER_SCHEMA_VERSION,
        "static_fingerprint": PYTHON_CONSUMER_STATIC_FINGERPRINT,
        "implementation_path": (
            "exchange_terminal/services/"
            "portfolio_correlation_admission_effective_budget_hash_envelope_"
            "source_consumer_v1.py"
        ),
        "implementation_sha256": PYTHON_CONSUMER_IMPLEMENTATION_SHA256,
        "test_path": (
            "tests/test_portfolio_correlation_admission_effective_budget_"
            "hash_envelope_source_consumer_v1.py"
        ),
        "test_sha256": PYTHON_CONSUMER_TEST_SHA256,
        "adr_path": (
            "docs/adr/0311-portfolio-correlation-admission-effective-budget-"
            "hash-envelope-source-consumer-v1.md"
        ),
        "adr_sha256": PYTHON_CONSUMER_ADR_SHA256,
        "host_binding": None,
    }


def _javascript_consumer_contract() -> dict[str, Any]:
    return {
        "consumer_id": JAVASCRIPT_CONSUMER_ID,
        "runtime": "JAVASCRIPT",
        "role": "VERIFY_EXTRACT_AND_BUILD_UNMOUNTED_INSPECTION_BRIDGE",
        "schema_version": JAVASCRIPT_CONSUMER_SCHEMA_VERSION,
        "static_fingerprint": JAVASCRIPT_CONSUMER_STATIC_FINGERPRINT,
        "browser_global": JAVASCRIPT_CONSUMER_GLOBAL,
        "implementation_path": (
            "exchange_terminal/static/"
            "evidence_portfolio_correlation_admission_effective_budget_"
            "inspection_consumer_v1.js"
        ),
        "implementation_sha256": JAVASCRIPT_CONSUMER_IMPLEMENTATION_SHA256,
        "test_path": (
            "exchange_terminal/static/"
            "evidence_portfolio_correlation_admission_effective_budget_"
            "inspection_consumer_v1.test.js"
        ),
        "test_sha256": JAVASCRIPT_CONSUMER_TEST_SHA256,
        "fixture_path": (
            "tests/fixtures/"
            "portfolio_correlation_admission_effective_budget_hash_envelope_"
            "source_consumer_v1.json"
        ),
        "fixture_sha256": JAVASCRIPT_CONSUMER_FIXTURE_SHA256,
        "fixture_canonical_hash": JAVASCRIPT_CONSUMER_FIXTURE_CANONICAL_HASH,
        "adr_path": (
            "docs/adr/0312-portfolio-correlation-admission-effective-budget-"
            "inspection-consumer-v1.md"
        ),
        "adr_sha256": JAVASCRIPT_CONSUMER_ADR_SHA256,
        "host_script": None,
        "host_stylesheet": None,
        "mount_slot": None,
    }


def _parity_matrix() -> list[dict[str, Any]]:
    return [
        {
            "state": "KNOWN",
            "python_status": "KNOWN",
            "javascript_status": "KNOWN",
            "python_result_hash": (
                "4271f49558382127bb0e1e737ca080686c305907e60e0b5514aded14a98e7b96"
            ),
            "python_envelope_hash": (
                "2bafa66dbb13a0bfe4e927edd91129003177fed0b2f4bc2e788d793b597803c3"
            ),
            "javascript_result_hash": (
                "5e88bb5f5ce875ef2a8b22315487e26a7069a3a16da936461c5f2602b7a23390"
            ),
            "extraction_receipt_hash": (
                "b2991d361f45421a59ceb6980692ecb892bfc60bc41c2691c7f2ac980d6804b3"
            ),
            "presentation_hash": (
                "55e67227c3ad29378d06b5bb8f29db5b3b20981a988f69cadf074298b49c4e5d"
            ),
            "markup_hash": (
                "b7f8be93a4cc11bfdd97436f748ab5c673f086b4c4ae980f55e5effbff84a734"
            ),
            "bridge_status_label": "LOCAL ALIGNMENT",
            "source_hash_policy": "EXACT_64_HEX",
        },
        {
            "state": "UNKNOWN",
            "python_status": "UNKNOWN",
            "javascript_status": "UNKNOWN",
            "python_result_hash": (
                "6c67f3e287102d467c5a22f3ff57a2130a40654c7ee994cc560bba4673b04273"
            ),
            "python_envelope_hash": (
                "a5136b988cf6baed8f1009b786828c855c493935e5ff9af570e110834972993c"
            ),
            "javascript_result_hash": (
                "4c438a0de624b03c54d4dbb78a10c9ec3b93ca7deadcbea875d28c00e4d87e15"
            ),
            "extraction_receipt_hash": (
                "14aacd9131f3d8c9131ba4e116d0eb52be26a0e110624b5b89df5e1be8c1e778"
            ),
            "presentation_hash": (
                "9efdb0d85e5176a92ae4acb35686573b7cb769553d031015ed403817c349c2c5"
            ),
            "markup_hash": (
                "57441de8a2b73e502c68ac51bcd923cf65699f7b66a970ba2512321aab74cdac"
            ),
            "bridge_status_label": "SOURCE UNKNOWN",
            "source_hash_policy": "ALL_NULL",
        },
        {
            "state": "BLOCKED",
            "python_status": "BLOCKED",
            "javascript_status": "BLOCKED",
            "python_result_hash": (
                "a762ed471125031bf15ed39290b8a6e778454dfa68f07500a473d60f0b8fe9f3"
            ),
            "python_envelope_hash": None,
            "javascript_result_hash": (
                "cb4d03284f25cd05a58563d63ef2a6cf51ce9ebe541ba6fb9d5f795f21e9fabc"
            ),
            "extraction_receipt_hash": None,
            "presentation_hash": None,
            "markup_hash": None,
            "bridge_status_label": None,
            "source_hash_policy": "ALL_NULL",
        },
    ]


def build_portfolio_correlation_admission_effective_budget_cross_runtime_consumer_parity_registration_v1() -> dict[str, Any]:
    consumers = [_python_consumer_contract(), _javascript_consumer_contract()]
    matrix = _parity_matrix()
    core: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "registration_id": REGISTRATION_ID,
        "status": STATUS,
        "registration_state": REGISTRATION_STATE,
        "consumer_preregistration": {
            "registration_hash": CONSUMER_PREREGISTRATION_HASH,
            "python_consumer_contract_hash": PYTHON_CONSUMER_CONTRACT_HASH,
            "javascript_consumer_contract_hash": JAVASCRIPT_CONSUMER_CONTRACT_HASH,
            "host_binding_required": False,
        },
        "consumer_contracts": consumers,
        "consumer_pair_hash": strict_canonical_hash(consumers),
        "parity_policy": {
            "state_order": list(STATE_ORDER),
            "python_to_javascript_mapping": {
                "KNOWN": "KNOWN",
                "UNKNOWN": "UNKNOWN",
                "BLOCKED": "BLOCKED",
            },
            "status_mapping_hash": STATUS_MAPPING_HASH,
            "known_source_hash_policy": "EXACT_64_HEX",
            "unknown_source_hash_policy": "ALL_NULL",
            "blocked_source_hash_policy": "ALL_NULL",
            "known_unknown_markup_must_differ": True,
            "known_bridge_status_label": "LOCAL ALIGNMENT",
            "unknown_bridge_status_label": "SOURCE UNKNOWN",
            "ready_word_allowed": False,
            "raw_source_evidence_embedded": False,
        },
        "parity_matrix": matrix,
        "parity_matrix_hash": strict_canonical_hash(matrix),
        "acceptance_contract": {
            "schema_version": ACCEPTANCE_SCHEMA_VERSION,
            "static_fingerprint": ACCEPTANCE_STATIC_FINGERPRINT,
            "browser_global": ACCEPTANCE_BROWSER_GLOBAL,
            "registration_input_mode": "SEALED_IN_MEMORY_ARGUMENT_ONLY",
            "fixture_input_mode": "SEALED_SYNTHETIC_THREE_STATE_ARGUMENT_ONLY",
            "output_mode": "HASH_ONLY_ACCEPTANCE_RECEIPT",
            "raw_state_documents_embedded": False,
            "host_binding": None,
        },
        "host_plan": {
            "python_provider": None,
            "javascript_module": None,
            "host_script": None,
            "host_stylesheet": None,
            "route": None,
            "endpoint": None,
            "mount_slot": None,
            "browser_review_receipt": None,
        },
        "activation_order": [
            "VERIFY_EXACT_ADR0310_CONSUMER_PREREGISTRATION",
            "VERIFY_ADR0313_PARITY_REGISTRATION",
            "VERIFY_SYNTHETIC_THREE_STATE_FIXTURE",
            "BUILD_ISOLATED_JAVASCRIPT_RESULTS",
            "VERIFY_THREE_STATE_PARITY_ACCEPTANCE_RECEIPT",
            "DECLARE_HOST_BINDINGS_IN_SEPARATE_VERSION",
            "RUN_AUTHORIZED_BROWSER_REVIEW_BEFORE_ANY_MOUNT",
            "CONSIDER_CURRENT_ONLY_BY_SEPARATE_EXPLICIT_DECISION",
        ],
        "facts": {
            "consumer_preregistration_hash_pinned": True,
            "python_consumer_source_pinned": True,
            "javascript_consumer_source_pinned": True,
            "synthetic_fixture_pinned": True,
            "three_state_parity_registered": True,
            "acceptance_executed": False,
            "host_bindings_declared": False,
            "browser_executed": False,
            "dom_mounted": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "blockers": [
            "PARITY_ACCEPTANCE_RECEIPT_NOT_YET_BOUND",
            "PYTHON_PROVIDER_UNBOUND",
            "JAVASCRIPT_HOST_MODULE_UNBOUND",
            "HOST_SCRIPT_STYLESHEET_ROUTE_ENDPOINT_AND_MOUNT_UNBOUND",
            "AUTHORIZED_BROWSER_REVIEW_NOT_RUN",
            "CURRENT_ACTIVATION_NOT_AUTHORIZED",
            "PAPER_AND_LIVE_PERMISSION_NOT_AUTHORIZED",
        ],
        "authority": {
            "acceptance_execution_allowed": False,
            "python_provider_binding_allowed": False,
            "javascript_module_binding_allowed": False,
            "app_import_allowed": False,
            "route_registration_allowed": False,
            "endpoint_registration_allowed": False,
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
            "THREE_STATE_PYTHON_JAVASCRIPT_CONSUMER_PARITY_REGISTERED_"
            "ACCEPTANCE_HOST_BROWSER_DOM_CURRENT_PAPER_AND_LIVE_UNBOUND"
        ),
    }
    return {
        **core,
        "parity_registration_hash": strict_canonical_hash(core),
    }


def verify_portfolio_correlation_admission_effective_budget_cross_runtime_consumer_parity_registration_v1(
    document: Any,
) -> bool:
    if type(document) is not dict or not _is_native_json_tree(document):
        return False
    try:
        supplied_hash = document.get("parity_registration_hash")
        if type(supplied_hash) is not str:
            return False
        core = {
            key: value
            for key, value in document.items()
            if key != "parity_registration_hash"
        }
        if strict_canonical_hash(core) != supplied_hash:
            return False
        expected = build_portfolio_correlation_admission_effective_budget_cross_runtime_consumer_parity_registration_v1()
        return document == expected and strict_canonical_hash(document) == strict_canonical_hash(
            expected
        )
    except (KeyError, TypeError, ValueError, RuntimeError, RecursionError):
        return False
