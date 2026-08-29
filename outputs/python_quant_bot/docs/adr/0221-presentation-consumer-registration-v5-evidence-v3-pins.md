# ADR 0221: Presentation consumer registration-v5 evidence-v3 pins

## Status

Accepted as a blocked static registration candidate.

## Context

Registration-v4 pins projection-v5, card-v5, stylesheet-v5, consumer-v5, and
their static verification artifacts. It intentionally leaves consumer-v5
execution receipt and independent execution evidence unversioned.

ADR 0219 introduced receipt-v3 for local Node execution observation. ADR 0220
introduced evidence-v3 for Python strict-canonical and cross-document
verification. Registration-v4 has no manifest keys for those artifacts, so it
cannot be reinterpreted as their registration.

## Decision

Introduce
strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v5.py
as a new blocked registration candidate.

Registration-v5 pins nine artifacts:

1. The registration-v4 implementation.
2. The Python strict-canonical implementation.
3. The receipt-v3 JavaScript implementation.
4. The receipt-v3 Node contract.
5. The receipt-v3 Python-to-Node contract.
6. ADR 0219.
7. The evidence-v3 Python implementation.
8. The evidence-v3 adversarial contract.
9. ADR 0220.

Registration-v5 also rebuilds an exact registration-v4 document and binds its
dynamic registration hash. This preserves the full frontend-v5 predecessor
chain without copying its manifest into a second mutable boundary.

The supplied nine-item manifest must have exact keys and exact SHA-256 values.
Missing, extra, or substituted values fail closed. The raw supplied manifest
is not embedded in the result, and the builder performs no file read or
artifact execution.

## Status calibration

The registration status is permanently BLOCKED in this candidate. A verifier
PASS means only that the blocked candidate was rebuilt exactly from the exact
manifest.

Even with an exact manifest, these blockers remain:

1. Independent Node process witnessing is absent.
2. Process identity and receipt signature are unverified.
3. Descriptor and dependency load-order review is unperformed.
4. DOM, browser, route, mount, and activation remain unauthorized.

Registration-v5 does not change a current pointer, publish a route, mount UI,
authorize a writer, or authorize paper or live trading.

## Consumer-first activation order

1. registration-v4 static frontend chain.
2. receipt-v3 local Node execution observation.
3. evidence-v3 Python cross-document binding.
4. registration-v5 blocked static candidate.
5. future independent execution identity or signature evidence.
6. future descriptor and dependency load-order review.
7. separate explicit production route or mount decision.

This ADR authorizes only step 4.

## Adversarial matrix

1. The expected manifest must have exactly nine artifacts.
2. The registration-v4 hash must be rebuilt and bound.
3. Receipt-v3 and evidence-v3 schemas and implementations must be explicit.
4. Missing, extra, and substituted manifest values must fail closed.
5. An exact blocked registration must verify exactly.
6. A valid document paired with a wrong manifest must fail.
7. A resealed authority promotion must fail exact verification.
8. Identity, signature, route, mount, paper, live, current, and writer
   authority must remain false.
9. The activation order must keep identity, review, and mount later.
10. No profitability or promotion claim may appear.

All validation is synthetic or in-memory. No runtime store, database, cache,
log, secret, service, browser, scheduler, market task, or trading path is
accessed.
