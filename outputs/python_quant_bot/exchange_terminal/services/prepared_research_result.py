from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable
import uuid


PREPARED_RESEARCH_RESULT_SCHEMA_VERSION = "prepared-research-result-v1"
PREPARED_RESEARCH_RESULT_STATUS = "PREPARED_RESULT_NOT_PUBLIC"
_PREPARED_FIELDS = {
    "schema_version",
    "status",
    "workflow",
    "registration_id",
    "protocol_hash",
    "claim_hash",
    "batch_spec_hash",
    "result_hash",
    "dataset_manifest_hash",
    "output_file",
    "report",
    "research_only",
    "paper_authorized",
    "live_order_allowed",
    "prepared_hash",
}
_AUTHORITY_FIELDS = {
    "armed",
    "automatic_paper_activation_allowed",
    "automated_paper_order_allowed",
    "binding_authorized",
    "can_execute",
    "can_trade",
    "direction_signal_allowed",
    "execution_allowed",
    "live_order_allowed",
    "live_ready",
    "live_trading_allowed",
    "live_trading_enabled",
    "mission_authorized",
    "order_allowed",
    "paper_activation_allowed",
    "paper_armed",
    "paper_authorized",
    "paper_order_allowed",
    "paper_ready",
    "parameter_selection_allowed",
    "performance_claim_allowed",
    "performance_claim_proven",
    "profitability_proven",
    "role_assignment_allowed",
    "runtime_mutations_allowed",
    "selection_allowed",
    "trade_allowed",
}


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _valid_sha256(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def _authority_violations(value: Any, prefix: str = "prepared") -> list[str]:
    blockers: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            clean_key = str(key or "").strip().lower()
            path = f"{prefix}.{clean_key}" if clean_key else prefix
            if clean_key in _AUTHORITY_FIELDS and nested is not False:
                blockers.append(f"prepared_result_authority_not_false:{path}")
            blockers.extend(_authority_violations(nested, path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            blockers.extend(_authority_violations(nested, f"{prefix}[{index}]"))
    return blockers


def prepared_research_result_path(
    report_dir: Path | str,
    *,
    protocol_hash: str,
) -> Path:
    clean_hash = str(protocol_hash or "").strip().lower()
    if not _valid_sha256(clean_hash):
        raise ValueError("prepared_result_protocol_hash_invalid")
    directory = Path(report_dir).resolve()
    # A leading dot and a hash-only suffix keep this deterministic while ensuring
    # the artifact never matches strategy_research_*.json or strategy_matrix_*.json.
    output = (directory / f".prepared_research_result_{clean_hash}.json").resolve()
    if output.parent != directory:
        raise ValueError("prepared_result_parent_invalid")
    return output


def build_prepared_research_result(
    *,
    workflow: str,
    registration_id: str,
    protocol_hash: str,
    claim_hash: str,
    batch_spec_hash: str,
    result_hash: str,
    dataset_manifest_hash: str,
    output_file: str,
    report: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema_version": PREPARED_RESEARCH_RESULT_SCHEMA_VERSION,
        "status": PREPARED_RESEARCH_RESULT_STATUS,
        "workflow": str(workflow or "").strip(),
        "registration_id": str(registration_id or "").strip(),
        "protocol_hash": str(protocol_hash or "").strip().lower(),
        "claim_hash": str(claim_hash or "").strip().lower(),
        "batch_spec_hash": str(batch_spec_hash or "").strip().lower(),
        "result_hash": str(result_hash or "").strip().lower(),
        "dataset_manifest_hash": str(dataset_manifest_hash or "").strip().lower(),
        "output_file": str(output_file or "").strip(),
        "report": dict(report or {}),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["prepared_hash"] = canonical_hash(payload)
    return payload


def verify_prepared_research_result(
    prepared: Any,
    *,
    expected_workflow: str,
    expected_protocol: dict[str, Any],
    expected_claim: dict[str, Any],
    report_verifier: Callable[[dict[str, Any]], dict[str, Any]],
    reserved_output_files: set[str] | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    payload = prepared if isinstance(prepared, dict) else {}
    if not isinstance(prepared, dict):
        blockers.append("prepared_result_type_invalid")
    if set(payload) != _PREPARED_FIELDS:
        blockers.append("prepared_result_field_contract_invalid")
    clean = dict(payload)
    expected_prepared_hash = str(clean.pop("prepared_hash", "") or "")
    if not _valid_sha256(expected_prepared_hash) or canonical_hash(clean) != expected_prepared_hash:
        blockers.append("prepared_result_hash_invalid")
    if payload.get("schema_version") != PREPARED_RESEARCH_RESULT_SCHEMA_VERSION:
        blockers.append("prepared_result_schema_invalid")
    if payload.get("status") != PREPARED_RESEARCH_RESULT_STATUS:
        blockers.append("prepared_result_status_invalid")
    if str(payload.get("workflow") or "") != str(expected_workflow or ""):
        blockers.append("prepared_result_workflow_mismatch")

    protocol_hash = str(expected_protocol.get("protocol_hash") or "")
    claim_hash = str(expected_claim.get("claim_hash") or "")
    batch_spec_hash = str(expected_protocol.get("batch_spec_hash") or "")
    expected_bindings = {
        "registration_id": str(expected_protocol.get("registration_id") or ""),
        "protocol_hash": protocol_hash,
        "claim_hash": claim_hash,
        "batch_spec_hash": batch_spec_hash,
    }
    for field, expected in expected_bindings.items():
        if str(payload.get(field) or "") != expected:
            blockers.append(f"prepared_result_{field}_mismatch")
    for field in (
        "protocol_hash",
        "claim_hash",
        "batch_spec_hash",
        "result_hash",
        "dataset_manifest_hash",
    ):
        if not _valid_sha256(payload.get(field)):
            blockers.append(f"prepared_result_{field}_invalid")

    output_file = str(payload.get("output_file") or "")
    reserved = {
        str(item or "").casefold()
        for item in set(reserved_output_files or set())
    }
    if (
        not output_file
        or Path(output_file).name != output_file
        or output_file.casefold() in reserved
    ):
        blockers.append("prepared_result_output_basename_invalid")
    report = payload.get("report")
    if not isinstance(report, dict):
        blockers.append("prepared_result_report_type_invalid")
        report = {}
    if str(report.get("batch_spec_hash") or "") != str(payload.get("batch_spec_hash") or ""):
        blockers.append("prepared_result_report_batch_hash_mismatch")
    if str(report.get("dataset_manifest_hash") or "") != str(payload.get("dataset_manifest_hash") or ""):
        blockers.append("prepared_result_report_dataset_hash_mismatch")
    declared_result_value = (
        report.get("matrix_result_hash")
        if str(expected_workflow or "") == "STRATEGY_MATRIX"
        else report.get("batch_run_hash")
    )
    declared_result_hash = str(declared_result_value or "")
    if declared_result_hash != str(payload.get("result_hash") or ""):
        blockers.append("prepared_result_report_result_hash_mismatch")

    governance = report.get("research_governance")
    governance = governance if isinstance(governance, dict) else {}
    if governance.get("protocol") != expected_protocol:
        blockers.append("prepared_result_report_protocol_mismatch")
    if governance.get("single_use_claim_receipt") != expected_claim:
        blockers.append("prepared_result_report_claim_mismatch")
    completion = governance.get("completion_receipt")
    completion = completion if isinstance(completion, dict) else {}
    if str(completion.get("result_hash") or "") != str(payload.get("result_hash") or ""):
        blockers.append("prepared_result_completion_result_hash_mismatch")
    if str(completion.get("dataset_manifest_hash") or "") != str(
        payload.get("dataset_manifest_hash") or ""
    ):
        blockers.append("prepared_result_completion_dataset_hash_mismatch")

    try:
        report_verification = report_verifier(report)
    except Exception as exc:  # fail closed at the artifact boundary
        report_verification = {
            "status": "BLOCK",
            "blockers": [f"prepared_result_report_verifier_error:{type(exc).__name__}"],
        }
    if report_verification.get("status") != "PASS":
        blockers.extend(
            f"prepared_result_report:{item}"
            for item in report_verification.get("blockers") or ["verification_blocked"]
        )
    if (
        payload.get("research_only") is not True
        or payload.get("paper_authorized") is not False
        or payload.get("live_order_allowed") is not False
    ):
        blockers.append("prepared_result_scope_invalid")
    blockers.extend(_authority_violations(payload))
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "prepared_hash": expected_prepared_hash,
        "output_file": output_file,
        "report": report,
        "completion": completion,
        "report_verification": report_verification,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def publish_json_no_clobber(
    output_path: Path | str,
    payload: dict[str, Any],
    *,
    failure_blocker: str,
) -> dict[str, Any]:
    output = Path(output_path).resolve()
    raw = _json_bytes(payload)
    if output.exists():
        try:
            existing = output.read_bytes()
        except OSError:
            existing = b""
        return {
            "status": "EXISTING_IDENTICAL" if existing == raw else "BLOCK",
            "blockers": [] if existing == raw else [f"{failure_blocker}:target_conflict"],
            "published": False,
            "path": str(output),
        }

    temporary = output.with_name(f".{output.name}.{uuid.uuid4().hex}.tmp")
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        with temporary.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, output)
        except FileExistsError:
            try:
                existing = output.read_bytes()
            except OSError:
                existing = b""
            return {
                "status": "EXISTING_IDENTICAL" if existing == raw else "BLOCK",
                "blockers": [] if existing == raw else [f"{failure_blocker}:target_conflict"],
                "published": False,
                "path": str(output),
            }
    except OSError:
        return {
            "status": "BLOCK",
            "blockers": [failure_blocker],
            "published": False,
            "path": str(output),
        }
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    try:
        persisted = output.read_bytes()
    except OSError:
        persisted = b""
    if persisted != raw:
        return {
            "status": "BLOCK",
            "blockers": [f"{failure_blocker}:post_publish_mismatch"],
            "published": False,
            "path": str(output),
        }
    return {
        "status": "PUBLISHED",
        "blockers": [],
        "published": True,
        "path": str(output),
    }


def publish_prepared_research_result_no_clobber(
    report_dir: Path | str,
    prepared: dict[str, Any],
) -> dict[str, Any]:
    try:
        path = prepared_research_result_path(
            report_dir,
            protocol_hash=str(prepared.get("protocol_hash") or ""),
        )
    except ValueError as exc:
        return {
            "status": "BLOCK",
            "blockers": [str(exc)],
            "published": False,
            "path": "",
        }
    return publish_json_no_clobber(
        path,
        prepared,
        failure_blocker="prepared_result_atomic_publish_failed",
    )


def load_prepared_research_result(
    report_dir: Path | str,
    *,
    protocol_hash: str,
) -> dict[str, Any]:
    try:
        path = prepared_research_result_path(report_dir, protocol_hash=protocol_hash)
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return {
            "status": "BLOCK",
            "blockers": ["prepared_result_unavailable"],
            "path": "",
            "prepared": {},
        }
    if not isinstance(payload, dict):
        return {
            "status": "BLOCK",
            "blockers": ["prepared_result_type_invalid"],
            "path": str(path),
            "prepared": {},
        }
    return {
        "status": "LOADED",
        "blockers": [],
        "path": str(path),
        "prepared": payload,
    }


__all__ = [
    "PREPARED_RESEARCH_RESULT_SCHEMA_VERSION",
    "PREPARED_RESEARCH_RESULT_STATUS",
    "build_prepared_research_result",
    "canonical_hash",
    "load_prepared_research_result",
    "prepared_research_result_path",
    "publish_json_no_clobber",
    "publish_prepared_research_result_no_clobber",
    "verify_prepared_research_result",
]
