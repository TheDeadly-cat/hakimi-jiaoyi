from __future__ import annotations

import hashlib
import inspect
import re
from collections.abc import Iterator, Mapping
from copy import deepcopy
from pathlib import Path
from unittest import TestCase

from exchange_terminal.interfaces.http import (
    portfolio_correlation_admission_effective_budget_readonly_projection_candidate_v1 as projection_candidate,
)
from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_python_provider_binding_v1 as provider_binding,
)
from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_readonly_http_projection_mount_preregistration_v1 as subject,
)
from tests import (
    test_portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1 as source_consumer_tests,
)


ROOT = Path(__file__).resolve().parents[1]


class SecondReadFlipMapping(Mapping[str, object]):
    def __init__(self, base: dict[str, object], key: str, forged: object) -> None:
        self._base = base
        self._key = key
        self._forged = forged
        self.reads = 0

    def __iter__(self) -> Iterator[str]:
        return iter(self._base)

    def __len__(self) -> int:
        return len(self._base)

    def __getitem__(self, key: str) -> object:
        if key == self._key:
            self.reads += 1
            if self.reads > 1:
                return self._forged
        return self._base[key]


class ReadonlyHttpProjectionMountPreregistrationV1Tests(TestCase):
    def setUp(self) -> None:
        self.document = subject.build_portfolio_correlation_admission_effective_budget_readonly_http_projection_mount_preregistration_v1()

    def _synthetic_responses(self) -> dict[str, dict]:
        case = source_consumer_tests.HashEnvelopeSourceConsumerV1Tests(
            methodName="runTest"
        )
        case.setUp()
        fixture = case.fixture
        evidence = fixture.evidence
        request = {
            "schema_version": projection_candidate.REQUEST_SCHEMA_VERSION,
            "projection_id": projection_candidate.PROJECTION_ID,
        }
        binding = provider_binding.build_portfolio_correlation_admission_effective_budget_python_provider_binding_v1()
        positional = [
            case.adapter_registration,
            case.consumer_preregistration,
            fixture.binding,
            fixture.admission,
            fixture.budget,
            evidence["report_document"],
            evidence["correlation_preregistration_document"],
            evidence["correlation_matrix_document"],
            evidence["selection_cells_document"],
            fixture.budget_case.audit,
            evidence["complete_link_gate_document"],
            evidence["strata_preregistration_document"],
            evidence["strata_gate_document"],
        ]
        keyword = {
            "strategy_id": evidence["strategy_id"],
            "variant_id": evidence["variant_id"],
            "lane": evidence["lane"],
            **fixture.inputs,
        }

        def build(context: list[object]) -> dict:
            return projection_candidate.build_portfolio_correlation_admission_effective_budget_readonly_http_projection_candidate_v1(
                request,
                provider_binding_document=binding,
                internal_provider_positional=context,
                internal_provider_keyword=keyword,
            )

        unknown = deepcopy(positional)
        unknown[2] = []
        blocked = deepcopy(positional)
        blocked[0]["facts"]["javascript_adapter_registered"] = False
        return {
            "known": build(positional),
            "unknown": build(unknown),
            "blocked": build(blocked),
        }

    def test_schema_state_and_hash_are_exact(self) -> None:
        self.assertEqual(self.document["schema_version"], subject.SCHEMA_VERSION)
        self.assertEqual(
            self.document["static_fingerprint"], subject.STATIC_FINGERPRINT
        )
        self.assertEqual(
            self.document["preregistration_id"], subject.PREREGISTRATION_ID
        )
        self.assertEqual(self.document["status"], "BLOCKED")
        self.assertEqual(
            self.document["mount_preregistration_hash"],
            subject.EXPECTED_MOUNT_PREREGISTRATION_HASH,
        )

    def test_candidate_contract_matches_adr0317(self) -> None:
        candidate = self.document["candidate_contract"]
        self.assertEqual(
            candidate["request_schema_version"],
            projection_candidate.REQUEST_SCHEMA_VERSION,
        )
        self.assertEqual(
            candidate["response_schema_version"],
            projection_candidate.RESPONSE_SCHEMA_VERSION,
        )
        self.assertEqual(
            candidate["static_fingerprint"], projection_candidate.STATIC_FINGERPRINT
        )
        self.assertEqual(candidate["projection_id"], projection_candidate.PROJECTION_ID)
        self.assertEqual(candidate["state_order"], ["KNOWN", "UNKNOWN", "BLOCKED"])

    def test_synthetic_state_receipts_match_current_candidate(self) -> None:
        responses = self._synthetic_responses()
        actual = {
            f"{state}_response_hash": response["response_hash"]
            for state, response in responses.items()
        }
        self.assertEqual(actual, subject.SYNTHETIC_STATE_RECEIPTS)
        self.assertEqual(
            [responses[state]["state"] for state in ("known", "unknown", "blocked")],
            ["KNOWN", "UNKNOWN", "BLOCKED"],
        )

    def test_source_baseline_files_match_exact_pins(self) -> None:
        pins = subject.SOURCE_BASELINE_PINS
        for prefix in (
            "candidate_implementation",
            "candidate_test",
            "candidate_adr",
            "server",
            "http_contract",
        ):
            path = ROOT / pins[f"{prefix}_path"]
            actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(actual_hash, pins[f"{prefix}_sha256"], prefix)
        self.assertEqual(
            pins["provider_binding_hash"],
            provider_binding.EXPECTED_PROVIDER_BINDING_HASH,
        )

    def test_method_and_route_are_proposed_but_unregistered(self) -> None:
        transport = self.document["proposed_transport"]
        self.assertEqual(transport["method"], subject.PROPOSED_METHOD)
        self.assertEqual(transport["route"], subject.PROPOSED_ROUTE)
        self.assertIsNone(transport["handler"])
        self.assertIsNone(transport["endpoint"])
        self.assertFalse(transport["registered"])
        self.assertFalse(transport["externally_callable"])

    def test_http_status_mapping_separates_transport_from_three_state_result(self) -> None:
        mapping = self.document["proposed_http_status_mapping"]
        self.assertEqual(mapping["known"], 200)
        self.assertEqual(mapping["verified_unknown"], 200)
        self.assertEqual(mapping["verified_blocked"], 200)
        self.assertEqual(mapping["request_contract_invalid"], 400)
        self.assertEqual(mapping["authentication_failed"], 401)
        self.assertEqual(mapping["csrf_failed"], 403)
        self.assertEqual(mapping["rate_limited"], 429)
        self.assertEqual(mapping["trusted_context_unavailable"], 503)
        self.assertEqual(mapping["provider_failure"], 503)

    def test_required_transport_controls_are_fail_closed(self) -> None:
        controls = self.document["required_transport_controls"]
        for field in (
            "loopback_only",
            "same_origin_required",
            "read_only",
            "exact_request_contract_required",
            "internal_provider_context_only",
        ):
            self.assertTrue(controls[field], field)
        for field in (
            "client_source_documents_allowed",
            "client_provider_context_allowed",
            "request_body_logging_allowed",
            "runtime_reads_allowed",
            "runtime_mutations_allowed",
            "database_reads_allowed",
            "database_writes_allowed",
            "cache_reads_allowed",
            "cache_writes_allowed",
        ):
            self.assertFalse(controls[field], field)

    def test_security_and_mount_controls_are_explicitly_unregistered(self) -> None:
        controls = self.document["unregistered_controls"]
        self.assertEqual(len(controls), 9)
        for name, control in controls.items():
            if "registered" in control:
                self.assertFalse(control["registered"], name)
        self.assertFalse(controls["independent_mount_review"]["completed"])
        self.assertIsNone(controls["authentication"]["mechanism"])
        self.assertIsNone(controls["csrf_protection"]["mechanism"])
        self.assertIsNone(controls["rate_limit"]["requests_per_window"])
        self.assertIsNone(controls["request_body_limit"]["maximum_bytes"])

    def test_client_context_and_request_logging_remain_forbidden(self) -> None:
        controls = self.document["unregistered_controls"]
        self.assertFalse(
            controls["trusted_internal_context_provider"]["client_supplied_allowed"]
        )
        self.assertFalse(
            controls["request_log_redaction"]["request_body_logging_allowed"]
        )

    def test_facts_record_no_handler_route_or_runtime_action(self) -> None:
        facts = self.document["facts"]
        self.assertTrue(facts["transport_policy_preregistered"])
        self.assertTrue(facts["control_requirements_complete"])
        for field in (
            "control_registrations_complete",
            "trusted_internal_context_provider_present",
            "handler_implemented",
            "route_registered",
            "externally_callable",
            "browser_executed",
            "ui_mounted",
            "current_activated",
            "runtime_mutations_performed",
            "profitability_proven",
        ):
            self.assertFalse(facts[field], field)

    def test_authority_is_descriptive_and_fully_locked(self) -> None:
        authority = self.document["authority"]
        self.assertTrue(authority["descriptive_only"])
        for key, value in authority.items():
            if key != "descriptive_only":
                self.assertFalse(value, key)

    def test_all_expected_blockers_remain(self) -> None:
        self.assertEqual(self.document["blockers"], list(subject.MOUNT_BLOCKERS))
        self.assertEqual(len(self.document["blockers"]), 13)

    def test_builder_accepts_no_policy_override(self) -> None:
        signature = inspect.signature(
            subject.build_portfolio_correlation_admission_effective_budget_readonly_http_projection_mount_preregistration_v1
        )
        self.assertEqual(list(signature.parameters), [])
        with self.assertRaises(TypeError):
            subject.build_portfolio_correlation_admission_effective_budget_readonly_http_projection_mount_preregistration_v1(
                route="/attacker"
            )

    def test_exact_rebuild_is_deterministic_and_verifiable(self) -> None:
        rebuilt = subject.build_portfolio_correlation_admission_effective_budget_readonly_http_projection_mount_preregistration_v1()
        self.assertEqual(rebuilt, self.document)
        self.assertTrue(
            subject.verify_portfolio_correlation_admission_effective_budget_readonly_http_projection_mount_preregistration_v1(
                self.document
            )
        )

    def test_transport_security_or_authority_promotion_is_rejected(self) -> None:
        mutations = (
            lambda value: value["proposed_transport"].update({"registered": True}),
            lambda value: value["unregistered_controls"]["authentication"].update(
                {"registered": True, "mechanism": "forged"}
            ),
            lambda value: value["unregistered_controls"]["route_registration"].update(
                {"registered": True, "registration_id": "forged"}
            ),
            lambda value: value["authority"].update({"mount_allowed": True}),
            lambda value: value.update({"current": True}),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                tampered = deepcopy(self.document)
                mutate(tampered)
                self.assertFalse(
                    subject.verify_portfolio_correlation_admission_effective_budget_readonly_http_projection_mount_preregistration_v1(
                        tampered
                    )
                )

    def test_single_snapshot_blocks_second_read_hash_swap(self) -> None:
        wrapped = SecondReadFlipMapping(
            self.document,
            "mount_preregistration_hash",
            "0" * 64,
        )
        self.assertTrue(
            subject.verify_portfolio_correlation_admission_effective_budget_readonly_http_projection_mount_preregistration_v1(
                wrapped
            )
        )
        self.assertEqual(wrapped.reads, 1)

    def test_cyclic_and_nonmapping_inputs_fail_closed(self) -> None:
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        self.assertFalse(
            subject.verify_portfolio_correlation_admission_effective_budget_readonly_http_projection_mount_preregistration_v1(
                cyclic
            )
        )
        self.assertFalse(
            subject.verify_portfolio_correlation_admission_effective_budget_readonly_http_projection_mount_preregistration_v1(
                None
            )
        )

    def test_values_have_no_ready_or_profitability_promotion(self) -> None:
        values: list[str] = []

        def collect(value: object) -> None:
            if isinstance(value, dict):
                for nested in value.values():
                    collect(nested)
            elif isinstance(value, list):
                for nested in value:
                    collect(nested)
            elif isinstance(value, str):
                values.append(value)

        collect(self.document)
        self.assertIsNone(
            re.search(r"\bREADY\b|\bprofit\b|\breturn\b|\balpha\b|win rate", " ".join(values), re.IGNORECASE)
        )

    def test_public_api_has_no_host_runtime_database_cache_or_secret_parameter(self) -> None:
        for function in (
            subject.build_portfolio_correlation_admission_effective_budget_readonly_http_projection_mount_preregistration_v1,
            subject.verify_portfolio_correlation_admission_effective_budget_readonly_http_projection_mount_preregistration_v1,
        ):
            parameters = set(inspect.signature(function).parameters)
            self.assertTrue(
                parameters.isdisjoint(
                    {
                        "server",
                        "route",
                        "handler",
                        "runtime",
                        "database",
                        "cache",
                        "private_key",
                        "authentication_token",
                    }
                )
            )
