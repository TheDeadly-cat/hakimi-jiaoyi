from __future__ import annotations

from collections.abc import Iterator, Mapping
from copy import deepcopy
from hashlib import sha256
import inspect
from pathlib import Path
import re
import unittest

from exchange_terminal.interfaces.http import (
    strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_candidate_v9
    as candidate_v9,
)
from exchange_terminal.services import (
    strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_mount_preregistration_v1
    as mount_preregistration,
)
from exchange_terminal.services import (
    strategy_correlation_matrix_geometry_budget_multi_window_presentation_trusted_internal_provider_preregistration_v1
    as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    strict_canonical_hash,
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


class GeometryBudgetMultiWindowTrustedProviderPreregistrationV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.document = subject.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_trusted_internal_provider_preregistration_v1()

    def test_schema_state_and_hash_are_exact(self) -> None:
        self.assertEqual(self.document["schema_version"], subject.SCHEMA_VERSION)
        self.assertEqual(
            self.document["static_fingerprint"], subject.STATIC_FINGERPRINT
        )
        self.assertEqual(
            self.document["preregistration_id"], subject.PREREGISTRATION_ID
        )
        self.assertEqual(self.document["status"], "BLOCKED")
        self.assertEqual(len(self.document["provider_preregistration_hash"]), 64)

    def test_exact_adr0336_predecessor_is_pinned_and_unmounted(self) -> None:
        predecessor = mount_preregistration.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_mount_preregistration_v1()
        self.assertTrue(
            mount_preregistration.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_mount_preregistration_v1(
                predecessor
            )
        )
        self.assertEqual(
            self.document["predecessor_contract"], subject.PREDECESSOR_CONTRACT
        )
        self.assertEqual(
            self.document["predecessor_contract"]["mount_preregistration_hash"],
            predecessor["preregistration_hash"],
        )
        self.assertFalse(predecessor["proposed_transport"]["registered"])
        self.assertIsNone(predecessor["proposed_transport"]["handler"])
        self.assertIsNone(predecessor["proposed_transport"]["endpoint"])

    def test_predecessor_source_files_match_pins(self) -> None:
        pins = self.document["predecessor_contract"]
        for prefix in ("mount_implementation", "mount_test", "mount_adr"):
            path = ROOT / pins[f"{prefix}_path"]
            self.assertEqual(
                sha256(path.read_bytes()).hexdigest(),
                pins[f"{prefix}_sha256"],
                prefix,
            )

    def test_candidate_contract_is_bound_to_predecessor(self) -> None:
        pins = self.document["predecessor_contract"]
        self.assertEqual(pins["candidate_contract_hash"], candidate_v9.CONTRACT_HASH)
        self.assertEqual(
            pins["candidate_request_schema_version"],
            candidate_v9.REQUEST_SCHEMA_VERSION,
        )
        self.assertEqual(
            pins["candidate_response_schema_version"],
            candidate_v9.RESPONSE_SCHEMA_VERSION,
        )
        self.assertEqual(
            pins["proposed_route"], mount_preregistration.PROPOSED_ROUTE
        )

    def test_request_role_order_and_hash_are_exact(self) -> None:
        shape = self.document["provider_output_shape"]
        self.assertEqual(shape["request_roles"], list(subject.REQUEST_ROLES))
        self.assertEqual(len(shape["request_roles"]), 3)
        self.assertEqual(
            strict_canonical_hash(shape["request_roles"]),
            subject.REQUEST_ROLE_HASH,
        )

    def test_verification_context_role_order_and_hash_are_exact(self) -> None:
        shape = self.document["provider_output_shape"]
        self.assertEqual(
            shape["verification_context_roles"],
            list(subject.VERIFICATION_CONTEXT_ROLES),
        )
        self.assertEqual(len(shape["verification_context_roles"]), 7)
        self.assertEqual(
            strict_canonical_hash(shape["verification_context_roles"]),
            subject.VERIFICATION_CONTEXT_ROLE_HASH,
        )

    def test_provider_output_shape_hash_and_ownership_are_exact(self) -> None:
        shape = self.document["provider_output_shape"]
        self.assertEqual(
            strict_canonical_hash(shape), subject.PROVIDER_OUTPUT_SHAPE_HASH
        )
        self.assertEqual(shape["owner"], "TRUSTED_INTERNAL_REQUEST_SCOPE_ONLY")
        self.assertEqual(
            shape["input_source"], "INTERNAL_ADR0334_EXACT_SOURCE_CHAIN_ONLY"
        )
        self.assertFalse(shape["candidate_document_client_supplied_allowed"])
        self.assertFalse(shape["verification_context_client_supplied_allowed"])
        self.assertFalse(shape["response_embedding_allowed"])

    def test_lifecycle_is_request_local_single_use_and_clockless(self) -> None:
        lifecycle = self.document["lifecycle_contract"]
        self.assertEqual(
            lifecycle["freshness_mode"], "SAME_SYNCHRONOUS_REQUEST_SCOPE_ONLY"
        )
        self.assertFalse(lifecycle["clock_or_timestamp_required"])
        self.assertEqual(lifecycle["maximum_resolution_count"], 1)
        self.assertTrue(lifecycle["single_use_required"])
        self.assertTrue(lifecycle["discard_after_candidate_response"])
        for field in (
            "reuse_across_requests_allowed",
            "persistence_allowed",
            "runtime_allowed",
            "database_allowed",
            "cache_allowed",
            "filesystem_allowed",
            "network_allowed",
        ):
            self.assertFalse(lifecycle[field], field)

    def test_client_cannot_supply_provider_or_context_fields(self) -> None:
        ownership = self.document["ownership_contract"]
        self.assertEqual(ownership["client_request_fields_allowed"], [])
        self.assertEqual(ownership["client_context_fields_allowed"], [])
        self.assertFalse(ownership["client_override_allowed"])
        self.assertFalse(ownership["client_context_hash_allowed"])
        self.assertFalse(ownership["client_freshness_evidence_allowed"])

    def test_binding_contract_is_exact_and_fully_unbound(self) -> None:
        binding = self.document["binding_contract"]
        self.assertEqual(binding["candidate_contract_hash"], candidate_v9.CONTRACT_HASH)
        self.assertEqual(
            binding["mount_preregistration_hash"],
            subject.PREDECESSOR_CONTRACT["mount_preregistration_hash"],
        )
        self.assertFalse(binding["registered"])
        for field in (
            "provider_implementation",
            "authenticated_request_scope_provider",
            "trusted_source_resolver",
            "context_generation_id_provider",
            "single_use_guard",
            "handler_binding",
            "route_binding",
        ):
            self.assertIsNone(binding[field], field)

    def test_redaction_forbids_request_source_context_position_and_symbol_logs(
        self,
    ) -> None:
        redaction = self.document["redaction_contract"]
        for field in (
            "request_body_logging_allowed",
            "provider_output_logging_allowed",
            "candidate_document_logging_allowed",
            "verification_context_logging_allowed",
            "position_logging_allowed",
            "symbol_logging_allowed",
            "provider_hash_response_embedding_allowed",
            "source_hash_response_embedding_allowed",
        ):
            self.assertFalse(redaction[field], field)
        self.assertTrue(redaction["candidate_response_only"])

    def test_all_provider_controls_are_unregistered(self) -> None:
        controls = self.document["unregistered_controls"]
        self.assertEqual(len(controls), 7)
        for name, control in controls.items():
            if "registered" in control:
                self.assertFalse(control["registered"], name)
        self.assertFalse(controls["independent_provider_review"]["completed"])

    def test_facts_record_no_implementation_handler_route_or_runtime_action(
        self,
    ) -> None:
        facts = self.document["facts"]
        self.assertTrue(facts["provider_output_shape_preregistered"])
        self.assertTrue(facts["provider_role_order_pinned"])
        self.assertTrue(facts["client_override_forbidden"])
        for field in (
            "provider_implemented",
            "request_scope_provider_present",
            "source_resolver_present",
            "single_use_guard_present",
            "redaction_policy_present",
            "handler_bound",
            "route_registered",
            "externally_callable",
            "runtime_assets_accessed",
            "runtime_mutations_performed",
            "profitability_proven",
        ):
            self.assertFalse(facts[field], field)

    def test_all_expected_blockers_and_authority_locks_remain(self) -> None:
        self.assertEqual(self.document["blockers"], list(subject.PROVIDER_BLOCKERS))
        self.assertEqual(len(self.document["blockers"]), 13)
        authority = self.document["authority"]
        self.assertTrue(authority["descriptive_only"])
        for key, value in authority.items():
            if key != "descriptive_only":
                self.assertFalse(value, key)

    def test_builder_accepts_no_runtime_or_policy_override(self) -> None:
        function = subject.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_trusted_internal_provider_preregistration_v1
        self.assertEqual(list(inspect.signature(function).parameters), [])
        with self.assertRaises(TypeError):
            function(provider="forged")

    def test_exact_rebuild_is_deterministic_and_verifiable(self) -> None:
        rebuilt = subject.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_trusted_internal_provider_preregistration_v1()
        self.assertEqual(rebuilt, self.document)
        self.assertTrue(
            subject.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_trusted_internal_provider_preregistration_v1(
                self.document
            )
        )

    def test_output_lifecycle_binding_or_authority_promotion_is_rejected(
        self,
    ) -> None:
        mutations = (
            lambda value: value["provider_output_shape"].update(
                {"candidate_document_client_supplied_allowed": True}
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
                    subject.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_trusted_internal_provider_preregistration_v1(
                        tampered
                    )
                )

    def test_single_snapshot_blocks_second_read_hash_swap(self) -> None:
        wrapped = SecondReadFlipMapping(
            self.document,
            "provider_preregistration_hash",
            "0" * 64,
        )
        self.assertTrue(
            subject.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_trusted_internal_provider_preregistration_v1(
                wrapped
            )
        )
        self.assertEqual(wrapped.reads, 1)

    def test_cyclic_and_nonmapping_inputs_fail_closed(self) -> None:
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        self.assertFalse(
            subject.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_trusted_internal_provider_preregistration_v1(
                cyclic
            )
        )
        self.assertFalse(
            subject.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_trusted_internal_provider_preregistration_v1(
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
            re.search(
                r"\bREADY\b|\bprofit\b|\breturn\b|\balpha\b|win rate",
                " ".join(values),
                re.IGNORECASE,
            )
        )

    def test_public_api_has_no_host_runtime_database_cache_or_secret_parameter(
        self,
    ) -> None:
        for function in (
            subject.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_trusted_internal_provider_preregistration_v1,
            subject.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_trusted_internal_provider_preregistration_v1,
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


if __name__ == "__main__":
    unittest.main()
