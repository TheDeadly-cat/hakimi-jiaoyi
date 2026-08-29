from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_cross_runtime_consumer_parity_registration_v1 as subject,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = (
    ROOT
    / "tests/fixtures/"
    "portfolio_correlation_admission_effective_budget_cross_runtime_consumer_parity_registration_v1.json"
)


def _reseal(document: dict) -> dict:
    document.pop("parity_registration_hash", None)
    document["parity_registration_hash"] = subject.strict_canonical_hash(document)
    return document


class CrossRuntimeConsumerParityRegistrationV1Tests(unittest.TestCase):
    def build(self) -> dict:
        return subject.build_portfolio_correlation_admission_effective_budget_cross_runtime_consumer_parity_registration_v1()

    def verify(self, document: object) -> bool:
        return subject.verify_portfolio_correlation_admission_effective_budget_cross_runtime_consumer_parity_registration_v1(
            document
        )

    def test_exact_registration_is_deterministic_and_verifies(self) -> None:
        first = self.build()
        second = self.build()
        self.assertEqual(first, second)
        self.assertTrue(self.verify(first))
        core = dict(first)
        supplied = core.pop("parity_registration_hash")
        self.assertEqual(subject.strict_canonical_hash(core), supplied)

    def test_identity_and_state_are_frozen(self) -> None:
        document = self.build()
        self.assertEqual(document["schema_version"], subject.SCHEMA_VERSION)
        self.assertEqual(document["static_fingerprint"], subject.STATIC_FINGERPRINT)
        self.assertEqual(document["registration_id"], subject.REGISTRATION_ID)
        self.assertEqual(document["status"], "BLOCKED")
        self.assertEqual(
            document["registration_state"],
            "THREE_STATE_CROSS_RUNTIME_CONSUMER_PARITY_REGISTERED_UNBOUND",
        )

    def test_consumer_preregistration_contract_is_exact(self) -> None:
        contract = self.build()["consumer_preregistration"]
        self.assertEqual(
            contract["registration_hash"], subject.CONSUMER_PREREGISTRATION_HASH
        )
        self.assertEqual(
            contract["python_consumer_contract_hash"],
            subject.PYTHON_CONSUMER_CONTRACT_HASH,
        )
        self.assertEqual(
            contract["javascript_consumer_contract_hash"],
            subject.JAVASCRIPT_CONSUMER_CONTRACT_HASH,
        )
        self.assertFalse(contract["host_binding_required"])

    def test_two_ordered_consumers_and_pair_hash_are_exact(self) -> None:
        document = self.build()
        consumers = document["consumer_contracts"]
        self.assertEqual(
            [consumer["consumer_id"] for consumer in consumers],
            [subject.PYTHON_CONSUMER_ID, subject.JAVASCRIPT_CONSUMER_ID],
        )
        self.assertEqual(
            document["consumer_pair_hash"],
            subject.strict_canonical_hash(consumers),
        )
        self.assertTrue(all(consumer.get("host_binding") is None for consumer in consumers[:1]))
        self.assertTrue(
            all(
                consumers[1][key] is None
                for key in ("host_script", "host_stylesheet", "mount_slot")
            )
        )

    def test_three_state_matrix_and_hash_are_exact(self) -> None:
        document = self.build()
        matrix = document["parity_matrix"]
        self.assertEqual([row["state"] for row in matrix], list(subject.STATE_ORDER))
        self.assertEqual(
            document["parity_matrix_hash"], subject.strict_canonical_hash(matrix)
        )

    def test_known_state_is_exact_and_hash_only(self) -> None:
        known = self.build()["parity_matrix"][0]
        self.assertEqual(known["python_status"], "KNOWN")
        self.assertEqual(known["javascript_status"], "KNOWN")
        self.assertEqual(known["bridge_status_label"], "LOCAL ALIGNMENT")
        self.assertEqual(known["source_hash_policy"], "EXACT_64_HEX")
        for key in (
            "python_result_hash",
            "python_envelope_hash",
            "javascript_result_hash",
            "extraction_receipt_hash",
            "presentation_hash",
            "markup_hash",
        ):
            self.assertEqual(len(known[key]), 64)

    def test_unknown_state_preserves_uncertainty(self) -> None:
        unknown = self.build()["parity_matrix"][1]
        self.assertEqual(unknown["python_status"], "UNKNOWN")
        self.assertEqual(unknown["javascript_status"], "UNKNOWN")
        self.assertEqual(unknown["bridge_status_label"], "SOURCE UNKNOWN")
        self.assertEqual(unknown["source_hash_policy"], "ALL_NULL")

    def test_blocked_state_has_no_presentation(self) -> None:
        blocked = self.build()["parity_matrix"][2]
        self.assertEqual(blocked["python_status"], "BLOCKED")
        self.assertEqual(blocked["javascript_status"], "BLOCKED")
        for key in (
            "python_envelope_hash",
            "extraction_receipt_hash",
            "presentation_hash",
            "markup_hash",
            "bridge_status_label",
        ):
            self.assertIsNone(blocked[key])

    def test_known_and_unknown_markup_must_differ(self) -> None:
        matrix = self.build()["parity_matrix"]
        self.assertNotEqual(matrix[0]["markup_hash"], matrix[1]["markup_hash"])
        self.assertTrue(
            self.build()["parity_policy"]["known_unknown_markup_must_differ"]
        )

    def test_acceptance_contract_is_unbound(self) -> None:
        contract = self.build()["acceptance_contract"]
        self.assertEqual(contract["schema_version"], subject.ACCEPTANCE_SCHEMA_VERSION)
        self.assertEqual(
            contract["static_fingerprint"], subject.ACCEPTANCE_STATIC_FINGERPRINT
        )
        self.assertEqual(contract["output_mode"], "HASH_ONLY_ACCEPTANCE_RECEIPT")
        self.assertFalse(contract["raw_state_documents_embedded"])
        self.assertIsNone(contract["host_binding"])

    def test_activation_order_keeps_host_and_current_last(self) -> None:
        order = self.build()["activation_order"]
        self.assertLess(
            order.index("VERIFY_THREE_STATE_PARITY_ACCEPTANCE_RECEIPT"),
            order.index("DECLARE_HOST_BINDINGS_IN_SEPARATE_VERSION"),
        )
        self.assertEqual(
            order[-1], "CONSIDER_CURRENT_ONLY_BY_SEPARATE_EXPLICIT_DECISION"
        )

    def test_host_plan_and_authority_remain_locked(self) -> None:
        document = self.build()
        self.assertTrue(all(value is None for value in document["host_plan"].values()))
        self.assertTrue(
            all(value is False for value in document["authority"].values())
        )

    def test_generated_fixture_matches_builder_exactly(self) -> None:
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(fixture, self.build())
        self.assertTrue(self.verify(fixture))

    def test_resealed_consumer_source_drift_is_rejected(self) -> None:
        document = self.build()
        document["consumer_contracts"][1]["implementation_sha256"] = "0" * 64
        document["consumer_pair_hash"] = subject.strict_canonical_hash(
            document["consumer_contracts"]
        )
        self.assertFalse(self.verify(_reseal(document)))

    def test_resealed_parity_matrix_drift_is_rejected(self) -> None:
        document = self.build()
        document["parity_matrix"][0]["markup_hash"] = "1" * 64
        document["parity_matrix_hash"] = subject.strict_canonical_hash(
            document["parity_matrix"]
        )
        self.assertFalse(self.verify(_reseal(document)))

    def test_resealed_state_reordering_is_rejected(self) -> None:
        document = self.build()
        document["parity_matrix"].reverse()
        document["parity_matrix_hash"] = subject.strict_canonical_hash(
            document["parity_matrix"]
        )
        self.assertFalse(self.verify(_reseal(document)))

    def test_resealed_host_binding_and_authority_are_rejected(self) -> None:
        document = self.build()
        document["host_plan"]["route"] = "/api/parity"
        document["authority"]["acceptance_execution_allowed"] = True
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

    def test_predecessor_source_pins_match_current_files(self) -> None:
        expected = {
            (
                "exchange_terminal/services/"
                "portfolio_correlation_admission_effective_budget_hash_"
                "envelope_source_consumer_v1.py"
            ): subject.PYTHON_CONSUMER_IMPLEMENTATION_SHA256,
            (
                "tests/test_portfolio_correlation_admission_effective_budget_"
                "hash_envelope_source_consumer_v1.py"
            ): subject.PYTHON_CONSUMER_TEST_SHA256,
            (
                "docs/adr/0311-portfolio-correlation-admission-effective-"
                "budget-hash-envelope-source-consumer-v1.md"
            ): subject.PYTHON_CONSUMER_ADR_SHA256,
            (
                "exchange_terminal/static/"
                "evidence_portfolio_correlation_admission_effective_budget_"
                "inspection_consumer_v1.js"
            ): subject.JAVASCRIPT_CONSUMER_IMPLEMENTATION_SHA256,
            (
                "exchange_terminal/static/"
                "evidence_portfolio_correlation_admission_effective_budget_"
                "inspection_consumer_v1.test.js"
            ): subject.JAVASCRIPT_CONSUMER_TEST_SHA256,
            (
                "tests/fixtures/"
                "portfolio_correlation_admission_effective_budget_hash_"
                "envelope_source_consumer_v1.json"
            ): subject.JAVASCRIPT_CONSUMER_FIXTURE_SHA256,
            (
                "docs/adr/0312-portfolio-correlation-admission-effective-"
                "budget-inspection-consumer-v1.md"
            ): subject.JAVASCRIPT_CONSUMER_ADR_SHA256,
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
