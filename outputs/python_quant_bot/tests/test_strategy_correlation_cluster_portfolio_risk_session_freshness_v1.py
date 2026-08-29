from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from unittest import TestCase
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_session_freshness_v1 as contract,
)
from exchange_terminal.services.strict_canonical_json_hash import strict_canonical_hash
from exchange_terminal.services.trusted_clock import (
    TRUSTED_CLOCK_LEGACY_SCHEMA_VERSION,
    build_trusted_clock_attestation,
)
from tests import (
    test_strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1
    as native_cutoff_tests,
)


_DEFAULT = object()


class StrategyCorrelationClusterPortfolioRiskSessionFreshnessV1Tests(TestCase):
    def setUp(self):
        self.native_case = (
            native_cutoff_tests.StrategyCorrelationClusterPortfolioRiskNativeCutoffManifestV1Tests(
                methodName="test_valid_manifest_binds_native_cutoff_to_verified_sessions"
            )
        )
        self.native_case.setUp()
        self.addCleanup(self.native_case.doCleanups)
        self.native_manifest = self.native_case._build()
        self.registration_inputs = {
            "native_cutoff_manifest": self.native_manifest,
            "native_cutoff_context": self.native_case.base_inputs,
            "expected_native_cutoff_manifest_hash": self.native_manifest[
                "manifest_hash"
            ],
            "max_completed_session_lag": 1,
            "declared_at_utc": "2026-09-18T00:00:00Z",
        }
        self.registration = self._register()

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

    def _clock(
        self,
        reference_utc: str = "2026-12-20T00:00:00Z",
        *,
        source_count: int = 2,
        minimum_sources: int | None = None,
    ) -> dict[str, object]:
        reference = datetime.fromisoformat(reference_utc.replace("Z", "+00:00"))
        reference_ms = int(reference.timestamp() * 1000)
        sources = [
            self._clock_source(f"CLOCK-{index + 1}", reference_ms)
            for index in range(source_count)
        ]
        return build_trusted_clock_attestation(
            local_now_ms=reference_ms,
            provider_evidence=sources,
            minimum_sources=(
                source_count if minimum_sources is None else minimum_sources
            ),
        )

    def _register(self, **overrides):
        values = dict(self.registration_inputs)
        values.update(overrides)
        with self.native_case.fixture.source_verifiers():
            return contract.build_strategy_correlation_cluster_portfolio_risk_session_freshness_policy_registration_v1(
                **values
            )

    def _evaluate(
        self,
        *,
        registration=_DEFAULT,
        registration_inputs=_DEFAULT,
        clock=_DEFAULT,
        expected_clock_hash=_DEFAULT,
    ):
        registration = self.registration if registration is _DEFAULT else registration
        registration_inputs = (
            self.registration_inputs
            if registration_inputs is _DEFAULT
            else registration_inputs
        )
        clock = self._clock() if clock is _DEFAULT else clock
        expected_clock_hash = (
            clock.get("attestation_hash")
            if expected_clock_hash is _DEFAULT and isinstance(clock, dict)
            else expected_clock_hash
        )
        with self.native_case.fixture.source_verifiers():
            return contract.evaluate_strategy_correlation_cluster_portfolio_risk_session_freshness_v1(
                registration,
                registration_inputs=registration_inputs,
                trusted_clock_attestation=clock,
                expected_trusted_clock_attestation_hash=expected_clock_hash,
            )

    def _verify_evaluation(self, document, **overrides):
        registration = overrides.pop("registration", self.registration)
        registration_inputs = overrides.pop(
            "registration_inputs", self.registration_inputs
        )
        clock = overrides.pop("clock", self._clock())
        expected_clock_hash = overrides.pop(
            "expected_clock_hash", clock["attestation_hash"]
        )
        self.assertFalse(overrides)
        with self.native_case.fixture.source_verifiers():
            return contract.verify_strategy_correlation_cluster_portfolio_risk_session_freshness_evaluation_v1(
                document,
                registration,
                registration_inputs=registration_inputs,
                trusted_clock_attestation=clock,
                expected_trusted_clock_attestation_hash=expected_clock_hash,
            )

    def test_existing_native_cutoff_explicitly_does_not_consume_reference_time(self):
        self.assertEqual(self.native_manifest["status"], "PASS")
        self.assertFalse(self.native_manifest["facts"]["freshness_policy_defined"])
        self.assertFalse(self.native_manifest["facts"]["freshness_evaluated"])

    def test_policy_registration_inherits_exact_native_calendar_projection(self):
        self.assertEqual(self.registration["status"], "REGISTERED")
        self.assertEqual(
            self.registration["source"]["native_cutoff_manifest_hash"],
            self.native_manifest["manifest_hash"],
        )
        self.assertEqual(
            self.registration["source"]["calendar_registration_hash"],
            self.native_case.context["calendar_verification_bundle"][
                "expected_calendar_registration_hash"
            ],
        )
        self.assertEqual(
            self.registration["source"]["calendar_session_verification_hash"],
            self.native_manifest["source"]["calendar_session_verification_hash"],
        )
        self.assertEqual(
            self.registration["registration_state"],
            "COMPLETED_SESSION_LAG_POLICY_REGISTERED_NOT_EVALUATED",
        )

    def test_registration_rejects_retrospective_or_non_native_thresholds(self):
        for overrides in (
            {"max_completed_session_lag": True},
            {"max_completed_session_lag": 4},
            {"max_completed_session_lag": -1},
            {"declared_at_utc": "2026-12-19T00:00:00Z"},
            {"declared_at_utc": "2026-09-18"},
        ):
            with self.subTest(overrides=overrides):
                self.assertEqual(self._register(**overrides)["status"], "BLOCK")

    def test_registration_rejects_native_manifest_or_context_drift(self):
        manifest = deepcopy(self.native_manifest)
        manifest["cutoff"]["session_label_date"] = "2026-12-18"
        context = deepcopy(self.native_case.base_inputs)
        context["composition_context"]["calendar_verification_bundle"][
            "expected_calendar_registration_hash"
        ] = "f" * 64
        for overrides in (
            {"native_cutoff_manifest": manifest},
            {"native_cutoff_context": context},
            {"expected_native_cutoff_manifest_hash": "f" * 64},
        ):
            with self.subTest(overrides=tuple(overrides)):
                self.assertEqual(self._register(**overrides)["status"], "BLOCK")

    def test_cutoff_session_at_exact_close_has_zero_lag(self):
        clock = self._clock("2026-12-20T00:00:00Z")
        document = self._evaluate(clock=clock)
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(document["lag"]["max_completed_session_lag"], 0)
        self.assertTrue(document["facts"]["freshness_policy_evaluated"])
        self.assertFalse(document["facts"]["freshness_externally_proven"])

    def test_one_completed_session_lag_is_the_registered_boundary(self):
        clock = self._clock("2026-12-21T00:00:00Z")
        document = self._evaluate(clock=clock)
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(document["lag"]["max_completed_session_lag"], 1)
        self.assertTrue(document["facts"]["session_lag_within_policy"])

    def test_two_completed_sessions_lag_is_stale_and_blocked(self):
        clock = self._clock("2026-12-22T00:00:00Z")
        document = self._evaluate(clock=clock)
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(
            document["decision"],
            "SESSION_LAG_EXCEEDS_PREREGISTERED_POLICY",
        )
        self.assertEqual(document["lag"]["max_completed_session_lag"], 2)
        self.assertTrue(document["facts"]["freshness_policy_evaluated"])
        self.assertFalse(document["facts"]["session_lag_within_policy"])

    def test_reference_before_cutoff_close_is_blocked(self):
        document = self._evaluate(clock=self._clock("2026-12-19T23:59:59Z"))
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn(
            "native_cutoff_not_completed_at_reference_time",
            document["blockers"],
        )

    def test_reference_horizon_is_bounded_before_calendar_lookup(self):
        document = self._evaluate(clock=self._clock("2027-01-31T00:00:00Z"))
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn(
            "reference_horizon_exceeds_policy_limit",
            document["blockers"],
        )
        self.assertFalse(document["facts"]["freshness_policy_evaluated"])

    def test_single_source_clock_is_not_a_quorum(self):
        clock = self._clock(source_count=1, minimum_sources=1)
        document = self._evaluate(clock=clock)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("trusted_clock_quorum_exact", document["blockers"])

    def test_legacy_or_tampered_clock_is_rejected(self):
        tampered = self._clock()
        tampered["attested_now_ms"] += 1
        legacy = self._clock()
        legacy["schema_version"] = TRUSTED_CLOCK_LEGACY_SCHEMA_VERSION
        legacy.pop("attestation_hash")
        legacy["attestation_hash"] = strict_canonical_hash(legacy)
        for clock in (tampered, legacy):
            with self.subTest(schema=clock["schema_version"]):
                document = self._evaluate(clock=clock)
                self.assertEqual(document["status"], "BLOCK")
                self.assertIn("trusted_clock_quorum_exact", document["blockers"])

    def test_calendar_runtime_lookup_failure_is_fail_closed(self):
        class BrokenCalendarRuntime:
            __version__ = contract.calendar_registration_contract.CALENDAR_LIBRARY_VERSION

            @staticmethod
            def get_calendar(_calendar_id):
                raise RuntimeError("synthetic lookup failure")

        with patch.object(
            contract.calendar_registration_contract,
            "exchange_calendars",
            BrokenCalendarRuntime(),
        ):
            document = self._evaluate()
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("calendar_session_lookup_failed", document["blockers"])

    def test_evaluation_requires_exact_registration_inputs(self):
        extra = dict(self.registration_inputs)
        extra["unexpected"] = True
        missing = dict(self.registration_inputs)
        missing.pop("declared_at_utc")
        for inputs in (extra, missing, None):
            with self.subTest(input_type=type(inputs).__name__):
                document = self._evaluate(registration_inputs=inputs)
                self.assertEqual(document["status"], "BLOCK")
                self.assertIn("freshness_registration_exact", document["blockers"])

    def test_evaluation_output_is_redacted_and_authority_locked(self):
        document = self._evaluate()
        encoded = json.dumps(document, ensure_ascii=True, sort_keys=True)
        for forbidden in (
            "price_rows",
            "completed_price_input",
            "matrix_replay",
            "observation_batch",
            "https://clock-1.invalid/time",
            '"calendar_id":',
            '"sources":',
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertTrue(all(value is False for value in document["authority"].values()))
        self.assertFalse(document["facts"]["external_clock_authority_authenticated"])
        self.assertFalse(document["facts"]["provider_identity_authenticated"])

    def test_registration_and_evaluation_verifiers_require_exact_rebuilds(self):
        with self.native_case.fixture.source_verifiers():
            self.assertTrue(
                contract.verify_strategy_correlation_cluster_portfolio_risk_session_freshness_policy_registration_v1(
                    self.registration,
                    **self.registration_inputs,
                )
            )
        clock = self._clock()
        document = self._evaluate(clock=clock)
        self.assertTrue(self._verify_evaluation(document, clock=clock))
        tampered = deepcopy(document)
        tampered["lag"]["max_completed_session_lag"] = 99
        self.assertFalse(self._verify_evaluation(tampered, clock=clock))
        self.assertFalse(self._verify_evaluation({"status": "PASS"}, clock=clock))

    def test_schema_and_static_contract_are_versioned(self):
        document = self._evaluate()
        self.assertEqual(
            self.registration["schema_version"],
            contract.REGISTRATION_SCHEMA_VERSION,
        )
        self.assertEqual(document["schema_version"], contract.EVALUATION_SCHEMA_VERSION)
        self.assertEqual(document["static_fingerprint"], contract.STATIC_FINGERPRINT)
        self.assertEqual(
            self.registration["policy"]["lag_rule"],
            contract.LAG_RULE,
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
