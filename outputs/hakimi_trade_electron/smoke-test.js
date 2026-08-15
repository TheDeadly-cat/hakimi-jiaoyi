const http = require("http");
const { ensureElectron } = require("./electron-smoke-runtime");

const DEBUG_PORT = Number(process.env.HAKIMI_DEBUG_PORT || 9333);
const BASE = `http://127.0.0.1:${DEBUG_PORT}`;
let smokeRuntime = null;

function getJson(path) {
  return new Promise((resolve, reject) => {
    const req = http.get(`${BASE}${path}`, { timeout: 2000 }, (res) => {
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
  throw new Error("Electron page target not found");
}

function cdp(wsUrl) {
  const socket = new WebSocket(wsUrl);
  let id = 0;
  const pending = new Map();
  socket.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) reject(new Error(message.error.message));
      else resolve(message.result);
    }
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

async function waitForEval(client, expression, timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs;
  let lastValue;
  while (Date.now() < deadline) {
    lastValue = await evaluate(client, expression);
    if (lastValue) return lastValue;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  return lastValue;
}

async function main() {
  smokeRuntime = await ensureElectron(getJson, DEBUG_PORT);
  let client = null;
  try {
    const target = await waitForTarget();
    client = await cdp(target.webSocketDebuggerUrl);
    await client.send("Runtime.enable");
    const appReady = await waitForEval(client, `(() => (
      document.readyState === 'complete' &&
      Array.from(document.body.classList).some((item) => item.startsWith('view-')) &&
      document.querySelectorAll('.chart-tool-trigger').length >= 4 &&
      document.querySelectorAll('#sideInsightTabs [data-side-insight]').length >= 7 &&
      document.querySelectorAll('#strategyPresetCards .strategy-preset-card').length >= 3
    ))()`, 30000);
    if (!appReady) throw new Error("Application boot did not complete before smoke checks");
    const checks = await evaluate(client, `(() => ({
      url: location.href,
      title: document.title,
      shellTitlebar: Boolean(document.querySelector('.shell-titlebar')),
      workspaceRail: Boolean(document.querySelector('#workspaceRail')),
      workspaceTabs: Boolean(document.querySelector('#workspaceTabs')),
      statusbar: Boolean(document.querySelector('.desktop-statusbar')),
      strategyCommandStrip: Boolean(document.querySelector('.strategy-command-strip')),
      botReadinessPanel: Boolean(document.querySelector('#botReadinessPanel')),
      strategyPresetPanel: Boolean(document.querySelector('.strategy-preset-panel')),
      strategyExplainPanel: Boolean(document.querySelector('#strategyExplainPanel')),
      warRoomBrief: Boolean(document.querySelector('.war-room-brief')),
      optimizerPanel: Boolean(document.querySelector('.optimizer-panel')),
      segmentList: Boolean(document.querySelector('#btSegmentRows')),
      dataReliabilityPanel: Boolean(document.querySelector('#dataReliabilityRows')),
      dataCachePanel: Boolean(document.querySelector('#dataCacheRows')),
      robotProfilePanel: Boolean(document.querySelector('#robotProfileRows')),
      playbookPanel: Boolean(document.querySelector('#strategyPlaybookCards')),
      anchorPanel: Boolean(document.querySelector('#strategyAnchorRows')),
      executionPanel: Boolean(document.querySelector('#strategyExecutionLog')),
      commandOverlay: Boolean(document.querySelector('#commandOverlay')),
      modeSwitch: Boolean(document.querySelector('#desktopModeSwitch')),
      interfaceSwitch: Boolean(document.querySelector('#interfaceModeSwitch')),
      interfaceBanner: Boolean(document.querySelector('#interfaceFocusBanner')),
      interfaceView: Array.from(document.body.classList).find((item) => item.startsWith('view-')) || '',
      quoteSource: Boolean(document.querySelector('#quoteSourceSelect')),
      refreshButton: Boolean(document.querySelector('#desktopRefresh')),
      futuSetupButton: Boolean(document.querySelector('#desktopFutuSetup')),
      futuDeepPanel: Boolean(document.querySelector('#futuDeepMetrics')),
      chartToolButtons: document.querySelectorAll('.chart-tool-trigger').length,
      chartToolPopover: Boolean(document.querySelector('#chartToolPopover')),
      chartStrategyOverlay: Boolean(document.querySelector('#chartStrategyOverlay')),
      bookStrategyHint: Boolean(document.querySelector('#bookStrategyHint')),
      sideInsightPanel: Boolean(document.querySelector('#sideInsightRows')),
      sideInsightTabs: Array.from(document.querySelectorAll('#sideInsightTabs [data-side-insight]')).map((button) => button.textContent.trim()),
      chartUpColor: getComputedStyle(document.body).getPropertyValue('--up').trim() || getComputedStyle(document.documentElement).getPropertyValue('--up').trim(),
      chartDownColor: getComputedStyle(document.body).getPropertyValue('--down').trim() || getComputedStyle(document.documentElement).getPropertyValue('--down').trim(),
      okxLamp: Boolean(document.querySelector('#okxStatusLamp')),
      futuText: document.querySelector('#futuStatusText')?.textContent || '',
      paperText: document.querySelector('#paperStatusText')?.textContent || '',
      initialValidatedPreset: document.querySelector('[data-strategy-preset="standard"]')?.classList.contains('active') || false,
      initialLeverage: document.querySelector('#leverageInput')?.value || '',
      initialOrderType: document.querySelector('#strategyOrderType')?.value || '',
      initialMarginMode: document.querySelector('#marginMode')?.value || '',
      initialRiskSource: document.querySelector('#riskSource')?.value || '',
      initialRiskValueMode: document.querySelector('#riskValueMode')?.value || '',
      visibleCommand: !document.querySelector('#commandOverlay')?.classList.contains('hidden'),
      mojibakeMatches: (document.body.innerText.match(/(?:\uFFFD|锟斤拷|涔[?]|鍗[?]|鈥|Ã|Â)/g) || []).slice(0, 10)
    }))()`);
    const mode = await evaluate(client, `(() => {
      document.querySelector('[data-desktop-mode="LOCKED"]')?.click();
      return {
        active: document.querySelector('[data-desktop-mode="LOCKED"]')?.classList.contains('active'),
        status: document.querySelector('#chartStatus')?.textContent || ''
      };
    })()`);
    const interfaceNav = await evaluate(client, `(() => {
      document.querySelector('[data-interface-view="research"]')?.click();
      const research = {
        active: document.querySelector('[data-interface-view="research"]')?.classList.contains('active'),
        body: document.body.classList.contains('view-research'),
        botHidden: getComputedStyle(document.querySelector('.bottom-grid')).display === 'none',
        banner: document.querySelector('#interfaceFocusBanner')?.textContent || ''
      };
      document.querySelector('[data-interface-view="system"]')?.click();
      const system = {
        active: document.querySelector('[data-interface-view="system"]')?.classList.contains('active'),
        body: document.body.classList.contains('view-system'),
        chartHidden: getComputedStyle(document.querySelector('.workspace-grid')).display === 'none'
      };
      document.querySelector('[data-interface-view="trade"]')?.click();
      const trade = {
        active: document.querySelector('[data-interface-view="trade"]')?.classList.contains('active'),
        body: document.body.classList.contains('view-trade'),
        botHidden: getComputedStyle(document.querySelector('.bottom-grid')).display === 'none',
        chartVisible: getComputedStyle(document.querySelector('.workspace-grid')).display !== 'none'
      };
      return { research, system, trade };
    })()`);
    const chartTools = await evaluate(client, `(() => {
      document.querySelector('[data-chart-tool-menu="drawing"]')?.click();
      return {
        visible: !document.querySelector('#chartToolPopover')?.classList.contains('hidden'),
        drawingPanelVisible: !document.querySelector('[data-chart-tool-panel="drawing"]')?.classList.contains('hidden'),
        drawingButtons: document.querySelectorAll('[data-chart-tool-panel="drawing"] button').length,
        sideRows: document.querySelectorAll('#sideInsightRows .side-insight-row').length
      };
    })()`);
    await evaluate(client, `document.querySelector('#workspaceTabs [data-workspace-focus=".strategy-desk"]')?.click()`);
    await waitForEval(client, `(() => document.querySelectorAll('#strategyPresetCards .strategy-preset-card').length >= 3 && document.querySelectorAll('#strategyPlaybookCards .playbook-card').length >= 3 && document.querySelectorAll('#strategyAnchorRows .anchor-row').length >= 3 && document.querySelectorAll('#strategyExecutionLog .execution-row').length >= 3)()`, 45000);
    const workspace = await evaluate(client, `(() => {
      document.querySelector('[data-strategy-preset="standard"]')?.click();
      return {
        tabActive: document.querySelector('#workspaceTabs [data-workspace-focus=".strategy-desk"]')?.classList.contains('active'),
        railActive: document.querySelector('#workspaceRail [data-workspace-focus=".strategy-desk"]')?.classList.contains('active'),
        commandStatus: document.querySelector('#strategyCommandStatus')?.textContent || '',
        commandDirection: document.querySelector('#strategyCommandDirection')?.textContent || '',
        presets: document.querySelectorAll('#strategyPresetCards .strategy-preset-card').length,
        presetActive: document.querySelector('[data-strategy-preset="standard"]')?.classList.contains('active'),
        leverage: document.querySelector('#leverageInput')?.value || '',
        position: document.querySelector('#positionInput')?.value || '',
        riskValueMode: document.querySelector('#riskValueMode')?.value || '',
        warSummary: document.querySelector('#strategyWarSummary')?.textContent || '',
        playbookRows: document.querySelectorAll('#strategyPlaybookCards .playbook-card').length,
        anchors: document.querySelectorAll('#strategyAnchorRows .anchor-row').length,
        executions: document.querySelectorAll('#strategyExecutionLog .execution-row').length
      };
    })()`);
    const opened = await evaluate(client, `(() => {
      document.querySelector('#commandOpen')?.click();
      return {
        visible: !document.querySelector('#commandOverlay')?.classList.contains('hidden'),
        rows: document.querySelectorAll('.command-row').length,
        groups: document.querySelectorAll('.command-row em').length
      };
    })()`);
    await evaluate(client, `document.querySelector('[data-desktop-mode="PAPER"]')?.click()`);
    await evaluate(client, `document.querySelector('#commandOverlay')?.classList.add('hidden')`);
    const failures = [];
    if (!checks.url.includes("127.0.0.1:8765")) failures.push("page url");
    if (!checks.shellTitlebar) failures.push("shell titlebar");
    if (!checks.workspaceRail) failures.push("workspace rail");
    if (!checks.workspaceTabs) failures.push("workspace tabs");
    if (!checks.statusbar) failures.push("desktop statusbar");
    if (!checks.strategyCommandStrip) failures.push("strategy command strip");
    if (!checks.botReadinessPanel) failures.push("bot readiness panel");
    if (!checks.strategyPresetPanel) failures.push("strategy preset panel");
    if (!checks.strategyExplainPanel) failures.push("strategy explain panel");
    if (!checks.warRoomBrief || !checks.playbookPanel || !checks.anchorPanel || !checks.executionPanel) failures.push("war room v2 panels");
    if (!checks.optimizerPanel || !checks.segmentList) failures.push("backtest optimizer panels");
    if (!checks.dataReliabilityPanel) failures.push("data reliability panel");
    if (!checks.dataCachePanel) failures.push("data cache panel");
    if (!checks.robotProfilePanel) failures.push("robot profile panel");
    if (!checks.commandOverlay) failures.push("command overlay");
    if (!checks.modeSwitch) failures.push("mode switch");
    if (!checks.interfaceSwitch || !checks.interfaceBanner || !checks.interfaceView) failures.push("interface workspaces");
    if (!checks.quoteSource) failures.push("quote source select");
    if (!checks.refreshButton) failures.push("refresh button");
    if (!checks.futuSetupButton) failures.push("futu setup button");
    if (!checks.futuDeepPanel) failures.push("futu deep panel");
    if (checks.chartToolButtons < 4 || !checks.chartToolPopover) failures.push("chart grouped tools");
    if (!checks.chartStrategyOverlay || !checks.bookStrategyHint) failures.push("strategy chart overlay");
    if (!checks.sideInsightPanel) failures.push("right insight panel");
    if (checks.sideInsightTabs.length < 7 || !checks.sideInsightTabs.includes("估值") || !checks.sideInsightTabs.includes("机构") || !checks.sideInsightTabs.includes("AI摘要")) failures.push("right insight tabs");
    if (!/ff|c8|red/i.test(checks.chartUpColor || "")) failures.push("red up convention");
    if (!/19|08|22|35|green/i.test(checks.chartDownColor || "")) failures.push("green down convention");
    if (!checks.okxLamp) failures.push("okx lamp");
    if (!checks.initialValidatedPreset || checks.initialLeverage !== "1" || checks.initialOrderType !== "CURRENT" || checks.initialMarginMode !== "CROSS" || checks.initialRiskSource !== "MANUAL" || checks.initialRiskValueMode !== "PCT") failures.push("initial validated strategy profile");
    if (checks.mojibakeMatches.length) failures.push(`visible mojibake: ${checks.mojibakeMatches.join(", ")}`);
    if (!interfaceNav.research.active || !interfaceNav.research.body || !interfaceNav.research.botHidden || !/研究|情报|Research/i.test(interfaceNav.research.banner)) failures.push("research workspace view");
    if (!interfaceNav.system.active || !interfaceNav.system.body || !interfaceNav.system.chartHidden) failures.push("system workspace view");
    if (!interfaceNav.trade.active || !interfaceNav.trade.body || !interfaceNav.trade.botHidden || !interfaceNav.trade.chartVisible) failures.push("trade workspace view");
    if (!chartTools.visible || !chartTools.drawingPanelVisible || chartTools.drawingButtons < 4) failures.push("chart tool menu open");
    if (chartTools.sideRows < 3) failures.push("right insight rows");
    if (!mode.active || !mode.status.includes("实盘硬锁")) failures.push("live lock mode");
    if (!workspace.tabActive || !workspace.railActive) failures.push("workspace sync");
    if (!workspace.commandStatus || !workspace.commandDirection) failures.push("strategy command summary");
    if (workspace.presets < 3 || !workspace.presetActive) failures.push("strategy presets");
    if (!workspace.leverage || !workspace.position || workspace.riskValueMode !== "PCT") failures.push("preset apply");
    if (workspace.playbookRows < 3) failures.push("strategy playbook rows");
    if (workspace.anchors < 3) failures.push("strategy anchors");
    if (workspace.executions < 3) failures.push("strategy execution log");
    if (!opened.visible) failures.push("command open");
    if (opened.rows < 3) failures.push("command rows");
    if (opened.groups < opened.rows) failures.push("command groups");
    if (failures.length) {
      throw new Error(`Smoke test failed: ${failures.join(", ")}\n${JSON.stringify({ checks, mode, interfaceNav, workspace, opened }, null, 2)}`);
    }
    console.log(JSON.stringify({ ok: true, checks, mode, interfaceNav, workspace, opened }, null, 2));
  } finally {
    client?.close();
    smokeRuntime?.stop();
  }
}

main().catch((error) => {
  smokeRuntime?.stop();
  console.error(error.stack || error.message);
  process.exit(1);
});
