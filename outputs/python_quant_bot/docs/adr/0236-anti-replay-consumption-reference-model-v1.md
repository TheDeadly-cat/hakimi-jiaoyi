# ADR 0236: Anti-replay consumption reference model-v1

## Status

Accepted as a blocked, pure, synthetic state-transition reference model.

## Context

ADR0235 verifies local Ed25519 key possession for an exact witness-v2 document,
but it intentionally rejects any claimed anti-replay consumption receipt. The
next consumer needs exact first-seen, duplicate, and same-scope conflict
semantics before an external registry adapter can be evaluated.

A local mutable map would be misleading. It could demonstrate branch-local
behavior but could not prove cross-process atomicity, durable compare-and-set,
registry identity, trusted time, or rollback resistance. It must not be named or
treated as the target consumption receipt-v1.

## Decision

Add four source-level contracts:

1. a sealed consumption request-v1 derived only from an exact PASS rebuild of a
   locally valid, still-BLOCKED witness-v2 verification document;
2. a sealed, immutable reference state-v1 with canonical key ordering;
3. a pure deterministic reducer with `REFERENCE_FIRST_SEEN`,
   `REFERENCE_DUPLICATE_REJECTED`, and `REFERENCE_CONFLICT_REJECTED` outcomes;
4. a public exact-rebuild verifier for the state and observation pair.

The consumption key binds the exact anti-replay namespace and scope hash. The
request also binds witness verification, policy, challenge, attestation,
issuance preregistration, witness id, and preregistered public-key hashes. It
contains no raw nonce, detached signature, public-key material, timestamp, or
private-key material.

An exact transition verifier may return PASS. That means only that the pure
reference transition was reproduced exactly. Every request and observation
remains BLOCKED, and every result states that external linearizability, atomic
nonce consumption, registry identity, trusted time, and target receipt issuance
are false.

## Adversarial matrix

- exact first-seen updates a sealed reference state once;
- exact replay is rejected without a state revision;
- a different request under the same scope is rejected as conflict;
- different scopes remain independent and canonically ordered;
- schema aliases, resealed authority drift, state rollback, entry tampering,
  next-state tampering, and observation tampering fail closed;
- two branch-local applications may both report first-seen, explicitly proving
  that the reference model cannot establish shared external linearizability;
- `CLEAR`, `TAIL_BLOCK`, and `EXACT_UNKNOWN` remain distinct and blocked.

## Consumer-first order

1. blocked witness-v2 and exact local signature verification;
2. consumption request and pure reference transition-v1;
3. independently governed external registry identity preregistration;
4. linearizable adapter with atomic compare-and-consume and duplicate evidence;
5. signed target consumption receipt-v1 with trusted registry time;
6. independently governed witness identity and process observation;
7. post-registration receipt-v5 and Python evidence;
8. explicit browser review and separate activation decision.

## Consequences

- Duplicate and conflict semantics are now executable without pretending that a
  process-local model is a durable registry.
- The target `portfolio-risk-post-registration-anti-replay-consumption-receipt-v1`
  schema is referenced but never emitted.
- Existing witness, preregistration, evidence, receipt, projection, current,
  pointer-v2, and natural-forward artifacts remain unchanged.
- No filesystem state, runtime asset, database, cache, log, network, service,
  browser, scheduler, market task, private key, or trading path is used.
- The reference model is not identity, linearizability, atomicity, profitability,
  receipt, current, runtime, paper/live, route, mount, migration, or writer
  authority.
