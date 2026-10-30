"use strict";

const assert = require("node:assert/strict");
const { EventEmitter } = require("node:events");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");
const { localResourceAllowed, quantPendingState, requestPrepareExit, stopOwnedBackend,
  waitForChildExit } = require("./desktop-lifecycle");

function runningChild() {
  const child = new EventEmitter();
  child.exitCode = null;
  child.signalCode = null;
  child.kill = () => assert.fail("A controlled shutdown must not kill the process");
  return child;
}

test("pending operations reject shutdown without waiting or killing", async () => {
  const result = await stopOwnedBackend({ child: runningChild(), token: "test", origin: "http://127.0.0.1:8765",
    request: async () => ({ statusCode: 409, body: '{}' }), wait: () => assert.fail("must not wait after busy") });
  assert.deepEqual(result, { ok: false, status: "BUSY", accepted: false });
});

test("request failures and unrecognized responses cannot authorize exit", async () => {
  for (const request of [async () => { throw new Error("timeout"); },
    async () => ({ statusCode: 200, body: "invalid" }),
    async () => ({ statusCode: 403, body: '{"ok":true,"status":"closing"}' }),
    async () => ({ statusCode: 200, body: '{"ok":true}' })]) {
    const result = await stopOwnedBackend({ child: runningChild(), token: "test", request,
      wait: () => assert.fail("unconfirmed shutdown must not wait/kill") });
    assert.equal(result.status, "UNKNOWN");
    assert.equal(result.ok, false);
  }
});

test("confirmed shutdown waits for the owned child before allowing exit", async () => {
  const child = runningChild();
  const result = await stopOwnedBackend({ child, token: "test",
    request: async () => ({ statusCode: 200, body: '{"ok":true,"status":"closing"}' }),
    wait: async (actual) => { assert.equal(actual, child); return true; } });
  assert.deepEqual(result, { ok: true, status: "STOPPED", accepted: true });
});

test("accepted but still-running shutdown stays pending and can be observed again", async () => {
  const child = runningChild();
  const result = await stopOwnedBackend({ child, accepted: true,
    request: () => assert.fail("accepted shutdown must not be resubmitted"), wait: async () => false });
  assert.deepEqual(result, { ok: false, status: "WAITING", accepted: true });
  child.exitCode = 0;
  const done = await stopOwnedBackend({ child, accepted: true,
    request: () => assert.fail("exited child needs no request") });
  assert.equal(done.ok, true);
});

test("unowned processes are never stopped", async () => {
  const result = await stopOwnedBackend({ child: null, request: () => assert.fail("no ownership") });
  assert.equal(result.status, "NOT_OWNED");
});

test("actual child exit and timeout clean up the exit observer", async () => {
  const child = runningChild();
  const exit = waitForChildExit(child, 500);
  child.exitCode = 0; child.emit("exit", 0);
  assert.equal(await exit, true);
  assert.equal(child.listenerCount("exit"), 0);
  const waiting = runningChild();
  assert.equal(await waitForChildExit(waiting, 5), false);
  assert.equal(waiting.listenerCount("exit"), 0);
});

test("pending health must be explicit and local-only resources stay on the exact origin", () => {
  assert.equal(quantPendingState({payload:{quant_workspace:{pending:true}}}), "BUSY");
  assert.equal(quantPendingState({payload:{quant_workspace:{pending:false}}}), "IDLE");
  assert.equal(quantPendingState({payload:{}}), "UNKNOWN");
  const base = "http://127.0.0.1:8765";
  for (const url of [base + "/quant/", "ws://127.0.0.1:8765/events", "file:///C:/local/boot.html", "data:image/png;base64,AA==", "blob:" + base + "/a"])
    assert.equal(localResourceAllowed(url, base), true, url);
  for (const url of ["https://example.com/", "wss://example.com/events", "http://127.0.0.1:11111/", "http://localhost:8765/", "https://127.0.0.1:8765/", "http://x@127.0.0.1:8765/", "blob:https://example.com/a", "file://remote/share/boot.html", "file:////remote/share/boot.html", "javascript:alert(1)"])
    assert.equal(localResourceAllowed(url, base), false, url);
});

test("prepare-exit sends the exact authenticated local request contract", async () => {
  for (const origin of ["http://127.0.0.1:8765", "http://localhost:8765", "http://[::1]:8765"]) {
    const transport = { request(url, options, callback) {
      assert.equal(url.origin, origin);
      assert.equal(url.pathname, "/api/desktop/prepare-exit");
      assert.equal(options.method, "POST");
      assert.equal(options.headers["X-Hakimi-Desktop-Control"], "test-token-only");
      assert.equal(options.headers["Content-Length"], "2");
      assert.equal(options.headers.Origin, origin);
      const request = new EventEmitter();
      request.end = body => {
        assert.equal(body, "{}");
        queueMicrotask(() => {
          const response = new EventEmitter(); response.statusCode = 200; response.setEncoding = () => {};
          callback(response); response.emit("data", '{"ok":true,"status":"closing"}'); response.emit("end");
        });
      };
      return request;
    }};
    const result = await requestPrepareExit(origin, "test-token-only", 5000, transport);
    assert.equal(result.statusCode, 200);
  }
});

test("invalid control destinations never dispatch a shutdown request", async () => {
  const transport = { request() { assert.fail("no request to an invalid destination"); } };
  for (const origin of ["https://127.0.0.1:8765", "http://example.com", "http://user@127.0.0.1:8765", "http://127.0.0.1.example.com"]) {
    await assert.rejects(requestPrepareExit(origin, "test", 10, transport), /destination_invalid/);
  }
  await assert.rejects(requestPrepareExit("http://127.0.0.1:8765", "", 10, transport), /destination_invalid/);
});

function desktopHarness(stopResult, { locked = true, state = {}, environment = {} } = {}) {
  const handlers = new Map();
  const observed = { prevented: 0, allowedQuit: 0, notices: 0, spawn: null, stop: null, filter: null,
    shown: 0, focused: 0, hidden: 0, paths: {}, shellState: { ...state } };
  const app = {
    getPath: name => observed.paths[name] || path.join(require("node:os").tmpdir(), "test-only-hakimi"),
    setName: name => { observed.appName = name; },
    setPath: (name, value) => { observed.paths[name] = value; },
    requestSingleInstanceLock: data => { observed.lockData = data; return locked; },
    commandLine: { appendSwitch() {}, removeSwitch() {} },
    whenReady: () => ({ then(callback) { observed.ready = callback; } }),
    on: (name, callback) => handlers.set(name, callback),
    quit() {
      let prevented = false;
      handlers.get("before-quit")?.({ preventDefault() { prevented = true; observed.prevented++; } });
      if (!prevented) observed.allowedQuit++;
    },
  };
  const child = runningChild();
  child.stdout = new EventEmitter(); child.stderr = new EventEmitter();
  class MockWindow extends EventEmitter {
    constructor() {
      super(); observed.window = this;
      this.webContents = { on() {}, setWindowOpenHandler() {}, loadURL() {}, executeJavaScript: async () => {} };
    }
    getNormalBounds() { return { width: 1500, height: 940 }; }
    isMaximized() { return false; }
    isDestroyed() { return false; }
    isMinimized() { return false; }
    loadFile() {}
    loadURL(url) { observed.loadedURL = url; }
    show() { observed.shown++; }
    focus() { observed.focused++; }
    hide() { observed.hidden++; }
  }
  class MockTray extends EventEmitter {
    setToolTip() {}
    setContextMenu(menu) { observed.trayMenu = menu; }
  }
  const lifecycle = require("./desktop-lifecycle");
  const context = vm.createContext({
    __dirname,
    console,
    URL,
    process: { env: { HAKIMI_LOCAL_ONLY: "1", HAKIMI_START_QUANT: "1", ...environment }, platform: "win32" },
    setTimeout, clearTimeout, setInterval, clearInterval,
    require(name) {
      if (name === "electron") return { app, BrowserWindow: MockWindow, Tray: MockTray,
        Menu: { buildFromTemplate: value => value, setApplicationMenu: value => { observed.menu = value; } },
        dialog: { showMessageBox: async () => { observed.notices++; }, showErrorBox: () => { observed.errors = (observed.errors || 0) + 1; } },
        session: { defaultSession: { webRequest: { onBeforeRequest: (_filter, callback) => { observed.filter = callback; } } } },
      };
      if (name === "fs") return { existsSync: () => true, mkdirSync() {},
        readFileSync: () => JSON.stringify(observed.shellState),
        writeFileSync: (_file, raw) => { observed.shellState = JSON.parse(raw); } };
      if (name === "child_process") return {
        spawn(executable, args, options) { observed.spawn = { executable, args, options }; return child; },
        spawnSync() { assert.fail("Desktop shutdown must never force-stop a process"); },
      };
      if (name === "./desktop-lifecycle") return { ...lifecycle,
        stopOwnedBackend: async (options) => { observed.stop = options; return stopResult; },
      };
      if (name === "./terminal-package-runtime") return { ...require(name),
        prepareDataDirectory: (value, root) => require(name).dataDirectory(value, root),
        configureDiagnostics: ({ profile }) => ({ directory: path.join(profile, "diagnostics") }),
        createStartupDiagnostic: () => ({
          append(value) { observed.startupStderr = (observed.startupStderr || "") + value; },
          finish(status) { observed.startupStatus = status; },
        }),
      };
      return require(name);
    },
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, "main.js"), "utf8"), context);
  return { app, child, context, observed, handlers };
}

test("backend reuse requires explicit matching local-only mode and preserves stricter health failures", async t => {
  const source = fs.readFileSync(path.join(__dirname, "main.js"), "utf8");
  const start = source.indexOf("async function readBackendHealth()");
  const end = source.indexOf("async function isBackendHealthy()", start);
  const temporary = fs.realpathSync.native(fs.mkdtempSync(path.join(require("node:os").tmpdir(), "hakimi-health-binding-")));
  t.after(() => fs.rmSync(temporary, { recursive: true, force: true }));
  const terminalPackage = require("./terminal-package-runtime");
  const sharedRoot = path.join(temporary, "broker-shared-v1");
  const workspaceContext = { workspace: path.join(temporary, "workspace"), brokerSharedRoot: sharedRoot,
    brokerSharedRootId: terminalPackage.brokerSharedRootIdentity(sharedRoot) };
  for (const [localOnly, payloadMode, expected] of [[true, true, true], [false, false, true],
    [true, false, false], [false, true, false], [false, undefined, false], [true, undefined, false]]) {
    const context = vm.createContext({ WORKSPACE_CONTEXT: workspaceContext,
      terminalPackage, LOCAL_ONLY: localOnly, HEALTH_URL: "http://127.0.0.1:8765/api/health",
      request: async () => ({}), classifyBackendHealthResponse: () => ({ healthy: true, reachable: true,
        status: "PASS", payload: { local_only: payloadMode, terminal_workspace_root: workspaceContext.workspace,
          broker_shared_root_id: workspaceContext.brokerSharedRootId } }) });
    vm.runInContext(source.slice(start, end), context);
    const result = await context.readBackendHealth();
    assert.equal(result.healthy, expected);
    if (!expected) { assert.equal(result.status, "MODE_MISMATCH"); assert.equal(result.reachable, true); }
  }
  const context = vm.createContext({ WORKSPACE_CONTEXT: workspaceContext,
    terminalPackage, LOCAL_ONLY: true, HEALTH_URL: "http://127.0.0.1:8765/api/health",
    request: async () => ({}), classifyBackendHealthResponse: () => ({ healthy: false, reachable: true,
      status: "RESTART_REQUIRED", payload: { local_only: true } }) });
  vm.runInContext(source.slice(start, end), context);
  assert.equal((await context.readBackendHealth()).status, "RESTART_REQUIRED");
  assert.equal(fs.existsSync(sharedRoot), false);
});

test("same workspace backend without the fixed shared root identity cannot attach", async t => {
  const source = fs.readFileSync(path.join(__dirname, "main.js"), "utf8");
  const start = source.indexOf("async function readBackendHealth()");
  const end = source.indexOf("async function isBackendHealthy()", start);
  const temporary = fs.realpathSync.native(fs.mkdtempSync(path.join(require("node:os").tmpdir(), "hakimi-health-root-mismatch-")));
  t.after(() => fs.rmSync(temporary, { recursive: true, force: true }));
  const terminalPackage = require("./terminal-package-runtime");
  const root = path.join(temporary, "host-root");
  const workspaceContext = { workspace: path.join(temporary, "workspace"), brokerSharedRoot: root,
    brokerSharedRootId: terminalPackage.brokerSharedRootIdentity(root) };
  const otherRootId = terminalPackage.brokerSharedRootIdentity(path.join(temporary, "other-host-root"));
  for (const identity of [undefined, null, otherRootId]) {
    const payload = { local_only: true, terminal_workspace_root: workspaceContext.workspace };
    if (identity !== undefined) payload.broker_shared_root_id = identity;
    const context = vm.createContext({ WORKSPACE_CONTEXT: workspaceContext, terminalPackage, LOCAL_ONLY: true,
      HEALTH_URL: "http://127.0.0.1:8765/api/health", request: async () => ({}),
      classifyBackendHealthResponse: () => ({ healthy: true, reachable: true, status: "PASS", payload }) });
    vm.runInContext(source.slice(start, end), context);
    const result = await context.readBackendHealth();
    assert.equal(result.healthy, false);
    assert.equal(result.reachable, true);
    assert.equal(result.status, "PACKAGE_OR_WORKSPACE_MISMATCH");
  }
  assert.deepEqual(fs.readdirSync(temporary), []);
});

test("actual desktop quit handler preserves owned processes on busy and unknown outcomes", async () => {
  for (const status of ["BUSY", "UNKNOWN", "WAITING"]) {
    const h = desktopHarness({ ok: false, status, accepted: status === "WAITING" });
    vm.runInContext("startBackend()", h.context);
    h.app.quit();
    await new Promise(setImmediate);
    assert.equal(h.observed.allowedQuit, 0);
    assert.equal(h.observed.prevented, 1);
    assert.equal(h.observed.notices, 1);
    assert.equal(h.observed.stop.child, h.child);
    const token = h.observed.spawn.options.env.HAKIMI_DESKTOP_CONTROL_TOKEN;
    assert.match(token, /^[0-9a-f]{64}$/);
    assert.equal(h.observed.stop.token, token);
    assert.equal(h.observed.spawn.args.join(" ").includes(token), false);
    assert.equal(h.observed.spawn.options.env.HAKIMI_RUNTIME_READ_ONLY, "1");
    assert.equal(h.observed.spawn.options.env.HAKIMI_QUANT_READ_ONLY, "0");
    assert.equal(h.observed.spawn.options.env.HAKIMI_LOAD_LOCAL_AI_ENV, "1");
    assert.equal(h.observed.spawn.options.env.HAKIMI_LOAD_LOCAL_AI_ENV_IN_READ_ONLY, "1");
  }
});

test("window close remains cancellable while an owned backend is busy", async () => {
  const h = desktopHarness({ ok: false, status: "BUSY", accepted: false });
  vm.runInContext("createWindow(); startBackend()", h.context);
  let closePrevented = false;
  h.observed.window.emit("close", { preventDefault() { closePrevented = true; } });
  await new Promise(setImmediate);
  assert.equal(closePrevented, true);
  assert.equal(h.observed.allowedQuit, 0);
  assert.equal(vm.runInContext("mainWindow !== null", h.context), true);
});

test("quitting an attached window does not stop a backend it does not own", async () => {
  const h = desktopHarness({ ok: false, status: "NOT_OWNED" });
  h.app.quit();
  await new Promise(setImmediate);
  assert.equal(h.observed.allowedQuit, 1);
  assert.equal(h.observed.stop, null);
  assert.equal(h.observed.spawn, null);
});

test("actual desktop quit handler allows exit only after confirmed owned shutdown", async () => {
  const h = desktopHarness({ ok: true, status: "STOPPED", accepted: true });
  vm.runInContext("startBackend()", h.context);
  h.app.quit();
  await new Promise(setImmediate);
  assert.equal(h.observed.prevented, 1);
  assert.equal(h.observed.allowedQuit, 1);
  assert.equal(h.observed.notices, 0);
});

test("desktop local session guard covers websocket requests and quant startup route", async () => {
  const h = desktopHarness({ ok: true });
  vm.runInContext("configureLocalNetworkGuard()", h.context);
  assert.equal(vm.runInContext("START_URL", h.context), "http://127.0.0.1:8765/?workspace=quant");
  h.observed.filter({ url: "wss://example.com/feed" }, ({cancel}) => assert.equal(cancel, true));
  h.observed.filter({ url: "http://127.0.0.1:8765/quant/" }, ({cancel}) => assert.equal(cancel, false));
  const blocked = await vm.runInContext("startFutuOpenDIfNeeded()", h.context);
  assert.equal(blocked.ok, false);
  assert.equal(blocked.status, "BLOCKED_LOCAL_MODE");
  assert.equal(h.observed.spawn, null);
});

test("close exits by default even with a tray and keeps owned shutdown cooperative", async () => {
  const h = desktopHarness({ ok: true, status: "STOPPED", accepted: true });
  vm.runInContext("createWindow(); createTray(); startBackend()", h.context);
  h.observed.window.emit("close", { preventDefault() {} });
  await new Promise(setImmediate);
  assert.equal(h.observed.hidden, 0);
  assert.equal(h.observed.allowedQuit, 1);
  assert.equal(h.observed.stop.child, h.child);
  assert.equal(h.observed.trayMenu[0].label, "关闭窗口将退出哈基米交易");
  assert.equal(h.observed.appName, "哈基米交易");
});

test("tray retention requires explicit opt-in and menu exit still stops owned backend", async () => {
  const h = desktopHarness({ ok: true, status: "STOPPED", accepted: true }, { state: { minimizeToTray: true } });
  vm.runInContext("createWindow(); createTray(); setAppMenu(); startBackend()", h.context);
  h.observed.window.emit("close", { preventDefault() {} });
  assert.equal(h.observed.hidden, 1);
  assert.equal(h.observed.allowedQuit, 0);
  assert.equal(h.observed.stop, null);
  assert.match(h.observed.trayMenu[0].label, /后台继续运行/);
  h.observed.trayMenu.at(-1).click();
  await new Promise(setImmediate);
  assert.equal(h.observed.allowedQuit, 1);
  assert.equal(h.observed.stop.child, h.child);
});

test("repeat launch focuses existing window and a losing instance never boots", async () => {
  const owner = desktopHarness({ ok: true });
  vm.runInContext("createWindow()", owner.context);
  owner.handlers.get("second-instance")();
  assert.equal(owner.observed.focused, 1);
  assert.equal(owner.observed.shown, 1);
  const duplicate = desktopHarness({ ok: true }, { locked: false });
  assert.equal(duplicate.observed.paths.userData, owner.observed.paths.userData);
  assert.equal(duplicate.observed.lockData.instanceId, owner.observed.lockData.instanceId);
  await duplicate.observed.ready();
  assert.equal(duplicate.observed.allowedQuit, 1);
  assert.equal(duplicate.observed.window, undefined);
  assert.equal(duplicate.observed.spawn, null);
});

test("different quant workspace gets a distinct singleton and launch keeps legacy source separate", () => {
  const temporary = require("node:fs").realpathSync.native(require("node:os").tmpdir());
  const old = path.join(temporary,"legacy-runtime-test");
  const first = desktopHarness({ ok: true }, { environment: { HAKIMI_RUNTIME_DIR: old, HAKIMI_QUANT_WORKSPACE_DIR: path.join(temporary,"quant-a-test") } });
  const second = desktopHarness({ ok: true }, { environment: { HAKIMI_RUNTIME_DIR: old, HAKIMI_QUANT_WORKSPACE_DIR: path.join(temporary,"quant-b-test") } });
  assert.notEqual(first.observed.paths.userData, second.observed.paths.userData);
  assert.notEqual(first.observed.lockData.instanceId, second.observed.lockData.instanceId);
  vm.runInContext("startBackend()", second.context);
  assert.equal(second.observed.spawn.options.env.HAKIMI_RUNTIME_DIR, old);
  assert.equal(second.observed.spawn.options.env.HAKIMI_QUANT_WORKSPACE_DIR, path.join(temporary,"quant-b-test"));
});

test("occupied service for a different workspace never attaches, spawns or receives stop", async () => {
  const h = desktopHarness({ ok: true });
  // Exercise the actual boot control flow with a service that is reachable but
  // did not pass the package/workspace match; no socket or process is started.
  vm.runInContext("readBackendHealth = async () => ({healthy:false,reachable:true,status:'PACKAGE_OR_WORKSPACE_MISMATCH'});", h.context);
  await vm.runInContext("boot()", h.context);
  assert.equal(h.observed.errors, 1);
  assert.equal(h.observed.loadedURL, undefined);
  assert.equal(h.observed.spawn, null);
  assert.equal(h.observed.stop, null);
  h.app.quit();
  await new Promise(setImmediate);
  assert.equal(h.observed.allowedQuit, 1);
  assert.equal(h.observed.stop, null);
});

test("backend spawn error records a bounded-diagnostic status and leaves no process authority", async () => {
  const h = desktopHarness({ ok: true });
  vm.runInContext("startBackend()", h.context);
  h.child.stderr.emit("data", "Synthetic startup failure\n");
  h.child.emit("error", new Error("private spawn arguments must not be recorded"));
  assert.equal(h.observed.startupStatus, "SPAWN_ERROR");
  assert.equal(h.observed.startupStderr, "Synthetic startup failure\n");
  assert.equal(vm.runInContext("backendStartedByShell", h.context), false);
  assert.equal(vm.runInContext("backendProcess", h.context), null);
  h.app.quit();
  await new Promise(setImmediate);
  assert.equal(h.observed.stop, null);
  assert.equal(h.observed.allowedQuit, 1);
});

test("developer legacy-only selection preserves the independent developer quant default", () => {
  const old = path.join(require("node:fs").realpathSync.native(require("node:os").tmpdir()), "legacy-read-only-selection");
  const h = desktopHarness({ ok: true }, { environment: { HAKIMI_RUNTIME_DIR: old } });
  vm.runInContext("startBackend()", h.context);
  assert.equal(h.observed.spawn.options.env.HAKIMI_RUNTIME_DIR, old);
  assert.notEqual(h.observed.spawn.options.env.HAKIMI_QUANT_WORKSPACE_DIR, old);
  assert.equal(h.observed.spawn.options.env.HAKIMI_QUANT_WORKSPACE_DIR,
    require("./terminal-package-runtime").dataDirectory(path.resolve(__dirname, "../python_quant_bot/runtime"), __dirname));
});
