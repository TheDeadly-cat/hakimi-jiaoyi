const fs = require("fs");
const path = require("path");

const RUNTIME_BUILD_SCHEMA_VERSION = "hakimi-runtime-build-v1";
const PRODUCT_CAPABILITY_DEFINITION_PATH = path.resolve(
  __dirname,
  "..",
  "..",
  "src",
  "hakimi_research",
  "contracts",
  "product-capabilities.json",
);
const DEFINITION_SCHEMA_VERSION = "product-capability-definition-v1";
const PRODUCT_CAPABILITY_CATALOG_SCHEMA_VERSION = "product-capability-catalog-v2";
const CAPABILITY_SCHEMA_VERSION = "capability-v1";
const SAFE_CAPABILITY_NAME = /^[a-z][a-z0-9_]*$/;
const SAFE_CLI_COMMAND = /^[a-z][a-z0-9-]*$/;
const ALLOWED_STATUSES = new Set(["Supported", "Experimental", "Archived", "Disabled"]);
const LOCKED_AUTHORITY = {
  schema_version: CAPABILITY_SCHEMA_VERSION,
  product_mode: "research_only",
  research_only: true,
  paper_allowed: false,
  live_allowed: false,
};
const LOCKED_CAPABILITY_STATUSES = {
  parameter_optimization: "Archived",
  paper_execution: "Archived",
  live_execution: "Archived",
  order_entry: "Disabled",
};
const LOCKED_CLI_BINDINGS = {
  optimize: "parameter_optimization",
  paper: "paper_execution",
};

function canonicalJson(value) {
  if (Array.isArray(value)) return value.map(canonicalJson);
  if (value && typeof value === "object") {
    return Object.keys(value).sort().reduce((result, key) => {
      result[key] = canonicalJson(value[key]);
      return result;
    }, {});
  }
  return value;
}

function sameExactJson(left, right) {
  return JSON.stringify(canonicalJson(left)) === JSON.stringify(canonicalJson(right));
}

function hasExactFields(value, fields) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const keys = Object.keys(value);
  return keys.length === fields.length
    && fields.every((field) => Object.prototype.hasOwnProperty.call(value, field));
}

function validateProductCapabilityDefinition(raw) {
  if (!hasExactFields(raw, ["$schema", "definition_schema_version", "catalog"])) {
    throw new Error("product_capability_definition_shape_invalid");
  }
  if (raw.$schema !== "./product-capabilities.schema.json") {
    throw new Error("product_capability_definition_schema_reference_invalid");
  }
  if (raw.definition_schema_version !== DEFINITION_SCHEMA_VERSION) {
    throw new Error("product_capability_definition_version_invalid");
  }

  const catalog = raw.catalog;
  if (!hasExactFields(catalog, [
    "schema_version",
    "product_mode",
    "authority",
    "capabilities",
    "cli_bindings",
  ])) {
    throw new Error("product_capability_definition_catalog_shape_invalid");
  }
  if (catalog.schema_version !== PRODUCT_CAPABILITY_CATALOG_SCHEMA_VERSION) {
    throw new Error("product_capability_definition_catalog_version_invalid");
  }
  if (catalog.product_mode !== "research_only") {
    throw new Error("product_capability_definition_product_mode_invalid");
  }
  if (!sameExactJson(catalog.authority, LOCKED_AUTHORITY)) {
    throw new Error("product_capability_definition_authority_invalid");
  }

  if (!Array.isArray(catalog.capabilities) || catalog.capabilities.length === 0) {
    throw new Error("product_capability_definition_capabilities_invalid");
  }
  const capabilityItems = catalog.capabilities.map((item) => {
    if (!hasExactFields(item, ["name", "status"])) {
      throw new Error("product_capability_definition_capability_shape_invalid");
    }
    if (typeof item.name !== "string" || !SAFE_CAPABILITY_NAME.test(item.name)) {
      throw new Error("product_capability_definition_capability_name_invalid");
    }
    if (typeof item.status !== "string" || !ALLOWED_STATUSES.has(item.status)) {
      throw new Error("product_capability_definition_capability_status_invalid");
    }
    return [item.name, item.status];
  });
  const capabilityNames = new Set(capabilityItems.map(([name]) => name));
  if (capabilityNames.size !== capabilityItems.length) {
    throw new Error("product_capability_definition_capability_duplicate");
  }
  const capabilities = Object.fromEntries(capabilityItems);
  for (const [name, expectedStatus] of Object.entries(LOCKED_CAPABILITY_STATUSES)) {
    if (capabilities[name] !== expectedStatus) {
      throw new Error("product_capability_definition_execution_lock_invalid");
    }
  }

  if (!Array.isArray(catalog.cli_bindings) || catalog.cli_bindings.length === 0) {
    throw new Error("product_capability_definition_cli_bindings_invalid");
  }
  const cliBindings = catalog.cli_bindings.map((item) => {
    if (!hasExactFields(item, ["command", "capability"])) {
      throw new Error("product_capability_definition_cli_binding_shape_invalid");
    }
    if (typeof item.command !== "string" || !SAFE_CLI_COMMAND.test(item.command)) {
      throw new Error("product_capability_definition_cli_command_invalid");
    }
    if (typeof item.capability !== "string" || !capabilityNames.has(item.capability)) {
      throw new Error("product_capability_definition_cli_capability_invalid");
    }
    return [item.command, item.capability];
  });
  const commandNames = new Set(cliBindings.map(([command]) => command));
  if (commandNames.size !== cliBindings.length) {
    throw new Error("product_capability_definition_cli_command_duplicate");
  }
  const bindings = Object.fromEntries(cliBindings);
  for (const [command, expectedCapability] of Object.entries(LOCKED_CLI_BINDINGS)) {
    if (bindings[command] !== expectedCapability) {
      throw new Error("product_capability_definition_archived_cli_lock_invalid");
    }
  }

  return {
    authority: Object.freeze({ ...catalog.authority }),
    capabilities: Object.freeze(capabilities),
    cliBindings: Object.freeze(cliBindings.map((item) => Object.freeze([...item]))),
  };
}

function loadProductCapabilityDefinition(
  definitionPath = PRODUCT_CAPABILITY_DEFINITION_PATH,
) {
  let raw;
  try {
    raw = JSON.parse(fs.readFileSync(definitionPath, "utf8"));
  } catch (error) {
    throw new Error("product_capability_definition_unreadable", { cause: error });
  }
  return validateProductCapabilityDefinition(raw);
}

const PRODUCT_CAPABILITY_DEFINITION = Object.freeze(loadProductCapabilityDefinition());
const EXPECTED_CAPABILITY = PRODUCT_CAPABILITY_DEFINITION.authority;
const CAPABILITY_FIELDS = Object.freeze(Object.keys(EXPECTED_CAPABILITY).sort());
const EXPECTED_PRODUCT_CAPABILITIES = PRODUCT_CAPABILITY_DEFINITION.capabilities;
const EXPECTED_CLI_COMMANDS = Object.freeze(Object.fromEntries(
  PRODUCT_CAPABILITY_DEFINITION.cliBindings.map(([command, capability]) => (
    [command, EXPECTED_PRODUCT_CAPABILITIES[capability]]
  )),
));

function parseBackendHealthResponse(response) {
  if (!response || response.statusCode !== 200 || typeof response.body !== "string") return null;
  try {
    const payload = JSON.parse(response.body);
    return payload && typeof payload === "object" && !Array.isArray(payload) ? payload : null;
  } catch {
    return null;
  }
}

function isExactResearchOnlyCapability(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const fields = Object.keys(value).sort();
  return JSON.stringify(fields) === JSON.stringify(CAPABILITY_FIELDS)
    && sameExactJson(value, EXPECTED_CAPABILITY);
}

function isExactResearchOnlyProductCatalog(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const fields = Object.keys(value).sort();
  const expectedFields = [
    "authority",
    "capabilities",
    "cli_commands",
    "product_mode",
    "schema_version",
  ];
  return JSON.stringify(fields) === JSON.stringify(expectedFields)
    && value.schema_version === PRODUCT_CAPABILITY_CATALOG_SCHEMA_VERSION
    && value.product_mode === "research_only"
    && isExactResearchOnlyCapability(value.authority)
    && sameExactJson(value.capabilities, EXPECTED_PRODUCT_CAPABILITIES)
    && sameExactJson(value.cli_commands, EXPECTED_CLI_COMMANDS);
}

function hasLegacyAuthorityClaim(payload, runtime) {
  const legacyFields = [
    [payload, "paper_authorized"],
    [payload, "paper_order_allowed"],
    [payload, "automated_paper_order_allowed"],
    [payload, "live_order_allowed"],
    [runtime, "paper_authorized"],
    [runtime, "live_order_allowed"],
  ];
  return legacyFields.some(([container, key]) => (
    container
    && Object.prototype.hasOwnProperty.call(container, key)
    && container[key] !== false
  ));
}

function classifyBackendHealth(payload) {
  if (!payload || typeof payload !== "object") {
    return { healthy: false, reachable: false, status: "OFFLINE", reason: "health_unavailable" };
  }

  const runtime = payload.runtime_build;

  if (!runtime || typeof runtime !== "object") {
    return { healthy: false, reachable: true, status: "RESTART_REQUIRED", reason: "runtime_contract_missing" };
  }
  if (runtime.schema_version !== RUNTIME_BUILD_SCHEMA_VERSION) {
    return { healthy: false, reachable: true, status: "RESTART_REQUIRED", reason: "runtime_contract_version_mismatch" };
  }
  if (runtime.status !== "PASS" || runtime.restart_required !== false) {
    return { healthy: false, reachable: true, status: "RESTART_REQUIRED", reason: "runtime_source_drift" };
  }
  if (hasLegacyAuthorityClaim(payload, runtime)) {
    return { healthy: false, reachable: true, status: "UNSAFE", reason: "execution_authority_invalid" };
  }
  if (payload.read_only !== true || payload.runtime_mutations_allowed !== false
      || payload.guardian_worker_running !== false || payload.paper_armed !== false) {
    return { healthy: false, reachable: true, status: "RESTART_REQUIRED", reason: "read_only_preview_required" };
  }
  if (
    !isExactResearchOnlyCapability(payload.capability)
    || !isExactResearchOnlyCapability(runtime.capability)
  ) {
    return { healthy: false, reachable: true, status: "RESTART_REQUIRED", reason: "capability_contract_missing_or_invalid" };
  }
  if (!CAPABILITY_FIELDS.every((field) => payload.capability[field] === runtime.capability[field])) {
    return { healthy: false, reachable: true, status: "RESTART_REQUIRED", reason: "capability_contract_mismatch" };
  }
  if (
    !isExactResearchOnlyProductCatalog(payload.product_capability_catalog)
    || !isExactResearchOnlyProductCatalog(runtime.product_capability_catalog)
  ) {
    return { healthy: false, reachable: true, status: "RESTART_REQUIRED", reason: "product_capability_catalog_missing_or_invalid" };
  }
  if (
    !sameExactJson(payload.product_capability_catalog, runtime.product_capability_catalog)
    || !sameExactJson(payload.product_capability_catalog.authority, payload.capability)
  ) {
    return { healthy: false, reachable: true, status: "RESTART_REQUIRED", reason: "product_capability_catalog_mismatch" };
  }
  if (payload.ok !== true) {
    return { healthy: false, reachable: true, status: "UNHEALTHY", reason: "health_not_ok" };
  }
  return { healthy: true, reachable: true, status: "CURRENT", reason: "" };
}

function classifyBackendHealthResponse(response) {
  const payload = parseBackendHealthResponse(response);
  return { ...classifyBackendHealth(payload), payload };
}

function isLoopbackHost(host) {
  return ["127.0.0.1", "localhost", "::1"].includes(String(host || "").trim().toLowerCase());
}

function buildVerifiedBackendStopScript(_options) {
  throw new Error("Port-based process termination is disabled");
}

module.exports = {
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
  isExactResearchOnlyProductCatalog,
  loadProductCapabilityDefinition,
  parseBackendHealthResponse,
  validateProductCapabilityDefinition,
};
