import http from "node:http";
import { createReadStream, existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const publicDir = path.join(__dirname, "public");
const dataDir = path.join(__dirname, "data");
const historyDir = path.join(dataDir, "history");
const stateFile = path.join(dataDir, "state.json");
const urlFile = path.join(__dirname, "server.url");
const preferredPort = Number(process.env.PORT || 4173);
const OKX_BASE_URL = "https://www.okx.com";

const symbols = {
  "BTC-USDT": { base: 67200, amp: 1850, trend: 0.58, step: 0.92 },
  "ETH-USDT": { base: 3520, amp: 142, trend: 0.33, step: 1.08 },
  "SOL-USDT": { base: 148, amp: 11, trend: 0.18, step: 1.21 }
};

const strategyTemplates = [
  {
    id: "ma_trend",
    name: "均线趋势",
    category: "趋势",
    risk: "中低",
    beginner: true,
    summary: "短期均线上穿长期均线入场，适合趋势清晰的主流币。",
    bestFor: "趋势行情、BTC/ETH 等高流动性品种",
    warning: "震荡行情容易反复止损。"
  },
  {
    id: "spot_grid",
    name: "现货网格",
    category: "震荡",
    risk: "中",
    beginner: true,
    summary: "在设定价格区间内低买高卖，赚取波动收益。",
    bestFor: "横盘震荡、无杠杆现货",
    warning: "跌破区间后可能长期浮亏。"
  },
  {
    id: "dca",
    name: "定投策略",
    category: "长期",
    risk: "低",
    beginner: true,
    summary: "按固定时间和金额买入，弱化择时。",
    bestFor: "长期配置 BTC/ETH",
    warning: "单边下跌时账户会持续浮亏。"
  },
  {
    id: "martingale",
    name: "马丁加仓",
    category: "仓位管理",
    risk: "高",
    beginner: false,
    summary: "价格朝不利方向移动时分批加仓，试图降低平均成本。",
    bestFor: "强风控模拟盘研究，不建议新手实盘",
    warning: "连续单边行情会快速放大亏损，默认只允许模拟盘。"
  },
  {
    id: "anti_martingale",
    name: "反马丁",
    category: "仓位管理",
    risk: "中高",
    beginner: false,
    summary: "盈利后逐步加仓，亏损后减仓，让仓位跟随优势行情。",
    bestFor: "趋势延续行情、严格止损",
    warning: "趋势反转时可能回吐利润。"
  },
  {
    id: "livermore",
    name: "利弗莫尔突破",
    category: "突破",
    risk: "中高",
    beginner: false,
    summary: "突破关键价位后试探建仓，确认趋势后金字塔加仓。",
    bestFor: "关键位突破、强趋势行情",
    warning: "假突破会造成连续小亏，需要严格试错成本。"
  },
  {
    id: "rsi_reversal",
    name: "RSI 反转",
    category: "反转",
    risk: "高",
    beginner: false,
    summary: "RSI 超卖尝试买入，超买尝试卖出。",
    bestFor: "短线反弹和回归均值",
    warning: "单边下跌时可能越跌越买。"
  }
];

const newsSources = [
  { name: "CoinDesk", url: "https://www.coindesk.com/arc/outboundfeeds/rss/" },
  { name: "Cointelegraph", url: "https://cointelegraph.com/rss" }
];

const defaultState = () => ({
  account: {
    connected: false,
    apiKeyMasked: "",
    environment: "demo",
    readPermission: true,
    tradePermission: false,
    withdrawPermission: false,
    ipWhitelist: "建议开启",
    lastTestAt: null
  },
  dashboard: {
    equity: 10164.2,
    dailyPnl: 82.4,
    allocation: 18,
    riskLevel: "低风险"
  },
  strategy: {
    templateId: "ma_trend",
    name: "均线趋势",
    symbol: "BTC-USDT",
    shortMa: 20,
    longMa: 60,
    allocationPct: 10,
    stopLossPct: 3,
    takeProfitPct: 0,
    timeframe: "4h",
    mode: "paper"
  },
  market: {
    source: "mock",
    instType: "SPOT",
    updatedAt: null
  },
  paper: {
    running: false,
    day: 3,
    equity: 10164.2,
    events: [
      {
        time: "10:40",
        title: "均线趋势买入 BTC-USDT",
        detail: "MA20 上穿 MA60，仓位 10%，止损 3%",
        result: "持仓中",
        tone: "green"
      },
      {
        time: "13:20",
        title: "现货网格卖出 ETH-USDT",
        detail: "触达上方网格，完成一次波动收益",
        result: "+8.2 USDT",
        tone: "green"
      }
    ]
  },
  risk: {
    paused: false,
    liveLocked: true,
    dailyLossPct: 0.8,
    dailyLossLimitPct: 3,
    strategyCapitalPct: 10,
    totalCapitalPct: 18,
    maxCapitalPct: 30,
    losingStreak: 1,
    losingStreakLimit: 4,
    apiLatencyMs: 180,
    marketLatencyMs: 260,
    leverageLocked: true
  },
  automation: {
    running: false,
    dryRun: true,
    refreshSeconds: 5,
    liveTradingLocked: true,
    profiles: [
      {
        symbol: "BTC-USDT",
        templateId: "livermore",
        anchorPrice: 67000,
        upperAnchor: 69000,
        lowerAnchor: 65000,
        maxCapitalPct: 8,
        positionSide: "flat",
        status: "观察",
        enabled: true
      },
      {
        symbol: "ETH-USDT",
        templateId: "anti_martingale",
        anchorPrice: 3500,
        upperAnchor: 3650,
        lowerAnchor: 3350,
        maxCapitalPct: 6,
        positionSide: "flat",
        status: "观察",
        enabled: true
      },
      {
        symbol: "SOL-USDT",
        templateId: "spot_grid",
        anchorPrice: 150,
        upperAnchor: 162,
        lowerAnchor: 138,
        maxCapitalPct: 5,
        positionSide: "flat",
        status: "观察",
        enabled: true
      }
    ],
    decisions: [
      {
        time: new Date().toISOString(),
        symbol: "BTC-USDT",
        strategy: "利弗莫尔突破",
        action: "等待",
        price: 0,
        reason: "等待实时价格靠近关键锚点",
        dryRun: true
      }
    ]
  },
  review: {
    summary: "表现稳定，但观察期不足，建议继续模拟观察。",
    rows: [
      ["买入 BTC", "MA20 上穿 MA60", "+1.2%", "趋势信号不是最低点信号"],
      ["卖出 ETH", "触达网格上沿", "+8.2 USDT", "网格赚的是波动收益"],
      ["暂停 SOL", "回测样本不足", "无交易", "样本不够时不进入实盘"]
    ]
  }
});

function ensureState() {
  if (!existsSync(dataDir)) mkdirSync(dataDir, { recursive: true });
  if (!existsSync(stateFile)) {
    const initial = defaultState();
    writeFileSync(stateFile, JSON.stringify(initial, null, 2), "utf8");
    return initial;
  }

  try {
    return deepMerge(defaultState(), JSON.parse(readFileSync(stateFile, "utf8")));
  } catch {
    const initial = defaultState();
    writeFileSync(stateFile, JSON.stringify(initial, null, 2), "utf8");
    return initial;
  }
}

function deepMerge(base, override) {
  if (!override || typeof override !== "object" || Array.isArray(override)) return base;
  const output = { ...base };
  Object.entries(override).forEach(([key, value]) => {
    if (value && typeof value === "object" && !Array.isArray(value) && base[key] && typeof base[key] === "object" && !Array.isArray(base[key])) {
      output[key] = deepMerge(base[key], value);
    } else {
      output[key] = value;
    }
  });
  return output;
}

let state = ensureState();

function saveState() {
  writeFileSync(stateFile, JSON.stringify(state, null, 2), "utf8");
}

function json(res, data, status = 200) {
  const body = JSON.stringify(data);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(body),
    "Cache-Control": "no-store"
  });
  res.end(body);
}

function badRequest(res, message) {
  json(res, { ok: false, error: message }, 400);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", chunk => {
      body += chunk;
      if (body.length > 1_000_000) {
        reject(new Error("请求内容过大"));
        req.destroy();
      }
    });
    req.on("end", () => {
      if (!body) {
        resolve({});
        return;
      }
      try {
        resolve(JSON.parse(body));
      } catch {
        reject(new Error("JSON 格式不正确"));
      }
    });
    req.on("error", reject);
  });
}

function maskKey(key = "") {
  const trimmed = String(key).trim();
  if (!trimmed) return "";
  if (trimmed.length <= 8) return `${trimmed.slice(0, 2)}••••${trimmed.slice(-2)}`;
  return `${trimmed.slice(0, 6)}••••••${trimmed.slice(-4)}`;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, Number(value)));
}

function average(values) {
  if (!values.length) return 0;
  return values.reduce((sum, item) => sum + item, 0) / values.length;
}

function generateCandles(symbol = "BTC-USDT", limit = 240, offset = 0) {
  const meta = symbols[symbol] || symbols["BTC-USDT"];
  const candles = [];
  const now = Date.now();
  let lastClose = meta.base;
  const phase = Number.isFinite(Number(offset)) ? ((Number(offset) % 240) + 240) % 240 : 0;

  for (let i = 0; i < limit; i += 1) {
    const t = i + phase;
    const wave = Math.sin(t / 9.5) * meta.amp + Math.cos(t / 21) * meta.amp * 0.42;
    const drift = (i - limit / 2) * meta.trend;
    const close = Math.max(0.1, meta.base + wave + drift);
    const open = i === 0 ? close * 0.998 : lastClose;
    const high = Math.max(open, close) * (1 + 0.0025 + Math.abs(Math.sin(t)) * 0.004);
    const low = Math.min(open, close) * (1 - 0.0025 - Math.abs(Math.cos(t)) * 0.004);
    const volume = Math.round((1200 + Math.abs(Math.sin(t / 4)) * 6800) * meta.step);

    candles.push({
      time: new Date(now - (limit - i) * 60 * 60 * 1000).toISOString(),
      open: Number(open.toFixed(4)),
      high: Number(high.toFixed(4)),
      low: Number(low.toFixed(4)),
      close: Number(close.toFixed(4)),
      volume
    });
    lastClose = close;
  }
  return candles;
}

function okxBar(timeframe = "4h") {
  const map = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "1h": "1H",
    "4h": "4H",
    "1d": "1D"
  };
  return map[String(timeframe).toLowerCase()] || "1H";
}

function timeframeMs(timeframe = "1h") {
  const map = {
    "1m": 60_000,
    "5m": 5 * 60_000,
    "15m": 15 * 60_000,
    "1h": 60 * 60_000,
    "4h": 4 * 60 * 60_000,
    "1d": 24 * 60 * 60_000
  };
  return map[String(timeframe).toLowerCase()] || map["1h"];
}

function historyFileName(symbol, timeframe, years) {
  return `${symbol.replace(/[^A-Z0-9_-]/gi, "_")}_${timeframe}_${years}y.json`;
}

function instTypeLabel(instType) {
  return {
    SPOT: "现货",
    SWAP: "永续合约",
    FUTURES: "交割合约"
  }[instType] || instType;
}

async function fetchOkx(pathname, params = {}, timeoutMs = 7000) {
  const url = new URL(pathname, OKX_BASE_URL);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, String(value));
  });
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      signal: controller.signal,
      headers: {
        "Accept": "application/json",
        "User-Agent": "OKX-Quant-Desk/0.1"
      }
    });
    if (!response.ok) throw new Error(`OKX HTTP ${response.status}`);
    const payload = await response.json();
    if (payload.code !== "0") throw new Error(payload.msg || `OKX code ${payload.code}`);
    return payload.data || [];
  } finally {
    clearTimeout(timer);
  }
}

function normalizeTicker(row, instType) {
  const last = Number(row.last || 0);
  const open = Number(row.open24h || row.sodUtc0 || last || 0);
  const changePct = open ? ((last - open) / open) * 100 : 0;
  return {
    instType,
    instTypeLabel: instTypeLabel(instType),
    instId: row.instId,
    last,
    bidPx: Number(row.bidPx || 0),
    askPx: Number(row.askPx || 0),
    high24h: Number(row.high24h || 0),
    low24h: Number(row.low24h || 0),
    vol24h: Number(row.vol24h || 0),
    volCcy24h: Number(row.volCcy24h || row.vol24h || 0),
    changePct: Number(changePct.toFixed(2)),
    ts: Number(row.ts || Date.now())
  };
}

function normalizeInstrument(row) {
  return {
    instType: row.instType,
    instTypeLabel: instTypeLabel(row.instType),
    instId: row.instId,
    baseCcy: row.baseCcy || "",
    quoteCcy: row.quoteCcy || "",
    settleCcy: row.settleCcy || "",
    ctVal: row.ctVal || "",
    ctType: row.ctType || "",
    state: row.state || "",
    tickSz: row.tickSz || "",
    lotSz: row.lotSz || "",
    minSz: row.minSz || "",
    lever: row.lever || ""
  };
}

function latestMockTicker(symbol = "BTC-USDT") {
  const instId = symbols[symbol] ? symbol : symbol.replace("-SWAP", "");
  const candles = generateCandles(instId, 32, Date.now() / 1000);
  const first = candles[0].close;
  const last = candles[candles.length - 1].close;
  return {
    instId: symbol,
    last,
    bidPx: Number((last * 0.9998).toFixed(4)),
    askPx: Number((last * 1.0002).toFixed(4)),
    high24h: Math.max(...candles.map(item => item.high)),
    low24h: Math.min(...candles.map(item => item.low)),
    vol24h: 12000,
    volCcy24h: Number((last * 12000).toFixed(2)),
    changePct: Number((((last - first) / first) * 100).toFixed(2)),
    ts: Date.now()
  };
}

function mockOrderBook(symbol = "BTC-USDT", depth = 18) {
  const last = latestMockTicker(symbol).last;
  const bids = [];
  const asks = [];
  for (let i = 0; i < depth; i += 1) {
    const spread = last * (0.00025 + i * 0.00016);
    const size = Number((0.08 + Math.abs(Math.sin(Date.now() / 900 + i)) * 2.6).toFixed(4));
    bids.push({ price: Number((last - spread).toFixed(4)), size, total: Number((size * (i + 1)).toFixed(4)) });
    asks.push({ price: Number((last + spread).toFixed(4)), size, total: Number((size * (i + 1)).toFixed(4)) });
  }
  return { bids, asks };
}

function mockTrades(symbol = "BTC-USDT", limit = 24) {
  const last = latestMockTicker(symbol).last;
  return Array.from({ length: limit }, (_, index) => {
    const side = Math.sin(Date.now() / 700 + index) > 0 ? "buy" : "sell";
    const price = Number((last + Math.sin(index * 1.7 + Date.now() / 1000) * last * 0.0018).toFixed(4));
    return {
      tradeId: `mock-${Date.now()}-${index}`,
      side,
      price,
      size: Number((0.01 + Math.abs(Math.cos(index + Date.now() / 1100)) * 1.8).toFixed(4)),
      time: new Date(Date.now() - index * 1200).toISOString()
    };
  });
}

async function getOrderBook(symbol = "BTC-USDT", depth = 18) {
  try {
    const data = await fetchOkx("/api/v5/market/books", { instId: symbol, sz: depth }, 2500);
    const book = data[0] || {};
    return {
      ok: true,
      source: "okx",
      symbol,
      bids: (book.bids || []).map(row => ({ price: Number(row[0]), size: Number(row[1]), total: Number(row[3] || row[1]) })),
      asks: (book.asks || []).map(row => ({ price: Number(row[0]), size: Number(row[1]), total: Number(row[3] || row[1]) })),
      updatedAt: new Date(Number(book.ts || Date.now())).toISOString()
    };
  } catch (error) {
    return { ok: true, source: "mock", symbol, ...mockOrderBook(symbol, depth), error: error.message, updatedAt: new Date().toISOString() };
  }
}

async function getRecentTrades(symbol = "BTC-USDT", limit = 24) {
  try {
    const data = await fetchOkx("/api/v5/market/trades", { instId: symbol, limit }, 2500);
    return {
      ok: true,
      source: "okx",
      symbol,
      trades: data.map(row => ({
        tradeId: row.tradeId,
        side: row.side,
        price: Number(row.px),
        size: Number(row.sz),
        time: new Date(Number(row.ts)).toISOString()
      })),
      updatedAt: new Date().toISOString()
    };
  } catch (error) {
    return { ok: true, source: "mock", symbol, trades: mockTrades(symbol, limit), error: error.message, updatedAt: new Date().toISOString() };
  }
}

async function getDerivativeMeta(symbol = "BTC-USDT") {
  if (!symbol.includes("SWAP") && !symbol.includes("FUTURES")) {
    const quote = await getLatestTicker(symbol);
    return {
      ok: true,
      source: quote.source,
      indexPrice: quote.ticker.last,
      markPrice: quote.ticker.last,
      fundingRate: 0,
      nextFundingTime: "",
      openInterest: 0
    };
  }

  try {
    const [markRows, fundingRows, oiRows] = await Promise.all([
      fetchOkx("/api/v5/public/mark-price", { instType: symbol.includes("SWAP") ? "SWAP" : "FUTURES", instId: symbol }, 2500),
      symbol.includes("SWAP")
        ? fetchOkx("/api/v5/public/funding-rate", { instId: symbol }, 2500)
        : Promise.resolve([]),
      fetchOkx("/api/v5/public/open-interest", { instType: symbol.includes("SWAP") ? "SWAP" : "FUTURES", instId: symbol }, 2500)
    ]);
    return {
      ok: true,
      source: "okx",
      indexPrice: Number(markRows[0]?.idxPx || markRows[0]?.markPx || 0),
      markPrice: Number(markRows[0]?.markPx || 0),
      fundingRate: Number(fundingRows[0]?.fundingRate || 0),
      nextFundingTime: fundingRows[0]?.nextFundingTime ? new Date(Number(fundingRows[0].nextFundingTime)).toISOString() : "",
      openInterest: Number(oiRows[0]?.oi || 0)
    };
  } catch (error) {
    const quote = await getLatestTicker(symbol);
    const last = quote.ticker.last;
    return {
      ok: true,
      source: "mock",
      indexPrice: Number((last * 0.9996).toFixed(4)),
      markPrice: Number((last * 1.0001).toFixed(4)),
      fundingRate: Number((Math.sin(Date.now() / 600000) * 0.00018).toFixed(6)),
      nextFundingTime: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
      openInterest: 120000 + Math.round(Math.abs(Math.sin(Date.now() / 100000)) * 90000),
      error: error.message
    };
  }
}

async function getLatestTicker(symbol = "BTC-USDT") {
  try {
    const data = await fetchOkx("/api/v5/market/ticker", { instId: symbol }, 2500);
    const ticker = normalizeTicker(data[0] || {}, symbol.includes("SWAP") ? "SWAP" : "SPOT");
    return { ok: true, source: "okx", ticker, updatedAt: new Date().toISOString() };
  } catch (error) {
    return {
      ok: true,
      source: "mock",
      ticker: latestMockTicker(symbol),
      error: error.message,
      updatedAt: new Date().toISOString()
    };
  }
}

function templateName(templateId) {
  return strategyTemplates.find(item => item.id === templateId)?.name || "自定义策略";
}

function normalizeProfile(input = {}, current = {}) {
  const symbol = String(input.symbol || current.symbol || "BTC-USDT").trim().toUpperCase();
  const anchorPrice = clamp(input.anchorPrice ?? current.anchorPrice ?? 0, 0, 1_000_000_000);
  const upperAnchor = clamp(input.upperAnchor ?? current.upperAnchor ?? anchorPrice * 1.03, 0, 1_000_000_000);
  const lowerAnchor = clamp(input.lowerAnchor ?? current.lowerAnchor ?? anchorPrice * 0.97, 0, 1_000_000_000);
  return {
    symbol,
    templateId: input.templateId || current.templateId || "ma_trend",
    anchorPrice,
    upperAnchor,
    lowerAnchor,
    maxCapitalPct: clamp(input.maxCapitalPct ?? current.maxCapitalPct ?? 5, 1, 30),
    positionSide: input.positionSide || current.positionSide || "flat",
    status: input.status || current.status || "观察",
    enabled: Boolean(input.enabled ?? current.enabled ?? true)
  };
}

function evaluateProfile(profile, ticker) {
  const price = Number(ticker.last || 0);
  const template = profile.templateId;
  let action = "等待";
  let reason = "价格未触发锚点条件";
  let nextStatus = "观察";

  if (!profile.enabled) {
    return { action: "停用", reason: "该品种自动策略已关闭", status: "停用" };
  }

  if (price <= 0) {
    return { action: "等待", reason: "没有有效实时价格", status: "等待行情" };
  }

  if (template === "martingale") {
    if (price <= profile.lowerAnchor) {
      action = "模拟加仓";
      reason = `价格跌破下方锚点 ${profile.lowerAnchor}，马丁策略进入分批加仓观察`;
      nextStatus = "高风险观察";
    } else if (price >= profile.anchorPrice) {
      action = "模拟减仓";
      reason = `价格回到中心锚点 ${profile.anchorPrice} 附近，马丁策略尝试降低风险`;
      nextStatus = "回到锚点";
    }
  } else if (template === "anti_martingale") {
    if (price >= profile.upperAnchor) {
      action = "模拟顺势加仓";
      reason = `价格突破上方锚点 ${profile.upperAnchor}，反马丁策略跟随盈利方向`;
      nextStatus = "趋势跟随";
    } else if (price <= profile.lowerAnchor) {
      action = "模拟减仓";
      reason = `价格跌破下方锚点 ${profile.lowerAnchor}，反马丁策略降低仓位`;
      nextStatus = "防守";
    }
  } else if (template === "livermore") {
    if (price >= profile.upperAnchor) {
      action = "模拟突破买入";
      reason = `价格突破关键锚点 ${profile.upperAnchor}，利弗莫尔突破策略试探建仓`;
      nextStatus = "突破试仓";
    } else if (price <= profile.lowerAnchor) {
      action = "模拟止损/不入场";
      reason = `价格跌破防守锚点 ${profile.lowerAnchor}，不追单并控制试错成本`;
      nextStatus = "防守";
    }
  } else if (template === "spot_grid") {
    if (price <= profile.lowerAnchor) {
      action = "模拟网格买入";
      reason = `价格触达网格下沿 ${profile.lowerAnchor}`;
      nextStatus = "网格买入区";
    } else if (price >= profile.upperAnchor) {
      action = "模拟网格卖出";
      reason = `价格触达网格上沿 ${profile.upperAnchor}`;
      nextStatus = "网格卖出区";
    }
  } else if (template === "dca") {
    action = "等待定投周期";
    reason = `围绕锚点 ${profile.anchorPrice} 记录长期配置价格`;
    nextStatus = "定投观察";
  } else if (price >= profile.upperAnchor) {
    action = "模拟买入";
    reason = `价格突破上方锚点 ${profile.upperAnchor}`;
    nextStatus = "触发";
  } else if (price <= profile.lowerAnchor) {
    action = "模拟止损";
    reason = `价格跌破下方锚点 ${profile.lowerAnchor}`;
    nextStatus = "防守";
  }

  return { action, reason, status: nextStatus };
}

async function runAutomationTick(symbolFilter = "") {
  const profiles = state.automation.profiles.map(profile => normalizeProfile(profile));
  const decisions = [];
  for (const profile of profiles) {
    if (symbolFilter && profile.symbol !== symbolFilter) continue;
    const quote = await getLatestTicker(profile.symbol);
    const decision = evaluateProfile(profile, quote.ticker);
    profile.status = decision.status;
    decisions.push({
      time: new Date().toISOString(),
      symbol: profile.symbol,
      strategy: templateName(profile.templateId),
      action: decision.action,
      price: quote.ticker.last,
      reason: decision.reason,
      source: quote.source,
      dryRun: true
    });
  }
  state.automation.profiles = profiles;
  state.automation.decisions = [...decisions, ...state.automation.decisions].slice(0, 80);
  saveState();
  return decisions;
}

function stripTags(value = "") {
  return String(value)
    .replace(/<!\[CDATA\[(.*?)\]\]>/gs, "$1")
    .replace(/<[^>]+>/g, "")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, "\"")
    .replace(/&#39;/g, "'")
    .trim();
}

function parseRssItems(xml, sourceName, keywords) {
  const items = [...String(xml).matchAll(/<item\b[\s\S]*?<\/item>/gi)].slice(0, 30);
  return items.map(match => {
    const raw = match[0];
    const read = tag => stripTags(raw.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`, "i"))?.[1] || "");
    const title = read("title");
    const summary = read("description");
    const text = `${title} ${summary}`.toLowerCase();
    const matched = keywords.filter(keyword => text.includes(keyword.toLowerCase()));
    return {
      source: sourceName,
      title,
      link: read("link"),
      publishedAt: read("pubDate") || read("published"),
      summary: summary.slice(0, 180),
      matched
    };
  }).filter(item => item.title && (keywords.length === 0 || item.matched.length > 0));
}

function fallbackNews(keywords) {
  const now = new Date().toISOString();
  return [
    {
      source: "本地提示",
      title: "等待联网后获取盘面相关新闻",
      link: "",
      publishedAt: now,
      summary: `当前会根据 ${keywords.join("、") || "BTC、ETH、SOL"} 等关键词过滤新闻。联网后会自动刷新。`,
      matched: keywords
    },
    {
      source: "风险提示",
      title: "自动交易不应只依赖新闻标题",
      link: "",
      publishedAt: now,
      summary: "新闻只作为交易侧参考，自动策略仍以行情、锚点和风控为准。",
      matched: []
    }
  ];
}

async function getMarketNews(symbols = ["BTC-USDT"], limit = 12) {
  const keywords = [...new Set(symbols.flatMap(symbol => {
    const base = symbol.split("-")[0];
    if (base === "BTC") return ["BTC", "Bitcoin"];
    if (base === "ETH") return ["ETH", "Ethereum"];
    if (base === "SOL") return ["SOL", "Solana"];
    return [base];
  }))];
  const results = [];
  const errors = [];
  await Promise.all(newsSources.map(async source => {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 6500);
      const response = await fetch(source.url, { signal: controller.signal, headers: { "Accept": "application/rss+xml,text/xml" } });
      clearTimeout(timer);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const xml = await response.text();
      results.push(...parseRssItems(xml, source.name, keywords));
    } catch (error) {
      errors.push(`${source.name}: ${error.message}`);
    }
  }));
  return {
    ok: true,
    source: results.length ? "rss" : "mock",
    errors,
    keywords,
    news: results.length ? results.slice(0, limit) : fallbackNews(keywords).slice(0, limit),
    updatedAt: new Date().toISOString()
  };
}

function mockTickers(instType = "SPOT", limit = 24) {
  const baseRows = Object.keys(symbols).map((instId, index) => {
    const candles = generateCandles(instId, 28, index * 11);
    const first = candles[0].close;
    const last = candles[candles.length - 1].close;
    const suffix = instType === "SPOT" ? instId : `${instId}-SWAP`;
    return {
      instType,
      instTypeLabel: instTypeLabel(instType),
      instId: suffix,
      last,
      bidPx: Number((last * 0.9998).toFixed(4)),
      askPx: Number((last * 1.0002).toFixed(4)),
      high24h: Math.max(...candles.map(item => item.high)),
      low24h: Math.min(...candles.map(item => item.low)),
      vol24h: 8000 + index * 2500,
      volCcy24h: 18000000 + index * 7200000,
      changePct: Number((((last - first) / first) * 100).toFixed(2)),
      ts: Date.now()
    };
  });
  return baseRows.slice(0, limit);
}

async function getOkxTickers(instType = "SPOT", limit = 30) {
  const data = await fetchOkx("/api/v5/market/tickers", { instType });
  return data
    .map(row => normalizeTicker(row, instType))
    .filter(row => row.instId && row.last > 0)
    .sort((a, b) => b.volCcy24h - a.volCcy24h)
    .slice(0, limit);
}

async function getMarketSnapshot(instTypes = ["SPOT", "SWAP", "FUTURES"], limit = 18) {
  const groups = {};
  const errors = [];
  await Promise.all(instTypes.map(async instType => {
    try {
      groups[instType] = await getOkxTickers(instType, limit);
    } catch (error) {
      errors.push(`${instType}: ${error.message}`);
      groups[instType] = mockTickers(instType, limit);
    }
  }));
  return {
    ok: true,
    source: errors.length === instTypes.length ? "mock" : errors.length ? "mixed" : "okx",
    updatedAt: new Date().toISOString(),
    errors,
    groups
  };
}

async function getOkxCandles(symbol, limit = 180, timeframe = "1h") {
  const data = await fetchOkx("/api/v5/market/candles", {
    instId: symbol,
    bar: okxBar(timeframe),
    limit
  });
  return data.reverse().map(row => ({
    time: new Date(Number(row[0])).toISOString(),
    open: Number(row[1]),
    high: Number(row[2]),
    low: Number(row[3]),
    close: Number(row[4]),
    volume: Number(row[5] || 0),
    confirm: row[8] === "1"
  }));
}

async function getOkxHistoryCandles(symbol, limit = 300, timeframe = "1h", before = "") {
  const params = {
    instId: symbol,
    bar: okxBar(timeframe),
    limit
  };
  if (before) params.before = before;
  const data = await fetchOkx("/api/v5/market/history-candles", params, 9000);
  return data.map(row => ({
    time: new Date(Number(row[0])).toISOString(),
    ts: Number(row[0]),
    open: Number(row[1]),
    high: Number(row[2]),
    low: Number(row[3]),
    close: Number(row[4]),
    volume: Number(row[5] || 0),
    confirm: row[8] === "1"
  }));
}

async function importHistoricalCandles({ symbol = "BTC-USDT", timeframe = "1h", years = 1 } = {}) {
  const safeYears = Math.round(clamp(years, 1, 10));
  const interval = timeframeMs(timeframe);
  const target = Math.min(20000, Math.ceil((safeYears * 365 * 24 * 60 * 60 * 1000) / interval));
  const pages = Math.ceil(target / 300);
  const candles = [];
  let before = "";
  let source = "okx";
  let error = "";

  try {
    for (let page = 0; page < pages; page += 1) {
      const rows = await getOkxHistoryCandles(symbol, Math.min(300, target - candles.length), timeframe, before);
      if (!rows.length) break;
      candles.push(...rows);
      before = String(Math.min(...rows.map(row => row.ts)));
      if (candles.length >= target) break;
    }
  } catch (err) {
    source = "mock";
    error = err.message;
    candles.length = 0;
    const mock = generateCandles(symbol.replace("-SWAP", ""), target, Date.now() / 1000);
    candles.push(...mock.map((row, index) => ({
      ...row,
      ts: Date.now() - (target - index) * interval
    })));
  }

  candles.sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());
  if (!existsSync(historyDir)) mkdirSync(historyDir, { recursive: true });
  const fileName = historyFileName(symbol, timeframe, safeYears);
  const filePath = path.join(historyDir, fileName);
  const payload = {
    symbol,
    timeframe,
    years: safeYears,
    source,
    error,
    count: candles.length,
    importedAt: new Date().toISOString(),
    candles
  };
  writeFileSync(filePath, JSON.stringify(payload, null, 2), "utf8");
  return { ...payload, fileName, candles: undefined };
}

async function getOkxInstruments(instType = "SPOT", limit = 80) {
  const data = await fetchOkx("/api/v5/public/instruments", { instType });
  return data
    .filter(row => row.state === "live")
    .map(normalizeInstrument)
    .slice(0, limit);
}

function runMovingAverageBacktest(config) {
  const symbol = config.symbol || state.strategy.symbol;
  const initialBalance = clamp(config.initialBalance || 10000, 100, 10_000_000);
  const shortMa = Math.round(clamp(config.shortMa || state.strategy.shortMa, 3, 200));
  const longMa = Math.round(clamp(config.longMa || state.strategy.longMa, shortMa + 1, 400));
  const allocationPct = clamp(config.allocationPct || state.strategy.allocationPct, 1, 100) / 100;
  const stopLossPct = clamp(config.stopLossPct || state.strategy.stopLossPct, 0.5, 80) / 100;
  const feeRate = clamp(config.feeRate || 0.0008, 0, 0.02);
  const candles = Array.isArray(config.candles) && config.candles.length > longMa + 5
    ? config.candles
    : generateCandles(symbol, 260);
  const closes = candles.map(candle => candle.close);
  let cash = initialBalance;
  let qty = 0;
  let entryPrice = 0;
  let fees = 0;
  let peak = initialBalance;
  let maxDrawdown = 0;
  let lastShort = null;
  let lastLong = null;
  let currentLosingStreak = 0;
  let maxLosingStreak = 0;
  const equityCurve = [];
  const trades = [];

  for (let i = longMa; i < candles.length; i += 1) {
    const candle = candles[i];
    const price = candle.close;
    const short = average(closes.slice(i - shortMa, i));
    const long = average(closes.slice(i - longMa, i));
    const equity = cash + qty * price;
    const crossUp = lastShort !== null && lastShort <= lastLong && short > long;
    const crossDown = lastShort !== null && lastShort >= lastLong && short < long;
    const stopLossHit = qty > 0 && price <= entryPrice * (1 - stopLossPct);

    if (qty === 0 && crossUp && !state.risk.paused) {
      const spend = cash * allocationPct;
      const fee = spend * feeRate;
      qty = (spend - fee) / price;
      cash -= spend;
      entryPrice = price;
      fees += fee;
      trades.push({
        time: candle.time,
        side: "买入",
        price: Number(price.toFixed(2)),
        qty: Number(qty.toFixed(6)),
        reason: `MA${shortMa} 上穿 MA${longMa}`,
        pnl: null
      });
    } else if (qty > 0 && (crossDown || stopLossHit)) {
      const gross = qty * price;
      const fee = gross * feeRate;
      const cost = qty * entryPrice;
      const pnl = gross - fee - cost;
      cash += gross - fee;
      fees += fee;
      trades.push({
        time: candle.time,
        side: "卖出",
        price: Number(price.toFixed(2)),
        qty: Number(qty.toFixed(6)),
        reason: stopLossHit ? "触发止损" : `MA${shortMa} 下穿 MA${longMa}`,
        pnl: Number(pnl.toFixed(2))
      });
      if (pnl < 0) {
        currentLosingStreak += 1;
        maxLosingStreak = Math.max(maxLosingStreak, currentLosingStreak);
      } else {
        currentLosingStreak = 0;
      }
      qty = 0;
      entryPrice = 0;
    }

    const markEquity = cash + qty * price;
    peak = Math.max(peak, markEquity);
    maxDrawdown = Math.max(maxDrawdown, peak === 0 ? 0 : (peak - markEquity) / peak);
    equityCurve.push({
      time: candle.time,
      equity: Number(markEquity.toFixed(2))
    });
    lastShort = short;
    lastLong = long;
  }

  const lastPrice = candles[candles.length - 1].close;
  const finalEquity = cash + qty * lastPrice;
  const closedTrades = trades.filter(trade => trade.side === "卖出");
  const wins = closedTrades.filter(trade => trade.pnl > 0).length;
  const returnPct = ((finalEquity - initialBalance) / initialBalance) * 100;

  return {
    ok: true,
    config: { symbol, initialBalance, shortMa, longMa, allocationPct: allocationPct * 100, stopLossPct: stopLossPct * 100 },
    metrics: {
      finalEquity: Number(finalEquity.toFixed(2)),
      returnPct: Number(returnPct.toFixed(2)),
      maxDrawdownPct: Number((maxDrawdown * 100).toFixed(2)),
      winRatePct: closedTrades.length ? Number(((wins / closedTrades.length) * 100).toFixed(1)) : 0,
      tradeCount: trades.length,
      maxLosingStreak,
      feeImpact: Number(fees.toFixed(2))
    },
    candles,
    equityCurve,
    trades: trades.slice(-12),
    beginnerNote: returnPct > 0 && maxDrawdown < 0.1
      ? "回测结果可以进入模拟盘观察，但不能代表未来收益。"
      : "当前参数风险偏高，建议降低仓位或延长均线周期。"
  };
}

function strategyBias(templateId, closes) {
  const first = closes[0] || 1;
  const last = closes[closes.length - 1] || first;
  const trend = (last - first) / first;
  const volatility = closes.reduce((sum, close, index) => {
    if (index === 0) return sum;
    return sum + Math.abs((close - closes[index - 1]) / closes[index - 1]);
  }, 0) / Math.max(1, closes.length - 1);

  const profile = {
    ma_trend: { trend: 1.2, vol: -0.2, risk: 0.55 },
    spot_grid: { trend: -0.15, vol: 1.05, risk: 0.48 },
    dca: { trend: 0.48, vol: -0.1, risk: 0.28 },
    martingale: { trend: -0.1, vol: 1.35, risk: 0.92 },
    anti_martingale: { trend: 1.35, vol: 0.12, risk: 0.72 },
    livermore: { trend: 1.55, vol: 0.28, risk: 0.76 },
    rsi_reversal: { trend: -0.3, vol: 1.18, risk: 0.86 }
  }[templateId] || { trend: 0.5, vol: 0.2, risk: 0.5 };

  const raw = trend * profile.trend + volatility * profile.vol;
  const returnPct = raw * 100 - profile.risk * 1.8;
  const maxDrawdownPct = Math.max(1.2, profile.risk * 14 + volatility * 220);
  const winRatePct = Math.max(24, Math.min(72, 48 + trend * 520 + volatility * 180 - profile.risk * 8));
  const score = Math.max(0, Math.min(100, 58 + returnPct * 1.7 - maxDrawdownPct * 1.25 + winRatePct * 0.25));

  let signal = "观察";
  if (templateId === "livermore" && trend > 0.012) signal = "突破试仓";
  else if (templateId === "anti_martingale" && trend > 0.008) signal = "顺势加仓";
  else if (templateId === "spot_grid" && volatility > 0.006 && Math.abs(trend) < 0.018) signal = "网格运行";
  else if (templateId === "martingale" && trend < -0.01) signal = "高风险加仓区";
  else if (templateId === "rsi_reversal" && trend < -0.012) signal = "反弹观察";
  else if (templateId === "dca") signal = "定投可执行";
  else if (templateId === "ma_trend" && trend > 0.006) signal = "趋势持有";

  return {
    returnPct: Number(returnPct.toFixed(2)),
    maxDrawdownPct: Number(maxDrawdownPct.toFixed(2)),
    winRatePct: Number(winRatePct.toFixed(1)),
    score: Number(score.toFixed(0)),
    signal,
    trendPct: Number((trend * 100).toFixed(2)),
    volatilityPct: Number((volatility * 100).toFixed(2))
  };
}

async function compareStrategies(symbol = "BTC-USDT", timeframe = "1m") {
  let candles;
  let source = "okx";
  try {
    candles = await getOkxCandles(symbol, 180, timeframe);
  } catch (error) {
    candles = generateCandles(symbol.replace("-SWAP", ""), 180, Date.now() / 1000);
    source = "mock";
  }
  const closes = candles.map(item => item.close);
  const results = strategyTemplates.map(template => {
    const metrics = strategyBias(template.id, closes);
    return {
      ...template,
      ...metrics,
      adopted: state.strategy.templateId === template.id && state.strategy.symbol === symbol
    };
  }).sort((a, b) => b.score - a.score);

  return {
    ok: true,
    source,
    symbol,
    timeframe,
    updatedAt: new Date().toISOString(),
    market: {
      last: closes[closes.length - 1],
      trendPct: results[0]?.trendPct || 0,
      volatilityPct: results[0]?.volatilityPct || 0
    },
    results,
    candles
  };
}

function nextPaperEvent() {
  const minutes = 9 + state.paper.events.length * 17;
  const hour = String(9 + Math.floor(minutes / 60)).padStart(2, "0");
  const minute = String(minutes % 60).padStart(2, "0");
  const variants = [
    {
      title: `${state.strategy.name} 风控检查通过`,
      detail: `资金占用 ${state.strategy.allocationPct}%，止损 ${state.strategy.stopLossPct}% 已开启`,
      result: "正常",
      tone: "blue",
      pnl: 4.6
    },
    {
      title: `${state.strategy.symbol} 触发观察信号`,
      detail: `短期均线接近长期均线，暂未下单`,
      result: "等待",
      tone: "amber",
      pnl: -2.1
    },
    {
      title: `${state.strategy.name} 更新模拟权益`,
      detail: `按最新行情重新估算持仓盈亏`,
      result: "+6.8 USDT",
      tone: "green",
      pnl: 6.8
    }
  ];
  const item = variants[state.paper.events.length % variants.length];
  state.paper.equity = Number((state.paper.equity + item.pnl).toFixed(2));
  state.dashboard.equity = state.paper.equity;
  state.dashboard.dailyPnl = Number((state.dashboard.dailyPnl + item.pnl).toFixed(2));
  state.paper.day = Math.min(7, state.paper.day + (state.paper.events.length % 3 === 2 ? 1 : 0));
  const event = { time: `${hour}:${minute}`, title: item.title, detail: item.detail, result: item.result, tone: item.tone };
  state.paper.events.unshift(event);
  state.paper.events = state.paper.events.slice(0, 8);
  return event;
}

async function handleApi(req, res, url) {
  if (req.method === "GET" && url.pathname === "/api/health") {
    json(res, { ok: true, name: "OKX Quant Desk", mode: "demo", time: new Date().toISOString() });
    return;
  }

  if (req.method === "GET" && url.pathname === "/api/state") {
    json(res, { ok: true, state });
    return;
  }

  if (req.method === "GET" && url.pathname === "/api/strategies/templates") {
    json(res, { ok: true, templates: strategyTemplates });
    return;
  }

  if (req.method === "GET" && url.pathname === "/api/strategies/compare") {
    const symbol = url.searchParams.get("symbol") || state.strategy.symbol || "BTC-USDT";
    const timeframe = url.searchParams.get("timeframe") || "1m";
    json(res, await compareStrategies(symbol, timeframe));
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/strategies/adopt") {
    const body = await readBody(req);
    const template = strategyTemplates.find(item => item.id === body.templateId);
    if (!template) {
      badRequest(res, "策略模板不存在");
      return;
    }
    state.strategy.templateId = template.id;
    state.strategy.name = template.name;
    state.strategy.symbol = body.symbol || state.strategy.symbol;
    const existing = state.automation.profiles.find(item => item.symbol === state.strategy.symbol);
    if (existing) {
      existing.templateId = template.id;
      existing.status = "已采用";
    } else {
      state.automation.profiles.unshift(normalizeProfile({
        symbol: state.strategy.symbol,
        templateId: template.id,
        anchorPrice: body.anchorPrice || 0,
        upperAnchor: body.upperAnchor || 0,
        lowerAnchor: body.lowerAnchor || 0,
        maxCapitalPct: 5,
        enabled: true,
        status: "已采用"
      }));
    }
    state.automation.decisions.unshift({
      time: new Date().toISOString(),
      symbol: state.strategy.symbol,
      strategy: template.name,
      action: "采用策略",
      price: Number(body.price || 0),
      reason: `已将 ${template.name} 设为当前 ${state.strategy.symbol} 的候选策略`,
      dryRun: true
    });
    state.automation.decisions = state.automation.decisions.slice(0, 80);
    saveState();
    json(res, { ok: true, strategy: state.strategy, automation: state.automation, message: `已采用 ${template.name}` });
    return;
  }

  if (req.method === "GET" && url.pathname === "/api/live/ticker") {
    const symbol = url.searchParams.get("symbol") || "BTC-USDT";
    json(res, await getLatestTicker(symbol));
    return;
  }

  if (req.method === "GET" && url.pathname === "/api/live/orderbook") {
    const symbol = url.searchParams.get("symbol") || "BTC-USDT";
    const depth = Number(url.searchParams.get("depth") || 18);
    json(res, await getOrderBook(symbol, clamp(depth, 5, 50)));
    return;
  }

  if (req.method === "GET" && url.pathname === "/api/live/trades") {
    const symbol = url.searchParams.get("symbol") || "BTC-USDT";
    const limit = Number(url.searchParams.get("limit") || 24);
    json(res, await getRecentTrades(symbol, clamp(limit, 5, 80)));
    return;
  }

  if (req.method === "GET" && url.pathname === "/api/live/terminal") {
    const symbol = url.searchParams.get("symbol") || "BTC-USDT";
    const timeframe = url.searchParams.get("timeframe") || "1m";
    const [ticker, book, trades, derivative] = await Promise.all([
      getLatestTicker(symbol),
      getOrderBook(symbol, 18),
      getRecentTrades(symbol, 24),
      getDerivativeMeta(symbol)
    ]);
    let candles;
    let candleSource = "okx";
    try {
      candles = await getOkxCandles(symbol, 120, timeframe);
    } catch {
      candles = generateCandles(symbol.replace("-SWAP", ""), 120, Date.now() / 1000);
      candleSource = "mock";
    }
    json(res, {
      ok: true,
      symbol,
      timeframe,
      source: ticker.source === "okx" || book.source === "okx" || trades.source === "okx" ? "okx" : "mock",
      ticker,
      book,
      trades,
      derivative,
      candles,
      candleSource,
      updatedAt: new Date().toISOString()
    });
    return;
  }

  if (req.method === "GET" && url.pathname === "/api/news") {
    const symbolsParam = url.searchParams.get("symbols") || state.automation.profiles.map(item => item.symbol).join(",");
    const symbolsList = symbolsParam.split(",").map(item => item.trim()).filter(Boolean);
    const limit = Number(url.searchParams.get("limit") || 12);
    json(res, await getMarketNews(symbolsList, clamp(limit, 3, 30)));
    return;
  }

  if (req.method === "GET" && url.pathname === "/api/automation/status") {
    json(res, { ok: true, automation: state.automation });
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/automation/config") {
    const body = await readBody(req);
    const profiles = Array.isArray(body.profiles) ? body.profiles : [];
    state.automation.profiles = profiles.length
      ? profiles.map((profile, index) => normalizeProfile(profile, state.automation.profiles[index] || {}))
      : state.automation.profiles;
    state.automation.refreshSeconds = Math.round(clamp(body.refreshSeconds || state.automation.refreshSeconds, 2, 60));
    state.automation.dryRun = true;
    state.automation.liveTradingLocked = true;
    saveState();
    json(res, { ok: true, automation: state.automation, message: "自动交易配置已保存，当前仍为模拟运行。" });
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/automation/start") {
    state.automation.running = true;
    state.automation.dryRun = true;
    state.automation.liveTradingLocked = true;
    const decisions = await runAutomationTick();
    json(res, { ok: true, automation: state.automation, decisions });
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/automation/stop") {
    state.automation.running = false;
    saveState();
    json(res, { ok: true, automation: state.automation });
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/automation/tick") {
    const body = await readBody(req);
    const decisions = await runAutomationTick(body.symbol || "");
    json(res, { ok: true, automation: state.automation, decisions });
    return;
  }

  if (req.method === "GET" && url.pathname === "/api/okx/markets") {
    const requested = (url.searchParams.get("instTypes") || "SPOT,SWAP,FUTURES")
      .split(",")
      .map(item => item.trim().toUpperCase())
      .filter(Boolean);
    const limit = Number(url.searchParams.get("limit") || 18);
    const snapshot = await getMarketSnapshot(requested, clamp(limit, 3, 80));
    state.market.source = snapshot.source;
    state.market.updatedAt = snapshot.updatedAt;
    saveState();
    json(res, snapshot);
    return;
  }

  if (req.method === "GET" && url.pathname === "/api/okx/instruments") {
    const instType = (url.searchParams.get("instType") || "SPOT").toUpperCase();
    const limit = Number(url.searchParams.get("limit") || 80);
    try {
      const instruments = await getOkxInstruments(instType, clamp(limit, 10, 200));
      json(res, { ok: true, source: "okx", instType, instruments, updatedAt: new Date().toISOString() });
    } catch (error) {
      json(res, {
        ok: true,
        source: "mock",
        instType,
        instruments: mockTickers(instType, clamp(limit, 3, 40)).map(row => ({
          instType,
          instTypeLabel: instTypeLabel(instType),
          instId: row.instId,
          baseCcy: row.instId.split("-")[0],
          quoteCcy: "USDT",
          settleCcy: instType === "SPOT" ? "" : "USDT",
          ctVal: instType === "SPOT" ? "" : "0.01",
          ctType: instType === "SPOT" ? "" : "linear",
          state: "mock",
          tickSz: "",
          lotSz: "",
          minSz: "",
          lever: instType === "SPOT" ? "" : "locked"
        })),
        error: error.message,
        updatedAt: new Date().toISOString()
      });
    }
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/history/import") {
    const body = await readBody(req);
    const result = await importHistoricalCandles({
      symbol: body.symbol || "BTC-USDT",
      timeframe: body.timeframe || "1h",
      years: Number(body.years || 1)
    });
    json(res, { ok: true, result });
    return;
  }

  if (req.method === "GET" && url.pathname === "/api/history/files") {
    if (!existsSync(historyDir)) mkdirSync(historyDir, { recursive: true });
    const files = readdirSync(historyDir)
      .filter(file => file.endsWith(".json"))
      .map(file => {
        const full = path.join(historyDir, file);
        const stat = statSync(full);
        return { file, size: stat.size, updatedAt: stat.mtime.toISOString() };
      });
    json(res, { ok: true, files });
    return;
  }

  if (req.method === "GET" && url.pathname === "/api/market") {
    const symbol = url.searchParams.get("symbol") || state.strategy.symbol;
    const limit = Number(url.searchParams.get("limit") || 160);
    const timeframe = url.searchParams.get("timeframe") || state.strategy.timeframe || "1h";
    try {
      const candles = await getOkxCandles(symbol, clamp(limit, 40, 300), timeframe);
      json(res, { ok: true, source: "okx", symbol, timeframe, candles, updatedAt: new Date().toISOString() });
    } catch (error) {
      json(res, {
        ok: true,
        source: "mock",
        symbol,
        timeframe,
        candles: generateCandles(symbol, clamp(limit, 40, 360)),
        error: error.message,
        updatedAt: new Date().toISOString()
      });
    }
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/account/test") {
    const body = await readBody(req);
    state.account = {
      ...state.account,
      connected: true,
      apiKeyMasked: maskKey(body.apiKey || "demo-api-key"),
      environment: body.environment === "live" ? "live-preview" : "demo",
      readPermission: true,
      tradePermission: Boolean(body.tradePermission),
      withdrawPermission: false,
      lastTestAt: new Date().toISOString()
    };
    saveState();
    json(res, {
      ok: true,
      account: state.account,
      message: "连接测试已通过。当前仍处于模拟盘，不会动用真实资金。"
    });
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/strategy") {
    const body = await readBody(req);
    const template = strategyTemplates.find(item => item.id === body.templateId) || strategyTemplates[0];
    const next = {
      ...state.strategy,
      templateId: template.id,
      name: template.name,
      symbol: body.symbol || state.strategy.symbol,
      shortMa: Math.round(clamp(body.shortMa, 3, 200)),
      longMa: Math.round(clamp(body.longMa, Math.round(clamp(body.shortMa, 3, 200)) + 1, 400)),
      allocationPct: clamp(body.allocationPct, 1, 30),
      stopLossPct: clamp(body.stopLossPct, 0.5, 30),
      timeframe: body.timeframe || state.strategy.timeframe
    };
    state.strategy = next;
    state.risk.strategyCapitalPct = next.allocationPct;
    state.risk.totalCapitalPct = Math.min(30, 8 + next.allocationPct);
    saveState();
    json(res, { ok: true, strategy: state.strategy, risk: state.risk });
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/backtest") {
    const body = await readBody(req);
    let result;
    try {
      const liveCandles = await getOkxCandles(body.symbol || state.strategy.symbol, 260, body.timeframe || state.strategy.timeframe || "1h");
      result = runMovingAverageBacktest({ ...body, candles: liveCandles });
      result.source = "okx";
    } catch (error) {
      result = runMovingAverageBacktest(body);
      result.source = "mock";
      result.sourceError = error.message;
    }
    json(res, result);
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/paper/start") {
    state.paper.running = true;
    state.risk.paused = false;
    const event = {
      time: new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false }),
      title: "模拟策略已启动",
      detail: `${state.strategy.symbol} 使用 ${state.strategy.allocationPct}% 模拟资金，实盘仍锁定`,
      result: "运行中",
      tone: "green"
    };
    state.paper.events.unshift(event);
    state.paper.events = state.paper.events.slice(0, 8);
    saveState();
    json(res, { ok: true, state, event });
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/paper/tick") {
    if (state.risk.paused || !state.paper.running) {
      json(res, { ok: false, paused: true, state, message: "模拟盘未运行或已暂停。" }, 409);
      return;
    }
    const event = nextPaperEvent();
    saveState();
    json(res, { ok: true, state, event });
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/risk/pause-all") {
    state.paper.running = false;
    state.risk.paused = true;
    state.paper.events.unshift({
      time: new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false }),
      title: "已暂停全部策略",
      detail: "全局风控触发，模拟盘和未来实盘任务均停止下单",
      result: "已暂停",
      tone: "red"
    });
    state.paper.events = state.paper.events.slice(0, 8);
    saveState();
    json(res, { ok: true, state });
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/risk/resume-demo") {
    state.risk.paused = false;
    state.paper.running = true;
    saveState();
    json(res, { ok: true, state });
    return;
  }

  json(res, { ok: false, error: "接口不存在" }, 404);
}

const mime = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml; charset=utf-8",
  ".ico": "image/x-icon"
};

function serveStatic(res, pathname) {
  const cleanPath = decodeURIComponent(pathname === "/" ? "/index.html" : pathname);
  const requested = path.normalize(path.join(publicDir, cleanPath));
  if (!requested.startsWith(publicDir)) {
    json(res, { ok: false, error: "非法路径" }, 403);
    return;
  }
  if (!existsSync(requested)) {
    const fallback = path.join(publicDir, "index.html");
    res.writeHead(200, { "Content-Type": mime[".html"] });
    createReadStream(fallback).pipe(res);
    return;
  }
  const ext = path.extname(requested);
  res.writeHead(200, { "Content-Type": mime[ext] || "application/octet-stream" });
  createReadStream(requested).pipe(res);
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url || "/", "http://127.0.0.1");
  try {
    if (url.pathname.startsWith("/api/")) {
      await handleApi(req, res, url);
      return;
    }
    if (req.method !== "GET") {
      badRequest(res, "只支持 GET 静态文件请求");
      return;
    }
    serveStatic(res, url.pathname);
  } catch (error) {
    json(res, { ok: false, error: error.message || "服务内部错误" }, 500);
  }
});

function runSmokeTest() {
  const market = generateCandles("BTC-USDT", 80);
  const btcTicker = latestMockTicker("BTC-USDT");
  const ethTicker = latestMockTicker("ETH-USDT");
  const backtest = runMovingAverageBacktest({
    symbol: "BTC-USDT",
    shortMa: 20,
    longMa: 60,
    allocationPct: 10,
    stopLossPct: 3,
    initialBalance: 10000
  });
  const event = nextPaperEvent();

  if (market.length !== 80) throw new Error("行情生成数量不正确");
  if (btcTicker.last < 10_000 || btcTicker.last > 200_000) throw new Error(`BTC 兜底价格异常: ${btcTicker.last}`);
  if (ethTicker.last < 500 || ethTicker.last > 20_000) throw new Error(`ETH 兜底价格异常: ${ethTicker.last}`);
  if (!backtest.ok) throw new Error("回测未返回成功状态");
  if (!Number.isFinite(backtest.metrics.finalEquity)) throw new Error("回测最终权益异常");
  if (!event.title) throw new Error("模拟盘事件生成失败");

  console.log(JSON.stringify({
    ok: true,
    marketCandles: market.length,
    btcMockPrice: btcTicker.last,
    ethMockPrice: ethTicker.last,
    backtestTrades: backtest.metrics.tradeCount,
    finalEquity: backtest.metrics.finalEquity,
    returnPct: backtest.metrics.returnPct,
    paperEvent: event.title
  }, null, 2));
}

function listen(port, attempts = 0) {
  server.once("error", error => {
    if (error.code === "EADDRINUSE" && attempts < 20) {
      listen(port + 1, attempts + 1);
      return;
    }
    console.error(error);
    process.exit(1);
  });

  server.listen(port, "127.0.0.1", () => {
    const address = server.address();
    const localUrl = `http://127.0.0.1:${address.port}`;
    writeFileSync(urlFile, localUrl, "utf8");
    console.log(`OKX Quant Desk 已启动: ${localUrl}`);
  });
}

if (process.argv.includes("--smoke-test")) {
  runSmokeTest();
} else {
  listen(preferredPort);
}
