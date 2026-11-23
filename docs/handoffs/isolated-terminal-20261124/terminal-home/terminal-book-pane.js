(() => {
  "use strict";

  // Local archives are optional. The public handoff contains no captured quotes.
  const marketReceipts = Object.freeze({});
  const numberFormat = new Intl.NumberFormat("zh-CN", {maximumFractionDigits: 4});
  const timeFormat = new Intl.DateTimeFormat("sv-SE", {
    timeZone: "America/New_York", year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23"
  });
  let host = null;
  let symbol = "";
  let version = 0;
  let result = null;
  let archive = null;
  let dailyRequest = null;
  let active = false;
  let notice = "";
  let depthLimit = 10;

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  const valid = value => Number.isFinite(value);
  const price = value => valid(value) ? value.toLocaleString("en-US", {minimumFractionDigits: 2, maximumFractionDigits: 4}) : "—";
  const size = value => valid(value) ? numberFormat.format(value) : "—";
  const signed = (value, suffix = "") => valid(value) ? (value > 0 ? "+" : "") + value.toFixed(2) + suffix : "—";
  const supported = value => /^[A-Z]{1,6}(?:\.[A-Z])?$/.test(value);

  function eastern(value) {
    if (!value) return "未提供";
    if (value.endsWith(" America/New_York")) return value.replace(" America/New_York", " 美东");
    const date = new Date(value);
    if (!Number.isFinite(date.getTime())) return "未提供";
    const milliseconds = date.getUTCMilliseconds();
    return timeFormat.format(date) + (milliseconds ? "." + String(milliseconds).padStart(3, "0") : "") + " 美东";
  }

  function dailySnapshot(data, ticker) {
    const bars = data?.symbols?.[ticker]?.bars;
    if (!Array.isArray(bars) || !bars.length || data.currency !== "USD") return null;
    const bar = bars[bars.length - 1];
    if (!bar?.date || !valid(bar.close)) return null;
    const previous = bars[bars.length - 2]?.close;
    const change = valid(previous) && previous > 0 ? bar.close - previous : null;
    return {
      daily: true, symbol: ticker, currency: "USD", source: data.provider,
      dailyDate: bar.date, lastPrice: bar.close, openPrice: bar.open, highPrice: bar.high,
      lowPrice: bar.low, previousClose: previous, volume: bar.volume, change,
      changePct: valid(change) ? 100 * change / previous : null
    };
  }

  function getDaily() {
    if (!dailyRequest) {
      dailyRequest = fetch("./market-recent.json", {credentials: "same-origin"})
        .then(response => {
          if (!response.ok) throw Error("archive");
          return response.json();
        }).catch(() => null);
    }
    return dailyRequest;
  }

  function select(value) {
    const next = String(value ?? "").trim().toUpperCase().replace(/^US\./, "");
    if (next === symbol) return;
    symbol = next;
    const selectedVersion = ++version;
    result = null;
    archive = Object.hasOwn(marketReceipts, symbol) ? marketReceipts[symbol].quote : null;
    notice = "";
    render();
    if (!archive && ["QQQ", "SPY", "SOXX"].includes(symbol)) {
      getDaily().then(data => {
        if (version !== selectedVersion) return;
        archive = dailySnapshot(data, symbol);
        render();
      });
    }
  }

  async function read() {
    if (active || !supported(symbol)) return;
    const requested = symbol;
    const requestedVersion = version;
    active = true;
    notice = "";
    render();
    try {
      const reply = await fetch("/api/studio/futu-quote", {
        method: "POST", headers: {"Content-Type": "application/json"}, credentials: "same-origin",
        cache: "no-store", body: JSON.stringify({symbol: requested, includeBook: true}),
        signal: AbortSignal.timeout(120000)
      });
      const data = await reply.json();
      if (requestedVersion !== version) return;
      if (data?.ok === false) {
        notice = data.message || "本次未取得行情。";
      } else if (reply.ok && data?.ok && data.status === "SNAPSHOT" &&
                 data.symbol === requested && data.code === "US." + requested && data.currency === "USD") {
        result = data;
      } else {
        notice = "返回标的或行情格式不符，无法采用本次读取。";
      }
    } catch (err) {
      if (requestedVersion === version) notice = err.name === "TimeoutError" ? "本次本机读取超时。" : "未收到本机行情服务的有效响应。";
    } finally {
      active = false;
      render();
    }
  }

  function metrics(quote) {
    const dl = el("dl", "tbp-metrics");
    const fields = [
      ["开盘", price(quote?.openPrice)], ["最高", price(quote?.highPrice)], ["最低", price(quote?.lowPrice)],
      ["前收", price(quote?.previousClose)], ["成交量（股）", size(quote?.volume)]
    ];
    for (const [name, value] of fields) {
      const item = el("div");
      item.append(el("dt", "", name), el("dd", "", value));
      dl.append(item);
    }
    return dl;
  }

  function topLevel(quote, side) {
    const p = quote?.[side + "Price"];
    return valid(p) && p > 0 ? [{level: 1, price: p, size: quote[side + "Size"]}] : [];
  }

  function bestPrices(bids, asks, timesDiffer) {
    const bid = bids.find(row => row.level === 1);
    const ask = asks.find(row => row.level === 1);
    const block = el("div", "tbp-best");
    for (const [side, label, row] of [["bid", "买一", bid], ["ask", "卖一", ask]]) {
      const item = el("div", "tbp-best-side tbp-best-" + side);
      item.append(el("span", "tbp-label", label), el("strong", "tbp-" + side, price(row?.price)),
                  el("small", "", valid(row?.size) ? size(row.size) + " 股" : "数量未知"));
      block.append(item);
    }
    const spread = el("div", "tbp-spread");
    let value = "—";
    if (bid && ask && !timesDiffer) {
      value = bid.price > ask.price ? "交叉" : price(ask.price - bid.price);
    }
    spread.append(el("span", "tbp-label", "读数价差"), el("strong", "", value),
                  el("small", "", timesDiffer ? "时点未对齐" : "USD"));
    block.append(spread);
    return block;
  }

  function depthQuantity(side, row, maxSize) {
    const cell = el("td", "tbp-quantity tbp-quantity-" + side);
    if (valid(row?.size) && row.size > 0 && maxSize > 0) {
      const bar = el("span", "tbp-depth-bar");
      bar.setAttribute("aria-hidden", "true");
      bar.style.width = (100 * row.size / maxSize) + "%";
      cell.append(bar);
    }
    cell.append(el("span", "tbp-quantity-value", size(row?.size)));
    return cell;
  }

  function ladder(quote) {
    const box = el("section", "tbp-ladder");
    const book = quote?.book;
    const hasDepth = book?.status === "AVAILABLE";
    const bids = hasDepth ? book.bids : topLevel(quote, "bid");
    const asks = hasDepth ? book.asks : topLevel(quote, "ask");
    const hasQuotes = bids.length || asks.length;
    const heading = el("div", "tbp-line");
    heading.append(el("h3", "", "买卖盘口"), el("span", "tbp-chip",
      hasDepth ? "买 " + bids.length + " 档 · 卖 " + asks.length + " 档" : hasQuotes ? "快照一档" : "暂无盘口"));
    box.append(heading);
    if (!hasQuotes) {
      box.append(el("p", "tbp-hint", book?.message || (quote?.daily ? "日线归档没有盘口价量。" : "手动读取可查看富途提供的价格与挂单数量。")));
      return box;
    }
    const bidTime = hasDepth ? book.bidTimeRaw : null;
    const askTime = hasDepth ? book.askTimeRaw : null;
    const timesDiffer = Boolean((bidTime || askTime) && bidTime !== askTime);
    box.append(bestPrices(bids, asks, timesDiffer));
    const readTime = hasDepth ? book.receivedAt : quote.receivedAt;
    const sourceLine = (hasDepth ? "富途摆盘" : "富途快照一档") + " · 采集 " + eastern(readTime);
    box.append(el("p", "tbp-time", sourceLine));
    box.append(el("p", "tbp-time", bidTime || askTime
      ? "盘口接收时点（时区未确认） · 买 " + (bidTime || "未提供") + " · 卖 " + (askTime || "未提供")
      : "盘口时点未提供"));

    const levels = [...new Set([...bids, ...asks].map(row => row.level))].sort((a,b) => a-b);
    const lastLevel = levels.at(-1);
    const maxSize = Math.max(0, ...bids.concat(asks).map(row => valid(row.size) ? row.size : 0));
    const table = el("table", "tbp-table");
    table.setAttribute("aria-label", hasDepth ? "富途摆盘实际返回的挂单价量" : "富途标的快照买一和卖一");
    const head = table.createTHead().insertRow();
    for (const title of ["档", "买量（股）", "买价", "卖价", "卖量（股）"]) {
      const th = el("th", "", title);
      th.scope = "col";
      head.append(th);
    }
    const body = table.createTBody();
    function showLevels(limit) {
      body.replaceChildren();
      for (const level of levels.filter(level => level <= limit)) {
        const bid = bids.find(row => row.level === level);
        const ask = asks.find(row => row.level === level);
        const row = body.insertRow();
        const rank = el("th", "tbp-rank", String(level));
        rank.scope = "row";
        row.append(rank, depthQuantity("bid", bid, maxSize), el("td", "tbp-bid", price(bid?.price)),
                   el("td", "tbp-ask", price(ask?.price)), depthQuantity("ask", ask, maxSize));
      }
    }
    if (lastLevel > 1) {
      const label = el("label", "tbp-depth-choice", "显示至");
      const select = el("select");
      select.setAttribute("aria-label", "显示盘口至第几档");
      const limits = [...new Set([1, 5, 10, lastLevel])].filter(n => n >= levels[0] && n <= lastLevel).sort((a,b) => a-b);
      for (const n of limits) select.add(new Option(n + " 档", String(n)));
      const visibleLimit = limits.find(n => n >= depthLimit) ?? lastLevel;
      select.value = String(visibleLimit);
      select.addEventListener("change", () => {
        depthLimit = Number(select.value);
        showLevels(depthLimit);
      });
      label.append(select);
      box.append(label);
      showLevels(visibleLimit);
    } else {
      showLevels(lastLevel);
    }
    box.append(table);
    if (!hasDepth && book?.message) box.append(el("p", "tbp-hint", "深度盘口：" + book.message));
    if (book?.invalidLevels) box.append(el("p", "tbp-hint", "本次有 " + book.invalidLevels + " 个无效档位，已略过。"));
    if (book?.crossed || (!hasDepth && bids[0] && asks[0] && bids[0].price > asks[0].price)) {
      box.append(el("p", "tbp-hint", "本次买价高于卖价，请核对来源与时点。"));
    }
    return box;
  }

  function provenance(quote, saved) {
    const details = el("details", "tbp-details");
    details.append(el("summary", "", "数据来源与时点"));
    const info = text => details.append(el("p", "", text));
    info("标的行情　" + (quote.source || "来源未提供") + (quote.daily ? " · " + quote.dailyDate + " 日线" : " · 快照更新 " + eastern(quote.sourceTime)));
    if (quote.daily) return details;
    info("快照读取　" + eastern(quote.receivedAt) + " · 行情延迟等级未知");
    if (quote.lastTick) info("逐笔来源　" + quote.lastTick.source + " · 读取 " + eastern(quote.lastTick.receivedAt));
    if (quote.book) {
      const book = quote.book;
      info("盘口来源　" + book.source + (book.bookType ? " · " + book.bookType : "") + " · 读取 " + eastern(book.receivedAt));
      info(book.bidTimeRaw || book.askTimeRaw
        ? "富途服务端接收盘口时点（时区未确认）　买 " + (book.bidTimeRaw || "未提供") + " · 卖 " + (book.askTimeRaw || "未提供")
        : "富途未提供买卖侧盘口时点。");
      if (book.status !== "AVAILABLE") info("快照买一卖一的独立时点未提供。");
    }
    if (saved) info("离线回执 SHA-256　" + marketReceipts[quote.symbol].sha256);
    return details;
  }

  function render() {
    if (!host) return;
    const quote = result || archive;
    const saved = Boolean(!result && archive);
    const heading = el("div", "tbp-head");
    const id = el("div", "tbp-id");
    id.append(el("h2", "", "行情与盘口"), el("span", "tbp-symbol", symbol || "未选标的"));
    const btn = el("button", "tbp-read", active ? "正在读取…" : "读取富途行情");
    btn.type = "button";
    btn.disabled = active || !supported(symbol);
    btn.addEventListener("click", read);
    heading.append(id, btn);
    const panel = [heading];
    if (!supported(symbol)) {
      panel.push(el("p", "tbp-hint", symbol ? "此标的不属于当前美股行情范围。请选择美股股票或 ETF。" : "请选择美股股票或 ETF。"));
      host.replaceChildren(...panel);
      return;
    }
    const flags = [quote ? (saved ? "离线归档" : "本次富途读取") : "等待读取"];
    if (quote?.marketSession) flags.push(quote.marketSession + (saved ? "（采集时）" : "（读取时）"));
    flags.push("USD");
    panel.push(el("div", "tbp-origin", flags.join(" · ")));
    if (notice) {
      const status = el("p", "tbp-notice", notice + (quote ? " 当前保留上次可核对的数据。" : ""));
      status.setAttribute("role", "status");
      panel.push(status);
    }
    const big = el("div", "tbp-price");
    big.append(el("span", "tbp-label", quote?.daily ? "日线收盘" : "最新价"), el("strong", "", price(quote?.lastPrice)));
    const delta = el("span", quote?.change > 0 ? "tbp-up" : quote?.change < 0 ? "tbp-down" : "",
      valid(quote?.change) ? signed(quote.change) + "  (" + signed(quote.changePct, "%") + ")" : "涨跌待补");
    big.append(delta);
    panel.push(big);
    const quoteTime = quote?.daily ? quote.dailyDate + " 美东交易日 · " + quote.source :
      quote ? "快照更新 " + eastern(quote.sourceTime) : "尚未读取此标的";
    panel.push(el("p", "tbp-time", quoteTime), metrics(quote));
    const tick = quote?.lastTick;
    const trade = el("div", "tbp-trade");
    trade.append(el("span", "tbp-label", "最近一笔"));
    if (tick?.status === "AVAILABLE") {
      trade.append(el("strong", "", price(tick.price) + " × " + size(tick.size) + " 股"), el("time", "", eastern(tick.sourceTime)));
    } else {
      trade.append(el("span", "", tick?.message || (quote?.daily ? "日线未附逐笔成交" : "尚无逐笔记录")));
    }
    panel.push(trade, ladder(quote));
    if (quote) panel.push(provenance(quote, saved));
    host.replaceChildren(...panel);
  }

  function mount(root) {
    const target = typeof root === "string" ? document.querySelector(root) : root;
    if (!target || target.nodeType !== 1 || target === host) return;
    host = target;
    host.classList.add("terminal-book-pane");
    render();
  }

  window.TerminalBookPane = Object.freeze({mount, select});
})();
