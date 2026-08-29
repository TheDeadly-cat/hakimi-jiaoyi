"use strict";

const projectionV2 = require("./evidence_anti_replay_registry_gap_projection_v2.js");

const CARD_SCHEMA_VERSION = "anti-replay-registry-gap-card-v2";
const CARD_STATIC_FINGERPRINT =
  "20260823-anti-replay-registry-identity-gap-card-v2-unmounted-lock-1";
const STAGE_ORDER = Object.freeze(["SOURCE", "GAP", "MATURITY", "PERMISSION"]);

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function shortHash(value) {
  return String(value).slice(0, 12) + "..." + String(value).slice(-6);
}

function buildAntiReplayRegistryGapViewModelV2(projection) {
  if (!projectionV2.verifyAntiReplayRegistryGapProjectionV2(projection)) {
    throw new TypeError("anti-replay registry gap projection-v2 is invalid");
  }
  return {
    eyebrow: "ANTI-REPLAY / ORGANIZATION EVIDENCE",
    footnote:
      "Six local signatures are observed. Process authenticity, evidence meaning, source trust, signer roles, revocation, and organization identity remain unverified.",
    gaps: projection.stages.gap.items.map((item, index) => ({
      index: String(index + 1).padStart(2, "0"),
      label: item.label,
      state: item.state,
    })),
    identity: {
      aggregate_hash: shortHash(projection.source.aggregation_hash),
      key_hash: shortHash(projection.source.public_key_spki_sha256),
      registry_id: projection.source.registry_id,
    },
    identity_ledger: projection.identity_evidence.ledger.map((item, index) => ({
      index: String(index + 1).padStart(2, "0"),
      label: item.label,
      state: item.state,
    })),
    lede:
      "Local key possession and six artifact signatures are hash-bound. The evidence still does not establish who operates the registry or whether external claims are trustworthy.",
    permission_locks: [
      "IDENTITY",
      "EVIDENCE",
      "CURRENT",
      "RUNTIME",
      "MOUNT",
      "PAPER",
      "LIVE",
      "WRITER",
    ],
    schema_version: CARD_SCHEMA_VERSION,
    stages: [
      {
        detail: "Key possession plus six signed artifact hashes",
        label: "SOURCE",
        state: "HASH-BOUND",
      },
      {
        detail: "Identity, source, semantics, process, and execution gaps",
        label: "GAP",
        state: "OPEN",
      },
      {
        detail: "Cryptographic observations remain local",
        label: "MATURITY",
        state: "LOCAL-CRYPTOGRAPHIC",
      },
      {
        detail: "No identity admission, route, mount, or trading path",
        label: "PERMISSION",
        state: "LOCKED",
      },
    ],
    static_fingerprint: CARD_STATIC_FINGERPRINT,
    status: "BLOCKED",
    status_label: "EVIDENCE GAP",
    title: "Registry identity evidence gap",
  };
}

function renderRows(rows) {
  return rows
    .map(
      (row) =>
        '<li class="ar-gap-card__gap-row">' +
        '<span class="ar-gap-card__gap-index">' +
        escapeHtml(row.index) +
        "</span>" +
        '<span class="ar-gap-card__gap-label">' +
        escapeHtml(row.label) +
        "</span>" +
        '<span class="ar-gap-card__gap-state">' +
        escapeHtml(row.state) +
        "</span>" +
        "</li>"
    )
    .join("");
}

function renderAntiReplayRegistryGapCardV2(projection) {
  const view = buildAntiReplayRegistryGapViewModelV2(projection);
  const stages = view.stages
    .map(
      (stage, index) =>
        '<li class="ar-gap-card__stage" data-stage="' +
        escapeHtml(stage.label) +
        '">' +
        '<span class="ar-gap-card__stage-index">0' +
        (index + 1) +
        "</span>" +
        '<span class="ar-gap-card__stage-label">' +
        escapeHtml(stage.label) +
        "</span>" +
        '<strong class="ar-gap-card__stage-state">' +
        escapeHtml(stage.state) +
        "</strong>" +
        '<span class="ar-gap-card__stage-detail">' +
        escapeHtml(stage.detail) +
        "</span>" +
        "</li>"
    )
    .join("");
  const locks = view.permission_locks
    .map(
      (lock) =>
        '<span class="ar-gap-card__lock">' +
        escapeHtml(lock) +
        " / LOCKED</span>"
    )
    .join("");
  return (
    '<article class="ar-gap-card" data-schema-version="' +
    escapeHtml(view.schema_version) +
    '" data-status="blocked">' +
    '<header class="ar-gap-card__header"><div>' +
    '<p class="ar-gap-card__eyebrow">' +
    escapeHtml(view.eyebrow) +
    "</p>" +
    '<h2 class="ar-gap-card__title">' +
    escapeHtml(view.title) +
    "</h2></div>" +
    '<span class="ar-gap-card__status">' +
    escapeHtml(view.status_label) +
    "</span></header>" +
    '<p class="ar-gap-card__lede">' +
    escapeHtml(view.lede) +
    "</p>" +
    '<dl class="ar-gap-card__identity">' +
    "<div><dt>REGISTRY</dt><dd>" +
    escapeHtml(view.identity.registry_id) +
    "</dd></div>" +
    "<div><dt>KEY HASH</dt><dd>" +
    escapeHtml(view.identity.key_hash) +
    "</dd></div>" +
    "<div><dt>AGGREGATE HASH</dt><dd>" +
    escapeHtml(view.identity.aggregate_hash) +
    "</dd></div></dl>" +
    '<ol class="ar-gap-card__stage-rail">' +
    stages +
    "</ol>" +
    '<section class="ar-gap-card__gap-panel" aria-label="Identity evidence ledger">' +
    '<div class="ar-gap-card__section-heading"><span>IDENTITY EVIDENCE LEDGER</span><strong>' +
    String(view.identity_ledger.length).padStart(2, "0") +
    "</strong></div>" +
    '<ol class="ar-gap-card__gap-list">' +
    renderRows(view.identity_ledger) +
    "</ol></section>" +
    '<section class="ar-gap-card__gap-panel" aria-label="Open system gaps">' +
    '<div class="ar-gap-card__section-heading"><span>OPEN SYSTEM GAP REGISTER</span><strong>' +
    String(view.gaps.length).padStart(2, "0") +
    "</strong></div>" +
    '<ol class="ar-gap-card__gap-list">' +
    renderRows(view.gaps) +
    "</ol></section>" +
    '<div class="ar-gap-card__locks" aria-label="Locked permissions">' +
    locks +
    "</div>" +
    '<footer class="ar-gap-card__footer">' +
    escapeHtml(view.footnote) +
    "</footer></article>"
  );
}

module.exports = {
  CARD_SCHEMA_VERSION,
  CARD_STATIC_FINGERPRINT,
  STAGE_ORDER,
  buildAntiReplayRegistryGapViewModelV2,
  renderAntiReplayRegistryGapCardV2,
};
