# ADR 0334: Geometry-bound multi-window presentation v9

- Status: accepted as an unmounted synthetic research candidate
- Date: 2026-08-24
- Authority: no UI mount, HTTP registration, runtime consumer, current admission,
  writer, paper, or live permission

## Context

ADR0332 closes direct presentation v7, and ADR0333 closes the HTTP branch.
Multi-window presentation v8 is the other direct presentation-v7 consumer.  A
simple presentation splice is already rejected by its anchor cross-bind.

The deeper synthetic contract path remained open because adapter v7 anchors
direct budget v3.  Under the existing synthetic budget, stability, adapter, and
presentation verifier boundaries, a matching three-window chain was built with
ADR0331's non-PSD direct budget as the anchor.  Stability gate v2, adapter v7,
and multi-window v8 all produced local PASS, while the geometry-bound budget
evaluation remained BLOCK.  This is synthetic contract evidence only, not
multi-window market evidence.

## Decision

Add the unmounted wrapper:

`exchange_terminal.services.strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9`

The wrapper:

1. Exact-verifies ADR0332 and requires its status and presentation verification
   to be PASS.
2. Derives the only accepted anchor budget and budget verification context from
   ADR0332.  Callers provide only stability-gate v2 document/context and the
   risk-increasing flag.
3. Independently rebuilds adapter v7 with the reviewed evaluator captured at v9
   import, requires exact self-hash and full equality, then applies its verifier.
4. Invokes unchanged multi-window presentation v8 with derived presentation and
   adapter contexts.
5. Independently rebuilds v8 with the reviewed builder captured at v9 import,
   requires exact self-hash and full equality, then applies the existing v8
   verifier.
6. Requires neutral `SOURCE -> GAP -> MATURITY -> PERMISSION`, `ui_mounted=false`,
   `http_candidate_registered=false`, `runtime_consumer_bound=false`, and all
   authority locks.

## Pinned dependencies

- ADR0332 source SHA-256:
  `e482206ff0e4a6e805e6f7318305135c8a291c4f9a1065ca2975b9ddb6093113`
- Adapter v7 source SHA-256:
  `09ecd921823260df4e8fda708f3c276d40fccd22c390b0ef7f920f9d9fc52f3e`
- Multi-window presentation v8 source SHA-256:
  `f2720ff7b2b32e7ffdf4c83502b1fa65f83ceb3ee8806dae94b0aaf71fd8ba6b`

## Adversarial acceptance matrix

- Exact ADR0332 PASS plus authentic adapter and v8: v9 evidence PASS; embedded
  v8 remains outer BLOCK and unauthorized.
- An authentic geometry-bound predecessor budget BLOCK with no stratified rows:
  stability and adapter remain UNKNOWN; v9 does not invoke v8 or promote the
  single-window decision to a multi-window BLOCK.
- Matching synthetic non-PSD direct budget/stability/adapter/v8 local PASS:
  ADR0332 BLOCK; adapter and v8 are not invoked by v9.
- Missing/recomputed-hash forged ADR0332 or adapter: UNKNOWN before v8.
- Context aliases, adapter rebuild failure, v8 exception, recomputed-hash v8
  forgery, axis reorder, or authority promotion: fail closed.

## Activation order

1. Keep v9 unmounted with no UI, HTTP, server, browser, or runtime consumer.
2. Preserve direct v8 only as legacy synthetic evidence, not a fallback source.
3. A future multi-window consumer must require exact v9 evidence and separately
   preregister its mount.
4. Browser exposure, current pointer changes, and trading authority require
   separate explicit authorization.

## Consequences

Both known presentation-v7 consumer branches now have geometry-bound wrappers.
Existing v8, adapter, stability, HTTP, server, and frontend code remain unchanged.
This ADR does not prove profitability or authorize paper/live trading.
