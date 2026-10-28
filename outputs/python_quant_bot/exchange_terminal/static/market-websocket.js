(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.HakimiMarketWebSocket = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const URLS = Object.freeze({
    public: "wss://ws.okx.com/ws/v5/public",
    business: "wss://ws.okx.com/ws/v5/business",
  });
  const key = (arg) => `${arg?.channel || ""}:${arg?.instId || ""}`;

  function createSession(options = {}) {
    const Socket = options.WebSocketCtor || globalThis.WebSocket;
    const later = options.setTimer || setTimeout;
    const cancel = options.clearTimer || clearTimeout;
    const current = options.isCurrent || (() => true);
    const onData = options.onData || (() => {});
    const onStatus = options.onStatus || (() => {});
    let closed = false;
    let started = false;
    const groups = ["public", "business"].map((name) => {
      const args = (options[`${name}Args`] || []).map((arg) => {
        const allowed = name === "public" ? ["tickers", "books5", "trades"].includes(arg?.channel)
          : /^candle(?:1m|3m|5m|15m|30m|1H|2H|4H|6H|12H|1D|2D|3D|5D|1W|1M|3M)(?:utc)?$/.test(arg?.channel || "");
        if (!allowed || !/^[A-Z0-9][A-Z0-9.-]{0,49}$/.test(arg?.instId || "")) {
          throw new Error("public_market_subscription_invalid");
        }
        return { channel: arg.channel, instId: arg.instId };
      });
      return { name, args, expected: new Set(args.map(key)), acknowledged: new Set(),
        socket: null, retry: null, heartbeat: null, status: "CONNECTING", reason: "", failed: false };
    }).filter((group) => group.args.length);

    function close() {
      closed = true;
      for (const group of groups) {
        cancel(group.retry); cancel(group.heartbeat);
        group.retry = group.heartbeat = null;
        const socket = group.socket;
        group.socket = null;
        if (socket) {
          socket.onopen = socket.onmessage = socket.onerror = socket.onclose = null;
          try { socket.close(); } catch {}
        }
      }
    }
    function active() {
      if (closed) return false;
      if (!current()) { close(); return false; }
      return true;
    }
    function status(group, value, reason = "") {
      if (!active()) return;
      group.status = value; group.reason = reason;
      onStatus({ ready: groups.length > 0 && groups.every((item) => item.status === "READY"),
        error: groups.some((item) => item.status === "ERROR"),
        groups: Object.fromEntries(groups.map((item) => [item.name, { status: item.status, reason: item.reason }])) });
    }
    function reconnect(group) {
      if (!active() || group.retry !== null) return;
      status(group, "RECONNECTING");
      group.retry = later(() => {
        group.retry = null;
        if (active()) open(group);
      }, options.reconnectMs ?? 3000);
    }
    function heartbeat(group, socket) {
      cancel(group.heartbeat);
      group.heartbeat = later(() => {
        if (!active() || group.socket !== socket) return;
        try { socket.send("ping"); } catch { socket.close(); return; }
        group.heartbeat = later(() => {
          if (!active() || group.socket !== socket) return;
          status(group, "ERROR", "heartbeat_timeout");
          socket.close();
        }, options.pongTimeoutMs ?? 10000);
      }, options.pingAfterMs ?? 20000);
    }
    function open(group) {
      if (!active()) return;
      group.acknowledged.clear(); group.failed = false;
      status(group, "CONNECTING");
      let socket;
      try { socket = new Socket(URLS[group.name]); }
      catch { status(group, "ERROR", "connection_failed"); reconnect(group); return; }
      group.socket = socket;
      const owns = () => active() && group.socket === socket;
      socket.onopen = () => {
        if (!owns()) return;
        status(group, "SUBSCRIBING");
        try { socket.send(JSON.stringify({ op: "subscribe", args: group.args })); }
        catch { status(group, "ERROR", "subscription_send_failed"); socket.close(); return; }
        heartbeat(group, socket);
      };
      socket.onmessage = (event) => {
        if (!owns()) return;
        heartbeat(group, socket);
        if (event.data === "pong") return;
        let message;
        try { message = JSON.parse(event.data); }
        catch { status(group, "ERROR", "invalid_message"); return; }
        if (!message || typeof message !== "object") return;
        if (message.event === "error") {
          group.failed = true;
          status(group, "ERROR", `subscription_error:${String(message.code || "UNKNOWN").slice(0, 24)}`);
          return;
        }
        const identity = key(message.arg);
        if (!group.expected.has(identity)) return;
        const hasData = Array.isArray(message.data) && message.data.length > 0;
        if (message.event === "subscribe" || hasData) {
          group.acknowledged.add(identity);
          if (!group.failed && group.acknowledged.size === group.expected.size) status(group, "READY");
        }
        if (hasData && owns()) onData(message, group.name);
      };
      socket.onerror = () => { if (owns()) status(group, "ERROR", "connection_error"); };
      socket.onclose = () => {
        if (!owns()) return;
        cancel(group.heartbeat); group.heartbeat = null; group.socket = null;
        reconnect(group);
      };
    }
    return { close, start() {
      if (started || !active()) return;
      started = true;
      for (const group of groups) open(group);
    } };
  }
  return { URLS, createSession };
});
