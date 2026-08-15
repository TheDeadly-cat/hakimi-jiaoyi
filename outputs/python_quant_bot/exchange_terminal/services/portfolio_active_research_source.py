from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .execution_authority import authority_violations
from .forward_artifact_io import (
    read_forward_json_artifact,
    windows_safe_artifact_basename,
)
from .portfolio_forward import load_active_portfolio_candidate


def _blocked(*blockers: str) -> dict[str, Any]:
    return {
        "ok": False,
        "status": "BLOCK",
        "blockers": list(dict.fromkeys(blockers or ("active_research_source_blocked",))),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _identity(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _research_report_byte_limit() -> int:
    # Keep the limit owned by the existing research-source document contract.
    # Import lazily because portfolio_backtest_pack imports portfolio_forward.
    from .portfolio_backtest_pack import MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES

    return MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES


def _research_report_read_blocker(blocker: str) -> str:
    if blocker == "strict_json_utf8_invalid":
        return "research_report_utf8_invalid"
    if blocker == "strict_json_object_required":
        return "research_report_payload_invalid"
    if blocker.startswith("strict_json_"):
        return "research_report_json_invalid"
    if blocker == "research_report_size_limit_exceeded":
        return blocker
    if blocker == "artifact_bundle_member_link_or_reparse_forbidden":
        return "research_report_link_or_reparse_forbidden"
    if blocker == "portfolio_forward_artifact_memory_exhausted":
        return "research_report_memory_exhausted"
    return "research_report_unavailable"


def load_active_portfolio_research_source(
    report_dir: Path | str,
    *,
    registry_path: Path | str | None = None,
) -> dict[str, Any]:
    """Load the one research report sealed by the verified active candidate receipt.

    The active-candidate service remains the authority for registry, candidate,
    robustness, activation, and completion-receipt verification.  This loader
    adds a narrow, deterministic projection from that verified receipt to the
    exact report bytes used by downstream research tools.
    """

    try:
        directory = Path(report_dir).resolve()
        active = load_active_portfolio_candidate(directory, registry_path=registry_path)
    except Exception:
        # This is a CLI-facing trust boundary.  Upstream diagnostics may carry
        # local paths, so unexpected verification failures collapse to one
        # non-sensitive blocker instead of escaping through a traceback.
        return _blocked("active_candidate_verification_failed")
    if (
        not isinstance(active, dict)
        or active.get("status") != "PASS"
        or active.get("ok") is not True
        or bool(active.get("blockers"))
    ):
        return _blocked("active_candidate_verification_failed")
    completion_verification = active.get("experiment_completion_verification")
    artifact_verification = active.get("experiment_artifact_verification")
    if (
        not isinstance(completion_verification, dict)
        or completion_verification.get("status") != "PASS"
        or not isinstance(artifact_verification, dict)
        or artifact_verification.get("status") != "PASS"
    ):
        return _blocked("active_candidate_completion_verification_failed")

    registry = active.get("registry")
    candidate = active.get("candidate")
    if not isinstance(registry, dict) or not isinstance(candidate, dict):
        return _blocked("active_candidate_contract_invalid")
    receipt = registry.get("experiment_completion_receipt")
    if not isinstance(receipt, dict):
        return _blocked("experiment_completion_receipt_invalid")

    report_file_value = receipt.get("report_file")
    report_file = report_file_value if isinstance(report_file_value, str) else ""
    if windows_safe_artifact_basename(report_file) is None:
        return _blocked("research_report_filename_invalid")
    report_path = directory / report_file
    if report_path.parent != directory:
        return _blocked("research_report_path_escape")

    artifact = read_forward_json_artifact(
        report_path,
        byte_limit=_research_report_byte_limit(),
        size_limit_blocker="research_report_size_limit_exceeded",
    )
    read_completed = artifact.status == "PASS" or artifact.blocker.startswith("strict_json_")
    if not read_completed:
        return _blocked(_research_report_read_blocker(artifact.blocker))

    actual_sha256 = hashlib.sha256(artifact.raw).hexdigest()
    expected_sha256 = _identity(receipt.get("report_file_sha256"))
    if not expected_sha256:
        return _blocked("research_report_file_sha256_missing")
    if actual_sha256 != expected_sha256:
        return _blocked("research_report_file_sha256_mismatch")
    if artifact.status != "PASS":
        return _blocked(_research_report_read_blocker(artifact.blocker))
    report = dict(artifact.payload)
    if authority_violations(report):
        return _blocked("research_report_contains_execution_authority")

    receipt_batch_hash = _identity(receipt.get("batch_run_hash"))
    candidate_batch_hash = _identity(candidate.get("research_report_hash"))
    report_batch_hash = _identity(report.get("batch_run_hash"))
    if not all((receipt_batch_hash, candidate_batch_hash, report_batch_hash)):
        return _blocked("research_report_batch_identity_missing")
    if len({receipt_batch_hash, candidate_batch_hash, report_batch_hash}) != 1:
        return _blocked("research_report_batch_identity_mismatch")

    frozen_candidate = report.get("frozen_candidate")
    if not isinstance(frozen_candidate, dict):
        return _blocked("research_report_frozen_candidate_invalid")
    registry_candidate_hash = _identity(registry.get("candidate_hash"))
    candidate_hash = _identity(candidate.get("candidate_hash"))
    receipt_candidate_hash = _identity(receipt.get("candidate_hash"))
    frozen_candidate_hash = _identity(frozen_candidate.get("candidate_hash"))
    if not all(
        (
            registry_candidate_hash,
            candidate_hash,
            receipt_candidate_hash,
            frozen_candidate_hash,
        )
    ):
        return _blocked("research_report_frozen_identity_missing")
    if len(
        {
            registry_candidate_hash,
            candidate_hash,
            receipt_candidate_hash,
            frozen_candidate_hash,
        }
    ) != 1:
        return _blocked("research_report_frozen_identity_mismatch")

    return {
        "ok": True,
        "status": "PASS",
        "blockers": [],
        "report_path": str(report_path),
        "report_file": report_file,
        "report_file_sha256": actual_sha256,
        "report": report,
        "registry": registry,
        "candidate": candidate,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = ["load_active_portfolio_research_source"]
