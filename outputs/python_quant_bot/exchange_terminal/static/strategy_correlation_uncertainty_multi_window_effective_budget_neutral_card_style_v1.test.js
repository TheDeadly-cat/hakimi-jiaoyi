"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const ROOT = __dirname;
const CSS_NAME =
  "strategy_correlation_uncertainty_multi_window_effective_budget_neutral_card_v1.css";
const CARD_NAME =
  "strategy_correlation_uncertainty_multi_window_effective_budget_neutral_card_v1.js";
const CARD_TEST_NAME =
  "strategy_correlation_uncertainty_multi_window_effective_budget_neutral_card_v1.test.js";
const ADR_PATH = path.resolve(
  ROOT,
  "../../docs/adr/0348-correlation-uncertainty-multi-window-effective-budget-neutral-card-v1.md"
);
const css = fs.readFileSync(path.join(ROOT, CSS_NAME), "utf8");
const cardSource = fs.readFileSync(path.join(ROOT, CARD_NAME), "utf8");

function sha256(filePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

test("pins the exact ADR0348 card implementation contract and decision", () => {
  assert.equal(
    sha256(path.join(ROOT, CARD_NAME)),
    "ff6df4552dd735483325ccde8f146f161228d3963685848b5f2905d5fdf59354"
  );
  assert.equal(
    sha256(path.join(ROOT, CARD_TEST_NAME)),
    "3acf29a3cd1385ef255a444750d98b79b9044f38860f83276f88c3c45e512eb8"
  );
  assert.equal(
    sha256(ADR_PATH),
    "e97baac2fa7d3bf9b071fa2ffe656589884a58de62c696ccf4896e80031f6b9c"
  );
});

test("protected host preimages are exact and the stylesheet is unmounted", () => {
  const protectedFiles = {
    "app.js": "9bf55162aff8d7a233804557c91605c801b92f515b2835978c05e2d1f3ef9210",
    "evidence_presentation.js": "9822b147c583d29fc7c6d4866d73a0015914e2971458239ab3d1d1c2ff39e409",
    "styles.css": "ee6a5ae746142e32df768fe3261746f66c2b1a902e38b85fa9c0ecc4ce7bdc2a",
  };
  Object.entries(protectedFiles).forEach(([name, expected]) => {
    const filePath = path.join(ROOT, name);
    assert.equal(sha256(filePath), expected);
    assert.equal(fs.readFileSync(filePath, "utf8").includes(CSS_NAME), false);
  });
});

test("every emitted card class has an explicit scoped style", () => {
  const expectedClasses = [
    "hakimi-uncertainty-budget-card-v1",
    "hakimi-uncertainty-budget-card-v1__footer",
    "hakimi-uncertainty-budget-card-v1__gaps",
    "hakimi-uncertainty-budget-card-v1__header",
    "hakimi-uncertainty-budget-card-v1__metric",
    "hakimi-uncertainty-budget-card-v1__metrics",
    "hakimi-uncertainty-budget-card-v1__metrics-empty",
    "hakimi-uncertainty-budget-card-v1__path",
    "hakimi-uncertainty-budget-card-v1__stage",
    "hakimi-uncertainty-budget-card-v1__status",
    "hakimi-uncertainty-budget-card-v1__summary",
  ];
  expectedClasses.forEach((className) => {
    assert.equal(cardSource.includes(className), true, className + " missing from card");
    assert.equal(css.includes("." + className), true, className + " missing from CSS");
  });
});

test("stylesheet has no global host selectors", () => {
  assert.doesNotMatch(css, /(^|[}\n]\s*)(?:html|body|:root)\b/im);
  assert.doesNotMatch(css, /(^|,)\s*\*/m);
  assert.doesNotMatch(css, /#[A-Za-z_][\w-]*\s*\{/);
  assert.match(css, /^\.hakimi-uncertainty-budget-card-v1\s*\{/);
});

test("visual direction uses scoped tokens expressive typography and layered paper", () => {
  ["paper", "source", "gap", "maturity", "permission"].forEach((token) => {
    assert.match(css, new RegExp("--hub-" + token + ":\\s*#[0-9a-f]{6}", "i"));
  });
  assert.match(css, /Bahnschrift SemiCondensed/);
  assert.match(css, /Iowan Old Style/);
  assert.match(css, /Cascadia Mono/);
  assert.match(css, /radial-gradient/);
  assert.match(css, /repeating-linear-gradient/);
});

test("desktop and narrow layouts preserve metrics stages gaps and permission", () => {
  assert.match(css, /grid-template-columns:\s*repeat\(3,\s*minmax\(0,\s*1fr\)\)/);
  assert.match(css, /grid-template-columns:\s*repeat\(4,\s*minmax\(0,\s*1fr\)\)/);
  assert.match(css, /@container hakimi-uncertainty-budget \(max-width:\s*52rem\)/);
  assert.match(css, /@container hakimi-uncertainty-budget \(max-width:\s*34rem\)/);
  assert.match(css, /@media \(max-width:\s*42rem\)/);
  assert.match(css, /\.hakimi-uncertainty-budget-card-v1__footer/);
});

test("normalized stage states receive scoped treatment and remain visible text", () => {
  [
    "hash-bound-local",
    "open",
    "synthetic-unmounted",
    "unauthorized",
  ].forEach((state) => {
    assert.match(css, new RegExp('data-state="' + state + '"'));
  });
  assert.match(cardSource, /escapeHtml\(stage\.state\)/);
  assert.match(cardSource, /escapeHtml\(stage\.axis\)/);
});

test("motion is finite meaningful and disabled for reduced motion", () => {
  assert.match(css, /@keyframes hub-card-arrival/);
  assert.match(css, /@keyframes hub-stage-arrival/);
  assert.doesNotMatch(css, /animation[^;]*\binfinite\b/i);
  assert.match(css, /@media \(prefers-reduced-motion:\s*reduce\)/);
  assert.match(css, /animation:\s*none/);
});

test("high contrast forced colors and print each have explicit fallbacks", () => {
  assert.match(css, /@media \(prefers-contrast:\s*more\)/);
  assert.match(css, /@media \(forced-colors:\s*active\)/);
  assert.match(css, /CanvasText/);
  assert.match(css, /@media print/);
});

test("stylesheet has no network executable or host-layout escape", () => {
  assert.doesNotMatch(css, /@import|url\s*\(|expression\s*\(|javascript:/i);
  assert.doesNotMatch(css, /position:\s*fixed/i);
  assert.doesNotMatch(css, /!important/i);
  assert.doesNotMatch(css, /behavior\s*:/i);
});

test("pseudo-elements inject decoration only and never UI copy", () => {
  const declarations = [...css.matchAll(/^\s*content:\s*([^;]+);/gm)].map(
    (match) => match[1].trim()
  );
  assert.ok(declarations.length >= 3);
  assert.deepEqual([...new Set(declarations)], ['""']);
});

test("stylesheet contains no promotional wording or sensitive data locator", () => {
  const forbidden = new RegExp(
    "\\b(?:" + ["REA", "DY|PRO", "FIT|RET", "URN|B", "UY|S", "ELL"].join("") + ")\\b",
    "i"
  );
  assert.equal(forbidden.test(css), false);
  assert.doesNotMatch(css, /connection_string|storage_path|private_key|api_key/i);
});

test("stylesheet is balanced and contains no unresolved template token", () => {
  const open = (css.match(/\{/g) || []).length;
  const close = (css.match(/\}/g) || []).length;
  assert.equal(open, close);
  assert.equal(open > 40, true);
  assert.doesNotMatch(css, /[$][{]|<%|[{][{]|[}][}]/);
});
