from __future__ import annotations

import base64
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


CONTRACT_VERSION = "strict-ed25519-public-contract-v1"
STATIC_FINGERPRINT = "20260824-strict-ed25519-public-contract-v1-lock-1"


def decode_canonical_base64_v1(value: Any, field: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be nonempty base64")
    try:
        decoded = base64.b64decode(value, validate=True)
    except Exception as exc:
        raise ValueError(f"{field} must be valid base64") from exc
    if base64.b64encode(decoded).decode("ascii") != value:
        raise ValueError(f"{field} must use canonical base64")
    return decoded


def load_canonical_ed25519_public_key_v1(
    spki_bytes: bytes,
) -> Ed25519PublicKey:
    if not isinstance(spki_bytes, bytes) or not spki_bytes:
        raise ValueError("public key SPKI must be nonempty bytes")
    try:
        public_key = serialization.load_der_public_key(spki_bytes)
    except Exception as exc:
        raise ValueError("public key SPKI is invalid") from exc
    if not isinstance(public_key, Ed25519PublicKey):
        raise ValueError("public key must be Ed25519")
    canonical_spki = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    if canonical_spki != spki_bytes:
        raise ValueError("public key SPKI must use canonical DER")
    return public_key
