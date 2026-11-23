/* The market desk uses the terminal's existing symbol and view controllers. */
(() => {
  "use strict";
  const selectedKey = "hakimi.terminal.market.selected.v1";
  let panes;
  let selected;
  let openMarket;

  function bindDeskDividers() {
    const shell = document.querySelector(".app-shell");
    const storageKey = "hakimi.terminal.market.panel-sizes.v1";
    let preferences = {};
    try {
      const stored = JSON.parse(localStorage.getItem(storageKey) || "{}");
      if (stored && typeof stored === "object" && !Array.isArray(stored)) preferences = stored;
    } catch { /* Default widths also work without local storage. */ }
    const parts = [
      {id:"deskWatchDivider", name:"watch", property:"--desk-watch-width", direction:1,
        range: w => [212, Math.min(480, Math.floor(w * .33)), Math.min(344, Math.round(w * .215))]},
      {id:"deskBookDivider", name:"book", property:"--desk-book-width", direction:-1,
        range: w => [232, Math.min(460, Math.floor(w * .32)), Math.min(350, Math.round(w * .225))]},
      {id:"deskChartDivider", name:"plot", property:"--desk-plot-height", direction:1,
        range: (_, h) => [145, Math.max(180, h - 445), Math.min(376, Math.max(195, Math.round(h * .5) - 143))]}
    ];

    const sync = [];
    for (const part of parts) {
      const bar = document.getElementById(part.id);
      let drag = null;
      const coordinate = e => part.name === "plot" ? e.clientY : e.clientX;
      const range = () => part.range(shell.clientWidth || innerWidth, innerHeight);
      function apply(value) {
        const [min,max,initial] = range();
        const size = Math.round(Math.max(min, Math.min(max, Number.isFinite(value) ? value : initial)));
        shell.style.setProperty(part.property, size+"px");
        bar.setAttribute("aria-valuemin", min);
        bar.setAttribute("aria-valuemax", max);
        bar.setAttribute("aria-valuenow", size);
        bar.setAttribute("aria-valuetext", size+" 像素");
        return size;
      }
      function save(value) {
        if (value === null) delete preferences[part.name];
        else preferences[part.name] = value;
        try { localStorage.setItem(storageKey, JSON.stringify(preferences)); } catch { /* Session preference still applies. */ }
      }
      apply(preferences[part.name]);
      sync.push(() => { if (!drag) apply(preferences[part.name]); });
      bar.addEventListener("pointerdown", e => {
        if (e.button !== 0 || drag) return;
        e.preventDefault();
        bar.focus({preventScroll:true});
        drag = {id:e.pointerId, start:coordinate(e), size:Number(bar.getAttribute("aria-valuenow"))};
        bar.setPointerCapture(e.pointerId);
        bar.classList.add("dragging");
      });
      bar.addEventListener("pointermove", e => {
        if (drag?.id === e.pointerId) apply(drag.size + part.direction * (coordinate(e) - drag.start));
      });
      const end = e => {
        if (drag?.id !== e.pointerId) return;
        if (e.type === "pointerup") save(apply(drag.size + part.direction * (coordinate(e) - drag.start)));
        else apply(preferences[part.name]);
        drag = null;
        bar.classList.remove("dragging");
        if (bar.hasPointerCapture(e.pointerId)) bar.releasePointerCapture(e.pointerId);
      };
      bar.addEventListener("pointerup", end);
      bar.addEventListener("pointercancel", end);
      bar.addEventListener("lostpointercapture", end);
      function reset() { save(null); apply(null); }
      bar.addEventListener("dblclick", reset);
      bar.addEventListener("keydown", e => {
        if (e.key === "Home") { e.preventDefault(); reset(); return; }
        const keys = part.name === "plot" ? ["ArrowUp","ArrowDown"] : ["ArrowLeft","ArrowRight"];
        if (!keys.includes(e.key)) return;
        e.preventDefault();
        const delta = (e.key === keys[0] ? -1 : 1) * part.direction * (e.shiftKey ? 32 : 8);
        save(apply(Number(bar.getAttribute("aria-valuenow")) + delta));
      });
    }
    const syncAll = () => sync.forEach(update => update());
    let shellWidth = -1;
    new ResizeObserver(() => {
      if (shell.clientWidth === shellWidth) return;
      shellWidth = shell.clientWidth;
      syncAll();
    }).observe(shell);
    window.addEventListener("resize", syncAll);
  }

  function initialSymbol() {
    try {
      const saved = localStorage.getItem(selectedKey);
      if (saved && /^[A-Z0-9][A-Z0-9.-]{0,39}$/.test(saved)) return saved;
    } catch { /* The terminal can also run with session-only preferences. */ }
    return "QQQ";
  }

  function mount({symbol, onSelect, showMarket, markets}) {
    if (panes) return;
    openMarket = showMarket;
    selected = symbol;
    bindDeskDividers();
    const bind = (component, ids, setup) => {
      try {
        return setup(component);
      } catch (error) {
        console.error("行情工作区加载失败", ids[0], error);
        for (const id of ids) document.getElementById(id).textContent = "此区域暂时无法加载。";
        return null;
      }
    };
    const watch = document.getElementById("terminalWatchPane");
    const chart = document.getElementById("terminalCandlePane");
    const book = document.getElementById("terminalBookPane");
    const research = document.getElementById("terminalInlineResearch");
    panes = [
      bind(window.TerminalMarketPane, [watch.id, chart.id], api => {
        api.mount({watch, chart, symbol, markets, onSelect});
        return api;
      }),
      bind(window.TerminalBookPane, [book.id], api => {
        const panel = api.mount(book) || api;
        panel.select(symbol);
        return panel;
      }),
      bind(window.TerminalResearchPane, [research.id], api => api.mount(research, {symbol, onSelect}) || api)
    ];
    const researchPanel = panes[2];
    if (researchPanel?.quoteHost) {
      const contracts = window.TerminalOptionReference.mount(researchPanel.quoteHost, quote => researchPanel.useOptionQuote(quote));
      contracts.select(symbol);
      panes.push(contracts);
    }
    document.getElementById("factorResearchOpen").addEventListener("click", () => {
      showMarket();
      panes[2]?.showTab("factors");
      research.scrollIntoView({block:"nearest"});
      research.querySelector("button")?.focus({preventScroll:true});
    });
  }

  function select(symbol) {
    if (!panes || !symbol || selected === symbol) return;
    selected = symbol;
    try { localStorage.setItem(selectedKey, symbol); } catch { /* Keep the active selection in memory. */ }
    for (const pane of panes) pane?.select(symbol);
  }

  function home() {
    if (!openMarket) return;
    openMarket();
    window.scrollTo(0, 0);
    document.querySelector(".terminal")?.scrollTo(0, 0);
  }

  window.HakimiMarketDesk = {initialSymbol, mount, select, home};
})();
