"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

test("session-freshness candidate remains absent from current UI mounts", () => {
  const app = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");
  const index = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
  const candidate =
    /HakimiPortfolioRiskSessionFreshnessCardV1|evidence_portfolio_risk_session_freshness_card_v1/;
  assert.doesNotMatch(app, candidate);
  assert.doesNotMatch(index, candidate);
});

test("suite v17 locks stage order, authority gap, and accessibility", () => {
  const js = fs.readFileSync(
    path.join(__dirname, "evidence_portfolio_risk_session_freshness_card_v1.js"),
    "utf8",
  );
  const css = fs.readFileSync(
    path.join(__dirname, "evidence_portfolio_risk_session_freshness_card_v1.css"),
    "utf8",
  );
  for (const stage of ["SOURCE", "GAP", "MATURITY", "PERMISSION"]) {
    assert.match(js, new RegExp('"' + stage + '"'));
  }
  assert.match(js, /外部时钟权威未认证/);
  assert.match(js, /PAPER \/ LIVE 未授权/);
  assert.doesNotMatch(js, /READY|收益保证|盈利保证/);
  assert.match(css, /prefers-reduced-motion/);
  assert.match(css, /forced-colors/);
});
