# ADR 0394: Challenge-consumption provider registration clock binding v1

## Status

Accepted as an isolated, pure synthetic clock-attestation adapter. It is not mounted into current, does not consume a challenge, and grants no runtime or trading authority.

## Context

ADR0393 proves an exact dual-signature handoff between a source-signed registration challenge and the ADR0392 provider-signed claim. Its issued and expiry times are still declarations. ADR0388 cannot be reused directly because it is exact-bound to the replay-cursor provider challenge schemas and implementation hash.

Reimplementing trusted-clock-authority-v3 would duplicate a cryptographic trust boundary. Verifying only a clock attestation would also be insufficient because an otherwise valid attestation could be paired with a different provider registration handoff.

## Decision

Add a specialized adapter that:

1. Rebuilds the exact ADR0393 handoff, including both preregistered key signatures.
2. Rebuilds trusted-clock-authority-v3 from caller-supplied registration, receipts, public keys, expected hashes, and verification-time claim.
3. Requires clock request context to equal the ADR0393 signed-challenge hash.
4. Requires clock request nonce to equal the end-to-end registration nonce.
5. Requires the signed multi-authority reference-time observation to lie inside the challenge's declared issue and expiry window.

A local PASS proves only cryptographic and structural binding of signed time observations to the exact dual-signature handoff. External time-authority trust, registration governance, trust in caller-supplied verification time, current time, freshness, nonce uniqueness, replay absence, consumption, provider registration, and external conformance remain false.

Production code accepts only public verification material. It has no private keys, system-clock reads, provider call, file, network, storage, runtime assets, service startup, browser, or scheduler.

## Consumer-first activation order

1. Keep ADR0394 isolated and preserve all current consumers.
2. Independently establish external clock-authority governance and key lifecycle.
3. Replace caller-supplied verification time with an independently trusted current-time source.
4. Design a non-circular bootstrap authority for consuming the consumption provider's own registration challenge.
5. Prove durable consume-once before running ADR0391 external conformance.
6. Consider a versioned current consumer change only under separate authorization.

## Adversarial matrix

Tests cover wrong context, wrong nonce, reference time outside the declared window, independently valid but mismatched provider claims, receipt-signature tampering, re-sealed current-time promotion, handoff freshness promotion, expected-hash drift, evidence mutation, raw-material redaction, bool-as-int time aliases, determinism, input immutability, and forbidden production capabilities.

## Consequences

ADR0394 closes the signed-clock-observation binding gap without claiming current time or freshness. It does not create a replay registry, consume-once proof, external provider, profitability evidence, or trading permission. The natural-forward chain, legacy pack-v5 UNKNOWN behavior, pointer-v2 fields and hashes, and neutral SOURCE -> GAP -> MATURITY -> PERMISSION UI remain unchanged.
