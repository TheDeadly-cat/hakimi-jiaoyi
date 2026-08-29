# ADR 0388: Registration challenge clock-attestation binding v1

## Status

Accepted as an isolated, pure synthetic adapter. It is not mounted into current and grants no runtime or trading authority.

## Context

ADR0387 proves that a preregistered challenge key signed an exact challenge containing a declared issue/expiry window. It does not prove that either timestamp came from a trusted clock or that the challenge is fresh.

The existing trusted-clock-authority-v3 contract already verifies an exact multi-authority Ed25519 receipt quorum while explicitly keeping external authority trust, registration governance, the supplied verification-time source, nonce uniqueness, replay absence, and current time unproved. Reimplementing its signature protocol would create a duplicate trust boundary.

## Decision

Add a narrow adapter that rebuilds both upstream contracts and requires:

1. The ADR0387 challenge evidence is exact and verifies the preregistered challenge-source signature.
2. trusted-clock-authority-v3 rebuilds the exact attestation from caller-supplied registration, receipts, public keys, expected hashes, and verification-time claim.
3. The clock request context equals the ADR0387 signed-challenge hash.
4. The clock request nonce equals the challenge registration-nonce hash.
5. The signed multi-authority reference-time observation lies inside the challenge's declared issue/expiry window.

A local PASS states only that signed multi-authority observations are cryptographically and structurally bound to the exact signed challenge. It must keep all of these false:

- external time-authority trust and registration governance
- trust in the caller-supplied verification-time source
- current-time establishment and challenge freshness
- nonce uniqueness, replay absence, and challenge consumption
- provider registration, current activation, paper, live, and writer authority

The adapter emits only a redacted projection. It does not expose receipts, public keys, or signatures and does not accept private keys or access files, clocks, network, storage, runtime assets, services, browsers, or schedulers.

## Consumer-first activation order

1. Keep ADR0388 isolated and prove exact context, nonce, and declared-window binding synthetically.
2. Independently establish external clock-authority governance and key lifecycle.
3. Replace the caller-supplied verification-time claim with an independently trusted verification-time source.
4. Atomically consume the exact signed-challenge hash through a durable replay/CAS provider.
5. Only then consider a versioned current consumer change under separate authorization.

## Adversarial matrix

Tests cover context and nonce substitution, valid clock observations outside the challenge window, receipt-signature tampering, re-sealed current-time promotion, challenge-evidence promotion, expected-hash drift, evidence mutation, material redaction, bool-as-int verification-time aliases, determinism, input immutability, and forbidden production capabilities.

## Consequences

This closes a local cross-contract binding gap but still does not establish trusted current time or freshness. Multi-authority signatures alone do not prevent replay. The natural-forward chain, legacy pack-v5 UNKNOWN behavior, pointer-v2, and neutral SOURCE -> GAP -> MATURITY -> PERMISSION UI remain unchanged.
