from __future__ import annotations

import base64
import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.application import (
    genesis_replay_reservation_provider_registration_clock_trust_bootstrap_topology_v1 as contract,
)
from exchange_terminal.services import trusted_clock_authority_v3 as clock


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _raw(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )


def _spki(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


class ClockTrustBootstrapTopologyV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock_private = [
            Ed25519PrivateKey.generate(),
            Ed25519PrivateKey.generate(),
        ]
        self.clock_raw = [_raw(key) for key in self.clock_private]
        self.clock_authorities = [
            {
                "authority_id": "clock.bootstrap.a.v1",
                "key_id": "clock.bootstrap.a.key.v1",
                "public_key_base64": _b64(self.clock_raw[0]),
            },
            {
                "authority_id": "clock.bootstrap.b.v1",
                "key_id": "clock.bootstrap.b.key.v1",
                "public_key_base64": _b64(self.clock_raw[1]),
            },
        ]
        self.clock_registration = (
            clock.build_trusted_clock_authority_registration_v3(
                self.clock_authorities,
                minimum_sources=2,
                max_receipt_age_ms=5_000,
                max_provider_spread_ms=100,
                max_local_skew_ms=1_000,
                max_receipt_issue_delay_ms=100,
                valid_from_ms=1_001_000,
                valid_until_ms=1_100_000,
                declared_at_ms=1_000_000,
            )
        )
        self.clock_public_keys = {
            item["authority_id"]: item["public_key_base64"]
            for item in self.clock_authorities
        }

        self.time_source_private = Ed25519PrivateKey.generate()
        self.time_source_spki = _spki(self.time_source_private)
        self.time_source_kwargs = {
            "source_id": "synthetic.verification.time.source.v1",
            "key_id": "synthetic.verification.time.key.v1",
            "public_key_spki_sha256": sha256(
                self.time_source_spki
            ).hexdigest(),
            "trust_domain": "synthetic.test-only",
            "implementation_claim_sha256": _hash(
                "synthetic-verification-time-source"
            ),
            "monotonic_epoch_namespace": (
                "synthetic.verification.time.epoch.v1"
            ),
        }
        self.time_source = (
            contract.build_verification_time_source_preregistration_v1(
                **self.time_source_kwargs
            )
        )

        self.root_private = [
            Ed25519PrivateKey.generate(),
            Ed25519PrivateKey.generate(),
            Ed25519PrivateKey.generate(),
        ]
        self.root_spki = [_spki(key) for key in self.root_private]
        self.roots = [
            {
                "authority_id": f"clock.root.{label}.v1",
                "key_id": f"clock.root.{label}.key.v1",
                "organization_claim": f"synthetic.org.{label}.v1",
                "public_key_spki_sha256": sha256(spki).hexdigest(),
            }
            for label, spki in zip(("a", "b", "c"), self.root_spki)
        ]
        self.topology_kwargs = {
            "clock_registration_document": self.clock_registration,
            "clock_public_keys_by_id": self.clock_public_keys,
            "expected_clock_registration_hash": self.clock_registration[
                "registration_hash"
            ],
            "verification_time_source_preregistration_document": (
                self.time_source
            ),
            "verification_time_source_preregistration_kwargs": (
                self.time_source_kwargs
            ),
            "root_authorities": self.roots,
            "minimum_root_signatures": 2,
            "governance_domain": "synthetic.clock.governance.v1",
            "genesis_policy_hash": _hash("synthetic-clock-genesis-policy"),
        }
        self.topology = contract.build_clock_trust_bootstrap_topology_v1(
            **self.topology_kwargs
        )
        self.plan_kwargs = {
            "expected_topology_hash": self.topology["topology_hash"],
            "topology_build_kwargs": self.topology_kwargs,
            "ceremony_id_hash": _hash("synthetic-clock-ceremony"),
            "admission_nonce_hash": _hash("synthetic-clock-admission-nonce"),
        }
        self.plan = contract.build_clock_trust_genesis_admission_plan_v1(
            self.topology, **self.plan_kwargs
        )

    def test_time_source_preregistration_is_exact_blocked_and_redacted(self) -> None:
        self.assertEqual(self.time_source["status"], "BLOCKED")
        self.assertTrue(
            self.time_source["facts"]["local_preregistration_complete"]
        )
        self.assertFalse(
            self.time_source["facts"]["verification_time_source_trusted"]
        )
        self.assertTrue(
            all(value is False for value in self.time_source["authority"].values())
        )
        self.assertTrue(
            contract.verify_verification_time_source_preregistration_v1(
                self.time_source, **self.time_source_kwargs
            )
        )
        self.assertNotIn(
            _b64(self.time_source_spki),
            json.dumps(self.time_source, sort_keys=True),
        )

    def test_topology_is_exact_acyclic_and_all_authority_false(self) -> None:
        self.assertEqual(self.topology["status"], "BLOCKED")
        for name in (
            "clock_registration_exact",
            "clock_registered_public_key_hashes_exact",
            "verification_time_source_preregistration_exact",
            "root_authority_set_preregistered",
            "root_key_separation_enforced",
            "bootstrap_dependency_cycle_absent",
            "offline_threshold_genesis_required",
        ):
            self.assertTrue(self.topology["facts"][name], name)
        for name in (
            "root_signatures_verified",
            "root_identities_verified",
            "clock_registration_governance_verified",
            "verification_time_source_trusted",
            "trusted_current_time_established",
            "challenge_freshness_verified",
        ):
            self.assertFalse(self.topology["facts"][name], name)
        self.assertTrue(
            all(value is False for value in self.topology["authority"].values())
        )
        self.assertTrue(
            contract.verify_clock_trust_bootstrap_topology_v1(
                self.topology,
                expected_topology_hash=self.topology["topology_hash"],
                **self.topology_kwargs,
            )
        )

    def test_plan_is_unexecuted_exact_and_has_no_time_dependency(self) -> None:
        self.assertEqual(self.plan["status"], "BLOCKED")
        self.assertTrue(self.plan["facts"]["plan_only"])
        self.assertFalse(self.plan["facts"]["ceremony_executed"])
        self.assertFalse(self.plan["facts"]["threshold_verified"])
        self.assertFalse(self.plan["facts"]["trusted_current_time_established"])
        self.assertFalse(self.plan["facts"]["runtime_mutations"])
        self.assertIn(
            "NO_CURRENT_TIME_DEPENDENCY_AT_GENESIS",
            self.plan["required_checks"],
        )
        self.assertTrue(
            contract.verify_clock_trust_genesis_admission_plan_v1(
                self.plan,
                self.topology,
                expected_plan_hash=self.plan["plan_hash"],
                **self.plan_kwargs,
            )
        )

    def test_clock_registration_tamper_and_expected_hash_drift_fail(self) -> None:
        tampered = deepcopy(self.topology_kwargs)
        tampered["clock_registration_document"]["policy"][
            "minimum_sources"
        ] = 1
        with self.assertRaises(contract.ClockTrustBootstrapTopologyError):
            contract.build_clock_trust_bootstrap_topology_v1(**tampered)
        drift = deepcopy(self.topology_kwargs)
        drift["expected_clock_registration_hash"] = "0" * 64
        with self.assertRaises(contract.ClockTrustBootstrapTopologyError):
            contract.build_clock_trust_bootstrap_topology_v1(**drift)

    def test_clock_public_key_mismatch_fails(self) -> None:
        drift = deepcopy(self.topology_kwargs)
        drift["clock_public_keys_by_id"][
            self.clock_authorities[0]["authority_id"]
        ] = _b64(b"x" * 32)
        with self.assertRaises(contract.ClockTrustBootstrapTopologyError):
            contract.build_clock_trust_bootstrap_topology_v1(**drift)

    def test_root_identity_key_and_organization_duplicates_fail(self) -> None:
        fields = (
            "authority_id",
            "key_id",
            "organization_claim",
            "public_key_spki_sha256",
        )
        for field in fields:
            drift = deepcopy(self.topology_kwargs)
            drift["root_authorities"][1][field] = drift["root_authorities"][0][
                field
            ]
            with self.subTest(field=field):
                with self.assertRaises(
                    contract.ClockTrustBootstrapTopologyError
                ):
                    contract.build_clock_trust_bootstrap_topology_v1(**drift)

    def test_root_key_must_not_overlap_clock_authority(self) -> None:
        drift = deepcopy(self.topology_kwargs)
        drift["root_authorities"][0]["public_key_spki_sha256"] = (
            self.clock_registration["authorities"][0]["public_key_sha256"]
        )
        with self.assertRaises(contract.ClockTrustBootstrapTopologyError):
            contract.build_clock_trust_bootstrap_topology_v1(**drift)

    def test_root_key_must_not_overlap_time_source(self) -> None:
        drift = deepcopy(self.topology_kwargs)
        drift["root_authorities"][0]["public_key_spki_sha256"] = (
            self.time_source_kwargs["public_key_spki_sha256"]
        )
        with self.assertRaises(contract.ClockTrustBootstrapTopologyError):
            contract.build_clock_trust_bootstrap_topology_v1(**drift)

    def test_threshold_bool_low_and_high_fail(self) -> None:
        for value in (True, 1, 4):
            drift = deepcopy(self.topology_kwargs)
            drift["minimum_root_signatures"] = value
            with self.subTest(value=value):
                with self.assertRaises(
                    contract.ClockTrustBootstrapTopologyError
                ):
                    contract.build_clock_trust_bootstrap_topology_v1(**drift)

    def test_time_source_preregistration_drift_and_extra_fields_fail(self) -> None:
        drift = deepcopy(self.topology_kwargs)
        drift["verification_time_source_preregistration_document"]["facts"][
            "verification_time_source_trusted"
        ] = True
        with self.assertRaises(contract.ClockTrustBootstrapTopologyError):
            contract.build_clock_trust_bootstrap_topology_v1(**drift)
        extra = deepcopy(self.topology_kwargs)
        extra["verification_time_source_preregistration_kwargs"][
            "unexpected"
        ] = "forbidden"
        with self.assertRaises(contract.ClockTrustBootstrapTopologyError):
            contract.build_clock_trust_bootstrap_topology_v1(**extra)

    def test_plan_rejects_same_identifiers_and_topology_drift(self) -> None:
        same = deepcopy(self.plan_kwargs)
        same["admission_nonce_hash"] = same["ceremony_id_hash"]
        with self.assertRaises(contract.ClockTrustBootstrapTopologyError):
            contract.build_clock_trust_genesis_admission_plan_v1(
                self.topology, **same
            )
        topology = deepcopy(self.topology)
        topology["facts"]["clock_registration_governance_verified"] = True
        with self.assertRaises(contract.ClockTrustBootstrapTopologyError):
            contract.build_clock_trust_genesis_admission_plan_v1(
                topology, **self.plan_kwargs
            )

    def test_public_verifiers_rebuild_and_reject_mutations(self) -> None:
        prereg = deepcopy(self.time_source)
        prereg["facts"]["verification_time_source_trusted"] = True
        self.assertFalse(
            contract.verify_verification_time_source_preregistration_v1(
                prereg, **self.time_source_kwargs
            )
        )
        topology = deepcopy(self.topology)
        topology["facts"]["trusted_current_time_established"] = True
        self.assertFalse(
            contract.verify_clock_trust_bootstrap_topology_v1(
                topology,
                expected_topology_hash=self.topology["topology_hash"],
                **self.topology_kwargs,
            )
        )
        plan = deepcopy(self.plan)
        plan["authority"]["current_activation_allowed"] = True
        self.assertFalse(
            contract.verify_clock_trust_genesis_admission_plan_v1(
                plan,
                self.topology,
                expected_plan_hash=self.plan["plan_hash"],
                **self.plan_kwargs,
            )
        )

    def test_outputs_are_deterministic_redacted_and_inputs_immutable(self) -> None:
        before = deepcopy(
            [
                self.clock_registration,
                self.clock_public_keys,
                self.time_source,
                self.time_source_kwargs,
                self.roots,
            ]
        )
        rebuilt = contract.build_clock_trust_bootstrap_topology_v1(
            **self.topology_kwargs
        )
        self.assertEqual(self.topology, rebuilt)
        encoded = json.dumps(
            [self.time_source, self.topology, self.plan], sort_keys=True
        )
        for raw_key in self.clock_public_keys.values():
            self.assertNotIn(raw_key, encoded)
        self.assertNotIn(_b64(self.time_source_spki), encoded)
        for spki in self.root_spki:
            self.assertNotIn(_b64(spki), encoded)
        self.assertEqual(
            before,
            [
                self.clock_registration,
                self.clock_public_keys,
                self.time_source,
                self.time_source_kwargs,
                self.roots,
            ],
        )

    def test_production_has_no_private_key_io_system_clock_runtime_or_consumer_import(self) -> None:
        source = Path(contract.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "Ed25519PrivateKey",
            "private_key",
            "open(",
            "Path(",
            "socket",
            "subprocess",
            "time.time",
            "datetime.now",
            "runtime/",
            ".consume_once(",
            "genesis_replay_reservation_provider_registration_clock_binding_v1 as",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
