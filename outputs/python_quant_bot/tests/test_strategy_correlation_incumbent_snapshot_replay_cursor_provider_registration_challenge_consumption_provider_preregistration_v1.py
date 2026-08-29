from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest

from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider_preregistration_v1 as preregistration,
)


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


class ChallengeConsumptionProviderPreregistrationV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.kwargs = {
            "registry_id": "synthetic.challenge.consumption.registry.v1",
            "operator_identity_claim": "synthetic.challenge.operator.v1",
            "public_key_spki_sha256": _hash("synthetic-provider-spki"),
            "trust_domain": "synthetic.test-only",
            "provider_implementation_claim_sha256": _hash(
                "synthetic-provider-implementation"
            ),
        }
        self.document = preregistration.build_challenge_consumption_provider_preregistration_v1(
            **self.kwargs
        )
        self.plan = preregistration.build_challenge_consumption_provider_conformance_plan_v1(
            self.document, **self.kwargs
        )

    def test_preregistration_is_exact_deterministic_and_blocked(self) -> None:
        rebuilt = preregistration.build_challenge_consumption_provider_preregistration_v1(
            **self.kwargs
        )
        self.assertEqual(rebuilt, self.document)
        self.assertEqual(rebuilt["status"], "BLOCKED")
        self.assertTrue(
            preregistration.verify_challenge_consumption_provider_preregistration_v1(
                rebuilt, **self.kwargs
            )
        )

    def test_preregistration_redacts_raw_key_and_grants_no_authority(self) -> None:
        encoded = json.dumps(self.document, sort_keys=True)
        self.assertNotIn("public_key_spki_base64", encoded)
        self.assertTrue(all(value is False for value in self.document["authority"].values()))
        self.assertFalse(self.document["facts"]["provider_registered"])
        self.assertFalse(self.document["facts"]["provider_key_possession_verified"])

    def test_preregistration_verifier_rejects_shape_and_semantic_drift(self) -> None:
        mutated = deepcopy(self.document)
        mutated["facts"]["provider_registered"] = True
        self.assertFalse(
            preregistration.verify_challenge_consumption_provider_preregistration_v1(
                mutated, **self.kwargs
            )
        )
        mutated = deepcopy(self.document)
        mutated["unexpected"] = False
        self.assertFalse(
            preregistration.verify_challenge_consumption_provider_preregistration_v1(
                mutated, **self.kwargs
            )
        )

    def test_invalid_identity_hash_and_protocol_alias_are_rejected(self) -> None:
        for overrides in (
            {"registry_id": "UPPER"},
            {"public_key_spki_sha256": "not-a-hash"},
            {"provider_protocol_version": preregistration.PROVIDER_PROTOCOL_VERSION + "-alias"},
        ):
            with self.assertRaises(
                preregistration.ChallengeConsumptionProviderPreregistrationError
            ):
                preregistration.build_challenge_consumption_provider_preregistration_v1(
                    **{**self.kwargs, **overrides}
                )

    def test_source_pins_specialized_namespace_schemas_and_implementations(self) -> None:
        source = self.document["source"]
        self.assertIn("registration-challenge-v1", source["registry_namespace"])
        self.assertIn("consume-once-command-v1", source["consume_once_command_schema_version"])
        self.assertIn("consume-once-result-v1", source["consume_once_result_schema_version"])
        self.assertEqual(
            source["consumption_port_implementation_sha256"],
            preregistration.CONSUMPTION_PORT_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(
            source["command_binding_implementation_sha256"],
            preregistration.COMMAND_BINDING_IMPLEMENTATION_SHA256,
        )

    def test_requirement_set_covers_external_safety_properties(self) -> None:
        required = set(self.document["requirements"])
        for name in (
            "ATOMIC_CONSUME_ONCE",
            "DUPLICATE_BEFORE_CONFLICT",
            "DURABLE_RESTART_RECOVERY",
            "ROLLBACK_RESISTANCE",
            "LINEARIZABLE_READ_AFTER_WRITE",
            "SIGNED_CONSUMPTION_RECEIPT_V1",
        ):
            self.assertIn(name, required)

    def test_conformance_plan_freezes_thirteen_unexecuted_cases(self) -> None:
        self.assertEqual(self.plan["summary"]["planned_case_count"], 13)
        self.assertEqual(self.plan["summary"]["executed_case_count"], 0)
        self.assertEqual(len(self.plan["cases"]), 13)
        self.assertTrue(all(case["executed"] is False for case in self.plan["cases"]))
        self.assertTrue(all(case["observed"] is None for case in self.plan["cases"]))
        self.assertFalse(self.plan["summary"]["runtime_mutations"])

    def test_conformance_cases_are_unique_and_cover_concurrency_recovery(self) -> None:
        names = [case["name"] for case in self.plan["cases"]]
        self.assertEqual(len(names), len(set(names)))
        joined = " ".join(names)
        for token in ("concurrency", "restart", "rollback", "timeout", "linearizable"):
            self.assertIn(token, joined)

    def test_conformance_plan_exact_verifier_rejects_mutation(self) -> None:
        self.assertTrue(
            preregistration.verify_challenge_consumption_provider_conformance_plan_v1(
                self.plan, self.document, **self.kwargs
            )
        )
        mutated = deepcopy(self.plan)
        mutated["cases"][0]["executed"] = True
        mutated["summary"]["executed_case_count"] = 1
        self.assertFalse(
            preregistration.verify_challenge_consumption_provider_conformance_plan_v1(
                mutated, self.document, **self.kwargs
            )
        )

    def test_preregistration_drift_cannot_build_plan(self) -> None:
        drifted = deepcopy(self.document)
        drifted["status"] = "PASS"
        with self.assertRaises(
            preregistration.ChallengeConsumptionProviderPreregistrationError
        ):
            preregistration.build_challenge_consumption_provider_conformance_plan_v1(
                drifted, **self.kwargs
            )

    def test_builders_are_deterministic_and_do_not_mutate_inputs(self) -> None:
        before = deepcopy(self.kwargs)
        first = preregistration.build_challenge_consumption_provider_conformance_plan_v1(
            self.document, **self.kwargs
        )
        second = preregistration.build_challenge_consumption_provider_conformance_plan_v1(
            self.document, **self.kwargs
        )
        self.assertEqual(first, second)
        self.assertEqual(before, self.kwargs)

    def test_implementation_pins_match_current_source_files(self) -> None:
        root = Path(__file__).resolve().parents[1]
        port_path = root / "exchange_terminal" / "application" / "ports" / (
            "strategy_correlation_incumbent_snapshot_replay_cursor_provider_"
            "registration_challenge_consumption_provider_v1.py"
        )
        binding_path = root / "exchange_terminal" / "application" / (
            "strategy_correlation_incumbent_snapshot_replay_cursor_provider_"
            "registration_challenge_consumption_command_binding_v1.py"
        )
        self.assertEqual(
            sha256(port_path.read_bytes()).hexdigest(),
            preregistration.CONSUMPTION_PORT_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(
            sha256(binding_path.read_bytes()).hexdigest(),
            preregistration.COMMAND_BINDING_IMPLEMENTATION_SHA256,
        )

    def test_production_module_has_no_private_key_provider_io_or_runtime(self) -> None:
        source = Path(preregistration.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "Ed25519PrivateKey",
            "private_key",
            ".consume_once(",
            "open(",
            "Path(",
            "socket",
            "subprocess",
            "runtime/",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
