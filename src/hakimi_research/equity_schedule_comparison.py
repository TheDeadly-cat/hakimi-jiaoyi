"""Fixed A/B schedule comparison with shared inputs and all outcomes retained."""
from __future__ import annotations

from .documents import canonical_bytes, digest
from .equity_event_context import DISABLED, RULE_VERSION, verify_event_context, schedule_view
from .equity_events import _timestamp
from .equity_research import EquityExperimentRunner, EquityExperimentSpec, verify_equity_report, SPEC_SCHEMA, EVENT_SPEC_SCHEMA, PERMISSIONS


def _metrics(report):
    result = report["result"]
    blocked = sum(any(review.get("disposition") == "BLOCK_NEW_BUY" for review in row.get("event_filter", {}).values())
                  for row in result["signals"])
    return {key: result[key] for key in ("total_return", "max_drawdown", "total_fees", "fill_count", "round_trip_count", "exposure_ratio")} | {
        "buy_fill_count": sum(fill["action"] == "BUY" for fill in result["fills"]),
        "turnover_over_initial_cash": sum(abs(fill["quantity"] * fill["price"]) for fill in result["fills"]) / report["spec"]["initial_cash"],
        "scheduled_price_decisions": len(result["signals"]), "blocked_new_buy_intents": blocked,
        "outcome": "NO_TRADE" if not result["fills"] else "LOSS" if result["total_return"] < 0 else "NONNEGATIVE_DESCRIPTIVE_RESULT"}


def build_schedule_comparison(a, b):
    a, b = verify_equity_report(a), verify_equity_report(b)
    if (a["spec"]["schema_version"] != EVENT_SPEC_SCHEMA or b["spec"]["schema_version"] != EVENT_SPEC_SCHEMA
            or a["spec"]["event_rule"] != DISABLED or b["spec"]["event_rule"] != RULE_VERSION):
        raise ValueError("equity_comparison_requires_disabled_A_and_schedule_B")
    common = {key: value for key, value in a["spec"].items() if key != "event_rule"}
    if (canonical_bytes(common) != canonical_bytes({key: value for key, value in b["spec"].items() if key != "event_rule"})
            or canonical_bytes(a["dataset"]) != canonical_bytes(b["dataset"])
            or canonical_bytes(a["event_context"]) != canonical_bytes(b["event_context"])):
        raise ValueError("equity_comparison_requires_identical_inputs_and_common_parameters")
    events = a["event_context"]["events"]
    cutoff = _timestamp(a["scoring_protocol"]["score_end"], "score_end")
    in_window = {event["event_id"] for event in events if event["availability"]["pit_admissible"]
                 and _timestamp(event["availability"]["available_at"], "available_at") <= cutoff
                 and schedule_view(event)["status"] == "ANNOUNCED"
                 and common["score_start_session"] <= schedule_view(event)["date"] <= common["score_end_session"]}
    a_metrics, b_metrics = _metrics(a), _metrics(b)
    core = {"schema_version": "equity-schedule-comparison-v1", "scope": "DESCRIPTIVE_ENGINEERING_AB_NOT_STRATEGY_CONFIRMATION",
            "snapshot_id": common["snapshot_id"], "event_context_hash": common["event_context_hash"], "common_parameters": common,
            "sample_units": {"company_count": 1, "announced_event_count_in_scoring_window": len(in_window),
                "archived_event_identities": sorted({event["event_id"] for event in events}),
                "scored_sessions_are_not_independent_event_samples": True},
            "A": {"report_hash": a["report_hash"], "result_hash": a["result_hash"], "rule": DISABLED, "metrics": a_metrics},
            "B": {"report_hash": b["report_hash"], "result_hash": b["result_hash"], "rule": RULE_VERSION, "metrics": b_metrics},
            "B_minus_A": {key: b_metrics[key] - a_metrics[key] for key in ("total_return", "max_drawdown", "total_fees", "buy_fill_count", "turnover_over_initial_cash", "exposure_ratio")},
            "retention": "KEEP_BOTH_REPORTS_ALL_DECISIONS_BLOCKS_NEGATIVE_AND_NO_TRADE_OUTCOMES",
            "limitations": ["One company's correlated dates and revisions are not independent market samples.",
                "Fewer entries and lower exposure may forgo gains; count and return differences do not identify causal lost profit.",
                "C/D content conditions are not run; no numeric field or missing consensus creates a directional entry."],
            "execution_permission": dict(PERMISSIONS)}
    return {**core, "comparison_hash": digest(core)}


def verify_schedule_comparison(document, a, b):
    expected = build_schedule_comparison(a, b)
    if canonical_bytes(document) != canonical_bytes(expected):
        raise ValueError("equity_schedule_comparison_binding_invalid")
    return expected


def run_schedule_comparison(snapshot, base_spec, context):
    original = EquityExperimentSpec.from_document(base_spec.document).document
    if original["schema_version"] != SPEC_SCHEMA:
        raise ValueError("equity_comparison_requires_price_only_base_spec")
    archive = verify_event_context(context)
    reports = []
    for rule in (DISABLED, RULE_VERSION):
        spec = EquityExperimentSpec.from_document({**original, "schema_version": EVENT_SPEC_SCHEMA,
            "event_context_hash": archive["context_hash"], "event_rule": rule})
        reports.append(EquityExperimentRunner().run(snapshot, spec, event_context=archive))
    a, b = reports
    return a, b, build_schedule_comparison(a.document, b.document)
