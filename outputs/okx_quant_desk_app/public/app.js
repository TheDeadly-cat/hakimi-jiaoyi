const $ = selector => document.querySelector(selector);

let appState = null;
let lastBacktest = null;

const viewTitles = {
  dashboard: "交易首页",
  exchange: "实时交易台",
  market: "OKX 行情",
  "strategy-market": "策略广场",
  "strategy-compare": "策略对比",
  history: "交易历史",
  account: "账户连接",
  strategy: "策略配置",
  automation: "自动交易",
  backtest: "回测中心",
  paper: "模拟盘",
  risk: "风控中心",
  review: "交易复盘"
};

const historyViews = new Set(["account", "backtest", "paper", "risk", "review"]);

let strategyTemplates = [];
let selectedTemplateId = "ma_trend";
let liveTickerTimer = null;
let automationTimer = null;
let newsTimer = null;
let marketRefreshTimer = null;
let terminalTimer = null;
let terminalSocket = null;
let terminalPingTimer = null;
let terminalSymbol = "BTC-USDT";
let terminalSeries = [];
let terminalWatch = {};
let terminalCandles = [];
let terminalBook = { bids: [], asks: [] };
let terminalChartMode = "line";
let terminalTimeframe = "1m";

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options
  });
  const data = await response.json();
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || data.message || "请求失败");
  }
  return data;
}

function showNotice(message, tone = "success") {
  const box = $("#notice");
  box.textContent = message;
  box.className = `notice show ${tone === "error" ? "error" : ""}`;
  window.clearTimeout(showNotice.timer);
  showNotice.timer = window.setTimeout(() => {
    box.className = "notice";
    box.textContent = "";
  }, 4200);
}

function fmtMoney(value) {
  return Number(value || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtPct(value) {
  const sign = Number(value) > 0 ? "+" : "";
  return `${sign}${Number(value || 0).toFixed(2)}%`;
}

function pointPath(values, width, height, pad = 18) {
  if (!values.length) return "";
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  return values.map((value, index) => {
    const x = pad + (index / Math.max(1, values.length - 1)) * (width - pad * 2);
    const y = height - pad - ((value - min) / span) * (height - pad * 2);
    return `${index === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`;
  }).join(" ");
}

function renderLineChart(svg, values, color = "#087f5b", fill = "rgba(8,127,91,0.12)") {
  const width = 900;
  const height = Number(svg.getAttribute("viewBox").split(" ")[3] || 260);
  const line = pointPath(values, width, height);
  if (!line) {
    svg.innerHTML = "";
    return;
  }
  const area = `${line} L${width - 18} ${height - 18} L18 ${height - 18} Z`;
  svg.innerHTML = `
    <path d="${area}" fill="${fill}"></path>
    <path d="${line}" fill="none" stroke="${color}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"></path>
  `;
}

function renderTerminalChart(values) {
  const svg = $("#terminalChart");
  if (!svg) return;
  if (terminalChartMode === "candle") {
    renderCandleChart(svg, terminalCandles.slice(-90));
    return;
  }
  if (terminalChartMode === "depth") {
    renderDepthChart(svg, terminalBook);
    return;
  }
  renderLineChart(svg, values.slice(-180), "#087f5b", "rgba(8,127,91,0.11)");
}

function renderCandleChart(svg, candles) {
  const width = 980;
  const height = 420;
  if (!candles.length) {
    svg.innerHTML = "";
    return;
  }
  const prices = candles.flatMap(item => [item.high, item.low]);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const span = max - min || 1;
  const pad = 22;
  const candleWidth = Math.max(3, (width - pad * 2) / candles.length * 0.58);
  const y = price => height - pad - ((price - min) / span) * (height - pad * 2);
  const nodes = candles.map((candle, index) => {
    const x = pad + (index / Math.max(1, candles.length - 1)) * (width - pad * 2);
    const up = candle.close >= candle.open;
    const color = up ? "#087f5b" : "#be3f42";
    const top = y(Math.max(candle.open, candle.close));
    const bottom = y(Math.min(candle.open, candle.close));
    return `
      <line x1="${x}" y1="${y(candle.high)}" x2="${x}" y2="${y(candle.low)}" stroke="${color}" stroke-width="1.4"></line>
      <rect x="${x - candleWidth / 2}" y="${top}" width="${candleWidth}" height="${Math.max(2, bottom - top)}" fill="${color}" rx="1"></rect>
    `;
  }).join("");
  svg.innerHTML = nodes;
}

function renderDepthChart(svg, book) {
  const width = 980;
  const height = 420;
  const bids = [...(book.bids || [])].slice(0, 40).reverse();
  const asks = [...(book.asks || [])].slice(0, 40);
  const bidTotals = bids.map((row, index) => bids.slice(0, index + 1).reduce((sum, item) => sum + Number(item.size || 0), 0));
  const askTotals = asks.map((row, index) => asks.slice(0, index + 1).reduce((sum, item) => sum + Number(item.size || 0), 0));
  const maxTotal = Math.max(...bidTotals, ...askTotals, 1);
  const mid = width / 2;
  const pad = 24;
  const bidPoints = bidTotals.map((total, index) => {
    const x = pad + (index / Math.max(1, bidTotals.length - 1)) * (mid - pad);
    const y = height - pad - (total / maxTotal) * (height - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const askPoints = askTotals.map((total, index) => {
    const x = mid + (index / Math.max(1, askTotals.length - 1)) * (mid - pad);
    const y = height - pad - (total / maxTotal) * (height - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  svg.innerHTML = `
    <polyline points="${bidPoints.join(" ")}" fill="none" stroke="#087f5b" stroke-width="4"></polyline>
    <polyline points="${askPoints.join(" ")}" fill="none" stroke="#be3f42" stroke-width="4"></polyline>
    <polygon points="${bidPoints.join(" ")} ${mid},${height - pad} ${pad},${height - pad}" fill="rgba(8,127,91,0.12)"></polygon>
    <polygon points="${askPoints.join(" ")} ${width - pad},${height - pad} ${mid},${height - pad}" fill="rgba(190,63,66,0.12)"></polygon>
  `;
}

function renderBookRows(container, rows, tone) {
  const maxTotal = Math.max(...rows.map(row => Number(row.total || row.size || 0)), 1);
  container.innerHTML = rows.slice(0, 12).map(row => `
    <div class="book-row" style="--depth:${Math.max(4, Number(row.total || row.size || 0) / maxTotal * 100).toFixed(0)}%">
      <span class="price">${fmtPrice(row.price)}</span>
      <span>${Number(row.size || 0).toFixed(4)}</span>
      <span>${Number(row.total || row.size || 0).toFixed(4)}</span>
    </div>
  `).join("");
}

function renderTerminalWatch() {
  const symbols = ["BTC-USDT", "ETH-USDT", "SOL-USDT", "BTC-USDT-SWAP"];
  $("#terminalWatchRows").innerHTML = symbols.map(symbol => {
    const item = terminalWatch[symbol];
    return `
      <button class="watch-item ${symbol === terminalSymbol ? "active" : ""}" type="button" data-terminal-watch="${symbol}">
        <strong>${symbol}<em class="${(item?.changePct || 0) >= 0 ? "positive" : "negative"}">${item ? fmtPct(item.changePct) : "--"}</em></strong>
        <span><small>最新</small><b>${item ? fmtPrice(item.last) : "--"}</b></span>
      </button>
    `;
  }).join("");
  $("#terminalWatchRows").querySelectorAll("[data-terminal-watch]").forEach(button => {
    button.addEventListener("click", () => setTerminalSymbol(button.dataset.terminalWatch));
  });
}

function renderTerminalPositions() {
  const profiles = appState?.automation?.profiles || [];
  const decisions = appState?.automation?.decisions || [];
  $("#terminalPositions").innerHTML = profiles.map(profile => {
    const latest = decisions.find(item => item.symbol === profile.symbol);
    return `
      <tr>
        <td>${profile.symbol}</td>
        <td>${templateNameFromId(profile.templateId)}</td>
        <td>${profile.status || "观察"}</td>
        <td>${fmtPrice(profile.lowerAnchor)} / ${fmtPrice(profile.anchorPrice)} / ${fmtPrice(profile.upperAnchor)}</td>
        <td>${latest ? latest.action : "等待"}</td>
      </tr>
    `;
  }).join("");
}

function templateNameFromId(templateId) {
  return strategyTemplates.find(item => item.id === templateId)?.name || templateId || "策略";
}

function renderTerminalSnapshot(snapshot) {
  const ticker = snapshot.ticker.ticker;
  terminalCandles = snapshot.candles || [];
  terminalBook = snapshot.book || { bids: [], asks: [] };
  terminalWatch[snapshot.symbol] = ticker;
  if (!terminalSeries.length || snapshot.symbol !== terminalSymbol) {
    terminalSeries = snapshot.candles.map(item => item.close);
  } else {
    terminalSeries.push(ticker.last);
    terminalSeries = terminalSeries.slice(-240);
  }
  $("#terminalSymbol").textContent = snapshot.symbol;
  $("#terminalPrice").textContent = `${fmtPrice(ticker.last)} USDT`;
  $("#terminalChange").textContent = fmtPct(ticker.changePct);
  $("#terminalChange").className = ticker.changePct >= 0 ? "positive" : "negative";
  $("#terminalSource").textContent = sourceLabel(snapshot.source);
  $("#terminalUpdated").textContent = new Date(snapshot.updatedAt).toLocaleTimeString("zh-CN");
  $("#indexPrice").textContent = fmtPrice(snapshot.derivative?.indexPrice || ticker.last);
  $("#markPrice").textContent = fmtPrice(snapshot.derivative?.markPrice || ticker.last);
  $("#fundingRate").textContent = `${((snapshot.derivative?.fundingRate || 0) * 100).toFixed(4)}%`;
  $("#openInterest").textContent = fmtMoney(snapshot.derivative?.openInterest || 0);
  $("#ticketPrice").value = ticker.last;
  $("#midPrice").textContent = fmtPrice(ticker.last);
  renderTerminalChart(terminalSeries);
  renderBookRows($("#askRows"), [...snapshot.book.asks].reverse(), "ask");
  renderBookRows($("#bidRows"), snapshot.book.bids, "bid");
  $("#terminalTrades").innerHTML = snapshot.trades.trades.slice(0, 18).map(trade => `
    <tr>
      <td>${new Date(trade.time).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</td>
      <td class="${trade.side === "buy" ? "positive" : "negative"}">${trade.side === "buy" ? "买入" : "卖出"}</td>
      <td>${fmtPrice(trade.price)}</td>
      <td>${Number(trade.size || 0).toFixed(4)}</td>
    </tr>
  `).join("");
  renderTerminalWatch();
  renderTerminalPositions();
}

function applyTerminalTicker(ticker, source = "OKX WebSocket") {
  if (!ticker || ticker.instId !== terminalSymbol) return;
  terminalWatch[ticker.instId] = ticker;
  terminalSeries.push(Number(ticker.last));
  terminalSeries = terminalSeries.slice(-240);
  $("#terminalSymbol").textContent = ticker.instId;
  $("#terminalPrice").textContent = `${fmtPrice(ticker.last)} USDT`;
  $("#terminalChange").textContent = fmtPct(ticker.changePct || 0);
  $("#terminalChange").className = (ticker.changePct || 0) >= 0 ? "positive" : "negative";
  $("#terminalSource").textContent = source;
  $("#terminalUpdated").textContent = new Date().toLocaleTimeString("zh-CN");
  $("#ticketPrice").value = ticker.last;
  $("#midPrice").textContent = fmtPrice(ticker.last);
  renderTerminalChart(terminalSeries);
  renderTerminalWatch();
  updateTicketSummary();
}

function startTerminalSocket() {
  if (!("WebSocket" in window)) return;
  if (terminalSocket) {
    terminalSocket.close();
    terminalSocket = null;
  }
  window.clearInterval(terminalPingTimer);
  try {
    terminalSocket = new WebSocket("wss://ws.okx.com:8443/ws/v5/public");
    terminalSocket.addEventListener("open", () => {
      terminalSocket.send(JSON.stringify({
        op: "subscribe",
        args: [
          { channel: "tickers", instId: terminalSymbol },
          { channel: "trades", instId: terminalSymbol },
          { channel: "books5", instId: terminalSymbol }
        ]
      }));
      terminalPingTimer = window.setInterval(() => {
        if (terminalSocket?.readyState === WebSocket.OPEN) terminalSocket.send("ping");
      }, 25000);
    });
    terminalSocket.addEventListener("message", event => {
      if (event.data === "pong") return;
      let payload;
      try {
        payload = JSON.parse(event.data);
      } catch {
        return;
      }
      if (!payload.arg || !Array.isArray(payload.data)) return;
      if (payload.arg.channel === "tickers") {
        const row = payload.data[0];
        const last = Number(row.last || 0);
        const open = Number(row.open24h || last || 0);
        applyTerminalTicker({
          instId: row.instId,
          last,
          bidPx: Number(row.bidPx || 0),
          askPx: Number(row.askPx || 0),
          changePct: open ? ((last - open) / open) * 100 : 0
        });
      }
      if (payload.arg.channel === "books5") {
        const row = payload.data[0];
        terminalBook = {
          asks: (row.asks || []).map(item => ({ price: Number(item[0]), size: Number(item[1]), total: Number(item[1]) })),
          bids: (row.bids || []).map(item => ({ price: Number(item[0]), size: Number(item[1]), total: Number(item[1]) }))
        };
        renderBookRows($("#askRows"), [...terminalBook.asks].reverse(), "ask");
        renderBookRows($("#bidRows"), terminalBook.bids, "bid");
        if (terminalChartMode === "depth") renderTerminalChart(terminalSeries);
      }
      if (payload.arg.channel === "trades") {
        $("#terminalTrades").innerHTML = payload.data.slice(0, 18).map(trade => `
          <tr>
            <td>${new Date(Number(trade.ts)).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</td>
            <td class="${trade.side === "buy" ? "positive" : "negative"}">${trade.side === "buy" ? "买入" : "卖出"}</td>
            <td>${fmtPrice(trade.px)}</td>
            <td>${Number(trade.sz || 0).toFixed(4)}</td>
          </tr>
        `).join("");
      }
    });
    terminalSocket.addEventListener("close", () => {
      terminalSocket = null;
      window.clearInterval(terminalPingTimer);
    });
  } catch {
    terminalSocket = null;
    window.clearInterval(terminalPingTimer);
  }
}

async function loadTerminalSnapshot() {
  const data = await api(`/api/live/terminal?symbol=${encodeURIComponent(terminalSymbol)}&timeframe=${encodeURIComponent(terminalTimeframe)}`);
  renderTerminalSnapshot(data);
}

function setTerminalSymbol(symbol) {
  terminalSymbol = symbol;
  terminalSeries = [];
  if ($("#compareSymbol")) {
    if (!Array.from($("#compareSymbol").options).some(option => option.value === symbol)) {
      $("#compareSymbol").add(new Option(symbol, symbol));
    }
    $("#compareSymbol").value = symbol;
  }
  document.querySelectorAll("[data-terminal-symbol]").forEach(button => {
    button.classList.toggle("active", button.dataset.terminalSymbol === symbol);
  });
  renderTerminalWatch();
  startTerminalSocket();
  loadTerminalSnapshot().catch(error => showNotice(error.message, "error"));
  loadStrategyCompare().catch(() => {});
}

function restartTerminalTimer() {
  window.clearInterval(terminalTimer);
  terminalTimer = window.setInterval(() => loadTerminalSnapshot().catch(() => {}), 1000);
}

function updateTicketSummary() {
  const price = Number($("#ticketPrice")?.value || 0);
  const size = Number($("#ticketSize")?.value || 0);
  const leverage = Math.max(1, Number($("#leverageSelect")?.value || 1));
  const value = price * size;
  $("#orderValue").textContent = `${fmtMoney(value)} USDT`;
  $("#marginNeeded").textContent = `${fmtMoney(value / leverage)} USDT`;
}

function applyTicketPercent(percent) {
  const price = Number($("#ticketPrice").value || 0);
  const leverage = Math.max(1, Number($("#leverageSelect").value || 1));
  const capital = 10000 * (Number(percent) / 100);
  const notional = capital * leverage;
  if (price > 0) {
    $("#ticketSize").value = (notional / price).toFixed(4);
  }
  updateTicketSummary();
}

function sourceLabel(source) {
  if (source === "okx") return "OKX 实时数据";
  if (source === "mixed") return "部分 OKX / 部分回退";
  return "模拟回退数据";
}

function fmtPrice(value) {
  const number = Number(value || 0);
  if (number >= 1000) return number.toLocaleString("en-US", { maximumFractionDigits: 2 });
  if (number >= 1) return number.toLocaleString("en-US", { maximumFractionDigits: 4 });
  return number.toLocaleString("en-US", { maximumFractionDigits: 8 });
}

function renderSourceChip(source) {
  const chip = $("#marketSourceChip");
  chip.textContent = sourceLabel(source);
  chip.className = `chip ${source === "okx" ? "green" : source === "mixed" ? "amber" : ""}`;
}

async function loadTemplates() {
  const data = await api("/api/strategies/templates");
  strategyTemplates = data.templates;
  selectedTemplateId = appState?.strategy?.templateId || strategyTemplates[0]?.id || "ma_trend";
  renderTemplates();
  renderStrategyMarket();
}

function renderTemplates() {
  const box = $("#strategyTemplates");
  if (!box || !strategyTemplates.length) return;
  box.innerHTML = strategyTemplates.map(template => `
    <button class="template-card ${template.id === selectedTemplateId ? "active" : ""}" type="button" data-template-id="${template.id}">
      <div class="template-meta">
        <span class="tag ${template.beginner ? "green" : "amber"}">${template.beginner ? "新手可试" : "进阶"}</span>
        <span class="tag ${template.risk === "高" ? "red" : template.risk.includes("中") ? "amber" : "green"}">风险 ${template.risk}</span>
      </div>
      <h3>${template.name}</h3>
      <p>${template.summary}</p>
      <p><b>适合：</b>${template.bestFor}</p>
    </button>
  `).join("");

  box.querySelectorAll("[data-template-id]").forEach(button => {
    button.addEventListener("click", () => {
      selectedTemplateId = button.dataset.templateId;
      $("#strategyForm").templateId.value = selectedTemplateId;
      const template = strategyTemplates.find(item => item.id === selectedTemplateId);
      if (template) {
        $("#strategyRiskNote").className = `risk-note ${template.risk === "高" ? "red" : template.risk.includes("中") ? "amber" : ""}`;
        $("#strategyRiskNote").querySelector("b").textContent = `${template.name}：风险 ${template.risk}`;
        $("#strategyRiskNote").querySelector("p").textContent = template.warning;
      }
      renderTemplates();
    });
  });
}

function renderStrategyMarket() {
  const box = $("#strategyMarketGrid");
  if (!box || !strategyTemplates.length) return;
  box.innerHTML = strategyTemplates.map(template => `
    <article class="strategy-product">
      <div class="template-meta">
        <span class="tag ${template.beginner ? "green" : "amber"}">${template.beginner ? "新手可试" : "进阶"}</span>
        <span class="tag ${template.risk === "高" ? "red" : template.risk.includes("中") ? "amber" : "green"}">风险 ${template.risk}</span>
        <span class="tag blue">${template.category}</span>
      </div>
      <h3>${template.name}</h3>
      <p>${template.summary}</p>
      <p><b>适合：</b>${template.bestFor}</p>
      <p><b>注意：</b>${template.warning}</p>
      <button class="btn ${template.id === selectedTemplateId ? "primary" : ""}" type="button" data-adopt-template="${template.id}">
        ${template.id === selectedTemplateId ? "当前采用" : "设为候选"}
      </button>
    </article>
  `).join("");
  box.querySelectorAll("[data-adopt-template]").forEach(button => {
    button.addEventListener("click", () => adoptStrategy(button.dataset.adoptTemplate, terminalSymbol));
  });
}

async function loadStrategyCompare() {
  const symbol = $("#compareSymbol").value;
  const timeframe = $("#compareTimeframe").value;
  const data = await api(`/api/strategies/compare?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}`);
  renderStrategyCompare(data);
}

function renderStrategyCompare(data) {
  const best = data.results[0];
  $("#comparePair").textContent = data.symbol;
  $("#compareSource").textContent = sourceLabel(data.source);
  $("#compareTrend").textContent = fmtPct(data.market.trendPct);
  $("#compareTrend").className = data.market.trendPct >= 0 ? "positive" : "negative";
  $("#compareVolatility").textContent = `${Number(data.market.volatilityPct).toFixed(2)}%`;
  $("#compareBest").textContent = best?.name || "--";
  $("#strategyRankList").innerHTML = data.results.map((item, index) => `
    <article class="strategy-rank">
      <div class="rank-number">${index + 1}</div>
      <div>
        <h3>${item.name}</h3>
        <p>${item.summary}</p>
        <div class="template-meta">
          <span class="tag ${item.risk === "高" ? "red" : item.risk.includes("中") ? "amber" : "green"}">风险 ${item.risk}</span>
          <span class="tag blue">${item.signal}</span>
        </div>
      </div>
      <div class="rank-metric"><span>评分</span><b>${item.score}</b></div>
      <div class="rank-metric"><span>收益估算</span><b class="${item.returnPct >= 0 ? "positive" : "negative"}">${fmtPct(item.returnPct)}</b></div>
      <div class="rank-metric"><span>最大回撤</span><b>${item.maxDrawdownPct}%</b></div>
      <div class="rank-metric"><span>胜率</span><b>${item.winRatePct}%</b></div>
      <button class="btn ${item.adopted ? "primary" : "blue"}" type="button" data-compare-adopt="${item.id}">
        ${item.adopted ? "已采用" : "采用"}
      </button>
    </article>
  `).join("");
  $("#strategyRankList").querySelectorAll("[data-compare-adopt]").forEach(button => {
    button.addEventListener("click", () => adoptStrategy(button.dataset.compareAdopt, data.symbol, data.market.last));
  });
}

async function adoptStrategy(templateId, symbol = terminalSymbol, price = 0) {
  const data = await api("/api/strategies/adopt", {
    method: "POST",
    body: JSON.stringify({ templateId, symbol, price })
  });
  appState.strategy = data.strategy;
  appState.automation = data.automation;
  selectedTemplateId = templateId;
  renderTemplates();
  renderStrategyMarket();
  renderAutomation();
  renderTerminalPositions();
  await loadStrategyCompare().catch(() => {});
  showNotice(data.message);
}

function templateOptions(selectedId) {
  return strategyTemplates.map(template => `
    <option value="${template.id}" ${template.id === selectedId ? "selected" : ""}>${template.name}</option>
  `).join("");
}

function renderAutomation() {
  if (!appState?.automation) return;
  const automation = appState.automation;
  $("#automationRunning").textContent = automation.running ? "运行中" : "未运行";
  $("#automationMode").textContent = automation.dryRun ? "模拟" : "实盘";
  $("#refreshSecondsLabel").textContent = automation.refreshSeconds;
  renderAnchorRows();
  renderDecisionRows();
}

function renderAnchorRows() {
  const profiles = appState.automation.profiles || [];
  $("#anchorRows").innerHTML = profiles.map((profile, index) => `
    <div class="anchor-row" data-index="${index}">
      <label>品种
        <input name="symbol" value="${profile.symbol}" />
      </label>
      <label>策略
        <select name="templateId">${templateOptions(profile.templateId)}</select>
      </label>
      <label>中心锚点
        <input name="anchorPrice" type="number" step="0.0001" value="${profile.anchorPrice}" />
      </label>
      <label>上方锚点
        <input name="upperAnchor" type="number" step="0.0001" value="${profile.upperAnchor}" />
      </label>
      <label>下方锚点
        <input name="lowerAnchor" type="number" step="0.0001" value="${profile.lowerAnchor}" />
      </label>
      <label>资金上限
        <input name="maxCapitalPct" type="number" min="1" max="30" step="1" value="${profile.maxCapitalPct}" />
      </label>
      <label>启用
        <select name="enabled">
          <option value="true" ${profile.enabled ? "selected" : ""}>开启</option>
          <option value="false" ${!profile.enabled ? "selected" : ""}>关闭</option>
        </select>
      </label>
    </div>
  `).join("");
}

function collectAnchorProfiles() {
  return [...document.querySelectorAll(".anchor-row")].map(row => ({
    symbol: row.querySelector('[name="symbol"]').value.trim().toUpperCase(),
    templateId: row.querySelector('[name="templateId"]').value,
    anchorPrice: Number(row.querySelector('[name="anchorPrice"]').value),
    upperAnchor: Number(row.querySelector('[name="upperAnchor"]').value),
    lowerAnchor: Number(row.querySelector('[name="lowerAnchor"]').value),
    maxCapitalPct: Number(row.querySelector('[name="maxCapitalPct"]').value),
    enabled: row.querySelector('[name="enabled"]').value === "true"
  }));
}

function renderDecisionRows() {
  const rows = appState.automation.decisions || [];
  $("#decisionRows").innerHTML = rows.length ? rows.slice(0, 18).map(row => `
    <tr>
      <td>${new Date(row.time).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</td>
      <td>${row.symbol}</td>
      <td>${row.strategy}</td>
      <td>${row.action}</td>
      <td>${fmtPrice(row.price)}</td>
      <td>${row.reason}</td>
    </tr>
  `).join("") : `<tr><td colspan="6">暂无自动决策</td></tr>`;
}

async function loadAutomationStatus() {
  const data = await api("/api/automation/status");
  appState.automation = data.automation;
  renderAutomation();
}

async function loadLiveTicker() {
  const data = await api("/api/live/ticker?symbol=BTC-USDT");
  $("#btcLivePrice").textContent = `${fmtPrice(data.ticker.last)} USDT`;
  $("#btcLiveChange").textContent = `24h ${fmtPct(data.ticker.changePct)}，买一 ${fmtPrice(data.ticker.bidPx)} / 卖一 ${fmtPrice(data.ticker.askPx)}`;
  $("#btcLiveChange").className = data.ticker.changePct >= 0 ? "positive" : "negative";
  $("#btcSource").textContent = sourceLabel(data.source);
}

function restartLiveTimers() {
  window.clearInterval(liveTickerTimer);
  window.clearInterval(automationTimer);
  window.clearInterval(newsTimer);
  const seconds = Math.max(2, Number(appState?.automation?.refreshSeconds || 5));
  liveTickerTimer = window.setInterval(() => loadLiveTicker().catch(() => {}), seconds * 1000);
  if (appState?.automation?.running) {
    automationTimer = window.setInterval(() => runAutomationTick(false).catch(() => {}), seconds * 1000);
  }
  newsTimer = window.setInterval(() => loadNews().catch(() => {}), 60 * 1000);
}

async function saveAnchors() {
  const data = await api("/api/automation/config", {
    method: "POST",
    body: JSON.stringify({
      refreshSeconds: Number(appState.automation.refreshSeconds || 5),
      profiles: collectAnchorProfiles()
    })
  });
  appState.automation = data.automation;
  renderAutomation();
  restartLiveTimers();
  showNotice(data.message);
}

async function runAutomationTick(showMessage = true) {
  const data = await api("/api/automation/tick", { method: "POST", body: "{}" });
  appState.automation = data.automation;
  renderAutomation();
  if (showMessage) showNotice("自动交易引擎已完成一次模拟判断。");
}

async function loadNews() {
  const symbols = (appState?.automation?.profiles || []).map(item => item.symbol).join(",");
  const data = await api(`/api/news?symbols=${encodeURIComponent(symbols)}&limit=10`);
  $("#newsSourceChip").textContent = data.source === "rss" ? "实时 RSS" : "本地回退";
  $("#newsSourceChip").className = `chip ${data.source === "rss" ? "green" : "amber"}`;
  $("#newsList").innerHTML = data.news.map(item => `
    <article class="news-item">
      ${item.link ? `<a href="${item.link}" target="_blank" rel="noreferrer">${item.title}</a>` : `<b>${item.title}</b>`}
      <div class="news-meta">${item.source} · ${item.publishedAt || "时间未知"} · ${item.matched?.join(", ") || "市场"}</div>
      <p>${item.summary || ""}</p>
    </article>
  `).join("");
}

async function loadOkxMarkets() {
  const instType = $("#marketTypeSelect").value;
  const data = await api(`/api/okx/markets?instTypes=${encodeURIComponent(instType)}&limit=24`);
  const rows = data.groups[instType] || [];
  renderSourceChip(data.source);
  $("#marketUpdatedAt").textContent = `更新时间：${new Date(data.updatedAt).toLocaleString("zh-CN")}`;
  $("#marketRows").innerHTML = rows.length ? rows.map(row => `
    <tr>
      <td><button class="link-button" type="button" data-symbol="${row.instId}">${row.instId}</button></td>
      <td>${row.instTypeLabel}</td>
      <td>${fmtPrice(row.last)}</td>
      <td class="${row.changePct >= 0 ? "positive" : "negative"}">${fmtPct(row.changePct)}</td>
      <td>${fmtPrice(row.bidPx)} / ${fmtPrice(row.askPx)}</td>
      <td>${fmtPrice(row.low24h)} - ${fmtPrice(row.high24h)}</td>
      <td>${fmtMoney(row.volCcy24h)}</td>
    </tr>
  `).join("") : `<tr><td colspan="7">没有取到 ${instType} 行情。</td></tr>`;

  $("#marketRows").querySelectorAll("[data-symbol]").forEach(button => {
    button.addEventListener("click", async () => {
      const symbol = button.dataset.symbol;
      [$("#symbolSelect"), $("#strategyForm").symbol].forEach(select => {
        if (!Array.from(select.options).some(option => option.value === symbol)) {
          select.add(new Option(symbol, symbol));
        }
        select.value = symbol;
      });
      await loadMarket(symbol);
      showNotice(`已加载 ${symbol} 的 K 线。`);
    });
  });
}

function restartMarketRefreshTimer() {
  window.clearInterval(marketRefreshTimer);
  marketRefreshTimer = window.setInterval(() => {
    loadOkxMarkets().catch(() => {});
  }, 5000);
}

async function loadOkxInstruments() {
  const instType = $("#marketTypeSelect").value;
  const data = await api(`/api/okx/instruments?instType=${encodeURIComponent(instType)}&limit=30`);
  $("#instrumentRows").innerHTML = data.instruments.length ? data.instruments.map(row => `
    <tr>
      <td>${row.instId}</td>
      <td>${row.state}</td>
      <td>${row.quoteCcy || "-"} / ${row.settleCcy || "-"}</td>
      <td>${row.minSz || "-"}</td>
      <td>${row.tickSz || "-"}</td>
      <td>${row.ctVal ? `${row.ctVal} ${row.ctType || ""}` : "-"}</td>
    </tr>
  `).join("") : `<tr><td colspan="6">没有取到合约或币种信息。</td></tr>`;
}

async function loadHistoryFiles() {
  const data = await api("/api/history/files");
  $("#historyFiles").innerHTML = data.files.length ? data.files.map(file => `
    <tr>
      <td>${file.file}</td>
      <td>${(file.size / 1024 / 1024).toFixed(2)} MB</td>
      <td>${new Date(file.updatedAt).toLocaleString("zh-CN")}</td>
    </tr>
  `).join("") : `<tr><td colspan="3">暂无历史数据文件</td></tr>`;
}

async function importHistoryData() {
  const body = {
    symbol: $("#historySymbol").value,
    timeframe: $("#historyTimeframe").value,
    years: Number($("#historyYears").value)
  };
  $("#historyImportStatus").textContent = "正在导入，请稍等...";
  const data = await api("/api/history/import", { method: "POST", body: JSON.stringify(body) });
  const result = data.result;
  $("#historyImportStatus").textContent = `已导入 ${result.symbol} ${result.timeframe} ${result.years} 年数据：${result.count} 根K线，来源 ${sourceLabel(result.source)}，文件 ${result.fileName}${result.error ? `；回退原因：${result.error}` : ""}`;
  await loadHistoryFiles();
}

function setView(view = "dashboard") {
  if (view === "history") view = "account";
  const requestedView = historyViews.has(view) ? view : view;
  const knownView = viewTitles[requestedView] ? requestedView : "dashboard";
  const overview = knownView === "dashboard";
  const historyMode = historyViews.has(knownView);
  document.body.classList.toggle("single-view", !overview);

  document.querySelectorAll(".app-section").forEach(section => {
    if (overview) {
      section.hidden = false;
      return;
    }
    if (historyMode) {
      section.hidden = !(section.id === "history" || section.id === knownView);
      return;
    }
    section.hidden = section.id !== knownView;
  });

  document.querySelectorAll(".nav a[data-view]").forEach(link => {
    link.classList.toggle("active", historyMode ? link.dataset.view === "history" : link.dataset.view === knownView);
  });

  document.querySelectorAll(".history-tab").forEach(button => {
    button.classList.toggle("active", button.dataset.historyTarget === (historyMode ? knownView : "account"));
  });

  $(".top-title h1").textContent = overview ? "交易首页" : historyMode ? `交易历史 · ${viewTitles[knownView]}` : viewTitles[knownView];
  if (window.location.hash !== `#${knownView}`) {
    history.replaceState(null, "", `#${knownView}`);
  }
}

async function loadState() {
  const health = await api("/api/health");
  $("#healthText").textContent = `${health.name} 已运行，本地服务正常`;
  const data = await api("/api/state");
  appState = data.state;
  renderState();
  await loadTemplates();
  renderAutomation();
  renderTerminalWatch();
  await loadTerminalSnapshot().catch(() => {});
  startTerminalSocket();
  updateTicketSummary();
  await loadStrategyCompare().catch(error => showNotice(`策略对比失败：${error.message}`, "error"));
  await loadMarket(appState.strategy.symbol);
  await loadLiveTicker().catch(() => {});
  await loadOkxMarkets().catch(error => showNotice(`行情加载失败：${error.message}`, "error"));
  await loadOkxInstruments().catch(error => showNotice(`合约列表加载失败：${error.message}`, "error"));
  await loadHistoryFiles().catch(() => {});
  await loadNews().catch(error => showNotice(`资讯加载失败：${error.message}`, "error"));
  restartLiveTimers();
  restartMarketRefreshTimer();
  restartTerminalTimer();
}

async function loadMarket(symbol) {
  const data = await api(`/api/market?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(appState?.strategy?.timeframe || "1h")}&limit=180`);
  $("#chartTitle").textContent = `${symbol} ${sourceLabel(data.source)}`;
  renderLineChart($("#marketChart"), data.candles.map(item => item.close));
}

function renderState() {
  const state = appState;
  selectedTemplateId = state.strategy.templateId || selectedTemplateId;
  $("#equityValue").textContent = `${fmtMoney(state.dashboard.equity)} USDT`;
  $("#dailyPnl").textContent = `今日 ${state.dashboard.dailyPnl >= 0 ? "+" : ""}${fmtMoney(state.dashboard.dailyPnl)} USDT`;
  $("#allocationValue").textContent = `${state.dashboard.allocation}%`;
  $("#runningMini").textContent = state.paper.running ? "运行中" : "未运行";
  $("#strategyCount").textContent = `${state.paper.running ? 2 : 0} / 5`;
  $("#strategyName").textContent = state.paper.running ? `${state.strategy.name}、现货网格` : "等待启动";
  $("#riskLevel").textContent = state.risk.paused ? "已暂停" : state.dashboard.riskLevel;
  $("#pauseState").textContent = state.risk.paused ? "已暂停" : "未暂停";
  $("#paperStep").textContent = `第 ${state.paper.day} 天`;
  $("#accountStep").textContent = state.account.connected ? "已连接" : "未连接";
  $("#accountStatus").textContent = state.account.connected ? "连接正常" : "本地安全";
  $("#modeChip").textContent = state.account.environment === "demo" ? "模拟盘" : "实盘预览";
  $("#estimatedLoss").textContent = `${fmtMoney(10000 * state.strategy.allocationPct / 100 * state.strategy.stopLossPct / 100)} USDT`;

  const form = $("#strategyForm");
  [form.symbol, $("#symbolSelect")].forEach(select => {
    if (!Array.from(select.options).some(option => option.value === state.strategy.symbol)) {
      select.add(new Option(state.strategy.symbol, state.strategy.symbol));
    }
  });
  form.templateId.value = selectedTemplateId;
  form.symbol.value = state.strategy.symbol;
  form.shortMa.value = state.strategy.shortMa;
  form.longMa.value = state.strategy.longMa;
  form.allocationPct.value = state.strategy.allocationPct;
  form.stopLossPct.value = state.strategy.stopLossPct;
  form.timeframe.value = state.strategy.timeframe;
  $("#symbolSelect").value = state.strategy.symbol;

  $("#positionRows").innerHTML = `
    <tr><td>${state.strategy.symbol}</td><td>${state.strategy.allocationPct}%</td><td class="positive">+1.2%</td></tr>
    <tr><td>ETH-USDT</td><td>8%</td><td class="negative">-0.4%</td></tr>
    <tr><td>SOL-USDT</td><td>0%</td><td>未持仓</td></tr>
  `;

  $("#unlockRows").innerHTML = `
    <tr><td>模拟观察 7 天</td><td><span class="tag ${state.paper.day >= 7 ? "green" : "amber"}">${state.paper.day >= 7 ? "通过" : "未完成"}</span></td></tr>
    <tr><td>最大回撤小于 10%</td><td><span class="tag green">通过</span></td></tr>
    <tr><td>止损已开启</td><td><span class="tag green">通过</span></td></tr>
    <tr><td>实盘交易功能</td><td><span class="tag red">锁定</span></td></tr>
  `;

  renderPaperEvents();
  renderRiskCards();
  renderAutomation();
  renderReview();
}

function renderPaperEvents() {
  $("#paperEvents").innerHTML = appState.paper.events.map(event => `
    <article class="event">
      <time>${event.time}</time>
      <div>
        <strong>${event.title}</strong>
        <span>${event.detail}</span>
      </div>
      <span class="tag ${event.tone || "green"}">${event.result}</span>
    </article>
  `).join("");
}

function renderRiskCards() {
  const risk = appState.risk;
  const cards = [
    ["每日最大亏损", `当前 ${risk.dailyLossPct}%，阈值 ${risk.dailyLossLimitPct}%`, risk.dailyLossPct / risk.dailyLossLimitPct * 100, ""],
    ["单策略资金", `当前 ${risk.strategyCapitalPct}%，新手建议不超过 10%`, risk.strategyCapitalPct / 30 * 100, ""],
    ["总资金使用", `当前 ${risk.totalCapitalPct}%，上限 ${risk.maxCapitalPct}%`, risk.totalCapitalPct / risk.maxCapitalPct * 100, ""],
    ["连续亏损", `当前 ${risk.losingStreak} 次，达到 ${risk.losingStreakLimit} 次暂停`, risk.losingStreak / risk.losingStreakLimit * 100, "amber"],
    ["API 状态", `最近同步延迟 ${risk.apiLatencyMs}ms`, Math.min(100, risk.apiLatencyMs / 1000 * 100), ""],
    ["合约杠杆", risk.leverageLocked ? "已锁定，新手模式不开放高杠杆" : "已开放", risk.leverageLocked ? 0 : 50, "red"]
  ];

  $("#riskCards").innerHTML = cards.map(([title, text, pct, tone]) => `
    <article class="risk-card">
      <b>${title}</b>
      <p>${text}</p>
      <div class="bar ${tone}"><span style="width:${Math.max(0, Math.min(100, pct)).toFixed(0)}%"></span></div>
    </article>
  `).join("");
}

function renderReview() {
  $("#reviewRows").innerHTML = appState.review.rows.map(row => `
    <tr><td>${row[0]}</td><td>${row[1]}</td><td>${row[2]}</td><td>${row[3]}</td></tr>
  `).join("");
  $("#reviewSummary").querySelector("p").textContent = appState.review.summary;
}

async function saveStrategy() {
  const form = $("#strategyForm");
  const body = {
    templateId: form.templateId.value || selectedTemplateId,
    symbol: form.symbol.value,
    shortMa: Number(form.shortMa.value),
    longMa: Number(form.longMa.value),
    allocationPct: Number(form.allocationPct.value),
    stopLossPct: Number(form.stopLossPct.value),
    timeframe: form.timeframe.value
  };
  if (body.shortMa >= body.longMa) {
    showNotice("短期均线必须小于长期均线。", "error");
    return false;
  }
  const data = await api("/api/strategy", { method: "POST", body: JSON.stringify(body) });
  appState.strategy = data.strategy;
  appState.risk = data.risk;
  appState.dashboard.allocation = data.risk.totalCapitalPct;
  selectedTemplateId = data.strategy.templateId || selectedTemplateId;
  renderState();
  renderTemplates();
  await loadMarket(appState.strategy.symbol);
  showNotice("策略配置已保存。");
  return true;
}

async function runBacktest() {
  const ok = await saveStrategy();
  if (!ok) return;
  const data = await api("/api/backtest", {
    method: "POST",
    body: JSON.stringify({
      symbol: appState.strategy.symbol,
      shortMa: appState.strategy.shortMa,
      longMa: appState.strategy.longMa,
      allocationPct: appState.strategy.allocationPct,
      stopLossPct: appState.strategy.stopLossPct,
      timeframe: appState.strategy.timeframe,
      initialBalance: 10000
    })
  });
  lastBacktest = data;
  $("#returnPct").textContent = fmtPct(data.metrics.returnPct);
  $("#returnPct").className = data.metrics.returnPct >= 0 ? "positive" : "negative";
  $("#finalEquity").textContent = `最终权益 ${fmtMoney(data.metrics.finalEquity)} USDT`;
  $("#drawdownPct").textContent = `-${Number(data.metrics.maxDrawdownPct).toFixed(2)}%`;
  $("#winRatePct").textContent = `${data.metrics.winRatePct}%`;
  $("#tradeCount").textContent = `交易次数 ${data.metrics.tradeCount}`;
  $("#feeImpact").textContent = `${fmtMoney(data.metrics.feeImpact)} USDT`;
  $("#losingStreak").textContent = `最大连续亏损 ${data.metrics.maxLosingStreak} 次`;
  $("#backtestNote").textContent = data.beginnerNote;
  if (data.source === "mock" && data.sourceError) {
    $("#backtestNote").textContent = `${data.beginnerNote} 数据源回退：${data.sourceError}`;
  }
  $("#backtestStep").textContent = "已完成";
  renderLineChart($("#equityChart"), data.equityCurve.map(item => item.equity), "#2169b5", "rgba(33,105,181,0.12)");
  $("#tradeRows").innerHTML = data.trades.length
    ? data.trades.map(trade => `
      <tr>
        <td>${new Date(trade.time).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })}</td>
        <td>${trade.side}</td>
        <td>${fmtMoney(trade.price)}</td>
        <td>${trade.reason}</td>
        <td>${trade.pnl === null ? "-" : fmtMoney(trade.pnl)}</td>
      </tr>
    `).join("")
    : `<tr><td colspan="5">当前参数没有产生交易，请调整均线或时间范围。</td></tr>`;
  showNotice("回测完成，可以进入模拟盘观察。");
}

function bindEvents() {
  document.querySelectorAll(".nav a[data-view]").forEach(link => {
    link.addEventListener("click", event => {
      event.preventDefault();
      setView(link.dataset.view);
    });
  });

  document.querySelectorAll("[data-history-target]").forEach(button => {
    button.addEventListener("click", () => setView(button.dataset.historyTarget));
  });

  window.addEventListener("hashchange", () => {
    setView((window.location.hash || "#dashboard").slice(1));
  });

  $("#symbolSelect").addEventListener("change", event => loadMarket(event.target.value).catch(error => showNotice(error.message, "error")));
  document.querySelectorAll("[data-terminal-symbol]").forEach(button => {
    button.addEventListener("click", () => setTerminalSymbol(button.dataset.terminalSymbol));
  });
  document.querySelectorAll("[data-chart-mode]").forEach(button => {
    button.addEventListener("click", () => {
      terminalChartMode = button.dataset.chartMode;
      document.querySelectorAll("[data-chart-mode]").forEach(item => item.classList.toggle("active", item === button));
      renderTerminalChart(terminalSeries);
    });
  });
  document.querySelectorAll("[data-terminal-timeframe]").forEach(button => {
    button.addEventListener("click", () => {
      terminalTimeframe = button.dataset.terminalTimeframe;
      document.querySelectorAll("[data-terminal-timeframe]").forEach(item => item.classList.toggle("active", item === button));
      terminalSeries = [];
      loadTerminalSnapshot().catch(error => showNotice(error.message, "error"));
    });
  });
  ["ticketPrice", "ticketSize", "leverageSelect"].forEach(id => {
    $(`#${id}`).addEventListener("input", updateTicketSummary);
    $(`#${id}`).addEventListener("change", updateTicketSummary);
  });
  document.querySelectorAll("[data-ticket-pct]").forEach(button => {
    button.addEventListener("click", () => applyTicketPercent(button.dataset.ticketPct));
  });
  $("#paperOrderBtn").addEventListener("click", () => {
    const price = Number($("#ticketPrice").value || 0);
    const leverage = Number($("#leverageSelect").value || 1);
    const marginMode = $("#marginMode").value === "cross" ? "全仓" : "逐仓";
    const orderType = $("#ticketOrderType").value;
    const event = {
      time: new Date().toISOString(),
      symbol: terminalSymbol,
      strategy: "手动模拟单",
      action: "提交模拟单",
      price,
      reason: `${marginMode} ${leverage}x ${orderType}，真实下单仍锁定`,
      dryRun: true
    };
    appState.automation.decisions = [event, ...(appState.automation.decisions || [])].slice(0, 80);
    renderDecisionRows();
    renderTerminalPositions();
    showNotice("模拟单已记录，不会提交 OKX。");
  });
  $("#marketTypeSelect").addEventListener("change", async () => {
    try {
      await loadOkxMarkets();
      await loadOkxInstruments();
    } catch (error) {
      showNotice(error.message, "error");
    }
  });
  $("#refreshMarketBtn").addEventListener("click", () => loadOkxMarkets().then(() => showNotice("行情已刷新。")).catch(error => showNotice(error.message, "error")));
  $("#refreshInstrumentsBtn").addEventListener("click", () => loadOkxInstruments().then(() => showNotice("合约与币种信息已刷新。")).catch(error => showNotice(error.message, "error")));
  $("#importHistoryBtn").addEventListener("click", () => importHistoryData().then(() => showNotice("历史数据导入完成。")).catch(error => {
    $("#historyImportStatus").textContent = `导入失败：${error.message}`;
    showNotice(error.message, "error");
  }));
  $("#refreshStrategyMarketBtn").addEventListener("click", () => {
    renderStrategyMarket();
    showNotice("策略广场已刷新。");
  });
  $("#runCompareBtn").addEventListener("click", () => loadStrategyCompare().then(() => showNotice("策略对比已更新。")).catch(error => showNotice(error.message, "error")));
  $("#compareSymbol").addEventListener("change", () => {
    setTerminalSymbol($("#compareSymbol").value);
  });
  $("#compareTimeframe").addEventListener("change", () => loadStrategyCompare().catch(error => showNotice(error.message, "error")));
  $("#saveAnchorsBtn").addEventListener("click", () => saveAnchors().catch(error => showNotice(error.message, "error")));
  $("#startAutomationBtn").addEventListener("click", async () => {
    try {
      await saveAnchors();
      const data = await api("/api/automation/start", { method: "POST", body: "{}" });
      appState.automation = data.automation;
      renderAutomation();
      restartLiveTimers();
      showNotice("自动交易模拟已启动。");
    } catch (error) {
      showNotice(error.message, "error");
    }
  });
  $("#stopAutomationBtn").addEventListener("click", async () => {
    try {
      const data = await api("/api/automation/stop", { method: "POST", body: "{}" });
      appState.automation = data.automation;
      renderAutomation();
      restartLiveTimers();
      showNotice("自动交易模拟已停止。");
    } catch (error) {
      showNotice(error.message, "error");
    }
  });
  $("#runAutomationTickBtn").addEventListener("click", () => runAutomationTick(true).catch(error => showNotice(error.message, "error")));
  $("#refreshNewsBtn").addEventListener("click", () => loadNews().then(() => showNotice("资讯已刷新。")).catch(error => showNotice(error.message, "error")));

  $("#accountForm").addEventListener("submit", async event => {
    event.preventDefault();
    const form = event.currentTarget;
    try {
      const data = await api("/api/account/test", {
        method: "POST",
        body: JSON.stringify({
          apiKey: form.apiKey.value,
          environment: form.environment.value,
          tradePermission: form.tradePermission.checked
        })
      });
      appState.account = data.account;
      renderState();
      showNotice(data.message);
    } catch (error) {
      showNotice(error.message, "error");
    }
  });

  $("#testAccountBtn").addEventListener("click", () => $("#accountForm").requestSubmit());
  $("#strategyForm").addEventListener("submit", event => {
    event.preventDefault();
    saveStrategy().catch(error => showNotice(error.message, "error"));
  });
  $("#runBacktestBtn").addEventListener("click", () => runBacktest().catch(error => showNotice(error.message, "error")));
  $("#backtestAgainBtn").addEventListener("click", () => runBacktest().catch(error => showNotice(error.message, "error")));

  $("#startPaperBtn").addEventListener("click", async () => {
    try {
      const data = await api("/api/paper/start", { method: "POST", body: "{}" });
      appState = data.state;
      renderState();
      showNotice("模拟策略已启动。");
    } catch (error) {
      showNotice(error.message, "error");
    }
  });

  $("#paperTickBtn").addEventListener("click", async () => {
    try {
      const data = await api("/api/paper/tick", { method: "POST", body: "{}" });
      appState = data.state;
      renderState();
      showNotice("已推进一次模拟行情。");
    } catch (error) {
      showNotice(error.message, "error");
    }
  });

  $("#pauseAllBtn").addEventListener("click", async () => {
    try {
      const data = await api("/api/risk/pause-all", { method: "POST", body: "{}" });
      appState = data.state;
      renderState();
      showNotice("已暂停全部策略。");
    } catch (error) {
      showNotice(error.message, "error");
    }
  });

  $("#resumeDemoBtn").addEventListener("click", async () => {
    try {
      const data = await api("/api/risk/resume-demo", { method: "POST", body: "{}" });
      appState = data.state;
      renderState();
      showNotice("模拟盘已恢复。");
    } catch (error) {
      showNotice(error.message, "error");
    }
  });

  $("#exportReviewBtn").addEventListener("click", () => {
    const metrics = lastBacktest?.metrics;
    $("#reviewText").value = [
      "OKX Quant Desk 今日复盘",
      `模拟权益：${fmtMoney(appState.dashboard.equity)} USDT`,
      `今日盈亏：${fmtMoney(appState.dashboard.dailyPnl)} USDT`,
      `策略：${appState.strategy.name} / ${appState.strategy.symbol}`,
      metrics ? `回测收益：${fmtPct(metrics.returnPct)}，最大回撤：-${metrics.maxDrawdownPct}%` : "回测：尚未在本次页面会话中运行",
      `结论：${appState.review.summary}`,
      "提醒：当前版本仍锁定实盘，不会真实下单。"
    ].join("\n");
    showNotice("复盘文本已生成。");
  });
}

bindEvents();
setView((window.location.hash || "#dashboard").slice(1));
loadState().catch(error => showNotice(error.message, "error"));
