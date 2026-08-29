# ADR 0399: Genesis Replay Reservation Provider Registration Challenge Handoff v1

- Status: Accepted for isolated synthetic research only
- Date: 2026-08-24
- Supersedes: nothing
- Activates current: no

## Context

ADR0397 preregisters the external replay-reservation provider contract, and ADR0398 proves possession of the preregistered provider key. That proof still accepts caller-supplied challenge and nonce hashes without independently proving challenge source authority or exact pairing. Treating the provider signature alone as registration would leave a cross-document substitution gap.

A pure synthetic gap probe established the missing boundary: provider key signature verification can pass while challenge source authority, freshness, replay consumption, and provider registration remain false.

## Decision

Add an isolated source-signed registration challenge and a dual-signature handoff. The source contract:

- preregisters an Ed25519 challenge authority identity and key hash;
- builds an exact bounded-lifetime challenge bound to the ADR0397 provider preregistration;
- signs the strict-canonical challenge hash;
- verifies only local key possession and exact document reconstruction.

The handoff rebuilds both source-signature and provider-signature evidence and requires exact equality across:

- provider preregistration hash;
- signed challenge hash used by the provider registration claim;
- registration nonce hash;
- both evidence hashes and strict-canonical documents.

An independently valid provider signature for another challenge or nonce is rejected. Local handoff PASS means only that the synthetic dual-signature binding is exact.

## Consumer-first activation order

1. Keep ADR0397 and ADR0398 unchanged as producer contracts.
2. Introduce ADR0399 source evidence without wiring any runtime consumer.
3. Introduce ADR0399 handoff evidence and adversarial tests.
4. Permit a future consumer only after trusted clock, freshness, replay consumption, provider identity, implementation continuity, and external conformance contracts exist.
5. Do not switch current, reissue pointer-v2, or grant paper/live/writer authority in this ADR.

## Adversarial matrix

The targeted matrix covers twelve ADR0399 cases: exact blocked preregistration/challenge, valid local handoff, valid wrong challenge, valid wrong nonce, wrong authority key, tampered signature, resealed freshness promotion, extra fields and preregistration drift, boolean time and excessive lifetime, verifier mutation, raw-material redaction and input immutability, and absence of private-key/I/O/clock/runtime dependencies in production modules.

## Consequences

- The caller-supplied challenge substitution gap is closed for this isolated synthetic chain.
- Trusted time, challenge freshness, replay consumption, provider registration, provider identity, implementation continuity, external atomicity/durability/linearizability, profitability, current activation, paper, live, and writer authority remain unproved or unauthorized.
- The natural-forward public chain remains audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2.
- Legacy pack-v5 public reads remain UNKNOWN, and pointer-v2 is not reissued.
