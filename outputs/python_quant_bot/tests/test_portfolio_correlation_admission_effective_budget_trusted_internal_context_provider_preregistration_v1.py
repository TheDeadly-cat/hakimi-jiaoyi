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
    portfolio_correlation_admission_effective_budget_readonly_http_projection_mount_preregistration_v1 as mount_preregistration,
)
from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_trusted_internal_context_provider_preregistration_v1 as subject,
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


class TrustedInternalContextProviderPreregistrationV1Tests(TestCase):
    def setUp(self) -> None:
        self.document = subject.build_portfolio_correlation_admission_effective_budget_trusted_internal_context_provider_preregistration_v1()

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
            self.document["context_provider_preregistration_hash"],
            subject.EXPECTED_CONTEXT_PROVIDER_PREREGISTRATION_HASH,
        )

    def test_exact_adr0318_predecessor_is_pinned_and_unmounted(self) -> None:
        predecessor = mount_preregistration.build_portfolio_correlation_admission_effective_budget_readonly_http_projection_mount_preregistration_v1()
        self.assertEqual(
            self.document["predecessor_contract"], subject.PREDECESSOR_CONTRACT
        )
        self.assertEqual(
            self.document["predecessor_contract"]["mount_preregistration_hash"],
            predecessor["mount_preregistration_hash"],
        )
        self.assertFalse(predecessor["proposed_transport"]["registered"])
        self.assertIsNone(predecessor["proposed_transport"]["handler"])
        self.assertIsNone(predecessor["proposed_transport"]["endpoint"])

    def test_predecessor_source_files_match_pins(self) -> None:
        pins = self.document["predecessor_contract"]
        for prefix in ("mount_implementation", "mount_test", "mount_adr"):
            path = ROOT / pins[f"{prefix}_path"]
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(actual, pins[f"{prefix}_sha256"], prefix)

    def test_positional_role_order_and_hash_are_exact(self) -> None:
        shape = self.document["context_shape"]
        self.assertEqual(shape["positional_roles"], list(subject.POSITIONAL_ROLES))
        self.assertEqual(len(shape["positional_roles"]), 13)
        self.assertEqual(
            strict_canonical_hash(shape["positional_roles"]),
            subject.POSITIONAL_ROLE_HASH,
        )

    def test_keyword_role_order_and_hash_are_exact(self) -> None:
        shape = self.document["context_shape"]
        self.assertEqual(shape["keyword_roles"], list(subject.KEYWORD_ROLES))
        self.assertEqual(len(shape["keyword_roles"]), 10)
        self.assertEqual(
            strict_canonical_hash(shape["keyword_roles"]),
            subject.KEYWORD_ROLE_HASH,
        )

    def test_context_shape_hash_and_ownership_are_exact(self) -> None:
        shape = self.document["context_shape"]
        self.assertEqual(strict_canonical_hash(shape), subject.CONTEXT_SHAPE_HASH)
        self.assertEqual(shape["owner"], "TRUSTED_INTERNAL_REQUEST_SCOPE_ONLY")
        self.assertEqual(
            shape["input_source"], "INTERNAL_ADR0311_EXACT_SOURCE_CHAIN_ONLY"
        )
        self.assertTrue(shape["source_documents_present_in_internal_context"])
        self.assertFalse(shape["source_documents_client_supplied_allowed"])
        self.assertFalse(shape["provider_context_client_supplied_allowed"])
        self.assertFalse(shape["response_embedding_allowed"])

    def test_lifecycle_is_request_local_single_use_and_clockless(self) -> None:
        lifecycle = self.document["lifecycle_contract"]
        self.assertEqual(
            lifecycle["freshness_mode"], "SAME_SYNCHRONOUS_REQUEST_SCOPE_ONLY"
        )
        self.assertFalse(lifecycle["clock_or_timestamp_required"])
        self.assertEqual(lifecycle["maximum_resolution_count"], 1)
        self.assertTrue(lifecycle["single_use_required"])
        self.assertTrue(lifecycle["discard_after_projection"])
        for field in (
            "reuse_across_requests_allowed",
            "persistence_allowed",
            "database_allowed",
            "cache_allowed",
            "filesystem_allowed",
            "network_allowed",
        ):
            self.assertFalse(lifecycle[field], field)

    def test_client_can_supply_only_fixed_projection_request_fields(self) -> None:
        ownership = self.document["ownership_contract"]
        self.assertEqual(
            ownership["client_request_fields_allowed"],
            ["schema_version", "projection_id"],
        )
        self.assertEqual(ownership["client_context_fields_allowed"], [])
        self.assertFalse(ownership["client_override_allowed"])
        self.assertFalse(ownership["client_context_hash_allowed"])
        self.assertFalse(ownership["client_freshness_evidence_allowed"])

    def test_binding_contract_is_exact_and_fully_unbound(self) -> None:
        binding = self.document["binding_contract"]
        self.assertEqual(binding["projection_id"], projection_candidate.PROJECTION_ID)
        self.assertEqual(
            binding["provider_binding_hash"],
            provider_binding.EXPECTED_PROVIDER_BINDING_HASH,
        )
        self.assertEqual(
            binding["mount_preregistration_hash"],
            mount_preregistration.EXPECTED_MOUNT_PREREGISTRATION_HASH,
        )
        self.assertFalse(binding["registered"])
        for field in (
            "context_provider_implementation",
            "request_scope_provider",
            "single_use_guard",
            "handler_binding",
            "route_binding",
        ):
            self.assertIsNone(binding[field], field)

    def test_redaction_forbids_context_source_position_and_symbol_logging(self) -> None:
        redaction = self.document["redaction_contract"]
        for field in (
            "request_body_logging_allowed",
            "context_logging_allowed",
            "source_document_logging_allowed",
            "position_logging_allowed",
            "symbol_logging_allowed",
            "context_hash_response_embedding_allowed",
        ):
            self.assertFalse(redaction[field], field)
        self.assertTrue(redaction["projection_response_only"])

    def test_all_context_controls_are_unregistered(self) -> None:
        controls = self.document["unregistered_controls"]
        self.assertEqual(len(controls), 7)
        for name, control in controls.items():
            if "registered" in control:
                self.assertFalse(control["registered"], name)
        self.assertFalse(controls["independent_context_review"]["completed"])

    def test_facts_record_no_implementation_handler_route_or_runtime_action(self) -> None:
        facts = self.document["facts"]
        self.assertTrue(facts["context_shape_preregistered"])
        self.assertTrue(facts["context_role_order_pinned"])
        self.assertTrue(facts["client_override_forbidden"])
        for field in (
            "context_provider_implemented",
            "request_scope_provider_present",
            "source_chain_resolver_present",
            "single_use_guard_present",
            "redaction_policy_present",
            "handler_bound",
            "route_registered",
            "externally_callable",
            "runtime_mutations_performed",
            "profitability_proven",
        ):
            self.assertFalse(facts[field], field)

    def test_all_expected_blockers_and_authority_locks_remain(self) -> None:
        self.assertEqual(self.document["blockers"], list(subject.CONTEXT_BLOCKERS))
        self.assertEqual(len(self.document["blockers"]), 13)
        authority = self.document["authority"]
        self.assertTrue(authority["descriptive_only"])
        for key, value in authority.items():
            if key != "descriptive_only":
                self.assertFalse(value, key)

    def test_builder_accepts_no_runtime_or_policy_override(self) -> None:
        function = subject.build_portfolio_correlation_admission_effective_budget_trusted_internal_context_provider_preregistration_v1
        self.assertEqual(list(inspect.signature(function).parameters), [])
        with self.assertRaises(TypeError):
            function(context_provider="forged")

    def test_exact_rebuild_is_deterministic_and_verifiable(self) -> None:
        rebuilt = subject.build_portfolio_correlation_admission_effective_budget_trusted_internal_context_provider_preregistration_v1()
        self.assertEqual(rebuilt, self.document)
        self.assertTrue(
            subject.verify_portfolio_correlation_admission_effective_budget_trusted_internal_context_provider_preregistration_v1(
                self.document
            )
        )

    def test_context_binding_lifecycle_or_authority_promotion_is_rejected(self) -> None:
        mutations = (
            lambda value: value["context_shape"].update(
                {"provider_context_client_supplied_allowed": True}
            ),
            lambda value: value["lifecycle_contract"].update(
                {"maximum_resolution_count": 2}
            ),
            lambda value: value["binding_contract"].update({"registered": True}),
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
                    subject.verify_portfolio_correlation_admission_effective_budget_trusted_internal_context_provider_preregistration_v1(
                        tampered
                    )
                )

    def test_single_snapshot_blocks_second_read_hash_swap(self) -> None:
        wrapped = SecondReadFlipMapping(
            self.document,
            "context_provider_preregistration_hash",
            "0" * 64,
        )
        self.assertTrue(
            subject.verify_portfolio_correlation_admission_effective_budget_trusted_internal_context_provider_preregistration_v1(
                wrapped
            )
        )
        self.assertEqual(wrapped.reads, 1)

    def test_cyclic_and_nonmapping_inputs_fail_closed(self) -> None:
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        self.assertFalse(
            subject.verify_portfolio_correlation_admission_effective_budget_trusted_internal_context_provider_preregistration_v1(
                cyclic
            )
        )
        self.assertFalse(
            subject.verify_portfolio_correlation_admission_effective_budget_trusted_internal_context_provider_preregistration_v1(
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
            subject.build_portfolio_correlation_admission_effective_budget_trusted_internal_context_provider_preregistration_v1,
            subject.verify_portfolio_correlation_admission_effective_budget_trusted_internal_context_provider_preregistration_v1,
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
