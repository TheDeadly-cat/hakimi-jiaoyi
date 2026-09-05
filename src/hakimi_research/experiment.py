"""One formal offline research runner shared by CLI and report consumers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from hakimi_research.backtest import BacktestEngine
from hakimi_research.benchmarks import BUY_AND_HOLD_POLICY, STANDARD_RISK_POLICY
from hakimi_research.config import BotConfig, ExecutionConfig, RiskConfig, StrategyConfig
from hakimi_research.dataset_registry import DatasetSnapshot, load_snapshot, utc_time, verify_snapshot
from hakimi_research.documents import canonical_bytes, digest, parse_document, read_document
from hakimi_research.environment import build_runtime_provenance
from hakimi_research.reporting import save_json_report
from hakimi_research.risk import RiskManager
from hakimi_research.strategies.templates import build_strategy

SPEC_SCHEMA = "research-experiment-spec-v1"
REPORT_SCHEMA = "research-report-v2"
_SPEC_FIELDS = {"schema_version", "name", "snapshot_id", "strategy", "score_start", "score_end",
                "initial_cash", "fee_rate", "slippage_pct", "risk", "end_policy", "purpose"}
_PARAMS = {
    "cash": set(), "buy_and_hold": {"target_position_pct"},
    "dual_ma": {"fast_window", "slow_window"}, "grid": {"lookback", "grids"},
    "bollinger": {"window", "std_mult"}, "macd": {"fast", "slow", "signal"},
    "rsi": {"window", "oversold", "overbought"}, "momentum": {"window", "threshold"},
}
_COMMON_PARAMS = {"position_pct", "stop_loss_pct"}
_PARAMS["dual_ma"].add("take_profit_pct")


def required_context(name: str, params: dict) -> int:
    if name in {"cash", "buy_and_hold"}:
        return 1
    def integer(key, default):
        value = params.get(key, default)
        if type(value) is not int or not 1 <= value <= 10000:
            raise ValueError("strategy_window_exact_positive_int_required:" + key)
        return value
    if name == "dual_ma":
        fast, slow = integer("fast_window", 20), integer("slow_window", 60)
        if fast >= slow:
            raise ValueError("fast_window_must_be_smaller_than_slow_window")
        return slow + 2
    if name == "macd":
        fast, slow, signal = integer("fast", 12), integer("slow", 26), integer("signal", 9)
        if fast >= slow:
            raise ValueError("macd_fast_must_be_smaller_than_slow")
        return max(40, slow + signal + 2)
    if name == "grid":
        integer("grids", 8)
        return integer("lookback", 80) + 2
    if name in {"bollinger", "rsi", "momentum"}:
        return integer("window", 14 if name == "rsi" else 20) + (3 if name in {"rsi", "momentum"} else 2)
    raise ValueError("unsupported_strategy")


@dataclass(frozen=True)
class StrategySpec:
    name: str
    params: dict

    def declaration(self) -> dict:
        return {
            "name": self.name, "parameters": self.params,
            "required_context_rows": required_context(self.name, self.params),
            "direction": "CASH_ONLY" if self.name == "cash" else "LONG_CASH",
            "required_fields": ["open", "high", "low", "close", "volume"],
            "state_initialization": "FRESH_STRATEGY_AND_FLAT_PORTFOLIO_AT_SCORE_START",
            "adding_to_position": self.name in {"grid", "bollinger", "macd", "rsi", "momentum"},
            "first_score_initialization": (
                "HOLD_CASH" if self.name == "cash" else
                "SINGLE_ENTRY_ATTEMPT_AT_FIRST_SCORED_OPEN" if self.name == "buy_and_hold" else
                "EVALUATE_LAST_CONTEXT_CLOSE_THEN_EXECUTE_SIGNAL_AT_FIRST_SCORED_OPEN"),
            "initial_condition_policy": "EXISTING_RULES_UNCHANGED_NO_FORCED_CROSSOVER_OR_EXTRA_TRADES",
        }


@dataclass(frozen=True)
class ExperimentSpec:
    document: dict

    @classmethod
    def from_document(cls, document: dict):
        # Detached finite JSON prevents caller mutation and implicit coercion.
        value = parse_document(canonical_bytes(document))
        if (set(value) - {"execution_policy"}) != _SPEC_FIELDS or value["schema_version"] != SPEC_SCHEMA:
            raise ValueError("experiment_spec_fields_or_schema_invalid")
        if type(value["name"]) is not str or not value["name"].strip():
            raise ValueError("experiment_name_required")
        if type(value["snapshot_id"]) is not str or not re.fullmatch("[0-9a-f]{64}", value["snapshot_id"]):
            raise ValueError("exact_snapshot_id_required")
        if value["end_policy"] != "MARK_TO_MARKET":
            raise ValueError("only_explicit_mark_to_market_end_policy_supported")
        if value["purpose"] not in {"DESCRIPTIVE_FIXED_PARAMETERS", "SYNTHETIC_REGRESSION"}:
            raise ValueError("formal_confirmation_or_parameter_selection_not_supported_by_this_runner")
        if utc_time(value["score_start"]) >= utc_time(value["score_end"]):
            raise ValueError("experiment_score_range_invalid")
        strategy = value["strategy"]
        if type(strategy) is not dict or set(strategy) != {"name", "params"}:
            raise ValueError("strategy_spec_invalid")
        name, params = strategy["name"], strategy["params"]
        if type(name) is not str or name not in _PARAMS or type(params) is not dict:
            raise ValueError("strategy_spec_invalid")
        common = set() if name in {"cash", "buy_and_hold"} else _COMMON_PARAMS
        if set(params) - _PARAMS[name] - common:
            raise ValueError("unknown_strategy_parameter")
        if any(type(number) not in (int, float) for number in params.values()):
            raise ValueError("strategy_parameters_exact_numbers_required")
        required_context(name, params)
        expected_policy = BUY_AND_HOLD_POLICY if name == "buy_and_hold" else STANDARD_RISK_POLICY
        if value.get("execution_policy", STANDARD_RISK_POLICY) != expected_policy:
            raise ValueError("strategy_execution_policy_must_be_explicit_and_consistent")
        build_strategy(name, params)
        risk = RiskConfig(**value["risk"])
        if risk.max_leverage != 1:
            raise ValueError("spot_mvp_requires_leverage_one")
        if name == "buy_and_hold" and (risk.max_position_pct != 1 or risk.min_cash_pct != 0):
            raise ValueError("buy_and_hold_requires_declared_full_spot_cash_policy")
        config = BotConfig(market="crypto_spot", initial_cash=value["initial_cash"], risk=risk,
                           strategy=StrategyConfig(name=name, params=params),
                           execution=ExecutionConfig(fee_rate=value["fee_rate"], slippage_pct=value["slippage_pct"]))
        # BotConfig enforces exact types and permanent execution locks.
        del config
        return cls(value)

    @classmethod
    def load(cls, path: str | Path):
        return cls.from_document(read_document(path))


@dataclass(frozen=True)
class ResearchReport:
    document: dict

    def save(self, directory: str | Path) -> Path:
        document = parse_document(canonical_bytes(self.document))
        verify_report(document)
        return Path(save_json_report(document, directory, "research", artifact_id=document["report_hash"]))


class ExperimentRunner:
    def run(self, snapshot: DatasetSnapshot, spec: ExperimentSpec) -> ResearchReport:
        spec = ExperimentSpec.from_document(spec.document)
        snapshot_document = verify_snapshot(snapshot.document)
        value = spec.document
        if value["snapshot_id"] != snapshot_document["snapshot_id"]:
            raise ValueError("experiment_snapshot_identity_mismatch")
        if value["purpose"] == "DESCRIPTIVE_FIXED_PARAMETERS" and snapshot_document["evidence_kind"] == "SYNTHETIC_TEST":
            raise ValueError("synthetic_snapshot_requires_regression_purpose")
        frame = snapshot.frame()
        start, end = utc_time(value["score_start"]), utc_time(value["score_end"])
        if start not in frame.index or end > utc_time(snapshot_document["end_exclusive"]):
            raise ValueError("score_outside_snapshot")
        first = int(frame.index.searchsorted(start))
        last = int(frame.index.searchsorted(end))
        strategy_spec = value["strategy"]
        warmup = required_context(strategy_spec["name"], strategy_spec["params"])
        if first < warmup:
            raise ValueError(f"insufficient_warmup:required={warmup}:available={first}")
        config = BotConfig(market="crypto_spot", initial_cash=value["initial_cash"],
                           strategy=StrategyConfig(**strategy_spec), risk=RiskConfig(**value["risk"]),
                           execution=ExecutionConfig(fee_rate=value["fee_rate"], slippage_pct=value["slippage_pct"]))
        engine = BacktestEngine(config, build_strategy(strategy_spec["name"], strategy_spec["params"]),
                                RiskManager(config.risk), benchmark_policy=value.get("execution_policy", STANDARD_RISK_POLICY))
        computed = engine.run(frame, score_start=first, score_end=last).to_dict()
        # The old manifest is an integration protocol, not verified runtime
        # evidence. Formal reports use the independent measured evidence below.
        computed.pop("experiment_manifest", None)
        provenance = build_runtime_provenance()
        result_identity = {"data_hash": snapshot_document["data_hash"], "spec": value, "result": computed}
        core = {
            "schema_version": REPORT_SCHEMA, "spec": value, "spec_hash": digest(value),
            "strategy_spec": StrategySpec(strategy_spec["name"], strategy_spec["params"]).declaration(),
            "dataset": {key: snapshot_document[key] for key in (
                "snapshot_id", "data_hash", "dataset_id", "start", "end_exclusive", "as_of",
                "volume_unit", "quote_unit", "quality", "evidence_kind", "source_authentication")},
            "scoring_protocol": {"start_inclusive": value["score_start"], "end_exclusive": value["score_end"],
                                 "required_context_rows": warmup, "available_context_rows": first,
                                 "warmup_trading": False, "parameter_selection": False,
                                 "confirmation_evaluation": False, "end_policy": value["end_policy"]},
            "result": computed, "result_hash": digest(result_identity),
            "computation_id": digest(result_identity),
            "run_id": digest({"computation_id": digest(result_identity), "provenance": provenance}),
            "evidence": {"input_integrity": "VERIFIED_AGAINST_STORED_RAW_BYTES",
                         "data_scope": {"market": "crypto_spot", "symbol": "BTC-USDT", "timeframe": "1h",
                                        "evidence_kind": snapshot_document["evidence_kind"], "scope": "ONE_FIXED_HISTORICAL_SNAPSHOT"},
                         "environment_verified": provenance["environment_verified"],
                         "source_identity": provenance["source_identity"],
                         "replay_verified": {"status": "NOT_RUN"},
                         "statistical_status": computed["statistical_status"]},
            "provenance": provenance,
            "execution_permission": {"research_only": True, "paper_allowed": False,
                                     "live_allowed": False, "order_allowed": False},
            "limitations": ["Fixed parameters; descriptive history, not independent confirmation or parameter selection.",
                            "Next-open OHLC approximation; no order book, spread dynamics, or guaranteed liquidity.",
                            "Fees and slippage are declared assumptions; closing positions are marked, not fabricated fills.",
                            "Source bytes and hashes do not establish provider truth or a profitable strategy.",
                            "No observed fills cannot establish stop, partial-fill, or cost-sensitivity behavior; software tests are separate evidence.",
                            "Cash benchmark: no fills, no fees, zero return for the identical score interval."],
        }
        return ResearchReport({**core, "report_hash": digest(core)})


def verify_report(document: dict) -> dict:
    if type(document) is not dict or document.get("schema_version") not in {REPORT_SCHEMA, "research-report-v1"}:
        raise ValueError("research_report_schema_invalid")
    fields = {"schema_version", "spec", "spec_hash", "dataset", "scoring_protocol", "result", "result_hash",
              "evidence", "provenance", "execution_permission", "limitations", "report_hash"}
    current = document["schema_version"] == REPORT_SCHEMA
    if current:
        fields |= {"strategy_spec", "computation_id", "run_id"}
    if set(document) != fields:
        raise ValueError("research_report_fields_invalid")
    core = {key: value for key, value in document.items() if key != "report_hash"}
    if document.get("report_hash") != digest(core):
        raise ValueError("research_report_hash_mismatch")
    ExperimentSpec.from_document(document["spec"])
    if document["spec_hash"] != digest(document["spec"]):
        raise ValueError("research_report_spec_mismatch")
    expected_permissions = {"research_only": True, "paper_allowed": False, "live_allowed": False, "order_allowed": False}
    if canonical_bytes(document["execution_permission"]) != canonical_bytes(expected_permissions):
        raise ValueError("research_report_execution_authority_rejected")
    if document["dataset"]["snapshot_id"] != document["spec"]["snapshot_id"]:
        raise ValueError("research_report_dataset_mismatch")
    expected_result = digest({"data_hash": document["dataset"]["data_hash"], "spec": document["spec"],
                              "result": document["result"]})
    if document["result_hash"] != expected_result:
        raise ValueError("research_report_result_mismatch")
    spec = document["spec"]
    protocol = document["scoring_protocol"]
    context = required_context(spec["strategy"]["name"], spec["strategy"]["params"])
    available = int((utc_time(spec["score_start"]) - utc_time(document["dataset"]["start"])).total_seconds() / 3600)
    expected_protocol = {"start_inclusive": spec["score_start"], "end_exclusive": spec["score_end"],
                         "required_context_rows": context, "available_context_rows": available,
                         "warmup_trading": False, "parameter_selection": False,
                         "confirmation_evaluation": False, "end_policy": "MARK_TO_MARKET"}
    if available < context or canonical_bytes(protocol) != canonical_bytes(expected_protocol):
        raise ValueError("research_report_scoring_claim_invalid")
    evidence, provenance = document["evidence"], document["provenance"]
    evidence_fields = {"input_integrity", "environment_verified", "source_identity", "replay_verified", "statistical_status"}
    if current:
        evidence_fields.add("data_scope")
    if type(evidence) is not dict or set(evidence) != evidence_fields or type(provenance) is not dict:
        raise ValueError("research_report_evidence_fields_invalid")
    if evidence["input_integrity"] != "VERIFIED_AGAINST_STORED_RAW_BYTES" or evidence["replay_verified"] != {"status": "NOT_RUN"}:
        raise ValueError("research_report_invalid_integrity_or_replay_claim")
    for key in ("source_identity", "environment_verified"):
        if type(evidence[key]) is not dict or "status" not in evidence[key] or canonical_bytes(evidence[key]) != canonical_bytes(provenance.get(key)):
            raise ValueError("research_report_runtime_evidence_mismatch")
    if canonical_bytes(evidence["statistical_status"]) != canonical_bytes(document["result"].get("statistical_status")):
        raise ValueError("research_report_statistical_claim_mismatch")
    if type(document["limitations"]) is not list or not document["limitations"] or any(type(item) is not str for item in document["limitations"]):
        raise ValueError("research_report_limitations_required")
    if current:
        declaration = StrategySpec(spec["strategy"]["name"], spec["strategy"]["params"]).declaration()
        if canonical_bytes(document["strategy_spec"]) != canonical_bytes(declaration):
            raise ValueError("research_report_strategy_declaration_mismatch")
        if document["computation_id"] != expected_result or document["run_id"] != digest({"computation_id": expected_result, "provenance": provenance}):
            raise ValueError("research_report_computation_or_run_identity_mismatch")
        data_scope = {"market": "crypto_spot", "symbol": "BTC-USDT", "timeframe": "1h",
                      "evidence_kind": document["dataset"]["evidence_kind"], "scope": "ONE_FIXED_HISTORICAL_SNAPSHOT"}
        if canonical_bytes(evidence["data_scope"]) != canonical_bytes(data_scope):
            raise ValueError("research_report_data_scope_mismatch")
    return document


def replay_report(snapshot: DatasetSnapshot, report: ResearchReport) -> dict:
    original = verify_report(report.document)
    replayed = ExperimentRunner().run(snapshot, ExperimentSpec.from_document(original["spec"])).document
    result_matches = original["result_hash"] == replayed["result_hash"]
    original_source = original["evidence"]["source_identity"]
    current_source = replayed["evidence"]["source_identity"]
    source_hash = original_source.get("content_sha256", "")
    source_matches = (type(source_hash) is str and re.fullmatch("[0-9a-f]{64}", source_hash) is not None
                      and original_source.get("status") in {"CONTENT_HASHED", "BUILD_VERIFIED"}
                      and current_source.get("status") in {"CONTENT_HASHED", "BUILD_VERIFIED"}
                      and source_hash == current_source.get("content_sha256"))
    original_env = original["evidence"]["environment_verified"]
    current_env = replayed["evidence"]["environment_verified"]
    environment_matches = (original_env.get("status") == current_env.get("status") == "VERIFIED"
                           and original_env.get("lock_sha256") == current_env.get("lock_sha256")
                           and original_env.get("packages") == current_env.get("packages"))
    verified = result_matches and source_matches and environment_matches
    core = {"schema_version": "research-replay-receipt-v1", "original_report_hash": original["report_hash"],
            "snapshot_id": snapshot.snapshot_id, "result_matches": result_matches, "source_matches": source_matches,
            "environment_verified": environment_matches, "replay_verified": verified,
            "original_result_hash": original["result_hash"], "replayed_result_hash": replayed["result_hash"],
            "replay_provenance": replayed["provenance"], "execution_permission": original["execution_permission"]}
    return {**core, "receipt_hash": digest(core)}
