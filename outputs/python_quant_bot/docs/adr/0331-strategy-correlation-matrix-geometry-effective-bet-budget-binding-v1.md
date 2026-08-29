# ADR 0331: Geometry-bound effective bet budget consumer v1

- Status: accepted as an unmounted research-only candidate
- Date: 2026-08-24
- Scope: synthetic, in-memory contract evidence only
- Authority: no current admission, writer, paper, or live permission

## Context

ADR0330 made matrix geometry a required predecessor for the complete-link gate.
The effective bet budget v3 still accepted the matrix, complete-link documents,
and strata documents directly.  A synthetic matrix with correlations `0.70`,
`0.70`, and `-0.10` has determinant `-0.088` and is not positive semidefinite,
but all absolute pairwise correlations remain below the legacy `0.75` threshold.
The existing matrix, complete-link, strata, and budget v3 contracts therefore all
returned `PASS`, including `PASS_STRATIFIED_RESEARCH_BUDGET`, while ADR0329
correctly returned geometry `BLOCK` for the same matrix.

This is a contract-composition gap.  The direct budget result still granted no
authority, but it allowed an impossible correlation geometry to be described as
a passing research budget.

## Decision

Add the unmounted binding:

`exchange_terminal.services.strategy_correlation_matrix_geometry_effective_bet_budget_binding_v1`

Its consumer order is fixed:

1. Exact-verify the ADR0330 preregistration and evaluation for the same matrix,
   cells, strategy, variant, and research lane.
2. Require the ADR0330 evaluation itself to be `PASS`.
3. Exact-verify the preregistered strata gate against the complete-link gate
   carried by the trusted ADR0330 evaluation.
4. Invoke effective bet budget v3 using only the trusted embedded complete-link
   audit and gate.
5. Independently rebuild the full budget with the reviewed evaluator captured at
   binding import, require an exact UTF-8 self-hash and full-document equality,
   then apply the existing v3 verifier.
6. Reject any authority escalation and return evidence-only output.

ADR0330 lock-3 preregisters `RAW_EXCESS` and `research` as the only research
lanes.  All other lane labels are rejected before complete-link and budget
consumer invocation.

## Pinned dependencies

- Effective bet budget v3 source SHA-256:
  `bece44fe40c02242c879d1dead5cc11d2ce00edfc91c8d78a5b29962516c002d`
- Preregistered strata source SHA-256:
  `0758bd054adc2c98b51bf027cb5deea25e3620f555fd3369cdaf799c964adbb8`
- ADR0330 binding contract hash and static fingerprint are embedded in the
  ADR0331 preregistration and contract manifest.

Dependency or upstream-contract drift requires a new review and lock version.

## Adversarial acceptance matrix

- Exact PSD geometry and authentic upstream/strata/budget documents: binding
  evidence `PASS`; budget PASS/BLOCK is preserved; authority remains false.
- Pairwise-valid non-PSD matrix that direct v3 accepts: upstream `BLOCK`; budget
  consumer not invoked.
- Missing or rehashed forged ADR0330 evaluation: `UNKNOWN`; budget not invoked.
- Rehashed forged strata gate: `UNKNOWN`; budget not invoked.
- Budget consumer exception: `UNKNOWN`; no budget document trusted.
- Rehashed forged budget output: `UNKNOWN`; no budget document trusted.
- Paper/live or unregistered lane: fail closed before budget invocation.

## Consumer-first activation order

1. Keep ADR0331 unmounted with no engine, route, scheduler, or writer consumer.
2. Preserve the direct-v3 non-PSD proof as a regression test.
3. Require a future budget consumer to accept only an exact ADR0331 evaluation;
   do not add a compatibility fallback to direct v3.
4. Any current pointer or writer activation requires a separate ADR and explicit
   authorization.

## Consequences

The geometry requirement now reaches the real effective-budget consumer through
a narrow composed candidate.  Existing v3 behavior is not rewritten.  This ADR
does not alter the natural-forward chain, publish a pointer, prove profitability,
or authorize paper/live trading.
