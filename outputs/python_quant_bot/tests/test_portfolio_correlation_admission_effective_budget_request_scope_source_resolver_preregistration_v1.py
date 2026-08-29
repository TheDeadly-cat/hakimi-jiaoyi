from __future__ import annotations

import hashlib
import inspect
import re
from collections.abc import Iterator, Mapping
from copy import deepcopy
from pathlib import Path
from unittest import TestCase

from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_request_scope_source_resolver_preregistration_v1 as subject,
)
from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_trusted_internal_context_provider_preregistration_v1 as context_preregistration,
)
from exchange_terminal.services.strict_canonical_json_hash import strict_canonical_hash


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


class RequestScopeSourceResolverPreregistrationV1Tests(TestCase):
    def setUp(self) -> None:
        self.document = subject.build_portfolio_correlation_admission_effective_budget_request_scope_source_resolver_preregistration_v1()

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
            self.document["scope_resolver_preregistration_hash"],
            subject.EXPECTED_SCOPE_RESOLVER_PREREGISTRATION_HASH,
        )

    def test_exact_adr0319_predecessor_is_pinned_and_unbound(self) -> None:
        predecessor = context_preregistration.build_portfolio_correlation_admission_effective_budget_trusted_internal_context_provider_preregistration_v1()
        self.assertEqual(
            self.document["predecessor_contract"], subject.PREDECESSOR_CONTRACT
        )
        self.assertEqual(
            predecessor["context_provider_preregistration_hash"],
            self.document["predecessor_contract"][
                "context_provider_preregistration_hash"
            ],
        )
        self.assertFalse(predecessor["binding_contract"]["registered"])

    def test_predecessor_source_files_match_pins(self) -> None:
        pins = self.document["predecessor_contract"]
        for prefix in (
            "context_preregistration_implementation",
            "context_preregistration_test",
            "context_preregistration_adr",
        ):
            path = ROOT / pins[f"{prefix}_path"]
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(actual, pins[f"{prefix}_sha256"], prefix)

    def test_request_scope_field_order_and_hash_are_exact(self) -> None:
        contract = self.document["request_scope_contract"]
        self.assertEqual(contract["field_order"], list(subject.REQUEST_SCOPE_FIELDS))
        self.assertEqual(len(contract["field_order"]), 11)
        self.assertEqual(
            strict_canonical_hash(contract["field_order"]),
            subject.REQUEST_SCOPE_FIELD_ORDER_HASH,
        )
        self.assertEqual(
            strict_canonical_hash(contract), subject.REQUEST_SCOPE_CONTRACT_HASH
        )

    def test_request_scope_evidence_is_hash_only_server_owned_and_unregistered(self) -> None:
        contract = self.document["request_scope_contract"]
        self.assertEqual(
            contract["evidence_owner"], "SERVER_TRANSPORT_SECURITY_LAYER_ONLY"
        )
        self.assertTrue(contract["hash_only_security_receipts"])
        self.assertTrue(contract["same_synchronous_request_scope_only"])
        self.assertEqual(contract["maximum_resolution_count"], 1)
        for field in (
            "raw_authentication_material_allowed",
            "raw_csrf_material_allowed",
            "raw_origin_material_allowed",
            "client_authored_allowed",
            "client_override_allowed",
            "registered",
        ):
            self.assertFalse(contract[field], field)
        self.assertIsNone(contract["request_scope_evidence_producer"])

    def test_source_resolver_contract_is_exact_explicit_and_side_effect_free(self) -> None:
        contract = self.document["source_resolver_contract"]
        self.assertEqual(
            strict_canonical_hash(contract), subject.SOURCE_RESOLVER_CONTRACT_HASH
        )
        self.assertEqual(
            contract["source_mode"],
            "EXPLICIT_ADR0311_INTERNAL_DOCUMENT_CHAIN_ONLY",
        )
        for field in (
            "runtime_reads_allowed",
            "database_reads_allowed",
            "cache_reads_allowed",
            "filesystem_reads_allowed",
            "network_reads_allowed",
            "client_source_documents_allowed",
            "client_provider_context_allowed",
            "registered",
        ):
            self.assertFalse(contract[field], field)
        self.assertIsNone(contract["resolver_implementation"])

    def test_source_resolver_requires_scope_generation_and_single_use(self) -> None:
        contract = self.document["source_resolver_contract"]
        self.assertTrue(contract["request_scope_hash_required"])
        self.assertTrue(contract["context_generation_id_required"])
        self.assertTrue(contract["single_use_guard_required"])
        self.assertEqual(
            contract["input_context_shape_hash"],
            context_preregistration.CONTEXT_SHAPE_HASH,
        )

    def test_cross_binding_contract_pins_all_three_boundaries(self) -> None:
        contract = self.document["cross_binding_contract"]
        self.assertEqual(
            strict_canonical_hash(contract), subject.CROSS_BINDING_CONTRACT_HASH
        )
        self.assertEqual(
            contract["request_scope_contract_hash"],
            subject.REQUEST_SCOPE_CONTRACT_HASH,
        )
        self.assertEqual(
            contract["source_resolver_contract_hash"],
            subject.SOURCE_RESOLVER_CONTRACT_HASH,
        )
        self.assertEqual(
            contract["context_provider_preregistration_hash"],
            context_preregistration.EXPECTED_CONTEXT_PROVIDER_PREREGISTRATION_HASH,
        )

    def test_cross_binding_requires_security_receipts_same_scope_and_unconsumed_state(self) -> None:
        contract = self.document["cross_binding_contract"]
        for field in (
            "same_request_scope_required",
            "same_context_generation_required",
            "authentication_receipt_required",
            "csrf_receipt_required",
            "origin_receipt_required",
            "unconsumed_scope_required",
        ):
            self.assertTrue(contract[field], field)
        self.assertFalse(contract["client_binding_override_allowed"])
        self.assertFalse(contract["registered"])
        self.assertIsNone(contract["binding_implementation"])

    def test_all_scope_resolver_controls_are_unregistered(self) -> None:
        controls = self.document["unregistered_controls"]
        self.assertEqual(len(controls), 8)
        for name, control in controls.items():
            if "registered" in control:
                self.assertFalse(control["registered"], name)
        self.assertFalse(controls["independent_binding_review"]["completed"])

    def test_facts_record_no_producer_resolver_context_handler_or_route(self) -> None:
        facts = self.document["facts"]
        for field in (
            "request_scope_evidence_producer_present",
            "security_receipt_providers_present",
            "source_resolver_implemented",
            "single_use_guard_present",
            "cross_binding_registered",
            "context_provider_implemented",
            "handler_bound",
            "route_registered",
            "externally_callable",
            "runtime_mutations_performed",
            "profitability_proven",
        ):
            self.assertFalse(facts[field], field)

    def test_all_expected_blockers_and_authority_locks_remain(self) -> None:
        self.assertEqual(
            self.document["blockers"], list(subject.SCOPE_RESOLVER_BLOCKERS)
        )
        self.assertEqual(len(self.document["blockers"]), 15)
        authority = self.document["authority"]
        self.assertTrue(authority["descriptive_only"])
        for key, value in authority.items():
            if key != "descriptive_only":
                self.assertFalse(value, key)

    def test_builder_accepts_no_runtime_or_policy_override(self) -> None:
        function = subject.build_portfolio_correlation_admission_effective_budget_request_scope_source_resolver_preregistration_v1
        self.assertEqual(list(inspect.signature(function).parameters), [])
        with self.assertRaises(TypeError):
            function(authentication_receipt="forged")

    def test_exact_rebuild_is_deterministic_and_verifiable(self) -> None:
        rebuilt = subject.build_portfolio_correlation_admission_effective_budget_request_scope_source_resolver_preregistration_v1()
        self.assertEqual(rebuilt, self.document)
        self.assertTrue(
            subject.verify_portfolio_correlation_admission_effective_budget_request_scope_source_resolver_preregistration_v1(
                self.document
            )
        )

    def test_scope_resolver_or_authority_promotion_is_rejected(self) -> None:
        mutations = (
            lambda value: value["request_scope_contract"].update(
                {"client_authored_allowed": True}
            ),
            lambda value: value["source_resolver_contract"].update(
                {"runtime_reads_allowed": True}
            ),
            lambda value: value["cross_binding_contract"].update(
                {"registered": True}
            ),
            lambda value: value["authority"].update(
                {"handler_binding_allowed": True}
            ),
            lambda value: value.update({"current": True}),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                tampered = deepcopy(self.document)
                mutate(tampered)
                self.assertFalse(
                    subject.verify_portfolio_correlation_admission_effective_budget_request_scope_source_resolver_preregistration_v1(
                        tampered
                    )
                )

    def test_single_snapshot_blocks_second_read_hash_swap(self) -> None:
        wrapped = SecondReadFlipMapping(
            self.document,
            "scope_resolver_preregistration_hash",
            "0" * 64,
        )
        self.assertTrue(
            subject.verify_portfolio_correlation_admission_effective_budget_request_scope_source_resolver_preregistration_v1(
                wrapped
            )
        )
        self.assertEqual(wrapped.reads, 1)

    def test_cyclic_and_nonmapping_inputs_fail_closed(self) -> None:
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        self.assertFalse(
            subject.verify_portfolio_correlation_admission_effective_budget_request_scope_source_resolver_preregistration_v1(
                cyclic
            )
        )
        self.assertFalse(
            subject.verify_portfolio_correlation_admission_effective_budget_request_scope_source_resolver_preregistration_v1(
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
            subject.build_portfolio_correlation_admission_effective_budget_request_scope_source_resolver_preregistration_v1,
            subject.verify_portfolio_correlation_admission_effective_budget_request_scope_source_resolver_preregistration_v1,
        ):
            parameters = set(inspect.signature(function).parameters)
            self.assertTrue(
                parameters.isdisjoint(
                    {
                        "server",
                        "handler",
                        "route",
                        "runtime",
                        "database",
                        "cache",
                        "private_key",
                        "authentication_token",
                    }
                )
            )
