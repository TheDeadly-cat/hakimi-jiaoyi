import unittest

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


class StrictJsonContractTests(unittest.TestCase):
    def test_native_boolean_integer_and_float_aliases_are_distinct(self):
        self.assertFalse(strict_json_contract_equal(True, 1))
        self.assertFalse(strict_json_contract_equal(False, 0))
        self.assertFalse(strict_json_contract_equal(19, 19.0))

    def test_nested_dictionary_order_is_irrelevant_but_types_are_exact(self):
        left = {"a": [{"enabled": False, "count": 7}], "b": "x"}
        right = {"b": "x", "a": [{"count": 7, "enabled": False}]}
        alias = {"b": "x", "a": [{"count": 7.0, "enabled": False}]}

        self.assertTrue(strict_json_contract_equal(left, right))
        self.assertFalse(strict_json_contract_equal(left, alias))

    def test_list_order_and_dictionary_key_sets_are_contractual(self):
        self.assertFalse(strict_json_contract_equal(["a", "b"], ["b", "a"]))
        self.assertFalse(strict_json_contract_equal({"a": 1}, {"a": 1, "b": 2}))

    def test_seal_replaces_stale_hash_with_exact_canonical_hash(self):
        source = {"schema_version": "x-v1", "value": 7, "hash": "stale"}

        sealed = seal_strict_canonical_document(source, "hash")
        expected_payload = {"schema_version": "x-v1", "value": 7}

        self.assertEqual(sealed["hash"], strict_canonical_hash(expected_payload))
        self.assertEqual(source["hash"], "stale")

    def test_seal_deep_copies_nested_values(self):
        source = {"nested": {"items": [1, 2]}}
        sealed = seal_strict_canonical_document(source, "document_hash")

        sealed["nested"]["items"].append(3)

        self.assertEqual(source, {"nested": {"items": [1, 2]}})

    def test_seal_rejects_invalid_document_or_hash_field(self):
        with self.assertRaisesRegex(ValueError, "strict_canonical_document_invalid"):
            seal_strict_canonical_document([], "hash")
        with self.assertRaisesRegex(ValueError, "strict_canonical_hash_field_invalid"):
            seal_strict_canonical_document({}, " hash ")

    def test_seal_preserves_nonfinite_fail_closed_boundary(self):
        with self.assertRaisesRegex(ValueError, "strict_canonical_json_invalid"):
            seal_strict_canonical_document({"value": float("nan")}, "hash")


if __name__ == "__main__":
    unittest.main()
