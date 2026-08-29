# ADR 0265: Unregistered common-observation presentation HTTP candidate-v10

## Status

Accepted as an unmounted, unregistered research-only candidate on 2026-08-23.

## Context

ADR0264 froze presentation-v10 with bounded risk, multi-window, edge uncertainty,
and common-observation provenance summaries. Candidate-v9 accepts only
presentation-v9.

A pure synthetic read-only proof passed 5/5:

1. the source carried the presentation-v10 schema;
2. candidate-v9 returned UNKNOWN;
3. candidate-v9 returned no payload;
4. candidate-v9 marked the result unavailable;
5. candidate-v9 rejected the request before invoking its verifier.

Widening candidate-v9 would alter a frozen interface. Registering a route before
a strict v10 consumer exists would reverse consumer-first activation.

## Decision

Add a separate candidate-v10 under `exchange_terminal/interfaces/http`. It
defines no route, transport, registry entry, current selector, writer, scheduler,
runtime binding, or UI mount.

The request contains only presentation-v10 and its expected hash. The exact
context contains presentation-v9, adapter-v9, and their verification contexts.
Extra keys, substituted hashes, malformed receipts, verifier exceptions, unknown
sources, and permission promotions fail closed to a sealed UNKNOWN response with
`payload=null`.

Known payload projects only:

- bounded portfolio-risk summary with canonical string numerics;
- aggregate multi-window stability;
- integer-micro edge uncertainty aggregates;
- integer common-observation counts and provenance flags;
- bounded lineage hashes and neutral stages.

Pair rows, sample IDs, window documents, positions, matrices, source documents,
and verification contexts are excluded. The response is float-free.

A local, multi-window, edge, or common-observation basis BLOCK remains visible as
an additional blocker. Known response and payload status remain BLOCK. Route,
mount, current, paper, live, writer, and runtime authority remain false.

## Consumer-first activation order

1. Freeze and adversarially test this unregistered candidate-v10.
2. Add an isolated unmounted card-v10 consuming only its payload.
3. Perform browser review only if separately authorized.
4. Propose route, mount, and current changes as distinct decisions.

No later step is authorized by this ADR.

## Adversarial matrix

The 12-case contract covers common-basis clear and BLOCK projections, unknown
source hiding, exact request/context shape, hash substitution, malformed receipt,
verifier exception, response permission mutation, bounded float-free projection,
resealed source permission promotion, and input immutability.

## Compatibility and authority

- presentation-v10 implementation pin:
  `85a317babc16b310b9c62639879a241b0bf206d33a4be460a8d98400fb71c22e`;
- strict canonical implementation pin:
  `cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412`;
- candidate-v9, presentation-v10, current, and natural-forward artifacts remain
  unchanged;
- legacy pack-v5 public reads remain UNKNOWN/null and pointer-v2 is not reissued;
- paper/live remain unauthorized and live remains permanently locked;
- no result is profitability evidence or trading authorization.

## Consequences

An eventual card-v10 can consume one narrow, versioned, provenance-aware payload
without hidden route or mount activation. The extra HTTP candidate version is a
compatibility boundary, not an authorization signal.
