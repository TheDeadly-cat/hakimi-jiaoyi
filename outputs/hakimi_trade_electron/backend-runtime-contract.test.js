const assert = require("assert");
const fs = require("fs");
const path = require("path");
const {
  CAPABILITY_SCHEMA_VERSION,
  EXPECTED_CLI_COMMANDS,
  EXPECTED_PRODUCT_CAPABILITIES,
  PRODUCT_CAPABILITY_DEFINITION_PATH,
  PRODUCT_CAPABILITY_CATALOG_SCHEMA_VERSION,
  RUNTIME_BUILD_SCHEMA_VERSION,
  buildVerifiedBackendStopScript,
  classifyBackendHealth,
  classifyBackendHealthResponse,
  isLoopbackHost,
  validateProductCapabilityDefinition,
} = require("./backend-runtime-contract");

function currentHealth(overrides = {}) {
  const capability = {
    product_mode: "research_only",
    research_only: true,
    paper_allowed: false,
    live_allowed: false,
    schema_version: CAPABILITY_SCHEMA_VERSION,
  };
  const productCapabilityCatalog = {
    schema_version: PRODUCT_CAPABILITY_CATALOG_SCHEMA_VERSION,
    product_mode: "research_only",
    capabilities: { ...EXPECTED_PRODUCT_CAPABILITIES },
    cli_commands: { ...EXPECTED_CLI_COMMANDS },
    authority: capability,
  };
  return {
    ok: true,
    read_only: true,
    runtime_mutations_allowed: false,
    guardian_worker_running: false,
    paper_armed: false,
    paper_authorized: false,
    paper_order_allowed: false,
    automated_paper_order_allowed: false,
    live_order_allowed: false,
    capability,
    product_capability_catalog: productCapabilityCatalog,
    runtime_build: {
      schema_version: RUNTIME_BUILD_SCHEMA_VERSION,
      status: "PASS",
      restart_required: false,
      paper_authorized: false,
      live_order_allowed: false,
      capability,
      product_capability_catalog: productCapabilityCatalog,
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
const capabilityDefinition = JSON.parse(
  fs.readFileSync(PRODUCT_CAPABILITY_DEFINITION_PATH, "utf8"),
);
const unsafeAuthority = structuredClone(capabilityDefinition);
unsafeAuthority.catalog.authority.paper_allowed = true;
assert.throws(
  () => validateProductCapabilityDefinition(unsafeAuthority),
  /product_capability_definition_authority_invalid/,
);
const numericAuthority = structuredClone(capabilityDefinition);
numericAuthority.catalog.authority.paper_allowed = 0;
assert.throws(
  () => validateProductCapabilityDefinition(numericAuthority),
  /product_capability_definition_authority_invalid/,
);
const unsafeCapability = structuredClone(capabilityDefinition);
unsafeCapability.catalog.capabilities.find(
  ({ name }) => name === "paper_execution",
).status = "Supported";
assert.throws(
  () => validateProductCapabilityDefinition(unsafeCapability),
  /product_capability_definition_execution_lock_invalid/,
);
const unsafeBinding = structuredClone(capabilityDefinition);
unsafeBinding.catalog.cli_bindings.find(
  ({ command }) => command === "paper",
).capability = "historical_backtest";
assert.throws(
  () => validateProductCapabilityDefinition(unsafeBinding),
  /product_capability_definition_archived_cli_lock_invalid/,
);
assert.strictEqual(classifyBackendHealth({ ok: true }).status, "RESTART_REQUIRED");
assert.strictEqual(classifyBackendHealth(currentHealth()).healthy, true);
for (const override of [
  { read_only: false }, { read_only: undefined }, { runtime_mutations_allowed: true },
  { guardian_worker_running: true }, { paper_armed: true },
]) {
  assert.equal(classifyBackendHealth(currentHealth(override)).reason, "read_only_preview_required");
}
assert.strictEqual(classifyBackendHealth(currentHealth({ capability: undefined })).status, "RESTART_REQUIRED");
assert.deepStrictEqual(
  classifyBackendHealth(currentHealth({ product_capability_catalog: undefined })),
  {
    healthy: false,
    reachable: true,
    status: "RESTART_REQUIRED",
    reason: "product_capability_catalog_missing_or_invalid",
  },
);
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
assert.strictEqual(classifyBackendHealth(currentHealth({
  product_capability_catalog: {
    ...currentHealth().product_capability_catalog,
    capabilities: {
      ...currentHealth().product_capability_catalog.capabilities,
      paper_execution: "Supported",
    },
  },
})).status, "RESTART_REQUIRED");
assert.deepStrictEqual(
  classifyBackendHealth(currentHealth({
    runtime_build: {
      ...currentHealth().runtime_build,
      product_capability_catalog: {
        ...currentHealth().runtime_build.product_capability_catalog,
        cli_commands: {
          ...currentHealth().runtime_build.product_capability_catalog.cli_commands,
          optimize: "Supported",
        },
      },
    },
  })),
  {
    healthy: false,
    reachable: true,
    status: "RESTART_REQUIRED",
    reason: "product_capability_catalog_missing_or_invalid",
  },
);
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
assert.throws(() => buildVerifiedBackendStopScript({ port: 8765, serverPath }), /process termination is disabled/);
assert.throws(() => buildVerifiedBackendStopScript({ port: 0, serverPath }), /process termination is disabled/);
assert.throws(() => buildVerifiedBackendStopScript({ port: 8765, serverPath: "C:\\other.py" }), /process termination is disabled/);

console.log("backend runtime contract tests passed");
