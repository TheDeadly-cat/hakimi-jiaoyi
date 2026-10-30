"use strict";

const http = require("http");

function quantPendingState(health) {
  const pending = health?.payload?.quant_workspace?.pending;
  return pending === true ? "BUSY" : pending === false ? "IDLE" : "UNKNOWN";
}

function localResourceAllowed(value, baseUrl) {
  try {
    const url = new URL(value);
    const base = new URL(baseUrl);
    if (url.protocol === "file:") return !url.hostname && !url.pathname.startsWith("//");
    if (url.protocol === "data:") return true;
    if (url.protocol === "blob:") return url.origin === base.origin;
    const protocol = url.protocol === "ws:" ? "http:" : url.protocol === "wss:" ? "https:" : url.protocol;
    return protocol === base.protocol && url.host === base.host && !url.username && !url.password;
  } catch (_) {
    return false;
  }
}

function requestPrepareExit(origin, token, timeoutMs = 5000, transport = http) {
  return new Promise((resolve, reject) => {
    const url = new URL("/api/desktop/prepare-exit", origin);
    const host = url.hostname.replace(/^\[|\]$/g, "").toLowerCase();
    if (url.protocol !== "http:" || !["127.0.0.1", "localhost", "::1"].includes(host)
        || url.username || url.password || typeof token !== "string" || !token) {
      reject(new Error("desktop_control_destination_invalid"));
      return;
    }
    const request = transport.request(url, {
      method: "POST",
      timeout: timeoutMs,
      headers: {
        "Content-Type": "application/json",
        "Content-Length": "2",
        "Origin": url.origin,
        "X-Hakimi-Desktop-Control": token,
      },
    }, (response) => {
      let body = "";
      response.setEncoding("utf8");
      response.on("data", (chunk) => {
        body += chunk;
        if (body.length > 16384) request.destroy(new Error("desktop_control_response_too_large"));
      });
      response.on("error", reject);
      response.on("end", () => resolve({ statusCode: response.statusCode, body }));
    });
    request.on("timeout", () => request.destroy(new Error("desktop_control_timeout")));
    request.on("error", reject);
    request.end("{}");
  });
}

function childHasExited(child) {
  return Boolean(child && (child.exitCode !== null && child.exitCode !== undefined
    || child.signalCode !== null && child.signalCode !== undefined));
}

function waitForChildExit(child, timeoutMs = 12000) {
  if (childHasExited(child)) return Promise.resolve(true);
  return new Promise((resolve) => {
    let timer;
    const done = (exited) => {
      clearTimeout(timer);
      child.removeListener("exit", onExit);
      resolve(exited);
    };
    const onExit = () => done(true);
    child.once("exit", onExit);
    timer = setTimeout(() => done(childHasExited(child)), timeoutMs);
    if (childHasExited(child)) done(true);
  });
}

async function stopOwnedBackend({ child, token, origin, accepted = false,
  request = requestPrepareExit, wait = waitForChildExit }) {
  if (!child) return { ok: false, status: "NOT_OWNED", accepted: false };
  if (childHasExited(child)) return { ok: true, status: "STOPPED", accepted };
  if (!accepted) {
    let response;
    try {
      response = await request(origin, token);
    } catch (_) {
      return { ok: false, status: "UNKNOWN", accepted: false };
    }
    if (response.statusCode === 409) return { ok: false, status: "BUSY", accepted: false };
    let payload;
    try { payload = JSON.parse(response.body); } catch (_) { payload = null; }
    if (response.statusCode !== 200 || payload?.ok !== true || payload?.status !== "closing") {
      return { ok: false, status: "UNKNOWN", accepted: false };
    }
    accepted = true;
  }
  try {
    return await wait(child)
      ? { ok: true, status: "STOPPED", accepted }
      : { ok: false, status: "WAITING", accepted };
  } catch (_) {
    return { ok: false, status: "WAITING", accepted };
  }
}

module.exports = {
  localResourceAllowed,
  quantPendingState,
  requestPrepareExit,
  stopOwnedBackend,
  waitForChildExit,
};
