# ADR 0332: Geometry-bound budget presentation binding v1

- Status: accepted as an unmounted research-only candidate
- Date: 2026-08-24
- Scope: synthetic, in-memory contract evidence only
- Authority: no presentation activation, HTTP registration, current admission,
  writer, paper, or live permission

## Context

ADR0331 prevents effective budget v3 from consuming a non-PSD correlation matrix.
Presentation v7 remained a direct budget-v3 consumer.  Under presentation v7's
existing synthetic envelope verification boundary, the same authentic non-PSD
matrix from ADR0331 made direct budget v3 return
`PASS_STRATIFIED_RESEARCH_BUDGET`, and presentation v7 projected
`PASS_LOCAL_RESEARCH_COMPONENTS` and
`EXACT_JOINT_LOCAL_CLEAR_PROJECTED_UNMOUNTED`.  The presentation stayed globally
`BLOCK`, used the neutral axis, and granted no authority, but its local semantic
claim still propagated the impossible matrix geometry.  Without an authentic or
synthetic envelope verifier, presentation v7 correctly degrades the source to
`UNKNOWN`; ADR0332 does not weaken that behavior.

Presentation v7 is already pinned by the unregistered HTTP candidate v7 and
multi-window presentation v8.  Rewriting it would create dependency drift and a
duplicate migration problem.

## Decision

Add an unmounted composed binding:

`exchange_terminal.services.strategy_correlation_matrix_geometry_budget_presentation_binding_v1`

The binding performs this fixed sequence:

1. Strictly validate the exact ADR0331 verification-context key set.  Unknown or
   compatibility keys are rejected.
2. Exact-verify the ADR0331 evaluation and require its binding status to be
   `PASS`.
3. Derive the budget-v3 verification context from the trusted ADR0331 chain;
   callers cannot supply a second complete-link audit or gate.
4. Invoke unchanged presentation v7 with the trusted budget document and the
   independent envelope-v6 context.
5. Independently rebuild presentation v7 with the reviewed builder captured at
   binding import, require exact UTF-8 self-hash and full-document equality, then
   run the existing presentation verifier.
6. Require the exact neutral axis `SOURCE -> GAP -> MATURITY -> PERMISSION` and
   reject any authority escalation.

## Pinned dependencies

- ADR0331 source SHA-256:
  `d728150d3ab2d9dd8b998b23d789cb59de2a220274e87b986e4343d5dd9258b3`
- Presentation v7 source SHA-256:
  `27bfeacbdcbdfb03009c0dec007274e3c143af1045a8bfe7587ca4629ada8b38`
- The ADR0331 binding contract hash and static fingerprint are embedded in the
  ADR0332 contract and preregistration.

## Adversarial acceptance matrix

- Exact ADR0331 PASS and authentic presentation: ADR0332 evidence `PASS`;
  presentation remains globally `BLOCK` and unauthorized.
- Exact ADR0331 PASS carrying an authentic budget BLOCK: presentation is built
  and preserves the neutral blocked state.
- Pairwise-valid non-PSD direct budget/presentation local PASS: ADR0331 `BLOCK`;
  presentation v7 is not invoked by ADR0332.
- Missing or rehashed forged ADR0331 evaluation: `UNKNOWN`; presentation not
  invoked.
- Unknown context key or compatibility alias: `UNKNOWN`; presentation not
  invoked.
- Presentation exception or rehashed forged presentation: `UNKNOWN`; no
  presentation document trusted.
- Reordered neutral axis or authority promotion: rejected.

## Consumer-first activation order

1. Keep ADR0332 unmounted with no HTTP, multi-window, browser, or UI consumer.
2. Preserve direct presentation v7 only as legacy test evidence, not as a future
   activation source.
3. A future HTTP or multi-window candidate must require an exact ADR0332
   evaluation and must not fall back to direct presentation v7.
4. Current pointer, browser exposure, and writer activation require separate
   review and explicit authorization.

## Consequences

The geometry gate now reaches the first real presentation consumer without
rewriting pinned presentation v7.  Existing HTTP and multi-window candidates are
unchanged and remain unregistered/unmounted.  This ADR does not change the
natural-forward chain, prove profitability, or authorize trading.
