from __future__ import annotations

import unittest

from tests.test_strategy_correlation_incumbent_snapshot_replay_cursor_provider_v1 import (
    IncumbentSnapshotReplayCursorProviderV1Tests as ProviderFixture,
)
from tests.test_strategy_correlation_incumbent_snapshot_replay_cursor_provider_signed_receipt_v1 import (
    ReplayCursorProviderSignedReceiptV1Tests as ReceiptFixture,
)
from tests.test_strategy_correlation_incumbent_snapshot_replay_cursor_provider_conformance_evidence_v1 import (
    ReplayCursorProviderConformanceEvidenceV1Tests as ConformanceFixture,
)
from tests.test_strategy_correlation_incumbent_snapshot_replay_cursor_provider_conformance_transcript_binding_v1 import (
    ReplayCursorProviderConformanceTranscriptBindingV1Tests as TranscriptFixture,
)
from tests.test_strategy_correlation_incumbent_snapshot_replay_cursor_provider_conformance_transcript_content_verifier_v1 import (
    ReplayCursorProviderConformanceTranscriptContentVerifierV1Tests as ContentFixture,
)


class ReplayCursorFixtureSetupCacheV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ContentFixture.setUpClass()

    def test_each_fixture_sets_a_class_local_success_sentinel(self) -> None:
        for fixture in (
            ProviderFixture,
            ReceiptFixture,
            ConformanceFixture,
            TranscriptFixture,
            ContentFixture,
        ):
            self.assertIs(
                fixture.__dict__.get("_fixture_setup_complete_v1"), True
            )

    def test_repeated_setup_preserves_material_identity(self) -> None:
        fixtures_and_materials = (
            (ProviderFixture, "command"),
            (ReceiptFixture, "provider_command"),
            (ConformanceFixture, "signed_reports"),
            (TranscriptFixture, "manifests"),
            (ContentFixture, "content_bundles"),
        )
        for fixture, material_name in fixtures_and_materials:
            before = getattr(fixture, material_name)
            fixture.setUpClass()
            fixture.setUpClass()
            self.assertIs(getattr(fixture, material_name), before)

    def test_cached_chain_still_produces_exact_blocked_content_evidence(
        self,
    ) -> None:
        fixture = ContentFixture(
            methodName=(
                "test_valid_local_content_passes_without_availability_promotion"
            )
        )
        first = fixture.evaluate()
        ContentFixture.setUpClass()
        second = fixture.evaluate()
        self.assertEqual(first, second)
        self.assertEqual(second["status"], "PASS")
        self.assertEqual(second["admission_status"], "BLOCKED")
        self.assertFalse(second["facts"]["public_artifact_availability_verified"])
        self.assertTrue(
            all(
                value is False
                for key, value in second["authority"].items()
                if key != "descriptive_only"
            )
        )


if __name__ == "__main__":
    unittest.main()
