"""Display-only contracts for the original terminal's nine research strategies.

The caller supplies canonical parameters: normalized catalog parameters for a
new task, or the exact saved parameters when reading history. This module never
adds defaults to that parameter object and is outside the execution fingerprint.
It deliberately does not import terminal_research, server, or the signal engine.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any


PRESENTATION_VERSION = "terminal-strategy-presentation-v1"

_COMMON_LIMITATIONS = (
    "当前研究只做多、单一持仓、1 倍现金账户。买入信号只在空仓时产生，退出信号只在持仓时产生。",
    "使用已完成日线收盘形成信号，下一根开盘成交；信号不保证成交。最后一根信号不补成交，期末持仓按收盘估值。",
    "本次独立设置的止盈止损也可能退出；同一根同时触及止盈止损时按止损优先。",
    "原策略与同名股票研究策略保留不同规则身份，不自动替换。",
)


def _field(key: str, label: str, kind: str, minimum: float, *, help_text: str = "") -> dict[str, Any]:
    settings = {
        "count": ("integer", "bars", "根", 1, 1, 10000),
        "ratio_percent": ("number", "ratio", "%", 100, "any", 1e6),
        "multiplier": ("number", "multiple", "倍", 1, "any", 1e6),
        "oscillator_points": ("number", "points", "点", 1, "any", 100),
    }
    value_type, storage_unit, display_unit, scale, step, maximum = settings[kind]
    return {"key": key, "label": label, "type": value_type, "unit": kind,
            "storage_unit": storage_unit, "display_unit": display_unit,
            "display_scale": scale, "step": step, "minimum": minimum,
            "maximum": maximum, "display_minimum": minimum * scale,
            "display_maximum": maximum * scale, "help": help_text}


def _count(key: str, label: str, minimum: int, help_text: str = "") -> dict[str, Any]:
    return _field(key, label, "count", minimum,
                  help_text=help_text or "完整K线根数；日线任务中 1 根为 1 个完成交易日。")


def _percent(key: str, label: str, help_text: str = "") -> dict[str, Any]:
    return _field(key, label, "ratio_percent", 1e-12,
                  help_text=help_text or "按百分比输入；例如 1.5% 保存为原始比率 0.015。必须大于 0。")


_FIELDS = {
    "dual_ma": (
        _count("fast_window", "快均线周期", 2),
        _count("slow_window", "慢均线周期", 3, "慢均线周期必须大于快均线周期。"),
    ),
    "bollinger": (
        _count("window", "布林计算周期", 10),
        _field("std_mult", "标准差倍数", "multiplier", .5,
               help_text="布林轨道距离中轨的总体标准差倍数。"),
    ),
    "macd": (
        _count("fast", "快线 EMA 周期", 2),
        _count("slow", "慢线 EMA 周期", 3, "慢线 EMA 周期必须大于快线周期。"),
        _count("signal", "信号线 EMA 周期", 2),
    ),
    "rsi": (
        _count("window", "RSI 周期", 5),
        _field("oversold", "超卖阈值", "oscillator_points", 1e-12,
               help_text="RSI 指标点数，必须低于超买阈值；30 表示 30 点，不是 30% 的价格变化。"),
        _field("overbought", "超买阈值", "oscillator_points", 1e-12,
               help_text="RSI 指标点数，必须高于超卖阈值。"),
    ),
    "momentum": (
        _count("window", "动量回看周期", 5),
        _percent("threshold", "动量阈值", "例如输入 1.5，买入要求动量高于 +1.5%，退出要求低于 −1.5%；保存为 0.015。"),
    ),
    "livermore": (
        _count("pivot_window", "关键点回看周期", 20),
        _percent("confirm_pct", "突破确认幅度", "例如 0.6% 保存为 0.006；退出采用固定 0.5% 缓冲，与此参数不同。"),
    ),
    "turtle": (
        _count("entry_window", "入场通道周期", 10),
        _count("exit_window", "退出通道周期", 5),
    ),
    "darvas": (
        _count("box_window", "箱体回看周期", 20),
        _percent("confirm_pct", "突破确认幅度", "例如 0.4% 保存为 0.004；退出要求跌破箱体下沿。"),
    ),
    "volume_trend": (
        _count("trend_window", "趋势均线周期", 30),
        _count("fast_window", "快均线周期", 5),
        _count("breakout_window", "突破回看周期", 10),
        _count("exit_window", "退出回看周期", 5),
        _count("volume_window", "均量周期", 5, "计算前 N 根成交量均值，不含当前根。"),
        _count("atr_window", "ATR 周期", 5),
        _field("volume_ratio", "最低量比", "multiplier", .5,
               help_text="当根成交量÷前均量；例如 1.1 表示达到前均量的 1.1 倍。"),
        _percent("min_atr_pct", "最低 ATR 比例", "ATR÷收盘价的下限；例如 1% 保存为 0.01。"),
        _percent("max_atr_pct", "最高 ATR 比例", "ATR÷收盘价的上限，不能低于下限；例如 8% 保存为 0.08。"),
        _percent("max_extension_pct", "最大向上乖离", "收盘价÷快均线−1 的上限；例如 12% 保存为 0.12。"),
    ),
}

_RULES = {
    "dual_ma": {
        "entry_rule": "空仓时，快均线高于慢均线产生买入信号。",
        "exit_rule": "持仓时，快均线低于慢均线产生退出信号。",
        "notes": ("判断当前相对位置，无需当日发生上穿或下穿；两线相等时不触发信号。",),
    },
    "bollinger": {
        "entry_rule": "空仓时，收盘价低于布林下轨产生买入信号。",
        "exit_rule": "持仓时，收盘价高于中轨产生全部退出信号。",
        "notes": ("不额外等待止跌或重新进入通道，不使用上轨分批退出；轨道采用总体标准差。",),
    },
    "macd": {
        "entry_rule": "空仓时，DIF 高于 DEA，且柱差为正、不小于上一根柱差，产生买入信号。",
        "exit_rule": "持仓时，DIF 低于 DEA 产生退出信号。",
        "notes": ("柱差为 DIF−DEA，未乘 2；无需当日金叉或死叉，仅柱差变弱不足以触发策略退出。",),
    },
    "rsi": {
        "entry_rule": "空仓时，RSI 低于超卖阈值产生买入信号。",
        "exit_rule": "持仓时，RSI 高于超买阈值产生退出信号。",
        "notes": ("不额外检查价格止跌或背离；RSI 使用简单滚动平均涨跌幅，不是 Wilder 平滑。",),
    },
    "momentum": {
        "entry_rule": "动量＝当前收盘价÷N 根前收盘价−1；空仓时，动量高于正阈值产生买入信号。",
        "exit_rule": "持仓时，动量低于负阈值产生退出信号；例如阈值 1.5% 时，须低于 −1.5%，仅略低于 0 不会退出。",
        "notes": ("等于正、负阈值时不触发对应信号；不额外要求持续确认或跌回突破位。",),
    },
    "livermore": {
        "entry_rule": "空仓时，收盘价高于前 N 根最高收盘价乘以（1＋突破确认幅度），产生买入信号。",
        "exit_rule": "持仓时，收盘价低于前 min(30,N) 根最低收盘价的 99.5%，产生退出信号。",
        "notes": ("N 为关键点回看周期；前 N 根不含当前根。退出的 0.5% 缓冲是固定规则，不随入场确认幅度变化。",),
    },
    "turtle": {
        "entry_rule": "空仓时，收盘价高于前入场周期根数的最高收盘价产生买入信号。",
        "exit_rule": "持仓时，收盘价低于前退出周期根数的最低收盘价产生退出信号。",
        "notes": ("通道由前 N 根收盘价构成，不含当前根；本信号不按 ATR 调整仓位或止损。",),
    },
    "darvas": {
        "entry_rule": "空仓时，收盘价高于前 N 根最高收盘价乘以（1＋突破确认幅度），产生买入信号。",
        "exit_rule": "持仓时，收盘价低于前 N 根最低收盘价产生退出信号。",
        "notes": ("N 为箱体回看周期；滚动收盘区间不含当前根，不额外识别整理形态或站稳条件，回到箱体内不直接触发退出。",),
    },
    "volume_trend": {
        "entry_rule": "空仓时须同时满足：收盘突破前突破周期的最高价；快均线高于趋势均线且收盘高于趋势均线；量比达到下限；ATR÷收盘价位于上下限之间；收盘相对快均线的向上乖离不超过上限。",
        "exit_rule": "持仓时，收盘价低于前退出周期的最低价产生退出信号。",
        "notes": ("突破和退出采用前 N 根最高价、最低价，不含当前根；量比为当前成交量÷前均量。量比门槛、ATR 上下限和乖离上限包含等号。",
                  "已有持仓不因快线轻微转弱或量比降低而直接退出；该策略的本地模拟时钟尚未获支持。"),
    },
}


def strategy_parameter_fields(strategy_id: str, params: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """Project units without inventing a value for an absent historical field.

    ``value`` is always in storage units. A caller may render ``missing_text``
    when ``recorded`` is false. Defaults belong to the existing catalog/validator,
    not this display module. Returned dictionaries are detached from the caller.
    """
    identity = str(strategy_id or "").strip().lower()
    supplied = {} if params is None else params
    if not isinstance(supplied, Mapping):
        raise TypeError("strategy_presentation_parameters_require_mapping")
    fields = []
    for declared in _FIELDS.get(identity, ()):
        field = deepcopy(declared)
        field["recorded"] = field["key"] in supplied
        if field["recorded"]:
            field["value"] = deepcopy(supplied[field["key"]])
        else:
            field["missing_text"] = "未记录"
        fields.append(field)
    return fields


def strategy_presentation(strategy_id: str, params: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return additive UI metadata; unsupported/historical-only IDs return {}."""
    identity = str(strategy_id or "").strip().lower()
    rule = _RULES.get(identity)
    if rule is None:
        return {}
    return {
        "presentation_version": PRESENTATION_VERSION,
        "research_description": rule["entry_rule"] + rule["exit_rule"],
        "entry_rule": rule["entry_rule"],
        "exit_rule": rule["exit_rule"],
        "rule_notes": list(rule["notes"]),
        "limitations": list(_COMMON_LIMITATIONS),
        "parameter_fields": strategy_parameter_fields(identity, params),
        "parameter_note": "按标注单位填写；百分比在界面换算，任务、历史和跨页面传递保留原始单位。执行仓位、止盈止损使用独立风控字段。",
    }
