"""Strict JSON for portable research identities (never stringify unknown objects)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode("ascii")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate_json_key:" + key)
        result[key] = value
    return result


def _constant(value):
    raise ValueError("nonfinite_json_constant:" + value)


def parse_document(raw: bytes, *, maximum_bytes: int = 64 * 1024 * 1024) -> dict:
    if type(raw) is not bytes or not raw or len(raw) > maximum_bytes:
        raise ValueError("document_size_or_type_invalid")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                       parse_constant=_constant)
    if type(value) is not dict:
        raise ValueError("document_object_required")
    return value


def read_document(path: str | Path) -> dict:
    with Path(path).open("rb") as handle:
        return parse_document(handle.read(64 * 1024 * 1024 + 1))
