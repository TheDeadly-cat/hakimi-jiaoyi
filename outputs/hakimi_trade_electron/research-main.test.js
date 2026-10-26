"use strict";
const test = require("node:test"), assert = require("node:assert/strict"), { EventEmitter } = require("node:events");
const { desktopSettings, expectedIdentity, writeDiagnostic, launchSpec, validateAnnouncement, startServer, isResearchEntry } = require("./research-main");

test("verified candidate profiles cannot be captured by the original single-instance window", () => {
  const original = desktopSettings("profile-root", {});
  const first = desktopSettings("profile-root", { HAKIMI_RESEARCH_DESKTOP_PROFILE: "a".repeat(64) });
  const repeated = desktopSettings("profile-root", { HAKIMI_RESEARCH_DESKTOP_PROFILE: "a".repeat(64) });
  const second = desktopSettings("profile-root", { HAKIMI_RESEARCH_DESKTOP_PROFILE: "b".repeat(64) });
  assert.notEqual(first.userData, original.userData);
  assert.notEqual(first.userData, second.userData);
  assert.deepEqual(first, repeated);
  assert.match(first.title, /日常候选/);
  assert.equal(original.title, "哈基米研究工作台");
  for (const value of ["", "../original", "a".repeat(63), "A".repeat(64)]) {
    assert.throws(() => desktopSettings("profile-root", { HAKIMI_RESEARCH_DESKTOP_PROFILE: value }), /身份无效/);
  }
});

test("Electron explicit file entry starts without require.main while imports and renderer processes remain inert", () => {
  const filename = require.resolve("./research-main"), runtime = {versions:{electron:"31.7.7"},type:"browser",argv:["electron",filename],platform:process.platform};
  assert.equal(isResearchEntry(runtime,filename,false),true);
  assert.equal(isResearchEntry({...runtime,type:"renderer"},filename,false),false);
  assert.equal(isResearchEntry({...runtime,versions:{}},filename,false),false);
  assert.equal(isResearchEntry({...runtime,argv:["electron",require.resolve("./research-main.test")]},filename,false),false);
  assert.equal(isResearchEntry({...runtime,argv:["electron"]},filename,false),false);
});

function child() {
  const value = new EventEmitter(); value.pid = 123; value.exitCode = null; value.signalCode = null; value.killed = false;
  value.stdout = new EventEmitter(); value.stderr = new EventEmitter(); value.stdout.setEncoding = value.stderr.setEncoding = () => {};
  value.kill = () => { value.killed = true; return true; }; return value;
}
test("independent entry launches only the canonical workbench with an argument array and ephemeral loopback port", () => {
  const spec = launchSpec({ workspace: "C:/research workspace", python: "C:/python path/python.exe", env: { HAKIMI_RUNTIME_READ_ONLY: "1" } });
  assert.equal(spec.executable, "C:/python path/python.exe");
  assert.deepEqual(spec.args.slice(0, 7), ["-I", "-B", "-u", "-X", "utf8", "-m", "hakimi_research.workbench_server"]);
  assert.deepEqual(spec.args.slice(-2), ["--port", "0"]);
  assert.equal(spec.options.shell, false); assert.equal(spec.options.windowsHide, true);
  assert.equal(spec.options.env.HAKIMI_RUNTIME_READ_ONLY, "1", "never relax legacy read-only mode");
  assert.ok(!JSON.stringify(spec).includes("exchange_terminal"));
});

test("bound candidates reject shadow packages and strip startup injection variables", async () => {
  const identity = { package_location: "C:/trial/runtime/Lib/site-packages/hakimi_research",
    python_executable: "C:/trial/runtime/python.exe", loaded_source_sha256: "a".repeat(64) };
  assert.deepEqual(expectedIdentity({ HAKIMI_RESEARCH_EXPECTED_IDENTITY: JSON.stringify(identity) }), identity);
  assert.throws(() => expectedIdentity({ HAKIMI_RESEARCH_DESKTOP_PROFILE: "a".repeat(64) }), /缺少/);
  assert.throws(() => expectedIdentity({ HAKIMI_RESEARCH_EXPECTED_IDENTITY: "{}" }), /不完整/);
  const spec = launchSpec({ workspace: "C:/data", python: identity.python_executable, identity,
    env: { PYTHONPATH: "shadow", PYTHONHOME: "shadow", NODE_OPTIONS: "--require shadow", ELECTRON_RUN_AS_NODE: "1" } });
  for (const key of ["PYTHONPATH", "PYTHONHOME", "NODE_OPTIONS", "ELECTRON_RUN_AS_NODE"]) assert.equal(spec.options.env[key], undefined);
  const valid = { url: "http://127.0.0.1:8766/", port: 8766, pid: 123, engine: "hakimi_research", ...identity };
  assert.equal(validateAnnouncement(valid, 123, identity).port, 8766);
  for (const change of [{ package_location: "C:/shadow/hakimi_research" }, { loaded_source_sha256: "b".repeat(64) },
    { python_executable: "C:/other/python.exe" }, { package_location: undefined }]) {
    assert.throws(() => validateAnnouncement({ ...valid, ...change }, 123, identity), /不一致/);
  }
  const process = child(); const started = startServer(spec, { spawnProcess: () => process });
  process.stdout.emit("data", JSON.stringify({ ...valid, package_location: "C:/shadow/hakimi_research" }) + "\n");
  await assert.rejects(started.ready, /回执无效/); assert.equal(process.killed, true);
});

test("diagnostics append new readable files and do not modify existing records", () => {
  const fs = require("node:fs"), os = require("node:os"), path = require("node:path");
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "hakimi-diagnostic-"));
  try {
    const old = path.join(root, "old.json"); fs.writeFileSync(old, "retained");
    const first = writeDiagnostic(root, { state: "USER_REQUESTED", new_economic_calculations: 0 });
    const second = writeDiagnostic(root, { state: "STARTUP_FAILED", error: "identity mismatch" });
    assert.notEqual(first.filename, second.filename);
    assert.equal(fs.readFileSync(first.filename, "utf8"), first.text);
    assert.equal(JSON.parse(first.text).schema_version, "workbench-desktop-diagnostic-v1");
    assert.equal(fs.readFileSync(old, "utf8"), "retained");
  } finally { fs.rmSync(root, { recursive: true }); }
});
test("only the owned process and announced canonical loopback URL are accepted", () => {
  const valid = { url: "http://127.0.0.1:8766/", port: 8766, pid: 123, engine: "hakimi_research" };
  assert.deepEqual(validateAnnouncement(valid, 123), valid);
  assert.deepEqual(validateAnnouncement({...valid,pid:456,parent_pid:123},123),{...valid,pid:456});
  assert.throws(()=>validateAnnouncement({...valid,pid:456,parent_pid:999},123));
  for (const patch of [{ pid: 999 }, { engine: "legacy" }, { port: 8765 }, { url: "http://localhost:8766/" },
    { url: "http://127.0.0.1:8766/?token=x" }, { url: "https://example.org/" }, { url: "http://name@127.0.0.1:8766/" }]) {
    assert.throws(() => validateAnnouncement({ ...valid, ...patch }, 123));
  }
});
test("split startup receipts are parsed once and invalid startup stops only its child handle", async () => {
  const process = child(); const launched = startServer(launchSpec({ workspace: "research" }), { spawnProcess: () => process });
  process.stdout.emit("data", '{"url":"http://127.0.0.1:8766/","port":');
  process.stdout.emit("data", '8766,"pid":123,"engine":"hakimi_research"}\n');
  assert.equal((await launched.ready).port, 8766); assert.equal(process.killed, false);
  const invalid = child(); const failed = startServer(launchSpec({ workspace: "research" }), { spawnProcess: () => invalid });
  invalid.stdout.emit("data", 'not a receipt\n');
  await assert.rejects(failed.ready, /回执无效/); assert.equal(invalid.killed, true);
});
test("early exit and timeout do not open an unrelated existing service", async () => {
  const process = child(); const launched = startServer(launchSpec({ workspace: "research" }), { spawnProcess: () => process });
  process.stderr.emit("data", "No module named hakimi_research.workbench_server"); process.emit("exit", 1);
  await assert.rejects(launched.ready, /找不到正式工作台模块/);
  const silent = child(); const waiting = startServer(launchSpec({ workspace: "research" }), { spawnProcess: () => silent, timeoutMs: 5 });
  await assert.rejects(waiting.ready, /超时/); assert.equal(silent.killed, true);
});
