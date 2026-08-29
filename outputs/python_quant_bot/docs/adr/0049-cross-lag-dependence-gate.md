# ADR 0049: Cross-lag dependence candidate gate

## Status

Candidate gate implemented. It is synthetic-only, non-formal, and not connected to current state.

## Gap

Contemporaneous, temporal-window, and downside-tail checks can still miss two strategies when one is a delayed copy of the other. Their zero-lag Pearson correlation may be near zero even though a fixed lead or lag has almost perfect dependence. Counting both as independent votes would overstate evidence.

## Decision

Test every cross-preregistered-stratum pair at the fixed non-zero lag family `-2, -1, +1, +2`.

- Require at least 64 exact, contiguous, caller-ordered observations.
- Require native finite return values and the exact identity set on every row.
- Apply a two-sided Bonferroni correction over all pair-by-lag tests.
- Use a Fisher-z lower confidence bound for absolute Pearson correlation.
- Adjust effective sample size with the clipped product of each shifted series lag1 autocorrelation.
- Block when any adjusted absolute lower bound is at least 0.75.
- Block malformed order, duplicates, missing identities, constant shifted series, low effective sample size, or hash mismatch.

The gate accepts an externally pinned canonical stratum-assignment hash instead of creating another registration writer. Stratum timing and sequence ordering remain unattested candidate inputs.

## Synthetic gap proof

A deterministic repeating source and its one-observation delayed copy have near-zero zero-lag correlation while lag `+1` is perfect. The gate blocks the pair. Independent deterministic random fixtures may PASS this candidate blocker but never prove independence or authorize vote counting.

## Authority and next order

The result exposes aggregate lag diagnostics but no observation ids or raw returns. Every formal registration, timing, independent-vote, current, writer, paper, live, and profitability permission remains false.

The next consumer-first step is a read-only semantic verifier and redacted projection. Formal strata-source integration must bind to the existing preregistration chain in a separate reviewed migration; this candidate gate does not create it.
