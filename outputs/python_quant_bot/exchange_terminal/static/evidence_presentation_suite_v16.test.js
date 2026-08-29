"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

test("portfolio-risk geometry candidate remains absent from current UI mounts", () => {
  const app = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");
  const index = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
  const candidate =
    /HakimiPortfolioRiskGeometryCardV1|evidence_portfolio_risk_geometry_card_v1/;
  assert.doesNotMatch(app, candidate);
  assert.doesNotMatch(index, candidate);
});

test("suite v16 locks neutral presentation and accessibility surfaces", () => {
  const js = fs.readFileSync(
    path.join(__dirname, "evidence_portfolio_risk_geometry_card_v1.js"),
    "utf8",
  );
  const css = fs.readFileSync(
    path.join(__dirname, "evidence_portfolio_risk_geometry_card_v1.css"),
    "utf8",
  );
  for (const stage of ["SOURCE", "GAP", "MATURITY", "PERMISSION"]) {
    assert.match(js, new RegExp('"' + stage + '"'));
  }
  assert.match(js, /PAPER \/ LIVE 未授权/);
  assert.doesNotMatch(js, /READY/);
  assert.match(css, /prefers-reduced-motion/);
  assert.match(css, /forced-colors/);
});
