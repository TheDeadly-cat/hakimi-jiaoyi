const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const staticRoot = __dirname;
const indexSource = fs.readFileSync(path.join(staticRoot, "index.html"), "utf8");
const polishSource = fs.readFileSync(
  path.join(staticRoot, "terminal_visual_polish_v1.css"),
  "utf8",
);

function sha256(fileName) {
  return crypto
    .createHash("sha256")
    .update(fs.readFileSync(path.join(staticRoot, fileName)))
    .digest("hex");
}

test("visual polish is loaded once after the established style layers", () => {
  const baseIndex = indexSource.indexOf("./styles.css?");
  const policyIndex = indexSource.indexOf("./strategy_correlation_cluster_ticket_policy_v1.css?");
  const polishIndex = indexSource.indexOf("./terminal_visual_polish_v1.css?");
  const occurrences = indexSource.match(/terminal_visual_polish_v1\.css/g) || [];

  assert.ok(baseIndex >= 0);
  assert.ok(policyIndex > baseIndex);
  assert.ok(polishIndex > policyIndex);
  assert.equal(occurrences.length, 1);
});

test("protected frontend assets retain their fixed fingerprints", () => {
  const expected = {
    "styles.css": "ee6a5ae746142e32df768fe3261746f66c2b1a902e38b85fa9c0ecc4ce7bdc2a",
    "app.js": "9bf55162aff8d7a233804557c91605c801b92f515b2835978c05e2d1f3ef9210",
    "evidence_presentation.js": "9822b147c583d29fc7c6d4866d73a0015914e2971458239ab3d1d1c2ff39e409",
    "strict_canonical_json_v1.js": "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39",
  };

  for (const [fileName, fingerprint] of Object.entries(expected)) {
    assert.equal(sha256(fileName), fingerprint, fileName);
  }
});

test("calibration reading order and locked authority copy remain intact", () => {
  const stages = [...indexSource.matchAll(/data-calibration-stage="([^"]+)"/g)]
    .slice(0, 4)
    .map((match) => match[1]);

  assert.deepEqual(stages, ["source", "gap", "maturity", "permission"]);
  assert.match(indexSource, /id="platformAuthorityForbidden"[^>]*>模拟运行（未授权）· 实盘下单（永久硬锁）</);
  assert.match(indexSource, /研究通过不产生交易授权/);
});

test("polish layer is self-contained, responsive, and accessibility-aware", () => {
  assert.doesNotMatch(polishSource, /@import|url\s*\(/i);
  assert.doesNotMatch(polishSource, /\b(?:ready|profit|approved)\b/i);
  assert.match(polishSource, /:focus-visible/);
  assert.match(polishSource, /@media \(max-width: 760px\)/);
  assert.match(polishSource, /@media \(prefers-reduced-motion: reduce\)/);
  assert.match(polishSource, /@media \(forced-colors: active\)/);
  assert.match(polishSource, /data-calibration-stage="source"/);
  assert.match(polishSource, /data-calibration-stage="gap"/);
  assert.match(polishSource, /data-calibration-stage="maturity"/);
  assert.match(polishSource, /data-calibration-stage="permission"/);
  assert.equal(
    (polishSource.match(/{/g) || []).length,
    (polishSource.match(/}/g) || []).length,
  );
});
