from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import run_internal_backtest

from exchange_terminal.services import portfolio_backtest_pack_pointer
from exchange_terminal.services.immutable_json_artifact import (
    json_artifact_bytes,
    publish_json_artifact_no_clobber,
)
from exchange_terminal.services.immutable_artifact_bundle import (
    DEFAULT_BUNDLE_MANIFEST_FILE,
    publish_immutable_artifact_bundle,
)
from exchange_terminal.services.portfolio_backtest_pack import (
    CURRENT_PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION,
    PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION,
    PORTFOLIO_INTERNAL_BACKTEST_PACK_V3_SCHEMA_VERSION,
    PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
    PORTFOLIO_INTERNAL_BACKTEST_PACK_V5_SCHEMA_VERSION,
    PORTFOLIO_INTERNAL_BACKTEST_PACK_V6_SCHEMA_VERSION,
    assemble_internal_backtest_pack,
    canonical_hash,
    verify_internal_backtest_bundle,
    verify_internal_backtest_pack,
)
from exchange_terminal.services.portfolio_backtest_pack_pointer import (
    DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE,
    MAX_PORTFOLIO_BACKTEST_PACK_POINTER_BYTES,
    MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_MEMBER_BYTES,
    MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_TOTAL_BYTES,
    MAX_PUBLIC_PORTFOLIO_BACKTEST_PACK_BYTES,
    PORTFOLIO_BACKTEST_BUNDLE_POINTER_SCHEMA_VERSION,
    PORTFOLIO_BACKTEST_FORWARD_PROMOTION_SUMMARY_SCHEMA_VERSION,
    PORTFOLIO_BACKTEST_FORWARD_PROMOTION_SUMMARY_V2_SCHEMA_VERSION,
    PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_SCHEMA_VERSION,
    PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_V3_SCHEMA_VERSION,
    PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_V4_SCHEMA_VERSION,
    load_portfolio_backtest_return_quality_snapshot,
    portfolio_backtest_bundle_manifest_bindings,
    portfolio_backtest_bundle_member_roles,
    portfolio_backtest_bundle_pointer_receipt_bindings,
    pointer_publication_eligibility,
    project_verified_portfolio_backtest_return_quality_snapshot,
    publish_portfolio_backtest_bundle_pointer,
    publish_portfolio_backtest_pack_pointer,
    verify_persisted_portfolio_backtest_bundle_pointer,
    verify_portfolio_backtest_bundle_pointer,
)
from exchange_terminal.services.portfolio_forward_statistical_audit import (
    forward_statistical_audit_v2_content,
)
from tests.test_portfolio_backtest_pack import (
    forward_projection,
    forward_projection_v2,
    sealed_v3_pack,
    sealed_v6_pack,
    v4_evidence,
    v5_bundle,
)


def reseal(pack: dict[str, object]) -> dict[str, object]:
    payload = deepcopy(pack)
    payload.pop("pack_hash", None)
    payload.pop("evidence_hash", None)
    evidence = deepcopy(payload)
    evidence.pop("generated_at", None)
    payload["evidence_hash"] = canonical_hash(evidence)
    payload["pack_hash"] = canonical_hash(payload)
    return payload


def publish_current_bundle_directory(
    report_dir: Path,
    *,
    prefix: str = "portfolio-backtest-test-bundle",
    generated_at: int = 100,
    pack_raw_suffix: bytes = b"",
) -> tuple[dict[str, object], list[dict[str, object]], dict[str, object]]:
    _legacy_pack, artifacts = v5_bundle()
    pack = assemble_internal_backtest_pack(v4_evidence(), generated_at=100)
    if generated_at != 100:
        pack = deepcopy(pack)
        pack["generated_at"] = generated_at
        pack = reseal(pack)
    pack_file = "pack.json"
    members = {pack_file: json_artifact_bytes(pack) + pack_raw_suffix}
    for artifact in artifacts:
        members[str(artifact["file"])] = artifact["raw_bytes"]
    publication = publish_immutable_artifact_bundle(
        report_dir,
        members,
        member_roles=portfolio_backtest_bundle_member_roles(pack, pack_file=pack_file),
        bindings=portfolio_backtest_bundle_manifest_bindings(pack, pack_file=pack_file),
        bundle_name_prefix=prefix,
        max_member_count=3,
        max_member_bytes=MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_MEMBER_BYTES,
        max_total_bytes=MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_TOTAL_BYTES,
    )
    if publication.get("status") not in {"PUBLISHED", "EXISTING_IDENTICAL"}:
        raise AssertionError(publication)
    return pack, artifacts, publication


def frozen_block_pack() -> dict[str, object]:
    pack = assemble_internal_backtest_pack(
        {},
        generated_at=100,
        schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION,
    )
    pack["return_quality"] = {
        "schema_version": "backtest-return-quality-v1",
        "status": "BLOCK",
        "interpretation": "DESCRIPTIVE_HISTORICAL_EVIDENCE_ONLY",
        "summary": {
            "strategy_return_pct": 3.0,
            "benchmark_return_pct": 2.0,
            "benchmark_excess_return_pct": 1.0,
            "benchmark_excess_status": "AVAILABLE",
            "cost_after_return_pct": 2.5,
            "cost_after_status": "AVAILABLE",
            "worst_stress_return_pct": -0.5,
            "max_drawdown_pct": 7.0,
            "sample_size": 120,
            "sample_unit": "PAIRED_RETURN_OBSERVATIONS",
            "evidence_stage": "DEVELOPMENT_HISTORICAL",
        },
        "stages": {
            "validation": {
                "stage": "VALIDATION",
                "evidence_status": "AVAILABLE",
                "benchmark_excess_status": "AVAILABLE",
                "benchmark_excess_basis": "RECOMPUTED_FROM_STRATEGY_AND_BENCHMARK_RETURNS",
                "strategy_return_pct": 4.0,
                "benchmark_return_pct": 3.0,
                "benchmark_excess_return_pct": 1.0,
                "reported_benchmark_excess_return_pct": 1.0,
                "strategy_max_drawdown_pct": 6.0,
                "benchmark_max_drawdown_pct": 8.0,
                "drawdown_improvement_pct": 2.0,
                "sample": {
                    "evaluated_rows": 121,
                    "order_event_count": 9,
                    "decision_event_count": 18,
                    "paired_return_observation_count": 120,
                    "internal_path": "must-not-leak",
                },
                "statistical_claim": {
                    "status": "PASS",
                    "observed_strategy_compound_return_pct": 4.0,
                    "observed_benchmark_compound_return_pct": 3.0,
                    "observed_compound_excess_return_pct": 1.0,
                    "blockers": [],
                    "secret": "must-not-leak",
                },
                "quality_flags": {
                    "strategy_return_positive": True,
                    "benchmark_excess_positive": True,
                    "unknown_flag": True,
                },
                "unknown_stage_field": "must-not-leak",
            },
            "test": {
                "stage": "TEST",
                "evidence_status": "AVAILABLE",
                "benchmark_excess_status": "AVAILABLE",
                "benchmark_excess_basis": "RECOMPUTED_FROM_STRATEGY_AND_BENCHMARK_RETURNS",
                "strategy_return_pct": 3.0,
                "benchmark_return_pct": 2.0,
                "benchmark_excess_return_pct": 1.0,
                "reported_benchmark_excess_return_pct": 1.0,
                "strategy_max_drawdown_pct": 7.0,
                "benchmark_max_drawdown_pct": 9.0,
                "drawdown_improvement_pct": 2.0,
                "sample": {
                    "evaluated_rows": 121,
                    "order_event_count": 10,
                    "decision_event_count": 19,
                    "paired_return_observation_count": 120,
                },
                "statistical_claim": {
                    "status": "BLOCK",
                    "observed_strategy_compound_return_pct": 3.0,
                    "observed_benchmark_compound_return_pct": 2.0,
                    "observed_compound_excess_return_pct": 1.0,
                    "blockers": ["bootstrap_probability"],
                },
                "quality_flags": {
                    "strategy_return_positive": True,
                    "benchmark_excess_positive": True,
                },
            },
        },
        "cost_after": {
            "status": "BLOCK",
            "baseline_model": {
                "status": "AVAILABLE",
                "fee_rate": 0.0005,
                "slippage_bps": 2.0,
                "test_return_after_configured_costs_pct": 2.5,
                "configured_costs_declared_in_test_run": True,
            },
            "stress_contract": {
                "status": "AVAILABLE",
                "expected_labels": ["SEVERE"],
                "reported_labels": ["SEVERE"],
            },
            "stress_scenarios": [
                {
                    "label": "SEVERE",
                    "status": "AVAILABLE",
                    "contract_match": True,
                    "fee_rate": 0.002,
                    "slippage_bps": 10.0,
                    "return_pct": -0.5,
                    "max_drawdown_pct": 8.0,
                    "internal_path": "must-not-leak",
                }
            ],
            "worst_stress_return_pct": -0.5,
            "worst_stress_max_drawdown_pct": 8.0,
            "all_stress_returns_positive": False,
            "unknown_secret_field": "must-not-leak",
        },
        "statistical_claim_status": "BLOCK",
        "failure_conditions": {
            "source_integrity": [],
            "observed": ["historical_statistical_claim_block"],
            "evidence_gaps": [],
            "promotion_gaps": ["natural_forward_observation_required"],
        },
        "unknown_top_level": "must-not-leak",
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "automatic_paper_activation_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return reseal(pack)


def write_pack(report_dir: Path, pack: dict[str, object], name: str = "frozen_pack.json") -> Path:
    path = report_dir / name
    path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")
    return path


def ready_cli_pack() -> dict[str, object]:
    return {
        "schema_version": CURRENT_PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION,
        "status": "INTERNAL_BACKTEST_EVIDENCE_READY",
        "promotion_status": "BLOCK",
        "candidate": {"candidate_hash": "a" * 64},
        "pack_hash": "b" * 64,
        "evidence_hash": "d" * 64,
        "blockers": [],
        "promotion_blockers": ["natural_forward_observation_required"],
        "forward_progress": {},
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def ready_cli_pointer_receipt(*, published: bool = True) -> dict[str, object]:
    pack = ready_cli_pack()
    file_sha256 = hashlib.sha256(json_artifact_bytes(pack)).hexdigest()
    return {
        "status": "PUBLISHED",
        "published": published,
        "blockers": [],
        "pack_hash": pack["pack_hash"],
        "evidence_hash": pack["evidence_hash"],
        "pack_status": pack["status"],
        "pack_file_sha256": file_sha256,
    }


def v3_forward_pack(*, outcomes: int, required: int, weak_edge: bool = False) -> dict[str, object]:
    pack = sealed_v3_pack(
        forward_projection(outcomes=outcomes, required=required, weak_edge=weak_edge)
    )
    pack["return_quality"] = deepcopy(frozen_block_pack()["return_quality"])
    return reseal(pack)


class PortfolioBacktestPackPointerTests(unittest.TestCase):
    def test_current_version_aliases_are_v6_evidence_v2_snapshot_v4_summary_v2(self) -> None:
        self.assertEqual(
            CURRENT_PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION,
            PORTFOLIO_INTERNAL_BACKTEST_PACK_V6_SCHEMA_VERSION,
        )
        self.assertEqual(
            PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_SCHEMA_VERSION,
            PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_V4_SCHEMA_VERSION,
        )
        self.assertEqual(
            PORTFOLIO_BACKTEST_FORWARD_PROMOTION_SUMMARY_SCHEMA_VERSION,
            PORTFOLIO_BACKTEST_FORWARD_PROMOTION_SUMMARY_V2_SCHEMA_VERSION,
        )

    def test_legacy_v5_bundle_verifies_historically_but_v2_pointer_is_public_unknown(self) -> None:
        pack, artifacts = v5_bundle()
        self.assertEqual(
            pack["schema_version"],
            PORTFOLIO_INTERNAL_BACKTEST_PACK_V5_SCHEMA_VERSION,
        )
        self.assertEqual(
            verify_internal_backtest_bundle(pack, artifacts)["status"],
            "PASS",
        )
        pack_file = "pack.json"
        members = {pack_file: json_artifact_bytes(pack)}
        for artifact in artifacts:
            members[str(artifact["file"])] = artifact["raw_bytes"]
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            publication = publish_immutable_artifact_bundle(
                report_dir,
                members,
                member_roles=portfolio_backtest_bundle_member_roles(
                    pack,
                    pack_file=pack_file,
                ),
                bindings=portfolio_backtest_bundle_manifest_bindings(
                    pack,
                    pack_file=pack_file,
                ),
                bundle_name_prefix="legacy-v5-pointer-v2",
                max_member_count=3,
                max_member_bytes=MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_MEMBER_BYTES,
                max_total_bytes=MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_TOTAL_BYTES,
            )
            pointer = portfolio_backtest_pack_pointer._build_bundle_pointer(
                bundle_dir=Path(str(publication["bundle_dir"])).name,
                bundle_semantics={
                    "manifest_file_sha256": publication["manifest_file_sha256"],
                    "bundle_hash": publication["bundle_hash"],
                    "pack_file": pack_file,
                    "pack_file_sha256": hashlib.sha256(members[pack_file]).hexdigest(),
                    "pack": pack,
                },
            )
            (report_dir / DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE).write_text(
                json.dumps(pointer, ensure_ascii=True, sort_keys=True),
                encoding="utf-8",
            )
            snapshot = load_portfolio_backtest_return_quality_snapshot(report_dir)

        self.assertEqual(
            pointer["schema_version"],
            PORTFOLIO_BACKTEST_BUNDLE_POINTER_SCHEMA_VERSION,
        )
        self.assertEqual(snapshot["schema_version"], PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_SCHEMA_VERSION)
        self.assertFalse(snapshot["ok"])
        self.assertEqual(snapshot["status"], "UNKNOWN")
        self.assertIsNone(snapshot["return_quality"])
        self.assertIsNone(snapshot["forward_promotion"])

    def test_current_v4_snapshot_keeps_frozen_decision_and_describes_tail(self) -> None:
        first_pack = sealed_v6_pack(forward_projection_v2(outcomes=8, required=8))
        tail_pack = sealed_v6_pack(forward_projection_v2(outcomes=12, required=8))
        pointer = {"generated_at": 100}

        first = project_verified_portfolio_backtest_return_quality_snapshot(
            pointer,
            first_pack,
            schema_version=PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_V4_SCHEMA_VERSION,
        )
        tail = project_verified_portfolio_backtest_return_quality_snapshot(
            pointer,
            tail_pack,
            schema_version=PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_V4_SCHEMA_VERSION,
        )
        wrong_version = project_verified_portfolio_backtest_return_quality_snapshot(
            pointer,
            tail_pack,
            schema_version=PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_V3_SCHEMA_VERSION,
        )

        self.assertTrue(first["ok"])
        self.assertTrue(tail["ok"])
        self.assertEqual(
            tail["schema_version"],
            PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_V4_SCHEMA_VERSION,
        )
        self.assertEqual(
            tail["forward_promotion"]["schema_version"],
            PORTFOLIO_BACKTEST_FORWARD_PROMOTION_SUMMARY_V2_SCHEMA_VERSION,
        )
        self.assertEqual(
            first["forward_promotion"]["decision"]["decision_hash"],
            tail["forward_promotion"]["decision"]["decision_hash"],
        )
        self.assertNotEqual(
            first["forward_promotion"]["tail_observation"]["full_series_hash"],
            tail["forward_promotion"]["tail_observation"]["full_series_hash"],
        )
        self.assertEqual(
            first["forward_promotion"]["tail_observation"]["later_settlement_count"],
            0,
        )
        self.assertEqual(
            tail["forward_promotion"]["tail_observation"]["later_settlement_count"],
            4,
        )
        self.assertTrue(
            tail["forward_promotion"]["tail_observation"][
                "later_settlements_descriptive_only"
            ]
        )
        self.assertFalse(wrong_version["ok"])
        self.assertIn(
            "pack_public_snapshot_schema_coupling_invalid",
            wrong_version["blockers"],
        )

    def test_v2_pointer_fields_and_hash_are_unchanged_for_noncurrent_pure_binding(self) -> None:
        pack = sealed_v6_pack(forward_projection_v2(outcomes=8, required=8))
        semantics = {
            "manifest_file_sha256": "a" * 64,
            "bundle_hash": "b" * 64,
            "pack_file": "pack.json",
            "pack_file_sha256": "c" * 64,
            "pack": pack,
        }
        pointer = portfolio_backtest_pack_pointer._build_bundle_pointer(
            bundle_dir="preview-bundle",
            bundle_semantics=semantics,
        )
        content = dict(pointer)
        pointer_hash = content.pop("pointer_hash")

        self.assertEqual(
            pointer["schema_version"],
            PORTFOLIO_BACKTEST_BUNDLE_POINTER_SCHEMA_VERSION,
        )
        self.assertEqual(set(pointer), portfolio_backtest_pack_pointer._POINTER_V2_FIELDS)
        self.assertEqual(pointer_hash, canonical_hash(content))
        self.assertEqual(
            pointer["pack_schema_version"],
            PORTFOLIO_INTERNAL_BACKTEST_PACK_V6_SCHEMA_VERSION,
        )
        self.assertEqual(
            portfolio_backtest_pack_pointer._POINTER_V2_FIELDS,
            {
                "schema_version",
                "status",
                "bundle_dir",
                "manifest_file",
                "manifest_file_sha256",
                "bundle_hash",
                "pack_file",
                "pack_file_sha256",
                "pack_schema_version",
                "candidate_hash",
                "pack_hash",
                "evidence_hash",
                "pack_status",
                "promotion_status",
                "generated_at",
                "research_only",
                "profitability_proven",
                "performance_claim_allowed",
                "parameter_selection_allowed",
                "automatic_paper_activation_allowed",
                "paper_authorized",
                "live_order_allowed",
                "pointer_hash",
            },
        )

    def test_noncurrent_v4_snapshot_fails_closed_on_missing_or_mixed_risk(self) -> None:
        cases = ("missing", "mixed")
        for label in cases:
            with self.subTest(label=label):
                projection = forward_projection_v2(outcomes=8, required=8)
                risk_owner = projection["forward_statistical_audit"]["decision_window"]
                if label == "missing":
                    risk_owner.pop("risk_acceptance")
                else:
                    risk_owner["risk_acceptance"]["status"] = "BLOCK"
                projection_content = deepcopy(projection)
                projection_content.pop("projection_hash", None)
                projection["projection_hash"] = canonical_hash(projection_content)
                pack = sealed_v6_pack(projection)

                snapshot = project_verified_portfolio_backtest_return_quality_snapshot(
                    {"generated_at": 100},
                    pack,
                    schema_version=(
                        PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_V4_SCHEMA_VERSION
                    ),
                )

                self.assertFalse(snapshot["ok"])
                self.assertEqual(snapshot["status"], "UNKNOWN")
                self.assertIn(
                    "forward_promotion_summary_unavailable",
                    snapshot["blockers"],
                )
                self.assertIsNone(snapshot["forward_promotion"])

    def test_noncurrent_v4_snapshot_hides_coherently_resealed_audit_failure(self) -> None:
        projection = deepcopy(forward_projection_v2(outcomes=8, required=8))
        audit = projection["forward_statistical_audit"]
        audit["checks"]["settlement_series_integrity_pass"] = False
        audit["audit_hash"] = canonical_hash(
            forward_statistical_audit_v2_content(audit)
        )
        projection["readiness"]["forward_statistical_audit"]["audit_hash"] = audit[
            "audit_hash"
        ]
        projection_content = deepcopy(projection)
        projection_content.pop("projection_hash", None)
        projection["projection_hash"] = canonical_hash(projection_content)

        snapshot = project_verified_portfolio_backtest_return_quality_snapshot(
            {"generated_at": 100},
            sealed_v6_pack(projection),
            schema_version=(
                PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_V4_SCHEMA_VERSION
            ),
        )

        self.assertFalse(snapshot["ok"])
        self.assertEqual(snapshot["status"], "UNKNOWN")
        self.assertEqual(snapshot["source_verification_status"], "BLOCK")
        self.assertIn(
            "forward_promotion_summary_unavailable",
            snapshot["blockers"],
        )
        self.assertIsNone(snapshot["forward_promotion"])

    def test_noncurrent_v4_snapshot_projects_collecting_and_frozen_block(self) -> None:
        scenarios = (
            (
                forward_projection_v2(outcomes=7, required=8),
                "COLLECTING",
                "NOT_DUE",
                "COLLECT_MORE",
            ),
            (
                forward_projection_v2(outcomes=12, required=8, weak_edge=True),
                "RESEARCH_REVIEW_BLOCKED",
                "BLOCK",
                "STOP_RESEARCH",
            ),
        )
        for projection, status, audit_status, action in scenarios:
            with self.subTest(status=status):
                snapshot = project_verified_portfolio_backtest_return_quality_snapshot(
                    {"generated_at": 100},
                    sealed_v6_pack(projection),
                    schema_version=(
                        PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_V4_SCHEMA_VERSION
                    ),
                )
                summary = snapshot["forward_promotion"]
                self.assertTrue(snapshot["ok"])
                self.assertEqual(summary["status"], status)
                self.assertEqual(summary["audit"]["status"], audit_status)
                self.assertEqual(summary["decision"]["research_action"], action)
                self.assertFalse(summary["profitability_proven"])
                self.assertFalse(summary["paper_authorized"])
                self.assertFalse(summary["live_order_allowed"])

    def test_public_artifact_byte_budgets_are_explicit(self) -> None:
        self.assertEqual(MAX_PORTFOLIO_BACKTEST_PACK_POINTER_BYTES, 64 * 1024)
        self.assertEqual(MAX_PUBLIC_PORTFOLIO_BACKTEST_PACK_BYTES, 32 * 1024 * 1024)

    def test_v2_bundle_pointer_publishes_v6_and_current_snapshot_is_v4(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            pack, _artifacts, bundle_publication = publish_current_bundle_directory(report_dir)
            bundle_dir = Path(str(bundle_publication["bundle_dir"]))
            publication = publish_portfolio_backtest_bundle_pointer(
                report_dir,
                bundle_dir,
                expected_bundle_hash=str(bundle_publication["bundle_hash"]),
                expected_manifest_file_sha256=str(
                    bundle_publication["manifest_file_sha256"]
                ),
                expected_pack_file_sha256=hashlib.sha256(
                    json_artifact_bytes(pack)
                ).hexdigest(),
                expected_pack_hash=str(pack["pack_hash"]),
                expected_evidence_hash=str(pack["evidence_hash"]),
                expected_pack_status=str(pack["status"]),
            )
            pointer = json.loads(
                (report_dir / DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE).read_text(
                    encoding="utf-8"
                )
            )
            snapshot = load_portfolio_backtest_return_quality_snapshot(report_dir)

        self.assertEqual(publication["status"], "PUBLISHED")
        self.assertTrue(publication["published"])
        self.assertEqual(
            pointer["schema_version"],
            PORTFOLIO_BACKTEST_BUNDLE_POINTER_SCHEMA_VERSION,
        )
        self.assertEqual(pointer["bundle_dir"], bundle_dir.name)
        self.assertEqual(pointer["bundle_hash"], bundle_publication["bundle_hash"])
        self.assertEqual(snapshot["schema_version"], PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_SCHEMA_VERSION)
        self.assertFalse(snapshot["ok"])
        self.assertEqual(snapshot["status"], "UNKNOWN")
        self.assertIn("forward_promotion_summary_unavailable", snapshot["blockers"])
        self.assertIsNone(snapshot["return_quality"])
        serialized = json.dumps(snapshot, ensure_ascii=False)
        self.assertNotIn("return_quality_source_manifest", serialized)
        self.assertNotIn("source_identity", serialized)
        self.assertNotIn("detached_source_binding_hash", serialized)

    def test_v2_pointer_requires_complete_expected_bindings_and_core_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            _pack, _artifacts, bundle_publication = publish_current_bundle_directory(report_dir)
            bundle_dir = Path(str(bundle_publication["bundle_dir"]))
            incomplete = publish_portfolio_backtest_bundle_pointer(
                report_dir,
                bundle_dir,
                expected_bundle_hash=str(bundle_publication["bundle_hash"]),
            )
            with patch.object(
                portfolio_backtest_pack_pointer,
                "verify_internal_backtest_bundle",
                return_value={
                    "status": "BLOCK",
                    "artifact_contract_status": "PASS",
                    "return_quality": {
                        "source_integrity_status": "BLOCK",
                        "numeric_claims_available": False,
                    },
                },
            ):
                core_blocked = publish_portfolio_backtest_bundle_pointer(
                    report_dir,
                    bundle_dir,
                )

        self.assertEqual(incomplete["status"], "BLOCK")
        self.assertEqual(
            incomplete["blockers"],
            ["bundle_pointer_expected_binding_incomplete"],
        )
        self.assertEqual(core_blocked["status"], "BLOCK")
        self.assertIn("portfolio_bundle_core_verification_blocked", core_blocked["blockers"])
        self.assertIn("portfolio_bundle_core_source_integrity_blocked", core_blocked["blockers"])

    def test_v2_pointer_blocks_stale_and_same_timestamp_conflicting_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            _new_pack, _new_artifacts, newer = publish_current_bundle_directory(
                report_dir,
                prefix="newer-bundle",
                generated_at=200,
            )
            self.assertEqual(
                publish_portfolio_backtest_bundle_pointer(
                    report_dir,
                    newer["bundle_dir"],
                )["status"],
                "PUBLISHED",
            )
            pointer_path = report_dir / DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE
            newer_pointer_bytes = pointer_path.read_bytes()
            _old_pack, _old_artifacts, older = publish_current_bundle_directory(
                report_dir,
                prefix="older-bundle",
                generated_at=100,
            )
            stale = publish_portfolio_backtest_bundle_pointer(
                report_dir,
                older["bundle_dir"],
            )
            after_stale_pointer_bytes = pointer_path.read_bytes()

        self.assertEqual(stale["status"], "BLOCK")
        self.assertEqual(stale["blockers"], ["bundle_pointer_stale_publication_blocked"])
        self.assertEqual(after_stale_pointer_bytes, newer_pointer_bytes)

        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            _first_pack, _first_artifacts, first = publish_current_bundle_directory(
                report_dir,
                prefix="same-time-first",
                generated_at=100,
            )
            self.assertEqual(
                publish_portfolio_backtest_bundle_pointer(
                    report_dir,
                    first["bundle_dir"],
                )["status"],
                "PUBLISHED",
            )
            pointer_path = report_dir / DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE
            first_pointer_bytes = pointer_path.read_bytes()
            _second_pack, _second_artifacts, second = publish_current_bundle_directory(
                report_dir,
                prefix="same-time-second",
                generated_at=100,
                pack_raw_suffix=b" ",
            )
            conflict = publish_portfolio_backtest_bundle_pointer(
                report_dir,
                second["bundle_dir"],
            )
            after_conflict_pointer_bytes = pointer_path.read_bytes()

        self.assertEqual(conflict["status"], "BLOCK")
        self.assertEqual(conflict["blockers"], ["bundle_pointer_same_timestamp_conflict"])
        self.assertEqual(after_conflict_pointer_bytes, first_pointer_bytes)

    def test_v2_pointer_publication_lock_is_nonblocking_and_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            _pack, _artifacts, bundle = publish_current_bundle_directory(report_dir)
            pointer_path = report_dir / DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE
            lock_path = pointer_path.with_name(f".{pointer_path.name}.lock")
            lock_path.write_bytes(b"")

            publication = publish_portfolio_backtest_bundle_pointer(
                report_dir,
                bundle["bundle_dir"],
            )

            self.assertEqual(publication["status"], "BLOCK")
            self.assertEqual(publication["blockers"], ["pointer_publication_locked"])
            self.assertFalse(pointer_path.exists())
            self.assertTrue(lock_path.exists())

    def test_v2_pointer_lock_prevents_older_concurrent_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            _old_pack, _old_artifacts, older = publish_current_bundle_directory(
                report_dir,
                prefix="concurrent-older",
                generated_at=100,
            )
            _new_pack, _new_artifacts, newer = publish_current_bundle_directory(
                report_dir,
                prefix="concurrent-newer",
                generated_at=200,
            )
            entered_lock = threading.Event()
            release_newer = threading.Event()
            newer_result: list[dict[str, object]] = []
            real_reader = portfolio_backtest_pack_pointer._read_valid_current_bundle_pointer

            def controlled_reader(directory: Path, pointer_path: Path) -> dict[str, object] | None:
                if threading.current_thread().name == "newer-pointer-publisher":
                    entered_lock.set()
                    if not release_newer.wait(timeout=5):
                        raise AssertionError("test coordination timeout")
                return real_reader(directory, pointer_path)

            def publish_newer() -> None:
                newer_result.append(
                    publish_portfolio_backtest_bundle_pointer(
                        report_dir,
                        newer["bundle_dir"],
                    )
                )

            with patch.object(
                portfolio_backtest_pack_pointer,
                "_read_valid_current_bundle_pointer",
                side_effect=controlled_reader,
            ):
                thread = threading.Thread(
                    target=publish_newer,
                    name="newer-pointer-publisher",
                )
                thread.start()
                self.assertTrue(entered_lock.wait(timeout=5))
                older_result = publish_portfolio_backtest_bundle_pointer(
                    report_dir,
                    older["bundle_dir"],
                )
                release_newer.set()
                thread.join(timeout=5)

            self.assertFalse(thread.is_alive())
            self.assertEqual(older_result["status"], "BLOCK")
            self.assertEqual(older_result["blockers"], ["pointer_publication_locked"])
            self.assertEqual(newer_result[0]["status"], "PUBLISHED")
            pointer = json.loads(
                (report_dir / DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(pointer["generated_at"], 200)
            self.assertEqual(pointer["bundle_dir"], Path(str(newer["bundle_dir"])).name)

    def test_v2_pointer_lock_cleanup_failure_is_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            _pack, _artifacts, bundle = publish_current_bundle_directory(report_dir)
            pointer_path = report_dir / DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE
            lock_path = pointer_path.with_name(f".{pointer_path.name}.lock")
            real_unlink = Path.unlink

            def fail_lock_cleanup(path: Path, *args: object, **kwargs: object) -> None:
                if path == lock_path:
                    raise PermissionError("synthetic lock cleanup failure")
                real_unlink(path, *args, **kwargs)

            with patch("pathlib.Path.unlink", new=fail_lock_cleanup):
                publication = publish_portfolio_backtest_bundle_pointer(
                    report_dir,
                    bundle["bundle_dir"],
                )

            self.assertEqual(publication["status"], "BLOCK")
            self.assertEqual(
                publication["blockers"],
                ["pointer_publication_lock_cleanup_failed"],
            )
            self.assertFalse(publication["published"])
            self.assertTrue(pointer_path.exists())
            self.assertTrue(lock_path.exists())

    def test_v2_pointer_existing_identical_receipt_hash_is_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            pack, _artifacts, bundle = publish_current_bundle_directory(report_dir)
            bundle_dir = Path(str(bundle["bundle_dir"]))
            first = publish_portfolio_backtest_bundle_pointer(report_dir, bundle_dir)
            second = publish_portfolio_backtest_bundle_pointer(report_dir, bundle_dir)
            expected = portfolio_backtest_bundle_pointer_receipt_bindings(
                bundle_dir_name=bundle_dir.name,
                manifest_file_sha256=str(bundle["manifest_file_sha256"]),
                bundle_hash=str(bundle["bundle_hash"]),
                pack_file="pack.json",
                pack_file_sha256=hashlib.sha256(json_artifact_bytes(pack)).hexdigest(),
                pack=pack,
            )

            self.assertEqual(first["status"], "PUBLISHED")
            self.assertEqual(second["status"], "EXISTING_IDENTICAL")
            for field, value in expected.items():
                self.assertEqual(second[field], value)
            persisted = verify_persisted_portfolio_backtest_bundle_pointer(
                report_dir,
                expected_bindings=expected,
            )
            self.assertEqual(persisted["status"], "PASS")
            for field, value in expected.items():
                self.assertEqual(persisted[field], value)

    def test_strict_json_rejects_duplicate_nonfinite_and_deep_documents(self) -> None:
        duplicate = b'{"schema_version":"x","schema_version":"x"}'
        for raw in (
            duplicate,
            b'{"value":NaN}',
            b'{"value":Infinity}',
            b'{"value":1e999}',
        ):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    portfolio_backtest_pack_pointer._read_json_object(raw)

        deep = (b'{"value":' * 1400) + b"null" + (b"}" * 1400)
        with self.assertRaises(ValueError):
            portfolio_backtest_pack_pointer._read_json_object(deep)

    def test_current_v2_depth_contract_does_not_retroactively_tighten_v1_parser(self) -> None:
        nested = (b"[" * 127) + b"0" + (b"]" * 127)
        legacy_boundary = (
            b'{"schema_version":"portfolio-backtest-pack-pointer-v1","value":'
            + nested
            + b"}"
        )
        current_boundary = (
            b'{"schema_version":"portfolio-backtest-pack-pointer-v2","value":'
            + nested
            + b"}"
        )

        self.assertIsInstance(
            portfolio_backtest_pack_pointer._read_json_object(legacy_boundary),
            dict,
        )
        with self.assertRaises(ValueError):
            portfolio_backtest_pack_pointer._read_current_json_object(legacy_boundary)
        self.assertEqual(
            portfolio_backtest_pack_pointer._read_pointer_object_by_schema(
                legacy_boundary
            )["schema_version"],
            "portfolio-backtest-pack-pointer-v1",
        )
        with self.assertRaises(ValueError):
            portfolio_backtest_pack_pointer._read_pointer_object_by_schema(
                current_boundary
            )

    def test_duplicate_v1_pointer_or_pack_loads_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            pack = frozen_block_pack()
            pack_path = write_pack(report_dir, pack)
            self.assertEqual(
                publish_portfolio_backtest_pack_pointer(report_dir, pack_path)["status"],
                "PUBLISHED",
            )
            pointer_path = report_dir / DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE
            pointer_raw = pointer_path.read_bytes()
            pointer_path.write_bytes(
                pointer_raw[:-1] + b',"schema_version":"portfolio-backtest-pack-pointer-v1"}'
            )
            duplicate_pointer = load_portfolio_backtest_return_quality_snapshot(report_dir)

            self.assertEqual(duplicate_pointer["status"], "UNKNOWN")
            self.assertIsNone(duplicate_pointer["return_quality"])

            pack_raw = pack_path.read_bytes()
            duplicate_pack_raw = (
                pack_raw[:-1]
                + b',"schema_version":"portfolio-internal-backtest-pack-v2"}'
            )
            pack_path.write_bytes(duplicate_pack_raw)
            duplicate_pack_pointer = portfolio_backtest_pack_pointer._build_pointer(
                pack_path.name,
                hashlib.sha256(duplicate_pack_raw).hexdigest(),
                pack,
            )
            pointer_path.write_text(
                json.dumps(duplicate_pack_pointer),
                encoding="utf-8",
            )
            duplicate_pack = load_portfolio_backtest_return_quality_snapshot(report_dir)

            self.assertEqual(duplicate_pack["status"], "UNKNOWN")
            self.assertIsNone(duplicate_pack["return_quality"])

    def test_v2_malformed_pack_member_blocks_publication_and_loads_unknown(self) -> None:
        pack, artifacts = v5_bundle()
        valid_raw = json_artifact_bytes(pack)
        malformed_cases = {
            "duplicate": (
                valid_raw[:-1]
                + b',"schema_version":"portfolio-internal-backtest-pack-v5"}'
            ),
            "nonfinite": valid_raw[:-1] + b',"synthetic_nonfinite":NaN}',
            "deep": (
                valid_raw[:-1]
                + b',"synthetic_deep":'
                + (b"[" * 140)
                + b"0"
                + (b"]" * 140)
                + b"}"
            ),
        }
        for label, malformed_pack_raw in malformed_cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                report_dir = Path(temporary)
                members = {"pack.json": malformed_pack_raw}
                for artifact in artifacts:
                    members[str(artifact["file"])] = artifact["raw_bytes"]
                bundle = publish_immutable_artifact_bundle(
                    report_dir,
                    members,
                    member_roles=portfolio_backtest_bundle_member_roles(
                        pack,
                        pack_file="pack.json",
                    ),
                    bindings=portfolio_backtest_bundle_manifest_bindings(
                        pack,
                        pack_file="pack.json",
                    ),
                    bundle_name_prefix=f"strict-json-{label}",
                    max_member_count=3,
                    max_member_bytes=MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_MEMBER_BYTES,
                    max_total_bytes=MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_TOTAL_BYTES,
                )
                publication = publish_portfolio_backtest_bundle_pointer(
                    report_dir,
                    bundle["bundle_dir"],
                )
                synthetic_pointer = portfolio_backtest_pack_pointer._build_bundle_pointer(
                    bundle_dir=Path(str(bundle["bundle_dir"])).name,
                    bundle_semantics={
                        "manifest_file_sha256": bundle["manifest_file_sha256"],
                        "bundle_hash": bundle["bundle_hash"],
                        "pack_file": "pack.json",
                        "pack_file_sha256": hashlib.sha256(malformed_pack_raw).hexdigest(),
                        "pack": pack,
                    },
                )
                (report_dir / DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE).write_text(
                    json.dumps(synthetic_pointer),
                    encoding="utf-8",
                )
                snapshot = load_portfolio_backtest_return_quality_snapshot(report_dir)

                self.assertEqual(bundle["status"], "PUBLISHED")
                self.assertEqual(publication["status"], "BLOCK")
                self.assertFalse(snapshot["ok"])
                self.assertEqual(snapshot["status"], "UNKNOWN")
                self.assertIsNone(snapshot["return_quality"])

    def test_v2_pointer_shared_authority_scanner_rejects_canonical_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            _pack, _artifacts, bundle_publication = publish_current_bundle_directory(report_dir)
            bundle_dir = Path(str(bundle_publication["bundle_dir"]))
            self.assertEqual(
                publish_portfolio_backtest_bundle_pointer(report_dir, bundle_dir)["status"],
                "PUBLISHED",
            )
            pointer = json.loads(
                (report_dir / DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE).read_text(
                    encoding="utf-8"
                )
            )
            pointer["ParameterSelectionAuthority"] = True
            pointer_content = dict(pointer)
            pointer_content.pop("pointer_hash", None)
            pointer["pointer_hash"] = canonical_hash(pointer_content)
            bundle = portfolio_backtest_pack_pointer._read_public_backtest_bundle(bundle_dir)
            verification = verify_portfolio_backtest_bundle_pointer(
                pointer,
                bundle=bundle,
                bundle_dir_name=bundle_dir.name,
            )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertTrue(
            any(
                "ParameterSelectionAuthority" in blocker
                for blocker in verification["blockers"]
            ),
            verification,
        )

    def test_pointer_versions_are_exact_and_mismatches_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            v5_pack, _artifacts, v5_publication = publish_current_bundle_directory(report_dir)
            standalone_v5 = write_pack(report_dir, v5_pack, "standalone-v5.json")
            v1_v5 = publish_portfolio_backtest_pack_pointer(report_dir, standalone_v5)

            v4_pack = assemble_internal_backtest_pack(
                v4_evidence(),
                generated_at=100,
                schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
            )
            v4_members = {"pack.json": json_artifact_bytes(v4_pack)}
            v4_bundle = publish_immutable_artifact_bundle(
                report_dir,
                v4_members,
                member_roles={"pack.json": "INTERNAL_BACKTEST_PACK"},
                bindings=portfolio_backtest_bundle_manifest_bindings(
                    v4_pack,
                    pack_file="pack.json",
                ),
                bundle_name_prefix="v4-bundle",
            )
            v2_v4 = publish_portfolio_backtest_bundle_pointer(
                report_dir,
                v4_bundle["bundle_dir"],
            )

            pointer_path = report_dir / DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE
            pointer_path.write_text(
                json.dumps({"schema_version": "portfolio-backtest-pack-pointer-v99"}),
                encoding="utf-8",
            )
            future = load_portfolio_backtest_return_quality_snapshot(report_dir)

        self.assertEqual(v1_v5["status"], "BLOCK")
        self.assertEqual(v1_v5["blockers"], ["pointer_v1_pack_schema_incompatible"])
        self.assertEqual(v2_v4["status"], "BLOCK")
        self.assertFalse(future["ok"])
        self.assertEqual(future["status"], "UNKNOWN")
        self.assertEqual(future["blockers"], ["frozen_pack_pointer_schema_unsupported"])
        self.assertIsNone(future["return_quality"])

    def test_v2_pointer_and_bundle_tampering_return_unknown_null(self) -> None:
        mutations = ("pointer", "pack", "manifest")
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                report_dir = Path(temporary)
                _pack, _artifacts, bundle_publication = publish_current_bundle_directory(
                    report_dir,
                    prefix=f"tamper-{mutation}-bundle",
                )
                bundle_dir = Path(str(bundle_publication["bundle_dir"]))
                self.assertEqual(
                    publish_portfolio_backtest_bundle_pointer(report_dir, bundle_dir)["status"],
                    "PUBLISHED",
                )
                pointer_path = report_dir / DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE
                if mutation == "pointer":
                    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
                    pointer["pack_hash"] = "f" * 64
                    pointer_path.write_text(json.dumps(pointer), encoding="utf-8")
                elif mutation == "pack":
                    (bundle_dir / "pack.json").write_bytes(b'{"forged":true}\n')
                else:
                    manifest_path = bundle_dir / "manifest.json"
                    manifest_path.write_bytes(manifest_path.read_bytes() + b" ")
                snapshot = load_portfolio_backtest_return_quality_snapshot(report_dir)

            self.assertFalse(snapshot["ok"])
            self.assertEqual(snapshot["status"], "UNKNOWN")
            self.assertIsNone(snapshot["return_quality"])
            self.assertIsNone(snapshot["forward_promotion"])

    def test_bundle_reader_does_not_apply_legacy_32m_limit_to_research_member(self) -> None:
        large_source = b"x" * (MAX_PUBLIC_PORTFOLIO_BACKTEST_PACK_BYTES + 1)
        members = {
            "pack.json": b"{}",
            "research.json": large_source,
            "statistical.json": b"{}",
        }
        with tempfile.TemporaryDirectory() as temporary:
            publication = publish_immutable_artifact_bundle(
                temporary,
                members,
                member_roles={
                    "pack.json": "INTERNAL_BACKTEST_PACK",
                    "research.json": "RESEARCH_REPORT",
                    "statistical.json": "STATISTICAL_AUDIT",
                },
                bindings={"synthetic": True},
                bundle_name_prefix="large-source-bundle",
                max_member_count=3,
                max_member_bytes=MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_MEMBER_BYTES,
                max_total_bytes=MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_TOTAL_BYTES,
            )
            loaded = portfolio_backtest_pack_pointer._read_public_backtest_bundle(
                Path(str(publication["bundle_dir"]))
            )

        self.assertEqual(publication["status"], "PUBLISHED")
        self.assertEqual(loaded["status"], "PASS")
        self.assertEqual(len(loaded["members"]["research.json"]), len(large_source))

    def test_bundle_pack_limit_blocks_before_pack_parse_or_core_verifier(self) -> None:
        members = {
            "pack.json": b"x" * 65,
            "research.json": b"{}",
            "statistical.json": b"{}",
        }
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            bundle = publish_immutable_artifact_bundle(
                report_dir,
                members,
                member_roles={
                    "pack.json": "INTERNAL_BACKTEST_PACK",
                    "research.json": "RESEARCH_REPORT",
                    "statistical.json": "STATISTICAL_AUDIT",
                },
                bindings={"synthetic": True},
                bundle_name_prefix="oversized-pack-bundle",
                max_member_count=3,
                max_member_bytes=MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_MEMBER_BYTES,
                max_total_bytes=MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_TOTAL_BYTES,
            )
            with patch.object(
                portfolio_backtest_pack_pointer,
                "MAX_PORTFOLIO_INTERNAL_BACKTEST_PACK_BYTES",
                64,
            ), patch.object(
                portfolio_backtest_pack_pointer,
                "verify_internal_backtest_bundle",
                side_effect=AssertionError("oversized pack reached core verifier"),
            ) as core_verifier:
                publication = publish_portfolio_backtest_bundle_pointer(
                    report_dir,
                    bundle["bundle_dir"],
                )

        self.assertEqual(publication["status"], "BLOCK")
        self.assertEqual(
            publication["blockers"],
            [
                "bundle_read:portfolio_backtest_bundle_member_size_limit_exceeded:INTERNAL_BACKTEST_PACK"
            ],
        )
        core_verifier.assert_not_called()

    def test_pack_publication_accepts_exact_byte_limit_and_blocks_next_byte_before_parse(self) -> None:
        pack = frozen_block_pack()
        with tempfile.TemporaryDirectory() as exact_temp:
            exact_dir = Path(exact_temp)
            exact_path = write_pack(exact_dir, pack, "exact_limit.json")
            exact_size = len(exact_path.read_bytes())
            with patch.object(
                portfolio_backtest_pack_pointer,
                "MAX_PUBLIC_PORTFOLIO_BACKTEST_PACK_BYTES",
                exact_size,
            ):
                exact = publish_portfolio_backtest_pack_pointer(exact_dir, exact_path)

        self.assertEqual(exact["status"], "PUBLISHED")

        with tempfile.TemporaryDirectory() as over_temp:
            over_dir = Path(over_temp)
            over_path = write_pack(over_dir, pack, "one_byte_over.json")
            over_size = len(over_path.read_bytes())
            with patch.object(
                portfolio_backtest_pack_pointer,
                "MAX_PUBLIC_PORTFOLIO_BACKTEST_PACK_BYTES",
                over_size - 1,
            ), patch.object(
                portfolio_backtest_pack_pointer,
                "_read_json_object",
                side_effect=AssertionError("oversized pack reached JSON parser"),
            ) as parser, patch.object(
                portfolio_backtest_pack_pointer,
                "verify_internal_backtest_pack",
                side_effect=AssertionError("oversized pack reached verifier"),
            ) as verifier:
                over = publish_portfolio_backtest_pack_pointer(over_dir, over_path)

        self.assertEqual(over["status"], "BLOCK")
        self.assertFalse(over["published"])
        self.assertEqual(
            over["blockers"],
            ["portfolio_backtest_pack_size_limit_exceeded"],
        )
        parser.assert_not_called()
        verifier.assert_not_called()

    def test_public_loader_blocks_oversized_pointer_before_parse_without_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            pointer_path = report_dir / DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE
            pointer_path.write_bytes(b"x" * 65)
            with patch.object(
                portfolio_backtest_pack_pointer,
                "MAX_PORTFOLIO_BACKTEST_PACK_POINTER_BYTES",
                64,
            ), patch.object(
                portfolio_backtest_pack_pointer,
                "_read_pointer_object_by_schema",
                side_effect=AssertionError("oversized pointer reached JSON parser"),
            ) as parser:
                result = load_portfolio_backtest_return_quality_snapshot(report_dir)

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(
            result["blockers"],
            ["portfolio_backtest_pack_pointer_size_limit_exceeded"],
        )
        self.assertIsNone(result["return_quality"])
        self.assertIsNone(result["forward_promotion"])
        self.assertNotIn(temp_dir, json.dumps(result, ensure_ascii=False))
        parser.assert_not_called()

    def test_public_loader_blocks_oversized_pack_before_pack_parse_or_verifier(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            pack_path = write_pack(report_dir, frozen_block_pack(), "oversized_after_publish.json")
            self.assertEqual(
                publish_portfolio_backtest_pack_pointer(report_dir, pack_path)["status"],
                "PUBLISHED",
            )
            pack_path.write_bytes(b"x" * 65)
            with patch.object(
                portfolio_backtest_pack_pointer,
                "MAX_PUBLIC_PORTFOLIO_BACKTEST_PACK_BYTES",
                64,
            ), patch.object(
                portfolio_backtest_pack_pointer,
                "_read_pointer_object_by_schema",
                wraps=portfolio_backtest_pack_pointer._read_pointer_object_by_schema,
            ) as parser, patch.object(
                portfolio_backtest_pack_pointer,
                "verify_internal_backtest_pack",
                side_effect=AssertionError("oversized pack reached verifier"),
            ) as verifier:
                result = load_portfolio_backtest_return_quality_snapshot(report_dir)

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(
            result["blockers"],
            ["portfolio_backtest_pack_size_limit_exceeded"],
        )
        self.assertIsNone(result["return_quality"])
        self.assertIsNone(result["forward_promotion"])
        self.assertNotIn(temp_dir, json.dumps(result, ensure_ascii=False))
        self.assertEqual(parser.call_count, 1)
        verifier.assert_not_called()

    def test_pointer_publication_and_loader_use_bounded_reader_for_every_artifact_read(self) -> None:
        pack = assemble_internal_backtest_pack(
            v4_evidence(),
            generated_at=100,
            schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            pack_path = write_pack(report_dir, pack, "bounded_reads.json")
            with patch.object(
                portfolio_backtest_pack_pointer,
                "_read_bounded_artifact",
                wraps=portfolio_backtest_pack_pointer._read_bounded_artifact,
            ) as publication_reader:
                publication = publish_portfolio_backtest_pack_pointer(report_dir, pack_path)

            self.assertEqual(publication["status"], "PUBLISHED")
            self.assertEqual(
                [call.args[0].name for call in publication_reader.call_args_list],
                [
                    "bounded_reads.json",
                    DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE,
                    "bounded_reads.json",
                ],
            )
            self.assertEqual(
                [call.kwargs["byte_limit"] for call in publication_reader.call_args_list],
                [
                    MAX_PUBLIC_PORTFOLIO_BACKTEST_PACK_BYTES,
                    MAX_PORTFOLIO_BACKTEST_PACK_POINTER_BYTES,
                    MAX_PUBLIC_PORTFOLIO_BACKTEST_PACK_BYTES,
                ],
            )

            with patch.object(
                portfolio_backtest_pack_pointer,
                "_read_bounded_artifact",
                wraps=portfolio_backtest_pack_pointer._read_bounded_artifact,
            ) as loader_reader:
                snapshot = load_portfolio_backtest_return_quality_snapshot(report_dir)

        self.assertFalse(snapshot["ok"])
        self.assertEqual(snapshot["status"], "UNKNOWN")
        self.assertEqual(
            [call.args[0].name for call in loader_reader.call_args_list],
            [DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE, "bounded_reads.json"],
        )
        self.assertEqual(
            [call.kwargs["byte_limit"] for call in loader_reader.call_args_list],
            [
                MAX_PORTFOLIO_BACKTEST_PACK_POINTER_BYTES,
                MAX_PUBLIC_PORTFOLIO_BACKTEST_PACK_BYTES,
            ],
        )

    def test_small_hash_bound_v4_extension_remains_semantically_compatible_and_private(self) -> None:
        pack = assemble_internal_backtest_pack(
            v4_evidence(),
            generated_at=100,
            schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
        )
        pack["uncontracted_padding"] = "bounded-small-extension"
        pack = reseal(pack)
        self.assertEqual(verify_internal_backtest_pack(pack)["status"], "PASS")

        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            pack_path = write_pack(report_dir, pack, "small_extension.json")
            publication = publish_portfolio_backtest_pack_pointer(report_dir, pack_path)
            snapshot = load_portfolio_backtest_return_quality_snapshot(report_dir)

        self.assertEqual(publication["status"], "PUBLISHED")
        self.assertFalse(snapshot["ok"])
        self.assertEqual(snapshot["status"], "UNKNOWN")
        self.assertNotIn("bounded-small-extension", json.dumps(snapshot, ensure_ascii=False))

    def test_verified_legacy_block_pack_pointer_publishes_but_public_quality_fails_closed(self) -> None:
        pack = frozen_block_pack()
        self.assertEqual(verify_internal_backtest_pack(pack)["status"], "PASS")
        self.assertEqual(pack["status"], "INTERNAL_BACKTEST_BLOCKED")
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            pack_path = write_pack(report_dir, pack)

            publication = publish_portfolio_backtest_pack_pointer(report_dir, pack_path)
            result = load_portfolio_backtest_return_quality_snapshot(report_dir)

        self.assertEqual(publication["status"], "PUBLISHED")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(
            result["schema_version"],
            PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_SCHEMA_VERSION,
        )
        self.assertEqual(result["source_verification_status"], "BLOCK")
        self.assertIn("pack_public_snapshot_schema_coupling_invalid", result["blockers"])
        self.assertIsNone(result["return_quality"])
        self.assertIsNone(result["forward_promotion"])
        self.assertFalse(result["profitability_proven"])
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("must-not-leak", serialized)
        self.assertNotIn(temp_dir, serialized)

    def test_legacy_v3_forward_pointers_publish_but_public_quality_fails_closed(self) -> None:
        scenarios = (
            (v3_forward_pack(outcomes=5, required=6), "COLLECTING", "NOT_DUE", "BLOCK"),
            (
                v3_forward_pack(outcomes=10, required=10),
                "RESEARCH_REVIEW_READY",
                "DUE",
                "REVIEW_REQUIRED",
            ),
            (
                v3_forward_pack(outcomes=10, required=10, weak_edge=True),
                "RESEARCH_REVIEW_BLOCKED",
                "DUE",
                "BLOCK",
            ),
        )
        for index, (pack, expected_status, expected_maturity, expected_promotion) in enumerate(
            scenarios
        ):
            with self.subTest(expected_status=expected_status), tempfile.TemporaryDirectory() as temp_dir:
                report_dir = Path(temp_dir)
                pack_path = write_pack(report_dir, pack, f"forward_{index}.json")
                self.assertEqual(
                    publish_portfolio_backtest_pack_pointer(report_dir, pack_path)["status"],
                    "PUBLISHED",
                )
                result = load_portfolio_backtest_return_quality_snapshot(report_dir)

            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "UNKNOWN")
            self.assertEqual(result["source_verification_status"], "BLOCK")
            self.assertIn("pack_public_snapshot_schema_coupling_invalid", result["blockers"])
            self.assertIsNone(result["return_quality"])
            self.assertIsNone(result["forward_promotion"])

    def test_legacy_v2_pointer_remains_publishable_without_public_numeric_quality(self) -> None:
        pack = assemble_internal_backtest_pack(
            {},
            generated_at=100,
            schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION,
        )
        pack["return_quality"] = deepcopy(frozen_block_pack()["return_quality"])
        pack = reseal(pack)
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            pack_path = write_pack(report_dir, pack)
            self.assertEqual(
                publish_portfolio_backtest_pack_pointer(report_dir, pack_path)["status"],
                "PUBLISHED",
            )
            result = load_portfolio_backtest_return_quality_snapshot(report_dir)

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["source_verification_status"], "BLOCK")
        self.assertIn("pack_public_snapshot_schema_coupling_invalid", result["blockers"])
        self.assertIsNone(result["return_quality"])
        self.assertIsNone(result["forward_promotion"])

    def test_legacy_v2_v3_resealed_coherent_return_claims_never_become_public(self) -> None:
        cases = (
            ("v2", frozen_block_pack()),
            ("v3", v3_forward_pack(outcomes=5, required=6)),
        )
        for index, (label, original) in enumerate(cases):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp_dir:
                pack = deepcopy(original)
                quality = pack["return_quality"]
                quality["status"] = "AVAILABLE"
                quality["summary"]["strategy_return_pct"] = 999.0
                quality["summary"]["benchmark_return_pct"] = 100.0
                quality["summary"]["benchmark_excess_return_pct"] = 899.0
                test_stage = quality["stages"]["test"]
                test_stage["strategy_return_pct"] = 999.0
                test_stage["benchmark_return_pct"] = 100.0
                test_stage["benchmark_excess_return_pct"] = 899.0
                test_stage["reported_benchmark_excess_return_pct"] = 899.0
                quality["failure_conditions"] = {
                    "source_integrity": [],
                    "observed": [],
                    "evidence_gaps": [],
                    "promotion_gaps": [],
                }
                pack = reseal(pack)
                self.assertEqual(verify_internal_backtest_pack(pack)["status"], "PASS")
                report_dir = Path(temp_dir)
                pack_path = write_pack(report_dir, pack, f"legacy_forged_{index}.json")

                publication = publish_portfolio_backtest_pack_pointer(report_dir, pack_path)
                result = load_portfolio_backtest_return_quality_snapshot(report_dir)

                self.assertEqual(publication["status"], "PUBLISHED")
                self.assertFalse(result["ok"])
                self.assertEqual(result["source_verification_status"], "BLOCK")
                self.assertIn("pack_public_snapshot_schema_coupling_invalid", result["blockers"])
                self.assertIsNone(result["return_quality"])
                self.assertNotIn("999.0", json.dumps(result, ensure_ascii=False))

    def test_legacy_v4_pointer_is_unknown_under_current_v4_snapshot(self) -> None:
        pack = assemble_internal_backtest_pack(
            v4_evidence(),
            generated_at=100,
            schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
        )
        self.assertEqual(verify_internal_backtest_pack(pack)["status"], "PASS")
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            pack_path = write_pack(report_dir, pack)
            self.assertEqual(
                publish_portfolio_backtest_pack_pointer(report_dir, pack_path)["status"],
                "PUBLISHED",
            )
            result = load_portfolio_backtest_return_quality_snapshot(report_dir)

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(
            result["schema_version"],
            PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_SCHEMA_VERSION,
        )
        self.assertIn("pack_public_snapshot_schema_coupling_invalid", result["blockers"])
        self.assertIsNone(result["return_quality"])
        self.assertIsNone(result["forward_promotion"])
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("return_quality_source_evidence", serialized)
        self.assertNotIn("source_identity", serialized)
        self.assertNotIn("source_evidence_hash", serialized)

    def test_pack_quality_version_mismatches_fail_closed_even_after_outer_verification(self) -> None:
        cases = []
        v2 = frozen_block_pack()
        v2["return_quality"]["schema_version"] = "backtest-return-quality-v2"
        cases.append(
            ("v2_with_quality_v2", reseal(v2), "pack_public_snapshot_schema_coupling_invalid")
        )
        v3 = v3_forward_pack(outcomes=5, required=6)
        v3["return_quality"]["schema_version"] = "backtest-return-quality-v2"
        cases.append(
            ("v3_with_quality_v2", reseal(v3), "pack_public_snapshot_schema_coupling_invalid")
        )
        v4 = assemble_internal_backtest_pack(
            v4_evidence(),
            generated_at=100,
            schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
        )
        v4["return_quality"]["schema_version"] = "backtest-return-quality-v1"
        cases.append(
            ("v4_with_quality_v1", reseal(v4), "pack_public_snapshot_schema_coupling_invalid")
        )

        for index, (label, pack, expected_blocker) in enumerate(cases):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp_dir:
                report_dir = Path(temp_dir)
                pack_path = write_pack(report_dir, pack, f"mismatch_{index}.json")
                with patch(
                    "exchange_terminal.services.portfolio_backtest_pack_pointer.verify_internal_backtest_pack",
                    return_value={
                        "status": "PASS",
                        "return_quality_source_integrity_status": "PASS",
                    },
                ):
                    self.assertEqual(
                        publish_portfolio_backtest_pack_pointer(report_dir, pack_path)["status"],
                        "PUBLISHED",
                    )
                    result = load_portfolio_backtest_return_quality_snapshot(report_dir)

            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "UNKNOWN")
            self.assertIn(expected_blocker, result["blockers"])

    def test_pointer_boundary_rejects_new_nested_authority_fields(self) -> None:
        pack = frozen_block_pack()
        pack["return_quality"]["nested_authority"] = {
            "can_trade": True,
            "direction_signal_allowed": True,
            "Paper_Authorized": True,
            "CAN_TRADE": True,
            "paperAuthorized": True,
            "parameter_selection_authority": True,
            "ParameterSelectionAuthority": True,
        }
        pack = reseal(pack)
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            pack_path = write_pack(report_dir, pack, "nested_authority.json")
            with patch(
                "exchange_terminal.services.portfolio_backtest_pack_pointer.verify_internal_backtest_pack",
                return_value={"status": "PASS"},
            ):
                publication = publish_portfolio_backtest_pack_pointer(report_dir, pack_path)

        self.assertEqual(publication["status"], "BLOCK")
        self.assertTrue(
            any("can_trade" in item for item in publication["blockers"]),
            publication,
        )
        for alias in (
            "Paper_Authorized",
            "CAN_TRADE",
            "paperAuthorized",
            "parameter_selection_authority",
            "ParameterSelectionAuthority",
        ):
            self.assertTrue(any(alias in item for item in publication["blockers"]), publication)

    def test_malicious_pack_object_shape_blocks_publisher_and_public_loader_without_throwing(self) -> None:
        malicious = frozen_block_pack()
        malicious["candidate"] = "not-an-object"
        malicious = reseal(malicious)
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            pack_path = write_pack(report_dir, malicious, "malicious_shape.json")

            publication = publish_portfolio_backtest_pack_pointer(report_dir, pack_path)
            self.assertEqual(publication["status"], "BLOCK")

            raw = pack_path.read_bytes()
            pointer_content = {
                "schema_version": "portfolio-backtest-pack-pointer-v1",
                "status": "CURRENT_FROZEN_INTERNAL_BACKTEST_PACK",
                "pack_file": pack_path.name,
                "pack_file_sha256": hashlib.sha256(raw).hexdigest(),
                "pack_schema_version": str(malicious.get("schema_version") or ""),
                "candidate_hash": "",
                "pack_hash": str(malicious.get("pack_hash") or ""),
                "evidence_hash": str(malicious.get("evidence_hash") or ""),
                "pack_status": str(malicious.get("status") or "UNKNOWN"),
                "promotion_status": str(malicious.get("promotion_status") or "UNKNOWN"),
                "generated_at": malicious.get("generated_at"),
                "research_only": True,
                "profitability_proven": False,
                "performance_claim_allowed": False,
                "parameter_selection_allowed": False,
                "automatic_paper_activation_allowed": False,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
            pointer = {**pointer_content, "pointer_hash": canonical_hash(pointer_content)}
            (report_dir / DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE).write_text(
                json.dumps(pointer),
                encoding="utf-8",
            )

            snapshot = load_portfolio_backtest_return_quality_snapshot(report_dir)

        self.assertFalse(snapshot["ok"])
        self.assertEqual(snapshot["status"], "UNKNOWN")
        self.assertTrue(snapshot["blockers"])

    def test_unexpected_pack_verifier_error_is_block_or_unknown_at_pointer_boundaries(self) -> None:
        pack = frozen_block_pack()
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            pack_path = write_pack(report_dir, pack, "verifier_exception.json")
            with patch(
                "exchange_terminal.services.portfolio_backtest_pack_pointer.verify_internal_backtest_pack",
                side_effect=RuntimeError("synthetic"),
            ):
                publication = publish_portfolio_backtest_pack_pointer(report_dir, pack_path)
            self.assertEqual(publication["status"], "BLOCK")
            self.assertIn("pointer_pack_verification_exception", publication["blockers"])

            self.assertEqual(
                publish_portfolio_backtest_pack_pointer(report_dir, pack_path)["status"],
                "PUBLISHED",
            )
            with patch(
                "exchange_terminal.services.portfolio_backtest_pack_pointer.verify_internal_backtest_pack",
                side_effect=RuntimeError("synthetic"),
            ):
                snapshot = load_portfolio_backtest_return_quality_snapshot(report_dir)

        self.assertFalse(snapshot["ok"])
        self.assertEqual(snapshot["status"], "UNKNOWN")
        self.assertIn("pointer_pack_verification_exception", snapshot["blockers"])

    def test_v4_structurally_valid_source_block_never_becomes_public_quality(self) -> None:
        evidence = v4_evidence()
        evidence["research"]["test"]["equity_curve"][-1]["equity"] = 200_000.0
        evidence["research"]["test"]["total_return_pct"] = 100.0
        pack = assemble_internal_backtest_pack(
            evidence,
            generated_at=100,
            schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
        )
        verification = verify_internal_backtest_pack(pack)
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["return_quality_source_integrity_status"], "BLOCK")

        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            pack_path = write_pack(report_dir, pack, "source_blocked_v4.json")
            publication = publish_portfolio_backtest_pack_pointer(report_dir, pack_path)
            snapshot = load_portfolio_backtest_return_quality_snapshot(report_dir)

        self.assertEqual(publication["status"], "BLOCK")
        self.assertIn("pointer_return_quality_source_integrity_blocked", publication["blockers"])
        self.assertFalse(snapshot["ok"])
        self.assertIsNone(snapshot["return_quality"])

    def test_legacy_v3_public_failure_does_not_expose_spec_rows_or_unknown_fields(self) -> None:
        pack = v3_forward_pack(outcomes=10, required=10)
        projection = pack["forward_promotion_evidence"]
        projection["private_note"] = "must-not-leak"
        projection["candidate"]["private_note"] = "must-not-leak"
        projection["performance_summary"]["internal_path"] = "must-not-leak"
        projection["forward_statistical_audit"]["internal_rows_note"] = "must-not-leak"
        projection_content = deepcopy(projection)
        projection_content.pop("projection_hash", None)
        projection["projection_hash"] = canonical_hash(projection_content)
        pack = reseal(pack)
        self.assertEqual(verify_internal_backtest_pack(pack)["status"], "PASS")

        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            pack_path = write_pack(report_dir, pack)
            self.assertEqual(
                publish_portfolio_backtest_pack_pointer(report_dir, pack_path)["status"],
                "PUBLISHED",
            )
            result = load_portfolio_backtest_return_quality_snapshot(report_dir)

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertFalse(result["ok"])
        self.assertEqual(result["source_verification_status"], "BLOCK")
        self.assertIn("pack_public_snapshot_schema_coupling_invalid", result["blockers"])
        self.assertIsNone(result["return_quality"])
        self.assertNotIn("must-not-leak", serialized)
        self.assertNotIn('"spec"', serialized)
        self.assertNotIn('"series_evidence"', serialized)
        self.assertNotIn('"performance_summary"', serialized)

    def test_legacy_v3_forward_ready_pack_still_fails_closed_publicly(self) -> None:
        pack = v3_forward_pack(outcomes=10, required=10)
        pack["checks"]["all_evidence"] = False
        pack["status"] = "INTERNAL_BACKTEST_BLOCKED"
        pack["promotion_status"] = "BLOCK"
        pack["promotion_blockers"] = ["internal_backtest_evidence_ready"]
        pack = reseal(pack)
        self.assertEqual(verify_internal_backtest_pack(pack)["status"], "PASS")

        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            pack_path = write_pack(report_dir, pack)
            self.assertEqual(
                publish_portfolio_backtest_pack_pointer(report_dir, pack_path)["status"],
                "PUBLISHED",
            )
            result = load_portfolio_backtest_return_quality_snapshot(report_dir)

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["source_verification_status"], "BLOCK")
        self.assertIn("pack_public_snapshot_schema_coupling_invalid", result["blockers"])
        self.assertIsNone(result["return_quality"])
        self.assertIsNone(result["forward_promotion"])

    def test_missing_pointer_returns_unknown_null_without_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = load_portfolio_backtest_return_quality_snapshot(Path(temp_dir))

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNone(result["return_quality"])
        self.assertIsNone(result["pack_hash"])
        self.assertIsNone(result["generated_at"])
        self.assertNotIn(temp_dir, json.dumps(result, ensure_ascii=False))

    def test_pointer_and_pack_binding_tampering_fail_closed(self) -> None:
        mutations = (
            ("pointer_hash", lambda pointer: pointer.__setitem__("candidate_hash", "x" * 64)),
            ("file_sha", lambda pointer: pointer.__setitem__("pack_file_sha256", "a" * 64)),
            ("pack_hash", lambda pointer: pointer.__setitem__("pack_hash", "b" * 64)),
            ("evidence_hash", lambda pointer: pointer.__setitem__("evidence_hash", "c" * 64)),
            ("schema", lambda pointer: pointer.__setitem__("pack_schema_version", "unknown-v99")),
        )
        for label, mutate in mutations:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp_dir:
                report_dir = Path(temp_dir)
                pack_path = write_pack(report_dir, frozen_block_pack())
                self.assertEqual(
                    publish_portfolio_backtest_pack_pointer(report_dir, pack_path)["status"],
                    "PUBLISHED",
                )
                pointer_path = report_dir / DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE
                pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
                mutate(pointer)
                if label != "pointer_hash":
                    content = dict(pointer)
                    content.pop("pointer_hash", None)
                    pointer["pointer_hash"] = canonical_hash(content)
                pointer_path.write_text(json.dumps(pointer), encoding="utf-8")

                result = load_portfolio_backtest_return_quality_snapshot(report_dir)

                self.assertEqual(result["status"], "UNKNOWN")
                self.assertIsNone(result["return_quality"])

    def test_pack_content_tampering_fails_file_and_pack_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            pack_path = write_pack(report_dir, frozen_block_pack())
            publish_portfolio_backtest_pack_pointer(report_dir, pack_path)
            tampered = json.loads(pack_path.read_text(encoding="utf-8"))
            tampered["return_quality"]["summary"]["strategy_return_pct"] = 999.0
            pack_path.write_text(json.dumps(tampered), encoding="utf-8")

            result = load_portfolio_backtest_return_quality_snapshot(report_dir)

        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNone(result["return_quality"])
        self.assertFalse(result["live_order_allowed"])

    def test_invalid_generated_at_is_blocked_even_when_pointer_and_pack_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            pack = frozen_block_pack()
            pack["generated_at"] = None
            pack = reseal(pack)
            pack_path = write_pack(report_dir, pack)

            publication = publish_portfolio_backtest_pack_pointer(report_dir, pack_path)

        self.assertEqual(publication["status"], "BLOCK")
        self.assertIn("pointer_generated_at_invalid", publication["blockers"])

    def test_external_output_skips_pointer_and_reserved_basename_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as report_temp, tempfile.TemporaryDirectory() as external_temp:
            report_dir = Path(report_temp)
            external_path = Path(external_temp) / "pack.json"
            reserved_path = report_dir / DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE

            external = pointer_publication_eligibility(report_dir, external_path)
            reserved = pointer_publication_eligibility(report_dir, reserved_path)

        self.assertEqual(external["status"], "SKIP")
        self.assertFalse(external["publish"])
        self.assertEqual(reserved["status"], "BLOCK")
        self.assertFalse(reserved["publish"])

    def test_no_clobber_helper_is_exact_byte_idempotent_and_preserves_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "pack.json"
            payload = ready_cli_pack()

            first = publish_json_artifact_no_clobber(output, payload)
            second = publish_json_artifact_no_clobber(output, payload)
            conflict = publish_json_artifact_no_clobber(output, {**payload, "pack_hash": "c" * 64})

            self.assertEqual(first["status"], "PUBLISHED")
            self.assertEqual(second["status"], "EXISTING_IDENTICAL")
            self.assertEqual(conflict["status"], "BLOCK")
            self.assertEqual(output.read_bytes(), json_artifact_bytes(payload))

    @staticmethod
    def _runner_ready_bundle() -> tuple[dict[str, object], list[dict[str, object]]]:
        _legacy, artifacts = v5_bundle()
        pack = assemble_internal_backtest_pack(v4_evidence(), generated_at=100)
        ready = deepcopy(pack)
        ready["status"] = "INTERNAL_BACKTEST_EVIDENCE_READY"
        ready["blockers"] = []
        return reseal(ready), artifacts

    @staticmethod
    def _runner_pass_verification() -> dict[str, object]:
        return {
            "status": "PASS",
            "artifact_contract_status": "PASS",
            "return_quality_source_integrity_status": "PASS",
            "numeric_claims_available": True,
            "return_quality": {
                "source_integrity_status": "PASS",
                "numeric_claims_available": True,
            },
            "blockers": [],
        }

    @staticmethod
    def _runner_pointer_receipt(
        pack: dict[str, object],
        bundle_dir: Path | str,
        expected: dict[str, object],
        *,
        published: bool = True,
        pointer_hash: str | None = None,
    ) -> dict[str, object]:
        bindings = portfolio_backtest_bundle_pointer_receipt_bindings(
            bundle_dir_name=Path(bundle_dir).name,
            manifest_file_sha256=str(expected["expected_manifest_file_sha256"]),
            bundle_hash=str(expected["expected_bundle_hash"]),
            pack_file="pack.json",
            pack_file_sha256=str(expected["expected_pack_file_sha256"]),
            pack=pack,
        )
        if pointer_hash is not None:
            bindings["pointer_hash"] = pointer_hash
        return {
            "status": "PUBLISHED",
            "published": published,
            "blockers": [],
            **bindings,
        }

    def test_writer_default_publishes_v6_bundle_then_fully_bound_pointer(self) -> None:
        pack, artifacts = self._runner_ready_bundle()
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            argv = ["run_internal_backtest.py", "--report-dir", str(report_dir)]

            def pointer_receipt(
                _report_dir: Path,
                bundle_dir: Path | str,
                **expected: object,
            ) -> dict[str, object]:
                return self._runner_pointer_receipt(pack, bundle_dir, expected)

            with patch("sys.argv", argv), patch(
                "run_internal_backtest.build_internal_backtest_bundle",
                return_value={"pack": pack, "detached_artifacts": artifacts},
            ) as build_bundle, patch(
                "run_internal_backtest.verify_internal_backtest_bundle",
                return_value=self._runner_pass_verification(),
            ) as verify_bundle, patch(
                "run_internal_backtest.publish_portfolio_backtest_bundle_pointer",
                side_effect=pointer_receipt,
            ) as publish_pointer, patch(
                "run_internal_backtest.verify_persisted_portfolio_backtest_bundle_pointer",
                side_effect=lambda _report_dir, *, expected_bindings: {
                    "status": "PASS",
                    "blockers": [],
                    **expected_bindings,
                },
            ) as verify_persisted_pointer, patch(
                "run_internal_backtest.build_internal_backtest_pack"
            ) as legacy_builder, patch("sys.stdout", new_callable=io.StringIO) as stdout:
                code = run_internal_backtest.main()

            result = json.loads(stdout.getvalue())
            bundle_dir = Path(result["bundle_publication"]["bundle_dir"])
            expected_files = {
                "pack.json",
                DEFAULT_BUNDLE_MANIFEST_FILE,
                *(str(item["file"]) for item in artifacts),
            }
            self.assertEqual(code, 0)
            self.assertEqual(result["status"], "INTERNAL_BACKTEST_EVIDENCE_READY")
            self.assertEqual(result["mode"], "CURRENT_REPORT_ROOT_V6_BUNDLE")
            self.assertEqual(result["pack_schema_version"], CURRENT_PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION)
            self.assertEqual(result["bundle_publication"]["status"], "PUBLISHED")
            self.assertEqual(result["pointer_publication"]["status"], "PUBLISHED")
            self.assertTrue(bundle_dir.is_dir())
            self.assertEqual({item.name for item in bundle_dir.iterdir()}, expected_files)
            build_bundle.assert_called_once()
            verify_bundle.assert_called_once_with(pack, artifacts)
            publish_pointer.assert_called_once()
            verify_persisted_pointer.assert_called_once()
            legacy_builder.assert_not_called()
            self.assertFalse(result["profitability_proven"])
            self.assertFalse(result["parameter_selection_allowed"])
            self.assertFalse(result["paper_authorized"])
            self.assertFalse(result["live_order_allowed"])

    def test_writer_retains_source_blocked_contract_valid_bundle_without_pointer(self) -> None:
        _legacy, artifacts = v5_bundle()
        pack = assemble_internal_backtest_pack(v4_evidence(), generated_at=100)
        source_blocked = {
            "status": "BLOCK",
            "artifact_contract_status": "PASS",
            "return_quality_source_integrity_status": "BLOCK",
            "numeric_claims_available": False,
            "return_quality": {},
            "blockers": ["synthetic_source_integrity_block"],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            with patch(
                "sys.argv",
                ["run_internal_backtest.py", "--report-dir", str(report_dir)],
            ), patch(
                "run_internal_backtest.build_internal_backtest_bundle",
                return_value={"pack": pack, "detached_artifacts": artifacts},
            ), patch(
                "run_internal_backtest.verify_internal_backtest_bundle",
                return_value=source_blocked,
            ), patch(
                "run_internal_backtest.publish_portfolio_backtest_bundle_pointer"
            ) as publish_pointer, patch("sys.stdout", new_callable=io.StringIO) as stdout:
                code = run_internal_backtest.main()

            result = json.loads(stdout.getvalue())
            bundle_dir = Path(result["bundle_publication"]["bundle_dir"])
            self.assertEqual(code, 2)
            self.assertEqual(result["bundle_publication"]["status"], "PUBLISHED")
            self.assertTrue(bundle_dir.is_dir())
            self.assertEqual(result["source_integrity_status"], "BLOCK")
            self.assertFalse(result["numeric_claims_available"])
            self.assertEqual(result["pointer_publication"]["status"], "SKIPPED")
            self.assertIn(
                "bundle_semantic_verification_blocked",
                result["pointer_publication"]["blockers"],
            )
            publish_pointer.assert_not_called()
            self.assertFalse(
                (report_dir / DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE).exists()
            )

    def test_writer_artifact_contract_block_never_publishes_bundle_or_pointer(self) -> None:
        pack, artifacts = v5_bundle()
        contract_blocked = {
            "status": "BLOCK",
            "artifact_contract_status": "BLOCK",
            "return_quality_source_integrity_status": "PASS",
            "numeric_claims_available": True,
            "return_quality": {
                "source_integrity_status": "PASS",
                "numeric_claims_available": True,
            },
            "blockers": ["synthetic_artifact_contract_block"],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            with patch(
                "sys.argv",
                ["run_internal_backtest.py", "--report-dir", str(report_dir)],
            ), patch(
                "run_internal_backtest.build_internal_backtest_bundle",
                return_value={"pack": pack, "detached_artifacts": artifacts},
            ), patch(
                "run_internal_backtest.verify_internal_backtest_bundle",
                return_value=contract_blocked,
            ), patch(
                "run_internal_backtest.publish_immutable_artifact_bundle"
            ) as publish_bundle, patch(
                "run_internal_backtest.publish_portfolio_backtest_bundle_pointer"
            ) as publish_pointer, patch("sys.stdout", new_callable=io.StringIO) as stdout:
                code = run_internal_backtest.main()

            result = json.loads(stdout.getvalue())
            self.assertEqual(code, 2)
            self.assertEqual(result["bundle_publication"]["status"], "SKIPPED")
            self.assertFalse(result["numeric_claims_available"])
            publish_bundle.assert_not_called()
            publish_pointer.assert_not_called()

    def test_writer_bundle_conflict_keeps_diagnostics_and_skips_pointer(self) -> None:
        pack, artifacts = self._runner_ready_bundle()
        conflict = {
            "status": "BLOCK",
            "published": False,
            "blockers": ["backtest_bundle_publication_failed:target_conflict"],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            with patch(
                "sys.argv",
                ["run_internal_backtest.py", "--report-dir", str(report_dir)],
            ), patch(
                "run_internal_backtest.build_internal_backtest_bundle",
                return_value={"pack": pack, "detached_artifacts": artifacts},
            ), patch(
                "run_internal_backtest.verify_internal_backtest_bundle",
                return_value=self._runner_pass_verification(),
            ), patch(
                "run_internal_backtest.publish_immutable_artifact_bundle",
                return_value=conflict,
            ), patch(
                "run_internal_backtest.publish_portfolio_backtest_bundle_pointer"
            ) as publish_pointer, patch("sys.stdout", new_callable=io.StringIO) as stdout:
                code = run_internal_backtest.main()

            result = json.loads(stdout.getvalue())
            self.assertEqual(code, 2)
            self.assertEqual(result["bundle_publication"], conflict)
            self.assertEqual(result["pointer_publication"]["status"], "SKIPPED")
            self.assertIn(
                "bundle_publication_blocked",
                result["pointer_publication"]["blockers"],
            )
            publish_pointer.assert_not_called()

    def test_writer_rejects_false_or_forged_full_pointer_receipt(self) -> None:
        cases = (
            ("false_receipt", False, None),
            ("forged_hash", True, "f" * 64),
            ("ghost_exact", True, None),
        )
        for label, published, forged_hash in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp_dir:
                pack, artifacts = self._runner_ready_bundle()
                report_dir = Path(temp_dir)

                def pointer_receipt(
                    _report_dir: Path,
                    bundle_dir: Path | str,
                    **expected: object,
                ) -> dict[str, object]:
                    return self._runner_pointer_receipt(
                        pack,
                        bundle_dir,
                        expected,
                        published=published,
                        pointer_hash=forged_hash,
                    )

                with patch(
                    "sys.argv",
                    ["run_internal_backtest.py", "--report-dir", str(report_dir)],
                ), patch(
                    "run_internal_backtest.build_internal_backtest_bundle",
                    return_value={"pack": pack, "detached_artifacts": artifacts},
                ), patch(
                    "run_internal_backtest.verify_internal_backtest_bundle",
                    return_value=self._runner_pass_verification(),
                ), patch(
                    "run_internal_backtest.publish_portfolio_backtest_bundle_pointer",
                    side_effect=pointer_receipt,
                ), patch("sys.stdout", new_callable=io.StringIO) as stdout:
                    code = run_internal_backtest.main()

                result = json.loads(stdout.getvalue())
                self.assertEqual(code, 2)
                self.assertEqual(result["bundle_publication"]["status"], "PUBLISHED")
                self.assertEqual(result["pointer_publication"]["status"], "PUBLISHED")
                self.assertFalse(
                    (report_dir / DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE).exists()
                )

    def test_writer_external_v4_rejects_exact_ghost_receipt_without_file(self) -> None:
        legacy_pack = ready_cli_pack()
        legacy_pack["schema_version"] = PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION
        legacy_pack["generated_at"] = 100
        raw = json_artifact_bytes(legacy_pack)
        with tempfile.TemporaryDirectory() as report_temp, tempfile.TemporaryDirectory() as external_temp:
            report_dir = Path(report_temp)
            output = Path(external_temp) / "ghost.json"
            ghost_receipt = {
                "status": "PUBLISHED",
                "published": True,
                "blockers": [],
                "path": str(output),
                "file_sha256": hashlib.sha256(raw).hexdigest(),
                "byte_length": len(raw),
            }
            with patch(
                "sys.argv",
                [
                    "run_internal_backtest.py",
                    "--report-dir",
                    str(report_dir),
                    "--output",
                    str(output),
                ],
            ), patch(
                "run_internal_backtest.build_internal_backtest_pack",
                return_value=legacy_pack,
            ), patch(
                "run_internal_backtest.verify_internal_backtest_pack",
                return_value={"status": "PASS", "blockers": []},
            ), patch(
                "run_internal_backtest.publish_json_artifact_no_clobber",
                return_value=ghost_receipt,
            ), patch("sys.stdout", new_callable=io.StringIO) as stdout:
                code = run_internal_backtest.main()

            result = json.loads(stdout.getvalue())
            self.assertEqual(code, 2)
            self.assertFalse(output.exists())
            self.assertEqual(result["artifact_publication"], ghost_receipt)
            self.assertEqual(result["post_publication_verification"], "BLOCK")
            self.assertTrue(
                any(
                    item.startswith("offline_v4_post_publication_verification_exception:")
                    for item in result["post_publication_verification_blockers"]
                )
            )

    def test_writer_external_output_is_immutable_legacy_v4_and_never_current(self) -> None:
        legacy_pack = ready_cli_pack()
        legacy_pack["schema_version"] = PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION
        legacy_pack["generated_at"] = 100
        with tempfile.TemporaryDirectory() as report_temp, tempfile.TemporaryDirectory() as external_temp:
            report_dir = Path(report_temp)
            output = Path(external_temp) / "offline_pack.json"
            argv = [
                "run_internal_backtest.py",
                "--report-dir",
                str(report_dir),
                "--output",
                str(output),
            ]
            with patch("sys.argv", argv), patch(
                "run_internal_backtest.build_internal_backtest_pack",
                return_value=legacy_pack,
            ) as legacy_builder, patch(
                "run_internal_backtest.verify_internal_backtest_pack",
                return_value={"status": "PASS", "blockers": []},
            ), patch(
                "run_internal_backtest.build_internal_backtest_bundle"
            ) as current_builder, patch(
                "run_internal_backtest.publish_immutable_artifact_bundle"
            ) as publish_bundle, patch(
                "run_internal_backtest.publish_portfolio_backtest_bundle_pointer"
            ) as publish_pointer, patch("sys.stdout", new_callable=io.StringIO) as first_stdout:
                first_code = run_internal_backtest.main()
            with patch("sys.argv", argv), patch(
                "run_internal_backtest.build_internal_backtest_pack",
                return_value=legacy_pack,
            ), patch(
                "run_internal_backtest.verify_internal_backtest_pack",
                return_value={"status": "PASS", "blockers": []},
            ), patch(
                "run_internal_backtest.build_internal_backtest_bundle"
            ) as retry_current_builder, patch(
                "run_internal_backtest.publish_portfolio_backtest_bundle_pointer"
            ) as retry_pointer, patch("sys.stdout", new_callable=io.StringIO) as retry_stdout:
                retry_code = run_internal_backtest.main()

            first = json.loads(first_stdout.getvalue())
            retry = json.loads(retry_stdout.getvalue())
            self.assertEqual(first_code, 0)
            self.assertEqual(retry_code, 0)
            self.assertEqual(output.read_bytes(), json_artifact_bytes(legacy_pack))
            self.assertEqual(first["mode"], "OFFLINE_EXPORT_LEGACY_V4")
            self.assertEqual(first["output_scope"], "OFFLINE_EXPORT_LEGACY_V4")
            self.assertEqual(first["pack_schema_version"], PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION)
            self.assertEqual(first["artifact_publication"]["status"], "PUBLISHED")
            self.assertEqual(retry["artifact_publication"]["status"], "EXISTING_IDENTICAL")
            self.assertEqual(first["pointer_publication"]["status"], "NOT_APPLICABLE")
            for call in legacy_builder.call_args_list:
                self.assertEqual(
                    call.kwargs["schema_version"],
                    PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
                )
            current_builder.assert_not_called()
            retry_current_builder.assert_not_called()
            publish_bundle.assert_not_called()
            publish_pointer.assert_not_called()
            retry_pointer.assert_not_called()

    def test_writer_blocks_any_report_root_output_before_either_builder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            outputs = (
                report_dir,
                report_dir / "manual.json",
                report_dir / "nested" / "manual.json",
            )
            for output in outputs:
                with self.subTest(output=output), patch(
                    "sys.argv",
                    [
                        "run_internal_backtest.py",
                        "--report-dir",
                        str(report_dir),
                        "--output",
                        str(output),
                    ],
                ), patch(
                    "run_internal_backtest.build_internal_backtest_pack"
                ) as legacy_builder, patch(
                    "run_internal_backtest.build_internal_backtest_bundle"
                ) as current_builder, patch("sys.stdout", new_callable=io.StringIO) as stdout:
                    code = run_internal_backtest.main()

                result = json.loads(stdout.getvalue())
                self.assertEqual(code, 2)
                self.assertIn(
                    "explicit_report_root_output_forbidden",
                    result["planning_blockers"],
                )
                legacy_builder.assert_not_called()
                current_builder.assert_not_called()

    def test_writer_flattens_build_and_bundle_publication_exceptions(self) -> None:
        with tempfile.TemporaryDirectory() as first_temp:
            report_dir = Path(first_temp)
            with patch(
                "sys.argv",
                ["run_internal_backtest.py", "--report-dir", str(report_dir)],
            ), patch(
                "run_internal_backtest.build_internal_backtest_bundle",
                side_effect=OSError("sensitive path must not leak"),
            ), patch("sys.stdout", new_callable=io.StringIO) as stdout:
                code = run_internal_backtest.main()
            raw = stdout.getvalue()
            self.assertEqual(code, 2)
            self.assertNotIn("sensitive path must not leak", raw)
            self.assertIn("bundle_v6_build_exception:OSError", raw)

        pack, artifacts = self._runner_ready_bundle()
        with tempfile.TemporaryDirectory() as second_temp:
            report_dir = Path(second_temp)
            with patch(
                "sys.argv",
                ["run_internal_backtest.py", "--report-dir", str(report_dir)],
            ), patch(
                "run_internal_backtest.build_internal_backtest_bundle",
                return_value={"pack": pack, "detached_artifacts": artifacts},
            ), patch(
                "run_internal_backtest.verify_internal_backtest_bundle",
                return_value=self._runner_pass_verification(),
            ), patch(
                "run_internal_backtest.publish_immutable_artifact_bundle",
                side_effect=PermissionError("sensitive bundle path must not leak"),
            ), patch(
                "run_internal_backtest.publish_portfolio_backtest_bundle_pointer"
            ) as publish_pointer, patch("sys.stdout", new_callable=io.StringIO) as stdout:
                code = run_internal_backtest.main()
            raw = stdout.getvalue()
            self.assertEqual(code, 2)
            self.assertNotIn("sensitive bundle path must not leak", raw)
            self.assertIn("backtest_bundle_publication_exception:PermissionError", raw)
            publish_pointer.assert_not_called()
    def test_server_route_is_fixed_pointer_only_without_glob_or_rebuild(self) -> None:
        server_path = Path(__file__).resolve().parents[1] / "exchange_terminal" / "server.py"
        tree = ast.parse(server_path.read_text(encoding="utf-8"), filename=str(server_path))
        matching_branches = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
                continue
            constants = [
                item.value
                for item in ast.walk(node.test)
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            ]
            if "/api/portfolio/backtest-return-quality" in constants:
                matching_branches.append(node)
        self.assertEqual(len(matching_branches), 1)
        calls = {
            item.func.id
            for item in ast.walk(matching_branches[0])
            if isinstance(item, ast.Call) and isinstance(item.func, ast.Name)
        }
        self.assertIn("load_portfolio_backtest_return_quality_snapshot", calls)
        self.assertNotIn("build_internal_backtest_pack", calls)
        self.assertNotIn("glob", calls)


if __name__ == "__main__":
    unittest.main()
