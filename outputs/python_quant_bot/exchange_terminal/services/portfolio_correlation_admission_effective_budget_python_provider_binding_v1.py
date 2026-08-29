"""Bind the correlation hash-envelope provider for explicit in-memory use only.

The binding is real: an exact binding document can resolve the existing ADR0311
Python callable.  It does not register an application import, HTTP handler,
route, endpoint, browser asset, mount, writer, or trading permission.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from exchange_terminal.services.portfolio_correlation_admission_effective_budget_consumer_static_asset_registration_v2 import (
    EXPECTED_ASSET_MANIFEST_HASH as ASSET_REGISTRATION_MANIFEST_HASH,
    EXPECTED_REGISTRATION_HASH as ASSET_REGISTRATION_HASH,
    EXPECTED_SPEC_HASH as ASSET_REGISTRATION_SPEC_HASH,
    build_portfolio_correlation_admission_effective_budget_consumer_static_asset_registration_v2,
    verify_portfolio_correlation_admission_effective_budget_consumer_static_asset_registration_v2,
)
from exchange_terminal.services.portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1 import (
    ADAPTER_REGISTRATION_HASH,
    CONSUMER_ID,
    CONSUMER_PREREGISTRATION_HASH,
    PYTHON_CONSUMER_CONTRACT_HASH,
    SCHEMA_VERSION as PROVIDER_OUTPUT_SCHEMA_VERSION,
    STATIC_FINGERPRINT as PROVIDER_OUTPUT_STATIC_FINGERPRINT,
    build_portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1 as _PROVIDER_CALLABLE,
)
from exchange_terminal.services.portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1 import (
    build_portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1,
    verify_portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-python-provider-binding-v1"
)
STATIC_FINGERPRINT = (
    "20260824-portfolio-correlation-admission-effective-budget-python-provider-"
    "binding-v1-internal-only-lock-1"
)
BINDING_ID = "portfolio-correlation-admission-effective-budget-python-provider-v1"
PROVIDER_KEY = "correlation-hash-envelope-provider-v1"
PROVIDER_CONTRACT_ID = "correlation-hash-envelope-provider-v1"
PROVIDER_MODULE_PATH = (
    "exchange_terminal/services/portfolio_correlation_admission_effective_budget_"
    "hash_envelope_source_consumer_v1.py"
)
PROVIDER_MODULE_IMPORT = (
    "exchange_terminal.services.portfolio_correlation_admission_effective_budget_"
    "hash_envelope_source_consumer_v1"
)
PROVIDER_MODULE_SHA256 = (
    "ec7de6b7dfdd30d4c29d9156551fd62525516a48e52cfc2cd945acc7b959eeca"
)
PROVIDER_CALLABLE_NAME = (
    "build_portfolio_correlation_admission_effective_budget_"
    "hash_envelope_source_consumer_v1"
)
PROVIDER_VERIFIER_NAME = (
    "verify_portfolio_correlation_admission_effective_budget_"
    "hash_envelope_source_consumer_v1"
)
PROVIDER_REGISTRY_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-python-provider-registry-v1"
)
PROVIDER_REGISTRY_ID = (
    "portfolio-correlation-admission-effective-budget-in-memory-provider-registry-v1"
)

HOST_BINDING_PREREGISTRATION_HASH = (
    "132eb51549337575ebb1ff80c870e7eb51d66a63b52f73930634e9e0467e9e6b"
)
HOST_BINDING_CANDIDATES_HASH = (
    "5a96998de64af8e7f3be65f54d5889e07e0587b6646c5bdae503b3a7c874ec6d"
)
HOST_PYTHON_PROVIDER_CANDIDATE_HASH = (
    "7afe9f01f2eef2ac20d39900d1c4102bd46b0f1eb1325dabdb41f6b012b460c6"
)
CALLABLE_IDENTITY_HASH = (
    "79b2eed39d69bf89cf599951e302e75dd40cfcf2f935d9bbe8e1f535c3f8e2ce"
)
REGISTRY_HASH = (
    "1e2eb0bb8ad241b8b8c9c50299a58cbf17cea166ef33a59e3fa34aed4a359db2"
)
EXPECTED_PROVIDER_BINDING_HASH = (
    "d9b36dc1dce884333a985ff0a64e71359dea7adf128431ef12c407eab1466060"
)

EXPECTED_HOST_PYTHON_PROVIDER_CANDIDATE = {
    "contract_id": PROVIDER_CONTRACT_ID,
    "module_path": PROVIDER_MODULE_PATH,
    "module_sha256": PROVIDER_MODULE_SHA256,
    "callable": PROVIDER_CALLABLE_NAME,
    "input_mode": "INTERNAL_EXACT_SOURCE_CHAIN_ONLY",
    "output_schema_version": PROVIDER_OUTPUT_SCHEMA_VERSION,
    "provider_registration": None,
    "active_import": None,
    "bound": False,
}

PREDECESSOR_CONTRACT = {
    "host_binding_preregistration_hash": HOST_BINDING_PREREGISTRATION_HASH,
    "host_binding_candidates_hash": HOST_BINDING_CANDIDATES_HASH,
    "host_python_provider_candidate_hash": HOST_PYTHON_PROVIDER_CANDIDATE_HASH,
    "consumer_static_asset_registration_hash": ASSET_REGISTRATION_HASH,
    "consumer_static_asset_spec_hash": ASSET_REGISTRATION_SPEC_HASH,
    "consumer_static_asset_manifest_hash": ASSET_REGISTRATION_MANIFEST_HASH,
    "host_implementation_path": (
        "exchange_terminal/services/portfolio_correlation_admission_effective_"
        "budget_host_binding_preregistration_v1.py"
    ),
    "host_implementation_sha256": (
        "340e2a2bb30061f810aa545095909cb0e51bf0f80d7f7b5217ab5359d8fc7850"
    ),
    "host_test_path": (
        "tests/test_portfolio_correlation_admission_effective_budget_"
        "host_binding_preregistration_v1.py"
    ),
    "host_test_sha256": (
        "207d3f9f3c7f36d73148ecaae79ec50a77faac574830b0f0a85996f04af846f5"
    ),
    "host_adr_path": (
        "docs/adr/0314-portfolio-correlation-admission-effective-budget-"
        "host-binding-preregistration-v1.md"
    ),
    "host_adr_sha256": (
        "7e0c7c08a781c91025f6ba7fc708c25f87d68243a9dc40268806bc3f1888651c"
    ),
    "asset_registration_implementation_path": (
        "exchange_terminal/services/portfolio_correlation_admission_effective_"
        "budget_consumer_static_asset_registration_v2.py"
    ),
    "asset_registration_implementation_sha256": (
        "d284186727e50ffc17b8ee0830b7826f0f09f9b87a3ee56c493b241a50dc1253"
    ),
    "asset_registration_test_path": (
        "tests/test_portfolio_correlation_admission_effective_budget_"
        "consumer_static_asset_registration_v2.py"
    ),
    "asset_registration_test_sha256": (
        "3645cc2d7ea93d5fe7f170eecb108c6bdef9256b8622744928c1553502df4cba"
    ),
    "asset_registration_adr_path": (
        "docs/adr/0315-portfolio-correlation-admission-effective-budget-"
        "consumer-static-asset-registration-v2.md"
    ),
    "asset_registration_adr_sha256": (
        "d31ffbdb1b0983667055d2427bab127882d4ad1f6d762efe5520e2432272fff4"
    ),
}


ProviderCallable = Callable[..., dict[str, Any]]


def _snapshot_json_value(value: Any, active_ids: set[int]) -> Any:
    if isinstance(value, Mapping):
        value_id = id(value)
        if value_id in active_ids:
            raise ValueError("cyclic mapping is not a JSON document")
        active_ids.add(value_id)
        try:
            snapshot: dict[str, Any] = {}
            for key in value:
                if type(key) is not str or key in snapshot:
                    raise TypeError("JSON object keys must be unique strings")
                snapshot[key] = _snapshot_json_value(value[key], active_ids)
            return snapshot
        finally:
            active_ids.remove(value_id)
    if type(value) is list:
        value_id = id(value)
        if value_id in active_ids:
            raise ValueError("cyclic list is not a JSON document")
        active_ids.add(value_id)
        try:
            return [_snapshot_json_value(item, active_ids) for item in value]
        finally:
            active_ids.remove(value_id)
    if value is None or type(value) in (bool, int, float, str):
        return value
    raise TypeError("input must contain only JSON-compatible values")


def _snapshot_json_mapping(document: Any) -> dict[str, Any] | None:
    if not isinstance(document, Mapping):
        return None
    try:
        snapshot = _snapshot_json_value(document, set())
    except Exception:
        return None
    return snapshot if type(snapshot) is dict else None


def _require_equal(label: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise ValueError(f"{label} does not match the pinned contract")


def _verify_predecessors() -> None:
    host = (
        build_portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1()
    )
    if not verify_portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1(
        host
    ):
        raise ValueError("ADR0314 host-binding preregistration is not exact")
    _require_equal(
        "ADR0314 host_binding_preregistration_hash",
        host.get("host_binding_preregistration_hash"),
        HOST_BINDING_PREREGISTRATION_HASH,
    )
    _require_equal(
        "ADR0314 binding_candidates_hash",
        host.get("binding_candidates_hash"),
        HOST_BINDING_CANDIDATES_HASH,
    )
    candidate = host["binding_candidates"]["python_provider"]
    _require_equal(
        "ADR0314 Python provider candidate",
        candidate,
        EXPECTED_HOST_PYTHON_PROVIDER_CANDIDATE,
    )
    _require_equal(
        "ADR0314 Python provider candidate hash",
        strict_canonical_hash(candidate),
        HOST_PYTHON_PROVIDER_CANDIDATE_HASH,
    )
    for key in ("python_provider", "app_import", "http_handler", "route", "endpoint"):
        if host["active_host_plan"][key] is not None:
            raise ValueError(f"ADR0314 active host slot {key} must remain null")

    assets = (
        build_portfolio_correlation_admission_effective_budget_consumer_static_asset_registration_v2()
    )
    if not verify_portfolio_correlation_admission_effective_budget_consumer_static_asset_registration_v2(
        assets
    ):
        raise ValueError("ADR0315 consumer static-asset registration is not exact")
    _require_equal(
        "ADR0315 registration_hash",
        assets.get("registration_hash"),
        ASSET_REGISTRATION_HASH,
    )
    _require_equal(
        "ADR0315 spec_hash", assets.get("spec_hash"), ASSET_REGISTRATION_SPEC_HASH
    )
    _require_equal(
        "ADR0315 asset_manifest_hash",
        assets.get("asset_manifest_hash"),
        ASSET_REGISTRATION_MANIFEST_HASH,
    )
    if any(value is not None for value in assets["host_plan"].values()):
        raise ValueError("ADR0315 host plan must remain fully null")


def _build_callable_identity() -> dict[str, Any]:
    return {
        "contract_id": PROVIDER_CONTRACT_ID,
        "consumer_id": CONSUMER_ID,
        "module_path": PROVIDER_MODULE_PATH,
        "module_sha256": PROVIDER_MODULE_SHA256,
        "callable": PROVIDER_CALLABLE_NAME,
        "verifier": PROVIDER_VERIFIER_NAME,
        "input_mode": "INTERNAL_EXACT_SOURCE_CHAIN_ONLY",
        "output_schema_version": PROVIDER_OUTPUT_SCHEMA_VERSION,
        "output_static_fingerprint": PROVIDER_OUTPUT_STATIC_FINGERPRINT,
        "adapter_registration_hash": ADAPTER_REGISTRATION_HASH,
        "consumer_preregistration_hash": CONSUMER_PREREGISTRATION_HASH,
        "python_consumer_contract_hash": PYTHON_CONSUMER_CONTRACT_HASH,
    }


def _build_registry() -> dict[str, Any]:
    return {
        "schema_version": PROVIDER_REGISTRY_SCHEMA_VERSION,
        "registry_id": PROVIDER_REGISTRY_ID,
        "entries": [
            {
                "provider_key": PROVIDER_KEY,
                "contract_id": PROVIDER_CONTRACT_ID,
                "callable_identity_hash": CALLABLE_IDENTITY_HASH,
            }
        ],
        "default_provider_key": None,
        "resolution_mode": "EXACT_BINDING_DOCUMENT_ONLY",
    }


def build_portfolio_correlation_admission_effective_budget_python_provider_binding_v1() -> dict[str, Any]:
    """Build the exact internal-only provider binding without resolving it."""

    _verify_predecessors()
    callable_identity = _build_callable_identity()
    registry = _build_registry()
    _require_equal(
        "callable_identity_hash",
        strict_canonical_hash(callable_identity),
        CALLABLE_IDENTITY_HASH,
    )
    _require_equal("registry_hash", strict_canonical_hash(registry), REGISTRY_HASH)

    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "binding_id": BINDING_ID,
        "status": "BLOCKED",
        "binding_state": (
            "PYTHON_PROVIDER_BOUND_INTERNAL_ONLY_HTTP_APP_HOST_CURRENT_UNBOUND"
        ),
        "predecessor_contract": dict(PREDECESSOR_CONTRACT),
        "callable_identity": callable_identity,
        "callable_identity_hash": CALLABLE_IDENTITY_HASH,
        "registry": registry,
        "registry_hash": REGISTRY_HASH,
        "provider_contract": {
            "provider_key": PROVIDER_KEY,
            "contract_id": PROVIDER_CONTRACT_ID,
            "bound": True,
            "callable_resolution": "EXACT_BINDING_DOCUMENT_ONLY",
            "invocation_mode": "EXPLICIT_IN_MEMORY_RESEARCH_ONLY",
            "raw_external_requests_allowed": False,
            "implicit_default_allowed": False,
            "provider_invoked_by_binding": False,
        },
        "host_plan": {
            "python_provider_registry_entry": PROVIDER_KEY,
            "application_importer": None,
            "http_handler": None,
            "route": None,
            "endpoint": None,
            "javascript_loader": None,
            "stylesheet_link": None,
            "mount_selector": None,
            "browser_review_receipt": None,
        },
        "activation_order": [
            "VERIFY_EXACT_ADR0314_HOST_BINDING_PREREGISTRATION",
            "VERIFY_EXACT_ADR0315_CONSUMER_STATIC_ASSET_REGISTRATION",
            "VERIFY_ADR0316_PYTHON_PROVIDER_BINDING",
            "RESOLVE_PROVIDER_ONLY_FOR_EXPLICIT_SYNTHETIC_RESEARCH_CALL",
            "IMPLEMENT_READONLY_HTTP_PROJECTION_IN_SEPARATE_VERSION",
            "IMPLEMENT_APPLICATION_AND_HOST_LOADING_IN_SEPARATE_VERSION",
            "RUN_AUTHORIZED_BROWSER_REVIEW_BEFORE_ANY_MOUNT",
            "CONSIDER_CURRENT_ONLY_BY_SEPARATE_EXPLICIT_DECISION",
        ],
        "facts": {
            "host_preregistration_exactly_verified": True,
            "asset_registration_exactly_verified": True,
            "callable_identity_pinned": True,
            "registry_pinned": True,
            "python_provider_bound_in_memory": True,
            "implicit_default_provider_present": False,
            "provider_resolved_by_binding_build": False,
            "provider_invoked_by_binding_build": False,
            "http_projection_bound": False,
            "application_imported": False,
            "host_assets_loaded": False,
            "browser_executed": False,
            "dom_mounted": False,
            "current_activated": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "blockers": [
            "ADR0316_INTERNAL_PROVIDER_ONLY",
            "READONLY_HTTP_PROJECTION_NOT_IMPLEMENTED",
            "APPLICATION_IMPORT_NOT_IMPLEMENTED",
            "HOST_ASSET_LOADING_NOT_IMPLEMENTED",
            "AUTHORIZED_BROWSER_REVIEW_NOT_RUN",
            "ROUTE_AND_MOUNT_UNBOUND",
            "CURRENT_ACTIVATION_NOT_AUTHORIZED",
            "PAPER_AND_LIVE_PERMISSION_NOT_AUTHORIZED",
        ],
        "authority": {
            "in_memory_provider_resolution_allowed": True,
            "synthetic_research_invocation_allowed": True,
            "external_request_invocation_allowed": False,
            "http_projection_binding_allowed": False,
            "application_import_allowed": False,
            "route_registration_allowed": False,
            "endpoint_registration_allowed": False,
            "runtime_asset_loading_allowed": False,
            "browser_execution_allowed": False,
            "dom_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
            "writer_allowed": False,
        },
        "decision": (
            "EXACT_PROVIDER_CALLABLE_BOUND_TO_NONDEFAULT_IN_MEMORY_REGISTRY_"
            "EXPLICIT_SYNTHETIC_RESEARCH_RESOLUTION_ONLY_HTTP_APP_HOST_BROWSER_"
            "MOUNT_CURRENT_PAPER_AND_LIVE_UNBOUND"
        ),
    }
    sealed = seal_strict_canonical_document(document, "provider_binding_hash")
    _require_equal(
        "provider_binding_hash",
        sealed.get("provider_binding_hash"),
        EXPECTED_PROVIDER_BINDING_HASH,
    )
    return sealed


def verify_portfolio_correlation_admission_effective_budget_python_provider_binding_v1(
    document: Any,
) -> bool:
    """Return true only for the exact ADR0316 binding document."""

    snapshot = _snapshot_json_mapping(document)
    if snapshot is None:
        return False
    try:
        expected = (
            build_portfolio_correlation_admission_effective_budget_python_provider_binding_v1()
        )
    except Exception:
        return False
    return strict_json_contract_equal(snapshot, expected)


def _callable_identity_is_exact(value: Any) -> bool:
    return (
        callable(value)
        and getattr(value, "__module__", None) == PROVIDER_MODULE_IMPORT
        and getattr(value, "__name__", None) == PROVIDER_CALLABLE_NAME
    )


def resolve_portfolio_correlation_admission_effective_budget_python_provider_v1(
    binding_document: Any,
) -> ProviderCallable | None:
    """Resolve the provider only from one safely snapshotted exact binding."""

    snapshot = _snapshot_json_mapping(binding_document)
    if snapshot is None:
        return None
    if not verify_portfolio_correlation_admission_effective_budget_python_provider_binding_v1(
        snapshot
    ):
        return None
    if not _callable_identity_is_exact(_PROVIDER_CALLABLE):
        return None
    return _PROVIDER_CALLABLE


__all__ = [
    "BINDING_ID",
    "CALLABLE_IDENTITY_HASH",
    "EXPECTED_PROVIDER_BINDING_HASH",
    "HOST_BINDING_CANDIDATES_HASH",
    "HOST_BINDING_PREREGISTRATION_HASH",
    "HOST_PYTHON_PROVIDER_CANDIDATE_HASH",
    "PREDECESSOR_CONTRACT",
    "PROVIDER_CALLABLE_NAME",
    "PROVIDER_CONTRACT_ID",
    "PROVIDER_KEY",
    "PROVIDER_MODULE_IMPORT",
    "PROVIDER_MODULE_PATH",
    "PROVIDER_MODULE_SHA256",
    "PROVIDER_REGISTRY_ID",
    "PROVIDER_REGISTRY_SCHEMA_VERSION",
    "REGISTRY_HASH",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_portfolio_correlation_admission_effective_budget_python_provider_binding_v1",
    "resolve_portfolio_correlation_admission_effective_budget_python_provider_v1",
    "verify_portfolio_correlation_admission_effective_budget_python_provider_binding_v1",
]
