/* The quant workspace is a persistent panel inside the existing terminal. */
(() => {
  "use strict";

  const host = document.getElementById("quantStrategyWorkspace");
  if (!host) return;
  const panel = document.getElementById("quantModulePanel");
  const frame = document.getElementById("quantModuleFrame");
  const feedback = document.getElementById("quantModuleFeedback");
  const feedbackText = document.getElementById("quantModuleFeedbackText");
  const retry = document.getElementById("quantModuleRetry");
  const legacyHint = document.getElementById("quantLegacyHint");
  const choices = [...host.querySelectorAll("[data-strategy-panel]")];
  let selected = "quant";
  let view = "platform";
  let frameStarted = false;
  let frameReady = false;
  let documentLoads = 0;
  let slowTimer = null;
  let bridgeReady = false;
  let pendingContext = null;
  let pendingInsights = null;
  const protocol = globalThis.HakimiTerminalQuantProtocol;

  function postContext(kind, context) {
    if (!protocol?.validContext(context)) return;
    frame.contentWindow.postMessage({schema:protocol.SCHEMA,kind,payload:context},location.origin);
  }

  function openTerminal(context) {
    if (!protocol?.validContext(context)) return;
    pendingContext = context;
    pendingInsights = null;
    select("quant");
    globalThis.setInterfaceView?.("bot");
    host.scrollIntoView({behavior:"smooth",block:"start"});
    if (bridgeReady) {
      postContext("open-terminal", pendingContext);
      pendingContext = null;
    }
  }

  function openInsights(section = "structure") {
    const context = globalThis.HakimiTerminalBridge?.insightsContext?.();
    const payload = {...context,section};
    if (!protocol?.validInsightsContext(payload)) return;
    pendingInsights = payload; pendingContext = null;
    select("quant"); globalThis.setInterfaceView?.("bot");
    host.scrollIntoView({behavior:"smooth",block:"start"});
    if (bridgeReady) {
      frame.contentWindow.postMessage({schema:protocol.SCHEMA,kind:"open-insights",payload},location.origin);
      pendingInsights = null;
    }
  }

  function fitFrameToViewport() {
    if (view !== "bot" || selected !== "quant") return;
    const top = Math.max(0, frame.getBoundingClientRect().top);
    frame.style.setProperty("--quant-available-height", `${Math.max(360, window.innerHeight - top - 18)}px`);
  }

  function showFeedback(message, failed = false) {
    feedback.hidden = false;
    feedback.classList.toggle("failed", failed);
    feedbackText.textContent = message;
    retry.hidden = !failed;
  }

  function loadFrame() {
    if (frameStarted) return;
    frameStarted = true;
    showFeedback("正在打开本地任务与回测…");
    frame.setAttribute("aria-busy", "true");
    frame.src = "/quant/";
    slowTimer = setTimeout(() => {
      if (!frameReady) {
        showFeedback("本地模块仍在加载，请稍候。可以切换到其他页面，当前加载会继续。");
      }
    }, 12000);
  }

  function render() {
    // Keep the loaded browsing context laid out when leaving the strategy view.
    // In particular, a modal form must survive a trip through another workspace.
    const parked = frameStarted && view !== "bot";
    if (view === "bot") {
      const width = host.getBoundingClientRect().width;
      if (width > 0) host.style.setProperty("--quant-parked-width", `${width}px`);
    }
    host.hidden = !frameStarted && view !== "bot";
    host.classList.toggle("quant-parked", parked);
    host.inert = parked;
    host.setAttribute("aria-hidden", String(view !== "bot"));
    const quantVisible = view === "bot" && selected === "quant";
    document.body.classList.toggle("quant-active", quantVisible);
    const panelParked = frameStarted && selected !== "quant";
    panel.hidden = !frameStarted && selected !== "quant";
    panel.classList.toggle("quant-panel-parked", panelParked);
    panel.inert = panelParked;
    panel.setAttribute("aria-hidden", String(selected !== "quant"));
    legacyHint.hidden = selected !== "legacy";
    choices.forEach((button) => {
      const active = button.dataset.strategyPanel === selected;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    if (quantVisible) {
      loadFrame();
      requestAnimationFrame(fitFrameToViewport);
    }
  }

  function select(next) {
    selected = next === "legacy" ? "legacy" : "quant";
    render();
  }

  frame.addEventListener("load", () => {
    if (!frameStarted) return;
    frame.dataset.documentLoads = String(++documentLoads);
    clearTimeout(slowTimer);
    frame.setAttribute("aria-busy", "false");
    try {
      const documentLoaded = frame.contentDocument;
      if (!documentLoaded?.getElementById("main")) {
        showFeedback("任务与回测暂未打开。策略分析与模拟记录仍可使用，请稍后重试。", true);
        return;
      }
      frameReady = true;
      feedback.hidden = true;
      requestAnimationFrame(fitFrameToViewport);
    } catch (_) {
      showFeedback("本地模块暂未连接，请稍后重试。", true);
    }
  });
  frame.addEventListener("error", () => {
    clearTimeout(slowTimer);
    frame.setAttribute("aria-busy", "false");
    showFeedback("本地模块暂未连接，请稍后重试。", true);
  });
  retry.addEventListener("click", () => {
    // A retry is offered only before a successful module load. Never reload a
    // live form or an operation merely because another panel was selected.
    if (frameReady) return;
    frameStarted = false;
    loadFrame();
  });
  choices.forEach((button) => button.addEventListener("click", () => select(button.dataset.strategyPanel)));
  window.addEventListener("resize", () => requestAnimationFrame(fitFrameToViewport));
  document.querySelectorAll("[data-open-quant]").forEach((button) => {
    button.addEventListener("click", () => {
      select("quant");
      globalThis.setInterfaceView?.("bot");
      host.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
  document.querySelectorAll("[data-open-terminal-research]").forEach((button) => {
    button.addEventListener("click", () => openTerminal(globalThis.HakimiTerminalBridge?.context(button.dataset.openTerminalResearch)));
  });
  document.querySelectorAll("[data-open-terminal-insights]").forEach((button) => {
    button.addEventListener("click", () => openInsights(button.dataset.openTerminalInsights));
  });
  window.addEventListener("message", (event) => {
    if (!protocol?.validMessage(event,frame.contentWindow,location.origin,
      ["bridge-ready","context-request","replay-result","copy-parameters","open-original"])) return;
    try {
      if (event.data.kind === "bridge-ready") {
        bridgeReady = true;
        if (pendingInsights) {
          frame.contentWindow.postMessage({schema:protocol.SCHEMA,kind:"open-insights",payload:pendingInsights},location.origin);
          pendingInsights = null;
        } else postContext(pendingContext ? "open-terminal" : "terminal-context",pendingContext || globalThis.HakimiTerminalBridge?.context());
        pendingContext = null;
      } else if (event.data.kind === "context-request") {
        postContext("terminal-context",globalThis.HakimiTerminalBridge?.context());
      } else if (event.data.kind === "replay-result" && protocol.validReplay(event.data.payload)) {
        globalThis.HakimiTerminalBridge?.replay(event.data.payload);
      } else if (event.data.kind === "copy-parameters" && protocol.validConfiguration(event.data.payload)) {
        globalThis.HakimiTerminalBridge?.copyParameters(event.data.payload);
      } else if (event.data.kind === "open-original" && ["portfolio","strategy"].includes(event.data.payload.section)) {
        globalThis.HakimiTerminalBridge?.openOriginal(event.data.payload.section);
      }
    } catch (error) {
      frame.contentWindow.postMessage({schema:protocol.SCHEMA,kind:"bridge-error",payload:{message:error.message}},location.origin);
    }
  });

  globalThis.HakimiQuantModule = {
    select,
    openTerminal,
    openInsights,
    onView(next) {
      view = next;
      render();
    },
    focusTarget(selector) {
      if (selector === ".strategy-desk") {
        return selected === "quant" ? ".quant-strategy-workspace" : selector;
      }
      if (/strategy|orders-panel|signals-panel|risk-panel|conditional-panel/.test(String(selector))) {
        select("legacy");
      }
      return selector;
    },
  };
})();
