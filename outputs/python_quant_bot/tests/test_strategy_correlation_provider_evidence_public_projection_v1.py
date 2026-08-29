from __future__ import annotations

import copy
import json
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_provider_evidence_public_projection_v1 as subject,
)


class StrategyCorrelationProviderEvidencePublicProjectionV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.protocol_summary = {
            "schema_version": "synthetic-protocol-summary-v1",
            "source": {"status": "OBSERVED"},
            "private_protocol_marker": "protocol-secret",
        }
        self.provider_replay_gate = {
            "schema_version": "synthetic-provider-replay-gate-v1",
            "status": "SYNTHETIC",
            "provider_key_id": "provider-key-secret",
            "merkle_path": ["merkle-secret"],
        }
        self.protocol_context = {"trusted_protocol_root": "protocol-root-secret"}
        self.replay_context = {"trusted_registry_key": "registry-key-secret"}

    def _build(
        self,
        *,
        protocol_status: str = "PASS",
        replay_status: str = "PASS",
    ) -> dict:
        with patch.object(
            subject,
            "verify_protocol_summary",
            return_value={"status": protocol_status, "blockers": []},
        ), patch.object(
            subject,
            "verify_provider_replay_gate",
            return_value={"status": replay_status, "blockers": []},
        ):
            return subject.build_strategy_correlation_provider_evidence_public_projection_v1(
                self.protocol_summary,
                self.provider_replay_gate,
                protocol_verification_context=self.protocol_context,
                provider_replay_verification_context=self.replay_context,
            )

    def test_verified_sources_are_observed_without_projecting_gate_outcome(self) -> None:
        document = self._build()

        self.assertEqual(document["source"]["status"], "OBSERVED")
        self.assertEqual(
            document["source"]["provider_dataset_key_lifecycle_replay_gate"],
            "VERIFIED",
        )
        self.assertFalse(document["source"]["semantic_gate_outcome_projected"])
        self.assertEqual(document["maturity"]["status"], "UNKNOWN")
        self.assertFalse(document["claims"]["provider_gate_outcome_proven"])
        self.assertEqual(document["activation"]["status"], "INACTIVE_CANDIDATE")

    def test_projection_redacts_documents_and_verification_contexts(self) -> None:
        serialized = json.dumps(self._build(), sort_keys=True)

        for secret in (
            "protocol-secret",
            "provider-key-secret",
            "merkle-secret",
            "protocol-root-secret",
            "registry-key-secret",
        ):
            self.assertNotIn(secret, serialized)
        self.assertTrue(all(value is False for value in self._build()["redaction"].values()))

    def test_each_blocked_upstream_verifier_fails_closed(self) -> None:
        for protocol_status, replay_status in (("BLOCK", "PASS"), ("PASS", "BLOCK")):
            with self.subTest(
                protocol_status=protocol_status,
                replay_status=replay_status,
            ):
                document = self._build(
                    protocol_status=protocol_status,
                    replay_status=replay_status,
                )
                self.assertEqual(document["source"]["status"], "UNKNOWN")
                self.assertFalse(document["maturity"]["source_contracts_verified"])

    def test_verifier_exception_fails_closed(self) -> None:
        with patch.object(
            subject,
            "verify_protocol_summary",
            side_effect=ValueError("synthetic failure"),
        ), patch.object(
            subject,
            "verify_provider_replay_gate",
            return_value={"status": "PASS", "blockers": []},
        ):
            document = subject.build_strategy_correlation_provider_evidence_public_projection_v1(
                self.protocol_summary,
                self.provider_replay_gate,
                protocol_verification_context=self.protocol_context,
                provider_replay_verification_context=self.replay_context,
            )

        self.assertEqual(document["source"]["status"], "UNKNOWN")

    def test_non_dict_context_fails_closed_without_calling_verifier(self) -> None:
        with patch.object(subject, "verify_protocol_summary") as protocol_verifier, patch.object(
            subject,
            "verify_provider_replay_gate",
            return_value={"status": "PASS", "blockers": []},
        ):
            document = subject.build_strategy_correlation_provider_evidence_public_projection_v1(
                self.protocol_summary,
                self.provider_replay_gate,
                protocol_verification_context=None,
                provider_replay_verification_context=self.replay_context,
            )

        protocol_verifier.assert_not_called()
        self.assertEqual(document["source"]["status"], "UNKNOWN")

    def test_builder_does_not_mutate_inputs(self) -> None:
        inputs_before = copy.deepcopy(
            (
                self.protocol_summary,
                self.provider_replay_gate,
                self.protocol_context,
                self.replay_context,
            )
        )

        self._build()

        self.assertEqual(
            (
                self.protocol_summary,
                self.provider_replay_gate,
                self.protocol_context,
                self.replay_context,
            ),
            inputs_before,
        )

    def test_verification_context_is_forwarded_but_not_returned(self) -> None:
        with patch.object(
            subject,
            "verify_protocol_summary",
            return_value={"status": "PASS", "blockers": []},
        ) as protocol_verifier, patch.object(
            subject,
            "verify_provider_replay_gate",
            return_value={"status": "PASS", "blockers": []},
        ) as replay_verifier:
            document = subject.build_strategy_correlation_provider_evidence_public_projection_v1(
                self.protocol_summary,
                self.provider_replay_gate,
                protocol_verification_context=self.protocol_context,
                provider_replay_verification_context=self.replay_context,
            )

        protocol_verifier.assert_called_once_with(
            self.protocol_summary,
            trusted_protocol_root="protocol-root-secret",
        )
        replay_verifier.assert_called_once_with(
            self.provider_replay_gate,
            trusted_registry_key="registry-key-secret",
        )
        self.assertNotIn("secret", json.dumps(document, sort_keys=True))

    def test_exact_rebuild_verification_passes_but_remains_non_authoritative(self) -> None:
        document = self._build()
        with patch.object(
            subject,
            "verify_protocol_summary",
            return_value={"status": "PASS", "blockers": []},
        ), patch.object(
            subject,
            "verify_provider_replay_gate",
            return_value={"status": "PASS", "blockers": []},
        ):
            verification = subject.verify_strategy_correlation_provider_evidence_public_projection_v1(
                document,
                self.protocol_summary,
                self.provider_replay_gate,
                protocol_verification_context=self.protocol_context,
                provider_replay_verification_context=self.replay_context,
            )

        self.assertEqual(verification["status"], "PASS")
        self.assertTrue(verification["upstream_source_contracts_verified"])
        self.assertFalse(verification["provider_gate_outcome_proven"])
        self.assertFalse(verification["current_admission_allowed"])
        self.assertFalse(verification["paper_authorized"])
        self.assertFalse(verification["live_order_allowed"])

    def test_tampering_is_blocked_by_exact_rebuild(self) -> None:
        document = self._build()
        document["permission"]["paper_authorized"] = True

        with patch.object(
            subject,
            "verify_protocol_summary",
            return_value={"status": "PASS", "blockers": []},
        ), patch.object(
            subject,
            "verify_provider_replay_gate",
            return_value={"status": "PASS", "blockers": []},
        ):
            verification = subject.verify_strategy_correlation_provider_evidence_public_projection_v1(
                document,
                self.protocol_summary,
                self.provider_replay_gate,
                protocol_verification_context=self.protocol_context,
                provider_replay_verification_context=self.replay_context,
            )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertEqual(
            verification["blockers"],
            ["provider_evidence_public_projection_exact_rebuild_mismatch"],
        )

    def test_exact_unknown_projection_is_valid_but_does_not_verify_sources(self) -> None:
        document = self._build(protocol_status="BLOCK")
        with patch.object(
            subject,
            "verify_protocol_summary",
            return_value={"status": "BLOCK", "blockers": ["synthetic"]},
        ), patch.object(
            subject,
            "verify_provider_replay_gate",
            return_value={"status": "PASS", "blockers": []},
        ):
            verification = subject.verify_strategy_correlation_provider_evidence_public_projection_v1(
                document,
                self.protocol_summary,
                self.provider_replay_gate,
                protocol_verification_context=self.protocol_context,
                provider_replay_verification_context=self.replay_context,
            )

        self.assertEqual(verification["status"], "PASS")
        self.assertFalse(verification["upstream_source_contracts_verified"])
        self.assertEqual(document["source"]["status"], "UNKNOWN")

    def test_all_authority_fields_are_permanently_false(self) -> None:
        document = self._build()

        self.assertEqual(document["permission"]["status"], "RESEARCH_ONLY")
        for field in (
            "profitability_claim_allowed",
            "current_admission_allowed",
            "current_writer_activation_allowed",
            "paper_authorized",
            "live_order_allowed",
        ):
            self.assertFalse(document["permission"][field])
        self.assertFalse(document["activation"]["automatic_activation_allowed"])
        self.assertFalse(document["activation"]["current_pointer_mutation_allowed"])


if __name__ == "__main__":
    unittest.main()
