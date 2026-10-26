"use strict";

// Explicit browser-process regression. Never starts Python or a research window.
// All fixtures and results are retained in a new evidence directory.
const fs = process.versions.electron ? require("original-fs") : require("node:fs");
const path = require("node:path"), crypto = require("node:crypto"), assert = require("node:assert/strict");
const hash = bytes => crypto.createHash("sha256").update(bytes).digest("hex");
function option(name) { const i = process.argv.indexOf(name); assert.ok(i >= 0 && process.argv[i + 1], "required " + name); return path.resolve(process.argv[i + 1]); }
function save(filename, value) { fs.writeFileSync(filename, JSON.stringify(value, null, 2) + "\n", { flag: "wx" }); }

async function browserProbe() {
  const { app, BrowserWindow, dialog } = require("electron"), output = option("--output"), bundle = option("--bundle");
  app.setPath("userData", path.join(output, "browser-profile")); app.disableHardwareAcceleration();
  const result = { schema_version: "trial-electron-asar-regression-v1", recorded_at: new Date().toISOString(),
    electron: process.versions.electron, process_type: process.type, executable: process.execPath,
    source_sha256: hash(fs.readFileSync(path.join(__dirname, "trial-main.js"))), bundle, new_economic_runs: 0, backend_starts: 0 };
  const originalSpawn = require("node:child_process").spawn, originalDialog = dialog.showMessageBox;
  let spawnCalls = 0, dialogCalls = 0;
  require("node:child_process").spawn = () => { spawnCalls++; throw new Error("test_forbids_backend_start"); };
  dialog.showMessageBox = async () => { dialogCalls++; throw new Error("test_forbids_import_side_effect"); };
  try {
    const trial = require("./trial-main");
    assert.equal(trial.isTrialEntry(process, path.join(__dirname, "trial-main.js"), false, app.getAppPath()), false);
    const driveRoot = path.parse(output).root;
    const nativePath = trial.physicalWorkspaceAssessment(driveRoot);
    assert.equal(nativePath.directory, fs.realpathSync.native(driveRoot));
    result.original_fs_native_path = nativePath.directory;
    const archive = path.join(bundle, "resources/default_app.asar"), raw = fs.readFileSync(archive);
    let virtualError;
    try { require("node:fs").readFileSync(archive); } catch (error) { virtualError = { code: error.code, message: error.message }; }
    assert.ok(virtualError, "real Electron must reproduce the virtual archive read failure");
    const manifest = trial.verifyBundle(bundle);
    assert.equal(hash(raw), manifest.files["resources/default_app.asar"]);
    result.bundle_id = manifest.bundle_id; result.verified_file_count = Object.keys(manifest.files).length;
    result.asar_sha256 = hash(raw); result.node_fs_archive_error = virtualError;
    // Suppress only the frozen r1 unconditional launch line. All verifier code
    // remains exact and is executed in the actual Electron browser process.
    const oldFile = path.join(bundle, "resources/app/trial-main.js"), oldSource = fs.readFileSync(oldFile, "utf8");
    const launchLine = 'if (process.versions.electron && process.type === "browser") runTrial(require("electron"));';
    assert.equal(oldSource.split(launchLine).length, 2, "expected frozen r1 launch line");
    const Module = require("node:module"), legacy = new Module(oldFile, module);
    legacy.filename = oldFile; legacy.paths = Module._nodeModulePaths(path.dirname(oldFile));
    legacy._compile(oldSource.replace(launchLine, "// Startup suppressed only in this read-only regression harness."), oldFile);
    assert.throws(() => legacy.exports.verifyBundle(bundle), /ENOENT/);
    result.legacy_verifier = { source_sha256: hash(Buffer.from(oldSource)), launch_line_suppressed: true, outcome: "EXPECTED_ENOENT" };
    // Only the new synthetic fixture is tampered; original package stays read-only.
    const fixture = path.join(output, "asar-fixture"), files = {};
    for (const name of ["runtime/python/python.exe", "runtime/python/Lib/site-packages/hakimi_research/__init__.py", "resources/app/runtime-probe.py", "HakimiWorkbench.exe", "resources/default_app.asar"]) {
      const bytes = name.endsWith(".asar") ? raw : Buffer.from("SYNTHETIC_NEVER_EXECUTED");
      fs.mkdirSync(path.dirname(path.join(fixture, name)), { recursive: true }); fs.writeFileSync(path.join(fixture, name), bytes, { flag: "wx" }); files[name] = hash(bytes);
    }
    const { bundle_id, ...core } = manifest; core.files = files;
    save(path.join(fixture, "trial-manifest.json"), { ...core, bundle_id: hash(trial.canonical(core)) });
    trial.verifyBundle(fixture);
    fs.appendFileSync(path.join(fixture, "resources/default_app.asar"), "tampered");
    assert.throws(() => trial.verifyBundle(fixture), /trial_file_hash_changed:resources\/default_app.asar/);
    result.archive_tamper = "REJECTED";
    await app.whenReady();
    assert.equal(spawnCalls, 0); assert.equal(dialogCalls, 0); assert.equal(BrowserWindow.getAllWindows().length, 0);
    result.import_started_backend_or_window = false; result.status = "PASS_REAL_ELECTRON_ARCHIVE_AND_IMPORT";
    save(path.join(output, "browser-result.json"), result); app.exit(0);
  } catch (error) {
    result.status = "FAIL"; result.error = error.stack; result.spawn_calls = spawnCalls; result.dialog_calls = dialogCalls;
    save(path.join(output, "browser-result.json"), result); app.exit(1);
  } finally { require("node:child_process").spawn = originalSpawn; dialog.showMessageBox = originalDialog; }
}

function nodeDriver() {
  const electron = option("--electron"), bundle = option("--bundle"), output = option("--output");
  assert.equal(fs.existsSync(output), false, "evidence output must be new; keep failed evidence");
  fs.mkdirSync(output, { recursive: true });
  const env = { ...process.env };
  for (const name of ["ELECTRON_RUN_AS_NODE", "NODE_OPTIONS", "PYTHONHOME", "PYTHONPATH"]) delete env[name];
  function execute(args, label) {
    const value = require("node:child_process").spawnSync(electron, args, { env, windowsHide: true, encoding: "utf8", timeout: 45000 });
    save(path.join(output, label + "-process.json"), { args, status: value.status, signal: value.signal,
      error: value.error?.message || null, stdout: value.stdout, stderr: value.stderr });
    assert.equal(value.error, undefined); assert.equal(value.status, 0, label + " exit status");
  }
  execute([__filename, "--browser-probe", "--bundle", bundle, "--output", output], "browser");
  const appRoot = path.join(output, "entry-fixture/resources/app"); fs.mkdirSync(appRoot, { recursive: true });
  fs.copyFileSync(path.join(__dirname, "trial-main.js"), path.join(appRoot, "trial-main.js"), fs.constants.COPYFILE_EXCL);
  save(path.join(appRoot, "package.json"), { name: "trial-entry-regression", version: "0.0.0", main: "trial-main.js" });
  save(path.join(output, "entry-fixture/trial-manifest.json"), {}); // Rejects before Python/workspace.
  const stub = `"use strict";
const fs=require("original-fs"),path=require("node:path"),assert=require("node:assert/strict"),{app,dialog,BrowserWindow}=require("electron");
const output=${JSON.stringify(output)};
app.setPath("userData",path.join(output,"entry-profile"));app.disableHardwareAcceleration();
const timer=setTimeout(()=>app.exit(74),15000);let diagnostic=null;
dialog.showMessageBox=async()=>{assert.equal(diagnostic.state,"TRIAL_STARTUP_FAILED");assert.equal(diagnostic.error,"trial_manifest_identity_invalid");assert.equal(BrowserWindow.getAllWindows().length,0);clearTimeout(timer);
fs.writeFileSync(path.join(output,"package-entry-result.json"),JSON.stringify({status:"PASS_REAL_ELECTRON_PACKAGE_ENTRY",electron:process.versions.electron,process_type:process.type,app_path:app.getAppPath(),argv:process.argv,require_main:require.main?.filename||null,expected_rejected_fixture:true,backend_starts:0,new_economic_runs:0,windows:0}),{flag:"wx"});return {response:1};};
module.exports={runDesktop:()=>{throw new Error("test_forbids_backend_start");},identityPath:x=>x,writeDiagnostic:(directory,value)=>{diagnostic=value;return {filename:"TEST_NO_PRODUCT_DIAGNOSTIC",text:JSON.stringify(value)};}};
`;
  fs.writeFileSync(path.join(appRoot, "research-main.js"), stub, { flag: "wx" });
  execute([appRoot], "package-entry");
  assert.equal(JSON.parse(fs.readFileSync(path.join(output, "package-entry-result.json"))).status, "PASS_REAL_ELECTRON_PACKAGE_ENTRY");
  save(path.join(output, "summary.json"), { status: "PASS_REAL_ELECTRON_ASAR_AND_ENTRY", recorded_at: new Date().toISOString(),
    electron, electron_sha256: hash(fs.readFileSync(electron)), bundle, output,
    source_sha256: hash(fs.readFileSync(path.join(__dirname, "trial-main.js"))),
    test_sha256: hash(fs.readFileSync(__filename)), new_economic_runs: 0, backend_starts: 0, windows: 0,
    scope: "Actual Electron browser process, unchanged r1 bundle verified read-only; synthetic package entry rejects before runtime/workspace. No full native product acceptance." });
  console.log(JSON.stringify({ status: "PASS_REAL_ELECTRON_ASAR_AND_ENTRY", output }));
}

if (process.versions.electron) browserProbe(); else nodeDriver();
