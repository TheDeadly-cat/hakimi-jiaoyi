"""Versioned schedule inputs for price-entry risk filtering, never order authority."""
from __future__ import annotations

from datetime import date
from zoneinfo import ZoneInfo

from .documents import canonical_bytes, digest, parse_document
from .equity_events import _lineage, _timestamp, _iso
from .models import Action, Signal

SCHEMA_VERSION = "equity-event-context-v1"
DISABLED = "DISABLED"
RULE_VERSION = "DROP_NEW_BUY_ON_ANNOUNCED_EARNINGS_DATE_V1"


def schedule_view(event):
    if "schedule" in event:
        return {key: event["schedule"][key] for key in ("status", "date", "time_precision", "timezone")}
    return {"status": "ANNOUNCED", "date": _timestamp(event["scheduled_release_at"], "scheduled_release_at").astimezone(
        ZoneInfo("America/New_York")).date().isoformat(), "time_precision": "EXACT_TIME", "timezone": "America/New_York"}


def build_event_context(events, security_id):
    if type(security_id) is not str or not security_id.strip() or security_id != security_id.strip():
        raise ValueError("event_context_security_id_required")
    grouped = _lineage(events)
    ordered = [event for _, versions in sorted(grouped.items()) for event in versions]
    if not ordered or any(event["security_id"] != security_id or event["event_kind"] != "EARNINGS_SCHEDULE" for event in ordered):
        raise ValueError("event_context_requires_schedule_versions_for_one_security")
    core = {"schema_version": SCHEMA_VERSION, "security_id": security_id, "events": ordered,
            "scope": "ANNOUNCED_SCHEDULE_RISK_FILTER_NOT_RELEASE_CONTENT", "order_allowed": False}
    return {**core, "context_hash": digest(core)}


def verify_event_context(document):
    value = parse_document(canonical_bytes(document))
    if type(value) is not dict or set(value) != {"schema_version", "security_id", "events", "scope", "order_allowed", "context_hash"}:
        raise ValueError("event_context_shape_invalid")
    expected = build_event_context(value["events"], value["security_id"])
    if canonical_bytes(expected) != canonical_bytes(value):
        raise ValueError("event_context_binding_invalid")
    return expected


class EventSchedulePolicy:
    def __init__(self, context, *, rule, security_id, purpose):
        self.context = verify_event_context(context)
        if self.context["security_id"] != security_id or rule not in {DISABLED, RULE_VERSION}:
            raise ValueError("event_context_security_or_rule_mismatch")
        if purpose != "SYNTHETIC_REGRESSION" and any(event["source"]["kind"] == "SYNTHETIC_FIXTURE" for event in self.context["events"]):
            raise ValueError("synthetic_event_cannot_be_real_research_evidence")
        self.rule = rule
        # Detached verified versions; a caller cannot mutate the input later.
        self.versions = _lineage(self.context["events"])

    def require_historical_schedule(self, through):
        if self.rule == DISABLED:
            return
        cutoff = _timestamp(through, "research_end")
        if not any(event["availability"]["pit_admissible"] and schedule_view(event)["status"] == "ANNOUNCED"
                   and _timestamp(event["availability"]["available_at"], "available_at") <= cutoff
                   for versions in self.versions.values() for event in versions):
            raise ValueError("event_schedule_filter_NOT_RUN_no_historical_usable_schedule")

    def known_at(self, as_of):
        cutoff = _timestamp(as_of, "decision_as_of")
        selected = []
        for _, versions in sorted(self.versions.items()):
            eligible = [event for event in versions if event["availability"]["pit_admissible"]
                        and _timestamp(event["availability"]["available_at"], "available_at") <= cutoff]
            if eligible:
                event = eligible[-1]
                selected.append({"event_id": event["event_id"], "version": event["version"], "event_hash": event["event_hash"],
                    "source_content_sha256": event["raw"]["content_sha256"], "version_public_at": event["version_public_at"],
                    "available_at": event["availability"]["available_at"], "available_at_kind": event["availability"]["available_at_kind"],
                    "schedule": schedule_view(event), "field_status": [{"name": fact["name"], "status": fact["status"]} for fact in event["facts"]]})
        return selected

    def review(self, signal, *, as_of, execution_time, execution_session, stage):
        if self.rule == DISABLED:
            return signal, {}
        if stage not in {"DECISION", "EXECUTION"}:
            raise ValueError("event_policy_stage_invalid")
        current, executed = _timestamp(as_of, "as_of"), _timestamp(execution_time, "execution_time")
        if (stage == "DECISION" and current >= executed or stage == "EXECUTION" and current != executed
                or executed.astimezone(ZoneInfo("America/New_York")).date() != date.fromisoformat(execution_session)):
            raise ValueError("event_policy_clock_or_session_invalid")
        known = self.known_at(_iso(current))
        blocking = [row["event_hash"] for row in known if row["schedule"]["status"] == "UNKNOWN"
                    or row["schedule"]["status"] == "ANNOUNCED" and row["schedule"]["date"] == execution_session]
        blocked = signal.action is Action.BUY and bool(blocking)
        disposition = "BLOCK_NEW_BUY" if blocked else "NO_PENDING_BUY" if signal.action is not Action.BUY else "ALLOW_PRICE_BUY"
        output = Signal.hold("announced earnings schedule blocks this new buy") if blocked else signal
        audit = {"rule_version": self.rule, "stage": stage, "as_of": _iso(current),
                 "execution_session": execution_session, "execution_time": _iso(executed),
                 "input_action": signal.action.value, "output_action": output.action.value,
                 "input_signal": {"confidence": signal.confidence, "size_pct": signal.size_pct, "reason": signal.reason,
                     "stop_loss_pct": signal.stop_loss_pct, "take_profit_pct": signal.take_profit_pct, "metadata": signal.metadata},
                 "disposition": disposition, "known_versions": known,
                 "blocking_event_hashes": blocking if blocked else []}
        return output, audit
