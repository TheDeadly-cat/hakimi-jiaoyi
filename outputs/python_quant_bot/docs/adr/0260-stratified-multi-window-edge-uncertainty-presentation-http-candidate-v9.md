# ADR 0260: Unregistered edge-uncertainty presentation HTTP candidate-v9

## Status

Accepted as an unmounted, unregistered research-only candidate on 2026-08-23.

## Context

ADR0259 introduced presentation-v9 as the bounded join of presentation-v8 and
adapter-v8. It preserves the existing stratified multi-window portfolio-risk
view while adding preregistered cross-cluster edge uncertainty and explicit
edge-block precedence. The existing HTTP candidate-v8 accepts only
presentation-v8.

A pure synthetic, read-only call chain proved the consumer gap 5/5:

1. the source document carried the presentation-v9 schema;
2. candidate-v8 returned UNKNOWN for that document;
3. candidate-v8 returned no payload;
4. candidate-v8 marked the result unavailable;
5. candidate-v8 rejected the request before invoking its verifier.

Widening candidate-v8 would silently change a frozen interface. Registering a
route before a v9 consumer contract and adversarial matrix exist would reverse
the consumer-first activation sequence.

## Decision

Add a distinct candidate-v9 module under `exchange_terminal/interfaces/http`.
It defines no route, transport, registry entry, current selector, writer,
scheduler, runtime binding, or UI mount.

The request contains only the presentation-v9 document and its expected hash.
The exact verification context contains the presentation-v8 document,
adapter-v8 document, and their two verification contexts. Extra keys,
substituted hashes, malformed receipts, verifier exceptions, unknown sources,
context splices, and permission promotions fail closed to a sealed UNKNOWN
response with no payload or partial summary.

An accepted source must produce the exact presentation-v9 verification receipt,
including `presentation_v9_exactly_verified=true`, matching hash, empty blockers,
and every execution or activation authority fixed false. The source shape also
cross-checks its partition hash between lineage and edge summary.

The known payload projects only:

- the bounded stratified portfolio-risk summary;
- aggregate multi-window stability counts and flags;
- aggregate cross-cluster edge counts and preregistered uncertainty thresholds;
- bounded component hashes and trade identity;
- neutral `SOURCE -> GAP -> MATURITY -> PERMISSION` stages.

Risk aggregates are rendered as canonical strings and edge statistics remain
integer micros, so the sealed response contains no floating-point values. Pair
rows, window rows, source documents, positions, correlation matrices, and
verification contexts are not embedded.

The response remains `KNOWN_BLOCKED` even when all local research components
pass. A local, multi-window, or cross-cluster edge block remains visible as an
additional blocker. Outer status remains BLOCK. Paper and live execution remain
unauthorized.

## Consumer-first activation order

1. Freeze this unregistered candidate-v9 contract and adversarial tests.
2. Add an isolated, unmounted card-v9 fixture that consumes only this payload.
3. Perform explicit static review and browser review only if separately authorized.
4. Propose route registration as a distinct versioned decision.
5. Consider current admission only after independent consumer evidence.

No later step is authorized by this ADR.

## Adversarial matrix

The 12-case contract covers edge-clear and edge-block projections, unknown-source
hiding, extra request keys, substituted hashes, exact context shape, malformed
receipts, verifier exceptions, response permission mutation, bounded float-free
projection, resealed source permission promotion, and input immutability.

## Compatibility and authority

- presentation-v9 implementation pin:
  `5fb7af67366913016c79236419f9b8df356a6b809ec876e0c312a67a4839b132`;
- strict canonical implementation pin:
  `cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412`;
- candidate-v8 remains unchanged and cannot consume v9;
- natural-forward artifact versions remain unchanged;
- legacy pack-v5 public reads remain UNKNOWN/null;
- pointer-v2 is neither changed nor reissued;
- no result is profitability evidence or trading authorization.

## Consequences

The next frontend consumer can depend on a narrow, versioned, edge-aware payload
without prematurely mounting UI or transport. The extra interface version is an
intentional compatibility boundary, not an activation signal.
