from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = ROOT_DIR.parents[2]


def load_local_ai_env() -> None:
    skip_local_env = any(
        str(os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on"}
        for name in (
            "HAKIMI_SKIP_LOCAL_AI_ENV",
            "HAKIMI_RUNTIME_READ_ONLY",
            "HAKIMI_TEST_MODE",
        )
    )
    if skip_local_env:
        return
    env_path = WORKSPACE_DIR / ".env.local"
    allowed = {"OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL", "GPT_MODEL"}
    if not env_path.is_file():
        return
    try:
        rows = env_path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return
    for raw in rows:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        if name not in allowed or os.getenv(name):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if value:
            os.environ[name] = value


load_local_ai_env()

PROJECT_DIR = ROOT_DIR.parent
STATIC_DIR = ROOT_DIR / "static"
APP_DATA_ROOT = Path(os.getenv("APPDATA") or (Path.home() / "AppData" / "Roaming")) / "HakimiTradeV2"
RUNTIME_DIR_OVERRIDE = str(os.getenv("HAKIMI_RUNTIME_DIR") or "").strip()
RUNTIME_DIR = (
    Path(RUNTIME_DIR_OVERRIDE).expanduser().resolve()
    if RUNTIME_DIR_OVERRIDE
    else APP_DATA_ROOT / "runtime"
    if getattr(sys, "frozen", False)
    else PROJECT_DIR / "runtime"
)
RUNTIME_READ_ONLY = str(os.getenv("HAKIMI_RUNTIME_READ_ONLY") or "").strip().lower() in {
    "1", "true", "yes", "on",
}
STATE_FILE = RUNTIME_DIR / "exchange_terminal_state.json"
LEDGER_FILE = RUNTIME_DIR / "exchange_terminal_ledger.jsonl"
API_CONFIG_FILE = RUNTIME_DIR / "exchange_api_config.json"
PROFILE_FILE = RUNTIME_DIR / "exchange_terminal_profile.json"
CODE_WORKER_FILE = RUNTIME_DIR / "deepseek_code_worker_drafts.json"
EXPORT_DIR = RUNTIME_DIR / "exports"

OKX_BASE_URL = "https://www.okx.com"
OKX_TIMEOUT = float(os.getenv("OKX_TIMEOUT", "4"))

FUTU_HOST = os.getenv("FUTU_HOST", "127.0.0.1")
FUTU_PORT = int(os.getenv("FUTU_PORT", "11111"))
FUTU_TELNET_HOST = os.getenv("FUTU_TELNET_HOST", "127.0.0.1")
FUTU_TELNET_PORT = int(os.getenv("FUTU_TELNET_PORT", "22222"))
FUTU_OPEND_XML = Path(os.getenv(
    "FUTU_OPEND_XML",
    r"C:\Users\Administrator\Documents\Futu_OpenD_10.7.6728_Windows\Futu_OpenD_10.7.6728_Windows\Futu_OpenD_10.7.6728_Windows\FutuOpenD.xml",
))

ALLOW_STOCK_FALLBACK = os.getenv("ALLOW_STOCK_FALLBACK", "false").lower() in {"1", "true", "yes", "on"}
ALLOW_STOCK_HISTORY_FALLBACK = os.getenv("ALLOW_STOCK_HISTORY_FALLBACK", "true").lower() in {"1", "true", "yes", "on"}
STOCK_QUOTE_TIMEOUT = float(os.getenv("STOCK_QUOTE_TIMEOUT", "3"))
STOCK_HISTORY_TIMEOUT = float(os.getenv("STOCK_HISTORY_TIMEOUT", "2"))
STOCK_EXTERNAL_PROVIDER_ORDER = [
    item.strip().lower()
    for item in os.getenv("STOCK_EXTERNAL_PROVIDER_ORDER", "yahoo,stooq").split(",")
    if item.strip()
]

APP_NAME = "哈基米交易"
TERMINAL_VERSION = "v2"
TERMINAL_RELEASE_NAME = "哈基米交易 v2"

DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
DEEPSEEK_THINKING_ENABLED = os.getenv("DEEPSEEK_THINKING", "enabled").lower() not in {"0", "false", "off", "disabled"}
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", os.getenv("GPT_MODEL", "gpt-4o-mini"))

# Real-order execution is permanently disabled in this codebase.  This is a
# code invariant, not a runtime preference that an environment variable may
# weaken.
LIVE_TRADING_HARD_BLOCK = True

CORE_CRYPTO_BASES = ["BTC", "ETH", "SOL", "BNB", "DOGE"]
STOCK_MARKETS = [
    {"symbol": "AAPL", "futu": "US.AAPL", "yahoo": "AAPL", "stooq": "aapl.us", "name": "Apple", "exchange": "NASDAQ", "market": "US", "quote": "USD", "sector": "Mega Cap Tech"},
    {"symbol": "MSFT", "futu": "US.MSFT", "yahoo": "MSFT", "stooq": "msft.us", "name": "Microsoft", "exchange": "NASDAQ", "market": "US", "quote": "USD", "sector": "Mega Cap Tech"},
    {"symbol": "NVDA", "futu": "US.NVDA", "yahoo": "NVDA", "stooq": "nvda.us", "name": "Nvidia", "exchange": "NASDAQ", "market": "US", "quote": "USD", "sector": "AI Chip"},
    {"symbol": "AMZN", "futu": "US.AMZN", "yahoo": "AMZN", "stooq": "amzn.us", "name": "Amazon", "exchange": "NASDAQ", "market": "US", "quote": "USD", "sector": "Mega Cap Tech"},
    {"symbol": "GOOGL", "futu": "US.GOOGL", "yahoo": "GOOGL", "stooq": "googl.us", "name": "Alphabet", "exchange": "NASDAQ", "market": "US", "quote": "USD", "sector": "Mega Cap Tech"},
    {"symbol": "META", "futu": "US.META", "yahoo": "META", "stooq": "meta.us", "name": "Meta Platforms", "exchange": "NASDAQ", "market": "US", "quote": "USD", "sector": "Mega Cap Tech"},
    {"symbol": "TSLA", "futu": "US.TSLA", "yahoo": "TSLA", "stooq": "tsla.us", "name": "Tesla", "exchange": "NASDAQ", "market": "US", "quote": "USD", "sector": "EV"},
    {"symbol": "MSTR", "futu": "US.MSTR", "yahoo": "MSTR", "stooq": "mstr.us", "name": "MicroStrategy", "exchange": "NASDAQ", "market": "US", "quote": "USD", "sector": "BTC Proxy"},
    {"symbol": "RKLB", "futu": "US.RKLB", "yahoo": "RKLB", "stooq": "rklb.us", "name": "Rocket Lab", "exchange": "NASDAQ", "market": "US", "quote": "USD", "sector": "Space / SpaceX proxy"},
    {"symbol": "ASTS", "futu": "US.ASTS", "yahoo": "ASTS", "stooq": "asts.us", "name": "AST SpaceMobile", "exchange": "NASDAQ", "market": "US", "quote": "USD", "sector": "Space / SpaceX proxy"},
    {"symbol": "SPY", "futu": "US.SPY", "yahoo": "SPY", "stooq": "spy.us", "name": "S&P 500 ETF", "exchange": "NYSE Arca", "market": "US", "quote": "USD", "sector": "Index ETF"},
    {"symbol": "QQQ", "futu": "US.QQQ", "yahoo": "QQQ", "stooq": "qqq.us", "name": "Nasdaq 100 ETF", "exchange": "NASDAQ", "market": "US", "quote": "USD", "sector": "Index ETF"},
    {"symbol": "AMD", "futu": "US.AMD", "yahoo": "AMD", "stooq": "amd.us", "name": "AMD", "exchange": "NASDAQ", "market": "US", "quote": "USD", "sector": "AI Chip"},
    {"symbol": "AVGO", "futu": "US.AVGO", "yahoo": "AVGO", "stooq": "avgo.us", "name": "Broadcom", "exchange": "NASDAQ", "market": "US", "quote": "USD", "sector": "AI Chip"},
    {"symbol": "TSM", "futu": "US.TSM", "yahoo": "TSM", "stooq": "tsm.us", "name": "TSMC ADR", "exchange": "NYSE", "market": "US", "quote": "USD", "sector": "Semiconductor Foundry"},
    {"symbol": "ASML", "futu": "US.ASML", "yahoo": "ASML", "stooq": "asml.us", "name": "ASML", "exchange": "NASDAQ", "market": "US", "quote": "USD", "sector": "Semi Equipment"},
    {"symbol": "AMAT", "futu": "US.AMAT", "yahoo": "AMAT", "stooq": "amat.us", "name": "Applied Materials", "exchange": "NASDAQ", "market": "US", "quote": "USD", "sector": "Semi Equipment"},
    {"symbol": "LRCX", "futu": "US.LRCX", "yahoo": "LRCX", "stooq": "lrcx.us", "name": "Lam Research", "exchange": "NASDAQ", "market": "US", "quote": "USD", "sector": "Semi Equipment"},
    {"symbol": "KLAC", "futu": "US.KLAC", "yahoo": "KLAC", "stooq": "klac.us", "name": "KLA", "exchange": "NASDAQ", "market": "US", "quote": "USD", "sector": "Semi Equipment"},
    {"symbol": "QCOM", "futu": "US.QCOM", "yahoo": "QCOM", "stooq": "qcom.us", "name": "Qualcomm", "exchange": "NASDAQ", "market": "US", "quote": "USD", "sector": "Semiconductor Design"},
    {"symbol": "ARM", "futu": "US.ARM", "yahoo": "ARM", "stooq": "arm.us", "name": "Arm Holdings", "exchange": "NASDAQ", "market": "US", "quote": "USD", "sector": "Semiconductor IP"},
    {"symbol": "ANET", "futu": "US.ANET", "yahoo": "ANET", "stooq": "anet.us", "name": "Arista Networks", "exchange": "NYSE", "market": "US", "quote": "USD", "sector": "AI Networking"},
    {"symbol": "MRVL", "futu": "US.MRVL", "yahoo": "MRVL", "stooq": "mrvl.us", "name": "Marvell Technology", "exchange": "NASDAQ", "market": "US", "quote": "USD", "sector": "Semiconductor Design"},
    {"symbol": "INTC", "futu": "US.INTC", "yahoo": "INTC", "stooq": "intc.us", "name": "Intel", "exchange": "NASDAQ", "market": "US", "quote": "USD", "sector": "Semiconductor Foundry"},
    {"symbol": "SMCI", "futu": "US.SMCI", "yahoo": "SMCI", "stooq": "smci.us", "name": "Super Micro", "exchange": "NASDAQ", "market": "US", "quote": "USD", "sector": "AI Server"},
    {"symbol": "MU", "futu": "US.MU", "yahoo": "MU", "stooq": "mu.us", "name": "Micron", "exchange": "NASDAQ", "market": "US", "quote": "USD", "sector": "Memory / Storage"},
    {"symbol": "WDC", "futu": "US.WDC", "yahoo": "WDC", "stooq": "wdc.us", "name": "Western Digital", "exchange": "NASDAQ", "market": "US", "quote": "USD", "sector": "Memory / Storage"},
    {"symbol": "STX", "futu": "US.STX", "yahoo": "STX", "stooq": "stx.us", "name": "Seagate", "exchange": "NASDAQ", "market": "US", "quote": "USD", "sector": "Memory / Storage"},
    {"symbol": "PSTG", "futu": "US.PSTG", "yahoo": "PSTG", "stooq": "pstg.us", "name": "Pure Storage", "exchange": "NYSE", "market": "US", "quote": "USD", "sector": "Memory / Storage"},
    {"symbol": "NTAP", "futu": "US.NTAP", "yahoo": "NTAP", "stooq": "ntap.us", "name": "NetApp", "exchange": "NASDAQ", "market": "US", "quote": "USD", "sector": "Memory / Storage"},
    {"symbol": "HK.00700", "futu": "HK.00700", "yahoo": "0700.HK", "name": "Tencent", "exchange": "HKEX", "market": "HK", "quote": "HKD", "sector": "China Internet"},
    {"symbol": "HK.09988", "futu": "HK.09988", "yahoo": "9988.HK", "name": "Alibaba HK", "exchange": "HKEX", "market": "HK", "quote": "HKD", "sector": "China Internet"},
    {"symbol": "HK.03690", "futu": "HK.03690", "yahoo": "3690.HK", "name": "Meituan", "exchange": "HKEX", "market": "HK", "quote": "HKD", "sector": "China Internet"},
    {"symbol": "HK.01810", "futu": "HK.01810", "yahoo": "1810.HK", "name": "Xiaomi", "exchange": "HKEX", "market": "HK", "quote": "HKD", "sector": "Smart Hardware"},
    {"symbol": "HK.01211", "futu": "HK.01211", "yahoo": "1211.HK", "name": "BYD", "exchange": "HKEX", "market": "HK", "quote": "HKD", "sector": "EV"},
    {"symbol": "HK.00002", "futu": "HK.00002", "yahoo": "0002.HK", "name": "CLP Holdings", "exchange": "HKEX", "market": "HK", "quote": "HKD", "sector": "HK Power"},
    {"symbol": "HK.00006", "futu": "HK.00006", "yahoo": "0006.HK", "name": "Power Assets", "exchange": "HKEX", "market": "HK", "quote": "HKD", "sector": "HK Power"},
    {"symbol": "HK.00836", "futu": "HK.00836", "yahoo": "0836.HK", "name": "China Resources Power", "exchange": "HKEX", "market": "HK", "quote": "HKD", "sector": "HK Power"},
    {"symbol": "HK.00902", "futu": "HK.00902", "yahoo": "0902.HK", "name": "Huaneng Power", "exchange": "HKEX", "market": "HK", "quote": "HKD", "sector": "HK Power"},
    {"symbol": "HK.00916", "futu": "HK.00916", "yahoo": "0916.HK", "name": "China Longyuan", "exchange": "HKEX", "market": "HK", "quote": "HKD", "sector": "HK Power"},
    {"symbol": "HK.02638", "futu": "HK.02638", "yahoo": "2638.HK", "name": "HK Electric", "exchange": "HKEX", "market": "HK", "quote": "HKD", "sector": "HK Power"},
]

STOCK_SEED_PRICES = {
    "AAPL": 195.0,
    "MSFT": 485.0,
    "NVDA": 180.0,
    "AMZN": 230.0,
    "GOOGL": 185.0,
    "META": 720.0,
    "TSLA": 320.0,
    "MSTR": 390.0,
    "RKLB": 40.0,
    "ASTS": 55.0,
    "SPY": 640.0,
    "QQQ": 560.0,
    "AMD": 155.0,
    "AVGO": 280.0,
    "TSM": 250.0,
    "ASML": 800.0,
    "AMAT": 210.0,
    "LRCX": 105.0,
    "KLAC": 900.0,
    "QCOM": 165.0,
    "ARM": 145.0,
    "ANET": 140.0,
    "MRVL": 90.0,
    "INTC": 23.0,
    "SMCI": 55.0,
    "MU": 130.0,
    "WDC": 70.0,
    "STX": 110.0,
    "PSTG": 65.0,
    "NTAP": 110.0,
    "HK.00700": 420.0,
    "HK.09988": 110.0,
    "HK.03690": 120.0,
    "HK.01810": 55.0,
    "HK.01211": 270.0,
    "HK.00002": 67.0,
    "HK.00006": 48.0,
    "HK.00836": 22.0,
    "HK.00902": 6.0,
    "HK.00916": 7.0,
    "HK.02638": 5.5,
}

STOCK_SEED_VOLUMES = {
    "AAPL": 72_000_000,
    "MSFT": 25_000_000,
    "NVDA": 210_000_000,
    "AMZN": 45_000_000,
    "GOOGL": 30_000_000,
    "META": 17_000_000,
    "TSLA": 95_000_000,
    "MSTR": 18_000_000,
    "RKLB": 32_000_000,
    "ASTS": 42_000_000,
    "SPY": 68_000_000,
    "QQQ": 48_000_000,
    "AMD": 55_000_000,
    "AVGO": 30_000_000,
    "TSM": 16_000_000,
    "ASML": 2_000_000,
    "AMAT": 8_000_000,
    "LRCX": 8_000_000,
    "KLAC": 1_500_000,
    "QCOM": 8_000_000,
    "ARM": 7_000_000,
    "ANET": 7_000_000,
    "MRVL": 12_000_000,
    "INTC": 95_000_000,
    "SMCI": 45_000_000,
    "MU": 28_000_000,
    "WDC": 6_000_000,
    "STX": 4_000_000,
    "PSTG": 5_000_000,
    "NTAP": 2_500_000,
    "HK.00700": 22_000_000,
    "HK.09988": 58_000_000,
    "HK.03690": 32_000_000,
    "HK.01810": 70_000_000,
    "HK.01211": 11_000_000,
    "HK.00002": 7_000_000,
    "HK.00006": 5_000_000,
    "HK.00836": 18_000_000,
    "HK.00902": 40_000_000,
    "HK.00916": 26_000_000,
    "HK.02638": 9_000_000,
}

BTC_DAILY_DATA_DIR = Path(os.getenv("BTC_DAILY_DATA_DIR", str(RUNTIME_DIR / "jiaoyiguowangshuju")))
BTC_DAILY_FALLBACK_DIR = Path(os.getenv("BTC_DAILY_FALLBACK_DIR", r"Z:\jiaoyiguowangshuju"))
BTC_DAILY_DB = Path(os.getenv("BTC_DAILY_DB", str(BTC_DAILY_DATA_DIR / "btc_daily_prices.sqlite")))
BTC_DAILY_CSV = Path(os.getenv("BTC_DAILY_CSV", str(BTC_DAILY_DATA_DIR / "btc_daily_prices.csv")))
BTC_DAILY_FALLBACK_DB = BTC_DAILY_FALLBACK_DIR / "btc_daily_prices.sqlite"
BTC_DAILY_FALLBACK_CSV = BTC_DAILY_FALLBACK_DIR / "btc_daily_prices.csv"
BTC_DAILY_DB_CACHE = RUNTIME_DIR / "btc_daily_prices_cache.sqlite"
MARKET_HISTORY_CACHE_DB = RUNTIME_DIR / "market_history_cache.sqlite"
STOCK_CANDLE_CACHE_DB = RUNTIME_DIR / "stock_candles_cache.sqlite"
CORPORATE_ACTION_DB = RUNTIME_DIR / "stock_corporate_actions.sqlite"
MARKET_DATA_REVISION_DB = RUNTIME_DIR / "market_data_revisions.sqlite"
PORTFOLIO_PAPER_DB = RUNTIME_DIR / "portfolio_paper.sqlite"
ANOMALY_EVENT_DB = RUNTIME_DIR / "market_anomaly_events.sqlite"
