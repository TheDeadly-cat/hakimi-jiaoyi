# ADR 0029: Within-cluster correlation stability gate

- Status: Accepted, consumer-only
- Date: 2026-08-21
- Policy: `strategy-correlation-cluster-stability-policy-v1`
- Gate: `strategy-correlation-cluster-stability-gate-v1`

## Context

Complete-link gate-v2 requires every internal pair to meet the point threshold
`|r| >= 0.75`. Existing uncertainty-v2 computes lag-1 effective sample sizes and
Fisher intervals for all pairs, but only cross-cluster ambiguity affects its
overall status. A synthetic 60-return example produced `r=0.8197` and
complete-link PASS while its effective-N 95 percent absolute lower bound was
only `0.7134`. The cluster topology was therefore treated as stable on a point
estimate despite explicitly available uncertainty evidence.

## Decision

Add a consumer-only stability gate over `WITHIN_CLUSTER_PAIRS_ONLY`. It consumes
an independently verified uncertainty-v2 audit and complete-link gate-v2, binds
their preregistration and pair matrix exactly, and reuses the existing lag-1
effective sample size. It applies a two-sided Bonferroni familywise correction
across every internal pair and requires each adjusted absolute interval lower
bound to remain at or above 0.75.

Singleton clusters have no internal pair requirement. Any source audit block,
complete-link block, input-binding mismatch, insufficient effective sample, or
unstable internal pair blocks the stability gate. Contract verification remains
separate from the PASS/BLOCK evidence decision.

## Consequences

Point-threshold clusters can no longer be described as stable without adjusted
uncertainty support. The gate has no report writer or current integration and
does not authorize parameter selection, paper trading, or live trading.
