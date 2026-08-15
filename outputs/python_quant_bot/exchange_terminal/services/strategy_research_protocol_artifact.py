from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any
import uuid


STRATEGY_RESEARCH_PROTOCOL_ARTIFACT_PLAN_SCHEMA_VERSION = (
    "strategy-research-protocol-artifact-plan-v2"
)
STRATEGY_RESEARCH_PROTOCOL_ARTIFACT_BINDING_SCHEMA_VERSION = (
    "strategy-research-protocol-artifact-binding-v1"
)
STRATEGY_RESEARCH_PROTOCOL_ARTIFACT_MODE = "IMMUTABLE_NO_CLOBBER"
DEFAULT_STRATEGY_RESEARCH_REPORT_POINTER_FILE = "current_strategy_research_report.json"


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _reserved_registry_paths(registry_path: Path | str) -> set[str]:
    registry = Path(registry_path).resolve()
    return {
        str(registry).casefold(),
        str(Path(f"{registry}-wal").resolve()).casefold(),
        str(Path(f"{registry}-shm").resolve()).casefold(),
        str(Path(f"{registry}-journal").resolve()).casefold(),
    }


def plan_strategy_research_protocol_artifact(
    report_dir: Path | str,
    *,
    registration_id: str,
    registry_path: Path | str,
    requested_output: Path | str | None = None,
) -> dict[str, Any]:
    """Plan one immutable protocol sidecar without reading or writing files."""

    directory = Path(report_dir).resolve()
    clean_registration_id = str(registration_id or "").strip()
    output = (
        Path(requested_output).resolve()
        if str(requested_output or "").strip()
        else (directory / f"strategy_research_protocol_{clean_registration_id}.json").resolve()
    )
    blockers: list[str] = []
    if not clean_registration_id:
        blockers.append("strategy_research_protocol_registration_id_missing")
    if output.parent != directory:
        blockers.append("strategy_research_protocol_output_parent_invalid")
    if output.name.casefold() == DEFAULT_STRATEGY_RESEARCH_REPORT_POINTER_FILE.casefold():
        blockers.append("strategy_research_protocol_output_collides_with_report_pointer")
    if str(output).casefold() in _reserved_registry_paths(registry_path):
        blockers.append("strategy_research_protocol_output_collides_with_registry")
    if output.suffix.casefold() != ".json":
        blockers.append("strategy_research_protocol_output_type_invalid")
    return {
        "schema_version": STRATEGY_RESEARCH_PROTOCOL_ARTIFACT_PLAN_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "output_path": output,
        "artifact_binding": build_strategy_research_protocol_artifact_binding(output),
        "write_before_registration_required": True,
    }


def build_strategy_research_protocol_artifact_binding(
    output_path: Path | str,
) -> dict[str, Any]:
    return {
        "schema_version": STRATEGY_RESEARCH_PROTOCOL_ARTIFACT_BINDING_SCHEMA_VERSION,
        "path": str(Path(output_path).resolve()),
        "mode": STRATEGY_RESEARCH_PROTOCOL_ARTIFACT_MODE,
        "payload_contract": "CANONICAL_FULL_PROTOCOL_JSON",
        "required_at_registration": True,
        "required_at_claim": True,
    }


def verify_strategy_research_protocol_artifact_binding(
    binding: dict[str, Any] | Any,
    *,
    expected_path: Path | str | None = None,
) -> dict[str, Any]:
    payload = dict(binding) if isinstance(binding, dict) else {}
    blockers: list[str] = []
    expected_fields = {
        "schema_version",
        "path",
        "mode",
        "payload_contract",
        "required_at_registration",
        "required_at_claim",
    }
    if not isinstance(binding, dict):
        blockers.append("strategy_research_protocol_artifact_binding_type_invalid")
    elif set(payload) != expected_fields:
        blockers.append("strategy_research_protocol_artifact_binding_fields_invalid")
    if payload.get("schema_version") != STRATEGY_RESEARCH_PROTOCOL_ARTIFACT_BINDING_SCHEMA_VERSION:
        blockers.append("strategy_research_protocol_artifact_binding_schema_invalid")
    raw_path = str(payload.get("path") or "").strip()
    if not raw_path or not Path(raw_path).is_absolute():
        blockers.append("strategy_research_protocol_artifact_binding_path_invalid")
    elif expected_path is not None and Path(raw_path).resolve() != Path(expected_path).resolve():
        blockers.append("strategy_research_protocol_artifact_binding_path_mismatch")
    if payload.get("mode") != STRATEGY_RESEARCH_PROTOCOL_ARTIFACT_MODE:
        blockers.append("strategy_research_protocol_artifact_binding_mode_invalid")
    if payload.get("payload_contract") != "CANONICAL_FULL_PROTOCOL_JSON":
        blockers.append("strategy_research_protocol_artifact_binding_payload_contract_invalid")
    if payload.get("required_at_registration") is not True:
        blockers.append("strategy_research_protocol_artifact_registration_requirement_missing")
    if payload.get("required_at_claim") is not True:
        blockers.append("strategy_research_protocol_artifact_claim_requirement_missing")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "artifact_path": Path(raw_path).resolve() if raw_path and Path(raw_path).is_absolute() else None,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def load_strategy_research_protocol_artifact(
    output_path: Path | str,
) -> dict[str, Any]:
    try:
        payload = json.loads(Path(output_path).resolve().read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {
            "status": "BLOCK",
            "blockers": ["strategy_research_protocol_artifact_unavailable"],
            "protocol": None,
        }
    if not isinstance(payload, dict):
        return {
            "status": "BLOCK",
            "blockers": ["strategy_research_protocol_artifact_type_invalid"],
            "protocol": None,
        }
    return {"status": "PASS", "blockers": [], "protocol": payload}


def verify_existing_strategy_research_protocol_artifact(
    existing_payload: dict[str, Any] | Any,
    expected_protocol: dict[str, Any] | Any,
) -> dict[str, Any]:
    """Accept an existing sidecar only when it is the exact canonical protocol."""

    blockers: list[str] = []
    if not isinstance(existing_payload, dict):
        blockers.append("strategy_research_protocol_existing_type_invalid")
    if not isinstance(expected_protocol, dict):
        blockers.append("strategy_research_protocol_expected_type_invalid")
    existing_hash = _canonical_hash(existing_payload) if isinstance(existing_payload, dict) else ""
    expected_hash = _canonical_hash(expected_protocol) if isinstance(expected_protocol, dict) else ""
    if existing_hash != expected_hash or existing_payload != expected_protocol:
        blockers.append("strategy_research_protocol_existing_content_mismatch")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "identical": not blockers,
        "write_required": False,
        "artifact_hash": expected_hash if not blockers else "",
    }


def verify_bound_strategy_research_protocol_artifact(
    protocol: dict[str, Any] | Any,
) -> dict[str, Any]:
    payload = dict(protocol) if isinstance(protocol, dict) else {}
    binding_verification = verify_strategy_research_protocol_artifact_binding(
        payload.get("protocol_artifact")
    )
    blockers = list(binding_verification.get("blockers") or [])
    artifact_path = binding_verification.get("artifact_path")
    registry_text = str(payload.get("registry_path") or "").strip()
    registry_path = Path(registry_text).resolve() if registry_text and Path(registry_text).is_absolute() else None
    if isinstance(artifact_path, Path):
        basename = artifact_path.name.casefold()
        if (
            artifact_path.suffix.casefold() != ".json"
            or basename.startswith(".env")
            or basename == "config.local.json"
            or basename == DEFAULT_STRATEGY_RESEARCH_REPORT_POINTER_FILE.casefold()
        ):
            blockers.append("strategy_research_protocol_artifact_path_forbidden")
        if artifact_path.parent.name.casefold() != "reports":
            blockers.append("strategy_research_protocol_artifact_report_root_invalid")
        if registry_path is None:
            blockers.append("strategy_research_protocol_artifact_registry_path_invalid")
        else:
            try:
                registry_path.relative_to(artifact_path.parent.parent)
            except ValueError:
                blockers.append("strategy_research_protocol_artifact_registry_root_mismatch")
            if str(artifact_path).casefold() in _reserved_registry_paths(registry_path):
                blockers.append("strategy_research_protocol_artifact_registry_collision")
    loaded: dict[str, Any] = {"status": "BLOCK", "protocol": None}
    if not blockers and isinstance(artifact_path, Path):
        loaded = load_strategy_research_protocol_artifact(artifact_path)
        blockers.extend(loaded.get("blockers") or [])
    if not blockers:
        content_verification = verify_existing_strategy_research_protocol_artifact(
            loaded.get("protocol"),
            payload,
        )
        blockers.extend(content_verification.get("blockers") or [])
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "artifact_hash": _canonical_hash(payload) if not blockers else "",
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def publish_strategy_research_protocol_artifact_no_clobber(
    output_path: Path | str,
    protocol: dict[str, Any],
) -> dict[str, Any]:
    """Publish a complete file atomically without ever replacing the target."""

    output = Path(output_path).resolve()
    binding_verification = verify_strategy_research_protocol_artifact_binding(
        protocol.get("protocol_artifact"),
        expected_path=output,
    )
    if binding_verification.get("status") != "PASS":
        return {
            "status": "BLOCK",
            "blockers": list(binding_verification.get("blockers") or []),
            "published": False,
        }
    if output.exists():
        loaded = load_strategy_research_protocol_artifact(output)
        existing = verify_existing_strategy_research_protocol_artifact(
            loaded.get("protocol"), protocol
        ) if loaded.get("status") == "PASS" else loaded
        return {
            "status": "EXISTING_IDENTICAL" if existing.get("status") == "PASS" else "BLOCK",
            "blockers": list(existing.get("blockers") or []),
            "published": False,
        }

    temporary = output.with_name(f".{output.name}.{uuid.uuid4().hex}.tmp")
    raw = json.dumps(protocol, ensure_ascii=False, indent=2).encode("utf-8")
    try:
        with temporary.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, output)
        except FileExistsError:
            loaded = load_strategy_research_protocol_artifact(output)
            existing = verify_existing_strategy_research_protocol_artifact(
                loaded.get("protocol"), protocol
            ) if loaded.get("status") == "PASS" else loaded
            return {
                "status": "EXISTING_IDENTICAL" if existing.get("status") == "PASS" else "BLOCK",
                "blockers": list(existing.get("blockers") or []),
                "published": False,
            }
    except OSError:
        return {
            "status": "BLOCK",
            "blockers": ["strategy_research_protocol_artifact_atomic_publish_failed"],
            "published": False,
        }
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    post_publish = verify_bound_strategy_research_protocol_artifact(protocol)
    if post_publish.get("status") != "PASS":
        return {
            "status": "BLOCK",
            "blockers": list(post_publish.get("blockers") or []),
            "published": False,
        }
    return {"status": "PUBLISHED", "blockers": [], "published": True}


__all__ = [
    "DEFAULT_STRATEGY_RESEARCH_REPORT_POINTER_FILE",
    "STRATEGY_RESEARCH_PROTOCOL_ARTIFACT_BINDING_SCHEMA_VERSION",
    "STRATEGY_RESEARCH_PROTOCOL_ARTIFACT_MODE",
    "STRATEGY_RESEARCH_PROTOCOL_ARTIFACT_PLAN_SCHEMA_VERSION",
    "build_strategy_research_protocol_artifact_binding",
    "load_strategy_research_protocol_artifact",
    "plan_strategy_research_protocol_artifact",
    "publish_strategy_research_protocol_artifact_no_clobber",
    "verify_bound_strategy_research_protocol_artifact",
    "verify_existing_strategy_research_protocol_artifact",
    "verify_strategy_research_protocol_artifact_binding",
]
