from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exchange_terminal.application import (  # noqa: E402
    strategy_correlation_history_covered_budget_universe_cluster_exposure_readonly_projection_v1
    as readonly_projection,
)
from exchange_terminal.application.strategy_correlation_history_covered_budget_universe_cluster_exposure_preflight_v1 import (  # noqa: E402
    POLICY_VERSION,
    ClusterExposurePolicyV1,
    ClusterExposureProposalV1,
)
from exchange_terminal.interfaces import (  # noqa: E402
    strategy_correlation_cluster_exposure_readonly_projection_handoff_v1
    as handoff,
)
from tests import (  # noqa: E402
    test_strategy_correlation_history_covered_budget_universe_batch_cluster_preflight_v1
    as batch_fixture_module,
)


PRESENTER_PATH = (
    ROOT
    / "exchange_terminal"
    / "static"
    / "evidence_cluster_exposure_readonly_projection_v1.js"
)


def policy(
    *,
    max_portfolio_gross_bps: int = 8_000,
    max_cluster_gross_bps: int = 3_000,
    max_single_proposal_gross_bps: int = 2_000,
) -> ClusterExposurePolicyV1:
    return ClusterExposurePolicyV1(
        policy_version=POLICY_VERSION,
        policy_id="python-js-handoff-policy-20260824",
        max_proposals=8,
        max_portfolio_gross_bps=max_portfolio_gross_bps,
        max_cluster_gross_bps=max_cluster_gross_bps,
        max_single_proposal_gross_bps=max_single_proposal_gross_bps,
    )


def proposal(
    proposal_id: str,
    symbol: str,
    requested_gross_bps: int,
) -> ClusterExposureProposalV1:
    return ClusterExposureProposalV1(
        proposal_id=proposal_id,
        symbol=symbol,
        requested_gross_bps=requested_gross_bps,
    )


def reseal_projection(document: dict) -> dict:
    mutated = copy.deepcopy(document)
    mutated.pop("readonly_projection_hash", None)
    encoded = json.dumps(
        mutated,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    mutated["readonly_projection_hash"] = hashlib.sha256(encoded).hexdigest()
    return mutated


def present_with_node(envelope: dict) -> dict:
    script = """
const presenter = require(process.argv[1]);
let source = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => { source += chunk; });
process.stdin.on("end", () => {
  const model = presenter.deriveClusterExposureViewModelV1(JSON.parse(source));
  process.stdout.write(JSON.stringify({
    verificationAccepted: model.verificationAccepted,
    rawStatus: model.rawStatus,
    metricValues: model.metrics.map((item) => item.value),
    statusLabel: model.statusLabel,
  }));
});
"""
    completed = subprocess.run(
        ["node", "-e", script, str(PRESENTER_PATH)],
        cwd=ROOT,
        input=json.dumps(envelope, ensure_ascii=True, separators=(",", ":")),
        text=True,
        capture_output=True,
        check=False,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr or completed.stdout)
    return json.loads(completed.stdout)


class ClusterExposureReadonlyProjectionHandoffV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fixture = (
            batch_fixture_module.StrategyCorrelationHistoryCoveredBudgetUniverseBatchClusterPreflightV1Tests
        )
        fixture.setUpClass()
        cls.fixture = fixture
        cls.projection = fixture.projection
        cls.projection_hash = fixture.projection_hash
        cls.context = fixture.context
        cls.projected_symbols = tuple(
            cls.projection["derivation"]["projected_symbols"]
        )
        if len(cls.projected_symbols) < 2:
            raise AssertionError("synthetic fixture needs two projected symbols")

    @classmethod
    def build_documents(cls, proposals, exposure_policy=None):
        selected_policy = policy() if exposure_policy is None else exposure_policy
        batch_document = cls.fixture._evaluate(
            [item.symbol for item in proposals]
        )
        projection_document = readonly_projection.build_cluster_exposure_readonly_projection_from_verified_batch_v1(
            batch_document,
            cls.projection,
            proposals,
            selected_policy,
            expected_batch_preflight_hash=batch_document["preflight_hash"],
            expected_projection_preregistration_hash=cls.projection_hash,
            projection_verification_context=cls.context,
        )
        if projection_document is None:
            raise AssertionError("readonly projection did not build")
        return selected_policy, batch_document, projection_document

    @classmethod
    def build_handoff(
        cls,
        proposals,
        *,
        exposure_policy=None,
        projection_document=None,
        expected_projection_hash=None,
    ):
        selected_policy, batch_document, built_projection = cls.build_documents(
            proposals,
            exposure_policy,
        )
        source_projection = (
            built_projection if projection_document is None else projection_document
        )
        source_hash = (
            source_projection["readonly_projection_hash"]
            if expected_projection_hash is None
            else expected_projection_hash
        )
        envelope = handoff.build_cluster_exposure_readonly_projection_handoff_v1(
            source_projection,
            batch_document,
            cls.projection,
            proposals,
            selected_policy,
            expected_readonly_projection_hash=source_hash,
            expected_batch_preflight_hash=batch_document["preflight_hash"],
            expected_projection_preregistration_hash=cls.projection_hash,
            projection_verification_context=cls.context,
        )
        return envelope, selected_policy, batch_document, source_projection

    def test_within_limit_handoff_is_accepted_by_real_node_presenter(self) -> None:
        first, second = self.projected_symbols[:2]
        proposals = (
            proposal("p-1", first, 1_000),
            proposal("p-2", second, 1_100),
        )
        envelope, _, _, _ = self.build_handoff(proposals)

        self.assertIsNotNone(envelope)
        assert envelope is not None
        presented = present_with_node(envelope)
        self.assertTrue(presented["verificationAccepted"])
        self.assertEqual(
            presented["rawStatus"],
            readonly_projection.PUBLIC_STATUS_WITHIN_LIMIT,
        )
        self.assertEqual(presented["metricValues"], ["2", "2", "21.00%", "11.00%"])
        self.assertEqual(presented["statusLabel"], "结构内观察")

    def test_shared_limit_breach_handoff_is_accepted_as_blocked(self) -> None:
        symbol = self.projected_symbols[0]
        proposals = (
            proposal("p-1", symbol, 1_600),
            proposal("p-2", symbol, 1_500),
        )
        envelope, _, _, _ = self.build_handoff(proposals)

        self.assertIsNotNone(envelope)
        assert envelope is not None
        presented = present_with_node(envelope)
        self.assertTrue(presented["verificationAccepted"])
        self.assertEqual(
            presented["rawStatus"],
            readonly_projection.PUBLIC_STATUS_LIMIT_BREACH,
        )
        self.assertEqual(presented["metricValues"], ["2", "1", "31.00%", "31.00%"])
        self.assertEqual(presented["statusLabel"], "预登记上限阻断")

    def test_unknown_policy_handoff_is_accepted_without_metrics(self) -> None:
        symbol = self.projected_symbols[0]
        proposals = (proposal("p-1", symbol, 400),)
        invalid_policy = policy(
            max_cluster_gross_bps=500,
            max_single_proposal_gross_bps=600,
        )
        envelope, _, _, _ = self.build_handoff(
            proposals,
            exposure_policy=invalid_policy,
        )

        self.assertIsNotNone(envelope)
        assert envelope is not None
        presented = present_with_node(envelope)
        self.assertTrue(presented["verificationAccepted"])
        self.assertEqual(presented["rawStatus"], readonly_projection.PUBLIC_STATUS_UNKNOWN)
        self.assertEqual(presented["metricValues"], ["--", "--", "--", "--"])

    def test_wrong_expected_projection_hash_produces_no_handoff(self) -> None:
        symbol = self.projected_symbols[0]
        proposals = (proposal("p-1", symbol, 500),)
        envelope, _, _, _ = self.build_handoff(
            proposals,
            expected_projection_hash="0" * 64,
        )
        self.assertIsNone(envelope)

    def test_resealed_authority_promotion_produces_no_handoff(self) -> None:
        symbol = self.projected_symbols[0]
        proposals = (proposal("p-1", symbol, 500),)
        selected_policy, batch_document, projection_document = self.build_documents(
            proposals
        )
        tampered = copy.deepcopy(projection_document)
        tampered["authority"]["readonly_projection_activation_allowed"] = True
        tampered = reseal_projection(tampered)
        envelope = handoff.build_cluster_exposure_readonly_projection_handoff_v1(
            tampered,
            batch_document,
            self.projection,
            proposals,
            selected_policy,
            expected_readonly_projection_hash=tampered["readonly_projection_hash"],
            expected_batch_preflight_hash=batch_document["preflight_hash"],
            expected_projection_preregistration_hash=self.projection_hash,
            projection_verification_context=self.context,
        )
        self.assertIsNone(envelope)

    def test_handoff_exact_verifier_rejects_mutated_envelope(self) -> None:
        first, second = self.projected_symbols[:2]
        proposals = (
            proposal("p-1", first, 700),
            proposal("p-2", second, 800),
        )
        envelope, selected_policy, batch_document, projection_document = (
            self.build_handoff(proposals)
        )
        self.assertIsNotNone(envelope)
        assert envelope is not None
        projection_hash = projection_document["readonly_projection_hash"]
        self.assertTrue(
            handoff.verify_cluster_exposure_readonly_projection_handoff_v1(
                envelope,
                projection_document,
                batch_document,
                self.projection,
                proposals,
                selected_policy,
                expected_readonly_projection_hash=projection_hash,
                expected_batch_preflight_hash=batch_document["preflight_hash"],
                expected_projection_preregistration_hash=self.projection_hash,
                projection_verification_context=self.context,
            )
        )
        mutated = copy.deepcopy(envelope)
        mutated["verification_status"] = "FORGED"
        self.assertFalse(
            handoff.verify_cluster_exposure_readonly_projection_handoff_v1(
                mutated,
                projection_document,
                batch_document,
                self.projection,
                proposals,
                selected_policy,
                expected_readonly_projection_hash=projection_hash,
                expected_batch_preflight_hash=batch_document["preflight_hash"],
                expected_projection_preregistration_hash=self.projection_hash,
                projection_verification_context=self.context,
            )
        )

    def test_handoff_is_a_deep_copy_and_remains_redacted(self) -> None:
        first, second = self.projected_symbols[:2]
        proposals = (
            proposal("p-1", first, 600),
            proposal("p-2", second, 700),
        )
        envelope, _, _, projection_document = self.build_handoff(proposals)
        self.assertIsNotNone(envelope)
        assert envelope is not None
        envelope["projection"]["status"] = "MUTATED"
        self.assertNotEqual(projection_document["status"], "MUTATED")

        serialized = json.dumps(projection_document, ensure_ascii=False)
        for symbol in (first, second):
            self.assertNotIn(json.dumps(symbol), serialized)

    def test_production_bridge_has_no_io_runtime_or_node_dependency(self) -> None:
        source = Path(handoff.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "open(",
            "subprocess",
            "requests.",
            "urllib.",
            "socket.",
            "sqlite3",
            "register_route(",
            "write_current_pointer(",
            "node ",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
