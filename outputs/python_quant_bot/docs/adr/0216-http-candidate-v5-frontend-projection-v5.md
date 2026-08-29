# ADR 0216: HTTP candidate-v5 frontend projection-v5

## Status

Accepted as a synthetic, summary-only, unmounted Python projection. It is not a JavaScript consumer, DOM renderer, route, mount, or activation record.

## Context

Projection-v4 directly consumes adapter-v4 and predates presentation HTTP candidate-v5. Candidate-v5 emits a separate response-v5 schema containing exactly verified preregistration and adapter-v5 joint-risk evidence.

A pure synthetic cross-schema call established the gap with `6/6` assertions:

- candidate-v5 response is exactly verified;
- response-v5 is not adapter-v4;
- projection-v4 exposes no candidate-v5 input;
- projection-v4 correctly returns `BLOCK/UNKNOWN` for response-v5;
- projection-v4 does not claim an adapter-v4 decision for that input;
- projection-v4 does not expose `adapter_v5_hash`.

Widening projection-v4 would break its immutable adapter-v4 contract and card-v4 lineage.

## Decision

Add projection-v5 as a separate summary-only consumer.

Projection-v5:

1. accepts candidate-v5 response plus one exact verification context;
2. calls the public candidate-v5 exact verifier;
3. independently checks schema, seal, transport, authority, stage order, hash lineage, and calibrated facts;
4. maps candidate `axis` entries to stable frontend projection `key` entries;
5. preserves `SOURCE -> GAP -> MATURITY -> PERMISSION`;
6. preserves adapter-v5 `PASS/BLOCK` as local research evidence while the projection remains `BLOCK` and permission remains unauthorized;
7. exposes only hashes, blocker summaries, joint-risk facts, and neutral stage descriptions;
8. never embeds request documents, verification contexts, positions, or correlation matrices;
9. pins candidate-v5 and strict-canonical implementations by SHA256;
10. seals every result and verifies only an exact deterministic rebuild.

Invalid, aliased, tampered, promoted, or unverifiable source evidence projects to `UNKNOWN_SOURCE` with permission still unauthorized.

## Consumer-first order

1. Keep projection-v5 synthetic and unmounted.
2. Complete targeted and independent adversarial review.
3. Version a separate static JavaScript card/consumer for projection-v5.
4. Review its descriptor and dependency order without mounting.
5. Separately authorize DOM and browser review.
6. Separately authorize route, registration, mount, and `current` only after all preceding evidence is closed.

## Consequences

- projection-v4 and its card-v4/consumer-v4 chain remain immutable.
- candidate-v5 is now consumable by a Python presentation projection, but not by frontend JavaScript or a runtime route.
- Adapter-v5 `PASS` remains a local research fact, not readiness, profitability, or permission.
- Adapter-v5 `BLOCK` remains a visible gap and is not collapsed into a false source failure.

## Non-goals

- No JavaScript or stylesheet artifact.
- No HTTP route, DOM target, selector, browser, or mount.
- No runtime, cache, database, provider, scheduler, paper, live, or order access.
- No return backtest or profitability claim.
- No registration activation, `current` switch, pack publication, or pointer reissue.
