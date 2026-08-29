"""Isolated Python consumer for the correlation delivery envelope.

The consumer enforces the exact ADR0309 adapter registration and ADR0310
consumer preregistration before invoking the pure ADR0306 in-memory adapter.
It has no provider, route, persistence, scheduler, browser, or trading authority.
"""

from __future__ import annotations

from typing import Any

from exchange_terminal.services.portfolio_correlation_admission_effective_budget_delivery_adapter_consumer_preregistration_v1 import (
    strict_canonical_hash,
    verify_portfolio_correlation_admission_effective_budget_delivery_adapter_consumer_preregistration_v1 as verify_consumer_preregistration_v1,
)
from exchange_terminal.services.portfolio_correlation_admission_effective_budget_in_memory_delivery_adapter_registration_v1 import (
    verify_portfolio_correlation_admission_effective_budget_in_memory_delivery_adapter_registration_v1 as verify_adapter_registration_v1,
)
from exchange_terminal.services.portfolio_correlation_admission_effective_budget_in_memory_delivery_v1 import (
    PAYLOAD_SCHEMA_VERSION as DELIVERY_PAYLOAD_SCHEMA_VERSION,
    SCHEMA_VERSION as DELIVERY_SCHEMA_VERSION,
    STATIC_FINGERPRINT as DELIVERY_STATIC_FINGERPRINT,
    build_portfolio_correlation_admission_effective_budget_in_memory_delivery_envelope_v1 as build_delivery_envelope_v1,
    verify_portfolio_correlation_admission_effective_budget_in_memory_delivery_envelope_v1 as verify_delivery_envelope_v1,
)


SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-hash-envelope-"
    "source-consumer-result-v1"
)
STATIC_FINGERPRINT = (
    "20260824-portfolio-correlation-admission-effective-budget-hash-envelope-"
    "source-consumer-v1-isolated-lock-1"
)
CONSUMER_ID = (
    "portfolio-correlation-admission-effective-budget-hash-envelope-source-v1"
)

ADAPTER_REGISTRATION_HASH = (
    "4c6eb60d842611d2babaf072527fe93d2a68f67bc6a7c2658b80fd1b9f07f4cb"
)
CONSUMER_PREREGISTRATION_HASH = (
    "4cc6352fb4083d8589d656481ecfd8fe3a33d6bba44bac6383ce2ca1f6d72987"
)
PYTHON_CONSUMER_CONTRACT_HASH = (
    "fd402270f5c03c5225201f9df8768859b398cc1912658a0880f367ff7afc882a"
)
PREREGISTRATION_AUTHORITY_HASH = (
    "0e657c14f87546c71ec1454c7e86fe044a597e704ddb4813d6ce46f5e6f406a6"
)
PREREGISTRATION_HOST_PLAN_HASH = (
    "639a93033c80d2f49629889d82051b32a57b46ddde727429345864818123768f"
)

PREREGISTRATION_IMPLEMENTATION_SHA256 = (
    "c789eb33f8791d136ca2c92886724596e82019470121cbb7af547aa26737b4cf"
)
PREREGISTRATION_TEST_SHA256 = (
    "cd73e1ec0c6191e3c1389dcc308a094e619d4322a31d5e70499ba1c27654e3b2"
)
PREREGISTRATION_ADR_SHA256 = (
    "facf9a7085edde72c1547a20bedeb52e1fc4dd471827271c3d3df9794ffc46fa"
)
DELIVERY_IMPLEMENTATION_SHA256 = (
    "9ada46b146fcecf48b96d9e5af1f4022ab23b4f0bbc5c1c39d59fb8d9a54d8db"
)
DELIVERY_TEST_SHA256 = (
    "d4b3e8a93aefe0eced326538d85ea49ffd8f6466098131a62a5b6bbb90716374"
)

FUNCTION_EXPORTS = (
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "CONSUMER_ID",
    "build_portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1",
    "verify_portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1",
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


def _assess_consumer_gate(
    adapter_registration_document: Any,
    consumer_preregistration_document: Any,
) -> dict[str, bool]:
    adapter_registration_exact = False
    consumer_preregistration_exact = False
    python_consumer_contract_exact = False
    python_consumer_unbound = False

    try:
        adapter_registration_exact = (
            type(adapter_registration_document) is dict
            and verify_adapter_registration_v1(adapter_registration_document)
            and adapter_registration_document.get("adapter_registration_hash")
            == ADAPTER_REGISTRATION_HASH
        )
    except (KeyError, TypeError, ValueError, RuntimeError, RecursionError):
        adapter_registration_exact = False

    try:
        consumer_preregistration_exact = (
            type(consumer_preregistration_document) is dict
            and verify_consumer_preregistration_v1(
                consumer_preregistration_document
            )
            and consumer_preregistration_document.get(
                "consumer_preregistration_hash"
            )
            == CONSUMER_PREREGISTRATION_HASH
            and strict_canonical_hash(
                consumer_preregistration_document.get("authority")
            )
            == PREREGISTRATION_AUTHORITY_HASH
            and strict_canonical_hash(
                consumer_preregistration_document.get("host_plan")
            )
            == PREREGISTRATION_HOST_PLAN_HASH
        )
        if consumer_preregistration_exact:
            consumers = consumer_preregistration_document["consumer_contracts"]
            python_consumer = consumers[0]
            python_consumer_contract_exact = (
                len(consumers) == 2
                and strict_canonical_hash(python_consumer)
                == PYTHON_CONSUMER_CONTRACT_HASH
                and python_consumer.get("consumer_id") == CONSUMER_ID
                and python_consumer.get("runtime") == "PYTHON"
                and python_consumer.get("role")
                == "HASH_ONLY_IN_MEMORY_ENVELOPE_SOURCE"
                and python_consumer.get("accepted_adapter_registration_hash")
                == ADAPTER_REGISTRATION_HASH
                and python_consumer.get("required_schema_version")
                == DELIVERY_SCHEMA_VERSION
                and python_consumer.get("required_static_fingerprint")
                == DELIVERY_STATIC_FINGERPRINT
                and python_consumer.get("required_payload_schema_version")
                == DELIVERY_PAYLOAD_SCHEMA_VERSION
            )
            python_consumer_unbound = (
                python_consumer_contract_exact
                and python_consumer.get("implementation_binding") is None
                and python_consumer.get("payload_source_provider") is None
                and python_consumer.get("host_slot") is None
                and python_consumer.get("implementation_bound") is False
                and python_consumer.get("execution_allowed") is False
                and python_consumer.get("route_allowed") is False
                and python_consumer.get("writer_allowed") is False
            )
    except (IndexError, KeyError, TypeError, ValueError, RuntimeError, RecursionError):
        consumer_preregistration_exact = False
        python_consumer_contract_exact = False
        python_consumer_unbound = False

    return {
        "adapter_registration_exact": adapter_registration_exact,
        "consumer_preregistration_exact": consumer_preregistration_exact,
        "python_consumer_contract_exact": python_consumer_contract_exact,
        "python_consumer_unbound": python_consumer_unbound,
    }


def _gate_blockers(gate: dict[str, bool]) -> list[str]:
    blockers: list[str] = []
    if not gate["adapter_registration_exact"]:
        blockers.append("ADAPTER_REGISTRATION_NOT_EXACT")
    if not gate["consumer_preregistration_exact"]:
        blockers.append("CONSUMER_PREREGISTRATION_NOT_EXACT")
    if not gate["python_consumer_contract_exact"]:
        blockers.append("PYTHON_CONSUMER_CONTRACT_NOT_EXACT")
    if not gate["python_consumer_unbound"]:
        blockers.append("PYTHON_CONSUMER_NOT_UNBOUND")
    return blockers


def _common_blockers() -> list[str]:
    return [
        "PAYLOAD_SOURCE_PROVIDER_UNBOUND",
        "HOST_IMPORT_ROUTE_AND_ENDPOINT_UNBOUND",
        "BROWSER_EXECUTION_AND_DOM_MOUNT_UNAUTHORIZED",
        "CURRENT_ACTIVATION_NOT_AUTHORIZED",
        "PAPER_AND_LIVE_PERMISSION_NOT_AUTHORIZED",
    ]


def build_portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1(
    adapter_registration_document: Any,
    consumer_preregistration_document: Any,
    binding_document: Any,
    admission_v2_document: Any,
    effective_budget_v3_document: Any,
    report_document: Any,
    correlation_preregistration_document: Any,
    correlation_matrix_document: Any,
    selection_cells_document: Any,
    complete_link_audit_document: Any,
    complete_link_gate_document: Any,
    strata_preregistration_document: Any,
    strata_gate_document: Any,
    *,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
    equity: Any,
    positions: Any,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any = "LONG",
    max_cluster_gross_pct: Any = 45.0,
    risk_increasing: Any = True,
) -> dict[str, Any]:
    """Build a sealed consumer result without host or I/O side effects."""

    gate = _assess_consumer_gate(
        adapter_registration_document,
        consumer_preregistration_document,
    )
    gate_exact = all(gate.values())
    adapter_invoked = False
    envelope_verified = False
    envelope: dict[str, Any] | None = None
    adapter_failed = False

    if gate_exact:
        adapter_invoked = True
        try:
            candidate = build_delivery_envelope_v1(
                binding_document,
                admission_v2_document,
                effective_budget_v3_document,
                report_document,
                correlation_preregistration_document,
                correlation_matrix_document,
                selection_cells_document,
                complete_link_audit_document,
                complete_link_gate_document,
                strata_preregistration_document,
                strata_gate_document,
                strategy_id=strategy_id,
                variant_id=variant_id,
                lane=lane,
                equity=equity,
                positions=positions,
                proposed_symbol=proposed_symbol,
                proposed_notional=proposed_notional,
                proposed_direction=proposed_direction,
                max_cluster_gross_pct=max_cluster_gross_pct,
                risk_increasing=risk_increasing,
            )
            envelope_verified = verify_delivery_envelope_v1(
                candidate,
                binding_document,
                admission_v2_document,
                effective_budget_v3_document,
                report_document,
                correlation_preregistration_document,
                correlation_matrix_document,
                selection_cells_document,
                complete_link_audit_document,
                complete_link_gate_document,
                strata_preregistration_document,
                strata_gate_document,
                strategy_id=strategy_id,
                variant_id=variant_id,
                lane=lane,
                equity=equity,
                positions=positions,
                proposed_symbol=proposed_symbol,
                proposed_notional=proposed_notional,
                proposed_direction=proposed_direction,
                max_cluster_gross_pct=max_cluster_gross_pct,
                risk_increasing=risk_increasing,
            )
            if envelope_verified:
                envelope = candidate
        except (KeyError, TypeError, ValueError, RuntimeError, RecursionError):
            adapter_failed = True
            envelope_verified = False
            envelope = None

    if not gate_exact:
        status = "BLOCKED"
        reason_code = "CONSUMER_GATE_REJECTED_NO_ADAPTER_INVOCATION"
        blockers = _gate_blockers(gate) + _common_blockers()
    elif not envelope_verified or envelope is None:
        status = "BLOCKED"
        reason_code = "ADAPTER_ENVELOPE_VERIFICATION_FAILED"
        blockers = ["ADAPTER_ENVELOPE_NOT_EXACT"] + _common_blockers()
    elif envelope.get("status") == "KNOWN":
        status = "KNOWN"
        reason_code = "EXACT_CONSUMER_GATE_KNOWN_ENVELOPE_RETURNED"
        blockers = _common_blockers()
    else:
        status = "UNKNOWN"
        reason_code = "EXACT_CONSUMER_GATE_UNKNOWN_ENVELOPE_RETURNED"
        blockers = ["SOURCE_ENVELOPE_UNKNOWN"] + _common_blockers()

    provenance = envelope.get("provenance", {}) if envelope is not None else {}
    core: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "consumer_id": CONSUMER_ID,
        "status": status,
        "reason_code": reason_code,
        "required_contracts": {
            "adapter_registration_hash": ADAPTER_REGISTRATION_HASH,
            "consumer_preregistration_hash": CONSUMER_PREREGISTRATION_HASH,
            "python_consumer_contract_hash": PYTHON_CONSUMER_CONTRACT_HASH,
            "delivery_schema_version": DELIVERY_SCHEMA_VERSION,
            "delivery_static_fingerprint": DELIVERY_STATIC_FINGERPRINT,
            "delivery_payload_schema_version": DELIVERY_PAYLOAD_SCHEMA_VERSION,
        },
        "gate": gate,
        "source_hashes": {
            "binding_hash": provenance.get("binding_hash"),
            "admission_v2_hash": provenance.get("admission_v2_hash"),
            "effective_budget_v3_hash": provenance.get("effective_budget_v3_hash"),
            "presentation_payload_hash": provenance.get(
                "presentation_payload_hash"
            ),
        },
        "envelope_hash": (
            envelope.get("delivery_envelope_hash") if envelope is not None else None
        ),
        "envelope": envelope,
        "transport": {
            "mode": "IN_MEMORY_RETURN_ONLY",
            "payload_source_provider": None,
            "route": None,
            "endpoint": None,
            "storage_used": False,
            "network_used": False,
        },
        "facts": {
            "consumer_gate_exact": gate_exact,
            "adapter_invoked": adapter_invoked,
            "adapter_failed": adapter_failed,
            "envelope_verified": envelope_verified,
            "input_documents_embedded": False,
            "browser_executed": False,
            "dom_mounted": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "blockers": blockers,
        "authority": {
            "payload_provider_binding_allowed": False,
            "host_import_allowed": False,
            "route_registration_allowed": False,
            "endpoint_registration_allowed": False,
            "runtime_delivery_allowed": False,
            "storage_allowed": False,
            "network_allowed": False,
            "browser_execution_allowed": False,
            "dom_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
            "writer_allowed": False,
        },
    }
    return {
        **core,
        "consumer_result_hash": strict_canonical_hash(core),
    }


def verify_portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1(
    document: Any,
    adapter_registration_document: Any,
    consumer_preregistration_document: Any,
    binding_document: Any,
    admission_v2_document: Any,
    effective_budget_v3_document: Any,
    report_document: Any,
    correlation_preregistration_document: Any,
    correlation_matrix_document: Any,
    selection_cells_document: Any,
    complete_link_audit_document: Any,
    complete_link_gate_document: Any,
    strata_preregistration_document: Any,
    strata_gate_document: Any,
    *,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
    equity: Any,
    positions: Any,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any = "LONG",
    max_cluster_gross_pct: Any = 45.0,
    risk_increasing: Any = True,
) -> bool:
    """Verify an exact result against the complete in-memory source chain."""

    if type(document) is not dict or not _is_native_json_tree(document):
        return False
    try:
        supplied_hash = document.get("consumer_result_hash")
        if type(supplied_hash) is not str:
            return False
        core = {
            key: value
            for key, value in document.items()
            if key != "consumer_result_hash"
        }
        if strict_canonical_hash(core) != supplied_hash:
            return False
        expected = build_portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1(
            adapter_registration_document,
            consumer_preregistration_document,
            binding_document,
            admission_v2_document,
            effective_budget_v3_document,
            report_document,
            correlation_preregistration_document,
            correlation_matrix_document,
            selection_cells_document,
            complete_link_audit_document,
            complete_link_gate_document,
            strata_preregistration_document,
            strata_gate_document,
            strategy_id=strategy_id,
            variant_id=variant_id,
            lane=lane,
            equity=equity,
            positions=positions,
            proposed_symbol=proposed_symbol,
            proposed_notional=proposed_notional,
            proposed_direction=proposed_direction,
            max_cluster_gross_pct=max_cluster_gross_pct,
            risk_increasing=risk_increasing,
        )
        return document == expected and strict_canonical_hash(document) == strict_canonical_hash(
            expected
        )
    except (KeyError, TypeError, ValueError, RuntimeError, RecursionError):
        return False
