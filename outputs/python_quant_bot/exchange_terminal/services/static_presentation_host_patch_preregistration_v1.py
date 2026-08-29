"""Preregister and roundtrip-preview host patches without writing host files."""

from __future__ import annotations

from hashlib import sha256
import math
from typing import Any

from exchange_terminal.services.static_presentation_application_load_descriptor_preregistration_v1 import (
    SCHEMA_VERSION as LOAD_DESCRIPTOR_SCHEMA_VERSION,
    STATIC_FINGERPRINT as LOAD_DESCRIPTOR_STATIC_FINGERPRINT,
    build_static_presentation_application_load_descriptor_preregistration_v1,
    verify_static_presentation_application_load_descriptor_preregistration_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = "static-presentation-host-patch-preregistration-v1"
ROUNDTRIP_SCHEMA_VERSION = (
    "static-presentation-host-patch-in-memory-roundtrip-evidence-v1"
)
STATIC_FINGERPRINT = (
    "20260823-static-presentation-host-patch-v1-not-applied-lock-1"
)
STATUS = "BLOCKED"

LOAD_DESCRIPTOR_HASH = (
    "5e42639940fab6645968421f7637948926f42eb4ccab4d22849d0bcb3ab666a4"
)
LOAD_DESCRIPTOR_IMPLEMENTATION_SHA256 = (
    "4c4fc4a21f101451fa4be9ebe26f939ef4d49e16bd49988639be0c4f21c73f09"
)
LOAD_DESCRIPTOR_TEST_SHA256 = (
    "ad478dbd84909974bdd6e0a27dcc63c62267afcb1fbde707f6ae5b1b4bd22894"
)
ADR0294_SHA256 = (
    "69027f11e643542ef88c884a272cdb709fe47a29790faad7df8cbd235c4b2985"
)
HOST_INDEX_HTML_SHA256 = (
    "553b33b0c4ef4ffb3e2f49d6671fe011f687696b95a7f5ff069f51f57bd5cd13"
)
HOST_APP_JS_SHA256 = (
    "9bf55162aff8d7a233804557c91605c801b92f515b2835978c05e2d1f3ef9210"
)
EXPECTED_INDEX_HTML_POST_SHA256 = (
    "4cc17b2b8c10d5c30ac86bc94ed70b54422887d6d49645012769702f6bfb027c"
)
EXPECTED_APP_JS_POST_SHA256 = (
    "d7470170c123f098b0385533acfd2b44df3a1e436c9869d3d53cff68b66f0ced"
)

STYLE_LINK_FRAGMENT_SHA256 = (
    "6b78fb86b71556a801f65a07f14e181dfc32a9dc38bde45c436404e387197357"
)
HOST_SLOT_FRAGMENT_SHA256 = (
    "7b654a5802a48a605420136ce603ed08026936f85d2a0a650d6bcc62920cffce"
)
SCRIPT_TAGS_FRAGMENT_SHA256 = (
    "15aac5cc3868d01d19b9c2de095fa6f230864a080215204b3bcef6a38f83ef3f"
)
APP_BINDING_FRAGMENT_SHA256 = (
    "356b49b8b9a701b12bc06d36eee28f99ebb40642f5f5e133d66819a7f58be24f"
)

_INDEX_PATH = "exchange_terminal/static/index.html"
_APP_PATH = "exchange_terminal/static/app.js"
_STYLE_ANCHOR = (
    '  <link rel="stylesheet" '
    'href="./styles.css?v=20260822-evidence-calibration-rail-2">'
)
_STYLE_FRAGMENT = (
    "\r\n  <link rel=\"stylesheet\" "
    "href=\"./evidence_portfolio_correlation_admission_rail_v1.css"
    "?v=20260823-admission-rail-1\">"
)
_SLOT_ANCHOR = (
    '          <div id="researchDataQualityCards" '
    'class="research-data-quality-grid"></div>'
)
_SLOT_FRAGMENT = (
    "\r\n          <div id=\"portfolioCorrelationAdmissionRailHost\" "
    "class=\"portfolio-correlation-admission-rail-host\" "
    "aria-live=\"polite\"></div>"
)
_APP_SCRIPT_ANCHOR = (
    '  <script src="./app.js?v=20260821-correlation-multiplicity-ledger-1">'
    "</script>"
)
_SCRIPT_FRAGMENT = "\r\n".join((
    '  <script src="./strict_canonical_json_v1.js'
    '?v=20260823-static-presentation-1"></script>',
    '  <script src="./evidence_portfolio_correlation_admission_rail_v1.js'
    '?v=20260823-admission-rail-1"></script>',
    '  <script src="./evidence_static_presentation_in_memory_delivery_v1.js'
    '?v=20260823-delivery-adapter-1"></script>',
    "",
))
_APP_BINDING_FRAGMENT = "\n".join((
    "",
    "",
    ";(function attachPortfolioCorrelationAdmissionRailHostV1(root) {",
    '  "use strict";',
    "",
    "  function unknownRenderCandidate(reasonCode) {",
    "    return Object.freeze({",
    '      schema_version: "portfolio-correlation-admission-rail-host-render-candidate-v1",',
    '      status: "UNKNOWN",',
    '      render_state: "UNKNOWN",',
    "      reason_code: reasonCode,",
    "      envelope_hash: null,",
    "      source_hash: null,",
    "      delivery_receipt_hash: null,",
    "      markup: null,",
    "    });",
    "  }",
    "",
    "  function buildPortfolioCorrelationAdmissionRailHostRenderCandidateV1(envelope) {",
    "    const delivery = root.HakimiStaticPresentationInMemoryDeliveryV1;",
    "    const rail = root.HakimiPortfolioCorrelationAdmissionRailV1;",
    "    if (!delivery || !rail) {",
    '      return unknownRenderCandidate("PRESENTATION_DEPENDENCY_UNAVAILABLE");',
    "    }",
    "    if (!delivery.verifyStaticPresentationInMemoryDeliveryEnvelopeV1(envelope)) {",
    '      return unknownRenderCandidate("DELIVERY_ENVELOPE_NOT_EXACT");',
    "    }",
    "    const candidate = delivery.extractAdmissionCandidateFromEnvelopeV1(envelope);",
    '    if (!candidate) return unknownRenderCandidate("ADMISSION_CANDIDATE_UNKNOWN");',
    "    const receipt = delivery.buildStaticPresentationInMemoryDeliveryReceiptV1(envelope);",
    "    if (!delivery.verifyStaticPresentationInMemoryDeliveryReceiptV1(receipt, envelope)) {",
    '      return unknownRenderCandidate("DELIVERY_RECEIPT_NOT_EXACT");',
    "    }",
    "    return Object.freeze({",
    '      schema_version: "portfolio-correlation-admission-rail-host-render-candidate-v1",',
    '      status: "BLOCKED",',
    '      render_state: "EXACT_UNMOUNTED_MARKUP_CANDIDATE",',
    '      reason_code: "EXACT_LOCAL_PRESENTATION_DERIVED_DOM_MOUNT_UNAUTHORIZED",',
    "      envelope_hash: envelope.envelope_hash,",
    "      source_hash: candidate.correlation_admission_hash,",
    "      delivery_receipt_hash: receipt.receipt_hash,",
    "      markup: rail.renderPortfolioCorrelationAdmissionRailV1(candidate),",
    "    });",
    "  }",
    "",
    "  root.HakimiPortfolioCorrelationAdmissionRailHostV1 = Object.freeze({",
    "    buildPortfolioCorrelationAdmissionRailHostRenderCandidateV1:",
    "      buildPortfolioCorrelationAdmissionRailHostRenderCandidateV1,",
    "  });",
    '})(typeof window !== "undefined" ? window : globalThis);',
    "",
))

_AUTHORITY_KEYS = (
    "app_fragment_execution_allowed",
    "browser_execution_allowed",
    "current_admission_allowed",
    "dom_mount_allowed",
    "host_asset_write_allowed",
    "live_order_allowed",
    "paper_authorized",
    "patch_application_allowed",
    "rollback_application_allowed",
    "runtime_asset_loading_allowed",
    "writer_allowed",
)


class _RoundtripError(ValueError):
    pass


def _text_hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _plain_json_snapshot(value: Any, active: set[int] | None = None) -> Any:
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("non-finite values are not permitted")
        return value
    if type(value) not in {dict, list}:
        raise TypeError("patch documents require native JSON values")
    active = set() if active is None else active
    marker = id(value)
    if marker in active:
        raise ValueError("cyclic patch documents are not permitted")
    active.add(marker)
    try:
        if type(value) is list:
            return [_plain_json_snapshot(item, active) for item in value]
        snapshot: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError("patch document keys must be strings")
            snapshot[key] = _plain_json_snapshot(item, active)
        return snapshot
    finally:
        active.remove(marker)


def _locked_authority() -> dict[str, bool]:
    return {key: False for key in _AUTHORITY_KEYS}


def _operation(
    sequence: int,
    operation_id: str,
    target_path: str,
    operation_type: str,
    anchor: str,
    required_anchor_count: int,
    fragment: str,
) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "operation_id": operation_id,
        "target_path": target_path,
        "operation_type": operation_type,
        "anchor": anchor,
        "anchor_sha256": _text_hash(anchor),
        "required_anchor_count": required_anchor_count,
        "fragment": fragment,
        "fragment_sha256": _text_hash(fragment),
        "fragment_length": len(fragment),
        "performed": False,
    }


def _patch_plan() -> dict[str, Any]:
    fragments = {
        STYLE_LINK_FRAGMENT_SHA256: _STYLE_FRAGMENT,
        HOST_SLOT_FRAGMENT_SHA256: _SLOT_FRAGMENT,
        SCRIPT_TAGS_FRAGMENT_SHA256: _SCRIPT_FRAGMENT,
        APP_BINDING_FRAGMENT_SHA256: _APP_BINDING_FRAGMENT,
    }
    if any(_text_hash(fragment) != digest for digest, fragment in fragments.items()):
        raise RuntimeError("host patch fragment fingerprint drifted")
    return {
        "content_encoding": "utf-8",
        "line_ending_policy": "PRESERVE_EXISTING_WITH_PINNED_FRAGMENT_ENDINGS",
        "targets": [
            {
                "target_id": "index_html",
                "path": _INDEX_PATH,
                "pre_sha256": HOST_INDEX_HTML_SHA256,
                "expected_post_sha256": EXPECTED_INDEX_HTML_POST_SHA256,
                "write_performed": False,
            },
            {
                "target_id": "app_javascript",
                "path": _APP_PATH,
                "pre_sha256": HOST_APP_JS_SHA256,
                "expected_post_sha256": EXPECTED_APP_JS_POST_SHA256,
                "write_performed": False,
            },
        ],
        "operations": [
            _operation(
                1,
                "INDEX_ISOLATED_STYLESHEET_AFTER_BASE",
                _INDEX_PATH,
                "INSERT_AFTER_UNIQUE_ANCHOR",
                _STYLE_ANCHOR,
                1,
                _STYLE_FRAGMENT,
            ),
            _operation(
                2,
                "INDEX_EMPTY_RAIL_SLOT_AFTER_RESEARCH_QUALITY",
                _INDEX_PATH,
                "INSERT_AFTER_UNIQUE_ANCHOR",
                _SLOT_ANCHOR,
                1,
                _SLOT_FRAGMENT,
            ),
            _operation(
                3,
                "INDEX_DEPENDENCY_SCRIPTS_BEFORE_APP",
                _INDEX_PATH,
                "INSERT_BEFORE_UNIQUE_ANCHOR",
                _APP_SCRIPT_ANCHOR,
                1,
                _SCRIPT_FRAGMENT,
            ),
            _operation(
                4,
                "APP_UNMOUNTED_RENDER_CANDIDATE_APPEND",
                _APP_PATH,
                "APPEND_EXACT_SUFFIX",
                "",
                0,
                _APP_BINDING_FRAGMENT,
            ),
        ],
    }


def _assert_exact_load_descriptor() -> None:
    descriptor = (
        build_static_presentation_application_load_descriptor_preregistration_v1()
    )
    if (
        not verify_static_presentation_application_load_descriptor_preregistration_v1(
            descriptor
        )
        or descriptor.get("schema_version") != LOAD_DESCRIPTOR_SCHEMA_VERSION
        or descriptor.get("static_fingerprint")
        != LOAD_DESCRIPTOR_STATIC_FINGERPRINT
        or descriptor.get("load_descriptor_hash") != LOAD_DESCRIPTOR_HASH
        or descriptor.get("status") != "BLOCKED"
        or any(row.get("performed") is not False for row in descriptor.get("planned_mutations", []))
        or any(value is not False for value in descriptor.get("authority", {}).values())
    ):
        raise RuntimeError("application load descriptor is not exact")


def build_static_presentation_host_patch_preregistration_v1() -> dict[str, Any]:
    _assert_exact_load_descriptor()
    patch_plan = _patch_plan()
    rollback_plan = {
        "exact_post_image_required": True,
        "reverse_operation_ids": [
            row["operation_id"]
            for row in reversed(patch_plan["operations"])
        ],
        "expected_recovered_targets": [
            {
                "path": row["path"],
                "recovered_sha256": row["pre_sha256"],
            }
            for row in patch_plan["targets"]
        ],
        "rollback_performed": False,
    }
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": STATUS,
        "preregistration_state": (
            "EXACT_REVERSIBLE_HOST_PATCH_PLAN_REGISTERED_NOT_APPLIED"
        ),
        "decision": (
            "PINNED_HOST_PREIMAGES_FRAGMENTS_POSTIMAGES_AND_ROLLBACK_"
            "NO_WRITER_EXECUTION_BROWSER_MOUNT_CURRENT_OR_TRADING_AUTHORITY"
        ),
        "source_contract": {
            "load_descriptor_schema_version": LOAD_DESCRIPTOR_SCHEMA_VERSION,
            "load_descriptor_static_fingerprint": (
                LOAD_DESCRIPTOR_STATIC_FINGERPRINT
            ),
            "load_descriptor_hash": LOAD_DESCRIPTOR_HASH,
            "implementation_path": (
                "exchange_terminal/services/"
                "static_presentation_application_load_descriptor_preregistration_v1.py"
            ),
            "implementation_sha256": LOAD_DESCRIPTOR_IMPLEMENTATION_SHA256,
            "test_path": (
                "tests/"
                "test_static_presentation_application_load_descriptor_preregistration_v1.py"
            ),
            "test_sha256": LOAD_DESCRIPTOR_TEST_SHA256,
            "adr_path": (
                "docs/adr/"
                "0294-static-presentation-application-load-descriptor-preregistration-v1.md"
            ),
            "adr_sha256": ADR0294_SHA256,
        },
        "patch_plan": patch_plan,
        "patch_plan_hash": strict_canonical_hash(patch_plan),
        "rollback_plan": rollback_plan,
        "rollback_plan_hash": strict_canonical_hash(rollback_plan),
        "execution_plan": {
            "approval_receipt": None,
            "patch_executor": None,
            "rollback_executor": None,
            "writer": None,
            "browser_review_receipt": None,
            "mount_receipt": None,
        },
        "activation_order": [
            "LOAD_DESCRIPTOR_EXACT",
            "HOST_PREIMAGE_HASHES_PINNED",
            "PATCH_FRAGMENTS_AND_POSTIMAGES_PINNED",
            "IN_MEMORY_APPLY_AND_ROLLBACK_ROUNDTRIP",
            "INDEPENDENT_PATCH_REVIEW",
            "EXPLICIT_HOST_WRITE_AUTHORIZATION",
            "HOST_PATCH_APPLICATION",
            "UNMOUNTED_RENDER_REVIEW",
            "BROWSER_VISUAL_REVIEW",
            "DOM_MOUNT_AND_CURRENT_ACTIVATION",
        ],
        "blockers": [
            "INDEPENDENT_PATCH_REVIEW_NOT_RECORDED",
            "HOST_WRITE_AUTHORIZATION_ABSENT",
            "PATCH_EXECUTOR_UNBOUND",
            "ROLLBACK_EXECUTOR_UNBOUND",
            "HOST_PATCH_NOT_APPLIED",
            "UNMOUNTED_RENDER_REVIEW_NOT_PERFORMED",
            "BROWSER_VISUAL_REVIEW_NOT_PERFORMED",
            "DOM_MOUNT_UNAUTHORIZED",
            "CURRENT_ADMISSION_LOCKED",
        ],
        "facts": {
            "load_descriptor_exactly_verified": True,
            "host_preimages_pinned": True,
            "patch_fragments_pinned": True,
            "expected_postimages_pinned": True,
            "rollback_order_pinned": True,
            "patch_operations_performed": False,
            "rollback_performed": False,
            "host_files_written": False,
            "app_fragment_executed": False,
            "html_parsed": False,
            "browser_executed": False,
            "dom_mounted": False,
            "current_activated": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "patch_preregistration_hash")


def verify_static_presentation_host_patch_preregistration_v1(
    document: Any,
) -> bool:
    try:
        snapshot = _plain_json_snapshot(document)
        expected = build_static_presentation_host_patch_preregistration_v1()
    except Exception:
        return False
    return strict_json_contract_equal(snapshot, expected)


def _apply_operation(source: str, operation: dict[str, Any]) -> str:
    fragment = operation["fragment"]
    if fragment in source:
        raise _RoundtripError("PATCH_FRAGMENT_ALREADY_PRESENT")
    operation_type = operation["operation_type"]
    if operation_type == "APPEND_EXACT_SUFFIX":
        return source + fragment
    anchor = operation["anchor"]
    if source.count(anchor) != operation["required_anchor_count"]:
        raise _RoundtripError("PATCH_ANCHOR_CONTRACT_FAILED")
    if operation_type == "INSERT_AFTER_UNIQUE_ANCHOR":
        return source.replace(anchor, anchor + fragment, 1)
    if operation_type == "INSERT_BEFORE_UNIQUE_ANCHOR":
        return source.replace(anchor, fragment + anchor, 1)
    raise _RoundtripError("PATCH_OPERATION_TYPE_UNKNOWN")


def _reverse_operation(source: str, operation: dict[str, Any]) -> str:
    fragment = operation["fragment"]
    operation_type = operation["operation_type"]
    if operation_type == "APPEND_EXACT_SUFFIX":
        if not source.endswith(fragment):
            raise _RoundtripError("ROLLBACK_SUFFIX_CONTRACT_FAILED")
        return source[:-len(fragment)]
    anchor = operation["anchor"]
    if operation_type == "INSERT_AFTER_UNIQUE_ANCHOR":
        combined = anchor + fragment
    elif operation_type == "INSERT_BEFORE_UNIQUE_ANCHOR":
        combined = fragment + anchor
    else:
        raise _RoundtripError("ROLLBACK_OPERATION_TYPE_UNKNOWN")
    if source.count(combined) != 1:
        raise _RoundtripError("ROLLBACK_ANCHOR_CONTRACT_FAILED")
    return source.replace(combined, anchor, 1)


def _simulate_roundtrip(
    patch_plan: dict[str, Any],
    index_html_source: str,
    app_javascript_source: str,
) -> dict[str, dict[str, str]]:
    sources = {
        _INDEX_PATH: index_html_source,
        _APP_PATH: app_javascript_source,
    }
    targets = {row["path"]: row for row in patch_plan["targets"]}
    if any(_text_hash(sources[path]) != row["pre_sha256"] for path, row in targets.items()):
        raise _RoundtripError("HOST_PRECONDITION_HASH_MISMATCH")
    for operation in patch_plan["operations"]:
        path = operation["target_path"]
        sources[path] = _apply_operation(sources[path], operation)
    if any(
        _text_hash(sources[path]) != row["expected_post_sha256"]
        for path, row in targets.items()
    ):
        raise _RoundtripError("PATCH_POSTIMAGE_HASH_MISMATCH")
    post_hashes = {path: _text_hash(value) for path, value in sources.items()}
    for operation in reversed(patch_plan["operations"]):
        path = operation["target_path"]
        sources[path] = _reverse_operation(sources[path], operation)
    if any(_text_hash(sources[path]) != row["pre_sha256"] for path, row in targets.items()):
        raise _RoundtripError("ROLLBACK_RECOVERY_HASH_MISMATCH")
    return {
        path: {
            "pre_sha256": targets[path]["pre_sha256"],
            "post_sha256": post_hashes[path],
            "recovered_sha256": _text_hash(sources[path]),
        }
        for path in (_INDEX_PATH, _APP_PATH)
    }


def _build_roundtrip_evidence(
    *,
    status: str,
    reason_code: str,
    preregistration_hash: str | None,
    load_descriptor_hash: str | None,
    patch_plan_hash: str | None,
    target_hashes: dict[str, dict[str, str]] | None,
    preregistration_exact: bool,
    descriptor_exact: bool,
    roundtrip_exact: bool,
) -> dict[str, Any]:
    document = {
        "schema_version": ROUNDTRIP_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "roundtrip_state": (
            "EXACT_IN_MEMORY_APPLY_AND_ROLLBACK_HASH_ROUNDTRIP"
            if roundtrip_exact
            else "UNKNOWN"
        ),
        "reason_code": reason_code,
        "patch_preregistration_hash": preregistration_hash,
        "load_descriptor_hash": load_descriptor_hash,
        "patch_plan_hash": patch_plan_hash,
        "target_hashes": target_hashes,
        "operation_count": 4 if roundtrip_exact else None,
        "facts": {
            "patch_preregistration_exactly_verified": preregistration_exact,
            "load_descriptor_exactly_verified": descriptor_exact,
            "host_preconditions_exact": roundtrip_exact,
            "unique_anchor_contracts_exact": roundtrip_exact,
            "postimage_hashes_exact": roundtrip_exact,
            "rollback_recovery_hashes_exact": roundtrip_exact,
            "raw_host_sources_embedded": False,
            "raw_patched_sources_embedded": False,
            "host_files_written": False,
            "app_fragment_executed": False,
            "html_parsed": False,
            "browser_executed": False,
            "dom_mounted": False,
            "current_activated": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "roundtrip_evidence_hash")


def build_static_presentation_host_patch_in_memory_roundtrip_evidence_v1(
    patch_preregistration_document: Any,
    load_descriptor_document: Any,
    index_html_source: Any,
    app_javascript_source: Any,
) -> dict[str, Any]:
    try:
        preregistration = _plain_json_snapshot(patch_preregistration_document)
    except Exception:
        return _build_roundtrip_evidence(
            status="UNKNOWN",
            reason_code="PATCH_PREREGISTRATION_SNAPSHOT_FAILED",
            preregistration_hash=None,
            load_descriptor_hash=None,
            patch_plan_hash=None,
            target_hashes=None,
            preregistration_exact=False,
            descriptor_exact=False,
            roundtrip_exact=False,
        )
    if not verify_static_presentation_host_patch_preregistration_v1(preregistration):
        return _build_roundtrip_evidence(
            status="UNKNOWN",
            reason_code="PATCH_PREREGISTRATION_NOT_EXACT",
            preregistration_hash=None,
            load_descriptor_hash=None,
            patch_plan_hash=None,
            target_hashes=None,
            preregistration_exact=False,
            descriptor_exact=False,
            roundtrip_exact=False,
        )
    try:
        descriptor = _plain_json_snapshot(load_descriptor_document)
    except Exception:
        descriptor = None
    if (
        descriptor is None
        or not verify_static_presentation_application_load_descriptor_preregistration_v1(
            descriptor
        )
        or descriptor.get("load_descriptor_hash") != LOAD_DESCRIPTOR_HASH
    ):
        return _build_roundtrip_evidence(
            status="UNKNOWN",
            reason_code="LOAD_DESCRIPTOR_NOT_EXACT",
            preregistration_hash=preregistration["patch_preregistration_hash"],
            load_descriptor_hash=None,
            patch_plan_hash=preregistration["patch_plan_hash"],
            target_hashes=None,
            preregistration_exact=True,
            descriptor_exact=False,
            roundtrip_exact=False,
        )
    if type(index_html_source) is not str or type(app_javascript_source) is not str:
        reason_code = "HOST_SOURCE_TYPE_INVALID"
        target_hashes = None
    else:
        try:
            target_hashes = _simulate_roundtrip(
                preregistration["patch_plan"],
                index_html_source,
                app_javascript_source,
            )
            reason_code = "EXACT_HOST_PATCH_AND_ROLLBACK_SIMULATED_IN_MEMORY"
        except _RoundtripError as exc:
            reason_code = str(exc)
            target_hashes = None
    roundtrip_exact = target_hashes is not None
    return _build_roundtrip_evidence(
        status="BLOCKED" if roundtrip_exact else "UNKNOWN",
        reason_code=reason_code,
        preregistration_hash=preregistration["patch_preregistration_hash"],
        load_descriptor_hash=descriptor["load_descriptor_hash"],
        patch_plan_hash=preregistration["patch_plan_hash"],
        target_hashes=target_hashes,
        preregistration_exact=True,
        descriptor_exact=True,
        roundtrip_exact=roundtrip_exact,
    )


def verify_static_presentation_host_patch_in_memory_roundtrip_evidence_v1(
    document: Any,
    patch_preregistration_document: Any,
    load_descriptor_document: Any,
    index_html_source: Any,
    app_javascript_source: Any,
) -> bool:
    try:
        snapshot = _plain_json_snapshot(document)
    except Exception:
        return False
    expected = build_static_presentation_host_patch_in_memory_roundtrip_evidence_v1(
        patch_preregistration_document,
        load_descriptor_document,
        index_html_source,
        app_javascript_source,
    )
    return strict_json_contract_equal(snapshot, expected)


__all__ = [
    "APP_BINDING_FRAGMENT_SHA256",
    "EXPECTED_APP_JS_POST_SHA256",
    "EXPECTED_INDEX_HTML_POST_SHA256",
    "LOAD_DESCRIPTOR_HASH",
    "ROUNDTRIP_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_static_presentation_host_patch_in_memory_roundtrip_evidence_v1",
    "build_static_presentation_host_patch_preregistration_v1",
    "verify_static_presentation_host_patch_in_memory_roundtrip_evidence_v1",
    "verify_static_presentation_host_patch_preregistration_v1",
]
