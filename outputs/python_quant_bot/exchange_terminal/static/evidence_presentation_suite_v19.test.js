"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

function read(name) {
  return fs.readFileSync(path.join(__dirname, name), "utf8");
}

test("registry identity gap v2 remains absent from current UI mounts", () => {
  const app = read("app.js");
  const index = read("index.html");
  const candidate =
    /AntiReplayRegistryGap.*V2|gap_projection_v2|gap_card_v2|gap_consumer_fixture_v2|anti-replay-registry-gap-card-v2/;
  assert.doesNotMatch(app, candidate);
  assert.doesNotMatch(index, candidate);
});

test("suite v19 locks neutral stage order and identity evidence ledger", () => {
  const projection = read("evidence_anti_replay_registry_gap_projection_v2.js");
  const card = read("evidence_anti_replay_registry_gap_card_v2.js");
  for (const stage of ["SOURCE", "GAP", "MATURITY", "PERMISSION"]) {
    assert.match(projection, new RegExp('"' + stage + '"'));
    assert.match(card, new RegExp('"' + stage + '"'));
  }
  assert.match(projection, /OBSERVED-LOCAL/);
  assert.match(projection, /UNVERIFIED/);
  assert.match(projection, /INCOMPLETE/);
  assert.match(card, /IDENTITY EVIDENCE LEDGER/);
  assert.match(card, /OPEN SYSTEM GAP REGISTER/);
  assert.match(card, /EVIDENCE GAP/);
  assert.match(card, /LOCKED/);
  assert.doesNotMatch(
    projection + card,
    /\bREADY\b|profit|win rate|收益保证|盈利保证/i
  );
});

test("suite v19 locks unmounted fixture and reused stylesheet", () => {
  const fixture = read(
    "evidence_anti_replay_registry_gap_consumer_fixture_v2.js"
  );
  assert.match(fixture, /status: "UNMOUNTED"/);
  assert.match(fixture, /mounted: false/);
  assert.match(fixture, /route_bound: false/);
  assert.match(fixture, /browser_visual_review_performed: false/);
  assert.match(fixture, /stylesheet_reused_without_modification: true/);
  assert.match(
    fixture,
    /evidence_anti_replay_registry_gap_card_v1\.css/
  );
});

test("suite v19 locks frozen v1 and shared stylesheet fingerprints", () => {
  const v1Css = read("evidence_anti_replay_registry_gap_card_v1.css");
  const sharedCss = read("styles.css");
  assert.equal(
    crypto.createHash("sha256").update(v1Css).digest("hex"),
    "8df1da62171147843bc655f07c79090d1176d16a8b3186c4f83390e3e02e08ad"
  );
  assert.equal(
    crypto.createHash("sha256").update(sharedCss).digest("hex"),
    "ee6a5ae746142e32df768fe3261746f66c2b1a902e38b85fa9c0ecc4ce7bdc2a"
  );
  assert.match(v1Css, /\.ar-gap-card/);
  assert.match(v1Css, /max-width: 720px/);
  assert.match(v1Css, /prefers-reduced-motion/);
  assert.match(v1Css, /forced-colors/);
  assert.doesNotMatch(v1Css, /(^|\n)\s*(body|html|:root)\b/);
});
