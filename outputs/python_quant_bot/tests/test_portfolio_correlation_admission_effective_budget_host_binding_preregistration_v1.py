from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_cross_runtime_consumer_parity_registration_v1 as predecessor,
)
from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1 as subject,
)


ROOT = Path(__file__).resolve().parents[1]


def _reseal(document: dict) -> dict:
    document.pop("host_binding_preregistration_hash", None)
    document["host_binding_preregistration_hash"] = subject.strict_canonical_hash(
        document
    )
    return document


class HostBindingPreregistrationV1Tests(unittest.TestCase):
    def build(self) -> dict:
        return subject.build_portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1()

    def verify(self, document: object) -> bool:
        return subject.verify_portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1(
            document
        )

    def test_exact_document_is_deterministic_and_verifies(self) -> None:
        first = self.build()
        second = self.build()
        self.assertEqual(first, second)
        self.assertTrue(self.verify(first))
        core = dict(first)
        supplied = core.pop("host_binding_preregistration_hash")
        self.assertEqual(subject.strict_canonical_hash(core), supplied)

    def test_identity_and_state_are_frozen(self) -> None:
        document = self.build()
        self.assertEqual(document["schema_version"], subject.SCHEMA_VERSION)
        self.assertEqual(document["static_fingerprint"], subject.STATIC_FINGERPRINT)
        self.assertEqual(document["preregistration_id"], subject.PREREGISTRATION_ID)
        self.assertEqual(document["status"], "BLOCKED")
        self.assertEqual(
            document["registration_state"],
            "HOST_BINDING_CANDIDATES_PREREGISTERED_ALL_ACTIVE_SLOTS_NULL",
        )

    def test_predecessor_contract_and_acceptance_are_exact(self) -> None:
        document = self.build()
        predecessor_contract = document["predecessor_contract"]
        acceptance = document["required_acceptance"]
        self.assertEqual(
            predecessor_contract["parity_registration_hash"],
            subject.PARITY_REGISTRATION_HASH,
        )
        self.assertEqual(
            predecessor_contract["parity_matrix_hash"],
            subject.PARITY_MATRIX_HASH,
        )
        self.assertEqual(
            acceptance["acceptance_receipt_hash"],
            subject.ACCEPTANCE_RECEIPT_HASH,
        )
        self.assertEqual(acceptance["status"], "EXACT")
        self.assertIsNone(acceptance["receipt_binding"])
        self.assertFalse(acceptance["verified_by_host"])

    def test_python_provider_candidate_is_internal_and_unbound(self) -> None:
        provider = self.build()["binding_candidates"]["python_provider"]
        self.assertEqual(provider["input_mode"], "INTERNAL_EXACT_SOURCE_CHAIN_ONLY")
        self.assertEqual(
            provider["output_schema_version"], subject.PYTHON_RESULT_SCHEMA_VERSION
        )
        self.assertIsNone(provider["active_import"])
        self.assertIsNone(provider["provider_registration"])
        self.assertFalse(provider["bound"])

    def test_http_projection_is_readonly_hash_result_only(self) -> None:
        projection = self.build()["binding_candidates"]["http_projection"]
        self.assertEqual(projection["input_source"], "INTERNAL_PROVIDER_RESULT_ONLY")
        self.assertFalse(projection["raw_source_inputs_allowed"])
        self.assertIsNone(projection["handler"])
        self.assertIsNone(projection["route"])
        self.assertIsNone(projection["endpoint"])
        self.assertFalse(projection["bound"])

    def test_javascript_asset_order_and_hashes_are_frozen(self) -> None:
        candidate = self.build()["binding_candidates"]["javascript_assets"]
        assets = candidate["assets"]
        self.assertEqual(len(assets), 5)
        self.assertEqual(candidate["load_order"], [asset["path"] for asset in assets])
        self.assertEqual(
            candidate["asset_manifest_hash"], subject.strict_canonical_hash(assets)
        )
        self.assertEqual(
            candidate["load_order_hash"],
            subject.strict_canonical_hash(candidate["load_order"]),
        )
        self.assertTrue(all(asset["script_binding"] is None for asset in assets))
        self.assertIsNone(candidate["runtime_loader"])
        self.assertFalse(candidate["bound"])

    def test_stylesheet_candidate_preserves_protected_styles(self) -> None:
        stylesheet = self.build()["binding_candidates"]["stylesheet"]
        self.assertEqual(
            stylesheet["isolated_sha256"], subject.BRIDGE_STYLESHEET_SHA256
        )
        self.assertEqual(
            stylesheet["protected_stylesheet_sha256"],
            subject.PROTECTED_STYLESHEET_SHA256,
        )
        self.assertFalse(stylesheet["protected_stylesheet_mutation_allowed"])
        self.assertIsNone(stylesheet["link_binding"])
        self.assertFalse(stylesheet["bound"])

    def test_mount_candidate_has_symbolic_id_but_no_selector(self) -> None:
        mount = self.build()["binding_candidates"]["mount"]
        self.assertEqual(
            mount["slot_contract_id"], "correlation-inspection-bridge-slot-v1"
        )
        self.assertEqual(
            mount["input_schema_version"], subject.JAVASCRIPT_RESULT_SCHEMA_VERSION
        )
        self.assertIsNone(mount["selector"])
        self.assertIsNone(mount["mount_function"])
        self.assertIsNone(mount["browser_review_receipt"])
        self.assertFalse(mount["bound"])

    def test_binding_candidates_hash_is_exact(self) -> None:
        document = self.build()
        self.assertEqual(
            document["binding_candidates_hash"],
            subject.strict_canonical_hash(document["binding_candidates"]),
        )

    def test_active_host_plan_is_entirely_null(self) -> None:
        plan = self.build()["active_host_plan"]
        self.assertTrue(plan)
        self.assertTrue(all(value is None for value in plan.values()))

    def test_activation_order_keeps_bindings_and_current_late(self) -> None:
        order = self.build()["activation_order"]
        self.assertLess(
            order.index("VERIFY_ADR0314_HOST_BINDING_PREREGISTRATION"),
            order.index("IMPLEMENT_PYTHON_PROVIDER_BINDING_IN_SEPARATE_VERSION"),
        )
        self.assertLess(
            order.index("IMPLEMENT_JAVASCRIPT_HOST_LOADING_IN_SEPARATE_VERSION"),
            order.index("RUN_AUTHORIZED_BROWSER_REVIEW_BEFORE_ANY_MOUNT"),
        )
        self.assertEqual(
            order[-1], "CONSIDER_CURRENT_ONLY_BY_SEPARATE_EXPLICIT_DECISION"
        )

    def test_authority_remains_entirely_false(self) -> None:
        authority = self.build()["authority"]
        self.assertTrue(authority)
        self.assertTrue(all(value is False for value in authority.values()))

    def test_resealed_predecessor_builder_drift_fails_closed(self) -> None:
        drifted = predecessor.build_portfolio_correlation_admission_effective_budget_cross_runtime_consumer_parity_registration_v1()
        drifted["registration_id"] = "drifted"
        drifted.pop("parity_registration_hash")
        drifted["parity_registration_hash"] = predecessor.strict_canonical_hash(
            drifted
        )
        with patch.object(subject, "build_parity_registration_v1", return_value=drifted):
            with self.assertRaises(ValueError):
                self.build()

    def test_resealed_acceptance_hash_drift_is_rejected(self) -> None:
        document = self.build()
        document["required_acceptance"]["acceptance_receipt_hash"] = "0" * 64
        self.assertFalse(self.verify(_reseal(document)))

    def test_fully_resealed_asset_and_order_drift_are_rejected(self) -> None:
        document = self.build()
        assets = document["binding_candidates"]["javascript_assets"]
        assets["assets"][0]["sha256"] = "1" * 64
        assets["asset_manifest_hash"] = subject.strict_canonical_hash(assets["assets"])
        assets["load_order"].reverse()
        assets["load_order_hash"] = subject.strict_canonical_hash(assets["load_order"])
        document["binding_candidates_hash"] = subject.strict_canonical_hash(
            document["binding_candidates"]
        )
        self.assertFalse(self.verify(_reseal(document)))

    def test_resealed_script_route_and_mount_bindings_are_rejected(self) -> None:
        document = self.build()
        candidates = document["binding_candidates"]
        candidates["javascript_assets"]["assets"][0]["script_binding"] = "script#x"
        candidates["http_projection"]["route"] = "/api/correlation"
        candidates["mount"]["selector"] = "#correlation"
        document["binding_candidates_hash"] = subject.strict_canonical_hash(candidates)
        self.assertFalse(self.verify(_reseal(document)))

    def test_resealed_active_host_plan_and_authority_are_rejected(self) -> None:
        document = self.build()
        document["active_host_plan"]["route"] = "/api/correlation"
        document["authority"]["route_registration_allowed"] = True
        self.assertFalse(self.verify(_reseal(document)))

    def test_resealed_extra_field_is_rejected(self) -> None:
        document = self.build()
        document["extension"] = {"enabled": False}
        self.assertFalse(self.verify(_reseal(document)))

    def test_non_native_and_cyclic_documents_are_rejected(self) -> None:
        self.assertFalse(self.verify({"value": object()}))
        self.assertFalse(self.verify({"value": ("tuple",)}))
        cyclic: dict = {}
        cyclic["cycle"] = cyclic
        self.assertFalse(self.verify(cyclic))

    def test_all_pinned_candidate_and_predecessor_files_match(self) -> None:
        expected = {
            (
                "exchange_terminal/services/"
                "portfolio_correlation_admission_effective_budget_cross_"
                "runtime_consumer_parity_registration_v1.py"
            ): subject.PARITY_IMPLEMENTATION_SHA256,
            (
                "tests/test_portfolio_correlation_admission_effective_budget_"
                "cross_runtime_consumer_parity_registration_v1.py"
            ): subject.PARITY_TEST_SHA256,
            (
                "tests/fixtures/"
                "portfolio_correlation_admission_effective_budget_cross_"
                "runtime_consumer_parity_registration_v1.json"
            ): subject.PARITY_FIXTURE_SHA256,
            (
                "exchange_terminal/static/"
                "evidence_portfolio_correlation_admission_effective_budget_"
                "cross_runtime_consumer_parity_acceptance_v1.js"
            ): subject.ACCEPTANCE_IMPLEMENTATION_SHA256,
            (
                "exchange_terminal/static/"
                "evidence_portfolio_correlation_admission_effective_budget_"
                "cross_runtime_consumer_parity_acceptance_v1.test.js"
            ): subject.ACCEPTANCE_TEST_SHA256,
            (
                "docs/adr/0313-portfolio-correlation-admission-effective-"
                "budget-cross-runtime-consumer-parity-v1.md"
            ): subject.PARITY_ADR_SHA256,
            (
                "exchange_terminal/services/"
                "portfolio_correlation_admission_effective_budget_hash_"
                "envelope_source_consumer_v1.py"
            ): subject.PYTHON_PROVIDER_SHA256,
            "exchange_terminal/static/strict_canonical_json_v1.js": subject.STRICT_CANONICAL_JAVASCRIPT_SHA256,
            (
                "exchange_terminal/static/"
                "evidence_portfolio_correlation_admission_effective_budget_"
                "in_memory_delivery_v1.js"
            ): subject.DELIVERY_JAVASCRIPT_SHA256,
            (
                "exchange_terminal/static/"
                "evidence_portfolio_correlation_admission_effective_budget_"
                "bridge_v1.js"
            ): subject.BRIDGE_JAVASCRIPT_SHA256,
            (
                "exchange_terminal/static/"
                "evidence_portfolio_correlation_admission_effective_budget_"
                "bridge_v1.css"
            ): subject.BRIDGE_STYLESHEET_SHA256,
            (
                "exchange_terminal/static/"
                "evidence_portfolio_correlation_admission_effective_budget_"
                "inspection_consumer_v1.js"
            ): subject.INSPECTION_CONSUMER_JAVASCRIPT_SHA256,
            "exchange_terminal/static/styles.css": subject.PROTECTED_STYLESHEET_SHA256,
        }
        for relative_path, expected_hash in expected.items():
            with self.subTest(relative_path=relative_path):
                actual = hashlib.sha256(
                    (ROOT / relative_path).read_bytes()
                ).hexdigest()
                self.assertEqual(actual, expected_hash)

    def test_production_module_has_no_io_or_host_capability(self) -> None:
        source = Path(subject.__file__).read_text(encoding="utf-8")
        for token in (
            "import requests",
            "import socket",
            "urllib.",
            "subprocess.",
            "open(",
            "Path(",
            "os.environ",
            "sqlite3",
            "flask",
            "fastapi",
        ):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
