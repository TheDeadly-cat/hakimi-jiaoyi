(function () {
  function isActiveRequest({ state, runtime, request, requestSeq, requestVersion, requestSymbol, requestBar, requestSession, isStockMarket }) {
    const seq = request?.requestSeq ?? requestSeq;
    const version = request?.requestVersion ?? requestVersion;
    const symbol = request?.requestSymbol ?? requestSymbol;
    const bar = request?.requestBar ?? requestBar;
    const session = request?.requestSession ?? requestSession;
    const stock = typeof isStockMarket === "function" ? isStockMarket(symbol) : false;
    const seqOk = !Number.isFinite(Number(seq)) || Number(seq) === Number(runtime.chartRequestSeq);
    return seqOk
      && version === runtime.symbolVersion
      && state.symbol === symbol
      && state.bar === bar
      && (!stock || state.stockSession === session);
  }

  function createCandleRequest({ state, runtime, requestVersion, chartCacheKey }) {
    const requestSeq = ++runtime.chartRequestSeq;
    const requestSymbol = state.symbol;
    const requestBar = state.bar;
    const requestSession = state.stockSession;
    const version = requestVersion ?? runtime.symbolVersion;
    return {
      requestSeq,
      requestVersion: version,
      requestSymbol,
      requestBar,
      requestSession,
      cacheKey: chartCacheKey(requestSymbol, requestBar, requestSession),
    };
  }

  function cacheIsUsable(cached, isPreviewSource) {
    if (!cached?.rows?.length) return false;
    return !isPreviewSource(cached.meta?.source, cached.meta?.warning);
  }

  function snapshotRefreshDelay(snapshot, { requestSymbol, isStockMarket }) {
    const source = String(snapshot?.candles?.source || "");
    const stock = typeof isStockMarket === "function" ? isStockMarket(requestSymbol) : false;
    const futuReady = stock && Boolean(snapshot?.data_sources?.futu?.opend_online);
    const stockCachedSource = stock && ["stock_sqlite_cache", "offline-seed", "quote_preview_seed"].includes(source);
    if (futuReady && stockCachedSource) return 120;
    if (["quick_preview_seed", "offline-seed", "quote_preview_seed"].includes(source)) return 1400;
    return 700;
  }

  function inFlightKey({ requestSymbol, requestBar, requestSession = "all" }) {
    return `${String(requestSymbol || "").trim().toUpperCase()}|${String(requestBar || "").trim()}|${String(requestSession || "all").trim().toLowerCase()}`;
  }

  function createRefreshCoordinator(options = {}) {
    const now = typeof options.now === "function" ? options.now : () => Date.now();
    const successCooldownMs = Math.max(0, Number(options.successCooldownMs ?? 60_000));
    const failureBaseCooldownMs = Math.max(0, Number(options.failureBaseCooldownMs ?? 5_000));
    const failureMaxCooldownMs = Math.max(failureBaseCooldownMs, Number(options.failureMaxCooldownMs ?? 60_000));
    const maxEntries = Math.max(8, Number(options.maxEntries ?? 128));
    const inFlight = new Map();
    const outcomes = new Map();
    let refreshSequence = 0;

    const currentTime = () => {
      const value = Number(now());
      return Number.isFinite(value) && value >= 0 ? value : Date.now();
    };

    const failureCooldown = (failureCount) => Math.min(
      failureMaxCooldownMs,
      failureBaseCooldownMs * (2 ** Math.max(0, Number(failureCount || 1) - 1)),
    );

    const rememberOutcome = (key, value) => {
      outcomes.delete(key);
      outcomes.set(key, value);
      while (outcomes.size > maxEntries) {
        const oldestKey = outcomes.keys().next().value;
        if (!oldestKey) break;
        outcomes.delete(oldestKey);
      }
    };

    function request({ key, manual = false, task }) {
      const cleanKey = String(key || "").trim();
      if (!cleanKey) return Promise.reject(new Error("refresh_key_required"));
      if (typeof task !== "function") return Promise.reject(new Error("refresh_task_required"));

      const existing = inFlight.get(cleanKey);
      if (existing) {
        existing.joinCount += 1;
        return existing.promise;
      }

      const requestedAt = currentTime();
      const previous = outcomes.get(cleanKey) || null;
      if (!manual && previous && requestedAt < Number(previous.nextAllowedAt || 0)) {
        return Promise.resolve({
          key: cleanKey,
          status: "COOLDOWN",
          value: null,
          refreshId: previous.refreshId || "",
          joined: false,
          lastOutcome: previous.status || "UNKNOWN",
          nextAllowedAt: Number(previous.nextAllowedAt || 0),
        });
      }

      const refreshId = `${cleanKey}|${++refreshSequence}`;
      const entry = { promise: null, joinCount: 0 };
      const work = Promise.resolve()
        .then(task)
        .then((value) => {
          const finishedAt = currentTime();
          const nextAllowedAt = finishedAt + successCooldownMs;
          rememberOutcome(cleanKey, {
            status: "SUCCESS",
            refreshId,
            failureCount: 0,
            finishedAt,
            nextAllowedAt,
          });
          return {
            key: cleanKey,
            status: "FETCHED",
            value,
            refreshId,
            joined: entry.joinCount > 0,
            finishedAt,
            nextAllowedAt,
          };
        }, (error) => {
          const finishedAt = currentTime();
          const previousFailureCount = previous?.status === "FAILED" ? Number(previous.failureCount || 0) : 0;
          const failureCount = previousFailureCount + 1;
          rememberOutcome(cleanKey, {
            status: "FAILED",
            refreshId,
            failureCount,
            finishedAt,
            nextAllowedAt: finishedAt + failureCooldown(failureCount),
          });
          throw error;
        })
        .finally(() => {
          if (inFlight.get(cleanKey) === entry) inFlight.delete(cleanKey);
        });
      entry.promise = work;
      inFlight.set(cleanKey, entry);
      return work;
    }

    return {
      request,
      inFlightCount: () => inFlight.size,
      inFlightPromise: (key) => inFlight.get(String(key || "").trim())?.promise || null,
      outcome: (key) => {
        const value = outcomes.get(String(key || "").trim());
        return value ? { ...value } : null;
      },
    };
  }

  function retryStatusText(current = "") {
    if (current.includes("快速预览")) return `${current} / 真实K线稍后重试`;
    if (current.includes("离线种子") || current.includes("旧缓存")) return `${current} / 实时源稍后重试`;
    return current;
  }

  window.HakimiChartController = {
    cacheIsUsable,
    createRefreshCoordinator,
    createCandleRequest,
    inFlightKey,
    isActiveRequest,
    retryStatusText,
    snapshotRefreshDelay,
  };
}());
