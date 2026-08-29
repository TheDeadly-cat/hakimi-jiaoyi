"use strict";

const assert = require("node:assert/strict");
const childProcess = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const PROJECT_ROOT = path.resolve(__dirname, "../..");
const strictCanonical = require("./strict_canonical_json_v1.js");
const rail = require("./evidence_portfolio_correlation_admission_rail_v1.js");
const delivery = require("./evidence_static_presentation_in_memory_delivery_v1.js");
const subject = require("./evidence_static_presentation_unmounted_render_review_v1.js");

const PYTHON_FIXTURE_SCRIPT = String.raw`
import copy
import json
from tests import test_static_presentation_in_memory_delivery_v1 as delivery_tests
from exchange_terminal.services.static_presentation_host_patch_preregistration_v1 import build_static_presentation_host_patch_preregistration_v1

case = delivery_tests.StaticPresentationInMemoryDeliveryV1Tests(methodName="runTest")
clear = case._build(case._fixture(0.1))
blocked = case._build(case._fixture(0.95))
unknown_fixture = case._fixture(0.1)
unknown_fixture["registration_document"] = copy.deepcopy(
    unknown_fixture["registration_document"]
)
unknown_fixture["registration_document"]["authority"]["paper_authorized"] = True
unknown = case._build(unknown_fixture)
registration = build_static_presentation_host_patch_preregistration_v1()
fragment = registration["patch_plan"]["operations"][-1]["fragment"]
assert clear["source_status"] == "PASS"
assert blocked["source_status"] == "BLOCK"
assert unknown["status"] == "UNKNOWN"
print(json.dumps({
    "app_fragment": fragment,
    "review_context": {
        "patch_preregistration_hash": registration["patch_preregistration_hash"],
        "patch_plan_hash": registration["patch_plan_hash"],
        "host_app_fragment_sha256": registration["patch_plan"]["operations"][-1]["fragment_sha256"],
    },
    "clear": clear,
    "blocked": blocked,
    "unknown": unknown,
}, separators=(",", ":")))
`;

const bundle = JSON.parse(childProcess.execFileSync(
  process.env.PYTHON || "python",
  ["-c", PYTHON_FIXTURE_SCRIPT],
  {
    cwd: PROJECT_ROOT,
    encoding: "utf8",
    maxBuffer: 2 * 1024 * 1024,
  }
));

assert.equal(
  strictCanonical.sha256Hex(bundle.app_fragment),
  subject.HOST_APP_FRAGMENT_SHA256
);
globalThis.HakimiStrictCanonicalJsonV1 = strictCanonical;
globalThis.HakimiPortfolioCorrelationAdmissionRailV1 = rail;
globalThis.HakimiStaticPresentationInMemoryDeliveryV1 = delivery;
new Function(bundle.app_fragment)();
const hostApi = globalThis.HakimiPortfolioCorrelationAdmissionRailHostV1;

function build(envelope = bundle.clear, api = hostApi, context = bundle.review_context) {
  return subject.buildStaticPresentationUnmountedRenderReviewReceiptV1(
    api,
    envelope,
    context
  );
}

test("exact clear envelope yields a blocked no-DOM LOCAL CLEAR review", () => {
  const receipt = build(bundle.clear);
  assert.equal(receipt.status, "BLOCKED");
  assert.equal(
    receipt.review_state,
    "EXACT_UNMOUNTED_RENDER_CANDIDATE_REVIEWED_NO_DOM"
  );
  assert.equal(receipt.source_status, "PASS");
  assert.equal(receipt.presentation_summary.status_label, "LOCAL CLEAR");
  assert.deepEqual(
    receipt.presentation_summary.stage_order,
    ["SOURCE", "GAP", "MATURITY", "PERMISSION"]
  );
  assert.equal(receipt.facts.dom_mounted, false);
});

test("exact high-correlation block remains visible and unauthorized", () => {
  const receipt = build(bundle.blocked);
  assert.equal(receipt.status, "BLOCKED");
  assert.equal(receipt.source_status, "BLOCK");
  assert.equal(receipt.presentation_summary.status_label, "LOCAL BLOCK");
  assert.equal(receipt.authority.current_admission_allowed, false);
  assert.equal(receipt.authority.paper_authorized, false);
  assert.equal(receipt.authority.live_order_allowed, false);
});

test("exact unknown envelope stays unknown without partial markup evidence", () => {
  const receipt = build(bundle.unknown);
  assert.equal(receipt.status, "UNKNOWN");
  assert.equal(receipt.reason_code, "ADMISSION_CANDIDATE_UNKNOWN");
  assert.equal(receipt.markup_sha256, null);
  assert.equal(receipt.markup_length, null);
  assert.equal(receipt.presentation_summary, null);
  assert.equal(receipt.facts.host_render_candidate_exactly_verified, true);
});

test("invalid envelope fails closed", () => {
  const receipt = build({});
  assert.equal(receipt.status, "UNKNOWN");
  assert.equal(receipt.reason_code, "DELIVERY_ENVELOPE_NOT_EXACT");
  assert.equal(receipt.facts.delivery_envelope_exactly_verified, false);
});

test("context hash drift prevents host invocation", () => {
  const context = { ...bundle.review_context, patch_plan_hash: "f".repeat(64) };
  let invoked = false;
  const api = {
    buildPortfolioCorrelationAdmissionRailHostRenderCandidateV1() {
      invoked = true;
      return null;
    },
  };
  const receipt = build(bundle.clear, api, context);
  assert.equal(receipt.status, "UNKNOWN");
  assert.equal(receipt.reason_code, "REVIEW_CONTEXT_NOT_EXACT");
  assert.equal(invoked, false);
});

test("host candidate markup substitution is rejected", () => {
  const api = {
    buildPortfolioCorrelationAdmissionRailHostRenderCandidateV1(envelope) {
      const candidate = hostApi
        .buildPortfolioCorrelationAdmissionRailHostRenderCandidateV1(envelope);
      return { ...candidate, markup: `${candidate.markup}<b>forged</b>` };
    },
  };
  const receipt = build(bundle.clear, api);
  assert.equal(receipt.status, "UNKNOWN");
  assert.equal(receipt.reason_code, "HOST_RENDER_CANDIDATE_NOT_EXACT");
});

test("host API exception is contained as unknown", () => {
  const api = {
    buildPortfolioCorrelationAdmissionRailHostRenderCandidateV1() {
      throw new Error("forged");
    },
  };
  const receipt = build(bundle.clear, api);
  assert.equal(receipt.status, "UNKNOWN");
  assert.equal(receipt.reason_code, "HOST_RENDER_API_EXCEPTION");
});

test("review receipt exact verifier accepts rebuild and rejects promotion", () => {
  const receipt = build(bundle.clear);
  assert.equal(
    subject.verifyStaticPresentationUnmountedRenderReviewReceiptV1(
      receipt,
      hostApi,
      bundle.clear,
      bundle.review_context
    ),
    true
  );
  const promoted = JSON.parse(JSON.stringify(receipt));
  promoted.authority.dom_mount_allowed = true;
  delete promoted.review_receipt_hash;
  const resealed = strictCanonical.sealDocument(promoted, "review_receipt_hash");
  assert.equal(
    subject.verifyStaticPresentationUnmountedRenderReviewReceiptV1(
      resealed,
      hostApi,
      bundle.clear,
      bundle.review_context
    ),
    false
  );
});

test("receipt stores markup hash only and contains no READY wording", () => {
  const receipt = build(bundle.clear);
  const serialized = JSON.stringify(receipt);
  assert.equal(serialized.includes("<section"), false);
  assert.match(receipt.markup_sha256, /^[0-9a-f]{64}$/);
  assert.equal(/\bREADY\b/i.test(serialized), false);
  assert.equal(receipt.facts.raw_markup_embedded, false);
});

test("local behavior review never claims external independence", () => {
  const receipt = build(bundle.clear);
  assert.equal(receipt.facts.local_unmounted_behavior_reviewed, true);
  assert.equal(receipt.facts.external_independent_review_complete, false);
  assert.equal(
    receipt.blockers.includes("EXTERNAL_INDEPENDENT_REVIEW_NOT_COMPLETED"),
    true
  );
  assert.equal(
    receipt.authority.external_independent_review_completion_allowed,
    false
  );
});

test("review is deterministic and production source has no DOM or network API", () => {
  assert.deepEqual(build(bundle.clear), build(bundle.clear));
  const source = fs.readFileSync(
    path.join(__dirname, "evidence_static_presentation_unmounted_render_review_v1.js"),
    "utf8"
  );
  assert.equal(source.includes("document."), false);
  assert.equal(source.includes("innerHTML"), false);
  assert.equal(source.includes("fetch("), false);
  assert.equal(source.includes("XMLHttpRequest"), false);
  assert.equal(source.includes("eval("), false);
});
