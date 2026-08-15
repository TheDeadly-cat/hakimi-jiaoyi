from __future__ import annotations

import ast
from contextlib import ExitStack
from copy import deepcopy
import inspect
import json
import os
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import Mock, patch

from exchange_terminal.services.implementation_manifest import build_implementation_manifest
from exchange_terminal.services.strategy_hypothesis_preregistration import (
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3,
    build_strategy_hypothesis_preregistration,
)
from exchange_terminal.services.strategy_matrix_protocol import (
    STRATEGY_MATRIX_PROTOCOL_ARTIFACT_VERSION,
    StrategyMatrixRegistrationStore,
    audit_strategy_matrix_holdout_exposure,
    build_strategy_matrix_protocol,
    canonical_hash,
    verify_strategy_matrix_protocol,
)
from exchange_terminal.services.strategy_research_protocol_artifact import (
    DEFAULT_STRATEGY_RESEARCH_REPORT_POINTER_FILE,
    plan_strategy_research_protocol_artifact,
    publish_strategy_research_protocol_artifact_no_clobber,
    verify_bound_strategy_research_protocol_artifact,
    verify_existing_strategy_research_protocol_artifact,
)
import run_preregister_strategy_research as preregister
import run_internal_strategy_research as research_runner
from tests.portfolio_governance_fixtures import attested_clock


class StopAfterExposureAudit(Exception):
    pass


class StrategyResearchPreregistrationCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.runtime = self.root / "runtime"
        self.reports = self.runtime / "reports"
        self.reports.mkdir(parents=True)
        self.registry = self.runtime / "research.sqlite3"
        self.source = self.root / "runner.py"
        self.source.write_text("VALUE = 1\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def clock(value: int) -> dict[str, object]:
        return attested_clock(value)

    @staticmethod
    def hypothesis() -> dict[str, object]:
        return build_strategy_hypothesis_preregistration({
            "schema_version": STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2,
            "hypothesis_id": "new-causal-mechanism-v2",
            "research_generation": "NEW_GENERATION",
            "strategy_ids": ["dual_ma"],
            "mechanism_family": "causal moving average persistence confirmation",
            "hypothesis_statement": (
                "Completed-bar moving-average persistence should retain positive "
                "benchmark excess after configured and stressed costs."
            ),
            "novelty_statement": (
                "This causal mechanism does not reuse or retune either falsified "
                "pullback or squeeze entry family."
            ),
            "mechanism_specific_failure_conditions": [{
                "condition_id": "validation_excess_lost",
                "evidence_stage": "DEVELOPMENT_SELECTION",
                "metric": "median_validation_excess_return_pct",
                "operator": "LTE",
                "threshold": 0.0,
                "required_action": "BLOCK_RESEARCH",
            }],
        })

    @staticmethod
    def hypothesis_v3() -> dict[str, object]:
        payload = dict(StrategyResearchPreregistrationCliTests.hypothesis())
        payload.pop("hypothesis_hash")
        payload.update({
            "schema_version": (
                STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3
            ),
            "hypothesis_id": "new-causal-mechanism-v3",
            "search_family_id": "causal-moving-average-global-search",
        })
        payload["hypothesis_hash"] = canonical_hash(payload)
        return payload

    def batch_spec(self) -> dict[str, object]:
        return research_runner.build_research_batch_spec(
            selection_symbols=["AAPL"],
            holdout_symbols=["ON"],
            strategies=["dual_ma"],
            position_pct=20.0,
            take_profit_pct=8.0,
            stop_loss_pct=4.0,
            fee_rate=0.0005,
            slippage_bps=2.0,
            limit=780,
            max_test_candidates=1,
            research_generation="NEW_GENERATION",
            selection_test_policy="BLIND_ONCE",
            hypothesis_preregistration=self.hypothesis(),
        )

    def plan(self, output: Path | None = None) -> dict[str, object]:
        return plan_strategy_research_protocol_artifact(
            self.reports,
            registration_id="research-1",
            registry_path=self.registry,
            requested_output=output or self.reports / "protocol.json",
        )

    def test_default_preregistration_batch_is_schema13_with_hypothesis_v2(self) -> None:
        batch_spec = self.batch_spec()

        self.assertEqual(batch_spec["report_schema_version"], 13)
        self.assertEqual(
            batch_spec["hypothesis_preregistration"]["schema_version"],
            STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2,
        )

    def test_cli_defaults_to_schema14_and_registers_canonical_lineage(self) -> None:
        canonical_registry = (
            self.runtime / "strategy_research_registrations.sqlite3"
        )
        output = self.reports / "schema14-protocol.json"
        exposure = self.exposure()
        exposure["symbols"] = ["ON", "MCHP"]
        exposure_content = dict(exposure)
        exposure_content.pop("audit_hash")
        exposure["audit_hash"] = canonical_hash(exposure_content)
        argv = [
            "run_preregister_strategy_research.py",
            "--strategies", "dual_ma",
            "--research-generation", "NEW_GENERATION",
            "--hypothesis-file", "docs/hypothesis-v3.json",
            "--registration-id", "schema14-cli",
            "--max-test-candidates", "1",
            "--output", str(output),
        ]
        with (
            patch.object(sys, "argv", argv),
            patch.object(preregister.server, "RUNTIME_DIR", self.runtime),
            patch.object(preregister.server, "RUNTIME_READ_ONLY", False),
            patch.object(
                preregister,
                "load_strategy_hypothesis_preregistration",
                return_value=self.hypothesis_v3(),
            ),
            patch.object(
                preregister,
                "audit_strategy_matrix_holdout_exposure",
                return_value=exposure,
            ),
            patch.object(
                preregister,
                "attest_utc_clock",
                return_value=self.clock(1_000_000),
            ),
            patch("builtins.print"),
        ):
            self.assertEqual(preregister.main(), 0)

        store = StrategyMatrixRegistrationStore(
            db_path=canonical_registry,
            canonical_runtime_root=self.runtime,
        )
        registered = store.get("schema14-cli")
        self.assertEqual(registered["status"], "REGISTERED")
        spec = registered["protocol"]["batch_spec"]
        self.assertEqual(spec["report_schema_version"], 14)
        self.assertEqual(
            spec["hypothesis_preregistration"]["schema_version"],
            STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3,
        )
        self.assertEqual(spec["search_lineage"]["current_trial_count"], 3)
        self.assertEqual(spec["search_lineage"]["cumulative_trial_count"], 3)

    def test_schema14_noncanonical_registry_blocks_before_hypothesis_or_store(self) -> None:
        argv = [
            "run_preregister_strategy_research.py",
            "--strategies", "dual_ma",
            "--research-generation", "NEW_GENERATION",
            "--hypothesis-file", "docs/hypothesis-v3.json",
            "--registry", str(self.runtime / "alternate.sqlite3"),
            "--max-test-candidates", "1",
        ]
        with (
            patch.object(sys, "argv", argv),
            patch.object(preregister.server, "RUNTIME_DIR", self.runtime),
            patch.object(
                preregister,
                "load_strategy_hypothesis_preregistration",
            ) as load_hypothesis,
            patch.object(
                preregister,
                "StrategyMatrixRegistrationStore",
            ) as store,
            self.assertRaisesRegex(
                SystemExit,
                "research_registry_canonical_preflight_blocked",
            ),
        ):
            preregister.main()

        load_hypothesis.assert_not_called()
        store.assert_not_called()

    def protocol(self, output: Path | None = None) -> dict[str, object]:
        plan = self.plan(output)
        self.assertEqual(plan["status"], "PASS", plan["blockers"])
        exposure: dict[str, object] = {
            "schema_version": "strategy-matrix-exposure-audit-v1",
            "status": "PASS",
            "evaluated_before_data_load": True,
            "symbols": ["ON"],
            "exposed_symbols": [],
            "evidence": {},
            "blockers": [],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        exposure["audit_hash"] = canonical_hash(exposure)
        return build_strategy_matrix_protocol(
            registration_id="research-1",
            research_generation="NEW_GENERATION",
            batch_spec=self.batch_spec(),
            implementation_manifest=build_implementation_manifest([self.source]),
            exposure_audit=exposure,
            registration_clock_attestation=self.clock(1_000_000),
            expires_at_ms=4_000_000,
            registry_path=self.registry,
            protocol_artifact=dict(plan["artifact_binding"]),
        )

    def _run_main(
        self,
        output: Path,
        *,
        read_only: bool = False,
        publisher: object | None = None,
        store_factory: object | None = None,
        clock_ms: int = 1_000_000,
        include_registration_id: bool = True,
    ) -> int:
        batch_spec = self.batch_spec()
        manifest = build_implementation_manifest([self.source])
        argv = [
            "run_preregister_strategy_research.py",
            "--strategies", "dual_ma",
            "--research-generation", "NEW_GENERATION",
            "--hypothesis-file", "docs/hypothesis.json",
            "--registry", str(self.registry),
            "--output", str(output),
            "--report-schema-version", "13",
        ]
        if include_registration_id:
            argv.extend(["--registration-id", "research-1"])
        with ExitStack() as stack:
            stack.enter_context(patch.object(sys, "argv", argv))
            stack.enter_context(patch.object(preregister.server, "RUNTIME_DIR", self.runtime))
            stack.enter_context(patch.object(preregister.server, "RUNTIME_READ_ONLY", read_only))
            stack.enter_context(patch.object(
                preregister,
                "load_strategy_hypothesis_preregistration",
                return_value=self.hypothesis(),
            ))
            stack.enter_context(patch.object(preregister, "build_research_batch_spec", return_value=batch_spec))
            stack.enter_context(patch.object(
                preregister,
                "audit_strategy_matrix_holdout_exposure",
                return_value=self.exposure(),
            ))
            stack.enter_context(patch.object(
                preregister,
                "attest_utc_clock",
                return_value=self.clock(clock_ms),
            ))
            stack.enter_context(patch.object(preregister, "build_implementation_manifest", return_value=manifest))
            stack.enter_context(patch("builtins.print"))
            if publisher is not None:
                stack.enter_context(patch.object(
                    preregister,
                    "publish_strategy_research_protocol_artifact_no_clobber",
                    new=publisher,
                ))
            if store_factory is not None:
                stack.enter_context(
                    patch.object(preregister, "StrategyMatrixRegistrationStore", new=store_factory)
                )
            return preregister.main()

    @staticmethod
    def exposure() -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": "strategy-matrix-exposure-audit-v1",
            "status": "PASS",
            "evaluated_before_data_load": True,
            "symbols": ["ON"],
            "exposed_symbols": [],
            "evidence": {},
            "blockers": [],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        payload["audit_hash"] = canonical_hash(payload)
        return payload

    def test_plan_blocks_registry_sidecars_reserved_pointer_and_wrong_parent(self) -> None:
        cases = (
            self.registry,
            Path(f"{self.registry}-wal"),
            Path(f"{self.registry}-shm"),
            Path(f"{self.registry}-journal"),
            self.reports / DEFAULT_STRATEGY_RESEARCH_REPORT_POINTER_FILE,
            self.reports / "nested" / "protocol.json",
            self.reports / "protocol.txt",
        )
        for output in cases:
            with self.subTest(output=output):
                plan = plan_strategy_research_protocol_artifact(
                    self.reports,
                    registration_id="research-1",
                    registry_path=self.registry,
                    requested_output=output,
                )
                self.assertEqual(plan["status"], "BLOCK")
        registry_in_reports = self.reports / "registry.sqlite3"
        for output in (
            registry_in_reports,
            Path(f"{registry_in_reports}-wal"),
            Path(f"{registry_in_reports}-shm"),
            Path(f"{registry_in_reports}-journal"),
        ):
            with self.subTest(registry_collision=output):
                plan = plan_strategy_research_protocol_artifact(
                    self.reports,
                    registration_id="research-1",
                    registry_path=registry_in_reports,
                    requested_output=output,
                )
                self.assertIn(
                    "strategy_research_protocol_output_collides_with_registry",
                    plan["blockers"],
                )

    def test_no_clobber_race_keeps_competing_target_and_cleans_own_temp(self) -> None:
        output = self.reports / "protocol.json"
        protocol = self.protocol(output)
        competing = b'{"competing":true}'
        real_link = os.link

        def racing_link(source: Path | str, destination: Path | str) -> None:
            Path(destination).write_bytes(competing)
            real_link(source, destination)

        with patch(
            "exchange_terminal.services.strategy_research_protocol_artifact.os.link",
            side_effect=racing_link,
        ):
            result = publish_strategy_research_protocol_artifact_no_clobber(output, protocol)

        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(output.read_bytes(), competing)
        self.assertEqual(list(self.reports.glob(".protocol.json.*.tmp")), [])

    def test_read_only_blocks_before_publish_or_store(self) -> None:
        output = self.reports / "protocol.json"
        publisher = Mock()
        store = Mock()

        with self.assertRaisesRegex(SystemExit, "research_protocol_read_only_blocked"):
            self._run_main(
                output,
                read_only=True,
                publisher=publisher,
                store_factory=store,
            )

        publisher.assert_not_called()
        store.assert_not_called()
        self.assertFalse(output.exists())

    def test_register_rechecks_artifact_and_rejects_tampering_before_insert(self) -> None:
        output = self.reports / "protocol.json"
        protocol = self.protocol(output)
        self.assertEqual(
            publish_strategy_research_protocol_artifact_no_clobber(output, protocol)["status"],
            "PUBLISHED",
        )
        output.write_text('{"tampered":true}', encoding="utf-8")
        store = StrategyMatrixRegistrationStore(db_path=self.registry)

        result = store.register(protocol)

        self.assertEqual(result["status"], "BLOCK")
        self.assertFalse(store.get("research-1")["ok"])

    def test_claim_rechecks_artifact_after_registered_sidecar_replacement(self) -> None:
        output = self.reports / "protocol.json"
        protocol = self.protocol(output)
        self.assertEqual(
            publish_strategy_research_protocol_artifact_no_clobber(output, protocol)["status"],
            "PUBLISHED",
        )
        store = StrategyMatrixRegistrationStore(db_path=self.registry)
        self.assertEqual(store.register(protocol)["status"], "REGISTERED")
        output.write_text('{"tampered":true}', encoding="utf-8")

        result = store.claim(
            "research-1",
            clock_attestation=self.clock(2_000_000),
            exposure_audit=self.exposure(),
        )

        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(any("matrix_claim_artifact" in item for item in result["blockers"]))
        self.assertEqual(store.get("research-1")["status"], "REGISTERED")

    def test_cli_post_register_check_detects_race_and_future_claim_stays_blocked(self) -> None:
        output = self.reports / "protocol.json"
        real_store: StrategyMatrixRegistrationStore | None = None

        class RacingStore:
            def __init__(inner_self, **kwargs: object) -> None:
                nonlocal real_store
                real_store = StrategyMatrixRegistrationStore(**kwargs)

            def register(inner_self, protocol: dict[str, object]) -> dict[str, object]:
                assert real_store is not None
                result = real_store.register(protocol)
                output.write_text('{"tampered":true}', encoding="utf-8")
                return result

        with self.assertRaisesRegex(SystemExit, "post_registration_artifact_blocked"):
            self._run_main(output, store_factory=RacingStore)

        self.assertIsNotNone(real_store)
        assert real_store is not None
        result = real_store.claim(
            "research-1",
            clock_attestation=self.clock(2_000_000),
            exposure_audit=self.exposure(),
        )
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(real_store.get("research-1")["status"], "REGISTERED")

    def test_existing_sidecar_recovers_original_protocol_not_new_clock_protocol(self) -> None:
        output = self.reports / "protocol.json"
        original = self.protocol(output)
        self.assertEqual(
            publish_strategy_research_protocol_artifact_no_clobber(output, original)["status"],
            "PUBLISHED",
        )
        captured: list[dict[str, object]] = []

        class FakeStore:
            def __init__(self, **_kwargs: object) -> None:
                pass

            def register(self, protocol: dict[str, object]) -> dict[str, object]:
                captured.append(protocol)
                return {"ok": True, "status": "REGISTERED"}

        self.assertEqual(
            self._run_main(output, store_factory=FakeStore, clock_ms=2_000_000),
            0,
        )

        self.assertEqual(captured, [original])
        self.assertEqual(captured[0]["registered_at_ms"], 1_000_000)

    def test_registration_failure_retry_recovers_published_protocol(self) -> None:
        output = self.reports / "protocol.json"

        class FailingStore:
            def __init__(self, **_kwargs: object) -> None:
                pass

            def register(self, _protocol: dict[str, object]) -> dict[str, object]:
                return {"ok": False, "status": "BLOCK", "blockers": ["synthetic_db_failure"]}

        with self.assertRaisesRegex(SystemExit, "research_protocol_registration_blocked"):
            self._run_main(
                output,
                store_factory=FailingStore,
                include_registration_id=False,
            )
        published = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(
            audit_strategy_matrix_holdout_exposure(
                self.reports,
                self.runtime,
                ["ON"],
            )["status"],
            "PASS",
        )
        captured: list[dict[str, object]] = []

        class RecoveryStore:
            def __init__(self, **_kwargs: object) -> None:
                pass

            def register(self, protocol: dict[str, object]) -> dict[str, object]:
                captured.append(protocol)
                return {"ok": True, "status": "REGISTERED"}

        self.assertEqual(
            self._run_main(
                output,
                store_factory=RecoveryStore,
                clock_ms=2_000_000,
                include_registration_id=False,
            ),
            0,
        )
        self.assertEqual(captured, [published])
        self.assertEqual(captured[0]["registered_at_ms"], 1_000_000)
        self.assertTrue(str(captured[0]["registration_id"]).startswith("sresearch-"))

    def test_recovery_rejects_resealed_generation_or_hypothesis_mismatch(self) -> None:
        output = self.reports / "protocol.json"
        protocol = self.protocol(output)
        tampered = deepcopy(protocol)
        tampered["research_generation"] = "OTHER_GENERATION"
        tampered["protocol_hash"] = canonical_hash({
            key: value for key, value in tampered.items() if key != "protocol_hash"
        })
        output.write_text(json.dumps(tampered), encoding="utf-8")
        store = Mock()

        with self.assertRaisesRegex(SystemExit, "research_protocol_recovery_blocked"):
            self._run_main(output, store_factory=store)

        store.assert_not_called()

    def test_recovery_rejects_expired_existing_protocol(self) -> None:
        output = self.reports / "protocol.json"
        protocol = self.protocol(output)
        self.assertEqual(
            publish_strategy_research_protocol_artifact_no_clobber(output, protocol)["status"],
            "PUBLISHED",
        )
        store = Mock()

        with self.assertRaisesRegex(SystemExit, "research_protocol_recovery_blocked"):
            self._run_main(
                output,
                store_factory=store,
                clock_ms=5_000_000,
            )

        store.assert_not_called()

    def test_protocol_binding_enters_hash_and_bound_artifact_matches(self) -> None:
        output = self.reports / "protocol.json"
        protocol = self.protocol(output)
        self.assertEqual(protocol["schema_version"], STRATEGY_MATRIX_PROTOCOL_ARTIFACT_VERSION)
        self.assertIn("protocol_artifact", protocol)
        content = dict(protocol)
        embedded_hash = content.pop("protocol_hash")
        self.assertEqual(embedded_hash, canonical_hash(content))
        self.assertEqual(
            publish_strategy_research_protocol_artifact_no_clobber(output, protocol)["status"],
            "PUBLISHED",
        )
        self.assertEqual(verify_bound_strategy_research_protocol_artifact(protocol)["status"], "PASS")

    def test_v3_resealed_alignment_policy_cannot_weaken_v2_contract(self) -> None:
        protocol = self.protocol(self.reports / "protocol.json")
        forged = deepcopy(protocol)
        forged["batch_spec"]["data_policy"]["alignment_schema_version"] = (
            "daily-batch-alignment-v0"
        )
        forged["batch_spec"]["data_policy"]["max_boundary_skew_days"] = 999_999
        forged["batch_spec_hash"] = canonical_hash(forged["batch_spec"])
        forged.pop("protocol_hash", None)
        forged["protocol_hash"] = canonical_hash(forged)

        verification = verify_strategy_matrix_protocol(
            forged,
            verify_current_implementation=False,
        )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("matrix_protocol_alignment_policy_invalid", verification["blockers"])

    def test_static_order_has_no_legacy_writer_and_rechecks_after_register(self) -> None:
        source = textwrap.dedent(inspect.getsource(preregister.main))
        self.assertNotIn("write_json_atomic", source)
        tree = ast.parse(source)
        calls: list[tuple[str, int]] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = node.func.id if isinstance(node.func, ast.Name) else (
                node.func.attr if isinstance(node.func, ast.Attribute) else ""
            )
            calls.append((name, node.lineno))
        publish_line = min(line for name, line in calls if name == "publish_strategy_research_protocol_artifact_no_clobber")
        register_line = min(line for name, line in calls if name == "register")
        post_check_line = max(line for name, line in calls if name == "verify_bound_strategy_research_protocol_artifact")
        self.assertLess(publish_line, register_line)
        self.assertLess(register_line, post_check_line)


if __name__ == "__main__":
    unittest.main()
