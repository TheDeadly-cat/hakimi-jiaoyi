# ADR 0333: Geometry-bound presentation HTTP candidate v8

- Status: accepted as an unregistered research-only candidate
- Date: 2026-08-24
- Scope: synthetic, in-memory HTTP contract evidence only
- Authority: no route registration, mount, current admission, writer, paper, or
  live permission

## Context

ADR0332 requires geometry-bound budget evidence before presentation v7 is built.
The existing HTTP candidate v7 still accepts a request that directly embeds any
presentation-v7 document plus its expected hash.  Under its existing synthetic
verification receipt, the non-PSD direct presentation from ADR0332 can therefore
reach a `KNOWN_BLOCKED` HTTP payload with local `joint_status=PASS`.

The HTTP v7 candidate is pinned and unregistered.  Rewriting it would invalidate
existing tests and consumers without proving a safe migration.

## Decision

Add the unregistered wrapper:

`exchange_terminal.interfaces.http.strategy_correlation_matrix_geometry_budget_presentation_http_candidate_v8`

The v8 request embeds only an ADR0332 evaluation and its expected hash.  The
verification context remains out of the request and must have an exact key set.
The wrapper:

1. Exact-verifies ADR0332 and requires its status and presentation verification
   result to be `PASS`.
2. Extracts the trusted presentation and derives the presentation-v7 context
   from the ADR0332 budget chain.  Callers cannot submit a second presentation,
   budget, complete-link audit, or complete-link gate.
3. Constructs the existing HTTP v7 request internally and invokes unchanged v7.
4. Independently rebuilds the complete v7 response with the reviewed builder
   captured at v8 import, requires exact UTF-8 self-hash and full equality, then
   applies the existing v7 response verifier.
5. Accepts only v7 `KNOWN_BLOCKED` with a payload and all route, mount, writer,
   admission, paper, and live authority fields false.
6. Returns a versioned v8 response with `INTERFACE_STATUS=UNREGISTERED_CANDIDATE`.

## Pinned dependencies

- ADR0332 source SHA-256:
  `e482206ff0e4a6e805e6f7318305135c8a291c4f9a1065ca2975b9ddb6093113`
- HTTP candidate v7 source SHA-256:
  `fdb2d0ff4abe5df9d7e83dae901e6bb11ae3e5b1fa3c4190b7d5123d3e058f23`
- ADR0332 contract hash and static fingerprint are embedded in the v8 contract.

## Adversarial acceptance matrix

- Exact ADR0332 PASS and authentic v7 response: v8 `KNOWN_BLOCKED`; route remains
  unregistered and authority remains false.
- Authentic budget BLOCK propagated through ADR0332: v8 `KNOWN_BLOCKED` with
  local BLOCK visible.
- Non-PSD direct HTTP local PASS: ADR0332 is not PASS; v7 builder is not invoked
  and v8 returns `UNKNOWN` with no payload.
- Missing or recomputed-hash forged ADR0332 evaluation: `UNKNOWN`; v7 not invoked.
- Extra request/context key or compatibility alias: `UNKNOWN` before verifier.
- v7 exception, recomputed-hash forged response, or authority promotion:
  `UNKNOWN`; payload withheld.

## Consumer-first activation order

1. Keep v8 unregistered with no server import, route, scheduler, browser, or UI
   consumer.
2. Preserve HTTP v7 only as legacy evidence; do not activate it as a fallback.
3. A future mount preregistration must pin this exact v8 source and contract and
   must still default to no route.
4. Route registration, current pointer changes, and browser exposure require a
   separate ADR and explicit authorization.

## Consequences

The geometry requirement now reaches an HTTP-shaped response without modifying
the server or existing HTTP v7 candidate.  This ADR does not activate a route,
change the natural-forward evidence chain, prove profitability, or authorize
paper/live trading.
