from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any


def strict_canonical_hash(payload: Any) -> str:
    try:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("strict_canonical_json_invalid") from exc
    return hashlib.sha256(encoded).hexdigest()


def strict_json_contract_equal(actual: Any, expected: Any) -> bool:
    """Compare JSON contract values without Python bool/int numeric aliases."""

    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(
            strict_json_contract_equal(actual[key], expected[key])
            for key in expected
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            strict_json_contract_equal(actual_item, expected_item)
            for actual_item, expected_item in zip(actual, expected)
        )
    return actual == expected


def seal_strict_canonical_document(
    document: Any,
    hash_field: Any,
) -> dict[str, Any]:
    """Return a deep-copied document sealed without its previous hash field."""

    if type(document) is not dict:
        raise ValueError("strict_canonical_document_invalid")
    if (
        type(hash_field) is not str
        or not hash_field
        or hash_field != hash_field.strip()
    ):
        raise ValueError("strict_canonical_hash_field_invalid")
    sealed = deepcopy(document)
    sealed.pop(hash_field, None)
    sealed[hash_field] = strict_canonical_hash(sealed)
    return sealed


__all__ = [
    "seal_strict_canonical_document",
    "strict_canonical_hash",
    "strict_json_contract_equal",
]
