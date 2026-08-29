"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { sealDocument } = require("./strict_canonical_json_v1.js");
const {
  buildProviderIdentityPresentationModelV1,
  constants,
  createProviderIdentityEvidenceCardV1,
} = require("./provider_identity_evidence_card_v1.js");

const tests = [];
function test(name, fn) {
  tests.push({ name, fn });
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function axes(unknown = false) {
  const states = unknown
    ? ["UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN"]
    : [
        "CRYPTOGRAPHIC_PROOF_BOUND",
        "EXTERNAL_TRUST_TIME_REPLAY_UNPROVEN",
        "DETACHED_CANDIDATE",
        "LOCKED",
      ];
  const headlines = [
    "Cryptographic assertion bound",
    "Trust root remains external",
    "Verification candidate only",
    "No permission granted",
  ];
  return ["SOURCE", "GAP", "MATURITY", "PERMISSION"].map((axis, index) => ({
    axis,
    detail: unknown
      ? "The sealed source contract did not verify for presentation."
      : `Neutral detail for ${axis.toLowerCase()} evidence.`,
    headline: unknown ? "Evidence unavailable" : headlines[index],
    signal: unknown ? "UNKNOWN" : ["SIGNATURE + MEMBERSHIP", "ROOT / TIME / REPLAY", "UNMOUNTED CANDIDATE", "NO ADMISSION"][index],
    state: states[index],
  }));
}

function makeEnvelope() {
  return sealDocument(
    {
      authority: {
        current_admission_allowed: false,
        current_pointer_written: false,
        descriptive_only: true,
        live_order_allowed: false,
        paper_authorized: false,
        profitability_claim_allowed: false,
        provider_identity_admission_allowed: false,
      },
      axes: axes(),
      axis_order: ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
      blockers: [
        "IDENTITY_REGISTRY_TRUST_ROOT_NOT_EXTERNALLY_ATTESTED",
        "IDENTITY_ASSERTION_REGISTRATION_TIME_NOT_EXTERNALLY_ATTESTED",
        "IDENTITY_ASSERTION_REPLAY_REGISTRY_NOT_CHECKED",
        "PROVIDER_IDENTITY_NOT_EXTERNALLY_ESTABLISHED",
        "LONG_HORIZON_EVALUATION_NOT_ACTIVATED",
      ],
      display_state: constants.DISPLAY_STATE,
      facts: {
        cryptographic_identity_assertion_verified: true,
        external_identity_registry_authenticity_proven: false,
        external_registration_time_verified: false,
        provider_identity_verified: false,
        replay_registry_checked: false,
        result_available: false,
        source_assertion_verification_verified: true,
      },
      lineage: {
        assertion_content_sha256: "1".repeat(64),
        assertion_hash: "2".repeat(64),
        identity_registry_snapshot_sha256: "3".repeat(64),
        identity_registry_trust_root_sha256: "4".repeat(64),
        membership_proof_hash: "5".repeat(64),
        provider_identity_document_sha256: "6".repeat(64),
        provider_receipt_trust_root_sha256: "7".repeat(64),
        source_provider_identity_registration_hash: "8".repeat(64),
        source_verification_hash: "9".repeat(64),
      },
      presentation_status: "UNMOUNTED_CANDIDATE",
      schema_version: constants.ENVELOPE_SCHEMA,
      source_schema_version: constants.SOURCE_SCHEMA,
      source_state: "VERIFIED",
      source_static_fingerprint: constants.SOURCE_FINGERPRINT,
      source_verification_state: constants.SOURCE_STATE,
      static_fingerprint: constants.ENVELOPE_FINGERPRINT,
      summary: {
        asserted_at_utc: "2026-09-17T00:00:00Z",
        assertion_id: "IDENTITY-ASSERTION-0001",
        identity_registry_id: "EXTERNAL-IDENTITY-REGISTRY-1",
        identity_registry_snapshot_id: "SNAPSHOT-20260915-1",
        membership_leaf_index: 0,
        membership_proof_count: 2,
        membership_tree_size: 4,
        provider_id: "APPEND-ONLY-PROVIDER-1",
        provider_subject_id: "PROVIDER-SUBJECT-1",
        valid_until_utc: "2026-10-31T23:59:59Z",
      },
    },
    "presentation_hash"
  );
}

function reseal(envelope) {
  const copy = clone(envelope);
  delete copy.presentation_hash;
  return sealDocument(copy, "presentation_hash");
}

function makeUnknownEnvelope(mode) {
  const envelope = makeEnvelope();
  envelope.axes = axes(true);
  envelope.blockers = ["SOURCE_VERIFICATION_NOT_VERIFIED"];
  envelope.display_state = "UNKNOWN";
  Object.keys(envelope.facts).forEach((key) => {
    envelope.facts[key] = false;
  });
  if (mode === "partial") {
    envelope.lineage.source_verification_hash = null;
  }
  if (mode === "sparse") {
    Object.keys(envelope.lineage).forEach((key) => {
      envelope.lineage[key] = null;
    });
    Object.keys(envelope.summary).forEach((key) => {
      envelope.summary[key] = null;
    });
    envelope.source_schema_version = null;
    envelope.source_state = "UNKNOWN";
    envelope.source_static_fingerprint = null;
    envelope.source_verification_state = null;
  }
  return reseal(envelope);
}

class FakeNode {
  constructor(tagName) {
    this.tagName = tagName.toUpperCase();
    this.children = [];
    this.attributes = {};
    this.className = "";
    this._text = "";
  }
  append(...nodes) {
    this.children.push(...nodes);
  }
  setAttribute(name, value) {
    this.attributes[name] = String(value);
  }
  set textContent(value) {
    this._text = String(value);
  }
  get textContent() {
    return this._text + this.children.map((child) => child.textContent).join("");
  }
}

class FakeDocument {
  constructor() {
    this.created = [];
  }
  createElement(tagName) {
    const node = new FakeNode(tagName);
    this.created.push(node);
    return node;
  }
}

test("exports exact envelope identities", () => {
  assert.equal(constants.ENVELOPE_SCHEMA.endsWith("presentation-envelope-v1"), true);
  assert.equal(constants.AXIS_ORDER.join("/"), "SOURCE/GAP/MATURITY/PERMISSION");
});

test("builds positive neutral model", () => {
  const model = buildProviderIdentityPresentationModelV1(makeEnvelope());
  assert.equal(model.displayState, constants.DISPLAY_STATE);
  assert.equal(model.axes.length, 4);
  assert.equal(model.statusLabel, "TRUST GAP RECORDED");
});

test("rejects presentation hash tamper", () => {
  const envelope = makeEnvelope();
  envelope.summary.membership_leaf_index = 1;
  assert.throws(() => buildProviderIdentityPresentationModelV1(envelope));
});

test("rejects extra top-level fields", () => {
  const envelope = reseal({ ...makeEnvelope(), ready: true });
  assert.throws(() => buildProviderIdentityPresentationModelV1(envelope));
});

test("rejects axis reorder", () => {
  const envelope = makeEnvelope();
  envelope.axes.reverse();
  assert.throws(() => buildProviderIdentityPresentationModelV1(reseal(envelope)));
});

test("rejects axis state drift", () => {
  const envelope = makeEnvelope();
  envelope.axes[0].state = "IDENTITY_VERIFIED";
  assert.throws(() => buildProviderIdentityPresentationModelV1(reseal(envelope)));
});

test("rejects blocker order drift", () => {
  const envelope = makeEnvelope();
  envelope.blockers.reverse();
  assert.throws(() => buildProviderIdentityPresentationModelV1(reseal(envelope)));
});

test("rejects source schema drift", () => {
  const envelope = makeEnvelope();
  envelope.source_schema_version = "legacy";
  assert.throws(() => buildProviderIdentityPresentationModelV1(reseal(envelope)));
});

test("rejects proof count arithmetic drift", () => {
  const envelope = makeEnvelope();
  envelope.summary.membership_proof_count = 1;
  assert.throws(() => buildProviderIdentityPresentationModelV1(reseal(envelope)));
});

test("rejects leaf index outside tree", () => {
  const envelope = makeEnvelope();
  envelope.summary.membership_leaf_index = 4;
  assert.throws(() => buildProviderIdentityPresentationModelV1(reseal(envelope)));
});

test("rejects permission drift", () => {
  const envelope = makeEnvelope();
  envelope.authority.current_admission_allowed = true;
  assert.throws(() => buildProviderIdentityPresentationModelV1(reseal(envelope)));
});

test("rejects provider identity promotion", () => {
  const envelope = makeEnvelope();
  envelope.facts.provider_identity_verified = true;
  assert.throws(() => buildProviderIdentityPresentationModelV1(reseal(envelope)));
});

test("rejects external trust promotion", () => {
  const envelope = makeEnvelope();
  envelope.facts.external_identity_registry_authenticity_proven = true;
  assert.throws(() => buildProviderIdentityPresentationModelV1(reseal(envelope)));
});

test("rejects malformed lineage hash", () => {
  const envelope = makeEnvelope();
  envelope.lineage.membership_proof_hash = "A".repeat(64);
  assert.throws(() => buildProviderIdentityPresentationModelV1(reseal(envelope)));
});

test("rejects promotional copy", () => {
  const envelope = makeEnvelope();
  envelope.axes[2].headline = "READY";
  assert.throws(() => buildProviderIdentityPresentationModelV1(reseal(envelope)));
});

test("accepts sealed unknown envelope", () => {
  const envelope = makeEnvelope();
  envelope.axes = axes(true);
  envelope.blockers = ["SOURCE_VERIFICATION_NOT_VERIFIED"];
  envelope.display_state = "UNKNOWN";
  Object.keys(envelope.facts).forEach((key) => {
    envelope.facts[key] = false;
  });
  envelope.source_state = "UNKNOWN";
  envelope.source_verification_state = "UNKNOWN";
  const model = buildProviderIdentityPresentationModelV1(reseal(envelope));
  assert.equal(model.statusLabel, "EVIDENCE UNKNOWN");
});

test("accepts unknown envelope with partial lineage", () => {
  const model = buildProviderIdentityPresentationModelV1(makeUnknownEnvelope("partial"));
  assert.equal(model.statusLabel, "EVIDENCE UNKNOWN");
  assert.equal(model.proof.known, true);
});

test("renders sparse unknown without null or negative arithmetic", () => {
  const document = new FakeDocument();
  const rendered = createProviderIdentityEvidenceCardV1(makeUnknownEnvelope("sparse"), { document });
  assert.equal(rendered.model.proof.known, false);
  assert.match(rendered.element.textContent, /UNKNOWN/);
  assert.doesNotMatch(rendered.element.textContent, /\bnull\b|-1/);
});

test("rejects partially populated unknown proof aggregates", () => {
  const envelope = makeUnknownEnvelope("sparse");
  envelope.summary.membership_tree_size = 4;
  assert.throws(() => buildProviderIdentityPresentationModelV1(reseal(envelope)));
});

test("creates detached semantic card", () => {
  const document = new FakeDocument();
  const rendered = createProviderIdentityEvidenceCardV1(makeEnvelope(), { document });
  assert.equal(rendered.element.tagName, "SECTION");
  assert.equal(rendered.element.className, "pirl1-card");
  assert.equal(rendered.element.attributes["aria-label"], "Provider identity evidence dossier");
});

test("renderer uses text nodes for source values", () => {
  const document = new FakeDocument();
  const rendered = createProviderIdentityEvidenceCardV1(makeEnvelope(), { document });
  assert.match(rendered.element.textContent, /APPEND-ONLY-PROVIDER-1/);
  assert.match(rendered.element.textContent, /No provider identity admission/);
});

test("renderer emits no button", () => {
  const document = new FakeDocument();
  createProviderIdentityEvidenceCardV1(makeEnvelope(), { document });
  assert.equal(document.created.some((node) => node.tagName === "BUTTON"), false);
});

test("renderer requires only createElement", () => {
  const document = { createElement: (tag) => new FakeNode(tag) };
  assert.doesNotThrow(() => createProviderIdentityEvidenceCardV1(makeEnvelope(), { document }));
});

test("source has no network page query or mount APIs", () => {
  const source = fs.readFileSync(path.join(__dirname, "provider_identity_evidence_card_v1.js"), "utf8");
  ["fetch(", "XMLHttpRequest", "querySelector", "getElementById", "addEventListener", "inner" + "HTML"].forEach((token) => {
    assert.equal(source.includes(token), false, token);
  });
});

test("browser script branch exposes helper card and model globals", () => {
  const sandbox = {
    TextDecoder,
    TextEncoder,
    clearTimeout,
    console,
    crypto: crypto.webcrypto,
    setTimeout,
  };
  sandbox.globalThis = sandbox;
  sandbox.self = sandbox;
  sandbox.window = sandbox;
  vm.createContext(sandbox);
  ["strict_canonical_json_v1.js", "provider_identity_evidence_card_v1.js"].forEach((file) => {
    vm.runInContext(fs.readFileSync(path.join(__dirname, file), "utf8"), sandbox, {
      filename: file,
    });
  });
  assert.equal(typeof sandbox.HakimiStrictCanonicalJsonV1, "object");
  assert.equal(typeof sandbox.ProviderIdentityEvidenceCardV1, "object");
  sandbox.envelopeJson = JSON.stringify(makeEnvelope());
  const displayState = vm.runInContext(
    "ProviderIdentityEvidenceCardV1.buildProviderIdentityPresentationModelV1(JSON.parse(envelopeJson)).displayState",
    sandbox
  );
  assert.equal(displayState, constants.DISPLAY_STATE);
});

test("css is scoped and visually layered", () => {
  const css = fs.readFileSync(path.join(__dirname, "provider_identity_evidence_card_v1.css"), "utf8");
  assert.match(css, /\.pirl1-card/);
  assert.match(css, /radial-gradient/);
  assert.match(css, /repeating-linear-gradient/);
  assert.doesNotMatch(css, /(^|\n)\s*(body|html|button)\s*\{/);
});

test("css has desktop and mobile breakpoints", () => {
  const css = fs.readFileSync(path.join(__dirname, "provider_identity_evidence_card_v1.css"), "utf8");
  assert.match(css, /max-width:\s*900px/);
  assert.match(css, /max-width:\s*560px/);
});

test("css honors reduced motion", () => {
  const css = fs.readFileSync(path.join(__dirname, "provider_identity_evidence_card_v1.css"), "utf8");
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
  assert.match(css, /animation:\s*none/);
});

test("model construction is deterministic", () => {
  const envelope = makeEnvelope();
  assert.deepEqual(
    buildProviderIdentityPresentationModelV1(envelope),
    buildProviderIdentityPresentationModelV1(envelope)
  );
});

let passed = 0;
for (const item of tests) {
  try {
    item.fn();
    passed += 1;
  } catch (error) {
    console.error(`FAIL ${item.name}`);
    throw error;
  }
}
console.log(`PROVIDER_IDENTITY_EVIDENCE_CARD_V1 PASS ${passed}/${tests.length}`);
