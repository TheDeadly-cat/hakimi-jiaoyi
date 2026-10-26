"use strict";

const path = require("node:path");
const fs = require("node:fs");
const crypto = require("node:crypto");
const { spawn } = require("node:child_process");
const { configureRemoteDebugging, installNavigationPolicy, stopOwnedBackend } = require("./desktop-security-policy");

function desktopSettings(appData, env = process.env) {
  const profile = env.HAKIMI_RESEARCH_DESKTOP_PROFILE;
  if (profile !== undefined && !/^[a-f0-9]{64}$/.test(profile)) {
    throw new Error("候选桌面身份无效，请使用已核对的启动入口。");
  }
  return { userData: profile ? path.join(appData, "HakimiResearchWorkbench", "candidates", profile)
    : path.join(appData, "HakimiResearchWorkbench"),
    title: env.HAKIMI_RESEARCH_TRIAL === "1" ? "哈基米量化工作台（试用版）"
      : profile ? "哈基米研究工作台（日常候选）" : "哈基米研究工作台" };
}

function expectedIdentity(env = process.env) {
  if (!env.HAKIMI_RESEARCH_EXPECTED_IDENTITY) {
    if (env.HAKIMI_RESEARCH_DESKTOP_PROFILE) throw new Error("候选入口缺少程序身份，请重新生成入口。");
    return null;
  }
  let value;
  try { value = JSON.parse(env.HAKIMI_RESEARCH_EXPECTED_IDENTITY); } catch { throw new Error("候选程序身份格式不正确。"); }
  if (!value || !/^[a-f0-9]{64}$/.test(value.loaded_source_sha256)
      || ![value.package_location, value.python_executable].every(v => typeof v === "string" && (path.isAbsolute(v) || path.win32.isAbsolute(v)))) {
    throw new Error("候选程序身份不完整。");
  }
  return value;
}

function identityPath(value) {
  return process.platform === "win32" || /^[a-z]:[\\/]|^\\\\/i.test(value)
    ? path.win32.normalize(value).toLowerCase() : path.resolve(value);
}

function launchSpec({ workspace, python = "python", env = process.env, identity = null }) {
  if (typeof workspace !== "string" || !workspace.trim() || typeof python !== "string" || !python.trim()) {
    throw new Error("请选择有效的工作区与 Python 程序。");
  }
  const clean = { ...env };
  for (const key of ["PYTHONPATH", "PYTHONHOME", "NODE_OPTIONS", "ELECTRON_RUN_AS_NODE"]) delete clean[key];
  return { executable: python, args: ["-I", "-B", "-u", "-X", "utf8", "-m", "hakimi_research.workbench_server", "--workspace", path.resolve(workspace), "--port", "0"], identity,
    options: { shell: false, windowsHide: true, stdio: ["ignore", "pipe", "pipe"],
      env: { ...clean, HAKIMI_SKIP_LOCAL_AI_ENV: "1" } } };
}

function validateAnnouncement(value, childPid, expected = null) {
  if (!value || value.engine !== "hakimi_research" || !Number.isInteger(value.port)
      || value.port < 1 || value.port > 65535 || !Number.isInteger(value.pid) || value.pid < 1
      || (value.pid !== childPid && value.parent_pid !== childPid) || !Number.isInteger(childPid) || childPid < 1) {
    throw new Error("工作台启动身份未通过核对。");
  }
  const url = new URL(value.url);
  if (url.href !== `http://127.0.0.1:${value.port}/` || url.username || url.password) {
    throw new Error("工作台必须使用本次本机服务地址。");
  }
  if (expected && (typeof value.package_location !== "string" || typeof value.python_executable !== "string"
      || identityPath(value.package_location) !== identityPath(expected.package_location)
      || identityPath(value.python_executable) !== identityPath(expected.python_executable)
      || value.loaded_source_sha256 !== expected.loaded_source_sha256)) {
    throw new Error("实际运行程序与已核验的安装不一致，未打开工作台。");
  }
  return { url: url.href, port: value.port, pid: value.pid, engine: value.engine };
}

function startServer(spec, { spawnProcess = spawn, timeoutMs = 20000 } = {}) {
  const child = spawnProcess(spec.executable, spec.args, spec.options);
  const ready = new Promise((resolve, reject) => {
    let finished = false, text = "", stderr = "";
    const fail = (error) => {
      if (finished) return;
      finished = true; clearTimeout(timer); stopOwnedBackend(child, true); reject(error);
    };
    const timer = setTimeout(() => fail(new Error("工作台启动超时，请检查已安装的正式 Python 包。")), timeoutMs);
    child.stdout.setEncoding("utf8"); child.stderr.setEncoding("utf8");
    child.stderr.on("data", value => { stderr = (stderr + value).slice(-2000); });
    child.on("error", () => fail(new Error("无法启动 Python。请安装当前研究包，或设置 HAKIMI_RESEARCH_PYTHON。")));
    child.on("exit", () => fail(new Error("工作台未完成启动。请核对当前研究包安装。" + (stderr.includes("No module named") ? " 找不到正式工作台模块。" : ""))));
    child.stdout.on("data", chunk => {
      if (finished) return;
      text += chunk;
      if (Buffer.byteLength(text, "utf8") > 16384) { fail(new Error("工作台启动回执过长。")); return; }
      const end = text.indexOf("\n"); if (end < 0) return;
      try {
        const announcement = validateAnnouncement(JSON.parse(text.slice(0, end)), child.pid, spec.identity);
        finished = true; clearTimeout(timer); resolve(announcement);
      } catch { fail(new Error("工作台启动回执无效，未打开页面。")); }
    });
  });
  return { child, ready };
}

function writeDiagnostic(directory, details) {
  fs.mkdirSync(directory, { recursive: true });
  const record = { schema_version: "workbench-desktop-diagnostic-v1", recorded_at: new Date().toISOString(), ...details };
  const text = JSON.stringify(record, null, 2) + "\n";
  const filename = path.join(directory, `diagnostic-${Date.now()}-${crypto.randomUUID()}.json`);
  fs.writeFileSync(filename, text, { flag: "wx", encoding: "utf8" });
  return { filename, text };
}

async function runDesktop(electron) {
  const { app, BrowserWindow, Menu, dialog, shell, clipboard } = electron;
  const desktop = desktopSettings(app.getPath("appData"));
  app.setName("Hakimi Research Workbench");
  app.setPath("userData", desktop.userData);
  configureRemoteDebugging(app, process.env);
  if (!app.requestSingleInstanceLock()) { app.quit(); return; }
  let window = null, backend = null, quitting = false;
  app.on("second-instance", () => { if (window) { if (window.isMinimized()) window.restore(); window.show(); window.focus(); } });
  app.on("before-quit", () => { quitting = true; stopOwnedBackend(backend, true); });
  app.on("window-all-closed", () => app.quit());
  await app.whenReady();
  const workspace = path.resolve(process.env.HAKIMI_RESEARCH_WORKSPACE || path.join(app.getPath("home"), ".hakimi-trade-workbench"));
  const diagnose = (state, error = null) => writeDiagnostic(path.join(app.getPath("userData"), "diagnostics"), {
    state, error, workspace, version: app.getVersion(), electron_version: process.versions.electron,
    expected_identity: (() => { try { return expectedIdentity(); } catch { return { status: "INVALID" }; } })(),
    new_economic_calculations: 0,
  });
  try {
    const started = startServer(launchSpec({ workspace, python: process.env.HAKIMI_RESEARCH_PYTHON || "python", identity: expectedIdentity() }));
    backend = started.child;
    const identity = await started.ready;
    if (quitting) return;
    window = new BrowserWindow({ title: desktop.title, width: 1440, height: 960, minWidth: 1000, minHeight: 680,
      backgroundColor: "#f3f6fa", show: false, webPreferences: { contextIsolation: true, nodeIntegration: false,
        sandbox: true, webSecurity: true, devTools: !app.isPackaged } });
    installNavigationPolicy(window.webContents, { baseUrl: identity.url, bootUrl: "", openExternal: url => shell.openExternal(url) });
    window.webContents.session.setPermissionRequestHandler((_contents, _permission, callback) => callback(false));
    // The page title describes its contents; the native title identifies the
    // isolated candidate entry even after navigation or reload.
    window.on("page-title-updated", event => { event.preventDefault(); });
    window.once("ready-to-show", () => window?.show());
    window.on("closed", () => { window = null; });
    backend.on("exit", () => { if (!quitting && window) dialog.showMessageBox(window, { type: "error", title: "研究服务已停止",
      message: "研究服务已停止，请重新打开工作台。", detail: "已保存的数据和结果仍在原工作区；不自动重做未确认的操作。" }); });
    Menu.setApplicationMenu(Menu.buildFromTemplate([{ label: "工作台", submenu: [
      { label: "刷新记录", accelerator: "CmdOrCtrl+R", click: () => window?.reload() },
      { label: "打开工作区文件夹", click: () => shell.openPath(workspace) },
      { label: "复制诊断信息", click: () => { const saved = diagnose("USER_REQUESTED"); clipboard.writeText(saved.text); } },
      { label: "打开诊断文件夹", click: () => { const saved = diagnose("USER_REQUESTED"); shell.showItemInFolder(saved.filename); } },
      { type: "separator" }, { label: "退出", role: "quit" },
    ] }]));
    await window.loadURL(identity.url);
    if (!quitting && window && !window.isDestroyed()) window.show();
  } catch (error) {
    stopOwnedBackend(backend, true);
    let saved = null;
    try { saved = diagnose("STARTUP_FAILED", error.message); } catch { /* Keep the original startup failure visible. */ }
    const choice = await dialog.showMessageBox({ type: "error", title: "工作台未能启动", message: error.message,
      detail: "已有数据和结果保持不变。请重新打开已核验的入口；仍有问题时复制诊断信息。" + (saved ? `\n诊断文件：${saved.filename}` : ""),
      buttons: saved ? ["复制诊断信息", "关闭"] : ["关闭"], defaultId: saved ? 1 : 0, cancelId: saved ? 1 : 0 });
    if (saved && choice.response === 0) clipboard.writeText(saved.text);
    app.quit();
  }
}

function isResearchEntry(runtime = process, filename = __filename, nodeMain = require.main === module) {
  if (nodeMain) return true;
  // Electron 31 loads its explicit application entry without setting require.main.
  // Match the entry path as well as the main-process identity so an import stays inert.
  if (!runtime.versions?.electron || runtime.type !== "browser" || !runtime.argv?.[1]) return false;
  const normalize = value => runtime.platform === "win32" ? path.resolve(value).toLowerCase() : path.resolve(value);
  return normalize(runtime.argv[1]) === normalize(filename);
}

if (isResearchEntry()) runDesktop(require("electron"));
module.exports = { desktopSettings, expectedIdentity, identityPath, writeDiagnostic, launchSpec, validateAnnouncement, startServer, runDesktop, isResearchEntry };
