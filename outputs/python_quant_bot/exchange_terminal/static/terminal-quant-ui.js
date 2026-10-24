/* Shared message validation and the original-terminal research task UI. */
(() => {
  "use strict";
  const SCHEMA = "hakimi-terminal-quant-bridge-v1";
  const ENGINE = "terminal.causal-long-only-signals-v7";
  const READABLE_ENGINES = new Set([ENGINE, "terminal.causal-long-only-signals-v6"]);
  const plain = (value) => Boolean(value && typeof value === "object" && !Array.isArray(value));
  const finite = (value) => typeof value === "number" && Number.isFinite(value);
  const text = (value, max = 120) => typeof value === "string" && value.length > 0 && value.length <= max;
  function validMessage(event, source, origin, kinds) {
    const data = event?.data;
    return event?.source === source && event?.origin === origin && plain(data)
      && Object.keys(data).every((key) => ["schema", "kind", "payload"].includes(key))
      && data.schema === SCHEMA && kinds.includes(data.kind) && plain(data.payload);
  }
  function validParams(params) {
    return plain(params) && Object.keys(params).length <= 40 && Object.entries(params).every(([key, value]) =>
      /^[A-Za-z][A-Za-z0-9_]{0,63}$/.test(key) && (finite(value) || typeof value === "boolean" || text(value, 100)));
  }
  function validContext(value) {
    return plain(value) && text(value.symbol, 40) && text(value.bar, 20) && text(value.strategy_id, 80)
      && validParams(value.strategy_params) && plain(value.risk) && Array.isArray(value.blockers)
      && value.blockers.length <= 20 && value.blockers.every((item) => text(item, 300))
      && (value.ai_evidence === undefined || validAiEvidence(value.ai_evidence, value));
  }
  function validInsightsContext(value) {
    const date = (v) => typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v)
      && Number.isFinite(Date.parse(v+"T00:00:00Z")) && new Date(v+"T00:00:00Z").toISOString().slice(0,10) === v;
    return plain(value) && Object.keys(value).every(key => ["symbol","input_id","as_of","frozen","section"].includes(key))
      && text(value.symbol,40) && typeof value.frozen === "boolean"
      && ["structure","peers","indicators"].includes(value.section)
      && typeof value.input_id === "string" && typeof value.as_of === "string"
      && (value.frozen ? text(value.input_id,150) && !value.input_id.includes("\0") && (!value.as_of || date(value.as_of))
        : value.input_id === "" && value.as_of === "");
  }
  function validAiEvidence(value, context = null) {
    const required = ["schema_version","symbol","bar","session","question","generated_at","input_identity","providers"];
    const daily = (bar) => ["1d","1dutc","daily","day"].includes(String(bar).toLowerCase());
    const bounded = (value,max) => typeof value === "string" && value.length <= max && !value.includes("\0");
    const integer = (value) => Number.isSafeInteger(value) && value > 0 && value <= 8640000000000000;
    if (!plain(value) || Object.keys(value).some((key) => !required.includes(key)) || required.some((key) => !(key in value))
      || value.schema_version !== "hakimi-ai-research-evidence-v1" || !text(value.symbol,40) || !text(value.session,40)
      || !daily(value.bar) || !bounded(value.question,900) || !integer(value.generated_at)) return false;
    if (context && (value.symbol !== context.symbol || !daily(context.bar)
      || value.session.toLowerCase() !== String(context.session).toLowerCase())) return false;
    const input = value.input_identity, keys = ["rows_sha256","row_count","first_ts","last_ts","source","price_basis","snapshot_id"];
    if (!plain(input) || Object.keys(input).some((key) => !keys.includes(key)) || !/^[0-9a-f]{64}$/.test(input.rows_sha256 || "")
      || !Number.isInteger(input.row_count) || input.row_count < 30 || input.row_count > 300
      || !integer(input.first_ts) || !integer(input.last_ts) || input.first_ts > input.last_ts
      || !text(input.source,200) || !text(input.price_basis,100)
      || (input.snapshot_id != null && !bounded(input.snapshot_id,160))) return false;
    const seen = new Set();
    return Array.isArray(value.providers) && value.providers.length >= 1 && value.providers.length <= 2
      && value.providers.every((item) => {
        if (!plain(item) || Object.keys(item).some((key) => !["provider","model","content","summary"].includes(key))
          || !["deepseek","openai"].includes(item.provider) || seen.has(item.provider)
          || !text(item.model,120) || !text(item.content,16000) || !bounded(item.content,16000)
          || (item.summary !== undefined && !bounded(item.summary,2000))) return false;
        seen.add(item.provider); return true;
      });
  }
  function chartRows(rows) {
    if (!Array.isArray(rows) || !rows.length || rows.length > 10000) throw new Error("冻结行情为空或超出可展示范围。");
    let previous = -Infinity;
    return rows.map((row) => {
      const ts = row.ts_ms ?? row.ts;
      if (!plain(row) || !finite(ts) || ts <= previous || !text(row.date, 40)
        || ![row.open, row.high, row.low, row.close, row.volume].every(finite)
        || row.open <= 0 || row.close <= 0 || row.low <= 0 || row.high < Math.max(row.open, row.close)
        || row.low > Math.min(row.open, row.close) || row.volume < 0) throw new Error("冻结行情时间或价格字段不完整，未替换原图表。");
      previous = ts;
      return { ts, date: row.date, open: row.open, high: row.high, low: row.low, close: row.close, volume: row.volume };
    });
  }
  function validReplay(value) {
    if (!plain(value) || !text(value.symbol, 40) || !text(value.input_id, 150)
      || !plain(value.meta) || !text(value.meta.price_basis, 100)
      || !text(value.meta.asset_class, 40) || !Array.isArray(value.trades) || value.trades.length > 20000) return false;
    if (value.source === "JUDGMENT_FROZEN_INPUT") {
      if (!/^[0-9a-f]{64}$/.test(value.judgment_id || "") || !/^[0-9a-f]{64}$/.test(value.record_hash || "")
        || value.trades.length !== 0 || value.run_id !== undefined || value.report_hash !== undefined) return false;
    } else if (["EXIT_RESEARCH_FROZEN","STRUCTURE_FROZEN"].includes(value.source)) {
      if (!/^[0-9a-f]{64}$/.test(value.input_id || "") || !/^[0-9a-f]{64}$/.test(value.record_hash || "")
        || value.trades.length !== 0 || value.run_id !== undefined || value.report_hash !== undefined
        || !Array.isArray(value.structure_marks) || value.structure_marks.length > 30000
        || !value.structure_marks.every(plain)) return false;
      if (value.source === "EXIT_RESEARCH_FROZEN" && (!/^[0-9a-f]{64}$/.test(value.exit_run_id || "")
        || !Array.isArray(value.exit_paths) || value.exit_paths.length > 60000 || !value.exit_paths.every(plain))) return false;
      if (value.source === "STRUCTURE_FROZEN" && (value.exit_run_id !== undefined || value.exit_paths !== undefined)) return false;
    } else if (!text(value.run_id, 120) || !text(value.report_hash, 150)) return false;
    try { chartRows(value.rows); return true; } catch (_) { return false; }
  }
  function validConfiguration(value) {
    return plain(value) && READABLE_ENGINES.has(value.engine_id) && text(value.strategy_id, 80)
      && validParams(value.strategy_params) && plain(value.risk)
      && ["position_pct", "take_profit_pct", "stop_loss_pct", "leverage"].every((key) => finite(value.risk[key]))
      && value.risk.leverage === 1 && value.risk.position_pct > 0 && value.risk.position_pct <= 100
      && value.risk.take_profit_pct >= 0 && value.risk.stop_loss_pct >= 0;
  }
  function contextSourceId(symbol, market, frozen = false) {
    return !frozen && market?.symbol === symbol && typeof market.source_id === "string" ? market.source_id : "";
  }
  function researchBlocker(entry) {
    if (!entry) return "策略目录尚未就绪，不能新建或运行任务。";
    const cap = entry.capability || {};
    return cap.backtest_supported === true && cap.new_research_allowed === true ? ""
      : cap.paper_blocker || cap.blocker || "此策略仅保留历史记录，当前不允许新建或运行研究任务。";
  }
  function comparisonSignalParams(row, catalog) {
    const params = row.configuration?.strategy_params || {};
    if (!READABLE_ENGINES.has(row.engine_id)) return params;
    const strategyId = row.configuration?.strategy_id || row.strategy_id;
    const keys = new Set((catalog.find((entry) => entry.id === strategyId)?.parameter_fields || []).map((field) => field.key));
    return Object.fromEntries(Object.entries(params).filter(([key]) => keys.has(key)));
  }
  const protocol = { SCHEMA, ENGINE, validMessage, validContext, validInsightsContext, validReplay, validConfiguration, chartRows, contextSourceId, researchBlocker, comparisonSignalParams, validAiEvidence };
  globalThis.HakimiTerminalQuantProtocol = protocol;
  if (typeof module === "object" && module.exports) module.exports = protocol;

  globalThis.installTerminalQuantUI = function installTerminalQuantUI({ api, perform, esc, modal, closeDialog,
    showError, getSelectedCoreRun = () => null, openCoreTask, openCoreRun,
    openCoreTaskForm, openCoreImport, initializeCoreExample }) {
    if (document.getElementById("terminalQuantWorkspace")) return;
    const coreMain = document.getElementById("main");
    const navRoot = document.getElementById("navigation");
    if (!coreMain || !navRoot) throw new Error("terminal_quant_ui_mount_missing");
    const state = { catalog: [], inputs: [], tasks: [], runs: [], coreTasks: [], coreRuns: [], coreInputs: [], coreStrategies: [], coreOverview: null, comparison: new Set(), history: [], reports: [], context: null, market: null,
      selectedRun: null, revisionOf: null, aiEvidence: null, aiEvidenceBinding: null, aiEvidenceEnabled: false, visible: false, loaded: false, marketRequest: 0, unifiedView: "dashboard", refreshPromise: null };
    const $ = (id) => document.getElementById(id);
    const value = (id) => $(id)?.value ?? "";
    const fmt = (number) => finite(Number(number)) ? Number(number).toLocaleString("zh-CN", {maximumFractionDigits:4}) : "—";
    const identity = (row) => row.id || row.task_id || row.run_id || row.input_id;
    const button = (label, action, id = "", extra = "") => `<button type="button" class="btn small" data-tq-action="${action}" data-tq-id="${esc(id)}" ${extra}>${esc(label)}</button>`;
    const warning = (message) => `<div class="notice warning">${esc(message)}</div>`;
    function notify(message, error = false) {
      $("tq-message").className = error ? "notice error" : "notice";
      $("tq-message").textContent = message;
      $("tq-message").hidden = !message;
    }
    async function act(action, payload, options = {}) {
      const {errorTarget: _unused, ...jobOptions} = options;
      notify("正在处理本地操作，请勿重复提交；操作记录会保留在当前工作区。");
      // The core errorTarget option is scoped to its modal dialog. This panel is
      // persistent, so let the durable job finish independently of that dialog.
      const result = await perform(action, payload, jobOptions);
      if (result === null) notify(coreMain.querySelector(".global-message")?.textContent?.trim()
        || "操作未完成。请查看设置与日志中的原操作记录，不要自动重试。", true);
      return result;
    }
    function send(kind, payload) { parent.postMessage({schema:SCHEMA, kind, payload}, location.origin); }
    function show(view = "dashboard", replaceHistory = false) {
      const wasVisible = state.visible;
      state.unifiedView = ["dashboard","tasks","results","insights"].includes(view) ? view : "dashboard";
      state.visible = true; coreMain.hidden = true; $("terminalQuantWorkspace").hidden = false;
      if (location.hash !== "#" + state.unifiedView) history[replaceHistory ? "replaceState" : "pushState"](null,"","#" + state.unifiedView);
      syncUnifiedNavigation();
      if (!state.loaded || !wasVisible) refreshAll().catch((error) => notify(error.message, true));
      if (state.unifiedView === "dashboard") {
        requestAnimationFrame(() => window.scrollTo({top:0,left:0,behavior:"auto"}));
      } else {
        const scrollTarget = state.unifiedView === "insights" ? $("terminalInsightsWorkspace") : $(state.unifiedView === "tasks" ? "tq-tasks" : "tq-runs").closest(".panel");
        requestAnimationFrame(() => {
          if (state.unifiedView === "insights" && insightsUI) { insightsUI.reveal(); return; }
          const navigationHeight = navRoot.closest(".sidebar")?.getBoundingClientRect().height || 0;
          scrollTarget.style.scrollMarginTop = `${Math.ceil(navigationHeight) + 8}px`;
          scrollTarget.scrollIntoView({block:"start"});
        });
      }
    }
    function syncUnifiedNavigation() {
      navRoot.querySelectorAll("[data-view]").forEach((item) => {
        const active = item.dataset.view === state.unifiedView;
        item.classList.toggle("active",active); item.setAttribute("aria-current",active ? "page" : "false");
      });
      if ($("breadcrumb")) $("breadcrumb").textContent = {dashboard:"研究工作台",tasks:"全部策略任务",results:"全部回测结果",insights:"行情洞察"}[state.unifiedView];
    }
    function hide() {
      state.visible = false; coreMain.hidden = false; $("terminalQuantWorkspace").hidden = true;
      // Core detail navigation owns its existing active state while visible.
    }
    const navButton = navRoot.querySelector('[data-view="dashboard"]');
    if (!navButton) throw new Error("terminal_quant_dashboard_navigation_missing");
    navButton.id = "terminalQuantNav";
    const navLabel = navButton.querySelector("span");
    if (navLabel) navLabel.textContent = "研究工作台"; else navButton.textContent = "研究工作台";
    const insightsNav = document.createElement("button"); insightsNav.type="button";insightsNav.className=navButton.className;
    insightsNav.dataset.view="insights";insightsNav.textContent="行情洞察";navButton.after(insightsNav);
    const host = document.createElement("section"); host.id = "terminalQuantWorkspace"; host.className = "main tq"; host.hidden = true;
    host.setAttribute("aria-label", "统一量化研究工作台");
    host.innerHTML = `
      <div class="page-heading"><div><h1>研究工作台</h1><p>统一查看已有任务和结果，核对行情、参数与版本。不同策略保留各自的计算规则。</p></div><div class="actions">${button("新建工作台策略任务","new-task-form")}${button("新建股票研究任务","core-create")}${button("导入行情","core-import")}${button("刷新记录","refresh")}</div></div>
      <div id="tq-example" class="notice section-gap" hidden>可使用明确标注的虚构行情熟悉操作。示例不代表真实市场，不能复用为工作台策略的真实行情。${button("准备虚构教学示例","core-example")}</div>
      <div id="tq-message" class="notice" role="status" aria-live="polite" hidden></div>
      <div id="tq-context" class="notice section-gap">从行情、雷达或策略分析进入，可带入当前标的和表单参数。</div>
      <div class="tq-flow" aria-label="研究步骤"><span>1 核对并冻结行情</span><span>2 保存策略任务</span><span>3 运行与复盘结果</span></div>
      <section class="panel"><div class="panel-head"><h2>1 · 核对本地缓存日线</h2><div class="actions"><label for="tq-symbol">标的</label><input id="tq-symbol" maxlength="40" placeholder="例如 AAPL / BTC-USDT">${button("读取本地日线","market")}</div></div><div class="panel-body"><div class="field"><label for="tq-source">单一来源、时段与价格口径</label><select id="tq-source"><option value="">先读取标的，再选择本地来源</option></select><span class="hint">不同来源、时段和复权口径不会拼接。更换来源后需要重新核对。</span></div></div><div class="panel-body" id="tq-market">尚未读取。这里只读取已有本地行情，不连接外部来源。</div></section>
      <section class="panel section-gap"><div class="panel-head"><h2>或复用已导入行情</h2></div><div class="panel-body">
        <p class="section-note">复用已接受的 CSV 或行情快照，沿用同一份行情及原来源声明、文件校验值。原输入保持原样；这里只为原工作台策略建立研究输入，不运行回测、不提升数据认证或交易权限。</p>
        <div class="field"><label for="tq-core-input">已有行情输入</label><select id="tq-core-input"><option value="">请选择一份可复用行情</option></select></div>
        <div id="tq-core-input-detail" class="section-gap"></div><div id="tq-core-input-blockers" class="section-gap"></div>
        <label class="check-label section-gap"><input id="tq-confirm-core-input" type="checkbox" disabled>我已核对原来源与校验值，保留原输入的研究限制。</label>
        <div class="actions section-gap">${button("复用这份行情","import-core-input","","disabled")}</div>
      </div></section>
      <section class="panel section-gap"><div class="panel-head"><h2 id="tq-form-title">2 · 新建策略任务</h2>${button("重新填写新任务","new")}</div><div class="panel-body"><form id="tq-task-form">
        <div id="tq-task-error" class="form-error"></div><div class="form-grid">
          <div class="field"><label for="tq-name">任务名称</label><input id="tq-name" maxlength="64" required placeholder="例如 AAPL 日线研究"></div>
          <div class="field"><label for="tq-strategy">原工作台策略</label><select id="tq-strategy" required></select></div>
          <div class="field span-2"><label for="tq-input">封存行情</label><select id="tq-input" required><option value="">先核对并冻结行情</option></select><span class="hint">每个任务绑定一份不再变化的行情；新版本保留旧数据与结果。</span><div class="actions">${button("记录这份行情的判断","judgment-input")}${button("查看已确认结构","structure-input")}</div></div>
        </div><div id="tq-strategy-note" class="section-note section-gap"></div><div id="tq-params" class="form-grid"></div>
        <div class="form-section"><h3>仓位、费用与保护</h3><div class="form-grid">
          <div class="field"><label for="tq-position">仓位（%）</label><input id="tq-position" type="number" min="0.000001" max="100" step="any" value="25" required></div>
          <div class="field"><label for="tq-stop">止损价格距离（%）</label><input id="tq-stop" type="number" min="0" max="100" step="any" value="8" required></div>
          <div class="field"><label for="tq-take">止盈价格距离（%）</label><input id="tq-take" type="number" min="0" max="1000" step="any" value="0" required></div>
          <div class="field"><label for="tq-fee">手续费率（%）</label><input id="tq-fee" type="number" min="0" max="2" step="any" value="0.05" required></div>
          <div class="field"><label for="tq-slippage">滑点（基点，1 基点 = 0.01%）</label><input id="tq-slippage" type="number" min="0" max="500" step="any" value="2" required></div>
          <div class="field"><label>当前执行模型</label><p>日线 · 只做多 · 1 倍杠杆；收盘形成信号，下一根开盘成交。止盈止损为 0 时不启用该项。</p></div>
        </div></div><p class="section-note">本地缓存需要来源复核。保存任务与研究结果不会开启模拟或实盘权限。</p>
        <div class="form-section"><h3>AI 研究依据（可选）</h3><label class="check-label"><input id="tq-use-ai" type="checkbox" disabled>随任务保存这份 AI 研究依据，不改变策略参数</label><div id="tq-ai-evidence" class="section-gap"></div></div>
        <div class="actions"><button id="tq-save-task" type="submit" class="btn primary">保存策略任务</button>${button("采用当前策略表单参数","apply-context")}</div>
      </form></div></section>
      <section class="panel section-gap"><div class="panel-head"><h2>全部策略任务与版本</h2></div><div id="tq-tasks" class="panel-body"></div></section>
      <section class="panel section-gap"><div class="panel-head"><h2>全部回测结果与复盘</h2>${button("比较选中的版本","compare")}</div><div id="tq-runs" class="panel-body"></div><div class="panel-body"><label for="tq-core-comparison">可选：并排查看一份已有导入任务结果（不同引擎不计算收益差）</label><select id="tq-core-comparison"><option value="">不加入</option></select></div><div id="tq-run-detail" class="panel-body"></div></section>
      <section class="panel section-gap"><div class="panel-head"><h2>原研究记录</h2><div class="actions">${button("查看原组合研究报告","original-portfolio")}${button("策略分析与模拟记录","original-strategy")}</div></div><div class="panel-body"><p class="section-note">直接读取原研究报告文件和策略流水线记录，保留各自身份；历史报告不作为当前报告，不补算、不重签。原组合报告、账户、日志和导出仍在工作台原位置。</p><h3>原研究报告文件</h3><div id="tq-reports"></div><div id="tq-report-detail"></div><h3 class="section-gap">原策略流水线记录</h3><div id="tq-history"></div><div id="tq-history-detail"></div></div></section>`;
    coreMain.before(host);
    const flow = host.querySelector(".tq-flow");
    flow.before($("tq-tasks").closest(".panel"),$("tq-runs").closest(".panel"));
    const style = document.createElement("style");
    style.textContent = `.tq{padding-top:20px}.tq [hidden]{display:none!important}.tq-flow{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0;color:var(--muted);font-size:13px}.tq-flow span{padding:8px 12px;background:var(--surface);border:1px solid var(--line);border-radius:6px}.tq input,.tq select{min-width:0}.tq-row{padding:14px 0;border-bottom:1px solid var(--line);display:flex;align-items:flex-start;justify-content:space-between;gap:14px}.tq-row:last-child{border:0}.tq-row p{margin:5px 0;color:var(--muted);font-size:12px}.tq-table{overflow:auto;max-height:310px}.tq-table table{min-width:600px}.tq-metrics{display:flex;gap:24px;flex-wrap:wrap;margin:16px 0}.tq-metrics strong{display:block;font-size:22px}.tq .form-grid{margin-bottom:15px}.tq .actions{flex-wrap:wrap}.tq .page-heading p{max-width:680px}@media(max-width:760px){.tq-row{display:block}.tq-row .actions{margin-top:10px}.tq .panel-head{align-items:flex-start}.tq .form-grid{grid-template-columns:1fr}.tq .span-2{grid-column:auto}}`;
    document.head.append(style);
    const judgmentUI = typeof globalThis.installTerminalJudgmentUI === "function"
      ? globalThis.installTerminalJudgmentUI({host,api,perform,notify,validReplay,sendReplay:(chart) => send("replay-result",chart)})
      : null;
    const exitResearchUI = typeof globalThis.installTerminalExitResearchUI === "function"
      ? globalThis.installTerminalExitResearchUI({host,api,perform,notify,validReplay,sendReplay:(chart) => send("replay-result",chart)})
      : null;
    const insightsUI = typeof globalThis.installTerminalInsightsUI === "function"
      ? globalThis.installTerminalInsightsUI({host,api,notify,openMarket:async (symbol) => {
        $("tq-symbol").value=symbol;await readMarket("");
        const card=$("tq-market").closest(".panel");card.scrollIntoView({block:"start"});$("tq-symbol").focus();
      }}) : null;
    insightsNav.hidden = !insightsUI;

    function renderCatalog() {
      const selected = value("tq-strategy");
      $("tq-strategy").innerHTML = state.catalog.map((row) => `<option value="${esc(row.id)}">${esc(row.name || row.id)}${row.capability?.new_research_allowed === false ? " · 仅历史记录" : researchBlocker(row) ? " · 当前不可新建" : ""}</option>`).join("");
      if (state.catalog.some((row) => row.id === selected)) $("tq-strategy").value = selected;
      renderParams();
    }
    function renderParams(params = null) {
      const entry = state.catalog.find((row) => row.id === value("tq-strategy"));
      const values = {...(entry?.params || {}),...(params || {})};
      const blocked = researchBlocker(entry);
      $("tq-strategy-note").textContent = blocked ? `仅历史记录 · ${blocked}` : `${entry.description || entry.name} · 使用原工作台信号引擎；与其它同名策略分别保留规则身份。`;
      $("tq-save-task").disabled = Boolean(blocked);
      const signalKeys = new Set((entry?.parameter_fields || []).map((field) => field.key));
      $("tq-params").innerHTML = Object.entries(values).filter(([key]) => signalKeys.has(key)).map(([key, val]) => {
        const field = entry?.parameter_fields?.find((item) => item.key === key);
        const input = typeof val === "boolean" ? `<select id="tq-param-${esc(key)}" data-tq-param="${esc(key)}" data-tq-type="boolean"><option value="true" ${val ? "selected" : ""}>是</option><option value="false" ${!val ? "selected" : ""}>否</option></select>`
          : `<input id="tq-param-${esc(key)}" data-tq-param="${esc(key)}" data-tq-type="${typeof val}" type="${typeof val === "number" ? "number" : "text"}" step="any" value="${esc(val)}" required>`;
        return `<div class="field"><label for="tq-param-${esc(key)}">${esc(field?.label || key)}</label>${input}</div>`;
      }).join("");
    }
    function renderInputs(preferred = null) {
      const selected = preferred || value("tq-input");
      $("tq-input").innerHTML = '<option value="">请选择已封存行情</option>' + state.inputs.map((row) => `<option value="${esc(identity(row))}">${esc(row.symbol)} · ${esc(row.date_start || "")} 至 ${esc(row.date_end || "")} · ${esc(row.row_count)} 日 · 来源待复核</option>`).join("");
      if (state.inputs.some((row) => identity(row) === selected)) $("tq-input").value = selected;
    }
    function renderCoreInputs() {
      const selected = value("tq-core-input");
      $("tq-core-input").innerHTML = '<option value="">请选择一份可复用行情</option>' + state.coreInputs.map((row) => `<option value="${esc(identity(row))}" ${row.available !== true ? "disabled" : ""}>${esc(row.label || row.symbol || identity(row))} · ${esc(row.symbol || "标的未记录")} · ${row.available === true ? "可复用研究行情" : "当前不可复用"}</option>`).join("");
      if (state.coreInputs.some((row) => identity(row) === selected && row.available === true)) $("tq-core-input").value = selected;
      $("tq-core-input-blockers").innerHTML = state.coreInputs.filter((row) => row.available !== true).map((row) => warning(`${row.label || row.symbol || identity(row)}：${(row.blockers || []).join("；") || "未通过原输入复用校验"}`)).join("");
      renderCoreInputSelection();
    }
    function renderCoreInputSelection() {
      const input = state.coreInputs.find((row) => identity(row) === value("tq-core-input"));
      const available = input?.available === true;
      $("tq-confirm-core-input").checked = false; $("tq-confirm-core-input").disabled = !available;
      host.querySelector('[data-tq-action="import-core-input"]').disabled = true;
      $("tq-core-input-detail").innerHTML = input ? `<p class="section-note">原输入身份：${esc(identity(input))} · 原来源声明保持不变；复用后仍不提供交易授权。</p>
        <dl class="kv section-gap"><dt>行情范围</dt><dd>${esc(input.date_start || "未记录")} 至 ${esc(input.date_end || "未记录")} · ${esc(input.row_count ?? "未记录")} 行</dd>
        <dt>原快照 SHA-256</dt><dd style="word-break:break-all">${esc(input.snapshot_hash || "未记录")}</dd><dt>来源声明 SHA-256</dt><dd style="word-break:break-all">${esc(input.source_manifest_hash || "未记录")}</dd><dt>原文件 SHA-256</dt><dd style="word-break:break-all">${esc(input.file_sha256 || "未记录")}</dd></dl>
        <details class="section-gap"><summary>查看原来源、价格口径与完整输入身份</summary><pre class="code-detail">${esc(JSON.stringify(input,null,2))}</pre></details>`
        : '<p class="muted">先选择可复用的行情。没有可用项时，可通过原数据导入功能接受行情；被阻挡的输入不会从这个入口绕过校验。</p>';
    }
    function renderTasks() {
      const nativeRows = state.tasks.map((row) => `<div class="tq-row"><div><strong>${esc(row.title || row.name)}</strong><p>工作台信号规则 · ${esc(row.strategy_name || row.strategy_id)} · 版本 ${esc(row.version)} · ${esc(row.input_summary?.symbol || "")} · ${row.state === "PAUSED" ? "已暂停" : "已启用"}</p><p>仓位 ${fmt(row.risk?.position_pct)}% · 止损 ${fmt(row.risk?.stop_loss_pct)}% · 止盈 ${fmt(row.risk?.take_profit_pct)}%</p>${row.requires_revision ? '<p>计算规则已更新；旧记录可查看，请修订为新版本后运行。</p>' : ""}</div><div class="actions">${button("查看 / 修订","edit",row.family_id)}${button(row.state === "PAUSED" ? "启用" : "暂停","state",row.family_id)}${button("运行回测","run",identity(row),row.requires_revision || row.state === "PAUSED" || researchBlocker(state.catalog.find((entry) => entry.id === row.strategy_id)) ? "disabled" : "")}${button("记录判断","judgment-task",identity(row))}</div></div>`);
      const importedRows = state.coreTasks.map((row) => {
        const snapshot = row.inputs?.snapshot, strategy = state.coreStrategies.find((entry) => entry.key === row.strategy);
        return `<div class="tq-row"><div><strong>${esc(row.title || row.name || row.label || "策略任务")}</strong><p>股票研究规则 · ${esc(strategy?.title || row.strategy || "规则未记录")} · ${esc(row.revisions?.length || 1)} 个保存版本 · ${esc(snapshot?.security?.symbol || snapshot?.security_id || snapshot?.label || "标的未记录")} · ${row.state === "PAUSED" ? "已暂停" : row.state === "ENABLED" ? "已启用" : esc(row.state || "状态未记录")}</p><p>${row.legacy_task ? "旧格式原任务只读保留；可复制后修订。" : "按此任务原有的输入、参数和执行规则管理。"}${snapshot?.evidence_kind === "SYNTHETIC_TEST" ? " 虚构教学数据，不代表真实市场。" : ""}</p></div>${button("查看 / 管理","core-task",row.id)}</div>`;
      });
      $("tq-tasks").innerHTML = nativeRows.concat(importedRows).join("") || '<p class="muted">尚无策略任务。可使用现有行情或导入数据，核对规则后保存任务。</p>';
    }
    function renderRuns() {
      const rows = state.runs.map((row) => ({kind:"terminal",row})).concat(state.coreRuns.map((row) => ({kind:"core",row})));
      rows.sort((a,b) => String(b.row.started_at || "").localeCompare(String(a.row.started_at || "")));
      $("tq-runs").innerHTML = rows.map(({kind,row}) => kind === "core"
        ? `<div class="tq-row"><div><strong>${esc(row.task_display_name || row.task_title || row.title || row.strategy?.title || row.label || "回测结果")}</strong><p>股票研究规则 · ${esc(row.strategy?.title || row.label || "规则未记录")} · ${esc(row.task_version_label || "版本未记录")} · ${esc(row.symbol || "")}</p><p>${esc(row.score_start || "")} 至 ${esc(row.score_end || "")} · ${esc(row.started_at || "时间未记录")}${row.data_kind === "SYNTHETIC_TEST" ? " · 虚构教学数据" : ""}</p></div>${button("查看结果","core-result",row.id)}</div>`
        : `<div class="tq-row"><label class="check-label"><input type="checkbox" data-tq-compare="${esc(identity(row))}" ${state.comparison.has(identity(row)) ? "checked" : ""} ${row.status !== "COMPLETED" ? "disabled" : ""}><span><strong>${esc(row.title || row.strategy_id || "未完成运行")}</strong><p>工作台信号规则 · ${esc(row.strategy_id || "规则未记录")} · 版本 ${esc(row.version)} · ${esc(row.input_summary?.symbol || "")}</p><p>${esc(row.started_at || "")} · ${esc(row.status)}</p></span></label><div class="actions">${button("查看结果","result",identity(row))}${button("记录判断","judgment-run",identity(row),row.status !== "COMPLETED" ? "disabled" : "")}${button("出场对照研究","exit-research-run",identity(row),row.status !== "COMPLETED" || researchBlocker(state.catalog.find((entry) => entry.id === row.strategy_id)) ? "disabled" : "")}</div></div>`).join("") || '<p class="muted">尚无回测结果。保存任务不会自动运行；已有结果和版本会一直保留。</p>';
      const selected = value("tq-core-comparison");
      $("tq-core-comparison").innerHTML = '<option value="">不加入</option>' + state.coreRuns.map((row) => `<option value="${esc(row.id)}">${esc(row.task_display_name || row.label || row.symbol)} · ${esc(row.task_version_label || "历史版本")} · ${esc(row.symbol || "")}</option>`).join("");
      $("tq-core-comparison").value = selected;
    }
    async function refreshAll() {
      if (state.refreshPromise) return state.refreshPromise;
      state.refreshPromise = loadAllRecords();
      try { return await state.refreshPromise; } finally { state.refreshPromise = null; }
    }
    async function loadAllRecords() {
      const [catalog, inputs, tasks, runs, history, reports, coreOverview, coreInputs] = await Promise.all([api("terminal_catalog"),api("terminal_inputs"),api("terminal_tasks"),api("terminal_runs"),api("terminal_history"),api("terminal_reports"),api("status"),api("terminal_core_inputs")]);
      if (!state.loaded) { state.catalog = catalog.items || []; renderCatalog(); }
      state.inputs = inputs.items || []; state.tasks = tasks.items || []; state.runs = runs.items || [];
      state.history = history.items || []; state.reports = reports.items || []; state.reportsPage = reports;
      state.coreOverview = coreOverview; state.coreTasks = coreOverview.tasks || []; state.coreRuns = coreOverview.runs || [];
      state.coreStrategies = catalog.core_items || []; state.coreInputs = coreInputs.items || [];
      $("tq-example").hidden = coreOverview.initialized !== false || Boolean(coreOverview.inputs?.length);
      renderCoreInputs(); renderInputs(); renderTasks(); renderRuns(); renderHistory(); renderReports(); state.loaded = true;
      judgmentUI?.setSources({inputs:state.inputs,tasks:state.tasks,runs:state.runs});
      await judgmentUI?.refresh();
      exitResearchUI?.setSources({inputs:state.inputs,runs:state.runs,catalog:state.catalog});
      await exitResearchUI?.refresh();
      insightsUI?.setSources({inputs:state.inputs});
      await insightsUI?.refresh();
      const warnings = [catalog,inputs,tasks,runs,history,reports,coreOverview,coreInputs].flatMap((item) => item.warnings || []);
      if (warnings.length) notify(`有 ${warnings.length} 项记录需要核对，未自动修复或重跑。`, true);
    }
    async function readMarket(explicitSource = null) {
      const symbol = value("tq-symbol").trim();
      if (!symbol) return notify("请填写需要研究的标的。", true);
      const generation = ++state.marketRequest;
      const sourceId = explicitSource ?? (state.market?.symbol === symbol ? value("tq-source") : state.context?.symbol === symbol ? state.context?.source_id || "" : "");
      state.market = null;
      $("tq-market").textContent = "正在读取已有本地日线…";
      try {
        const result = await api("terminal_market/" + encodeURIComponent(symbol) + (sourceId ? "/" + encodeURIComponent(sourceId) : ""));
        if (generation !== state.marketRequest) return;
        state.market = result;
        const market = state.market, rows = market.rows || [], blocked = market.quality?.status === "BLOCK" || !rows.length;
        const sources = market.available_sources || [];
        $("tq-source").innerHTML = (sources.length ? sources : [{source_id:market.source_id,source:market.source_id,session:market.meta?.session,price_basis:market.meta?.price_basis,completed_count:rows.length}]).map((item) => `<option value="${esc(item.source_id || "")}">${esc(item.source || item.provider || item.source_id)} · ${esc(item.session || "UNKNOWN")} · ${esc(item.price_basis || "UNKNOWN")} · ${esc(item.completed_count ?? item.row_count ?? "?")} 日</option>`).join("");
        $("tq-source").value = market.source_id || "";
        const contextNote = state.context ? `工作台原选择：${state.context.symbol} / ${state.context.bar} / ${state.context.session || "时段未指定"}。这里将使用下方明确列出的缓存日线快照。` : "这里使用明确列出的缓存日线快照。";
        $("tq-market").innerHTML = `<p class="section-note">${esc(contextNote)}</p>${warning(blocked ? (market.quality?.blockers || ["缺少可用本地日线"]).join("；") : "本地缓存 · 来源待复核。可用于研究，不代表外部认证或交易授权。")}
          <dl class="kv section-gap"><dt>标的 / 周期</dt><dd>${esc(market.symbol)} / 日线</dd><dt>范围</dt><dd>${esc(rows[0]?.date || "—")} 至 ${esc(rows.at(-1)?.date || "—")} · ${rows.length} 日</dd><dt>来源</dt><dd>${esc(market.source_id || "UNKNOWN")}</dd><dt>价格口径</dt><dd>${esc(market.meta?.price_basis || "UNKNOWN")}</dd><dt>已排除未完成K线</dt><dd>${esc(market.excluded_incomplete_count ?? 0)}</dd></dl>
          <div class="tq-table section-gap"><table><thead><tr><th>日期</th><th>开</th><th>高</th><th>低</th><th>收</th><th>成交量</th></tr></thead><tbody>${rows.slice(-5).map((row) => `<tr><td>${esc(row.date)}</td>${[row.open,row.high,row.low,row.close,row.volume].map((number) => `<td>${fmt(number)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>
          <label class="check-label section-gap"><input id="tq-confirm-market" type="checkbox" ${blocked ? "disabled" : ""}>我已核对标的、日线范围和来源，保留“来源待复核”的研究状态。</label><div class="actions section-gap">${button("冻结这份行情","freeze","","disabled")}</div>`;
      } catch (error) { if (generation !== state.marketRequest) return; state.market = null; $("tq-market").textContent = error.message; }
    }
    function aiEvidenceHtml(evidence, binding = null) {
      if (!validAiEvidence(evidence)) return '<p class="section-note">没有可带入的日线 AI 研究依据。请在行情页对当前标的完成分析后再进入；失败、过期或其它周期的报告不会自动附入。</p>';
      const input = evidence.input_identity;
      const match = binding?.status === "SAME_NUMERIC_ROWS" ? "与任务封存行情的数值和时段一致，来源仍未独立认证。"
        : binding ? "与本次封存行情不同，仅保留为参考依据；不代表分析过这份回测数据。"
        : "保存时将核对封存行情。AI 图表快照可能与任务历史范围、时段或来源不同。";
      return `<p><strong>${esc(evidence.symbol)} · ${esc(evidence.bar)} · ${esc(evidence.session)}</strong> · ${esc(new Date(evidence.generated_at).toISOString())}</p>
        <p>图表来源 ${esc(input.source)} · 价格说明 ${esc(input.price_basis)} · ${esc(input.row_count)} 根</p><p class="section-note">${esc(match)} AI 文字未经独立核验，不提供参数选定、模拟或实盘权限。</p>
        <p>研究问题：${esc(evidence.question || "未填写")}</p>${evidence.providers.map((item) => `<details class="section-gap"><summary>${esc(item.provider)} / ${esc(item.model)} · 查看原始研究文字</summary><p>${esc(item.summary || "")}</p><pre class="code-detail">${esc(item.content)}</pre></details>`).join("")}
        <details class="section-gap"><summary>研究快照身份</summary><pre class="code-detail">${esc(JSON.stringify({input_identity:input,binding},null,2))}</pre></details>`;
    }
    function renderAiEvidence() {
      const checkbox = $("tq-use-ai");
      checkbox.disabled = !validAiEvidence(state.aiEvidence);
      checkbox.checked = !checkbox.disabled && state.aiEvidenceEnabled;
      $("tq-ai-evidence").innerHTML = aiEvidenceHtml(state.aiEvidence,state.aiEvidenceBinding);
    }
    function applyContext(context) {
      state.context = context;
      if (!state.revisionOf) {
        const candidate = validAiEvidence(context.ai_evidence,context) ? context.ai_evidence : null;
        if (JSON.stringify(candidate) !== JSON.stringify(state.aiEvidence)) {
          state.aiEvidence = candidate ? JSON.parse(JSON.stringify(candidate)) : null;
          state.aiEvidenceBinding = null; state.aiEvidenceEnabled = Boolean(candidate);
        }
      }
      renderAiEvidence();
      if (!value("tq-symbol")) $("tq-symbol").value = context.symbol;
      $("tq-context").innerHTML = `<strong>工作台当前选择：${esc(context.symbol)} · ${esc(context.bar)} · ${esc(context.session || "时段未指定")} · ${esc(context.strategy_name || context.strategy_id)}</strong><p>图表来源：${esc(context.chart_source || "未指定")}</p><p>${context.blockers.length ? esc(context.blockers.join("；")) : "可显式采用当前策略参数。日线来源、时段和价格口径仍需单独核对并冻结。"}</p><div class="actions section-gap">${button("读取这个标的的日线","context-market")}${button("采用当前策略表单参数","apply-context")}</div>`;
    }
    function applyContextParams() {
      const context = state.context;
      if (!context) return notify("请从工作台发送当前选择。", true);
      if (context.blockers.length) return notify("当前表单包含本研究模型不支持的设置：" + context.blockers.join("；") + "。请在原表单调整，或在这里明确填写支持的设置。", true);
      if (!state.catalog.some((item) => item.id === context.strategy_id)) return notify("当前策略不在原引擎目录中，未自动替换。", true);
      $("tq-strategy").value = context.strategy_id; renderParams(context.strategy_params);
      $("tq-position").value = context.risk.position_pct; $("tq-stop").value = context.risk.stop_loss_pct; $("tq-take").value = context.risk.take_profit_pct;
      if (!value("tq-name")) $("tq-name").value = `${context.symbol} ${context.strategy_name || context.strategy_id}研究`;
      notify("当前表单参数已带入草稿；未保存、未运行。请继续核对封存行情与费用。");
    }
    async function editTask(familyId) {
      const task = await api("terminal_tasks/" + encodeURIComponent(familyId));
      state.revisionOf = task.task_id || task.id;
      state.aiEvidence = task.ai_evidence || null; state.aiEvidenceBinding = task.ai_evidence_binding || null;
      state.aiEvidenceEnabled = Boolean(state.aiEvidence); renderAiEvidence();
      $("tq-form-title").textContent = `2 · 修订任务 · 当前版本 ${task.version}`;
      $("tq-name").value = task.title || task.name; $("tq-strategy").value = task.strategy_id;
      renderParams(task.strategy_params); renderInputs(task.input_id);
      $("tq-position").value = task.risk.position_pct; $("tq-stop").value = task.risk.stop_loss_pct; $("tq-take").value = task.risk.take_profit_pct;
      $("tq-fee").value = task.costs.fee_rate * 100; $("tq-slippage").value = task.costs.slippage_bps;
      $("tq-task-form").scrollIntoView({behavior:"smooth",block:"start"});
      notify("修订将形成新版本；旧结果和原版本保留，暂停状态保持。");
    }
    async function saveTask(event) {
      event.preventDefault(); const form = $("tq-task-form"); if (!form.reportValidity()) return;
      const blocked = researchBlocker(state.catalog.find((entry) => entry.id === value("tq-strategy")));
      if (blocked) return notify(blocked,true);
      const params = {};
      const signalKeys = new Set((state.catalog.find((entry) => entry.id === value("tq-strategy"))?.parameter_fields || []).map((field) => field.key));
      for (const input of form.querySelectorAll("[data-tq-param]")) {
        if (signalKeys.has(input.dataset.tqParam)) params[input.dataset.tqParam] = input.dataset.tqType === "number" ? Number(input.value) : input.dataset.tqType === "boolean" ? input.value === "true" : input.value;
      }
      const payload = {name:value("tq-name").trim(),strategy_id:value("tq-strategy"),strategy_params:params,input_id:value("tq-input"),
        risk:{position_pct:Number(value("tq-position")),take_profit_pct:Number(value("tq-take")),stop_loss_pct:Number(value("tq-stop")),leverage:1},
        costs:{fee_rate:Number(value("tq-fee"))/100,slippage_bps:Number(value("tq-slippage"))},
        ...(state.revisionOf ? {parent_task_id:state.revisionOf} : {}),
        ...(state.aiEvidenceEnabled && validAiEvidence(state.aiEvidence) ? {ai_evidence:state.aiEvidence} : {})};
      await act("terminal_save_task", payload, {button:event.submitter,onSuccess:async (task) => {
        state.revisionOf = task.task_id || task.id; $("tq-form-title").textContent = `2 · 修订任务 · 当前版本 ${task.version}`;
        state.aiEvidence = task.ai_evidence || null; state.aiEvidenceBinding = task.ai_evidence_binding || null;
        state.aiEvidenceEnabled = Boolean(state.aiEvidence); renderAiEvidence();
        await refreshAll(); notify(`任务版本 ${task.version} 已保存。请在任务列表明确选择运行。`);
      }});
    }
    async function showRun(id) {
      const run = await api("terminal_runs/" + encodeURIComponent(id)); state.selectedRun = run;
      if (run.status !== "COMPLETED") {
        $("tq-run-detail").innerHTML = warning(run.message || run.error || "此运行未取得完整结果。原记录保留，不自动重跑，也不使用当前行情补齐。");
        return;
      }
      const result = run.result || {}, config = run.configuration || {}, trades = result.trades || [];
      $("tq-run-detail").innerHTML = `<h3>${esc(run.title || run.strategy_id)} · 版本 ${esc(run.version)}</h3>${warning("冻结研究结果 · 来源待复核 · 不授予模拟或实盘权限")}
        <div class="tq-metrics"><div>收益率<strong>${fmt(result.total_return_pct)}%</strong></div><div>最大回撤<strong>${fmt(result.max_drawdown_pct)}%</strong></div><div>成交事件<strong>${fmt(result.order_event_count ?? trades.length)}</strong></div></div>
        <div class="actions">${button("在行情图表复盘","replay",id)}${button("复制参数到策略分析","copy-params",id)}${button("记录这次结果的判断","judgment-run",id)}${button("出场对照研究","exit-research-run",id,researchBlocker(state.catalog.find((entry) => entry.id === run.strategy_id)) ? "disabled" : "")}</div>
        <details class="section-gap"><summary>本次冻结配置与来源</summary><pre class="code-detail">${esc(JSON.stringify({engine:run.engine_id,configuration:config,input:run.input_summary,report_hash:run.report_hash},null,2))}</pre></details>
        ${config.ai_evidence ? '<h3 class="section-gap">本任务保存的 AI 研究依据</h3>' + aiEvidenceHtml(config.ai_evidence,config.ai_evidence_binding) : ""}
        <div class="tq-table section-gap"><table><thead><tr><th>日期</th><th>动作</th><th>价格</th><th>数量</th><th>原因</th></tr></thead><tbody>${trades.map((trade) => `<tr><td>${esc(trade.date)}</td><td>${esc(trade.side)}</td><td>${fmt(trade.price)}</td><td>${fmt(trade.quantity)}</td><td>${esc(trade.reason || "")}</td></tr>`).join("")}</tbody></table></div>`;
    }
    async function replayTerminal(id) {
      const run = state.selectedRun?.id === id ? state.selectedRun : await api("terminal_runs/" + encodeURIComponent(id));
      const chart = {...run.chart,run_id:run.run_id || run.id,report_hash:run.report_hash};
      if (!validReplay(chart)) throw new Error("冻结复盘数据或身份不完整，未替换原图表。");
      send("replay-result", chart); notify("已在同一工作台图表打开冻结行情与成交。任务和结果仍保留在这里。");
    }
    async function copyParameters(id) {
      const run = state.selectedRun?.id === id ? state.selectedRun : await api("terminal_runs/" + encodeURIComponent(id));
      const config = {...run.configuration,engine_id:run.engine_id,strategy_id:run.strategy_id};
      if (!validConfiguration(config)) throw new Error("冻结配置与原策略引擎不兼容，未复制。");
      send("copy-parameters", config); notify("已复制到原策略分析表单，未运行、未授权。");
    }
    function renderHistory() {
      $("tq-history").innerHTML = state.history.length ? state.history.map((row) => `<div class="tq-row"><div><strong>${esc(row.title || row.strategy_id || row.id)}</strong><p>${esc(row.symbol || "标的未记录")} · ${esc(row.updated_at || "时间未记录")} · ${row.integrity_status === "PASS" ? "记录校验通过" : "旧版关联资料需要核对"}</p><p>${esc(row.replay_reason || "未提供可核验的封存行情")}</p></div>${button("查看原记录","history",row.run_id || row.id)}</div>`).join("") : '<p class="muted">未读取到原策略流水线记录。其它原报告仍可通过上方入口查看。</p>';
    }
    async function showHistory(id) {
      const record = await api("terminal_history/" + encodeURIComponent(id));
      $("tq-history-detail").innerHTML = `${warning(record.replay_reason || "缺少可核验的原封存行情，不能用当前行情替代复盘。")}
        <details class="section-gap" open><summary>原记录与原报告（只读，不重算、不重签）</summary><pre class="code-detail">${esc(JSON.stringify(record,null,2))}</pre></details>`;
    }
    function renderReports() {
      const info = state.reportsPage || {};
      $("tq-reports").innerHTML = (state.reports.length ? state.reports.map((row) => `<div class="tq-row"><div><strong>${esc(row.file_name)}</strong><p>${esc(row.created_at || "时间未记录")} · 历史文件 · 未重新验证原报告</p><p>文件 SHA-256：${esc(row.file_sha256 || row.id)}</p></div>${button("查看历史报告","report",row.id)}</div>`).join("") : '<p class="muted">当前页未读取到原研究报告文件；其它报告仍保留在原位置。</p>')
        + (info.next_page ? button("读取下一页历史报告","reports-page",info.next_page) : "")
        + (info.omitted_by_scope ? `<p class="section-note">有 ${esc(info.omitted_by_scope)} 份文件未包含在本次读取范围。</p>` : "");
    }
    async function showReport(id) {
      const record = await api("terminal_reports/" + encodeURIComponent(id));
      $("tq-report-detail").innerHTML = `<h3>${esc(record.file_name)}</h3>${warning(record.notice || "原历史报告文件，只读；未重新验证原报告，不作为当前报告或交易授权。")}
        <p class="section-note">文件 SHA-256：${esc(record.file_sha256 || record.id)} · 当前报告：否 · 原报告验证：未重跑</p>
        <details class="section-gap" open><summary>原报告内容与文件身份</summary><pre class="code-detail">${esc(JSON.stringify(record,null,2))}</pre></details>`;
    }
    async function compareSelected(target) {
      const ids = [...state.comparison];
      if (!ids.length) return notify("请至少选择一份原工作台冻结结果。",true);
      if (value("tq-core-comparison")) ids.push(value("tq-core-comparison"));
      if (ids.length < 2) return notify("请选择两份结果进行版本比较。",true);
      await act("terminal_compare",{run_ids:ids},{button:target,onSuccess:(comparison) => {
        const rows = comparison.rows || [], comparable = comparison.status === "COMPARABLE_CONDITIONS";
        const keys = new Set(rows.flatMap((row) => Object.keys(comparisonSignalParams(row,state.catalog))));
        const fields = [["引擎规则",(row) => row.engine_id],["策略",(row) => row.configuration?.strategy_id || row.title],
          ...[...keys].map((key) => [key,(row) => comparisonSignalParams(row,state.catalog)[key] ?? "不适用"]),
          ...[["仓位（%）","position_pct"],["止盈（%）","take_profit_pct"],["止损（%）","stop_loss_pct"]].map(([label,key]) => [label,(row) => row.configuration?.risk?.[key] ?? "不适用"]),
          ["收益率（%）",(row) => row.metrics?.total_return_pct ?? "—"],["最大回撤（%）",(row) => row.metrics?.max_drawdown_pct ?? "—"]];
        $("tq-run-detail").innerHTML = `<h3>版本与参数对照</h3>${warning(comparable ? "数据与评分条件可比；参数差异按冻结配置展示。结果仍是独立本金研究。" : "条件不可比：只并排展示参数与结果，不计算跨结果收益差。")}
          <div class="tq-table section-gap"><table><thead><tr><th>字段</th>${rows.map((row) => `<th>${esc(row.title || row.engine_id)}<br>版本 ${esc(row.version ?? "未知")}</th>`).join("")}</tr></thead><tbody>${fields.map(([label,get]) => {const values=rows.map(get);return `<tr><th>${esc(label)}</th>${values.map((value) => `<td ${new Set(values.map(String)).size > 1 ? 'style="background:var(--blue-pale)"' : ""}>${esc(value)}</td>`).join("")}</tr>`;}).join("")}</tbody></table></div>
          ${comparable ? `<p class="section-note section-gap">${(comparison.differences_from_first || []).map((row) => `第 ${row.row} 项相对第一项收益差：${fmt(row.total_return_pct)} 个百分点`).join("；")}</p>` : `<p class="section-note section-gap">差异条件：${esc((comparison.mismatches || []).flatMap((row) => row.fields || []).join("、"))}</p>`}
          <details><summary>完整冻结配置、费用与比较条件</summary><pre class="code-detail">${esc(JSON.stringify(comparison,null,2))}</pre></details>`;
        notify("已展示所选冻结版本，未新增回测。");
      }});
    }
    async function dispatch(action, id, target) {
      if (action === "exit-research-run" || action === "structure-input") {
        if (!exitResearchUI) throw new Error("结构与出场研究模块尚未载入，请重新打开工作台。");
        return action === "structure-input" ? exitResearchUI.replayStructure(value("tq-input")) : exitResearchUI.openSource(id);
      }
      if (["judgment-input","judgment-task","judgment-run"].includes(action)) {
        if (!judgmentUI) throw new Error("判断记录模块尚未载入，请重新打开研究工作台。");
        const kind = {"judgment-input":"terminal_input","judgment-task":"terminal_task","judgment-run":"terminal_run"}[action];
        const selectedId = action === "judgment-input" ? value("tq-input") : id;
        if (!selectedId) throw new Error("请先选择一份已封存行情。");
        return judgmentUI.openSource(kind,selectedId);
      }
      if (action === "refresh") return refreshAll();
      if (action === "new-task-form") return $("tq-form-title").scrollIntoView({behavior:"smooth",block:"start"});
      if (action === "core-task" || action === "core-result") {
        const records = action === "core-task" ? state.coreTasks : state.coreRuns;
        const callback = action === "core-task" ? openCoreTask : openCoreRun;
        if (!records.some((row) => row.id === id) || typeof callback !== "function") throw new Error("未找到对应的原任务或结果详情入口。");
        hide(); return callback(id);
      }
      if (action === "core-create" || action === "core-import") {
        const callback = action === "core-create" ? openCoreTaskForm : openCoreImport;
        if (typeof callback !== "function") throw new Error("原任务或导入表单尚未连接。");
        hide(); return callback();
      }
      if (action === "core-example") {
        if (state.coreOverview?.initialized !== false || state.coreOverview.inputs?.length || typeof initializeCoreExample !== "function") return;
        await initializeCoreExample(target); await refreshAll();
        const message = coreMain.querySelector(".global-message")?.textContent?.trim(); if (message) notify(message);
        return;
      }
      if (action === "market") return readMarket();
      if (action === "context-market") { $("tq-symbol").value = state.context.symbol; return readMarket(state.context.source_id || ""); }
      if (action === "apply-context") return applyContextParams();
      if (action === "new") { state.revisionOf = null; state.aiEvidence = null; state.aiEvidenceBinding = null; state.aiEvidenceEnabled = false; if (state.context) applyContext(state.context); else renderAiEvidence(); $("tq-form-title").textContent = "2 · 新建策略任务"; $("tq-name").value = ""; return notify("正在填写新任务；原任务、版本与结果保持不变。"); }
      if (action === "edit") return editTask(id);
      if (action === "result") return showRun(id);
      if (action === "compare") return compareSelected(target);
      if (action === "replay") return replayTerminal(id);
      if (action === "copy-params") return copyParameters(id);
      if (action === "history") return showHistory(id);
      if (action === "report") return showReport(id);
      if (action === "reports-page") { state.reportsPage = await api("terminal_reports/" + encodeURIComponent(id)); state.reports = state.reportsPage.items || []; return renderReports(); }
      if (action === "original-portfolio" || action === "original-strategy") return send("open-original",{section:action === "original-portfolio" ? "portfolio" : "strategy"});
      if (action === "import-core-input") {
        const input = state.coreInputs.find((row) => identity(row) === value("tq-core-input"));
        if (!input || input.available !== true || !$("tq-confirm-core-input")?.checked) return notify("请先选择通过原输入校验的行情，并核对来源与校验值。",true);
        return act("terminal_import_core_input",{input_id:identity(input)},{button:target,onSuccess:async (created) => {
          await refreshAll(); renderInputs(created.input_id || created.id);
          notify("已复用原行情并选入任务草稿，保留原来源声明与校验值；未运行回测、未提升权限。");
        }});
      }
      if (action === "freeze") {
        if (!$("tq-confirm-market")?.checked || !state.market?.digest) return;
        return act("terminal_freeze_market",{symbol:state.market.symbol,source_id:state.market.source_id,limit:2000,expected_digest:state.market.digest},{button:target,onSuccess:async (input) => {
          await refreshAll(); renderInputs(input.input_id || input.id); notify("行情已封存并选入任务草稿。请核对策略参数后保存任务。");
        }});
      }
      if (action === "run") {
        const task = state.tasks.find((row) => identity(row) === id);
        const blocked = researchBlocker(state.catalog.find((entry) => entry.id === task?.strategy_id));
        if (blocked) return notify(blocked,true);
        return act("terminal_run_task",{task_id:id},{button:target,onSuccess:async (run) => {await refreshAll(); if(run.status !== "COMPLETED") return notify(run.message || run.error || "运行结果待核对；保留原操作，不自动重跑。",true);await showRun(run.run_id || run.id);notify("回测完成，已保留数据、参数版本和结果。");}});
      }
      if (action === "state") {
        const task = state.tasks.find((row) => row.family_id === id);
        return act("terminal_set_task_state",{family_id:id,state:task.state === "PAUSED" ? "ENABLED" : "PAUSED",expected_task_id:task.task_id || task.id},{button:target,onSuccess:async () => {await refreshAll();notify("任务状态已更新，未运行回测。");}});
      }
    }
    host.addEventListener("click", (event) => {
      const target = event.target.closest("[data-tq-action]");
      if (target && !target.disabled) dispatch(target.dataset.tqAction,target.dataset.tqId,target).catch((error) => notify(error.message,true));
    });
    host.addEventListener("change", (event) => {
      if (event.target.id === "tq-strategy") renderParams();
      if (event.target.id === "tq-core-input") renderCoreInputSelection();
      if (event.target.id === "tq-confirm-core-input") host.querySelector('[data-tq-action="import-core-input"]').disabled = !event.target.checked || !state.coreInputs.some((row) => identity(row) === value("tq-core-input") && row.available === true);
      if (event.target.id === "tq-source") readMarket(event.target.value).catch((error) => notify(error.message,true));
      if (event.target.id === "tq-confirm-market") host.querySelector('[data-tq-action="freeze"]').disabled = !event.target.checked;
      if (event.target.dataset.tqCompare) event.target.checked ? state.comparison.add(event.target.dataset.tqCompare) : state.comparison.delete(event.target.dataset.tqCompare);
    });
    $("tq-use-ai").addEventListener("change", (event) => { state.aiEvidenceEnabled = event.target.checked && validAiEvidence(state.aiEvidence); });
    renderAiEvidence();
    $("tq-task-form").addEventListener("submit", (event) => saveTask(event).catch((error) => notify(error.message,true)));
    document.addEventListener("click", (event) => {
      const control = event.target.closest("[data-view]");
      if (!control) return;
      if (["dashboard","tasks","results","insights"].includes(control.dataset.view)) {
        event.preventDefault(); event.stopImmediatePropagation(); show(control.dataset.view); send("context-request",{});
      } else hide();
    }, true);
    window.addEventListener("popstate", () => {
      const view = location.hash.slice(1) || "dashboard";
      if (["dashboard","tasks","results","insights"].includes(view)) show(view,true); else hide();
    });
    window.addEventListener("message", async (event) => {
      if (!validMessage(event,parent,location.origin,["open-terminal","terminal-context","open-insights","bridge-error"])) return;
      if (event.data.kind === "bridge-error") { if (text(event.data.payload.message,1000)) notify(event.data.payload.message,true); return; }
      if (event.data.kind === "open-insights") {
        if (!validInsightsContext(event.data.payload) || !insightsUI) return;
        try { await refreshAll();show("insights");await insightsUI.open(event.data.payload); }
        catch(error) { notify(error.message,true); } return;
      }
      if (!validContext(event.data.payload)) return;
      applyContext(event.data.payload); if (event.data.kind === "open-terminal") show();
    });
    // This button is attached to a verified core result, not a task definition.
    const coreObserver = new MutationObserver(() => {
      if (state.visible) syncUnifiedNavigation();
      const heading = coreMain.querySelector(".result-heading");
      if (!heading || heading.querySelector("[data-core-replay]")) return;
      const control = document.createElement("button"); control.type="button";control.className="btn small";control.dataset.coreReplay="1";control.textContent="在行情图表复盘此结果";
      control.addEventListener("click", async () => {
        try {
          const id = getSelectedCoreRun(); if (!id) throw new Error("请先选择一个冻结结果。");
          const chart = await api("core_replay/" + encodeURIComponent(id));
          if (!validReplay(chart)) throw new Error("此结果缺少可核验的证券或行情身份，未替换原图表。");
          send("replay-result",chart);
        } catch (error) { showError(error); }
      });
      heading.append(control);
    });
    coreObserver.observe(coreMain,{childList:true,subtree:true});
    const initialView = location.hash.slice(1) || "dashboard";
    if (["dashboard","tasks","results","insights"].includes(initialView)) show(initialView,true);
    send("bridge-ready",{});
  };
})();
