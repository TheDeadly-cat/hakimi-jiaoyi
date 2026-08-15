const assert = require("assert");
const path = require("path");
const {
  RUNTIME_BUILD_SCHEMA_VERSION,
  buildVerifiedBackendStopScript,
  classifyBackendHealth,
  classifyBackendHealthResponse,
  isLoopbackHost,
} = require("./backend-runtime-contract");

function currentHealth(overrides = {}) {
  return {
    ok: true,
    paper_authorized: false,
    live_order_allowed: false,
    runtime_build: {
      schema_version: RUNTIME_BUILD_SCHEMA_VERSION,
      status: "PASS",
      restart_required: false,
      paper_authorized: false,
      live_order_allowed: false,
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
assert.strictEqual(classifyBackendHealth(currentHealth({
  runtime_build: { ...currentHealth().runtime_build, restart_required: true },
})).status, "RESTART_REQUIRED");
assert.strictEqual(classifyBackendHealth(currentHealth({ live_order_allowed: true })).status, "UNSAFE");
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
