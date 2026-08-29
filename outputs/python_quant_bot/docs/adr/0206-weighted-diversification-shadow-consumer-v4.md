# ADR 0206: Weighted diversification shadow consumer v4

Date: 2026-08-23

Status: accepted for an unmounted synthetic shadow fixture only

## Context

ADR 0205 added an exact projection-v4 and a neutral card-v4 for the weighted
effective-cluster gate. The presentation remained intentionally unmounted. A
same-input synthetic call proved the next boundary: a valid concentrated
projection-v4 with weighted effective cluster count `1.090722` is rejected by
the legacy v3 consumer as `UNKNOWN`, because that consumer is correctly pinned
to projection-v3 and card-v3.

The missing capability is not a browser mount or an HTTP route. It is a
versioned, pure consumer descriptor that proves the Python projection-v4 can be
rendered by the JavaScript card-v4 while retaining the authority lock and
without echoing raw source evidence.

## Decision

Add
`evidence_portfolio_risk_weighted_diversification_consumer_fixture_v4.js` as a
pure UMD/CommonJS shadow fixture. It performs no DOM, network, storage, server,
or runtime access and exposes no mount function.

The fixture accepts a projection only when all of the following are true:

- the card-v4 public API has the exact expected keys, schemas, fingerprints,
  stage order, builder, and renderer;
- the card-v4 verifier recomputes the projection seal with the existing
  synchronous UTF-8/SHA256 primitive and a projection-v4 schema-aware encoder
  that matches Python canonical JSON for its three declared floating fields;
- the projection-v4 schema, fingerprint, status, decision, hash shape, and
  authority map are exact;
- the card view-model has the exact summary-only shape and fixed
  `SOURCE -> GAP -> MATURITY -> PERMISSION` order;
- the permission stage remains `UNAUTHORIZED`;
- rendered markup has the expected card class, contains the permission lock,
  and contains no executable or event-handler markup.

Any mismatch returns a frozen `BLOCK/UNKNOWN` descriptor and safe fallback
markup. The descriptor never embeds the projection document, positions,
returns, correlation matrices, or upstream evidence.

## Seal and implementation identity

The card and consumer fingerprints advance to sealed-projection lock 2. The
consumer verifies the projection document seal but does not claim to verify the
implementation files that are executing. It therefore embeds no self-reported
implementation hash and explicitly reports
`implementation_hashes_runtime_verified: false`. Final artifact hashes belong
in independent validation evidence and a later registration successor, not in
the artifact that would be claiming its own identity.

## Consumer-first activation order

1. Prove the unmounted consumer fixture with Node unit contracts.
2. Prove the real Python projection-v4 to JavaScript card-v4 path with a
   cross-runtime synthetic contract.
3. Add a presentation registration successor that independently pins the
   projection, card, fixture, and cross-runtime contract artifacts.
4. Add separate execution evidence and independent review attestations.
5. Version any HTTP candidate separately while transport remains unregistered.
6. Require an explicit browser review before considering a mount.
7. Keep `current`, writers, registry admission, paper, and live authority locked
   unless separately authorized.

This ADR completes only steps 1 and 2. It does not activate steps 3 through 7.

## Adversarial matrix

- malformed projection returns `BLOCK/UNKNOWN`;
- replacing the projection seal with another valid 64-character hash returns
  `BLOCK/UNKNOWN`;
- card API drift returns `BLOCK/UNKNOWN` before renderer invocation;
- projection authority promotion returns `BLOCK/UNKNOWN`;
- stage reorder returns `BLOCK/UNKNOWN`;
- renderer or builder exceptions return `BLOCK/UNKNOWN`;
- executable markup returns `BLOCK/UNKNOWN` and is replaced by safe markup;
- context-spliced projection remains unknown across Python and Node;
- descriptors are deterministic, deeply frozen, unmounted, and summary-only.

## Non-claims

This synthetic shadow consumer is not browser evidence, visual QA, runtime
activation, natural-forward maturity, profitability evidence, paper/live
authorization, or permission to trade. The established natural-forward chain,
legacy pack-v5 behavior, and pointer-v2 contract remain unchanged.
