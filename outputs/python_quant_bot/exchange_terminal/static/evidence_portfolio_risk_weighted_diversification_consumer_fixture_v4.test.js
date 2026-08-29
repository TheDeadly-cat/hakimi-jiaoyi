"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const fixturePath = path.join(
  __dirname,
  "evidence_portfolio_risk_weighted_diversification_consumer_fixture_v4.js"
);
const fixture = require(fixturePath);

const CARD_SCHEMA = "portfolio-risk-weighted-diversification-card-v4";
const CARD_FINGERPRINT =
  "20260823-weighted-diversification-card-v4-sealed-projection-lock-2";
const PROJECTION_SCHEMA =
  "strategy-correlation-cluster-portfolio-risk-projection-v4";
const PROJECTION_FINGERPRINT =
  "20260823-weighted-diversification-public-projection-v4-lock-1";
const STAGES = ["SOURCE", "GAP", "MATURITY", "PERMISSION"];

function projection() {
  return {
    schema_version: PROJECTION_SCHEMA,
    static_fingerprint: PROJECTION_FINGERPRINT,
    status: "PASS",
    decision:
      "EXACT_WEIGHTED_LOCAL_RESEARCH_DECISION_PROJECTED_AUTHORITY_UNCHANGED",
    projection_hash: "a".repeat(64),
    authority: {
      research_only: true,
      presentation_only: true,
      current_admission_allowed: false,
      current_pointer_written: false,
      formal_registry_activation_allowed: false,
      live_order_allowed: false,
      migration_allowed: false,
      paper_authorized: false,
      runtime_gate_activation_allowed: false,
      shadow_consumer_activation_allowed: false,
      writer_allowed: false
    }
  };
}

function knownModel(stages = STAGES) {
  return {
    schema_version: CARD_SCHEMA,
    static_fingerprint: CARD_FINGERPRINT,
    contract_state: "KNOWN",
    kicker: "PORTFOLIO RISK / LOCAL RESEARCH",
    title: "Weighted diversification",
    summary: "Concentration is declared without permission promotion.",
    stages: stages.map((key, index) => ({
      key,
      state: index === 3 ? "UNAUTHORIZED" : "VERIFIED",
      detail: index === 3 ? "NO_RUNTIME_PAPER_OR_LIVE_AUTHORITY" : "EXACT"
    })),
    metrics: [
      { label: "Label count", value: "2", note: "Declared" },
      { label: "Weighted effective count", value: "1.09", note: "Concentrated" },
      { label: "Dominant share", value: "95.65%", note: "Observed" },
      { label: "Minimum", value: "1.50", note: "Registered" }
    ],
    blockers: ["WEIGHTED_CLUSTER_DIVERSIFICATION"],
    effective_ratio_pct: 54.5361,
    projection_hash_short: "aaaaaaaaaaaa",
    permission_note: "Research display only.",
    tone: "concentrated"
  };
}

function fakeCard({
  model,
  markup,
  buildError = false,
  renderError = false,
  sealValid = true
} = {}) {
  return Object.freeze({
    CARD_SCHEMA_VERSION: CARD_SCHEMA,
    CARD_STATIC_FINGERPRINT: CARD_FINGERPRINT,
    PROJECTION_SCHEMA_VERSION: PROJECTION_SCHEMA,
    PROJECTION_STATIC_FINGERPRINT: PROJECTION_FINGERPRINT,
    STAGE_ORDER: Object.freeze(STAGES.slice()),
    buildPortfolioRiskWeightedDiversificationViewModelV4() {
      if (buildError) throw new Error("build failed");
      return model || knownModel();
    },
    renderPortfolioRiskWeightedDiversificationCardV4() {
      if (renderError) throw new Error("render failed");
      return markup
        || '<section class="prwd-v4" data-contract-state="KNOWN"><strong>UNAUTHORIZED</strong></section>';
    },
    verifyPortfolioRiskProjectionSealV4() {
      return sealValid;
    }
  });
}

function loadWithCard(card) {
  const source = fs.readFileSync(fixturePath, "utf8");
  const sandbox = {
    HakimiPortfolioRiskWeightedDiversificationCardV4: card
  };
  vm.runInNewContext(source, sandbox, { filename: fixturePath });
  return sandbox.HakimiPortfolioRiskWeightedDiversificationConsumerFixtureV4;
}

test("public API is version locked", () => {
  assert.equal(
    fixture.SCHEMA_VERSION,
    "portfolio-risk-weighted-diversification-presentation-consumer-fixture-v4"
  );
  assert.deepEqual(Object.keys(fixture).sort(), [
    "EXPECTED_CARD_SCHEMA_VERSION",
    "EXPECTED_CARD_STATIC_FINGERPRINT",
    "EXPECTED_PROJECTION_SCHEMA_VERSION",
    "EXPECTED_PROJECTION_STATIC_FINGERPRINT",
    "SCHEMA_VERSION",
    "STAGE_ORDER",
    "STATIC_FINGERPRINT",
    "buildPortfolioRiskWeightedDiversificationPresentationConsumerFixtureV4"
  ]);
  assert.equal(fixture.mount, undefined);
});

test("known fake card builds a frozen unmounted descriptor", () => {
  const isolated = loadWithCard(fakeCard());
  const result =
    isolated.buildPortfolioRiskWeightedDiversificationPresentationConsumerFixtureV4(
      projection()
    );
  assert.equal(result.status, "PASS");
  assert.equal(result.presentation.contract_state, "KNOWN");
  assert.equal(result.presentation.metric_count, 4);
  assert.equal(result.mount.requested, false);
  assert.equal(result.mount.performed, false);
  assert.equal(result.mount.dom_accessed, false);
  assert.equal(result.authority.presentation_consumer_activation_allowed, false);
  assert.equal(Object.isFrozen(result), true);
  assert.equal(Object.isFrozen(result.presentation.view_model), true);
});

test("actual card rejects malformed projection through safe fallback", () => {
  const result =
    fixture.buildPortfolioRiskWeightedDiversificationPresentationConsumerFixtureV4(
      null
    );
  assert.equal(result.status, "BLOCK");
  assert.equal(result.presentation.contract_state, "UNKNOWN");
  assert.match(result.presentation.markup, /UNKNOWN/);
  assert.match(result.presentation.markup, /UNAUTHORIZED/);
  assert.equal(result.presentation.metric_count, 0);
});

test("card public API drift fails closed before renderer invocation", () => {
  const drifted = { ...fakeCard(), mount() {} };
  const isolated = loadWithCard(drifted);
  const result =
    isolated.buildPortfolioRiskWeightedDiversificationPresentationConsumerFixtureV4(
      projection()
    );
  assert.equal(result.status, "BLOCK");
  assert.equal(result.source.card_contract_available, false);
  assert.equal(result.facts.renderer_invoked, false);
});

test("projection authority promotion fails closed even with a permissive fake card", () => {
  const input = projection();
  input.authority.paper_authorized = true;
  const isolated = loadWithCard(fakeCard());
  const result =
    isolated.buildPortfolioRiskWeightedDiversificationPresentationConsumerFixtureV4(
      input
    );
  assert.equal(result.status, "BLOCK");
  assert.equal(result.presentation.contract_state, "UNKNOWN");
  assert.equal(result.authority.paper_authorized, false);
});

test("card seal verifier rejection fails closed", () => {
  const isolated = loadWithCard(fakeCard({ sealValid: false }));
  const result =
    isolated.buildPortfolioRiskWeightedDiversificationPresentationConsumerFixtureV4(
      projection()
    );
  assert.equal(result.status, "BLOCK");
  assert.equal(result.presentation.contract_state, "UNKNOWN");
  assert.equal(result.source.projection_hash, null);
});

test("model stage reorder fails closed", () => {
  const isolated = loadWithCard(fakeCard({
    model: knownModel(["SOURCE", "MATURITY", "GAP", "PERMISSION"])
  }));
  const result =
    isolated.buildPortfolioRiskWeightedDiversificationPresentationConsumerFixtureV4(
      projection()
    );
  assert.equal(result.status, "BLOCK");
  assert.equal(result.presentation.view_model.stages[3].state, "UNAUTHORIZED");
});

test("dangerous renderer markup fails closed", () => {
  const isolated = loadWithCard(fakeCard({
    markup: '<section class="prwd-v4"><script>bad()</script><strong>UNAUTHORIZED</strong></section>'
  }));
  const result =
    isolated.buildPortfolioRiskWeightedDiversificationPresentationConsumerFixtureV4(
      projection()
    );
  assert.equal(result.status, "BLOCK");
  assert.doesNotMatch(result.presentation.markup, /<script/i);
});

test("builder and renderer exceptions both fail closed", () => {
  for (const card of [fakeCard({ buildError: true }), fakeCard({ renderError: true })]) {
    const isolated = loadWithCard(card);
    const result =
      isolated.buildPortfolioRiskWeightedDiversificationPresentationConsumerFixtureV4(
        projection()
      );
    assert.equal(result.status, "BLOCK");
    assert.equal(result.mount.performed, false);
  }
});

test("descriptor does not echo projection or raw evidence", () => {
  const input = projection();
  input.positions = [{ symbol: "SECRET_SYMBOL", notional: 999 }];
  input.correlation_matrix = { pairs: ["SECRET_PAIR"] };
  const isolated = loadWithCard(fakeCard());
  const result =
    isolated.buildPortfolioRiskWeightedDiversificationPresentationConsumerFixtureV4(
      input
    );
  const serialized = JSON.stringify(result);
  assert.doesNotMatch(serialized, /SECRET_SYMBOL|SECRET_PAIR/);
  assert.equal(result.facts.projection_document_embedded, false);
  assert.equal(result.facts.source_evidence_embedded, false);
  assert.equal(result.source.projection_hash, input.projection_hash);
});

test("input is not mutated and output is deterministic", () => {
  const input = projection();
  const before = JSON.stringify(input);
  const isolated = loadWithCard(fakeCard());
  const first =
    isolated.buildPortfolioRiskWeightedDiversificationPresentationConsumerFixtureV4(
      input
    );
  const second =
    isolated.buildPortfolioRiskWeightedDiversificationPresentationConsumerFixtureV4(
      input
    );
  assert.equal(JSON.stringify(input), before);
  assert.equal(JSON.stringify(first), JSON.stringify(second));
});

test("implementation identity is not self-certified at runtime", () => {
  const isolated = loadWithCard(fakeCard());
  const result =
    isolated.buildPortfolioRiskWeightedDiversificationPresentationConsumerFixtureV4(
      projection()
  );
  assert.equal(result.source.implementation_hashes_runtime_verified, false);
  assert.equal(
    Object.hasOwn(result.source, "card_implementation_sha256_review_pin"),
    false
  );
  assert.equal(
    Object.hasOwn(result.source, "projection_implementation_sha256_review_pin"),
    false
  );
  assert.equal(result.authority.current_admission_allowed, false);
  assert.equal(result.authority.shadow_consumer_activation_allowed, false);
});

test("render descriptor contains no promotion wording", () => {
  const isolated = loadWithCard(fakeCard());
  const result =
    isolated.buildPortfolioRiskWeightedDiversificationPresentationConsumerFixtureV4(
      projection()
    );
  const promotion = new RegExp("\\b" + "R" + "EADY" + "\\b", "i");
  assert.doesNotMatch(JSON.stringify(result), promotion);
  assert.match(result.presentation.markup, /UNAUTHORIZED/);
});

test("production fixture has no DOM network or mount primitive", () => {
  const source = fs.readFileSync(fixturePath, "utf8");
  for (const forbidden of [
    "document.",
    "window.",
    "querySelector",
    "innerHTML",
    "appendChild",
    "replaceChildren",
    "fetch(",
    "XMLHttpRequest",
    "WebSocket"
  ]) {
    assert.doesNotMatch(
      source,
      new RegExp(forbidden.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    );
  }
});
