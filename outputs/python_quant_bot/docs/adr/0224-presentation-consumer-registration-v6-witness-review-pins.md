# ADR 0224: Presentation consumer registration-v6 witness and review pins

## Status

Accepted as a blocked static registration candidate.

## Context

Registration-v5 pins the receipt-v3 and evidence-v3 chain. It intentionally
leaves cryptographic witness verification and descriptor/load-order review
outside its manifest.

ADR 0222 adds a preregistered Ed25519 key-possession candidate. ADR 0223 adds
an unmounted descriptor, CSS, and dependency-order static review. Neither
artifact changes external authority or browser state.

## Decision

Introduce
strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v6.py
with an exact eleven-item manifest:

1. registration-v5.
2. strict-canonical Python.
3. strict-canonical JavaScript.
4. witness signature candidate implementation.
5. witness Node adversarial contract.
6. witness Python-to-Node contract.
7. ADR 0222.
8. descriptor review implementation.
9. descriptor review Node adversarial contract.
10. descriptor review Python-to-Node contract.
11. ADR 0223.

Registration-v6 exactly rebuilds registration-v5 and binds its dynamic hash.
It does not copy or modify the predecessor manifest.

## Status calibration

Registration-v6 remains permanently BLOCKED. An exact verifier PASS proves
only that the blocked registration document and its eleven static pins were
rebuilt exactly.

The local candidate closes three versioning gaps:

1. Preregistered key-possession verification is versioned.
2. Descriptor static review is versioned.
3. Dependency load-order static review is versioned.

These blockers remain:

1. External witness policy registry and organization identity are unbound.
2. Independent execution-process witnessing and shared anti-replay checking
   are unverified.
3. Browser visual review is unperformed.
4. Production route, mount, and activation remain unauthorized.

## Adversarial matrix

1. The expected manifest must contain exactly eleven pins.
2. The registration-v5 dynamic hash must be rebuilt and bound.
3. Witness and descriptor-review schemas and implementations are explicit.
4. Missing, extra, and substituted manifest values fail closed.
5. An exact blocked registration verifies exactly.
6. A valid document with a wrong manifest fails.
7. A resealed authority promotion fails exact verification.
8. Key possession remains distinct from external identity.
9. Static review remains distinct from browser review and mounting.
10. Activation order keeps all external and browser steps later.
11. No profitability, current, writer, paper, live, or mount authority exists.

All validation is synthetic or in-memory. No external key, secret, runtime
store, database, cache, log, service, browser, scheduler, market task, or
trading path is used.

## Activation order

1. registration-v5 receipt/evidence chain.
2. witness signature key-possession candidate.
3. descriptor and load-order static review.
4. registration-v6 static candidate.
5. future external policy registry and witness identity.
6. future independent process witness and shared anti-replay.
7. future explicit browser visual review.
8. separate explicit production route or mount decision.

This ADR authorizes only step 4.
