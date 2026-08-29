"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const indexSource = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const stylesSource = fs.readFileSync(path.join(__dirname, "styles.css"), "utf8");

function openingDivsWithClass(source, className) {
  const matches = [];
  const openingDivPattern = /<div\b[^>]*\bclass=(['"])(.*?)\1[^>]*>/gis;

  for (const match of source.matchAll(openingDivPattern)) {
    const classes = match[2].trim().split(/\s+/);
    if (classes.includes(className)) {
      matches.push({ index: match.index, tag: match[0] });
    }
  }

  return matches;
}

function extractBalancedDiv(source, openingIndex) {
  const divPattern = /<\/?div\b[^>]*>/gi;
  divPattern.lastIndex = openingIndex;
  let depth = 0;

  for (let match = divPattern.exec(source); match; match = divPattern.exec(source)) {
    if (/^<div\b/i.test(match[0])) {
      depth += 1;
      continue;
    }

    depth -= 1;
    if (depth === 0) {
      return source.slice(openingIndex, divPattern.lastIndex);
    }
  }

  throw new Error("evidence calibration rail is not a balanced div");
}

test("calibration rail preserves the neutral evidence reading sequence", () => {
  const railOpenings = openingDivsWithClass(indexSource, "evidence-calibration-rail");
  assert.equal(railOpenings.length, 1);

  const rail = extractBalancedDiv(indexSource, railOpenings[0].index);
  const stages = Array.from(
    rail.matchAll(/\bdata-calibration-stage=(['"])(.*?)\1/gi),
    (match) => match[2],
  );

  assert.deepEqual(stages, ["source", "gap", "maturity", "permission"]);
  assert.match(
    railOpenings[0].tag,
    /\baria-labelledby=(['"])evidenceCalibrationTitle\1/,
  );
  assert.match(
    railOpenings[0].tag,
    /\baria-describedby=(['"])evidenceCalibrationNote\1/,
  );
  assert.match(rail, /<strong\s+id=(['"])evidenceCalibrationTitle\1>/);
  assert.match(rail, /<small\s+id=(['"])evidenceCalibrationNote\1>/);
  assert.match(rail, /<ol\s+aria-label=(['"])证据校准四步阅读顺序\1>/);
  assert.match(rail, /阅读顺序\s*·\s*非就绪评分/);

  const expectedCopy = [
    "01 · SOURCE",
    "先核对来源",
    "来源、时点、归属",
    "02 · GAP",
    "再保留缺口",
    "未知项不得被补写",
    "03 · MATURITY",
    "单独评估成熟度",
    "样本与证据链分开核验",
    "04 · PERMISSION",
    "最后判定权限",
    "研究通过不产生交易授权",
  ];
  for (const copy of expectedCopy) {
    assert.ok(rail.includes(copy), `missing calibration copy: ${copy}`);
  }

  assert.doesNotMatch(rail, /\bREADY\b|盈利证明|交易已授权|模拟已授权|实盘已授权/);

  const ids = Array.from(
    indexSource.matchAll(/\bid=(['"])(.*?)\1/gi),
    (match) => match[2],
  );
  assert.equal(new Set(ids).size, ids.length, "HTML ids must remain unique");
});

test("calibration styles remain scoped without displacing legacy media contracts", () => {
  const scopeMarker = ".platform-control-center.evidence-calibrated {";
  const scopeIndex = stylesSource.indexOf(scopeMarker);
  assert.notEqual(scopeIndex, -1);

  const calibrationStyles = stylesSource.slice(scopeIndex);
  for (const width of [960, 720, 480]) {
    assert.ok(
      calibrationStyles.includes(`@media screen and (max-width: ${width}px)`),
      `missing scoped ${width}px calibration breakpoint`,
    );
  }

  const legacyMedia = Array.from(
    stylesSource.matchAll(/@media \(max-width: (?:720|480)px\)/g),
  );
  assert.ok(legacyMedia.length > 0, "expected pre-existing exact media contracts");
  assert.ok(
    legacyMedia.every((match) => match.index < scopeIndex),
    "calibration styles must not append an exact legacy media contract",
  );
  assert.doesNotMatch(calibrationStyles, /@media \(max-width: (?:960|720|480)px\)/);
  assert.match(
    calibrationStyles,
    /\.evidence-calibrated button:focus-visible\s*,\s*\.evidence-calibrated summary:focus-visible/,
  );
  assert.match(calibrationStyles, /@media \(prefers-reduced-motion: reduce\)/);
  assert.match(calibrationStyles, /@media \(forced-colors: active\)/);
  assert.match(
    calibrationStyles,
    /\.evidence-calibration-rail li::after[\s\S]*background:\s*CanvasText/,
  );
});

test("calibration stylesheet cache version remains isolated from production scripts", () => {
  assert.equal(
    (indexSource.match(/styles\.css\?v=20260822-evidence-calibration-rail-2/g) || []).length,
    1,
  );
  assert.equal(
    (indexSource.match(/20260822-evidence-calibration-rail-2/g) || []).length,
    1,
  );
  assert.equal(
    (indexSource.match(/20260821-correlation-multiplicity-ledger-1/g) || []).length,
    2,
  );
  assert.match(
    indexSource,
    /evidence_presentation\.js\?v=20260821-correlation-multiplicity-ledger-1/,
  );
  assert.match(indexSource, /app\.js\?v=20260821-correlation-multiplicity-ledger-1/);
});
