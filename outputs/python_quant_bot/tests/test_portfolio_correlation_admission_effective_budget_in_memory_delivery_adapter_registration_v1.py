from __future__ import annotations

import copy
from hashlib import sha256
import json
from pathlib import Path
import unittest

from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1 as predecessor,
)
from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_in_memory_delivery_adapter_registration_v1 as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


ROOT = Path(__file__).resolve().parents[1]


class _DictSubclass(dict):
    pass


class PortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryAdapterRegistrationV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.registration = (
            subject.build_portfolio_correlation_admission_effective_budget_in_memory_delivery_adapter_registration_v1()
        )

    def test_registration_is_deterministic_and_exact(self) -> None:
        repeated = (
            subject.build_portfolio_correlation_admission_effective_budget_in_memory_delivery_adapter_registration_v1()
        )
        self.assertEqual(self.registration, repeated)
        self.assertTrue(
            subject.verify_portfolio_correlation_admission_effective_budget_in_memory_delivery_adapter_registration_v1(
                self.registration
            )
        )
        self.assertEqual(self.registration["status"], "BLOCKED")
        self.assertEqual(
            self.registration["registration_state"],
            "DUAL_RUNTIME_DELIVERY_ADAPTER_ASSETS_REGISTERED_UNBOUND",
        )

    def test_predecessor_registration_is_exact_and_transitively_pinned(self) -> None:
        base = (
            predecessor.build_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1()
        )
        self.assertTrue(
            predecessor.verify_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1(
                base
            )
        )
        contract = self.registration["predecessor_contract"]
        self.assertEqual(
            contract["registration_hash"],
            base["registration_hash"],
        )
        self.assertEqual(
            contract["registration_hash"],
            subject.PREDECESSOR_REGISTRATION_HASH,
        )
        self.assertEqual(
            contract["asset_manifest_hash"],
            base["asset_manifest_hash"],
        )

    def test_six_direct_adapter_assets_are_unique_and_hash_only(self) -> None:
        manifest = self.registration["asset_manifest"]
        self.assertEqual(len(manifest), 6)
        self.assertEqual(
            len({entry["asset_id"] for entry in manifest}),
            6,
        )
        self.assertEqual(
            self.registration["asset_manifest_hash"],
            subject.strict_canonical_hash(manifest),
        )
        for entry in manifest:
            self.assertEqual(len(entry["sha256"]), 64)
            self.assertNotIn("content", entry)

    def test_python_contract_pins_builder_verifier_and_exports(self) -> None:
        contract = self.registration["python_contract"]
        self.assertEqual(
            contract["schema_version"],
            subject.ENVELOPE_SCHEMA_VERSION,
        )
        self.assertEqual(contract["exports"], list(subject.PYTHON_EXPORTS))
        self.assertTrue(contract["builder"].startswith("build_"))
        self.assertTrue(contract["verifier"].startswith("verify_"))

    def test_javascript_contract_pins_global_exports_and_load_order(self) -> None:
        contract = self.registration["javascript_contract"]
        self.assertEqual(
            contract["browser_global"],
            subject.JAVASCRIPT_GLOBAL,
        )
        self.assertEqual(
            contract["exports"],
            list(subject.JAVASCRIPT_EXPORTS),
        )
        self.assertEqual(
            contract["relative_load_order"],
            list(subject.RELATIVE_LOAD_ORDER),
        )
        self.assertEqual(contract["module_format"], "UMD_COMMONJS")

    def test_presentation_and_transport_contracts_remain_unbound(self) -> None:
        presentation = self.registration["presentation_contract"]
        self.assertEqual(
            presentation["asset_registration_hash"],
            subject.PREDECESSOR_REGISTRATION_HASH,
        )
        self.assertFalse(presentation["ready_word_allowed"])
        self.assertFalse(presentation["raw_source_evidence_embedded"])
        transport = self.registration["transport_contract"]
        self.assertEqual(transport["mode"], "IN_MEMORY_ARGUMENT_ONLY")
        self.assertIsNone(transport["endpoint"])
        self.assertIsNone(transport["route"])
        self.assertIsNone(transport["host_slot"])

    def test_host_plan_authority_and_runtime_facts_remain_locked(self) -> None:
        self.assertTrue(
            all(value is None for value in self.registration["host_plan"].values())
        )
        self.assertTrue(
            all(value is False for value in self.registration["authority"].values())
        )
        facts = self.registration["facts"]
        self.assertFalse(facts["delivery_attempted"])
        self.assertFalse(facts["python_adapter_invoked"])
        self.assertFalse(facts["javascript_adapter_runtime_loaded"])
        self.assertFalse(facts["browser_executed"])
        self.assertFalse(facts["dom_mounted"])
        self.assertFalse(facts["current_activated"])
        self.assertFalse(facts["profitability_proven"])

    def test_resealed_predecessor_hash_drift_is_rejected(self) -> None:
        drifted = copy.deepcopy(self.registration)
        drifted["predecessor_contract"]["registration_hash"] = "0" * 64
        drifted = seal_strict_canonical_document(
            drifted,
            "adapter_registration_hash",
        )
        self.assertFalse(
            subject.verify_portfolio_correlation_admission_effective_budget_in_memory_delivery_adapter_registration_v1(
                drifted
            )
        )

    def test_resealed_adapter_hash_drift_is_rejected(self) -> None:
        drifted = copy.deepcopy(self.registration)
        drifted["asset_manifest"][0]["sha256"] = "0" * 64
        drifted["asset_manifest_hash"] = subject.strict_canonical_hash(
            drifted["asset_manifest"]
        )
        drifted = seal_strict_canonical_document(
            drifted,
            "adapter_registration_hash",
        )
        self.assertFalse(
            subject.verify_portfolio_correlation_admission_effective_budget_in_memory_delivery_adapter_registration_v1(
                drifted
            )
        )

    def test_resealed_load_order_drift_is_rejected(self) -> None:
        drifted = copy.deepcopy(self.registration)
        drifted["javascript_contract"]["relative_load_order"].reverse()
        drifted = seal_strict_canonical_document(
            drifted,
            "adapter_registration_hash",
        )
        self.assertFalse(
            subject.verify_portfolio_correlation_admission_effective_budget_in_memory_delivery_adapter_registration_v1(
                drifted
            )
        )

    def test_resealed_host_and_authority_promotions_are_rejected(self) -> None:
        variants = []
        host = copy.deepcopy(self.registration)
        host["host_plan"]["payload_source_provider"] = "forged"
        variants.append(host)
        authority = copy.deepcopy(self.registration)
        authority["authority"]["adapter_execution_allowed"] = True
        variants.append(authority)
        for variant in variants:
            with self.subTest(variant=variant["host_plan"]):
                variant = seal_strict_canonical_document(
                    variant,
                    "adapter_registration_hash",
                )
                self.assertFalse(
                    subject.verify_portfolio_correlation_admission_effective_budget_in_memory_delivery_adapter_registration_v1(
                        variant
                    )
                )

    def test_extra_field_is_rejected_even_when_resealed(self) -> None:
        drifted = copy.deepcopy(self.registration)
        drifted["unexpected"] = True
        drifted = seal_strict_canonical_document(
            drifted,
            "adapter_registration_hash",
        )
        self.assertFalse(
            subject.verify_portfolio_correlation_admission_effective_budget_in_memory_delivery_adapter_registration_v1(
                drifted
            )
        )

    def test_non_native_and_cyclic_documents_fail_closed(self) -> None:
        self.assertFalse(
            subject.verify_portfolio_correlation_admission_effective_budget_in_memory_delivery_adapter_registration_v1(
                _DictSubclass(self.registration)
            )
        )
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        self.assertFalse(
            subject.verify_portfolio_correlation_admission_effective_budget_in_memory_delivery_adapter_registration_v1(
                cyclic
            )
        )

    def test_direct_and_predecessor_files_match_pinned_hashes(self) -> None:
        expected = {
            entry["path"]: entry["sha256"]
            for entry in self.registration["asset_manifest"]
        }
        predecessor_contract = self.registration["predecessor_contract"]
        expected.update({
            predecessor_contract["implementation_path"]: (
                predecessor_contract["implementation_sha256"]
            ),
            predecessor_contract["test_path"]: predecessor_contract["test_sha256"],
            predecessor_contract["adr_path"]: predecessor_contract["adr_sha256"],
        })
        for path, digest in expected.items():
            with self.subTest(path=path):
                self.assertEqual(
                    sha256((ROOT / path).read_bytes()).hexdigest(),
                    digest,
                )

    def test_registration_contains_no_raw_evidence_or_permission_claim(self) -> None:
        encoded = json.dumps(self.registration, sort_keys=True)
        for forbidden in (
            '"positions":',
            '"symbol":',
            '"notional":',
            "synthetic-strategy",
            "synthetic-variant",
            "cluster_exposures",
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(
            self.registration["presentation_contract"][
                "raw_source_evidence_embedded"
            ]
        )


if __name__ == "__main__":
    unittest.main()
