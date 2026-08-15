from __future__ import annotations

import hashlib
import json
import math
import os
from collections.abc import Mapping
from pathlib import Path
import uuid
from typing import Any

from .portfolio_backtest_pack import (
    CURRENT_PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION,
    MAX_PORTFOLIO_INTERNAL_BACKTEST_PACK_BYTES,
    MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES,
    MAX_PORTFOLIO_STATISTICAL_AUDIT_BYTES,
    PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION,
    PORTFOLIO_INTERNAL_BACKTEST_PACK_V3_SCHEMA_VERSION,
    PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
    PORTFOLIO_INTERNAL_BACKTEST_PACK_V5_SCHEMA_VERSION,
    PORTFOLIO_INTERNAL_BACKTEST_PACK_V6_SCHEMA_VERSION,
    PORTFOLIO_INTERNAL_FORWARD_EVIDENCE_SCHEMA_VERSION,
    PORTFOLIO_INTERNAL_FORWARD_EVIDENCE_V2_SCHEMA_VERSION,
    required_internal_backtest_bundle_members,
    verify_internal_forward_evidence,
    verify_internal_backtest_bundle,
    verify_internal_backtest_pack,
)
from .backtest_return_quality import (
    BACKTEST_RETURN_QUALITY_SCHEMA_VERSION,
    BACKTEST_RETURN_QUALITY_V2_SCHEMA_VERSION,
    BACKTEST_RETURN_QUALITY_V3_SCHEMA_VERSION,
    CURRENT_BACKTEST_RETURN_QUALITY_SCHEMA_VERSION,
)
from .portfolio_forward_performance import PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION
from .portfolio_forward_statistical_audit import (
    PORTFOLIO_FORWARD_DECISION_POLICY,
    PORTFOLIO_FORWARD_DECISION_WINDOW_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_RISK_ACCEPTANCE_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_STATISTICAL_AUDIT_V2_SCHEMA_VERSION,
)
from .immutable_artifact_bundle import (
    ArtifactBundleByteLimitExceeded,
    ArtifactBundleError,
    DEFAULT_BUNDLE_MANIFEST_FILE,
    DEFAULT_MAX_BUNDLE_MANIFEST_BYTES,
    read_bounded_artifact,
    read_immutable_artifact_bundle,
    verify_content_addressed_bundle_manifest,
    windows_safe_basename_identity,
)
from .execution_authority import authority_violations as shared_authority_violations
from .strict_json_artifact import parse_strict_json_object


PORTFOLIO_BACKTEST_PACK_POINTER_SCHEMA_VERSION = "portfolio-backtest-pack-pointer-v1"
PORTFOLIO_BACKTEST_BUNDLE_POINTER_SCHEMA_VERSION = "portfolio-backtest-pack-pointer-v2"
PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_V3_SCHEMA_VERSION = (
    "portfolio-backtest-return-quality-snapshot-v3"
)
PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_V4_SCHEMA_VERSION = (
    "portfolio-backtest-return-quality-snapshot-v4"
)
PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_SCHEMA_VERSION = (
    PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_V4_SCHEMA_VERSION
)
PORTFOLIO_BACKTEST_FORWARD_PROMOTION_SUMMARY_V1_SCHEMA_VERSION = (
    "portfolio-backtest-forward-promotion-summary-v1"
)
PORTFOLIO_BACKTEST_FORWARD_PROMOTION_SUMMARY_V2_SCHEMA_VERSION = (
    "portfolio-backtest-forward-promotion-summary-v2"
)
PORTFOLIO_BACKTEST_FORWARD_PROMOTION_SUMMARY_SCHEMA_VERSION = (
    PORTFOLIO_BACKTEST_FORWARD_PROMOTION_SUMMARY_V2_SCHEMA_VERSION
)
DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE = "current_internal_portfolio_backtest_pack.json"
MAX_PORTFOLIO_BACKTEST_PACK_POINTER_BYTES = 64 * 1024
MAX_PUBLIC_PORTFOLIO_BACKTEST_PACK_BYTES = 32 * 1024 * 1024
MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_MANIFEST_BYTES = DEFAULT_MAX_BUNDLE_MANIFEST_BYTES
MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_MEMBER_COUNT = 3
MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_MEMBER_BYTES = (
    MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES
)
MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_TOTAL_BYTES = (
    MAX_PORTFOLIO_INTERNAL_BACKTEST_PACK_BYTES
    + MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES
    + MAX_PORTFOLIO_STATISTICAL_AUDIT_BYTES
)
_POINTER_STATUS = "CURRENT_FROZEN_INTERNAL_BACKTEST_PACK"
_BUNDLE_POINTER_STATUS = "CURRENT_FROZEN_INTERNAL_BACKTEST_BUNDLE"
_POINTER_SIZE_LIMIT_BLOCKER = "portfolio_backtest_pack_pointer_size_limit_exceeded"
_PACK_SIZE_LIMIT_BLOCKER = "portfolio_backtest_pack_size_limit_exceeded"
_POINTER_V1_FIELDS = {
    "schema_version",
    "status",
    "pack_file",
    "pack_file_sha256",
    "pack_schema_version",
    "candidate_hash",
    "pack_hash",
    "evidence_hash",
    "pack_status",
    "promotion_status",
    "generated_at",
    "research_only",
    "profitability_proven",
    "performance_claim_allowed",
    "parameter_selection_allowed",
    "automatic_paper_activation_allowed",
    "paper_authorized",
    "live_order_allowed",
    "pointer_hash",
}
_POINTER_V2_FIELDS = {
    "schema_version",
    "status",
    "bundle_dir",
    "manifest_file",
    "manifest_file_sha256",
    "bundle_hash",
    "pack_file",
    "pack_file_sha256",
    "pack_schema_version",
    "candidate_hash",
    "pack_hash",
    "evidence_hash",
    "pack_status",
    "promotion_status",
    "generated_at",
    "research_only",
    "profitability_proven",
    "performance_claim_allowed",
    "parameter_selection_allowed",
    "automatic_paper_activation_allowed",
    "paper_authorized",
    "live_order_allowed",
    "pointer_hash",
}
_PORTFOLIO_BUNDLE_BINDING_FIELDS = {
    "contract",
    "pack_file",
    "pack_schema_version",
    "candidate_hash",
    "pack_hash",
    "evidence_hash",
    "pack_status",
    "promotion_status",
    "generated_at",
}
_PORTFOLIO_BUNDLE_CONTRACT = "PORTFOLIO_INTERNAL_BACKTEST_BUNDLE_V1"
PORTFOLIO_BACKTEST_BUNDLE_PACK_ROLE = "INTERNAL_BACKTEST_PACK"
_WINDOWS_RESERVED_BASENAMES = {
    "aux",
    "clock$",
    "con",
    "nul",
    "prn",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}
_PACK_PUBLIC_EVIDENCE_COUPLING = {
    PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION: {
        "quality_schema": BACKTEST_RETURN_QUALITY_SCHEMA_VERSION,
        "forward_required": False,
        "source_bound_quality": False,
        "snapshot_schema": PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_V3_SCHEMA_VERSION,
    },
    PORTFOLIO_INTERNAL_BACKTEST_PACK_V3_SCHEMA_VERSION: {
        "quality_schema": BACKTEST_RETURN_QUALITY_SCHEMA_VERSION,
        "forward_required": True,
        "source_bound_quality": False,
        "snapshot_schema": PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_V3_SCHEMA_VERSION,
    },
    PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION: {
        "quality_schema": BACKTEST_RETURN_QUALITY_V2_SCHEMA_VERSION,
        "forward_required": True,
        "source_bound_quality": True,
        "snapshot_schema": PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_V3_SCHEMA_VERSION,
    },
    PORTFOLIO_INTERNAL_BACKTEST_PACK_V5_SCHEMA_VERSION: {
        "quality_schema": BACKTEST_RETURN_QUALITY_V3_SCHEMA_VERSION,
        "forward_required": True,
        "source_bound_quality": True,
        "snapshot_schema": PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_V3_SCHEMA_VERSION,
    },
    CURRENT_PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION: {
        "quality_schema": BACKTEST_RETURN_QUALITY_V3_SCHEMA_VERSION,
        "forward_required": True,
        "source_bound_quality": True,
        "snapshot_schema": PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_SCHEMA_VERSION,
    },
}


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _file_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class _ArtifactByteLimitExceeded(ValueError):
    def __init__(self, blocker: str) -> None:
        super().__init__(blocker)
        self.blocker = blocker


def _read_bounded_artifact(
    path: Path,
    *,
    byte_limit: int,
    blocker: str,
) -> bytes:
    """Read at most one byte beyond a public artifact's fixed byte budget."""

    if type(byte_limit) is not int or byte_limit < 1:
        raise ValueError("artifact byte limit invalid")
    with open(path, "rb") as handle:
        raw = handle.read(byte_limit + 1)
    if len(raw) > byte_limit:
        raise _ArtifactByteLimitExceeded(blocker)
    return raw


def _is_sha256(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def _strict_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _authority_violations(value: Any, path: str = "pointer") -> list[str]:
    return [
        f"authority_not_false:{violation}"
        for violation in shared_authority_violations(value, path=path)
    ]


def _read_json_object(raw: bytes) -> dict[str, Any]:
    """Legacy pointer-v1 parser; preserve its historical root-at-zero depth."""

    def reject_constant(value: str) -> Any:
        raise ValueError(f"non-finite JSON constant forbidden: {value}")

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for key, value in pairs:
            if key in payload:
                raise ValueError("duplicate JSON object key forbidden")
            payload[key] = value
        return payload

    try:
        payload = json.loads(
            raw.decode("utf-8"),
            parse_constant=reject_constant,
            object_pairs_hook=reject_duplicate_keys,
        )
    except RecursionError as exc:
        raise ValueError("JSON nesting depth invalid") from exc
    if not isinstance(payload, dict):
        raise ValueError("JSON object required")

    def require_bounded_depth(value: Any, depth: int = 0) -> None:
        if depth > 128:
            raise ValueError("JSON nesting depth invalid")
        if isinstance(value, dict):
            for nested in value.values():
                require_bounded_depth(nested, depth + 1)
        elif isinstance(value, list):
            for nested in value:
                require_bounded_depth(nested, depth + 1)
        elif isinstance(value, float) and not math.isfinite(value):
            raise ValueError("non-finite JSON number forbidden")

    try:
        require_bounded_depth(payload)
    except RecursionError as exc:
        raise ValueError("JSON nesting depth invalid") from exc
    return payload


def _read_current_json_object(raw: bytes) -> dict[str, Any]:
    """Current pointer-v2 and immutable-bundle strict JSON boundary."""

    return parse_strict_json_object(raw)


def _read_pointer_object_by_schema(raw: bytes) -> dict[str, Any]:
    """Prefer the current contract, with a one-way v1-only depth fallback."""

    try:
        return _read_current_json_object(raw)
    except ValueError as current_error:
        try:
            legacy = _read_json_object(raw)
        except ValueError:
            raise current_error
        if legacy.get("schema_version") != PORTFOLIO_BACKTEST_PACK_POINTER_SCHEMA_VERSION:
            raise current_error
        return legacy


def _windows_basename_identity(value: Any) -> str | None:
    name = str(value or "")
    if not name or name != name.rstrip(" .") or ":" in name:
        return None
    if name in {".", ".."} or Path(name).name != name:
        return None
    device_name = name.split(".", 1)[0].casefold()
    if device_name in _WINDOWS_RESERVED_BASENAMES:
        return None
    return name.casefold()


def _valid_pack_basename(value: Any) -> bool:
    identity = _windows_basename_identity(value)
    pointer_identity = _windows_basename_identity(DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE)
    return identity is not None and identity != pointer_identity


def _fixed_pointer_path(report_dir: Path | str) -> tuple[Path, Path]:
    directory = Path(report_dir).resolve()
    pointer = (directory / DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE).resolve()
    if pointer.parent != directory or pointer.name != DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE:
        raise ValueError("fixed pointer path invalid")
    return directory, pointer


def _fixed_pointer_publication_lock_path(pointer_path: Path) -> Path:
    lock_name = f".{pointer_path.name}.lock"
    if _windows_basename_identity(lock_name) is None:
        raise ValueError("fixed pointer lock path invalid")
    lock_path = pointer_path.with_name(lock_name)
    if lock_path.parent != pointer_path.parent or lock_path.name != lock_name:
        raise ValueError("fixed pointer lock path invalid")
    return lock_path


def _fixed_bundle_path(
    report_dir: Path | str,
    bundle_dir_name: Any,
) -> tuple[Path, Path] | None:
    directory, _pointer = _fixed_pointer_path(report_dir)
    if windows_safe_basename_identity(bundle_dir_name) is None:
        return None
    name = str(bundle_dir_name)
    bundle = directory / name
    try:
        resolved = bundle.resolve()
    except OSError:
        return None
    if resolved.parent != directory or resolved.name != name:
        return None
    return directory, bundle


def portfolio_backtest_bundle_manifest_bindings(
    pack: Mapping[str, Any],
    *,
    pack_file: str,
) -> dict[str, Any]:
    candidate = _mapping(pack.get("candidate"))
    return {
        "contract": _PORTFOLIO_BUNDLE_CONTRACT,
        "pack_file": pack_file,
        "pack_schema_version": str(pack.get("schema_version") or ""),
        "candidate_hash": str(candidate.get("candidate_hash") or ""),
        "pack_hash": str(pack.get("pack_hash") or ""),
        "evidence_hash": str(pack.get("evidence_hash") or ""),
        "pack_status": str(pack.get("status") or "UNKNOWN"),
        "promotion_status": str(pack.get("promotion_status") or "UNKNOWN"),
        "generated_at": _strict_int(pack.get("generated_at")),
    }


def portfolio_backtest_bundle_member_roles(
    pack: Mapping[str, Any],
    *,
    pack_file: str,
) -> dict[str, str]:
    roles = {pack_file: PORTFOLIO_BACKTEST_BUNDLE_PACK_ROLE}
    for record in required_internal_backtest_bundle_members(dict(pack)):
        roles[str(record.get("file") or "")] = str(record.get("role") or "")
    return roles


def pointer_publication_eligibility(
    report_dir: Path | str,
    output_path: Path | str,
) -> dict[str, Any]:
    directory, _pointer = _fixed_pointer_path(report_dir)
    raw_output = Path(output_path)
    raw_identity = _windows_basename_identity(raw_output.name)
    pointer_identity = _windows_basename_identity(DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE)
    if raw_identity is None:
        return {
            "status": "BLOCK",
            "blockers": ["pack_output_basename_invalid"],
            "publish": False,
        }
    if raw_identity == pointer_identity:
        return {
            "status": "BLOCK",
            "blockers": ["pack_output_collides_with_fixed_pointer"],
            "publish": False,
        }
    output = raw_output.resolve()
    if _windows_basename_identity(output.name) != raw_identity:
        return {
            "status": "BLOCK",
            "blockers": ["pack_output_basename_alias_invalid"],
            "publish": False,
        }
    if output.parent != directory:
        return {
            "status": "SKIP",
            "blockers": ["pack_output_outside_report_root"],
            "publish": False,
        }
    return {"status": "PASS", "blockers": [], "publish": True}


def _build_pointer(pack_file: str, pack_file_sha256: str, pack: dict[str, Any]) -> dict[str, Any]:
    candidate = _mapping(pack.get("candidate"))
    content = {
        "schema_version": PORTFOLIO_BACKTEST_PACK_POINTER_SCHEMA_VERSION,
        "status": _POINTER_STATUS,
        "pack_file": pack_file,
        "pack_file_sha256": pack_file_sha256,
        "pack_schema_version": str(pack.get("schema_version") or ""),
        "candidate_hash": str(candidate.get("candidate_hash") or ""),
        "pack_hash": str(pack.get("pack_hash") or ""),
        "evidence_hash": str(pack.get("evidence_hash") or ""),
        "pack_status": str(pack.get("status") or "UNKNOWN"),
        "promotion_status": str(pack.get("promotion_status") or "UNKNOWN"),
        "generated_at": _strict_int(pack.get("generated_at")),
        "research_only": True,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "automatic_paper_activation_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {**content, "pointer_hash": _canonical_hash(content)}


def verify_portfolio_backtest_pack_pointer(
    pointer: dict[str, Any] | None,
    *,
    pack: dict[str, Any] | None,
    pack_file_sha256: str,
) -> dict[str, Any]:
    blockers: list[str] = []
    if not isinstance(pointer, Mapping):
        blockers.append("pointer_payload_not_object")
    if not isinstance(pack, Mapping):
        blockers.append("pointer_pack_not_object")
    payload = _mapping(pointer)
    frozen_pack = _mapping(pack)
    if set(payload) != _POINTER_V1_FIELDS:
        blockers.append("pointer_field_contract_invalid")
    expected_pointer_hash = str(payload.get("pointer_hash") or "")
    pointer_content = dict(payload)
    pointer_content.pop("pointer_hash", None)
    if not _is_sha256(expected_pointer_hash) or _canonical_hash(pointer_content) != expected_pointer_hash:
        blockers.append("pointer_hash_invalid")
    if payload.get("schema_version") != PORTFOLIO_BACKTEST_PACK_POINTER_SCHEMA_VERSION:
        blockers.append("pointer_schema_invalid")
    if payload.get("status") != _POINTER_STATUS:
        blockers.append("pointer_status_invalid")

    pack_file = str(payload.get("pack_file") or "")
    if not _valid_pack_basename(pack_file):
        blockers.append("pointer_pack_basename_invalid")
    declared_file_sha = str(payload.get("pack_file_sha256") or "")
    if not _is_sha256(declared_file_sha) or declared_file_sha != pack_file_sha256:
        blockers.append("pointer_pack_file_sha256_mismatch")

    try:
        pack_verification = _mapping(verify_internal_backtest_pack(frozen_pack))
    except Exception:
        pack_verification = {}
        blockers.append("pointer_pack_verification_exception")
    if pack_verification.get("status") != "PASS":
        blockers.append("pointer_pack_verification_blocked")
    if (
        frozen_pack.get("schema_version")
        == PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION
        and pack_verification.get("return_quality_source_integrity_status") != "PASS"
    ):
        blockers.append("pointer_return_quality_source_integrity_blocked")
    blockers.extend(_authority_violations(frozen_pack, "pack"))
    candidate_value = frozen_pack.get("candidate")
    if not isinstance(candidate_value, Mapping):
        blockers.append("pointer_pack_candidate_not_object")
    candidate = _mapping(candidate_value)
    bindings = {
        "pack_schema_version": str(frozen_pack.get("schema_version") or ""),
        "candidate_hash": str(candidate.get("candidate_hash") or ""),
        "pack_hash": str(frozen_pack.get("pack_hash") or ""),
        "evidence_hash": str(frozen_pack.get("evidence_hash") or ""),
        "pack_status": str(frozen_pack.get("status") or "UNKNOWN"),
        "promotion_status": str(frozen_pack.get("promotion_status") or "UNKNOWN"),
    }
    for field, expected in bindings.items():
        if str(payload.get(field) or "") != expected:
            blockers.append(f"pointer_{field}_mismatch")
    if not _is_sha256(bindings["pack_hash"]):
        blockers.append("pointer_pack_hash_invalid")
    if not _is_sha256(bindings["evidence_hash"]):
        blockers.append("pointer_evidence_hash_invalid")
    pointer_generated_at = _strict_int(payload.get("generated_at"))
    pack_generated_at = _strict_int(frozen_pack.get("generated_at"))
    if pointer_generated_at is None or pack_generated_at is None:
        blockers.append("pointer_generated_at_invalid")
    elif pointer_generated_at != pack_generated_at:
        blockers.append("pointer_generated_at_mismatch")

    for field, expected in (
        ("research_only", True),
        ("profitability_proven", False),
        ("performance_claim_allowed", False),
        ("parameter_selection_allowed", False),
        ("automatic_paper_activation_allowed", False),
        ("paper_authorized", False),
        ("live_order_allowed", False),
    ):
        if payload.get(field) is not expected:
            blockers.append(f"pointer_scope_invalid:{field}")
    blockers.extend(_authority_violations(payload))
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "pack_verification_status": str(pack_verification.get("status") or "BLOCK"),
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _publish_portfolio_backtest_pack_pointer(
    report_dir: Path | str,
    pack_path: Path | str,
    *,
    expected_pack_hash: str | None = None,
    expected_evidence_hash: str | None = None,
    expected_pack_file_sha256: str | None = None,
    expected_pack_status: str | None = None,
) -> dict[str, Any]:
    eligibility = pointer_publication_eligibility(report_dir, pack_path)
    if eligibility.get("status") != "PASS":
        return {
            "status": "SKIPPED" if eligibility.get("status") == "SKIP" else "BLOCK",
            "blockers": list(eligibility.get("blockers") or []),
            "published": False,
        }
    directory, pointer_path = _fixed_pointer_path(report_dir)
    source_path = Path(pack_path).resolve()
    if source_path.parent != directory:
        return {"status": "BLOCK", "blockers": ["pack_parent_invalid"], "published": False}
    try:
        raw = _read_bounded_artifact(
            source_path,
            byte_limit=MAX_PUBLIC_PORTFOLIO_BACKTEST_PACK_BYTES,
            blocker=_PACK_SIZE_LIMIT_BLOCKER,
        )
        pack = _read_json_object(raw)
    except _ArtifactByteLimitExceeded as exc:
        return {"status": "BLOCK", "blockers": [exc.blocker], "published": False}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return {"status": "BLOCK", "blockers": ["pack_file_unavailable"], "published": False}

    pack_file_sha256 = _file_sha256(raw)
    if pack.get("schema_version") in {
        PORTFOLIO_INTERNAL_BACKTEST_PACK_V5_SCHEMA_VERSION,
        CURRENT_PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION,
    }:
        return {
            "status": "BLOCK",
            "blockers": ["pointer_v1_pack_schema_incompatible"],
            "published": False,
        }
    expected_bindings = {
        "pack_hash": expected_pack_hash,
        "evidence_hash": expected_evidence_hash,
        "pack_file_sha256": expected_pack_file_sha256,
        "pack_status": expected_pack_status,
    }
    provided = [value is not None for value in expected_bindings.values()]
    if any(provided) and not all(provided):
        return {
            "status": "BLOCK",
            "blockers": ["pointer_expected_binding_incomplete"],
            "published": False,
        }
    if all(provided):
        actual_bindings = {
            "pack_hash": str(pack.get("pack_hash") or ""),
            "evidence_hash": str(pack.get("evidence_hash") or ""),
            "pack_file_sha256": pack_file_sha256,
            "pack_status": str(pack.get("status") or "UNKNOWN"),
        }
        binding_blockers = [
            f"pointer_expected_{field}_mismatch"
            for field, expected in expected_bindings.items()
            if actual_bindings[field] != str(expected or "")
        ]
        if binding_blockers:
            return {
                "status": "BLOCK",
                "blockers": binding_blockers,
                "published": False,
                **actual_bindings,
            }
    pointer = _build_pointer(source_path.name, pack_file_sha256, pack)
    verification = verify_portfolio_backtest_pack_pointer(
        pointer,
        pack=pack,
        pack_file_sha256=pack_file_sha256,
    )
    if verification.get("status") != "PASS":
        return {
            "status": "BLOCK",
            "blockers": list(verification.get("blockers") or ["pointer_verification_blocked"]),
            "published": False,
        }

    temporary = pointer_path.with_name(f".{pointer_path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(pointer, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(pointer_path)
    except OSError:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        return {"status": "BLOCK", "blockers": ["pointer_atomic_write_failed"], "published": False}
    try:
        persisted_pointer_raw = _read_bounded_artifact(
            pointer_path,
            byte_limit=MAX_PORTFOLIO_BACKTEST_PACK_POINTER_BYTES,
            blocker=_POINTER_SIZE_LIMIT_BLOCKER,
        )
        persisted_pointer = _read_json_object(persisted_pointer_raw)
        persisted_pack_raw = _read_bounded_artifact(
            source_path,
            byte_limit=MAX_PUBLIC_PORTFOLIO_BACKTEST_PACK_BYTES,
            blocker=_PACK_SIZE_LIMIT_BLOCKER,
        )
    except _ArtifactByteLimitExceeded as exc:
        return {
            "status": "BLOCK",
            "blockers": [exc.blocker],
            "published": False,
        }
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return {
            "status": "BLOCK",
            "blockers": ["pointer_post_publish_read_failed"],
            "published": False,
        }
    if persisted_pointer != pointer or _file_sha256(persisted_pack_raw) != pack_file_sha256:
        return {
            "status": "BLOCK",
            "blockers": ["pointer_post_publish_binding_mismatch"],
            "published": False,
        }
    return {
        "status": "PUBLISHED",
        "blockers": [],
        "published": True,
        "pointer_hash": pointer["pointer_hash"],
        "pack_hash": pointer["pack_hash"],
        "evidence_hash": pointer["evidence_hash"],
        "pack_status": pointer["pack_status"],
        "pack_file_sha256": pointer["pack_file_sha256"],
    }


def publish_portfolio_backtest_pack_pointer(
    report_dir: Path | str,
    pack_path: Path | str,
    *,
    expected_pack_hash: str | None = None,
    expected_evidence_hash: str | None = None,
    expected_pack_file_sha256: str | None = None,
    expected_pack_status: str | None = None,
) -> dict[str, Any]:
    try:
        return _publish_portfolio_backtest_pack_pointer(
            report_dir,
            pack_path,
            expected_pack_hash=expected_pack_hash,
            expected_evidence_hash=expected_evidence_hash,
            expected_pack_file_sha256=expected_pack_file_sha256,
            expected_pack_status=expected_pack_status,
        )
    except Exception:
        return {
            "status": "BLOCK",
            "blockers": ["pointer_publication_unexpected_error"],
            "published": False,
        }


def _portfolio_backtest_bundle_semantics(bundle: Mapping[str, Any] | None) -> dict[str, Any]:
    blockers: list[str] = []
    payload = dict(bundle or {}) if isinstance(bundle, Mapping) else {}
    if payload.get("status") != "PASS":
        blockers.extend(
            f"bundle_read:{item}"
            for item in list(payload.get("blockers") or [])
            or ["artifact_bundle_verification_blocked"]
        )
        return {
            "status": "BLOCK",
            "blockers": list(dict.fromkeys(blockers)),
            "pack": {},
            "pack_file": "",
            "pack_file_sha256": "",
            "bundle_hash": "",
            "manifest_file_sha256": "",
            "core_verification_status": "BLOCK",
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    manifest = _mapping(payload.get("manifest"))
    bindings = _mapping(manifest.get("bindings"))
    records = [
        _mapping(item)
        for item in list(manifest.get("members") or [])
        if isinstance(item, Mapping)
    ]
    members = dict(payload.get("members") or {}) if isinstance(payload.get("members"), Mapping) else {}
    if set(bindings) != _PORTFOLIO_BUNDLE_BINDING_FIELDS:
        blockers.append("portfolio_bundle_binding_field_contract_invalid")
    if bindings.get("contract") != _PORTFOLIO_BUNDLE_CONTRACT:
        blockers.append("portfolio_bundle_contract_invalid")
    blockers.extend(_authority_violations(manifest, "bundle_manifest"))

    if len(records) != MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_MEMBER_COUNT:
        blockers.append("portfolio_bundle_member_inventory_count_invalid")
    records_by_role: dict[str, dict[str, Any]] = {}
    for record in records:
        role = str(record.get("role") or "")
        if not role or role in records_by_role:
            blockers.append("portfolio_bundle_member_role_duplicate_or_invalid")
        else:
            records_by_role[role] = record
    pack_record = records_by_role.get(PORTFOLIO_BACKTEST_BUNDLE_PACK_ROLE) or {}
    pack_file = str(pack_record.get("file") or "")
    pack_raw = members.get(pack_file)
    if not isinstance(pack_raw, bytes):
        blockers.append("portfolio_bundle_pack_member_unavailable")
        pack_raw = b""
    if len(pack_raw) > MAX_PORTFOLIO_INTERNAL_BACKTEST_PACK_BYTES:
        blockers.append("portfolio_bundle_pack_size_limit_exceeded")
    try:
        pack = _read_current_json_object(pack_raw)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        pack = {}
        blockers.append("portfolio_bundle_pack_json_invalid")
    if pack.get("schema_version") != CURRENT_PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION:
        blockers.append("portfolio_bundle_pack_schema_invalid")

    required = list(required_internal_backtest_bundle_members(pack))
    required_roles = {str(item.get("role") or "") for item in required}
    if set(records_by_role) != {
        PORTFOLIO_BACKTEST_BUNDLE_PACK_ROLE,
        *required_roles,
    }:
        blockers.append("portfolio_bundle_member_role_inventory_invalid")
    detached_artifacts: list[dict[str, Any]] = []
    for required_record in required:
        role = str(required_record.get("role") or "")
        manifest_record = records_by_role.get(role) or {}
        name = str(manifest_record.get("file") or "")
        raw = members.get(name)
        if not isinstance(raw, bytes):
            blockers.append(f"portfolio_bundle_member_unavailable:{role}")
            continue
        expected_limit = (
            MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES
            if role == "RESEARCH_REPORT"
            else MAX_PORTFOLIO_STATISTICAL_AUDIT_BYTES
            if role == "STATISTICAL_AUDIT"
            else 0
        )
        if expected_limit < 1 or len(raw) > expected_limit:
            blockers.append(f"portfolio_bundle_member_size_limit_exceeded:{role}")
        if name != str(required_record.get("file") or ""):
            blockers.append(f"portfolio_bundle_member_file_mismatch:{role}")
        if manifest_record.get("size") != required_record.get("byte_length"):
            blockers.append(f"portfolio_bundle_member_size_binding_mismatch:{role}")
        if str(manifest_record.get("sha256") or "") != str(
            required_record.get("sha256") or ""
        ):
            blockers.append(f"portfolio_bundle_member_sha256_binding_mismatch:{role}")
        detached_artifacts.append(
            {
                "role": role,
                "file": name,
                "sha256": str(manifest_record.get("sha256") or ""),
                "byte_length": manifest_record.get("size"),
                "raw_bytes": raw,
            }
        )

    expected_roles = portfolio_backtest_bundle_member_roles(pack, pack_file=pack_file)
    actual_roles = {
        str(record.get("file") or ""): str(record.get("role") or "")
        for record in records
    }
    if actual_roles != expected_roles:
        blockers.append("portfolio_bundle_member_file_role_contract_invalid")
    expected_bindings = portfolio_backtest_bundle_manifest_bindings(
        pack,
        pack_file=pack_file,
    )
    if bindings != expected_bindings:
        blockers.append("portfolio_bundle_pack_binding_mismatch")
    try:
        core_verification = _mapping(
            verify_internal_backtest_bundle(pack, detached_artifacts)
        )
    except Exception:
        core_verification = {}
        blockers.append("portfolio_bundle_core_verification_exception")
    if core_verification.get("status") != "PASS":
        blockers.append("portfolio_bundle_core_verification_blocked")
    if core_verification.get("artifact_contract_status") != "PASS":
        blockers.append("portfolio_bundle_core_artifact_contract_blocked")
    verified_quality = _mapping(core_verification.get("return_quality"))
    if (
        verified_quality.get("source_integrity_status") != "PASS"
        or verified_quality.get("numeric_claims_available") is not True
    ):
        blockers.append("portfolio_bundle_core_source_integrity_blocked")
    blockers = list(dict.fromkeys(blockers))
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "pack": pack,
        "pack_file": pack_file,
        "pack_file_sha256": hashlib.sha256(pack_raw).hexdigest() if pack_raw else "",
        "bundle_hash": str(manifest.get("bundle_hash") or ""),
        "manifest_file_sha256": str(payload.get("manifest_file_sha256") or ""),
        "core_verification_status": str(core_verification.get("status") or "BLOCK"),
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _build_bundle_pointer(
    *,
    bundle_dir: str,
    bundle_semantics: Mapping[str, Any],
) -> dict[str, Any]:
    pack = _mapping(bundle_semantics.get("pack"))
    candidate = _mapping(pack.get("candidate"))
    content = {
        "schema_version": PORTFOLIO_BACKTEST_BUNDLE_POINTER_SCHEMA_VERSION,
        "status": _BUNDLE_POINTER_STATUS,
        "bundle_dir": bundle_dir,
        "manifest_file": DEFAULT_BUNDLE_MANIFEST_FILE,
        "manifest_file_sha256": str(bundle_semantics.get("manifest_file_sha256") or ""),
        "bundle_hash": str(bundle_semantics.get("bundle_hash") or ""),
        "pack_file": str(bundle_semantics.get("pack_file") or ""),
        "pack_file_sha256": str(bundle_semantics.get("pack_file_sha256") or ""),
        "pack_schema_version": str(pack.get("schema_version") or ""),
        "candidate_hash": str(candidate.get("candidate_hash") or ""),
        "pack_hash": str(pack.get("pack_hash") or ""),
        "evidence_hash": str(pack.get("evidence_hash") or ""),
        "pack_status": str(pack.get("status") or "UNKNOWN"),
        "promotion_status": str(pack.get("promotion_status") or "UNKNOWN"),
        "generated_at": _strict_int(pack.get("generated_at")),
        "research_only": True,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "automatic_paper_activation_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {**content, "pointer_hash": _canonical_hash(content)}


def portfolio_backtest_bundle_pointer_receipt_bindings(
    *,
    bundle_dir_name: str,
    manifest_file_sha256: str,
    bundle_hash: str,
    pack_file: str,
    pack_file_sha256: str,
    pack: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the exact immutable fields a successful v2 publication must receipt.

    This pure helper deliberately reuses the canonical pointer builder so callers
    can bind a publisher receipt to the bundle directory as well as every pack
    identity field without duplicating the pointer hash algorithm.
    """

    pointer = _build_bundle_pointer(
        bundle_dir=str(bundle_dir_name),
        bundle_semantics={
            "manifest_file_sha256": str(manifest_file_sha256),
            "bundle_hash": str(bundle_hash),
            "pack_file": str(pack_file),
            "pack_file_sha256": str(pack_file_sha256),
            "pack": dict(pack or {}),
        },
    )
    return {
        "pointer_hash": pointer["pointer_hash"],
        "bundle_hash": pointer["bundle_hash"],
        "manifest_file_sha256": pointer["manifest_file_sha256"],
        "pack_file_sha256": pointer["pack_file_sha256"],
        "pack_hash": pointer["pack_hash"],
        "evidence_hash": pointer["evidence_hash"],
        "pack_status": pointer["pack_status"],
        "candidate_hash": pointer["candidate_hash"],
        "pack_schema_version": pointer["pack_schema_version"],
        "promotion_status": pointer["promotion_status"],
        "generated_at": pointer["generated_at"],
    }


def verify_portfolio_backtest_bundle_pointer(
    pointer: Mapping[str, Any] | None,
    *,
    bundle: Mapping[str, Any] | None,
    bundle_dir_name: str,
) -> dict[str, Any]:
    blockers: list[str] = []
    payload = _mapping(pointer)
    if not isinstance(pointer, Mapping):
        blockers.append("bundle_pointer_payload_not_object")
    if set(payload) != _POINTER_V2_FIELDS:
        blockers.append("bundle_pointer_field_contract_invalid")
    if payload.get("schema_version") != PORTFOLIO_BACKTEST_BUNDLE_POINTER_SCHEMA_VERSION:
        blockers.append("bundle_pointer_schema_invalid")
    if payload.get("status") != _BUNDLE_POINTER_STATUS:
        blockers.append("bundle_pointer_status_invalid")
    content = dict(payload)
    declared_pointer_hash = str(content.pop("pointer_hash", "") or "")
    if not _is_sha256(declared_pointer_hash) or _canonical_hash(content) != declared_pointer_hash:
        blockers.append("bundle_pointer_hash_invalid")
    if (
        windows_safe_basename_identity(payload.get("bundle_dir")) is None
        or str(payload.get("bundle_dir") or "") != bundle_dir_name
    ):
        blockers.append("bundle_pointer_directory_binding_invalid")
    if payload.get("manifest_file") != DEFAULT_BUNDLE_MANIFEST_FILE:
        blockers.append("bundle_pointer_manifest_file_invalid")

    semantics = _portfolio_backtest_bundle_semantics(bundle)
    if semantics.get("status") != "PASS":
        blockers.extend(
            f"bundle_pointer:{item}"
            for item in list(semantics.get("blockers") or [])
            or ["bundle_semantic_verification_blocked"]
        )
    pack = _mapping(semantics.get("pack"))
    candidate = _mapping(pack.get("candidate"))
    bindings = {
        "manifest_file_sha256": str(semantics.get("manifest_file_sha256") or ""),
        "bundle_hash": str(semantics.get("bundle_hash") or ""),
        "pack_file": str(semantics.get("pack_file") or ""),
        "pack_file_sha256": str(semantics.get("pack_file_sha256") or ""),
        "pack_schema_version": str(pack.get("schema_version") or ""),
        "candidate_hash": str(candidate.get("candidate_hash") or ""),
        "pack_hash": str(pack.get("pack_hash") or ""),
        "evidence_hash": str(pack.get("evidence_hash") or ""),
        "pack_status": str(pack.get("status") or "UNKNOWN"),
        "promotion_status": str(pack.get("promotion_status") or "UNKNOWN"),
    }
    for field, expected in bindings.items():
        if str(payload.get(field) or "") != expected:
            blockers.append(f"bundle_pointer_{field}_mismatch")
    pointer_generated_at = _strict_int(payload.get("generated_at"))
    pack_generated_at = _strict_int(pack.get("generated_at"))
    if pointer_generated_at is None or pack_generated_at is None:
        blockers.append("bundle_pointer_generated_at_invalid")
    elif pointer_generated_at != pack_generated_at:
        blockers.append("bundle_pointer_generated_at_mismatch")
    if bindings["pack_schema_version"] != CURRENT_PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION:
        blockers.append("bundle_pointer_pack_schema_incompatible")
    for field, expected in (
        ("research_only", True),
        ("profitability_proven", False),
        ("performance_claim_allowed", False),
        ("parameter_selection_allowed", False),
        ("automatic_paper_activation_allowed", False),
        ("paper_authorized", False),
        ("live_order_allowed", False),
    ):
        if payload.get(field) is not expected:
            blockers.append(f"bundle_pointer_scope_invalid:{field}")
    blockers.extend(_authority_violations(payload, "bundle_pointer"))
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "bundle_verification_status": str(semantics.get("status") or "BLOCK"),
        "core_verification_status": str(semantics.get("core_verification_status") or "BLOCK"),
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def verify_persisted_portfolio_backtest_bundle_pointer(
    report_dir: Path | str,
    *,
    expected_bindings: Mapping[str, Any],
) -> dict[str, Any]:
    """Strictly reread the fixed v2 pointer and its exact immutable bundle."""

    try:
        directory, pointer_path = _fixed_pointer_path(report_dir)
        expected = dict(expected_bindings or {})
        expected_fields = {
            "pointer_hash",
            "bundle_hash",
            "manifest_file_sha256",
            "pack_file_sha256",
            "pack_hash",
            "evidence_hash",
            "pack_status",
            "candidate_hash",
            "pack_schema_version",
            "promotion_status",
            "generated_at",
        }
        if set(expected) != expected_fields:
            return {
                "status": "BLOCK",
                "blockers": ["persisted_bundle_pointer_expected_binding_invalid"],
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        pointer_raw = read_bounded_artifact(
            pointer_path,
            byte_limit=MAX_PORTFOLIO_BACKTEST_PACK_POINTER_BYTES,
            size_limit_blocker=_POINTER_SIZE_LIMIT_BLOCKER,
        )
        pointer = _read_current_json_object(pointer_raw)
        bundle_dir_name = str(pointer.get("bundle_dir") or "")
        fixed_bundle = _fixed_bundle_path(directory, bundle_dir_name)
        if fixed_bundle is None:
            return {
                "status": "BLOCK",
                "blockers": ["persisted_bundle_pointer_directory_invalid"],
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        bundle = _read_public_backtest_bundle(fixed_bundle[1])
        verification = verify_portfolio_backtest_bundle_pointer(
            pointer,
            bundle=bundle,
            bundle_dir_name=bundle_dir_name,
        )
        actual = {
            "pointer_hash": pointer.get("pointer_hash"),
            "bundle_hash": pointer.get("bundle_hash"),
            "manifest_file_sha256": pointer.get("manifest_file_sha256"),
            "pack_file_sha256": pointer.get("pack_file_sha256"),
            "pack_hash": pointer.get("pack_hash"),
            "evidence_hash": pointer.get("evidence_hash"),
            "pack_status": pointer.get("pack_status"),
            "candidate_hash": pointer.get("candidate_hash"),
            "pack_schema_version": pointer.get("pack_schema_version"),
            "promotion_status": pointer.get("promotion_status"),
            "generated_at": pointer.get("generated_at"),
        }
        blockers = list(verification.get("blockers") or [])
        if actual != expected:
            blockers.append("persisted_bundle_pointer_expected_binding_mismatch")
        blockers = list(dict.fromkeys(blockers))
        return {
            "status": "PASS" if not blockers else "BLOCK",
            "blockers": blockers,
            **actual,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    except ArtifactBundleByteLimitExceeded as exc:
        blockers = [exc.blocker]
    except ArtifactBundleError as exc:
        blockers = [f"persisted_bundle_pointer_read:{exc.blocker}"]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        blockers = ["persisted_bundle_pointer_unavailable"]
    except Exception:
        blockers = ["persisted_bundle_pointer_verification_failed"]
    return {
        "status": "BLOCK",
        "blockers": blockers,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _read_public_backtest_bundle(bundle_path: Path) -> dict[str, Any]:
    try:
        manifest_raw = read_bounded_artifact(
            bundle_path / DEFAULT_BUNDLE_MANIFEST_FILE,
            byte_limit=MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_MANIFEST_BYTES,
            size_limit_blocker="portfolio_backtest_bundle_manifest_size_limit_exceeded",
        )
        manifest = _read_current_json_object(manifest_raw)
        manifest_verification = verify_content_addressed_bundle_manifest(
            manifest,
            manifest_file=DEFAULT_BUNDLE_MANIFEST_FILE,
            max_member_count=MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_MEMBER_COUNT,
            max_member_bytes=MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_MEMBER_BYTES,
            max_total_bytes=MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_TOTAL_BYTES,
        )
        if manifest_verification.get("status") != "PASS":
            return {
                "status": "BLOCK",
                "blockers": list(
                    manifest_verification.get("blockers")
                    or ["portfolio_backtest_bundle_manifest_invalid"]
                ),
                "members": {},
            }
        records_by_role = {
            str(record.get("role") or ""): record
            for record in list(manifest_verification.get("member_records") or [])
        }
        role_limits = {
            PORTFOLIO_BACKTEST_BUNDLE_PACK_ROLE: MAX_PORTFOLIO_INTERNAL_BACKTEST_PACK_BYTES,
            "RESEARCH_REPORT": MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES,
            "STATISTICAL_AUDIT": MAX_PORTFOLIO_STATISTICAL_AUDIT_BYTES,
        }
        if set(records_by_role) != set(role_limits):
            return {
                "status": "BLOCK",
                "blockers": ["portfolio_bundle_member_role_inventory_invalid"],
                "members": {},
            }
        for role, byte_limit in role_limits.items():
            name = str(records_by_role[role].get("file") or "")
            read_bounded_artifact(
                bundle_path / name,
                byte_limit=byte_limit,
                size_limit_blocker=f"portfolio_backtest_bundle_member_size_limit_exceeded:{role}",
            )
    except ArtifactBundleByteLimitExceeded as exc:
        return {"status": "BLOCK", "blockers": [exc.blocker], "members": {}}
    except ArtifactBundleError as exc:
        return {"status": "BLOCK", "blockers": [exc.blocker], "members": {}}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return {
            "status": "BLOCK",
            "blockers": ["portfolio_backtest_bundle_preflight_failed"],
            "members": {},
        }
    return read_immutable_artifact_bundle(
        bundle_path,
        manifest_file=DEFAULT_BUNDLE_MANIFEST_FILE,
        max_manifest_bytes=MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_MANIFEST_BYTES,
        max_member_count=MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_MEMBER_COUNT,
        max_member_bytes=MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_MEMBER_BYTES,
        max_total_bytes=MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_TOTAL_BYTES,
    )


def _read_valid_current_bundle_pointer(
    directory: Path,
    pointer_path: Path,
) -> dict[str, Any] | None:
    try:
        raw = _read_bounded_artifact(
            pointer_path,
            byte_limit=MAX_PORTFOLIO_BACKTEST_PACK_POINTER_BYTES,
            blocker=_POINTER_SIZE_LIMIT_BLOCKER,
        )
        pointer = _read_current_json_object(raw)
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        _ArtifactByteLimitExceeded,
    ):
        return None
    if pointer.get("schema_version") != PORTFOLIO_BACKTEST_BUNDLE_POINTER_SCHEMA_VERSION:
        return None
    name = str(pointer.get("bundle_dir") or "")
    fixed = _fixed_bundle_path(directory, name)
    if fixed is None:
        return None
    bundle = _read_public_backtest_bundle(fixed[1])
    verification = verify_portfolio_backtest_bundle_pointer(
        pointer,
        bundle=bundle,
        bundle_dir_name=name,
    )
    return pointer if verification.get("status") == "PASS" else None


def publish_portfolio_backtest_bundle_pointer(
    report_dir: Path | str,
    bundle_dir: Path | str,
    *,
    expected_bundle_hash: str | None = None,
    expected_manifest_file_sha256: str | None = None,
    expected_pack_file_sha256: str | None = None,
    expected_pack_hash: str | None = None,
    expected_evidence_hash: str | None = None,
    expected_pack_status: str | None = None,
) -> dict[str, Any]:
    try:
        directory, pointer_path = _fixed_pointer_path(report_dir)
        raw_bundle = Path(bundle_dir)
        raw_name = raw_bundle.name
        fixed = _fixed_bundle_path(directory, raw_name)
        if fixed is None or raw_bundle.resolve() != fixed[1].resolve():
            return {
                "status": "BLOCK",
                "blockers": ["bundle_pointer_bundle_path_invalid"],
                "published": False,
            }
        bundle_path = fixed[1]
        bundle = _read_public_backtest_bundle(bundle_path)
        semantics = _portfolio_backtest_bundle_semantics(bundle)
        if semantics.get("status") != "PASS":
            return {
                "status": "BLOCK",
                "blockers": list(semantics.get("blockers") or ["bundle_verification_blocked"]),
                "published": False,
            }
        actual_expected_bindings = {
            "bundle_hash": str(semantics.get("bundle_hash") or ""),
            "manifest_file_sha256": str(semantics.get("manifest_file_sha256") or ""),
            "pack_file_sha256": str(semantics.get("pack_file_sha256") or ""),
            "pack_hash": str(_mapping(semantics.get("pack")).get("pack_hash") or ""),
            "evidence_hash": str(_mapping(semantics.get("pack")).get("evidence_hash") or ""),
            "pack_status": str(_mapping(semantics.get("pack")).get("status") or "UNKNOWN"),
        }
        expected_bindings = {
            "bundle_hash": expected_bundle_hash,
            "manifest_file_sha256": expected_manifest_file_sha256,
            "pack_file_sha256": expected_pack_file_sha256,
            "pack_hash": expected_pack_hash,
            "evidence_hash": expected_evidence_hash,
            "pack_status": expected_pack_status,
        }
        provided = [value is not None for value in expected_bindings.values()]
        if any(provided) and not all(provided):
            return {
                "status": "BLOCK",
                "blockers": ["bundle_pointer_expected_binding_incomplete"],
                "published": False,
            }
        if all(provided):
            mismatches = [
                f"bundle_pointer_expected_{field}_mismatch"
                for field, expected in expected_bindings.items()
                if actual_expected_bindings[field] != str(expected or "")
            ]
            if mismatches:
                return {
                    "status": "BLOCK",
                    "blockers": mismatches,
                    "published": False,
                    **actual_expected_bindings,
                }
        pointer = _build_bundle_pointer(
            bundle_dir=bundle_path.name,
            bundle_semantics=semantics,
        )
        verification = verify_portfolio_backtest_bundle_pointer(
            pointer,
            bundle=bundle,
            bundle_dir_name=bundle_path.name,
        )
        if verification.get("status") != "PASS":
            return {
                "status": "BLOCK",
                "blockers": list(verification.get("blockers") or ["bundle_pointer_verification_blocked"]),
                "published": False,
            }

        lock_path = _fixed_pointer_publication_lock_path(pointer_path)
        try:
            lock_handle = lock_path.open("xb")
        except FileExistsError:
            return {
                "status": "BLOCK",
                "blockers": ["pointer_publication_locked"],
                "published": False,
            }
        except OSError:
            return {
                "status": "BLOCK",
                "blockers": ["pointer_publication_lock_failed"],
                "published": False,
            }
        result: dict[str, Any] | None = None
        try:
            try:
                lock_handle.flush()
                os.fsync(lock_handle.fileno())
            finally:
                lock_handle.close()

            existing_pointer = _read_valid_current_bundle_pointer(directory, pointer_path)
            if existing_pointer is not None:
                existing_generated_at = _strict_int(existing_pointer.get("generated_at"))
                next_generated_at = _strict_int(pointer.get("generated_at"))
                if existing_generated_at is not None and next_generated_at is not None:
                    if existing_generated_at > next_generated_at:
                        result = {
                            "status": "BLOCK",
                            "blockers": ["bundle_pointer_stale_publication_blocked"],
                            "published": False,
                        }
                    elif existing_generated_at == next_generated_at:
                        if existing_pointer != pointer:
                            result = {
                                "status": "BLOCK",
                                "blockers": ["bundle_pointer_same_timestamp_conflict"],
                                "published": False,
                            }
                        else:
                            result = {
                                "status": "EXISTING_IDENTICAL",
                                "blockers": [],
                                "published": False,
                                "pointer_hash": pointer["pointer_hash"],
                                **actual_expected_bindings,
                                "candidate_hash": pointer["candidate_hash"],
                                "pack_schema_version": pointer["pack_schema_version"],
                                "promotion_status": pointer["promotion_status"],
                                "generated_at": pointer["generated_at"],
                            }

            if result is None:
                temporary = pointer_path.with_name(f".{pointer_path.name}.{uuid.uuid4().hex}.tmp")
                try:
                    raw_pointer = json.dumps(pointer, ensure_ascii=False, indent=2).encode("utf-8")
                    with temporary.open("xb") as handle:
                        handle.write(raw_pointer)
                        handle.flush()
                        os.fsync(handle.fileno())
                    temporary.replace(pointer_path)
                except OSError:
                    try:
                        temporary.unlink(missing_ok=True)
                    except OSError:
                        result = {
                            "status": "BLOCK",
                            "blockers": ["bundle_pointer_temporary_cleanup_failed"],
                            "published": False,
                        }
                    else:
                        result = {
                            "status": "BLOCK",
                            "blockers": ["bundle_pointer_atomic_write_failed"],
                            "published": False,
                        }
            if result is None:
                try:
                    persisted_raw = _read_bounded_artifact(
                        pointer_path,
                        byte_limit=MAX_PORTFOLIO_BACKTEST_PACK_POINTER_BYTES,
                        blocker=_POINTER_SIZE_LIMIT_BLOCKER,
                    )
                    persisted_pointer = _read_current_json_object(persisted_raw)
                    persisted_bundle = _read_public_backtest_bundle(bundle_path)
                except _ArtifactByteLimitExceeded as exc:
                    result = {"status": "BLOCK", "blockers": [exc.blocker], "published": False}
                except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
                    result = {
                        "status": "BLOCK",
                        "blockers": ["bundle_pointer_post_publish_read_failed"],
                        "published": False,
                    }
            if result is None:
                persisted_verification = verify_portfolio_backtest_bundle_pointer(
                    persisted_pointer,
                    bundle=persisted_bundle,
                    bundle_dir_name=bundle_path.name,
                )
                if persisted_pointer != pointer or persisted_verification.get("status") != "PASS":
                    result = {
                        "status": "BLOCK",
                        "blockers": ["bundle_pointer_post_publish_binding_mismatch"],
                        "published": False,
                    }
                else:
                    result = {
                        "status": "PUBLISHED",
                        "blockers": [],
                        "published": True,
                        "pointer_hash": pointer["pointer_hash"],
                        **actual_expected_bindings,
                        "candidate_hash": pointer["candidate_hash"],
                        "pack_schema_version": pointer["pack_schema_version"],
                        "promotion_status": pointer["promotion_status"],
                        "generated_at": pointer["generated_at"],
                    }
        except Exception:
            result = {
                "status": "BLOCK",
                "blockers": ["bundle_pointer_publication_unexpected_error"],
                "published": False,
            }
        finally:
            try:
                lock_path.unlink()
            except OSError:
                result = {
                    "status": "BLOCK",
                    "blockers": ["pointer_publication_lock_cleanup_failed"],
                    "published": False,
                }
        return result or {
            "status": "BLOCK",
            "blockers": ["bundle_pointer_publication_unexpected_error"],
            "published": False,
        }
    except Exception:
        return {
            "status": "BLOCK",
            "blockers": ["bundle_pointer_publication_unexpected_error"],
            "published": False,
        }


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item)[:240] for item in value if isinstance(item, str) and item]


def _stage_quality_projection(value: Any) -> dict[str, Any]:
    source = dict(value or {}) if isinstance(value, dict) else {}
    sample = dict(source.get("sample") or {})
    statistical_claim = dict(source.get("statistical_claim") or {})
    quality_flags = dict(source.get("quality_flags") or {})
    return {
        "stage": str(source.get("stage") or "UNKNOWN")[:32],
        "evidence_status": str(source.get("evidence_status") or "UNKNOWN")[:32],
        "benchmark_excess_status": str(
            source.get("benchmark_excess_status") or "UNKNOWN"
        )[:32],
        "benchmark_excess_basis": str(
            source.get("benchmark_excess_basis") or "UNKNOWN"
        )[:80],
        "strategy_return_pct": _number(source.get("strategy_return_pct")),
        "benchmark_return_pct": _number(source.get("benchmark_return_pct")),
        "benchmark_excess_return_pct": _number(source.get("benchmark_excess_return_pct")),
        "reported_benchmark_excess_return_pct": _number(
            source.get("reported_benchmark_excess_return_pct")
        ),
        "strategy_max_drawdown_pct": _number(source.get("strategy_max_drawdown_pct")),
        "benchmark_max_drawdown_pct": _number(source.get("benchmark_max_drawdown_pct")),
        "drawdown_improvement_pct": _number(source.get("drawdown_improvement_pct")),
        "sample": {
            "evaluated_rows": _strict_int(sample.get("evaluated_rows")),
            "order_event_count": _strict_int(sample.get("order_event_count")),
            "decision_event_count": _strict_int(sample.get("decision_event_count")),
            "paired_return_observation_count": _strict_int(
                sample.get("paired_return_observation_count")
            ),
        },
        "statistical_claim": {
            "status": str(statistical_claim.get("status") or "UNKNOWN")[:32],
            "observed_strategy_compound_return_pct": _number(
                statistical_claim.get("observed_strategy_compound_return_pct")
            ),
            "observed_benchmark_compound_return_pct": _number(
                statistical_claim.get("observed_benchmark_compound_return_pct")
            ),
            "observed_compound_excess_return_pct": _number(
                statistical_claim.get("observed_compound_excess_return_pct")
            ),
            "blockers": _strings(statistical_claim.get("blockers")),
        },
        "quality_flags": {
            "strategy_return_positive": (
                quality_flags.get("strategy_return_positive")
                if isinstance(quality_flags.get("strategy_return_positive"), bool)
                else None
            ),
            "benchmark_excess_positive": (
                quality_flags.get("benchmark_excess_positive")
                if isinstance(quality_flags.get("benchmark_excess_positive"), bool)
                else None
            ),
        },
    }


def _quality_projection(value: Any) -> dict[str, Any] | None:
    source = dict(value or {}) if isinstance(value, dict) else {}
    if _authority_violations(source, "return_quality"):
        return None
    quality_schema = str(source.get("schema_version") or "")
    if quality_schema not in {
        BACKTEST_RETURN_QUALITY_SCHEMA_VERSION,
        BACKTEST_RETURN_QUALITY_V2_SCHEMA_VERSION,
        CURRENT_BACKTEST_RETURN_QUALITY_SCHEMA_VERSION,
        BACKTEST_RETURN_QUALITY_V3_SCHEMA_VERSION,
    }:
        return None
    if quality_schema == BACKTEST_RETURN_QUALITY_V3_SCHEMA_VERSION and (
        source.get("source_integrity_status") != "PASS"
        or source.get("numeric_claims_available") is not True
    ):
        return None
    summary = dict(source.get("summary") or {})
    stages = dict(source.get("stages") or {})
    cost_after = dict(source.get("cost_after") or {})
    baseline = dict(cost_after.get("baseline_model") or {})
    stress_contract = dict(cost_after.get("stress_contract") or {})
    scenarios = []
    for raw in list(cost_after.get("stress_scenarios") or []):
        scenario = dict(raw or {}) if isinstance(raw, dict) else {}
        scenarios.append(
            {
                "label": str(scenario.get("label") or "UNKNOWN")[:80],
                "status": str(scenario.get("status") or "UNKNOWN")[:32],
                "contract_match": scenario.get("contract_match") if isinstance(scenario.get("contract_match"), bool) else None,
                "fee_rate": _number(scenario.get("fee_rate")),
                "slippage_bps": _number(scenario.get("slippage_bps")),
                "return_pct": _number(scenario.get("return_pct")),
                "max_drawdown_pct": _number(scenario.get("max_drawdown_pct")),
            }
        )
    failures = dict(source.get("failure_conditions") or {})
    return {
        "schema_version": quality_schema,
        "status": str(source.get("status") or "UNKNOWN")[:32],
        "interpretation": "DESCRIPTIVE_HISTORICAL_EVIDENCE_ONLY",
        "summary": {
            "strategy_return_pct": _number(summary.get("strategy_return_pct")),
            "benchmark_return_pct": _number(summary.get("benchmark_return_pct")),
            "benchmark_excess_return_pct": _number(summary.get("benchmark_excess_return_pct")),
            "benchmark_excess_status": str(summary.get("benchmark_excess_status") or "UNKNOWN")[:32],
            "cost_after_return_pct": _number(summary.get("cost_after_return_pct")),
            "cost_after_status": str(summary.get("cost_after_status") or "UNKNOWN")[:32],
            "worst_stress_return_pct": _number(summary.get("worst_stress_return_pct")),
            "max_drawdown_pct": _number(summary.get("max_drawdown_pct")),
            "sample_size": _strict_int(summary.get("sample_size")),
            "sample_unit": str(summary.get("sample_unit") or "UNKNOWN")[:48],
            "evidence_stage": str(summary.get("evidence_stage") or "UNKNOWN")[:48],
        },
        "stages": {
            "validation": _stage_quality_projection(stages.get("validation")),
            "test": _stage_quality_projection(stages.get("test")),
        },
        "cost_after": {
            "status": str(cost_after.get("status") or "UNKNOWN")[:32],
            "baseline_model": {
                "status": str(baseline.get("status") or "UNKNOWN")[:32],
                "fee_rate": _number(baseline.get("fee_rate")),
                "slippage_bps": _number(baseline.get("slippage_bps")),
                "test_return_after_configured_costs_pct": _number(
                    baseline.get("test_return_after_configured_costs_pct")
                ),
                "configured_costs_declared_in_test_run": (
                    baseline.get("configured_costs_declared_in_test_run")
                    if isinstance(baseline.get("configured_costs_declared_in_test_run"), bool)
                    else None
                ),
            },
            "stress_contract": {
                "status": str(stress_contract.get("status") or "UNKNOWN")[:32],
                "expected_labels": _strings(stress_contract.get("expected_labels")),
                "reported_labels": _strings(stress_contract.get("reported_labels")),
            },
            "stress_scenarios": scenarios[:20],
            "worst_stress_return_pct": _number(cost_after.get("worst_stress_return_pct")),
            "worst_stress_max_drawdown_pct": _number(
                cost_after.get("worst_stress_max_drawdown_pct")
            ),
            "all_stress_returns_positive": (
                cost_after.get("all_stress_returns_positive")
                if isinstance(cost_after.get("all_stress_returns_positive"), bool)
                else None
            ),
        },
        "statistical_claim_status": str(source.get("statistical_claim_status") or "UNKNOWN")[:32],
        "failure_conditions": {
            "source_integrity": _strings(failures.get("source_integrity")),
            "observed": _strings(failures.get("observed")),
            "evidence_gaps": _strings(failures.get("evidence_gaps")),
            "promotion_gaps": _strings(failures.get("promotion_gaps")),
        },
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "automatic_paper_activation_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _forward_promotion_projection_v2(pack: dict[str, Any]) -> dict[str, Any] | None:
    if pack.get("schema_version") != PORTFOLIO_INTERNAL_BACKTEST_PACK_V6_SCHEMA_VERSION:
        return None
    source = pack.get("forward_promotion_evidence")
    if not isinstance(source, dict):
        return None
    if source.get("schema_version") != PORTFOLIO_INTERNAL_FORWARD_EVIDENCE_V2_SCHEMA_VERSION:
        return None
    verification = _mapping(verify_internal_forward_evidence(source))
    if verification.get("status") != "PASS":
        return None
    if _authority_violations(source, "forward_promotion_evidence"):
        return None

    source_integrity_status = source.get("source_integrity_status")
    forward_evidence_status = source.get("forward_evidence_status")
    if source_integrity_status not in {"PASS", "BLOCK"}:
        return None
    if verification.get("source_integrity_status") != source_integrity_status:
        return None
    if forward_evidence_status not in {
        "COLLECTING",
        "RESEARCH_REVIEW_READY",
        "RESEARCH_REVIEW_BLOCKED",
        "BLOCK",
    }:
        return None
    if pack.get("forward_evidence_status") != forward_evidence_status:
        return None

    performance = source.get("performance_summary")
    readiness = source.get("readiness")
    audit = source.get("forward_statistical_audit")
    historical = source.get("historical_statistical_contract_source")
    scope = source.get("validation_scope")
    if not all(
        isinstance(value, dict)
        for value in (performance, readiness, audit, historical, scope)
    ):
        return None
    if (
        audit.get("schema_version")
        != PORTFOLIO_FORWARD_STATISTICAL_AUDIT_V2_SCHEMA_VERSION
        or readiness.get("schema_version")
        != PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION
    ):
        return None
    maturity = audit.get("maturity")
    series = audit.get("series_evidence")
    stage = audit.get("stage")
    decision = audit.get("decision_window")
    audit_binding = audit.get("input_binding")
    if not all(
        isinstance(value, dict)
        for value in (maturity, series, stage, decision, audit_binding)
    ):
        return None
    prefix = decision.get("first_joint_maturity_prefix")
    risk = decision.get("risk_acceptance")
    if not isinstance(prefix, dict) or not isinstance(risk, dict):
        return None
    if (
        decision.get("schema_version") != PORTFOLIO_FORWARD_DECISION_WINDOW_SCHEMA_VERSION
        or decision.get("policy") != PORTFOLIO_FORWARD_DECISION_POLICY
        or decision.get("later_settlements_used") is not False
        or risk.get("schema_version") != PORTFOLIO_FORWARD_RISK_ACCEPTANCE_SCHEMA_VERSION
    ):
        return None

    decision_hash = decision.get("decision_hash")
    stage_hash = stage.get("stage_hash")
    risk_hash = risk.get("risk_hash")
    full_series_hash = series.get("series_hash")
    decision_series_hash = decision.get("decision_series_hash")
    if not all(
        _is_sha256(value)
        for value in (decision_hash, risk_hash, full_series_hash)
    ):
        return None
    maturity_status = maturity.get("status")
    prefix_status = prefix.get("status")
    if maturity_status not in {"DUE", "NOT_DUE"} or prefix_status != maturity_status:
        return None

    counts = {
        "forward_outcomes": _strict_int(maturity.get("forward_outcomes")),
        "required_forward_outcomes": _strict_int(
            maturity.get("required_forward_outcomes")
        ),
        "remaining_forward_outcomes": _strict_int(
            maturity.get("remaining_forward_outcomes")
        ),
        "executed_rebalances": _strict_int(maturity.get("executed_rebalances")),
        "required_executed_rebalances": _strict_int(
            maturity.get("required_executed_rebalances")
        ),
        "remaining_executed_rebalances": _strict_int(
            maturity.get("remaining_executed_rebalances")
        ),
        "full_settlement_count": _strict_int(series.get("settlement_count")),
        "prefix_settlement_count": _strict_int(prefix.get("settlement_count")),
        "prefix_outcome_period_count": _strict_int(
            prefix.get("outcome_period_count")
        ),
        "prefix_rebalance_execution_count": _strict_int(
            prefix.get("rebalance_execution_count")
        ),
    }
    if any(value is None for value in counts.values()):
        return None
    if (
        counts["required_forward_outcomes"] < 1
        or counts["required_executed_rebalances"] < 1
        or counts["full_settlement_count"] < counts["prefix_settlement_count"]
    ):
        return None
    first_due_index = prefix.get("first_due_settlement_index")
    first_due_date = str(prefix.get("first_due_settlement_date") or "")
    first_due_hash = str(prefix.get("first_due_settlement_hash") or "")
    if maturity_status == "DUE":
        if (
            _strict_int(first_due_index) is None
            or not first_due_date
            or not _is_sha256(first_due_hash)
            or counts["prefix_settlement_count"] != first_due_index + 1
            or not _is_sha256(decision_series_hash)
            or not _is_sha256(stage_hash)
            or stage.get("status") not in {"PASS", "BLOCK"}
            or risk.get("status") not in {"PASS", "BLOCK"}
        ):
            return None
    elif (
        first_due_index is not None
        or first_due_date
        or first_due_hash
        or counts["prefix_settlement_count"] != 0
        or str(decision_series_hash or "")
        or str(stage_hash or "")
        or stage
        or risk.get("status") != "NOT_DUE"
    ):
        return None

    decision_status = str(decision.get("decision_status") or "")
    research_action = str(decision.get("research_action") or "")
    readiness_status = str(readiness.get("status") or "")
    readiness_promotion_status = str(readiness.get("promotion_status") or "")
    if maturity_status == "NOT_DUE":
        expected_state = (
            "NOT_DUE",
            "COLLECT_MORE",
            "NOT_DUE",
            "COLLECTING",
            "BLOCK",
            "COLLECTING",
        )
    elif stage.get("status") == "PASS" and risk.get("status") == "PASS":
        expected_state = (
            "PASS",
            "REVIEW_REQUIRED",
            "PASS",
            "RESEARCH_REVIEW_READY",
            "REVIEW_REQUIRED",
            "RESEARCH_REVIEW_READY",
        )
    else:
        expected_state = (
            "BLOCK",
            "STOP_RESEARCH",
            "BLOCK",
            "RESEARCH_REVIEW_BLOCKED",
            "BLOCK",
            "RESEARCH_REVIEW_BLOCKED",
        )
    if (
        decision_status,
        research_action,
        str(audit.get("status") or ""),
        readiness_status,
        readiness_promotion_status,
        forward_evidence_status,
    ) != expected_state:
        return None
    if (
        str(audit_binding.get("decision_hash") or "") != decision_hash
        or str(audit_binding.get("decision_series_hash") or "")
        != decision_series_hash
        or str(audit_binding.get("risk_acceptance_hash") or "") != risk_hash
        or str(audit_binding.get("forward_series_hash") or "") != full_series_hash
        or str(decision.get("stage_hash") or "") != str(stage_hash or "")
        or str(decision.get("risk_acceptance_hash") or "") != risk_hash
        or str(risk.get("decision_series_hash") or "") != decision_series_hash
    ):
        return None
    for field in (
        "first_due_settlement_index",
        "first_due_settlement_date",
        "first_due_settlement_hash",
    ):
        if audit_binding.get(field) != prefix.get(field) or maturity.get(field) != prefix.get(field):
            return None
    risk_limit = _number(risk.get("required_max_drawdown_below_pct"))
    risk_drawdown = _number(risk.get("prefix_max_drawdown_pct"))
    if risk_limit is None or risk_limit <= 0.0:
        return None
    if maturity_status == "DUE" and risk_drawdown is None:
        return None
    if maturity_status == "NOT_DUE" and risk_drawdown is not None:
        return None

    return {
        "schema_version": PORTFOLIO_BACKTEST_FORWARD_PROMOTION_SUMMARY_V2_SCHEMA_VERSION,
        "status": forward_evidence_status,
        "source_integrity_status": source_integrity_status,
        "decision": {
            "policy": PORTFOLIO_FORWARD_DECISION_POLICY,
            "status": str(decision.get("status") or "UNKNOWN")[:32],
            "decision_status": decision_status,
            "research_action": research_action,
            "decision_hash": str(decision_hash),
            "later_settlements_used": False,
        },
        "maturity": {
            "status": maturity_status,
            **{
                key: counts[key]
                for key in (
                    "forward_outcomes",
                    "required_forward_outcomes",
                    "remaining_forward_outcomes",
                    "executed_rebalances",
                    "required_executed_rebalances",
                    "remaining_executed_rebalances",
                )
            },
            "both_thresholds_required": maturity.get("both_thresholds_required") is True,
            "first_due_settlement_index": first_due_index,
            "first_due_settlement_date": first_due_date or None,
            "first_due_settlement_hash": first_due_hash or None,
        },
        "frozen_prefix": {
            "status": prefix_status,
            "settlement_count": counts["prefix_settlement_count"],
            "outcome_period_count": counts["prefix_outcome_period_count"],
            "rebalance_execution_count": counts["prefix_rebalance_execution_count"],
            "decision_series_hash": str(decision_series_hash),
        },
        "audit": {
            "status": str(audit.get("status") or "UNKNOWN")[:32],
            "conclusion": str(audit.get("conclusion") or "")[:96],
            "verification_status": str(audit.get("verification_status") or "UNKNOWN")[:32],
            "semantic_recomputed": audit.get("semantic_recomputed") is True,
            "audit_hash": str(audit.get("audit_hash")) if _is_sha256(audit.get("audit_hash")) else None,
            "full_series_hash": str(full_series_hash),
            "stage": {
                "status": str(stage.get("status") or "NOT_DUE")[:32],
                "stage_hash": str(stage_hash) if _is_sha256(stage_hash) else None,
            },
            "risk_acceptance": {
                "status": str(risk.get("status") or "UNKNOWN")[:32],
                "risk_hash": str(risk_hash),
                "required_max_drawdown_below_pct": risk_limit,
                "prefix_max_drawdown_pct": risk_drawdown,
            },
        },
        "tail_observation": {
            "full_settlement_count": counts["full_settlement_count"],
            "frozen_prefix_settlement_count": counts["prefix_settlement_count"],
            "later_settlement_count": (
                counts["full_settlement_count"] - counts["prefix_settlement_count"]
            ),
            "full_series_hash": str(full_series_hash),
            "frozen_decision_hash": str(decision_hash),
            "later_settlements_descriptive_only": True,
        },
        "readiness_status": readiness_status,
        "readiness_promotion_status": readiness_promotion_status,
        "historical_contract_claim_status": str(
            historical.get("claim_status") or "UNKNOWN"
        )[:32],
        "blockers": _strings(source.get("blockers")),
        "promotion_blockers": _strings(pack.get("promotion_blockers")),
        "validation_scope": {
            "pack_validates_upstream_single_look_semantic_receipt": True,
            "settlement_database_reloaded_by_pack": False,
            "settlement_chain_independently_replayed_by_pack": False,
            "full_forward_rows_hash_bound": True,
            "first_joint_maturity_prefix_hash_bound": True,
            "decision_stage_and_risk_hashes_bound": True,
            "later_settlements_descriptive_only": True,
        },
        "manual_review_required": True,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "automatic_paper_activation_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _forward_promotion_projection(pack: dict[str, Any]) -> dict[str, Any] | None:
    pack_schema = pack.get("schema_version")
    if pack_schema == PORTFOLIO_INTERNAL_BACKTEST_PACK_V6_SCHEMA_VERSION:
        return _forward_promotion_projection_v2(pack)
    if pack_schema == PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION:
        return None
    if pack_schema not in {
        PORTFOLIO_INTERNAL_BACKTEST_PACK_V3_SCHEMA_VERSION,
        PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
        PORTFOLIO_INTERNAL_BACKTEST_PACK_V5_SCHEMA_VERSION,
    }:
        return None

    source = pack.get("forward_promotion_evidence")
    if not isinstance(source, dict):
        return None
    if source.get("schema_version") != PORTFOLIO_INTERNAL_FORWARD_EVIDENCE_SCHEMA_VERSION:
        return None
    if _authority_violations(source, "forward_promotion_evidence"):
        return None

    source_integrity_status = source.get("source_integrity_status")
    forward_evidence_status = source.get("forward_evidence_status")
    if source_integrity_status not in {"PASS", "BLOCK"}:
        return None
    if forward_evidence_status not in {
        "COLLECTING",
        "RESEARCH_REVIEW_READY",
        "RESEARCH_REVIEW_BLOCKED",
        "BLOCK",
    }:
        return None
    if pack.get("forward_evidence_status") != forward_evidence_status:
        return None

    performance = source.get("performance_summary")
    readiness = source.get("readiness")
    audit = source.get("forward_statistical_audit")
    historical = source.get("historical_statistical_contract_source")
    scope = source.get("validation_scope")
    if not all(isinstance(value, dict) for value in (performance, readiness, audit, historical, scope)):
        return None
    maturity = audit.get("maturity")
    series = audit.get("series_evidence")
    if not isinstance(maturity, dict) or not isinstance(series, dict):
        if source_integrity_status == "PASS":
            return None
        maturity = maturity if isinstance(maturity, dict) else {}
        series = series if isinstance(series, dict) else {}
    if (
        scope.get("settlement_database_reloaded_by_pack") is not False
        or scope.get("settlement_chain_independently_replayed_by_pack") is not False
        or scope.get("full_forward_rows_hash_bound") is not True
    ):
        return None

    counts = {
        "forward_outcomes": _strict_int(maturity.get("forward_outcomes")),
        "required_forward_outcomes": _strict_int(maturity.get("required_forward_outcomes")),
        "remaining_forward_outcomes": _strict_int(maturity.get("remaining_forward_outcomes")),
        "executed_rebalances": _strict_int(maturity.get("executed_rebalances")),
        "required_executed_rebalances": _strict_int(
            maturity.get("required_executed_rebalances")
        ),
        "remaining_executed_rebalances": _strict_int(
            maturity.get("remaining_executed_rebalances")
        ),
    }
    if source_integrity_status == "PASS" and any(value is None for value in counts.values()):
        return None
    maturity_status = maturity.get("status")
    if maturity_status not in {"DUE", "NOT_DUE"}:
        if source_integrity_status == "PASS":
            return None
        maturity_status = "UNKNOWN"

    audit_status = audit.get("status")
    readiness_status = readiness.get("status")
    readiness_promotion_status = readiness.get("promotion_status")
    historical_claim_status = historical.get("claim_status")
    if audit_status not in {"NOT_DUE", "PASS", "BLOCK"}:
        audit_status = "UNKNOWN"
    if readiness_status not in {
        "COLLECTING",
        "RESEARCH_REVIEW_READY",
        "RESEARCH_REVIEW_BLOCKED",
        "BLOCK",
    }:
        readiness_status = "UNKNOWN"
    if readiness_promotion_status not in {"BLOCK", "REVIEW_REQUIRED"}:
        readiness_promotion_status = "UNKNOWN"
    if historical_claim_status not in {"PASS", "BLOCK"}:
        historical_claim_status = "UNKNOWN"

    return {
        "schema_version": PORTFOLIO_BACKTEST_FORWARD_PROMOTION_SUMMARY_V1_SCHEMA_VERSION,
        "status": forward_evidence_status,
        "source_integrity_status": source_integrity_status,
        "maturity": {
            "status": maturity_status,
            **counts,
            "both_thresholds_required": maturity.get("both_thresholds_required") is True,
        },
        "audit": {
            "status": audit_status,
            "conclusion": str(audit.get("conclusion") or "")[:96],
            "verification_status": str(audit.get("verification_status") or "UNKNOWN")[:32],
            "semantic_recomputed": audit.get("semantic_recomputed") is True,
            "audit_hash": (
                str(audit.get("audit_hash")) if _is_sha256(audit.get("audit_hash")) else None
            ),
            "series_hash": (
                str(series.get("series_hash")) if _is_sha256(series.get("series_hash")) else None
            ),
        },
        "readiness_status": readiness_status,
        "readiness_promotion_status": readiness_promotion_status,
        "historical_contract_claim_status": historical_claim_status,
        "blockers": _strings(source.get("blockers")),
        "promotion_blockers": _strings(pack.get("promotion_blockers")),
        "validation_scope": {
            "pack_validates_upstream_semantic_receipt": True,
            "settlement_database_reloaded_by_pack": False,
            "settlement_chain_independently_replayed_by_pack": False,
            "full_forward_rows_hash_bound": True,
        },
        "manual_review_required": True,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "automatic_paper_activation_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _unknown_snapshot(
    blockers: list[str],
    *,
    schema_version: str = PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_SCHEMA_VERSION,
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "ok": False,
        "status": "UNKNOWN",
        "source_verification_status": "BLOCK",
        "blockers": list(dict.fromkeys(blockers or ["frozen_pack_pointer_unavailable"])),
        "generated_at": None,
        "pack_schema_version": None,
        "candidate_hash": None,
        "pack_hash": None,
        "evidence_hash": None,
        "pack_status": "UNKNOWN",
        "promotion_status": "UNKNOWN",
        "return_quality": None,
        "forward_promotion": None,
        "read_only": True,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "automatic_paper_activation_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _verified_pack_snapshot(
    pointer: Mapping[str, Any],
    pack: dict[str, Any],
    *,
    snapshot_schema_version: str = (
        PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_SCHEMA_VERSION
    ),
) -> dict[str, Any]:
    pack_schema = str(pack.get("schema_version") or "")
    coupling = _PACK_PUBLIC_EVIDENCE_COUPLING.get(pack_schema)
    if coupling is None:
        return _unknown_snapshot(
            ["pack_public_evidence_coupling_unknown"],
            schema_version=snapshot_schema_version,
        )
    if coupling.get("snapshot_schema") != snapshot_schema_version:
        return _unknown_snapshot(
            ["pack_public_snapshot_schema_coupling_invalid"],
            schema_version=snapshot_schema_version,
        )
    if coupling.get("source_bound_quality") is not True:
        return _unknown_snapshot(
            ["legacy_return_quality_not_source_bound"],
            schema_version=snapshot_schema_version,
        )
    raw_quality = pack.get("return_quality")
    if (
        not isinstance(raw_quality, dict)
        or raw_quality.get("schema_version") != coupling["quality_schema"]
    ):
        return _unknown_snapshot(
            ["return_quality_pack_schema_coupling_invalid"],
            schema_version=snapshot_schema_version,
        )
    return_quality = _quality_projection(raw_quality)
    if return_quality is None:
        return _unknown_snapshot(
            ["return_quality_unavailable"],
            schema_version=snapshot_schema_version,
        )
    forward_promotion = _forward_promotion_projection(pack)
    if coupling["forward_required"] and forward_promotion is None:
        return _unknown_snapshot(
            ["forward_promotion_summary_unavailable"],
            schema_version=snapshot_schema_version,
        )
    if not coupling["forward_required"] and forward_promotion is not None:
        return _unknown_snapshot(
            ["forward_promotion_pack_schema_coupling_invalid"],
            schema_version=snapshot_schema_version,
        )

    return {
        "schema_version": snapshot_schema_version,
        "ok": True,
        "status": "AVAILABLE",
        "source_verification_status": "PASS",
        "blockers": [],
        "generated_at": int(pointer.get("generated_at")),
        "pack_schema_version": str(pack.get("schema_version") or ""),
        "candidate_hash": str(_mapping(pack.get("candidate")).get("candidate_hash") or "") or None,
        "pack_hash": str(pack.get("pack_hash") or ""),
        "evidence_hash": str(pack.get("evidence_hash") or ""),
        "pack_status": str(pack.get("status") or "UNKNOWN"),
        "promotion_status": str(pack.get("promotion_status") or "UNKNOWN"),
        "return_quality": return_quality,
        "forward_promotion": forward_promotion,
        "read_only": True,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "automatic_paper_activation_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def project_verified_portfolio_backtest_return_quality_snapshot(
    pointer: Mapping[str, Any],
    pack: dict[str, Any],
    *,
    schema_version: str,
) -> dict[str, Any]:
    """Pure projection for an already verified pack/pointer pair.

    Historical callers may still request v3 explicitly; the fixed-pointer
    loader always emits the current v4 contract.
    """

    if schema_version not in {
        PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_V3_SCHEMA_VERSION,
        PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_SCHEMA_VERSION,
    }:
        return _unknown_snapshot(
            ["portfolio_backtest_snapshot_schema_invalid"],
            schema_version=str(schema_version or "UNKNOWN"),
        )
    try:
        return _verified_pack_snapshot(
            pointer,
            dict(pack or {}),
            snapshot_schema_version=schema_version,
        )
    except Exception:
        return _unknown_snapshot(
            ["portfolio_backtest_snapshot_projection_blocked"],
            schema_version=schema_version,
        )


def _load_portfolio_backtest_return_quality_snapshot(
    report_dir: Path | str,
) -> dict[str, Any]:
    try:
        directory, pointer_path = _fixed_pointer_path(report_dir)
        pointer_raw = _read_bounded_artifact(
            pointer_path,
            byte_limit=MAX_PORTFOLIO_BACKTEST_PACK_POINTER_BYTES,
            blocker=_POINTER_SIZE_LIMIT_BLOCKER,
        )
        pointer = _read_pointer_object_by_schema(pointer_raw)
    except _ArtifactByteLimitExceeded as exc:
        return _unknown_snapshot([exc.blocker])
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return _unknown_snapshot(["frozen_pack_pointer_unavailable"])

    pointer_schema = str(pointer.get("schema_version") or "")
    if pointer_schema == PORTFOLIO_BACKTEST_BUNDLE_POINTER_SCHEMA_VERSION:
        bundle_dir_name = str(pointer.get("bundle_dir") or "")
        fixed_bundle = _fixed_bundle_path(directory, bundle_dir_name)
        if fixed_bundle is None:
            return _unknown_snapshot(["frozen_bundle_pointer_basename_invalid"])
        bundle = _read_public_backtest_bundle(fixed_bundle[1])
        verification = verify_portfolio_backtest_bundle_pointer(
            pointer,
            bundle=bundle,
            bundle_dir_name=bundle_dir_name,
        )
        if verification.get("status") != "PASS":
            return _unknown_snapshot(
                list(verification.get("blockers") or ["frozen_bundle_verification_blocked"])
            )
        semantics = _portfolio_backtest_bundle_semantics(bundle)
        if semantics.get("status") != "PASS":
            return _unknown_snapshot(
                list(semantics.get("blockers") or ["frozen_bundle_semantics_blocked"])
            )
        return _verified_pack_snapshot(pointer, _mapping(semantics.get("pack")))

    if pointer_schema != PORTFOLIO_BACKTEST_PACK_POINTER_SCHEMA_VERSION:
        return _unknown_snapshot(["frozen_pack_pointer_schema_unsupported"])
    pack_file = str(pointer.get("pack_file") or "")
    if not _valid_pack_basename(pack_file):
        return _unknown_snapshot(["frozen_pack_pointer_basename_invalid"])
    pack_path = (directory / pack_file).resolve()
    if pack_path.parent != directory:
        return _unknown_snapshot(["frozen_pack_parent_invalid"])
    try:
        pack_raw = _read_bounded_artifact(
            pack_path,
            byte_limit=MAX_PUBLIC_PORTFOLIO_BACKTEST_PACK_BYTES,
            blocker=_PACK_SIZE_LIMIT_BLOCKER,
        )
        pack = _read_json_object(pack_raw)
    except _ArtifactByteLimitExceeded as exc:
        return _unknown_snapshot([exc.blocker])
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return _unknown_snapshot(["frozen_pack_unavailable"])

    verification = verify_portfolio_backtest_pack_pointer(
        pointer,
        pack=pack,
        pack_file_sha256=_file_sha256(pack_raw),
    )
    if verification.get("status") != "PASS":
        return _unknown_snapshot(
            list(verification.get("blockers") or ["frozen_pack_verification_blocked"])
        )
    return _verified_pack_snapshot(pointer, pack)


def load_portfolio_backtest_return_quality_snapshot(
    report_dir: Path | str,
) -> dict[str, Any]:
    try:
        return _load_portfolio_backtest_return_quality_snapshot(report_dir)
    except Exception:
        return _unknown_snapshot(["frozen_pack_processing_blocked"])
