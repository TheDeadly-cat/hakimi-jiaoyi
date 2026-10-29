const { app, BrowserWindow, Menu, Tray, dialog, shell, session } = require("electron");
const crypto = require("crypto");
const childProcess = require("child_process");
const fs = require("fs");
const http = require("http");
const net = require("net");
const path = require("path");
const { pathToFileURL } = require("url");
const { configureRemoteDebugging, installNavigationPolicy } = require("./desktop-security-policy");
const {
  classifyBackendHealthResponse,
  isLoopbackHost,
} = require("./backend-runtime-contract");

const { localResourceAllowed, quantPendingState, stopOwnedBackend } = require("./desktop-lifecycle");
const terminalPackage = require("./terminal-package-runtime");
const PACKAGE_CONTEXT = app.isPackaged ? terminalPackage.createContext({
  resourcesPath: process.resourcesPath,
  localAppData: process.env.LOCALAPPDATA,
  home: app.getPath("home"),
  runtimeDirectory: process.env.HAKIMI_RUNTIME_DIR,
  quantWorkspaceDirectory: process.env.HAKIMI_QUANT_WORKSPACE_DIR,
}) : null;

const APP_TITLE = PACKAGE_CONTEXT ? `哈基米交易 · ${PACKAGE_CONTEXT.manifest.version}` : "哈基米交易 · 开发预览";
const HOST = String(process.env.HAKIMI_HOST || "127.0.0.1").trim().toLowerCase();
const PORT = Number(process.env.HAKIMI_PORT || 8765);
if (!isLoopbackHost(HOST) || !Number.isInteger(PORT) || PORT < 1 || PORT > 65535) {
  throw new Error("哈基米交易需要有效的本机地址和端口");
}
const BASE_URL = `http://${HOST === "::1" ? "[::1]" : HOST}:${PORT}`;
const HEALTH_URL = `${BASE_URL}/api/health`;
const LOCAL_ONLY = ["1", "true", "yes", "on"].includes(String(process.env.HAKIMI_LOCAL_ONLY ?? (PACKAGE_CONTEXT ? "1" : "")).trim().toLowerCase());
const START_URL = PACKAGE_CONTEXT || process.env.HAKIMI_START_QUANT === "1" ? `${BASE_URL}/?workspace=quant` : BASE_URL;
const ROOT_DIR = path.resolve(__dirname, "..");
const PYTHON_ROOT = PACKAGE_CONTEXT?.pythonRoot || path.join(ROOT_DIR, "python_quant_bot");
const SOURCE_RUNTIME = PACKAGE_CONTEXT ? null : terminalPackage.dataDirectory(
  process.env.HAKIMI_RUNTIME_DIR || path.join(PYTHON_ROOT, "runtime"), __dirname);
const WORKSPACE_CONTEXT = PACKAGE_CONTEXT || {
  root: __dirname, legacyRuntime: SOURCE_RUNTIME,
  workspace: terminalPackage.prepareDataDirectory(process.env.HAKIMI_QUANT_WORKSPACE_DIR || path.join(PYTHON_ROOT, "runtime"), __dirname),
};
if (!PACKAGE_CONTEXT) WORKSPACE_CONTEXT.legacyRuntime = terminalPackage.dataDirectory(SOURCE_RUNTIME, __dirname);
const INSTANCE_ID = PACKAGE_CONTEXT?.instanceId || terminalPackage.instanceIdentity(__dirname, WORKSPACE_CONTEXT.workspace);
const SHELL_PROFILE = PACKAGE_CONTEXT?.userData || terminalPackage.prepareDataDirectory(
  path.join(app.getPath("appData"), "HakimiTradeTerminal", "developer-shells", INSTANCE_ID), __dirname);
app.setName("哈基米交易");
fs.mkdirSync(SHELL_PROFILE, { recursive: true });
app.setPath("userData", SHELL_PROFILE);
app.setPath("sessionData", SHELL_PROFILE);
const DIAGNOSTICS = terminalPackage.configureDiagnostics({
  app, programRoot: WORKSPACE_CONTEXT.root, profile: SHELL_PROFILE,
  environment: process.env, changeDirectory: directory => process.chdir(directory),
});
if (PACKAGE_CONTEXT) PACKAGE_CONTEXT.diagnosticsDirectory = DIAGNOSTICS.directory;
const SERVER_PATH = path.join(PYTHON_ROOT, "exchange_terminal", "server.py");
const FIND_PYTHON = path.join(PYTHON_ROOT, "find_python.ps1");
const ICON_PATH = path.join(PYTHON_ROOT, "assets", "hakimi_trade_v2.ico");
const FUTU_HOST = process.env.FUTU_HOST || "127.0.0.1";
const FUTU_PORT = Number(process.env.FUTU_PORT || 11111);
const FUTU_OPEND_EXE = process.env.FUTU_OPEND_EXE || path.join(
  process.env.USERPROFILE || "C:\\Users\\Administrator",
  "Documents",
  "Futu_OpenD_10.7.6728_Windows",
  "Futu_OpenD_10.7.6728_Windows",
  "Futu_OpenD_10.7.6728_Windows",
  "FutuOpenD.exe"
);
const SHELL_STATE_FILE = path.join(app.getPath("userData"), "desktop-shell-state.json");

let mainWindow = null;
let tray = null;
let backendProcess = null;
let backendStartup = null;
let backendStartedByShell = false;
let statusTimer = null;
let quitting = false;
let quitReady = false;
let lifecycleBusy = false;
let backendControlToken = null;
let backendShutdownAccepted = false;
let backendStopping = false;
let localNetworkGuardInstalled = false;

const singleInstanceLock = app.requestSingleInstanceLock({ instanceId: INSTANCE_ID });
if (!singleInstanceLock) {
  app.quit();
}

configureRemoteDebugging(app, process.env);

function request(url, timeoutMs = 1500) {
  return new Promise((resolve, reject) => {
    const req = http.get(url, { timeout: timeoutMs }, (res) => {
      let body = "";
      res.setEncoding("utf8");
      res.on("data", (chunk) => {
        body += chunk;
      });
      res.on("end", () => {
        resolve({ statusCode: res.statusCode, body });
      });
    });
    req.on("timeout", () => {
      req.destroy(new Error("timeout"));
    });
    req.on("error", reject);
  });
}

function waitForPort(host, port, timeoutMs = 10000) {
  const started = Date.now();
  return new Promise((resolve) => {
    const tick = () => {
      const socket = net.createConnection({ host, port, timeout: 700 });
      socket.once("connect", () => {
        socket.destroy();
        resolve(true);
      });
      socket.once("timeout", () => {
        socket.destroy();
      });
      socket.once("error", () => {});
      socket.once("close", () => {
        if (Date.now() - started > timeoutMs) {
          resolve(false);
          return;
        }
        setTimeout(tick, 250);
      });
    };
    tick();
  });
}

async function isPortOpen(host, port, timeoutMs = 700) {
  return new Promise((resolve) => {
    const socket = net.createConnection({ host, port, timeout: timeoutMs });
    let settled = false;
    const done = (value) => {
      if (settled) return;
      settled = true;
      socket.destroy();
      resolve(value);
    };
    socket.once("connect", () => done(true));
    socket.once("timeout", () => done(false));
    socket.once("error", () => done(false));
  });
}

async function readBackendHealth() {
  try {
    const response = await request(HEALTH_URL, 1200);
    const health = classifyBackendHealthResponse(response);
    if (health.healthy && health.payload?.local_only !== LOCAL_ONLY) {
      return { ...health, healthy: false, status: "MODE_MISMATCH", reason: "local_mode_mismatch" };
    }
    if (health.healthy && !terminalPackage.matchesBackend(WORKSPACE_CONTEXT, health.payload, LOCAL_ONLY)) {
      return { ...health, healthy: false, status: "PACKAGE_OR_WORKSPACE_MISMATCH", reason: "package_or_workspace_mismatch" };
    }
    return health;
  } catch {
    return { healthy: false, reachable: false, status: "OFFLINE", reason: "health_unavailable", payload: null };
  }
}

async function isBackendHealthy() {
  return (await readBackendHealth()).healthy;
}

function readShellState() {
  try {
    return JSON.parse(fs.readFileSync(SHELL_STATE_FILE, "utf8"));
  } catch {
    return {};
  }
}

function writeShellState(patch) {
  try {
    fs.mkdirSync(path.dirname(SHELL_STATE_FILE), { recursive: true });
    const next = { ...readShellState(), ...patch };
    fs.writeFileSync(SHELL_STATE_FILE, JSON.stringify(next, null, 2), "utf8");
  } catch {}
}

function startFutuOpenDIfNeeded() {
  if (LOCAL_ONLY) return { ok: false, status: "BLOCKED_LOCAL_MODE" };
  if (!fs.existsSync(FUTU_OPEND_EXE)) return false;
  isPortOpen(FUTU_HOST, FUTU_PORT, 500).then((online) => {
    if (online || quitting) return;
    try {
      childProcess.spawn(FUTU_OPEND_EXE, {
        cwd: path.dirname(FUTU_OPEND_EXE),
        detached: true,
        windowsHide: true,
        stdio: "ignore"
      }).unref();
    } catch (error) {
      console.error(`[futu-opend] ${error.message}`);
    }
  });
  return true;
}

function startBackend() {
  if (!fs.existsSync(SERVER_PATH)) {
    throw new Error(`找不到后端入口：${SERVER_PATH}`);
  }
  if (!PACKAGE_CONTEXT && !fs.existsSync(FIND_PYTHON)) {
    throw new Error(`找不到 Python 检测脚本：${FIND_PYTHON}`);
  }

  const command = [
    `$ErrorActionPreference='Stop'`,
    `. '${FIND_PYTHON.replace(/'/g, "''")}'`,
    `$py = Find-Python`,
    `if (-not $py) { throw 'Python not found' }`,
    `& $py.Exe @($py.Args) '${SERVER_PATH.replace(/'/g, "''")}' --host ${HOST} --port ${PORT} --no-browser`
  ].join("; ");

  backendControlToken = crypto.randomBytes(32).toString("hex");
  backendShutdownAccepted = false;
  backendStopping = false;
  const startup = terminalPackage.createStartupDiagnostic({
    directory: DIAGNOSTICS.directory, secrets: [backendControlToken], environment: process.env,
  });
  backendStartup = startup;
  const packagedLaunch = PACKAGE_CONTEXT ? terminalPackage.backendLaunch(PACKAGE_CONTEXT, {
    host: HOST, port: PORT, token: backendControlToken, localOnly: LOCAL_ONLY,
  }) : null;
  try {
    backendProcess = childProcess.spawn(
      packagedLaunch?.executable || "powershell.exe",
      packagedLaunch?.args || ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
      packagedLaunch?.options || {
        cwd: DIAGNOSTICS.directory,
        env: {
          ...process.env,
          HAKIMI_DESKTOP_CONTROL_TOKEN: backendControlToken,
          HAKIMI_RUNTIME_DIR: WORKSPACE_CONTEXT.legacyRuntime,
          HAKIMI_QUANT_WORKSPACE_DIR: WORKSPACE_CONTEXT.workspace,
          HAKIMI_RUNTIME_READ_ONLY: "1",
          HAKIMI_QUANT_READ_ONLY: process.env.HAKIMI_QUANT_READ_ONLY || "0",
          HAKIMI_LOAD_LOCAL_AI_ENV: process.env.HAKIMI_LOAD_LOCAL_AI_ENV || "1",
          HAKIMI_LOAD_LOCAL_AI_ENV_IN_READ_ONLY: process.env.HAKIMI_LOAD_LOCAL_AI_ENV_IN_READ_ONLY || "1",
        },
        windowsHide: true,
        stdio: ["ignore", "pipe", "pipe"]
      }
    );
  } catch {
    startup.finish("SPAWN_ERROR");
    throw new Error(`后台程序未能创建。诊断记录：${DIAGNOSTICS.directory}`);
  }
  backendStartedByShell = true;

  // Consume both pipes without copying arbitrary provider output into Chromium
  // logs. Only bounded, redacted stderr during startup is retained separately.
  backendProcess.stdout.on("data", () => {});
  backendProcess.stderr.on("data", chunk => startup.append(chunk));
  const child = backendProcess;
  child.once("error", () => {
    startup.finish("SPAWN_ERROR");
    if (backendProcess === child) { backendProcess = null; backendStartedByShell = false; }
    showBootMessage("后台未能启动", `诊断记录：${DIAGNOSTICS.directory}`);
  });
  child.once("close", code => startup.finish("EXITED", code));
  backendProcess.once("exit", (code) => {
    if (!quitting && !backendStopping && code !== 0) {
      showBootMessage("后台服务已退出", `Python 后台进程退出，代码 ${code ?? "unknown"}。`);
    }
  });
}

async function prepareBackendStop() {
  if (!backendStartedByShell || !backendProcess) {
    if (!await isPortOpen(HOST, PORT)) return { ok: true, status: "STOPPED" };
    const pending = quantPendingState(await readBackendHealth());
    return { ok: false, status: pending === "BUSY" ? "BUSY" : pending === "UNKNOWN" ? "UNKNOWN" : "NOT_OWNED" };
  }
  backendStopping = true;
  const result = await stopOwnedBackend({
    child: backendProcess,
    token: backendControlToken,
    origin: BASE_URL,
    accepted: backendShutdownAccepted,
  });
  backendShutdownAccepted = result.accepted;
  if (result.ok) {
    backendProcess = null;
    backendStartedByShell = false;
    backendControlToken = null;
  } else if (!result.accepted) {
    backendStopping = false;
  }
  return result;
}

function explainStopBlocked(result, action) {
  const messages = {
    BUSY: "量化操作仍在执行，请等待操作结束后再" + action + "。当前窗口和后台已保留。",
    WAITING: "后台已接受关闭请求，仍在保存和退出，请稍候再" + action + "。不会强制结束进程。",
    NOT_OWNED: "当前后台由另一个入口启动。请从原来的窗口正常退出后再重试，当前窗口不会强制关闭它。",
    UNKNOWN: "未能确认后台可以安全关闭。请查看任务与回测的操作记录，等待操作结束后再重试。当前后台已保留。",
  };
  showMainWindow();
  const options = { type: "info", title: APP_TITLE, message: "暂未" + action,
    detail: messages[result.status] || "后台状态仍需核对，当前进程已保留。", buttons: ["知道了"] };
  const pendingDialog = mainWindow && !mainWindow.isDestroyed()
    ? dialog.showMessageBox(mainWindow, options) : dialog.showMessageBox(options);
  pendingDialog.catch(() => {});
}

function configureLocalNetworkGuard() {
  if (!LOCAL_ONLY || localNetworkGuardInstalled) return;
  localNetworkGuardInstalled = true;
  session.defaultSession.webRequest.onBeforeRequest({ urls: ["<all_urls>"] }, (details, callback) => {
    callback({ cancel: !localResourceAllowed(details.url, BASE_URL) });
  });
}

function showMainWindow() {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.show();
  mainWindow.focus();
}

async function restartBackend() {
  if (lifecycleBusy || quitting) return;
  lifecycleBusy = true;
  try {
    const result = await prepareBackendStop();
    if (!result.ok) {
      explainStopBlocked(result, "重启");
      return;
    }
    if (await isPortOpen(HOST, PORT)) {
      explainStopBlocked({ status: "NOT_OWNED" }, "重启");
      return;
    }
    showBootMessage("正在重启后台", "重新启动 Python 行情与策略服务。");
    startBackend();
    await waitForPort(HOST, PORT, 18000);
    if (await isBackendHealthy()) {
      backendStartup?.finish("READY");
      await mainWindow?.loadURL(START_URL);
    } else {
      backendStartup?.finish("NOT_READY");
      showBootMessage("重启失败", `后台服务没有在预期时间内就绪。诊断记录：${DIAGNOSTICS.directory}`);
    }
  } finally {
    lifecycleBusy = false;
  }
}

function setAppMenu() {
  const template = [
    {
      label: "哈基米交易",
      submenu: [
        { label: "显示窗口", click: showMainWindow },
        { label: "刷新", accelerator: "CmdOrCtrl+R", click: () => mainWindow?.reload() },
        { label: "重启后台", click: restartBackend },
        { label: "回到交易台", click: () => mainWindow?.loadURL(BASE_URL) },
        { label: "在浏览器打开", click: () => shell.openExternal(BASE_URL) },
        { label: "打开诊断文件夹", click: () => shell.openPath(DIAGNOSTICS.directory) },
        { label: "关闭窗口后留在托盘（后台继续运行）", type: "checkbox",
          checked: readShellState().minimizeToTray === true, enabled: fs.existsSync(ICON_PATH),
          click: item => { writeShellState({ minimizeToTray: item.checked === true }); setAppMenu(); updateTrayMenu(); } },
        { type: "separator" },
        ...(!app.isPackaged ? [{ label: "开发者工具", accelerator: "F12", click: () => mainWindow?.webContents.openDevTools({ mode: "detach" }) }] : []),
        { type: "separator" },
        { label: "退出哈基米交易（关闭本程序后台）", role: "quit" }
      ]
    }
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

function createTray() {
  if (tray || !fs.existsSync(ICON_PATH)) return;
  tray = new Tray(ICON_PATH);
  tray.setToolTip(APP_TITLE);
  updateTrayMenu();
  tray.on("double-click", showMainWindow);
}

function updateTrayMenu() {
  if (!tray) return;
  const keepRunning = readShellState().minimizeToTray === true;
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: keepRunning ? "关闭窗口会留在托盘，后台继续运行" : "关闭窗口将退出哈基米交易", enabled: false },
    { label: "显示哈基米交易", click: showMainWindow },
    { label: "回到交易台", click: () => { showMainWindow(); mainWindow?.loadURL(BASE_URL); } },
    { label: "重启后台", click: restartBackend },
    { type: "separator" },
    { label: "退出哈基米交易（关闭本程序后台）", click: () => app.quit() }
  ]));
}

function createWindow() {
  const state = readShellState();
  const bounds = state.windowBounds || {};
  mainWindow = new BrowserWindow({
    title: APP_TITLE,
    width: Number(bounds.width || 1500),
    height: Number(bounds.height || 940),
    x: Number.isFinite(bounds.x) ? bounds.x : undefined,
    y: Number.isFinite(bounds.y) ? bounds.y : undefined,
    minWidth: 1180,
    minHeight: 760,
    backgroundColor: "#050707",
    icon: fs.existsSync(ICON_PATH) ? ICON_PATH : undefined,
    autoHideMenuBar: true,
    show: false,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      devTools: !app.isPackaged,
      webSecurity: true
    }
  });

  mainWindow.once("ready-to-show", () => {
    if (state.maximized) mainWindow.maximize();
    mainWindow.show();
  });

  mainWindow.on("page-title-updated", (event) => {
    event.preventDefault();
    mainWindow.setTitle(APP_TITLE);
  });

  installNavigationPolicy(mainWindow.webContents, {
    baseUrl: BASE_URL,
    bootUrl: pathToFileURL(path.join(__dirname, "boot.html")).href,
    openExternal: (url) => shell.openExternal(url),
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  mainWindow.on("close", (event) => {
    if (!quitting && process.platform === "win32") {
      writeShellState({
        windowBounds: mainWindow.getNormalBounds(),
        maximized: mainWindow.isMaximized()
      });
    }
    if (!quitting && readShellState().minimizeToTray === true && tray) {
      event.preventDefault();
      mainWindow.hide();
    } else if (!quitting) {
      event.preventDefault();
      app.quit();
    }
  });

  mainWindow.loadFile(path.join(__dirname, "boot.html"));
}

function showBootMessage(title, detail) {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  mainWindow.webContents.executeJavaScript(
    `window.setBootStatus && window.setBootStatus(${JSON.stringify(title)}, ${JSON.stringify(detail)});`
  ).catch(() => {});
}

async function pollRuntimeStatus() {
  if (quitting) return;
  const backendHealth = await readBackendHealth();
  const backend = backendHealth.healthy;
  const futu = LOCAL_ONLY ? false : await isPortOpen(FUTU_HOST, FUTU_PORT, 500);
  if (tray) {
    const backendLabel = backend ? "在线" : backendHealth.reachable ? "需要重启" : "离线";
    tray.setToolTip(`${APP_TITLE}\n后台：${backendLabel}\nFutuOpenD：${futu ? "在线" : "离线"}`);
  }
  if (!backend && mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send?.("hakimi-runtime-status", { backend, futu });
  }
}

function startStatusMonitor() {
  if (statusTimer) clearInterval(statusTimer);
  statusTimer = setInterval(pollRuntimeStatus, 30000);
  pollRuntimeStatus();
}

async function boot() {
  configureLocalNetworkGuard();
  createWindow();
  setAppMenu();
  createTray();
  showBootMessage("正在检查本机服务", HEALTH_URL);

  const initialHealth = await readBackendHealth();
  if (!initialHealth.healthy) {
    const portOccupied = initialHealth.reachable || await isPortOpen(HOST, PORT, 700);
    if (portOccupied) {
      showBootMessage("此工作区暂未打开", "本机端口已有其他程序版本、工作区或运行模式的服务。请先从原窗口退出，或为当前工作区选择另一个端口。已有后台保持运行。");
      dialog.showErrorBox(APP_TITLE, `端口 ${PORT} 正由既有服务使用，当前窗口没有连接或停止它。`);
      return;
    }
    showBootMessage("正在启动后台", "启动 Python 行情与策略服务。");
    startBackend();
  }

  const ready = await waitForPort(HOST, PORT, 18000);
  const healthy = ready && (await isBackendHealthy());
  if (!healthy) {
    backendStartup?.finish("NOT_READY");
    showBootMessage("启动失败", PACKAGE_CONTEXT ? "包内后台未能就绪，请检查程序文件与端口占用。" : "后台服务没有在预期时间内就绪。请确认 Python 环境可用。");
    dialog.showErrorBox(APP_TITLE, (PACKAGE_CONTEXT ? `包内后台没有启动成功。请检查程序文件和端口 ${PORT}。` : "后台服务没有启动成功。请先检查 Python 环境和端口 8765。") + `\n诊断记录：${DIAGNOSTICS.directory}`);
    return;
  }

  backendStartup?.finish("READY");
  showBootMessage("正在打开交易台", BASE_URL);
  await mainWindow.loadURL(START_URL);
  startStatusMonitor();
}

app.on("second-instance", () => {
  if (singleInstanceLock) showMainWindow();
});

app.whenReady().then(() => { if (singleInstanceLock) return boot(); });

app.on("before-quit", (event) => {
  if (!singleInstanceLock) return;
  if (quitReady) {
    quitting = true;
    if (statusTimer) clearInterval(statusTimer);
    return;
  }
  event.preventDefault();
  if (lifecycleBusy) return;
  lifecycleBusy = true;
  (async () => {
    // A shell that only attached to an existing service leaves that service
    // running. It has no process authority or private control token for it.
    const result = backendStartedByShell ? await prepareBackendStop() : { ok: true };
    if (!result.ok) {
      explainStopBlocked(result, "退出");
      return;
    }
    if (mainWindow && !mainWindow.isDestroyed()) {
      writeShellState({ windowBounds: mainWindow.getNormalBounds(), maximized: mainWindow.isMaximized() });
    }
    quitReady = true;
    quitting = true;
    app.quit();
  })().catch(() => {
    explainStopBlocked({ status: "UNKNOWN" }, "退出");
  }).finally(() => {
    lifecycleBusy = false;
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (singleInstanceLock && BrowserWindow.getAllWindows().length === 0) boot();
});
