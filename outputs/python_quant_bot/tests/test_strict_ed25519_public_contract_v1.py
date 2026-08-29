from __future__ import annotations

import base64
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.services.strict_ed25519_public_contract_v1 import (
    CONTRACT_VERSION,
    decode_canonical_base64_v1,
    load_canonical_ed25519_public_key_v1,
)


class StrictEd25519PublicContractV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.private_key = Ed25519PrivateKey.generate()
        self.spki = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def test_contract_version_is_fixed(self):
        self.assertEqual("strict-ed25519-public-contract-v1", CONTRACT_VERSION)

    def test_canonical_base64_round_trip(self):
        encoded = base64.b64encode(self.spki).decode("ascii")
        self.assertEqual(self.spki, decode_canonical_base64_v1(encoded, "spki"))

    def test_empty_and_non_string_base64_are_rejected(self):
        for value in (None, b"abc", ""):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    decode_canonical_base64_v1(value, "value")

    def test_invalid_or_whitespace_base64_is_rejected(self):
        for value in ("not-base64!", "YQ==\n", "Y Q=="):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    decode_canonical_base64_v1(value, "value")

    def test_noncanonical_base64_padding_is_rejected(self):
        with self.assertRaises(ValueError):
            decode_canonical_base64_v1("YQ===", "value")

    def test_canonical_ed25519_spki_loads(self):
        public_key = load_canonical_ed25519_public_key_v1(self.spki)
        rebuilt = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self.assertEqual(self.spki, rebuilt)

    def test_empty_nonbytes_and_malformed_der_are_rejected(self):
        for value in (None, "not-bytes", b"", b"not-der"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    load_canonical_ed25519_public_key_v1(value)

    def test_non_ed25519_spki_is_rejected(self):
        ec_private = ec.generate_private_key(ec.SECP256R1())
        ec_spki = ec_private.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        with self.assertRaises(ValueError):
            load_canonical_ed25519_public_key_v1(ec_spki)

    def test_der_with_trailing_bytes_is_rejected(self):
        with self.assertRaises(ValueError):
            load_canonical_ed25519_public_key_v1(self.spki + b"trailing")

    def test_production_has_no_private_key_io_network_clock_or_runtime_access(self):
        from exchange_terminal.services import strict_ed25519_public_contract_v1 as module

        source = Path(module.__file__).read_text(encoding="utf-8")
        forbidden = (
            "Ed25519PrivateKey",
            "private_key",
            "time.time",
            "datetime.now",
            "Path(",
            "open(",
            "requests.",
            "urllib.",
            "sqlite3",
            ".env",
            "runtime/",
            "runtime\\\\",
        )
        for token in forbidden:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
