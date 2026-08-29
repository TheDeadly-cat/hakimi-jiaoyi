"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const style = require(
  "./evidence_source_baseline_provider_conformance_style_preregistration_v1.js"
);

const CSS_PATH = path.join(
  __dirname,
  "evidence_source_baseline_provider_conformance_card_v1.css"
);
const CARD_PATH = path.join(
  __dirname,
  "evidence_source_baseline_provider_conformance_card_v1.js"
);
const STRICT_PATH = path.join(__dirname, "strict_canonical_json_v1.js");
const PROTECTED_STYLE_PATH = path.join(__dirname, "styles.css");
const css = fs.readFileSync(CSS_PATH, "utf8");
const cardSource = fs.readFileSync(CARD_PATH, "utf8");

function fileHash(filePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

function cssVariable(name) {
  const match = css.match(new RegExp("--" + name + "\\s*:\\s*([^;]+);"));
  return match ? match[1].trim() : null;
}

function channel(hex, offset) {
  return Number.parseInt(hex.slice(offset, offset + 2), 16) / 255;
}

function linear(value) {
  return value <= 0.04045
    ? value / 12.92
    : ((value + 0.055) / 1.055) ** 2.4;
}

function luminance(hex) {
  return (
    0.2126 * linear(channel(hex, 1)) +
    0.7152 * linear(channel(hex, 3)) +
    0.0722 * linear(channel(hex, 5))
  );
}

function contrast(left, right) {
  const high = Math.max(luminance(left), luminance(right));
  const low = Math.min(luminance(left), luminance(right));
  return (high + 0.05) / (low + 0.05);
}

function stringValues(value, output = []) {
  if (Array.isArray(value)) {
    value.forEach((item) => stringValues(item, output));
  } else if (value && typeof value === "object") {
    Object.values(value).forEach((item) => stringValues(item, output));
  } else if (typeof value === "string") {
    output.push(value);
  }
  return output;
}

test("style preregistration is exact, blocked, and unmounted", () => {
  const document =
    style.buildSourceBaselineProviderConformanceStylePreregistrationV1();
  assert.equal(
    style.verifySourceBaselineProviderConformanceStylePreregistrationV1(
      document
    ),
    true
  );
  assert.equal(document.status, "BLOCKED");
  assert.equal(document.candidate_state, "ISOLATED_STYLESHEET_UNMOUNTED");
});

test("preregistration pins current registration, card, and canonical helper", () => {
  assert.equal(
    style.CONSUMER_REGISTRATION_IMPLEMENTATION_SHA256,
    "948aaa77ea86658732226d2ed4d4c585a625ba409b946ef1f79fac58f0a883fe"
  );
  assert.equal(fileHash(CARD_PATH), style.CARD_IMPLEMENTATION_SHA256);
  assert.equal(fileHash(STRICT_PATH), style.STRICT_CANONICAL_JS_SHA256);
});

test("protected stylesheet remains unchanged and unimported", () => {
  const document =
    style.buildSourceBaselineProviderConformanceStylePreregistrationV1();
  assert.equal(fileHash(PROTECTED_STYLE_PATH), style.PROTECTED_STYLESHEET_SHA256);
  assert.equal(document.asset_plan.protected_stylesheet_imported, false);
  assert.equal(css.includes("styles.css"), false);
});

test("stylesheet hash and app bindings remain unregistered", () => {
  const document =
    style.buildSourceBaselineProviderConformanceStylePreregistrationV1();
  assert.equal(document.asset_plan.stylesheet_sha256, null);
  assert.equal(document.asset_plan.app_importer, null);
  assert.equal(document.asset_plan.html_template, null);
  assert.equal(document.authority.stylesheet_binding_allowed, false);
});

test("palette has six deliberate non-purple non-neon colors", () => {
  const colors = style.STYLE_TOKENS.colors;
  assert.equal(Object.keys(colors).length, 6);
  assert.deepEqual(colors, {
    surface: "#e8eef0",
    ink: "#142226",
    trace: "#245f63",
    gap: "#8a521f",
    lock: "#7a3028",
    line: "#779097",
  });
  assert.equal(/purple|violet|magenta|lime|neon/i.test(css), false);
});

test("all preregistered color tokens are implemented exactly", () => {
  for (const [name, value] of Object.entries(style.STYLE_TOKENS.colors)) {
    assert.equal(cssVariable("sb-color-" + name), value);
  }
});

test("display, body, and utility typography roles are distinct", () => {
  const typography = style.STYLE_TOKENS.typography;
  assert.equal(cssVariable("sb-font-display"), typography.display);
  assert.equal(cssVariable("sb-font-body"), typography.body);
  assert.equal(cssVariable("sb-font-utility"), typography.utility);
  assert.equal(new Set(Object.values(typography)).size, 3);
  assert.equal(/\bInter\b|\bRoboto\b/i.test(css), false);
});

test("critical card classes exist in both renderer and stylesheet", () => {
  const required =
    style.buildSourceBaselineProviderConformanceStylePreregistrationV1()
      .selector_contract.required_classes;
  for (const className of required) {
    assert.ok(cardSource.includes(className), className + " missing in renderer");
    assert.ok(css.includes("." + className), className + " missing in CSS");
  }
});

test("four semantic stage selectors are explicit", () => {
  const stages = ["SOURCE", "GAP", "MATURITY", "PERMISSION"];
  for (const stageName of stages) {
    assert.ok(css.includes('[data-stage="' + stageName + '"]'));
  }
  assert.ok(css.includes("FOUR_STAGE_CALIBRATION_SPINE") === false);
  assert.ok(css.includes("sb-conformance-card__stage-rail::before"));
});

test("all selectors remain card-namespaced", () => {
  assert.equal(/(^|})\s*(html|body|:root)(?=\s|,|\{)/m.test(css), false);
  assert.equal(/(^|})\s*\*(?=\s|,|\{)/m.test(css), false);
  const classNames = [...css.matchAll(/\.([A-Za-z_][\w-]*)/g)].map(
    (match) => match[1]
  );
  assert.ok(classNames.length > 0);
  assert.deepEqual(
    [...new Set(classNames.filter((name) => !name.startsWith("sb-conformance-card")))],
    []
  );
});

test("stylesheet has no external import or network asset", () => {
  assert.equal(/@import|url\s*\(|https?:|data:/i.test(css), false);
});

test("desktop and compact layouts are both explicit", () => {
  assert.ok(css.includes("grid-template-columns: repeat(5, minmax(0, 1fr))"));
  assert.ok(css.includes("grid-template-columns: repeat(4, minmax(0, 1fr))"));
  assert.ok(css.includes("@media (max-width: 780px)"));
  assert.ok(css.includes("@media (max-width: 520px)"));
  assert.ok(css.includes("grid-template-columns: 1fr"));
});

test("motion is mounted-only and reduced-motion aware", () => {
  assert.ok(
    css.includes(
      '.sb-conformance-card[data-mount-state="mounted"]'
    )
  );
  assert.ok(css.includes("@keyframes sb-conformance-calibration-in"));
  assert.ok(css.includes("@media (prefers-reduced-motion: reduce)"));
  assert.ok(css.includes("animation: none"));
  const baseStageRule = css.match(
    /^\.sb-conformance-card__stage\s*\{([^}]*)\}/m
  );
  assert.ok(baseStageRule);
  assert.equal(/\banimation(?:-name)?\s*:/.test(baseStageRule[1]), false);
});

test("primary text and semantic states meet normal-text contrast", () => {
  const colors = style.STYLE_TOKENS.colors;
  assert.ok(contrast(colors.surface, colors.ink) >= 7);
  assert.ok(contrast(colors.surface, colors.trace) >= 4.5);
  assert.ok(contrast(colors.surface, colors.gap) >= 4.5);
  assert.ok(contrast(colors.surface, colors.lock) >= 4.5);
});

test("copy and stylesheet contain no promotional language", () => {
  const document =
    style.buildSourceBaselineProviderConformanceStylePreregistrationV1();
  const values = stringValues(document).join(" ");
  assert.equal(
    /\bREADY\b|\bprofit\b|\breturn\b|\balpha\b|win rate/i.test(values),
    false
  );
  assert.equal(/\bREADY\b|profit|return|alpha|win rate/i.test(css), false);
  assert.equal(document.facts.profitability_proven, false);
});

test("style preregistration rejects promotion and extra fields", () => {
  const promoted =
    style.buildSourceBaselineProviderConformanceStylePreregistrationV1();
  promoted.authority.ui_consumer_mount_allowed = true;
  assert.equal(
    style.verifySourceBaselineProviderConformanceStylePreregistrationV1(
      promoted
    ),
    false
  );
  const extra =
    style.buildSourceBaselineProviderConformanceStylePreregistrationV1();
  extra.synthetic_promotion = true;
  assert.equal(
    style.verifySourceBaselineProviderConformanceStylePreregistrationV1(extra),
    false
  );
});

test("throwing getter and cyclic input fail closed", () => {
  const throwing =
    style.buildSourceBaselineProviderConformanceStylePreregistrationV1();
  Object.defineProperty(throwing, "status", {
    enumerable: true,
    get() {
      throw new Error("synthetic getter failure");
    },
  });
  assert.equal(
    style.verifySourceBaselineProviderConformanceStylePreregistrationV1(
      throwing
    ),
    false
  );
  const cyclic = {};
  cyclic.self = cyclic;
  assert.equal(
    style.verifySourceBaselineProviderConformanceStylePreregistrationV1(cyclic),
    false
  );
});

test("preregistration is deterministic and CSS is bounded", () => {
  assert.deepEqual(
    style.buildSourceBaselineProviderConformanceStylePreregistrationV1(),
    style.buildSourceBaselineProviderConformanceStylePreregistrationV1()
  );
  assert.ok(Buffer.byteLength(css, "utf8") >= 6000);
  assert.ok(Buffer.byteLength(css, "utf8") <= 20000);
});
