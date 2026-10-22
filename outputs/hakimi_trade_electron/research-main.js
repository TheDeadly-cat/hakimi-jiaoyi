"use strict";

const path = require("node:path");
const { spawn } = require("node:child_process");
const { configureRemoteDebugging, installNavigationPolicy, stopOwnedBackend } = require("./desktop-security-policy");

function launchSpec({ workspace, python = "python", env = process.env }) {
  if (typeof workspace !== "string" || !workspace.trim() || typeof python !== "string" || !python.trim()) {
    throw new Error("请选择有效的工作区与 Python 程序。");
  }
  return { executable: python, args: ["-m", "hakimi_research.workbench_server", "--workspace", path.resolve(workspace), "--port", "0"],
    options: { shell: false, windowsHide: true, stdio: ["ignore", "pipe", "pipe"],
      env: { ...env, PYTHONUNBUFFERED: "1", PYTHONIOENCODING: "utf-8", HAKIMI_SKIP_LOCAL_AI_ENV: "1" } } };
}

function validateAnnouncement(value, childPid) {
  if (!value || value.engine !== "hakimi_research" || !Number.isInteger(value.port)
      || value.port < 1 || value.port > 65535 || !Number.isInteger(value.pid) || value.pid < 1
      || (value.pid !== childPid && value.parent_pid !== childPid) || !Number.isInteger(childPid) || childPid < 1) {
    throw new Error("工作台启动身份未通过核对。");
  }
  const url = new URL(value.url);
  if (url.href !== `http://127.0.0.1:${value.port}/` || url.username || url.password) {
    throw new Error("工作台必须使用本次本机服务地址。");
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
        const announcement = validateAnnouncement(JSON.parse(text.slice(0, end)), child.pid);
        finished = true; clearTimeout(timer); resolve(announcement);
      } catch { fail(new Error("工作台启动回执无效，未打开页面。")); }
    });
  });
  return { child, ready };
}

async function runDesktop(electron) {
  const { app, BrowserWindow, Menu, dialog, shell } = electron;
  app.setName("Hakimi Research Workbench");
  app.setPath("userData", path.join(app.getPath("appData"), "HakimiResearchWorkbench"));
  configureRemoteDebugging(app, process.env);
  if (!app.requestSingleInstanceLock()) { app.quit(); return; }
  let window = null, backend = null, quitting = false;
  app.on("second-instance", () => { if (window) { if (window.isMinimized()) window.restore(); window.show(); window.focus(); } });
  app.on("before-quit", () => { quitting = true; stopOwnedBackend(backend, true); });
  app.on("window-all-closed", () => app.quit());
  await app.whenReady();
  const workspace = path.resolve(process.env.HAKIMI_RESEARCH_WORKSPACE || path.join(app.getPath("home"), ".hakimi-trade-workbench"));
  try {
    const started = startServer(launchSpec({ workspace, python: process.env.HAKIMI_RESEARCH_PYTHON || "python" }));
    backend = started.child;
    const identity = await started.ready;
    if (quitting) return;
    window = new BrowserWindow({ title: "哈基米研究工作台", width: 1440, height: 960, minWidth: 1000, minHeight: 680,
      backgroundColor: "#f3f6fa", show: false, webPreferences: { contextIsolation: true, nodeIntegration: false,
        sandbox: true, webSecurity: true, devTools: !app.isPackaged } });
    installNavigationPolicy(window.webContents, { baseUrl: identity.url, bootUrl: "", openExternal: url => shell.openExternal(url) });
    window.webContents.session.setPermissionRequestHandler((_contents, _permission, callback) => callback(false));
    window.once("ready-to-show", () => window?.show());
    window.on("closed", () => { window = null; });
    backend.on("exit", () => { if (!quitting && window) dialog.showMessageBox(window, { type: "error", title: "研究服务已停止",
      message: "研究服务已停止，请重新打开工作台。", detail: "已保存的数据和结果仍在原工作区；不自动重做未确认的操作。" }); });
    Menu.setApplicationMenu(Menu.buildFromTemplate([{ label: "工作台", submenu: [
      { label: "刷新记录", accelerator: "CmdOrCtrl+R", click: () => window?.reload() },
      { label: "打开工作区文件夹", click: () => shell.openPath(workspace) },
      { type: "separator" }, { label: "退出", role: "quit" },
    ] }]));
    await window.loadURL(identity.url);
    if (!quitting && window && !window.isDestroyed()) window.show();
  } catch (error) {
    stopOwnedBackend(backend, true);
    await dialog.showMessageBox({ type: "error", title: "工作台未能启动", message: error.message,
      detail: "请按当前版本安装说明安装 hakimi-research，再重新打开。旧桌面入口与原有记录不会被修改。" });
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
module.exports = { launchSpec, validateAnnouncement, startServer, runDesktop, isResearchEntry };
