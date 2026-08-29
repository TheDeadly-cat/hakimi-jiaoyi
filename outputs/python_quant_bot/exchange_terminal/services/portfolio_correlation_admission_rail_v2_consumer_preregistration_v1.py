from __future__ import annotations

from typing import Any

from exchange_terminal.services.portfolio_correlation_admission_v2_in_memory_delivery_adapter_registration_v1 import (
    build_portfolio_correlation_admission_v2_in_memory_delivery_adapter_registration_v1,
    verify_portfolio_correlation_admission_v2_in_memory_delivery_adapter_registration_v1,
)
from exchange_terminal.services.portfolio_correlation_admission_v2_in_memory_delivery_v1 import (
    seal_strict_canonical_document,
)


SCHEMA_VERSION = (
    "portfolio-correlation-admission-rail-v2-consumer-preregistration-v1"
)
CANDIDATE_MANIFEST_SCHEMA_VERSION = (
    "portfolio-correlation-admission-rail-v2-candidate-manifest-v1"
)
BINDING_SCHEMA_VERSION = (
    "portfolio-correlation-admission-rail-v2-consumer-binding-v1"
)
STATIC_FINGERPRINT = (
    "20260823-portfolio-correlation-admission-rail-v2-"
    "consumer-preregistration-v1-lock-1"
)

DELIVERY_ADAPTER_REGISTRATION_SCHEMA_VERSION = (
    "portfolio-correlation-admission-v2-in-memory-delivery-"
    "adapter-registration-v1"
)
DELIVERY_ADAPTER_REGISTRATION_HASH = (
    "f75c9f71eabd5522edc4e87c2c2c669c94ee641ee236c10f7bcdf5907396d941"
)
DELIVERY_ENVELOPE_SCHEMA_VERSION = (
    "portfolio-correlation-admission-v2-in-memory-delivery-envelope-v1"
)
DELIVERY_STATIC_FINGERPRINT = (
    "20260823-portfolio-correlation-admission-v2-"
    "in-memory-delivery-v1-lock-1"
)

RAIL_SCHEMA_VERSION = "portfolio-correlation-admission-rail-v2"
RAIL_STATIC_FINGERPRINT = (
    "20260823-portfolio-correlation-admission-rail-v2-unmounted-lock-1"
)
RAIL_IMPLEMENTATION_SHA256 = (
    "a58a89e3eff4ce309f5e153fbef3c53e8bd850d86d998dbc2da73ef68eb87cf2"
)
RAIL_STYLESHEET_SHA256 = (
    "e77a2b81a837ced2fd029ff45e4784318e42e5974e42e31710caf731a5668cce"
)
RAIL_CONTRACT_SHA256 = (
    "77120107768a13a1b1ad2796585770269d2ac935b078f07f41cbf42e71d63880"
)
RAIL_ADR_SHA256 = (
    "a2729dc5db2fa8733b1ac4894cc016fd5e1c1b4e1b276ec4d2065a6629d21a33"
)
RAIL_CSS_NAMESPACE = ".hakimi-correlation-v2-rail"

STAGE_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")
TIER_ORDER = (
    "INPUT_SNAPSHOT",
    "INPUT_IDENTITY",
    "REPORT_UNIVERSE",
    "CORRELATION_PREREGISTRATION",
    "COMMON_UNIVERSE",
    "V1_ADMISSION",
    "PERMISSION",
)
FUNCTION_EXPORTS = (
    "buildPortfolioCorrelationAdmissionRailViewModelV2",
    "renderPortfolioCorrelationAdmissionRailV2",
)

_HEX_CHARS = frozenset("0123456789abcdef")


class _InvalidJsonDocument(ValueError):
    pass


def _plain_json_snapshot(
    value: Any,
    active: set[int] | None = None,
) -> Any:
    if value is None or type(value) in (bool, int, str):
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


def _is_sha256(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in _HEX_CHARS for character in value)
    )


def _is_exact_sealed_document(document: Any, hash_field: str) -> bool:
    try:
        snapshot = _plain_json_snapshot(document)
        if type(snapshot) is not dict or not _is_sha256(snapshot.get(hash_field)):
            return False
        return snapshot == seal_strict_canonical_document(snapshot, hash_field)
    except (TypeError, ValueError):
        return False


def _sealed_hash(document: Any, hash_field: str) -> str | None:
    if not _is_exact_sealed_document(document, hash_field):
        return None
    value = document.get(hash_field)
    return value if type(value) is str else None


def build_portfolio_correlation_admission_rail_v2_consumer_preregistration_v1(
) -> dict[str, Any]:
    registration = {
        "schema_version": SCHEMA_VERSION,
        "binding_schema_version": BINDING_SCHEMA_VERSION,
        "candidate_manifest_schema_version": CANDIDATE_MANIFEST_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "registration_state": "PREREGISTERED_UNMOUNTED",
        "decision": (
            "RAIL_ASSETS_EXPORTS_ORDER_NAMESPACE_AND_PREDECESSOR_PINNED_"
            "HOST_MOUNT_RENDER_CURRENT_PAPER_AND_LIVE_ABSENT"
        ),
        "predecessor_contract": {
            "adapter_registration_schema_version": (
                DELIVERY_ADAPTER_REGISTRATION_SCHEMA_VERSION
            ),
            "adapter_registration_hash": DELIVERY_ADAPTER_REGISTRATION_HASH,
            "delivery_envelope_schema_version": DELIVERY_ENVELOPE_SCHEMA_VERSION,
            "delivery_static_fingerprint": DELIVERY_STATIC_FINGERPRINT,
        },
        "consumer_contract": {
            "browser_global": "HakimiPortfolioCorrelationAdmissionRailV2",
            "module_format": "UMD_COMMONJS",
            "rail_schema_version": RAIL_SCHEMA_VERSION,
            "rail_static_fingerprint": RAIL_STATIC_FINGERPRINT,
            "function_exports": list(FUNCTION_EXPORTS),
            "renderer_input": "EXACT_DELIVERY_ENVELOPE_V1",
            "stage_order": list(STAGE_ORDER),
            "tier_order": list(TIER_ORDER),
            "css_namespace": RAIL_CSS_NAMESPACE,
            "status_labels": [
                "LOCAL CLEAR",
                "LOCAL BLOCK",
                "SOURCE UNKNOWN",
            ],
            "permission_stage_terminal_state": "UNAUTHORIZED",
        },
        "source_contract": {
            "manifest_is_hash_only": True,
            "implementation_sha256": RAIL_IMPLEMENTATION_SHA256,
            "stylesheet_sha256": RAIL_STYLESHEET_SHA256,
            "contract_sha256": RAIL_CONTRACT_SHA256,
            "adr_sha256": RAIL_ADR_SHA256,
        },
        "activation_order": [
            "CONSUMER_PREREGISTRATION",
            "INDEPENDENT_SOURCE_HASH_MEASUREMENT",
            "HASH_ONLY_CANDIDATE_BINDING",
            "SEPARATE_HOST_REGISTRATION_REVIEW",
            "SEPARATE_ISOLATED_MOUNT_REVIEW",
            "SEPARATE_CURRENT_WRITER_REVIEW",
        ],
        "facts": {
            "consumer_preregistered": True,
            "candidate_bound": False,
            "adapter_predecessor_pinned": True,
            "source_bytes_embedded": False,
            "raw_delivery_envelope_embedded": False,
            "dom_accessed": False,
            "browser_executed": False,
            "render_called": False,
            "host_assets_modified": False,
            "host_registered": False,
            "ui_mounted": False,
            "current_activated": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": {
            "descriptive_only": True,
            "candidate_binding_allowed": True,
            "source_file_read_allowed": False,
            "host_asset_write_allowed": False,
            "host_registration_allowed": False,
            "stylesheet_registration_allowed": False,
            "route_registration_allowed": False,
            "endpoint_registration_allowed": False,
            "payload_source_registration_allowed": False,
            "render_allowed": False,
            "dom_access_allowed": False,
            "browser_execution_allowed": False,
            "ui_consumer_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    return seal_strict_canonical_document(
        registration,
        "consumer_preregistration_hash",
    )


def verify_portfolio_correlation_admission_rail_v2_consumer_preregistration_v1(
    document: Any,
) -> bool:
    try:
        snapshot = _plain_json_snapshot(document)
    except (TypeError, ValueError):
        return False
    return snapshot == (
        build_portfolio_correlation_admission_rail_v2_consumer_preregistration_v1()
    )


def build_portfolio_correlation_admission_rail_v2_candidate_manifest_v1(
) -> dict[str, Any]:
    manifest = {
        "schema_version": CANDIDATE_MANIFEST_SCHEMA_VERSION,
        "rail_schema_version": RAIL_SCHEMA_VERSION,
        "rail_static_fingerprint": RAIL_STATIC_FINGERPRINT,
        "predecessor_adapter_registration_hash": (
            DELIVERY_ADAPTER_REGISTRATION_HASH
        ),
        "module_contract": {
            "browser_global": "HakimiPortfolioCorrelationAdmissionRailV2",
            "module_format": "UMD_COMMONJS",
            "function_exports": list(FUNCTION_EXPORTS),
            "stage_order": list(STAGE_ORDER),
            "tier_order": list(TIER_ORDER),
        },
        "stylesheet_contract": {
            "namespace": RAIL_CSS_NAMESPACE,
            "external_imports_allowed": False,
            "external_urls_allowed": False,
            "global_selectors_allowed": False,
            "responsive_contract_present": True,
            "reduced_motion_contract_present": True,
        },
        "source_artifacts": {
            "implementation": {
                "path": (
                    "exchange_terminal/static/"
                    "evidence_portfolio_correlation_admission_rail_v2.js"
                ),
                "sha256": RAIL_IMPLEMENTATION_SHA256,
            },
            "stylesheet": {
                "path": (
                    "exchange_terminal/static/"
                    "evidence_portfolio_correlation_admission_rail_v2.css"
                ),
                "sha256": RAIL_STYLESHEET_SHA256,
            },
            "contract": {
                "path": (
                    "exchange_terminal/static/"
                    "evidence_portfolio_correlation_admission_rail_v2.test.js"
                ),
                "sha256": RAIL_CONTRACT_SHA256,
            },
            "decision_record": {
                "path": (
                    "docs/adr/"
                    "0303-portfolio-correlation-admission-rail-v2.md"
                ),
                "sha256": RAIL_ADR_SHA256,
            },
        },
        "facts": {
            "hash_only": True,
            "source_bytes_embedded": False,
            "raw_delivery_envelope_embedded": False,
            "raw_strategy_ids_embedded": False,
            "raw_symbol_lists_embedded": False,
            "host_registered": False,
            "render_called": False,
            "ui_mounted": False,
            "current_activated": False,
            "profitability_proven": False,
        },
        "authority": {
            "descriptive_only": True,
            "host_registration_allowed": False,
            "render_allowed": False,
            "dom_access_allowed": False,
            "browser_execution_allowed": False,
            "ui_consumer_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    return seal_strict_canonical_document(manifest, "candidate_manifest_hash")


def verify_portfolio_correlation_admission_rail_v2_candidate_manifest_v1(
    document: Any,
) -> bool:
    try:
        snapshot = _plain_json_snapshot(document)
    except (TypeError, ValueError):
        return False
    return snapshot == (
        build_portfolio_correlation_admission_rail_v2_candidate_manifest_v1()
    )


def _build_binding(
    *,
    status: str,
    binding_state: str,
    reason_code: str,
    consumer_preregistration_hash: str | None,
    candidate_manifest_hash: str | None,
    adapter_registration_hash: str | None,
    registration_exact: bool,
    candidate_manifest_exact: bool,
    adapter_registration_exact: bool,
) -> dict[str, Any]:
    binding = {
        "schema_version": BINDING_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "binding_state": binding_state,
        "reason_code": reason_code,
        "source": {
            "consumer_preregistration_hash": consumer_preregistration_hash,
            "candidate_manifest_hash": candidate_manifest_hash,
            "adapter_registration_hash": adapter_registration_hash,
        },
        "facts": {
            "registration_exact": registration_exact,
            "candidate_manifest_exact": candidate_manifest_exact,
            "adapter_registration_exact": adapter_registration_exact,
            "hash_only_binding": True,
            "source_bytes_embedded": False,
            "raw_candidate_manifest_embedded": False,
            "raw_adapter_registration_embedded": False,
            "raw_delivery_envelope_embedded": False,
            "render_called": False,
            "dom_accessed": False,
            "browser_executed": False,
            "host_assets_modified": False,
            "host_registered": False,
            "ui_mounted": False,
            "current_activated": False,
            "profitability_proven": False,
        },
        "authority": {
            "descriptive_only": True,
            "manual_review_required": True,
            "host_asset_write_allowed": False,
            "host_registration_allowed": False,
            "stylesheet_registration_allowed": False,
            "route_registration_allowed": False,
            "endpoint_registration_allowed": False,
            "payload_source_registration_allowed": False,
            "render_allowed": False,
            "dom_access_allowed": False,
            "browser_execution_allowed": False,
            "ui_consumer_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    return seal_strict_canonical_document(binding, "consumer_binding_hash")


def _unknown_binding(reason_code: str) -> dict[str, Any]:
    return _build_binding(
        status="UNKNOWN",
        binding_state="UNKNOWN",
        reason_code=reason_code,
        consumer_preregistration_hash=None,
        candidate_manifest_hash=None,
        adapter_registration_hash=None,
        registration_exact=False,
        candidate_manifest_exact=False,
        adapter_registration_exact=False,
    )


def build_portfolio_correlation_admission_rail_v2_consumer_binding_v1(
    consumer_preregistration_document: Any,
    candidate_manifest_document: Any,
    adapter_registration_document: Any,
) -> dict[str, Any]:
    registration_hash = _sealed_hash(
        consumer_preregistration_document,
        "consumer_preregistration_hash",
    )
    if registration_hash is None:
        return _unknown_binding("CONSUMER_PREREGISTRATION_UNKNOWN")

    candidate_manifest_hash = _sealed_hash(
        candidate_manifest_document,
        "candidate_manifest_hash",
    )
    if candidate_manifest_hash is None:
        return _unknown_binding("CANDIDATE_MANIFEST_UNKNOWN")

    adapter_registration_hash = _sealed_hash(
        adapter_registration_document,
        "adapter_registration_hash",
    )
    if adapter_registration_hash is None:
        return _unknown_binding("ADAPTER_REGISTRATION_UNKNOWN")

    registration_exact = (
        verify_portfolio_correlation_admission_rail_v2_consumer_preregistration_v1(
            consumer_preregistration_document
        )
    )
    candidate_manifest_exact = (
        verify_portfolio_correlation_admission_rail_v2_candidate_manifest_v1(
            candidate_manifest_document
        )
    )
    adapter_registration_exact = (
        adapter_registration_hash == DELIVERY_ADAPTER_REGISTRATION_HASH
        and verify_portfolio_correlation_admission_v2_in_memory_delivery_adapter_registration_v1(
            adapter_registration_document
        )
    )

    if not registration_exact:
        reason_code = "CONSUMER_PREREGISTRATION_DRIFT"
        binding_state = "BLOCK"
    elif not candidate_manifest_exact:
        reason_code = "CANDIDATE_MANIFEST_DRIFT"
        binding_state = "BLOCK"
    elif not adapter_registration_exact:
        reason_code = "ADAPTER_REGISTRATION_DRIFT"
        binding_state = "BLOCK"
    else:
        reason_code = "EXACT_HASH_ONLY_RAIL_CANDIDATE_BOUND_UNMOUNTED"
        binding_state = "PASS"

    return _build_binding(
        status="BLOCKED",
        binding_state=binding_state,
        reason_code=reason_code,
        consumer_preregistration_hash=registration_hash,
        candidate_manifest_hash=candidate_manifest_hash,
        adapter_registration_hash=adapter_registration_hash,
        registration_exact=registration_exact,
        candidate_manifest_exact=candidate_manifest_exact,
        adapter_registration_exact=adapter_registration_exact,
    )


def verify_portfolio_correlation_admission_rail_v2_consumer_binding_v1(
    document: Any,
    consumer_preregistration_document: Any,
    candidate_manifest_document: Any,
    adapter_registration_document: Any,
) -> bool:
    try:
        snapshot = _plain_json_snapshot(document)
    except (TypeError, ValueError):
        return False
    return snapshot == (
        build_portfolio_correlation_admission_rail_v2_consumer_binding_v1(
            consumer_preregistration_document,
            candidate_manifest_document,
            adapter_registration_document,
        )
    )


def build_exact_portfolio_correlation_admission_rail_v2_consumer_bundle_v1(
) -> dict[str, dict[str, Any]]:
    adapter_registration = (
        build_portfolio_correlation_admission_v2_in_memory_delivery_adapter_registration_v1()
    )
    consumer_preregistration = (
        build_portfolio_correlation_admission_rail_v2_consumer_preregistration_v1()
    )
    candidate_manifest = (
        build_portfolio_correlation_admission_rail_v2_candidate_manifest_v1()
    )
    consumer_binding = (
        build_portfolio_correlation_admission_rail_v2_consumer_binding_v1(
            consumer_preregistration,
            candidate_manifest,
            adapter_registration,
        )
    )
    return {
        "consumer_preregistration": consumer_preregistration,
        "candidate_manifest": candidate_manifest,
        "adapter_registration": adapter_registration,
        "consumer_binding": consumer_binding,
    }
