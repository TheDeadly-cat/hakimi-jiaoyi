"use strict";

const {
  sealDocument,
  strictCanonicalHash,
  verifySealedDocument,
} = require("./strict_canonical_json_v1.js");
const projectionV1 = require("./evidence_anti_replay_registry_gap_projection_v1.js");
const cardV1 = require("./evidence_anti_replay_registry_gap_card_v1.js");

const FIXTURE_SCHEMA_VERSION =
  "anti-replay-registry-gap-presentation-consumer-fixture-v1";
const FIXTURE_STATIC_FINGERPRINT =
  "20260823-anti-replay-registry-gap-consumer-v1-unmounted-lock-1";
const STYLESHEET_ASSET = "evidence_anti_replay_registry_gap_card_v1.css";
const AUTHORITY_KEYS = [
  "current_admission_allowed",
  "live_order_allowed",
  "paper_authorized",
  "presentation_mount_allowed",
  "runtime_gate_activation_allowed",
  "writer_allowed",
];

function lockedAuthority() {
  return Object.fromEntries(AUTHORITY_KEYS.map((key) => [key, false]));
}

function buildAntiReplayRegistryGapPresentationConsumerFixtureV1(projection) {
  if (!projectionV1.verifyAntiReplayRegistryGapProjectionV1(projection)) {
    throw new TypeError("anti-replay registry gap projection-v1 is invalid");
  }
  const viewModel = cardV1.buildAntiReplayRegistryGapViewModelV1(projection);
  return sealDocument(
    {
      authority: lockedAuthority(),
      blockers: [
        "ROUTE_NOT_BOUND",
        "MOUNT_SELECTOR_NOT_BOUND",
        "APP_IMPORT_NOT_BOUND",
        "BROWSER_REVIEW_NOT_PERFORMED",
        "EXTERNAL_REGISTRY_EVIDENCE_GAPS_REMAIN",
      ],
      facts: {
        app_imported: false,
        browser_visual_review_performed: false,
        mounted: false,
        route_bound: false,
        stylesheet_scoped: true,
      },
      html: cardV1.renderAntiReplayRegistryGapCardV1(projection),
      schema_version: FIXTURE_SCHEMA_VERSION,
      source: {
        card_schema_version: cardV1.CARD_SCHEMA_VERSION,
        card_static_fingerprint: cardV1.CARD_STATIC_FINGERPRINT,
        projection_hash: projection.projection_hash,
        projection_schema_version: projectionV1.PROJECTION_SCHEMA_VERSION,
        projection_static_fingerprint: projectionV1.PROJECTION_STATIC_FINGERPRINT,
        stylesheet_asset: STYLESHEET_ASSET,
      },
      stage_order: [...projectionV1.STAGE_ORDER],
      static_fingerprint: FIXTURE_STATIC_FINGERPRINT,
      status: "UNMOUNTED",
      view_model: viewModel,
    },
    "fixture_hash"
  );
}

function verifyAntiReplayRegistryGapPresentationConsumerFixtureV1(
  projection,
  fixture
) {
  try {
    const expected = buildAntiReplayRegistryGapPresentationConsumerFixtureV1(
      projection
    );
    const exact =
      verifySealedDocument(fixture, "fixture_hash") &&
      strictCanonicalHash(fixture) === strictCanonicalHash(expected);
    return {
      blockers: exact ? [] : ["ANTI_REPLAY_REGISTRY_GAP_FIXTURE_EXACT_REBUILD"],
      browser_visual_review_performed: false,
      current_admission_allowed: false,
      fixture_document_exactly_rebuilt: exact,
      fixture_status: exact ? "UNMOUNTED" : "UNKNOWN",
      live_order_allowed: false,
      mounted: false,
      paper_authorized: false,
      presentation_mount_allowed: false,
      route_bound: false,
      runtime_gate_activation_allowed: false,
      schema_version:
        "anti-replay-registry-gap-presentation-consumer-fixture-exact-rebuild-v1",
      status: exact ? "PASS" : "BLOCK",
      writer_allowed: false,
    };
  } catch (_error) {
    return {
      blockers: ["ANTI_REPLAY_REGISTRY_GAP_FIXTURE_INPUT_INVALID"],
      browser_visual_review_performed: false,
      current_admission_allowed: false,
      fixture_document_exactly_rebuilt: false,
      fixture_status: "UNKNOWN",
      live_order_allowed: false,
      mounted: false,
      paper_authorized: false,
      presentation_mount_allowed: false,
      route_bound: false,
      runtime_gate_activation_allowed: false,
      schema_version:
        "anti-replay-registry-gap-presentation-consumer-fixture-exact-rebuild-v1",
      status: "BLOCK",
      writer_allowed: false,
    };
  }
}

module.exports = {
  FIXTURE_SCHEMA_VERSION,
  FIXTURE_STATIC_FINGERPRINT,
  STYLESHEET_ASSET,
  buildAntiReplayRegistryGapPresentationConsumerFixtureV1,
  verifyAntiReplayRegistryGapPresentationConsumerFixtureV1,
};
