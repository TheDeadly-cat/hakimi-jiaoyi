import unittest
from copy import deepcopy
from datetime import date, timedelta
from decimal import getcontext, setcontext

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_fold_schedule_preregistration_v1 import (
    FOLD_ORDER,
    build_strategy_correlation_cross_lag_factor_calibration_long_horizon_fold_schedule_preregistration_v1,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_batch_verifier_v1 import (
    BATCH_STATIC_FINGERPRINT,
    POSITIVE_STATE,
    SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    evaluate_strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_batch_verifier_v1,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_batch_verifier_v1,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_protocol_v1 import (
    OBSERVATION_BATCH_SCHEMA,
)
from tests import (
    test_strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_signature_verifier_v1 as source_tests,
)


_DEFAULT = object()


def _all_keys(value):
    if isinstance(value, dict):
        keys = set(value)
        for child in value.values():
            keys.update(_all_keys(child))
        return keys
    if isinstance(value, list):
        keys = set()
        for child in value:
            keys.update(_all_keys(child))
        return keys
    return set()


class StrategyCorrelationCrossLagFactorCalibrationLongHorizonObservationBatchVerifierV1Tests(
    unittest.TestCase
):
    def setUp(self):
        self.addCleanup(setcontext, getcontext().copy())
        self.case = (
            source_tests.StrategyCorrelationCrossLagFactorCalibrationLongHorizonAnchorAdapterSignatureVerifierV1Tests(
                methodName="test_valid_signature_is_verified_but_not_admitted"
            )
        )
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.schedule_declared_at_utc = "2026-09-16T00:00:00Z"
        self.schedule_context = {
            "declared_at_utc": self.schedule_declared_at_utc,
            "expected_observation_protocol_hash": self.case.protocol[
                "protocol_hash"
            ],
            "expected_preregistration_hash": self.case.preregistration[
                "preregistration_hash"
            ],
            "long_horizon_preregistration_v1": self.case.preregistration,
            "observation_protocol_v1": self.case.protocol,
            "source_verification_context": self.case.source_context,
        }
        self.schedule = build_strategy_correlation_cross_lag_factor_calibration_long_horizon_fold_schedule_preregistration_v1(
            self.case.protocol,
            self.case.preregistration,
            self.case.source_context,
            expected_observation_protocol_hash=self.case.protocol["protocol_hash"],
            expected_preregistration_hash=self.case.preregistration[
                "preregistration_hash"
            ],
            declared_at_utc=self.schedule_declared_at_utc,
        )
        self.batch = self._batch()
        self.receipt = self.case._receipt(
            observation_batch_hash=self.batch["observation_batch_hash"],
            batch_first_observation_date=self.batch["first_observation_date"],
            batch_last_observation_date=self.batch["last_observation_date"],
            provider_timestamp_utc="2026-12-20T00:00:00Z",
        )
        self.signature_verification = self.case._build(
            receipt=self.receipt,
            expected_attestation_hash=self.receipt["attestation_hash"],
        )
        self.signature_context = {
            "attestation_receipt": self.receipt,
            "expected_attestation_hash": self.receipt["attestation_hash"],
            "expected_registration_hash": self.case.registration[
                "registration_hash"
            ],
            "long_horizon_preregistration_v1": self.case.preregistration,
            "observation_protocol_v1": self.case.protocol,
            "registration_v1": self.case.registration,
            "registration_verification_context": self.case.registration_context,
            "source_verification_context": self.case.source_context,
        }

    def _batch(self, rows=None, **overrides):
        identities = self.case.source_context["residualization_registration"][
            "identity_order"
        ]
        if rows is None:
            rows = []
            start = date(2026, 10, 1)
            for index in range(80):
                factor = ((index % 7) - 3) / 100
                rows.append(
                    {
                        "factor_return": factor,
                        "fold_id": FOLD_ORDER[index // 20],
                        "fold_position": index % 20,
                        "observation_date": (start + timedelta(days=index)).isoformat(),
                        "observation_id": f"lh-{index:03d}",
                        "position": index,
                        "returns": {
                            identity: factor * (identity_index + 1)
                            + ((index % 5) - 2) / 1000
                            for identity_index, identity in enumerate(identities)
                        },
                    }
                )
        document = {
            "factor_id": self.schedule["factor_id"],
            "factor_source_hash": self.schedule["factor_source_hash"],
            "first_observation_date": rows[0]["observation_date"] if rows else "",
            "fold_order": list(FOLD_ORDER),
            "fold_order_hash": strict_canonical_hash(list(FOLD_ORDER)),
            "future_evaluation_id": self.schedule["future_evaluation_id"],
            "identity_order_hash": self.schedule["identity_order_hash"],
            "last_observation_date": rows[-1]["observation_date"] if rows else "",
            "rows": rows,
            "schedule_hash": self.schedule["schedule_hash"],
            "schema_version": OBSERVATION_BATCH_SCHEMA,
            "source_report_consumer_v7_hash": self.schedule[
                "source_report_consumer_v7_hash"
            ],
            "static_fingerprint": BATCH_STATIC_FINGERPRINT,
        }
        document.update(overrides)
        return seal_strict_canonical_document(document, "observation_batch_hash")

    def _rebind(self, batch):
        receipt = self.case._receipt(
            observation_batch_hash=batch["observation_batch_hash"],
            batch_first_observation_date=batch.get("first_observation_date"),
            batch_last_observation_date=batch.get("last_observation_date"),
            provider_timestamp_utc="2026-12-20T00:00:00Z",
        )
        signature = self.case._build(
            receipt=receipt,
            expected_attestation_hash=receipt["attestation_hash"],
        )
        context = {
            **self.signature_context,
            "attestation_receipt": receipt,
            "expected_attestation_hash": receipt["attestation_hash"],
        }
        return signature, context

    def _build(
        self,
        schedule=_DEFAULT,
        schedule_context=_DEFAULT,
        signature_verification=_DEFAULT,
        signature_context=_DEFAULT,
        batch=_DEFAULT,
        expected_schedule_hash=_DEFAULT,
        expected_signature_hash=_DEFAULT,
        expected_batch_hash=_DEFAULT,
    ):
        schedule = self.schedule if schedule is _DEFAULT else schedule
        schedule_context = (
            self.schedule_context
            if schedule_context is _DEFAULT
            else schedule_context
        )
        signature_verification = (
            self.signature_verification
            if signature_verification is _DEFAULT
            else signature_verification
        )
        signature_context = (
            self.signature_context
            if signature_context is _DEFAULT
            else signature_context
        )
        batch = self.batch if batch is _DEFAULT else batch
        expected_schedule_hash = (
            self.schedule["schedule_hash"]
            if expected_schedule_hash is _DEFAULT
            else expected_schedule_hash
        )
        expected_signature_hash = (
            self.signature_verification["verification_hash"]
            if expected_signature_hash is _DEFAULT
            else expected_signature_hash
        )
        expected_batch_hash = (
            self.batch["observation_batch_hash"]
            if expected_batch_hash is _DEFAULT
            else expected_batch_hash
        )
        return evaluate_strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_batch_verifier_v1(
            schedule,
            schedule_context,
            signature_verification,
            signature_context,
            batch,
            expected_schedule_hash=expected_schedule_hash,
            expected_signature_verification_hash=expected_signature_hash,
            expected_batch_hash=expected_batch_hash,
        )

    def _verify(self, document, **overrides):
        values = {
            "schedule": self.schedule,
            "schedule_context": self.schedule_context,
            "signature_verification": self.signature_verification,
            "signature_context": self.signature_context,
            "batch": self.batch,
            "expected_schedule_hash": self.schedule["schedule_hash"],
            "expected_signature_hash": self.signature_verification[
                "verification_hash"
            ],
            "expected_batch_hash": self.batch["observation_batch_hash"],
        }
        values.update(overrides)
        return verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_batch_verifier_v1(
            document,
            values["schedule"],
            values["schedule_context"],
            values["signature_verification"],
            values["signature_context"],
            values["batch"],
            expected_schedule_hash=values["expected_schedule_hash"],
            expected_signature_verification_hash=values["expected_signature_hash"],
            expected_batch_hash=values["expected_batch_hash"],
        )

    def test_valid_batch_content_is_verified_but_not_admitted(self):
        document = self._build()
        self.assertEqual(document["verification_state"], POSITIVE_STATE)
        self.assertTrue(document["facts"]["batch_content_verified"])
        self.assertTrue(document["facts"]["batch_hash_signed"])
        self.assertTrue(document["facts"]["fold_assignment_verified"])
        self.assertFalse(document["facts"]["observation_admitted"])
        self.assertTrue(self._verify(document))

    def test_contract_identity_is_exact(self):
        document = self._build()
        self.assertEqual(document["schema_version"], SCHEMA_VERSION)
        self.assertEqual(document["static_fingerprint"], STATIC_FINGERPRINT)

    def test_schedule_signature_and_batch_hashes_are_cross_bound(self):
        document = self._build()
        self.assertEqual(document["schedule_hash"], self.schedule["schedule_hash"])
        self.assertEqual(
            document["signature_verification_hash"],
            self.signature_verification["verification_hash"],
        )
        self.assertEqual(
            document["observation_batch_hash"],
            self.batch["observation_batch_hash"],
        )
        self.assertEqual(
            document["attestation_hash"], self.receipt["attestation_hash"]
        )

    def test_counts_dates_and_support_are_exact(self):
        document = self._build()
        self.assertEqual(document["row_count"], 80)
        self.assertEqual(document["fold_count"], 4)
        self.assertEqual(document["rows_per_fold"], 20)
        self.assertEqual(document["maximum_evaluated_lag"], 12)
        self.assertEqual(document["minimum_pairs_at_maximum_lag"], 8)
        self.assertEqual(document["first_observation_date"], "2026-10-01")
        self.assertEqual(document["last_observation_date"], "2026-12-19")

    def test_output_redacts_private_rows_returns_and_ids(self):
        document = self._build()
        forbidden = {
            "factor_return",
            "fold_id",
            "fold_position",
            "observation_id",
            "position",
            "returns",
            "rows",
            "signature_base64",
            "public_key_base64",
        }
        self.assertTrue(forbidden.isdisjoint(_all_keys(document)))
        self.assertEqual(
            document["private_observation_ledger_hash"],
            strict_canonical_hash(self.batch["rows"]),
        )

    def test_batch_schedule_hash_tamper_is_rejected(self):
        batch = self._batch(schedule_hash="0" * 64)
        signature, context = self._rebind(batch)
        document = self._build(
            batch=batch,
            signature_verification=signature,
            signature_context=context,
            expected_signature_hash=signature["verification_hash"],
            expected_batch_hash=batch["observation_batch_hash"],
        )
        self.assertEqual(
            document["blockers"], ["OBSERVATION_BATCH_SOURCE_BINDINGS_INVALID"]
        )

    def test_row_count_must_be_exactly_eighty(self):
        for rows in (self.batch["rows"][:-1], self.batch["rows"] + [deepcopy(self.batch["rows"][-1])]):
            batch = self._batch(rows=rows)
            signature, context = self._rebind(batch)
            document = self._build(
                batch=batch,
                signature_verification=signature,
                signature_context=context,
                expected_signature_hash=signature["verification_hash"],
                expected_batch_hash=batch["observation_batch_hash"],
            )
            self.assertEqual(
                document["blockers"], ["OBSERVATION_BATCH_ROW_COUNT_INVALID"]
            )

    def test_fold_id_position_and_fold_position_are_exact(self):
        for key, value in (("fold_id", "LH-FOLD-04"), ("position", 99), ("fold_position", 19)):
            rows = deepcopy(self.batch["rows"])
            rows[1][key] = value
            batch = self._batch(rows=rows)
            signature, context = self._rebind(batch)
            document = self._build(
                batch=batch,
                signature_verification=signature,
                signature_context=context,
                expected_signature_hash=signature["verification_hash"],
                expected_batch_hash=batch["observation_batch_hash"],
            )
            self.assertEqual(
                document["blockers"], ["OBSERVATION_FOLD_ASSIGNMENT_INVALID"]
            )

    def test_dates_must_be_after_cutoff_unique_and_strictly_increasing(self):
        variants = []
        before = deepcopy(self.batch["rows"])
        before[0]["observation_date"] = "2026-09-30"
        variants.append((before, "SOURCE_SIGNATURE_STATE_NOT_POSITIVE"))
        duplicate = deepcopy(self.batch["rows"])
        duplicate[1]["observation_date"] = duplicate[0]["observation_date"]
        variants.append((duplicate, "OBSERVATION_DATE_ORDER_OR_WINDOW_INVALID"))
        reversed_rows = deepcopy(self.batch["rows"])
        reversed_rows[2]["observation_date"] = "2026-10-01"
        variants.append(
            (reversed_rows, "OBSERVATION_DATE_ORDER_OR_WINDOW_INVALID")
        )
        for rows, reason in variants:
            batch = self._batch(rows=rows)
            signature, context = self._rebind(batch)
            document = self._build(
                batch=batch,
                signature_verification=signature,
                signature_context=context,
                expected_signature_hash=signature["verification_hash"],
                expected_batch_hash=batch["observation_batch_hash"],
            )
            self.assertEqual(document["blockers"], [reason])

    def test_observation_ids_are_strict_and_unique(self):
        for value in ("bad id", self.batch["rows"][0]["observation_id"]):
            rows = deepcopy(self.batch["rows"])
            rows[1]["observation_id"] = value
            batch = self._batch(rows=rows)
            signature, context = self._rebind(batch)
            document = self._build(
                batch=batch,
                signature_verification=signature,
                signature_context=context,
                expected_signature_hash=signature["verification_hash"],
                expected_batch_hash=batch["observation_batch_hash"],
            )
            self.assertEqual(
                document["blockers"], ["OBSERVATION_ID_INVALID_OR_DUPLICATE"]
            )

    def test_identity_return_keys_must_be_exact(self):
        for mutate in ("missing", "extra"):
            rows = deepcopy(self.batch["rows"])
            if mutate == "missing":
                rows[0]["returns"].pop("B")
            else:
                rows[0]["returns"]["C"] = 0.0
            batch = self._batch(rows=rows)
            signature, context = self._rebind(batch)
            document = self._build(
                batch=batch,
                signature_verification=signature,
                signature_context=context,
                expected_signature_hash=signature["verification_hash"],
                expected_batch_hash=batch["observation_batch_hash"],
            )
            self.assertEqual(
                document["blockers"], ["OBSERVATION_IDENTITY_RETURNS_INVALID"]
            )

    def test_factor_and_identity_values_must_be_finite_numbers_not_bool(self):
        variants = []
        factor = deepcopy(self.batch["rows"])
        factor[0]["factor_return"] = True
        variants.append((factor, "OBSERVATION_FACTOR_RETURN_INVALID"))
        identity = deepcopy(self.batch["rows"])
        identity[0]["returns"]["A"] = False
        variants.append((identity, "OBSERVATION_IDENTITY_RETURN_VALUE_INVALID"))
        for rows, reason in variants:
            batch = self._batch(rows=rows)
            signature, context = self._rebind(batch)
            document = self._build(
                batch=batch,
                signature_verification=signature,
                signature_context=context,
                expected_signature_hash=signature["verification_hash"],
                expected_batch_hash=batch["observation_batch_hash"],
            )
            self.assertEqual(document["blockers"], [reason])

    def test_source_identity_factor_and_fold_hashes_are_exact(self):
        for key, value in (
            ("identity_order_hash", "0" * 64),
            ("factor_source_hash", "0" * 64),
            ("fold_order_hash", "0" * 64),
            ("source_report_consumer_v7_hash", "0" * 64),
        ):
            batch = self._batch(**{key: value})
            signature, context = self._rebind(batch)
            document = self._build(
                batch=batch,
                signature_verification=signature,
                signature_context=context,
                expected_signature_hash=signature["verification_hash"],
                expected_batch_hash=batch["observation_batch_hash"],
            )
            self.assertEqual(
                document["blockers"], ["OBSERVATION_BATCH_SOURCE_BINDINGS_INVALID"]
            )

    def test_batch_first_and_last_dates_match_rows_and_signed_receipt(self):
        batch = self._batch(first_observation_date="2026-10-02")
        signature, context = self._rebind(batch)
        document = self._build(
            batch=batch,
            signature_verification=signature,
            signature_context=context,
            expected_signature_hash=signature["verification_hash"],
            expected_batch_hash=batch["observation_batch_hash"],
        )
        self.assertEqual(
            document["blockers"], ["OBSERVATION_BATCH_DATE_BINDINGS_INVALID"]
        )

    def test_expected_hashes_are_bound(self):
        self.assertEqual(
            self._build(expected_schedule_hash="0" * 64)["blockers"],
            ["SOURCE_SCHEDULE_HASH_MISMATCH"],
        )
        self.assertEqual(
            self._build(expected_signature_hash="0" * 64)["blockers"],
            ["SOURCE_SIGNATURE_VERIFICATION_HASH_MISMATCH"],
        )
        self.assertEqual(
            self._build(expected_batch_hash="0" * 64)["blockers"],
            ["SIGNED_BATCH_HASH_MISMATCH"],
        )

    def test_contexts_require_exact_fields(self):
        schedule_context = deepcopy(self.schedule_context)
        schedule_context.pop("declared_at_utc")
        signature_context = deepcopy(self.signature_context)
        signature_context["authority"] = "forged"
        self.assertEqual(
            self._build(schedule_context=schedule_context)["blockers"],
            ["SCHEDULE_VERIFICATION_CONTEXT_INVALID"],
        )
        self.assertEqual(
            self._build(signature_context=signature_context)["blockers"],
            ["SIGNATURE_VERIFICATION_CONTEXT_INVALID"],
        )

    def test_resealed_schedule_tamper_is_rejected(self):
        schedule = deepcopy(self.schedule)
        schedule["total_scheduled_rows"] = 81
        schedule = seal_strict_canonical_document(
            {key: value for key, value in schedule.items() if key != "schedule_hash"},
            "schedule_hash",
        )
        document = self._build(
            schedule=schedule,
            expected_schedule_hash=schedule["schedule_hash"],
        )
        self.assertEqual(document["blockers"], ["SOURCE_SCHEDULE_NOT_VERIFIED"])

    def test_signature_verification_tamper_is_rejected(self):
        signature = deepcopy(self.signature_verification)
        signature["provider_id"] = "OTHER-PROVIDER"
        signature = seal_strict_canonical_document(
            {
                key: value
                for key, value in signature.items()
                if key != "verification_hash"
            },
            "verification_hash",
        )
        document = self._build(
            signature_verification=signature,
            expected_signature_hash=signature["verification_hash"],
        )
        self.assertEqual(
            document["blockers"], ["SOURCE_SIGNATURE_VERIFICATION_NOT_VERIFIED"]
        )

    def test_authority_and_remaining_gaps_are_locked(self):
        document = self._build()
        self.assertTrue(document["authority"]["descriptive_only"])
        for key, value in document["authority"].items():
            if key != "descriptive_only":
                self.assertFalse(value, key)
        for key in (
            "external_authenticity_proven",
            "external_registration_time_verified",
            "observation_admitted",
            "provider_identity_verified",
            "replay_registry_checked",
            "result_available",
        ):
            self.assertFalse(document["facts"][key], key)

    def test_build_is_deterministic(self):
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertEqual(first["verification_hash"], second["verification_hash"])

    def test_verifier_rejects_tamper_and_extra_keys(self):
        document = self._build()
        tampered = deepcopy(document)
        tampered["verification_state"] = "OBSERVATION_ADMITTED"
        extra = deepcopy(document)
        extra["ready"] = True
        self.assertFalse(self._verify(tampered))
        self.assertFalse(self._verify(extra))
        self.assertFalse(self._verify(None))

    def test_schema_keys_are_exact(self):
        document = self._build()
        self.assertEqual(
            set(document),
            {
                "attestation_hash",
                "authority",
                "blockers",
                "factor_id",
                "factor_source_hash",
                "facts",
                "first_observation_date",
                "fold_count",
                "fold_order_hash",
                "future_evaluation_id",
                "identity_count",
                "identity_order_hash",
                "last_observation_date",
                "maximum_evaluated_lag",
                "minimum_pairs_at_maximum_lag",
                "observation_batch_hash",
                "private_observation_ledger_hash",
                "provider_id",
                "provider_timestamp_utc",
                "row_count",
                "rows_per_fold",
                "schedule_hash",
                "schema_version",
                "signature_verification_hash",
                "source_report_consumer_v7_hash",
                "source_state",
                "static_fingerprint",
                "verification_hash",
                "verification_reason",
                "verification_state",
            },
        )


if __name__ == "__main__":
    unittest.main()
