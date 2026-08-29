"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const strictCanonical = require("./strict_canonical_json_v1.js");
const card = require("./evidence_portfolio_risk_joint_evidence_card_v5.js");
const consumer = require(
  "./evidence_portfolio_risk_joint_evidence_consumer_fixture_v5.js"
);
const review = require(
  "./evidence_portfolio_risk_joint_evidence_descriptor_load_order_review_candidate_v1.js"
);

const stylesheetText = fs.readFileSync(
  path.resolve(
    __dirname,
    "evidence_portfolio_risk_joint_evidence_card_v5.css"
  ),
  "utf8"
);

function projection(localStatus) {
  const status = localStatus || "PASS";
  const passed = status === "PASS";
  return strictCanonical.sealDocument(
    {
      schema_version: card.PROJECTION_SCHEMA_VERSION,
      static_fingerprint: card.PROJECTION_STATIC_FINGERPRINT,
      status: "BLOCK",
      decision:
        "EXACT_HTTP_CANDIDATE_V5_PROJECTED_KNOWN_BLOCKED_AUTHORITY_UNCHANGED",
      source: {
        candidate_v5_schema_version: "candidate-v5",
        candidate_v5_static_fingerprint: "candidate-v5-lock",
        candidate_v5_response_hash: "1".repeat(64),
        candidate_v5_exactly_verified: true,
        candidate_v5_implementation_sha256: "2".repeat(64),
        candidate_state: "KNOWN_BLOCKED",
        source_preregistration_hash: "3".repeat(64),
        portfolio_risk_adapter_v5_hash: "4".repeat(64)
      },
      local_decision: {
        status,
        decision: "PASS_WEIGHTED_AND_MULTI_WINDOW_STABLE_RESEARCH_GATE",
        joint_risk_gate_passed: passed,
        blockers: ["PRESENTATION_HTTP_CANDIDATE_V5_UNREGISTERED"]
      },
      joint_risk: {
        assessment: passed
          ? "LOCAL_JOINT_RESEARCH_GATE_PASSED"
          : "LOCAL_JOINT_RESEARCH_GATE_BLOCKED",
        multi_window_stability_gate_verified: passed,
        anchor_window_budget_and_context_bound: true,
        trade_identity_cross_bound: true,
        anchor_window_id: "medium",
        trade_identity_hash: "5".repeat(64)
      },
      gaps: {
        remaining_blocker_count: 1,
        remaining_blockers: ["route_unregistered"],
        candidate_blockers: ["PRESENTATION_HTTP_CANDIDATE_V5_UNREGISTERED"]
      },
      stages: [
        { key: "SOURCE", state: "VERIFIED", detail: "V5_EXACT_REBUILD" },
        { key: "GAP", state: "PRESENT", detail: "EXTERNAL_GAPS" },
        { key: "MATURITY", state: "LOCAL_EVIDENCE_BOUND", detail: "LOCAL_ONLY" },
        { key: "PERMISSION", state: "UNAUTHORIZED", detail: "NO_AUTHORITY" }
      ],
      facts: {
        projection_only: true,
        candidate_v5_exactly_verified: true,
        http_candidate_to_projection_bound: true,
        source_document_embedded: false,
        verification_context_embedded: false,
        positions_embedded: false,
        correlation_matrices_embedded: false,
        profitability_proven: false,
        runtime_consumer_bound: false,
        ui_mounted: false
      },
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
    },
    "projection_hash"
  );
}

function manifest() {
  return { ...review.EXPECTED_ASSET_MANIFEST };
}

function descriptor(source) {
  return consumer.buildPortfolioRiskJointEvidencePresentationConsumerFixtureV5(
    source
  );
}

function build(overrides) {
  const options = overrides || {};
  const source = options.projection || projection(options.localStatus);
  const observed = options.descriptor || descriptor(source);
  return {
    source,
    observed,
    stylesheet:
      options.stylesheet === undefined ? stylesheetText : options.stylesheet,
    assets: options.assets || manifest(),
    javascriptOrder:
      options.javascriptOrder || review.EXPECTED_JAVASCRIPT_LOAD_ORDER.slice(),
    stylesheetOrder:
      options.stylesheetOrder || review.EXPECTED_STYLESHEET_LOAD_ORDER.slice(),
    document: review.buildPortfolioRiskDescriptorLoadOrderStaticReviewCandidateV1(
      source,
      observed,
      options.stylesheet === undefined ? stylesheetText : options.stylesheet,
      options.assets || manifest(),
      options.javascriptOrder
        || review.EXPECTED_JAVASCRIPT_LOAD_ORDER.slice(),
      options.stylesheetOrder
        || review.EXPECTED_STYLESHEET_LOAD_ORDER.slice()
    )
  };
}

test("exports and dependency declarations are frozen and versioned", () => {
  assert.equal(Object.isFrozen(review), true);
  assert.equal(Object.isFrozen(review.EXPECTED_ASSET_MANIFEST), true);
  assert.equal(Object.isFrozen(review.EXPECTED_JAVASCRIPT_LOAD_ORDER), true);
  assert.equal(Object.keys(review.EXPECTED_ASSET_MANIFEST).length, 6);
  assert.equal(review.SCHEMA_VERSION.endsWith("review-v1"), true);
});

test("valid descriptor CSS and load order produce static review pass", () => {
  const result = build();
  assert.equal(result.document.status, "PASS");
  assert.equal(result.document.verification.descriptor_exactly_rebuilt, true);
  assert.equal(
    result.document.verification.stylesheet_content_sha256_verified,
    true
  );
  assert.equal(result.document.facts.static_descriptor_review_performed, true);
  assert.equal(
    result.document.facts.static_dependency_load_order_reviewed,
    true
  );
  assert.equal(result.document.facts.browser_visual_review_performed, false);
});

test("local gate block remains a valid unmounted static review", () => {
  const result = build({ localStatus: "BLOCK" });
  assert.equal(result.document.status, "PASS");
  assert.equal(result.observed.status, "BLOCK");
  assert.equal(
    result.observed.presentation.view_model.status_label,
    "LOCAL GATE BLOCK"
  );
  assert.equal(result.document.authority.presentation_mount_allowed, false);
});

test("swapped JavaScript dependency order blocks review", () => {
  const order = review.EXPECTED_JAVASCRIPT_LOAD_ORDER.slice();
  [order[1], order[2]] = [order[2], order[1]];
  const result = build({ javascriptOrder: order });
  assert.equal(result.document.status, "BLOCK");
  assert.ok(
    result.document.blockers.includes(
      "javascript_dependency_load_order_exact"
    )
  );
});

test("duplicate JavaScript asset blocks exact load order", () => {
  const order = review.EXPECTED_JAVASCRIPT_LOAD_ORDER.slice();
  order.push(order[order.length - 1]);
  const result = build({ javascriptOrder: order });
  assert.equal(result.document.status, "BLOCK");
  assert.equal(
    result.document.verification.javascript_load_order.length,
    0
  );
});

test("missing extra and substituted manifest values block review", () => {
  const missing = manifest();
  delete missing.joint_evidence_card_v5_css;
  const extra = manifest();
  extra.unexpected = "f".repeat(64);
  const wrong = manifest();
  wrong.joint_evidence_consumer_v5_js = "f".repeat(64);
  for (const assets of [missing, extra, wrong]) {
    const result = build({ assets });
    assert.equal(result.document.status, "BLOCK");
    assert.ok(
      result.document.blockers.includes("six_asset_manifest_exact")
    );
  }
});

test("stylesheet hash substitution blocks content contract", () => {
  const result = build({ stylesheet: stylesheetText + "\n/* altered */\n" });
  assert.equal(result.document.status, "BLOCK");
  assert.ok(
    result.document.blockers.includes("stylesheet_content_sha256_exact")
  );
});

test("global stylesheet leakage is independently detected", () => {
  const result = build({ stylesheet: "body { color: red; }\n" + stylesheetText });
  assert.equal(result.document.status, "BLOCK");
  assert.ok(
    result.document.blockers.includes("stylesheet_global_scope_absent")
  );
});

test("missing responsive and reduced-motion contracts block review", () => {
  const withoutResponsive = stylesheetText.replace(
    "@media (max-width: 760px)",
    "@media (min-width: 9999px)"
  );
  const responsive = build({ stylesheet: withoutResponsive });
  assert.ok(
    responsive.document.blockers.includes(
      "stylesheet_responsive_contract_present"
    )
  );
  const withoutReducedMotion = stylesheetText.replace(
    "prefers-reduced-motion",
    "prefers-color-scheme"
  );
  const motion = build({ stylesheet: withoutReducedMotion });
  assert.ok(
    motion.document.blockers.includes(
      "stylesheet_reduced_motion_contract_present"
    )
  );
});

test("resealed mount promotion blocks descriptor exact rebuild", () => {
  const source = projection();
  const altered = JSON.parse(JSON.stringify(descriptor(source)));
  delete altered.descriptor_hash;
  altered.mount.mode = "MOUNTED";
  altered.facts.ui_mounted = true;
  const resealed = strictCanonical.sealDocument(altered, "descriptor_hash");
  const result = build({ projection: source, descriptor: resealed });
  assert.equal(result.document.status, "BLOCK");
  assert.ok(
    result.document.blockers.includes(
      "consumer_v5_descriptor_exact_rebuild"
    )
  );
});

test("resealed markup script injection blocks review", () => {
  const source = projection();
  const altered = JSON.parse(JSON.stringify(descriptor(source)));
  delete altered.descriptor_hash;
  altered.presentation.markup += "<script>boom()</script>";
  const resealed = strictCanonical.sealDocument(altered, "descriptor_hash");
  const result = build({ projection: source, descriptor: resealed });
  assert.equal(result.document.status, "BLOCK");
  assert.ok(
    result.document.blockers.includes(
      "consumer_v5_descriptor_exact_rebuild"
    )
  );
});

test("resealed wrong projection schema remains unknown and blocked", () => {
  const altered = JSON.parse(JSON.stringify(projection()));
  delete altered.projection_hash;
  altered.schema_version =
    "strategy-correlation-cluster-portfolio-risk-projection-v4";
  const resealed = strictCanonical.sealDocument(altered, "projection_hash");
  const result = build({ projection: resealed });
  assert.equal(result.document.status, "BLOCK");
  assert.equal(result.document.source.projection_schema_version, "UNKNOWN");
});

test("public verifier accepts exact review and rejects authority tamper", () => {
  const result = build();
  assert.equal(
    review.verifyPortfolioRiskDescriptorLoadOrderStaticReviewCandidateV1(
      result.document,
      result.source,
      result.observed,
      result.stylesheet,
      result.assets,
      result.javascriptOrder,
      result.stylesheetOrder
    ).status,
    "PASS"
  );
  const altered = JSON.parse(JSON.stringify(result.document));
  delete altered.review_hash;
  altered.authority.paper_authorized = true;
  const resealed = strictCanonical.sealDocument(altered, "review_hash");
  assert.equal(
    review.verifyPortfolioRiskDescriptorLoadOrderStaticReviewCandidateV1(
      resealed,
      result.source,
      result.observed,
      result.stylesheet,
      result.assets,
      result.javascriptOrder,
      result.stylesheetOrder
    ).status,
    "BLOCK"
  );
});

test("review is deeply frozen neutral and embeds no source artifacts", () => {
  const result = build();
  assert.equal(Object.isFrozen(result.document), true);
  assert.equal(Object.isFrozen(result.document.checks), true);
  assert.equal(result.document.source.asset_manifest_embedded, false);
  assert.equal(result.document.source.descriptor_embedded, false);
  assert.equal(result.document.source.stylesheet_source_embedded, false);
  assert.equal(result.document.facts.stylesheet_executed, false);
  assert.equal(result.document.facts.ui_mounted, false);
  assert.equal(result.document.facts.profitability_proven, false);
  const promotion = new RegExp("\\b" + "R" + "EADY" + "\\b", "i");
  assert.doesNotMatch(JSON.stringify(result.document), promotion);
});

test("production review module reads no file DOM browser or network", () => {
  const source = fs.readFileSync(
    path.resolve(
      __dirname,
      "evidence_portfolio_risk_joint_evidence_descriptor_load_order_review_candidate_v1.js"
    ),
    "utf8"
  );
  for (const forbidden of [
    "node:fs",
    "document.",
    "window.",
    "fetch(",
    "XMLHttpRequest",
    "WebSocket"
  ]) assert.equal(source.includes(forbidden), false);
});
