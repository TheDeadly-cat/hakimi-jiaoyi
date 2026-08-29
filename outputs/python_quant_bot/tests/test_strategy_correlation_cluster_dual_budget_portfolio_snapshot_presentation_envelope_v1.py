from __future__ import annotations

from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_cluster_dual_budget_portfolio_snapshot_presentation_envelope_v1
    as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


SOURCE_VERIFIER = (
    "verify_dual_budget_portfolio_snapshot_reconciliation_v9"
)


def _source(status: str = "PASS") -> dict[str, object]:
    return {
        "schema_version": subject.SOURCE_SCHEMA_VERSION,
        "static_fingerprint": subject.SOURCE_STATIC_FINGERPRINT,
        "status": status,
        "decision": "LOCAL_RESEARCH_SCOPE_RECONCILED",
        "facts": {"synthetic_fixture": True},
        "authority": {"paper_allowed": False, "live_allowed": False},
        "blockers": [],
        "portfolio_snapshot_reconciliation_v9_hash": "a" * 64,
    }


def _context() -> dict[str, object]:
    return {
        "preregistration": {"status": "PASS"},
        "proposal_reconciliation_v8_document": {"status": "PASS"},
        "proposal_reconciliation_v8_context": {"synthetic": True},
        "expected_portfolio_snapshot_preregistration_v9_hash": "b" * 64,
    }


class DualBudgetPortfolioSnapshotPresentationEnvelopeV1Tests(unittest.TestCase):
    def _build(
        self,
        source: dict[str, object] | None = None,
        *,
        context: object | None = None,
        expected_hash: object = "a" * 64,
        verifier_result: object = None,
        verifier_error: Exception | None = None,
    ) -> dict[str, object]:
        source = deepcopy(source if source is not None else _source())
        context = deepcopy(_context() if context is None else context)
        result = {"verified": True} if verifier_result is None else verifier_result
        with patch.object(
            subject.source_contract,
            SOURCE_VERIFIER,
            return_value=result,
            side_effect=verifier_error,
        ):
            return subject.build_strategy_correlation_cluster_dual_budget_portfolio_snapshot_presentation_envelope_v1(
                source,
                context,
                expected_source_hash=expected_hash,
            )

    def _verify(
        self,
        envelope: object,
        source: dict[str, object] | None = None,
    ) -> dict[str, object]:
        with patch.object(
            subject.source_contract,
            SOURCE_VERIFIER,
            return_value={"verified": True},
        ):
            return subject.verify_strategy_correlation_cluster_dual_budget_portfolio_snapshot_presentation_envelope_v1(
                envelope,
                deepcopy(source if source is not None else _source()),
                _context(),
                expected_source_hash="a" * 64,
            )

    def test_raw_v9_shape_has_no_frontend_sequence_but_envelope_does(self) -> None:
        source = _source()
        self.assertNotIn("axis_order", source)
        self.assertNotIn("stages", source)
        envelope = self._build(source)
        self.assertEqual(envelope["axis_order"], list(subject.AXIS_ORDER))
        self.assertEqual(
            [stage["axis"] for stage in envelope["stages"]],
            list(subject.AXIS_ORDER),
        )

    def test_exact_source_verifier_receives_only_detached_context(self) -> None:
        source = _source()
        context = _context()
        with patch.object(
            subject.source_contract,
            SOURCE_VERIFIER,
            return_value={"verified": True},
        ) as verifier:
            envelope = subject.build_strategy_correlation_cluster_dual_budget_portfolio_snapshot_presentation_envelope_v1(
                deepcopy(source),
                deepcopy(context),
                expected_source_hash="a" * 64,
            )
        verifier.assert_called_once_with(source, **context)
        self.assertEqual(envelope["source"]["state"], "OBSERVED")

    def test_local_pass_never_unlocks_permission(self) -> None:
        envelope = self._build()
        self.assertEqual(envelope["status"], "PASS")
        self.assertEqual(envelope["stages"][3]["state"], "LOCKED")
        self.assertTrue(envelope["authority"]["research_only"])
        self.assertTrue(envelope["authority"]["presentation_only"])
        self.assertTrue(envelope["authority"]["descriptive_only"])
        self.assertTrue(
            all(
                value is False
                for key, value in envelope["authority"].items()
                if key
                not in {"research_only", "presentation_only", "descriptive_only"}
            )
        )

    def test_local_non_pass_is_visible_without_changing_locks(self) -> None:
        envelope = self._build(_source("BLOCK"))
        self.assertEqual(envelope["status"], "BLOCK")
        self.assertEqual(
            envelope["stages"][0]["state"], "LOCAL_CONTRACT_NOT_PASS"
        )
        self.assertEqual(envelope["stages"][3]["state"], "LOCKED")

    def test_expected_source_hash_is_strict_and_bound(self) -> None:
        self.assertEqual(
            self._build(expected_hash="not-a-hash")["blockers"][0],
            "EXPECTED_SOURCE_HASH_INVALID",
        )
        self.assertEqual(
            self._build(expected_hash="b" * 64)["blockers"][0],
            "SOURCE_V9_HASH_MISMATCH",
        )

    def test_source_identity_is_exact(self) -> None:
        source = _source()
        source["schema_version"] = "other"
        self.assertEqual(
            self._build(source)["blockers"][0], "SOURCE_V9_SCHEMA_MISMATCH"
        )
        source = _source()
        source["static_fingerprint"] = "other"
        self.assertEqual(
            self._build(source)["blockers"][0],
            "SOURCE_V9_FINGERPRINT_MISMATCH",
        )

    def test_unverified_or_raising_source_fails_closed(self) -> None:
        self.assertEqual(
            self._build(verifier_result={"verified": False})["decision"],
            "UNKNOWN_SOURCE",
        )
        self.assertEqual(
            self._build(verifier_error=ValueError("synthetic"))["decision"],
            "UNKNOWN_SOURCE",
        )

    def test_unknown_source_exposes_no_hash_or_local_status(self) -> None:
        envelope = self._build(verifier_result=False)
        self.assertIsNone(
            envelope["source"]["portfolio_snapshot_reconciliation_v9_hash"]
        )
        self.assertIsNone(envelope["source"]["local_contract_status"])
        self.assertFalse(envelope["facts"]["source_exactly_verified"])

    def test_external_truth_profitability_and_market_evidence_stay_false(self) -> None:
        facts = self._build()["facts"]
        self.assertFalse(facts["external_portfolio_provider_identity_verified"])
        self.assertFalse(facts["external_portfolio_source_truth_verified"])
        self.assertFalse(facts["external_portfolio_freshness_verified"])
        self.assertFalse(facts["formal_market_evidence_verified"])
        self.assertFalse(facts["profitability_proven"])

    def test_user_facing_stage_text_has_no_promotional_tokens(self) -> None:
        envelope = self._build()
        visible = " ".join(
            f"{stage['state']} {stage['headline']}"
            for stage in envelope["stages"]
        ).upper()
        for token in ("READY", "PROFIT", "BUY", "SELL"):
            self.assertNotIn(token, visible)

    def test_projection_is_bounded_and_excludes_raw_portfolio_inputs(self) -> None:
        envelope = self._build()
        encoded = json.dumps(envelope, sort_keys=True)
        self.assertLess(len(encoded), 6000)
        forbidden_keys = {
            "positions",
            "portfolio_snapshot",
            "return_panel",
            "market_data_envelopes",
            "source_verification_context",
        }

        def keys(value: object) -> set[str]:
            if type(value) is dict:
                return set(value) | set().union(*(keys(item) for item in value.values()))
            if type(value) is list:
                return set().union(*(keys(item) for item in value))
            return set()

        self.assertFalse(keys(envelope) & forbidden_keys)

    def test_exact_verification_and_resealed_promotion_attack(self) -> None:
        envelope = self._build()
        self.assertTrue(self._verify(envelope)["verified"])
        altered = deepcopy(envelope)
        altered["authority"]["paper_allowed"] = True
        altered = seal_strict_canonical_document(altered, "envelope_hash")
        receipt = self._verify(altered)
        self.assertFalse(receipt["verified"])
        self.assertEqual(receipt["blockers"], ["PRESENTATION_ENVELOPE_NOT_EXACT"])


if __name__ == "__main__":
    unittest.main()
