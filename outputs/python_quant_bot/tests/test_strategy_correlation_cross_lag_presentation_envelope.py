from __future__ import annotations

import ast
from copy import deepcopy
import inspect
from pathlib import Path
import random
import socket
import sqlite3
import time
import unittest
from unittest.mock import patch
import uuid

import exchange_terminal.application.strategy_correlation_cross_lag_presentation_envelope as adapter
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strategy_correlation_cross_lag_public_projection import (
    build_strategy_correlation_cross_lag_public_summary,
)
from tests.test_strategy_correlation_cross_lag_public_projection import (
    StrategyCorrelationCrossLagPublicProjectionTests,
)


class StrategyCorrelationCrossLagPresentationEnvelopeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = StrategyCorrelationCrossLagPublicProjectionTests(
            methodName="test_valid_pass_maps_to_four_neutral_axes"
        )
        self.fixture.setUp()

    def tearDown(self) -> None:
        self.fixture.tearDown()

    def _values(self) -> dict:
        return self.fixture._values()

    def _build(self, **overrides):
        values = self._values()
        values.update(overrides)
        return (
            adapter.build_strategy_correlation_cross_lag_presentation_envelope(
                **values
            ),
            values,
        )

    def _verify(self, document, values) -> bool:
        return adapter.verify_strategy_correlation_cross_lag_presentation_envelope(
            document,
            **values,
        )

    def test_versioned_constants_are_exact(self) -> None:
        self.assertEqual(
            adapter.ENVELOPE_SCHEMA_VERSION,
            "strategy-correlation-cross-lag-presentation-envelope-v1",
        )
        self.assertEqual(
            adapter.ADAPTER_STATIC_FINGERPRINT,
            "20260821-cross-lag-c5-presentation-envelope-adapter-1",
        )

    def test_public_signatures_explicitly_mirror_all_c3_inputs(self) -> None:
        c3 = inspect.signature(build_strategy_correlation_cross_lag_public_summary)
        build = inspect.signature(
            adapter.build_strategy_correlation_cross_lag_presentation_envelope
        )
        verify = inspect.signature(
            adapter.verify_strategy_correlation_cross_lag_presentation_envelope
        )
        self.assertEqual(tuple(build.parameters), tuple(c3.parameters))
        self.assertEqual(tuple(verify.parameters), ("document", *c3.parameters))
        self.assertEqual(len(tuple(c3.parameters)[1:]), 26)
        self.assertNotIn(
            inspect.Parameter.VAR_KEYWORD,
            {parameter.kind for parameter in build.parameters.values()},
        )
        self.assertNotIn(
            inspect.Parameter.VAR_KEYWORD,
            {parameter.kind for parameter in verify.parameters.values()},
        )

    def test_valid_pass_builds_exact_three_field_envelope(self) -> None:
        document, _values = self._build()
        self.assertEqual(
            set(document), {"schema_version", "summary", "verification"}
        )
        self.assertEqual(document["summary"]["public_state"], "OBSERVED_PASS")
        self.assertIs(document["verification"]["valid"], True)
        self.assertEqual(
            document["verification"]["supplied_public_summary_hash"],
            document["summary"]["public_summary_hash"],
        )
        self.assertEqual(
            document["verification"]["rebuilt_public_summary_hash"],
            document["summary"]["public_summary_hash"],
        )

    def test_valid_block_remains_visible_and_nonzero(self) -> None:
        block_context = self.fixture._block_context(99173)
        document, _values = self._build(**block_context)
        self.assertEqual(document["summary"]["public_state"], "OBSERVED_BLOCK")
        self.assertGreater(document["summary"]["dependent_test_count"], 0)
        self.assertEqual(
            document["summary"]["blockers"][0], "CROSS_LAG_DEPENDENCE_DETECTED"
        )

    def test_not_supplied_and_invalid_remain_distinct(self) -> None:
        missing, _missing_values = self._build(binding_assessment=None)
        invalid, _invalid_values = self._build(
            binding_assessment={"schema_version": "invalid"}
        )
        self.assertEqual(missing["summary"]["public_state"], "NOT_SUPPLIED")
        self.assertEqual(invalid["summary"]["public_state"], "UNKNOWN")

    def test_all_four_states_exactly_verify(self) -> None:
        contexts = (
            {},
            self.fixture._block_context(99173),
            {"binding_assessment": None},
            {"binding_assessment": {"schema_version": "invalid"}},
        )
        states = []
        for overrides in contexts:
            with self.subTest(overrides=tuple(sorted(overrides))):
                document, values = self._build(**overrides)
                self.assertTrue(self._verify(document, values))
                states.append(document["summary"]["public_state"])
        self.assertEqual(
            set(states), {"NOT_SUPPLIED", "UNKNOWN", "OBSERVED_PASS", "OBSERVED_BLOCK"}
        )

    def test_valid_envelope_rejects_another_context(self) -> None:
        document, values = self._build()
        other_values = dict(values)
        other_values.update(self.fixture._block_context(44017))
        self.assertFalse(self._verify(document, other_values))

    def test_validity_aliases_fail_closed(self) -> None:
        document, values = self._build()
        for alias in (1, "true", {}, []):
            with self.subTest(alias=alias):
                tampered = deepcopy(document)
                tampered["verification"]["valid"] = alias
                self.assertFalse(self._verify(tampered, values))

    def test_verification_hash_tamper_fails_closed(self) -> None:
        document, values = self._build()
        for key in (
            "supplied_public_summary_hash",
            "rebuilt_public_summary_hash",
        ):
            with self.subTest(key=key):
                tampered = deepcopy(document)
                tampered["verification"][key] = "0" * 64
                self.assertFalse(self._verify(tampered, values))

    def test_non_mapping_and_extra_field_fail_closed(self) -> None:
        document, values = self._build()
        for candidate in (None, [], "document", 1, True):
            with self.subTest(candidate=repr(candidate)):
                self.assertFalse(self._verify(candidate, values))
        tampered = deepcopy(document)
        tampered["raw_returns"] = ["hostile"]
        self.assertFalse(self._verify(tampered, values))

    def test_real_nonzero_count_reseal_rejects_original_context(self) -> None:
        document, values = self._build(**self.fixture._block_context(99173))
        self.assertGreater(document["summary"]["dependent_test_count"], 0)
        tampered = deepcopy(document)
        tampered["summary"]["dependent_test_count"] += 1
        unsealed = dict(tampered["summary"])
        unsealed.pop("public_summary_hash")
        tampered["summary"] = seal_strict_canonical_document(
            unsealed,
            "public_summary_hash",
        )
        new_hash = tampered["summary"]["public_summary_hash"]
        tampered["verification"]["supplied_public_summary_hash"] = new_hash
        tampered["verification"]["rebuilt_public_summary_hash"] = new_hash
        self.assertFalse(self._verify(tampered, values))

    def test_c3_verifier_requires_native_true(self) -> None:
        values = self._values()
        for result in (False, 1, "true", {}, []):
            with self.subTest(result=repr(result)), patch.object(
                adapter,
                "verify_strategy_correlation_cross_lag_public_summary",
                return_value=result,
            ):
                self.assertIsNone(
                    adapter.build_strategy_correlation_cross_lag_presentation_envelope(
                        **values
                    )
                )

    def test_c3_builder_and_verifier_exceptions_fail_closed(self) -> None:
        values = self._values()
        with patch.object(
            adapter,
            "build_strategy_correlation_cross_lag_public_summary",
            side_effect=RuntimeError("synthetic builder failure"),
        ):
            self.assertIsNone(
                adapter.build_strategy_correlation_cross_lag_presentation_envelope(
                    **values
                )
            )
        with patch.object(
            adapter,
            "verify_strategy_correlation_cross_lag_public_summary",
            side_effect=RuntimeError("synthetic verifier failure"),
        ):
            self.assertIsNone(
                adapter.build_strategy_correlation_cross_lag_presentation_envelope(
                    **values
                )
            )

    def test_invalid_c3_builder_results_fail_closed(self) -> None:
        values = self._values()
        valid_summary = self.fixture._build()
        candidates = (
            None,
            [],
            {**valid_summary, "schema_version": "wrong"},
            {**valid_summary, "verification_schema_version": "wrong"},
            {**valid_summary, "static_fingerprint": "wrong"},
            {**valid_summary, "public_summary_hash": "not-a-hash"},
        )
        for candidate in candidates:
            with self.subTest(candidate_type=type(candidate).__name__), patch.object(
                adapter,
                "build_strategy_correlation_cross_lag_public_summary",
                return_value=candidate,
            ), patch.object(
                adapter,
                "verify_strategy_correlation_cross_lag_public_summary",
                return_value=True,
            ):
                self.assertIsNone(
                    adapter.build_strategy_correlation_cross_lag_presentation_envelope(
                        **values
                    )
                )

    def test_source_and_returned_mappings_do_not_alias(self) -> None:
        values = self._values()
        source = self.fixture._build()
        original_state = source["public_state"]
        with patch.object(
            adapter,
            "build_strategy_correlation_cross_lag_public_summary",
            return_value=source,
        ), patch.object(
            adapter,
            "verify_strategy_correlation_cross_lag_public_summary",
            return_value=True,
        ):
            document = (
                adapter.build_strategy_correlation_cross_lag_presentation_envelope(
                    **values
                )
            )
        source["public_state"] = "MUTATED_SOURCE"
        self.assertEqual(document["summary"]["public_state"], original_state)
        document["summary"]["public_state"] = "MUTATED_ENVELOPE"
        self.assertEqual(source["public_state"], "MUTATED_SOURCE")

    def test_all_authority_fields_remain_native_locked(self) -> None:
        document, _values = self._build(**self.fixture._block_context(99173))
        authority = document["summary"]["authority"]
        self.assertIs(authority["descriptive_only"], True)
        self.assertTrue(
            all(
                value is False
                for key, value in authority.items()
                if key != "descriptive_only"
            )
        )

    def test_build_and_verify_use_no_denied_io_or_nondeterminism(self) -> None:
        values = self._values()
        denied = AssertionError("denied side effect")
        with patch("builtins.open", side_effect=denied), patch.object(
            socket, "socket", side_effect=denied
        ), patch.object(sqlite3, "connect", side_effect=denied), patch.object(
            time, "time", side_effect=denied
        ), patch.object(random, "random", side_effect=denied), patch.object(
            uuid, "uuid4", side_effect=denied
        ):
            document = (
                adapter.build_strategy_correlation_cross_lag_presentation_envelope(
                    **values
                )
            )
            self.assertIsNotNone(document)
            self.assertTrue(self._verify(document, values))

    def test_source_imports_exclude_transport_storage_and_frontend(self) -> None:
        source_path = Path(adapter.__file__)
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
        forbidden = (
            "server",
            "http_contract",
            "flask",
            "sqlite",
            "socket",
            "subprocess",
            "pathlib",
            "static",
            "paper",
            "live",
        )
        self.assertFalse(
            [name for name in imported if any(token in name for token in forbidden)]
        )

    def test_verifier_exception_never_escapes(self) -> None:
        document, values = self._build()
        with patch.object(
            adapter,
            "build_strategy_correlation_cross_lag_presentation_envelope",
            side_effect=RuntimeError("synthetic envelope failure"),
        ):
            self.assertFalse(self._verify(document, values))


if __name__ == "__main__":
    unittest.main()
