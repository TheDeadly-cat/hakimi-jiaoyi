from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import inspect
import json
from pathlib import Path
import re
import unittest

from exchange_terminal.application import (
    genesis_replay_reservation_commitment_semantic_profile_quarantine_v1 as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import (
    test_genesis_replay_reservation_provider_registration_clock_trust_threshold_genesis_admission_v1 as genesis_fixture,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class NonNativeDocument(dict):
    pass


class GenesisCommitmentSemanticProfileQuarantineV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        fixture_class = (
            genesis_fixture.ClockTrustThresholdGenesisAdmissionV1Tests
        )
        self.fixture = fixture_class(
            "test_valid_threshold_signatures_are_local_pass_only"
        )
        self.fixture.setUp()
        self.commitment = self.fixture.commitment
        self.bundle = self.fixture.bundle
        self.quarantine = self._evaluate()

    def _verification_args(self):
        return (
            self.bundle["evidence"],
            self.bundle["signed"],
            self.fixture.claim,
            self.fixture.topology,
            self.fixture.plan,
        )

    def _verification_kwargs(self):
        return {
            "expected_verification_evidence_hash": self.bundle["evidence"][
                "verification_evidence_hash"
            ],
            "evaluation_kwargs": self.bundle["evaluation_kwargs"],
        }

    def _evaluate(self, commitment=None, expected_hash=None):
        commitment = self.commitment if commitment is None else commitment
        expected_hash = (
            self.commitment["genesis_commitment_hash"]
            if expected_hash is None
            else expected_hash
        )
        return subject.evaluate_genesis_replay_reservation_commitment_semantic_profile_quarantine_v1(
            commitment,
            *self._verification_args(),
            expected_genesis_commitment_hash=expected_hash,
            **self._verification_kwargs(),
        )

    def _verify(self, document, expected_quarantine_hash=None):
        expected_quarantine_hash = (
            document["semantic_quarantine_hash"]
            if expected_quarantine_hash is None
            else expected_quarantine_hash
        )
        return subject.verify_genesis_replay_reservation_commitment_semantic_profile_quarantine_v1(
            document,
            self.commitment,
            *self._verification_args(),
            expected_semantic_quarantine_hash=expected_quarantine_hash,
            expected_genesis_commitment_hash=self.commitment[
                "genesis_commitment_hash"
            ],
            **self._verification_kwargs(),
        )

    def test_exact_source_is_quarantined_block_not_interpreted(self) -> None:
        self.assertEqual(self.quarantine["status"], subject.STATUS_BLOCK)
        self.assertEqual(
            self.quarantine["decision"],
            subject.DECISION_DO_NOT_INTERPRET_OR_ACTIVATE,
        )
        self.assertTrue(
            self.quarantine["facts"]["source_commitment_exactly_verified"]
        )

    def test_candidate_profiles_are_explicit_and_none_is_selected(self) -> None:
        profiles = self.quarantine["semantic_profiles"]
        self.assertEqual(
            [item["profile_id"] for item in profiles["candidate_profiles"]],
            list(subject.SEMANTIC_PROFILE_CANDIDATES),
        )
        self.assertTrue(
            all(item["selected"] is False for item in profiles["candidate_profiles"])
        )
        self.assertEqual(
            profiles["profile_state"], subject.PROFILE_STATE_UNRESOLVED
        )
        self.assertIsNone(profiles["selected_profile_id"])
        self.assertIsNone(profiles["selected_profile_commitment_hash"])

    def test_out_of_band_hash_is_preserved_as_opaque_without_interpretation(self) -> None:
        self.assertEqual(
            self.quarantine["source"][
                "opaque_out_of_band_genesis_commitment_hash"
            ],
            self.commitment["binding"][
                "expected_out_of_band_genesis_commitment_hash"
            ],
        )
        self.assertTrue(
            self.quarantine["facts"][
                "opaque_hash_preserved_without_interpretation"
            ]
        )

    def test_all_source_blockers_and_quarantine_blockers_are_preserved(self) -> None:
        self.assertEqual(
            self.quarantine["source_blockers"], self.commitment["blockers"]
        )
        self.assertEqual(
            self.quarantine["blockers"],
            [*self.commitment["blockers"], *subject.QUARANTINE_BLOCKERS],
        )

    def test_profile_installation_current_and_trading_authority_are_locked(self) -> None:
        self.assertTrue(
            all(value is False for value in self.quarantine["authority"].values())
        )
        facts = self.quarantine["facts"]
        self.assertFalse(facts["semantic_profile_preregistered"])
        self.assertFalse(facts["semantic_profile_selected"])
        self.assertFalse(facts["profile_domain_separation_verified"])
        self.assertFalse(facts["genesis_commitment_installed"])
        self.assertFalse(facts["current_activated"])

    def test_exact_verifier_accepts_only_exact_quarantine(self) -> None:
        self.assertTrue(self._verify(self.quarantine))
        promoted = deepcopy(self.quarantine)
        promoted["semantic_profiles"]["selected_profile_id"] = (
            subject.SEMANTIC_PROFILE_CANDIDATES[0]
        )
        promoted["semantic_profiles"]["candidate_profiles"][0][
            "selected"
        ] = True
        promoted["authority"]["profile_interpretation_allowed"] = True
        promoted.pop("semantic_quarantine_hash")
        promoted = seal_strict_canonical_document(
            promoted, "semantic_quarantine_hash"
        )
        self.assertFalse(
            self._verify(promoted, promoted["semantic_quarantine_hash"])
        )

    def test_tampered_source_commitment_degrades_to_unknown_without_echo(self) -> None:
        tampered = deepcopy(self.commitment)
        tampered["binding"][
            "expected_out_of_band_genesis_commitment_hash"
        ] = "f" * 64
        tampered["private_locator"] = "must-not-echo"
        result = self._evaluate(tampered)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNone(
            result["source"]["opaque_out_of_band_genesis_commitment_hash"]
        )
        self.assertNotIn("must-not-echo", json.dumps(result, sort_keys=True))

    def test_invalid_expected_commitment_hash_degrades_to_unknown(self) -> None:
        result = self._evaluate(expected_hash="not-a-hash")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(
            result["decision"],
            subject.DECISION_DO_NOT_INTERPRET_OR_ACTIVATE,
        )
        self.assertTrue(
            all(value is False for value in result["authority"].values())
        )

    def test_adr0402_implementation_pin_matches_current_source(self) -> None:
        path = (
            PROJECT_ROOT
            / "exchange_terminal/application/genesis_replay_reservation_provider_registration_clock_trust_threshold_genesis_admission_v1.py"
        )
        self.assertEqual(
            sha256(path.read_bytes()).hexdigest(),
            subject.ADR0402_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(
            self.quarantine["source"]["adr0402_implementation_sha256"],
            subject.ADR0402_IMPLEMENTATION_SHA256,
        )

    def test_public_evaluator_has_no_profile_selection_or_authority_parameter(self) -> None:
        signature = inspect.signature(
            subject.evaluate_genesis_replay_reservation_commitment_semantic_profile_quarantine_v1
        )
        forbidden_fragments = ("profile", "select", "override", "authorize")
        parameter_names = tuple(signature.parameters)
        self.assertTrue(
            all(
                not any(fragment in name for fragment in forbidden_fragments)
                for name in parameter_names
            )
        )

    def test_non_native_cyclic_and_extra_quarantines_fail_verification(self) -> None:
        self.assertFalse(
            subject.verify_genesis_replay_reservation_commitment_semantic_profile_quarantine_v1(
                NonNativeDocument(self.quarantine),
                self.commitment,
                *self._verification_args(),
                expected_semantic_quarantine_hash=self.quarantine[
                    "semantic_quarantine_hash"
                ],
                expected_genesis_commitment_hash=self.commitment[
                    "genesis_commitment_hash"
                ],
                **self._verification_kwargs(),
            )
        )
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        self.assertFalse(
            subject.verify_genesis_replay_reservation_commitment_semantic_profile_quarantine_v1(
                cyclic,
                self.commitment,
                *self._verification_args(),
                expected_semantic_quarantine_hash=self.quarantine[
                    "semantic_quarantine_hash"
                ],
                expected_genesis_commitment_hash=self.commitment[
                    "genesis_commitment_hash"
                ],
                **self._verification_kwargs(),
            )
        )
        extra = deepcopy(self.quarantine)
        extra["compatibility_alias"] = True
        self.assertFalse(self._verify(extra))

    def test_projection_is_bounded_and_contains_no_raw_source_documents(self) -> None:
        serialized = json.dumps(self.quarantine, sort_keys=True)
        self.assertFalse(
            self.quarantine["facts"]["raw_source_commitment_embedded"]
        )
        self.assertFalse(self.quarantine["facts"]["raw_evidence_embedded"])
        self.assertNotIn("signatures", serialized)
        self.assertNotIn("public_key", serialized)
        self.assertNotIn("topology", serialized)
        self.assertNotIn("plan_document", serialized)

    def test_projection_contains_no_promotional_or_directional_wording(self) -> None:
        serialized = json.dumps(self.quarantine, sort_keys=True)
        forbidden = re.compile(
            r"\b(?:READY|PROFIT|RETURN|BUY|SELL)\b", re.IGNORECASE
        )
        self.assertIsNone(forbidden.search(serialized))

    def test_evaluation_is_deterministic_and_does_not_mutate_source(self) -> None:
        before = deepcopy(self.commitment)
        second = self._evaluate()
        self.assertEqual(self.quarantine, second)
        self.assertEqual(self.commitment, before)


if __name__ == "__main__":
    unittest.main()
