const path = require("path");

const RUNTIME_BUILD_SCHEMA_VERSION = "hakimi-runtime-build-v1";

function parseBackendHealthResponse(response) {
  if (!response || response.statusCode !== 200 || typeof response.body !== "string") return null;
  try {
    const payload = JSON.parse(response.body);
    return payload && typeof payload === "object" && !Array.isArray(payload) ? payload : null;
  } catch {
    return null;
  }
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
  if (
    payload.paper_authorized !== false ||
    payload.live_order_allowed !== false ||
    runtime.paper_authorized !== false ||
    runtime.live_order_allowed !== false
  ) {
    return { healthy: false, reachable: true, status: "UNSAFE", reason: "execution_authority_invalid" };
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
    "$command=([string]$owner.CommandLine).Replace('\\','/').ToLowerInvariant()",
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
  RUNTIME_BUILD_SCHEMA_VERSION,
  buildVerifiedBackendStopScript,
  classifyBackendHealth,
  classifyBackendHealthResponse,
  isLoopbackHost,
  parseBackendHealthResponse,
};
