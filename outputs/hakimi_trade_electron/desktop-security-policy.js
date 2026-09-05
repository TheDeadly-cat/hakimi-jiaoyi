"use strict";

function parseSafeUrl(value) {
  if (typeof value !== "string" || /[\u0000-\u0020\u007f\\]/.test(value)
      || /%(?:0[0-9a-f]|1[0-9a-f]|7f)/i.test(value)) return null;
  try {
    const parsed = new URL(value);
    if (parsed.username || parsed.password) return null;
    return parsed;
  } catch {
    return null;
  }
}

function externalUrl(value) {
  const parsed = parseSafeUrl(value);
  if (!parsed || !/^https:\/\//i.test(value) || parsed.protocol !== "https:") return null;
  return parsed.href;
}

function isInternalUrl(value, baseUrl, bootUrl) {
  const parsed = parseSafeUrl(value);
  const base = parseSafeUrl(baseUrl);
  if (!parsed || !base) return false;
  return (parsed.protocol === "http:" && parsed.origin === base.origin)
    || (parsed.protocol === "file:" && parsed.href === bootUrl);
}

function installNavigationPolicy(webContents, { baseUrl, bootUrl, openExternal }) {
  const openSafeExternal = (value) => {
    const safeUrl = externalUrl(value);
    if (safeUrl) Promise.resolve(openExternal(safeUrl)).catch(() => {});
  };
  webContents.setWindowOpenHandler(({ url }) => {
    if (isInternalUrl(url, baseUrl, bootUrl)) {
      Promise.resolve(webContents.loadURL(url)).catch(() => {});
    } else {
      openSafeExternal(url);
    }
    // Reuse the window with the installed policy; never create an unguarded child.
    return { action: "deny" };
  });
  for (const eventName of ["will-navigate", "will-redirect"]) {
    webContents.on(eventName, (event, url) => {
      if (isInternalUrl(url, baseUrl, bootUrl)) return;
      event.preventDefault();
      openSafeExternal(url);
    });
  }
}

function configureRemoteDebugging(app, env) {
  for (const name of ["remote-debugging-port", "remote-debugging-address", "remote-allow-origins"]) {
    app.commandLine.removeSwitch(name);
  }
  if (app.isPackaged !== false) return;
  const value = env.HAKIMI_DEBUG_PORT;
  if (typeof value !== "string" || !/^[0-9]{1,5}$/.test(value)) return;
  const port = Number(value);
  if (port < 1 || port > 65535) return;
  app.commandLine.appendSwitch("remote-debugging-address", "127.0.0.1");
  app.commandLine.appendSwitch("remote-debugging-port", String(port));
}

function stopOwnedBackend(child, startedByShell) {
  if (startedByShell !== true || !child || !Number.isInteger(child.pid) || child.pid <= 0
      || child.exitCode !== null || child.signalCode !== null || child.killed !== false) return false;
  // Use the ChildProcess handle, never a PID/port lookup or a command-line guess.
  return child.kill();
}

module.exports = { configureRemoteDebugging, externalUrl, installNavigationPolicy, isInternalUrl, stopOwnedBackend };
