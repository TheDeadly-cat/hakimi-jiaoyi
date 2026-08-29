# ADR 0203: Weighted effective-cluster budget v2

## Status

Accepted as an unmounted shadow strategy-risk contract. It does not replace the
v1 budget or activate any adapter, runtime gate, current writer, paper workflow,
or live workflow.

## Context

The v1 effective-bet budget correctly aggregates gross notional across every
verified complete-link cluster and does not net long/short directions. Its
`effective_independent_bet_count`, however, is the number of active cluster
labels. It does not account for how active gross is distributed across those
clusters.

A pure synthetic call reproduces the gap: 44 percent gross in one cluster and 2
percent in another passes v1 and reports two independent bets, while the
inverse-Herfindahl effective cluster count is only 1.090722 and the dominant
cluster contains 95.6522 percent of active gross.

## Decision

Add `strategy_correlation_cluster_effective_bet_budget_v2.py` as a versioned
shadow successor that:

- always rebuilds and public-verifies v1 from the original inputs;
- independently validates the v1 cluster-exposure rows before deriving metrics;
- calculates inverse-Herfindahl effective cluster count from gross cluster
  notionals, without direction netting;
- applies a minimum weighted effective count of 1.5 only when total active gross
  exceeds the v1 per-cluster gross limit;
- preserves every v1 block and all research-only authority locks;
- emits summary metrics only and does not embed source exposure rows or raw
  correlations.

The trigger lets a small portfolio start in one cluster. Once total gross grows
beyond what one cluster is allowed to carry, multiple labels count as meaningful
diversification only when their weights clear the preregistered effective-count
threshold.

## Consumer-first activation order

1. Build and verify v2 only in pure synthetic shadow calls.
2. Exercise skewed, balanced, boundary, malformed, and source-drift cases.
3. Design a separately versioned adapter candidate only after v2 evidence is
   reviewed.
4. Do not modify v1, switch existing adapters, mount UI, write current, or reissue
   pointers automatically.

## Consequences

The project can now distinguish cluster-label count from weight-aware effective
diversification without changing current behavior. The 1.5 threshold is a
research policy constant, not evidence of profitability or trading authority.
