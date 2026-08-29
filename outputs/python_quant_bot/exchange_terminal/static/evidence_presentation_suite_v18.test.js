"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

function read(name) {
  return fs.readFileSync(path.join(__dirname, name), "utf8");
}

test("anti-replay gap candidate remains absent from current UI mounts", () => {
  const app = read("app.js");
  const index = read("index.html");
  const candidate =
    /ar-gap-card|AntiReplayRegistryGap|evidence_anti_replay_registry_gap/;
  assert.doesNotMatch(app, candidate);
  assert.doesNotMatch(index, candidate);
});

test("suite v18 locks neutral stage order and non-promotional copy", () => {
  const projection = read("evidence_anti_replay_registry_gap_projection_v1.js");
  const card = read("evidence_anti_replay_registry_gap_card_v1.js");
  for (const stage of ["SOURCE", "GAP", "MATURITY", "PERMISSION"]) {
    assert.match(projection, new RegExp('"' + stage + '"'));
    assert.match(card, new RegExp('"' + stage + '"'));
  }
  assert.match(card, /EVIDENCE GAP/);
  assert.match(card, /LOCAL-ONLY/);
  assert.match(card, /LOCKED/);
  assert.doesNotMatch(card, /\bREADY\b|profit|win rate|收益保证|盈利保证/i);
});

test("suite v18 locks unmounted fixture and permission authority", () => {
  const fixture = read(
    "evidence_anti_replay_registry_gap_consumer_fixture_v1.js"
  );
  assert.match(fixture, /status: "UNMOUNTED"/);
  assert.match(fixture, /mounted: false/);
  assert.match(fixture, /route_bound: false/);
  assert.match(fixture, /browser_visual_review_performed: false/);
  assert.match(fixture, /presentation_mount_allowed/);
});

test("suite v18 locks scoped responsive high-contrast stylesheet", () => {
  const css = read("evidence_anti_replay_registry_gap_card_v1.css");
  assert.match(css, /\.ar-gap-card/);
  assert.match(css, /max-width: 720px/);
  assert.match(css, /prefers-reduced-motion/);
  assert.match(css, /forced-colors/);
  assert.match(css, /CanvasText/);
  assert.doesNotMatch(css, /(^|\n)\s*(body|html|:root)\b/);
  assert.equal(
    crypto.createHash("sha256").update(css).digest("hex"),
    "8df1da62171147843bc655f07c79090d1176d16a8b3186c4f83390e3e02e08ad"
  );
  assert.equal(
    crypto.createHash("sha256").update(read("styles.css")).digest("hex"),
    "ee6a5ae746142e32df768fe3261746f66c2b1a902e38b85fa9c0ecc4ce7bdc2a"
  );
});
