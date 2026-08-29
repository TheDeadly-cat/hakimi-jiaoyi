from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import unittest

from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_preregistration_v1
    as contract,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


ROOT = Path(__file__).resolve().parents[1]


class ReplayCursorProviderPreregistrationV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.kwargs = {
            "registry_id": "synthetic.replay-cursor.registry.v1",
            "operator_identity_claim": "synthetic-independent-provider-operator",
            "public_key_spki_sha256": sha256(
                b"synthetic-replay-cursor-provider-key"
            ).hexdigest(),
            "trust_domain": "synthetic.replay-cursor.provider.test",
            "provider_implementation_claim_sha256": sha256(
                b"synthetic-provider-implementation-claim"
            ).hexdigest(),
        }
        cls.preregistration = contract.build_replay_cursor_provider_preregistration_v1(
            **cls.kwargs
        )
        cls.plan = contract.build_replay_cursor_provider_conformance_plan_v1(
            cls.preregistration,
            **cls.kwargs,
        )

    def test_preregistration_is_exact_but_operationally_blocked(self) -> None:
        result = contract.verify_replay_cursor_provider_preregistration_v1(
            self.preregistration,
            **self.kwargs,
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["preregistration_status"], "BLOCKED")
        self.assertFalse(result["provider_identity_verified"])
        self.assertFalse(result["provider_key_possession_verified"])
        self.assertFalse(result["external_provider_conformance_verified"])
        self.assertFalse(result["current_activation_allowed"])

    def test_preregistration_has_no_endpoint_key_material_or_authority(self) -> None:
        serialized = repr(self.preregistration).lower()
        self.assertNotIn("private_key", serialized)
        self.assertNotIn("endpoint", self.preregistration["identity"])
        self.assertNotIn("secret", serialized)
        self.assertEqual(self.preregistration["status"], "BLOCKED")
        self.assertTrue(
            all(value is False for value in self.preregistration["authority"].values())
        )

    def test_identity_or_implementation_claim_changes_hash(self) -> None:
        for field, value in (
            ("registry_id", "synthetic.replay-cursor.registry.v2"),
            ("provider_implementation_claim_sha256", "0" * 64),
        ):
            with self.subTest(field=field):
                changed = dict(self.kwargs)
                changed[field] = value
                other = contract.build_replay_cursor_provider_preregistration_v1(
                    **changed
                )
                self.assertNotEqual(
                    self.preregistration["preregistration_hash"],
                    other["preregistration_hash"],
                )

    def test_invalid_identity_and_cross_port_aliases_fail_closed(self) -> None:
        invalid = (
            ("registry_id", "UPPERCASE"),
            ("registry_id", "x"),
            ("public_key_spki_sha256", "0" * 63),
            ("trust_domain", "contains space"),
            ("operator_identity_claim", ""),
            ("provider_implementation_claim_sha256", "not-a-hash"),
            ("provider_protocol_version", "anti-replay-compare-and-consume-port-v1"),
        )
        for field, value in invalid:
            with self.subTest(field=field):
                kwargs = dict(self.kwargs)
                kwargs[field] = value
                with self.assertRaises(ValueError):
                    contract.build_replay_cursor_provider_preregistration_v1(
                        **kwargs
                    )

    def test_tamper_and_resealed_schema_alias_do_not_verify(self) -> None:
        tampered = deepcopy(self.preregistration)
        tampered["facts"]["provider_identity_verified"] = True
        self.assertEqual(
            contract.verify_replay_cursor_provider_preregistration_v1(
                tampered,
                **self.kwargs,
            )["status"],
            "BLOCK",
        )
        alias_body = deepcopy(self.preregistration)
        alias_body.pop("preregistration_hash")
        alias_body["schema_version"] = (
            f"{contract.PREREGISTRATION_SCHEMA_VERSION}.0"
        )
        alias = seal_strict_canonical_document(
            alias_body,
            "preregistration_hash",
        )
        self.assertEqual(
            contract.verify_replay_cursor_provider_preregistration_v1(
                alias,
                **self.kwargs,
            )["status"],
            "BLOCK",
        )

    def test_requirements_are_unique_and_keep_external_gaps_explicit(self) -> None:
        requirements = self.preregistration["requirements"]
        self.assertEqual(len(requirements), 11)
        self.assertEqual(len(set(requirements)), 11)
        self.assertIn("ATOMIC_COMPARE_AND_ADVANCE", requirements)
        self.assertIn("DURABLE_RESTART_RECOVERY", requirements)
        self.assertIn("INDEPENDENT_CONFORMANCE_OBSERVER", requirements)
        self.assertFalse(
            self.preregistration["facts"][
                "durable_atomic_compare_and_advance_verified"
            ]
        )

    def test_conformance_plan_preregisters_eleven_unexecuted_cases(self) -> None:
        self.assertEqual(len(self.plan["cases"]), 11)
        self.assertEqual(len({case["case_id"] for case in self.plan["cases"]}), 11)
        self.assertTrue(
            all(case["requires_external_provider"] for case in self.plan["cases"])
        )
        self.assertTrue(
            all(
                case["requires_independent_observer"]
                for case in self.plan["cases"]
            )
        )
        self.assertEqual(self.plan["status"], "BLOCKED")
        self.assertFalse(self.plan["facts"]["conformance_cases_executed"])

    def test_exact_plan_pass_grants_no_authority(self) -> None:
        result = contract.verify_replay_cursor_provider_conformance_plan_v1(
            self.plan,
            self.preregistration,
            **self.kwargs,
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["plan_status"], "BLOCKED")
        self.assertFalse(result["external_provider_conformance_verified"])
        self.assertFalse(result["conformance_cases_executed"])
        self.assertFalse(result["provider_identity_verified"])
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])
        self.assertFalse(result["writer_allowed"])

    def test_plan_tampering_fails_exact_rebuild(self) -> None:
        tampered = deepcopy(self.plan)
        tampered["cases"][0]["requires_external_provider"] = False
        result = contract.verify_replay_cursor_provider_conformance_plan_v1(
            tampered,
            self.preregistration,
            **self.kwargs,
        )
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["plan_status"], "UNKNOWN")
        self.assertFalse(result["signed_provider_receipt_verified"])

    def test_dependency_pins_match_current_source_files(self) -> None:
        paths = {
            contract.PROVIDER_INTERFACE_IMPLEMENTATION_SHA256: (
                ROOT
                / "exchange_terminal"
                / "application"
                / "ports"
                / "strategy_correlation_incumbent_snapshot_replay_cursor_provider_v1.py"
            ),
            contract.CAS_IMPLEMENTATION_SHA256: (
                ROOT
                / "exchange_terminal"
                / "application"
                / "strategy_correlation_incumbent_snapshot_replay_cursor_cas_transition_v1.py"
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

    def test_production_contract_has_no_io_runtime_or_provider_invocation(self) -> None:
        source = Path(contract.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "open(",
            "subprocess",
            "requests.",
            "urllib.",
            "socket.",
            "sqlite3",
            "compare_and_advance(",
            "register_route(",
            "write_current_pointer(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
