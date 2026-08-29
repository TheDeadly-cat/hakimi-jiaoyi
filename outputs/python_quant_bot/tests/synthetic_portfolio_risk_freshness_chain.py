from __future__ import annotations

import copy
from datetime import date, datetime, timedelta
import hashlib
import random

from exchange_terminal.services.portfolio_risk import build_correlation_matrix
from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    build_correlation_cluster_complete_link_audit,
    evaluate_correlation_cluster_gate_v2,
)
from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_cluster_preregistration,
    build_correlation_matrix_contract,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_adapter_v1 import (
    evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v1,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_adapter_v2 import (
    evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v2,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v1 import (
    build_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v1,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_legacy_matrix_derivation_binding_v1 import (
    build_strategy_correlation_cluster_portfolio_risk_legacy_matrix_derivation_binding_v1,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1 import (
    build_strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_session_freshness_v1 import (
    build_strategy_correlation_cluster_portfolio_risk_session_freshness_policy_registration_v1,
    evaluate_strategy_correlation_cluster_portfolio_risk_session_freshness_v1,
)
from exchange_terminal.services.strategy_correlation_cluster_stability import (
    evaluate_strategy_correlation_cluster_stability_gate,
)
from exchange_terminal.services.strategy_correlation_common_support_derivation_receipt_v1 import (
    build_correlation_common_support_derivation_receipt_v1,
)
from exchange_terminal.services.strategy_correlation_return_replay import (
    build_correlation_completed_price_input,
    build_correlation_matrix_replay,
)
from exchange_terminal.services.strategy_correlation_uncertainty_audit import (
    build_strategy_correlation_uncertainty_audit,
)
from exchange_terminal.services.strict_canonical_json_hash import strict_canonical_hash
from exchange_terminal.services.trusted_clock import build_trusted_clock_attestation
from tests import test_strategy_correlation_provider_dataset_content_attestation_v1 as provider_tests
from tests.test_strategy_correlation_cluster_temporal_stability import (
    StrategyCorrelationClusterTemporalStabilityTests,
)


class SyntheticCorrelatedPortfolioRiskFreshnessChain:
    """Reusable pure-synthetic three-symbol signed-content lineage."""

    def __init__(self) -> None:
        self.fixture = (
            provider_tests.StrategyCorrelationProviderDatasetContentAttestationV1Tests(
                methodName="runTest"
            )
        )
        self.fixture.setUp()
        self._closed = False
        self._build()

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self.fixture.doCleanups()

    def source_verifiers(self):
        return self.fixture.source_verifiers()

    @staticmethod
    def _clock_source(name: str, reference_ms: int) -> dict[str, object]:
        source = {
            "source": name,
            "endpoint": f"https://{name.lower()}.invalid/time",
            "status": "PASS",
            "error": "",
            "requested_at_ms": reference_ms - 10,
            "received_at_ms": reference_ms + 10,
            "round_trip_ms": 20,
            "midpoint_local_ms": reference_ms,
            "server_time_ms": reference_ms,
            "offset_ms": 0,
        }
        source["evidence_hash"] = strict_canonical_hash(source)
        return source

    @classmethod
    def clock(cls, reference_utc: str) -> dict[str, object]:
        reference = datetime.fromisoformat(reference_utc.replace("Z", "+00:00"))
        reference_ms = int(reference.timestamp() * 1000)
        sources = [
            cls._clock_source(f"CLOCK-{index + 1}", reference_ms)
            for index in range(2)
        ]
        return build_trusted_clock_attestation(
            local_now_ms=reference_ms,
            provider_evidence=sources,
            minimum_sources=2,
        )

    def _build(self) -> None:
        fixture = self.fixture
        source = fixture.source
        source.symbols = ["A", "B", "C"]
        for index, row in enumerate(source.batch_rows):
            a_value = row["returns"]["A"]
            b_noise = row["returns"]["B"]
            row["returns"]["B"] = 0.98 * a_value + 0.02 * b_noise
            row["returns"]["C"] = random.Random((index + 1) * 303).uniform(
                -0.01,
                0.01,
            )

        self.preregistration = build_correlation_cluster_preregistration(
            [
                {"cluster_id": "cluster-ab", "members": ["A", "B"]},
                {"cluster_id": "cluster-c", "members": ["C"]},
            ]
        )
        initial = (
            date.fromisoformat(source.batch_dates[0]) - timedelta(days=1)
        ).isoformat()
        payloads = {}
        manifests = []
        for symbol in source.symbols:
            price = 100.0
            rows = [{"date": initial, "close": price, "complete": True}]
            for batch_row in source.batch_rows:
                price *= 1.0 + batch_row["returns"][symbol]
                rows.append(
                    {
                        "date": batch_row["observation_date"],
                        "close": price,
                        "complete": True,
                    }
                )
            payloads[symbol] = {"source": source.provider_id, "rows": rows}
            manifests.append(
                {
                    "role": "SELECTION",
                    "symbol": symbol,
                    "timeframe": "1D",
                    "source": source.provider_id,
                    "data_hash": hashlib.sha256(
                        (symbol + "|v1").encode("ascii")
                    ).hexdigest(),
                    "row_count": len(rows),
                }
            )
        self.completed_price_input = build_correlation_completed_price_input(
            payloads,
            manifests,
            self.preregistration,
            cutoff_date=source.batch_dates[-1],
            selection_alignment_input_hash="d" * 64,
        )
        self.matrix_replay = build_correlation_matrix_replay(
            self.completed_price_input,
            self.preregistration,
        )
        self.derivation_receipt = (
            build_correlation_common_support_derivation_receipt_v1(
                self.matrix_replay
            )
        )
        source.matrix_replay = self.matrix_replay
        source.derivation_receipt = self.derivation_receipt
        source.calendar_document, source.calendar_bundle = source.calendar_evidence()
        source.provider_document, source.provider_bundle = source.provider_evidence()

        public_key = provider_tests._public_key_base64
        fixture.calendar_bundle = copy.deepcopy(source.calendar_bundle)
        fixture.calendar_bundle["batch_verification_context"] = {
            "signature_verification_context": {
                "attestation_receipt": {
                    "public_key_base64": public_key(fixture.timestamp_private_key)
                }
            }
        }
        fixture.provider_bundle = copy.deepcopy(source.provider_bundle)
        fixture.provider_bundle["identity_assertion_receipt"][
            "registry_public_key_base64"
        ] = public_key(fixture.registry_private_key)
        with fixture.source_verifiers():
            self.composition_document = provider_tests.composition_source.build_correlation_common_support_calendar_provider_composition_v1(
                self.derivation_receipt,
                self.matrix_replay,
                source.calendar_document,
                fixture.calendar_bundle,
                source.provider_document,
                fixture.provider_bundle,
            )
        self.composition_context = {
            "derivation_receipt": self.derivation_receipt,
            "matrix_replay": self.matrix_replay,
            "calendar_session_verification": source.calendar_document,
            "calendar_verification_bundle": fixture.calendar_bundle,
            "provider_identity_verification": source.provider_document,
            "provider_verification_bundle": fixture.provider_bundle,
        }
        fixture.composition_document = self.composition_document
        fixture.composition_context = self.composition_context
        fixture.registration = fixture.build_registration()
        fixture.receipt = fixture.build_receipt()
        with fixture.source_verifiers():
            self.dataset_attestation_verification = fixture.evaluate()

        self.legacy_matrix = build_correlation_matrix(
            {
                item["symbol"]: {"rows": item["price_rows"]}
                for item in self.completed_price_input["datasets"]
            },
            lookback=self.preregistration["lookback_observations"],
            minimum_overlap=self.preregistration["minimum_pair_overlap"],
        )
        self.legacy_context = {
            "legacy_correlation_matrix": self.legacy_matrix,
            "completed_price_input": self.completed_price_input,
            "matrix_replay": self.matrix_replay,
            "derivation_receipt": self.derivation_receipt,
            "composition_document": self.composition_document,
            "composition_context": self.composition_context,
            "dataset_attestation_verification": self.dataset_attestation_verification,
            "dataset_attestation_registration": fixture.registration,
            "provider_dataset_public_key_base64": fixture.dataset_public_key_base64,
            "dataset_attestation_receipt": fixture.receipt,
            "expected_registration_hash": fixture.registration["registration_hash"],
            "expected_attestation_hash": fixture.receipt["attestation_hash"],
        }
        with fixture.source_verifiers():
            self.legacy_binding = build_strategy_correlation_cluster_portfolio_risk_legacy_matrix_derivation_binding_v1(
                **self.legacy_context
            )

        self.uncertainty_audit = build_strategy_correlation_uncertainty_audit(
            self.matrix_replay
        )
        correlations = {}
        overlaps = {}
        for pair in self.uncertainty_audit["pairs"]:
            key = (pair["left_symbol"], pair["right_symbol"])
            correlations[key] = pair["correlation"]
            overlaps[key] = pair["overlap_observations"]
        self.adapter_matrix = build_correlation_matrix_contract(
            self.preregistration["symbols"],
            correlations,
            overlap_observations=overlaps,
        )
        self.selection_cells = [
            {
                "strategy_id": "S",
                "variant_id": "V",
                "lane": "RAW_EXCESS",
                "symbol": symbol,
                "gate_status": "PASS",
            }
            for symbol in self.preregistration["symbols"]
        ]
        self.complete_link_gate = evaluate_correlation_cluster_gate_v2(
            self.preregistration,
            self.adapter_matrix,
            self.selection_cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )
        self.full_stability_gate = evaluate_strategy_correlation_cluster_stability_gate(
            self.uncertainty_audit,
            self.complete_link_gate,
            preregistration=self.preregistration,
            correlation_matrix=self.adapter_matrix,
            selection_cells=self.selection_cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )
        temporal_globals = (
            StrategyCorrelationClusterTemporalStabilityTests._piecewise_gap.__globals__
        )
        self.temporal_stability_gate = temporal_globals[
            "evaluate_strategy_correlation_cluster_temporal_stability_gate"
        ](
            self.uncertainty_audit,
            self.full_stability_gate,
            complete_link_gate=self.complete_link_gate,
            preregistration=self.preregistration,
            correlation_matrix=self.adapter_matrix,
            selection_cells=self.selection_cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )
        complete_audit = build_correlation_cluster_complete_link_audit(
            self.preregistration,
            self.adapter_matrix,
        )
        legacy_correlations = {
            "pairs": {
                key: item["correlation"]
                for key, item in self.legacy_matrix["pairs"].items()
            }
        }
        self.adapter_v1_context = {
            "preregistration": self.preregistration,
            "cluster_correlation_matrix": self.adapter_matrix,
            "complete_link_audit": complete_audit,
            "equity": 10_000,
            "positions": [
                {"symbol": "A", "notional": 1_800, "direction": "LONG"},
                {"symbol": "C", "notional": 1_800, "direction": "LONG"},
            ],
            "proposed_symbol": "B",
            "proposed_notional": 500,
            "proposed_direction": "LONG",
            "proposed_cluster": "",
            "risk_increasing": True,
            "legacy_correlations": legacy_correlations,
            "regime": None,
            "legacy_limits": None,
            "max_cluster_gross_pct": 45.0,
        }
        self.adapter_v1_document = (
            evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v1(
                **self.adapter_v1_context
            )
        )
        self.temporal_context = {
            "source_uncertainty_audit": self.uncertainty_audit,
            "full_window_stability_gate": self.full_stability_gate,
            "complete_link_gate": self.complete_link_gate,
            "preregistration": self.preregistration,
            "correlation_matrix": self.adapter_matrix,
            "selection_cells": self.selection_cells,
            "strategy_id": "S",
            "variant_id": "V",
            "lane": "RAW_EXCESS",
        }
        self.adapter_v2_document = (
            evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v2(
                self.adapter_v1_document,
                self.temporal_stability_gate,
                adapter_v1_verification_context=self.adapter_v1_context,
                temporal_stability_verification_context=self.temporal_context,
            )
        )
        self.adapter_v2_context = {
            "adapter_v1_document": self.adapter_v1_document,
            "temporal_stability_gate": self.temporal_stability_gate,
            "adapter_v1_verification_context": self.adapter_v1_context,
            "temporal_stability_verification_context": self.temporal_context,
        }

        cutoff = self.completed_price_input["cutoff_date"]
        self.native_context = {
            "completed_price_input": self.completed_price_input,
            "matrix_replay": self.matrix_replay,
            "derivation_receipt": self.derivation_receipt,
            "composition_document": self.composition_document,
            "composition_context": self.composition_context,
            "expected_observation_cutoff_utc": f"{cutoff}T00:00:00Z",
        }
        with fixture.source_verifiers():
            self.native_manifest = build_strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1(
                **self.native_context
            )
        self.registration_inputs = {
            "native_cutoff_manifest": self.native_manifest,
            "native_cutoff_context": self.native_context,
            "expected_native_cutoff_manifest_hash": self.native_manifest[
                "manifest_hash"
            ],
            "max_completed_session_lag": 1,
            "declared_at_utc": "2026-09-18T00:00:00Z",
        }
        with fixture.source_verifiers():
            self.freshness_registration = build_strategy_correlation_cluster_portfolio_risk_session_freshness_policy_registration_v1(
                **self.registration_inputs
            )
        self.freshness_evaluation, self.freshness_context = self.build_freshness(
            "2026-12-21T00:00:00Z"
        )

    def build_freshness(self, reference_utc: str):
        clock = self.clock(reference_utc)
        with self.fixture.source_verifiers():
            evaluation = evaluate_strategy_correlation_cluster_portfolio_risk_session_freshness_v1(
                self.freshness_registration,
                registration_inputs=self.registration_inputs,
                trusted_clock_attestation=clock,
                expected_trusted_clock_attestation_hash=clock["attestation_hash"],
            )
        context = {
            "registration": self.freshness_registration,
            "registration_inputs": self.registration_inputs,
            "trusted_clock_attestation": clock,
            "expected_trusted_clock_attestation_hash": clock["attestation_hash"],
        }
        return evaluation, context

    def build_lineage_v1(self, *, freshness=None, freshness_context=None):
        freshness = self.freshness_evaluation if freshness is None else freshness
        freshness_context = (
            self.freshness_context
            if freshness_context is None
            else freshness_context
        )
        with self.fixture.source_verifiers():
            return build_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v1(
                self.adapter_v2_document,
                freshness,
                self.legacy_binding,
                adapter_v2_verification_context=self.adapter_v2_context,
                freshness_verification_context=freshness_context,
                legacy_matrix_binding_verification_context=self.legacy_context,
            )
