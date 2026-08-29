"use strict";

const {
  sealDocument,
  strictCanonicalHash,
  verifySealedDocument,
} = require("./strict_canonical_json_v1.js");
const projectionV2 = require("./evidence_anti_replay_registry_gap_projection_v2.js");
const cardV2 = require("./evidence_anti_replay_registry_gap_card_v2.js");

const FIXTURE_SCHEMA_VERSION =
  "anti-replay-registry-gap-presentation-consumer-fixture-v2";
const FIXTURE_STATIC_FINGERPRINT =
  "20260823-anti-replay-registry-identity-gap-consumer-v2-unmounted-lock-1";
const STYLESHEET_ASSET = "evidence_anti_replay_registry_gap_card_v1.css";
const STYLESHEET_IMPLEMENTATION_SHA256 =
  "8df1da62171147843bc655f07c79090d1176d16a8b3186c4f83390e3e02e08ad";
const AUTHORITY_KEYS = [
  "current_admission_allowed",
  "evidence_bundle_admission_allowed",
  "live_order_allowed",
  "paper_authorized",
  "presentation_mount_allowed",
  "registry_identity_admission_allowed",
  "runtime_gate_activation_allowed",
  "writer_allowed",
];

function lockedAuthority() {
  return Object.fromEntries(AUTHORITY_KEYS.map((key) => [key, false]));
}

function buildAntiReplayRegistryGapPresentationConsumerFixtureV2(projection) {
  if (!projectionV2.verifyAntiReplayRegistryGapProjectionV2(projection)) {
    throw new TypeError("anti-replay registry gap projection-v2 is invalid");
  }
  const viewModel = cardV2.buildAntiReplayRegistryGapViewModelV2(projection);
  return sealDocument(
    {
      authority: lockedAuthority(),
      blockers: [
        "ROUTE_NOT_BOUND",
        "MOUNT_SELECTOR_NOT_BOUND",
        "APP_IMPORT_NOT_BOUND",
        "BROWSER_REVIEW_NOT_PERFORMED",
        "REGISTRY_ORGANIZATION_IDENTITY_GAPS_REMAIN",
      ],
      facts: {
        app_imported: false,
        browser_visual_review_performed: false,
        mounted: false,
        route_bound: false,
        stylesheet_reused_without_modification: true,
        stylesheet_scoped: true,
        v1_assets_modified: false,
      },
      html: cardV2.renderAntiReplayRegistryGapCardV2(projection),
      schema_version: FIXTURE_SCHEMA_VERSION,
      source: {
        card_schema_version: cardV2.CARD_SCHEMA_VERSION,
        card_static_fingerprint: cardV2.CARD_STATIC_FINGERPRINT,
        projection_hash: projection.projection_hash,
        projection_schema_version: projectionV2.PROJECTION_SCHEMA_VERSION,
        projection_static_fingerprint: projectionV2.PROJECTION_STATIC_FINGERPRINT,
        stylesheet_asset: STYLESHEET_ASSET,
        stylesheet_implementation_sha256:
          STYLESHEET_IMPLEMENTATION_SHA256,
      },
      stage_order: [...projectionV2.STAGE_ORDER],
      static_fingerprint: FIXTURE_STATIC_FINGERPRINT,
      status: "UNMOUNTED",
      view_model: viewModel,
    },
    "fixture_hash"
  );
}

function verifyAntiReplayRegistryGapPresentationConsumerFixtureV2(
  projection,
  fixture
) {
  try {
    const expected = buildAntiReplayRegistryGapPresentationConsumerFixtureV2(
      projection
    );
    const exact =
      verifySealedDocument(fixture, "fixture_hash") &&
      strictCanonicalHash(fixture) === strictCanonicalHash(expected);
    return {
      blockers: exact ? [] : ["ANTI_REPLAY_REGISTRY_GAP_FIXTURE_V2_EXACT_REBUILD"],
      browser_visual_review_performed: false,
      current_admission_allowed: false,
      evidence_bundle_admission_allowed: false,
      fixture_document_exactly_rebuilt: exact,
      fixture_status: exact ? "UNMOUNTED" : "UNKNOWN",
      live_order_allowed: false,
      mounted: false,
      paper_authorized: false,
      presentation_mount_allowed: false,
      registry_identity_admission_allowed: false,
      route_bound: false,
      runtime_gate_activation_allowed: false,
      schema_version:
        "anti-replay-registry-gap-presentation-consumer-fixture-v2-exact-rebuild-v1",
      status: exact ? "PASS" : "BLOCK",
      writer_allowed: false,
    };
  } catch (_error) {
    return {
      blockers: ["ANTI_REPLAY_REGISTRY_GAP_FIXTURE_V2_INPUT_INVALID"],
      browser_visual_review_performed: false,
      current_admission_allowed: false,
      evidence_bundle_admission_allowed: false,
      fixture_document_exactly_rebuilt: false,
      fixture_status: "UNKNOWN",
      live_order_allowed: false,
      mounted: false,
      paper_authorized: false,
      presentation_mount_allowed: false,
      registry_identity_admission_allowed: false,
      route_bound: false,
      runtime_gate_activation_allowed: false,
      schema_version:
        "anti-replay-registry-gap-presentation-consumer-fixture-v2-exact-rebuild-v1",
      status: "BLOCK",
      writer_allowed: false,
    };
  }
}

module.exports = {
  FIXTURE_SCHEMA_VERSION,
  FIXTURE_STATIC_FINGERPRINT,
  STYLESHEET_ASSET,
  STYLESHEET_IMPLEMENTATION_SHA256,
  buildAntiReplayRegistryGapPresentationConsumerFixtureV2,
  verifyAntiReplayRegistryGapPresentationConsumerFixtureV2,
};
