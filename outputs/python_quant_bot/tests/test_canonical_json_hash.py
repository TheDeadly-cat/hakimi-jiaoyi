from __future__ import annotations

import unittest

from exchange_terminal.services.canonical_json_hash import (
    canonical_hash as utility_hash,
)
from exchange_terminal.services.strategy_correlation_multiplicity_audit import (
    canonical_hash as multiplicity_hash,
)
from exchange_terminal.services.strategy_correlation_uncertainty_audit import (
    canonical_hash as uncertainty_hash,
)
from exchange_terminal.services.strategy_matrix_protocol import (
    canonical_hash as protocol_hash,
)


class CanonicalJsonHashTests(unittest.TestCase):
    def test_legacy_golden_digests_are_bit_for_bit_stable(self) -> None:
        vectors = (
            (None, "74234e98afe7498fb5daf1f36ac2d78acc339464f950703b8c019892f982b90b"),
            (True, "b5bea41b6c623f7c09f1bf24dcae58ebab3c0cdd90ad966bc43a45b44867e12b"),
            (17, "4523540f1504cd17100c4835e85b7eefd49911580f8efff0599a8f283be6b9e3"),
            (0.125, "52c003e77e74cbacd60930b997433027175ca60b20b7fbb4ec6073b2c4932bb9"),
            (
                "\u54c8\u57fa\u7c73",
                "ab7dc81da3ead5c5edb9801050088f45eb57b21183e7222bb5edcfe466c7cb4c",
            ),
            (
                [1, "x", False],
                "46d5f18f17001d1d00950c20b2313e0851fe402023a91837d6c8cb5f3465ee2d",
            ),
            (
                {"b": 2, "a": [1, None]},
                "9730e6516a38d2d8ce3fc60389e7fed5df8ac18401a09123ed24452a40388ac9",
            ),
        )
        for payload, expected in vectors:
            with self.subTest(payload=payload):
                self.assertEqual(utility_hash(payload), expected)

    def test_protocol_and_correlation_modules_reexport_one_function(self) -> None:
        self.assertIs(protocol_hash, utility_hash)
        self.assertIs(uncertainty_hash, utility_hash)
        self.assertIs(multiplicity_hash, utility_hash)

    def test_legacy_default_str_behavior_remains_compatible(self) -> None:
        class StableValue:
            def __str__(self) -> str:
                return "stable-value-v1"

        self.assertEqual(utility_hash(StableValue()), utility_hash("stable-value-v1"))


if __name__ == "__main__":
    unittest.main()
