from __future__ import annotations

import base64
from copy import deepcopy
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v4 as budget_v4,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v5 as subject,
)
from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    build_correlation_cluster_complete_link_audit,
    evaluate_correlation_cluster_gate_v2,
)
from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_cluster_preregistration,
    build_correlation_matrix_contract,
)
from exchange_terminal.services.strategy_correlation_preregistered_strata import (
    build_strategy_correlation_strata_preregistration,
    evaluate_strategy_correlation_strata_gate,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _spki(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


class StrategyCorrelationClusterEffectiveBetBudgetV5Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider_private = Ed25519PrivateKey.generate()
        self.provider_spki = _spki(self.provider_private)
        self.provider_kwargs = {
            "provider_id": "synthetic.portfolio.snapshot.provider.v1",
            "key_id": "synthetic.portfolio.snapshot.key.v1",
            "public_key_spki_sha256": sha256(
                self.provider_spki
            ).hexdigest(),
            "trust_domain": "synthetic.test-only",
            "account_scope_hash": _hash("synthetic-account-scope"),
            "implementation_claim_sha256": _hash(
                "synthetic-portfolio-snapshot-provider"
            ),
        }
        self.provider = (
            subject.build_portfolio_snapshot_provider_preregistration_v1(
                **self.provider_kwargs
            )
        )

        self.preregistration = build_correlation_cluster_preregistration(
            [
                {"cluster_id": "cluster-a", "members": ["A"]},
                {"cluster_id": "cluster-b", "members": ["B"]},
                {"cluster_id": "cluster-c", "members": ["C"]},
            ]
        )
        correlations = {
            pair: 0.10
            for pair in combinations(self.preregistration["symbols"], 2)
        }
        self.matrix = build_correlation_matrix_contract(
            self.preregistration["symbols"], correlations
        )
        self.audit = build_correlation_cluster_complete_link_audit(
            self.preregistration, self.matrix
        )
        cells = [
            {
                "gate_status": "PASS",
                "lane": "RAW_EXCESS",
                "strategy_id": "synthetic-strategy",
                "symbol": symbol,
                "variant_id": "synthetic-variant",
            }
            for symbol in self.preregistration["symbols"]
        ]
        self.complete_link_gate = evaluate_correlation_cluster_gate_v2(
            self.preregistration,
            self.matrix,
            cells,
            strategy_id="synthetic-strategy",
            variant_id="synthetic-variant",
            lane="RAW_EXCESS",
        )
        self.strata_registration = (
            build_strategy_correlation_strata_preregistration(
                self.preregistration,
                [
                    {
                        "dimension_id": "asset-family",
                        "strata": [
                            {
                                "stratum_id": "family-a",
                                "cluster_ids": ["cluster-a"],
                            },
                            {
                                "stratum_id": "family-b",
                                "cluster_ids": ["cluster-b"],
                            },
                            {
                                "stratum_id": "family-c",
                                "cluster_ids": ["cluster-c"],
                            },
                        ],
                    }
                ],
            )
        )
        self.strata_gate = evaluate_strategy_correlation_strata_gate(
            self.strata_registration,
            self.complete_link_gate,
            source_preregistration=self.preregistration,
        )
        self.positions = [
            {"symbol": "A", "notional": 2_500, "direction": "LONG"}
        ]
        self.low_equity_bundle = self.build_snapshot_bundle(
            equity=5_000,
            positions=self.positions,
            sequence=7,
            label="low-equity",
        )
        self.high_equity_bundle = self.build_snapshot_bundle(
            equity=10_000,
            positions=self.positions,
            sequence=8,
            label="high-equity",
        )
        self.increase_kwargs = {
            "strata_registration": self.strata_registration,
            "strata_gate": self.strata_gate,
            "complete_link_gate": self.complete_link_gate,
            "proposed_symbol": "B",
            "proposed_notional": 2_500,
            "proposed_direction": "LONG",
            "max_cluster_gross_pct": 45.0,
            "risk_increasing": True,
        }

    def build_snapshot_bundle(
        self,
        *,
        equity,
        positions,
        sequence,
        label,
        private_key=None,
        spki=None,
    ):
        claim_kwargs = {
            "provider_preregistration_kwargs": self.provider_kwargs,
            "snapshot_id_hash": _hash(f"snapshot-{label}"),
            "snapshot_sequence": sequence,
            "observed_at_unix_ms": 1_800_000_000_000 + sequence,
            "equity": equity,
            "positions": positions,
        }
        claim = subject.build_portfolio_snapshot_claim_v1(
            self.provider, **claim_kwargs
        )
        signer = self.provider_private if private_key is None else private_key
        public_spki = self.provider_spki if spki is None else spki
        signature = signer.sign(bytes.fromhex(claim["snapshot_claim_hash"]))
        signed = subject.build_signed_portfolio_snapshot_v1(
            claim,
            self.provider,
            public_key_spki_base64=_b64(public_spki),
            signature_base64=_b64(signature),
            expected_snapshot_claim_hash=claim["snapshot_claim_hash"],
            claim_build_kwargs=claim_kwargs,
        )
        evaluation_kwargs = {
            "public_key_spki_base64": _b64(public_spki),
            "signature_base64": _b64(signature),
            "expected_snapshot_claim_hash": claim["snapshot_claim_hash"],
            "expected_signed_snapshot_hash": signed["signed_snapshot_hash"],
            "claim_build_kwargs": claim_kwargs,
        }
        evidence = subject.evaluate_signed_portfolio_snapshot_v1(
            signed,
            claim,
            self.provider,
            **evaluation_kwargs,
        )
        return {
            "claim": claim,
            "signed": signed,
            "signature": signature,
            "evaluation_kwargs": evaluation_kwargs,
            "evidence": evidence,
        }

    def evaluate_v5(self, bundle, **overrides):
        kwargs = {
            "expected_snapshot_evidence_hash": bundle["evidence"][
                "snapshot_evidence_hash"
            ],
            "snapshot_evaluation_kwargs": bundle["evaluation_kwargs"],
            **self.increase_kwargs,
        }
        kwargs.update(overrides)
        return subject.evaluate_strategy_correlation_cluster_effective_bet_budget_v5(
            bundle["evidence"],
            bundle["signed"],
            bundle["claim"],
            self.provider,
            self.preregistration,
            self.matrix,
            self.audit,
            **kwargs,
        )

    def test_reproduces_v4_caller_equity_gap(self) -> None:
        base = {
            "strata_registration": self.strata_registration,
            "strata_gate": self.strata_gate,
            "complete_link_gate": self.complete_link_gate,
            "positions": self.positions,
            "proposed_symbol": "B",
            "proposed_notional": 2_500,
            "proposed_direction": "LONG",
            "risk_increasing": True,
        }
        actual = budget_v4.evaluate_strategy_correlation_cluster_effective_bet_budget_v4(
            self.preregistration,
            self.matrix,
            self.audit,
            equity=5_000,
            **base,
        )
        inflated = budget_v4.evaluate_strategy_correlation_cluster_effective_bet_budget_v4(
            self.preregistration,
            self.matrix,
            self.audit,
            equity=10_000,
            **base,
        )
        self.assertEqual(actual["status"], "BLOCK")
        self.assertEqual(inflated["status"], "PASS")
        self.assertFalse(
            inflated["facts"]["position_snapshot_provenance_verified"]
        )

    def test_provider_preregistration_is_exact_blocked_and_untrusted(self) -> None:
        self.assertEqual(self.provider["status"], "BLOCKED")
        self.assertTrue(
            self.provider["facts"]["local_preregistration_complete"]
        )
        self.assertFalse(
            self.provider["facts"]["snapshot_source_truth_verified"]
        )
        self.assertTrue(
            subject.verify_portfolio_snapshot_provider_preregistration_v1(
                self.provider, **self.provider_kwargs
            )
        )

    def test_signed_snapshot_is_local_signature_pass_only(self) -> None:
        evidence = self.high_equity_bundle["evidence"]
        self.assertEqual(evidence["status"], "PASS")
        self.assertTrue(
            evidence["facts"][
                "preregistered_provider_key_signature_verified"
            ]
        )
        for name in (
            "provider_identity_verified",
            "provider_implementation_verified",
            "snapshot_source_truth_verified",
            "snapshot_sequence_continuity_verified",
            "snapshot_freshness_verified",
        ):
            self.assertFalse(evidence["facts"][name], name)

    def test_signed_low_equity_snapshot_blocks_budget(self) -> None:
        document = self.evaluate_v5(self.low_equity_bundle)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn(
            "effective_budget_v4_decision_blocked",
            document["blockers"],
        )
        self.assertEqual(document["snapshot_summary"]["equity"], 5_000.0)

    def test_signed_high_equity_snapshot_passes_local_binding(self) -> None:
        document = self.evaluate_v5(self.high_equity_bundle)
        self.assertEqual(document["status"], "PASS")
        self.assertTrue(
            document["checks"]["snapshot_inputs_used_exclusively"]
        )
        self.assertFalse(document["facts"]["caller_equity_input_accepted"])
        self.assertFalse(document["facts"]["caller_positions_input_accepted"])
        self.assertFalse(
            document["facts"]["snapshot_source_truth_verified"]
        )
        self.assertEqual(document["admission_status"], "BLOCKED")

    def test_tampered_equity_claim_is_rejected(self) -> None:
        bundle = self.high_equity_bundle
        claim = deepcopy(bundle["claim"])
        claim["snapshot"]["equity"] = 100_000.0
        document = subject.evaluate_strategy_correlation_cluster_effective_bet_budget_v5(
            bundle["evidence"],
            bundle["signed"],
            claim,
            self.provider,
            self.preregistration,
            self.matrix,
            self.audit,
            expected_snapshot_evidence_hash=bundle["evidence"][
                "snapshot_evidence_hash"
            ],
            snapshot_evaluation_kwargs=bundle["evaluation_kwargs"],
            **self.increase_kwargs,
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertFalse(document["checks"]["snapshot_evidence_exact"])

    def test_wrong_key_self_signature_is_blocked(self) -> None:
        outsider = Ed25519PrivateKey.generate()
        bundle = self.build_snapshot_bundle(
            equity=10_000,
            positions=self.positions,
            sequence=9,
            label="outsider",
            private_key=outsider,
            spki=_spki(outsider),
        )
        self.assertEqual(bundle["evidence"]["status"], "BLOCK")
        self.assertFalse(
            bundle["evidence"]["facts"]["key_hash_matches_preregistration"]
        )

    def test_tampered_signature_is_blocked(self) -> None:
        bundle = self.high_equity_bundle
        kwargs = deepcopy(bundle["evaluation_kwargs"])
        kwargs["signature_base64"] = _b64(b"x" * 64)
        signed = subject.build_signed_portfolio_snapshot_v1(
            bundle["claim"],
            self.provider,
            public_key_spki_base64=kwargs["public_key_spki_base64"],
            signature_base64=kwargs["signature_base64"],
            expected_snapshot_claim_hash=bundle["claim"][
                "snapshot_claim_hash"
            ],
            claim_build_kwargs=kwargs["claim_build_kwargs"],
        )
        kwargs["expected_signed_snapshot_hash"] = signed[
            "signed_snapshot_hash"
        ]
        evidence = subject.evaluate_signed_portfolio_snapshot_v1(
            signed,
            bundle["claim"],
            self.provider,
            **kwargs,
        )
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertFalse(
            evidence["facts"]["cryptographic_signature_verified"]
        )

    def test_invalid_position_rows_fail_closed(self) -> None:
        cases = [
            self.positions + [deepcopy(self.positions[0])],
            [{"symbol": "A", "notional": True, "direction": "LONG"}],
            [{"symbol": "A", "notional": float("inf"), "direction": "LONG"}],
            [{"symbol": "A", "notional": 1_000, "direction": "FLAT"}],
        ]
        for positions in cases:
            with self.subTest(positions=positions):
                with self.assertRaises(
                    subject.SignedPortfolioSnapshotBudgetError
                ):
                    subject.build_portfolio_snapshot_claim_v1(
                        self.provider,
                        provider_preregistration_kwargs=self.provider_kwargs,
                        snapshot_id_hash=_hash("invalid-snapshot"),
                        snapshot_sequence=1,
                        observed_at_unix_ms=1_800_000_000_000,
                        equity=10_000,
                        positions=positions,
                    )

    def test_snapshot_sequence_time_and_equity_aliases_fail_closed(self) -> None:
        for overrides in (
            {"snapshot_sequence": True},
            {"observed_at_unix_ms": False},
            {"equity": True},
        ):
            kwargs = {
                "provider_preregistration_kwargs": self.provider_kwargs,
                "snapshot_id_hash": _hash("alias-snapshot"),
                "snapshot_sequence": 1,
                "observed_at_unix_ms": 1_800_000_000_000,
                "equity": 10_000,
                "positions": self.positions,
            }
            kwargs.update(overrides)
            with self.subTest(overrides=overrides):
                with self.assertRaises(
                    subject.SignedPortfolioSnapshotBudgetError
                ):
                    subject.build_portfolio_snapshot_claim_v1(
                        self.provider, **kwargs
                    )

    def test_provider_preregistration_drift_is_rejected(self) -> None:
        provider = deepcopy(self.provider)
        provider["identity"]["account_scope_hash"] = "0" * 64
        bundle = self.high_equity_bundle
        evidence = subject.evaluate_signed_portfolio_snapshot_v1(
            bundle["signed"],
            bundle["claim"],
            provider,
            **bundle["evaluation_kwargs"],
        )
        self.assertEqual(evidence["status"], "BLOCK")

    def test_signed_before_snapshot_binds_verified_risk_reduction(self) -> None:
        before = [
            {"symbol": "A", "notional": 2_500, "direction": "LONG"},
            {"symbol": "B", "notional": 1_000, "direction": "SHORT"},
        ]
        after = [
            {"symbol": "A", "notional": 2_000, "direction": "LONG"},
            {"symbol": "B", "notional": 1_000, "direction": "SHORT"},
        ]
        bundle = self.build_snapshot_bundle(
            equity=5_000,
            positions=before,
            sequence=10,
            label="reduction-before",
        )
        transition = budget_v4.build_strategy_correlation_cluster_risk_reduction_transition_v1(
            before,
            after,
            proposed_symbol="A",
            proposed_notional=500,
            proposed_direction="SHORT",
        )
        document = self.evaluate_v5(
            bundle,
            strata_registration=None,
            strata_gate=None,
            complete_link_gate=None,
            proposed_symbol="A",
            proposed_notional=500,
            proposed_direction="SHORT",
            risk_increasing=False,
            positions_after=after,
            risk_reduction_transition=transition,
        )
        self.assertEqual(document["status"], "PASS")
        self.assertTrue(
            document["budget_summary"]["verified_risk_reduction"]
        )

    def test_transition_from_different_before_snapshot_is_blocked(self) -> None:
        before = [
            {"symbol": "A", "notional": 3_000, "direction": "LONG"}
        ]
        after = [
            {"symbol": "A", "notional": 2_500, "direction": "LONG"}
        ]
        transition = budget_v4.build_strategy_correlation_cluster_risk_reduction_transition_v1(
            before,
            after,
            proposed_symbol="A",
            proposed_notional=500,
            proposed_direction="SHORT",
        )
        document = self.evaluate_v5(
            self.high_equity_bundle,
            strata_registration=None,
            strata_gate=None,
            complete_link_gate=None,
            proposed_symbol="A",
            proposed_notional=500,
            proposed_direction="SHORT",
            risk_increasing=False,
            positions_after=after,
            risk_reduction_transition=transition,
        )
        self.assertEqual(document["status"], "BLOCK")

    def test_exact_verifiers_reject_resealed_promotions(self) -> None:
        bundle = self.high_equity_bundle
        evidence = deepcopy(bundle["evidence"])
        evidence["facts"]["snapshot_source_truth_verified"] = True
        evidence = seal_strict_canonical_document(
            evidence, "snapshot_evidence_hash"
        )
        self.assertFalse(
            subject.verify_signed_portfolio_snapshot_evidence_v1(
                evidence,
                bundle["signed"],
                bundle["claim"],
                self.provider,
                expected_snapshot_evidence_hash=evidence[
                    "snapshot_evidence_hash"
                ],
                **bundle["evaluation_kwargs"],
            )
        )
        document = self.evaluate_v5(bundle)
        promoted = deepcopy(document)
        promoted["authority"]["current_admission_allowed"] = True
        promoted = seal_strict_canonical_document(
            promoted, "budget_v5_hash"
        )
        receipt = subject.verify_strategy_correlation_cluster_effective_bet_budget_v5(
            promoted,
            bundle["evidence"],
            bundle["signed"],
            bundle["claim"],
            self.provider,
            self.preregistration,
            self.matrix,
            self.audit,
            expected_snapshot_evidence_hash=bundle["evidence"][
                "snapshot_evidence_hash"
            ],
            snapshot_evaluation_kwargs=bundle["evaluation_kwargs"],
            **self.increase_kwargs,
        )
        self.assertEqual(receipt["status"], "BLOCK")

    def test_outputs_are_redacted_deterministic_and_inputs_immutable(self) -> None:
        bundle = self.high_equity_bundle
        before = deepcopy(
            [
                bundle["claim"],
                bundle["signed"],
                bundle["evidence"],
                self.provider,
            ]
        )
        first = self.evaluate_v5(bundle)
        second = self.evaluate_v5(bundle)
        self.assertEqual(first, second)
        encoded_evidence = json.dumps(bundle["evidence"], sort_keys=True)
        encoded_budget = json.dumps(first, sort_keys=True)
        self.assertNotIn('"positions":', encoded_evidence)
        self.assertNotIn('"positions":', encoded_budget)
        self.assertNotIn(_b64(self.provider_spki), encoded_evidence)
        self.assertNotIn(_b64(bundle["signature"]), encoded_evidence)
        self.assertEqual(
            before,
            [
                bundle["claim"],
                bundle["signed"],
                bundle["evidence"],
                self.provider,
            ],
        )

    def test_production_has_no_private_key_io_system_clock_or_runtime(self) -> None:
        source = Path(subject.__file__).read_text(encoding="utf-8")
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
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
