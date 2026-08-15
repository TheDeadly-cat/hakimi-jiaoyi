const http = require("http");
const { ensureElectron } = require("./electron-smoke-runtime");

const DEBUG_PORT = Number(process.env.HAKIMI_DEBUG_PORT || 9333);
const BASE = `http://127.0.0.1:${DEBUG_PORT}`;
const STOCKS = (process.env.HAKIMI_CHART_STOCKS || "NVDA,AAPL,TSLA").split(",").map((item) => item.trim()).filter(Boolean);
let smokeRuntime = null;

function getJson(path) {
  return new Promise((resolve, reject) => {
    const req = http.get(`${BASE}${path}`, { timeout: 2500 }, (res) => {
      let body = "";
      res.setEncoding("utf8");
      res.on("data", (chunk) => {
        body += chunk;
      });
      res.on("end", () => {
        try {
          resolve(JSON.parse(body));
        } catch (error) {
          reject(error);
        }
      });
    });
    req.on("timeout", () => req.destroy(new Error("timeout")));
    req.on("error", reject);
  });
}

async function waitForTarget() {
  const deadline = Date.now() + 20000;
  while (Date.now() < deadline) {
    try {
      const targets = await getJson("/json/list");
      const target = targets.find((item) => item.type === "page" && /127\.0\.0\.1:8765/.test(item.url || ""));
      if (target?.webSocketDebuggerUrl) return target;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error("Electron page target not found. Start the desktop shell with remote debugging before running this smoke test.");
}

function cdp(wsUrl) {
  const socket = new WebSocket(wsUrl);
  let id = 0;
  const pending = new Map();
  socket.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (!message.id || !pending.has(message.id)) return;
    const { resolve, reject } = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) reject(new Error(message.error.message));
    else resolve(message.result);
  };
  return new Promise((resolve, reject) => {
    socket.onerror = () => reject(new Error("WebSocket error"));
    socket.onopen = () => {
      resolve({
        send(method, params = {}) {
          const requestId = ++id;
          socket.send(JSON.stringify({ id: requestId, method, params }));
          return new Promise((requestResolve, requestReject) => {
            pending.set(requestId, { resolve: requestResolve, reject: requestReject });
          });
        },
        close() {
          socket.close();
        },
      });
    };
  });
}

async function evaluate(client, expression) {
  const result = await client.send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.text || "Runtime exception");
  }
  return result.result.value;
}

async function waitForAppReady(client, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  let last = {};
  while (Date.now() < deadline) {
    last = await evaluate(client, `(() => ({
      readyState: document.readyState,
      selectSymbolReady: typeof selectSymbol === "function",
      marketRowCount: document.querySelectorAll("#marketList .market-row").length,
      chartPresent: Boolean(document.querySelector("#priceChart")),
      viewReady: Array.from(document.body.classList).some((item) => item.startsWith("view-"))
    }))()`);
    if (last.readyState === "complete" && last.selectSymbolReady && last.marketRowCount >= 3 && last.chartPresent && last.viewReady) {
      return last;
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Application did not become ready for chart checks: ${JSON.stringify(last)}`);
}

async function waitForChart(client, symbol, timeoutMs = 25000) {
  const deadline = Date.now() + timeoutMs;
  let last = {};
  while (Date.now() < deadline) {
    last = await evaluate(client, `(() => {
      const rows = (state?.candles || []).slice(-200);
      const wickRatios = rows.flatMap((row) => {
        const open = Number(row.open);
        const high = Number(row.high);
        const low = Number(row.low);
        const close = Number(row.close);
        const bodyHigh = Math.max(open, close, 1e-9);
        const bodyLow = Math.max(Math.min(open, close), 1e-9);
        return [high / bodyHigh, bodyLow / Math.max(low, 1e-9)];
      }).filter(Number.isFinite);
      return {
        symbol: document.querySelector(".market-row.active")?.dataset?.symbol || "",
        rows: Number(document.querySelector("#priceChart")?.dataset?.candleCount || 0),
        totalRows: Number(document.querySelector("#priceChart")?.dataset?.totalCandles || 0),
        chartDataSymbol: document.querySelector("#priceChart")?.dataset?.chartSymbol || "",
        status: document.querySelector("#chartStatus")?.textContent || "",
        source: document.querySelector("#chartQualitySource")?.textContent || "",
        freshness: document.querySelector("#chartQualityFreshness")?.textContent || "",
        mode: document.querySelector("#chartQualityMode")?.textContent || "",
        activeBar: document.querySelector("#timeframeTabs button.active")?.dataset?.bar || "",
        activeSession: document.querySelector("#stockSessionTabs button.active")?.dataset?.stockSession || "",
        canvasWidth: document.querySelector("#priceChart")?.width || 0,
        canvasHeight: document.querySelector("#priceChart")?.height || 0,
        maxWickRatio: Math.max(0, ...wickRatios)
      };
    })()`);
    const qualityText = `${last.status} ${last.source} ${last.mode}`;
    const authoritative = !/预览|旧缓存|STALE|seed|offline|等待真实数据/i.test(qualityText);
    if (last.symbol === symbol && last.rows >= 30 && authoritative && (!last.chartDataSymbol || last.chartDataSymbol === symbol) && last.canvasWidth > 0 && last.canvasHeight > 0 && last.maxWickRatio <= 2) {
      return last;
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`Chart did not load enough candles for ${symbol}: ${JSON.stringify(last)}`);
}

async function waitForStockVolumeSemantics(client, symbol, timeoutMs = 10000) {
  const deadline = Date.now() + timeoutMs;
  let last = {};
  while (Date.now() < deadline) {
    last = await evaluate(client, `(() => {
      const market = typeof currentMarket === "function" ? currentMarket() : {};
      const baseVolume = Number(market?.baseVolume24h);
      if (typeof renderSideInsights === "function") renderSideInsights();
      const ticker = document.querySelector('.market-ticker-row[data-symbol="${symbol}"]');
      const tickerCells = ticker?.querySelectorAll(':scope > span') || [];
      const sideVolumeRow = Array.from(document.querySelectorAll('#sideInsightRows .side-insight-row'))
        .find((row) => row.querySelector('span')?.textContent?.trim() === 'Volume');
      const latestQuote = document.querySelector('#trades .trade-row.latest')?.textContent?.trim() || "";
      return {
        symbol: document.querySelector("#activeSymbol")?.textContent?.trim() || "",
        label: document.querySelector("#vol24hLabel")?.textContent?.trim() || "",
        displayed: document.querySelector("#vol24h")?.textContent?.trim() || "",
        tickerDisplayed: tickerCells[3]?.textContent?.trim() || "",
        sideDisplayed: sideVolumeRow?.querySelector('strong')?.textContent?.trim() || "",
        latestQuote,
        baseVolume,
        expected: Number.isFinite(baseVolume) && typeof compact === "function" ? compact(baseVolume) : ""
      };
    })()`);
    if (
      last.symbol === symbol
      && last.label === "当日成交量"
      && last.baseVolume > 0
      && last.displayed === last.expected
      && last.tickerDisplayed === last.expected
      && last.sideDisplayed === last.expected
      && last.latestQuote.includes(last.expected)
    ) {
      return last;
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Stock volume semantics did not settle for ${symbol}: ${JSON.stringify(last)}`);
}

async function waitForAnomalySelection(client, symbol, timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs;
  let last = {};
  while (Date.now() < deadline) {
    last = await evaluate(client, `(() => ({
      activeSymbol: document.querySelector("#activeSymbol")?.textContent?.trim() || "",
      selectedSymbol: state?.selectedAnomaly?.symbol || "",
      activeRadarSymbol: document.querySelector(".anomaly-row.active")?.dataset?.symbol || "",
      prompt: document.querySelector("#anomalyPromptPreview")?.textContent || ""
    }))()`);
    if (last.activeSymbol === symbol && last.selectedSymbol === symbol && last.activeRadarSymbol === symbol && last.prompt.includes(symbol)) {
      return last;
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Anomaly selection did not follow ${symbol}: ${JSON.stringify(last)}`);
}

async function waitForSession(client, symbol, session, timeoutMs = 25000) {
  const deadline = Date.now() + timeoutMs;
  let last = {};
  while (Date.now() < deadline) {
    last = await evaluate(client, `(() => ({
      symbol: document.querySelector(".market-row.active")?.dataset?.symbol || "",
      chartDataSymbol: document.querySelector("#priceChart")?.dataset?.chartSymbol || "",
      rows: Number(document.querySelector("#priceChart")?.dataset?.candleCount || 0),
      activeBar: document.querySelector("#timeframeTabs button.active")?.dataset?.bar || "",
      activeSession: document.querySelector("#stockSessionTabs button.active")?.dataset?.stockSession || "",
      status: document.querySelector("#chartStatus")?.textContent || "",
      source: document.querySelector("#chartQualitySource")?.textContent || "",
      mode: document.querySelector("#chartQualityMode")?.textContent || ""
    }))()`);
    const qualityText = `${last.status} ${last.source} ${last.mode}`;
    const authoritative = !/预览|旧缓存|STALE|seed|offline|等待真实数据/i.test(qualityText);
    if (
      last.symbol === symbol
      && last.chartDataSymbol === symbol
      && last.rows >= 1
      && last.activeBar === "1m"
      && last.activeSession === session
      && last.status.includes(`/ ${session === "regular" ? "盘中" : "盘后"} /`)
      && authoritative
    ) {
      return last;
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`Chart session did not settle for ${symbol}/${session}: ${JSON.stringify(last)}`);
}

async function main() {
  smokeRuntime = await ensureElectron(getJson, DEBUG_PORT);
  let client = null;
  try {
    const target = await waitForTarget();
    client = await cdp(target.webSocketDebuggerUrl);
    await client.send("Runtime.enable");
    await waitForAppReady(client);
    const results = [];
    for (const symbol of STOCKS) {
      await evaluate(client, `(() => {
        if (typeof selectSymbol === "function") {
          selectSymbol(${JSON.stringify(symbol)}, { focusChart: true, force: true });
          return;
        }
        document.querySelector('[data-interface-view="trade"]')?.click();
        document.querySelector('#marketCategoryTabs [data-category="stocks"]')?.click();
        document.querySelector('#marketList .market-row[data-symbol="${symbol}"]')?.click();
      })()`);
      const chart = await waitForChart(client, symbol);
      const volumeSemantics = await waitForStockVolumeSemantics(client, symbol);
      results.push({ ...chart, volumeSemantics });
    }
    await evaluate(client, `(async () => {
      for (const symbol of ${JSON.stringify(STOCKS)}) {
        selectSymbol(symbol, { focusChart: true, force: true });
        await new Promise((resolve) => setTimeout(resolve, 90));
      }
    })()`);
    const rapidSwitch = await waitForChart(client, STOCKS[STOCKS.length - 1]);
    const crossSymbolGuard = await evaluate(client, `(() => {
      const activeSymbol = state.symbol;
      const beforePrice = Number(state.lastPrice || 0);
      const beforeCandle = { ...(state.candles.at(-1) || {}) };
      updateTicker({ instId: "BTC-USDT", last: "62758.20", high24h: "63150", low24h: "62268", ts: Date.now() }, "STALE_TEST");
      const afterCandle = { ...(state.candles.at(-1) || {}) };
      return {
        activeSymbol,
        beforePrice,
        afterPrice: Number(state.lastPrice || 0),
        beforeCandle,
        afterCandle,
        unchanged: beforePrice === Number(state.lastPrice || 0)
          && JSON.stringify(beforeCandle) === JSON.stringify(afterCandle)
      };
    })()`);
    if (!crossSymbolGuard.unchanged) {
      throw new Error(`Stale cross-symbol quote mutated active stock chart: ${JSON.stringify(crossSymbolGuard)}`);
    }
    const hitTest = await evaluate(client, `(() => {
      const button = document.querySelector('#stockSessionTabs button[data-stock-session="post"]');
      const rect = button.getBoundingClientRect();
      const hit = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
      hit?.click();
      return {
        buttonHit: hit === button || button.contains(hit),
        hitTag: hit?.tagName || "",
        hitText: hit?.textContent || ""
      };
    })()`);
    if (!hitTest.buttonHit) {
      throw new Error(`Stock session button is covered: ${JSON.stringify(hitTest)}`);
    }
    const postSession = await waitForSession(client, STOCKS[STOCKS.length - 1], "post");
    await evaluate(client, `document.querySelector('#stockSessionTabs button[data-stock-session="regular"]')?.click()`);
    const regularSession = await waitForSession(client, STOCKS[STOCKS.length - 1], "regular");
    const anomalySymbol = STOCKS.includes("AAPL") ? "AAPL" : STOCKS[0];
    await evaluate(client, `selectSymbol(${JSON.stringify(anomalySymbol)}, { focusChart: false, force: true })`);
    await evaluate(client, `(async () => {
      setInterfaceView("research");
      await loadAnomalyRadar(false, runtime.symbolVersion, { force: true });
    })()`);
    const anomalySelection = await waitForAnomalySelection(client, anomalySymbol);
    console.log(JSON.stringify({ ok: true, checked: results, rapidSwitch, crossSymbolGuard, hitTest, sessions: [postSession, regularSession], anomalySelection }, null, 2));
  } finally {
    client?.close();
    smokeRuntime?.stop();
  }
}

main().catch((error) => {
  smokeRuntime?.stop();
  console.error(error.message);
  process.exit(1);
});
