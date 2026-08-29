# ADR 0255: Unregistered stratified multi-window presentation HTTP candidate-v8

## Status

Accepted as an unmounted, unregistered research-only candidate on 2026-08-23.

## Context

ADR0254 introduced presentation-v8 as the first bounded presentation that joins
the anchor-local presentation-v7 decision with the preregistered multi-window
adapter-v7 decision. The existing HTTP candidate-v7 only accepts presentation-v7.
A pure synthetic, read-only call chain proved the resulting consumer gap 5/5:

1. presentation-v8 rebuilt exactly under its two predecessor receipts;
2. the document carried the presentation-v8 schema;
3. the legacy v7 consumer returned UNKNOWN;
4. the legacy v7 consumer returned no payload;
5. the legacy v7 consumer marked the result unavailable.

Adding v8 fields to the v7 contract would silently widen an already frozen
interface and would permit compatibility drift. Registering a route before the
consumer contract was adversarially tested would reverse the consumer-first
activation order.

## Decision

Add a separate candidate-v8 module under `exchange_terminal/interfaces/http`.
It deliberately defines no route, transport, registry entry, current selector,
writer, scheduler, or runtime binding.

The request contains only the presentation-v8 document and its expected hash.
The exact verification context contains the presentation-v7 document,
adapter-v7 document, and both predecessor verification contexts. Extra keys,
substituted hashes, malformed receipts, verifier exceptions, unknown sources,
and permission promotions all fail closed to a sealed UNKNOWN response with no
payload or partial summary.

An accepted source must produce the exact presentation-v8 verification receipt,
including `presentation_v8_exactly_verified=true`, matching hash, empty blockers,
and every execution or activation authority fixed false.

The known payload projects only:

- the bounded presentation-v7 risk summary;
- aggregate multi-window counts and stability flags;
- the minimum conservative effective-strata count;
- the worst registered-window maximum stratum gross;
- bounded source hashes and trade identity;
- neutral `SOURCE -> GAP -> MATURITY -> PERMISSION` stages.

Numeric risk aggregates are rendered as canonical strings so the sealed HTTP
candidate contains no cross-runtime floating-point values. Source documents,
window documents, positions, correlation matrices, and verification contexts are
not embedded.

The response remains `KNOWN_BLOCKED` even when every local research component
passes. A local or multi-window block remains visible as an additional blocker.
Outer status remains BLOCK. Paper and live execution remain unauthorized.

## Consumer-first activation order

1. Freeze this unregistered candidate contract and adversarial tests.
2. Add an isolated, unmounted card fixture that consumes only this payload.
3. Perform explicit static and browser review if separately authorized.
4. Propose route registration as a distinct versioned decision.
5. Consider current admission only after independent consumer evidence.

No later step is authorized by this ADR.

## Compatibility and authority

- presentation-v8 implementation pin:
  `f2720ff7b2b32e7ffdf4c83502b1fa65f83ceb3ee8806dae94b0aaf71fd8ba6b`
- strict canonical implementation pin:
  `cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412`
- presentation-v7 HTTP candidate remains unchanged and cannot consume v8;
- natural-forward artifact versions remain unchanged;
- legacy pack-v5 public reads remain UNKNOWN/null;
- pointer-v2 is neither changed nor reissued;
- no result is profitability evidence or trading authorization.

## Consequences

The frontend now has a narrow, versioned payload boundary for a future
multi-window stability card without prematurely mounting UI or transport. The
cost is one additional explicit interface version, which is preferable to
compatibility widening or hidden authority drift.
