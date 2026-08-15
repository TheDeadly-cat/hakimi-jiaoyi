from __future__ import annotations

import json
import math
from typing import Any


DEFAULT_STRICT_JSON_MAX_NESTING = 128


class StrictJsonArtifactError(ValueError):
    """Stable, path-free failure at a strict JSON artifact boundary."""


class StrictJsonConfigurationError(StrictJsonArtifactError):
    pass


class StrictJsonInputTypeError(StrictJsonArtifactError):
    pass


class StrictJsonUtf8Error(StrictJsonArtifactError):
    pass


class StrictJsonSyntaxError(StrictJsonArtifactError):
    pass


class StrictJsonDuplicateKeyError(StrictJsonArtifactError):
    pass


class StrictJsonNonFiniteNumberError(StrictJsonArtifactError):
    pass


class StrictJsonNestingError(StrictJsonArtifactError):
    pass


class StrictJsonRootTypeError(StrictJsonArtifactError):
    pass


def parse_strict_json_object(
    raw: bytes,
    *,
    max_nesting: int = DEFAULT_STRICT_JSON_MAX_NESTING,
) -> dict[str, Any]:
    """Parse one UTF-8 JSON object under a bounded, ambiguity-free contract.

    The root object has depth 1. Every object-member value or array element is
    one level deeper, including scalar values. Duplicate object keys at any
    depth and every non-finite number form are rejected. This parser does not
    require or produce a canonical serialization; byte canonicalization stays
    with the artifact owner.
    """

    if type(raw) is not bytes:
        raise StrictJsonInputTypeError("strict_json_bytes_required")
    if type(max_nesting) is not int or max_nesting < 1:
        raise StrictJsonConfigurationError("strict_json_max_nesting_invalid")

    def reject_constant(_value: str) -> None:
        raise StrictJsonNonFiniteNumberError("strict_json_non_finite_number")

    def strict_float(value: str) -> float:
        parsed = float(value)
        if not math.isfinite(parsed):
            raise StrictJsonNonFiniteNumberError("strict_json_non_finite_number")
        return parsed

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for key, value in pairs:
            if key in payload:
                raise StrictJsonDuplicateKeyError("strict_json_duplicate_object_key")
            payload[key] = value
        return payload

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StrictJsonUtf8Error("strict_json_utf8_invalid") from exc
    try:
        payload = json.loads(
            text,
            parse_constant=reject_constant,
            parse_float=strict_float,
            object_pairs_hook=reject_duplicate_keys,
        )
    except StrictJsonArtifactError:
        raise
    except RecursionError as exc:
        raise StrictJsonNestingError("strict_json_nesting_limit_exceeded") from exc
    except (json.JSONDecodeError, ValueError) as exc:
        raise StrictJsonSyntaxError("strict_json_syntax_invalid") from exc

    if not isinstance(payload, dict):
        raise StrictJsonRootTypeError("strict_json_object_required")

    stack: list[tuple[Any, int]] = [(payload, 1)]
    while stack:
        value, depth = stack.pop()
        if depth > max_nesting:
            raise StrictJsonNestingError("strict_json_nesting_limit_exceeded")
        if isinstance(value, dict):
            stack.extend((child, depth + 1) for child in value.values())
        elif isinstance(value, list):
            stack.extend((child, depth + 1) for child in value)
        elif isinstance(value, float) and not math.isfinite(value):
            raise StrictJsonNonFiniteNumberError("strict_json_non_finite_number")
    return payload
