const assert = require("assert");
const path = require("path");
const {
  CAPABILITY_SCHEMA_VERSION,
  RUNTIME_BUILD_SCHEMA_VERSION,
  buildVerifiedBackendStopScript,
  classifyBackendHealth,
  classifyBackendHealthResponse,
  isLoopbackHost,
} = require("./backend-runtime-contract");

function currentHealth(overrides = {}) {
  const capability = {
    product_mode: "research_only",
    research_only: true,
    paper_allowed: false,
    live_allowed: false,
    schema_version: CAPABILITY_SCHEMA_VERSION,
  };
  return {
    ok: true,
    paper_authorized: false,
    paper_order_allowed: false,
    automated_paper_order_allowed: false,
    live_order_allowed: false,
    capability,
    runtime_build: {
      schema_version: RUNTIME_BUILD_SCHEMA_VERSION,
      status: "PASS",
      restart_required: false,
      paper_authorized: false,
      live_order_allowed: false,
      capability,
    },
    ...overrides,
  };
}

assert.deepStrictEqual(classifyBackendHealth(null), {
  healthy: false,
  reachable: false,
  status: "OFFLINE",
  reason: "health_unavailable",
});
assert.strictEqual(classifyBackendHealth({ ok: true }).status, "RESTART_REQUIRED");
assert.strictEqual(classifyBackendHealth(currentHealth()).healthy, true);
assert.strictEqual(classifyBackendHealth(currentHealth({ capability: undefined })).status, "RESTART_REQUIRED");
assert.strictEqual(classifyBackendHealth(currentHealth({
  capability: { ...currentHealth().capability, schema_version: "capability-v2" },
})).status, "RESTART_REQUIRED");
assert.strictEqual(classifyBackendHealth(currentHealth({
  capability: {
    schema_version: CAPABILITY_SCHEMA_VERSION,
    live_allowed: false,
    paper_allowed: false,
    research_only: true,
    product_mode: "research_only",
  },
})).healthy, true);
assert.strictEqual(classifyBackendHealth(currentHealth({
  runtime_build: { ...currentHealth().runtime_build, restart_required: true },
})).status, "RESTART_REQUIRED");
assert.strictEqual(classifyBackendHealth(currentHealth({ live_order_allowed: true })).status, "UNSAFE");
assert.strictEqual(classifyBackendHealth(currentHealth({ paper_authorized: "false" })).status, "UNSAFE");
assert.strictEqual(classifyBackendHealthResponse({
  statusCode: 200,
  body: JSON.stringify(currentHealth()),
}).healthy, true);
assert.strictEqual(classifyBackendHealthResponse({ statusCode: 200, body: "not-json" }).healthy, false);
assert.strictEqual(isLoopbackHost("127.0.0.1"), true);
assert.strictEqual(isLoopbackHost("localhost"), true);
assert.strictEqual(isLoopbackHost("192.0.2.1"), false);

const serverPath = path.join("C:\\workspace", "python_quant_bot", "exchange_terminal", "server.py");
const stopScript = buildVerifiedBackendStopScript({ port: 8765, serverPath });
assert.match(stopScript, /LocalPort 8765/);
assert.match(stopScript, /StartsWith\('python'\)/);
assert.match(stopScript, /exchange_terminal\/server\.py/);
assert.match(stopScript, /Stop-Process/);
assert.throws(() => buildVerifiedBackendStopScript({ port: 0, serverPath }), /Invalid backend port/);
assert.throws(() => buildVerifiedBackendStopScript({ port: 8765, serverPath: "C:\\other.py" }), /Invalid backend server path/);

console.log("backend runtime contract tests passed");
