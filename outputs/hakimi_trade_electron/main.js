const { app, BrowserWindow, Menu, Tray, dialog, shell } = require("electron");
const childProcess = require("child_process");
const fs = require("fs");
const http = require("http");
const net = require("net");
const path = require("path");
const { pathToFileURL } = require("url");
const { configureRemoteDebugging, installNavigationPolicy, stopOwnedBackend } = require("./desktop-security-policy");
const {
  classifyBackendHealthResponse,
  isLoopbackHost,
} = require("./backend-runtime-contract");

const APP_TITLE = "哈基米研究 · Legacy Preview";
const HOST = String(process.env.HAKIMI_HOST || "127.0.0.1").trim().toLowerCase();
const PORT = Number(process.env.HAKIMI_PORT || 8765);
if (!isLoopbackHost(HOST) || !Number.isInteger(PORT) || PORT < 1 || PORT > 65535) {
  throw new Error("Legacy preview requires a valid loopback host and port");
}
const BASE_URL = `http://${HOST === "::1" ? "[::1]" : HOST}:${PORT}`;
const HEALTH_URL = `${BASE_URL}/api/health`;
const ROOT_DIR = path.resolve(__dirname, "..");
const PYTHON_ROOT = path.join(ROOT_DIR, "python_quant_bot");
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
let backendStartedByShell = false;
let statusTimer = null;
let quitting = false;

const singleInstanceLock = app.requestSingleInstanceLock();
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
    return classifyBackendHealthResponse(response);
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
  if (!fs.existsSync(FIND_PYTHON)) {
    throw new Error(`找不到 Python 检测脚本：${FIND_PYTHON}`);
  }

  const command = [
    `$ErrorActionPreference='Stop'`,
    `. '${FIND_PYTHON.replace(/'/g, "''")}'`,
    `$py = Find-Python`,
    `if (-not $py) { throw 'Python not found' }`,
    `& $py.Exe @($py.Args) '${SERVER_PATH.replace(/'/g, "''")}' --host ${HOST} --port ${PORT} --no-browser`
  ].join("; ");

  backendProcess = childProcess.spawn(
    "powershell.exe",
    ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
    {
      cwd: PYTHON_ROOT,
      env: { ...process.env, HAKIMI_RUNTIME_READ_ONLY: "1" },
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"]
    }
  );
  backendStartedByShell = true;

  backendProcess.stdout.on("data", (chunk) => {
    console.log(`[hakimi-backend] ${chunk.toString().trim()}`);
  });
  backendProcess.stderr.on("data", (chunk) => {
    console.error(`[hakimi-backend] ${chunk.toString().trim()}`);
  });
  backendProcess.once("exit", (code) => {
    if (!quitting && code !== 0) {
      showBootMessage("后台服务已退出", `Python 后台进程退出，代码 ${code ?? "unknown"}。`);
    }
  });
}

function stopBackend() {
  try {
    return stopOwnedBackend(backendProcess, backendStartedByShell);
  } catch { return false; }
}

function showMainWindow() {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.show();
  mainWindow.focus();
}

async function restartBackend() {
  dialog.showMessageBox(mainWindow, { type: "info", title: APP_TITLE,
    message: "请在启动后台的终端中手动重启。",
    detail: "Legacy Preview 不依据端口、进程名称或相对路径结束既有服务。" });
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
        { type: "separator" },
        ...(!app.isPackaged ? [{ label: "开发者工具", accelerator: "F12", click: () => mainWindow?.webContents.openDevTools({ mode: "detach" }) }] : []),
        { type: "separator" },
        { label: "退出", role: "quit" }
      ]
    }
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

function createTray() {
  if (tray || !fs.existsSync(ICON_PATH)) return;
  tray = new Tray(ICON_PATH);
  tray.setToolTip(APP_TITLE);
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: "显示哈基米交易", click: showMainWindow },
    { label: "回到交易台", click: () => { showMainWindow(); mainWindow?.loadURL(BASE_URL); } },
    { label: "重启后台", click: restartBackend },
    { type: "separator" },
    { label: "退出", click: () => app.quit() }
  ]));
  tray.on("double-click", showMainWindow);
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
    if (!quitting && state.minimizeToTray !== false && tray) {
      event.preventDefault();
      mainWindow.hide();
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
  const futu = await isPortOpen(FUTU_HOST, FUTU_PORT, 500);
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
  createWindow();
  setAppMenu();
  createTray();
  showBootMessage("正在检查本机服务", HEALTH_URL);

  const initialHealth = await readBackendHealth();
  if (!initialHealth.healthy) {
    const portOccupied = initialHealth.reachable || await isPortOpen(HOST, PORT, 700);
    if (portOccupied) {
      showBootMessage("后台不可复用", "端口已有未通过只读合同的服务，请手动处理；未结束任何进程。");
      dialog.showErrorBox(APP_TITLE, `端口 ${PORT} 已被既有服务占用；未执行自动终止。`);
      return;
    }
    showBootMessage("正在启动后台", "启动 Python 行情与策略服务。");
    startBackend();
  }

  const ready = await waitForPort(HOST, PORT, 18000);
  const healthy = ready && (await isBackendHealthy());
  if (!healthy) {
    showBootMessage("启动失败", "后台服务没有在预期时间内就绪。请确认 Python 环境可用。");
    dialog.showErrorBox(APP_TITLE, "后台服务没有启动成功。请先检查 Python 环境和端口 8765。");
    return;
  }

  showBootMessage("正在打开交易台", BASE_URL);
  await mainWindow.loadURL(BASE_URL);
  startStatusMonitor();
}

app.on("second-instance", () => {
  showMainWindow();
});

app.whenReady().then(boot);

app.on("before-quit", () => {
  quitting = true;
  if (statusTimer) clearInterval(statusTimer);
  if (mainWindow && !mainWindow.isDestroyed()) {
    writeShellState({
      windowBounds: mainWindow.getNormalBounds(),
      maximized: mainWindow.isMaximized()
    });
  }
  stopBackend();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) boot();
});
