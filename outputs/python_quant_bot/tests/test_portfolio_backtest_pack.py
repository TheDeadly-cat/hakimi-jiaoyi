from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from exchange_terminal.services.portfolio_backtest_pack import (
    CURRENT_PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION,
    MAX_PORTFOLIO_COMPACT_CANDIDATE_BYTES,
    MAX_PORTFOLIO_INTERNAL_BACKTEST_PACK_BYTES,
    MAX_PORTFOLIO_SOURCE_BLOCKERS,
    PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION,
    PORTFOLIO_INTERNAL_BACKTEST_PACK_V3_SCHEMA_VERSION,
    PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
    PORTFOLIO_INTERNAL_BACKTEST_PACK_V5_SCHEMA_VERSION,
    PORTFOLIO_INTERNAL_BACKTEST_PACK_V6_SCHEMA_VERSION,
    PORTFOLIO_INTERNAL_FORWARD_EVIDENCE_V2_SCHEMA_VERSION,
    _build_v5_source_material,
    _assemble_internal_backtest_pack_v3,
    _assemble_internal_backtest_pack_v5,
    _verify_internal_backtest_pack_v6_structure,
    _project_forward_promotion_evidence,
    _research_source_document,
    _safe_detached_basename,
    _strict_json_object,
    _verify_research_source_document,
    assemble_internal_backtest_pack,
    build_internal_backtest_pack,
    required_internal_backtest_bundle_members,
    canonical_hash,
    execution_rehearsal_report_hash,
    research_batch_hash,
    statistical_audit_content,
    verify_execution_rehearsal_artifact,
    verify_forward_performance_artifact,
    verify_internal_backtest_pack,
    verify_internal_backtest_bundle,
    project_internal_forward_evidence,
    verify_internal_forward_evidence,
    verify_statistical_audit_artifact,
)
from exchange_terminal.services.portfolio_statistical_audit import (
    audit_portfolio_research_statistics,
)
from exchange_terminal.services.portfolio_forward_performance import (
    PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION,
    build_forward_performance_readiness,
)
from exchange_terminal.services.portfolio_forward_statistical_audit import (
    audit_forward_portfolio_statistics_v2,
    forward_statistical_audit_v2_content,
    verify_forward_portfolio_statistical_audit_v2_semantics,
)
from tests.test_portfolio_forward_statistical_audit import (
    frozen_candidate,
    performance_summary_from,
    synthetic_settlement_chain,
    verified_forward_audit,
    verified_historical_audit,
)
from tests.test_backtest_return_quality import (
    research_report as quality_research_report,
)
from tests.portfolio_governance_fixtures import (
    attested_clock,
)


CANDIDATE_HASH = "c" * 64
RESEARCH_HASH = "r" * 64
RESEARCH_FILE_HASH = "f" * 64


def rehearsal() -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "portfolio-internal-execution-rehearsal-v1",
        "status": "PASS",
        "source_batch_run_hash": RESEARCH_HASH,
        "source_candidate_hash": CANDIDATE_HASH,
        "checks": {
            "source_report_research_only": True,
            "all_stage_rehearsals_pass": True,
            "all_stage_rehearsals_deterministic": True,
        },
        "determinism": {"test": {"status": "PASS"}},
        "stages": {"test": {"status": "PASS", "generated_at": 10}},
        "stage_summary": {"test": {"status": "PASS"}},
        "interpretation": "test",
        "isolated_in_memory": True,
        "network_accessed": False,
        "production_runtime_mutated": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["report_hash"] = execution_rehearsal_report_hash(payload)
    payload["generated_at"] = 100
    payload["source_research_report"] = "research.json"
    payload["source_research_file_sha256"] = RESEARCH_FILE_HASH
    payload["active_candidate_registry"] = "active.json"
    payload["active_candidate_hash"] = CANDIDATE_HASH
    payload["artifact_hash"] = canonical_hash(payload)
    return payload


def statistical_research_report() -> dict[str, object]:
    return {
        "batch_run_hash": RESEARCH_HASH,
        "spec_hash": "s" * 64,
        "spec": {"trial_count": 4},
        "dataset_manifest": {"data_hash": "d" * 64},
        "frozen_candidate": {"candidate_hash": CANDIDATE_HASH},
        "validation": {
            "run_hash": "v" * 64,
            "initial_cash": 100_000.0,
            "equity_curve": [],
        },
        "validation_benchmark": {
            "benchmark_run_hash": "b" * 64,
            "initial_cash": 100_000.0,
            "equity_curve": [],
        },
        "test": {
            "run_hash": "t" * 64,
            "initial_cash": 100_000.0,
            "equity_curve": [],
        },
        "test_benchmark": {
            "benchmark_run_hash": "m" * 64,
            "initial_cash": 100_000.0,
            "equity_curve": [],
        },
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def statistical_audit() -> dict[str, object]:
    payload = audit_portfolio_research_statistics(
        statistical_research_report(),
        generated_at=100,
    )
    payload["source_research_report"] = "research.json"
    payload["source_research_file_sha256"] = RESEARCH_FILE_HASH
    payload["active_candidate_registry"] = "active.json"
    payload["active_candidate_hash"] = CANDIDATE_HASH
    payload["artifact_hash"] = canonical_hash(payload)
    return payload


def sealed_pack() -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION,
        "status": "INTERNAL_BACKTEST_EVIDENCE_READY",
        "promotion_status": "BLOCK",
        "blockers": [],
        "promotion_blockers": ["minimum_forward_outcomes"],
        "checks": {"all_evidence": True},
        "generated_at": 100,
        "source_mode": "FROZEN_ARTIFACT_VERIFICATION_ONLY",
        "parameter_selection_allowed": False,
        "automatic_paper_activation_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    evidence = deepcopy(payload)
    evidence.pop("generated_at")
    payload["evidence_hash"] = canonical_hash(evidence)
    payload["pack_hash"] = canonical_hash(payload)
    return payload


def reseal_pack(payload: dict[str, object]) -> dict[str, object]:
    payload.pop("pack_hash", None)
    payload.pop("evidence_hash", None)
    evidence = deepcopy(payload)
    evidence.pop("generated_at", None)
    payload["evidence_hash"] = canonical_hash(evidence)
    payload["pack_hash"] = canonical_hash(payload)
    return payload


def forward_projection(*, outcomes: int, required: int, weak_edge: bool = False) -> dict[str, object]:
    frozen = frozen_candidate(outcomes=required, rebalances=required)
    historical = verified_historical_audit(frozen, claim_status="BLOCK")
    settlements = synthetic_settlement_chain(outcomes, weak_edge=weak_edge)
    audit = verified_forward_audit(frozen, settlements, historical)
    summary = performance_summary_from(settlements)
    readiness = build_forward_performance_readiness(
        candidate=frozen,
        shadow_audit={"status": "PASS", "valid_observation_count": len(settlements)},
        performance_summary=summary,
        historical_statistical_audit=historical,
        forward_statistical_audit=audit,
        readiness_schema_version=PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION,
    )
    historical_verification = {
        "status": "PASS",
        "semantic_verification": {
            "status": "PASS",
            "claim_status": "BLOCK",
            "expected_status": "BLOCK",
            "expected_conclusion": historical["conclusion"],
            "expected_audit_hash": historical["audit_hash"],
            "recomputed_from_frozen_research": True,
        },
    }
    return _project_forward_promotion_evidence(
        candidate=frozen,
        statistical=historical,
        statistical_verification=historical_verification,
        performance={
            "performance": summary,
            "readiness": readiness,
            "forward_statistical_audit": audit,
        },
    )


def forward_projection_v2(
    *,
    outcomes: int,
    required: int,
    weak_edge: bool = False,
) -> dict[str, object]:
    frozen = frozen_candidate(outcomes=required, rebalances=required)
    historical = verified_historical_audit(frozen, claim_status="BLOCK")
    settlements = synthetic_settlement_chain(outcomes, weak_edge=weak_edge)
    summary = performance_summary_from(settlements)
    report = audit_forward_portfolio_statistics_v2(
        candidate=frozen,
        settlements=settlements,
        historical_statistical_audit=historical,
        generated_at=100,
    )
    verification = verify_forward_portfolio_statistical_audit_v2_semantics(
        report,
        candidate=frozen,
        settlements=settlements,
        historical_statistical_audit=historical,
    )
    audit = {
        **report,
        "verification_status": verification["status"],
        "verification_blockers": list(verification["blockers"]),
        "semantic_recomputed": verification[
            "recomputed_from_verified_forward_settlements"
        ],
    }
    readiness = build_forward_performance_readiness(
        candidate=frozen,
        shadow_audit={"status": "PASS", "valid_observation_count": len(settlements)},
        performance_summary=summary,
        historical_statistical_audit=historical,
        forward_statistical_audit=audit,
        readiness_schema_version=PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION,
    )
    historical_verification = {
        "status": "PASS",
        "semantic_verification": {
            "status": "PASS",
            "claim_status": "BLOCK",
            "expected_status": "BLOCK",
            "expected_conclusion": historical["conclusion"],
            "expected_audit_hash": historical["audit_hash"],
            "recomputed_from_frozen_research": True,
        },
    }
    return project_internal_forward_evidence(
        candidate=frozen,
        statistical=historical,
        statistical_verification=historical_verification,
        performance={
            "performance": summary,
            "readiness": readiness,
            "forward_statistical_audit": audit,
        },
        schema_version=PORTFOLIO_INTERNAL_FORWARD_EVIDENCE_V2_SCHEMA_VERSION,
    )


def sealed_v3_pack(projection: dict[str, object]) -> dict[str, object]:
    candidate = dict(projection["candidate"])
    forward_status = str(projection["forward_evidence_status"])
    evidence_blockers = list(projection["blockers"])
    payload: dict[str, object] = {
        "schema_version": PORTFOLIO_INTERNAL_BACKTEST_PACK_V3_SCHEMA_VERSION,
        "status": "INTERNAL_BACKTEST_EVIDENCE_READY",
        "promotion_status": (
            "REVIEW_REQUIRED" if forward_status == "RESEARCH_REVIEW_READY" else "BLOCK"
        ),
        "forward_evidence_status": forward_status,
        "blockers": [],
        "promotion_blockers": evidence_blockers,
        "checks": {
            "all_evidence": True,
            "forward_statistical_evidence_source_integrity_pass": True,
        },
        "candidate": {
            "candidate_hash": candidate["candidate_hash"],
            "spec": candidate["spec"],
            "declared_spec_hash": candidate["declared_spec_hash"],
            "computed_spec_hash": candidate["computed_spec_hash"],
        },
        "forward_promotion_evidence": projection,
        "generated_at": 100,
        "source_mode": "FROZEN_ARTIFACT_VERIFICATION_ONLY",
        "parameter_selection_allowed": False,
        "automatic_paper_activation_allowed": False,
        "profitability_proven": False,
        "performance_claim_proven": False,
        "manual_review_required": True,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return reseal_pack(payload)


def v4_evidence() -> dict[str, object]:
    research = quality_research_report()
    research["schema_version"] = "portfolio-backtest-v1"
    research["spec"]["research_generation"] = "PORTFOLIO_SYNTHETIC_V4"
    research["spec"]["research_protocol_hash"] = "9" * 64
    research["spec_hash"] = canonical_hash(research["spec"])
    research["dataset_manifest"] = {
        "status": "PASS",
        "data_hash": "d" * 64,
    }
    research["frozen_candidate"] = {"candidate_hash": CANDIDATE_HASH}
    for stage_name, end_equity in (("validation", 108_000.0), ("test", 106_000.0)):
        stage = research[stage_name]
        stage["initial_cash"] = 100_000.0
        stage["equity_curve"] = [
            {"date": "2026-01-02", "equity": 100_000.0},
            {"date": "2026-01-05", "equity": end_equity},
        ]
        stage["evaluation_window"] = {
            "start": "2026-01-02",
            "end": "2026-01-05",
            "evaluated_rows": 2,
        }
        stage["final_equity"] = end_equity
        stage["run_spec"] = {
            "stage": stage_name,
            "fee_rate": research["spec"]["fee_rate"],
            "slippage_bps": research["spec"]["slippage_bps"],
        }
        stage["max_drawdown_pct"] = 0.0
        stage["run_hash"] = canonical_hash(stage["run_spec"])
        benchmark = research[f"{stage_name}_benchmark"]
        benchmark["initial_cash"] = 100_000.0
        benchmark["equity_curve"] = [
            {"date": "2026-01-02", "equity": 100_000.0},
            {
                "date": "2026-01-05",
                "equity": 105_000.0 if stage_name == "validation" else 104_000.0,
            },
        ]
        benchmark["evaluation_window"] = {
            "start": "2026-01-02",
            "end": "2026-01-05",
            "evaluated_rows": 2,
        }
        benchmark["max_drawdown_pct"] = 0.0
        benchmark["final_equity"] = benchmark["equity_curve"][-1]["equity"]
        benchmark["run_spec"] = {"stage": stage_name, "benchmark": "SPY"}
        benchmark["benchmark_run_hash"] = canonical_hash(benchmark)
    research["full"] = {"run_hash": "7" * 64}
    for index, scenario in enumerate(research["cost_stress"], start=1):
        scenario["initial_cash"] = 100_000.0
        scenario["final_equity"] = 100_000.0 * (1.0 + scenario["total_return_pct"] / 100.0)
        scenario["max_drawdown_pct"] = 0.0
        scenario["equity_curve"] = [
            {"date": "2026-01-02", "equity": 100_000.0},
            {"date": "2026-01-05", "equity": scenario["final_equity"]},
        ]
        scenario["evaluation_window"] = {
            "start": "2026-01-02",
            "end": "2026-01-05",
            "evaluated_rows": 2,
        }
        scenario["run_spec"] = {
            "label": scenario["label"],
            "fee_rate": scenario["fee_rate"],
            "slippage_bps": scenario["slippage_bps"],
        }
        scenario["run_hash"] = canonical_hash(scenario["run_spec"])
    research["causal_audit"] = {"status": "PASS"}
    research["correlation_matrix"] = {"status": "PASS", "matrix_hash": "8" * 64}
    research["batch_run_hash"] = research_batch_hash(research)

    research_text = json.dumps(research, ensure_ascii=False, indent=2)
    research_bytes = research_text.encode("utf-8")

    candidate = {
        "candidate_id": "PORTFOLIO_SYNTHETIC_V4",
        "candidate_hash": CANDIDATE_HASH,
        "research_report_hash": research["batch_run_hash"],
        "spec": deepcopy(research["spec"]),
        "spec_hash": research["spec_hash"],
        "dataset_hash": research["dataset_manifest"]["data_hash"],
        "implementation": {"fingerprint": "e" * 64},
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    statistical = audit_portfolio_research_statistics(research, generated_at=100)
    projection = forward_projection(outcomes=10, required=10)
    base = sealed_v3_pack(projection)
    clock = attested_clock(1_000_000)
    receipt = {
        "schema_version": "portfolio-experiment-completion-v1",
        "status": "COMPLETED",
        "experiment_id": "pexp-v4",
        "intent_hash": "a" * 64,
        "protocol_hash": research["spec"]["research_protocol_hash"],
        "binding_hash": "b" * 64,
        "batch_run_hash": research["batch_run_hash"],
        "dataset_hash": research["dataset_manifest"]["data_hash"],
        "report_file": "research.json",
        "report_path": "C:/synthetic/research.json",
        "report_file_sha256": hashlib.sha256(research_bytes).hexdigest(),
        "candidate_file": "",
        "candidate_path": "",
        "candidate_file_sha256": "",
        "candidate_hash": CANDIDATE_HASH,
        "completed_at": 1_000_000,
        "completion_clock_attestation_hash": clock["attestation_hash"],
        "completion_clock_attestation": clock,
        "artifact_policy": "CONTENT_ADDRESSED_LOCAL_REPORTS",
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
        "completion_event_hash": "c" * 64,
    }
    receipt["receipt_hash"] = canonical_hash(receipt)
    registry = {
        "schema_version": "active-portfolio-candidate-v1",
        "status": "ACTIVE_RESEARCH_CANDIDATE",
        "candidate_file": "candidate.json",
        "candidate_file_sha256": "f" * 64,
        "candidate_hash": CANDIDATE_HASH,
        "dataset_hash": research["dataset_manifest"]["data_hash"],
        "experiment_completion_receipt_hash": receipt["receipt_hash"],
        "experiment_completion_receipt": receipt,
        "selection_policy": "EXPLICIT_LOCAL_ACTIVATION_ONLY",
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    registry["registry_hash"] = canonical_hash(registry)
    source_document = {
        "schema_version": "portfolio-research-source-document-v1",
        "encoding": "UTF-8_JSON_OBJECT_EXACT_BYTES_V1",
        "byte_length": len(research_bytes),
        "sha256": hashlib.sha256(research_bytes).hexdigest(),
        "payload": research_text,
        "internal_verification_only": True,
        "public_projection_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    source_document["document_hash"] = canonical_hash(source_document)
    return {
        "active": {
            "candidate": candidate,
            "registry": registry,
        },
        "research": research,
        "research_artifact": {
            "file": "research.json",
            "file_sha256": hashlib.sha256(research_bytes).hexdigest(),
            "size": len(research_bytes),
        },
        "research_source_document": source_document,
        "statistical": statistical,
        "performance": {
            "performance": projection["performance_summary"],
            "readiness": projection["readiness"],
            "forward_statistical_audit": projection["forward_statistical_audit"],
        },
        "_base": base,
    }


def rebuild_self_signed_research_chain(evidence: dict[str, object]) -> None:
    research = evidence["research"]
    candidate = evidence["active"]["candidate"]
    registry = evidence["active"]["registry"]
    research["batch_run_hash"] = research_batch_hash(research)
    candidate["research_report_hash"] = research["batch_run_hash"]
    evidence["statistical"] = audit_portfolio_research_statistics(research, generated_at=100)
    registry["experiment_completion_receipt"]["batch_run_hash"] = research["batch_run_hash"]
    receipt_content = deepcopy(registry["experiment_completion_receipt"])
    receipt_content.pop("receipt_hash", None)
    registry["experiment_completion_receipt"]["receipt_hash"] = canonical_hash(receipt_content)
    registry["experiment_completion_receipt_hash"] = registry[
        "experiment_completion_receipt"
    ]["receipt_hash"]
    registry_content = deepcopy(registry)
    registry_content.pop("registry_hash", None)
    registry["registry_hash"] = canonical_hash(registry_content)


def v5_bundle() -> tuple[dict[str, object], list[dict[str, object]]]:
    evidence = v4_evidence()
    pack = assemble_internal_backtest_pack(
        evidence,
        generated_at=100,
        schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_V5_SCHEMA_VERSION,
    )
    detached_artifacts = _build_v5_source_material(evidence)[2]
    return pack, detached_artifacts


def sealed_v6_pack(projection: dict[str, object]) -> dict[str, object]:
    pack, _detached = v5_bundle()
    payload = deepcopy(pack)
    payload["schema_version"] = PORTFOLIO_INTERNAL_BACKTEST_PACK_V6_SCHEMA_VERSION
    projected_candidate = dict(projection["candidate"])
    payload["candidate"].update({
        "candidate_hash": projected_candidate["candidate_hash"],
        "spec": projected_candidate["spec"],
        "declared_spec_hash": projected_candidate["declared_spec_hash"],
        "computed_spec_hash": projected_candidate["computed_spec_hash"],
    })
    payload["forward_promotion_evidence"] = deepcopy(projection)
    payload["forward_evidence_status"] = projection["forward_evidence_status"]
    payload["checks"]["forward_statistical_evidence_source_integrity_pass"] = True
    payload["blockers"] = [
        item
        for item in payload["blockers"]
        if not str(item).startswith("forward_statistical_evidence:")
    ]
    internal_ready = all(payload["checks"].values()) and not payload["blockers"]
    payload["status"] = (
        "INTERNAL_BACKTEST_EVIDENCE_READY"
        if internal_ready
        else "INTERNAL_BACKTEST_BLOCKED"
    )
    payload["promotion_blockers"] = list(projection["blockers"])
    if not internal_ready:
        payload["promotion_blockers"].append("internal_backtest_evidence_ready")
    payload["promotion_blockers"] = list(dict.fromkeys(payload["promotion_blockers"]))
    payload["promotion_status"] = (
        "REVIEW_REQUIRED"
        if internal_ready
        and projection["forward_evidence_status"] == "RESEARCH_REVIEW_READY"
        and not payload["promotion_blockers"]
        else "BLOCK"
    )
    return reseal_pack(payload)


class PortfolioBacktestPackTests(unittest.TestCase):
    def test_v2_forward_projection_freezes_first_due_decision_across_tail(self) -> None:
        first_due = forward_projection_v2(outcomes=8, required=8)
        with_tail = forward_projection_v2(outcomes=12, required=8)

        first_verification = verify_internal_forward_evidence(first_due)
        tail_verification = verify_internal_forward_evidence(with_tail)
        self.assertEqual(first_verification["status"], "PASS")
        self.assertEqual(tail_verification["status"], "PASS")
        self.assertEqual(first_due["forward_evidence_status"], "RESEARCH_REVIEW_READY")
        self.assertEqual(with_tail["forward_evidence_status"], "RESEARCH_REVIEW_READY")
        first_audit = first_due["forward_statistical_audit"]
        tail_audit = with_tail["forward_statistical_audit"]
        for field in ("decision_hash", "stage_hash", "risk_acceptance_hash"):
            self.assertEqual(
                first_audit["decision_window"][field],
                tail_audit["decision_window"][field],
            )
        self.assertEqual(
            first_audit["decision_window"]["first_joint_maturity_prefix"],
            tail_audit["decision_window"]["first_joint_maturity_prefix"],
        )
        self.assertNotEqual(
            first_audit["series_evidence"]["series_hash"],
            tail_audit["series_evidence"]["series_hash"],
        )
        self.assertFalse(tail_audit["decision_window"]["later_settlements_used"])

    def test_v2_forward_projection_blocks_missing_unknown_or_mixed_risk(self) -> None:
        original = forward_projection_v2(outcomes=8, required=8)

        def missing(payload: dict[str, object]) -> None:
            payload["forward_statistical_audit"]["decision_window"].pop(
                "risk_acceptance"
            )

        def unknown(payload: dict[str, object]) -> None:
            payload["forward_statistical_audit"]["decision_window"][
                "risk_acceptance"
            ]["status"] = "UNKNOWN"

        def mixed(payload: dict[str, object]) -> None:
            payload["forward_statistical_audit"]["decision_window"][
                "risk_acceptance"
            ]["status"] = "BLOCK"

        for label, mutate in (("missing", missing), ("unknown", unknown), ("mixed", mixed)):
            with self.subTest(label=label):
                tampered = deepcopy(original)
                mutate(tampered)
                projection_content = deepcopy(tampered)
                projection_content.pop("projection_hash", None)
                tampered["projection_hash"] = canonical_hash(projection_content)
                verification = verify_internal_forward_evidence(tampered)
                self.assertEqual(verification["status"], "BLOCK")
                self.assertEqual(verification["source_integrity_status"], "BLOCK")
                self.assertTrue(
                    any(
                        "risk" in item or "decision" in item
                        for item in verification.get("source_blockers") or []
                    ),
                    verification,
                )

    def test_v2_forward_projection_accepts_collecting_and_frozen_block_states(self) -> None:
        collecting = forward_projection_v2(outcomes=7, required=8)
        blocked = forward_projection_v2(outcomes=8, required=8, weak_edge=True)
        blocked_with_tail = forward_projection_v2(
            outcomes=12,
            required=8,
            weak_edge=True,
        )

        for projection, expected in (
            (collecting, "COLLECTING"),
            (blocked, "RESEARCH_REVIEW_BLOCKED"),
            (blocked_with_tail, "RESEARCH_REVIEW_BLOCKED"),
        ):
            verification = verify_internal_forward_evidence(projection)
            self.assertEqual(verification["status"], "PASS")
            self.assertEqual(verification["source_integrity_status"], "PASS")
            self.assertEqual(projection["forward_evidence_status"], expected)
        self.assertEqual(
            blocked["forward_statistical_audit"]["decision_window"]["decision_hash"],
            blocked_with_tail["forward_statistical_audit"]["decision_window"][
                "decision_hash"
            ],
        )
        self.assertEqual(
            blocked["forward_statistical_audit"]["decision_window"]["research_action"],
            "STOP_RESEARCH",
        )

    def test_v2_forward_projection_cross_bindings_fail_closed(self) -> None:
        original = forward_projection_v2(outcomes=12, required=8)

        def audit_version(payload: dict[str, object]) -> None:
            payload["forward_statistical_audit"]["schema_version"] = (
                "portfolio-forward-statistical-audit-v1"
            )

        def readiness_version(payload: dict[str, object]) -> None:
            payload["readiness"]["schema_version"] = "portfolio-forward-readiness-v2"

        def first_due(payload: dict[str, object]) -> None:
            payload["forward_statistical_audit"]["decision_window"][
                "first_joint_maturity_prefix"
            ]["first_due_settlement_hash"] = "f" * 64

        def stage_hash(payload: dict[str, object]) -> None:
            payload["forward_statistical_audit"]["stage"]["stage_hash"] = "e" * 64

        def full_series_hash(payload: dict[str, object]) -> None:
            payload["forward_statistical_audit"]["series_evidence"]["series_hash"] = (
                "d" * 64
            )

        for label, mutate in (
            ("audit_version", audit_version),
            ("readiness_version", readiness_version),
            ("first_due", first_due),
            ("stage_hash", stage_hash),
            ("full_series_hash", full_series_hash),
        ):
            with self.subTest(label=label):
                tampered = deepcopy(original)
                mutate(tampered)
                projection_content = deepcopy(tampered)
                projection_content.pop("projection_hash", None)
                tampered["projection_hash"] = canonical_hash(projection_content)
                verification = verify_internal_forward_evidence(tampered)
                self.assertEqual(verification["status"], "BLOCK")
                self.assertEqual(verification["source_integrity_status"], "BLOCK")
                self.assertTrue(verification.get("source_blockers"), verification)

    def test_v2_coherent_reseal_cannot_override_audit_receipt_semantics(self) -> None:
        original = forward_projection_v2(outcomes=8, required=8)

        def check_false(payload: dict[str, object]) -> None:
            payload["forward_statistical_audit"]["checks"][
                "settlement_series_integrity_pass"
            ] = False

        def blockers_drift(payload: dict[str, object]) -> None:
            payload["forward_statistical_audit"]["blockers"] = [
                "settlement_series_integrity_invalid"
            ]

        def status_flip(payload: dict[str, object]) -> None:
            payload["forward_statistical_audit"]["status"] = "BLOCK"
            payload["forward_statistical_audit"]["conclusion"] = (
                "FORWARD_FIRST_JOINT_MATURITY_RESEARCH_ACCEPTANCE_FAILED"
            )

        def contract_drift(payload: dict[str, object]) -> None:
            comparison = payload["forward_statistical_audit"]["contract_comparison"]
            comparison["copied_fields"]["method"]["matches"] = False
            comparison["other_differences_allowed"] = True

        for label, mutate in (
            ("check_false", check_false),
            ("blockers_drift", blockers_drift),
            ("status_flip", status_flip),
            ("contract_drift", contract_drift),
        ):
            with self.subTest(label=label):
                tampered = deepcopy(original)
                mutate(tampered)
                audit = tampered["forward_statistical_audit"]
                audit["audit_hash"] = canonical_hash(
                    forward_statistical_audit_v2_content(audit)
                )
                readiness_audit = tampered["readiness"]["forward_statistical_audit"]
                for field in (
                    "status",
                    "conclusion",
                    "audit_hash",
                    "contract_comparison",
                ):
                    readiness_audit[field] = deepcopy(audit[field])
                projection_content = deepcopy(tampered)
                projection_content.pop("projection_hash", None)
                tampered["projection_hash"] = canonical_hash(projection_content)

                verification = verify_internal_forward_evidence(tampered)

                self.assertEqual(verification["status"], "BLOCK", verification)
                self.assertEqual(
                    verification["source_integrity_status"],
                    "BLOCK",
                    verification,
                )
                self.assertTrue(verification.get("source_blockers"), verification)

    def test_v2_receipt_safety_boundaries_fail_closed(self) -> None:
        original = forward_projection_v2(outcomes=8, required=8)
        cases: list[tuple[str, dict[str, object]]] = []
        unsafe_integer = deepcopy(original)
        unsafe_integer["forward_statistical_audit"]["generated_at"] = (
            9_007_199_254_740_992
        )
        cases.append(("unsafe_integer", unsafe_integer))
        nonfinite = deepcopy(original)
        nonfinite["forward_statistical_audit"]["generated_at"] = float("nan")
        cases.append(("nonfinite", nonfinite))
        authority = deepcopy(original)
        authority["nested_authority"] = {"live-order-allowed": True}
        cases.append(("authority", authority))

        for label, tampered in cases:
            with self.subTest(label=label):
                projection_content = deepcopy(tampered)
                projection_content.pop("projection_hash", None)
                tampered["projection_hash"] = canonical_hash(projection_content)
                verification = verify_internal_forward_evidence(tampered)
                self.assertEqual(verification["status"], "BLOCK", verification)
                self.assertEqual(
                    verification["source_integrity_status"],
                    "BLOCK",
                    verification,
                )

        cyclic = deepcopy(original)
        cyclic["cycle"] = cyclic
        cycle_verification = verify_internal_forward_evidence(cyclic)
        self.assertEqual(cycle_verification["status"], "BLOCK")
        self.assertEqual(cycle_verification["source_integrity_status"], "BLOCK")

    def test_v6_pack_is_current_and_requires_v2_forward_evidence(self) -> None:
        self.assertEqual(
            CURRENT_PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION,
            "portfolio-internal-backtest-pack-v6",
        )
        projection = forward_projection_v2(outcomes=12, required=8)
        pack = sealed_v6_pack(projection)
        structure = _verify_internal_backtest_pack_v6_structure(pack)
        pack_only = verify_internal_backtest_pack(pack)

        self.assertEqual(pack["schema_version"], PORTFOLIO_INTERNAL_BACKTEST_PACK_V6_SCHEMA_VERSION)
        self.assertEqual(structure["status"], "PASS")
        self.assertEqual(pack_only["status"], "BLOCK")
        self.assertIn("detached_artifacts_required", pack_only["blockers"])
        self.assertEqual(
            [item["role"] for item in required_internal_backtest_bundle_members(pack)],
            ["RESEARCH_REPORT", "STATISTICAL_AUDIT"],
        )

        mixed = deepcopy(pack)
        mixed["forward_promotion_evidence"] = forward_projection(
            outcomes=8,
            required=8,
        )
        mixed = reseal_pack(mixed)
        mixed_verification = _verify_internal_backtest_pack_v6_structure(mixed)
        self.assertEqual(mixed_verification["status"], "BLOCK")
        self.assertTrue(
            any("forward" in item for item in mixed_verification["blockers"]),
            mixed_verification,
        )

    def test_v6_pack_verifier_never_recomputes_statistical_bootstrap(self) -> None:
        pack = sealed_v6_pack(forward_projection_v2(outcomes=12, required=8))
        with patch(
            "exchange_terminal.services.portfolio_forward_statistical_audit."
            "audit_paired_equity_curve_stage",
            side_effect=AssertionError("pack verifier must not run bootstrap"),
        ) as bootstrap:
            verification = _verify_internal_backtest_pack_v6_structure(pack)

        self.assertEqual(verification["status"], "PASS")
        bootstrap.assert_not_called()

    def test_v6_builder_is_default_while_v5_remains_explicit_legacy(self) -> None:
        evidence = v4_evidence()
        current = assemble_internal_backtest_pack(evidence, generated_at=100)
        legacy = assemble_internal_backtest_pack(
            evidence,
            generated_at=100,
            schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_V5_SCHEMA_VERSION,
        )

        self.assertEqual(
            current["schema_version"],
            CURRENT_PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION,
        )
        self.assertEqual(
            legacy["schema_version"],
            PORTFOLIO_INTERNAL_BACKTEST_PACK_V5_SCHEMA_VERSION,
        )
        self.assertEqual(
            current["forward_promotion_evidence"]["schema_version"],
            PORTFOLIO_INTERNAL_FORWARD_EVIDENCE_V2_SCHEMA_VERSION,
        )
        detached = _build_v5_source_material(evidence)[2]
        bundle = verify_internal_backtest_bundle(current, detached)
        missing = verify_internal_backtest_bundle(current, detached[:1])
        self.assertEqual(bundle["status"], "PASS")
        self.assertEqual(bundle["artifact_contract_status"], "PASS")
        self.assertEqual(missing["status"], "BLOCK")
        self.assertIn(
            "detached_artifact_missing:STATISTICAL_AUDIT",
            missing["blockers"],
        )

    def test_v5_compact_bundle_verifies_only_with_exact_detached_members(self) -> None:
        pack, detached_artifacts = v5_bundle()

        pack_only = verify_internal_backtest_pack(pack)
        bundle = verify_internal_backtest_bundle(pack, detached_artifacts)

        self.assertEqual(
            pack["schema_version"],
            PORTFOLIO_INTERNAL_BACKTEST_PACK_V5_SCHEMA_VERSION,
        )
        self.assertEqual(pack["return_quality"]["schema_version"], "backtest-return-quality-v3")
        self.assertEqual(pack_only["status"], "BLOCK")
        self.assertIn("detached_artifacts_required", pack_only["blockers"])
        self.assertEqual(bundle["status"], "PASS")
        self.assertTrue(bundle["numeric_claims_available"])
        self.assertEqual(
            [item["role"] for item in required_internal_backtest_bundle_members(pack)],
            ["RESEARCH_REPORT", "STATISTICAL_AUDIT"],
        )

        forbidden: list[str] = []

        def visit(value: object) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    if key in {
                        "return_quality_source_evidence",
                        "research_source_document",
                        "source_result",
                        "equity_curve",
                    }:
                        forbidden.append(key)
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(pack)
        self.assertEqual(forbidden, [])

    def test_v5_detached_drift_or_missing_member_blocks_and_redacts(self) -> None:
        pack, detached_artifacts = v5_bundle()
        missing = verify_internal_backtest_bundle(pack, detached_artifacts[:1])
        drifted = deepcopy(detached_artifacts)
        drifted[0]["raw_bytes"] = drifted[0]["raw_bytes"] + b" "

        drift = verify_internal_backtest_bundle(pack, drifted)

        self.assertEqual(missing["status"], "BLOCK")
        self.assertFalse(missing["numeric_claims_available"])
        self.assertEqual(missing["return_quality"], {})
        self.assertIn(
            "detached_artifact_missing:STATISTICAL_AUDIT",
            missing["blockers"],
        )
        self.assertEqual(drift["status"], "BLOCK")
        self.assertFalse(drift["numeric_claims_available"])
        self.assertEqual(drift["return_quality"], {})
        self.assertTrue(any(
            item.startswith("detached_artifact_")
            for item in drift["blockers"]
        ))

    def test_v5_exact_detached_authority_alias_blocks_numeric_claims(self) -> None:
        evidence = v4_evidence()
        evidence["research"]["unknown_nested"] = {"can_trade": True}
        research_text = json.dumps(evidence["research"], ensure_ascii=False, indent=2)
        research_raw = research_text.encode("utf-8")
        evidence["research_raw_bytes"] = research_raw
        evidence["research_artifact"] = {
            "file": "research.json",
            "file_sha256": hashlib.sha256(research_raw).hexdigest(),
            "size": len(research_raw),
        }
        receipt = evidence["active"]["registry"]["experiment_completion_receipt"]
        receipt["report_file_sha256"] = hashlib.sha256(research_raw).hexdigest()
        receipt_content = deepcopy(receipt)
        receipt_content.pop("receipt_hash", None)
        receipt["receipt_hash"] = canonical_hash(receipt_content)
        registry = evidence["active"]["registry"]
        registry["experiment_completion_receipt_hash"] = receipt["receipt_hash"]
        registry_content = deepcopy(registry)
        registry_content.pop("registry_hash", None)
        registry["registry_hash"] = canonical_hash(registry_content)
        pack = assemble_internal_backtest_pack(evidence, generated_at=100)
        detached_artifacts = _build_v5_source_material(evidence)[2]

        result = verify_internal_backtest_bundle(pack, detached_artifacts)

        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["artifact_contract_status"], "PASS")
        self.assertEqual(result["return_quality_source_integrity_status"], "BLOCK")
        self.assertFalse(result["numeric_claims_available"])
        self.assertEqual(result["return_quality"], {})
        self.assertTrue(any(
            "contains_execution_authority" in item
            for item in result["blockers"]
        ))

    def test_v5_detached_parser_and_record_contract_are_exact(self) -> None:
        for raw in (b'{"x":NaN}', b'{"x":1e999}', b'{"x":1,"x":2}'):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    _strict_json_object(raw)
        depth_overflow = b'{"x":' + (b"[" * 127) + b"0" + (b"]" * 127) + b"}"
        with self.assertRaises(ValueError):
            _strict_json_object(depth_overflow)
        for unsafe in (
            "dir\\research.json",
            "research.json:ads",
            "research.json. ",
            "CON.json",
            "a?.json",
        ):
            with self.subTest(unsafe=unsafe):
                self.assertEqual(_safe_detached_basename(unsafe), "")

        pack, detached_artifacts = v5_bundle()
        extra = deepcopy(detached_artifacts)
        extra[0]["unexpected"] = False
        result = verify_internal_backtest_bundle(pack, extra)

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("detached_artifact_fields_invalid", result["blockers"])
        self.assertFalse(result["numeric_claims_available"])

        deeply_nested = b'{"child":' * 2_000 + b"0" + b"}" * 2_000
        deep = deepcopy(detached_artifacts)
        deep[0]["raw_bytes"] = deeply_nested
        deep[0]["sha256"] = hashlib.sha256(deep[0]["raw_bytes"]).hexdigest()
        deep[0]["byte_length"] = len(deep[0]["raw_bytes"])
        deep_result = verify_internal_backtest_bundle(pack, deep)
        self.assertEqual(deep_result["status"], "BLOCK")
        self.assertFalse(deep_result["numeric_claims_available"])

    def test_v5_windows_detached_basenames_and_aliases_fail_closed(self) -> None:
        for unsafe in ("CON.json", "a?.json"):
            with self.subTest(builder_name=unsafe):
                evidence = v4_evidence()
                evidence["research_artifact"]["file"] = unsafe
                with self.assertRaisesRegex(ValueError, "detached artifact basename"):
                    _build_v5_source_material(evidence)

        collision_evidence = v4_evidence()
        collision_evidence["statistical_artifact"] = {"file": "RESEARCH.JSON"}
        with self.assertRaisesRegex(ValueError, "basename identity duplicate"):
            _build_v5_source_material(collision_evidence)

        cases = (
            ("research_report", 0, "CON.json", "basename_invalid:RESEARCH_REPORT"),
            ("research_report", 0, "a?.json", "basename_invalid:RESEARCH_REPORT"),
            (
                "statistical_audit",
                1,
                "RESEARCH.JSON",
                "basename_identity_duplicate",
            ),
        )
        for manifest_field, artifact_index, unsafe, expected_blocker in cases:
            with self.subTest(verifier_name=unsafe):
                pack, artifacts = v5_bundle()
                forged = deepcopy(pack)
                forged_artifacts = deepcopy(artifacts)
                manifest = forged["return_quality_source_manifest"]
                manifest[manifest_field]["file"] = unsafe
                forged_artifacts[artifact_index]["file"] = unsafe
                manifest_content = deepcopy(manifest)
                manifest_content.pop("manifest_hash", None)
                manifest["manifest_hash"] = canonical_hash(manifest_content)
                forged["return_quality"]["source_manifest_hash"] = manifest["manifest_hash"]
                reseal_pack(forged)

                result = verify_internal_backtest_bundle(forged, forged_artifacts)

                self.assertEqual(result["status"], "BLOCK")
                self.assertEqual(result["artifact_contract_status"], "BLOCK")
                self.assertFalse(result["numeric_claims_available"])
                self.assertEqual(result["return_quality"], {})
                self.assertTrue(
                    any(expected_blocker in blocker for blocker in result["blockers"]),
                    result,
                )

    def test_v5_malformed_containers_and_deep_unknown_values_never_escape(self) -> None:
        pack, artifacts = v5_bundle()
        for malformed_pack in (None, [], "not-a-pack"):
            with self.subTest(pack_type=type(malformed_pack).__name__):
                pack_result = verify_internal_backtest_pack(malformed_pack)  # type: ignore[arg-type]
                bundle_result = verify_internal_backtest_bundle(  # type: ignore[arg-type]
                    malformed_pack,
                    artifacts,
                )
                self.assertEqual(pack_result["status"], "BLOCK")
                self.assertFalse(pack_result["numeric_claims_available"])
                self.assertEqual(bundle_result["status"], "BLOCK")
                self.assertFalse(bundle_result["numeric_claims_available"])
                self.assertEqual(bundle_result["return_quality"], {})
                self.assertEqual(
                    required_internal_backtest_bundle_members(malformed_pack),  # type: ignore[arg-type]
                    (),
                )

        malformed_manifest = deepcopy(pack)
        malformed_manifest["return_quality_source_manifest"] = [1]
        malformed_record = deepcopy(pack)
        malformed_record["return_quality_source_manifest"]["research_report"] = [1]
        for malformed in (malformed_manifest, malformed_record):
            with self.subTest(container=type(malformed["return_quality_source_manifest"]).__name__):
                pack_result = verify_internal_backtest_pack(malformed)
                bundle_result = verify_internal_backtest_bundle(malformed, artifacts)
                self.assertEqual(pack_result["status"], "BLOCK")
                self.assertFalse(pack_result["numeric_claims_available"])
                self.assertEqual(bundle_result["status"], "BLOCK")
                self.assertFalse(bundle_result["numeric_claims_available"])
                self.assertEqual(bundle_result["return_quality"], {})
                self.assertEqual(required_internal_backtest_bundle_members(malformed), ())

        deeply_nested = deepcopy(pack)
        node: dict[str, object] = {}
        deeply_nested["unknown_deep_container"] = node
        for _index in range(2_000):
            child: dict[str, object] = {}
            node["child"] = child
            node = child

        pack_result = verify_internal_backtest_pack(deeply_nested)
        bundle_result = verify_internal_backtest_bundle(deeply_nested, artifacts)

        self.assertEqual(pack_result["status"], "BLOCK")
        self.assertEqual(
            pack_result["blockers"],
            ["backtest_pack_verification_unexpected_error"],
        )
        self.assertFalse(pack_result["numeric_claims_available"])
        self.assertEqual(bundle_result["status"], "BLOCK")
        self.assertEqual(
            bundle_result["blockers"],
            ["backtest_bundle_verification_unexpected_error"],
        )
        self.assertFalse(bundle_result["numeric_claims_available"])
        self.assertEqual(bundle_result["return_quality"], {})

    def test_v5_coherently_resealed_pack_candidate_spec_cannot_diverge(self) -> None:
        pack, detached_artifacts = v5_bundle()
        forged = deepcopy(pack)
        forged_spec = deepcopy(forged["candidate"]["spec"])
        forged_spec["fee_rate"] = 0.123
        forged_hash = canonical_hash(forged_spec)
        forged["candidate"]["spec"] = forged_spec
        forged["candidate"]["declared_spec_hash"] = forged_hash
        forged["candidate"]["computed_spec_hash"] = forged_hash
        forward_candidate = forged["forward_promotion_evidence"]["candidate"]
        forward_candidate["spec"] = deepcopy(forged_spec)
        forward_candidate["declared_spec_hash"] = forged_hash
        forward_candidate["computed_spec_hash"] = forged_hash
        projection = forged["forward_promotion_evidence"]
        projection_content = deepcopy(projection)
        projection_content.pop("projection_hash", None)
        projection["projection_hash"] = canonical_hash(projection_content)
        reseal_pack(forged)

        result = verify_internal_backtest_bundle(forged, detached_artifacts)

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn(
            "backtest_pack_return_quality_candidate_binding_mismatch:spec",
            result["blockers"],
        )
        self.assertFalse(result["numeric_claims_available"])

    def test_v5_pack_size_is_nearly_constant_when_detached_source_grows(self) -> None:
        baseline = assemble_internal_backtest_pack(v4_evidence(), generated_at=100)
        evidence = v4_evidence()
        evidence["research"]["unused_large_payload"] = [
            {"row": index, "value": "x" * 32}
            for index in range(5_000)
        ]
        research_raw = json.dumps(
            evidence["research"], ensure_ascii=False, indent=2
        ).encode("utf-8")
        evidence["research_raw_bytes"] = research_raw
        evidence["research_artifact"] = {
            "file": "research.json",
            "file_sha256": hashlib.sha256(research_raw).hexdigest(),
            "size": len(research_raw),
        }
        receipt = evidence["active"]["registry"]["experiment_completion_receipt"]
        receipt["report_file_sha256"] = hashlib.sha256(research_raw).hexdigest()
        receipt_content = deepcopy(receipt)
        receipt_content.pop("receipt_hash", None)
        receipt["receipt_hash"] = canonical_hash(receipt_content)
        registry = evidence["active"]["registry"]
        registry["experiment_completion_receipt_hash"] = receipt["receipt_hash"]
        registry_content = deepcopy(registry)
        registry_content.pop("registry_hash", None)
        registry["registry_hash"] = canonical_hash(registry_content)

        large = assemble_internal_backtest_pack(evidence, generated_at=100)
        encoded = lambda value: json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        self.assertGreater(len(research_raw), 250_000)
        self.assertLess(abs(len(encoded(large)) - len(encoded(baseline))), 512)
        self.assertNotIn("unused_large_payload", encoded(large).decode("utf-8"))

    def test_v5_quality_business_projection_matches_v4_for_same_sources(self) -> None:
        evidence = v4_evidence()
        v4 = assemble_internal_backtest_pack(
            evidence,
            generated_at=100,
            schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
        )
        v5 = assemble_internal_backtest_pack(
            evidence,
            generated_at=100,
            schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_V5_SCHEMA_VERSION,
        )
        historical = deepcopy(v4["return_quality"])
        current = deepcopy(v5["return_quality"])
        for projection in (historical, current):
            projection.pop("schema_version", None)
            projection.pop("source_identity", None)
            projection.pop("source_evidence_hash", None)
            projection.pop("source_manifest_hash", None)
            projection.pop("detached_source_binding_hash", None)

        self.assertEqual(current, historical)

    def test_v5_normalized_path_preserves_v4_and_v5_golden_hashes(self) -> None:
        evidence = v4_evidence()
        v5 = assemble_internal_backtest_pack(
            evidence,
            generated_at=100,
            schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_V5_SCHEMA_VERSION,
        )
        v4 = assemble_internal_backtest_pack(
            evidence,
            generated_at=100,
            schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
        )

        self.assertEqual(
            (
                v5["pack_hash"],
                v5["evidence_hash"],
                v5["return_quality_source_manifest"]["manifest_hash"],
                v5["return_quality"]["source_identity"]["identity_hash"],
            ),
            (
                "de6fc7004f67c27f2a1c35a800f83902511d76f81ba879204debe0ffa559c5e3",
                "9c9681ae33f6e710d407c9b42881b1b15cab1be109e2a45cdf7efcd4f6e917d1",
                "b6e05b3b962da5eb789f2de946486aa7bd48f991b0438d3b5ff4adbbc57ad261",
                "a1669726335e0d8fb5043ea58e88cf7dfae26f10cb02f76b3f7cf8c9715b28a2",
            ),
        )
        self.assertEqual(
            (
                v4["pack_hash"],
                v4["evidence_hash"],
                v4["return_quality_source_evidence"]["source_evidence_hash"],
                v4["return_quality"]["source_identity"]["identity_hash"],
            ),
            (
                "a3a509b63eb0705437950b7ce6a851d81a0205d487a770030fb3d6696ff51440",
                "043c82b4930c1add115fbecd20d0b114e58a48aedee4518681cb31b0f5f0ec23",
                "e3951a6b9d5aab03b1009aba5591e57864073554e65aa15d1935609007775fd0",
                "82c2bd43ed5aacc1d38590c954e227a6609422ce8227db3dbf2d516e55620d3f",
            ),
        )

    def test_v5_normalized_path_never_builds_legacy_heavy_source_wrappers(self) -> None:
        with (
            patch(
                "exchange_terminal.services.portfolio_backtest_pack."
                "_research_source_document",
                side_effect=AssertionError("legacy source document used"),
            ),
            patch(
                "exchange_terminal.services.portfolio_backtest_pack."
                "_project_return_quality_source_evidence",
                side_effect=AssertionError("legacy source evidence used"),
            ),
            patch(
                "exchange_terminal.services.portfolio_backtest_pack."
                "_verify_return_quality_source_evidence",
                side_effect=AssertionError("legacy source verifier used"),
            ),
        ):
            manifest, quality, artifacts = _build_v5_source_material(v4_evidence())

        self.assertEqual(manifest["source_integrity_status"], "PASS")
        self.assertTrue(quality["numeric_claims_available"])
        self.assertEqual(len(artifacts), 2)

    def test_v5_normalized_blockers_match_legacy_checker_attack_matrix(self) -> None:
        import exchange_terminal.services.portfolio_backtest_pack as pack_module

        def synchronize_raw(evidence: dict[str, object]) -> None:
            raw = json.dumps(
                evidence["research"],
                ensure_ascii=False,
                indent=2,
            ).encode("utf-8")
            evidence["research_raw_bytes"] = raw
            evidence["research_artifact"] = {
                "file": "research.json",
                "file_sha256": hashlib.sha256(raw).hexdigest(),
                "size": len(raw),
            }

        def legacy_blockers(evidence: dict[str, object]) -> list[str]:
            active = dict(evidence.get("active") or {})
            candidate = dict(active.get("candidate") or {})
            registry = dict(active.get("registry") or {})
            research = dict(evidence.get("research") or {})
            statistical = dict(evidence.get("statistical") or {})
            artifact = dict(evidence.get("research_artifact") or {})
            raw = pack_module._detached_source_bytes(
                evidence,
                "research_raw_bytes",
                research,
            )
            document = pack_module._research_source_document(raw.decode("utf-8"))
            source = pack_module._project_return_quality_source_evidence(
                candidate=candidate,
                research=research,
                statistical=statistical,
                research_artifact={
                    "file": str(artifact.get("file") or "research.json"),
                    "file_sha256": hashlib.sha256(raw).hexdigest(),
                    "size": len(raw),
                },
                registry=registry,
                research_source_document=document,
            )
            verification = pack_module._verify_return_quality_source_evidence(source)
            exact = [
                f"detached_{name}_contains_execution_authority:{item}"
                for name, value in (
                    ("research", research),
                    ("statistical", statistical),
                )
                for item in pack_module.authority_violations(value)
            ]
            return list(dict.fromkeys([
                *list(verification.get("source_blockers") or []),
                *exact,
            ]))

        cases: list[tuple[str, dict[str, object]]] = []
        for label, mutate, synchronize in (
            (
                "stage_authority",
                lambda evidence: evidence["research"]["test"].__setitem__(
                    "can_trade",
                    True,
                ),
                True,
            ),
            (
                "benchmark_authority",
                lambda evidence: evidence["research"]["test_benchmark"].__setitem__(
                    "execution_allowed",
                    True,
                ),
                True,
            ),
            (
                "cost_authority",
                lambda evidence: evidence["research"]["cost_stress"][0].__setitem__(
                    "paper_ready",
                    True,
                ),
                True,
            ),
            (
                "raw_object_drift",
                lambda evidence: evidence["research"]["test"].__setitem__(
                    "total_return_pct",
                    999.0,
                ),
                False,
            ),
            (
                "statistical_drift",
                lambda evidence: evidence["statistical"]["stages"]["test"].__setitem__(
                    "observation_count",
                    999,
                ),
                False,
            ),
            (
                "bounded_unknown_authority",
                lambda evidence: evidence["research"].__setitem__(
                    "authority_noise",
                    [{"can_trade": True} for _index in range(148)],
                ),
                True,
            ),
        ):
            evidence = v4_evidence()
            mutate(evidence)
            if synchronize:
                synchronize_raw(evidence)
            cases.append((label, evidence))

        for label, evidence in cases:
            with self.subTest(label=label):
                expected = legacy_blockers(evidence)
                manifest, _quality, _artifacts = _build_v5_source_material(evidence)
                self.assertEqual(
                    manifest["source_blockers"],
                    expected[:MAX_PORTFOLIO_SOURCE_BLOCKERS],
                )
                self.assertEqual(manifest["source_blocker_count"], len(expected))
                self.assertEqual(
                    manifest["source_blockers_truncated"],
                    len(expected) > MAX_PORTFOLIO_SOURCE_BLOCKERS,
                )

    def test_v5_bundle_verifier_parses_each_detached_member_once(self) -> None:
        pack, detached_artifacts = v5_bundle()
        import exchange_terminal.services.portfolio_backtest_pack as pack_module

        original = pack_module._strict_json_object
        parsed_roles: list[bytes] = []

        def count_parse(raw: bytes) -> dict[str, object]:
            parsed_roles.append(raw)
            return original(raw)

        with patch.object(pack_module, "_strict_json_object", side_effect=count_parse):
            result = verify_internal_backtest_bundle(pack, detached_artifacts)

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(parsed_roles, [
            detached_artifacts[0]["raw_bytes"],
            detached_artifacts[1]["raw_bytes"],
        ])

    def test_public_pack_and_bundle_verifiers_fail_closed_on_memory_error(self) -> None:
        pack, detached_artifacts = v5_bundle()
        with patch(
            "exchange_terminal.services.portfolio_backtest_pack."
            "_verify_internal_backtest_pack_v5_structure",
            side_effect=MemoryError,
        ):
            pack_result = verify_internal_backtest_pack(pack)
        with patch(
            "exchange_terminal.services.portfolio_backtest_pack."
            "_verify_internal_backtest_bundle",
            side_effect=MemoryError,
        ):
            bundle_result = verify_internal_backtest_bundle(pack, detached_artifacts)

        self.assertEqual(pack_result["status"], "BLOCK")
        self.assertEqual(
            pack_result["blockers"],
            ["backtest_pack_verification_memory_exhausted"],
        )
        self.assertFalse(pack_result["numeric_claims_available"])
        self.assertEqual(bundle_result["status"], "BLOCK")
        self.assertEqual(
            bundle_result["blockers"],
            ["backtest_bundle_verification_memory_exhausted"],
        )
        self.assertEqual(bundle_result["return_quality"], {})
        self.assertFalse(bundle_result["numeric_claims_available"])

    def test_v5_compact_caps_precede_transient_source_projection(self) -> None:
        too_many_costs = v4_evidence()
        too_many_costs["research"]["cost_stress"] = [
            {"label": f"S{index}"}
            for index in range(65)
        ]
        with patch(
            "exchange_terminal.services.portfolio_backtest_pack."
            "_project_return_quality_source_evidence"
        ) as transient:
            with self.assertRaisesRegex(ValueError, "cost stress scenario limit"):
                _build_v5_source_material(too_many_costs)
            transient.assert_not_called()

        oversized_candidate = v4_evidence()
        oversized_candidate["active"]["candidate"]["spec"]["padding"] = (
            "x" * (MAX_PORTFOLIO_COMPACT_CANDIDATE_BYTES + 1)
        )
        with patch(
            "exchange_terminal.services.portfolio_backtest_pack."
            "_project_return_quality_source_evidence"
        ) as transient:
            with self.assertRaisesRegex(ValueError, "compact candidate size limit"):
                _build_v5_source_material(oversized_candidate)
            transient.assert_not_called()

        oversized_registry = v4_evidence()
        oversized_registry["active"]["registry"]["selection_policy"] = (
            "x" * (4 * 1024 * 1024 + 1)
        )
        with patch(
            "exchange_terminal.services.portfolio_backtest_pack."
            "_project_return_quality_source_evidence"
        ) as transient:
            with self.assertRaisesRegex(ValueError, "compact registry size limit"):
                _build_v5_source_material(oversized_registry)
            transient.assert_not_called()

        oversized_statistical = v4_evidence()
        oversized_statistical["statistical"]["unknown_large_detail"] = (
            "x" * (16 * 1024 * 1024 + 1)
        )
        oversized_statistical["statistical_raw_bytes"] = b"{}"
        with patch(
            "exchange_terminal.services.portfolio_backtest_pack."
            "_project_return_quality_source_evidence"
        ) as transient:
            with self.assertRaisesRegex(ValueError, "statistical canonical size limit"):
                _build_v5_source_material(oversized_statistical)
            transient.assert_not_called()

    def test_v5_source_blockers_are_bounded_with_explicit_total(self) -> None:
        evidence = v4_evidence()
        evidence["research"]["authority_noise"] = [
            {"can_trade": True}
            for _index in range(MAX_PORTFOLIO_SOURCE_BLOCKERS + 20)
        ]
        research_raw = json.dumps(
            evidence["research"], ensure_ascii=False, indent=2
        ).encode("utf-8")
        evidence["research_raw_bytes"] = research_raw
        evidence["research_artifact"] = {
            "file": "research.json",
            "file_sha256": hashlib.sha256(research_raw).hexdigest(),
            "size": len(research_raw),
        }
        receipt = evidence["active"]["registry"]["experiment_completion_receipt"]
        receipt["report_file_sha256"] = hashlib.sha256(research_raw).hexdigest()
        receipt_content = deepcopy(receipt)
        receipt_content.pop("receipt_hash", None)
        receipt["receipt_hash"] = canonical_hash(receipt_content)
        registry = evidence["active"]["registry"]
        registry["experiment_completion_receipt_hash"] = receipt["receipt_hash"]
        registry_content = deepcopy(registry)
        registry_content.pop("registry_hash", None)
        registry["registry_hash"] = canonical_hash(registry_content)

        manifest, quality, _artifacts = _build_v5_source_material(evidence)

        self.assertEqual(len(manifest["source_blockers"]), MAX_PORTFOLIO_SOURCE_BLOCKERS)
        self.assertGreater(manifest["source_blocker_count"], MAX_PORTFOLIO_SOURCE_BLOCKERS)
        self.assertTrue(manifest["source_blockers_truncated"])
        self.assertFalse(quality["numeric_claims_available"])

    def test_v5_builder_never_returns_an_oversized_pack(self) -> None:
        evidence = v4_evidence()
        material = _build_v5_source_material(evidence)
        oversized_base = _assemble_internal_backtest_pack_v3(
            evidence,
            generated_at=100,
        )
        oversized_base["unexpected_large_projection"] = (
            "x" * (MAX_PORTFOLIO_INTERNAL_BACKTEST_PACK_BYTES + 1)
        )
        with patch(
            "exchange_terminal.services.portfolio_backtest_pack."
            "_assemble_internal_backtest_pack_v3",
            return_value=oversized_base,
        ):
            with self.assertRaisesRegex(ValueError, "pack size limit"):
                _assemble_internal_backtest_pack_v5(
                    evidence,
                    generated_at=100,
                    source_material=material,
                )

    def test_core_verifier_blocks_resealed_authority_key_aliases(self) -> None:
        packs = {
            "v2": sealed_pack(),
            "v3": sealed_v3_pack(forward_projection(outcomes=10, required=10)),
            "v4": assemble_internal_backtest_pack(
                v4_evidence(),
                generated_at=100,
                schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
            ),
        }
        wrappers = {
            "mapping": lambda alias: {alias: True},
            "list": lambda alias: [{alias: True}],
            "tuple": lambda alias: ({alias: True},),
        }
        for version, original in packs.items():
            self.assertEqual(verify_internal_backtest_pack(original)["status"], "PASS")
            for alias in ("Paper_Authorized", "CAN_TRADE", "paperAuthorized"):
                for wrapper, build_nested in wrappers.items():
                    with self.subTest(version=version, alias=alias, wrapper=wrapper):
                        forged = deepcopy(original)
                        forged["unknown_nested_scope"] = build_nested(alias)
                        reseal_pack(forged)

                        result = verify_internal_backtest_pack(forged)

                        self.assertEqual(result["status"], "BLOCK")
                        self.assertIn(
                            "backtest_pack_contains_execution_authority",
                            result["blockers"],
                        )

    def test_v4_source_document_rejects_hidden_nested_authority(self) -> None:
        document = _research_source_document(json.dumps({
            "schema_version": "portfolio-backtest-v1",
            "nested_unknown": {
                "can_trade": True,
                "mission_authorized": True,
            },
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }))

        verification = _verify_research_source_document(document)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "research_source_document_parsed_contains_execution_authority",
            verification["blockers"],
        )

    def assert_v4_source_block_redacts_numeric_claims(
        self,
        pack: dict[str, object],
        *,
        blocker_fragment: str,
    ) -> None:
        verification = verify_internal_backtest_pack(pack)
        quality = pack["return_quality"]
        summary = quality["summary"]

        self.assertEqual(pack["status"], "INTERNAL_BACKTEST_BLOCKED")
        self.assertEqual(
            pack["return_quality_source_evidence"]["source_integrity_status"],
            "BLOCK",
        )
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["artifact_contract_status"], "PASS")
        self.assertEqual(verification["return_quality_source_integrity_status"], "BLOCK")
        self.assertEqual(quality["status"], "BLOCK")
        self.assertEqual(quality["source_integrity_status"], "BLOCK")
        self.assertFalse(quality["numeric_claims_available"])
        self.assertTrue(any(
            blocker_fragment in item
            for item in quality["failure_conditions"]["source_integrity"]
        ))
        for field in (
            "strategy_return_pct",
            "benchmark_return_pct",
            "benchmark_excess_return_pct",
            "cost_after_return_pct",
            "worst_stress_return_pct",
            "max_drawdown_pct",
            "sample_size",
        ):
            self.assertIsNone(summary[field])
        self.assertEqual(summary["benchmark_excess_status"], "UNKNOWN")
        self.assertEqual(summary["cost_after_status"], "UNKNOWN")
        self.assertEqual(quality["cost_after"]["stress_scenarios"], [])

    def test_research_batch_hash_binds_provider_governance_contract(self) -> None:
        report = statistical_research_report()
        report["provider_governance"] = {"contract_hash": "a" * 64}
        first = research_batch_hash(report)
        report["provider_governance"] = {"contract_hash": "b" * 64}

        self.assertNotEqual(first, research_batch_hash(report))

    def test_untampered_pack_verifies(self) -> None:
        result = verify_internal_backtest_pack(sealed_pack())

        self.assertEqual(result["status"], "PASS")

    def test_missing_active_evidence_fails_closed_without_market_access(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = build_internal_backtest_pack(
                Path(temp_dir),
                generated_at=100,
                schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
            )

        self.assertEqual(pack["status"], "INTERNAL_BACKTEST_BLOCKED")
        self.assertEqual(verify_internal_backtest_pack(pack)["status"], "PASS")
        self.assertTrue(pack["checks"]["artifact_verification_only"])
        self.assertTrue(pack["checks"]["no_market_data_fetch"])
        self.assertFalse(pack["checks"]["forward_statistical_evidence_source_integrity_pass"])
        self.assertTrue(any(
            item.startswith("forward_statistical_evidence:")
            for item in pack["blockers"]
        ))
        self.assertFalse(pack["paper_authorized"])
        self.assertFalse(pack["live_order_allowed"])

    def test_execution_rehearsal_tamper_and_candidate_mismatch_are_blocked(self) -> None:
        valid = rehearsal()
        valid_result = verify_execution_rehearsal_artifact(
            valid,
            candidate_hash=CANDIDATE_HASH,
            research_batch_run_hash=RESEARCH_HASH,
            research_file_sha256=RESEARCH_FILE_HASH,
        )
        tampered = deepcopy(valid)
        tampered["stage_summary"]["test"]["status"] = "BLOCK"
        tampered_result = verify_execution_rehearsal_artifact(
            tampered,
            candidate_hash="x" * 64,
            research_batch_run_hash=RESEARCH_HASH,
            research_file_sha256=RESEARCH_FILE_HASH,
        )

        self.assertEqual(valid_result["status"], "PASS")
        self.assertEqual(tampered_result["status"], "BLOCK")
        self.assertIn("execution_rehearsal_candidate_mismatch", tampered_result["blockers"])
        self.assertIn("execution_rehearsal_report_hash_invalid", tampered_result["blockers"])
        self.assertIn("execution_rehearsal_artifact_hash_invalid", tampered_result["blockers"])

    def test_statistical_block_is_valid_evidence_but_candidate_mismatch_is_not(self) -> None:
        report = statistical_audit()
        valid = verify_statistical_audit_artifact(
            report,
            candidate_hash=CANDIDATE_HASH,
            research_batch_run_hash=RESEARCH_HASH,
            research_file_sha256=RESEARCH_FILE_HASH,
            research_report=statistical_research_report(),
        )
        mismatched = verify_statistical_audit_artifact(
            report,
            candidate_hash="x" * 64,
            research_batch_run_hash=RESEARCH_HASH,
            research_file_sha256=RESEARCH_FILE_HASH,
            research_report=statistical_research_report(),
        )

        self.assertEqual(valid["status"], "PASS")
        self.assertEqual(valid["claim_status"], "BLOCK")
        self.assertEqual(mismatched["status"], "BLOCK")
        self.assertIn("statistical_audit_candidate_mismatch", mismatched["blockers"])

    def test_resealed_pack_cannot_carry_execution_authority(self) -> None:
        unsafe = sealed_pack()
        unsafe["paper_authorized"] = True
        reseal_pack(unsafe)

        result = verify_internal_backtest_pack(unsafe)

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("backtest_pack_contains_execution_authority", result["blockers"])

    def test_resealed_forward_progress_non_native_counts_are_blocked(self) -> None:
        valid = sealed_pack()
        valid["forward_progress"] = {
            "observations": 60,
            "required_observations": 60,
            "outcome_periods": 10,
            "required_outcome_periods": 10,
            "executed_rebalances": 8,
            "required_executed_rebalances": 8,
            "scheduler_health": "PASS",
        }
        reseal_pack(valid)

        self.assertEqual(verify_internal_backtest_pack(valid)["status"], "PASS")

        for bad_value in ("10", True, -1, 10.0):
            with self.subTest(bad_value=bad_value):
                forged = deepcopy(valid)
                forged["forward_progress"]["outcome_periods"] = bad_value
                reseal_pack(forged)

                result = verify_internal_backtest_pack(forged)

                self.assertEqual(result["status"], "BLOCK")
                self.assertIn(
                    "backtest_pack_forward_progress_type_invalid:outcome_periods",
                    result["blockers"],
                )

    def test_non_boolean_authority_values_fail_closed(self) -> None:
        for value in (1, "true", "false", None):
            with self.subTest(value=value):
                unsafe = sealed_pack()
                unsafe["paper_authorized"] = value
                reseal_pack(unsafe)

                result = verify_internal_backtest_pack(unsafe)

                self.assertEqual(result["status"], "BLOCK")
                self.assertIn("backtest_pack_contains_execution_authority", result["blockers"])

    def test_forward_performance_must_bind_the_same_shadow_snapshot(self) -> None:
        audit = {
            "status": "PASS",
            "candidate_hash": CANDIDATE_HASH,
            "valid_observation_count": 1,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        forward = {
            "candidate_hash": CANDIDATE_HASH,
            "readiness": {"ledger_audit": audit},
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        statistical = statistical_audit()
        performance = {
            "candidate_hash": CANDIDATE_HASH,
            "shadow_audit": deepcopy(audit),
            "shadow_audit_hash": canonical_hash(audit),
            "performance": {"status": "PASS", "candidate_hash": CANDIDATE_HASH},
            "readiness": {
                "integrity_checks": {
                    "shadow_ledger_integrity_pass": True,
                    "performance_ledger_integrity_pass": True,
                    "all_captured_observations_settled": True,
                    "zero_execution_authority": True,
                }
            },
            "historical_statistical_audit": {
                "audit_hash": statistical["audit_hash"],
                "artifact_hash": statistical["artifact_hash"],
            },
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        valid = verify_forward_performance_artifact(
            performance,
            CANDIDATE_HASH,
            statistical,
            forward,
        )
        lagged = deepcopy(performance)
        lagged["shadow_audit"]["valid_observation_count"] = 0
        lagged["shadow_audit_hash"] = canonical_hash(lagged["shadow_audit"])
        mismatched = verify_forward_performance_artifact(
            lagged,
            CANDIDATE_HASH,
            statistical,
            forward,
        )

        self.assertEqual(valid["status"], "PASS")
        self.assertEqual(mismatched["status"], "BLOCK")
        self.assertIn("forward_performance_observation_snapshot_mismatch", mismatched["blockers"])

    def test_resealed_pack_cannot_claim_promotion_when_evidence_is_blocked(self) -> None:
        inconsistent = sealed_pack()
        inconsistent["checks"]["all_evidence"] = False
        inconsistent["status"] = "INTERNAL_BACKTEST_BLOCKED"
        inconsistent["promotion_status"] = "PASS"
        inconsistent["promotion_blockers"] = []
        reseal_pack(inconsistent)

        result = verify_internal_backtest_pack(inconsistent)

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("backtest_pack_promotion_status_inconsistent", result["blockers"])

    def test_v3_not_due_is_collecting_and_never_promotes(self) -> None:
        projection = forward_projection(outcomes=5, required=6)
        pack = sealed_v3_pack(projection)

        result = verify_internal_backtest_pack(pack)

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(pack["forward_evidence_status"], "COLLECTING")
        self.assertEqual(pack["promotion_status"], "BLOCK")
        self.assertIn(
            "natural_forward_statistical_evidence_not_mature",
            pack["promotion_blockers"],
        )
        self.assertFalse(pack["profitability_proven"])
        self.assertFalse(pack["paper_authorized"])
        self.assertFalse(pack["live_order_allowed"])

    def test_v3_due_forward_pass_requires_manual_review_despite_historical_block(self) -> None:
        projection = forward_projection(outcomes=10, required=10)
        pack = sealed_v3_pack(projection)

        result = verify_internal_backtest_pack(pack)

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(pack["forward_evidence_status"], "RESEARCH_REVIEW_READY")
        self.assertEqual(pack["promotion_status"], "REVIEW_REQUIRED")
        self.assertNotIn("historical_statistical_audit_pass", pack["promotion_blockers"])
        self.assertEqual(
            projection["historical_statistical_contract_source"]["claim_status"],
            "BLOCK",
        )
        self.assertTrue(pack["manual_review_required"])
        self.assertFalse(pack["performance_claim_proven"])

    def test_v3_due_valid_negative_is_review_blocked_not_corrupt(self) -> None:
        projection = forward_projection(outcomes=10, required=10, weak_edge=True)
        pack = sealed_v3_pack(projection)

        result = verify_internal_backtest_pack(pack)

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(pack["forward_evidence_status"], "RESEARCH_REVIEW_BLOCKED")
        self.assertEqual(pack["promotion_status"], "BLOCK")
        self.assertEqual(projection["source_integrity_status"], "PASS")
        self.assertIn(
            "natural_forward_statistical_evidence_not_passed",
            pack["promotion_blockers"],
        )

    def test_v3_resealed_semantic_claim_or_nested_authority_is_blocked(self) -> None:
        projection = forward_projection(outcomes=10, required=10)
        forged = sealed_v3_pack(deepcopy(projection))
        forged["forward_evidence_status"] = "COLLECTING"
        forged["promotion_status"] = "BLOCK"
        forged["promotion_blockers"] = ["natural_forward_statistical_evidence_not_mature"]
        reseal_pack(forged)

        forged_result = verify_internal_backtest_pack(forged)

        self.assertEqual(forged_result["status"], "BLOCK")
        self.assertIn("backtest_pack_forward_evidence_status_inconsistent", forged_result["blockers"])

        unsafe = sealed_v3_pack(deepcopy(projection))
        unsafe["forward_promotion_evidence"]["nested"] = {"execution_allowed": True}
        forward_content = dict(unsafe["forward_promotion_evidence"])
        forward_content.pop("projection_hash", None)
        unsafe["forward_promotion_evidence"]["projection_hash"] = canonical_hash(forward_content)
        reseal_pack(unsafe)

        unsafe_result = verify_internal_backtest_pack(unsafe)

        self.assertEqual(unsafe_result["status"], "BLOCK")
        self.assertIn("backtest_pack_contains_execution_authority", unsafe_result["blockers"])
        self.assertTrue(any(
            "forward_evidence_source_integrity_status_inconsistent" in item
            for item in unsafe_result["blockers"]
        ))

    def test_v3_resealed_top_level_candidate_cannot_drift_from_forward_projection(self) -> None:
        pack = sealed_v3_pack(forward_projection(outcomes=10, required=10))
        pack["candidate"]["candidate_hash"] = "x" * 64
        reseal_pack(pack)

        result = verify_internal_backtest_pack(pack)

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("backtest_pack_forward_candidate_hash_mismatch", result["blockers"])

    def test_v4_recomputes_return_quality_from_bound_portfolio_sources(self) -> None:
        pack = assemble_internal_backtest_pack(
            v4_evidence(), generated_at=100,
            schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
        )

        result = verify_internal_backtest_pack(pack)

        self.assertEqual(
            pack["schema_version"],
            PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["return_quality_source_integrity_status"], "PASS")
        self.assertEqual(pack["return_quality"]["schema_version"], "backtest-return-quality-v2")
        identity = pack["return_quality"]["source_identity"]
        self.assertEqual(identity["source_artifact_family"], "PORTFOLIO_RESEARCH_PROTOCOL_V1")
        self.assertEqual(identity["strategy_schema7_preregistration_status"], "NOT_APPLICABLE")
        self.assertFalse(pack["return_quality"]["profitability_proven"])
        self.assertFalse(pack["paper_authorized"])
        self.assertFalse(pack["live_order_allowed"])

    def test_v4_cost_stress_declared_return_reseal_is_valid_blocked_artifact(self) -> None:
        evidence = v4_evidence()
        for scenario in evidence["research"]["cost_stress"]:
            scenario["total_return_pct"] = 999.0

        pack = assemble_internal_backtest_pack(
            evidence, generated_at=100,
            schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
        )

        self.assert_v4_source_block_redacts_numeric_claims(
            pack,
            blocker_fragment="cost_stress_MODERATE_total_return_pct_mismatch",
        )

    def test_v4_strategy_equity_coherent_reseal_is_valid_blocked_artifact(self) -> None:
        evidence = v4_evidence()
        stage = evidence["research"]["test"]
        stage["equity_curve"][-1]["equity"] = 200_000.0
        stage["total_return_pct"] = 100.0
        stage["final_equity"] = 200_000.0
        stage["max_drawdown_pct"] = 0.0
        rebuild_self_signed_research_chain(evidence)

        pack = assemble_internal_backtest_pack(
            evidence, generated_at=100,
            schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
        )

        self.assert_v4_source_block_redacts_numeric_claims(
            pack,
            blocker_fragment="research_document_projection_mismatch",
        )

    def test_v4_benchmark_declared_return_coherent_reseal_is_valid_blocked_artifact(self) -> None:
        evidence = v4_evidence()
        benchmark = evidence["research"]["test_benchmark"]
        benchmark["total_return_pct"] = -50.0
        benchmark.pop("benchmark_run_hash", None)
        benchmark["benchmark_run_hash"] = canonical_hash(benchmark)
        rebuild_self_signed_research_chain(evidence)

        pack = assemble_internal_backtest_pack(
            evidence, generated_at=100,
            schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
        )

        self.assert_v4_source_block_redacts_numeric_claims(
            pack,
            blocker_fragment="test_benchmark_total_return_pct_mismatch",
        )

    def test_v4_resealed_return_cost_or_statistical_projection_tamper_is_blocked(self) -> None:
        original = assemble_internal_backtest_pack(
            v4_evidence(), generated_at=100,
            schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
        )
        mutations = (
            ("return", lambda quality: quality["summary"].__setitem__("strategy_return_pct", 999.0)),
            (
                "cost",
                lambda quality: quality["cost_after"]["stress_scenarios"][0].__setitem__(
                    "return_pct",
                    999.0,
                ),
            ),
            (
                "statistical",
                lambda quality: quality["stages"]["test"]["statistical_claim"].__setitem__(
                    "status",
                    "PASS",
                ),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                forged = deepcopy(original)
                mutate(forged["return_quality"])
                reseal_pack(forged)

                result = verify_internal_backtest_pack(forged)

                self.assertEqual(result["status"], "BLOCK")
                self.assertIn("backtest_pack_return_quality_semantic_mismatch", result["blockers"])

    def test_v4_missing_or_resealed_source_identity_is_blocked(self) -> None:
        original = assemble_internal_backtest_pack(
            v4_evidence(), generated_at=100,
            schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
        )
        missing = deepcopy(original)
        missing.pop("return_quality_source_evidence")
        reseal_pack(missing)

        missing_result = verify_internal_backtest_pack(missing)

        self.assertEqual(missing_result["status"], "BLOCK")
        self.assertTrue(any(
            item.startswith("return_quality_source_evidence:")
            for item in missing_result["blockers"]
        ))

        forged = deepcopy(original)
        source = forged["return_quality_source_evidence"]
        source["source_identity"]["strategy_schema7_preregistration_status"] = "PASS"
        identity_content = deepcopy(source["source_identity"])
        identity_content.pop("identity_hash", None)
        source["source_identity"]["identity_hash"] = canonical_hash(identity_content)
        source_content = deepcopy(source)
        source_content.pop("source_evidence_hash", None)
        source["source_evidence_hash"] = canonical_hash(source_content)
        forged["return_quality"]["source_identity"] = deepcopy(source["source_identity"])
        forged["return_quality"]["source_evidence_hash"] = source["source_evidence_hash"]
        reseal_pack(forged)

        forged_result = verify_internal_backtest_pack(forged)

        self.assertEqual(forged_result["status"], "BLOCK")
        self.assertIn(
            "return_quality_source_evidence:return_quality_source_integrity_status_inconsistent",
            forged_result["blockers"],
        )
        self.assertIn(
            "backtest_pack_return_quality_semantic_mismatch",
            forged_result["blockers"],
        )

    def test_v4_resealed_statistical_source_detail_fails_semantic_recomputation(self) -> None:
        forged = assemble_internal_backtest_pack(
            v4_evidence(), generated_at=100,
            schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
        )
        source = forged["return_quality_source_evidence"]
        statistical = source["statistical"]
        stage = statistical["stages"]["test"]
        stage["observation_count"] = 999
        stage_content = deepcopy(stage)
        stage_content.pop("stage_hash", None)
        stage["stage_hash"] = canonical_hash(stage_content)
        statistical["audit_hash"] = canonical_hash(statistical_audit_content(statistical))
        source["source_identity"]["statistical_audit_hash"] = statistical["audit_hash"]
        identity_content = deepcopy(source["source_identity"])
        identity_content.pop("identity_hash", None)
        source["source_identity"]["identity_hash"] = canonical_hash(identity_content)
        source_content = deepcopy(source)
        source_content.pop("source_evidence_hash", None)
        source["source_evidence_hash"] = canonical_hash(source_content)
        forged["return_quality"]["source_identity"] = deepcopy(source["source_identity"])
        forged["return_quality"]["source_evidence_hash"] = source["source_evidence_hash"]
        reseal_pack(forged)

        result = verify_internal_backtest_pack(forged)

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn(
            "return_quality_source_evidence:return_quality_source_integrity_status_inconsistent",
            result["blockers"],
        )
        self.assertIn(
            "backtest_pack_return_quality_semantic_mismatch",
            result["blockers"],
        )

    def test_v4_resealed_source_return_equity_or_nested_authority_is_blocked(self) -> None:
        original = assemble_internal_backtest_pack(
            v4_evidence(), generated_at=100,
            schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
        )
        mutations = (
            (
                "return",
                lambda source: source["research"]["test"].__setitem__(
                    "total_return_pct",
                    999.0,
                ),
            ),
            (
                "equity",
                lambda source: source["research"]["test"]["equity_curve"][-1].__setitem__(
                    "equity",
                    999_999.0,
                ),
            ),
            (
                "authority",
                lambda source: source["research"]["test"].__setitem__(
                    "can_trade",
                    True,
                ),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                forged = deepcopy(original)
                source = forged["return_quality_source_evidence"]
                mutate(source)
                source_content = deepcopy(source)
                source_content.pop("source_evidence_hash", None)
                source["source_evidence_hash"] = canonical_hash(source_content)
                forged["return_quality"]["source_evidence_hash"] = source[
                    "source_evidence_hash"
                ]
                reseal_pack(forged)

                result = verify_internal_backtest_pack(forged)

                self.assertEqual(result["status"], "BLOCK")
                self.assertTrue(any(
                    item.startswith("return_quality_source_evidence:")
                    or item == "backtest_pack_return_quality_semantic_mismatch"
                    or item == "backtest_pack_contains_execution_authority"
                    for item in result["blockers"]
                ))


if __name__ == "__main__":
    unittest.main()
