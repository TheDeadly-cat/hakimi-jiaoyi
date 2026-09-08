const assert = require("assert");
const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const indexSource = fs.readFileSync(
  path.join(root, "python_quant_bot", "exchange_terminal", "static", "index.html"),
  "utf8",
);
const appSource = fs.readFileSync(
  path.join(root, "python_quant_bot", "exchange_terminal", "static", "app.js"),
  "utf8",
);
const mainSource = fs.readFileSync(path.join(__dirname, "main.js"), "utf8");
const packageJson = JSON.parse(fs.readFileSync(path.join(__dirname, "package.json"), "utf8"));
const readme = fs.readFileSync(path.join(__dirname, "README.md"), "utf8");

assert.match(indexSource, /当前产品仅支持本地数据研究、历史回测、确定性 Frozen benchmark/);
assert.match(indexSource, /data-archived-capability-surface/);
assert.match(indexSource, /id="armStrategy" data-archived-capability-control disabled/);
assert.match(indexSource, /class="manual-trade-layout" data-archived-capability-surface/);
assert.match(indexSource, /class="conditional-panel" data-archived-capability-surface/);
assert.match(indexSource, /class="transfer-panel" data-archived-capability-surface/);
assert.match(indexSource, /class="guardian-panel" data-archived-capability-surface/);
assert.match(indexSource, /class="daemon-panel" data-archived-capability-surface/);

assert.match(appSource, /const PRODUCT_CAPABILITY_LOCK = Object\.freeze/);
assert.match(appSource, /paper_execution: "Archived"/);
assert.match(appSource, /live_execution: "Archived"/);
assert.match(appSource, /order_entry: "Disabled"/);
assert.match(appSource, /function applyResearchOnlyCapabilityLock\(\)/);
assert.match(appSource, /if \(blockArchivedCapability\("paper_execution", "strategyAnalysis"\)\) return;/);
assert.match(appSource, /if \(blockArchivedCapability\("order_entry"\)\) return;/);
assert.match(appSource, /if \(blockArchivedCapability\("live_execution", "apiKeyState"\)\) return;/);

function functionBlock(name) {
  const start = appSource.indexOf(`async function ${name}`);
  assert.ok(start >= 0, `missing function ${name}`);
  const candidates = [
    appSource.indexOf("\nasync function ", start + 1),
    appSource.indexOf("\nfunction ", start + 1),
  ].filter((value) => value >= 0);
  return appSource.slice(start, Math.min(...candidates));
}

for (const [name, requestToken] of [
  ["armStrategy", "apiMutation("],
  ["stopStrategy", "apiMutation("],
  ["resetPaper", "apiMutation("],
  ["manualPaperOrder", "apiMutation("],
  ["addCondition", "apiMutation("],
  ["estimateOrder", "api("],
  ["cancelCondition", "apiMutation("],
  ["transferAsset", "apiMutation("],
  ["setGuardian", "apiMutation("],
  ["guardianEmergencyStop", "apiMutation("],
  ["prepareDaemon", "apiMutation("],
  ["saveApiConfig", "apiMutation("],
]) {
  const source = functionBlock(name);
  const guard = source.indexOf("blockArchivedCapability(");
  const request = source.indexOf(requestToken);
  assert.ok(guard >= 0, `${name} missing capability guard`);
  assert.ok(request >= 0, `${name} missing expected request token`);
  assert.ok(guard < request, `${name} guard must precede network request`);
}

const bootBlock = mainSource.slice(
  mainSource.indexOf("async function boot()"),
  mainSource.indexOf('app.on("second-instance"'),
);
assert.ok(bootBlock);
assert.doesNotMatch(bootBlock, /startFutuOpenDIfNeeded/);
assert.match(mainSource, /const APP_TITLE = "哈基米研究 v2"/);
assert.match(packageJson.description, /Research-only desktop shell/);
assert.match(readme, /research-only/);
assert.doesNotMatch(readme, /回测寻优支持/);

console.log("research capability lock tests passed");
