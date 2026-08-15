from __future__ import annotations

import hashlib
import json
from pathlib import Path

from exchange_terminal.services.portfolio_experiment import (
    PORTFOLIO_EXPERIMENT_BINDING_VERSION,
    PORTFOLIO_EXPERIMENT_COMPLETION_VERSION,
)
from exchange_terminal.services.trusted_clock import build_trusted_clock_attestation


def canonical_hash(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def attested_clock(stamp: int) -> dict[str, object]:
    evidence = {
        "source": "TEST_CLOCK",
        "endpoint": "https://clock.test/time",
        "status": "PASS",
        "error": "",
        "requested_at_ms": stamp - 10,
        "received_at_ms": stamp + 10,
        "round_trip_ms": 20,
        "midpoint_local_ms": stamp,
        "server_time_ms": stamp,
        "offset_ms": 0,
    }
    evidence["evidence_hash"] = canonical_hash(evidence)
    return build_trusted_clock_attestation(local_now_ms=stamp, provider_evidence=[evidence])


def experiment_binding(
    stamp: int = 1_000_000,
    *,
    experiment_id: str = "pexp-test",
    protocol_hash: str = "protocol-hash",
    implementation_fingerprint: str = "implementation-fingerprint",
) -> dict[str, object]:
    clock = attested_clock(stamp)
    payload: dict[str, object] = {
        "schema_version": PORTFOLIO_EXPERIMENT_BINDING_VERSION,
        "status": "CLAIMED_FOR_SINGLE_RUN",
        "experiment_id": experiment_id,
        "intent_hash": "intent-hash",
        "protocol_hash": protocol_hash,
        "implementation_fingerprint": implementation_fingerprint,
        "registered_at": stamp - 1_000,
        "started_at": stamp,
        "start_clock_attestation_hash": clock["attestation_hash"],
        "start_clock_attestation": clock,
        "consumption_policy": "SINGLE_CLAIM_NO_REPLAY",
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
        "start_event_hash": "start-event-hash",
    }
    payload["binding_hash"] = canonical_hash(payload)
    return payload


def experiment_completion_receipt(
    candidate: dict[str, object],
    *,
    stamp: int = 1_010_000,
    report_path: Path | str | None = None,
    candidate_path: Path | str | None = None,
) -> dict[str, object]:
    governance = candidate.get("research_governance") if isinstance(candidate.get("research_governance"), dict) else {}
    binding = governance.get("experiment_binding") if isinstance(governance.get("experiment_binding"), dict) else {}
    clock = attested_clock(stamp)
    resolved_report = Path(report_path).resolve() if report_path else Path("C:/test/portfolio_research_test.json")
    resolved_candidate = Path(candidate_path).resolve() if candidate_path else Path("C:/test/portfolio_candidate_test.json")
    report_file_hash = hashlib.sha256(resolved_report.read_bytes()).hexdigest() if report_path else "report-file-sha256"
    candidate_file_hash = hashlib.sha256(resolved_candidate.read_bytes()).hexdigest() if candidate_path else "candidate-file-sha256"
    payload: dict[str, object] = {
        "schema_version": PORTFOLIO_EXPERIMENT_COMPLETION_VERSION,
        "status": "COMPLETED",
        "experiment_id": str(binding.get("experiment_id") or "pexp-test"),
        "intent_hash": str(binding.get("intent_hash") or "intent-hash"),
        "protocol_hash": str(binding.get("protocol_hash") or "protocol-hash"),
        "binding_hash": str(binding.get("binding_hash") or "binding-hash"),
        "batch_run_hash": str(candidate.get("research_report_hash") or "report-hash"),
        "dataset_hash": str(candidate.get("dataset_hash") or "data-hash"),
        "report_file": resolved_report.name,
        "report_path": str(resolved_report),
        "report_file_sha256": report_file_hash,
        "candidate_file": resolved_candidate.name,
        "candidate_path": str(resolved_candidate),
        "candidate_file_sha256": candidate_file_hash,
        "candidate_hash": str(candidate.get("candidate_hash") or "candidate-hash"),
        "completed_at": stamp,
        "completion_clock_attestation_hash": clock["attestation_hash"],
        "completion_clock_attestation": clock,
        "artifact_policy": "CONTENT_ADDRESSED_LOCAL_REPORTS",
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
        "completion_event_hash": "completion-event-hash",
    }
    payload["receipt_hash"] = canonical_hash(payload)
    return payload
