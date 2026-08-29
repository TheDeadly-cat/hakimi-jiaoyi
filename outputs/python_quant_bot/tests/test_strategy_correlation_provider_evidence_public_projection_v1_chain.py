from __future__ import annotations

import copy
import json
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_provider_evidence_public_projection_v1 as consumer,
)
from exchange_terminal.services.strategy_correlation_strata_protocol_projection import (
    build_strategy_correlation_strata_protocol_migration_public_summary,
    verify_strategy_correlation_strata_protocol_migration_public_summary,
)
from tests import (
    test_strategy_correlation_provider_dataset_key_lifecycle_replay_gate_v1 as replay_gate_tests,
)
from tests import (
    test_strategy_correlation_strata_protocol_projection as protocol_projection_tests,
)


def _fixture_instance(test_case_class: type[unittest.TestCase]) -> unittest.TestCase:
    method_name = next(
        name for name in test_case_class.__dict__ if name.startswith("test_")
    )
    instance = test_case_class(methodName=method_name)
    setup = getattr(instance, "setUp", None)
    if callable(setup):
        setup()
    return instance


class StrategyCorrelationProviderEvidencePublicProjectionV1ChainTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        protocol_fixture = _fixture_instance(
            protocol_projection_tests.StrategyCorrelationStrataProtocolProjectionTests
        )
        (
            cls.protocol_registration,
            cls.protocol_inputs,
        ) = protocol_fixture._registry()
        cls.protocol_summary = (
            build_strategy_correlation_strata_protocol_migration_public_summary(
                cls.protocol_registration,
                **cls.protocol_inputs,
            )
        )
        cls.protocol_context = {
            "source_protocol_registration": cls.protocol_registration,
            **cls.protocol_inputs,
        }
        protocol_verification = (
            verify_strategy_correlation_strata_protocol_migration_public_summary(
                cls.protocol_summary,
                **cls.protocol_context,
            )
        )
        if protocol_verification.get("status") != "PASS":
            raise AssertionError("synthetic protocol projection fixture invalid")

        cls.replay_fixture = _fixture_instance(
            replay_gate_tests.StrategyCorrelationProviderDatasetKeyLifecycleReplayGateV1Tests
        )
        cls.replay_gate = cls.replay_fixture.evaluate()
        if cls.replay_fixture.verify(cls.replay_gate) is not True:
            raise AssertionError("synthetic lifecycle replay fixture invalid")

    def _replay_verifier_adapter(self, document, **context):
        if context:
            return {"status": "BLOCK", "blockers": ["unexpected_context"]}
        passed = self.replay_fixture.verify(document) is True
        return {
            "status": "PASS" if passed else "BLOCK",
            "blockers": [] if passed else ["synthetic_replay_verification_failed"],
        }

    def _build(
        self,
        *,
        protocol_summary=None,
        replay_gate=None,
        replay_context=None,
    ):
        if protocol_summary is None:
            protocol_summary = self.protocol_summary
        if replay_gate is None:
            replay_gate = self.replay_gate
        if replay_context is None:
            replay_context = {}
        with patch.object(
            consumer,
            "verify_provider_replay_gate",
            self._replay_verifier_adapter,
        ):
            return consumer.build_strategy_correlation_provider_evidence_public_projection_v1(
                protocol_summary,
                replay_gate,
                protocol_verification_context=self.protocol_context,
                provider_replay_verification_context=replay_context,
            )

    def test_real_synthetic_verifier_chain_observes_sources_only(self) -> None:
        projection = self._build()

        self.assertEqual(projection["source"]["status"], "OBSERVED")
        self.assertTrue(projection["maturity"]["source_contracts_verified"])
        self.assertEqual(projection["maturity"]["status"], "UNKNOWN")
        self.assertFalse(projection["source"]["semantic_gate_outcome_projected"])
        self.assertFalse(projection["claims"]["provider_gate_outcome_proven"])
        self.assertFalse(projection["activation"]["current_reference_present"])

    def test_real_protocol_verifier_rejects_tampered_summary(self) -> None:
        tampered = copy.deepcopy(self.protocol_summary)
        tampered["unexpected_field"] = "tampered"

        projection = self._build(protocol_summary=tampered)

        self.assertEqual(projection["source"]["status"], "UNKNOWN")
        self.assertFalse(projection["maturity"]["source_contracts_verified"])

    def test_real_replay_verifier_rejects_tampered_gate(self) -> None:
        tampered = copy.deepcopy(self.replay_gate)
        tampered["unexpected_field"] = "tampered"

        projection = self._build(replay_gate=tampered)

        self.assertEqual(projection["source"]["status"], "UNKNOWN")
        self.assertFalse(projection["maturity"]["source_contracts_verified"])

    def test_replay_adapter_rejects_unregistered_context(self) -> None:
        projection = self._build(replay_context={"unexpected": "context"})

        self.assertEqual(projection["source"]["status"], "UNKNOWN")
        self.assertFalse(projection["maturity"]["source_contracts_verified"])

    def test_real_chain_exact_rebuild_remains_non_authoritative_and_redacted(self) -> None:
        projection = self._build()
        with patch.object(
            consumer,
            "verify_provider_replay_gate",
            self._replay_verifier_adapter,
        ):
            verification = consumer.verify_strategy_correlation_provider_evidence_public_projection_v1(
                projection,
                self.protocol_summary,
                self.replay_gate,
                protocol_verification_context=self.protocol_context,
                provider_replay_verification_context={},
            )

        self.assertEqual(verification["status"], "PASS")
        self.assertTrue(verification["upstream_source_contracts_verified"])
        self.assertFalse(verification["provider_gate_outcome_proven"])
        self.assertFalse(verification["current_admission_allowed"])
        self.assertFalse(verification["paper_authorized"])
        self.assertFalse(verification["live_order_allowed"])

        serialized = json.dumps(projection, sort_keys=True)
        self.assertNotIn(self.protocol_summary["schema_version"], serialized)
        self.assertNotIn(self.replay_gate["schema_version"], serialized)
        self.assertNotIn("source_protocol_registration", serialized)
        self.assertNotIn("provider_replay_gate", serialized)


if __name__ == "__main__":
    unittest.main()
