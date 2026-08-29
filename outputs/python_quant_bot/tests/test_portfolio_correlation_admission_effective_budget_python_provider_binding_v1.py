from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterator, Mapping
from copy import deepcopy
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

from exchange_terminal.services import portfolio_correlation_admission_effective_budget_python_provider_binding_v1 as subject
from exchange_terminal.services.portfolio_correlation_admission_effective_budget_consumer_static_asset_registration_v2 import (
    build_portfolio_correlation_admission_effective_budget_consumer_static_asset_registration_v2,
)
from exchange_terminal.services.portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1 import (
    build_portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1,
    verify_portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1,
)
from exchange_terminal.services.portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1 import (
    build_portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import strict_canonical_hash
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


class PythonProviderBindingV1Tests(TestCase):
    def setUp(self) -> None:
        self.binding = (
            subject.build_portfolio_correlation_admission_effective_budget_python_provider_binding_v1()
        )

    def _known_call(self) -> tuple[tuple[object, ...], dict[str, object]]:
        case = source_consumer_tests.HashEnvelopeSourceConsumerV1Tests(
            methodName="runTest"
        )
        case.setUp()
        fixture = case.fixture
        evidence = fixture.evidence
        args = (
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
        )
        kwargs = {
            "strategy_id": evidence["strategy_id"],
            "variant_id": evidence["variant_id"],
            "lane": evidence["lane"],
            **fixture.inputs,
        }
        return args, kwargs

    def test_binding_has_exact_schema_state_and_hash(self) -> None:
        self.assertEqual(self.binding["schema_version"], subject.SCHEMA_VERSION)
        self.assertEqual(
            self.binding["static_fingerprint"], subject.STATIC_FINGERPRINT
        )
        self.assertEqual(self.binding["binding_id"], subject.BINDING_ID)
        self.assertEqual(self.binding["status"], "BLOCKED")
        self.assertEqual(
            self.binding["binding_state"],
            "PYTHON_PROVIDER_BOUND_INTERNAL_ONLY_HTTP_APP_HOST_CURRENT_UNBOUND",
        )
        self.assertEqual(
            self.binding["provider_binding_hash"],
            subject.EXPECTED_PROVIDER_BINDING_HASH,
        )

    def test_exact_predecessors_are_pinned(self) -> None:
        host = (
            build_portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1()
        )
        assets = (
            build_portfolio_correlation_admission_effective_budget_consumer_static_asset_registration_v2()
        )
        predecessor = self.binding["predecessor_contract"]
        self.assertEqual(
            predecessor["host_binding_preregistration_hash"],
            host["host_binding_preregistration_hash"],
        )
        self.assertEqual(
            predecessor["consumer_static_asset_registration_hash"],
            assets["registration_hash"],
        )
        self.assertEqual(predecessor, subject.PREDECESSOR_CONTRACT)

    def test_host_candidate_is_upgraded_without_mutating_adr0314(self) -> None:
        host = (
            build_portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1()
        )
        candidate = host["binding_candidates"]["python_provider"]
        self.assertFalse(candidate["bound"])
        self.assertIsNone(candidate["provider_registration"])
        self.assertIsNone(host["active_host_plan"]["python_provider"])
        self.assertEqual(
            strict_canonical_hash(candidate),
            subject.HOST_PYTHON_PROVIDER_CANDIDATE_HASH,
        )
        self.assertTrue(self.binding["provider_contract"]["bound"])

    def test_callable_identity_and_registry_hashes_are_exact(self) -> None:
        self.assertEqual(
            strict_canonical_hash(self.binding["callable_identity"]),
            subject.CALLABLE_IDENTITY_HASH,
        )
        self.assertEqual(
            strict_canonical_hash(self.binding["registry"]), subject.REGISTRY_HASH
        )
        identity = self.binding["callable_identity"]
        self.assertEqual(identity["module_sha256"], subject.PROVIDER_MODULE_SHA256)
        self.assertEqual(identity["callable"], subject.PROVIDER_CALLABLE_NAME)

    def test_registry_has_one_nondefault_entry(self) -> None:
        registry = self.binding["registry"]
        self.assertEqual(registry["registry_id"], subject.PROVIDER_REGISTRY_ID)
        self.assertEqual(len(registry["entries"]), 1)
        self.assertEqual(registry["entries"][0]["provider_key"], subject.PROVIDER_KEY)
        self.assertIsNone(registry["default_provider_key"])
        self.assertFalse(self.binding["provider_contract"]["implicit_default_allowed"])

    def test_only_internal_provider_slot_is_bound(self) -> None:
        host_plan = self.binding["host_plan"]
        self.assertEqual(host_plan["python_provider_registry_entry"], subject.PROVIDER_KEY)
        for key, value in host_plan.items():
            if key != "python_provider_registry_entry":
                self.assertIsNone(value, key)

    def test_build_records_no_provider_resolution_or_invocation(self) -> None:
        facts = self.binding["facts"]
        self.assertTrue(facts["python_provider_bound_in_memory"])
        self.assertFalse(facts["provider_resolved_by_binding_build"])
        self.assertFalse(facts["provider_invoked_by_binding_build"])
        self.assertFalse(facts["http_projection_bound"])
        self.assertFalse(facts["runtime_mutations_performed"])
        self.assertFalse(facts["profitability_proven"])

    def test_authority_is_limited_to_explicit_synthetic_resolution(self) -> None:
        authority = self.binding["authority"]
        allowed = {key for key, value in authority.items() if value}
        self.assertEqual(
            allowed,
            {
                "in_memory_provider_resolution_allowed",
                "synthetic_research_invocation_allowed",
            },
        )
        self.assertFalse(authority["external_request_invocation_allowed"])
        self.assertFalse(authority["paper_authorized"])
        self.assertFalse(authority["live_order_allowed"])

    def test_binding_build_does_not_call_provider(self) -> None:
        exploding = Mock(side_effect=AssertionError("provider must not run"))
        with patch.object(subject, "_PROVIDER_CALLABLE", exploding):
            rebuilt = (
                subject.build_portfolio_correlation_admission_effective_budget_python_provider_binding_v1()
            )
        exploding.assert_not_called()
        self.assertEqual(rebuilt, self.binding)

    def test_exact_binding_resolves_the_exact_adr0311_callable(self) -> None:
        resolved = (
            subject.resolve_portfolio_correlation_admission_effective_budget_python_provider_v1(
                self.binding
            )
        )
        self.assertIs(
            resolved,
            build_portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1,
        )

    def test_resolved_provider_executes_exact_known_synthetic_chain(self) -> None:
        provider = (
            subject.resolve_portfolio_correlation_admission_effective_budget_python_provider_v1(
                self.binding
            )
        )
        self.assertIsNotNone(provider)
        args, kwargs = self._known_call()
        result = provider(*args, **kwargs)
        self.assertEqual(result["status"], "KNOWN")
        self.assertEqual(
            result["consumer_result_hash"],
            "4271f49558382127bb0e1e737ca080686c305907e60e0b5514aded14a98e7b96",
        )
        self.assertTrue(
            verify_portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1(
                result, *args, **kwargs
            )
        )

    def test_binding_and_provider_call_are_deterministic(self) -> None:
        self.assertEqual(
            self.binding,
            subject.build_portfolio_correlation_admission_effective_budget_python_provider_binding_v1(),
        )
        provider = (
            subject.resolve_portfolio_correlation_admission_effective_budget_python_provider_v1(
                self.binding
            )
        )
        args, kwargs = self._known_call()
        self.assertEqual(provider(*args, **kwargs), provider(*args, **kwargs))

    def test_exact_verifier_accepts_rebuild(self) -> None:
        self.assertTrue(
            subject.verify_portfolio_correlation_admission_effective_budget_python_provider_binding_v1(
                self.binding
            )
        )

    def test_predecessor_source_bytes_match_pins(self) -> None:
        for key, expected_hash in subject.PREDECESSOR_CONTRACT.items():
            if not key.endswith("_path"):
                continue
            hash_key = key[:-5] + "_sha256"
            actual_hash = hashlib.sha256((ROOT / expected_hash).read_bytes()).hexdigest()
            self.assertEqual(actual_hash, subject.PREDECESSOR_CONTRACT[hash_key], key)
        actual_provider_hash = hashlib.sha256(
            (ROOT / subject.PROVIDER_MODULE_PATH).read_bytes()
        ).hexdigest()
        self.assertEqual(actual_provider_hash, subject.PROVIDER_MODULE_SHA256)

    def test_registration_contains_no_raw_source_documents_or_promotional_copy(self) -> None:
        serialized = json.dumps(self.binding, sort_keys=True)
        for forbidden_key in (
            '"report_document"',
            '"correlation_matrix_document"',
            '"positions"',
            '"presentation_payload"',
        ):
            self.assertNotIn(forbidden_key, serialized)
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

        collect(self.binding)
        self.assertIsNone(
            re.search(r"\bREADY\b|\bprofit\b|\breturn\b|\balpha\b|win rate", " ".join(values), re.IGNORECASE)
        )

    def test_tampered_binding_does_not_resolve(self) -> None:
        tampered = deepcopy(self.binding)
        tampered["callable_identity"]["module_sha256"] = "0" * 64
        self.assertFalse(
            subject.verify_portfolio_correlation_admission_effective_budget_python_provider_binding_v1(
                tampered
            )
        )
        self.assertIsNone(
            subject.resolve_portfolio_correlation_admission_effective_budget_python_provider_v1(
                tampered
            )
        )

    def test_registry_default_promotion_does_not_resolve(self) -> None:
        tampered = deepcopy(self.binding)
        tampered["registry"]["default_provider_key"] = subject.PROVIDER_KEY
        self.assertIsNone(
            subject.resolve_portfolio_correlation_admission_effective_budget_python_provider_v1(
                tampered
            )
        )

    def test_host_promotion_does_not_resolve(self) -> None:
        tampered = deepcopy(self.binding)
        tampered["host_plan"]["http_handler"] = "injected_handler"
        self.assertIsNone(
            subject.resolve_portfolio_correlation_admission_effective_budget_python_provider_v1(
                tampered
            )
        )

    def test_authority_promotion_does_not_resolve(self) -> None:
        tampered = deepcopy(self.binding)
        tampered["authority"]["external_request_invocation_allowed"] = True
        self.assertIsNone(
            subject.resolve_portfolio_correlation_admission_effective_budget_python_provider_v1(
                tampered
            )
        )

    def test_extra_field_does_not_resolve(self) -> None:
        tampered = deepcopy(self.binding)
        tampered["current"] = True
        self.assertIsNone(
            subject.resolve_portfolio_correlation_admission_effective_budget_python_provider_v1(
                tampered
            )
        )

    def test_callable_identity_drift_does_not_resolve(self) -> None:
        replacement = lambda: None
        with patch.object(subject, "_PROVIDER_CALLABLE", replacement):
            self.assertIsNone(
                subject.resolve_portfolio_correlation_admission_effective_budget_python_provider_v1(
                    self.binding
                )
            )

    def test_single_snapshot_blocks_second_read_hash_swap(self) -> None:
        wrapped = SecondReadFlipMapping(
            self.binding,
            "provider_binding_hash",
            "0" * 64,
        )
        resolved = (
            subject.resolve_portfolio_correlation_admission_effective_budget_python_provider_v1(
                wrapped
            )
        )
        self.assertIs(
            resolved,
            build_portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1,
        )
        self.assertEqual(wrapped.reads, 1)

    def test_cyclic_and_nonmapping_inputs_fail_closed(self) -> None:
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        self.assertFalse(
            subject.verify_portfolio_correlation_admission_effective_budget_python_provider_binding_v1(
                cyclic
            )
        )
        self.assertIsNone(
            subject.resolve_portfolio_correlation_admission_effective_budget_python_provider_v1(
                cyclic
            )
        )
        self.assertFalse(
            subject.verify_portfolio_correlation_admission_effective_budget_python_provider_binding_v1(
                None
            )
        )
        self.assertIsNone(
            subject.resolve_portfolio_correlation_admission_effective_budget_python_provider_v1(
                None
            )
        )
