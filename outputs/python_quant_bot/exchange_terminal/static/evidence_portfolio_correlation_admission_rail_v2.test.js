"use strict";

const assert = require("node:assert/strict");
const childProcess = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const strictCanonical = require("./strict_canonical_json_v1.js");
const rail = require("./evidence_portfolio_correlation_admission_rail_v2.js");

const PROJECT_ROOT = path.resolve(__dirname, "../..");
const PYTHON_FIXTURE_SCRIPT = String.raw`
import json
from exchange_terminal.services.portfolio_correlation_admission_v2 import build_portfolio_correlation_admission_v2
from exchange_terminal.services.portfolio_correlation_admission_v2_consumer_preregistration_v1 import build_portfolio_correlation_admission_v2_consumer_binding_v1
from tests.test_portfolio_correlation_admission_v2_in_memory_delivery_v1 import PortfolioCorrelationAdmissionV2InMemoryDeliveryV1Tests
case = PortfolioCorrelationAdmissionV2InMemoryDeliveryV1Tests(methodName="runTest")
case.setUp()
_, _, common_block = case._block_fixture()
high_evidence = case.fixture._evidence(correlation=0.95)
high_candidate = build_portfolio_correlation_admission_v2(**high_evidence)
high_binding = build_portfolio_correlation_admission_v2_consumer_binding_v1(case.registration, high_candidate, **high_evidence)
high_envelope = case._envelope(binding=high_binding, candidate=high_candidate, evidence=high_evidence)
print(json.dumps({"clear": case.envelope, "common_block": common_block, "v1_block": high_envelope}, separators=(",", ":")))
`;
const bundle = JSON.parse(childProcess.execFileSync(
  process.env.PYTHON || "python",
  ["-c", PYTHON_FIXTURE_SCRIPT],
  { cwd: PROJECT_ROOT, encoding: "utf8", maxBuffer: 2 * 1024 * 1024 }
));

test("exact local pass builds a bounded common-universe view", () => {
  const view = rail.buildPortfolioCorrelationAdmissionRailViewModelV2(bundle.clear);
  assert.equal(view.contract_state, "KNOWN");
  assert.equal(view.status_label, "LOCAL CLEAR");
  assert.equal(view.handshake.report.state, "PASS");
  assert.equal(view.handshake.common.state, "PASS");
  assert.equal(view.handshake.correlation.state, "PASS");
  assert.equal(view.stages[3].state, "UNAUTHORIZED");
});

test("common-universe mismatch is the visible handshake stop", () => {
  const view = rail.buildPortfolioCorrelationAdmissionRailViewModelV2(bundle.common_block);
  assert.equal(view.status_label, "LOCAL BLOCK");
  assert.equal(view.title, "The evidence sets do not meet");
  assert.equal(view.handshake.report.state, "PASS");
  assert.equal(view.handshake.correlation.state, "PASS");
  assert.equal(view.handshake.common.state, "BLOCK");
  assert.equal(view.metrics[1].value, "NOT_EVALUATED");
  assert.equal(view.stages[1].detail, "COMMON_UNIVERSE");
});

test("matching universe with v1 block preserves downstream detail", () => {
  const view = rail.buildPortfolioCorrelationAdmissionRailViewModelV2(bundle.v1_block);
  assert.equal(view.handshake.common.state, "PASS");
  assert.equal(view.status_label, "LOCAL BLOCK");
  assert.equal(view.title, "The universe meets; admission still stops");
  assert.match(view.summary, /complete link/);
  const v1 = view.tiers.find((tier) => tier.tier === "V1_ADMISSION");
  assert.equal(v1.state, "BLOCK");
  assert.equal(v1.detail, "BLOCK / COMPLETE_LINK");
});

test("unknown envelope exposes no metrics and preserves permission lock", () => {
  const view = rail.buildPortfolioCorrelationAdmissionRailViewModelV2({});
  assert.equal(view.contract_state, "UNKNOWN");
  assert.deepEqual(view.metrics, []);
  assert.equal(view.handshake.common.state, "NOT_EVALUATED");
  assert.equal(view.stages[3].state, "UNAUTHORIZED");
  assert.equal(Object.isFrozen(view), true);
});

test("renderer carries the handshake and ordered neutral governance stages", () => {
  const markup = rail.renderPortfolioCorrelationAdmissionRailV2(bundle.clear);
  assert.match(markup, /Common universe handshake/);
  assert.match(markup, /REPORT UNIVERSE/);
  assert.match(markup, /COMMON UNIVERSE/);
  assert.match(markup, /CORRELATION PREREGISTRATION/);
  const stagesStart = markup.indexOf(
    '<ol class="hakimi-correlation-v2-rail__stages"'
  );
  const stagesEnd = markup.indexOf("</ol>", stagesStart);
  const stagesMarkup = markup.slice(stagesStart, stagesEnd);
  const positions = rail.STAGE_ORDER.map(
    (stage) => stagesMarkup.indexOf(`>${stage}<`)
  );
  assert.equal(positions.every((value) => value >= 0), true);
  assert.equal(positions.every((value, index) => index === 0 || value > positions[index - 1]), true);
  assert.doesNotMatch(markup, /\bREADY\b/i);
});

test("delivery payload identity and raw symbols never enter markup", () => {
  const markup = rail.renderPortfolioCorrelationAdmissionRailV2(bundle.clear);
  assert.doesNotMatch(markup, /strategy-1|variant-1|AAA|BBB/);
  assert.match(markup, /Research display only/);
});

test("forged blocker text fails to unknown and cannot inject markup", () => {
  const altered = structuredClone(bundle.common_block);
  delete altered.presentation_payload.presentation_payload_hash;
  altered.presentation_payload.blockers = ['<script>alert("x")</script>'];
  altered.presentation_payload = strictCanonical.sealDocument(
    altered.presentation_payload,
    "presentation_payload_hash"
  );
  delete altered.delivery_envelope_hash;
  const resealed = strictCanonical.sealDocument(altered, "delivery_envelope_hash");
  const markup = rail.renderPortfolioCorrelationAdmissionRailV2(resealed);
  assert.doesNotMatch(markup, /<script>/i);
  assert.match(markup, /SOURCE UNKNOWN/);
});

test("public API and ordered constants stay frozen", () => {
  assert.equal(Object.isFrozen(rail), true);
  assert.equal(Object.isFrozen(rail.STAGE_ORDER), true);
  assert.equal(Object.isFrozen(rail.TIER_ORDER), true);
  assert.deepEqual(rail.STAGE_ORDER, ["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
  assert.equal(rail.TIER_ORDER.includes("COMMON_UNIVERSE"), true);
});

test("isolated CSS encodes the cartographic handshake and motion guard", () => {
  const css = fs.readFileSync(
    path.join(__dirname, "evidence_portfolio_correlation_admission_rail_v2.css"),
    "utf8"
  );
  assert.match(css, /\.hakimi-correlation-v2-rail\s*\{/);
  assert.match(css, /--v2-tide:\s*#0d6670/);
  assert.match(css, /__handshake-gate/);
  assert.match(css, /clip-path:\s*polygon/);
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
  assert.match(css, /max-width:\s*520px/);
  assert.doesNotMatch(css, /(^|\n)\s*(?:body|html|:root)\s*\{/);
});

test("production rail has no DOM, network, storage, or runtime loader API", () => {
  const source = fs.readFileSync(
    path.join(__dirname, "evidence_portfolio_correlation_admission_rail_v2.js"),
    "utf8"
  );
  assert.equal(source.includes("globalThis.document"), false);
  assert.equal(source.includes("innerHTML"), false);
  assert.equal(source.includes("fetch("), false);
  assert.equal(source.includes("XMLHttpRequest"), false);
  assert.equal(source.includes("localStorage"), false);
  assert.equal(source.includes("sessionStorage"), false);
  assert.equal(/\bREADY\b/i.test(source), false);
});
