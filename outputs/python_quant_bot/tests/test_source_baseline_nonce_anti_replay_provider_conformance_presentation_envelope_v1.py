from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from hashlib import sha256
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.application.anti_replay_registry_identity_preregistration_v1 import (
    build_anti_replay_registry_identity_preregistration_v1,
)
from exchange_terminal.application.anti_replay_registry_organization_identity_intake_preregistration_v1 import (
    build_anti_replay_registry_organization_identity_intake_preregistration_v1,
)
from exchange_terminal.application.anti_replay_registry_signer_source_trust_preregistration_v1 import (
    build_anti_replay_registry_signer_source_trust_preregistration_v1,
)
from exchange_terminal.application.source_baseline_nonce_anti_replay_namespace_preregistration_v1 import (
    build_source_baseline_nonce_anti_replay_namespace_preregistration_v1,
)
from exchange_terminal.application.source_baseline_nonce_anti_replay_provider_conformance_plan_v2 import (
    build_source_baseline_nonce_anti_replay_provider_conformance_plan_v2,
    build_source_baseline_nonce_anti_replay_provider_identity_binding_v2,
)
from exchange_terminal.application.source_baseline_nonce_anti_replay_provider_conformance_presentation_envelope_v1 import (
    DISPLAY_STATE,
    ORDERED_STAGES,
    PRESENTATION_STATUS,
    build_source_baseline_nonce_anti_replay_provider_conformance_presentation_envelope_v1,
    verify_source_baseline_nonce_anti_replay_provider_conformance_presentation_envelope_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


class SourceBaselineProviderConformancePresentationEnvelopeV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.kwargs = {
            "registry_id": "synthetic.presentation.registry.v2",
            "operator_identity_claim": "synthetic-presentation-operator-claim",
            "public_key_spki_sha256": sha256(
                b"synthetic-presentation-registry-spki"
            ).hexdigest(),
            "trust_domain": "synthetic.presentation.registry.test",
        }
        self.identity = build_anti_replay_registry_identity_preregistration_v1(
            **self.kwargs
        )
        self.intake = (
            build_anti_replay_registry_organization_identity_intake_preregistration_v1(
                self.identity, **self.kwargs
            )
        )
        self.source_trust = (
            build_anti_replay_registry_signer_source_trust_preregistration_v1(
                self.intake, self.identity, **self.kwargs
            )
        )
        self.namespace = (
            build_source_baseline_nonce_anti_replay_namespace_preregistration_v1()
        )
        self.binding = build_source_baseline_nonce_anti_replay_provider_identity_binding_v2(
            self.namespace,
            self.identity,
            self.intake,
            self.source_trust,
            **self.kwargs,
        )
        self.plan = build_source_baseline_nonce_anti_replay_provider_conformance_plan_v2(
            self.binding,
            self.namespace,
            self.identity,
            self.intake,
            self.source_trust,
            **self.kwargs,
        )
        self.envelope = self._build()

    def _build(self, **overrides: object) -> dict:
        values = {
            "conformance_plan_document": self.plan,
            "provider_identity_binding_document": self.binding,
            "namespace_preregistration_document": self.namespace,
            "identity_preregistration_document": self.identity,
            "organization_identity_intake_document": self.intake,
            "signer_source_trust_preregistration_document": self.source_trust,
            **self.kwargs,
        }
        values.update(overrides)
        return build_source_baseline_nonce_anti_replay_provider_conformance_presentation_envelope_v1(
            **values
        )

    def test_exact_source_builds_unmounted_neutral_envelope(self) -> None:
        self.assertEqual(self.envelope["presentation_status"], PRESENTATION_STATUS)
        self.assertEqual(self.envelope["display_tone"], "NEUTRAL")
        self.assertEqual(self.envelope["display_state"], DISPLAY_STATE)

    def test_axes_follow_source_gap_maturity_permission_order(self) -> None:
        self.assertEqual(
            [item["stage"] for item in self.envelope["axes"]],
            list(ORDERED_STAGES),
        )
        self.assertEqual(
            self.envelope["ordered_stage_contract"], list(ORDERED_STAGES)
        )

    def test_axis_states_are_bound_open_preregistered_and_blocked(self) -> None:
        self.assertEqual(
            [item["state"] for item in self.envelope["axes"]],
            ["BOUND", "OPEN", "PREREGISTERED_NOT_RUN", "BLOCKED"],
        )

    def test_summary_projects_counts_without_raw_cases(self) -> None:
        self.assertEqual(
            self.envelope["summary"],
            {
                "source_document_count": 6,
                "required_case_count": 14,
                "executed_case_count": 0,
                "passed_case_count": 0,
                "open_gap_count": 7,
            },
        )
        self.assertNotIn("cases", self.envelope)
        self.assertFalse(self.envelope["facts"]["raw_conformance_cases_embedded"])

    def test_lineage_contains_only_source_hashes(self) -> None:
        lineage = self.envelope["lineage"]
        self.assertEqual(
            lineage["provider_identity_binding_hash"],
            self.binding["provider_identity_binding_hash"],
        )
        self.assertEqual(
            lineage["conformance_plan_hash"], self.plan["conformance_plan_hash"]
        )
        self.assertTrue(all(isinstance(value, str) and len(value) == 64 for value in lineage.values()))

    def test_projection_contains_no_ready_or_profitability_language(self) -> None:
        serialized = json.dumps(self.envelope, sort_keys=True).upper()
        self.assertNotIn('"READY"', serialized)
        self.assertFalse(self.envelope["facts"]["profitability_proven"])

    def test_raw_identity_claims_are_redacted(self) -> None:
        serialized = json.dumps(self.envelope, sort_keys=True)
        self.assertNotIn(self.kwargs["registry_id"], serialized)
        self.assertNotIn(self.kwargs["operator_identity_claim"], serialized)
        self.assertNotIn(self.kwargs["trust_domain"], serialized)
        self.assertFalse(self.envelope["facts"]["raw_identity_material_embedded"])

    def test_all_authority_locks_remain_false(self) -> None:
        self.assertTrue(all(value is False for value in self.envelope["authority"].values()))

    def test_ui_http_and_current_remain_unmounted(self) -> None:
        facts = self.envelope["facts"]
        self.assertFalse(facts["http_registered"])
        self.assertFalse(facts["ui_mounted"])
        self.assertFalse(facts["current_activated"])

    def test_invalid_plan_returns_ordered_unknown_projection(self) -> None:
        tampered = deepcopy(self.plan)
        tampered["facts"]["executed_case_count"] = 14
        result = self._build(conformance_plan_document=tampered)
        self.assertEqual(result["display_state"], "UNKNOWN")
        self.assertEqual(
            [item["stage"] for item in result["axes"]], list(ORDERED_STAGES)
        )
        self.assertTrue(all(item["state"] == "UNKNOWN" for item in result["axes"]))

    def test_invalid_binding_returns_unknown_projection(self) -> None:
        tampered = deepcopy(self.binding)
        tampered["status"] = "PASS"
        result = self._build(provider_identity_binding_document=tampered)
        self.assertEqual(result["display_state"], "UNKNOWN")

    def test_resealed_plan_promotion_returns_unknown(self) -> None:
        promoted = deepcopy(self.plan)
        promoted["facts"]["provider_conformance_verified"] = True
        promoted.pop("conformance_plan_hash")
        promoted = seal_strict_canonical_document(promoted, "conformance_plan_hash")
        result = self._build(conformance_plan_document=promoted)
        self.assertEqual(result["display_state"], "UNKNOWN")

    def test_exact_verifier_accepts_rebuild(self) -> None:
        self.assertTrue(
            verify_source_baseline_nonce_anti_replay_provider_conformance_presentation_envelope_v1(
                self.envelope,
                self.plan,
                self.binding,
                self.namespace,
                self.identity,
                self.intake,
                self.source_trust,
                **self.kwargs,
            )
        )

    def test_envelope_promotion_fails_exact_verifier(self) -> None:
        promoted = deepcopy(self.envelope)
        promoted["facts"]["ui_mounted"] = True
        promoted.pop("presentation_envelope_hash")
        promoted = seal_strict_canonical_document(
            promoted, "presentation_envelope_hash"
        )
        self.assertFalse(
            verify_source_baseline_nonce_anti_replay_provider_conformance_presentation_envelope_v1(
                promoted,
                self.plan,
                self.binding,
                self.namespace,
                self.identity,
                self.intake,
                self.source_trust,
                **self.kwargs,
            )
        )

    def test_inputs_are_not_mutated(self) -> None:
        names = ("plan", "binding", "namespace", "identity", "intake", "source_trust")
        before = {name: deepcopy(getattr(self, name)) for name in names}
        self._build()
        self.assertEqual(before, {name: getattr(self, name) for name in names})

    def test_envelope_is_deterministic(self) -> None:
        self.assertEqual(self.envelope, self._build())


if __name__ == "__main__":
    unittest.main()
