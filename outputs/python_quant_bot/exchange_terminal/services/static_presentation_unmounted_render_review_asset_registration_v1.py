"""Register no-DOM render-review assets without loading or executing them."""

from __future__ import annotations

import math
from typing import Any

from exchange_terminal.services.static_presentation_host_patch_preregistration_v1 import (
    SCHEMA_VERSION as PATCH_PREREGISTRATION_SCHEMA_VERSION,
    STATIC_FINGERPRINT as PATCH_PREREGISTRATION_STATIC_FINGERPRINT,
    build_static_presentation_host_patch_preregistration_v1,
    verify_static_presentation_host_patch_preregistration_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = "static-presentation-unmounted-render-review-asset-registration-v1"
STATIC_FINGERPRINT = (
    "20260823-static-presentation-render-review-assets-v1-unbound-lock-1"
)
REGISTRATION_ID = "static-presentation-unmounted-render-review-v1"
STATUS = "BLOCKED"

PATCH_PREREGISTRATION_HASH = (
    "90a9a0e4ba600007a7c1d11239bafbbeb52367ffdd45680395ddf96c0ff5df36"
)
PATCH_PLAN_HASH = (
    "26a9d7637648b59cd5fb1900b20d2ba292920db0385493012ce0bc2ec72e932b"
)
HOST_APP_FRAGMENT_SHA256 = (
    "356b49b8b9a701b12bc06d36eee28f99ebb40642f5f5e133d66819a7f58be24f"
)
PATCH_PREREGISTRATION_IMPLEMENTATION_SHA256 = (
    "a0424d797b54300c35956eeb930ddd60a56075f3454a50c563b1694d8e89e14c"
)
PATCH_PREREGISTRATION_TEST_SHA256 = (
    "cad1bbc1da09a42e2ddd751fdfb3bb6837fd14f62af727b50c8952bb777436cb"
)
ADR0295_SHA256 = (
    "aa85504422e1029b98c2047a48cd288c04a3acb4e84ec7ffeb3d46fd074cfa8b"
)
STRICT_CANONICAL_JS_SHA256 = (
    "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39"
)
ADMISSION_RAIL_JS_SHA256 = (
    "10604c3ec6953310cbbdb6c213261e538041bab7e236ea10d6fd0311dc5e8e87"
)
DELIVERY_ADAPTER_JS_SHA256 = (
    "5271d1122ef712cf2be7a2955d906e5ff436b6ea8102438187a5b957cf10d0c7"
)
REVIEW_IMPLEMENTATION_SHA256 = (
    "7fe82458e3d9b2e2df853a8203b4f3cea82a4edf5f957bbb0a122a09a1eccc44"
)
REVIEW_NODE_TEST_SHA256 = (
    "e97745d653a71e8b2d36b56a6dfe09ffad553da7290e783b3f0b4b357f7abf63"
)
PYTHON_DELIVERY_FIXTURE_TEST_SHA256 = (
    "1eb0606c739eb6f3ee203617eb324bff6d22d3900103e38b685f23aa55e28ea0"
)
ADR0296_SHA256 = (
    "6b5b9fe946d61d385f7a8ccaae90afd2e103f6321852dc527954dff950ce7a87"
)

_STAGE_ORDER = ["SOURCE", "GAP", "MATURITY", "PERMISSION"]
_HOST_PLAN_KEYS = (
    "app_importer",
    "browser_global_binding",
    "browser_review_receipt",
    "external_review_attestation",
    "html_script",
    "mount_slot",
    "node_test_executor",
    "python_fixture_executor",
    "route",
)
_AUTHORITY_KEYS = (
    "app_import_allowed",
    "browser_execution_allowed",
    "current_admission_allowed",
    "dom_mount_allowed",
    "external_independent_review_completion_allowed",
    "host_asset_write_allowed",
    "live_order_allowed",
    "paper_authorized",
    "review_asset_execution_allowed",
    "route_registration_allowed",
    "runtime_asset_loading_allowed",
    "test_fixture_execution_allowed",
    "writer_allowed",
)


def _plain_json_snapshot(value: Any, active: set[int] | None = None) -> Any:
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("non-finite values are not permitted")
        return value
    if type(value) not in {dict, list}:
        raise TypeError("asset registration requires native JSON values")
    active = set() if active is None else active
    marker = id(value)
    if marker in active:
        raise ValueError("cyclic asset registration is not permitted")
    active.add(marker)
    try:
        if type(value) is list:
            return [_plain_json_snapshot(item, active) for item in value]
        snapshot: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError("asset registration keys must be strings")
            snapshot[key] = _plain_json_snapshot(item, active)
        return snapshot
    finally:
        active.remove(marker)


def _locked_authority() -> dict[str, bool]:
    return {key: False for key in _AUTHORITY_KEYS}


def _asset_manifest() -> list[dict[str, str]]:
    rows = [
        {
            "asset_id": "adr0296",
            "path": "docs/adr/0296-static-presentation-unmounted-render-review-v1.md",
            "role": "decision",
            "sha256": ADR0296_SHA256,
        },
        {
            "asset_id": "delivery_javascript",
            "path": (
                "exchange_terminal/static/"
                "evidence_static_presentation_in_memory_delivery_v1.js"
            ),
            "role": "production_dependency",
            "sha256": DELIVERY_ADAPTER_JS_SHA256,
        },
        {
            "asset_id": "python_delivery_fixture_test",
            "path": "tests/test_static_presentation_in_memory_delivery_v1.py",
            "role": "test_only_dependency",
            "sha256": PYTHON_DELIVERY_FIXTURE_TEST_SHA256,
        },
        {
            "asset_id": "rail_javascript",
            "path": (
                "exchange_terminal/static/"
                "evidence_portfolio_correlation_admission_rail_v1.js"
            ),
            "role": "production_dependency",
            "sha256": ADMISSION_RAIL_JS_SHA256,
        },
        {
            "asset_id": "review_javascript",
            "path": (
                "exchange_terminal/static/"
                "evidence_static_presentation_unmounted_render_review_v1.js"
            ),
            "role": "production",
            "sha256": REVIEW_IMPLEMENTATION_SHA256,
        },
        {
            "asset_id": "review_node_test",
            "path": (
                "exchange_terminal/static/"
                "evidence_static_presentation_unmounted_render_review_v1.test.js"
            ),
            "role": "verification",
            "sha256": REVIEW_NODE_TEST_SHA256,
        },
        {
            "asset_id": "strict_canonical_javascript",
            "path": "exchange_terminal/static/strict_canonical_json_v1.js",
            "role": "production_dependency",
            "sha256": STRICT_CANONICAL_JS_SHA256,
        },
    ]
    return sorted(rows, key=lambda row: row["asset_id"])


def _assert_exact_patch_preregistration() -> None:
    registration = build_static_presentation_host_patch_preregistration_v1()
    operations = registration.get("patch_plan", {}).get("operations", [])
    if (
        not verify_static_presentation_host_patch_preregistration_v1(registration)
        or registration.get("schema_version")
        != PATCH_PREREGISTRATION_SCHEMA_VERSION
        or registration.get("static_fingerprint")
        != PATCH_PREREGISTRATION_STATIC_FINGERPRINT
        or registration.get("patch_preregistration_hash")
        != PATCH_PREREGISTRATION_HASH
        or registration.get("patch_plan_hash") != PATCH_PLAN_HASH
        or len(operations) != 4
        or operations[-1].get("fragment_sha256") != HOST_APP_FRAGMENT_SHA256
        or registration.get("status") != "BLOCKED"
        or any(
            value is not None
            for value in registration.get("execution_plan", {}).values()
        )
        or any(
            value is not False
            for value in registration.get("authority", {}).values()
        )
    ):
        raise RuntimeError("host patch preregistration is not exact")


def build_static_presentation_unmounted_render_review_asset_registration_v1(
) -> dict[str, Any]:
    _assert_exact_patch_preregistration()
    assets = _asset_manifest()
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "registration_id": REGISTRATION_ID,
        "status": STATUS,
        "registration_state": "NO_DOM_RENDER_REVIEW_ASSETS_REGISTERED_UNBOUND",
        "decision": (
            "EXACT_REVIEW_ASSETS_RUNTIME_DEPENDENCIES_AND_TEST_ONLY_BRIDGE_"
            "PINNED_LOADING_EXECUTION_EXTERNAL_REVIEW_HOST_BROWSER_MOUNT_"
            "CURRENT_AND_TRADING_UNBOUND"
        ),
        "source_contract": {
            "patch_preregistration_schema_version": (
                PATCH_PREREGISTRATION_SCHEMA_VERSION
            ),
            "patch_preregistration_static_fingerprint": (
                PATCH_PREREGISTRATION_STATIC_FINGERPRINT
            ),
            "patch_preregistration_hash": PATCH_PREREGISTRATION_HASH,
            "patch_plan_hash": PATCH_PLAN_HASH,
            "host_app_fragment_sha256": HOST_APP_FRAGMENT_SHA256,
            "implementation_path": (
                "exchange_terminal/services/"
                "static_presentation_host_patch_preregistration_v1.py"
            ),
            "implementation_sha256": (
                PATCH_PREREGISTRATION_IMPLEMENTATION_SHA256
            ),
            "test_path": "tests/test_static_presentation_host_patch_preregistration_v1.py",
            "test_sha256": PATCH_PREREGISTRATION_TEST_SHA256,
            "adr_path": "docs/adr/0295-static-presentation-host-patch-preregistration-v1.md",
            "adr_sha256": ADR0295_SHA256,
        },
        "review_contract": {
            "schema_version": (
                "static-presentation-unmounted-render-review-receipt-v1"
            ),
            "static_fingerprint": (
                "20260823-static-presentation-unmounted-render-review-"
                "v1-no-dom-lock-1"
            ),
            "module_format": "UMD_COMMONJS",
            "browser_global": (
                "HakimiStaticPresentationUnmountedRenderReviewV1"
            ),
            "expected_commonjs_exports": [
                "HOST_APP_FRAGMENT_SHA256",
                "PATCH_PLAN_HASH",
                "PATCH_PREREGISTRATION_HASH",
                "SCHEMA_VERSION",
                "STAGE_ORDER",
                "STATIC_FINGERPRINT",
                "buildStaticPresentationUnmountedRenderReviewReceiptV1",
                "verifyStaticPresentationUnmountedRenderReviewReceiptV1",
            ],
            "stage_order": list(_STAGE_ORDER),
            "no_dom_environment_required": True,
            "local_behavior_review_only": True,
            "external_independent_review_complete": False,
            "ready_word_allowed": False,
            "raw_envelope_embedded": False,
            "raw_source_candidate_embedded": False,
            "raw_markup_embedded": False,
        },
        "production_load_order": [
            "strict_canonical_javascript",
            "rail_javascript",
            "delivery_javascript",
            "review_javascript",
        ],
        "test_contract": {
            "node_test_asset_id": "review_node_test",
            "python_fixture_asset_id": "python_delivery_fixture_test",
            "python_fixture_mode": "TEST_ONLY_CHILD_PROCESS",
            "python_fixture_is_runtime_asset": False,
            "node_child_process_is_runtime_capability": False,
            "browser_required": False,
            "service_required": False,
        },
        "asset_manifest": assets,
        "asset_manifest_hash": strict_canonical_hash(assets),
        "host_plan": {key: None for key in _HOST_PLAN_KEYS},
        "activation_order": [
            "HOST_PATCH_PREREGISTRATION_EXACT",
            "REVIEW_ASSETS_AND_DEPENDENCIES_PINNED",
            "NO_DOM_REVIEW_ASSET_REGISTRATION",
            "EXTERNAL_INDEPENDENT_REVIEW_REQUEST",
            "AUTHENTICATED_EXTERNAL_ATTESTATION",
            "EXPLICIT_HOST_WRITE_AUTHORIZATION",
            "HOST_PATCH_AND_ROLLBACK_BINDING",
            "BROWSER_VISUAL_REVIEW",
            "DOM_MOUNT_AND_CURRENT_ACTIVATION",
        ],
        "blockers": [
            "EXTERNAL_INDEPENDENT_REVIEW_NOT_COMPLETED",
            "HOST_WRITE_AUTHORIZATION_ABSENT",
            "APP_IMPORTER_UNBOUND",
            "HTML_SCRIPT_UNBOUND",
            "HOST_PATCH_NOT_APPLIED",
            "BROWSER_VISUAL_REVIEW_NOT_PERFORMED",
            "DOM_MOUNT_UNAUTHORIZED",
            "CURRENT_ADMISSION_LOCKED",
        ],
        "facts": {
            "patch_preregistration_exactly_verified": True,
            "review_assets_registered": True,
            "production_dependencies_pinned": True,
            "test_only_bridge_pinned": True,
            "python_fixture_excluded_from_runtime_load_order": True,
            "review_assets_runtime_loaded": False,
            "node_test_executed_by_registration": False,
            "python_fixture_executed_by_registration": False,
            "external_independent_review_complete": False,
            "host_patch_applied": False,
            "browser_executed": False,
            "dom_mounted": False,
            "current_activated": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "asset_registration_hash")


def verify_static_presentation_unmounted_render_review_asset_registration_v1(
    document: Any,
) -> bool:
    try:
        snapshot = _plain_json_snapshot(document)
        expected = (
            build_static_presentation_unmounted_render_review_asset_registration_v1()
        )
    except Exception:
        return False
    return strict_json_contract_equal(snapshot, expected)


__all__ = [
    "PATCH_PREREGISTRATION_HASH",
    "REGISTRATION_ID",
    "REVIEW_IMPLEMENTATION_SHA256",
    "REVIEW_NODE_TEST_SHA256",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_static_presentation_unmounted_render_review_asset_registration_v1",
    "verify_static_presentation_unmounted_render_review_asset_registration_v1",
]
