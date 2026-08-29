const state = {
  symbol: "AAPL",
  bar: "1Dutc",
  chartMode: "candles",
  candles: [],
  chartDataSymbol: "",
  chartCache: {},
  chartQualityBySymbol: {},
  trades: [],
  stockPriceLog: [],
  orderBook: { asks: [], bids: [] },
  strategies: [],
  paper: null,
  profile: null,
  lastPrice: 0,
  stockQuoteContext: null,
  orderFilter: "ALL",
  indicators: { ma: true, bollinger: false, volume: true, signals: true, volumeProfile: false, autoMarks: false },
  marketCategory: "all",
  stockSession: "regular",
  layout: "classic",
  socket: null,
  reconnectTimer: null,
  marketSocket: null,
  marketReconnectTimer: null,
  chartView: { offset: 0, visible: 420, dragging: false, dragX: 0, dragOffset: 0 },
  chartHover: null,
  chartMeta: null,
  chartQuality: null,
  chartCandleQuality: null,
  marketSession: null,
  marketSnapshotContext: null,
  drawingTool: "cursor",
  drawings: [],
  draftDrawing: null,
  chartAi: null,
  contract: {},
  strategyLab: null,
  strategyResearchEvidence: null,
  strategyResearchEvidenceCache: {},
  strategyBacktest: null,
  internalBacktestReturnQuality: null,
  internalBacktestReturnQualityLoaded: false,
  marketInsights: null,
  marketScanner: null,
  contractCenter: null,
  strategyCompare: null,
  strategyDoctor: null,
  strategyWarRoom: null,
  botCenter: null,
  botScheduler: null,
  research: null,
  anomalyRadar: null,
  anomalyFilter: "all",
  anomalyEvents: null,
  anomalyDetail: null,
  trendCockpit: null,
  selectedAnomaly: null,
  deepseek: null,
  marketAi: null,
  tradingAgents: null,
  tradingAgentsStatus: null,
  codeWorker: null,
  v2Platform: null,
  sixLane: null,
  fullConfig: null,
  dataReliability: null,
  dataCache: null,
  stockSourceControl: null,
  stockAsyncResearch: null,
  strategyRobotProfiles: null,
  platformControl: null,
  platformReplay: null,
  futu: null,
  futuDeep: null,
  sideInsight: "volatility",
  tradeFilter: "ALL",
  microSignal: null,
  latestStrategyAnalysis: null,
  activeStrategyPreset: null,
  interfaceView: (() => {
    try {
      const platformDefaultVersion = localStorage.getItem("hakimi.interface.platform_default_v2");
      if (!platformDefaultVersion) {
        localStorage.setItem("hakimi.interface.platform_default_v2", "1");
        localStorage.setItem("hakimi.interface.view", "platform");
        return "platform";
      }
      const stored = localStorage.getItem("hakimi.interface.view");
      if (["platform", "trade", "bot", "marketai", "research", "system", "all"].includes(stored)) return stored;
      localStorage.setItem("hakimi.interface.view", "platform");
    } catch (error) {
      return "platform";
    }
    return "platform";
  })(),
  desktop: { okxOnline: false, commandOpen: false, commandIndex: 0, mode: "PAPER", quoteSource: "AUTO", activeWorkspace: ".anomaly-workbench" },
  replay: { active: false, index: 0, timer: null },
};

const VALIDATED_STRATEGY_LEVERAGE = 1;

const runtime = {
  symbolVersion: 0,
  chartRequestSeq: 0,
  stockQuoteSeq: 0,
  stockQuoteInFlight: false,
  stockQuoteAbortController: null,
  stockQuoteAt: 0,
  stockQuoteSymbol: "",
  symbolTaskTimers: [],
  stockHistoryInFlightKey: "",
  stockHistoryPrewarmAt: 0,
  chartRequestAbortController: null,
  chartRequestKey: "",
  chartRefreshCoordinator: window.HakimiChartController.createRefreshCoordinator({
    successCooldownMs: 60_000,
    failureBaseCooldownMs: 5_000,
    failureMaxCooldownMs: 60_000,
  }),
  chartRefreshApplied: new Map(),
  marketListSignature: "",
  marketTickerSignature: "",
  stockPanelSignature: "",
  marketRenderTimer: null,
  marketRenderPricesOnly: true,
  chartPrewarmInFlight: new Set(),
  chartPrewarmDone: new Set(),
  stockStaleRefreshInFlight: new Set(),
  stockStaleRefreshAt: {},
  stockStaleRefreshStatus: {},
  platformControlInFlight: new Map(),
  anomalyRadarInFlight: false,
  anomalyRadarAt: 0,
  anomalyEventsInFlight: false,
  anomalyDetailSymbol: "",
  stockSourceControlSymbol: "",
  chartUserZoomed: false,
  forceMarketAiUntil: 0,
  tradingAgentsTranscriptSeq: 0,
  strategyLabRequestSeq: 0,
  tradingAgentsAbortController: null,
  lastDrawAt: 0,
  drawTimer: null,
  stockSessionEventsBound: false,
  interactionGuardBound: false,
  userInteractionStarted: false,
};

const WATCHLIST_PRIORITY = [
  "BTC-USDT", "ETH-USDT", "SOL-USDT", "BTC-USDT-SWAP", "ETH-USDT-SWAP",
  "NVDA", "AAPL", "MSFT", "GOOGL", "META", "AMZN", "TSLA",
  "AMD", "AVGO", "TSM", "ASML", "ARM", "AMAT", "QCOM", "SMCI",
  "MU", "WDC", "STX", "PSTG", "NTAP",
  "QQQ", "SPY", "MSTR", "RKLB", "ASTS",
  "HK.00002", "HK.00006", "HK.00836", "HK.00902", "HK.00916", "HK.02638",
];
const WATCHLIST_PRIORITY_MAP = new Map(WATCHLIST_PRIORITY.map((symbol, index) => [symbol, index]));

let markets = [
  { symbol: "BTC-USDT", instId: "BTC-USDT", name: "Bitcoin", category: "spot", type: "spot", source: "okx", price: "--", change: "--" },
  { symbol: "ETH-USDT", instId: "ETH-USDT", name: "Ethereum", category: "spot", type: "spot", source: "okx", price: "--", change: "--" },
  { symbol: "SOL-USDT", instId: "SOL-USDT", name: "Solana", category: "spot", type: "spot", source: "okx", price: "--", change: "--" },
  { symbol: "BNB-USDT", instId: "BNB-USDT", name: "BNB", category: "spot", type: "spot", source: "okx", price: "--", change: "--" },
  { symbol: "DOGE-USDT", instId: "DOGE-USDT", name: "Dogecoin", category: "spot", type: "spot", source: "okx", price: "--", change: "--" },
  { symbol: "BTC-USDT-SWAP", instId: "BTC-USDT-SWAP", name: "BTC Perpetual", category: "swap", type: "swap", source: "okx", price: "--", change: "--" },
  { symbol: "ETH-USDT-SWAP", instId: "ETH-USDT-SWAP", name: "ETH Perpetual", category: "swap", type: "swap", source: "okx", price: "--", change: "--" },
  { symbol: "SOL-USDT-SWAP", instId: "SOL-USDT-SWAP", name: "SOL Perpetual", category: "swap", type: "swap", source: "okx", price: "--", change: "--" },
  { symbol: "DOGE-USDT-SWAP", instId: "DOGE-USDT-SWAP", name: "DOGE Perpetual", category: "swap", type: "swap", source: "okx", price: "--", change: "--" },
  { symbol: "AAPL", instId: "AAPL", name: "Apple", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "MSFT", instId: "MSFT", name: "Microsoft", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "NVDA", instId: "NVDA", name: "Nvidia", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "AMZN", instId: "AMZN", name: "Amazon", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "GOOGL", instId: "GOOGL", name: "Alphabet", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "META", instId: "META", name: "Meta", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "TSLA", instId: "TSLA", name: "Tesla", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "MSTR", instId: "MSTR", name: "MicroStrategy", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "RKLB", instId: "RKLB", name: "Rocket Lab", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "ASTS", instId: "ASTS", name: "AST SpaceMobile", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "SPY", instId: "SPY", name: "S&P 500 ETF", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "QQQ", instId: "QQQ", name: "Nasdaq 100 ETF", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "AMD", instId: "AMD", name: "AMD", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "AVGO", instId: "AVGO", name: "Broadcom", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "TSM", instId: "TSM", name: "TSMC ADR", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "ASML", instId: "ASML", name: "ASML", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "AMAT", instId: "AMAT", name: "Applied Materials", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "LRCX", instId: "LRCX", name: "Lam Research", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "KLAC", instId: "KLAC", name: "KLA", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "QCOM", instId: "QCOM", name: "Qualcomm", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "ARM", instId: "ARM", name: "Arm", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "INTC", instId: "INTC", name: "Intel", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "SMCI", instId: "SMCI", name: "Super Micro", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "MU", instId: "MU", name: "Micron", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "WDC", instId: "WDC", name: "Western Digital", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "STX", instId: "STX", name: "Seagate", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "PSTG", instId: "PSTG", name: "Pure Storage", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "NTAP", instId: "NTAP", name: "NetApp", category: "stocks", type: "stock", source: "stooq", price: "--", change: "--" },
  { symbol: "HK.00700", instId: "HK.00700", name: "Tencent", category: "stocks", type: "stock", source: "yahoo", price: "--", change: "--" },
  { symbol: "HK.09988", instId: "HK.09988", name: "Alibaba HK", category: "stocks", type: "stock", source: "yahoo", price: "--", change: "--" },
  { symbol: "HK.01211", instId: "HK.01211", name: "BYD", category: "stocks", type: "stock", source: "yahoo", price: "--", change: "--" },
  { symbol: "HK.00002", instId: "HK.00002", name: "CLP Holdings", category: "stocks", type: "stock", source: "yahoo", price: "--", change: "--" },
  { symbol: "HK.00006", instId: "HK.00006", name: "Power Assets", category: "stocks", type: "stock", source: "yahoo", price: "--", change: "--" },
  { symbol: "HK.00836", instId: "HK.00836", name: "CR Power", category: "stocks", type: "stock", source: "yahoo", price: "--", change: "--" },
  { symbol: "HK.00902", instId: "HK.00902", name: "Huaneng Power", category: "stocks", type: "stock", source: "yahoo", price: "--", change: "--" },
  { symbol: "HK.00916", instId: "HK.00916", name: "Longyuan Power", category: "stocks", type: "stock", source: "yahoo", price: "--", change: "--" },
  { symbol: "HK.02638", instId: "HK.02638", name: "HK Electric", category: "stocks", type: "stock", source: "yahoo", price: "--", change: "--" },
];

const $ = (id) => document.getElementById(id);

const INTERFACE_VIEWS = {
  platform: {
    label: "总控",
    title: "量化策略验证与模拟交易",
    summary: "统一查看策略流水线、模拟账户、风控、数据健康和审计事件。",
    focus: ".platform-control-center",
  },
  trade: {
    label: "行情",
    title: "行情工作台",
    summary: "K线、盘口、成交和市场扫描保持在前台。",
    focus: ".ticker-header",
  },
  bot: {
    label: "Bot",
    title: "Strategy War Room",
    summary: "Strategy controls, paper orders, risk checks, signal logs and backtests are grouped here.",
    focus: ".strategy-desk",
  },
  marketai: {
    label: "AI Market",
    title: "AI研究员会议室",
    summary: "多AI按研究员会议纪要输出：观点、证据、反证、风险和后续观察条件。",
    focus: ".market-ai-panel",
  },
  research: {
    label: "雷达",
    title: "异动雷达",
    summary: "市场异动、趋势驾驶舱、研究档案和AI证据链集中在这里。",
    focus: ".research-panel",
  },
  system: {
    label: "System",
    title: "Account And System",
    summary: "History, account, guardian, exports, plugins and settings are grouped here.",
    focus: ".history-panel",
  },
  all: {
    label: "All",
    title: "Full Overview",
    summary: "Show every module for full inspection and bulk configuration.",
    focus: ".ticker-header",
  },
};

function currentMarket(symbol = state.symbol) {
  return markets.find((item) => item.symbol === symbol || item.instId === symbol) || { symbol, instId: symbol, type: symbol.endsWith("-SWAP") ? "swap" : "spot", source: "okx" };
}

function isStockMarket(symbol = state.symbol) {
  return currentMarket(symbol).type === "stock";
}

function okxInstId(symbol = state.symbol) {
  return currentMarket(symbol).instId || symbol;
}

function spotSymbol(symbol = state.symbol) {
  return symbol.endsWith("-SWAP") ? symbol.replace("-SWAP", "") : symbol;
}

function marketTypeLabel(item = currentMarket()) {
  if (item.type === "swap") return "永续";
  if (item.type === "stock") return "股票";
  return "现货";
}

function compactMarketRailMatches() {
  const query = window.matchMedia?.("(max-width: 480px)");
  return query ? query.matches : window.innerWidth <= 480;
}

function renderMarketRailDisclosureSummary() {
  const current = $("marketRailDisclosureCurrent");
  if (!current) return;
  current.textContent = `${state.symbol} · ${marketTypeLabel(currentMarket(state.symbol))}`;
}

function syncMarketRailDisclosure() {
  const disclosure = $("marketRailDisclosure");
  if (!disclosure) return;
  const compact = compactMarketRailMatches();
  const layoutMode = compact ? "compact" : "wide";
  if (disclosure.dataset.layoutMode === layoutMode) return;
  disclosure.dataset.layoutMode = layoutMode;
  disclosure.open = !compact;
}

function closeCompactMarketRailDisclosure() {
  const disclosure = $("marketRailDisclosure");
  if (!disclosure || !compactMarketRailMatches()) return;
  const restoreFocus = disclosure.contains(document.activeElement);
  disclosure.open = false;
  if (restoreFocus) disclosure.querySelector("summary")?.focus({ preventScroll: true });
}

function stockSourceLabel(item = currentMarket()) {
  if (item.source === "stock_sqlite_cache") return marketSourceLabel(item.source, item.originSource || item.origin_source || "");
  if (item.source === "futu") return item.market ? `Futu ${item.market}` : "Futu";
  if (item.source === "offline-seed") return "离线种子";
  if (item.source === "yahoo") return "Yahoo";
  if (item.source === "yahoo_adjusted") return "Yahoo Adj";
  if (item.source === "stooq") return "Stooq";
  return item.exchange || item.source || "--";
}

function bidAskText(bidValue, askValue, precision = 2) {
  const bid = Number(bidValue);
  const ask = Number(askValue);
  if (!Number.isFinite(bid) || !Number.isFinite(ask) || bid <= 0 || ask <= 0) return "--";
  return `${number(bid, precision)} / ${number(ask, precision)}`;
}

function marketDataBadge(item = currentMarket()) {
  const quoteQuality = item.quoteQuality || {};
  if (item.type === "stock" && quoteQuality.quarantined) {
    return {
      label: "待核",
      tone: "down",
      detail: [...(quoteQuality.quarantine_reasons || []), ...(quoteQuality.warnings || [])].filter(Boolean).join(" / ") || "报价基准待核",
    };
  }
  const knownQuality = state.chartQualityBySymbol?.[item.symbol];
  if (knownQuality) {
    return {
      label: knownQuality.mode || "K线",
      tone: knownQuality.tone || "flat",
      detail: [
        knownQuality.sourceText || knownQuality.sourceLabel || knownQuality.source || "K线",
        knownQuality.freshnessText || "",
        knownQuality.warningText || "",
      ].filter(Boolean).join(" / "),
    };
  }
  return window.HakimiChartQuality.marketDataBadge(item, Date.now());
}

function numericMarketValue(value) {
  const parsed = Number(String(value ?? "").replaceAll(",", "").replace("%", ""));
  return Number.isFinite(parsed) ? parsed : 0;
}

function stockQuoteContextSource(context = {}) {
  return String(context.source || context.origin_source || context.originSource || "").trim();
}

function stockQuoteContextForMarket(market = currentMarket()) {
  if (state.stockQuoteContext?.symbol === state.symbol && Number(state.stockQuoteContext.last) > 0) {
    return state.stockQuoteContext;
  }
  const last = numericMarketValue(market.price);
  if (!last) return null;
  return {
    symbol: state.symbol,
    source: market.quoteSource || market.source || "",
    origin_source: market.originSource || market.origin_source || "",
    last,
    ts: Number(market.lastUpdated || 0),
  };
}

function acceptStockQuoteContext(data = {}) {
  if (!isStockMarket(data.symbol || data.instId || state.symbol)) return true;
  const incoming = {
    ...data,
    symbol: data.symbol || data.instId || state.symbol,
    source: data.source || data.origin_source || data.originSource || "",
  };
  const current = state.stockQuoteContext?.symbol === state.symbol ? state.stockQuoteContext : null;
  const guard = window.HakimiStockQuoteGuard;
  const decision = guard && typeof guard.shouldAcceptStockQuoteContext === "function"
    ? guard.shouldAcceptStockQuoteContext({ incoming, current, nowMs: Date.now() })
    : { allowed: true };
  if (!decision.allowed) return false;
  state.stockQuoteContext = {
    symbol: incoming.symbol,
    source: incoming.source,
    origin_source: incoming.origin_source || incoming.originSource || "",
    last: Number(incoming.last),
    ts: Number(incoming.ts || incoming.updated_at || 0),
    status: incoming.status || "",
    quote_quality: incoming.quote_quality || incoming.quoteQuality || {},
    rank: Number(decision.rank || 0),
  };
  return true;
}

function activeStockPriceLogRows(limit = 48) {
  const context = stockQuoteContextForMarket();
  const source = window.HakimiStockQuoteGuard?.normalizeSource
    ? window.HakimiStockQuoteGuard.normalizeSource(stockQuoteContextSource(context))
    : stockQuoteContextSource(context).toLowerCase();
  const rows = state.stockPriceLog.filter((row) => row.symbol === state.symbol);
  if (!source) return rows.slice(0, limit);
  const sameSource = rows.filter((row) => {
    const rowSource = window.HakimiStockQuoteGuard?.normalizeSource
      ? window.HakimiStockQuoteGuard.normalizeSource(row.source)
      : String(row.source || "").toLowerCase();
    return rowSource === source;
  });
  return sameSource.slice(0, limit);
}

function marketVolumeForDisplay(market = {}) {
  const value = Number(market.type === "stock" ? (market.baseVolume24h ?? market.vol24h) : market.vol24h);
  return Number.isFinite(value) && value >= 0 ? value : 0;
}

function activeSymbolMetaText(market = currentMarket()) {
  const stock = market.type === "stock";
  const marketSession = state.marketSession || market.marketSession || {};
  const activeSessionPrice = Number(marketSession.active_price || 0);
  const sessionDetail = stock && (marketSession.status_label || marketSession.phase_label)
    ? ` / ${marketSession.status_label || marketSession.phase_label}${activeSessionPrice > 0 && marketSession.active_session !== "regular" ? ` ${number(activeSessionPrice, activeSessionPrice > 100 ? 2 : 4)}` : ""}`
    : "";
  return `${marketTypeLabel(market)} / ${stock ? stockSourceLabel(market) : "OKX 实时行情"}${sessionDetail} / 仅研究观察`;
}

function syncActiveSymbolHeader(statusText = "") {
  const market = currentMarket();
  const stock = market.type === "stock";
  const spot = market.type === "spot";
  const preview = previewPriceForSymbol(state.symbol);
  const price = numericMarketValue(market.price) || state.lastPrice || preview;
  const rawChange = numericMarketValue(market.rawChange ?? market.change);
  $("activeSymbol").textContent = state.symbol;
  const meta = document.querySelector(".symbol-meta");
  if (meta) meta.textContent = activeSymbolMetaText(market);
  $("lastPrice").textContent = price ? number(price, price > 100 ? 2 : 4) : "--";
  $("lastPrice").className = `last-price ${cssMove(rawChange)}`;
  $("priceChange").textContent = market.change && market.change !== "--" ? market.change : "等待报价";
  $("priceChange").className = `price-change ${cssMove(rawChange)}`;
  $("high24h").textContent = market.high24h ? number(market.high24h, price > 100 ? 2 : 4) : "--";
  $("low24h").textContent = market.low24h ? number(market.low24h, price > 100 ? 2 : 4) : "--";
  $("vol24hLabel").textContent = stock ? "当日成交量" : spot ? "24h 成交额" : "24h 成交量";
  $("vol24h").textContent = compact(marketVolumeForDisplay(market));
  $("bidAsk").textContent = bidAskText(market.bidPx, market.askPx, price > 100 ? 2 : 4);
  setConnection(statusText || (stock ? "股票数据准备中" : "行情数据准备中"), "flat");
  renderMarketWorkflowStrip();
}

function syncActiveMarketQuote(reason = "报价已同步") {
  const market = currentMarket();
  const last = numericMarketValue(market.price);
  if (!last) return false;
  if (isStockMarket() && !acceptStockQuoteContext({
    symbol: state.symbol,
    source: market.quoteSource || market.source || "",
    origin_source: market.originSource || market.origin_source || "",
    last,
    ts: market.lastUpdated || 0,
    status: market.status || "",
    quote_quality: market.quoteQuality || {},
  })) return false;
  state.lastPrice = last;
  syncActiveSymbolHeader(reason);
  if (state.candles.length && (!state.chartDataSymbol || state.chartDataSymbol === state.symbol)) {
    syncLiveCandle(last, {
      source: market.quoteSource || market.source,
      quote_quality: market.quoteQuality,
      change_basis: market.quoteChangeBasis,
      prevClose: market.quotePreviousClose,
      change24h_pct: market.quoteChangePct,
    });
  }
  renderLiveSourceBar();
  renderMarketWorkflowStrip();
  renderSideInsights();
  return true;
}

function statusTone(value) {
  if (["ok", "ready", "online"].includes(value)) return "up";
  if (["blocked", "offline", "missing", "error"].includes(value)) return "down";
  return "flat";
}

function workflowSetCard(cardId, valueId, detailId, tone, value, detail) {
  const card = $(cardId);
  if (card) card.className = `workflow-item ${tone || "flat"}`;
  if ($(valueId)) $(valueId).textContent = value || "--";
  if ($(detailId)) $(detailId).textContent = detail || "--";
}

function workflowEvidenceCount() {
  const trend = state.trendCockpit || {};
  const anomaly = state.selectedAnomaly || {};
  const stockDeep = state.futuDeep || {};
  const detail = state.anomalyDetail || {};
  return [
    ...(trend.evidence || []),
    ...(trend.counter_evidence || []),
    ...(trend.waiting_conditions || []),
    ...(anomaly.evidence || []),
    ...(detail.evidence_chain || []),
    ...(stockDeep.evidence || []),
    ...(state.research?.focus?.checklist || []),
  ].filter(Boolean).length;
}

function workflowTrendLabel(trend, local) {
  const cards = Array.isArray(trend?.cards) ? trend.cards : [];
  const structureCard = cards.find((card) => String(card.label || "").includes("趋势"));
  const direct = structureCard?.value || trend?.structure || trend?.regime || local?.trend_state;
  if (direct && String(direct).length <= 14) return "研究观察";
  const summary = String(trend?.summary || "");
  const match = summary.match(/[：:]\s*([^，,。；;]+)/);
  if (match?.[1] && match[1].length <= 14) return "研究观察";
  if (local?.trend_state) return "研究观察";
  return direct ? "研究观察" : "等待走势";
}

function renderMarketWorkflowStrip() {
  if (!$("marketWorkflowStrip")) return;
  const market = currentMarket();
  const quality = state.chartQuality || {};
  const local = frontendMarketAiLocal();
  const trend = state.trendCockpit?.symbol && state.trendCockpit.symbol !== state.symbol ? null : state.trendCockpit;
  const anomalyRows = state.anomalyRadar?.rows || [];
  const anomaly = state.selectedAnomaly?.symbol === state.symbol
    ? state.selectedAnomaly
    : anomalyRows.find((row) => row.symbol === state.symbol) || state.selectedAnomaly || null;
  const evidenceCount = workflowEvidenceCount();
  const symbolText = `${state.symbol} · ${marketTypeLabel(market)}`;
  const marketText = `${market.name || market.instId || state.symbol} / ${state.bar}${isStockMarket() ? ` / ${stockSessionLabel()}` : ""}`;
  if ($("workflowSymbol")) $("workflowSymbol").textContent = symbolText;
  if ($("workflowMarket")) $("workflowMarket").textContent = marketText;

  const dataTone = quality.tone || (quality.realtime ? "up" : quality.fallback || quality.preview ? "down" : "flat");
  const dataState = quality.mode || (quality.realtime ? "实时" : quality.fallback ? "兜底" : "等待");
  const dataDetail = quality.sourceText ? `${quality.sourceText}${quality.freshnessText ? ` / ${quality.freshnessText}` : ""}` : "等待行情快照";
  workflowSetCard("workflowDataCard", "workflowDataState", "workflowDataDetail", dataTone, dataState, dataDetail);

  const trendSummary = workflowTrendLabel(trend, local);
  const trendTone = "flat";
  const trendDetail = trend?.preferred
    ? `研究观察 / ${trend.safe_action || "仅研究"}`
    : `${local.volume_state || "量能等待"} / 支撑 ${local.support ? priceText(local.support) : "--"} / 压力 ${local.resistance ? priceText(local.resistance) : "--"}`;
  workflowSetCard("workflowTrendCard", "workflowTrendState", "workflowTrendDetail", trendTone, trendSummary, trendDetail);

  if (anomaly) {
    const change = Number(anomaly.change24h_pct || 0);
    const anomalyState = `${anomaly.severity_label || anomaly.severity || "WATCH"} ${number(anomaly.score || 0, 0)}`;
    const anomalyDetail = `${anomaly.symbol || state.symbol} / ${anomaly.reason || anomaly.direction || "等待确认"}`;
    workflowSetCard("workflowAnomalyCard", "workflowAnomalyState", "workflowAnomalyDetail", anomalyTone(anomaly), anomalyState, anomalyDetail);
    if ($("workflowAnomalyDetail")) $("workflowAnomalyDetail").className = "flat";
  } else {
    workflowSetCard("workflowAnomalyCard", "workflowAnomalyState", "workflowAnomalyDetail", "flat", "等待雷达", "刷新后捕捉放量、突破和波动扩张");
  }

  const evidenceTone = evidenceCount >= 8 ? "up" : evidenceCount >= 3 ? "flat" : "down";
  const evidenceDetail = quality.warningText || anomaly?.safe_action || trend?.safe_action || "观察 / 仅研究 / 仅模拟盘验证";
  workflowSetCard("workflowEvidenceCard", "workflowEvidenceState", "workflowEvidenceDetail", evidenceTone, `${evidenceCount} 条`, evidenceDetail);

  let actionTone = "flat";
  let actionState = "等待确认";
  let actionDetail = "观察，不是实盘指令";
  if (quality.preview || quality.fallback) {
    actionTone = "down";
    actionState = "先复核数据";
    actionDetail = quality.warningText || "当前非实时或兜底数据";
  } else if (anomaly?.symbol === state.symbol) {
    actionTone = "flat";
    actionState = "打开证据链";
    actionDetail = "看反证、等待条件和关键价位";
  } else if (trend?.summary || local.candle_count > 80) {
    actionTone = "flat";
    actionState = "看关键位";
    actionDetail = "支撑/压力、量能和假突破风险";
  }
  workflowSetCard("workflowActionCard", "workflowActionState", "workflowActionDetail", actionTone, actionState, actionDetail);
}

function setLamp(id, stateName) {
  const lamp = $(id);
  if (!lamp) return;
  lamp.className = `lamp ${stateName || "flat"}`;
}

function updateDesktopClock() {
  const clock = $("desktopClock");
  if (!clock) return;
  clock.textContent = new Date().toLocaleTimeString("zh-CN", { hour12: false });
}

function setText(selector, text) {
  const target = document.querySelector(selector);
  if (target) target.textContent = text;
}

function applyMarketResearchCopy() {
  setText(".brand-sub", "MARKET RADAR");
  setText(".shell-title-main span", "策略验证 + 模拟交易 + 风险审计");
  setText("#commandOpen", "搜索标的 / 功能");
  setText(".workspace-nav [data-workspace-focus='.ticker-header'] strong", "行情工作台");
  setText(".workspace-nav [data-workspace-focus='.ticker-header'] em", "K线 / 盘口 / 异动");
  setText(".workspace-nav [data-workspace-focus='.strategy-desk'] strong", "策略研究");
  setText(".workspace-nav [data-workspace-focus='.strategy-desk'] em", "仅研究 / 模拟验证");
  setText(".workspace-nav [data-workspace-focus='.orders-panel'] strong", "模拟记录");
  setText(".workspace-nav [data-workspace-focus='.orders-panel'] em", "订单 / 条件 / 复盘");
  setText(".workspace-nav [data-workspace-focus='.history-panel'] strong", "数据记录");
  setText(".workspace-nav [data-workspace-focus='.history-panel'] em", "账本 / 导出 / 日志");
  setText(".market-ai-panel .panel-title strong", "AI行情研究室");
  setText("#marketAiState", "等待行情问题");
  setText("#runMarketAiAnalysis", "双AI分析");
  setText("#refreshMarketAiSnapshot", "刷新快照");
  setText(".trading-agents-head strong", "TradingAgents 研究员会议室");
  setText("#tradingAgentsState", "等待研究员会议纪要");
  setText("#runTradingAgentsRoom", "生成会议纪要");
  setText(".trading-agents-subtitle", "辩论记录");
  setText(".runtime-key-head strong", "本机运行时密钥");
  setText("#runtimeKeyState", "重启失效，不写文件");
  setText("#saveRuntimeKeys", "载入内存");
  setText("#clearRuntimeKeys", "清空");
  document.querySelectorAll("[data-interface-view]").forEach((button) => {
    const labels = { platform: "交易总控", trade: "行情", marketai: "AI分析", bot: "策略研究", research: "异动雷达", system: "系统", all: "全览" };
    button.textContent = labels[button.dataset.interfaceView] || button.textContent;
  });
  document.querySelectorAll(".shell-tabs [data-workspace-focus], .module-bar [data-focus]").forEach((button) => {
    const target = button.dataset.workspaceFocus || button.dataset.focus;
    const labels = {
      ".ticker-header": "行情",
      ".strategy-desk": "策略",
      ".orders-panel": "模拟",
      ".account-center-grid": "账户",
      ".history-panel": "数据",
      ".system-grid": "系统",
    };
    if (labels[target]) button.textContent = labels[target];
  });
}

function viewForSelector(selector = "") {
  const target = String(selector);
  if (target.includes("platform-control")) return "platform";
  if (target.includes("strategy") || target.includes("orders-panel") || target.includes("signals-panel") || target.includes("risk-panel") || target.includes("conditional-panel")) {
    return "bot";
  }
  if (target.includes("market-ai")) {
    return "marketai";
  }
  if (target.includes("stock") || target.includes("futu") || target.includes("market-intel") || target.includes("deepseek") || target.includes("research") || target.includes("derivatives") || target.includes("leaderboard")) {
    return "research";
  }
  if (target.includes("account") || target.includes("system") || target.includes("history") || target.includes("ledger") || target.includes("export") || target.includes("api") || target.includes("daemon") || target.includes("guardian")) {
    return "system";
  }
  return "trade";
}

function renderInterfaceView() {
  const view = INTERFACE_VIEWS[state.interfaceView] ? state.interfaceView : "platform";
  state.interfaceView = view;
  document.body.classList.remove("view-platform", "view-trade", "view-bot", "view-marketai", "view-research", "view-system", "view-all");
  document.body.classList.add(`view-${view}`);
  document.querySelectorAll("[data-interface-view]").forEach((button) => {
    button.classList.toggle("active", button.dataset.interfaceView === view);
  });
  const meta = INTERFACE_VIEWS[view];
  const banner = $("interfaceFocusBanner");
  if (banner) {
    banner.innerHTML = `
      <div>
        <strong>${escapeHtml(meta.title)}</strong>
        <span>${escapeHtml(meta.summary)}</span>
      </div>
      <button data-interface-focus="${escapeHtml(meta.focus)}">进入重点模块</button>
    `;
    banner.querySelector("[data-interface-focus]")?.addEventListener("click", () => focusModule(meta.focus, false));
  }
}

function setInterfaceView(view, persist = true) {
  const requestedView = INTERFACE_VIEWS[view] ? view : "platform";
  state.interfaceView = requestedView === "trade" && runtime.forceMarketAiUntil > Date.now() ? "marketai" : requestedView;
  if (persist) {
    try {
      localStorage.setItem("hakimi.interface.view", state.interfaceView);
    } catch (error) {
      // Local storage can be unavailable in some embedded previews.
    }
  }
  renderInterfaceView();
  if (["trade", "marketai", "research", "all"].includes(state.interfaceView)) {
    const needsChartLoad = state.chartDataSymbol !== state.symbol
      || !state.candles.length
      || !chartIsVisibleForSymbol(state.symbol)
      || Boolean(state.chartQuality?.preview);
    ensureActiveChartPreview(state.symbol, state.bar);
    requestAnimationFrame(() => {
      drawChart();
      if (needsChartLoad) loadCandles(runtime.symbolVersion).catch(() => {});
    });
  }
  if (["platform", "bot"].includes(state.interfaceView)) {
    loadPlatformControlCenter().catch(() => {});
  }
  if (state.interfaceView === "marketai") {
    setTimeout(() => {
      drawChart();
      renderMarketAiLocal();
      loadRuntimeKeyStatus().catch(() => {});
      loadTradingAgentsStatus().catch(() => {});
    }, 0);
  }
  if (state.interfaceView === "research") {
    renderResearchDataQualityCards(researchDataQualitySnapshot());
    loadAnomalyRadar(false).catch(() => {});
    loadResearchPanel().catch(() => {});
    loadDataReliability().catch(() => {});
    if (isStockMarket()) loadFutuDeep(false).catch(() => {});
  }
  if (state.interfaceView === "bot") {
    loadStrategyCompare().catch(() => {});
    loadStrategyWarRoom().catch(() => {});
    loadStrategyDoctor().catch(() => {});
  }
  if (state.interfaceView === "system") {
    loadFullConfig().catch(() => {});
    loadV2Platform().catch(() => {});
    loadDataReliability().catch(() => {});
    loadDataCache().catch(() => {});
    loadApiConfig().catch(() => {});
  }
}

function renderDesktopStatus() {
  const activeMode = state.desktop.mode || "PAPER";
  document.querySelectorAll("[data-desktop-mode]").forEach((button) => {
    button.classList.toggle("active", button.dataset.desktopMode === activeMode);
  });
  renderInterfaceView();
  $("quoteSourceSelect").value = state.desktop.quoteSource || "AUTO";
  const market = currentMarket();
  $("desktopSession").textContent = `${marketTypeLabel(market)} / ${state.symbol}`;
  const okxState = state.desktop.okxOnline ? "up" : "down";
  setLamp("okxStatusLamp", okxState);
  $("okxStatusText").textContent = state.desktop.okxOnline ? "实时" : "等待";

  const futuOnline = futuOpenDOnline();
  setLamp("futuStatusLamp", futuOnline ? "up" : "down");
  $("futuStatusText").textContent = futuOnline ? "ONLINE" : "OFFLINE";

  // Paper state remains raw audit metadata, never a permission signal.  Keep
  // the top-level status neutral even if an old/runtime snapshot says armed.
  const armed = Boolean(state.paper?.armed);
  setLamp("paperStatusLamp", "flat");
  const paperStatusText = $("paperStatusText");
  if (paperStatusText) {
    paperStatusText.textContent = armed ? "研究记录 · 模拟未授权" : "模拟未授权";
    paperStatusText.dataset.rawArmed = String(armed);
    paperStatusText.title = `原始 armed=${String(armed)} · 不代表模拟授权`;
  }

  const risk = state.paper?.risk_status || "--";
  const riskOk = risk === "正常" || risk === "OK";
  setLamp("riskStatusLamp", riskOk ? "up" : risk === "--" ? "flat" : "down");
  $("desktopRiskText").textContent = risk;
  $("shellDataSource").textContent = `${state.desktop.quoteSource || "AUTO"} / ${market.source?.toUpperCase?.() || "LOCAL"}`;
  $("shellGuardState").textContent = state.desktop.mode === "LOCKED" ? "实盘永久硬锁" : state.desktop.mode === "WATCH" ? "观察模式" : "模拟未授权";
  renderStrategyCommandStrip();
}

function futuOpenDOnline(futu = state.futu || {}) {
  const message = String(futu.message || futu.error || "");
  return Boolean(futu.opend_online) && !/(offline|timed out|timeout|failed|error)/i.test(message);
}

function optionText(id) {
  const element = $(id);
  return element?.selectedOptions?.[0]?.textContent || element?.value || "--";
}

function renderStrategyCommandStrip() {
  if (!$("strategyCommandStatus")) return;
  const strategyName = optionText("strategySelect");
  const armed = Boolean(state.paper?.armed);
  const leverage = $("leverageInput")?.value || "1";
  const orderType = optionText("strategyOrderType");
  const marginMode = optionText("marginMode");
  const riskSource = optionText("riskSource");
  const explanation = currentStrategyExplanation();
  const presetMatches = state.activeStrategyPreset?.strategyId === $("strategySelect")?.value;
  const presetLabel = presetMatches && state.activeStrategyPreset?.label ? ` / ${state.activeStrategyPreset.label}` : "";
  const riskValue = explanation.hasEvidence
    ? `研究证据 / ${explanation.estimateText}`
    : `${riskSource}${presetLabel} / 尚无研究证据`;
  $("strategyCommandStatus").textContent = armed
    ? `本地模拟状态已记录 · 模拟仍未授权 · ${strategyName} ${leverage}x${presetLabel}`
    : `研究观察 · 尚无模拟记录${presetLabel}`;
  $("strategyCommandDirection").textContent = explanation.directionText;
  $("strategyCommandOrder").textContent = `模拟参数仅供规划 · ${orderType} / ${marginMode}`;
  $("strategyCommandRisk").textContent = riskValue;
  $("strategyCommandProbability").textContent = explanation.estimateText;
  renderBotReadiness();
}

function botReadinessSnapshot() {
  const market = currentMarket();
  const analysis = state.latestStrategyAnalysis || state.paper?.ai_analysis || {};
  const guardian = state.profile?.guardian || {};
  const platformControl = state.platformControl && typeof state.platformControl === "object"
    ? state.platformControl
    : null;
  const latestPipeline = platformControl?.pipeline?.latest || {};
  const pipelineStages = latestPipeline.stages || {};
  const price = Number(state.lastPrice || state.candles[state.candles.length - 1]?.close || 0);
  const leverage = Number($("leverageInput")?.value || 1);
  const position = Number($("positionInput")?.value || 0);
  const riskSource = $("riskSource")?.value || "AI";
  const riskMode = $("riskValueMode")?.value || "PRICE";
  const takeProfitInput = Number($("takeProfitInput")?.value || 0);
  const stopLossInput = Number($("stopLossInput")?.value || 0);
  const directionMode = $("directionMode")?.value || "LONG_ONLY";
  const trailingExitEnabled = Boolean($("trailingTakeEnabled")?.checked || $("trailingStopEnabled")?.checked);
  const strategyOrderType = $("strategyOrderType")?.value || "MARKET";
  const strategyMarginMode = $("marginMode")?.value || "CROSS";
  const strategyId = $("strategySelect")?.value || "";
  const strategy = state.strategies.find((item) => item.id === strategyId) || {};
  const researchProfile = strategy.research_risk_profile || {};
  const frozenRisk = researchProfile.risk || {};
  const structureExit = researchProfile.profile_id === "TREND_STRUCTURE_EXIT";
  const closeEnough = (left, right) => Number.isFinite(Number(left))
    && Number.isFinite(Number(right))
    && Math.abs(Number(left) - Number(right)) < 0.000001;
  const frozenRiskMatches = Boolean(researchProfile.profile_id)
    && closeEnough(position, frozenRisk.position_pct)
    && closeEnough(takeProfitInput, frozenRisk.take_profit_pct)
    && closeEnough(stopLossInput, frozenRisk.stop_loss_pct)
    && closeEnough(leverage, frozenRisk.leverage);
  const manualRiskComplete = stopLossInput > 0 && (takeProfitInput > 0 || (structureExit && takeProfitInput === 0));
  const runtimeWritable = Boolean(platformControl) && platformControl.read_only === false;
  const pipelineMatches = Boolean(latestPipeline.run_id)
    && latestPipeline.symbol === state.symbol
    && latestPipeline.strategy_id === strategyId;
  const pipelineValidated = pipelineMatches
    && pipelineStages.backtest?.status === "PASS"
    && pipelineStages.doctor?.status === "PASS"
    && !latestPipeline.legacy_blockers?.length
    && !latestPipeline.validation_blockers?.length;
  const paperAuthorizationStatus = pipelineStages.paper_authorization?.status || "WAIT";
  const pipelineEligible = pipelineValidated
    && (latestPipeline.paper_authorized === true
      ? paperAuthorizationStatus === "PASS"
      : paperAuthorizationStatus === "WAIT");
  const liveHardWall = Boolean(platformControl)
    && platformControl.live_trading_hard_block === true
    && platformControl.live_order_allowed === false;
  const marketAge = market.lastUpdated ? Date.now() - Number(market.lastUpdated) : Infinity;
  const checks = [];
  const add = (id, label, status, detail, weight = 12) => {
    checks.push({ id, label, status, detail, weight });
  };

  add("price", "Market price", price > 0 ? "PASS" : "BLOCK", price > 0 ? `Last ${number(price, price > 100 ? 2 : 5)}` : "No price", 18);
  add("fresh", "Freshness", marketAge < 15000 || state.candles.length ? "PASS" : "WARN", marketAge < 15000 ? `${Math.max(1, Math.round(marketAge / 1000))}s ago` : "Waiting for quote", 10);
  add("candles", "K-line sample", state.candles.length >= 80 ? "PASS" : state.candles.length >= 30 ? "WARN" : "BLOCK", `${state.candles.length} bars`, 12);
  add("strategy", "Strategy", $("strategySelect")?.value ? "PASS" : "BLOCK", optionText("strategySelect"), 14);
  add(
    "runtime_write",
    "Runtime mode",
    runtimeWritable ? "PASS" : "BLOCK",
    !platformControl ? "等待总控证据" : platformControl.read_only ? "只读预览实例" : "可写模拟实例；仍不等于授权",
    18,
  );
  add(
    "pipeline_authorization",
    "Strategy pipeline",
    pipelineEligible ? "PASS" : "BLOCK",
    !latestPipeline.run_id
        ? "No frozen validation run"
        : !pipelineMatches
          ? `Latest run is ${latestPipeline.symbol || "--"} / ${latestPipeline.strategy_id || "--"}`
          : !pipelineValidated
          ? "回测或体检证据未同时核对"
          : latestPipeline.paper_authorized === true
            ? "上游声称模拟权限；当前页面仍需独立人工核对"
            : "研究证据已核对；模拟仍未授权",
    18,
  );
  const planningTakeProfit = strategyPlanningValue(analysis, "take_profit");
  const planningStopLoss = strategyPlanningValue(analysis, "stop_loss");
  add("analysis", "AI risk", planningTakeProfit && planningStopLoss ? "PASS" : riskSource === "AI" ? "WARN" : "PASS", planningTakeProfit ? `研究规划 TP ${number(planningTakeProfit, 2)} / 规划 SL ${number(planningStopLoss, 2)}` : "Run research analysis first", 12);
  const manualRiskDetail = riskSource === "MANUAL"
    ? structureExit && takeProfitInput === 0
      ? `${riskMode} structure exit / emergency SL ${stopLossInput || "--"}%`
      : `${riskMode} TP ${takeProfitInput || "--"} / SL ${stopLossInput || "--"}`
    : "AI";
  add("manual_risk", "Manual risk", riskSource !== "MANUAL" || manualRiskComplete ? "PASS" : "BLOCK", manualRiskDetail, 12);
  add("sizing", "Size and leverage", leverage === VALIDATED_STRATEGY_LEVERAGE ? (position <= 35 ? "PASS" : "WARN") : "BLOCK", `${leverage}x / ${position}%`, 14);
  add("validated_direction", "Backtest direction", directionMode === "LONG_ONLY" ? "PASS" : "BLOCK", directionMode === "LONG_ONLY" ? "Long-only causal model" : "Short model is not validated", 12);
  add(
    "validated_risk_profile",
    "Frozen risk profile",
    riskSource === "MANUAL" && riskMode === "PCT" && frozenRiskMatches ? "PASS" : "BLOCK",
    frozenRiskMatches ? researchProfile.profile_id : `${riskSource} / ${riskMode} / differs from research contract`,
    12,
  );
  add(
    "validated_exit_model",
    "Exit model",
    trailingExitEnabled ? "BLOCK" : "PASS",
    trailingExitEnabled ? "Trailing exits are not backtested" : structureExit ? "Signal structure exit / emergency stop" : "Fixed TP / SL",
    10,
  );
  add("validated_execution", "Execution profile", strategyOrderType === "CURRENT" && strategyMarginMode === "CROSS" ? "PASS" : "BLOCK", `${strategyOrderType} / ${strategyMarginMode}`, 10);
  add(
    "guardian",
    "Guardian",
    guardian.status === "RUNNING" || guardian.enabled ? "PASS" : "WARN",
    guardian.status === "RUNNING" || guardian.enabled ? "守护状态已核对" : "守护进程未启动 · 待复核",
    8,
  );
  add(
    "hard_lock",
    "Live hard wall",
    liveHardWall ? "PASS" : "BLOCK",
    !platformControl ? "Waiting for control center" : liveHardWall ? "Live orders permanently blocked" : "Live-order invariant is not confirmed",
    18,
  );

  const maxScore = checks.reduce((sum, item) => sum + item.weight, 0);
  const score = checks.reduce((sum, item) => {
    if (item.status === "PASS") return sum + item.weight;
    if (item.status === "WARN") return sum + item.weight * 0.48;
    return sum;
  }, 0) / Math.max(maxScore, 1) * 100;
  const blockers = checks.filter((item) => item.status === "BLOCK");
  const warnings = checks.filter((item) => item.status === "WARN");
  const status = blockers.length ? "BLOCK" : warnings.length ? "WARN" : "PASS";
  return { score: Math.round(score), status, checks, blockers, warnings };
}

function readinessTone(status) {
  if (status === "PASS") return "up";
  if (status === "BLOCK") return "down";
  return "flat";
}

function renderBotReadiness() {
  const target = $("botReadinessPanel");
  if (!target) return botReadinessSnapshot();
  const snap = botReadinessSnapshot();
  const headline = snap.status === "PASS"
    ? "研究预检已核对 · 模拟仍未授权"
    : snap.status === "WARN"
      ? "研究预检待复核 · 模拟仍未授权"
      : "研究预检存在阻断 · 禁止启动";
  target.className = "bot-readiness-panel flat evidence-neutral";
  target.innerHTML = `
    <div class="readiness-score">
      <span>研究预检分 · 非授权</span>
      <strong>${snap.score}</strong>
      <em>${headline}</em>
    </div>
    <div class="readiness-checks">
      ${snap.checks.map((item) => `
        <div class="flat" data-raw-status="${escapeHtml(item.status)}" title="原始状态 ${escapeHtml(item.status)}">
          <span>${escapeHtml(item.label)}</span>
          <strong>${item.status === "PASS" ? "已核对" : item.status === "WARN" ? "待复核" : "阻断"}</strong>
          <em>${escapeHtml(item.detail)}</em>
        </div>
      `).join("")}
    </div>
  `;
  return snap;
}

function syncWorkspaceNav(selector = state.desktop.activeWorkspace) {
  state.desktop.activeWorkspace = selector || ".ticker-header";
  document.querySelectorAll("[data-workspace-focus]").forEach((button) => {
    button.classList.toggle("active", button.dataset.workspaceFocus === state.desktop.activeWorkspace);
  });
}

function moduleCommands() {
  return [
    { group: "模块", label: "交易总控", hint: "策略流水线、模拟账户、风控、数据和审计", action: () => setInterfaceView("platform") },
    { group: "模块", label: "异动雷达", hint: "市场异常、趋势驾驶舱和研究证据链", action: () => setInterfaceView("research") },
    { group: "模块", label: "行情工作台", hint: "报价、K线、盘口和逐笔成交", action: () => focusModule(".ticker-header") },
    { group: "模块", label: "AI行情分析", hint: "K线加DeepSeek初评和GPT复核", action: () => setInterfaceView("marketai") },
    { group: "模块", label: "策略研究", hint: "参数、回测、模拟验证和AI风控", action: () => focusModule(".strategy-desk") },
    { group: "模块", label: "模拟记录", hint: "模拟订单、条件单和成交流水", action: () => focusModule(".orders-panel") },
    { group: "模块", label: "账户", hint: "模拟权益和资产", action: () => focusModule(".account-center-grid") },
    { group: "模块", label: "历史数据", hint: "账本、历史和导出", action: () => focusModule(".history-panel") },
    { group: "模块", label: "系统", hint: "主题、布局、API和数据状态", action: () => focusModule(".system-grid") },
    { group: "Action", label: "Futu Setup", hint: "OpenD account, verify code and port", action: () => window.location.href = "/futu_setup.html" },
    { group: "Action", label: "刷新Futu", hint: "重新检查FutuOpenD", action: () => loadFutuStatus(true) },
    { group: "Action", label: "刷新行情", hint: "OKX和股票报价", action: () => refreshMarketTickers(true) },
    { group: "Action", label: "扫描异动雷达", hint: "刷新异动、趋势驾驶舱和事件库", action: () => { setInterfaceView("research"); loadAnomalyRadar(false, runtime.symbolVersion, { force: true }); loadTrendCockpit(state.symbol, runtime.symbolVersion); loadAnomalyEvents("", { force: true, limit: 120 }); } },
    { group: "Action", label: "核对当前证据", hint: "查看已存行情、自然前向、策略与纯规划证据；不自动重跑历史", action: () => reviewPlatformEvidence().catch(() => {}) },
    { group: "Action", label: "打开风险解释", hint: "查看实盘硬墙、模拟盘风控和阻断原因", action: () => { focusModule(".risk-panel"); loadRiskEngine(); } },
    { group: "Action", label: "刷新数据总控", hint: "数据可靠性、adapter和六路线进度", action: () => { focusModule(".system-grid"); loadDataReliability(); loadMarketAdapters(); loadSixLaneRoadmap(); } },
    { group: "Action", label: "TradingAgents会议纪要", hint: "外部AI研究员会议：走势、证据、反证、风险、观察条件", action: () => { setInterfaceView("marketai"); loadTradingAgentsStatus(); runTradingAgentsRoom(); } },
    { group: "Action", label: "图表自动标注", hint: "显示策略锚点、支撑压力和风险线", action: () => { state.indicators.autoMarks = true; syncIndicatorButtons(); renderChartStrategyOverlay(); drawChart(); } },
    { group: "Action", label: "回放模式", hint: "复盘历史K线和策略信号", action: () => { focusModule(".chart-panel"); if (!state.replay.active) toggleReplay(); } },
    { group: "Action", label: "Emergency Stop", hint: "Stop paper strategy and guardian", action: guardianEmergencyStop },
  ];
}

function commandItems() {
  const marketItems = markets.map((item) => ({
    group: "市场",
    label: item.symbol,
    hint: `${marketTypeLabel(item)} / ${item.name} / ${item.source || "--"}`,
    action: () => selectSymbol(item.symbol, { focusChart: true }),
  }));
  return [...marketItems, ...moduleCommands()];
}

function openCommandPanel(prefill = "") {
  state.desktop.commandOpen = true;
  state.desktop.commandIndex = 0;
  $("commandOverlay").classList.remove("hidden");
  $("commandInput").value = prefill;
  renderCommandResults();
  setTimeout(() => $("commandInput").focus(), 0);
}

function closeCommandPanel() {
  state.desktop.commandOpen = false;
  $("commandOverlay").classList.add("hidden");
  $("commandInput").value = "";
}

function setDesktopMode(mode) {
  state.desktop.mode = ["PAPER", "WATCH", "LOCKED"].includes(mode) ? mode : "PAPER";
  if (state.desktop.mode === "LOCKED") {
    $("chartStatus").textContent = "实盘硬锁已开启；当前仅允许研究和模拟盘。";
  }
  renderDesktopStatus();
}

function setQuoteSource(source) {
  state.desktop.quoteSource = ["AUTO", "OKX", "FUTU"].includes(source) ? source : "AUTO";
  if (state.desktop.quoteSource === "FUTU") {
    state.marketCategory = "stocks";
    syncMarketCategoryTabs();
    renderMarkets();
    loadFutuStatus(true);
  }
  if (state.desktop.quoteSource === "OKX") {
    state.marketCategory = "all";
    syncMarketCategoryTabs();
    renderMarkets();
    refreshMarketTickers();
  }
  renderDesktopStatus();
}

function syncMarketCategoryTabs() {
  document.querySelectorAll("#marketCategoryTabs button").forEach((button) => {
    button.classList.toggle("active", button.dataset.category === state.marketCategory);
  });
}

function renderCommandResults() {
  const query = $("commandInput").value.trim().toUpperCase();
  const rows = commandItems()
    .filter((item) => !query || item.label.toUpperCase().includes(query) || item.hint.toUpperCase().includes(query))
    .slice(0, 12);
  if (state.desktop.commandIndex >= rows.length) state.desktop.commandIndex = 0;
  $("commandResults").innerHTML = rows.map((item, index) => `
    <div class="command-row ${index === state.desktop.commandIndex ? "active" : ""}" data-command-index="${index}">
      <em>${item.group || "命令"}</em>
      <strong>${item.label}</strong>
      <span>${item.hint}</span>
    </div>
  `).join("") || `<div class="command-empty">没有匹配结果</div>`;
  document.querySelectorAll("[data-command-index]").forEach((row) => {
    row.addEventListener("mouseenter", () => {
      state.desktop.commandIndex = Number(row.dataset.commandIndex || 0);
      renderCommandResults();
    });
    row.addEventListener("click", () => runCommand(rows[Number(row.dataset.commandIndex || 0)]));
  });
  state.desktop.commandRows = rows;
}

function setupChartToolMenus() {
  if ($("chartToolPopover")) return;
  const toolbar = document.querySelector(".chart-panel .toolbar-actions");
  const panel = document.querySelector(".chart-panel");
  const canvas = $("priceChart");
  if (!toolbar || !panel || !canvas) return;
  const groups = [
    { id: "view", label: "视图", title: "视图工具", buttons: [["toggleChartMode", "K线"], ["loadLocalHistory", "本地历史"]] },
    { id: "indicator", label: "指标", title: "指标工具", buttons: [["toggleMA", "MA"], ["toggleBollinger", "BOLL"], ["toggleVolume", "成交量"], ["toggleSignals", "信号"], ["toggleVolumeProfile", "VP"]] },
    { id: "drawing", label: "画线", title: "画线工具", buttons: [["drawCursor", "光标"], ["drawTrend", "趋势线"], ["drawHorizontal", "水平线"], ["drawFib", "斐波"], ["clearDrawings", "清除"]] },
    { id: "ai", label: "分析", title: "分析与回放", buttons: [["autoChartMarks", "自动标注"], ["toggleReplay", "回放"], ["analyzeChartAi", "图表分析"]] },
  ];

  const moved = new Map();
  groups.forEach((group) => {
    group.buttons.forEach(([id, label]) => {
      const button = $(id);
      if (button) {
        button.textContent = label;
        moved.set(id, button);
      }
    });
  });

  toolbar.innerHTML = "";
  groups.forEach((group, index) => {
    const trigger = document.createElement("button");
    trigger.className = `chart-tool-trigger ${index === 0 ? "active" : ""}`;
    trigger.dataset.chartToolMenu = group.id;
    trigger.textContent = group.label;
    toolbar.appendChild(trigger);
  });

  const popover = document.createElement("div");
  popover.id = "chartToolPopover";
  popover.className = "chart-tool-popover hidden";
  popover.innerHTML = `
    <div class="chart-tool-popover-head">
      <strong id="chartToolTitle">行情工具</strong>
      <button id="closeChartTools" type="button">关闭</button>
    </div>
  `;
  groups.forEach((group, index) => {
    const body = document.createElement("div");
    body.className = `chart-tool-panel ${index === 0 ? "" : "hidden"}`;
    body.dataset.chartToolPanel = group.id;
    group.buttons.forEach(([id]) => {
      const button = moved.get(id);
      if (button) body.appendChild(button);
    });
    popover.appendChild(body);
  });
  if (canvas.parentElement === panel) {
    panel.insertBefore(popover, canvas);
  } else {
    panel.appendChild(popover);
  }

  const openMenu = (id) => {
    const group = groups.find((item) => item.id === id) || groups[0];
    $("chartToolTitle").textContent = group.title;
    popover.classList.remove("hidden");
    document.querySelectorAll("[data-chart-tool-menu]").forEach((button) => button.classList.toggle("active", button.dataset.chartToolMenu === group.id));
    document.querySelectorAll("[data-chart-tool-panel]").forEach((body) => body.classList.toggle("hidden", body.dataset.chartToolPanel !== group.id));
  };

  document.querySelectorAll("[data-chart-tool-menu]").forEach((button) => {
    button.addEventListener("click", () => openMenu(button.dataset.chartToolMenu));
  });
  $("closeChartTools")?.addEventListener("click", () => popover.classList.add("hidden"));
}

function setupFutuStyleWorkspace() {
  setupChartToolMenus();
  setupRightInsightPanel();
}

function runCommand(item = state.desktop.commandRows?.[state.desktop.commandIndex]) {
  if (!item) return;
  closeCommandPanel();
  item.action();
}

function renderFutuGuide(data = state.futu) {
  const target = $("futuGuideRows");
  if (!target || !data) return;
  const steps = data.steps || [];
  const markets = data.markets || {};
  const marketText = Object.entries(markets)
    .filter(([, count]) => Number(count) > 0)
    .map(([market, count]) => `${market} ${count}`)
    .join(" / ");
  target.innerHTML = `
    <div class="futu-guide-summary">
      <strong>${data.setup_hint || "Waiting for FutuOpenD status"}</strong>
      <span>${marketText || "Stock pool not loaded"}</span>
    </div>
    <div class="futu-guide-steps">
      ${steps.map((step) => `
        <div>
          <span>${step.label}</span>
          <strong class="${statusTone(step.state)}">${step.state}</strong>
          <em>${step.detail}</em>
        </div>
      `).join("")}
    </div>
  `;
}

function stockIntervalForBar(bar = state.bar) {
  const map = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1H": "1h",
    "4H": "4h",
    "1Dutc": "1d",
  };
  return map[bar] || "1d";
}

function isStockDailyBar(bar = state.bar) {
  return stockIntervalForBar(bar) === "1d";
}

function isStockMinuteBar(bar = state.bar) {
  return ["1m", "5m", "15m", "30m", "1H"].includes(bar);
}

function stockBarLabel(bar = state.bar) {
  return {
    "1m": "1分钟",
    "5m": "5分钟",
    "15m": "15分钟",
    "30m": "30分钟",
    "1H": "60分钟",
    "4H": "4小时",
    "1Dutc": "日线",
  }[bar] || String(bar || "--");
}

function stockVisibleBarsForBar(bar = state.bar) {
  if (bar === "1m") return state.stockSession === "regular" ? 420 : 520;
  if (bar === "5m") return 180;
  if (bar === "15m") return 160;
  if (bar === "30m") return 140;
  if (bar === "1H") return 140;
  return 160;
}

function stockSessionLabel(session = state.stockSession) {
  return {
    all: "全部",
    pre: "盘前",
    regular: "盘中",
    post: "盘后",
    overnight: "夜盘",
  }[session] || "全部";
}

function stockChartScopeLabel(bar = state.bar, session = state.stockSession) {
  return isStockDailyBar(bar) ? "日线" : stockSessionLabel(session);
}

function isRecentStockDailyData({ bar = state.bar, latestTs = 0, ageMs = 0 } = {}) {
  return Boolean(window.HakimiChartQuality?.isRecentStockDaily?.({
    bar: stockIntervalForBar(bar),
    latestTs,
    ageMs,
    now: Date.now(),
  }));
}

function stockIntradayLabel(session = state.stockSession) {
  if (session === "all") return "全天分时";
  return `${stockSessionLabel(session)}分时`;
}

function syncChartControlLabels() {
  const timeframeLabels = isStockMarket()
    ? {
        "1m": "分时",
        "5m": "5分",
        "15m": "15分",
        "30m": "30分",
        "1H": "60分",
        "4H": "4小时",
        "1Dutc": "日线",
      }
    : {
        "1m": "1m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1H": "1h",
        "4H": "4h",
        "1Dutc": "1D",
      };
  $("timeframeTabs")?.querySelectorAll("button").forEach((button) => {
    button.textContent = timeframeLabels[button.dataset.bar] || button.dataset.bar || "--";
  });
  const sessionLabels = { all: "全部", pre: "盘前", regular: "盘中", post: "盘后", overnight: "夜盘" };
  $("stockSessionTabs")?.querySelectorAll("button").forEach((button) => {
    button.textContent = sessionLabels[button.dataset.stockSession] || button.dataset.stockSession || "--";
  });
  const toggle = $("toggleChartMode");
  if (toggle) toggle.textContent = state.chartMode === "candles" ? "K线" : "分时";
}

function number(value, digits = 2) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return "--";
  return parsed.toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

function priceDigits(value) {
  const parsed = Math.abs(Number(value));
  if (!Number.isFinite(parsed) || parsed === 0) return 2;
  if (parsed >= 100) return 2;
  if (parsed >= 1) return 4;
  if (parsed >= 0.01) return 5;
  return 8;
}

function priceText(value) {
  return number(value, priceDigits(value));
}

function chartPriceSpan(minPrice, maxPrice) {
  const min = Number(minPrice);
  const max = Number(maxPrice);
  if (!Number.isFinite(min) || !Number.isFinite(max)) return 1;
  const center = Math.max(Math.abs((min + max) / 2), Math.abs(min), Math.abs(max));
  const natural = Math.abs(max - min);
  return Math.max(natural, center * 0.006, 1e-10);
}

function priceFitsCurrentChart(price, referencePrice) {
  const parsed = Number(price);
  const reference = Number(referencePrice);
  if (!Number.isFinite(parsed) || parsed <= 0 || !Number.isFinite(reference) || reference <= 0) return false;
  const ratio = parsed / reference;
  return ratio >= 0.2 && ratio <= 5;
}

function chartScaleAnchorPrices(rawMinPrice, rawMaxPrice, referencePrice) {
  const rawRange = chartPriceSpan(rawMinPrice, rawMaxPrice);
  const extension = Math.max(rawRange * 0.55, Math.abs(referencePrice) * 0.012, 1e-10);
  return strategyAnchorLines()
    .map((line) => line.price)
    .filter((price) => Number.isFinite(price) && price > 0)
    .filter((price) => price >= rawMinPrice - extension && price <= rawMaxPrice + extension);
}

function compact(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return "--";
  if (Math.abs(parsed) >= 1_000_000_000) return `${number(parsed / 1_000_000_000, 2)}B`;
  if (Math.abs(parsed) >= 1_000_000) return `${number(parsed / 1_000_000, 2)}M`;
  if (Math.abs(parsed) >= 1_000) return `${number(parsed / 1_000, 2)}K`;
  return number(parsed, 2);
}

function tradeSizeText(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return "--";
  if (Math.abs(parsed) >= 1000) return compact(parsed);
  if (Math.abs(parsed) >= 100) return number(parsed, 2);
  if (Math.abs(parsed) >= 1) return number(parsed, 4);
  return number(parsed, 6);
}

function tradeTimeText(ts) {
  const date = new Date(Number(ts));
  if (Number.isNaN(date.getTime())) return "--";
  return date.toLocaleTimeString("zh-CN", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function cssMove(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed === 0) return "flat";
  return parsed > 0 ? "up" : "down";
}

function cssColor(name, fallback) {
  const value = getComputedStyle(document.body).getPropertyValue(name).trim()
    || getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

function chartUpColor() {
  return cssColor("--up", "#ff4d5e");
}

function chartDownColor() {
  return cssColor("--down", "#19c37d");
}

function chartAlpha(color, alpha) {
  const hex = String(color || "").trim();
  if (/^#[0-9a-f]{6}$/i.test(hex)) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r},${g},${b},${alpha})`;
  }
  return color;
}

function chartThemeColors() {
  const light = document.body.classList.contains("theme-light");
  return {
    surface: light ? cssColor("--panel", "#fff") : cssColor("--bg", "#0a0d0c"),
    grid: light ? cssColor("--line", "#d8dee9") : "#202724",
    muted: cssColor("--muted", light ? "#5f6b7a" : "#8f9b96"),
    text: cssColor("--text", light ? "#101419" : "#edf2ef"),
    overlayBg: light ? "rgba(255, 255, 255, 0.92)" : "rgba(5, 7, 7, 0.82)",
    hover: light ? "rgba(95, 107, 122, 0.55)" : "rgba(143, 155, 150, 0.55)",
    danger: light ? "rgba(16, 20, 25, 0.72)" : "rgba(255, 255, 255, 0.72)",
    volumeProfile: light ? "rgba(15, 98, 254, 0.13)" : "rgba(67, 215, 255, 0.14)",
  };
}

function timeText(ts) {
  const date = new Date(Number(ts));
  return date.toLocaleTimeString("zh-CN", { hour12: false });
}

function drawingKey() {
  return `quantx.drawings.${state.symbol}.${state.bar}`;
}

function loadDrawings() {
  try {
    state.drawings = JSON.parse(localStorage.getItem(drawingKey()) || "[]").slice(-80);
  } catch (error) {
    state.drawings = [];
  }
}

function saveDrawings() {
  try {
    localStorage.setItem(drawingKey(), JSON.stringify(state.drawings.slice(-80)));
  } catch (error) {
    // Drawing persistence is optional; the chart itself should keep working.
  }
  renderMarketAiLocal();
}

function marketMatchesQuery(item, query) {
  return !query || item.symbol.includes(query) || item.name.toUpperCase().includes(query);
}

function commitMarketSearch() {
  const input = $("marketSearch");
  const query = input?.value.trim().toUpperCase() || "";
  if (!query) return false;
  const matches = markets.filter((item) => marketMatchesQuery(item, query));
  const target = matches.find((item) => item.symbol === query)
    || matches.find((item) => item.name.toUpperCase() === query)
    || (matches.length === 1 ? matches[0] : null);
  if (!target) return false;
  input.value = "";
  runtime.marketListSignature = "";
  renderMarkets();
  selectSymbol(target.symbol, { focusChart: true });
  return true;
}

function marketListRows() {
  const query = $("marketSearch").value.trim().toUpperCase();
  const typeOrder = { stock: 0, spot: 1, swap: 2 };
  let rows = [...markets]
    .filter((item) => marketMatchesQuery(item, query))
    .filter((item) => state.marketCategory === "all" || item.category === state.marketCategory);
  if (query && state.marketCategory !== "all" && !rows.length) {
    const allMatches = [...markets].filter((item) => marketMatchesQuery(item, query));
    if (allMatches.length) {
      state.marketCategory = "all";
      rows = allMatches;
    }
  }
  return rows
    .sort((a, b) => {
      if (!query && state.marketCategory === "all") {
        const priorityDiff = (WATCHLIST_PRIORITY_MAP.get(a.symbol) ?? 999) - (WATCHLIST_PRIORITY_MAP.get(b.symbol) ?? 999);
        if (priorityDiff) return priorityDiff;
      }
      const typeDiff = (typeOrder[a.type] ?? 9) - (typeOrder[b.type] ?? 9);
      return typeDiff || a.symbol.localeCompare(b.symbol);
    });
}

function marketRowHtml(item) {
  const badge = marketDataBadge(item);
  return `
      <button type="button" class="market-row ${item.symbol === state.symbol ? "active" : ""}" data-symbol="${item.symbol}" aria-label="切换到 ${escapeHtml(item.symbol)} ${escapeHtml(item.name)}" aria-pressed="${item.symbol === state.symbol ? "true" : "false"}">
        <div>
          <div class="market-symbol">${item.symbol}</div>
          <div class="market-sub-line">
            <span class="market-sub">${marketTypeLabel(item)} / ${item.name}</span>
            <span class="market-data-badge ${badge.tone}" title="${escapeHtml(badge.detail)}">${escapeHtml(badge.label)}</span>
          </div>
        </div>
        <div>
          <div class="market-price">${item.price}</div>
          <div class="market-change ${cssMove(String(item.change).replace("%", ""))}">${item.change}</div>
        </div>
      </button>
    `;
}

function updateMarketRowDom(row, item) {
  if (!row) return;
  row.classList.toggle("active", item.symbol === state.symbol);
  row.setAttribute("aria-pressed", item.symbol === state.symbol ? "true" : "false");
  row.querySelector(".market-price").textContent = item.price || "--";
  const change = row.querySelector(".market-change");
  change.textContent = item.change || "--";
  change.className = `market-change ${cssMove(String(item.change).replace("%", ""))}`;
  const badge = marketDataBadge(item);
  const badgeEl = row.querySelector(".market-data-badge");
  if (badgeEl) {
    badgeEl.textContent = badge.label;
    badgeEl.className = `market-data-badge ${badge.tone}`;
    badgeEl.title = badge.detail || "";
  }
}

function selectorEscape(value) {
  if (window.CSS && typeof window.CSS.escape === "function") return window.CSS.escape(String(value));
  return String(value).replace(/["\\]/g, "\\$&");
}

function keepActiveMarketRowVisible() {
  const rail = document.querySelector(".market-rail");
  const row = document.querySelector(`.market-row[data-symbol="${selectorEscape(state.symbol)}"]`);
  if (!rail || !row) return;
  const railTop = rail.scrollTop;
  const railBottom = railTop + rail.clientHeight;
  const rowTop = row.offsetTop;
  const rowBottom = rowTop + row.offsetHeight;
  const margin = 84;
  if (rowTop < railTop + margin) {
    rail.scrollTop = Math.max(0, rowTop - margin);
  } else if (rowBottom > railBottom - margin) {
    rail.scrollTop = rowBottom - rail.clientHeight + margin;
  }
}

function renderMarkets(options = {}) {
  const pricesOnly = Boolean(options.pricesOnly);
  const target = $("marketList");
  if (!target) return;
  renderMarketRailDisclosureSummary();
  const rows = marketListRows();
  syncMarketCategoryTabs();
  const query = $("marketSearch").value.trim().toUpperCase();
  const signature = `${state.marketCategory}|${query}|${rows.map((item) => item.symbol).join("|")}`;
  const shouldRebuild = signature !== runtime.marketListSignature;
  if (shouldRebuild) {
    target.innerHTML = rows.map(marketRowHtml).join("");
    runtime.marketListSignature = signature;
  } else {
    rows.forEach((item) => updateMarketRowDom(target.querySelector(`.market-row[data-symbol="${selectorEscape(item.symbol)}"]`), item));
  }
  renderMarketTickerPanel({ pricesOnly: pricesOnly && !shouldRebuild });
  renderStockPanel({ pricesOnly: pricesOnly && !shouldRebuild });
}

function scheduleMarketRender(pricesOnly = true) {
  runtime.marketRenderPricesOnly = runtime.marketRenderTimer ? runtime.marketRenderPricesOnly && pricesOnly : pricesOnly;
  if (runtime.marketRenderTimer) return;
  runtime.marketRenderTimer = requestAnimationFrame(() => {
    const mode = runtime.marketRenderPricesOnly;
    runtime.marketRenderTimer = null;
    runtime.marketRenderPricesOnly = true;
    renderMarkets({ pricesOnly: mode });
  });
}

function activeStockChartQuoteGuard(data = {}, symbol = state.symbol) {
  const cleanSymbol = canonicalTickerSymbol(symbol);
  if (!isStockMarket(cleanSymbol) || canonicalTickerSymbol(state.symbol) !== cleanSymbol) return null;
  if (canonicalTickerSymbol(state.chartDataSymbol) !== cleanSymbol || !state.candles.length) return null;
  const quality = state.chartQuality || {};
  if (quality.preview || isPreviewChartSource(quality.source, quality.warningText || quality.warning || "")) return null;
  const referenceClose = Number(state.candles[state.candles.length - 1]?.close);
  if (!Number.isFinite(referenceClose) || referenceClose <= 0) return null;
  const previousClose = Number(state.candles[state.candles.length - 2]?.close);
  const guard = window.HakimiStockQuoteGuard;
  if (!guard || typeof guard.chooseStockDisplayQuote !== "function") return null;
  const selection = guard.chooseStockDisplayQuote({
    price: Number(data.last),
    candleClose: referenceClose,
    previousCandleClose: previousClose,
    chartTrusted: true,
    source: data.source || data.origin_source || data.originSource,
    quoteQuality: data.quote_quality || data.quoteQuality,
    changeBasis: data.change_basis || data.changeBasis,
    previousClose: data.prevClose || data.previousClose,
    changePct: data.change24h_pct ?? data.changePct,
  });
  return {
    decision: selection.decision,
    referenceClose: selection.displayPrice,
    previousClose,
    changePct: selection.displayChangePct,
    source: quality.source || quality.sourceName || currentMarket(cleanSymbol).source || "chart",
  };
}

function updateMarketFromTicker(data, options = {}) {
  if (!data?.instId && !data?.symbol) return;
  const key = data.symbol || data.instId;
  const last = Number(data.last);
  const open24h = Number(data.open24h);
  const change = Number.isFinite(Number(data.change24h_pct)) ? Number(data.change24h_pct) : open24h ? ((last - open24h) / open24h) * 100 : 0;
  const index = markets.findIndex((item) => item.symbol === key || item.instId === key);
  if (index < 0) return;
  const chartGuard = activeStockChartQuoteGuard(data, key);
  if (chartGuard && !chartGuard.decision.allowed) {
    markets[index] = {
      ...markets[index],
      source: chartGuard.source,
      price: number(chartGuard.referenceClose, chartGuard.referenceClose > 100 ? 1 : 4),
      change: `${chartGuard.changePct >= 0 ? "+" : ""}${number(chartGuard.changePct, 2)}%`,
      rawChange: chartGuard.changePct,
      quoteSource: "",
      quoteQuality: {},
      quotePreviousClose: null,
      quoteChangeBasis: "",
      quoteChangePct: null,
      marketSession: data.market_session || markets[index].marketSession || null,
    };
    if (options.syncActive !== false) {
      state.lastPrice = chartGuard.referenceClose;
      syncActiveSymbolHeader("低质量报价已隔离，显示K线最新价格");
    }
    return;
  }
  const baseVolume24h = Number(data.vol24h);
  const quoteVolume24h = Number(data.volCcy24h);
  const incomingQuoteQuality = data.quote_quality && typeof data.quote_quality === "object" ? data.quote_quality : null;
  const incomingMarketSession = data.market_session && typeof data.market_session === "object" ? data.market_session : null;
  const stockQuoteEvidence = markets[index].type === "stock";
  const quoteQuality = incomingQuoteQuality || (stockQuoteEvidence ? {} : markets[index].quoteQuality || {});
  const verifiedPreviousClose = Number(data.prevClose);
  const verifiedChange = verifiedPreviousClose > 0 ? (last / verifiedPreviousClose - 1) * 100 : Number.NaN;
  const verifiedExtreme = incomingQuoteQuality?.status === "READY"
    && data.change_basis === "previous_close"
    && Number.isFinite(verifiedChange)
    && Math.abs(verifiedChange - change) <= 0.5;
  const changeNeedsReview = markets[index].type === "stock"
    && (Boolean(incomingQuoteQuality?.quarantined) || (Math.abs(change) >= 45 && !verifiedExtreme));
  markets[index] = {
    ...markets[index],
    source: data.source || markets[index].source,
    quoteSource: incomingQuoteQuality
      ? (data.source || markets[index].quoteSource || markets[index].source)
      : stockQuoteEvidence ? "" : markets[index].quoteSource,
    originSource: data.origin_source || data.originSource || markets[index].originSource || "",
    warning: data.warning || "",
    dataAgeMs: data.data_age_ms ?? markets[index].dataAgeMs ?? null,
    exchange: data.exchange || markets[index].exchange,
    market: data.market || markets[index].market,
    price: last > 0 ? number(last, last > 100 ? 1 : 4) : "--",
    change: changeNeedsReview ? "待核" : `${change >= 0 ? "+" : ""}${number(change, 2)}%`,
    rawChange: changeNeedsReview ? 0 : change,
    quoteQuality,
    quotePreviousClose: incomingQuoteQuality && verifiedPreviousClose > 0
      ? verifiedPreviousClose
      : stockQuoteEvidence ? null : markets[index].quotePreviousClose,
    quoteChangeBasis: incomingQuoteQuality
      ? (data.change_basis || "")
      : stockQuoteEvidence ? "" : markets[index].quoteChangeBasis || "",
    quoteChangePct: incomingQuoteQuality && Number.isFinite(Number(data.change24h_pct))
      ? Number(data.change24h_pct)
      : stockQuoteEvidence ? null : markets[index].quoteChangePct,
    marketSession: incomingMarketSession || markets[index].marketSession || null,
    high24h: data.high24h,
    low24h: data.low24h,
    vol24h: markets[index].type === "stock"
      ? (Number.isFinite(baseVolume24h) ? baseVolume24h : markets[index].vol24h)
      : (data.volCcy24h || data.vol24h),
    baseVolume24h: Number.isFinite(baseVolume24h) ? baseVolume24h : markets[index].baseVolume24h,
    quoteVolume24h: Number.isFinite(quoteVolume24h) ? quoteVolume24h : markets[index].quoteVolume24h,
    bidPx: data.bidPx,
    askPx: data.askPx,
    lastUpdated: Number(data.ts || Date.now()),
  };
  if (options.syncActive !== false && (markets[index].symbol === state.symbol || markets[index].instId === state.symbol)) {
    syncActiveMarketQuote(data.source ? `报价同步：${String(data.source).toUpperCase()}` : "报价已同步");
  }
}

function updateTickerPanelRow(row, item) {
  if (!row) return;
  row.classList.toggle("active", item.symbol === state.symbol);
  const cells = row.querySelectorAll(":scope > span");
  if (cells[1]) cells[1].textContent = item.price || "--";
  if (cells[2]) {
    cells[2].textContent = item.change || "--";
    cells[2].className = cssMove(item.rawChange ?? String(item.change).replace("%", ""));
  }
  if (cells[3]) cells[3].textContent = compact(marketVolumeForDisplay(item));
  if (cells[4]) cells[4].textContent = bidAskText(item.bidPx, item.askPx, 2);
}

function renderMarketTickerPanel(options = {}) {
  const target = $("marketTickerRows");
  if (!target) return;
  const signature = markets.map((item) => item.symbol).join("|");
  if (!options.pricesOnly || runtime.marketTickerSignature !== signature) {
    target.innerHTML = markets.map((item) => `
    <div class="market-ticker-row ${item.symbol === state.symbol ? "active" : ""}" data-symbol="${item.symbol}">
      <span><strong>${item.symbol}</strong><em>${marketTypeLabel(item)} / ${item.name}</em></span>
      <span>${item.price || "--"}</span>
      <span class="${cssMove(item.rawChange ?? String(item.change).replace("%", ""))}">${item.change || "--"}</span>
      <span>${compact(marketVolumeForDisplay(item))}</span>
      <span>${bidAskText(item.bidPx, item.askPx, 2)}</span>
    </div>
  `).join("");
    runtime.marketTickerSignature = signature;
  } else {
    markets.forEach((item) => updateTickerPanelRow(target.querySelector(`.market-ticker-row[data-symbol="${item.symbol}"]`), item));
  }
  const latest = Math.max(0, ...markets.map((item) => Number(item.lastUpdated || 0)));
  $("marketTickerState").textContent = latest ? `后台刷新 ${timeText(latest)}` : "后台刷新";
}

function updateStockPanelRow(row, item) {
  if (!row) return;
  row.classList.toggle("active", item.symbol === state.symbol);
  const cells = row.querySelectorAll(":scope > span");
  if (cells[1]) cells[1].textContent = item.price || "--";
  if (cells[2]) {
    cells[2].textContent = item.change || "--";
    cells[2].className = cssMove(item.rawChange ?? String(item.change).replace("%", ""));
  }
  if (cells[3]) cells[3].textContent = compact(marketVolumeForDisplay(item));
  if (cells[4]) cells[4].textContent = stockSourceLabel(item);
}

function renderStockPanel(options = {}) {
  const target = $("stockRows");
  if (!target) return;
  const rows = markets.filter((item) => item.type === "stock");
  $("stockState").textContent = state.futu?.message ? `${rows.length} stocks / ${state.futu.message}` : `${rows.length} stocks`;
  const signature = rows.map((item) => item.symbol).join("|");
  if (!options.pricesOnly || runtime.stockPanelSignature !== signature) {
    target.innerHTML = rows.map((item) => `
    <div class="stock-row ${item.symbol === state.symbol ? "active" : ""}" data-symbol="${item.symbol}">
      <span><strong>${item.symbol}</strong><em>${item.name}</em></span>
      <span>${item.price || "--"}</span>
      <span class="${cssMove(item.rawChange ?? String(item.change).replace("%", ""))}">${item.change || "--"}</span>
      <span>${compact(marketVolumeForDisplay(item))}</span>
      <span>${stockSourceLabel(item)}</span>
    </div>
  `).join("");
    runtime.stockPanelSignature = signature;
  } else {
    rows.forEach((item) => updateStockPanelRow(target.querySelector(`.stock-row[data-symbol="${item.symbol}"]`), item));
  }
}

function futuDeepSymbol() {
  if (isStockMarket()) return state.symbol;
  return markets.find((item) => item.type === "stock")?.symbol || "AAPL";
}

function formatFutuMetric(item = {}) {
  const value = item.value;
  if (item.format === "text") return escapeHtml(value || "--");
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed === 0) return "--";
  if (item.format === "pct") return `${number(parsed, 2)}%`;
  if (item.format === "x") return `${number(parsed, 2)}x`;
  if (item.format === "compact") return compact(parsed);
  if (item.format === "price") return number(parsed, parsed > 100 ? 2 : 4);
  return number(parsed, 2);
}

function renderFutuDeep(data) {
  state.futuDeep = data;
  const stateEl = $("futuDeepState");
  if (!stateEl) return;
  if (!data?.ok) {
    stateEl.textContent = "OFFLINE";
    stateEl.className = "down";
    $("futuDeepSummary").textContent = data?.error || "Futu enhanced data unavailable";
    $("futuDeepMetrics").innerHTML = "";
    $("futuOrderBookRows").innerHTML = `<div class="futu-deep-row"><span>Book</span><strong>--</strong><em>Waiting for OpenD or permission</em></div>`;
    $("futuCapitalRows").innerHTML = `<div class="futu-deep-row"><span>Flow</span><strong>--</strong><em>Waiting for data</em></div>`;
    $("futuTickerRows").innerHTML = `<div class="futu-deep-row"><span>Tape</span><strong>--</strong><em>Waiting for data</em></div>`;
    renderStockEvidencePanel(data);
    return;
  }
  stateEl.textContent = `${data.symbol} / ${data.market_state || "--"}`;
  stateEl.className = "up";
  $("futuDeepSummary").textContent = data.summary || "Futu enhanced data updated";
  $("futuDeepMetrics").innerHTML = (data.metrics || []).map((item) => `
    <div>
      <span>${escapeHtml(item.label)}</span>
      <strong class="${item.tone || "flat"}">${formatFutuMetric(item)}</strong>
    </div>
  `).join("");

  const bids = data.order_book?.bids || [];
  const asks = data.order_book?.asks || [];
  const depth = Math.max(bids.length, asks.length, 1);
  $("futuOrderBookRows").innerHTML = Array.from({ length: Math.min(depth, 10) }).map((_, index) => {
    const bid = bids[index] || {};
    const ask = asks[index] || {};
    return `
      <div class="futu-deep-row book">
        <span class="up">${bid.price ? number(bid.price, bid.price > 100 ? 2 : 4) : "--"} / ${compact(bid.volume)}</span>
        <strong>L${index + 1}</strong>
        <em class="down">${ask.price ? number(ask.price, ask.price > 100 ? 2 : 4) : "--"} / ${compact(ask.volume)}</em>
      </div>
    `;
  }).join("");

  const flow = data.capital_flow || {};
  const dist = data.capital_distribution?.net || {};
  const flowRows = (flow.rows || []).slice(-7).reverse();
  $("futuCapitalRows").innerHTML = `
    <div class="futu-deep-row">
      <span>Net flow</span><strong class="${cssMove(flow.net_total)}">${compact(flow.net_total)}</strong><em>Main ${compact(flow.main_net_total)}</em>
    </div>
    <div class="futu-deep-row">
      <span>Large net</span><strong class="${cssMove((dist.super_net || 0) + (dist.big_net || 0))}">${compact((dist.super_net || 0) + (dist.big_net || 0))}</strong><em>Super + big</em>
    </div>
    ${flowRows.map((row) => `
      <div class="futu-deep-row">
        <span>${escapeHtml(String(row.capital_flow_item_time || "").slice(11, 16) || "--")}</span>
        <strong class="${cssMove(row.in_flow)}">${compact(row.in_flow)}</strong>
        <em>Large ${compact((Number(row.super_in_flow) || 0) + (Number(row.big_in_flow) || 0))}</em>
      </div>
    `).join("")}
  `;

  const tickerRows = (data.ticker || []).slice(-9).reverse();
  $("futuTickerRows").innerHTML = tickerRows.map((row) => `
    <div class="futu-deep-row">
      <span>${escapeHtml(String(row.time || "").slice(11, 19) || "--")}</span>
      <strong class="${row.ticker_direction === "BUY" ? "up" : row.ticker_direction === "SELL" ? "down" : "flat"}">${number(row.price, Number(row.price) > 100 ? 2 : 4)}</strong>
      <em>${escapeHtml(row.ticker_direction || "--")} / ${compact(row.volume)}</em>
    </div>
  `).join("") || `<div class="futu-deep-row"><span>Tape</span><strong>--</strong><em>Waiting for subscription data</em></div>`;
  mergeFutuTickerRowsIntoStockLog(data);
  renderBook();

  if (data.errors?.length) {
    $("futuDeepSummary").textContent = `${data.summary || "Futu enhanced data updated"} / ${data.errors.length} items need subscription or permission`;
  }
  renderStockEvidencePanel(data);
}

function refreshFutuDeepSideInsight() {
  renderSideInsights();
}

async function loadFutuDeep(force = false, requestVersion = runtime.symbolVersion) {
  const symbol = futuDeepSymbol();
  try {
    $("futuDeepState").textContent = `${symbol} loading`;
    $("futuDeepState").className = "flat";
    const data = await api(`/api/futu/deep?symbol=${encodeURIComponent(symbol)}&force=${force ? "true" : "false"}`);
    if (requestVersion !== runtime.symbolVersion || symbol !== futuDeepSymbol()) return null;
    renderFutuDeep(data);
    if (symbol === state.symbol) maybeRefreshActiveStockCandles("futu_deep", force);
    refreshFutuDeepSideInsight();
    return data;
  } catch (error) {
    if (requestVersion !== runtime.symbolVersion || symbol !== futuDeepSymbol()) return null;
    renderFutuDeep({ ok: false, symbol, error: error.message });
    refreshFutuDeepSideInsight();
    return null;
  }
}

function sideInsightRow(label, value, detail = "", tone = "flat") {
  return `
    <div class="side-insight-row">
      <span>${escapeHtml(label)}</span>
      <strong class="${tone}">${escapeHtml(value)}</strong>
      <em>${escapeHtml(detail)}</em>
    </div>
  `;
}

function renderSideInsights() {
  const target = $("sideInsightRows");
  if (!target) return;
  document.querySelectorAll("[data-side-insight]").forEach((button) => {
    button.classList.toggle("active", button.dataset.sideInsight === state.sideInsight);
  });
  const market = currentMarket();
  const last = Number(state.lastPrice || String(market.price || "").replaceAll(",", ""));
  const high = Number(market.high24h || $("high24h")?.textContent?.replaceAll(",", ""));
  const low = Number(market.low24h || $("low24h")?.textContent?.replaceAll(",", ""));
  const vol = marketVolumeForDisplay(market);
  const bid = Number(market.bidPx || 0);
  const ask = Number(market.askPx || 0);
  const rangePct = high > 0 && low > 0 ? (high / low - 1) * 100 : 0;
  const spreadPct = ask > 0 && bid > 0 ? (ask - bid) / ((ask + bid) / 2) * 100 : 0;
  const mode = state.sideInsight || "volatility";
  const futu = state.futuDeep || {};
  const stateLabel = SIDE_INSIGHT_LABELS?.[mode] || "AI";
  if ($("sideInsightState")) $("sideInsightState").textContent = `${market.symbol || state.symbol} / ${stateLabel}`;

  if (mode === "volatility") {
    target.innerHTML = [
      sideInsightRow("Last", last > 0 ? number(last, last > 100 ? 2 : 4) : "--", marketTypeLabel(market), cssMove(market.rawChange || 0)),
      sideInsightRow("Range", rangePct ? `${number(rangePct, 2)}%` : "--", `${high ? number(high, 2) : "--"} / ${low ? number(low, 2) : "--"}`, rangePct > 6 ? "down" : rangePct > 2 ? "flat" : "up"),
      sideInsightRow("Spread", spreadPct ? `${number(spreadPct, 4)}%` : "--", `${bid ? number(bid, 2) : "--"} / ${ask ? number(ask, 2) : "--"}`, spreadPct > 0.08 ? "down" : "up"),
      sideInsightRow("Volume", compact(vol), "Realtime volatility data", "flat"),
      sideInsightRow("Chart", $("chartStatus")?.textContent || "--", $("chartRange")?.textContent || "--", "flat"),
    ].join("");
    return;
  }

  if (mode === "capital") {
    const flow = futu.capital_flow || {};
    const dist = futu.capital_distribution?.net || {};
    const metrics = state.contractCenter?.metrics || {};
    target.innerHTML = (isStockMarket() || futu.ok) ? [
      sideInsightRow("Futu", futu.market_state || state.futu?.message || "--", futu.symbol || futuDeepSymbol(), futu.ok ? "up" : "flat"),
      sideInsightRow("Net flow", compact(flow.net_total), `Main ${compact(flow.main_net_total)}`, cssMove(flow.net_total)),
      sideInsightRow("Large net", compact((dist.super_net || 0) + (dist.big_net || 0)), dist.update_time || "--", cssMove((dist.super_net || 0) + (dist.big_net || 0))),
      sideInsightRow("Book depth", `${futu.order_book?.bids?.length || 0}/${futu.order_book?.asks?.length || 0}`, "Bid/ask levels", "flat"),
    ].join("") : [
      sideInsightRow("Funding", `${number(metrics.funding_rate_pct, 5)}%`, `Annual ${number(metrics.funding_annualized_pct, 2)}%`, cssMove(metrics.funding_rate_pct)),
      sideInsightRow("Open interest", compact(metrics.open_interest_ccy || metrics.open_interest), "Contract OI", "flat"),
      sideInsightRow("Mark/index basis", `${number(metrics.mark_index_basis_pct, 5)}%`, "Perp deviation", cssMove(metrics.mark_index_basis_pct)),
      sideInsightRow("Spot/swap basis", `${number(metrics.spot_swap_basis_pct, 5)}%`, "Basis watch", cssMove(metrics.spot_swap_basis_pct)),
    ].join("");
    return;
  }

  if (mode === "news") {
    const news = state.research?.news || [];
    const events = state.research?.events || [];
    target.innerHTML = [
      sideInsightRow("Research", state.research?.summary || "Waiting for research panel", state.symbol, "flat"),
      ...news.slice(0, 4).map((row) => sideInsightRow(row.source || "News", row.title || "--", row.published || "", "flat")),
      ...events.slice(0, 2).map((row) => sideInsightRow(row.time || "Event", row.title || "--", row.impact || "", "flat")),
    ].join("");
    return;
  }

  if (mode === "watch") {
    const detail = futu.watch_detail || {};
    const sessions = detail.session_prices || {};
    target.innerHTML = [
      sideInsightRow("Watch", detail.symbol || market.symbol || state.symbol, detail.name || market.name || "--", futu.ok ? "up" : "flat"),
      sideInsightRow("Market", `${detail.market || market.market || "--"} / ${detail.quote || "--"}`, detail.sector || marketTypeLabel(market), "flat"),
      sideInsightRow("Session", detail.market_state || futu.market_state || "--", detail.sec_status || detail.update_time || "--", "flat"),
      sideInsightRow("Pre/post", `${number(sessions.pre, 2)} / ${number(sessions.post, 2)}`, `Overnight ${number(sessions.overnight, 2)}`, "flat"),
    ].join("");
    return;
  }

  if (mode === "valuation") {
    const valuation = futu.valuation || {};
    target.innerHTML = [
      sideInsightRow("PE/PB", `${number(valuation.pe_ttm_ratio, 2)} / ${number(valuation.pb_ratio, 2)}`, "TTM / PB", "flat"),
      sideInsightRow("Valuation pct", valuation.valuation_percentile ? `${number(valuation.valuation_percentile, 1)}%` : "--", valuation.valuation_update || "Futu valuation", cssMove(Number(valuation.valuation_percentile || 0) - 50)),
      sideInsightRow("Market cap", compact(valuation.total_market_val), `Float ${compact(valuation.circular_market_val)}`, "flat"),
    ].join("");
    return;
  }

  if (mode === "unusual") {
    const unusual = futu.unusual || {};
    const rows = unusual.rows || [];
    target.innerHTML = [
      sideInsightRow("Unusual", `${rows.length}`, `Imbalance ${number(unusual.imbalance_pct, 1)}%`, rows.length ? "up" : "flat"),
      ...rows.slice(0, 8).map((row) => sideInsightRow(row.label || "Signal", row.value || "--", row.detail || row.source || "", row.tone || "flat")),
    ].join("") || sideInsightRow("Unusual", "--", "Waiting for FutuOpenD", "flat");
    return;
  }

  if (mode === "holder") {
    const holders = futu.institutional || [];
    const ratings = futu.rating || [];
    target.innerHTML = [
      sideInsightRow("Institutions", `${holders.length} rows`, futu.futu_code || futu.symbol || "--", holders.length ? "up" : "flat"),
      ...holders.slice(0, 5).map((row) => sideInsightRow(row.holder_name || row.institution_name || row.name || "Institution", row.holding_ratio || row.holding_shares || "--", row.update_time || row.date || "", "flat")),
      sideInsightRow("Ratings", `${ratings.length} rows`, "Broker views", ratings.length ? "flat" : "down"),
      ...ratings.slice(0, 4).map((row) => sideInsightRow(row.broker_name || row.institution || row.name || "Rating", row.rating || row.target_price || "--", row.update_time || row.date || "", "flat")),
    ].join("");
    return;
  }

  const ai = futu.ai_news_summary || {};
  const war = state.strategyWarRoom || {};
  const analysis = state.latestStrategyAnalysis || state.paper?.ai_analysis || {};
  target.innerHTML = [
    sideInsightRow("AI summary", ai.bias || strategyPlanningDirectionText(analysis), ai.source || "Local AI/DeepSeek", "flat"),
    sideInsightRow("Confidence", ai.confidence ? `${number(ai.confidence, 1)}%` : "--", ai.summary || "Waiting for analysis", "flat"),
    ...(ai.bullets || []).slice(0, 4).map((text, index) => sideInsightRow(`Point ${index + 1}`, text, "", "flat")),
    sideInsightRow("Strategy", war.summary || "Waiting for strategy room", $("strategySelect")?.selectedOptions?.[0]?.textContent || "--", "flat"),
    sideInsightRow("研究规划 TP/SL", `${strategyPlanningValue(analysis, "take_profit") ? number(strategyPlanningValue(analysis, "take_profit"), 2) : "--"} / ${strategyPlanningValue(analysis, "stop_loss") ? number(strategyPlanningValue(analysis, "stop_loss"), 2) : "--"}`, "非订单 · 手动值仍需独立风险合同", "flat"),
  ].join("");
}

const SIDE_INSIGHT_TABS = [
  ["volatility", "波动"],
  ["capital", "资金"],
  ["watch", "自选"],
  ["valuation", "估值"],
  ["unusual", "异动"],
  ["holder", "机构"],
  ["ai", "AI摘要"],
];

const SIDE_INSIGHT_LABELS = Object.fromEntries(SIDE_INSIGHT_TABS);

function setupRightInsightPanel() {
  if ($("sideInsightRows")) return;
  const stack = document.querySelector(".right-stack");
  if (!stack) return;
  const section = document.createElement("section");
  section.className = "side-insight-panel";
  section.innerHTML = `
    <div class="panel-title">
      <strong>右侧作战栏</strong>
      <span id="sideInsightState">波动 / 自选 / 估值 / 异动 / 机构 / AI</span>
    </div>
    <div id="sideInsightTabs" class="side-insight-tabs">
      ${SIDE_INSIGHT_TABS.map(([id, label], index) => `
        <button class="${index === 0 ? "active" : ""}" data-side-insight="${id}">${label}</button>
      `).join("")}
    </div>
    <div id="sideInsightRows" class="side-insight-list"></div>
  `;
  stack.appendChild(section);
  section.querySelectorAll("[data-side-insight]").forEach((button) => {
    button.addEventListener("click", () => {
      state.sideInsight = button.dataset.sideInsight || "volatility";
      renderSideInsights();
    });
  });
}

function insightFirst(row = {}, keys = [], fallback = "--") {
  for (const key of keys) {
    const value = row?.[key];
    if (value !== undefined && value !== null && value !== "") return value;
  }
  return fallback;
}

function insightNumber(value, digits = 2, zeroAsBlank = true) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || (zeroAsBlank && parsed === 0)) return "--";
  return number(parsed, digits);
}

function insightCompact(value, zeroAsBlank = true) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || (zeroAsBlank && parsed === 0)) return "--";
  return compact(parsed);
}

function insightText(value, fallback = "--") {
  if (value === undefined || value === null || value === "") return fallback;
  if (typeof value === "number") return Math.abs(value) >= 1000 ? compact(value) : number(value, 2);
  if (typeof value === "object") return JSON.stringify(value).slice(0, 64);
  return String(value);
}

function insightPercent(value, digits = 2) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed === 0) return "--";
  return `${number(parsed, digits)}%`;
}

function insightRecordRows(records = [], labelKeys = [], valueKeys = [], detailKeys = [], fallbackLabel = "记录", limit = 5) {
  return records.slice(0, limit).map((row) => {
    const value = insightFirst(row, valueKeys, "--");
    const parsed = Number(value);
    return sideInsightRow(
      insightText(insightFirst(row, labelKeys, fallbackLabel)),
      Number.isFinite(parsed) ? insightText(parsed) : insightText(value),
      insightText(insightFirst(row, detailKeys, ""), ""),
      cssMove(Number.isFinite(parsed) ? parsed : 0),
    );
  });
}

function selectStockSession(session = "all") {
  if (!isStockMarket()) return;
  state.stockSession = ["all", "pre", "regular", "post", "overnight"].includes(session) ? session : "all";
  if (!isStockMinuteBar(state.bar)) {
    state.bar = "1m";
    syncTimeframeTabs();
  }
  state.chartMode = "line";
  syncStockSessionTabs();
  state.chartView.offset = 0;
  state.chartView.visible = stockVisibleBarsForBar(state.bar);
  runtime.chartUserZoomed = false;
  $("chartStatus").textContent = `正在切换${stockIntradayLabel(state.stockSession)}...`;
  renderInstantPreviewCandles(state.symbol, state.bar);
  loadCandles().catch(() => {});
  loadStockSourceControl(state.symbol, runtime.symbolVersion).catch(() => {});
}

function syncStockSessionTabs() {
  const tabs = $("stockSessionTabs");
  if (!tabs) return;
  tabs.classList.toggle("hidden", !isStockMarket());
  tabs.querySelectorAll("button").forEach((button) => {
    button.classList.toggle("active", button.dataset.stockSession === state.stockSession);
  });
  syncChartControlLabels();
}

function syncTimeframeTabs() {
  const tabs = $("timeframeTabs");
  if (!tabs) return;
  tabs.querySelectorAll("button").forEach((button) => {
    button.classList.toggle("active", button.dataset.bar === state.bar);
  });
  syncChartControlLabels();
}

function clearSymbolTasks() {
  for (const timer of runtime.symbolTaskTimers || []) clearTimeout(timer);
  runtime.symbolTaskTimers = [];
}

function abortMarketRequests() {
  runtime.chartRequestAbortController?.abort();
  runtime.chartRequestAbortController = null;
  runtime.chartRequestKey = "";
  runtime.stockQuoteAbortController?.abort();
  runtime.stockQuoteAbortController = null;
}

function isAbortError(error) {
  return error?.name === "AbortError" || String(error?.message || "").toLowerCase().includes("aborted");
}

function scheduleSymbolTask(version, delayMs, task) {
  const timer = setTimeout(() => {
    runtime.symbolTaskTimers = (runtime.symbolTaskTimers || []).filter((item) => item !== timer);
    if (runtime.symbolVersion !== version) return;
    try {
      const result = task();
      if (result?.catch) result.catch(() => {});
    } catch (error) {
      // Background refreshes should not block chart switching.
    }
  }, delayMs);
  runtime.symbolTaskTimers.push(timer);
  return timer;
}

function normalizeAiRoomSymbol(value) {
  const raw = String(value || "").trim().toUpperCase().replace(/\s+/g, "");
  if (!raw) return state.symbol;
  const hkMatch = raw.match(/^HK\.?(\d{1,5})$/);
  if (hkMatch) return `HK.${hkMatch[1].padStart(5, "0")}`;
  if (/^\d{5}$/.test(raw)) return `HK.${raw}`;
  if (/^(BTC|ETH|SOL|DOGE|BNB)$/.test(raw)) return `${raw}-USDT`;
  return raw;
}

function ensureMarketSymbol(symbol) {
  const normalized = normalizeAiRoomSymbol(symbol);
  const existing = markets.find((item) => item.symbol === normalized || item.instId === normalized);
  if (existing) return existing.symbol;
  const isOkxLike = normalized.includes("-USDT");
  const isSwap = normalized.endsWith("-SWAP");
  const isHk = normalized.startsWith("HK.");
  const row = isOkxLike
    ? {
        symbol: normalized,
        instId: normalized,
        name: normalized.replace("-USDT-SWAP", " Perpetual").replace("-USDT", ""),
        category: isSwap ? "swap" : "spot",
        type: isSwap ? "swap" : "spot",
        source: "okx",
        price: "--",
        change: "--",
      }
    : {
        symbol: normalized,
        instId: normalized,
        name: isHk ? `HK ${normalized.slice(3)}` : normalized,
        category: "stocks",
        type: "stock",
        source: isHk ? "yahoo" : "stooq",
        market: isHk ? "HK" : "US",
        price: "--",
        change: "--",
      };
  markets.unshift(row);
  return row.symbol;
}

function renderAiRoomSymbolSuggestions() {
  const input = $("aiRoomSymbolInput");
  const target = $("aiRoomSymbolSuggestions");
  if (!input || !target) return;
  const query = String(input.value || "").trim().toUpperCase();
  if (!query) {
    target.innerHTML = "";
    target.classList.remove("open");
    return;
  }
  const normalized = normalizeAiRoomSymbol(query);
  const rows = markets
    .filter((item) => item.symbol.includes(query) || item.symbol.includes(normalized) || String(item.name || "").toUpperCase().includes(query))
    .slice(0, 7);
  const hasExact = rows.some((item) => item.symbol === normalized);
  const suggestionRows = hasExact ? rows : [{ symbol: normalized, name: "临时载入", type: normalized.includes("-USDT") ? "crypto" : "stock" }, ...rows].slice(0, 7);
  target.innerHTML = suggestionRows.map((item) => `
    <button type="button" data-ai-room-suggestion="${escapeHtml(item.symbol)}">
      <strong>${escapeHtml(item.symbol)}</strong>
      <span>${escapeHtml(item.name || item.type || "symbol")}</span>
    </button>
  `).join("");
  target.classList.toggle("open", suggestionRows.length > 0);
}

function renderAiRoomHeader() {
  const input = $("aiRoomSymbolInput");
  if (input && document.activeElement !== input) input.value = state.symbol;
  const market = currentMarket();
  const quality = state.chartQuality || {};
  const local = frontendMarketAiLocal();
  const trend = state.trendCockpit?.symbol === state.symbol ? state.trendCockpit : null;
  const anomalyRows = state.anomalyRadar?.rows || [];
  const anomaly = state.selectedAnomaly?.symbol === state.symbol
    ? state.selectedAnomaly
    : anomalyRows.find((row) => row.symbol === state.symbol) || null;
  const probabilities = trend?.probabilities || {};
  const longRate = Number(probabilities.long_win_rate_pct);
  const shortRate = Number(probabilities.short_win_rate_pct);
  const hasProbabilities = Number.isFinite(longRate) && Number.isFinite(shortRate);
  const support = Number(local.support || 0);
  const resistance = Number(local.resistance || 0);
  const priority = anomaly ? anomalyPriority(anomaly) : null;
  const nextCondition = anomaly?.next_observation
    || anomaly?.waiting_conditions?.[0]
    || trend?.waiting_conditions?.[0]
    || "等待量能、结构或数据源确认。";
  if ($("aiRoomTitle")) $("aiRoomTitle").textContent = `${state.symbol} 研究会议`;
  if ($("aiRoomMeta")) {
    const dataText = [marketTypeLabel(market), market.name || market.instId || state.symbol, state.bar, stockSourceLabel(market)].filter(Boolean).join(" / ");
    $("aiRoomMeta").textContent = `${dataText} / 仅观察 / 仅研究 / 仅模拟盘验证`;
  }
  document.querySelectorAll("[data-ai-room-symbol]").forEach((button) => {
    const quickSymbol = normalizeAiRoomSymbol(button.dataset.aiRoomSymbol || "");
    button.classList.toggle("active", quickSymbol === state.symbol);
  });
  const target = $("aiRoomTopSnapshot");
  if (!target) return;
  const trendText = workflowTrendLabel(trend, local);
  const trendDetail = anomaly
    ? `${priority?.label || anomaly.severity_label || "异动观察"} / 评分 ${number(anomaly.score || 0, 0)}`
    : `${trend ? "研究观察" : "等待研究观察"} / ${quality.mode || "研究快照"}`;
  const nextState = priority?.label || (trend ? "等待确认" : "等待研究");
  target.innerHTML = `
    <div><span>趋势结构</span><strong>${escapeHtml(trendText)}</strong><em title="${escapeHtml(trendDetail)}">${escapeHtml(trendDetail)}</em></div>
    <div><span>多空估计</span><strong>${hasProbabilities ? `多 ${number(longRate, 1)}% / 空 ${number(shortRate, 1)}%` : "等待走势样本"}</strong><em>当前样本和规则估计，不是保证</em></div>
    <div><span>关键位置</span><strong>${support ? `支 ${priceText(support)}` : "支 --"}</strong><em>${resistance ? `压 ${priceText(resistance)}` : "压 --"}</em></div>
    <div><span>研究观察</span><strong>${escapeHtml(nextState)}</strong><em title="${escapeHtml(nextCondition)}">${escapeHtml(nextCondition)}</em></div>
  `;
}

function loadAiRoomSymbolFromInput(options = {}) {
  const input = $("aiRoomSymbolInput");
  const symbol = ensureMarketSymbol(input?.value || state.symbol);
  if (input) input.value = symbol;
  runtime.forceMarketAiUntil = Date.now() + 4200;
  setInterfaceView("marketai");
  selectSymbol(symbol, { focusChart: false });
  setInterfaceView("marketai", false);
  renderAiRoomHeader();
  requestAnimationFrame(() => {
    setInterfaceView("marketai", false);
    if (state.interfaceView === "marketai") {
      document.querySelector(".chart-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
      drawChart();
    }
  });
  setTimeout(() => {
    if (state.symbol !== symbol) return;
    setInterfaceView("marketai", false);
    renderAiRoomHeader();
    drawChart();
  }, 650);
  if (options.meeting) {
    $("tradingAgentsState").textContent = `${symbol} 行情载入中，准备研究员会议`;
    $("tradingAgentsFinal").textContent = "正在组织 Codex/GPT、DeepSeek、豆包、GLM/智谱按顺序发言。先展示排队状态，行情快照载入后自动生成会议纪要。";
    renderAiRoomPendingMeeting(aiRoomMeetingQuestion());
    const version = runtime.symbolVersion;
    scheduleSymbolTask(version, 1400, () => {
      if (runtime.symbolVersion === version && state.symbol === symbol) runTradingAgentsRoom();
    });
  }
}

function focusAiRoomKeys() {
  setInterfaceView("marketai");
  const target = document.querySelector(".runtime-key-panel");
  if (target) target.scrollIntoView({ behavior: "smooth", block: "center" });
}

function aiRoomMeetingQuestion() {
  const roomQuestion = $("aiRoomQuestionInput")?.value?.trim() || "";
  if (roomQuestion) return roomQuestion;
  return $("marketAiQuestion")?.value?.trim() || `请按研究员会议形式分析 ${state.symbol}：日线波段、成交量、关键支撑压力、行业联动、反证和等待条件。`;
}

function syncAiRoomQuestionToMarketAi() {
  const question = aiRoomMeetingQuestion();
  if ($("marketAiQuestion")) $("marketAiQuestion").value = question;
}

function aiRoomPendingBubble(order, speaker, provider, message, status = "QUEUED") {
  return tradingAgentDebateRowHtml({
    order,
    speaker,
    provider,
    status,
    stance: "WAIT",
    role_title: "正在抽取研究身份",
    message,
  }, order - 1);
}

function renderAiRoomPendingMeeting(question) {
  runtime.tradingAgentsTranscriptSeq += 1;
  if ($("tradingAgentCards")) $("tradingAgentCards").innerHTML = `<div class="trading-agent-empty">正在随机分配本轮研究身份，随后四位 AI 按顺序进入聊天室。</div>`;
  if ($("tradingAgentDebateRows")) {
    $("tradingAgentDebateRows").innerHTML = [
      tradingAgentDebateRowHtml({ chat_key: "user", provider: "user", speaker: "我", status: "SENT", role_title: "研究问题", message: question }, 0),
      aiRoomPendingBubble(1, "Codex/GPT", "openai", "正在读取行情证据链", "THINK"),
    ].join("");
    $("tradingAgentDebateRows").scrollTop = $("tradingAgentDebateRows").scrollHeight;
  }
}

function focusActiveChart(smooth = true) {
  if (["research", "marketai"].includes(state.interfaceView)) {
    const scrollToCurrentViewChart = () => {
      document.querySelector(".chart-panel")?.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "start" });
      drawChart();
    };
    requestAnimationFrame(scrollToCurrentViewChart);
    setTimeout(scrollToCurrentViewChart, 180);
    return;
  }
  setInterfaceView("trade", false);
  syncWorkspaceNav(".ticker-header");
  document.querySelectorAll("#moduleNav button").forEach((button) => {
    button.classList.toggle("active", button.dataset.focus === ".ticker-header");
  });
  const scrollToChart = () => {
    const target = document.querySelector(".chart-panel") || document.querySelector(".ticker-header");
    if (target) target.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "start" });
    drawChart();
  };
  requestAnimationFrame(scrollToChart);
  setTimeout(scrollToChart, 180);
}

function selectSymbol(symbol, options = {}) {
  const sameSymbol = state.symbol === symbol;
  const version = ++runtime.symbolVersion;
  clearSymbolTasks();
  abortMarketRequests();
  runtime.stockQuoteSeq += 1;
  runtime.stockQuoteInFlight = false;
  state.symbol = symbol;
  state.marketSession = null;
  state.stockQuoteContext = null;
  state.marketSnapshotContext = null;
  state.stockSourceControl = null;
  resetPlatformSmallCapitalPlan();
  const market = currentMarket(symbol);
  const stock = market.type === "stock";
  if (state.marketCategory !== "all" && state.marketCategory !== market.category) {
    state.marketCategory = market.category || "all";
  }
  if (stock && isStockMinuteBar(state.bar)) state.chartMode = "line";
  if (!stock && state.chartMode === "line") state.chartMode = "candles";
  syncTimeframeTabs();
  syncStockSessionTabs();
  state.chartView.offset = 0;
  state.chartView.visible = stock ? stockVisibleBarsForBar(state.bar) : 180;
  runtime.chartUserZoomed = false;
  state.chartHover = null;
  state.latestStrategyAnalysis = null;
  loadDrawings();
  state.trades = [];
  state.stockPriceLog = [];
  state.orderBook = { asks: [], bids: [] };
  state.microSignal = null;
  syncActiveSymbolHeader(sameSymbol ? "刷新当前标的" : stock ? "正在切换股票行情" : "正在切换行情");
  $("chartStatus").textContent = sameSymbol ? "正在刷新当前K线..." : stock ? "正在切换股票K线..." : "正在切换行情K线...";
  renderAiRoomHeader();
  renderMarketWorkflowStrip();
  renderInstantPreviewCandles(symbol, state.bar);
  renderMarkets({ pricesOnly: true });
  closeCompactMarketRailDisclosure();
  if (options.focusChart) requestAnimationFrame(keepActiveMarketRowVisible);
  renderTrades();
  renderBook();
  resetResearchPanelForSymbol(symbol);
  scheduleSymbolTask(version, 80, () => ensureActiveChartPreview(symbol, state.bar));
  loadCandles(version);
  if (stock) connectSocket();
  else scheduleSymbolTask(version, 220, connectSocket);
  scheduleSymbolTask(version, 180, () => pollLiveTicker(false));
  scheduleSymbolTask(version, 520, () => loadTrendCockpit(symbol, version));
  scheduleSymbolTask(version, 700, () => loadStockSourceControl(symbol, version));
  scheduleSymbolTask(version, 1200, () => loadResearchPanel(version));
  scheduleSymbolTask(version, 2200, () => loadAnomalyRadar(false, version, { background: true }));
  if (stock) {
    scheduleSymbolTask(version, 2400, () => loadFutuDeep(false, version));
  } else {
    scheduleSymbolTask(version, 900, loadDerivatives);
    scheduleSymbolTask(version, 1300, () => loadMarketInsights(false));
  }
  if (["bot", "all"].includes(state.interfaceView)) {
    scheduleSymbolTask(version, 700, () => refreshPaper(false));
    scheduleSymbolTask(version, 900, loadStrategyCompare);
    scheduleSymbolTask(version, 1150, loadStrategyWarRoom);
    scheduleSymbolTask(version, 1500, loadBotCenter);
    scheduleSymbolTask(version, 1700, loadBotScheduler);
    scheduleSymbolTask(version, 1900, loadStrategyRobotProfiles);
    scheduleSymbolTask(version, 1200, estimateOrder);
  }
  if (state.interfaceView === "platform") scheduleSymbolTask(version, 450, loadPlatformControlCenter);
  if (options.focusChart) focusActiveChart(options.smooth !== false);
}

function setConnection(text, kind = "flat") {
  const el = $("connectionState");
  el.textContent = text;
  el.className = kind;
}

async function api(path, options = {}) {
  const response = await fetch(path, { cache: "no-store", ...options });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  const data = await response.json();
  if (data.ok === false) throw new Error(data.error || "api error");
  return data;
}

async function apiPost(path, payload) {
  const idempotencyKey = String(payload?.idempotencyKey || "");
  const response = await fetch(path, {
    method: "POST",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      "X-Hakimi-Write": "1",
      ...(idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {}),
    },
    body: JSON.stringify(payload || {}),
  });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  const data = await response.json();
  if (data.ok === false) throw new Error(data.error || "api error");
  return data;
}

function mutationId(path) {
  const suffix = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `hakimi:${path}:${suffix}`;
}

async function apiMutation(path, extraPayload = {}) {
  const url = new URL(path, window.location.origin);
  const payload = Object.fromEntries(url.searchParams.entries());
  Object.assign(payload, extraPayload || {});
  payload.idempotencyKey ||= mutationId(url.pathname);
  return apiPost(url.pathname, payload);
}

function platformTone(status) {
  const text = String(status || "").toUpperCase();
  if (["PASS", "READY", "RUNNING", "ACTIVE", "ARMED", "ONLINE", "PROTECTED", "COMPLETE"].includes(text)) return "up";
  if (["BLOCK", "BLOCKED", "LEGACY_BLOCKED", "VALIDATION_BLOCKED", "ERROR", "REJECTED", "UNSAFE", "RISK_BLOCK", "RUNTIME_READ_ONLY", "STRATEGY_AUTHORIZATION_BLOCK", "LIVE_TRADING_HARD_WALL_MISSING"].includes(text)) return "down";
  return "flat";
}

function researchStatusShort(status, fallback = "研究状态待核验") {
  const raw = String(status || "").trim().toUpperCase();
  if (!raw) return fallback;
  if (/(BLOCK|ERROR|FAIL|REJECT|UNSAFE|INVALID|MISSING)/.test(raw)) return "存在阻断";
  if (/(PASS|READY|COMPLETE|COMPLETED|DONE|SUCCESS|SUCCEEDED|UPDATED|UP_TO_DATE|VERIFIED|RECORDED|ONLINE|ACTIVE)/.test(raw)) return "已核对";
  if (/(RUN|WAIT|PENDING|NOT_RUN|UNKNOWN|STALE|DEGRADED|DUE)/.test(raw)) return "待复核";
  return fallback;
}

function evidenceStatusPresentation(kind, status) {
  const presentation = globalThis.HakimiEvidencePresentation;
  if (presentation?.statusPresentation) return presentation.statusPresentation(kind, status);
  const fallback = {
    market: ["行情证据不足 · 等待可信快照", "仅行情证据 · 不代表策略有效或交易授权"],
    forward: ["自然前向证据不足", "只读观察 · 模拟未授权 · 实盘永久硬锁"],
    plan: ["纯规划证据不足", "只读规划 · 不充值 · 不下单 · 模拟未授权 · 实盘永久硬锁"],
  }[kind] || ["证据状态待核验", "不授予模拟或实盘权限"];
  return {
    rawStatus: String(status || "UNKNOWN").trim().toUpperCase() || "UNKNOWN",
    label: fallback[0],
    permissionText: fallback[1],
  };
}

function evidenceForwardGapPresentation(input = {}) {
  const presentation = globalThis.HakimiEvidencePresentation;
  if (presentation?.forwardEvidenceGapPresentation) {
    return presentation.forwardEvidenceGapPresentation(input);
  }
  return {
    rawStatus: "UNKNOWN",
    gapKind: "UNKNOWN",
    text: "下一条尚缺证据：候选、只读调度与首个可信观察证据 · 仅观察，不补写旧样本；不授予模拟或实盘权限",
  };
}

function evidenceForwardStatisticalMaturityPresentation(dashboard = {}) {
  const presentation = globalThis.HakimiEvidencePresentation;
  if (presentation?.forwardStatisticalMaturityPresentation) {
    return presentation.forwardStatisticalMaturityPresentation(dashboard);
  }
  const legacy = Boolean(
    dashboard?.schema_version === "portfolio-forward-dashboard-v4"
    && !Object.hasOwn(dashboard, "statistical_maturity"),
  );
  return {
    valid: false,
    available: false,
    legacy,
    dashboardAuthoritySafe: false,
    rawStatus: legacy ? "NOT_AVAILABLE" : "BLOCK",
    statusText: legacy
      ? "旧版运行看板未携带统计成熟度 · 不作通过结论"
      : "统计来源或绑定不可核验 · 不使用成熟度结论",
    progressText: legacy
      ? "结果 --/-- · 调仓 --/-- · 结算 -- · 观察 --"
      : "结果 0/0 · 调仓 0/0 · 结算 0 · 观察 0",
    sourceBindingAvailable: false,
    sourceBindingRawStatus: legacy ? "NOT_AVAILABLE" : "CONTRADICTION",
    sourceBindingText: legacy
      ? "未取得本地归档覆盖 · 不作来源覆盖结论"
      : "本地归档与当前序列矛盾 · 不使用成熟度结论",
    sourceBindingDetailText: "仅本地归档跨工件绑定 · 不证明外部真实性或盈利 · 覆盖计数不可核验",
  };
}

function evidenceMarketTruthGapPresentation(input = {}) {
  const presentation = globalThis.HakimiEvidencePresentation;
  if (presentation?.marketTruthEvidenceGapPresentation) {
    return presentation.marketTruthEvidenceGapPresentation(input);
  }
  return {
    rawStatus: "UNKNOWN",
    gapKind: "UNKNOWN",
    text: "下一条尚缺证据：活动标的、报价来源、K 线来源与新鲜度证据 · 仅核行情，不生成策略结论或订单",
  };
}

function evidenceSmallCapitalGapPresentation(input = {}) {
  const presentation = globalThis.HakimiEvidencePresentation;
  if (presentation?.smallCapitalEvidenceGapPresentation) {
    return presentation.smallCapitalEvidenceGapPresentation(input);
  }
  return {
    rawStatus: String(input.status || "UNKNOWN").trim().toUpperCase() || "UNKNOWN",
    gapKind: "UNKNOWN",
    text: "下一条尚缺证据：尚未核验 · 仅研究，不生成订单",
  };
}

function evidenceStrategyPresentation(input = {}) {
  const presentation = globalThis.HakimiEvidencePresentation;
  if (presentation?.strategyEvidencePresentation) return presentation.strategyEvidencePresentation(input);
  return {
    hasEvidence: false,
    conclusionText: "尚无研究结论",
    directionText: "方向未形成",
    estimateText: "模型估计未校准",
    noTradeText: "失效与禁做条件尚未核验",
    permissionText: "研究解释 · 非订单 · 不授予模拟或实盘权限",
  };
}

function evidenceStrategySourceText(value) {
  const presentation = globalThis.HakimiEvidencePresentation;
  if (presentation?.strategySourceTextPresentation) {
    return presentation.strategySourceTextPresentation(value);
  }
  return "";
}

function evidenceBacktestPresentation(current = {}, data = {}) {
  const presentation = globalThis.HakimiEvidencePresentation;
  const input = {
    current,
    reproducibility: data.reproducibility || {},
    dataPoints: data.data_points,
    benchmarkReturnPct: data.benchmark_return_pct ?? data.benchmark?.total_return_pct,
    costsIncluded: data.costs_included,
    temporalStatus: data.temporal_validation?.status,
  };
  if (presentation?.backtestEvidencePresentation) {
    return presentation.backtestEvidencePresentation(input);
  }
  return {
    hasResult: false,
    returnText: "累计收益未提供",
    benchmarkText: "基准收益未提供",
    excessText: "超额收益不可计算",
    costsText: "费率未提供 · 滑点未提供",
    returnBasisText: "尚无可解释的开发回测结果",
    drawdownText: "最大回撤未提供",
    sampleText: "样本量未提供",
    tradesText: "闭合交易数未提供",
    annualizedText: "年化收益未提供",
    winRateText: "胜率未提供",
    sharpeText: "夏普未提供",
    rawTemporalStatus: "UNKNOWN",
    temporalText: "样本外证据未核验",
    boundaryText: "开发回测 · 非盈利证明 · 模拟未授权 · 实盘永久硬锁",
  };
}

function evidenceBacktestRobustnessPresentation(data = {}) {
  const presentation = globalThis.HakimiEvidencePresentation;
  if (presentation?.backtestRobustnessPresentation) {
    return presentation.backtestRobustnessPresentation(data);
  }
  return {
    valid: false,
    modeText: "时间稳健性证据未核验",
    temporalText: "验证/测试时间切片未提供",
    foldsText: "固定参数折叠未提供",
    costText: "成本压力未提供",
    parameterText: "风险控制参数表面未提供 · 策略信号参数平台未连接",
    surfaceStatusText: "风险控制参数表面未核验",
    surfaceCoverageText: "同数据开发网格覆盖未核验",
    surfaceNeighborhoodText: "局部邻域未核验",
    causalText: "因果/前视检查未提供",
    failureText: "稳健性失败条件/证据缺口未核验",
    rawTemporalStatus: "UNKNOWN",
    rawFoldStatus: "UNKNOWN",
    rawCostStatus: "UNKNOWN",
    rawSurfaceStatus: "UNKNOWN",
    rawCausalStatus: "UNKNOWN",
    permissionText: "研究解释 · 非订单 · 不授予模拟或实盘权限",
  };
}

function evidenceInternalBacktestReturnQualityPresentation(payload = {}) {
  const presentation = globalThis.HakimiEvidencePresentation;
  if (presentation?.internalBacktestReturnQualityPresentation) {
    return presentation.internalBacktestReturnQualityPresentation(payload);
  }
  return {
    verified: false,
    connectionStatus: "UNKNOWN",
    qualityState: "UNKNOWN",
    statusText: "冻结收益质量未核验",
    detailText: "固定来源缺失或合同校验失败 · 模拟未授权 · 实盘永久硬锁",
    returnsText: "策略 -- · 基准 -- · 重算超额 --",
    costText: "成本绑定未核验 · 成本后 --",
    riskText: "压力最差 -- · 最大回撤 --",
    sampleText: "样本 -- · 时间证据未核验",
    validationStageText: "验证段来源未核验",
    validationStageDetailText: "验证段依据、样本和统计主张未核验",
    testStageText: "测试段来源未核验",
    testStageDetailText: "测试段依据、样本和统计主张未核验",
    validationStageRawStatus: "UNKNOWN",
    validationStageRawBenchmarkStatus: "UNKNOWN",
    validationStageRawClaimStatus: "UNKNOWN",
    testStageRawStatus: "UNKNOWN",
    testStageRawBenchmarkStatus: "UNKNOWN",
    testStageRawClaimStatus: "UNKNOWN",
    forwardStatusText: "自然前向晋级证据未核验",
    forwardMaturityText: "收益期 --/-- · 实际调仓 --/--",
    maturityCueText: "自然前向成熟度未核验 · 收益期 --/-- · 实际调仓 --/--",
    forwardBoundaryText: "自然前向来源、语义重算与人工复核边界未核验",
    forwardSourceText: "自然前向审计指纹未核验",
    rawForwardStatus: "UNKNOWN",
    rawForwardIntegrityStatus: "UNKNOWN",
    rawForwardMaturityStatus: "UNKNOWN",
    rawForwardAuditStatus: "UNKNOWN",
    evidenceGapKind: "SOURCE",
    evidenceGapText: "先补冻结来源：固定快照、冻结时间与内容指纹需同时可核验",
    evidenceGapCount: null,
    failureText: "先补冻结来源：固定快照、冻结时间与内容指纹需同时可核验",
    sourceText: "冻结来源未核验",
    generatedAt: null,
    packHash: null,
    evidenceHash: null,
    rawPackSchema: "UNKNOWN",
    rawQualitySchema: "UNKNOWN",
    sourceMode: "UNKNOWN",
    rawPackStatus: "UNKNOWN",
    rawPromotionStatus: "UNKNOWN",
  };
}

function evidenceAttributionSpinePresentation(input = {}) {
  const presentation = globalThis.HakimiEvidencePresentation;
  if (presentation?.evidenceAttributionPresentation) {
    return presentation.evidenceAttributionPresentation(input);
  }
  return {
    relationStatus: "UNKNOWN",
    frozenCandidateText: "冻结组合归属未核验",
    forwardCandidateText: "当前自然前向归属未核验",
    relationText: "候选归属未核验 · 禁止合并解读",
    strategyAttributionText: "当前策略未核验 · 事前假设归属未核验 · 与组合候选未建立白名单绑定",
    rawFrozenCandidateHash: null,
    rawForwardCandidateHash: null,
    rawHypothesisHash: null,
  };
}

function evidenceStrategyCorrelationClusterPresentation(payload = {}) {
  const presentation = globalThis.HakimiEvidencePresentation;
  if (presentation?.strategyCorrelationClusterSummaryPresentation) {
    return presentation.strategyCorrelationClusterSummaryPresentation(payload);
  }
  return {
    valid: false,
    rawStatus: "UNKNOWN",
    statusText: "未核验",
    sourceText: "本地冻结完成日收盘复算：未核验",
    gapText: "输入完整性、事前截止日与正式协议绑定尚未闭合",
    maturityText: "独立簇票：-- / --",
    permissionText: "仅研究描述 · 不选参 · 模拟未授权 · 实盘永久硬锁",
    detailText: "固定 60 个完成日收益、绝对 Pearson 阈值 0.75；当前不形成准入结论",
  };
}

function evidenceStrategyLabPresentation(payload = {}) {
  const presentation = globalThis.HakimiEvidencePresentation;
  if (presentation?.strategyLabEvidencePresentation) {
    return presentation.strategyLabEvidencePresentation(payload);
  }
  return {
    valid: false,
    connectionStatus: "UNKNOWN",
    modeText: "即时启发式规划 · 未形成冻结研究证据",
    sourceText: "冻结来源未核验",
    implementationText: "策略信号实现：未核验",
    currentnessText: "完整源码闭包、数据新鲜度与报告年龄门槛：未核验",
    hypothesisText: "事前研究假设：未核验",
    hypothesisFailureText: "事前失效条件：未核验",
    admissionText: "事前研究门禁：未核验",
    mechanismConditionText: "开发期机制条件：未核验",
    futureConditionText: "未来标准条件：未核验 · 未评估、非通过",
    postSelectionText: "冻结后历史复算：未核验 · 非自然前向",
    frozenTestText: "冻结 TEST 历史复算：未核验 · 非盈利证明",
    holdoutText: "单次历史留出：未核验 · 非自然前向 · 非盈利证明",
    parameterText: "参数平台稳定性：未核验",
    costText: "成本压力：未核验",
    temporalText: "固定参数时间切片：未核验",
    coverageText: "研究覆盖未核验",
    failureText: "失效条件与证据缺口：未核验",
    detailText: "开发期分只作描述，不选参、不证明盈利；模拟未授权，实盘永久硬锁",
    rawParameterStatus: "UNKNOWN",
    rawCostStatus: "UNKNOWN",
    rawTemporalStatus: "UNKNOWN",
    rawImplementationStatus: "UNKNOWN",
    rawFullImplementationStatus: "UNKNOWN",
    rawHypothesisStatus: "UNKNOWN",
    rawAdmissionStatus: "UNKNOWN",
    rawMechanismStatus: "UNKNOWN",
    rawFutureConditionStatus: "UNKNOWN",
    rawPostSelectionStatus: "UNKNOWN",
    rawFrozenTestStatus: "UNKNOWN",
    rawHoldoutStatus: "UNKNOWN",
    permissionText: "只读规划 · 不充值 · 不下单 · 模拟未授权 · 实盘永久硬锁",
  };
}

function evidencePipelineSummaryPresentation(status, hasRun) {
  const presentation = globalThis.HakimiEvidencePresentation;
  if (presentation?.pipelineSummaryPresentation) {
    return presentation.pipelineSummaryPresentation(status, hasRun);
  }
  return {
    rawStatus: String(status || (hasRun ? "UNKNOWN" : "NOT_STARTED")).trim().toUpperCase(),
    stateKind: "waiting",
    label: hasRun
      ? "研究证据链尚未形成 · 不授予模拟或实盘权限"
      : "尚无已登记研究证据 · 不授予模拟或实盘权限",
  };
}

function evidencePipelineStagePresentation(stageKey, status, context = {}) {
  const presentation = globalThis.HakimiEvidencePresentation;
  if (presentation?.pipelineStagePresentation) {
    return presentation.pipelineStagePresentation(stageKey, status, context);
  }
  const liveStage = String(stageKey || "").trim().toLowerCase() === "live_trading";
  return {
    rawStatus: String(status || (liveStage ? "BLOCKED" : "WAIT")).trim().toUpperCase(),
    stateKind: liveStage ? "locked" : "waiting",
    label: liveStage ? "实盘保护未确认 · 禁止执行" : "等待研究证据",
    detailText: liveStage
      ? "AI、回测与研究证据不得解锁实盘"
      : "研究证据不授予模拟或实盘权限",
  };
}

function evidenceResearchStatusPresentation(status) {
  const presentation = globalThis.HakimiEvidencePresentation;
  if (presentation?.researchEvidenceStatusPresentation) {
    return presentation.researchEvidenceStatusPresentation(status);
  }
  const raw = String(status || "WAIT").trim().toUpperCase() || "WAIT";
  const blocked = ["BLOCK", "BLOCKED", "RESEARCH_BLOCKED", "ERROR", "FAILED", "REJECTED", "UNSAFE"].includes(raw);
  const active = ["RUNNING", "ACTIVE", "IN_PROGRESS", "RESEARCH_REVIEW"].includes(raw);
  const verified = ["PASS", "READY", "COMPLETE", "COMPLETED", "DONE", "SUCCESS", "SUCCEEDED", "PAPER_READY", "PAPER_RUNNING", "PAPER_MANUAL_READY", "PAPER_STRATEGY_READY", "RESTART_READY", "RESEARCH_VERIFIED"].includes(raw);
  return {
    rawStatus: raw,
    stateKind: blocked ? "blocked" : active ? "active" : verified ? "verified" : "waiting",
    label: blocked
      ? "研究证据存在阻断"
      : active
        ? "研究证据核对中 · 非授权"
        : verified
          ? "研究证据已核对 · 非授权"
          : "等待研究证据",
    detailText: "仅研究证据 · 不授予模拟或实盘权限",
  };
}

function evidenceStrategyActionPresentation(action) {
  const raw = String(action || "WAIT").trim().toUpperCase();
  if (raw.startsWith("研究假设：") || raw.startsWith("研究结论：")) {
    return {
      hasEvidence: true,
      conclusionText: String(action),
      directionText: String(action),
      estimateText: "模型估计未校准",
      noTradeText: "失效与禁做条件尚未核验",
      permissionText: "研究解释 · 非订单 · 不授予模拟或实盘权限",
    };
  }
  return evidenceStrategyPresentation({
    hasSignal: true,
    action: raw || "WAIT",
  });
}

function evidenceResearchCellPresentation(status, fallback = "研究状态待核验") {
  const raw = String(status || "").trim().toUpperCase();
  const known = [
    "PASS", "READY", "COMPLETE", "COMPLETED", "DONE", "SUCCESS", "SUCCEEDED",
    "PAPER_READY", "PAPER_RUNNING", "PAPER_MANUAL_READY", "PAPER_STRATEGY_READY", "RESTART_READY",
    "RUNNING", "ACTIVE", "IN_PROGRESS", "RESEARCH_REVIEW", "BLOCK", "BLOCKED", "RESEARCH_BLOCKED", "ERROR", "FAILED", "REJECTED", "UNSAFE",
    "RESEARCH_VERIFIED", "RESEARCH_OBSERVE",
    "WAIT", "WAITING", "NOT_STARTED", "UNKNOWN",
  ];
  if (known.includes(raw)) return evidenceResearchStatusPresentation(raw);
  return {
    rawStatus: raw || "UNKNOWN",
    stateKind: "waiting",
    label: fallback,
    detailText: "仅研究证据 · 不授予模拟或实盘权限",
  };
}

function evidenceResearchValue(value) {
  const text = String(value ?? "").trim();
  const raw = text.toUpperCase();
  const statusValues = [
    "PASS", "READY", "COMPLETE", "COMPLETED", "DONE", "SUCCESS", "SUCCEEDED",
    "PAPER_READY", "PAPER_RUNNING", "PAPER_MANUAL_READY", "PAPER_STRATEGY_READY", "RESTART_READY",
    "RUNNING", "ACTIVE", "IN_PROGRESS", "RESEARCH_REVIEW", "BLOCK", "BLOCKED", "RESEARCH_BLOCKED", "ERROR", "FAILED", "REJECTED", "UNSAFE",
    "RESEARCH_VERIFIED", "RESEARCH_OBSERVE",
    "WAIT", "WAITING", "NOT_STARTED", "UNKNOWN",
  ];
  return statusValues.includes(raw) ? evidenceResearchCellPresentation(raw).label : (text || "--");
}

function evidenceResearchStatusClass(status) {
  return evidenceResearchStatusPresentation(status).stateKind === "blocked" ? "down" : "flat";
}

function evidenceResearchStatusBadge(status, fallback = "研究状态待核验") {
  const presentation = evidenceResearchCellPresentation(status, fallback);
  const raw = escapeHtml(presentation.rawStatus || "UNKNOWN");
  return `<span class="${evidenceResearchStatusClass(status)}" data-raw-status="${raw}" title="原始研究状态 ${raw} · ${escapeHtml(presentation.detailText || "仅研究证据 · 不授予模拟或实盘权限")}">${escapeHtml(presentation.label)}</span>`;
}

function renderPlatformAuthoritySummary() {
  const authority = globalThis.HakimiEvidencePresentation?.AUTHORITY_SUMMARY;
  if (!authority) return;
  if ($("platformAuthorityAllowed")) {
    $("platformAuthorityAllowed").textContent = String(authority.allowed || "").replace(/^可做：/, "");
  }
  if ($("platformAuthorityForbidden")) {
    $("platformAuthorityForbidden").textContent = String(authority.forbidden || "").replace(/^不可做：/, "");
  }
}

function setPlatformBlock(id, status, detail, options = {}) {
  const card = $(id);
  if (!card) return;
  const tone = options.neutral === true ? "flat evidence-status" : platformTone(status);
  card.className = `platform-status-block ${tone}`;
  card.dataset.rawStatus = String(status || "--");
  card.title = options.title || "";
  const strong = card.querySelector("strong");
  const em = card.querySelector("em");
  if (strong) strong.textContent = options.label || status || "--";
  if (em) em.textContent = detail || "--";
}

const PLATFORM_MARKET_STATUSES = new Set(["READY", "STALE", "UNKNOWN", "BLOCK"]);

function platformBarIdentity(value) {
  const text = String(value || "").trim().toLowerCase();
  return ["1d", "1dutc"].includes(text) ? "1d" : text;
}

function platformControlRequestContext() {
  const symbol = String(state.symbol || "").trim().toUpperCase();
  const bar = String(state.bar || "").trim();
  const session = isStockMarket(symbol) ? String(state.stockSession || "regular") : "all";
  const symbolVersion = runtime.symbolVersion;
  return {
    symbol,
    bar,
    session,
    symbolVersion,
    price: Number(state.lastPrice || 0),
    key: `${symbol}|${bar}|${session}|${symbolVersion}`,
  };
}

function isCurrentPlatformControlRequest(context) {
  if (!context) return true;
  const current = platformControlRequestContext();
  return context.key === current.key;
}

function platformTruthTimeText(timestamp, explicit = "") {
  if (String(explicit || "").trim()) return String(explicit).trim();
  const parsed = Number(timestamp || 0);
  if (!Number.isFinite(parsed) || parsed <= 0) return "--";
  return new Date(parsed).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function platformMarketTruthView(data = {}, requestContext = null) {
  const truth = data.market_truth || data.data_health?.data_truth || {};
  const expected = requestContext || platformControlRequestContext();
  const symbol = String(truth.symbol || "").trim().toUpperCase();
  const requestedBar = String(truth.requested_bar || "").trim();
  const requestedSession = String(truth.requested_session || "").trim().toLowerCase();
  const quote = truth.quote || {};
  const candles = truth.candles || {};
  const schemaReady = truth.schema_version === "market-data-truth-v1";
  const identityMismatch = Boolean(
    schemaReady
    && (
      (symbol && expected.symbol && symbol !== expected.symbol)
      || (requestedBar && platformBarIdentity(requestedBar) !== platformBarIdentity(expected.bar))
      || (requestedSession && requestedSession !== String(expected.session || "").toLowerCase())
    )
  );
  let status = PLATFORM_MARKET_STATUSES.has(String(truth.status || "").toUpperCase())
    ? String(truth.status).toUpperCase()
    : "UNKNOWN";
  if (!schemaReady) status = "UNKNOWN";
  if (identityMismatch) status = "BLOCK";
  const readyContractComplete = Boolean(
    truth.snapshot_available === true
    && truth.observation_current === true
    && truth.realtime_ready === true
    && String(quote.source || "").trim()
    && String(candles.source || "").trim()
    && Number(candles.last_completed_ts || 0) > 0
  );
  if (status === "READY" && !readyContractComplete) status = "BLOCK";
  const statusCopy = evidenceStatusPresentation("market", status);

  const mode = identityMismatch ? "IDENTITY_MISMATCH" : String(truth.mode || (schemaReady ? status : "UNOBSERVED"));
  const snapshotAge = truth.snapshot_age_ms === null || truth.snapshot_age_ms === undefined
    ? Number.NaN
    : Number(truth.snapshot_age_ms);
  const freshness = Number.isFinite(snapshotAge)
    ? `${mode === "HISTORICAL_READY" ? "最近完成时段" : researchStatusShort(quote.status || status, "行情状态待核验")} · 快照${chartAgeText(snapshotAge)}`
    : mode === "UNOBSERVED" ? "尚未观察" : researchStatusShort(quote.status || status, "行情状态待核验");
  const quoteText = String(quote.label || "").trim()
    || (quote.source ? marketSourceLabel(quote.source) : "等待快照");
  const candleText = candles.source
    ? `${marketSourceLabel(candles.source)} · ${candles.bar || expected.bar || "--"}`
    : "等待快照";
  const evidenceGap = evidenceMarketTruthGapPresentation({ status });
  return {
    status,
    statusLabel: statusCopy.label,
    permissionsText: statusCopy.permissionText,
    mode,
    symbol: symbol || expected.symbol || "--",
    quoteText,
    candleText,
    freshness,
    lastCompleted: platformTruthTimeText(candles.last_completed_ts, candles.last_completed_at),
    evidenceGapText: evidenceGap.text,
    revisionStatus: String(truth.revision_status || data.data_revision?.status || "UNKNOWN").toUpperCase(),
  };
}

function renderPlatformMarketTruth(view) {
  const band = $("platformMarketTruthCenter");
  if (band) {
    band.dataset.marketStatus = view.status;
    band.title = `原始行情证据状态 ${view.status}`;
  }
  if ($("platformTruthStatus")) {
    $("platformTruthStatus").textContent = view.statusLabel;
    $("platformTruthStatus").title = `原始状态 ${view.status}`;
  }
  if ($("platformTruthPermissions")) $("platformTruthPermissions").textContent = view.permissionsText;
  if ($("platformTruthSymbol")) $("platformTruthSymbol").textContent = view.symbol;
  if ($("platformTruthQuoteSource")) $("platformTruthQuoteSource").textContent = view.quoteText;
  if ($("platformTruthCandleSource")) $("platformTruthCandleSource").textContent = view.candleText;
  if ($("platformTruthFreshness")) $("platformTruthFreshness").textContent = view.freshness;
  if ($("platformTruthLastCompleted")) $("platformTruthLastCompleted").textContent = view.lastCompleted;
  if ($("platformTruthEvidenceGap")) $("platformTruthEvidenceGap").textContent = view.evidenceGapText;
  const cardStatus = view.revisionStatus === "BLOCK" ? "BLOCK" : view.status;
  const cardCopy = evidenceStatusPresentation("market", cardStatus);
  setPlatformBlock(
    "platformDataCard",
    cardStatus,
    `${view.symbol} · 报价 ${view.quoteText} · K线 ${view.candleText}`,
    {
      neutral: true,
      label: cardCopy.label,
      title: `原始行情状态 ${view.status} · 原始修订状态 ${view.revisionStatus}`,
    },
  );
}

const PLATFORM_FORWARD_STATUSES = new Set(["UP_TO_DATE", "WAITING", "DUE", "PAUSED", "BLOCK", "UNKNOWN"]);

function platformForwardProgressText(value, required) {
  const cleanValue = Number.isInteger(value) && value >= 0 ? String(value) : "--";
  const cleanRequired = Number.isInteger(required) && required > 0 ? String(required) : "--";
  return `${cleanValue}/${cleanRequired}`;
}

function platformForwardObservationView(forward) {
  const raw = forward?.incremental_observation || {};
  const legacySchemaValid = raw.schema_version === "portfolio-forward-dashboard-v4"
    && !Object.hasOwn(raw, "statistical_maturity");
  const currentSchemaValid = raw.schema_version === "portfolio-forward-dashboard-v5"
    || raw.schema_version === "portfolio-forward-dashboard-v6"
    || raw.schema_version === "portfolio-forward-dashboard-v7";
  const schemaValid = legacySchemaValid || currentSchemaValid;
  const statisticalMaturity = evidenceForwardStatisticalMaturityPresentation(raw);
  const permissions = raw.permissions || {};
  const permissionsValid = schemaValid
    && statisticalMaturity.dashboardAuthoritySafe === true
    && permissions.read_only === true
    && permissions.observation_only === true
    && permissions.simulation_only === true
    && permissions.paper_authorized === false
    && permissions.live_order_allowed === false
    && permissions.live_trading_hard_block === true;
  let status = String(raw.status || "UNKNOWN").toUpperCase();
  if (!schemaValid || !PLATFORM_FORWARD_STATUSES.has(status)) status = "UNKNOWN";
  if (schemaValid && !permissionsValid) status = "BLOCK";
  const evidenceGap = evidenceForwardGapPresentation({ status });

  const completed = raw.latest_completed_bar || {};
  const data = raw.data || {};
  const pending = raw.pending || {};
  const skipped = raw.skipped || {};
  const nextCheck = raw.next_check || {};
  const service = raw.service || {};
  const observer = raw.observer || {};
  const latestObservation = raw.latest_observation || {};
  const latestObservationChange = raw.latest_observation_change || {};
  const recentObserverJobs = raw.recent_observer_jobs;
  const processed = Number.isInteger(data.processed_count) && data.processed_count >= 0
    ? data.processed_count
    : null;
  const latestBar = completed.known === true && completed.date
    ? `${completed.date} · ${completed.bar || "1D"}`
    : "尚无可信完成日线";
  const lastAccounted = data.last_accounted_date || "尚未计入自然样本";
  let pendingText = "UNKNOWN";
  if (pending.known === true) {
    const dates = Array.isArray(pending.dates) ? pending.dates.filter(Boolean) : [];
    if (pending.state === "FINALIZING") pendingText = "等待完成确认";
    else if (pending.state === "OVERDUE") pendingText = `逾期审核 ${dates.join("、") || "待确认"}`;
    else if (pending.state === "DUE") pendingText = dates.join("、") || "观察窗口已到";
    else pendingText = dates.length ? dates.join("、") : "无";
  }
  const skippedText = skipped.known === true && Number.isInteger(skipped.total)
    ? `${skipped.total} 条 · 已记录 ${skipped.recorded || 0} / 已分类 ${skipped.classified || 0}`
    : "尚无通过审计的跳过证据";
  let nextCheckText = "等待调度证据";
  if (nextCheck.mode === "NOW") nextCheckText = "现在";
  else if (nextCheck.mode === "AT" && Number(nextCheck.at_ms) > 0) nextCheckText = timeText(Number(nextCheck.at_ms));
  const exactKeys = (value, expected) => (
    value && typeof value === "object" && !Array.isArray(value)
    && Object.keys(value).sort().join("|") === [...expected].sort().join("|")
  );
  const hashText = (value) => /^[a-f0-9]{64}$/.test(String(value || ""));
  const signalDateText = (value) => /^\d{4}-\d{2}-\d{2}$/.test(String(value || ""));
  const targetSymbols = Array.isArray(latestObservation.target_symbols)
    ? latestObservation.target_symbols
    : [];
  const targetSymbolsValid = (
    Array.isArray(latestObservation.target_symbols)
    && targetSymbols.every((value) => (
      typeof value === "string"
      && /^[A-Z0-9][A-Z0-9._-]{0,31}$/.test(value)
    ))
    && new Set(targetSymbols).size === targetSymbols.length
  );
  const allocation = latestObservation.target_allocation_pct;
  const riskStatus = String(latestObservation.risk_status || "").toUpperCase();
  const observedAt = latestObservation.observed_at;
  const receiptValid = Boolean(
    schemaValid
    && permissionsValid
    && exactKeys(latestObservation, [
      "known", "source", "signal_date", "target_symbols", "target_allocation_pct", "reason",
      "risk_status", "record_status", "observed_at", "decision_hash", "observation_hash", "receipt_hash",
    ])
    && latestObservation.known === true
    && latestObservation.source === "VERIFIED_LEDGER_RECEIPT"
    && signalDateText(latestObservation.signal_date)
    && latestObservation.signal_date === data.latest_observation_date
    && targetSymbolsValid
    && typeof allocation === "number"
    && Number.isFinite(allocation)
    && allocation >= 0
    && allocation <= 100
    && typeof latestObservation.reason === "string"
    && ["PASS", "BLOCK", "NOT_EVALUATED", "UNKNOWN"].includes(riskStatus)
    && latestObservation.record_status === "VERIFIED_LEDGER_OBSERVATION"
    && Number.isSafeInteger(observedAt)
    && observedAt > 0
    && Number.isSafeInteger(raw.as_of_ms)
    && raw.as_of_ms >= observedAt
    && hashText(raw.candidate_hash)
    && hashText(latestObservation.decision_hash)
    && hashText(latestObservation.observation_hash)
    && hashText(latestObservation.receipt_hash)
  );
  const changeKeysValid = exactKeys(latestObservationChange, [
    "known", "status", "source", "candidate_hash", "previous_signal_date", "current_signal_date",
    "previous_observation_hash", "current_observation_hash", "target_set_changed", "added_symbols",
    "removed_symbols", "retained_symbols", "risk_status_before", "risk_status_after", "risk_changed",
    "change_hash", "descriptive_only", "direction_signal_allowed", "performance_claim_allowed",
    "paper_authorized", "live_order_allowed",
  ]);
  const changeSafetyValid = Boolean(
    changeKeysValid
    && latestObservationChange.descriptive_only === true
    && latestObservationChange.direction_signal_allowed === false
    && latestObservationChange.performance_claim_allowed === false
    && latestObservationChange.paper_authorized === false
    && latestObservationChange.live_order_allowed === false
  );
  const changeCandidateValid = Boolean(
    hashText(latestObservationChange.candidate_hash)
    && latestObservationChange.candidate_hash === raw.candidate_hash
  );
  const sortedUniqueSymbols = (value) => (
    Array.isArray(value)
    && value.every((symbol) => (
      typeof symbol === "string"
      && /^[A-Z0-9][A-Z0-9._-]{0,31}$/.test(symbol)
    ))
    && new Set(value).size === value.length
    && value.join("|") === [...value].sort().join("|")
  );
  const addedSymbols = latestObservationChange.added_symbols;
  const removedSymbols = latestObservationChange.removed_symbols;
  const retainedSymbols = latestObservationChange.retained_symbols;
  const changeSymbolListsValid = Boolean(
    sortedUniqueSymbols(addedSymbols)
    && sortedUniqueSymbols(removedSymbols)
    && sortedUniqueSymbols(retainedSymbols)
    && new Set([...addedSymbols, ...removedSymbols, ...retainedSymbols]).size
      === addedSymbols.length + removedSymbols.length + retainedSymbols.length
  );
  const previousRiskStatus = String(latestObservationChange.risk_status_before || "").toUpperCase();
  const currentRiskStatus = String(latestObservationChange.risk_status_after || "").toUpperCase();
  const verifiedChangeValid = Boolean(
    schemaValid
    && receiptValid
    && changeSafetyValid
    && changeCandidateValid
    && latestObservationChange.known === true
    && latestObservationChange.status === "VERIFIED"
    && latestObservationChange.source === "VERIFIED_LEDGER_CHANGE"
    && signalDateText(latestObservationChange.previous_signal_date)
    && signalDateText(latestObservationChange.current_signal_date)
    && latestObservationChange.previous_signal_date < latestObservationChange.current_signal_date
    && latestObservationChange.current_signal_date === latestObservation.signal_date
    && hashText(latestObservationChange.previous_observation_hash)
    && hashText(latestObservationChange.current_observation_hash)
    && latestObservationChange.previous_observation_hash !== latestObservationChange.current_observation_hash
    && latestObservationChange.current_observation_hash === latestObservation.observation_hash
    && changeSymbolListsValid
    && typeof latestObservationChange.target_set_changed === "boolean"
    && latestObservationChange.target_set_changed
      === (addedSymbols.length > 0 || removedSymbols.length > 0)
    && ["PASS", "BLOCK"].includes(previousRiskStatus)
    && ["PASS", "BLOCK"].includes(currentRiskStatus)
    && currentRiskStatus === riskStatus
    && typeof latestObservationChange.risk_changed === "boolean"
    && latestObservationChange.risk_changed === (previousRiskStatus !== currentRiskStatus)
    && hashText(latestObservationChange.change_hash)
  );
  const emptyChangeClaims = Boolean(
    latestObservationChange.target_set_changed === null
    && Array.isArray(addedSymbols) && addedSymbols.length === 0
    && Array.isArray(removedSymbols) && removedSymbols.length === 0
    && Array.isArray(retainedSymbols) && retainedSymbols.length === 0
    && previousRiskStatus === ""
    && currentRiskStatus === ""
    && latestObservationChange.risk_changed === null
  );
  const notEnoughCurrentValid = receiptValid
    ? (
      latestObservationChange.current_signal_date === latestObservation.signal_date
      && latestObservationChange.current_observation_hash === latestObservation.observation_hash
    )
    : (
      latestObservationChange.current_signal_date === ""
      && latestObservationChange.current_observation_hash === ""
    );
  const notEnoughChangeValid = Boolean(
    schemaValid
    && changeSafetyValid
    && changeCandidateValid
    && latestObservationChange.known === false
    && latestObservationChange.status === "NOT_ENOUGH_OBSERVATIONS"
    && latestObservationChange.source === "VERIFIED_LEDGER_CHANGE"
    && latestObservationChange.previous_signal_date === ""
    && latestObservationChange.previous_observation_hash === ""
    && notEnoughCurrentValid
    && emptyChangeClaims
    && hashText(latestObservationChange.change_hash)
  );
  const notCheckedChangeValid = Boolean(
    schemaValid
    && changeSafetyValid
    && changeCandidateValid
    && latestObservationChange.known === false
    && latestObservationChange.status === "NOT_CHECKED"
    && latestObservationChange.source === ""
    && latestObservationChange.previous_signal_date === ""
    && latestObservationChange.current_signal_date === ""
    && latestObservationChange.previous_observation_hash === ""
    && latestObservationChange.current_observation_hash === ""
    && emptyChangeClaims
    && latestObservationChange.change_hash === ""
  );
  let changeText = "";
  let changeTitle = "";
  if (verifiedChangeValid) {
    changeText = `较前次（非订单 / 非方向信号） ${latestObservationChange.previous_signal_date}→${latestObservationChange.current_signal_date}`
      + ` · 观察集合${latestObservationChange.target_set_changed ? "有变化" : "未变"}`
      + ` · 风险复核 ${researchStatusShort(previousRiskStatus, "待核验")}→${researchStatusShort(currentRiskStatus, "待核验")}`;
    changeTitle = `Change ${latestObservationChange.change_hash}\nPrevious observation ${latestObservationChange.previous_observation_hash}`;
  } else if (notEnoughChangeValid) {
    changeText = "较前次：尚无可验证前次观察";
    changeTitle = `Change ${latestObservationChange.change_hash}`;
  } else if (schemaValid && !notCheckedChangeValid) {
    changeText = "较前次：比较证据异常 · 已隐藏";
  }
  const observerJobKeys = [
    "known", "source", "job_id", "candidate_hash", "outcome", "started_at_ms", "finished_at_ms",
    "duration_ms", "observer_status", "processed_count", "pre_last_signal_date", "post_last_signal_date",
    "reconciliation_required", "receipt_hash", "descriptive_only", "direction_signal_allowed",
    "performance_claim_allowed", "paper_authorized", "live_order_allowed",
  ];
  const observerJobOutcomeText = {
    PROCESSED_NEW_BARS: "已计入新完成K线",
    NO_NEW_BAR: "无新完成K线",
    NO_WORK_ALREADY_ACCOUNTED: "最新完成K线已计入",
    BLOCKED: "观察被阻断",
    FAILED: "观察作业失败",
  };
  const blockedObserverStatuses = new Set([
    "BLOCK", "CLOCK_ATTESTATION_BLOCKED", "INCREMENTAL_OBSERVATION_PLAN_BLOCKED", "FORWARD_VALIDATION_BLOCKED",
  ]);
  const validObserverJobDate = (value) => value === "" || signalDateText(value);
  const observerJobValid = (job) => {
    if (!exactKeys(job, observerJobKeys)) return false;
    const outcome = String(job.outcome || "");
    const observerStatus = String(job.observer_status || "");
    const startedAt = job.started_at_ms;
    const finishedAt = job.finished_at_ms;
    const duration = job.duration_ms;
    const processedCount = job.processed_count;
    const preDate = String(job.pre_last_signal_date || "");
    const postDate = String(job.post_last_signal_date || "");
    const baseValid = Boolean(
      job.known === true
      && job.source === "VERIFIED_SCHEDULER_JOB_RECEIPT"
      && hashText(job.job_id)
      && hashText(job.candidate_hash)
      && job.candidate_hash === raw.candidate_hash
      && Object.hasOwn(observerJobOutcomeText, outcome)
      && Number.isSafeInteger(startedAt) && startedAt > 0
      && Number.isSafeInteger(finishedAt) && finishedAt >= startedAt
      && Number.isSafeInteger(duration) && duration === finishedAt - startedAt
      && Number.isSafeInteger(raw.as_of_ms) && finishedAt <= raw.as_of_ms
      && observerStatus
      && Number.isSafeInteger(processedCount) && processedCount >= 0
      && validObserverJobDate(preDate)
      && validObserverJobDate(postDate)
      && hashText(job.receipt_hash)
      && job.descriptive_only === true
      && job.direction_signal_allowed === false
      && job.performance_claim_allowed === false
      && job.paper_authorized === false
      && job.live_order_allowed === false
      && job.reconciliation_required === (outcome === "FAILED")
    );
    if (!baseValid) return false;
    if (outcome === "PROCESSED_NEW_BARS") {
      return observerStatus === "FORWARD_OBSERVATIONS_UPDATED"
        && processedCount > 0
        && signalDateText(postDate)
        && (!preDate || preDate < postDate);
    }
    if (outcome === "NO_NEW_BAR") {
      return observerStatus === "WAITING_FOR_NEW_COMPLETED_BAR"
        && processedCount === 0
        && preDate === postDate;
    }
    if (outcome === "NO_WORK_ALREADY_ACCOUNTED") {
      return observerStatus === "UP_TO_DATE_INCREMENTAL"
        && processedCount === 0
        && preDate === postDate;
    }
    if (outcome === "BLOCKED") return blockedObserverStatuses.has(observerStatus);
    return true;
  };
  const observerJobsArrayValid = Boolean(
    Array.isArray(recentObserverJobs)
    && recentObserverJobs.length <= 2
    && recentObserverJobs.every(observerJobValid)
  );
  let observerJobsPairValid = observerJobsArrayValid;
  if (observerJobsPairValid && recentObserverJobs.length === 2) {
    const [olderJob, newerJob] = recentObserverJobs;
    observerJobsPairValid = Boolean(
      olderJob.job_id !== newerJob.job_id
      && olderJob.receipt_hash !== newerJob.receipt_hash
      && newerJob.started_at_ms >= olderJob.finished_at_ms
    );
  }
  if (observerJobsPairValid && recentObserverJobs.length > 0) {
    const newestJob = recentObserverJobs[recentObserverJobs.length - 1];
    observerJobsPairValid = Boolean(
      newestJob.observer_status === String(observer.last_job_status || "")
      && newestJob.duration_ms === observer.last_job_duration_ms
    );
  }
  let processedText = processed === null ? "--" : `${processed} 条`;
  let processedTitle = "";
  if (schemaValid && status === "BLOCK" && Array.isArray(recentObserverJobs) && recentObserverJobs.length === 0) {
    processedText = "作业结果异常 · 已隐藏";
  } else if (schemaValid && observerJobsPairValid && recentObserverJobs.length > 0) {
    const newestJob = recentObserverJobs[recentObserverJobs.length - 1];
    const olderJob = recentObserverJobs.length === 2 ? recentObserverJobs[0] : null;
    processedText = `最近作业 ${newestJob.processed_count}条 · ${observerJobOutcomeText[newestJob.outcome]}`
      + `；前次 ${olderJob ? `${olderJob.processed_count}条` : "--"}`;
    const jobTitle = (label, job) => (
      `${label} ${platformTruthTimeText(job.finished_at_ms)} · ${observerJobOutcomeText[job.outcome]}`
      + ` · 前沿 ${job.pre_last_signal_date || "--"}→${job.post_last_signal_date || "--"}`
      + `\nJob ${job.job_id}\nReceipt ${job.receipt_hash}`
    );
    processedTitle = [
      jobTitle("最近作业", newestJob),
      olderJob ? jobTitle("前次作业", olderJob) : "",
    ].filter(Boolean).join("\n");
  } else if (schemaValid && (!Array.isArray(recentObserverJobs) || recentObserverJobs.length > 0)) {
    processedText = "作业结果异常 · 已隐藏";
  }
  const targetText = targetSymbols.length ? targetSymbols.join("、") : "无目标标的";
  const latestObservationBase = receiptValid
    ? `观察目标（非订单） ${targetText} · 日期 ${latestObservation.signal_date} · 风险复核 ${researchStatusShort(riskStatus, "待核验")} · 收据 ${latestObservation.receipt_hash.slice(0, 12)}…`
    : "最近观察不可验证 · 已隐藏";
  const latestObservationText = `${latestObservationBase}${changeText ? ` · ${changeText}` : ""}`;
  const latestObservationTitle = [
    receiptValid
      ? `只读观察收据 ${latestObservation.receipt_hash}\nDecision ${latestObservation.decision_hash}\nObservation ${latestObservation.observation_hash}`
      : "",
    changeTitle,
  ].filter(Boolean).join("\n");
  const permissionsText = permissionsValid
    ? evidenceStatusPresentation("forward", status).permissionText
    : schemaValid ? "权限合同异常 · 已阻断" : "等待只读权限合同";
  const statusCopy = evidenceStatusPresentation("forward", status);
  return {
    status,
    statusLabel: statusCopy.label,
    operationalTruthText: statusCopy.label,
    maturityRawStatus: statisticalMaturity.rawStatus,
    maturityText: statisticalMaturity.statusText,
    maturityProgressText: statisticalMaturity.progressText,
    sourceBindingAvailable: statisticalMaturity.sourceBindingAvailable,
    sourceBindingRawStatus: statisticalMaturity.sourceBindingRawStatus,
    sourceBindingText: statisticalMaturity.sourceBindingText,
    sourceBindingDetailText: statisticalMaturity.sourceBindingDetailText,
    latestBar,
    lastAccounted,
    pendingText,
    processedText,
    processedTitle,
    skippedText,
    nextCheckText,
    evidenceGapText: evidenceGap.text,
    latestObservationText,
    latestObservationTitle,
    permissionsText,
    summary: `调度 ${researchStatusShort(service.status, "调度待核验")} · 观察 ${researchStatusShort(observer.status, "观察待核验")} · 最近 ${data.latest_observation_date || "--"}`,
  };
}

function renderPlatformForwardObservation(forward) {
  const view = platformForwardObservationView(forward);
  const root = $("platformForwardObservationCenter");
  if (root) {
    root.dataset.forwardStatus = view.status;
    root.dataset.forwardOperationalStatus = view.status;
    root.dataset.forwardMaturityStatus = view.maturityRawStatus;
    root.dataset.forwardSourceStatus = view.sourceBindingRawStatus;
    root.title = `原始来源覆盖 ${view.sourceBindingRawStatus} · 原始自然前向运行状态 ${view.status} · 原始统计成熟度 ${view.maturityRawStatus}`;
  }
  if ($("platformForwardObservationStatus")) {
    $("platformForwardObservationStatus").textContent = view.statusLabel;
    $("platformForwardObservationStatus").title = `原始状态 ${view.status}`;
  }
  if ($("platformForwardPermissions")) $("platformForwardPermissions").textContent = view.permissionsText;
  if ($("platformForwardLatestBar")) $("platformForwardLatestBar").textContent = view.latestBar;
  if ($("platformForwardLastAccounted")) $("platformForwardLastAccounted").textContent = view.lastAccounted;
  if ($("platformForwardPendingDates")) $("platformForwardPendingDates").textContent = view.pendingText;
  if ($("platformForwardProcessedCount")) {
    $("platformForwardProcessedCount").textContent = view.processedText;
    $("platformForwardProcessedCount").title = view.processedTitle;
  }
  if ($("platformForwardSkippedCount")) $("platformForwardSkippedCount").textContent = view.skippedText;
  if ($("platformForwardNextCheck")) $("platformForwardNextCheck").textContent = view.nextCheckText;
  if ($("platformForwardEvidenceGap")) {
    $("platformForwardEvidenceGap").textContent = view.evidenceGapText;
  }
  const evidenceLedger = $("platformForwardEvidenceLedger");
  if (evidenceLedger) {
    evidenceLedger.dataset.operationalStatus = view.status;
    evidenceLedger.dataset.maturityStatus = view.maturityRawStatus;
    evidenceLedger.dataset.sourceBindingStatus = view.sourceBindingRawStatus;
  }
  const sourceBinding = $("platformForwardLocalSourceBinding");
  if (sourceBinding) {
    sourceBinding.textContent = view.sourceBindingText;
    sourceBinding.dataset.rawStatus = view.sourceBindingRawStatus;
    sourceBinding.title = `原始本地归档覆盖状态 ${view.sourceBindingRawStatus}`;
  }
  if ($("platformForwardLocalSourceDetail")) {
    $("platformForwardLocalSourceDetail").textContent = view.sourceBindingDetailText;
  }
  if ($("platformForwardOperationalTruth")) {
    $("platformForwardOperationalTruth").textContent = view.operationalTruthText;
  }
  if ($("platformForwardStatisticalMaturity")) {
    $("platformForwardStatisticalMaturity").textContent = view.maturityText;
  }
  if ($("platformForwardStatisticalProgress")) {
    $("platformForwardStatisticalProgress").textContent = view.maturityProgressText;
  }
  const returnSourceBinding = $("internalBacktestMaturitySourceBinding");
  if (returnSourceBinding) {
    returnSourceBinding.textContent = `本地归档覆盖：${view.sourceBindingText}`;
    returnSourceBinding.dataset.rawStatus = view.sourceBindingRawStatus;
    returnSourceBinding.title = `原始本地归档覆盖状态 ${view.sourceBindingRawStatus}`;
  }
  if ($("internalBacktestMaturitySourceBindingDetail")) {
    $("internalBacktestMaturitySourceBindingDetail").textContent = view.sourceBindingDetailText;
  }
  if ($("platformForwardObservationReceipt")) {
    $("platformForwardObservationReceipt").textContent = view.latestObservationText;
    $("platformForwardObservationReceipt").title = view.latestObservationTitle;
  }
  renderEvidenceAttributionSpine();
  return view;
}

function platformSmallCapitalPlanView(raw, marketTruth = {}, requestContext = null) {
  const unknownView = {
    status: "UNKNOWN",
    permissionsText: "只读规划 · 不充值 · 不下单 · 模拟未授权 · 实盘永久硬锁 · 权限合同待核验",
    budgetText: "名义封套待核验",
    singleOrderText: "--",
    quantityPreviewText: "等待可信报价、公开深度与 lot/minSz",
    quantityPreviewTitle: "完整深度、费率、滑点、最小金额、余额与 USD/USDT 换算均未核验",
    dailyGuardText: "示例周转上限 -- · 示例亏损上限 --",
    instrumentRulesText: "Tick -- · Lot -- · Min --",
    ruleEvidenceText: "来源 -- · 抓取 -- · Hash -- · 费率未核验",
    ruleEvidenceTitle: "",
    circuitText: "--",
    evidenceGapText: evidenceSmallCapitalGapPresentation({ status: "UNKNOWN" }).text,
  };
  const schemaValid = raw?.schema_version === "small-capital-planning-v3";
  if (!schemaValid) return unknownView;

  const modeValid = raw?.mode === "PLAN_ONLY_NO_EXECUTION";
  const topLevelAuthorityValid = (
    raw?.execution_allowed === false
    && raw?.paper_authorized === false
    && raw?.live_order_allowed === false
    && raw?.illustrative_not_investment_advice === true
  );
  const permissions = raw?.permissions || {};
  const permissionsValid = (
    permissions.planning_only === true
    && permissions.runtime_mutations_allowed === false
    && permissions.deposit_allowed === false
    && permissions.order_submission_allowed === false
    && permissions.execution_allowed === false
    && permissions.paper_authorized === false
    && permissions.live_order_allowed === false
    && permissions.live_trading_hard_block === true
  );
  const budget = raw?.budget || {};
  const currency = String(budget.currency || "").toUpperCase();
  const exactNumber = (value, expected) => (
    typeof value === "number" && Number.isFinite(value) && value === expected
  );
  const exactKeys = (value, expected) => (
    value && typeof value === "object" && !Array.isArray(value)
    && Object.keys(value).sort().join("|") === [...expected].sort().join("|")
  );
  const budgetValid = (
    exactKeys(budget, ["currency", "min_usd", "max_usd"])
    && currency === "USD"
    && exactNumber(budget.min_usd, 100)
    && exactNumber(budget.max_usd, 200)
  );
  const scope = raw?.scope || {};
  const scopeSymbol = String(scope.symbol || "").trim().toUpperCase();
  const truthSymbol = String(marketTruth?.symbol || "").trim().toUpperCase();
  const requestSymbol = String(requestContext?.symbol || scopeSymbol).trim().toUpperCase();
  const identityValid = Boolean(
    scopeSymbol
    && truthSymbol === scopeSymbol
    && requestSymbol === scopeSymbol
  );
  const scopeValid = (
    exactKeys(scope, ["symbol", "asset_class", "leverage", "margin_allowed", "derivatives_allowed"])
    && identityValid
    && scope.asset_class === "SPOT_ONLY"
    && exactNumber(scope.leverage, 1)
    && scope.margin_allowed === false
    && scope.derivatives_allowed === false
  );
  const guardrails = raw?.guardrails || {};
  const exactRange = (value, low, high) => (
    exactKeys(value, ["min", "max"])
    && exactNumber(value.min, low)
    && exactNumber(value.max, high)
  );
  const requiredGuardrailKeys = [
    "reserve_pct", "reserve_usd", "max_deployed_pct", "max_deployed_usd",
    "single_order_pct", "single_order_usd", "daily_gross_pct", "daily_gross_usd",
    "daily_loss_pct", "daily_loss_usd", "drawdown_halt_pct", "drawdown_halt_usd",
    "max_open_positions", "max_orders_24h", "consecutive_losses_halt", "cooldown_hours",
  ];
  const guardrailsValid = (
    exactKeys(guardrails, requiredGuardrailKeys)
    && exactNumber(guardrails.reserve_pct, 20)
    && exactRange(guardrails.reserve_usd, 20, 40)
    && exactNumber(guardrails.max_deployed_pct, 80)
    && exactRange(guardrails.max_deployed_usd, 80, 160)
    && exactNumber(guardrails.single_order_pct, 10)
    && exactRange(guardrails.single_order_usd, 10, 20)
    && exactNumber(guardrails.daily_gross_pct, 40)
    && exactRange(guardrails.daily_gross_usd, 40, 80)
    && exactNumber(guardrails.daily_loss_pct, 2)
    && exactRange(guardrails.daily_loss_usd, 2, 4)
    && exactNumber(guardrails.drawdown_halt_pct, 5)
    && exactRange(guardrails.drawdown_halt_usd, 5, 10)
    && exactNumber(guardrails.max_open_positions, 2)
    && exactNumber(guardrails.max_orders_24h, 4)
    && exactNumber(guardrails.consecutive_losses_halt, 2)
    && exactNumber(guardrails.cooldown_hours, 24)
  );
  const rangeText = (value) => {
    const low = Number(value?.min);
    const high = Number(value?.max);
    return Number.isFinite(low) && Number.isFinite(high) ? `$${low}–$${high}` : "--";
  };
  const rawChecks = Array.isArray(raw?.checks) ? raw.checks : [];
  const checks = new Map(
    rawChecks
      .filter((item) => item && typeof item.id === "string")
      .map((item) => [item.id, String(item.status || "UNKNOWN")]),
  );
  const requiredChecks = [
    "permission_boundary",
    "market_evidence",
    "forward_evidence",
    "fee_evidence",
    "instrument_rules",
    "order_book_depth",
    "security_isolation",
    "circuit_breaker_reconciliation",
  ];
  const allowedCheckStatuses = new Set(["PASS", "NOT_CHECKED", "INVALID", "BLOCK"]);
  const checksValid = (
    rawChecks.length === requiredChecks.length
    && checks.size === requiredChecks.length
    && requiredChecks.every((id) => allowedCheckStatuses.has(checks.get(id)))
  );
  const allChecksPass = checksValid && requiredChecks.every((id) => checks.get(id) === "PASS");
  const anyCheckBlocks = checksValid && requiredChecks.some((id) => ["BLOCK", "INVALID"].includes(checks.get(id)));
  const feeSchedule = raw?.fee_schedule || {};
  const feeScheduleValid = (
    exactKeys(feeSchedule, ["status", "account_specific", "public_default_accepted", "maker_fee", "taker_fee"])
    && feeSchedule.status === "NOT_CHECKED"
    && feeSchedule.account_specific === true
    && feeSchedule.public_default_accepted === false
    && feeSchedule.maker_fee === null
    && feeSchedule.taker_fee === null
    && checks.get("fee_evidence") === "NOT_CHECKED"
  );
  const instrumentRules = raw?.instrument_rules || {};
  const ruleSource = instrumentRules?.source || {};
  const ruleVerification = instrumentRules?.verification || {};
  const hashText = (value) => typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  const nativeNonnegativeInt = (value) => Number.isInteger(value) && value >= 0;
  const nativeBoolean = (value) => value === true || value === false;
  const positiveDecimalText = (value) => (
    typeof value === "string"
    && /^(?:0|[1-9]\d*)(?:\.\d+)?$/.test(value)
    && /[1-9]/.test(value)
    && (!value.includes(".") || !value.endsWith("0"))
  );
  const nonnegativeDecimalText = (value) => (
    value === "0" || positiveDecimalText(value)
  );
  const compareDecimalText = (left, right) => {
    if (!nonnegativeDecimalText(left) || !nonnegativeDecimalText(right)) return Number.NaN;
    const [leftWhole, leftFraction = ""] = left.split(".");
    const [rightWhole, rightFraction = ""] = right.split(".");
    if (leftWhole.length !== rightWhole.length) return leftWhole.length > rightWhole.length ? 1 : -1;
    if (leftWhole !== rightWhole) return leftWhole > rightWhole ? 1 : -1;
    const width = Math.max(leftFraction.length, rightFraction.length);
    const paddedLeft = leftFraction.padEnd(width, "0");
    const paddedRight = rightFraction.padEnd(width, "0");
    if (paddedLeft === paddedRight) return 0;
    return paddedLeft > paddedRight ? 1 : -1;
  };
  const scaledDecimalInteger = (value, places) => {
    if (!nonnegativeDecimalText(value) || !Number.isInteger(places) || places < 0) return null;
    const [whole, fraction = ""] = value.split(".");
    if (fraction.length > places) return null;
    return BigInt(`${whole}${fraction.padEnd(places, "0")}`);
  };
  const decimalSumEquals = (left, right, expected) => {
    if (![left, right, expected].every(nonnegativeDecimalText)) return false;
    const places = Math.max(
      (left.split(".")[1] || "").length,
      (right.split(".")[1] || "").length,
      (expected.split(".")[1] || "").length,
    );
    const leftUnits = scaledDecimalInteger(left, places);
    const rightUnits = scaledDecimalInteger(right, places);
    const expectedUnits = scaledDecimalInteger(expected, places);
    return leftUnits !== null && rightUnits !== null && expectedUnits !== null
      && leftUnits + rightUnits === expectedUnits;
  };
  const decimalDoubleEqualsSum = (value, left, right) => {
    if (![value, left, right].every(nonnegativeDecimalText)) return false;
    const places = Math.max(
      (value.split(".")[1] || "").length,
      (left.split(".")[1] || "").length,
      (right.split(".")[1] || "").length,
    );
    const valueUnits = scaledDecimalInteger(value, places);
    const leftUnits = scaledDecimalInteger(left, places);
    const rightUnits = scaledDecimalInteger(right, places);
    return valueUnits !== null && leftUnits !== null && rightUnits !== null
      && valueUnits * 2n === leftUnits + rightUnits;
  };
  const decimalRatioText = (numeratorText, denominatorText, places) => {
    if (!nonnegativeDecimalText(numeratorText) || !positiveDecimalText(denominatorText)) return "";
    const numeratorScale = (numeratorText.split(".")[1] || "").length;
    const denominatorScale = (denominatorText.split(".")[1] || "").length;
    const numerator = scaledDecimalInteger(numeratorText, numeratorScale);
    const denominator = scaledDecimalInteger(denominatorText, denominatorScale);
    if (numerator === null || denominator === null || denominator === 0n) return "";
    const ratioNumerator = numerator * (10n ** BigInt(denominatorScale)) * (10n ** BigInt(places));
    const ratioDenominator = denominator * (10n ** BigInt(numeratorScale));
    let rounded = ratioNumerator / ratioDenominator;
    const remainder = ratioNumerator % ratioDenominator;
    const twice = remainder * 2n;
    if (twice > ratioDenominator || (twice === ratioDenominator && rounded % 2n === 1n)) rounded += 1n;
    const digits = rounded.toString().padStart(places + 1, "0");
    if (places === 0) return digits;
    return `${digits.slice(0, -places)}.${digits.slice(-places)}`.replace(/0+$/, "").replace(/\.$/, "");
  };
  const decimalIntegerProductText = (value, multiplier) => {
    if (!nonnegativeDecimalText(value) || !Number.isInteger(multiplier) || multiplier < 0) return "";
    const places = (value.split(".")[1] || "").length;
    const units = scaledDecimalInteger(value, places);
    if (units === null) return "";
    const digits = (units * BigInt(multiplier)).toString().padStart(places + 1, "0");
    if (places === 0) return digits;
    return `${digits.slice(0, -places)}.${digits.slice(-places)}`.replace(/0+$/, "").replace(/\.$/, "");
  };
  const scaledUnitsText = (units, places) => {
    if (typeof units !== "bigint" || !Number.isInteger(places) || places < 0 || units < 0n) return "";
    const digits = units.toString().padStart(places + 1, "0");
    if (places === 0) return digits;
    return `${digits.slice(0, -places)}.${digits.slice(-places)}`.replace(/0+$/, "").replace(/\.$/, "");
  };
  const decimalRowsSumText = (rows, field, count) => {
    if (!Array.isArray(rows) || !Number.isInteger(count) || count <= 0 || count > rows.length) return "";
    const values = rows.slice(0, count).map((row) => row?.[field]);
    if (!values.every(nonnegativeDecimalText)) return "";
    const places = Math.max(...values.map((value) => (value.split(".")[1] || "").length));
    const total = values.reduce((sum, value) => sum + scaledDecimalInteger(value, places), 0n);
    return scaledUnitsText(total, places);
  };
  const decimalPriceSizeSumText = (rows, count) => {
    if (!Array.isArray(rows) || !Number.isInteger(count) || count <= 0 || count > rows.length) return "";
    const terms = rows.slice(0, count).map((row) => {
      if (!positiveDecimalText(row?.price) || !positiveDecimalText(row?.size)) return null;
      const pricePlaces = (row.price.split(".")[1] || "").length;
      const sizePlaces = (row.size.split(".")[1] || "").length;
      const priceUnits = scaledDecimalInteger(row.price, pricePlaces);
      const sizeUnits = scaledDecimalInteger(row.size, sizePlaces);
      return priceUnits === null || sizeUnits === null
        ? null
        : { units: priceUnits * sizeUnits, places: pricePlaces + sizePlaces };
    });
    if (terms.some((term) => term === null)) return "";
    const places = Math.max(...terms.map((term) => term.places));
    const total = terms.reduce(
      (sum, term) => sum + term.units * (10n ** BigInt(places - term.places)),
      0n,
    );
    return scaledUnitsText(total, places);
  };
  const decimalBandBoundaryText = (referencePrice, bandBps, side) => {
    if (
      !positiveDecimalText(referencePrice)
      || !Number.isInteger(bandBps)
      || bandBps <= 0
      || bandBps >= 10000
      || !["BID", "ASK"].includes(side)
    ) return "";
    const places = (referencePrice.split(".")[1] || "").length;
    const units = scaledDecimalInteger(referencePrice, places);
    if (units === null) return "";
    const factor = BigInt(side === "BID" ? 10000 - bandBps : 10000 + bandBps);
    return scaledUnitsText(units * factor, places + 4);
  };
  const decimalSelectedRowsSumText = (rows, field) => {
    if (!Array.isArray(rows)) return "";
    return rows.length === 0 ? "0" : decimalRowsSumText(rows, field, rows.length);
  };
  const decimalSelectedPriceSizeSumText = (rows) => {
    if (!Array.isArray(rows)) return "";
    return rows.length === 0 ? "0" : decimalPriceSizeSumText(rows, rows.length);
  };
  const ruleCapturedAt = ruleSource.captured_at_ms;
  const ruleMaxAge = ruleSource.max_age_ms;
  const ruleAge = (
    nativeNonnegativeInt(ruleCapturedAt) && nativeNonnegativeInt(ruleMaxAge)
      ? Date.now() - ruleCapturedAt
      : Number.NaN
  );
  const safeRuleEnvelope = (
    instrumentRules.schema_version === "public-instrument-rules-v1"
    && instrumentRules.mode === "PUBLIC_READ_ONLY"
    && instrumentRules.symbol === scopeSymbol
    && instrumentRules.venue === "OKX"
    && instrumentRules.instrument_type === "SPOT"
    && instrumentRules.minimum_cost === null
    && instrumentRules.public_only === true
    && instrumentRules.credentials_used === false
    && instrumentRules.read_only === true
    && instrumentRules.paper_authorized === false
    && instrumentRules.live_order_allowed === false
    && ruleSource.provider === "OKX_PUBLIC_API"
    && ruleSource.endpoint === "/api/v5/public/instruments"
    && nativeNonnegativeInt(ruleCapturedAt)
    && ruleCapturedAt > 0
    && nativeNonnegativeInt(ruleMaxAge)
    && ruleMaxAge > 0
  );
  const falseVerification = (
    exactKeys(ruleVerification, [
      "venue_rules_verified", "account_tradeability_verified",
      "account_fee_verified", "minimum_cost_verified",
    ])
    && ruleVerification.venue_rules_verified === false
    && ruleVerification.account_tradeability_verified === false
    && ruleVerification.account_fee_verified === false
    && ruleVerification.minimum_cost_verified === false
  );
  const verifiedRuleIdentity = scopeSymbol.split("-");
  const verifiedRulesValid = (
    safeRuleEnvelope
    && checks.get("instrument_rules") === "PASS"
    && instrumentRules.status === "VERIFIED"
    && instrumentRules.current === true
    && instrumentRules.asset_type === "crypto"
    && instrumentRules.instrument_state === "live"
    && positiveDecimalText(instrumentRules.tick_size)
    && positiveDecimalText(instrumentRules.lot_size)
    && positiveDecimalText(instrumentRules.minimum_order_size)
    && instrumentRules.size_unit === verifiedRuleIdentity[0]
    && instrumentRules.price_unit === verifiedRuleIdentity[1]
    && instrumentRules.ccxt_symbol === `${verifiedRuleIdentity[0]}/${verifiedRuleIdentity[1]}`
    && Array.isArray(instrumentRules.upcoming_changes)
    && instrumentRules.upcoming_changes.length === 0
    && Array.isArray(instrumentRules.blockers)
    && instrumentRules.blockers.length === 0
    && hashText(instrumentRules.rules_hash)
    && hashText(instrumentRules.snapshot_hash)
    && instrumentRules.hash_verified === true
    && Number.isFinite(ruleAge)
    && ruleAge >= -5000
    && ruleAge <= ruleMaxAge
    && exactKeys(ruleVerification, [
      "venue_rules_verified", "account_tradeability_verified",
      "account_fee_verified", "minimum_cost_verified",
    ])
    && ruleVerification.venue_rules_verified === true
    && ruleVerification.account_tradeability_verified === false
    && ruleVerification.account_fee_verified === false
    && ruleVerification.minimum_cost_verified === false
  );
  const unverifiedRuleStatuses = new Set(["NOT_APPLICABLE", "NOT_CHECKED", "NOT_FOUND", "UNAVAILABLE"]);
  const emptyUnverifiedRules = (
    instrumentRules.instrument_state === ""
    && instrumentRules.tick_size === ""
    && instrumentRules.lot_size === ""
    && instrumentRules.minimum_order_size === ""
    && instrumentRules.size_unit === ""
    && instrumentRules.price_unit === ""
    && Array.isArray(instrumentRules.upcoming_changes)
    && instrumentRules.upcoming_changes.length === 0
    && Array.isArray(instrumentRules.blockers)
    && instrumentRules.blockers.length > 0
  );
  const unverifiedAssetValid = instrumentRules.status === "NOT_APPLICABLE"
    ? instrumentRules.asset_type === "not_applicable"
    : instrumentRules.asset_type === "crypto";
  const unverifiedRulesValid = (
    safeRuleEnvelope
    && checks.get("instrument_rules") === "NOT_CHECKED"
    && unverifiedRuleStatuses.has(instrumentRules.status)
    && instrumentRules.current === false
    && emptyUnverifiedRules
    && unverifiedAssetValid
    && falseVerification
    && instrumentRules.hash_verified === false
    && instrumentRules.rules_hash === ""
    && instrumentRules.snapshot_hash === ""
    && Number.isFinite(ruleAge)
    && ruleAge >= -5000
  );
  const staleRulesValid = (
    safeRuleEnvelope
    && checks.get("instrument_rules") === "NOT_CHECKED"
    && instrumentRules.status === "STALE"
    && instrumentRules.current === false
    && instrumentRules.asset_type === "crypto"
    && instrumentRules.instrument_state === "live"
    && positiveDecimalText(instrumentRules.tick_size)
    && positiveDecimalText(instrumentRules.lot_size)
    && positiveDecimalText(instrumentRules.minimum_order_size)
    && instrumentRules.size_unit === verifiedRuleIdentity[0]
    && instrumentRules.price_unit === verifiedRuleIdentity[1]
    && instrumentRules.ccxt_symbol === `${verifiedRuleIdentity[0]}/${verifiedRuleIdentity[1]}`
    && Array.isArray(instrumentRules.upcoming_changes)
    && instrumentRules.upcoming_changes.length === 0
    && hashText(instrumentRules.rules_hash)
    && hashText(instrumentRules.snapshot_hash)
    && instrumentRules.hash_verified === true
    && Number.isFinite(ruleAge)
    && ruleAge >= -5000
    && exactKeys(ruleVerification, [
      "venue_rules_verified", "account_tradeability_verified",
      "account_fee_verified", "minimum_cost_verified",
    ])
    && ruleVerification.venue_rules_verified === true
    && ruleVerification.account_tradeability_verified === false
    && ruleVerification.account_fee_verified === false
    && ruleVerification.minimum_cost_verified === false
  );
  const blockedRulesValid = (
    ["BLOCK", "INVALID"].includes(checks.get("instrument_rules"))
    && safeRuleEnvelope
  );
  const instrumentRulesValid = verifiedRulesValid || unverifiedRulesValid || staleRulesValid || blockedRulesValid;
  const quantityPreview = raw?.quantity_preview || {};
  const quantityBudget = quantityPreview?.budget_basis || {};
  const quantityPrice = quantityPreview?.price_evidence || {};
  const quantityRules = quantityPreview?.rule_binding || {};
  const quantityQuantization = quantityPreview?.quantization || {};
  const quantityRiskBuffer = quantityPreview?.risk_check_buffer || {};
  const quantityUnknowns = quantityPreview?.unknowns || {};
  const quantityPermissions = quantityPreview?.permissions || {};
  const quantityRows = Array.isArray(quantityPreview?.rows) ? quantityPreview.rows : [];
  const rawSizingReference = marketTruth?.quote?.sizing_reference || {};
  const allowedQuantityStatuses = new Set([
    "PREVIEW_ONLY", "BELOW_MIN_SIZE", "TOP_OF_BOOK_LIMITED",
    "NEEDS_EVIDENCE", "NOT_APPLICABLE", "BLOCK",
  ]);
  const quantityBaseValid = (
    quantityPreview.schema_version === "small-capital-quantity-preview-v2"
    && quantityPreview.mode === "GROSS_QUOTE_TO_BASE_ESTIMATE_ONLY"
    && quantityPreview.symbol === scopeSymbol
    && allowedQuantityStatuses.has(quantityPreview.status)
    && exactKeys(quantityBudget, ["amounts", "currency", "usd_equivalence_verified", "display_relation"])
    && Array.isArray(quantityBudget.amounts)
    && quantityBudget.amounts.length === 2
    && quantityBudget.amounts[0] === "10"
    && quantityBudget.amounts[1] === "20"
    && quantityBudget.currency === "USDT"
    && quantityBudget.usd_equivalence_verified === false
    && quantityBudget.display_relation === "REFERENCE_ONLY"
    && exactKeys(quantityQuantization, [
      "mode", "sizing_unit", "venue_auto_rounding_assumed", "price_tick_used",
      "order_parameters_generated", "side_inferred", "tgt_ccy_generated",
    ])
    && quantityQuantization.mode === "FLOOR_TO_PUBLIC_LOT"
    && quantityQuantization.sizing_unit === "BASE_CURRENCY_ESTIMATE"
    && quantityQuantization.venue_auto_rounding_assumed === false
    && quantityQuantization.price_tick_used === false
    && quantityQuantization.order_parameters_generated === false
    && quantityQuantization.side_inferred === false
    && quantityQuantization.tgt_ccy_generated === false
    && exactKeys(quantityRiskBuffer, [
      "status", "rate", "currency", "basis", "scenario", "semantics",
      "account_balance_checked", "fee_estimate", "slippage_estimate",
      "order_intent_created", "order_parameters_generated",
    ])
    && quantityRiskBuffer.status === "ILLUSTRATIVE_ONLY"
    && quantityRiskBuffer.rate === "0.05"
    && quantityRiskBuffer.currency === "USDT"
    && quantityRiskBuffer.basis === "REQUESTED_QUOTE_SPEND"
    && quantityRiskBuffer.scenario === "HYPOTHETICAL_OKX_SPOT_MARKET_BUY_QUOTE_SPEND"
    && quantityRiskBuffer.semantics === "TEMP_RISK_CHECK_BUFFER_NOT_FEE"
    && quantityRiskBuffer.account_balance_checked === false
    && quantityRiskBuffer.fee_estimate === false
    && quantityRiskBuffer.slippage_estimate === false
    && quantityRiskBuffer.order_intent_created === false
    && quantityRiskBuffer.order_parameters_generated === false
    && exactKeys(quantityUnknowns, [
      "account_fee", "slippage", "minimum_cost", "account_balance",
      "usd_usdt_conversion", "spread_and_side", "fill_price",
      "order_book_depth", "venue_slippage_policy",
    ])
    && Object.values(quantityUnknowns).every((value) => value === "NOT_CHECKED")
    && exactKeys(quantityPermissions, [
      "planning_only", "order_submission_allowed", "execution_allowed", "paper_authorized", "live_order_allowed",
    ])
    && quantityPermissions.planning_only === true
    && quantityPermissions.order_submission_allowed === false
    && quantityPermissions.execution_allowed === false
    && quantityPermissions.paper_authorized === false
    && quantityPermissions.live_order_allowed === false
    && quantityPreview.execution_allowed === false
    && quantityPreview.paper_authorized === false
    && quantityPreview.live_order_allowed === false
    && Array.isArray(quantityPreview.blockers)
    && hashText(quantityPreview.preview_hash)
    && quantityPreview.hash_verified === true
  );
  const quantityRowKeys = [
    "budget_quote_amount", "raw_quantity", "lot_steps", "quantity_floor", "quantity_unit",
    "reference_notional", "notional_currency", "unallocated_before_costs", "lot_aligned",
    "risk_check_buffer_quote", "planning_quote_availability", "best_ask_size_reference",
    "top_of_book_reference_covers_quantity", "top_of_book_depth_verified",
    "within_quote_budget", "minimum_order_size_met", "minimum_cost_checked", "fees_included",
    "slippage_included", "executable",
  ];
  const calculatedQuantityRowsValid = (
    quantityRows.length === 2
    && quantityRows.every((row, index) => (
      exactKeys(row, quantityRowKeys)
      && row.budget_quote_amount === quantityBudget.amounts[index]
      && positiveDecimalText(row.raw_quantity)
      && /^(?:0|[1-9]\d*)$/.test(row.lot_steps)
      && nonnegativeDecimalText(row.quantity_floor)
      && row.quantity_unit === instrumentRules.size_unit
      && nonnegativeDecimalText(row.reference_notional)
      && row.notional_currency === "USDT"
      && nonnegativeDecimalText(row.unallocated_before_costs)
      && row.risk_check_buffer_quote === (index === 0 ? "0.5" : "1")
      && row.planning_quote_availability === (index === 0 ? "10.5" : "21")
      && positiveDecimalText(row.best_ask_size_reference)
      && row.best_ask_size_reference === quantityPrice.available_size
      && nativeBoolean(row.top_of_book_reference_covers_quantity)
      && row.top_of_book_depth_verified === false
      && row.lot_aligned === true
      && row.within_quote_budget === true
      && nativeBoolean(row.minimum_order_size_met)
      && row.minimum_cost_checked === false
      && row.fees_included === false
      && row.slippage_included === false
      && row.executable === false
    ))
  );
  const calculatedQuantityContractValid = (
    quantityBaseValid
    && ["PREVIEW_ONLY", "BELOW_MIN_SIZE", "TOP_OF_BOOK_LIMITED"].includes(quantityPreview.status)
    && checks.get("market_evidence") === "PASS"
    && checks.get("instrument_rules") === "PASS"
    && verifiedRulesValid
    && exactKeys(quantityPrice, [
      "value", "kind", "available_size", "size_basis", "source", "timestamp_ms", "snapshot_id",
      "depth_levels", "is_executable_quote", "in_memory_only", "client_price_used",
      "fallback_used", "cache_regression",
    ])
    && positiveDecimalText(quantityPrice.value)
    && quantityPrice.kind === "PUBLIC_BEST_ASK_REFERENCE"
    && positiveDecimalText(quantityPrice.available_size)
    && quantityPrice.size_basis === "BASE_CURRENCY"
    && String(quantityPrice.source || "")
    && nativeNonnegativeInt(quantityPrice.timestamp_ms)
    && quantityPrice.timestamp_ms > 0
    && nativeNonnegativeInt(marketTruth?.max_observation_age_ms)
    && marketTruth.max_observation_age_ms > 0
    && Date.now() - quantityPrice.timestamp_ms >= -5000
    && Date.now() - quantityPrice.timestamp_ms <= marketTruth.max_observation_age_ms
    && String(quantityPrice.snapshot_id || "")
    && quantityPrice.in_memory_only === true
    && quantityPrice.client_price_used === false
    && quantityPrice.depth_levels === 1
    && quantityPrice.is_executable_quote === false
    && quantityPrice.fallback_used === false
    && quantityPrice.cache_regression === false
    && marketTruth?.schema_version === "market-data-truth-v1"
    && marketTruth?.status === "READY"
    && marketTruth?.mode === "REALTIME_READY"
    && marketTruth?.snapshot_id === quantityPrice.snapshot_id
    && rawSizingReference?.status === "PASS"
    && rawSizingReference?.kind === "PUBLIC_BEST_ASK_REFERENCE"
    && rawSizingReference?.value === quantityPrice.value
    && rawSizingReference?.available_size === quantityPrice.available_size
    && rawSizingReference?.size_basis === quantityPrice.size_basis
    && rawSizingReference?.source === quantityPrice.source
    && rawSizingReference?.timestamp_ms === quantityPrice.timestamp_ms
    && rawSizingReference?.snapshot_id === quantityPrice.snapshot_id
    && rawSizingReference?.depth_levels === 1
    && rawSizingReference?.is_executable_quote === false
    && rawSizingReference?.in_memory_only === true
    && rawSizingReference?.client_price_used === false
    && rawSizingReference?.fallback_used === false
    && rawSizingReference?.cache_regression === false
    && exactKeys(quantityRules, [
      "rules_hash", "snapshot_hash", "lot_size", "minimum_order_size",
      "effective_minimum_order_size", "minimum_cost", "base_currency", "quote_currency",
    ])
    && quantityRules.rules_hash === instrumentRules.rules_hash
    && quantityRules.snapshot_hash === instrumentRules.snapshot_hash
    && quantityRules.lot_size === instrumentRules.lot_size
    && quantityRules.minimum_order_size === instrumentRules.minimum_order_size
    && positiveDecimalText(quantityRules.effective_minimum_order_size)
    && quantityRules.minimum_cost === null
    && quantityRules.base_currency === instrumentRules.size_unit
    && quantityRules.quote_currency === "USDT"
    && calculatedQuantityRowsValid
    && (quantityPreview.status === "PREVIEW_ONLY"
      ? quantityRows.every((row) => (
        row.minimum_order_size_met === true && row.top_of_book_reference_covers_quantity === true
      ))
      : quantityPreview.status === "BELOW_MIN_SIZE"
        ? quantityRows.some((row) => row.minimum_order_size_met === false)
        : quantityRows.every((row) => row.minimum_order_size_met === true)
          && quantityRows.some((row) => row.top_of_book_reference_covers_quantity === false))
  );
  const emptyQuantityContractValid = (
    quantityBaseValid
    && ["NEEDS_EVIDENCE", "NOT_APPLICABLE", "BLOCK"].includes(quantityPreview.status)
    && quantityRows.length === 0
    && quantityPrice.value === ""
    && quantityPrice.client_price_used === false
    && quantityRules.minimum_cost === null
    && (quantityPreview.status !== "NOT_APPLICABLE" || instrumentRules.status === "NOT_APPLICABLE")
  );
  const quantityPreviewValid = calculatedQuantityContractValid || emptyQuantityContractValid;
  const publicOrderBook = raw?.public_order_book || {};
  const bookSource = publicOrderBook?.source || {};
  const bookValidation = publicOrderBook?.validation || {};
  const bookPermissions = publicOrderBook?.permissions || {};
  const bookAsks = Array.isArray(publicOrderBook?.asks) ? publicOrderBook.asks : [];
  const bookBids = Array.isArray(publicOrderBook?.bids) ? publicOrderBook.bids : [];
  const bookEnvelopeKeys = [
    "schema_version", "mode", "status", "symbol", "venue", "instrument_type", "book_half_used",
    "liquidity_scope", "checksum", "checksum_policy", "exchange_timestamp_ms", "sequence_id",
    "observed_at_ms", "max_age_ms", "snapshot_id", "depth_requested", "bids", "asks",
    "source", "validation", "book_hash", "hash_verified", "current", "planning_usable",
    "complete_book_verified", "is_executable_quote", "permissions", "execution_allowed",
    "paper_authorized", "live_order_allowed", "blockers", "contract_hash", "contract_hash_verified",
  ];
  const bookBaseValid = (
    exactKeys(publicOrderBook, bookEnvelopeKeys)
    && publicOrderBook.schema_version === "okx-public-order-book-planning-v1"
    && publicOrderBook.mode === "PUBLIC_READ_ONLY_PLANNING"
    && publicOrderBook.symbol === scopeSymbol
    && publicOrderBook.venue === "OKX"
    && publicOrderBook.instrument_type === "SPOT"
    && publicOrderBook.book_half_used === "ASKS"
    && publicOrderBook.liquidity_scope === "STANDARD_BOOK_NON_RPI"
    && publicOrderBook.checksum === null
    && publicOrderBook.checksum_policy === "NOT_APPLICABLE"
    && publicOrderBook.depth_requested === 20
    && nativeNonnegativeInt(publicOrderBook.exchange_timestamp_ms)
    && nativeNonnegativeInt(publicOrderBook.sequence_id)
    && nativeNonnegativeInt(publicOrderBook.observed_at_ms)
    && nativeNonnegativeInt(publicOrderBook.max_age_ms)
    && publicOrderBook.max_age_ms > 0
    && exactKeys(bookSource, ["provider", "endpoint", "public", "credentials_used"])
    && bookSource.provider === "OKX_PUBLIC_API"
    && bookSource.endpoint === "/api/v5/market/books"
    && bookSource.public === true
    && bookSource.credentials_used === false
    && exactKeys(bookPermissions, [
      "planning_only", "order_submission_allowed", "execution_allowed", "paper_authorized", "live_order_allowed",
    ])
    && bookPermissions.planning_only === true
    && bookPermissions.order_submission_allowed === false
    && bookPermissions.execution_allowed === false
    && bookPermissions.paper_authorized === false
    && bookPermissions.live_order_allowed === false
    && publicOrderBook.complete_book_verified === false
    && publicOrderBook.is_executable_quote === false
    && publicOrderBook.execution_allowed === false
    && publicOrderBook.paper_authorized === false
    && publicOrderBook.live_order_allowed === false
    && Array.isArray(publicOrderBook.blockers)
    && hashText(publicOrderBook.contract_hash)
    && publicOrderBook.contract_hash_verified === true
  );
  const normalizedBookRow = (row, index) => (
    exactKeys(row, ["level", "price", "size", "order_count"])
    && row.level === index + 1
    && positiveDecimalText(row.price)
    && positiveDecimalText(row.size)
    && typeof row.order_count === "string"
    && /^(?:|0|[1-9]\d*)$/.test(row.order_count)
  );
  const strictBookOrder = (rows, ascending) => rows.every((row, index) => (
    index === 0
    || (ascending
      ? compareDecimalText(rows[index - 1].price, row.price) < 0
      : compareDecimalText(rows[index - 1].price, row.price) > 0)
  ));
  const structuredBookValid = (
    bookAsks.length >= 2
    && bookAsks.length <= 20
    && bookBids.length >= 1
    && bookBids.length <= 20
    && bookAsks.every(normalizedBookRow)
    && bookBids.every(normalizedBookRow)
    && strictBookOrder(bookAsks, true)
    && strictBookOrder(bookBids, false)
    && compareDecimalText(bookBids[0].price, bookAsks[0].price) <= 0
  );
  const bookValidationShapeValid = exactKeys(bookValidation, [
    "timestamp_current", "bids_descending", "asks_ascending", "uncrossed",
    "cache_regression", "sequence_status",
  ]);
  const bookAge = Date.now() - publicOrderBook.exchange_timestamp_ms;
  const verifiedBookValid = (
    bookBaseValid
    && checks.get("order_book_depth") === "PASS"
    && publicOrderBook.status === "VERIFIED"
    && publicOrderBook.current === true
    && publicOrderBook.planning_usable === true
    && structuredBookValid
    && bookValidationShapeValid
    && bookValidation.timestamp_current === true
    && bookValidation.bids_descending === true
    && bookValidation.asks_ascending === true
    && bookValidation.uncrossed === true
    && bookValidation.cache_regression === false
    && ["SNAPSHOT_ONLY", "MONOTONIC_OR_EQUAL", "EPOCH_UNPROVEN"].includes(bookValidation.sequence_status)
    && nativeNonnegativeInt(publicOrderBook.exchange_timestamp_ms)
    && publicOrderBook.exchange_timestamp_ms > 0
    && publicOrderBook.observed_at_ms > 0
    && Number.isFinite(bookAge)
    && bookAge >= -5000
    && bookAge <= publicOrderBook.max_age_ms
    && hashText(publicOrderBook.book_hash)
    && publicOrderBook.hash_verified === true
    && publicOrderBook.snapshot_id === `${scopeSymbol}:${publicOrderBook.exchange_timestamp_ms}:${publicOrderBook.sequence_id}:${publicOrderBook.book_hash.slice(0, 12)}`
    && publicOrderBook.blockers.length === 0
  );
  const safeEmptyBookValid = (
    bookBaseValid
    && checks.get("order_book_depth") === "NOT_CHECKED"
    && ["NOT_CHECKED", "UNAVAILABLE", "NOT_APPLICABLE"].includes(publicOrderBook.status)
    && bookAsks.length === 0
    && bookBids.length === 0
    && publicOrderBook.exchange_timestamp_ms === 0
    && publicOrderBook.sequence_id === 0
    && publicOrderBook.snapshot_id === ""
    && publicOrderBook.book_hash === ""
    && publicOrderBook.hash_verified === false
    && publicOrderBook.current === false
    && publicOrderBook.planning_usable === false
    && bookValidationShapeValid
    && bookValidation.timestamp_current === false
    && bookValidation.bids_descending === false
    && bookValidation.asks_ascending === false
    && bookValidation.uncrossed === false
    && bookValidation.cache_regression === false
    && bookValidation.sequence_status === "UNAVAILABLE"
    && publicOrderBook.blockers.length > 0
  );
  const staleBookValid = (
    bookBaseValid
    && checks.get("order_book_depth") === "NOT_CHECKED"
    && publicOrderBook.status === "STALE"
    && publicOrderBook.current === false
    && publicOrderBook.planning_usable === false
    && structuredBookValid
    && bookValidationShapeValid
    && bookValidation.bids_descending === true
    && bookValidation.asks_ascending === true
    && bookValidation.uncrossed === true
    && bookValidation.cache_regression === false
    && ["SNAPSHOT_ONLY", "MONOTONIC_OR_EQUAL", "EPOCH_UNPROVEN"].includes(bookValidation.sequence_status)
    && hashText(publicOrderBook.book_hash)
    && publicOrderBook.hash_verified === true
    && publicOrderBook.blockers.length > 0
  );
  const blockedBookValid = (
    bookBaseValid
    && checks.get("order_book_depth") === "BLOCK"
    && publicOrderBook.status === "BLOCK"
    && publicOrderBook.current === false
    && publicOrderBook.planning_usable === false
    && publicOrderBook.blockers.length > 0
  );
  const publicOrderBookValid = verifiedBookValid || safeEmptyBookValid || staleBookValid || blockedBookValid;

  const microstructureTruth = raw?.microstructure_truth || {};
  const microEvidence = microstructureTruth?.evidence || {};
  const microTop = microstructureTruth?.top_of_book || {};
  const microDepth = microstructureTruth?.visible_depth || {};
  const microPriceBands = microstructureTruth?.price_band_depth || {};
  const microPriceBandRows = Array.isArray(microPriceBands?.rows) ? microPriceBands.rows : [];
  const microInterpretation = microstructureTruth?.interpretation || {};
  const microUnknowns = microstructureTruth?.unknowns || {};
  const microPermissions = microstructureTruth?.permissions || {};
  const microStatuses = new Set(["OBSERVATION_ONLY", "NOT_CHECKED", "NOT_APPLICABLE", "BLOCK"]);
  const microBaseValid = (
    exactKeys(microstructureTruth, [
      "schema_version", "mode", "status", "symbol", "venue", "instrument_type",
      "book_sides_observed", "liquidity_scope", "evidence", "top_of_book", "visible_depth",
      "price_band_depth",
      "interpretation", "unknowns", "permissions", "read_only", "execution_allowed",
      "paper_authorized", "live_order_allowed", "blockers", "microstructure_hash", "hash_verified",
    ])
    && microstructureTruth.schema_version === "public-order-book-microstructure-v2"
    && microstructureTruth.mode === "PUBLIC_READ_ONLY_OBSERVATION"
    && microStatuses.has(microstructureTruth.status)
    && microstructureTruth.symbol === scopeSymbol
    && microstructureTruth.venue === "OKX"
    && microstructureTruth.instrument_type === "SPOT"
    && ["NONE", "BIDS_AND_ASKS"].includes(microstructureTruth.book_sides_observed)
    && microstructureTruth.liquidity_scope === "STANDARD_BOOK_NON_RPI"
    && exactKeys(microInterpretation, [
      "descriptive_only", "signal_allowed", "direction_inferred", "trade_flow_inferred", "spoofing_checked",
    ])
    && microInterpretation.descriptive_only === true
    && microInterpretation.signal_allowed === false
    && microInterpretation.direction_inferred === false
    && microInterpretation.trade_flow_inferred === false
    && microInterpretation.spoofing_checked === false
    && exactKeys(microUnknowns, [
      "complete_order_book", "rpi_access", "hidden_liquidity", "queue_position",
      "cancellations_after_snapshot", "execution_probability", "future_direction",
    ])
    && Object.values(microUnknowns).every((value) => value === "NOT_CHECKED")
    && exactKeys(microPermissions, [
      "planning_only", "order_submission_allowed", "execution_allowed", "paper_authorized", "live_order_allowed",
    ])
    && microPermissions.planning_only === true
    && microPermissions.order_submission_allowed === false
    && microPermissions.execution_allowed === false
    && microPermissions.paper_authorized === false
    && microPermissions.live_order_allowed === false
    && microstructureTruth.read_only === true
    && microstructureTruth.execution_allowed === false
    && microstructureTruth.paper_authorized === false
    && microstructureTruth.live_order_allowed === false
    && Array.isArray(microstructureTruth.blockers)
    && hashText(microstructureTruth.microstructure_hash)
    && microstructureTruth.hash_verified === true
  );
  const microEvidenceShapeValid = exactKeys(microEvidence, [
    "book_snapshot_id", "book_hash", "book_contract_hash", "source_provider", "source_endpoint",
    "exchange_timestamp_ms", "observed_at_ms", "evaluated_at_ms", "max_age_ms", "depth_requested",
    "observed_bid_levels", "observed_ask_levels", "comparison_level_count",
    "sequence_status", "sequence_continuity", "checksum_policy",
  ]);
  const microTopShapeValid = exactKeys(microTop, [
    "best_bid", "best_ask", "mid_price", "spread_quote", "spread_bps", "spread_bps_basis",
    "spread_bps_places", "spread_bps_rounding",
  ]);
  const microDepthShapeValid = exactKeys(microDepth, [
    "basis", "bid_base_total", "ask_base_total", "bid_quote_notional", "ask_quote_notional",
    "total_quote_notional", "bid_share", "ask_share", "bid_to_ask_quote_ratio",
    "share_places", "ratio_places", "ratio_rounding", "complete_book_verified",
  ]);
  const microPriceBandShapeValid = (
    exactKeys(microPriceBands, [
      "basis", "bands_bps", "boundary_inclusive", "reference_mid_price", "coverage_rule",
      "quote_notional_semantics", "rows", "complete_book_verified",
    ])
    && microPriceBands.basis === "SYMMETRIC_MID_PRICE_BPS"
    && Array.isArray(microPriceBands.bands_bps)
    && microPriceBands.bands_bps.length === 3
    && microPriceBands.bands_bps.every((value, index) => value === [5, 10, 25][index])
    && microPriceBands.boundary_inclusive === true
    && microPriceBands.coverage_rule === "VISIBLE_PREFIX_REACHES_BAND_BOUNDARY"
    && microPriceBands.quote_notional_semantics === "VISIBLE_LOWER_BOUND_WHEN_BOUNDARY_NOT_COVERED"
    && Array.isArray(microPriceBands.rows)
    && microPriceBands.complete_book_verified === false
  );
  const microPriceBandRowKeys = [
    "band_bps", "bid_floor_price", "ask_ceiling_price", "visible_bid_levels", "visible_ask_levels",
    "visible_bid_base_total", "visible_ask_base_total", "visible_bid_quote_notional",
    "visible_ask_quote_notional", "bid_band_boundary_covered", "ask_band_boundary_covered",
    "two_sided_band_boundary_covered",
  ];
  const expectedMicroPriceBandRows = [5, 10, 25].map((bandBps) => {
    const bidFloorPrice = decimalBandBoundaryText(microTop.mid_price, bandBps, "BID");
    const askCeilingPrice = decimalBandBoundaryText(microTop.mid_price, bandBps, "ASK");
    const visibleBids = bookBids.filter((row) => compareDecimalText(row?.price, bidFloorPrice) >= 0);
    const visibleAsks = bookAsks.filter((row) => compareDecimalText(row?.price, askCeilingPrice) <= 0);
    const bidBoundaryCovered = Boolean(
      bidFloorPrice
      && bookBids.length > 0
      && compareDecimalText(bookBids[bookBids.length - 1]?.price, bidFloorPrice) <= 0
    );
    const askBoundaryCovered = Boolean(
      askCeilingPrice
      && bookAsks.length > 0
      && compareDecimalText(bookAsks[bookAsks.length - 1]?.price, askCeilingPrice) >= 0
    );
    return {
      band_bps: bandBps,
      bid_floor_price: bidFloorPrice,
      ask_ceiling_price: askCeilingPrice,
      visible_bid_levels: visibleBids.length,
      visible_ask_levels: visibleAsks.length,
      visible_bid_base_total: decimalSelectedRowsSumText(visibleBids, "size"),
      visible_ask_base_total: decimalSelectedRowsSumText(visibleAsks, "size"),
      visible_bid_quote_notional: decimalSelectedPriceSizeSumText(visibleBids),
      visible_ask_quote_notional: decimalSelectedPriceSizeSumText(visibleAsks),
      bid_band_boundary_covered: bidBoundaryCovered,
      ask_band_boundary_covered: askBoundaryCovered,
      two_sided_band_boundary_covered: bidBoundaryCovered && askBoundaryCovered,
    };
  });
  const microPriceBandRowsExact = (
    microPriceBandRows.length === 3
    && microPriceBandRows.every((row, index) => {
      const expected = expectedMicroPriceBandRows[index];
      return (
        exactKeys(row, microPriceBandRowKeys)
        && nativeNonnegativeInt(row.band_bps)
        && row.band_bps === expected.band_bps
        && positiveDecimalText(row.bid_floor_price)
        && positiveDecimalText(row.ask_ceiling_price)
        && row.bid_floor_price === expected.bid_floor_price
        && row.ask_ceiling_price === expected.ask_ceiling_price
        && nativeNonnegativeInt(row.visible_bid_levels)
        && nativeNonnegativeInt(row.visible_ask_levels)
        && row.visible_bid_levels === expected.visible_bid_levels
        && row.visible_ask_levels === expected.visible_ask_levels
        && nonnegativeDecimalText(row.visible_bid_base_total)
        && nonnegativeDecimalText(row.visible_ask_base_total)
        && nonnegativeDecimalText(row.visible_bid_quote_notional)
        && nonnegativeDecimalText(row.visible_ask_quote_notional)
        && row.visible_bid_base_total === expected.visible_bid_base_total
        && row.visible_ask_base_total === expected.visible_ask_base_total
        && row.visible_bid_quote_notional === expected.visible_bid_quote_notional
        && row.visible_ask_quote_notional === expected.visible_ask_quote_notional
        && nativeBoolean(row.bid_band_boundary_covered)
        && nativeBoolean(row.ask_band_boundary_covered)
        && nativeBoolean(row.two_sided_band_boundary_covered)
        && row.bid_band_boundary_covered === expected.bid_band_boundary_covered
        && row.ask_band_boundary_covered === expected.ask_band_boundary_covered
        && row.two_sided_band_boundary_covered === expected.two_sided_band_boundary_covered
      );
    })
  );
  const microPriceBandRowsMonotonic = microPriceBandRows.every((row, index) => {
    if (index === 0) return true;
    const previous = microPriceBandRows[index - 1];
    if (!exactKeys(row, microPriceBandRowKeys) || !exactKeys(previous, microPriceBandRowKeys)) return false;
    return (
      compareDecimalText(previous.bid_floor_price, row.bid_floor_price) > 0
      && compareDecimalText(previous.ask_ceiling_price, row.ask_ceiling_price) < 0
      && row.visible_bid_levels >= previous.visible_bid_levels
      && row.visible_ask_levels >= previous.visible_ask_levels
      && compareDecimalText(row.visible_bid_base_total, previous.visible_bid_base_total) >= 0
      && compareDecimalText(row.visible_ask_base_total, previous.visible_ask_base_total) >= 0
      && compareDecimalText(row.visible_bid_quote_notional, previous.visible_bid_quote_notional) >= 0
      && compareDecimalText(row.visible_ask_quote_notional, previous.visible_ask_quote_notional) >= 0
      && (!row.bid_band_boundary_covered || previous.bid_band_boundary_covered)
      && (!row.ask_band_boundary_covered || previous.ask_band_boundary_covered)
      && (!row.two_sided_band_boundary_covered || previous.two_sided_band_boundary_covered)
    );
  });
  const microComparisonLevelCount = microEvidence.comparison_level_count;
  const expectedMicroBidBase = decimalRowsSumText(bookBids, "size", microComparisonLevelCount);
  const expectedMicroAskBase = decimalRowsSumText(bookAsks, "size", microComparisonLevelCount);
  const expectedMicroBidQuote = decimalPriceSizeSumText(bookBids, microComparisonLevelCount);
  const expectedMicroAskQuote = decimalPriceSizeSumText(bookAsks, microComparisonLevelCount);
  const microAge = Date.now() - microEvidence.exchange_timestamp_ms;
  const observedMicrostructureValid = (
    microBaseValid
    && microstructureTruth.status === "OBSERVATION_ONLY"
    && microstructureTruth.book_sides_observed === "BIDS_AND_ASKS"
    && microstructureTruth.blockers.length === 0
    && verifiedBookValid
    && microEvidenceShapeValid
    && microEvidence.book_snapshot_id === publicOrderBook.snapshot_id
    && microEvidence.book_hash === publicOrderBook.book_hash
    && microEvidence.book_contract_hash === publicOrderBook.contract_hash
    && microEvidence.source_provider === bookSource.provider
    && microEvidence.source_endpoint === bookSource.endpoint
    && microEvidence.exchange_timestamp_ms === publicOrderBook.exchange_timestamp_ms
    && microEvidence.observed_at_ms === publicOrderBook.observed_at_ms
    && nativeNonnegativeInt(microEvidence.evaluated_at_ms)
    && microEvidence.evaluated_at_ms - microEvidence.exchange_timestamp_ms >= -5000
    && microEvidence.max_age_ms === publicOrderBook.max_age_ms
    && microEvidence.depth_requested === 20
    && microEvidence.observed_bid_levels === bookBids.length
    && microEvidence.observed_ask_levels === bookAsks.length
    && microEvidence.comparison_level_count === Math.min(bookBids.length, bookAsks.length)
    && microEvidence.comparison_level_count > 0
    && microEvidence.sequence_status === bookValidation.sequence_status
    && microEvidence.sequence_continuity === "NOT_PROVABLE_REST"
    && microEvidence.checksum_policy === "NOT_APPLICABLE"
    && Number.isFinite(microAge)
    && microAge >= -5000
    && microAge <= microEvidence.max_age_ms
    && microTopShapeValid
    && microTop.best_bid === bookBids[0].price
    && microTop.best_ask === bookAsks[0].price
    && positiveDecimalText(microTop.mid_price)
    && nonnegativeDecimalText(microTop.spread_quote)
    && nonnegativeDecimalText(microTop.spread_bps)
    && microTop.spread_bps_basis === "MID_PRICE"
    && microTop.spread_bps_places === 8
    && microTop.spread_bps_rounding === "HALF_EVEN"
    && decimalSumEquals(microTop.best_bid, microTop.spread_quote, microTop.best_ask)
    && decimalDoubleEqualsSum(microTop.mid_price, microTop.best_bid, microTop.best_ask)
    && microTop.spread_bps === decimalRatioText(
      decimalIntegerProductText(microTop.spread_quote, 10000),
      microTop.mid_price,
      8,
    )
    && microDepthShapeValid
    && microDepth.basis === "QUOTE_NOTIONAL"
    && positiveDecimalText(microDepth.bid_base_total)
    && positiveDecimalText(microDepth.ask_base_total)
    && positiveDecimalText(microDepth.bid_quote_notional)
    && positiveDecimalText(microDepth.ask_quote_notional)
    && positiveDecimalText(microDepth.total_quote_notional)
    && microDepth.bid_base_total === expectedMicroBidBase
    && microDepth.ask_base_total === expectedMicroAskBase
    && microDepth.bid_quote_notional === expectedMicroBidQuote
    && microDepth.ask_quote_notional === expectedMicroAskQuote
    && nonnegativeDecimalText(microDepth.bid_share)
    && nonnegativeDecimalText(microDepth.ask_share)
    && nonnegativeDecimalText(microDepth.bid_to_ask_quote_ratio)
    && microDepth.share_places === 12
    && microDepth.ratio_places === 12
    && microDepth.ratio_rounding === "HALF_EVEN"
    && microDepth.complete_book_verified === false
    && decimalSumEquals(microDepth.bid_quote_notional, microDepth.ask_quote_notional, microDepth.total_quote_notional)
    && decimalSumEquals(microDepth.bid_share, microDepth.ask_share, "1")
    && microDepth.bid_share === decimalRatioText(microDepth.bid_quote_notional, microDepth.total_quote_notional, 12)
    && microDepth.bid_to_ask_quote_ratio === decimalRatioText(microDepth.bid_quote_notional, microDepth.ask_quote_notional, 12)
    && microPriceBandShapeValid
    && microPriceBands.reference_mid_price === microTop.mid_price
    && microPriceBandRowsExact
    && microPriceBandRowsMonotonic
  );
  const emptyMicrostructureValid = (
    microBaseValid
    && ["NOT_CHECKED", "NOT_APPLICABLE", "BLOCK"].includes(microstructureTruth.status)
    && microstructureTruth.book_sides_observed === "NONE"
    && microstructureTruth.blockers.length > 0
    && microEvidenceShapeValid
    && microEvidence.book_snapshot_id === ""
    && microEvidence.book_hash === ""
    && microEvidence.book_contract_hash === ""
    && microEvidence.source_provider === "OKX_PUBLIC_API"
    && microEvidence.source_endpoint === "/api/v5/market/books"
    && microEvidence.exchange_timestamp_ms === 0
    && microEvidence.observed_at_ms === 0
    && microEvidence.evaluated_at_ms === 0
    && microEvidence.max_age_ms === 5000
    && microEvidence.depth_requested === 20
    && microEvidence.observed_bid_levels === 0
    && microEvidence.observed_ask_levels === 0
    && microEvidence.comparison_level_count === 0
    && microEvidence.sequence_status === "UNAVAILABLE"
    && microEvidence.sequence_continuity === "NOT_PROVABLE_REST"
    && microEvidence.checksum_policy === "NOT_APPLICABLE"
    && microTopShapeValid
    && [microTop.best_bid, microTop.best_ask, microTop.mid_price, microTop.spread_quote, microTop.spread_bps]
      .every((value) => value === "")
    && microTop.spread_bps_basis === "MID_PRICE"
    && microTop.spread_bps_places === 8
    && microTop.spread_bps_rounding === "HALF_EVEN"
    && microDepthShapeValid
    && microDepth.basis === "QUOTE_NOTIONAL"
    && [
      microDepth.bid_base_total, microDepth.ask_base_total, microDepth.bid_quote_notional,
      microDepth.ask_quote_notional, microDepth.total_quote_notional, microDepth.bid_share,
      microDepth.ask_share, microDepth.bid_to_ask_quote_ratio,
    ].every((value) => value === "")
    && microDepth.share_places === 12
    && microDepth.ratio_places === 12
    && microDepth.ratio_rounding === "HALF_EVEN"
    && microDepth.complete_book_verified === false
    && microPriceBandShapeValid
    && microPriceBands.reference_mid_price === ""
    && microPriceBandRows.length === 0
    && (microstructureTruth.status !== "NOT_APPLICABLE" || publicOrderBook.status === "NOT_APPLICABLE")
    && (microstructureTruth.status !== "NOT_CHECKED" || !verifiedBookValid)
    && (microstructureTruth.status !== "BLOCK" || checks.get("order_book_depth") === "BLOCK")
  );
  const microstructureTruthValid = observedMicrostructureValid || emptyMicrostructureValid;

  const depthPreview = raw?.depth_impact_preview || {};
  const depthBudget = depthPreview?.budget_basis || {};
  const depthEvidence = depthPreview?.evidence || {};
  const depthRules = depthPreview?.rule_binding || {};
  const depthPrecision = depthPreview?.display_precision || {};
  const depthUnknowns = depthPreview?.unknowns || {};
  const depthPermissions = depthPreview?.permissions || {};
  const depthRows = Array.isArray(depthPreview?.rows) ? depthPreview.rows : [];
  const allowedDepthStatuses = new Set([
    "DEPTH_PREVIEW_ONLY", "VISIBLE_DEPTH_CAPACITY_LIMITED", "BELOW_MIN_SIZE",
    "NOT_CHECKED", "NOT_APPLICABLE", "BLOCK",
  ]);
  const depthPreviewBaseValid = (
    exactKeys(depthPreview, [
      "schema_version", "mode", "status", "symbol", "budget_basis", "evidence",
      "rule_binding", "display_precision", "rows", "unknowns", "permissions", "execution_allowed",
      "paper_authorized", "live_order_allowed", "blockers", "preview_hash", "hash_verified",
    ])
    && depthPreview.schema_version === "small-capital-order-book-impact-v1"
    && depthPreview.mode === "VISIBLE_ASK_DEPTH_REFERENCE_ONLY"
    && depthPreview.symbol === scopeSymbol
    && allowedDepthStatuses.has(depthPreview.status)
    && exactKeys(depthBudget, ["amounts", "currency", "usd_equivalence_verified"])
    && Array.isArray(depthBudget.amounts)
    && depthBudget.amounts.length === 2
    && depthBudget.amounts[0] === "10"
    && depthBudget.amounts[1] === "20"
    && depthBudget.currency === "USDT"
    && depthBudget.usd_equivalence_verified === false
    && exactKeys(depthPrecision, [
      "quantity_price_cost", "coverage_ratio_places", "vwap_places", "impact_bps_places",
    ])
    && depthPrecision.quantity_price_cost === "EXACT_FINITE_DECIMAL"
    && depthPrecision.coverage_ratio_places === 12
    && depthPrecision.vwap_places === 12
    && depthPrecision.impact_bps_places === 8
    && exactKeys(depthUnknowns, [
      "complete_order_book", "rpi_access", "hidden_liquidity", "queue_position",
      "account_balance", "account_fee", "slippage", "minimum_cost", "arrival_latency",
      "actual_fill", "usd_usdt_conversion",
    ])
    && Object.values(depthUnknowns).every((value) => value === "NOT_CHECKED")
    && exactKeys(depthPermissions, [
      "planning_only", "order_submission_allowed", "execution_allowed", "paper_authorized", "live_order_allowed",
    ])
    && depthPermissions.planning_only === true
    && depthPermissions.order_submission_allowed === false
    && depthPermissions.execution_allowed === false
    && depthPermissions.paper_authorized === false
    && depthPermissions.live_order_allowed === false
    && depthPreview.execution_allowed === false
    && depthPreview.paper_authorized === false
    && depthPreview.live_order_allowed === false
    && Array.isArray(depthPreview.blockers)
    && hashText(depthPreview.preview_hash)
    && depthPreview.hash_verified === true
  );
  const depthEvidenceValid = (
    exactKeys(depthEvidence, [
      "book_snapshot_id", "book_hash", "book_contract_hash", "source", "endpoint", "exchange_timestamp_ms",
      "observed_at_ms", "depth_requested", "observed_ask_levels", "liquidity_scope",
      "checksum_policy", "complete_book_verified", "same_snapshot_as_ticker",
      "is_executable_quote", "hash_verified",
    ])
    && depthEvidence.book_snapshot_id === publicOrderBook.snapshot_id
    && depthEvidence.book_hash === publicOrderBook.book_hash
    && depthEvidence.book_contract_hash === publicOrderBook.contract_hash
    && depthEvidence.source === bookSource.provider
    && depthEvidence.endpoint === bookSource.endpoint
    && depthEvidence.exchange_timestamp_ms === publicOrderBook.exchange_timestamp_ms
    && depthEvidence.observed_at_ms === publicOrderBook.observed_at_ms
    && depthEvidence.depth_requested === 20
    && depthEvidence.observed_ask_levels === bookAsks.length
    && depthEvidence.liquidity_scope === "STANDARD_BOOK_NON_RPI"
    && depthEvidence.checksum_policy === "NOT_APPLICABLE"
    && depthEvidence.complete_book_verified === false
    && depthEvidence.same_snapshot_as_ticker === false
    && depthEvidence.is_executable_quote === false
    && depthEvidence.hash_verified === true
  );
  const depthRuleBindingValid = (
    exactKeys(depthRules, [
      "rules_hash", "snapshot_hash", "lot_size", "minimum_order_size", "base_currency", "quote_currency",
    ])
    && depthRules.rules_hash === instrumentRules.rules_hash
    && depthRules.snapshot_hash === instrumentRules.snapshot_hash
    && depthRules.lot_size === instrumentRules.lot_size
    && depthRules.minimum_order_size === instrumentRules.minimum_order_size
    && depthRules.base_currency === instrumentRules.size_unit
    && depthRules.quote_currency === instrumentRules.price_unit
  );
  const depthRowKeys = [
    "budget_quote_amount", "quantity_floor", "quantity_unit", "lot_steps",
    "visible_reference_cost", "visible_depth_quote", "visible_depth_shortfall_quote",
    "unallocated_after_lot_floor", "coverage_ratio", "visible_vwap_reference",
    "best_ask_reference", "last_consumed_price", "impact_bps", "levels_used",
    "visible_levels_scanned", "observed_depth_covers_budget", "minimum_order_size_met",
    "within_quote_budget", "fees_included", "account_balance_checked",
    "complete_book_verified", "executable",
  ];
  const depthRowsValid = (
    depthRows.length === 2
    && depthRows.every((row, index) => {
      const zeroQuantity = row.quantity_floor === "0";
      const budgetText = depthBudget.amounts[index];
      return (
        exactKeys(row, depthRowKeys)
        && row.budget_quote_amount === budgetText
        && nonnegativeDecimalText(row.quantity_floor)
        && row.quantity_unit === instrumentRules.size_unit
        && /^(?:0|[1-9]\d*)$/.test(row.lot_steps)
        && nonnegativeDecimalText(row.visible_reference_cost)
        && nonnegativeDecimalText(row.visible_depth_quote)
        && nonnegativeDecimalText(row.visible_depth_shortfall_quote)
        && nonnegativeDecimalText(row.unallocated_after_lot_floor)
        && nonnegativeDecimalText(row.coverage_ratio)
        && compareDecimalText(row.coverage_ratio, "1") <= 0
        && (zeroQuantity
          ? row.visible_reference_cost === "0" && row.visible_vwap_reference === ""
          : compareDecimalText(row.visible_reference_cost, "0") > 0
            && positiveDecimalText(row.visible_vwap_reference))
        && positiveDecimalText(row.best_ask_reference)
        && row.best_ask_reference === bookAsks[0].price
        && positiveDecimalText(row.last_consumed_price)
        && nonnegativeDecimalText(row.impact_bps)
        && nativeNonnegativeInt(row.levels_used)
        && nativeNonnegativeInt(row.visible_levels_scanned)
        && (zeroQuantity ? row.levels_used === 0 : row.levels_used > 0)
        && row.visible_levels_scanned > 0
        && row.levels_used <= row.visible_levels_scanned
        && row.visible_levels_scanned <= bookAsks.length
        && nativeBoolean(row.observed_depth_covers_budget)
        && nativeBoolean(row.minimum_order_size_met)
        && row.within_quote_budget === true
        && row.fees_included === false
        && row.account_balance_checked === false
        && row.complete_book_verified === false
        && row.executable === false
        && compareDecimalText(row.visible_reference_cost, row.visible_depth_quote) <= 0
        && compareDecimalText(row.visible_depth_quote, budgetText) <= 0
        && compareDecimalText(row.visible_depth_shortfall_quote, budgetText) <= 0
        && compareDecimalText(row.unallocated_after_lot_floor, budgetText) <= 0
        && decimalSumEquals(row.visible_depth_quote, row.visible_depth_shortfall_quote, budgetText)
        && decimalSumEquals(row.visible_reference_cost, row.unallocated_after_lot_floor, budgetText)
        && row.coverage_ratio === decimalRatioText(row.visible_depth_quote, budgetText, 12)
        && (row.observed_depth_covers_budget
          ? row.visible_depth_shortfall_quote === "0"
            && row.visible_depth_quote === budgetText
            && row.coverage_ratio === "1"
          : compareDecimalText(row.visible_depth_shortfall_quote, "0") > 0
            && compareDecimalText(row.coverage_ratio, "1") < 0)
      );
    })
  );
  const calculatedDepthContractValid = (
    depthPreviewBaseValid
    && ["DEPTH_PREVIEW_ONLY", "VISIBLE_DEPTH_CAPACITY_LIMITED", "BELOW_MIN_SIZE"].includes(depthPreview.status)
    && verifiedBookValid
    && observedMicrostructureValid
    && verifiedRulesValid
    && checks.get("order_book_depth") === "PASS"
    && depthEvidenceValid
    && depthRuleBindingValid
    && depthRowsValid
    && (depthPreview.status === "DEPTH_PREVIEW_ONLY"
      ? depthPreview.blockers.length === 0
        && depthRows.every((row) => row.observed_depth_covers_budget && row.minimum_order_size_met)
      : depthPreview.status === "VISIBLE_DEPTH_CAPACITY_LIMITED"
        ? depthRows.some((row) => !row.observed_depth_covers_budget)
          && depthRows.every((row) => row.minimum_order_size_met)
          && depthPreview.blockers.length === 1
          && depthPreview.blockers[0] === "visible_order_book_does_not_cover_all_budgets"
        : depthRows.some((row) => !row.minimum_order_size_met)
          && depthPreview.blockers.length === 1
          && depthPreview.blockers[0] === "one_or_more_depth_tiers_below_public_minimum_size")
  );
  const emptyDepthContractValid = (
    depthPreviewBaseValid
    && ["NOT_CHECKED", "NOT_APPLICABLE", "BLOCK"].includes(depthPreview.status)
    && depthRows.length === 0
    && exactKeys(depthEvidence, [
      "book_snapshot_id", "book_hash", "book_contract_hash", "source", "endpoint", "exchange_timestamp_ms",
      "observed_at_ms", "depth_requested", "observed_ask_levels", "liquidity_scope",
      "checksum_policy", "complete_book_verified", "same_snapshot_as_ticker",
      "is_executable_quote", "hash_verified",
    ])
    && depthEvidence.book_snapshot_id === ""
    && depthEvidence.book_hash === ""
    && depthEvidence.book_contract_hash === ""
    && depthEvidence.hash_verified === false
    && exactKeys(depthRules, [
      "rules_hash", "snapshot_hash", "lot_size", "minimum_order_size", "base_currency", "quote_currency",
    ])
    && Object.values(depthRules).every((value) => value === "")
  );
  const depthPreviewValid = calculatedDepthContractValid || emptyDepthContractValid;
  const planHashValid = hashText(raw?.plan_hash);
  const allowedStatuses = new Set(["PLANNING_ONLY", "NEEDS_EVIDENCE", "BLOCK"]);
  const contractValid = (
    modeValid
    && topLevelAuthorityValid
    && permissionsValid
    && budgetValid
    && scopeValid
    && guardrailsValid
    && checksValid
    && feeScheduleValid
    && instrumentRulesValid
    && quantityPreviewValid
    && publicOrderBookValid
    && microstructureTruthValid
    && depthPreviewValid
    && planHashValid
    && allowedStatuses.has(raw.status)
  );
  if (!contractValid) {
    return {
      ...unknownView,
      status: "BLOCK",
      permissionsText: "只读规划阻断 · 模拟未授权 · 实盘永久硬锁",
      evidenceGapText: evidenceSmallCapitalGapPresentation({ status: "BLOCK" }).text,
    };
  }
  let status = raw.status;
  if (anyCheckBlocks) status = "BLOCK";
  if (quantityPreview.status === "BLOCK") status = "BLOCK";
  if (depthPreview.status === "BLOCK") status = "BLOCK";
  if (microstructureTruth.status === "BLOCK") status = "BLOCK";
  if (status === "PLANNING_ONLY" && !allChecksPass) status = "NEEDS_EVIDENCE";
  const firstBlockedCheckId = requiredChecks.find(
    (id) => ["BLOCK", "INVALID"].includes(checks.get(id)),
  ) || "";
  const firstMissingCheckId = requiredChecks.find((id) => checks.get(id) !== "PASS") || "";
  const evidenceGap = evidenceSmallCapitalGapPresentation({
    status,
    checkId: status === "BLOCK" ? firstBlockedCheckId : firstMissingCheckId,
  });
  const maxOrders = Number(guardrails.max_orders_24h);
  const consecutiveLosses = Number(guardrails.consecutive_losses_halt);
  const cooldownHours = Number(guardrails.cooldown_hours);
  const circuitText = (
    Number.isInteger(maxOrders) && Number.isInteger(consecutiveLosses) && Number.isFinite(cooldownHours)
      ? `示例：连续亏损 ${consecutiveLosses} 次即停止观察 · 24h 最多 ${maxOrders} 次 · 冷却 ${cooldownHours}h`
      : "--"
  );
  const ruleVisible = verifiedRulesValid;
  const instrumentRulesText = ruleVisible
    ? `Tick ${instrumentRules.tick_size} · Lot ${instrumentRules.lot_size} · Min ${instrumentRules.minimum_order_size} ${instrumentRules.size_unit}`
    : "Tick -- · Lot -- · Min --";
  let ruleEvidenceText = ruleVisible
    ? `OKX公开 · 抓取 ${platformTruthTimeText(ruleCapturedAt)} · Hash ${instrumentRules.snapshot_hash.slice(0, 12)} · 费率/滑点/最小金额 未核验`
    : `规则 ${researchStatusShort(instrumentRules.status, "待核验")} · 检查 ${platformTruthTimeText(ruleCapturedAt)} · Hash -- · 费率/滑点/最小金额 未核验`;
  let ruleEvidenceTitle = ruleVisible ? instrumentRules.snapshot_hash : "";
  let singleOrderText = rangeText(guardrails.single_order_usd);
  let quantityPreviewText = "等待可信报价、公开深度与 lot/minSz";
  let quantityPreviewTitle = "完整深度、余额、费率、最小金额与 USD/USDT 换算均未核验";
  if (calculatedDepthContractValid) {
    singleOrderText = "$10–$20 · 多档仅观察";
    const priceBandLines = microPriceBandRows.map((row) => {
      const bidAmount = `${row.bid_band_boundary_covered ? "" : "已见 "}${number(row.visible_bid_quote_notional, 2)}`;
      const askAmount = `${row.ask_band_boundary_covered ? "" : "已见 "}${number(row.visible_ask_quote_notional, 2)}`;
      const partial = row.two_sided_band_boundary_covered
        ? ""
        : !row.bid_band_boundary_covered && !row.ask_band_boundary_covered
          ? " · 双侧部分"
          : !row.bid_band_boundary_covered
            ? " · 买侧部分"
            : " · 卖侧部分";
      return `${row.band_bps} bps｜买 ${bidAmount} · 卖 ${askAmount}${partial}`;
    });
    const depthLines = [
      "盘口真值 · 距中价带内可见名义（USDT）· 非信号",
      ...priceBandLines,
      "“部分”仅表示当前返回档位未抵达该侧带宽边界；数值为已见下界",
      ...depthRows.map((row) => {
        const minimumText = row.minimum_order_size_met ? "达到公开 minSz" : "低于公开 minSz";
        if (!row.observed_depth_covers_budget) {
          const coveragePct = `${(Number(row.coverage_ratio) * 100).toFixed(1).replace(/\.0$/, "")}%`;
          return `${row.budget_quote_amount} USDT：可见深度 ${row.visible_depth_quote} USDT`
            + ` · 深度短缺 ${row.visible_depth_shortfall_quote} USDT · 未外推 · 覆盖率 ${coveragePct} · ${minimumText}`;
        }
        return `${row.budget_quote_amount} USDT：数量参考 ${row.quantity_floor} ${row.quantity_unit}`
          + ` · 可见档均价 ${row.visible_vwap_reference} USDT · 较卖一 +${row.impact_bps} bps`
          + ` · lot取整余款 ${row.unallocated_after_lot_floor} USDT`
          + ` · 覆盖 ${row.levels_used} 档 · ${minimumText}`;
      }),
      "仅观察当前公开档位；完整深度/RPI资格/余额/费率/滑点/最小金额/到达延迟/实际成交/USD-USDT 均未核验",
    ];
    quantityPreviewText = depthLines.join("\n");
    quantityPreviewTitle = `价格带以中价 ${microTop.mid_price} 为对称基准；盘口价差 ${microTop.spread_bps} bps；“已见/部分”表示当前返回档位未抵达该侧带宽边界，数值只是可见下界；不是方向信号、完整深度、预计滑点、成交保证或下单授权；逐档扫描公开标准卖盘并向下对齐 lot`
      + `\nMicrostructure ${microstructureTruth.microstructure_hash}`;
    ruleEvidenceText = `OKX公开 · Depth ${bookAsks.length}/20 · ${platformTruthTimeText(publicOrderBook.exchange_timestamp_ms)}`
      + ` · DepthHash ${publicOrderBook.book_hash.slice(0, 12)} · RuleHash ${instrumentRules.snapshot_hash.slice(0, 12)}`
      + " · 费率/最小金额 未核验";
    ruleEvidenceTitle = `Depth ${publicOrderBook.book_hash}\nMicrostructure ${microstructureTruth.microstructure_hash}\nRules ${instrumentRules.snapshot_hash}`;
  } else if (calculatedQuantityContractValid) {
    quantityPreviewText = `卖一 ${quantityPrice.value} USDT · ` + quantityRows.map((row) => {
      const rowState = !row.minimum_order_size_met
        ? "低于 minSz"
        : !row.top_of_book_reference_covers_quantity
          ? "超过当前一档卖一量"
          : "估算达到 minSz";
      return `${row.budget_quote_amount} USDT≈${row.quantity_floor} ${row.quantity_unit}`
        + `（${rowState}；5% 缓冲后的名义规划值 ${row.planning_quote_availability} USDT）`;
    }).join(" · ")
      + " · 5%名义缓冲参考，非余额冻结或手续费"
      + " · 仅一档卖一，完整深度/余额/费率/滑点/最小金额/USD-USDT 均未核验";
  } else if (quantityPreview.status === "NOT_APPLICABLE") {
    quantityPreviewText = "当前股票标的不适用 OKX 现货数量预览";
  } else if (quantityPreview.status === "BLOCK") {
    quantityPreviewText = "数量预览合同异常 · 已隐藏";
  }
  return {
    status,
    permissionsText: evidenceStatusPresentation("plan", status).permissionText,
    budgetText: "USD 100–200 · 名义封套",
    singleOrderText,
    quantityPreviewText,
    quantityPreviewTitle,
    dailyGuardText: `示例周转上限 ${rangeText(guardrails.daily_gross_usd)} · 示例亏损上限 ${rangeText(guardrails.daily_loss_usd)}`,
    instrumentRulesText,
    ruleEvidenceText,
    ruleEvidenceTitle,
    circuitText,
    evidenceGapText: evidenceGap.text,
  };
}

function renderPlatformSmallCapitalPlan(raw, marketTruth = {}, requestContext = null) {
  const view = platformSmallCapitalPlanView(raw, marketTruth, requestContext);
  const statusCopy = evidenceStatusPresentation("plan", view.status);
  const root = $("platformSmallCapitalPlanCenter");
  if (root) {
    root.dataset.planStatus = view.status;
    root.title = `原始纯规划状态 ${view.status}`;
  }
  if ($("platformSmallCapitalPlanStatus")) {
    $("platformSmallCapitalPlanStatus").textContent = statusCopy.label;
    $("platformSmallCapitalPlanStatus").title = `原始状态 ${view.status}`;
  }
  if ($("platformSmallCapitalPlanPermissions")) $("platformSmallCapitalPlanPermissions").textContent = view.permissionsText;
  if ($("platformSmallCapitalBudget")) $("platformSmallCapitalBudget").textContent = view.budgetText;
  if ($("platformSmallCapitalSingleOrder")) $("platformSmallCapitalSingleOrder").textContent = view.singleOrderText;
  if ($("platformSmallCapitalQuantityPreview")) {
    $("platformSmallCapitalQuantityPreview").textContent = view.quantityPreviewText;
    $("platformSmallCapitalQuantityPreview").title = view.quantityPreviewTitle;
  }
  if ($("platformSmallCapitalDailyGuard")) $("platformSmallCapitalDailyGuard").textContent = view.dailyGuardText;
  if ($("platformSmallCapitalInstrumentRules")) $("platformSmallCapitalInstrumentRules").textContent = view.instrumentRulesText;
  if ($("platformSmallCapitalRuleEvidence")) {
    $("platformSmallCapitalRuleEvidence").textContent = view.ruleEvidenceText;
    $("platformSmallCapitalRuleEvidence").title = view.ruleEvidenceTitle;
  }
  if ($("platformSmallCapitalCircuitBreaker")) $("platformSmallCapitalCircuitBreaker").textContent = view.circuitText;
  if ($("platformSmallCapitalEvidenceGap")) $("platformSmallCapitalEvidenceGap").textContent = view.evidenceGapText;
  return view;
}

function resetPlatformSmallCapitalPlan(status = "UNKNOWN", evidenceGapText = "下一条尚缺证据：尚未核验 · 仅研究，不生成订单") {
  renderPlatformSmallCapitalPlan({}, {}, null);
  const statusCopy = evidenceStatusPresentation("plan", status);
  const root = $("platformSmallCapitalPlanCenter");
  if (root) root.dataset.planStatus = status;
  if ($("platformSmallCapitalPlanStatus")) {
    $("platformSmallCapitalPlanStatus").textContent = statusCopy.label;
    $("platformSmallCapitalPlanStatus").title = `原始状态 ${status}`;
  }
  if ($("platformSmallCapitalEvidenceGap")) $("platformSmallCapitalEvidenceGap").textContent = evidenceGapText;
}

const RUNTIME_MUTATION_CONTROL_IDS = [
  "freezeBacktest",
  "armStrategy",
  "stopStrategy",
  "resetPaper",
  "manualBuy",
  "manualSell",
  "manualClose",
  "addCondition",
];

function setRuntimeMutationControls(readOnly, detail = "当前实例只读，只能预览") {
  RUNTIME_MUTATION_CONTROL_IDS.forEach((id) => {
    const control = $(id);
    if (!control) return;
    if (readOnly) {
      if (control.dataset.runtimePreviousDisabled === undefined) {
        control.dataset.runtimePreviousDisabled = control.disabled ? "1" : "0";
        control.dataset.runtimePreviousTitle = control.title || "";
      }
      control.disabled = true;
      control.title = detail;
      return;
    }
    if (control.dataset.runtimePreviousDisabled !== undefined) {
      control.disabled = control.dataset.runtimePreviousDisabled === "1";
      control.title = control.dataset.runtimePreviousTitle || "";
      delete control.dataset.runtimePreviousDisabled;
      delete control.dataset.runtimePreviousTitle;
    }
  });
}

function renderPlatformControlCenter(data, requestContext = null) {
  if (requestContext && !isCurrentPlatformControlRequest(requestContext)) return false;
  renderPlatformAuthoritySummary();
  state.platformControl = data;
  const summary = data.summary || {};
  const paper = data.paper || {};
  const risk = data.risk || {};
  const pipeline = data.pipeline || {};
  const latest = pipeline.latest || {};
  const executor = data.executor || {};
  const dataHealth = data.data_health || {};
  const dataRevision = data.data_revision || {};
  const audit = data.audit || {};
  const ledger = data.paper_ledger || {};
  const mutations = data.mutation_journal || {};
  const latestOrder = data.latest_order || {};
  const forward = data.forward_validation || {};
  const forwardReadiness = forward.readiness || {};
  const forwardProgress = forwardReadiness.progress || {};
  const experimentRegistry = forward.experiment_registry || {};
  const runtimeReadOnly = !(
    data.read_only === false
    && data.live_trading_hard_block === true
    && data.live_order_allowed === false
  );
  setRuntimeMutationControls(runtimeReadOnly);

  const strategyCardRawStatus = summary.pipeline_status || "NOT_STARTED";
  const strategyCardPresentation = evidenceResearchStatusPresentation(strategyCardRawStatus);
  setPlatformBlock(
    "platformStrategyCard",
    strategyCardRawStatus,
    latest.run_id
      ? latest.legacy_blockers?.length
        ? `${latest.symbol || "--"} / 旧记录需重验：${latest.legacy_blockers.join("、")}`
        : `${latest.symbol || "--"} / ${latest.strategy_id || "--"} / ${latest.current_stage || "definition"}`
      : "尚无已登记研究证据；新机制需先预注册",
    {
      neutral: true,
      label: strategyCardPresentation.label,
      title: `原始状态 ${strategyCardPresentation.rawStatus} · ${strategyCardPresentation.detailText}`,
    },
  );
  const claimedPaperAuthorized = data.paper_authorized === true
    && risk.paper_authorized === true
    && !runtimeReadOnly;
  const paperCardStatus = paper.armed ? "RUNNING" : "IDLE";
  setPlatformBlock(
    "platformPaperCard",
    paperCardStatus,
    `${paper.symbol || "--"} / 权益 ${number(paper.equity, 2)} / 持仓 ${paper.position_side || "FLAT"}`,
    {
      neutral: true,
      label: "模拟未授权",
      title: `原始状态 ${paperCardStatus} · 上游权限声称=${String(claimedPaperAuthorized)}\n模拟权限与研究证据分离 · 实盘永久硬锁`,
    },
  );
  const riskCardRawStatus = risk.status || risk.pretrade?.status || summary.risk_status || "CHECKING";
  const riskCardBlocked = ["BLOCK", "BLOCKED", "ERROR", "FAILED", "REJECTED", "UNSAFE"].includes(String(riskCardRawStatus).toUpperCase());
  setPlatformBlock(
    "platformRiskCard",
    riskCardRawStatus,
    `${risk.automated_paper_order_allowed ? "上游模拟条件声称可用 · 仍需权限复核" : risk.paper_order_allowed ? "上游手动模拟入口声称可用 · 仍需权限复核" : "模拟执行阻断"} / ${risk.runtime_read_only ? "运行只读" : "运行可写"} / 风险规则 ${risk.risk_policy_allows_paper ? "通过" : "阻断"} / 实盘永久禁止`,
    {
      neutral: true,
      label: riskCardBlocked ? "风控证据存在阻断" : "风控证据待核验 · 不授予执行",
      title: `原始状态 ${riskCardRawStatus} · 模拟未授权 · 实盘永久硬锁`,
    },
  );
  const marketTruthView = platformMarketTruthView(data, requestContext);
  renderPlatformMarketTruth(marketTruthView);
  setPlatformBlock(
    "platformLedgerCard",
    ledger.restart_ready ? "RESTART_READY" : "BLOCK",
    `SQLite v${ledger.schema_version || "--"} / 待结算 ${ledger.pending_settlement_count || 0} / 成交 ${ledger.fill_count || 0}`,
    {
      neutral: true,
      label: ledger.restart_ready ? "账本恢复证据已核对" : "账本恢复证据阻断",
      title: `原始状态 ${ledger.restart_ready ? "RESTART_READY" : "BLOCK"} · 不代表交易授权`,
    },
  );
  const forwardView = renderPlatformForwardObservation(forward);
  renderPlatformSmallCapitalPlan(
    data.small_capital_plan || {},
    data.market_truth || data.data_health?.data_truth || {},
    requestContext,
  );
  const forwardCardStatus = experimentRegistry.status === "BLOCK" ? "BLOCK" : forwardView.status;
  const forwardCardCopy = evidenceStatusPresentation("forward", forwardCardStatus);
  setPlatformBlock(
    "platformForwardCard",
    forwardCardStatus,
    `${forwardView.latestBar} · 待处理 ${forwardView.pendingText} · 下一次 ${forwardView.nextCheckText}`,
    {
      neutral: true,
      label: forwardCardCopy.label,
      title: `原始状态 ${forwardCardStatus}\n${forwardView.summary}\n时钟 ${platformForwardProgressText(forwardProgress.externally_attested_observations, forwardProgress.required_externally_attested_observations)} · 调仓 ${platformForwardProgressText(forwardProgress.planned_rebalances, forwardProgress.required_planned_rebalances)}`,
    },
  );
  if ($("platformAuditDetail")) $("platformAuditDetail").textContent = `SQLite / ${audit.event_count || 0} 条事件 / 实盘下单 0`;

  const pipelineHasRun = Boolean(latest.run_id);
  const pipelineSummary = evidencePipelineSummaryPresentation(latest.status, pipelineHasRun);
  if ($("platformPipelineRun")) {
    $("platformPipelineRun").textContent = pipelineSummary.label;
    $("platformPipelineRun").dataset.rawStatus = pipelineSummary.rawStatus;
    $("platformPipelineRun").dataset.evidenceState = pipelineSummary.stateKind;
    $("platformPipelineRun").title = pipelineHasRun
      ? `运行 ${latest.run_id} · 原始状态 ${pipelineSummary.rawStatus}`
      : `原始状态 ${pipelineSummary.rawStatus}`;
  }
  const stageLabels = {
    definition: "策略定义",
    backtest: "可复现回测",
    doctor: "策略体检",
    paper_authorization: "模拟授权",
    paper_run: "模拟运行",
    audit_review: "审计复盘",
    live_trading: "实盘",
  };
  const stages = latest.stages || {};
  if ($("platformPipelineStages")) {
    $("platformPipelineStages").innerHTML = Object.entries(stageLabels).map(([key, label]) => {
      const row = stages[key] || { status: key === "live_trading" ? "BLOCKED" : "WAIT" };
      const presentation = evidencePipelineStagePresentation(key, row.status, {
        paperAuthorized: false,
        liveHardLocked: data.live_trading_hard_block === true && data.live_order_allowed === false,
      });
      const reason = String(row.reason || "").trim();
      const rawOnlyReason = /^(PASS|READY|COMPLETE|COMPLETED|WAIT|WAITING|BLOCK|BLOCKED)$/i.test(reason);
      const detail = !rawOnlyReason && reason
        ? reason
        : row.blockers?.length
          ? `缺少 ${row.blockers.join("、")}`
          : presentation.detailText;
      return `
        <div
          class="platform-stage evidence-stage"
          role="listitem"
          aria-label="${escapeHtml(`${label}：${presentation.label}`)}"
          data-stage="${escapeHtml(key)}"
          data-evidence-state="${escapeHtml(presentation.stateKind)}"
          data-raw-status="${escapeHtml(presentation.rawStatus)}"
          title="${escapeHtml(`原始状态 ${presentation.rawStatus}${reason ? `\n${reason}` : ""}`)}"
        >
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(presentation.label)}</strong>
          <em>${escapeHtml(detail)}</em>
        </div>
      `;
    }).join("");
  }

  if ($("platformExecutorSummary")) $("platformExecutorSummary").textContent = `${executor.order_count || 0} 笔订单 / ${executor.working_count || 0} 笔挂单`;
  const lifecycleStates = ["CREATED", "RISK_CHECKED", "ACCEPTED", "WORKING", "PARTIALLY_FILLED", "FILLED", "CANCELLED", "REJECTED"];
  if ($("platformExecutorStates")) {
    $("platformExecutorStates").innerHTML = lifecycleStates.map((name) => `
      <div><span>${escapeHtml(name)}</span><strong>${Number(executor.counts?.[name] || 0)}</strong></div>
    `).join("");
  }
  if ($("platformLedgerRestart")) {
    $("platformLedgerRestart").textContent = ledger.restart_ready ? "恢复证据已核对" : "恢复证据阻断";
    $("platformLedgerRestart").className = "flat";
  }
  if ($("platformLedgerVersion")) $("platformLedgerVersion").textContent = String(ledger.account_version || 0);
  if ($("platformMutationStatus")) {
    const completeCount = Number(mutations.counts?.COMPLETE || 0);
    const inProgressCount = Number(mutations.counts?.IN_PROGRESS || 0);
    $("platformMutationStatus").textContent = inProgressCount ? `写入处理中 ${inProgressCount}` : `已完成 ${completeCount}`;
    $("platformMutationStatus").className = "flat";
  }
  if ($("platformReplayLatest")) {
    $("platformReplayLatest").disabled = !latestOrder.order_id;
    $("platformReplayLatest").dataset.orderId = latestOrder.order_id || "";
    $("platformReplayLatest").title = latestOrder.order_id ? `${latestOrder.symbol || "--"} / ${latestOrder.state || "--"}` : "暂无可回放订单";
  }
  if (!state.platformReplay || state.platformReplay.order_id !== latestOrder.order_id) {
    renderPlatformReplay(null, latestOrder);
  }

  if ($("platformAuditRows")) {
    $("platformAuditRows").innerHTML = (data.recent_audit || []).slice().reverse().map((row) => `
      <div class="platform-audit-row">
        <span>${escapeHtml(timeText(row.time))}</span>
        <strong>${escapeHtml(row.type || "audit_event")}</strong>
        <span>${escapeHtml(row.symbol || row.strategy_id || "--")}</span>
      <span class="flat" data-raw-status="${escapeHtml(row.status || row.state || "RECORDED")}" title="原始审计状态仅供追溯；不代表交易授权">${escapeHtml(researchStatusShort(row.status || row.state, "审计事件已记录"))}</span>
      </div>
    `).join("") || `<div class="platform-audit-empty">暂无审计事件</div>`;
  }
  renderStrategyCommandStrip();
  return true;
}

function renderPlatformReplay(data, latestOrder = state.platformControl?.latest_order || {}) {
  const target = $("platformReplayResult");
  if (!target) return;
  if (!data) {
    target.innerHTML = latestOrder.order_id
      ? `<div class="platform-replay-empty">最近订单 ${escapeHtml(latestOrder.order_id)} · 点击回放验证信号、风控、行情和成交</div>`
      : `<div class="platform-replay-empty">产生模拟订单后可校验完整事件链</div>`;
    return;
  }
  const checks = Array.isArray(data.checks) ? data.checks : [];
  const summaryPresentation = evidenceResearchStatusPresentation(data.status);
  target.innerHTML = `
    <div class="platform-replay-summary flat evidence-neutral" data-raw-status="${escapeHtml(summaryPresentation.rawStatus)}" title="原始回放状态 ${escapeHtml(summaryPresentation.rawStatus)} · 不代表交易授权">
      <strong>${escapeHtml(summaryPresentation.label)}</strong>
      <span>${escapeHtml(data.order_id || "--")} / hash ${escapeHtml(String(data.replay_hash || "--").slice(0, 12))}</span>
    </div>
    <div class="platform-replay-checks">
      ${checks.map((check) => {
        const presentation = evidenceResearchCellPresentation(check.status, "回放检查待核验");
        return `
        <div class="platform-replay-check flat evidence-neutral" data-raw-status="${escapeHtml(presentation.rawStatus)}" title="原始检查状态 ${escapeHtml(presentation.rawStatus)} · 不代表交易授权">
          <strong>${escapeHtml(check.name || "check")} · ${escapeHtml(presentation.label)}</strong>
          <span>${escapeHtml(check.detail || "--")}</span>
        </div>
      `;
      }).join("") || `<div class="platform-replay-empty">没有可验证的检查项</div>`}
    </div>
  `;
}

async function replayLatestPlatformOrder() {
  const button = $("platformReplayLatest");
  const orderId = button?.dataset.orderId || state.platformControl?.latest_order?.order_id || "";
  if (!orderId) return;
  const original = button.textContent;
  button.disabled = true;
  button.textContent = "校验中...";
  try {
    const data = await api(`/api/replay/order?orderId=${encodeURIComponent(orderId)}`);
    state.platformReplay = data;
    renderPlatformReplay(data);
  } catch (error) {
    state.platformReplay = { order_id: orderId, status: "BLOCK", checks: [{ name: "replay_request", status: "BLOCK", detail: error.message }] };
    renderPlatformReplay(state.platformReplay);
  } finally {
    button.disabled = false;
    button.textContent = original;
  }
}

async function loadPlatformControlCenter() {
  const context = platformControlRequestContext();
  const existing = runtime.platformControlInFlight.get(context.key);
  if (existing) return existing;
  setRuntimeMutationControls(true, "正在确认运行权限，只能预览");
  const task = (async () => {
    try {
      const params = new URLSearchParams({
        price: String(context.price),
        symbol: context.symbol,
        bar: context.bar,
        session: context.session,
      });
      const data = await api(`/api/platform/control-center?${params.toString()}`);
      if (!isCurrentPlatformControlRequest(context)) return null;
      renderPlatformControlCenter(data, context);
      return data;
    } catch (error) {
      if (!isCurrentPlatformControlRequest(context)) return null;
      setRuntimeMutationControls(true, "运行权限状态不可用，只能预览");
      setPlatformBlock("platformRiskCard", "OFFLINE", error.message);
      resetPlatformSmallCapitalPlan(
        "BLOCK",
        "下一条尚缺证据：控制中心证据可用性（当前阻断）· 数量预览已清空",
      );
      throw error;
    }
  })();
  runtime.platformControlInFlight.set(context.key, task);
  try {
    return await task;
  } finally {
    if (runtime.platformControlInFlight.get(context.key) === task) {
      runtime.platformControlInFlight.delete(context.key);
    }
  }
}

async function reviewPlatformEvidence() {
  const button = $("platformValidate");
  if (button) button.textContent = "核对中...";
  try {
    await loadPlatformControlCenter();
    $("platformAuthoritySummary")?.scrollIntoView({ behavior: "smooth", block: "start" });
  } finally {
    if (button) button.textContent = "核对当前证据";
  }
}

async function apiPostStream(path, payload, onEvent, signal) {
  const response = await fetch(path, {
    method: "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json", "X-Hakimi-Write": "1" },
    body: JSON.stringify(payload || {}),
    signal,
  });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  const contentType = String(response.headers.get("content-type") || "").toLowerCase();
  if (!contentType.includes("application/x-ndjson") || !response.body) {
    const data = await response.json();
    if (data.ok === false) throw new Error(data.error || "api error");
    onEvent({ type: "complete", data, fallback: true });
    return data;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let completed = null;
  const consumeLine = (line) => {
    if (!line.trim()) return;
    const event = JSON.parse(line);
    if (event.type === "error") throw new Error(event.error || "AI 讨论流中断");
    if (event.type === "complete") completed = event.data || null;
    onEvent(event);
  };
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    lines.forEach(consumeLine);
    if (done) break;
  }
  consumeLine(buffer);
  return completed;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function candleFromOkx(row) {
  return {
    ts: Number(row[0]),
    open: Number(row[1]),
    high: Number(row[2]),
    low: Number(row[3]),
    close: Number(row[4]),
    volume: Number(row[5] || 0),
  };
}

function candleFromCsv(row) {
  return {
    ts: Number(row.ts_ms),
    open: Number(row.open),
    high: Number(row.high),
    low: Number(row.low),
    close: Number(row.close),
    volume: Number(row.volume || 0),
  };
}

function candleFromApi(row) {
  return {
    ts: Number(row.ts ?? row.ts_ms ?? row.time ?? 0),
    open: Number(row.open ?? row.close ?? 0),
    high: Number(row.high ?? row.close ?? 0),
    low: Number(row.low ?? row.close ?? 0),
    close: Number(row.close ?? 0),
    volume: Number(row.volume ?? row.vol ?? row.volume_quote ?? 0),
  };
}

function stockCandleRows(data) {
  return (data.rows || []).map((row) => ({
    ts: Number(row.ts),
    open: Number(row.open),
    high: Number(row.high),
    low: Number(row.low),
    close: Number(row.close),
    volume: Number(row.volume || 0),
  })).filter((row) => Number.isFinite(row.close) && row.close > 0);
}

function marketSourceLabel(source, originSource = "") {
  return window.HakimiChartQuality.sourceLabel(source, originSource);
}

function isPreviewChartSource(source, warning = "") {
  return window.HakimiChartQuality.isPreviewSource(source, warning);
}

function latestCandleTimeText(rows = [], latestTs = 0) {
  return window.HakimiChartQuality.latestCandleTimeText(rows, latestTs, formatCandleTime);
}

function chartAgeText(ms) {
  return window.HakimiChartQuality.ageText(ms);
}

function chartQualityFromSource({ symbol, bar, rows = [], source = "", warning = "", originSource = "", latestTs = 0, latestAt = "", realtime = null, fallback = false, cached = false, cacheAgeMs = 0, dataAgeMs = null, marketSession = null }) {
  return window.HakimiChartQuality.qualityFromSource({
    symbol,
    bar,
    rows,
    source,
    warning,
    originSource,
    latestTs,
    latestAt,
    realtime,
    fallback,
    cached,
    cacheAgeMs,
    dataAgeMs,
    marketSession,
  }, { barToMs, isStockMarket, formatCandleTime, now: () => Date.now() });
}

function renderChartQuality(quality = state.chartQuality) {
  const strip = $("chartQualityStrip");
  if (!strip || !quality) return;
  strip.className = `chart-quality-strip ${quality.tone || "flat"}`;
  const source = $("chartQualitySource");
  const freshness = $("chartQualityFreshness");
  const mode = $("chartQualityMode");
  const warning = $("chartQualityWarning");
  if (source) source.textContent = quality.sourceText || quality.sourceLabel || "--";
  if (freshness) freshness.textContent = quality.freshnessText || "--";
  if (mode) mode.textContent = quality.mode || "--";
  if (warning) warning.textContent = quality.warningText || "--";
  renderResearchDataQualityCards(researchDataQualitySnapshot());
  maybeAutoRefreshChartStale(quality);
}

function researchDataQualitySnapshot() {
  const quality = state.chartQuality || {};
  const stock = isStockMarket();
  const futuOnline = futuOpenDOnline();
  const cryptoOnline = Boolean(state.desktop.okxOnline) || markets.some((item) => item.type !== "stock" && numericMarketValue(item.price) > 0);
  const stockCount = markets.filter((item) => item.type === "stock").length;
  const cryptoCount = markets.filter((item) => item.type !== "stock").length;
  const sourceText = quality.sourceText || quality.sourceLabel || quality.source || "等待K线";
  const modeText = quality.mode || "加载中";
  const tone = quality.tone || (quality.realtime ? "up" : "flat");
  return {
    status: "LOCAL_SNAPSHOT",
    cards: [
      {
        label: "K线可信度",
        value: modeText,
        detail: `${sourceText}${quality.freshnessText ? ` / ${quality.freshnessText}` : ""}`,
        tone,
      },
      {
        label: "市场覆盖",
        value: `${stockCount}股 / ${cryptoCount}币`,
        detail: state.marketCategory === "all" ? "全市场可见，股票/加密可直接切换" : `当前筛选：${state.marketCategory}`,
        tone: "up",
      },
      {
        label: stock ? "Futu连接" : "OKX行情",
        value: stock ? (futuOnline ? "ONLINE" : "OFFLINE") : (cryptoOnline ? "ONLINE" : "WAIT"),
        detail: stock ? (futuOnline ? "OpenD可用，是否实时以交易时段和报价时间为准" : "Futu离线时使用Yahoo/本地缓存") : "公共行情，无需私钥",
        tone: stock ? (futuOnline ? "up" : "down") : (cryptoOnline ? "up" : "flat"),
      },
      {
        label: "实盘边界",
        value: "BLOCKED",
        detail: "仅观察 / 仅研究 / 仅模拟盘验证",
        tone: "down",
      },
    ],
  };
}

function stockCandleStatus(data, interval) {
  const sourceLabel = marketSourceLabel(data.source, data.origin_source);
  const cacheText = data.cached ? ` / 缓存${data.cache_age_ms ? ` ${chartAgeText(data.cache_age_ms)}` : ""}` : "";
  const latestTs = Number(data.latest_ts) || Math.max(0, ...(data.rows || []).map((row) => Number(row.ts || row.ts_ms || 0)));
  const recentDaily = isRecentStockDailyData({ bar: data.interval || interval, latestTs, ageMs: data.data_age_ms || 0 });
  const dataAgeText = data.data_age_ms ? (recentDaily ? " / 上一交易日" : ` / 数据约${chartAgeText(data.data_age_ms)}前`) : "";
  const warningText = data.warning && !recentDaily ? (data.source === "offline-seed" ? " / 非真实行情" : data.source === "stock_sqlite_cache" ? " / 旧缓存" : " / 兜底") : "";
  const latestText = latestCandleTimeText(data.rows || [], data.latest_ts);
  const freshText = latestText ? ` / 最新 ${latestText}` : "";
  const realtimeText = data.realtime === false && data.source !== "offline-seed" ? " / 延迟" : "";
  const chartKind = isStockIntradayLineChart() ? "股票分时" : "股票K线";
  return `${chartKind} ${data.interval || interval} / ${stockChartScopeLabel(data.interval || interval, data.session || state.stockSession)} / ${sourceLabel}${cacheText}${freshText}${dataAgeText}${warningText}${realtimeText}`;
}

function marketSnapshotSymbol(symbol = state.symbol) {
  return isStockMarket(symbol) ? symbol : okxInstId(symbol);
}

function marketSnapshotBar(symbol = state.symbol, bar = state.bar) {
  return isStockMarket(symbol) ? stockIntervalForBar(bar) : bar;
}

function marketSnapshotLimit(symbol = state.symbol, bar = state.bar) {
  if (!isStockMarket(symbol)) return 300;
  const interval = stockIntervalForBar(bar);
  if (interval === "1m") return 720;
  if (interval === "1d") return 520;
  return 420;
}

function marketSnapshotPath({ symbol, bar, limit, session = "all", fast = true, force = false, emit = false, consumer = "chart" }) {
  const params = new URLSearchParams({
    symbol: marketSnapshotSymbol(symbol),
    bar: marketSnapshotBar(symbol, bar),
    limit: String(limit || marketSnapshotLimit(symbol, bar)),
    session,
    fast: fast ? "true" : "false",
    force: force ? "true" : "false",
    emit: emit ? "true" : "false",
    consumer,
  });
  return `/api/market/snapshot?${params.toString()}`;
}

function stockContinuityViewMeta(snapshot) {
  if (snapshot?.asset_type !== "stock") return { active: false };
  const candleQuality = snapshot?.candles?.candle_quality || {};
  const quote = snapshot?.quote || {};
  const quoteQuality = quote.quote_quality || {};
  const latestBreak = candleQuality.latest_break || {};
  const breakIndex = Number(candleQuality.segment_start);
  const totalRows = Number(candleQuality.total_rows);
  const rawPreviousClose = Number(latestBreak.previous_close);
  const quotePreviousClose = Number(quote.prevClose);
  const factor = quotePreviousClose / rawPreviousClose;
  const active = Boolean(
    candleQuality.has_break
    && candleQuality.segment_rows === 1
    && breakIndex === totalRows - 1
    && quoteQuality.status === "READY"
    && !quoteQuality.quarantined
    && Number.isFinite(factor)
    && factor >= 0.2
    && factor <= 5
    && Math.abs(factor - 1) >= 0.1
  );
  return { active, breakIndex, factor };
}

function marketSnapshotRows(snapshot) {
  const rows = (snapshot?.candles?.rows || [])
    .map(candleFromApi)
    .filter((row) => Number.isFinite(row.close) && row.close > 0);
  const continuity = stockContinuityViewMeta(snapshot);
  if (!continuity.active || continuity.breakIndex >= rows.length) return rows;
  return rows.map((row, index) => {
    if (index >= continuity.breakIndex) return row;
    return {
      ...row,
      open: row.open * continuity.factor,
      high: row.high * continuity.factor,
      low: row.low * continuity.factor,
      close: row.close * continuity.factor,
      displayAdjusted: true,
    };
  });
}

function marketSnapshotWarning(snapshot) {
  const candles = snapshot?.candles || {};
  const quality = snapshot?.data_quality || {};
  const candleQuality = candles.candle_quality || {};
  const warnings = Array.isArray(quality.warnings) ? quality.warnings : [];
  const continuityWarning = stockContinuityViewMeta(snapshot).active ? "图表按实时报价昨收生成临时连续视图，原始日线仍待核" : "";
  const parts = [candles.warning, candleQuality.warning, ...warnings, continuityWarning]
    .flatMap((warning) => String(warning || "").split(" / "))
    .map((warning) => warning.trim())
    .filter(Boolean);
  return [...new Set(parts)].join(" / ");
}

function marketSnapshotStatus(snapshot, rows, fallbackBar = state.bar) {
  const candles = snapshot?.candles || {};
  const source = snapshot?.source || {};
  const quality = snapshot?.data_quality || {};
  const assetType = snapshot?.asset_type || (isStockMarket(snapshot?.symbol) ? "stock" : "crypto");
  const sourceName = candles.source || source.primary || "market_snapshot";
  const sourceText = marketSourceLabel(sourceName, source.origin || "");
  const barText = candles.bar || snapshot?.bar || fallbackBar;
  const latestText = candles.latest_at || latestCandleTimeText(rows, candles.latest_ts);
  const latestPart = latestText ? ` / 最新 ${latestText}` : "";
  const ageMs = candles.data_age_ms ?? source.data_age_ms;
  const latestTs = Number(candles.latest_ts) || Math.max(0, ...rows.map((row) => Number(row.ts || row.ts_ms || 0)));
  const recentDaily = assetType === "stock" && isRecentStockDailyData({ bar: barText, latestTs, ageMs: ageMs || 0 });
  const agePart = ageMs ? (recentDaily ? " / 上一交易日" : ` / 数据约${chartAgeText(ageMs)}前`) : "";
  const statusText = quality.status && quality.status !== "READY" && !(recentDaily && String(quality.status).toUpperCase() === "STALE") ? ` / ${quality.status}` : "";
  const fallbackText = quality.fallback || candles.fallback ? " / 兜底" : "";
  const continuityText = stockContinuityViewMeta(snapshot).active ? " / 临时连续视图待核" : "";
  if (assetType === "stock") {
    const sessionText = stockChartScopeLabel(barText, snapshot?.session || state.stockSession);
    const marketSession = snapshot?.market_session || {};
    const marketPhaseText = marketSession.status_label || marketSession.phase_label || "";
    const relationText = marketSession.session_relation === "LAST_SESSION" ? "上一交易时段" : marketPhaseText;
    const chartKind = isStockIntradayLineChart() ? "股票分时" : "股票K线";
    return `${chartKind} ${barText} / ${sessionText}${relationText ? ` / ${relationText}` : ""} / ${sourceText}${latestPart}${agePart}${statusText}${fallbackText}${continuityText}`;
  }
  return `${sourceText} K线${barText ? ` / ${barText}` : ""}${latestPart}${agePart}${statusText}${fallbackText}`;
}

function tickerFromMarketSnapshot(snapshot) {
  const quote = snapshot?.quote || {};
  const source = snapshot?.source || {};
  return {
    ...quote,
    symbol: snapshot?.symbol || state.symbol,
    instId: snapshot?.symbol || state.symbol,
    source: source.quote || source.primary || quote.source || "market_snapshot",
    origin_source: source.origin || quote.origin_source || "",
    ts: quote.ts || snapshot?.updated_at || Date.now(),
    market_session: snapshot?.market_session || quote.market_session || null,
  };
}

function snapshotConsumerLabel(value = "") {
  return ({
    chart: "K线",
    chart_refresh: "K线刷新",
    prewarm: "预热",
    trend_cockpit: "走势驾驶舱",
    research: "研究面板",
    stock_research: "股票研究",
    ai: "AI分析",
    api: "行情接口",
  })[String(value || "").toLowerCase()] || String(value || "行情模块");
}

function applySharedSnapshotContext(context = {}) {
  if (!context?.snapshot_id || (context.symbol && context.symbol !== state.symbol)) return;
  const consumers = [...new Set([
    ...((state.marketSnapshotContext?.symbol === state.symbol && state.marketSnapshotContext?.consumers) || []),
    ...(context.consumers || []),
  ])];
  state.marketSnapshotContext = { ...state.marketSnapshotContext, ...context, consumers };
  if ($("stockSourceControlRows")) renderStockSourceControl(state.stockSourceControl || cryptoSourceControl(state.symbol));
}

function applyMarketSnapshotToChart(snapshot, { requestSymbol, requestBar, cacheKey }) {
  const rows = marketSnapshotRows(snapshot);
  if (!rows.length) throw new Error(snapshot?.source?.degradation_reason || snapshot?.candles?.warning || `no candles for ${requestSymbol}`);
  const candles = snapshot.candles || {};
  const source = snapshot.source || {};
  const quality = snapshot.data_quality || {};
  if (requestSymbol === state.symbol && snapshot.market_session) state.marketSession = snapshot.market_session;
  applySharedSnapshotContext(snapshot.context || {});
  const sourceName = candles.source || source.primary || "market_snapshot";
  const applied = applyChartRows({
    symbol: requestSymbol,
    bar: candles.bar || snapshot.bar || requestBar,
    rows,
    status: marketSnapshotStatus(snapshot, rows, requestBar),
    source: sourceName,
    cacheKey,
    warning: marketSnapshotWarning(snapshot),
    originSource: source.origin || "",
    latestTs: candles.latest_ts || 0,
    latestAt: candles.latest_at || "",
    realtime: quality.realtime ?? source.realtime ?? candles.realtime ?? null,
    fallback: Boolean(quality.fallback || candles.fallback),
    cached: Boolean(snapshot.cached || source.cached || candles.cached),
    cacheAgeMs: candles.cache_age_ms || snapshot.snapshot_cache_age_ms || 0,
    dataAgeMs: candles.data_age_ms ?? source.data_age_ms ?? null,
    candleQuality: candles.candle_quality || null,
    marketSession: snapshot.market_session || null,
  });
  if (applied) {
    updateTicker(tickerFromMarketSnapshot(snapshot), String(source.quote || source.primary || "SNAPSHOT").toUpperCase());
  }
  return applied;
}

function storeMarketSnapshotCacheOnly(snapshot, { requestSymbol, requestBar, requestSession, cacheKey }) {
  const rows = marketSnapshotRows(snapshot);
  if (!rows.length) return false;
  const candles = snapshot.candles || {};
  const source = snapshot.source || {};
  const quality = snapshot.data_quality || {};
  const sourceName = candles.source || source.primary || "market_snapshot";
  const warning = marketSnapshotWarning(snapshot);
  if (isPreviewChartSource(sourceName, warning)) return false;
  const normalizedRows = normalizeChartRows(rows);
  if (!normalizedRows.length) return false;
  const qualitySnapshot = chartQualityFromSource({
    symbol: requestSymbol,
    bar: candles.bar || snapshot.bar || requestBar,
    rows: normalizedRows,
    source: sourceName,
    warning,
    originSource: source.origin || "",
    latestTs: candles.latest_ts || 0,
    latestAt: candles.latest_at || "",
    realtime: quality.realtime ?? source.realtime ?? candles.realtime ?? null,
    fallback: Boolean(quality.fallback || candles.fallback),
    cached: Boolean(snapshot.cached || source.cached || candles.cached),
    cacheAgeMs: candles.cache_age_ms || snapshot.snapshot_cache_age_ms || 0,
    dataAgeMs: candles.data_age_ms ?? source.data_age_ms ?? null,
    candleQuality: candles.candle_quality || null,
    marketSession: snapshot.market_session || null,
  });
  storeChartCache(cacheKey || chartCacheKey(requestSymbol, requestBar, requestSession), normalizedRows, {
    source: sourceName,
    bar: candles.bar || snapshot.bar || requestBar,
    warning,
    originSource: source.origin || "",
    latestTs: qualitySnapshot.latestTs,
    latestAt: qualitySnapshot.latestAt,
    realtime: qualitySnapshot.realtime,
    fallback: qualitySnapshot.fallback,
    dataAgeMs: qualitySnapshot.dataAgeMs,
    candleQuality: candles.candle_quality || null,
    marketSession: snapshot.market_session || null,
  });
  return true;
}

function prewarmChartSymbols(limit = 14) {
  const seen = new Set();
  return [state.symbol, ...WATCHLIST_PRIORITY]
    .filter((symbol) => {
      if (!symbol || seen.has(symbol)) return false;
      seen.add(symbol);
      return markets.some((item) => item.symbol === symbol || item.instId === symbol);
    })
    .slice(0, limit);
}

async function prewarmChartCache(symbol, bar = "1Dutc") {
  const requestSymbol = symbol;
  const requestBar = bar;
  const requestSession = isStockMarket(requestSymbol) ? "regular" : "all";
  const cacheKey = chartCacheKey(requestSymbol, requestBar, requestSession);
  const cached = state.chartCache[cacheKey];
  if (cached?.rows?.length && !isPreviewChartSource(cached.meta?.source, cached.meta?.warning)) return true;
  if (runtime.chartPrewarmDone.has(cacheKey) || runtime.chartPrewarmInFlight.has(cacheKey)) return false;
  runtime.chartPrewarmInFlight.add(cacheKey);
  try {
    const snapshot = await api(marketSnapshotPath({
      symbol: requestSymbol,
      bar: requestBar,
      limit: marketSnapshotLimit(requestSymbol, requestBar),
      session: requestSession,
      fast: true,
      force: false,
      emit: false,
      consumer: "prewarm",
    }));
    const stored = storeMarketSnapshotCacheOnly(snapshot, {
      requestSymbol,
      requestBar,
      requestSession,
      cacheKey,
    });
    if (stored) runtime.chartPrewarmDone.add(cacheKey);
    return stored;
  } catch (error) {
    return false;
  } finally {
    runtime.chartPrewarmInFlight.delete(cacheKey);
  }
}

function prewarmPriorityChartCache() {
  const symbols = prewarmChartSymbols(14);
  symbols.forEach((symbol, index) => {
    setTimeout(() => {
      prewarmChartCache(symbol, "1Dutc").catch(() => {});
    }, 450 + index * 650);
  });
}

async function startStockHistoryPrewarm(force = false) {
  const now = Date.now();
  if (!force && now - Number(runtime.stockHistoryPrewarmAt || 0) < 30 * 60 * 1000) return null;
  runtime.stockHistoryPrewarmAt = now;
  try {
    return await api(`/api/stocks/history-prewarm?start=true&symbol=${encodeURIComponent(isStockMarket() ? state.symbol : "AAPL")}&force=${force ? "true" : "false"}`);
  } catch (error) {
    if (force) runtime.stockHistoryPrewarmAt = 0;
    return null;
  }
}

function marketSnapshotNeedsRefresh(snapshot) {
  const quality = snapshot?.data_quality || {};
  const candles = snapshot?.candles || {};
  const warnings = Array.isArray(quality.warnings) ? quality.warnings : [];
  return quality.status !== "READY"
    || Boolean(quality.fallback)
    || Boolean(candles.fallback)
    || Boolean(candles.warning)
    || warnings.length > 0
    || candles.source === "quick_preview_seed";
}

function chartCacheKey(symbol, bar, session = state.stockSession) {
  return `${symbol}|${bar}|${isStockMarket(symbol) ? session : "all"}`;
}

function storeChartCache(key, rows, meta = {}) {
  if (!rows?.length) return;
  if (isPreviewChartSource(meta.source, meta.warning)) return;
  state.chartCache[key] = {
    rows: rows.slice(-500),
    meta: { ...meta, cached_at: Date.now() },
  };
}

function cachedChartStatus(cached, bar) {
  const source = cached?.meta?.source || "memory_cache";
  const warning = cached?.meta?.warning || "";
  const sourceLabel = marketSourceLabel(source, cached?.meta?.originSource || "");
  const latestTs = Number(cached?.meta?.latestTs) || Math.max(0, ...(cached?.rows || []).map((row) => Number(row.ts || row.ts_ms || 0)));
  const latestText = cached?.meta?.latestAt || latestCandleTimeText(cached?.rows || [], latestTs);
  const dataAgeMs = Number(cached?.meta?.dataAgeMs) || (latestTs ? Math.max(0, Date.now() - latestTs) : 0);
  const recentDaily = isStockMarket(state.symbol) && isRecentStockDailyData({ bar: cached?.meta?.bar || bar, latestTs, ageMs: dataAgeMs });
  const freshnessText = latestText ? ` / 最新 ${latestText}${recentDaily ? " / 上一交易日" : ""}` : "";
  if (isStockMarket(state.symbol)) {
    const warningText = warning ? (source === "offline-seed" ? " / 非真实行情" : " / 兜底") : "";
    const chartKind = isStockIntradayLineChart() ? "股票分时" : "股票K线";
    return `${chartKind} ${cached?.meta?.bar || bar} / ${stockChartScopeLabel(cached?.meta?.bar || bar)} / ${sourceLabel} / 秒开缓存${freshnessText}${warningText}`;
  }
  if (source === "offline-seed") {
    return `股票K线 ${cached?.meta?.bar || bar} / ${stockChartScopeLabel(cached?.meta?.bar || bar)} / 离线种子 / 秒开缓存${freshnessText}${warning ? " / 非真实行情" : ""}`;
  }
  return `${sourceLabel} K线 / 秒开缓存${warning ? " / 兜底" : ""}`;
}

function normalizeChartRows(rows = []) {
  return rows.map((row, index) => {
    const close = Number(row.close);
    if (!Number.isFinite(close) || close <= 0) return null;
    const open = Number.isFinite(Number(row.open)) && Number(row.open) > 0 ? Number(row.open) : close;
    const rawHigh = Number(row.high);
    const rawLow = Number(row.low);
    const high = Number.isFinite(rawHigh) && rawHigh > 0 ? Math.max(rawHigh, open, close) : Math.max(open, close);
    const low = Number.isFinite(rawLow) && rawLow > 0 ? Math.min(rawLow, open, close) : Math.min(open, close);
    const ts = Number.isFinite(Number(row.ts)) && Number(row.ts) > 0 ? Number(row.ts) : Date.now() - (rows.length - index) * barToMs(state.bar);
    return {
      ts,
      open,
      high,
      low,
      close,
      volume: Number.isFinite(Number(row.volume)) && Number(row.volume) >= 0 ? Number(row.volume) : 0,
    };
  }).filter(Boolean);
}

function stockSessionAllowsPriceOverlay(symbol, marketSession = state.marketSession) {
  if (!isStockMarket(symbol) || !marketSession?.active_session) return true;
  const activeSession = String(marketSession.active_session || "regular");
  const selectedSession = String(state.stockSession || "regular");
  return selectedSession === "all" || selectedSession === activeSession;
}

function applyChartRows({ symbol, bar, rows, status, source, cacheKey, warning = "", originSource = "", latestTs = 0, latestAt = "", realtime = null, fallback = false, cached = false, cacheAgeMs = 0, dataAgeMs = null, candleQuality = null, marketSession = null }) {
  const cleanRows = normalizeChartRows(rows);
  if (!cleanRows.length) return false;
  if (symbol === state.symbol && marketSession) state.marketSession = marketSession;
  const lastClose = Number(cleanRows[cleanRows.length - 1]?.close);
  let marketQuoteApplied = false;
  if (symbol === state.symbol && Number.isFinite(lastClose) && lastClose > 0) {
    // A stock list price can still be an offline preview while real candles are loading.
    // Only a separately validated quote may touch stock candles in syncLiveCandle().
    const marketQuote = !isStockMarket(symbol) && stockSessionAllowsPriceOverlay(symbol, marketSession)
      ? numericMarketValue(currentMarket(symbol).price)
      : 0;
    const quoteDiff = marketQuote > 0 ? Math.abs(marketQuote - lastClose) / Math.max(lastClose, 1e-9) : 0;
    if (marketQuote > 0 && quoteDiff > 0.001) {
      const live = cleanRows[cleanRows.length - 1];
      live.close = marketQuote;
      live.high = Math.max(Number(live.high || 0), marketQuote);
      live.low = Math.min(Number(live.low || marketQuote), marketQuote);
      state.lastPrice = marketQuote;
      marketQuoteApplied = true;
    } else {
      state.lastPrice = lastClose;
      if (!marketQuote) {
        updateMarketFromTicker({ symbol, instId: symbol, last: lastClose, source: source || "chart", ts: latestTs || Date.now() });
      }
    }
  }
  state.candles = cleanRows;
  state.chartDataSymbol = symbol;
  state.chartCandleQuality = symbol === state.symbol && isStockMarket(symbol) ? candleQuality : null;
  if (symbol === state.symbol
    && isStockMarket(symbol)
    && isStockMinuteBar(bar)
    && state.chartMode === "line"
    && !runtime.chartUserZoomed) {
    const targetVisible = Math.min(stockVisibleBarsForBar(bar), cleanRows.length || stockVisibleBarsForBar(bar));
    if (state.chartView.visible < targetVisible) state.chartView.visible = targetVisible;
  }
  state.chartView.offset = 0;
  const quality = chartQualityFromSource({
    symbol,
    bar,
    rows: cleanRows,
    source,
    warning,
    originSource,
    latestTs,
    latestAt,
    realtime,
    fallback,
    cached,
    cacheAgeMs,
    dataAgeMs,
    marketSession,
  });
  state.chartQuality = quality;
  state.chartQualityBySymbol[symbol] = quality;
  renderChartQuality(quality);
  const statusText = status || `${source || "market"} candles${bar ? ` / ${bar}` : ""}${warning ? " / fallback" : ""}`;
  $("chartStatus").textContent = marketQuoteApplied && !statusText.includes("已叠加报价")
    ? `${statusText} / 已叠加报价`
    : statusText;
  if (cacheKey && !isPreviewChartSource(source, warning)) {
    storeChartCache(cacheKey, cleanRows, {
      source,
      bar,
      warning,
      originSource,
      latestTs: quality.latestTs,
      latestAt: quality.latestAt,
      realtime: quality.realtime,
      fallback: quality.fallback,
      dataAgeMs: quality.dataAgeMs,
      candleQuality,
      marketSession,
    });
  }
  loadDrawings();
  drawChart();
  if (symbol === state.symbol) {
    syncActiveSymbolHeader(marketQuoteApplied ? "报价已同步到K线" : "");
    scheduleMarketRender(true);
  }
  renderMarketAiLocal();
  renderLiveSourceBar();
  renderMarketWorkflowStrip();
  return true;
}

function previewPriceForSymbol(symbol) {
  const market = currentMarket(symbol);
  const parsed = Number(String(market.price || "").replaceAll(",", ""));
  if (Number.isFinite(parsed) && parsed > 0) return parsed;
  const seeds = {
    "BTC-USDT": 65000,
    "ETH-USDT": 1733,
    "DOGE-USDT": 0.076,
    "BTC-USDT-SWAP": 65000,
    "ETH-USDT-SWAP": 1733,
    "DOGE-USDT-SWAP": 0.076,
    AAPL: 195,
    MSFT: 485,
    NVDA: 180,
    TSLA: 320,
    MSTR: 390,
    SPY: 640,
    QQQ: 560,
  };
  return seeds[symbol] || state.lastPrice || state.candles[state.candles.length - 1]?.close || 1;
}

function previewCandlesFromBase(basePrice, bar, count = 140) {
  const base = Number(basePrice) > 0 ? Number(basePrice) : 1;
  const interval = barToMs(bar);
  const now = Date.now();
  const rows = Array.from({ length: count }, (_, index) => {
    const phase = index / Math.max(count - 1, 1);
    const wave = Math.sin(phase * Math.PI * 6) * 0.006 + Math.cos(phase * Math.PI * 2) * 0.004;
    const prevPhase = Math.max(index - 1, 0) / Math.max(count - 1, 1);
    const prevWave = Math.sin(prevPhase * Math.PI * 6) * 0.006 + Math.cos(prevPhase * Math.PI * 2) * 0.004;
    const drift = (phase - 0.5) * 0.014;
    const prevDrift = (prevPhase - 0.5) * 0.014;
    const close = base * (1 + wave + drift);
    const open = base * (1 + prevWave + prevDrift);
    return {
      ts: now - (count - index) * interval,
      open,
      high: Math.max(open, close) * 1.003,
      low: Math.min(open, close) * 0.997,
      close,
      volume: 1000 + Math.abs(Math.sin(phase * Math.PI * 8)) * 180,
    };
  });
  const lastClose = Number(rows[rows.length - 1]?.close);
  if (Number.isFinite(lastClose) && lastClose > 0) {
    const factor = base / lastClose;
    for (const row of rows) {
      row.open *= factor;
      row.high *= factor;
      row.low *= factor;
      row.close *= factor;
    }
    const last = rows[rows.length - 1];
    last.close = base;
    last.high = Math.max(last.high, base);
    last.low = Math.min(last.low, base);
  }
  return rows;
}

function previewCandlesForSymbol(symbol, bar, count = 140) {
  return previewCandlesFromBase(previewPriceForSymbol(symbol), bar, count);
}

function renderInstantPreviewCandles(symbol, bar) {
  const cacheKey = chartCacheKey(symbol, bar, state.stockSession);
  const cached = state.chartCache[cacheKey];
  if (cached?.rows?.length) {
    applyChartRows({
      symbol,
      bar: cached.meta?.bar || bar,
      rows: cached.rows,
      source: cached.meta?.source || "memory_cache",
      status: cachedChartStatus(cached, bar),
      cacheKey,
      warning: cached.meta?.warning || "",
      originSource: cached.meta?.originSource || "",
      latestTs: cached.meta?.latestTs || 0,
      latestAt: cached.meta?.latestAt || "",
      realtime: cached.meta?.realtime ?? null,
      fallback: Boolean(cached.meta?.fallback),
      cached: true,
      cacheAgeMs: Date.now() - Number(cached.meta?.cached_at || Date.now()),
      dataAgeMs: null,
      candleQuality: cached.meta?.candleQuality || null,
      marketSession: cached.meta?.marketSession || null,
    });
    return;
  }
  applyChartRows({
    symbol,
    bar,
    rows: previewCandlesForSymbol(symbol, bar),
    source: "client_quick_preview",
    status: "快速预览K线 / 等待真实数据",
    cacheKey: "",
    warning: "仅用于切换时避免空白，不用于分析。",
  });
}

function chartIsVisibleForSymbol(symbol) {
  const canvas = $("priceChart");
  const count = Number(canvas?.dataset?.candleCount || 0);
  return state.chartDataSymbol === symbol && state.candles?.length > 0 && count > 0;
}

function ensureActiveChartPreview(symbol = state.symbol, bar = state.bar) {
  if (state.symbol !== symbol || chartIsVisibleForSymbol(symbol)) return;
  renderInstantPreviewCandles(symbol, bar);
}

function stockQuotePreviewStatus(reason = "等待真实K线") {
  return `股票报价预览 / ${stockSessionLabel()} / ${reason}`;
}

function rebuildStockQuotePreview(price, reason = "报价与兜底K线偏离") {
  const parsed = Number(price);
  if (!isStockMarket() || !Number.isFinite(parsed) || parsed <= 0) return false;
  const count = clampNumber(state.candles.length || state.chartView.visible || 140, 80, 180);
  return applyChartRows({
    symbol: state.symbol,
    bar: state.bar,
    rows: previewCandlesFromBase(parsed, state.bar, count),
    source: "client_quote_preview",
    status: stockQuotePreviewStatus(reason),
    cacheKey: "",
    warning: "报价驱动预览，不用于最终行情判断。",
    realtime: false,
    fallback: true,
  });
}

function stockLiveCandleTs() {
  const interval = barToMs(state.bar);
  if (state.bar === "1Dutc") {
    const date = new Date();
    return Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate());
  }
  return Math.floor(Date.now() / interval) * interval;
}

function stockMarketClock(symbol = state.symbol) {
  const market = String(currentMarket(symbol).market || currentMarket(symbol).exchange || "US").toUpperCase();
  const timeZone = market === "HK" ? "Asia/Hong_Kong" : "America/New_York";
  try {
    const parts = new Intl.DateTimeFormat("en-US", {
      timeZone,
      weekday: "short",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).formatToParts(new Date());
    const part = (type) => parts.find((item) => item.type === type)?.value || "";
    const weekday = part("weekday");
    const hour = Number(part("hour"));
    const minute = Number(part("minute"));
    const total = hour * 60 + minute;
    const weekdayOpen = !["Sat", "Sun"].includes(weekday);
    if (!weekdayOpen || !Number.isFinite(total)) return { open: false, regular: false, extended: false, timeZone };
    if (market === "HK") {
      const regular = (total >= 9 * 60 + 30 && total < 12 * 60) || (total >= 13 * 60 && total < 16 * 60);
      return { open: regular || (total >= 9 * 60 && total < 18 * 60), regular, extended: total >= 9 * 60 && total < 18 * 60, timeZone };
    }
    const regular = total >= 9 * 60 + 30 && total < 16 * 60;
    return { open: total >= 4 * 60 && total < 20 * 60, regular, extended: total >= 4 * 60 && total < 20 * 60, timeZone };
  } catch (error) {
    return { open: false, regular: false, extended: false, timeZone };
  }
}

function shouldAppendStockQuotePreview(status = "", quality = state.chartQuality) {
  if (!isStockMarket()) return false;
  const marketOpen = typeof state.marketSession?.is_open === "boolean"
    ? state.marketSession.is_open
    : stockMarketClock().open;
  if (!marketOpen) return false;
  const source = String(quality?.source || "").toLowerCase();
  const previewLike = quality?.preview
    || quality?.fallback
    || status.includes("快速预览")
    || status.includes("报价预览")
    || status.includes("离线种子")
    || status.includes("兜底")
    || status.includes("旧缓存");
  if (previewLike) return true;
  if (quality?.realtime || source === "futu") return true;
  return stockMarketClock().open;
}

function barToMs(bar) {
  const map = {
    "1m": 60_000,
    "5m": 5 * 60_000,
    "15m": 15 * 60_000,
    "30m": 30 * 60_000,
    "1H": 60 * 60_000,
    "4H": 4 * 60 * 60_000,
    "1Dutc": 24 * 60 * 60_000,
  };
  return map[bar] || 60_000;
}

function stockQuoteOverlayDecision(price, candleClose, quoteData = {}) {
  const guard = window.HakimiStockQuoteGuard;
  if (!guard || typeof guard.evaluateStockQuoteOverlay !== "function") {
    return { allowed: false, reason: "guard_unavailable" };
  }
  return guard.evaluateStockQuoteOverlay({
    price,
    candleClose,
    source: quoteData.source || quoteData.origin_source || quoteData.originSource,
    quoteQuality: quoteData.quote_quality || quoteData.quoteQuality,
    changeBasis: quoteData.change_basis || quoteData.changeBasis,
    previousClose: quoteData.prevClose || quoteData.previousClose,
    changePct: quoteData.change24h_pct ?? quoteData.changePct,
  });
}

function syncLiveCandle(price, quoteData = {}) {
  const parsed = Number(price);
  if (!Number.isFinite(parsed) || !state.candles.length) return;
  if (state.chartDataSymbol && state.chartDataSymbol !== state.symbol) return;
  if (isStockMarket() && state.stockSession !== "all" && state.stockSession !== String(state.marketSession?.active_session || "regular")) return;
  if (isStockMarket() && !stockSessionAllowsPriceOverlay(state.symbol, state.marketSession)) return;
  const last = state.candles[state.candles.length - 1];
  const lastClose = Number(last.close);
  const status = $("chartStatus")?.textContent || "";
  const quality = state.chartQuality || {};
  const diffRatio = Number.isFinite(lastClose) && lastClose > 0 ? Math.abs(parsed - lastClose) / lastClose : 0;
  if (isStockMarket()) {
    const decision = stockQuoteOverlayDecision(parsed, lastClose, quoteData);
    if (!decision.allowed) {
      const reportableMismatch = !["untrusted_source", "quote_not_ready", "guard_unavailable"].includes(decision.reason);
      if (reportableMismatch && diffRatio > 0.08 && !status.includes("报价证据异常")) {
        $("chartStatus").textContent = `${status} / 报价证据异常，未叠加到K线`;
      }
      return;
    }
    if (status.includes(" / 报价证据异常，未叠加到K线")) {
      $("chartStatus").textContent = status.replaceAll(" / 报价证据异常，未叠加到K线", "");
    }
  }
  if (!isStockMarket() && status.includes("快速预览") && Number.isFinite(lastClose) && lastClose > 0 && diffRatio > 0.08) {
    state.candles = previewCandlesFromBase(parsed, state.bar, clampNumber(state.candles.length || 140, 80, 180));
    state.chartDataSymbol = state.symbol;
    drawChart();
    renderMarketAiLocal();
    return;
  }
  const interval = barToMs(state.bar);
  if (Date.now() - last.ts > interval * 2.2) {
    if (!isStockMarket()) return;
    if (!shouldAppendStockQuotePreview(status, quality)) {
      return;
    }
    const nextTs = Math.max(stockLiveCandleTs(), Number(last.ts || 0) + interval);
    state.candles.push({
      ts: nextTs,
      open: Number.isFinite(lastClose) && lastClose > 0 ? lastClose : parsed,
      high: parsed,
      low: parsed,
      close: parsed,
      volume: 0,
    });
    state.candles = state.candles.slice(-500);
    state.chartDataSymbol = state.symbol;
    $("chartStatus").textContent = stockQuotePreviewStatus("最新报价已补到图上，真实K线后台刷新");
    state.chartQuality = chartQualityFromSource({
      symbol: state.symbol,
      bar: state.bar,
      rows: state.candles,
      source: "client_quote_preview",
      warning: "报价驱动预览，不用于最终行情判断。",
      realtime: false,
      fallback: true,
    });
    state.chartQualityBySymbol[state.symbol] = state.chartQuality;
    renderChartQuality(state.chartQuality);
    drawChart();
    renderMarketAiLocal();
    renderLiveSourceBar();
    renderMarketWorkflowStrip();
    return;
  }
  last.close = parsed;
  last.high = Math.max(Number(last.high), parsed);
  last.low = Math.min(Number(last.low), parsed);
  drawChart();
}

function maybeRefreshActiveStockCandles(reason = "quote", manual = false) {
  if (!isStockMarket()) return;
  const quality = state.chartQuality || {};
  const status = $("chartStatus")?.textContent || "";
  const needsRefresh = quality.preview
    || quality.fallback
    || status.includes("报价预览")
    || status.includes("快速预览")
    || status.includes("旧缓存")
    || status.includes("兜底");
  if (!needsRefresh) return;
  const requestVersion = runtime.symbolVersion;
  const requestSymbol = state.symbol;
  const requestBar = state.bar;
  const requestSession = state.stockSession;
  const cacheKey = chartCacheKey(requestSymbol, requestBar, requestSession);
  refreshSnapshotCandlesInBackground({
    requestVersion,
    requestSymbol,
    requestBar,
    requestSession,
    limit: marketSnapshotLimit(requestSymbol, requestBar),
    cacheKey,
    manual,
    reason,
  }).catch(() => {
    if (requestVersion === runtime.symbolVersion && requestSymbol === state.symbol) {
      const current = $("chartStatus")?.textContent || "";
      if (current.includes("预览")) $("chartStatus").textContent = `${current} / 真实K线稍后重试`;
    }
  });
}

function movingAverage(candles, window) {
  return candles.map((_, index) => {
    if (index + 1 < window) return null;
    const slice = candles.slice(index + 1 - window, index + 1);
    return slice.reduce((sum, candle) => sum + candle.close, 0) / window;
  });
}

function bollingerBands(candles, window = 20, mult = 2) {
  return candles.map((_, index) => {
    if (index + 1 < window) return null;
    const slice = candles.slice(index + 1 - window, index + 1).map((candle) => candle.close);
    const mid = slice.reduce((sum, value) => sum + value, 0) / window;
    const variance = slice.reduce((sum, value) => sum + (value - mid) ** 2, 0) / window;
    const band = Math.sqrt(variance) * mult;
    return { upper: mid + band, mid, lower: mid - band };
  });
}

async function loadCandles(requestVersion = runtime.symbolVersion) {
  runtime.chartRequestAbortController?.abort();
  const controller = new AbortController();
  runtime.chartRequestAbortController = controller;
  const request = window.HakimiChartController.createCandleRequest({
    state,
    runtime,
    requestVersion,
    chartCacheKey,
  });
  const { requestSymbol, requestBar, cacheKey } = request;
  const requestSession = isStockMarket(requestSymbol) ? request.requestSession : "all";
  request.requestSession = requestSession;
  const refreshKey = window.HakimiChartController.inFlightKey(request);
  runtime.chartRequestKey = refreshKey;
  let cached = state.chartCache[cacheKey];
  if (cached?.rows?.length && !window.HakimiChartController.cacheIsUsable(cached, isPreviewChartSource)) {
    delete state.chartCache[cacheKey];
    cached = null;
  }
  const activeRequest = () => window.HakimiChartController.isActiveRequest({
    state,
    runtime,
    request,
    isStockMarket,
  });

  if (cached?.rows?.length) {
    applyChartRows({
      symbol: requestSymbol,
      bar: cached.meta?.bar || requestBar,
      rows: cached.rows,
      source: cached.meta?.source || "memory_cache",
      status: cachedChartStatus(cached, requestBar),
      cacheKey,
      warning: cached.meta?.warning || "",
      originSource: cached.meta?.originSource || "",
      latestTs: cached.meta?.latestTs || 0,
      latestAt: cached.meta?.latestAt || "",
      realtime: cached.meta?.realtime ?? null,
      fallback: Boolean(cached.meta?.fallback),
      cached: true,
      cacheAgeMs: Date.now() - Number(cached.meta?.cached_at || Date.now()),
      dataAgeMs: null,
      candleQuality: cached.meta?.candleQuality || null,
      marketSession: cached.meta?.marketSession || null,
    });
  } else if (state.chartDataSymbol !== requestSymbol || !state.candles.length) {
    $("chartStatus").textContent = "快速加载K线...";
  }

  const sharedForceRefresh = runtime.chartRefreshCoordinator.inFlightPromise(refreshKey);
  if (sharedForceRefresh) {
    try {
      const outcome = await sharedForceRefresh;
      applyCoordinatedMarketSnapshot(outcome, {
        requestSymbol,
        requestBar,
        requestSession,
        cacheKey,
      });
    } catch (error) {
      if (!isAbortError(error) && activeRequest()) {
        const current = $("chartStatus").textContent || "";
        $("chartStatus").textContent = window.HakimiChartController.retryStatusText(current);
      }
    } finally {
      if (runtime.chartRequestAbortController === controller) {
        runtime.chartRequestAbortController = null;
        runtime.chartRequestKey = "";
      }
    }
    return;
  }

  try {
    const limit = marketSnapshotLimit(requestSymbol, requestBar);
    const data = await api(marketSnapshotPath({
      symbol: requestSymbol,
      bar: requestBar,
      limit,
      session: requestSession,
      fast: true,
      emit: false,
    }), { signal: controller.signal });
    if (!activeRequest()) return;
    applyMarketSnapshotToChart(data, { requestSymbol, requestBar, cacheKey });
    if (marketSnapshotNeedsRefresh(data)) {
      const refreshDelay = window.HakimiChartController.snapshotRefreshDelay(data, { requestSymbol, isStockMarket });
      scheduleSymbolTask(requestVersion, refreshDelay, () => refreshSnapshotCandlesInBackground({
        requestVersion,
        requestSymbol,
        requestBar,
        requestSession,
        limit,
        cacheKey,
      }));
    }
  } catch (error) {
    if (isAbortError(error)) return;
    if (!activeRequest()) return;
    if (state.symbol === "BTC-USDT" && ["1D", "1Dutc"].includes(requestBar)) {
      let local;
      try {
        local = await api("/api/local/btc-daily?limit=500", { signal: controller.signal });
      } catch (localError) {
        if (isAbortError(localError) || !activeRequest()) return;
        ensureActiveChartPreview(requestSymbol, requestBar);
        $("chartStatus").textContent = `K线加载失败：${localError.message}，保留快速预览`;
        return;
      }
      if (!activeRequest()) return;
      const rows = (local.rows || []).map(candleFromCsv).filter((row) => Number.isFinite(row.close) && row.close > 0);
      applyChartRows({
        symbol: requestSymbol,
        bar: "1Dutc",
        rows,
        status: "Local BTC daily database",
        source: local.source || "local_btc_daily",
        cacheKey,
        warning: local.warning || "",
        realtime: false,
        fallback: true,
      });
    } else {
      ensureActiveChartPreview(requestSymbol, requestBar);
      const keepText = chartIsVisibleForSymbol(requestSymbol) ? "，保留快速预览" : "";
      $("chartStatus").textContent = `K线加载失败：${error.message}${keepText}`;
      return;
    }
  } finally {
    if (runtime.chartRequestAbortController === controller) {
      runtime.chartRequestAbortController = null;
      runtime.chartRequestKey = "";
    }
  }
}

function chartRefreshTargetIsCurrent({ requestSymbol, requestBar, requestSession = "all" }) {
  return state.symbol === requestSymbol
    && state.bar === requestBar
    && (!isStockMarket(requestSymbol) || state.stockSession === requestSession);
}

function applyCoordinatedMarketSnapshot(outcome, { requestSymbol, requestBar, requestSession = "all", cacheKey }) {
  const data = outcome?.value;
  if (!data || data?.candles?.source === "quick_preview_seed") return null;
  if (!chartRefreshTargetIsCurrent({ requestSymbol, requestBar, requestSession })) return data;
  const refreshKey = window.HakimiChartController.inFlightKey({ requestSymbol, requestBar, requestSession });
  if (runtime.chartRefreshApplied.get(refreshKey) === outcome.refreshId) return data;
  runtime.chartRefreshApplied.set(refreshKey, outcome.refreshId);
  while (runtime.chartRefreshApplied.size > 64) {
    runtime.chartRefreshApplied.delete(runtime.chartRefreshApplied.keys().next().value);
  }
  applyMarketSnapshotToChart(data, { requestSymbol, requestBar, cacheKey });
  return data;
}

async function refreshSnapshotCandlesInBackground({ requestVersion, requestSymbol, requestBar, requestSession = "all", limit = 300, cacheKey, manual = false, reason = "auto_refresh", throwOnError = false }) {
  const refreshKey = window.HakimiChartController.inFlightKey({ requestSymbol, requestBar, requestSession, limit });
  try {
    const outcome = await runtime.chartRefreshCoordinator.request({
      key: refreshKey,
      manual,
      task: async () => {
        // A full force snapshot supersedes an unfinished fast snapshot for the same identity.
        if (runtime.chartRequestKey === refreshKey) runtime.chartRequestAbortController?.abort();
        const data = await api(marketSnapshotPath({
          symbol: requestSymbol,
          bar: requestBar,
          limit,
          session: requestSession,
          fast: false,
          force: true,
          emit: false,
          consumer: reason === "manual" ? "manual_chart_refresh" : "chart_refresh",
        }));
        if (data?.candles?.source === "quick_preview_seed") {
          throw new Error("forced_refresh_returned_preview");
        }
        return data;
      },
    });
    const data = applyCoordinatedMarketSnapshot(outcome, {
      requestSymbol,
      requestBar,
      requestSession,
      cacheKey,
    });
    return { outcome, data };
  } catch (error) {
    if (isAbortError(error)) return { outcome: null, data: null };
    if (chartRefreshTargetIsCurrent({ requestSymbol, requestBar, requestSession })) {
      const current = $("chartStatus").textContent || "";
      $("chartStatus").textContent = window.HakimiChartController.retryStatusText(current);
    }
    if (throwOnError) throw error;
    return { outcome: null, data: null, error };
  }
}

async function refreshChartCandlesInBackground({ requestVersion, requestSymbol, requestBar, cacheKey }) {
  return refreshSnapshotCandlesInBackground({
    requestVersion,
    requestSymbol,
    requestBar,
    requestSession: "all",
    limit: marketSnapshotLimit(requestSymbol, requestBar),
    cacheKey,
  });
}

async function refreshStockCandlesInBackground({ requestVersion, requestSymbol, requestBar, requestSession, limit, cacheKey }) {
  return refreshSnapshotCandlesInBackground({
    requestVersion,
    requestSymbol,
    requestBar,
    requestSession,
    limit: limit || marketSnapshotLimit(requestSymbol, requestBar),
    cacheKey,
  });
}

async function loadLocalHistory() {
  if (state.symbol !== "BTC-USDT") {
    $("chartStatus").textContent = "Local history currently contains BTC-USDT only";
    return;
  }
  const local = await api("/api/local/btc-daily?limit=1000");
  state.candles = (local.rows || []).map(candleFromCsv);
  state.chartView.offset = 0;
  $("chartStatus").textContent = "Local BTC history loaded";
  loadDrawings();
  drawChart();
  renderHistory(local.rows || []);
}

function stockQuoteStamp(data = {}) {
  const ts = Number(data.ts || data.updated_at || Date.now());
  return Number.isFinite(ts) && ts > 0 ? ts : Date.now();
}

function addStockPriceLog(data = {}, source = "STOCK") {
  if (!isStockMarket()) return;
  const price = Number(data.last);
  if (!Number.isFinite(price) || price <= 0) return;
  const symbol = (data.symbol || state.symbol || "").toUpperCase();
  if (symbol !== state.symbol) return;
  const open = Number(data.open24h);
  const change = Number.isFinite(Number(data.change24h_pct))
    ? Number(data.change24h_pct)
    : open > 0 ? ((price - open) / open) * 100 : 0;
  const stamp = stockQuoteStamp(data);
  const row = {
    symbol,
    price,
    change,
    source: String(data.source || source || "STOCK").toUpperCase(),
    status: data.status || "",
    volume: Number(data.vol24h || 0),
    bid: Number(data.bidPx || 0),
    ask: Number(data.askPx || 0),
    ts: stamp,
  };
  const top = state.stockPriceLog[0];
  if (top
    && top.symbol === row.symbol
    && top.source === row.source
    && Math.abs(Number(top.price || 0) - row.price) / Math.max(row.price, 1e-9) < 0.00001
    && Math.abs(stamp - Number(top.ts || 0)) < 8000) {
    state.stockPriceLog[0] = { ...top, ...row };
  } else {
    state.stockPriceLog.unshift(row);
  }
  state.stockPriceLog = state.stockPriceLog
    .filter((item) => item.symbol === state.symbol)
    .sort((a, b) => Number(b.ts || 0) - Number(a.ts || 0))
    .slice(0, 80);
  renderTrades();
  renderBook();
}

function mergeFutuTickerRowsIntoStockLog(data = {}) {
  if (!isStockMarket() || data.symbol !== state.symbol) return;
  const rows = (data.ticker || []).slice(-20).reverse();
  if (!rows.length) return;
  for (const item of rows) {
    const price = Number(item.price);
    if (!Number.isFinite(price) || price <= 0) continue;
    const stamp = Date.parse(item.time || "") || Date.now();
    state.stockPriceLog.push({
      symbol: state.symbol,
      price,
      change: 0,
      source: "FUTU_TAPE",
      status: item.ticker_direction || "",
      volume: Number(item.volume || 0),
      bid: 0,
      ask: 0,
      ts: stamp,
    });
  }
  const seen = new Set();
  state.stockPriceLog = state.stockPriceLog
    .filter((row) => {
      const key = `${row.symbol}|${row.source}|${Math.round(Number(row.ts || 0) / 1000)}|${Number(row.price || 0).toFixed(4)}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return row.symbol === state.symbol;
    })
    .sort((a, b) => Number(b.ts || 0) - Number(a.ts || 0))
    .slice(0, 80);
  renderTrades();
}

function canonicalTickerSymbol(value = "") {
  const symbol = String(value || "").trim().toUpperCase();
  return symbol.startsWith("US.") ? symbol.slice(3) : symbol;
}

function updateTicker(data, source = "WS") {
  const last = Number(data.last);
  if (!Number.isFinite(last) || last <= 0) return;
  const incomingSymbol = canonicalTickerSymbol(data.symbol || data.instId || "");
  const activeSymbol = canonicalTickerSymbol(state.symbol);
  const activeInstId = canonicalTickerSymbol(okxInstId(state.symbol));
  if (incomingSymbol && incomingSymbol !== activeSymbol && incomingSymbol !== activeInstId) {
    updateMarketFromTicker({ ...data, symbol: incomingSymbol, instId: incomingSymbol }, { syncActive: false });
    scheduleMarketRender(true);
    return;
  }
  if (isStockMarket() && data.market_session && typeof data.market_session === "object") {
    state.marketSession = data.market_session;
  }
  const chartGuard = isStockMarket() ? activeStockChartQuoteGuard(data, activeSymbol) : null;
  if (chartGuard && !chartGuard.decision.allowed) {
    const status = $("chartStatus")?.textContent || "";
    const reportableMismatch = !["untrusted_source", "quote_not_ready", "guard_unavailable"].includes(chartGuard.decision.reason);
    if (reportableMismatch && chartGuard.decision.deviation > 0.08 && !status.includes("报价证据异常")) {
      $("chartStatus").textContent = `${status} / 报价证据异常，未叠加到K线`;
    }
    updateMarketFromTicker({ ...data, symbol: activeSymbol, instId: activeSymbol });
    scheduleMarketRender(true);
    return;
  }
  if (isStockMarket() && !acceptStockQuoteContext(data)) return;
  state.lastPrice = last;
  const open24h = Number(data.open24h);
  const change = Number.isFinite(Number(data.change24h_pct))
    ? Number(data.change24h_pct)
    : open24h ? ((last - open24h) / open24h) * 100 : 0;
  const quoteQuality = data.quote_quality && typeof data.quote_quality === "object" ? data.quote_quality : {};
  const verifiedPreviousClose = Number(data.prevClose);
  const verifiedChange = verifiedPreviousClose > 0 ? (last / verifiedPreviousClose - 1) * 100 : Number.NaN;
  const verifiedExtreme = quoteQuality.status === "READY"
    && data.change_basis === "previous_close"
    && Number.isFinite(verifiedChange)
    && Math.abs(verifiedChange - change) <= 0.5;
  const changeNeedsReview = isStockMarket() && (Boolean(quoteQuality.quarantined) || (Math.abs(change) >= 45 && !verifiedExtreme));
  $("lastPrice").textContent = number(last, last > 100 ? 1 : 4);
  $("lastPrice").className = `last-price ${changeNeedsReview ? "flat" : cssMove(change)}`;
  $("priceChange").textContent = changeNeedsReview ? "数据待核" : `${change >= 0 ? "+" : ""}${number(change, 2)}%`;
  $("priceChange").className = `price-change ${changeNeedsReview ? "flat" : cssMove(change)}`;
  $("high24h").textContent = number(data.high24h, 2);
  $("low24h").textContent = number(data.low24h, 2);
  $("vol24h").textContent = compact(isStockMarket() ? data.vol24h : (data.volCcy24h || data.vol24h));
  $("bidAsk").textContent = bidAskText(data.bidPx, data.askPx, 2);
  $("midPrice").textContent = number(last, 2);
  const stamp = Number(data.ts || Date.now());
  if (isStockMarket()) {
    const stockSource = String(data.source || source || "STOCK").toUpperCase();
    const isSeed = stockSource.includes("OFFLINE") || stockSource.includes("SEED");
    const sessionLabel = state.marketSession?.status_label || state.marketSession?.phase_label || "";
    setConnection(`${isSeed ? "离线种子" : `股票${stockSource}`}${sessionLabel ? ` / ${sessionLabel}` : ""} ${timeText(stamp)}`, isSeed ? "flat" : "up");
    state.futu = { ...(state.futu || {}), last_stock_source: stockSource };
    addStockPriceLog(data, stockSource);
  } else {
    setConnection(`${source === "REST" ? "后端实盘" : "实盘"} ${timeText(stamp)}`, "up");
    state.desktop.okxOnline = true;
  }
  syncLiveCandle(last, data);
  if (isStockMarket()) maybeRefreshActiveStockCandles("quote");

  updateMarketFromTicker({
    ...data,
    symbol: incomingSymbol || data.symbol || state.symbol,
    instId: incomingSymbol || data.instId || state.symbol,
  }, { syncActive: false });
  scheduleMarketRender(true);
  renderDesktopStatus();
  renderSideInsights();
  const meta = document.querySelector(".symbol-meta");
  if (meta) meta.textContent = activeSymbolMetaText();
  renderLiveSourceBar();
}

async function loadMarkets() {
  try {
    const data = await api("/api/markets");
    const existing = new Map(markets.map((item) => [item.symbol, item]));
    markets = (data.markets || markets).map((item) => {
      const prev = existing.get(item.symbol) || {};
      const hasNewerQuote = Number(prev.lastUpdated || 0) > 0;
      return {
        ...prev,
        ...item,
        price: prev.price && prev.price !== "--" ? prev.price : item.price || "--",
        change: prev.change && prev.change !== "--" ? prev.change : item.change || "--",
        rawChange: prev.rawChange ?? item.rawChange,
        lastUpdated: prev.lastUpdated || item.lastUpdated,
        ...(hasNewerQuote ? {
          source: prev.source,
          originSource: prev.originSource || prev.origin_source || "",
          warning: prev.warning || "",
          dataAgeMs: prev.dataAgeMs ?? null,
          quoteQuality: prev.quoteQuality || {},
          marketSession: prev.marketSession || null,
          high24h: prev.high24h,
          low24h: prev.low24h,
          vol24h: prev.vol24h,
          baseVolume24h: prev.baseVolume24h,
          quoteVolume24h: prev.quoteVolume24h,
          bidPx: prev.bidPx,
          askPx: prev.askPx,
        } : {}),
      };
    });
    renderMarkets();
    syncActiveMarketQuote("市场列表已同步");
  } catch (error) {
    renderMarkets();
  }
}

async function loadFutuStatus(force = false) {
  try {
    const data = await api(`/api/futu/status?force=${force ? "true" : "false"}`);
    state.futu = data;
    let sourceSummary = "";
    let sourceStateText = data.opend_online ? "Futu" : "Offline seed";
    let sourceStateClass = data.opend_online ? "up" : "flat";
    try {
      const sourceSymbol = isStockMarket(state.symbol) ? state.symbol : "AAPL";
      const sourceData = await api(`/api/stocks/data-sources?symbol=${encodeURIComponent(sourceSymbol)}&interval=${encodeURIComponent(stockIntervalForBar(state.bar))}&session=${encodeURIComponent(state.stockSession)}`);
      const cache = sourceData.cache || {};
      if (cache.persistent) {
        const ageText = cache.persistent_data_age_ms ? ` / 数据约${chartAgeText(cache.persistent_data_age_ms)}前` : "";
        const latestText = cache.persistent_latest_at ? ` / 最新 ${cache.persistent_latest_at}` : "";
        sourceStateText = cache.persistent_fresh
          ? `本地库 ${marketSourceLabel(cache.persistent_source)}`
          : `旧缓存 ${marketSourceLabel(cache.persistent_source)}`;
        sourceStateText = `${sourceStateText}${latestText}${ageText}`;
        sourceStateClass = cache.persistent_fresh ? "up" : "down";
      } else if ((sourceData.order || []).length) {
        sourceStateText = (sourceData.order || []).slice(0, 3).join(" > ");
      }
      sourceSummary = sourceData.summary ? ` / ${sourceData.summary}` : "";
    } catch (sourceError) {
      sourceSummary = " / data source status unavailable";
    }
    $("futuOpenDState").textContent = data.opend_online ? "ONLINE" : "OFFLINE";
    $("futuOpenDState").className = data.opend_online ? "up" : "down";
    $("futuPortState").textContent = `${data.host}:${data.port}`;
    $("futuSourceState").textContent = sourceStateText;
    $("futuSourceState").className = sourceStateClass;
    $("futuTradeState").textContent = data.live_trading_hard_block ? "实盘永久硬锁" : "保护未确认 · 禁止执行";
    $("futuTradeState").className = "flat";
    $("stockState").textContent = `${data.stock_count || 0} stocks / ${data.message || "--"}${sourceSummary}`;
    renderFutuGuide(data);
    renderDesktopStatus();
    renderLiveSourceBar();
  } catch (error) {
    $("futuOpenDState").textContent = "ERROR";
    $("futuOpenDState").className = "down";
    $("stockState").textContent = `Futu status failed: ${error.message}`;
    renderFutuGuide({ setup_hint: "Futu status failed", steps: [{ label: "Connection", state: "error", detail: error.message }] });
    state.futu = { opend_online: false };
    renderDesktopStatus();
    renderLiveSourceBar();
  }
}

async function refreshMarketTickers(force = false) {
  try {
    const data = await api(force ? "/api/markets/tickers?force=true" : "/api/markets/tickers?fast=true");
    for (const row of data.tickers || []) updateMarketFromTicker(row);
    state.desktop.okxOnline = (data.tickers || []).some((row) => row.source === "okx" && Number(row.last) > 0);
    scheduleMarketRender(true);
    renderDesktopStatus();
  } catch (error) {
    state.desktop.okxOnline = false;
    renderDesktopStatus();
    // Keep existing market prices when the exchange API is unreachable.
  }
}

function renderMarketScanner(data = {}) {
  state.marketScanner = data;
  const rows = Array.isArray(data.rows) ? data.rows : [];
  const summary = $("scannerSummary");
  const target = $("scannerRows");
  if (summary) summary.textContent = data.summary || "等待研究扫描";
  if (!target) return;
  target.innerHTML = rows.map((row) => {
    const symbol = escapeHtml(row.symbol || "--");
    const change = Number(row.change24h_pct);
    const changeText = Number.isFinite(change) ? `${change >= 0 ? "+" : ""}${number(change, 1)}%` : "--";
    return `
    <div class="scanner-row" role="listitem" data-symbol="${symbol}">
      <span><strong>${symbol}</strong></span>
      <span class="flat" title="开发期扫描分数 · 非交易信号">${number(row.score, 1)}</span>
      <span class="flat">${changeText}</span>
      <span>${number(row.location_pct, 0)}%</span>
      <span>${escapeHtml(row.strategy_name || "研究观察 · 未选参")}</span>
      <span class="flat">${escapeHtml(row.risk || "风险观察")}</span>
      <span>${escapeHtml(row.action || "观察 / 仅研究 / 非订单")} / ${escapeHtml(row.reason || "等待更多证据")}</span>
    </div>
  `;
  }).join("");
  target.querySelectorAll(".scanner-row").forEach((row) => {
    row.addEventListener("click", () => {
      selectSymbol(row.dataset.symbol, { focusChart: true });
      if (summary) summary.textContent = `已切换到 ${row.dataset.symbol} · 研究观察，未套用策略`;
    });
  });
}

async function loadMarketScanner(writeNotification = false) {
  try {
    $("scannerSummary").textContent = writeNotification ? "正在写入研究提醒..." : "正在整理研究扫描...";
    const data = await api(`/api/market/scanner?notify=${writeNotification ? "true" : "false"}`);
    renderMarketScanner(data);
    if (writeNotification) await loadProfile();
  } catch (error) {
    $("scannerSummary").textContent = `研究扫描暂不可用：${error.message}`;
  }
}

function anomalyTone(row = {}) {
  if (row.tone) return row.tone;
  if (row.severity === "CRITICAL" || row.severity === "HIGH") return "down";
  if (row.severity === "MEDIUM") return "flat";
  return "flat";
}

function anomalyQuality(row = {}) {
  const quality = row.data_quality || {};
  const source = String(quality.source || row.metrics?.source || row.market_type || "").toLowerCase();
  if (quality.label) return quality;
  if (source.includes("okx") || row.market_type === "crypto") return { label: "OKX待确认", tone: "flat", realtime: false, fallback: false };
  if (source === "futu") return { label: "Futu待确认", tone: "flat", realtime: false, fallback: false };
  if (["yahoo", "stooq", "external"].includes(source)) return { label: `${row.metrics?.source || "外部源"}延迟`, tone: "flat", realtime: false, fallback: false };
  if (source.includes("local") || source.includes("seed") || source.includes("cache")) return { label: "本地兜底", tone: "down", realtime: false, fallback: true };
  return { label: "待确认", tone: "flat", realtime: false, fallback: false };
}

function anomalyPriority(row = {}) {
  const priority = row.watch_priority || {};
  const score = Number(row.raw_score ?? row.score ?? 0);
  const quality = anomalyQuality(row);
  if (quality.fallback && score >= 68) return { label: "C 高分待核", level: "C", tone: "down", detail: "异动分较高，但来源为缓存或兜底；刷新报价与K线确认后才能升级。" };
  if (priority.label) return priority;
  if (quality.fallback) return { label: "C 先验数据源", level: "C", tone: "down", detail: "兜底/缓存数据，先确认来源。" };
  if (score >= 82 && quality.realtime) return { label: "A 立即看图", level: "A", tone: "up", detail: "强异动且数据较新。" };
  if (score >= 68) return { label: "B 等确认", level: "B", tone: "flat", detail: "等待量能、结构或数据源确认。" };
  return { label: "C 记录观察", level: "C", tone: "flat", detail: "放入观察队列。" };
}

function anomalyQuarantine(row = {}) {
  if (row.data_quarantined || row.data_quality?.quarantined) {
    return { active: true, reason: row.quarantine_reason || row.data_quality?.quarantine_reason || "数据源标记为待核" };
  }
  const quality = anomalyQuality(row);
  const change = Math.abs(Number(row.change24h_pct || 0));
  const range = Number(row.range24h_pct || 0);
  const active = Boolean(quality.fallback && (change >= 25 || range >= 40));
  return { active, reason: active ? "缓存极值疑似复权、拆股或基准价错配" : "" };
}

function anomalySeverityLabel(row = {}) {
  if (anomalyQuarantine(row).active) return "数据待核";
  if (anomalyQuality(row).fallback && Number(row.raw_score ?? row.score ?? 0) >= 68) return "高分待核";
  return row.severity_label || row.severity || "--";
}

function anomalyNeedsReview(row = {}) {
  return anomalyQuarantine(row).active
    || (anomalyQuality(row).fallback && Number(row.raw_score ?? row.score ?? 0) >= 68);
}

function anomalyMotion(row = {}) {
  const motion = row.motion || {};
  return {
    state: String(motion.state || "BASELINE").toUpperCase(),
    label: motion.label || "基线",
    tone: motion.tone || "flat",
    comparisonAvailable: Boolean(motion.comparison_available),
    scoreDelta: Number(motion.score_delta || 0),
    changeDelta: Number(motion.change_delta_pct || 0),
  };
}

function anomalyOutcome(row = {}) {
  const outcome = row.outcome || {};
  return {
    state: String(outcome.state || "NO_BASELINE").toUpperCase(),
    label: outcome.label || "等待评估",
    tone: outcome.tone || "flat",
    entryPrice: Number(outcome.entry_price || row.entry_price || 0),
    currentPrice: Number(outcome.current_price || row.price || 0),
    directionalReturn: Number(outcome.directional_return_pct || 0),
    reason: outcome.reason || "等待后续扫描形成后验结果。",
  };
}

function anomalyRowsForFilter(rows = []) {
  if (state.anomalyFilter === "changes") {
    return rows.filter((row) => ["NEW", "SURGING", "CONFIRMING"].includes(anomalyMotion(row).state));
  }
  if (state.anomalyFilter === "priority") {
    return rows.filter((row) => ["A", "B"].includes(anomalyPriority(row).level) && !anomalyNeedsReview(row));
  }
  if (state.anomalyFilter === "review") return rows.filter(anomalyNeedsReview);
  return rows;
}

function anomalyDirectionLabel(row = {}) {
  if (anomalyQuarantine(row).active) return "研究观察·数据待核";
  return anomalyNeedsReview(row) ? "研究观察·待核" : "研究观察";
}

function normalizeAnomalyCards(cards = [], rows = []) {
  const priorityRows = rows.map((row) => ({ row, priority: anomalyPriority(row) }));
  const priorityA = priorityRows.filter(({ priority }) => priority.level === "A").length;
  const priorityB = priorityRows.filter(({ priority }) => priority.level === "B").length;
  const pendingReview = priorityRows.filter(({ row, priority }) => priority.level === "C"
    && (anomalyQuarantine(row).active || Number(row.raw_score ?? row.score ?? 0) >= 68)).length;
  const trustedHigh = rows.filter((row) => !anomalyQuality(row).fallback
    && !anomalyQuarantine(row).active
    && ["HIGH", "CRITICAL"].includes(String(row.severity || ""))).length;
  return cards.map((card) => {
    if (String(card.label || "").includes("高严重度")) {
      return { ...card, value: String(trustedHigh), detail: "只统计已通过数据质量检查的高关注项；缓存极值进入待核。" };
    }
    if (["观察队列", "可行动队列"].includes(String(card.label || ""))) {
      return {
        ...card,
        label: "研究优先队列",
        value: `A ${priorityA} / B ${priorityB} / 待核 ${pendingReview}`,
        tone: "flat",
        detail: "按证据完整度与数据质量排序；不生成方向或订单。",
      };
    }
    return card;
  });
}

function renderAnomalyCards(cards = []) {
  const target = $("anomalyRadarCards");
  if (!target) return;
  target.innerHTML = cards.length ? cards.map((card) => `
    <div class="anomaly-card ${card.tone || "flat"}">
      <span>${escapeHtml(card.label || "--")}</span>
      <strong>${escapeHtml(card.value || "--")}</strong>
      <em>${escapeHtml(card.detail || "")}</em>
    </div>
  `).join("") : `
    <div class="anomaly-card flat"><span>雷达</span><strong>等待数据</strong><em>刷新后显示同步异动和严重度。</em></div>
  `;
}

function renderAnomalyDetailCards(row = state.selectedAnomaly, trend = state.trendCockpit) {
  const target = $("anomalyDetailCards");
  if (!target) return;
  if (!row) {
    target.innerHTML = `<div class="anomaly-detail-card flat"><span>异动</span><strong>等待选择</strong><em>点击雷达行后生成详情。</em></div>`;
    return;
  }
  const quality = anomalyQuality(row);
  const change = Number(row.change24h_pct || 0);
  const range = Number(row.range24h_pct || 0);
  const location = Number(row.location_pct || 0);
  const probabilities = trend?.symbol === row.symbol ? trend?.probabilities || {} : {};
  const longRate = Number(probabilities.long_win_rate_pct);
  const shortRate = Number(probabilities.short_win_rate_pct);
  const priority = anomalyPriority(row);
  const motion = anomalyMotion(row);
  const outcome = anomalyOutcome(row);
  const probabilityText = Number.isFinite(longRate) && Number.isFinite(shortRate)
    ? `多 ${number(longRate, 1)}% / 空 ${number(shortRate, 1)}%`
    : "等待驾驶舱";
  const cards = [
    { label: "数据源", value: quality.label || "--", detail: quality.fallback ? "兜底数据，必须复核" : quality.realtime ? "实时观察源" : "延迟研究源", tone: quality.tone || "flat" },
    { label: "观察优先级", value: priority.label || "--", detail: priority.detail || row.next_observation || "等待下一轮雷达确认", tone: "flat" },
    { label: "本轮变化", value: motion.label, detail: motion.comparisonAvailable ? `评分 ${motion.scoreDelta >= 0 ? "+" : ""}${number(motion.scoreDelta, 1)} / 涨跌变化 ${motion.changeDelta >= 0 ? "+" : ""}${number(motion.changeDelta, 2)}%` : "已建立基线，等待下一轮比较", tone: "flat" },
    { label: "后验评估", value: outcome.label, detail: outcome.reason, tone: "flat" },
    { label: "严重度", value: anomalySeverityLabel(row), detail: anomalyQuarantine(row).active ? anomalyQuarantine(row).reason : `评分 ${number(row.score || 0, 1)} / 100`, tone: anomalyNeedsReview(row) ? "flat" : anomalyTone(row) },
    { label: "方向", value: anomalyDirectionLabel(row), detail: row.reason || "--", tone: "flat" },
    { label: "联动主题", value: row.theme || row.market_type || "--", detail: `涨跌 ${change >= 0 ? "+" : ""}${number(change, 2)}% / 振幅 ${number(range, 2)}%`, tone: "flat" },
    { label: "位置/量能", value: `${number(location, 1)}%`, detail: `成交排名 ${row.volume_rank || "--"}，位置越极端越要等确认`, tone: "flat" },
    { label: "多空估计", value: probabilityText, detail: probabilities.estimate_note || "样本估计，仅研究和模拟盘验证", tone: "flat" },
  ];
  target.innerHTML = cards.map((card) => `
    <div class="anomaly-detail-card ${card.tone || "flat"}">
      <span>${escapeHtml(card.label || "--")}</span>
      <strong>${escapeHtml(card.value || "--")}</strong>
      <em>${escapeHtml(card.detail || "")}</em>
    </div>
  `).join("");
}

function renderAnomalyDetail(row = state.selectedAnomaly, trend = state.trendCockpit, detail = state.anomalyDetail) {
  const evidenceTarget = $("anomalyEvidenceRows");
  const promptTarget = $("anomalyPromptPreview");
  if (!evidenceTarget || !promptTarget) return;
  renderAnomalyDetailCards(row, trend);
  const detailMatches = Boolean(detail?.symbol && row?.symbol && detail.symbol === row.symbol);
  const detailChain = detailMatches ? (detail.evidence_chain || []) : [];
  const evidence = detailChain.length ? detailChain : [
    ...(row ? [
      { label: "数据质量", value: anomalyQuality(row).label || "--" },
      { label: "安全边界", value: row.safe_action || "观察 / 仅研究 / 仅模拟盘验证" },
    ] : []),
    ...(row?.evidence || []).map((item) => ({ label: "雷达证据", value: item })),
    ...(row?.waiting_conditions || []).slice(0, 4).map((item) => ({ label: "等待条件", value: item })),
    ...(trend?.evidence || []).slice(0, 5).map((item) => ({ label: "走势证据", value: item })),
    ...(trend?.counter_evidence || []).slice(0, 4).map((item) => ({ label: "反证/失效", value: item })),
    ...(trend?.waiting_conditions || []).slice(0, 4).map((item) => ({ label: "等待条件", value: item })),
  ];
  evidenceTarget.innerHTML = evidence.length ? evidence.map((item) => `
    <div class="anomaly-evidence-row">
      <span>${escapeHtml(item.label)}</span>
      <strong>${escapeHtml(item.value)}</strong>
    </div>
  `).join("") : `<div class="anomaly-evidence-row"><span>证据链</span><strong>点击异动标的后生成。</strong></div>`;

  const prompt = detailMatches ? (detail.ai_prompt || trend?.ai_prompt || {}) : (trend?.ai_prompt || {});
  if (prompt.user_prompt) {
    let parsed = prompt.user_prompt;
    try {
      parsed = JSON.stringify(JSON.parse(prompt.user_prompt), null, 2);
    } catch (error) {
      parsed = prompt.user_prompt;
    }
    const fullPrompt = `${prompt.safety_notice || "仅研究 / 仅模拟盘验证"}\n\n系统提示:\n${prompt.system_prompt || ""}\n\n结构化输入:\n${parsed}`;
    promptTarget.dataset.fullPrompt = fullPrompt;
    promptTarget.textContent = [
      prompt.safety_notice || "仅研究 / 仅模拟盘验证",
      `AI结构化输入已准备：${row?.symbol || trend?.symbol || state.symbol}`,
      `证据 ${trend?.evidence?.length || row?.evidence?.length || 0} 条 / 反证 ${trend?.counter_evidence?.length || 0} 条 / 等待条件 ${trend?.waiting_conditions?.length || 0} 条`,
      "完整提示词将在后续AI聊天室中使用，当前面板仅显示摘要以保持切换流畅。",
    ].join("\n");
  } else if (row) {
    promptTarget.dataset.fullPrompt = JSON.stringify({
      safety_notice: "观察 / 仅研究 / 仅模拟盘验证",
      anomaly: row,
    }, null, 2);
    promptTarget.textContent = `观察 / 仅研究 / 仅模拟盘验证\n${row.symbol || state.symbol} 异动摘要：${row.reason || "--"}\n证据 ${(row.evidence || []).length} 条，点击后续AI聊天室再展开完整提示。`;
  } else {
    promptTarget.dataset.fullPrompt = "";
    promptTarget.textContent = "等待选择异动标的";
  }
  renderMarketWorkflowStrip();
}

function renderAnomalyEvents(data = state.anomalyEvents || {}) {
  const target = $("anomalyEventRows");
  const summary = $("anomalyEventSummary");
  if (!target) return;
  state.anomalyEvents = data;
  const rows = data.rows || [];
  if (summary) summary.textContent = data.summary || (rows.length ? `已记录 ${rows.length} 条异动` : "等待异动事件入库");
  target.innerHTML = rows.length ? rows.slice(0, 18).map((row) => {
    const change = Number(row.change24h_pct || 0);
    const age = row.age_ms ? `${chartAgeText(row.age_ms)}前` : row.last_seen_text || "--";
    const motion = anomalyMotion(row);
    const outcome = anomalyOutcome(row);
    const outcomeMove = ["CONFIRMED", "INVALIDATED", "NO_FOLLOW_THROUGH", "MONITORING"].includes(outcome.state)
      ? ` ${outcome.directionalReturn >= 0 ? "+" : ""}${number(outcome.directionalReturn, 2)}%`
      : "";
    return `
      <button class="anomaly-event-row" data-symbol="${escapeHtml(row.symbol || "")}">
        <span><strong>${escapeHtml(row.symbol || "--")}</strong><em>${escapeHtml(row.last_seen_text || "--")} / ${escapeHtml(age)}</em></span>
        <span class="${anomalyTone(row)}"><strong>${escapeHtml(row.severity_label || row.severity || "WATCH")}</strong><em class="flat">${escapeHtml(motion.label)}</em></span>
        <span class="flat">${change >= 0 ? "+" : ""}${number(change, 2)}%</span>
        <span>${escapeHtml(row.reason || "--")}</span>
        <span class="flat"><strong>${number(row.score || 0, 1)}</strong><em>${escapeHtml(outcome.label)}${escapeHtml(outcomeMove)}</em></span>
      </button>
    `;
  }).join("") : `<div class="anomaly-event-empty">暂无历史异动。刷新雷达后会自动记录。</div>`;
  target.querySelectorAll(".anomaly-event-row").forEach((row) => {
    row.addEventListener("click", () => selectAnomaly(row.dataset.symbol || state.symbol));
  });
}

async function loadAnomalyEvents(symbol = "", options = {}) {
  if (runtime.anomalyEventsInFlight && !options.force) return null;
  runtime.anomalyEventsInFlight = true;
  try {
    const params = new URLSearchParams({ limit: String(options.limit || 80) });
    if (symbol) params.set("symbol", symbol);
    const data = await api(`/api/market/anomaly-events?${params.toString()}`);
    renderAnomalyEvents(data);
    return data;
  } catch (error) {
    const summary = $("anomalyEventSummary");
    if (summary) summary.textContent = `事件库离线：${error.message}`;
    return null;
  } finally {
    runtime.anomalyEventsInFlight = false;
  }
}

function cryptoSourceControl(symbol = state.symbol) {
  const quality = state.chartQuality || {};
  return {
    ok: true,
    symbol,
    summary: `${symbol} 使用OKX公共行情；本面板只做观察和研究。`,
    cards: [
      { label: "行情源", value: "OKX", detail: "公共行情端点，无需私钥", tone: "up" },
      { label: "K线源", value: quality.sourceLabel || quality.source || "OKX实时/缓存", detail: quality.warningText || "切换时先显示预览，再补实时K线", tone: quality.tone || "flat" },
      { label: "实时状态", value: quality.mode || "latest", detail: quality.freshnessText || "等待K线刷新", tone: quality.tone || "flat" },
      { label: "实盘边界", value: "BLOCKED", detail: "不开放真实下单，只做行情分析", tone: "down" },
    ],
    rows: [
      { name: "OKX Ticker", status: "AUTO", detail: "WebSocket/轮询", freshness: "实时优先", next: "用于价格与盘口刷新", tone: "up" },
      { name: "OKX K线", status: quality.source ? "READY" : "WAIT", detail: quality.sourceLabel || quality.source || "--", freshness: quality.freshnessText || "--", next: "用于走势分析和AI证据链", tone: quality.tone || "flat" },
      { name: "本地兜底", status: quality.fallback ? "ACTIVE" : "STANDBY", detail: quality.warningText || "网络异常时兜底", freshness: "仅研究", next: "实时源恢复后复核", tone: quality.fallback ? "down" : "flat" },
    ],
  };
}

function renderStockSourceControl(data = state.stockSourceControl || cryptoSourceControl()) {
  const cardTarget = $("stockSourceControlCards");
  const rowTarget = $("stockSourceControlRows");
  const summary = $("stockSourceControlSummary");
  if (!cardTarget || !rowTarget) return;
  state.stockSourceControl = data;
  if (summary) summary.textContent = data.summary || `${data.symbol || state.symbol} 数据源状态`;
  const cards = data.cards || [];
  cardTarget.innerHTML = cards.length ? cards.map((card) => `
    <div class="stock-source-card ${card.tone || "flat"}">
      <span>${escapeHtml(card.label || "--")}</span>
      <strong>${escapeHtml(marketSourceLabel(card.value || "--"))}</strong>
      <em>${escapeHtml(card.detail || "")}</em>
    </div>
  `).join("") : `<div class="stock-source-card flat"><span>数据源</span><strong>等待检查</strong><em>切换标的后刷新。</em></div>`;
  const shared = state.marketSnapshotContext || {};
  const sharedRow = shared.snapshot_id ? {
    name: "共享行情快照",
    status: shared.shared ? "REUSED" : "READY",
    detail: `${(shared.consumers || []).map(snapshotConsumerLabel).join(" / ") || snapshotConsumerLabel(shared.consumer || "chart")} / 请求 ${number(shared.request_count || 1, 0)}`,
    freshness: shared.snapshot_cache_hit ? "快照复用" : shared.quote_cache_hit ? "报价复用" : "新快照",
    next: "K线、研究和AI共用同一报价与质量标记",
    tone: "up",
  } : null;
  const rows = [sharedRow, ...(data.rows || [])].filter(Boolean);
  rowTarget.innerHTML = rows.length ? rows.map((row) => `
    <div class="stock-source-row">
      <span><strong>${escapeHtml(row.name || "--")}</strong><em>${escapeHtml(row.detail || "--")}</em></span>
      <span class="${row.tone || dataSourceTone(row)}">${escapeHtml(row.status || "--")}</span>
      <span>${escapeHtml(row.freshness || "--")}</span>
      <span>${escapeHtml(row.next || "--")}</span>
    </div>
  `).join("") : `<div class="stock-source-row empty"><span>无源控数据</span><span>--</span><span>--</span><span>--</span></div>`;
  renderMarketWorkflowStrip();
}

async function loadStockSourceControl(symbol = state.symbol, requestVersion = runtime.symbolVersion) {
  const requestSymbol = symbol || state.symbol;
  const requestBar = state.bar;
  const requestSession = state.stockSession;
  const activeRequest = () => requestVersion === runtime.symbolVersion
    && requestSymbol === state.symbol
    && requestBar === state.bar
    && requestSession === state.stockSession;
  if (!isStockMarket(requestSymbol)) {
    if (activeRequest()) renderStockSourceControl(cryptoSourceControl(requestSymbol));
    return null;
  }
  runtime.stockSourceControlSymbol = requestSymbol;
  try {
    const data = await api(`/api/stocks/source-control?symbol=${encodeURIComponent(requestSymbol)}&interval=${encodeURIComponent(stockIntervalForBar(requestBar))}&session=${encodeURIComponent(requestSession)}`);
    if (!activeRequest()) return null;
    renderStockSourceControl(data);
    return data;
  } catch (error) {
    if (!activeRequest()) return null;
    const summary = $("stockSourceControlSummary");
    if (summary) summary.textContent = `数据源总控离线：${error.message}`;
    return null;
  }
}

function renderAnomalyDetailPayload(data = {}) {
  if (!data?.ok) return;
  state.anomalyDetail = data;
  if (data.anomaly) {
    state.selectedAnomaly = { ...(state.selectedAnomaly || {}), ...data.anomaly };
  }
  if (data.trend?.ok && (!state.trendCockpit?.symbol || data.trend.symbol === state.symbol || data.trend.symbol === state.selectedAnomaly?.symbol)) {
    state.trendCockpit = data.trend;
  }
  if (data.events) renderAnomalyEvents({ ok: true, symbol: data.symbol, rows: data.events, summary: `${data.symbol} 最近异动事件 ${data.events.length || 0} 条` });
  if (data.source_control) renderStockSourceControl(data.source_control);
  renderAnomalyDetail(state.selectedAnomaly, data.trend || state.trendCockpit, data);
  renderMarketWorkflowStrip();
}

async function loadAnomalyDetail(symbol = state.selectedAnomaly?.symbol || state.symbol, requestVersion = runtime.symbolVersion) {
  const requestSymbol = symbol || state.symbol;
  if (!requestSymbol) return null;
  runtime.anomalyDetailSymbol = requestSymbol;
  const promptTarget = $("anomalyPromptPreview");
  if (promptTarget && state.selectedAnomaly?.symbol === requestSymbol) {
    promptTarget.textContent = `${requestSymbol} 正在补全异动详情、事件库和数据源证据...`;
  }
  try {
    const data = await api(`/api/market/anomaly-detail?symbol=${encodeURIComponent(requestSymbol)}`);
    if (runtime.anomalyDetailSymbol !== requestSymbol) return null;
    if (requestVersion !== runtime.symbolVersion && requestSymbol === state.symbol) return null;
    if (requestSymbol !== state.symbol && requestSymbol !== state.selectedAnomaly?.symbol) return null;
    renderAnomalyDetailPayload(data);
    return data;
  } catch (error) {
    if (promptTarget && state.selectedAnomaly?.symbol === requestSymbol) {
      promptTarget.textContent = `${requestSymbol} 异动详情暂不可用：${error.message}`;
    }
    return null;
  }
}

function renderTrendCockpit(data = {}) {
  applySharedSnapshotContext(data.shared_snapshot || {});
  state.trendCockpit = data;
  const cardsTarget = $("trendCockpitCards");
  const summaryTarget = $("trendCockpitSummary");
  if (!cardsTarget || !summaryTarget) return;
  const cards = data.cards || [];
  cardsTarget.innerHTML = cards.length ? cards.map((card) => `
    <div class="trend-cockpit-card flat">
      <span>${escapeHtml(card.label || "--")}</span>
      <strong>${escapeHtml(card.value || "--")}</strong>
      <em>${escapeHtml(card.detail || "")}</em>
    </div>
  `).join("") : `<div class="trend-cockpit-card flat"><span>驾驶舱</span><strong>等待走势数据</strong><em>刷新后显示趋势、量能、关键价位和风险。</em></div>`;
  const probabilities = data.probabilities || {};
  summaryTarget.innerHTML = `
    <strong title="${escapeHtml(data.summary || "等待当前标的走势快照")}">${escapeHtml(data.preferred ? `${data.symbol || state.symbol} 走势研究观察：证据与反证并列` : (data.summary || "等待当前标的走势快照"))}</strong>
    <span>安全边界：${escapeHtml(data.safe_action || "观察 / 仅研究 / 仅模拟盘验证")}</span>
    <span>胜率说明：${escapeHtml(probabilities.estimate_note || "当前样本估计，不是保证性结论。")}</span>
  `;
  renderAnomalyDetail(state.selectedAnomaly, data);
  renderMarketWorkflowStrip();
  renderAiRoomHeader();
}

async function loadTrendCockpit(symbol = state.symbol, requestVersion = runtime.symbolVersion) {
  const requestSymbol = symbol || state.symbol;
  const summaryTarget = $("trendCockpitSummary");
  if (summaryTarget) summaryTarget.textContent = `正在生成 ${requestSymbol} 走势驾驶舱...`;
  try {
    const data = await api(`/api/market/trend-cockpit?symbol=${encodeURIComponent(requestSymbol)}`);
    if (requestVersion !== runtime.symbolVersion && requestSymbol === state.symbol) return;
    if (requestSymbol !== state.symbol && state.selectedAnomaly?.symbol !== requestSymbol) return;
    renderTrendCockpit(data);
  } catch (error) {
    if (summaryTarget) summaryTarget.textContent = `走势驾驶舱离线：${error.message}`;
  }
}

function selectAnomaly(symbol) {
  const rows = state.anomalyRadar?.rows || [];
  const eventRows = state.anomalyEvents?.rows || [];
  const selected = rows.find((row) => row.symbol === symbol) || eventRows.find((row) => row.symbol === symbol) || rows[0] || null;
  state.selectedAnomaly = selected;
  document.querySelectorAll(".anomaly-row").forEach((row) => {
    row.classList.toggle("active", row.dataset.symbol === selected?.symbol);
  });
  renderAnomalyDetail(selected, state.trendCockpit);
  if (selected?.symbol) {
    if (state.symbol !== selected.symbol) selectSymbol(selected.symbol);
    loadTrendCockpit(selected.symbol);
    loadAnomalyEvents(selected.symbol, { limit: 40 }).catch(() => {});
    loadAnomalyDetail(selected.symbol).catch(() => {});
  }
}

function renderAnomalyRadar(data = {}) {
  state.anomalyRadar = data;
  const allRows = data.rows || [];
  const rows = anomalyRowsForFilter(allRows);
  const summary = $("anomalyRadarSummary");
  const target = $("anomalyRows");
  const pendingReview = allRows.filter((row) => anomalyNeedsReview(row));
  const topTrusted = allRows.find((row) => !anomalyQuality(row).fallback);
  if (summary) {
    const fallbackSummary = pendingReview.length
      ? `已扫描 ${allRows.length} 个标的；${pendingReview.length} 条高分缓存转入待核。${topTrusted ? `当前最高可复核：${topTrusted.symbol} / ${anomalySeverityLabel(topTrusted)}` : "实时可复核队列等待数据源。"}`
      : (data.summary || "等待雷达扫描。");
    const baseSummary = data.progression?.summary && data.summary ? data.summary : fallbackSummary;
    const filterText = state.anomalyFilter === "changes" ? "新增增强" : state.anomalyFilter === "priority" ? "研究优先队列" : state.anomalyFilter === "review" ? "数据待核" : "";
    const filteredSummary = filterText ? `${baseSummary} / ${filterText} ${rows.length} 条` : baseSummary;
    const quoteBatch = data.quote_batch || data.scanner?.quote_batch || {};
    const batchState = (quoteBatch.source_errors || []).length ? "部分降级" : quoteBatch.cache_hit ? "已复用" : "已更新";
    const batchSummary = Number(quoteBatch.symbol_count || 0) > 0
      ? `轻量快照 ${number(quoteBatch.symbol_count, 0)} 标的 · ${batchState}`
      : "";
    summary.textContent = batchSummary ? `${filteredSummary} / ${batchSummary}` : filteredSummary;
  }
  renderAnomalyCards(normalizeAnomalyCards(data.cards || [], allRows));
  if (!target) return;
  target.innerHTML = rows.length ? rows.map((row) => {
    const evidence = (row.evidence || []).slice(0, 2).join(" / ");
    const change = Number(row.change24h_pct || 0);
    const quality = anomalyQuality(row);
    const priority = anomalyPriority(row);
    const motion = anomalyMotion(row);
    const scoreDelta = motion.comparisonAvailable ? `评分 ${motion.scoreDelta >= 0 ? "+" : ""}${number(motion.scoreDelta, 1)}` : "等待下轮对比";
    const next = row.next_observation || (row.waiting_conditions || [])[0] || evidence || row.safe_action || "--";
    return `
      <button class="anomaly-row ${row.symbol === state.selectedAnomaly?.symbol ? "active" : ""}" data-symbol="${escapeHtml(row.symbol)}">
        <span class="flat"><strong>${escapeHtml(priority.label || "--")}</strong><em>${escapeHtml(quality.label || "--")} · ${escapeHtml(motion.label)}</em></span>
        <span><strong>${escapeHtml(row.symbol)}</strong><em>${escapeHtml(row.market_type || "--")} / ${escapeHtml(anomalySeverityLabel(row))}</em></span>
        <span class="flat"><strong>${number(row.score || 0, 1)}</strong><em>${escapeHtml(scoreDelta)}</em></span>
        <span class="flat">${escapeHtml(anomalyDirectionLabel(row))} ${change >= 0 ? "+" : ""}${number(change, 2)}%</span>
        <span><strong>${escapeHtml(row.theme || row.reason || "--")}</strong><em>${escapeHtml(row.reason || "--")}</em></span>
        <span><strong>${escapeHtml(next)}</strong><em>${escapeHtml(evidence || row.safe_action || "--")}</em></span>
      </button>
    `;
  }).join("") : `<div class="anomaly-empty">当前筛选没有匹配项；可切回“全部”查看完整雷达。</div>`;
  target.querySelectorAll(".anomaly-row").forEach((row) => {
    row.addEventListener("click", () => selectAnomaly(row.dataset.symbol));
  });
  const next = rows.find((row) => row.symbol === state.symbol) || rows[0] || null;
  const activeSymbolHasRow = Boolean(next && next.symbol === state.symbol);
  if (next && (activeSymbolHasRow && state.selectedAnomaly?.symbol !== state.symbol
    || !state.selectedAnomaly
    || !rows.some((row) => row.symbol === state.selectedAnomaly.symbol))) {
    state.selectedAnomaly = next;
    if (state.anomalyDetail?.symbol !== next.symbol) state.anomalyDetail = null;
    target.querySelectorAll(".anomaly-row").forEach((row) => row.classList.toggle("active", row.dataset.symbol === next.symbol));
  }
  renderAnomalyDetail(state.selectedAnomaly, state.trendCockpit);
  renderMarketWorkflowStrip();
  renderAiRoomHeader();
}

async function loadAnomalyRadar(writeNotification = false, requestVersion = runtime.symbolVersion, options = {}) {
  const summary = $("anomalyRadarSummary");
  const hasRows = Boolean(state.anomalyRadar?.rows?.length);
  const background = Boolean(options.background || hasRows);
  const force = Boolean(options.force || writeNotification);
  if (!force && runtime.anomalyRadarInFlight) return;
  if (!force && state.anomalyRadar && Date.now() - Number(runtime.anomalyRadarAt || 0) < 45000) {
    renderAnomalyRadar(state.anomalyRadar);
    return;
  }
  if (summary) {
    summary.textContent = writeNotification
      ? "正在写入异动提醒..."
      : background
        ? "后台刷新异动雷达，保留当前列表..."
        : "正在扫描市场异动...";
  }
  runtime.anomalyRadarInFlight = true;
  try {
    const data = await api(`/api/market/anomaly-radar?notify=${writeNotification ? "true" : "false"}&force=${force ? "true" : "false"}`);
    if (requestVersion !== runtime.symbolVersion && !writeNotification) return;
    runtime.anomalyRadarAt = Date.now();
    renderAnomalyRadar(data);
    loadAnomalyEvents("", { limit: 80 }).catch(() => {});
    if (state.selectedAnomaly?.symbol) loadAnomalyDetail(state.selectedAnomaly.symbol, requestVersion).catch(() => {});
    if (writeNotification) await loadProfile();
  } catch (error) {
    if (summary && !hasRows) summary.textContent = `异动雷达离线：${error.message}`;
  } finally {
    runtime.anomalyRadarInFlight = false;
  }
}

function openAnomalyPromptInAi() {
  const row = state.selectedAnomaly;
  const trend = state.trendCockpit;
  const prompt = trend?.ai_prompt || {};
  const question = prompt.user_prompt
    ? `请基于以下结构化异动数据做研究员会议复核，明确证据、反证、多空概率估计、关键位置和等待条件。${prompt.safety_notice || "仅研究 / 仅模拟盘验证"}\n${prompt.user_prompt}`
    : `请分析${row?.symbol || state.symbol}当前异动，分别整理多头证据、空头证据、反证、关键位置和等待条件。只做研究纪要，不输出实盘指令。`;
  if ($("marketAiQuestion")) $("marketAiQuestion").value = question;
  if ($("aiRoomQuestionInput")) $("aiRoomQuestionInput").value = question;
  setInterfaceView("marketai");
  setTimeout(() => {
    renderMarketAiLocal();
    $("marketAiState").textContent = "已带入异动雷达证据链";
    const roomInput = $("aiRoomQuestionInput");
    roomInput?.scrollIntoView({ behavior: "smooth", block: "center" });
    roomInput?.focus({ preventScroll: true });
  }, 0);
}

function researchStatusTone(status) {
  if (status === "PASS") return "up";
  if (status === "BLOCK") return "down";
  return "flat";
}

function openResearchPromptInAi(prompt = "") {
  const question = prompt || state.research?.focus?.prompts?.[0] || `请分析当前${state.symbol}的多空胜率和止盈止损。`;
  if ($("marketAiQuestion")) $("marketAiQuestion").value = question;
  if ($("aiRoomQuestionInput")) $("aiRoomQuestionInput").value = question;
  setInterfaceView("marketai");
  setTimeout(() => {
    renderMarketAiLocal();
    $("marketAiState").textContent = "已带入研究问题";
    const roomInput = $("aiRoomQuestionInput");
    roomInput?.scrollIntoView({ behavior: "smooth", block: "center" });
    roomInput?.focus({ preventScroll: true });
  }, 0);
}

function renderResearchFocus(focus = {}) {
  const panel = $("researchFocusPanel");
  if (!panel) return;
  const cards = focus.cards || [];
  $("researchFocusTitle").textContent = `${focus.symbol || state.symbol} 研究档案`;
  $("researchFocusBrief").textContent = focus.summary || "等待市场情报、K线和AI研究快照。";
  $("researchFocusCards").innerHTML = cards.length ? cards.map((card) => `
    <div class="research-focus-card ${card.tone || "flat"}">
      <span>${escapeHtml(card.label || "--")}</span>
      <strong>${escapeHtml(card.value || "--")}</strong>
      <em>${escapeHtml(card.detail || "")}</em>
    </div>
  `).join("") : `<div class="research-focus-card flat"><span>研究档案</span><strong>等待数据</strong><em>刷新研究面板后生成</em></div>`;

  $("researchChecklistRows").innerHTML = (focus.checklist || []).map((row) => `
    <div class="research-check-row ${researchStatusTone(row.status)}">
      <span>${escapeHtml(row.priority || "P2")}</span>
      <strong>${escapeHtml(row.name || "--")}</strong>
      <em>${escapeHtml(row.status || "WATCH")}</em>
      <small>${escapeHtml(row.detail || "--")}</small>
    </div>
  `).join("") || `<div class="research-check-row flat"><span>P2</span><strong>等待检查项</strong><em>WATCH</em><small>刷新研究面板</small></div>`;

  $("researchPromptRows").innerHTML = (focus.prompts || []).map((prompt) => `
    <button class="research-prompt" data-research-prompt="${escapeHtml(prompt)}">${escapeHtml(prompt)}</button>
  `).join("") || `<button class="research-prompt" data-research-prompt="请分析当前${escapeHtml(state.symbol)}的多空胜率和止盈止损。">生成当前标的AI问题</button>`;

  document.querySelectorAll("[data-research-prompt]").forEach((button) => {
    button.addEventListener("click", () => openResearchPromptInAi(button.dataset.researchPrompt || ""));
  });
}

function researchItemText(item = {}) {
  const symbol = item.symbol || item.label || "--";
  const value = item.value ? ` ${item.value}` : "";
  const change = Number(item.change24h_pct);
  const changeText = Number.isFinite(change) && Math.abs(change) < 20
    ? ` ${change >= 0 ? "+" : ""}${number(change, 1)}%`
    : "";
  const reason = item.reason || item.name || item.sector || "";
  return `${symbol}${value || changeText}${reason ? ` · ${reason}` : ""}`;
}

function stockRowTone(row = {}) {
  if (row.tone) return row.tone;
  const change = Number(row.change_pct ?? row.change24h_pct ?? row.gap_pct ?? 0);
  if (Number.isFinite(change) && change > 0) return "up";
  if (Number.isFinite(change) && change < 0) return "down";
  return "flat";
}

function renderStockResearchRows(targetId, rows = [], renderer) {
  const target = $(targetId);
  if (!target) return;
  target.innerHTML = rows.length ? rows.map((row) => renderer(row)).join("") : `
    <div class="stock-research-row flat">
      <strong>等待数据</strong>
      <span>当前数据源暂未返回该模块内容。</span>
      <em>仅研究 / 仅模拟验证</em>
    </div>
  `;
}

function normalizeStockResearchLabels(panel) {
  if (!panel) return;
  const heading = panel.querySelector(".stock-research-head strong");
  if (heading) heading.textContent = "股票专项研究";
  if ($("stockResearchMode")) $("stockResearchMode").textContent = "仅研究 / 仅模拟验证";
  const titles = panel.querySelectorAll(".stock-research-grid .research-title");
  ["盘前 / 盘中 / 盘后", "财报 / 估值 / 风险", "行业联动", "异常成交"].forEach((label, index) => {
    if (titles[index]) titles[index].textContent = label;
  });
}

function stockBriefTone(value, flat = 0) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "flat";
  if (numeric > flat) return "up";
  if (numeric < flat) return "down";
  return "flat";
}

function renderStockResearchBrief(data = {}, stock = {}) {
  const target = $("stockResearchBriefCards");
  const thesis = $("stockResearchThesis");
  if (!target && !thesis) return;
  const meta = stock.meta || {};
  const quote = stock.quote || {};
  const session = stock.session || {};
  const unusual = stock.unusual || {};
  const linkage = stock.linkage || {};
  const industryChain = stock.industry_chain || {};
  const dailySwing = stock.daily_swing || {};
  const newsCount = (data.news || []).length;
  const eventCount = (stock.calendar || data.events || []).length;
  const asyncReady = data.async_research?.news_calendar === "ready" || state.stockAsyncResearch?.symbol === (meta.symbol || data.symbol) && state.stockAsyncResearch?.status === "ready";
  const asyncPending = data.async_research?.news_calendar === "pending" || state.stockAsyncResearch?.symbol === (meta.symbol || data.symbol) && state.stockAsyncResearch?.status === "loading";
  const peerRows = linkage.rows || [];
  const chainSegments = industryChain.segments || [];
  const upCount = peerRows.filter((row) => Number(row.change24h_pct || 0) > 0).length;
  const downCount = peerRows.filter((row) => Number(row.change24h_pct || 0) < 0).length;
  const price = Number(quote.last || 0);
  const change = Number(quote.change24h_pct || 0);
  const volumeRatio = Number(unusual.volume_ratio || 1);
  const chainChange = Number(industryChain.avg_change_pct ?? linkage.avg_change_pct ?? 0);
  const chainLead = chainSegments[0];
  const dailyTone = dailySwing.tone || (String(dailySwing.stage || "").includes("上升") ? "up" : String(dailySwing.stage || "").includes("下降") ? "down" : "flat");
  if (price > 0) {
    updateMarketFromTicker({ ...quote, symbol: meta.symbol || data.symbol || state.symbol, instId: quote.instId || meta.symbol || state.symbol });
    scheduleMarketRender(true);
  }
  const cards = [
    { label: "当前价格", value: price ? number(price, price > 100 ? 2 : 4) : "--", detail: `${change >= 0 ? "+" : ""}${number(change, 2)}% / ${quote.source || session.source || "stock"}`, tone: stockBriefTone(change) },
    { label: "日线波段", value: dailySwing.stage || "等待", detail: dailySwing.summary || "等待日线缓存", tone: dailyTone },
    { label: "股票新闻", value: asyncPending ? "异步中" : String(newsCount), detail: asyncReady ? "公司/市场新闻已补全" : "首屏本地摘要，外部新闻异步补全", tone: asyncReady ? "up" : "flat" },
    { label: "财报事件", value: asyncPending ? "异步中" : String(eventCount), detail: asyncReady ? "财报、估值、评级和风险已补全" : "财报日历异步加载，不阻塞首屏", tone: asyncReady ? "up" : "flat" },
    { label: "同业联动", value: `${upCount}涨/${downCount}跌`, detail: linkage.summary || meta.sector || "等待同组确认", tone: stockBriefTone(Number(linkage.avg_change_pct || 0)) },
    { label: "产业链", value: `${chainChange >= 0 ? "+" : ""}${number(chainChange, 2)}%`, detail: chainLead ? `${chainLead.role || chainLead.sector || "强段"} ${Number(chainLead.avg_change_pct || 0) >= 0 ? "+" : ""}${number(Number(chainLead.avg_change_pct || 0), 2)}%` : industryChain.summary || "等待上下游拆分", tone: stockBriefTone(chainChange) },
    { label: "异常成交", value: `${number(volumeRatio, 2)}x`, detail: unusual.headline || "观察量比、跳空、振幅", tone: (unusual.flags || []).length ? "up" : "flat" },
  ];
  if (target) {
    target.innerHTML = cards.map((card) => `
      <div class="stock-research-brief-card ${card.tone || "flat"}">
        <span>${escapeHtml(card.label)}</span>
        <strong>${escapeHtml(card.value)}</strong>
        <em>${escapeHtml(card.detail)}</em>
      </div>
    `).join("");
  }
  if (thesis) {
    thesis.textContent = `${meta.symbol || data.symbol || state.symbol} · ${meta.name || "--"} · ${meta.sector || "Stock"}。当前结论只用于观察和模拟验证：先看日线波段结构，再看新闻/财报催化、盘前盘后、同业和上下游链条是否同步，最后用异常成交和K线确认。`;
  }
}

function stockSessionMove(rows = [], keys = []) {
  return rows.find((row) => keys.includes(row.session) && Number.isFinite(Number(row.change_pct)));
}

function stockResearchBulletList(items = []) {
  return items.slice(0, 4).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function mergeStockQuality(base = {}, incoming = {}) {
  const baseCards = Array.isArray(base.cards) ? base.cards : [];
  const incomingCards = Array.isArray(incoming.cards) ? incoming.cards : [];
  const merged = new Map();
  baseCards.forEach((card) => merged.set(card.key || card.label, card));
  incomingCards.forEach((card) => merged.set(card.key || card.label, card));
  return {
    ...base,
    ...incoming,
    cards: Array.from(merged.values()),
    summary: incoming.summary || base.summary || "",
    source: incoming.source || base.source || "",
    updated_at: incoming.updated_at || base.updated_at || Date.now(),
  };
}

function stockResearchQualitySnapshot(data = {}, stock = {}) {
  const symbol = stock.meta?.symbol || data.symbol || state.symbol;
  const asyncQuality = state.stockAsyncResearch?.symbol === symbol && state.stockAsyncResearch?.status === "ready"
    ? state.stockAsyncResearch.data?.data_quality || {}
    : {};
  const quality = mergeStockQuality(stock.quality || data.data_quality || {}, asyncQuality);
  const cards = (quality.cards || []).length ? quality.cards : stockQualityFallbackCards(stock);
  return { symbol, quality, cards };
}

function stockQualityFallbackCards(stock = {}) {
  const quote = stock.quote || {};
  const session = stock.session || {};
  const daily = stock.daily_swing || {};
  const source = quote.source || session.source || daily.source || "stock";
  return [
    { key: "quote", label: "报价", status: "WATCH", value: source, detail: quote.time || session.latest_at || "等待报价时间", tone: "flat" },
    { key: "daily", label: "日线", status: daily.ok ? "READY" : "WAIT", value: daily.source || "daily", detail: daily.summary || "等待日线缓存", tone: daily.tone || "flat" },
    { key: "session", label: "盘前盘后", status: "WATCH", value: session.source || "session", detail: session.latest_at || "等待分时缓存", tone: "flat" },
    { key: "news", label: "新闻", status: "WAIT", value: "本地摘要", detail: "等待异步新闻补全", tone: "flat" },
    { key: "calendar", label: "财报事件", status: "WAIT", value: "本地框架", detail: "等待外部财报日历", tone: "flat" },
  ];
}

function stockQualityCardNeedsRefresh(card = {}) {
  const status = String(card.status || "").toUpperCase();
  const text = `${card.key || ""} ${card.label || ""} ${card.value || ""} ${card.detail || ""}`.toLowerCase();
  if (status === "OLD_CACHE" || status === "SEED") return true;
  if (text.includes("旧缓存") || text.includes("stale stock") || text.includes("behind current session")) return true;
  return (card.key === "quote" || card.label === "报价") && text.includes("stock_sqlite_cache");
}

function chartQualityNeedsStockRefresh(quality = state.chartQuality, symbol = state.symbol) {
  if (!isStockMarket(symbol) || !quality) return false;
  const source = String(quality.source || "").toLowerCase();
  const text = `${quality.mode || ""} ${quality.sourceText || ""} ${quality.warningText || ""}`.toLowerCase();
  return quality.mode === "旧缓存"
    || source === "stock_sqlite_cache"
    || text.includes("旧缓存")
    || text.includes("stale stock")
    || text.includes("behind current session");
}

function stockStaleReasons(data = {}, stock = {}) {
  if (data.mode !== "stock_research" || !stock) return { symbol: state.symbol, reasons: [] };
  const { symbol, cards } = stockResearchQualitySnapshot(data, stock);
  const reasons = cards
    .filter(stockQualityCardNeedsRefresh)
    .map((card) => `${card.label || card.key || "数据"} ${card.status || ""}`.trim());
  if (symbol === state.symbol && chartQualityNeedsStockRefresh(state.chartQuality, symbol)) {
    reasons.push(`K线 ${state.chartQuality?.mode || "旧缓存"}`);
  }
  return { symbol, reasons: Array.from(new Set(reasons)).slice(0, 4) };
}

function stockStaleRefreshKey(symbol = state.symbol, bar = state.bar, session = state.stockSession) {
  return window.HakimiChartController.inFlightKey({
    requestSymbol: symbol,
    requestBar: bar,
    requestSession: session,
  });
}

function renderStockStaleAlert(data = state.research || {}, stock = data.stock || {}) {
  const target = $("stockStaleAlert");
  if (!target) return;
  if (data.mode !== "stock_research" || !stock) {
    target.className = "stock-stale-alert hidden";
    target.innerHTML = "";
    return;
  }
  const { symbol, reasons } = stockStaleReasons(data, stock);
  const status = runtime.stockStaleRefreshStatus[stockStaleRefreshKey(symbol)] || {};
  const recent = status.at && Date.now() - Number(status.at) < 18_000;
  const refreshing = status.state === "refreshing";
  const show = reasons.length || refreshing || status.state === "error" || recent;
  if (!show) {
    target.className = "stock-stale-alert hidden";
    target.innerHTML = "";
    return;
  }
  const tone = refreshing ? "flat" : status.state === "error" ? "down" : reasons.length ? "down" : "up";
  const title = refreshing
    ? `${symbol} 正在刷新行情源`
    : reasons.length
      ? `${symbol} 检测到旧行情/旧缓存`
      : `${symbol} 行情刷新已完成`;
  const detail = refreshing
    ? (status.detail || "正在强制刷新报价、K线和数据源总控。")
    : status.state === "error"
      ? (status.detail || "刷新失败，继续显示缓存并保留风险提示。")
      : reasons.length
        ? `${reasons.join(" / ")}。正在后台尝试拉取 Futu、Yahoo、Stooq；所有结论仅研究。`
        : (status.detail || "报价、K线和研究卡片已重新检查。");
  target.className = `stock-stale-alert ${tone}`;
  target.innerHTML = `
    <div>
      <strong>${escapeHtml(title)}</strong>
      <span>${escapeHtml(detail)}</span>
    </div>
    <button type="button" data-stock-stale-refresh="${escapeHtml(symbol)}" ${refreshing ? "disabled" : ""}>立即刷新</button>
  `;
  const button = target.querySelector("[data-stock-stale-refresh]");
  if (button) {
    button.addEventListener("click", () => {
      refreshStaleStockData(symbol, "manual", { auto: false }).catch(() => {});
    });
  }
}

function maybeAutoRefreshStockResearch(data = state.research || {}, stock = data.stock || {}) {
  const { symbol, reasons } = stockStaleReasons(data, stock);
  if (!reasons.length || symbol !== state.symbol) return;
  refreshStaleStockData(symbol, "research_quality", { auto: true }).catch(() => {});
}

function maybeAutoRefreshChartStale(quality = state.chartQuality) {
  const symbol = quality?.symbol || state.symbol;
  if (!chartQualityNeedsStockRefresh(quality, symbol) || symbol !== state.symbol) return;
  refreshStaleStockData(symbol, "chart_quality", { auto: true }).catch(() => {});
}

function syncStockResearchQuoteToHeader(stock = {}) {
  const quote = stock.quote || {};
  const symbol = quote.symbol || stock.meta?.symbol || state.symbol;
  const last = Number(quote.last);
  if (!isStockMarket(symbol) || symbol !== state.symbol || !Number.isFinite(last) || last <= 0) return;
  const source = String(quote.source || "").toLowerCase();
  const ageMs = Number(quote.data_age_ms || 0);
  const oldLocalCache = source === "stock_sqlite_cache" && ageMs > 12 * 60 * 60 * 1000;
  const seedLike = source.includes("seed") || source.includes("offline");
  if (oldLocalCache || seedLike) return;
  const current = Number(state.lastPrice || 0);
  const currentChange = Number(currentMarket(symbol).rawChange || 0);
  const quoteChange = Number(quote.change24h_pct || 0);
  const changed = !Number.isFinite(current) || current <= 0 || Math.abs(current - last) / Math.max(last, 1e-9) > 0.0005;
  const changeChanged = Number.isFinite(quoteChange) && Math.abs(currentChange - quoteChange) > 0.25;
  if (!changed && !changeChanged && state.futu?.last_stock_source === source.toUpperCase()) return;
  updateTicker({ ...quote, symbol, instId: quote.instId || symbol, ts: quote.ts || Date.now() }, source.toUpperCase() || "STOCK");
}

async function refreshStaleStockData(symbol = state.symbol, reason = "old_cache", options = {}) {
  if (!isStockMarket(symbol)) return null;
  const requestSymbol = symbol;
  const requestBar = state.bar;
  const requestSession = state.stockSession;
  const requestVersion = runtime.symbolVersion;
  const key = stockStaleRefreshKey(requestSymbol, requestBar, requestSession);
  const now = Date.now();
  const auto = options.auto !== false;
  if (runtime.stockStaleRefreshInFlight.has(key)) return null;
  if (auto && now - Number(runtime.stockStaleRefreshAt[key] || 0) < 60_000) return null;
  runtime.stockStaleRefreshAt[key] = now;
  runtime.stockStaleRefreshInFlight.add(key);
  runtime.stockStaleRefreshStatus[key] = {
    state: "refreshing",
    detail: "正在强制刷新报价、K线和数据源总控。",
    reason,
    at: now,
  };
  renderStockStaleAlert(state.research || {}, state.research?.stock || {});

  const cacheKey = chartCacheKey(requestSymbol, requestBar, requestSession);
  const quotePath = `/api/stocks/quote?symbol=${encodeURIComponent(requestSymbol)}&force=true&ts=${now}`;
  const sourcePath = `/api/stocks/source-control?symbol=${encodeURIComponent(requestSymbol)}&interval=${encodeURIComponent(stockIntervalForBar(requestBar))}&session=${encodeURIComponent(requestSession)}&force=true&ts=${now}`;

  try {
    const [snapshotResult, sourceResult] = await Promise.allSettled([
      refreshSnapshotCandlesInBackground({
        requestVersion,
        requestSymbol,
        requestBar,
        requestSession,
        limit: marketSnapshotLimit(requestSymbol, requestBar),
        cacheKey,
        manual: !auto,
        reason,
        throwOnError: true,
      }),
      api(sourcePath),
    ]);
    let quoteResult = null;
    if (snapshotResult.status === "rejected") {
      try {
        quoteResult = await api(quotePath);
        if (chartRefreshTargetIsCurrent({ requestSymbol, requestBar, requestSession })) {
          updateTicker(quoteResult.quote, String(quoteResult.quote?.source || "STOCK").toUpperCase());
        }
      } catch (error) {
        quoteResult = null;
      }
    }
    if (chartRefreshTargetIsCurrent({ requestSymbol, requestBar, requestSession }) && sourceResult.status === "fulfilled") {
      renderStockSourceControl(sourceResult.value);
    }
    const refreshResult = snapshotResult.status === "fulfilled" ? snapshotResult.value : null;
    const snapshot = refreshResult?.data || null;
    const cooldown = refreshResult?.outcome?.status === "COOLDOWN";
    const sourceName = snapshot?.source?.primary || snapshot?.candles?.source || quoteResult?.quote?.source || "stock";
    const mode = snapshot?.data_quality?.status || (cooldown ? "RECENT_REFRESH" : "WATCH");
    const warning = snapshot?.source?.degradation_reason || snapshot?.candles?.warning || "";
    runtime.stockStaleRefreshStatus[key] = {
      state: snapshotResult.status === "rejected" ? "error" : snapshot && !marketSnapshotNeedsRefresh(snapshot) ? "ready" : "watch",
      detail: snapshotResult.status === "rejected"
        ? `K线刷新失败：${snapshotResult.reason?.message || "unknown"}`
        : cooldown
          ? "同键行情最近已刷新，自动请求处于冷却期。"
          : `${sourceName} / ${mode}${warning ? ` / ${warning}` : ""}`,
      reason,
      at: Date.now(),
    };
    if (snapshotResult.status === "rejected") runtime.stockStaleRefreshAt[key] = Date.now() - 45_000;
    if (chartRefreshTargetIsCurrent({ requestSymbol, requestBar, requestSession })) {
      renderStockStaleAlert(state.research || {}, state.research?.stock || {});
      if (Date.now() - Number(runtime.stockStaleResearchReloadAt || 0) > 3500) {
        runtime.stockStaleResearchReloadAt = Date.now();
        await loadResearchPanel(requestVersion).catch(() => null);
      }
    }
    return snapshot;
  } catch (error) {
    runtime.stockStaleRefreshAt[key] = Date.now() - 45_000;
    runtime.stockStaleRefreshStatus[key] = {
      state: "error",
      detail: `刷新失败：${error.message}`,
      reason,
      at: Date.now(),
    };
    if (chartRefreshTargetIsCurrent({ requestSymbol, requestBar, requestSession })) {
      renderStockStaleAlert(state.research || {}, state.research?.stock || {});
    }
    return null;
  } finally {
    runtime.stockStaleRefreshInFlight.delete(key);
  }
}

function renderStockDataQuality(data = {}, stock = {}) {
  const target = $("stockQualityRows");
  if (!target) return;
  if (data.mode !== "stock_research" || !stock) {
    target.innerHTML = "";
    return;
  }
  const { quality, cards } = stockResearchQualitySnapshot(data, stock);
  target.innerHTML = cards.slice(0, 6).map((card) => `
    <div class="stock-quality-card ${card.tone || "flat"}">
      <div class="stock-quality-head">
        <span>${escapeHtml(card.label || "--")}</span>
        <strong>${escapeHtml(card.value || "--")}</strong>
      </div>
      <em>${escapeHtml(card.status || "WATCH")}</em>
      <p>${escapeHtml(card.detail || quality.summary || "仅研究观察。")}</p>
    </div>
  `).join("");
}

function stockCatalystSessionSummary(session = {}) {
  const rows = session.rows || [];
  const ready = rows.filter((row) => row.status === "READY");
  const changes = ready.map((row) => Number(row.change_pct || 0)).filter((value) => Number.isFinite(value));
  const tone = changes.some((value) => value > 0.4) ? "up" : changes.some((value) => value < -0.4) ? "down" : "flat";
  return {
    value: `${ready.length}/${rows.length || 4} READY`,
    detail: ready.slice(0, 3).map((row) => `${row.label || row.session || "--"} ${number(Number(row.change_pct || 0), 2)}%`).join(" / ") || "等待盘前/盘中/盘后样本",
    tone,
  };
}

function stockDailySwingFallbackCards(stock = {}) {
  const quote = stock.quote || {};
  const unusual = stock.unusual || {};
  const change = Number(quote.change24h_pct || unusual.change_pct || 0);
  const volumeRatio = Number(unusual.volume_ratio || 1);
  const tone = change > 0.5 ? "up" : change < -0.5 ? "down" : "flat";
  return [
    { label: "日线阶段", value: "等待缓存", detail: `当日 ${change >= 0 ? "+" : ""}${number(change, 2)}%`, tone },
    { label: "压力区", value: "--", detail: "等待日线高点", tone: "flat" },
    { label: "支撑区", value: "--", detail: "等待日线低点", tone: "flat" },
    { label: "均线结构", value: "等待", detail: "需要MA20/MA50", tone: "flat" },
    { label: "量能确认", value: `${number(volumeRatio, 2)}x`, detail: "等待20日均量", tone: volumeRatio >= 1.35 ? "up" : volumeRatio <= 0.75 ? "down" : "flat" },
  ];
}

function applyStockCandleQualityNotice(daily = {}) {
  const quality = daily.data_quality || {};
  if (!quality.has_break || !quality.warning) return;
  const warning = `${quality.warning} 图表使用临时连续视图；波段结论暂停。`;
  const warningTarget = $("chartQualityWarning");
  if (warningTarget) warningTarget.textContent = warning;
  const strip = $("chartQualityStrip");
  if (strip) strip.className = "chart-quality-strip down";
  const status = $("chartStatus");
  if (status && !status.textContent.includes("日线尺度待核")) status.textContent = `${status.textContent} / 日线尺度待核`;
  const liveState = $("liveCandleState");
  const liveDetail = $("liveCandleDetail");
  if (liveState) liveState.textContent = "待核";
  if (liveDetail) liveDetail.textContent = "实时报价可用；历史日线复权尺度待核";
}

function renderStockDailySwing(data = {}, stock = {}) {
  const target = $("stockDailySwingRows");
  if (!target) return;
  if (data.mode !== "stock_research" || !stock) {
    target.innerHTML = "";
    return;
  }
  const daily = stock.daily_swing || {};
  applyStockCandleQualityNotice(daily);
  const cards = (daily.cards || []).length ? daily.cards : stockDailySwingFallbackCards(stock);
  const waiting = daily.waiting_conditions || [];
  target.innerHTML = cards.slice(0, 5).map((card, index) => {
    const footer = index === 0
      ? daily.safe_action || "观察 / 仅研究"
      : index === 4
        ? (waiting[0] || "等待日线收盘确认。")
        : daily.latest_at || daily.source || "本地日线缓存";
    return `
      <div class="stock-daily-card ${card.tone || "flat"}">
        <div class="stock-daily-head">
          <span>${escapeHtml(card.label || "--")}</span>
          <strong>${escapeHtml(card.value || "--")}</strong>
        </div>
        <em>${escapeHtml(card.detail || daily.summary || "--")}</em>
        <small>${escapeHtml(footer)}</small>
      </div>
    `;
  }).join("");
}

function stockCatalystFallbackRows(data = {}, stock = {}) {
  const meta = stock.meta || {};
  const quote = stock.quote || {};
  const session = stock.session || {};
  const unusual = stock.unusual || {};
  const linkage = stock.linkage || {};
  const industryChain = stock.industry_chain || {};
  const calendarRows = stock.calendar || data.events || [];
  const newsRows = data.news || [];
  const sessionSummary = stockCatalystSessionSummary(session);
  const priceChange = Number(quote.change24h_pct || 0);
  const chainChange = Number(industryChain.avg_change_pct ?? linkage.avg_change_pct ?? 0);
  const volumeRatio = Number(unusual.volume_ratio || 1);
  const gapPct = Number(unusual.gap_pct || 0);
  const rangePct = Number(unusual.range_pct || 0);
  const quality = state.chartQuality || {};
  return [
    {
      key: "earnings_news",
      label: "财报 / 新闻",
      status: newsRows.length || calendarRows.length ? "READY" : "WAIT",
      value: `${newsRows.length}新闻 / ${calendarRows.length}事件`,
      detail: `${calendarRows[0]?.title || "等待财报日历"} / ${newsRows[0]?.title || "等待股票新闻源"}`,
      tone: newsRows.length && calendarRows.length ? "up" : "flat",
      watch: "确认催化是否解释放量、跳空或趋势延续。",
    },
    {
      key: "session_flow",
      label: "盘前 / 盘后",
      status: sessionSummary.value.includes("0/") ? "WAIT" : "READY",
      value: sessionSummary.value,
      detail: sessionSummary.detail,
      tone: sessionSummary.tone,
      watch: "盘前盘后流动性薄，必须等盘中量价确认。",
    },
    {
      key: "industry_chain",
      label: "行业链",
      status: (industryChain.rows || linkage.rows || []).length ? "READY" : "WAIT",
      value: `${chainChange >= 0 ? "+" : ""}${number(chainChange, 2)}%`,
      detail: industryChain.summary || linkage.summary || `${meta.sector || "Stock"} 同业等待确认`,
      tone: chainChange > 0.4 ? "up" : chainChange < -0.4 ? "down" : "flat",
      watch: "同业、上下游、指数分化时降低趋势置信。",
    },
    {
      key: "unusual_trade",
      label: "异常成交",
      status: (unusual.flags || []).length || rangePct >= 3 ? "WATCH" : "CALM",
      value: `${number(volumeRatio, 2)}x`,
      detail: `跳空 ${gapPct >= 0 ? "+" : ""}${number(gapPct, 2)}% / 振幅 ${number(rangePct, 2)}% / 价格 ${priceChange >= 0 ? "+" : ""}${number(priceChange, 2)}%`,
      tone: volumeRatio >= 1.4 && priceChange > 0 ? "up" : volumeRatio >= 1.4 && priceChange < 0 ? "down" : "flat",
      watch: "放量后等第二根K线确认，警惕假突破。",
    },
    {
      key: "data_quality",
      label: "数据质量",
      status: "RESEARCH_ONLY",
      value: quality.mode || quote.source || session.source || "stock",
      detail: `${quality.sourceText || quote.source || session.source || "等待数据源"} / ${quality.freshnessText || session.latest_at || quote.time || "--"}`,
      tone: quality.tone || "flat",
      watch: "Futu离线或旧缓存时只做观察，等待实时源复核。",
    },
  ];
}

function stockChainRoleLabel(sector = "") {
  const text = String(sector || "Stock");
  const roles = {
    "AI Chip": "核心芯片",
    "AI Server": "服务器/整机",
    "Semi Equipment": "设备",
    "Semiconductor Foundry": "代工",
    "Semiconductor Design": "芯片设计",
    "Semiconductor IP": "IP/架构",
    "Memory / Storage": "存储/HBM",
    "Mega Cap Tech": "平台/需求端",
    "EV": "电动化需求",
    "Space / SpaceX proxy": "航天链",
    "HK Power": "电力运营",
    "China Internet": "互联网平台",
    "Smart Hardware": "硬件/终端",
    "Index ETF": "指数环境",
    "BTC Proxy": "加密映射",
  };
  return roles[text] || text || "产业链";
}

function stockChainFallbackSegments(stock = {}) {
  const industryChain = stock.industry_chain || {};
  const linkage = stock.linkage || {};
  const sourceRows = (industryChain.rows || []).length ? industryChain.rows : linkage.rows || [];
  const buckets = new Map();
  sourceRows.forEach((row) => {
    const sector = row.sector || row.reason || linkage.sector || stock.meta?.sector || "Stock";
    const role = row.role || stockChainRoleLabel(sector);
    const key = `${role}|${sector}`;
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key).push(row);
  });
  return Array.from(buckets.values()).map((rows) => {
    const first = rows[0] || {};
    const changes = rows.map((row) => Number(row.change24h_pct || row.change_pct || 0)).filter((value) => Number.isFinite(value));
    const avg = changes.length ? changes.reduce((sum, value) => sum + value, 0) / changes.length : 0;
    const upCount = changes.filter((value) => value > 0).length;
    const downCount = changes.filter((value) => value < 0).length;
    const leaders = rows
      .slice()
      .sort((a, b) => Math.abs(Number(b.change24h_pct || b.change_pct || 0)) - Math.abs(Number(a.change24h_pct || a.change_pct || 0)))
      .slice(0, 4);
    const tone = avg > 0.4 ? "up" : avg < -0.4 ? "down" : "flat";
    return {
      role: first.role || stockChainRoleLabel(first.sector || first.reason || stock.meta?.sector || "Stock"),
      sector: first.sector || linkage.sector || stock.meta?.sector || "Stock",
      avg_change_pct: avg,
      up_count: upCount,
      down_count: downCount,
      count: rows.length,
      tone,
      symbols: leaders.map((row) => row.symbol).filter(Boolean),
      summary: `${first.role || stockChainRoleLabel(first.sector || first.reason || stock.meta?.sector || "Stock")}：${rows.length}样本，${upCount}涨 ${downCount}跌，均值 ${avg >= 0 ? "+" : ""}${number(avg, 2)}%`,
    };
  }).sort((a, b) => Math.abs(Number(b.avg_change_pct || 0)) - Math.abs(Number(a.avg_change_pct || 0)));
}

function renderStockChainMap(data = {}, stock = {}) {
  const target = $("stockChainRows");
  if (!target) return;
  if (data.mode !== "stock_research" || !stock) {
    target.innerHTML = "";
    return;
  }
  const industryChain = stock.industry_chain || {};
  const segments = (industryChain.segments || []).length ? industryChain.segments : stockChainFallbackSegments(stock);
  target.innerHTML = segments.length ? segments.slice(0, 6).map((segment) => {
    const avg = Number(segment.avg_change_pct || 0);
    const symbols = (segment.symbols || []).join(" / ") || "等待样本";
    const tone = segment.tone || (avg > 0.4 ? "up" : avg < -0.4 ? "down" : "flat");
    return `
      <div class="stock-chain-card ${tone}">
        <div class="stock-chain-head">
          <span>${escapeHtml(segment.role || segment.sector || "产业链")}</span>
          <strong>${avg >= 0 ? "+" : ""}${number(avg, 2)}%</strong>
        </div>
        <em>${escapeHtml(`${segment.up_count || 0}涨/${segment.down_count || 0}跌 · ${segment.sector || industryChain.chain_label || "链条样本"}`)}</em>
        <p>${escapeHtml(segment.summary || "观察链条是否同向共振，分化时降低趋势置信。")}</p>
        <small>${escapeHtml(symbols)}</small>
      </div>
    `;
  }).join("") : `
    <div class="stock-chain-card flat">
      <div class="stock-chain-head"><span>产业链拆分</span><strong>等待</strong></div>
      <em>上下游样本未返回</em>
      <p>等待同业、上游、下游和指数样本补齐后再判断共振。</p>
      <small>仅研究 / 仅模拟验证</small>
    </div>
  `;
}

function renderStockCatalystRadar(data = {}, stock = {}) {
  const target = $("stockCatalystRadar");
  if (!target) return;
  if (data.mode !== "stock_research" || !stock) {
    target.innerHTML = "";
    return;
  }
  const catalysts = stock.catalysts || {};
  const rows = (catalysts.rows || []).length ? catalysts.rows : stockCatalystFallbackRows(data, stock);
  const newsCount = (data.news || []).length;
  const eventCount = (stock.calendar || data.events || []).length;
  target.innerHTML = rows.length ? rows.map((row) => {
    const key = row.key || "";
    const value = key === "earnings_news" && (newsCount || eventCount)
      ? `${newsCount}新闻 / ${eventCount}事件`
      : row.value || "--";
    const detail = key === "earnings_news" && state.stockAsyncResearch?.symbol === (stock.meta?.symbol || data.symbol) && state.stockAsyncResearch?.status === "ready"
      ? `${state.stockAsyncResearch.detail} / ${row.watch || ""}`
      : row.detail || row.watch || "--";
    return `
      <div class="stock-catalyst-card ${row.tone || "flat"}">
        <div>
          <span>${escapeHtml(row.label || "--")}</span>
          <strong>${escapeHtml(value)}</strong>
        </div>
        <em>${escapeHtml(row.status || "WATCH")}</em>
        <p>${escapeHtml(detail)}</p>
        <small>${escapeHtml(row.watch || "观察证据，不是下单指令。")}</small>
      </div>
    `;
  }).join("") : `
    <div class="stock-catalyst-card flat">
      <div><span>事件催化</span><strong>等待</strong></div>
      <em>WAIT</em>
      <p>等待财报、新闻、盘前盘后、行业链和异常成交。</p>
      <small>仅研究 / 仅模拟验证</small>
    </div>
  `;
}

function renderStockResearchMemo(data = {}, stock = {}) {
  const target = $("stockResearchMemo");
  if (!target) return;
  if (data.mode !== "stock_research" || !stock) {
    target.innerHTML = "";
    return;
  }
  const meta = stock.meta || {};
  const quote = stock.quote || {};
  const sessionRows = stock.session?.rows || [];
  const unusual = stock.unusual || {};
  const linkage = stock.linkage || {};
  const fundamentals = stock.fundamentals || {};
  const calendarRows = stock.calendar || data.events || [];
  const newsRows = data.news || [];
  const peerRows = linkage.rows || [];
  const priceChange = Number(quote.change24h_pct || 0);
  const peerAvg = Number(linkage.avg_change_pct || 0);
  const volumeRatio = Number(unusual.volume_ratio || 1);
  const gapPct = Number(unusual.gap_pct || 0);
  const rangePct = Number(unusual.range_pct || 0);
  const preMove = stockSessionMove(sessionRows, ["pre"]);
  const postMove = stockSessionMove(sessionRows, ["post", "overnight"]);
  const eventCount = calendarRows.length;
  const newsCount = newsRows.length;
  const quality = state.chartQuality || {};
  const dataRisk = quality.preview || quality.fallback || quality.mode === "旧缓存" || quality.mode === "预览";

  let score = 0;
  if (priceChange > 0.8) score += 1;
  if (priceChange < -0.8) score -= 1;
  if (peerAvg > 0.4) score += 1;
  if (peerAvg < -0.4) score -= 1;
  if (volumeRatio >= 1.4 && priceChange > 0) score += 1;
  if (volumeRatio >= 1.4 && priceChange < 0) score -= 1;
  if (Number(preMove?.change_pct || 0) > 0.4 || Number(postMove?.change_pct || 0) > 0.4) score += 1;
  if (Number(preMove?.change_pct || 0) < -0.4 || Number(postMove?.change_pct || 0) < -0.4) score -= 1;
  if (dataRisk) score -= 1;

  const stance = score >= 2 ? "偏多观察" : score <= -2 ? "偏空观察" : "震荡观察";
  const stanceTone = score >= 2 ? "up" : score <= -2 ? "down" : "flat";
  const longItems = [
    priceChange > 0 ? `价格当日 ${priceChange >= 0 ? "+" : ""}${number(priceChange, 2)}%，短线买盘仍在。` : "",
    peerAvg > 0 ? `${linkage.sector || meta.sector || "同业"} 均值 ${peerAvg >= 0 ? "+" : ""}${number(peerAvg, 2)}%，存在行业联动支持。` : "",
    volumeRatio >= 1.2 ? `成交量约 ${number(volumeRatio, 2)}x，量能高于常态，需要结合K线确认。` : "",
    Number(preMove?.change_pct || 0) > 0 ? `盘前表现 ${number(preMove.change_pct, 2)}%，开盘情绪偏强。` : "",
    newsCount ? `${newsCount} 条新闻/摘要已纳入，催化线索可继续复核。` : "",
  ].filter(Boolean);
  const shortItems = [
    priceChange < 0 ? `价格当日 ${number(priceChange, 2)}%，空头仍有压制。` : "",
    peerAvg < 0 ? `${linkage.sector || meta.sector || "同业"} 均值 ${number(peerAvg, 2)}%，行业分化或同步走弱。` : "",
    Math.abs(gapPct) >= 1.2 ? `跳空 ${gapPct >= 0 ? "+" : ""}${number(gapPct, 2)}%，追涨/抄底都要防回补。` : "",
    rangePct >= 3 ? `日内振幅 ${number(rangePct, 2)}%，假突破和止损滑点风险上升。` : "",
    dataRisk ? `当前K线数据为 ${quality.sourceText || quality.mode || "缓存/兜底"}，不能当实时结论。` : "",
    eventCount ? `财报/估值/风险事件 ${eventCount} 条，事件窗口前后波动可能放大。` : "",
  ].filter(Boolean);
  const waitItems = [
    "等待日线收盘确认，不把盘中波动当成趋势完成。",
    volumeRatio >= 1.2 ? "等待放量后第二根K线确认，避免单日脉冲。" : "等待成交量重新放大或缩量回踩。",
    peerRows.length ? "观察同业是否继续同向，若龙头和上下游分化则降低判断强度。" : "补齐同业联动样本后再提高结论权重。",
    eventCount ? "财报/分红/评级窗口前后只做观察，避免把事件波动误判为趋势。" : "等待外部财报日历和新闻源补全。",
  ];
  const cards = [
    {
      label: "会议结论",
      value: stance,
      detail: `规则分 ${score} / ${data.safe_action || "观察 / 仅研究"}`,
      tone: stanceTone,
      items: [
        `${meta.symbol || data.symbol || state.symbol} 当前先按${stance}处理。`,
        "这不是下单建议，只是研究会议纪要。",
      ],
    },
    {
      label: "多头证据",
      value: longItems.length ? `${longItems.length} 条` : "不足",
      detail: "价格、量能、同业、盘前盘后",
      tone: longItems.length >= 2 ? "up" : "flat",
      items: longItems.length ? longItems : ["暂未形成足够多头证据，等待价格和行业同步确认。"],
    },
    {
      label: "空头反证",
      value: shortItems.length ? `${shortItems.length} 条` : "较少",
      detail: "事件、跳空、振幅、数据风险",
      tone: shortItems.length >= 2 ? "down" : "flat",
      items: shortItems.length ? shortItems : ["暂未看到明显空头反证，但仍需防假突破和旧缓存误导。"],
    },
    {
      label: "等待条件",
      value: "观察清单",
      detail: "只用于研究和模拟验证",
      tone: "flat",
      items: waitItems,
    },
  ];
  target.innerHTML = cards.map((card) => `
    <div class="stock-research-memo-card ${card.tone || "flat"}">
      <div class="stock-research-memo-head">
        <span>${escapeHtml(card.label)}</span>
        <strong>${escapeHtml(card.value)}</strong>
      </div>
      <em>${escapeHtml(card.detail)}</em>
      <ul>${stockResearchBulletList(card.items)}</ul>
    </div>
  `).join("");
}

function resetResearchPanelForSymbol(symbol = state.symbol) {
  const stock = isStockMarket(symbol);
  state.research = null;
  state.stockAsyncResearch = stock ? { symbol, status: "loading", detail: "外部新闻和财报日历异步加载中" } : null;
  renderLiveSourceBar();
  if ($("researchSummary")) $("researchSummary").textContent = stock ? `${symbol} 股票研究加载中...` : `${symbol} 行情研究加载中...`;
  if ($("researchNewsRows")) $("researchNewsRows").innerHTML = `<div class="research-row"><strong>${escapeHtml(symbol)}</strong><span>正在刷新新闻和研究摘要...</span></div>`;
  if ($("researchEventRows")) $("researchEventRows").innerHTML = `<div class="research-row"><strong>${escapeHtml(symbol)}</strong><span>正在刷新事件、风险和关键观察项...</span></div>`;
  if ($("researchMoverRows")) $("researchMoverRows").innerHTML = `<div class="research-row"><strong>${escapeHtml(symbol)}</strong><span>正在刷新异动、涨跌幅和成交额...</span></div>`;
  renderResearchFocus({
    symbol,
    summary: `${symbol} 正在刷新研究档案`,
    cards: [
      { label: stock ? "股票研究" : "行情研究", value: "加载中", detail: "先清空旧内容，等待当前标的数据回填", tone: "flat" },
    ],
    checklist: [
      { name: "当前标的", status: "WATCH", detail: `${symbol} 数据刷新中`, priority: "P0" },
      { name: "真实下单墙", status: "PASS", detail: "本页仅研究 / 仅模拟验证", priority: "P0" },
    ],
    prompts: [
      `请分析当前${symbol}的走势结构、成交量、关键价位和等待条件。`,
    ],
  });
  if (!stock) {
    renderStockResearchPanel({ mode: "market_research", symbol });
    renderStockEvidencePanel({ ok: false, symbol });
    renderLiveSourceBar();
    return;
  }
  const panel = $("stockResearchPanel");
  if (panel) panel.classList.remove("hidden");
  normalizeStockResearchLabels(panel);
  if ($("stockResearchSummary")) $("stockResearchSummary").textContent = `${symbol} / 股票专项研究加载中 / 仅研究`;
  if ($("stockResearchBriefCards")) $("stockResearchBriefCards").innerHTML = `
    <div class="stock-research-brief-card flat">
      <span>研究摘要</span>
      <strong>加载中</strong>
      <em>等待价格、新闻、财报、联动和异常成交。</em>
    </div>
  `;
  if ($("stockResearchThesis")) $("stockResearchThesis").textContent = `${symbol} 股票研究证据链加载中，所有结论仅用于观察和模拟验证。`;
  if ($("stockStaleAlert")) {
    $("stockStaleAlert").className = "stock-stale-alert hidden";
    $("stockStaleAlert").innerHTML = "";
  }
  if ($("stockQualityRows")) $("stockQualityRows").innerHTML = `
    <div class="stock-quality-card flat">
      <div class="stock-quality-head"><span>数据可信度</span><strong>加载中</strong></div>
      <em>WATCH</em>
      <p>正在检查报价、日线、盘前盘后、新闻和财报来源。</p>
    </div>
  `;
  if ($("stockDailySwingRows")) $("stockDailySwingRows").innerHTML = `
    <div class="stock-daily-card flat">
      <div class="stock-daily-head"><span>日线波段</span><strong>加载中</strong></div>
      <em>等待日线K线、均线、支撑压力和量能结构。</em>
      <small>仅观察 / 仅研究 / 仅模拟验证</small>
    </div>
  `;
  if ($("stockCatalystRadar")) $("stockCatalystRadar").innerHTML = `
    <div class="stock-catalyst-card flat">
      <div><span>事件催化</span><strong>加载中</strong></div>
      <em>WAIT</em>
      <p>等待财报/新闻、盘前盘后、行业链、异常成交和数据质量。</p>
      <small>仅观察 / 仅研究 / 仅模拟验证</small>
    </div>
  `;
  if ($("stockChainRows")) $("stockChainRows").innerHTML = `
    <div class="stock-chain-card flat">
      <div class="stock-chain-head"><span>产业链拆分</span><strong>加载中</strong></div>
      <em>等待上下游样本</em>
      <p>即将按核心、上游、下游和同细分行业拆分链条共振。</p>
      <small>仅观察 / 仅研究 / 仅模拟验证</small>
    </div>
  `;
  if ($("stockResearchMemo")) $("stockResearchMemo").innerHTML = `
    <div class="stock-research-memo-card flat">
      <div class="stock-research-memo-head"><span>会议纪要</span><strong>加载中</strong></div>
      <em>等待股票证据链</em>
      <ul><li>即将汇总新闻、财报、盘前盘后、同业联动和异常成交。</li></ul>
    </div>
  `;
  ["stockSessionRows", "stockCalendarRows", "stockLinkageRows", "stockUnusualRows"].forEach((targetId) => {
    renderStockResearchRows(targetId, [], () => "");
  });
  const evidencePanel = $("stockEvidencePanel");
  if (evidencePanel) evidencePanel.classList.remove("hidden");
  if ($("stockEvidenceSummary")) $("stockEvidenceSummary").textContent = `${symbol} Futu 证据摘要加载中...`;
  if ($("stockEvidenceCards")) $("stockEvidenceCards").innerHTML = `
    <div class="stock-evidence-card flat"><span>证据链</span><strong>加载中</strong><em>等待盘口、逐笔、资金流和估值。</em></div>
  `;
  if ($("stockEvidenceRows")) $("stockEvidenceRows").innerHTML = `
    <div class="stock-evidence-row flat"><strong>等待 Futu deep</strong><span>切换股票后自动刷新。</span><em>仅研究</em></div>
  `;
  renderLiveSourceBar();
}

function renderStockResearchPanel(data = state.research || {}) {
  const panel = $("stockResearchPanel");
  if (!panel) return;
  if (data.mode !== "stock_research" || !data.stock) {
    panel.classList.add("hidden");
    if ($("stockStaleAlert")) {
      $("stockStaleAlert").className = "stock-stale-alert hidden";
      $("stockStaleAlert").innerHTML = "";
    }
    return;
  }
  panel.classList.remove("hidden");
  normalizeStockResearchLabels(panel);
  const stock = data.stock || {};
  const meta = stock.meta || {};
  const session = stock.session || {};
  const unusual = stock.unusual || {};
  const linkage = stock.linkage || {};
  syncStockResearchQuoteToHeader(stock);
  const summary = $("stockResearchSummary");
  if (summary) summary.textContent = `${meta.symbol || data.symbol || state.symbol} / ${meta.name || "--"} / ${meta.sector || "Stock"} / ${data.safe_action || "仅研究"}`;
  renderStockResearchBrief(data, stock);
  renderStockDataQuality(data, stock);
  renderStockStaleAlert(data, stock);
  maybeAutoRefreshStockResearch(data, stock);
  renderStockDailySwing(data, stock);
  renderStockCatalystRadar(data, stock);
  renderStockChainMap(data, stock);
  renderStockResearchMemo(data, stock);

  renderStockResearchRows("stockSessionRows", session.rows || [], (row) => `
    <div class="stock-research-row ${stockRowTone(row)}">
      <strong>${escapeHtml(row.label || row.session || "--")} · ${escapeHtml(row.status || "--")}</strong>
      <span>${escapeHtml(row.detail || "暂无该时段样本")}</span>
      <em>${escapeHtml(session.source || "--")} ${session.latest_at ? `/ ${escapeHtml(session.latest_at)}` : ""}</em>
    </div>
  `);

  renderStockResearchRows("stockCalendarRows", stock.calendar || data.events || [], (row) => `
    <div class="stock-research-row ${stockRowTone(row)}">
      <strong>${escapeHtml(row.time || "--")} · ${escapeHtml(row.title || "--")}</strong>
      <span>${escapeHtml(row.impact || "--")}</span>
      <em>${escapeHtml(row.category || "财报 / 评级 / 分红 / 风险事件")}</em>
    </div>
  `);

  renderStockResearchRows("stockLinkageRows", linkage.rows || [], (row) => {
    const change = Number(row.change24h_pct || 0);
    return `
      <div class="stock-research-row ${stockRowTone(row)}">
        <strong>${escapeHtml(row.symbol || "--")} ${change >= 0 ? "+" : ""}${number(change, 2)}%</strong>
        <span>${escapeHtml(row.name || row.sector || "--")}</span>
        <em>${escapeHtml(row.source || "--")} / ${escapeHtml(row.reason || linkage.sector || "--")}</em>
      </div>
    `;
  });

  renderStockResearchRows("stockUnusualRows", unusual.rows || [], (row) => `
    <div class="stock-research-row ${stockRowTone(row)}">
      <strong>${escapeHtml(row.label || row.symbol || "--")} ${escapeHtml(row.value || "")}</strong>
      <span>${escapeHtml(row.reason || unusual.headline || "--")}</span>
      <em>量比 ${number(unusual.volume_ratio || 1, 2)}x / 跳空 ${number(unusual.gap_pct || 0, 2)}% / 振幅 ${number(unusual.range_pct || 0, 2)}%</em>
    </div>
  `);
}

function findEvidenceRow(data = {}, matchers = []) {
  const rows = data.unusual?.rows || [];
  return rows.find((row) => matchers.some((item) => String(row.label || row.source || "").includes(item))) || null;
}

function evidenceToneFromNumber(value, neutral = 0) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return "flat";
  if (parsed > neutral) return "up";
  if (parsed < neutral) return "down";
  return "flat";
}

function evidenceCard(label, value, detail, tone = "flat") {
  return { label, value: value || "--", detail: detail || "仅研究 / 仅模拟验证", tone };
}

function renderStockEvidencePanel(data = state.futuDeep || {}) {
  const panel = $("stockEvidencePanel");
  if (!panel) return;
  const symbol = data?.symbol || state.symbol;
  if (!isStockMarket(symbol) || symbol !== state.symbol) {
    panel.classList.add("hidden");
    return;
  }
  panel.classList.remove("hidden");
  if (!data?.ok) {
    $("stockEvidenceSummary").textContent = `${symbol} Futu 证据暂不可用：${data?.error || "等待 OpenD 或权限"}`;
    $("stockEvidenceCards").innerHTML = `
      <div class="stock-evidence-card down">
        <span>Futu 证据</span>
        <strong>不可用</strong>
        <em>${escapeHtml(data?.error || "等待盘口、逐笔、资金流和估值数据。")}</em>
      </div>
    `;
    $("stockEvidenceRows").innerHTML = `<div class="stock-evidence-row flat"><strong>等待数据</strong><span>证据摘要只用于研究，不影响 K线和异动雷达。</span><em>仅研究</em></div>`;
    return;
  }

  const snapshot = data.snapshot || {};
  const valuation = data.valuation || {};
  const flow = data.capital_flow || {};
  const dist = data.capital_distribution?.net || {};
  const watch = data.watch_detail || {};
  const spread = findEvidenceRow(data, ["盘口价差"]);
  const bookTilt = findEvidenceRow(data, ["买卖盘倾斜"]);
  const tape = findEvidenceRow(data, ["逐笔主动性"]);
  const shortFlow = findEvidenceRow(data, ["卖空成交", "空头"]);
  const technical = findEvidenceRow(data, ["技术异动"]);
  const financial = findEvidenceRow(data, ["财务异动"]);
  const valuationPct = Number(valuation.valuation_percentile);
  const mainFlow = Number(flow.main_net_total || 0);
  const largeNet = Number(dist.super_net || 0) + Number(dist.big_net || 0);
  const pre = Number(snapshot.pre_price || watch.session_prices?.pre || 0);
  const post = Number(snapshot.after_price || watch.session_prices?.post || 0);
  const overnight = Number(snapshot.overnight_price || watch.session_prices?.overnight || 0);

  const cards = [
    evidenceCard("盘口价差", spread?.value, spread?.detail || "买一卖一距离", spread?.tone || "flat"),
    evidenceCard("买卖盘倾斜", bookTilt?.value, bookTilt?.detail || "盘口深度强弱", bookTilt?.tone || "flat"),
    evidenceCard("逐笔主动性", tape?.value, tape?.detail || "主动买卖笔数", tape?.tone || "flat"),
    evidenceCard("主力资金", compact(mainFlow), `净流 ${compact(flow.net_total)} / 大单 ${compact(largeNet)}`, evidenceToneFromNumber(mainFlow)),
    evidenceCard("估值分位", Number.isFinite(valuationPct) ? `${number(valuationPct, 1)}%` : "--", `PE TTM ${number(valuation.pe_ttm_ratio || snapshot.pe_ttm_ratio || 0, 2)} / PB ${number(valuation.pb_ratio || snapshot.pb_ratio || 0, 2)}`, Number.isFinite(valuationPct) && valuationPct >= 80 ? "down" : Number.isFinite(valuationPct) && valuationPct <= 30 ? "up" : "flat"),
    evidenceCard("盘前/盘后", `${pre ? number(pre, 2) : "--"} / ${post ? number(post, 2) : "--"}`, `夜盘 ${overnight ? number(overnight, 2) : "--"} / ${data.market_state || "--"}`, "flat"),
  ];

  $("stockEvidenceSummary").textContent = `${symbol} · ${data.market_state || "--"} · Futu 证据链已压缩，所有结论仅用于观察和模拟验证`;
  $("stockEvidenceCards").innerHTML = cards.map((card) => `
    <div class="stock-evidence-card ${card.tone || "flat"}">
      <span>${escapeHtml(card.label)}</span>
      <strong>${escapeHtml(card.value)}</strong>
      <em>${escapeHtml(card.detail)}</em>
    </div>
  `).join("");

  const evidenceRows = [
    technical,
    financial,
    shortFlow,
    ...(data.unusual?.rows || []).filter((row) => ![spread, bookTilt, tape, shortFlow, technical, financial].includes(row)).slice(0, 6),
  ].filter(Boolean);
  $("stockEvidenceRows").innerHTML = evidenceRows.map((row) => `
    <div class="stock-evidence-row ${row.tone || "flat"}">
      <strong>${escapeHtml(row.label || row.source || "--")} · ${escapeHtml(row.value || "--")}</strong>
      <span>${escapeHtml(row.detail || row.source || "--")}</span>
      <em>${escapeHtml(row.source || "Futu evidence")} / 观察证据，不是下单命令</em>
    </div>
  `).join("") || `<div class="stock-evidence-row flat"><strong>等待证据</strong><span>Futu deep 暂未返回可展示证据。</span><em>仅研究</em></div>`;
}

function setLiveSourceItem(itemId, stateId, detailId, tone, stateText, detailText) {
  const item = $(itemId);
  if (item) item.className = `live-source-item ${tone || "flat"}`;
  if ($(stateId)) $(stateId).textContent = stateText || "--";
  if ($(detailId)) $(detailId).textContent = detailText || "--";
}

function renderLiveSourceBar() {
  if (!$("liveSourceBar")) return;
  const stock = isStockMarket();
  const futu = state.futu || {};
  const futuOnline = futuOpenDOnline(futu);
  const chartStatus = $("chartStatus")?.textContent || "";
  const quality = state.chartQuality || {};
  const chartSource = quality.sourceText || quality.sourceLabel || chartStatus || "等待K线";
  const chartDetail = quality.freshnessText && quality.freshnessText !== "--"
    ? `${chartSource} / ${quality.freshnessText}`
    : chartSource;
  const isRealtime = Boolean(quality.realtime) || String(chartStatus).includes("实时");
  const isPreview = Boolean(quality.preview) || String(chartStatus).includes("快速预览");
  const isOldCache = quality.mode === "旧缓存" || String(chartSource).includes("旧缓存") || String(chartStatus).includes("旧缓存");
  const isDelayed = !isRealtime && (isOldCache || Boolean(quality.cached) || Boolean(quality.fallback) || String(chartStatus).includes("缓存") || String(chartStatus).includes("延迟"));
  const hasLoadedChart = state.chartDataSymbol === state.symbol
    && Array.isArray(state.candles)
    && state.candles.length > 0
    && Boolean(quality.source || quality.sourceText || chartStatus);
  const loadedChartState = String(quality.mode || "").trim() || "已加载";
  setLiveSourceItem(
    "liveSourceBarFutu",
    "liveFutuState",
    "liveFutuDetail",
    !stock ? "flat" : futuOnline ? "up" : "down",
    !stock ? "非股票" : futuOnline ? "ONLINE" : "OFFLINE",
    !stock ? "加密行情使用 OKX 公共数据" : `${futu.host || "127.0.0.1"}:${futu.port || "11111"} / ${futu.message || "等待 OpenD"}`
  );
  setLiveSourceItem(
    "liveSourceBarCandle",
    "liveCandleState",
    "liveCandleDetail",
    isRealtime ? "up" : isOldCache || isPreview ? "down" : isDelayed ? "flat" : "flat",
    isRealtime ? "实时" : isOldCache ? "旧缓存" : isPreview ? "预览" : isDelayed ? "缓存/延迟" : hasLoadedChart ? loadedChartState : "加载中",
    chartDetail
  );
  const asyncState = state.stockAsyncResearch?.symbol === state.symbol ? state.stockAsyncResearch : null;
  const newsTone = !stock ? "flat" : asyncState?.status === "ready" ? "up" : asyncState?.status === "loading" ? "flat" : asyncState?.status === "error" ? "down" : "flat";
  const newsText = !stock ? "非股票" : asyncState?.status === "ready" ? "已补全" : asyncState?.status === "error" ? "失败" : "异步中";
  const newsDetail = !stock ? "股票新闻/财报仅在股票研究中启用" : asyncState?.detail || "首屏先用本地摘要，外部新闻和财报稍后补全";
  setLiveSourceItem("liveSourceBarNews", "liveNewsState", "liveNewsDetail", newsTone, newsText, newsDetail);
}

function renderResearchNewsRows(news = []) {
  if (!$("researchNewsRows")) return;
  $("researchNewsRows").innerHTML = news.map((row) => `
    <div class="research-row"><strong>${escapeHtml(row.title || "--")}</strong><span>${escapeHtml(row.source || "--")}${row.category ? ` / ${escapeHtml(row.category)}` : ""}${row.published ? ` / ${escapeHtml(row.published)}` : ""}</span></div>
  `).join("") || `<div class="research-row"><strong>等待新闻</strong><span>外部新闻异步加载中，首屏先使用本地摘要。</span></div>`;
}

function renderResearchEventRows(events = []) {
  if (!$("researchEventRows")) return;
  $("researchEventRows").innerHTML = events.map((row) => `
    <div class="research-row"><strong>${escapeHtml(row.time || "--")} / ${escapeHtml(row.title || "--")}</strong><span>${escapeHtml(row.impact || "--")}</span></div>
  `).join("") || `<div class="research-row"><strong>等待事件</strong><span>财报、估值和风险日历异步加载中。</span></div>`;
}

async function loadStockAsyncResearch(requestSymbol = state.symbol, requestVersion = runtime.symbolVersion) {
  if (!isStockMarket(requestSymbol)) return null;
  state.stockAsyncResearch = { symbol: requestSymbol, status: "loading", detail: "外部新闻和财报日历异步加载中" };
  renderLiveSourceBar();
  try {
    const data = await api(`/api/stocks/news-calendar?symbol=${encodeURIComponent(requestSymbol)}&limit=8`);
    if (requestVersion !== runtime.symbolVersion || requestSymbol !== state.symbol) return null;
    state.stockAsyncResearch = {
      symbol: requestSymbol,
      status: "ready",
      data,
      detail: `${data.news?.length || 0}条新闻 / ${data.events?.length || 0}条事件 / ${data.source || "local"} / ${number(data.latency_ms || 0, 0)}ms`,
    };
    if (state.research?.symbol === requestSymbol) {
      state.research = {
        ...state.research,
        news: data.news || state.research.news || [],
        events: data.events || state.research.events || [],
        async_research: { news_calendar: "ready", source: data.source || "async" },
        stock: {
          ...(state.research.stock || {}),
          calendar: data.events || state.research.stock?.calendar || [],
          fundamentals: data.fundamentals || state.research.stock?.fundamentals || {},
          quality: mergeStockQuality(state.research.stock?.quality || state.research.data_quality || {}, data.data_quality || {}),
        },
        data_quality: mergeStockQuality(state.research.data_quality || state.research.stock?.quality || {}, data.data_quality || {}),
      };
      renderStockResearchPanel(state.research);
      renderResearchNewsRows(state.research.news || []);
      renderResearchEventRows(state.research.events || []);
    }
    renderLiveSourceBar();
    return data;
  } catch (error) {
    if (requestVersion !== runtime.symbolVersion || requestSymbol !== state.symbol) return null;
    state.stockAsyncResearch = { symbol: requestSymbol, status: "error", detail: `新闻/财报异步失败：${error.message}` };
    renderLiveSourceBar();
    return null;
  }
}

async function loadResearchPanel(requestVersion = runtime.symbolVersion) {
  const requestSymbol = state.symbol;
  try {
    if (requestVersion === runtime.symbolVersion && requestSymbol === state.symbol) resetResearchPanelForSymbol(requestSymbol);
    const data = await api(`/api/research/panel?symbol=${encodeURIComponent(requestSymbol)}`);
    if (requestVersion !== runtime.symbolVersion || requestSymbol !== state.symbol) return;
    applySharedSnapshotContext(data.shared_snapshot || data.focus?.shared_snapshot || {});
    state.research = data;
    $("researchSummary").textContent = data.summary || "--";
    renderResearchFocus(data.focus || {});
    renderStockResearchPanel(data);
    renderResearchNewsRows(data.news || []);
    renderResearchEventRows(data.events || []);
    const blocks = (data.mover_blocks || []).length ? data.mover_blocks.map((block) => [block.title, block.rows || [], block.summary || ""]) : [
      ["Hot", data.hot || [], ""],
      ["Gainers", data.gainers || [], ""],
      ["Losers", data.losers || [], ""],
      ["Volume", data.volume || [], ""],
    ];
    $("researchMoverRows").innerHTML = blocks.map(([title, rows, summary]) => `
      <div class="research-row"><strong>${escapeHtml(title || "--")}</strong><span>${escapeHtml(summary || rows.slice(0, 4).map(researchItemText).join(" / ") || "--")}</span></div>
    `).join("");
    loadAnomalyEvents("", { limit: 80 }).catch(() => {});
    loadStockSourceControl(requestSymbol, requestVersion).catch(() => {});
    if (isStockMarket(requestSymbol)) loadStockAsyncResearch(requestSymbol, requestVersion).catch(() => {});
    renderLiveSourceBar();
  } catch (error) {
    $("researchSummary").textContent = `Research panel offline: ${error.message}`;
    renderLiveSourceBar();
  }
}

function updateBook(data) {
  state.orderBook = {
    asks: (data.asks || []).slice(0, 8).map((row) => ({ price: Number(row[0]), size: Number(row[1]) })).reverse(),
    bids: (data.bids || []).slice(0, 8).map((row) => ({ price: Number(row[0]), size: Number(row[1]) })),
  };
  renderBook();
}

function renderStockOrderBook() {
  const futu = state.futuDeep?.symbol === state.symbol ? state.futuDeep : {};
  const rawBids = futu.order_book?.bids || [];
  const rawAsks = futu.order_book?.asks || [];
  const bids = rawBids.slice(0, 8).map((row) => ({
    price: Number(row.price),
    size: Number(row.volume || row.size || 0),
  })).filter((row) => Number.isFinite(row.price) && row.price > 0);
  const asks = rawAsks.slice(0, 8).map((row) => ({
    price: Number(row.price),
    size: Number(row.volume || row.size || 0),
  })).filter((row) => Number.isFinite(row.price) && row.price > 0);
  const market = currentMarket();
  const quoteContext = stockQuoteContextForMarket(market);
  const price = Number(quoteContext?.last || state.lastPrice || market.price || 0);
  const quoteSource = stockQuoteContextSource(quoteContext) || market.quoteSource || market.source || "QUOTE";
  const visibleLog = state.stockPriceLog.find((row) => row.symbol === state.symbol);
  const sourceMismatch = Boolean(visibleLog && quoteSource && String(visibleLog.source || "").toLowerCase() !== String(quoteSource).toLowerCase());
  if (!bids.length && !asks.length) {
    $("asks").innerHTML = `<div class="book-row"><span class="flat">Futu深度</span><span>盘口</span><span>待订阅/权限</span></div>`;
    $("bids").innerHTML = `<div class="book-row"><span class="flat">${price > 0 ? priceText(price) : "--"}</span><span>当前报价</span><span>${escapeHtml(quoteSource.toUpperCase())}</span></div>`;
    $("bookSpread").textContent = sourceMismatch
      ? "股票盘口待 Futu OpenD；非当前报价源日志已隔离"
      : "股票盘口待 Futu OpenD；当前使用同源报价观察";
    $("bookSpread").className = "flat";
    if ($("bookPressureBar")) {
      $("bookPressureBar").innerHTML = `
        <span class="bid-pressure" style="width:50%"></span>
        <span class="ask-pressure" style="width:50%"></span>
        <em>股票盘口等待实时源</em>
      `;
    }
    renderStockMicroSignal();
    return;
  }
  const maxSize = Math.max(1, ...bids.map((row) => row.size), ...asks.map((row) => row.size));
  const renderRows = (rows, side) => rows.map((row) => {
    const width = Math.min(100, (Number(row.size || 0) / maxSize) * 100);
    return `
      <div class="book-row">
        <div class="book-depth" style="width:${width}%"></div>
        <span class="${side}">${priceText(row.price)}</span>
        <span>${compact(row.size)}</span>
        <span>${side === "up" ? "Bid" : "Ask"}</span>
      </div>
    `;
  }).join("");
  $("asks").innerHTML = renderRows(asks.slice().reverse(), "down");
  $("bids").innerHTML = renderRows(bids, "up");
  const bestAsk = asks[0]?.price || 0;
  const bestBid = bids[0]?.price || 0;
  const spread = bestAsk > 0 && bestBid > 0 ? bestAsk - bestBid : 0;
  const mid = bestAsk > 0 && bestBid > 0 ? (bestAsk + bestBid) / 2 : price;
  const spreadPct = mid > 0 ? (spread / mid) * 100 : 0;
  const bidDepth = bids.reduce((sum, row) => sum + Number(row.size || 0), 0);
  const askDepth = asks.reduce((sum, row) => sum + Number(row.size || 0), 0);
  const pressure = (bidDepth - askDepth) / Math.max(bidDepth + askDepth, 1) * 100;
  state.orderBook.pressure = pressure;
  $("bookSpread").textContent = `Futu股票盘口 / spread ${spread ? priceText(spread) : "--"} / ${number(spreadPct, 3)}% / 非信号`;
  $("bookSpread").className = "flat";
  if ($("bookPressureBar")) {
    const bidPct = Math.max(8, Math.min(92, (bidDepth / Math.max(bidDepth + askDepth, 1)) * 100));
    $("bookPressureBar").innerHTML = `
      <em>挂单分布（非信号）：买价侧 ${number(bidPct, 0)}% / 卖价侧 ${number(100 - bidPct, 0)}%</em>
    `;
  }
  renderStockMicroSignal();
}

function renderBook() {
  if (isStockMarket()) {
    renderStockOrderBook();
    return;
  }
  const { asks, bids } = state.orderBook;
  const maxTotal = Math.max(
    1,
    ...asks.map((_, i) => asks.slice(0, i + 1).reduce((sum, row) => sum + row.size, 0)),
    ...bids.map((_, i) => bids.slice(0, i + 1).reduce((sum, row) => sum + row.size, 0)),
  );
  const renderRows = (rows, side) => rows.map((row, index) => {
    const total = rows.slice(0, index + 1).reduce((sum, item) => sum + item.size, 0);
    const width = Math.min(100, (total / maxTotal) * 100);
    const formattedPrice = number(row.price, row.price > 100 ? 2 : 5);
    return `
      <div class="book-row" data-book-price="${row.price}" data-book-side="${side === "up" ? "BID" : "ASK"}" title="点击填入限价 ${formattedPrice}">
        <div class="book-depth" style="width:${width}%"></div>
        <span class="${side}">${formattedPrice}</span>
        <span>${number(row.size, 4)}</span>
        <span>${number(total, 4)}</span>
      </div>
    `;
  }).join("");
  $("asks").innerHTML = renderRows(asks, "down");
  $("bids").innerHTML = renderRows(bids, "up");
  document.querySelectorAll("[data-book-price]").forEach((row) => {
    row.addEventListener("click", () => applyBookPrice(Number(row.dataset.bookPrice), row.dataset.bookSide));
  });
  if (asks.length && bids.length) {
    const spread = asks[asks.length - 1].price - bids[0].price;
    const mid = (asks[asks.length - 1].price + bids[0].price) / 2;
    const spreadPct = mid > 0 ? (spread / mid) * 100 : 0;
    const askDepth = asks.reduce((sum, row) => sum + row.size, 0);
    const bidDepth = bids.reduce((sum, row) => sum + row.size, 0);
    const pressure = (bidDepth - askDepth) / Math.max(bidDepth + askDepth, 1) * 100;
    state.orderBook.pressure = pressure;
    $("bookSpread").textContent = `spread ${number(spread, spread > 1 ? 2 : 5)} / ${number(spreadPct, 3)}% / 非信号`;
    $("bookSpread").className = "flat";
    if ($("bookPressureBar")) {
      const bidPct = Math.max(8, Math.min(92, (bidDepth / Math.max(bidDepth + askDepth, 1)) * 100));
      $("bookPressureBar").innerHTML = `
        <em>挂单分布（非信号）：买价侧 ${number(bidPct, 0)}% / 卖价侧 ${number(100 - bidPct, 0)}%</em>
      `;
    }
    renderMicroSignal();
  }
}

function applyBookPrice(price, bookSide = "") {
  if (!Number.isFinite(price) || price <= 0) return;
  const text = price > 100 ? price.toFixed(2) : price.toFixed(5);
  if ($("manualLimitPrice")) $("manualLimitPrice").value = text;
  if ($("conditionLimitPrice")) $("conditionLimitPrice").value = text;
  if ($("manualOrderType")) $("manualOrderType").value = "LIMIT";
  if ($("conditionOrderType")) $("conditionOrderType").value = "LIMIT";
  if ($("conditionPrice") && !$("conditionPrice").value) $("conditionPrice").value = text;
  if ($("conditionSide")) $("conditionSide").value = bookSide === "ASK" ? "SELL" : "BUY";
  syncConditionForm();
  estimateOrder();
  $("chartStatus").textContent = `已带入盘口价 ${text}`;
}

function addTrades(rows) {
  for (const row of rows) {
    state.trades.unshift({
      price: Number(row.px),
      size: Number(row.sz),
      side: row.side,
      ts: Number(row.ts),
    });
  }
  state.trades = state.trades.slice(0, 80);
  renderTrades();
}

function largeTradeThreshold(trades = state.trades) {
  const sizes = trades.map((trade) => Number(trade.size || 0)).filter((size) => size > 0).sort((a, b) => a - b);
  if (!sizes.length) return Infinity;
  const index = Math.max(0, Math.floor(sizes.length * 0.82) - 1);
  return Math.max(sizes[index], sizes.reduce((sum, size) => sum + size, 0) / sizes.length * 1.8);
}

function filteredTrades() {
  const threshold = largeTradeThreshold(state.trades);
  if (state.tradeFilter === "BUY") return state.trades.filter((trade) => trade.side === "buy");
  if (state.tradeFilter === "SELL") return state.trades.filter((trade) => trade.side !== "buy");
  if (state.tradeFilter === "LARGE") return state.trades.filter((trade) => Number(trade.size || 0) >= threshold);
  return state.trades;
}

function renderStockMicroSignal() {
  if (!$("microSignal")) return;
  const rows = activeStockPriceLogRows(12);
  const latest = Number(rows[0]?.price || state.lastPrice || 0);
  const oldest = Number(rows[rows.length - 1]?.price || latest);
  const movePct = latest > 0 && oldest > 0 ? (latest / oldest - 1) * 100 : 0;
  const pressure = Number(state.orderBook.pressure || 0);
  const label = "近端报价/挂单分布（非信号）";
  state.microSignal = {
    pressure,
    tapeImbalance: movePct,
    tone: "flat",
    label,
    descriptiveOnly: true,
  };
  $("microSignal").className = "micro-signal flat";
  $("microSignal").textContent = `${label} / 近端变化 ${number(movePct, 2)}% / 挂单分布 ${number(pressure, 0)}%`;
  renderBookStrategyHint();
  renderStrategyExplainPanel();
}

function renderStockPriceLog() {
  document.querySelectorAll("[data-trade-filter]").forEach((button) => {
    button.classList.toggle("active", button.dataset.tradeFilter === "ALL");
  });
  const rows = activeStockPriceLogRows(48);
  const quoteContext = stockQuoteContextForMarket();
  const quoteSource = stockQuoteContextSource(quoteContext);
  $("tradeCount").textContent = `${rows.length} 条`;
  const latest = rows[0];
  const previous = rows[1];
  const latestPrice = Number(latest?.price || state.lastPrice || 0);
  const previousPrice = Number(previous?.price || latestPrice);
  const shortMove = latestPrice > 0 && previousPrice > 0 ? (latestPrice / previousPrice - 1) * 100 : 0;
  if ($("tradeTapeSummary")) {
    $("tradeTapeSummary").innerHTML = `
      <span class="${cssMove(latest?.change || 0)}">日内 ${latest ? `${number(latest.change, 2)}%` : "--"}</span>
      <span class="${cssMove(shortMove)}">最近 ${latest && previous ? `${number(shortMove, 3)}%` : "--"}</span>
      <span>源 ${escapeHtml(quoteSource || latest?.source || state.futu?.last_stock_source || "等待报价")}</span>
    `;
  }
  $("trades").innerHTML = rows.length ? rows.map((row, index) => {
    const next = rows[index + 1];
    const tickMove = next?.price ? row.price - next.price : row.change;
    const side = cssMove(tickMove);
    const sideLabel = row.source === "FUTU_TAPE"
      ? (String(row.status || "").toUpperCase().startsWith("S") ? "S" : String(row.status || "").toUpperCase().startsWith("B") ? "B" : "T")
      : "Q";
    const detail = row.source === "FUTU_TAPE"
      ? `${escapeHtml(row.status || "Tape")} / ${compact(row.volume)}`
      : `${number(row.change, 2)}% / ${compact(row.volume)} / ${escapeHtml(row.source)}`;
    const title = `股票价格日志 / ${row.symbol} / ${priceText(row.price)} / ${row.source} / ${tradeTimeText(row.ts)}`;
    return `
      <div class="trade-row ${index === 0 ? "latest" : ""}" title="${escapeHtml(title)}">
        <span class="${side}"><em>${sideLabel}</em>${priceText(row.price)}</span>
        <span>${detail}</span>
        <span>${tradeTimeText(row.ts)}</span>
      </div>
    `;
  }).join("") : `
    <div class="trade-row">
      <span class="flat"><em>Q</em>--</span>
      <span>等待股票报价</span>
      <span>--</span>
    </div>
  `;
  renderStockMicroSignal();
}

function renderTrades() {
  if (isStockMarket()) {
    renderStockPriceLog();
    return;
  }
  document.querySelectorAll("[data-trade-filter]").forEach((button) => {
    button.classList.toggle("active", button.dataset.tradeFilter === state.tradeFilter);
  });
  const displayTrades = filteredTrades();
  const visibleTrades = displayTrades.slice(0, 48);
  const recentTrades = state.trades.slice(0, 30);
  const largeThreshold = largeTradeThreshold(recentTrades);
  const buyVolume = recentTrades.filter((trade) => trade.side === "buy").reduce((sum, trade) => sum + Number(trade.size || 0), 0);
  const sellVolume = recentTrades.filter((trade) => trade.side !== "buy").reduce((sum, trade) => sum + Number(trade.size || 0), 0);
  const largest = recentTrades.reduce((max, trade) => Math.max(max, Number(trade.size || 0)), 0);
  $("tradeCount").textContent = `${visibleTrades.length}/${displayTrades.length}`;
  if ($("tradeTapeSummary")) {
    $("tradeTapeSummary").innerHTML = `
      <span class="up">买盘 ${tradeSizeText(buyVolume)}</span>
      <span class="down">卖盘 ${tradeSizeText(sellVolume)}</span>
      <span>大单 ${tradeSizeText(largest)} / 阈值 ${tradeSizeText(largeThreshold)}</span>
    `;
  }
  $("trades").innerHTML = visibleTrades.map((trade, index) => {
    const side = trade.side === "buy" ? "up" : "down";
    const sideLabel = trade.side === "buy" ? "B" : "S";
    const priceText = number(trade.price, trade.price > 100 ? 2 : 5);
    const sizeText = tradeSizeText(trade.size);
    const time = tradeTimeText(trade.ts);
    const title = `${trade.side === "buy" ? "买入成交" : "卖出成交"} / 价格 ${priceText} / 数量 ${number(trade.size, 8)} / ${time}`;
    const isLarge = Number(trade.size || 0) >= largeThreshold;
    return `
    <div class="trade-row ${index === 0 ? "latest" : ""} ${isLarge ? "large-trade" : ""}" title="${escapeHtml(title)}">
      <span class="${side}"><em>${sideLabel}</em>${priceText}</span>
      <span>${sizeText}</span>
      <span>${time}</span>
    </div>
  `;
  }).join("");
  renderMicroSignal();
}

function renderMicroSignal() {
  if (!$("microSignal")) return;
  const recent = state.trades.slice(0, 24);
  const buyVolume = recent.filter((trade) => trade.side === "buy").reduce((sum, trade) => sum + Number(trade.size || 0), 0);
  const sellVolume = recent.filter((trade) => trade.side !== "buy").reduce((sum, trade) => sum + Number(trade.size || 0), 0);
  const tapeImbalance = (buyVolume - sellVolume) / Math.max(buyVolume + sellVolume, 1) * 100;
  const pressure = Number(state.orderBook.pressure || 0);
  const label = "瞬时盘口/成交分布（非信号）";
  state.microSignal = {
    pressure,
    tapeImbalance,
    tone: "flat",
    label,
    descriptiveOnly: true,
  };
  $("microSignal").className = "micro-signal flat";
  $("microSignal").textContent = `${label} / 挂单分布 ${number(pressure, 0)}% / 成交分布 ${number(tapeImbalance, 0)}%`;
  renderBookStrategyHint();
  renderStrategyExplainPanel();
}

function renderBookStrategyHint() {
  const target = $("bookStrategyHint");
  if (!target) return;
  const paper = state.paper || {};
  const analysis = state.latestStrategyAnalysis || paper.ai_analysis || {};
  const probability = Number(analysis.profit_probability || 0);
  const direction = strategyRawDirection(analysis) === "SHORT" || paper.position_side === "SHORT" ? "研究偏空" : strategyRawDirection(analysis) === "LONG" || paper.position_side === "LONG" ? "研究偏多" : "方向未形成";
  const tp = paper.take_profit_price || strategyPlanningValue(analysis, "take_profit") || 0;
  const sl = paper.stop_loss_price || strategyPlanningValue(analysis, "stop_loss") || 0;
  const stateText = "研究观察";
  target.className = "book-strategy-hint flat";
  target.dataset.rawPaperArmed = String(Boolean(paper.armed));
  target.title = `原始 armed=${String(Boolean(paper.armed))} · 不代表模拟授权`;
  target.textContent = `${stateText} / ${direction} · 非订单 / 概率 ${probability ? `${number(probability * 100, 0)}%` : "--"} / 规划 TP ${tp ? number(tp, tp > 100 ? 2 : 5) : "--"} / 规划 SL ${sl ? number(sl, sl > 100 ? 2 : 5) : "--"}`;
}

function updateCandle(row) {
  const candle = candleFromOkx(row);
  const last = state.candles[state.candles.length - 1];
  if (last && last.ts === candle.ts) {
    state.candles[state.candles.length - 1] = candle;
  } else {
    state.candles.push(candle);
    state.candles = state.candles.slice(-400);
  }
  state.chartQuality = chartQualityFromSource({
    symbol: state.symbol,
    bar: state.bar,
    rows: state.candles,
    source: "okx_realtime_candles",
    latestTs: candle.ts,
    realtime: true,
    fallback: false,
  });
  state.chartQualityBySymbol[state.symbol] = state.chartQuality;
  renderChartQuality(state.chartQuality);
  drawChart();
}

function clampNumber(value, min, max) {
  return Math.max(min, Math.min(value, max));
}

function visibleCandles() {
  const source = state.replay.active ? state.candles.slice(0, clampNumber(state.replay.index, 1, state.candles.length || 1)) : state.candles;
  const total = source.length;
  const visible = clampNumber(state.chartView.visible, 40, Math.max(40, Math.min(800, total || 180)));
  state.chartView.visible = visible;
  const maxOffset = Math.max(0, total - visible);
  state.chartView.offset = clampNumber(state.chartView.offset, 0, maxOffset);
  const end = total - state.chartView.offset;
  const start = Math.max(0, end - visible);
  return {
    candles: source.slice(start, end),
    start,
    end,
    total,
  };
}

function formatCandleTime(ts) {
  const date = new Date(ts);
  if (state.bar === "1Dutc") return date.toISOString().slice(0, 10);
  return date.toLocaleString("zh-CN", { hour12: false, month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function updateChartTooltip() {
  const tooltip = $("chartTooltip");
  const meta = state.chartMeta;
  if (!tooltip || !meta || !state.chartHover) {
    tooltip?.classList.add("hidden");
    return;
  }
  const candle = meta.candles[state.chartHover.localIndex];
  if (!candle) {
    tooltip.classList.add("hidden");
    return;
  }
  const change = candle.open ? ((candle.close - candle.open) / candle.open) * 100 : 0;
  tooltip.innerHTML = `
    <strong>${formatCandleTime(candle.ts)}</strong>
    <div><span>开</span><b>${priceText(candle.open)}</b></div>
    <div><span>高</span><b>${priceText(candle.high)}</b></div>
    <div><span>低</span><b>${priceText(candle.low)}</b></div>
    <div><span>收</span><b class="${cssMove(change)}">${priceText(candle.close)}</b></div>
    <div><span>涨跌</span><b class="${cssMove(change)}">${change >= 0 ? "+" : ""}${number(change, 2)}%</b></div>
    <div><span>量</span><b>${compact(candle.volume)}</b></div>
  `;
  tooltip.style.left = `${clampNumber(state.chartHover.x + 14, 68, meta.width - 240)}px`;
  tooltip.style.top = `${clampNumber(state.chartHover.y + 14, 50, meta.height - 190)}px`;
  tooltip.classList.remove("hidden");
}

const FIB_LEVELS = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1];
const FIB_EXTENSIONS = [1.272, 1.618, 2.0];

function drawingPointFromEvent(event) {
  const meta = state.chartMeta;
  if (!meta) return null;
  const point = chartPoint(event);
  const xRatio = clampNumber((point.x - meta.pad.left) / Math.max(1, meta.chartW), 0, 1);
  const localIndex = clampNumber(Math.round(xRatio * (meta.candles.length - 1)), 0, meta.candles.length - 1);
  const candle = meta.candles[localIndex];
  const priceRatio = clampNumber((point.y - meta.pad.top) / Math.max(1, meta.chartH), 0, 1);
  const price = meta.maxPrice - priceRatio * meta.range;
  return {
    index: meta.start + localIndex,
    ts: candle?.ts || 0,
    price,
  };
}

function pointToScreen(point, meta) {
  let localIndex = point.index - meta.start;
  if (point.ts) {
    const matched = meta.candles.findIndex((candle) => candle.ts === point.ts);
    if (matched >= 0) localIndex = matched;
  }
  const xRatio = meta.candles.length <= 1 ? 0 : localIndex / Math.max(1, meta.candles.length - 1);
  return {
    x: meta.pad.left + xRatio * meta.chartW,
    y: meta.y(point.price),
    visible: localIndex >= 0 && localIndex <= meta.candles.length - 1,
  };
}

function drawSingleDrawing(ctx, drawing, meta, draft = false) {
  if (!drawing?.p1 || !drawing?.p2) return;
  const p1 = pointToScreen(drawing.p1, meta);
  const p2 = pointToScreen(drawing.p2, meta);
  ctx.save();
  ctx.lineWidth = draft ? 1 : 1.4;
  ctx.strokeStyle = drawing.type === "fib" ? "rgba(239,185,11,.82)" : "rgba(67,215,255,.82)";
  ctx.fillStyle = drawing.type === "fib" ? "#efb90b" : "#43d7ff";
  ctx.setLineDash(draft ? [5, 5] : []);

  if (drawing.type === "horizontal") {
    const yy = p1.y;
    ctx.beginPath();
    ctx.moveTo(meta.pad.left, yy);
    ctx.lineTo(meta.width - meta.pad.right, yy);
    ctx.stroke();
    ctx.fillText(number(drawing.p1.price, 2), meta.width - meta.pad.right + 10, yy + 4);
  } else if (drawing.type === "trend") {
    ctx.beginPath();
    ctx.moveTo(p1.x, p1.y);
    ctx.lineTo(p2.x, p2.y);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(p1.x, p1.y, 3, 0, Math.PI * 2);
    ctx.arc(p2.x, p2.y, 3, 0, Math.PI * 2);
    ctx.fill();
  } else if (drawing.type === "fib") {
    const start = drawing.p1.price;
    const end = drawing.p2.price;
    [...FIB_LEVELS, ...FIB_EXTENSIONS].forEach((level) => {
      const price = end + (start - end) * level;
      const yy = meta.y(price);
      if (yy < meta.pad.top || yy > meta.height - meta.pad.bottom) return;
      ctx.globalAlpha = level === 0 || level === 1 ? 0.95 : 0.72;
      ctx.beginPath();
      ctx.moveTo(meta.pad.left, yy);
      ctx.lineTo(meta.width - meta.pad.right, yy);
      ctx.stroke();
      ctx.fillText(`${level > 1 ? "扩展 " : ""}${number(level * 100, 1)}% ${priceText(price)}`, meta.pad.left + 8, yy - 4);
    });
    ctx.globalAlpha = 1;
    ctx.strokeStyle = "rgba(239,185,11,.35)";
    ctx.beginPath();
    ctx.moveTo(p1.x, p1.y);
    ctx.lineTo(p2.x, p2.y);
    ctx.stroke();
  }
  ctx.restore();
}

function drawUserDrawings(ctx, meta) {
  state.drawings.forEach((drawing) => drawSingleDrawing(ctx, drawing, meta));
  if (state.draftDrawing) drawSingleDrawing(ctx, state.draftDrawing, meta, true);
}

function drawVolumeProfile(ctx, candles, meta) {
  if (!state.indicators.volumeProfile || !candles.length) return;
  const colors = chartThemeColors();
  const bins = 24;
  const buckets = Array.from({ length: bins }, () => 0);
  candles.forEach((candle) => {
    const mid = (candle.high + candle.low + candle.close) / 3;
    const index = clampNumber(Math.floor(((mid - meta.minPrice) / Math.max(meta.range, 1e-9)) * bins), 0, bins - 1);
    buckets[index] += Number(candle.volume || 0);
  });
  const maxVol = Math.max(1, ...buckets);
  ctx.save();
  buckets.forEach((value, index) => {
    const price = meta.minPrice + (index / bins) * meta.range;
    const y = meta.y(price);
    const width = (value / maxVol) * Math.min(140, meta.chartW * 0.18);
    ctx.fillStyle = colors.volumeProfile;
    ctx.fillRect(meta.width - meta.pad.right - width, y - 4, width, 8);
  });
  ctx.restore();
}

function drawAutoMarks(ctx, meta) {
  if (!state.indicators.autoMarks || !meta.candles.length) return;
  const highs = meta.candles.map((item) => item.high);
  const lows = meta.candles.map((item) => item.low);
  const resistance = Math.max(...highs.slice(-80));
  const support = Math.min(...lows.slice(-80));
  const mid = (resistance + support) / 2;
  const lines = [
    { label: "压力", price: resistance, color: "rgba(255,77,94,.75)" },
    { label: "支撑", price: support, color: "rgba(25,195,125,.75)" },
    { label: "箱体中线", price: mid, color: "rgba(143,155,150,.55)" },
  ];
  ctx.save();
  ctx.setLineDash([6, 4]);
  lines.forEach((line) => {
    const yy = meta.y(line.price);
    if (yy < meta.pad.top || yy > meta.height - meta.pad.bottom) return;
    ctx.strokeStyle = line.color;
    ctx.beginPath();
    ctx.moveTo(meta.pad.left, yy);
    ctx.lineTo(meta.width - meta.pad.right, yy);
    ctx.stroke();
    ctx.fillStyle = line.color;
    ctx.fillText(`${line.label} ${priceText(line.price)}`, meta.pad.left + 10, yy - 5);
  });
  ctx.restore();
}

function strategyAnchorLines() {
  const paper = state.paper || {};
  const analysis = state.latestStrategyAnalysis || paper.ai_analysis || {};
  const lines = [];
  const seen = new Set();
  const add = (key, label, price, tone = "flat", detail = "") => {
    const parsed = Number(price);
    if (!Number.isFinite(parsed) || parsed <= 0) return;
    const unique = `${key}:${parsed.toFixed(parsed > 100 ? 2 : 5)}`;
    if (seen.has(unique)) return;
    seen.add(unique);
    lines.push({ key, label, price: parsed, tone, detail });
  };

  const direction = ["LONG", "SHORT"].includes(strategyRawDirection(analysis))
    ? strategyRawDirection(analysis)
    : ["LONG", "SHORT"].includes(String(paper.position_side || "").toUpperCase())
      ? String(paper.position_side).toUpperCase()
      : "";
  const probability = Number(analysis.profit_probability || 0);
  const current = state.lastPrice || state.candles[state.candles.length - 1]?.close || 0;
  add("current", "Current", current, "mark", direction === "SHORT" ? "研究偏空 · 非订单" : direction === "LONG" ? "研究偏多 · 非订单" : "方向未形成");
  add("entry", "Entry", paper.entry_price, "entry", paper.position_side || "");
  add("scale", "Scale", paper.last_scale_price, "entry", "Last fill");
  add("take", "研究规划 TP", paper.take_profit_price || strategyPlanningValue(analysis, "take_profit"), "flat", probability ? `${number(probability * 100, 0)}%` : "");
  add("stop", "研究规划 SL", paper.stop_loss_price || strategyPlanningValue(analysis, "stop_loss"), "flat", "研究风险参考");
  add("trail_take", "Trailing TP", paper.trailing_take_price, "take", `${number(paper.trailing_take_pct, 2)}%`);
  add("trail_stop", "Trailing SL", paper.trailing_stop_price, "stop", `${number(paper.trailing_stop_pct, 2)}%`);
  add("liq", "Liq warn", paper.liquidation_price, "danger", paper.margin_mode === "ISOLATED" ? "Isolated" : "Cross");
  return lines;
}

function drawStrategyAnchors(ctx, meta) {
  const referencePrice = meta.candles[meta.candles.length - 1]?.close || state.lastPrice || 0;
  const lines = strategyAnchorLines().filter((line) => priceFitsCurrentChart(line.price, referencePrice));
  if (!lines.length) return;
  const colors = {
    mark: "rgba(239, 185, 11, 0.78)",
    entry: "rgba(67, 215, 255, 0.86)",
    take: chartAlpha(chartUpColor(), 0.86),
    stop: chartAlpha(chartDownColor(), 0.9),
    danger: chartThemeColors().danger,
    flat: "rgba(143, 155, 150, 0.72)",
  };
  const themeColors = chartThemeColors();
  ctx.save();
  ctx.font = "11px Segoe UI";
  lines.forEach((line) => {
    const yy = meta.y(line.price);
    if (yy < meta.pad.top - 8 || yy > meta.height - meta.pad.bottom + 8) return;
    const color = colors[line.tone] || colors.flat;
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = line.key === "current" ? 1.2 : 1;
    ctx.setLineDash(line.key === "current" ? [5, 5] : [8, 5]);
    ctx.beginPath();
    ctx.moveTo(meta.pad.left, yy);
    ctx.lineTo(meta.width - meta.pad.right, yy);
    ctx.stroke();
    ctx.setLineDash([]);
    const label = `${line.label} ${priceText(line.price)}${line.detail ? ` / ${line.detail}` : ""}`;
    const labelWidth = Math.min(210, ctx.measureText(label).width + 16);
    const x0 = meta.width - meta.pad.right - labelWidth - 6;
    const y0 = clampNumber(yy - 12, meta.pad.top + 2, meta.height - meta.pad.bottom - 22);
    ctx.fillStyle = themeColors.overlayBg;
    ctx.fillRect(x0, y0, labelWidth, 22);
    ctx.strokeStyle = color;
    ctx.strokeRect(x0, y0, labelWidth, 22);
    ctx.fillStyle = color;
    ctx.fillText(label, x0 + 8, y0 + 15);
  });
  ctx.restore();
}

function renderChartStrategyOverlay() {
  const target = $("chartStrategyOverlay");
  if (!target) return;
  const paper = state.paper || {};
  const analysis = state.latestStrategyAnalysis || paper.ai_analysis || {};
  const explanation = currentStrategyExplanation();
  const position = paper.position_side === "LONG" ? `多 ${number(Math.abs(paper.position_qty || 0), 4)}` : paper.position_side === "SHORT" ? `空 ${number(Math.abs(paper.position_qty || 0), 4)}` : "空仓";
  const referencePrice = state.candles[state.candles.length - 1]?.close || state.lastPrice || 0;
  const rawTp = paper.take_profit_price || strategyPlanningValue(analysis, "take_profit") || 0;
  const rawSl = paper.stop_loss_price || strategyPlanningValue(analysis, "stop_loss") || 0;
  const tp = priceFitsCurrentChart(rawTp, referencePrice) ? rawTp : 0;
  const sl = priceFitsCurrentChart(rawSl, referencePrice) ? rawSl : 0;
  const rr = analysis.risk_reward ? `盈亏比 ${number(analysis.risk_reward, 2)}` : "等待盈亏比";
  target.className = "chart-strategy-overlay muted evidence-neutral";
  target.innerHTML = `
    <div>
      <span>策略层</span>
      <strong>${analysis.strategy_name || paper.strategy?.name || optionText("strategySelect") || "等待策略"}</strong>
    </div>
    <div>
      <span>研究方向 / 模型估计</span>
      <strong>${escapeHtml(explanation.directionText)} / ${escapeHtml(explanation.estimateText)}</strong>
    </div>
    <div>
      <span>研究规划 TP / SL</span>
      <strong>${tp ? priceText(tp) : "--"} / ${sl ? priceText(sl) : "--"}</strong>
    </div>
    <div>
      <span>模拟持仓 · 仍未授权</span>
      <strong>${position} / ${rr}</strong>
    </div>
  `;
}

function setDrawingTool(tool) {
  state.drawingTool = tool;
  state.draftDrawing = null;
  document.querySelectorAll("[data-draw-tool]").forEach((button) => {
    button.classList.toggle("active", button.dataset.drawTool === tool);
  });
  $("chartStatus").textContent = tool === "cursor" ? "Cursor mode" : `${tool === "fib" ? "Fibonacci" : tool === "trend" ? "Trend line" : "Horizontal line"}: drag on chart`;
}

function toggleReplay() {
  state.replay.active = !state.replay.active;
  $("toggleReplay").classList.toggle("active", state.replay.active);
  if (state.replay.active) {
    state.replay.index = Math.max(40, Math.floor(state.candles.length * 0.35));
    clearInterval(state.replay.timer);
    state.replay.timer = setInterval(() => {
      state.replay.index += 1;
      if (state.replay.index >= state.candles.length) {
        state.replay.active = false;
        $("toggleReplay").classList.remove("active");
        clearInterval(state.replay.timer);
      }
      drawChart();
    }, 650);
    $("chartStatus").textContent = "K线回放中";
  } else {
    clearInterval(state.replay.timer);
    $("chartStatus").textContent = "K线回放已停止";
  }
  drawChart();
}

function latestFibLevels() {
  const fib = [...state.drawings].reverse().find((item) => item.type === "fib" && item.p1 && item.p2);
  if (!fib) return [];
  return FIB_LEVELS.map((level) => ({
    level,
    price: fib.p2.price + (fib.p1.price - fib.p2.price) * level,
  })).sort((a, b) => a.price - b.price);
}

function analyzeChartAi() {
  const meta = state.chartMeta;
  if (!meta || !meta.candles.length) return;
  const candles = meta.candles;
  const closes = candles.map((candle) => candle.close);
  const last = state.lastPrice || closes[closes.length - 1];
  const first = closes[0];
  const high = Math.max(...candles.map((candle) => candle.high));
  const low = Math.min(...candles.map((candle) => candle.low));
  const trendPct = first ? ((last - first) / first) * 100 : 0;
  const rangePct = low ? ((high - low) / low) * 100 : 0;
  const fibs = latestFibLevels();
  const below = fibs.filter((item) => item.price <= last).slice(-1)[0];
  const above = fibs.find((item) => item.price > last);
  const direction = trendPct > 1 ? "Bullish" : trendPct < -1 ? "Bearish" : "Range";
  const fibText = fibs.length
    ? `Nearest fib: below ${below ? `${number(below.level * 100, 1)}% / ${number(below.price, 2)}` : "none"}, above ${above ? `${number(above.level * 100, 1)}% / ${number(above.price, 2)}` : "none"}`
    : "No Fibonacci drawing yet. Use the Fib tool on a swing high/low.";
  const suggestion = direction === "Bullish"
    ? "Trend strategies can be watched if price holds above key fib levels; tighten stops if it breaks lower levels."
    : direction === "Bearish"
      ? "Current structure is weak; rebounds near upper fib levels may face pressure."
      : "Current structure is closer to range trading; grid or Bollinger-style strategies deserve attention.";
  state.chartAi = { headline: "AI Chart Analysis", bias: direction, suggestion, trendPct, rangePct };
  $("chartAiBox").innerHTML = `
    <strong>AI Chart Analysis / ${direction}</strong>
    Last ${number(last, 2)}, window move ${trendPct >= 0 ? "+" : ""}${number(trendPct, 2)}%, range ${number(rangePct, 2)}%.
    <span>${fibText}</span>
    <span>${suggestion}</span>
  `;
  $("chartAiBox").classList.remove("hidden");
  renderSideInsights();
  $("chartStatus").textContent = "AI chart analysis updated";
}

function validVolumeValues(values = []) {
  return values.map((value) => Number(value || 0)).filter((value) => Number.isFinite(value) && value > 0);
}

function volumeRatioSignal(newerValues = [], olderValues = []) {
  const newer = validVolumeValues(newerValues);
  const older = validVolumeValues(olderValues);
  if (newer.length < 5 || older.length < 5) {
    return { ratio: 1, state: "量能样本不足", note: "前后窗口有效成交量不足，暂不判断放量。" };
  }
  const avg = (rows) => rows.reduce((sum, value) => sum + value, 0) / Math.max(rows.length, 1);
  const raw = avg(newer) / Math.max(avg(older), 1e-9);
  const ratio = clampNumber(raw, 0.05, 8);
  return {
    ratio,
    state: ratio >= 1.8 ? "明显放量" : ratio >= 1.15 ? "温和放量" : ratio <= 0.72 ? "缩量" : "量能正常",
    note: raw > 8 ? "量能倍率已截断到8x，需结合盘口和分时确认。" : `近40根/前40根 ${number(ratio, 2)}x`,
  };
}

function frontendMarketAiLocal() {
  const candles = !state.chartDataSymbol || state.chartDataSymbol === state.symbol ? state.candles || [] : [];
  const dataSourceText = $("chartStatus")?.textContent || "等待K线";
  const last = state.lastPrice || candles[candles.length - 1]?.close || 0;
  const candleQuality = state.chartCandleQuality || {};
  if (isStockMarket() && candleQuality.has_break && !candleQuality.analysis_ready) {
    const warning = candleQuality.warning || "检测到日线价格尺度断点，需核对复权、拆股或数据源口径。";
    return {
      symbol: state.symbol,
      bar: state.bar,
      price: last,
      candle_count: candles.length,
      drawing_count: state.drawings.length,
      fib_count: latestFibLevels().length,
      analysis_paused: true,
      trend_state: "复权断点待核",
      change_pct: 0,
      range_pct: 0,
      volume_ratio: 0,
      support: 0,
      resistance: 0,
      source: dataSourceText,
      long_plan: { win_rate_pct: 0, take_profit: 0, stop_loss: 0 },
      short_plan: { win_rate_pct: 0, take_profit: 0, stop_loss: 0 },
      evidence: [warning, "历史日线分析暂停；仅保留实时报价和临时连续视图。", "等待同口径日线样本达到20根后重新计算。"],
      summary: `${state.symbol} 历史日线尺度待核，趋势、振幅、关键价位和多空估计已暂停。`,
    };
  }
  const recent = candles.slice(-80);
  const first = recent[0]?.close || candles[0]?.close || last;
  const high = recent.length ? Math.max(...recent.map((candle) => Number(candle.high || 0))) : 0;
  const low = recent.length ? Math.min(...recent.map((candle) => Number(candle.low || last)).filter((value) => value > 0)) : 0;
  const olderVol = candles.slice(-80, -40).map((candle) => Number(candle.volume || 0));
  const newerVol = candles.slice(-40).map((candle) => Number(candle.volume || 0));
  const avg = (rows) => rows.reduce((sum, value) => sum + value, 0) / Math.max(rows.length, 1);
  const changePct = first ? ((last - first) / first) * 100 : 0;
  const rangePct = high > 0 && low > 0 ? ((high / low) - 1) * 100 : 0;
  const volumeSignal = volumeRatioSignal(newerVol, olderVol);
  const volumeRatio = volumeSignal.ratio;
  const closes = candles.map((candle) => Number(candle.close || 0)).filter((value) => value > 0);
  const avgClose = (count) => {
    const slice = closes.slice(-count);
    return avg(slice);
  };
  const ma20 = avgClose(20);
  const ma60 = avgClose(60);
  const recentLows = recent.map((candle) => Number(candle.low || last)).filter((value) => value > 0);
  const recentHighs = recent.map((candle) => Number(candle.high || 0)).filter((value) => value > 0);
  const support = low || (recentLows.length ? Math.min(...recentLows) : 0);
  const resistance = high || (recentHighs.length ? Math.max(...recentHighs) : 0);
  const breakoutRoom = resistance && last ? ((resistance - last) / last) * 100 : 0;
  const downsideRoom = support && last ? ((last - support) / last) * 100 : 0;
  const trendState = closes.length < 30
    ? "样本不足"
    : last > ma20 && ma20 > ma60 && changePct > 0
      ? "上升趋势"
      : last < ma20 && ma20 < ma60 && changePct < 0
        ? "下降趋势"
        : rangePct > 6
          ? "高波动震荡"
          : "区间震荡";
  const volumeState = volumeSignal.state;
  const longScore = clampNumber(50 + (last > ma20 ? 8 : -6) + (ma20 > ma60 ? 8 : -5) + (volumeRatio > 1.2 ? 5 : 0) - (breakoutRoom < 1.2 ? 4 : 0), 35, 72);
  const shortScore = clampNumber(50 + (last < ma20 ? 8 : -6) + (ma20 < ma60 ? 8 : -5) + (volumeRatio > 1.2 ? 4 : 0) - (downsideRoom < 1.2 ? 4 : 0), 35, 72);
  return {
    symbol: state.symbol,
    bar: state.bar,
    price: last,
    candle_count: candles.length,
    drawing_count: state.drawings.length,
    fib_count: latestFibLevels().length,
    change_pct: changePct,
    range_pct: rangePct,
    volume_ratio: volumeRatio,
    source: dataSourceText,
    trend_state: trendState,
    volume_state: volumeState,
    support,
    resistance,
    ma20,
    ma60,
    long_plan: {
      win_rate_pct: longScore,
      take_profit: resistance || 0,
      stop_loss: support ? support * 0.992 : 0,
    },
    short_plan: {
      win_rate_pct: shortScore,
      take_profit: support || 0,
      stop_loss: resistance ? resistance * 1.008 : 0,
    },
    evidence: [
      `数据源：${dataSourceText}`,
      `趋势：${trendState}`,
      `量能：${volumeState}，${volumeSignal.note}`,
      support && resistance ? `支撑 ${priceText(support)} / 压力 ${priceText(resistance)}` : "等待关键价位",
    ],
    summary: candles.length
      ? `${state.symbol} ${state.bar} 当前价 ${priceText(last)}，${trendState}，近窗口 ${changePct >= 0 ? "+" : ""}${number(changePct, 2)}%，振幅 ${number(rangePct, 2)}%。`
      : "等待K线数据。",
  };
}

function renderMarketAiLocal(local = null) {
  const snapshot = $("marketAiSnapshot");
  if (!snapshot) return;
  const front = frontendMarketAiLocal();
  const requestedLocal = local?.symbol === state.symbol ? local : null;
  const savedLocal = state.marketAi?.symbol === state.symbol ? state.marketAi?.local : null;
  const data = requestedLocal || savedLocal || front;
  const price = Number(data.price || front.price || 0);
  snapshot.innerHTML = `
    <div><span>标的</span><strong>${escapeHtml(data.symbol || state.symbol)}</strong></div>
    <div><span>K线</span><strong>${escapeHtml(data.bar || state.bar)} / ${Number(data.candle_count || front.candle_count || 0)}</strong></div>
    <div><span>画线</span><strong>${Number(front.drawing_count || 0)} 条 / Fib ${Number(front.fib_count || 0)}</strong></div>
    <div><span>价格</span><strong>${price ? number(price, price > 100 ? 2 : 5) : "--"}</strong></div>
  `;
  const target = $("marketAiLocal");
  if (!target) return;
  const longPlan = data.long_plan || {};
  const shortPlan = data.short_plan || {};
  const metrics = data.metrics || {};
  const longRate = Number(longPlan.win_rate_pct || 0);
  const shortRate = Number(shortPlan.win_rate_pct || 0);
  const support = Number(data.support || front.support || 0);
  const resistance = Number(data.resistance || front.resistance || 0);
  const evidence = data.evidence || front.evidence || [];
  const rawVolumeRatio = Number(metrics.volume_ratio ?? front.volume_ratio);
  const volumeRatioText = Number.isFinite(rawVolumeRatio) && rawVolumeRatio > 0
    ? `${number(clampNumber(rawVolumeRatio, 0.05, 8), 2)}x${rawVolumeRatio > 8 ? "+" : ""}`
    : "--";
  const analysisPaused = Boolean(data.analysis_paused || front.analysis_paused);
  target.innerHTML = `
    <div class="market-ai-local-head">
      <strong>${escapeHtml(data.summary || front.summary)}</strong>
      <span>${escapeHtml(data.source || "本地规则")} / ${escapeHtml(data.trend_state || front.trend_state || "等待K线")}</span>
    </div>
    <div class="market-ai-mini-grid">
      <div><span>偏多模型估计 · 未校准</span><strong class="flat">${longRate ? `${number(longRate, 1)}%` : "--"}</strong></div>
      <div><span>偏空模型估计 · 未校准</span><strong class="flat">${shortRate ? `${number(shortRate, 1)}%` : "--"}</strong></div>
      <div><span>量能倍率</span><strong>${volumeRatioText}</strong></div>
      <div><span>窗口振幅</span><strong>${analysisPaused ? "待核" : `${number(metrics.range_pct ?? front.range_pct, 2)}%`}</strong></div>
    </div>
    <div class="market-analysis-levels">
      <div><span>支撑观察 · 非方向</span><strong class="flat">${support ? priceText(support) : "--"}</strong></div>
      <div><span>压力观察 · 非方向</span><strong class="flat">${resistance ? priceText(resistance) : "--"}</strong></div>
      <div><span>多头失效参考</span><strong class="flat">${support ? priceText(support * 0.992) : "--"}</strong></div>
      <div><span>空头失效参考</span><strong class="flat">${resistance ? priceText(resistance * 1.008) : "--"}</strong></div>
    </div>
    <div class="market-analysis-evidence">
      ${(evidence || []).slice(0, 4).map((item) => `<p>${escapeHtml(item)}</p>`).join("") || "<p>等待更多K线和成交量样本。</p>"}
    </div>
  `;
  renderMarketWorkflowStrip();
  renderAiRoomHeader();
}

function marketAiPayload() {
  const front = frontendMarketAiLocal();
  const meta = state.chartMeta || {};
  const chartMatchesSymbol = !state.chartDataSymbol || state.chartDataSymbol === state.symbol;
  const visible = chartMatchesSymbol ? meta.candles || visibleCandles().candles : [];
  return {
    symbol: state.symbol,
    bar: state.bar,
    price: state.lastPrice || state.candles[state.candles.length - 1]?.close || 0,
    question: $("marketAiQuestion")?.value.trim() || "",
    drawings: state.drawings.slice(-24),
    candles: (chartMatchesSymbol ? state.candles : []).slice(-300).map((candle) => ({
      ts: Number(candle.ts || 0),
      open: Number(candle.open || candle.close || 0),
      high: Number(candle.high || candle.close || 0),
      low: Number(candle.low || candle.close || 0),
      close: Number(candle.close || 0),
      volume: Number(candle.volume || 0),
    })),
    chart_context: {
      indicators: state.indicators,
      chart_mode: state.chartMode,
      visible_bars: visible.length,
      visible_start: visible[0]?.ts || 0,
      visible_end: visible[visible.length - 1]?.ts || 0,
      fib_levels: latestFibLevels(),
      frontend_snapshot: front,
      chart_ai: state.chartAi,
      candle_quality: state.chartCandleQuality,
      shared_snapshot: state.marketSnapshotContext || {},
      snapshot_source: state.chartQuality?.source || state.chartQuality?.sourceLabel || "",
      anomaly_radar: state.selectedAnomaly,
      trend_cockpit: state.trendCockpit ? {
        summary: state.trendCockpit.summary,
        preferred: state.trendCockpit.preferred,
        probabilities: state.trendCockpit.probabilities,
        key_levels: state.trendCockpit.key_levels,
        evidence: state.trendCockpit.evidence,
        counter_evidence: state.trendCockpit.counter_evidence,
        waiting_conditions: state.trendCockpit.waiting_conditions,
        safe_action: state.trendCockpit.safe_action,
      } : null,
    },
  };
}

function firstValue(...values) {
  for (const value of values) {
    if (value !== undefined && value !== null && value !== "") return value;
  }
  return "";
}

function marketResearchDirectionLabel(value) {
  const raw = String(value || "").trim().toUpperCase();
  if (raw === "RESEARCH_LONG" || raw === "LONG") return "研究偏多 · 非订单";
  if (raw === "RESEARCH_SHORT" || raw === "SHORT") return "研究偏空 · 非订单";
  if (raw === "RESEARCH_NEUTRAL" || raw === "WAIT" || raw === "HOLD") return "研究等待 · 非订单";
  return "研究方向待核验 · 非订单";
}

function marketPlanningValue(report = {}, localPlan = {}, key = "long_take_profit") {
  const planningKey = `planning_${key}`;
  const planKey = key.replace(/^long_|^short_/, "");
  return firstValue(report?.[planningKey], localPlan?.[planningKey], localPlan?.[`planning_${planKey}`], report?.[key], localPlan?.[planKey], "--");
}

function listBlock(title, rows) {
  const safeRows = Array.isArray(rows) ? rows.filter(Boolean).slice(0, 6) : [];
  if (!safeRows.length) return "";
  return `
    <div class="market-ai-list-block">
      <span>${escapeHtml(title)}</span>
      ${safeRows.map((row) => `<p>${escapeHtml(row)}</p>`).join("")}
    </div>
  `;
}

function aiReportHtml(report = {}, raw = {}, local = {}) {
  const hasStructured = report && Object.keys(report).length > 0;
  if (!hasStructured) {
    const fallback = raw?.content || raw?.error || "未返回结构化分析。";
    return `<div class="market-ai-raw">${escapeHtml(fallback)}</div>`;
  }
  const longPlan = local.long_plan || {};
  const shortPlan = local.short_plan || {};
  const preferred = firstValue(report.final_decision, report.preferred_direction, report.direction, "WAIT");
  const anomalyType = firstValue(report.anomaly_type, report.severity, "");
  const longRate = firstValue(report.long_win_rate_pct, longPlan.win_rate_pct, "--");
  const shortRate = firstValue(report.short_win_rate_pct, shortPlan.win_rate_pct, "--");
  const longTp = marketPlanningValue(report, longPlan, "long_take_profit");
  const longSl = marketPlanningValue(report, longPlan, "long_stop_loss");
  const shortTp = marketPlanningValue(report, shortPlan, "short_take_profit");
  const shortSl = marketPlanningValue(report, shortPlan, "short_stop_loss");
  const summary = firstValue(report.summary, report.answer, "等待结论");
  return `
    <div class="market-ai-report-summary">
      <strong>${escapeHtml(summary)}</strong>
      <span>方向：${escapeHtml(marketResearchDirectionLabel(preferred))}${anomalyType ? ` / 异动：${escapeHtml(anomalyType)}` : ""}</span>
      <span>${escapeHtml(report.safe_action || "观察 / 仅研究 / 仅模拟盘验证")}</span>
    </div>
    <div class="market-ai-plan-grid">
      <div><span>偏多估计 · 未校准</span><strong class="flat">${escapeHtml(longRate)}${String(longRate).includes("%") || longRate === "--" ? "" : "%"}</strong></div>
      <div><span>偏多规划 TP / SL</span><strong class="flat">${escapeHtml(longTp)} / ${escapeHtml(longSl)}</strong></div>
      <div><span>偏空估计 · 未校准</span><strong class="flat">${escapeHtml(shortRate)}${String(shortRate).includes("%") || shortRate === "--" ? "" : "%"}</strong></div>
      <div><span>偏空规划 TP / SL</span><strong class="flat">${escapeHtml(shortTp)} / ${escapeHtml(shortSl)}</strong></div>
    </div>
    ${report.deepseek_review ? listBlock("复核意见", [report.deepseek_review]) : ""}
    ${listBlock("关键证据", report.key_evidence || report.reasons || report.evidence)}
    ${listBlock("反证/失效", report.counter_evidence || report.invalidation || report.no_trade_conditions)}
    ${listBlock("等待条件", report.waiting_conditions || report.no_trade_conditions)}
    ${listBlock("交易法则", report.trading_rule_notes || report.risk_notes || report.warnings)}
    ${report.answer ? listBlock("回答", [report.answer]) : ""}
  `;
}

function renderMarketAiAnalysis(data) {
  state.marketAi = data;
  renderMarketAiLocal(data.local || null);
  const status = data.status || {};
  const paused = Boolean(data.local?.analysis_paused || status.analysis === "paused_data_quality");
  $("marketAiState").textContent = paused ? "数据待核，AI研究已暂停" : "双AI研究回执已更新 · 未校准";
  $("marketAiDeepSeekBadge").textContent = data.deepseek?.ok ? `${status.deepseek?.model || "DeepSeek"} · 研究回执` : data.deepseek?.error || "未配置";
  $("marketAiGptBadge").textContent = data.gpt?.ok ? `${status.gpt?.model || "GPT"} · 研究回执` : data.gpt?.error || "未配置";
  $("marketAiDeepSeekBadge").className = "flat";
  $("marketAiGptBadge").className = "flat";
  $("marketAiDeepSeekReport").innerHTML = aiReportHtml(data.analysis?.deepseek || {}, data.deepseek || {}, data.local || {});
  $("marketAiGptReport").innerHTML = aiReportHtml(data.analysis?.gpt || {}, data.gpt || {}, data.local || {});
}

async function runMarketAiAnalysis() {
  renderMarketAiLocal();
  await loadRuntimeKeyStatus().catch(() => null);
  $("marketAiState").textContent = "DeepSeek初评 + GPT复核中";
  $("marketAiDeepSeekBadge").textContent = "分析中";
  $("marketAiGptBadge").textContent = "排队中";
  $("marketAiDeepSeekBadge").className = "flat";
  $("marketAiGptBadge").className = "flat";
  $("marketAiDeepSeekReport").textContent = "正在把K线、成交量、画线、价格和交易法则交给 DeepSeek。";
  $("marketAiGptReport").textContent = "等待 DeepSeek 初评后复核。";
  try {
    const data = await apiPost("/api/ai/market/dual-analysis", marketAiPayload());
    renderMarketAiAnalysis(data);
  } catch (error) {
    $("marketAiState").textContent = "分析失败";
    $("marketAiDeepSeekBadge").textContent = "错误";
    $("marketAiGptBadge").textContent = "错误";
    $("marketAiDeepSeekBadge").className = "down";
    $("marketAiGptBadge").className = "down";
    $("marketAiDeepSeekReport").textContent = error.message;
    $("marketAiGptReport").textContent = "请确认后端服务、DeepSeek Key 和 OpenAI Key。";
  }
}

function renderTradingAgentsStatus(data) {
  state.tradingAgentsStatus = data || null;
  const target = $("tradingAgentsProviders");
  if (!target || !data) return;
  $("tradingAgentsState").textContent = "AI 研究接口状态已更新 · 不代表交易授权";
  $("tradingAgentsState").className = "flat";
  target.innerHTML = (data.rows || []).map((row) => {
    const missing = Array.isArray(row.missing) && row.missing.length ? `缺：${row.missing.join(", ")}` : "";
    const detail = [row.model || row.env || "--", row.auth_mode ? `auth=${row.auth_mode}` : "", missing || row.role_hint || ""].filter(Boolean).join(" / ");
    const statusText = row.configured ? "已配置" : row.partial_configured ? "部分配置" : "未配置";
    return `
      <div class="trading-agent-provider">
        <span>${escapeHtml(row.name || row.id || "--")}</span>
        <strong class="flat">${statusText}</strong>
        <em>${escapeHtml(detail)}</em>
      </div>
    `;
  }).join("") || `<div class="trading-agent-provider"><span>Provider</span><strong class="flat">未配置</strong><em>等待研究接口配置</em></div>`;
}

function renderMarketAiProviderStrip(rows = []) {
  const target = $("marketAiProviderStrip");
  if (!target) return;
  const order = [
    { id: "openai", label: "GPT" },
    { id: "deepseek", label: "DeepSeek" },
    { id: "doubao", label: "豆包" },
    { id: "glm", label: "GLM" },
  ];
  const byId = Object.fromEntries((rows || []).map((row) => [row.id, row]));
  let readyCount = 0;
  const missingLabels = [];
  target.innerHTML = order.map((item) => {
    const row = byId[item.id] || {};
    const configured = Boolean(row.configured);
    if (configured) readyCount += 1;
    else missingLabels.push(item.label);
    const source = row.source === "runtime" ? "内存" : row.source === "env" ? "环境" : "未接入";
    return `
      <div class="${configured ? "ready" : ""}">
        <span>${escapeHtml(item.label)}</span>
        <strong class="${configured ? "up" : "flat"}">${configured ? "KEY" : "WAIT"}</strong>
        <em>${escapeHtml(source)}</em>
      </div>
    `;
  }).join("");
  const readiness = $("marketAiReadiness");
  if (readiness) {
    const missingText = missingLabels.length ? `缺少 ${missingLabels.join(" / ")}` : "四个核心辩手已接入";
    readiness.textContent = `${readyCount}/4 AI 已接入；${missingText}。密钥只保存在本机内存，重启后失效。`;
    readiness.className = `market-ai-readiness ${readyCount >= 4 ? "ready" : readyCount > 0 ? "partial" : "missing"}`;
  }
}

async function loadTradingAgentsStatus() {
  try {
    const data = await api("/api/ai/trading-agents/status");
    renderTradingAgentsStatus(data);
    return data;
  } catch (error) {
    if ($("tradingAgentsState")) {
      $("tradingAgentsState").textContent = `Provider status offline: ${error.message}`;
      $("tradingAgentsState").className = "down";
    }
    return null;
  }
}

function renderRuntimeKeyStatus(data) {
  const target = $("runtimeKeyRows");
  if (!target || !data) return;
  renderMarketAiProviderStrip(data.rows || []);
  const readyRows = (data.rows || []).filter((row) => row.configured);
  const readyCount = readyRows.length;
  const sourceText = readyRows.length
    ? readyRows.map((row) => `${row.name || row.id}:${row.source === "runtime" ? "内存" : row.source === "env" ? "环境" : "未知"}`).join(" / ")
    : "尚未载入真实 Key";
  if ($("runtimeKeyState")) {
    $("runtimeKeyState").textContent = `${readyCount}/4 已接入；${sourceText}`;
  }
  target.innerHTML = (data.rows || []).map((row) => `
    <div class="runtime-key-row">
      <span>${escapeHtml(row.name || row.id || "--")}</span>
      <strong class="${row.configured ? "up" : "flat"}">${row.configured ? "KEY" : "WAIT"}</strong>
      <em>${escapeHtml(row.source === "runtime" ? "内存" : row.source === "env" ? "环境变量" : row.env || "--")}</em>
    </div>
  `).join("") || "";
}

async function loadRuntimeKeyStatus() {
  try {
    const data = await api("/api/ai/runtime-keys/status");
    renderRuntimeKeyStatus(data);
    return data;
  } catch (error) {
    if ($("runtimeKeyState")) $("runtimeKeyState").textContent = `密钥状态读取失败：${error.message}`;
    return null;
  }
}

function clearRuntimeKeyInputs() {
  ["runtimeOpenAIKey", "runtimeDeepSeekKey", "runtimeDoubaoKey", "runtimeGlmKey", "runtimeArkKey"].forEach((id) => {
    if ($(id)) $(id).value = "";
  });
}

async function saveRuntimeKeys() {
  const payload = {
    openai_api_key: $("runtimeOpenAIKey")?.value?.trim() || "",
    deepseek_api_key: $("runtimeDeepSeekKey")?.value?.trim() || "",
    doubao_api_key: $("runtimeDoubaoKey")?.value?.trim() || "",
    glm_api_key: $("runtimeGlmKey")?.value?.trim() || "",
    ark_api_key: $("runtimeArkKey")?.value?.trim() || "",
  };
  if (!payload.openai_api_key && !payload.deepseek_api_key && !payload.doubao_api_key && !payload.glm_api_key && !payload.ark_api_key) {
    if ($("runtimeKeyState")) $("runtimeKeyState").textContent = "没有新的密钥需要载入";
    return;
  }
  if ($("runtimeKeyState")) $("runtimeKeyState").textContent = "正在载入到本机内存";
  try {
    const data = await apiPost("/api/ai/runtime-keys", payload);
    clearRuntimeKeyInputs();
    renderRuntimeKeyStatus(data);
    await loadTradingAgentsStatus();
  } catch (error) {
    if ($("runtimeKeyState")) $("runtimeKeyState").textContent = `载入失败：${error.message}`;
  }
}

async function clearRuntimeKeys() {
  if ($("runtimeKeyState")) $("runtimeKeyState").textContent = "正在清空内存密钥";
  try {
    const data = await apiPost("/api/ai/runtime-keys/clear", { providers: ["openai", "deepseek", "ark", "doubao", "glm"] });
    clearRuntimeKeyInputs();
    renderRuntimeKeyStatus(data);
    await loadTradingAgentsStatus();
  } catch (error) {
    if ($("runtimeKeyState")) $("runtimeKeyState").textContent = `清空失败：${error.message}`;
  }
}

function tradingAgentList(title, rows) {
  const safeRows = Array.isArray(rows) ? rows.filter(Boolean).slice(0, 4) : [];
  if (!safeRows.length) return "";
  return `
    <div class="trading-agent-list-block">
      <span>${escapeHtml(title)}</span>
      ${safeRows.map((row) => `<p>${escapeHtml(row)}</p>`).join("")}
    </div>
  `;
}

function tradingAgentTranscriptRows(data) {
  if (!data) return [];
  if (Array.isArray(data.meeting_transcript) && data.meeting_transcript.length) return data.meeting_transcript;
  if (Array.isArray(data.debate) && data.debate.length) return data.debate;
  return [];
}

function tradingAgentEmptyTranscriptHtml() {
  return `
    <div class="trading-agent-debate-row empty">
      <div class="trading-agent-avatar">AI</div>
      <div class="trading-agent-bubble">
        <div class="trading-agent-debate-head"><span>RESEARCH_REVIEW</span><strong>Research minutes</strong></div>
        <em>--</em>
        <p>等待研究员会议纪要。</p>
      </div>
    </div>
  `;
}

function tradingAgentDebateRowHtml(row, index) {
  const status = row.status || row.round || "TALK";
  const isUser = row.provider === "user";
  const isTyping = status === "THINK" || status === "QUEUED";
  const displayStatus = isTyping ? "RESEARCH_REVIEW" : status === "ERROR" ? "RESEARCH_BLOCKED" : "RESEARCH_OBSERVE";
  const stance = row.stance ? ` / ${marketResearchDirectionLabel(row.stance)}` : "";
  const confidence = row.confidence_pct != null ? " / 未校准" : "";
  const roleTitle = row.role_title || row.role || "本轮研究员";
  const meta = [roleTitle, [row.provider, row.model].filter(Boolean).join(" / "), row.reply_to ? `回应 ${row.reply_to}` : ""].filter(Boolean).join(" · ");
  const message = row.message || row.raw_content || "--";
  const speaker = row.speaker || "--";
  const providerId = String(row.provider || "ai").toLowerCase().replace(/[^a-z0-9_-]/g, "") || "ai";
  const avatar = ({ user: "我", openai: "GPT", deepseek: "DS", doubao: "豆", glm: "GLM" })[providerId]
    || String(speaker).replace(/\s+/g, "").slice(0, 2).toUpperCase()
    || "AI";
  const chatKey = row.chat_key || row.order || index + 1;
  const orderLabel = isUser ? "已发送" : `#${row.order || index + 1} ${displayStatus}${stance}${confidence}`;
  return `
    <div class="trading-agent-debate-row provider-${escapeHtml(providerId)} flat${isTyping ? " is-typing" : ""}" data-chat-order="${escapeHtml(chatKey)}">
      <div class="trading-agent-avatar">${escapeHtml(avatar)}</div>
      <div class="trading-agent-bubble">
        <div class="trading-agent-debate-head">
          <span>${escapeHtml(orderLabel)}</span>
          <strong>${escapeHtml(speaker)}</strong>
        </div>
        ${isUser ? "" : `<div class="trading-agent-role-badge">本轮身份 · ${escapeHtml(roleTitle)}</div>`}
        ${isUser ? "" : `<em>${escapeHtml(meta || "--")}</em>`}
        ${isTyping ? `<div class="chat-typing"><span></span><span></span><span></span><em>${escapeHtml(message)}</em></div>` : `<p>${escapeHtml(message)}</p>`}
        ${tradingAgentList("赞同", row.agree_with)}
        ${tradingAgentList("质疑", row.challenge)}
        ${tradingAgentList("证据", row.evidence)}
        ${tradingAgentList("观察条件", row.watch_conditions)}
      </div>
    </div>
  `;
}

function upsertTradingAgentChatRow(row) {
  const target = $("tradingAgentDebateRows");
  if (!target || !row) return;
  const order = Number(row.order || 0);
  const current = order > 0 ? target.querySelector(`[data-chat-order="${order}"]`) : null;
  const html = tradingAgentDebateRowHtml(row, Math.max(0, order - 1));
  if (current) current.outerHTML = html;
  else target.insertAdjacentHTML("beforeend", html);
  target.scrollTop = target.scrollHeight;
}

function renderTradingAgentsStreamEvent(event) {
  if (!event) return;
  if (event.type === "roles") {
    const assignments = Array.isArray(event.role_assignments) ? event.role_assignments : [];
    assignments.slice(0, 1).forEach((row) => upsertTradingAgentChatRow({
      ...row,
      status: "THINK",
      stance: "WAIT",
      message: "正在阅读行情证据和研究问题",
    }));
    $("tradingAgentsState").textContent = "研究身份已分配，正在按顺序发言";
    return;
  }
  if (event.type === "typing" || event.type === "message") {
    upsertTradingAgentChatRow(event.row);
    if (event.type === "typing") $("tradingAgentsState").textContent = `${event.row?.speaker || "AI"} 正在输入`;
    return;
  }
  if (event.type === "complete") {
    renderTradingAgentsRoom(event.data, { skipTranscript: !event.fallback });
    if (event.fallback) {
      const target = $("tradingAgentDebateRows");
      target?.insertAdjacentHTML("afterbegin", tradingAgentDebateRowHtml({
        chat_key: "user",
        provider: "user",
        speaker: "我",
        status: "SENT",
        role_title: "研究问题",
        message: aiRoomMeetingQuestion(),
      }, 0));
      if (target) target.scrollTop = target.scrollHeight;
    }
  }
}

function renderTradingAgentTranscript(data) {
  const target = $("tradingAgentDebateRows");
  if (!target) return;
  const rows = tradingAgentTranscriptRows(data);
  target.innerHTML = rows.length ? rows.map((row, index) => tradingAgentDebateRowHtml(row, index)).join("") : tradingAgentEmptyTranscriptHtml();
}

function replayTradingAgentTranscript(data) {
  const target = $("tradingAgentDebateRows");
  const rows = tradingAgentTranscriptRows(data);
  if (!target || !rows.length) return;
  const seq = ++runtime.tradingAgentsTranscriptSeq;
  target.innerHTML = "";
  rows.forEach((row, index) => {
    setTimeout(() => {
      if (runtime.tradingAgentsTranscriptSeq !== seq) return;
      target.insertAdjacentHTML("beforeend", tradingAgentDebateRowHtml(row, index));
      target.scrollTop = target.scrollHeight;
    }, index * 620);
  });
}

function renderTradingAgentsRoom(data, options = {}) {
  runtime.tradingAgentsTranscriptSeq += 1;
  state.tradingAgents = data || null;
  if (!data) return;
  const final = data.final || {};
  const decision = final.decision || "RESEARCH_NEUTRAL";
  const decisionLabel = marketResearchDirectionLabel(decision);
  const project = data.project || (data.status && data.status.project) || {};
  const roleAssignments = Array.isArray(data.role_assignments) ? data.role_assignments : [];
  renderTradingAgentsStatus(data.status || state.tradingAgentsStatus || null);
  $("tradingAgentsState").textContent = `${data.symbol || state.symbol} 研究员会议纪要已生成 · 不代表授权`;
  $("tradingAgentsState").className = "flat";
  $("tradingAgentsFinal").innerHTML = `
    <div class="trading-agents-minutes-head">
      <strong>${escapeHtml(data.symbol || state.symbol)} 研究员会议纪要</strong>
      <span>${escapeHtml(data.safety || "仅观察 / 仅研究 / 仅模拟盘验证")}</span>
    </div>
    <div class="trading-agents-final-grid">
      <div><span>会议方向 · 研究标签</span><strong class="flat">${escapeHtml(decisionLabel)}</strong></div>
      <div><span>多头论据权重</span><strong class="flat">未校准</strong></div>
      <div><span>空头论据权重</span><strong class="flat">未校准</strong></div>
      <div><span>安全边界</span><strong>${escapeHtml(final.safe_action || data.safety || "仅研究")}</strong></div>
    </div>
    <div class="trading-agents-levels">
      <span>多头研究规划：目标区 ${priceText(final.planning_long_take_profit)} / 失效位 ${priceText(final.planning_long_stop_loss)}</span>
      <span>空头研究规划：目标区 ${priceText(final.planning_short_take_profit)} / 失效位 ${priceText(final.planning_short_stop_loss)}</span>
      <span>${final.risk_block ? "风险会议备注：波动或区间风险偏高" : "会议备注：继续观察，等待二次确认"}</span>
      <span>TradingAgents 结构：${project.ok ? "已接入研究流程" : "未接入"}</span>
    </div>
    ${roleAssignments.length ? `
      <div class="trading-agent-role-roster">
        <strong>本轮随机角色</strong>
        ${roleAssignments.map((row) => `<span>#${escapeHtml(row.order || "-")} ${escapeHtml(row.speaker || row.provider || "AI")} · ${escapeHtml(row.role_title || "研究员")}</span>`).join("")}
      </div>
    ` : ""}
  `;
  $("tradingAgentCards").innerHTML = (data.agents || []).map((agent) => {
    const stance = marketResearchDirectionLabel(agent.stance || "RESEARCH_NEUTRAL");
    return `
      <article class="trading-agent-card">
        <header>
          <span>${escapeHtml(agent.team || "--")}</span>
          <strong>${escapeHtml(agent.name || agent.id || "--")}</strong>
          <em class="flat">研究回执 / ${escapeHtml(agent.provider || "--")}</em>
        </header>
        <div class="trading-agent-stance">
          <strong class="flat">${escapeHtml(stance)}</strong>
          <span>未校准</span>
        </div>
        <div class="trading-agent-role-note">${escapeHtml(agent.role_hint || agent.provider || "研究员观点")}</div>
        <p>${escapeHtml(agent.summary || "--")}</p>
        ${tradingAgentList("证据", agent.evidence)}
        ${tradingAgentList("质疑", agent.challenges)}
        ${tradingAgentList("观察条件", agent.asks)}
      </article>
    `;
  }).join("") || `<div class="trading-agent-empty">等待研究员会议纪要</div>`;
  if (!options.skipTranscript) renderTradingAgentTranscript(data);
}

async function runTradingAgentsRoom() {
  if (runtime.tradingAgentsAbortController) runtime.tradingAgentsAbortController.abort();
  runtime.tradingAgentsAbortController = new AbortController();
  const controller = runtime.tradingAgentsAbortController;
  renderMarketAiLocal();
  syncAiRoomQuestionToMarketAi();
  const question = aiRoomMeetingQuestion();
  $("tradingAgentsState").textContent = "问题已发送，研究员正在进入聊天室";
  $("tradingAgentsState").className = "flat";
  $("tradingAgentsFinal").textContent = "正在为 Codex/GPT、DeepSeek、豆包、GLM/智谱随机分配研究身份；后发言者会读取并回应前序观点。";
  renderAiRoomPendingMeeting(question);
  loadRuntimeKeyStatus().catch(() => null);
  try {
    const payload = {
      ...marketAiPayload(),
      question,
      provider_mode: "auto",
      room_style: "tradingagents",
      stream: true,
    };
    await apiPostStream("/api/ai/trading-agents/discuss", payload, renderTradingAgentsStreamEvent, controller.signal);
  } catch (error) {
    if (error.name === "AbortError") return;
    $("tradingAgentsState").textContent = "讨论室失败";
    $("tradingAgentsState").className = "down";
    $("tradingAgentsFinal").textContent = error.message;
  } finally {
    if (runtime.tradingAgentsAbortController === controller) runtime.tradingAgentsAbortController = null;
  }
}

function isStockIntradayLineChart() {
  return isStockMarket() && isStockMinuteBar(state.bar) && state.chartMode === "line";
}

function stockIntradayAverageSeries(candles = []) {
  let cumulativeVolume = 0;
  let cumulativeValue = 0;
  let cumulativeClose = 0;
  return candles.map((candle, index) => {
    const close = Number(candle.close);
    const volume = Number(candle.volume || 0);
    if (!Number.isFinite(close) || close <= 0) return null;
    if (volume > 0) {
      cumulativeVolume += volume;
      cumulativeValue += close * volume;
      return cumulativeValue / Math.max(cumulativeVolume, 1);
    }
    cumulativeClose += close;
    return cumulativeClose / (index + 1);
  });
}

function drawStockIntradayAverageLine(ctx, candles, x, y, colors) {
  if (!isStockIntradayLineChart() || candles.length < 2) return;
  const averageSeries = stockIntradayAverageSeries(candles);
  drawLineOverlay(ctx, averageSeries, x, y, "rgba(239, 185, 11, 0.92)");
  const latestAverage = averageSeries.findLast((value) => Number.isFinite(value));
  if (!Number.isFinite(latestAverage)) return;
  ctx.fillStyle = colors.muted;
  ctx.font = "11px Segoe UI";
  ctx.fillText(`均价 ${priceText(latestAverage)}`, 64, 38);
}

function drawChart() {
  const canvas = $("priceChart");
  const parent = canvas.parentElement;
  const dpr = window.devicePixelRatio || 1;
  const footerRect = document.querySelector(".chart-footer")?.getBoundingClientRect();
  const canvasRect = canvas.getBoundingClientRect();
  const gridHeight = footerRect && footerRect.top > canvasRect.top ? footerRect.top - canvasRect.top : 0;
  const width = Math.max(320, Math.floor(parent.clientWidth || canvasRect.width || 720));
  const height = Math.max(300, Math.floor(gridHeight || canvas.clientHeight || parent.clientHeight - 160));
  canvas.width = Math.floor(width * dpr);
  canvas.height = Math.floor(height * dpr);
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;

  const ctx = canvas.getContext("2d");
  const upColor = chartUpColor();
  const downColor = chartDownColor();
  const colors = chartThemeColors();
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = colors.surface;
  ctx.fillRect(0, 0, width, height);

  const view = visibleCandles();
  const candles = view.candles;
  if (!candles.length) {
    canvas.dataset.chartSymbol = state.chartDataSymbol || state.symbol;
    canvas.dataset.candleCount = "0";
    canvas.dataset.minPrice = "";
    canvas.dataset.maxPrice = "";
    canvas.dataset.priceRange = "";
    ctx.fillStyle = colors.muted;
    ctx.font = "14px Segoe UI";
    ctx.fillText(`${state.symbol} 等待K线数据`, 24, 36);
    state.chartMeta = null;
    updateChartTooltip();
    return;
  }

  const showVolume = Boolean(state.indicators.volume);
  const pad = { left: 64, right: 88, top: 34, bottom: showVolume ? 134 : 56 };
  const chartW = width - pad.left - pad.right;
  const chartH = height - pad.top - pad.bottom;
  const rawMinPrice = Math.min(...candles.map((c) => c.low));
  const rawMaxPrice = Math.max(...candles.map((c) => c.high));
  if (!Number.isFinite(rawMinPrice) || !Number.isFinite(rawMaxPrice) || rawMaxPrice <= 0) {
    state.candles = previewCandlesForSymbol(state.symbol, state.bar, 140);
    state.chartDataSymbol = state.symbol;
    $("chartStatus").textContent = "快速预览K线 / 数据修复中";
    drawChart();
    return;
  }
  const referencePrice = candles[candles.length - 1]?.close || state.lastPrice || ((rawMinPrice + rawMaxPrice) / 2);
  const anchorPrices = chartScaleAnchorPrices(rawMinPrice, rawMaxPrice, referencePrice);
  const anchoredMinPrice = Math.min(rawMinPrice, ...anchorPrices);
  const anchoredMaxPrice = Math.max(rawMaxPrice, ...anchorPrices);
  const anchoredRange = chartPriceSpan(anchoredMinPrice, anchoredMaxPrice);
  const pricePadding = Math.max(anchoredRange * 0.08, Math.abs(referencePrice) * 0.001, 1e-10);
  const minPrice = rawMinPrice >= 0 ? Math.max(0, anchoredMinPrice - pricePadding) : anchoredMinPrice - pricePadding;
  const maxPrice = anchoredMaxPrice + pricePadding;
  const range = Math.max(maxPrice - minPrice, chartPriceSpan(minPrice, maxPrice));
  const y = (price) => pad.top + ((maxPrice - price) / range) * chartH;
  const x = (index) => pad.left + (index / Math.max(1, candles.length - 1)) * chartW;
  state.chartMeta = { width, height, pad, chartW, chartH, minPrice, maxPrice, range, candles, start: view.start, end: view.end, x, y };
  canvas.dataset.chartSymbol = state.chartDataSymbol || state.symbol;
  canvas.dataset.candleCount = String(candles.length);
  canvas.dataset.totalCandles = String(view.total || candles.length);
  canvas.dataset.minPrice = String(minPrice);
  canvas.dataset.maxPrice = String(maxPrice);
  canvas.dataset.priceRange = String(range);

  ctx.strokeStyle = colors.grid;
  ctx.lineWidth = 1;
  ctx.fillStyle = colors.muted;
  ctx.font = "11px Segoe UI";
  for (let i = 0; i <= 5; i += 1) {
    const yy = pad.top + (chartH / 5) * i;
    const price = maxPrice - (range / 5) * i;
    ctx.beginPath();
    ctx.moveTo(pad.left, yy);
    ctx.lineTo(width - pad.right, yy);
    ctx.stroke();
    ctx.fillText(priceText(price), width - pad.right + 10, yy + 4);
  }

  const latest = candles[candles.length - 1];
  const latestMove = latest.open ? ((latest.close - latest.open) / latest.open) * 100 : 0;
  const sourceText = $("chartStatus")?.textContent || "";
  ctx.fillStyle = cssMove(latestMove) === "up" ? upColor : cssMove(latestMove) === "down" ? downColor : colors.muted;
  ctx.font = "12px Segoe UI";
  ctx.fillText(
    `${state.symbol} ${isStockIntradayLineChart() ? `${stockIntradayLabel()} ${stockBarLabel(state.bar)}` : ""}  O ${priceText(latest.open)}  H ${priceText(latest.high)}  L ${priceText(latest.low)}  C ${priceText(latest.close)}  ${latestMove >= 0 ? "+" : ""}${number(latestMove, 2)}%`,
    pad.left,
    20,
  );
  if (sourceText.includes("离线种子") || sourceText.includes("非真实行情") || sourceText.includes("快速预览")) {
    ctx.fillStyle = "rgba(245, 182, 66, 0.92)";
    ctx.fillText("预览数据 / 不用于行情判断", Math.max(pad.left + 390, width - 280), 20);
  }

  if (state.chartMode === "line") {
    const firstClose = candles[0]?.close || 0;
    const lastClose = candles[candles.length - 1]?.close || firstClose;
    ctx.strokeStyle = lastClose >= firstClose ? upColor : downColor;
    ctx.lineWidth = 2;
    ctx.beginPath();
    candles.forEach((candle, index) => {
      const xx = x(index);
      const yy = y(candle.close);
      if (index === 0) ctx.moveTo(xx, yy);
      else ctx.lineTo(xx, yy);
    });
    ctx.stroke();
    drawStockIntradayAverageLine(ctx, candles, x, y, colors);
  } else {
    const candleW = Math.max(3, chartW / candles.length * 0.62);
    candles.forEach((candle, index) => {
      const xx = x(index);
      const color = candle.close >= candle.open ? upColor : downColor;
      ctx.strokeStyle = color;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.moveTo(xx, y(candle.high));
      ctx.lineTo(xx, y(candle.low));
      ctx.stroke();
      const bodyTop = y(Math.max(candle.open, candle.close));
      const bodyHeight = Math.max(1, Math.abs(y(candle.open) - y(candle.close)));
      ctx.fillRect(xx - candleW / 2, bodyTop, candleW, bodyHeight);
    });
  }

  if (state.indicators.ma) {
    const ma20 = movingAverage(candles, 20);
    const ma60 = movingAverage(candles, 60);
    drawLineOverlay(ctx, ma20, x, y, "#f5b642");
    drawLineOverlay(ctx, ma60, x, y, "#43d7ff");
  }

  if (state.indicators.bollinger) {
    const bands = bollingerBands(candles, 20, 2);
    drawLineOverlay(ctx, bands.map((band) => band?.upper ?? null), x, y, "rgba(143,155,150,.85)");
    drawLineOverlay(ctx, bands.map((band) => band?.mid ?? null), x, y, "rgba(143,155,150,.45)");
    drawLineOverlay(ctx, bands.map((band) => band?.lower ?? null), x, y, "rgba(143,155,150,.85)");
  }

  if (state.indicators.signals && state.paper?.signals?.length) {
    drawSignalMarkers(ctx, candles, x, y);
  }

  if (showVolume) {
    const volTop = height - pad.bottom + 22;
    const volH = Math.max(64, pad.bottom - 72);
    ctx.strokeStyle = colors.grid;
    ctx.beginPath();
    ctx.moveTo(pad.left, volTop - 10);
    ctx.lineTo(width - pad.right, volTop - 10);
    ctx.stroke();
    ctx.fillStyle = colors.muted;
    ctx.font = "11px Segoe UI";
    ctx.fillText("VOL", pad.left, volTop - 18);
    const maxVol = Math.max(1, ...candles.map((c) => c.volume));
    const barW = Math.max(2, chartW / candles.length * 0.65);
    candles.forEach((candle, index) => {
      const xx = x(index);
      const vh = (candle.volume / maxVol) * volH;
      ctx.fillStyle = candle.close >= candle.open ? chartAlpha(upColor, 0.35) : chartAlpha(downColor, 0.35);
      ctx.fillRect(xx - barW / 2, volTop + volH - vh, barW, vh);
    });
  }

  drawVolumeProfile(ctx, candles, state.chartMeta);
  drawAutoMarks(ctx, state.chartMeta);
  drawUserDrawings(ctx, state.chartMeta);
  drawStrategyAnchors(ctx, state.chartMeta);

  const lastPrice = state.lastPrice || candles[candles.length - 1].close;
  if (Number.isFinite(lastPrice) && priceFitsCurrentChart(lastPrice, referencePrice) && lastPrice >= minPrice && lastPrice <= maxPrice) {
    const yy = y(lastPrice);
    ctx.strokeStyle = "rgba(239,185,11,.72)";
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    ctx.moveTo(pad.left, yy);
    ctx.lineTo(width - pad.right, yy);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "#efb90b";
    ctx.fillText(priceText(lastPrice), width - pad.right + 10, yy + 4);
  }

  if (state.chartHover) {
    const hover = state.chartHover;
    const candle = candles[hover.localIndex];
    if (candle) {
      const xx = x(hover.localIndex);
      const yy = y(candle.close);
      ctx.strokeStyle = colors.hover;
      ctx.setLineDash([3, 4]);
      ctx.beginPath();
      ctx.moveTo(xx, pad.top);
      ctx.lineTo(xx, height - pad.bottom);
      ctx.moveTo(pad.left, yy);
      ctx.lineTo(width - pad.right, yy);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }

  const firstDate = formatCandleTime(candles[0].ts);
  const lastDate = formatCandleTime(candles[candles.length - 1].ts);
  const liveText = state.chartQuality?.realtime ? " / realtime" : " / latest";
  const dragText = state.chartView.offset > 0 ? ` / back ${state.chartView.offset} bars` : liveText;
  $("chartRange").textContent = `${firstDate} -> ${lastDate}${dragText}`;
  renderChartStrategyOverlay();
  updateChartTooltip();
}

function drawLineOverlay(ctx, values, x, y, color) {
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  let started = false;
  values.forEach((value, index) => {
    if (value === null || value === undefined || !Number.isFinite(value)) {
      return;
    }
    const xx = x(index);
    const yy = y(value);
    if (!started) {
      ctx.moveTo(xx, yy);
      started = true;
    } else {
      ctx.lineTo(xx, yy);
    }
  });
  if (started) ctx.stroke();
}

function drawSignalMarkers(ctx, candles, x, y) {
  const recent = state.paper.signals.slice(-8);
  const upColor = chartUpColor();
  const downColor = chartDownColor();
  recent.forEach((signal, index) => {
    const candleIndex = Math.max(0, candles.length - 1 - index * 8);
    const candle = candles[candleIndex];
    if (!candle) return;
    const action = signal.action;
    if (!["BUY", "SELL", "EXIT"].includes(action)) return;
    const color = action === "BUY" ? upColor : downColor;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(x(candleIndex), y(candle.close), 4.5, 0, Math.PI * 2);
    ctx.fill();
  });
}

function chartPoint(event) {
  const rect = $("priceChart").getBoundingClientRect();
  return {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top,
  };
}

function updateChartHover(event) {
  const meta = state.chartMeta;
  if (!meta) return;
  const point = chartPoint(event);
  if (point.x < meta.pad.left || point.x > meta.width - meta.pad.right || point.y < meta.pad.top || point.y > meta.height - meta.pad.bottom) {
    state.chartHover = null;
    drawChart();
    return;
  }
  const ratio = (point.x - meta.pad.left) / Math.max(1, meta.chartW);
  const localIndex = clampNumber(Math.round(ratio * (meta.candles.length - 1)), 0, meta.candles.length - 1);
  state.chartHover = { localIndex, x: point.x, y: point.y };
  drawChart();
}

function bindChartEvents() {
  const canvas = $("priceChart");
  canvas.addEventListener("mousemove", (event) => {
    if (state.draftDrawing) {
      const point = drawingPointFromEvent(event);
      if (point) {
        state.draftDrawing.p2 = state.draftDrawing.type === "horizontal" ? { ...point, price: state.draftDrawing.p1.price } : point;
        drawChart();
      }
      return;
    }
    if (state.chartView.dragging && state.chartMeta) {
      const dx = event.clientX - state.chartView.dragX;
      const candleStep = state.chartMeta.chartW / Math.max(1, state.chartMeta.candles.length - 1);
      const delta = Math.round(dx / Math.max(1, candleStep));
      const maxOffset = Math.max(0, state.candles.length - state.chartView.visible);
      state.chartView.offset = clampNumber(state.chartView.dragOffset + delta, 0, maxOffset);
      drawChart();
      return;
    }
    updateChartHover(event);
  });
  canvas.addEventListener("mousedown", (event) => {
    if (state.drawingTool !== "cursor") {
      const point = drawingPointFromEvent(event);
      if (!point) return;
      state.draftDrawing = {
        id: `D${Date.now()}`,
        type: state.drawingTool,
        p1: point,
        p2: point,
      };
      state.chartHover = null;
      drawChart();
      event.preventDefault();
      return;
    }
    state.chartView.dragging = true;
    state.chartView.dragX = event.clientX;
    state.chartView.dragOffset = state.chartView.offset;
    canvas.classList.add("dragging");
  });
  window.addEventListener("mouseup", (event) => {
    if (state.draftDrawing) {
      const point = drawingPointFromEvent(event);
      if (point) {
        state.draftDrawing.p2 = state.draftDrawing.type === "horizontal" ? { ...point, price: state.draftDrawing.p1.price } : point;
      }
      if (Math.abs((state.draftDrawing.p2?.index || 0) - state.draftDrawing.p1.index) > 0 || Math.abs((state.draftDrawing.p2?.price || 0) - state.draftDrawing.p1.price) > 0) {
        state.drawings.push(state.draftDrawing);
        state.drawings = state.drawings.slice(-40);
        saveDrawings();
      }
      state.draftDrawing = null;
      drawChart();
    }
    state.chartView.dragging = false;
    canvas.classList.remove("dragging");
  });
  canvas.addEventListener("mouseleave", () => {
    if (!state.chartView.dragging) {
      state.chartHover = null;
      drawChart();
    }
  });
  canvas.addEventListener("wheel", (event) => {
    event.preventDefault();
    const direction = event.deltaY > 0 ? 1 : -1;
    const next = state.chartView.visible + direction * 24;
    state.chartView.visible = clampNumber(next, 40, Math.max(80, Math.min(800, state.candles.length || 300)));
    state.chartView.offset = clampNumber(state.chartView.offset, 0, Math.max(0, state.candles.length - state.chartView.visible));
    runtime.chartUserZoomed = true;
    drawChart();
  }, { passive: false });
  canvas.addEventListener("dblclick", () => {
    state.chartView.offset = 0;
    state.chartView.visible = isStockMarket() ? stockVisibleBarsForBar(state.bar) : 180;
    runtime.chartUserZoomed = false;
    drawChart();
  });
}

function connectSocket() {
  if (state.socket) {
    state.socket.onclose = null;
    state.socket.close();
    state.socket = null;
  }
  clearTimeout(state.reconnectTimer);
  const requestVersion = runtime.symbolVersion;
  const requestSymbol = state.symbol;
  const requestInstId = okxInstId(requestSymbol);
  const requestBar = state.bar;
  if (isStockMarket(requestSymbol)) {
    setConnection("Stock REST", "flat");
    return;
  }
  setConnection("Connecting", "flat");

  const socket = new WebSocket("wss://ws.okx.com:8443/ws/v5/public");
  state.socket = socket;
  socket.onopen = () => {
    if (requestVersion !== runtime.symbolVersion || requestSymbol !== state.symbol || state.socket !== socket) {
      socket.close();
      return;
    }
    setConnection("Realtime", "up");
    socket.send(JSON.stringify({
      op: "subscribe",
      args: [
        { channel: "tickers", instId: requestInstId },
        { channel: "books5", instId: requestInstId },
        { channel: "trades", instId: requestInstId },
        { channel: `candle${requestBar}`, instId: requestInstId },
      ],
    }));
  };
  socket.onmessage = (event) => {
    if (requestVersion !== runtime.symbolVersion || requestSymbol !== state.symbol || state.socket !== socket) return;
    const message = JSON.parse(event.data);
    if (!message.arg || !message.data) return;
    const channel = message.arg.channel || "";
    if (message.arg.instId !== requestInstId) return;
    if (channel === "tickers") updateTicker(message.data[0], "WS");
    if (channel === "books5") updateBook(message.data[0]);
    if (channel === "trades") addTrades(message.data);
    if (channel.startsWith("candle")) updateCandle(message.data[0]);
  };
  socket.onerror = () => {
    if (requestVersion === runtime.symbolVersion && requestSymbol === state.symbol && state.socket === socket) setConnection("WS error", "down");
  };
  socket.onclose = () => {
    if (requestVersion !== runtime.symbolVersion || requestSymbol !== state.symbol || state.socket !== socket) return;
    state.socket = null;
    setConnection("Reconnecting", "down");
    state.reconnectTimer = setTimeout(connectSocket, 3000);
  };
}

function connectMarketSocket() {
  if (state.marketSocket) {
    state.marketSocket.onclose = null;
    state.marketSocket.close();
  }
  clearTimeout(state.marketReconnectTimer);
  const socket = new WebSocket("wss://ws.okx.com:8443/ws/v5/public");
  state.marketSocket = socket;
  socket.onopen = () => {
    $("marketTickerState").textContent = "后台实时";
    const okxMarkets = markets.filter((market) => market.source === "okx");
    socket.send(JSON.stringify({
      op: "subscribe",
      args: okxMarkets.map((market) => ({ channel: "tickers", instId: market.instId || market.symbol })),
    }));
  };
  socket.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (!message.arg || !message.data || message.arg.channel !== "tickers") return;
    for (const row of message.data) updateMarketFromTicker(row);
    scheduleMarketRender(true);
  };
  socket.onerror = () => {
    $("marketTickerState").textContent = "后台异常";
  };
  socket.onclose = () => {
    $("marketTickerState").textContent = "后台重连";
    state.marketReconnectTimer = setTimeout(connectMarketSocket, 5000);
  };
}

async function fallbackPoll() {
  const requestVersion = runtime.symbolVersion;
  const requestSymbol = state.symbol;
  const requestIsStock = isStockMarket(requestSymbol);
  const requestInstId = okxInstId(requestSymbol);
  try {
    if (requestIsStock) {
      await pollLiveTicker(false);
      if (requestVersion !== runtime.symbolVersion || requestSymbol !== state.symbol) return;
      renderBook();
      renderTrades();
      return;
    }
    const [ticker, books, trades] = await Promise.all([
      api(`/api/okx/ticker?instId=${encodeURIComponent(requestInstId)}`),
      api(`/api/okx/books?instId=${encodeURIComponent(requestInstId)}&sz=20`),
      api(`/api/okx/trades?instId=${encodeURIComponent(requestInstId)}&limit=30`),
    ]);
    if (requestVersion !== runtime.symbolVersion || requestSymbol !== state.symbol) return;
    updateTicker(ticker.payload.data[0], "REST");
    updateBook(books.payload.data[0]);
    addTrades((trades.payload.data || []).reverse());
  } catch (error) {
    if (requestVersion === runtime.symbolVersion && requestSymbol === state.symbol) setConnection("本地/离线", "flat");
  }
}

async function pollLiveTicker(force = false) {
  const requestVersion = runtime.symbolVersion;
  const requestSymbol = state.symbol;
  const requestIsStock = isStockMarket(requestSymbol);
  const requestInstId = okxInstId(requestSymbol);
  let controller = null;
  try {
    if (requestIsStock) {
      const now = Date.now();
      if (!force && runtime.stockQuoteInFlight) return;
      if (!force && runtime.stockQuoteSymbol === requestSymbol && now - runtime.stockQuoteAt < 9000) return;
      const seq = ++runtime.stockQuoteSeq;
      runtime.stockQuoteAbortController?.abort();
      controller = new AbortController();
      runtime.stockQuoteAbortController = controller;
      runtime.stockQuoteInFlight = true;
      runtime.stockQuoteAt = now;
      runtime.stockQuoteSymbol = requestSymbol;
      const data = await api(`/api/stocks/quote?symbol=${encodeURIComponent(requestSymbol)}`, { signal: controller.signal });
      if (seq !== runtime.stockQuoteSeq || requestVersion !== runtime.symbolVersion || state.symbol !== requestSymbol) return;
      updateTicker(data.quote, String(data.quote?.source || "STOCK").toUpperCase());
    } else {
      const ticker = await api(`/api/okx/ticker?instId=${encodeURIComponent(requestInstId)}`);
      if (requestVersion !== runtime.symbolVersion || requestSymbol !== state.symbol) return;
      updateTicker(ticker.payload.data[0], "REST");
    }
  } catch (error) {
    if (isAbortError(error)) return;
    if (requestVersion === runtime.symbolVersion && requestSymbol === state.symbol) setConnection("后端离线", "down");
  } finally {
    if (!controller || runtime.stockQuoteAbortController === controller) {
      runtime.stockQuoteInFlight = false;
      if (controller) runtime.stockQuoteAbortController = null;
    }
  }
}

async function loadStrategies() {
  const data = await api("/api/strategies");
  state.strategies = data.strategies || [];
  $("strategySelect").innerHTML = state.strategies.map((strategy) => `<option value="${strategy.id}">${strategy.name}</option>`).join("");
  renderStrategyCards();
  if (!state.activeStrategyPreset) applyStrategyPreset("research", { refresh: false });
}

function makePreset(id, label, tone, values) {
  return {
    id,
    label,
    tone,
    riskSource: "MANUAL",
    riskValueMode: "PCT",
    orderType: "LIMIT",
    marginMode: "ISOLATED",
    trailingTakeEnabled: true,
    trailingStopEnabled: true,
    reduceOnly: false,
    ...values,
    leverage: VALIDATED_STRATEGY_LEVERAGE,
    trailingTakeEnabled: false,
    trailingStopEnabled: false,
    orderType: "CURRENT",
    marginMode: "CROSS",
  };
}

function strategyPresetCatalog(strategyId) {
  const strategy = state.strategies.find((item) => item.id === strategyId) || {};
  const researchRisk = strategy.research_risk_profile?.risk || {};
  const research = makePreset("research", "研究基线", "因果验证", {
    leverage: 1,
    position: Number(researchRisk.position_pct ?? 20),
    takeProfit: Number(researchRisk.take_profit_pct ?? 0),
    stopLoss: Number(researchRisk.stop_loss_pct ?? 0),
    riskProfileId: strategy.research_risk_profile?.profile_id || "",
    orderType: "CURRENT",
    marginMode: "CROSS",
    note: "与内部策略矩阵风险合同一致；通过前仅用于研究。",
  });
  const trend = [
    research,
    makePreset("conservative", "Conservative Trend", "Low risk", { leverage: 1, position: 12, takeProfit: 2.0, stopLoss: 1.0, trailingTakePct: 1.0, trailingStopPct: 0.7, orderType: "CURRENT", marginMode: "CROSS", note: "Small size, wait for trend confirmation." }),
    makePreset("standard", "Standard Trend", "Balanced", { leverage: 2, position: 20, takeProfit: 3.0, stopLoss: 1.4, trailingTakePct: 1.4, trailingStopPct: 1.0, orderType: "LIMIT", marginMode: "ISOLATED", note: "Enter on pullback; stop near trend failure." }),
    makePreset("aggressive", "Aggressive Trend", "High volatility", { leverage: 3, position: 28, takeProfit: 4.5, stopLoss: 1.8, trailingTakePct: 1.8, trailingStopPct: 1.2, orderType: "IOC", marginMode: "ISOLATED", note: "Only for strong trend and paper testing." }),
  ];
  const grid = [
    makePreset("conservative", "Narrow Grid", "Low risk", { leverage: 1, position: 8, takeProfit: 1.0, stopLoss: 3.0, trailingTakeEnabled: false, trailingStopEnabled: true, trailingStopPct: 1.4, orderType: "LIMIT", note: "Low size range test." }),
    makePreset("standard", "Standard Grid", "Range", { leverage: 2, position: 14, takeProfit: 1.6, stopLoss: 4.5, trailingTakeEnabled: false, trailingStopEnabled: true, trailingStopPct: 1.8, orderType: "LIMIT", note: "For range markets; stop when range breaks." }),
    makePreset("aggressive", "Dense Grid", "High frequency", { leverage: 3, position: 20, takeProfit: 2.2, stopLoss: 6.0, trailingTakeEnabled: false, trailingStopEnabled: true, trailingStopPct: 2.4, orderType: "POST_ONLY", note: "Cost-focused, higher trend risk." }),
  ];
  const martingale = [
    makePreset("conservative", "Small Martingale", "High risk capped", { leverage: 1, position: 6, takeProfit: 1.0, stopLoss: 4.0, trailingTakeEnabled: false, trailingStopEnabled: true, trailingStopPct: 1.8, orderType: "LIMIT", note: "Very small first layer; no unlimited averaging." }),
    makePreset("standard", "Four-layer Martingale", "Counter trend", { leverage: 2, position: 10, takeProfit: 1.4, stopLoss: 6.0, trailingTakeEnabled: false, trailingStopEnabled: true, trailingStopPct: 2.2, orderType: "LIMIT", note: "Layer by anchors; stop averaging at stop line." }),
    makePreset("aggressive", "Aggressive Martingale", "Extreme risk", { leverage: 3, position: 16, takeProfit: 2.0, stopLoss: 8.0, trailingTakeEnabled: false, trailingStopEnabled: true, trailingStopPct: 2.8, orderType: "LIMIT", note: "Paper observation only; one-way trend is dangerous." }),
  ];
  const antiMartingale = [
    makePreset("conservative", "Anti-Martingale Safe", "Trend", { leverage: 1, position: 12, takeProfit: 2.2, stopLoss: 0.9, trailingTakePct: 1.0, trailingStopPct: 0.6, orderType: "CURRENT", marginMode: "CROSS", note: "Add only after profit; protect principal first." }),
    makePreset("standard", "Anti-Martingale Standard", "Scale winners", { leverage: 2, position: 18, takeProfit: 3.4, stopLoss: 1.2, trailingTakePct: 1.4, trailingStopPct: 0.9, orderType: "LIMIT", note: "Add gradually in clear trend; reduce on pullback." }),
    makePreset("aggressive", "Anti-Martingale Strong", "Momentum", { leverage: 3, position: 26, takeProfit: 5.0, stopLoss: 1.6, trailingTakePct: 2.0, trailingStopPct: 1.2, orderType: "IOC", note: "Only under strong trend and volume." }),
  ];
  const livermore = [
    makePreset("conservative", "Pivot Watch", "Breakout confirm", { leverage: 1, position: 10, takeProfit: 2.4, stopLoss: 1.0, trailingTakePct: 1.0, trailingStopPct: 0.7, orderType: "POST_ONLY", note: "Wait for breakout and retest." }),
    makePreset("standard", "Pivot Breakout", "Classic", { leverage: 2, position: 18, takeProfit: 3.6, stopLoss: 1.4, trailingTakePct: 1.5, trailingStopPct: 1.0, orderType: "LIMIT", note: "Small probe after confirmed breakout." }),
    makePreset("aggressive", "Breakout Follow", "Momentum", { leverage: 3, position: 25, takeProfit: 5.2, stopLoss: 1.9, trailingTakePct: 2.2, trailingStopPct: 1.3, orderType: "IOC", note: "For strong volume breakout; strict stop." }),
  ];
  const meanReversion = [
    research,
    makePreset("conservative", "Mean Revert Safe", "Low risk", { leverage: 1, position: 10, takeProfit: 1.5, stopLoss: 1.2, trailingTakePct: 0.8, trailingStopPct: 0.8, orderType: "CURRENT", marginMode: "CROSS", note: "Only confirmed mean-reversion signals." }),
    makePreset("standard", "Mean Revert Standard", "Balanced", { leverage: 2, position: 16, takeProfit: 2.2, stopLoss: 1.6, trailingTakePct: 1.1, trailingStopPct: 1.0, orderType: "LIMIT", note: "Take profit near mean zone." }),
    makePreset("aggressive", "Mean Revert Aggressive", "High volatility", { leverage: 3, position: 22, takeProfit: 3.0, stopLoss: 2.0, trailingTakePct: 1.5, trailingStopPct: 1.3, orderType: "LIMIT", note: "For wide range markets only." }),
  ];
  const common = {
    dual_ma: trend,
    grid,
    martingale,
    anti_martingale: antiMartingale,
    livermore,
  };
  if (common[strategyId]) return common[strategyId];
  if (["bollinger", "rsi"].includes(strategyId)) return meanReversion;
  return [
    research,
    makePreset("conservative", "Conservative Template", "Low risk", { leverage: 1, position: 10, takeProfit: 2.0, stopLoss: 1.0, trailingTakePct: 0.9, trailingStopPct: 0.7, orderType: "CURRENT", marginMode: "CROSS", note: "Small size until the strategy proves itself." }),
    makePreset("standard", "Standard Template", "Balanced", { leverage: 2, position: 18, takeProfit: 3.0, stopLoss: 1.4, trailingTakePct: 1.4, trailingStopPct: 1.0, orderType: "LIMIT", marginMode: "ISOLATED", note: "Default paper observation profile." }),
    makePreset("aggressive", "Aggressive Template", "High volatility", { leverage: 3, position: 25, takeProfit: 4.5, stopLoss: 1.9, trailingTakePct: 2.0, trailingStopPct: 1.3, orderType: "IOC", marginMode: "ISOLATED", note: "Only for strong signals in paper mode." }),
  ];
}
function renderStrategyPresetPanel() {
  if (!$("strategyPresetCards")) return;
  const strategyId = $("strategySelect").value || "dual_ma";
  const presets = strategyPresetCatalog(strategyId);
  const activeId = state.activeStrategyPreset?.strategyId === strategyId ? state.activeStrategyPreset.id : "";
  $("strategyPresetCards").innerHTML = presets.map((preset) => `
    <button class="strategy-preset-card ${preset.id === activeId ? "active" : ""}" data-strategy-preset="${preset.id}">
      <span>${preset.tone}</span>
      <strong>${preset.label}</strong>
      <em>${preset.leverage}x / ${preset.position}% / ${preset.riskProfileId === "TREND_STRUCTURE_EXIT" && preset.takeProfit === 0 ? "结构退出" : `TP ${preset.takeProfit}%`} / SL ${preset.stopLoss}%</em>
      <small>${preset.note}</small>
    </button>
  `).join("");
  document.querySelectorAll("[data-strategy-preset]").forEach((button) => {
    button.addEventListener("click", () => applyStrategyPreset(button.dataset.strategyPreset));
  });
}

function applyStrategyPreset(presetId, options = {}) {
  const strategyId = $("strategySelect").value || "dual_ma";
  const preset = strategyPresetCatalog(strategyId).find((item) => item.id === presetId);
  if (!preset) return;
  $("leverageInput").value = String(preset.leverage);
  $("positionInput").value = String(preset.position);
  $("riskSource").value = preset.riskSource;
  $("riskValueMode").value = preset.riskValueMode;
  $("takeProfitInput").value = String(preset.takeProfit);
  $("stopLossInput").value = String(preset.stopLoss);
  $("strategyOrderType").value = preset.orderType;
  $("marginMode").value = preset.marginMode;
  $("trailingTakeEnabled").checked = Boolean(preset.trailingTakeEnabled);
  $("trailingTakePct").value = String(preset.trailingTakePct || 1.5);
  $("trailingStopEnabled").checked = Boolean(preset.trailingStopEnabled);
  $("trailingStopPct").value = String(preset.trailingStopPct || 1);
  $("reduceOnly").checked = Boolean(preset.reduceOnly);
  state.activeStrategyPreset = { ...preset, strategyId };
  state.latestStrategyAnalysis = null;
  syncRiskPlaceholders();
  renderStrategyPresetPanel();
  renderStrategyCommandStrip();
  renderStrategyExplainPanel();
  $("strategyAnalysis").textContent = `已套用 ${preset.label}，可继续手动微调或点击 AI 分析`;
  if (options.refresh !== false) {
    loadStrategyWarRoom();
    loadStrategyDoctor();
    estimateOrder();
  }
}

function renderStrategyCards() {
  const selected = $("strategySelect").value || "dual_ma";
  if (state.activeStrategyPreset?.strategyId && state.activeStrategyPreset.strategyId !== selected) {
    state.activeStrategyPreset = null;
  }
  $("strategyCards").innerHTML = state.strategies.map((strategy) => `
    <div class="strategy-card ${strategy.id === selected ? "active" : ""}" data-strategy="${strategy.id}">
      <div class="strategy-tag">${strategy.style}</div>
      <h3>${strategy.name}</h3>
      <p>${strategy.description}</p>
    </div>
  `).join("");
  document.querySelectorAll(".strategy-card").forEach((card) => {
    card.addEventListener("click", () => {
      $("strategySelect").value = card.dataset.strategy;
      renderStrategyCards();
      loadStrategyLab();
      loadStrategyWarRoom();
      loadStrategyDoctor();
      loadBotCenter();
      loadBotScheduler();
    });
  });
  renderStrategyDetail();
  renderStrategyParams();
  renderStrategyPresetPanel();
  renderStrategyCommandStrip();
}

function renderStrategyDetail() {
  const selected = $("strategySelect").value || state.paper?.strategy?.id || "dual_ma";
  const strategy = state.strategies.find((item) => item.id === selected) || state.paper?.strategy;
  if (!strategy) return;
  $("strategyDetailTitle").textContent = `${strategy.name} / ${strategy.style}`;
  const params = strategy.params || {};
  const recentSignal = state.paper?.signals?.slice(-1)[0];
  const analysis = state.paper?.ai_analysis || recentSignal?.analysis || {};
  const analysisTakeProfit = strategyPlanningValue(analysis, "take_profit");
  const analysisStopLoss = strategyPlanningValue(analysis, "stop_loss");
  const recentSignalPresentation = recentSignal
    ? evidenceStrategyActionPresentation(recentSignal.action)
    : null;
  $("strategyDetail").innerHTML = `
    <div class="strategy-detail-card"><span>策略说明</span><strong>${strategy.description || "--"}</strong></div>
    <div class="strategy-detail-card"><span>适用风格</span><strong>${strategy.style || "--"}</strong></div>
    <div class="strategy-detail-card"><span>核心参数</span><strong>${Object.entries(params).map(([key, value]) => `${key}: ${value}`).join(" / ") || "--"}</strong></div>
    <div class="strategy-detail-card"><span>最近研究信号</span><strong>${recentSignal ? `${recentSignalPresentation?.conclusionText || "研究观察"} / ${recentSignal.reason || "--"}` : "暂无信号"}</strong></div>
    <div class="strategy-detail-card"><span>模型估计（未校准）</span><strong>${analysis.profit_probability ? `${number(analysis.profit_probability * 100, 0)}% · 未校准 / ${analysis.probability_level || ""}` : "模型估计未校准"}</strong></div>
    <div class="strategy-detail-card"><span>研究价格规划</span><strong>${analysisTakeProfit ? `规划 TP ${number(analysisTakeProfit, 2)} / 规划 SL ${number(analysisStopLoss, 2)} · 非订单` : "--"}</strong></div>
  `;
}

function renderStrategyParams() {
  const selected = $("strategySelect").value || "dual_ma";
  const strategy = state.strategies.find((item) => item.id === selected);
  const params = strategy?.params || {};
  const target = $("strategyParamRows");
  if (!target) return;
  target.innerHTML = Object.entries(params).map(([key, value]) => `
    <label class="param-row">
      <span>${key}</span>
      <input data-strategy-param="${key}" value="${value}">
    </label>
  `).join("") || `<div class="param-row"><span>暂无参数</span><input disabled value="--"></div>`;
}

function strategyRawDirection(analysis = {}) {
  const raw = String(analysis.raw_direction || analysis.direction || "").trim().toUpperCase();
  if (raw === "RESEARCH_LONG") return "LONG";
  if (raw === "RESEARCH_SHORT") return "SHORT";
  return ["LONG", "SHORT"].includes(raw) ? raw : "";
}

function strategyPlanningValue(analysis = {}, key = "take_profit") {
  const planningKey = `planning_${key}`;
  const planned = analysis?.[planningKey];
  if (planned !== undefined && planned !== null && planned !== "") return planned;
  return analysis?.[key] ?? 0;
}

function strategyPlanningDirectionText(analysis = {}) {
  const raw = strategyRawDirection(analysis);
  return raw === "LONG" ? "研究偏多 · 非订单" : raw === "SHORT" ? "研究偏空 · 非订单" : "方向未形成 · 非订单";
}

function renderStrategyAnalysis(analysis) {
  const cards = $("aiAnalysisCards");
  const planningTakeProfit = strategyPlanningValue(analysis, "take_profit");
  const planningStopLoss = strategyPlanningValue(analysis, "stop_loss");
  if (!analysis || (!planningTakeProfit && !planningStopLoss && !analysis.profit_probability)) {
    state.latestStrategyAnalysis = null;
    $("strategyAnalysis").textContent = "等待策略分析";
    if (cards) {
      cards.innerHTML = `
        <div class="ai-analysis-card evidence-neutral"><span>研究结论</span><strong class="flat">尚无研究结论</strong></div>
        <div class="ai-analysis-card evidence-neutral"><span>模型估计（未校准）</span><strong class="flat">模型估计未校准</strong></div>
        <div class="ai-analysis-card evidence-neutral"><span>研究规划 TP</span><strong class="flat">--</strong></div>
        <div class="ai-analysis-card evidence-neutral"><span>研究规划 SL</span><strong class="flat">--</strong></div>
        <div class="ai-analysis-card evidence-neutral"><span>研究盈亏比</span><strong class="flat">--</strong></div>
        <div class="ai-analysis-card reason evidence-neutral"><span>研究说明</span><strong>等待策略、图表、成本与风险证据</strong></div>
      `;
    }
    renderStrategyCommandStrip();
    renderChartStrategyOverlay();
    renderBookStrategyHint();
    renderStrategyExplainPanel();
    drawChart();
    return;
  }
  state.latestStrategyAnalysis = analysis;
  const selectedDirection = strategyPlanningDirectionText(analysis);
  $("strategyAnalysis").textContent = `${analysis.strategy_name || "Strategy"} / ${selectedDirection} / 模型估计 ${number((analysis.profit_probability || 0) * 100, 0)}% · 未校准 / 规划 TP ${number(planningTakeProfit, 2)} / 规划 SL ${number(planningStopLoss, 2)} / ${analysis.probability_level || "--"}`;
  if (cards) {
    const probability = `${number((analysis.profit_probability || 0) * 100, 0)}%`;
    const deepseek = analysis.deepseek || {};
    const longPlan = analysis.long_plan || {};
    const shortPlan = analysis.short_plan || {};
    const deepseekDirection = strategyPlanningDirectionText(deepseek);
    const longText = `模型估计 ${number((longPlan.profit_probability || 0) * 100, 0)}% · 未校准 / 规划 TP ${number(strategyPlanningValue(longPlan, "take_profit"), 2)} / 规划 SL ${number(strategyPlanningValue(longPlan, "stop_loss"), 2)}`;
    const shortText = `模型估计 ${number((shortPlan.profit_probability || 0) * 100, 0)}% · 未校准 / 规划 TP ${number(strategyPlanningValue(shortPlan, "take_profit"), 2)} / 规划 SL ${number(strategyPlanningValue(shortPlan, "stop_loss"), 2)}`;
    cards.innerHTML = `
      <div class="ai-analysis-card evidence-neutral"><span>研究方向</span><strong class="flat">${selectedDirection} / ${deepseekDirection}</strong></div>
      <div class="ai-analysis-card evidence-neutral"><span>偏多研究方案 · 非订单</span><strong class="flat">${longText}</strong></div>
      <div class="ai-analysis-card evidence-neutral"><span>偏空研究方案 · 非订单</span><strong class="flat">${shortText}</strong></div>
      <div class="ai-analysis-card evidence-neutral"><span>模型估计（未校准）</span><strong class="flat">${deepseek.confidence_pct ? `${number(deepseek.confidence_pct, 0)}% DS / ` : ""}${probability} ${analysis.probability_level || ""}</strong></div>
      <div class="ai-analysis-card evidence-neutral"><span>研究规划 TP</span><strong class="flat">${number(planningTakeProfit, 2)}</strong></div>
      <div class="ai-analysis-card evidence-neutral"><span>研究规划 SL</span><strong class="flat">${number(planningStopLoss, 2)}</strong></div>
      <div class="ai-analysis-card evidence-neutral"><span>研究盈亏比</span><strong class="flat">${number(analysis.risk_reward, 2)}</strong></div>
      <div class="ai-analysis-card evidence-neutral"><span>历史波动估计</span><strong class="flat">${number(analysis.volatility_pct, 2)}%</strong></div>
      <div class="ai-analysis-card reason evidence-neutral"><span>研究说明</span><strong>${escapeHtml(deepseek.summary || analysis.reason || "等待策略、波动、成本与风险证据")}</strong></div>
    `;
  }
  if (planningTakeProfit && !$("takeProfitInput").value) $("takeProfitInput").placeholder = number(planningTakeProfit, 2);
  if (planningStopLoss && !$("stopLossInput").value) $("stopLossInput").placeholder = number(planningStopLoss, 2);
  renderStrategyCommandStrip();
  renderChartStrategyOverlay();
  renderBookStrategyHint();
  renderStrategyExplainPanel();
  drawChart();
}

function riskQueryParams() {
  const riskSource = $("riskSource").value;
  const valueMode = $("riskValueMode").value;
  const takeProfitRaw = $("takeProfitInput").value || "0";
  const stopLossRaw = $("stopLossInput").value || "0";
  const params = new URLSearchParams({
    riskSource,
    riskValueMode: valueMode,
    orderType: $("strategyOrderType").value,
    marginMode: $("marginMode").value,
    directionMode: $("directionMode").value,
    takeProfit: valueMode === "PRICE" ? takeProfitRaw : "0",
    stopLoss: valueMode === "PRICE" ? stopLossRaw : "0",
    takeProfitPct: valueMode === "PCT" ? takeProfitRaw : "0",
    stopLossPct: valueMode === "PCT" ? stopLossRaw : "0",
    trailingTakeEnabled: $("trailingTakeEnabled").checked ? "true" : "false",
    trailingTakePct: $("trailingTakePct").value || "1.5",
    trailingStopEnabled: $("trailingStopEnabled").checked ? "true" : "false",
    trailingStopPct: $("trailingStopPct").value || "1",
    reduceOnly: $("reduceOnly").checked ? "true" : "false",
  });
  return params.toString();
}

function syncRiskPlaceholders() {
  const valueModeEl = $("riskValueMode");
  const takeProfitEl = $("takeProfitInput");
  const stopLossEl = $("stopLossInput");
  if (!valueModeEl || !takeProfitEl || !stopLossEl) return;
  const isPct = valueModeEl.value === "PCT";
  const isShort = $("directionMode")?.value === "SHORT_ONLY";
  takeProfitEl.placeholder = isPct ? (isShort ? "e.g. 3 means down 3%" : "e.g. 3 means +3%") : "AI auto / fixed price";
  stopLossEl.placeholder = isPct ? (isShort ? "e.g. 1.5 means up 1.5%" : "e.g. 1.5 means -1.5%") : "AI auto / fixed price";
}

async function analyzeStrategy() {
  const price = state.lastPrice || (state.candles[state.candles.length - 1]?.close || 0);
  const strategy = $("strategySelect").value || "dual_ma";
  $("strategyAnalysis").textContent = "AI analyzing...";
  const data = await api(`/api/strategy/analyze?symbol=${encodeURIComponent(state.symbol)}&strategy=${encodeURIComponent(strategy)}&price=${encodeURIComponent(price)}&${riskQueryParams()}`);
  renderStrategyAnalysis(data.analysis);
  loadDeepSeekAnalysis().catch(() => {});
  return data.analysis;
}

async function refreshPaper(evaluate = false) {
  const price = state.lastPrice || (state.candles[state.candles.length - 1]?.close || 0);
  const shouldEvaluate = evaluate && Boolean(state.paper?.armed || state.paper?.conditional_orders?.some((order) => ["WAITING", "WAITING_LIMIT", "WAITING_OCO", "MAKER_WAIT"].includes(order.status)));
  const endpoint = shouldEvaluate
    ? `/api/paper/evaluate?symbol=${encodeURIComponent(state.symbol)}&price=${encodeURIComponent(price)}`
    : `/api/paper/snapshot?price=${encodeURIComponent(price)}`;
  try {
    const data = await (shouldEvaluate ? apiMutation(endpoint) : api(endpoint));
    state.paper = data.paper;
    renderPaper();
  } catch (error) {
    if ($("signalSummary")) $("signalSummary").textContent = `模拟盘离线：${error.message}`;
  }
}

async function armStrategy() {
  const readiness = renderBotReadiness();
  if (readiness.blockers.length) {
    const reason = readiness.blockers.map((item) => item.label).join(", ");
    $("strategyAnalysis").textContent = `Start blocked by preflight: ${reason}`;
    $("chartStatus").textContent = `Bot not started: ${reason}`;
    renderStrategyExplainPanel();
    return;
  }
  const strategy = state.strategies.find((item) => item.id === $("strategySelect").value);
  const leverage = $("leverageInput").value;
  const position = $("positionInput").value;
  const price = state.lastPrice || (state.candles[state.candles.length - 1]?.close || 0);
  try {
    const data = await apiMutation(`/api/paper/arm?symbol=${encodeURIComponent(state.symbol)}&strategy=${encodeURIComponent(strategy?.id || "dual_ma")}&leverage=${encodeURIComponent(leverage)}&positionPct=${encodeURIComponent(position)}&price=${encodeURIComponent(price)}&${riskQueryParams()}`);
    state.paper = data.paper;
    renderPaper();
    renderStrategyCommandStrip();
    $("chartStatus").textContent = "模拟策略已启动";
  } catch (error) {
    $("strategyAnalysis").textContent = `模拟启动被阻断：${error.message}`;
    $("chartStatus").textContent = "模拟策略未启动";
  }
}

async function stopStrategy() {
  const data = await apiMutation(`/api/paper/stop?price=${encodeURIComponent(state.lastPrice || 0)}`);
  state.paper = data.paper;
  renderPaper();
  renderStrategyCommandStrip();
}

async function resetPaper() {
  const data = await apiMutation(`/api/paper/reset?price=${encodeURIComponent(state.lastPrice || 0)}`);
  state.paper = data.paper;
  renderPaper();
  renderStrategyCommandStrip();
}

async function loadRiskEngine() {
  try {
    const price = state.lastPrice || (state.candles[state.candles.length - 1]?.close || 0);
    const data = await api(`/api/risk/engine?price=${encodeURIComponent(price)}`);
    const metric = $("riskEngineMetric");
    if (!metric) return;
    metric.dataset.rawAutomatedPaperOrderAllowed = String(Boolean(data.automated_paper_order_allowed));
    metric.dataset.rawPaperOrderAllowed = String(Boolean(data.paper_order_allowed));
    metric.title = `原始模拟条件 automated=${String(Boolean(data.automated_paper_order_allowed))} / manual=${String(Boolean(data.paper_order_allowed))} · 不代表模拟授权`;
    if (!data.live_trading_hard_block) {
      metric.textContent = "实盘安全墙异常";
      metric.className = "down";
    } else if (data.runtime_read_only) {
      metric.textContent = data.risk_policy_allows_paper ? "只读运行 / 风险条件已返回" : "只读运行 / 风险规则阻断";
      metric.className = "flat";
    } else if (!data.risk_policy_allows_paper) {
      metric.textContent = "实盘硬墙 / 风险规则阻断";
      metric.className = "down";
    } else if (data.automated_paper_order_allowed) {
      metric.textContent = "实盘硬墙 / 模拟条件待权限核验";
      metric.className = "flat";
    } else if (data.paper_order_allowed) {
      metric.textContent = "实盘硬墙 / 手动模拟条件待权限核验";
      metric.className = "flat";
    } else {
      metric.textContent = "实盘硬墙 / 模拟执行阻断";
      metric.className = "down";
    }
  } catch (error) {
    if ($("riskEngineMetric")) {
      $("riskEngineMetric").textContent = "离线";
      $("riskEngineMetric").className = "down";
    }
  }
}

async function manualPaperOrder(side) {
  const price = state.lastPrice || (state.candles[state.candles.length - 1]?.close || 0);
  const quantity = $("manualQty").value || $("positionInput").value || "25";
  const orderType = $("manualOrderType").value || $("strategyOrderType").value || "MARKET";
  const limitPrice = $("manualLimitPrice").value || "0";
  const data = await apiMutation(`/api/paper/manual-order?symbol=${encodeURIComponent(state.symbol)}&side=${encodeURIComponent(side)}&quantityPct=${encodeURIComponent(quantity)}&orderType=${encodeURIComponent(orderType)}&limitPrice=${encodeURIComponent(limitPrice)}&price=${encodeURIComponent(price)}&${riskQueryParams()}`);
  state.paper = data.paper;
  renderPaper();
  $("chartStatus").textContent = side === "BUY" ? "Paper buy submitted" : side === "SELL" ? "Paper sell submitted" : "Paper close submitted";
}

function renderPaper() {
  const paper = state.paper;
  if (!paper) return;
  if (!$("railEquity") || !$("strategyState") || !$("riskState")) {
    renderChartStrategyOverlay();
    renderDesktopStatus();
    return;
  }
  $("railEquity").textContent = `${number(paper.equity, 2)} USDT`;
  $("strategyState").textContent = paper.armed ? "本地模拟状态已记录 · 模拟未授权" : "研究观察 · 尚无模拟记录";
  $("strategyState").className = "flat";
  $("riskState").textContent = paper.risk_status ? `研究风险状态 · ${paper.risk_status}` : "研究风险状态待核验";
  $("riskState").className = "flat";
  $("cashMetric").textContent = `${number(paper.cash, 2)} USDT`;
  $("unrealizedMetric").textContent = number(paper.unrealized_pnl, 2);
  $("unrealizedMetric").className = "flat";
  $("realizedMetric").textContent = number(paper.realized_pnl, 2);
  $("realizedMetric").className = "flat";
  $("drawdownMetric").textContent = `${number(paper.drawdown_pct, 2)}%`;
  $("drawdownMetric").className = "flat";
  $("marginMetric").textContent = `${number(paper.margin_used, 2)} USDT`;
  $("liqMetric").textContent = paper.liquidation_price ? number(paper.liquidation_price, 2) : "--";
  $("liqMetric").className = "flat";
  const analysis = paper.ai_analysis || {};
  $("directionMode").value = paper.direction_mode === "SHORT_ONLY" ? "SHORT_ONLY" : "LONG_ONLY";
  if (paper.armed) {
    $("marginMode").value = paper.margin_mode || "CROSS";
    $("directionMode").value = paper.direction_mode === "SHORT_ONLY" ? "SHORT_ONLY" : "LONG_ONLY";
    $("strategyOrderType").value = paper.order_type || "MARKET";
    $("reduceOnly").checked = Boolean(paper.reduce_only);
    $("riskSource").value = paper.risk_source || "AI";
    $("riskValueMode").value = paper.risk_value_mode || "PRICE";
    $("trailingTakeEnabled").checked = Boolean(paper.trailing_take_enabled);
    $("trailingTakePct").value = paper.trailing_take_pct || 1.5;
    $("trailingStopEnabled").checked = Boolean(paper.trailing_stop_enabled);
    $("trailingStopPct").value = paper.trailing_stop_pct || 1;
    syncRiskPlaceholders();
  }
  $("profitProbabilityMetric").textContent = analysis.profit_probability
    ? `${number(analysis.profit_probability * 100, 0)}% · 未校准`
    : "模型估计未校准";
  $("profitProbabilityMetric").className = "flat";
  $("takeProfitMetric").textContent = paper.take_profit_price ? number(paper.take_profit_price, 2) : "--";
  $("takeProfitMetric").className = "flat";
  $("stopLossMetric").textContent = paper.stop_loss_price ? number(paper.stop_loss_price, 2) : "--";
  $("stopLossMetric").className = "flat";
  $("marginModeMetric").textContent = paper.margin_mode === "ISOLATED" ? "逐仓" : "全仓";
  const trailingParts = [];
  if (paper.trailing_take_enabled) trailingParts.push(`盈 ${paper.trailing_take_price ? number(paper.trailing_take_price, 2) : `${number(paper.trailing_take_pct, 2)}%`}`);
  if (paper.trailing_stop_enabled) trailingParts.push(`损 ${paper.trailing_stop_price ? number(paper.trailing_stop_price, 2) : `${number(paper.trailing_stop_pct, 2)}%`}`);
  $("trailingMetric").textContent = trailingParts.length ? trailingParts.join(" / ") : "--";
  renderStrategyAnalysis(analysis);

  const side = paper.position_side === "SHORT" ? "空头" : paper.position_side === "LONG" || paper.position_qty > 0 ? "多头" : "等待";
  const shownQty = Math.abs(Number(paper.position_qty || 0));
  const paperDirectionMode = paper.direction_mode === "SHORT_ONLY"
    ? "Short only"
    : paper.direction_mode === "LONG_ONLY"
      ? "Long only"
      : "未设定";
  $("positionRows").innerHTML = `
    <div class="position-row"><span>${paper.symbol}</span><span>${side} / ${paper.margin_mode === "ISOLATED" ? "Isolated" : "Cross"} / ${paperDirectionMode}</span><span>${number(shownQty, 6)}</span><span class="${cssMove(paper.unrealized_pnl)}">${number(paper.unrealized_pnl, 2)}</span></div>
    <div class="position-row"><span>USDT</span><span>现金</span><span>${number(paper.cash, 2)}</span><span class="flat">--</span></div>
  `;
  renderOrders(paper.orders || []);
  renderSignals(paper.signals || []);
  renderConditions(paper.conditional_orders || []);
  renderStrategyDetail();
  renderOrderHistory(paper.orders || []);
  drawEquityChart(paper.equity_curve || []);
  renderChartStrategyOverlay();
  renderBookStrategyHint();
  renderBotReadiness();
  renderDesktopStatus();
}

function renderOrders(orders) {
  const filtered = state.orderFilter === "ALL" ? orders : orders.filter((order) => order.side === state.orderFilter);
  $("orderSummary").textContent = `${filtered.length} orders`;
  $("orderRows").innerHTML = filtered.slice().reverse().map((order) => `
    <div class="order-row">
      <span>${timeText(order.time)}</span>
      <span class="${order.side === "BUY" || order.side === "ADD" ? "up" : "down"}">${order.side}</span>
      <span>${number(order.price, 2)}</span>
      <span>${number(order.quantity, 6)}</span>
      <span>${order.order_type || "MARKET"}${order.reduce_only ? " / reduce-only" : ""}${order.slippage_pct !== undefined ? ` / slippage ${number(order.slippage_pct, 4)}%` : ""}${order.fee !== undefined ? ` / fee ${number(order.fee, 4)}` : ""}${order.funding_estimate ? ` / funding est. ${number(order.funding_estimate, 4)} (not charged)` : ""}${order.funding_charged ? ` / funding charged ${number(order.funding_charged, 4)}` : ""} / ${order.reason || "--"}</span>
    </div>
  `).join("");
}

function renderOrderHistory(orders) {
  $("historyOrderSummary").textContent = `${orders.length} rows`;
  $("historyOrderRows").innerHTML = orders.slice().reverse().map((order) => `
    <div class="history-order-row">
      <span>${timeText(order.time)}</span>
      <span class="${order.side === "BUY" || order.side === "ADD" ? "up" : "down"}">${order.side}</span>
      <span>${number(order.price, 2)}</span>
      <span>${number(order.quantity, 6)}</span>
      <span>${order.order_type || "MARKET"}${order.reduce_only ? " / reduce-only" : ""}${order.slippage_pct !== undefined ? ` / slippage ${number(order.slippage_pct, 4)}%` : ""}${order.fee !== undefined ? ` / fee ${number(order.fee, 4)}` : ""} / ${order.reason || "--"}</span>
    </div>
  `).join("");
}

function strategyActionTone(action = "") {
  if (["BUY", "ADD", "LONG"].includes(action)) return "up";
  if (["SELL", "EXIT", "SHORT", "COVER"].includes(action)) return "down";
  if (["HALT", "BLOCK", "WAIT"].includes(action)) return "down";
  return "flat";
}

function strategyActionLabel(action = "") {
  return {
    BUY: "Buy",
    ADD: "Add",
    SELL: "Sell",
    EXIT: "Exit",
    SHORT: "Short",
    COVER: "Cover",
    HALT: "Halt",
    BLOCK: "Block",
    WAIT: "Wait",
    WATCH: "Watch",
  }[action] || action || "Watch";
}

function currentStrategyExplanation() {
  const paper = state.paper || {};
  const signals = paper.signals || [];
  const latestSignal = signals[signals.length - 1] || null;
  const analysis = state.latestStrategyAnalysis || paper.ai_analysis || {};
  const war = state.strategyWarRoom || {};
  const top = (war.top_strategies || [])[0] || {};
  const noTrade = Array.isArray(war.no_trade)
    ? war.no_trade.slice(0, 3).map(evidenceStrategySourceText).filter(Boolean)
    : [];
  const latestSignalReason = evidenceStrategySourceText(latestSignal?.reason);
  const topReason = evidenceStrategySourceText(top.reason);
  const topName = evidenceStrategySourceText(top.name || top.id);
  const analysisReason = evidenceStrategySourceText(analysis.reason);
  const action = latestSignal?.action || top.action || (paper.armed ? "WATCH" : "WAIT");
  const analysisFields = ["direction", "profit_probability", "probability_level", "planning_take_profit", "planning_stop_loss", "reason"];
  const hasAnalysis = analysisFields.some((key) => analysis[key] !== undefined && analysis[key] !== null && analysis[key] !== "");
  const analysisDirection = strategyRawDirection(analysis);
  const positionDirection = String(paper.position_side || "").toUpperCase();
  const direction = ["LONG", "SHORT"].includes(analysisDirection)
    ? analysisDirection
    : ["LONG", "SHORT"].includes(positionDirection)
      ? positionDirection
      : "";
  const probability = Number(analysis.profit_probability);
  const probabilityKnown = analysis.profit_probability !== undefined
    && analysis.profit_probability !== null
    && analysis.profit_probability !== ""
    && Number.isFinite(probability);
  const presentation = evidenceStrategyPresentation({
    hasSignal: Boolean(latestSignal),
    hasAnalysis,
    hasWarEvidence: Boolean(topReason || noTrade.length),
    action,
    direction,
    probability,
    probabilityKnown,
    noTrade,
  });
  const evidence = [];
  if (probabilityKnown) evidence.push(presentation.estimateText);
  const planningTakeProfit = strategyPlanningValue(analysis, "take_profit");
  const planningStopLoss = strategyPlanningValue(analysis, "stop_loss");
  if (planningTakeProfit || paper.take_profit_price) evidence.push(`研究止盈参考 ${number(paper.take_profit_price || planningTakeProfit, 2)} · 非订单`);
  if (planningStopLoss || paper.stop_loss_price) evidence.push(`研究止损参考 ${number(paper.stop_loss_price || planningStopLoss, 2)} · 非订单`);
  if (topReason) evidence.push(`候选策略：${topName || "--"} / ${topReason}`);
  if (latestSignalReason) evidence.push(`最近研究信号：${latestSignalReason}`);
  const why = latestSignalReason || topReason || analysisReason || noTrade[0] || "等待策略、图表、成本与风险证据。";
  const conflict = "盘口与成交分布仅作描述性观察，不与策略方向合并，也不产生订单。";
  return {
    action,
    tone: "neutral",
    label: presentation.conclusionText,
    direction,
    directionText: presentation.directionText,
    probability,
    estimateText: presentation.estimateText,
    hasEvidence: presentation.hasEvidence,
    why,
    conflict,
    evidence: evidence.slice(0, 5),
    noTrade,
    noTradeText: presentation.noTradeText,
    permissionText: presentation.permissionText,
    latestSignal,
  };
}

function renderStrategyExplainPanel() {
  const target = $("strategyExplainPanel");
  if (!target) return;
  const explanation = currentStrategyExplanation();
  target.className = "strategy-explain-panel evidence-neutral";
  target.dataset.evidenceStatus = explanation.hasEvidence ? "PRESENT" : "UNKNOWN";
  target.title = explanation.permissionText;
  target.innerHTML = `
    <div class="explain-no-trade" data-evidence-role="failure" role="status" aria-live="polite" aria-atomic="true">
      <span>失效与禁做条件</span>
      <strong>${escapeHtml(explanation.noTradeText)}</strong>
    </div>
    <div class="explain-permission">
      <span>权限边界</span>
      <strong>${escapeHtml(explanation.permissionText)}</strong>
    </div>
    <div class="explain-main">
      <span>研究状态</span>
      <strong>${escapeHtml(explanation.label)}</strong>
      <em>${escapeHtml(explanation.directionText)} · ${escapeHtml(explanation.estimateText)}</em>
    </div>
    <div class="explain-why">
      <span>证据解释</span>
      <strong>${escapeHtml(explanation.why)}</strong>
      <em>${escapeHtml(explanation.conflict)}</em>
    </div>
    <div class="explain-evidence">
      ${(explanation.evidence.length ? explanation.evidence : ["等待策略、图表、成本与风险证据。"]).map((item) => `<small>${escapeHtml(item)}</small>`).join("")}
    </div>
  `;
}

function signalEvidenceText(signal = {}) {
  const analysis = state.latestStrategyAnalysis || state.paper?.ai_analysis || {};
  const parts = [];
  if (signal.price) parts.push(`Price ${number(signal.price, Number(signal.price) > 100 ? 2 : 5)}`);
  if (signal.confidence) parts.push(`Confidence ${number(signal.confidence * 100, 0)}%`);
  if (analysis.profit_probability) parts.push(`模型估计 ${number(analysis.profit_probability * 100, 0)}% · 未校准`);
  return parts.join(" / ") || "Waiting for evidence";
}

function renderSignals(signals) {
  renderStrategyExplainPanel();
  $("signalSummary").textContent = signals.length ? `${signals.length} signals / explainable` : "Waiting for strategy";
  if (!signals.length) {
    const explanation = currentStrategyExplanation();
    $("signalRows").innerHTML = `
      <div class="signal-item signal-empty">
        <div class="signal-main">
          <span>--</span>
          <span class="flat">研究观察</span>
          <span>${escapeHtml(explanation.why)}</span>
          <span>--</span>
        </div>
        <div class="signal-evidence">${escapeHtml(explanation.noTradeText)}</div>
      </div>
    `;
    return;
  }
  $("signalRows").innerHTML = signals.slice().reverse().map((signal) => {
    const action = evidenceStrategyActionPresentation(signal.action);
    return `
      <div class="signal-item evidence-neutral" data-raw-action="${escapeHtml(String(signal.action || "WAIT"))}" title="${escapeHtml(action.permissionText)}">
        <div class="signal-main">
          <span>${timeText(signal.time)}</span>
          <span class="flat">${escapeHtml(action.conclusionText)}</span>
          <span>${escapeHtml(signal.reason || "--")}</span>
          <span>模型估计 ${number((signal.confidence || 0) * 100, 0)}% · 未校准</span>
        </div>
        <div class="signal-evidence">
          ${escapeHtml(signalEvidenceText(signal))}
        </div>
      </div>
    `;
  }).join("");
}

function drawEquityChart(points) {
  const canvas = $("equityChart");
  const dpr = window.devicePixelRatio || 1;
  const width = Math.max(260, canvas.clientWidth);
  const height = Math.max(90, canvas.clientHeight);
  canvas.width = Math.floor(width * dpr);
  canvas.height = Math.floor(height * dpr);
  const ctx = canvas.getContext("2d");
  const colors = chartThemeColors();
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = colors.surface;
  ctx.fillRect(0, 0, width, height);
  if (!points.length) return;
  const values = points.map((point) => Number(point.equity));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = Math.max(1, max - min);
  ctx.strokeStyle = "#43d7ff";
  ctx.lineWidth = 2;
  ctx.beginPath();
  values.forEach((value, index) => {
    const x = values.length <= 1 ? 0 : (index / (values.length - 1)) * width;
    const y = height - ((value - min) / range) * (height - 14) - 7;
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

function renderConditions(orders) {
  $("conditionRows").innerHTML = orders.slice().reverse().map((order) => `
    <div class="condition-row">
      <span class="${order.status === "TRIGGERED" ? "up" : order.status === "CANCELLED" || order.status === "REJECTED" ? "flat" : "down"}">${order.status}</span>
      <span class="${order.side === "BUY" ? "up" : "down"}">${order.side}</span>
      <span>${order.order_type || "MARKET"}</span>
      <span>${number(order.trigger_price, 2)}</span>
      <span>${order.order_type === "OCO" ? `${number(order.take_profit_price, 2)} / ${number(order.stop_loss_price, 2)}` : (order.limit_price ? `${number(order.limit_price, 2)} / ${order.time_in_force || "GTC"}` : "--")}</span>
      <span>${number(order.quantity_pct, 0)}%</span>
      <span>${order.reduce_only ? "Reduce only / " : ""}${order.batch_plan ? `Entry ${order.batch_plan} / ` : ""}${order.take_profit_plan ? `TP ${order.take_profit_plan} / ` : ""}${order.reject_reason || order.note || "--"}</span>
      <button data-cancel-condition="${order.id}" ${!["WAITING", "WAITING_LIMIT", "WAITING_OCO"].includes(order.status) ? "disabled" : ""}>Cancel</button>
    </div>
  `).join("");
  document.querySelectorAll("[data-cancel-condition]").forEach((button) => {
    button.addEventListener("click", () => cancelCondition(button.dataset.cancelCondition));
  });
}

function syncConditionForm() {
  const orderTypeEl = $("conditionOrderType");
  if (!orderTypeEl) return;
  const orderType = orderTypeEl.value;
  if (orderType === "CURRENT") {
    if ($("conditionLimitPrice")) $("conditionLimitPrice").value = state.lastPrice ? Number(state.lastPrice).toFixed(2) : "";
  }
  if (orderType === "IOC" || orderType === "FOK" || orderType === "POST_ONLY") {
    if ($("conditionTimeInForce")) $("conditionTimeInForce").value = orderType === "POST_ONLY" ? "POST_ONLY" : orderType;
  }
  if (orderType === "OCO") {
    if ($("conditionSide")) $("conditionSide").value = "SELL";
    if ($("conditionReduceOnly")) $("conditionReduceOnly").checked = true;
    if ($("conditionPrice")) $("conditionPrice").placeholder = "Optional, monitor directly";
    if ($("conditionTpPrice")) $("conditionTpPrice").placeholder = state.lastPrice ? `TP > ${number(state.lastPrice, 2)}` : "Take-profit price";
    if ($("conditionSlPrice")) $("conditionSlPrice").placeholder = state.lastPrice ? `SL < ${number(state.lastPrice, 2)}` : "Stop-loss price";
  } else {
    if ($("conditionPrice")) $("conditionPrice").placeholder = "Trigger price";
    if ($("conditionTpPrice")) $("conditionTpPrice").placeholder = "Take-profit price";
    if ($("conditionSlPrice")) $("conditionSlPrice").placeholder = "Stop-loss price";
  }
}

async function addCondition() {
  const side = $("conditionSide").value;
  const price = $("conditionPrice").value || state.lastPrice || 0;
  const orderType = $("conditionOrderType").value;
  const limitPrice = $("conditionLimitPrice").value || (orderType === "CURRENT" ? state.lastPrice || 0 : 0);
  const takeProfitPrice = $("conditionTpPrice").value || 0;
  const stopLossPrice = $("conditionSlPrice").value || 0;
  const timeInForce = $("conditionTimeInForce").value || "GTC";
  const qty = $("conditionQty").value || 25;
  const note = $("conditionNote").value || "Strategy condition order";
  const data = await apiMutation(`/api/paper/condition/add?symbol=${encodeURIComponent(state.symbol)}&side=${encodeURIComponent(side)}&triggerPrice=${encodeURIComponent(price)}&orderType=${encodeURIComponent(orderType)}&limitPrice=${encodeURIComponent(limitPrice)}&takeProfitPrice=${encodeURIComponent(takeProfitPrice)}&stopLossPrice=${encodeURIComponent(stopLossPrice)}&timeInForce=${encodeURIComponent(timeInForce)}&quantityPct=${encodeURIComponent(qty)}&batchPlan=${encodeURIComponent($("conditionBatchPlan").value || "")}&takeProfitPlan=${encodeURIComponent($("conditionTpPlan").value || "")}&reduceOnly=${$("conditionReduceOnly").checked ? "true" : "false"}&note=${encodeURIComponent(note)}&price=${encodeURIComponent(state.lastPrice || 0)}`);
  state.paper = data.paper;
  renderPaper();
  $("conditionNote").value = "";
  syncConditionForm();
}

async function estimateOrder() {
  if (!$("conditionSide") || !$("conditionOrderType") || !$("conditionLimitPrice") || !$("conditionQty")) return;
  try {
    const side = $("conditionSide").value || "BUY";
    const orderType = $("conditionOrderType").value || "MARKET";
    const limitPrice = $("conditionLimitPrice").value || 0;
    const equity = state.paper?.equity || 10000;
    const notional = equity * Number($("conditionQty").value || 25) / 100;
    const price = state.lastPrice || (state.candles[state.candles.length - 1]?.close || 0);
    const data = await api(`/api/order/estimate?symbol=${encodeURIComponent(state.symbol)}&side=${encodeURIComponent(side)}&orderType=${encodeURIComponent(orderType)}&limitPrice=${encodeURIComponent(limitPrice)}&price=${encodeURIComponent(price)}&notional=${encodeURIComponent(notional)}`);
    const e = data.estimate || {};
    $("orderEstimate").textContent = `Match ${e.status || "--"} / Avg ${number(e.avg_price, 2)} / Slippage ${number(e.slippage_pct, 4)}% / Fee ${number(e.fee, 4)} / Funding estimate ${number(e.funding_estimate, 4)} (not charged) / ${e.note || ""}`;
  } catch (error) {
    $("orderEstimate").textContent = `Order estimate offline: ${error.message}`;
  }
}

async function cancelCondition(id) {
  const data = await apiMutation(`/api/paper/condition/cancel?id=${encodeURIComponent(id)}&price=${encodeURIComponent(state.lastPrice || 0)}`);
  state.paper = data.paper;
  renderPaper();
}

async function loadFundingHistory(swap) {
  try {
    const data = await api(`/api/okx/funding-rate-history?instId=${encodeURIComponent(swap)}&limit=8`);
    const rows = data.payload.data || [];
    $("fundingHistory").innerHTML = rows.map((row) => `
      <div class="funding-row">
        <span>${new Date(Number(row.fundingTime)).toLocaleString("zh-CN", { hour12: false })}</span>
        <strong class="${cssMove(row.realizedRate || row.fundingRate)}">${number(Number(row.realizedRate || row.fundingRate || 0) * 100, 4)}%</strong>
      </div>
    `).join("");
  } catch (error) {
    $("fundingHistory").innerHTML = `<div class="funding-row"><span>资金费率历史离线</span><strong>--</strong></div>`;
  }
}

function renderMarketInsights(data) {
  if (!data) return;
  state.marketInsights = data;
  $("marketIntelState").textContent = `鏇存柊 ${timeText(Date.now())}`;
  $("intelBias").textContent = data.bias || "--";
  $("intelBias").className = data.bias === "鍋忓" ? "up" : data.bias === "鍋忕┖" ? "down" : "flat";
  $("intelSummary").textContent = data.summary || "--";
  const metrics = data.metrics || {};
  $("intelScore").textContent = number(data.score, 1);
  $("intelScore").className = data.score >= 60 ? "up" : data.score <= 40 ? "down" : "flat";
  $("intelTrend").textContent = `${metrics.trend12h_pct >= 0 ? "+" : ""}${number(metrics.trend12h_pct, 2)}%`;
  $("intelTrend").className = cssMove(metrics.trend12h_pct);
  $("intelRange").textContent = `${number(metrics.range24h_pct, 2)}%`;
  $("intelFunding").textContent = `${metrics.funding_rate_pct >= 0 ? "+" : ""}${number(metrics.funding_rate_pct, 4)}%`;
  $("intelFunding").className = Math.abs(Number(metrics.funding_rate_pct || 0)) >= 0.03 ? "down" : "flat";
  $("marketIntelRows").innerHTML = (data.alerts || []).map((item) => `
    <div class="market-intel-row">
      <span class="${item.level === "WARN" ? "down" : item.level === "INFO" ? "up" : "flat"}">${item.level}</span>
      <span>${item.tag || "--"}</span>
      <span><strong>${item.title || "--"}</strong>${item.body || ""}</span>
    </div>
  `).join("");
}

async function loadMarketInsights(writeNotification = false) {
  try {
    $("marketIntelState").textContent = writeNotification ? "Writing..." : "Refreshing...";
    const data = await api(`/api/market/insights?symbol=${encodeURIComponent(state.symbol)}&notify=${writeNotification ? "true" : "false"}`);
    renderMarketInsights(data);
    if (writeNotification) await loadProfile();
  } catch (error) {
    $("marketIntelState").textContent = "Offline";
    $("intelSummary").textContent = error.message;
  }
}

function renderDeepSeekStatus(status = {}) {
  $("deepseekModel").textContent = status.model || "--";
  $("deepseekThinking").textContent = status.thinking === "enabled" ? "研究模式" : "未开启";
  $("deepseekThinking").className = "flat";
  $("deepseekState").textContent = status.configured ? "研究接口已配置" : "研究接口未配置";
  $("deepseekState").className = "flat";
}

function renderDeepSeekRows(rows = []) {
  $("deepseekRows").innerHTML = rows.length ? rows.map((row) => `
    <div class="deepseek-row">
      <strong>${row.symbol || row.area || state.symbol}</strong>
      <span class="flat">${escapeHtml(marketResearchDirectionLabel(row.direction || "RESEARCH_NEUTRAL"))}</span>
      <span>${row.confidence_pct != null ? "未校准" : row.risk || row.effort || "--"}</span>
      <span>${row.strategy || row.actionability || row.upgrade || "--"} / ${row.reason || row.planning_entry_hint || row.summary || "--"}</span>
    </div>
  `).join("") : `<div class="deepseek-row"><strong>${state.symbol}</strong><span class="flat">RESEARCH_REVIEW</span><span>--</span><span>等待 DeepSeek 研究回执</span></div>`;
}

function renderDeepSeekAnalysis(data) {
  state.deepseek = data;
  const status = data.status || data.deepseek?.status || {};
  renderDeepSeekStatus(status);
  const result = data.analysis?.deepseek || data.analysis || {};
  if (!data.ok && data.deepseek?.error) {
    $("deepseekHeadline").textContent = "DeepSeek offline";
    $("deepseekSummary").textContent = data.deepseek.error;
    $("deepseekDirection").textContent = "--";
    $("deepseekConfidence").textContent = "--";
    renderDeepSeekRows([]);
    return;
  }
  $("deepseekHeadline").textContent = result.summary || data.analysis?.summary || "DeepSeek Pro analysis complete";
  $("deepseekSummary").textContent = (result.risk_notes || result.warnings || []).slice(0, 2).join(" / ") || data.deepseek?.content || "No extra risk warning";
  $("deepseekDirection").textContent = marketResearchDirectionLabel(result.direction || "RESEARCH_NEUTRAL");
  $("deepseekDirection").className = "flat";
  $("deepseekConfidence").textContent = result.confidence_pct != null ? "未校准" : "--";
  $("deepseekConfidence").className = "flat";
  $("deepseekArchitecture").textContent = result.architecture_score != null ? "未校准" : "--";
  $("deepseekArchitecture").className = "flat";
  const rows = result.top_priorities || result.opportunities || [{
    symbol: state.symbol,
    direction: result.direction || "RESEARCH_NEUTRAL",
    confidence_pct: null,
    strategy: result.actionability || "Research suggestion",
    planning_entry_hint: result.planning_entry_hint,
    reason: (result.reasons || []).join(" / ") || result.summary || "--",
  }];
  renderDeepSeekRows(rows);
}

async function loadDeepSeekStatus() {
  try {
    const data = await api("/api/ai/deepseek/status");
    renderDeepSeekStatus(data.status || {});
  } catch (error) {
    $("deepseekState").textContent = "Offline";
    $("deepseekState").className = "down";
  }
}

async function loadDeepSeekAnalysis() {
  const price = state.lastPrice || (state.candles[state.candles.length - 1]?.close || 0);
  const strategy = $("strategySelect").value || "dual_ma";
  $("deepseekState").textContent = "V4 Pro thinking";
  const data = await api(`/api/ai/deepseek/analyze?symbol=${encodeURIComponent(state.symbol)}&strategy=${encodeURIComponent(strategy)}&price=${encodeURIComponent(price)}&${riskQueryParams()}`);
  renderDeepSeekAnalysis(data);
  if (data.analysis) {
    renderStrategyAnalysis(data.analysis);
  }
  return data;
}

async function loadDeepSeekOpportunities(silent = false) {
  try {
    if (!silent) $("deepseekState").textContent = "Scanning opportunities";
    const data = await api("/api/ai/deepseek/opportunities");
    renderDeepSeekAnalysis(data);
  } catch (error) {
    if (!silent) {
      $("deepseekHeadline").textContent = "Opportunity scan offline";
      $("deepseekSummary").textContent = error.message;
    }
  }
}

async function loadDeepSeekPlatformReview() {
  $("deepseekState").textContent = "Reviewing platform";
  const data = await api("/api/ai/deepseek/platform-review");
  renderDeepSeekAnalysis(data);
  if (data.analysis?.next_build_batch?.length) {
    $("deepseekSummary").textContent = `${$("deepseekSummary").textContent} / Next batch: ${data.analysis.next_build_batch.slice(0, 3).join(" / ")}`;
  }
  return data;
}

function renderCodeWorkerDrafts(data = {}) {
  state.codeWorker = data;
  const target = $("codeWorkerRows");
  if (!target) return;
  const drafts = data.drafts || [];
  const active = drafts.filter((row) => row.status !== "ARCHIVED").slice().reverse();
  const configured = data.status?.configured;
  $("codeWorkerState").textContent = configured === false ? "API key missing" : `${active.length} drafts`;
  $("codeWorkerState").className = configured === false ? "down" : "flat";
  target.innerHTML = active.length ? active.map((row) => {
    const risk = row.risk?.level || "LOW";
    const riskClass = risk === "HIGH" ? "down" : risk === "MEDIUM" ? "flat" : "up";
    const files = (row.files || []).slice(0, 3).map((file) => file.path || file).join(" / ") || "No files specified";
    const notes = (row.notes || []).slice(0, 2).join(" / ");
    const patch = row.patch || row.raw || "";
    return `
      <article class="code-worker-row">
        <header>
          <strong title="${escapeHtml(row.task || "")}">${escapeHtml(row.summary || row.task || "DeepSeek draft")}</strong>
          <span class="${riskClass}">${escapeHtml(risk)}</span>
          <button data-code-worker-archive="${escapeHtml(row.id)}">Archive</button>
        </header>
        <p>${escapeHtml(row.mode_label || row.mode || "draft")} / ${escapeHtml(files)}</p>
        <p>${escapeHtml(notes || "Waiting for Codex review before applying.")}</p>
        ${patch ? `<pre>${escapeHtml(patch.slice(0, 1800))}</pre>` : ""}
      </article>
    `;
  }).join("") : `
    <article class="code-worker-row">
      <header><strong>No drafts</strong><span class="flat">READY</span><span></span></header>
      <p>Enter a routine development task. DeepSeek will draft, and Codex will review before applying.</p>
    </article>
  `;
  document.querySelectorAll("[data-code-worker-archive]").forEach((button) => {
    button.addEventListener("click", () => archiveCodeWorkerDraft(button.dataset.codeWorkerArchive));
  });
}

async function loadCodeWorkerDrafts() {
  try {
    const data = await api("/api/ai/deepseek/code-worker/drafts");
    renderCodeWorkerDrafts(data);
    return data;
  } catch (error) {
    if ($("codeWorkerState")) {
      $("codeWorkerState").textContent = "Offline";
      $("codeWorkerState").className = "down";
    }
    if ($("codeWorkerRows")) {
      $("codeWorkerRows").innerHTML = `<article class="code-worker-row"><p>${escapeHtml(error.message)}</p></article>`;
    }
    return null;
  }
}

async function runCodeWorker() {
  const task = $("codeWorkerTask").value.trim();
  const mode = $("codeWorkerMode").value || "draft";
  if (task.length < 4) {
    $("codeWorkerState").textContent = "Task too short";
    $("codeWorkerState").className = "down";
    return null;
  }
  const button = $("runCodeWorker");
  button.disabled = true;
  $("codeWorkerState").textContent = "DeepSeek processing";
  try {
    const data = await apiMutation(`/api/ai/deepseek/code-worker/run?mode=${encodeURIComponent(mode)}&task=${encodeURIComponent(task)}`);
    renderCodeWorkerDrafts(data);
    $("codeWorkerTask").value = "";
    return data;
  } catch (error) {
    $("codeWorkerState").textContent = "Generation failed";
    $("codeWorkerState").className = "down";
    $("codeWorkerRows").innerHTML = `<article class="code-worker-row"><p>${escapeHtml(error.message)}</p></article>`;
    return null;
  } finally {
    button.disabled = false;
  }
}

async function archiveCodeWorkerDraft(id) {
  if (!id) return;
  try {
    const data = await apiMutation(`/api/ai/deepseek/code-worker/archive?id=${encodeURIComponent(id)}`);
    renderCodeWorkerDrafts(data);
  } catch (error) {
    $("codeWorkerState").textContent = "Archive failed";
    $("codeWorkerState").className = "down";
  }
}

function configStatusClass(status = "") {
  const value = String(status).toUpperCase();
  // Configuration evidence is descriptive only: positive source states must
  // not become a green/ready-looking permission signal in the research UI.
  if (["READY", "ONLINE", "CONFIGURED", "PROTECTED", "RUNNING", "PASS", "LOCKED"].includes(value)) return "flat";
  if (["OFFLINE", "MISSING", "ERROR", "UNSAFE", "BLOCK", "BLOCKED"].includes(value)) return "down";
  return "flat";
}

function renderFullConfig(data = {}) {
  state.fullConfig = data;
  const items = data.items || [];
  const byId = Object.fromEntries(items.map((item) => [item.id, item]));
  const deepseekReady = Boolean(byId.deepseek?.configured);
  const gptReady = Boolean(byId.gpt_review?.configured);
  const dataReady = ["READY", "研究配置已核对"].includes(byId.history_cache?.raw_status || byId.history_cache?.status)
    && ["READY", "研究配置已核对"].includes(byId.okx_public?.raw_status || byId.okx_public?.status);
  $("configCenterState").textContent = data.applied ? "配置已写入" : (data.status || "研究配置观察");
  $("configCenterState").className = "flat";
  $("configScore").textContent = data.score ? `${number(data.score, 1)}/100` : "--";
  $("configScore").className = "flat";
  $("configLiveWall").textContent = byId.live_wall?.locked ? "实盘永久硬锁" : "保护待复核";
  $("configLiveWall").className = "flat";
  $("configAiPair").textContent = deepseekReady && gptReady ? "双AI研究配置已核对" : "研究配置待补";
  $("configAiPair").className = "flat";
  $("configDataMode").textContent = dataReady ? "行情来源已核对" : "行情来源待复核";
  $("configDataMode").className = "flat";
  $("configSummary").textContent = data.summary || "全局配置等待刷新；仅供研究配置观察。";
  $("configCenterCards").innerHTML = items.slice(0, 12).map((item) => `
    <article class="config-card flat" data-raw-status="${escapeHtml(item.raw_status || item.status || "UNKNOWN")}" title="原始状态仅供审计：${escapeHtml(item.raw_status || item.status || "UNKNOWN")}；此页不授予模拟或实盘权限。">
      <span>${escapeHtml(item.priority || "P1")} / ${escapeHtml(item.status || "研究观察")}</span>
      <strong>${escapeHtml(item.name || item.id || "--")}</strong>
      <em>${escapeHtml(item.detail || item.action || "--")}</em>
    </article>
  `).join("") || `<article class="config-card flat"><span>EMPTY</span><strong>等待配置</strong><em>刷新后显示研究配置观察。</em></article>`;
  $("configChecklistRows").innerHTML = (data.checklist || []).map((row) => `
    <div class="config-check-row">
      <strong>${escapeHtml(row.label || "--")}</strong>
      <span class="flat" data-raw-status="${escapeHtml(row.raw_status || row.status || "UNKNOWN")}">${escapeHtml(row.status || "研究观察")}</span>
      <span>${escapeHtml(row.detail || "研究配置状态待补充")}</span>
    </div>
  `).join("") || `<div class="config-check-row"><strong>等待</strong><span class="flat">研究观察</span><span>刷新后生成检查项</span></div>`;
}

async function loadFullConfig() {
  try {
    const price = state.lastPrice || (state.candles[state.candles.length - 1]?.close || 0);
    $("configCenterState").textContent = "检查中";
    const data = await api(`/api/config/full?price=${encodeURIComponent(price)}`);
    renderFullConfig(data);
    return data;
  } catch (error) {
    $("configCenterState").textContent = "配置状态未核验";
    $("configCenterState").className = "flat";
    $("configSummary").textContent = `配置状态未核验；${error.message || "请稍后重试"}`;
    return null;
  }
}

async function applyFullConfigPreset() {
  const button = $("applyFullConfigPreset");
  button.disabled = true;
  try {
    const price = state.lastPrice || (state.candles[state.candles.length - 1]?.close || 0);
    $("configCenterState").textContent = "应用中";
    const data = await apiMutation(`/api/config/full/apply?price=${encodeURIComponent(price)}`);
    renderFullConfig(data);
    if (data.providers?.api) {
      const saved = data.providers.api.saved || {};
      $("apiKeyEnv").value = saved.api_key_env || "OKX_API_KEY";
      $("secretEnv").value = saved.secret_env || "OKX_SECRET";
      $("passwordEnv").value = saved.password_env || "OKX_PASSWORD";
    }
    if (data.safe_defaults) {
      $("themeSelect").value = data.safe_defaults.theme || "dark";
      $("densitySelect").value = data.safe_defaults.density || "compact";
      $("refreshSeconds").value = data.safe_defaults.refresh_seconds || 8;
      $("startModule").value = data.safe_defaults.start_module || ".ticker-header";
      $("layoutPreset").value = data.safe_defaults.layout || "analysis";
    }
    await loadProfile();
    await loadApiConfig();
    await loadStrategyMarketplace();
  } catch (error) {
    $("configCenterState").textContent = "应用失败";
    $("configCenterState").className = "down";
    $("configSummary").textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

function renderSixLaneRoadmap(data) {
  const target = $("sixLaneRows");
  if (!target) return;
  state.sixLane = data || null;
  const rows = data?.lanes || [];
  $("sixLaneSummary").textContent = data?.summary || "等待六路线状态";
  $("sixLaneSummary").className = data?.status === "PASS" ? "up" : data?.status === "BLOCK" ? "down" : "flat";
  target.innerHTML = rows.length ? rows.map((row) => `
    <div class="six-lane-row">
      <span class="${renderStatusClass(row.status)}">${escapeHtml(row.status || "--")}</span>
      <div>
        <strong>${escapeHtml(row.name || row.id || "--")}</strong>
        <em>${escapeHtml(row.objective || "")}</em>
      </div>
      <span class="${Number(row.score || 0) >= 76 ? "up" : Number(row.score || 0) < 55 ? "down" : "flat"}">${number(row.score, 1)}</span>
      <div class="six-lane-evidence">
        ${(row.landed || []).slice(0, 3).map((item) => `<b>${escapeHtml(item)}</b>`).join("")}
      </div>
      <div class="six-lane-next">
        ${(row.next || []).slice(0, 2).map((item) => `<i>${escapeHtml(item)}</i>`).join("")}
      </div>
    </div>
  `).join("") : `
    <div class="six-lane-row empty">
      <span>WAIT</span>
      <div><strong>Six-lane roadmap</strong><em>等待平台状态</em></div>
      <span>--</span>
      <div class="six-lane-evidence"></div>
      <div class="six-lane-next"></div>
    </div>
  `;
}

function renderV2Platform(data = {}) {
  state.v2Platform = data;
  $("v2PlatformState").textContent = data.stage || "V2";
  $("v2Version").textContent = data.version || "--";
  $("v2Score").textContent = data.score ? `${number(data.score, 1)}/100` : "--";
  $("v2Score").className = Number(data.score || 0) >= 75 ? "up" : Number(data.score || 0) < 55 ? "down" : "flat";
  $("v2LiveWall").textContent = data.live_trading?.hard_block ? "Live trading blocked" : "Needs check";
  $("v2LiveWall").className = data.live_trading?.hard_block ? "up" : "down";
  $("v2HighRisk").textContent = String(data.metrics?.high_risk_count ?? "--");
  $("v2HighRisk").className = Number(data.metrics?.high_risk_count || 0) > 0 ? "down" : "up";
  $("v2Summary").textContent = data.summary || "--";
  const redesign = data.competitive_redesign || {};
  const redesignRows = $("v2CompetitiveRows");
  if (redesignRows) {
    const principles = (redesign.principles || []).slice(0, 4);
    const actions = (redesign.next_actions || []).slice(0, 3);
    redesignRows.innerHTML = `
      <div class="v2-competitive-summary">
        <span>${escapeHtml(redesign.status || "PLANNED")}</span>
        <strong>${escapeHtml(redesign.summary || "等待竞品重设计路线")}</strong>
        <em>${escapeHtml(redesign.safety_boundary || "")}</em>
      </div>
      <div class="v2-competitive-source">
        <span>参考项目</span>
        <strong>${escapeHtml((redesign.source_projects || []).join(" / ") || "--")}</strong>
        <em>${escapeHtml(redesign.document || "")}</em>
      </div>
      <div class="v2-competitive-list">
        ${principles.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}
      </div>
      <div class="v2-competitive-list next">
        ${actions.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}
      </div>
    `;
  }

  $("v2Lanes").innerHTML = (data.release_lanes || []).slice(0, 4).map((lane) => `
    <div class="v2-lane">
      <strong>${escapeHtml(lane.lane || "--")}</strong>
      <span>${escapeHtml(lane.status || "--")} / ${escapeHtml((lane.items || []).slice(0, 3).join(" / "))}</span>
    </div>
  `).join("");
  renderSixLaneRoadmap(data.six_lane || null);

  $("v2ModuleRows").innerHTML = (data.modules || []).map((item) => {
    const maturity = Number(item.maturity || 0);
    const riskClass = item.risk === "HIGH" ? "down" : item.risk === "LOW" ? "up" : "flat";
    const maturityClass = maturity >= 72 ? "up" : maturity < 60 ? "down" : "flat";
    return `
      <div class="v2-module-row">
        <div><strong>${escapeHtml(item.name || item.id || "--")}</strong><span>${escapeHtml(item.id || "--")}</span></div>
        <span class="${maturityClass}">${number(maturity, 0)}%</span>
        <span class="${riskClass}">${escapeHtml(item.risk || "--")}</span>
        <span>${escapeHtml(item.status || "--")} / ${escapeHtml(item.next || "--")}</span>
      </div>
    `;
  }).join("");
  renderDataReliability(data.data_reliability || null);
  renderMarketAdapters(data.market_adapters || null);
}

function dataSourceTone(row = {}) {
  if (row.tone) return row.tone;
  if (row.status === "ONLINE") return "up";
  if (row.status === "OFFLINE") return "down";
  return "flat";
}

function renderResearchDataQualityCards(data) {
  const target = $("researchDataQualityCards");
  if (!target) return;
  let cards = data?.cards || [];
  if (!cards.length && Array.isArray(data?.rows) && data.rows.length) {
    cards = data.rows.slice(0, 4).map((row) => ({
      label: row.name || row.id || "数据源",
      value: row.research_label || row.status || "--",
      detail: row.warning || row.next || row.freshness || row.detail || "",
      tone: dataSourceTone(row),
    }));
  }
  if (!cards.length) cards = researchDataQualitySnapshot().cards;
  target.innerHTML = cards.length ? cards.map((card) => `
    <div class="research-data-card ${card.tone || "flat"}">
      <span>${escapeHtml(card.label || "--")}</span>
      <strong>${escapeHtml(card.value || "--")}</strong>
      <em>${escapeHtml(card.detail || "")}</em>
    </div>
  `).join("") : `
    <div class="research-data-card flat"><span>数据源</span><strong>等待体检</strong><em>刷新后显示实时、延迟和兜底状态。</em></div>
  `;
}

function renderDataReliability(data) {
  if (!data) return;
  state.dataReliability = data;
  renderResearchDataQualityCards(data);
  $("dataReliabilitySummary").textContent = data.summary || "Data source check updated";
  $("dataReliabilitySummary").className = data.status === "ONLINE" ? "up" : data.status === "OFFLINE" ? "down" : "flat";
  $("dataReliabilityRows").innerHTML = (data.rows || []).map((row) => `
    <div class="data-quality-row">
      <span><strong>${escapeHtml(row.name || row.id || "--")}</strong><em>${escapeHtml(row.use_for || row.detail || "--")}</em></span>
      <span class="${dataSourceTone(row)}">${escapeHtml(row.research_label || row.status || "--")}</span>
      <span>${Number(row.latency_ms || 0) > 0 ? `${number(row.latency_ms, 0)}ms` : "--"}</span>
      <span>${escapeHtml(row.freshness || row.mode || "--")}</span>
      <span>${escapeHtml(row.warning || row.next || "--")}</span>
    </div>
  `).join("") || `<div class="data-quality-row empty"><span>No data source status</span><span>--</span><span>--</span><span>--</span><span>--</span></div>`;
}

function renderMarketAdapters(data) {
  if (!data || !$("marketAdapterRows")) return;
  state.marketAdapters = data;
  $("marketAdapterSummary").textContent = data.summary || "Adapter status updated";
  $("marketAdapterSummary").className = data.status === "ONLINE" ? "up" : data.status === "OFFLINE" ? "down" : "flat";
  $("marketAdapterRows").innerHTML = (data.rows || []).map((row) => `
    <div class="adapter-row">
      <span><strong>${escapeHtml(row.name || row.id || "--")}</strong><em>${escapeHtml((row.sources || []).join(" / "))}</em></span>
      <span class="${renderStatusClass(row.status)}">${escapeHtml(row.status || "--")}</span>
      <span>${number(row.score, 1)}</span>
      <span>${escapeHtml((row.capabilities || []).slice(0, 5).join(" / "))} / ${escapeHtml(row.safety || "--")}</span>
    </div>
  `).join("") || `<div class="adapter-row empty"><span>No adapters</span><span>--</span><span>--</span><span>--</span></div>`;
}

async function loadMarketAdapters() {
  try {
    $("marketAdapterSummary").textContent = "Checking adapters";
    const data = await api("/api/market/adapters");
    renderMarketAdapters(data);
    return data;
  } catch (error) {
    $("marketAdapterSummary").textContent = `Adapter status offline: ${error.message}`;
    $("marketAdapterSummary").className = "down";
    return null;
  }
}

function renderDataCache(data) {
  if (!data) return;
  state.dataCache = data;
  $("dataCacheSummary").textContent = data.summary || "History cache status updated";
  $("dataCacheRows").innerHTML = (data.rows || []).map((row) => {
    const statusClass = row.status === "READY" ? "up" : row.status === "MISSING" ? "down" : "flat";
    return `
      <div class="cache-backfill-row">
        <span><strong>${escapeHtml(row.symbol || "--")}</strong><em>${escapeHtml(row.source || "--")}</em></span>
        <span class="${statusClass}">${escapeHtml(row.status || "--")}</span>
        <span>${number(row.rows, 0)}</span>
        <span>${escapeHtml(row.first || "--")}~${escapeHtml(row.last || "--")}</span>
        <span>${escapeHtml(row.next || "--")}</span>
      </div>
    `;
  }).join("") || `<div class="cache-backfill-row empty"><span>No cache</span><span>--</span><span>--</span><span>--</span><span>--</span></div>`;
}

function renderDataBackfillProgress(status, results = [], activeSymbol = "") {
  const resultMap = new Map((results || []).map((row) => [row.symbol, row]));
  const rows = status?.rows || [];
  const done = results.length;
  const okCount = results.filter((row) => row.ok).length;
  const failCount = results.filter((row) => row.ok === false).length;
  $("dataCacheSummary").textContent = activeSymbol
    ? `补全缓存中：${activeSymbol} / 已完成 ${done} 个 / 成功 ${okCount} / 失败 ${failCount}`
    : `补全缓存进度：已完成 ${done} 个 / 成功 ${okCount} / 失败 ${failCount}`;
  $("dataCacheRows").innerHTML = rows.map((row) => {
    const result = resultMap.get(row.symbol);
    const running = activeSymbol === row.symbol;
    const statusText = running ? "RUNNING" : result ? (result.ok ? "READY" : "FAILED") : row.status;
    const statusClass = statusText === "READY" ? "up" : statusText === "FAILED" || statusText === "MISSING" ? "down" : "flat";
    const rowCount = result?.stats?.rows ?? row.rows;
    const source = result?.source || row.source || "--";
    const detail = running
      ? "正在从 OKX/Binance 拉取日线"
      : result
        ? `${result.fetched || 0} fetched / ${result.stored || 0} stored`
        : row.next || "--";
    return `
      <div class="cache-backfill-row">
        <span><strong>${escapeHtml(row.symbol || "--")}</strong><em>${escapeHtml(source)}</em></span>
        <span class="${statusClass}">${escapeHtml(statusText || "--")}</span>
        <span>${number(rowCount, 0)}</span>
        <span>${escapeHtml(row.first || result?.stats?.first || "--")}~${escapeHtml(row.last || result?.stats?.last || "--")}</span>
        <span>${escapeHtml(detail)}</span>
      </div>
    `;
  }).join("") || `<div class="cache-backfill-row empty"><span>No cache</span><span>--</span><span>--</span><span>--</span><span>--</span></div>`;
}

async function loadDataCache() {
  try {
    const data = await api("/api/data/cache/status");
    renderDataCache(data);
    return data;
  } catch (error) {
    $("dataCacheSummary").textContent = `History cache offline: ${error.message}`;
    $("dataCacheSummary").className = "down";
    return null;
  }
}

async function runDataBackfill() {
  const button = $("runDataBackfill");
  try {
    if (button) button.disabled = true;
    $("dataCacheSummary").textContent = "正在读取历史缓存队列...";
    let status = await api("/api/data/cache/status");
    const queue = (status.queue || []).filter((row) => row.symbol);
    if (!queue.length) {
      renderDataCache(status);
      $("dataCacheSummary").textContent = "历史缓存已补全，无需重复回填";
      return;
    }
    const results = [];
    renderDataBackfillProgress(status, results, queue[0].symbol);
    for (const row of queue) {
      renderDataBackfillProgress(status, results, row.symbol);
      const result = await apiMutation(`/api/data/cache/backfill?symbol=${encodeURIComponent(row.symbol)}&limit=500`);
      results.push(result);
      status = await api("/api/data/cache/status");
      renderDataBackfillProgress(status, results, "");
    }
    renderDataCache(status);
    const okCount = results.filter((row) => row.ok).length;
    $("dataCacheSummary").textContent = `补全完成：成功 ${okCount}/${results.length}，历史缓存状态已刷新`;
    await loadDataReliability();
  } catch (error) {
    $("dataCacheSummary").textContent = `Backfill failed: ${error.message}`;
    $("dataCacheSummary").className = "down";
  } finally {
    if (button) button.disabled = false;
  }
}

async function loadDataReliability() {
  try {
    $("dataReliabilitySummary").textContent = "Checking data sources";
    const data = await api("/api/data/reliability");
    renderDataReliability(data);
    loadMarketAdapters().catch(() => {});
    return data;
  } catch (error) {
    $("dataReliabilitySummary").textContent = `Data sources offline: ${error.message}`;
    $("dataReliabilitySummary").className = "down";
    renderResearchDataQualityCards(researchDataQualitySnapshot());
    return null;
  }
}

async function loadV2Platform() {
  try {
    const price = state.lastPrice || (state.candles[state.candles.length - 1]?.close || 0);
    const data = await api(`/api/platform/v2?price=${encodeURIComponent(price)}`);
    renderV2Platform(data);
    return data;
  } catch (error) {
    if ($("v2PlatformState")) {
      $("v2PlatformState").textContent = "Offline";
      $("v2PlatformState").className = "down";
      $("v2Summary").textContent = error.message;
    }
    return null;
  }
}

async function loadSixLaneRoadmap() {
  try {
    const price = state.lastPrice || (state.candles[state.candles.length - 1]?.close || 0);
    const data = await api(`/api/platform/six-lane?price=${encodeURIComponent(price)}`);
    renderSixLaneRoadmap(data);
    return data;
  } catch (error) {
    if ($("sixLaneSummary")) {
      $("sixLaneSummary").textContent = `Six-lane roadmap offline: ${error.message}`;
      $("sixLaneSummary").className = "down";
    }
    return null;
  }
}

async function loadDerivatives() {
  try {
    if (isStockMarket()) {
      const data = await api(`/api/contract/center?symbol=${encodeURIComponent(state.symbol)}`);
      const m = data.metrics || {};
      $("derivativeState").textContent = "Stock mode";
      $("contractSpot").textContent = m.spot_last ? number(m.spot_last, m.spot_last > 100 ? 1 : 4) : "--";
      ["fundingRate", "fundingAnnualized", "fundingTime", "openInterest", "contractValue", "swapLast", "markPrice", "indexPrice", "basisMetric", "spotSwapBasis", "contractTickLot"].forEach((id) => { if ($(id)) $(id).textContent = "--"; });
      $("fundingHistory").innerHTML = `<div class="funding-row"><span>Stock mode does not use funding rate</span><strong>--</strong></div>`;
      return;
    }
    const data = await api(`/api/contract/center?symbol=${encodeURIComponent(state.symbol)}`);
    state.contractCenter = data;
    const m = data.metrics || {};
    $("derivativeState").textContent = data.swap || state.symbol;
    $("contractSpot").textContent = m.spot_last ? number(m.spot_last, m.spot_last > 100 ? 1 : 4) : "--";
    $("swapLast").textContent = m.swap_last ? number(m.swap_last, m.swap_last > 100 ? 1 : 4) : "--";
    $("indexPrice").textContent = m.index_price ? number(m.index_price, m.index_price > 100 ? 1 : 4) : "--";
    $("markPrice").textContent = m.mark_price ? number(m.mark_price, m.mark_price > 100 ? 1 : 4) : "--";
    $("fundingRate").textContent = `${number(m.funding_rate_pct, 5)}%`;
    $("fundingRate").className = cssMove(m.funding_rate_pct);
    $("fundingAnnualized").textContent = `${number(m.funding_annualized_pct, 2)}%`;
    $("fundingTime").textContent = m.next_funding_time ? new Date(Number(m.next_funding_time)).toLocaleString("zh-CN", { hour12: false }) : "--";
    $("openInterest").textContent = compact(m.open_interest_ccy || m.open_interest);
    $("basisMetric").textContent = `${m.mark_index_basis_pct >= 0 ? "+" : ""}${number(m.mark_index_basis_pct, 5)}%`;
    $("basisMetric").className = cssMove(m.mark_index_basis_pct);
    $("spotSwapBasis").textContent = `${m.spot_swap_basis_pct >= 0 ? "+" : ""}${number(m.spot_swap_basis_pct, 5)}%`;
    $("spotSwapBasis").className = cssMove(m.spot_swap_basis_pct);
    $("contractValue").textContent = m.contract_value ? `${m.contract_value} ${m.contract_value_ccy || ""}` : "--";
    $("contractTickLot").textContent = `${m.tick_size || "--"} / ${m.lot_size || "--"}`;
    loadFundingHistory(data.swap);
  } catch (error) {
    ["contractSpot", "fundingRate", "fundingAnnualized", "fundingTime", "openInterest", "contractValue", "swapLast", "markPrice", "indexPrice", "basisMetric", "spotSwapBasis", "contractTickLot"].forEach((id) => { if ($(id)) $(id).textContent = "--"; });
  }
}

async function loadLeaderboard() {
  try {
    const data = await api("/api/strategy/leaderboard?limit=240");
    const rows = data.leaderboard || [];
    $("leaderboardRows").innerHTML = rows.map((row, index) => `
      <div class="leader-row evidence-neutral">
        <span class="leader-rank">${index + 1}</span>
        <span class="leader-main"><strong>${row.name}</strong><span>${row.note}</span></span>
        <span class="flat" data-raw-score="${escapeHtml(row.score)}" title="开发期启发式分数仅用于描述比较，不构成选参或授权">${number(row.score, 2)}</span>
        <span>${row.risk}</span>
      </div>
    `).join("");
  } catch (error) {
    $("leaderboardRows").innerHTML = `<div class="leader-row"><span></span><span class="leader-main"><strong>Offline</strong><span>${error.message}</span></span><span>--</span><span>--</span></div>`;
  }
}

function renderStrategyConditionLedger(rows, {
  headingId,
  headingText,
  detailKey,
  observationKey = null,
  kind,
}) {
  if (!Array.isArray(rows) || !rows.length) return "";
  const rowMarkup = rows.map((row) => {
    const observationMarkup = observationKey
      ? `<span class="strategy-condition-observation">${escapeHtml(row?.[observationKey] || "--")}</span>`
      : "";
    return `
      <div class="strategy-condition-row" data-raw-status="${escapeHtml(row?.rawStatus || "UNKNOWN")}">
        <dt><code>${escapeHtml(row?.conditionId || "--")}</code></dt>
        <dd>
          <span class="strategy-condition-predicate">${escapeHtml(row?.[detailKey] || "--")}</span>
          ${observationMarkup}
          <span class="strategy-condition-outcome">${escapeHtml(row?.outcomeText || "未核验")}</span>
          <small class="strategy-condition-boundary">${escapeHtml(row?.boundaryText || "边界未核验")}</small>
        </dd>
      </div>
    `;
  }).join("");
  return `
    <section class="strategy-condition-ledger" data-ledger-kind="${escapeHtml(kind)}" aria-labelledby="${escapeHtml(headingId)}">
      <h4 id="${escapeHtml(headingId)}">${escapeHtml(headingText)}</h4>
      <dl class="strategy-condition-list">${rowMarkup}</dl>
    </section>
  `;
}

function renderStrategyLabEvidence(data = {}) {
  const target = $("strategyLabEvidence");
  if (!target) return;
  const evidence = evidenceStrategyLabPresentation(data);
  const correlation = evidenceStrategyCorrelationClusterPresentation(data?.correlation_cluster_summary);
  target.dataset.connectionStatus = evidence.connectionStatus;
  target.dataset.rawParameterStatus = evidence.rawParameterStatus;
  target.dataset.rawCostStatus = evidence.rawCostStatus;
  target.dataset.rawSurfaceStatus = evidence.rawSurfaceStatus;
  if ($("btRiskSurfaceDetails")) $("btRiskSurfaceDetails").dataset.rawStatus = evidence.rawSurfaceStatus;
  target.dataset.rawTemporalStatus = evidence.rawTemporalStatus;
  target.dataset.rawImplementationStatus = evidence.rawImplementationStatus;
  target.dataset.rawFullImplementationStatus = evidence.rawFullImplementationStatus;
  target.dataset.rawHypothesisStatus = evidence.rawHypothesisStatus;
  target.dataset.rawSearchLineageStatus = evidence.rawSearchLineageStatus;
  target.dataset.rawAdmissionStatus = evidence.rawAdmissionStatus;
  target.dataset.rawMechanismStatus = evidence.rawMechanismStatus;
  target.dataset.rawFutureConditionStatus = evidence.rawFutureConditionStatus;
  target.dataset.rawPostSelectionStatus = evidence.rawPostSelectionStatus;
  target.dataset.rawFrozenTestStatus = evidence.rawFrozenTestStatus;
  target.dataset.rawHoldoutStatus = evidence.rawHoldoutStatus;
  target.dataset.rawCorrelationClusterStatus = correlation.rawStatus;
  target.title = `${evidence.permissionText}\n${evidence.sourceText}`;
  target.innerHTML = `
    <section class="strategy-evidence-band provenance" aria-labelledby="strategyEvidenceSourceHeading">
      <header><span aria-hidden="true" data-band-code="source">源</span><h3 id="strategyEvidenceSourceHeading">来源与当前性</h3></header>
      <div data-evidence-role="mode"><span>证据模式</span><strong>${escapeHtml(evidence.modeText)}</strong></div>
      <div data-evidence-role="source"><span>冻结来源</span><strong>${escapeHtml(evidence.sourceText)}</strong></div>
      <div data-evidence-role="implementation" data-raw-status="${escapeHtml(evidence.rawImplementationStatus)}" data-raw-full-status="${escapeHtml(evidence.rawFullImplementationStatus)}"><span>实现身份</span><strong>${escapeHtml(evidence.implementationText)}</strong></div>
      <div data-evidence-role="currentness"><span>时效边界</span><strong>${escapeHtml(evidence.currentnessText)}</strong></div>
      <div data-evidence-role="hypothesis" data-raw-status="${escapeHtml(evidence.rawHypothesisStatus)}"><span>研究假设</span><strong>${escapeHtml(evidence.hypothesisText)}</strong></div>
      <div class="strategy-search-lineage-row" data-evidence-role="search-lineage" data-raw-status="${escapeHtml(evidence.rawSearchLineageStatus)}"><span>检索谱系</span><strong>${escapeHtml(evidence.lineageText)}</strong></div>
    </section>
    <section class="strategy-evidence-band robustness" aria-labelledby="strategyEvidenceRobustnessHeading">
      <header><span aria-hidden="true" data-band-code="robustness">稳</span><h3 id="strategyEvidenceRobustnessHeading">完整性与稳健性</h3></header>
      <div data-evidence-role="coverage"><span>研究覆盖</span><strong>${escapeHtml(evidence.coverageText)}</strong></div>
      <section class="strategy-correlation-ledger" data-evidence-role="correlation-cluster" data-raw-status="${escapeHtml(correlation.rawStatus)}" aria-labelledby="strategyCorrelationLedgerHeading">
        <header><span>跨标的独立性</span><strong>${escapeHtml(correlation.statusText)}</strong></header>
        <ol class="strategy-correlation-flow">
          <li data-stage="source"><span>SOURCE</span><strong>${escapeHtml(correlation.sourceText)}</strong></li>
          <li data-stage="gap"><span>GAP</span><strong>${escapeHtml(correlation.gapText)}</strong></li>
          <li data-stage="maturity"><span>MATURITY</span><strong>${escapeHtml(correlation.maturityText)}</strong></li>
          <li data-stage="permission"><span>PERMISSION</span><strong>${escapeHtml(correlation.permissionText)}</strong></li>
        </ol>
        <small id="strategyCorrelationLedgerHeading">${escapeHtml(correlation.detailText)}</small>
      </section>
      <div class="strategy-post-selection-group" data-evidence-role="post-selection" data-raw-status="${escapeHtml(evidence.rawPostSelectionStatus)}" role="group" aria-label="冻结后历史复算，历史回测，不是自然前向">
        <span>冻结后历史复算 · 非自然前向</span>
        <strong>${escapeHtml(evidence.postSelectionText)}</strong>
        <div data-evidence-role="frozen-test" data-raw-status="${escapeHtml(evidence.rawFrozenTestStatus)}"><span>冻结 TEST · 历史重放</span><strong>${escapeHtml(evidence.frozenTestText)}</strong></div>
        <div data-evidence-role="holdout-confirmation" data-raw-status="${escapeHtml(evidence.rawHoldoutStatus)}"><span>单次历史留出 · 非自然前向</span><strong>${escapeHtml(evidence.holdoutText)}</strong></div>
      </div>
      <div data-raw-status="${escapeHtml(evidence.rawParameterStatus)}"><span>参数平台</span><strong>${escapeHtml(evidence.parameterText)}</strong></div>
      <div data-raw-status="${escapeHtml(evidence.rawCostStatus)}"><span>成本压力</span><strong>${escapeHtml(evidence.costText)}</strong></div>
      <div data-raw-status="${escapeHtml(evidence.rawTemporalStatus)}"><span>时间切片</span><strong>${escapeHtml(evidence.temporalText)}</strong></div>
    </section>
    <section class="strategy-evidence-band invalidation" aria-labelledby="strategyEvidenceInvalidationHeading">
      <header><span aria-hidden="true" data-band-code="invalidation">止</span><h3 id="strategyEvidenceInvalidationHeading">失效与权限边界</h3></header>
      <div class="strategy-preregistered-gate-group" role="group" aria-label="开发期机制门与未来未到期条件">
        <div data-evidence-role="admission" data-raw-status="${escapeHtml(evidence.rawAdmissionStatus)}"><span>事前研究门禁</span><strong>${escapeHtml(evidence.admissionText)}</strong></div>
        <div data-evidence-role="mechanism-condition" data-raw-status="${escapeHtml(evidence.rawMechanismStatus)}"><span>开发期机制条件</span><strong>${escapeHtml(evidence.mechanismConditionText)}</strong></div>
        ${renderStrategyConditionLedger(evidence.mechanismConditionRows, {
          headingId: "strategyMechanismLedgerHeading",
          headingText: "开发期机制判据账页",
          detailKey: "predicateText",
          observationKey: "observationText",
          kind: "mechanism",
        })}
        <div data-evidence-role="future-condition" data-raw-status="${escapeHtml(evidence.rawFutureConditionStatus)}"><span>未来标准条件 · 非通过</span><strong>${escapeHtml(evidence.futureConditionText)}</strong></div>
        ${renderStrategyConditionLedger(evidence.futureConditionRows, {
          headingId: "strategyFutureLedgerHeading",
          headingText: "未来条件到期账页",
          detailKey: "stageText",
          kind: "future",
        })}
      </div>
      <div data-evidence-role="failure"><span>当前失效证据</span><strong>${escapeHtml(evidence.failureText)}</strong></div>
      <div data-evidence-role="hypothesis-failure"><span>事前失效条件</span><strong>${escapeHtml(evidence.hypothesisFailureText)}</strong></div>
      <small>${escapeHtml(evidence.detailText)}</small>
    </section>
  `;
  renderEvidenceAttributionSpine();
}

async function loadStrategyResearchEvidence(strategy, { force = false } = {}) {
  if (
    !force
    && Object.prototype.hasOwnProperty.call(state.strategyResearchEvidenceCache, strategy)
  ) {
    return state.strategyResearchEvidenceCache[strategy];
  }
  try {
    const response = await fetch(
      `/api/strategy/research-evidence?strategy=${encodeURIComponent(strategy)}`,
      { cache: "no-store", headers: { Accept: "application/json" } },
    );
    const payload = await response.json();
    const snapshot = response.ok && payload && typeof payload === "object" && !Array.isArray(payload)
      ? payload
      : null;
    if (snapshot) state.strategyResearchEvidenceCache[strategy] = snapshot;
    return snapshot;
  } catch (_error) {
    return null;
  }
}

async function loadStrategyLab({ refreshEvidence = false } = {}) {
  const strategy = $("strategySelect").value || "dual_ma";
  renderEvidenceAttributionSpine();
  const price = state.lastPrice || (state.candles[state.candles.length - 1]?.close || 0);
  const requestSeq = ++runtime.strategyLabRequestSeq;
  try {
    $("strategyLabSummary").textContent = "Calculating";
    const [data, frozenEvidence] = await Promise.all([
      api(`/api/strategy/lab?symbol=${encodeURIComponent(state.symbol)}&strategy=${encodeURIComponent(strategy)}&price=${encodeURIComponent(price)}`),
      loadStrategyResearchEvidence(strategy, { force: refreshEvidence }),
    ]);
    if (requestSeq !== runtime.strategyLabRequestSeq) return;
    state.strategyLab = data;
    state.strategyResearchEvidence = frozenEvidence;
    renderStrategyLabEvidence(frozenEvidence || {});
    $("strategyLabSummary").textContent = `研究候选 · ${data.strategy?.name || "Strategy"} / ${data.regime || "--"}`;
    $("strategyRegime").textContent = `开发期环境观察 · Trend ${number(data.trend_pct, 2)}% / Vol ${number(data.volatility_pct, 2)}%`;
    $("strategyLabRows").innerHTML = (data.rows || []).map((row) => `
      <div class="strategy-lab-row evidence-neutral" data-lab-planning-only="1" data-lab-position="${row.planning_candidate?.position_pct ?? ""}" data-lab-tp="${row.planning_candidate?.take_profit ?? ""}" data-lab-sl="${row.planning_candidate?.stop_loss ?? ""}" role="button" tabindex="0" aria-label="开发期规划候选 ${row.preset || ""} · 仅研究，不选参、不授权" title="开发期启发式规划候选 · 仅研究，不选参、不授权">
        <span>${row.preset}</span>
        <span>${row.planning_candidate?.position_pct == null ? "--" : `${number(row.planning_candidate.position_pct, 0)}%`}</span>
        <span>${number(row.planning_candidate?.take_profit, 2)}</span>
        <span>${number(row.planning_candidate?.stop_loss, 2)}</span>
        <span class="flat">${row.raw_score == null ? "开发期分待核" : `开发期分 ${number(row.raw_score, 1)}`}</span>
        <span>${row.note}</span>
      </div>
    `).join("");
    document.querySelectorAll(".strategy-lab-row").forEach((row) => {
      row.addEventListener("click", () => {
        $("positionInput").value = row.dataset.labPosition || "25";
        $("riskSource").value = "MANUAL";
        $("riskValueMode").value = "PRICE";
        $("takeProfitInput").value = row.dataset.labTp || "";
        $("stopLossInput").value = row.dataset.labSl || "";
        syncRiskPlaceholders();
        $("strategyAnalysis").textContent = "已复制到研究表单，仅作规划观察；不代表参数选定，不授予模拟或实盘权限。";
      });
      row.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          row.click();
        }
      });
    });
  } catch (error) {
    if (requestSeq !== runtime.strategyLabRequestSeq) return;
    $("strategyLabSummary").textContent = "Offline";
    $("strategyRegime").textContent = error.message;
    state.strategyResearchEvidence = null;
    renderStrategyLabEvidence({});
  }
}

function warRoomQuery(price) {
  const query = new URLSearchParams({
    symbol: state.symbol,
    strategy: $("strategySelect").value || "dual_ma",
    price: String(price || 0),
    leverage: $("leverageInput").value || "1",
    positionPct: $("positionInput").value || "25",
    riskSource: $("riskSource").value || "AI",
    riskValueMode: $("riskValueMode").value || "PRICE",
    takeProfit: $("takeProfitInput").value || "0",
    stopLoss: $("stopLossInput").value || "0",
    takeProfitPct: riskInputAsPct("take"),
    stopLossPct: riskInputAsPct("stop"),
    orderType: $("strategyOrderType").value || "MARKET",
    marginMode: $("marginMode").value || "CROSS",
    directionMode: $("directionMode").value || "LONG_ONLY",
    trailingTakeEnabled: $("trailingTakeEnabled").checked ? "true" : "false",
    trailingTakePct: $("trailingTakePct").value || "1.5",
    trailingStopEnabled: $("trailingStopEnabled").checked ? "true" : "false",
    trailingStopPct: $("trailingStopPct").value || "1.0",
    reduceOnly: $("reduceOnly").checked ? "true" : "false",
  });
  return query.toString();
}

function renderWarRoomBrief(data) {
  const playbook = data.playbook || {};
  const indicators = (playbook.primary_indicators || []).join(" / ") || "--";
  $("strategyPlaybookCards").innerHTML = `
    <div class="playbook-card"><span>Core Rule</span><strong>${escapeHtml(playbook.core_rule || "--")}</strong></div>
    <div class="playbook-card"><span>Best Regime</span><strong>${escapeHtml(playbook.best_regime || "--")}</strong></div>
    <div class="playbook-card"><span>Avoid Regime</span><strong>${escapeHtml(playbook.avoid_regime || "--")}</strong></div>
    <div class="playbook-card"><span>Indicators</span><strong>${escapeHtml(indicators)}</strong></div>
    <div class="playbook-card"><span>Entry Logic</span><strong>${escapeHtml(playbook.entry_logic || "--")}</strong></div>
    <div class="playbook-card"><span>Exit Logic</span><strong>${escapeHtml(playbook.exit_logic || "--")}</strong></div>
  `;
  $("strategyAnchorRows").innerHTML = (data.anchor_plan || []).map((row) => {
    const status = evidenceResearchCellPresentation(row.status);
    const action = evidenceStrategyActionPresentation(row.raw_action || row.action);
    return `
      <div class="anchor-row evidence-neutral" data-raw-status="${escapeHtml(status.rawStatus)}" data-raw-action="${escapeHtml(String(row.action || "WAIT"))}" title="${escapeHtml(`原始状态 ${status.rawStatus} · ${action.permissionText}`)}">
        <span class="flat">${escapeHtml(status.label)}</span>
        <strong>${escapeHtml(row.name)}</strong>
        <em>${number(row.anchor, row.anchor > 100 ? 2 : 6)}</em>
        <small>${escapeHtml(action.conclusionText)} / ${escapeHtml(row.detail)}</small>
      </div>
    `;
  }).join("") || `<div class="war-room-note">Waiting for anchor plan</div>`;
  $("strategyExecutionLog").innerHTML = (data.execution_log || []).map((row) => {
    const level = evidenceResearchCellPresentation(row.level, "研究记录");
    return `
      <div class="execution-row evidence-neutral" data-raw-status="${escapeHtml(level.rawStatus)}" title="${escapeHtml(`原始状态 ${level.rawStatus} · 仅研究记录`)}">
        <span class="flat">${escapeHtml(level.label)}</span>
        <strong>${escapeHtml(row.title)}</strong>
        <small>${escapeHtml(row.detail)}</small>
      </div>
    `;
  }).join("") || `<div class="war-room-note">Waiting for research explanation</div>`;
}

async function loadStrategyWarRoom() {
  const price = state.lastPrice || (state.candles[state.candles.length - 1]?.close || 0);
  try {
    $("strategyWarSummary").textContent = "Strategy room calculating";
    const data = await api(`/api/strategy/war-room?${warRoomQuery(price)}`);
    state.strategyWarRoom = data;
    $("strategyWarSummary").textContent = evidenceResearchValue(data.summary || "Strategy room updated");
    $("strategyWarCards").innerHTML = (data.cards || []).map((card) => {
      const status = evidenceResearchCellPresentation(card.status);
      return `
        <div class="strategy-war-card evidence-neutral" data-raw-status="${escapeHtml(status.rawStatus)}" title="${escapeHtml(`原始状态 ${status.rawStatus} · ${status.detailText}`)}">
          <span>${escapeHtml(card.name)}</span>
          <strong>${escapeHtml(evidenceResearchValue(card.value))}</strong>
          <em>${escapeHtml(card.detail)}</em>
        </div>
      `;
    }).join("");
    renderWarRoomBrief(data);
    $("strategyWarMatrix").innerHTML = (data.matrix || []).map((row) => {
      const status = evidenceResearchCellPresentation(row.status);
      return `
        <div class="war-room-row" data-raw-status="${escapeHtml(status.rawStatus)}" title="${escapeHtml(`原始状态 ${status.rawStatus}`)}">
          <span>${escapeHtml(row.name)}</span>
          <span class="flat">${escapeHtml(status.label)}</span>
          <span>${number(row.score, 1)}</span>
          <span>${escapeHtml(row.detail)}</span>
        </div>
      `;
    }).join("");
    $("strategyWarEntry").innerHTML = (data.entry_ladder || []).map((row) => `
      <div class="war-room-row ladder">
        <span>${escapeHtml(row.name)}</span>
        <span>${number(row.price, 2)}</span>
        <span>${number(row.size_pct, 0)}%</span>
        <span>${escapeHtml(row.rule)}</span>
      </div>
    `).join("");
    $("strategyWarExit").innerHTML = (data.exit_ladder || []).map((row) => `
      <div class="war-room-row ladder">
        <span>${escapeHtml(row.name)}</span>
        <span>${number(row.price, 2)}</span>
        <span>${number(row.size_pct, 0)}%</span>
        <span>${escapeHtml(row.rule)}</span>
      </div>
    `).join("");
    $("strategyWarNoTrade").innerHTML = (data.no_trade || []).map((item) => `
      <div class="war-room-note">${escapeHtml(item)}</div>
    `).join("");
    $("strategyWarTimeline").innerHTML = (data.timeline || []).map((row) => {
      const status = evidenceResearchCellPresentation(row.status);
      return `
        <div class="war-room-row timeline" data-raw-status="${escapeHtml(status.rawStatus)}" title="${escapeHtml(`原始状态 ${status.rawStatus}`)}">
          <span>${escapeHtml(row.step)}</span>
          <span class="flat">${escapeHtml(status.label)}</span>
          <span>${escapeHtml(row.name)}</span>
          <span>${escapeHtml(row.detail)}</span>
        </div>
      `;
    }).join("");
    $("strategyWarTop").innerHTML = (data.top_strategies || []).map((row) => {
      const action = evidenceStrategyActionPresentation(row.raw_action || row.action);
      return `
        <div class="war-room-row top-strategy" data-strategy="${escapeHtml(row.id)}" data-raw-action="${escapeHtml(String(row.action || "WAIT"))}" title="${escapeHtml(action.permissionText)}">
          <span>${escapeHtml(row.name)}</span>
          <span class="flat">${escapeHtml(action.conclusionText)}</span>
          <span>${number(row.score, 1)}</span>
          <span>${escapeHtml(row.reason)}</span>
        </div>
      `;
    }).join("");
    document.querySelectorAll(".top-strategy").forEach((row) => {
      row.addEventListener("click", () => {
        $("strategySelect").value = row.dataset.strategy;
        renderStrategyCards();
        loadStrategyLab();
        loadStrategyWarRoom();
        loadStrategyDoctor();
      });
    });
    renderStrategyExplainPanel();
    renderSideInsights();
  } catch (error) {
    $("strategyWarSummary").textContent = `Strategy room offline: ${error.message}`;
    renderStrategyExplainPanel();
  }
}

async function loadStrategyCompare() {
  const price = state.lastPrice || (state.candles[state.candles.length - 1]?.close || 0);
  try {
    $("strategyCompareSummary").textContent = "开发期研究比较中";
    const data = await api(`/api/strategy/compare?symbol=${encodeURIComponent(state.symbol)}&price=${encodeURIComponent(price)}`);
    state.strategyCompare = data;
    $("strategyCompareSummary").textContent = `市场环境观察 · ${data.regime?.regime || "--"} / Trend ${number(data.regime?.trend_pct, 2)}% / Range ${number(data.regime?.range_pct, 2)}%`;
    $("strategyCompareRows").innerHTML = (data.rows || []).slice(0, 12).map((row) => {
      const action = evidenceStrategyActionPresentation(row.raw_action || row.action);
      return `
        <div class="strategy-compare-row evidence-neutral" data-strategy="${row.id}" data-raw-action="${escapeHtml(String(row.raw_action || row.action || "WAIT"))}" role="button" tabindex="0" aria-label="开发期策略比较 ${row.name || ""} · 仅研究，不选参、不授权" title="${escapeHtml(action.permissionText)}">
          <span>${escapeHtml(row.name)}</span>
          <span class="flat">${escapeHtml(action.conclusionText)}</span>
          <span>模型估计 ${number(row.probability_pct, 0)}% · 未校准</span>
          <span class="flat">${number(row.score, 1)}</span>
          <span>${escapeHtml(row.reason)} / Start-Stop: ${escapeHtml(row.enabled_condition)} / ${escapeHtml(row.stop_condition)}</span>
        </div>
      `;
    }).join("");
    document.querySelectorAll(".strategy-compare-row").forEach((row) => {
      row.addEventListener("click", () => {
        $("strategySelect").value = row.dataset.strategy;
        renderStrategyCards();
        loadStrategyLab();
        loadStrategyWarRoom();
      });
      row.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          row.click();
        }
      });
    });
  } catch (error) {
    $("strategyCompareSummary").textContent = `研究比较离线：${error.message}`;
  }
}

function renderStatusClass(status) {
  return status === "PASS" || status === "DONE" || status === "READY" || status === "RUNNING" || status === "EXTERNAL"
    ? "up"
    : status === "BLOCK" || status === "BLOCKED" || status === "ERROR"
      ? "down"
      : "flat";
}

function readinessClass(value) {
  return value >= 70 ? "up" : value <= 45 ? "down" : "flat";
}

function renderReleasePipeline(targetId, pipeline) {
  const target = $(targetId);
  if (!target) return;
  const stages = pipeline?.stages || [];
  const stageLabels = {
    research: "研究输入",
    backtest: "可复现回测",
    temporal_validation: "样本外验证",
    lookahead: "未来函数检查",
    strategy_doctor: "策略体检",
    paper_run: "模拟候选",
    audit_report: "审计报告",
    live_trading: "实盘硬墙",
  };
  target.innerHTML = stages.length ? stages.map((row) => {
    const stage = String(row?.stage || "").trim().toLowerCase();
    const rawStatus = String(row?.status || "WAIT").trim().toUpperCase() || "WAIT";
    const presentation = stage === "paper_run" || stage === "live_trading"
      ? evidencePipelineStagePresentation(stage, rawStatus, {
        paperAuthorized: pipeline?.paper_authorized === true,
        liveHardLocked: true,
      })
      : evidenceResearchStatusPresentation(rawStatus);
    const detail = String(row?.detail || "").trim();
    const rawOnly = /^(PASS|READY|COMPLETE|COMPLETED|DONE|WAIT|WAITING|BLOCK|BLOCKED|RUNNING|ACTIVE)$/i.test(detail);
    return `
      <div class="release-step evidence-stage" data-evidence-state="${escapeHtml(presentation.stateKind)}" data-raw-status="${escapeHtml(presentation.rawStatus)}" title="${escapeHtml(`原始状态 ${presentation.rawStatus}${detail && !rawOnly ? `\n${detail}` : ""}`)}">
        <span class="flat">${escapeHtml(presentation.label)}</span>
        <strong>${escapeHtml(stageLabels[stage] || stage || "研究阶段")}</strong>
        <em>${escapeHtml(!rawOnly && detail ? detail : presentation.detailText)}</em>
      </div>
    `;
  }).join("") : `
    <div class="release-step empty evidence-stage" data-evidence-state="waiting"><span class="flat">尚无研究证据</span><strong>研究证据路径</strong><em>先完成登记、回测和体检；这些状态不授予模拟或实盘权限。</em></div>
  `;
}

async function loadStrategyDoctor(record = false) {
  const strategy = $("strategySelect").value || "dual_ma";
  const directionMode = $("directionMode").value || "LONG_ONLY";
  const price = state.lastPrice || (state.candles[state.candles.length - 1]?.close || 0);
  try {
    $("strategyDoctorSummary").textContent = "Checking";
    const endpoint = `${record ? "/api/strategy/doctor" : "/api/strategy/doctor/preview"}?symbol=${encodeURIComponent(state.symbol)}&strategy=${encodeURIComponent(strategy)}&price=${encodeURIComponent(price)}&directionMode=${encodeURIComponent(directionMode)}`;
    const data = await (record ? apiMutation(endpoint) : api(endpoint));
    state.strategyDoctor = data;
    $("strategyDoctorSummary").textContent = evidenceResearchValue(data.summary || "Check complete");
    const doctorPresentation = evidenceStrategyPresentation({
      hasSignal: Boolean(data.signal?.action),
      hasAnalysis: Boolean(data.direction),
      action: data.signal?.raw_action || data.signal?.action,
      direction: data.direction,
    });
    $("strategyDoctorScores").innerHTML = `
      <div><span>Score · 研究诊断</span><strong class="flat">${number(data.score, 1)}</strong></div>
      <div><span>Market</span><strong>${data.regime?.regime || "--"}</strong></div>
      <div><span>结论</span><strong class="flat">${escapeHtml(doctorPresentation.conclusionText)}</strong></div>
      <div><span>方向</span><strong>${escapeHtml(doctorPresentation.directionText)}</strong></div>
    `;
    $("strategyDoctorLifecycle").innerHTML = (data.lifecycle || []).map((row) => {
      const presentation = evidenceResearchStatusPresentation(row.status);
      return `
        <div class="lifecycle-step evidence-stage" data-evidence-state="${escapeHtml(presentation.stateKind)}" data-raw-status="${escapeHtml(presentation.rawStatus)}" title="${escapeHtml(`原始状态 ${presentation.rawStatus}`)}">
          <span class="flat">${escapeHtml(presentation.label)}</span>
          <strong>${escapeHtml(row.stage || "研究阶段")}</strong>
          <em>${escapeHtml(row.detail || presentation.detailText)}</em>
        </div>
      `;
    }).join("");
    renderReleasePipeline("strategyReleasePipeline", data.release_pipeline);
    $("strategyDoctorRows").innerHTML = (data.rows || []).map((row) => {
      const presentation = evidenceResearchStatusPresentation(row.status);
      return `
        <div class="doctor-row" data-evidence-state="${escapeHtml(presentation.stateKind)}" data-raw-status="${escapeHtml(presentation.rawStatus)}" title="${escapeHtml(`原始状态 ${presentation.rawStatus}`)}">
          <span>${escapeHtml(row.name || "研究检查")}</span>
          <span class="flat">${escapeHtml(row.label || presentation.label)}</span>
          <span>${number(row.score, 1)}</span>
          <span>${escapeHtml(row.detail || presentation.detailText)}</span>
        </div>
      `;
    }).join("");
    $("strategyCallbackRows").innerHTML = (data.callbacks || []).map((row) => {
      const presentation = evidenceResearchStatusPresentation(row.status);
      return `
        <div class="callback-row" data-evidence-state="${escapeHtml(presentation.stateKind)}" data-raw-status="${escapeHtml(presentation.rawStatus)}" title="${escapeHtml(`原始状态 ${presentation.rawStatus}`)}">
          <span>${escapeHtml(row.name || "模块")}</span>
          <span>${escapeHtml(row.mapped || "--")}</span>
          <span class="flat">${escapeHtml(presentation.label)}</span>
        </div>
      `;
    }).join("");
  } catch (error) {
    $("strategyDoctorSummary").textContent = `Strategy check offline: ${error.message}`;
  }
}

async function loadBotCenter() {
  const price = state.lastPrice || (state.candles[state.candles.length - 1]?.close || 0);
  try {
    $("botCenterSummary").textContent = "正在核对研究观察台";
    const data = await api(`/api/bot/center?symbol=${encodeURIComponent(state.symbol)}&price=${encodeURIComponent(price)}`);
    state.botCenter = data;
    $("botCenterSummary").textContent = data.summary || "研究机器人观察台已更新";
    $("botLayerRows").innerHTML = (data.layers || []).map((row) => `
      <div class="bot-layer-card">
        <span class="flat" data-raw-status="${escapeHtml(row.raw_status || row.status || "UNKNOWN")}" title="原始状态 ${escapeHtml(row.raw_status || "UNKNOWN")}">研究状态</span>
        <strong>${escapeHtml(row.name || "研究层")}</strong>
        <em>${number(row.score, 0)} · ${escapeHtml(row.detail || "研究证据待核验")}</em>
      </div>
    `).join("");
    $("botBlueprintRows").innerHTML = (data.blueprints || []).map((row) => `
      <div class="bot-blueprint-row evidence-neutral">
        <span><strong>${escapeHtml(row.name || "研究机器人")}</strong><em>${escapeHtml(row.inspired_by || "研究参考")}</em></span>
        <span>${escapeHtml(row.family || "研究类型")}</span>
        <span class="flat" data-raw-status="${escapeHtml(row.raw_status || row.status || "UNKNOWN")}">研究观察</span>
        <span class="flat">${number(row.readiness, 0)}</span>
        <span>${escapeHtml(row.best_regime || "适用区间待核验")} / ${escapeHtml(row.next || "研究缺口待补")}</span>
      </div>
    `).join("");
    $("botAllocationRows").innerHTML = (data.allocations || []).map((row) => `
      <div class="allocation-row">
        <span>${escapeHtml(row.bucket || "研究桶")}</span>
        <span>未提供</span>
        <span>${escapeHtml(row.reason || "研究草案待核验")}</span>
      </div>
    `).join("");
    $("botGapRows").innerHTML = (data.gaps || []).map((row) => `
      <div class="gap-row">
        <span>${escapeHtml(row.gap || "研究缺口")}</span>
        <span class="flat">${escapeHtml(row.priority || "研究缺口")}</span>
        <span>${escapeHtml(row.detail || "证据待核验")}</span>
      </div>
    `).join("");
  } catch (error) {
    $("botCenterSummary").textContent = `研究机器人观察台离线：${error.message}`;
  }
}

function renderStrategyRobotProfiles(data) {
  if (!data) return;
  state.strategyRobotProfiles = data;
  $("robotProfileSummary").textContent = data.summary || "机器人研究档案已更新";
  $("robotProfileRows").innerHTML = (data.rows || []).slice(0, 12).map((row) => `
    <div class="robot-profile-row" data-robot-strategy="${escapeHtml(row.id)}">
      <span><strong>${escapeHtml(row.bot_name || "--")}</strong><em>${escapeHtml(row.bot_family || "--")} / ${row.research_role === "RESEARCH_PRIMARY" ? "研究主观察" : "研究观察"}</em></span>
      <span><strong>${escapeHtml(row.name || row.id || "--")}</strong><em>${escapeHtml(row.style || "--")} / ${escapeHtml(row.market_action || "研究结论待核验")}</em></span>
      <span class="flat">${number(row.readiness, 1)}</span>
      <span class="flat" data-raw-status="${escapeHtml(row.raw_status || row.status || "UNKNOWN")}">${escapeHtml(row.status_label || "研究状态待核验")}</span>
      <span>${escapeHtml(row.start_condition || "研究观察条件待核验")} / ${escapeHtml(row.next || row.stop_condition || "研究缺口待补")}</span>
    </div>
  `).join("") || `<div class="robot-profile-row empty"><span>No robot profiles</span><span>--</span><span>--</span><span>--</span><span>--</span></div>`;
  document.querySelectorAll("[data-robot-strategy]").forEach((row) => {
    row.addEventListener("click", () => {
      if (!row.dataset.robotStrategy) return;
      $("strategySelect").value = row.dataset.robotStrategy;
      renderStrategyCards();
      loadStrategyLab();
      loadStrategyWarRoom();
      loadStrategyDoctor();
    });
  });
}

async function loadStrategyRobotProfiles() {
  const price = state.lastPrice || (state.candles[state.candles.length - 1]?.close || 0);
  try {
    $("robotProfileSummary").textContent = "正在核对机器人研究档案";
    const data = await api(`/api/strategy/robot-profiles?symbol=${encodeURIComponent(state.symbol)}&price=${encodeURIComponent(price)}`);
    renderStrategyRobotProfiles(data);
    return data;
  } catch (error) {
    $("robotProfileSummary").textContent = `机器人研究档案离线：${error.message}`;
    return null;
  }
}

async function loadBotScheduler() {
  const price = state.lastPrice || (state.candles[state.candles.length - 1]?.close || 0);
  try {
    $("botSchedulerSummary").textContent = "正在核对研究角色";
    const data = await api(`/api/bot/scheduler?symbol=${encodeURIComponent(state.symbol)}&price=${encodeURIComponent(price)}`);
    state.botScheduler = data;
    $("botSchedulerSummary").textContent = data.summary || "研究角色观察台已更新";
    $("botSchedulerRows").innerHTML = (data.candidates || []).map((row) => `
      <div class="scheduler-row evidence-neutral">
        <span><strong>${escapeHtml(row.name || "研究机器人")}</strong><em>${escapeHtml(row.family || "研究类型")}</em></span>
        <span class="flat">${row.research_role === "RESEARCH_PRIMARY" ? "研究主观察" : "研究观察"}</span>
        <span class="flat">${number(row.score, 1)}</span>
        <span class="flat" data-raw-status="${escapeHtml(row.raw_status || row.status || "UNKNOWN")}">研究状态</span>
        <span>
          <button data-bot-owner="${escapeHtml(row.id)}" ${row.research_role === "RESEARCH_PRIMARY" ? "disabled" : ""}>设为研究主观察</button>
          <em>${escapeHtml(row.reason || "研究说明待核验")}</em>
        </span>
      </div>
    `).join("");
    $("botSchedulerConflicts").innerHTML = (data.conflicts || []).map((row) => `
      <div class="scheduler-conflict flat">${escapeHtml(row.message || "研究冲突待核验")}</div>
    `).join("");
    document.querySelectorAll("[data-bot-owner]").forEach((button) => {
      button.addEventListener("click", () => assignBotOwner(button.dataset.botOwner));
    });
  } catch (error) {
    $("botSchedulerSummary").textContent = `研究角色观察台离线：${error.message}`;
  }
}

async function assignBotOwner(botId) {
  if (!botId) return;
  try {
    $("botSchedulerSummary").textContent = "记录研究主观察角色";
    const data = await apiMutation(`/api/bot/assign?symbol=${encodeURIComponent(state.symbol)}&botId=${encodeURIComponent(botId)}&mode=research`);
    state.botScheduler = data.scheduler;
    await loadBotCenter();
    await loadBotScheduler();
  } catch (error) {
    $("botSchedulerSummary").textContent = `记录研究角色失败：${error.message}`;
  }
}

async function releaseBotOwner() {
  try {
    $("botSchedulerSummary").textContent = "释放研究角色标签";
    await apiMutation(`/api/bot/release?symbol=${encodeURIComponent(state.symbol)}`);
    await loadBotCenter();
    await loadBotScheduler();
  } catch (error) {
    $("botSchedulerSummary").textContent = `释放研究角色失败：${error.message}`;
  }
}

function riskInputAsPct(kind) {
  const price = state.lastPrice || (state.candles[state.candles.length - 1]?.close || 0);
  const value = Number(kind === "take" ? $("takeProfitInput").value : $("stopLossInput").value);
  if ($("riskValueMode").value === "PCT") {
    return Number.isFinite(value) && value >= 0 ? value : kind === "take" ? 2.4 : 1.2;
  }
  if (!Number.isFinite(value) || value <= 0) return kind === "take" ? 2.4 : 1.2;
  if (!price) return kind === "take" ? 2.4 : 1.2;
  return kind === "take" ? Math.max(0, (value / price - 1) * 100) : Math.max(0, (1 - value / price) * 100);
}

function renderEvidenceAttributionSpine() {
  const evidence = evidenceAttributionSpinePresentation({
    frozenSnapshot: state.internalBacktestReturnQuality || {},
    // The attribution contract verifies the dashboard itself, while the
    // control-center response carries it under forward_validation.
    forwardDashboard: state.platformControl?.forward_validation?.incremental_observation || {},
    strategySnapshot: state.strategyResearchEvidence || {},
    currentStrategyId: $("strategySelect")?.value || "",
  });
  const verifiedHashText = (value) => (
    typeof value === "string" && /^[a-f0-9]{64}$/.test(value) ? value : "未核验"
  );
  const title = [
    evidence.rawFrozenCandidateHash ? `冻结组合候选 ${evidence.rawFrozenCandidateHash}` : "",
    evidence.rawForwardCandidateHash ? `自然前向候选 ${evidence.rawForwardCandidateHash}` : "",
    evidence.rawHypothesisHash ? `事前假设 ${evidence.rawHypothesisHash}` : "",
  ].filter(Boolean).join("\n") || "证据归属未核验";
  [
    {
      spine: "internalBacktestAttributionSpine",
      frozen: "internalBacktestFrozenCandidate",
      forward: "internalBacktestCurrentForwardCandidate",
      relation: "internalBacktestCandidateRelation",
      strategy: "internalBacktestStrategyAttribution",
    },
    {
      spine: "platformEvidenceAttributionSpine",
      frozen: "platformFrozenCandidateAttribution",
      forward: "platformForwardCandidateAttribution",
      relation: "platformCandidateAttributionRelation",
      strategy: "platformStrategyAttribution",
    },
  ].forEach((target) => {
    const spine = $(target.spine);
    if (!spine) return;
    spine.dataset.relationStatus = evidence.relationStatus;
    spine.dataset.frozenCandidateHash = evidence.rawFrozenCandidateHash || "";
    spine.dataset.forwardCandidateHash = evidence.rawForwardCandidateHash || "";
    spine.dataset.hypothesisHash = evidence.rawHypothesisHash || "";
    spine.title = title;
    if ($(target.frozen)) $(target.frozen).textContent = evidence.frozenCandidateText;
    if ($(target.forward)) $(target.forward).textContent = evidence.forwardCandidateText;
    if ($(target.relation)) $(target.relation).textContent = evidence.relationText;
    if ($(target.strategy)) $(target.strategy).textContent = evidence.strategyAttributionText;
  });
  [
    ["platformFrozenCandidateHash", evidence.rawFrozenCandidateHash],
    ["platformForwardCandidateHash", evidence.rawForwardCandidateHash],
    ["platformHypothesisHash", evidence.rawHypothesisHash],
  ].forEach(([id, value]) => {
    const node = $(id);
    if (node) node.textContent = verifiedHashText(value);
  });
  return evidence;
}

function renderInternalBacktestReturnQuality(payload = {}) {
  const evidence = evidenceInternalBacktestReturnQualityPresentation(payload);
  const boundary = $("internalBacktestPackBoundary");
  if (boundary) {
    boundary.dataset.connectionStatus = evidence.connectionStatus;
    boundary.dataset.packSchema = evidence.rawPackSchema;
    boundary.dataset.qualitySchema = evidence.rawQualitySchema;
    boundary.dataset.sourceMode = evidence.sourceMode;
  }
  const status = $("internalBacktestQualityStatus");
  if (status) {
    status.textContent = evidence.statusText;
    status.dataset.rawQualityStatus = evidence.qualityState;
    status.title = `原始包状态 ${evidence.rawPackStatus} · 原始晋级状态 ${evidence.rawPromotionStatus}`;
  }
  if ($("internalBacktestQualityBoundary")) $("internalBacktestQualityBoundary").textContent = evidence.detailText;
  const maturityCue = $("internalBacktestMaturityCue");
  if (maturityCue) {
    maturityCue.dataset.rawStatus = evidence.rawForwardMaturityStatus;
    maturityCue.title = `原始自然前向状态 ${evidence.rawForwardStatus} · 原始成熟度 ${evidence.rawForwardMaturityStatus}`;
  }
  if ($("internalBacktestMaturityText")) {
    $("internalBacktestMaturityText").textContent = evidence.maturityCueText;
  }
  if ($("internalBacktestQualityReturns")) $("internalBacktestQualityReturns").textContent = evidence.returnsText;
  if ($("internalBacktestQualityCosts")) $("internalBacktestQualityCosts").textContent = evidence.costText;
  if ($("internalBacktestQualityRisk")) $("internalBacktestQualityRisk").textContent = evidence.riskText;
  if ($("internalBacktestQualitySample")) $("internalBacktestQualitySample").textContent = evidence.sampleText;
  const stageDetails = $("internalBacktestQualityStages");
  if (stageDetails) stageDetails.dataset.connectionStatus = evidence.connectionStatus;
  const renderStage = (prefix, text, detail, rawStatus, rawBenchmarkStatus, rawClaimStatus) => {
    const value = $(prefix);
    if (value) {
      value.textContent = text;
      value.dataset.rawStatus = rawStatus;
      value.title = `原始阶段 ${rawStatus} · 基准超额 ${rawBenchmarkStatus} · 统计主张 ${rawClaimStatus}`;
    }
    const detailNode = $(`${prefix}Detail`);
    if (detailNode) detailNode.textContent = detail;
  };
  renderStage(
    "internalBacktestQualityValidation",
    evidence.validationStageText,
    evidence.validationStageDetailText,
    evidence.validationStageRawStatus,
    evidence.validationStageRawBenchmarkStatus,
    evidence.validationStageRawClaimStatus,
  );
  renderStage(
    "internalBacktestQualityTest",
    evidence.testStageText,
    evidence.testStageDetailText,
    evidence.testStageRawStatus,
    evidence.testStageRawBenchmarkStatus,
    evidence.testStageRawClaimStatus,
  );
  const forwardDetails = $("internalBacktestForwardEvidence");
  if (forwardDetails) forwardDetails.dataset.connectionStatus = evidence.connectionStatus;
  const forwardStatus = $("internalBacktestForwardStatus");
  if (forwardStatus) {
    forwardStatus.textContent = evidence.forwardStatusText;
    forwardStatus.dataset.rawStatus = evidence.rawForwardStatus;
    forwardStatus.title = `原始前向状态 ${evidence.rawForwardStatus} · 来源完整性 ${evidence.rawForwardIntegrityStatus} · 审计 ${evidence.rawForwardAuditStatus}`;
  }
  const forwardMaturity = $("internalBacktestForwardMaturity");
  if (forwardMaturity) {
    forwardMaturity.textContent = evidence.forwardMaturityText;
    forwardMaturity.dataset.rawStatus = evidence.rawForwardMaturityStatus;
    forwardMaturity.title = `原始成熟度 ${evidence.rawForwardMaturityStatus}`;
  }
  if ($("internalBacktestForwardBoundary")) {
    $("internalBacktestForwardBoundary").textContent = evidence.forwardBoundaryText;
  }
  if ($("internalBacktestForwardSource")) {
    $("internalBacktestForwardSource").textContent = evidence.forwardSourceText;
  }
  const evidenceCue = $("internalBacktestEvidenceCue");
  if (evidenceCue) evidenceCue.dataset.evidenceGapKind = evidence.evidenceGapKind;
  const evidenceGap = $("internalBacktestQualityFailures");
  if (evidenceGap) evidenceGap.textContent = evidence.evidenceGapText || evidence.failureText;
  const source = $("internalBacktestQualitySource");
  if (source) {
    source.textContent = evidence.verified && evidence.generatedAt
      ? `${evidence.sourceText} · 冻结于 ${platformTruthTimeText(evidence.generatedAt)}`
      : evidence.sourceText;
    source.title = evidence.verified
      ? `Pack ${evidence.packHash}\nEvidence ${evidence.evidenceHash}`
      : "固定来源缺失或合同校验失败";
  }
  renderEvidenceAttributionSpine();
}

async function loadInternalBacktestReturnQuality() {
  if (state.internalBacktestReturnQualityLoaded) return;
  state.internalBacktestReturnQualityLoaded = true;
  try {
    const response = await fetch("/api/portfolio/backtest-return-quality", { cache: "no-store" });
    const payload = await response.json();
    state.internalBacktestReturnQuality = response.ok && payload && typeof payload === "object" ? payload : null;
  } catch (_error) {
    state.internalBacktestReturnQuality = null;
  }
  renderInternalBacktestReturnQuality(state.internalBacktestReturnQuality || {});
}

function renderBacktestMetrics(current, data = {}) {
  const evidence = evidenceBacktestPresentation(current, data);
  const ledger = $("backtestEvidenceLedger");
  if (ledger) ledger.dataset.resultStatus = evidence.hasResult ? "PRESENT" : "UNKNOWN";
  if ($("btEvidenceBoundary")) $("btEvidenceBoundary").textContent = evidence.boundaryText;
  $("btReturn").textContent = evidence.returnText;
  $("btReturn").className = "evidence-metric-value";
  $("btReturnBasis").textContent = evidence.returnBasisText;
  $("btBenchmark").textContent = evidence.benchmarkText;
  $("btExcess").textContent = evidence.excessText;
  $("btCosts").textContent = evidence.costsText;
  $("btDrawdown").textContent = evidence.drawdownText;
  $("btDrawdown").className = "evidence-metric-value";
  $("btSample").textContent = evidence.sampleText;
  $("btTrades").textContent = evidence.tradesText;
  $("btTemporal").textContent = evidence.temporalText;
  $("btTemporal").dataset.rawStatus = evidence.rawTemporalStatus;
  $("btTemporal").title = `原始时间证据状态 ${evidence.rawTemporalStatus}`;
  $("btAnnual").textContent = evidence.annualizedText;
  $("btAnnual").className = "evidence-metric-value";
  $("btWinRate").textContent = evidence.winRateText;
  $("btSharpe").textContent = evidence.sharpeText;
  if (!current?.ok) {
    $("backtestSummary").textContent = `${current?.error || "开发回测结果不可用"} · 模拟未授权 · 实盘永久硬锁`;
    $("btOptimizerNotes").textContent = "开发回测结果不可用；参数解释尚未形成。";
  }
  return evidence;
}

function backtestPercentText(value, digits = 1) {
  if (value === null || value === undefined || value === "" || typeof value === "boolean") return "未提供";
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return "未提供";
  return `${parsed > 0 ? "+" : ""}${parsed.toFixed(digits)}%`;
}

function planLabel(row) {
  if (!row?.ok) return "--";
  return `${number(row.position_pct, 0)}% position / TP ${number(row.take_profit_pct, 1)} / SL ${number(row.stop_loss_pct, 1)}`;
}

function planMeta(row) {
  if (!row?.ok) return "等待候选比较";
  return `${backtestPercentText(row.total_return_pct)} / 回撤 ${backtestPercentText(row.max_drawdown_pct)} / ${row.risk_label || "--"}`;
}

function renderBacktestOptimizer(data) {
  const optimizer = data.optimizer || {};
  const best = optimizer.best || {};
  const safest = optimizer.safest || {};
  const highest = optimizer.highest_return || {};
  $("btBestPlan").textContent = planLabel(best);
  $("btBestMeta").textContent = planMeta(best);
  $("btSafePlan").textContent = planLabel(safest);
  $("btSafeMeta").textContent = planMeta(safest);
  $("btReturnPlan").textContent = planLabel(highest);
  $("btReturnMeta").textContent = highest?.ok
    ? `${planMeta(highest)} / 选择偏差未校正`
    : "等待候选比较 · 选择偏差未校正";
  const evidence = evidenceBacktestPresentation(data.current || {}, data);
  const source = data.source ? `来源 ${data.source} / ${evidence.sampleText}` : "";
  const notes = optimizer.notes || [];
  $("btOptimizerNotes").textContent = [source, ...notes, data.data_warning || ""].filter(Boolean).join(" / ") || "等待开发期候选比较证据；收益选择偏差未校正";
  $("btSegmentRows").innerHTML = (data.segments || []).map((row) => `
    <div class="segment-row">
      <span>${escapeHtml(row.name || "--")}</span>
      <span>${escapeHtml(row.start || "--")}~${escapeHtml(row.end || "--")}</span>
      <span class="evidence-metric-value">${backtestPercentText(row.return_pct)}</span>
      <span>${backtestPercentText(row.drawdown_pct)}</span>
      <span>${number(row.sharpe, 2)}</span>
      ${evidenceResearchStatusBadge(row.status, "时间切片待核验")}
    </div>
  `).join("") || `<div class="segment-row empty"><span>Waiting</span><span>No segment data</span><span>--</span><span>--</span><span>--</span><span>--</span></div>`;
  renderBacktestQuality(data);
}

function renderBacktestRobustness(data = {}) {
  const target = $("backtestRobustnessLedger");
  if (!target) return;
  const evidence = evidenceBacktestRobustnessPresentation(data);
  target.dataset.resultStatus = evidence.valid ? "PRESENT" : "UNKNOWN";
  target.dataset.rawTemporalStatus = evidence.rawTemporalStatus;
  target.dataset.rawFoldStatus = evidence.rawFoldStatus;
  target.dataset.rawCostStatus = evidence.rawCostStatus;
  target.dataset.rawCausalStatus = evidence.rawCausalStatus;
  target.title = evidence.permissionText;
  if ($("btRobustnessMode")) $("btRobustnessMode").textContent = evidence.modeText;
  if ($("btRobustnessTemporal")) $("btRobustnessTemporal").textContent = evidence.temporalText;
  if ($("btRobustnessFolds")) $("btRobustnessFolds").textContent = evidence.foldsText;
  if ($("btRobustnessCosts")) $("btRobustnessCosts").textContent = evidence.costText;
  if ($("btRobustnessParameter")) $("btRobustnessParameter").textContent = evidence.parameterText;
  if ($("btRiskSurfaceStatus")) $("btRiskSurfaceStatus").textContent = evidence.surfaceStatusText;
  if ($("btRiskSurfaceCoverage")) $("btRiskSurfaceCoverage").textContent = evidence.surfaceCoverageText;
  if ($("btRiskSurfaceNeighborhood")) $("btRiskSurfaceNeighborhood").textContent = evidence.surfaceNeighborhoodText;
  if ($("btRobustnessCausal")) $("btRobustnessCausal").textContent = evidence.causalText;
  if ($("btRobustnessFailures")) $("btRobustnessFailures").textContent = evidence.failureText;
  const rawStatuses = [
    evidence.rawTemporalStatus,
    evidence.rawFoldStatus,
    evidence.rawCostStatus,
    evidence.rawSurfaceStatus,
    evidence.rawCausalStatus,
  ];
  target.querySelectorAll(".backtest-robustness-item").forEach((item, index) => {
    if (index > 0 && rawStatuses[index - 1]) item.dataset.rawStatus = rawStatuses[index - 1];
  });
}

function renderBacktestQuality(data) {
  renderBacktestRobustness(data);
  const gateTarget = $("backtestGateRows");
  const reproTarget = $("backtestReproRows");
  if (gateTarget) {
    const acceptance = data.acceptance || {};
    const gateLabels = {
      sample_size: "样本数量",
      has_trades: "闭合交易",
      drawdown: "最大回撤",
      dataset_integrity: "数据完整性",
      reproducible: "运行可复现",
      causal_execution: "因果成交",
      optimizer: "参数候选",
      data_warning: "数据警告",
    };
    gateTarget.innerHTML = `
      <div class="backtest-gate-summary">
        ${evidenceResearchStatusBadge(acceptance.status, "研究门槛待核验")}
        <strong>${number(acceptance.score, 1)}/100</strong>
        <em>${escapeHtml(acceptance.summary || "Run backtest to generate acceptance gates.")}</em>
      </div>
      ${(acceptance.checks || []).map((row) => `
        <div class="backtest-gate-row">
          <span>${escapeHtml(gateLabels[row.name] || row.name || "--")}</span>
          ${evidenceResearchStatusBadge(row.status)}
          <span>${escapeHtml(row.detail || "--")}</span>
        </div>
      `).join("")}
    `;
  }
  if (reproTarget) {
    const repro = data.reproducibility || {};
    const manifest = data.dataset_manifest || repro.dataset_manifest || {};
    const artifact = data.pipeline_run?.backtest_artifact || {};
    const evidence = evidenceBacktestPresentation(data.current || {}, data);
    reproTarget.innerHTML = `
      <div><span>运行哈希</span><strong>${escapeHtml(repro.run_hash || "--")}</strong></div>
      <div><span>数据哈希</span><strong>${escapeHtml(repro.data_hash || "--")}</strong></div>
      <div><span>参数哈希</span><strong>${escapeHtml(repro.param_hash || "--")}</strong></div>
      <div><span>数据清单</span><strong>${evidenceResearchStatusBadge(manifest.status, "数据清单待核验")} / ${escapeHtml(manifest.hash_scope || "--")}</strong></div>
      <div><span>来源与样本</span><strong>${escapeHtml(`${repro.source || "来源未提供"} / ${evidence.sampleText}`)}</strong></div>
      <div><span>样本区间</span><strong>${escapeHtml(`${repro.data_first || "--"} ~ ${repro.data_last || "--"}`)}</strong></div>
      <div><span>成交模型</span><strong>${escapeHtml(repro.execution_model || data.execution_model || "--")}</strong></div>
      <div><span>成本假设</span><strong>${escapeHtml(evidence.costsText)}</strong></div>
      <div><span>审计工件</span><strong>${artifact.artifact_id ? `${evidenceResearchStatusBadge(artifact.integrity_status, "审计工件待核验")} / ${escapeHtml(artifact.artifact_id)}` : "--"}</strong></div>
    `;
  }
}

async function loadBacktest(options = {}) {
  const record = options?.record === true;
  const strategy = $("strategySelect").value || "dual_ma";
  const positionPct = $("positionInput").value || 35;
  const takeProfitPct = riskInputAsPct("take");
  const stopLossPct = riskInputAsPct("stop");
  const leverage = Number($("leverageInput").value || 1);
  const directionMode = $("directionMode").value || "LONG_ONLY";
  if (leverage !== VALIDATED_STRATEGY_LEVERAGE) {
    $("backtestSummary").textContent = "当前因果回测仅支持 1x；杠杆模型尚未完成验证";
    return;
  }
  if (directionMode !== "LONG_ONLY") {
    $("backtestSummary").textContent = "当前因果回测仅支持只做多；做空需要独立成交与风控模型";
    return;
  }
  if ($("riskSource").value !== "MANUAL" || $("riskValueMode").value !== "PCT") {
    $("backtestSummary").textContent = "请先冻结为手动百分比止盈止损，再运行可绑定回测";
    return;
  }
  if ($("trailingTakeEnabled").checked || $("trailingStopEnabled").checked) {
    $("backtestSummary").textContent = "移动止盈止损尚未纳入当前回测模型，请先关闭";
    return;
  }
  if ($("strategyOrderType").value !== "CURRENT" || $("marginMode").value !== "CROSS") {
    $("backtestSummary").textContent = "当前验证档仅绑定现价委托与全仓 1x 模拟";
    return;
  }
  try {
    if (record && state.platformControl?.read_only) {
      $("backtestSummary").textContent = "当前实例只读：可以预览，不能冻结流水线记录";
      return;
    }
    $("backtestSummary").textContent = record ? "正在冻结因果回测" : "正在预览因果回测";
    const query = `symbol=${encodeURIComponent(state.symbol)}&strategy=${encodeURIComponent(strategy)}&positionPct=${encodeURIComponent(positionPct)}&takeProfitPct=${encodeURIComponent(takeProfitPct)}&stopLossPct=${encodeURIComponent(stopLossPct)}&leverage=${encodeURIComponent(leverage)}&directionMode=${encodeURIComponent(directionMode)}&limit=1800`;
    const data = record
      ? await apiMutation(`/api/strategy/backtest?${query}`)
      : await api(`/api/strategy/backtest/preview?${query}`);
    state.strategyBacktest = data;
    renderBacktestOptimizer(data);
    const backtestEvidence = renderBacktestMetrics(data.current, data);
    const rows = data.candidates || [];
    const gridCount = Number(data.optimizer?.grid_count);
    const gridText = Number.isInteger(gridCount) && gridCount >= 0
      ? `参数组 ${gridCount}`
      : rows.length
        ? `参数组 ${rows.length}`
        : "参数组未提供";
    $("backtestSummary").dataset.rawTemporalStatus = backtestEvidence.rawTemporalStatus;
    $("backtestSummary").title = `原始样本外状态 ${backtestEvidence.rawTemporalStatus}`;
    if (backtestEvidence.hasResult) {
      $("backtestSummary").textContent = `${record ? "研究快照已冻结" : "开发预览"} · ${data.current?.strategy?.name || strategy} · ${backtestEvidence.temporalText} · ${gridText} · 不授予模拟或实盘权限`;
    }
    $("backtestRows").innerHTML = rows.map((row, index) => `
      <div class="backtest-row evidence-neutral" data-bt-position="${row.position_pct}" data-bt-tp="${row.take_profit_pct}" data-bt-sl="${row.stop_loss_pct}" data-raw-score="${escapeHtml(row.score)}" title="开发期参数比较；点击只复制到研究表单，不运行、不授权">
        <span>${index + 1}</span>
        <span>${number(row.position_pct, 0)}%</span>
        <span>${number(row.take_profit_pct, 1)}</span>
        <span>${number(row.stop_loss_pct, 1)}</span>
        <span class="evidence-metric-value">${backtestPercentText(row.total_return_pct)}</span>
        <span>${backtestPercentText(row.max_drawdown_pct)}</span>
        <span class="flat" data-raw-score="${escapeHtml(row.score)}">${number(row.score, 1)}</span>
      </div>
    `).join("");
    document.querySelectorAll(".backtest-row").forEach((row) => {
      row.addEventListener("click", () => {
        $("positionInput").value = row.dataset.btPosition || "35";
        $("riskSource").value = "MANUAL";
        $("riskValueMode").value = "PCT";
        $("takeProfitInput").value = row.dataset.btTp || "2.4";
        $("stopLossInput").value = row.dataset.btSl || "1.2";
        syncRiskPlaceholders();
        renderStrategyCommandStrip();
        loadStrategyWarRoom();
        loadStrategyDoctor();
        $("strategyAnalysis").textContent = "研究参数已复制到表单 · 未运行 · 未授权";
      });
    });
  } catch (error) {
    renderBacktestMetrics({ ok: false, error: `回测失败：${error.message}` }, {});
  }
}

async function loadApiConfig() {
  try {
    const data = await api("/api/config/api");
    const config = data.config || {};
    const saved = config.saved || {};
    $("apiKeyEnv").value = saved.api_key_env || "OKX_API_KEY";
    $("secretEnv").value = saved.secret_env || "OKX_SECRET";
    $("passwordEnv").value = saved.password_env || "OKX_PASSWORD";
    const env = config.env_status || {};
    const mapped = config.mapped_env_status || {};
    const privateRead = config.private_read || {};
    const ready = Boolean((mapped.api_key && mapped.secret && mapped.password) || (env.OKX_API_KEY && env.OKX_SECRET && env.OKX_PASSWORD));
    const privateReady = privateRead.status === "READY";
    $("apiKeyState").textContent = privateReady ? "READ OK" : ready ? "CHECKED" : privateRead.status === "MISSING" ? "缺少Passphrase" : "UNCHECKED";
    $("apiKeyState").className = privateReady ? "up" : ready ? "flat" : "flat";
    $("apiKeyState").title = privateRead.message || config.message || "";
    $("liveAuthState").textContent = config.live_enabled ? "ENABLED" : "LOCKED";
    $("liveAuthState").className = config.live_enabled ? "down" : "flat";
  } catch (error) {
    $("apiKeyState").textContent = "Offline";
  }
}

async function loadProfile() {
  try {
    const data = await api("/api/profile");
    state.profile = data.profile;
    state.indicators = { ...state.indicators, ...(state.profile.indicators || {}) };
    renderProfile();
    syncIndicatorButtons();
    drawChart();
  } catch (error) {
    $("accountSummary").textContent = `Account offline: ${error.message}`;
  }
}

function renderProfile() {
  const profile = state.profile;
  if (!profile) return;
  if (!$("assetRows") && !$("accountSummary") && !$("transferRows") && !$("guardianState")) {
    applySettings(profile.settings || {});
    return;
  }
  const assets = profile.assets || {};
  const assetRows = Object.entries(assets).map(([asset, values]) => `
    <div class="asset-row">
      <span>${asset}</span>
      <span>${number(values.wallet || 0, asset === "USDT" ? 2 : 6)}</span>
      <span>${number(values.trading || 0, asset === "USDT" ? 2 : 6)}</span>
      <span>${number(values.funding || 0, asset === "USDT" ? 2 : 6)}</span>
    </div>
  `).join("");
  if ($("assetRows")) $("assetRows").innerHTML = `
    <div class="asset-row header"><span>Asset</span><span>Wallet</span><span>Trading</span><span>Funding</span></div>
    ${assetRows}
  `;
  if ($("accountSummary")) $("accountSummary").textContent = `${profile.unread_notifications || 0} unread notifications`;

  const transfers = profile.transfers || [];
  if ($("transferRows")) $("transferRows").innerHTML = transfers.slice().reverse().map((transfer) => `
    <div class="transfer-row">
      <span>${timeText(transfer.time)}</span>
      <span>${transfer.asset}</span>
      <span>${transfer.source} -> ${transfer.target}</span>
      <span>${number(transfer.amount, transfer.asset === "USDT" ? 2 : 6)}</span>
      <span class="${transfer.status === "DONE" ? "up" : "down"}">${transfer.status}</span>
    </div>
  `).join("");

  const guardian = profile.guardian || {};
  if ($("guardianState")) {
    $("guardianState").textContent = guardian.status || "STOPPED";
    $("guardianState").className = guardian.status === "RUNNING" ? "up" : ["ERROR", "PAUSED"].includes(guardian.status) ? "down" : "flat";
  }
  if ($("guardianHeartbeat")) $("guardianHeartbeat").textContent = guardian.heartbeat_ms ? timeText(guardian.heartbeat_ms) : "--";
  if ($("guardianCycles")) $("guardianCycles").textContent = String(guardian.cycles || 0);
  if ($("guardianLastPrice")) $("guardianLastPrice").textContent = guardian.last_price ? number(guardian.last_price, Number(guardian.last_price) > 100 ? 1 : 4) : "--";
  if ($("guardianLastAction")) {
    $("guardianLastAction").textContent = guardian.last_action || "--";
    $("guardianLastAction").className = ["BUY", "ADD"].includes(guardian.last_action) ? "up" : ["SELL", "EXIT"].includes(guardian.last_action) ? "down" : "flat";
  }
  if ($("guardianLastEquity")) $("guardianLastEquity").textContent = guardian.last_equity ? `${number(guardian.last_equity, 2)} USDT` : "--";
  if ($("guardianLastError")) {
    $("guardianLastError").textContent = guardian.last_error || "--";
    $("guardianLastError").className = guardian.last_error ? "down" : "flat";
  }
  if ($("guardianMessage")) $("guardianMessage").textContent = guardian.message || "Strategy guardian is not running";

  renderNotifications(profile.notifications || []);
  applySettings(profile.settings || {});
}

function applySettings(settings) {
  const theme = { warm: "dark", midnight: "blue", contrast: "light" }[settings.theme] || settings.theme || "dark";
  const density = settings.density || "compact";
  const layout = settings.layout || "classic";
  state.layout = layout;
  document.body.classList.remove("theme-warm", "theme-midnight", "theme-contrast");
  document.body.classList.toggle("theme-blue", theme === "blue");
  document.body.classList.toggle("theme-light", theme === "light");
  document.body.classList.toggle("density-standard", density === "standard");
  document.body.classList.toggle("layout-focus", layout === "focus");
  document.body.classList.toggle("layout-analysis", layout === "analysis");
  if ($("themeSelect")) $("themeSelect").value = theme;
  if ($("densitySelect")) $("densitySelect").value = density;
  if ($("refreshSeconds")) $("refreshSeconds").value = settings.refresh_seconds || 8;
  if ($("startModule")) $("startModule").value = settings.start_module || ".ticker-header";
  if ($("layoutPreset")) $("layoutPreset").value = layout;
}

function renderNotifications(notifications) {
  if (!$("notificationRows")) return;
  $("notificationRows").innerHTML = notifications.slice().reverse().map((item) => `
    <div class="notification-row ${item.read ? "" : "active"}">
      <span>${timeText(item.time)}</span>
      <span class="${item.level === "WARN" ? "down" : item.level === "INFO" ? "up" : "flat"}">${item.level}</span>
      <span><span class="notification-title">${item.title}</span><span class="notification-body">${item.body}</span></span>
    </div>
  `).join("");
}

async function transferAsset() {
  const data = await apiMutation(`/api/profile/transfer?asset=${encodeURIComponent($("transferAsset").value)}&source=${encodeURIComponent($("transferSource").value)}&target=${encodeURIComponent($("transferTarget").value)}&amount=${encodeURIComponent($("transferAmount").value || "0")}`);
  state.profile = data.profile;
  renderProfile();
}

async function setGuardian(enabled) {
  const data = await apiMutation(`/api/profile/guardian?enabled=${enabled ? "true" : "false"}`);
  state.profile = data.profile;
  renderProfile();
}

async function guardianHeartbeat() {
  if (!state.profile?.guardian?.enabled) return;
  const data = await apiMutation("/api/profile/guardian/heartbeat");
  state.profile = data.profile;
  if (data.cycle?.paper) {
    state.paper = data.cycle.paper;
    renderPaper();
  }
  renderProfile();
}

async function guardianEmergencyStop() {
  const price = state.lastPrice || (state.candles[state.candles.length - 1]?.close || 0);
  const data = await apiMutation(`/api/profile/guardian/emergency-stop?price=${encodeURIComponent(price)}&reason=${encodeURIComponent("手动一键急停")}`);
  state.profile = data.profile;
  state.paper = data.paper;
  renderProfile();
  renderPaper();
}

async function markNotificationsRead() {
  const data = await apiMutation("/api/profile/notifications/read");
  state.profile = data.profile;
  renderProfile();
}

function syncIndicatorButtons() {
  $("toggleMA").classList.toggle("active", Boolean(state.indicators.ma));
  $("toggleBollinger").classList.toggle("active", Boolean(state.indicators.bollinger));
  $("toggleVolume").classList.toggle("active", Boolean(state.indicators.volume));
  $("toggleSignals").classList.toggle("active", Boolean(state.indicators.signals));
  $("toggleVolumeProfile")?.classList.toggle("active", Boolean(state.indicators.volumeProfile));
  $("autoChartMarks")?.classList.toggle("active", Boolean(state.indicators.autoMarks));
}

async function saveIndicators() {
  syncIndicatorButtons();
  drawChart();
  try {
    const data = await apiMutation(`/api/profile/indicators?ma=${state.indicators.ma}&bollinger=${state.indicators.bollinger}&volume=${state.indicators.volume}&signals=${state.indicators.signals}`);
    state.profile = data.profile;
    renderProfile();
  } catch (error) {
    // Local toggles still work when persistence is temporarily unavailable.
  }
}

function focusModule(selector, autoView = true) {
  if (autoView) setInterfaceView(viewForSelector(selector));
  const target = document.querySelector(selector);
  if (!target) return;
  target.scrollIntoView({ behavior: "smooth", block: "start" });
  syncWorkspaceNav(selector);
  document.querySelectorAll("#moduleNav button").forEach((button) => {
    button.classList.toggle("active", button.dataset.focus === selector);
  });
}

async function saveTerminalSettings() {
  const theme = $("themeSelect").value;
  const density = $("densitySelect").value;
  const refreshSeconds = $("refreshSeconds").value || 8;
  const startModule = $("startModule").value;
  const layout = $("layoutPreset").value;
  const data = await apiMutation(`/api/profile/settings?theme=${encodeURIComponent(theme)}&density=${encodeURIComponent(density)}&refreshSeconds=${encodeURIComponent(refreshSeconds)}&startModule=${encodeURIComponent(startModule)}&layout=${encodeURIComponent(layout)}`);
  state.profile = data.profile;
  renderProfile();
}

async function prepareDaemon() {
  const data = await apiMutation("/api/daemon/prepare");
  state.profile = data.profile;
  $("daemonState").textContent = data.message || "prepared";
  renderProfile();
}

async function loadLedger() {
  try {
    const data = await api("/api/ledger?limit=80");
    const rows = data.ledger || [];
    $("ledgerSummary").textContent = `${rows.length} rows`;
    $("ledgerRows").innerHTML = rows.slice().reverse().map((row) => `
      <div class="ledger-row">
        <span>${timeText(row.time)}</span>
        <span>${row.type || "--"}</span>
        <span>${JSON.stringify(row).slice(0, 180)}</span>
      </div>
    `).join("");
  } catch (error) {
    $("ledgerSummary").textContent = "Offline";
  }
}

async function exportOrders() {
  const data = await apiMutation("/api/export/orders");
  $("exportState").textContent = `${data.export.rows} rows`;
  $("exportPath").textContent = data.export.path;
  await loadLedger();
}

async function exportLedger() {
  const data = await apiMutation("/api/export/ledger");
  $("exportState").textContent = `${data.export.rows} rows`;
  $("exportPath").textContent = data.export.path;
  await loadLedger();
}

async function loadStrategyMarketplace() {
  try {
    const data = await api("/api/strategy/marketplace");
    const rows = data.strategies || [];
    $("strategyMarketSummary").textContent = `${rows.filter((row) => row.installed).length}/${rows.length} installed`;
    $("strategyMarketRows").innerHTML = rows.map((row) => `
      <div class="strategy-market-row">
        <div><strong>${row.name}</strong><span>${(row.badges || []).join(" / ")} / v${row.version}</span></div>
        <span class="${row.installed ? "up" : "flat"}">${row.installed ? "Installed" : "Available"}</span>
        <button data-strategy-market="${row.id}" data-installed="${row.installed ? "1" : "0"}">${row.installed ? "Remove" : "Install"}</button>
      </div>
    `).join("");
    document.querySelectorAll("[data-strategy-market]").forEach((button) => {
      button.addEventListener("click", () => toggleStrategyPlugin(button.dataset.strategyMarket, button.dataset.installed === "1"));
    });
  } catch (error) {
    $("strategyMarketSummary").textContent = "Offline";
  }
}

async function toggleStrategyPlugin(id, installed) {
  await apiMutation(`/api/strategy/${installed ? "uninstall" : "install"}?id=${encodeURIComponent(id)}`);
  await loadStrategyMarketplace();
  await loadProfile();
}

function cycleTheme() {
  const order = ["dark", "blue", "light"];
  const current = $("themeSelect").value || "dark";
  const next = order[(order.indexOf(current) + 1) % order.length];
  $("themeSelect").value = next;
  saveTerminalSettings();
}

function handleShortcut(event) {
  if (event.target && ["INPUT", "SELECT", "TEXTAREA"].includes(event.target.tagName)) return;
  const key = event.key.toUpperCase();
  const map = {
    "1": ".ticker-header",
    "2": ".strategy-desk",
    "3": ".orders-panel",
    "4": ".account-center-grid",
    "5": ".history-panel",
    "6": ".system-grid",
  };
  if (map[key]) {
    focusModule(map[key]);
  }
  if (key === "T") {
    cycleTheme();
  }
}

async function saveApiConfig() {
  const data = await apiMutation(`/api/config/api/save?exchange=okx&mode=paper&apiKeyEnv=${encodeURIComponent($("apiKeyEnv").value)}&secretEnv=${encodeURIComponent($("secretEnv").value)}&passwordEnv=${encodeURIComponent($("passwordEnv").value)}`);
  const config = data.config || {};
  const env = config.env_status || {};
  const mapped = config.mapped_env_status || {};
  const privateRead = config.private_read || {};
  const ready = Boolean((mapped.api_key && mapped.secret && mapped.password) || (env.OKX_API_KEY && env.OKX_SECRET && env.OKX_PASSWORD));
  const privateReady = privateRead.status === "READY";
  $("apiKeyState").textContent = privateReady ? "READ OK" : ready ? "CHECKED" : "SAVED";
  $("apiKeyState").className = privateReady ? "up" : ready ? "flat" : "flat";
  $("apiKeyState").title = privateRead.message || config.message || "";
  await loadFullConfig();
}

function renderHistory(rows) {
  const list = rows.slice(-80).reverse();
  $("historySummary").textContent = `${rows.length} 条 / ${rows[0]?.date || "--"} 至 ${rows[rows.length - 1]?.date || "--"}`;
  $("historyRows").innerHTML = list.map((row) => `
    <tr>
      <td>${row.date}</td>
      <td>${number(row.open, 2)}</td>
      <td>${number(row.high, 2)}</td>
      <td>${number(row.low, 2)}</td>
      <td>${number(row.close, 2)}</td>
      <td>${compact(row.volume)}</td>
    </tr>
  `).join("");
}

async function loadHistoryTable() {
  try {
    const data = await api("/api/local/btc-daily?limit=5000");
    renderHistory(data.rows || []);
  } catch (error) {
    $("historySummary").textContent = `本地历史读取失败：${error.message}`;
  }
}

function bindEvents() {
  if (!runtime.interactionGuardBound) {
    runtime.interactionGuardBound = true;
    const markUserInteraction = () => {
      runtime.userInteractionStarted = true;
    };
    document.addEventListener("click", markUserInteraction, true);
    document.addEventListener("keydown", markUserInteraction, true);
  }
  if (!runtime.stockSessionEventsBound) {
    runtime.stockSessionEventsBound = true;
    document.addEventListener("click", (event) => {
      const button = event.target instanceof Element
        ? event.target.closest("#stockSessionTabs button[data-stock-session]")
        : null;
      if (!button) return;
      event.preventDefault();
      selectStockSession(button.dataset.stockSession || "all");
    });
  }
  document.querySelectorAll("[data-interface-view]").forEach((button) => {
    button.addEventListener("click", () => setInterfaceView(button.dataset.interfaceView));
  });
  $("platformRefresh")?.addEventListener("click", () => loadPlatformControlCenter().catch(() => {}));
  $("platformReplayLatest")?.addEventListener("click", () => replayLatestPlatformOrder());
  $("platformValidate")?.addEventListener("click", () => reviewPlatformEvidence().catch((error) => {
    setPlatformBlock("platformStrategyCard", "BLOCK", error.message);
  }));
  $("platformOpenStrategy")?.addEventListener("click", () => {
    setInterfaceView("bot");
    setTimeout(() => focusModule(".strategy-desk", false), 0);
  });
  document.querySelectorAll("[data-desktop-mode]").forEach((button) => {
    button.addEventListener("click", () => setDesktopMode(button.dataset.desktopMode));
  });
  $("quoteSourceSelect")?.addEventListener("change", () => setQuoteSource($("quoteSourceSelect").value));
  $("desktopRefresh")?.addEventListener("click", () => {
    refreshMarketTickers();
    loadFutuStatus(true);
    pollLiveTicker();
    refreshPaper(true);
  });
  $("desktopFutuSetup")?.addEventListener("click", () => {
    window.location.href = "/futu_setup.html";
  });
  $("commandOpen")?.addEventListener("click", () => openCommandPanel());
  $("commandOverlay")?.addEventListener("click", (event) => {
    if (event.target.id === "commandOverlay") closeCommandPanel();
  });
  $("commandInput")?.addEventListener("input", () => {
    state.desktop.commandIndex = 0;
    renderCommandResults();
  });
  $("commandInput")?.addEventListener("keydown", (event) => {
    const rows = state.desktop.commandRows || [];
    if (event.key === "ArrowDown") {
      event.preventDefault();
      state.desktop.commandIndex = rows.length ? (state.desktop.commandIndex + 1) % rows.length : 0;
      renderCommandResults();
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      state.desktop.commandIndex = rows.length ? (state.desktop.commandIndex - 1 + rows.length) % rows.length : 0;
      renderCommandResults();
    }
    if (event.key === "Enter") {
      event.preventDefault();
      runCommand();
    }
    if (event.key === "Escape") {
      event.preventDefault();
      closeCommandPanel();
    }
  });
  $("marketSearch")?.addEventListener("input", renderMarkets);
  window.matchMedia?.("(max-width: 480px)")?.addEventListener?.("change", syncMarketRailDisclosure);
  $("marketSearch")?.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && commitMarketSearch()) event.preventDefault();
    if (event.key === "Escape") {
      event.preventDefault();
      event.currentTarget.value = "";
      runtime.marketListSignature = "";
      renderMarkets();
    }
  });
  $("marketList")?.addEventListener("click", (event) => {
    const row = event.target.closest(".market-row");
    if (row?.dataset?.symbol) selectSymbol(row.dataset.symbol, { focusChart: true });
  });
  $("marketTickerRows")?.addEventListener("click", (event) => {
    const row = event.target.closest(".market-ticker-row");
    if (row?.dataset?.symbol) selectSymbol(row.dataset.symbol, { focusChart: true });
  });
  $("workflowRefreshRadar")?.addEventListener("click", () => {
    renderMarketWorkflowStrip();
    loadTrendCockpit(state.symbol, runtime.symbolVersion).catch(() => {});
    loadAnomalyRadar(false, runtime.symbolVersion, { force: true }).catch(() => {});
    loadAnomalyEvents("", { force: true, limit: 120 }).catch(() => {});
    loadStockSourceControl(state.symbol, runtime.symbolVersion).catch(() => {});
    if (isStockMarket()) loadFutuDeep(true, runtime.symbolVersion).catch(() => {});
  });
  $("workflowOpenEvidence")?.addEventListener("click", () => {
    setInterfaceView("research");
    if (state.selectedAnomaly?.symbol) loadAnomalyDetail(state.selectedAnomaly.symbol, runtime.symbolVersion).catch(() => {});
    setTimeout(() => {
      document.querySelector(".anomaly-workbench, .research-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 0);
  });
  $("workflowAskAi")?.addEventListener("click", () => {
    if (state.selectedAnomaly?.symbol) openAnomalyPromptInAi();
    else openResearchPromptInAi(`请为${state.symbol}生成研究员会议纪要：结合日线波段结构、成交量、关键支撑压力、异动雷达、行业联动和数据质量，分别整理多头论据、空头论据、反证、风险、观察位和后续等待条件。只做研究纪要，不输出实盘指令。`);
  });
  $("stockRows")?.addEventListener("click", (event) => {
    const row = event.target.closest(".stock-row");
    if (row?.dataset?.symbol) selectSymbol(row.dataset.symbol, { focusChart: true });
  });
  $("marketCategoryTabs")?.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      $("marketCategoryTabs")?.querySelectorAll("button").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      state.marketCategory = button.dataset.category;
      renderMarkets();
    });
  });
  $("moduleNav")?.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => focusModule(button.dataset.focus));
  });
  document.querySelectorAll("[data-workspace-focus]").forEach((button) => {
    button.addEventListener("click", () => focusModule(button.dataset.workspaceFocus));
  });
  $("toggleChartMode")?.addEventListener("click", () => {
    state.chartMode = state.chartMode === "candles" ? "line" : "candles";
    $("toggleChartMode").textContent = state.chartMode === "candles" ? "K线" : "分时";
    drawChart();
  });
  $("toggleMA")?.addEventListener("click", () => {
    state.indicators.ma = !state.indicators.ma;
    saveIndicators();
  });
  $("toggleBollinger")?.addEventListener("click", () => {
    state.indicators.bollinger = !state.indicators.bollinger;
    saveIndicators();
  });
  $("toggleVolume")?.addEventListener("click", () => {
    state.indicators.volume = !state.indicators.volume;
    saveIndicators();
  });
  $("toggleSignals")?.addEventListener("click", () => {
    state.indicators.signals = !state.indicators.signals;
    saveIndicators();
  });
  $("toggleVolumeProfile")?.addEventListener("click", () => {
    state.indicators.volumeProfile = !state.indicators.volumeProfile;
    syncIndicatorButtons();
    drawChart();
  });
  $("autoChartMarks")?.addEventListener("click", () => {
    state.indicators.autoMarks = !state.indicators.autoMarks;
    syncIndicatorButtons();
    drawChart();
  });
  $("toggleReplay")?.addEventListener("click", toggleReplay);
  document.querySelectorAll("[data-draw-tool]").forEach((button) => {
    button.addEventListener("click", () => setDrawingTool(button.dataset.drawTool));
  });
  $("clearDrawings")?.addEventListener("click", () => {
    state.drawings = [];
    state.draftDrawing = null;
    saveDrawings();
    $("chartAiBox").classList.add("hidden");
    drawChart();
  });
  $("analyzeChartAi")?.addEventListener("click", analyzeChartAi);
  $("loadLocalHistory")?.addEventListener("click", loadLocalHistory);
  $("strategySelect")?.addEventListener("change", () => {
    renderStrategyCards();
    loadStrategyLab();
    loadStrategyCompare();
    loadStrategyWarRoom();
    loadStrategyDoctor();
    loadBotCenter();
    loadBotScheduler();
    loadStrategyRobotProfiles();
  });
  $("directionMode")?.addEventListener("change", () => {
    syncRiskPlaceholders();
    renderStrategyAnalysis(state.paper?.ai_analysis || null);
    loadStrategyWarRoom();
    loadStrategyDoctor();
    loadBotCenter();
    loadBotScheduler();
    loadStrategyRobotProfiles();
  });
  $("riskValueMode")?.addEventListener("change", syncRiskPlaceholders);
  ["leverageInput", "positionInput", "riskSource", "riskValueMode", "takeProfitInput", "stopLossInput", "strategyOrderType", "marginMode", "trailingTakeEnabled", "trailingTakePct", "trailingStopEnabled", "trailingStopPct", "reduceOnly"].forEach((id) => {
    $(id)?.addEventListener("change", loadStrategyWarRoom);
    $(id)?.addEventListener("input", loadStrategyWarRoom);
    $(id)?.addEventListener("change", renderStrategyCommandStrip);
    $(id)?.addEventListener("input", renderStrategyCommandStrip);
  });
  $("conditionOrderType")?.addEventListener("change", syncConditionForm);
  ["conditionSide", "conditionOrderType", "conditionLimitPrice", "conditionQty"].forEach((id) => {
    $(id)?.addEventListener("change", estimateOrder);
    $(id)?.addEventListener("input", estimateOrder);
  });
  document.querySelectorAll("[data-trade-filter]").forEach((button) => {
    button.addEventListener("click", () => {
      state.tradeFilter = button.dataset.tradeFilter || "ALL";
      renderTrades();
    });
  });
  $("analyzeStrategy")?.addEventListener("click", analyzeStrategy);
  $("runStrategyLab")?.addEventListener("click", () => {
    loadStrategyLab({ refreshEvidence: true });
    loadStrategyWarRoom();
  });
  $("refreshWarRoom")?.addEventListener("click", loadStrategyWarRoom);
  $("runStrategyCompare")?.addEventListener("click", loadStrategyCompare);
  $("runStrategyDoctor")?.addEventListener("click", () => loadStrategyDoctor(true));
  $("refreshBotCenter")?.addEventListener("click", loadBotCenter);
  $("refreshBotScheduler")?.addEventListener("click", loadBotScheduler);
  $("refreshRobotProfiles")?.addEventListener("click", loadStrategyRobotProfiles);
  $("releaseBotOwner")?.addEventListener("click", releaseBotOwner);
  $("runBacktest")?.addEventListener("click", () => loadBacktest({ record: false }));
  $("freezeBacktest")?.addEventListener("click", () => loadBacktest({ record: true }));
  $("refreshResearch")?.addEventListener("click", () => loadResearchPanel());
  $("openResearchInAi")?.addEventListener("click", () => openResearchPromptInAi());
  $("refreshAnomalyEvents")?.addEventListener("click", () => loadAnomalyEvents("", { force: true, limit: 120 }));
  $("refreshSourceControl")?.addEventListener("click", () => loadStockSourceControl(state.symbol, runtime.symbolVersion));
  $("refreshAnomalyRadar")?.addEventListener("click", () => loadAnomalyRadar(false, runtime.symbolVersion, { force: true }));
  $("anomalyFilterBar")?.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      state.anomalyFilter = button.dataset.anomalyFilter || "all";
      $("anomalyFilterBar")?.querySelectorAll("button").forEach((item) => item.classList.toggle("active", item === button));
      renderAnomalyRadar(state.anomalyRadar || {});
    });
  });
  $("pushAnomalyNotice")?.addEventListener("click", () => loadAnomalyRadar(true, runtime.symbolVersion, { force: true }));
  $("anomalyToAi")?.addEventListener("click", openAnomalyPromptInAi);
  $("refreshFutuStatus")?.addEventListener("click", () => loadFutuStatus(true));
  $("refreshFutuDeep")?.addEventListener("click", () => loadFutuDeep(true));
  $("refreshIntel")?.addEventListener("click", () => loadMarketInsights(false));
  $("pushIntelNotice")?.addEventListener("click", () => loadMarketInsights(true));
  $("deepseekAnalyze")?.addEventListener("click", loadDeepSeekAnalysis);
  $("deepseekScan")?.addEventListener("click", () => loadDeepSeekOpportunities(false));
  $("deepseekReview")?.addEventListener("click", loadDeepSeekPlatformReview);
  $("runMarketAiAnalysis")?.addEventListener("click", runMarketAiAnalysis);
  $("runTradingAgentsRoom")?.addEventListener("click", runTradingAgentsRoom);
  $("saveRuntimeKeys")?.addEventListener("click", saveRuntimeKeys);
  $("clearRuntimeKeys")?.addEventListener("click", clearRuntimeKeys);
  $("aiRoomLoadSymbol")?.addEventListener("click", () => loadAiRoomSymbolFromInput());
  $("aiRoomStartMeeting")?.addEventListener("click", () => loadAiRoomSymbolFromInput({ meeting: true }));
  $("aiRoomFocusKeys")?.addEventListener("click", focusAiRoomKeys);
  $("aiRoomSymbolInput")?.addEventListener("focus", (event) => {
    event.target.select();
    renderAiRoomSymbolSuggestions();
  });
  $("aiRoomSymbolInput")?.addEventListener("input", renderAiRoomSymbolSuggestions);
  $("aiRoomSymbolSuggestions")?.addEventListener("mousedown", (event) => {
    const row = event.target.closest("[data-ai-room-suggestion]");
    if (!row) return;
    event.preventDefault();
    if ($("aiRoomSymbolInput")) $("aiRoomSymbolInput").value = row.dataset.aiRoomSuggestion || state.symbol;
    $("aiRoomSymbolSuggestions").classList.remove("open");
    loadAiRoomSymbolFromInput();
  });
  $("aiRoomSymbolInput")?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      $("aiRoomSymbolSuggestions")?.classList.remove("open");
      loadAiRoomSymbolFromInput({ meeting: event.ctrlKey || event.metaKey });
    }
    if (event.key === "Escape") $("aiRoomSymbolSuggestions")?.classList.remove("open");
  });
  $("aiRoomAskMeeting")?.addEventListener("click", () => {
    syncAiRoomQuestionToMarketAi();
    runTradingAgentsRoom();
  });
  $("aiRoomQuestionInput")?.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      syncAiRoomQuestionToMarketAi();
      runTradingAgentsRoom();
    }
  });
  document.querySelectorAll("[data-ai-room-symbol]").forEach((button) => {
    button.addEventListener("click", () => {
      if ($("aiRoomSymbolInput")) $("aiRoomSymbolInput").value = button.dataset.aiRoomSymbol || state.symbol;
      loadAiRoomSymbolFromInput();
    });
  });
  $("refreshMarketAiSnapshot")?.addEventListener("click", () => {
    renderMarketAiLocal();
    $("marketAiState").textContent = "本地快照已刷新";
    loadTradingAgentsStatus().catch(() => {});
  });
  $("marketAiQuestion")?.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      runMarketAiAnalysis();
    }
  });
  $("runCodeWorker")?.addEventListener("click", runCodeWorker);
  $("refreshCodeWorker")?.addEventListener("click", loadCodeWorkerDrafts);
  $("refreshFullConfig")?.addEventListener("click", loadFullConfig);
  $("applyFullConfigPreset")?.addEventListener("click", applyFullConfigPreset);
  $("configOpenMarketAi")?.addEventListener("click", () => setInterfaceView("marketai"));
  $("configOpenResearch")?.addEventListener("click", () => setInterfaceView("research"));
  $("configRefreshData")?.addEventListener("click", () => {
    loadDataReliability();
    loadDataCache();
  });
  $("refreshV2Platform")?.addEventListener("click", loadV2Platform);
  $("refreshDataReliability")?.addEventListener("click", loadDataReliability);
  $("refreshMarketAdapters")?.addEventListener("click", loadMarketAdapters);
  $("runDataBackfill")?.addEventListener("click", runDataBackfill);
  $("refreshScanner")?.addEventListener("click", () => loadMarketScanner(false));
  $("pushScannerNotice")?.addEventListener("click", () => loadMarketScanner(true));
  $("armStrategy")?.addEventListener("click", armStrategy);
  $("stopStrategy")?.addEventListener("click", stopStrategy);
  $("resetPaper")?.addEventListener("click", resetPaper);
  $("manualBuy")?.addEventListener("click", () => manualPaperOrder("BUY"));
  $("manualSell")?.addEventListener("click", () => manualPaperOrder("SELL"));
  $("manualClose")?.addEventListener("click", () => manualPaperOrder("CLOSE"));
  $("addCondition")?.addEventListener("click", addCondition);
  $("orderFilter")?.addEventListener("change", () => {
    state.orderFilter = $("orderFilter").value;
    renderOrders(state.paper?.orders || []);
  });
  $("saveApiConfig")?.addEventListener("click", saveApiConfig);
  $("transferAssetButton")?.addEventListener("click", transferAsset);
  $("guardianStart")?.addEventListener("click", () => setGuardian(true));
  $("guardianStop")?.addEventListener("click", () => setGuardian(false));
  $("guardianEmergencyStop")?.addEventListener("click", guardianEmergencyStop);
  $("markNotificationsRead")?.addEventListener("click", markNotificationsRead);
  $("saveTerminalSettings")?.addEventListener("click", saveTerminalSettings);
  $("daemonPrepare")?.addEventListener("click", prepareDaemon);
  $("daemonOpenLogs")?.addEventListener("click", () => focusModule(".ledger-panel"));
  $("exportOrders")?.addEventListener("click", exportOrders);
  $("exportLedger")?.addEventListener("click", exportLedger);
  document.addEventListener("keydown", handleShortcut);
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      openCommandPanel();
    }
  });
  bindChartEvents();
  $("timeframeTabs").querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      $("timeframeTabs").querySelectorAll("button").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      state.bar = button.dataset.bar;
      if (isStockMarket()) {
        if (state.bar === "1m" && state.stockSession === "all") state.stockSession = "regular";
        state.chartMode = isStockMinuteBar(state.bar) ? "line" : "candles";
        syncStockSessionTabs();
      } else {
        state.chartMode = "candles";
      }
      syncChartControlLabels();
      state.chartView.offset = 0;
      state.chartView.visible = isStockMarket() ? stockVisibleBarsForBar(state.bar) : 180;
      runtime.chartUserZoomed = false;
      $("chartStatus").textContent = isStockMarket()
        ? `正在切换${stockSessionLabel()} ${stockBarLabel(state.bar)}分时...`
        : "正在切换周期...";
      renderInstantPreviewCandles(state.symbol, state.bar);
      loadCandles();
      loadStockSourceControl(state.symbol, runtime.symbolVersion).catch(() => {});
      connectSocket();
    });
  });
  window.addEventListener("resize", drawChart);
  syncRiskPlaceholders();
  syncConditionForm();
}

function deferBootLoad(delayMs, task) {
  setTimeout(() => {
    try {
      const result = task();
      if (result?.catch) result.catch(() => {});
    } catch (error) {
      // Non-critical boot panels must not block the market desk.
    }
  }, delayMs);
}

function runForInterface(views, task) {
  if (!views.includes(state.interfaceView) && state.interfaceView !== "all") return;
  try {
    const result = task();
    if (result?.catch) result.catch(() => {});
  } catch (error) {
    // Hidden-workspace refreshes are opportunistic.
  }
}

async function boot() {
  if ("scrollRestoration" in window.history) window.history.scrollRestoration = "manual";
  const bootStartedAt = Date.now();
  const restoreTop = () => {
    if (Date.now() - bootStartedAt < 2600) window.scrollTo(0, 0);
  };
  restoreTop();
  requestAnimationFrame(restoreTop);
  setTimeout(restoreTop, 300);
  setTimeout(restoreTop, 1200);
  syncMarketRailDisclosure();
  renderMarketRailDisclosureSummary();
  applyMarketResearchCopy();
  const chartWorkspace = ["trade", "research", "marketai", "all"].includes(state.interfaceView);
  updateDesktopClock();
  renderDesktopStatus();
  setupFutuStyleWorkspace();
  renderSideInsights();
  renderLiveSourceBar();
  renderMarketWorkflowStrip();
  syncActiveSymbolHeader("准备加载行情");
  if (chartWorkspace) {
    if ($("chartStatus")) $("chartStatus").textContent = "优先显示K线预览...";
    renderInstantPreviewCandles(state.symbol, state.bar);
    requestAnimationFrame(() => ensureActiveChartPreview(state.symbol, state.bar));
  }
  loadMarkets();
  renderSideInsights();
  loadFutuStatus(false).catch(() => {});
  refreshMarketTickers().catch(() => {});
  bindEvents();
  syncTimeframeTabs();
  syncStockSessionTabs();
  if (state.interfaceView === "research") {
    const focusRadar = () => focusModule(".anomaly-workbench", false);
    setTimeout(focusRadar, 1400);
    setTimeout(focusRadar, 3600);
  }
  const strategiesReady = loadStrategies().catch(() => {});
  if (chartWorkspace) {
    if ($("chartStatus") && !chartIsVisibleForSymbol(state.symbol)) $("chartStatus").textContent = "优先加载K线和行情雷达...";
    ensureActiveChartPreview(state.symbol, state.bar);
    loadCandles().catch(() => {});
  }
  loadPlatformControlCenter().catch(() => {});
  deferBootLoad(1300, loadInternalBacktestReturnQuality);
  deferBootLoad(650, () => runForInterface(["research"], () => loadResearchPanel()));
  if (state.interfaceView === "research" && isStockMarket()) {
    deferBootLoad(1800, () => loadFutuDeep(false));
  }
  connectSocket();
  connectMarketSocket();
  pollLiveTicker();
  fallbackPoll();
  deferBootLoad(2200, () => runForInterface(["trade", "research", "marketai", "all"], () => loadTrendCockpit(state.symbol)));
  deferBootLoad(2600, () => runForInterface(["trade", "research", "marketai", "all"], () => isStockMarket() ? loadFutuDeep(false) : null));
  deferBootLoad(3200, () => runForInterface(["research", "marketai", "all"], () => loadMarketScanner(false)));
  deferBootLoad(3300, () => runForInterface(["trade", "research", "marketai", "all"], () => startStockHistoryPrewarm(false)));
  deferBootLoad(3600, () => runForInterface(["trade", "research", "marketai", "all"], prewarmPriorityChartCache));
  deferBootLoad(4400, () => runForInterface(["marketai", "all"], () => loadResearchPanel()));
  deferBootLoad(5000, () => runForInterface(["research", "marketai", "all"], () => loadStockSourceControl(state.symbol)));
  deferBootLoad(5600, () => runForInterface(["research", "marketai", "all"], () => loadMarketInsights(false)));
  deferBootLoad(6800, () => runForInterface(["research", "all"], () => loadAnomalyRadar(false)));
  deferBootLoad(7600, () => runForInterface(["research", "all"], () => loadAnomalyEvents("")));
  deferBootLoad(8200, () => runForInterface(["trade", "research", "marketai", "all"], () => isStockMarket() ? loadFutuDeep(false) : loadDerivatives()));
  deferBootLoad(900, () => runForInterface(["platform", "bot", "all"], () => refreshPaper(false)));
  deferBootLoad(1050, () => runForInterface(["marketai", "all"], () => loadDeepSeekStatus()));
  deferBootLoad(1080, () => runForInterface(["marketai", "all"], () => loadRuntimeKeyStatus()));
  deferBootLoad(1120, () => runForInterface(["marketai", "all"], () => loadTradingAgentsStatus()));
  deferBootLoad(1200, () => runForInterface(["bot", "all"], () => strategiesReady.then(() => loadStrategyCompare())));
  deferBootLoad(1400, () => runForInterface(["bot", "all"], () => strategiesReady.then(() => loadStrategyWarRoom())));
  deferBootLoad(1520, () => runForInterface(["bot", "all"], () => estimateOrder()));
  deferBootLoad(1650, () => runForInterface(["system", "all"], () => loadHistoryTable()));
  deferBootLoad(1900, () => loadProfile().then(() => {
    if (
      state.profile?.settings?.start_module
      && !runtime.userInteractionStarted
      && !["platform", "research"].includes(state.interfaceView)
    ) {
      setTimeout(() => {
        if (!runtime.userInteractionStarted) focusModule(state.profile.settings.start_module);
      }, 200);
    }
  }));
  deferBootLoad(9200, () => runForInterface(["system", "all"], () => loadApiConfig()));
  deferBootLoad(9800, () => runForInterface(["system", "all"], () => loadLedger()));
  deferBootLoad(10400, () => runForInterface(["system", "all"], () => loadFullConfig()));
  deferBootLoad(11000, () => runForInterface(["system", "all"], () => loadV2Platform()));
  deferBootLoad(11600, () => runForInterface(["system", "all"], () => loadDataCache()));
  deferBootLoad(12200, () => runForInterface(["all"], () => loadLeaderboard()));
  deferBootLoad(12800, () => runForInterface(["bot", "all"], () => loadStrategyLab()));
  deferBootLoad(13400, () => runForInterface(["bot", "all"], () => loadStrategyDoctor()));
  deferBootLoad(14000, () => runForInterface(["bot", "all"], () => loadBotCenter()));
  deferBootLoad(14600, () => runForInterface(["bot", "all"], () => loadBotScheduler()));
  deferBootLoad(15200, () => runForInterface(["bot", "all"], () => loadStrategyRobotProfiles()));
  deferBootLoad(15800, () => runForInterface(["system", "all"], () => loadCodeWorkerDrafts()));
  deferBootLoad(16400, () => runForInterface(["marketai", "all"], () => loadDeepSeekOpportunities(true)));
  deferBootLoad(17000, () => runForInterface(["bot", "all"], () => loadStrategyMarketplace()));
  setInterval(pollLiveTicker, 3000);
  setInterval(fallbackPoll, 7000);
  setInterval(refreshMarketTickers, 8000);
  setInterval(renderSideInsights, 3000);
  setInterval(() => loadFutuStatus(false), 30000);
  setInterval(() => runForInterface(["trade", "research", "marketai", "all"], () => isStockMarket() ? loadFutuDeep(false) : null), 45000);
  setInterval(() => runForInterface(["research", "marketai", "all"], () => loadMarketScanner(false)), 45000);
  setInterval(() => runForInterface(["research", "marketai", "all"], () => loadAnomalyRadar(false)), 75000);
  setInterval(() => runForInterface(["research", "marketai"], () => loadStockSourceControl(state.symbol)), 60000);
  setInterval(() => runForInterface(["research"], () => loadDeepSeekOpportunities(true)), 60000);
  setInterval(() => runForInterface(["system"], loadCodeWorkerDrafts), 60000);
  setInterval(() => runForInterface(["system"], loadV2Platform), 45000);
  setInterval(() => runForInterface(["system"], loadDataCache), 60000);
  setInterval(() => runForInterface(["platform", "bot", "system", "all"], () => refreshPaper(true)), 7000);
  setInterval(() => runForInterface(["platform", "bot", "system", "all"], loadRiskEngine), 7000);
  setInterval(() => runForInterface(["platform"], loadPlatformControlCenter), 7000);
  setInterval(() => runForInterface(["trade", "research", "marketai", "all"], () => { if (!isStockMarket()) loadDerivatives(); }), 30000);
  setInterval(() => runForInterface(["research", "marketai", "all"], () => loadMarketInsights(false)), 45000);
  setInterval(() => runForInterface(["research"], loadLeaderboard), 60000);
  setInterval(() => runForInterface(["bot"], loadStrategyLab), 60000);
  setInterval(() => runForInterface(["bot"], loadStrategyCompare), 60000);
  setInterval(() => runForInterface(["bot"], loadStrategyWarRoom), 60000);
  setInterval(() => runForInterface(["bot"], loadStrategyDoctor), 60000);
  setInterval(() => runForInterface(["bot"], loadBotCenter), 60000);
  setInterval(() => runForInterface(["bot"], loadBotScheduler), 60000);
  setInterval(() => runForInterface(["bot"], loadStrategyRobotProfiles), 60000);
  setInterval(() => runForInterface(["research", "marketai"], loadResearchPanel), 90000);
  setInterval(() => runForInterface(["bot"], estimateOrder), 15000);
  setInterval(() => runForInterface(["system"], loadApiConfig), 45000);
  setInterval(() => runForInterface(["system", "bot"], loadProfile), 45000);
  setInterval(guardianHeartbeat, 15000);
  setInterval(() => runForInterface(["system"], loadLedger), 30000);
  setInterval(() => runForInterface(["system"], loadStrategyMarketplace), 60000);
  setInterval(updateDesktopClock, 1000);
}

boot();


;(function attachStrategyCorrelationUncertaintyLedger(root) {
  "use strict";

  const originalRenderStrategyLabEvidence = renderStrategyLabEvidence;

  function uncertaintyPresentation(value) {
    const shared = root.HakimiEvidencePresentation;
    if (
      shared
      && typeof shared.strategyCorrelationUncertaintySummaryPresentation === "function"
    ) {
      return shared.strategyCorrelationUncertaintySummaryPresentation(value);
    }
    return {
      valid: false,
      rawStatus: "UNKNOWN",
      rawGapCategory: "SOURCE_INVALID",
      statusText: "未核验",
      sourceText: "相关性不确定性审计：未核验",
      gapText: "有效样本、区间分类与事前协议绑定尚未闭合",
      maturityText: "跨簇 pair：-- / -- · 有效样本门槛：12",
      permissionText: "仅研究描述 · 不选参 · 模拟未授权 · 实盘永久硬锁",
      detailText: "公共投影只接受聚合计数",
    };
  }

  function uncertaintyLedgerHtml(presentation) {
    const safe = (value) => escapeHtml(String(value || "未核验"));
    return [
      '<section class="strategy-correlation-ledger strategy-uncertainty-ledger"',
      ' data-evidence-role="correlation-uncertainty"',
      ' data-raw-status="' + safe(presentation.rawStatus) + '"',
      ' data-gap-category="' + safe(presentation.rawGapCategory) + '"',
      ' data-contract-valid="' + (presentation.valid ? "true" : "false") + '"',
      ' aria-labelledby="strategyUncertaintyLedgerHeading" aria-live="polite">',
      '<header><span id="strategyUncertaintyLedgerHeading">相关性不确定性</span>',
      '<strong>' + safe(presentation.statusText) + '</strong></header>',
      '<ol class="strategy-correlation-flow">',
      '<li data-stage="source"><span>SOURCE</span><strong>'
        + safe(presentation.sourceText) + '</strong></li>',
      '<li data-stage="gap"><span>GAP</span><strong>'
        + safe(presentation.gapText) + '</strong></li>',
      '<li data-stage="maturity"><span>MATURITY</span><strong>'
        + safe(presentation.maturityText) + '</strong></li>',
      '<li data-stage="permission"><span>PERMISSION</span><strong>'
        + safe(presentation.permissionText) + '</strong></li>',
      '</ol>',
      '<small>' + safe(presentation.detailText) + '</small>',
      '</section>',
    ].join("");
  }

  renderStrategyLabEvidence = function renderStrategyLabEvidenceWithUncertainty(
    data = {}
  ) {
    const result = originalRenderStrategyLabEvidence.call(this, data);
    const host = document.getElementById("strategyLabEvidence");
    if (!host) return result;
    const previous = host.querySelector(
      '[data-evidence-role="correlation-uncertainty"]'
    );
    if (previous && typeof previous.remove === "function") previous.remove();
    const presentation = uncertaintyPresentation(
      data?.correlation_uncertainty_summary
    );
    const html = uncertaintyLedgerHtml(presentation);
    const clusterLedger = host.querySelector(
      '[data-evidence-role="correlation-cluster"]'
    );
    if (clusterLedger && typeof clusterLedger.insertAdjacentHTML === "function") {
      clusterLedger.insertAdjacentHTML("afterend", html);
      return result;
    }
    const robustnessBand = host.querySelector(".strategy-evidence-band.robustness");
    if (robustnessBand && typeof robustnessBand.insertAdjacentHTML === "function") {
      robustnessBand.insertAdjacentHTML("beforeend", html);
    }
    return result;
  };
})(typeof window !== "undefined" ? window : globalThis);


;(function attachStrategyCorrelationMultiplicityLedger(root) {
  "use strict";

  const originalRenderStrategyLabEvidence = renderStrategyLabEvidence;

  function multiplicityPresentation(value) {
    const shared = root.HakimiEvidencePresentation;
    if (
      shared
      && typeof shared.strategyCorrelationMultiplicitySummaryPresentation
        === "function"
    ) {
      return shared.strategyCorrelationMultiplicitySummaryPresentation(value);
    }
    return {
      valid: false,
      rawStatus: "UNKNOWN",
      rawGapCategory: "SOURCE_INVALID",
      statusText: "未核验",
      sourceText: "Schema16 family evidence：未核验",
      gapText: "事前 family size、Bonferroni 调整与来源重放尚未闭合",
      maturityText: "跨簇 family：-- / -- · 单 pair α：--",
      permissionText: "仅研究描述 · 不选参 · 模拟未授权 · 实盘永久硬锁",
      detailText: "只公开 family 聚合",
    };
  }

  function multiplicityLedgerHtml(presentation) {
    const safe = (value) => escapeHtml(String(value || "未核验"));
    return [
      '<section class="strategy-correlation-ledger strategy-multiplicity-ledger"',
      ' data-evidence-role="correlation-multiplicity"',
      ' data-raw-status="' + safe(presentation.rawStatus) + '"',
      ' data-gap-category="' + safe(presentation.rawGapCategory) + '"',
      ' data-contract-valid="' + (presentation.valid ? "true" : "false") + '"',
      ' aria-labelledby="strategyMultiplicityLedgerHeading" aria-live="polite">',
      '<header><span id="strategyMultiplicityLedgerHeading">相关簇 Family 预算</span>',
      '<strong>' + safe(presentation.statusText) + '</strong></header>',
      '<ol class="strategy-correlation-flow">',
      '<li data-stage="source"><span>SOURCE</span><strong>'
        + safe(presentation.sourceText) + '</strong></li>',
      '<li data-stage="gap"><span>GAP</span><strong>'
        + safe(presentation.gapText) + '</strong></li>',
      '<li data-stage="maturity"><span>MATURITY</span><strong>'
        + safe(presentation.maturityText) + '</strong></li>',
      '<li data-stage="permission"><span>PERMISSION</span><strong>'
        + safe(presentation.permissionText) + '</strong></li>',
      '</ol>',
      '<small>' + safe(presentation.detailText) + '</small>',
      '</section>',
    ].join("");
  }

  renderStrategyLabEvidence = function renderStrategyLabEvidenceWithMultiplicity(
    data = {}
  ) {
    const result = originalRenderStrategyLabEvidence.call(this, data);
    const host = document.getElementById("strategyLabEvidence");
    if (!host) return result;
    const previous = host.querySelector(
      '[data-evidence-role="correlation-multiplicity"]'
    );
    if (previous && typeof previous.remove === "function") previous.remove();
    const presentation = multiplicityPresentation(
      data?.correlation_multiplicity_summary
    );
    const html = multiplicityLedgerHtml(presentation);
    const uncertaintyLedger = host.querySelector(
      '[data-evidence-role="correlation-uncertainty"]'
    );
    if (
      uncertaintyLedger
      && typeof uncertaintyLedger.insertAdjacentHTML === "function"
    ) {
      uncertaintyLedger.insertAdjacentHTML("afterend", html);
      return result;
    }
    const clusterLedger = host.querySelector(
      '[data-evidence-role="correlation-cluster"]'
    );
    if (clusterLedger && typeof clusterLedger.insertAdjacentHTML === "function") {
      clusterLedger.insertAdjacentHTML("afterend", html);
    }
    return result;
  };
})(typeof window !== "undefined" ? window : globalThis);
