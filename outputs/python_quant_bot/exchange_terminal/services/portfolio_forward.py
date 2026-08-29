from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from .execution_authority import authority_violations
from .forward_artifact_io import (
    MAX_PORTFOLIO_FORWARD_CONTROL_ARTIFACT_BYTES,
    read_forward_json_artifact,
    windows_safe_artifact_basename,
)
from .market_calendar import build_market_calendar_contract
from .portfolio_experiment import (
    verify_completion_against_candidate,
    verify_experiment_completion_artifacts,
    verify_experiment_completion_receipt,
)
from .portfolio_forward_scheduler import CAPTURE_DEADLINE_SAFETY_MS, CAPTURE_FINALIZATION_DELAY_MS
from .portfolio_candidate import verify_frozen_portfolio_candidate
from .portfolio_robustness import verify_robustness_report
from .trusted_clock import verify_trusted_clock_attestation


PORTFOLIO_FORWARD_SCHEMA_VERSION = "portfolio-forward-validation-v3"
ACTIVE_CANDIDATE_SCHEMA_VERSION = "active-portfolio-candidate-v3"
ACTIVE_CANDIDATE_DATASET_BINDING_VERSION = "active-candidate-dataset-binding-v1"
ACTIVE_CANDIDATE_REPLACEMENT_GATE_VERSION = "active-candidate-replacement-gate-v1"
ACTIVE_CANDIDATE_VERIFIER_INPUT_CONTRACT_VERSION = "active-candidate-verifier-input-v1"
RETIRED_CANDIDATE_REGISTRY_SCHEMA_VERSION = "retired-portfolio-candidate-v1"
CANDIDATE_RETIREMENT_RECEIPT_SCHEMA_VERSION = "portfolio-candidate-retirement-v1"
DEFAULT_ACTIVE_CANDIDATE_FILE = "active_portfolio_candidate.json"


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _nonnegative_integer(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _portfolio_artifact_byte_limits() -> dict[str, int]:
    # Imported lazily because portfolio_backtest_pack imports this module.  The
    # limits remain owned by the existing artifact contracts rather than
    # being silently redefined at this forward boundary.
    from .portfolio_backtest_pack import (
        MAX_PORTFOLIO_COMPACT_CANDIDATE_BYTES,
        MAX_PORTFOLIO_INTERNAL_BACKTEST_PACK_BYTES,
        MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES,
    )

    return {
        "candidate": MAX_PORTFOLIO_COMPACT_CANDIDATE_BYTES,
        "registry": MAX_PORTFOLIO_FORWARD_CONTROL_ARTIFACT_BYTES,
        "invalidation": MAX_PORTFOLIO_INTERNAL_BACKTEST_PACK_BYTES,
        # The producer labels robustness as a diagnostic-only research
        # document and has no smaller persisted-size contract.  Reuse the
        # established research-document ceiling instead of inventing one.
        "robustness": MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES,
    }


def _read_json_artifact(
    path: Path,
    *,
    byte_limit: int,
    size_limit_blocker: str,
) -> tuple[bytes, dict[str, Any]]:
    result = read_forward_json_artifact(
        path,
        byte_limit=byte_limit,
        size_limit_blocker=size_limit_blocker,
    )
    if result.status != "PASS":
        raise ValueError(result.blocker or "portfolio_forward_artifact_unreadable")
    return result.raw, dict(result.payload)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def verify_active_candidate_activation(registry: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(registry, dict):
        return {
            "input_contract_version": ACTIVE_CANDIDATE_VERIFIER_INPUT_CONTRACT_VERSION,
            "status": "BLOCK",
            "blockers": ["active_candidate_registry_object_required"],
            "activated_at": 0,
            "candidate_hash": "",
            "dataset_binding_version": "",
            "replacement_gate_version": "",
            "registry_hash": "",
            "clock_attestation": {},
            "clock_verification": {"status": "BLOCK"},
            "experiment_completion_receipt": {},
            "experiment_completion_verification": {"status": "BLOCK"},
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    pointer = dict(registry or {})
    blockers: list[str] = []
    expected_hash = str(pointer.get("registry_hash") or "")
    hash_payload = dict(pointer)
    hash_payload.pop("registry_hash", None)
    if str(pointer.get("schema_version") or "") != ACTIVE_CANDIDATE_SCHEMA_VERSION:
        blockers.append("active_candidate_registry_schema_invalid")
    if str(pointer.get("status") or "") != "ACTIVE_RESEARCH_CANDIDATE":
        blockers.append("active_candidate_registry_status_invalid")
    if not expected_hash or _canonical_hash(hash_payload) != expected_hash:
        blockers.append("active_candidate_registry_hash_mismatch")
    dataset_binding_version = str(pointer.get("dataset_binding_version") or "")
    if (
        dataset_binding_version
        and dataset_binding_version != ACTIVE_CANDIDATE_DATASET_BINDING_VERSION
    ):
        blockers.append("active_candidate_dataset_binding_version_invalid")
    replacement_gate_version = str(pointer.get("replacement_gate_version") or "")
    if (
        replacement_gate_version
        and replacement_gate_version != ACTIVE_CANDIDATE_REPLACEMENT_GATE_VERSION
    ):
        blockers.append("active_candidate_replacement_gate_version_invalid")
    if not str(pointer.get("candidate_hash") or ""):
        blockers.append("active_candidate_hash_missing")
    raw_clock = pointer.get("activation_clock_attestation")
    if not isinstance(raw_clock, dict):
        blockers.append("activation_clock_attestation_object_required")
        clock: dict[str, Any] = {}
    else:
        clock = dict(raw_clock)
    clock_verification = verify_trusted_clock_attestation(clock)
    if clock_verification.get("status") != "PASS":
        blockers.extend(
            f"activation_clock:{item}"
            for item in clock_verification.get("blockers") or ["attestation_blocked"]
        )
    activated_at_contract = _nonnegative_integer(pointer.get("activated_at"))
    activated_at = activated_at_contract if activated_at_contract is not None else 0
    attested_at_contract = _nonnegative_integer(clock.get("attested_now_ms"))
    attested_at = attested_at_contract if attested_at_contract is not None else 0
    if activated_at_contract is None or activated_at <= 0:
        blockers.append("candidate_activated_at_invalid")
    if attested_at_contract is None or attested_at <= 0:
        blockers.append("candidate_activation_clock_attested_time_invalid")
    elif activated_at > 0 and abs(activated_at - attested_at) > 5_000:
        blockers.append("candidate_activation_clock_mismatch")
    if str(pointer.get("activation_clock_attestation_hash") or "") != str(clock.get("attestation_hash") or ""):
        blockers.append("candidate_activation_clock_hash_mismatch")
    raw_completion = pointer.get("experiment_completion_receipt")
    if not isinstance(raw_completion, dict):
        blockers.append("experiment_completion_receipt_object_required")
        completion: dict[str, Any] = {}
    else:
        completion = dict(raw_completion)
    completion_verification = verify_experiment_completion_receipt(completion)
    if completion_verification.get("status") != "PASS":
        blockers.extend(
            f"experiment_completion:{item}"
            for item in completion_verification.get("blockers") or ["receipt_blocked"]
        )
    if str(pointer.get("experiment_completion_receipt_hash") or "") != str(completion.get("receipt_hash") or ""):
        blockers.append("experiment_completion_receipt_hash_mismatch")
    if str(pointer.get("candidate_hash") or "") != str(completion.get("candidate_hash") or ""):
        blockers.append("experiment_completion_candidate_hash_mismatch")
    if (
        pointer.get("research_only") is not True
        or pointer.get("paper_authorized") is not False
        or pointer.get("live_order_allowed") is not False
    ):
        blockers.append("active_candidate_registry_execution_authority_invalid")
    if authority_violations(pointer):
        blockers.append("active_candidate_registry_contains_execution_authority")
    return {
        "input_contract_version": ACTIVE_CANDIDATE_VERIFIER_INPUT_CONTRACT_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "activated_at": activated_at,
        "candidate_hash": str(pointer.get("candidate_hash") or ""),
        "dataset_binding_version": dataset_binding_version,
        "replacement_gate_version": replacement_gate_version,
        "registry_hash": expected_hash,
        "clock_attestation": clock,
        "clock_verification": clock_verification,
        "experiment_completion_receipt": completion,
        "experiment_completion_verification": completion_verification,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def verify_candidate_retirement_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    payload = dict(receipt or {})
    blockers: list[str] = []
    expected_hash = str(payload.get("receipt_hash") or "")
    hash_payload = dict(payload)
    hash_payload.pop("receipt_hash", None)
    if str(payload.get("schema_version") or "") != CANDIDATE_RETIREMENT_RECEIPT_SCHEMA_VERSION:
        blockers.append("candidate_retirement_receipt_schema_invalid")
    if str(payload.get("status") or "") != "RETIRED_RESEARCH_CANDIDATE":
        blockers.append("candidate_retirement_receipt_status_invalid")
    if not expected_hash or _canonical_hash(hash_payload) != expected_hash:
        blockers.append("candidate_retirement_receipt_hash_mismatch")
    candidate_hash = str(payload.get("candidate_hash") or "")
    if not candidate_hash:
        blockers.append("candidate_retirement_candidate_hash_missing")
    reason = str(payload.get("reason") or "").strip()
    if len(reason) < 12:
        blockers.append("candidate_retirement_reason_too_short")

    prior_registry = dict(payload.get("prior_registry") or {})
    prior_verification = verify_active_candidate_activation(prior_registry)
    if prior_verification.get("status") != "PASS":
        blockers.extend(
            f"prior_activation:{item}"
            for item in prior_verification.get("blockers") or ["activation_invalid"]
        )
    if str(prior_registry.get("candidate_hash") or "") != candidate_hash:
        blockers.append("candidate_retirement_prior_candidate_hash_mismatch")
    if str(payload.get("prior_registry_hash") or "") != str(prior_registry.get("registry_hash") or ""):
        blockers.append("candidate_retirement_prior_registry_hash_mismatch")
    if str(payload.get("prior_registry_content_hash") or "") != _canonical_hash(prior_registry):
        blockers.append("candidate_retirement_prior_registry_content_hash_mismatch")

    clock = dict(payload.get("retirement_clock_attestation") or {})
    clock_verification = verify_trusted_clock_attestation(clock)
    if clock_verification.get("status") != "PASS":
        blockers.extend(
            f"retirement_clock:{item}"
            for item in clock_verification.get("blockers") or ["attestation_blocked"]
        )
    retired_at = int(payload.get("retired_at") or 0)
    if retired_at <= 0:
        blockers.append("candidate_retirement_timestamp_invalid")
    if abs(retired_at - int(clock.get("attested_now_ms") or 0)) > 5_000:
        blockers.append("candidate_retirement_clock_mismatch")
    if str(payload.get("retirement_clock_attestation_hash") or "") != str(clock.get("attestation_hash") or ""):
        blockers.append("candidate_retirement_clock_hash_mismatch")

    invalidation_file = str(payload.get("invalidation_file") or "")
    if windows_safe_artifact_basename(invalidation_file) is None:
        blockers.append("candidate_retirement_invalidation_filename_invalid")
    if not str(payload.get("invalidation_file_sha256") or ""):
        blockers.append("candidate_retirement_invalidation_file_hash_missing")
    if not str(payload.get("invalidation_pack_hash") or ""):
        blockers.append("candidate_retirement_invalidation_pack_hash_missing")
    if (
        payload.get("research_only") is not True
        or payload.get("paper_authorized") is not False
        or payload.get("live_order_allowed") is not False
    ):
        blockers.append("candidate_retirement_contains_execution_authority")
    if authority_violations(payload):
        blockers.append("candidate_retirement_contains_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "candidate_hash": candidate_hash,
        "receipt_hash": expected_hash,
        "prior_activation_verification": prior_verification,
        "retirement_clock_verification": clock_verification,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def verify_retired_candidate_registry(
    registry: dict[str, Any],
    *,
    report_dir: Path | str,
) -> dict[str, Any]:
    pointer = dict(registry or {})
    directory = Path(report_dir).resolve()
    blockers: list[str] = []
    expected_hash = str(pointer.get("registry_hash") or "")
    hash_payload = dict(pointer)
    hash_payload.pop("registry_hash", None)
    if str(pointer.get("schema_version") or "") != RETIRED_CANDIDATE_REGISTRY_SCHEMA_VERSION:
        blockers.append("retired_candidate_registry_schema_invalid")
    if str(pointer.get("status") or "") != "NO_ACTIVE_RESEARCH_CANDIDATE":
        blockers.append("retired_candidate_registry_status_invalid")
    if not expected_hash or _canonical_hash(hash_payload) != expected_hash:
        blockers.append("retired_candidate_registry_hash_mismatch")
    candidate_hash = str(pointer.get("candidate_hash") or "")
    if not candidate_hash:
        blockers.append("retired_candidate_hash_missing")
    if (
        pointer.get("research_only") is not True
        or pointer.get("paper_authorized") is not False
        or pointer.get("live_order_allowed") is not False
    ):
        blockers.append("retired_candidate_registry_contains_execution_authority")
    if authority_violations(pointer):
        blockers.append("retired_candidate_registry_contains_execution_authority")

    receipt: dict[str, Any] = {}
    receipt_file = str(pointer.get("retirement_receipt_file") or "")
    receipt_path = directory / "missing"
    if windows_safe_artifact_basename(receipt_file) is None:
        blockers.append("retired_candidate_receipt_filename_invalid")
    else:
        receipt_path = directory / receipt_file
        if receipt_path.parent != directory:
            blockers.append("retired_candidate_receipt_path_escape")
        else:
            try:
                raw, receipt = _read_json_artifact(
                    receipt_path,
                    byte_limit=MAX_PORTFOLIO_FORWARD_CONTROL_ARTIFACT_BYTES,
                    size_limit_blocker="retired_candidate_receipt_size_limit_exceeded",
                )
                if hashlib.sha256(raw).hexdigest() != str(pointer.get("retirement_receipt_file_sha256") or ""):
                    blockers.append("retired_candidate_receipt_file_hash_mismatch")
            except ValueError as exc:
                blockers.append(f"retired_candidate_receipt_unavailable:{exc}")

    receipt_verification = verify_candidate_retirement_receipt(receipt)
    if receipt_verification.get("status") != "PASS":
        blockers.extend(
            f"retirement_receipt:{item}"
            for item in receipt_verification.get("blockers") or ["receipt_invalid"]
        )
    if str(receipt.get("candidate_hash") or "") != candidate_hash:
        blockers.append("retired_candidate_receipt_candidate_hash_mismatch")
    if str(receipt.get("receipt_hash") or "") != str(pointer.get("retirement_receipt_hash") or ""):
        blockers.append("retired_candidate_receipt_hash_mismatch")

    invalidation_file = str(receipt.get("invalidation_file") or "")
    if windows_safe_artifact_basename(invalidation_file) is not None:
        invalidation_path = directory / invalidation_file
        if invalidation_path.parent != directory:
            blockers.append("retired_candidate_invalidation_path_escape")
        else:
            try:
                raw, invalidation = _read_json_artifact(
                    invalidation_path,
                    byte_limit=_portfolio_artifact_byte_limits()["invalidation"],
                    size_limit_blocker="retired_candidate_invalidation_size_limit_exceeded",
                )
                if hashlib.sha256(raw).hexdigest() != str(receipt.get("invalidation_file_sha256") or ""):
                    blockers.append("retired_candidate_invalidation_file_hash_mismatch")
                if authority_violations(invalidation):
                    blockers.append("retired_candidate_invalidation_contains_execution_authority")
                if str(dict(invalidation.get("candidate") or {}).get("candidate_hash") or "") != candidate_hash:
                    blockers.append("retired_candidate_invalidation_candidate_hash_mismatch")
                if str(invalidation.get("status") or "") != "INTERNAL_BACKTEST_BLOCKED":
                    blockers.append("retired_candidate_invalidation_status_invalid")
                if str(invalidation.get("promotion_status") or "") != "BLOCK":
                    blockers.append("retired_candidate_invalidation_promotion_status_invalid")
                if str(invalidation.get("pack_hash") or "") != str(receipt.get("invalidation_pack_hash") or ""):
                    blockers.append("retired_candidate_invalidation_pack_hash_mismatch")
            except ValueError as exc:
                blockers.append(f"retired_candidate_invalidation_unavailable:{exc}")
    elif invalidation_file:
        blockers.append("retired_candidate_invalidation_filename_invalid")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "candidate_hash": candidate_hash,
        "registry_hash": expected_hash,
        "retirement_receipt": receipt,
        "retirement_receipt_path": str(receipt_path),
        "retirement_receipt_verification": receipt_verification,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def build_forward_capture_contract(
    *,
    calendar_name: str,
    signal_date: str,
    observed_at: int,
    clock_attestation: dict[str, Any] | None = None,
    activation_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    clean_date = str(signal_date or "").strip()[:10]
    blockers: list[str] = []
    try:
        session_day = date.fromisoformat(clean_date)
    except ValueError:
        session_day = date.min
        blockers.append("signal_date_invalid")
    try:
        observed = datetime.fromtimestamp(int(observed_at) / 1000.0, tz=timezone.utc)
    except (OSError, OverflowError, TypeError, ValueError):
        observed = datetime.fromtimestamp(0, tz=timezone.utc)
        blockers.append("observed_at_invalid")

    clock = dict(clock_attestation or {})
    clock_verification = verify_trusted_clock_attestation(clock) if clock else {
        "status": "UNATTESTED",
        "blockers": [],
    }
    clock_attested = bool(clock) and clock_verification.get("status") == "PASS"
    if clock and not clock_attested:
        blockers.extend(f"clock:{item}" for item in clock_verification.get("blockers") or ["attestation_blocked"])
    if clock_attested and abs(int(clock.get("attested_now_ms") or 0) - int(observed_at or 0)) > 5_000:
        blockers.append("clock_attestation_observed_at_mismatch")

    activation = verify_active_candidate_activation(dict(activation_registry or {}))
    if activation.get("status") != "PASS":
        blockers.extend(
            f"activation:{item}"
            for item in activation.get("blockers") or ["registry_blocked"]
        )

    calendar: dict[str, Any] = {}
    session: dict[str, Any] = {}
    next_session: dict[str, Any] = {}
    if not blockers:
        calendar = build_market_calendar_contract(
            calendar_name=str(calendar_name or "").upper(),
            start_date=clean_date,
            end_date=(session_day + timedelta(days=21)).isoformat(),
        )
        if calendar.get("status") != "PASS":
            blockers.extend(f"calendar:{item}" for item in calendar.get("blockers") or ["calendar_blocked"])
        schedule = list(calendar.get("schedule") or [])
        session = next((dict(item) for item in schedule if str(item.get("date") or "") == clean_date), {})
        next_session = next((dict(item) for item in schedule if str(item.get("date") or "") > clean_date), {})
        if not session:
            blockers.append("signal_date_is_not_an_official_session")
        if not next_session:
            blockers.append("next_official_session_unavailable")

    close_at = datetime.fromtimestamp(0, tz=timezone.utc)
    next_open_at = datetime.fromtimestamp(0, tz=timezone.utc)
    capture_not_before = datetime.fromtimestamp(0, tz=timezone.utc)
    capture_deadline = datetime.fromtimestamp(0, tz=timezone.utc)
    candidate_active_before_signal_close = False
    if not blockers:
        try:
            close_at = datetime.fromisoformat(str(session.get("close_utc") or "")).astimezone(timezone.utc)
            next_open_at = datetime.fromisoformat(str(next_session.get("open_utc") or "")).astimezone(timezone.utc)
            capture_not_before = close_at + timedelta(milliseconds=CAPTURE_FINALIZATION_DELAY_MS)
            capture_deadline = next_open_at - timedelta(milliseconds=CAPTURE_DEADLINE_SAFETY_MS)
        except ValueError:
            blockers.append("calendar_session_timestamp_invalid")
        if capture_deadline <= capture_not_before:
            blockers.append("capture_window_is_not_positive")

    activated_at = int(activation.get("activated_at") or 0)
    signal_close_ms = int(close_at.timestamp() * 1000) if close_at.timestamp() > 0 else 0
    if not blockers:
        candidate_active_before_signal_close = activated_at < signal_close_ms

    if blockers:
        status = "BLOCK"
    elif not candidate_active_before_signal_close:
        status = "PRE_ACTIVATION"
    elif observed < capture_not_before:
        status = "WAITING"
    elif observed >= capture_deadline:
        status = "MISSED"
    else:
        status = "PASS"
    payload = {
        "schema_version": PORTFOLIO_FORWARD_SCHEMA_VERSION,
        "status": status,
        "blockers": list(dict.fromkeys(blockers)),
        "calendar_name": str(calendar_name or "").upper(),
        "calendar_contract_hash": str(calendar.get("contract_hash") or ""),
        "calendar_schedule_hash": str(calendar.get("schedule_hash") or ""),
        "signal_date": clean_date,
        "session_close_utc": close_at.isoformat() if not blockers else "",
        "capture_not_before_utc": capture_not_before.isoformat() if not blockers else "",
        "next_session_date": str(next_session.get("date") or ""),
        "next_session_open_utc": next_open_at.isoformat() if not blockers else "",
        "capture_deadline_utc": capture_deadline.isoformat() if not blockers else "",
        "candidate_hash": str(activation.get("candidate_hash") or ""),
        "candidate_activated_at": activated_at,
        "candidate_activation_registry_hash": str(activation.get("registry_hash") or ""),
        "candidate_active_before_signal_close": candidate_active_before_signal_close,
        "activation_clock_attestation_hash": str(
            (activation.get("clock_attestation") or {}).get("attestation_hash") or ""
        ),
        "activation_clock_attestation": dict(activation.get("clock_attestation") or {}),
        "observed_at": int(observed_at or 0),
        "observed_at_utc": observed.isoformat(),
        "timely": status == "PASS",
        "natural_observation": status == "PASS",
        "backfill_allowed": False,
        "clock_source": str(clock.get("quality") or "LOCAL_SYSTEM_UTC_UNATTESTED"),
        "clock_attested": clock_attested,
        "clock_attestation_hash": str(clock.get("attestation_hash") or ""),
        "clock_attestation": clock,
        "observation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["capture_contract_hash"] = _canonical_hash(payload)
    return payload


def retire_active_portfolio_candidate(
    *,
    registry_path: Path | str,
    expected_candidate_hash: str,
    retired_at: int,
    retirement_clock_attestation: dict[str, Any],
    reason: str,
    invalidation_path: Path | str,
) -> dict[str, Any]:
    registry = Path(registry_path).absolute()
    directory = registry.parent
    artifact_limits = _portfolio_artifact_byte_limits()
    expected_hash = str(expected_candidate_hash or "").strip()
    clean_reason = str(reason or "").strip()
    blockers: list[str] = []
    pointer: dict[str, Any] = {}
    original_raw = b""
    try:
        original_raw, pointer = _read_json_artifact(
            registry,
            byte_limit=artifact_limits["registry"],
            size_limit_blocker="active_candidate_registry_size_limit_exceeded",
        )
    except ValueError as exc:
        blockers.append(f"active_candidate_registry_unavailable:{exc}")

    if str(pointer.get("status") or "") == "NO_ACTIVE_RESEARCH_CANDIDATE":
        verification = verify_retired_candidate_registry(pointer, report_dir=directory)
        if verification.get("status") != "PASS":
            blockers.extend(
                f"existing_retirement:{item}"
                for item in verification.get("blockers") or ["retirement_invalid"]
            )
        if str(pointer.get("candidate_hash") or "") != expected_hash:
            blockers.append("retired_candidate_expected_hash_mismatch")
        return {
            "ok": not blockers,
            "status": "ALREADY_RETIRED" if not blockers else "BLOCK",
            "blockers": list(dict.fromkeys(blockers)),
            "registry": pointer,
            "registry_path": str(registry),
            "retirement_verification": verification,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    activation_verification = verify_active_candidate_activation(pointer)
    if activation_verification.get("status") != "PASS":
        blockers.extend(
            f"active_candidate:{item}"
            for item in activation_verification.get("blockers") or ["activation_invalid"]
        )
    active_hash = str(pointer.get("candidate_hash") or "")
    if not expected_hash or active_hash != expected_hash:
        blockers.append("active_candidate_expected_hash_mismatch")
    if len(clean_reason) < 12:
        blockers.append("candidate_retirement_reason_too_short")

    clock = dict(retirement_clock_attestation or {})
    clock_verification = verify_trusted_clock_attestation(clock)
    if clock_verification.get("status") != "PASS":
        blockers.extend(
            f"retirement_clock:{item}"
            for item in clock_verification.get("blockers") or ["attestation_blocked"]
        )
    if abs(int(retired_at or 0) - int(clock.get("attested_now_ms") or 0)) > 5_000:
        blockers.append("candidate_retirement_clock_mismatch")

    invalidation = Path(invalidation_path).absolute()
    invalidation_payload: dict[str, Any] = {}
    invalidation_raw = b""
    if invalidation.parent != directory:
        blockers.append("candidate_retirement_invalidation_must_be_in_registry_directory")
    elif windows_safe_artifact_basename(invalidation.name) is None:
        blockers.append("candidate_retirement_invalidation_filename_invalid")
    else:
        try:
            invalidation_raw, invalidation_payload = _read_json_artifact(
                invalidation,
                byte_limit=artifact_limits["invalidation"],
                size_limit_blocker="candidate_retirement_invalidation_size_limit_exceeded",
            )
        except ValueError as exc:
            blockers.append(f"candidate_retirement_invalidation_unavailable:{exc}")
    if invalidation_payload:
        if authority_violations(invalidation_payload):
            blockers.append("candidate_retirement_invalidation_contains_execution_authority")
        if str(dict(invalidation_payload.get("candidate") or {}).get("candidate_hash") or "") != active_hash:
            blockers.append("candidate_retirement_invalidation_candidate_hash_mismatch")
        if str(invalidation_payload.get("status") or "") != "INTERNAL_BACKTEST_BLOCKED":
            blockers.append("candidate_retirement_invalidation_status_invalid")
        if str(invalidation_payload.get("promotion_status") or "") != "BLOCK":
            blockers.append("candidate_retirement_invalidation_promotion_status_invalid")
        if not str(invalidation_payload.get("pack_hash") or ""):
            blockers.append("candidate_retirement_invalidation_pack_hash_missing")
    if blockers:
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": list(dict.fromkeys(blockers)),
            "registry_path": str(registry),
            "activation_verification": activation_verification,
            "retirement_clock_verification": clock_verification,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    receipt = {
        "schema_version": CANDIDATE_RETIREMENT_RECEIPT_SCHEMA_VERSION,
        "status": "RETIRED_RESEARCH_CANDIDATE",
        "candidate_hash": active_hash,
        "prior_registry_hash": str(pointer.get("registry_hash") or ""),
        "prior_registry_content_hash": _canonical_hash(pointer),
        "prior_registry": pointer,
        "retired_at": int(retired_at),
        "retirement_clock_attestation_hash": str(clock.get("attestation_hash") or ""),
        "retirement_clock_attestation": clock,
        "reason": clean_reason,
        "invalidation_file": invalidation.name,
        "invalidation_file_sha256": hashlib.sha256(invalidation_raw).hexdigest(),
        "invalidation_pack_hash": str(invalidation_payload.get("pack_hash") or ""),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    receipt["receipt_hash"] = _canonical_hash(receipt)
    receipt_file = f"portfolio_candidate_retirement_{active_hash[:12]}_{int(retired_at)}.json"
    receipt_path = directory / receipt_file
    receipt_text = json.dumps(receipt, ensure_ascii=False, indent=2)
    # Text-mode writes may expand LF to CRLF on Windows.  Count that possible
    # byte per line so the persisted control receipt cannot cross its ceiling.
    receipt_size_upper_bound = (
        len(receipt_text.encode("utf-8"))
        + receipt_text.count("\n")
    )
    if receipt_size_upper_bound > MAX_PORTFOLIO_FORWARD_CONTROL_ARTIFACT_BYTES:
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": ["candidate_retirement_receipt_size_limit_exceeded"],
            "registry_path": str(registry),
            "activation_verification": activation_verification,
            "retirement_clock_verification": clock_verification,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    _atomic_write_json(receipt_path, receipt)
    try:
        receipt_raw, _ = _read_json_artifact(
            receipt_path,
            byte_limit=MAX_PORTFOLIO_FORWARD_CONTROL_ARTIFACT_BYTES,
            size_limit_blocker="candidate_retirement_receipt_size_limit_exceeded",
        )
    except ValueError as exc:
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": [f"candidate_retirement_receipt_unavailable:{exc}"],
            "registry_path": str(registry),
            "orphaned_receipt_path": str(receipt_path),
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    receipt_file_sha256 = hashlib.sha256(receipt_raw).hexdigest()

    try:
        current_raw, _ = _read_json_artifact(
            registry,
            byte_limit=artifact_limits["registry"],
            size_limit_blocker="active_candidate_registry_size_limit_exceeded",
        )
        registry_unchanged = current_raw == original_raw
    except ValueError:
        registry_unchanged = False
    if not registry_unchanged:
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": ["active_candidate_registry_changed_during_retirement"],
            "registry_path": str(registry),
            "orphaned_receipt_path": str(receipt_path),
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    retired_registry = {
        "schema_version": RETIRED_CANDIDATE_REGISTRY_SCHEMA_VERSION,
        "status": "NO_ACTIVE_RESEARCH_CANDIDATE",
        "candidate_hash": active_hash,
        "retired_at": int(retired_at),
        "retirement_receipt_file": receipt_file,
        "retirement_receipt_file_sha256": receipt_file_sha256,
        "retirement_receipt_hash": str(receipt.get("receipt_hash") or ""),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    retired_registry["registry_hash"] = _canonical_hash(retired_registry)
    _atomic_write_json(registry, retired_registry)
    retirement_verification = verify_retired_candidate_registry(retired_registry, report_dir=directory)
    return {
        "ok": retirement_verification.get("status") == "PASS",
        "status": "RETIRED" if retirement_verification.get("status") == "PASS" else "BLOCK",
        "blockers": list(retirement_verification.get("blockers") or []),
        "registry": retired_registry,
        "registry_path": str(registry),
        "retirement_receipt": receipt,
        "retirement_receipt_path": str(receipt_path),
        "retirement_verification": retirement_verification,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def activate_portfolio_candidate(
    *,
    candidate_path: Path | str,
    registry_path: Path | str,
    robustness_path: Path | str,
    activated_at: int,
    activation_clock_attestation: dict[str, Any] | None = None,
    experiment_completion_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    path = Path(candidate_path).absolute()
    registry = Path(registry_path).absolute()
    artifact_limits = _portfolio_artifact_byte_limits()
    blockers: list[str] = []
    candidate: dict[str, Any] = {}
    candidate_raw = b""
    robustness: dict[str, Any] = {}
    robustness_raw = b""
    robustness_file = Path(robustness_path).absolute()
    existing_registry_raw = b""
    existing_registry: dict[str, Any] = {}
    existing_registry_status = ""
    existing_registry_activation_verification: dict[str, Any] = {}
    registry_preexisting = registry.exists() or registry.is_symlink()
    if registry_preexisting:
        try:
            existing_registry_raw, existing_registry = _read_json_artifact(
                registry,
                byte_limit=artifact_limits["registry"],
                size_limit_blocker="active_candidate_registry_size_limit_exceeded",
            )
        except ValueError as exc:
            blockers.append(f"existing_active_candidate_registry_unavailable:{exc}")
        existing_registry_status = str(existing_registry.get("status") or "")
        if existing_registry_status == "ACTIVE_RESEARCH_CANDIDATE":
            existing_registry_activation_verification = verify_active_candidate_activation(
                existing_registry
            )
            if existing_registry_activation_verification.get("status") != "PASS":
                blockers.extend(
                    f"existing_active_candidate:{item}"
                    for item in existing_registry_activation_verification.get("blockers")
                    or ["activation_invalid"]
                )
        elif existing_registry_status == "NO_ACTIVE_RESEARCH_CANDIDATE":
            retirement_verification = verify_retired_candidate_registry(
                existing_registry,
                report_dir=registry.parent,
            )
            if retirement_verification.get("status") != "PASS":
                blockers.extend(
                    f"existing_retirement:{item}"
                    for item in retirement_verification.get("blockers")
                    or ["retirement_invalid"]
                )
        elif existing_registry:
            blockers.append("existing_active_candidate_registry_status_invalid")
    try:
        candidate_raw, candidate = _read_json_artifact(
            path,
            byte_limit=artifact_limits["candidate"],
            size_limit_blocker="candidate_size_limit_exceeded",
        )
    except ValueError as exc:
        blockers.append(f"candidate_unavailable:{exc}")
    verification = verify_frozen_portfolio_candidate(candidate) if candidate else {"status": "BLOCK", "blockers": ["candidate_unavailable"]}
    if verification.get("status") != "PASS":
        blockers.extend(f"candidate:{item}" for item in verification.get("blockers") or ["verification_failed"])
    if path.parent != registry.parent:
        blockers.append("candidate_must_be_in_registry_directory")
    if windows_safe_artifact_basename(path.name) is None:
        blockers.append("candidate_filename_invalid")
    if (
        candidate.get("research_only") is not True
        or candidate.get("paper_authorized") is not False
        or candidate.get("live_order_allowed") is not False
    ):
        blockers.append("candidate_has_execution_authority")
    if authority_violations(candidate):
        blockers.append("candidate_has_execution_authority")
    try:
        robustness_raw, robustness = _read_json_artifact(
            robustness_file,
            byte_limit=artifact_limits["robustness"],
            size_limit_blocker="robustness_report_size_limit_exceeded",
        )
    except ValueError as exc:
        blockers.append(f"robustness_report_unavailable:{exc}")
    robustness_verification = verify_robustness_report(
        robustness,
        candidate_hash=str(candidate.get("candidate_hash") or ""),
    ) if robustness else {"status": "BLOCK", "blockers": ["robustness_report_unavailable"]}
    if robustness_verification.get("status") != "PASS":
        blockers.extend(f"robustness:{item}" for item in robustness_verification.get("blockers") or ["verification_failed"])
    if robustness_file.parent != registry.parent:
        blockers.append("robustness_report_must_be_in_registry_directory")
    if windows_safe_artifact_basename(robustness_file.name) is None:
        blockers.append("robustness_report_filename_invalid")
    if authority_violations(robustness):
        blockers.append("robustness_report_has_execution_authority")
    if not isinstance(activation_clock_attestation, dict):
        blockers.append("activation_clock_attestation_object_required")
        activation_clock: dict[str, Any] = {}
    else:
        activation_clock = dict(activation_clock_attestation)
    activation_clock_verification = verify_trusted_clock_attestation(activation_clock)
    if activation_clock_verification.get("status") != "PASS":
        blockers.extend(
            f"activation_clock:{item}"
            for item in activation_clock_verification.get("blockers") or ["attestation_blocked"]
        )
    clean_activated_at = _nonnegative_integer(activated_at)
    if clean_activated_at is None or clean_activated_at <= 0:
        blockers.append("activation_timestamp_invalid")
    attested_now = _nonnegative_integer(activation_clock.get("attested_now_ms"))
    if attested_now is None or attested_now <= 0:
        blockers.append("activation_clock_attested_time_invalid")
    elif clean_activated_at is not None and clean_activated_at > 0 and abs(clean_activated_at - attested_now) > 5_000:
        blockers.append("activation_clock_timestamp_mismatch")
    if not isinstance(experiment_completion_receipt, dict):
        blockers.append("experiment_completion_receipt_object_required")
        experiment_completion: dict[str, Any] = {}
    else:
        experiment_completion = dict(experiment_completion_receipt)
    experiment_completion_verification = verify_completion_against_candidate(
        experiment_completion,
        candidate,
    )
    if experiment_completion_verification.get("status") != "PASS":
        blockers.extend(
            f"experiment_completion:{item}"
            for item in experiment_completion_verification.get("blockers") or ["receipt_blocked"]
        )
    experiment_artifact_verification = verify_experiment_completion_artifacts(
        experiment_completion,
        candidate_path=path,
        required_directory=registry.parent,
    )
    if experiment_artifact_verification.get("status") != "PASS":
        blockers.extend(
            f"experiment_artifact:{item}"
            for item in experiment_artifact_verification.get("blockers") or ["artifact_blocked"]
        )
    if existing_registry_status == "ACTIVE_RESEARCH_CANDIDATE" and not blockers:
        exact_replay = (
            str(existing_registry.get("candidate_hash") or "")
            == str(candidate.get("candidate_hash") or "")
            and str(existing_registry.get("candidate_file") or "") == path.name
            and str(existing_registry.get("candidate_file_sha256") or "")
            == hashlib.sha256(candidate_raw).hexdigest()
            and str(existing_registry.get("robustness_file") or "") == robustness_file.name
            and str(existing_registry.get("robustness_file_sha256") or "")
            == hashlib.sha256(robustness_raw).hexdigest()
            and str(existing_registry.get("robustness_hash") or "")
            == str(robustness.get("robustness_hash") or "")
            and str(existing_registry.get("experiment_completion_receipt_hash") or "")
            == str(experiment_completion.get("receipt_hash") or "")
        )
        if exact_replay:
            loaded_existing = load_active_portfolio_candidate(
                registry.parent,
                registry_path=registry,
            )
            if loaded_existing.get("status") == "PASS":
                return {
                    "ok": True,
                    "status": "ALREADY_ACTIVE",
                    "registry": existing_registry,
                    "registry_path": str(registry),
                    "candidate_verification": verification,
                    "robustness_verification": robustness_verification,
                    "activation_clock_verification": existing_registry_activation_verification.get(
                        "clock_verification",
                        {},
                    ),
                    "experiment_completion_verification": experiment_completion_verification,
                    "experiment_artifact_verification": experiment_artifact_verification,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            blockers.extend(
                f"existing_active_candidate_load:{item}"
                for item in loaded_existing.get("blockers") or ["load_invalid"]
            )
        else:
            blockers.append("active_candidate_replacement_requires_retirement")
    if blockers:
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": list(dict.fromkeys(blockers)),
            "candidate_verification": verification,
            "robustness_verification": robustness_verification,
            "activation_clock_verification": activation_clock_verification,
            "experiment_completion_verification": experiment_completion_verification,
            "experiment_artifact_verification": experiment_artifact_verification,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    payload = {
        "schema_version": ACTIVE_CANDIDATE_SCHEMA_VERSION,
        "status": "ACTIVE_RESEARCH_CANDIDATE",
        "candidate_file": path.name,
        "candidate_file_sha256": hashlib.sha256(candidate_raw).hexdigest(),
        "candidate_hash": str(candidate.get("candidate_hash") or ""),
        "dataset_binding_version": ACTIVE_CANDIDATE_DATASET_BINDING_VERSION,
        "replacement_gate_version": ACTIVE_CANDIDATE_REPLACEMENT_GATE_VERSION,
        "dataset_hash": str(candidate.get("dataset_hash") or ""),
        "dataset_last": str(candidate.get("dataset_last") or ""),
        "robustness_file": robustness_file.name,
        "robustness_file_sha256": hashlib.sha256(robustness_raw).hexdigest(),
        "robustness_hash": str(robustness.get("robustness_hash") or ""),
        "activated_at": int(clean_activated_at or 0),
        "activation_clock_attestation_hash": str(activation_clock.get("attestation_hash") or ""),
        "activation_clock_attestation": activation_clock,
        "experiment_completion_receipt_hash": str(experiment_completion.get("receipt_hash") or ""),
        "experiment_completion_receipt": experiment_completion,
        "selection_policy": "EXPLICIT_LOCAL_ACTIVATION_ONLY",
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["registry_hash"] = _canonical_hash(payload)
    if registry_preexisting:
        try:
            current_registry_raw, _ = _read_json_artifact(
                registry,
                byte_limit=artifact_limits["registry"],
                size_limit_blocker="active_candidate_registry_size_limit_exceeded",
            )
            registry_unchanged = current_registry_raw == existing_registry_raw
        except ValueError:
            registry_unchanged = False
    else:
        registry_unchanged = not registry.exists() and not registry.is_symlink()
    if not registry_unchanged:
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": ["active_candidate_registry_changed_during_activation"],
            "candidate_verification": verification,
            "robustness_verification": robustness_verification,
            "activation_clock_verification": activation_clock_verification,
            "experiment_completion_verification": experiment_completion_verification,
            "experiment_artifact_verification": experiment_artifact_verification,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    _atomic_write_json(registry, payload)
    return {
        "ok": True,
        "status": "ACTIVATED",
        "registry": payload,
        "registry_path": str(registry),
        "candidate_verification": verification,
        "robustness_verification": robustness_verification,
        "activation_clock_verification": activation_clock_verification,
        "experiment_completion_verification": experiment_completion_verification,
        "experiment_artifact_verification": experiment_artifact_verification,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def load_active_portfolio_candidate(
    report_dir: Path | str,
    *,
    registry_path: Path | str | None = None,
) -> dict[str, Any]:
    directory = Path(report_dir).resolve()
    registry = Path(registry_path).absolute() if registry_path else directory / DEFAULT_ACTIVE_CANDIDATE_FILE
    artifact_limits = _portfolio_artifact_byte_limits()
    blockers: list[str] = []
    pointer: dict[str, Any] = {}
    candidate: dict[str, Any] = {}
    robustness: dict[str, Any] = {}
    candidate_path = directory / "missing"
    try:
        _, pointer = _read_json_artifact(
            registry,
            byte_limit=artifact_limits["registry"],
            size_limit_blocker="active_candidate_registry_size_limit_exceeded",
        )
    except ValueError as exc:
        blockers.append(f"active_candidate_registry_unavailable:{exc}")
    if str(pointer.get("status") or "") == "NO_ACTIVE_RESEARCH_CANDIDATE":
        retirement_verification = verify_retired_candidate_registry(pointer, report_dir=directory)
        retirement_blockers = list(retirement_verification.get("blockers") or [])
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": [
                "active_candidate_retired",
                *(f"retirement:{item}" for item in retirement_blockers),
            ],
            "registry": pointer,
            "registry_path": str(registry),
            "candidate": {},
            "candidate_path": "",
            "candidate_verification": {"status": "BLOCK", "blockers": ["candidate_retired"]},
            "robustness": {},
            "robustness_verification": {"status": "BLOCK", "blockers": ["candidate_retired"]},
            "activation_verification": {"status": "BLOCK", "blockers": ["candidate_retired"]},
            "retirement_verification": retirement_verification,
            "experiment_completion_verification": {"status": "BLOCK", "blockers": ["candidate_retired"]},
            "experiment_artifact_verification": {"status": "BLOCK", "blockers": ["candidate_retired"]},
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    if pointer:
        activation_verification = verify_active_candidate_activation(pointer)
        if activation_verification.get("status") != "PASS":
            blockers.extend(activation_verification.get("blockers") or ["active_candidate_activation_invalid"])
        candidate_file = str(pointer.get("candidate_file") or "")
        if windows_safe_artifact_basename(candidate_file) is None:
            blockers.append("active_candidate_filename_invalid")
        else:
            candidate_path = directory / candidate_file
            if candidate_path.parent != directory:
                blockers.append("active_candidate_path_escape")
            else:
                try:
                    raw, candidate = _read_json_artifact(
                        candidate_path,
                        byte_limit=artifact_limits["candidate"],
                        size_limit_blocker="active_candidate_size_limit_exceeded",
                    )
                    if hashlib.sha256(raw).hexdigest() != str(pointer.get("candidate_file_sha256") or ""):
                        blockers.append("active_candidate_file_hash_mismatch")
                    if authority_violations(candidate):
                        blockers.append("active_candidate_contains_execution_authority")
                except ValueError as exc:
                    blockers.append(f"active_candidate_unavailable:{exc}")
        robustness_file = str(pointer.get("robustness_file") or "")
        if windows_safe_artifact_basename(robustness_file) is None:
            blockers.append("active_robustness_filename_invalid")
        else:
            robustness_path = directory / robustness_file
            if robustness_path.parent != directory:
                blockers.append("active_robustness_path_escape")
            else:
                try:
                    raw, robustness = _read_json_artifact(
                        robustness_path,
                        byte_limit=artifact_limits["robustness"],
                        size_limit_blocker="active_robustness_size_limit_exceeded",
                    )
                    if hashlib.sha256(raw).hexdigest() != str(pointer.get("robustness_file_sha256") or ""):
                        blockers.append("active_robustness_file_hash_mismatch")
                    if authority_violations(robustness):
                        blockers.append("active_robustness_contains_execution_authority")
                except ValueError as exc:
                    blockers.append(f"active_robustness_unavailable:{exc}")
    verification = verify_frozen_portfolio_candidate(candidate) if candidate else {"status": "BLOCK", "blockers": ["candidate_unavailable"]}
    if candidate and str(candidate.get("candidate_hash") or "") != str(pointer.get("candidate_hash") or ""):
        blockers.append("active_candidate_hash_mismatch")
    if candidate and str(candidate.get("dataset_hash") or "") != str(pointer.get("dataset_hash") or ""):
        blockers.append("active_candidate_dataset_hash_mismatch")
    if candidate and str(candidate.get("dataset_last") or "") != str(pointer.get("dataset_last") or ""):
        blockers.append("active_candidate_dataset_last_mismatch")
    if verification.get("status") != "PASS":
        blockers.extend(f"candidate:{item}" for item in verification.get("blockers") or ["verification_failed"])
    experiment_completion_verification = verify_completion_against_candidate(
        dict(pointer.get("experiment_completion_receipt") or {}),
        candidate,
    ) if candidate else {"status": "BLOCK", "blockers": ["candidate_unavailable"]}
    if experiment_completion_verification.get("status") != "PASS":
        blockers.extend(
            f"experiment_completion:{item}"
            for item in experiment_completion_verification.get("blockers") or ["receipt_blocked"]
        )
    experiment_artifact_verification = verify_experiment_completion_artifacts(
        dict(pointer.get("experiment_completion_receipt") or {}),
        candidate_path=candidate_path,
        required_directory=directory,
    ) if candidate else {"status": "BLOCK", "blockers": ["candidate_unavailable"]}
    if experiment_artifact_verification.get("status") != "PASS":
        blockers.extend(
            f"experiment_artifact:{item}"
            for item in experiment_artifact_verification.get("blockers") or ["artifact_blocked"]
        )
    robustness_verification = verify_robustness_report(
        robustness,
        candidate_hash=str(candidate.get("candidate_hash") or ""),
    ) if robustness else {"status": "BLOCK", "blockers": ["robustness_report_unavailable"]}
    if robustness_verification.get("status") != "PASS":
        blockers.extend(f"robustness:{item}" for item in robustness_verification.get("blockers") or ["verification_failed"])
    if robustness and str(robustness.get("robustness_hash") or "") != str(pointer.get("robustness_hash") or ""):
        blockers.append("active_robustness_hash_mismatch")
    return {
        "ok": not blockers,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "registry": pointer,
        "registry_path": str(registry),
        "candidate": candidate,
        "candidate_path": str(candidate_path),
        "candidate_verification": verification,
        "robustness": robustness,
        "robustness_verification": robustness_verification,
        "activation_verification": (
            verify_active_candidate_activation(pointer)
            if pointer else {"status": "BLOCK", "blockers": ["active_candidate_registry_unavailable"]}
        ),
        "experiment_completion_verification": experiment_completion_verification,
        "experiment_artifact_verification": experiment_artifact_verification,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def build_forward_readiness(
    *,
    candidate: dict[str, Any],
    candidate_verification: dict[str, Any],
    ledger_audit: dict[str, Any],
    frozen_dataset_hash_matches: bool,
    minimum_observations: int = 60,
    minimum_planned_rebalances: int = 8,
) -> dict[str, Any]:
    required_observations = max(int(minimum_observations), 1)
    required_rebalances = max(int(minimum_planned_rebalances), 1)
    metric_names = (
        "valid_observation_count",
        "externally_attested_observation_count",
        "planned_rebalance_count",
        "capture_violation_count",
        "timely_observation_count",
        "activation_verified_observation_count",
        "candidate_activation_violation_count",
        "clock_attestation_violation_count",
        "risk_pass_observation_count",
        "risk_block_reassessment_count",
        "execution_authority_violation_count",
    )
    metrics = {name: _nonnegative_integer(ledger_audit.get(name)) for name in metric_names}
    metrics_valid = all(value is not None for value in metrics.values())
    observation_count = metrics["valid_observation_count"] or 0
    attested_observation_count = metrics["externally_attested_observation_count"] or 0
    planned_rebalances = metrics["planned_rebalance_count"] or 0
    critical_checks = {
        "candidate_verification_pass": candidate_verification.get("status") == "PASS",
        "candidate_execution_authority_locked": candidate.get("research_only") is True
        and candidate.get("paper_authorized") is False
        and candidate.get("live_order_allowed") is False,
        "frozen_dataset_prefix_unchanged": frozen_dataset_hash_matches is True,
        "ledger_integrity_pass": ledger_audit.get("status") == "PASS",
        "ledger_metric_types_valid": metrics_valid,
        "zero_capture_contract_violations": metrics["capture_violation_count"] == 0,
        "all_observations_timely": metrics["timely_observation_count"] == observation_count,
        "all_observations_externally_attested": attested_observation_count == observation_count,
        "all_observations_precede_signal_with_active_candidate": metrics[
            "activation_verified_observation_count"
        ] == observation_count,
        "zero_candidate_activation_violations": metrics["candidate_activation_violation_count"] == 0,
        "zero_clock_attestation_violations": metrics["clock_attestation_violation_count"] == 0,
        "all_observation_risk_gates_pass": metrics["risk_pass_observation_count"] == observation_count,
        "zero_blocked_risk_reassessments": metrics["risk_block_reassessment_count"] == 0,
        "no_execution_authority": metrics["execution_authority_violation_count"] == 0,
    }
    progress_checks = {
        "minimum_natural_observations": observation_count >= required_observations,
        "minimum_externally_attested_observations": attested_observation_count >= required_observations,
        "minimum_planned_rebalances": planned_rebalances >= required_rebalances,
    }
    if not all(critical_checks.values()):
        status = "BLOCK"
    elif all(progress_checks.values()):
        status = "READY_FOR_FROZEN_EVALUATION"
    else:
        status = "COLLECTING"
    payload = {
        "schema_version": PORTFOLIO_FORWARD_SCHEMA_VERSION,
        "status": status,
        "candidate_hash": str(candidate.get("candidate_hash") or ""),
        "dataset_last": str(candidate.get("dataset_last") or ""),
        "critical_checks": critical_checks,
        "progress_checks": progress_checks,
        "progress": {
            "natural_observations": observation_count,
            "required_natural_observations": required_observations,
            "externally_attested_observations": attested_observation_count,
            "required_externally_attested_observations": required_observations,
            "planned_rebalances": planned_rebalances,
            "required_planned_rebalances": required_rebalances,
            "remaining_observations": max(required_observations - observation_count, 0),
            "remaining_externally_attested_observations": max(required_observations - attested_observation_count, 0),
            "remaining_planned_rebalances": max(required_rebalances - planned_rebalances, 0),
        },
        "ledger_audit": ledger_audit,
        "manual_frozen_evaluation_required": True,
        "automatic_paper_activation_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["readiness_hash"] = _canonical_hash(payload)
    return payload
