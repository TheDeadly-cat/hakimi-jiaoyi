from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exchange_terminal.application import strategy_correlation_history_covered_budget_universe_cluster_exposure_concentration_gate_v1 as concentration_gate  # noqa: E402
from exchange_terminal.application import strategy_correlation_history_covered_budget_universe_cluster_exposure_concentration_readonly_projection_v1 as readonly_projection  # noqa: E402
from exchange_terminal.application.strategy_correlation_history_covered_budget_universe_cluster_exposure_preflight_v1 import POLICY_VERSION as EXPOSURE_POLICY_VERSION, ClusterExposurePolicyV1, ClusterExposureProposalV1  # noqa: E402
from exchange_terminal.interfaces import strategy_correlation_cluster_exposure_concentration_readonly_projection_handoff_v1 as handoff  # noqa: E402
from tests import test_strategy_correlation_history_covered_budget_universe_batch_cluster_preflight_v1 as batch_fixture_module  # noqa: E402


PRESENTER = ROOT / "exchange_terminal" / "static" / "evidence_cluster_exposure_concentration_readonly_projection_v1.js"


def exposure_policy():
    return ClusterExposurePolicyV1(policy_version=EXPOSURE_POLICY_VERSION, policy_id="concentration-handoff-source-policy-20260824", max_proposals=8, max_portfolio_gross_bps=8000, max_cluster_gross_bps=3000, max_single_proposal_gross_bps=3000)


def concentration_policy():
    return concentration_gate.ClusterExposureConcentrationPolicyV1(policy_version=concentration_gate.POLICY_VERSION, policy_id="concentration-handoff-policy-20260824", min_independent_clusters=2, max_largest_cluster_share_bps=6000, max_hhi_ppm=550000)


def proposal(proposal_id, symbol, gross):
    return ClusterExposureProposalV1(proposal_id=proposal_id, symbol=symbol, requested_gross_bps=gross)


def reseal(document):
    mutated = copy.deepcopy(document)
    mutated.pop("readonly_projection_hash", None)
    encoded = json.dumps(mutated, allow_nan=False, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("ascii")
    mutated["readonly_projection_hash"] = hashlib.sha256(encoded).hexdigest()
    return mutated


def present(envelope):
    script = 'const p=require(process.argv[1]);let s="";process.stdin.setEncoding("utf8");process.stdin.on("data",c=>s+=c);process.stdin.on("end",()=>{const m=p.deriveClusterConcentrationViewModelV1(JSON.parse(s));process.stdout.write(JSON.stringify({accepted:m.verificationAccepted,status:m.rawStatus,values:m.metrics.map(x=>x.value),label:m.statusLabel}));});'
    completed = subprocess.run(["node", "-e", script, str(PRESENTER)], cwd=ROOT, input=json.dumps(envelope, ensure_ascii=True, separators=(",", ":")), text=True, capture_output=True, check=False, encoding="utf-8")
    if completed.returncode != 0:
        raise AssertionError(completed.stderr or completed.stdout)
    return json.loads(completed.stdout)


class ClusterExposureConcentrationReadonlyProjectionHandoffV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = batch_fixture_module.StrategyCorrelationHistoryCoveredBudgetUniverseBatchClusterPreflightV1Tests
        fixture.setUpClass()
        cls.fixture = fixture
        cls.projection = fixture.projection
        cls.projection_hash = fixture.projection_hash
        cls.context = fixture.context
        cls.symbols = tuple(cls.projection["derivation"]["projected_symbols"])

    @classmethod
    def documents(cls, proposals, c_policy=None):
        ep = exposure_policy()
        cp = concentration_policy() if c_policy is None else c_policy
        batch = cls.fixture._evaluate([item.symbol for item in proposals])
        projection = readonly_projection.build_cluster_exposure_concentration_readonly_projection_from_verified_batch_v1(batch, cls.projection, proposals, ep, cp, expected_batch_preflight_hash=batch["preflight_hash"], expected_projection_preregistration_hash=cls.projection_hash, projection_verification_context=cls.context)
        if projection is None:
            raise AssertionError("concentration projection did not build")
        return ep, cp, batch, projection

    @classmethod
    def build(cls, proposals, c_policy=None, projection_document=None, expected_hash=None):
        ep, cp, batch, built = cls.documents(proposals, c_policy)
        source = built if projection_document is None else projection_document
        source_hash = source["readonly_projection_hash"] if expected_hash is None else expected_hash
        envelope = handoff.build_cluster_exposure_concentration_readonly_projection_handoff_v1(source, batch, cls.projection, proposals, ep, cp, expected_readonly_projection_hash=source_hash, expected_batch_preflight_hash=batch["preflight_hash"], expected_projection_preregistration_hash=cls.projection_hash, projection_verification_context=cls.context)
        return envelope, ep, cp, batch, source

    def test_balanced_handoff_is_accepted_by_node_as_observation(self):
        first, second = self.symbols[:2]
        proposals = (proposal("p-1", first, 2000), proposal("p-2", second, 2000))
        envelope, *_ = self.build(proposals)
        self.assertIsNotNone(envelope)
        output = present(envelope)
        self.assertTrue(output["accepted"])
        self.assertEqual(output["status"], concentration_gate.STATUS_WITHIN_CONCENTRATION_LIMIT)
        self.assertEqual(output["values"], ["2", "2", "40.00%", "50.00%", "0.500000", "2.000"])

    def test_concentration_breach_handoff_is_accepted_as_blocked(self):
        first, second = self.symbols[:2]
        proposals = (proposal("p-1", first, 3000), proposal("p-2", second, 1000))
        envelope, *_ = self.build(proposals)
        output = present(envelope)
        self.assertEqual(output["status"], concentration_gate.STATUS_CONCENTRATION_LIMIT_BREACH)
        self.assertEqual(output["label"], "集中度门禁阻断")
        self.assertEqual(output["values"][3:], ["75.00%", "0.625000", "1.600"])

    def test_upstream_block_and_unknown_handoffs_hide_metrics(self):
        symbol = self.symbols[0]
        blocked = (proposal("p-1", symbol, 2000), proposal("p-2", symbol, 1500))
        unknown_policy = replace(concentration_policy(), max_hhi_ppm=True)
        unknown = (proposal("p-1", symbol, 400),)
        blocked_envelope, *_ = self.build(blocked)
        unknown_envelope, *_ = self.build(unknown, unknown_policy)
        for envelope in (blocked_envelope, unknown_envelope):
            output = present(envelope)
            self.assertTrue(output["accepted"])
            self.assertEqual(output["values"], ["--", "--", "--", "--", "--", "--"])

    def test_wrong_hash_produces_no_handoff(self):
        first, second = self.symbols[:2]
        proposals = (proposal("p-1", first, 1000), proposal("p-2", second, 1000))
        envelope, *_ = self.build(proposals, expected_hash="0" * 64)
        self.assertIsNone(envelope)

    def test_resealed_diversification_promotion_produces_no_handoff(self):
        first, second = self.symbols[:2]
        proposals = (proposal("p-1", first, 1000), proposal("p-2", second, 1000))
        ep, cp, batch, projection = self.documents(proposals)
        tampered = copy.deepcopy(projection)
        tampered["authority"]["diversification_claim_allowed"] = True
        tampered = reseal(tampered)
        envelope = handoff.build_cluster_exposure_concentration_readonly_projection_handoff_v1(tampered, batch, self.projection, proposals, ep, cp, expected_readonly_projection_hash=tampered["readonly_projection_hash"], expected_batch_preflight_hash=batch["preflight_hash"], expected_projection_preregistration_hash=self.projection_hash, projection_verification_context=self.context)
        self.assertIsNone(envelope)

    def test_exact_handoff_verifier_rejects_mutation(self):
        first, second = self.symbols[:2]
        proposals = (proposal("p-1", first, 1200), proposal("p-2", second, 1100))
        envelope, ep, cp, batch, projection = self.build(proposals)
        projection_hash = projection["readonly_projection_hash"]
        self.assertTrue(handoff.verify_cluster_exposure_concentration_readonly_projection_handoff_v1(envelope, projection, batch, self.projection, proposals, ep, cp, expected_readonly_projection_hash=projection_hash, expected_batch_preflight_hash=batch["preflight_hash"], expected_projection_preregistration_hash=self.projection_hash, projection_verification_context=self.context))
        mutated = copy.deepcopy(envelope)
        mutated["verification_status"] = "FORGED"
        self.assertFalse(handoff.verify_cluster_exposure_concentration_readonly_projection_handoff_v1(mutated, projection, batch, self.projection, proposals, ep, cp, expected_readonly_projection_hash=projection_hash, expected_batch_preflight_hash=batch["preflight_hash"], expected_projection_preregistration_hash=self.projection_hash, projection_verification_context=self.context))

    def test_handoff_is_deep_copied_and_redacted(self):
        first, second = self.symbols[:2]
        proposals = (proposal("p-1", first, 1000), proposal("p-2", second, 1000))
        envelope, _, _, _, projection = self.build(proposals)
        envelope["projection"]["status"] = "MUTATED"
        self.assertNotEqual(projection["status"], "MUTATED")
        serialized = json.dumps(projection, ensure_ascii=False)
        for symbol in (first, second):
            self.assertNotIn(json.dumps(symbol), serialized)

    def test_production_bridge_has_no_io_runtime_or_node_dependency(self):
        source = Path(handoff.__file__).read_text(encoding="utf-8")
        for forbidden in ("open(", "subprocess", "requests.", "urllib.", "socket.", "sqlite3", "register_route(", "write_current_pointer(", "node "):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
