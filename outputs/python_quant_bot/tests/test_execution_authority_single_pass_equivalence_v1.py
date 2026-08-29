from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any
import random
import unittest
import unicodedata

from exchange_terminal.services.execution_authority import (
    EXECUTION_AUTHORITY_FIELD_KEYS,
    authority_violations,
    canonical_authority_key,
)


def _reference_canonical_authority_key(value: Any) -> str:
    normalized = unicodedata.normalize("NFKC", str(value))
    return "".join(
        character for character in normalized.casefold() if character.isalnum()
    )


def _reference_authority_violations(payload: Any, *, path: str = "$") -> list[str]:
    violations: list[str] = []
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            child = f"{path}.{key}"
            if (
                _reference_canonical_authority_key(key)
                in EXECUTION_AUTHORITY_FIELD_KEYS
                and value is not False
            ):
                violations.append(child)
            violations.extend(_reference_authority_violations(value, path=child))
    elif isinstance(payload, (list, tuple)):
        for index, value in enumerate(payload):
            violations.extend(
                _reference_authority_violations(value, path=f"{path}[{index}]")
            )
    return violations


class _MutableText:
    def __init__(self, text: str) -> None:
        self.text = text

    def __str__(self) -> str:
        return self.text


class ExecutionAuthoritySinglePassEquivalenceV1Tests(unittest.TestCase):
    def assert_reference_equivalent(self, payload: Any, *, path: str = "$") -> None:
        self.assertEqual(
            authority_violations(payload, path=path),
            _reference_authority_violations(payload, path=path),
        )

    def test_adversarial_aliases_preserve_exact_paths_and_order(self) -> None:
        payload = MappingProxyType({
            "live_authorized": False,
            "nested": [
                {"CAN_TRADE": "false", "raw_can_trade": "descriptive"},
                (
                    {"可下单": True},
                    {"实盘－授权": 0},
                    {"Ｐａｐｅｒ＿Ａｕｔｈｏｒｉｚｅｄ": None},
                    {"parameter-selection-allowed": []},
                ),
            ],
            7: {"paperAuthorized": {}},
        })

        self.assert_reference_equivalent(payload, path="evidence")
        self.assertEqual(
            authority_violations(payload, path="evidence"),
            [
                "evidence.nested[0].CAN_TRADE",
                "evidence.nested[1][0].可下单",
                "evidence.nested[1][1].实盘－授权",
                "evidence.nested[1][2].Ｐａｐｅｒ＿Ａｕｔｈｏｒｉｚｅｄ",
                "evidence.nested[1][3].parameter-selection-allowed",
                "evidence.7.paperAuthorized",
            ],
        )

    def test_native_false_remains_the_only_allowed_value(self) -> None:
        values = (False, True, "false", 0, None, [], {}, ())
        for value in values:
            with self.subTest(value=value):
                payload = {"liveAuthorized": value}
                self.assert_reference_equivalent(payload)
                expected = [] if value is False else ["$.liveAuthorized"]
                self.assertEqual(authority_violations(payload), expected)

    def test_deterministic_nested_corpus_matches_historical_algorithm(self) -> None:
        rng = random.Random(20260825)
        keys = (
            "source_id",
            "source_authority",
            "live_authorized",
            "live-authorized",
            "CAN_TRADE",
            "paperAuthorized",
            "可下单",
            "实盘－授权",
            "raw_live_authorized",
            "Ｐａｐｅｒ＿Ａｕｔｈｏｒｉｚｅｄ",
        )
        values = (False, True, "false", 0, 1, None, "research-only")

        for sample_index in range(128):
            rows: list[Any] = []
            for row_index in range(rng.randint(0, 12)):
                row = {
                    rng.choice(keys): rng.choice(values),
                    rng.choice(keys): rng.choice(values),
                    "row_index": row_index,
                }
                rows.append(row if rng.randrange(2) else (row,))
            payload = {
                "sample_index": sample_index,
                "rows": rows,
                rng.choice(keys): rng.choice(values),
            }
            self.assert_reference_equivalent(payload, path="synthetic")

    def test_scalar_roots_and_unhashable_inputs_keep_public_contract(self) -> None:
        for payload in (None, False, 0, "canTrade", object()):
            with self.subTest(payload=payload):
                self.assert_reference_equivalent(payload)

        self.assertEqual(
            canonical_authority_key(["Live", "Authorized"]),
            _reference_canonical_authority_key(["Live", "Authorized"]),
        )

    def test_cache_keys_follow_current_text_not_object_identity(self) -> None:
        mutable = _MutableText("live_authorized")
        self.assertEqual(
            canonical_authority_key(mutable),
            _reference_canonical_authority_key("live_authorized"),
        )

        mutable.text = "source_authority"
        self.assertEqual(
            canonical_authority_key(mutable),
            _reference_canonical_authority_key("source_authority"),
        )
        self.assertNotIn(canonical_authority_key(mutable), EXECUTION_AUTHORITY_FIELD_KEYS)


if __name__ == "__main__":
    unittest.main()
