from __future__ import annotations

import unittest

from exchange_terminal.services.strict_json_artifact import (
    StrictJsonConfigurationError,
    StrictJsonDuplicateKeyError,
    StrictJsonInputTypeError,
    StrictJsonNestingError,
    StrictJsonNonFiniteNumberError,
    StrictJsonRootTypeError,
    StrictJsonSyntaxError,
    StrictJsonUtf8Error,
    parse_strict_json_object,
)


class StrictJsonArtifactTests(unittest.TestCase):
    def test_accepts_utf8_object_without_imposing_canonical_bytes(self) -> None:
        raw = ' { "message": "\u7814\u7a76", "values": [1, 2.5, null] }\n'.encode("utf-8")

        parsed = parse_strict_json_object(raw)

        self.assertEqual(parsed, {"message": "\u7814\u7a76", "values": [1, 2.5, None]})

    def test_requires_exact_bytes_valid_utf8_syntax_and_object_root(self) -> None:
        invalid = (
            ("{}", StrictJsonInputTypeError),
            (bytearray(b"{}"), StrictJsonInputTypeError),
            (b'{"value":"\xff"}', StrictJsonUtf8Error),
            (b'{"value":}', StrictJsonSyntaxError),
            (b"[]", StrictJsonRootTypeError),
            (b"null", StrictJsonRootTypeError),
        )
        for raw, error in invalid:
            with self.subTest(raw=raw, error=error.__name__):
                with self.assertRaises(error):
                    parse_strict_json_object(raw)  # type: ignore[arg-type]

    def test_rejects_duplicate_keys_at_every_object_depth(self) -> None:
        for raw in (
            b'{"value":1,"value":2}',
            b'{"outer":{"value":1,"value":2}}',
            b'{"items":[{"value":1,"value":2}]}',
        ):
            with self.subTest(raw=raw):
                with self.assertRaises(StrictJsonDuplicateKeyError):
                    parse_strict_json_object(raw)

    def test_rejects_every_non_finite_number_form(self) -> None:
        for number in (b"NaN", b"Infinity", b"-Infinity", b"1e999", b"-1e999"):
            with self.subTest(number=number):
                with self.assertRaises(StrictJsonNonFiniteNumberError):
                    parse_strict_json_object(b'{"value":' + number + b"}")

    def test_depth_limit_counts_root_as_one_and_every_child_value(self) -> None:
        at_limit = b'{"value":' + (b"[" * 126) + b"0" + (b"]" * 126) + b"}"
        beyond_limit = b'{"value":' + (b"[" * 127) + b"0" + (b"]" * 127) + b"}"

        self.assertIsInstance(parse_strict_json_object(at_limit), dict)
        with self.assertRaises(StrictJsonNestingError):
            parse_strict_json_object(beyond_limit)

        with self.assertRaises(StrictJsonNestingError):
            parse_strict_json_object(b'{"value":0}', max_nesting=1)
        self.assertEqual(parse_strict_json_object(b"{}", max_nesting=1), {})

    def test_parser_recursion_failure_has_stable_nesting_error(self) -> None:
        deeply_nested = b'{"value":' + (b"[" * 1400) + b"0" + (b"]" * 1400) + b"}"

        with self.assertRaises(StrictJsonNestingError):
            parse_strict_json_object(deeply_nested)

    def test_max_nesting_configuration_is_exact_positive_int(self) -> None:
        for value in (True, False, 0, -1, 1.5, "128"):
            with self.subTest(value=value):
                with self.assertRaises(StrictJsonConfigurationError):
                    parse_strict_json_object(b"{}", max_nesting=value)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
