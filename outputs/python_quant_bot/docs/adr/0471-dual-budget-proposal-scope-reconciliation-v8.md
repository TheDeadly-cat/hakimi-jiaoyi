# ADR0471: Dual-budget proposal-scope reconciliation v8

Date: 2026-08-25

## Status

Accepted as a versioned research-only reconciliation candidate. It does not
establish a combined budget, portfolio admission, runtime authority, or
`current` activation.

## Context

ADR0470 introduced a cutoff-bound dynamic multi-window effective-ticket budget.
Legacy effective-bet budget v11 remains a separate witness/checkpoint/replay
chain. Both documents can report a local `PASS` while keeping admission blocked.

A synthetic audit found that the default v11 fixture evaluates B with notional
2500, while the default v7 fixture evaluates B with notional 2000. Both local
budgets pass, and neither output contains a shared proposal-scope hash. No
existing dual-budget or v11/v7 binding was present.

The v11 evaluator exposes proposal symbol, notional, direction, risk-increasing
state, and cluster-gross percentage. It does not expose a portfolio snapshot
hash that can be reconciled with v7 positions and equity. A full dual-budget
merge would therefore overstate evidence.

## Decision

Add a v8 proposal-scope preregistration and exact reconciliation consumer that:

- exact-verifies the complete v7 and v11 predecessor contexts;
- requires both local budget conditions to be `PASS` while both admissions
  remain `BLOCKED`;
- preregisters proposal symbol, direction, notional in dynamic integer minor
  units, cluster-gross bps, and a positive integer legacy-unit conversion;
- requires the v11 integer notional multiplied by the registered scale to equal
  the v7 minor-unit notional exactly;
- converts the v11 cluster-gross percent to integral bps with decimal arithmetic
  and requires exact equality with the v7 preregistered cap;
- requires v11 `risk_increasing=true` and v7 additive-gross semantics;
- returns `BLOCK` for an exact predecessor decision or scope mismatch and
  `UNKNOWN` for unverifiable predecessor documents or contexts;
- reports `combined_budget_status=NOT_ESTABLISHED` and
  `combined_admission_status=BLOCKED` even when proposal reconciliation passes.

A v8 `PASS` means only:

`THE_TWO_EXACT_LOCAL_BUDGETS_EVALUATED_THE_SAME_PREREGISTERED_PROPOSAL_AND_CAP`

It does not mean the two budgets used the same positions, equity, market-data
snapshot, or admission authority.

## Consumer-first activation order

1. Produce the v7 and v11 local research documents independently.
2. Create a proposal-scope preregistration with an explicit integer unit scale.
3. Evaluate v8 only with exact predecessor contexts in synthetic or isolated
   read-only consumers.
4. Keep combined budget and admission unavailable until v11 provides a source
   portfolio snapshot hash that can be matched to v7 positions/equity hashes.
5. Require a separate ADR before any runtime, `current`, paper, live, or public
   evidence integration.

## Adversarial matrix

- B/2500 legacy versus B/2000 dynamic dual local PASS;
- aligned B/2500 proposal and 4500-bps cap;
- symbol and direction mismatch;
- exact integer unit conversion at scale 100;
- cluster-gross policy mismatch;
- exact v7 UNKNOWN predecessor from a shifted cutoff chain;
- v11 document and context drift;
- boolean scale/notional and malformed preregistration fields;
- resealed preregistration, scope summary, and authority promotion;
- deterministic output, input immutability, and predecessor-context redaction.

## Consequences

Two unrelated local PASS documents can no longer be presented as evaluating the
same proposal merely because both are green. The remaining portfolio snapshot
gap is explicit and machine-readable. Combined budgeting, profitability,
execution, paper/live permission, runtime activation, and public evidence
promotion remain unproven and unauthorized.
