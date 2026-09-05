from __future__ import annotations

import copy
import math
from functools import wraps
from typing import Any

import pandas as pd

from hakimi_research.models import Portfolio, Signal


STRATEGY_BASE_SCHEMA_VERSION = "research-strategy-base-v1"
_MAX_PARAM_DEPTH = 32


def _fail(code: str) -> None:
    raise ValueError(code)


def _exact_text(value: object, *, label: str) -> str:
    if type(value) is not str:
        _fail(f"research_strategy_{label}_exact_str_required")
    if not value:
        _fail(f"research_strategy_{label}_nonempty_required")
    return value


def _clone_json(
    value: object,
    *,
    path: str,
    active_container_ids: set[int] | None = None,
    depth: int = 0,
    allow_nonfinite: bool = False,
) -> object:
    if depth > _MAX_PARAM_DEPTH:
        _fail("research_strategy_params_depth_exceeded")
    if active_container_ids is None:
        active_container_ids = set()
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        if not math.isfinite(value) and not allow_nonfinite:
            _fail(f"research_strategy_{path}_finite_required")
        return value
    if type(value) is list:
        identity = id(value)
        if identity in active_container_ids:
            _fail("research_strategy_params_cycle_rejected")
        active_container_ids.add(identity)
        try:
            return [
                _clone_json(
                    item,
                    path=f"{path}_{index}",
                    active_container_ids=active_container_ids,
                    depth=depth + 1,
                    allow_nonfinite=allow_nonfinite,
                )
                for index, item in enumerate(value)
            ]
        finally:
            active_container_ids.remove(identity)
    if type(value) is dict:
        identity = id(value)
        if identity in active_container_ids:
            _fail("research_strategy_params_cycle_rejected")
        active_container_ids.add(identity)
        try:
            cloned: dict[str, object] = {}
            for key, item in value.items():
                exact_key = _exact_text(key, label=f"{path}_key")
                cloned[exact_key] = _clone_json(
                    item,
                    path=f"{path}_{exact_key}",
                    active_container_ids=active_container_ids,
                    depth=depth + 1,
                    allow_nonfinite=allow_nonfinite,
                )
            return cloned
        finally:
            active_container_ids.remove(identity)
    _fail(f"research_strategy_{path}_exact_json_value_required")


def clone_strategy_params(
    params: dict[str, Any] | None,
    *,
    allow_nonfinite: bool = False,
) -> dict[str, Any]:
    if params is None:
        return {}
    if type(params) is not dict:
        _fail("research_strategy_params_exact_dict_required")
    return _clone_json(
        params,
        path="params",
        allow_nonfinite=allow_nonfinite,
    )


class StrategyBase:
    def __init__(
        self,
        params: dict[str, Any] | None = None,
        name: str = "base",
        version: str = "v1",
    ) -> None:
        object.__setattr__(
            self,
            "_params",
            clone_strategy_params(
                params,
                allow_nonfinite=type(self) is not StrategyBase,
            ),
        )
        object.__setattr__(self, "_name", _exact_text(name, label="name"))
        object.__setattr__(self, "_version", _exact_text(version, label="version"))

    def __setattr__(self, name: str, value: object) -> None:
        if name in {"params", "name", "version"}:
            raise AttributeError(f"research_strategy_identity_is_read_only:{name}")
        if name in {"_params", "_name", "_version"} and name in self.__dict__:
            raise AttributeError(f"research_strategy_identity_is_read_only:{name}")
        object.__setattr__(self, name, value)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        original = cls.__dict__.get("generate_signal")
        if original is None or getattr(original, "_research_strategy_guarded", False):
            return

        @wraps(original)
        def guarded(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
            if type(data) is not pd.DataFrame:
                _fail("research_strategy_exact_dataframe_required")
            if type(portfolio) is not Portfolio:
                _fail("research_strategy_exact_canonical_portfolio_required")
            data_snapshot = data.copy(deep=True)
            portfolio_snapshot = Portfolio(
                cash=portfolio.cash,
                position_qty=portfolio.position_qty,
                avg_entry_price=portfolio.avg_entry_price,
                realized_pnl=portfolio.realized_pnl,
                entry_fees=portfolio.entry_fees,
            )
            signal = original(self, data_snapshot, portfolio_snapshot)
            if type(signal) is not Signal:
                _fail("research_strategy_exact_canonical_signal_required")
            return signal

        guarded._research_strategy_guarded = True
        setattr(cls, "generate_signal", guarded)

    @property
    def params(self) -> dict[str, Any]:
        return copy.deepcopy(self._params)

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    def get(self, key: str, default: Any) -> Any:
        exact_key = _exact_text(key, label="param_key")
        if exact_key not in self._params:
            return copy.deepcopy(default)
        return copy.deepcopy(self._params[exact_key])

    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        raise NotImplementedError

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(params={self.params!r}, "
            f"name={self.name!r}, version={self.version!r})"
        )

    def __eq__(self, other: object) -> bool:
        return (
            type(other) is type(self)
            and other.params == self.params
            and other.name == self.name
            and other.version == self.version
        )


__all__ = [
    "STRATEGY_BASE_SCHEMA_VERSION",
    "StrategyBase",
    "Portfolio",
    "Signal",
    "clone_strategy_params",
]

