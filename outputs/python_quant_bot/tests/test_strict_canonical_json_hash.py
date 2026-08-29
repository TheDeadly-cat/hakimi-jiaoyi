from __future__ import annotations

import hashlib
import json
import math
import unittest

from exchange_terminal.services.strict_canonical_json_hash import (
    strict_canonical_hash,
)


class StrictCanonicalJsonHashTests(unittest.TestCase):
    @staticmethod
    def _independent_hash(value: object) -> str:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def test_matches_independent_unicode_canonicalization(self) -> None:
        payload = {"z": [1, 2.5, False, None], "a": {"中文": "值"}}
        self.assertEqual(strict_canonical_hash(payload), self._independent_hash(payload))

    def test_dictionary_insertion_order_does_not_change_hash(self) -> None:
        left = {"b": 2, "a": 1}
        right = {"a": 1, "b": 2}
        self.assertEqual(strict_canonical_hash(left), strict_canonical_hash(right))

    def test_native_boolean_and_integer_remain_distinct(self) -> None:
        self.assertNotEqual(
            strict_canonical_hash({"value": True}),
            strict_canonical_hash({"value": 1}),
        )

    def test_nonfinite_numbers_fail_closed(self) -> None:
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "strict_canonical_json_invalid"):
                    strict_canonical_hash({"value": value})

    def test_non_json_types_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "strict_canonical_json_invalid"):
            strict_canonical_hash({"value": {1, 2, 3}})


if __name__ == "__main__":
    unittest.main()
