from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import date, timedelta
import hashlib
import json
import random
import unittest
from unittest.mock import patch

from exchange_terminal.services import strategy_correlation_common_support_calendar_provider_composition_v1 as composition
from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1 as calendar_source
from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1 as provider_source
from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_cluster_preregistration,
)
from exchange_terminal.services.strategy_correlation_common_support_derivation_receipt_v1 import (
    build_correlation_common_support_derivation_receipt_v1,
)
from exchange_terminal.services.strategy_correlation_return_replay import (
    build_correlation_completed_price_input,
    build_correlation_matrix_replay,
)


def _hash(value: object) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class StrategyCorrelationCommonSupportCalendarProviderCompositionV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.symbols = ["A", "B"]
        self.provider_id = "APPEND-ONLY-PROVIDER-1"
        self.future_evaluation_id = "FUTURE-EVALUATION-1"
        self.batch_dates = [
            (date(2026, 10, 1) + timedelta(days=index)).isoformat()
            for index in range(80)
        ]
        self.batch_rows = [
            {
                "observation_date": label,
                "returns": {
                    symbol: random.Random((index + 1) * seed).uniform(-0.01, 0.01)
                    for seed, symbol in enumerate(self.symbols, start=101)
                },
            }
            for index, label in enumerate(self.batch_dates)
        ]
        self.matrix_replay = self.replay()
        self.derivation_receipt = (
            build_correlation_common_support_derivation_receipt_v1(
                self.matrix_replay
            )
        )
        self.calendar_document, self.calendar_bundle = self.calendar_evidence()
        self.provider_document, self.provider_bundle = self.provider_evidence()

    def replay(
        self,
        *,
        provider_id: str | None = None,
        data_hash_suffix: str = "v1",
    ) -> dict[str, object]:
        source = provider_id or self.provider_id
        preregistration = build_correlation_cluster_preregistration([
            {"cluster_id": "cluster-a", "members": ["A"]},
            {"cluster_id": "cluster-b", "members": ["B"]},
        ])
        initial = (date.fromisoformat(self.batch_dates[0]) - timedelta(days=1)).isoformat()
        payloads = {}
        manifests = []
        for symbol in self.symbols:
            price = 100.0
            rows: list[dict[str, object]] = [
                {"date": initial, "close": price, "complete": True}
            ]
            for batch_row in self.batch_rows:
                price *= 1.0 + batch_row["returns"][symbol]
                rows.append({
                    "date": batch_row["observation_date"],
                    "close": price,
                    "complete": True,
                })
            payloads[symbol] = {"source": source, "rows": rows}
            manifests.append({
                "role": "SELECTION",
                "symbol": symbol,
                "timeframe": "1D",
                "source": source,
                "data_hash": hashlib.sha256(
                    (symbol + "|" + data_hash_suffix).encode("ascii")
                ).hexdigest(),
                "row_count": len(rows),
            })
        completed = build_correlation_completed_price_input(
            payloads,
            manifests,
            preregistration,
            cutoff_date=self.batch_dates[-1],
            selection_alignment_input_hash="d" * 64,
        )
        return build_correlation_matrix_replay(completed, preregistration)

    def calendar_evidence(self):
        observation_batch = {
            "observation_batch_hash": _hash(self.batch_rows),
            "rows": deepcopy(self.batch_rows),
        }
        registration = {
            "identity_calendar_assignments": [
                {"calendar_id": "24/7", "identity_index": index}
                for index in range(len(self.symbols))
            ],
            "distinct_calendar_ids": ["24/7"],
        }
        document = {
            "schema_version": calendar_source.SCHEMA_VERSION,
            "static_fingerprint": calendar_source.STATIC_FINGERPRINT,
            "source_state": "VERIFIED",
            "verification_hash": _hash("calendar-verification"),
            "calendar_session_evaluation_hash": _hash("calendar-evaluation"),
            "source_calendar_registration_hash": _hash("calendar-registration"),
            "source_batch_verification_hash": _hash("batch-verification"),
            "observation_batch_hash": observation_batch["observation_batch_hash"],
            "provider_id": self.provider_id,
            "future_evaluation_id": self.future_evaluation_id,
            "identity_count": len(self.symbols),
            "distinct_calendar_count": 1,
            "row_count": len(self.batch_dates),
            "session_check_count": len(self.batch_dates),
            "completed_common_session_count": len(self.batch_dates),
            "first_observation_date": self.batch_dates[0],
            "last_observation_date": self.batch_dates[-1],
            "facts": {
                "calendar_registration_verified": True,
                "source_batch_verified": True,
                "schedule_cross_binding_verified": True,
                "calendar_sessions_evaluated": True,
                "common_session_intersection_verified": True,
                "all_registered_sessions_completed": True,
                "external_provider_identity_verified": False,
                "observation_admission_allowed": False,
            },
            "authority": {
                "calendar_enforcement_activated": False,
                "candidate_activation_allowed": False,
                "current_admission_allowed": False,
                "current_pointer_written": False,
                "future_evaluation_allowed": False,
                "observation_admission_allowed": False,
                "paper_authorized": False,
                "live_order_allowed": False,
                "profitability_claim_allowed": False,
            },
        }
        bundle = {
            "calendar_registration_v1": registration,
            "calendar_registration_verification_context": {},
            "batch_verification_v1": {},
            "batch_verification_context": {},
            "observation_batch": observation_batch,
            "expected_calendar_registration_hash": document[
                "source_calendar_registration_hash"
            ],
            "expected_batch_verification_hash": document[
                "source_batch_verification_hash"
            ],
        }
        return document, bundle

    def provider_evidence(self):
        registration_hash = _hash("provider-registration")
        assertion_hash = _hash("provider-assertion")
        document = {
            "schema_version": provider_source.SCHEMA_VERSION,
            "static_fingerprint": provider_source.STATIC_FINGERPRINT,
            "source_state": "VERIFIED",
            "verification_hash": _hash("provider-verification"),
            "source_provider_identity_registration_hash": registration_hash,
            "assertion_hash": assertion_hash,
            "provider_identity_document_sha256": _hash("identity-document"),
            "provider_id": self.provider_id,
            "future_evaluation_id": self.future_evaluation_id,
            "facts": {
                "source_registration_verified": True,
                "source_bindings_verified": True,
                "assertion_receipt_seal_verified": True,
                "assertion_content_hash_verified": True,
                "identity_registry_key_match": True,
                "identity_registry_signature_verified": True,
                "snapshot_membership_verified": True,
                "assertion_chronology_claim_valid": True,
                "provider_identity_verified": False,
                "external_identity_registry_authenticity_proven": False,
            },
            "authority": {
                "candidate_activation_allowed": False,
                "current_admission_allowed": False,
                "current_pointer_written": False,
                "external_provider_identity_verified": False,
                "future_evaluation_allowed": False,
                "identity_assertion_use_allowed": False,
                "provider_identity_admission_allowed": False,
                "paper_authorized": False,
                "live_order_allowed": False,
                "profitability_claim_allowed": False,
            },
        }
        bundle = {
            "provider_identity_registration_v1": {
                "provider_id": self.provider_id,
            },
            "provider_identity_registration_verification_context": {},
            "identity_assertion_receipt": {
                "provider_id": self.provider_id,
            },
            "expected_provider_identity_registration_hash": registration_hash,
            "expected_identity_assertion_hash": assertion_hash,
        }
        return document, bundle

    @contextmanager
    def source_verifiers(self, *, calendar: bool = True, provider: bool = True):
        with patch.object(
            calendar_source,
            "verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1",
            return_value=calendar,
        ) as calendar_mock, patch.object(
            provider_source,
            "verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1",
            return_value=provider,
        ) as provider_mock:
            yield calendar_mock, provider_mock

    def build(self, **overrides):
        values = {
            "derivation_receipt": self.derivation_receipt,
            "matrix_replay": self.matrix_replay,
            "calendar_session_verification": self.calendar_document,
            "calendar_verification_bundle": self.calendar_bundle,
            "provider_identity_verification": self.provider_document,
            "provider_verification_bundle": self.provider_bundle,
        }
        values.update(overrides)
        with self.source_verifiers() as mocks:
            result = composition.build_correlation_common_support_calendar_provider_composition_v1(
                **values
            )
        self.assertEqual(mocks[0].call_count, 1)
        self.assertEqual(mocks[1].call_count, 1)
        return result

    def verify(self, document, **overrides):
        values = {
            "derivation_receipt": self.derivation_receipt,
            "matrix_replay": self.matrix_replay,
            "calendar_session_verification": self.calendar_document,
            "calendar_verification_bundle": self.calendar_bundle,
            "provider_identity_verification": self.provider_document,
            "provider_verification_bundle": self.provider_bundle,
        }
        values.update(overrides)
        with self.source_verifiers():
            return composition.verify_correlation_common_support_calendar_provider_composition_v1(
                document,
                **values,
            )

    def test_positive_composition_is_bounded_and_inactive(self) -> None:
        result = self.build()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["composition_state"], composition.COMPOSITION_STATE)
        self.assertEqual(result["calendar_batch_session_count"], 80)
        self.assertEqual(result["common_price_row_count"], 61)
        self.assertEqual(result["calendar_suffix_start_offset"], 19)
        self.assertTrue(result["facts"]["calendar_price_suffix_exact"])
        self.assertTrue(result["facts"]["dataset_source_label_matches_provider_id"])
        self.assertFalse(result["facts"]["dataset_content_attested_by_provider"])
        self.assertFalse(result["current_writer_activation_allowed"])
        self.assertFalse(result["current_admission_allowed"])
        self.assertEqual(result["permissions"], {
            "paper_authorized": False,
            "live_order_allowed": False,
        })

    def test_verifier_accepts_exact_rebuild(self) -> None:
        self.assertEqual(self.verify(self.build())["status"], "PASS")

    def test_output_is_deterministic_and_private(self) -> None:
        first = self.build()
        second = self.build()
        self.assertEqual(first, second)
        rendered = repr(first)
        self.assertNotIn("2026-", rendered)
        self.assertNotIn("price_rows", rendered)
        self.assertNotIn("returns", rendered)
        self.assertNotIn(self.provider_id, rendered)

    def test_calendar_public_verifier_failure_blocks(self) -> None:
        with self.source_verifiers(calendar=False):
            with self.assertRaisesRegex(ValueError, "calendar_source_invalid"):
                composition.build_correlation_common_support_calendar_provider_composition_v1(
                    self.derivation_receipt,
                    self.matrix_replay,
                    self.calendar_document,
                    self.calendar_bundle,
                    self.provider_document,
                    self.provider_bundle,
                )

    def test_provider_public_verifier_failure_blocks(self) -> None:
        with self.source_verifiers(provider=False):
            with self.assertRaisesRegex(ValueError, "provider_source_invalid"):
                composition.build_correlation_common_support_calendar_provider_composition_v1(
                    self.derivation_receipt,
                    self.matrix_replay,
                    self.calendar_document,
                    self.calendar_bundle,
                    self.provider_document,
                    self.provider_bundle,
                )

    def test_derivation_receipt_tamper_blocks(self) -> None:
        receipt = deepcopy(self.derivation_receipt)
        receipt["common_price_row_count"] -= 1
        with self.assertRaisesRegex(ValueError, "derivation_receipt_invalid"):
            self.build(derivation_receipt=receipt)

    def test_calendar_suffix_mismatch_blocks(self) -> None:
        document = deepcopy(self.calendar_document)
        bundle = deepcopy(self.calendar_bundle)
        shifted = [
            (date.fromisoformat(item) + timedelta(days=1)).isoformat()
            for item in self.batch_dates
        ]
        for row, label in zip(bundle["observation_batch"]["rows"], shifted):
            row["observation_date"] = label
        bundle["observation_batch"]["observation_batch_hash"] = _hash(
            bundle["observation_batch"]["rows"]
        )
        document["observation_batch_hash"] = bundle["observation_batch"][
            "observation_batch_hash"
        ]
        document["first_observation_date"] = shifted[0]
        document["last_observation_date"] = shifted[-1]
        with self.assertRaisesRegex(ValueError, "suffix_mismatch"):
            self.build(
                calendar_session_verification=document,
                calendar_verification_bundle=bundle,
            )

    def test_batch_identity_mismatch_blocks(self) -> None:
        bundle = deepcopy(self.calendar_bundle)
        bundle["observation_batch"]["rows"][0]["returns"]["C"] = (
            bundle["observation_batch"]["rows"][0]["returns"].pop("B")
        )
        with self.assertRaisesRegex(ValueError, "identity_mismatch"):
            self.build(calendar_verification_bundle=bundle)

    def test_dataset_source_label_mismatch_blocks(self) -> None:
        replay = self.replay(provider_id="OTHER-PROVIDER")
        receipt = build_correlation_common_support_derivation_receipt_v1(replay)
        with self.assertRaisesRegex(ValueError, "provider_label_mismatch"):
            self.build(matrix_replay=replay, derivation_receipt=receipt)

    def test_provider_id_cross_source_mismatch_blocks(self) -> None:
        document = deepcopy(self.provider_document)
        bundle = deepcopy(self.provider_bundle)
        document["provider_id"] = "OTHER-PROVIDER"
        bundle["provider_identity_registration_v1"]["provider_id"] = "OTHER-PROVIDER"
        bundle["identity_assertion_receipt"]["provider_id"] = "OTHER-PROVIDER"
        with self.assertRaisesRegex(ValueError, "provider_identity_mismatch"):
            self.build(
                provider_identity_verification=document,
                provider_verification_bundle=bundle,
            )

    def test_future_evaluation_mismatch_blocks(self) -> None:
        document = deepcopy(self.provider_document)
        document["future_evaluation_id"] = "UNRELATED-EVALUATION"
        with self.assertRaisesRegex(ValueError, "provider_identity_mismatch"):
            self.build(provider_identity_verification=document)

    def test_calendar_assignment_order_and_bool_alias_block(self) -> None:
        for invalid in (1, True):
            bundle = deepcopy(self.calendar_bundle)
            bundle["calendar_registration_v1"]["identity_calendar_assignments"][0][
                "identity_index"
            ] = invalid
            with self.subTest(invalid=invalid), self.assertRaisesRegex(
                ValueError,
                "assignment_invalid",
            ):
                self.build(calendar_verification_bundle=bundle)

    def test_missing_calendar_source_fact_blocks(self) -> None:
        document = deepcopy(self.calendar_document)
        document["facts"]["common_session_intersection_verified"] = False
        with self.assertRaisesRegex(ValueError, "source_fact_missing"):
            self.build(calendar_session_verification=document)

    def test_missing_provider_source_fact_blocks(self) -> None:
        document = deepcopy(self.provider_document)
        document["facts"]["snapshot_membership_verified"] = False
        with self.assertRaisesRegex(ValueError, "source_fact_missing"):
            self.build(provider_identity_verification=document)

    def test_calendar_authority_injection_blocks(self) -> None:
        fields = {
            "calendar_enforcement_activated",
            "candidate_activation_allowed",
            "current_admission_allowed",
            "current_pointer_written",
            "future_evaluation_allowed",
            "live_order_allowed",
            "observation_admission_allowed",
            "paper_authorized",
            "profitability_claim_allowed",
        }
        for field in fields:
            document = deepcopy(self.calendar_document)
            document["authority"][field] = True
            with self.subTest(field=field), self.assertRaisesRegex(
                ValueError,
                "execution_authority_invalid",
            ):
                self.build(calendar_session_verification=document)

    def test_provider_authority_injection_blocks(self) -> None:
        fields = {
            "candidate_activation_allowed",
            "current_admission_allowed",
            "current_pointer_written",
            "external_provider_identity_verified",
            "future_evaluation_allowed",
            "identity_assertion_use_allowed",
            "live_order_allowed",
            "paper_authorized",
            "profitability_claim_allowed",
            "provider_identity_admission_allowed",
        }
        for field in fields:
            document = deepcopy(self.provider_document)
            document["authority"][field] = True
            with self.subTest(field=field), self.assertRaisesRegex(
                ValueError,
                "execution_authority_invalid",
            ):
                self.build(provider_identity_verification=document)

    def test_extra_bundle_fields_block(self) -> None:
        bundle = deepcopy(self.calendar_bundle)
        bundle["extra"] = True
        with self.assertRaisesRegex(ValueError, "calendar_source_invalid"):
            self.build(calendar_verification_bundle=bundle)

    def test_dataset_hash_drift_changes_composition_hash(self) -> None:
        first = self.build()
        replay = self.replay(data_hash_suffix="v2")
        receipt = build_correlation_common_support_derivation_receipt_v1(replay)
        second = self.build(matrix_replay=replay, derivation_receipt=receipt)
        self.assertNotEqual(
            first["dataset_provider_binding_hash"],
            second["dataset_provider_binding_hash"],
        )
        self.assertNotEqual(first["composition_hash"], second["composition_hash"])

    def test_coherently_resealed_output_drift_blocks(self) -> None:
        result = self.build()
        result["symbol_count"] += 1
        result["composition_hash"] = _hash({
            key: value for key, value in result.items() if key != "composition_hash"
        })
        check = self.verify(result)
        self.assertEqual(check["status"], "BLOCK")
        self.assertIn(
            "calendar_provider_composition_semantic_mismatch",
            check["blockers"],
        )


if __name__ == "__main__":
    unittest.main()
