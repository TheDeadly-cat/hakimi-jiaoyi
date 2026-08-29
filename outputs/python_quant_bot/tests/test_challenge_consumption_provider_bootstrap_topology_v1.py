from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import unittest

from exchange_terminal.application import (
    challenge_consumption_provider_bootstrap_topology_v1 as bootstrap,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider_preregistration_v1 as preregistration,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


class ChallengeConsumptionProviderBootstrapTopologyV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider_kwargs = {
            "registry_id": "synthetic.challenge.consumption.registry.v1",
            "operator_identity_claim": "synthetic.candidate.operator.v1",
            "public_key_spki_sha256": _hash("candidate-provider-key"),
            "trust_domain": "synthetic.candidate-domain",
            "provider_implementation_claim_sha256": _hash(
                "candidate-provider-implementation"
            ),
        }
        self.provider = (
            preregistration.build_challenge_consumption_provider_preregistration_v1(
                **self.provider_kwargs
            )
        )
        self.root_authorities = [
            {
                "authority_id": "synthetic.root.charlie.v1",
                "public_key_spki_sha256": _hash("root-key-charlie"),
                "trust_domain": "synthetic.root-domain-charlie",
                "governance_implementation_claim_sha256": _hash(
                    "root-governance-charlie"
                ),
            },
            {
                "authority_id": "synthetic.root.alpha.v1",
                "public_key_spki_sha256": _hash("root-key-alpha"),
                "trust_domain": "synthetic.root-domain-alpha",
                "governance_implementation_claim_sha256": _hash(
                    "root-governance-alpha"
                ),
            },
            {
                "authority_id": "synthetic.root.bravo.v1",
                "public_key_spki_sha256": _hash("root-key-bravo"),
                "trust_domain": "synthetic.root-domain-bravo",
                "governance_implementation_claim_sha256": _hash(
                    "root-governance-bravo"
                ),
            },
        ]
        self.build_kwargs = {
            "root_authorities": self.root_authorities,
            "minimum_root_signatures": 2,
            "provider_preregistration_kwargs": self.provider_kwargs,
        }
        self.topology = (
            bootstrap.build_challenge_consumption_provider_bootstrap_topology_v1(
                self.provider, **self.build_kwargs
            )
        )
        self.plan = (
            bootstrap.build_challenge_consumption_provider_genesis_admission_plan_v1(
                self.topology,
                self.provider,
                **self.build_kwargs,
            )
        )

    def test_topology_is_deterministic_non_circular_and_blocked(self) -> None:
        rebuilt = (
            bootstrap.build_challenge_consumption_provider_bootstrap_topology_v1(
                self.provider, **self.build_kwargs
            )
        )
        self.assertEqual(rebuilt, self.topology)
        self.assertEqual(rebuilt["status"], "BLOCKED")
        self.assertTrue(
            rebuilt["facts"]["bootstrap_topology_structurally_non_circular"]
        )
        self.assertFalse(rebuilt["facts"]["external_root_governance_verified"])
        self.assertFalse(rebuilt["facts"]["provider_registered"])
        self.assertTrue(all(value is False for value in rebuilt["authority"].values()))

    def test_root_authority_order_is_canonical(self) -> None:
        reversed_topology = (
            bootstrap.build_challenge_consumption_provider_bootstrap_topology_v1(
                self.provider,
                **{
                    **self.build_kwargs,
                    "root_authorities": list(reversed(self.root_authorities)),
                },
            )
        )
        self.assertEqual(reversed_topology, self.topology)
        ids = [
            item["authority_id"]
            for item in self.topology["bootstrap_root"]["root_authority_set"][
                "authorities"
            ]
        ]
        self.assertEqual(ids, sorted(ids))

    def test_candidate_provider_key_cannot_be_a_root_key(self) -> None:
        roots = deepcopy(self.root_authorities)
        roots[0]["public_key_spki_sha256"] = self.provider_kwargs[
            "public_key_spki_sha256"
        ]
        with self.assertRaisesRegex(
            bootstrap.ChallengeConsumptionProviderBootstrapTopologyError,
            "candidate provider key",
        ):
            bootstrap.build_challenge_consumption_provider_bootstrap_topology_v1(
                self.provider,
                **{**self.build_kwargs, "root_authorities": roots},
            )

    def test_candidate_operator_cannot_be_a_root_authority(self) -> None:
        roots = deepcopy(self.root_authorities)
        roots[0]["authority_id"] = self.provider_kwargs[
            "operator_identity_claim"
        ]
        with self.assertRaisesRegex(
            bootstrap.ChallengeConsumptionProviderBootstrapTopologyError,
            "candidate operator",
        ):
            bootstrap.build_challenge_consumption_provider_bootstrap_topology_v1(
                self.provider,
                **{**self.build_kwargs, "root_authorities": roots},
            )

    def test_candidate_trust_domain_cannot_be_a_root_domain(self) -> None:
        roots = deepcopy(self.root_authorities)
        roots[0]["trust_domain"] = self.provider_kwargs["trust_domain"]
        with self.assertRaisesRegex(
            bootstrap.ChallengeConsumptionProviderBootstrapTopologyError,
            "candidate trust domain",
        ):
            bootstrap.build_challenge_consumption_provider_bootstrap_topology_v1(
                self.provider,
                **{**self.build_kwargs, "root_authorities": roots},
            )

    def test_duplicate_root_identity_key_or_domain_is_rejected(self) -> None:
        for field in (
            "authority_id",
            "public_key_spki_sha256",
            "trust_domain",
        ):
            roots = deepcopy(self.root_authorities)
            roots[1][field] = roots[0][field]
            with self.subTest(field=field), self.assertRaises(
                bootstrap.ChallengeConsumptionProviderBootstrapTopologyError
            ):
                bootstrap.build_challenge_consumption_provider_bootstrap_topology_v1(
                    self.provider,
                    **{**self.build_kwargs, "root_authorities": roots},
                )

    def test_threshold_requires_integer_bounds_and_strict_majority(self) -> None:
        for roots, threshold in (
            (self.root_authorities, True),
            (self.root_authorities, 1),
            (self.root_authorities, 4),
            (
                [
                    *self.root_authorities,
                    {
                        "authority_id": "synthetic.root.delta.v1",
                        "public_key_spki_sha256": _hash("root-key-delta"),
                        "trust_domain": "synthetic.root-domain-delta",
                        "governance_implementation_claim_sha256": _hash(
                            "root-governance-delta"
                        ),
                    },
                ],
                2,
            ),
        ):
            with self.subTest(threshold=threshold), self.assertRaises(
                bootstrap.ChallengeConsumptionProviderBootstrapTopologyError
            ):
                bootstrap.build_challenge_consumption_provider_bootstrap_topology_v1(
                    self.provider,
                    root_authorities=roots,
                    minimum_root_signatures=threshold,
                    provider_preregistration_kwargs=self.provider_kwargs,
                )

    def test_root_authority_count_is_bounded(self) -> None:
        with self.assertRaises(
            bootstrap.ChallengeConsumptionProviderBootstrapTopologyError
        ):
            bootstrap.build_challenge_consumption_provider_bootstrap_topology_v1(
                self.provider,
                root_authorities=self.root_authorities[:1],
                minimum_root_signatures=1,
                provider_preregistration_kwargs=self.provider_kwargs,
            )
        too_many = [
            {
                "authority_id": f"synthetic.root.{index}.v1",
                "public_key_spki_sha256": _hash(f"root-key-{index}"),
                "trust_domain": f"synthetic.root-domain-{index}",
                "governance_implementation_claim_sha256": _hash(
                    f"root-governance-{index}"
                ),
            }
            for index in range(8)
        ]
        with self.assertRaises(
            bootstrap.ChallengeConsumptionProviderBootstrapTopologyError
        ):
            bootstrap.build_challenge_consumption_provider_bootstrap_topology_v1(
                self.provider,
                root_authorities=too_many,
                minimum_root_signatures=5,
                provider_preregistration_kwargs=self.provider_kwargs,
            )

    def test_provider_preregistration_drift_is_rejected(self) -> None:
        drifted = deepcopy(self.provider)
        drifted["status"] = "PASS"
        with self.assertRaisesRegex(
            bootstrap.ChallengeConsumptionProviderBootstrapTopologyError,
            "not exact",
        ):
            bootstrap.build_challenge_consumption_provider_bootstrap_topology_v1(
                drifted, **self.build_kwargs
            )

    def test_public_verifier_rebuilds_and_rejects_promotion(self) -> None:
        self.assertTrue(
            bootstrap.verify_challenge_consumption_provider_bootstrap_topology_v1(
                self.topology,
                self.provider,
                expected_bootstrap_topology_hash=self.topology[
                    "bootstrap_topology_hash"
                ],
                **self.build_kwargs,
            )
        )
        forged = deepcopy(self.topology)
        forged.pop("bootstrap_topology_hash")
        forged["facts"]["external_root_governance_verified"] = True
        forged = seal_strict_canonical_document(
            forged, "bootstrap_topology_hash"
        )
        self.assertFalse(
            bootstrap.verify_challenge_consumption_provider_bootstrap_topology_v1(
                forged,
                self.provider,
                expected_bootstrap_topology_hash=forged[
                    "bootstrap_topology_hash"
                ],
                **self.build_kwargs,
            )
        )

    def test_plan_freezes_twelve_unexecuted_external_cases(self) -> None:
        self.assertEqual(self.plan["summary"]["planned_case_count"], 12)
        self.assertEqual(self.plan["summary"]["executed_case_count"], 0)
        self.assertFalse(self.plan["summary"]["runtime_mutations"])
        self.assertTrue(all(case["executed"] is False for case in self.plan["cases"]))
        self.assertTrue(all(case["observed"] is None for case in self.plan["cases"]))
        self.assertTrue(
            bootstrap.verify_challenge_consumption_provider_genesis_admission_plan_v1(
                self.plan,
                self.topology,
                self.provider,
                expected_genesis_admission_plan_hash=self.plan[
                    "genesis_admission_plan_hash"
                ],
                **self.build_kwargs,
            )
        )

    def test_plan_rejects_topology_mutation(self) -> None:
        mutated = deepcopy(self.topology)
        mutated["status"] = "PASS"
        with self.assertRaisesRegex(
            bootstrap.ChallengeConsumptionProviderBootstrapTopologyError,
            "not exact",
        ):
            bootstrap.build_challenge_consumption_provider_genesis_admission_plan_v1(
                mutated,
                self.provider,
                **self.build_kwargs,
            )

    def test_hash_only_topology_redacts_key_material_and_preserves_inputs(self) -> None:
        before = deepcopy(self.root_authorities)
        encoded = json.dumps(self.topology, sort_keys=True)
        self.assertNotIn("public_key_spki_base64", encoded)
        self.assertNotIn("signature_base64", encoded)
        self.assertEqual(before, self.root_authorities)
        changed = deepcopy(self.root_authorities)
        changed[0]["public_key_spki_sha256"] = _hash("changed-root-key")
        changed_topology = (
            bootstrap.build_challenge_consumption_provider_bootstrap_topology_v1(
                self.provider,
                **{**self.build_kwargs, "root_authorities": changed},
            )
        )
        self.assertNotEqual(
            changed_topology["bootstrap_topology_hash"],
            self.topology["bootstrap_topology_hash"],
        )

    def test_production_has_no_private_key_io_provider_or_runtime(self) -> None:
        source = Path(bootstrap.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "Ed25519PrivateKey",
            "private_key",
            ".consume_once(",
            "open(",
            "Path(",
            "socket",
            "subprocess",
            "runtime/",
            "time.time",
            "datetime.now",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
