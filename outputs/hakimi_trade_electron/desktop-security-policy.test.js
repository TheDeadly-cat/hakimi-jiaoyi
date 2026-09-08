"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { configureRemoteDebugging, externalUrl, installNavigationPolicy, isInternalUrl, stopOwnedBackend } = require("./desktop-security-policy");

const baseUrl = "http://127.0.0.1:8765";
const bootUrl = "file:///C:/hakimi/boot.html";
assert.equal(externalUrl("https://example.org/research?q=btc#source"), "https://example.org/research?q=btc#source");
for (const value of [undefined, "", "invalid", "http://example.org", "file:///C:/data.txt",
  "custom:sample", "https://user:pass@example.org/", "https://example.org/\n",
  "https://example.org/%0a", "https:\\example.org", " https://example.org"]) {
  assert.equal(externalUrl(value), null);
}
assert.equal(isInternalUrl(`${baseUrl}/api/health`, baseUrl, bootUrl), true);
assert.equal(isInternalUrl(bootUrl, baseUrl, bootUrl), true);
for (const value of ["https://127.0.0.1:8765/", "http://127.0.0.1:8766/", "file:///C:/other.html",
  "http://name@127.0.0.1:8765/", "http://127.0.0.1.example.org:8765/"]) {
  assert.equal(isInternalUrl(value, baseUrl, bootUrl), false);
}

// Call the same installed handlers as Electron, without opening a browser or socket.
const handlers = {};
const opened = [];
const loaded = [];
const contents = {
  on: (name, callback) => { handlers[name] = callback; },
  setWindowOpenHandler: (callback) => { handlers.popup = callback; },
  loadURL: (url) => { loaded.push(url); },
};
installNavigationPolicy(contents, { baseUrl, bootUrl, openExternal: (url) => { opened.push(url); } });
assert.deepEqual(handlers.popup({ url: `${baseUrl}/report` }), { action: "deny" });
assert.deepEqual(loaded, [`${baseUrl}/report`]);
for (const eventName of ["will-navigate", "will-redirect"]) {
  let prevented = false;
  handlers[eventName]({ preventDefault: () => { prevented = true; } }, `${baseUrl}/api/health`);
  assert.equal(prevented, false);
  handlers[eventName]({ preventDefault: () => { prevented = true; } }, "https://example.org/research");
  assert.equal(prevented, true);
  assert.equal(opened.at(-1), "https://example.org/research");
  const count = opened.length;
  for (const value of ["file:///C:/other.html", "custom:sample", "https://name@example.org/", "invalid"]) {
    handlers[eventName]({ preventDefault: () => {} }, value);
    handlers.popup({ url: value });
    assert.equal(opened.length, count);
  }
}

for (const isPackaged of [true, undefined, false]) {
  for (const port of ["9333", "0", "65536", "9333x", "", undefined]) {
    const switches = new Map([["remote-debugging-port", "1234"], ["remote-allow-origins", "*"]]);
    configureRemoteDebugging({ isPackaged, commandLine: {
      removeSwitch: (name) => switches.delete(name),
      appendSwitch: (name, value) => switches.set(name, value),
    } }, { HAKIMI_DEBUG_PORT: port });
    assert.equal(switches.has("remote-allow-origins"), false);
    if (isPackaged === false && port === "9333") {
      assert.equal(switches.get("remote-debugging-port"), "9333");
      assert.equal(switches.get("remote-debugging-address"), "127.0.0.1");
    } else assert.equal(switches.size, 0);
  }
}
const main = fs.readFileSync(path.join(__dirname, "main.js"), "utf8");
assert.match(main, /installNavigationPolicy\(mainWindow\.webContents/);
assert.match(main, /configureRemoteDebugging\(app, process\.env\)/);
assert.match(main, /env: \{ \.\.\.process\.env, HAKIMI_RUNTIME_READ_ONLY: "1" \}/);
assert.equal((main.match(/startFutuOpenDIfNeeded\(/g) || []).length, 1); // Historical function only; no caller.
assert.match(main, /Legacy Preview/);
let stopped = 0;
const owned = { pid: 123, exitCode: null, signalCode: null, killed: false, kill: () => { stopped += 1; return true; } };
assert.equal(stopOwnedBackend(owned, false), false);
for (const override of [{ exitCode: 0 }, { signalCode: "SIGTERM" }, { killed: true }, { pid: 0 }]) {
  assert.equal(stopOwnedBackend({ ...owned, ...override }, true), false);
}
assert.equal(stopped, 0);
assert.equal(stopOwnedBackend(owned, true), true);
assert.equal(stopped, 1);
assert.doesNotMatch(main, /taskkill|Stop-Process|stopVerifiedBackendListener|buildVerifiedBackendStopScript/);
console.log("desktop security policy tests passed");
