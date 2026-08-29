# ADR 0335: Geometry-bound multi-window HTTP candidate v9

- Status: accepted as an unregistered synthetic research candidate
- Date: 2026-08-24
- Authority: no route, transport, UI mount, runtime consumer, current admission,
  writer, paper, or live permission

## Context

ADR0334 binds multi-window presentation v8 to the geometry-gated ADR0332 chain.
The existing HTTP candidate v8 still accepts a direct presentation-v8 document
and its direct presentation-v7/adapter-v7 verification context.

The read-only synthetic gap proof used ADR0331's non-PSD direct budget chain.
Direct v8 had local joint PASS and hash
`21438884ac6a769cb9f0dc3df61b64a5deec28325011ba08f6d9d5ab7cbf24ce`.
Under the existing synthetic v8 verification boundary, HTTP v8 returned a
payload-bearing KNOWN_BLOCKED response with hash
`08a5160016f8cb305cecd2550f570ddaeafc89ab7427a20352af016fb596097c`.
ADR0334 correctly returned BLOCK / PRESENTATION_BINDING_EVALUATION_DID_NOT_PASS
before adapter or v8 invocation. This proves a verifier-boundary consumer gap,
not market behavior or profitability.

## Decision

Add the unregistered wrapper:

`exchange_terminal.interfaces.http.strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_candidate_v9`

The wrapper:

1. Accepts only an ADR0334 evaluation and its expected evaluation hash.
2. Requires an exact ADR0334 verification context with no compatibility keys.
3. Requires an exact PASS verification receipt, then requires the ADR0334
   evaluation itself to be PASS with a verified embedded v8 document.
4. Derives the only accepted legacy HTTP-v8 request and verification context
   from the verified ADR0334 sources; callers cannot supply a replacement v8.
5. Calls unchanged HTTP v8, independently rebuilds it with the builder captured
   at v9 import, requires exact response hash and full equality, then applies
   the existing v8 response verifier.
6. Returns payload only for an exact KNOWN_BLOCKED v8 response with locked top
   and payload authority. Every other path is UNKNOWN with no payload.

## Pinned dependencies

- ADR0334 source SHA-256:
  `17f43a0bfa4b9c1912e8f167efa9be4bd5f4c9e56d0d818fda88abe5f6705295`
- Legacy HTTP v8 source SHA-256:
  `70e2cabb54d0a9bf51973756fbe40173b142745d3a3f9d0f6f816ca759eb2770`

## Adversarial acceptance matrix

- Exact ADR0334 PASS plus authentic HTTP v8: KNOWN_BLOCKED with bounded payload.
- Missing, substituted, or recomputed-hash ADR0334: UNKNOWN before HTTP v8.
- non-PSD direct v8 gap: ADR0334 BLOCK; HTTP v8 is not invoked by v9.
- Predecessor budget BLOCK without stratified rows: ADR0334 UNKNOWN; HTTP v8 is
  not invoked.
- Context aliases, consumer exceptions, exact-rebuild exceptions, recomputed-
  hash HTTP-v8 forgeries, authority promotion, and response tamper: UNKNOWN.

## Consumer-first activation order

1. Keep v9 unregistered with no server import, route, transport, UI, or runtime
   consumer.
2. Preserve legacy HTTP v8 only as synthetic compatibility evidence, not as a
   fallback source for a future geometry-bound route.
3. Any future route must first preregister a mount that requires exact v9
   evidence and preserves UNKNOWN payload suppression.
4. Current pointer, browser exposure, paper, and live authority require separate
   explicit authorization.

## Consequences

The known multi-window HTTP branch now has a geometry-bound candidate without
changing HTTP v8, server, current selectors, CSS, or frontend code. This ADR is
contract evidence only and does not prove profitability or authorize trading.
