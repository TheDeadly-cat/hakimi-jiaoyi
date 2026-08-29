"""Focused ADR0502 contracts for exact-native artifact receipt identifiers."""

from __future__ import annotations

import unittest

from exchange_terminal.application import (
    strategy_correlation_identity_bound_transcript_artifact_availability_receipt_candidate_v1
    as candidate,
)


class _EqualityAliasStr(str):
    def __new__(cls, value: str, equality_target: str) -> "_EqualityAliasStr":
        instance = super().__new__(cls, value)
        instance.equality_target = equality_target
        return instance

    def __eq__(self, other: object) -> bool:
        return str(other) == self.equality_target

    def __hash__(self) -> int:
        return hash(self.equality_target)


class StrategyCorrelationTranscriptArtifactIdentifierExactNativeLockV1Tests(
    unittest.TestCase
):
    def test_native_token_and_hash_remain_accepted(self) -> None:
        self.assertEqual(candidate._require_token("retriever_id", "retriever-1"), "retriever-1")
        self.assertTrue(candidate._is_hash("0" * 64))

    def test_equality_alias_retriever_identifier_is_rejected(self) -> None:
        alias = _EqualityAliasStr("other-retriever", "registered-retriever")
        self.assertNotEqual(str(alias), "registered-retriever")

        with self.assertRaisesRegex(ValueError, "bounded exact token"):
            candidate._require_token("retriever_id", alias)

    def test_equality_alias_artifact_identifier_is_rejected(self) -> None:
        alias = _EqualityAliasStr("other-artifact", "registered-artifact")
        self.assertNotEqual(str(alias), "registered-artifact")

        with self.assertRaisesRegex(ValueError, "bounded exact token"):
            candidate._require_token("artifact_id", alias)

    def test_string_subclass_hash_is_rejected(self) -> None:
        alias = _EqualityAliasStr("0" * 64, "1" * 64)
        self.assertFalse(candidate._is_hash(alias))


if __name__ == "__main__":
    unittest.main()
