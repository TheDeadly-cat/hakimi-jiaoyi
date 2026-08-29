"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const canonical = require("./strict_canonical_json_v1.js");
const card = require("./evidence_source_baseline_provider_conformance_card_v1.js");

function fixture() {
  return canonical.sealDocument(
    {
      schema_version: card.PAYLOAD_SCHEMA_VERSION,
      static_fingerprint: card.PAYLOAD_STATIC_FINGERPRINT,
      status: "BLOCKED",
      consumer_status: "PAYLOAD_BUILT_CONSUMER_UNREGISTERED",
      reason_code:
        "BOUNDED_PAYLOAD_BUILT_ASSETS_ROUTE_BROWSER_AND_MOUNT_ABSENT",
      source_envelope_hash: "1".repeat(64),
      consumer_preregistration_hash: card.CONSUMER_PREREGISTRATION_HASH,
      payload: {
        display_tone: "NEUTRAL",
        display_state:
          "SOURCE_BOUND_CONFORMANCE_NOT_RUN_PERMISSION_BLOCKED",
        ordered_stage_contract: [
          "SOURCE",
          "GAP",
          "MATURITY",
          "PERMISSION",
        ],
        axes: [
          {
            detail: "V1_IDENTITY_AND_SOURCE_TRUST_EXACT_V2_BINDING_BLOCKED",
            stage: "SOURCE",
            state: "BOUND",
          },
          {
            detail:
              "EXTERNAL_IDENTITY_TRUST_CONFORMANCE_ATOMICITY_DURABILITY_UNVERIFIED",
            stage: "GAP",
            state: "OPEN",
          },
          {
            detail: "14_REQUIRED_CASES_0_EXECUTED_0_PASSED",
            stage: "MATURITY",
            state: "PREREGISTERED_NOT_RUN",
          },
          {
            detail: "PROVIDER_HTTP_UI_CURRENT_PAPER_LIVE_DISABLED",
            stage: "PERMISSION",
            state: "BLOCKED",
          },
        ],
        summary: {
          source_document_count: 6,
          required_case_count: 14,
          executed_case_count: 0,
          passed_case_count: 0,
          open_gap_count: 7,
        },
        blockers: [
          "EXTERNAL_REGISTRY_IDENTITY_UNVERIFIED",
          "EXTERNAL_SOURCE_TRUST_UNVERIFIED",
          "PROVIDER_CONFORMANCE_CASES_NOT_RUN",
          "ATOMIC_COMPARE_AND_CONSUME_UNVERIFIED",
          "LINEARIZABILITY_UNVERIFIED",
          "DURABLE_COMMIT_UNVERIFIED",
          "AUTHENTICATED_CONSUMPTION_RECEIPT_NOT_ISSUED",
        ],
        permission: {
          state: "BLOCKED",
          provider_call_allowed: false,
          writer_allowed: false,
          route_registration_allowed: false,
          ui_consumer_mount_allowed: false,
          current_admission_allowed: false,
          paper_authorized: false,
          live_order_allowed: false,
        },
      },
      facts: {
        source_envelope_exactly_verified: true,
        preregistration_exactly_verified: true,
        bounded_payload_built: true,
        source_lineage_details_embedded: false,
        raw_source_documents_embedded: false,
        raw_identity_material_embedded: false,
        consumer_implementation_present: false,
        asset_manifest_complete: false,
        browser_executed: false,
        route_registered: false,
        ui_mounted: false,
        current_activated: false,
        runtime_mutations_performed: false,
        profitability_proven: false,
      },
      authority: {
        descriptive_only: true,
        asset_write_allowed: false,
        browser_execution_allowed: false,
        route_registration_allowed: false,
        ui_consumer_mount_allowed: false,
        current_admission_allowed: false,
        paper_authorized: false,
        live_order_allowed: false,
      },
    },
    "payload_candidate_hash"
  );
}

function reseal(mutator) {
  const value = structuredClone(fixture());
  delete value.payload_candidate_hash;
  mutator(value);
  return canonical.sealDocument(value, "payload_candidate_hash");
}

test("pins ADR0281 producer and strict canonical helper", () => {
  assert.equal(
    card.CONSUMER_PREREGISTRATION_IMPLEMENTATION_SHA256,
    "7ff64216e70dcedd43b86210cfac68b632c1eb7bc10a390bec9d4ffb619ac572"
  );
  assert.equal(
    card.STRICT_CANONICAL_JS_SHA256,
    "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39"
  );
});

test("accepts exact blocked ADR0281 payload candidate", () => {
  assert.equal(
    card.verifySourceBaselineProviderConformancePayloadCandidateV1(fixture()),
    true
  );
});

test("rejects non-record and invalid seal", () => {
  assert.equal(
    card.verifySourceBaselineProviderConformancePayloadCandidateV1(null),
    false
  );
  const value = fixture();
  value.payload_candidate_hash = "0".repeat(64);
  assert.equal(
    card.verifySourceBaselineProviderConformancePayloadCandidateV1(value),
    false
  );
});

test("view model stays neutral, blocked, and unmounted", () => {
  const view = card.buildSourceBaselineProviderConformanceViewModelV1(fixture());
  assert.equal(view.status, "BLOCKED");
  assert.equal(view.mount_state, "UNMOUNTED_CANDIDATE");
  assert.equal(view.tone, "NEUTRAL");
  assert.equal(canonical.verifySealedDocument(view, "view_model_hash"), true);
});

test("view model preserves source-gap-maturity-permission order", () => {
  const view = card.buildSourceBaselineProviderConformanceViewModelV1(fixture());
  assert.deepEqual(
    view.stages.map((stage) => stage.label),
    ["SOURCE", "GAP", "MATURITY", "PERMISSION"]
  );
  assert.deepEqual(
    view.stages.map((stage) => stage.state),
    ["BOUND", "OPEN", "PREREGISTERED_NOT_RUN", "BLOCKED"]
  );
});

test("bounded metrics distinguish required from executed and passed", () => {
  const view = card.buildSourceBaselineProviderConformanceViewModelV1(fixture());
  assert.deepEqual(
    view.metrics.map((metric) => [metric.label, metric.value, metric.state]),
    [
      ["SOURCE DOCUMENTS", "06", "BOUND"],
      ["REQUIRED CASES", "14", "PREREGISTERED"],
      ["EXECUTED", "00", "NOT RUN"],
      ["PASSED", "00", "NOT RUN"],
      ["OPEN GAPS", "07", "OPEN"],
    ]
  );
});

test("permission rail remains fully locked", () => {
  const view = card.buildSourceBaselineProviderConformanceViewModelV1(fixture());
  assert.deepEqual(view.permission_locks, [
    "PROVIDER CALL",
    "WRITER",
    "ROUTE",
    "UI MOUNT",
    "CURRENT",
    "PAPER",
    "LIVE",
  ]);
});

test("rendered card preserves ordered stages and bounded panels", () => {
  const html = card.renderSourceBaselineProviderConformanceCardV1(fixture());
  const positions = ["SOURCE", "GAP", "MATURITY", "PERMISSION"].map(
    (stage) => html.indexOf('data-stage="' + stage + '"')
  );
  assert.ok(positions.every((position) => position >= 0));
  assert.deepEqual(positions, [...positions].sort((left, right) => left - right));
  assert.ok(html.includes("OPEN GAP REGISTER"));
  assert.ok(html.includes("Bounded conformance counts"));
});

test("rendered copy contains no promotional or permission implication", () => {
  const html = card.renderSourceBaselineProviderConformanceCardV1(fixture());
  assert.equal(/\bREADY\b|profit|return|alpha|win rate/i.test(html), false);
  assert.equal(/data-status="ready"/i.test(html), false);
  assert.ok(html.includes("NOT RUN / BLOCKED"));
  assert.ok(html.includes("LIVE / LOCKED"));
});

test("resealed extra top-level field is rejected", () => {
  const value = reseal((document) => {
    document.synthetic_promotion = true;
  });
  assert.equal(
    card.verifySourceBaselineProviderConformancePayloadCandidateV1(value),
    false
  );
});

test("resealed status or tone promotion is rejected", () => {
  const status = reseal((document) => {
    document.status = "PASS";
  });
  const tone = reseal((document) => {
    document.payload.display_tone = "POSITIVE";
  });
  assert.equal(
    card.verifySourceBaselineProviderConformancePayloadCandidateV1(status),
    false
  );
  assert.equal(
    card.verifySourceBaselineProviderConformancePayloadCandidateV1(tone),
    false
  );
});

test("resealed stage reorder is rejected", () => {
  const value = reseal((document) => {
    document.payload.axes.reverse();
    document.payload.ordered_stage_contract.reverse();
  });
  assert.equal(
    card.verifySourceBaselineProviderConformancePayloadCandidateV1(value),
    false
  );
});

test("resealed execution or pass-count promotion is rejected", () => {
  const value = reseal((document) => {
    document.payload.summary.executed_case_count = 14;
    document.payload.summary.passed_case_count = 14;
  });
  assert.equal(
    card.verifySourceBaselineProviderConformancePayloadCandidateV1(value),
    false
  );
});

test("resealed permission promotion is rejected", () => {
  const value = reseal((document) => {
    document.payload.permission.ui_consumer_mount_allowed = true;
    document.authority.ui_consumer_mount_allowed = true;
  });
  assert.equal(
    card.verifySourceBaselineProviderConformancePayloadCandidateV1(value),
    false
  );
});

test("resealed blocker omission is rejected", () => {
  const value = reseal((document) => {
    document.payload.blockers.pop();
    document.payload.summary.open_gap_count = 6;
  });
  assert.equal(
    card.verifySourceBaselineProviderConformancePayloadCandidateV1(value),
    false
  );
});

test("one-time snapshot blocks second-read provenance substitution", () => {
  const value = fixture();
  let reads = 0;
  const adversarial = new Proxy(value, {
    get(target, property, receiver) {
      if (property === "source_envelope_hash") {
        reads += 1;
        if (reads >= 2) return "f".repeat(64);
      }
      return Reflect.get(target, property, receiver);
    },
  });
  const view =
    card.buildSourceBaselineProviderConformanceViewModelV1(adversarial);
  assert.equal(reads, 1);
  assert.equal(view.provenance.source_envelope_hash, "111111111111...111111");
});

test("throwing getter fails closed", () => {
  const value = fixture();
  Object.defineProperty(value, "source_envelope_hash", {
    enumerable: true,
    get() {
      throw new Error("synthetic getter failure");
    },
  });
  assert.equal(
    card.verifySourceBaselineProviderConformancePayloadCandidateV1(value),
    false
  );
  assert.throws(
    () => card.buildSourceBaselineProviderConformanceViewModelV1(value),
    /payload candidate is invalid/
  );
});

test("consumer does not mutate the producer payload", () => {
  const value = fixture();
  const before = canonical.strictCanonicalStringify(value);
  card.buildSourceBaselineProviderConformanceViewModelV1(value);
  card.renderSourceBaselineProviderConformanceCardV1(value);
  assert.equal(canonical.strictCanonicalStringify(value), before);
});

test("view model and HTML are deterministic", () => {
  const value = fixture();
  assert.deepEqual(
    card.buildSourceBaselineProviderConformanceViewModelV1(value),
    card.buildSourceBaselineProviderConformanceViewModelV1(value)
  );
  assert.equal(
    card.renderSourceBaselineProviderConformanceCardV1(value),
    card.renderSourceBaselineProviderConformanceCardV1(value)
  );
});
