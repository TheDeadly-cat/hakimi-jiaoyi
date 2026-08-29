# ADR 0080: Factor-calibration precommit report consumer v6

## Status

Accepted as an unmounted aggregate-only consumer candidate. It is not an API, current-chain, scheduler, or UI activation decision.

## Context

Precommit v6 composes the frozen v5 precommit chain with residual-order gate v3. A public consumer must preserve the existing v5 consumer contract while exposing the new finite lag boundary. Reimplementing v5 public mapping without consuming its frozen artifact would create a parallel compatibility surface.

## Decision

Add a consumer v6 that:

- accepts and rebuilding-verifies both precommit v6 and report consumer v5;
- requires every document and expected hash needed by both source verifiers;
- cross-binds their v5, v2, v1, beta, replay, registration, and observations hashes;
- preserves v5 protocol metadata and public three-state semantics;
- maps a v3-induced v6 block to `VERIFIED_BLOCK` even when consumer v5 remains `VERIFIED_LOCAL_BINDING`;
- exposes `[1,2,3]`, maximum lag 3, one aggregate maximum, one ceiling, fold count, and unstable-identity count only;
- excludes rows, returns, betas, residuals, per-lag results, identities, and fold ledgers;
- keeps presentation mounting, current admission, paper, live, and profitability authority denied.

The consumer does not claim arbitrary-lag independence. Lags above 3 and external timing remain unresolved.

## Consumer-first activation order

1. Freeze and validate consumer v6.
2. Build a detached presentation envelope that consumes only consumer v6.
3. Build or revise a detached card after the envelope is frozen.
4. Consider any mounting or current admission through a separate explicit decision.

This ADR authorizes only step 1.

## Adversarial matrix

The targeted contract covers positive local binding, v3-induced block over a still-positive v5 consumer, v5 block, missing and unsupported sources, top-level and context expected hashes, coherently resealed v6 and v5-consumer tampering, context rebinding, exact three-lag aggregate projection, privacy, authority denial, determinism, consumer-verifier tampering, and exact schema/fingerprint registration.
