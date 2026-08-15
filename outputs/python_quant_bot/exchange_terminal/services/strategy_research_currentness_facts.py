from __future__ import annotations

from datetime import date, datetime, timezone
import re
from typing import Any


STRATEGY_RESEARCH_CURRENTNESS_FACTS_SCHEMA_VERSION = (
    "strategy-research-currentness-facts-v1"
)
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _native_nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _report_instant(value: Any) -> tuple[int | None, str]:
    if not isinstance(value, str) or not value.strip():
        return None, "NOT_AVAILABLE"
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        basis = "ISO8601_EXPLICIT_OFFSET"
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
            basis = "UTC_ASSUMED_FOR_NAIVE_ISO8601"
        instant = int(parsed.timestamp() * 1000)
    except (TypeError, ValueError, OverflowError):
        return None, "INVALID"
    return (instant, basis) if instant >= 0 else (None, "INVALID")


def _strict_date(value: Any) -> date | None:
    if not isinstance(value, str) or not _ISO_DATE.fullmatch(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def build_strategy_research_currentness_facts(
    *,
    report_created_at: Any,
    summary_common_as_of: Any,
    selection_common_as_of: Any,
    observed_at_ms: Any,
) -> dict[str, Any]:
    """Project timestamp facts without inventing a freshness or expiry policy."""

    blockers: list[str] = []
    evidence_gaps: list[str] = []
    report_created_at_text = report_created_at.strip() if isinstance(report_created_at, str) else ""
    report_created_at_ms, report_time_basis = _report_instant(report_created_at)
    if report_created_at_ms is None:
        blockers.append("research_report_created_at_invalid")

    observed = _native_nonnegative_int(observed_at_ms)
    if observed_at_ms is None:
        evidence_gaps.append("currentness_observation_time_not_supplied")
    elif observed is None:
        blockers.append("currentness_observation_time_invalid")

    summary_text = summary_common_as_of.strip() if isinstance(summary_common_as_of, str) else ""
    alignment_text = (
        selection_common_as_of.strip() if isinstance(selection_common_as_of, str) else ""
    )
    summary_date = _strict_date(summary_text) if summary_text else None
    alignment_date = _strict_date(alignment_text) if alignment_text else None
    if summary_text and summary_date is None:
        blockers.append("research_summary_common_as_of_invalid")
    if alignment_text and alignment_date is None:
        blockers.append("research_selection_common_as_of_invalid")
    if summary_date is not None and alignment_date is not None and summary_date != alignment_date:
        blockers.append("research_dataset_as_of_sources_mismatch")

    dataset_date: date | None = None
    dataset_as_of_source = "NOT_AVAILABLE"
    if summary_date is not None and alignment_date is not None and summary_date == alignment_date:
        dataset_date = summary_date
        dataset_as_of_source = "REPORT_SUMMARY_AND_SELECTION_ALIGNMENT"
    elif summary_date is not None and alignment_date is None and not alignment_text:
        dataset_date = summary_date
        dataset_as_of_source = "REPORT_SUMMARY"
    elif alignment_date is not None and summary_date is None and not summary_text:
        dataset_date = alignment_date
        dataset_as_of_source = "SELECTION_ALIGNMENT"
    elif not summary_text and not alignment_text:
        evidence_gaps.append("research_dataset_as_of_not_available")

    report_age_ms: int | None = None
    calendar_days_since_dataset_as_of: int | None = None
    if observed is not None and report_created_at_ms is not None:
        if report_created_at_ms > observed:
            blockers.append("research_report_created_after_observation")
        else:
            report_age_ms = observed - report_created_at_ms
    if observed is not None and dataset_date is not None:
        try:
            observed_date = datetime.fromtimestamp(observed / 1000, timezone.utc).date()
        except (OSError, OverflowError, ValueError):
            blockers.append("currentness_observation_time_out_of_range")
        else:
            if dataset_date > observed_date:
                blockers.append("research_dataset_as_of_after_observation")
            else:
                calendar_days_since_dataset_as_of = (observed_date - dataset_date).days

    blockers = list(dict.fromkeys(blockers))
    evidence_gaps = list(dict.fromkeys(evidence_gaps))
    if blockers:
        status = "BLOCK"
    elif evidence_gaps:
        status = "PARTIAL"
    else:
        status = "FACTS_AVAILABLE"

    return {
        "schema_version": STRATEGY_RESEARCH_CURRENTNESS_FACTS_SCHEMA_VERSION,
        "status": status,
        "basis": "VERIFIED_REPORT_TIMESTAMPS_WITH_CALLER_OBSERVATION",
        "observed_at_ms": observed,
        "report_created_at": report_created_at_text or None,
        "report_created_at_ms": report_created_at_ms,
        "report_time_basis": report_time_basis,
        "report_age_ms": report_age_ms,
        "dataset_as_of": dataset_date.isoformat() if dataset_date is not None else None,
        "dataset_as_of_source": dataset_as_of_source,
        "calendar_days_since_dataset_as_of": calendar_days_since_dataset_as_of,
        "dataset_age_basis": "UTC_CALENDAR_DAYS_NOT_TRADING_SESSIONS",
        "facts_complete": status == "FACTS_AVAILABLE",
        "report_age_threshold_ms": None,
        "dataset_age_threshold_calendar_days": None,
        "report_age_policy_status": "NOT_DEFINED",
        "dataset_freshness_policy_status": "NOT_DEFINED",
        "threshold_applied": False,
        "freshness_conclusion_allowed": False,
        "stale_claim_allowed": False,
        "dataset_currentness_checked": False,
        "report_age_policy_checked": False,
        "blockers": blockers,
        "evidence_gaps": evidence_gaps,
        "read_only": True,
        "research_only": True,
        "descriptive_only": True,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "STRATEGY_RESEARCH_CURRENTNESS_FACTS_SCHEMA_VERSION",
    "build_strategy_research_currentness_facts",
]
