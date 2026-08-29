# ADR0465: Dynamic-window correlation source and independent-ticket gate v2

## Status

Accepted as an unmounted, synthetic, research-only consumer-first candidate on
2026-08-25. It does not replace the legacy 60-observation source, mount the
multi-window consumer, switch current, or authorize paper/live activity.

## Current-tree audit

The existing correlation-cluster gate v1 already prevents a symbol majority
inside one highly correlated cluster from being counted as independent votes.
The complete-link gate v2 also rebuilds its result from preregistration,
matrix, and selection cells, so coherently resealed derived conclusions fail.
The project therefore does not need another copy of those boundaries.

The remaining compatibility gap is between the fixed legacy source and the
pre-registered multi-window consumer:

- matrix-v1 always declares `lookback_observations=60`;
- multi-window stratified stability v2 preregisters 20/60/120 windows;
- its positive unit tests patch `_VERIFY_BUDGET_V3` with synthetic receipts;
- the same synthetic documents passed to the unpatched consumer return
  `UNKNOWN`, decision `BLOCK_MULTI_WINDOW_STRATIFIED_SOURCE_UNVERIFIED`, with
  zero verified windows.

This is not a market or performance result. It is a pure in-memory contract
reachability proof.

## Decision

Add `strategy_correlation_cluster_window_source_v2.py` without modifying any
legacy implementation or pinned hash chain. The v2 source:

1. Structurally preregisters an explicit window ID, lookback, exact legacy
   cluster partition, complete-link policy, and one-vote-per-cluster policy.
2. Declares chronology independently unproven; an expected preregistration
   hash must be supplied by the consumer.
3. Builds a full pair matrix whose overlap cannot exceed the preregistered
   lookback. The minimum usable overlap is `ceil(2/3 * lookback)`.
4. Recomputes cross-cluster threshold conflicts and all internal complete-link
   pairs using absolute Pearson correlation.
5. Counts an all-member-pass cluster as one effective independent ticket,
   regardless of how many symbols it contains.
6. Rebuilds preregistration, matrix, and gate documents exactly. Resealed count,
   topology, source, or authority promotion is rejected.
7. Keeps writer, runtime activation, current admission, paper, and live fields
   false.

## Consumer-first activation order

1. Land and independently review the v2 consumer/verifiers while unmounted.
2. Produce only synthetic shadow documents for preregistered windows.
3. Design a separate multi-window adapter that consumes exact v2 receipts and
   retains the legacy v2 result as UNKNOWN rather than promoting it.
4. Run isolated natural-forward shadow evidence only after separate approval.
5. Require an independently anchored preregistration chronology contract before
   any non-synthetic claim.
6. Make a separate current decision only after consumer parity, adversarial
   review, and explicit authorization. No step activates the next one.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Legacy short-window request | legacy document still says 60 |
| Exact v2 short window | binds 20 and overlap floor 14 |
| Two correlated symbols plus one independent symbol pass | three raw tickets become two effective tickets |
| Only correlated cluster passes | independent-cluster vote gate blocks |
| Positive or negative cross-cluster threshold edge | topology blocks |
| Internal pair below threshold | complete-link topology blocks |
| Pair overlap below floor | coverage blocks |
| Pair overlap above lookback | builder rejects |
| Missing, duplicate, non-finite pair | builder rejects |
| Wrong preregistration pin or resealed policy drift | verifier blocks |
| Resealed ticket-count or authority promotion | exact gate verifier blocks |
| Missing/non-native source | UNKNOWN and all authority remains false |

## Evidence and permission boundary

This ADR uses only pure synthetic values and in-memory function calls. It does
not run historical data, profitability research, G50/G51, formal blind tests,
services, browsers, schedulers, publishing, paper execution, or live execution.

The public natural-forward chain remains:

audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 is unchanged and is
not reissued.
