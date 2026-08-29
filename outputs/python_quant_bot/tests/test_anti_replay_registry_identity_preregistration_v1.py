from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import unittest

from exchange_terminal.application import (
    anti_replay_registry_identity_preregistration_v1 as contract,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


ROOT = Path(__file__).resolve().parents[1]


class AntiReplayRegistryIdentityPreregistrationV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.kwargs = {
            "registry_id": "synthetic.registry.v1",
            "operator_identity_claim": "synthetic-independent-operator-claim",
            "public_key_spki_sha256": sha256(b"synthetic-registry-key").hexdigest(),
            "trust_domain": "synthetic.registry.test",
        }
        cls.preregistration = (
            contract.build_anti_replay_registry_identity_preregistration_v1(
                **cls.kwargs
            )
        )
        cls.plan = contract.build_anti_replay_registry_adapter_conformance_plan_v1(
            cls.preregistration,
            **cls.kwargs,
        )

    def test_preregistration_is_exact_and_blocked(self) -> None:
        verification = (
            contract.verify_anti_replay_registry_identity_preregistration_v1(
                self.preregistration,
                **self.kwargs,
            )
        )
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["preregistration_status"], "BLOCKED")
        self.assertFalse(verification["registry_identity_verified"])
        self.assertFalse(verification["external_linearizability_verified"])
        self.assertFalse(verification["target_consumption_receipt_issued"])

    def test_preregistration_has_no_endpoint_private_key_or_authority(self) -> None:
        serialized = repr(self.preregistration).lower()
        self.assertNotIn("private_key", serialized)
        self.assertNotIn("endpoint", self.preregistration["identity"])
        self.assertNotIn("secret", serialized)
        self.assertTrue(all(value is False for value in self.preregistration["authority"].values()))
        self.assertEqual(self.preregistration["status"], "BLOCKED")

    def test_identity_change_changes_preregistration_hash(self) -> None:
        changed = dict(self.kwargs)
        changed["registry_id"] = "synthetic.registry.v2"
        other = contract.build_anti_replay_registry_identity_preregistration_v1(
            **changed
        )
        self.assertNotEqual(
            self.preregistration["preregistration_hash"],
            other["preregistration_hash"],
        )

    def test_invalid_identity_fields_fail_closed(self) -> None:
        invalid = (
            ("registry_id", "UPPERCASE"),
            ("registry_id", "x"),
            ("public_key_spki_sha256", "0" * 63),
            ("trust_domain", "contains space"),
            ("operator_identity_claim", ""),
            ("adapter_protocol_version", f"{contract.ADAPTER_PROTOCOL_VERSION}.0"),
        )
        for field, value in invalid:
            with self.subTest(field=field, value=value):
                kwargs = dict(self.kwargs)
                kwargs[field] = value
                with self.assertRaises(ValueError):
                    contract.build_anti_replay_registry_identity_preregistration_v1(
                        **kwargs
                    )

    def test_tamper_and_resealed_schema_alias_do_not_verify(self) -> None:
        tampered = deepcopy(self.preregistration)
        tampered["facts"]["registry_key_possession_verified"] = True
        self.assertEqual(
            contract.verify_anti_replay_registry_identity_preregistration_v1(
                tampered,
                **self.kwargs,
            )["status"],
            "BLOCK",
        )
        alias_body = deepcopy(self.preregistration)
        alias_body.pop("preregistration_hash")
        alias_body["schema_version"] = f"{contract.PREREGISTRATION_SCHEMA_VERSION}.0"
        alias = seal_strict_canonical_document(alias_body, "preregistration_hash")
        self.assertEqual(
            contract.verify_anti_replay_registry_identity_preregistration_v1(
                alias,
                **self.kwargs,
            )["status"],
            "BLOCK",
        )

    def test_conformance_plan_preregisters_ten_external_cases(self) -> None:
        self.assertEqual(len(self.plan["cases"]), 10)
        self.assertEqual(len({case["case_id"] for case in self.plan["cases"]}), 10)
        self.assertTrue(
            all(case["requires_external_runtime"] for case in self.plan["cases"])
        )
        self.assertTrue(
            all(case["requires_independent_observer"] for case in self.plan["cases"])
        )
        self.assertEqual(self.plan["status"], "BLOCKED")
        self.assertFalse(self.plan["facts"]["conformance_cases_executed"])

    def test_conformance_plan_exact_pass_grants_no_authority(self) -> None:
        exact = contract.verify_anti_replay_registry_adapter_conformance_plan_v1(
            self.plan,
            self.preregistration,
            **self.kwargs,
        )
        self.assertEqual(exact["status"], "PASS")
        self.assertEqual(exact["plan_status"], "BLOCKED")
        self.assertFalse(exact["adapter_conformance_verified"])
        self.assertFalse(exact["conformance_cases_executed"])
        self.assertFalse(exact["current_admission_allowed"])
        self.assertFalse(exact["paper_authorized"])
        self.assertFalse(exact["live_order_allowed"])
        self.assertFalse(exact["writer_allowed"])

    def test_plan_tampering_fails_exact_rebuild(self) -> None:
        tampered = deepcopy(self.plan)
        tampered["cases"][0]["requires_external_runtime"] = False
        exact = contract.verify_anti_replay_registry_adapter_conformance_plan_v1(
            tampered,
            self.preregistration,
            **self.kwargs,
        )
        self.assertEqual(exact["status"], "BLOCK")
        self.assertEqual(exact["plan_status"], "UNKNOWN")
        self.assertFalse(exact["target_consumption_receipt_issued"])

    def test_source_dependency_pins_are_current(self) -> None:
        paths = {
            contract.REFERENCE_MODEL_IMPLEMENTATION_SHA256: (
                ROOT
                / "exchange_terminal"
                / "static"
                / "evidence_portfolio_risk_post_registration_anti_replay_consumption_reference_v1.js"
            ),
            contract.STRICT_CANONICAL_IMPLEMENTATION_SHA256: (
                ROOT
                / "exchange_terminal"
                / "services"
                / "strict_canonical_json_hash.py"
            ),
        }
        for expected, path in paths.items():
            with self.subTest(path=str(path)):
                self.assertEqual(sha256(path.read_bytes()).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()
