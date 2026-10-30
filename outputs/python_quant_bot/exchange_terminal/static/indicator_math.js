/* Mirrors services/indicator_math.py; cross-language fixtures guard the contract. */
(function (root) {
  "use strict";
  const version = "hakimi-indicators-v1";
  const finite = (value) => typeof value === "number" && Number.isFinite(value) ? value : null;
  function windowSize(window) {
    if (!Number.isInteger(window) || window < 1) throw new Error("indicator_window_must_be_positive_integer");
    return window;
  }
  function sma(values, window) {
    windowSize(window);
    values = values.map(finite);
    return values.map((_, index) => {
      const sample = values.slice(Math.max(0, index + 1 - window), index + 1);
      return sample.length === window && !sample.includes(null) ? finite(sample.reduce((a, b) => a + b, 0) / window) : null;
    });
  }
  function ema(values, window) {
    const alpha = 2 / (windowSize(window) + 1);
    let previous = null;
    return values.map((raw) => {
      const value = finite(raw);
      previous = value === null ? null : previous === null ? value : finite(alpha * value + (1 - alpha) * previous);
      return previous;
    });
  }
  function bollinger(values, window = 20, mult = 2) {
    windowSize(window);
    if (finite(mult) === null || mult < 0) throw new Error("indicator_band_multiplier_invalid");
    values = values.map(finite);
    return sma(values, window).map((mid, index) => {
      if (mid === null) return null;
      const sample = values.slice(index + 1 - window, index + 1);
      const band = Math.sqrt(sample.reduce((sum, value) => sum + (value - mid) ** 2, 0) / window) * mult;
      const upper = finite(mid + band), lower = finite(mid - band);
      return upper !== null && lower !== null ? {upper, mid, lower} : null;
    });
  }
  function macd(values, fast = 12, slow = 26, signal = 9) {
    const a = ema(values, fast), b = ema(values, slow);
    const line = a.map((value, i) => value === null || b[i] === null ? null : finite(value - b[i]));
    const signalLine = ema(line, signal);
    return [line, signalLine, line.map((value, i) => value === null || signalLine[i] === null ? null : finite(value - signalLine[i]))];
  }
  function rsi(values, window = 14) {
    windowSize(window);
    values = values.map(finite);
    const changes = values.map((value, i) => !i || value === null || values[i - 1] === null ? null : value - values[i - 1]);
    const gain = sma(changes.map((v) => v === null ? null : Math.max(v, 0)), window);
    const loss = sma(changes.map((v) => v === null ? null : Math.max(-v, 0)), window);
    return gain.map((g, i) => g === null || loss[i] === null ? null :
      loss[i] === 0 ? (g === 0 ? 50 : 100) : 100 - 100 / (1 + g / loss[i]));
  }
  function momentum(values, window = 20) {
    windowSize(window);
    values = values.map(finite);
    return values.map((value, i) => i < window || values.slice(Math.max(0, i - window), i + 1).includes(null) || values[i - window] === 0
      ? null : finite(value / values[i - window] - 1));
  }
  function atr(rows, window = 14) {
    let previous = null;
    const ranges = rows.map((row) => {
      const high = finite(row.high), low = finite(row.low), close = finite(row.close);
      const valid = high !== null && low !== null && close !== null && high >= close && close >= low;
      const value = valid && previous !== null ? Math.max(high - low, Math.abs(high - previous), Math.abs(low - previous)) : null;
      previous = valid ? close : null;
      return value;
    });
    return sma(ranges, window);
  }
  function chartWindow(rows, start = 0, end = rows.length) {
    // Calculate on the full loaded prefix, then crop. Panning never reseeds a formula.
    const closes = rows.map((row) => row.close);
    return {version, ma20: sma(closes, 20).slice(start, end), ma60: sma(closes, 60).slice(start, end),
      bollinger: bollinger(closes).slice(start, end)};
  }
  const api = Object.freeze({version, sma, ema, bollinger, macd, rsi, momentum, atr, chartWindow});
  root.HakimiIndicators = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
