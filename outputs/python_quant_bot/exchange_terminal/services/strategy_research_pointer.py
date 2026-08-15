from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import unicodedata
import uuid
from typing import Any, Callable

from .implementation_manifest import verify_implementation_manifest
from .execution_authority import authority_violations as canonical_authority_violations
from .strategy_research_failure_conditions import (
    STRATEGY_RESEARCH_FAILURE_CONDITIONS_SCHEMA_VERSION,
    STRATEGY_RESEARCH_FAILURE_CONDITIONS_SCHEMA_VERSION_V2,
    STRATEGY_RESEARCH_FAILURE_CONDITIONS_SCHEMA_VERSION_V3,
    STRATEGY_RESEARCH_FAILURE_CONDITIONS_SCHEMA_VERSION_V4,
    build_strategy_research_failure_conditions,
    build_strategy_research_failure_conditions_v2,
    build_strategy_research_failure_conditions_v3,
    build_strategy_research_failure_conditions_v4,
)
from .strategy_research_evidence import (
    IMPLEMENTATION_MANIFEST_REPORT_SCHEMA_VERSION,
    verify_strategy_research_report,
)
from .strategy_hypothesis_preregistration import (
    MECHANISM_FAILURE_EVIDENCE_STAGE_V2,
    MECHANISM_FAILURE_METRICS_V2,
    MECHANISM_FAILURE_OPERATORS_V2,
    MECHANISM_FAILURE_REQUIRED_ACTION_V2,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_REPORT_SCHEMA_VERSION,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SUMMARY_SCHEMA_VERSION,
    verify_strategy_hypothesis_preregistration,
)
from .strategy_research_currentness_facts import (
    STRATEGY_RESEARCH_CURRENTNESS_FACTS_SCHEMA_VERSION,
    build_strategy_research_currentness_facts,
)
from .strategy_preregistered_failure_admission import (
    MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
    PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
    STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION,
    STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION_V2,
    STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION_V3,
)
from .strategy_post_selection_replay_summary import (
    build_strategy_post_selection_replay_summary,
)
from .strategy_research_search_lineage import (
    STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION,
    STRATEGY_RESEARCH_SEARCH_LINEAGE_SCHEMA_VERSION,
    verify_strategy_research_search_lineage,
)


STRATEGY_RESEARCH_POINTER_SCHEMA_VERSION = "strategy-research-report-pointer-v1"
STRATEGY_RESEARCH_POINTER_PUBLICATION_EXPECTATION_SCHEMA_VERSION = (
    "strategy-research-pointer-publication-expectation-v1"
)
STRATEGY_LAB_FROZEN_EVIDENCE_SCHEMA_VERSION_V3 = "strategy-lab-frozen-evidence-v3"
STRATEGY_LAB_FROZEN_EVIDENCE_SCHEMA_VERSION_V4 = "strategy-lab-frozen-evidence-v4"
STRATEGY_LAB_FROZEN_EVIDENCE_SCHEMA_VERSION_V5 = "strategy-lab-frozen-evidence-v5"
STRATEGY_LAB_FROZEN_EVIDENCE_SCHEMA_VERSION_V6 = "strategy-lab-frozen-evidence-v6"
STRATEGY_LAB_FROZEN_EVIDENCE_SCHEMA_VERSION_V7 = "strategy-lab-frozen-evidence-v7"
STRATEGY_LAB_FROZEN_EVIDENCE_SCHEMA_VERSION = (
    STRATEGY_LAB_FROZEN_EVIDENCE_SCHEMA_VERSION_V7
)
STRATEGY_HYPOTHESIS_PREREGISTRATION_SUMMARY_SCHEMA_VERSION_V2 = (
    "strategy-hypothesis-preregistration-summary-v2"
)
STRATEGY_HYPOTHESIS_PREREGISTRATION_SUMMARY_SCHEMA_VERSION_V3 = (
    "strategy-hypothesis-preregistration-summary-v3"
)
STRATEGY_RESEARCH_SEARCH_LINEAGE_PUBLIC_SCHEMA_VERSION = (
    "strategy-research-search-lineage-public-v1"
)
_PUBLIC_REPORT_SCHEMA_CAPABILITIES: dict[int, dict[str, str | None]] = {
    3: {"evidence": "v3", "hypothesis": None, "replay": None, "admission": None, "failure": "v1"},
    4: {"evidence": "v3", "hypothesis": None, "replay": None, "admission": None, "failure": "v1"},
    5: {"evidence": "v3", "hypothesis": None, "replay": None, "admission": None, "failure": "v1"},
    6: {"evidence": "v3", "hypothesis": None, "replay": None, "admission": None, "failure": "v1"},
    7: {"evidence": "v3", "hypothesis": "v1", "replay": None, "admission": None, "failure": "v1"},
    8: {"evidence": "v3", "hypothesis": "v1", "replay": None, "admission": None, "failure": "v1"},
    9: {"evidence": "v3", "hypothesis": "v1", "replay": None, "admission": None, "failure": "v1"},
    10: {"evidence": "v3", "hypothesis": "v1", "replay": None, "admission": None, "failure": "v1"},
    11: {"evidence": "v5", "hypothesis": "v1", "replay": "v1", "admission": None, "failure": "v2"},
    12: {"evidence": "v5", "hypothesis": "v1", "replay": "v1", "admission": "v1", "failure": "v2"},
    13: {"evidence": "v6", "hypothesis": "v2", "replay": "v1", "admission": "v2", "failure": "v3"},
    14: {
        "evidence": "v7",
        "hypothesis": "v3",
        "replay": "v1",
        "admission": "v3",
        "failure": "v4",
        "search_lineage": "v1",
    },
}
_PUBLIC_CONDITION_KINDS = frozenset({"STANDARD", "MECHANISM_SPECIFIC"})
_PUBLIC_CONDITION_STATUSES = frozenset({"PASS", "BLOCK", "NOT_APPLICABLE", "NOT_DUE"})
_PUBLIC_EVIDENCE_STAGES = frozenset({
    MECHANISM_FAILURE_EVIDENCE_STAGE_V2,
    "PREREGISTERED_BLIND_SINGLE_USE",
    "NATURAL_FORWARD_MATURITY",
    "ANY",
})
_PUBLIC_REQUIRED_ACTIONS = frozenset({
    MECHANISM_FAILURE_REQUIRED_ACTION_V2,
    "RETIRE_OR_NEW_REGISTRATION",
    "RETIRE_HYPOTHESIS",
    "NEW_REGISTRATION_REQUIRED",
})
STRATEGY_SIGNAL_IMPLEMENTATION_CURRENTNESS_SCHEMA_VERSION = (
    "strategy-signal-implementation-currentness-v1"
)
STRATEGY_FULL_IMPLEMENTATION_CURRENTNESS_SCHEMA_VERSION = (
    "strategy-full-implementation-currentness-v1"
)
DEFAULT_STRATEGY_RESEARCH_POINTER_FILE = "current_strategy_research_report.json"
_POINTER_STATUS = "CURRENT_VERIFIED_STRATEGY_RESEARCH_REPORT"
_POINTER_FIELDS = {
    "schema_version",
    "status",
    "report_file",
    "report_file_sha256",
    "report_schema_version",
    "batch_spec_hash",
    "dataset_manifest_hash",
    "batch_run_hash",
    "governance_status",
    "created_at",
    "research_only",
    "descriptive_only",
    "profitability_proven",
    "performance_claim_allowed",
    "parameter_selection_allowed",
    "automatic_paper_activation_allowed",
    "paper_authorized",
    "live_order_allowed",
    "pointer_hash",
}
_PUBLICATION_EXPECTATION_FIELDS = {
    "schema_version",
    "report_file",
    "report_hash",
    "report_file_sha256",
    "report_file_size_bytes",
    "report_schema_version",
    "batch_spec_hash",
    "dataset_manifest_hash",
    "batch_run_hash",
    "governance_status",
    "created_at",
    "research_only",
    "paper_authorized",
    "live_order_allowed",
    "expectation_hash",
}
_PUBLICATION_RECEIPT_FIELDS = {
    "status",
    "published",
    "blockers",
    "expectation_hash",
    "pointer_hash",
    "report_hash",
    "report_file_sha256",
    "report_file_size_bytes",
    "report_schema_version",
    "batch_spec_hash",
    "dataset_manifest_hash",
    "batch_run_hash",
    "governance_status",
    "created_at",
    "source_verification_status",
    "pointer_post_read_verified",
    "report_post_read_verified",
    "research_only",
    "paper_authorized",
    "live_order_allowed",
}
_WINDOWS_RESERVED_BASENAMES = frozenset({
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "CLOCK$",
    "CONIN$",
    "CONOUT$",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
})


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _file_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _is_sha256(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def _native_nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _native_safe_nonnegative_int(value: Any) -> int | None:
    number = _native_nonnegative_int(value)
    return number if number is not None and number <= (1 << 53) - 1 else None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _created_at_ms(value: Any) -> int | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        instant = int(parsed.timestamp() * 1000)
        return instant if instant >= 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def _strings(value: Any, *, limit: int = 24) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item)[:240] for item in value if isinstance(item, str) and item][:limit]


def _authority_violations(value: Any, path: str = "payload") -> list[str]:
    return [
        f"authority_not_false:{item}"
        for item in canonical_authority_violations(value, path=path)
    ]


def _windows_canonical_basename(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = unicodedata.normalize("NFKC", value)
    if normalized != normalized.strip() or normalized.endswith((".", " ")):
        return None
    if normalized in {".", ".."}:
        return None
    if any(character in normalized for character in '<>:"/\\|?*'):
        return None
    if any(ord(character) < 32 for character in normalized):
        return None
    if Path(normalized).name != normalized:
        return None
    device_stem = normalized.split(".", 1)[0].rstrip(" .").upper()
    if device_stem in _WINDOWS_RESERVED_BASENAMES:
        return None
    return normalized.casefold()


def build_strategy_research_pointer_publication_expectation(
    report: dict[str, Any] | Any,
    *,
    report_file: str,
    report_file_bytes: bytes | bytearray,
) -> dict[str, Any]:
    frozen_report = dict(report) if isinstance(report, dict) else {}
    raw = bytes(report_file_bytes) if isinstance(report_file_bytes, (bytes, bytearray)) else b""
    canonical_file = _windows_canonical_basename(report_file)
    if canonical_file is None or canonical_file == _windows_canonical_basename(
        DEFAULT_STRATEGY_RESEARCH_POINTER_FILE
    ):
        raise ValueError("strategy_research_expectation_report_basename_invalid")
    try:
        if _read_json_object(raw) != frozen_report:
            raise ValueError("strategy_research_expectation_report_bytes_mismatch")
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("strategy_research_expectation_report_bytes_invalid") from None
    governance = frozen_report.get("research_governance")
    governance = governance if isinstance(governance, dict) else {}
    content = {
        "schema_version": (
            STRATEGY_RESEARCH_POINTER_PUBLICATION_EXPECTATION_SCHEMA_VERSION
        ),
        "report_file": report_file,
        "report_hash": _canonical_hash(frozen_report),
        "report_file_sha256": _file_sha256(raw),
        "report_file_size_bytes": len(raw),
        "report_schema_version": frozen_report.get("schema_version"),
        "batch_spec_hash": str(frozen_report.get("batch_spec_hash") or ""),
        "dataset_manifest_hash": str(
            frozen_report.get("dataset_manifest_hash") or ""
        ),
        "batch_run_hash": str(frozen_report.get("batch_run_hash") or ""),
        "governance_status": str(governance.get("status") or "UNKNOWN"),
        "created_at": str(frozen_report.get("created_at") or ""),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {**content, "expectation_hash": _canonical_hash(content)}


def _verify_publication_expectation(
    expectation: dict[str, Any] | Any,
) -> dict[str, Any]:
    payload = dict(expectation) if isinstance(expectation, dict) else {}
    blockers: list[str] = []
    if set(payload) != _PUBLICATION_EXPECTATION_FIELDS:
        blockers.append("strategy_research_pointer_expectation_field_contract_invalid")
    content = dict(payload)
    expectation_hash = str(content.pop("expectation_hash", "") or "")
    if not _is_sha256(expectation_hash) or _canonical_hash(content) != expectation_hash:
        blockers.append("strategy_research_pointer_expectation_hash_invalid")
    if payload.get("schema_version") != (
        STRATEGY_RESEARCH_POINTER_PUBLICATION_EXPECTATION_SCHEMA_VERSION
    ):
        blockers.append("strategy_research_pointer_expectation_schema_invalid")
    report_file = payload.get("report_file")
    canonical_file = _windows_canonical_basename(report_file)
    if canonical_file is None or canonical_file == _windows_canonical_basename(
        DEFAULT_STRATEGY_RESEARCH_POINTER_FILE
    ):
        blockers.append("strategy_research_pointer_expectation_report_basename_invalid")
    for field in (
        "report_hash",
        "report_file_sha256",
        "batch_spec_hash",
        "dataset_manifest_hash",
        "batch_run_hash",
    ):
        if not _is_sha256(payload.get(field)):
            blockers.append(f"strategy_research_pointer_expectation_{field}_invalid")
    if _native_nonnegative_int(payload.get("report_file_size_bytes")) is None:
        blockers.append("strategy_research_pointer_expectation_file_size_invalid")
    if _native_nonnegative_int(payload.get("report_schema_version")) is None:
        blockers.append("strategy_research_pointer_expectation_report_schema_invalid")
    if not isinstance(payload.get("governance_status"), str) or not payload.get(
        "governance_status"
    ):
        blockers.append("strategy_research_pointer_expectation_governance_invalid")
    if _created_at_ms(payload.get("created_at")) is None:
        blockers.append("strategy_research_pointer_expectation_created_at_invalid")
    for field, expected in (
        ("research_only", True),
        ("paper_authorized", False),
        ("live_order_allowed", False),
    ):
        if payload.get(field) is not expected:
            blockers.append(f"strategy_research_pointer_expectation_scope_invalid:{field}")
    blockers.extend(_authority_violations(payload, "expectation"))
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
    }


def _read_json_object(raw: bytes) -> dict[str, Any]:
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON object required")
    return payload


def _fixed_pointer_path(report_dir: Path | str) -> tuple[Path, Path]:
    directory = Path(report_dir).resolve()
    pointer = (directory / DEFAULT_STRATEGY_RESEARCH_POINTER_FILE).resolve()
    if pointer.parent != directory or pointer.name != DEFAULT_STRATEGY_RESEARCH_POINTER_FILE:
        raise ValueError("fixed strategy research pointer path invalid")
    return directory, pointer


def strategy_research_pointer_publication_eligibility(
    report_dir: Path | str,
    output_path: Path | str,
) -> dict[str, Any]:
    directory, _pointer = _fixed_pointer_path(report_dir)
    output = Path(output_path).resolve()
    output_basename = _windows_canonical_basename(output.name)
    pointer_basename = _windows_canonical_basename(
        DEFAULT_STRATEGY_RESEARCH_POINTER_FILE
    )
    if output_basename is None:
        return {
            "status": "BLOCK",
            "blockers": ["strategy_research_output_basename_invalid"],
            "publish": False,
        }
    if output_basename == pointer_basename:
        return {
            "status": "BLOCK",
            "blockers": ["strategy_research_output_collides_with_fixed_pointer"],
            "publish": False,
        }
    if output.parent != directory:
        return {
            "status": "SKIP",
            "blockers": ["strategy_research_output_outside_report_root"],
            "publish": False,
        }
    return {"status": "PASS", "blockers": [], "publish": True}


def _build_pointer(
    report_file: str,
    report_file_sha256: str,
    report: dict[str, Any],
) -> dict[str, Any]:
    governance = report.get("research_governance")
    governance = governance if isinstance(governance, dict) else {}
    content = {
        "schema_version": STRATEGY_RESEARCH_POINTER_SCHEMA_VERSION,
        "status": _POINTER_STATUS,
        "report_file": report_file,
        "report_file_sha256": report_file_sha256,
        "report_schema_version": report.get("schema_version"),
        "batch_spec_hash": str(report.get("batch_spec_hash") or ""),
        "dataset_manifest_hash": str(report.get("dataset_manifest_hash") or ""),
        "batch_run_hash": str(report.get("batch_run_hash") or ""),
        "governance_status": str(governance.get("status") or "UNKNOWN"),
        "created_at": str(report.get("created_at") or ""),
        "research_only": True,
        "descriptive_only": True,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "automatic_paper_activation_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {**content, "pointer_hash": _canonical_hash(content)}


def verify_strategy_research_report_pointer(
    pointer: dict[str, Any] | None,
    *,
    report: dict[str, Any] | None,
    report_file_sha256: str,
) -> dict[str, Any]:
    payload = dict(pointer or {})
    frozen_report = dict(report or {})
    blockers: list[str] = []
    if set(payload) != _POINTER_FIELDS:
        blockers.append("strategy_research_pointer_field_contract_invalid")
    expected_pointer_hash = str(payload.get("pointer_hash") or "")
    pointer_content = dict(payload)
    pointer_content.pop("pointer_hash", None)
    if not _is_sha256(expected_pointer_hash) or _canonical_hash(pointer_content) != expected_pointer_hash:
        blockers.append("strategy_research_pointer_hash_invalid")
    if payload.get("schema_version") != STRATEGY_RESEARCH_POINTER_SCHEMA_VERSION:
        blockers.append("strategy_research_pointer_schema_invalid")
    if payload.get("status") != _POINTER_STATUS:
        blockers.append("strategy_research_pointer_status_invalid")

    report_file = str(payload.get("report_file") or "")
    canonical_report_file = _windows_canonical_basename(report_file)
    if (
        canonical_report_file is None
        or canonical_report_file
        == _windows_canonical_basename(DEFAULT_STRATEGY_RESEARCH_POINTER_FILE)
    ):
        blockers.append("strategy_research_pointer_report_basename_invalid")
    declared_file_sha = str(payload.get("report_file_sha256") or "")
    if not _is_sha256(declared_file_sha) or declared_file_sha != report_file_sha256:
        blockers.append("strategy_research_pointer_file_sha256_mismatch")

    report_verification = verify_strategy_research_report(
        frozen_report,
        require_formal=False,
    )
    if report_verification.get("status") != "PASS":
        blockers.append("strategy_research_report_verification_blocked")
    governance = frozen_report.get("research_governance")
    governance = governance if isinstance(governance, dict) else {}
    bindings = {
        "report_schema_version": frozen_report.get("schema_version"),
        "batch_spec_hash": str(frozen_report.get("batch_spec_hash") or ""),
        "dataset_manifest_hash": str(frozen_report.get("dataset_manifest_hash") or ""),
        "batch_run_hash": str(frozen_report.get("batch_run_hash") or ""),
        "governance_status": str(governance.get("status") or "UNKNOWN"),
        "created_at": str(frozen_report.get("created_at") or ""),
    }
    for field, expected in bindings.items():
        if payload.get(field) != expected:
            blockers.append(f"strategy_research_pointer_{field}_mismatch")
    for field in ("batch_spec_hash", "dataset_manifest_hash", "batch_run_hash"):
        if not _is_sha256(bindings[field]):
            blockers.append(f"strategy_research_pointer_{field}_invalid")
    if _native_nonnegative_int(bindings["report_schema_version"]) is None:
        blockers.append("strategy_research_pointer_report_schema_version_invalid")
    if _created_at_ms(bindings["created_at"]) is None:
        blockers.append("strategy_research_pointer_created_at_invalid")

    for field, expected in (
        ("research_only", True),
        ("descriptive_only", True),
        ("profitability_proven", False),
        ("performance_claim_allowed", False),
        ("parameter_selection_allowed", False),
        ("automatic_paper_activation_allowed", False),
        ("paper_authorized", False),
        ("live_order_allowed", False),
    ):
        if payload.get(field) is not expected:
            blockers.append(f"strategy_research_pointer_scope_invalid:{field}")
    blockers.extend(_authority_violations(payload, "pointer"))
    blockers.extend(_authority_violations(frozen_report, "report"))
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "report_verification_status": str(report_verification.get("status") or "BLOCK"),
        "formal_single_use": report_verification.get("formal_single_use") is True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def _publication_block(blockers: list[str]) -> dict[str, Any]:
    return {
        "status": "BLOCK",
        "blockers": list(dict.fromkeys(
            blockers or ["strategy_research_pointer_publication_blocked"]
        )),
        "published": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _expectation_binding_blockers(
    expectation: dict[str, Any],
    *,
    source_name: str,
    report_raw: bytes,
    report: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    governance = report.get("research_governance")
    governance = governance if isinstance(governance, dict) else {}
    bindings = {
        "report_file": source_name,
        "report_hash": _canonical_hash(report),
        "report_file_sha256": _file_sha256(report_raw),
        "report_file_size_bytes": len(report_raw),
        "report_schema_version": report.get("schema_version"),
        "batch_spec_hash": str(report.get("batch_spec_hash") or ""),
        "dataset_manifest_hash": str(report.get("dataset_manifest_hash") or ""),
        "batch_run_hash": str(report.get("batch_run_hash") or ""),
        "governance_status": str(governance.get("status") or "UNKNOWN"),
        "created_at": str(report.get("created_at") or ""),
    }
    for field, actual in bindings.items():
        if expectation.get(field) != actual:
            blockers.append(f"strategy_research_pointer_expectation_{field}_mismatch")
    return blockers


def verify_strategy_research_pointer_publication_receipt(
    receipt: dict[str, Any] | Any,
    *,
    expectation: dict[str, Any] | Any,
) -> dict[str, Any]:
    payload = dict(receipt) if isinstance(receipt, dict) else {}
    expected = dict(expectation) if isinstance(expectation, dict) else {}
    blockers = list(_verify_publication_expectation(expected).get("blockers") or [])
    if set(payload) != _PUBLICATION_RECEIPT_FIELDS:
        blockers.append("strategy_research_pointer_receipt_field_contract_invalid")
    if payload.get("status") != "PUBLISHED" or payload.get("published") is not True:
        blockers.append("strategy_research_pointer_receipt_status_invalid")
    if payload.get("blockers") != []:
        blockers.append("strategy_research_pointer_receipt_blockers_invalid")
    for field in (
        "expectation_hash",
        "report_hash",
        "report_file_sha256",
        "report_file_size_bytes",
        "report_schema_version",
        "batch_spec_hash",
        "dataset_manifest_hash",
        "batch_run_hash",
        "governance_status",
        "created_at",
    ):
        if payload.get(field) != expected.get(field):
            blockers.append(f"strategy_research_pointer_receipt_{field}_mismatch")
    expected_pointer = _build_pointer(
        str(expected.get("report_file") or ""),
        str(expected.get("report_file_sha256") or ""),
        {
            "schema_version": expected.get("report_schema_version"),
            "batch_spec_hash": expected.get("batch_spec_hash"),
            "dataset_manifest_hash": expected.get("dataset_manifest_hash"),
            "batch_run_hash": expected.get("batch_run_hash"),
            "created_at": expected.get("created_at"),
            "research_governance": {
                "status": expected.get("governance_status"),
            },
        },
    )
    if payload.get("pointer_hash") != expected_pointer.get("pointer_hash"):
        blockers.append("strategy_research_pointer_receipt_pointer_hash_mismatch")
    if payload.get("source_verification_status") != "PASS":
        blockers.append("strategy_research_pointer_receipt_source_verification_invalid")
    if payload.get("pointer_post_read_verified") is not True:
        blockers.append("strategy_research_pointer_receipt_pointer_post_read_invalid")
    if payload.get("report_post_read_verified") is not True:
        blockers.append("strategy_research_pointer_receipt_report_post_read_invalid")
    for field, required in (
        ("research_only", True),
        ("paper_authorized", False),
        ("live_order_allowed", False),
    ):
        if payload.get(field) is not required:
            blockers.append(f"strategy_research_pointer_receipt_scope_invalid:{field}")
    blockers.extend(_authority_violations(payload, "publication_receipt"))
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _publish_strategy_research_report_pointer(
    report_dir: Path | str,
    report_path: Path | str,
    *,
    expectation: dict[str, Any] | Any,
) -> dict[str, Any]:
    eligibility = strategy_research_pointer_publication_eligibility(
        report_dir,
        report_path,
    )
    if eligibility.get("status") != "PASS":
        if eligibility.get("status") == "SKIP":
            return {
                **_publication_block(list(eligibility.get("blockers") or [])),
                "status": "SKIPPED",
            }
        return _publication_block(list(eligibility.get("blockers") or []))
    expected = dict(expectation) if isinstance(expectation, dict) else {}
    expectation_verification = _verify_publication_expectation(expected)
    if expectation_verification.get("status") != "PASS":
        return _publication_block(list(expectation_verification.get("blockers") or []))

    directory, pointer_path = _fixed_pointer_path(report_dir)
    source_path = Path(report_path).resolve()
    if source_path.parent != directory:
        return _publication_block(["strategy_research_report_parent_invalid"])
    try:
        raw = _read_bytes(source_path)
        report = _read_json_object(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return _publication_block(["strategy_research_report_unavailable"])
    binding_blockers = _expectation_binding_blockers(
        expected,
        source_name=source_path.name,
        report_raw=raw,
        report=report,
    )
    if binding_blockers:
        return _publication_block(binding_blockers)

    report_file_sha256 = _file_sha256(raw)
    pointer = _build_pointer(source_path.name, report_file_sha256, report)
    verification = verify_strategy_research_report_pointer(
        pointer,
        report=report,
        report_file_sha256=report_file_sha256,
    )
    if verification.get("status") != "PASS":
        return _publication_block(list(
            verification.get("blockers")
            or ["strategy_research_pointer_verification_blocked"]
        ))

    temporary = pointer_path.with_name(
        f".{pointer_path.name}.{uuid.uuid4().hex}.tmp"
    )
    pointer_raw = json.dumps(pointer, ensure_ascii=False, indent=2).encode("utf-8")
    try:
        with temporary.open("xb") as handle:
            handle.write(pointer_raw)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(pointer_path)
    except OSError:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        return _publication_block(["strategy_research_pointer_atomic_write_failed"])

    try:
        persisted_pointer_raw = _read_bytes(pointer_path)
        persisted_pointer = _read_json_object(persisted_pointer_raw)
        persisted_report_raw = _read_bytes(source_path)
        persisted_report = _read_json_object(persisted_report_raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return _publication_block([
            "strategy_research_pointer_post_read_unavailable"
        ])
    post_read_blockers: list[str] = []
    if persisted_pointer_raw != pointer_raw or persisted_pointer != pointer:
        post_read_blockers.append("strategy_research_pointer_post_read_mismatch")
    if persisted_report_raw != raw or persisted_report != report:
        post_read_blockers.append("strategy_research_report_post_read_mismatch")
    post_read_blockers.extend(_expectation_binding_blockers(
        expected,
        source_name=source_path.name,
        report_raw=persisted_report_raw,
        report=persisted_report,
    ))
    post_verification = verify_strategy_research_report_pointer(
        persisted_pointer,
        report=persisted_report,
        report_file_sha256=_file_sha256(persisted_report_raw),
    )
    if post_verification.get("status") != "PASS":
        post_read_blockers.append(
            "strategy_research_pointer_post_read_verification_blocked"
        )
    if post_read_blockers:
        return _publication_block(post_read_blockers)

    receipt = {
        "status": "PUBLISHED",
        "published": True,
        "blockers": [],
        "expectation_hash": expected["expectation_hash"],
        "pointer_hash": pointer["pointer_hash"],
        "report_hash": expected["report_hash"],
        "report_file_sha256": expected["report_file_sha256"],
        "report_file_size_bytes": expected["report_file_size_bytes"],
        "report_schema_version": expected["report_schema_version"],
        "batch_spec_hash": expected["batch_spec_hash"],
        "dataset_manifest_hash": expected["dataset_manifest_hash"],
        "batch_run_hash": expected["batch_run_hash"],
        "governance_status": expected["governance_status"],
        "created_at": expected["created_at"],
        "source_verification_status": "PASS",
        "pointer_post_read_verified": True,
        "report_post_read_verified": True,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    receipt_verification = verify_strategy_research_pointer_publication_receipt(
        receipt,
        expectation=expected,
    )
    if receipt_verification.get("status") != "PASS":
        return _publication_block(list(receipt_verification.get("blockers") or []))
    return receipt


def publish_strategy_research_report_pointer(
    report_dir: Path | str,
    report_path: Path | str,
    *,
    expectation: dict[str, Any] | Any,
) -> dict[str, Any]:
    try:
        return _publish_strategy_research_report_pointer(
            report_dir,
            report_path,
            expectation=expectation,
        )
    except Exception:
        return _publication_block([
            "strategy_research_pointer_publication_unexpected_failure"
        ])


def _aggregate_status(values: list[str]) -> str:
    statuses = [str(value or "UNKNOWN").upper() for value in values]
    if not statuses:
        return "UNKNOWN"
    if "BLOCK" in statuses:
        return "BLOCK"
    if "REVIEW" in statuses:
        return "REVIEW"
    if "NOT_ENOUGH_VARIANTS" in statuses:
        return "NOT_ENOUGH_VARIANTS"
    if all(value == "PASS" for value in statuses):
        return "PASS"
    return "UNKNOWN"


def _plateau_projection(report: dict[str, Any], strategy_id: str) -> dict[str, Any]:
    snapshot = report.get("parameter_stability")
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    rows = snapshot.get("strategies")
    rows = rows if isinstance(rows, list) else []
    selected = next(
        (
            row for row in rows
            if isinstance(row, dict)
            and str(row.get("strategy_id") or "").strip().lower() == strategy_id
        ),
        {},
    )
    return {
        "schema_version": str(snapshot.get("schema_version") or "UNKNOWN")[:64],
        "status": str(selected.get("status") or "UNKNOWN")[:32],
        "topology_basis": str(snapshot.get("topology_basis") or "UNKNOWN")[:80],
        "numeric_parameter_distance_checked": (
            snapshot.get("numeric_parameter_distance_checked")
            if isinstance(snapshot.get("numeric_parameter_distance_checked"), bool)
            else None
        ),
        "frozen_variant_count": _native_nonnegative_int(selected.get("frozen_variant_count")),
        "eligible_variant_count": _native_nonnegative_int(selected.get("eligible_variant_count")),
        "near_best_eligible_variant_count": _native_nonnegative_int(
            selected.get("near_best_eligible_variant_count")
        ),
        "adjacent_near_best_variant_count": _native_nonnegative_int(
            selected.get("adjacent_near_best_variant_count")
        ),
        "plateau_width": _native_nonnegative_int(selected.get("plateau_width")),
        "best_adjusted_score": _number(selected.get("best_adjusted_score")),
        "peak_only": selected.get("peak_only") if isinstance(selected.get("peak_only"), bool) else None,
        "blockers": _strings(selected.get("blockers")),
        "descriptive_only": True,
        "parameter_selection_allowed": False,
    }


def _public_admission_check_projection(
    value: Any,
    *,
    future_standard: bool = False,
) -> tuple[dict[str, Any] | None, list[str]]:
    row = value if isinstance(value, dict) else {}
    blockers: list[str] = []
    condition_id = str(row.get("condition_id") or "")
    condition_kind = str(row.get("condition_kind") or "")
    evidence_stage = str(row.get("evidence_stage") or "")
    required_action = str(row.get("required_action") or "")
    status = str(row.get("status") or "")
    triggered = row.get("triggered")
    if not condition_id or len(condition_id) > 96:
        blockers.append("public_admission_condition_id_invalid")
    if condition_kind not in _PUBLIC_CONDITION_KINDS:
        blockers.append("public_admission_condition_kind_invalid")
    if future_standard and condition_kind != "STANDARD":
        blockers.append("public_admission_future_condition_kind_invalid")
    if evidence_stage not in _PUBLIC_EVIDENCE_STAGES:
        blockers.append("public_admission_evidence_stage_invalid")
    if required_action not in _PUBLIC_REQUIRED_ACTIONS:
        blockers.append("public_admission_required_action_invalid")
    if status not in _PUBLIC_CONDITION_STATUSES:
        blockers.append("public_admission_condition_status_invalid")
    if triggered is not None and not isinstance(triggered, bool):
        blockers.append("public_admission_condition_triggered_invalid")
    public_blockers: list[str] = []
    if status == "BLOCK":
        if condition_kind == "MECHANISM_SPECIFIC":
            public_blockers.append(
                "mechanism_condition_triggered"
                if triggered is True
                else "mechanism_condition_unresolved"
                if triggered is None
                else "mechanism_condition_blocked"
            )
        else:
            public_blockers.append("standard_condition_blocked")
    projected = {
        "condition_id": condition_id[:96],
        "condition_kind": condition_kind,
        "evidence_stage": evidence_stage,
        "required_action": required_action,
        "status": status,
        "triggered": triggered if isinstance(triggered, bool) else None,
        "blockers": public_blockers,
    }
    if condition_kind == "MECHANISM_SPECIFIC":
        metric = str(row.get("metric") or "")
        operator = str(row.get("operator") or "")
        threshold = _number(row.get("threshold"))
        metric_value = _number(row.get("metric_value"))
        if metric not in MECHANISM_FAILURE_METRICS_V2:
            blockers.append("public_admission_metric_invalid")
        if operator not in MECHANISM_FAILURE_OPERATORS_V2:
            blockers.append("public_admission_operator_invalid")
        if threshold is None:
            blockers.append("public_admission_threshold_invalid")
        if row.get("metric_value") is not None and metric_value is None:
            blockers.append("public_admission_metric_value_invalid")
        projected.update({
            "metric": metric,
            "operator": operator,
            "threshold": threshold,
            "metric_value": metric_value,
        })
    return (projected if not blockers else None), blockers


def _public_search_lineage_projection(
    report: dict[str, Any],
    strategy_id: str,
) -> tuple[dict[str, Any], list[str]]:
    """Project schema-14 lineage without identities or current-registry claims."""

    common = {
        "schema_version": STRATEGY_RESEARCH_SEARCH_LINEAGE_PUBLIC_SCHEMA_VERSION,
        "descriptive_only": True,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "automatic_paper_activation_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    batch_spec = report.get("batch_spec")
    batch_spec = batch_spec if isinstance(batch_spec, dict) else {}
    hypothesis = batch_spec.get("hypothesis_preregistration")
    hypothesis = hypothesis if isinstance(hypothesis, dict) else {}
    lineage = batch_spec.get("search_lineage")
    lineage = lineage if isinstance(lineage, dict) else {}
    variants = batch_spec.get("variants")
    variants = variants if isinstance(variants, list) else []
    admission = report.get("preregistered_failure_admission")
    admission = admission if isinstance(admission, dict) else {}
    lineage_binding = admission.get("search_lineage_binding")
    lineage_binding = lineage_binding if isinstance(lineage_binding, dict) else {}
    registration_binding = admission.get("registration_binding")
    registration_binding = (
        registration_binding if isinstance(registration_binding, dict) else {}
    )
    blockers: list[str] = []

    if report.get("schema_version") != STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION:
        blockers.append("public_search_lineage_report_schema_invalid")
    if hypothesis.get("schema_version") != (
        STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3
    ):
        blockers.append("public_search_lineage_hypothesis_schema_invalid")
    if admission.get("schema_version") != (
        STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION_V3
    ):
        blockers.append("public_search_lineage_admission_schema_invalid")

    lineage_verification = verify_strategy_research_search_lineage(
        lineage,
        expected_search_family_id=str(hypothesis.get("search_family_id") or ""),
        expected_current_trial_count=len(variants),
    )
    if lineage_verification.get("status") != "PASS":
        blockers.append("public_search_lineage_source_invalid")
    prior_trials = _native_safe_nonnegative_int(lineage.get("prior_trial_count"))
    current_trials = _native_safe_nonnegative_int(lineage.get("current_trial_count"))
    cumulative_trials = _native_safe_nonnegative_int(
        lineage.get("cumulative_trial_count")
    )
    if (
        prior_trials is None
        or current_trials is None
        or current_trials < 1
        or cumulative_trials is None
        or cumulative_trials != prior_trials + current_trials
    ):
        blockers.append("public_search_lineage_trial_counts_invalid")

    expected_lineage_binding_fields = {
        "report_schema_version",
        "status",
        "lineage_hash",
        "search_family_id",
        "trial_count_scope",
        "current_trial_count",
        "cumulative_trial_count",
        "derived_before_selection",
        "blockers",
    }
    lineage_binding_valid = (
        set(lineage_binding) == expected_lineage_binding_fields
        and lineage_binding.get("report_schema_version")
        == STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION
        and lineage_binding.get("status") == "PASS"
        and lineage_binding.get("lineage_hash") == lineage.get("lineage_hash")
        and _is_sha256(lineage_binding.get("lineage_hash"))
        and lineage_binding.get("search_family_id")
        == lineage.get("search_family_id")
        and lineage_binding.get("trial_count_scope")
        == "GLOBAL_REGISTERED_STRATEGY_RESEARCH"
        and lineage_binding.get("trial_count_scope")
        == lineage.get("trial_count_scope")
        and lineage_binding.get("current_trial_count") == current_trials
        and lineage_binding.get("cumulative_trial_count") == cumulative_trials
        and lineage_binding.get("derived_before_selection") is True
        and lineage.get("derived_before_selection") is True
        and lineage_binding.get("blockers") == []
    )
    if not lineage_binding_valid:
        blockers.append("public_search_lineage_admission_binding_invalid")

    expected_registration_binding_fields = {
        "status",
        "verification_scope",
        "registration_id",
        "protocol_hash",
        "claim_hash",
        "registry_anchor_hash",
        "registry_status",
        "registry_audit_status",
        "blockers",
    }
    registration_common_valid = (
        set(registration_binding) == expected_registration_binding_fields
        and isinstance(registration_binding.get("registration_id"), str)
        and bool(str(registration_binding.get("registration_id") or "").strip())
        and _is_sha256(registration_binding.get("protocol_hash"))
        and _is_sha256(registration_binding.get("claim_hash"))
        and _is_sha256(registration_binding.get("registry_anchor_hash"))
        and registration_binding.get("registry_status") == "RUNNING"
        and registration_binding.get("registry_audit_status") == "PASS"
        and registration_binding.get("blockers") == []
    )
    live_at_selection = registration_common_valid and (
        registration_binding.get("status") == "LIVE_REGISTRY_VERIFIED"
        and registration_binding.get("verification_scope")
        == "LIVE_REGISTRY_AUDIT_AND_PREREGISTRATION_RECEIPT"
    )
    receipt_only = registration_common_valid and (
        registration_binding.get("status") == "SELF_CONSISTENT_RECEIPT"
        and registration_binding.get("verification_scope")
        == "SELF_CONSISTENT_RECEIPT_ONLY"
    )
    if not live_at_selection:
        blockers.append("public_search_lineage_registration_binding_invalid")

    admission_status = str(admission.get("status") or "").upper()
    if admission_status not in {"PASS", "BLOCK"}:
        blockers.append("public_search_lineage_admission_status_invalid")
    if receipt_only:
        strategy_rows = admission.get("strategies")
        strategy_rows = strategy_rows if isinstance(strategy_rows, list) else []
        if (
            admission_status != "BLOCK"
            or admission.get("admitted_variant_ids") != []
            or any(
                not isinstance(row, dict) or row.get("admitted_variant_ids") != []
                for row in strategy_rows
            )
            or "strategy_search_lineage_live_registry_verification_required"
            not in (admission.get("blockers") or [])
        ):
            blockers.append("public_search_lineage_receipt_only_status_invalid")
        blockers.append("public_search_lineage_live_at_selection_required")
    if canonical_authority_violations(admission, path="preregistered_failure_admission"):
        blockers.append("public_search_lineage_contains_execution_authority")

    if blockers:
        return {
            **common,
            "status": "BLOCK",
            "family_bound": False,
            "trial_count_scope": None,
            "prior_trial_count": None,
            "current_trial_count": None,
            "cumulative_trial_count": None,
            "selection_binding_scope": None,
            "offline_verification_scope": (
                "OFFLINE_REPORT_AND_PREREGISTRATION_RECEIPT_CONSISTENCY_ONLY"
            ),
            "admission_status": "BLOCK",
            "blockers": ["public_search_lineage_contract_invalid"],
        }, list(dict.fromkeys(blockers))

    if not strategy_id:
        return {
            **common,
            "status": "NOT_IN_REPORT",
            "family_bound": False,
            "trial_count_scope": None,
            "prior_trial_count": None,
            "current_trial_count": None,
            "cumulative_trial_count": None,
            "selection_binding_scope": None,
            "offline_verification_scope": (
                "OFFLINE_REPORT_AND_PREREGISTRATION_RECEIPT_CONSISTENCY_ONLY"
            ),
            "admission_status": "NOT_IN_REPORT",
            "blockers": ["strategy_not_in_frozen_research_report"],
        }, []

    return {
        **common,
        "status": "BOUND",
        "family_bound": True,
        "trial_count_scope": "GLOBAL_REGISTERED_STRATEGY_RESEARCH",
        "prior_trial_count": prior_trials,
        "current_trial_count": current_trials,
        "cumulative_trial_count": cumulative_trials,
        "selection_binding_scope": str(
            registration_binding.get("verification_scope") or ""
        ),
        "offline_verification_scope": (
            "OFFLINE_REPORT_AND_PREREGISTRATION_RECEIPT_CONSISTENCY_ONLY"
        ),
        "admission_status": admission_status,
        "blockers": [],
    }, []


def _preregistered_failure_admission_projection(
    report: dict[str, Any],
    strategy_id: str,
    *,
    search_lineage: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    common = {
        "descriptive_only": True,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "automatic_paper_activation_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    report_schema_version = report.get("schema_version")
    if report_schema_version != PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION:
        if report_schema_version in {
            MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
            STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION,
        }:
            uses_admission_v3 = (
                report_schema_version
                == STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION
            )
            expected_admission_schema = (
                STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION_V3
                if uses_admission_v3
                else STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION_V2
            )
            expected_hypothesis_schema = (
                STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3
                if uses_admission_v3
                else STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2
            )
            admission = report.get("preregistered_failure_admission")
            admission = admission if isinstance(admission, dict) else {}
            rows = admission.get("strategies")
            rows = rows if isinstance(rows, list) else []
            matching = (
                [
                    row for row in rows
                    if isinstance(row, dict)
                    and str(row.get("strategy_id") or "").strip().lower()
                    == strategy_id
                ]
                if strategy_id
                else []
            )
            selected = matching[0] if len(matching) == 1 else {}
            blockers: list[str] = []
            if admission.get("schema_version") != expected_admission_schema:
                blockers.append(
                    "public_admission_schema_v3_required"
                    if uses_admission_v3
                    else "public_admission_schema_v2_required"
                )
            if admission.get("status") not in {"PASS", "BLOCK"}:
                blockers.append("public_admission_status_invalid")
            if admission.get("admission_scope") != "HYPOTHESIS_BATCH":
                blockers.append("public_admission_scope_invalid")
            if strategy_id:
                if len(matching) != 1:
                    blockers.append("public_admission_selected_strategy_row_invalid")
                if selected.get("status") not in {"PASS", "BLOCK"}:
                    blockers.append("public_admission_selected_strategy_status_invalid")
            hypothesis = (
                dict(report.get("batch_spec") or {}).get("hypothesis_preregistration")
            )
            hypothesis = hypothesis if isinstance(hypothesis, dict) else {}
            if hypothesis.get("schema_version") != expected_hypothesis_schema:
                blockers.append(
                    "public_admission_hypothesis_schema_v3_required"
                    if uses_admission_v3
                    else "public_admission_hypothesis_schema_v2_required"
                )
            if str(admission.get("hypothesis_id") or "") != str(
                hypothesis.get("hypothesis_id") or ""
            ):
                blockers.append("public_admission_hypothesis_binding_invalid")
            hypothesis_failure = hypothesis.get("failure_contract")
            hypothesis_failure = (
                hypothesis_failure if isinstance(hypothesis_failure, dict) else {}
            )
            hypothesis_mechanism_conditions = hypothesis_failure.get(
                "mechanism_specific_conditions"
            )
            hypothesis_mechanism_conditions = (
                hypothesis_mechanism_conditions
                if isinstance(hypothesis_mechanism_conditions, list)
                else []
            )
            expected_mechanism_conditions: list[dict[str, Any]] = []
            for raw_condition in hypothesis_mechanism_conditions[:8]:
                projected, condition_blockers = (
                    _public_hypothesis_mechanism_condition_projection(raw_condition)
                )
                blockers.extend(condition_blockers)
                if projected is not None:
                    expected_mechanism_conditions.append(projected)
            mechanism_ids = admission.get("mechanism_condition_ids")
            mechanism_ids = mechanism_ids if isinstance(mechanism_ids, list) else []
            if (
                not 1 <= len(mechanism_ids) <= 8
                or any(not isinstance(item, str) or not item for item in mechanism_ids)
                or len(set(mechanism_ids)) != len(mechanism_ids)
            ):
                blockers.append("public_admission_mechanism_condition_ids_invalid")
            checks: list[dict[str, Any]] = []
            raw_checks = selected.get("checks")
            raw_checks = raw_checks if isinstance(raw_checks, list) else []
            for raw_check in raw_checks[:16]:
                projected, check_blockers = _public_admission_check_projection(raw_check)
                blockers.extend(check_blockers)
                if projected is not None:
                    checks.append(projected)
            if len(raw_checks) > 16:
                blockers.append("public_admission_check_count_invalid")
            projected_mechanism_ids = [
                str(item.get("condition_id") or "")
                for item in checks
                if item.get("condition_kind") == "MECHANISM_SPECIFIC"
            ]
            expected_mechanism_ids = [
                str(item.get("condition_id") or "")
                for item in expected_mechanism_conditions
            ]
            if mechanism_ids != expected_mechanism_ids:
                blockers.append("public_admission_mechanism_check_binding_invalid")
            projected_mechanism_conditions = [
                {
                    key: item.get(key)
                    for key in (
                        "condition_id",
                        "evidence_stage",
                        "metric",
                        "operator",
                        "threshold",
                        "required_action",
                    )
                }
                for item in checks
                if item.get("condition_kind") == "MECHANISM_SPECIFIC"
            ]
            if (
                strategy_id
                and (
                    projected_mechanism_ids != mechanism_ids
                    or projected_mechanism_conditions
                    != expected_mechanism_conditions
                )
            ):
                blockers.append("public_admission_mechanism_hypothesis_binding_invalid")
            future_checks: list[dict[str, Any]] = []
            raw_future = admission.get("future_standard_checks")
            raw_future = raw_future if isinstance(raw_future, list) else []
            for raw_check in raw_future[:8]:
                projected, check_blockers = _public_admission_check_projection(
                    raw_check,
                    future_standard=True,
                )
                blockers.extend(check_blockers)
                if projected is not None:
                    future_checks.append(projected)
            if len(raw_future) > 8:
                blockers.append("public_admission_future_check_count_invalid")
            if (
                [item.get("condition_id") for item in future_checks]
                != [
                    "fresh_single_use_holdout_failure",
                    "natural_forward_statistical_failure",
                ]
                or any(
                    item.get("status") != "NOT_DUE"
                    or item.get("triggered") is not False
                    for item in future_checks
                )
            ):
                blockers.append("public_admission_future_checks_invalid")
            if canonical_authority_violations(admission, path="preregistered_failure_admission"):
                blockers.append("public_admission_contains_execution_authority")
            public_lineage_status = str(
                (search_lineage or {}).get("status") or ""
            ).upper()
            if uses_admission_v3 and (
                not isinstance(search_lineage, dict)
                or search_lineage.get("schema_version")
                != STRATEGY_RESEARCH_SEARCH_LINEAGE_PUBLIC_SCHEMA_VERSION
                or public_lineage_status
                != ("BOUND" if strategy_id else "NOT_IN_REPORT")
            ):
                blockers.append("public_admission_search_lineage_binding_invalid")
            if not strategy_id:
                projection = {
                    **common,
                    "schema_version": expected_admission_schema,
                    "status": "NOT_IN_REPORT",
                    "admission_scope": "HYPOTHESIS_BATCH",
                    "hypothesis_id": None,
                    "selected_strategy_status": "NOT_IN_REPORT",
                    "selected_strategy_candidate_count": 0,
                    "selected_strategy_admitted_count": 0,
                    "admitted_candidate_count": 0,
                    "mechanism_condition_ids": [],
                    "checks": [],
                    "future_standard_checks": [],
                    "blockers": ["strategy_not_in_frozen_research_report"],
                }
                if uses_admission_v3:
                    projection["search_lineage_status"] = "NOT_IN_REPORT"
                return projection, list(dict.fromkeys(blockers))
            projection = {
                **common,
                "schema_version": expected_admission_schema,
                "status": str(admission.get("status") or "BLOCK")[:32],
                "admission_scope": "HYPOTHESIS_BATCH",
                "hypothesis_id": str(admission.get("hypothesis_id") or "")[:96] or None,
                "selected_strategy_status": str(selected.get("status") or "NOT_IN_REPORT")[:32],
                "selected_strategy_candidate_count": len(
                    selected.get("candidate_variant_ids")
                    if isinstance(selected.get("candidate_variant_ids"), list)
                    else []
                ),
                "selected_strategy_admitted_count": len(
                    selected.get("admitted_variant_ids")
                    if isinstance(selected.get("admitted_variant_ids"), list)
                    else []
                ),
                "admitted_candidate_count": len(
                    admission.get("admitted_variant_ids")
                    if isinstance(admission.get("admitted_variant_ids"), list)
                    else []
                ),
                "mechanism_condition_ids": [str(item)[:96] for item in mechanism_ids],
                "checks": checks,
                "future_standard_checks": future_checks,
                "blockers": (
                    ["preregistered_failure_admission_blocked"]
                    if admission.get("status") == "BLOCK"
                    else []
                ),
            }
            if uses_admission_v3:
                projection["search_lineage_status"] = public_lineage_status
            return projection, list(dict.fromkeys(blockers))
        return {
            **common,
            "schema_version": STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION,
            "status": "NOT_REQUIRED",
            "admission_scope": "HYPOTHESIS_BATCH",
            "hypothesis_id": None,
            "selected_strategy_status": "NOT_REQUIRED",
            "selected_strategy_candidate_count": 0,
            "selected_strategy_admitted_count": 0,
            "admitted_candidate_count": 0,
            "checks": [],
            "blockers": [],
        }, []
    admission = report.get("preregistered_failure_admission")
    admission = admission if isinstance(admission, dict) else {}
    rows = admission.get("strategies")
    rows = rows if isinstance(rows, list) else []
    selected = next((
        row for row in rows
        if isinstance(row, dict)
        and str(row.get("strategy_id") or "").strip().lower() == strategy_id
    ), {})
    checks = selected.get("checks")
    checks = checks if isinstance(checks, list) else []
    if not strategy_id:
        return {
            **common,
            "schema_version": STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION,
            "status": "NOT_IN_REPORT",
            "admission_scope": "HYPOTHESIS_BATCH",
            "hypothesis_id": None,
            "selected_strategy_status": "NOT_IN_REPORT",
            "selected_strategy_candidate_count": 0,
            "selected_strategy_admitted_count": 0,
            "admitted_candidate_count": 0,
            "checks": [],
            "blockers": ["strategy_not_in_frozen_research_report"],
        }, []
    return {
        **common,
        "schema_version": str(admission.get("schema_version") or "UNKNOWN")[:96],
        "status": str(admission.get("status") or "BLOCK")[:32],
        "admission_scope": str(admission.get("admission_scope") or "UNKNOWN")[:64],
        "hypothesis_id": str(admission.get("hypothesis_id") or "")[:96] or None,
        "selected_strategy_status": str(selected.get("status") or "NOT_IN_REPORT")[:32],
        "selected_strategy_candidate_count": len(
            selected.get("candidate_variant_ids")
            if isinstance(selected.get("candidate_variant_ids"), list)
            else []
        ),
        "selected_strategy_admitted_count": len(
            selected.get("admitted_variant_ids")
            if isinstance(selected.get("admitted_variant_ids"), list)
            else []
        ),
        "admitted_candidate_count": len(
            admission.get("admitted_variant_ids")
            if isinstance(admission.get("admitted_variant_ids"), list)
            else []
        ),
        "checks": [
            {
                "condition_id": str(row.get("condition_id") or "UNKNOWN")[:96],
                "status": str(row.get("status") or "BLOCK")[:32],
                "triggered": row.get("triggered") is True,
                "blockers": _strings(row.get("blockers"), limit=8),
            }
            for row in checks[:8]
            if isinstance(row, dict)
        ],
        "blockers": _strings(admission.get("blockers"), limit=24),
    }, []


def _public_hypothesis_mechanism_condition_projection(
    value: Any,
) -> tuple[dict[str, Any] | None, list[str]]:
    row = value if isinstance(value, dict) else {}
    required_fields = {
        "condition_id",
        "evidence_stage",
        "metric",
        "operator",
        "threshold",
        "required_action",
    }
    blockers: list[str] = []
    if set(row) != required_fields:
        blockers.append("public_hypothesis_mechanism_condition_shape_invalid")
    condition_id = str(row.get("condition_id") or "")
    if (
        not 3 <= len(condition_id) <= 64
        or not condition_id[0:1].islower()
        or not condition_id[0:1].isalpha()
        or any(not (character.islower() or character.isdigit() or character == "_") for character in condition_id)
    ):
        blockers.append("public_hypothesis_mechanism_condition_id_invalid")
    evidence_stage = str(row.get("evidence_stage") or "")
    if evidence_stage != MECHANISM_FAILURE_EVIDENCE_STAGE_V2:
        blockers.append("public_hypothesis_mechanism_evidence_stage_invalid")
    metric = str(row.get("metric") or "")
    if metric not in MECHANISM_FAILURE_METRICS_V2:
        blockers.append("public_hypothesis_mechanism_metric_invalid")
    operator = str(row.get("operator") or "")
    if operator not in MECHANISM_FAILURE_OPERATORS_V2:
        blockers.append("public_hypothesis_mechanism_operator_invalid")
    threshold = _number(row.get("threshold"))
    if threshold is None:
        blockers.append("public_hypothesis_mechanism_threshold_invalid")
    required_action = str(row.get("required_action") or "")
    if required_action != MECHANISM_FAILURE_REQUIRED_ACTION_V2:
        blockers.append("public_hypothesis_mechanism_required_action_invalid")
    projected = {
        "condition_id": condition_id[:64],
        "evidence_stage": evidence_stage,
        "metric": metric,
        "operator": operator,
        "threshold": threshold,
        "required_action": required_action,
    }
    return (projected if not blockers else None), blockers


def _hypothesis_projection(report: dict[str, Any], strategy_id: str) -> dict[str, Any]:
    batch_spec = report.get("batch_spec")
    batch_spec = batch_spec if isinstance(batch_spec, dict) else {}
    report_schema_version = report.get("schema_version")
    capabilities = _PUBLIC_REPORT_SCHEMA_CAPABILITIES.get(report_schema_version, {})
    hypothesis_capability = capabilities.get("hypothesis")
    uses_hypothesis_v2 = hypothesis_capability == "v2"
    uses_hypothesis_v3 = hypothesis_capability == "v3"
    uses_structured_hypothesis = uses_hypothesis_v2 or uses_hypothesis_v3
    common = {
        "schema_version": (
            STRATEGY_HYPOTHESIS_PREREGISTRATION_SUMMARY_SCHEMA_VERSION_V3
            if uses_hypothesis_v3
            else STRATEGY_HYPOTHESIS_PREREGISTRATION_SUMMARY_SCHEMA_VERSION_V2
            if uses_hypothesis_v2
            else STRATEGY_HYPOTHESIS_PREREGISTRATION_SUMMARY_SCHEMA_VERSION
        ),
        "descriptive_only": True,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "automatic_paper_activation_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    if hypothesis_capability is None:
        return {
            **common,
            "status": "LEGACY_NOT_BOUND",
            "contract_checked": False,
            "hypothesis_id": None,
            "hypothesis_hash": None,
            "research_generation": str(batch_spec.get("research_generation") or "")[:96],
            "strategy_ids": [],
            "selected_strategy_match": None,
            "mechanism_family": None,
            "hypothesis_statement": None,
            "novelty_statement": None,
            "mechanism_specific_failure_conditions": [],
            "parameter_topology_basis": None,
            "numeric_parameter_distance_claimed": None,
            "cost_stress_required": None,
            "stressed_return_must_remain_positive": None,
            "chronological_evaluation_mode": None,
            "parameters_refit_per_fold": None,
            "walk_forward_optimization_claim_allowed": False,
            "fresh_single_use_holdout_required": None,
            "minimum_natural_forward_outcomes": None,
            "minimum_executed_rebalances": None,
            "statistical_contract_recheck_required_at_maturity": None,
            "historical_backtest_can_substitute_natural_forward": None,
            "reuses_falsified_strategy_id": None,
            "retunes_falsified_mechanism": None,
            "material_mechanism_change_requires_new_strategy_id": None,
            "blockers": ["historical_report_predates_hypothesis_preregistration"],
        }

    hypothesis = batch_spec.get("hypothesis_preregistration")
    verification = verify_strategy_hypothesis_preregistration(
        hypothesis,
        expected_strategy_ids=[
            str(item or "") for item in (
                batch_spec.get("strategies")
                if isinstance(batch_spec.get("strategies"), list)
                else []
            )
        ],
        expected_research_generation=str(batch_spec.get("research_generation") or ""),
        expected_schema_version=(
            STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3
            if uses_hypothesis_v3
            else STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2
            if uses_hypothesis_v2
            else STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION
        ),
    )
    payload = hypothesis if isinstance(hypothesis, dict) else {}
    strategy_ids = [
        str(item).strip().lower()
        for item in (payload.get("strategy_ids") if isinstance(payload.get("strategy_ids"), list) else [])
        if isinstance(item, str) and item.strip()
    ]
    mechanism = payload.get("mechanism")
    mechanism = mechanism if isinstance(mechanism, dict) else {}
    robustness = payload.get("parameter_robustness_contract")
    robustness = robustness if isinstance(robustness, dict) else {}
    cost_time = payload.get("cost_and_time_contract")
    cost_time = cost_time if isinstance(cost_time, dict) else {}
    forward = payload.get("holdout_and_forward_contract")
    forward = forward if isinstance(forward, dict) else {}
    ancestry = payload.get("falsified_ancestry_contract")
    ancestry = ancestry if isinstance(ancestry, dict) else {}
    failure = payload.get("failure_contract")
    failure = failure if isinstance(failure, dict) else {}
    selected_match = bool(strategy_id) and strategy_id in strategy_ids
    blockers = list(verification.get("blockers") or [])
    if not selected_match:
        blockers.append("selected_strategy_not_bound_to_hypothesis")
    mechanism_conditions: list[dict[str, Any]] = []
    if uses_structured_hypothesis:
        raw_conditions = failure.get("mechanism_specific_conditions")
        raw_conditions = raw_conditions if isinstance(raw_conditions, list) else []
        if not 1 <= len(raw_conditions) <= 8:
            blockers.append("public_hypothesis_mechanism_condition_count_invalid")
        for raw_condition in raw_conditions[:8]:
            projected, condition_blockers = (
                _public_hypothesis_mechanism_condition_projection(raw_condition)
            )
            blockers.extend(condition_blockers)
            if projected is not None:
                mechanism_conditions.append(projected)
        condition_ids = [item["condition_id"] for item in mechanism_conditions]
        if len(set(condition_ids)) != len(condition_ids):
            blockers.append("public_hypothesis_mechanism_condition_id_duplicate")
    projection = {
        **common,
        "status": "BOUND" if not blockers else "BLOCK",
        "contract_checked": True,
        "hypothesis_id": str(payload.get("hypothesis_id") or "")[:96] or None,
        "hypothesis_hash": str(payload.get("hypothesis_hash") or "") or None,
        "research_generation": str(payload.get("research_generation") or "")[:96],
        "strategy_ids": strategy_ids[:32],
        "selected_strategy_match": selected_match,
        "mechanism_family": str(mechanism.get("family") or "")[:96] or None,
        "hypothesis_statement": (
            None
            if uses_structured_hypothesis
            else str(mechanism.get("hypothesis_statement") or "")[:480] or None
        ),
        "novelty_statement": (
            None
            if uses_structured_hypothesis
            else str(mechanism.get("novelty_statement") or "")[:480] or None
        ),
        "mechanism_specific_failure_conditions": (
            mechanism_conditions
            if uses_structured_hypothesis
            else _strings(failure.get("mechanism_specific_conditions"), limit=8)
        ),
        "parameter_topology_basis": str(robustness.get("topology_basis") or "")[:80] or None,
        "numeric_parameter_distance_claimed": robustness.get(
            "numeric_parameter_distance_claimed"
        ) if isinstance(robustness.get("numeric_parameter_distance_claimed"), bool) else None,
        "cost_stress_required": cost_time.get("cost_stress_required") if isinstance(
            cost_time.get("cost_stress_required"), bool
        ) else None,
        "stressed_return_must_remain_positive": cost_time.get(
            "stressed_return_must_remain_positive"
        ) if isinstance(cost_time.get("stressed_return_must_remain_positive"), bool) else None,
        "chronological_evaluation_mode": str(
            cost_time.get("chronological_evaluation_mode") or ""
        )[:80] or None,
        "parameters_refit_per_fold": cost_time.get("parameters_refit_per_fold") if isinstance(
            cost_time.get("parameters_refit_per_fold"), bool
        ) else None,
        "walk_forward_optimization_claim_allowed": False,
        "fresh_single_use_holdout_required": forward.get(
            "fresh_single_use_holdout_required"
        ) if isinstance(forward.get("fresh_single_use_holdout_required"), bool) else None,
        "minimum_natural_forward_outcomes": _native_nonnegative_int(
            forward.get("minimum_natural_forward_outcomes")
        ),
        "minimum_executed_rebalances": _native_nonnegative_int(
            forward.get("minimum_executed_rebalances")
        ),
        "statistical_contract_recheck_required_at_maturity": forward.get(
            "statistical_contract_recheck_required_at_maturity"
        ) if isinstance(
            forward.get("statistical_contract_recheck_required_at_maturity"), bool
        ) else None,
        "historical_backtest_can_substitute_natural_forward": forward.get(
            "historical_backtest_can_substitute_natural_forward"
        ) if isinstance(
            forward.get("historical_backtest_can_substitute_natural_forward"), bool
        ) else None,
        "reuses_falsified_strategy_id": ancestry.get("reuses_falsified_strategy_id") if isinstance(
            ancestry.get("reuses_falsified_strategy_id"), bool
        ) else None,
        "retunes_falsified_mechanism": ancestry.get("retunes_falsified_mechanism") if isinstance(
            ancestry.get("retunes_falsified_mechanism"), bool
        ) else None,
        "material_mechanism_change_requires_new_strategy_id": ancestry.get(
            "material_mechanism_change_requires_new_strategy_id"
        ) if isinstance(
            ancestry.get("material_mechanism_change_requires_new_strategy_id"), bool
        ) else None,
        "blockers": list(dict.fromkeys(str(item) for item in blockers))[:24],
    }
    if uses_structured_hypothesis:
        projection["source_schema_version"] = (
            STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3
            if uses_hypothesis_v3
            else STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2
        )
        projection.pop("hypothesis_statement", None)
        projection.pop("novelty_statement", None)
    if uses_hypothesis_v3:
        projection["search_family_bound"] = bool(
            selected_match and str(payload.get("search_family_id") or "")
        )
    return projection


def _cost_projection(cells: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = [str(cell.get("cost_sensitivity_status") or "UNKNOWN") for cell in cells]
    evidence = [
        cell.get("cost_sensitivity")
        for cell in cells
        if isinstance(cell.get("cost_sensitivity"), dict)
    ]
    worst_returns = [
        number for number in (_number(item.get("worst_return_pct")) for item in evidence)
        if number is not None
    ]
    worst_drawdowns = [
        number for number in (_number(item.get("worst_drawdown_pct")) for item in evidence)
        if number is not None
    ]
    break_even_values = [item.get("break_even_preserved") for item in evidence]
    blockers = [
        blocker
        for item in evidence
        for blocker in _strings(item.get("blockers"))
    ]
    return {
        "status": _aggregate_status(statuses),
        "evaluated_cell_count": len(cells),
        "pass_cell_count": sum(value.upper() == "PASS" for value in statuses),
        "worst_stressed_return_pct": min(worst_returns) if worst_returns else None,
        "worst_stressed_drawdown_pct": max(worst_drawdowns) if worst_drawdowns else None,
        "break_even_preserved": (
            all(value is True for value in break_even_values)
            if len(break_even_values) == len(cells) and cells
            else None
        ),
        "blockers": list(dict.fromkeys(blockers))[:24],
        "descriptive_only": True,
        "profitability_proven": False,
    }


def _chronological_projection(cells: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = [str(cell.get("fold_stability_status") or "UNKNOWN") for cell in cells]
    evidence = [
        cell.get("fold_stability")
        for cell in cells
        if isinstance(cell.get("fold_stability"), dict)
    ]
    usable_folds = [
        value for value in (_native_nonnegative_int(item.get("usable_folds")) for item in evidence)
        if value is not None
    ]
    positive_folds = [
        value for value in (_native_nonnegative_int(item.get("positive_folds")) for item in evidence)
        if value is not None
    ]
    worst_drawdowns = [
        number for number in (_number(item.get("worst_drawdown_pct")) for item in evidence)
        if number is not None
    ]
    modes = {
        str(item.get("evaluation_mode") or "UNKNOWN")
        for item in evidence
    }
    blockers = [
        blocker
        for item in evidence
        for blocker in _strings(item.get("blockers"))
    ]
    return {
        "status": _aggregate_status(statuses),
        "evaluation_mode": next(iter(modes)) if len(modes) == 1 else "MIXED_OR_UNKNOWN",
        "evaluated_cell_count": len(cells),
        "pass_cell_count": sum(value.upper() == "PASS" for value in statuses),
        "usable_fold_count": sum(usable_folds) if len(usable_folds) == len(cells) and cells else None,
        "positive_fold_count": sum(positive_folds) if len(positive_folds) == len(cells) and cells else None,
        "worst_drawdown_pct": max(worst_drawdowns) if worst_drawdowns else None,
        "parameters_refit_per_fold": (
            False
            if len(evidence) == len(cells)
            and cells
            and all(item.get("parameters_refit_per_fold") is False for item in evidence)
            else None
        ),
        "walk_forward_optimization_claim_allowed": False,
        "blockers": list(dict.fromkeys(blockers))[:24],
        "descriptive_only": True,
    }


def _signal_implementation_currentness(
    report: dict[str, Any],
    strategy_id: str,
    fingerprint_fn: Callable[[str, dict[str, Any]], str] | None,
) -> dict[str, Any]:
    basis = "FROZEN_STRATEGY_SIGNAL_IMPLEMENTATION_FINGERPRINT"
    if not strategy_id:
        return {
            "schema_version": STRATEGY_SIGNAL_IMPLEMENTATION_CURRENTNESS_SCHEMA_VERSION,
            "status": "NOT_IN_REPORT",
            "basis": basis,
            "checked": False,
            "matches_current": None,
            "frozen_variant_count": 0,
            "matched_variant_count": 0,
            "mismatched_variant_count": 0,
            "blockers": ["strategy_not_in_frozen_research_report"],
            "full_implementation_manifest_checked": False,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    batch_spec = report.get("batch_spec")
    batch_spec = batch_spec if isinstance(batch_spec, dict) else {}
    variants = [
        dict(item)
        for item in (batch_spec.get("variants") if isinstance(batch_spec.get("variants"), list) else [])
        if isinstance(item, dict)
        and str(item.get("strategy_id") or "").strip().lower() == strategy_id
    ]
    blockers: list[str] = []
    matched = 0
    mismatched = 0
    if not variants:
        blockers.append("strategy_signal_implementation_variants_missing")
    if not callable(fingerprint_fn):
        blockers.append("strategy_signal_implementation_fingerprint_provider_missing")
    if callable(fingerprint_fn):
        for variant in variants:
            params = variant.get("params")
            expected = str(variant.get("implementation_fingerprint") or "")
            if not isinstance(params, dict) or not _is_sha256(expected):
                blockers.append("strategy_signal_implementation_identity_invalid")
                continue
            try:
                current = str(fingerprint_fn(strategy_id, dict(params)) or "")
            except Exception:
                current = ""
            if not _is_sha256(current):
                blockers.append("strategy_signal_implementation_current_fingerprint_unavailable")
                continue
            if current == expected:
                matched += 1
            else:
                mismatched += 1

    completed = bool(variants) and matched + mismatched == len(variants) and not blockers
    matches_current = completed and mismatched == 0
    if completed and matches_current:
        status = "MATCH"
    elif completed:
        status = "MISMATCH"
        blockers.append("strategy_signal_implementation_fingerprint_changed")
    else:
        status = "BLOCK" if variants else "UNKNOWN"
    return {
        "schema_version": STRATEGY_SIGNAL_IMPLEMENTATION_CURRENTNESS_SCHEMA_VERSION,
        "status": status,
        "basis": basis,
        "checked": completed,
        "matches_current": matches_current if completed else None,
        "frozen_variant_count": len(variants),
        "matched_variant_count": matched,
        "mismatched_variant_count": mismatched,
        "blockers": list(dict.fromkeys(blockers))[:24],
        "full_implementation_manifest_checked": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _research_source_path_allowed(path: Path) -> bool:
    root = Path(__file__).resolve().parents[2]
    resolved = path.resolve()
    if resolved != root and not resolved.is_relative_to(root):
        return False
    relative = resolved.relative_to(root)
    directory_parts = [part.lower() for part in relative.parts[:-1]]
    if any(part.startswith("runtime") for part in directory_parts):
        return False
    if resolved.name.lower().startswith(".env") or resolved.name.lower() == "config.local.json":
        return False
    return resolved.suffix.lower() == ".py"


def _research_manifest_entrypoints() -> list[Path]:
    return [Path(__file__).resolve().parents[2] / "run_internal_strategy_research.py"]


def _full_implementation_currentness(report: dict[str, Any]) -> dict[str, Any]:
    basis = "FROZEN_IMPLEMENTATION_MANIFEST_EXACT_FILES_AND_RUNTIME"
    manifest = report.get("implementation_manifest")
    report_schema_version = report.get("schema_version")
    if (
        isinstance(report_schema_version, bool)
        or not isinstance(report_schema_version, int)
        or report_schema_version < IMPLEMENTATION_MANIFEST_REPORT_SCHEMA_VERSION
        or not isinstance(manifest, dict)
    ):
        return {
            "schema_version": STRATEGY_FULL_IMPLEMENTATION_CURRENTNESS_SCHEMA_VERSION,
            "status": "NOT_AVAILABLE",
            "basis": basis,
            "checked": False,
            "matches_current": None,
            "expected_source_count": 0,
            "verified_source_count": 0,
            "exact_files_checked": False,
            "runtime_checked": False,
            "blockers": ["research_report_does_not_embed_full_implementation_manifest"],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    try:
        verification = verify_implementation_manifest(
            manifest,
            source_path_allowed=_research_source_path_allowed,
            source_entrypoints=_research_manifest_entrypoints(),
        )
    except Exception:
        verification = {
            "status": "BLOCK",
            "blockers": ["implementation_manifest_verifier_unavailable"],
            "source_count": 0,
        }
    raw_blockers = [str(item) for item in verification.get("blockers") or []]
    incomplete = any(
        item.startswith((
            "implementation_source_unavailable:",
            "implementation_source_path_not_allowed:",
            "implementation_manifest_",
            "implementation_source_type_invalid:",
        ))
        or item in {
            "implementation_source_closure_path_not_allowed",
            "implementation_source_closure_unavailable",
        }
        for item in raw_blockers
    )
    verification_passed = verification.get("status") == "PASS"
    completed = verification_passed or (bool(raw_blockers) and not incomplete)
    if verification_passed:
        status = "MATCH"
        matches_current: bool | None = True
        blockers: list[str] = []
    elif completed:
        status = "MISMATCH"
        matches_current = False
        blockers = ["research_full_implementation_or_runtime_changed"]
    else:
        status = "BLOCK"
        matches_current = None
        blockers = ["research_full_implementation_currentness_unavailable"]
    expected_files = manifest.get("files") if isinstance(manifest.get("files"), list) else []
    source_count = _native_nonnegative_int(verification.get("source_count")) or 0
    return {
        "schema_version": STRATEGY_FULL_IMPLEMENTATION_CURRENTNESS_SCHEMA_VERSION,
        "status": status,
        "basis": basis,
        "checked": completed,
        "matches_current": matches_current,
        "expected_source_count": len(expected_files),
        "verified_source_count": source_count,
        "exact_files_checked": completed,
        "runtime_checked": completed,
        "blockers": blockers,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _evidence_projection(
    report: dict[str, Any],
    pointer: dict[str, Any],
    verification: dict[str, Any],
    *,
    requested_strategy_id: str,
    implementation_fingerprint_fn: Callable[[str, dict[str, Any]], str] | None,
    observed_at_ms: int | None,
) -> dict[str, Any]:
    report_schema_version = report.get("schema_version")
    capabilities = _PUBLIC_REPORT_SCHEMA_CAPABILITIES.get(report_schema_version)
    if capabilities is None:
        return _unknown_snapshot(
            ["strategy_research_public_schema_unsupported"],
            requested_strategy_id=requested_strategy_id,
        )
    batch_spec = report.get("batch_spec")
    batch_spec = batch_spec if isinstance(batch_spec, dict) else {}
    strategy_ids = [
        str(value).strip().lower()
        for value in (batch_spec.get("strategies") if isinstance(batch_spec.get("strategies"), list) else [])
        if str(value).strip()
    ]
    requested = str(requested_strategy_id or "").strip().lower()
    selected_strategy = requested if requested in strategy_ids else strategy_ids[0] if not requested and strategy_ids else ""
    matching_cells = [
        cell for cell in (
            report.get("selection_cells") if isinstance(report.get("selection_cells"), list) else []
        )
        if isinstance(cell, dict)
        and str(cell.get("strategy_id") or "").strip().lower() == selected_strategy
    ]
    summary = report.get("summary")
    summary = summary if isinstance(summary, dict) else {}
    selection_alignment = report.get("selection_alignment")
    selection_alignment = selection_alignment if isinstance(selection_alignment, dict) else {}
    governance = report.get("research_governance")
    governance = governance if isinstance(governance, dict) else {}
    plateau = _plateau_projection(report, selected_strategy)
    hypothesis = _hypothesis_projection(report, selected_strategy)
    if capabilities.get("search_lineage") == "v1":
        search_lineage, search_lineage_projection_blockers = (
            _public_search_lineage_projection(report, selected_strategy)
        )
    else:
        search_lineage = None
        search_lineage_projection_blockers = []
    (
        preregistered_failure_admission,
        admission_projection_blockers,
    ) = _preregistered_failure_admission_projection(
        report,
        selected_strategy,
        search_lineage=search_lineage,
    )
    capability_blockers: list[str] = []
    if capabilities.get("hypothesis") in {"v2", "v3"}:
        uses_hypothesis_v3 = capabilities.get("hypothesis") == "v3"
        expected_hypothesis_summary_schema = (
            STRATEGY_HYPOTHESIS_PREREGISTRATION_SUMMARY_SCHEMA_VERSION_V3
            if uses_hypothesis_v3
            else STRATEGY_HYPOTHESIS_PREREGISTRATION_SUMMARY_SCHEMA_VERSION_V2
        )
        expected_hypothesis_source_schema = (
            STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3
            if uses_hypothesis_v3
            else STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2
        )
        hypothesis_contract_blocker = (
            "public_hypothesis_v3_contract_invalid"
            if uses_hypothesis_v3
            else "public_hypothesis_v2_contract_invalid"
        )
        if (
            hypothesis.get("schema_version")
            != expected_hypothesis_summary_schema
            or hypothesis.get("source_schema_version")
            != expected_hypothesis_source_schema
            or (
                uses_hypothesis_v3
                and hypothesis.get("search_family_bound")
                is not bool(selected_strategy)
            )
        ):
            capability_blockers.append(hypothesis_contract_blocker)
        hypothesis_blockers = _strings(hypothesis.get("blockers"), limit=24)
        if selected_strategy:
            if hypothesis.get("status") != "BOUND":
                capability_blockers.append(hypothesis_contract_blocker)
            capability_blockers.extend(hypothesis_blockers)
        else:
            if (
                hypothesis.get("status") != "BLOCK"
                or hypothesis.get("selected_strategy_match") is not False
            ):
                capability_blockers.append(
                    "public_hypothesis_v3_not_in_report_contract_invalid"
                    if uses_hypothesis_v3
                    else "public_hypothesis_v2_not_in_report_contract_invalid"
                )
            capability_blockers.extend(
                blocker for blocker in hypothesis_blockers
                if blocker != "selected_strategy_not_bound_to_hypothesis"
            )
    if capabilities.get("search_lineage") == "v1":
        expected_lineage_status = "BOUND" if selected_strategy else "NOT_IN_REPORT"
        if (
            not isinstance(search_lineage, dict)
            or search_lineage.get("schema_version")
            != STRATEGY_RESEARCH_SEARCH_LINEAGE_PUBLIC_SCHEMA_VERSION
            or search_lineage.get("status") != expected_lineage_status
        ):
            capability_blockers.append("public_search_lineage_contract_invalid")
        capability_blockers.extend(search_lineage_projection_blockers)
    if capabilities.get("admission") in {"v2", "v3"}:
        uses_admission_v3 = capabilities.get("admission") == "v3"
        expected_admission_schema = (
            STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION_V3
            if uses_admission_v3
            else STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION_V2
        )
        if (
            preregistered_failure_admission.get("schema_version")
            != expected_admission_schema
            or (
                uses_admission_v3
                and preregistered_failure_admission.get("search_lineage_status")
                != ("BOUND" if selected_strategy else "NOT_IN_REPORT")
            )
        ):
            capability_blockers.append(
                "public_admission_v3_contract_invalid"
                if uses_admission_v3
                else "public_admission_v2_contract_invalid"
            )
        capability_blockers.extend(admission_projection_blockers)
    if capability_blockers:
        return _unknown_snapshot(
            [
                "strategy_research_public_capability_contract_invalid",
                *list(dict.fromkeys(capability_blockers)),
            ],
            requested_strategy_id=requested_strategy_id,
        )
    cost = _cost_projection(matching_cells)
    chronological = _chronological_projection(matching_cells)
    implementation_currentness = _signal_implementation_currentness(
        report,
        selected_strategy,
        implementation_fingerprint_fn,
    )
    full_implementation_currentness = _full_implementation_currentness(report)
    currentness_facts = build_strategy_research_currentness_facts(
        report_created_at=report.get("created_at"),
        summary_common_as_of=summary.get("common_as_of"),
        selection_common_as_of=selection_alignment.get("common_as_of"),
        observed_at_ms=observed_at_ms,
    )
    uses_post_selection_replay_summary = capabilities.get("replay") == "v1"
    try:
        post_selection_replay_summary = (
            build_strategy_post_selection_replay_summary(
                report,
                strategy_id=selected_strategy,
            )
            if uses_post_selection_replay_summary
            else None
        )
    except (TypeError, ValueError):
        return _unknown_snapshot(
            ["strategy_research_post_selection_projection_blocked"],
            requested_strategy_id=requested_strategy_id,
        )
    failure_capability = capabilities.get("failure")
    failure_builder = {
        "v1": build_strategy_research_failure_conditions,
        "v2": build_strategy_research_failure_conditions_v2,
        "v3": build_strategy_research_failure_conditions_v3,
        "v4": build_strategy_research_failure_conditions_v4,
    }[str(failure_capability)]
    failure_kwargs = {
        "strategy_id": selected_strategy,
        "parameter_stability": plateau,
        "cost_sensitivity": cost,
        "chronological_slices": chronological,
        "implementation_currentness": implementation_currentness,
        "full_implementation_currentness": full_implementation_currentness,
    }
    if uses_post_selection_replay_summary:
        failure_kwargs["post_selection_replay_summary"] = (
            post_selection_replay_summary
        )
    if failure_capability in {"v3", "v4"}:
        failure_kwargs["preregistered_failure_admission"] = (
            preregistered_failure_admission
        )
    if failure_capability == "v4":
        failure_kwargs["search_lineage"] = search_lineage
    failure_conditions = failure_builder(**failure_kwargs)
    strategy_match_status = "MATCHED" if selected_strategy else "NOT_IN_REPORT"
    uses_preregistered_failure_admission = capabilities.get("admission") in {
        "v1",
        "v2",
        "v3",
    }
    evidence_contract_schema_version = {
        "v3": STRATEGY_LAB_FROZEN_EVIDENCE_SCHEMA_VERSION_V3,
        "v5": STRATEGY_LAB_FROZEN_EVIDENCE_SCHEMA_VERSION_V5,
        "v6": STRATEGY_LAB_FROZEN_EVIDENCE_SCHEMA_VERSION_V6,
        "v7": STRATEGY_LAB_FROZEN_EVIDENCE_SCHEMA_VERSION_V7,
    }[str(capabilities.get("evidence"))]
    projection = {
        "ok": True,
        "status": "AVAILABLE",
        "source_verification_status": "PASS",
        "blockers": [],
        "pointer_schema_version": STRATEGY_RESEARCH_POINTER_SCHEMA_VERSION,
        "pointer_hash": str(pointer.get("pointer_hash") or ""),
        "report_schema_version": report.get("schema_version"),
        "created_at": str(report.get("created_at") or ""),
        "created_at_ms": _created_at_ms(report.get("created_at")),
        "batch_spec_hash": str(report.get("batch_spec_hash") or ""),
        "dataset_manifest_hash": str(report.get("dataset_manifest_hash") or ""),
        "batch_run_hash": str(report.get("batch_run_hash") or ""),
        "governance_status": str(governance.get("status") or "UNKNOWN")[:64],
        "formal_single_use": verification.get("formal_single_use") is True,
        "selection_test_policy": str(batch_spec.get("selection_test_policy") or "UNKNOWN")[:32],
        "research_generation": str(batch_spec.get("research_generation") or "")[:96],
        "requested_strategy_id": requested,
        "selected_strategy_id": selected_strategy or None,
        "strategy_match_status": strategy_match_status,
        "available_strategy_ids": strategy_ids[:32],
        "scope": {
            "strategy_count": _native_nonnegative_int(summary.get("strategies")),
            "parameter_variant_count": _native_nonnegative_int(summary.get("parameter_variants")),
            "selection_symbol_count": _native_nonnegative_int(summary.get("selection_symbols")),
            "selection_cell_count": _native_nonnegative_int(summary.get("selection_cells")),
            "frozen_test_candidate_count": _native_nonnegative_int(summary.get("frozen_test_candidates")),
            "test_cell_count": _native_nonnegative_int(summary.get("test_cells")),
            "forward_candidate_count": _native_nonnegative_int(summary.get("forward_candidates")),
        },
        "evidence_contract": {
            "schema_version": evidence_contract_schema_version,
            "connection_status": "VERIFIED_FROZEN_SOURCE",
            "mode": "FROZEN_RESEARCH_EVIDENCE",
            "research_report_source": _POINTER_STATUS,
            "interpretation": "DESCRIPTIVE_RESEARCH_EVIDENCE_ONLY",
            "strategy_match_status": strategy_match_status,
            "parameter_stability_status": str(plateau.get("status") or "UNKNOWN"),
            "hypothesis_preregistration_status": str(
                hypothesis.get("status") or "UNKNOWN"
            ),
            "cost_sensitivity_status": str(cost.get("status") or "UNKNOWN"),
            "chronological_slice_status": str(chronological.get("status") or "UNKNOWN"),
            "research_only": True,
            "descriptive_only": True,
            "development_heuristic_only": False,
            "profitability_proven": False,
            "performance_claim_allowed": False,
            "parameter_selection_allowed": False,
            "implementation_currentness_checked": implementation_currentness["checked"],
            "implementation_currentness_status": implementation_currentness["status"],
            "implementation_currentness_match": implementation_currentness["matches_current"],
            "implementation_currentness_basis": implementation_currentness["basis"],
            "full_implementation_manifest_checked": full_implementation_currentness["checked"],
            "full_implementation_manifest_status": full_implementation_currentness["status"],
            "full_implementation_manifest_match": full_implementation_currentness["matches_current"],
            "full_implementation_manifest_basis": full_implementation_currentness["basis"],
            "currentness_facts_schema_version": STRATEGY_RESEARCH_CURRENTNESS_FACTS_SCHEMA_VERSION,
            "currentness_facts_status": currentness_facts["status"],
            "currentness_threshold_applied": False,
            "dataset_currentness_checked": False,
            "report_age_policy_checked": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "parameter_stability": plateau,
        "hypothesis_preregistration": hypothesis,
        "cost_sensitivity": cost,
        "chronological_slices": chronological,
        "implementation_currentness": implementation_currentness,
        "full_implementation_currentness": full_implementation_currentness,
        "currentness_facts": currentness_facts,
        "failure_conditions": failure_conditions,
        "read_only": True,
        "research_only": True,
        "descriptive_only": True,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "implementation_currentness_checked": implementation_currentness["checked"],
        "implementation_currentness_status": implementation_currentness["status"],
        "implementation_currentness_match": implementation_currentness["matches_current"],
        "implementation_currentness_basis": implementation_currentness["basis"],
        "full_implementation_manifest_checked": full_implementation_currentness["checked"],
        "full_implementation_manifest_status": full_implementation_currentness["status"],
        "full_implementation_manifest_match": full_implementation_currentness["matches_current"],
        "full_implementation_manifest_basis": full_implementation_currentness["basis"],
        "currentness_facts_status": currentness_facts["status"],
        "dataset_currentness_checked": False,
        "report_age_policy_checked": False,
        "automatic_paper_activation_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    if capabilities.get("evidence") == "v6":
        projection["evidence_contract"].update({
            "hypothesis_preregistration_schema_version": (
                STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2
            ),
            "preregistered_failure_admission_schema_version": (
                STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION_V2
            ),
            "failure_conditions_schema_version": (
                STRATEGY_RESEARCH_FAILURE_CONDITIONS_SCHEMA_VERSION_V3
            ),
        })
    if capabilities.get("evidence") == "v7":
        projection["evidence_contract"].update({
            "hypothesis_preregistration_schema_version": (
                STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3
            ),
            "preregistered_failure_admission_schema_version": (
                STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION_V3
            ),
            "failure_conditions_schema_version": (
                STRATEGY_RESEARCH_FAILURE_CONDITIONS_SCHEMA_VERSION_V4
            ),
            "search_lineage_schema_version": (
                STRATEGY_RESEARCH_SEARCH_LINEAGE_PUBLIC_SCHEMA_VERSION
            ),
            "search_lineage_status": str(
                (search_lineage or {}).get("status") or "BLOCK"
            ),
        })
        projection["search_lineage_status"] = str(
            (search_lineage or {}).get("status") or "BLOCK"
        )
        projection["search_lineage"] = search_lineage
    if uses_preregistered_failure_admission:
        projection["preregistered_failure_admission_status"] = str(
            preregistered_failure_admission.get("status") or "BLOCK"
        )
        projection["evidence_contract"][
            "preregistered_failure_admission_status"
        ] = str(preregistered_failure_admission.get("status") or "BLOCK")
        projection[
            "preregistered_failure_admission"
        ] = preregistered_failure_admission
    if uses_post_selection_replay_summary:
        replay_status = str(
            (post_selection_replay_summary or {}).get("status") or "BLOCK"
        )
        projection["post_selection_replay_status"] = replay_status
        projection["evidence_contract"][
            "post_selection_replay_status"
        ] = replay_status
        projection["post_selection_replay_summary"] = (
            post_selection_replay_summary
        )
    return projection


def _unknown_snapshot(blockers: list[str], *, requested_strategy_id: str) -> dict[str, Any]:
    return {
        "ok": False,
        "status": "UNKNOWN",
        "source_verification_status": "BLOCK",
        "blockers": list(dict.fromkeys(blockers or ["strategy_research_pointer_unavailable"])),
        "pointer_schema_version": STRATEGY_RESEARCH_POINTER_SCHEMA_VERSION,
        "pointer_hash": None,
        "report_schema_version": None,
        "created_at": None,
        "created_at_ms": None,
        "batch_spec_hash": None,
        "dataset_manifest_hash": None,
        "batch_run_hash": None,
        "governance_status": "UNKNOWN",
        "formal_single_use": False,
        "selection_test_policy": "UNKNOWN",
        "research_generation": "",
        "requested_strategy_id": str(requested_strategy_id or "").strip().lower(),
        "selected_strategy_id": None,
        "strategy_match_status": "UNKNOWN",
        "available_strategy_ids": [],
        "scope": {},
        "evidence_contract": None,
        "parameter_stability": None,
        "hypothesis_preregistration": None,
        "cost_sensitivity": None,
        "chronological_slices": None,
        "implementation_currentness": None,
        "full_implementation_currentness": None,
        "currentness_facts": None,
        "currentness_facts_status": "UNKNOWN",
        "failure_conditions": None,
        "read_only": True,
        "research_only": True,
        "descriptive_only": True,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "implementation_currentness_checked": False,
        "implementation_currentness_status": "UNKNOWN",
        "implementation_currentness_match": None,
        "implementation_currentness_basis": "FROZEN_STRATEGY_SIGNAL_IMPLEMENTATION_FINGERPRINT",
        "full_implementation_manifest_checked": False,
        "full_implementation_manifest_status": "UNKNOWN",
        "full_implementation_manifest_match": None,
        "full_implementation_manifest_basis": "FROZEN_IMPLEMENTATION_MANIFEST_EXACT_FILES_AND_RUNTIME",
        "dataset_currentness_checked": False,
        "report_age_policy_checked": False,
        "automatic_paper_activation_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def load_strategy_research_evidence_snapshot(
    report_dir: Path | str,
    *,
    strategy_id: str = "",
    implementation_fingerprint_fn: Callable[[str, dict[str, Any]], str] | None = None,
    observed_at_ms: int | None = None,
) -> dict[str, Any]:
    try:
        directory, pointer_path = _fixed_pointer_path(report_dir)
        pointer = _read_json_object(pointer_path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return _unknown_snapshot(
            ["strategy_research_pointer_unavailable"],
            requested_strategy_id=strategy_id,
        )

    report_file = str(pointer.get("report_file") or "")
    if (
        _windows_canonical_basename(report_file) is None
        or _windows_canonical_basename(report_file)
        == _windows_canonical_basename(DEFAULT_STRATEGY_RESEARCH_POINTER_FILE)
    ):
        return _unknown_snapshot(
            ["strategy_research_pointer_basename_invalid"],
            requested_strategy_id=strategy_id,
        )
    report_path = (directory / report_file).resolve()
    if report_path.parent != directory:
        return _unknown_snapshot(
            ["strategy_research_report_parent_invalid"],
            requested_strategy_id=strategy_id,
        )
    try:
        report_raw = report_path.read_bytes()
        report = _read_json_object(report_raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return _unknown_snapshot(
            ["strategy_research_report_unavailable"],
            requested_strategy_id=strategy_id,
        )

    verification = verify_strategy_research_report_pointer(
        pointer,
        report=report,
        report_file_sha256=_file_sha256(report_raw),
    )
    if verification.get("status") != "PASS":
        return _unknown_snapshot(
            list(verification.get("blockers") or ["strategy_research_pointer_verification_blocked"]),
            requested_strategy_id=strategy_id,
        )
    return _evidence_projection(
        report,
        pointer,
        verification,
        requested_strategy_id=strategy_id,
        implementation_fingerprint_fn=implementation_fingerprint_fn,
        observed_at_ms=observed_at_ms,
    )


__all__ = [
    "DEFAULT_STRATEGY_RESEARCH_POINTER_FILE",
    "STRATEGY_LAB_FROZEN_EVIDENCE_SCHEMA_VERSION",
    "STRATEGY_LAB_FROZEN_EVIDENCE_SCHEMA_VERSION_V3",
    "STRATEGY_LAB_FROZEN_EVIDENCE_SCHEMA_VERSION_V4",
    "STRATEGY_LAB_FROZEN_EVIDENCE_SCHEMA_VERSION_V5",
    "STRATEGY_LAB_FROZEN_EVIDENCE_SCHEMA_VERSION_V6",
    "STRATEGY_LAB_FROZEN_EVIDENCE_SCHEMA_VERSION_V7",
    "STRATEGY_RESEARCH_FAILURE_CONDITIONS_SCHEMA_VERSION",
    "STRATEGY_RESEARCH_FAILURE_CONDITIONS_SCHEMA_VERSION_V2",
    "STRATEGY_RESEARCH_FAILURE_CONDITIONS_SCHEMA_VERSION_V3",
    "STRATEGY_RESEARCH_FAILURE_CONDITIONS_SCHEMA_VERSION_V4",
    "STRATEGY_RESEARCH_POINTER_SCHEMA_VERSION",
    "STRATEGY_RESEARCH_POINTER_PUBLICATION_EXPECTATION_SCHEMA_VERSION",
    "STRATEGY_RESEARCH_SEARCH_LINEAGE_PUBLIC_SCHEMA_VERSION",
    "STRATEGY_FULL_IMPLEMENTATION_CURRENTNESS_SCHEMA_VERSION",
    "STRATEGY_RESEARCH_CURRENTNESS_FACTS_SCHEMA_VERSION",
    "STRATEGY_SIGNAL_IMPLEMENTATION_CURRENTNESS_SCHEMA_VERSION",
    "build_strategy_research_pointer_publication_expectation",
    "load_strategy_research_evidence_snapshot",
    "publish_strategy_research_report_pointer",
    "strategy_research_pointer_publication_eligibility",
    "verify_strategy_research_report_pointer",
    "verify_strategy_research_pointer_publication_receipt",
]
