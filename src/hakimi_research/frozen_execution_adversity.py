from __future__ import annotations

from copy import deepcopy
import math
from typing import Any, Final

import pandas as pd

from hakimi_research.experiment_manifest import canonical_payload_hash
from hakimi_research.execution import ResearchExecutionSimulator
from hakimi_research.models import Action, Order, Portfolio, Signal
from hakimi_research.strategies.base import StrategyBase


POLICY_SCHEMA_VERSION: Final = "frozen-execution-adversity-policy-v2"
LIQUIDITY_REJECTION_EVIDENCE_SCHEMA_VERSION: Final = (
    "frozen-liquidity-rejection-evidence-v1"
)
WRAPPER_VERSION: Final = "execution-adversity-v1"
SCENARIO_IDS: Final = (
    "one_bar_signal_release_delay",
    "drop_every_third_actionable_signal",
    "source_fill_adverse_open_2pct",
)
UNMODELLED_GAPS: Final = (
    "DYNAMIC_MARKET_IMPACT_NOT_MODELLED",
    "INTRABAR_SHARED_VOLUME_BUDGET_NOT_MODELLED",
    "PARTIAL_FILL_REMAINDER_LIFECYCLE_NOT_MODELLED",
)


def _fail(code: str) -> None:
    raise ValueError(f"frozen_execution_adversity_{code}")


def _native_json(value: Any, *, path: str = "root") -> None:
    if value is None or type(value) in {bool, int, str}:
        return
    if type(value) is float:
        if not math.isfinite(value):
            _fail(f"{path}_nonfinite")
        return
    if type(value) is list:
        for index, item in enumerate(value):
            _native_json(item, path=f"{path}_{index}")
        return
    if type(value) is dict:
        for key in value:
            if type(key) is not str:
                _fail(f"{path}_key_type")
        for key, item in value.items():
            _native_json(item, path=f"{path}_{key}")
        return
    _fail(f"{path}_native_json_required")


def execution_adversity_policy_v2() -> dict[str, Any]:
    core = {
        "schema_version": POLICY_SCHEMA_VERSION,
        "source_cost_scenario": "BASE",
        "roles": ["VALIDATION", "FROZEN_TEST"],
        "scenarios": [
            {
                "scenario_id": "one_bar_signal_release_delay",
                "rule": "BUFFER_EACH_GENERATED_SIGNAL_FOR_ONE_ADDITIONAL_BAR",
                "performance_selected": False,
            },
            {
                "scenario_id": "drop_every_third_actionable_signal",
                "rule": "REPLACE_EVERY_THIRD_BUY_SELL_OR_EXIT_SIGNAL_WITH_HOLD",
                "drop_every": 3,
                "performance_selected": False,
            },
            {
                "scenario_id": "source_fill_adverse_open_2pct",
                "rule": "AT_SOURCE_NEXT_OPEN_FILL_TIMES_BUY_OPEN_PLUS_2_PERCENT_SELL_OPEN_MINUS_2_PERCENT",
                "shock_fraction": 0.02,
                "performance_selected": False,
            },
        ],
        "unmodelled_gaps": list(UNMODELLED_GAPS),
        "liquidity_capacity_probe": {
            "schema_version": "frozen-liquidity-capacity-probe-v1",
            "source_run_kind": "FIXED_BENCHMARK",
            "source_benchmark_id": "ENGINE_BUY_AND_HOLD",
            "source_cost_scenario": "BASE",
            "roles": ["VALIDATION", "FROZEN_TEST"],
            "scenario_id": "volume_participation_cap_0_1pct",
            "max_volume_participation_rate": 0.001,
            "remainder_lifecycle_modelled": False,
            "shared_bar_volume_budget_modelled": False,
            "performance_selected": False,
        },
        "liquidity_rejection_probe": {
            "schema_version": "frozen-liquidity-rejection-probe-v1",
            "source_capacity_scenario_id": "volume_participation_cap_0_1pct",
            "source_fill_selector": "FIRST_BUY_FILL",
            "roles": ["VALIDATION", "FROZEN_TEST"],
            "scenario_id": "minimum_executable_quantity_rejection",
            "max_volume_participation_rate": 0.000000001,
            "minimum_executable_quantity": 0.001,
            "performance_selected": False,
        },
        "formal_inference_claimed": False,
        "parameter_selection_allowed": False,
        "ranking_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "order_entry_allowed": False,
    }
    return {**core, "policy_hash": canonical_payload_hash(core)}


class OneBarSignalReleaseDelay(StrategyBase):
    def __init__(
        self,
        base: StrategyBase,
        strategy_id: str,
        identity_sha256: str,
        *,
        observer: dict[str, int] | None = None,
    ) -> None:
        super().__init__(
            params={
                "scenario_id": "one_bar_signal_release_delay",
                "base_strategy_id": strategy_id,
                "base_strategy_identity_sha256": identity_sha256,
            },
            name=base.name,
            version=WRAPPER_VERSION,
        )
        self._base = base
        self._strategy_id = strategy_id
        self._identity_sha256 = identity_sha256
        self._observer = observer if type(observer) is dict else {
            "generated_signal_count": 0,
            "released_signal_count": 0,
        }
        self._buffer: Signal | None = None

    def __deepcopy__(self, memo: dict[int, Any]) -> OneBarSignalReleaseDelay:
        clone = type(self)(
            deepcopy(self._base, memo),
            self._strategy_id,
            self._identity_sha256,
            observer=self._observer,
        )
        memo[id(self)] = clone
        return clone

    @property
    def generated_signal_count(self) -> int:
        return self._observer["generated_signal_count"]

    @property
    def released_signal_count(self) -> int:
        return self._observer["released_signal_count"]

    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        current = self._base.generate_signal(data, portfolio)
        self._observer["generated_signal_count"] += 1
        released = self._buffer
        self._buffer = current
        if released is None:
            return Signal(Action.HOLD, reason="execution adversity delay warmup")
        self._observer["released_signal_count"] += 1
        return released


class DropEveryThirdActionableSignal(StrategyBase):
    def __init__(
        self,
        base: StrategyBase,
        strategy_id: str,
        identity_sha256: str,
        *,
        observer: dict[str, int] | None = None,
    ) -> None:
        super().__init__(
            params={
                "scenario_id": "drop_every_third_actionable_signal",
                "base_strategy_id": strategy_id,
                "base_strategy_identity_sha256": identity_sha256,
                "drop_every": 3,
            },
            name=base.name,
            version=WRAPPER_VERSION,
        )
        self._base = base
        self._strategy_id = strategy_id
        self._identity_sha256 = identity_sha256
        self._observer = observer if type(observer) is dict else {
            "actionable_signal_count": 0,
            "dropped_signal_count": 0,
        }

    def __deepcopy__(self, memo: dict[int, Any]) -> DropEveryThirdActionableSignal:
        clone = type(self)(
            deepcopy(self._base, memo),
            self._strategy_id,
            self._identity_sha256,
            observer=self._observer,
        )
        memo[id(self)] = clone
        return clone

    @property
    def actionable_signal_count(self) -> int:
        return self._observer["actionable_signal_count"]

    @property
    def dropped_signal_count(self) -> int:
        return self._observer["dropped_signal_count"]

    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        signal = self._base.generate_signal(data, portfolio)
        if signal.action in {Action.BUY, Action.SELL, Action.EXIT}:
            self._observer["actionable_signal_count"] += 1
            if self._observer["actionable_signal_count"] % 3 == 0:
                self._observer["dropped_signal_count"] += 1
                return Signal(
                    Action.HOLD,
                    reason="execution adversity deterministic dropped signal",
                )
        return signal


def build_adverse_open_frame(
    source_frame: pd.DataFrame,
    source_result: dict[str, Any],
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    if type(source_frame) is not pd.DataFrame or type(source_result) is not dict:
        _fail("adverse_open_inputs_invalid")
    fills = source_result.get("fills")
    if type(fills) is not list:
        _fail("source_fills_exact_list_required")
    frame = source_frame.copy(deep=True)
    index_by_text = {str(index): index for index in frame.index}
    schedule: dict[str, str] = {}
    for fill in fills:
        if type(fill) is not dict:
            _fail("source_fill_exact_dict_required")
        if fill.get("fill_basis") != "NEXT_BAR_OPEN":
            continue
        action = fill.get("action")
        if action not in {"BUY", "SELL"}:
            continue
        fill_time = fill.get("fill_time")
        if type(fill_time) is not str or fill_time not in index_by_text:
            _fail("source_fill_time_not_bound")
        previous = schedule.get(fill_time)
        if previous is not None and previous != action:
            _fail("source_fill_schedule_conflict")
        schedule[fill_time] = action
    events: list[dict[str, Any]] = []
    for fill_time in sorted(
        schedule,
        key=lambda value: frame.index.get_loc(index_by_text[value]),
    ):
        action = schedule[fill_time]
        index = index_by_text[fill_time]
        source_open = float(frame.at[index, "open"])
        shock = 0.02 if action == "BUY" else -0.02
        stressed_open = source_open * (1.0 + shock)
        close = float(frame.at[index, "close"])
        frame.at[index, "open"] = stressed_open
        frame.at[index, "high"] = max(float(frame.at[index, "high"]), stressed_open, close)
        frame.at[index, "low"] = min(float(frame.at[index, "low"]), stressed_open, close)
        core = {
            "fill_time": fill_time,
            "source_action": action,
            "source_open": source_open,
            "stressed_open": stressed_open,
            "shock_fraction": shock,
        }
        events.append({**core, "event_sha256": canonical_payload_hash(core)})
    return frame, events


def prepare_execution_adversity_inputs(
    scenario_id: str,
    base_strategy: StrategyBase,
    source_frame: pd.DataFrame,
    source_result: dict[str, Any],
) -> tuple[StrategyBase, pd.DataFrame, list[dict[str, Any]]]:
    if type(scenario_id) is not str or scenario_id not in SCENARIO_IDS:
        _fail("scenario_id_invalid")
    if not isinstance(base_strategy, StrategyBase):
        _fail("base_strategy_invalid")
    identity = canonical_payload_hash({
        "name": base_strategy.name,
        "version": base_strategy.version,
        "params": base_strategy.params,
    })
    if scenario_id == "one_bar_signal_release_delay":
        strategy: StrategyBase = OneBarSignalReleaseDelay(base_strategy, base_strategy.name, identity)
        return strategy, source_frame.copy(deep=True), []
    if scenario_id == "drop_every_third_actionable_signal":
        strategy = DropEveryThirdActionableSignal(base_strategy, base_strategy.name, identity)
        return strategy, source_frame.copy(deep=True), []
    frame, events = build_adverse_open_frame(source_frame, source_result)
    return base_strategy, frame, events


def build_execution_adversity_metadata(
    scenario_id: str,
    strategy: StrategyBase,
    adverse_events: list[dict[str, Any]],
) -> dict[str, Any]:
    if scenario_id == "one_bar_signal_release_delay":
        if type(strategy) is not OneBarSignalReleaseDelay:
            _fail("delay_wrapper_mismatch")
        core = {
            "scenario_id": scenario_id,
            "generated_signal_count": strategy.generated_signal_count,
            "released_signal_count": strategy.released_signal_count,
            "unreleased_terminal_signal_count": strategy.generated_signal_count - strategy.released_signal_count,
        }
    elif scenario_id == "drop_every_third_actionable_signal":
        if type(strategy) is not DropEveryThirdActionableSignal:
            _fail("drop_wrapper_mismatch")
        core = {
            "scenario_id": scenario_id,
            "actionable_signal_count": strategy.actionable_signal_count,
            "dropped_signal_count": strategy.dropped_signal_count,
            "drop_every": 3,
        }
    elif scenario_id == "source_fill_adverse_open_2pct":
        if type(adverse_events) is not list:
            _fail("adverse_events_exact_list_required")
        core = {
            "scenario_id": scenario_id,
            "adverse_open_event_count": len(adverse_events),
            "adverse_open_events": deepcopy(adverse_events),
        }
    else:
        _fail("scenario_id_invalid")
    _native_json(core, path="metadata")
    return {**core, "metadata_hash": canonical_payload_hash(core)}


def verify_execution_adversity_metadata(value: Any) -> bool:
    _native_json(value, path="metadata")
    if type(value) is not dict or type(value.get("scenario_id")) is not str:
        _fail("metadata_shape_invalid")
    core = {key: item for key, item in value.items() if key != "metadata_hash"}
    if value.get("metadata_hash") != canonical_payload_hash(core):
        _fail("metadata_hash_invalid")
    scenario_id = value["scenario_id"]
    if scenario_id == "one_bar_signal_release_delay":
        if set(value) != {"scenario_id", "generated_signal_count", "released_signal_count", "unreleased_terminal_signal_count", "metadata_hash"}:
            _fail("delay_metadata_shape_invalid")
        generated = value["generated_signal_count"]
        released = value["released_signal_count"]
        if type(generated) is not int or type(released) is not int or generated <= 0 or released != generated - 1 or value["unreleased_terminal_signal_count"] != 1:
            _fail("delay_metadata_semantics_invalid")
    elif scenario_id == "drop_every_third_actionable_signal":
        if set(value) != {"scenario_id", "actionable_signal_count", "dropped_signal_count", "drop_every", "metadata_hash"}:
            _fail("drop_metadata_shape_invalid")
        actionable = value["actionable_signal_count"]
        dropped = value["dropped_signal_count"]
        if type(actionable) is not int or type(dropped) is not int or actionable < 0 or dropped != actionable // 3 or value["drop_every"] != 3:
            _fail("drop_metadata_semantics_invalid")
    elif scenario_id == "source_fill_adverse_open_2pct":
        events = value.get("adverse_open_events")
        if set(value) != {"scenario_id", "adverse_open_event_count", "adverse_open_events", "metadata_hash"} or type(events) is not list or value["adverse_open_event_count"] != len(events):
            _fail("adverse_open_metadata_shape_invalid")
        for event in events:
            if type(event) is not dict or set(event) != {"fill_time", "source_action", "source_open", "stressed_open", "shock_fraction", "event_sha256"}:
                _fail("adverse_open_event_shape_invalid")
            event_core = {key: item for key, item in event.items() if key != "event_sha256"}
            if event["event_sha256"] != canonical_payload_hash(event_core):
                _fail("adverse_open_event_hash_invalid")
            action = event["source_action"]
            expected_shock = 0.02 if action == "BUY" else -0.02 if action == "SELL" else None
            if expected_shock is None or event["shock_fraction"] != expected_shock:
                _fail("adverse_open_event_action_invalid")
            if not math.isclose(float(event["stressed_open"]), float(event["source_open"]) * (1.0 + expected_shock), rel_tol=0.0, abs_tol=1e-12):
                _fail("adverse_open_event_shock_invalid")
    else:
        _fail("metadata_scenario_invalid")
    return True


def _number(record: dict[str, Any], key: str) -> float:
    value = record.get(key)
    if type(value) not in {int, float} or type(value) is bool:
        _fail(f"result_{key}_number_required")
    parsed = float(value)
    if not math.isfinite(parsed):
        _fail(f"result_{key}_finite_required")
    return parsed


def build_execution_adversity_delta(source_result: Any, stressed_result: Any) -> dict[str, Any]:
    if type(source_result) is not dict or type(stressed_result) is not dict:
        _fail("delta_results_exact_dict_required")
    core = {
        "total_return_delta": _number(stressed_result, "total_return") - _number(source_result, "total_return"),
        "max_drawdown_delta": _number(stressed_result, "max_drawdown") - _number(source_result, "max_drawdown"),
        "trade_count_delta": int(_number(stressed_result, "trades")) - int(_number(source_result, "trades")),
        "final_equity_delta": _number(stressed_result, "final_equity") - _number(source_result, "final_equity"),
        "total_fee_delta": _number(stressed_result, "total_fees") - _number(source_result, "total_fees"),
    }
    return {**core, "delta_hash": canonical_payload_hash(core)}


def execution_adversity_observation_status(
    metadata: Any,
    source_result: Any,
) -> str:
    if type(metadata) is not dict or type(source_result) is not dict:
        _fail("observation_inputs_exact_dict_required")
    verify_execution_adversity_metadata(metadata)
    fills = source_result.get("fills")
    if type(fills) is not list:
        _fail("observation_source_fills_exact_list_required")
    scenario_id = metadata["scenario_id"]
    if scenario_id == "one_bar_signal_release_delay":
        observed = len(fills) > 0
    elif scenario_id == "drop_every_third_actionable_signal":
        observed = metadata["dropped_signal_count"] > 0
    else:
        observed = metadata["adverse_open_event_count"] > 0
    return "OBSERVED" if observed else "UNOBSERVED_SOURCE_ACTIVITY"


def build_liquidity_capacity_summary(
    result: Any,
    *,
    max_volume_participation_rate: float,
) -> dict[str, Any]:
    if type(result) is not dict:
        _fail("liquidity_result_exact_dict_required")
    if (
        type(max_volume_participation_rate) not in {int, float}
        or type(max_volume_participation_rate) is bool
    ):
        _fail("liquidity_participation_exact_number_required")
    rate = float(max_volume_participation_rate)
    if not math.isfinite(rate) or not 0 < rate <= 1:
        _fail("liquidity_participation_rate_invalid")
    fills = result.get("fills")
    if type(fills) is not list:
        _fail("liquidity_fills_exact_list_required")
    requested_total = 0.0
    filled_total = 0.0
    ratios: list[float] = []
    participation_rates: list[float] = []
    partial_fill_count = 0
    for fill in fills:
        if type(fill) is not dict:
            _fail("liquidity_fill_exact_dict_required")
        requested = _number(fill, "requested_quantity")
        filled = _number(fill, "filled_quantity")
        available = _number(fill, "available_volume")
        capacity = _number(fill, "volume_capacity_quantity")
        fill_ratio = _number(fill, "fill_ratio")
        if (
            fill.get("max_volume_participation_rate") != rate
            or type(fill.get("partial_fill")) is not bool
            or requested <= 0
            or filled <= 0
            or available <= 0
            or capacity <= 0
            or filled > requested + 1e-12
            or filled > capacity + 1e-12
            or not math.isclose(fill_ratio, filled / requested, rel_tol=0.0, abs_tol=1e-12)
        ):
            _fail("liquidity_fill_semantics_invalid")
        requested_total += requested
        filled_total += filled
        ratios.append(fill_ratio)
        participation_rates.append(filled / available)
        partial_fill_count += int(fill["partial_fill"])
    core = {
        "schema_version": "frozen-liquidity-capacity-summary-v1",
        "status": "OBSERVED" if fills and partial_fill_count > 0 else "UNOBSERVED",
        "fill_count": len(fills),
        "partial_fill_count": partial_fill_count,
        "requested_quantity_total": requested_total,
        "filled_quantity_total": filled_total,
        "minimum_fill_ratio": min(ratios) if ratios else None,
        "maximum_observed_participation_rate": (
            max(participation_rates) if participation_rates else None
        ),
        "max_volume_participation_rate": rate,
        "remainder_lifecycle_modelled": False,
        "shared_bar_volume_budget_modelled": False,
    }
    return {**core, "summary_hash": canonical_payload_hash(core)}


def verify_liquidity_capacity_summary(
    value: Any,
    result: Any,
    *,
    max_volume_participation_rate: float,
) -> bool:
    _native_json(value, path="liquidity_summary")
    if type(value) is not dict:
        _fail("liquidity_summary_exact_dict_required")
    expected = build_liquidity_capacity_summary(
        result,
        max_volume_participation_rate=max_volume_participation_rate,
    )
    if value != expected:
        _fail("liquidity_summary_verification_failed")
    return True


def build_liquidity_rejection_evidence(
    source_record: Any,
    *,
    probe: Any,
    policy_hash: str,
    initial_cash: float,
) -> dict[str, Any]:
    if type(source_record) is not dict or type(probe) is not dict:
        _fail("liquidity_rejection_inputs_exact_dict_required")
    role = source_record.get("role")
    if type(role) is not str or role not in probe.get("roles", []):
        _fail("liquidity_rejection_role_invalid")
    if source_record.get("scenario_id") != probe.get("source_capacity_scenario_id"):
        _fail("liquidity_rejection_source_scenario_invalid")
    result = source_record.get("result")
    fills = result.get("fills") if type(result) is dict else None
    if type(fills) is not list:
        _fail("liquidity_rejection_source_fills_exact_list_required")
    source_fill = next(
        (
            fill
            for fill in fills
            if type(fill) is dict and fill.get("action") == "BUY"
        ),
        None,
    )
    if type(source_fill) is not dict:
        _fail("liquidity_rejection_source_buy_fill_missing")
    order = Order(
        source_fill.get("symbol"),
        Action.BUY,
        _number(source_fill, "requested_quantity"),
        _number(source_fill, "price"),
        "source-bound liquidity rejection admission probe",
    )
    portfolio = Portfolio(cash=initial_cash)
    before = dict(portfolio.__dict__)
    simulator = ResearchExecutionSimulator(
        fee_rate=source_record.get("fee_rate"),
        slippage_pct=source_record.get("slippage_pct"),
        max_volume_participation_rate=probe.get(
            "max_volume_participation_rate"
        ),
        minimum_executable_quantity=probe.get("minimum_executable_quantity"),
    )
    decision = simulator.assess_order(
        order,
        portfolio,
        available_volume=_number(source_fill, "available_volume"),
    ).to_dict()
    if (
        portfolio.__dict__ != before
        or decision["status"] != "REJECTED"
        or decision["reason"] != "MINIMUM_EXECUTABLE_QUANTITY_NOT_MET"
    ):
        _fail("liquidity_rejection_decision_invalid")
    manifest = source_record.get("experiment_manifest")
    source_result_hash = (
        manifest.get("result_hash") if type(manifest) is dict else None
    )
    if type(source_result_hash) is not str or type(policy_hash) is not str:
        _fail("liquidity_rejection_source_hash_invalid")
    core = {
        "schema_version": LIQUIDITY_REJECTION_EVIDENCE_SCHEMA_VERSION,
        "role": role,
        "scenario_id": probe.get("scenario_id"),
        "source_capacity_scenario_id": source_record.get("scenario_id"),
        "source_benchmark_id": source_record.get("source_benchmark_id"),
        "source_result_hash": source_result_hash,
        "source_fill_sha256": canonical_payload_hash(source_fill),
        "policy_hash": policy_hash,
        "fixed_probe_initial_cash": float(initial_cash),
        "decision": decision,
        "portfolio_mutated": False,
        "interpretation": "SOURCE_BOUND_RESEARCH_ADMISSION_REJECTION_ONLY",
        "authority": {
            "tradable": False,
            "paper": False,
            "live": False,
            "order": False,
            "profitability_proof": False,
        },
    }
    return {**core, "evidence_hash": canonical_payload_hash(core)}


def verify_liquidity_rejection_evidence(
    value: Any,
    source_record: Any,
    *,
    probe: Any,
    policy_hash: str,
    initial_cash: float,
) -> bool:
    _native_json(value, path="liquidity_rejection_evidence")
    if type(value) is not dict:
        _fail("liquidity_rejection_evidence_exact_dict_required")
    expected = build_liquidity_rejection_evidence(
        source_record,
        probe=probe,
        policy_hash=policy_hash,
        initial_cash=initial_cash,
    )
    if value != expected:
        _fail("liquidity_rejection_evidence_verification_failed")
    return True
