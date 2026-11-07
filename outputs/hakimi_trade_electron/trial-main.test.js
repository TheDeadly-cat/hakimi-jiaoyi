"use strict";
const test = require("node:test"), assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), os = require("node:os"), crypto = require("node:crypto");
const { EventEmitter } = require("node:events");
const { canonical, verifyBundle, probeRuntime, trialPaths, workspacePathAssessment, physicalWorkspaceAssessment, bindWorkspace, isTrialEntry } = require("./trial-main");
const hash = value => crypto.createHash("sha256").update(value).digest("hex");

function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "hakimi-trial-node-"));
  const files = {};
  for (const name of ["runtime/python/python.exe", "runtime/python/Lib/site-packages/hakimi_research/__init__.py", "resources/app/runtime-probe.py", "resources/default_app.asar", "HakimiWorkbench.exe"]) {
    fs.mkdirSync(path.dirname(path.join(root, name)), { recursive: true }); fs.writeFileSync(path.join(root, name), "FAKE_NOT_EXECUTED"); files[name] = hash("FAKE_NOT_EXECUTED");
  }
  const expected = { version: "0.6.0.dev4", source_status: "BUILD_VERIFIED", source_sha256: "a".repeat(64), build_receipt: { content_sha256: "a".repeat(64) }, environment_status: "VERIFIED", lock_sha256: "b".repeat(64) };
  const core = { schema_version: "research-windows-trial-v1", platform: "win32-x64", files, python: "runtime/python/python.exe",
    package_directory: "runtime/python/Lib/site-packages/hakimi_research", probe: "resources/app/runtime-probe.py", desktop_entry: "HakimiWorkbench.exe", expected_installation: expected,
    runtimes: { python: { version: "3.14.6" } } };
  const manifest = { ...core, bundle_id: hash(canonical(core)) };
  fs.writeFileSync(path.join(root, "trial-manifest.json"), canonical(manifest));
  return { root, manifest, expected, close() { fs.rmSync(root, { recursive: true }); } };
}

test("trial accepts the complete frozen tree and rejects additions or changed bytes", () => {
  const f = fixture();
  try {
    assert.equal(verifyBundle(f.root).bundle_id, f.manifest.bundle_id);
    fs.writeFileSync(path.join(f.root, "shadow.py"), "unexpected");
    assert.throws(() => verifyBundle(f.root), /inventory_changed/); fs.unlinkSync(path.join(f.root, "shadow.py"));
    fs.writeFileSync(path.join(f.root, f.manifest.python), "changed");
    assert.throws(() => verifyBundle(f.root), /hash_changed/);
  } finally { f.close(); }
});

test("archive bytes remain part of the frozen manifest", () => {
  const f = fixture();
  try {
    assert.equal(verifyBundle(f.root).bundle_id, f.manifest.bundle_id);
    fs.appendFileSync(path.join(f.root, "resources/default_app.asar"), "changed");
    assert.throws(() => verifyBundle(f.root), /trial_file_hash_changed:resources\/default_app.asar/);
  } finally { f.close(); }
});

test("Electron explicit and package entries run while imported verifier stays inert", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "hakimi-trial-entry-"));
  const filename = path.join(root, "trial-main.js");
  const runtime = { versions: { electron: "31.7.7" }, type: "browser", platform: process.platform, argv: ["electron", "unrelated-probe.js"] };
  try {
    assert.equal(isTrialEntry(runtime, filename, false, root), false);
    fs.writeFileSync(path.join(root, "package.json"), JSON.stringify({ main: "probe-main.js" }));
    assert.equal(isTrialEntry(runtime, filename, false, root), false);
    fs.writeFileSync(path.join(root, "package.json"), JSON.stringify({ main: "trial-main.js" }));
    assert.equal(isTrialEntry(runtime, filename, false, root), true);
    assert.equal(isTrialEntry({ ...runtime, argv: ["electron", filename] }, filename, false), true);
    assert.equal(isTrialEntry(runtime, filename, true), true);
    assert.equal(isTrialEntry({ ...runtime, type: "renderer" }, filename, true, root), false);
    assert.equal(isTrialEntry({ ...runtime, versions: {} }, filename, true, root), false);
  } finally { fs.rmSync(root, { recursive: true }); }
});

test("default trial data stays outside program files and ignores legacy workspace overrides", () => {
  const app = { getPath: () => path.join(os.tmpdir(), "home") }, manifest = { bundle_id: "c".repeat(64) };
  const a = trialPaths(app, manifest, { LOCALAPPDATA: path.join(os.tmpdir(), "local"), HAKIMI_RESEARCH_WORKSPACE: "legacy" });
  const b = trialPaths(app, manifest, { LOCALAPPDATA: path.join(os.tmpdir(), "local") });
  assert.deepEqual(a, b); assert.ok(a.workspace.endsWith(manifest.bundle_id.slice(0, 20))); assert.ok(a.workspace.includes("HakimiTradeTrial"));
});

test("short workspace name binds the full identity and never adopts or overwrites another workspace", () => {
  // AppData can be virtualized by the process host. Normal-path fixtures use a
  // short user-owned directory; redirection itself is explicitly tested below.
  const root = fs.mkdtempSync(path.join(os.homedir(), "hakimi-workspace-")), data = path.join(root, "data"), id = "a".repeat(64);
  try {
    bindWorkspace(data, id); const marker = path.join(data, "trial-workspace-identity.json"), before = fs.readFileSync(marker);
    fs.writeFileSync(path.join(data, "old.json"), "retained"); bindWorkspace(data, id);
    assert.deepEqual(fs.readFileSync(marker), before);
    assert.throws(() => bindWorkspace(data, "a".repeat(20) + "b".repeat(44)), /identity_conflict/);
    assert.equal(fs.readFileSync(path.join(data, "old.json"), "utf8"), "retained");
    const other = path.join(root, "existing"); fs.mkdirSync(other); fs.writeFileSync(path.join(other, "old.json"), "retained");
    assert.throws(() => bindWorkspace(other, id), /existing_records_not_adopted/);
    assert.equal(fs.existsSync(path.join(other, "trial-workspace-identity.json")), false);
    const tooLong = path.join(root, "x".repeat(180));
    assert.ok(workspacePathAssessment(tooLong).maximum_characters >= 260);
    assert.throws(() => bindWorkspace(tooLong, id), /path_too_long/);
    assert.equal(fs.existsSync(tooLong), false);
  } finally { fs.rmSync(root, { recursive: true }); }
});

test("physical workspace length is checked before a marker or research record is written", () => {
  const root = fs.mkdtempSync(path.join(os.homedir(), "hakimi-path-")), data = path.join(root, "data"), id = "a".repeat(64);
  const redirected = path.join(root, "Packages", "host".repeat(20), "LocalCache", "Local", "data");
  try {
    assert.ok(workspacePathAssessment(data).maximum_characters < 260);
    assert.ok(workspacePathAssessment(redirected).maximum_characters >= 260);
    assert.throws(() => bindWorkspace(data, id, { resolveNative: () => redirected }), error => {
      assert.match(error.message, /trial_workspace_redirected_path_too_long/);
      assert.equal(error.workspace_paths.physical, redirected); return true;
    });
    assert.deepEqual(fs.readdirSync(data), []);
    const actual = physicalWorkspaceAssessment(data);
    assert.equal(actual.directory, fs.realpathSync.native(data));
    const bound = bindWorkspace(data, id);
    assert.equal(bound.directory, actual.directory);
    const marker = path.join(data, "trial-workspace-identity.json"), before = fs.readFileSync(marker);
    assert.throws(() => bindWorkspace(data, id, { resolveNative: () => redirected }), /redirected_path_too_long/);
    assert.deepEqual(fs.readFileSync(marker), before);
  } finally { fs.rmSync(root, { recursive: true }); }
});

test("probe uses only bundled Python, handles drift and never launches an engine", async () => {
  const f = fixture();
  try {
    const prefix = path.join(f.root, "runtime/python");
    const actual = { ...f.expected, python: path.join(f.root, f.manifest.python), package_directory: path.join(f.root, f.manifest.package_directory), isolated_venv: false, package_inside_venv: true,
      python_version: "3.14.6", python_prefix: prefix, python_base_prefix: prefix, import_search_paths: [path.join(prefix, "Lib"), path.join(prefix, "Lib/site-packages")] };
    function factory(value) {
      return (exe, args, options) => {
        assert.equal(exe, actual.python); assert.deepEqual(args.slice(0, 4), ["-I", "-B", "-X", "utf8"]);
        assert.ok(args.at(-1).endsWith("runtime-probe.py")); assert.equal(options.shell, false);
        const child = new EventEmitter(); child.stdout = new EventEmitter(); child.stderr = new EventEmitter();
        child.stdout.setEncoding = child.stderr.setEncoding = () => {}; child.kill = () => {};
        queueMicrotask(() => { child.stdout.emit("data", JSON.stringify(value)); child.emit("close", 0); }); return child;
      };
    }
    assert.deepEqual(await probeRuntime(f.root, f.manifest, { spawnProcess: factory(actual) }), actual);
    await assert.rejects(probeRuntime(f.root, f.manifest, { spawnProcess: factory({ ...actual, python: path.join(f.root, "external.exe") }) }), /location_changed/);
    await assert.rejects(probeRuntime(f.root, f.manifest, { spawnProcess: factory({ ...actual, source_sha256: "f".repeat(64) }) }), /identity_changed/);
    await assert.rejects(probeRuntime(f.root, f.manifest, { spawnProcess: factory({ ...actual, import_search_paths: [path.join(f.root, "external/Lib")] }) }), /external_python/);
    await assert.rejects(probeRuntime(f.root, f.manifest, { spawnProcess: factory({ ...actual, python_version: "3.14.7" }) }), /external_python/);
  } finally { f.close(); }
});
