# ADR 0400: Genesis Replay Reservation Provider Registration Clock Binding v1

- Status: Accepted for isolated synthetic research only
- Date: 2026-08-24
- Supersedes: nothing
- Activates current: no

## Context

ADR0399 closes the exact challenge and nonce substitution gap with a source signature and provider signature. Its local PASS intentionally leaves current time and challenge freshness false. Reusing a caller-supplied integer as authoritative time would collapse observation, trust, and authorization into one boundary.

ADR0394 already defines a fail-closed consumer pattern for trusted_clock_authority_v3. The new reservation-provider chain needs the same semantics without importing the old provider identity or changing ADR0399.

## Decision

Add an isolated ADR0400 consumer that rebuilds the complete ADR0399 handoff and verifies a strict trusted_clock_authority_v3 attestation. Local binding PASS requires all of the following:

- the ADR0399 handoff document and expected hash rebuild exactly;
- both source and provider signature facts remain exact;
- the clock registration, registered key hashes, detached signatures, and quorum rebuild exactly;
- the clock request_context_hash equals the signed registration challenge hash;
- the clock request_nonce_hash equals the registration nonce hash;
- the clock reference observation falls inside the challenge's declared issue and expiry window.

The caller-provided verification time is only an input to cryptographic contract reconstruction. It is not promoted to trusted current time.

## Consumer-first activation order

1. Keep ADR0397 through ADR0399 immutable as producer evidence.
2. Add ADR0400 only as an isolated consumer of exact handoff and clock documents.
3. Require a separate governance boundary for clock authority identity and registration continuity.
4. Require a separate trusted verification-time source and replay registry before any freshness conclusion.
5. Do not switch current, reissue pointer-v2, register the provider, or grant paper/live/writer authority in this ADR.

## Adversarial matrix

Fourteen focused cases cover local binding, wrong context, wrong nonce, out-of-window reference time, independently valid wrong provider challenge, receipt signature tampering, resealed current-time promotion, forged handoff freshness, expected-hash drift, verifier mutation, raw-material redaction, determinism and input immutability, boolean verification-time aliasing, and absence of private-key/I/O/system-clock/runtime access in production code.

## Consequences

- Signed clock observations can be associated with the exact ADR0399 dual-signature handoff without treating them as trusted current time.
- External time-authority trust, clock registration governance, verification-time trust, nonce uniqueness, clock replay protection, challenge freshness, registration replay consumption, provider registration, external conformance, profitability, current activation, paper, live, and writer authority remain unproved or unauthorized.
- The natural-forward public chain remains audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2.
- Legacy pack-v5 public reads remain UNKNOWN, and pointer-v2 is not reissued.
