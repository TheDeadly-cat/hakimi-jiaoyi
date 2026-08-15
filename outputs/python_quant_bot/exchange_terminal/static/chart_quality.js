(function () {
  function sourceLabel(source, originSource = "") {
    const text = String(source || "").toLowerCase();
    const origin = originSource ? sourceLabel(originSource) : "";
    if (text === "offline-seed") return "离线种子";
    if (text === "stock_sqlite_cache") return origin ? `本地K线库(${origin})` : "本地K线库";
    if (text === "futu") return "Futu OpenD";
    if (text === "yahoo") return "Yahoo";
    if (text === "yahoo_adjusted") return "Yahoo Adj";
    if (text === "yahoo_intraday_daily") return "Yahoo盘中日K";
    if (text === "quote_preview_seed" || text === "client_quote_preview") return "报价预览";
    if (text === "stooq") return "Stooq";
    if (text === "stooq_intraday_daily") return "Stooq盘中日K";
    if (text === "memory_cache") return "内存缓存";
    if (text === "client_quick_preview" || text === "quick_preview_seed") return "快速预览";
    if (text === "okx_realtime_candles") return "OKX实时";
    if (text === "okx" || text === "rest") return "OKX";
    if (text === "external") return "外部行情源";
    return source || "--";
  }

  function isPreviewSource(source, warning = "") {
    const text = String(source || "").toLowerCase();
    const warningText = String(warning || "").toLowerCase();
    return ["offline-seed", "client_quick_preview", "quick_preview_seed", "quote_preview_seed", "client_quote_preview"].includes(text)
      || warningText.includes("seed")
      || warningText.includes("预览");
  }

  function ageText(ms) {
    const value = Number(ms);
    if (!Number.isFinite(value) || value <= 0) return "--";
    if (value < 60_000) return `${Math.max(1, Math.round(value / 1000))}秒`;
    if (value < 3_600_000) return `${Math.round(value / 60_000)}分钟`;
    if (value < 86_400_000) return `${Math.round(value / 3_600_000)}小时`;
    return `${Math.round(value / 86_400_000)}天`;
  }

  function isDailyBar(bar = "") {
    const text = String(bar || "").toLowerCase();
    return ["1d", "d", "day", "daily"].includes(text);
  }

  function weekdayTradingDaysBetween(fromTs, toTs) {
    const from = Number(fromTs);
    const to = Number(toTs);
    if (!Number.isFinite(from) || !Number.isFinite(to) || from <= 0 || to <= 0 || to < from) return 999;
    const cursor = new Date(from);
    cursor.setHours(0, 0, 0, 0);
    const end = new Date(to);
    end.setHours(0, 0, 0, 0);
    let days = 0;
    cursor.setDate(cursor.getDate() + 1);
    while (cursor <= end && days <= 10) {
      const weekday = cursor.getDay();
      if (weekday !== 0 && weekday !== 6) days += 1;
      cursor.setDate(cursor.getDate() + 1);
    }
    return days;
  }

  function isRecentStockDaily({ bar = "1d", latestTs = 0, ageMs = 0, now = Date.now() } = {}) {
    if (!isDailyBar(bar) || !Number.isFinite(Number(latestTs)) || Number(latestTs) <= 0) return false;
    const age = Number(ageMs);
    if (Number.isFinite(age) && age > 5 * 86_400_000) return false;
    return weekdayTradingDaysBetween(Number(latestTs), Number(now)) <= 1;
  }

  function latestCandleTimeText(rows = [], latestTs = 0, formatTime = null) {
    const ts = Number(latestTs) || Math.max(0, ...rows.map((row) => Number(row.ts || row.ts_ms || 0)));
    if (!Number.isFinite(ts) || ts <= 0) return "";
    return typeof formatTime === "function" ? formatTime(ts) : new Date(ts).toLocaleString("zh-CN", { hour12: false });
  }

  function qualityFromSource(args = {}, deps = {}) {
    const {
      symbol,
      bar,
      rows = [],
      source = "",
      warning = "",
      originSource = "",
      latestTs = 0,
      latestAt = "",
      realtime = null,
      fallback = false,
      cached = false,
      cacheAgeMs = 0,
      dataAgeMs = null,
      marketSession = null,
    } = args;
    const cleanSource = String(source || "").toLowerCase();
    const label = sourceLabel(source, originSource);
    const preview = isPreviewSource(source, warning);
    const warningLower = String(warning || "").toLowerCase();
    const rowLatestTs = Number(latestTs) || Math.max(0, ...rows.map((row) => Number(row.ts || row.ts_ms || 0)));
    const now = typeof deps.now === "function" ? deps.now() : Date.now();
    const computedAgeMs = rowLatestTs > 0 ? Math.max(0, now - rowLatestTs) : 0;
    const ageMs = Number.isFinite(Number(dataAgeMs)) && Number(dataAgeMs) > 0 ? Number(dataAgeMs) : computedAgeMs;
    const intervalMs = typeof deps.barToMs === "function" ? deps.barToMs(bar) : 60_000;
    const staleLimitMs = Math.max(intervalMs * 3, 90_000);
    const isStock = typeof deps.isStockMarket === "function" ? deps.isStockMarket(symbol) : false;
    const isLocalStockCache = cleanSource === "stock_sqlite_cache";
    const sourceFallback = Boolean(fallback) || cleanSource === "offline-seed" || isLocalStockCache || cleanSource.includes("fallback") || cleanSource.includes("local_");
    const recentStockDaily = isStock && isRecentStockDaily({ bar, latestTs: rowLatestTs, ageMs, now });
    const staleStockCache = isStock && !recentStockDaily && (isLocalStockCache || warningLower.includes("stale") || warningLower.includes("behind current session"));
    let isRealtime = realtime === true;
    if (realtime === null || realtime === undefined) {
      isRealtime = !preview && !sourceFallback && rowLatestTs > 0 && ageMs <= staleLimitMs;
    }
    if (preview || sourceFallback) isRealtime = false;
    if (isStock && cleanSource !== "futu") isRealtime = false;
    let mode = "延迟";
    let tone = "flat";
    let warningText = "注意数据延迟，仅用于研究";
    if (preview) {
      mode = "预览";
      tone = "down";
      warningText = "预览K线，不用于行情判断";
    } else if (sourceFallback) {
      mode = recentStockDaily && isLocalStockCache ? "上一交易日" : staleStockCache ? "旧缓存" : "兜底";
      tone = recentStockDaily && isLocalStockCache ? "flat" : "down";
      warningText = recentStockDaily && isLocalStockCache
        ? "Futu离线，显示最近交易日历史K线；不是实时盘口。"
        : staleStockCache
        ? `本地K线约${ageText(ageMs)}前，非实时行情；启动 Futu OpenD 后刷新。`
        : "本地/兜底数据，需等实时源复核";
    } else if (isRealtime) {
      mode = "实时";
      tone = "up";
      warningText = "可用于当前观察，仍仅研究";
    } else if (isStock) {
      mode = "延迟";
      tone = "flat";
      warningText = "股票源延迟，等待Futu实时源更佳";
    }
    const session = marketSession && typeof marketSession === "object" ? marketSession : {};
    const sessionStatus = String(session.status || "").toUpperCase();
    const sessionRelation = String(session.session_relation || "").toUpperCase();
    const sessionStatusLabel = String(session.status_label || "");
    const phaseLabel = String(session.phase_label || session.active_session_label || "");
    if (isStock && !preview && !staleStockCache && Object.keys(session).length) {
      if (sessionRelation === "LAST_SESSION") {
        mode = "上一交易时段";
        tone = sourceFallback ? "flat" : tone;
        warningText = `${sessionStatusLabel || phaseLabel || "当前非所选时段"}，图表展示所选时段最近完成的数据；不是当前时段价格。`;
      } else if (sessionRelation === "HISTORICAL_SESSION") {
        mode = "历史时段";
        tone = "flat";
        warningText = `${phaseLabel || "当前市场"}与所选图表时段不同，当前展示历史时段数据。`;
      } else if (sessionStatus === "LIVE_SESSION") {
        mode = sessionStatusLabel || `${phaseLabel || "行情"}进行中`;
        tone = isRealtime ? "up" : "flat";
        warningText = isRealtime
          ? `${mode}，提供方已确认；仍仅用于研究和模拟验证。`
          : `${mode}，但当前K线源存在延迟，等待刷新确认。`;
      } else if (sessionStatus === "SESSION_BREAK") {
        mode = sessionStatusLabel || "盘中休市";
        tone = "flat";
        warningText = "当前处于盘中休市，图表保留最近有效行情。";
      } else if (sessionStatus === "DELAYED_SOURCE") {
        mode = sessionStatusLabel || "时段推断";
        tone = "flat";
        warningText = "交易时段由本地时钟推断，尚未得到行情提供方确认。";
      } else if (sessionStatus === "HALTED") {
        mode = "停牌/异常";
        tone = "down";
        warningText = "证券状态异常或停牌，行情仅供核对。";
      }
    }
    if (warning && !preview && !sourceFallback) warningText = warning;
    const formatTime = deps.formatCandleTime || null;
    const latestText = isStock
      ? (latestAt || latestCandleTimeText(rows, rowLatestTs, formatTime))
      : (latestCandleTimeText(rows, rowLatestTs, formatTime) || latestAt);
    const cacheText = cached ? ` / 缓存${ageText(cacheAgeMs)}` : "";
    const staleText = staleStockCache ? " / 旧缓存" : "";
    const freshnessAgeText = recentStockDaily && !isRealtime ? "上一交易日" : ageText(ageMs);
    return {
      symbol,
      bar,
      source,
      sourceLabel: label,
      latestTs: rowLatestTs,
      latestAt: latestText,
      dataAgeMs: ageMs,
      realtime: isRealtime,
      fallback: sourceFallback,
      preview,
      cached: Boolean(cached),
      mode,
      tone,
      warningText,
      marketSession: session,
      sessionStatus,
      sessionRelation,
      sessionLabel: sessionStatusLabel || phaseLabel,
      sourceText: `${label}${cacheText}${staleText}`,
      freshnessText: latestText ? `${latestText} / ${freshnessAgeText}` : "--",
    };
  }

  function marketDataBadge(item = {}, now = Date.now()) {
    const source = String(item.source || "").toLowerCase();
    const warning = String(item.warning || "").toLowerCase();
    const ageMs = Number.isFinite(Number(item.dataAgeMs)) && Number(item.dataAgeMs) > 0
      ? Number(item.dataAgeMs)
      : item.lastUpdated ? Math.max(0, now - Number(item.lastUpdated)) : 0;
    if (isPreviewSource(source, warning)) {
      return { label: "预览", tone: "down", detail: "切换临时预览，不用于行情判断" };
    }
    const stockDailyRecent = item.type === "stock" && isRecentStockDaily({
      bar: item.bar || item.interval || "1d",
      latestTs: item.latestTs || item.latest_ts || item.lastUpdated || item.last_updated,
      ageMs,
      now,
    });
    if (stockDailyRecent && source === "stock_sqlite_cache") {
      return { label: "上一交易日", tone: "flat", detail: `本地日线 / ${ageMs ? ageText(ageMs) : "最近交易日"} / 非实时盘口` };
    }
    if (source === "stock_sqlite_cache" || warning.includes("stale") || warning.includes("behind current session")) {
      return { label: "旧缓存", tone: "down", detail: ageMs ? `本地缓存约${ageText(ageMs)}前` : "本地旧缓存" };
    }
    if (item.type === "stock" && source !== "futu") {
      return { label: "延迟", tone: "flat", detail: `${sourceLabel(source, item.originSource || item.origin_source)} / ${ageMs ? ageText(ageMs) : "等待刷新"}` };
    }
    if (source === "futu" || source === "okx_realtime_candles" || source === "okx") {
      const realtime = ageMs > 0 && ageMs <= (item.type === "stock" ? 90_000 : 30_000);
      return { label: realtime ? "实时" : "缓存", tone: realtime ? "up" : "flat", detail: `${sourceLabel(source)} / ${ageMs ? ageText(ageMs) : "刚更新"}` };
    }
    return { label: ageMs ? "缓存" : "待定", tone: "flat", detail: `${sourceLabel(source)}${ageMs ? ` / ${ageText(ageMs)}` : ""}` };
  }

  window.HakimiChartQuality = {
    ageText,
    latestCandleTimeText,
    marketDataBadge,
    qualityFromSource,
    sourceLabel,
    isPreviewSource,
    isRecentStockDaily,
  };
}());
