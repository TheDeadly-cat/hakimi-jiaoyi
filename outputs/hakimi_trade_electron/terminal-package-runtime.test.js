"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const runtime = require("./terminal-package-runtime");

function fixture(t) {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), "hakimi-terminal-中文 空格-"));
  t.after(() => fs.rmSync(base, { recursive: true, force: true }));
  const root = path.join(base, "安装 程序");
  const files = {};
  for (const name of ["runtime/python/python.exe", "resources/app/terminal-bootstrap.py", "HakimiTrade.exe"]) {
    const target = path.join(root, name);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, "synthetic non-executed " + name);
    files[name] = runtime.hash(fs.readFileSync(target));
  }
  const core = { schema_version: "hakimi-original-terminal-v1", platform: "win32-x64", version: "0.7.0.dev1",
    python: "runtime/python/python.exe", bootstrap: "resources/app/terminal-bootstrap.py", desktop_entry: "HakimiTrade.exe",
    backend_entry: "exchange_terminal.server", primary_route: "/?workspace=quant", quant_route: "/quant/",
    source_provenance: { git: { commit: "a".repeat(40) } }, files };
  const manifest = { ...core, bundle_id: runtime.hash(runtime.canonical(core)) };
  fs.writeFileSync(path.join(root, "terminal-manifest.json"), JSON.stringify(manifest));
  const diagnosticsDirectory = path.join(base, "诊断 记录");
  fs.mkdirSync(diagnosticsDirectory);
  return { base, root, manifest, context: { root, manifest, workspace: path.join(base, "工作 区"), diagnosticsDirectory } };
}
test("verified original route uses only private Python with separate Unicode arguments", t => {
  const { root, context, manifest } = fixture(t);
  assert.equal(runtime.verifyBundle(root).bundle_id, manifest.bundle_id);
  const launch = runtime.backendLaunch(context, { host: "127.0.0.1", port: 18765, token: "token", localOnly: true,
    environment: { PYTHONPATH: "evil", PythonHome: "evil", PYTHONSTARTUP: "evil", NODE_OPTIONS: "evil", SAFE: "kept" } });
  assert.equal(launch.executable, path.join(root, "runtime/python/python.exe"));
  assert.deepEqual(launch.args.slice(0, 5), ["-I", "-S", "-B", "-X", "utf8"]);
  assert.equal(launch.options.shell, false);
  assert.equal(launch.options.cwd, context.diagnosticsDirectory);
  assert.equal(launch.options.env.SAFE, "kept");
  assert.equal(Object.keys(launch.options.env).some(key => key.toUpperCase().startsWith("PYTHON")), false);
  assert.equal(launch.options.env.HAKIMI_TERMINAL_PACKAGE_ID, manifest.bundle_id);
  assert.equal(launch.options.env.HAKIMI_RUNTIME_DIR, context.workspace);
  assert.equal(launch.options.env.HAKIMI_QUANT_WORKSPACE_DIR, context.workspace);
});
test("changed executable bytes and unexpected modules fail before launch", t => {
  const { root } = fixture(t);
  fs.writeFileSync(path.join(root, "injected.py"), "raise RuntimeError('unsafe')");
  assert.throws(() => runtime.verifyBundle(root), /inventory_changed/);
  fs.unlinkSync(path.join(root, "injected.py"));
  fs.writeFileSync(path.join(root, "debug.log"), "early crashpad diagnostic");
  assert.throws(() => runtime.verifyBundle(root), /inventory_changed/);
  fs.unlinkSync(path.join(root, "debug.log"));
  fs.appendFileSync(path.join(root, "runtime/python/python.exe"), "changed");
  assert.throws(() => runtime.verifyBundle(root), /hash_changed/);
});
test("missing resource and manifest identity tampering fail closed", t => {
  const { root } = fixture(t);
  fs.unlinkSync(path.join(root, "resources/app/terminal-bootstrap.py"));
  assert.throws(() => runtime.verifyBundle(root), /inventory_changed/);
});
test("existing backend requires exact package, mode and physical workspace", t => {
  const { context } = fixture(t);
  fs.mkdirSync(context.workspace);
  const health = { terminal_package_id: context.manifest.bundle_id, terminal_workspace_root: context.workspace, local_only: true };
  assert.equal(runtime.matchesBackend(context, health, true), true);
  assert.equal(runtime.matchesBackend(context, { ...health, terminal_package_id: "different" }, true), false);
  assert.equal(runtime.matchesBackend(context, { ...health, terminal_workspace_root: path.dirname(context.workspace) }, true), false);
  assert.equal(runtime.matchesBackend(context, health, false), false);
});
test("workspace is separate from immutable program and stable across versions", t => {
  const { base, root } = fixture(t);
  const args = { resourcesPath: path.join(root, "resources"), localAppData: base, home: base };
  assert.equal(runtime.createContext(args).workspace, path.join(base, "HakimiTradeTerminal/workspaces/default/runtime"));
  assert.throws(() => runtime.createContext({ ...args, runtimeDirectory: path.join(root, "user-data") }), /inside_program/);
});
test("directory junction and escaping relative resources are rejected", t => {
  const { base, root } = fixture(t);
  const alias = path.join(base, "alias");
  fs.symlinkSync(root, alias, process.platform === "win32" ? "junction" : "dir");
  assert.throws(() => runtime.verifyBundle(alias), /reparse/);
  assert.throws(() => runtime.boundPath(root, "../outside.py"), /relative_path/);
});

test("quant workspace stays distinct from the legacy read root and singleton key uses installation plus workspace", t => {
  const { base, root } = fixture(t);
  const args = { resourcesPath: path.join(root, "resources"), localAppData: base, home: base,
    runtimeDirectory: path.join(base, "旧数据"), quantWorkspaceDirectory: path.join(base, "新量化 空间") };
  const context = runtime.createContext(args);
  context.diagnosticsDirectory = path.join(base, "诊断 记录");
  const again = runtime.createContext({ ...args, quantWorkspaceDirectory: path.join(base, "ignored", "..", "新量化 空间") });
  const other = runtime.createContext({ ...args, quantWorkspaceDirectory: path.join(base, "另一个工作区") });
  assert.equal(context.instanceId, again.instanceId);
  assert.equal(context.userData, again.userData);
  assert.notEqual(context.instanceId, other.instanceId);
  const launch = runtime.backendLaunch(context, { host: "127.0.0.1", port: 18765, token: "test", localOnly: true, environment: {} });
  assert.equal(launch.options.env.HAKIMI_RUNTIME_DIR, args.runtimeDirectory);
  assert.equal(launch.options.env.HAKIMI_QUANT_WORKSPACE_DIR, args.quantWorkspaceDirectory);
  const anotherInstall = path.join(base, "另一个安装");
  fs.mkdirSync(anotherInstall);
  assert.notEqual(context.instanceId, runtime.instanceIdentity(anotherInstall, context.workspace));
  const health = { terminal_package_id: context.manifest.bundle_id, local_only: true, terminal_workspace_root: context.workspace };
  assert.equal(runtime.matchesBackend(context, health, true), true);
  assert.equal(runtime.matchesBackend(other, health, true), false);
  assert.equal(runtime.matchesBackend(context, { ...health, terminal_workspace_root: context.legacyRuntime }, true), false);
});

test("data directories reject relative paths, package storage and junction aliases including missing children", t => {
  const { base, root } = fixture(t);
  const args = { resourcesPath: path.join(root, "resources"), localAppData: base, home: base };
  const target = path.join(base, "真实数据");
  fs.mkdirSync(target);
  const alias = path.join(base, "别名");
  fs.symlinkSync(target, alias, process.platform === "win32" ? "junction" : "dir");
  for (const option of ["runtimeDirectory", "quantWorkspaceDirectory"]) {
    assert.throws(() => runtime.createContext({ ...args, [option]: "relative-data" }), /absolute_directory/);
    assert.throws(() => runtime.createContext({ ...args, [option]: path.join(root, "data") }), /inside_program/);
    assert.throws(() => runtime.createContext({ ...args, [option]: alias }), /reparse/);
    assert.throws(() => runtime.createContext({ ...args, [option]: path.join(alias, "new-data") }), /reparse/);
  }
});

test("installed Electron health contract loads its package capability resource with no source tree", t => {
  const { root } = fixture(t);
  const destination = path.join(root, "components/canonical/hakimi_research/contracts/product-capabilities.json");
  fs.mkdirSync(path.dirname(destination), { recursive: true });
  const current = require("./backend-runtime-contract");
  fs.copyFileSync(current.PRODUCT_CAPABILITY_DEFINITION_PATH, destination);
  const module = path.join(root, "resources/app/backend-runtime-contract.js");
  fs.copyFileSync(path.join(__dirname, "backend-runtime-contract.js"), module);
  const { spawnSync } = require("node:child_process");
  const script = "const m=require(process.argv[1]);console.log(JSON.stringify({path:m.PRODUCT_CAPABILITY_DEFINITION_PATH,count:Object.keys(m.EXPECTED_PRODUCT_CAPABILITIES).length}));";
  const actual = spawnSync(process.execPath, ["-e", script, module], { cwd: os.tmpdir(), encoding: "utf8" });
  assert.equal(actual.status, 0, actual.stderr);
  assert.equal(JSON.parse(actual.stdout).path, destination);
  assert.equal(fs.existsSync(path.join(root, "src")), false);
  fs.unlinkSync(destination);
  const missing = spawnSync(process.execPath, ["-e", script, module], { cwd: os.tmpdir(), encoding: "utf8" });
  assert.notEqual(missing.status, 0);
  assert.match(missing.stderr, /product_capability_definition_unreadable/);
});

test("actual packaged main resolves boot, icon, contract and private backend without a source checkout", async t => {
  const { base, root, manifest } = fixture(t);
  const appDirectory = path.join(root, "resources/app");
  const resources = ["main.js", "boot.html", "desktop-security-policy.js", "backend-runtime-contract.js",
    "desktop-lifecycle.js", "terminal-package-runtime.js"];
  const extra = {
    "components/canonical/hakimi_research/contracts/product-capabilities.json": fs.readFileSync(require("./backend-runtime-contract").PRODUCT_CAPABILITY_DEFINITION_PATH),
    "components/terminal/exchange_terminal/server.py": Buffer.from("# fixture is never executed\n"),
    "components/terminal/assets/hakimi_trade_v2.ico": Buffer.from("non-executed fixture icon"),
  };
  for (const name of resources) extra["resources/app/" + name] = fs.readFileSync(path.join(__dirname, name));
  for (const [name, bytes] of Object.entries(extra)) {
    fs.mkdirSync(path.dirname(path.join(root, name)), { recursive: true });
    fs.writeFileSync(path.join(root, name), bytes);
    manifest.files[name] = runtime.hash(bytes);
  }
  const { bundle_id: _oldId, ...core } = manifest;
  manifest.bundle_id = runtime.hash(runtime.canonical(core));
  fs.writeFileSync(path.join(root, "terminal-manifest.json"), JSON.stringify(manifest));
  const { EventEmitter } = require("node:events");
  const { createRequire } = require("node:module");
  const vm = require("node:vm");
  const observed = { paths: {}, spawns: [], switches: {}, events: [] };
  const app = { isPackaged: true, getPath: key => observed.paths[key] || base,
    setPath: (key, value) => { observed.paths[key] = value; }, setName: value => { observed.name = value; },
    setAppLogsPath: value => { observed.logs = value; observed.events.push("logs"); },
    requestSingleInstanceLock: () => { observed.events.push("singleton"); return true; },
    commandLine: { appendSwitch(key, value) { observed.switches[key] = value; }, removeSwitch() {} },
    on() {}, whenReady: () => ({ then() {} }), quit() {} };
  class Window extends EventEmitter {
    constructor() {
      super(); observed.events.push("window");
      assert.equal(vm.runInContext("process.env.CHROME_CRASHPAD_PIPE_NAME", context), undefined);
      this.webContents = { on() {}, setWindowOpenHandler() {}, executeJavaScript: async () => {} };
    }
    isDestroyed() { return false; }
    loadFile(file) { assert.equal(fs.existsSync(file), true); observed.bootFile = file; }
    loadURL(url) { observed.loadedURL = url; }
  }
  class Tray extends EventEmitter {
    constructor(icon) { super(); assert.equal(fs.existsSync(icon), true); observed.icon = icon; }
    setToolTip() {} setContextMenu() {}
  }
  const fromPackage = createRequire(path.join(appDirectory, "main.js"));
  const child = new EventEmitter(); child.stdout = new EventEmitter(); child.stderr = new EventEmitter();
  const context = vm.createContext({ __dirname: appDirectory, console, URL, setTimeout, clearTimeout, setInterval, clearInterval,
    process: { platform: "win32", resourcesPath: path.join(root, "resources"), env: { LOCALAPPDATA: base, HAKIMI_LOCAL_ONLY: "1",
      CHROME_CRASHPAD_PIPE_NAME: "unowned-launcher-pipe", CHROME_CRASHPAD_SERVER_URL: "https://unowned.invalid" },
      chdir(directory) { observed.cwd = directory; observed.events.push("cwd"); } },
    require(name) {
      if (name === "electron") return { app, BrowserWindow: Window, Tray,
        Menu: { buildFromTemplate: value => value, setApplicationMenu() {} },
        session: { defaultSession: { webRequest: { onBeforeRequest() {} } } }, dialog: {}, shell: {} };
      if (name === "child_process") return { spawn(executable, args, options) {
        observed.events.push("backend"); observed.spawns.push({ executable, args, options });
        queueMicrotask(() => child.stderr.emit("data", "Synthetic startup trace\n")); return child;
      } };
      return fromPackage(name);
    },
  });
  vm.runInContext(fs.readFileSync(path.join(appDirectory, "main.js"), "utf8"), context);
  vm.runInContext("let calls=0; readBackendHealth=async()=>({healthy:++calls>1,reachable:false}); isPortOpen=async()=>false; waitForPort=async()=>true; startStatusMonitor=()=>{};", context);
  await vm.runInContext("boot()", context);
  assert.equal(observed.name, "哈基米交易");
  assert.equal(observed.loadedURL, "http://127.0.0.1:8765/?workspace=quant");
  assert.equal(observed.bootFile, path.join(appDirectory, "boot.html"));
  assert.equal(observed.spawns.length, 1);
  assert.equal(observed.spawns[0].executable, path.join(root, "runtime/python/python.exe"));
  assert.equal(observed.spawns[0].options.shell, false);
  assert.equal(observed.spawns[0].options.cwd, observed.logs);
  assert.equal(observed.cwd, observed.logs);
  assert.deepEqual(observed.events, ["logs", "cwd", "singleton", "window", "backend"]);
  assert.equal(observed.switches["log-file"], path.join(observed.logs, "electron.log"));
  assert.equal(observed.switches["enable-logging"], "file");
  assert.equal(vm.runInContext("process.env.ELECTRON_LOG_FILE", context), observed.switches["log-file"]);
  const diagnostic = fs.readdirSync(observed.logs).find(name => name.startsWith("backend-startup-"));
  const recorded = JSON.parse(fs.readFileSync(path.join(observed.logs, diagnostic), "utf8"));
  assert.equal(recorded.status, "READY");
  assert.match(recorded.stderr, /Synthetic startup trace/);
  // Relative application diagnostics use the safe cwd; Windows Crashpad's
  // pre-init EXE-directory fallback is prevented by removing its foreign pipe.
  fs.writeFileSync(path.join(observed.cwd, "debug.log"), "early child diagnostic");
  assert.equal(runtime.verifyBundle(root).bundle_id, manifest.bundle_id);
  assert.equal(observed.spawns[0].options.env.CHROME_CRASHPAD_PIPE_NAME, undefined);
  assert.equal(observed.spawns[0].options.env.CHROME_CRASHPAD_SERVER_URL, undefined);
  assert.equal(observed.spawns[0].options.env.HAKIMI_QUANT_WORKSPACE_DIR, vm.runInContext("WORKSPACE_CONTEXT.workspace", context));
  assert.equal(fs.existsSync(path.join(root, "src")), false);
});

test("diagnostic configuration overrides inherited log destinations without writing program files", t => {
  const { root, base } = fixture(t);
  const environment = { ELECTRON_LOG_FILE: path.join(root, "debug.log"), ELECTRON_ENABLE_LOGGING: "1",
    CHROME_CRASHPAD_PIPE_NAME: "unowned-launcher-pipe", chrome_crashpad_server_url: "https://unowned.invalid" };
  const switches = {}, observed = {};
  const app = { commandLine: { appendSwitch: (key, value) => { switches[key] = value; } },
    setAppLogsPath: directory => { observed.logs = directory; } };
  const diagnostics = runtime.configureDiagnostics({ app, programRoot: root, profile: path.join(base, "壳 配置"),
    environment, changeDirectory: directory => { observed.cwd = directory; } });
  assert.equal(environment.ELECTRON_LOG_FILE, diagnostics.chromiumLog);
  assert.equal(environment.ELECTRON_ENABLE_LOGGING, "file");
  assert.equal(environment.CHROME_CRASHPAD_PIPE_NAME, undefined);
  assert.equal(environment.chrome_crashpad_server_url, undefined);
  assert.equal(switches["log-file"], diagnostics.chromiumLog);
  assert.equal(observed.cwd, diagnostics.directory);
  assert.equal(observed.logs, diagnostics.directory);
  assert.throws(() => runtime.configureDiagnostics({ app, programRoot: root, profile: root, environment,
    changeDirectory() { assert.fail("cannot enter program"); } }), /inside_program/);
  const alias = path.join(base, "诊断别名");
  fs.symlinkSync(diagnostics.directory, alias, process.platform === "win32" ? "junction" : "dir");
  assert.throws(() => runtime.configureDiagnostics({ app, programRoot: root, profile: alias, environment,
    changeDirectory() { assert.fail("cannot enter alias"); } }), /reparse/);
  assert.doesNotThrow(() => runtime.verifyBundle(root));
});

test("startup stderr is bounded, redacted across chunks and frozen at completion", t => {
  const { context } = fixture(t);
  const token = "private-control-" + "a".repeat(48), apiKey = "private-api-key-value";
  const recorder = runtime.createStartupDiagnostic({ directory: context.diagnosticsDirectory, secrets: [token],
    environment: { API_KEY: apiKey, NORMAL: "must-not-be-dumped" } });
  recorder.append("Traceback (most recent call last):\nterminal_file_inventory_changed\n" + token.slice(0, 10));
  recorder.append(token.slice(10) + "\nAuthorization: Bearer provider-secret\nAPI_KEY=" + apiKey + "\n");
  recorder.append("Authorization: Basic encoded-auth-value\npassword='multiple secret words'\n");
  recorder.append("x".repeat(70000) + "secret-cut-in-final-line");
  recorder.finish("EXITED", 1);
  const before = fs.readFileSync(recorder.file, "utf8");
  const record = JSON.parse(before);
  assert.match(record.stderr, /terminal_file_inventory_changed/);
  for (const secret of [token, apiKey, "provider-secret", "encoded-auth-value", "multiple secret words", "must-not-be-dumped", "secret-cut"]) assert.equal(before.includes(secret), false);
  assert.equal(record.truncated, true);
  assert.ok(record.stderr.length <= 8192);
  assert.equal(record.exit_code, 1);
  recorder.append("late provider error"); recorder.finish("READY");
  assert.equal(fs.readFileSync(recorder.file, "utf8"), before);
});

test("absent Crashpad pipe stays absent and mixed-case foreign endpoints never reach Python", t => {
  const { context, root, base } = fixture(t);
  const environment = { SAFE: "preserved" };
  const app = { commandLine: { appendSwitch() {} }, setAppLogsPath() {} };
  runtime.configureDiagnostics({ app, programRoot: root, profile: path.join(base, "no-pipe"), environment, changeDirectory() {} });
  assert.equal(Object.keys(environment).some(key => key.toUpperCase().startsWith("CHROME_CRASHPAD")), false);
  const launch = runtime.backendLaunch(context, { host: "127.0.0.1", port: 18765, token: "test", localOnly: true,
    environment: { ...environment, chrome_crashpad_pipe_name: "foreign", Chrome_Crashpad_Server_Url: "https://foreign.invalid" } });
  assert.equal(Object.keys(launch.options.env).some(key => key.toUpperCase().startsWith("CHROME_CRASHPAD")), false);
  assert.equal(launch.options.env.SAFE, "preserved");
});

test("a startup diagnostic write failure preserves existing bytes and cannot interrupt lifecycle", t => {
  const { context } = fixture(t);
  const recorder = runtime.createStartupDiagnostic({ directory: context.diagnosticsDirectory });
  fs.writeFileSync(recorder.file, "preserved-existing-record");
  recorder.append("Traceback\n");
  assert.equal(recorder.finish("SPAWN_ERROR"), null);
  assert.equal(fs.readFileSync(recorder.file, "utf8"), "preserved-existing-record");
});
