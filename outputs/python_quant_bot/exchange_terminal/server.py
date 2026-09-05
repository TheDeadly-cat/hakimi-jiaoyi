from __future__ import annotations

try:
    from application.market_data_envelope import attach_market_data_envelope
except ModuleNotFoundError:  # Package import path.
    from exchange_terminal.application.market_data_envelope import attach_market_data_envelope

import argparse
import base64
import csv
import hashlib
import hmac
import io
import json
import ipaddress
import math
import mimetypes
import os
import random
import shutil
import socket
import sqlite3
import threading
import time
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo


RUNTIME_READ_ONLY = str(os.getenv("HAKIMI_RUNTIME_READ_ONLY") or "1").strip().lower() not in {
    "0", "false", "no", "off",
}

try:
    from services.anomaly_outcomes import anomaly_outcome_summary, evaluate_anomaly_outcome
    from services.anomaly_progression import annotate_anomaly_progression, anomaly_progression_summary
    from services.audit_log import AuditLog
    from services.backtest_engine import CAUSAL_AUDIT_VERSION, EXECUTION_MODEL_VERSION, causal_prefix_invariance_check, prepare_backtest_dataset, run_causal_long_only_backtest
    from services.event_replay import EventReplayService
    from services.event_bus import EventBus
    from services.event_lineage import build_signal_context
    from services.guardian_service import GuardianService
    from services.http_contract import RETIRED_MANAGEMENT_PATHS, MUTATION_PATHS, POST_API_PATHS, READABLE_MUTATION_PATHS, allowed_web_origin, archived_execution_route_state, payload_to_query, read_only_get_mutation_requested, trusted_refresh_get_allowed
    from services.instrument_rules import PublicInstrumentRuleService
    from services.forward_artifact_io import (
        MAX_PORTFOLIO_FORWARD_CONTROL_ARTIFACT_BYTES as MAX_PORTFOLIO_FORWARD_RECEIPT_ARTIFACT_BYTES,
        MAX_PORTFOLIO_FORWARD_STATUS_ARTIFACT_BYTES,
    )
    from services.immutable_artifact_bundle import ArtifactBundleError, read_bounded_artifact
    from services.market_adapters import build_market_adapter_catalog
    from services.configuration_projection import build_full_configuration_projection
    from services.market_anomaly_projection import (
        build_market_anomaly_detail_projection,
        build_market_anomaly_radar_projection,
        build_market_trend_cockpit_projection,
    )
    from services.market_scanner_projection import build_market_scanner_projection
    from services.market_data_service import MarketDataService, normalize_quote_data_quality
    from services.market_history_store import MarketHistoryStore, build_history_dataset_evidence, fetch_okx_daily_history_pages, normalize_history_candle
    from services.market_regime import classify_market_regime
    from services.mutation_journal import MutationJournal
    from application.archived_paper_runtime import (
        LEGACY_ORDER_TYPES as ORDER_TYPES,
        build_archived_paper_runtime,
    )
    from services.portfolio_experiment import PortfolioExperimentRegistry
    from services.portfolio_forward import load_active_portfolio_candidate
    from services.portfolio_evidence_archive import DEFAULT_BACKUP_STATUS_FILE
    from services.portfolio_forward_projection import build_portfolio_forward_status_projection
    from services.portfolio_forward_watchdog import DEFAULT_WATCHDOG_STATUS_FILE
    from services.portfolio_backtest_pack_pointer import load_portfolio_backtest_return_quality_snapshot
    from services.portfolio_forward_scheduler import (
        DEFAULT_SCHEDULER_STATUS_FILE,
        build_forward_observer_artifact_evidence,
        load_forward_scheduler_status,
    )
    from services.portfolio_shadow import (
        verify_forward_observation_change,
        verify_forward_status_artifact,
        verify_latest_forward_observation_receipt,
    )
    from services.portfolio_risk import build_correlation_matrix, evaluate_portfolio_risk
    from services.platform_control_center import (
        build_market_data_health_projection,
        build_platform_control_center_projection,
    )
    from services.platform_roadmap import build_six_lane_roadmap
    from services.public_order_book import PublicOrderBookService, legacy_okx_order_book_payload
    from services.research_bridge import ResearchBridge
    from services.research_query_projection import (
        build_research_context_projection,
        build_research_summaries_projection,
    )
    from services.research_panel_projection import build_research_panel_projection
    from services.risk_service import RiskService, apply_runtime_pretrade_authorization, build_pretrade_check, build_risk_snapshot, build_runtime_risk_view
    from services.runtime_build import RuntimeBuildGuard
    from services.small_capital_trial import build_small_capital_trial_plan
    from services.strategy_pipeline import StrategyPipeline
    from services.strategy_backtest_projection import (
        build_strategy_backtest_preview_error,
        build_strategy_backtest_preview_projection,
    )
    from services.backtest_risk_control_surface import BACKTEST_RISK_CONTROL_GRID, build_backtest_risk_control_surface
    from services.bot_research_projection import (
        build_bot_center_projection,
        build_bot_scheduler_projection,
        build_bot_scheduler_result_projection,
        build_strategy_robot_profiles_projection,
    )
    from services.strategy_analysis_projection import build_strategy_analysis_projection
    from services.market_ai_projection import build_market_ai_projection
    from services.deepseek_projection import build_deepseek_projection
    from services.trading_agents_projection import (
        build_trading_agents_projection,
        project_trading_agents_event,
    )
    from services.strategy_compare_projection import build_strategy_compare_projection
    from services.strategy_doctor_projection import build_strategy_doctor_projection
    from services.strategy_lab_projection import build_strategy_lab_projection
    from services.strategy_research_pointer import load_strategy_research_evidence_snapshot
    from services.strategy_war_room_projection import build_strategy_war_room_projection
    from services.strategy_data_admission import build_strategy_data_admission
    from services.strategy_matrix_evidence import latest_strategy_matrix_evidence
    from services.strategy_risk_profiles import strategy_research_risk_profile
    from services.strategy_signals import (
        build_strategy_signal_fn,
        rolling_strategy_signal as causal_rolling_strategy_signal,
        strategy_signal_input,
        strategy_signal_fingerprint,
        strategy_startup_candles_for_params as _strategy_startup_candles_for_params,
        strategy_validation_capability,
    )
    from services.stock_history_service import StockHistoryPrewarmService
    from services.strategy_quality import (
        backtest_acceptance_report,
        backtest_reproducibility,
        strategy_lookahead_check,
        strategy_release_pipeline,
    )
    from services.strategy_validation import chronological_folds, summarize_cost_sensitivity, summarize_walk_forward, temporal_data_split
    from services.strict_json_artifact import StrictJsonArtifactError, parse_strict_json_object
    from interfaces.http.health import build_research_disabled_response, build_health_response_from_runtime
except ModuleNotFoundError:
    from exchange_terminal.services.anomaly_outcomes import anomaly_outcome_summary, evaluate_anomaly_outcome
    from exchange_terminal.services.anomaly_progression import annotate_anomaly_progression, anomaly_progression_summary
    from exchange_terminal.services.audit_log import AuditLog
    from exchange_terminal.services.backtest_engine import CAUSAL_AUDIT_VERSION, EXECUTION_MODEL_VERSION, causal_prefix_invariance_check, prepare_backtest_dataset, run_causal_long_only_backtest
    from exchange_terminal.services.event_replay import EventReplayService
    from exchange_terminal.services.event_bus import EventBus
    from exchange_terminal.services.event_lineage import build_signal_context
    from exchange_terminal.services.guardian_service import GuardianService
    from exchange_terminal.services.http_contract import RETIRED_MANAGEMENT_PATHS, MUTATION_PATHS, POST_API_PATHS, READABLE_MUTATION_PATHS, allowed_web_origin, archived_execution_route_state, payload_to_query, read_only_get_mutation_requested, trusted_refresh_get_allowed
    from exchange_terminal.services.instrument_rules import PublicInstrumentRuleService
    from exchange_terminal.services.forward_artifact_io import (
        MAX_PORTFOLIO_FORWARD_CONTROL_ARTIFACT_BYTES as MAX_PORTFOLIO_FORWARD_RECEIPT_ARTIFACT_BYTES,
        MAX_PORTFOLIO_FORWARD_STATUS_ARTIFACT_BYTES,
    )
    from exchange_terminal.services.immutable_artifact_bundle import ArtifactBundleError, read_bounded_artifact
    from exchange_terminal.services.market_adapters import build_market_adapter_catalog
    from exchange_terminal.services.configuration_projection import build_full_configuration_projection
    from exchange_terminal.services.market_anomaly_projection import (
        build_market_anomaly_detail_projection,
        build_market_anomaly_radar_projection,
        build_market_trend_cockpit_projection,
    )
    from exchange_terminal.services.market_scanner_projection import build_market_scanner_projection
    from exchange_terminal.services.market_data_service import MarketDataService, normalize_quote_data_quality
    from exchange_terminal.services.market_history_store import MarketHistoryStore, build_history_dataset_evidence, fetch_okx_daily_history_pages, normalize_history_candle
    from exchange_terminal.services.market_regime import classify_market_regime
    from exchange_terminal.services.mutation_journal import MutationJournal
    from exchange_terminal.application.archived_paper_runtime import (
        LEGACY_ORDER_TYPES as ORDER_TYPES,
        build_archived_paper_runtime,
    )
    from exchange_terminal.services.portfolio_experiment import PortfolioExperimentRegistry
    from exchange_terminal.services.portfolio_forward import load_active_portfolio_candidate
    from exchange_terminal.services.portfolio_evidence_archive import DEFAULT_BACKUP_STATUS_FILE
    from exchange_terminal.services.portfolio_forward_projection import build_portfolio_forward_status_projection
    from exchange_terminal.services.portfolio_forward_watchdog import DEFAULT_WATCHDOG_STATUS_FILE
    from exchange_terminal.services.portfolio_backtest_pack_pointer import load_portfolio_backtest_return_quality_snapshot
    from exchange_terminal.services.portfolio_forward_scheduler import (
        DEFAULT_SCHEDULER_STATUS_FILE,
        build_forward_observer_artifact_evidence,
        load_forward_scheduler_status,
    )
    from exchange_terminal.services.portfolio_shadow import (
        verify_forward_observation_change,
        verify_forward_status_artifact,
        verify_latest_forward_observation_receipt,
    )
    from exchange_terminal.services.portfolio_risk import build_correlation_matrix, evaluate_portfolio_risk
    from exchange_terminal.services.platform_control_center import (
        build_market_data_health_projection,
        build_platform_control_center_projection,
    )
    from exchange_terminal.services.platform_roadmap import build_six_lane_roadmap
    from exchange_terminal.services.public_order_book import PublicOrderBookService, legacy_okx_order_book_payload
    from exchange_terminal.services.research_bridge import ResearchBridge
    from exchange_terminal.services.research_query_projection import (
        build_research_context_projection,
        build_research_summaries_projection,
    )
    from exchange_terminal.services.research_panel_projection import build_research_panel_projection
    from exchange_terminal.services.risk_service import RiskService, apply_runtime_pretrade_authorization, build_pretrade_check, build_risk_snapshot, build_runtime_risk_view
    from exchange_terminal.services.runtime_build import RuntimeBuildGuard
    from exchange_terminal.services.small_capital_trial import build_small_capital_trial_plan
    from exchange_terminal.services.strategy_pipeline import StrategyPipeline
    from exchange_terminal.services.strategy_backtest_projection import (
        build_strategy_backtest_preview_error,
        build_strategy_backtest_preview_projection,
    )
    from exchange_terminal.services.backtest_risk_control_surface import BACKTEST_RISK_CONTROL_GRID, build_backtest_risk_control_surface
    from exchange_terminal.services.bot_research_projection import (
        build_bot_center_projection,
        build_bot_scheduler_projection,
        build_bot_scheduler_result_projection,
        build_strategy_robot_profiles_projection,
    )
    from exchange_terminal.services.strategy_analysis_projection import build_strategy_analysis_projection
    from exchange_terminal.services.market_ai_projection import build_market_ai_projection
    from exchange_terminal.services.deepseek_projection import build_deepseek_projection
    from exchange_terminal.services.trading_agents_projection import (
        build_trading_agents_projection,
        project_trading_agents_event,
    )
    from exchange_terminal.services.strategy_compare_projection import build_strategy_compare_projection
    from exchange_terminal.services.strategy_doctor_projection import build_strategy_doctor_projection
    from exchange_terminal.services.strategy_lab_projection import build_strategy_lab_projection
    from exchange_terminal.services.strategy_research_pointer import load_strategy_research_evidence_snapshot
    from exchange_terminal.services.strategy_war_room_projection import build_strategy_war_room_projection
    from exchange_terminal.services.strategy_data_admission import build_strategy_data_admission
    from exchange_terminal.services.strategy_matrix_evidence import latest_strategy_matrix_evidence
    from exchange_terminal.services.strategy_risk_profiles import strategy_research_risk_profile
    from exchange_terminal.services.strategy_signals import (
        build_strategy_signal_fn,
        rolling_strategy_signal as causal_rolling_strategy_signal,
        strategy_signal_input,
        strategy_signal_fingerprint,
        strategy_startup_candles_for_params as _strategy_startup_candles_for_params,
        strategy_validation_capability,
    )
    from exchange_terminal.services.stock_history_service import StockHistoryPrewarmService
    from exchange_terminal.services.strategy_quality import (
        backtest_acceptance_report,
        backtest_reproducibility,
        strategy_lookahead_check,
        strategy_release_pipeline,
    )
    from exchange_terminal.services.strategy_validation import chronological_folds, summarize_cost_sensitivity, summarize_walk_forward, temporal_data_split
    from exchange_terminal.services.strict_json_artifact import StrictJsonArtifactError, parse_strict_json_object
    from exchange_terminal.interfaces.http.health import build_research_disabled_response, build_health_response_from_runtime

try:
    from config import (
        ALLOW_STOCK_FALLBACK,
        ALLOW_STOCK_HISTORY_FALLBACK,
        ANOMALY_EVENT_DB,
        API_CONFIG_FILE,
        APP_NAME,
        BTC_DAILY_CSV,
        BTC_DAILY_DATA_DIR,
        BTC_DAILY_DB,
        BTC_DAILY_DB_CACHE,
        BTC_DAILY_FALLBACK_CSV,
        BTC_DAILY_FALLBACK_DB,
        BTC_DAILY_FALLBACK_DIR,
        CODE_WORKER_FILE,
        CORE_CRYPTO_BASES,
        DEEPSEEK_BASE_URL,
        DEEPSEEK_MODEL,
        DEEPSEEK_THINKING_ENABLED,
        EXPORT_DIR,
        FUTU_HOST,
        FUTU_OPEND_XML,
        FUTU_PORT,
        FUTU_TELNET_HOST,
        FUTU_TELNET_PORT,
        LIVE_TRADING_HARD_BLOCK,
        MARKET_HISTORY_CACHE_DB,
        OKX_BASE_URL,
        OKX_TIMEOUT,
        OPENAI_BASE_URL,
        OPENAI_MODEL,
        PROFILE_FILE,
        PROJECT_DIR,
        ROOT_DIR,
        RUNTIME_DIR,
        STATIC_DIR,
        STOCK_CANDLE_CACHE_DB,
        STOCK_HISTORY_TIMEOUT,
        STOCK_MARKETS,
        STOCK_QUOTE_TIMEOUT,
        STOCK_SEED_PRICES,
        STOCK_SEED_VOLUMES,
        TERMINAL_RELEASE_NAME,
        TERMINAL_VERSION,
        LEDGER_FILE,
    )
except ModuleNotFoundError:
    from hakimi_research.terminal_config import (
        ALLOW_STOCK_FALLBACK,
        ALLOW_STOCK_HISTORY_FALLBACK,
        ANOMALY_EVENT_DB,
        API_CONFIG_FILE,
        APP_NAME,
        BTC_DAILY_CSV,
        BTC_DAILY_DATA_DIR,
        BTC_DAILY_DB,
        BTC_DAILY_DB_CACHE,
        BTC_DAILY_FALLBACK_CSV,
        BTC_DAILY_FALLBACK_DB,
        BTC_DAILY_FALLBACK_DIR,
        CODE_WORKER_FILE,
        CORE_CRYPTO_BASES,
        DEEPSEEK_BASE_URL,
        DEEPSEEK_MODEL,
        DEEPSEEK_THINKING_ENABLED,
        EXPORT_DIR,
        FUTU_HOST,
        FUTU_OPEND_XML,
        FUTU_PORT,
        FUTU_TELNET_HOST,
        FUTU_TELNET_PORT,
        LIVE_TRADING_HARD_BLOCK,
        MARKET_HISTORY_CACHE_DB,
        OKX_BASE_URL,
        OKX_TIMEOUT,
        OPENAI_BASE_URL,
        OPENAI_MODEL,
        PROFILE_FILE,
        PROJECT_DIR,
        ROOT_DIR,
        RUNTIME_DIR,
        STATIC_DIR,
        STOCK_CANDLE_CACHE_DB,
        STOCK_HISTORY_TIMEOUT,
        STOCK_MARKETS,
        STOCK_QUOTE_TIMEOUT,
        STOCK_SEED_PRICES,
        STOCK_SEED_VOLUMES,
        TERMINAL_RELEASE_NAME,
        TERMINAL_VERSION,
        LEDGER_FILE,
    )

try:
    from utils import (
        average,
        choice,
        clamp,
        clean_json_value,
        flag,
        human_age_ms,
        market_source_name,
        now_ms,
        pct,
        recent_volatility,
        safe_volume_ratio,
        trend_score,
    )
except ModuleNotFoundError:
    from hakimi_research.terminal_utils import (
        average,
        choice,
        clamp,
        clean_json_value,
        flag,
        human_age_ms,
        market_source_name,
        now_ms,
        pct,
        recent_volatility,
        safe_volume_ratio,
        trend_score,
    )

try:
    from hakimi_research.stock_metadata import (
        futu_code,
        is_stock_symbol,
        normalize_stock_interval,
        stock_meta,
        stock_session_from_ts,
        stock_session_label,
        stock_source_symbol,
        stock_timezone,
        yahoo_stock_symbol,
    )
    from hakimi_research.stock_candles import (
        aggregate_stock_rows,
        filter_stock_rows_by_session,
        latest_stock_candle_ts,
        stock_cache_fresh_ms,
        stock_cache_interval,
        stock_candle_cache_key,
        stock_candle_stale_warning,
        stock_payload_is_futu,
        stock_payload_has_due_incomplete_daily,
        stock_payload_needs_session_refresh,
        with_stock_freshness,
    )
    from market_data.stock_candles_io import (
        attest_stock_backtest_rows,
        attest_stock_candle_cache,
        audit_stock_daily_sources,
        augment_stock_daily_with_intraday,
        enrich_stock_series_contract,
        prepare_stock_candle_cache_rows,
        read_external_stock_candles,
        read_stock_persistent_candle_cache,
        record_stock_revision_snapshot,
        stock_candle_cache_coverage,
        stock_data_revision_summary,
        stock_external_provider_order,
        upsert_stock_candle_cache,
    )
    from market_data.provider_health import provider_call_allowed, provider_health_for_scope, provider_health_snapshot, record_provider_call
    from hakimi_research.stock_session import with_stock_session_contract
    from hakimi_research.stock_candle_quality import analyze_stock_candle_series, stock_candle_quality_public
    from services.market_calendar import resolve_stock_candle_schedule_attestation
    from market_data.futu import (
        futu_status_snapshot,
        futu_universe_snapshot,
        import_futu_sdk,
        reset_futu_status_cache,
    )
    from market_data.futu_quotes import (
        read_futu_quotes as read_futu_quotes_io,
        read_futu_stock_candles as read_futu_stock_candles_io,
    )
    from market_data.futu_deep import read_futu_deep_stock
    from hakimi_research.stock_quote_quality import normalize_stock_quote_quality, stock_quote_quarantine_reasons
    from market_data.okx import (
        okx_first as okx_first_io,
        okx_rows as okx_rows_io,
        okx_rows_with_error as okx_rows_with_error_io,
        read_bodyless_okx as read_bodyless_okx_io,
    )
    from research.stock_research import (
        stock_news_calendar_async as stock_news_calendar_async_io,
        stock_research_panel as stock_research_panel_io,
    )
except ModuleNotFoundError:
    from hakimi_research.stock_metadata import (
        futu_code,
        is_stock_symbol,
        normalize_stock_interval,
        stock_meta,
        stock_session_from_ts,
        stock_session_label,
        stock_source_symbol,
        stock_timezone,
        yahoo_stock_symbol,
    )
    from hakimi_research.stock_candles import (
        aggregate_stock_rows,
        filter_stock_rows_by_session,
        latest_stock_candle_ts,
        stock_cache_fresh_ms,
        stock_cache_interval,
        stock_candle_cache_key,
        stock_candle_stale_warning,
        stock_payload_is_futu,
        stock_payload_has_due_incomplete_daily,
        stock_payload_needs_session_refresh,
        with_stock_freshness,
    )
    from exchange_terminal.market_data.stock_candles_io import (
        attest_stock_backtest_rows,
        attest_stock_candle_cache,
        audit_stock_daily_sources,
        augment_stock_daily_with_intraday,
        enrich_stock_series_contract,
        prepare_stock_candle_cache_rows,
        read_external_stock_candles,
        read_stock_persistent_candle_cache,
        record_stock_revision_snapshot,
        stock_candle_cache_coverage,
        stock_data_revision_summary,
        stock_external_provider_order,
        upsert_stock_candle_cache,
    )
    from exchange_terminal.market_data.provider_health import provider_call_allowed, provider_health_for_scope, provider_health_snapshot, record_provider_call
    from hakimi_research.stock_session import with_stock_session_contract
    from hakimi_research.stock_candle_quality import analyze_stock_candle_series, stock_candle_quality_public
    from exchange_terminal.services.market_calendar import resolve_stock_candle_schedule_attestation
    from exchange_terminal.market_data.futu import (
        futu_status_snapshot,
        futu_universe_snapshot,
        import_futu_sdk,
        reset_futu_status_cache,
    )
    from exchange_terminal.market_data.futu_quotes import (
        read_futu_quotes as read_futu_quotes_io,
        read_futu_stock_candles as read_futu_stock_candles_io,
    )
    from exchange_terminal.market_data.futu_deep import read_futu_deep_stock
    from hakimi_research.stock_quote_quality import normalize_stock_quote_quality, stock_quote_quarantine_reasons
    from exchange_terminal.market_data.okx import (
        okx_first as okx_first_io,
        okx_rows as okx_rows_io,
        okx_rows_with_error as okx_rows_with_error_io,
        read_bodyless_okx as read_bodyless_okx_io,
    )
    from exchange_terminal.research.stock_research import (
        stock_news_calendar_async as stock_news_calendar_async_io,
        stock_research_panel as stock_research_panel_io,
    )
STOCK_QUOTE_CACHE: dict[str, Any] = {"time": 0, "rows": []}
STOCK_SINGLE_QUOTE_CACHE: dict[str, dict[str, Any]] = {}
STOCK_CANDLE_CACHE: dict[str, dict[str, Any]] = {}
STOCK_HISTORY_PREWARM_SERVICE: StockHistoryPrewarmService | None = None
RUNTIME_BUILD_GUARD = RuntimeBuildGuard(project_root=PROJECT_DIR, source_roots=[ROOT_DIR])
STOCK_HISTORY_PRIORITY = [
    "AAPL", "NVDA", "MSFT", "AMZN", "GOOGL", "META", "TSLA",
    "MU", "WDC", "STX", "PSTG", "NTAP", "AMD", "AVGO", "TSM", "ASML",
    "QQQ", "SPY", "HK.00002", "HK.00836",
]
MARKET_TICKERS_CACHE: dict[str, Any] = {"time": 0, "payload": None}
ANOMALY_RADAR_CACHE: dict[str, Any] = {"time": 0, "key": "", "payload": None}
STATE_LOCK = threading.RLock()


STRATEGIES = [
    {
        "id": "dual_ma",
        "name": "双均线趋势",
        "style": "趋势",
        "description": "快均线上穿慢均线后建立仓位，跌破后退出。",
        "params": {"fast_window": 20, "slow_window": 60, "position_pct": 0.25, "stop_loss_pct": 0.03},
    },
    {
        "id": "grid",
        "name": "网格策略",
        "style": "震荡",
        "description": "在价格区间内分层买入卖出，适合震荡行情。",
        "params": {"lookback": 80, "grids": 8, "position_pct": 0.12, "stop_loss_pct": 0.05},
    },
    {
        "id": "bollinger",
        "name": "布林带回归",
        "style": "均值回归",
        "description": "跌破下轨尝试建仓，回归中轨或上轨逐步退出。",
        "params": {"window": 20, "std_mult": 2.0, "position_pct": 0.2, "stop_loss_pct": 0.04},
    },
    {
        "id": "macd",
        "name": "MACD 动能",
        "style": "动量",
        "description": "MACD 金叉且柱体转强时入场，死叉时退出。",
        "params": {"fast": 12, "slow": 26, "signal": 9, "position_pct": 0.25, "stop_loss_pct": 0.035},
    },
    {
        "id": "rsi",
        "name": "RSI 超买超卖",
        "style": "反转",
        "description": "RSI 进入超卖区时尝试低吸，超买区退出。",
        "params": {"window": 14, "oversold": 30, "overbought": 70, "position_pct": 0.15},
    },
    {
        "id": "momentum",
        "name": "动量突破",
        "style": "突破",
        "description": "价格动量超过阈值后跟随趋势，动量转负退出。",
        "params": {"window": 20, "threshold": 0.015, "position_pct": 0.22},
    },
    {
        "id": "volume_trend",
        "name": "量价趋势突破",
        "style": "日线趋势",
        "description": "价格突破前高且趋势、成交量与波动率同时确认后进入研究观察。",
        "params": {
            "trend_window": 100,
            "fast_window": 50,
            "breakout_window": 20,
            "exit_window": 10,
            "volume_window": 20,
            "volume_ratio": 1.1,
            "position_pct": 0.22,
        },
    },
    {
        "id": "trend_pullback",
        "name": "趋势回调再启动",
        "style": "日线波段",
        "description": "只在长期趋势向上时，等待快线回调收复或放量突破，并用波动与结构条件退出。",
        "params": {
            "trend_window": 100,
            "fast_window": 20,
            "breakout_window": 20,
            "exit_window": 10,
            "volume_window": 20,
            "atr_window": 14,
        },
    },
    {
        "id": "squeeze_breakout",
        "name": "Volatility Squeeze Breakout",
        "style": "Daily Swing Research",
        "description": "Research-only volatility and volume contraction followed by confirmed range expansion.",
        "research_only": True,
        "params": {
            "atr_short_window": 10,
            "atr_long_window": 50,
            "volume_short_window": 10,
            "volume_long_window": 50,
            "squeeze_atr_ratio": 0.70,
            "volume_contraction_ratio": 0.75,
            "breakout_window": 20,
            "range_expansion_ratio": 1.40,
            "volume_expansion_ratio": 1.35,
            "trend_window": 100,
            "exit_window": 15,
            "max_breakout_atr": 1.75,
            "atr_stop_mult": 2.5,
        },
    },
    {
        "id": "martingale",
        "name": "马丁格尔",
        "style": "逆势加仓",
        "description": "价格回撤到锚点下方时分批加仓，反弹到均价上方时退出，属于高风险体系。",
        "params": {"anchor": "last_scale_price", "step_pct": 0.025, "take_profit_atr": 0.9, "stop_loss_atr": 3.2, "max_layers": 4},
    },
    {
        "id": "anti_martingale",
        "name": "反马丁",
        "style": "顺势加仓",
        "description": "只有浮盈扩大时才继续加仓，价格跌破跟踪锚点时退出。",
        "params": {"anchor": "last_scale_price", "step_pct": 0.02, "take_profit_atr": 2.4, "stop_loss_atr": 1.1, "max_layers": 3},
    },
    {
        "id": "livermore",
        "name": "利弗莫尔突破",
        "style": "关键点突破",
        "description": "参考利弗莫尔关键点思想，突破近期高点时跟随，跌回关键点下方时退出。",
        "params": {"pivot_window": 60, "confirm_pct": 0.006, "take_profit_atr": 2.8, "stop_loss_atr": 1.2},
    },
    {
        "id": "turtle",
        "name": "海龟交易",
        "style": "通道突破",
        "description": "突破20周期高点建仓，跌破10周期低点退出，使用波动率控制止损。",
        "params": {"entry_window": 20, "exit_window": 10, "take_profit_atr": 2.2, "stop_loss_atr": 1.0},
    },
    {
        "id": "darvas",
        "name": "达瓦斯箱体",
        "style": "箱体突破",
        "description": "价格突破整理箱体上沿时建仓，跌回箱体内部或下沿时退出。",
        "params": {"box_window": 40, "confirm_pct": 0.004, "take_profit_atr": 2.0, "stop_loss_atr": 1.1},
    },
]


def ensure_runtime() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            backup = path.with_suffix(f"{path.suffix}.bak")
            if backup.exists():
                try:
                    return json.loads(backup.read_text(encoding="utf-8"))
                except Exception:
                    return default
            return default
    except Exception:
        return default
    return default


def read_optional_portfolio_forward_status_artifact(
    path: Path,
    *,
    byte_limit: int = MAX_PORTFOLIO_FORWARD_STATUS_ARTIFACT_BYTES,
) -> dict[str, Any]:
    """Read one exact forward-status path without following links or retrying."""

    try:
        raw = read_bounded_artifact(
            path,
            byte_limit=byte_limit,
            size_limit_blocker="portfolio_forward_status_size_limit_exceeded",
        )
        payload = parse_strict_json_object(raw)
    except ArtifactBundleError as exc:
        read_status = "MISSING" if isinstance(exc.__cause__, FileNotFoundError) else "UNREADABLE"
        return {"read_status": read_status, "payload": {}}
    except (StrictJsonArtifactError, MemoryError):
        return {"read_status": "UNREADABLE", "payload": {}}
    if not payload:
        return {"read_status": "UNREADABLE", "payload": {}}
    return {"read_status": "READABLE", "payload": payload}


def write_json(path: Path, payload: Any) -> None:
    ensure_runtime()
    clean_payload = clean_json_value(payload)
    serialized = json.dumps(clean_payload, ensure_ascii=False, indent=2, sort_keys=True)
    with _json_guard:
        path.parent.mkdir(parents=True, exist_ok=True)
        backup_path = path.with_suffix(f"{path.suffix}.bak")
        if path.exists():
            try:
                shutil.copy2(path, backup_path)
            except Exception:
                pass
        temp_path = path.with_suffix(f"{path.suffix}.tmp")
        temp_file: Path | None = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=str(path.parent)) as handle:
                handle.write(serialized)
                handle.flush()
                try:
                    os.fsync(handle.fileno())
                except OSError:
                    pass
                temp_file = Path(handle.name)
            os.replace(temp_file, path)
            try:
                _ = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise RuntimeError("written json is corrupt") from exc
        except Exception:
            if temp_file is not None and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            if path.exists() and backup_path.exists():
                try:
                    shutil.copy2(backup_path, path)
                except Exception:
                    pass
            raise


def portfolio_forward_status_snapshot() -> dict[str, Any]:
    report_dir = Path(RUNTIME_DIR) / "reports"
    observed_now = now_ms()
    active_candidate: dict[str, Any] = {}
    performance_status: dict[str, Any] = {}
    backup_status: dict[str, Any] = {}
    watchdog_status: dict[str, Any] = {}
    backup_read_status = "MISSING"
    watchdog_read_status = "MISSING"

    def experiment_summary() -> dict[str, Any]:
        try:
            return PORTFOLIO_EXPERIMENTS.summary(3)
        except FileNotFoundError:
            if not RUNTIME_READ_ONLY:
                raise
            return {
                "status": "NOT_INITIALIZED",
                "experiments": [],
                "read_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }

    scheduler = load_forward_scheduler_status(
        report_dir / DEFAULT_SCHEDULER_STATUS_FILE,
        now_ms=observed_now,
    )

    def finalize(
        payload: dict[str, Any],
        *,
        observer_artifact_evidence: dict[str, Any] | None = None,
        observer_status: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return build_portfolio_forward_status_projection(
            payload,
            observed_now_ms=observed_now,
            live_trading_hard_block=LIVE_TRADING_HARD_BLOCK,
            observer_artifact_evidence=observer_artifact_evidence,
            active_candidate=active_candidate,
            observer_status=observer_status,
            performance_status=performance_status,
            backup_status=backup_status,
            watchdog_status=watchdog_status,
            backup_read_status=backup_read_status,
            watchdog_read_status=watchdog_read_status,
        )

    active = load_active_portfolio_candidate(report_dir)
    if active.get("status") != "PASS":
        return finalize({
            "status": "BLOCK",
            "blockers": list(active.get("blockers") or []),
            "active_candidate": dict(active.get("registry") or {}),
            "scheduler": scheduler,
            "experiment_registry": experiment_summary(),
        })
    active_candidate = dict(active.get("candidate") or {})
    candidate_hash = str(active_candidate.get("candidate_hash") or "")
    status_path = report_dir / f"portfolio_forward_status_{candidate_hash[:12]}.json"
    performance_status_path = (
        report_dir / f"portfolio_forward_performance_status_{candidate_hash[:12]}.json"
    )
    backup_status_path = report_dir / DEFAULT_BACKUP_STATUS_FILE
    watchdog_status_path = report_dir / DEFAULT_WATCHDOG_STATUS_FILE
    observer_read = read_optional_portfolio_forward_status_artifact(
        status_path,
        byte_limit=MAX_PORTFOLIO_FORWARD_STATUS_ARTIFACT_BYTES,
    )
    performance_read = read_optional_portfolio_forward_status_artifact(
        performance_status_path,
        byte_limit=MAX_PORTFOLIO_FORWARD_STATUS_ARTIFACT_BYTES,
    )
    backup_read = read_optional_portfolio_forward_status_artifact(
        backup_status_path,
        byte_limit=MAX_PORTFOLIO_FORWARD_RECEIPT_ARTIFACT_BYTES,
    )
    watchdog_read = read_optional_portfolio_forward_status_artifact(
        watchdog_status_path,
        byte_limit=MAX_PORTFOLIO_FORWARD_RECEIPT_ARTIFACT_BYTES,
    )
    payload = dict(observer_read.get("payload") or {})
    performance_status = dict(performance_read.get("payload") or {})
    backup_status = dict(backup_read.get("payload") or {})
    watchdog_status = dict(watchdog_read.get("payload") or {})
    backup_read_status = str(backup_read.get("read_status") or "UNREADABLE")
    watchdog_read_status = str(watchdog_read.get("read_status") or "UNREADABLE")
    if observer_read.get("read_status") != "READABLE":
        if observer_read.get("read_status") == "UNREADABLE":
            return finalize({
                "status": "BLOCK",
                "candidate_hash": candidate_hash,
                "blockers": ["forward_status_artifact_unreadable"],
                "active_candidate": dict(active.get("registry") or {}),
                "scheduler": scheduler,
                "experiment_registry": experiment_summary(),
            })
        return finalize({
            "status": "WAITING_FOR_FIRST_OBSERVATION",
            "candidate_hash": candidate_hash,
            "active_candidate": dict(active.get("registry") or {}),
            "robustness_status": str((active.get("robustness") or {}).get("status") or ""),
            "scheduler": scheduler,
            "experiment_registry": experiment_summary(),
        })
    verification = verify_forward_status_artifact(payload, candidate_hash=candidate_hash)
    if verification.get("status") != "PASS":
        return finalize({
            "status": "BLOCK",
            "candidate_hash": candidate_hash,
            "blockers": list(verification.get("blockers") or []),
            "artifact_verification": verification,
            "active_candidate": dict(active.get("registry") or {}),
            "scheduler": scheduler,
            "experiment_registry": experiment_summary(),
        })
    payload_blockers = [str(item) for item in payload.get("blockers") or [] if str(item)] if isinstance(payload.get("blockers"), list) else []
    observer_artifact_evidence = build_forward_observer_artifact_evidence(
        payload,
        candidate_hash=candidate_hash,
    )
    if observer_artifact_evidence.get("status") == "BLOCK":
        payload_blockers.extend(observer_artifact_evidence.get("blockers") or [])
    try:
        generated_at = int(payload.get("generated_at") or 0)
    except (TypeError, ValueError):
        generated_at = 0
        payload_blockers.append("forward_status_generated_at_invalid")
    if generated_at < 0:
        generated_at = 0
        payload_blockers.append("forward_status_generated_at_invalid")
    if generated_at > observed_now + 5_000:
        payload_blockers.append("forward_status_generated_at_from_future")

    def object_field(name: str) -> dict[str, Any]:
        value = payload.get(name)
        if isinstance(value, dict):
            return dict(value)
        if value is not None:
            payload_blockers.append(f"forward_status_{name}_invalid")
        return {}

    ledger_summary = object_field("ledger")
    latest_receipt_raw = payload.get("latest_observation_receipt")
    if latest_receipt_raw is None:
        latest_receipt_raw = {}
    elif not isinstance(latest_receipt_raw, dict):
        payload_blockers.append("forward_status_latest_observation_receipt_invalid")
        latest_receipt_raw = {}
    latest_receipt_verification = verify_latest_forward_observation_receipt(
        latest_receipt_raw,
        candidate_hash=candidate_hash,
        expected_signal_date=str(ledger_summary.get("last_signal_date") or ""),
        ledger_audit=ledger_summary.get("forward_audit"),
    )
    if latest_receipt_verification.get("status") == "BLOCK":
        payload_blockers.extend(latest_receipt_verification.get("blockers") or [])
    latest_receipt = dict(latest_receipt_verification.get("receipt") or {})
    latest_change_raw = payload.get("latest_observation_change")
    if latest_change_raw is None:
        latest_change_raw = {}
    elif not isinstance(latest_change_raw, dict):
        payload_blockers.append("forward_status_latest_observation_change_invalid")
        latest_change_raw = {}
    latest_change_verification = verify_forward_observation_change(
        latest_change_raw,
        candidate_hash=candidate_hash,
        expected_current_signal_date=str(ledger_summary.get("last_signal_date") or ""),
        ledger_audit=ledger_summary.get("forward_audit"),
    )
    if latest_change_verification.get("status") == "BLOCK":
        payload_blockers.extend(latest_change_verification.get("blockers") or [])
    latest_change = dict(latest_change_verification.get("change") or {})
    if str(latest_change.get("status") or "") == "VERIFIED":
        current_change = dict(latest_change.get("current") or {})
        if latest_receipt_verification.get("status") != "PASS":
            payload_blockers.append("forward_observation_change_latest_receipt_missing")
        elif (
            str(current_change.get("signal_date") or "") != str(latest_receipt.get("signal_date") or "")
            or str(current_change.get("observation_hash") or "") != str(latest_receipt.get("observation_hash") or "")
        ):
            payload_blockers.append("forward_observation_change_latest_receipt_mismatch")

    records_raw = payload.get("records")
    if records_raw is None:
        records_raw = []
    elif not isinstance(records_raw, list):
        payload_blockers.append("forward_status_records_invalid")
        records_raw = []
    records = [dict(item) for item in records_raw if isinstance(item, dict)]
    if len(records) != len(records_raw):
        payload_blockers.append("forward_status_record_invalid")
    observation = {
        "status": str(payload.get("status") or "UNKNOWN"),
        "generated_at": generated_at,
        "candidate_hash": candidate_hash,
        "frozen_dataset_last": str(payload.get("frozen_dataset_last") or ""),
        "current_dataset_last": str(payload.get("current_dataset_last") or ""),
        "incremental_plan": object_field("incremental_plan"),
        "work_summary": object_field("work_summary"),
        "ledger": ledger_summary,
        "latest_observation_receipt": latest_receipt,
        "latest_observation_change": latest_change,
        "latest_record": latest_receipt,
        "observation_only": payload.get("observation_only"),
        "simulation_only": payload.get("simulation_only"),
        "paper_authorized": payload.get("paper_authorized"),
        "live_order_allowed": payload.get("live_order_allowed"),
    }
    return finalize(
        {
            "status": str((payload.get("readiness") or {}).get("status") or payload.get("status") or "UNKNOWN"),
            "candidate_hash": candidate_hash,
            "active_candidate": dict(active.get("registry") or {}),
            "robustness_status": str((active.get("robustness") or {}).get("status") or ""),
            "generated_at": generated_at,
            "status_age_ms": max(observed_now - generated_at, 0) if generated_at else None,
            "readiness": object_field("readiness"),
            "blockers": list(dict.fromkeys(payload_blockers)),
            "last_run_status": str(payload.get("status") or ""),
            "artifact_verification": verification,
            "scheduler": scheduler,
            "observation": observation,
            "experiment_registry": experiment_summary(),
            "operational_health": str(scheduler.get("health") or "MISSING"),
        },
        observer_artifact_evidence=observer_artifact_evidence,
        observer_status=payload,
    )


EVENT_BUS = EventBus(now_ms=now_ms)
AUDIT_LOG = AuditLog(
    path=LEDGER_FILE,
    ensure_runtime=ensure_runtime,
    now_ms=now_ms,
    publish_event=lambda event_type, payload: EVENT_BUS.publish(event_type, payload, source="audit_log"),
    read_only=RUNTIME_READ_ONLY,
)


def record_runtime_audit(event: dict[str, Any]) -> dict[str, Any]:
    if not RUNTIME_READ_ONLY:
        return AUDIT_LOG.append(event)
    event_type = str(event.get("type") or "audit_event")
    row = {
        "time": now_ms(),
        **event,
        "persistence_status": "READ_ONLY_SKIPPED",
        "read_only": True,
    }
    bus_event = EVENT_BUS.publish(event_type, row, source="read_only_audit")
    row["event_seq"] = bus_event.get("seq")
    return row


(
    PAPER_ACCOUNT,
    PAPER_LEDGER,
    PAPER_EXECUTOR,
    PORTFOLIO_PAPER_LEDGER,
    PAPER_RECONCILIATION,
) = build_archived_paper_runtime()

EVENT_REPLAY = EventReplayService(
    now_ms=now_ms,
    audit_query=lambda **kwargs: AUDIT_LOG.query(**kwargs),
    order_loader=lambda order_id: PAPER_LEDGER.get_lifecycle_order(order_id),
    run_order_loader=lambda run_id, limit: PAPER_LEDGER.load_run_orders(run_id, limit),
)
MUTATION_JOURNAL = MutationJournal(
    db_path=RUNTIME_DIR / "mutation_journal.sqlite3",
    now_ms=now_ms,
    read_only=RUNTIME_READ_ONLY,
)
STRATEGY_PIPELINE = StrategyPipeline(
    db_path=RUNTIME_DIR / "strategy_pipeline.sqlite3",
    now_ms=now_ms,
    audit_writer=record_runtime_audit,
    read_only=RUNTIME_READ_ONLY,
)
RESEARCH_BRIDGE = ResearchBridge(
    db_path=RUNTIME_DIR / "research_bridge.sqlite3",
    now_ms=now_ms,
    audit_writer=record_runtime_audit,
    read_only=RUNTIME_READ_ONLY,
)
PORTFOLIO_EXPERIMENTS = PortfolioExperimentRegistry(
    db_path=RUNTIME_DIR / "portfolio_experiments.sqlite3",
    now_ms=now_ms,
    read_only=RUNTIME_READ_ONLY,
)


def append_ledger(event: dict[str, Any]) -> None:
    record_runtime_audit(event)


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    ensure_runtime()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def choose_strategy(strategy_id: str) -> dict[str, Any]:
    for strategy in STRATEGIES:
        if strategy["id"] == strategy_id:
            return strategy
    return {
        "id": str(strategy_id or "unknown"),
        "name": "Unsupported strategy",
        "style": "BLOCKED",
        "description": "Unknown strategy ids cannot fall back to another implementation.",
        "params": {},
        "unsupported": True,
    }


def strategy_playbook(strategy_id: str) -> dict[str, Any]:
    defaults = {
        "core_rule": "先识别市场状态，再让策略给出方向和仓位，风控永远先于信号。",
        "best_regime": "趋势或震荡不明确时只观察。",
        "avoid_regime": "急剧放量反向、流动性不足、风控分低于50。",
        "primary_indicators": ["价格", "波动率", "成交量", "趋势评分"],
        "entry_logic": "小仓试探，确认后再考虑加仓。",
        "exit_logic": "触发止损、趋势失效或策略反向时退出。",
        "risk_notes": ["不双向开仓", "先模拟盘验证", "单笔风险受风控限制"],
        "beginner_tip": "新手先看禁用条件，不要只看买入信号。",
    }
    playbooks = {
        "dual_ma": {
            "core_rule": "快均线站上慢均线代表趋势尝试，跌回慢均线下方退出。",
            "best_regime": "缓慢单边趋势、回撤较浅。",
            "avoid_regime": "横盘反复穿越均线、消息跳空。",
            "primary_indicators": ["MA20", "MA60", "趋势评分", "成交量确认"],
            "entry_logic": "MA20 > MA60 且价格不远离均线时开仓。",
            "exit_logic": "MA20 < MA60 或价格跌破风控线。",
        },
        "grid": {
            "core_rule": "在明确区间内低买高卖，不预测突破方向。",
            "best_regime": "震荡、箱体、资金费率温和。",
            "avoid_regime": "单边趋势、突破放量、区间上沿连续失守。",
            "primary_indicators": ["区间高低点", "网格层数", "位置百分比", "波动率"],
            "entry_logic": "价格接近区间下沿分批建仓。",
            "exit_logic": "价格接近区间上沿分批止盈，跌破区间停止补仓。",
        },
        "bollinger": {
            "core_rule": "价格偏离均值过远后，等待回归中轨。",
            "best_regime": "震荡回归、波动扩张后收敛。",
            "avoid_regime": "趋势加速时沿轨运行，不能盲目抄底摸顶。",
            "primary_indicators": ["布林上轨", "布林中轨", "布林下轨", "带宽"],
            "entry_logic": "跌破下轨后等待止跌或重新进入通道。",
            "exit_logic": "回到中轨/上轨分批减仓。",
        },
        "macd": {
            "core_rule": "用 MACD 金叉/死叉和柱体变化判断动能。",
            "best_regime": "趋势初期、动能连续增强。",
            "avoid_regime": "极窄震荡和假突破。",
            "primary_indicators": ["DIF", "DEA", "MACD柱", "零轴位置"],
            "entry_logic": "金叉且柱体转强时开仓。",
            "exit_logic": "死叉、柱体转弱或跌破止损线。",
        },
        "rsi": {
            "core_rule": "用 RSI 判断短期过热或过冷，偏均值回归。",
            "best_regime": "区间震荡、短线超跌反弹。",
            "avoid_regime": "强趋势里 RSI 可长时间超买/超卖。",
            "primary_indicators": ["RSI14", "超买线", "超卖线", "价格背离"],
            "entry_logic": "RSI 低位并出现止跌迹象时观察开仓。",
            "exit_logic": "RSI 回到中性/超买区或跌破止损。",
        },
        "momentum": {
            "core_rule": "只跟随已经形成的动能，不提前猜底顶。",
            "best_regime": "突破、热点、成交量扩张。",
            "avoid_regime": "缩量横盘、假突破后快速回落。",
            "primary_indicators": ["动量窗口", "涨跌幅阈值", "成交量", "突破失败"],
            "entry_logic": "动量超过阈值并持续时入场。",
            "exit_logic": "动量转负或跌回突破位。",
        },
        "martingale": {
            "core_rule": "逆势分层加仓，目标是反弹回均价上方退出；高风险。",
            "best_regime": "宽幅震荡、流动性好、无单边崩盘。",
            "avoid_regime": "趋势性下跌、杠杆过高、资金不足、连续破位。",
            "primary_indicators": ["首层锚点", "加仓间距", "最大层数", "均价"],
            "entry_logic": "价格低于短期均线锚点开首层，跌破下一层锚点才加仓。",
            "exit_logic": "回到均价上方或触发最大亏损熔断立即退出。",
            "risk_notes": ["只适合小仓模拟", "最大层数必须固定", "不能无限补仓"],
        },
        "anti_martingale": {
            "core_rule": "只在盈利后加仓，把资金压到顺势方向。",
            "best_regime": "趋势明确、浮盈持续扩大。",
            "avoid_regime": "震荡回吐、假突破、追高后无量。",
            "primary_indicators": ["浮盈锚点", "MA20", "MA60", "跟踪止损"],
            "entry_logic": "趋势与价格同步向上，先开首层。",
            "exit_logic": "跌破跟踪锚点或浮盈回吐时减仓/退出。",
        },
        "livermore": {
            "core_rule": "只交易关键点突破，突破失败立即承认错误。",
            "best_regime": "明确箱体突破、趋势初期、成交量放大。",
            "avoid_regime": "突破后快速跌回关键点、量能不足。",
            "primary_indicators": ["关键点", "突破确认", "回踩", "失败突破"],
            "entry_logic": "突破近期关键高点并确认后开仓。",
            "exit_logic": "跌回关键点下方或突破失败时退出。",
        },
        "turtle": {
            "core_rule": "突破通道高点跟随趋势，跌破短通道低点退出。",
            "best_regime": "中长线趋势、波动扩张。",
            "avoid_regime": "短线噪音过大、频繁假突破。",
            "primary_indicators": ["20周期高点", "10周期低点", "ATR", "单位风险"],
            "entry_logic": "突破入场通道后按波动率控制仓位。",
            "exit_logic": "跌破退出通道或ATR止损。",
        },
        "darvas": {
            "core_rule": "价格在箱体内整理，突破箱体上沿后跟随。",
            "best_regime": "强势整理后突破。",
            "avoid_regime": "箱体下沿被跌破或箱体高度过窄。",
            "primary_indicators": ["箱体上沿", "箱体下沿", "突破确认", "成交量"],
            "entry_logic": "突破箱体上沿并站稳时入场。",
            "exit_logic": "跌回箱体或跌破箱体下沿退出。",
        },
    }
    return {**defaults, **playbooks.get(strategy_id, {})}


def strategy_anchor_plan(
    strategy_id: str,
    direction: str,
    price: float,
    analysis: dict[str, Any],
    risk_config: dict[str, Any],
) -> list[dict[str, Any]]:
    strategy = choose_strategy(strategy_id)
    params = strategy.get("params", {})
    step_pct = float(params.get("step_pct") or 0.018)
    take_profit = float(analysis.get("take_profit") or 0.0)
    stop_loss = float(analysis.get("stop_loss") or 0.0)
    side_word = "上方" if direction == "LONG" else "下方"

    def level(name: str, anchor: float, action: str, detail: str, status: str = "WATCH") -> dict[str, Any]:
        return {
            "name": name,
            "anchor": round(anchor, 6) if anchor else 0.0,
            "action": action,
            "status": status,
            "detail": detail,
        }

    if price <= 0:
        return [level("等待价格", 0.0, "WAIT", "没有有效价格，不能计算锚点。", "BLOCK")]

    if strategy_id == "martingale":
        sign = -1 if direction == "LONG" else 1
        return [
            level("首层锚点", price, "OPEN_SMALL", "低于短期均线锚点才开首层，仓位要小。", "READY"),
            level("二层锚点", price * (1 + sign * step_pct), "ADD", f"价格逆向移动 {step_pct * 100:.1f}% 后才允许第二层。"),
            level("三层锚点", price * (1 + sign * step_pct * 2), "ADD", "必须确认仍未触发单日亏损限制。"),
            level("无效锚点", stop_loss, "STOP", "触发后停止补仓并平仓，禁止继续摊平。", "BLOCK"),
        ]
    if strategy_id == "anti_martingale":
        sign = 1 if direction == "LONG" else -1
        return [
            level("首层趋势锚", price, "OPEN_SMALL", "趋势成立后先开首层。", "READY"),
            level("浮盈加仓锚", price * (1 + sign * step_pct), "ADD_WINNER", f"只有盈利扩大 {step_pct * 100:.1f}% 才加仓。"),
            level("跟踪保护锚", price * (1 - sign * max(step_pct * 0.65, 0.01)), "REDUCE", "跌破浮盈保护位时减仓。"),
            level("最终止盈锚", take_profit, "TAKE_PROFIT", "达到目标后分批止盈，不一次性贪满。"),
        ]
    if strategy_id == "livermore":
        confirm = float(params.get("confirm_pct") or 0.006)
        sign = 1 if direction == "LONG" else -1
        pivot = price * (1 + sign * confirm)
        fail = price * (1 - sign * confirm * 0.8)
        return [
            level("关键点", round(price, 6), "WATCH", "当前价格作为最近关键点基准。"),
            level("突破确认", pivot, "OPEN", f"价格突破关键点{side_word} {confirm * 100:.2f}% 才考虑开仓。", "READY"),
            level("回踩验证", price, "HOLD", "突破后回踩不破关键点才保留仓位。"),
            level("失败突破", fail, "EXIT", "跌回关键点另一侧，视为突破失败。", "BLOCK"),
        ]
    if strategy_id == "grid":
        return [
            level("区间下沿", price * 0.96, "BUY", "接近下沿分批买入。", "READY"),
            level("区间中轴", price, "HOLD", "中间区域不追单。"),
            level("区间上沿", price * 1.04, "SELL", "接近上沿分批止盈。"),
            level("破位线", stop_loss or price * 0.94, "STOP", "跌破区间后暂停网格。", "BLOCK"),
        ]
    return [
        level("观察锚点", price, "WATCH", "等待策略信号确认。"),
        level("入场锚点", price * (1.003 if direction == "LONG" else 0.997), "OPEN_SMALL", "确认方向后小仓入场。", "READY"),
        level("止盈锚点", take_profit, "TAKE_PROFIT", "达到目标后分批减仓。"),
        level("止损锚点", stop_loss, "STOP", "触发止损后只减仓/退出。", "BLOCK"),
    ]


def local_candles_for_signal(limit: int = 120) -> list[dict[str, float]]:
    payload = read_local_btc_daily(limit)
    candles = []
    for row in payload.get("rows", []):
        try:
            candles.append({
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row.get("volume") or 0),
            })
        except Exception:
            continue
    return candles


def strategy_candles_for_symbol(symbol: str, limit: int = 180) -> list[dict[str, Any]]:
    try:
        payload = backtest_market_rows(symbol, max(int(limit), 120))
    except Exception:
        return []
    rows = [
        row for row in payload.get("rows") or []
        if bool(row.get("complete", True)) and float(row.get("close") or 0.0) > 0
    ]
    rows.sort(key=lambda row: int(row.get("ts_ms") or 0))
    return rows[-limit:]


def trade_direction_from_mode(value: str) -> str:
    return "SHORT" if str(value or "").upper() in {"SHORT", "SHORT_ONLY"} else "LONG"


def estimate_hit_probability(
    candles: list[dict[str, float]],
    entry_price: float,
    take_profit: float,
    stop_loss: float,
    direction: str = "LONG",
) -> float:
    direction = trade_direction_from_mode(direction)
    if len(candles) < 80 or entry_price <= 0:
        return 0.5
    if direction == "LONG" and (take_profit <= entry_price or stop_loss >= entry_price):
        return 0.5
    if direction == "SHORT" and (take_profit >= entry_price or stop_loss <= entry_price):
        return 0.5
    if direction == "SHORT":
        target_pct = 1 - take_profit / entry_price
        stop_pct = stop_loss / entry_price - 1
    else:
        target_pct = take_profit / entry_price - 1
        stop_pct = 1 - stop_loss / entry_price
    wins = 0
    losses = 0
    max_start = len(candles) - 12
    for index in range(max(30, len(candles) - 260), max_start):
        entry = float(candles[index]["close"])
        if direction == "SHORT":
            target = entry * (1 - target_pct)
            stop = entry * (1 + stop_pct)
        else:
            target = entry * (1 + target_pct)
            stop = entry * (1 - stop_pct)
        outcome = None
        for future in candles[index + 1:index + 12]:
            if direction == "SHORT" and float(future["high"]) >= stop:
                outcome = "loss"
                break
            if direction == "SHORT" and float(future["low"]) <= target:
                outcome = "win"
                break
            if direction == "LONG" and float(future["low"]) <= stop:
                outcome = "loss"
                break
            if direction == "LONG" and float(future["high"]) >= target:
                outcome = "win"
                break
        if outcome == "win":
            wins += 1
        elif outcome == "loss":
            losses += 1
    total = wins + losses
    if total < 12:
        return 0.5
    return clamp(wins / total, 0.18, 0.82)


def build_risk_config(query: dict[str, str], price: float) -> dict[str, Any]:
    risk_source = choice(query.get("riskSource"), {"AI", "MANUAL"}, "AI")
    value_mode = choice(query.get("riskValueMode"), {"PRICE", "PCT"}, "PRICE")
    order_type = choice(query.get("orderType"), ORDER_TYPES, "MARKET")
    margin_mode = choice(query.get("marginMode"), {"CROSS", "ISOLATED"}, "CROSS")
    direction_mode = choice(query.get("directionMode"), {"LONG_ONLY", "SHORT_ONLY"}, "LONG_ONLY")
    analysis_direction = trade_direction_from_mode(direction_mode)
    take_profit = pct(query.get("takeProfit", "0"))
    stop_loss = pct(query.get("stopLoss", "0"))
    take_profit_pct = pct(query.get("takeProfitPct", "0"))
    stop_loss_pct = pct(query.get("stopLossPct", "0"))

    manual_take_profit = 0.0
    manual_stop_loss = 0.0
    if risk_source == "MANUAL":
        if value_mode == "PCT":
            if price > 0 and take_profit_pct > 0:
                manual_take_profit = price * (1 - take_profit_pct / 100) if analysis_direction == "SHORT" else price * (1 + take_profit_pct / 100)
            if price > 0 and stop_loss_pct > 0:
                manual_stop_loss = price * (1 + stop_loss_pct / 100) if analysis_direction == "SHORT" else price * (1 - stop_loss_pct / 100)
        else:
            manual_take_profit = take_profit
            manual_stop_loss = stop_loss

    return {
        "risk_source": risk_source,
        "value_mode": value_mode,
        "order_type": order_type,
        "margin_mode": margin_mode,
        "direction_mode": direction_mode,
        "analysis_direction": analysis_direction,
        "manual_take_profit": manual_take_profit,
        "manual_stop_loss": manual_stop_loss,
        "take_profit_input": take_profit,
        "stop_loss_input": stop_loss,
        "take_profit_pct": max(0.0, take_profit_pct),
        "stop_loss_pct": max(0.0, stop_loss_pct),
        "trailing_take_enabled": flag(query.get("trailingTakeEnabled")),
        "trailing_take_pct": clamp(pct(query.get("trailingTakePct", "1.5")), 0.05, 50.0),
        "trailing_stop_enabled": flag(query.get("trailingStopEnabled")),
        "trailing_stop_pct": clamp(pct(query.get("trailingStopPct", "1.0")), 0.05, 50.0),
        "reduce_only": flag(query.get("reduceOnly")),
    }


def analyze_strategy_context(
    strategy_id: str,
    symbol: str,
    price: float,
    manual_take_profit: float = 0.0,
    manual_stop_loss: float = 0.0,
    direction: str = "LONG",
) -> dict[str, Any]:
    direction = trade_direction_from_mode(direction)
    candles = strategy_candles_for_symbol(symbol, 360)
    closes = [float(item["close"]) for item in candles]
    if len(candles) < 60 or price <= 0:
        empty_plan = {
            "direction": direction,
            "take_profit": round(manual_take_profit, 4) if manual_take_profit else 0.0,
            "stop_loss": round(manual_stop_loss, 4) if manual_stop_loss else 0.0,
            "profit_probability": 0.5,
            "risk_reward": 0.0,
            "probability_level": "中性",
        }
        return {
            "symbol": symbol,
            "strategy_id": strategy_id,
            "direction": direction,
            "direction_label": "做空" if direction == "SHORT" else "做多",
            "take_profit": round(manual_take_profit, 4) if manual_take_profit else 0.0,
            "stop_loss": round(manual_stop_loss, 4) if manual_stop_loss else 0.0,
            "profit_probability": 0.5,
            "risk_reward": 0.0,
            "trend_score": 0.0,
            "volatility_pct": 0.0,
            "long_plan": empty_plan if direction == "LONG" else {**empty_plan, "direction": "LONG", "take_profit": 0.0, "stop_loss": 0.0},
            "short_plan": empty_plan if direction == "SHORT" else {**empty_plan, "direction": "SHORT", "take_profit": 0.0, "stop_loss": 0.0},
            "source": "insufficient_history",
            "reason": "等待足够历史数据后再估算止盈止损",
            "manual_take_profit": bool(manual_take_profit),
            "manual_stop_loss": bool(manual_stop_loss),
        }

    strategy = choose_strategy(strategy_id)
    params = strategy.get("params", {})
    vol = recent_volatility(candles, 20)
    trend = trend_score(closes)
    tp_mult = float(params.get("take_profit_atr", 1.8))
    sl_mult = float(params.get("stop_loss_atr", 1.1))
    if strategy_id == "martingale":
        tp_mult, sl_mult = 0.9, 3.2
    elif strategy_id == "anti_martingale":
        tp_mult, sl_mult = 2.4, 1.1
    elif strategy_id == "livermore":
        tp_mult, sl_mult = 2.8, 1.2
    elif strategy_id == "grid":
        tp_mult, sl_mult = 1.0, 1.8

    style_adjust = {
        "martingale": -0.05,
        "anti_martingale": 0.04 if trend > 0 else -0.03,
        "livermore": 0.06 if trend > 0.12 else -0.02,
        "turtle": 0.04 if trend > 0.08 else -0.01,
        "darvas": 0.03 if trend > 0 else -0.01,
        "grid": 0.03 if abs(trend) < 0.16 else -0.03,
    }.get(strategy_id, 0.0)

    def build_plan(plan_direction: str, use_manual: bool = False) -> dict[str, Any]:
        plan_direction = trade_direction_from_mode(plan_direction)
        tp_pct = clamp(vol * tp_mult, 0.008, 0.35)
        sl_pct = clamp(vol * sl_mult, 0.006, 0.45)
        if plan_direction == "SHORT":
            suggested_take_profit = price * (1 - tp_pct)
            suggested_stop_loss = price * (1 + sl_pct)
            take_profit = manual_take_profit if use_manual and 0 < manual_take_profit < price else suggested_take_profit
            stop_loss = manual_stop_loss if use_manual and manual_stop_loss > price else suggested_stop_loss
            direction_trend = -trend
            risk = max(stop_loss - price, 1e-9)
            reward = max(price - take_profit, 0.0)
            level_mid = "中性偏空"
            label = "做空"
        else:
            suggested_take_profit = price * (1 + tp_pct)
            suggested_stop_loss = price * (1 - sl_pct)
            take_profit = manual_take_profit if use_manual and manual_take_profit > price else suggested_take_profit
            stop_loss = manual_stop_loss if use_manual and 0 < manual_stop_loss < price else suggested_stop_loss
            direction_trend = trend
            risk = max(price - stop_loss, 1e-9)
            reward = max(take_profit - price, 0.0)
            level_mid = "中性偏多"
            label = "做多"
        win_rate = estimate_hit_probability(candles, price, take_profit, stop_loss, plan_direction)
        probability = clamp(win_rate * 0.7 + (0.5 + direction_trend * 0.18) * 0.3 + style_adjust, 0.18, 0.82)
        risk_reward = reward / risk
        if probability >= 0.62:
            level = "偏高"
        elif probability >= 0.52:
            level = level_mid
        elif probability >= 0.45:
            level = "中性"
        else:
            level = "偏低"
        return {
            "direction": plan_direction,
            "direction_label": label,
            "take_profit": round(take_profit, 4),
            "stop_loss": round(stop_loss, 4),
            "suggested_take_profit": round(suggested_take_profit, 4),
            "suggested_stop_loss": round(suggested_stop_loss, 4),
            "profit_probability": round(probability, 4),
            "historical_hit_rate": round(win_rate, 4),
            "risk_reward": round(risk_reward, 2),
            "probability_level": level,
        }

    selected_plan = build_plan(direction, True)
    long_plan = selected_plan if direction == "LONG" else build_plan("LONG", False)
    short_plan = selected_plan if direction == "SHORT" else build_plan("SHORT", False)

    return {
        "symbol": symbol,
        "strategy_id": strategy_id,
        "strategy_name": strategy["name"],
        "direction": selected_plan["direction"],
        "direction_label": selected_plan["direction_label"],
        "take_profit": selected_plan["take_profit"],
        "stop_loss": selected_plan["stop_loss"],
        "suggested_take_profit": selected_plan["suggested_take_profit"],
        "suggested_stop_loss": selected_plan["suggested_stop_loss"],
        "profit_probability": selected_plan["profit_probability"],
        "historical_hit_rate": selected_plan["historical_hit_rate"],
        "risk_reward": selected_plan["risk_reward"],
        "trend_score": round(trend, 4),
        "volatility_pct": round(vol * 100, 2),
        "probability_level": selected_plan["probability_level"],
        "long_plan": long_plan,
        "short_plan": short_plan,
        "source": "local_ai_heuristic",
        "manual_take_profit": bool(manual_take_profit),
        "manual_stop_loss": bool(manual_stop_loss),
        "reason": f"{strategy['name']}：当前采用{selected_plan['direction_label']}，近期波动约 {vol * 100:.2f}%，趋势评分 {trend:.2f}，盈亏比 {selected_plan['risk_reward']:.2f}",
    }


def _legacy_evaluate_strategy_signal(
    strategy_id: str,
    price: float,
    has_position: bool,
    entry_price: float = 0.0,
    last_scale_price: float = 0.0,
) -> dict[str, Any]:
    candles = local_candles_for_signal(160)
    closes = [item["close"] for item in candles]
    if len(closes) < 30 or price <= 0:
        return {"action": "HOLD", "confidence": 0.0, "reason": "等待足够历史K线"}

    if strategy_id == "dual_ma":
        fast = average(closes[-20:])
        slow = average(closes[-60:]) if len(closes) >= 60 else average(closes)
        if fast > slow and not has_position:
            return {"action": "BUY", "confidence": 0.72, "reason": "快均线位于慢均线上方"}
        if fast < slow and has_position:
            return {"action": "EXIT", "confidence": 0.68, "reason": "快均线跌破慢均线"}
        return {"action": "HOLD", "confidence": 0.42, "reason": "均线未触发新动作"}

    if strategy_id == "grid":
        recent = closes[-80:]
        low = min(recent)
        high = max(recent)
        if high <= low:
            return {"action": "HOLD", "confidence": 0.0, "reason": "网格区间过窄"}
        location = (price - low) / (high - low)
        if location < 0.28 and not has_position:
            return {"action": "BUY", "confidence": 0.63, "reason": "价格接近网格下沿"}
        if location > 0.72 and has_position:
            return {"action": "SELL", "confidence": 0.61, "reason": "价格接近网格上沿"}
        return {"action": "HOLD", "confidence": 0.38, "reason": "价格处于网格中部"}

    if strategy_id == "bollinger":
        recent = closes[-20:]
        mid = average(recent)
        variance = average([(value - mid) ** 2 for value in recent])
        band = variance ** 0.5 * 2
        if price < mid - band and not has_position:
            return {"action": "BUY", "confidence": 0.66, "reason": "价格跌破布林下轨"}
        if price > mid and has_position:
            return {"action": "SELL", "confidence": 0.58, "reason": "价格回归布林中轨上方"}
        return {"action": "HOLD", "confidence": 0.35, "reason": "价格仍在布林通道内"}

    if strategy_id == "rsi":
        gains = []
        losses = []
        for previous, current in zip(closes[-15:-1], closes[-14:]):
            change = current - previous
            gains.append(max(change, 0))
            losses.append(abs(min(change, 0)))
        rs = average(gains) / max(average(losses), 1e-9)
        rsi = 100 - 100 / (1 + rs)
        if rsi < 30 and not has_position:
            return {"action": "BUY", "confidence": 0.64, "reason": f"RSI 超卖 {rsi:.1f}"}
        if rsi > 70 and has_position:
            return {"action": "EXIT", "confidence": 0.64, "reason": f"RSI 超买 {rsi:.1f}"}
        return {"action": "HOLD", "confidence": 0.36, "reason": f"RSI 中性 {rsi:.1f}"}

    if strategy_id == "martingale":
        anchor = last_scale_price or entry_price or closes[-1]
        step = 0.025
        if not has_position and price < average(closes[-20:]) * 0.985:
            return {"action": "BUY", "confidence": 0.58, "reason": "马丁首层：价格低于短期均线锚点"}
        if has_position and price <= anchor * (1 - step):
            return {"action": "ADD", "confidence": 0.54, "reason": "马丁加仓：价格跌破下一层锚点"}
        if has_position and entry_price and price >= entry_price * 1.018:
            return {"action": "EXIT", "confidence": 0.62, "reason": "马丁退出：价格回到均价上方"}
        return {"action": "HOLD", "confidence": 0.34, "reason": "马丁等待下一层锚点"}

    if strategy_id == "anti_martingale":
        ma20 = average(closes[-20:])
        ma60 = average(closes[-60:]) if len(closes) >= 60 else average(closes)
        anchor = last_scale_price or entry_price or price
        if not has_position and ma20 > ma60 and price > ma20:
            return {"action": "BUY", "confidence": 0.66, "reason": "反马丁首层：趋势与价格同步向上"}
        if has_position and price >= anchor * 1.02:
            return {"action": "ADD", "confidence": 0.62, "reason": "反马丁加仓：浮盈突破新锚点"}
        if has_position and price < ma20 * 0.985:
            return {"action": "EXIT", "confidence": 0.6, "reason": "反马丁退出：跌破短期趋势锚点"}
        return {"action": "HOLD", "confidence": 0.4, "reason": "反马丁等待浮盈扩张"}

    if strategy_id == "livermore":
        pivot_high = max(closes[-60:-1])
        pivot_low = min(closes[-30:])
        if not has_position and price > pivot_high * 1.006:
            return {"action": "BUY", "confidence": 0.7, "reason": "利弗莫尔关键点突破"}
        if has_position and price < pivot_low * 0.995:
            return {"action": "EXIT", "confidence": 0.66, "reason": "跌回关键点防守位"}
        return {"action": "HOLD", "confidence": 0.44, "reason": "等待关键点确认"}

    if strategy_id == "turtle":
        entry_high = max(closes[-20:-1])
        exit_low = min(closes[-10:])
        if not has_position and price > entry_high:
            return {"action": "BUY", "confidence": 0.68, "reason": "海龟20周期突破"}
        if has_position and price < exit_low:
            return {"action": "EXIT", "confidence": 0.64, "reason": "海龟10周期退出"}
        return {"action": "HOLD", "confidence": 0.41, "reason": "通道未触发"}

    if strategy_id == "darvas":
        box_high = max(closes[-40:-1])
        box_low = min(closes[-40:-1])
        if not has_position and price > box_high * 1.004:
            return {"action": "BUY", "confidence": 0.64, "reason": "达瓦斯箱体向上突破"}
        if has_position and price < box_low:
            return {"action": "EXIT", "confidence": 0.63, "reason": "跌破达瓦斯箱体下沿"}
        return {"action": "HOLD", "confidence": 0.39, "reason": "箱体内震荡"}

    momentum = price / max(closes[-20], 1e-9) - 1
    if momentum > 0.015 and not has_position:
        return {"action": "BUY", "confidence": 0.7, "reason": f"20日动量 {momentum:.2%}"}
    if momentum < -0.015 and has_position:
        return {"action": "EXIT", "confidence": 0.67, "reason": f"20日动量转弱 {momentum:.2%}"}
    return {"action": "HOLD", "confidence": 0.4, "reason": "动量未突破阈值"}


def _legacy_evaluate_directional_strategy_signal(
    strategy_id: str,
    price: float,
    direction_mode: str,
    position_qty: float,
    entry_price: float = 0.0,
    last_scale_price: float = 0.0,
) -> dict[str, Any]:
    if direction_mode != "SHORT_ONLY":
        return evaluate_strategy_signal(strategy_id, price, position_qty > 0, entry_price, last_scale_price)
    if position_qty < 0:
        raw = evaluate_strategy_signal(strategy_id, price, False, entry_price, last_scale_price)
        if raw.get("action") in {"BUY", "ADD"}:
            return {
                **raw,
                "action": "EXIT",
                "reason": f"空头平仓：{raw.get('reason', '多头信号出现')}",
            }
        return {
            **raw,
            "action": "HOLD",
            "reason": f"空头持有：{raw.get('reason', '未出现平空信号')}",
        }
    raw = evaluate_strategy_signal(strategy_id, price, True, entry_price, last_scale_price)
    if raw.get("action") in {"SELL", "EXIT"}:
        return {
            **raw,
            "action": "SELL",
            "reason": f"空头开仓：{raw.get('reason', '反向信号出现')}",
        }
    return {
        **raw,
        "action": "HOLD",
        "reason": f"只做空等待：{raw.get('reason', '未出现空头入场信号')}",
    }


def evaluate_directional_strategy_signal(
    strategy_id: str,
    price: float,
    direction_mode: str,
    position_qty: float,
    entry_price: float = 0.0,
    last_scale_price: float = 0.0,
    *,
    closes: list[float] | None = None,
    bars: list[dict[str, Any]] | None = None,
    symbol: str = "",
) -> dict[str, Any]:
    if str(direction_mode or "LONG_ONLY").upper() != "LONG_ONLY":
        return {
            "action": "HOLD",
            "confidence": 0.0,
            "reason": "short_strategy_model_not_validated",
            "validation_blocker": "SHORT_ONLY is not supported by the current causal signal engine.",
        }
    signal_mode = strategy_signal_input(strategy_id)
    signal_bars = [
        dict(row) for row in (bars or [])
        if isinstance(row, dict)
        and bool(row.get("complete", row.get("confirm", not bool(row.get("provisional")))))
    ]
    signal_closes = [float(value) for value in (closes or [])]
    if not signal_bars and symbol:
        payload = backtest_market_rows(symbol, 180)
        signal_bars = [
            dict(row) for row in payload.get("rows") or []
            if isinstance(row, dict)
            and bool(row.get("complete", row.get("confirm", not bool(row.get("provisional")))))
        ]
    if not signal_closes and signal_bars:
        signal_closes = [float(row.get("close") or 0.0) for row in signal_bars if float(row.get("close") or 0.0) > 0]
    history: list[Any] = signal_bars if signal_mode == "BARS" else signal_closes
    if not history:
        return {
            "action": "HOLD",
            "confidence": 0.0,
            "reason": "symbol_history_required",
            "validation_blocker": "Paper signals require completed candles for the armed symbol.",
        }
    strategy = choose_strategy(strategy_id)
    signal_price = float(signal_bars[-1].get("close") or price) if signal_mode == "BARS" else price
    raw = build_strategy_signal_fn(strategy_id, strategy.get("params") or {})(
        history,
        signal_price,
        position_qty > 0,
        entry_price,
        last_scale_price,
    )
    confidence = 0.7 if raw.get("action") in {"BUY", "EXIT", "SELL"} else 0.4
    return {"confidence": confidence, **raw}


PORTFOLIO_REGIME_CACHE: dict[str, dict[str, Any]] = {}


def portfolio_cluster_for_symbol(symbol: str) -> str:
    clean_symbol = str(symbol or "").upper()
    if is_stock_symbol(clean_symbol):
        try:
            return str(stock_meta(clean_symbol).get("sector") or "STOCK").upper()
        except Exception:
            return "STOCK"
    return "CRYPTO"


def runtime_portfolio_regime(symbol: str) -> dict[str, Any]:
    clean_symbol = str(symbol or "").upper()
    cached = PORTFOLIO_REGIME_CACHE.get(clean_symbol) or {}
    stamp = now_ms()
    if cached and stamp - int(cached.get("updated_at") or 0) < 300_000:
        return dict(cached.get("regime") or {})
    payload = backtest_market_rows(clean_symbol, 180)
    rows = [
        dict(row) for row in payload.get("rows") or []
        if isinstance(row, dict)
        and bool(row.get("complete", row.get("confirm", not bool(row.get("provisional")))))
    ]
    regime = classify_market_regime(
        rows,
        market="stock" if is_stock_symbol(clean_symbol) else "crypto",
    )
    PORTFOLIO_REGIME_CACHE[clean_symbol] = {"updated_at": stamp, "regime": regime}
    return regime


def runtime_portfolio_risk_context(
    risk: dict[str, Any],
    symbol: str,
    side: str,
    notional: float,
    price: float,
    context: dict[str, Any],
) -> dict[str, Any]:
    del price
    paper = risk.get("paper") if isinstance(risk.get("paper"), dict) else {}
    clean_symbol = str(symbol or "").upper()
    clean_side = str(side or "").upper()
    position_side = str(context.get("position_side") or paper.get("position_side") or "FLAT").upper()
    reduce_only = context.get("reduce_only") is True
    reduces_long = position_side == "LONG" and clean_side in {"SELL", "CLOSE"}
    reduces_short = position_side == "SHORT" and clean_side in {"BUY", "COVER", "CLOSE"}
    risk_increasing = not reduce_only and not reduces_long and not reduces_short and clean_side in {
        "BUY", "SELL", "SHORT", "ARM", "CONDITION",
    }
    proposed_direction = "SHORT" if clean_side in {"SELL", "SHORT"} and not reduces_long else "LONG"
    current_symbol = str(paper.get("symbol") or "").upper()
    current_notional = max(float(paper.get("position_value") or 0.0), 0.0)
    positions: list[dict[str, Any]] = []
    if current_symbol and current_notional > 0 and position_side in {"LONG", "SHORT"}:
        positions.append({
            "symbol": current_symbol,
            "notional": current_notional,
            "direction": position_side,
            "cluster": portfolio_cluster_for_symbol(current_symbol),
        })
    portfolio_paper = PORTFOLIO_PAPER_LEDGER.mark_to_market()
    portfolio_equity = float(paper.get("equity") or 0.0)
    if portfolio_paper.get("simulation_enabled") is True:
        portfolio_equity = float(portfolio_paper.get("equity") or 0.0)
        positions = [
            {
                "symbol": str(item.get("symbol") or "").upper(),
                "notional": float(item.get("market_value") or 0.0),
                "direction": "LONG",
                "cluster": portfolio_cluster_for_symbol(str(item.get("symbol") or "")),
            }
            for item in portfolio_paper.get("positions") or []
            if float(item.get("market_value") or 0.0) > 0
        ]

    correlation_matrix: dict[str, Any] = {}
    if positions and any(item["symbol"] != clean_symbol for item in positions):
        symbols = list(dict.fromkeys([clean_symbol, *[item["symbol"] for item in positions]]))
        payloads = {item: backtest_market_rows(item, 180) for item in symbols}
        correlation_matrix = build_correlation_matrix(payloads)

    automated = clean_side == "ARM" or str(context.get("source") or "").lower() == "strategy"
    regime = runtime_portfolio_regime(clean_symbol) if automated and risk_increasing and proposed_direction == "LONG" else {}
    result = evaluate_portfolio_risk(
        equity=portfolio_equity,
        positions=positions,
        proposed_symbol=clean_symbol,
        proposed_notional=float(notional or 0.0),
        proposed_direction=proposed_direction,
        proposed_cluster=portfolio_cluster_for_symbol(clean_symbol),
        risk_increasing=risk_increasing,
        correlations=correlation_matrix,
        regime=regime,
    )
    result["correlation_matrix_hash"] = str(correlation_matrix.get("matrix_hash") or "")
    result["market_regime_hash"] = str(regime.get("regime_hash") or "")
    result["automated_regime_budget_applied"] = bool(regime)
    result["portfolio_paper_account"] = {
        "status": portfolio_paper.get("status"),
        "simulation_enabled": portfolio_paper.get("simulation_enabled") is True,
        "position_count": int(portfolio_paper.get("position_count") or 0),
        "version": int(portfolio_paper.get("version") or 0),
    }
    return result


RISK_SERVICE = RiskService(
    snapshot_provider=lambda price: risk_policy_snapshot(price),
    now_ms=now_ms,
    audit_writer=record_runtime_audit,
    data_context_provider=lambda symbol, price, context: MARKET_DATA_SERVICE.execution_context(symbol, price, context),
    portfolio_context_provider=runtime_portfolio_risk_context,
)
EVENT_BUS.publish("runtime_ready", {"service": "exchange_terminal", "paper_symbol": PAPER_ACCOUNT.symbol}, source="server")

CLIENT_DISCONNECT_ERRORS = (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)


LOCAL_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost", "::ffff:127.0.0.1"})


def allowed_cors_origin(handler: BaseHTTPRequestHandler) -> str:
    return allowed_web_origin(handler.headers.get("Origin"))


def is_loopback_host(host: str) -> bool:
    clean = str(host or "").strip()
    if clean.lower() in LOCAL_LOOPBACK_HOSTS:
        return True
    try:
        return ipaddress.ip_address(clean).is_loopback
    except ValueError:
        return False


def block_non_loopback_client(handler: BaseHTTPRequestHandler) -> bool:
    client_host = str(getattr(handler, "client_address", [""])[0] or "").strip()
    if is_loopback_host(client_host):
        return False
    handler.send_response(403)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(json.dumps({
        "ok": False,
        "error": "local requests only",
        "live_order_allowed": False,
    }, ensure_ascii=False).encode("utf-8"))
    return True


_json_guard = threading.Lock()


def json_response(handler: BaseHTTPRequestHandler, payload: dict[str, Any], status: int = 200) -> None:
    mutation_key = str(getattr(handler, "_mutation_idempotency_key", "") or "")
    if mutation_key:
        if status < 500:
            MUTATION_JOURNAL.complete(mutation_key, status, payload)
        else:
            MUTATION_JOURNAL.abandon(mutation_key)
        setattr(handler, "_mutation_idempotency_key", "")
    body = json.dumps(clean_json_value(payload), ensure_ascii=False).encode("utf-8")
    try:
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Cache-Control", "no-store")
        handler.send_header("X-Content-Type-Options", "nosniff")
        handler.send_header("X-Frame-Options", "DENY")
        handler.send_header("Referrer-Policy", "no-referrer")
        handler.send_header("Cross-Origin-Opener-Policy", "same-origin")
        cors_origin = allowed_cors_origin(handler)
        if cors_origin:
            handler.send_header("Access-Control-Allow-Origin", cors_origin)
            handler.send_header("Vary", "Origin")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)
    except CLIENT_DISCONNECT_ERRORS:
        handler.close_connection = True


def read_bodyless_okx(path: str, query: dict[str, str]) -> dict[str, Any]:
    return read_bodyless_okx_io(path, query)


def okx_private_env_names() -> dict[str, str]:
    saved = read_json(API_CONFIG_FILE, {})
    return {
        "api_key_env": saved.get("api_key_env", "OKX_API_KEY"),
        "secret_env": saved.get("secret_env", "OKX_SECRET"),
        "password_env": saved.get("password_env", "OKX_PASSWORD"),
    }


def okx_private_credentials() -> tuple[dict[str, str], dict[str, str], list[str]]:
    names = okx_private_env_names()
    credentials = {
        "api_key": os.getenv(names["api_key_env"], ""),
        "secret": os.getenv(names["secret_env"], ""),
        "password": os.getenv(names["password_env"], ""),
    }
    missing = [label for label, value in credentials.items() if not value]
    return names, credentials, missing


def read_signed_okx(path: str, query: dict[str, str] | None = None) -> dict[str, Any]:
    _, credentials, missing = okx_private_credentials()
    if missing:
        raise RuntimeError(f"missing OKX private env: {', '.join(missing)}")
    encoded_query = urllib.parse.urlencode(query or {})
    request_path = f"{path}?{encoded_query}" if encoded_query else path
    timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    message = f"{timestamp}GET{request_path}"
    signature = base64.b64encode(
        hmac.new(credentials["secret"].encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
    ).decode("utf-8")
    request = urllib.request.Request(
        f"{OKX_BASE_URL}{request_path}",
        headers={
            "User-Agent": "Python-Quant-Exchange-Terminal/0.1",
            "OK-ACCESS-KEY": credentials["api_key"],
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": credentials["password"],
        },
    )
    with urllib.request.urlopen(request, timeout=OKX_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def okx_private_read_status() -> dict[str, Any]:
    names, credentials, missing = okx_private_credentials()
    env_status = {key: bool(value) for key, value in credentials.items()}
    if missing:
        return {
            "ok": False,
            "configured": False,
            "status": "MISSING",
            "env_status": env_status,
            "env_names": names,
            "message": "缺少 OKX 私有读取所需字段：api_key / secret / password(passphrase) 必须齐全。",
        }
    try:
        payload = read_signed_okx("/api/v5/account/config")
        code = str(payload.get("code", ""))
        success = code == "0"
        rows = payload.get("data") if isinstance(payload.get("data"), list) else []
        account = rows[0] if rows else {}
        return {
            "ok": success,
            "configured": True,
            "status": "READY" if success else "ERROR",
            "env_status": env_status,
            "env_names": names,
            "message": "OKX 只读私有接口已连通。" if success else payload.get("msg", "OKX 私有读取认证失败。"),
            "account": {
                "uid": mask_secret_text(str(account.get("uid", ""))) if account.get("uid") else "",
                "main_uid": mask_secret_text(str(account.get("mainUid", ""))) if account.get("mainUid") else "",
                "acct_lv": account.get("acctLv", ""),
                "pos_mode": account.get("posMode", ""),
            },
        }
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")[:500]
        return {
            "ok": False,
            "configured": True,
            "status": "ERROR",
            "env_status": env_status,
            "env_names": names,
            "message": f"OKX 私有读取认证失败：HTTP {exc.code}",
            "detail": detail,
        }
    except Exception as exc:
        return {
            "ok": False,
            "configured": True,
            "status": "ERROR",
            "env_status": env_status,
            "env_names": names,
            "message": f"OKX 私有读取检查失败：{exc}",
        }


def crypto_spot_symbol(base: str) -> str:
    return f"{base}-USDT"


def crypto_swap_symbol(base: str) -> str:
    return f"{base}-USDT-SWAP"


def normalize_crypto_spot(symbol: str) -> str:
    text = (symbol or "BTC-USDT").upper()
    if text.endswith("-SWAP"):
        return text.replace("-SWAP", "")
    return text


def market_universe() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for base in CORE_CRYPTO_BASES:
        rows.append({
            "symbol": crypto_spot_symbol(base),
            "instId": crypto_spot_symbol(base),
            "name": {"BTC": "Bitcoin", "ETH": "Ethereum", "DOGE": "Dogecoin"}.get(base, base),
            "quote": "USDT",
            "type": "spot",
            "category": "spot",
            "source": "okx",
            "tradable": True,
        })
    for base in CORE_CRYPTO_BASES:
        rows.append({
            "symbol": crypto_swap_symbol(base),
            "instId": crypto_swap_symbol(base),
            "name": f"{base} Perpetual",
            "quote": "USDT",
            "type": "swap",
            "category": "swap",
            "source": "okx",
            "tradable": True,
        })
    for stock in STOCK_MARKETS:
        rows.append({
            "symbol": stock["symbol"],
            "instId": stock.get("futu", stock["symbol"]),
            "name": stock["name"],
            "quote": stock.get("quote", "USD"),
            "type": "stock",
            "category": "stocks",
            "source": "futu",
            "exchange": stock["exchange"],
            "market": stock.get("market", "US"),
            "futu": stock.get("futu", stock["symbol"]),
            "yahoo": stock.get("yahoo", stock["symbol"]),
            "sector": stock["sector"],
            "tradable": False,
        })
    return rows


def mask_secret_text(value: str) -> str:
    text = str(value or "")
    if len(text) <= 4:
        return "*" * len(text)
    return f"{text[:2]}{'*' * max(3, len(text) - 4)}{text[-2:]}"


def set_xml_child_text(root: ET.Element, tag: str, value: str, after_tag: str | None = None) -> None:
    node = root.find(tag)
    if node is None:
        node = ET.Element(tag)
        if after_tag:
            children = list(root)
            insert_at = next((index + 1 for index, child in enumerate(children) if child.tag == after_tag), len(children))
            root.insert(insert_at, node)
        else:
            root.append(node)
    node.text = value


def configure_futu_opend_credentials(account: str, password: str) -> dict[str, Any]:
    clean_account = str(account or "").strip()
    clean_password = str(password or "")
    if not clean_account:
        return {"ok": False, "error": "请输入富途账号"}
    if not clean_password:
        return {"ok": False, "error": "请输入富途密码"}
    if not FUTU_OPEND_XML.exists():
        return {"ok": False, "error": f"找不到 FutuOpenD.xml: {FUTU_OPEND_XML}"}

    backup = FUTU_OPEND_XML.with_name(f"{FUTU_OPEND_XML.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copyfile(FUTU_OPEND_XML, backup)
    tree = ET.parse(FUTU_OPEND_XML)
    root = tree.getroot()
    if root.tag != "futu_opend":
        return {"ok": False, "error": "FutuOpenD.xml 格式不正确"}

    password_md5 = hashlib.md5(clean_password.encode("utf-8")).hexdigest()
    set_xml_child_text(root, "login_account", clean_account)
    set_xml_child_text(root, "login_pwd_md5", password_md5, "login_account")
    set_xml_child_text(root, "login_pwd", "")
    set_xml_child_text(root, "telnet_ip", FUTU_TELNET_HOST)
    set_xml_child_text(root, "telnet_port", str(FUTU_TELNET_PORT), "telnet_ip")
    tree.write(FUTU_OPEND_XML, encoding="utf-8", xml_declaration=False)

    reset_futu_status_cache("credentials updated")
    return {
        "ok": True,
        "account": mask_secret_text(clean_account),
        "target": str(FUTU_OPEND_XML),
        "backup": str(backup),
        "message": "富途 OpenD 登录配置已写入，密码已转为 MD5。",
    }


def ensure_futu_telnet_config() -> dict[str, Any]:
    if not FUTU_OPEND_XML.exists():
        return {"ok": False, "error": f"找不到 FutuOpenD.xml: {FUTU_OPEND_XML}"}
    backup = FUTU_OPEND_XML.with_name(f"{FUTU_OPEND_XML.name}.telnet-bak-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copyfile(FUTU_OPEND_XML, backup)
    tree = ET.parse(FUTU_OPEND_XML)
    root = tree.getroot()
    if root.tag != "futu_opend":
        return {"ok": False, "error": "FutuOpenD.xml 格式不正确"}
    set_xml_child_text(root, "telnet_ip", FUTU_TELNET_HOST)
    set_xml_child_text(root, "telnet_port", str(FUTU_TELNET_PORT), "telnet_ip")
    tree.write(FUTU_OPEND_XML, encoding="utf-8", xml_declaration=False)
    return {"ok": True, "host": FUTU_TELNET_HOST, "port": FUTU_TELNET_PORT, "backup": str(backup)}


def submit_futu_phone_verify_code(code: str) -> dict[str, Any]:
    clean_code = "".join(ch for ch in str(code or "") if ch.isdigit())
    if len(clean_code) < 4 or len(clean_code) > 8:
        return {"ok": False, "error": "请输入 4-8 位数字验证码"}
    command = f"input_phone_verify_code -code={clean_code}\n"
    try:
        with socket.create_connection((FUTU_TELNET_HOST, FUTU_TELNET_PORT), timeout=4) as sock:
            sock.settimeout(2)
            try:
                _ = sock.recv(4096)
            except Exception:
                pass
            sock.sendall(command.encode("utf-8"))
            chunks: list[bytes] = []
            deadline = time.time() + 3
            while time.time() < deadline:
                try:
                    chunk = sock.recv(4096)
                except Exception:
                    break
                if not chunk:
                    break
                chunks.append(chunk)
            response = b"".join(chunks).decode("utf-8", errors="ignore")
    except Exception as exc:
        return {"ok": False, "error": f"验证码提交失败：{exc}", "host": FUTU_TELNET_HOST, "port": FUTU_TELNET_PORT}
    reset_futu_status_cache("phone verify code submitted")
    return {
        "ok": True,
        "message": "验证码已提交到本机 FutuOpenD。",
        "host": FUTU_TELNET_HOST,
        "port": FUTU_TELNET_PORT,
        "response": response[-800:],
    }


def stock_seed_quote(symbol: str) -> dict[str, Any]:
    meta = stock_meta(symbol)
    seed = float(STOCK_SEED_PRICES.get(meta["symbol"], 100.0))
    volume = float(STOCK_SEED_VOLUMES.get(meta["symbol"], 8_000_000))
    quote = {
        "symbol": meta["symbol"],
        "instId": meta.get("futu", meta["symbol"]),
        "name": meta["name"],
        "quote": meta.get("quote", "USD"),
        "type": "stock",
        "category": "stocks",
        "source": "offline-seed",
        "exchange": meta.get("exchange", "US"),
        "market": meta.get("market", "US"),
        "sector": meta.get("sector", "Stock"),
        "status": "OFFLINE",
        "last": seed,
        "open24h": round(seed * 0.996, 4),
        "high24h": round(seed * 1.012, 4),
        "low24h": round(seed * 0.988, 4),
        "vol24h": volume,
        "volCcy24h": volume * seed,
        "bidPx": 0.0,
        "askPx": 0.0,
        "change24h_pct": 0.4,
        "ts": now_ms(),
        "date": "",
        "time": "",
        "futu_code": meta.get("futu", meta["symbol"]),
        "warning": "offline seed, not live market data",
    }
    return normalize_stock_quote_quality(
        quote,
        previous_close=quote["open24h"],
        change_basis="synthetic",
        provider_change=quote["change24h_pct"],
        now_ms=now_ms(),
    )


def stock_seed_candles(symbol: str, limit: int = 120, interval: str = "1d", session: str = "all", base_price: float | None = None) -> dict[str, Any]:
    meta = stock_meta(symbol)
    quote_seed = pct(base_price, 0.0) if base_price is not None else 0.0
    seed = quote_seed if quote_seed > 0 else float(STOCK_SEED_PRICES.get(meta["symbol"], 100.0))
    seed_source = "quote_preview_seed" if quote_seed > 0 else "offline-seed"
    volume_base = float(STOCK_SEED_VOLUMES.get(meta["symbol"], 8_000_000))
    clean_session = session if session in {"all", "pre", "regular", "post", "overnight"} else "all"
    normalized_interval, _ = normalize_stock_interval(interval)
    step_ms = {
        "1m": 60_000,
        "5m": 5 * 60_000,
        "15m": 15 * 60_000,
        "30m": 30 * 60_000,
        "60m": 60 * 60_000,
        "4h": 4 * 60 * 60_000,
        "1d": 24 * 60 * 60_000,
        "1dutc": 24 * 60 * 60_000,
    }.get(normalized_interval, 24 * 60 * 60_000)
    rows = []
    max_count = 520 if normalized_interval in {"1d", "1dutc"} else 420
    count = max(30, min(int(limit), max_count))
    if normalized_interval in {"1d", "1dutc"}:
        end_day = datetime.now(stock_timezone(meta["symbol"])).date()
        days = []
        cursor = end_day
        while len(days) < count:
            if cursor.weekday() < 5:
                days.append(cursor)
            cursor -= timedelta(days=1)
        timestamps = [
            int(datetime(day.year, day.month, day.day, tzinfo=stock_timezone(meta["symbol"])).timestamp() * 1000)
            for day in reversed(days)
        ]
    else:
        end = now_ms() // step_ms * step_ms
        timestamps = [end - (count - index - 1) * step_ms for index in range(count)]
    for index, ts in enumerate(timestamps):
        phase = index / max(count - 1, 1)
        drift = (phase - 0.5) * 0.065
        wave = math.sin(phase * math.pi * 5.5) * 0.018 + math.cos(phase * math.pi * 17) * 0.006
        pulse = math.sin(phase * math.pi * 13) * 0.004
        close = seed * (1 + drift + wave)
        open_price = seed * (1 + drift + wave - pulse)
        high = max(open_price, close) * (1.0045 + abs(math.sin(index * 1.7)) * 0.004)
        low = min(open_price, close) * (0.9955 - abs(math.cos(index * 1.3)) * 0.003)
        volume = volume_base * (0.72 + abs(math.sin(index * 0.83)) * 0.75 + (0.18 if abs(close - open_price) / max(seed, 1e-9) > 0.01 else 0))
        rows.append({
            "ts": ts,
            "date": time.strftime("%Y-%m-%d", time.gmtime(ts / 1000)),
            "open": round(open_price, 4),
            "high": round(high, 4),
            "low": round(low, 4),
            "close": round(close, 4),
            "volume": round(volume, 2),
            "source": seed_source,
            "session": "regular" if normalized_interval in {"1d", "1dutc"} else stock_session_from_ts(ts, meta["symbol"]),
        })
    rows = filter_stock_rows_by_session(rows, clean_session)
    if quote_seed > 0 and rows:
        last_close = pct(rows[-1].get("close", 0.0), 0.0)
        if last_close > 0:
            factor = quote_seed / last_close
            for row in rows:
                row["open"] = round(pct(row.get("open", 0.0), 0.0) * factor, 4)
                row["high"] = round(pct(row.get("high", 0.0), 0.0) * factor, 4)
                row["low"] = round(pct(row.get("low", 0.0), 0.0) * factor, 4)
                row["close"] = round(pct(row.get("close", 0.0), 0.0) * factor, 4)
            rows[-1]["close"] = round(quote_seed, 4)
            rows[-1]["high"] = max(pct(rows[-1].get("high", quote_seed), quote_seed), round(quote_seed, 4))
            rows[-1]["low"] = min(pct(rows[-1].get("low", quote_seed), quote_seed), round(quote_seed, 4))
    return {
        "ok": True,
        "symbol": meta["symbol"],
        "source": seed_source,
        "interval": normalized_interval,
        "session": clean_session,
        "session_label": stock_session_label(clean_session),
        "session_counts": {"pre": 0, "regular": len(rows), "post": 0, "overnight": 0},
        "rows": rows[-limit:],
        "updated_at": now_ms(),
        "warning": "quote driven preview candles, not live market data" if quote_seed > 0 else "offline seed, not live market data",
    }


def read_futu_quotes(symbols: list[str]) -> dict[str, dict[str, Any]]:
    rows = read_futu_quotes_io(symbols)
    if rows:
        stamp = now_ms()
        for symbol, quote in rows.items():
            normalized = normalize_stock_quote_quality(
                quote,
                previous_close=quote.get("prevClose"),
                change_basis="previous_close" if pct(quote.get("prevClose", 0)) > 0 else "provider",
                provider_change=quote.get("change24h_pct"),
                now_ms=stamp,
            )
            normalized = with_stock_session_contract(
                normalized,
                symbol,
                market_state=str(quote.get("market_state") or ""),
                now_ms_value=stamp,
            )
            rows[symbol] = normalized
            STOCK_SINGLE_QUOTE_CACHE[symbol] = {"time": stamp, "quote": normalized}
    return rows


def read_futu_stock_candles(
    symbol: str,
    limit: int = 260,
    interval: str = "1d",
    session: str = "all",
    *,
    include_snapshot: bool = True,
) -> dict[str, Any]:
    return read_futu_stock_candles_io(
        symbol,
        limit,
        interval,
        session,
        quote_reader=(lambda text: read_stock_quote(text, max_age_ms=1500, use_futu=True)) if include_snapshot else None,
    )


def cache_stock_quote(symbol: str, quote: dict[str, Any]) -> dict[str, Any]:
    key = stock_meta(symbol)["symbol"]
    stamp = now_ms()
    normalized = with_stock_session_contract(
        quote,
        key,
        market_state=str(quote.get("market_state") or ""),
        now_ms_value=stamp,
    )
    STOCK_SINGLE_QUOTE_CACHE[key] = {"time": stamp, "quote": normalized}
    return normalized


def normalize_stock_history_session(interval: str, session: str) -> str:
    clean_session = session if session in {"all", "pre", "regular", "post", "overnight"} else "all"
    if stock_cache_interval(interval) in {"1d", "1dutc"} and clean_session == "all":
        return "regular"
    return clean_session


def cache_stock_candles(symbol: str, interval: str, session: str, payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("rows") or []
    if not rows or payload.get("source") in {"offline-seed", "stock_sqlite_cache"}:
        return with_stock_freshness(payload, interval, symbol)
    stale_warning = stock_candle_stale_warning(list(rows), interval, symbol)
    if stale_warning:
        return with_stock_freshness({**payload, "warning": stale_warning}, interval, symbol)
    clean_session = normalize_stock_history_session(interval, session)
    persistent_cache_writable = not RUNTIME_READ_ONLY
    payload = enrich_stock_series_contract(
        payload,
        symbol,
        interval,
        clean_session,
        persist=persistent_cache_writable,
    )
    source_name = str(payload.get("cache_source") or payload.get("source") or "stock")
    provider_rows = list(payload.get("rows") or [])
    if persistent_cache_writable and stock_cache_interval(interval) in {"1d", "1dutc"}:
        try:
            provider_revision = record_stock_revision_snapshot(
                symbol=symbol,
                provider=source_name,
                rows=provider_rows,
                interval=interval,
                session=clean_session,
                adjustment_basis=str(payload.get("adjustment_basis") or ""),
                corporate_actions_hash=str(
                    (payload.get("adjustment_evidence") or {}).get("corporate_actions_hash") or ""
                ),
                observation_scope=str(payload.get("provider_observation_scope") or "QUERY_WINDOW"),
            )
            payload["provider_revision_evidence"] = provider_revision
        except Exception as exc:
            payload["provider_revision_warning"] = str(exc)
    try:
        cache_preparation = prepare_stock_candle_cache_rows(
            symbol,
            interval,
            clean_session,
            provider_rows,
            source_name,
        )
        cache_rows = list(cache_preparation.get("rows") or [])
    except ValueError as exc:
        if not persistent_cache_writable:
            return with_stock_freshness({
                **payload,
                "warning": f"daily cache preparation rejected: {exc}",
                "cache_write_blocked": True,
                "cache_persistence": "READ_ONLY_SKIPPED",
                "read_only": True,
            }, interval, symbol)
        cached = read_stock_persistent_candle_cache(symbol, len(rows), interval, clean_session)
        if cached:
            return with_stock_freshness({
                **cached,
                "warning": f"daily refresh rejected: {exc}",
                "refresh_rejected": True,
            }, interval, symbol)
        return with_stock_freshness({
            **payload,
            "warning": f"daily cache write rejected: {exc}",
            "cache_write_blocked": True,
        }, interval, symbol)
    stored_payload = {
        **payload,
        "rows": cache_rows,
        "cache_vintage": {key: value for key, value in cache_preparation.items() if key != "rows"},
    }
    stamp = now_ms()
    if persistent_cache_writable:
        try:
            saved = upsert_stock_candle_cache(
                symbol,
                interval,
                clean_session,
                cache_rows,
                source_name,
                prepared=True,
            )
            if saved:
                stored_payload["persistent_cache_saved"] = saved
        except Exception as exc:
            stored_payload["cache_warning"] = str(exc)
    else:
        stored_payload["persistent_cache_saved"] = 0
        stored_payload["cache_persistence"] = "READ_ONLY_SKIPPED"
        stored_payload["read_only"] = True
    if persistent_cache_writable and stock_cache_interval(interval) in {"1d", "1dutc"}:
        try:
            revision_evidence = attest_stock_candle_cache(symbol, interval, clean_session)
            if revision_evidence:
                stored_payload["data_revision_evidence"] = revision_evidence
                if revision_evidence.get("status") == "BLOCK":
                    stored_payload["warning"] = "daily cache revision blocked pending review"
        except Exception as exc:
            stored_payload["data_revision_warning"] = str(exc)
    key = stock_candle_cache_key(symbol, interval, clean_session)
    STOCK_CANDLE_CACHE[key] = {
        "time": stamp,
        "payload": stored_payload,
    }
    if clean_session == "all" and stock_cache_interval(interval) not in {"1d", "1dutc"}:
        partitions: dict[str, int] = {}
        for partition_session in ("pre", "regular", "post", "overnight"):
            partition_rows = filter_stock_rows_by_session(list(rows), partition_session)
            if not partition_rows or stock_candle_stale_warning(partition_rows, interval, symbol):
                continue
            partition_payload = {
                **payload,
                "rows": partition_rows,
                "session": partition_session,
                "session_label": stock_session_label(partition_session),
                "session_counts": {partition_session: len(partition_rows)},
                "derived_from_session": "all",
            }
            if persistent_cache_writable:
                try:
                    partition_payload["persistent_cache_saved"] = upsert_stock_candle_cache(
                        symbol,
                        interval,
                        partition_session,
                        partition_rows,
                        source_name,
                    )
                except Exception as exc:
                    partition_payload["cache_warning"] = str(exc)
            else:
                partition_payload["persistent_cache_saved"] = 0
                partition_payload["cache_persistence"] = "READ_ONLY_SKIPPED"
                partition_payload["read_only"] = True
            STOCK_CANDLE_CACHE[stock_candle_cache_key(symbol, interval, partition_session)] = {
                "time": stamp,
                "payload": partition_payload,
            }
            partitions[partition_session] = len(partition_rows)
        if partitions:
            stored_payload["session_cache_partitions"] = partitions
    return with_stock_freshness(stored_payload, interval, symbol)


def read_stock_candle_cache(symbol: str, limit: int, interval: str, session: str, max_age_ms: int | None = None) -> dict[str, Any] | None:
    if max_age_ms is None:
        max_age_ms = stock_cache_fresh_ms(interval)
    clean_session = normalize_stock_history_session(interval, session)
    key = stock_candle_cache_key(symbol, interval, clean_session)
    cached = STOCK_CANDLE_CACHE.get(key) or {}
    stamp = int(cached.get("time") or 0)
    payload = cached.get("payload")
    if (not isinstance(payload, dict) or now_ms() - stamp > max_age_ms) and clean_session != "all":
        shared = STOCK_CANDLE_CACHE.get(stock_candle_cache_key(symbol, interval, "all")) or {}
        shared_stamp = int(shared.get("time") or 0)
        shared_payload = shared.get("payload")
        shared_rows = filter_stock_rows_by_session(list((shared_payload or {}).get("rows") or []), clean_session) if isinstance(shared_payload, dict) else []
        if (
            isinstance(shared_payload, dict)
            and now_ms() - shared_stamp <= max_age_ms
            and shared_rows
            and not stock_candle_stale_warning(shared_rows, interval, symbol)
        ):
            stamp = shared_stamp
            payload = {
                **shared_payload,
                "rows": shared_rows,
                "session": clean_session,
                "session_label": stock_session_label(clean_session),
                "session_counts": {clean_session: len(shared_rows)},
                "derived_from_session": "all",
            }
    if not isinstance(payload, dict) or now_ms() - stamp > max_age_ms:
        return None
    rows = list(payload.get("rows") or [])[-limit:]
    if not rows:
        return None
    if stock_candle_stale_warning(rows, interval, symbol):
        return None
    payload = with_stock_freshness({
        **payload,
        "rows": rows,
        "cached": True,
        "cache_age_ms": now_ms() - stamp,
        "updated_at": payload.get("updated_at") or stamp,
    }, interval, symbol)
    if stock_payload_needs_session_refresh(payload, interval, symbol):
        return None
    return payload


def stock_data_sources_snapshot(symbol: str = "AAPL", interval: str = "1d", session: str = "all", force: bool = False) -> dict[str, Any]:
    meta = stock_meta(symbol)
    clean_session = normalize_stock_history_session(interval, session)
    key = stock_candle_cache_key(meta["symbol"], interval, clean_session)
    memory_cached = STOCK_CANDLE_CACHE.get(key) or {}
    memory_payload = memory_cached.get("payload") if isinstance(memory_cached, dict) else {}
    memory_age = now_ms() - int(memory_cached.get("time") or 0) if memory_cached else None
    persistent = read_stock_persistent_candle_cache(meta["symbol"], 1, interval, clean_session)
    provider_order = stock_external_provider_order()
    futu = futu_status_snapshot(force)
    coverage = stock_candle_cache_coverage(meta["symbol"], interval, clean_session)
    health = provider_health_snapshot(["futu", "yahoo", "stooq"])
    health_providers = health.get("providers") or {}
    health_interval, _ = normalize_stock_interval(interval)
    health_scope = f"{meta['symbol']}|{health_interval}|{clean_session}".upper()
    scoped_health = {
        provider: provider_health_for_scope(health, provider, "history", health_scope)
        for provider in ["futu", "yahoo", "stooq"]
    }
    prewarm = STOCK_HISTORY_PREWARM_SERVICE.status(meta["symbol"]) if STOCK_HISTORY_PREWARM_SERVICE else {"ok": True, "jobs": [], "counts": {}}
    cache_source = persistent.get("origin_source") if persistent else None
    cache_age = persistent.get("cache_age_ms") if persistent else None
    summary_parts = []
    summary_parts.append("Futu在线" if futu.get("opend_online") else "Futu离线")
    summary_parts.append("本地K线库可用" if persistent else "本地K线库为空")
    if persistent and persistent.get("warning"):
        summary_parts.append("本地K线为旧缓存")
    if coverage.get("available"):
        summary_parts.append(f"覆盖 {coverage.get('row_count', 0)} 根 / {coverage.get('first_date') or '--'} 至 {coverage.get('latest_date') or '--'}")
    summary_parts.append("外部源 " + "/".join(provider_order))
    return {
        "ok": True,
        "symbol": meta["symbol"],
        "interval": stock_cache_interval(interval),
        "session": clean_session,
        "session_label": stock_session_label(clean_session),
        "mode": "market_research_only",
        "live_trading_hard_block": LIVE_TRADING_HARD_BLOCK,
        "forced": bool(force),
        "order": ["futu", "stock_sqlite_cache", *provider_order, "offline-seed"],
        "summary": " / ".join(summary_parts),
        "futu": {
            "opend_online": bool(futu.get("opend_online")),
            "sdk_installed": bool(futu.get("sdk_installed")),
            "host": futu.get("host"),
            "port": futu.get("port"),
            "message": futu.get("message"),
            "health": scoped_health["futu"] if scoped_health["futu"].get("calls") else health_providers.get("futu") or {},
        },
        "cache": {
            "memory": bool(memory_payload),
            "memory_source": (memory_payload or {}).get("source") if isinstance(memory_payload, dict) else None,
            "memory_age_ms": memory_age,
            "persistent": bool(persistent),
            "persistent_source": cache_source,
            "persistent_age_ms": cache_age,
            "persistent_data_age_ms": persistent.get("data_age_ms") if persistent else None,
            "persistent_latest_at": persistent.get("latest_at") if persistent else None,
            "persistent_warning": persistent.get("warning") if persistent else "",
            "persistent_fresh": bool(persistent and not persistent.get("warning")),
            "path": str(STOCK_CANDLE_CACHE_DB),
            "coverage": coverage,
        },
        "providers": [
            {
                "id": provider,
                "enabled": provider in provider_order and bool(ALLOW_STOCK_FALLBACK or ALLOW_STOCK_HISTORY_FALLBACK),
                "timeout_sec": STOCK_HISTORY_TIMEOUT,
                "health": scoped_health[provider],
            }
            for provider in ["yahoo", "stooq"]
        ],
        "provider_health": health,
        "provider_health_scope": {
            "scope": health_scope,
            "operation": "history",
            "providers": scoped_health,
        },
        "history_prewarm": prewarm,
    }


def read_stock_quote(symbol: str, max_age_ms: int = 4500, use_futu: bool = True) -> dict[str, Any]:
    text = str(symbol or "AAPL").strip().upper() or "AAPL"
    meta = stock_meta(text)
    cache_key = meta["symbol"]
    cached = STOCK_SINGLE_QUOTE_CACHE.get(cache_key) or {}

    def forced_last_good(reason: str) -> dict[str, Any] | None:
        previous = cached.get("quote")
        if max_age_ms > 0 or not isinstance(previous, dict):
            return None
        source = str(previous.get("source") or previous.get("origin_source") or "").strip().lower()
        status = str(previous.get("status") or "").strip().upper()
        if pct(previous.get("last", 0)) <= 0 or source in {"offline", "offline-seed"} or status in {"OFFLINE", "ERROR", "UNAVAILABLE"}:
            return None
        warning = str(reason or "forced stock quote refresh failed; using last known good").strip()
        quote_quality = dict(previous.get("quote_quality") or {})
        quote_quality["status"] = "DEGRADED"
        quote_quality["fallback"] = True
        quote_quality["warnings"] = list(dict.fromkeys([
            *list(quote_quality.get("warnings") or []),
            warning,
        ]))
        return {
            **dict(previous),
            "status": "STALE",
            "fallback": True,
            "forced": True,
            "refresh_failed": True,
            "warning": warning,
            "quote_quality": quote_quality,
        }

    if now_ms() - int(cached.get("time") or 0) < max_age_ms and isinstance(cached.get("quote"), dict):
        return dict(cached["quote"])
    if use_futu:
        futu_rows = read_futu_quotes([text])
        if futu_rows.get(meta["symbol"]):
            return cache_stock_quote(text, futu_rows[meta["symbol"]])
    if not (ALLOW_STOCK_FALLBACK or ALLOW_STOCK_HISTORY_FALLBACK):
        last_good = forced_last_good("forced stock quote refresh unavailable; using last known good")
        if last_good:
            return last_good
        return cache_stock_quote(text, stock_seed_quote(text))
    url = "https://stooq.com/q/l/?" + urllib.parse.urlencode({
        "s": stock_source_symbol(text),
        "f": "sd2t2ohlcv",
        "h": "",
        "e": "csv",
    })
    row: dict[str, Any] = {}
    quote_scope = meta["symbol"]
    stooq_error = ""
    stooq_allowed, _stooq_retry_after_ms = provider_call_allowed("stooq", "quote", quote_scope)
    stooq_started = time.perf_counter()
    if stooq_allowed:
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Python-Quant-Exchange-Terminal/0.1"})
            with urllib.request.urlopen(request, timeout=STOCK_QUOTE_TIMEOUT) as response:
                content = response.read().decode("utf-8", errors="ignore")
            reader = csv.DictReader(io.StringIO(content))
            row = next(reader, {}) or {}
        except Exception as exc:
            stooq_error = str(exc)
            row = {}
    close = pct(row.get("Close", "0"))
    open_price = pct(row.get("Open", "0"))
    high = pct(row.get("High", "0"))
    low = pct(row.get("Low", "0"))
    volume = pct(row.get("Volume", "0"))
    source = "stooq"
    previous_close = 0.0
    change_basis = ""
    provider_change: float | None = None
    quote_ts = now_ms()
    quote_date = str(row.get("Date") or "")
    quote_time = str(row.get("Time") or "")
    if stooq_allowed:
        record_provider_call(
            "stooq",
            "quote",
            success=close > 0,
            latency_ms=(time.perf_counter() - stooq_started) * 1000,
            error=stooq_error or ("quote returned no price" if close <= 0 else ""),
            scope=quote_scope,
        )
    if quote_date:
        try:
            quote_dt = datetime.strptime(f"{quote_date} {quote_time or '16:00:00'}", "%Y-%m-%d %H:%M:%S")
            quote_ts = int(quote_dt.replace(tzinfo=stock_timezone(text)).timestamp() * 1000)
        except ValueError:
            pass
    if close > 0:
        daily_cache = read_stock_persistent_candle_cache(text, 3, "1d", "all")
        daily_rows = list((daily_cache or {}).get("rows") or [])
        if daily_rows:
            latest_date = str(daily_rows[-1].get("date") or "")
            previous_row = daily_rows[-2] if quote_date and latest_date == quote_date and len(daily_rows) >= 2 else daily_rows[-1]
            previous_close = pct(previous_row.get("close", 0.0))
            change_basis = "local_previous_close" if previous_close > 0 else ""
    if close <= 0:
        yahoo_error = ""
        yahoo_allowed, _yahoo_retry_after_ms = provider_call_allowed("yahoo", "quote", quote_scope)
        yahoo_started = time.perf_counter()
        try:
            if not yahoo_allowed:
                raise RuntimeError("provider cooldown")
            yahoo_url = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(yahoo_stock_symbol(text)) + "?" + urllib.parse.urlencode({"range": "5d", "interval": "1d"})
            request = urllib.request.Request(yahoo_url, headers={"User-Agent": "Mozilla/5.0 HakimiTrade/2.0"})
            with urllib.request.urlopen(request, timeout=STOCK_QUOTE_TIMEOUT) as response:
                payload = json.loads(response.read().decode("utf-8", errors="ignore"))
            result = ((payload.get("chart") or {}).get("result") or [{}])[0]
            yahoo_meta = result.get("meta") or {}
            quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
            closes = [item for item in (quote.get("close") or []) if item is not None]
            opens = [item for item in (quote.get("open") or []) if item is not None]
            highs = [item for item in (quote.get("high") or []) if item is not None]
            lows = [item for item in (quote.get("low") or []) if item is not None]
            volumes = [item for item in (quote.get("volume") or []) if item is not None]
            close = pct(yahoo_meta.get("regularMarketPrice", 0)) or (float(closes[-1]) if closes else 0.0)
            previous_close = pct(yahoo_meta.get("previousClose", yahoo_meta.get("chartPreviousClose", 0)))
            open_price = float(opens[-1]) if opens else previous_close
            high = float(highs[-1]) if highs else close
            low = float(lows[-1]) if lows else close
            volume = float(volumes[-1]) if volumes else 0.0
            source = "yahoo"
            change_basis = "previous_close" if previous_close > 0 else ""
            provider_change = yahoo_meta.get("regularMarketChangePercent")
            market_time = int(pct(yahoo_meta.get("regularMarketTime", 0), 0))
            if market_time > 0:
                quote_ts = market_time * 1000
                market_dt = datetime.fromtimestamp(market_time, stock_timezone(text))
                quote_date = market_dt.strftime("%Y-%m-%d")
                quote_time = market_dt.strftime("%H:%M:%S")
        except Exception as exc:
            yahoo_error = str(exc)
            source = "offline"
        if yahoo_allowed:
            record_provider_call(
                "yahoo",
                "quote",
                success=close > 0 and source == "yahoo",
                latency_ms=(time.perf_counter() - yahoo_started) * 1000,
                error=yahoo_error or ("quote returned no price" if close <= 0 else ""),
                scope=quote_scope,
            )
    if close <= 0:
        last_good = forced_last_good(
            "; ".join(item for item in (stooq_error, yahoo_error) if item)
            or "forced stock quote refresh failed; using last known good"
        )
        if last_good:
            return last_good
        return cache_stock_quote(text, stock_seed_quote(text))
    status = "ONLINE" if close > 0 else "OFFLINE"
    quote = normalize_stock_quote_quality({
        "symbol": text,
        "instId": meta.get("futu", text),
        "name": meta["name"],
        "quote": meta.get("quote", "USD"),
        "type": "stock",
        "category": "stocks",
        "source": source,
        "exchange": meta.get("exchange", "US"),
        "market": meta.get("market", "US"),
        "sector": meta.get("sector", "Stock"),
        "status": status,
        "last": close,
        "open24h": open_price,
        "high24h": high,
        "low24h": low,
        "vol24h": volume,
        "volCcy24h": volume,
        "bidPx": 0.0,
        "askPx": 0.0,
        "change24h_pct": provider_change if provider_change is not None else 0.0,
        "ts": quote_ts,
        "date": quote_date,
        "time": quote_time,
    }, previous_close=previous_close, change_basis=change_basis, provider_change=provider_change, now_ms=now_ms())
    return cache_stock_quote(text, quote)


def read_stock_quotes_cached(max_age_ms: int = 60000, fast: bool = False) -> list[dict[str, Any]]:
    if now_ms() - int(STOCK_QUOTE_CACHE.get("time") or 0) < max_age_ms:
        return STOCK_QUOTE_CACHE.get("rows", [])
    symbols = [item["symbol"] for item in STOCK_MARKETS]
    futu_rows = {} if fast else read_futu_quotes(symbols)
    rows = []
    for item in STOCK_MARKETS:
        cache_quote_fn = globals().get("_stock_quote_from_cache")
        fallback_quote = cache_quote_fn(item["symbol"]) if callable(cache_quote_fn) else read_stock_quote(item["symbol"], max_age_ms=max_age_ms, use_futu=False)
        rows.append(futu_rows.get(item["symbol"]) or fallback_quote)
    STOCK_QUOTE_CACHE.update({"time": now_ms(), "rows": rows})
    return rows


def cached_stock_quote_price(symbol: str, max_age_ms: int = 15 * 60 * 1000) -> float:
    meta = stock_meta(symbol)
    cached = STOCK_SINGLE_QUOTE_CACHE.get(meta["symbol"]) or {}
    if now_ms() - int(cached.get("time") or 0) > max_age_ms:
        return 0.0
    quote = cached.get("quote")
    if not isinstance(quote, dict):
        return 0.0
    return pct(quote.get("last", 0.0), 0.0)


def stock_candle_reference_ts(payload: dict[str, Any] | None, interval: str, session: str) -> int:
    rows = list((payload or {}).get("rows") or [])
    if stock_cache_interval(interval) not in {"1d", "1dutc"} and session == "all":
        regular_rows = filter_stock_rows_by_session(rows, "regular")
        if regular_rows:
            rows = regular_rows
    return latest_stock_candle_ts(rows)


def stock_candle_needs_source_comparison(payload: dict[str, Any] | None, interval: str, session: str) -> bool:
    if stock_cache_interval(interval) in {"1d", "1dutc"}:
        return False
    reference_ts = stock_candle_reference_ts(payload, interval, session)
    return reference_ts <= 0 or now_ms() - reference_ts > 18 * 60 * 60 * 1000


def read_stock_candles(
    symbol: str,
    limit: int = 260,
    interval: str = "1d",
    session: str = "all",
    fast: bool = False,
    force: bool = False,
    completed_only: bool = False,
) -> dict[str, Any]:
    text = (symbol or "AAPL").upper()
    clean_session = normalize_stock_history_session(interval, session)
    cached = None if force else read_stock_candle_cache(text, limit, interval, clean_session)
    persistent = read_stock_persistent_candle_cache(text, limit, interval, clean_session)
    completion_refresh_required = False
    completed_cache_fallback: dict[str, Any] | None = None
    if completed_only and not force and stock_cache_interval(interval) in {"1d", "1dutc"}:
        required_rows = max(120, max(int(limit) - 1, 1))
        for candidate in (cached, persistent):
            if not isinstance(candidate, dict):
                continue
            complete_rows = [
                dict(row) for row in candidate.get("rows") or []
                if bool(row.get("complete", row.get("confirm", not bool(row.get("provisional")))))
            ]
            stale_warning = stock_candle_stale_warning(complete_rows, interval, text)
            completion_due = stock_payload_has_due_incomplete_daily(candidate, interval, text)
            completion_refresh_required = completion_refresh_required or completion_due
            if len(complete_rows) < required_rows or stale_warning:
                continue
            completed_payload = with_stock_freshness({
                **candidate,
                "rows": complete_rows[-limit:],
                "warning": "",
                "completed_only": True,
                "retrieval_source": str(candidate.get("source") or "memory_cache"),
                "origin_source": str(candidate.get("origin_source") or candidate.get("source") or "stock_cache"),
            }, interval, text)
            if completion_due:
                completed_cache_fallback = completed_payload
                continue
            return completed_payload
    persistent_current = bool(
        persistent
        and not persistent.get("warning")
        and not stock_payload_needs_session_refresh(persistent, interval, text)
        and not stock_payload_has_due_incomplete_daily(persistent, interval, text)
    )
    if fast and not force:
        if cached:
            return {**cached, "fast": True}
        if persistent_current:
            return {**persistent, "fast": True}
        if persistent:
            return {**persistent, "fast": True}
        payload = stock_seed_candles(text, limit, interval, clean_session, cached_stock_quote_price(text))
        payload["fast"] = True
        payload["warning"] = "fast quote preview, stock cache unavailable; background refresh pending" if payload.get("source") == "quote_preview_seed" else "fast seed, stock cache unavailable; background refresh pending"
        return with_stock_freshness(payload, interval, text)
    futu_status = futu_status_snapshot(False)
    futu_online = bool(futu_status.get("opend_online"))
    if cached and not completion_refresh_required and (not futu_online or stock_payload_is_futu(cached)):
        return cached
    futu_rows = {"ok": False, "rows": [], "source": "futu", "error": futu_status.get("message", "Futu offline")}
    futu_candidate: dict[str, Any] | None = None
    if futu_online:
        futu_rows = read_futu_stock_candles(
            text,
            limit,
            interval,
            clean_session,
            include_snapshot=not completed_only,
        )
        if futu_rows.get("ok") and futu_rows.get("rows"):
            if not stock_candle_needs_source_comparison(futu_rows, interval, clean_session):
                return cache_stock_candles(text, interval, clean_session, futu_rows)
            futu_candidate = futu_rows
    if cached and not force and not completion_refresh_required:
        return {**cached, "refresh_note": "Futu online but refresh failed; showing latest cache", "refresh_error": futu_rows.get("error", "")}
    if persistent_current and not force:
        return persistent
    external: dict[str, Any] = {"ok": False, "rows": [], "source": "external", "errors": []}
    if ALLOW_STOCK_FALLBACK or ALLOW_STOCK_HISTORY_FALLBACK:
        external = read_external_stock_candles(text, limit, interval, clean_session)
        if external.get("ok") and external.get("rows"):
            winner = external
            if futu_candidate:
                futu_ts = stock_candle_reference_ts(futu_candidate, interval, clean_session)
                external_ts = stock_candle_reference_ts(external, interval, clean_session)
                if futu_ts >= external_ts:
                    winner = futu_candidate
                winner = {
                    **winner,
                    "source_arbitration": {
                        "reason": "intraday freshness comparison",
                        "selected": winner.get("source"),
                        "futu_latest_ts": futu_ts,
                        "external_source": external.get("source"),
                        "external_latest_ts": external_ts,
                    },
                }
            return cache_stock_candles(text, interval, clean_session, winner)
    if futu_candidate:
        return cache_stock_candles(text, interval, clean_session, {
            **futu_candidate,
            "source_arbitration": {
                "reason": "external comparison unavailable",
                "selected": futu_candidate.get("source"),
                "futu_latest_ts": stock_candle_reference_ts(futu_candidate, interval, clean_session),
                "external_errors": list(external.get("errors") or []),
            },
        })
    if completed_only and completed_cache_fallback:
        return {
            **completed_cache_fallback,
            "warning": "latest completed daily candle refresh pending; using prior completed history",
            "refresh_errors": list(external.get("errors") or []),
            "refresh_error": futu_rows.get("error", ""),
        }
    if persistent_current:
        result = {
            **persistent,
            "refresh_errors": list(external.get("errors") or []),
            "refresh_error": futu_rows.get("error", ""),
        }
        if force:
            result.update({
                "forced": True,
                "refresh_failed": True,
                "warning": str(result.get("warning") or "forced stock refresh failed; using local cache"),
            })
        return result
    if persistent:
        result = {
            **augment_stock_daily_with_intraday(persistent, text, limit, interval, clean_session),
            "refresh_errors": list(external.get("errors") or []),
            "refresh_error": futu_rows.get("error", ""),
        }
        if force:
            result.update({
                "forced": True,
                "refresh_failed": True,
                "warning": str(result.get("warning") or "forced stock refresh failed; using local cache"),
            })
        return result
    seed = stock_seed_candles(text, limit, interval, clean_session, cached_stock_quote_price(text))
    seed["errors"] = [
        {"provider": "futu", "error": futu_rows.get("error", "no rows")},
        *list(external.get("errors") or []),
    ]
    return with_stock_freshness(seed, interval, text)


STOCK_HISTORY_PREWARM_SERVICE = StockHistoryPrewarmService(
    read_candles=read_stock_candles,
    cache_coverage=stock_candle_cache_coverage,
    futu_status=futu_status_snapshot,
    now_ms=now_ms,
    max_workers=2,
)


def stock_history_prewarm_snapshot(symbol: str = "", start: bool = False, force: bool = False) -> dict[str, Any]:
    if not STOCK_HISTORY_PREWARM_SERVICE:
        return {"ok": False, "error": "history prewarm unavailable", "live_trading_allowed": False}
    if RUNTIME_READ_ONLY and start:
        return {
            **STOCK_HISTORY_PREWARM_SERVICE.status(),
            "ok": False,
            "status": "BLOCK",
            "error": "runtime is read-only",
            "read_only": True,
            "queued_now": 0,
            "live_trading_allowed": False,
        }
    clean_symbol = stock_meta(symbol)["symbol"] if symbol else ""
    if start:
        queued_now = 0
        skipped_now = 0
        if clean_symbol:
            intraday = STOCK_HISTORY_PREWARM_SERVICE.start(
                [clean_symbol],
                interval="1m",
                session="all",
                limit=1000,
                force=force,
            )
            queued_now += int(intraday.get("queued_now") or 0)
            skipped_now += int(intraday.get("skipped_now") or 0)
        symbols = [clean_symbol, *STOCK_HISTORY_PRIORITY] if clean_symbol else list(STOCK_HISTORY_PRIORITY)
        daily = STOCK_HISTORY_PREWARM_SERVICE.start(
            symbols,
            interval="1d",
            session="regular",
            limit=520,
            force=force,
        )
        queued_now += int(daily.get("queued_now") or 0)
        skipped_now += int(daily.get("skipped_now") or 0)
        return {
            **STOCK_HISTORY_PREWARM_SERVICE.status(),
            "queued_now": queued_now,
            "skipped_now": skipped_now,
            "profiles": ["active_symbol_intraday", "priority_daily"],
        }
    return STOCK_HISTORY_PREWARM_SERVICE.status(clean_symbol)


def market_tickers_snapshot(fast: bool = False, force: bool = False) -> dict[str, Any]:
    cached_payload = MARKET_TICKERS_CACHE.get("payload")
    cache_age = now_ms() - int(MARKET_TICKERS_CACHE.get("time") or 0)
    if fast and not force and isinstance(cached_payload, dict) and cache_age < 120000:
        return {**cached_payload, "cached": True, "fast": True, "cache_age_ms": cache_age}
    universe = market_universe()
    previous_tickers = {
        row.get("symbol") or row.get("instId"): row
        for row in ((cached_payload or {}).get("tickers", []) if isinstance(cached_payload, dict) else [])
        if isinstance(row, dict)
    }
    spot_rows = {} if fast and not force else {row.get("instId"): row for row in okx_rows("/api/v5/market/tickers", {"instType": "SPOT"})}
    swap_rows = {} if fast and not force else {row.get("instId"): row for row in okx_rows("/api/v5/market/tickers", {"instType": "SWAP"})}
    stock_rows = {row.get("symbol"): row for row in read_stock_quotes_cached(fast=fast and not force)}
    tickers = []
    for item in universe:
        source_row: dict[str, Any] = {}
        if item["type"] == "spot":
            source_row = spot_rows.get(item["instId"], {}) or previous_tickers.get(item["symbol"], {}) or previous_tickers.get(item["instId"], {})
        elif item["type"] == "swap":
            source_row = swap_rows.get(item["instId"], {}) or previous_tickers.get(item["symbol"], {}) or previous_tickers.get(item["instId"], {})
        elif item["type"] == "stock":
            source_row = stock_rows.get(item["symbol"], {})
        last = pct(source_row.get("last", "0"))
        open24h = pct(source_row.get("open24h", "0"))
        change = source_row.get("change24h_pct")
        if change is None:
            change = (last / open24h - 1) * 100 if last > 0 and open24h > 0 else 0.0
        tickers.append({
            **item,
            "source": source_row.get("source", item.get("source", "")),
            "origin_source": source_row.get("origin_source", ""),
            "exchange": source_row.get("exchange", item.get("exchange", "")),
            "market": source_row.get("market", item.get("market", "")),
            "quote": source_row.get("quote", item.get("quote", "")),
            "warning": source_row.get("warning", ""),
            "data_age_ms": source_row.get("data_age_ms"),
            "last": last,
            "price": last,
            "change24h_pct": round(float(change or 0), 2),
            "high24h": pct(source_row.get("high24h", "0")),
            "low24h": pct(source_row.get("low24h", "0")),
            "vol24h": pct(source_row.get("vol24h", source_row.get("volCcy24h", "0"))),
            "volCcy24h": pct(source_row.get("volCcy24h", source_row.get("vol24h", "0"))),
            "bidPx": pct(source_row.get("bidPx", "0")),
            "askPx": pct(source_row.get("askPx", "0")),
            "status": source_row.get("status", "ONLINE" if last > 0 else "OFFLINE"),
            "ts": int(source_row.get("ts") or now_ms()),
        })
    payload = {"ok": True, "markets": universe, "tickers": tickers, "updated_at": now_ms(), "fast": bool(fast and not force)}
    MARKET_TICKERS_CACHE.update({"time": now_ms(), "payload": payload})
    return payload


def read_btc_daily_sqlite(db_path: Path, limit: int) -> list[dict[str, Any]]:
    uri = db_path.absolute().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        columns = """
            trading_date AS date,
            ts_ms,
            open,
            high,
            low,
            close,
            volume,
            volume_ccy,
            volume_quote,
            confirmed,
            source
        """
        if limit > 0:
            cursor = conn.execute(f"""
                SELECT * FROM (
                    SELECT {columns}
                    FROM btc_daily_prices
                    WHERE symbol = 'BTC-USDT'
                    ORDER BY trading_date DESC
                    LIMIT ?
                )
                ORDER BY date ASC
            """, (limit,))
        else:
            cursor = conn.execute(f"""
                SELECT {columns}
                FROM btc_daily_prices
                WHERE symbol = 'BTC-USDT'
                ORDER BY trading_date ASC
            """)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def copy_btc_database_for_reading() -> Path:
    ensure_runtime()
    source_stat = BTC_DAILY_DB.stat()
    should_copy = True
    if BTC_DAILY_DB_CACHE.exists():
        cache_stat = BTC_DAILY_DB_CACHE.stat()
        should_copy = cache_stat.st_size != source_stat.st_size or cache_stat.st_mtime < source_stat.st_mtime
    if should_copy:
        shutil.copyfile(BTC_DAILY_DB, BTC_DAILY_DB_CACHE)
    return BTC_DAILY_DB_CACHE


def unique_existing_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        key = str(path).lower()
        if key not in seen and path.exists():
            seen.add(key)
            result.append(path)
    return result


def btc_daily_source_available() -> bool:
    return bool(unique_existing_paths([BTC_DAILY_DB, BTC_DAILY_FALLBACK_DB, BTC_DAILY_DB_CACHE, BTC_DAILY_CSV, BTC_DAILY_FALLBACK_CSV]))


def read_local_btc_daily(limit: int = 500) -> dict[str, Any]:
    errors = []
    for db_path in unique_existing_paths([BTC_DAILY_DB, BTC_DAILY_FALLBACK_DB, BTC_DAILY_DB_CACHE]):
        try:
            rows = read_btc_daily_sqlite(db_path, limit)
            return {"ok": True, "source": "local_sqlite", "path": str(db_path), "rows": rows}
        except Exception as exc:
            errors.append(f"sqlite direct {db_path}: {exc}")
            try:
                cache_path = copy_btc_database_for_reading()
                rows = read_btc_daily_sqlite(cache_path, limit)
                return {
                    "ok": True,
                    "source": "local_sqlite_cache",
                    "path": str(db_path),
                    "cache_path": str(cache_path),
                    "warning": errors[-1],
                    "rows": rows,
                }
            except Exception as cache_exc:
                errors.append(f"sqlite cache: {cache_exc}")

    for csv_path in unique_existing_paths([BTC_DAILY_CSV, BTC_DAILY_FALLBACK_CSV]):
        with csv_path.open("r", encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        rows = rows[-limit:] if limit > 0 else rows
        return {
            "ok": True,
            "source": "local_csv",
            "path": str(csv_path),
            "warning": "; ".join(errors) if errors else "",
            "rows": rows,
        }
    missing = [BTC_DAILY_DB, BTC_DAILY_FALLBACK_DB, BTC_DAILY_CSV, BTC_DAILY_FALLBACK_CSV]
    return {"ok": False, "error": "; ".join(errors) or f"not found: {' / '.join(str(item) for item in missing)}", "rows": []}


def history_cache_symbols() -> list[str]:
    spot = [f"{base}-USDT" for base in CORE_CRYPTO_BASES]
    swaps = [f"{base}-USDT-SWAP" for base in CORE_CRYPTO_BASES]
    return spot + swaps


def market_history_store() -> MarketHistoryStore:
    return MarketHistoryStore(
        MARKET_HISTORY_CACHE_DB,
        now_ms=now_ms,
        read_only=RUNTIME_READ_ONLY,
    )


def ensure_market_history_cache_db() -> sqlite3.Connection:
    return market_history_store().connect(write=not RUNTIME_READ_ONLY)


def candle_date_from_ts(ts_ms: int) -> str:
    if ts_ms <= 0:
        return ""
    return datetime.fromtimestamp(ts_ms / 1000, tz=ZoneInfo("UTC")).strftime("%Y-%m-%d")


def normalize_cache_candle(row: Any) -> dict[str, Any] | None:
    return normalize_history_candle(
        row,
        default_complete=False,
        require_utc_date=True,
    )


def upsert_market_history_cache_report(
    symbol: str,
    rows: list[Any],
    source: str = "okx",
) -> dict[str, Any]:
    return market_history_store().upsert(symbol, rows, source)


def upsert_market_history_cache(symbol: str, rows: list[Any], source: str = "okx") -> int:
    return int(upsert_market_history_cache_report(symbol, rows, source).get("stored") or 0)


def read_market_history_cache(symbol: str, limit: int = 500) -> dict[str, Any]:
    return market_history_store().read(symbol, limit)


def market_history_cache_stats(symbol: str) -> dict[str, Any]:
    return market_history_store().stats(symbol)


def fetch_okx_daily_history(symbol: str, limit: int = 300) -> list[dict[str, Any]]:
    rows, _source, _attempts = fetch_okx_daily_history_pages(
        lambda path, query: (okx_rows(path, query), ""),
        (symbol or "BTC-USDT").upper(),
        limit,
    )
    return rows


def okx_rows_with_error(path: str, query: dict[str, str]) -> tuple[list[Any], str]:
    return okx_rows_with_error_io(path, query)


def binance_daily_history(symbol: str, limit: int = 300) -> tuple[list[Any], str, str]:
    text = (symbol or "BTC-USDT").upper()
    base = text.replace("-USDT-SWAP", "").replace("-USDT", "")
    if base not in CORE_CRYPTO_BASES:
        return [], "", "unsupported symbol"
    pair = f"{base}USDT"
    is_swap = text.endswith("-SWAP")
    endpoint = "https://fapi.binance.com/fapi/v1/klines" if is_swap else "https://api.binance.com/api/v3/klines"
    source = "binance_futures_klines" if is_swap else "binance_spot_klines"
    query = urllib.parse.urlencode({"symbol": pair, "interval": "1d", "limit": str(min(max(int(limit), 30), 1000))})
    request = urllib.request.Request(f"{endpoint}?{query}", headers={"User-Agent": "HakimiTrade/2.0"})
    try:
        with urllib.request.urlopen(request, timeout=OKX_TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8", errors="ignore"))
        rows: list[dict[str, Any]] = []
        for row in payload if isinstance(payload, list) else []:
            if not isinstance(row, list) or len(row) < 7:
                continue
            rows.append({
                "ts_ms": int(row[0]),
                "open": row[1],
                "high": row[2],
                "low": row[3],
                "close": row[4],
                "volume": row[5],
                "complete": int(row[6]) < now_ms(),
                "source": source,
            })
        return rows, source, ""
    except Exception as exc:
        return [], source, str(exc)


def fetch_daily_history_with_report(symbol: str, limit: int = 300) -> tuple[list[Any], str, list[dict[str, Any]]]:
    text = (symbol or "BTC-USDT").upper()
    rows, selected_source, attempts = fetch_okx_daily_history_pages(
        okx_rows_with_error,
        text,
        limit,
    )
    if rows:
        return rows, selected_source or "okx_history_candles", attempts

    fallback_rows, source, error = binance_daily_history(text, limit)
    attempts.append({"source": source or "binance", "path": "binance_klines", "rows": len(fallback_rows), "error": error[:160] if error else ""})
    normalized = [
        item for item in (
            normalize_history_candle(
                row,
                source=source,
                default_complete=False,
                require_utc_date=True,
            )
            for row in fallback_rows
        )
        if item
    ]
    if normalized:
        return normalized[-limit:], source, attempts
    return [], "", attempts


def backfill_market_history_cache(symbol: str, limit: int = 300) -> dict[str, Any]:
    text = (symbol or "BTC-USDT").upper()
    limit = int(clamp(limit, 30, 2000))
    if RUNTIME_READ_ONLY:
        return {
            "ok": False,
            "status": "RUNTIME_READ_ONLY",
            "symbol": text,
            "error": "runtime is read-only",
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    if text not in history_cache_symbols():
        return {"ok": False, "symbol": text, "error": "symbol is not in crypto history cache universe"}
    rows, source, attempts = fetch_daily_history_with_report(text, limit)
    write_report = upsert_market_history_cache_report(text, rows, source or "unknown") if rows else {}
    inserted = int(write_report.get("stored") or 0)
    stats = market_history_cache_stats(text)
    append_ledger({"type": "history_cache_backfill", "symbol": text, "requested": limit, "source": source, "fetched": len(rows), "stored": inserted, "write_report": write_report, "attempts": attempts})
    return {
        "ok": inserted > 0,
        "symbol": text,
        "requested": limit,
        "source": source,
        "fetched": len(rows),
        "stored": inserted,
        "write_report": write_report,
        "stats": stats,
        "attempts": attempts,
        "error": "" if inserted > 0 else "all history sources returned no rows",
    }


def market_history_cache_status() -> dict[str, Any]:
    rows = []
    for symbol in history_cache_symbols():
        stats = market_history_cache_stats(symbol)
        source = stats["source"]
        if symbol == "BTC-USDT":
            btc = read_local_btc_daily(5000)
            raw_external_rows = list(btc.get("rows") or [])
            external_rows = [
                item for item in (
                    normalize_history_candle(
                        row,
                        source=(
                            str(row.get("source") or btc.get("source") or "local_btc_daily")
                            if isinstance(row, dict)
                            else str(btc.get("source") or "local_btc_daily")
                        ),
                        default_complete=True,
                        require_utc_date=True,
                    )
                    for row in raw_external_rows
                )
                if item
            ]
            cache_payload = read_market_history_cache(symbol, 10_000)
            cache_blocked = str(cache_payload.get("status") or "MISSING") == "BLOCK"
            cache_rows = [] if cache_blocked else list(cache_payload.get("rows") or [])
            combined_rows = merge_backtest_history(external_rows, cache_rows, limit=10_000)
            if combined_rows:
                complete_rows = [row for row in combined_rows if row.get("complete") is True]
                invalid_rows = len(raw_external_rows) - len(external_rows)
                latest_complete_ts = max(
                    (int(row.get("ts_ms") or 0) for row in complete_rows),
                    default=0,
                )
                stale = latest_complete_ts <= 0 or now_ms() - latest_complete_ts > 4 * 86_400_000
                blockers = []
                if invalid_rows:
                    blockers.append(f"invalid_external_rows:{invalid_rows}")
                if cache_blocked:
                    blockers.append("market_history_cache_blocked")
                if stale:
                    blockers.append("completed_history_stale")
                combined_source = "+".join(dict.fromkeys(
                    str(row.get("source") or "") for row in combined_rows if row.get("source")
                )) or str(btc.get("source") or "local_btc_daily")
                evidence = build_history_dataset_evidence(
                    symbol=symbol,
                    rows=combined_rows,
                    source=combined_source,
                )
                status = (
                    "BLOCK"
                    if invalid_rows or cache_blocked
                    else "PARTIAL"
                    if stale or len(complete_rows) < 240
                    else "READY"
                )
                stats = {
                    **stats,
                    "status": status,
                    "source": combined_source,
                    "external_ready": True,
                    "rows": len(combined_rows),
                    "complete_rows": len(complete_rows),
                    "incomplete_rows": len(combined_rows) - len(complete_rows),
                    "invalid_rows": invalid_rows,
                    "first": str(combined_rows[0].get("date") or ""),
                    "last": str(combined_rows[-1].get("date") or ""),
                    "data_hash": str(evidence.get("data_hash") or ""),
                    "blockers": blockers,
                }
                source = stats["source"]
        rows.append({
            **stats,
            "source": source,
            "priority": "P0" if stats["status"] in {"MISSING", "BLOCK"} else "P1" if stats["status"] == "PARTIAL" else "OK",
            "next": "补全日线缓存" if stats["status"] != "READY" else "可用于回测/策略评分",
        })
    blocked = [row for row in rows if row["status"] == "BLOCK"]
    missing = [row for row in rows if row["status"] == "MISSING"]
    partial = [row for row in rows if row["status"] == "PARTIAL"]
    ready = [row for row in rows if row["status"] == "READY"]
    return {
        "ok": True,
        "path": str(MARKET_HISTORY_CACHE_DB),
        "summary": f"历史缓存：READY {len(ready)} / PARTIAL {len(partial)} / MISSING {len(missing)} / BLOCK {len(blocked)}",
        "rows": rows,
        "queue": [row for row in rows if row["status"] != "READY"],
        "updated_at": now_ms(),
    }




def strategy_leaderboard(limit: int = 240) -> list[dict[str, Any]]:
    payload = read_local_btc_daily(limit)
    rows = payload.get("rows", [])
    closes = []
    for row in rows:
        try:
            closes.append(float(row["close"]))
        except Exception:
            continue
    if len(closes) < 30:
        return []
    total_return = closes[-1] / closes[0] - 1
    recent_return = closes[-1] / closes[-30] - 1 if len(closes) >= 30 else total_return
    volatility = average([abs(closes[i] / closes[i - 1] - 1) for i in range(1, len(closes))])
    trend_strength = abs(recent_return) / max(volatility, 1e-9)
    base = [
        ("dual_ma", total_return * 0.45 + recent_return * 0.55 + trend_strength * 0.004, "趋势行情适配度高"),
        ("grid", (0.06 - abs(recent_return)) + volatility * 2.2, "震荡区间收益假设更优"),
        ("bollinger", volatility * 1.8 - abs(recent_return) * 0.25, "均值回归机会评分"),
        ("macd", recent_return * 0.8 + volatility * 0.9, "动量延续评分"),
        ("rsi", volatility * 1.3 - recent_return * 0.15, "超买超卖反转评分"),
        ("momentum", recent_return * 1.1 + trend_strength * 0.003, "突破动量评分"),
        ("martingale", volatility * 1.9 - abs(recent_return) * 0.55, "回撤分层加仓评分"),
        ("anti_martingale", recent_return * 1.2 + trend_strength * 0.004, "顺势浮盈加仓评分"),
        ("livermore", recent_return * 1.35 + trend_strength * 0.006, "关键点突破评分"),
        ("turtle", recent_return * 1.1 + volatility * 0.6, "通道突破评分"),
        ("darvas", recent_return * 0.95 + volatility * 0.75, "箱体突破评分"),
    ]
    result = []
    for strategy_id, score, note in base:
        strategy = choose_strategy(strategy_id)
        result.append({
            "id": strategy_id,
            "name": strategy["name"],
            "style": strategy["style"],
            "score": round(max(score * 100, -99), 2),
            "estimated_return": round(score * 10, 2),
            "risk": "高" if abs(score) > 0.12 else "中" if abs(score) > 0.04 else "低",
            "note": note,
        })
    return sorted(result, key=lambda item: item["score"], reverse=True)


def strategy_lab(symbol: str, strategy_id: str, price: float) -> dict[str, Any]:
    strategy = choose_strategy(strategy_id)
    payload = read_local_btc_daily(420)
    closes = []
    for row in payload.get("rows", [])[-180:]:
        try:
            closes.append(float(row["close"]))
        except Exception:
            continue
    if not closes:
        closes = [price if price > 0 else 0.0]
    last = price or closes[-1]
    short = average(closes[-20:])
    long = average(closes[-80:]) if len(closes) >= 80 else average(closes)
    high = max(closes[-80:]) if len(closes) >= 80 else max(closes)
    low = min(closes[-80:]) if len(closes) >= 80 else min(closes)
    volatility = (high - low) / max(last, 1.0)
    trend = (short - long) / max(long, 1.0)
    regime = "趋势偏多" if trend > 0.015 else "趋势偏空" if trend < -0.015 else "震荡区间"
    if volatility > 0.18:
        regime += " · 高波动"
    elif volatility < 0.07:
        regime += " · 低波动"
    base_score = clamp(55 + trend * 600 - volatility * 35, 18, 88)
    templates = [
        ("稳健", 0.35, 1.6, 0.8, "低杠杆，确认后进场"),
        ("均衡", 0.55, 2.4, 1.2, "跟随主策略，允许轻微回撤"),
        ("进攻", 0.75, 3.6, 1.8, "只适合波动放大时小仓尝试"),
    ]
    rows = []
    for name, position, take_pct, stop_pct, note in templates:
        score = clamp(base_score + (0.55 - position) * 12 - stop_pct * 1.3, 10, 92)
        if strategy_id in {"martingale", "grid", "bollinger"} and "震荡" in regime:
            score = clamp(score + 8, 10, 94)
        if strategy_id in {"livermore", "turtle", "darvas", "momentum"} and "趋势偏多" in regime:
            score = clamp(score + 9, 10, 95)
        rows.append({
            "preset": name,
            "strategy": strategy["name"],
            "regime": regime,
            "anchor": round(last, 4),
            "position_pct": round(position * 100, 0),
            "take_profit": round(last * (1 + take_pct / 100), 4),
            "stop_loss": round(last * (1 - stop_pct / 100), 4),
            "score": round(score, 1),
            "note": note,
        })
    return {
        "ok": True,
        "symbol": symbol,
        "strategy": strategy,
        "price": round(last, 4),
        "regime": regime,
        "volatility_pct": round(volatility * 100, 2),
        "trend_pct": round(trend * 100, 2),
        "rows": rows,
    }


def _legacy_rolling_strategy_signal(
    strategy_id: str,
    closes: list[float],
    price: float,
    has_position: bool,
    entry_price: float = 0.0,
    last_scale_price: float = 0.0,
) -> dict[str, Any]:
    if len(closes) < 30 or price <= 0:
        return {"action": "HOLD", "reason": "历史样本不足"}
    if strategy_id == "dual_ma":
        fast = average(closes[-20:])
        slow = average(closes[-60:]) if len(closes) >= 60 else average(closes)
        if fast > slow and not has_position:
            return {"action": "BUY", "reason": "快均线上穿慢均线"}
        if fast < slow and has_position:
            return {"action": "EXIT", "reason": "快均线跌破慢均线"}
    elif strategy_id == "grid":
        recent = closes[-80:] if len(closes) >= 80 else closes
        low = min(recent)
        high = max(recent)
        location = (price - low) / max(high - low, 1e-9)
        if location < 0.28 and not has_position:
            return {"action": "BUY", "reason": "靠近网格下沿"}
        if location > 0.72 and has_position:
            return {"action": "SELL", "reason": "靠近网格上沿"}
    elif strategy_id == "bollinger":
        recent = closes[-20:]
        mid = average(recent)
        band = average([(value - mid) ** 2 for value in recent]) ** 0.5 * 2
        if price < mid - band and not has_position:
            return {"action": "BUY", "reason": "跌破布林下轨"}
        if price > mid and has_position:
            return {"action": "SELL", "reason": "回到布林中轨上方"}
    elif strategy_id == "rsi":
        gains, losses = [], []
        for previous, current in zip(closes[-15:-1], closes[-14:]):
            change = current - previous
            gains.append(max(change, 0))
            losses.append(abs(min(change, 0)))
        rs = average(gains) / max(average(losses), 1e-9)
        rsi = 100 - 100 / (1 + rs)
        if rsi < 30 and not has_position:
            return {"action": "BUY", "reason": f"RSI超卖 {rsi:.1f}"}
        if rsi > 70 and has_position:
            return {"action": "EXIT", "reason": f"RSI超买 {rsi:.1f}"}
    elif strategy_id == "martingale":
        anchor = last_scale_price or entry_price or closes[-1]
        if not has_position and price < average(closes[-20:]) * 0.985:
            return {"action": "BUY", "reason": "马丁首层低吸"}
        if has_position and price <= anchor * 0.975:
            return {"action": "ADD", "reason": "马丁下跌加仓"}
        if has_position and entry_price and price >= entry_price * 1.018:
            return {"action": "EXIT", "reason": "马丁均价上方退出"}
    elif strategy_id == "anti_martingale":
        ma20 = average(closes[-20:])
        ma60 = average(closes[-60:]) if len(closes) >= 60 else average(closes)
        anchor = last_scale_price or entry_price or price
        if not has_position and ma20 > ma60 and price > ma20:
            return {"action": "BUY", "reason": "反马丁顺势首仓"}
        if has_position and price >= anchor * 1.02:
            return {"action": "ADD", "reason": "反马丁盈利加仓"}
        if has_position and price < ma20 * 0.985:
            return {"action": "EXIT", "reason": "跌破短期趋势"}
    elif strategy_id == "livermore":
        pivot_high = max(closes[-60:-1])
        pivot_low = min(closes[-30:])
        if not has_position and price > pivot_high * 1.006:
            return {"action": "BUY", "reason": "利弗莫尔关键点突破"}
        if has_position and price < pivot_low * 0.995:
            return {"action": "EXIT", "reason": "跌回关键防守位"}
    elif strategy_id == "turtle":
        entry_high = max(closes[-20:-1])
        exit_low = min(closes[-10:])
        if not has_position and price > entry_high:
            return {"action": "BUY", "reason": "海龟20周期突破"}
        if has_position and price < exit_low:
            return {"action": "EXIT", "reason": "海龟10周期退出"}
    elif strategy_id == "darvas":
        box_high = max(closes[-40:-1])
        box_low = min(closes[-40:-1])
        if not has_position and price > box_high * 1.004:
            return {"action": "BUY", "reason": "达瓦斯箱体突破"}
        if has_position and price < box_low:
            return {"action": "EXIT", "reason": "跌破箱体下沿"}
    else:
        momentum = price / max(closes[-20], 1e-9) - 1
        if momentum > 0.015 and not has_position:
            return {"action": "BUY", "reason": "20日动量突破"}
        if momentum < -0.015 and has_position:
            return {"action": "EXIT", "reason": "20日动量转弱"}
    return {"action": "HOLD", "reason": "等待信号"}


def rolling_strategy_signal(
    strategy_id: str,
    closes: list[float],
    price: float,
    has_position: bool,
    entry_price: float = 0.0,
    last_scale_price: float = 0.0,
) -> dict[str, Any]:
    strategy = next((item for item in STRATEGIES if item["id"] == strategy_id), None)
    if strategy is None:
        return {
            "action": "HOLD",
            "reason": "unsupported_strategy",
            "validation_blocker": "Unknown strategy id; implicit fallback is forbidden.",
        }
    return causal_rolling_strategy_signal(
        strategy_id,
        closes,
        price,
        has_position,
        entry_price,
        last_scale_price,
        params=strategy.get("params") or {},
    )


def evaluate_strategy_signal(
    strategy_id: str,
    price: float,
    has_position: bool,
    entry_price: float = 0.0,
    last_scale_price: float = 0.0,
    *,
    symbol: str = "",
) -> dict[str, Any]:
    rows = strategy_candles_for_symbol(symbol, 180) if symbol else []
    if not rows:
        return {
            "action": "HOLD",
            "confidence": 0.0,
            "reason": "symbol_history_required",
            "validation_blocker": "A strategy signal must be bound to completed candles for its symbol.",
        }
    strategy = choose_strategy(strategy_id)
    signal_mode = strategy_signal_input(strategy_id)
    history: list[Any] = rows if signal_mode == "BARS" else [float(row["close"]) for row in rows]
    signal_price = float(rows[-1].get("close") or price) if signal_mode == "BARS" else price
    raw = build_strategy_signal_fn(strategy_id, strategy.get("params") or {})(
        history,
        signal_price,
        has_position,
        entry_price,
        last_scale_price,
    )
    confidence = 0.7 if raw.get("action") in {"BUY", "EXIT", "SELL"} else 0.4
    return {"confidence": confidence, **raw}


def max_drawdown(equity_values: list[float]) -> float:
    peak = equity_values[0] if equity_values else 0.0
    drawdown = 0.0
    for value in equity_values:
        peak = max(peak, value)
        if peak > 0:
            drawdown = max(drawdown, (peak - value) / peak)
    return drawdown


def sharpe_ratio(equity_values: list[float]) -> float:
    returns = []
    for previous, current in zip(equity_values[:-1], equity_values[1:]):
        if previous > 0:
            returns.append(current / previous - 1)
    if len(returns) < 5:
        return 0.0
    avg = average(returns)
    variance = average([(item - avg) ** 2 for item in returns])
    std = variance ** 0.5
    return avg / max(std, 1e-9) * (365 ** 0.5)


def normalize_backtest_candle(row: Any) -> dict[str, Any] | None:
    source = str(row.get("source") or row.get("origin_source") or "") if isinstance(row, dict) else ""
    return normalize_history_candle(
        row,
        source=source,
        default_complete=True,
        require_utc_date=False,
    )


def merge_backtest_history(*collections: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for rows in collections:
        for row in rows:
            key = str(row.get("date") or row.get("ts_ms") or "")
            if not key:
                continue
            existing = merged.get(key)
            if existing and existing.get("complete") is True and row.get("complete") is not True:
                continue
            merged[key] = row
    ordered = sorted(merged.values(), key=lambda item: int(item.get("ts_ms") or 0))
    return ordered[-max(int(limit), 1):]


def backtest_market_rows(symbol: str, limit: int, dataset_lineage_id: str = "") -> dict[str, Any]:
    text = (symbol or "BTC-USDT").upper()
    if is_stock_symbol(text):
        payload = read_stock_persistent_candle_cache(text, limit, "1d", "regular")
        if not isinstance(payload, dict) or not payload.get("rows"):
            payload = read_stock_candles(text, limit, "1d", "regular", completed_only=True)
        completed_rows = [
            row for row in payload.get("rows", [])
            if bool(row.get("complete", row.get("confirm", not bool(row.get("provisional")))))
        ]
        rows = [item for item in (normalize_backtest_candle(row) for row in completed_rows) if item]
        source = str(payload.get("origin_source") or payload.get("source") or "futu_stock")
        adjustment = dict(payload.get("adjustment_evidence") or {})
        clean_lineage_id = str(dataset_lineage_id or "").strip()
        accepted_revision = (
            attest_stock_candle_cache(text, "1d", "regular")
            if clean_lineage_id
            else {
                "status": "REVIEW",
                "classification": "INTERACTIVE_CACHE_NOT_ATTESTED",
                "warnings": ["frozen_backtest_required_for_cache_attestation"],
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        )
        dataset_revision = (
            attest_stock_backtest_rows(
                symbol=text,
                provider=source,
                rows=rows,
                adjustment_basis=str(payload.get("adjustment_basis") or ""),
                corporate_actions_hash=str(adjustment.get("corporate_actions_hash") or ""),
                dataset_lineage_id=clean_lineage_id,
            )
            if clean_lineage_id
            else {
                "schema_version": "backtest-dataset-attestation-v1",
                "status": "REVIEW",
                "classification": "INTERACTIVE_DATASET_NOT_FROZEN",
                "warnings": ["dataset_lineage_id_required_for_immutable_freeze"],
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        )
        revision_statuses = {
            str(accepted_revision.get("status") or "PASS"),
            str(dataset_revision.get("status") or "PASS"),
        }
        data_revision_evidence = {
            "status": "BLOCK" if "BLOCK" in revision_statuses else "REVIEW" if "REVIEW" in revision_statuses else "PASS",
            "accepted_cache": accepted_revision,
            "backtest_dataset": dataset_revision,
            "cross_source": stock_data_revision_summary(text).get("latest_cross_source") or [],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        return attach_market_data_envelope({
            "ok": bool(rows),
            "symbol": text,
            "source": source,
            "retrieval_source": payload.get("retrieval_source") or payload.get("source") or source,
            "origin_sources": list(payload.get("origin_sources") or ([source] if source else [])),
            "adjustment_basis": payload.get("adjustment_basis") or "",
            "corporate_action_coverage": payload.get("corporate_action_coverage") or "",
            "corporate_actions": list(payload.get("corporate_actions") or []),
            "adjustment_evidence": adjustment,
            "data_revision_evidence": data_revision_evidence,
            "trading_status_events": list(payload.get("trading_status_events") or []),
            "rows": rows[-limit:],
            "warning": payload.get("warning") or payload.get("error") or "",
        }, symbol=text, timeframe="1D")

    spot_symbol = text.replace("-SWAP", "")
    source_limit = max(int(limit) + 2, 3)
    local_payload: dict[str, Any] = {}
    local_rows: list[dict[str, Any]] = []
    if text == "BTC-USDT":
        local_payload = read_local_btc_daily(source_limit)
        local_rows = [item for item in (normalize_backtest_candle(row) for row in local_payload.get("rows", [])) if item]
    cached = read_market_history_cache(text, source_limit)
    cache_blocked = str(cached.get("status") or "MISSING") == "BLOCK"
    cached_rows = [] if cache_blocked else [
        item for item in (normalize_backtest_candle(row) for row in cached.get("rows", [])) if item
    ]
    base_rows = merge_backtest_history(local_rows, cached_rows, limit=source_limit)
    complete_base_rows = [row for row in base_rows if row.get("complete") is True]
    latest_complete_ts = max(
        (int(row.get("ts_ms") or 0) for row in complete_base_rows),
        default=0,
    )
    stale = latest_complete_ts <= 0 or now_ms() - latest_complete_ts > 3 * 86_400_000
    needs_refresh = len(complete_base_rows) < limit or stale
    inst_id = text if text.endswith("-SWAP") else spot_symbol
    fresh_rows = fetch_okx_daily_history(inst_id, source_limit) if needs_refresh else []
    if fresh_rows:
        upsert_market_history_cache(text, fresh_rows, "okx_history_candles")
    merged_rows = merge_backtest_history(base_rows, fresh_rows, limit=source_limit)
    rows = [row for row in merged_rows if row.get("complete") is True][-limit:]
    source_parts = [str(row.get("source") or "") for row in rows if row.get("source")]
    if not source_parts and rows:
        source_parts.append("completed_market_history")
    warning_parts = [str(local_payload.get("warning") or "")]
    if cache_blocked:
        warning_parts.append("blocked market history cache was excluded")
    if needs_refresh and not fresh_rows:
        warning_parts.append("daily history refresh failed; cached history may be stale")
    source = "+".join(dict.fromkeys(source_parts)) or "okx_history_candles"
    market_history_evidence = build_history_dataset_evidence(
        symbol=text,
        rows=rows,
        source=source,
        dataset_lineage_id=dataset_lineage_id,
        cache_manifest=dict(cached.get("manifest") or {}),
        cache_admitted=bool(cached_rows),
    )
    return attach_market_data_envelope({
        "ok": bool(rows),
        "symbol": text,
        "source": source,
        "path": cached.get("path") or local_payload.get("path", ""),
        "market_history_evidence": market_history_evidence,
        "rows": rows,
        "warning": "; ".join(dict.fromkeys(item for item in warning_parts if item)) if rows else "no market history available",
    }, symbol=text, timeframe="1D")


def chart_candle_payload_row(row: dict[str, Any]) -> dict[str, Any]:
    ts = int(row.get("ts_ms") or row.get("ts") or row.get("time") or 0)
    close = pct(row.get("close", 0.0))
    return {
        "ts": ts,
        "open": pct(row.get("open", close)),
        "high": pct(row.get("high", close)),
        "low": pct(row.get("low", close)),
        "close": close,
        "volume": pct(row.get("volume", row.get("volume_quote", row.get("vol", 0.0)))),
        "complete": row.get("complete", row.get("confirm", not bool(row.get("provisional")))),
    }


def chart_bar_interval_ms(bar: str) -> int:
    mapping = {
        "1m": 60000,
        "5m": 300000,
        "15m": 900000,
        "30m": 1800000,
        "1H": 3600000,
        "4H": 14400000,
        "1D": 86400000,
        "1Dutc": 86400000,
    }
    return mapping.get(str(bar or "1m"), 60000)


def latest_chart_candle_ts(rows: list[dict[str, Any]]) -> int:
    values = [int(row.get("ts") or row.get("ts_ms") or 0) for row in rows or []]
    return max(values) if values else 0


def chart_freshness_fields(
    rows: list[dict[str, Any]],
    bar: str,
    *,
    source: str = "",
    fallback: bool = False,
    tz: timezone = timezone.utc,
) -> dict[str, Any]:
    latest_ts = latest_chart_candle_ts(rows)
    age_ms = max(0, now_ms() - latest_ts) if latest_ts else 0
    interval_ms = chart_bar_interval_ms(bar)
    live_limit_ms = max(interval_ms * 3, 90000)
    source_text = str(source or "").lower()
    preview = source_text in {"offline-seed", "quick_preview_seed", "client_quick_preview", "fallback_history", "local_btc_daily", "local_market_cache"}
    realtime = bool(latest_ts) and not fallback and not preview and age_ms <= live_limit_ms
    latest_at = datetime.fromtimestamp(latest_ts / 1000, tz).strftime("%Y-%m-%d %H:%M") if latest_ts else ""
    return {
        "latest_ts": latest_ts,
        "latest_at": latest_at,
        "data_age_ms": age_ms,
        "realtime": realtime,
    }


def anomaly_data_quality(source: str, market_type: str, *, realtime: bool = False, fallback: bool = False) -> dict[str, Any]:
    source_text = str(source or "").lower()
    if source_text in {"okx", "okx_realtime_candles", "rest"}:
        label = "OKX实时" if realtime else "OKX待确认"
        tone = "up" if realtime else "flat"
    elif source_text == "futu":
        label = "Futu实时" if realtime else "Futu待确认"
        tone = "up" if realtime else "flat"
    elif source_text in {"yahoo", "stooq", "external"}:
        label = f"{source or '外部源'}延迟"
        tone = "flat"
    elif fallback or source_text in {"offline-seed", "local", "local_btc_daily", "stock_sqlite_cache"}:
        label = "本地兜底"
        tone = "down"
        fallback = True
    else:
        label = source or market_type or "未知来源"
        tone = "flat"
    return {
        "status": "READY" if realtime and not fallback else "DEGRADED" if fallback else "DELAYED",
        "source": source or market_type or "",
        "label": label,
        "realtime": bool(realtime),
        "fallback": bool(fallback),
        "tone": tone,
        "priority_eligible": bool(realtime and not fallback),
    }


def quick_preview_price(symbol: str) -> float:
    text = (symbol or "BTC-USDT").upper()
    spot = normalize_crypto_spot(text)
    if spot == "BTC-USDT":
        local = local_btc_candles_for_ai(5)
        if local:
            return float(local[-1]["close"])
    seed = {
        "BTC-USDT": 65000.0,
        "ETH-USDT": 1733.0,
        "DOGE-USDT": 0.076,
        "BTC-USDT-SWAP": 65000.0,
        "ETH-USDT-SWAP": 1733.0,
        "DOGE-USDT-SWAP": 0.076,
    }
    return seed.get(text, seed.get(spot, 1.0))


def synthetic_chart_candles(symbol: str, bar: str, limit: int) -> list[dict[str, Any]]:
    count = int(clamp(float(limit), 80, 300))
    interval = chart_bar_interval_ms(bar)
    base = quick_preview_price(symbol)
    now = now_ms()
    rows: list[dict[str, Any]] = []
    for index in range(count):
        phase = index / max(count - 1, 1)
        wave = math.sin(phase * math.pi * 6) * 0.006 + math.cos(phase * math.pi * 2) * 0.004
        drift = (phase - 0.5) * 0.018
        close = base * (1 + wave + drift)
        open_price = base * (1 + math.sin(max(index - 1, 0) / max(count - 1, 1) * math.pi * 6) * 0.006 + ((max(index - 1, 0) / max(count - 1, 1)) - 0.5) * 0.018)
        high = max(open_price, close) * 1.003
        low = min(open_price, close) * 0.997
        rows.append({
            "ts": now - (count - index) * interval,
            "open": round(open_price, 8),
            "high": round(high, 8),
            "low": round(low, 8),
            "close": round(close, 8),
            "volume": round(1000 + 180 * abs(math.sin(phase * math.pi * 8)), 4),
        })
    return rows


def local_chart_candles(symbol: str, limit: int) -> dict[str, Any] | None:
    text = (symbol or "BTC-USDT").upper()
    spot_symbol = normalize_crypto_spot(text)
    if spot_symbol == "BTC-USDT":
        payload = read_local_btc_daily(max(limit, 300))
        rows = [chart_candle_payload_row(item) for item in (normalize_backtest_candle(row) for row in payload.get("rows", [])) if item]
        rows = [row for row in rows if row.get("close", 0) > 0]
        if rows:
            return {
                "ok": True,
                "symbol": text,
                "bar": "1Dutc",
                "source": payload.get("source", "local_btc_daily"),
                "path": payload.get("path", ""),
                "rows": rows[-limit:],
                "warning": payload.get("warning", ""),
                "updated_at": now_ms(),
            }
    cached = read_market_history_cache(text, max(limit, 300))
    rows = [chart_candle_payload_row(item) for item in (normalize_backtest_candle(row) for row in cached.get("rows", [])) if item]
    rows = [row for row in rows if row.get("close", 0) > 0]
    if rows:
        return {
            "ok": True,
            "symbol": text,
            "bar": "1Dutc",
            "source": cached.get("source", "local_market_cache"),
            "path": cached.get("path", ""),
            "rows": rows[-limit:],
            "warning": "",
            "updated_at": now_ms(),
        }
    return None


def legacy_market_chart_candles(symbol: str, bar: str = "1m", limit: int = 300, fast: bool = False) -> dict[str, Any]:
    text = (symbol or "BTC-USDT").upper()
    clean_bar = str(bar or "1m")
    clean_limit = int(clamp(float(limit), 30, 1000))
    warnings: list[str] = []

    if is_stock_symbol(text):
        interval = "1d" if clean_bar in {"1D", "1Dutc"} else clean_bar
        payload = read_stock_candles(text, clean_limit, interval, "all", fast)
        rows = [chart_candle_payload_row({"ts_ms": row.get("ts"), **row}) for row in payload.get("rows", [])]
        return {
            "ok": bool(rows),
            "symbol": text,
            "bar": payload.get("interval", interval),
            "source": payload.get("source", "stock"),
            "cached": bool(payload.get("cached")),
            "cache_age_ms": payload.get("cache_age_ms", 0),
            "rows": rows[-clean_limit:],
            "warning": payload.get("warning") or payload.get("error") or "",
            "updated_at": now_ms(),
        }

    local_payload = local_chart_candles(text, clean_limit)
    if local_payload:
        return local_payload
    if fast:
        return {
            "ok": True,
            "symbol": text,
            "bar": clean_bar,
            "source": "quick_preview_seed",
            "rows": synthetic_chart_candles(text, clean_bar, min(clean_limit, 180)),
            "warning": "快速预览K线，等待真实K线或历史缓存；仅用于避免切换空白，不用于分析。",
            "updated_at": now_ms(),
        }

    inst_id = text
    try:
        payload = read_bodyless_okx("/api/v5/market/candles", {
            "instId": inst_id,
            "bar": clean_bar,
            "limit": str(clean_limit),
        })
        raw_rows = payload.get("data") or []
        rows = [chart_candle_payload_row(item) for item in (normalize_backtest_candle(row) for row in reversed(raw_rows)) if item]
        rows = [row for row in rows if row.get("close", 0) > 0]
        if rows:
            return {
                "ok": True,
                "symbol": text,
                "bar": clean_bar,
                "source": "okx_realtime_candles",
                "rows": rows[-clean_limit:],
                "warning": "",
                "updated_at": now_ms(),
            }
        warnings.append("OKX returned no candles")
    except Exception as exc:
        warnings.append(f"OKX candles failed: {exc}")

    fallback = backtest_market_rows(text, max(clean_limit, 300))
    rows = [chart_candle_payload_row(item) for item in (normalize_backtest_candle(row) for row in fallback.get("rows", [])) if item]
    rows = [row for row in rows if row.get("close", 0) > 0]
    return {
        "ok": bool(rows),
        "symbol": text,
        "bar": "1Dutc" if rows else clean_bar,
        "source": fallback.get("source", "fallback_history"),
        "rows": rows[-clean_limit:],
        "warning": "; ".join([*warnings, fallback.get("warning", "")]).strip("; ") or "no chart candles available",
        "updated_at": now_ms(),
    }


def market_chart_candles(symbol: str, bar: str = "1m", limit: int = 300, fast: bool = False, session: str = "all", force: bool = False) -> dict[str, Any]:
    text = (symbol or "BTC-USDT").upper()
    clean_bar = str(bar or "1m")
    clean_session = str(session or "all")
    clean_limit = int(clamp(float(limit), 30, 1000))
    warnings: list[str] = []

    if is_stock_symbol(text):
        interval = "1d" if clean_bar in {"1D", "1Dutc"} else clean_bar
        payload = read_stock_candles(text, clean_limit, interval, clean_session, fast, force)
        payload_rows = list(payload.get("rows") or [])
        rows = [chart_candle_payload_row({"ts_ms": row.get("ts"), **row}) for row in payload_rows]
        candle_source = payload.get("origin_source") or payload.get("source") or "stock"
        candle_quality = analyze_stock_candle_series(
            payload_rows,
            symbol=text,
            interval=interval,
            source=candle_source,
            schedule_attestation=resolve_stock_candle_schedule_attestation(
                benchmark_symbol=text,
                source=candle_source,
                rows=payload_rows,
            ),
            minimum_analysis_rows=20,
        ) if interval in {"1d", "1dutc"} else {}
        warning_parts = [str(payload.get("warning") or payload.get("error") or "")]
        if candle_quality.get("status") in {"BLOCK", "REVIEW"}:
            warning_parts.append(str(candle_quality.get("warning") or "日线价格尺度断点待核"))
        warning = " / ".join(dict.fromkeys(item for item in warning_parts if item))
        fallback = payload.get("source") in {"offline-seed", "stock_sqlite_cache", "quote_preview_seed"}
        revision_summary = stock_data_revision_summary(text)
        return {
            "ok": bool(rows),
            "symbol": text,
            "bar": payload.get("interval", interval),
            "session": payload.get("session", normalize_stock_history_session(interval, clean_session)),
            "session_label": payload.get("session_label", stock_session_label(normalize_stock_history_session(interval, clean_session))),
            "source": payload.get("source", "stock"),
            "cached": bool(payload.get("cached")),
            "cache_age_ms": payload.get("cache_age_ms", 0),
            "latest_ts": payload.get("latest_ts", 0),
            "latest_at": payload.get("latest_at", ""),
            "data_age_ms": payload.get("data_age_ms", 0),
            "realtime": bool(payload.get("realtime")),
            "in_progress": bool(payload.get("in_progress")),
            "rows": rows[-clean_limit:],
            "warning": warning,
            "fallback": fallback,
            "candle_quality": stock_candle_quality_public(candle_quality) if candle_quality else {},
            "adjustment_basis": payload.get("adjustment_basis") or "",
            "adjustment_evidence": dict(payload.get("adjustment_evidence") or {}),
            "data_revision_evidence": dict(payload.get("data_revision_evidence") or revision_summary),
            "corporate_action_count": len(payload.get("corporate_actions") or []),
            "updated_at": now_ms(),
        }

    try:
        payload = read_bodyless_okx("/api/v5/market/candles", {
            "instId": text,
            "bar": clean_bar,
            "limit": str(clean_limit),
        })
        raw_rows = payload.get("data") or []
        rows = [chart_candle_payload_row(item) for item in (normalize_backtest_candle(row) for row in reversed(raw_rows)) if item]
        rows = [row for row in rows if row.get("close", 0) > 0]
        if rows:
            chart_rows = rows[-clean_limit:]
            return {
                "ok": True,
                "symbol": text,
                "bar": clean_bar,
                "source": "okx_realtime_candles",
                "rows": chart_rows,
                "warning": "",
                "fallback": False,
                **chart_freshness_fields(chart_rows, clean_bar, source="okx_realtime_candles", fallback=False),
                "updated_at": now_ms(),
            }
        warnings.append("OKX returned no candles")
    except Exception as exc:
        warnings.append(f"OKX candles failed: {exc}")

    if fast:
        preview_rows = synthetic_chart_candles(text, clean_bar, min(clean_limit, 180))
        return {
            "ok": True,
            "symbol": text,
            "bar": clean_bar,
            "source": "quick_preview_seed",
            "rows": preview_rows,
            "warning": "OKX realtime candles unavailable; showing quick preview only.",
            "fallback": True,
            **chart_freshness_fields(preview_rows, clean_bar, source="quick_preview_seed", fallback=True),
            "updated_at": now_ms(),
        }

    local_payload = local_chart_candles(text, clean_limit)
    if local_payload:
        local_rows = local_payload.get("rows") or []
        local_bar = str(local_payload.get("bar") or clean_bar)
        local_source = str(local_payload.get("source") or "local_market_cache")
        return {
            **local_payload,
            "warning": "; ".join([*warnings, local_payload.get("warning", ""), "fallback local history"]).strip("; "),
            "fallback": True,
            **chart_freshness_fields(local_rows, local_bar, source=local_source, fallback=True),
        }

    fallback = backtest_market_rows(text, max(clean_limit, 300))
    rows = [chart_candle_payload_row(item) for item in (normalize_backtest_candle(row) for row in fallback.get("rows", [])) if item]
    rows = [row for row in rows if row.get("close", 0) > 0]
    chart_rows = rows[-clean_limit:]
    fallback_bar = "1Dutc" if rows else clean_bar
    fallback_source = str(fallback.get("source", "fallback_history"))
    return {
        "ok": bool(rows),
        "symbol": text,
        "bar": fallback_bar,
        "source": fallback_source,
        "rows": chart_rows,
        "warning": "; ".join([*warnings, fallback.get("warning", "")]).strip("; ") or "no chart candles available",
        "fallback": True,
        **chart_freshness_fields(chart_rows, fallback_bar, source=fallback_source, fallback=True),
        "updated_at": now_ms(),
    }


def equity_segment_report(equity_curve: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(equity_curve) < 30:
        return []
    labels = ["前段", "中段", "近段"]
    size = max(1, len(equity_curve) // 3)
    segments = [
        equity_curve[:size],
        equity_curve[size:size * 2],
        equity_curve[size * 2:],
    ]
    result = []
    for label, segment in zip(labels, segments):
        values = [float(item.get("equity") or 0) for item in segment if float(item.get("equity") or 0) > 0]
        if len(values) < 2:
            continue
        return_pct = (values[-1] / values[0] - 1) * 100
        drawdown_pct = max_drawdown(values) * 100
        result.append({
            "name": label,
            "start": segment[0].get("date", ""),
            "end": segment[-1].get("date", ""),
            "return_pct": round(return_pct, 2),
            "drawdown_pct": round(drawdown_pct, 2),
            "sharpe": round(sharpe_ratio(values), 2),
            "status": "PASS" if return_pct > 0 and drawdown_pct < 18 else "WATCH" if drawdown_pct < 28 else "BLOCK",
        })
    return result


def backtest_score(item: dict[str, Any]) -> float:
    if not item.get("ok"):
        return -9999.0
    trade_penalty = 8.0 if int(item.get("trade_count") or 0) == 0 else 0.0
    return (
        float(item.get("total_return_pct") or 0) * 0.55
        + float(item.get("annualized_pct") or 0) * 0.25
        + float(item.get("win_rate_pct") or 0) * 0.06
        + float(item.get("sharpe") or 0) * 4.0
        - float(item.get("max_drawdown_pct") or 0) * 1.15
        - trade_penalty
    )


def backtest_risk_label(item: dict[str, Any]) -> str:
    drawdown = float(item.get("max_drawdown_pct") or 0)
    leverage = float(item.get("leverage") or 1)
    if drawdown >= 30 or leverage >= 5:
        return "高风险"
    if drawdown >= 16 or leverage >= 3:
        return "中风险"
    return "低风险"


def run_strategy_backtest(
    strategy_id: str,
    position_pct: float,
    take_profit_pct: float,
    stop_loss_pct: float,
    leverage: float,
    limit: int = 1600,
    symbol: str = "BTC-USDT",
    market_payload: dict[str, Any] | None = None,
    fee_rate: float = 0.0005,
    slippage_bps: float = 2.0,
    evaluation_start_index: int | None = None,
    strategy_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    capability = strategy_validation_capability(strategy_id)
    if not capability.get("backtest_supported"):
        return {
            "ok": False,
            "error": capability.get("blocker") or "Strategy is not supported by the causal backtest engine.",
            "strategy_id": strategy_id,
            "validation_capability": capability,
            "execution_model": EXECUTION_MODEL_VERSION,
        }
    payload = market_payload or backtest_market_rows(symbol, limit)
    source = str(payload.get("source") or "")
    strategy = choose_strategy(strategy_id)
    bound_params = dict(strategy_params) if isinstance(strategy_params, dict) else dict(strategy.get("params") or {})
    report = run_causal_long_only_backtest(
        rows=list(payload.get("rows") or []),
        symbol=symbol,
        source=source,
        signal_fn=build_strategy_signal_fn(strategy_id, bound_params),
        position_pct=position_pct,
        take_profit_pct=take_profit_pct,
        stop_loss_pct=stop_loss_pct,
        startup_candles=strategy_startup_candles(strategy_id, bound_params),
        fee_rate=fee_rate,
        slippage_bps=slippage_bps,
        leverage=leverage,
        market="stock" if is_stock_symbol(symbol) else "crypto",
        timeframe=str(payload.get("bar") or "1D"),
        evaluation_start_index=evaluation_start_index,
        signal_input=strategy_signal_input(strategy_id),
    )
    report.update({
        "data_warning": payload.get("warning", ""),
        "strategy": {**strategy, "params": bound_params},
        "position_pct": round(position_pct, 2),
        "take_profit_pct": round(take_profit_pct, 2),
        "stop_loss_pct": round(stop_loss_pct, 2),
        "leverage": round(leverage, 2),
    })
    if not report.get("ok"):
        return report
    full_trades = list(report.get("trades") or [])
    full_curve = list(report.get("equity_curve") or [])
    report["segments"] = equity_segment_report(full_curve)
    report["risk_label"] = backtest_risk_label(report)
    report["trades"] = full_trades[-24:]
    report["equity_curve"] = full_curve[-240:]
    return report


def strategy_temporal_validation_report(
    *,
    strategy_id: str,
    symbol: str,
    rows: list[dict[str, Any]],
    source: str,
    position_pct: float,
    take_profit_pct: float,
    stop_loss_pct: float,
    leverage: float,
    baseline: dict[str, Any],
    strategy_params: dict[str, Any] | None = None,
    train_end_index: int | None = None,
    validation_end_index: int | None = None,
) -> dict[str, Any]:
    validation_rows = [
        dict(row) for row in rows
        if bool(row.get("complete", row.get("confirm", not bool(row.get("provisional")))))
    ]
    split = temporal_data_split(
        validation_rows,
        train_ratio=0.50,
        validation_ratio=0.25,
        minimum_segment_rows=120,
        train_end_index=train_end_index,
        validation_end_index=validation_end_index,
    )
    segment_reports: dict[str, dict[str, Any]] = {}
    blockers = list(split.get("blockers") or [])
    for name, segment_rows in (split.get("rows") or {}).items():
        segment_meta = (split.get("segments") or {}).get(name) or {}
        start_index = int(segment_meta.get("start_index") or 0)
        end_index = int(segment_meta.get("end_index") or 0)
        context_rows = validation_rows[:end_index]
        report = run_strategy_backtest(
            strategy_id,
            position_pct,
            take_profit_pct,
            stop_loss_pct,
            leverage,
            len(context_rows),
            symbol,
            {"rows": context_rows, "source": f"{source}:{name}"},
            evaluation_start_index=start_index if start_index > 0 else None,
            strategy_params=strategy_params,
        )
        segment_reports[name] = report
        if not report.get("ok"):
            blockers.append(f"{name} segment backtest failed")
    for name in ("validation", "test"):
        report = segment_reports.get(name) or {}
        if int(report.get("trade_count") or 0) < 2:
            blockers.append(f"{name} segment has fewer than 2 closed trades")
        if float(report.get("total_return_pct") or 0.0) <= 0:
            blockers.append(f"{name} segment return is not positive")
        if float(report.get("max_drawdown_pct") or 100.0) >= 25:
            blockers.append(f"{name} segment drawdown exceeds 25%")

    fold_definition = chronological_folds(validation_rows, fold_count=3, minimum_fold_rows=120)
    fold_reports: list[dict[str, Any]] = []
    for fold in fold_definition.get("folds") or []:
        fold_rows = list(fold.get("rows") or [])
        fold_start = int(fold.get("start_index") or 0)
        fold_end = int(fold.get("end_index") or 0)
        context_rows = validation_rows[:fold_end]
        report = run_strategy_backtest(
            strategy_id,
            position_pct,
            take_profit_pct,
            stop_loss_pct,
            leverage,
            len(context_rows),
            symbol,
            {"rows": context_rows, "source": f"{source}:fold-{fold.get('fold')}"},
            evaluation_start_index=fold_start if fold_start > 0 else None,
            strategy_params=strategy_params,
        )
        fold_reports.append({
            "fold": fold.get("fold"),
            "start": fold.get("start"),
            "end": fold.get("end"),
            "count": fold.get("count"),
            "ok": bool(report.get("ok")),
            "total_return_pct": report.get("total_return_pct"),
            "max_drawdown_pct": report.get("max_drawdown_pct"),
            "trade_count": report.get("trade_count"),
            "sharpe": report.get("sharpe"),
        })
    walk_forward = summarize_walk_forward(fold_reports)
    if fold_definition.get("status") == "BLOCK":
        walk_forward["status"] = "BLOCK"
        walk_forward["blockers"] = list(dict.fromkeys([
            *list(walk_forward.get("blockers") or []),
            *list(fold_definition.get("blockers") or []),
        ]))

    cost_scenarios: list[dict[str, Any]] = []
    for name, fee_rate, slippage_bps in (
        ("normal", 0.0005, 2.0),
        ("stressed", 0.0010, 8.0),
        ("severe", 0.0015, 15.0),
    ):
        report = run_strategy_backtest(
            strategy_id,
            position_pct,
            take_profit_pct,
            stop_loss_pct,
            leverage,
            len(validation_rows),
            symbol,
            {"rows": validation_rows, "source": f"{source}:cost-{name}"},
            fee_rate=fee_rate,
            slippage_bps=slippage_bps,
            strategy_params=strategy_params,
        )
        cost_scenarios.append({
            "name": name,
            "fee_rate": fee_rate,
            "slippage_bps": slippage_bps,
            "ok": bool(report.get("ok")),
            "total_return_pct": report.get("total_return_pct"),
            "max_drawdown_pct": report.get("max_drawdown_pct"),
            "trade_count": report.get("trade_count"),
        })
    cost_sensitivity = summarize_cost_sensitivity(baseline, cost_scenarios)
    temporal_status = "PASS" if not blockers else "BLOCK"
    split_public = {key: value for key, value in split.items() if key != "rows"}
    return {
        "status": "PASS" if temporal_status == "PASS" and walk_forward.get("status") == "PASS" and cost_sensitivity.get("status") == "PASS" else "BLOCK",
        "data_split": split_public,
        "temporal_segments": segment_reports,
        "temporal_status": temporal_status,
        "temporal_blockers": list(dict.fromkeys(blockers)),
        "walk_forward": walk_forward,
        "cost_sensitivity": cost_sensitivity,
    }


def strategy_backtest_report(query: dict[str, str], *, dataset_lineage_id: str = "") -> dict[str, Any]:
    symbol = query.get("symbol", "BTC-USDT")
    strategy_id = query.get("strategy", "dual_ma")
    capability = strategy_validation_capability(strategy_id)
    if not capability.get("known"):
        raise ValueError("未知策略，禁止隐式降级到其他信号实现。")
    if not capability.get("backtest_supported"):
        raise ValueError(str(capability.get("blocker") or "当前策略尚未完成因果回测模型。"))
    direction_mode = str(query.get("directionMode", "LONG_ONLY") or "LONG_ONLY").upper()
    if direction_mode != "LONG_ONLY":
        raise ValueError("当前因果回测内核仅支持 LONG_ONLY；做空模型尚未完成独立验证。")
    position_pct = clamp(pct(query.get("positionPct", "35")), 1, 100)
    take_profit_pct = clamp(pct(query.get("takeProfitPct", "2.4")), 0, 80)
    stop_loss_pct = clamp(pct(query.get("stopLossPct", "1.2")), 0, 80)
    leverage = clamp(pct(query.get("leverage", "1")), 1, 10)
    limit = int(clamp(pct(query.get("limit", "1600")), 160, 5000))
    market_payload = backtest_market_rows(symbol, limit, dataset_lineage_id=dataset_lineage_id)
    strategy = choose_strategy(strategy_id)
    strategy_params = dict(strategy.get("params") or {})
    implementation_fingerprint = strategy_implementation_fingerprint(strategy_id, strategy_params)
    backtest_params = {
        "strategy_params": strategy.get("params", {}),
        "position_pct": round(position_pct, 4),
        "take_profit_pct": round(take_profit_pct, 4),
        "stop_loss_pct": round(stop_loss_pct, 4),
        "leverage": round(leverage, 4),
        "direction_mode": direction_mode,
        "limit": limit,
        "fee_rate": 0.0005,
        "slippage_bps": 2.0,
    }
    reproducibility = backtest_reproducibility(
        symbol=symbol,
        strategy_id=strategy_id,
        params=backtest_params,
        market_payload=market_payload,
        fee_rate=0.0005,
        slippage_bps=2.0,
        strategy_fingerprint=implementation_fingerprint,
        execution_model=EXECUTION_MODEL_VERSION,
    )
    data_admission = build_strategy_data_admission(
        market_payload=market_payload,
        dataset_manifest=reproducibility.get("dataset_manifest") or {},
        dataset_lineage_id=dataset_lineage_id,
        market="stock" if is_stock_symbol(symbol) else "crypto",
        generated_at=now_ms(),
    )
    prefix_invariance = causal_prefix_invariance_check(
        rows=list(market_payload.get("rows") or []),
        symbol=symbol,
        source=str(market_payload.get("source") or "unknown"),
        signal_factory=lambda _rows: build_strategy_signal_fn(strategy_id, strategy_params),
        position_pct=position_pct,
        take_profit_pct=take_profit_pct,
        stop_loss_pct=stop_loss_pct,
        startup_candles=strategy_startup_candles(strategy_id, strategy_params),
        fee_rate=0.0005,
        slippage_bps=2.0,
        leverage=leverage,
        market="stock" if is_stock_symbol(symbol) else "crypto",
        timeframe=str(market_payload.get("bar") or "1D"),
        signal_input=strategy_signal_input(strategy_id),
    )
    lookahead = strategy_lookahead_check(
        strategy,
        candle_count=len(market_payload.get("rows") or []),
        startup_candles=strategy_startup_candles(strategy_id, strategy_params),
        rows=market_payload.get("rows") or [],
        prefix_invariance=prefix_invariance,
    )
    matrix_evidence = latest_strategy_matrix_evidence(
        Path(RUNTIME_DIR) / "reports",
        strategy_id=strategy_id,
        strategy_params=strategy_params,
        implementation_fingerprint=implementation_fingerprint,
        risk={
            "position_pct": float(position_pct),
            "take_profit_pct": float(take_profit_pct),
            "stop_loss_pct": float(stop_loss_pct),
            "fee_rate": 0.0005,
            "slippage_bps": 2.0,
            "leverage": float(leverage),
        },
        symbol=symbol,
        now_ms=now_ms(),
    )
    if not market_payload.get("rows"):
        acceptance = backtest_acceptance_report({"ok": False, "trade_count": 0}, [], reproducibility)
        return {
            "ok": False,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
            "error": f"{symbol} 历史数据不足或数据源暂不可用",
            "symbol": symbol,
            "source": market_payload.get("source", ""),
            "data_points": 0,
            "data_warning": market_payload.get("warning", ""),
            "current": {"ok": False, "error": "历史数据不足"},
            "candidates": [],
            "optimizer": {"notes": []},
            "risk_control_surface": build_backtest_risk_control_surface([]),
            "segments": [],
            "reproducibility": reproducibility,
            "dataset_manifest": reproducibility.get("dataset_manifest", {}),
            "execution_model": EXECUTION_MODEL_VERSION,
            "lookahead_check": lookahead,
            "selection_evidence": matrix_evidence,
            "data_admission": data_admission,
            "acceptance": acceptance,
            "temporal_validation": {
                "status": "BLOCK",
                "data_split": {"status": "BLOCK", "blockers": ["历史数据不足"]},
                "temporal_status": "BLOCK",
                "temporal_blockers": ["历史数据不足"],
                "walk_forward": {"status": "BLOCK", "blockers": ["历史数据不足"]},
                "cost_sensitivity": {"status": "BLOCK", "blockers": ["历史数据不足"]},
            },
            "release_pipeline": strategy_release_pipeline(
                doctor_score=0,
                lookahead=lookahead,
                backtest_acceptance=acceptance,
                temporal_validation={"status": "BLOCK"},
                selection_evidence=matrix_evidence,
                data_admission=data_admission,
                live_hard_block=LIVE_TRADING_HARD_BLOCK,
            ),
        }
    current = run_strategy_backtest(
        strategy_id, position_pct, take_profit_pct, stop_loss_pct, leverage,
        limit, symbol, market_payload, strategy_params=strategy_params,
    )
    candidates = []
    for pos in BACKTEST_RISK_CONTROL_GRID["position_pct"]:
        for take in BACKTEST_RISK_CONTROL_GRID["take_profit_pct"]:
            for stop in BACKTEST_RISK_CONTROL_GRID["stop_loss_pct"]:
                item = run_strategy_backtest(
                    strategy_id, pos, take, stop, leverage,
                    limit, symbol, market_payload, strategy_params=strategy_params,
                )
                if not item.get("ok"):
                    continue
                score = backtest_score(item)
                candidates.append({**item, "score": round(score, 2), "risk_label": backtest_risk_label(item)})
    candidates.sort(key=lambda item: item["score"], reverse=True)
    best = candidates[0] if candidates else {}
    safest = sorted(candidates, key=lambda item: (item["max_drawdown_pct"], -item["total_return_pct"]))[0] if candidates else {}
    highest_return = sorted(candidates, key=lambda item: item["total_return_pct"], reverse=True)[0] if candidates else {}
    current_score = round(backtest_score(current), 2) if current.get("ok") else 0.0
    current_rank = len([item for item in candidates if item.get("score", -9999) > current_score]) + 1 if current.get("ok") else 0
    notes = []
    if best:
        notes.append(f"开发期最高评分单元：仓位 {best['position_pct']}%，止盈 {best['take_profit_pct']}%，止损 {best['stop_loss_pct']}%，评分 {best['score']}；同数据比较，不构成选参。")
    if safest and safest != best:
        notes.append(f"开发期最低回撤单元：仓位 {safest['position_pct']}%，最大回撤 {safest['max_drawdown_pct']}%；未做样本外确认。")
    if highest_return and highest_return != best:
        notes.append(f"开发期最高收益单元：仓位 {highest_return['position_pct']}%，收益 {highest_return['total_return_pct']}%；选择偏差未校正。")
    if current.get("ok") and best:
        gap = float(best.get("score") or 0) - current_score
        notes.append(f"当前风险控制组合的开发期分位约第 {current_rank}，与网格最高开发期分差 {gap:.2f}；策略信号参数未参与该网格。")
    acceptance = backtest_acceptance_report(current, candidates, reproducibility)
    temporal_validation = strategy_temporal_validation_report(
        strategy_id=strategy_id,
        symbol=symbol,
        rows=list(market_payload.get("rows") or []),
        source=str(market_payload.get("source") or "unknown"),
        position_pct=position_pct,
        take_profit_pct=take_profit_pct,
        stop_loss_pct=stop_loss_pct,
        leverage=leverage,
        baseline=current,
        strategy_params=strategy_params,
    )
    return {
        "ok": True,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
        "symbol": symbol,
        "source": market_payload.get("source", ""),
        "data_points": int(reproducibility.get("data_points") or 0),
        "data_warning": market_payload.get("warning", ""),
        "current": current,
        "candidates": candidates[:10],
        "optimizer": {
            "best": best,
            "safest": safest,
            "highest_return": highest_return,
            "current_score": current_score,
            "current_rank": current_rank,
            "grid_count": len(candidates),
            "notes": notes,
        },
        "risk_control_surface": build_backtest_risk_control_surface(candidates),
        "segments": current.get("segments", []) if current.get("ok") else [],
        "reproducibility": reproducibility,
        "dataset_manifest": current.get("dataset_manifest") or reproducibility.get("dataset_manifest", {}),
        "execution_model": current.get("execution_model") or EXECUTION_MODEL_VERSION,
        "lookahead_check": lookahead,
        "selection_evidence": matrix_evidence,
        "data_admission": data_admission,
        "acceptance": acceptance,
        "temporal_validation": temporal_validation,
        "release_pipeline": strategy_release_pipeline(
            doctor_score=acceptance.get("score", 0),
            lookahead=lookahead,
            backtest_acceptance=acceptance,
            temporal_validation=temporal_validation,
            selection_evidence=matrix_evidence,
            data_admission=data_admission,
            live_hard_block=LIVE_TRADING_HARD_BLOCK,
        ),
    }


def strategy_implementation_fingerprint(strategy_id: str, strategy_params: dict[str, Any] | None = None) -> str:
    strategy = next((item for item in STRATEGIES if item["id"] == strategy_id), None)
    if strategy is None:
        return ""
    return strategy_signal_fingerprint(strategy_id, {
        "strategy": {**strategy, "params": dict(strategy_params) if isinstance(strategy_params, dict) else dict(strategy.get("params") or {})},
        "terminal_version": TERMINAL_VERSION,
        "execution_model": EXECUTION_MODEL_VERSION,
        "causal_audit": CAUSAL_AUDIT_VERSION,
    })


def okx_first(path: str, query: dict[str, str]) -> dict[str, Any]:
    return okx_first_io(path, query)


def okx_rows(path: str, query: dict[str, str]) -> list[Any]:
    return okx_rows_io(path, query)


PUBLIC_INSTRUMENT_RULES = PublicInstrumentRuleService(
    fetch_payload=read_bodyless_okx,
    now_ms=now_ms,
)
PUBLIC_ORDER_BOOK = PublicOrderBookService(
    fetch_payload=read_bodyless_okx,
    now_ms=now_ms,
)


MARKET_DATA_SERVICE = MarketDataService(
    now_ms=now_ms,
    pct=pct,
    is_stock_symbol=is_stock_symbol,
    read_stock_quote=read_stock_quote,
    stock_data_sources_snapshot=stock_data_sources_snapshot,
    market_chart_candles=market_chart_candles,
    okx_first=okx_first,
    read_crypto_quotes=lambda: okx_rows("/api/v5/market/tickers", {"instType": "SPOT"}),
    read_stock_quotes=lambda force=False: read_stock_quotes_cached(0 if force else 180000, fast=not force),
    read_fast_stock_quote=lambda symbol: _stock_quote_from_cache(symbol),
    publish_event=lambda event_type, payload: record_runtime_audit({"type": event_type, **payload}),
)


def market_data_snapshot(
    symbol: str,
    bar: str = "1m",
    limit: int = 300,
    session: str = "all",
    fast: bool = False,
    force: bool = False,
    emit_event: bool = False,
    consumer: str = "unspecified",
) -> dict[str, Any]:
    return MARKET_DATA_SERVICE.snapshot(
        symbol,
        bar=bar,
        limit=limit,
        session=session,
        fast=fast,
        force=force,
        emit_event=emit_event,
        consumer=consumer,
    )


def market_data_snapshot_health(
    symbol: str = "",
    bar: str = "",
    session: str = "",
) -> dict[str, Any]:
    health = MARKET_DATA_SERVICE.health(symbol, bar=bar, session=session)
    return build_market_data_health_projection(
        health,
        runtime_read_only=RUNTIME_READ_ONLY,
        live_trading_hard_block=LIVE_TRADING_HARD_BLOCK,
    )


def paper_market_cycle_snapshot(symbol: str, source: str = "paper_cycle") -> dict[str, Any]:
    text = str(symbol or "").strip().upper()
    stock = is_stock_symbol(text)
    bar = "1D" if stock else "1Dutc"
    snapshot = market_data_snapshot(
        text,
        bar=bar,
        limit=300,
        session="all",
        fast=False,
        force=False,
        emit_event=True,
        consumer=source,
    )
    quote = dict(snapshot.get("quote") or {})
    candles = dict(snapshot.get("candles") or {})
    quality = dict(snapshot.get("data_quality") or {})
    market_session = dict(snapshot.get("market_session") or {})
    rows = [
        item for item in (normalize_backtest_candle(row) for row in candles.get("rows") or [])
        if item
    ]
    complete_rows = [
        row for row in rows
        if row.get("complete_attested") is True and row.get("complete") is True
    ]
    dataset = prepare_backtest_dataset(
        complete_rows,
        symbol=text,
        source=str(candles.get("source") or ""),
        timeframe=bar,
        minimum_rows=strategy_startup_candles(PAPER_ACCOUNT.strategy_id) + 2,
        market="stock" if stock else "crypto",
    )
    fallback = quality.get("fallback") is not False
    quarantined = quality.get("quarantined") is not False
    clock_data_allowed = dataset.get("status") == "PASS" and not fallback and not quarantined
    execution_ready = (
        clock_data_allowed
        and quality.get("realtime") is True
        and (not stock or market_session.get("execution_eligible") is True)
    )
    return {
        "ok": snapshot.get("ok") is True and pct(quote.get("last", 0.0)) > 0,
        "symbol": text,
        "price": pct(quote.get("last", 0.0)),
        "rows": rows if clock_data_allowed else [],
        "source": str(candles.get("source") or quote.get("source") or "unknown"),
        "execution_ready": execution_ready,
        "clock_data_allowed": clock_data_allowed,
        "dataset_manifest": dataset.get("manifest") or {},
        "data_quality": quality,
        "market_session": market_session,
        "snapshot_id": str((snapshot.get("context") or {}).get("snapshot_id") or ""),
    }


def market_quote_batch(
    symbols: list[str],
    force: bool = False,
    consumer: str = "market_radar",
) -> dict[str, Any]:
    return MARKET_DATA_SERVICE.quote_batch(
        symbols,
        force=force,
        consumer=consumer,
    )


def market_adapter_status() -> dict[str, Any]:
    return build_market_adapter_catalog(data_reliability_center(), now_ms=now_ms)


def stock_market_insights(symbol: str, write_notification: bool = False) -> dict[str, Any]:
    quote = read_stock_quote(symbol)
    candles = read_stock_candles(symbol, 80).get("rows", [])
    closes = [float(row.get("close") or 0) for row in candles if float(row.get("close") or 0) > 0]
    last = float(quote.get("last") or (closes[-1] if closes else 0))
    trend = (average(closes[-12:]) / max(average(closes[-48:]), 1e-9) - 1) * 100 if len(closes) >= 48 else 0.0
    high = max([float(row.get("high") or 0) for row in candles[-20:]] or [0])
    low = min([float(row.get("low") or 0) for row in candles[-20:] if float(row.get("low") or 0) > 0] or [0])
    range_pct = (high / max(low, 1e-9) - 1) * 100 if high > 0 and low > 0 else 0.0
    change = float(quote.get("change24h_pct") or 0)
    score = clamp(52 + trend * 2 + change * 1.2 - min(range_pct, 18) * 0.45, 0, 100)
    bias = "偏多" if trend > 1.0 or change > 1.5 else "偏空" if trend < -1.0 or change < -1.5 else "震荡"
    alerts = [
        {"level": "INFO", "tag": "股票", "title": f"{symbol} 股票行情", "body": f"最新 {last:.2f} USD，日内变化 {change:.2f}%"},
        {"level": "INFO" if abs(trend) < 3 else "WARN", "tag": "趋势", "title": "近 48 日趋势", "body": f"{trend:.2f}%"},
        {"level": "INFO" if range_pct < 10 else "WARN", "tag": "波动", "title": "20 日区间振幅", "body": f"{range_pct:.2f}%"},
    ]
    if write_notification:
        PROFILE.notify("INFO", "股票观察", f"{symbol} {bias}，最新 {last:.2f}，评分 {score:.1f}")
    return {
        "ok": True,
        "symbol": symbol,
        "market_type": "stock",
        "bias": bias,
        "score": round(score, 1),
        "summary": "股票内容当前用于研究、观察和策略回测准备，不接入真实股票下单。",
        "metrics": {
            "trend12h_pct": round(trend, 2),
            "range24h_pct": round(range_pct, 2),
            "funding_rate_pct": 0.0,
            "open_interest": 0.0,
            "mark_index_basis_pct": 0.0,
            "spot_swap_basis_pct": 0.0,
            "volume_ratio": 0.0,
        },
        "alerts": alerts,
    }


def market_insights(symbol: str, write_notification: bool = False) -> dict[str, Any]:
    write_notification = bool(write_notification and not RUNTIME_READ_ONLY)
    if is_stock_symbol(symbol):
        return stock_market_insights(symbol, write_notification)
    spot_symbol = normalize_crypto_spot(symbol)
    swap = symbol if symbol.endswith("-SWAP") else spot_symbol.replace("-USDT", "-USDT-SWAP")
    spot = okx_first("/api/v5/market/ticker", {"instId": spot_symbol})
    swap_ticker = okx_first("/api/v5/market/ticker", {"instId": swap})
    funding = okx_first("/api/v5/public/funding-rate", {"instId": swap})
    open_interest = okx_first("/api/v5/public/open-interest", {"instType": "SWAP", "instId": swap})
    mark = okx_first("/api/v5/public/mark-price", {"instType": "SWAP", "instId": swap})
    index_ticker = okx_first("/api/v5/market/index-tickers", {"instId": spot_symbol})
    candles_raw = okx_rows("/api/v5/market/candles", {"instId": symbol if symbol.endswith("-SWAP") else spot_symbol, "bar": "1H", "limit": "80"})
    candles = []
    for row in reversed(candles_raw):
        try:
            candles.append({
                "ts": int(row[0]),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5] or 0),
            })
        except Exception:
            continue

    last = pct(spot.get("last", "0"))
    open24h = pct(spot.get("open24h", "0"))
    high24h = pct(spot.get("high24h", "0"))
    low24h = pct(spot.get("low24h", "0"))
    change24h = (last / open24h - 1) * 100 if last > 0 and open24h > 0 else 0.0
    mark_px = pct(mark.get("markPx", "0"))
    idx_px = pct(index_ticker.get("idxPx", "0"))
    basis = (mark_px / idx_px - 1) * 100 if mark_px > 0 and idx_px > 0 else 0.0
    funding_rate = pct(funding.get("fundingRate", "0")) * 100
    oi = pct(open_interest.get("oi", open_interest.get("oiCcy", "0")))
    spot_swap_basis = 0.0
    swap_last = pct(swap_ticker.get("last", "0"))
    if swap_last > 0 and last > 0:
        spot_swap_basis = (swap_last / last - 1) * 100

    recent = candles[-24:] if len(candles) >= 24 else candles
    trend_12h = 0.0
    range_24h = 0.0
    volume_ratio = 1.0
    if len(recent) >= 2:
        trend_12h = (recent[-1]["close"] / recent[max(0, len(recent) - 12)]["close"] - 1) * 100
        range_24h = (max(row["high"] for row in recent) / max(min(row["low"] for row in recent), 1e-9) - 1) * 100
        old_volume_rows = [row["volume"] for row in recent[: max(1, len(recent) // 2)]]
        new_volume_rows = [row["volume"] for row in recent[max(1, len(recent) // 2):]]
        volume_ratio = safe_volume_ratio(new_volume_rows, old_volume_rows)

    alerts: list[dict[str, Any]] = []

    def add(level: str, title: str, body: str, tag: str) -> None:
        alerts.append({"time": now_ms(), "level": level, "title": title, "body": body, "tag": tag})

    if abs(change24h) >= 3:
        add("INFO" if change24h > 0 else "WARN", "24小时波动放大", f"{symbol} 24小时涨跌 {change24h:+.2f}%，策略应降低盲目追单。", "价格")
    if high24h > 0 and last >= high24h * 0.995:
        add("INFO", "接近24小时高点", f"现价接近 {high24h:.2f}，突破策略可关注确认，反转策略应谨慎。", "突破")
    if low24h > 0 and last <= low24h * 1.005:
        add("WARN", "接近24小时低点", f"现价接近 {low24h:.2f}，网格/马丁需要检查单日亏损限制。", "防守")
    if abs(funding_rate) >= 0.03:
        side = "多头拥挤" if funding_rate > 0 else "空头拥挤"
        add("WARN", "资金费率偏高", f"资金费率 {funding_rate:+.4f}%，可能代表{side}。", "合约")
    if abs(basis) >= 0.08:
        add("INFO", "标记价偏离指数价", f"标记价相对指数价 {basis:+.4f}%，高杠杆仓位需注意强平线。", "基差")
    if range_24h >= 6:
        add("WARN", "日内振幅较大", f"近24根小时K振幅约 {range_24h:.2f}%，移动止损比固定止损更有意义。", "波动")
    if volume_ratio >= 1.6:
        add("INFO", "成交量放大", f"最近半段小时成交量约为前半段 {volume_ratio:.2f} 倍，信号可信度可能提升。", "量能")
    if not alerts:
        add("INFO", "盘面暂稳", "未发现明显拥挤或剧烈偏离，适合先用小仓位观察策略信号。", "概览")

    score = 50 + change24h * 2 + trend_12h * 2 - abs(funding_rate) * 80 - max(0, range_24h - 4) * 2
    score = clamp(score, 0, 100)
    bias = "偏多" if score >= 60 else "偏空" if score <= 40 else "震荡"
    summary = f"{symbol} 当前盘面{bias}，24小时 {change24h:+.2f}%，12小时趋势 {trend_12h:+.2f}%，资金费率 {funding_rate:+.4f}%。"
    if write_notification:
        lead = alerts[0]
        PROFILE.notify(lead["level"], f"市场情报：{lead['title']}", lead["body"])
    return {
        "ok": True,
        "symbol": symbol,
        "swap": swap,
        "summary": summary,
        "bias": bias,
        "score": round(score, 1),
        "metrics": {
            "last": round(last, 4),
            "change24h_pct": round(change24h, 2),
            "trend12h_pct": round(trend_12h, 2),
            "range24h_pct": round(range_24h, 2),
            "funding_rate_pct": round(funding_rate, 4),
            "open_interest": round(oi, 4),
            "mark_index_basis_pct": round(basis, 4),
            "spot_swap_basis_pct": round(spot_swap_basis, 4),
            "volume_ratio": round(volume_ratio, 2),
        },
        "alerts": alerts[:10],
    }


def contract_center(symbol: str) -> dict[str, Any]:
    if is_stock_symbol(symbol):
        return {
            "ok": True,
            "symbol": symbol,
            "swap": "",
            "market_type": "stock",
            "updated_at": now_ms(),
            "metrics": {
                "spot_last": pct(read_stock_quote(symbol).get("last", 0)),
                "swap_last": 0.0,
                "index_price": 0.0,
                "mark_price": 0.0,
                "funding_rate_pct": 0.0,
                "funding_annualized_pct": 0.0,
                "next_funding_time": "",
                "open_interest": 0.0,
                "open_interest_ccy": 0.0,
                "spot_swap_basis_pct": 0.0,
                "mark_index_basis_pct": 0.0,
                "contract_value": "",
                "contract_value_ccy": "",
                "tick_size": "",
                "lot_size": "",
            },
        }
    swap = symbol if symbol.endswith("-SWAP") else symbol.replace("-USDT", "-USDT-SWAP")
    spot_symbol = symbol.replace("-SWAP", "") if symbol.endswith("-SWAP") else symbol
    spot = okx_first("/api/v5/market/ticker", {"instId": spot_symbol})
    swap_ticker = okx_first("/api/v5/market/ticker", {"instId": swap})
    mark = okx_first("/api/v5/public/mark-price", {"instType": "SWAP", "instId": swap})
    index_ticker = okx_first("/api/v5/market/index-tickers", {"instId": spot_symbol})
    funding = okx_first("/api/v5/public/funding-rate", {"instId": swap})
    oi = okx_first("/api/v5/public/open-interest", {"instType": "SWAP", "instId": swap})
    instrument_rows = okx_rows("/api/v5/public/instruments", {"instType": "SWAP"})
    instrument = next((item for item in instrument_rows if item.get("instId") == swap), {})
    spot_last = pct(spot.get("last", "0"))
    swap_last = pct(swap_ticker.get("last", "0"))
    mark_px = pct(mark.get("markPx", "0"))
    idx_px = pct(index_ticker.get("idxPx", "0"))
    funding_rate = pct(funding.get("fundingRate", "0"))
    spot_swap_basis = (swap_last / spot_last - 1) * 100 if spot_last > 0 and swap_last > 0 else 0.0
    mark_index_basis = (mark_px / idx_px - 1) * 100 if mark_px > 0 and idx_px > 0 else 0.0
    return {
        "ok": True,
        "symbol": spot_symbol,
        "swap": swap,
        "updated_at": now_ms(),
        "metrics": {
            "spot_last": round(spot_last, 6),
            "swap_last": round(swap_last, 6),
            "index_price": round(idx_px, 6),
            "mark_price": round(mark_px, 6),
            "funding_rate_pct": round(funding_rate * 100, 5),
            "funding_annualized_pct": round(funding_rate * 3 * 365 * 100, 2),
            "next_funding_time": funding.get("fundingTime", ""),
            "open_interest": pct(oi.get("oi", "0")),
            "open_interest_ccy": pct(oi.get("oiCcy", "0")),
            "spot_swap_basis_pct": round(spot_swap_basis, 5),
            "mark_index_basis_pct": round(mark_index_basis, 5),
            "contract_value": instrument.get("ctVal", ""),
            "contract_value_ccy": instrument.get("ctValCcy", ""),
            "tick_size": instrument.get("tickSz", ""),
            "lot_size": instrument.get("lotSz", ""),
        },
    }


def scanner_strategy(change24h: float, location: float, volume_rank: int) -> tuple[str, str, str]:
    if change24h >= 4 and location >= 0.72:
        return "livermore", "突破观察", "接近高位且涨幅放大，适合关键点突破/动量类策略"
    if change24h >= 2:
        return "anti_martingale", "顺势候选", "趋势偏强，适合反马丁式盈利加仓"
    if change24h <= -4 and location <= 0.32:
        return "martingale", "防守低吸", "跌幅较大且接近低位，只适合小仓分层并严控熔断"
    if abs(change24h) <= 1.2 and 0.28 <= location <= 0.72:
        return "grid", "震荡候选", "价格处于区间中部，适合网格或布林回归"
    if location <= 0.25:
        return "bollinger", "反弹观察", "接近24小时低位，优先等回归确认"
    if volume_rank <= 3:
        return "momentum", "量能观察", "成交额靠前，适合观察动量延续"
    return "dual_ma", "等待确认", "没有极端信号，先用均线趋势过滤"


def market_scanner(
    symbols_text: str = "",
    write_notification: bool = False,
    quote_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    write_notification = bool(write_notification and not RUNTIME_READ_ONLY)
    default_symbols = [crypto_spot_symbol(base) for base in CORE_CRYPTO_BASES]
    symbols = [item.strip().upper() for item in symbols_text.split(",") if item.strip()] or default_symbols
    quote_batch: dict[str, Any] = {}
    if quote_rows is None:
        quote_batch = market_quote_batch(symbols, consumer="market_scanner")
        quote_rows = list(quote_batch.get("rows") or [])
    rows = [row for row in quote_rows if str(row.get("symbol") or row.get("instId") or "").upper() in symbols]
    by_symbol = {str(row.get("symbol") or row.get("instId") or "").upper(): row for row in rows}
    volumes = sorted([pct(row.get("volCcy24h", row.get("vol24h", "0"))) for row in by_symbol.values()], reverse=True)
    result = []
    for symbol in symbols:
        row = by_symbol.get(symbol)
        if not row:
            continue
        last = pct(row.get("last", "0"))
        open24h = pct(row.get("open24h", "0"))
        high24h = pct(row.get("high24h", "0"))
        low24h = pct(row.get("low24h", "0"))
        volume = pct(row.get("volCcy24h", row.get("vol24h", "0")))
        change = (last / open24h - 1) * 100 if last > 0 and open24h > 0 else 0.0
        location = (last - low24h) / max(high24h - low24h, 1e-9) if high24h > low24h else 0.5
        volume_rank = volumes.index(volume) + 1 if volume in volumes else 99
        strategy_id, action, reason = scanner_strategy(change, location, volume_rank)
        range_pct = (high24h / max(low24h, 1e-9) - 1) * 100 if high24h > 0 and low24h > 0 else 0.0
        score = 45 + abs(change) * 4 + min(volume_rank, 20) * -0.6 + (12 if location >= 0.78 or location <= 0.22 else 0) + min(range_pct, 12)
        risk = "高" if range_pct >= 8 or abs(change) >= 6 else "中" if range_pct >= 4 or abs(change) >= 3 else "低"
        result.append({
            "symbol": symbol,
            "last": round(last, 6),
            "change24h_pct": round(change, 2),
            "range24h_pct": round(range_pct, 2),
            "location_pct": round(location * 100, 1),
            "volume": round(volume, 2),
            "volume_rank": volume_rank,
            "strategy_id": strategy_id,
            "strategy_name": choose_strategy(strategy_id)["name"],
            "action": action,
            "risk": risk,
            "score": round(clamp(score, 0, 100), 1),
            "reason": reason,
            "source": row.get("source", ""),
            "quote_ts": row.get("ts"),
            "quote_age_ms": row.get("quote_age_ms"),
            "data_quality": dict(row.get("data_quality") or {}),
            "market_session": dict(row.get("market_session") or {}),
        })
    result.sort(key=lambda item: item["score"], reverse=True)
    summary = f"已扫描 {len(result)} 个币种，最高机会：{result[0]['symbol']} · {result[0]['action']}" if result else "暂无可用扫描结果"
    if write_notification and result:
        top = result[0]
        PROFILE.notify("INFO", "多币种机会扫描", f"{top['symbol']}：{top['action']}，推荐 {top['strategy_name']}，评分 {top['score']}")
    return {
        "ok": True,
        "summary": summary,
        "rows": result[:30],
        "quote_batch": quote_batch.get("context") or {},
        "updated_at": now_ms(),
    }


def signed_pct_text(value: float, digits: int = 2) -> str:
    return f"{value:+.{digits}f}%"


def market_anomaly_severity(score: float) -> dict[str, str]:
    if score >= 82:
        return {"level": "CRITICAL", "label": "强异动", "tone": "down"}
    if score >= 68:
        return {"level": "HIGH", "label": "高关注", "tone": "up"}
    if score >= 52:
        return {"level": "MEDIUM", "label": "观察", "tone": "flat"}
    return {"level": "LOW", "label": "低噪音", "tone": "flat"}


def market_anomaly_direction(change_pct: float, location_pct: float) -> str:
    if change_pct >= 2.0 and location_pct >= 62:
        return "偏多突破"
    if change_pct <= -2.0 and location_pct <= 38:
        return "偏空下破"
    if abs(change_pct) >= 2.0:
        return "急涨急跌"
    if location_pct >= 78:
        return "压力测试"
    if location_pct <= 22:
        return "支撑测试"
    return "多空争夺"


def market_anomaly_tags(change_pct: float, range_pct: float, location_pct: float, volume_rank: int, metrics: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    volume_ratio = pct(metrics.get("volume_ratio", 0.0))
    funding = pct(metrics.get("funding_rate_pct", 0.0))
    basis = pct(metrics.get("mark_index_basis_pct", 0.0))
    if abs(change_pct) >= 3:
        tags.append("急涨急跌")
    if volume_rank <= 5 or volume_ratio >= 1.45:
        tags.append("放量")
    if location_pct >= 80:
        tags.append("接近突破")
    if location_pct <= 20:
        tags.append("接近跌破")
    if range_pct >= 6:
        tags.append("波动扩张")
    if abs(funding) >= 0.03:
        tags.append("资金费率异常")
    if abs(basis) >= 0.08:
        tags.append("合约基差异常")
    return tags or ["常规波动"]


def anomaly_market_theme(symbol: str, market_type: str, meta: dict[str, Any] | None = None) -> str:
    clean_symbol = str(symbol or "").upper()
    clean_type = str(market_type or "").lower()
    sector = str((meta or {}).get("sector") or "")
    if clean_type.startswith("crypto"):
        if clean_symbol.endswith("-SWAP"):
            return "加密合约 / 杠杆情绪"
        base = clean_symbol.split("-")[0]
        if base in {"BTC", "ETH", "SOL"}:
            return "主流加密 / 风险偏好"
        return "加密观察池"
    if sector == "Mega Cap Tech":
        return "美股七姐妹 / 大盘权重"
    if sector in {"AI Chip", "Semiconductor Design", "Semiconductor Foundry", "Semi Equipment", "Semiconductor IP", "AI Server"}:
        return "半导体与AI算力链"
    if sector == "Memory / Storage":
        return "存储 / HBM / 数据中心"
    if sector == "HK Power":
        return "港股电力股"
    if "Space" in sector:
        return "SpaceX相关替代观察"
    if sector == "BTC Proxy":
        return "美股加密代理"
    if sector == "Index ETF":
        return "指数ETF / 市场温度"
    if sector in {"China Internet", "Smart Hardware", "EV"}:
        return f"{sector} / 港美联动"
    return sector or ("股票观察池" if clean_type == "stock" else "市场观察池")


def anomaly_watch_priority(score: float, data_quality: dict[str, Any] | None = None) -> dict[str, str]:
    quality = data_quality or {}
    fallback = bool(quality.get("fallback"))
    realtime = bool(quality.get("realtime"))
    quality_status = str(quality.get("status") or "").upper()
    if quality.get("quarantined"):
        return {
            "level": "C",
            "label": "C 数据待核",
            "tone": "down",
            "detail": "报价质量检查未通过；核对昨收、复权和K线后才能进入观察队列。",
        }
    if fallback:
        if score >= 68:
            return {
                "level": "C",
                "label": "C 高分待核",
                "tone": "down",
                "detail": "异动分较高，但来源为缓存或兜底；刷新报价与K线确认后才能升级。",
            }
        return {"level": "C", "label": "C 先验数据源", "tone": "down", "detail": "兜底/缓存数据，先确认来源再研究。"}
    if quality_status in {"OFFLINE", "STALE", "UNKNOWN", "REVIEW", "DEGRADED", "DELAYED"}:
        return {
            "level": "C",
            "label": "C 数据待确认",
            "tone": "down" if quality_status in {"OFFLINE", "STALE", "REVIEW"} else "flat",
            "detail": "报价时效、会话或质量合同未通过，刷新并核对K线后再研究。",
        }
    priority_eligible = bool(quality.get("priority_eligible", realtime))
    if score >= 82 and realtime and priority_eligible:
        return {"level": "A", "label": "A 立即看图", "tone": "up", "detail": "强异动且数据较新，优先打开K线和盘口复核。"}
    if score >= 68:
        return {"level": "B", "label": "B 等确认", "tone": "flat", "detail": "高关注，但需等待量能、结构或数据源确认。"}
    return {"level": "C", "label": "C 记录观察", "tone": "flat", "detail": "暂不追，放入观察队列等待二次触发。"}


def anomaly_waiting_conditions(
    *,
    market_type: str,
    change_pct: float,
    range_pct: float,
    location_pct: float,
    volume_rank: int,
    tags: list[str],
    data_quality: dict[str, Any] | None = None,
    theme: str = "",
) -> list[str]:
    quality = data_quality or {}
    conditions: list[str] = []
    if not quality.get("realtime"):
        conditions.append("先确认数据源新鲜度，延迟/缓存行情只做研究。")
    if location_pct >= 80:
        conditions.append("等突破后站稳或回踩不破，再判断是否是真突破。")
    elif location_pct <= 20:
        conditions.append("等跌破后是否快速收回，确认支撑是否有效。")
    elif abs(change_pct) >= 2.5:
        conditions.append("等下一根K线方向和成交量确认，避免追急涨急跌。")
    if volume_rank <= 5 or "放量" in tags:
        conditions.append("复核放量是否延续，单根放量不能直接当趋势。")
    if range_pct >= 5 or "波动扩张" in tags:
        conditions.append("波动扩张时先收窄止损假设，避免用常规波动区间。")
    if str(market_type).startswith("crypto"):
        conditions.append("同步检查资金费率、OI和盘口，确认是否是杠杆驱动。")
    else:
        if theme:
            conditions.append(f"查看{theme}同组股票是否同步，单股孤立异动降低可信度。")
        else:
            conditions.append("查看同业、指数和盘前盘后是否同步，确认是否有板块共振。")
    conditions.append("结论只用于观察、研究和模拟盘验证，不作为实盘指令。")
    return conditions[:6]


def anomaly_ai_output_schema() -> dict[str, Any]:
    return {
        "summary": "一句话解释这次异动，不超过60字",
        "anomaly_type": ["放量", "急涨急跌", "突破/跌破", "波动率扩张", "资金费率异常", "OI变化", "盘口变化", "消息驱动", "联动异动"],
        "severity": "LOW/MEDIUM/HIGH/CRITICAL",
        "direction_bias": "LONG_BIAS/SHORT_BIAS/NEUTRAL/WAIT",
        "long_win_rate_pct": "0-100，仅为当前样本和规则估计，不是保证",
        "short_win_rate_pct": "0-100，仅为当前样本和规则估计，不是保证",
        "long_take_profit_zone": "做多观察止盈区，允许为空",
        "long_stop_loss_zone": "做多结构失效区，允许为空",
        "short_take_profit_zone": "做空观察止盈区，允许为空",
        "short_stop_loss_zone": "做空结构失效区，允许为空",
        "evidence": ["支持结论的K线、成交量、盘口、资金费率、OI、新闻或联动证据"],
        "counter_evidence": ["可能推翻结论的反证、假突破风险或数据缺口"],
        "waiting_conditions": ["下一步观察条件，不满足则等待"],
        "risk_notes": ["风控提示，必须包含仅研究/仅模拟盘验证"],
        "safe_action": "观察 / 仅研究 / 仅模拟盘验证",
    }


def event_time_text(ts_ms: int, symbol: str = "") -> str:
    if not ts_ms:
        return "--"
    try:
        tz = stock_timezone(symbol) if symbol and is_stock_symbol(symbol) else ZoneInfo("Asia/Shanghai")
        return datetime.fromtimestamp(ts_ms / 1000, tz).strftime("%m-%d %H:%M:%S")
    except Exception:
        return str(ts_ms)


def ensure_anomaly_event_db() -> sqlite3.Connection:
    ensure_runtime()
    conn = sqlite3.connect(ANOMALY_EVENT_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_anomaly_events (
            event_id TEXT PRIMARY KEY,
            first_seen INTEGER NOT NULL,
            last_seen INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            market_type TEXT DEFAULT '',
            direction TEXT DEFAULT '',
            severity TEXT DEFAULT '',
            severity_label TEXT DEFAULT '',
            tone TEXT DEFAULT '',
            score REAL DEFAULT 0,
            reason TEXT DEFAULT '',
            price REAL DEFAULT 0,
            change24h_pct REAL DEFAULT 0,
            range24h_pct REAL DEFAULT 0,
            location_pct REAL DEFAULT 0,
            volume REAL DEFAULT 0,
            volume_rank INTEGER DEFAULT 99,
            scan_depth TEXT DEFAULT 'fast',
            hit_count INTEGER DEFAULT 1,
            evidence_json TEXT DEFAULT '[]',
            tags_json TEXT DEFAULT '[]',
            metrics_json TEXT DEFAULT '{}',
            data_quality_json TEXT DEFAULT '{}',
            safe_action TEXT DEFAULT '',
            live_trading_allowed INTEGER DEFAULT 0
        )
    """)
    for ddl in [
        "ALTER TABLE market_anomaly_events ADD COLUMN theme TEXT DEFAULT ''",
        "ALTER TABLE market_anomaly_events ADD COLUMN next_observation TEXT DEFAULT ''",
        "ALTER TABLE market_anomaly_events ADD COLUMN watch_priority_json TEXT DEFAULT '{}'",
        "ALTER TABLE market_anomaly_events ADD COLUMN waiting_conditions_json TEXT DEFAULT '[]'",
        "ALTER TABLE market_anomaly_events ADD COLUMN motion_json TEXT DEFAULT '{}'",
        "ALTER TABLE market_anomaly_events ADD COLUMN entry_price REAL DEFAULT 0",
        "ALTER TABLE market_anomaly_events ADD COLUMN outcome_json TEXT DEFAULT '{}'",
    ]:
        try:
            conn.execute(ddl)
        except sqlite3.OperationalError:
            pass
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_market_anomaly_events_last_seen
        ON market_anomaly_events(last_seen DESC)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_market_anomaly_events_symbol_last_seen
        ON market_anomaly_events(symbol, last_seen DESC)
    """)
    return conn


def open_anomaly_event_db_read_only() -> sqlite3.Connection | None:
    path = Path(ANOMALY_EVENT_DB)
    if not path.is_file():
        return None
    try:
        conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error:
        return None


def anomaly_event_id(row: dict[str, Any]) -> str:
    symbol = str(row.get("symbol") or "").upper()
    direction = str(row.get("direction") or "watch")
    reason = str(row.get("reason") or "")
    bucket = int(pct(row.get("time", now_ms()), now_ms())) // (15 * 60 * 1000)
    digest = hashlib.sha1(f"{symbol}|{bucket}|{direction}|{reason[:96]}".encode("utf-8")).hexdigest()[:16]
    return f"{symbol}:{bucket}:{digest}"


def json_blob(value: Any, default: Any) -> str:
    try:
        return json.dumps(clean_json_value(value if value is not None else default), ensure_ascii=False)
    except Exception:
        return json.dumps(default, ensure_ascii=False)


def parse_json_blob(text: str, default: Any) -> Any:
    try:
        value = json.loads(text or "")
        return value if value is not None else default
    except Exception:
        return default


def persist_anomaly_events(rows: list[dict[str, Any]], scan_depth: str = "fast") -> int:
    if not rows:
        return 0
    conn = ensure_anomaly_event_db()
    saved = 0
    try:
        for row in rows[:50]:
            symbol = str(row.get("symbol") or "").upper()
            if not symbol:
                continue
            event_ts = int(pct(row.get("time", now_ms()), now_ms()))
            payload = {
                "event_id": anomaly_event_id(row),
                "first_seen": event_ts,
                "last_seen": now_ms(),
                "symbol": symbol,
                "market_type": str(row.get("market_type") or ""),
                "direction": str(row.get("direction") or ""),
                "severity": str(row.get("severity") or ""),
                "severity_label": str(row.get("severity_label") or row.get("severity") or ""),
                "tone": str(row.get("tone") or ""),
                "score": pct(row.get("score", 0.0)),
                "reason": str(row.get("reason") or ""),
                "theme": str(row.get("theme") or ""),
                "next_observation": str(row.get("next_observation") or ""),
                "price": pct(row.get("price", 0.0)),
                "entry_price": pct(row.get("price", 0.0)),
                "change24h_pct": pct(row.get("change24h_pct", 0.0)),
                "range24h_pct": pct(row.get("range24h_pct", 0.0)),
                "location_pct": pct(row.get("location_pct", 0.0)),
                "volume": pct(row.get("volume", 0.0)),
                "volume_rank": int(pct(row.get("volume_rank", 99), 99)),
                "scan_depth": scan_depth,
                "evidence_json": json_blob(row.get("evidence"), []),
                "tags_json": json_blob(row.get("type_tags"), []),
                "metrics_json": json_blob(row.get("metrics"), {}),
                "data_quality_json": json_blob(row.get("data_quality"), {}),
                "watch_priority_json": json_blob(row.get("watch_priority"), {}),
                "waiting_conditions_json": json_blob(row.get("waiting_conditions"), []),
                "motion_json": json_blob(row.get("motion"), {}),
                "outcome_json": json_blob(row.get("outcome"), {}),
                "safe_action": str(row.get("safe_action") or "观察 / 仅研究 / 仅模拟盘验证"),
                "live_trading_allowed": 1 if row.get("live_trading_allowed") else 0,
            }
            conn.execute("""
                INSERT INTO market_anomaly_events (
                    event_id, first_seen, last_seen, symbol, market_type, direction,
                    severity, severity_label, tone, score, reason, price, change24h_pct,
                    range24h_pct, location_pct, volume, volume_rank, scan_depth,
                    evidence_json, tags_json, metrics_json, data_quality_json,
                    safe_action, live_trading_allowed, theme, next_observation,
                    watch_priority_json, waiting_conditions_json, motion_json,
                    entry_price, outcome_json
                ) VALUES (
                    :event_id, :first_seen, :last_seen, :symbol, :market_type, :direction,
                    :severity, :severity_label, :tone, :score, :reason, :price, :change24h_pct,
                    :range24h_pct, :location_pct, :volume, :volume_rank, :scan_depth,
                    :evidence_json, :tags_json, :metrics_json, :data_quality_json,
                    :safe_action, :live_trading_allowed, :theme, :next_observation,
                    :watch_priority_json, :waiting_conditions_json, :motion_json,
                    :entry_price, :outcome_json
                )
                ON CONFLICT(event_id) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    market_type = excluded.market_type,
                    direction = excluded.direction,
                    severity = excluded.severity,
                    severity_label = excluded.severity_label,
                    tone = excluded.tone,
                    score = excluded.score,
                    reason = excluded.reason,
                    theme = excluded.theme,
                    next_observation = excluded.next_observation,
                    price = excluded.price,
                    entry_price = CASE
                        WHEN market_anomaly_events.entry_price > 0 THEN market_anomaly_events.entry_price
                        ELSE excluded.entry_price
                    END,
                    change24h_pct = excluded.change24h_pct,
                    range24h_pct = excluded.range24h_pct,
                    location_pct = excluded.location_pct,
                    volume = excluded.volume,
                    volume_rank = excluded.volume_rank,
                    scan_depth = excluded.scan_depth,
                    hit_count = market_anomaly_events.hit_count + 1,
                    evidence_json = excluded.evidence_json,
                    tags_json = excluded.tags_json,
                    metrics_json = excluded.metrics_json,
                    data_quality_json = excluded.data_quality_json,
                    watch_priority_json = excluded.watch_priority_json,
                    waiting_conditions_json = excluded.waiting_conditions_json,
                    motion_json = excluded.motion_json,
                    safe_action = excluded.safe_action,
                    live_trading_allowed = 0
            """, payload)
            saved += 1
        conn.commit()
        return saved
    finally:
        conn.close()


def anomaly_event_from_row(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    data = dict(row)
    symbol = str(data.get("symbol") or "").upper()
    evidence = parse_json_blob(str(data.get("evidence_json") or "[]"), [])
    tags = parse_json_blob(str(data.get("tags_json") or "[]"), [])
    metrics = parse_json_blob(str(data.get("metrics_json") or "{}"), {})
    quality = parse_json_blob(str(data.get("data_quality_json") or "{}"), {})
    watch_priority = parse_json_blob(str(data.get("watch_priority_json") or "{}"), {})
    waiting_conditions = parse_json_blob(str(data.get("waiting_conditions_json") or "[]"), [])
    motion = parse_json_blob(str(data.get("motion_json") or "{}"), {})
    outcome = parse_json_blob(str(data.get("outcome_json") or "{}"), {})
    last_seen = int(pct(data.get("last_seen", 0), 0))
    first_seen = int(pct(data.get("first_seen", 0), 0))
    return {
        "event_id": data.get("event_id", ""),
        "time": last_seen,
        "first_seen": first_seen,
        "last_seen": last_seen,
        "first_seen_text": event_time_text(first_seen, symbol),
        "last_seen_text": event_time_text(last_seen, symbol),
        "age_ms": max(0, now_ms() - last_seen) if last_seen else 0,
        "symbol": symbol,
        "market_type": data.get("market_type", ""),
        "direction": data.get("direction", ""),
        "severity": data.get("severity", ""),
        "severity_label": data.get("severity_label", ""),
        "tone": data.get("tone", ""),
        "score": round(pct(data.get("score", 0.0)), 1),
        "reason": data.get("reason", ""),
        "theme": data.get("theme", ""),
        "next_observation": data.get("next_observation", ""),
        "price": pct(data.get("price", 0.0)),
        "entry_price": pct(data.get("entry_price", 0.0)),
        "change24h_pct": round(pct(data.get("change24h_pct", 0.0)), 2),
        "range24h_pct": round(pct(data.get("range24h_pct", 0.0)), 2),
        "location_pct": round(pct(data.get("location_pct", 0.0)), 1),
        "volume": pct(data.get("volume", 0.0)),
        "volume_rank": int(pct(data.get("volume_rank", 99), 99)),
        "scan_depth": data.get("scan_depth", "fast"),
        "hit_count": int(pct(data.get("hit_count", 1), 1)),
        "evidence": evidence if isinstance(evidence, list) else [],
        "type_tags": tags if isinstance(tags, list) else [],
        "metrics": metrics if isinstance(metrics, dict) else {},
        "data_quality": quality if isinstance(quality, dict) else {},
        "watch_priority": watch_priority if isinstance(watch_priority, dict) else {},
        "waiting_conditions": waiting_conditions if isinstance(waiting_conditions, list) else [],
        "motion": motion if isinstance(motion, dict) else {},
        "outcome": outcome if isinstance(outcome, dict) else {},
        "safe_action": data.get("safe_action") or "观察 / 仅研究 / 仅模拟盘验证",
        "live_trading_allowed": False,
    }


def update_anomaly_event_outcomes(rows: list[dict[str, Any]]) -> dict[str, Any]:
    current_by_symbol = {
        str(row.get("symbol") or "").upper(): row
        for row in rows
        if isinstance(row, dict) and row.get("symbol") and pct(row.get("price", 0.0)) > 0
    }
    if not current_by_symbol:
        return {**anomaly_outcome_summary([]), "updated": 0, "outcomes": {}}
    current_event_ids = {
        anomaly_event_id(row): str(row.get("symbol") or "").upper()
        for row in rows
        if isinstance(row, dict) and row.get("symbol")
    }
    conn = ensure_anomaly_event_db()
    evaluated_at = now_ms()
    updated_events: list[dict[str, Any]] = []
    updated_count = 0
    current_outcomes: dict[str, dict[str, Any]] = {}
    try:
        symbols = list(current_by_symbol)
        placeholders = ",".join("?" for _ in symbols)
        cursor = conn.execute(f"""
            SELECT *
            FROM market_anomaly_events
            WHERE symbol IN ({placeholders})
              AND entry_price > 0
            ORDER BY first_seen DESC
            LIMIT 500
        """, symbols)
        for db_row in cursor.fetchall():
            event = anomaly_event_from_row(db_row)
            previous_state = str((event.get("outcome") or {}).get("state") or "")
            if previous_state in {"CONFIRMED", "INVALIDATED", "NO_FOLLOW_THROUGH"}:
                updated_events.append(event)
                if event.get("event_id") in current_event_ids:
                    current_outcomes[event.get("symbol")] = event.get("outcome") or {}
                continue
            current = current_by_symbol.get(event.get("symbol")) or {}
            outcome = evaluate_anomaly_outcome(event, current.get("price"), evaluated_at)
            conn.execute(
                "UPDATE market_anomaly_events SET outcome_json = ? WHERE event_id = ?",
                (json_blob(outcome, {}), event.get("event_id")),
            )
            updated_count += 1
            event["outcome"] = outcome
            updated_events.append(event)
            if event.get("event_id") in current_event_ids:
                current_outcomes[event.get("symbol")] = outcome
        conn.commit()
    finally:
        conn.close()
    return {**anomaly_outcome_summary(updated_events), "updated": updated_count, "outcomes": current_outcomes}


def read_anomaly_events(
    limit: int = 80,
    symbol: str = "",
    min_score: float = 0.0,
    *,
    create_if_missing: bool | None = None,
) -> dict[str, Any]:
    clean_limit = int(clamp(pct(limit, 80), 1, 300))
    clean_symbol = (symbol or "").upper().strip()
    clean_score = pct(min_score, 0.0)
    allow_create = not RUNTIME_READ_ONLY if create_if_missing is None else bool(create_if_missing)
    conn = ensure_anomaly_event_db() if allow_create else open_anomaly_event_db_read_only()
    rows: list[dict[str, Any]] = []
    if conn is not None:
        try:
            params: list[Any] = []
            where = ["score >= ?"]
            params.append(clean_score)
            if clean_symbol:
                where.append("symbol = ?")
                params.append(clean_symbol)
            params.append(clean_limit)
            cursor = conn.execute(f"""
                SELECT *
                FROM market_anomaly_events
                WHERE {" AND ".join(where)}
                ORDER BY last_seen DESC, score DESC
                LIMIT ?
            """, params)
            rows = [anomaly_event_from_row(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            rows = []
        finally:
            conn.close()
    evaluation = anomaly_outcome_summary(rows)
    return {
        "ok": True,
        "symbol": clean_symbol,
        "summary": (
            f"已记录 {len(rows)} 条可追踪异动事件"
            + (f" / {clean_symbol}" if clean_symbol else "")
            + f"；{evaluation.get('summary')}"
        ),
        "rows": rows,
        "evaluation": evaluation,
        "safe_action": "观察 / 仅研究 / 仅模拟盘验证",
        "live_trading_allowed": False,
        "updated_at": now_ms(),
    }


def latest_anomaly_event(symbol: str) -> dict[str, Any] | None:
    events = read_anomaly_events(1, symbol).get("rows") or []
    return events[0] if events else None


def stock_source_control(symbol: str = "AAPL", interval: str = "1d", session: str = "all", force: bool = False) -> dict[str, Any]:
    meta = stock_meta(symbol)
    if force and STOCK_HISTORY_PREWARM_SERVICE:
        STOCK_HISTORY_PREWARM_SERVICE.start([meta["symbol"]], interval="1d", session="regular", limit=520, force=True)
    snapshot = stock_data_sources_snapshot(meta["symbol"], interval, session, force=force)
    cache = snapshot.get("cache") or {}
    coverage = cache.get("coverage") or {}
    futu = snapshot.get("futu") or {}
    providers = snapshot.get("providers") or []
    prewarm = snapshot.get("history_prewarm") or {}
    prewarm_job = next(iter(prewarm.get("jobs") or []), {})
    persistent_warning = str(cache.get("persistent_warning") or "")
    persistent_data_age = human_age_ms(cache.get("persistent_data_age_ms"))
    persistent_cache_age = human_age_ms(cache.get("persistent_age_ms"))
    persistent_latest = cache.get("persistent_latest_at") or "--"
    persistent_is_stale = bool(cache.get("persistent") and not cache.get("persistent_fresh"))
    current = {
        "source": cache.get("memory_source") or ("stock_sqlite_cache" if cache.get("persistent") else "waiting"),
        "origin_source": cache.get("persistent_source") or "",
        "fresh": bool(cache.get("memory") or cache.get("persistent_fresh")),
        "memory_age_ms": cache.get("memory_age_ms"),
        "persistent_age_ms": cache.get("persistent_age_ms"),
    }
    cards = [
        {
            "label": "当前K线源",
            "value": current["source"],
            "detail": f"原始来源 {market_source_name(current['origin_source'])} / 最新 {persistent_latest} / 数据约{persistent_data_age}前" if cache.get("persistent") else "等待Futu或外部延迟源补入本地库",
            "tone": "up" if current["fresh"] else "down" if cache.get("persistent") else "down",
        },
        {
            "label": "Futu OpenD",
            "value": "ONLINE" if futu.get("opend_online") else "OFFLINE",
            "detail": f"{futu.get('host', FUTU_HOST)}:{futu.get('port', FUTU_PORT)} / {futu.get('message', '')}",
            "tone": "up" if futu.get("opend_online") else "down",
        },
        {
            "label": "本地缓存",
            "value": "旧缓存" if persistent_is_stale else "READY" if cache.get("persistent") else "EMPTY",
            "detail": f"{coverage.get('row_count', 0)} 根 / {coverage.get('first_date') or '--'} 至 {coverage.get('latest_date') or '--'} / 写入约{persistent_cache_age}前 / {persistent_warning or '可用于秒开，仍需实时源复核'}",
            "tone": "up" if cache.get("persistent_fresh") else "down" if cache.get("persistent") else "down",
        },
        {
            "label": "实盘边界",
            "value": "BLOCKED" if LIVE_TRADING_HARD_BLOCK else "CHECK",
            "detail": "本面板只解释行情源，不开放真实下单",
            "tone": "down",
        },
        {
            "label": "历史预热",
            "value": prewarm_job.get("status") or "WAIT",
            "detail": f"{prewarm_job.get('row_count', coverage.get('row_count', 0))} 根 / 最新 {prewarm_job.get('latest_date') or coverage.get('latest_date') or '--'} / 并发上限 {prewarm.get('max_concurrency', 2)}",
            "tone": "up" if prewarm_job.get("status") == "READY" else "down" if prewarm_job.get("status") == "ERROR" else "flat",
        },
    ]
    rows = [
        {
            "name": "Futu OpenD",
            "status": "ONLINE" if futu.get("opend_online") else "OFFLINE",
            "detail": futu.get("message", ""),
            "freshness": (
                f"最近 {human_age_ms((futu.get('health') or {}).get('last_attempt_at') and now_ms() - int((futu.get('health') or {}).get('last_attempt_at')))} / "
                f"{(futu.get('health') or {}).get('last_latency_ms', '--')}ms"
            ) if (futu.get("health") or {}).get("calls") else ("实时优先" if futu.get("opend_online") else "等待本机OpenD登录"),
            "next": "在线时优先拉取股票K线/盘口",
            "tone": "up" if futu.get("opend_online") else "down",
        },
        {
            "name": "内存K线缓存",
            "status": "READY" if cache.get("memory") else "WAIT",
            "detail": cache.get("memory_source") or "--",
            "freshness": human_age_ms(cache.get("memory_age_ms")) if cache.get("memory_age_ms") is not None else "--",
            "next": "切换标的先用它秒开预览",
            "tone": "up" if cache.get("memory") else "flat",
        },
        {
            "name": "SQLite K线库",
            "status": "旧缓存" if persistent_is_stale else "READY" if cache.get("persistent") else "EMPTY",
            "detail": f"原始来源 {market_source_name(cache.get('persistent_source'))} / {coverage.get('row_count', 0)} 根 / {coverage.get('first_date') or '--'} 至 {coverage.get('latest_date') or persistent_latest}",
            "freshness": f"数据约{persistent_data_age}前 / 写入约{persistent_cache_age}前" if cache.get("persistent") else "--",
            "next": "用于避免切换股票空图；实时判断需等Futu或外部源刷新",
            "tone": "up" if cache.get("persistent_fresh") else "down" if cache.get("persistent") else "down",
        },
    ]
    for provider in providers:
        provider_health = provider.get("health") or {}
        provider_status = provider_health.get("status") or ("ENABLED" if provider.get("enabled") else "DISABLED")
        rows.append({
            "name": str(provider.get("id") or "").upper(),
            "status": provider_status,
            "detail": f"timeout {provider.get('timeout_sec', STOCK_HISTORY_TIMEOUT)}s / 调用 {provider_health.get('calls', 0)} 次 / 平均 {provider_health.get('average_latency_ms', '--')}ms",
            "freshness": f"最近 {provider_health.get('last_latency_ms', '--')}ms / {provider_health.get('last_error') or '无错误记录'}",
            "next": "仅在Futu/缓存不足时补K线",
            "tone": "down" if provider_status in {"CIRCUIT_OPEN", "DEGRADED", "DISABLED"} else "up" if provider_status == "HEALTHY" else "flat",
        })
    if prewarm_job:
        rows.append({
            "name": "历史补齐队列",
            "status": prewarm_job.get("status") or "WAIT",
            "detail": f"{prewarm_job.get('source') or '等待数据源'} / {prewarm_job.get('row_count', 0)} 根 / 最新 {prewarm_job.get('latest_date') or '--'}",
            "freshness": f"耗时 {prewarm_job.get('latency_ms', 0)}ms / {prewarm_job.get('error') or '无错误'}",
            "next": "后台低并发补齐日线，不阻塞当前股票切换",
            "tone": "up" if prewarm_job.get("status") == "READY" else "down" if prewarm_job.get("status") == "ERROR" else "flat",
        })
    return {
        "ok": True,
        "symbol": meta["symbol"],
        "interval": snapshot.get("interval"),
        "session": snapshot.get("session"),
        "session_label": snapshot.get("session_label"),
        "summary": snapshot.get("summary", ""),
        "mode": "market_research_only",
        "forced": bool(force),
        "cards": cards,
        "rows": rows,
        "order": snapshot.get("order", []),
        "snapshot": snapshot,
        "safe_action": "观察 / 仅研究 / 仅模拟盘验证",
        "live_trading_allowed": False,
        "updated_at": now_ms(),
    }


def market_anomaly_detail(symbol: str = "BTC-USDT") -> dict[str, Any]:
    clean_symbol = (symbol or "BTC-USDT").upper()
    radar = market_anomaly_radar(force=False)
    radar_rows = radar.get("rows") or []
    row = next((item for item in radar_rows if item.get("symbol") == clean_symbol), None)
    if not row:
        row = latest_anomaly_event(clean_symbol)
    if not row:
        row = {
            "symbol": clean_symbol,
            "market_type": "stock" if is_stock_symbol(clean_symbol) else "crypto",
            "direction": "观察",
            "severity": "WATCH",
            "severity_label": "观察",
            "score": 0,
            "reason": "暂无雷达异动，等待新样本",
            "evidence": ["暂无可追踪异动事件，先查看K线、量能和数据源状态"],
            "safe_action": "观察 / 仅研究 / 仅模拟盘验证",
            "live_trading_allowed": False,
        }
    try:
        cockpit = trend_analysis_cockpit(clean_symbol)
    except Exception as exc:
        cockpit = {"ok": False, "symbol": clean_symbol, "error": str(exc), "evidence": [], "counter_evidence": [], "waiting_conditions": []}
    chart_bar = "1m" if is_stock_symbol(clean_symbol) else "1H"
    try:
        chart = market_chart_candles(clean_symbol, chart_bar, 160, fast=True)
    except Exception as exc:
        chart = {"ok": False, "symbol": clean_symbol, "source": "unavailable", "rows": [], "warning": str(exc)}
    events = read_anomaly_events(12, clean_symbol).get("rows", [])
    source = stock_source_control(clean_symbol, chart_bar, "all") if is_stock_symbol(clean_symbol) else {
        "ok": True,
        "symbol": clean_symbol,
        "summary": "OKX public market data / realtime when network is available",
        "cards": [
            {"label": "行情源", "value": "OKX", "detail": "公共行情端点，无需私钥", "tone": "up"},
            {"label": "K线源", "value": chart.get("source", "--"), "detail": chart.get("warning", "") or "实时/缓存自动兜底", "tone": "down" if chart.get("fallback") else "up"},
            {"label": "实盘边界", "value": "BLOCKED" if LIVE_TRADING_HARD_BLOCK else "CHECK", "detail": "只研究行情，不开放真实下单", "tone": "down"},
        ],
        "rows": [],
    }
    prompt = market_anomaly_ai_prompt(clean_symbol, row, cockpit)
    evidence_chain = [
        {"label": "雷达原因", "value": row.get("reason", "--")},
        {"label": "安全边界", "value": row.get("safe_action") or "观察 / 仅研究 / 仅模拟盘验证"},
    ]
    evidence_chain.extend({"label": "雷达证据", "value": item} for item in (row.get("evidence") or [])[:8])
    evidence_chain.extend({"label": "走势证据", "value": item} for item in (cockpit.get("evidence") or [])[:8])
    evidence_chain.extend({"label": "反证", "value": item} for item in (cockpit.get("counter_evidence") or [])[:6])
    evidence_chain.extend({"label": "等待条件", "value": item} for item in (cockpit.get("waiting_conditions") or [])[:6])
    return {
        "ok": True,
        "symbol": clean_symbol,
        "summary": f"{clean_symbol} 异动详情：{row.get('reason', '等待样本')} / {row.get('severity_label', row.get('severity', 'WATCH'))}",
        "anomaly": row,
        "trend": cockpit,
        "chart": {
            "ok": bool(chart.get("ok")),
            "bar": chart.get("bar", chart_bar),
            "source": chart.get("source", ""),
            "warning": chart.get("warning", ""),
            "fallback": bool(chart.get("fallback")),
            "latest_at": chart.get("latest_at", ""),
            "rows": (chart.get("rows") or [])[-80:],
        },
        "events": events,
        "source_control": source,
        "evidence_chain": evidence_chain[:28],
        "ai_prompt": prompt,
        "safe_action": "观察 / 仅研究 / 仅模拟盘验证",
        "live_trading_allowed": False,
        "updated_at": now_ms(),
    }


def market_anomaly_ai_prompt(symbol: str, anomaly: dict[str, Any] | None = None, cockpit: dict[str, Any] | None = None, news: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    output_schema = anomaly_ai_output_schema()
    payload = {
        "task": "解释行情异动并复核多空力量，不得输出实盘下单指令",
        "symbol": symbol,
        "anomaly": anomaly or {},
        "trend_cockpit": cockpit or {},
        "news_context": (news or [])[:5],
        "required_output_schema": output_schema,
        "safety_boundary": {
            "live_trading_enabled": False,
            "safe_action_only": "观察 / 仅研究 / 仅模拟盘验证",
            "win_rate_note": "胜率只能是基于当前样本、规则和数据质量的估计，不能写成保证性结论。",
        },
    }
    return {
        "system_prompt": (
            "你是哈基米交易 v2 的行情异动解释员。你只能做行情研究、风险解释和模拟盘验证建议，"
            "不能要求系统绕过风控，不能输出实盘买入、卖出、开仓、加仓或强平指令。"
            "必须同时给出证据和反证，必须分别估计做多与做空胜率，必须说明等待条件。"
            "输出必须是 JSON，不能使用 Markdown。"
        ),
        "user_prompt": json.dumps(payload, ensure_ascii=False),
        "output_schema": output_schema,
        "safety_notice": "所有结论仅用于观察、研究和模拟盘验证，不构成实盘下单指令。",
    }


def build_crypto_anomaly_row(row: dict[str, Any], rank: int, deep: bool = False) -> dict[str, Any]:
    symbol = str(row.get("symbol") or "").upper()
    change_pct = pct(row.get("change24h_pct", 0.0))
    range_pct = pct(row.get("range24h_pct", 0.0))
    location_pct = pct(row.get("location_pct", 50.0), 50.0)
    volume_rank = int(pct(row.get("volume_rank", 99), 99))
    metrics: dict[str, Any] = {}
    insight_alerts: list[dict[str, Any]] = []
    if deep:
        try:
            insights = market_insights(symbol)
            metrics = insights.get("metrics") or {}
            insight_alerts = insights.get("alerts") or []
        except Exception as exc:
            metrics = {"error": str(exc)}
    volume_ratio = pct(metrics.get("volume_ratio", 0.0))
    funding = abs(pct(metrics.get("funding_rate_pct", 0.0)))
    basis = abs(pct(metrics.get("mark_index_basis_pct", 0.0)))
    oi = pct(metrics.get("open_interest", 0.0))
    score = max(
        pct(row.get("score", 0.0)),
        34
        + abs(change_pct) * 5.2
        + min(range_pct, 14) * 1.7
        + (16 if location_pct >= 82 or location_pct <= 18 else 0)
        + (12 if volume_rank <= 3 else 7 if volume_rank <= 8 else 0)
        + clamp((volume_ratio - 1.0) * 12, 0, 18)
        + min(funding * 260, 13)
        + min(basis * 95, 10),
    )
    score = round(clamp(score, 0, 100), 1)
    severity = market_anomaly_severity(score)
    direction = market_anomaly_direction(change_pct, location_pct)
    tags = market_anomaly_tags(change_pct, range_pct, location_pct, volume_rank, metrics)
    evidence = [
        f"24h涨跌 {signed_pct_text(change_pct)}，区间位置 {location_pct:.1f}%",
        f"24h振幅 {range_pct:.2f}%，成交额排名 {volume_rank}",
    ]
    if volume_ratio:
        evidence.append(f"近窗口量能约 {volume_ratio:.2f}x")
    if funding:
        evidence.append(f"资金费率 {signed_pct_text(pct(metrics.get('funding_rate_pct', 0.0)), 4)}")
    if oi:
        evidence.append(f"未平仓量 {oi:.4g}")
    evidence.extend(str(item.get("title") or item.get("body") or "") for item in insight_alerts[:2] if isinstance(item, dict))
    reason = " / ".join(tags[:3])
    data_quality = dict(row.get("data_quality") or normalize_quote_data_quality(
        {**row, "ts": row.get("quote_ts") or row.get("ts")},
        asset_type="crypto",
        observed_at_ms=now_ms(),
    ))
    theme = anomaly_market_theme(symbol, "crypto")
    watch_priority = anomaly_watch_priority(score, data_quality)
    waiting_conditions = anomaly_waiting_conditions(
        market_type="crypto",
        change_pct=change_pct,
        range_pct=range_pct,
        location_pct=location_pct,
        volume_rank=volume_rank,
        tags=tags,
        data_quality=data_quality,
        theme=theme,
    )
    return {
        "time": now_ms(),
        "symbol": symbol,
        "market_type": "crypto",
        "theme": theme,
        "rank": rank,
        "price": row.get("last") or metrics.get("last") or 0,
        "change24h_pct": round(change_pct, 2),
        "range24h_pct": round(range_pct, 2),
        "location_pct": round(location_pct, 1),
        "volume": row.get("volume", 0),
        "volume_rank": volume_rank,
        "score": score,
        "severity": severity["level"],
        "severity_label": severity["label"],
        "tone": severity["tone"],
        "direction": direction,
        "reason": reason,
        "type_tags": tags,
        "evidence": [item for item in evidence if item][:8],
        "watch_priority": watch_priority,
        "next_observation": waiting_conditions[0] if waiting_conditions else "等待下一轮雷达确认。",
        "waiting_conditions": waiting_conditions,
        "metrics": metrics,
        "data_quality": data_quality,
        "risk": "仅研究，需等待K线和量能确认" if score < 68 else "强异动，只允许观察和模拟盘验证",
        "safe_action": "观察 / 仅研究 / 仅模拟盘验证",
        "live_trading_allowed": False,
    }


def build_stock_anomaly_rows(
    limit: int = 8,
    allow_network: bool = False,
    stock_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if stock_rows is None:
        try:
            if allow_network:
                stock_rows = read_stock_quotes_cached(180000)
            elif now_ms() - int(STOCK_QUOTE_CACHE.get("time") or 0) < 180000:
                stock_rows = STOCK_QUOTE_CACHE.get("rows", [])
            else:
                stock_rows = []
        except Exception:
            return []
    volumes = sorted([pct(row.get("volCcy24h", row.get("vol24h", 0))) for row in stock_rows if pct(row.get("volCcy24h", row.get("vol24h", 0))) > 0], reverse=True)
    result: list[dict[str, Any]] = []
    for row in stock_rows:
        symbol = str(row.get("symbol") or "").upper()
        if not symbol:
            continue
        last = pct(row.get("last", 0.0))
        high = pct(row.get("high24h", 0.0))
        low = pct(row.get("low24h", 0.0))
        change_pct = pct(row.get("change24h_pct", 0.0))
        volume = pct(row.get("volCcy24h", row.get("vol24h", 0.0)))
        range_pct = (high / max(low, 1e-9) - 1) * 100 if high > 0 and low > 0 else abs(change_pct)
        location_pct = ((last - low) / max(high - low, 1e-9) * 100) if high > low and last > 0 else 50.0
        volume_rank = volumes.index(volume) + 1 if volume > 0 and volume in volumes else 99
        if abs(change_pct) < 0.8 and volume_rank > 5 and range_pct < 2.5:
            continue
        raw_score = round(clamp(30 + abs(change_pct) * 8 + min(range_pct, 10) * 1.8 + (12 if volume_rank <= 3 else 5 if volume_rank <= 6 else 0), 0, 100), 1)
        score = raw_score
        severity = market_anomaly_severity(score)
        direction = market_anomaly_direction(change_pct, location_pct)
        tags = market_anomaly_tags(change_pct, range_pct, location_pct, volume_rank, {})
        meta = stock_meta(symbol)
        quote_source = str(row.get("source") or "stock")
        data_quality = dict(row.get("data_quality") or normalize_quote_data_quality(
            row,
            asset_type="stock",
            observed_at_ms=now_ms(),
        ))
        quarantine_reasons = list(dict.fromkeys([
            *stock_quote_quarantine_reasons(row),
            *[str(item) for item in data_quality.get("quarantine_reasons") or [] if str(item)],
        ]))
        data_quarantined = bool(quarantine_reasons or data_quality.get("quarantined"))
        if data_quarantined:
            score = min(score, 67.0)
            severity = {"level": "REVIEW", "label": "数据待核", "tone": "flat"}
            direction = "数据异常"
            tags = ["复权/缓存待核", *tags]
            data_quality = {
                **data_quality,
                "quarantined": True,
                "quarantine_reason": "；".join(quarantine_reasons),
            }
        elif data_quality.get("fallback") and raw_score >= 68:
            severity = {"level": "REVIEW", "label": "高分待核", "tone": "flat"}
        theme = anomaly_market_theme(symbol, "stock", meta)
        watch_priority = anomaly_watch_priority(raw_score, data_quality)
        waiting_conditions = anomaly_waiting_conditions(
            market_type="stock",
            change_pct=change_pct,
            range_pct=range_pct,
            location_pct=location_pct,
            volume_rank=volume_rank,
            tags=tags,
            data_quality=data_quality,
            theme=theme,
        )
        result.append({
            "time": now_ms(),
            "symbol": symbol,
            "market_type": "stock",
            "theme": theme,
            "rank": 100 + volume_rank,
            "price": round(last, 6),
            "change24h_pct": round(change_pct, 2),
            "range24h_pct": round(range_pct, 2),
            "location_pct": round(location_pct, 1),
            "volume": round(volume, 2),
            "volume_rank": volume_rank,
            "score": score,
            "raw_score": raw_score,
            "severity": severity["level"],
            "severity_label": severity["label"],
            "tone": severity["tone"],
            "direction": direction,
            "reason": " / ".join(tags[:3]),
            "type_tags": tags,
            "evidence": [
                f"{meta.get('sector', 'Stock')}，数据源 {row.get('source', 'stock')}",
                f"日内涨跌 {signed_pct_text(change_pct)}，区间位置 {location_pct:.1f}%",
                f"日内振幅 {range_pct:.2f}%，成交量排名 {volume_rank}",
            ],
            "watch_priority": watch_priority,
            "next_observation": waiting_conditions[0] if waiting_conditions else "等待下一轮雷达确认。",
            "waiting_conditions": waiting_conditions,
            "metrics": {
                "source": row.get("source", ""),
                "sector": meta.get("sector", ""),
                "market": meta.get("market", ""),
            },
            "data_quality": data_quality,
            "data_quarantined": data_quarantined,
            "quarantine_reason": "；".join(quarantine_reasons),
            "risk": "股票行情只用于研究和模拟验证，当前版本不接入真实股票下单",
            "safe_action": "观察 / 仅研究 / 仅模拟盘验证",
            "live_trading_allowed": False,
        })
    return sorted(result, key=lambda item: item["score"], reverse=True)[:limit]


def build_local_fallback_anomaly_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        payload = read_local_btc_daily(90)
        candles = payload.get("rows") or []
    except Exception:
        candles = []
        payload = {"source": "local"}
    parsed = []
    for row in candles[-80:]:
        try:
            close = pct(row.get("close", 0.0))
            high = pct(row.get("high", close))
            low = pct(row.get("low", close))
            volume = pct(row.get("volume", 0.0))
            if close <= 0:
                continue
            parsed.append({"close": close, "high": high, "low": low, "volume": volume})
        except Exception:
            continue
    if len(parsed) < 8:
        return rows
    last = parsed[-1]["close"]
    open_ref = parsed[-2]["close"] if len(parsed) >= 2 else parsed[0]["close"]
    high = max(item["high"] for item in parsed[-24:])
    low = min(item["low"] for item in parsed[-24:] if item["low"] > 0)
    change_pct = (last / max(open_ref, 1e-9) - 1) * 100
    range_pct = (high / max(low, 1e-9) - 1) * 100
    location_pct = (last - low) / max(high - low, 1e-9) * 100 if high > low else 50.0
    volume_now = average([item["volume"] for item in parsed[-10:]])
    volume_before = average([item["volume"] for item in parsed[-30:-10]] or [volume_now])
    volume_ratio = volume_now / max(volume_before, 1e-9) if volume_before > 0 else 0.0
    metrics = {"volume_ratio": round(volume_ratio, 2), "source": payload.get("source", "local_btc_daily")}
    tags = market_anomaly_tags(change_pct, range_pct, location_pct, 99, metrics)
    score = round(clamp(32 + abs(change_pct) * 4.5 + min(range_pct, 12) * 1.4 + clamp((volume_ratio - 1) * 10, 0, 12), 0, 100), 1)
    severity = market_anomaly_severity(score)
    data_quality = anomaly_data_quality(str(payload.get("source", "local_btc_daily")), "crypto", realtime=False, fallback=True)
    theme = anomaly_market_theme("BTC-USDT", "crypto-local")
    watch_priority = anomaly_watch_priority(score, data_quality)
    waiting_conditions = anomaly_waiting_conditions(
        market_type="crypto-local",
        change_pct=change_pct,
        range_pct=range_pct,
        location_pct=location_pct,
        volume_rank=99,
        tags=tags,
        data_quality=data_quality,
        theme=theme,
    )
    rows.append({
        "time": now_ms(),
        "symbol": "BTC-USDT",
        "market_type": "crypto-local",
        "theme": theme,
        "rank": 999,
        "price": round(last, 6),
        "change24h_pct": round(change_pct, 2),
        "range24h_pct": round(range_pct, 2),
        "location_pct": round(location_pct, 1),
        "volume": round(volume_now, 2),
        "volume_rank": 99,
        "score": score,
        "severity": severity["level"],
        "severity_label": severity["label"],
        "tone": severity["tone"],
        "direction": market_anomaly_direction(change_pct, location_pct),
        "reason": " / ".join(tags[:3]),
        "type_tags": tags,
        "evidence": [
            f"OKX实时雷达暂不可用，使用本地BTC日线兜底：{payload.get('source', 'local')}",
            f"最近样本涨跌 {signed_pct_text(change_pct)}，区间位置 {location_pct:.1f}%",
            f"近24样本振幅 {range_pct:.2f}%，量能约 {volume_ratio:.2f}x",
        ],
        "watch_priority": watch_priority,
        "next_observation": waiting_conditions[0] if waiting_conditions else "等待实时行情恢复后复核。",
        "waiting_conditions": waiting_conditions,
        "metrics": metrics,
        "data_quality": data_quality,
        "risk": "兜底数据只用于研究，必须等待实时行情恢复后再复核。",
        "safe_action": "观察 / 仅研究 / 仅模拟盘验证",
        "live_trading_allowed": False,
    })
    return rows


def local_btc_candles_for_ai(limit: int = 260) -> list[dict[str, float]]:
    try:
        payload = read_local_btc_daily(limit)
        source_rows = payload.get("rows") or []
    except Exception:
        source_rows = []
    rows: list[dict[str, float]] = []
    for index, row in enumerate(source_rows[-limit:]):
        try:
            close = pct(row.get("close", 0.0))
            if close <= 0:
                continue
            ts = int(pct(row.get("ts_ms", row.get("time", 0)), 0.0))
            if ts <= 0:
                date_text = str(row.get("date") or row.get("trading_date") or "")
                try:
                    ts = int(time.mktime(time.strptime(date_text, "%Y-%m-%d")) * 1000)
                except Exception:
                    ts = now_ms() - (len(source_rows) - index) * 86400000
            rows.append({
                "ts": ts,
                "open": pct(row.get("open", close)),
                "high": pct(row.get("high", close)),
                "low": pct(row.get("low", close)),
                "close": close,
                "volume": pct(row.get("volume", row.get("volume_quote", 0.0))),
            })
        except Exception:
            continue
    return rows


def market_sync_cards(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    crypto = [row for row in rows if str(row.get("market_type", "")).startswith("crypto")]
    stocks = [row for row in rows if row.get("market_type") == "stock"]
    priority_a = len([row for row in rows if (row.get("watch_priority") or {}).get("level") == "A"])
    priority_b = len([row for row in rows if (row.get("watch_priority") or {}).get("level") == "B"])
    priority_review = len([
        row for row in rows
        if (row.get("watch_priority") or {}).get("level") == "C"
        and (bool(row.get("data_quarantined")) or pct(row.get("raw_score", row.get("score", 0))) >= 68)
    ])
    trusted_high = len([
        row for row in rows
        if row.get("severity") in {"HIGH", "CRITICAL"}
        and not bool(row.get("data_quarantined"))
        and not bool((row.get("data_quality") or {}).get("fallback"))
    ])

    def balance(items: list[dict[str, Any]]) -> tuple[int, int]:
        up = len([item for item in items if pct(item.get("change24h_pct", 0)) > 0])
        down = len([item for item in items if pct(item.get("change24h_pct", 0)) < 0])
        return up, down

    crypto_up, crypto_down = balance(crypto)
    stock_up, stock_down = balance(stocks)
    cards = [
        {
            "label": "币种同步",
            "value": f"{crypto_up}涨 / {crypto_down}跌",
            "detail": "核心币种同向越多，趋势或风险偏好信号越强。",
            "tone": "up" if crypto_up > crypto_down else "down" if crypto_down > crypto_up else "flat",
        },
        {
            "label": "股票热度",
            "value": f"{stock_up}涨 / {stock_down}跌" if stocks else "等待缓存",
            "detail": "科技股、BTC代理股和指数ETF用于观察跨市场联动。",
            "tone": "up" if stock_up > stock_down else "down" if stock_down > stock_up else "flat",
        },
        {
            "label": "高严重度",
            "value": str(trusted_high),
            "detail": "只统计已通过数据质量检查的高关注项；缓存极值进入待核。",
            "tone": "down" if any(row.get("severity") == "CRITICAL" for row in rows) else "flat",
        },
        {
            "label": "可行动队列",
            "value": f"A {priority_a} / B {priority_b} / 待核 {priority_review}",
            "detail": "A优先看图，B等待确认；高分旧缓存不会冒充可行动信号。",
            "tone": "up" if priority_a else "flat",
        },
    ]
    return cards


def market_anomaly_radar(
    symbols_text: str = "",
    write_notification: bool = False,
    force: bool = False,
    *,
    persist_history: bool | None = None,
) -> dict[str, Any]:
    history_writable = not RUNTIME_READ_ONLY if persist_history is None else bool(persist_history)
    write_notification = bool(write_notification and history_writable)
    force = bool(force and history_writable)
    cache_key = str(symbols_text or "").strip().upper() or "ALL"
    previous_payload = ANOMALY_RADAR_CACHE.get("payload") if ANOMALY_RADAR_CACHE.get("key") == cache_key else None
    if not write_notification and not force and ANOMALY_RADAR_CACHE.get("key") == cache_key:
        cached = ANOMALY_RADAR_CACHE.get("payload")
        if isinstance(cached, dict) and now_ms() - int(ANOMALY_RADAR_CACHE.get("time") or 0) < 45_000:
            return {**cached, "cached": True, "cache_age_ms": now_ms() - int(ANOMALY_RADAR_CACHE.get("time") or 0)}
    deep_scan = bool(force or write_notification)
    crypto_symbols = [item.strip().upper() for item in symbols_text.split(",") if item.strip()] or [
        crypto_spot_symbol(base) for base in CORE_CRYPTO_BASES
    ]
    stock_symbols = [str(item.get("symbol") or "").upper() for item in STOCK_MARKETS if item.get("symbol")]
    quote_batch = market_quote_batch(
        [*crypto_symbols, *stock_symbols],
        force=deep_scan,
        consumer="anomaly_radar",
    )
    batch_rows = list(quote_batch.get("rows") or [])
    scanner = market_scanner(symbols_text, False, batch_rows)
    rows = [build_crypto_anomaly_row(row, index + 1, deep_scan) for index, row in enumerate(scanner.get("rows", [])[:12])]
    rows.extend(build_stock_anomaly_rows(
        18,
        allow_network=deep_scan,
        stock_rows=[row for row in batch_rows if is_stock_symbol(str(row.get("symbol") or row.get("instId") or ""))],
    ))
    if not rows:
        rows.extend(build_local_fallback_anomaly_rows())
    rows.sort(key=lambda item: item["score"], reverse=True)
    rows = rows[:30]
    previous_rows = list((previous_payload or {}).get("rows") or []) if isinstance(previous_payload, dict) else []
    rows = annotate_anomaly_progression(rows, previous_rows)
    progression = anomaly_progression_summary(rows)
    scan_depth = "deep" if deep_scan else "fast"
    saved_events = persist_anomaly_events(rows, scan_depth) if history_writable else 0
    previous_outcomes = {
        str(row.get("symbol") or "").upper(): dict(row.get("outcome") or {})
        for row in previous_rows
        if isinstance(row, dict) and isinstance(row.get("outcome"), dict)
    }
    outcome_update = (
        update_anomaly_event_outcomes(rows)
        if history_writable
        else {**anomaly_outcome_summary([]), "updated": 0, "outcomes": previous_outcomes}
    )
    current_outcomes = outcome_update.get("outcomes") or {}
    rows = [
        {**row, "outcome": current_outcomes.get(str(row.get("symbol") or "").upper(), {})}
        for row in rows
    ]
    evaluation = (
        read_anomaly_events(300, create_if_missing=True).get("evaluation")
        if history_writable
        else (previous_payload or {}).get("evaluation")
        if isinstance(previous_payload, dict)
        else None
    ) or anomaly_outcome_summary([])
    top = rows[0] if rows else {}
    top_reviewable = next(
        (row for row in rows if not bool((row.get("data_quality") or {}).get("fallback"))),
        {},
    )
    pending_review = len([
        row for row in rows
        if bool((row.get("data_quality") or {}).get("fallback"))
        and pct(row.get("raw_score", row.get("score", 0))) >= 68
    ])
    notify_target = top_reviewable or top
    if write_notification and notify_target:
        PROFILE.notify(
            "INFO",
            "行情异动雷达",
            f"{notify_target.get('symbol')} {notify_target.get('severity_label')}，{notify_target.get('reason')}，评分 {notify_target.get('score')}",
        )
    summary = (
        f"异动雷达已扫描 {len(rows)} 个标的"
        + (f"，{pending_review} 条高分缓存转入待核" if pending_review else "")
        + (
            f"；最高可复核：{top_reviewable.get('symbol')} / {top_reviewable.get('reason')} / {top_reviewable.get('severity_label')}"
            if top_reviewable else "；实时可复核队列等待数据源"
        )
        if rows else "异动雷达暂未发现可用标的，保持观察。"
    )
    if rows and progression.get("comparison_available"):
        summary = f"{summary}；{progression.get('summary')}"
    motion_card = {
        "label": "雷达变化",
        "value": (
            f"新 {progression.get('new', 0)} / 增强 {progression.get('strengthening', 0)} / 衰减 {progression.get('fading', 0)}"
            if progression.get("comparison_available") else "基线已建立"
        ),
        "detail": progression.get("summary", "下一轮开始比较异动变化。"),
        "tone": "up" if progression.get("new") or progression.get("strengthening") else "down" if progression.get("fading") else "flat",
    }
    confirmation_rate = evaluation.get("direction_confirmation_rate_pct")
    false_signal_rate = evaluation.get("false_signal_rate_pct")
    outcome_card = {
        "label": "信号后验",
        "value": (
            f"确认 {pct(confirmation_rate):.1f}%"
            if evaluation.get("sample_sufficient") and confirmation_rate is not None
            else f"完成 {evaluation.get('resolved', 0)}"
            if evaluation.get("resolved")
            else "积累样本"
        ),
        "detail": evaluation.get("summary", "从新事件开始积累后验样本。"),
        "tone": (
            "up" if evaluation.get("sample_sufficient") and pct(confirmation_rate) >= 60
            else "down" if evaluation.get("sample_sufficient") and pct(false_signal_rate) >= 60
            else "flat"
        ),
    }
    payload = {
        "ok": True,
        "mode": "market_research",
        "summary": summary,
        "rows": rows,
        "cards": [motion_card, outcome_card, *market_sync_cards(rows)],
        "progression": progression,
        "evaluation": evaluation,
        "outcome_update": {"updated": outcome_update.get("updated", 0)},
        "scanner": {
            "summary": scanner.get("summary", ""),
            "updated_at": scanner.get("updated_at"),
            "quote_batch": quote_batch.get("context") or {},
        },
        "quote_batch": quote_batch.get("context") or {},
        "scan_depth": scan_depth,
        "saved_events": saved_events,
        "history_persistence": "ENABLED" if history_writable else "READ_ONLY_SKIPPED",
        "read_only": not history_writable,
        "safe_action": "观察 / 仅研究 / 仅模拟盘验证",
        "live_trading_allowed": False,
        "updated_at": now_ms(),
    }
    if not write_notification:
        ANOMALY_RADAR_CACHE.update({"time": now_ms(), "key": cache_key, "payload": payload})
    return payload


def trend_structure_label(metrics: dict[str, Any]) -> tuple[str, str]:
    trend = pct(metrics.get("trend_score", 0.0))
    window_return = pct(metrics.get("window_return_pct", 0.0))
    location = pct(metrics.get("price_location_pct", 50.0), 50.0)
    volume_ratio = pct(metrics.get("volume_ratio", 1.0), 1.0)
    if trend > 0.22 and window_return > 1 and location >= 62:
        return "趋势偏多", "上涨结构占优，继续看量能是否确认突破。"
    if trend < -0.22 and window_return < -1 and location <= 38:
        return "趋势偏空", "下跌结构占优，反弹需要等待量价修复。"
    if location >= 78 and volume_ratio < 1.1:
        return "高位假突破风险", "价格接近区间上沿但量能确认不足。"
    if location <= 22 and volume_ratio < 1.1:
        return "低位假跌破风险", "价格接近区间下沿但尚未出现有效承接。"
    if pct(metrics.get("range_pct", 0.0)) >= 8:
        return "波动扩张", "区间振幅扩大，止损和仓位假设需要更保守。"
    return "震荡观察", "趋势证据不够集中，优先等待突破或回踩确认。"


def trend_analysis_cockpit(symbol: str = "BTC-USDT") -> dict[str, Any]:
    clean_symbol = (symbol or "BTC-USDT").upper()
    analysis_bar = "1d" if is_stock_symbol(clean_symbol) else "1H"
    analysis_session = "regular" if is_stock_symbol(clean_symbol) else "all"
    try:
        shared_snapshot = market_data_snapshot(
            clean_symbol,
            analysis_bar,
            260,
            analysis_session,
            True,
            False,
            False,
            "trend_cockpit",
        )
    except Exception:
        shared_snapshot = {}
    price = pct((shared_snapshot.get("quote") or {}).get("last", 0.0))
    shared_candles = list((shared_snapshot.get("candles") or {}).get("rows") or [])
    fallback_candles = local_btc_candles_for_ai(260) if clean_symbol == "BTC-USDT" else []
    if price <= 0 and fallback_candles:
        price = fallback_candles[-1]["close"]
    local = local_market_ai_analysis(
        clean_symbol,
        analysis_bar,
        price,
        [],
        {
            "source": "trend_cockpit",
            "shared_snapshot": shared_snapshot.get("context") or {},
            "snapshot_source": (shared_snapshot.get("source") or {}).get("primary", ""),
        },
        shared_candles or fallback_candles,
    )
    metrics = local.get("metrics") or {}
    long_plan = local.get("long_plan") or {}
    short_plan = local.get("short_plan") or {}
    structure, structure_detail = trend_structure_label(metrics)
    try:
        insights = market_insights(clean_symbol)
    except Exception as exc:
        insights = {"ok": False, "error": str(exc), "alerts": [], "metrics": {}}
    try:
        contract = contract_center(clean_symbol)
    except Exception as exc:
        contract = {"ok": False, "error": str(exc), "metrics": {}}

    long_rate = pct(long_plan.get("win_rate_pct", 50), 50)
    short_rate = pct(short_plan.get("win_rate_pct", 50), 50)
    preferred = "等待" if abs(long_rate - short_rate) < 4 else "偏多" if long_rate > short_rate else "偏空"
    key_levels = [
        {"label": "做多止盈区", "value": long_plan.get("take_profit", 0), "role": "resistance"},
        {"label": "做多止损区", "value": long_plan.get("stop_loss", 0), "role": "support"},
        {"label": "做空止盈区", "value": short_plan.get("take_profit", 0), "role": "support"},
        {"label": "做空止损区", "value": short_plan.get("stop_loss", 0), "role": "resistance"},
    ]
    evidence = list(local.get("evidence") or [])
    evidence.extend(str(item.get("title") or item.get("body") or "") for item in (insights.get("alerts") or [])[:3] if isinstance(item, dict))
    counter_evidence = [
        "胜率是基于当前K线样本、量能和规则估计，不代表未来确定结果。",
        "若价格先触发结构失效区，当前方向判断作废。",
    ]
    if pct(metrics.get("volume_ratio", 1.0), 1.0) < 1.0:
        counter_evidence.append("量能低于前窗，突破或跌破的确认质量不足。")
    if pct(metrics.get("range_pct", 0.0)) >= 8:
        counter_evidence.append("波动率扩张会放大止损触发概率，需降低仓位假设。")
    waiting_conditions = [
        "等待关键支撑/压力附近出现放量确认，再交给模拟盘验证。",
        "等待DeepSeek初评和GPT复核都能解释同一条证据链。",
        "若出现相反K线结构或盘口急变，重新生成驾驶舱。",
    ]
    cards = [
        {"label": "趋势状态", "value": structure, "detail": structure_detail, "tone": "up" if preferred == "偏多" else "down" if preferred == "偏空" else "flat"},
        {"label": "波动", "value": f"{pct(metrics.get('range_pct', 0.0)):.2f}%", "detail": f"ATR {pct(metrics.get('atr', 0.0)):.6g}，波动率 {pct(metrics.get('volatility_pct', 0.0)):.2f}%", "tone": "down" if pct(metrics.get("range_pct", 0.0)) >= 8 else "flat"},
        {"label": "量能", "value": f"{pct(metrics.get('volume_ratio', 0.0)):.2f}x", "detail": "大于1代表近窗口成交量高于前窗。", "tone": "up" if pct(metrics.get("volume_ratio", 0.0)) >= 1.35 else "flat"},
        {"label": "多空概率", "value": f"多 {long_rate:.1f}% / 空 {short_rate:.1f}%", "detail": "当前样本估计，仅研究和模拟盘验证。", "tone": "up" if long_rate > short_rate + 4 else "down" if short_rate > long_rate + 4 else "flat"},
        {"label": "关键价位", "value": f"{long_plan.get('stop_loss', '--')} / {long_plan.get('take_profit', '--')}", "detail": "左侧为多头结构失效参考，右侧为上方观察目标。", "tone": "flat"},
        {"label": "安全边界", "value": "仅研究", "detail": "不开放实盘真实下单，AI不能绕过风控。", "tone": "down"},
    ]
    anomaly = {
        "symbol": clean_symbol,
        "direction": preferred,
        "reason": structure,
        "score": round(max(long_rate, short_rate), 1),
        "evidence": evidence[:8],
        "safe_action": "观察 / 仅研究 / 仅模拟盘验证",
    }
    prompt = market_anomaly_ai_prompt(clean_symbol, anomaly, {"cards": cards, "local": local, "contract": contract, "insights": insights})
    return {
        "ok": True,
        "symbol": clean_symbol,
        "price": local.get("price", price),
        "bar": local.get("bar", "1H"),
        "source": local.get("source", "unknown"),
        "summary": f"{clean_symbol} 当前走势驾驶舱：{structure}，多头估计 {long_rate:.1f}%，空头估计 {short_rate:.1f}%，结论仅用于研究。",
        "preferred": preferred,
        "cards": cards,
        "metrics": metrics,
        "probabilities": {
            "long_win_rate_pct": round(long_rate, 1),
            "short_win_rate_pct": round(short_rate, 1),
            "estimate_note": "基于当前样本、量价结构和本地规则估计，不是保证性结论。",
        },
        "key_levels": key_levels,
        "evidence": evidence[:10],
        "counter_evidence": counter_evidence[:8],
        "waiting_conditions": waiting_conditions,
        "local_ai": local,
        "market_insights": insights,
        "contract_center": contract,
        "shared_snapshot": shared_snapshot.get("context") or {},
        "ai_prompt": prompt,
        "safe_action": "观察 / 仅研究 / 仅模拟盘验证",
        "live_trading_allowed": False,
        "updated_at": now_ms(),
    }


def market_regime_from_candles(symbol: str) -> dict[str, Any]:
    closes = []
    highs = []
    lows = []
    if is_stock_symbol(symbol):
        rows = read_stock_candles(symbol, 160).get("rows", [])
        for row in rows:
            try:
                closes.append(float(row.get("close") or 0))
                highs.append(float(row.get("high") or 0))
                lows.append(float(row.get("low") or 0))
            except Exception:
                continue
    else:
        rows = okx_rows("/api/v5/market/candles", {"instId": symbol, "bar": "1H", "limit": "120"})
        for row in reversed(rows):
            try:
                closes.append(float(row[4]))
                highs.append(float(row[2]))
                lows.append(float(row[3]))
            except Exception:
                continue
    if len(closes) < 30:
        return {"regime": "数据不足", "trend_pct": 0.0, "range_pct": 0.0}
    trend = (average(closes[-12:]) / max(average(closes[-48:]), 1e-9) - 1) * 100
    range_pct = (max(highs[-48:]) / max(min(lows[-48:]), 1e-9) - 1) * 100
    regime = "牛市/趋势偏多" if trend > 1.2 else "熊市/趋势偏空" if trend < -1.2 else "震荡市"
    return {"regime": regime, "trend_pct": round(trend, 2), "range_pct": round(range_pct, 2)}


def strategy_compare(symbol: str, price: float = 0.0) -> dict[str, Any]:
    if price <= 0:
        if is_stock_symbol(symbol):
            price = pct(read_stock_quote(symbol).get("last", "0"))
        else:
            ticker = okx_first("/api/v5/market/ticker", {"instId": symbol})
            price = pct(ticker.get("last", "0"))
    regime = market_regime_from_candles(symbol)
    rows = []
    for strategy in STRATEGIES:
        signal = evaluate_strategy_signal(strategy["id"], price, False, 0.0, 0.0, symbol=symbol)
        analysis = analyze_strategy_context(strategy["id"], symbol, price)
        score = (analysis.get("profit_probability", 0.5) * 100) + (signal.get("confidence", 0.0) * 20)
        if "趋势" in regime["regime"] and strategy["id"] in {"dual_ma", "momentum", "livermore", "turtle", "darvas", "anti_martingale"}:
            score += 8
        if "震荡" in regime["regime"] and strategy["id"] in {"grid", "bollinger", "rsi", "martingale"}:
            score += 8
        rows.append({
            "id": strategy["id"],
            "name": strategy["name"],
            "style": strategy["style"],
            "action": signal.get("action", "HOLD"),
            "reason": signal.get("reason", "--"),
            "probability_pct": round(float(analysis.get("profit_probability") or 0) * 100, 1),
            "score": round(clamp(score, 0, 100), 1),
            "enabled_condition": "评分>60 且风控正常",
            "stop_condition": "触发止损/回撤熔断/趋势失效",
        })
    rows.sort(key=lambda item: item["score"], reverse=True)
    return {"ok": True, "symbol": symbol, "price": round(price, 6), "regime": regime, "rows": rows}


def strategy_startup_candles(strategy_id: str, strategy_params: dict[str, Any] | None = None) -> int:
    strategy = choose_strategy(strategy_id)
    params = dict(strategy_params) if isinstance(strategy_params, dict) else dict(strategy.get("params") or {})
    return _strategy_startup_candles_for_params(strategy_id, params)


def score_row(name: str, score: float, detail: str) -> dict[str, Any]:
    score = round(clamp(score, 0, 100), 1)
    if score >= 72:
        status = "PASS"
        label = "通过"
    elif score >= 50:
        status = "WATCH"
        label = "观察"
    else:
        status = "BLOCK"
        label = "阻断"
    return {"name": name, "score": score, "status": status, "label": label, "detail": detail}


def strategy_doctor(symbol: str, strategy_id: str, price: float = 0.0, direction_mode: str = "LONG_ONLY") -> dict[str, Any]:
    if price <= 0:
        if is_stock_symbol(symbol):
            price = pct(read_stock_quote(symbol).get("last", "0"))
        else:
            ticker = okx_first("/api/v5/market/ticker", {"instId": symbol})
            price = pct(ticker.get("last", "0"))
    strategy = choose_strategy(strategy_id)
    direction_mode = choice(direction_mode, {"LONG_ONLY", "SHORT_ONLY"}, "LONG_ONLY")
    direction = trade_direction_from_mode(direction_mode)
    analysis = analyze_strategy_context(strategy_id, symbol, price, direction=direction)
    signal = evaluate_directional_strategy_signal(
        strategy_id,
        price,
        direction_mode,
        PAPER_ACCOUNT.position_qty,
        PAPER_ACCOUNT.entry_price,
        PAPER_ACCOUNT.last_scale_price,
        symbol=symbol,
    )
    regime = market_regime_from_candles(symbol)
    candles = strategy_candles_for_symbol(symbol, 420)
    candle_count = len(candles)
    startup = strategy_startup_candles(strategy_id)
    params = strategy.get("params", {})
    param_count = len(params)
    data_score = min(100.0, candle_count / max(startup, 1) * 100)
    signal_score = float(signal.get("confidence") or 0) * 100
    risk_reward = float(analysis.get("risk_reward") or 0.0)
    probability = float(analysis.get("profit_probability") or 0.5)
    risk_score = clamp((probability * 70) + min(risk_reward, 3.0) * 10, 0, 100)
    execution_score = 82 if PAPER_ACCOUNT.order_type in {"MARKET", "CURRENT", "LIMIT"} else 72
    overfit_score = clamp(92 - max(param_count - 4, 0) * 8 - (0 if candle_count >= startup * 2 else 18), 20, 100)
    prefix_invariance = causal_prefix_invariance_check(
        rows=candles,
        symbol=symbol,
        source="strategy-doctor",
        signal_factory=lambda _rows: build_strategy_signal_fn(strategy_id, params),
        position_pct=35,
        take_profit_pct=2.4,
        stop_loss_pct=1.2,
        startup_candles=startup,
        fee_rate=0.0005,
        slippage_bps=2.0,
        market="stock" if is_stock_symbol(symbol) else "crypto",
        signal_input=strategy_signal_input(strategy_id),
    )
    lookahead = strategy_lookahead_check(
        strategy,
        candle_count=candle_count,
        startup_candles=startup,
        rows=candles,
        prefix_invariance=prefix_invariance,
    )
    rows = [
        lookahead,
        score_row("数据准备", data_score, f"需要约 {startup} 根稳定K线，当前本地可用 {candle_count} 根；低于要求时不建议启动自动执行。"),
        score_row("信号清晰度", signal_score, f"当前信号 {signal.get('action', 'HOLD')}，置信度 {signal_score:.0f}%，原因：{signal.get('reason', '--')}"),
        score_row("风险收益", risk_score, f"{analysis.get('direction_label', '做多')} 概率 {probability * 100:.0f}%，盈亏比 {risk_reward:.2f}，止盈 {analysis.get('take_profit')} / 止损 {analysis.get('stop_loss')}"),
        score_row("执行适配", execution_score, f"当前委托 {PAPER_ACCOUNT.order_type}，保证金 {PAPER_ACCOUNT.margin_mode}，方向 {direction_mode}，默认只允许单向持仓。"),
        score_row("过拟合风险", overfit_score, f"参数数量 {param_count}，建议先做参数寻优、前向观察和蒙特卡洛压力测试。"),
    ]
    total_score = round(sum(item["score"] for item in rows) / max(len(rows), 1), 1)
    lifecycle = [
        {"stage": "模板", "status": "DONE", "detail": f"{strategy['name']} 已加载，风格 {strategy['style']}。"},
        {"stage": "指标", "status": "DONE" if candle_count >= startup else "WAIT", "detail": f"startup_candle_count={startup}，用于降低指标不稳定。"},
        {"stage": "入场/出场", "status": "DONE", "detail": "策略已拆分信号、止盈止损、移动风控和只减仓。"},
        {"stage": "回测/寻优", "status": "READY", "detail": "可运行回测寻优；上线前应比较收益、回撤、胜率、夏普。"},
        {"stage": "ARCHIVED PAPER", "status": "ARCHIVED", "detail": "Paper execution is archived; no execution authority is available."},
        {"stage": "实盘", "status": "BLOCKED", "detail": "实盘硬墙仍开启，未完成审计前不允许真实下单。"},
    ]
    guardrails = [
        {"name": "不使用未完成K线", "status": "PASS", "detail": "策略决策应基于完成K线，避免 repainting。"},
        {"name": "单向持仓", "status": "PASS", "detail": "当前只暴露只做多/只做空，不提供普通双开仓。"},
        {"name": "启动前风控", "status": "PASS" if risk_score >= 50 else "WATCH", "detail": "启动策略前检查止盈、止损、仓位、杠杆和方向。"},
        {"name": "仓位调整", "status": "READY", "detail": "支持马丁/反马丁加仓，但高风险策略应降低仓位并设置熔断。"},
        {"name": "交易后复盘", "status": "READY", "detail": "每个信号写入日志，后续应做失败样本归因。"},
    ]
    callbacks = [
        {"name": "custom_stake", "mapped": "仓位百分比/杠杆", "status": "READY"},
        {"name": "custom_stoploss", "mapped": "固定/百分比/移动止损", "status": "READY"},
        {"name": "custom_roi", "mapped": "AI/手动止盈与分批止盈", "status": "PARTIAL"},
        {"name": "confirm_entry", "mapped": "风控引擎预检查", "status": "READY"},
        {"name": "adjust_position", "mapped": "马丁/反马丁/只减仓", "status": "READY"},
        {"name": "order_filled", "mapped": "订单流和日志", "status": "PARTIAL"},
    ]
    playbook = [
        {"phase": "1. 选择方向", "detail": "先确定只做多或只做空，再让 AI 分别评估两边概率。"},
        {"phase": "2. 规则拆分", "detail": "入场、退出、止损、止盈、仓位调整分开显示，避免黑箱按钮。"},
        {"phase": "3. 回测寻优", "detail": "用参数组比较，不只看收益，还看最大回撤和胜率。"},
        {"phase": "4. 前向观察", "detail": "模拟盘连续观察，记录每个 HOLD/BUY/SELL 的解释。"},
        {"phase": "5. 审计上线", "detail": "只有实盘硬墙、API权限和急停链路全部完成后才允许实盘。"},
    ]
    monte_carlo = [
        {"scenario": "基准", "score": total_score, "detail": "当前参数和风险配置。"},
        {"scenario": "滑点扩大", "score": round(max(0, total_score - 8), 1), "detail": "盘口恶化或市价单成本上升。"},
        {"scenario": "波动冲击", "score": round(max(0, total_score - 14), 1), "detail": "大幅波动时止损可能更频繁触发。"},
        {"scenario": "信号乱序", "score": round(max(0, total_score - 10), 1), "detail": "用于观察策略是否依赖少数幸运交易。"},
    ]
    summary = f"{strategy['name']} · {analysis.get('direction_label', '做多')} · 体检 {total_score}/100 · {regime.get('regime', '--')}"
    return {
        "ok": True,
        "symbol": symbol,
        "price": round(price, 6),
        "strategy": strategy,
        "direction_mode": direction_mode,
        "direction": direction,
        "summary": summary,
        "score": total_score,
        "regime": regime,
        "analysis": analysis,
        "signal": signal,
        "rows": rows,
        "lookahead_check": lookahead,
        "lifecycle": lifecycle,
        "release_pipeline": strategy_release_pipeline(
            doctor_score=total_score,
            lookahead=lookahead,
            live_hard_block=LIVE_TRADING_HARD_BLOCK,
        ),
        "guardrails": guardrails,
        "callbacks": callbacks,
        "playbook": playbook,
        "monte_carlo": monte_carlo,
        "inspired_by": ["Freqtrade: strategy anatomy, hyperopt, callbacks", "Jesse: metrics, debug, optimize, Monte Carlo", "Hummingbot: connector abstraction and bot deployment"],
        "updated_at": now_ms(),
    }


def bot_blueprints() -> list[dict[str, Any]]:
    return [
        {
            "id": "dca_martingale",
            "name": "DCA / 马丁机器人",
            "family": "仓位分层",
            "inspired_by": "3Commas DCA / Safety Orders",
            "best_regime": "宽幅震荡或急跌反弹",
            "entry_source": "价格偏离锚点 + 分层安全单",
            "exit_source": "均价回归、分批止盈、移动止盈",
            "risk_controls": ["最大层数", "单日亏损熔断", "只减仓", "逐仓优先"],
            "status": "PARTIAL",
            "readiness": 67,
            "next": "补完整安全单阶梯、最大保证金占用、异常行情暂停。",
        },
        {
            "id": "grid",
            "name": "网格机器人",
            "family": "区间做市",
            "inspired_by": "Grid Bots / Hummingbot PMM",
            "best_regime": "震荡市、资金费率温和",
            "entry_source": "区间上下沿 + 盘口价差",
            "exit_source": "网格成交、库存再平衡",
            "risk_controls": ["网格上下界", "库存偏移", "突破暂停", "手续费过滤"],
            "status": "PARTIAL",
            "readiness": 61,
            "next": "补真实网格挂单簿、库存偏差、突破后停止补单。",
        },
        {
            "id": "trend_follower",
            "name": "趋势跟随机器人",
            "family": "动量/突破",
            "inspired_by": "Freqtrade / Jesse trend strategies",
            "best_regime": "单边趋势、突破后延续",
            "entry_source": "均线、通道、利弗莫尔关键点",
            "exit_source": "趋势失效、ATR止损、移动止盈",
            "risk_controls": ["startup K线", "回撤熔断", "波动仓位", "滑点估算"],
            "status": "ONLINE",
            "readiness": 76,
            "next": "补多周期确认和失败突破归因。",
        },
        {
            "id": "signal_webhook",
            "name": "信号机器人",
            "family": "外部信号",
            "inspired_by": "TradingView / Signal bots",
            "best_regime": "需要外部指标或人工研究接入",
            "entry_source": "Webhook、AI机会扫描、研究员信号",
            "exit_source": "信号反转、固定/移动风控",
            "risk_controls": ["信号冷却", "重复信号去重", "来源评分", "风控前置"],
            "status": "DESIGN",
            "readiness": 45,
            "next": "增加本地 webhook 接收器、签名校验和信号队列。",
        },
        {
            "id": "market_maker",
            "name": "盘口做市机器人",
            "family": "高频/报价",
            "inspired_by": "Hummingbot market making",
            "best_regime": "深度充足、价差稳定",
            "entry_source": "盘口深度、价差、库存偏差",
            "exit_source": "撤单重挂、库存再平衡",
            "risk_controls": ["最小价差", "最大库存", "撤单频率", "交易所限频"],
            "status": "DESIGN",
            "readiness": 38,
            "next": "补盘口深度统计、限频器和订单生命周期。",
        },
        {
            "id": "portfolio_rotation",
            "name": "组合轮动机器人",
            "family": "资产配置",
            "inspired_by": "Portfolio construction / rolling Sharpe",
            "best_regime": "多资产比较、趋势强弱分化",
            "entry_source": "相对强弱、波动率、资金费率",
            "exit_source": "排名下降、相关性升高、组合回撤",
            "risk_controls": ["单币上限", "相关性限制", "现金保留", "再平衡周期"],
            "status": "DESIGN",
            "readiness": 42,
            "next": "补组合层资金分配和跨标的相关性。",
        },
        {
            "id": "ml_filter",
            "name": "AI/ML过滤机器人",
            "family": "信号过滤",
            "inspired_by": "FreqAI / Jesse ML pipeline",
            "best_regime": "策略信号过多，需要二次筛选",
            "entry_source": "特征记录、模型概率、AI审计",
            "exit_source": "置信度下降、风险标签变化",
            "risk_controls": ["样本外验证", "过拟合检测", "特征漂移", "冷却间隔"],
            "status": "DESIGN",
            "readiness": 35,
            "next": "增加特征记录、标签生成和样本外评分。",
        },
    ]


def bot_blueprint_map() -> dict[str, dict[str, Any]]:
    return {row["id"]: row for row in bot_blueprints()}


def strategy_to_bot(strategy_id: str) -> str:
    if strategy_id in {"martingale", "anti_martingale"}:
        return "dca_martingale"
    if strategy_id in {"grid", "bollinger", "rsi"}:
        return "grid"
    if strategy_id in {"dual_ma", "macd", "momentum", "livermore", "turtle", "darvas"}:
        return "trend_follower"
    return "signal_webhook"


def default_bot_owner(symbol: str, preferred: list[str]) -> str:
    if PAPER_ACCOUNT.armed and PAPER_ACCOUNT.symbol == symbol:
        return strategy_to_bot(PAPER_ACCOUNT.strategy_id)
    return preferred[0] if preferred else "trend_follower"


def bot_center(symbol: str = "BTC-USDT", price: float = 0.0) -> dict[str, Any]:
    if price <= 0:
        if is_stock_symbol(symbol):
            price = pct(read_stock_quote(symbol).get("last", "0"))
        else:
            ticker = okx_first("/api/v5/market/ticker", {"instId": symbol})
            price = pct(ticker.get("last", "0"))
    regime = market_regime_from_candles(symbol)
    blueprints = bot_blueprints()
    regime_text = regime.get("regime", "")
    if "震荡" in regime_text:
        preferred = ["grid", "dca_martingale", "signal_webhook"]
    elif "偏空" in regime_text:
        preferred = ["trend_follower", "dca_martingale", "ml_filter"]
    else:
        preferred = ["trend_follower", "portfolio_rotation", "signal_webhook"]
    preferred_set = set(preferred)
    scheduler = PROFILE.bot_scheduler_for(symbol, preferred)
    active_bot = scheduler.get("active_bot") or default_bot_owner(symbol, preferred)
    for row in blueprints:
        row["recommended"] = row["id"] in preferred_set
        row["priority"] = preferred.index(row["id"]) + 1 if row["id"] in preferred_set else 99
        row["execution_role"] = "OWNER" if row["id"] == active_bot else "OBSERVER"
    blueprints.sort(key=lambda row: (row["priority"], -row["readiness"]))
    paper = PAPER_ACCOUNT.snapshot(price)
    connector_score = 86 if not is_stock_symbol(symbol) else 62
    layers = [
        {"name": "交易平台层", "status": "ONLINE", "score": 82, "detail": "行情、K线、盘口、合约行情中心、股票研究面板。"},
        {"name": "策略机器人层", "status": "PARTIAL", "score": 68, "detail": "已有模板、体检、回测、并行评分；缺 webhook/多机器人调度。"},
        {"name": "执行撮合层", "status": "PROTECTED", "score": 63, "detail": "模拟撮合已有，需拆成事件队列和订单生命周期。"},
        {"name": "风控资金层", "status": "PROTECTED", "score": 74, "detail": "实盘硬墙、熔断、仓位、保证金；需组合层风险预算。"},
        {"name": "监控审计层", "status": "PARTIAL", "score": 60, "detail": "日志、通知、守护进程；需机器人级健康检查。"},
        {"name": "AI研究层", "status": "ONLINE", "score": 66, "detail": "AI分析和Code Worker；需特征记录和样本外审计。"},
        {"name": "交易所连接层", "status": "PARTIAL", "score": connector_score, "detail": "OKX公开行情可用，实盘接口仍默认阻断；股票交易接口未接入。"},
    ]
    allocations = [
        {"bucket": "现金/等待", "pct": 35, "reason": "v2阶段保留现金，避免机器人未成熟时满仓。"},
        {"bucket": "趋势机器人", "pct": 25 if preferred[0] == "trend_follower" else 15, "reason": "用于突破/趋势行情，只走单向仓。"},
        {"bucket": "网格/DCA", "pct": 20 if "震荡" in regime_text else 12, "reason": "震荡时提高，趋势时降低，避免逆势摊平过重。"},
        {"bucket": "AI信号/研究", "pct": 8, "reason": "只用于机会发现和模拟验证，不直接实盘。"},
        {"bucket": "组合轮动", "pct": 12, "reason": "未来扩展到 BTC/ETH/DOGE 和股票观察池。"},
    ]
    gaps = [
        {"gap": "多机器人调度器", "priority": "P0", "detail": "需要同一标的只允许一个机器人拥有执行权，其他机器人只观察。"},
        {"gap": "事件驱动执行队列", "priority": "P0", "detail": "订单创建、挂单、部分成交、撤单、手续费、资金费率必须统一。"},
        {"gap": "组合风险预算", "priority": "P1", "detail": "按机器人/标的/方向设置最大风险，而不是只看单笔仓位。"},
        {"gap": "Webhook信号接收器", "priority": "P1", "detail": "接入TradingView/外部AI信号，需要签名、去重、冷却。"},
        {"gap": "样本外和蒙特卡洛", "priority": "P1", "detail": "防止只在历史上漂亮，加入随机扰动和交易顺序压力测试。"},
        {"gap": "机器人级运行日志", "priority": "P1", "detail": "每个机器人必须解释为什么买、为什么不买、为什么卖。"},
    ]
    summary = f"{symbol} · {regime_text or '未知市场'} · 执行权 {bot_blueprint_map().get(active_bot, {}).get('name', active_bot)} · 实盘仍阻断"
    return {
        "ok": True,
        "symbol": symbol,
        "price": round(price, 6),
        "summary": summary,
        "regime": regime,
        "paper": {
            "armed": paper.get("armed"),
            "strategy": (paper.get("strategy") or {}).get("name"),
            "position_side": paper.get("position_side"),
            "direction_mode": paper.get("direction_mode"),
            "risk_status": paper.get("risk_status"),
        },
        "recommended": preferred,
        "scheduler": scheduler,
        "blueprints": blueprints,
        "layers": layers,
        "allocations": allocations,
        "gaps": gaps,
        "rules": [
            "交易平台负责行情、订单、账户、图表；机器人负责信号、风控、执行意图。",
            "同一标的默认单向持仓，不让多个机器人抢同一执行权。",
            "AI只给研究和过滤，不直接跳过风控下单。",
            "所有机器人先模拟盘、再前向观察、最后才考虑实盘授权。",
        ],
        "references": [
            "Freqtrade: backtesting, hyperopt, callbacks, strategy anatomy",
            "Jesse: metrics, debug, optimize, Monte Carlo, ML pipeline",
            "Hummingbot: exchange connectors, market making, deployment",
        ],
        "updated_at": now_ms(),
    }


def strategy_robot_profiles(symbol: str = "BTC-USDT", price: float = 0.0) -> dict[str, Any]:
    compare = strategy_compare(symbol, price)
    compare_rows = {row["id"]: row for row in compare.get("rows", [])}
    regime = compare.get("regime", {})
    installed = set(PROFILE.installed_strategy_plugins)
    bot_map = bot_blueprint_map()
    scheduler = PROFILE.bot_scheduler_for(symbol, [strategy_to_bot((compare.get("rows") or [{"id": "dual_ma"}])[0]["id"])])
    active_bot = scheduler.get("active_bot")
    if is_stock_symbol(symbol):
        data_points = len(read_stock_candles(symbol, 240, "1d", "all").get("rows", []))
    elif symbol.upper().replace("-SWAP", "") == "BTC-USDT":
        data_points = len(read_local_btc_daily(240).get("rows", []))
    else:
        data_points = len(okx_rows("/api/v5/market/candles", {"instId": symbol, "bar": "1Dutc", "limit": "120"}))
    rows: list[dict[str, Any]] = []
    for strategy in STRATEGIES:
        strategy_id = strategy["id"]
        score_info = compare_rows.get(strategy_id, {})
        playbook = strategy_playbook(strategy_id)
        bot_id = strategy_to_bot(strategy_id)
        bot = bot_map.get(bot_id, {})
        startup = strategy_startup_candles(strategy_id)
        data_score = clamp(data_points / max(startup, 1) * 100, 0, 100)
        market_score = float(score_info.get("score") or 0)
        install_score = 12 if strategy_id in installed else -18
        readiness = clamp(market_score * 0.62 + data_score * 0.23 + install_score + min(len(strategy.get("params", {})), 8), 0, 100)
        if strategy_id not in installed:
            status = "BLOCK"
            status_label = "未安装"
        elif data_points < startup:
            status = "WATCH"
            status_label = "数据不足"
        elif readiness >= 72:
            status = "PASS"
            status_label = "可模拟"
        elif readiness >= 52:
            status = "WATCH"
            status_label = "观察"
        else:
            status = "BLOCK"
            status_label = "不建议"
        rows.append({
            "id": strategy_id,
            "name": strategy["name"],
            "style": strategy["style"],
            "installed": strategy_id in installed,
            "bot_id": bot_id,
            "bot_name": bot.get("name", bot_id),
            "bot_family": bot.get("family", "--"),
            "owner": bot_id == active_bot,
            "readiness": round(readiness, 1),
            "status": status,
            "status_label": status_label,
            "market_action": score_info.get("action", "HOLD"),
            "probability_pct": score_info.get("probability_pct", 0),
            "market_score": market_score,
            "data_points": data_points,
            "startup_candles": startup,
            "best_regime": playbook.get("best_regime", "--"),
            "avoid_regime": playbook.get("avoid_regime", "--"),
            "start_condition": score_info.get("enabled_condition", "评分>60 且风控正常"),
            "stop_condition": score_info.get("stop_condition", "触发止损/回撤熔断/趋势失效"),
            "reason": score_info.get("reason", "--"),
            "next": (
                "先安装策略模板" if strategy_id not in installed else
                "补足历史K线后再启动" if data_points < startup else
                "可进入模拟盘前向观察" if readiness >= 72 else
                "等待行情与风控评分改善"
            ),
        })
    rows.sort(key=lambda item: (item["status"] != "PASS", -float(item["readiness"])))
    ready_count = len([row for row in rows if row["status"] == "PASS"])
    return {
        "ok": True,
        "symbol": symbol,
        "regime": regime,
        "data_points": data_points,
        "summary": f"{symbol} 机器人档案：{ready_count}/{len(rows)} 个可进入模拟观察 · {regime.get('regime', '--')}",
        "rows": rows,
        "rules": [
            "机器人档案只决定模拟和研究优先级，不直接授权实盘。",
            "同一标的一次只允许一个机器人拥有执行权，其余只能观察。",
            "启动前必须满足数据准备、风控正常、策略已安装和回测/前向观察要求。",
        ],
        "updated_at": now_ms(),
    }


def bot_scheduler_snapshot(symbol: str = "BTC-USDT", price: float = 0.0) -> dict[str, Any]:
    center = bot_center(symbol, price)
    scheduler = center["scheduler"]
    active_bot = scheduler.get("active_bot")
    blueprints = center.get("blueprints", [])
    candidates = []
    for row in blueprints:
        readiness = float(row.get("readiness") or 0)
        recommended_bonus = 12 if row.get("recommended") else 0
        owner_bonus = 8 if row.get("id") == active_bot else 0
        score = clamp(readiness + recommended_bonus + owner_bonus, 0, 100)
        candidates.append({
            "id": row["id"],
            "name": row["name"],
            "family": row["family"],
            "role": "OWNER" if row["id"] == active_bot else "OBSERVER",
            "recommended": bool(row.get("recommended")),
            "readiness": row.get("readiness"),
            "score": round(score, 1),
            "can_execute": row["id"] == active_bot,
            "status": row.get("status"),
            "reason": row.get("next"),
        })
    conflicts = []
    if PAPER_ACCOUNT.armed and PAPER_ACCOUNT.symbol == symbol:
        paper_bot = strategy_to_bot(PAPER_ACCOUNT.strategy_id)
        if active_bot and active_bot != paper_bot:
            conflicts.append({
                "level": "WARN",
                "message": f"当前模拟策略属于 {paper_bot}，但执行权 owner 是 {active_bot}，建议切换或停止策略。",
            })
    if not active_bot:
        conflicts.append({"level": "WARN", "message": "当前标的尚未设置执行权 owner。"})
    return {
        "ok": True,
        "symbol": symbol,
        "price": center.get("price", 0.0),
        "active_bot": active_bot,
        "active_name": bot_blueprint_map().get(active_bot, {}).get("name", active_bot or "--"),
        "mode": scheduler.get("mode", "paper"),
        "locked": bool(active_bot),
        "summary": f"{symbol} 执行权：{bot_blueprint_map().get(active_bot, {}).get('name', active_bot or '未设置')}；观察者 {max(len(candidates) - 1, 0)} 个",
        "candidates": candidates,
        "conflicts": conflicts,
        "rules": [
            "一个标的一次只能有一个 OWNER。",
            "OWNER 可向模拟执行层提交动作；OBSERVER 只能评分、解释和提醒。",
            "切换 OWNER 不会自动下单，只改变后续机器人执行权。",
            "如果已有持仓，切换前应先检查止盈止损和只减仓状态。",
        ],
        "updated_at": now_ms(),
    }


def bot_scheduler_assign(symbol: str, bot_id: str, mode: str = "paper") -> dict[str, Any]:
    available = bot_blueprint_map()
    clean_symbol = (symbol or "BTC-USDT").upper()
    if bot_id not in available:
        return {"ok": False, "error": f"未知机器人 {bot_id}", "scheduler": bot_scheduler_snapshot(clean_symbol)}
    PROFILE.assign_bot_owner(clean_symbol, bot_id, mode)
    append_ledger({"type": "bot_owner_assign", "symbol": clean_symbol, "bot_id": bot_id, "mode": mode})
    return {"ok": True, "scheduler": bot_scheduler_snapshot(clean_symbol)}


def bot_scheduler_release(symbol: str) -> dict[str, Any]:
    clean_symbol = (symbol or "BTC-USDT").upper()
    PROFILE.release_bot_owner(clean_symbol)
    append_ledger({"type": "bot_owner_release", "symbol": clean_symbol})
    return {"ok": True, "scheduler": bot_scheduler_snapshot(clean_symbol)}


def strategy_war_room(symbol: str, strategy_id: str, price: float = 0.0, risk_config: dict[str, Any] | None = None) -> dict[str, Any]:
    risk_config = risk_config or {}
    if price <= 0:
        if is_stock_symbol(symbol):
            price = pct(read_stock_quote(symbol).get("last", "0"))
        else:
            ticker = okx_first("/api/v5/market/ticker", {"instId": symbol})
            price = pct(ticker.get("last", "0"))
    strategy = choose_strategy(strategy_id)
    direction_mode = choice(risk_config.get("direction_mode"), {"LONG_ONLY", "SHORT_ONLY"}, "LONG_ONLY")
    direction = trade_direction_from_mode(direction_mode)
    analysis = analyze_strategy_context(
        strategy_id,
        symbol,
        price,
        float(risk_config.get("manual_take_profit") or 0.0),
        float(risk_config.get("manual_stop_loss") or 0.0),
        direction,
    )
    signal = evaluate_directional_strategy_signal(
        strategy_id,
        price,
        direction_mode,
        PAPER_ACCOUNT.position_qty,
        PAPER_ACCOUNT.entry_price,
        PAPER_ACCOUNT.last_scale_price,
        symbol=symbol,
    )
    doctor = strategy_doctor(symbol, strategy_id, price, direction_mode)
    compare = strategy_compare(symbol, price)
    scheduler = bot_scheduler_snapshot(symbol, price)
    bot_id = strategy_to_bot(strategy_id)
    bot_name = bot_blueprint_map().get(bot_id, {}).get("name", bot_id)
    active_bot = scheduler.get("active_bot", "")
    bot_role = "OWNER" if active_bot == bot_id else "OBSERVER"
    probability = float(analysis.get("profit_probability") or 0.0)
    risk_reward = float(analysis.get("risk_reward") or 0.0)
    doctor_score = float(doctor.get("score") or 0.0)
    signal_confidence = float(signal.get("confidence") or 0.0) * 100
    can_trade = (
        price > 0
        and bot_role == "OWNER"
        and doctor_score >= 60
        and probability >= 0.48
        and risk_reward >= 0.8
        and signal.get("action") not in {"HOLD", ""}
        and not risk_config.get("reduce_only")
    )
    mission_status = "READY" if can_trade else "WATCH" if doctor_score >= 50 and probability >= 0.42 else "BLOCK"
    mission_label = "可模拟执行" if mission_status == "READY" else "观察等待" if mission_status == "WATCH" else "暂不交易"

    take_profit = float(analysis.get("take_profit") or 0.0)
    stop_loss = float(analysis.get("stop_loss") or 0.0)
    if direction == "SHORT":
        entry_ladder = [
            {"name": "侦察仓", "price": round(price, 4), "size_pct": 25, "rule": "信号确认后只开小仓"},
            {"name": "确认仓", "price": round(price * 1.006, 4), "size_pct": 35, "rule": "反弹不破压力再加仓"},
            {"name": "防守仓", "price": round(max(stop_loss, price * 1.012), 4), "size_pct": 0, "rule": "触及则停止加仓并检查止损"},
        ]
        exit_ladder = [
            {"name": "第一止盈", "price": round(price - (price - take_profit) * 0.45, 4) if take_profit else 0.0, "size_pct": 35, "rule": "先减风险"},
            {"name": "核心止盈", "price": round(take_profit, 4), "size_pct": 45, "rule": "达到AI目标后分批减仓"},
            {"name": "止损线", "price": round(stop_loss, 4), "size_pct": 100, "rule": "只减仓/平仓，不反手"},
        ]
    else:
        entry_ladder = [
            {"name": "侦察仓", "price": round(price, 4), "size_pct": 25, "rule": "信号确认后只开小仓"},
            {"name": "确认仓", "price": round(price * 0.994, 4), "size_pct": 35, "rule": "回踩不破支撑再加仓"},
            {"name": "防守仓", "price": round(min(stop_loss or price, price * 0.988), 4), "size_pct": 0, "rule": "触及则停止加仓并检查止损"},
        ]
        exit_ladder = [
            {"name": "第一止盈", "price": round(price + (take_profit - price) * 0.45, 4) if take_profit else 0.0, "size_pct": 35, "rule": "先收回部分风险"},
            {"name": "核心止盈", "price": round(take_profit, 4), "size_pct": 45, "rule": "达到AI目标后分批减仓"},
            {"name": "止损线", "price": round(stop_loss, 4), "size_pct": 100, "rule": "只减仓/平仓，不反手"},
        ]

    matrix = [
        {"name": "市场状态", "status": "INFO", "score": round(float(compare.get("regime", {}).get("range_pct") or 0), 1), "detail": compare.get("regime", {}).get("regime", "--")},
        {"name": "策略信号", "status": "PASS" if signal.get("action") not in {"HOLD", ""} else "WATCH", "score": round(signal_confidence, 1), "detail": f"{signal.get('action', 'HOLD')} · {signal.get('reason', '--')}"},
        {"name": "盈利概率", "status": "PASS" if probability >= 0.55 else "WATCH" if probability >= 0.45 else "BLOCK", "score": round(probability * 100, 1), "detail": f"盈亏比 {risk_reward:.2f}，历史命中 {float(analysis.get('historical_hit_rate') or 0) * 100:.0f}%"},
        {"name": "策略体检", "status": "PASS" if doctor_score >= 70 else "WATCH" if doctor_score >= 50 else "BLOCK", "score": round(doctor_score, 1), "detail": doctor.get("summary", "--")},
        {"name": "机器人执行权", "status": "PASS" if bot_role == "OWNER" else "BLOCK", "score": 100 if bot_role == "OWNER" else 35, "detail": f"{bot_name} 当前为 {bot_role}，活动 owner={active_bot or '--'}"},
        {"name": "实盘闸门", "status": "BLOCK", "score": 0, "detail": "当前仍只允许模拟/观察，真实下单保持阻断"},
    ]
    no_trade = []
    if bot_role != "OWNER":
        no_trade.append("当前策略对应机器人没有执行权，先在调度器点击接管。")
    if signal.get("action") in {"HOLD", ""}:
        no_trade.append("策略信号仍为 HOLD，不应为了交易而交易。")
    if probability < 0.45:
        no_trade.append("盈利概率低于 45%，等待更清晰的位置。")
    if risk_reward < 0.8:
        no_trade.append("盈亏比不足 0.8，止盈止损结构不合格。")
    if doctor_score < 50:
        no_trade.append("策略体检分数低于 50，先修参数或换策略。")
    if risk_config.get("reduce_only"):
        no_trade.append("当前启用只减仓，新开仓会被阻断。")
    hard_no_trade = bool(no_trade)
    if not no_trade:
        no_trade.append("无硬阻断；仍建议先跑模拟盘和观察日志。")

    timeline = [
        {"step": "1", "name": "读取行情", "status": "DONE", "detail": f"{symbol} 最新价 {price:.4f}"},
        {"step": "2", "name": "策略判定", "status": "DONE", "detail": f"{strategy['name']} 输出 {signal.get('action', 'HOLD')}"},
        {"step": "3", "name": "AI风控", "status": "DONE", "detail": f"止盈 {take_profit:.4f} / 止损 {stop_loss:.4f}"},
        {"step": "4", "name": "执行权检查", "status": "DONE" if bot_role == "OWNER" else "BLOCK", "detail": f"{bot_name}={bot_role}"},
        {"step": "5", "name": "模拟执行", "status": mission_status, "detail": mission_label},
    ]
    cards = [
        {"name": "作战结论", "value": mission_label, "status": mission_status, "detail": f"{strategy['name']} · {analysis.get('direction_label', '--')}"},
        {"name": "策略动作", "value": signal.get("action", "HOLD"), "status": matrix[1]["status"], "detail": signal.get("reason", "--")},
        {"name": "概率/盈亏比", "value": f"{probability * 100:.0f}% / {risk_reward:.2f}", "status": matrix[2]["status"], "detail": analysis.get("probability_level", "--")},
        {"name": "执行机器人", "value": bot_name, "status": "PASS" if bot_role == "OWNER" else "BLOCK", "detail": bot_role},
        {"name": "委托/保证金", "value": f"{risk_config.get('order_type', PAPER_ACCOUNT.order_type)} / {risk_config.get('margin_mode', PAPER_ACCOUNT.margin_mode)}", "status": "INFO", "detail": f"杠杆 {float(risk_config.get('leverage') or PAPER_ACCOUNT.leverage):g}x，仓位 {float(risk_config.get('position_pct') or PAPER_ACCOUNT.position_pct):g}%"},
        {"name": "风控模式", "value": "只减仓" if risk_config.get("reduce_only") else "可开仓", "status": "WATCH" if risk_config.get("reduce_only") else "PASS", "detail": f"移动止盈 {risk_config.get('trailing_take_pct', PAPER_ACCOUNT.trailing_take_pct)}% / 移动止损 {risk_config.get('trailing_stop_pct', PAPER_ACCOUNT.trailing_stop_pct)}%"},
    ]
    playbook = strategy_playbook(strategy_id)
    anchor_plan = strategy_anchor_plan(strategy_id, direction, price, analysis, risk_config)
    execution_log = [
        {
            "level": "INFO",
            "title": "为什么不直接实盘",
            "detail": "系统保持实盘硬锁，当前所有策略动作只进入模拟/观察层。",
        },
        {
            "level": "PASS" if signal.get("action") not in {"HOLD", ""} else "WATCH",
            "title": f"为什么{signal.get('action', 'HOLD')}",
            "detail": signal.get("reason", "策略没有给出明确动作。"),
        },
        {
            "level": "PASS" if probability >= 0.55 else "WATCH" if probability >= 0.45 else "BLOCK",
            "title": "盈利概率判断",
            "detail": f"当前概率 {probability * 100:.0f}%，盈亏比 {risk_reward:.2f}；低概率时只观察。",
        },
        {
            "level": "PASS" if bot_role == "OWNER" else "BLOCK",
            "title": "机器人执行权",
            "detail": f"{bot_name} 当前角色为 {bot_role}；只有 OWNER 才能向模拟执行层提交动作。",
        },
        {
            "level": "WATCH" if hard_no_trade else "PASS",
            "title": "禁用条件检查",
            "detail": "；".join(no_trade[:2]) if no_trade else "未发现硬性禁用条件。",
        },
    ]
    return {
        "ok": True,
        "symbol": symbol,
        "price": round(price, 6),
        "strategy": strategy,
        "direction": direction,
        "direction_mode": direction_mode,
        "summary": f"{symbol} · {strategy['name']} · {mission_label} · {analysis.get('direction_label', '--')}",
        "mission_status": mission_status,
        "mission_label": mission_label,
        "analysis": analysis,
        "signal": signal,
        "doctor_score": round(doctor_score, 1),
        "bot": {"id": bot_id, "name": bot_name, "role": bot_role, "active_bot": active_bot},
        "playbook": playbook,
        "anchor_plan": anchor_plan,
        "execution_log": execution_log,
        "cards": cards,
        "matrix": matrix,
        "entry_ladder": entry_ladder,
        "exit_ladder": exit_ladder,
        "no_trade": no_trade,
        "timeline": timeline,
        "top_strategies": (compare.get("rows") or [])[:5],
        "updated_at": now_ms(),
    }


def read_rss_items(url: str, source: str, limit: int = 6) -> list[dict[str, Any]]:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Python-Quant-Exchange-Terminal/0.1"})
        with urllib.request.urlopen(request, timeout=8) as response:
            root = ET.fromstring(response.read())
        items = []
        for item in root.findall(".//item")[:limit]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            published = (item.findtext("pubDate") or "").strip()
            if title:
                items.append({"source": source, "title": title, "link": link, "published": published})
        return items
    except Exception:
        return []


def yahoo_raw(value: Any, default: Any = "") -> Any:
    if isinstance(value, dict):
        if "fmt" in value and value.get("fmt") not in {None, ""}:
            return value.get("fmt")
        if "raw" in value:
            return value.get("raw")
    if value is None or value == "":
        return default
    return value




def yahoo_quote_summary(symbol: str) -> dict[str, Any]:
    meta = stock_meta(symbol)
    modules = "calendarEvents,summaryDetail,financialData,defaultKeyStatistics,earningsTrend"
    url = "https://query1.finance.yahoo.com/v10/finance/quoteSummary/" + urllib.parse.quote(yahoo_stock_symbol(meta["symbol"])) + "?" + urllib.parse.urlencode({"modules": modules})
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 HakimiTrade/2.0"})
        with urllib.request.urlopen(request, timeout=min(STOCK_HISTORY_TIMEOUT + 1, 1.8)) as response:
            payload = json.loads(response.read().decode("utf-8", errors="ignore"))
        result = ((payload.get("quoteSummary") or {}).get("result") or [{}])[0]
        return result if isinstance(result, dict) else {}
    except Exception:
        return {}


def read_stock_rss_items_fast(url: str, source: str, limit: int = 4) -> list[dict[str, Any]]:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 HakimiTrade/2.0"})
        with urllib.request.urlopen(request, timeout=1.4) as response:
            root = ET.fromstring(response.read())
        items: list[dict[str, Any]] = []
        for item in root.findall(".//item")[:limit]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            published = (item.findtext("pubDate") or "").strip()
            if title:
                items.append({"source": source, "title": title, "link": link, "published": published})
        return items
    except Exception:
        return []


def lightweight_stock_quote(symbol: str, max_age_ms: int = 600000) -> dict[str, Any]:
    meta = stock_meta(symbol)
    cached = STOCK_SINGLE_QUOTE_CACHE.get(meta["symbol"]) or {}
    if now_ms() - int(cached.get("time") or 0) < max_age_ms and isinstance(cached.get("quote"), dict):
        return dict(cached["quote"])
    return stock_seed_quote(meta["symbol"])
















def stock_news_items(symbol: str, limit: int = 8) -> list[dict[str, Any]]:
    meta = stock_meta(symbol)
    news: list[dict[str, Any]] = []
    yahoo_symbol = yahoo_stock_symbol(meta["symbol"])
    rss_urls = [
        ("Yahoo Finance", "https://feeds.finance.yahoo.com/rss/2.0/headline?" + urllib.parse.urlencode({"s": yahoo_symbol, "region": "US", "lang": "en-US"})),
        ("Yahoo Finance Market", "https://feeds.finance.yahoo.com/rss/2.0/headline?" + urllib.parse.urlencode({"s": "^GSPC", "region": "US", "lang": "en-US"})),
    ]
    seen_titles: set[str] = set()
    for source, url in rss_urls:
        for item in read_rss_items(url, source, limit):
            title = str(item.get("title") or "").strip()
            if title and title not in seen_titles:
                seen_titles.add(title)
                news.append({**item, "source": source, "category": "股票新闻"})
            if len(news) >= limit:
                return news[:limit]

    quote = lightweight_stock_quote(meta["symbol"])
    change = pct(quote.get("change24h_pct", 0.0))
    session = stock_session_snapshot(meta["symbol"], quote)
    unusual = stock_unusual_activity(meta["symbol"], quote)
    return [
        {
            "source": "本地股票摘要",
            "title": f"{meta['symbol']} {meta.get('name', '')}: 现价 {pct(quote.get('last')):.2f}, 当日 {change:+.2f}%",
            "published": session.get("updated_label", ""),
            "link": "",
            "category": "行情快照",
        },
        {
            "source": "本地股票摘要",
            "title": f"{meta.get('sector', 'Stock')} 同业联动需要复核：观察同组股票是否同步放量或分化。",
            "published": "",
            "link": "",
            "category": "行业联动",
        },
        {
            "source": "异常成交摘要",
            "title": unusual.get("headline", "等待成交量、跳空、振幅异常样本。"),
            "published": unusual.get("updated_label", ""),
            "link": "",
            "category": "异常成交",
        },
    ][:limit]


def stock_session_snapshot(symbol: str, quote: dict[str, Any] | None = None) -> dict[str, Any]:
    meta = stock_meta(symbol)
    quote = quote or lightweight_stock_quote(meta["symbol"])
    payload = read_stock_persistent_candle_cache(meta["symbol"], 260, "1m", "all") or {
        "rows": [],
        "source": quote.get("source", "quote"),
        "latest_at": quote.get("time", ""),
        "latest_ts": quote.get("ts", now_ms()),
    }
    rows = list(payload.get("rows") or [])
    latest_ts = int(pct(payload.get("latest_ts", 0), 0)) or max([int(pct(row.get("ts", 0), 0)) for row in rows] or [0])
    latest_date = datetime.fromtimestamp(latest_ts / 1000, stock_timezone(meta["symbol"])).strftime("%Y-%m-%d") if latest_ts else ""
    today_rows: list[dict[str, Any]] = []
    for row in rows:
        ts = int(pct(row.get("ts", 0), 0))
        if latest_date and ts and datetime.fromtimestamp(ts / 1000, stock_timezone(meta["symbol"])).strftime("%Y-%m-%d") == latest_date:
            today_rows.append(row)
    sessions: dict[str, list[dict[str, Any]]] = {"pre": [], "regular": [], "post": [], "overnight": []}
    for row in today_rows:
        session = str(row.get("session") or stock_session_from_ts(int(pct(row.get("ts", 0), 0)), meta["symbol"]))
        if session in sessions:
            sessions[session].append(row)

    def session_row(label: str, key: str) -> dict[str, Any]:
        items = sessions.get(key, [])
        if not items:
            return {"label": label, "session": key, "status": "WAIT", "detail": "暂无该时段样本", "tone": "flat"}
        first = pct(items[0].get("open", items[0].get("close", 0)))
        last = pct(items[-1].get("close", first))
        change = (last / max(first, 1e-9) - 1) * 100 if first > 0 and last > 0 else 0.0
        volume = sum(pct(item.get("volume", 0)) for item in items)
        return {
            "label": label,
            "session": key,
            "status": "READY",
            "detail": f"收 {last:.2f} / {change:+.2f}% / 量 {volume:.0f}",
            "change_pct": round(change, 2),
            "last": round(last, 4),
            "volume": round(volume, 2),
            "tone": "up" if change > 0 else "down" if change < 0 else "flat",
        }

    source = payload.get("source", quote.get("source", "stock"))
    return {
        "ok": True,
        "symbol": meta["symbol"],
        "source": source,
        "latest_ts": latest_ts,
        "latest_at": payload.get("latest_at", ""),
        "updated_label": payload.get("latest_at") or quote.get("time", ""),
        "quote": quote,
        "rows": [
            session_row("盘前", "pre"),
            session_row("盘中", "regular"),
            session_row("盘后", "post"),
            session_row("夜盘", "overnight"),
        ],
        "summary": f"{meta['symbol']} 分时、盘前和盘后来自 {source}，仅用于研究观察。",
    }


def stock_unusual_activity(symbol: str, quote: dict[str, Any] | None = None) -> dict[str, Any]:
    meta = stock_meta(symbol)
    quote = quote or lightweight_stock_quote(meta["symbol"])
    payload = read_stock_persistent_candle_cache(meta["symbol"], 90, "1d", "regular") or {
        "rows": [],
        "source": quote.get("source", "quote"),
        "latest_at": quote.get("time", ""),
        "latest_ts": quote.get("ts", now_ms()),
    }
    rows = list(payload.get("rows") or [])
    volumes = [pct(row.get("volume", 0.0)) for row in rows if pct(row.get("volume", 0.0)) > 0]
    recent_volume = volumes[-1] if volumes else pct(quote.get("vol24h", 0.0))
    baseline = average(volumes[-21:-1]) if len(volumes) >= 22 else average(volumes[:-1]) if len(volumes) > 1 else recent_volume
    volume_ratio = recent_volume / max(baseline, 1e-9) if baseline > 0 and recent_volume > 0 else 1.0
    open_price = pct(quote.get("open24h", 0.0))
    high = pct(quote.get("high24h", 0.0))
    low = pct(quote.get("low24h", 0.0))
    change = pct(quote.get("change24h_pct", 0.0))
    range_pct = (high / max(low, 1e-9) - 1) * 100 if high > 0 and low > 0 else abs(change)
    gap_pct = 0.0
    if len(rows) >= 2:
        prev_close = pct(rows[-2].get("close", 0.0))
        gap_pct = (open_price / max(prev_close, 1e-9) - 1) * 100 if open_price > 0 and prev_close > 0 else 0.0
    flags: list[str] = []
    if volume_ratio >= 1.6:
        flags.append(f"成交量 {volume_ratio:.2f}x")
    if abs(gap_pct) >= 1.2:
        flags.append(f"跳空 {gap_pct:+.2f}%")
    if range_pct >= 3.2:
        flags.append(f"日内振幅 {range_pct:.2f}%")
    if abs(change) >= 2.5:
        flags.append(f"价格异动 {change:+.2f}%")
    headline = f"{meta['symbol']} " + (" / ".join(flags) if flags else "暂无明显异常成交，继续观察量价确认。")
    return {
        "ok": True,
        "symbol": meta["symbol"],
        "headline": headline,
        "volume_ratio": round(volume_ratio, 2),
        "gap_pct": round(gap_pct, 2),
        "range_pct": round(range_pct, 2),
        "change_pct": round(change, 2),
        "recent_volume": round(recent_volume, 2),
        "baseline_volume": round(baseline, 2),
        "flags": flags,
        "updated_label": payload.get("latest_at", "") or quote.get("time", ""),
        "rows": [
            {"symbol": meta["symbol"], "label": "成交量倍率", "value": f"{volume_ratio:.2f}x", "change24h_pct": volume_ratio - 1, "reason": "最近一日成交量相对20日均量"},
            {"symbol": meta["symbol"], "label": "跳空", "value": f"{gap_pct:+.2f}%", "change24h_pct": gap_pct, "reason": "今日开盘相对前收"},
            {"symbol": meta["symbol"], "label": "振幅", "value": f"{range_pct:.2f}%", "change24h_pct": range_pct, "reason": "日内高低点区间"},
        ],
    }


def stock_sector_linkage(symbol: str) -> dict[str, Any]:
    meta = stock_meta(symbol)
    sector = str(meta.get("sector") or "Stock")
    peers = [
        item for item in STOCK_MARKETS
        if item["symbol"] != meta["symbol"] and (item.get("sector") == sector or item.get("market") == meta.get("market"))
    ][:6]
    rows: list[dict[str, Any]] = []
    cached_rows = {
        str(row.get("symbol", "")).upper(): row
        for row in (STOCK_QUOTE_CACHE.get("rows", []) or [])
        if now_ms() - int(STOCK_QUOTE_CACHE.get("time") or 0) < 600000
    }
    for peer in peers:
        quote = cached_rows.get(peer["symbol"]) or lightweight_stock_quote(peer["symbol"])
        rows.append({
            "symbol": peer["symbol"],
            "name": peer.get("name", peer["symbol"]),
            "sector": peer.get("sector", ""),
            "last": pct(quote.get("last", 0.0)),
            "change24h_pct": pct(quote.get("change24h_pct", 0.0)),
            "volume": pct(quote.get("vol24h", 0.0)),
            "source": quote.get("source", ""),
            "reason": peer.get("sector", ""),
        })
    avg_change = average([row["change24h_pct"] for row in rows]) if rows else 0.0
    up_count = len([row for row in rows if row["change24h_pct"] > 0])
    down_count = len([row for row in rows if row["change24h_pct"] < 0])
    return {
        "ok": True,
        "symbol": meta["symbol"],
        "sector": sector,
        "avg_change_pct": round(avg_change, 2),
        "summary": f"{sector} 同组：{up_count}涨 {down_count}跌，均值 {avg_change:+.2f}%",
        "rows": sorted(rows, key=lambda row: abs(row["change24h_pct"]), reverse=True),
    }


def stock_calendar_events(symbol: str, quote_summary: dict[str, Any]) -> list[dict[str, Any]]:
    meta = stock_meta(symbol)
    calendar = quote_summary.get("calendarEvents") or {}
    summary_detail = quote_summary.get("summaryDetail") or {}
    financial = quote_summary.get("financialData") or {}
    stats = quote_summary.get("defaultKeyStatistics") or {}
    events: list[dict[str, Any]] = []
    earnings = calendar.get("earnings") or {}
    earnings_dates = earnings.get("earningsDate") or []
    if earnings_dates:
        date_text = " / ".join(str(yahoo_raw(item, "")) for item in earnings_dates if yahoo_raw(item, ""))
        events.append({"time": date_text or "待确认", "title": f"{meta['symbol']} 财报窗口", "impact": "财报日前后波动和跳空风险上升。", "category": "财报"})
    revenue_avg = yahoo_raw(earnings.get("revenueAverage"), "")
    eps_avg = yahoo_raw(earnings.get("earningsAverage"), "")
    if revenue_avg or eps_avg:
        events.append({"time": "财报预期", "title": "EPS / Revenue 预期", "impact": f"EPS {eps_avg or '--'} / Revenue {revenue_avg or '--'}", "category": "财报"})
    ex_dividend = yahoo_raw(calendar.get("exDividendDate") or summary_detail.get("exDividendDate"), "")
    if ex_dividend:
        events.append({"time": str(ex_dividend), "title": "除息 / 分红观察", "impact": "可能影响缺口、收益率和持仓成本。", "category": "分红"})
    target = yahoo_raw(financial.get("targetMeanPrice"), "")
    recommendation = yahoo_raw(financial.get("recommendationKey"), "")
    if target or recommendation:
        events.append({"time": "分析师", "title": "目标价 / 评级", "impact": f"目标价 {target or '--'} / 评级 {recommendation or '--'}", "category": "评级"})
    beta = yahoo_raw(stats.get("beta"), "")
    short_ratio = yahoo_raw(stats.get("shortRatio"), "")
    if beta or short_ratio:
        events.append({"time": "风险因子", "title": "Beta / 空头天数", "impact": f"Beta {beta or '--'} / Short ratio {short_ratio or '--'}", "category": "风险"})
    if not events:
        events = [
            {"time": "盘前", "title": "盘前缺口与成交额", "impact": "观察是否高开低走或低开修复。", "category": "观察"},
            {"time": "盘中", "title": "行业同向 / 分化", "impact": "同组确认比单股异动更可靠。", "category": "观察"},
            {"time": "盘后", "title": "财报 / 公告 / 评级", "impact": "盘后消息可能改变次日开盘结构。", "category": "观察"},
        ]
    return events[:8]


def stock_fundamental_snapshot(
    symbol: str,
    quote_summary: dict[str, Any],
    quote: dict[str, Any],
    unusual: dict[str, Any],
) -> dict[str, Any]:
    meta = stock_meta(symbol)
    summary_detail = quote_summary.get("summaryDetail") or {}
    financial = quote_summary.get("financialData") or {}
    stats = quote_summary.get("defaultKeyStatistics") or {}
    rows: list[dict[str, Any]] = []

    def add_row(label: str, value: Any, detail: str, tone: str = "flat") -> None:
        if value in ("", None, "--"):
            return
        rows.append({"time": label, "title": str(value), "impact": detail, "tone": tone, "category": "基本面"})

    last = pct(quote.get("last", 0.0))
    change = pct(quote.get("change24h_pct", 0.0))
    if last > 0:
        add_row("行情", f"{last:.4g} / {change:+.2f}%", "当前股价和当日涨跌幅，用于判断跳空、趋势延续和回补压力。", "up" if change > 0 else "down" if change < 0 else "flat")

    trailing_pe = yahoo_raw(summary_detail.get("trailingPE"), "")
    forward_pe = yahoo_raw(summary_detail.get("forwardPE"), "")
    market_cap = yahoo_raw(summary_detail.get("marketCap"), "")
    if trailing_pe or forward_pe or market_cap:
        add_row("估值", f"PE {trailing_pe or '--'} / FPE {forward_pe or '--'}", f"市值 {market_cap or '--'}，估值只做研究参考，需要结合行业和增速。")

    revenue_growth = yahoo_raw(financial.get("revenueGrowth"), "")
    earnings_growth = yahoo_raw(financial.get("earningsGrowth"), "")
    gross_margin = yahoo_raw(financial.get("grossMargins"), "")
    if revenue_growth or earnings_growth or gross_margin:
        add_row("盈利质量", f"Rev {revenue_growth or '--'} / EPS {earnings_growth or '--'}", f"毛利率 {gross_margin or '--'}，观察业绩趋势是否支撑价格突破。")

    target = yahoo_raw(financial.get("targetMeanPrice"), "")
    recommendation = yahoo_raw(financial.get("recommendationKey"), "")
    analyst_count = yahoo_raw(financial.get("numberOfAnalystOpinions"), "")
    if target or recommendation or analyst_count:
        add_row("评级", f"{recommendation or '--'} / Target {target or '--'}", f"分析师样本 {analyst_count or '--'}，只作为市场预期参考，不等于交易指令。")

    beta = yahoo_raw(stats.get("beta"), "")
    short_ratio = yahoo_raw(stats.get("shortRatio"), "")
    held_percent = yahoo_raw(stats.get("heldPercentInstitutions"), "")
    risk_bits = []
    if beta:
        risk_bits.append(f"Beta {beta}")
    if short_ratio:
        risk_bits.append(f"Short ratio {short_ratio}")
    if held_percent:
        risk_bits.append(f"机构持仓 {held_percent}")
    if risk_bits:
        add_row("风险因子", " / ".join(risk_bits), "高 Beta、空头拥挤或机构调仓都可能放大盘前盘后波动。", "down")

    volume_ratio = pct(unusual.get("volume_ratio", 1.0), 1.0)
    gap_pct = pct(unusual.get("gap_pct", 0.0))
    range_pct = pct(unusual.get("range_pct", 0.0))
    add_row("量能风险", f"{volume_ratio:.2f}x / Gap {gap_pct:+.2f}%", f"日内振幅 {range_pct:.2f}%，观察放量是否由新闻、财报或行业联动解释。", "up" if volume_ratio >= 1.4 else "flat")

    return {
        "ok": True,
        "symbol": meta["symbol"],
        "rows": rows[:8],
        "summary": " / ".join(f"{row['time']} {row['title']}" for row in rows[:3]) if rows else "基本面数据暂不可用。",
    }




def safe_research_call(label: str, fn, fallback: Any) -> Any:
    try:
        return fn()
    except Exception as exc:
        if isinstance(fallback, dict):
            return {**fallback, "ok": False, "error": f"{label}: {exc}"}
        return fallback


def research_status_row(name: str, status: str, detail: str, priority: str = "P2") -> dict[str, Any]:
    clean_status = choice(status, {"PASS", "WATCH", "BLOCK"}, "WATCH")
    return {"name": name, "status": clean_status, "detail": detail, "priority": priority}


def symbol_research_brief(symbol: str = "BTC-USDT") -> dict[str, Any]:
    clean_symbol = (symbol or "BTC-USDT").upper()
    try:
        shared_snapshot = market_data_snapshot(
            clean_symbol,
            "1H",
            260,
            "all",
            True,
            False,
            False,
            "research",
        )
    except Exception:
        shared_snapshot = {}
    insights = safe_research_call("market_insights", lambda: market_insights(clean_symbol), {"metrics": {}, "alerts": [], "summary": "市场情报暂不可用"})
    contract = safe_research_call("contract_center", lambda: contract_center(clean_symbol), {"metrics": {}})
    local_ai = safe_research_call(
        "local_market_ai",
        lambda: local_market_ai_analysis(
            clean_symbol,
            "1H",
            pct((shared_snapshot.get("quote") or {}).get("last", 0.0)),
            [],
            {
                "shared_snapshot": shared_snapshot.get("context") or {},
                "snapshot_source": (shared_snapshot.get("source") or {}).get("primary", ""),
            },
            (shared_snapshot.get("candles") or {}).get("rows"),
        ),
        {"long_plan": {}, "short_plan": {}, "metrics": {}, "summary": "本地多空估算暂不可用"},
    )

    market_metrics = insights.get("metrics", {}) if isinstance(insights, dict) else {}
    contract_metrics = contract.get("metrics", {}) if isinstance(contract, dict) else {}
    ai_metrics = local_ai.get("metrics", {}) if isinstance(local_ai, dict) else {}
    long_plan = local_ai.get("long_plan", {}) if isinstance(local_ai, dict) else {}
    short_plan = local_ai.get("short_plan", {}) if isinstance(local_ai, dict) else {}
    long_rate = pct(long_plan.get("win_rate_pct"), 0.0)
    short_rate = pct(short_plan.get("win_rate_pct"), 0.0)
    price = pct(local_ai.get("price"), 0.0) or pct(market_metrics.get("last"), 0.0) or pct(contract_metrics.get("spot_last"), 0.0)
    candle_count = int(pct(local_ai.get("candle_count"), 0.0))
    range_pct = pct(ai_metrics.get("range_pct"), pct(market_metrics.get("range24h_pct"), 0.0))
    volume_ratio = pct(ai_metrics.get("volume_ratio"), pct(market_metrics.get("volume_ratio"), 1.0))
    funding = pct(market_metrics.get("funding_rate_pct"), pct(contract_metrics.get("funding_rate_pct"), 0.0))
    open_interest = pct(contract_metrics.get("open_interest"), pct(market_metrics.get("open_interest"), 0.0))

    if max(long_rate, short_rate) < 52 or abs(long_rate - short_rate) < 3:
        preferred = "WAIT"
        stance = "等待"
        stance_detail = "多空优势不够清楚，先观察关键位。"
    elif long_rate > short_rate:
        preferred = "LONG"
        stance = "偏多研究"
        stance_detail = "做多概率暂时高于做空，但仍只作为研究和模拟参考。"
    else:
        preferred = "SHORT"
        stance = "偏空研究"
        stance_detail = "做空概率暂时高于做多，但仍只作为研究和模拟参考。"

    cards = [
        {"label": "研究立场", "value": stance, "tone": "up" if preferred == "LONG" else "down" if preferred == "SHORT" else "flat", "detail": stance_detail},
        {"label": "做多/做空", "value": f"{long_rate:.1f}% / {short_rate:.1f}%" if long_rate or short_rate else "--", "tone": "up" if long_rate > short_rate + 3 else "down" if short_rate > long_rate + 3 else "flat", "detail": f"多TP {long_plan.get('take_profit', '--')} / 空TP {short_plan.get('take_profit', '--')}"},
        {"label": "波动与量能", "value": f"{range_pct:.2f}% / {volume_ratio:.2f}x", "tone": "down" if range_pct >= 8 else "up" if volume_ratio >= 1.35 else "flat", "detail": "高波动要缩小仓位；量能放大时信号可信度才提高。"},
        {"label": "合约/资金", "value": f"{funding:+.4f}% / OI {open_interest:.2f}", "tone": "down" if abs(funding) >= 0.03 else "flat", "detail": "资金费率偏高时注意拥挤交易和反向波动。"},
    ]

    checklist = [
        research_status_row("K线样本", "PASS" if candle_count >= 80 else "WATCH" if candle_count >= 30 else "BLOCK", f"{candle_count} 根1H样本", "P0"),
        research_status_row("价格可用", "PASS" if price > 0 else "BLOCK", f"当前价 {price:.6g}" if price > 0 else "等待行情", "P0"),
        research_status_row("多空优势", "PASS" if preferred != "WAIT" else "WATCH", f"做多 {long_rate:.1f}% / 做空 {short_rate:.1f}%", "P1"),
        research_status_row("波动风险", "WATCH" if range_pct >= 8 else "PASS", f"窗口振幅 {range_pct:.2f}%", "P1"),
        research_status_row("资金拥挤", "WATCH" if abs(funding) >= 0.03 else "PASS", f"资金费率 {funding:+.4f}%", "P1"),
        research_status_row("真实下单墙", "PASS", "本页只做研究和模拟，不开放真实下单。", "P0"),
    ]

    prompts = [
        f"请基于当前{clean_symbol}的K线、成交量和关键位，复核做多和做空胜率。",
        f"{clean_symbol} 如果只允许单向持仓，现在更应该等待、做多还是做空？反证是什么？",
        f"请给出{clean_symbol}的模拟止盈止损位置，并说明这些位置失效的条件。",
        f"如果未来30分钟波动突然放大，{clean_symbol}研究结论应该如何调整？",
    ]

    stock_extra: dict[str, Any] = {}
    if is_stock_symbol(clean_symbol):
        deep = safe_research_call("futu_deep", lambda: read_futu_deep_stock(clean_symbol, False), {"ok": False})
        stock_extra = {
            "summary": deep.get("ai_news_summary", "") if isinstance(deep, dict) else "",
            "valuation": (deep.get("valuation") or {}) if isinstance(deep, dict) else {},
            "institutional_count": len(deep.get("institutional") or []) if isinstance(deep, dict) else 0,
            "rating_count": len(deep.get("rating") or []) if isinstance(deep, dict) else 0,
            "source": deep.get("source", "futu") if isinstance(deep, dict) else "futu",
            "ok": bool(deep.get("ok")) if isinstance(deep, dict) else False,
        }

    return {
        "symbol": clean_symbol,
        "price": round(price, 6),
        "preferred": preferred,
        "summary": f"{clean_symbol}：{stance}。{insights.get('summary', '') if isinstance(insights, dict) else ''}",
        "cards": cards,
        "checklist": checklist,
        "prompts": prompts,
        "alerts": (insights.get("alerts") or [])[:5] if isinstance(insights, dict) else [],
        "local_ai": local_ai,
        "market_metrics": market_metrics,
        "contract_metrics": contract_metrics,
        "stock_extra": stock_extra,
        "shared_snapshot": shared_snapshot.get("context") or {},
    }


def research_panel(symbol: str = "BTC-USDT") -> dict[str, Any]:
    if is_stock_symbol(symbol):
        return stock_research_panel(symbol, None, None)
    scanner = market_scanner()
    movers = scanner.get("rows", [])
    focus = symbol_research_brief(symbol)
    news = []
    news.extend(read_rss_items("https://www.coindesk.com/arc/outboundfeeds/rss/", "CoinDesk", 5))
    news.extend(read_rss_items("https://cointelegraph.com/rss", "Cointelegraph", 5))
    if not news:
        top = movers[0] if movers else {"symbol": symbol, "action": "等待扫描", "reason": "暂无外部新闻源"}
        news = [{"source": "本地AI摘要", "title": f"{top['symbol']}：{top['action']}，{top['reason']}", "link": "", "published": ""}]
    events = [
        {"time": "每日 08:00", "title": "永续资金费率结算窗口", "impact": "合约持仓成本"},
        {"time": "每日 00:00 UTC", "title": "日线收盘与策略回测刷新", "impact": "趋势/回撤评估"},
        {"time": "每小时", "title": "多币种机会扫描", "impact": "异动提醒"},
    ]
    summary = f"研究面板已更新：{focus['symbol']} 当前{focus['cards'][0]['value']}，并汇总新闻流、热点币种、涨跌幅、成交额与事件。"
    return {
        "ok": True,
        "summary": summary,
        "focus": focus,
        "news": news[:8],
        "events": events,
        "hot": movers[:8],
        "gainers": sorted(movers, key=lambda item: item["change24h_pct"], reverse=True)[:8],
        "losers": sorted(movers, key=lambda item: item["change24h_pct"])[:8],
        "volume": sorted(movers, key=lambda item: item["volume"], reverse=True)[:8],
    }


_legacy_research_panel = research_panel


def _stock_quote_from_cache(symbol: str, max_age_ms: int = 600000) -> dict[str, Any]:
    meta = stock_meta(symbol)
    cached = STOCK_SINGLE_QUOTE_CACHE.get(meta["symbol"]) or {}
    if now_ms() - int(cached.get("time") or 0) < max_age_ms and isinstance(cached.get("quote"), dict):
        quote = dict(cached["quote"])
    else:
        quote = stock_seed_quote(meta["symbol"])

    daily = read_stock_persistent_candle_cache(meta["symbol"], 2, "1d", "all")
    intraday = read_stock_persistent_candle_cache(meta["symbol"], 1, "1m", "all")
    daily_rows = list((daily or {}).get("rows") or [])
    intraday_rows = list((intraday or {}).get("rows") or [])
    latest_daily = daily_rows[-1] if daily_rows else {}
    prev_daily = daily_rows[-2] if len(daily_rows) >= 2 else {}
    latest_intraday = intraday_rows[-1] if intraday_rows else {}
    latest = latest_intraday or latest_daily
    if not latest:
        return quote

    quote_last = pct(quote.get("last", 0.0))
    quote_ts = int(pct(quote.get("ts", 0), 0))
    quote_source = str(quote.get("source") or "").lower()
    quote_age_ms = max(0, now_ms() - quote_ts) if quote_ts > 0 else 0
    quote_is_liveish = (
        quote_last > 0
        and quote_ts > 0
        and quote_age_ms <= max_age_ms
        and quote_source not in {"stock_sqlite_cache", "offline-seed", "quote_preview_seed", ""}
        and "seed" not in quote_source
        and "offline" not in quote_source
    )
    if quote_is_liveish:
        live_quote = normalize_stock_quote_quality({
            **quote,
            "symbol": meta["symbol"],
            "instId": meta.get("futu", meta["symbol"]),
            "name": meta.get("name", meta["symbol"]),
            "type": "stock",
            "category": "stocks",
            "exchange": meta.get("exchange", "US"),
            "market": meta.get("market", "US"),
            "sector": meta.get("sector", "Stock"),
            "status": quote.get("status") or "ONLINE",
            "last": quote_last,
            "open24h": pct(quote.get("open24h", latest_daily.get("open", quote_last))) or quote_last,
            "high24h": max(pct(quote.get("high24h", quote_last)), quote_last),
            "low24h": min(pct(quote.get("low24h", quote_last)) or quote_last, quote_last),
            "vol24h": pct(quote.get("vol24h", quote.get("volCcy24h", 0.0))),
            "volCcy24h": pct(quote.get("volCcy24h", quote.get("vol24h", 0.0))),
            "ts": quote_ts,
            "data_age_ms": quote_age_ms,
            "local_candle_ts": latest.get("ts"),
            "local_candle_source": latest.get("source") or (daily or {}).get("origin_source") or (intraday or {}).get("origin_source") or "",
        }, previous_close=quote.get("prevClose"), change_basis=quote.get("change_basis", ""), now_ms=now_ms())
        return cache_stock_quote(meta["symbol"], live_quote)

    last = pct(latest.get("close", quote_last))
    open_price = pct(latest_daily.get("open", quote.get("open24h", last)))
    high = max(pct(latest_daily.get("high", last)), last)
    low = min(pct(latest_daily.get("low", last)) or last, last)
    volume = pct(latest_daily.get("volume", quote.get("vol24h", 0.0)))
    prev_close = pct(prev_daily.get("close", open_price))
    change = (last / max(prev_close, 1e-9) - 1) * 100 if last > 0 and prev_close > 0 else pct(quote.get("change24h_pct", 0.0))
    origin_source = str(latest.get("source") or (daily or {}).get("origin_source") or (intraday or {}).get("origin_source") or "stock")
    latest_ts = int(pct(latest.get("ts", quote.get("ts", now_ms())), now_ms()))
    data_age_ms = max(0, now_ms() - latest_ts) if latest_ts > 0 else 0
    stale_quote = data_age_ms > 30 * 60 * 1000
    merged = normalize_stock_quote_quality({
        **quote,
        "symbol": meta["symbol"],
        "instId": meta.get("futu", meta["symbol"]),
        "name": meta.get("name", meta["symbol"]),
        "type": "stock",
        "category": "stocks",
        "source": "stock_sqlite_cache",
        "origin_source": origin_source,
        "exchange": meta.get("exchange", "US"),
        "market": meta.get("market", "US"),
        "sector": meta.get("sector", "Stock"),
        "status": "CACHE",
        "last": last,
        "open24h": open_price,
        "high24h": high,
        "low24h": low,
        "vol24h": volume,
        "volCcy24h": volume,
        "change24h_pct": round(change, 2),
        "ts": latest_ts,
        "date": latest.get("date", quote.get("date", "")),
        "time": latest.get("time", quote.get("time", "")),
        "data_age_ms": data_age_ms,
        "warning": "stale stock quote from local candle cache" if stale_quote else "stock quote from local candle cache",
    }, previous_close=prev_close, change_basis="local_previous_close", now_ms=now_ms())
    return cache_stock_quote(meta["symbol"], merged)


def _selected_stock_research_quote(symbol: str) -> dict[str, Any]:
    meta = stock_meta(symbol)
    quote = _stock_quote_from_cache(meta["symbol"])
    quality = quote.get("quote_quality") if isinstance(quote.get("quote_quality"), dict) else {}
    source = str(quote.get("source") or "").lower()
    fallback = source in {"stock_sqlite_cache", "offline-seed", "quote_preview_seed", ""} or "offline" in source or "seed" in source
    if not fallback and not quality.get("quarantined"):
        return quote
    if futu_status_snapshot(False).get("opend_online"):
        futu_quote = read_futu_quotes([meta["symbol"]]).get(meta["symbol"])
        if futu_quote:
            return futu_quote
    return quote


def stock_news_calendar_async(symbol: str, limit: int = 8) -> dict[str, Any]:
    return stock_news_calendar_async_io(
        symbol,
        quote_reader=_stock_quote_from_cache,
        quote_summary_reader=yahoo_quote_summary,
        calendar_events_reader=stock_calendar_events,
        fundamental_snapshot_builder=stock_fundamental_snapshot,
        limit=limit,
    )


def stock_research_panel(symbol: str, scanner: dict[str, Any] | None = None, focus: dict[str, Any] | None = None) -> dict[str, Any]:
    selected_symbol = stock_meta(symbol)["symbol"]
    try:
        shared_snapshot = market_data_snapshot(
            selected_symbol,
            "1d",
            260,
            "regular",
            False,
            False,
            False,
            "stock_research",
        )
    except Exception:
        shared_snapshot = {}
    snapshot_quote = dict(shared_snapshot.get("quote") or {})
    if pct(snapshot_quote.get("last", 0.0)) > 0:
        selected_quote = {
            **snapshot_quote,
            "symbol": selected_symbol,
            "instId": stock_meta(selected_symbol).get("futu", selected_symbol),
            "source": (shared_snapshot.get("source") or {}).get("quote") or snapshot_quote.get("source") or "stock",
            "origin_source": (shared_snapshot.get("source") or {}).get("origin") or snapshot_quote.get("origin_source") or "",
        }
    else:
        selected_quote = _selected_stock_research_quote(selected_symbol)

    def research_quote_reader(request_symbol: str) -> dict[str, Any]:
        if stock_meta(request_symbol)["symbol"] == selected_symbol:
            return dict(selected_quote)
        return _stock_quote_from_cache(request_symbol)

    panel = stock_research_panel_io(
        symbol,
        quote_reader=research_quote_reader,
        status_row_builder=research_status_row,
        stock_quote_cache_rows=STOCK_QUOTE_CACHE.get("rows", []),
        stock_quote_cache_time=int(STOCK_QUOTE_CACHE.get("time") or 0),
    )
    panel["shared_snapshot"] = shared_snapshot.get("context") or {}
    return panel


def research_panel(symbol: str = "BTC-USDT") -> dict[str, Any]:
    if is_stock_symbol(symbol):
        return stock_research_panel(symbol, None, None)
    return _legacy_research_panel(symbol)


RUNTIME_AI_KEYS: dict[str, str] = {}
RUNTIME_AI_KEYS_LOCK = threading.RLock()


def runtime_secret(*names: str) -> tuple[str, str, str]:
    with RUNTIME_AI_KEYS_LOCK:
        for name in names:
            value = RUNTIME_AI_KEYS.get(name)
            if value:
                return name, value, "runtime"
    for name in names:
        value = os.getenv(name)
        if value:
            return name, value, "env"
    return names[0] if names else "", "", "none"


def runtime_ai_key_status() -> dict[str, Any]:
    rows = []
    specs = [
        ("openai", "1号辩手 Codex/GPT", ("OPENAI_API_KEY", "GPT_API_KEY")),
        ("deepseek", "2号辩手 DeepSeek", ("DEEPSEEK_API_KEY",)),
        ("doubao", "3号辩手 豆包", ("DOUBAO_API_KEY", "ARK_DOUBAO_API_KEY", "VOLCENGINE_DOUBAO_API_KEY", "ARK_API_KEY", "VOLCENGINE_API_KEY")),
        ("glm", "4号辩手 GLM/智谱", ("ARK_GLM_API_KEY", "GLM_API_KEY", "VOLCENGINE_GLM_API_KEY", "ARK_API_KEY", "VOLCENGINE_API_KEY", "DOUBAO_API_KEY")),
    ]
    for provider, name, env_names in specs:
        active_env, value, source = runtime_secret(*env_names)
        rows.append({
            "id": provider,
            "name": name,
            "configured": bool(value),
            "source": source,
            "active_env": active_env if value else "",
            "env": " / ".join(env_names),
        })
    has_environment_key = any(row.get("source") == "env" for row in rows)
    summary = (
        "OpenAI 可由本机忽略文件或进程环境载入；界面粘贴的密钥仍只保存在当前后端进程内存中。"
        if has_environment_key else
        "界面粘贴的密钥只保存在当前后端进程内存中；重启服务后失效。"
    )
    return {
        "ok": True,
        "rows": rows,
        "summary": summary,
        "updated_at": now_ms(),
    }


def set_runtime_ai_keys(payload: dict[str, Any]) -> dict[str, Any]:
    fields = {
        "openai_api_key": "OPENAI_API_KEY",
        "gpt_api_key": "OPENAI_API_KEY",
        "deepseek_api_key": "DEEPSEEK_API_KEY",
        "ark_api_key": "ARK_API_KEY",
        "doubao_api_key": "DOUBAO_API_KEY",
        "ark_doubao_api_key": "DOUBAO_API_KEY",
        "glm_api_key": "ARK_GLM_API_KEY",
        "ark_glm_api_key": "ARK_GLM_API_KEY",
        "volcengine_api_key": "ARK_API_KEY",
    }
    changed: list[str] = []
    with RUNTIME_AI_KEYS_LOCK:
        for field, env_name in fields.items():
            value = str(payload.get(field) or "").strip()
            if value:
                RUNTIME_AI_KEYS[env_name] = value
                changed.append(env_name)
    status = runtime_ai_key_status()
    status["changed"] = sorted(set(changed))
    status["summary"] = "已写入当前进程内存；不会保存到代码、配置文件或前端。"
    return status


def clear_runtime_ai_keys(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    providers = payload.get("providers") if isinstance(payload, dict) else None
    wanted = {str(item).lower() for item in providers} if isinstance(providers, list) else {"openai", "deepseek", "ark", "doubao", "glm"}
    provider_envs = {
        "openai": ("OPENAI_API_KEY", "GPT_API_KEY"),
        "deepseek": ("DEEPSEEK_API_KEY",),
        "ark": ("ARK_API_KEY", "VOLCENGINE_API_KEY", "DOUBAO_API_KEY", "ARK_DOUBAO_API_KEY", "ARK_GLM_API_KEY", "GLM_API_KEY"),
        "doubao": ("DOUBAO_API_KEY", "ARK_DOUBAO_API_KEY", "VOLCENGINE_DOUBAO_API_KEY", "ARK_API_KEY", "VOLCENGINE_API_KEY"),
        "glm": ("ARK_GLM_API_KEY", "GLM_API_KEY", "VOLCENGINE_GLM_API_KEY", "ARK_API_KEY", "VOLCENGINE_API_KEY", "DOUBAO_API_KEY"),
    }
    cleared: list[str] = []
    with RUNTIME_AI_KEYS_LOCK:
        for provider, env_names in provider_envs.items():
            if provider not in wanted:
                continue
            for env_name in env_names:
                if env_name in RUNTIME_AI_KEYS:
                    RUNTIME_AI_KEYS.pop(env_name, None)
                    cleared.append(env_name)
    status = runtime_ai_key_status()
    status["cleared"] = sorted(cleared)
    status["summary"] = "已清空当前进程内存中的运行时密钥。"
    return status


def deepseek_status() -> dict[str, Any]:
    active_env, api_key, source = runtime_secret("DEEPSEEK_API_KEY")
    return {
        "provider": "deepseek",
        "configured": bool(api_key),
        "active_env": active_env if api_key else "",
        "source": source,
        "model": DEEPSEEK_MODEL,
        "thinking": "enabled" if DEEPSEEK_THINKING_ENABLED else "disabled",
        "base_url": DEEPSEEK_BASE_URL,
        "role": "AI研究员，只提供分析、解释和机会扫描，不直接下单",
    }


def extract_json_object(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        value = json.loads(cleaned)
        return value if isinstance(value, dict) else None
    except Exception:
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        try:
            value = json.loads(cleaned[start:end + 1])
            return value if isinstance(value, dict) else None
        except Exception:
            return None
    return None


def deepseek_chat(messages: list[dict[str, str]], purpose: str, max_tokens: int = 1200, timeout: int = 30) -> dict[str, Any]:
    _, api_key, _ = runtime_secret("DEEPSEEK_API_KEY")
    if not api_key:
        return {"ok": False, "configured": False, "error": "DEEPSEEK_API_KEY 未配置"}
    payload: dict[str, Any] = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if DEEPSEEK_THINKING_ENABLED:
        payload["thinking"] = {"type": "enabled"}
        payload["reasoning_effort"] = "high"

    def post(body: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Python-Quant-Exchange-Terminal/0.1",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    thinking_requested = DEEPSEEK_THINKING_ENABLED
    try:
        response = post(payload)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        if DEEPSEEK_THINKING_ENABLED and exc.code in {400, 422}:
            fallback_payload = dict(payload)
            fallback_payload.pop("thinking", None)
            fallback_payload.pop("reasoning_effort", None)
            try:
                response = post(fallback_payload)
                thinking_requested = False
            except Exception as fallback_exc:
                return {"ok": False, "configured": True, "error": str(fallback_exc), "http_error": body[:500], "purpose": purpose}
        else:
            return {"ok": False, "configured": True, "error": body[:500] or str(exc), "purpose": purpose}
    except Exception as exc:
        return {"ok": False, "configured": True, "error": str(exc), "purpose": purpose}

    choice_row = (response.get("choices") or [{}])[0]
    message = choice_row.get("message") or {}
    content = message.get("content") or ""
    parsed = extract_json_object(content)
    return {
        "ok": True,
        "configured": True,
        "provider": "deepseek",
        "model": response.get("model", DEEPSEEK_MODEL),
        "purpose": purpose,
        "thinking_requested": DEEPSEEK_THINKING_ENABLED,
        "thinking_used": thinking_requested,
        "reasoning": (message.get("reasoning_content") or "")[:1200],
        "content": content,
        "json": parsed,
        "usage": response.get("usage", {}),
    }


def deepseek_system_prompt() -> str:
    return (
        "你是量化交易系统里的AI研究员。你只能输出研究、解释、风险提示和机会扫描，"
        "不能要求系统绕过风控，不能直接下实盘订单。请使用中文。"
        "必须分别评估做多和做空方向；除非用户明确切换模式，不建议同一标的同时多空双开仓。"
        "必须把建议区分为：可观察、仅模拟盘、可交给策略引擎评估。"
        "输出必须是JSON，不要输出Markdown。"
    )


def deepseek_strategy_analysis(symbol: str, strategy_id: str, price: float, risk_config: dict[str, Any]) -> dict[str, Any]:
    if price <= 0:
        if is_stock_symbol(symbol):
            price = pct(read_stock_quote(symbol).get("last", "0"))
        else:
            ticker = okx_first("/api/v5/market/ticker", {"instId": symbol})
            price = pct(ticker.get("last", "0"))
    base = analyze_strategy_context(
        strategy_id,
        symbol,
        price,
        float(risk_config.get("manual_take_profit") or 0.0),
        float(risk_config.get("manual_stop_loss") or 0.0),
        risk_config.get("analysis_direction", "LONG"),
    )
    market = market_insights(symbol)
    contract = contract_center(symbol)
    compare = strategy_compare(symbol, price)
    prompt = {
        "task": "分析当前币种与策略，给出机会、风险、止盈止损建议",
        "symbol": symbol,
        "price": price,
        "strategy": choose_strategy(strategy_id),
        "direction_mode": risk_config.get("direction_mode", "LONG_ONLY"),
        "risk_config": {key: value for key, value in risk_config.items() if not key.startswith("manual_") or isinstance(value, (int, float, bool, str))},
        "local_analysis": base,
        "market_insights": market,
        "contract_center": contract,
        "strategy_compare_top": (compare.get("rows") or [])[:5],
        "output_schema": {
            "summary": "一句话研究结论",
            "direction": "LONG/SHORT/NEUTRAL",
            "confidence_pct": "0-100",
            "actionability": "WAIT/WATCH/PAPER_ONLY/ALLOW_STRATEGY_EVALUATION",
            "take_profit": "数字或0",
            "stop_loss": "数字或0",
            "position_hint_pct": "建议仓位百分比",
            "reasons": ["主要原因"],
            "risk_notes": ["风险提示"],
            "next_check_seconds": "建议下次分析间隔",
        },
    }
    result = deepseek_chat(
        [
            {"role": "system", "content": deepseek_system_prompt()},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
        "strategy_analysis",
        1400,
    )
    parsed = result.get("json") or {}
    merged = {**base, "deepseek": parsed, "deepseek_raw": result if not parsed else {"ok": result.get("ok"), "usage": result.get("usage"), "thinking_used": result.get("thinking_used")}}
    if parsed.get("take_profit"):
        merged["deepseek_take_profit"] = pct(parsed.get("take_profit"))
    if parsed.get("stop_loss"):
        merged["deepseek_stop_loss"] = pct(parsed.get("stop_loss"))
    return {"ok": bool(result.get("ok")), "status": deepseek_status(), "analysis": merged, "deepseek": result}


def openai_status() -> dict[str, Any]:
    active_env, api_key, source = runtime_secret("OPENAI_API_KEY", "GPT_API_KEY")
    return {
        "provider": "openai",
        "configured": bool(api_key),
        "active_env": active_env if api_key else "",
        "source": source,
        "model": OPENAI_MODEL,
        "base_url": OPENAI_BASE_URL,
        "role": "GPT二次复核，只输出行情研究、风控位置和反证，不直接下单",
    }

TRADING_AGENTS_PROJECT_DIR = Path(os.getenv("TRADINGAGENTS_PROJECT_DIR", r"C:\Users\Administrator\Documents\交易分析\TradingAgents"))
DOUBAO_API_KEY_ENVS = ("DOUBAO_API_KEY", "ARK_DOUBAO_API_KEY", "VOLCENGINE_DOUBAO_API_KEY", "ARK_API_KEY", "VOLCENGINE_API_KEY")
ARK_API_KEY_ENVS = ("ARK_API_KEY", "VOLCENGINE_API_KEY", "DOUBAO_API_KEY")
GLM_API_KEY_ENVS = ("ARK_GLM_API_KEY", "GLM_API_KEY", "VOLCENGINE_GLM_API_KEY", "ARK_API_KEY", "VOLCENGINE_API_KEY", "DOUBAO_API_KEY")
DOUBAO_ACCESS_KEY_ID_ENVS = ("DOUBAO_ACCESS_KEY_ID", "ARK_ACCESS_KEY_ID", "VOLCENGINE_ACCESS_KEY_ID", "VOLC_ACCESSKEY")
DOUBAO_SECRET_ACCESS_KEY_ENVS = ("DOUBAO_SECRET_ACCESS_KEY", "ARK_SECRET_ACCESS_KEY", "VOLCENGINE_SECRET_ACCESS_KEY", "VOLC_SECRETKEY")
DOUBAO_ENDPOINT_ID_ENVS = ("DOUBAO_ENDPOINT_ID", "ARK_ENDPOINT_ID", "VOLCENGINE_ENDPOINT_ID")


def first_env_value(names: tuple[str, ...]) -> tuple[str, str]:
    name, value, _ = runtime_secret(*names)
    return name, value


def doubao_model() -> str:
    return os.getenv("ARK_DOUBAO_MODEL") or os.getenv("DOUBAO_MODEL") or os.getenv("ARK_MODEL") or "doubao-seed-1-6"


def ark_glm_model() -> str:
    return os.getenv("ARK_GLM_MODEL") or os.getenv("GLM_MODEL") or os.getenv("ZHIPU_MODEL") or "glm-5-2-260617"


def doubao_base_url() -> str:
    return (os.getenv("DOUBAO_BASE_URL") or os.getenv("ARK_BASE_URL") or "https://ark.cn-beijing.volces.com/api/v3").rstrip("/")


def ark_base_url() -> str:
    return (os.getenv("ARK_BASE_URL") or os.getenv("VOLCENGINE_BASE_URL") or doubao_base_url()).rstrip("/")


def doubao_endpoint_id() -> tuple[str, str]:
    return first_env_value(DOUBAO_ENDPOINT_ID_ENVS)


def doubao_sdk_available() -> bool:
    try:
        import importlib.util
        return importlib.util.find_spec("volcenginesdkarkruntime") is not None
    except Exception:
        return False


def doubao_auth_state() -> dict[str, Any]:
    api_env, api_key = first_env_value(DOUBAO_API_KEY_ENVS)
    ak_env, ak_value = first_env_value(DOUBAO_ACCESS_KEY_ID_ENVS)
    sk_env, sk_value = first_env_value(DOUBAO_SECRET_ACCESS_KEY_ENVS)
    endpoint_env, endpoint_id = doubao_endpoint_id()
    sdk_ready = doubao_sdk_available()
    api_ready = bool(api_key)
    ak_pair_ready = bool(ak_value and sk_value)
    ak_ready = bool(ak_pair_ready and endpoint_id and sdk_ready)
    missing: list[str] = []
    if ak_pair_ready and not endpoint_id:
        missing.append("DOUBAO_ENDPOINT_ID / ARK_ENDPOINT_ID")
    if ak_pair_ready and not sdk_ready:
        missing.append("volcenginesdkarkruntime")
    return {
        "api_env": api_env if api_key else "",
        "api_ready": api_ready,
        "ak_env": ak_env if ak_value else "",
        "sk_env": sk_env if sk_value else "",
        "ak_pair_ready": ak_pair_ready,
        "endpoint_env": endpoint_env if endpoint_id else "",
        "endpoint_id": endpoint_id,
        "sdk_available": sdk_ready,
        "access_key_ready": ak_ready,
        "configured": api_ready or ak_ready,
        "partial_configured": bool(not api_ready and ak_pair_ready and not ak_ready),
        "auth_mode": "api_key" if api_ready else "access_key" if ak_pair_ready else "none",
        "missing": missing,
    }


def doubao_status() -> dict[str, Any]:
    auth = doubao_auth_state()
    return {
        "provider": "doubao",
        "configured": bool(auth["configured"]),
        "partial_configured": bool(auth["partial_configured"]),
        "env": "DOUBAO_API_KEY / ARK_DOUBAO_API_KEY / ARK_API_KEY or AK/SK + ARK_ENDPOINT_ID",
        "active_env": auth["api_env"] or auth["ak_env"],
        "auth_mode": auth["auth_mode"],
        "endpoint_configured": bool(auth["endpoint_id"]),
        "sdk_available": bool(auth["sdk_available"]),
        "missing": auth["missing"],
        "model": doubao_model(),
        "base_url": doubao_base_url(),
        "role": "第三辩手：豆包，负责中文语境、情绪/新闻和反方追问，只做研究与模拟验证",
    }


def ark_glm_status() -> dict[str, Any]:
    env_name, api_key = first_env_value(GLM_API_KEY_ENVS)
    model = ark_glm_model()
    return {
        "provider": "ark_glm",
        "configured": bool(api_key and model),
        "env": "ARK_GLM_API_KEY / GLM_API_KEY / ARK_API_KEY + ARK_GLM_MODEL",
        "active_env": env_name if api_key else "",
        "auth_mode": "ark_api_key" if api_key else "none",
        "model": model,
        "base_url": ark_base_url(),
        "role": "第四辩手：GLM/智谱，经火山方舟 Ark 调用，负责长上下文、逻辑推理和反方复核。",
        "shared_key_note": "Ark API Key is platform auth. The model field decides whether the request goes to Doubao, GLM, or another enabled Ark model.",
    }


def trading_agents_project_snapshot() -> dict[str, Any]:
    root = TRADING_AGENTS_PROJECT_DIR
    return {
        "ok": root.exists(),
        "name": "TradingAgents",
        "path": str(root),
        "run_script": str(root / "run_tradingagents.cmd"),
        "pyproject": (root / "pyproject.toml").exists(),
        "package": (root / "tradingagents").exists(),
        "readme": (root / "README.md").exists(),
        "integration": "结构集成：借鉴分析师、牛熊研究员、交易员、风险经理、组合经理流程；不让外部项目直接下单。",
    }


def openai_message_text(message: dict[str, Any]) -> str:
    content = message.get("content") or ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    return str(content)


def openai_chat(messages: list[dict[str, str]], purpose: str, max_tokens: int = 1200, timeout: int = 30) -> dict[str, Any]:
    _, api_key, _ = runtime_secret("OPENAI_API_KEY", "GPT_API_KEY")
    if not api_key:
        return {"ok": False, "configured": False, "error": "OPENAI_API_KEY 未配置", "purpose": purpose}

    payload: dict[str, Any] = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": 0.15,
        "max_tokens": max_tokens,
        "stream": False,
    }

    def post(body: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{OPENAI_BASE_URL}/chat/completions",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "HakimiTradeV2/market-ai",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    used_payload = dict(payload)
    try:
        response = post(used_payload)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        fallback_payload = dict(payload)
        fallback_payload.pop("temperature", None)
        if "max_completion_tokens" in body or "max_tokens" in body:
            fallback_payload.pop("max_tokens", None)
            fallback_payload["max_completion_tokens"] = max_tokens
        try:
            response = post(fallback_payload)
            used_payload = fallback_payload
        except Exception as fallback_exc:
            return {"ok": False, "configured": True, "error": str(fallback_exc), "http_error": body[:500], "purpose": purpose}
    except Exception as exc:
        return {"ok": False, "configured": True, "error": str(exc), "purpose": purpose}

    choice_row = (response.get("choices") or [{}])[0]
    message = choice_row.get("message") or {}
    content = openai_message_text(message)
    return {
        "ok": True,
        "configured": True,
        "provider": "openai",
        "model": response.get("model", OPENAI_MODEL),
        "purpose": purpose,
        "content": content,
        "json": extract_json_object(content),
        "usage": response.get("usage", {}),
        "compat": "max_completion_tokens" if "max_completion_tokens" in used_payload else "max_tokens",
    }


def doubao_chat(messages: list[dict[str, str]], purpose: str, max_tokens: int = 1200, timeout: int = 35) -> dict[str, Any]:
    auth = doubao_auth_state()
    env_name, api_key = first_env_value(DOUBAO_API_KEY_ENVS)
    if not api_key and auth["auth_mode"] == "access_key":
        return doubao_chat_with_access_key(messages, purpose, max_tokens, timeout, auth)
    if not api_key:
        return {"ok": False, "configured": False, "provider": "doubao", "error": "DOUBAO_API_KEY / ARK_API_KEY not configured", "purpose": purpose}
    model = doubao_model()
    base_url = doubao_base_url()
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.18,
        "max_tokens": max_tokens,
        "stream": False,
    }

    def post(body: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "HakimiTradeV2/trading-agents-doubao",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    used_payload = dict(payload)
    try:
        response = post(used_payload)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        fallback_payload = dict(payload)
        fallback_payload.pop("temperature", None)
        fallback_payload["max_tokens"] = min(max_tokens, 520)
        try:
            response = post(fallback_payload)
            used_payload = fallback_payload
        except Exception as fallback_exc:
            return {"ok": False, "configured": True, "provider": "doubao", "error": str(fallback_exc), "http_error": body[:500], "purpose": purpose}
    except Exception as exc:
        if "timed out" in str(exc).lower() or "timeout" in str(exc).lower():
            return {"ok": False, "configured": True, "provider": "doubao", "error": str(exc), "purpose": purpose}
        fallback_payload = dict(payload)
        fallback_payload.pop("temperature", None)
        fallback_payload["max_tokens"] = min(max_tokens, 520)
        try:
            response = post(fallback_payload)
            used_payload = fallback_payload
        except Exception as fallback_exc:
            return {"ok": False, "configured": True, "provider": "doubao", "error": str(fallback_exc), "first_error": str(exc), "purpose": purpose}

    choice_row = (response.get("choices") or [{}])[0]
    message = choice_row.get("message") or {}
    content = openai_message_text(message)
    return {
        "ok": True,
        "configured": True,
        "provider": "doubao",
        "auth_mode": "api_key",
        "active_env": env_name,
        "model": response.get("model", model),
        "purpose": purpose,
        "content": content,
        "json": extract_json_object(content),
        "usage": response.get("usage", {}),
        "compat": "temperature" if "temperature" in used_payload else "no_temperature",
    }


def ark_openai_compatible_chat(
    provider: str,
    model: str,
    messages: list[dict[str, str]],
    purpose: str,
    max_tokens: int = 1200,
    timeout: int = 35,
    key_envs: tuple[str, ...] = ARK_API_KEY_ENVS,
) -> dict[str, Any]:
    env_name, api_key = first_env_value(key_envs)
    if not api_key:
        return {"ok": False, "configured": False, "provider": provider, "error": f"{' / '.join(key_envs[:3])} not configured", "purpose": purpose}
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.18,
        "max_tokens": max_tokens,
        "stream": False,
    }

    def post(body: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{ark_base_url()}/chat/completions",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": f"HakimiTradeV2/{provider}",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    used_payload = dict(payload)
    try:
        response = post(used_payload)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        fallback_payload = dict(payload)
        fallback_payload.pop("temperature", None)
        try:
            response = post(fallback_payload)
            used_payload = fallback_payload
        except Exception as fallback_exc:
            return {
                "ok": False,
                "configured": True,
                "provider": provider,
                "auth_mode": "ark_api_key",
                "model": model,
                "error": str(fallback_exc),
                "http_error": body[:500],
                "purpose": purpose,
            }
    except Exception as exc:
        return {"ok": False, "configured": True, "provider": provider, "auth_mode": "ark_api_key", "model": model, "error": str(exc), "purpose": purpose}

    choice_row = (response.get("choices") or [{}])[0]
    message = choice_row.get("message") or {}
    content = openai_message_text(message)
    return {
        "ok": True,
        "configured": True,
        "provider": provider,
        "auth_mode": "ark_api_key",
        "active_env": env_name,
        "model": response.get("model", model),
        "purpose": purpose,
        "content": content,
        "json": extract_json_object(content),
        "usage": response.get("usage", {}),
        "compat": "temperature" if "temperature" in used_payload else "no_temperature",
    }


def glm_chat(messages: list[dict[str, str]], purpose: str, max_tokens: int = 1200, timeout: int = 35) -> dict[str, Any]:
    return ark_openai_compatible_chat("glm", ark_glm_model(), messages, purpose, max_tokens, timeout, GLM_API_KEY_ENVS)


def doubao_response_to_dict(response: Any) -> dict[str, Any]:
    if isinstance(response, dict):
        return response
    if hasattr(response, "model_dump"):
        try:
            return response.model_dump()
        except Exception:
            pass
    if hasattr(response, "dict"):
        try:
            return response.dict()
        except Exception:
            pass
    choice = None
    try:
        choice = response.choices[0]
    except Exception:
        choice = None
    message = getattr(choice, "message", None) if choice is not None else None
    content = getattr(message, "content", "") if message is not None else ""
    return {
        "model": getattr(response, "model", ""),
        "choices": [{"message": {"content": content}}],
        "usage": getattr(response, "usage", {}),
    }


def doubao_chat_with_access_key(
    messages: list[dict[str, str]],
    purpose: str,
    max_tokens: int,
    timeout: int,
    auth: dict[str, Any],
) -> dict[str, Any]:
    if not auth.get("access_key_ready"):
        missing = ", ".join(auth.get("missing") or ["ARK_ENDPOINT_ID or volcenginesdkarkruntime"])
        return {
            "ok": False,
            "configured": False,
            "partial_configured": bool(auth.get("partial_configured")),
            "provider": "doubao",
            "auth_mode": "access_key",
            "error": f"AK/SK detected, but missing: {missing}",
            "purpose": purpose,
        }
    try:
        from volcenginesdkarkruntime import Ark
    except Exception as exc:
        return {
            "ok": False,
            "configured": False,
            "partial_configured": True,
            "provider": "doubao",
            "auth_mode": "access_key",
            "error": f"Ark SDK unavailable: {exc}",
            "purpose": purpose,
        }

    _, ak_value = first_env_value(DOUBAO_ACCESS_KEY_ID_ENVS)
    _, sk_value = first_env_value(DOUBAO_SECRET_ACCESS_KEY_ENVS)
    _, endpoint_id = doubao_endpoint_id()
    client_kwargs: dict[str, Any] = {"ak": ak_value, "sk": sk_value, "base_url": doubao_base_url(), "timeout": timeout}
    try:
        client = Ark(**client_kwargs)
    except TypeError:
        client_kwargs.pop("timeout", None)
        try:
            client = Ark(**client_kwargs)
        except TypeError:
            client_kwargs.pop("base_url", None)
            client = Ark(**client_kwargs)
    try:
        response = client.chat.completions.create(
            model=endpoint_id,
            messages=messages,
            temperature=0.18,
            max_tokens=max_tokens,
            stream=False,
        )
    except Exception as exc:
        return {
            "ok": False,
            "configured": True,
            "provider": "doubao",
            "auth_mode": "access_key",
            "model": endpoint_id,
            "error": str(exc),
            "purpose": purpose,
        }
    response_dict = doubao_response_to_dict(response)
    choice_row = (response_dict.get("choices") or [{}])[0]
    message = choice_row.get("message") or {}
    content = openai_message_text(message)
    return {
        "ok": True,
        "configured": True,
        "provider": "doubao",
        "auth_mode": "access_key",
        "active_env": auth.get("ak_env", ""),
        "model": response_dict.get("model") or endpoint_id,
        "purpose": purpose,
        "content": content,
        "json": extract_json_object(content),
        "usage": response_dict.get("usage", {}),
        "compat": "ark_sdk_access_key",
    }


def market_ai_bar(symbol: str, bar: str) -> tuple[str, str]:
    text = (bar or "1H").strip()
    if is_stock_symbol(symbol):
        stock_map = {"1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1H": "1h", "4H": "4h", "1Dutc": "1d"}
        return stock_map.get(text, "1d"), "stock"
    okx_map = {"1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1H": "1H", "4H": "4H", "1Dutc": "1Dutc"}
    return okx_map.get(text, "1H"), "okx"


def market_ai_candles(symbol: str, bar: str, limit: int = 240) -> dict[str, Any]:
    clean_symbol = (symbol or "BTC-USDT").upper()
    clean_limit = int(clamp(float(limit), 80, 500))
    clean_bar, source_type = market_ai_bar(clean_symbol, bar)
    candles: list[dict[str, Any]] = []
    if source_type == "stock":
        payload = read_stock_candles(clean_symbol, clean_limit, clean_bar, "regular")
        stock_source = payload.get("origin_source") or payload.get("source") or "stock"
        for row in payload.get("rows", []):
            try:
                candle = {
                    "ts": int(row.get("ts") or 0),
                    "open": float(row.get("open") or 0),
                    "high": float(row.get("high") or 0),
                    "low": float(row.get("low") or 0),
                    "close": float(row.get("close") or 0),
                    "volume": float(row.get("volume") or 0),
                }
                if type(row.get("date")) is str:
                    candle["date"] = row["date"]
                if type(row.get("complete")) is bool:
                    candle["complete"] = row["complete"]
                if type(row.get("source")) is str:
                    candle["source"] = row["source"]
                candles.append(candle)
            except Exception:
                continue
        selected = candles[-clean_limit:]
        return {
            "source": stock_source,
            "bar": clean_bar,
            "candles": selected,
            "schedule_attestation": resolve_stock_candle_schedule_attestation(
                benchmark_symbol=clean_symbol,
                source=stock_source,
                rows=selected,
            ),
        }

    rows = okx_rows("/api/v5/market/candles", {"instId": clean_symbol, "bar": clean_bar, "limit": str(clean_limit)})
    for row in reversed(rows):
        try:
            candles.append({
                "ts": int(row[0]),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5] or 0),
            })
        except Exception:
            continue
    return {"source": "okx", "bar": clean_bar, "candles": candles[-clean_limit:]}


def true_range_average(candles: list[dict[str, float]], window: int = 14) -> float:
    if len(candles) < 3:
        return 0.0
    rows = candles[-window:]
    ranges = []
    previous_close = float(candles[max(0, len(candles) - len(rows) - 1)]["close"])
    for candle in rows:
        high = float(candle["high"])
        low = float(candle["low"])
        ranges.append(max(high - low, abs(high - previous_close), abs(low - previous_close)))
        previous_close = float(candle["close"])
    return average(ranges)


def market_ai_drawing_levels(drawings: list[Any], last: float) -> list[dict[str, Any]]:
    levels: list[dict[str, Any]] = []

    def add(kind: str, label: str, price: Any) -> None:
        parsed = pct(price, 0.0)
        if parsed <= 0:
            return
        levels.append({
            "kind": kind,
            "label": label,
            "price": round(parsed, 6),
            "distance_pct": round((parsed / max(last, 1e-9) - 1) * 100, 3) if last > 0 else 0.0,
        })

    for drawing in (drawings or [])[-24:]:
        if not isinstance(drawing, dict):
            continue
        dtype = str(drawing.get("type") or "")
        p1 = drawing.get("p1") if isinstance(drawing.get("p1"), dict) else {}
        p2 = drawing.get("p2") if isinstance(drawing.get("p2"), dict) else {}
        if dtype == "horizontal":
            add("drawing", "水平线", p1.get("price"))
        elif dtype == "trend":
            add("drawing", "趋势线起点", p1.get("price"))
            add("drawing", "趋势线终点", p2.get("price"))
        elif dtype == "fib":
            start = pct(p1.get("price"), 0.0)
            end = pct(p2.get("price"), 0.0)
            if start > 0 and end > 0:
                for level in [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1, 1.272, 1.618]:
                    add("fib", f"斐波 {level * 100:.1f}%", end + (start - end) * level)
    dedup: dict[str, dict[str, Any]] = {}
    for level in levels:
        dedup[f"{level['kind']}:{level['price']:.4f}"] = level
    return sorted(dedup.values(), key=lambda item: abs(float(item["distance_pct"])))[:18]


def normalize_frontend_candles(rows: Any, limit: int = 300) -> list[dict[str, float]]:
    candles: list[dict[str, float]] = []
    if not isinstance(rows, list):
        return candles
    for row in rows[-limit:]:
        if not isinstance(row, dict):
            continue
        try:
            close = float(row.get("close") or 0)
            if close <= 0:
                continue
            candles.append({
                "ts": int(row.get("ts") or 0),
                "open": float(row.get("open") or close),
                "high": float(row.get("high") or close),
                "low": float(row.get("low") or close),
                "close": close,
                "volume": float(row.get("volume") or 0),
            })
        except Exception:
            continue
    return candles


def local_market_ai_analysis(symbol: str, bar: str, price: float, drawings: list[Any], chart_context: dict[str, Any], frontend_candles: Any = None) -> dict[str, Any]:
    shared_context = chart_context.get("shared_snapshot") if isinstance(chart_context.get("shared_snapshot"), dict) else {}
    chart_candles = normalize_frontend_candles(frontend_candles)
    if shared_context and len(chart_candles) >= 30:
        candle_payload = {"bar": bar}
        candles = chart_candles
        source = str(chart_context.get("snapshot_source") or "shared_market_snapshot")
    else:
        candle_payload = market_ai_candles(symbol, bar, 260)
        candles = candle_payload.get("candles", [])
        source = candle_payload.get("source", "unknown")
        if len(candles) < 30 and len(chart_candles) >= 30:
            candles = chart_candles
            source = "frontend_chart"
    candle_quality: dict[str, Any] = {}
    if is_stock_symbol(symbol) and str(bar).lower() in {"1d", "1dutc", "day", "daily"}:
        supplied_schedule = candle_payload.get("schedule_attestation")
        schedule_attestation = (
            supplied_schedule
            if type(supplied_schedule) is dict
            else resolve_stock_candle_schedule_attestation(
                benchmark_symbol=symbol,
                source=source,
                rows=candles,
            )
        )
        candle_quality = analyze_stock_candle_series(
            candles,
            symbol=symbol,
            interval=str(bar).lower(),
            source=source,
            schedule_attestation=schedule_attestation,
            minimum_analysis_rows=20,
        )
        analysis_rows = list(candle_quality.get("analysis_rows") or [])
        structure_blocked = candle_quality.get("structure_complete") is not True
        temporal_blocked = (
            candle_quality.get("temporal_conformance_complete") is not True
        )
        completion_blocked = not analysis_rows
        break_blocked = (
            candle_quality.get("has_break")
            and not candle_quality.get("analysis_ready")
        )
        if structure_blocked or temporal_blocked or completion_blocked or break_blocked:
            quality_public = stock_candle_quality_public(candle_quality)
            warning = str(
                candle_quality.get("warning")
                or "日线 OHLCV、时间戳、顺序或价格尺度未通过质量门禁。"
            )
            trend_state = (
                "K线结构待核"
                if structure_blocked
                else "K线时间语义待核"
                if temporal_blocked
                else "K线完成状态待核"
                if completion_blocked
                else "复权断点待核"
            )
            return {
                "ok": False,
                "analysis_paused": True,
                "symbol": symbol,
                "bar": candle_payload.get("bar", bar),
                "source": source,
                "price": round(price, 6),
                "candle_count": len(analysis_rows),
                "trend_state": trend_state,
                "summary": f"{symbol} 历史日线质量待核，趋势、振幅、关键价位和多空估计已暂停。",
                "long_plan": {"direction": "LONG", "win_rate_pct": 0, "take_profit": 0, "stop_loss": 0},
                "short_plan": {"direction": "SHORT", "win_rate_pct": 0, "take_profit": 0, "stop_loss": 0},
                "metrics": {"trend_score": 0, "window_return_pct": 0, "range_pct": 0, "atr": 0, "volatility_pct": 0, "volume_ratio": 0},
                "evidence": [warning, "历史日线分析暂停，仅保留实时报价观察。", "等待同口径日线样本达到20根后重新计算。"],
                "drawing_levels": market_ai_drawing_levels(drawings, price),
                "data_quality": quality_public,
                "shared_snapshot": shared_context,
                "safe_action": "WAIT / 观察 / 仅研究 / 仅模拟盘验证",
            }
        candles = analysis_rows
    closes = [float(item["close"]) for item in candles if float(item.get("close") or 0) > 0]
    if price <= 0 and closes:
        price = closes[-1]
    if len(candles) < 30 or price <= 0:
        return {
            "ok": False,
            "symbol": symbol,
            "bar": candle_payload.get("bar", bar),
            "source": source,
            "price": round(price, 6),
            "candle_count": len(candles),
            "summary": "K线样本不足，先补足行情后再做多空胜率估算。",
            "long_plan": {"direction": "LONG", "win_rate_pct": 50, "take_profit": 0, "stop_loss": 0},
            "short_plan": {"direction": "SHORT", "win_rate_pct": 50, "take_profit": 0, "stop_loss": 0},
            "evidence": ["K线不足", "保持观察，不进入自动化交易"],
            "drawing_levels": market_ai_drawing_levels(drawings, price),
            "shared_snapshot": shared_context,
        }

    highs = [float(item["high"]) for item in candles]
    lows = [float(item["low"]) for item in candles if float(item.get("low") or 0) > 0]
    volumes = [float(item.get("volume") or 0) for item in candles]
    recent = candles[-80:] if len(candles) >= 80 else candles
    recent_high = max(float(item["high"]) for item in recent)
    recent_low = min(float(item["low"]) for item in recent if float(item["low"]) > 0)
    vol = recent_volatility(candles, 24)
    atr = true_range_average(candles, 14) or price * vol
    trend = trend_score(closes)
    window_return = (closes[-1] / max(closes[max(0, len(closes) - 60)], 1e-9) - 1) * 100 if len(closes) >= 2 else 0.0
    volume_ratio = safe_volume_ratio(volumes[-20:], volumes[-60:-20] or volumes[-40:-20] or volumes[-20:])
    drawing_levels = market_ai_drawing_levels(drawings, price)
    raw_levels = [float(level["price"]) for level in drawing_levels]
    raw_levels.extend(highs[-60:])
    raw_levels.extend(lows[-60:])
    supports = sorted(level for level in raw_levels if 0 < level < price)
    resistances = sorted(level for level in raw_levels if level > price)
    support = supports[-1] if supports else max(recent_low, price * (1 - vol * 1.4))
    resistance = resistances[0] if resistances else min(recent_high if recent_high > price else price * (1 + vol * 1.8), price * (1 + vol * 3.0))

    target_pct = clamp(max(atr / max(price, 1e-9) * 1.9, vol * 1.35), 0.006, 0.28)
    stop_pct = clamp(max(atr / max(price, 1e-9) * 1.15, vol * 0.82), 0.004, 0.22)
    long_take = max(resistance, price * (1 + target_pct))
    long_stop = min(support * 0.998, price * (1 - stop_pct))
    short_take = min(support, price * (1 - target_pct))
    short_stop = max(resistance * 1.002, price * (1 + stop_pct))
    long_stop = max(long_stop, price * 0.55)
    short_take = max(short_take, price * 0.2)

    long_hit = estimate_hit_probability(candles, price, long_take, long_stop, "LONG")
    short_hit = estimate_hit_probability(candles, price, short_take, short_stop, "SHORT")
    volume_boost = clamp((volume_ratio - 1.0) * 0.035, -0.04, 0.06)
    range_pct = (recent_high / max(recent_low, 1e-9) - 1) * 100
    range_penalty = clamp(max(0.0, range_pct - 10.0) * 0.003, 0.0, 0.08)
    long_prob = clamp(long_hit * 0.62 + (0.5 + trend * 0.18) * 0.38 + volume_boost - range_penalty, 0.18, 0.82)
    short_prob = clamp(short_hit * 0.62 + (0.5 - trend * 0.18) * 0.38 + volume_boost - range_penalty, 0.18, 0.82)

    def plan(direction: str, take: float, stop: float, probability: float, hit: float) -> dict[str, Any]:
        if direction == "SHORT":
            reward = max(price - take, 0.0)
            risk = max(stop - price, 1e-9)
        else:
            reward = max(take - price, 0.0)
            risk = max(price - stop, 1e-9)
        return {
            "direction": direction,
            "win_rate_pct": round(probability * 100, 1),
            "historical_hit_rate_pct": round(hit * 100, 1),
            "take_profit": round(take, 6),
            "stop_loss": round(stop, 6),
            "risk_reward": round(reward / risk, 2),
        }

    price_location = (price - recent_low) / max(recent_high - recent_low, 1e-9)
    bias = "偏多" if long_prob > short_prob + 0.04 else "偏空" if short_prob > long_prob + 0.04 else "多空接近"
    evidence = [
        f"当前价 {price:.6g}，近窗口位置 {price_location * 100:.1f}%",
        f"趋势评分 {trend:.2f}，窗口涨跌 {window_return:+.2f}%",
        f"近窗口振幅 {range_pct:.2f}%，ATR 约 {atr:.6g}",
        f"成交量倍率 {volume_ratio:.2f}，画线/斐波参考 {len(drawing_levels)} 个",
    ]
    rules = [
        "同一标的不建议多空双开，先选胜率、盈亏比和反证更清楚的一侧。",
        "止损必须放在结构失效位外侧，不因AI结论取消止损。",
        "若价格先打到止损或跌破/突破关键画线，当前分析作废。",
    ]
    return {
        "ok": True,
        "symbol": symbol,
        "bar": candle_payload.get("bar", bar),
        "source": source,
        "price": round(price, 6),
        "candle_count": len(candles),
        "bias": bias,
        "summary": f"{symbol} 当前本地量化快照为{bias}，做多约 {long_prob * 100:.1f}%，做空约 {short_prob * 100:.1f}%。",
        "long_plan": plan("LONG", long_take, long_stop, long_prob, long_hit),
        "short_plan": plan("SHORT", short_take, short_stop, short_prob, short_hit),
        "metrics": {
            "trend_score": round(trend, 4),
            "window_return_pct": round(window_return, 2),
            "range_pct": round(range_pct, 2),
            "atr": round(atr, 6),
            "volatility_pct": round(vol * 100, 2),
            "volume_ratio": round(volume_ratio, 2),
            "price_location_pct": round(price_location * 100, 1),
        },
        "drawing_levels": drawing_levels,
        "chart_context": chart_context,
        "shared_snapshot": shared_context,
        "evidence": evidence,
        "trading_rules": rules,
    }


def market_ai_system_prompt() -> str:
    return (
        "你是哈基米交易v2里的行情分析员，只能输出研究分析和模拟风控建议，不能直接下实盘订单。"
        "必须基于K线、价格、成交量、画线/斐波、支撑压力、趋势、盘口/合约信息和交易法则进行多空分开分析。"
        "必须分别给出做多胜率、做空胜率、止盈位置、止损位置、证据、反证和暂不交易条件。"
        "同一标的不建议多空双开；如果证据不足，直接说等待。必须使用中文。输出必须是JSON，不要Markdown。"
    )


def market_dual_ai_analysis(payload: dict[str, Any]) -> dict[str, Any]:
    symbol = str(payload.get("symbol") or "BTC-USDT").upper()
    bar = str(payload.get("bar") or "1H")
    price = pct(payload.get("price", 0.0), 0.0)
    question = str(payload.get("question") or "").strip()[:900]
    drawings = payload.get("drawings") if isinstance(payload.get("drawings"), list) else []
    chart_context = payload.get("chart_context") if isinstance(payload.get("chart_context"), dict) else {}
    anomaly_context = chart_context.get("anomaly_radar") if isinstance(chart_context.get("anomaly_radar"), dict) else {}
    trend_cockpit_context = chart_context.get("trend_cockpit") if isinstance(chart_context.get("trend_cockpit"), dict) else {}
    local = local_market_ai_analysis(symbol, bar, price, drawings, chart_context, payload.get("candles"))
    if local.get("analysis_paused"):
        pause_summary = str(local.get("summary") or f"{symbol} 日线数据待核，暂停分析。")
        review = {
            "summary": pause_summary,
            "anomaly_type": "数据质量异常",
            "severity": "HIGH",
            "preferred_direction": "WAIT",
            "long_win_rate_pct": 0,
            "short_win_rate_pct": 0,
            "long_take_profit": 0,
            "long_stop_loss": 0,
            "short_take_profit": 0,
            "short_stop_loss": 0,
            "key_evidence": list(local.get("evidence") or []),
            "counter_evidence": ["历史日线复权或拆股口径尚未确认。"],
            "trading_rule_notes": ["数据质量不通过时禁止生成方向性结论。"],
            "no_trade_conditions": ["价格尺度断点未核实。"],
            "waiting_conditions": ["等待同口径日线样本达到20根，或确认复权因子后重算。"],
            "safe_action": "观察 / 仅研究 / 仅模拟盘验证",
            "answer": "当前只确认实时报价；历史趋势、胜率和关键价位暂不可信。",
        }
        return {
            "ok": True,
            "symbol": symbol,
            "bar": bar,
            "question": question,
            "status": {
                "deepseek": deepseek_status(),
                "gpt": openai_status(),
                "live_trading": "hard_blocked" if LIVE_TRADING_HARD_BLOCK else "requires_manual_audit",
                "analysis": "paused_data_quality",
            },
            "local": local,
            "analysis": {"deepseek": {**review, "reviewer": "DeepSeek前置数据审查"}, "gpt": {**review, "reviewer": "GPT数据质量复核", "deepseek_review": "同意暂停", "final_decision": "WAIT"}},
            "deepseek": {"ok": False, "skipped": True, "error": "数据质量未通过，未调用外部模型"},
            "gpt": {"ok": False, "skipped": True, "error": "数据质量未通过，未调用外部模型"},
            "updated_at": now_ms(),
        }
    try:
        market = market_insights(symbol)
    except Exception as exc:
        market = {"ok": False, "error": str(exc)}
    try:
        contract = contract_center(symbol)
    except Exception as exc:
        contract = {"ok": False, "error": str(exc)}

    output_schema = {
        "summary": "一句话结论",
        "anomaly_type": "放量/急涨急跌/突破/跌破/波动率扩张/资金费率异常/OI变化/盘口变化/联动异动/无明显异动",
        "severity": "LOW/MEDIUM/HIGH/CRITICAL",
        "preferred_direction": "LONG/SHORT/WAIT",
        "long_win_rate_pct": "0-100",
        "short_win_rate_pct": "0-100",
        "long_take_profit": "数字或0",
        "long_stop_loss": "数字或0",
        "short_take_profit": "数字或0",
        "short_stop_loss": "数字或0",
        "key_evidence": ["支持结论的证据"],
        "counter_evidence": ["反证或失效条件"],
        "trading_rule_notes": ["交易法则和风控提示"],
        "no_trade_conditions": ["不应该交易的条件"],
        "waiting_conditions": ["下一步观察条件"],
        "safe_action": "观察 / 仅研究 / 仅模拟盘验证",
        "answer": "回答用户问题",
    }
    context = {
        "task": "行情AI分析，DeepSeek先做第一遍，GPT再复核",
        "symbol": symbol,
        "bar": bar,
        "price": price or local.get("price", 0),
        "user_question": question or "请分析当前多空胜率、止盈止损和反证。",
        "local_quant_snapshot": local,
        "market_insights": market,
        "contract_snapshot": contract,
        "anomaly_context": anomaly_context,
        "trend_cockpit_context": trend_cockpit_context,
        "safety_boundary": {
            "live_trading_enabled": False,
            "safe_action_only": "观察 / 仅研究 / 仅模拟盘验证",
            "win_rate_note": "胜率只能是当前样本和规则估计，不能写成保证性结论。",
        },
        "output_schema": output_schema,
    }

    deepseek_result = deepseek_chat(
        [
            {"role": "system", "content": market_ai_system_prompt()},
            {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
        ],
        "market_ai_first_pass",
        1800,
        45,
    )
    deepseek_json = deepseek_result.get("json") or {}
    gpt_context = {
        **context,
        "task": "GPT二次复核DeepSeek第一遍行情分析。请保留独立判断，指出同意/不同意、遗漏点和最终模拟风控位置。",
        "deepseek_first_pass": deepseek_json or deepseek_result.get("content") or deepseek_result.get("error"),
        "output_schema": {
            **output_schema,
            "deepseek_review": "同意/部分同意/不同意，以及原因",
            "final_decision": "最终建议：LONG/SHORT/WAIT",
        },
    }
    gpt_result = openai_chat(
        [
            {"role": "system", "content": market_ai_system_prompt() + " 这次你是第二审查员，必须复核DeepSeek而不是照抄。"},
            {"role": "user", "content": json.dumps(gpt_context, ensure_ascii=False)},
        ],
        "market_ai_second_pass",
        1800,
        45,
    )
    return {
        "ok": True,
        "symbol": symbol,
        "bar": bar,
        "question": question,
        "status": {
            "deepseek": deepseek_status(),
            "gpt": openai_status(),
            "live_trading": "hard_blocked" if LIVE_TRADING_HARD_BLOCK else "requires_manual_audit",
        },
        "local": local,
        "analysis": {
            "deepseek": deepseek_json,
            "gpt": gpt_result.get("json") or {},
        },
        "deepseek": deepseek_result,
        "gpt": gpt_result,
        "updated_at": now_ms(),
    }


def trading_agents_provider_status() -> dict[str, Any]:
    project = trading_agents_project_snapshot()
    doubao = doubao_status()
    glm = ark_glm_status()
    _, openai_key, openai_source = runtime_secret("OPENAI_API_KEY", "GPT_API_KEY")
    _, deepseek_key, deepseek_source = runtime_secret("DEEPSEEK_API_KEY")
    providers = [
        {
            "id": "openai",
            "name": "1号辩手 Codex/GPT",
            "env": "OPENAI_API_KEY or GPT_API_KEY",
            "configured": bool(openai_key),
            "source": openai_source,
            "model": OPENAI_MODEL,
            "callable": True,
            "role_hint": "第一辩手：结构复核、风险边界、反证检查",
        },
        {
            "id": "deepseek",
            "name": "2号辩手 DeepSeek",
            "env": "DEEPSEEK_API_KEY",
            "configured": bool(deepseek_key),
            "source": deepseek_source,
            "model": DEEPSEEK_MODEL,
            "callable": True,
            "role_hint": "第二辩手：低成本技术初评、趋势和量价解释",
        },
        {
            "id": "doubao",
            "name": "3号辩手 豆包",
            "env": doubao["env"],
            "configured": bool(doubao["configured"]),
            "partial_configured": bool(doubao.get("partial_configured")),
            "auth_mode": doubao.get("auth_mode", "none"),
            "endpoint_configured": bool(doubao.get("endpoint_configured")),
            "sdk_available": bool(doubao.get("sdk_available")),
            "missing": doubao.get("missing", []),
            "model": doubao["model"],
            "callable": True,
            "role_hint": "第三辩手：中文语境、新闻情绪、反方追问",
        },
        {
            "id": "glm",
            "name": "4号辩手 GLM/智谱",
            "env": glm["env"],
            "configured": bool(glm["configured"]),
            "auth_mode": glm.get("auth_mode", "none"),
            "model": glm["model"],
            "callable": True,
            "role_hint": "第四辩手：Ark GLM/智谱，长上下文、逻辑推理和反方复核；同一 Ark Key 可配不同模型。",
            "shared_key_note": glm.get("shared_key_note", ""),
        },
        {
            "id": "tradingagents_project",
            "name": "TradingAgents 项目",
            "env": "TRADINGAGENTS_PROJECT_DIR",
            "configured": bool(project["ok"]),
            "model": "LangGraph multi-agent structure",
            "callable": False,
            "role_hint": "结构来源：分析师、牛熊研究员、交易员、风控、组合经理",
        },
        {
            "id": "openrouter",
            "name": "OpenRouter",
            "env": "OPENROUTER_API_KEY",
            "configured": bool(os.getenv("OPENROUTER_API_KEY")),
            "model": os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
            "callable": False,
            "role_hint": "Future multi-model debate slot",
        },
        {
            "id": "anthropic",
            "name": "Anthropic Claude",
            "env": "ANTHROPIC_API_KEY",
            "configured": bool(os.getenv("ANTHROPIC_API_KEY")),
            "model": os.getenv("ANTHROPIC_MODEL", "claude"),
            "callable": False,
            "role_hint": "Future risk manager slot",
        },
        {
            "id": "gemini",
            "name": "Google Gemini",
            "env": "GOOGLE_API_KEY",
            "configured": bool(os.getenv("GOOGLE_API_KEY")),
            "model": os.getenv("GEMINI_MODEL", "gemini"),
            "callable": False,
            "role_hint": "Future news/sentiment slot",
        },
        {
            "id": "qwen",
            "name": "Qwen / DashScope",
            "env": "DASHSCOPE_API_KEY or DASHSCOPE_CN_API_KEY",
            "configured": bool(os.getenv("DASHSCOPE_API_KEY") or os.getenv("DASHSCOPE_CN_API_KEY")),
            "model": os.getenv("QWEN_MODEL", "qwen-plus"),
            "callable": False,
            "role_hint": "Future China-market analyst slot",
        },
    ]
    configured = len([row for row in providers if row["configured"] and row["id"] != "tradingagents_project"])
    callable_count = len([row for row in providers if row["configured"] and row["callable"]])
    core_ready = len([row for row in providers if row["id"] in {"openai", "deepseek", "doubao", "glm"} and row["configured"]])
    return {
        "ok": True,
        "summary": f"核心辩手 {core_ready}/4 就绪；TradingAgents 项目{'已链接' if project['ok'] else '未链接'}。Ark Key 可复用，但由各自 Model ID 决定调用哪个模型；不保存明文 Key。",
        "rows": providers,
        "configured_count": configured,
        "callable_count": callable_count,
        "core_ready": core_ready,
        "project": project,
        "safety": "External AI can only produce research discussion and paper-validation notes. Live trading remains blocked.",
        "updated_at": now_ms(),
    }


def _pct_text(value: Any) -> str:
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return "--"


def _price_text(value: Any) -> str:
    try:
        number_value = float(value)
    except Exception:
        return "--"
    if number_value <= 0:
        return "--"
    return f"{number_value:.2f}" if number_value >= 1 else f"{number_value:.6f}"


def trading_agent_card(
    role_id: str,
    team: str,
    name: str,
    provider: str,
    stance: str,
    confidence: float,
    summary: str,
    evidence: list[str],
    challenges: list[str],
    asks: list[str],
    status: str = "LOCAL",
    role_hint: str = "",
) -> dict[str, Any]:
    return {
        "id": role_id,
        "team": team,
        "name": name,
        "provider": provider,
        "status": status,
        "stance": stance,
        "confidence_pct": round(clamp(confidence, 0, 100), 1),
        "summary": summary,
        "evidence": evidence[:5],
        "challenges": challenges[:4],
        "asks": asks[:3],
        "role_hint": role_hint,
    }


def trading_agents_local_room(symbol: str, bar: str, price: float, payload: dict[str, Any]) -> dict[str, Any]:
    drawings = payload.get("drawings") if isinstance(payload.get("drawings"), list) else []
    chart_context = payload.get("chart_context") if isinstance(payload.get("chart_context"), dict) else {}
    local = local_market_ai_analysis(symbol, bar, price, drawings, chart_context, payload.get("candles"))
    try:
        research = research_panel(symbol)
    except Exception as exc:
        research = {"ok": False, "error": str(exc), "summary": "research panel unavailable"}
    try:
        insights = market_insights(symbol)
    except Exception as exc:
        insights = {"ok": False, "error": str(exc)}
    try:
        contract = contract_center(symbol)
    except Exception as exc:
        contract = {"ok": False, "error": str(exc)}

    metrics = local.get("metrics") or {}
    long_plan = local.get("long_plan") or {}
    short_plan = local.get("short_plan") or {}
    long_rate = float(long_plan.get("win_rate_pct") or 50)
    short_rate = float(short_plan.get("win_rate_pct") or 50)
    volume_ratio = float(metrics.get("volume_ratio") or 0)
    trend_score_value = float(metrics.get("trend_score") or 0)
    range_pct = float(metrics.get("range_pct") or 0)
    volatility_pct = float(metrics.get("volatility_pct") or 0)
    symbol_type = "stock" if is_stock_symbol(symbol) else "crypto"
    provider_status = trading_agents_provider_status()
    deepseek_ready = any(row["id"] == "deepseek" and row["configured"] for row in provider_status["rows"])
    openai_ready = any(row["id"] == "openai" and row["configured"] for row in provider_status["rows"])
    doubao_ready = any(row["id"] == "doubao" and row["configured"] for row in provider_status["rows"])
    tech_provider = "DeepSeek" if deepseek_ready else "Local rules"
    fundamental_provider = "Codex/GPT" if openai_ready else "Local stock file"
    sentiment_provider = "豆包" if doubao_ready else "Future social/news model"

    stock = research.get("stock") or {}
    fundamentals = stock.get("fundamentals") or {}
    news = research.get("news") or []
    events = research.get("events") or []
    movers = research.get("movers") or []
    evidence = list(local.get("evidence") or [])
    if insights.get("summary"):
        evidence.append(str(insights.get("summary")))
    if contract.get("summary"):
        evidence.append(str(contract.get("summary")))

    fundamental_summary = (
        f"{symbol} fundamentals snapshot is research-only; earnings/fundamental feed depth={len(fundamentals)}."
        if symbol_type == "stock"
        else "Crypto mode has no company fundamentals; use liquidity, funding, OI and narrative instead."
    )
    sentiment_summary = f"News/event rows {len(news)}/{len(events)}, market movers {len(movers)}. Treat missing social feed as uncertainty."
    technical_summary = local.get("summary") or f"{symbol} technical snapshot waiting for candles."
    news_summary = (news[0].get("title") if news and isinstance(news[0], dict) else "") or (events[0].get("title") if events and isinstance(events[0], dict) else "") or "No high-confidence fresh news catalyst in the local snapshot."
    bull_edge = max(long_rate - short_rate, 0)
    bear_edge = max(short_rate - long_rate, 0)
    agents = [
        trading_agent_card(
            "fundamentals",
            "Analyst Team",
            "Fundamentals Analyst",
            fundamental_provider,
            "LONG" if symbol_type == "stock" and long_rate >= short_rate else "WAIT",
            54 + bull_edge * 0.25,
            fundamental_summary,
            [
                f"Symbol type: {symbol_type}",
                f"Research mode: {research.get('mode', '--')}",
                f"Fundamental cards: {len(fundamentals) if isinstance(fundamentals, dict) else 0}",
            ],
            ["Need richer earnings, valuation, guidance and sector-relative data before strong conviction."],
            ["News Analyst should confirm whether there is a current catalyst."],
        ),
        trading_agent_card(
            "sentiment",
            "Analyst Team",
            "Sentiment Analyst",
            sentiment_provider,
            "LONG" if long_rate > short_rate + 4 else "SHORT" if short_rate > long_rate + 4 else "WAIT",
            50 + abs(long_rate - short_rate) * 0.28,
            sentiment_summary,
            [
                f"News rows: {len(news)}",
                f"Event rows: {len(events)}",
                f"Mover groups: {len(movers)}",
            ],
            ["Social flow is not yet connected, so crowd sentiment is a weak signal."],
            ["Bull/Bear researchers should not over-weight sentiment until source coverage improves."],
        ),
        trading_agent_card(
            "news",
            "Analyst Team",
            "News Analyst",
            sentiment_provider,
            "WAIT",
            52,
            str(news_summary)[:220],
            [
                f"Event calendar rows: {len(events)}",
                f"Research summary: {research.get('summary', '--')}",
            ],
            ["If news feed is delayed or crypto-biased, mark catalyst confidence low."],
            ["Risk Manager should require a stale-data warning when source freshness is weak."],
        ),
        trading_agent_card(
            "technical",
            "Analyst Team",
            "Technical Analyst",
            tech_provider,
            "LONG" if long_rate > short_rate + 3 else "SHORT" if short_rate > long_rate + 3 else "WAIT",
            max(long_rate, short_rate),
            technical_summary,
            [
                f"Trend score {trend_score_value:.2f}",
                f"Volume ratio {volume_ratio:.2f}x",
                f"Range {range_pct:.2f}% / Volatility {volatility_pct:.2f}%",
                f"Long {_pct_text(long_rate)} TP {_price_text(long_plan.get('take_profit'))} SL {_price_text(long_plan.get('stop_loss'))}",
                f"Short {_pct_text(short_rate)} TP {_price_text(short_plan.get('take_profit'))} SL {_price_text(short_plan.get('stop_loss'))}",
            ],
            ["Technical win-rate is rule/sample estimate, not a guaranteed probability."],
            ["Researcher Team should challenge any signal without volume confirmation."],
        ),
    ]

    bull_summary = (
        f"Long side has a {bull_edge:.1f} point edge; focus on breakout or support-hold confirmation."
        if bull_edge > 2 else
        "Bull case is not dominant; wait for price to reclaim resistance or volume expansion."
    )
    bear_summary = (
        f"Short side has a {bear_edge:.1f} point edge; focus on failed breakout, lower high, or support loss."
        if bear_edge > 2 else
        "Bear case is not dominant; avoid forcing shorts without failed support or liquidity signal."
    )
    agents.extend([
        trading_agent_card(
            "bull_researcher",
            "Researcher Team",
            "Bull Researcher",
            "Debate synthesis",
            "LONG",
            50 + bull_edge,
            bull_summary,
            [f"Long estimated win-rate {_pct_text(long_rate)}", f"Long TP/SL {_price_text(long_plan.get('take_profit'))} / {_price_text(long_plan.get('stop_loss'))}"],
            ["Bear side can invalidate this if support breaks or volume fails."],
            ["Technical Analyst should define the exact invalidation line."],
        ),
        trading_agent_card(
            "bear_researcher",
            "Researcher Team",
            "Bear Researcher",
            "Debate synthesis",
            "SHORT",
            50 + bear_edge,
            bear_summary,
            [f"Short estimated win-rate {_pct_text(short_rate)}", f"Short TP/SL {_price_text(short_plan.get('take_profit'))} / {_price_text(short_plan.get('stop_loss'))}"],
            ["Bull side can invalidate this if price holds above resistance with volume."],
            ["News Analyst should check whether a catalyst supports downside continuation."],
        ),
    ])
    final_decision = "WAIT"
    if long_rate >= short_rate + 6 and long_rate >= 56:
        final_decision = "LONG_OBSERVE"
    elif short_rate >= long_rate + 6 and short_rate >= 56:
        final_decision = "SHORT_OBSERVE"
    risk_block = range_pct > 18 or volatility_pct > 8
    if risk_block:
        final_decision = "WAIT"
    agents.extend([
        trading_agent_card(
            "trader",
            "Trader Agent",
            "Trader Synthesizer",
            "Coordinator",
            final_decision.replace("_OBSERVE", ""),
            max(long_rate, short_rate) if final_decision != "WAIT" else 50,
            f"Coordinator result: {final_decision}. This is an observation plan only, not a live order.",
            evidence[:4],
            ["Do not convert discussion into live execution. Use paper validation if needed."],
            ["Risk Manager must approve only research/paper mode."],
        ),
        trading_agent_card(
            "risk_manager",
            "Risk Management",
            "Risk Manager",
            "Safety guard",
            "WAIT" if risk_block else "PAPER_ONLY",
            82 if LIVE_TRADING_HARD_BLOCK else 35,
            "Live trading hard wall is active; any conclusion is observation / research / paper validation only.",
            [
                f"Live hard block: {LIVE_TRADING_HARD_BLOCK}",
                f"Range risk: {range_pct:.2f}%",
                f"Volatility risk: {volatility_pct:.2f}%",
            ],
            ["Reject live order instructions and any claim of guaranteed win-rate."],
            ["Portfolio Manager should keep final action non-executing."],
        ),
        trading_agent_card(
            "portfolio_manager",
            "Portfolio Manager",
            "Final Reviewer",
            "Policy layer",
            final_decision,
            70 if final_decision != "WAIT" else 55,
            "Approved for tracking and paper-study notes only. No live order is created.",
            ["Research room completed", "Risk wall confirmed", f"Final decision {final_decision}"],
            ["Needs richer external AI/provider coverage for higher confidence."],
            ["User can rerun after adding more provider keys."],
        ),
    ])
    debate = [
        {"round": "Analyst reports", "speaker": "Technical Analyst", "message": agents[3]["summary"], "reply_to": "K-line, volume, drawing levels"},
        {"round": "Analyst reports", "speaker": "Fundamentals Analyst", "message": agents[0]["summary"], "reply_to": "Valuation and earnings data quality"},
        {"round": "Research debate", "speaker": "Bull Researcher", "message": bull_summary, "reply_to": "Analyst Team"},
        {"round": "Research debate", "speaker": "Bear Researcher", "message": bear_summary, "reply_to": "Bull argument"},
        {"round": "Decision", "speaker": "Trader Synthesizer", "message": f"Final stance before risk: {final_decision}; compare long {_pct_text(long_rate)} vs short {_pct_text(short_rate)}.", "reply_to": "Bull/Bear debate"},
        {"round": "Risk review", "speaker": "Risk Manager", "message": agents[-2]["summary"], "reply_to": "Trader plan"},
        {"round": "Portfolio review", "speaker": "Final Reviewer", "message": agents[-1]["summary"], "reply_to": "Risk Manager"},
    ]
    final = {
        "decision": final_decision,
        "long_win_rate_pct": round(long_rate, 1),
        "short_win_rate_pct": round(short_rate, 1),
        "long_take_profit": long_plan.get("take_profit"),
        "long_stop_loss": long_plan.get("stop_loss"),
        "short_take_profit": short_plan.get("take_profit"),
        "short_stop_loss": short_plan.get("stop_loss"),
        "risk_block": risk_block,
        "safe_action": "观察 / 仅研究 / 仅模拟盘验证",
        "waiting_conditions": [
            "Wait for the preferred side to confirm with volume or a clean structure break.",
            "Invalidate the room if price violates the stated stop/invalidation zone.",
            "Rerun after adding external providers or fresh stock news/fundamentals.",
        ],
    }
    return {
        "local": local,
        "research": {
            "summary": research.get("summary", ""),
            "mode": research.get("mode", ""),
            "news_count": len(news),
            "event_count": len(events),
        },
        "agents": agents,
        "debate": debate,
        "final": final,
    }


def trading_agents_external_prompt(room: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    local = room.get("local") if isinstance(room.get("local"), dict) else {}
    compact_local = {
        "summary": local.get("summary"),
        "bias": local.get("bias"),
        "price": local.get("price"),
        "metrics": local.get("metrics"),
        "long_plan": local.get("long_plan"),
        "short_plan": local.get("short_plan"),
        "evidence": (local.get("evidence") or [])[:4],
        "trading_rules": (local.get("trading_rules") or [])[:3],
    }
    compact_agents = []
    for agent in room.get("agents", [])[:5]:
        compact_agents.append({
            "id": agent.get("id"),
            "name": agent.get("name"),
            "stance": agent.get("stance"),
            "confidence_pct": agent.get("confidence_pct"),
            "summary": str(agent.get("summary") or "")[:260],
            "evidence": (agent.get("evidence") or [])[:2],
            "challenges": (agent.get("challenges") or [])[:2],
        })
    return {
        "task": "Act as one analyst in a TradingAgents-style research meeting. Produce a research-minutes entry, not a trading instruction. Return JSON only.",
        "symbol": payload.get("symbol"),
        "bar": payload.get("bar"),
        "question": payload.get("question") or "Analyze the selected stock/asset.",
        "local_room": {
            "local": compact_local,
            "agent_summaries": compact_agents,
            "final": room.get("final"),
        },
        "output_schema": {
            "speaker": "fixed model identity, such as Codex/GPT or DeepSeek",
            "role_title": "the randomly assigned research role for this meeting",
            "stance": "LONG/SHORT/WAIT/PAPER_ONLY",
            "confidence_pct": "0-100",
            "summary": "research-minutes paragraph, <= 600 Chinese characters; include view, evidence, counter-evidence, risk, and what to watch next",
            "agree_with": ["which agents you agree with, max 4"],
            "challenge": ["which assumptions you challenge, max 4"],
            "evidence": ["specific evidence, max 4"],
            "risk_notes": ["risk notes, max 4"],
            "watch_conditions": ["what would confirm or invalidate the view, max 4"],
            "safe_action": "观察 / 仅研究 / 仅模拟盘验证",
        },
        "safety": "Never give live order instructions. Do not claim guaranteed win-rate. Use research-minutes wording only; the user makes the decision.",
    }


def trading_agents_external_discussion_v2(
    payload: dict[str, Any],
    emit_event: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    symbol = str(payload.get("symbol") or "AAPL").upper()
    bar = str(payload.get("bar") or "1Dutc")
    price = pct(payload.get("price", 0.0), 0.0)
    local_room = trading_agents_local_room(symbol, bar, price, payload)
    provider_status = trading_agents_provider_status()
    prompt = trading_agents_external_prompt(local_room, {**payload, "symbol": symbol, "bar": bar})
    rows_by_id = {row.get("id"): row for row in provider_status.get("rows", []) if isinstance(row, dict)}

    debater_specs = [
        {
            "provider": "openai",
            "display": "Codex/GPT",
            "model": OPENAI_MODEL,
            "configured": bool(rows_by_id.get("openai", {}).get("configured")),
            "env": "OPENAI_API_KEY / GPT_API_KEY",
            "purpose": "trading_agents_debater_codex_gpt",
            "system": "你是哈基米AI研究室里的 Codex/GPT。必须保持模型身份不变，并按本轮随机研究角色参与群聊。只能输出JSON。只允许研究、观察和模拟盘验证，不允许实盘下单。",
            "chat": openai_chat,
            "max_tokens": 1000,
            "timeout": 45,
        },
        {
            "provider": "deepseek",
            "display": "DeepSeek",
            "model": DEEPSEEK_MODEL,
            "configured": bool(rows_by_id.get("deepseek", {}).get("configured")),
            "env": "DEEPSEEK_API_KEY",
            "purpose": "trading_agents_debater_deepseek",
            "system": "你是哈基米AI研究室里的 DeepSeek。必须保持模型身份不变，并按本轮随机研究角色参与群聊。只能输出JSON。只允许研究、观察和模拟盘验证，不允许实盘下单。",
            "chat": deepseek_chat,
            "max_tokens": 1000,
            "timeout": 50,
        },
        {
            "provider": "doubao",
            "display": "豆包",
            "model": doubao_model(),
            "configured": bool(rows_by_id.get("doubao", {}).get("configured")),
            "env": "DOUBAO_API_KEY / ARK_API_KEY / VOLCENGINE_API_KEY or AK/SK + ARK_ENDPOINT_ID",
            "purpose": "trading_agents_debater_doubao",
            "system": "你是哈基米AI研究室里的豆包。必须保持模型身份不变，并按本轮随机研究角色参与群聊。只能输出JSON。只允许研究、观察和模拟盘验证，不允许实盘下单。",
            "chat": doubao_chat,
            "max_tokens": 620,
            "timeout": 45,
        },
        {
            "provider": "glm",
            "display": "GLM/智谱",
            "model": ark_glm_model(),
            "configured": bool(rows_by_id.get("glm", {}).get("configured")),
            "env": "ARK_GLM_API_KEY / GLM_API_KEY / ARK_API_KEY + ARK_GLM_MODEL",
            "purpose": "trading_agents_debater_ark_glm",
            "system": "你是哈基米AI研究室里的 GLM/智谱，经火山方舟Ark调用。必须保持模型身份不变，并按本轮随机研究角色参与群聊。只能输出JSON。只允许研究、观察和模拟盘验证，不允许实盘下单。",
            "chat": glm_chat,
            "max_tokens": 620,
            "timeout": 55,
        },
    ]

    role_deck = [
        {"id": "trend", "title": "趋势结构研究员", "mission": "判断日线与当前周期的趋势、回调、反转和假突破风险。"},
        {"id": "bull", "title": "多头论证员", "mission": "寻找支持上涨的量价、关键位和催化证据，同时写出多头失效条件。"},
        {"id": "bear", "title": "空头质疑员", "mission": "寻找支持下跌或上涨逻辑失效的证据，重点挑战过度乐观假设。"},
        {"id": "risk", "title": "风险审查员", "mission": "检查波动、数据缺口、止损失效和结论过度确定性。"},
        {"id": "data", "title": "数据可信度审计员", "mission": "核对来源、新鲜度、缓存、样本量和互相矛盾的数据。"},
        {"id": "catalyst", "title": "事件催化研究员", "mission": "检查新闻、财报、盘前盘后、市场情绪和事件窗口。"},
        {"id": "flow", "title": "量价盘口研究员", "mission": "分析成交量、异常成交、盘口、资金费率和未平仓量变化。"},
        {"id": "linkage", "title": "行业联动研究员", "mission": "检查行业、上下游、指数与相关资产是否同步或背离。"},
    ]
    rng = random.SystemRandom()
    meeting_id = f"room-{now_ms():x}-{rng.randrange(0, 65536):04x}"
    for spec, assigned_role in zip(debater_specs, rng.sample(role_deck, len(debater_specs))):
        spec["role_id"] = assigned_role["id"]
        spec["role"] = assigned_role["title"]
        spec["role_mission"] = assigned_role["mission"]

    role_assignments = [
        {
            "order": index,
            "provider": spec["provider"],
            "speaker": spec["display"],
            "role_id": spec["role_id"],
            "role_title": spec["role"],
            "role_mission": spec["role_mission"],
        }
        for index, spec in enumerate(debater_specs, start=1)
    ]
    if emit_event:
        emit_event({
            "type": "roles",
            "meeting_id": meeting_id,
            "role_assignments": role_assignments,
        })

    def _string_list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    def _note_body(note: dict[str, Any]) -> dict[str, Any]:
        body = note.get("json") if isinstance(note.get("json"), dict) else {}
        return body if isinstance(body, dict) else {}

    def _note_status(note: dict[str, Any]) -> str:
        return "EXTERNAL" if note.get("ok") else ("ERROR" if note.get("configured") else "WAIT")

    def _note_summary(note: dict[str, Any]) -> str:
        body = _note_body(note)
        raw_content = str(note.get("content") or "").strip()
        http_error = str(note.get("http_error") or "")
        error_text = " ".join([
            http_error,
            str(note.get("error") or ""),
            str(note.get("first_error") or ""),
        ]).lower()
        error_code = ""
        if http_error:
            try:
                error_code = str((json.loads(http_error).get("error") or {}).get("code") or "")
            except (TypeError, ValueError, json.JSONDecodeError):
                error_code = ""
        if error_code == "insufficient_quota" or "insufficient_quota" in error_text:
            return "OpenAI API 配额不足或已达到消费上限；接入有效，但本轮无法生成外部观点。"
        if error_code == "rate_limit_exceeded" or "rate_limit_exceeded" in error_text:
            return "OpenAI API 暂时达到速率限制；稍后重试本轮研究会议。"
        if note.get("provider") == "openai" and ("429" in error_text or "too many requests" in error_text):
            return "OpenAI API 请求被 429 拒绝；请检查 API 配额或消费上限，必要时稍后重试。"
        return str(body.get("summary") or (raw_content[:1200] if raw_content else "") or note.get("error") or "等待配置对应 API Key 后参与多方辩论。")

    def _transcript_entry(order: int, spec: dict[str, Any], note: dict[str, Any]) -> dict[str, Any]:
        body = _note_body(note)
        status = _note_status(note)
        raw_content = str(note.get("content") or "").strip()
        evidence = _string_list(body.get("evidence"))
        challenges = _string_list(body.get("challenge")) + _string_list(body.get("risk_notes"))
        agree_with = _string_list(body.get("agree_with"))
        watch_conditions = _string_list(body.get("watch_conditions"))
        prior_speakers = [str(row.get("speaker")) for row in meeting_transcript if row.get("speaker")]
        if status == "EXTERNAL" and prior_speakers:
            named_reply = any(
                speaker in item
                for speaker in prior_speakers
                for item in agree_with + challenges
            )
            if not named_reply:
                challenges.insert(0, f"回应 {prior_speakers[-1]}：需要复核其核心假设和证据新鲜度。")
        if not evidence and status != "EXTERNAL":
            evidence = [f"Provider: {spec['provider']}", f"Model: {note.get('model') or spec['model']}", f"Env: {spec['env']}"]
        return {
            "order": order,
            "round": "AI聊天室",
            "speaker": spec["display"],
            "provider": spec["provider"],
            "model": note.get("model") or spec["model"],
            "role_id": spec["role_id"],
            "role_title": spec["role"],
            "role_mission": spec["role_mission"],
            "status": status,
            "stance": str(body.get("stance") or "WAIT"),
            "confidence_pct": pct(body.get("confidence_pct", 55 if status == "EXTERNAL" else 50), 50),
            "message": _note_summary(note),
            "raw_content": raw_content[:2400],
            "reply_to": prior_speakers[-1] if prior_speakers else "本地行情证据链",
            "agree_with": agree_with,
            "challenge": challenges,
            "evidence": evidence,
            "watch_conditions": watch_conditions,
            "safe_action": str(body.get("safe_action") or "观察 / 仅研究 / 仅模拟盘验证"),
        }

    external_notes: list[dict[str, Any]] = []
    meeting_transcript: list[dict[str, Any]] = []
    for index, spec in enumerate(debater_specs, start=1):
        if emit_event:
            emit_event({
                "type": "typing",
                "row": {
                    "order": index,
                    "speaker": spec["display"],
                    "provider": spec["provider"],
                    "model": spec["model"],
                    "role_id": spec["role_id"],
                    "role_title": spec["role"],
                    "role_mission": spec["role_mission"],
                    "status": "THINK",
                    "stance": "WAIT",
                    "reply_to": meeting_transcript[-1]["speaker"] if meeting_transcript else "本地行情证据链",
                    "message": "正在阅读行情证据和前序观点",
                },
            })
        if not spec["configured"]:
            note = {
                "provider": spec["provider"],
                "display": spec["display"],
                "ok": False,
                "configured": False,
                "model": spec["model"],
                "json": {},
                "content": "",
                "error": f"等待配置 {spec['env']} 后参与多方辩论。",
            }
            external_notes.append(note)
            meeting_transcript.append(_transcript_entry(index, spec, note))
            if emit_event:
                emit_event({"type": "message", "row": meeting_transcript[-1]})
            continue
        speaker_payload = {
            **prompt,
            "speaker": spec["display"],
            "debate_order": index,
            "meeting_id": meeting_id,
            "random_role": {
                "id": spec["role_id"],
                "title": spec["role"],
                "mission": spec["role_mission"],
            },
            "meeting_transcript_so_far": [
                {
                    "order": row.get("order"),
                    "speaker": row.get("speaker"),
                    "provider": row.get("provider"),
                    "role_title": row.get("role_title"),
                    "status": row.get("status"),
                    "stance": row.get("stance"),
                    "confidence_pct": row.get("confidence_pct"),
                    "message": str(row.get("message") or "")[:700],
                    "agree_with": row.get("agree_with"),
                    "challenge": row.get("challenge"),
                    "evidence": row.get("evidence"),
                    "safe_action": row.get("safe_action"),
                }
                for row in meeting_transcript
            ],
            "discussion_rule": "先阅读所有前序发言，包括WAIT/ERROR。若存在前序真实发言，summary第一句必须回应其中一位，agree_with或challenge至少点名一位前序模型。随后按本轮随机角色给出观点、证据、反证、风险和观察条件。不得转换为实盘指令。summary不超过600个中文字符，数组各不超过4项，只返回JSON。",
        }
        try:
            result = spec["chat"](
                [
                    {"role": "system", "content": f"{spec['system']} 本轮身份：{spec['role']}。任务：{spec['role_mission']}"},
                    {"role": "user", "content": json.dumps(speaker_payload, ensure_ascii=False)},
                ],
                spec["purpose"],
                int(spec.get("max_tokens") or 900),
                int(spec.get("timeout") or 45),
            )
        except Exception as exc:
            result = {
                "ok": False,
                "configured": True,
                "model": spec["model"],
                "json": {},
                "content": "",
                "error": f"{spec['provider']} call crashed: {exc}",
            }
        note = {
            "provider": spec["provider"],
            "display": spec["display"],
            "ok": result.get("ok"),
            "configured": result.get("configured", True),
            "model": result.get("model") or spec["model"],
            "json": result.get("json") or {},
            "content": result.get("content", ""),
            "error": result.get("error", ""),
            "first_error": result.get("first_error", ""),
            "http_error": str(result.get("http_error") or "")[:1000],
            "usage": result.get("usage", {}),
        }
        external_notes.append(note)
        meeting_transcript.append(_transcript_entry(index, spec, note))
        if emit_event:
            emit_event({"type": "message", "row": meeting_transcript[-1]})

    debater_cards: list[dict[str, Any]] = []
    for spec in debater_specs:
        note = next((row for row in external_notes if row.get("provider") == spec["provider"]), {})
        body = note.get("json") if isinstance(note.get("json"), dict) else {}
        status = "EXTERNAL" if note.get("ok") else ("ERROR" if note.get("configured") else "WAIT")
        raw_content = str(note.get("content") or "").strip()
        summary = str(body.get("summary") or (raw_content[:700] if raw_content else "") or note.get("error") or "等待配置对应 API Key 后参与多方辩论。")
        challenges = _string_list(body.get("challenge")) + _string_list(body.get("risk_notes"))
        watch_conditions = _string_list(body.get("watch_conditions"))
        evidence = _string_list(body.get("evidence"))
        if not evidence and status != "EXTERNAL":
            evidence = [f"Provider: {spec['provider']}", f"Model: {note.get('model') or spec['model']}", f"Env: {spec['env']}"]
        debater_cards.append(trading_agent_card(
            f"debater_{spec['provider']}",
            "核心辩手",
            spec["display"],
            f"{spec['provider']} / {note.get('model') or spec['model']}",
            str(body.get("stance") or "WAIT"),
            pct(body.get("confidence_pct", 55 if status == "EXTERNAL" else 50), 50),
            summary,
            evidence,
            challenges or [spec["role"]],
            _string_list(body.get("agree_with")) or ["TradingAgents 本地结构"],
            status,
            spec["role"],
        ))
        if status == "EXTERNAL":
            local_room["debate"].append({
                "round": "AI聊天室",
                "speaker": spec["display"],
                "message": summary,
                "reply_to": "前序模型发言" if meeting_transcript else "TradingAgents 本地结构",
            })
        else:
            local_room["debate"].append({
                "round": "AI聊天室",
                "speaker": spec["display"],
                "message": summary,
                "reply_to": "等待API配置" if status == "WAIT" else "模型调用错误",
            })

    local_room["agents"] = debater_cards + list(local_room.get("agents") or [])
    return {
        "ok": True,
        "symbol": symbol,
        "bar": bar,
        "status": provider_status,
        "source": "TradingAgents GitHub project structure + Hakimi market snapshot + 4-debater AI room",
        "meeting_id": meeting_id,
        "meeting_mode": "random-role relay chat",
        "role_assignments": role_assignments,
        "project": provider_status.get("project"),
        "safety": "All outputs are observation / research / paper validation only. Live trading is hard-blocked.",
        "agents": local_room["agents"],
        "debate": local_room["debate"],
        "meeting_transcript": meeting_transcript,
        "final": local_room["final"],
        "local": local_room["local"],
        "research": local_room["research"],
        "external_notes": external_notes,
        "updated_at": now_ms(),
    }


def trading_agents_external_discussion(
    payload: dict[str, Any],
    emit_event: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    return trading_agents_external_discussion_v2(payload, emit_event)
def deepseek_opportunity_scan(symbols_text: str = "") -> dict[str, Any]:
    scanner = market_scanner(symbols_text)
    rows = scanner.get("rows", [])[:12]
    context = {
        "task": "从候选币中寻找交易机会，只做研究建议，不直接下单",
        "scanner_summary": scanner.get("summary"),
        "candidates": rows,
        "output_schema": {
            "summary": "一句话总览",
            "market_regime": "牛市/熊市/震荡/不确定",
            "opportunities": [
                {
                    "symbol": "BTC-USDT",
                    "direction": "LONG/SHORT/NEUTRAL",
                    "strategy": "策略名",
                    "confidence_pct": "0-100",
                    "reason": "原因",
                    "risk": "LOW/MEDIUM/HIGH",
                    "entry_hint": "入场观察点",
                    "take_profit_hint": "止盈提示",
                    "stop_loss_hint": "止损提示",
                }
            ],
            "warnings": ["风险提示"],
            "next_check_seconds": "建议下次扫描间隔",
        },
    }
    result = deepseek_chat(
        [
            {"role": "system", "content": deepseek_system_prompt()},
            {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
        ],
        "opportunity_scan",
        1600,
    )
    return {
        "ok": bool(result.get("ok")),
        "status": deepseek_status(),
        "scanner": scanner,
        "deepseek": result,
        "analysis": result.get("json") or {"summary": result.get("content") or result.get("error", "DeepSeek 暂无输出"), "opportunities": []},
        "updated_at": now_ms(),
    }


def platform_snapshot_for_review() -> dict[str, Any]:
    ledger_rows = read_ledger(80)
    paper = PAPER_ACCOUNT.snapshot()
    profile = PROFILE.snapshot()
    return {
        "positioning": "Market research workstation for anomaly detection, trend explanation, AI evidence review and paper-only validation",
        "modules": [
            "real_time_market",
            "contract_center",
            "kline_tools",
            "strategy_engine",
            "paper_execution",
            "risk_center",
            "strategy_lab",
            "backtest_optimizer",
            "market_scanner",
            "market_anomaly_radar",
            "trend_analysis_cockpit",
            "research_panel",
            "guardian_daemon",
            "deepseek_researcher",
            "account_center",
            "export_and_ledger",
        ],
        "data_sources": {
            "okx_realtime": True,
            "local_btc_daily_db": btc_daily_source_available(),
            "rss_news": True,
            "deepseek": deepseek_status(),
        },
        "execution": {
            "paper_only": False,
            "live_trading_enabled": False,
            "order_types": [],
            "direction_modes": ["LONG_ONLY", "SHORT_ONLY"],
            "current_paper": {
                "symbol": paper.get("symbol"),
                "armed": paper.get("armed"),
                "strategy": (paper.get("strategy") or {}).get("name"),
                "direction_mode": paper.get("direction_mode"),
                "margin_mode": paper.get("margin_mode"),
                "order_type": paper.get("order_type"),
                "risk_status": paper.get("risk_status"),
                "position_side": paper.get("position_side"),
            },
        },
        "automation": {
            "guardian": {
                "enabled": (profile.get("guardian") or {}).get("enabled"),
                "status": (profile.get("guardian") or {}).get("status"),
                "refresh_seconds": (profile.get("settings") or {}).get("refresh_seconds"),
            },
            "browser_refresh_intervals": {
                "ticker_ms": 1500,
                "paper_ms": 7000,
                "market_scanner_ms": 30000,
                "market_anomaly_radar_ms": 45000,
                "deepseek_opportunities_ms": 60000,
            },
        },
        "known_boundaries": [
            "live trading deliberately disabled until API permission and kill-switch flow are hardened",
            "backend is currently a single large Python service file",
            "paper futures simulation is approximate and should be separated before real money",
            "DeepSeek can advise but must not bypass risk checks or place orders directly",
        ],
        "risk_engine": risk_engine_snapshot(),
        "recent_events": [{"type": row.get("type"), "time": row.get("time")} for row in ledger_rows[-20:]],
    }


def timed_check(label: str, fn) -> tuple[bool, int, str, Any]:
    start = time.time()
    try:
        payload = fn()
        latency_ms = int((time.time() - start) * 1000)
        return True, latency_ms, "", payload
    except Exception as exc:
        latency_ms = int((time.time() - start) * 1000)
        return False, latency_ms, str(exc), None


def data_reliability_center() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []

    def add_source(
        source_id: str,
        name: str,
        ok: bool,
        latency_ms: int,
        detail: str,
        freshness: str,
        next_action: str,
        warning: str = "",
        weight: float = 1.0,
        required: bool = True,
    ) -> None:
        if required:
            status = "ONLINE" if ok and not warning else "WATCH" if ok else "OFFLINE"
        else:
            status = "AVAILABLE" if ok else "OPTIONAL"
        score = 92 if status == "ONLINE" else 62 if status == "WATCH" else 22
        rows.append({
            "id": source_id,
            "name": name,
            "status": status,
            "score": round(score * weight, 1),
            "required": required,
            "score_included": required,
            "latency_ms": latency_ms,
            "freshness": freshness,
            "detail": detail,
            "warning": warning,
            "next": next_action,
        })

    ok, latency, error, ticker = timed_check(
        "okx_ticker",
        lambda: okx_first("/api/v5/market/ticker", {"instId": "BTC-USDT"}),
    )
    last = pct((ticker or {}).get("last", "0")) if ok else 0.0
    add_source(
        "okx_realtime",
        "OKX 实时行情",
        ok and last > 0,
        latency,
        f"BTC-USDT last={last:.2f}" if last > 0 else "无法读取 BTC-USDT 实时报价",
        "秒级轮询",
        "继续改造成 websocket + 本地缓存双通道",
        error,
    )

    ok, latency, error, page = timed_check(
        "okx_history",
        lambda: okx_rows("/api/v5/market/history-candles", {"instId": "BTC-USDT", "bar": "1Dutc", "limit": "2"}),
    )
    add_source(
        "okx_history",
        "OKX 历史K线",
        ok and bool(page),
        latency,
        f"history candles={len(page or [])}",
        "按需拉取",
        "增加历史补全队列和失败重试",
        error if not page else "",
        0.9,
    )

    ok, latency, error, btc = timed_check("btc_local", lambda: read_local_btc_daily(5))
    btc_rows = (btc or {}).get("rows", []) if ok else []
    add_source(
        "btc_local_daily",
        "BTC 本地日线库",
        ok and bool(btc_rows),
        latency,
        f"{len(btc_rows)} 条样本 · {(btc or {}).get('source', '--')}",
        "本地文件",
        "扩展到 ETH/DOGE/永续合约日线缓存",
        (btc or {}).get("warning", "") if ok else error,
    )

    cache_status = market_history_cache_status()
    cache_ready = len([row for row in cache_status.get("rows", []) if row.get("status") == "READY"])
    cache_total = len(cache_status.get("rows", []))
    cache_complete = cache_ready >= max(cache_total - 1, 1)
    add_source(
        "market_history_cache",
        "通用历史缓存",
        cache_ready > 0,
        0,
        f"READY {cache_ready}/{cache_total} · {Path(cache_status.get('path', '')).name}",
        "本地 SQLite",
        "补全 ETH/DOGE/永续合约日线缓存",
        "" if cache_complete else cache_status.get("summary", ""),
        0.95,
    )

    ok, latency, error, futu = timed_check("futu_status", lambda: futu_status_snapshot(False))
    add_source(
        "futu_opend",
        "富途 OpenD",
        ok and bool((futu or {}).get("opend_online")),
        latency,
        (futu or {}).get("message", "OpenD 未连接") if ok else "OpenD 状态读取失败",
        "5秒缓存",
        "补充股票历史缓存和盘前/盘后数据完整性检查",
        "" if ok and bool((futu or {}).get("opend_online")) else error or (futu or {}).get("message", ""),
    )

    stock_cache_age = now_ms() - int(STOCK_QUOTE_CACHE.get("time") or 0)
    stock_rows = STOCK_QUOTE_CACHE.get("rows", [])
    add_source(
        "stock_quotes",
        "股票报价缓存",
        bool(stock_rows) and stock_cache_age < 120000,
        0,
        f"{len(stock_rows)} 个标的 · cache_age={stock_cache_age // 1000}s",
        "60秒缓存",
        "增加单标的数据延迟灯和缺口报警",
        "" if stock_rows else "等待富途快照刷新",
        0.8,
    )

    deepseek = deepseek_status()
    add_source(
        "deepseek_research",
        "DeepSeek 研究通道",
        bool(deepseek.get("configured")),
        0,
        f"{deepseek.get('model', '--')} · thinking={deepseek.get('thinking')}",
        "按需调用",
        "给 AI 输出增加行情快照引用和冷却时间",
        "" if deepseek.get("configured") else "可选能力未配置，不影响行情数据可靠性",
        0.7,
        required=False,
    )

    source_roles = {
        "okx_realtime": {"mode": "实时", "use_for": "币种报价 / K线 / 异动雷达", "trust": "HIGH", "tone": "up"},
        "okx_history": {"mode": "历史", "use_for": "回看结构 / 回测 / 日线参考", "trust": "HIGH", "tone": "up"},
        "btc_local_daily": {"mode": "本地兜底", "use_for": "BTC长期结构兜底", "trust": "MEDIUM", "tone": "flat"},
        "market_history_cache": {"mode": "本地缓存", "use_for": "断网兜底 / 快速加载", "trust": "MEDIUM", "tone": "flat"},
        "futu_opend": {"mode": "股票实时入口", "use_for": "股票实时 / 盘前盘后 / 深度", "trust": "HIGH", "tone": "up"},
        "stock_quotes": {"mode": "股票报价缓存", "use_for": "股票列表 / 异动雷达", "trust": "MEDIUM", "tone": "flat"},
        "deepseek_research": {"mode": "AI解释", "use_for": "行情解释 / Prompt草稿", "trust": "REVIEW", "tone": "flat"},
    }
    for row in rows:
        role = source_roles.get(str(row.get("id") or ""), {})
        row.update(role)
        if row.get("status") == "OFFLINE":
            row["tone"] = "down"
            row["trust"] = "LOW"
        elif row.get("status") == "WATCH":
            row["tone"] = "flat"
        row["research_label"] = f"{row.get('mode', '数据源')} / {row.get('status', '--')}"

    scored_rows = [row for row in rows if row.get("score_included")]
    if scored_rows:
        score = round(average([float(row["score"]) for row in scored_rows]), 1)
    else:
        score = 0.0
    incidents = [
        {"level": "WARN" if row["status"] == "WATCH" else "ERROR", "source": row["name"], "message": row["warning"] or row["next"]}
        for row in rows
        if row.get("required") and row["status"] != "ONLINE"
    ]
    status_counts = {
        "online": len([row for row in rows if row.get("status") == "ONLINE"]),
        "watch": len([row for row in rows if row.get("status") == "WATCH"]),
        "offline": len([row for row in rows if row.get("status") == "OFFLINE"]),
        "optional": len([row for row in rows if not row.get("required")]),
    }
    by_id = {str(row.get("id") or ""): row for row in rows}
    summary_cards = [
        {
            "label": "币种实时",
            "value": by_id.get("okx_realtime", {}).get("status", "--"),
            "detail": by_id.get("okx_realtime", {}).get("detail", "OKX public market"),
            "tone": by_id.get("okx_realtime", {}).get("tone", "flat"),
        },
        {
            "label": "股票实时",
            "value": by_id.get("futu_opend", {}).get("status", "--"),
            "detail": "Futu在线才允许标记股票实时；Yahoo/Stooq只作延迟研究源。",
            "tone": by_id.get("futu_opend", {}).get("tone", "flat"),
        },
        {
            "label": "本地兜底",
            "value": by_id.get("market_history_cache", {}).get("status", "--"),
            "detail": by_id.get("market_history_cache", {}).get("detail", "local cache"),
            "tone": by_id.get("market_history_cache", {}).get("tone", "flat"),
        },
        {
            "label": "数据体检",
            "value": f"{score}/100",
            "detail": f"ONLINE {status_counts['online']} / WATCH {status_counts['watch']} / OFFLINE {status_counts['offline']}",
            "tone": "up" if score >= 75 else "flat" if score >= 50 else "down",
        },
    ]
    overall_status = "ONLINE" if score >= 75 else "WATCH" if score >= 45 or by_id.get("okx_realtime", {}).get("status") == "ONLINE" else "OFFLINE"
    return {
        "ok": True,
        "score": score,
        "status": overall_status,
        "summary": f"数据可靠性 {score}/100 · 异常 {len(incidents)} 个",
        "rows": rows,
        "cards": summary_cards,
        "status_counts": status_counts,
        "incidents": incidents[:8],
        "updated_at": now_ms(),
    }


def platform_v2_module_catalog(price: float = 0.0) -> list[dict[str, Any]]:
    paper = PAPER_ACCOUNT.snapshot(price)
    profile = PROFILE.snapshot()
    deepseek = deepseek_status()
    btc_db_ready = btc_daily_source_available()
    code_worker_active = len([row for row in read_code_worker_drafts() if row.get("status") != "ARCHIVED"])
    return [
        {
            "id": "market_data",
            "name": "行情数据层",
            "status": "ONLINE",
            "maturity": 79,
            "risk": "MEDIUM",
            "evidence": ["BTC/ETH/DOGE 现货", "BTC/ETH/DOGE 永续", "股票研究列表", f"BTC 日线库 {'READY' if btc_db_ready else 'MISSING'}"],
            "next": "把 OKX 数据缓存和历史回补拆成独立 data_service",
        },
        {
            "id": "contract_center",
            "name": "合约行情中心",
            "status": "ONLINE",
            "maturity": 72,
            "risk": "MEDIUM",
            "evidence": ["现货价/永续价/指数价/标记价", "资金费率", "未平仓量", "基差"],
            "next": "增加多交易所基差对比和资金费率套利观察",
        },
        {
            "id": "market_radar",
            "name": "行情异动雷达与走势驾驶舱",
            "status": "ONLINE",
            "maturity": 70,
            "risk": "LOW",
            "evidence": ["放量/急涨急跌", "突破/跌破", "波动率扩张", "资金费率/OI/基差", "股票/币种联动"],
            "next": "增加本地异动事件库、盘口快照和新闻事件归因",
        },
        {
            "id": "strategy_lab",
            "name": "策略实验室",
            "status": "PARTIAL",
            "maturity": 66,
            "risk": "MEDIUM",
            "evidence": [f"{len(STRATEGIES)} 个策略模板", "策略评分", "回测/寻优入口"],
            "next": "把策略评分、回测和参数寻优拆成独立 strategy_service",
        },
        {
            "id": "paper_execution",
            "name": "模拟执行引擎",
            "status": "ARCHIVED",
            "maturity": 63,
            "risk": "HIGH",
            "evidence": [f"订单类型 {len(ORDER_TYPES)} 种", paper.get("position_side", "FLAT"), paper.get("risk_status", "--")],
            "next": "改为事件驱动撮合队列，单独模拟延迟、滑点、手续费和资金费率",
        },
        {
            "id": "risk_center",
            "name": "风控中心",
            "status": "PROTECTED",
            "maturity": 78,
            "risk": "LOW",
            "evidence": ["实盘硬墙开启", "影子风控", "熔断/急停/守护进程入口"],
            "next": "把 risk_engine 从页面服务拆出，成为所有执行路径前置检查",
        },
        {
            "id": "ai_research",
            "name": "AI 研究与开发助手",
            "status": "ONLINE" if deepseek.get("configured") else "OFFLINE",
            "maturity": 61 if deepseek.get("configured") else 38,
            "risk": "MEDIUM",
            "evidence": [deepseek.get("model", "--"), f"Code Worker 草稿 {code_worker_active} 个", "禁止自动应用补丁"],
            "next": "给 AI 输出增加引用行情快照、审查日志和冷却间隔",
        },
        {
            "id": "guardian_daemon",
            "name": "策略守护进程",
            "status": (profile.get("guardian") or {}).get("status", "STOPPED"),
            "maturity": 58,
            "risk": "MEDIUM",
            "evidence": [f"enabled={(profile.get('guardian') or {}).get('enabled')}", f"cycles={(profile.get('guardian') or {}).get('cycles', 0)}"],
            "next": "升级为独立后台进程，失败后可自动恢复并写入心跳文件",
        },
        {
            "id": "operations",
            "name": "运维与审计",
            "status": "PARTIAL",
            "maturity": 57,
            "risk": "MEDIUM",
            "evidence": ["事件账本", "CSV 导出", "通知中心", "本地配置"],
            "next": "增加系统自检、数据源延迟、错误率和服务重启入口",
        },
    ]


def competitive_redesign_route() -> dict[str, Any]:
    return {
        "status": "ADOPTED",
        "document": "outputs/python_quant_bot/docs/competitive_redesign_2026-07-09.md",
        "summary": "对标 NautilusTrader、Freqtrade、QuantConnect LEAN、Hummingbot、TradingView 和 OpenBB 后，v2 下一阶段聚焦事件驱动、风控前置、研究到模拟一致、数据层解耦。",
        "principles": [
            "专业行情工作台：多图同步、命令搜索、图上策略解释、回放和告警",
            "研究到模拟一致：同一套策略语义贯穿研究、回测、模拟盘和未来实盘",
            "Dry-run 与风控优先：先模拟、先体检、先审计，再考虑执行权限",
            "数据层解耦：OKX、Futu、本地缓存、AI 摘要统一成可追踪数据服务",
        ],
        "source_projects": [
            "NautilusTrader",
            "Freqtrade",
            "QuantConnect LEAN",
            "Hummingbot",
            "TradingView",
            "OpenBB",
        ],
        "next_actions": [
            "建立 research_execution_rehearsal.py，统一纯内存研究撮合、费用、滑点与生命周期证据",
            "扩展 risk_service.py，让人工单、策略单、条件单和守护进程全部先走 pretrade check",
            "新增 market_data_service.py，统一行情来源、新鲜度、缓存和降级说明",
            "把命令面板升级为运行回测、停止买入、风险解释和数据体检的全局入口",
            "补齐 lookahead 检查、浏览器 smoke test 和 AI 草稿测试建议",
        ],
        "safety_boundary": "继续保持实盘硬锁；API 面板只保存环境变量名；DeepSeek 只产出草稿，不接触密钥、不改实盘墙、不新增真实下单路径。",
    }


def platform_v2_overview(price: float = 0.0) -> dict[str, Any]:
    modules = platform_v2_module_catalog(price)
    universe = market_universe()
    risk = risk_engine_snapshot(price)
    data_reliability = data_reliability_center()
    adapters = build_market_adapter_catalog(data_reliability, now_ms=now_ms)
    six_lane = build_six_lane_roadmap(modules, data_reliability, adapters, risk, now_ms=now_ms)
    maturity_score = average([float(item["maturity"]) for item in modules])
    protected_score = 100 if risk.get("live_trading_hard_block") and not risk.get("live_order_allowed") else 35
    data_bonus = 6 if btc_daily_source_available() else 0
    score = round(clamp(maturity_score * 0.74 + protected_score * 0.20 + data_bonus, 0, 100), 1)
    high_risk = [item for item in modules if item.get("risk") == "HIGH"]
    partial = [item for item in modules if item.get("status") in {"PARTIAL", "STOPPED", "OFFLINE"}]
    release_lanes = [
        {
            "lane": "P0 风控与执行硬化",
            "items": ["独立 risk_service", "事件驱动 research execution rehearsal", "全局 kill-switch", "实盘授权双确认"],
            "status": "NEXT",
        },
        {
            "lane": "P1 数据与策略服务拆分",
            "items": ["market_data_service", "strategy_service", "backtest_worker", "历史数据回补队列"],
            "status": "READY_TO_BUILD",
        },
        {
            "lane": "P1 交易所级体验",
            "items": ["多周期布局", "盘口深度统计", "订单生命周期", "持仓风险热区"],
            "status": "IN_PROGRESS",
        },
        {
            "lane": "P2 AI 研究工位",
            "items": ["机会扫描冷却", "AI 结论审计", "Code Worker 草稿审查", "策略解释日志"],
            "status": "IN_PROGRESS",
        },
    ]
    return {
        "ok": True,
        "version": TERMINAL_VERSION,
        "release_name": TERMINAL_RELEASE_NAME,
        "score": score,
        "stage": "V2_FOUNDATION",
        "summary": "v2 重点是把交易终端升级成可审计、可拆分、可守护的量化平台内核。",
        "live_trading": {
            "enabled": False,
            "hard_block": LIVE_TRADING_HARD_BLOCK,
            "order_allowed": False,
            "reason": "v2 阶段继续默认阻断实盘，先完成独立风控与执行服务。",
        },
        "risk_engine": risk,
        "data_reliability": data_reliability,
        "market_adapters": adapters,
        "six_lane": six_lane,
        "competitive_redesign": competitive_redesign_route(),
        "modules": modules,
        "release_lanes": release_lanes,
        "metrics": {
            "module_count": len(modules),
            "market_count": len(universe),
            "stock_count": len([item for item in universe if item.get("type") == "stock"]),
            "swap_count": len([item for item in universe if item.get("type") == "swap"]),
            "high_risk_count": len(high_risk),
            "partial_count": len(partial),
            "strategy_count": len(STRATEGIES),
            "order_type_count": 0,
            "code_worker_drafts": len([row for row in read_code_worker_drafts() if row.get("status") != "ARCHIVED"]),
            "data_reliability_score": data_reliability.get("score"),
            "data_incident_count": len(data_reliability.get("incidents", [])),
            "adapter_online_count": adapters.get("counts", {}).get("online", 0),
            "adapter_offline_count": adapters.get("counts", {}).get("offline", 0),
            "six_lane_score": six_lane.get("score"),
            "six_lane_pass_count": six_lane.get("counts", {}).get("pass", 0),
        },
        "next_batch": [
            "拆出 risk_service.py，让所有下单路径先走统一风控",
            "建立 research_execution_rehearsal.py，把纯内存研究撮合、费用、滑点与资金费率假设独立出来",
            "拆出 market_data_service.py，统一实时行情、历史缓存和数据延迟状态",
            "给策略实验室增加策略运行日志：为什么买、为什么不买、为什么卖",
            "把 v2 控制中心作为系统区主入口，后续所有健康检查都汇总到这里",
        ],
        "updated_at": now_ms(),
    }


def risk_policy_snapshot(price: float = 0.0) -> dict[str, Any]:
    mark_price = price or PAPER_ACCOUNT.entry_price
    paper = PAPER_ACCOUNT.snapshot(mark_price)
    guardian = PROFILE.snapshot().get("guardian", {})
    paper["max_drawdown_pct"] = PAPER_ACCOUNT.max_drawdown_pct
    return build_risk_snapshot(paper, guardian, LIVE_TRADING_HARD_BLOCK, now_ms())


def risk_engine_snapshot(price: float = 0.0) -> dict[str, Any]:
    mark_price = price or PAPER_ACCOUNT.entry_price
    paper = PAPER_ACCOUNT.snapshot(mark_price)
    pipeline_run_id = str(paper.get("pipeline_run_id") or "").strip()
    pipeline_run = STRATEGY_PIPELINE.get(pipeline_run_id) if pipeline_run_id else None
    return build_runtime_risk_view(
        risk_policy_snapshot(mark_price),
        runtime_read_only=RUNTIME_READ_ONLY,
        paper=paper,
        pipeline_run=pipeline_run,
    )


def estimate_paper_notional(price: float, quantity_pct: float, leverage: float | None = None) -> float:
    mark_price = price or PAPER_ACCOUNT.entry_price
    equity = PAPER_ACCOUNT.equity(mark_price)
    return max(equity * clamp(quantity_pct, 1.0, 100.0) / 100 * max(float(leverage or PAPER_ACCOUNT.leverage or 1.0), 1.0), 0.0)


def paper_pretrade_context(price: float, risk_config: dict[str, Any] | None = None, **extra: Any) -> dict[str, Any]:
    risk_config = risk_config or {}
    paper = PAPER_ACCOUNT.snapshot(price or PAPER_ACCOUNT.entry_price)
    ledger = PAPER_LEDGER.summary()
    context = {
        "position_side": paper.get("position_side", "FLAT"),
        "direction_mode": risk_config.get("direction_mode", PAPER_ACCOUNT.direction_mode),
        "reduce_only": risk_config.get("reduce_only", PAPER_ACCOUNT.reduce_only),
        "order_type": risk_config.get("order_type", PAPER_ACCOUNT.order_type),
        "margin_mode": risk_config.get("margin_mode", PAPER_ACCOUNT.margin_mode),
        "leverage": float(extra.get("leverage") or PAPER_ACCOUNT.leverage or 1.0),
        "position_pct": float(extra.get("position_pct") or PAPER_ACCOUNT.position_pct or 0.0),
        "source": "strategy" if PAPER_ACCOUNT.armed else "manual",
        "strategy_id": PAPER_ACCOUNT.strategy_id,
        "run_id": PAPER_ACCOUNT.pipeline_run_id,
        "ledger_reconciliation_required": ledger.get("restart_ready") is not True,
        "ledger_pending_settlements": int(ledger.get("pending_settlement_count") or 0),
    }
    context.update(extra)
    return context


def risk_pretrade_check(symbol: str, side: str, mode: str, notional: float, price: float, context: dict[str, Any] | None = None) -> dict[str, Any]:
    clean_context = build_signal_context(
        context,
        now_ms=now_ms,
        symbol=symbol,
        side=side,
    )
    ledger = PAPER_LEDGER.summary()
    clean_context.setdefault("source", "strategy" if PAPER_ACCOUNT.armed else "manual")
    clean_context.setdefault("strategy_id", PAPER_ACCOUNT.strategy_id)
    clean_context.setdefault("run_id", PAPER_ACCOUNT.pipeline_run_id)
    clean_context["ledger_reconciliation_required"] = ledger.get("restart_ready") is not True
    clean_context["ledger_pending_settlements"] = int(ledger.get("pending_settlement_count") or 0)
    result = RISK_SERVICE.evaluate(
        symbol=symbol,
        side=side,
        mode=mode,
        notional=notional,
        price=price,
        context=clean_context,
    )
    return apply_runtime_pretrade_authorization(
        result,
        runtime_read_only=RUNTIME_READ_ONLY,
    )


def execute_paper_order(
    symbol: str,
    side: str,
    order_type: str,
    mark_price: float,
    notional: float,
    limit_price: float = 0.0,
    risk_result: dict[str, Any] | None = None,
    requested_qty: float = 0.0,
) -> dict[str, Any]:
    risk_context = risk_result.get("context") if isinstance((risk_result or {}).get("context"), dict) else {}
    context = {
        "source": "strategy" if PAPER_ACCOUNT.armed else "manual",
        "strategy_id": PAPER_ACCOUNT.strategy_id,
        "run_id": PAPER_ACCOUNT.pipeline_run_id,
        "market_snapshot_id": risk_context.get("market_snapshot_id"),
        "idempotency_key": risk_context.get("idempotency_key", ""),
    }
    if not risk_result:
        risk_result = risk_pretrade_check(
            symbol,
            side,
            "PAPER",
            notional,
            mark_price,
            paper_pretrade_context(
                mark_price,
                order_type=order_type,
                limit_price=limit_price,
                **context,
            ),
        )
    return PAPER_EXECUTOR.submit(
        symbol=symbol,
        side=side,
        order_type=order_type,
        mark_price=mark_price,
        notional=notional,
        limit_price=limit_price,
        risk_result=risk_result,
        requested_qty=requested_qty,
        context=context,
    )


def record_strategy_paper_snapshot(run_id: str, paper: dict[str, Any]) -> dict[str, Any]:
    enriched = {
        **dict(paper or {}),
        "ledger_metrics": PAPER_LEDGER.run_metrics(run_id),
    }
    return STRATEGY_PIPELINE.record_paper_run(run_id, enriched)


def strategy_pipeline_mutation(payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
    action = str(payload.get("action") or "define")
    if action == "define":
        run = STRATEGY_PIPELINE.define(
            strategy_id=payload.get("strategy_id", "dual_ma"),
            symbol=payload.get("symbol", "BTC-USDT"),
            params=payload.get("params") if isinstance(payload.get("params"), dict) else {},
            research_summary_id=str(payload.get("research_summary_id") or ""),
            code_fingerprint=strategy_implementation_fingerprint(payload.get("strategy_id", "dual_ma")),
        )
    elif action == "authorize-paper":
        return {
            "ok": False,
            "error": "Direct pipeline authorization is disabled; use the paper arm preflight with exact parameter and execution bindings.",
            "paper_authorized": False,
            "live_order_allowed": False,
        }, 422
    elif action == "record-paper":
        run = record_strategy_paper_snapshot(
            str(payload.get("run_id") or ""), PAPER_ACCOUNT.snapshot(pct(payload.get("price", 0)))
        )
    elif action == "audit-review":
        run = STRATEGY_PIPELINE.review_paper_run(
            str(payload.get("run_id") or ""),
            decision=str(payload.get("decision") or ""),
            reviewer=str(payload.get("reviewer") or "local-user"),
            notes=str(payload.get("notes") or ""),
        )
    else:
        return {"ok": False, "error": "unsupported pipeline action", "live_order_allowed": False}, 400
    return {"ok": True, "run": run, "live_order_allowed": False}, 200


def platform_control_center_snapshot(
    price: float = 0.0,
    symbol: str = "",
    bar: str = "",
    session: str = "",
) -> dict[str, Any]:
    def read_only_component(
        component: str,
        loader: Callable[[], Any],
        fallback: Any,
    ) -> Any:
        try:
            return loader()
        except FileNotFoundError:
            if not RUNTIME_READ_ONLY:
                raise
            if isinstance(fallback, dict):
                return {
                    **fallback,
                    "ok": False,
                    "status": "NOT_INITIALIZED",
                    "component": component,
                    "read_only": True,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            return fallback

    paper = PAPER_ACCOUNT.snapshot(price)
    risk = risk_engine_snapshot(price)
    pipeline = read_only_component(
        "strategy_pipeline",
        STRATEGY_PIPELINE.snapshot,
        {"latest": {}, "runs": []},
    )
    active_symbol = str(symbol or paper.get("symbol") or "").strip().upper()
    data_health = market_data_snapshot_health(active_symbol, bar, session)
    market_truth = dict(data_health.get("data_truth") or {})
    data_revision = read_only_component(
        "market_data_revision",
        stock_data_revision_summary,
        {"latest_revision_review_count": 0, "latest_cross_source": []},
    )
    audit = read_only_component(
        "audit_log",
        AUDIT_LOG.summary,
        {"event_count": 0},
    )
    executor = PAPER_EXECUTOR.snapshot()
    paper_ledger = PAPER_LEDGER.summary()
    mutation_journal = read_only_component(
        "mutation_journal",
        MUTATION_JOURNAL.summary,
        {"counts": {}},
    )
    latest_orders = PAPER_EXECUTOR.list(1)
    latest_order = latest_orders[0] if latest_orders else {}
    forward_validation = read_only_component(
        "portfolio_forward",
        portfolio_forward_status_snapshot,
        {
            "scheduler": {"health": "MISSING", "status": "NOT_INITIALIZED"},
            "experiment_registry": {"status": "NOT_INITIALIZED", "experiments": []},
        },
    )
    instrument_rules = PUBLIC_INSTRUMENT_RULES.snapshot(active_symbol)
    public_order_book = PUBLIC_ORDER_BOOK.snapshot(active_symbol)
    plan_observed_at = now_ms()
    small_capital_plan = build_small_capital_trial_plan(
        runtime_read_only=RUNTIME_READ_ONLY,
        live_trading_hard_block=LIVE_TRADING_HARD_BLOCK,
        risk_snapshot=risk,
        market_truth=market_truth,
        forward_validation=forward_validation,
        symbol=active_symbol,
        instrument_rules_evidence=instrument_rules,
        order_book_evidence=public_order_book,
        current_time_ms=plan_observed_at,
        capabilities={},
    )
    recent_audit = read_only_component("audit_log", lambda: AUDIT_LOG.query(limit=16), [])
    return build_platform_control_center_projection(
        runtime_read_only=RUNTIME_READ_ONLY,
        live_trading_hard_block=LIVE_TRADING_HARD_BLOCK,
        effective_paper_authorized=risk.get("paper_authorized") is True,
        default_strategy_id=PAPER_ACCOUNT.strategy_id,
        paper=paper,
        risk=risk,
        pipeline=pipeline,
        executor=executor,
        paper_ledger=paper_ledger,
        mutation_journal=mutation_journal,
        latest_order=latest_order,
        data_health=data_health,
        market_truth=market_truth,
        data_revision=data_revision,
        forward_validation=forward_validation,
        small_capital_plan=small_capital_plan,
        audit=audit,
        recent_audit=recent_audit,
        updated_at=now_ms(),
    )


def config_center_item(
    item_id: str,
    name: str,
    status: str,
    detail: str,
    action: str,
    priority: str = "P1",
    locked: bool = False,
    configured: bool = False,
) -> dict[str, Any]:
    positive = {"READY", "ONLINE", "CONFIGURED", "PROTECTED", "RUNNING", "PASS"}
    negative = {"OFFLINE", "MISSING", "ERROR", "UNSAFE", "BLOCK"}
    score = 100 if status in positive else 40 if status in negative else 68
    if locked and status == "PROTECTED":
        score = 100
    return {
        "id": item_id,
        "name": name,
        "status": status,
        "score": score,
        "detail": detail,
        "action": action,
        "priority": priority,
        "locked": locked,
        "configured": configured,
    }


def full_configuration_snapshot(price: float = 0.0, applied: bool = False) -> dict[str, Any]:
    api_config = api_config_snapshot()
    deepseek = deepseek_status()
    gpt = openai_status()
    profile = PROFILE.snapshot()
    paper = PAPER_ACCOUNT.snapshot(price)
    risk = risk_engine_snapshot(price)
    cache = market_history_cache_status()
    futu = futu_status_snapshot(False)
    saved = api_config.get("saved") or {}
    mapped_env = api_config.get("mapped_env_status") or {}
    mapped_ready = bool(mapped_env.get("api_key") and mapped_env.get("secret") and mapped_env.get("password"))
    cache_rows = cache.get("rows") or []
    cache_ready = len([row for row in cache_rows if row.get("status") == "READY"])
    installed = profile.get("installed_strategy_plugins") or []
    guardian = profile.get("guardian") or {}
    settings = profile.get("settings") or {}
    items = [
        config_center_item(
            "live_wall",
            "实盘硬保护墙",
            "PROTECTED" if LIVE_TRADING_HARD_BLOCK else "UNSAFE",
            "真实下单默认阻断，当前只允许研究、模拟盘和风控预演。" if LIVE_TRADING_HARD_BLOCK else "实盘硬墙被关闭，需要立即复核。",
            "保持开启；未完成审计前不要解除。",
            "P0",
            locked=LIVE_TRADING_HARD_BLOCK,
            configured=LIVE_TRADING_HARD_BLOCK,
        ),
        config_center_item(
            "paper_engine",
            "模拟盘执行",
            "READY",
            f"{paper.get('symbol', '--')} / {paper.get('risk_status', '--')} / {paper.get('direction_mode', '--')}",
            "策略、手动单和守护进程都继续走模拟账户。",
            "P0",
            configured=True,
        ),
        config_center_item(
            "risk_engine",
            "影子风控",
            "READY" if risk.get("live_trading_hard_block") else "WATCH",
            f"预检查={risk.get('pretrade', {}).get('status', '--')} / 急停={guardian.get('status', 'STOPPED')}",
            "所有模拟执行前继续经过统一风险检查。",
            "P0",
            configured=True,
        ),
        config_center_item(
            "deepseek",
            "DeepSeek 初评",
            "CONFIGURED" if deepseek.get("configured") else "MISSING",
            f"{deepseek.get('model', '--')} / thinking={deepseek.get('thinking', '--')}",
            "配置 DEEPSEEK_API_KEY 后可启用低成本第一遍行情分析。",
            "P1",
            configured=bool(deepseek.get("configured")),
        ),
        config_center_item(
            "gpt_review",
            "GPT 复核",
            "CONFIGURED" if gpt.get("configured") else "MISSING",
            f"{gpt.get('model', '--')} / {gpt.get('base_url', '--')}",
            "配置 OPENAI_API_KEY 或 GPT_API_KEY 后可显示第二遍复核。",
            "P1",
            configured=bool(gpt.get("configured")),
        ),
        config_center_item(
            "okx_public",
            "OKX 公共行情",
            "READY",
            "现货、永续、指数价、标记价、资金费率和未平仓量走公开接口。",
            "无需 API Key，继续作为行情主数据源。",
            "P1",
            configured=True,
        ),
        config_center_item(
            "okx_private_mapping",
            "OKX 私有映射",
            "CONFIGURED" if mapped_ready else "OPTIONAL",
            f"{mapped_env.get('api_key_env', 'OKX_API_KEY')} / live=false / mode={saved.get('mode', 'paper')}",
            "只保存环境变量名，不保存密钥；研究阶段可保持未配置。",
            "P2",
            configured=mapped_ready,
        ),
        config_center_item(
            "futu_opend",
            "Futu OpenD 股票数据",
            "ONLINE" if futu.get("opend_online") else "OPTIONAL",
            futu.get("message", "OpenD 未连接"),
            "股票深度数据可选；未连接时使用缓存或离线种子。",
            "P2",
            configured=bool(futu.get("opend_online")),
        ),
        config_center_item(
            "history_cache",
            "历史缓存",
            "READY" if cache_ready >= max(len(cache_rows) - 1, 1) else "WATCH",
            f"READY {cache_ready}/{len(cache_rows)} / {Path(cache.get('path', '')).name}",
            "可在系统页继续补全 ETH/DOGE/永续历史缓存。",
            "P1",
            configured=cache_ready > 0,
        ),
        config_center_item(
            "strategy_plugins",
            "策略模板",
            "READY" if len(installed) >= len(STRATEGIES) else "WATCH",
            f"{len(installed)}/{len(STRATEGIES)} installed / 默认模式 paper",
            "所有策略只进入模拟和研究，不直接实盘。",
            "P1",
            configured=bool(installed),
        ),
        config_center_item(
            "research_station",
            "行情研究工作台",
            "READY",
            "异动雷达 + 走势驾驶舱 + AI行情 + DeepSeek/GPT 双窗口已接入。",
            "从研究页可一键把异动证据链带入 AI行情。",
            "P1",
            configured=True,
        ),
        config_center_item(
            "guardian",
            "后台守护",
            "RUNNING" if guardian.get("enabled") else "STOPPED",
            guardian.get("message", "策略守护未启动"),
            "建议先手动确认策略和风控参数，再启动守护。",
            "P2",
            configured=bool(guardian.get("enabled")),
        ),
    ]
    score = round(average([float(item["score"]) for item in items]), 1) if items else 0.0
    blockers = [item for item in items if item["status"] in {"UNSAFE", "ERROR", "BLOCK"}]
    missing_ai = [item for item in items if item["id"] in {"deepseek", "gpt_review"} and not item["configured"]]
    status = "BLOCKED" if blockers else "READY" if score >= 78 and not missing_ai else "RESEARCH_READY"
    summary = (
        f"全局配置 {score}/100：研究和模拟盘已就绪，实盘仍被硬保护墙锁定。"
        if not blockers else
        f"全局配置 {score}/100：存在 P0 阻断项，需要先恢复安全边界。"
    )
    checklist = [
        {"label": "实盘真实下单", "status": "LOCKED" if LIVE_TRADING_HARD_BLOCK else "UNSAFE", "detail": "保持硬锁，不因配置中心而打开。"},
        {"label": "行情研究", "status": "READY", "detail": "K线、画线、成交量、异动雷达、走势驾驶舱和 AI行情已连通。"},
        {"label": "双 AI 分析", "status": "READY" if deepseek.get("configured") and gpt.get("configured") else "NEEDS_KEY", "detail": "DeepSeek 负责第一遍，GPT 负责第二遍复核；缺 Key 时仍显示本地快照。"},
        {"label": "模拟执行", "status": "READY", "detail": "策略、手动单、条件单和风控预演只写入模拟账户。"},
        {"label": "数据源", "status": "READY" if cache_ready else "WATCH", "detail": "OKX 公共数据可用；股票和历史缓存可继续补全。"},
        {"label": "配置落盘", "status": "READY", "detail": f"本地 runtime 配置目录：{RUNTIME_DIR}"},
    ]
    return {
        "ok": True,
        "applied": applied,
        "score": score,
        "status": status,
        "summary": summary,
        "items": items,
        "checklist": checklist,
        "quick_actions": [
            {"id": "apply_research_preset", "label": "应用研究优先配置"},
            {"id": "open_market_ai", "label": "打开AI行情"},
            {"id": "open_research", "label": "打开研究档案"},
            {"id": "refresh_data", "label": "刷新数据可靠性"},
        ],
        "safe_defaults": {
            "theme": settings.get("theme", "dark"),
            "density": settings.get("density", "compact"),
            "layout": settings.get("layout", "analysis"),
            "refresh_seconds": settings.get("refresh_seconds", 8),
            "start_module": settings.get("start_module", ".research-panel"),
            "live_trading_enabled": False,
            "bot_default_mode": (profile.get("bot_scheduler") or {}).get("default_mode", "paper"),
        },
        "providers": {
            "deepseek": deepseek,
            "gpt": gpt,
            "futu": futu,
            "api": api_config,
        },
        "updated_at": now_ms(),
    }


def apply_full_research_config(price: float = 0.0) -> dict[str, Any]:
    with STATE_LOCK:
        PROFILE.set_settings({
            "theme": "dark",
            "density": "compact",
            "refresh_seconds": 8,
            "start_module": ".research-panel",
            "layout": "analysis",
        })
        PROFILE.set_indicators({
            "ma": True,
            "bollinger": True,
            "volume": True,
            "signals": True,
        })
        PROFILE.installed_strategy_plugins = [strategy["id"] for strategy in STRATEGIES]
        PROFILE.ensure_bot_scheduler()
        PROFILE.bot_scheduler["default_mode"] = "paper"
        PROFILE.bot_scheduler["updated_at"] = now_ms()
        saved = read_json(API_CONFIG_FILE, {})
        saved.update({
            "exchange": saved.get("exchange", "okx"),
            "mode": "paper",
            "api_key_env": saved.get("api_key_env", "OKX_API_KEY"),
            "secret_env": saved.get("secret_env", "OKX_SECRET"),
            "password_env": saved.get("password_env", "OKX_PASSWORD"),
            "updated_at": now_ms(),
            "live_trading_enabled": False,
        })
        write_json(API_CONFIG_FILE, saved)
        PROFILE.notify("INFO", "全局配置", "已应用研究优先配置：深色紧凑、研究雷达优先、全策略模板、模拟盘默认、实盘硬锁保持。")
        PROFILE.persist()
        append_ledger({"type": "full_config_applied", "mode": "research_first", "live_trading_enabled": False})
    return full_configuration_snapshot(price, applied=True)


def deepseek_platform_review() -> dict[str, Any]:
    snapshot = platform_snapshot_for_review()
    compact_snapshot = {
        "positioning": snapshot["positioning"],
        "modules": snapshot["modules"],
        "data_sources": snapshot["data_sources"],
        "execution": snapshot["execution"],
        "automation": snapshot["automation"],
        "known_boundaries": snapshot["known_boundaries"],
    }
    context = {
        "task": "审查这个量化交易平台的整体结构，并给出下一步升级路线。请偏实用，不要空泛。每个字段尽量短，保证输出完整JSON。",
        "platform": compact_snapshot,
        "output_schema": {
            "summary": "一句话总体判断",
            "architecture_score": "0-100",
            "top_priorities": [
                {
                    "area": "模块名称",
                    "priority": "P0/P1/P2",
                    "upgrade": "要升级什么",
                    "reason": "为什么重要",
                    "impact": "HIGH/MEDIUM/LOW",
                    "effort": "S/M/L",
                }
            ],
            "quick_wins": ["短句，最多5条"],
            "refactor_plan": ["短句，最多5条"],
            "safeguards": ["短句，最多5条"],
            "next_build_batch": ["短句，最多5条"],
        },
    }
    result = deepseek_chat(
        [
            {"role": "system", "content": deepseek_system_prompt() + " 这次你还要充当交易平台产品架构师和高级工程审查员。"},
            {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
        ],
        "platform_review",
        3200,
        75,
    )
    parsed = result.get("json") or {"summary": result.get("content") or result.get("error", "DeepSeek 暂无平台审查输出"), "top_priorities": []}
    return {
        "ok": bool(result.get("ok")),
        "status": deepseek_status(),
        "snapshot": compact_snapshot,
        "analysis": parsed,
        "deepseek": result,
        "updated_at": now_ms(),
    }


def code_worker_forbidden_terms() -> list[str]:
    return [
        "DEEPSEEK_API_KEY",
        "OKX_SECRET",
        "OKX_API_KEY",
        "OKX_PASSWORD",
        "sk-",
        "/api/v5/trade/order",
        "LIVE_TRADING_HARD_BLOCK = False",
        "LIVE_TRADING_HARD_BLOCK=false",
        "live_trading_enabled\": true",
        "private_key",
        "secret_key",
    ]


def code_worker_modes() -> dict[str, str]:
    return {
        "draft": "代码草稿",
        "explain": "解释整理",
        "refactor_plan": "重构计划",
        "test_draft": "测试草稿",
    }


def read_code_worker_drafts() -> list[dict[str, Any]]:
    rows = read_json(CODE_WORKER_FILE, [])
    return rows if isinstance(rows, list) else []


def write_code_worker_drafts(rows: list[dict[str, Any]]) -> None:
    write_json(CODE_WORKER_FILE, rows[-30:])


def scan_code_worker_risk(text: str) -> dict[str, Any]:
    value = text or ""
    hits = []
    for term in code_worker_forbidden_terms():
        if term.lower() in value.lower():
            hits.append(term)
    live_terms = [
        "live trading",
        "实盘",
        "下单",
        "自动应用",
        "auto apply",
        "place_order",
        "create_order",
    ]
    live_hits = [term for term in live_terms if term.lower() in value.lower()]
    if hits:
        level = "HIGH"
    elif live_hits:
        level = "MEDIUM"
    else:
        level = "LOW"
    return {
        "level": level,
        "forbidden_hits": hits,
        "live_trading_hits": live_hits,
        "allow_auto_apply": False,
        "requires_codex_review": True,
    }


def code_worker_context(task: str, mode: str) -> dict[str, Any]:
    return {
        "task": task[:1800],
        "mode": mode,
        "project": "Python quant trading robot and OKX-like exchange terminal",
        "repo_root": str(PROJECT_DIR.name),
        "main_files": [
            "exchange_terminal/server.py",
            "exchange_terminal/static/index.html",
            "exchange_terminal/static/app.js",
            "exchange_terminal/static/styles.css",
            "quant_bot/strategies/templates.py",
            "quant_bot/risk.py",
            "quant_bot/execution.py",
            "quant_bot/backtest.py",
        ],
        "hard_rules": [
            "只生成草稿，不要声称已经修改文件",
            "不要输出、猜测、保存或请求任何 API key、secret、password",
            "不要关闭 LIVE_TRADING_HARD_BLOCK",
            "不要添加真实实盘下单逻辑；实盘相关内容必须保持阻断或仅给设计草案",
            "优先给小补丁、清晰文件路径和审查清单",
            "输出必须是 JSON，不要 Markdown",
        ],
        "output_schema": {
            "summary": "一句话说明草稿做什么",
            "risk_level": "LOW/MEDIUM/HIGH",
            "files": [{"path": "相对路径", "intent": "修改意图"}],
            "patch_unified": "统一 diff 草稿；如果只是解释可为空字符串",
            "notes": ["实现说明或限制"],
            "review_checklist": ["Codex 应重点检查什么"],
        },
    }


def deepseek_code_worker(task: str, mode: str = "draft") -> dict[str, Any]:
    clean_task = (task or "").strip()
    clean_mode = mode if mode in code_worker_modes() else "draft"
    if len(clean_task) < 4:
        return {
            "ok": False,
            "error": "任务太短，请给 DeepSeek 一个明确的基础开发任务",
            "status": deepseek_status(),
            "drafts": read_code_worker_drafts(),
        }
    request_risk = scan_code_worker_risk(clean_task)
    context = code_worker_context(clean_task, clean_mode)
    result = deepseek_chat(
        [
            {
                "role": "system",
                "content": (
                    "你是 DeepSeek Code Worker，只负责生成基础代码草稿、解释、测试草案或重构计划。"
                    "你不能接触密钥，不能执行命令，不能自动应用补丁，不能绕过交易风控。"
                    "输出必须是严格 JSON。"
                ),
            },
            {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
        ],
        "code_worker",
        3200,
        75,
    )
    parsed = result.get("json") or {}
    raw = result.get("content") or result.get("error") or ""
    combined = json.dumps(parsed, ensure_ascii=False) + "\n" + raw
    output_risk = scan_code_worker_risk(combined)
    risk_order = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
    risk_level = output_risk["level"] if risk_order[output_risk["level"]] >= risk_order[request_risk["level"]] else request_risk["level"]
    draft = {
        "id": f"cw_{now_ms()}",
        "time": now_ms(),
        "task": clean_task[:500],
        "mode": clean_mode,
        "mode_label": code_worker_modes().get(clean_mode, clean_mode),
        "summary": parsed.get("summary") or ("DeepSeek 已返回草稿" if result.get("ok") else "DeepSeek 草稿生成失败"),
        "risk": {
            "level": parsed.get("risk_level") if parsed.get("risk_level") in {"LOW", "MEDIUM", "HIGH"} else risk_level,
            "request": request_risk,
            "output": output_risk,
            "allow_auto_apply": False,
            "requires_codex_review": True,
        },
        "files": parsed.get("files") if isinstance(parsed.get("files"), list) else [],
        "patch": parsed.get("patch_unified") or "",
        "notes": parsed.get("notes") if isinstance(parsed.get("notes"), list) else ([raw[:1200]] if raw else []),
        "review_checklist": parsed.get("review_checklist") if isinstance(parsed.get("review_checklist"), list) else [],
        "raw": "" if parsed else raw[:6000],
        "status": "DRAFT",
        "deepseek_usage": result.get("usage", {}),
        "deepseek_ok": bool(result.get("ok")),
        "thinking_used": bool(result.get("thinking_used")),
    }
    rows = read_code_worker_drafts()
    rows.append(draft)
    write_code_worker_drafts(rows)
    append_ledger({
        "type": "deepseek_code_worker_draft",
        "mode": clean_mode,
        "risk": draft["risk"]["level"],
        "summary": draft["summary"],
    })
    return {
        "ok": bool(result.get("ok")),
        "status": deepseek_status(),
        "draft": draft,
        "drafts": read_code_worker_drafts(),
        "deepseek": result,
        "updated_at": now_ms(),
    }


def archive_code_worker_draft(draft_id: str) -> dict[str, Any]:
    rows = read_code_worker_drafts()
    found = False
    for row in rows:
        if row.get("id") == draft_id:
            row["status"] = "ARCHIVED"
            row["archived_at"] = now_ms()
            found = True
            break
    if found:
        write_code_worker_drafts(rows)
    return {"ok": found, "drafts": read_code_worker_drafts()}


def read_ledger(limit: int = 120) -> list[dict[str, Any]]:
    return AUDIT_LOG.read(limit)


def read_event_stream(limit: int = 120, event_type: str = "") -> list[dict[str, Any]]:
    return EVENT_BUS.recent(limit, event_type)


def strategy_marketplace() -> list[dict[str, Any]]:
    installed = set(PROFILE.installed_strategy_plugins)
    badges = {
        "dual_ma": ["趋势", "新手友好"],
        "grid": ["震荡", "仓位分层"],
        "bollinger": ["回归", "低吸"],
        "macd": ["动量", "确认信号"],
        "rsi": ["反转", "超买超卖"],
        "momentum": ["突破", "强趋势"],
        "martingale": ["马丁", "高风险"],
        "anti_martingale": ["反马丁", "浮盈加仓"],
        "livermore": ["利弗莫尔", "关键点"],
        "turtle": ["海龟", "通道"],
        "darvas": ["达瓦斯", "箱体"],
    }
    return [
        {
            **strategy,
            "installed": strategy["id"] in installed,
            "badges": badges.get(strategy["id"], []),
            "version": "1.0.0",
        }
        for strategy in STRATEGIES
    ]


def export_orders() -> dict[str, Any]:
    filename = f"paper_orders_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    path = EXPORT_DIR / filename
    columns = ["time", "symbol", "side", "order_type", "price", "quantity", "notional", "pnl", "take_profit", "stop_loss", "reduce_only", "reason"]
    write_csv(path, PAPER_ACCOUNT.orders, columns)
    append_ledger({"type": "export_orders", "path": str(path), "rows": len(PAPER_ACCOUNT.orders)})
    return {"path": str(path), "rows": len(PAPER_ACCOUNT.orders)}


def export_ledger() -> dict[str, Any]:
    rows = read_ledger(5000)
    filename = f"terminal_ledger_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    path = EXPORT_DIR / filename
    flat_rows = [{"time": row.get("time"), "type": row.get("type"), "payload": json.dumps(row, ensure_ascii=False)} for row in rows]
    write_csv(path, flat_rows, ["time", "type", "payload"])
    append_ledger({"type": "export_ledger", "path": str(path), "rows": len(flat_rows)})
    return {"path": str(path), "rows": len(flat_rows)}


def api_config_snapshot() -> dict[str, Any]:
    saved = read_json(API_CONFIG_FILE, {})
    api_key_env = saved.get("api_key_env", "OKX_API_KEY")
    secret_env = saved.get("secret_env", "OKX_SECRET")
    password_env = saved.get("password_env", "OKX_PASSWORD")
    private_read = okx_private_read_status()
    return {
        "saved": saved,
        "env_status": {
            "OKX_API_KEY": bool(os.getenv("OKX_API_KEY")),
            "OKX_SECRET": bool(os.getenv("OKX_SECRET")),
            "OKX_PASSWORD": bool(os.getenv("OKX_PASSWORD")),
        },
        "mapped_env_status": {
            "api_key": bool(os.getenv(api_key_env)) if api_key_env else False,
            "secret": bool(os.getenv(secret_env)) if secret_env else False,
            "password": bool(os.getenv(password_env)) if password_env else False,
            "api_key_env": api_key_env,
            "secret_env": secret_env,
            "password_env": password_env,
        },
        "private_read": private_read,
        "live_enabled": False,
        "message": "当前终端只展示配置状态，真实下单开关仍保持关闭。",
    }


class TerminalProfile:
    def __init__(self) -> None:
        self.assets = {
            "USDT": {"wallet": 10000.0, "trading": 10000.0, "funding": 0.0},
            "BTC": {"wallet": 0.0, "trading": 0.0, "funding": 0.0},
            "ETH": {"wallet": 0.0, "trading": 0.0, "funding": 0.0},
        }
        self.transfers: list[dict[str, Any]] = []
        self.notifications: list[dict[str, Any]] = [
            {"time": now_ms(), "level": "INFO", "title": "终端已准备", "body": "实时行情、模拟盘和历史库已接入。", "read": False}
        ]
        self.guardian = {
            "enabled": False,
            "heartbeat_ms": 0,
            "cycles": 0,
            "status": "STOPPED",
            "message": "策略守护未启动",
            "last_symbol": "",
            "last_price": 0.0,
            "last_action": "WAIT",
            "last_equity": 0.0,
            "last_error": "",
        }
        self.bot_scheduler = {
            "owners": {},
            "default_mode": "paper",
            "updated_at": now_ms(),
        }
        self.indicators = {
            "ma": True,
            "bollinger": False,
            "volume": True,
            "signals": True,
        }
        self.settings = {
            "theme": "dark",
            "density": "compact",
            "refresh_seconds": 8,
            "start_module": ".ticker-header",
            "layout": "classic",
        }
        self.installed_strategy_plugins = [
            "dual_ma",
            "grid",
            "bollinger",
            "macd",
            "rsi",
            "momentum",
            "martingale",
            "anti_martingale",
            "livermore",
            "turtle",
            "darvas",
        ]
        self.shortcuts = {
            "focus_trade": "1",
            "focus_strategy": "2",
            "focus_orders": "3",
            "focus_account": "4",
            "focus_system": "6",
            "toggle_theme": "T",
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "assets": self.assets,
            "transfers": self.transfers,
            "notifications": self.notifications,
            "guardian": self.guardian,
            "bot_scheduler": self.bot_scheduler,
            "indicators": self.indicators,
            "settings": self.settings,
            "installed_strategy_plugins": self.installed_strategy_plugins,
            "shortcuts": self.shortcuts,
        }

    def load(self, payload: dict[str, Any]) -> None:
        for key, value in payload.items():
            if hasattr(self, key):
                setattr(self, key, value)
        available = [strategy["id"] for strategy in STRATEGIES]
        for strategy_id in available:
            if strategy_id not in self.installed_strategy_plugins:
                self.installed_strategy_plugins.append(strategy_id)
        self.ensure_bot_scheduler()

    def persist(self) -> None:
        write_json(PROFILE_FILE, self.to_dict())

    def notify(self, level: str, title: str, body: str) -> None:
        self.notifications.append({
            "time": now_ms(),
            "level": level,
            "title": title,
            "body": body,
            "read": False,
        })
        self.notifications = self.notifications[-120:]
        append_ledger({"type": "notification", "level": level, "title": title, "body": body})
        self.persist()

    def snapshot(self) -> dict[str, Any]:
        unread = sum(1 for item in self.notifications if not item.get("read"))
        return {
            **self.to_dict(),
            "unread_notifications": unread,
        }

    def transfer(self, asset: str, source: str, target: str, amount: float) -> dict[str, Any]:
        asset = asset.upper()
        if asset not in self.assets:
            self.assets[asset] = {"wallet": 0.0, "trading": 0.0, "funding": 0.0}
        amount = max(amount, 0.0)
        source = source if source in self.assets[asset] else "wallet"
        target = target if target in self.assets[asset] else "trading"
        available = float(self.assets[asset].get(source, 0.0))
        moved = min(available, amount)
        self.assets[asset][source] = available - moved
        self.assets[asset][target] = float(self.assets[asset].get(target, 0.0)) + moved
        transfer = {
            "time": now_ms(),
            "asset": asset,
            "source": source,
            "target": target,
            "amount": round(moved, 8),
            "status": "DONE" if moved > 0 else "REJECTED",
        }
        self.transfers.append(transfer)
        self.transfers = self.transfers[-120:]
        self.notify("INFO" if moved > 0 else "WARN", "资产划转", f"{asset} {source} → {target} {moved:.8f}")
        append_ledger({"type": "asset_transfer", "transfer": transfer})
        self.persist()
        return transfer

    def set_guardian(self, enabled: bool) -> None:
        self.guardian["enabled"] = enabled
        self.guardian["status"] = "RUNNING" if enabled else "STOPPED"
        self.guardian["heartbeat_ms"] = now_ms() if enabled else self.guardian.get("heartbeat_ms", 0)
        self.guardian["message"] = "后台自动守护运行中" if enabled else "策略守护已停止"
        self.guardian["last_error"] = ""
        self.notify("INFO", "策略守护", self.guardian["message"])
        self.persist()

    def ensure_bot_scheduler(self) -> None:
        if not isinstance(getattr(self, "bot_scheduler", None), dict):
            self.bot_scheduler = {}
        owners = self.bot_scheduler.get("owners")
        if not isinstance(owners, dict):
            self.bot_scheduler["owners"] = {}
        self.bot_scheduler.setdefault("default_mode", "paper")
        self.bot_scheduler.setdefault("updated_at", now_ms())

    def bot_scheduler_for(self, symbol: str, preferred: list[str] | None = None) -> dict[str, Any]:
        self.ensure_bot_scheduler()
        clean_symbol = (symbol or "BTC-USDT").upper()
        preferred = preferred or []
        owners = self.bot_scheduler["owners"]
        owner = owners.get(clean_symbol)
        if not isinstance(owner, dict) or not owner.get("bot_id"):
            bot_id = default_bot_owner(clean_symbol, preferred)
            owner = {
                "bot_id": bot_id,
                "mode": self.bot_scheduler.get("default_mode", "paper"),
                "source": "auto",
                "updated_at": now_ms(),
            }
            owners[clean_symbol] = owner
            self.bot_scheduler["updated_at"] = owner["updated_at"]
            self.persist()
        return {
            "symbol": clean_symbol,
            "active_bot": owner.get("bot_id", ""),
            "mode": owner.get("mode", self.bot_scheduler.get("default_mode", "paper")),
            "source": owner.get("source", "auto"),
            "preferred": preferred,
            "updated_at": owner.get("updated_at", self.bot_scheduler.get("updated_at", now_ms())),
        }

    def assign_bot_owner(self, symbol: str, bot_id: str, mode: str = "paper") -> None:
        self.ensure_bot_scheduler()
        clean_symbol = (symbol or "BTC-USDT").upper()
        clean_mode = mode if mode in {"paper", "forward", "live"} else "paper"
        self.bot_scheduler["owners"][clean_symbol] = {
            "bot_id": bot_id,
            "mode": clean_mode,
            "source": "manual",
            "updated_at": now_ms(),
        }
        self.bot_scheduler["updated_at"] = self.bot_scheduler["owners"][clean_symbol]["updated_at"]
        self.persist()

    def release_bot_owner(self, symbol: str) -> None:
        self.ensure_bot_scheduler()
        clean_symbol = (symbol or "BTC-USDT").upper()
        self.bot_scheduler["owners"].pop(clean_symbol, None)
        self.bot_scheduler["updated_at"] = now_ms()
        self.persist()

    def heartbeat(self) -> None:
        if not self.guardian.get("enabled"):
            return
        self.guardian["heartbeat_ms"] = now_ms()
        self.guardian["cycles"] = int(self.guardian.get("cycles", 0)) + 1
        self.guardian["status"] = "RUNNING"
        self.guardian["message"] = f"已完成 {self.guardian['cycles']} 次策略巡检"
        self.persist()

    def set_indicators(self, values: dict[str, bool]) -> None:
        self.indicators.update(values)
        append_ledger({"type": "indicator_config", "indicators": self.indicators})
        self.persist()

    def set_settings(self, values: dict[str, Any]) -> None:
        self.settings.update(values)
        legacy_theme = {"warm": "dark", "midnight": "blue", "contrast": "light"}.get(self.settings.get("theme"))
        if legacy_theme:
            self.settings["theme"] = legacy_theme
        if self.settings.get("theme") not in {"dark", "blue", "light"}:
            self.settings["theme"] = "dark"
        if self.settings.get("density") not in {"compact", "standard"}:
            self.settings["density"] = "compact"
        if self.settings.get("layout") not in {"classic", "focus", "analysis"}:
            self.settings["layout"] = "classic"
        try:
            self.settings["refresh_seconds"] = max(3, min(int(self.settings.get("refresh_seconds", 8)), 60))
        except Exception:
            self.settings["refresh_seconds"] = 8
        append_ledger({"type": "terminal_settings", "settings": self.settings})
        self.notify("INFO", "系统设置", "终端设置已保存")
        self.persist()

    def set_layout(self, layout: str) -> None:
        if layout not in {"classic", "focus", "analysis"}:
            layout = "classic"
        self.settings["layout"] = layout
        append_ledger({"type": "layout_changed", "layout": layout})
        self.persist()

    def install_strategy(self, strategy_id: str) -> None:
        available = {strategy["id"] for strategy in STRATEGIES}
        if strategy_id in available and strategy_id not in self.installed_strategy_plugins:
            self.installed_strategy_plugins.append(strategy_id)
            self.notify("INFO", "策略市场", f"已安装策略 {choose_strategy(strategy_id)['name']}")
            self.persist()

    def uninstall_strategy(self, strategy_id: str) -> None:
        if strategy_id in self.installed_strategy_plugins and len(self.installed_strategy_plugins) > 1:
            self.installed_strategy_plugins = [item for item in self.installed_strategy_plugins if item != strategy_id]
            self.notify("INFO", "策略市场", f"已移除策略 {choose_strategy(strategy_id)['name']}")
            self.persist()

    def mark_notifications_read(self) -> None:
        for notification in self.notifications:
            notification["read"] = True
        self.persist()


PROFILE = TerminalProfile()
PROFILE.load(read_json(PROFILE_FILE, {}))


GUARDIAN_SERVICE = GuardianService(
    profile=PROFILE,
    account=PAPER_ACCOUNT,
    state_lock=STATE_LOCK,
    okx_first=okx_first,
    pct=pct,
    now_ms=now_ms,
    append_ledger=append_ledger,
    risk_pretrade_check=lambda *args, **kwargs: risk_pretrade_check(*args, **kwargs),
    estimate_paper_notional=estimate_paper_notional,
    paper_pretrade_context=paper_pretrade_context,
    market_reader=paper_market_cycle_snapshot,
)


def guardian_interval_seconds() -> int:
    return GUARDIAN_SERVICE.interval_seconds()


def guardian_emergency_stop(price: float = 0.0, reason: str = "风控急停", source: str = "manual") -> dict[str, Any]:
    result = GUARDIAN_SERVICE.emergency_stop(price, reason, source)
    paper = result.get("paper") if isinstance(result.get("paper"), dict) else {}
    emergency = paper.get("emergency_stop") if isinstance(paper.get("emergency_stop"), dict) else {}
    pipeline_run_id = str(emergency.get("pipeline_run_id") or "")
    if pipeline_run_id:
        result["pipeline_run"] = record_strategy_paper_snapshot(pipeline_run_id, paper)
    return result


def guardian_circuit_reason(paper: dict[str, Any], price: float) -> str:
    return GUARDIAN_SERVICE.circuit_reason(paper, price)


def run_guardian_cycle(source: str = "daemon") -> dict[str, Any]:
    return GUARDIAN_SERVICE.run_cycle(source)


def guardian_worker() -> None:
    GUARDIAN_SERVICE.worker()


def start_guardian_worker() -> None:
    GUARDIAN_SERVICE.start_worker()


def stop_guardian_worker() -> None:
    GUARDIAN_SERVICE.stop_worker()


def safe_static_path(request_path: str) -> Path | None:
    if request_path == "/":
        request_path = "/index.html"
    relative = request_path.lstrip("/")
    target = (STATIC_DIR / relative).resolve()
    try:
        target.relative_to(STATIC_DIR.resolve())
    except ValueError:
        return None
    return target


class ExchangeTerminalHandler(BaseHTTPRequestHandler):
    server_version = "PythonQuantExchangeTerminal/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} - {fmt % args}")

    def do_OPTIONS(self) -> None:
        origin = allowed_cors_origin(self)
        if self.headers.get("Origin") and not origin:
            self.send_response(403)
            self.end_headers()
            return
        self.send_response(204)
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Hakimi-Write, Idempotency-Key")
        self.end_headers()

    def do_GET(self) -> None:
        if block_non_loopback_client(self):
            return
        parsed = urllib.parse.urlparse(self.path)
        query = {key: values[-1] for key, values in urllib.parse.parse_qs(parsed.query).items()}
        if parsed.path.startswith("/api/"):
            if parsed.path in RETIRED_MANAGEMENT_PATHS:
                json_response(self, {"ok": False, "error": "not found"}, 404)
                return
            if not trusted_refresh_get_allowed(
                parsed.path,
                query,
                client_host=self.client_address[0],
                origin=self.headers.get("Origin"),
                sec_fetch_site=self.headers.get("Sec-Fetch-Site"),
            ):
                json_response(self, {
                    "ok": False,
                    "error": "force/emit GET requires a trusted local client and origin",
                    "live_order_allowed": False,
                }, 403)
                return
            if RUNTIME_READ_ONLY and read_only_get_mutation_requested(parsed.path, query):
                json_response(self, {
                    "ok": False,
                    "error": "runtime is read-only",
                    "read_only": True,
                    "live_order_allowed": False,
                }, 423)
                return
            if parsed.path in MUTATION_PATHS and parsed.path not in READABLE_MUTATION_PATHS:
                json_response(self, {
                    "ok": False,
                    "error": "state-changing endpoint requires POST",
                    "required_method": "POST",
                }, 405)
                return
            self.handle_api(parsed.path, query)
            return
        self.handle_static(parsed.path)

    def do_POST(self) -> None:
        if block_non_loopback_client(self):
            return
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path not in POST_API_PATHS | MUTATION_PATHS:
            json_response(self, {"ok": False, "error": "not found"}, 404)
            return
        if RUNTIME_READ_ONLY:
            json_response(self, {
                "ok": False,
                "error": "runtime is read-only",
                "read_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }, 423)
            return
        origin = str(self.headers.get("Origin") or "").strip()
        if origin and not allowed_cors_origin(self):
            json_response(self, {"ok": False, "error": "origin not allowed"}, 403)
            return
        if parsed.path in MUTATION_PATHS and self.headers.get("X-Hakimi-Write") != "1":
            json_response(self, {"ok": False, "error": "missing local write header"}, 403)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            max_length = 180000 if parsed.path in {"/api/ai/market/dual-analysis", "/api/ai/trading-agents/discuss"} else 120000 if parsed.path == "/api/integration/trading-analysis/research-summaries" else 20000 if parsed.path == "/api/strategy/pipeline" or parsed.path in MUTATION_PATHS else 12000 if parsed.path.startswith("/api/ai/runtime-keys") else 4096
            if length < 0 or length > max_length:
                json_response(self, {"ok": False, "error": "invalid request size"}, 400)
                return
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            payload = json.loads(raw or "{}")
            if not isinstance(payload, dict):
                json_response(self, {"ok": False, "error": "JSON object required"}, 400)
                return
            if parsed.path in MUTATION_PATHS:
                header_key = str(self.headers.get("Idempotency-Key") or "").strip()
                body_key = str(payload.get("idempotencyKey") or "").strip()
                if header_key and body_key and header_key != body_key:
                    json_response(self, {"ok": False, "error": "idempotency header/body mismatch"}, 400)
                    return
                idempotency_key = header_key or body_key
                if not idempotency_key:
                    json_response(self, {"ok": False, "error": "Idempotency-Key is required for mutations"}, 400)
                    return
                payload["idempotencyKey"] = idempotency_key
                journal = MUTATION_JOURNAL.begin(parsed.path, idempotency_key, payload)
                if journal.get("status") == "REPLAY":
                    json_response(self, journal.get("response") or {}, int(journal.get("http_status") or 200))
                    return
                if journal.get("status") in {"INVALID", "CONFLICT", "IN_PROGRESS"}:
                    json_response(self, {"ok": False, "error": journal.get("error"), "idempotency_status": journal.get("status")}, 409)
                    return
                self._mutation_idempotency_key = idempotency_key
                if parsed.path == "/api/strategy/pipeline":
                    result, status = strategy_pipeline_mutation(payload)
                    json_response(self, result, status)
                    return
                query = payload_to_query(payload)
                self.handle_api(parsed.path, query)
                return
            if parsed.path == "/api/futu/configure":
                json_response(self, configure_futu_opend_credentials(
                    payload.get("account", ""),
                    payload.get("password", ""),
                ))
                return
            if parsed.path == "/api/stocks/data-audit":
                json_response(self, audit_stock_daily_sources(
                    payload.get("symbol", "AAPL"),
                    int(clamp(pct(payload.get("limit", 1600)), 120, 2000)),
                ))
                return
            if parsed.path == "/api/futu/verify-code":
                json_response(self, submit_futu_phone_verify_code(payload.get("code", "")))
                return
            if parsed.path == "/api/futu/enable-telnet":
                json_response(self, ensure_futu_telnet_config())
                return
            if parsed.path == "/api/ai/market/dual-analysis":
                json_response(self, build_market_ai_projection(market_dual_ai_analysis(payload)))
                return
            if parsed.path == "/api/ai/runtime-keys":
                json_response(self, set_runtime_ai_keys(payload))
                return
            if parsed.path == "/api/ai/runtime-keys/clear":
                json_response(self, clear_runtime_ai_keys(payload))
                return
            if parsed.path == "/api/integration/trading-analysis/research-summaries":
                result = RESEARCH_BRIDGE.import_summary(payload)
                response_status = (
                    200
                    if result.get("ok")
                    else 409
                    if result.get("status") == "IDEMPOTENCY_CONFLICT"
                    else 400
                )
                json_response(self, result, response_status)
                return
            if parsed.path == "/api/ai/trading-agents/discuss":
                if payload.get("stream"):
                    self.send_response(200)
                    self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Connection", "close")
                    self.end_headers()

                    def emit_event(event: dict[str, Any]) -> None:
                        projected_event = project_trading_agents_event(event)
                        line = json.dumps(projected_event, ensure_ascii=False, separators=(",", ":")) + "\n"
                        self.wfile.write(line.encode("utf-8"))
                        self.wfile.flush()

                    try:
                        result = trading_agents_external_discussion(payload, emit_event)
                        emit_event({"type": "complete", "data": result})
                    except CLIENT_DISCONNECT_ERRORS:
                        pass
                    except Exception as stream_exc:
                        try:
                            emit_event({"type": "error", "error": str(stream_exc)})
                        except CLIENT_DISCONNECT_ERRORS:
                            pass
                    self.close_connection = True
                    return
                json_response(self, build_trading_agents_projection(trading_agents_external_discussion(payload)))
                return
        except Exception as exc:
            json_response(self, {"ok": False, "error": str(exc)}, 500)

    def handle_api(self, path: str, query: dict[str, str]) -> None:
        if path in RETIRED_MANAGEMENT_PATHS:
            json_response(self, {"ok": False, "error": "not found"}, 404)
            return
        try:
            archived_route_state = archived_execution_route_state(
                str(getattr(self, "command", "GET")), path
            )
            if archived_route_state == "BLOCK":
                json_response(
                    self,
                    build_research_disabled_response({
                        "status": "ARCHIVED",
                        "armed": False,
                        "read_only": True,
                        "paper_authorized": False,
                        "live_order_allowed": False,
                    }),
                    423,
                )
                return
            if path == "/api/health":
                runtime_build = RUNTIME_BUILD_GUARD.snapshot()
                paper = PAPER_ACCOUNT.snapshot(0.0)
                runtime_build = {
                    "time": int(time.time() * 1000),
                    **runtime_build,
                }
                json_response(
                    self,
                    build_health_response_from_runtime(
                        runtime_build,
                        paper,
                        read_only=RUNTIME_READ_ONLY,
                        runtime_mutations_allowed=not RUNTIME_READ_ONLY,
                        live_trading_hard_block=LIVE_TRADING_HARD_BLOCK is True,
                        guardian_worker_running=bool(GUARDIAN_SERVICE.thread and GUARDIAN_SERVICE.thread.is_alive()),
                    ),
                )
                return
            if path == "/api/platform/control-center":
                json_response(self, platform_control_center_snapshot(
                    pct(query.get("price", "0")),
                    query.get("symbol", ""),
                    query.get("bar", ""),
                    query.get("session", ""),
                ))
                return
            if path == "/api/strategy/pipeline":
                json_response(self, STRATEGY_PIPELINE.snapshot())
                return
            if path == "/api/strategy/backtest/artifact":
                artifact = STRATEGY_PIPELINE.get_backtest_artifact(query.get("runId", ""))
                json_response(
                    self,
                    {"ok": bool(artifact), "artifact": artifact},
                    200 if artifact else 404,
                )
                return
            if path == "/api/audit/events":
                json_response(self, {
                    "ok": True,
                    "events": AUDIT_LOG.query(
                        limit=int(query.get("limit", "120")),
                        event_type=query.get("type", ""),
                        run_id=query.get("runId", ""),
                        symbol=query.get("symbol", ""),
                    ),
                })
                return
            if path == "/api/audit/summary":
                json_response(self, AUDIT_LOG.summary())
                return
            if path == "/api/replay/order":
                result = EVENT_REPLAY.replay_order(query.get("orderId", ""))
                json_response(self, result, 200 if result.get("status") != "NOT_FOUND" else 404)
                return
            if path == "/api/replay/run":
                json_response(self, EVENT_REPLAY.replay_run(query.get("runId", ""), int(query.get("limit", "500"))))
                return
            if path == "/api/paper/orders/lifecycle":
                json_response(self, {"ok": True, "orders": PAPER_EXECUTOR.list(int(query.get("limit", "100"))), "executor": PAPER_EXECUTOR.snapshot()})
                return
            if path == "/api/paper/ledger":
                json_response(self, {
                    "ok": True,
                    "ledger": PAPER_LEDGER.summary(),
                    "paper": PAPER_ACCOUNT.snapshot(pct(query.get("price", "0"))),
                    "live_order_allowed": False,
                })
                return
            if path == "/api/paper/portfolio":
                json_response(self, {
                    "ok": True,
                    "portfolio": PORTFOLIO_PAPER_LEDGER.summary(),
                    "forward_validation": portfolio_forward_status_snapshot(),
                    "read_only": True,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                })
                return
            if path == "/api/portfolio/forward":
                json_response(self, {
                    "ok": True,
                    "forward_validation": portfolio_forward_status_snapshot(),
                    "read_only": True,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                })
                return
            if path == "/api/portfolio/backtest-return-quality":
                json_response(
                    self,
                    load_portfolio_backtest_return_quality_snapshot(Path(RUNTIME_DIR) / "reports"),
                )
                return
            if path == "/api/research/portfolio/experiments":
                try:
                    experiment_limit = int(query.get("limit", "10"))
                except (TypeError, ValueError):
                    experiment_limit = 10
                json_response(self, {
                    "ok": True,
                    "experiment_registry": PORTFOLIO_EXPERIMENTS.summary(experiment_limit),
                    "read_only": True,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                })
                return
            if path == "/api/integration/trading-analysis/context":
                symbol = query.get("symbol", PAPER_ACCOUNT.symbol)
                bar = query.get("bar", "1Dutc")
                contract = RESEARCH_BRIDGE.schema()
                market = market_data_snapshot(
                    symbol,
                    bar=bar,
                    limit=int(query.get("limit", "300")),
                    consumer="trading_analysis_bridge",
                )
                research_summaries = RESEARCH_BRIDGE.list(
                    symbol,
                    int(query.get("summaryLimit", "10")),
                )
                json_response(self, build_research_context_projection(
                    contract=contract,
                    market=market,
                    research_summaries=research_summaries,
                ))
                return
            if path == "/api/integration/trading-analysis/research-summaries":
                schema = RESEARCH_BRIDGE.schema()
                summaries = RESEARCH_BRIDGE.list(
                    query.get("symbol", ""),
                    int(query.get("limit", "30")),
                )
                json_response(self, build_research_summaries_projection(
                    schema=schema,
                    summaries=summaries,
                ))
                return
            if path == "/api/strategies":
                json_response(self, {
                    "ok": True,
                    "strategies": [
                        {
                            **strategy,
                            "validation": strategy_validation_capability(strategy["id"]),
                            "research_risk_profile": strategy_research_risk_profile(strategy["id"], {
                                "position_pct": 20.0,
                                "take_profit_pct": 8.0,
                                "stop_loss_pct": 4.0,
                                "fee_rate": 0.0005,
                                "slippage_bps": 2.0,
                            }),
                        }
                        for strategy in STRATEGIES
                    ],
                })
                return
            if path == "/api/strategy/leaderboard":
                json_response(self, {"ok": True, "leaderboard": strategy_leaderboard(int(query.get("limit", "240")))})
                return
            if path == "/api/strategy/marketplace":
                json_response(self, {"ok": True, "strategies": strategy_marketplace()})
                return
            if path == "/api/strategy/analyze":
                price = pct(query.get("price", "0"))
                risk_config = build_risk_config(query, price)
                analysis = analyze_strategy_context(
                    query.get("strategy", "dual_ma"),
                    query.get("symbol", "BTC-USDT"),
                    price,
                    float(risk_config.get("manual_take_profit") or 0.0),
                    float(risk_config.get("manual_stop_loss") or 0.0),
                    risk_config.get("analysis_direction", "LONG"),
                )
                analysis["risk_config"] = risk_config
                json_response(self, build_strategy_analysis_projection({"ok": True, "analysis": analysis}))
                return
            if path == "/api/strategy/lab":
                json_response(self, build_strategy_lab_projection(
                    strategy_lab(
                        query.get("symbol", "BTC-USDT"),
                        query.get("strategy", "dual_ma"),
                        pct(query.get("price", "0")),
                    )
                ))
                return
            if path == "/api/strategy/research-evidence":
                json_response(
                    self,
                    load_strategy_research_evidence_snapshot(
                        Path(RUNTIME_DIR) / "reports",
                        strategy_id=query.get("strategy", "dual_ma"),
                        implementation_fingerprint_fn=strategy_implementation_fingerprint,
                        observed_at_ms=now_ms(),
                    ),
                )
                return
            if path == "/api/strategy/war-room":
                price = pct(query.get("price", "0"))
                risk_config = build_risk_config(query, price)
                risk_config["leverage"] = clamp(pct(query.get("leverage", "1")), 1, 125)
                risk_config["position_pct"] = clamp(pct(query.get("positionPct", "25")), 1, 100)
                json_response(self, build_strategy_war_room_projection(
                    strategy_war_room(
                        query.get("symbol", "BTC-USDT"),
                        query.get("strategy", "dual_ma"),
                        price,
                        risk_config,
                    )
                ))
                return
            if path == "/api/strategy/backtest/preview":
                try:
                    report = strategy_backtest_report(query)
                except ValueError as exc:
                    json_response(self, build_strategy_backtest_preview_error(exc), 422)
                    return
                json_response(self, build_strategy_backtest_preview_projection(report))
                return
            if path == "/api/strategy/backtest":
                try:
                    mutation_key = str(getattr(self, "_mutation_idempotency_key", "") or "")
                    lineage_digest = hashlib.sha256(
                        f"/api/strategy/backtest:{mutation_key}".encode("utf-8")
                    ).hexdigest()[:32]
                    report = strategy_backtest_report(
                        query,
                        dataset_lineage_id=f"strategy-backtest:{lineage_digest}" if mutation_key else "",
                    )
                except ValueError as exc:
                    json_response(self, {
                        "ok": False,
                        "error": str(exc),
                        "live_order_allowed": False,
                    }, 422)
                    return
                reproducibility = report.get("reproducibility") if isinstance(report.get("reproducibility"), dict) else {}
                run = STRATEGY_PIPELINE.define(
                    strategy_id=query.get("strategy", "dual_ma"),
                    symbol=query.get("symbol", "BTC-USDT"),
                    params=reproducibility.get("params") or {},
                    code_fingerprint=strategy_implementation_fingerprint(query.get("strategy", "dual_ma")),
                )
                run = STRATEGY_PIPELINE.record_backtest(run["run_id"], report)
                report["preview"] = False
                report["pipeline_run"] = run
                json_response(self, report)
                return
            if path == "/api/strategy/compare":
                json_response(self, build_strategy_compare_projection(
                    strategy_compare(
                        query.get("symbol", "BTC-USDT"),
                        pct(query.get("price", "0")),
                    )
                ))
                return
            if path in {"/api/strategy/doctor", "/api/strategy/doctor/preview"}:
                symbol = query.get("symbol", "BTC-USDT")
                strategy_id = query.get("strategy", "dual_ma")
                report = strategy_doctor(
                    symbol,
                    strategy_id,
                    pct(query.get("price", "0")),
                    query.get("directionMode", "LONG_ONLY"),
                )
                run = STRATEGY_PIPELINE.latest(symbol, strategy_id)
                if path == "/api/strategy/doctor":
                    if not run or not run.get("strategy_version_id"):
                        run = STRATEGY_PIPELINE.define(
                            strategy_id=strategy_id,
                            symbol=symbol,
                            code_fingerprint=strategy_implementation_fingerprint(strategy_id),
                        )
                    run = STRATEGY_PIPELINE.record_doctor(run["run_id"], report)
                    report["preview"] = False
                else:
                    report["preview"] = True
                report["pipeline_run"] = run
                json_response(self, build_strategy_doctor_projection(report))
                return
            if path == "/api/strategy/robot-profiles":
                json_response(self, build_strategy_robot_profiles_projection(
                    strategy_robot_profiles(
                        query.get("symbol", "BTC-USDT"),
                        pct(query.get("price", "0")),
                    )
                ))
                return
            if path == "/api/bot/center":
                json_response(self, build_bot_center_projection(
                    bot_center(
                        query.get("symbol", "BTC-USDT"),
                        pct(query.get("price", "0")),
                    )
                ))
                return
            if path == "/api/bot/scheduler":
                json_response(self, build_bot_scheduler_projection(
                    bot_scheduler_snapshot(
                        query.get("symbol", "BTC-USDT"),
                        pct(query.get("price", "0")),
                    )
                ))
                return
            if path == "/api/bot/assign":
                json_response(build_bot_scheduler_result_projection(
                    bot_scheduler_assign(
                        query.get("symbol", "BTC-USDT"),
                        query.get("botId", "trend_follower"),
                        query.get("mode", "paper"),
                    )
                ))
                return
            if path == "/api/bot/release":
                json_response(build_bot_scheduler_result_projection(
                    bot_scheduler_release(query.get("symbol", "BTC-USDT"))
                ))
                return
            if path == "/api/strategy/install":
                PROFILE.install_strategy(query.get("id", ""))
                json_response(self, {"ok": True, "profile": PROFILE.snapshot(), "strategies": strategy_marketplace()})
                return
            if path == "/api/strategy/uninstall":
                PROFILE.uninstall_strategy(query.get("id", ""))
                json_response(self, {"ok": True, "profile": PROFILE.snapshot(), "strategies": strategy_marketplace()})
                return
            if path == "/api/ledger":
                json_response(self, {"ok": True, "ledger": read_ledger(int(query.get("limit", "120")))})
                return
            if path == "/api/events":
                json_response(self, {
                    "ok": True,
                    "events": read_event_stream(
                        int(query.get("limit", "120")),
                        query.get("type", ""),
                    ),
                })
                return
            if path == "/api/risk/engine":
                json_response(self, risk_engine_snapshot(pct(query.get("price", "0"))))
                return
            if path == "/api/risk/pretrade":
                price = pct(query.get("price", "0"))
                reduce_only = PAPER_ACCOUNT.reduce_only if "reduceOnly" not in query else flag(query.get("reduceOnly"))
                context = {
                    "position_side": query.get("positionSide") or PAPER_ACCOUNT.snapshot(price).get("position_side", "FLAT"),
                    "direction_mode": query.get("directionMode", PAPER_ACCOUNT.direction_mode),
                    "reduce_only": reduce_only,
                    "order_type": query.get("orderType", PAPER_ACCOUNT.order_type),
                    "margin_mode": query.get("marginMode", PAPER_ACCOUNT.margin_mode),
                    "leverage": pct(query.get("leverage", str(PAPER_ACCOUNT.leverage)), PAPER_ACCOUNT.leverage),
                    "position_pct": pct(query.get("positionPct", str(PAPER_ACCOUNT.position_pct)), PAPER_ACCOUNT.position_pct),
                    "audit_event": False,
                }
                json_response(self, risk_pretrade_check(
                    query.get("symbol", PAPER_ACCOUNT.symbol),
                    query.get("side", "BUY"),
                    query.get("mode", "PAPER"),
                    pct(query.get("notional", "0")),
                    price,
                    context,
                ))
                return
            if path == "/api/export/orders":
                json_response(self, {"ok": True, "export": export_orders()})
                return
            if path == "/api/export/ledger":
                json_response(self, {"ok": True, "export": export_ledger()})
                return
            if path == "/api/config/api":
                json_response(self, {"ok": True, "config": api_config_snapshot()})
                return
            if path == "/api/config/full":
                json_response(self, build_full_configuration_projection(
                    full_configuration_snapshot(pct(query.get("price", "0")))
                ))
                return
            if path == "/api/config/full/apply":
                json_response(self, build_full_configuration_projection(
                    apply_full_research_config(pct(query.get("price", "0")))
                ))
                return
            if path == "/api/ai/deepseek/status":
                json_response(self, {"ok": True, "status": deepseek_status()})
                return
            if path == "/api/ai/trading-agents/status":
                json_response(self, trading_agents_provider_status())
                return
            if path == "/api/ai/runtime-keys/status":
                json_response(self, runtime_ai_key_status())
                return
            if path == "/api/ai/deepseek/analyze":
                price = pct(query.get("price", "0"))
                risk_config = build_risk_config(query, price)
                json_response(self, build_deepseek_projection(deepseek_strategy_analysis(
                    query.get("symbol", "BTC-USDT"),
                    query.get("strategy", "dual_ma"),
                    price,
                    risk_config,
                )))
                return
            if path == "/api/ai/deepseek/opportunities":
                json_response(self, build_deepseek_projection(deepseek_opportunity_scan(query.get("symbols", ""))))
                return
            if path == "/api/ai/deepseek/platform-review":
                json_response(self, build_deepseek_projection(deepseek_platform_review()))
                return
            if path == "/api/ai/deepseek/code-worker/drafts":
                json_response(self, {
                    "ok": True,
                    "status": deepseek_status(),
                    "modes": code_worker_modes(),
                    "drafts": read_code_worker_drafts(),
                    "safety": {
                        "auto_apply": False,
                        "codex_review_required": True,
                        "live_trading_hard_block": LIVE_TRADING_HARD_BLOCK,
                    },
                })
                return
            if path == "/api/ai/deepseek/code-worker/run":
                json_response(self, deepseek_code_worker(
                    query.get("task", ""),
                    query.get("mode", "draft"),
                ))
                return
            if path == "/api/ai/deepseek/code-worker/archive":
                json_response(self, archive_code_worker_draft(query.get("id", "")))
                return
            if path == "/api/config/api/save":
                config = {
                    "exchange": query.get("exchange", "okx"),
                    "mode": query.get("mode", "paper"),
                    "api_key_env": query.get("apiKeyEnv", "OKX_API_KEY"),
                    "secret_env": query.get("secretEnv", "OKX_SECRET"),
                    "password_env": query.get("passwordEnv", "OKX_PASSWORD"),
                    "updated_at": now_ms(),
                    "live_trading_enabled": False,
                }
                write_json(API_CONFIG_FILE, config)
                append_ledger({"type": "api_config_saved", "exchange": config["exchange"], "mode": config["mode"]})
                json_response(self, {"ok": True, "config": api_config_snapshot()})
                return
            if path == "/api/profile":
                json_response(self, {"ok": True, "profile": PROFILE.snapshot()})
                return
            if path == "/api/platform/snapshot":
                json_response(self, {"ok": True, "platform": platform_snapshot_for_review()})
                return
            if path == "/api/platform/v2":
                json_response(self, platform_v2_overview(pct(query.get("price", "0"))))
                return
            if path == "/api/platform/six-lane":
                json_response(self, platform_v2_overview(pct(query.get("price", "0"))).get("six_lane", {"ok": False}))
                return
            if path == "/api/data/reliability":
                json_response(self, data_reliability_center())
                return
            if path == "/api/data/cache/status":
                json_response(self, market_history_cache_status())
                return
            if path == "/api/data/cache/backfill":
                limit = int(clamp(pct(query.get("limit", "300")), 30, 2000))
                symbol = query.get("symbol", "ETH-USDT").upper()
                if symbol == "ALL":
                    results = [backfill_market_history_cache(item, min(limit, 500)) for item in history_cache_symbols() if item != "BTC-USDT"]
                    json_response(self, {"ok": True, "results": results, "status": market_history_cache_status()})
                    return
                json_response(self, backfill_market_history_cache(symbol, limit))
                return
            if path == "/api/profile/transfer":
                transfer = PROFILE.transfer(
                    query.get("asset", "USDT"),
                    query.get("source", "wallet"),
                    query.get("target", "trading"),
                    pct(query.get("amount", "0")),
                )
                json_response(self, {"ok": True, "transfer": transfer, "profile": PROFILE.snapshot()})
                return
            if path == "/api/profile/notifications/read":
                PROFILE.mark_notifications_read()
                json_response(self, {"ok": True, "profile": PROFILE.snapshot()})
                return
            if path == "/api/profile/guardian":
                enabled = query.get("enabled", "false").lower() in {"1", "true", "yes", "on"}
                PROFILE.set_guardian(enabled)
                json_response(self, {"ok": True, "profile": PROFILE.snapshot()})
                return
            if path == "/api/profile/guardian/heartbeat":
                result = run_guardian_cycle("manual")
                json_response(self, {"ok": bool(result.get("ok", True)), "cycle": result, "profile": PROFILE.snapshot()})
                return
            if path == "/api/profile/guardian/emergency-stop":
                result = guardian_emergency_stop(
                    pct(query.get("price", "0")),
                    query.get("reason", "手动一键急停"),
                    "manual",
                )
                json_response(self, result)
                return
            if path == "/api/profile/indicators":
                PROFILE.set_indicators({
                    "ma": query.get("ma", "false").lower() in {"1", "true", "yes", "on"},
                    "bollinger": query.get("bollinger", "false").lower() in {"1", "true", "yes", "on"},
                    "volume": query.get("volume", "false").lower() in {"1", "true", "yes", "on"},
                    "signals": query.get("signals", "false").lower() in {"1", "true", "yes", "on"},
                })
                json_response(self, {"ok": True, "profile": PROFILE.snapshot()})
                return
            if path == "/api/profile/settings":
                PROFILE.set_settings({
                    "theme": query.get("theme", "dark"),
                    "density": query.get("density", "compact"),
                    "refresh_seconds": query.get("refreshSeconds", "8"),
                    "start_module": query.get("startModule", ".ticker-header"),
                    "layout": query.get("layout", "classic"),
                })
                json_response(self, {"ok": True, "profile": PROFILE.snapshot()})
                return
            if path == "/api/profile/layout":
                PROFILE.set_layout(query.get("layout", "classic"))
                json_response(self, {"ok": True, "profile": PROFILE.snapshot()})
                return
            if path == "/api/daemon/prepare":
                PROFILE.notify("INFO", "后台守护入口", "后台任务入口已准备，当前仍使用本地模拟守护。")
                append_ledger({"type": "daemon_prepare", "status": "prepared"})
                json_response(self, {"ok": True, "profile": PROFILE.snapshot(), "message": "prepared"})
                return
            if path == "/api/markets":
                json_response(self, {"ok": True, "markets": market_universe()})
                return
            if path == "/api/futu/status":
                json_response(self, futu_status_snapshot(force=query.get("force", "false").lower() == "true"))
                return
            if path == "/api/futu/deep":
                json_response(self, read_futu_deep_stock(query.get("symbol", "AAPL"), force=query.get("force", "false").lower() == "true"))
                return
            if path == "/api/futu/universe":
                json_response(self, futu_universe_snapshot())
                return
            if path == "/api/markets/tickers":
                json_response(self, market_tickers_snapshot(
                    fast=query.get("fast", "false").lower() == "true",
                    force=query.get("force", "false").lower() == "true",
                ))
                return
            if path == "/api/stocks/data-sources":
                json_response(self, stock_data_sources_snapshot(
                    query.get("symbol", "AAPL"),
                    query.get("interval", "1d"),
                    query.get("session", "all"),
                ))
                return
            if path == "/api/stocks/data-revisions":
                json_response(self, stock_data_revision_summary(query.get("symbol", "")))
                return
            if path == "/api/stocks/history-prewarm":
                json_response(self, stock_history_prewarm_snapshot(
                    query.get("symbol", ""),
                    start=flag(query.get("start")),
                    force=flag(query.get("force")),
                ))
                return
            if path == "/api/stocks/source-control":
                json_response(self, stock_source_control(
                    query.get("symbol", "AAPL"),
                    query.get("interval", "1d"),
                    query.get("session", "all"),
                    force=flag(query.get("force")),
                ))
                return
            if path == "/api/stocks/news-calendar":
                json_response(self, stock_news_calendar_async(
                    query.get("symbol", "AAPL"),
                    int(clamp(pct(query.get("limit", "8")), 3, 20)),
                ))
                return
            if path == "/api/stocks/quote":
                forced = flag(query.get("force"))
                quote = read_stock_quote(query.get("symbol", "AAPL"), max_age_ms=0 if forced else 4500, use_futu=True)
                if str(quote.get("source") or "").lower() == "offline-seed":
                    quote = _stock_quote_from_cache(query.get("symbol", "AAPL"))
                json_response(self, {"ok": True, "quote": quote, "forced": forced})
                return
            if path == "/api/stocks/candles":
                json_response(self, read_stock_candles(
                    query.get("symbol", "AAPL"),
                    int(clamp(pct(query.get("limit", "300")), 30, 2000)),
                    query.get("interval", "1d"),
                    query.get("session", "all"),
                    flag(query.get("fast")),
                    flag(query.get("force")),
                ))
                return
            if path == "/api/market/insights":
                json_response(self, market_insights(
                    query.get("symbol", "BTC-USDT"),
                    flag(query.get("notify")),
                ))
                return
            if path == "/api/market/chart-candles":
                json_response(self, market_chart_candles(
                    query.get("symbol", "BTC-USDT"),
                    query.get("bar", "1m"),
                    int(clamp(pct(query.get("limit", "300")), 30, 1000)),
                    flag(query.get("fast")),
                    query.get("session", "all"),
                    flag(query.get("force")),
                ))
                return
            if path == "/api/market/snapshot":
                json_response(self, market_data_snapshot(
                    query.get("symbol", "BTC-USDT"),
                    query.get("bar", "1m"),
                    int(clamp(pct(query.get("limit", "300")), 30, 1000)),
                    query.get("session", "all"),
                    flag(query.get("fast")),
                    flag(query.get("force")),
                    flag(query.get("emit")) and not RUNTIME_READ_ONLY,
                    query.get("consumer", "api"),
                ))
                return
            if path == "/api/market/snapshot-health":
                json_response(self, market_data_snapshot_health(
                    query.get("symbol", ""),
                    query.get("bar", ""),
                    query.get("session", ""),
                ))
                return
            if path == "/api/market/quote-batch":
                json_response(self, market_quote_batch(
                    [item.strip().upper() for item in query.get("symbols", "").split(",") if item.strip()],
                    flag(query.get("force")),
                    query.get("consumer", "api"),
                ))
                return
            if path == "/api/market/adapters":
                json_response(self, market_adapter_status())
                return
            if path == "/api/contract/center":
                json_response(self, contract_center(query.get("symbol", "BTC-USDT")))
                return
            if path == "/api/market/scanner":
                json_response(self, build_market_scanner_projection(market_scanner(
                    query.get("symbols", ""),
                    flag(query.get("notify")),
                )))
                return
            if path == "/api/market/anomaly-radar":
                json_response(self, build_market_anomaly_radar_projection(market_anomaly_radar(
                    query.get("symbols", ""),
                    flag(query.get("notify")),
                    flag(query.get("force")),
                )))
                return
            if path == "/api/market/anomaly-events":
                json_response(self, read_anomaly_events(
                    int(clamp(pct(query.get("limit", "80")), 1, 300)),
                    query.get("symbol", ""),
                    pct(query.get("minScore", "0")),
                ))
                return
            if path == "/api/market/anomaly-detail":
                json_response(self, build_market_anomaly_detail_projection(
                    market_anomaly_detail(query.get("symbol", "BTC-USDT"))
                ))
                return
            if path == "/api/market/trend-cockpit":
                json_response(self, build_market_trend_cockpit_projection(
                    trend_analysis_cockpit(query.get("symbol", "BTC-USDT"))
                ))
                return
            if path == "/api/research/panel":
                json_response(self, build_research_panel_projection(
                    research_panel(query.get("symbol", "BTC-USDT"))
                ))
                return
            if path == "/api/paper/snapshot":
                json_response(self, {"ok": True, "paper": PAPER_ACCOUNT.snapshot(pct(query.get("price", "0")))})
                return
            if path == "/api/local/btc-daily":
                limit = int(query.get("limit", "500"))
                json_response(self, read_local_btc_daily(limit))
                return
            if path == "/api/okx/candles":
                okx_query = {
                    "instId": query.get("instId", "BTC-USDT"),
                    "bar": query.get("bar", "1Dutc"),
                    "limit": query.get("limit", "300"),
                }
                if query.get("after"):
                    okx_query["after"] = query["after"]
                if query.get("before"):
                    okx_query["before"] = query["before"]
                json_response(self, {"ok": True, "source": "okx", "payload": read_bodyless_okx("/api/v5/market/candles", okx_query)})
                return
            if path == "/api/okx/history-candles":
                okx_query = {
                    "instId": query.get("instId", "BTC-USDT"),
                    "bar": query.get("bar", "1Dutc"),
                    "limit": query.get("limit", "300"),
                }
                if query.get("after"):
                    okx_query["after"] = query["after"]
                if query.get("before"):
                    okx_query["before"] = query["before"]
                json_response(self, {"ok": True, "source": "okx", "payload": read_bodyless_okx("/api/v5/market/history-candles", okx_query)})
                return
            if path == "/api/okx/ticker":
                json_response(self, {"ok": True, "source": "okx", "payload": read_bodyless_okx("/api/v5/market/ticker", {"instId": query.get("instId", "BTC-USDT")})})
                return
            if path == "/api/okx/tickers":
                json_response(self, {"ok": True, "source": "okx", "payload": read_bodyless_okx("/api/v5/market/tickers", {"instType": query.get("instType", "SPOT")})})
                return
            if path == "/api/okx/instruments":
                json_response(self, {"ok": True, "source": "okx", "payload": read_bodyless_okx("/api/v5/public/instruments", {"instType": query.get("instType", "SPOT")})})
                return
            if path == "/api/okx/funding-rate":
                json_response(self, {"ok": True, "source": "okx", "payload": read_bodyless_okx("/api/v5/public/funding-rate", {"instId": query.get("instId", "BTC-USDT-SWAP")})})
                return
            if path == "/api/okx/mark-price":
                json_response(self, {"ok": True, "source": "okx", "payload": read_bodyless_okx("/api/v5/public/mark-price", {"instType": query.get("instType", "SWAP"), "instId": query.get("instId", "BTC-USDT-SWAP")})})
                return
            if path == "/api/okx/index-tickers":
                okx_query = {"instId": query.get("instId", "BTC-USDT")}
                if query.get("quoteCcy"):
                    okx_query = {"quoteCcy": query["quoteCcy"]}
                json_response(self, {"ok": True, "source": "okx", "payload": read_bodyless_okx("/api/v5/market/index-tickers", okx_query)})
                return
            if path == "/api/okx/funding-rate-history":
                okx_query = {
                    "instId": query.get("instId", "BTC-USDT-SWAP"),
                    "limit": query.get("limit", "30"),
                }
                if query.get("after"):
                    okx_query["after"] = query["after"]
                if query.get("before"):
                    okx_query["before"] = query["before"]
                json_response(self, {"ok": True, "source": "okx", "payload": read_bodyless_okx("/api/v5/public/funding-rate-history", okx_query)})
                return
            if path == "/api/okx/open-interest":
                json_response(self, {"ok": True, "source": "okx", "payload": read_bodyless_okx("/api/v5/public/open-interest", {"instType": query.get("instType", "SWAP"), "instId": query.get("instId", "BTC-USDT-SWAP")})})
                return
            if path == "/api/okx/books":
                book = PUBLIC_ORDER_BOOK.snapshot(query.get("instId", "BTC-USDT"))
                payload = legacy_okx_order_book_payload(book)
                if payload.get("code") != "0":
                    json_response(self, {
                        "ok": False,
                        "error": "public_order_book_unavailable",
                        "order_book": book,
                        "live_order_allowed": False,
                    }, 503)
                    return
                json_response(self, {
                    "ok": True,
                    "source": "okx_public_order_book",
                    "payload": payload,
                    "order_book": book,
                    "live_order_allowed": False,
                })
                return
            if path == "/api/okx/trades":
                json_response(self, {"ok": True, "source": "okx", "payload": read_bodyless_okx("/api/v5/market/trades", {"instId": query.get("instId", "BTC-USDT"), "limit": query.get("limit", "50")})})
                return
            json_response(self, {"ok": False, "error": f"unknown endpoint: {path}"}, 404)
        except Exception as exc:
            json_response(self, {"ok": False, "error": str(exc)}, 502)

    def handle_static(self, path: str) -> None:
        target = safe_static_path(path)
        if target is None or not target.exists() or not target.is_file():
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except CLIENT_DISCONNECT_ERRORS:
            self.close_connection = True


class ExclusiveThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = False
    allow_reuse_port = False
    daemon_threads = True

    def server_bind(self) -> None:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local exchange terminal.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    normalized_host = str(args.host or "").strip().lower()
    if normalized_host == "localhost":
        args.host = "127.0.0.1"
        normalized_host = "127.0.0.1"
    if normalized_host not in LOCAL_LOOPBACK_HOSTS:
        raise SystemExit("Only loopback hosts are allowed. Use --host 127.0.0.1, --host ::1, or --host localhost.")
    try:
        server = ExclusiveThreadingHTTPServer((args.host, args.port), ExchangeTerminalHandler)
    except OSError as exc:
        raise SystemExit(f"Cannot start Hakimi Trade on {args.host}:{args.port}; another instance may already be running: {exc}") from exc
    url = f"http://{args.host}:{args.port}/"
    guardian_started = not RUNTIME_READ_ONLY
    if guardian_started:
        start_guardian_worker()
    print(f"Exchange terminal running: {url}")
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if guardian_started:
            stop_guardian_worker()
        server.server_close()


if __name__ == "__main__":
    main()
