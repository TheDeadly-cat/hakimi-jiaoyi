"use strict";

const fs = process.versions.electron ? require("original-fs") : require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const hash = raw => crypto.createHash("sha256").update(raw).digest("hex");
function canonical(value) {
  if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
  if (value && typeof value === "object") return "{" + Object.keys(value).sort().map(key => JSON.stringify(key) + ":" + canonical(value[key])).join(",") + "}";
  return JSON.stringify(value);
}
function noLinks(full) {
  for (let cursor = full; ; cursor = path.dirname(cursor)) {
    if (fs.lstatSync(cursor).isSymbolicLink()) throw new Error("terminal_reparse_path_rejected");
    if (cursor === path.dirname(cursor)) break;
  }
}
function boundPath(root, name) {
  if (typeof name !== "string" || !name || /[\\:]/.test(name) || path.posix.isAbsolute(name)
      || name.split("/").some(part => !part || part === "." || part === "..")) throw new Error("terminal_relative_path_invalid");
  const full = path.resolve(root, name);
  noLinks(full);
  const relative = path.relative(root, fs.realpathSync(full));
  if (relative.startsWith("..") || path.isAbsolute(relative)) throw new Error("terminal_resource_escape");
  return full;
}
function verifyBundle(inputRoot) {
  noLinks(inputRoot);
  const root = fs.realpathSync(inputRoot);
  const manifest = JSON.parse(fs.readFileSync(boundPath(root, "terminal-manifest.json"), "utf8"));
  const { bundle_id: bundleId, ...core } = manifest;
  if (manifest.schema_version !== "hakimi-original-terminal-v1" || manifest.platform !== "win32-x64"
      || bundleId !== hash(canonical(core)) || !manifest.files || !Object.keys(manifest.files).length)
    throw new Error("terminal_manifest_identity_invalid");
  const observed = [];
  function walk(directory, prefix = "") {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const name = prefix + entry.name, full = path.join(directory, entry.name);
      noLinks(full);
      if (entry.isDirectory()) walk(full, name + "/");
      else if (entry.isFile() && name !== "terminal-manifest.json") observed.push(name);
      else if (!entry.isFile()) throw new Error("terminal_special_file_rejected");
    }
  }
  walk(root);
  if (canonical(observed.sort()) !== canonical(Object.keys(manifest.files).sort())) throw new Error("terminal_file_inventory_changed");
  for (const [name, expected] of Object.entries(manifest.files)) {
    if (!/^[a-f0-9]{64}$/.test(expected) || hash(fs.readFileSync(boundPath(root, name))) !== expected)
      throw new Error("terminal_file_hash_changed:" + name);
  }
  if (manifest.python !== "runtime/python/python.exe" || manifest.bootstrap !== "resources/app/terminal-bootstrap.py"
      || manifest.desktop_entry !== "HakimiTrade.exe" || manifest.backend_entry !== "exchange_terminal.server"
      || manifest.primary_route !== "/?workspace=quant" || manifest.quant_route !== "/quant/") throw new Error("terminal_runtime_layout_changed");
  for (const name of [manifest.python, manifest.bootstrap, manifest.desktop_entry]) boundPath(root, name);
  return manifest;
}
function physicalDirectory(value, { allowMissing = false } = {}) {
  if (typeof value !== "string" || !path.isAbsolute(value)) throw new Error("terminal_absolute_directory_required");
  const full = path.resolve(value);
  let nearest = full;
  for (let cursor = full; ; cursor = path.dirname(cursor)) {
    try {
      const info = fs.lstatSync(cursor);
      if (info.isSymbolicLink()) throw new Error("terminal_reparse_path_rejected");
      if (!info.isDirectory()) throw new Error("terminal_directory_required");
    } catch (error) {
      if (!allowMissing || error.code !== "ENOENT") throw error;
      if (nearest === cursor) nearest = path.dirname(cursor);
    }
    if (cursor === path.dirname(cursor)) break;
  }
  // Resolve an existing ancestor, retaining a not-yet-created workspace suffix.
  return path.resolve(fs.realpathSync(nearest), path.relative(nearest, full));
}
function dataDirectory(value, programRoot) {
  const directory = physicalDirectory(value, { allowMissing: true });
  const relative = path.relative(programRoot, directory);
  if (!relative || (!relative.startsWith("..") && !path.isAbsolute(relative))) throw new Error("terminal_workspace_inside_program_rejected");
  return directory;
}
function instanceIdentity(installation, workspace) {
  return hash(canonical({ installation: physicalPath(physicalDirectory(installation)),
    workspace: physicalPath(physicalDirectory(workspace, { allowMissing: true })) }));
}
function createContext({ resourcesPath, localAppData, home, runtimeDirectory, quantWorkspaceDirectory }) {
  const root = path.resolve(resourcesPath, "..");
  const manifest = verifyBundle(root);
  const local = localAppData && path.isAbsolute(localAppData) ? localAppData : path.join(home, "AppData", "Local");
  const legacyRuntime = dataDirectory(runtimeDirectory || path.join(local, "HakimiTradeTerminal", "workspaces", "default", "runtime"), root);
  const workspace = dataDirectory(quantWorkspaceDirectory || legacyRuntime, root);
  const instanceId = instanceIdentity(root, workspace);
  const userData = dataDirectory(path.join(local, "HakimiTradeTerminal", "shells", instanceId), root);
  return { root, manifest, legacyRuntime, workspace, instanceId, userData,
    pythonRoot: path.join(root, "components", "terminal") };
}
function cleanEnvironment(environment) {
  return Object.fromEntries(Object.entries(environment).filter(([key]) => !key.toUpperCase().startsWith("PYTHON")
    && !["NODE_OPTIONS", "ELECTRON_RUN_AS_NODE", "CHROME_CRASHPAD_PIPE_NAME", "CHROME_CRASHPAD_SERVER_URL"].includes(key.toUpperCase())));
}
function configureDiagnostics({ app, programRoot, profile, environment, changeDirectory }) {
  // This application does not enable crashReporter. Do not let Windows child
  // processes register with an unrelated launcher's inherited Crashpad pipe.
  // Chromium does this before Electron initializes renderer logging, and a
  // failed registration writes debug.log beside the EXE, irrespective of cwd.
  for (const key of Object.keys(environment)) {
    if (["CHROME_CRASHPAD_PIPE_NAME", "CHROME_CRASHPAD_SERVER_URL"].includes(key.toUpperCase())) delete environment[key];
  }
  const directory = dataDirectory(path.join(profile, "diagnostics"), programRoot);
  fs.mkdirSync(directory, { recursive: true });
  const physical = dataDirectory(directory, programRoot);
  const chromiumLog = path.join(physical, "electron.log");
  environment.ELECTRON_LOG_FILE = chromiumLog;
  environment.ELECTRON_ENABLE_LOGGING = "file";
  app.commandLine.appendSwitch("log-file", chromiumLog);
  app.commandLine.appendSwitch("enable-logging", "file");
  app.commandLine.appendSwitch("log-level", "2");
  app.setAppLogsPath(physical);
  // Keep relative diagnostics and subprocess defaults outside the bundle too.
  // This alone cannot redirect Windows pre-initialization Crashpad logging.
  // Run synchronously before singleton setup, readiness, windows or children.
  changeDirectory(physical);
  return { directory: physical, chromiumLog };
}
function createStartupDiagnostic({ directory, secrets = [], environment = {} }) {
  const destination = physicalDirectory(directory);
  const file = path.join(destination, `backend-startup-${Date.now()}-${crypto.randomBytes(6).toString("hex")}.json`);
  const privateValues = [...secrets, ...Object.entries(environment)
    .filter(([key]) => /token|secret|password|api.?key|credential|authorization/i.test(key)).map(([, value]) => value)]
    .filter(value => typeof value === "string" && value.length >= 4).sort((a, b) => b.length - a.length);
  const inputLimit = 65536, outputLimit = 8192;
  let captured = "", truncated = false, finished = false, saved = null;
  return {
    file,
    append(chunk) {
      if (finished || truncated) return;
      const value = String(chunk);
      const remaining = inputLimit - captured.length;
      captured += value.slice(0, remaining);
      truncated = value.length > remaining;
    },
    finish(status, exitCode = null) {
      if (finished) return saved;
      finished = true;
      // Discard a cut-off line before redaction so a partial secret is never
      // persisted when the input bound falls within its value.
      let stderr = truncated ? captured.slice(0, Math.max(0, captured.lastIndexOf("\n") + 1)) : captured;
      for (const value of privateValues) stderr = stderr.split(value).join("[REDACTED]");
      stderr = stderr.replace(/^.*(?:authorization|[\w-]*(?:token|secret|password|api[_-]?key|credential)[\w-]*)["']?\s*[:=].*$/gmi, "[REDACTED credential line]")
        .replace(/\bsk-[A-Za-z0-9_-]{8,}\b/g, "[REDACTED]");
      truncated ||= stderr.length > outputLimit;
      const record = { schema_version: "terminal-startup-diagnostic-v1",
        status: ["READY", "NOT_READY", "EXITED", "SPAWN_ERROR"].includes(status) ? status : "NOT_READY",
        exit_code: Number.isInteger(exitCode) ? exitCode : null, stderr: stderr.slice(0, outputLimit), truncated };
      captured = "";
      // A diagnostic-write failure must not replace the startup result or
      // interrupt cooperative shutdown (for example when storage is full).
      try {
        fs.writeFileSync(file, JSON.stringify(record, null, 2) + "\n", { encoding: "utf8", flag: "wx", mode: 0o600 });
        saved = file;
      } catch {}
      return saved;
    },
  };
}
function backendLaunch(context, { host, port, token, localOnly, environment = process.env }) {
  // No shell parsing, global Python discovery, inherited PYTHONPATH, or current
  // directory imports. Each argument remains separate for Chinese/space paths.
  return {
    executable: boundPath(context.root, context.manifest.python),
    args: ["-I", "-S", "-B", "-X", "utf8", boundPath(context.root, context.manifest.bootstrap), "--host", host, "--port", String(port), "--no-browser"],
    options: { cwd: physicalDirectory(dataDirectory(context.diagnosticsDirectory, context.root)), shell: false, windowsHide: true, stdio: ["ignore", "pipe", "pipe"],
      env: { ...cleanEnvironment(environment), HAKIMI_RUNTIME_DIR: context.legacyRuntime || context.workspace,
        HAKIMI_QUANT_WORKSPACE_DIR: context.workspace,
        HAKIMI_DESKTOP_CONTROL_TOKEN: token, HAKIMI_RUNTIME_READ_ONLY: "1", HAKIMI_QUANT_READ_ONLY: "0",
        HAKIMI_LOCAL_ONLY: localOnly ? "1" : "0", HAKIMI_TERMINAL_PACKAGE_ID: context.manifest.bundle_id,
        HAKIMI_TERMINAL_PACKAGE_VERSION: context.manifest.version,
        HAKIMI_TERMINAL_BUILD_COMMIT: context.manifest.source_provenance.git.commit,
        HAKIMI_LOAD_LOCAL_AI_ENV: "0", HAKIMI_SKIP_LOCAL_AI_ENV: "1",
        FUTU_PY_APPDATA: path.join(context.workspace, "futu-sdk") } },
  };
}
function physicalPath(value) {
  if (typeof value !== "string" || !path.isAbsolute(value)) return null;
  let full;
  try { full = fs.realpathSync(value); } catch { full = path.resolve(value); }
  return process.platform === "win32" ? full.toLowerCase() : full;
}
function matchesBackend(context, payload, localOnly) {
  return (context.manifest ? payload?.terminal_package_id === context.manifest.bundle_id : !payload?.terminal_package_id)
    && payload?.local_only === localOnly
    && physicalPath(payload?.terminal_workspace_root) === physicalPath(context.workspace);
}
module.exports = { canonical, hash, boundPath, verifyBundle, createContext, cleanEnvironment, backendLaunch, matchesBackend,
  physicalDirectory, dataDirectory, instanceIdentity, configureDiagnostics, createStartupDiagnostic };
