from __future__ import annotations

import hashlib
import inspect
import unittest
from pathlib import Path

from exchange_terminal.services import (
    strategy_correlation_cluster_stability_formal_persistence_projection as persistence_projection,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_stability_formal_persistence_protocol as persistence_protocol,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_stability_formal_registry_adapter as frozen_adapter,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_stability_registry_projection as registry_projection,
)
from exchange_terminal.services.strict_governance_primitives import (
    strict_date_before,
    strict_iso_date,
    strict_locked_fields,
    strict_native_false,
    strict_native_true,
    strict_nonempty_string,
    strict_sha256,
    strict_timestamp_date_before,
    strict_utc_second_timestamp,
)


class StrictGovernancePrimitivesTests(unittest.TestCase):
    FROZEN_ADAPTER_HASH = (
        "28104ef1b7d1cc1048cabc564bfea81f9538e7adc8f98901b6e4904f2390e1b4"
    )

    def test_native_true_rejects_truthy_aliases(self):
        self.assertTrue(strict_native_true(True))
        for value in (1, "true", [True], None, False):
            self.assertFalse(strict_native_true(value))

    def test_native_false_rejects_falsy_aliases(self):
        self.assertTrue(strict_native_false(False))
        for value in (0, "", "false", [], None, True):
            self.assertFalse(strict_native_false(value))

    def test_nonempty_string_is_exact_and_trim_aware(self):
        self.assertTrue(strict_nonempty_string("registry-v1"))
        for value in ("", "   ", 1, True, None, ["registry-v1"]):
            self.assertFalse(strict_nonempty_string(value))

    def test_sha256_requires_lowercase_exact_hex(self):
        self.assertTrue(strict_sha256("a" * 64))
        for value in ("A" * 64, "a" * 63, "g" * 64, 0, True, None):
            self.assertFalse(strict_sha256(value))

    def test_iso_date_is_canonical(self):
        self.assertTrue(strict_iso_date("2026-08-21"))
        self.assertTrue(strict_iso_date("2024-02-29"))
        for value in (
            "2026-8-21",
            "2026-08-21T00:00:00Z",
            "2023-02-29",
            20260821,
            None,
        ):
            self.assertFalse(strict_iso_date(value))

    def test_utc_timestamp_requires_second_precision_and_z(self):
        self.assertTrue(strict_utc_second_timestamp("2026-08-20T08:00:00Z"))
        for value in (
            "2026-08-20T08:00:00+00:00",
            "2026-08-20T08:00:00.000Z",
            "2026-08-20 08:00:00Z",
            "2026-08-20T08:00Z",
            None,
        ):
            self.assertFalse(strict_utc_second_timestamp(value))

    def test_date_before_is_strict(self):
        self.assertTrue(strict_date_before("2026-08-20", "2026-08-21"))
        self.assertFalse(strict_date_before("2026-08-21", "2026-08-21"))
        self.assertFalse(strict_date_before("2026-08-22", "2026-08-21"))
        self.assertFalse(strict_date_before("invalid", "2026-08-21"))

    def test_timestamp_date_before_is_strict_by_utc_date(self):
        self.assertTrue(
            strict_timestamp_date_before(
                "2026-08-20T23:59:59Z",
                "2026-08-21",
            )
        )
        self.assertFalse(
            strict_timestamp_date_before(
                "2026-08-21T00:00:00Z",
                "2026-08-21",
            )
        )
        self.assertFalse(strict_timestamp_date_before("invalid", "2026-08-21"))

    def test_locked_fields_require_unique_explicit_native_false_fields(self):
        document = {"formal": False, "writer": False}
        self.assertTrue(strict_locked_fields(document, ("formal", "writer")))
        for fields in (
            (),
            ("formal", "formal"),
            ("formal", ""),
            {"formal", "writer"},
            "formal",
        ):
            self.assertFalse(strict_locked_fields(document, fields))
        for attacked in (
            {"formal": 0, "writer": False},
            {"formal": False, "writer": "false"},
            {"formal": False},
            None,
        ):
            self.assertFalse(
                strict_locked_fields(attacked, ("formal", "writer"))
            )

    def test_migrated_modules_no_longer_define_duplicate_primitives(self):
        forbidden = {
            "_native_true",
            "_native_false",
            "_is_sha256",
            "_is_date",
            "_is_utc_timestamp",
            "_preregistered_before_evidence",
            "_locked_document",
        }
        for module in (
            registry_projection,
            persistence_protocol,
            persistence_projection,
        ):
            local = {
                name
                for name, value in inspect.getmembers(module, inspect.isfunction)
                if value.__module__ == module.__name__
            }
            self.assertFalse(forbidden & local, module.__name__)

    def test_excluded_adapter_source_hash_remains_frozen(self):
        source_path = Path(frozen_adapter.__file__)
        digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
        self.assertEqual(digest, self.FROZEN_ADAPTER_HASH)


if __name__ == "__main__":
    unittest.main()
