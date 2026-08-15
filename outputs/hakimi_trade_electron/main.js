const { app, BrowserWindow, Menu, Tray, dialog, shell } = require("electron");
const childProcess = require("child_process");
const fs = require("fs");
const http = require("http");
const net = require("net");
const path = require("path");
const {
  buildVerifiedBackendStopScript,
  classifyBackendHealthResponse,
  isLoopbackHost,
} = require("./backend-runtime-contract");

const APP_TITLE = "哈基米交易 v2";
const HOST = process.env.HAKIMI_HOST || "127.0.0.1";
const PORT = Number(process.env.HAKIMI_PORT || 8765);
const BASE_URL = `http://${HOST}:${PORT}`;
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

if (process.env.HAKIMI_DEBUG_PORT) {
  app.commandLine.appendSwitch("remote-debugging-port", String(process.env.HAKIMI_DEBUG_PORT));
  app.commandLine.appendSwitch("remote-allow-origins", "*");
}

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
  if (!backendProcess || backendProcess.killed) return;
  if (!backendStartedByShell) return;
  try {
    childProcess.spawnSync("taskkill.exe", ["/PID", String(backendProcess.pid), "/T", "/F"], {
      windowsHide: true,
      stdio: "ignore"
    });
  } catch {
    try {
      backendProcess.kill();
    } catch {}
  }
}

function stopVerifiedBackendListener() {
  if (!isLoopbackHost(HOST)) return false;
  try {
    const script = buildVerifiedBackendStopScript({ port: PORT, serverPath: SERVER_PATH });
    const result = childProcess.spawnSync(
      "powershell.exe",
      ["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
      { cwd: PYTHON_ROOT, windowsHide: true, stdio: "pipe", encoding: "utf8", timeout: 12000 }
    );
    if (result.status === 0) return true;
    console.error(`[hakimi-backend] verified stop failed: ${(result.stderr || result.stdout || "unknown").trim()}`);
  } catch (error) {
    console.error(`[hakimi-backend] verified stop failed: ${error.message}`);
  }
  return false;
}

function stopBackendCompletely() {
  stopBackend();
  const stopped = stopVerifiedBackendListener();
  backendProcess = null;
  backendStartedByShell = false;
  return stopped;
}

function showMainWindow() {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.show();
  mainWindow.focus();
}

async function restartBackend() {
  if (!stopBackendCompletely()) {
    showBootMessage("无法重启后台", "8765 端口不是可验证的哈基米 Python 服务，请手动检查端口占用。 ");
    return;
  }
  showBootMessage("正在重启后台", "重新启动 Python 行情与策略服务。");
  startBackend();
  await waitForPort(HOST, PORT, 18000);
  if (await isBackendHealthy()) {
    await mainWindow?.loadURL(BASE_URL);
  } else {
    showBootMessage("重启失败", "后台服务没有在预期时间内就绪。");
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
        { label: "启动 FutuOpenD", click: () => startFutuOpenDIfNeeded() },
        { label: "富途配置", click: () => mainWindow?.loadURL(`${BASE_URL}/futu_setup.html`) },
        { label: "回到交易台", click: () => mainWindow?.loadURL(BASE_URL) },
        { label: "在浏览器打开", click: () => shell.openExternal(BASE_URL) },
        { type: "separator" },
        { label: "开发者工具", accelerator: "F12", click: () => mainWindow?.webContents.openDevTools({ mode: "detach" }) },
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
    { label: "富途配置", click: () => { showMainWindow(); mainWindow?.loadURL(`${BASE_URL}/futu_setup.html`); } },
    { label: "启动 FutuOpenD", click: () => startFutuOpenDIfNeeded() },
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
      webSecurity: true
    }
  });

  mainWindow.once("ready-to-show", () => {
    if (state.maximized) mainWindow.maximize();
    mainWindow.show();
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    const parsed = new URL(url);
    if (parsed.hostname === HOST && Number(parsed.port || 80) === PORT) {
      return { action: "allow" };
    }
    shell.openExternal(url);
    return { action: "deny" };
  });

  mainWindow.webContents.on("will-navigate", (event, url) => {
    const parsed = new URL(url);
    const isLocal = parsed.hostname === HOST && Number(parsed.port || 80) === PORT;
    const isBoot = parsed.protocol === "file:";
    if (!isLocal && !isBoot) {
      event.preventDefault();
      shell.openExternal(url);
    }
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
  startFutuOpenDIfNeeded();

  const initialHealth = await readBackendHealth();
  if (!initialHealth.healthy) {
    const portOccupied = initialHealth.reachable || await isPortOpen(HOST, PORT, 700);
    if (portOccupied) {
      showBootMessage("正在更新后台", "检测到旧版或源码已变化的本地服务，正在安全重启。");
      if (!stopVerifiedBackendListener()) {
        showBootMessage("无法启动", "8765 端口不是可验证的哈基米 Python 服务。");
        dialog.showErrorBox(APP_TITLE, "端口 8765 已被其他程序占用，未执行自动终止。");
        return;
      }
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
