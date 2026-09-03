const path = require("path");

const RUNTIME_BUILD_SCHEMA_VERSION = "hakimi-runtime-build-v1";
const CAPABILITY_SCHEMA_VERSION = "capability-v1";
const PRODUCT_CAPABILITY_CATALOG_SCHEMA_VERSION = "product-capability-catalog-v2";
const CAPABILITY_FIELDS = [
  "live_allowed",
  "paper_allowed",
  "product_mode",
  "research_only",
  "schema_version",
];
const EXPECTED_PRODUCT_CAPABILITIES = {
  product_capability_catalog: "Supported",
  market_data_research: "Supported",
  historical_backtest: "Supported",
  deterministic_frozen_benchmark: "Supported",
  deterministic_strategy_family_benchmark: "Supported",
  deterministic_strategy_robustness_benchmark: "Supported",
  deterministic_strategy_statistical_correction_benchmark: "Supported",
  research_reporting: "Supported",
  strategy_catalog: "Supported",
  local_research_terminal: "Experimental",
  parameter_optimization: "Archived",
  paper_execution: "Archived",
  live_execution: "Archived",
  order_entry: "Disabled",
};
const EXPECTED_CLI_COMMANDS = {
  backtest: "Supported",
  "frozen-benchmark": "Supported",
  "strategy-family-benchmark": "Supported",
  "strategy-robustness-benchmark": "Supported",
  "strategy-statistical-correction-benchmark": "Supported",
  "strategy-research-dossier": "Supported",
  capabilities: "Supported",
  "list-strategies": "Supported",
  optimize: "Archived",
  paper: "Archived",
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
    && value.schema_version === CAPABILITY_SCHEMA_VERSION
    && value.product_mode === "research_only"
    && value.research_only === true
    && value.paper_allowed === false
    && value.live_allowed === false;
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

function powershellQuote(value) {
  return `'${String(value).replace(/'/g, "''")}'`;
}

function buildVerifiedBackendStopScript({ port, serverPath }) {
  const cleanPort = Number(port);
  if (!Number.isInteger(cleanPort) || cleanPort < 1 || cleanPort > 65535) {
    throw new Error("Invalid backend port");
  }
  const expected = path.resolve(String(serverPath || "")).replace(/\\/g, "/").toLowerCase();
  if (!expected.endsWith("/exchange_terminal/server.py")) {
    throw new Error("Invalid backend server path");
  }
  return [
    "$ErrorActionPreference='Stop'",
    `$listener=Get-NetTCPConnection -State Listen -LocalPort ${cleanPort} -ErrorAction SilentlyContinue | Select-Object -First 1`,
    "if (-not $listener) { exit 0 }",
    "$owner=Get-CimInstance Win32_Process -Filter \"ProcessId=$($listener.OwningProcess)\"",
    "if (-not $owner) { throw 'Backend port owner is unavailable' }",
    "$exe=[IO.Path]::GetFileName([string]$owner.ExecutablePath).ToLowerInvariant()",
    "$command=([string]$owner.CommandLine).Replace('\\\\','/').ToLowerInvariant()",
    `$expected=${powershellQuote(expected)}`,
    "$relative='exchange_terminal/server.py'",
    "if (-not $exe.StartsWith('python') -or (-not $command.Contains($expected) -and -not $command.Contains($relative))) { throw 'Port owner is not the Hakimi Python backend' }",
    "Stop-Process -Id ([int]$listener.OwningProcess) -ErrorAction Stop",
    "$deadline=(Get-Date).AddSeconds(8)",
    `do { Start-Sleep -Milliseconds 100; $remaining=Get-NetTCPConnection -State Listen -LocalPort ${cleanPort} -ErrorAction SilentlyContinue | Select-Object -First 1 } while ($remaining -and (Get-Date) -lt $deadline)`,
    "if ($remaining) { throw 'Hakimi backend port did not close' }",
  ].join("; ");
}

module.exports = {
  CAPABILITY_SCHEMA_VERSION,
  EXPECTED_CLI_COMMANDS,
  EXPECTED_PRODUCT_CAPABILITIES,
  PRODUCT_CAPABILITY_CATALOG_SCHEMA_VERSION,
  RUNTIME_BUILD_SCHEMA_VERSION,
  buildVerifiedBackendStopScript,
  classifyBackendHealth,
  classifyBackendHealthResponse,
  isLoopbackHost,
  isExactResearchOnlyProductCatalog,
  parseBackendHealthResponse,
};
