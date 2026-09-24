"""Fixed offline C/D research using the canonical event ledger and session engine.

This repository tool adds a signal adapter, not a second accounting simulator.
The installed research package is unchanged. Its provenance and these adapter
bytes are both bound to each new report; old reports are never re-signed.
"""
from __future__ import annotations

from datetime import timedelta
import hashlib
from pathlib import Path

import pandas as pd

from hakimi_research.config import BotConfig, ExecutionConfig, RiskConfig, StrategyConfig
from hakimi_research.documents import canonical_bytes, digest
from hakimi_research.equity_dataset import EquitySnapshot, verify_equity_snapshot
from hakimi_research.equity_events import build_equity_event, event_snapshot_eligibility, select_event_versions
from hakimi_research.equity_research import EquityExperimentSpec, PERMISSIONS, _SessionEngine, _projection
from hakimi_research.models import Signal
from hakimi_research.environment import build_runtime_provenance
from hakimi_research.risk import RiskManager
from hakimi_research.strategies.base import StrategyBase
from tools.equity_content_protocol import content_condition, price_confirmation, utc, validate_approval

REPORT_SCHEMA = "us-equity-content-research-report-v1"
FROZEN_PROTOCOL_HASH = "096fcedff143df62e19e1b4fd05966068e891349c0131657d314942c5f975dfc"
FIXED_RISK = {"max_position_pct": 0.25, "max_single_loss_pct": 0.03,
              "max_daily_loss_pct": 1.0, "max_leverage": 1.0, "min_cash_pct": 0.0}


def tool_identity():
    root = Path(__file__).parent
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in ("equity_content_study.py", "equity_content_protocol.py", "verify_announcement_review.py",
                         "prepare_announcement_review.py")}


def event_context(packet, approval, texts, *, event_id):
    """Import only the two used facts into the existing versioned event contract.

    Other reviewed fields stay in the unchanged candidate packet. In particular,
    no signed EPS token is manufactured to satisfy the canonical token validator.
    Guidance basis maps explicitly to NOT_APPLICABLE; its name and next fiscal
    period distinguish an outlook from realized GAAP revenue.
    """
    approved = validate_approval(packet, approval)
    candidates = sorted((row for row in packet["events"] if row["event_id"] == event_id), key=lambda r: r["version"])
    if not candidates:
        raise ValueError("content_event_missing")
    events, bindings = [], {}
    previous_candidate = None
    for candidate in candidates:
        if candidate["candidate_hash"] != digest({k: v for k, v in candidate.items() if k != "candidate_hash"}):
            raise ValueError("content_candidate_identity_changed")
        if candidate["prior_version_hash"] != previous_candidate:
            raise ValueError("content_candidate_lineage_mismatch")
        text = texts[candidate["plain_text_sha256"]]
        if hashlib.sha256(text.encode()).hexdigest() != candidate["plain_text_sha256"]:
            raise ValueError("content_normalized_source_changed")
        used = []
        for name in ("actual_revenue", "next_revenue_guidance_midpoint"):
            matches = [f for f in candidate["facts"] if f["name"] == name]
            if len(matches) != 1:
                raise ValueError("content_unique_required_fact_missing")
            fact = matches[0]
            evidence = fact["evidence"]
            eligible = (candidate["candidate_hash"] in approved and fact["status"] in {"KNOWN", "UNCERTAIN"}
                        and fact.get("reason") in {None, "PENDING_HUMAN_SEMANTIC_REVIEW"})
            status = "KNOWN" if eligible else "UNCERTAIN"
            if fact["status"] == "MISSING":
                used.append({"name": name, "status": "MISSING", **{k: None for k in
                    ("value", "value_text", "scale", "currency", "unit", "fiscal_period", "basis")},
                    "evidence": [], "reason": fact["reason"]})
                continue
            used.append({"name": name, "status": status, "value": fact["value"], "value_text": fact["value"],
                "scale": fact["scale"], "currency": fact["currency"], "unit": fact["unit"],
                "fiscal_period": fact["fiscal_period"], "basis": "GAAP" if name == "actual_revenue" else "NOT_APPLICABLE",
                "evidence": [{"start": evidence["plain_text_start"], "end": evidence["plain_text_end"], "quote": evidence["quote"]}],
                "reason": None if eligible else "NOT_APPROVED_OR_UNCERTAIN"})
        metadata = {"event_id": event_id, "security_id": candidate["security_id"], "event_kind": "EARNINGS",
            "version": candidate["version"], "prior_version_hash": events[-1]["event_hash"] if events else None,
            "source": {"url": candidate["source_url"], "kind": "COMPANY_IR", "document_type": "EARNINGS_RELEASE_NORMALIZED_TEXT",
                       "disclosure_items": [], "official_source_status": "DECLARED_UNVERIFIED"},
            "first_public_at": candidate["first_public_at"],
            "version_public_at": candidate.get("version_public_at", candidate["first_public_at"]),
            "publication_clock": {"status": "ATTESTED", "verification_method": "RETAINED_CURRENT_HTML_AND_SCOPED_HUMAN_FIELD_REVIEW",
                                  "evidence": "candidate_sha256=" + candidate["candidate_hash"]},
            "retrieved_at": candidate["retrieved_at"],
            "timing": {"mode": "HISTORICAL_RECONSTRUCTION", "received_at": None,
                       "extraction_completed_at": candidate["extraction_completed_at"],
                       "collection_delay_seconds": 60, "processing_delay_seconds": 60},
            "scheduled_release_at": None, "facts": used,
            "uncertainties": ["Current HTML is not authenticated immutable historical content.",
                "60+60 seconds is an explicit decomposition of the frozen 120-second model, not measured latency.",
                "Only two rule inputs are projected; full reviewed fields stay in the original packet.",
                "Original HTML sha256=" + candidate["raw_sha256"],
                "Human approval receipt sha256=" + digest(approval) if approval else "No human approval."]}
        event = build_equity_event(text.encode(), metadata)
        events.append(event)
        bindings[event["event_hash"]] = candidate
        previous_candidate = candidate["candidate_hash"]
    # Enforce the existing complete-lineage/conflict contract before any decision.
    select_event_versions(events, "9999-01-01T00:00:00Z")
    return {"events": events, "candidates": bindings, "approved_hashes": approved}


def decisions(snapshot, context, *, enabled):
    """Compute each historical decision with only completed, available closes."""
    data = verify_equity_snapshot(snapshot)
    first_event = context["events"][0]
    timing = event_snapshot_eligibility(first_event, data)
    if timing["status"] != "READY":
        raise ValueError("content_calendar_not_ready:" + timing["reason"])
    sessions = data["sessions"]
    rows = []
    bars = []
    for candle, session in zip(data["candles"], sessions):
        decision_at = (utc(session["close_utc"]) + timedelta(seconds=data["bar_availability_lag_seconds"])).isoformat().replace("+00:00", "Z")
        bars.append({"session": session["date"], "close": str(candle[4]), "available_at": decision_at, "completed": True})
        c = price_confirmation(release_at=first_event["first_public_at"], decision_at=decision_at, sessions=sessions, bars=bars)
        selected = select_event_versions(context["events"], decision_at)
        versions = [context["candidates"][e["event_hash"]] for e in selected]
        result = content_condition(c, versions=versions, decision_at=decision_at,
                                   approved_hashes=context["approved_hashes"], enabled=enabled)
        rows.append({"decision_at": decision_at, **result})
    if sum(row["action"] == "BUY" for row in rows) > 1:
        raise ValueError("content_more_than_one_entry_intent")
    return rows


class ContentSignalAdapter(StrategyBase):
    """An explicit fixed signal plan; execution/risk/accounting stay canonical."""
    def __init__(self, params):
        super().__init__(params, name="equity_post_release_confirmation", version="v1")

    def generate_signal(self, data, portfolio):
        # Only an exact confirmation-bar identity can produce a BUY. No retry
        # after a rejected intent or a protective exit is possible at later bars.
        if str(data.index[-1]) == self.get("confirmation_bar_open", None):
            return Signal.buy("FIRST_POST_RELEASE_CLOSE_ABOVE_PRE_RELEASE_CLOSE", 0.25,
                              stop_loss_pct=0.03, take_profit_pct=0.06)
        return Signal.hold("NO_AVAILABLE_PRICE_CONFIRMATION")


def run_cell(snapshot, reference_spec, packet, approval, texts, *, event_id, variant, protocol_hash=FROZEN_PROTOCOL_HASH):
    if variant not in {"C", "D", "D_DISABLED"} or protocol_hash != FROZEN_PROTOCOL_HASH:
        raise ValueError("content_frozen_variant_or_protocol_required")
    data = verify_equity_snapshot(snapshot.document)
    base = EquityExperimentSpec.from_document(reference_spec).document
    if (base["snapshot_id"] != data["snapshot_id"] or not data["research_admission"]["allowed"]
            or data["bar_availability_lag_seconds"] != 60 or base["risk"] != FIXED_RISK
            or base["initial_cash"] != 10000 or base["end_policy"] != "MARK_TO_MARKET"
            or base["execution_policy"] != "STANDARD_STRATEGY_RISK"
            or (base["fee_rate"], base["slippage_pct"]) not in {(0.0008, 0.0005), (0.0016, 0.0010)}):
        raise ValueError("content_fixed_input_risk_or_cost_mismatch")
    if data["research_admission"]["synthetic_only"] and base["purpose"] != "SYNTHETIC_REGRESSION":
        raise ValueError("content_synthetic_not_market_evidence")
    context = event_context(packet, approval, texts, event_id=event_id)
    if any(e["security_id"] != data["security"]["security_id"] for e in context["events"]):
        raise ValueError("content_security_identity_mismatch")
    plan = decisions(data, context, enabled=variant == "D")
    dates = [s["date"] for s in data["sessions"]]
    start, end = dates.index(base["score_start_session"]), dates.index(base["score_end_session"]) + 1
    if start < 1 or start >= end:
        raise ValueError("content_scoring_context_invalid")
    opens = {s["open_utc"] for s in data["sessions"][start:end]}
    entry = next((r for r in plan if r["action"] == "BUY" and r["execution_at"] in opens), None)
    confirmation_open = None
    if entry is not None:
        index = next(i for i, r in enumerate(plan) if r["decision_at"] == entry["decision_at"])
        confirmation_open = str(pd.Timestamp(data["sessions"][index]["open_utc"]))
    params = {"confirmation_bar_open": confirmation_open, "decision_plan_hash": digest(plan),
              "protocol_hash": protocol_hash, "position_pct": 0.25, "stop_loss_pct": 0.03, "take_profit_pct": 0.06}
    strategy = ContentSignalAdapter(params)
    config = BotConfig(market="stock", symbol=data["security"]["symbol"], timeframe="1d", initial_cash=10000,
        strategy=StrategyConfig(name=strategy.name, params=params), risk=RiskConfig(**base["risk"]),
        execution=ExecutionConfig(fee_rate=base["fee_rate"], slippage_pct=base["slippage_pct"]))
    result = _SessionEngine(config, strategy, RiskManager(config.risk), sessions=data["sessions"], lag=60,
        benchmark_policy="STANDARD_STRATEGY_RISK").run(EquitySnapshot(data).frame(), score_start=start, score_end=end).to_dict()
    result.pop("experiment_manifest", None)
    buys = [f for f in result["fills"] if f["action"] == "BUY"]
    if len(buys) > 1 or any(entry is None or pd.Timestamp(f["fill_time"]) != pd.Timestamp(entry["execution_at"]) for f in buys):
        raise ValueError("content_entry_execution_mismatch")
    spec = {k: base[k] for k in ("snapshot_id", "score_start_session", "score_end_session", "initial_cash", "fee_rate",
        "slippage_pct", "risk", "end_policy", "purpose", "quantity_policy", "execution_policy")}
    spec.update(schema_version="us-equity-content-experiment-spec-v1", strategy={"name": strategy.name, "params": params},
                variant=variant, event_id=event_id, protocol_hash=protocol_hash, reference_spec_hash=digest(base))
    core = {"schema_version": REPORT_SCHEMA, "spec": spec, "spec_hash": digest(spec), "dataset": _projection(data),
        "decision_plan": plan, "effective_entry": entry, "result": result, "result_hash": digest(result),
        "event_hashes": [e["event_hash"] for e in context["events"]], "packet_hash": packet["packet_hash"],
        "approval_hash": digest(approval), "provenance": build_runtime_provenance(), "tool_identity": tool_identity(),
        "execution_permission": dict(PERMISSIONS),
        "limitations": ["Already-seen AMD development windows; no unseen confirmation or profitability inference.",
            "Current retained HTML and human semantic attestation do not establish immutable historical publication.",
            "120-second event and 60-second completed-bar availability are assumptions, not live measurements.",
            "Fractional shares, proportional fees, fixed slippage, daily OHLC protective exits and mark-to-market are research approximations.",
            "Prior guidance revisions and analyst consensus remain unavailable to this rule."]}
    return {**core, "report_hash": digest(core)}


def replay_cell(report, snapshot, reference_spec, packet, approval, texts):
    if report["report_hash"] != digest({k: v for k, v in report.items() if k != "report_hash"}):
        raise ValueError("content_report_hash_mismatch")
    replay = run_cell(snapshot, reference_spec, packet, approval, texts, event_id=report["spec"]["event_id"],
                      variant=report["spec"]["variant"], protocol_hash=report["spec"]["protocol_hash"])
    # Complete deterministic report comparison, excluding only measured runtime
    # provenance which is independently checked below.
    same = canonical_bytes({k: v for k, v in report.items() if k not in {"provenance", "report_hash"}}) == canonical_bytes(
        {k: v for k, v in replay.items() if k not in {"provenance", "report_hash"}})
    before, after = report["provenance"], replay["provenance"]
    source = (before["source_identity"]["content_sha256"] == after["source_identity"]["content_sha256"]
              and before["source_identity"]["status"] in {"CONTENT_HASHED", "BUILD_VERIFIED"}
              and after["source_identity"]["status"] in {"CONTENT_HASHED", "BUILD_VERIFIED"})
    environment = (before["environment_verified"] == after["environment_verified"]
                   and after["environment_verified"]["status"] == "VERIFIED")
    return {"schema_version": "equity-content-replay-v1", "report_hash": report["report_hash"],
            "result_and_inputs_match": same, "source_matches": source, "environment_verified": environment,
            "replay_verified": same and source and environment, "order_allowed": False}
