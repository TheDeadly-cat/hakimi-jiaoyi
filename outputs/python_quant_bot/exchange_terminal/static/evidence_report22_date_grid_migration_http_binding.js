"use strict";

const lockboardContract =
  typeof module !== "undefined" && module.exports
    ? require("./evidence_report22_date_grid_migration_lockboard.js")
    : window.HakimiReport22DateGridMigrationLockboard;

const RESPONSE_SCHEMA =
  "strategy-correlation-cluster-temporal-date-grid-migration-http-candidate-response-v1";
const RESPONSE_FINGERPRINT =
  "20260822-report22-date-grid-migration-http-candidate-1";
const INTERFACE_STATUS = "UNREGISTERED_CANDIDATE";
const PUBLIC_SUMMARY_SCHEMA =
  "strategy-correlation-cluster-temporal-date-grid-migration-public-summary-v1";
const PUBLIC_SUMMARY_FINGERPRINT =
  "20260822-report22-date-grid-migration-projection-lock-1";

const ROOT_FIELDS = [
  "schema_version",
  "static_fingerprint",
  "interface_status",
  "state",
  "payload",
  "facts",
  "lineage",
  "transport",
  "authority",
  "blockers",
  "response_hash",
];
const FACT_FIELDS = [
  "request_contract_valid",
  "trusted_context_contract_valid",
  "migration_assessment_supplied",
  "source_projection_verified",
  "source_assessment_observed",
  "report22_evaluated",
  "payload_available",
  "transport_registered",
  "runtime_asset_accessed",
];
const LINEAGE_FIELDS = [
  "source_projection_schema_version",
  "source_projection_static_fingerprint",
  "request_documents_embedded",
  "migration_assessment_embedded",
  "verification_context_embedded",
  "report22_extension_embedded",
  "source_hashes_embedded",
];
const TRANSPORT_FIELDS = [
  "registered",
  "externally_callable",
  "method",
  "route",
  "runtime_reads",
  "runtime_mutations",
  "cache_reads",
  "cache_writes",
  "request_body_logging",
];
const AUTHORITY_FIELDS = [
  "descriptive_only",
  "route_registration_allowed",
  "migration_execution_allowed",
  "fresh_migration_allowed",
  "writer_allowed",
  "current_admission_allowed",
  "current_pointer_written",
  "paper_authorized",
  "live_order_allowed",
];

const SHA256_CONSTANTS = [
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
  0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
  0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
  0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
  0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
  0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
  0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
  0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
  0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
];

function hasExactKeys(value, fields) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const keys = Object.keys(value);
  return (
    keys.length === fields.length &&
    fields.every((field) => Object.prototype.hasOwnProperty.call(value, field))
  );
}

function canonicalJson(value) {
  if (value === null) return "null";
  if (typeof value === "string") return JSON.stringify(value);
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") {
    if (!Number.isSafeInteger(value)) throw new TypeError("canonical number invalid");
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map((item) => canonicalJson(item)).join(",")}]`;
  }
  if (typeof value === "object") {
    const prototype = Object.getPrototypeOf(value);
    if (prototype !== Object.prototype && prototype !== null) {
      throw new TypeError("canonical object invalid");
    }
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`)
      .join(",")}}`;
  }
  throw new TypeError("canonical value invalid");
}

function utf8Bytes(value) {
  if (typeof TextEncoder === "function") {
    return Array.from(new TextEncoder().encode(value));
  }
  if (typeof Buffer !== "undefined") {
    return Array.from(Buffer.from(value, "utf8"));
  }
  throw new TypeError("utf8 encoder unavailable");
}

function rotateRight(value, bits) {
  return (value >>> bits) | (value << (32 - bits));
}

function sha256Hex(value) {
  const bytes = utf8Bytes(value);
  const bitLength = bytes.length * 8;
  const highLength = Math.floor(bitLength / 0x100000000);
  const lowLength = bitLength >>> 0;
  bytes.push(0x80);
  while (bytes.length % 64 !== 56) bytes.push(0);
  for (let shift = 24; shift >= 0; shift -= 8) {
    bytes.push((highLength >>> shift) & 0xff);
  }
  for (let shift = 24; shift >= 0; shift -= 8) {
    bytes.push((lowLength >>> shift) & 0xff);
  }

  const hash = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
  ];
  const words = new Array(64);
  for (let offset = 0; offset < bytes.length; offset += 64) {
    for (let index = 0; index < 16; index += 1) {
      const start = offset + index * 4;
      words[index] = (
        (bytes[start] << 24) |
        (bytes[start + 1] << 16) |
        (bytes[start + 2] << 8) |
        bytes[start + 3]
      ) >>> 0;
    }
    for (let index = 16; index < 64; index += 1) {
      const small0 =
        rotateRight(words[index - 15], 7) ^
        rotateRight(words[index - 15], 18) ^
        (words[index - 15] >>> 3);
      const small1 =
        rotateRight(words[index - 2], 17) ^
        rotateRight(words[index - 2], 19) ^
        (words[index - 2] >>> 10);
      words[index] = (
        words[index - 16] + small0 + words[index - 7] + small1
      ) >>> 0;
    }

    let [a, b, c, d, e, f, g, h] = hash;
    for (let index = 0; index < 64; index += 1) {
      const sigma1 = rotateRight(e, 6) ^ rotateRight(e, 11) ^ rotateRight(e, 25);
      const choose = (e & f) ^ (~e & g);
      const temporary1 = (
        h + sigma1 + choose + SHA256_CONSTANTS[index] + words[index]
      ) >>> 0;
      const sigma0 = rotateRight(a, 2) ^ rotateRight(a, 13) ^ rotateRight(a, 22);
      const majority = (a & b) ^ (a & c) ^ (b & c);
      const temporary2 = (sigma0 + majority) >>> 0;
      h = g;
      g = f;
      f = e;
      e = (d + temporary1) >>> 0;
      d = c;
      c = b;
      b = a;
      a = (temporary1 + temporary2) >>> 0;
    }
    hash[0] = (hash[0] + a) >>> 0;
    hash[1] = (hash[1] + b) >>> 0;
    hash[2] = (hash[2] + c) >>> 0;
    hash[3] = (hash[3] + d) >>> 0;
    hash[4] = (hash[4] + e) >>> 0;
    hash[5] = (hash[5] + f) >>> 0;
    hash[6] = (hash[6] + g) >>> 0;
    hash[7] = (hash[7] + h) >>> 0;
  }
  return hash.map((word) => word.toString(16).padStart(8, "0")).join("");
}

function hasValidResponseHash(response) {
  if (!/^[0-9a-f]{64}$/.test(response.response_hash)) return false;
  const unsigned = {};
  for (const [key, value] of Object.entries(response)) {
    if (key !== "response_hash") unsigned[key] = value;
  }
  try {
    return sha256Hex(canonicalJson(unsigned)) === response.response_hash;
  } catch {
    return false;
  }
}

function expectedBlockers(state, decision) {
  const blockers = ["TRANSPORT_UNREGISTERED", "MIGRATION_EXECUTION_NOT_ALLOWED"];
  if (state === "NOT_SUPPLIED") {
    blockers.push("MIGRATION_ASSESSMENT_NOT_SUPPLIED");
  } else if (state === "UNKNOWN") {
    blockers.push("MIGRATION_ASSESSMENT_UNKNOWN");
  } else if (state === "PLAN_LISTED") {
    blockers.push("REPORT22_NOT_EVALUATED");
  } else if (decision === "BLOCK") {
    blockers.push("REPORT22_DECISION_BLOCK");
  }
  return blockers;
}

function exactArray(value, expected) {
  return Boolean(
    Array.isArray(value) &&
      value.length === expected.length &&
      expected.every((item, index) => value[index] === item),
  );
}

function verifyFacts(facts, state) {
  if (!hasExactKeys(facts, FACT_FIELDS)) return false;
  const supplied = state !== "NOT_SUPPLIED";
  const observed = state === "PLAN_LISTED" || state === "DRY_RUN_VERIFIED";
  return Boolean(
    facts.request_contract_valid === true &&
      facts.trusted_context_contract_valid === true &&
      facts.migration_assessment_supplied === supplied &&
      facts.source_projection_verified === true &&
      facts.source_assessment_observed === observed &&
      facts.report22_evaluated === (state === "DRY_RUN_VERIFIED") &&
      facts.payload_available === true &&
      facts.transport_registered === false &&
      facts.runtime_asset_accessed === false
  );
}

function verifyLineage(lineage) {
  return Boolean(
    hasExactKeys(lineage, LINEAGE_FIELDS) &&
      lineage.source_projection_schema_version === PUBLIC_SUMMARY_SCHEMA &&
      lineage.source_projection_static_fingerprint === PUBLIC_SUMMARY_FINGERPRINT &&
      lineage.request_documents_embedded === false &&
      lineage.migration_assessment_embedded === false &&
      lineage.verification_context_embedded === false &&
      lineage.report22_extension_embedded === false &&
      lineage.source_hashes_embedded === false
  );
}

function verifyTransport(transport) {
  return Boolean(
    hasExactKeys(transport, TRANSPORT_FIELDS) &&
      transport.registered === false &&
      transport.externally_callable === false &&
      transport.method === null &&
      transport.route === null &&
      transport.runtime_reads === false &&
      transport.runtime_mutations === false &&
      transport.cache_reads === false &&
      transport.cache_writes === false &&
      transport.request_body_logging === false
  );
}

function verifyAuthority(authority) {
  return Boolean(
    hasExactKeys(authority, AUTHORITY_FIELDS) &&
      authority.descriptive_only === true &&
      AUTHORITY_FIELDS
        .filter((field) => field !== "descriptive_only")
        .every((field) => authority[field] === false)
  );
}

function verifyReport22DateGridMigrationHttpCandidateResponse(response) {
  if (
    !hasExactKeys(response, ROOT_FIELDS) ||
    response.schema_version !== RESPONSE_SCHEMA ||
    response.static_fingerprint !== RESPONSE_FINGERPRINT ||
    response.interface_status !== INTERFACE_STATUS ||
    !["NOT_SUPPLIED", "UNKNOWN", "PLAN_LISTED", "DRY_RUN_VERIFIED"].includes(
      response.state,
    ) ||
    !response.payload ||
    typeof response.payload !== "object" ||
    Array.isArray(response.payload) ||
    response.payload.source?.state !== response.state ||
    !verifyFacts(response.facts, response.state) ||
    !verifyLineage(response.lineage) ||
    !verifyTransport(response.transport) ||
    !verifyAuthority(response.authority) ||
    !hasValidResponseHash(response)
  ) {
    return false;
  }
  const model = lockboardContract.presentReport22DateGridMigrationLockboard(
    response.payload,
  );
  if (model.variant !== "report22-date-grid" || model.state !== response.state) {
    return false;
  }
  return exactArray(
    response.blockers,
    expectedBlockers(response.state, model.decision),
  );
}

function bindingMetadata(verified) {
  return {
    status: verified ? "VERIFIED_HTTP_CANDIDATE" : "UNKNOWN",
    response_hash_verified: verified,
    payload_contract_verified: verified,
    route_registered: false,
    externally_callable: false,
    descriptive_only: true,
    current_admission_allowed: false,
    paper_authorized: false,
    live_order_allowed: false,
  };
}

function presentReport22DateGridMigrationFromHttpCandidate(response) {
  const verified = verifyReport22DateGridMigrationHttpCandidateResponse(response);
  const model = lockboardContract.presentReport22DateGridMigrationLockboard(
    verified ? response.payload : undefined,
  );
  return { ...model, httpBinding: bindingMetadata(verified) };
}

function renderReport22DateGridMigrationFromHttpCandidate(response, target) {
  const verified = verifyReport22DateGridMigrationHttpCandidateResponse(response);
  const model = lockboardContract.renderReport22DateGridMigrationLockboard(
    verified ? response.payload : undefined,
    target,
  );
  return { ...model, httpBinding: bindingMetadata(verified) };
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    INTERFACE_STATUS,
    RESPONSE_FINGERPRINT,
    RESPONSE_SCHEMA,
    presentReport22DateGridMigrationFromHttpCandidate,
    renderReport22DateGridMigrationFromHttpCandidate,
    verifyReport22DateGridMigrationHttpCandidateResponse,
  };
}

if (typeof window !== "undefined") {
  window.HakimiReport22DateGridMigrationHttpBinding = {
    presentReport22DateGridMigrationFromHttpCandidate,
    renderReport22DateGridMigrationFromHttpCandidate,
    verifyReport22DateGridMigrationHttpCandidateResponse,
  };
}
