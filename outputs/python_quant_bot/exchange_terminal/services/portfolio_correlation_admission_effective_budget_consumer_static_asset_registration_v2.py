"""Versioned static-asset registration for the correlation admission consumers.

This module is deliberately registration-only.  It verifies the exact ADR0308
asset registration and ADR0314 host-binding preregistration, then registers the
ADR0312 and ADR0313 consumer assets without importing them into an application,
loading them in a browser, or binding any host slot.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from exchange_terminal.services.portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1 import (
    build_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1,
    expected_portfolio_correlation_admission_effective_budget_bridge_asset_spec_v1,
    verify_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1,
)
from exchange_terminal.services.portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1 import (
    build_portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1,
    verify_portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1,
)
from exchange_terminal.services.static_presentation_asset_registration_v1 import (
    build_static_presentation_asset_registration_v1,
    verify_static_presentation_asset_registration_v1,
)


SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-consumer-static-assets-v2"
)
STATIC_FINGERPRINT = (
    "20260824-portfolio-correlation-admission-effective-budget-consumer-"
    "static-assets-v2-unmounted-lock-1"
)
REGISTRATION_ID = (
    "portfolio-correlation-admission-effective-budget-consumer-assets-v2"
)

PREDECESSOR_REGISTRATION_HASH = (
    "265a897bb11a9d2df873f23a3faf5dc21bc4f66bb93ef8d313994e35938d04c4"
)
HOST_BINDING_PREREGISTRATION_HASH = (
    "132eb51549337575ebb1ff80c870e7eb51d66a63b52f73930634e9e0467e9e6b"
)
HOST_BINDING_CANDIDATES_HASH = (
    "5a96998de64af8e7f3be65f54d5889e07e0587b6646c5bdae503b3a7c874ec6d"
)
HOST_JAVASCRIPT_ASSET_MANIFEST_HASH = (
    "8016095846418cbe664dfda72d20b7405fc1d0480f4d2516a4e3cdaa8a131088"
)
HOST_JAVASCRIPT_LOAD_ORDER_HASH = (
    "6512458f5abcec6ebadfc9026bef3ab4c11fc059dc6ca130afe5abcfb9a97a7d"
)

EXPECTED_SPEC_HASH = (
    "bb14803ac0b8ff6aba6d5a9aed3ee3368339a1abf73e84457fa5a2613319aa6d"
)
EXPECTED_ASSET_MANIFEST_HASH = (
    "21a70bdf26842d15fc6e6d0067c3beb7b5b28545546e4bf71fa171631d1a02bf"
)
EXPECTED_REGISTRATION_HASH = (
    "098a8952afbf3459cdcd046b1695bb296a32bdbe44f54d061300ba128c2b2cc0"
)

PROTECTED_STYLESHEET_PATH = "exchange_terminal/static/styles.css"
PROTECTED_STYLESHEET_SHA256 = (
    "ee6a5ae746142e32df768fe3261746f66c2b1a902e38b85fa9c0ecc4ce7bdc2a"
)

SOURCE_CONTRACT = {
    "schema_version": (
        "portfolio-correlation-admission-effective-budget-"
        "host-binding-preregistration-v1"
    ),
    "implementation_path": (
        "exchange_terminal/services/portfolio_correlation_admission_"
        "effective_budget_host_binding_preregistration_v1.py"
    ),
    "implementation_sha256": (
        "340e2a2bb30061f810aa545095909cb0e51bf0f80d7f7b5217ab5359d8fc7850"
    ),
    "test_path": (
        "tests/test_portfolio_correlation_admission_effective_budget_"
        "host_binding_preregistration_v1.py"
    ),
    "test_sha256": (
        "207d3f9f3c7f36d73148ecaae79ec50a77faac574830b0f0a85996f04af846f5"
    ),
    "adr_path": (
        "docs/adr/0314-portfolio-correlation-admission-effective-budget-"
        "host-binding-preregistration-v1.md"
    ),
    "adr_sha256": (
        "7e0c7c08a781c91025f6ba7fc708c25f87d68243a9dc40268806bc3f1888651c"
    ),
}

DELTA_ASSETS = (
    {
        "asset_id": "adr0312",
        "path": (
            "docs/adr/0312-portfolio-correlation-admission-effective-budget-"
            "inspection-consumer-v1.md"
        ),
        "sha256": (
            "e4ab75bf5ac2579843668ec97bfa9cf22ea01e8b63e36f1fb577ce5f6763a718"
        ),
        "role": "decision",
    },
    {
        "asset_id": "adr0313",
        "path": (
            "docs/adr/0313-portfolio-correlation-admission-effective-budget-"
            "cross-runtime-consumer-parity-v1.md"
        ),
        "sha256": (
            "c36d5f262be23b69ad31522b6bd9de713584cc8b51f798dd03c30f843b80cffb"
        ),
        "role": "decision",
    },
    {
        "asset_id": "cross_runtime_parity_acceptance_javascript",
        "path": (
            "exchange_terminal/static/evidence_portfolio_correlation_"
            "admission_effective_budget_cross_runtime_consumer_parity_"
            "acceptance_v1.js"
        ),
        "sha256": (
            "5d848c691ab3e7bbb5528a3bfe818dfc6ab428743f1c9680691a0968e82ad245"
        ),
        "role": "production",
    },
    {
        "asset_id": "cross_runtime_parity_acceptance_node_test",
        "path": (
            "exchange_terminal/static/evidence_portfolio_correlation_"
            "admission_effective_budget_cross_runtime_consumer_parity_"
            "acceptance_v1.test.js"
        ),
        "sha256": (
            "f072cef4e6a2cdc9b1d205ec89df34e8db8940db2ca5b4d2edb3ffbbf2f002f6"
        ),
        "role": "verification",
    },
    {
        "asset_id": "cross_runtime_parity_fixture",
        "path": (
            "tests/fixtures/portfolio_correlation_admission_effective_budget_"
            "cross_runtime_consumer_parity_registration_v1.json"
        ),
        "sha256": (
            "761072df49eca0f8622da4f33ee8ecb0ad4bf4070f7d467906186b7788ec4b02"
        ),
        "role": "verification",
    },
    {
        "asset_id": "cross_runtime_parity_python",
        "path": (
            "exchange_terminal/services/portfolio_correlation_admission_"
            "effective_budget_cross_runtime_consumer_parity_registration_v1.py"
        ),
        "sha256": (
            "366d5850dbdbc0da5e2f7c870304dd4837ac28b38020a1fc35376720131c4e68"
        ),
        "role": "production",
    },
    {
        "asset_id": "cross_runtime_parity_python_test",
        "path": (
            "tests/test_portfolio_correlation_admission_effective_budget_"
            "cross_runtime_consumer_parity_registration_v1.py"
        ),
        "sha256": (
            "0dcf44997ebaf07b3923a4be19f2c80c07aab836e74652c8bb343474544c42b5"
        ),
        "role": "verification",
    },
    {
        "asset_id": "inspection_consumer_fixture",
        "path": (
            "tests/fixtures/portfolio_correlation_admission_effective_budget_"
            "hash_envelope_source_consumer_v1.json"
        ),
        "sha256": (
            "b25be196152f370101bc43cf61e065308761d3070c4edb4656ffd00ad287dbe7"
        ),
        "role": "verification",
    },
    {
        "asset_id": "inspection_consumer_javascript",
        "path": (
            "exchange_terminal/static/evidence_portfolio_correlation_"
            "admission_effective_budget_inspection_consumer_v1.js"
        ),
        "sha256": (
            "7ea19bbcf27a40657623f2f1a5b503e3b834939d4e08519a4455d95b3255b5e6"
        ),
        "role": "production",
    },
    {
        "asset_id": "inspection_consumer_node_test",
        "path": (
            "exchange_terminal/static/evidence_portfolio_correlation_"
            "admission_effective_budget_inspection_consumer_v1.test.js"
        ),
        "sha256": (
            "2fa4f1b2f9abc044e483ca66f3fd3decce10287d18646353b9b7e72b28df680f"
        ),
        "role": "verification",
    },
)

EXPECTED_COMMONJS_EXPORTS = (
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "BROWSER_GLOBAL",
    "PYTHON_RESULT_SCHEMA_VERSION",
    "verifyPortfolioCorrelationAdmissionEffectiveBudgetPythonConsumerResultV1",
    "buildPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1",
    "verifyPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1",
)

SCRIPT_LOAD_ORDER = (
    "strict_canonical_javascript",
    "binding_delivery_javascript",
    "binding_bridge_javascript",
    "inspection_consumer_javascript",
    "cross_runtime_parity_acceptance_javascript",
)

HOST_CANDIDATE_LOAD_ORDER = (
    "exchange_terminal/static/strict_canonical_json_v1.js",
    (
        "exchange_terminal/static/evidence_portfolio_correlation_admission_"
        "effective_budget_in_memory_delivery_v1.js"
    ),
    (
        "exchange_terminal/static/evidence_portfolio_correlation_admission_"
        "effective_budget_bridge_v1.js"
    ),
    (
        "exchange_terminal/static/evidence_portfolio_correlation_admission_"
        "effective_budget_inspection_consumer_v1.js"
    ),
    (
        "exchange_terminal/static/evidence_portfolio_correlation_admission_"
        "effective_budget_cross_runtime_consumer_parity_acceptance_v1.js"
    ),
)


def _require_equal(label: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise ValueError(f"{label} does not match the pinned contract")


def _verify_predecessors() -> None:
    predecessor = (
        build_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1()
    )
    verify_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1(
        predecessor
    )
    _require_equal(
        "ADR0308 registration_hash",
        predecessor.get("registration_hash"),
        PREDECESSOR_REGISTRATION_HASH,
    )

    host = (
        build_portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1()
    )
    verify_portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1(
        host
    )
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

    javascript = host["binding_candidates"]["javascript_assets"]
    _require_equal(
        "ADR0314 javascript asset_manifest_hash",
        javascript.get("asset_manifest_hash"),
        HOST_JAVASCRIPT_ASSET_MANIFEST_HASH,
    )
    _require_equal(
        "ADR0314 javascript load_order_hash",
        javascript.get("load_order_hash"),
        HOST_JAVASCRIPT_LOAD_ORDER_HASH,
    )
    _require_equal(
        "ADR0314 javascript load_order",
        javascript.get("load_order"),
        list(HOST_CANDIDATE_LOAD_ORDER),
    )
    if any(host["authority"].values()):
        raise ValueError("ADR0314 authority must remain fully denied")


def expected_portfolio_correlation_admission_effective_budget_consumer_static_asset_spec_v2() -> dict[str, Any]:
    """Return the exact v2 input spec for the generic static registration."""

    _verify_predecessors()
    predecessor_spec = deepcopy(
        expected_portfolio_correlation_admission_effective_budget_bridge_asset_spec_v1()
    )

    consumer_contract = deepcopy(predecessor_spec["consumer_contract"])
    consumer_contract.update(
        {
            "schema_version": SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "browser_global": (
                "HakimiPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1"
            ),
            "javascript_asset_id": "inspection_consumer_javascript",
            "test_asset_id": "inspection_consumer_node_test",
            "adr_asset_id": "adr0312",
            "expected_commonjs_exports": list(EXPECTED_COMMONJS_EXPORTS),
            "script_load_order": list(SCRIPT_LOAD_ORDER),
        }
    )
    _require_equal(
        "protected stylesheet path",
        consumer_contract.get("protected_stylesheet_path"),
        PROTECTED_STYLESHEET_PATH,
    )
    _require_equal(
        "protected stylesheet sha256",
        consumer_contract.get("protected_stylesheet_sha256"),
        PROTECTED_STYLESHEET_SHA256,
    )

    assets = deepcopy(predecessor_spec["assets"])
    assets.extend(deepcopy(DELTA_ASSETS))

    return {
        "registration_id": REGISTRATION_ID,
        "source_contract": deepcopy(SOURCE_CONTRACT),
        "assets": assets,
        "consumer_contract": consumer_contract,
        "host_plan": {
            "app_importer": None,
            "browser_review_receipt": None,
            "html_script": None,
            "mount_slot": None,
            "route": None,
            "stylesheet_link": None,
        },
    }


def build_portfolio_correlation_admission_effective_budget_consumer_static_asset_registration_v2() -> dict[str, Any]:
    """Build the deterministic, unbound v2 static-asset registration."""

    document = build_static_presentation_asset_registration_v1(
        expected_portfolio_correlation_admission_effective_budget_consumer_static_asset_spec_v2()
    )
    _require_equal("spec_hash", document.get("spec_hash"), EXPECTED_SPEC_HASH)
    _require_equal(
        "asset_manifest_hash",
        document.get("asset_manifest_hash"),
        EXPECTED_ASSET_MANIFEST_HASH,
    )
    _require_equal(
        "registration_hash",
        document.get("registration_hash"),
        EXPECTED_REGISTRATION_HASH,
    )
    return document


def verify_portfolio_correlation_admission_effective_budget_consumer_static_asset_registration_v2(
    document: Any,
) -> bool:
    """Fail closed unless *document* is the exact unbound v2 registration."""

    spec = (
        expected_portfolio_correlation_admission_effective_budget_consumer_static_asset_spec_v2()
    )
    if not verify_static_presentation_asset_registration_v1(document, spec):
        raise ValueError("generic static registration verification failed")
    _require_equal(
        "registration_hash",
        document.get("registration_hash") if isinstance(document, dict) else None,
        EXPECTED_REGISTRATION_HASH,
    )
    return True


__all__ = [
    "DELTA_ASSETS",
    "EXPECTED_ASSET_MANIFEST_HASH",
    "EXPECTED_REGISTRATION_HASH",
    "EXPECTED_SPEC_HASH",
    "HOST_BINDING_CANDIDATES_HASH",
    "HOST_BINDING_PREREGISTRATION_HASH",
    "HOST_CANDIDATE_LOAD_ORDER",
    "HOST_JAVASCRIPT_ASSET_MANIFEST_HASH",
    "HOST_JAVASCRIPT_LOAD_ORDER_HASH",
    "PREDECESSOR_REGISTRATION_HASH",
    "PROTECTED_STYLESHEET_PATH",
    "PROTECTED_STYLESHEET_SHA256",
    "REGISTRATION_ID",
    "SCHEMA_VERSION",
    "SCRIPT_LOAD_ORDER",
    "SOURCE_CONTRACT",
    "STATIC_FINGERPRINT",
    "build_portfolio_correlation_admission_effective_budget_consumer_static_asset_registration_v2",
    "expected_portfolio_correlation_admission_effective_budget_consumer_static_asset_spec_v2",
    "verify_portfolio_correlation_admission_effective_budget_consumer_static_asset_registration_v2",
]
