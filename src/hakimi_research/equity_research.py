"""US regular-session research using the existing backtest ledger and risk core.

The initial slice admits only declared action-free common-stock windows. It is
not a broker adapter and does not authenticate imported market data.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from types import MappingProxyType

import pandas as pd

from hakimi_research.backtest import BacktestEngine
from hakimi_research.benchmarks import BUY_AND_HOLD_POLICY, STANDARD_RISK_POLICY
from hakimi_research.config import BotConfig, ExecutionConfig, RiskConfig, StrategyConfig
from hakimi_research.documents import canonical_bytes, digest, parse_document, read_document
from hakimi_research.environment import build_runtime_provenance
from hakimi_research.equity_dataset import EquitySnapshot, verify_equity_snapshot
from hakimi_research.experiment import ExperimentSpec, required_context
from hakimi_research.reporting import save_json_report
from hakimi_research.risk import RiskManager
from hakimi_research.strategies.templates import build_strategy

SPEC_SCHEMA = "us-equity-experiment-spec-v1"
REPORT_SCHEMA = "us-equity-research-report-v1"
PERMISSIONS = {"research_only": True, "paper_allowed": False, "live_allowed": False, "order_allowed": False}
_FIELDS = {"schema_version", "name", "snapshot_id", "score_start_session", "score_end_session",
           "strategy", "initial_cash", "fee_rate", "slippage_pct", "risk", "end_policy", "purpose",
           "quantity_policy", "execution_policy"}


@dataclass(frozen=True)
class EquityExperimentSpec:
    document: dict

    @classmethod
    def from_document(cls, document):
        value = parse_document(canonical_bytes(document))
        if set(value) != _FIELDS or value["schema_version"] != SPEC_SCHEMA:
            raise ValueError("equity_spec_fields_or_schema_invalid")
        for key in ("score_start_session", "score_end_session"):
            if type(value[key]) is not str or pd.Timestamp(value[key]).strftime("%Y-%m-%d") != value[key]:
                raise ValueError("equity_score_session_date_required")
        if value["score_start_session"] > value["score_end_session"]:
            raise ValueError("equity_score_session_range_invalid")
        if value["quantity_policy"] != "FRACTIONAL_SHARES_RESEARCH_APPROXIMATION":
            raise ValueError("equity_quantity_model_not_supported")
        if value["purpose"] not in {"SYNTHETIC_REGRESSION", "DESCRIPTIVE_DEVELOPMENT"}:
            raise ValueError("equity_purpose_must_not_claim_confirmation")
        if type(value["strategy"]) is not dict or value["strategy"].get("name") not in {"cash", "buy_and_hold", "dual_ma"}:
            raise ValueError("equity_first_slice_strategy_not_supported")
        # Reuse the canonical fixed-rule/risk/cost validation. These temporary
        # UTC bounds validate no stock chronology and never enter the report.
        common = {key: value[key] for key in ("name", "snapshot_id", "strategy", "initial_cash",
                  "fee_rate", "slippage_pct", "risk", "end_policy", "purpose", "execution_policy")}
        common.update(schema_version="research-experiment-spec-v1", score_start="2000-01-01T00:00:00Z",
                      score_end="2000-01-02T00:00:00Z")
        if common["purpose"] == "DESCRIPTIVE_DEVELOPMENT":
            common["purpose"] = "DESCRIPTIVE_FIXED_PARAMETERS"
        ExperimentSpec.from_document(common)
        return cls(value)

    @classmethod
    def load(cls, path):
        return cls.from_document(read_document(path))


class _SessionEngine(BacktestEngine):
    """Change the clock only; fill, fee, protection and portfolio logic is shared."""
    def __init__(self, *args, sessions, lag, **kwargs):
        clocks = {pd.Timestamp(row["open_utc"]): pd.Timestamp(row["close_utc"]) for row in sessions}
        available = {opened: closed + pd.Timedelta(seconds=lag) for opened, closed in clocks.items()}
        opens = list(clocks)
        if any(available[previous] >= following for previous, following in zip(opens, opens[1:])):
            raise ValueError("equity_bar_unavailable_before_next_open")
        self._equity_closes = MappingProxyType(clocks)
        self._equity_available = MappingProxyType(available)
        self._equity_clock_hash = digest({"sessions": sessions, "bar_availability_lag_seconds": lag})
        super().__init__(*args, **kwargs)

    def _close_time(self, value):
        return str(self._equity_closes[value])

    def _signal_time(self, value):
        return str(self._equity_available[value])

    def _reproducibility(self, data, **kwargs):
        result = super()._reproducibility(data, **kwargs)
        clock = {"market_clock_model": "US_REGULAR_SESSION_CLOSE_WITH_DECLARED_AVAILABILITY_LAG_V1",
                 "session_clock_hash": self._equity_clock_hash}
        return {**result, **clock, "run_hash": digest({"base_run_hash": result["run_hash"], **clock})}


def _range(snapshot, spec):
    sessions = snapshot["sessions"]
    dates = [row["date"] for row in sessions]
    try:
        first = dates.index(spec["score_start_session"])
        last = dates.index(spec["score_end_session"]) + 1
    except ValueError as exc:
        raise ValueError("equity_score_session_not_in_snapshot") from exc
    context = required_context(spec["strategy"]["name"], spec["strategy"]["params"])
    if first < context or last <= first:
        raise ValueError("equity_insufficient_context_sessions")
    return first, last, context


def _protocol(snapshot, spec):
    first, last, context = _range(snapshot, spec)
    return {"score_start": snapshot["sessions"][first]["open_utc"],
            "score_end": snapshot["sessions"][last - 1]["close_utc"],
            "available_context_sessions": first, "required_context_sessions": context,
            "scored_sessions": last - first, "warmup_trading": False,
            "annualization": "252_REGULAR_SESSIONS_PER_YEAR_DESCRIPTIVE_ASSUMPTION",
            "bar_availability_lag_seconds": snapshot["bar_availability_lag_seconds"],
            "session_clock_hash": digest({"sessions": snapshot["sessions"],
                                          "bar_availability_lag_seconds": snapshot["bar_availability_lag_seconds"]}),
            "company_actions": "DECLARED_ACTION_FREE_WINDOW_ONLY",
            "parameter_selection": False, "confirmation_evaluation": False}


def _projection(data):
    return {key: data[key] for key in ("snapshot_id", "data_hash", "security", "sessions",
            "price_basis", "volume_unit", "evidence_kind", "research_admission", "bar_availability_lag_seconds")}


@dataclass(frozen=True)
class EquityResearchReport:
    document: dict

    def save(self, directory):
        checked = verify_equity_report(self.document)
        return Path(save_json_report(checked, directory, "equity_research", artifact_id=checked["report_hash"]))


class EquityExperimentRunner:
    def run(self, snapshot: EquitySnapshot, spec: EquityExperimentSpec):
        data = verify_equity_snapshot(snapshot.document)
        value = EquityExperimentSpec.from_document(spec.document).document
        if value["snapshot_id"] != data["snapshot_id"]:
            raise ValueError("equity_spec_snapshot_mismatch")
        if not data["research_admission"]["allowed"]:
            raise ValueError("equity_economic_research_blocked:" + ",".join(data["research_admission"]["block_reasons"]))
        if data["research_admission"]["synthetic_only"] and value["purpose"] != "SYNTHETIC_REGRESSION":
            raise ValueError("synthetic_equity_cannot_be_market_evidence")
        first, last, _ = _range(data, value)
        strategy = value["strategy"]
        config = BotConfig(market="stock", symbol=data["security"]["symbol"], timeframe="1d",
                           initial_cash=value["initial_cash"], strategy=StrategyConfig(**strategy),
                           risk=RiskConfig(**value["risk"]),
                           execution=ExecutionConfig(fee_rate=value["fee_rate"], slippage_pct=value["slippage_pct"]))
        engine = _SessionEngine(config, build_strategy(strategy["name"], strategy["params"]), RiskManager(config.risk),
                                sessions=data["sessions"], lag=data["bar_availability_lag_seconds"],
                                benchmark_policy=value["execution_policy"])
        computed = engine.run(EquitySnapshot(data).frame(), score_start=first, score_end=last).to_dict()
        computed.pop("experiment_manifest", None)
        provenance = build_runtime_provenance()
        projected = _projection(data)
        result_hash = digest({"snapshot_id": data["snapshot_id"], "spec": value, "result": computed})
        core = {"schema_version": REPORT_SCHEMA, "spec": value, "spec_hash": digest(value), "dataset": projected,
                "scoring_protocol": _protocol(data, value), "result": computed, "result_hash": result_hash,
                "provenance": provenance, "execution_permission": dict(PERMISSIONS),
                "limitations": ["Imported source/calendar/action declarations are not independently authenticated.",
                    "Only stable-identity, declared action-free windows are admitted. Corporate actions require further accounting implementation.",
                    "Fractional shares, proportional fees and constant slippage are research approximations, not broker rules or fills.",
                    "No spread, auction participation, liquidity or intraday execution guarantee is established.",
                    "This is a fixed development or synthetic regression, not a profitability or out-of-sample claim."]}
        return EquityResearchReport({**core, "report_hash": digest(core)})


def verify_equity_report(document):
    value = parse_document(canonical_bytes(document))
    fields = {"schema_version", "spec", "spec_hash", "dataset", "scoring_protocol", "result", "result_hash",
              "provenance", "execution_permission", "limitations", "report_hash"}
    if set(value) != fields or value["schema_version"] != REPORT_SCHEMA:
        raise ValueError("equity_report_schema_invalid")
    if value["report_hash"] != digest({k: v for k, v in value.items() if k != "report_hash"}):
        raise ValueError("equity_report_hash_mismatch")
    spec = EquityExperimentSpec.from_document(value["spec"]).document
    dataset = value["dataset"]
    if (value["spec_hash"] != digest(spec) or dataset["snapshot_id"] != spec["snapshot_id"]
            or canonical_bytes(value["execution_permission"]) != canonical_bytes(PERMISSIONS)
            or dataset["research_admission"]["allowed"] is not True
            or (dataset["research_admission"]["synthetic_only"] and spec["purpose"] != "SYNTHETIC_REGRESSION")):
        raise ValueError("equity_report_identity_or_permission_mismatch")
    if canonical_bytes(value["scoring_protocol"]) != canonical_bytes(_protocol(dataset, spec)):
        raise ValueError("equity_report_session_protocol_mismatch")
    result = value["result"]
    if value["result_hash"] != digest({"snapshot_id": dataset["snapshot_id"], "spec": spec, "result": result}):
        raise ValueError("equity_report_result_hash_mismatch")
    first, last, _ = _range(dataset, spec)
    marks = result["equity_curve"]
    if len(marks) != last - first + 1 or pd.Timestamp(marks[0]["time"]) != pd.Timestamp(dataset["sessions"][first]["open_utc"]):
        raise ValueError("equity_report_initial_or_mark_count_mismatch")
    for mark, session in zip(marks[1:], dataset["sessions"][first:last]):
        if pd.Timestamp(mark["time"]) != pd.Timestamp(session["close_utc"]):
            raise ValueError("equity_report_mark_not_regular_close")
    lag = pd.Timedelta(seconds=dataset["bar_availability_lag_seconds"])
    expected_signals = [pd.Timestamp(row["close_utc"]) + lag for row in dataset["sessions"][first - 1:last - 1]]
    if [pd.Timestamp(row["time"]) for row in result["signals"]] != expected_signals:
        raise ValueError("equity_report_signal_availability_mismatch")
    opens = {pd.Timestamp(row["open_utc"]) for row in dataset["sessions"][first:last]}
    prior_availability = dict(zip((pd.Timestamp(row["open_utc"]) for row in dataset["sessions"][first:last]), expected_signals))
    for fill in result["fills"]:
        at = pd.Timestamp(fill["fill_time"])
        if (fill["fill_basis"] not in {"NEXT_BAR_OPEN", "GAP_OPEN", "OPEN_TARGET", "INTRABAR_STOP", "INTRABAR_TARGET"}
                or at not in opens or fill["symbol"] != dataset["security"]["symbol"]
                or (fill["fill_basis"] == "NEXT_BAR_OPEN" and (
                    pd.Timestamp(fill["signal_time"]) != prior_availability[at] or prior_availability[at] >= at))):
            raise ValueError("equity_fill_before_signal_or_outside_session")
    return value


def replay_equity_report(snapshot, report):
    original = verify_equity_report(report.document)
    if canonical_bytes(original["dataset"]) != canonical_bytes(_projection(verify_equity_snapshot(snapshot.document))):
        raise ValueError("equity_replay_dataset_projection_mismatch")
    replayed = EquityExperimentRunner().run(snapshot, EquityExperimentSpec.from_document(original["spec"])).document
    before, after = original["provenance"], replayed["provenance"]
    result_matches = original["result_hash"] == replayed["result_hash"]
    source_hash = before["source_identity"].get("content_sha256")
    source_matches = (type(source_hash) is str and re.fullmatch(r"[0-9a-f]{64}", source_hash) is not None
                      and before["source_identity"].get("status") in {"CONTENT_HASHED", "BUILD_VERIFIED"}
                      and after["source_identity"].get("status") in {"CONTENT_HASHED", "BUILD_VERIFIED"}
                      and source_hash == after["source_identity"].get("content_sha256"))
    environment_matches = (before["environment_verified"]["status"] == after["environment_verified"]["status"] == "VERIFIED"
                           and before["environment_verified"]["lock_sha256"] == after["environment_verified"]["lock_sha256"]
                           and before["environment_verified"]["packages"] == after["environment_verified"]["packages"])
    core = {"schema_version": "us-equity-replay-receipt-v1", "original_report_hash": original["report_hash"],
            "snapshot_id": snapshot.snapshot_id, "original_result_hash": original["result_hash"],
            "replayed_result_hash": replayed["result_hash"], "result_matches": result_matches,
            "source_matches": source_matches, "environment_verified": environment_matches,
            "replay_verified": result_matches and source_matches and environment_matches,
            "execution_permission": dict(PERMISSIONS), "replay_provenance": after}
    return {**core, "receipt_hash": digest(core)}
