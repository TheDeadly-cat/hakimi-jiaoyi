"use strict";

// A separate packaged entry. It neither selects a global interpreter nor writes
// inside the immutable distribution. The existing local/developer entry remains.
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { spawn } = require("node:child_process");
const { runDesktop, writeDiagnostic, identityPath } = require("./research-main");

function canonical(value) {
  if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
  if (value && typeof value === "object") return "{" + Object.keys(value).sort().map(k => JSON.stringify(k) + ":" + canonical(value[k])).join(",") + "}";
  return JSON.stringify(value);
}
const hash = bytes => crypto.createHash("sha256").update(bytes).digest("hex");

function boundPath(root, name) {
  if (typeof name !== "string" || !name || name.includes("\\") || name.includes(":")
      || path.posix.isAbsolute(name) || name.split("/").some(x => !x || x === "." || x === "..")) throw new Error("trial_relative_path_invalid");
  const full = path.resolve(root, name), relative = path.relative(root, fs.realpathSync(full));
  if (relative.startsWith("..") || path.isAbsolute(relative) || fs.lstatSync(full).isSymbolicLink()) throw new Error("trial_path_escape");
  return full;
}

function verifyBundle(root) {
  root = fs.realpathSync(root);
  const manifest = JSON.parse(fs.readFileSync(path.join(root, "trial-manifest.json"), "utf8"));
  const { bundle_id: id, ...core } = manifest;
  if (manifest.schema_version !== "research-windows-trial-v1" || id !== hash(canonical(core))
      || manifest.platform !== "win32-x64" || !manifest.files || !Object.keys(manifest.files).length) throw new Error("trial_manifest_identity_invalid");
  if (Object.keys(manifest.files).some(name => path.resolve(root, name).length >= 260)) throw new Error("trial_program_path_too_long");
  const observed = [];
  function walk(directory, prefix = "") {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const name = prefix + entry.name, full = path.join(directory, entry.name);
      if (entry.isSymbolicLink()) throw new Error("trial_symlink_not_allowed");
      if (entry.isDirectory()) walk(full, name + "/");
      else if (entry.isFile() && name !== "trial-manifest.json") observed.push(name);
      else if (!entry.isFile()) throw new Error("trial_special_file_not_allowed");
    }
  }
  walk(root);
  if (canonical(observed.sort()) !== canonical(Object.keys(manifest.files).sort())) throw new Error("trial_file_inventory_changed");
  for (const [name, expected] of Object.entries(manifest.files)) {
    if (!/^[a-f0-9]{64}$/.test(expected) || hash(fs.readFileSync(boundPath(root, name))) !== expected) throw new Error("trial_file_hash_changed:" + name);
  }
  for (const key of ["python", "package_directory", "probe", "desktop_entry"]) boundPath(root, manifest[key]);
  if (manifest.python !== "runtime/python/python.exe" || manifest.package_directory !== "runtime/python/Lib/site-packages/hakimi_research"
      || manifest.probe !== "resources/app/runtime-probe.py" || manifest.desktop_entry !== "HakimiWorkbench.exe") throw new Error("trial_runtime_layout_changed");
  return manifest;
}

function probeRuntime(root, manifest, { spawnProcess = spawn, timeoutMs = 30000 } = {}) {
  const env = { ...process.env };
  for (const key of ["PYTHONPATH", "PYTHONHOME", "NODE_OPTIONS", "ELECTRON_RUN_AS_NODE"]) delete env[key];
  return new Promise((resolve, reject) => {
    const child = spawnProcess(boundPath(root, manifest.python), ["-I", "-B", "-X", "utf8", boundPath(root, manifest.probe)],
      { cwd: root, env, shell: false, windowsHide: true, stdio: ["ignore", "pipe", "pipe"] });
    let text = "", settled = false;
    const finish = (error, value) => {
      if (settled) return;
      settled = true; clearTimeout(timer);
      if (error) { try { child.kill(); } catch {} reject(error); } else resolve(value);
    };
    const timer = setTimeout(() => finish(new Error("trial_runtime_probe_timeout")), timeoutMs);
    child.stdout.setEncoding("utf8"); child.stderr.setEncoding("utf8");
    child.stderr.on("data", () => {}); // Do not copy arbitrary dependency output into user diagnostics.
    child.stdout.on("data", chunk => { text += chunk; if (Buffer.byteLength(text) > 65536) finish(new Error("trial_runtime_probe_too_large")); });
    child.on("error", () => finish(new Error("trial_bundled_python_unavailable")));
    child.on("close", code => {
      if (code !== 0) return finish(new Error("trial_bundled_runtime_check_failed"));
      try {
        const value = JSON.parse(text);
        for (const key of ["version", "source_status", "source_sha256", "build_receipt", "environment_status", "lock_sha256"]) {
          if (canonical(value[key]) !== canonical(manifest.expected_installation[key])) throw new Error("trial_installed_identity_changed:" + key);
        }
        if (identityPath(value.python) !== identityPath(boundPath(root, manifest.python))
            || identityPath(value.package_directory) !== identityPath(boundPath(root, manifest.package_directory))
            || value.package_inside_venv !== true || value.isolated_venv !== false) throw new Error("trial_bundled_runtime_location_changed");
        const prefix = identityPath(path.dirname(boundPath(root, manifest.python))), separator = prefix.includes("\\") ? "\\" : "/";
        if (value.python_version !== manifest.runtimes.python.version || identityPath(value.python_prefix) !== prefix
            || identityPath(value.python_base_prefix) !== prefix || !Array.isArray(value.import_search_paths) || !value.import_search_paths.length
            || !value.import_search_paths.every(p => typeof p === "string" && (identityPath(p) === prefix || identityPath(p).startsWith(prefix + separator)))) {
          throw new Error("trial_external_python_search_path_or_version");
        }
        finish(null, value);
      } catch (error) { finish(error); }
    });
  });
}

function trialPaths(app, manifest, env = process.env) {
  const local = env.LOCALAPPDATA && path.isAbsolute(env.LOCALAPPDATA) ? env.LOCALAPPDATA : path.join(app.getPath("home"), "AppData", "Local");
  const base = path.join(local, "HakimiTradeTrial");
  return { workspace: path.join(base, "workspaces", manifest.bundle_id.slice(0, 20)), diagnostics: path.join(base, "diagnostics") };
}

function workspacePathAssessment(directory) {
  const h = "a".repeat(64), uuid = "a".repeat(36), revision = "a".repeat(32);
  const layouts = [
    `data/snapshots/${h}/${h}.json`, `data/csv-imports/${h}/${h}/conversion.json`,
    `tasks/task-${uuid}/versions/r0001-${revision}/inputs/snapshot.json`,
    `runs/run-${h}/inputs/snapshot.json`, `validations/validation-${h}/base/inputs/snapshot.json`,
    `validations/validation-${h}/benchmark-buy_and_hold/report.json`, `operations/${uuid}/result.json`,
  ];
  const paths = layouts.map(relative => ({ layout: relative, utf16_characters: path.resolve(directory, relative).length }));
  return { maximum_characters: Math.max(...paths.map(p => p.utf16_characters)), legacy_windows_limit: 260, paths,
    scope: "Known first-use snapshot, CSV original, task, run, validation and operation layouts with generated IDs; not arbitrary external filenames." };
}

function bindWorkspace(directory, bundleId) {
  if (!/^[a-f0-9]{64}$/.test(bundleId)) throw new Error("trial_workspace_identity_invalid");
  const assessment = workspacePathAssessment(directory);
  if (assessment.maximum_characters >= assessment.legacy_windows_limit) throw new Error(`trial_workspace_path_too_long:${assessment.maximum_characters}`);
  if (fs.existsSync(directory) && fs.lstatSync(directory).isSymbolicLink()) throw new Error("trial_workspace_symlink_not_allowed");
  fs.mkdirSync(directory, { recursive: true });
  const marker = path.join(directory, "trial-workspace-identity.json"), expected = { schema_version: "research-trial-workspace-v1", bundle_id: bundleId };
  function check() {
    if (fs.lstatSync(marker).isSymbolicLink() || canonical(JSON.parse(fs.readFileSync(marker, "utf8"))) !== canonical(expected)) throw new Error("trial_workspace_identity_conflict");
  }
  if (fs.existsSync(marker)) { check(); return assessment; }
  if (fs.readdirSync(directory).length) throw new Error("trial_workspace_existing_records_not_adopted");
  try { fs.writeFileSync(marker, canonical(expected) + "\n", { encoding: "utf8", flag: "wx" }); }
  catch (error) { if (error.code !== "EEXIST") throw error; check(); }
  return assessment;
}

async function runTrial(electron, root = path.resolve(__dirname, "../..")) {
  const { app, dialog, clipboard } = electron;
  let manifest = null, locations = trialPaths(app, { bundle_id: "startup" });
  try {
    if (process.platform !== "win32" || process.arch !== "x64") throw new Error("trial_requires_windows_x64");
    manifest = verifyBundle(root);
    locations = trialPaths(app, manifest);
    const actual = await probeRuntime(root, manifest);
    bindWorkspace(locations.workspace, manifest.bundle_id);
    process.env.HAKIMI_RESEARCH_PYTHON = actual.python;
    process.env.HAKIMI_RESEARCH_WORKSPACE = locations.workspace;
    process.env.HAKIMI_RESEARCH_DESKTOP_PROFILE = manifest.bundle_id;
    process.env.HAKIMI_RESEARCH_TRIAL = "1";
    process.env.HAKIMI_RESEARCH_EXPECTED_IDENTITY = JSON.stringify({ package_location: actual.package_directory,
      python_executable: actual.python, loaded_source_sha256: actual.source_sha256 });
    await runDesktop(electron);
  } catch (error) {
    await app.whenReady();
    let saved = null;
    try { saved = writeDiagnostic(locations.diagnostics, { state: "TRIAL_STARTUP_FAILED", error: String(error.message).slice(0, 2000),
      bundle_id: manifest?.bundle_id || null, new_economic_calculations: 0 }); } catch {}
    const dataPathTooLong = String(error.message).startsWith("trial_workspace_path_too_long");
    const choice = await dialog.showMessageBox({ type: "error", title: "试用版暂时无法打开",
      message: dataPathTooLong ? "当前用户的数据目录过长，已在创建研究记录前停止。" : "程序文件或运行环境未通过检查。已有数据和结果保持不变。",
      detail: (dataPathTooLong ? "请复制诊断信息，联系维护者选择较短的数据位置。已有记录保持不变，不需要启用系统功能。"
        : "请将同一试用包完整解压到较短的新文件夹后重试。仍有问题时复制诊断信息。") + (saved ? `\n诊断文件：${saved.filename}` : ""),
      buttons: saved ? ["复制诊断信息", "关闭"] : ["关闭"], defaultId: saved ? 1 : 0, cancelId: saved ? 1 : 0 });
    if (saved && choice.response === 0) clipboard.writeText(saved.text);
    app.quit();
  }
}

if (process.versions.electron && process.type === "browser") runTrial(require("electron"));
module.exports = { canonical, boundPath, verifyBundle, probeRuntime, trialPaths, workspacePathAssessment, bindWorkspace, runTrial };
