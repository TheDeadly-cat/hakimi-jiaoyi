(function attachStockQuoteGuard(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.HakimiStockQuoteGuard = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createStockQuoteGuard() {
  const DEFAULT_SOFT_DEVIATION = 0.08;
  const DEFAULT_HARD_DEVIATION = 0.45;
  const DEFAULT_CHANGE_TOLERANCE_PCT = 0.75;
  const UNTRUSTED_SOURCE_MARKERS = ["OFFLINE", "SEED", "PREVIEW", "SYNTHETIC"];

  // A fallback quote must not overwrite a better source that is already
  // visible for the same symbol.  This is a display-integrity rule only; it
  // never grants execution authority.
  const SOURCE_RANKS = [
    ["futu", 40],
    ["yahoo", 30],
    ["stooq", 30],
    ["external", 25],
    ["sqlite", 20],
    ["cache", 20],
    ["local", 20],
    ["offline", 10],
    ["seed", 10],
    ["preview", 10],
  ];

  function normalizeSource(value) {
    return String(value || "").trim().toLowerCase().replaceAll(" ", "_");
  }

  function sourceRank(value) {
    const source = normalizeSource(value);
    if (!source) return 0;
    const match = SOURCE_RANKS.find(([marker]) => source.includes(marker));
    return match ? match[1] : 15;
  }

  function canonicalSymbol(value) {
    const symbol = String(value || "").trim().toUpperCase();
    return symbol.startsWith("US.") ? symbol.slice(3) : symbol;
  }

  function shouldAcceptStockQuoteContext({ incoming = {}, current = null, nowMs = Date.now(), staleAfterMs = 15 * 60 * 1000 } = {}) {
    const incomingSymbol = canonicalSymbol(incoming.symbol || incoming.instId);
    const incomingPrice = finitePositive(incoming.last);
    if (!incomingSymbol || !incomingPrice) return { allowed: false, reason: "invalid_quote_context" };
    if (!current || canonicalSymbol(current.symbol) !== incomingSymbol || !finitePositive(current.last)) {
      return { allowed: true, reason: "initial_quote_context", rank: sourceRank(incoming.source) };
    }
    const incomingSource = normalizeSource(incoming.source || incoming.origin_source);
    const currentSource = normalizeSource(current.source || current.origin_source);
    const incomingTs = Number(incoming.ts || incoming.updated_at || 0);
    const currentTs = Number(current.ts || current.updated_at || 0);
    const currentAge = currentTs > 0 ? Math.max(0, Number(nowMs) - currentTs) : Number.POSITIVE_INFINITY;
    const incomingRank = sourceRank(incomingSource);
    const currentRank = sourceRank(currentSource);
    if (incomingRank < currentRank && currentAge <= Number(staleAfterMs)) {
      return { allowed: false, reason: "lower_quality_source", rank: incomingRank, currentRank };
    }
    if (incomingRank === currentRank && incomingTs > 0 && currentTs > 0 && incomingTs < currentTs) {
      return { allowed: false, reason: "older_quote_timestamp", rank: incomingRank };
    }
    return { allowed: true, reason: "source_accepted", rank: incomingRank };
  }

  function finitePositive(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
  }

  function reject(reason, deviation = null) {
    return { allowed: false, verified: false, reason, deviation };
  }

  function evaluateStockQuoteOverlay(input = {}) {
    const price = finitePositive(input.price);
    const candleClose = finitePositive(input.candleClose);
    if (!price || !candleClose) return reject("invalid_price");

    const deviation = Math.abs(price - candleClose) / candleClose;
    const source = String(input.source || "").trim().toUpperCase();
    if (!source || UNTRUSTED_SOURCE_MARKERS.some((marker) => source.includes(marker))) {
      return reject("untrusted_source", deviation);
    }

    const quoteQuality = input.quoteQuality && typeof input.quoteQuality === "object" ? input.quoteQuality : {};
    if (quoteQuality.quarantined) return reject("quarantined_quote", deviation);
    if (String(quoteQuality.status || "").toUpperCase() !== "READY") {
      return reject("quote_not_ready", deviation);
    }

    const softDeviation = Number.isFinite(Number(input.softDeviation))
      ? Number(input.softDeviation)
      : DEFAULT_SOFT_DEVIATION;
    const hardDeviation = Number.isFinite(Number(input.hardDeviation))
      ? Number(input.hardDeviation)
      : DEFAULT_HARD_DEVIATION;
    if (deviation > hardDeviation) return reject("hard_scale_mismatch", deviation);
    if (deviation <= softDeviation) {
      return { allowed: true, verified: true, reason: "ready_near_chart", deviation };
    }

    const previousClose = finitePositive(input.previousClose);
    const changeBasis = String(input.changeBasis || "").toLowerCase();
    const declaredChangePct = Number(input.changePct);
    if (changeBasis !== "previous_close" || !previousClose || !Number.isFinite(declaredChangePct)) {
      return reject("large_move_missing_evidence", deviation);
    }

    const baselineDeviation = Math.abs(previousClose - candleClose) / candleClose;
    if (baselineDeviation > softDeviation) return reject("previous_close_mismatch", deviation);

    const computedChangePct = (price / previousClose - 1) * 100;
    const tolerance = Number.isFinite(Number(input.changeTolerancePct))
      ? Number(input.changeTolerancePct)
      : DEFAULT_CHANGE_TOLERANCE_PCT;
    if (Math.abs(computedChangePct - declaredChangePct) > tolerance) {
      return reject("change_mismatch", deviation);
    }

    return {
      allowed: true,
      verified: true,
      reason: "verified_large_move",
      deviation,
      baselineDeviation,
      computedChangePct,
    };
  }

  function chooseStockDisplayQuote(input = {}) {
    const price = finitePositive(input.price);
    const candleClose = finitePositive(input.candleClose);
    const previousCandleClose = finitePositive(input.previousCandleClose);
    const decision = evaluateStockQuoteOverlay(input);
    const useChart = input.chartTrusted === true && candleClose > 0 && !decision.allowed;
    const chartChangePct = previousCandleClose > 0
      ? (candleClose / previousCandleClose - 1) * 100
      : 0;
    return {
      decision,
      useChart,
      displayPrice: useChart ? candleClose : price,
      displayChangePct: useChart ? chartChangePct : Number(input.changePct || 0),
    };
  }

  return {
    DEFAULT_SOFT_DEVIATION,
    DEFAULT_HARD_DEVIATION,
    chooseStockDisplayQuote,
    evaluateStockQuoteOverlay,
    canonicalSymbol,
    normalizeSource,
    shouldAcceptStockQuoteContext,
    sourceRank,
  };
});
