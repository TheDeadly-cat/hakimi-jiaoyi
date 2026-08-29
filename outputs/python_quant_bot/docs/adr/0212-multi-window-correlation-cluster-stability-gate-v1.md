# ADR0212: multi-window correlation-cluster stability gate-v1

## Status

Accepted as an unmounted, research-only strategy gate. It is not connected to
current, runtime risk execution, paper trading, or live trading.

## Observed gap

Adapter-v4 accepts exactly one correlation matrix and one complete-link audit.
Its public API has no registered windows, sample horizon set, partition drift, or
stability fact. A real synthetic PASS call proved five API-gap predicates. A
second counterexample constructed opposite short/long cluster partitions and
proved six predicates showing those histories cannot affect adapter-v4 output.

This means a short window can label A/B as one bet and C as independent while a
long window places A/B/C in one cluster, yet the single-window decision can still
pass without observing the disagreement.

## Decision

Add a separate gate instead of changing pinned adapter-v4. Before evaluation,
the caller preregisters exactly three unique windows with strictly increasing
lookbacks and retains the preregistration hash out of band.

For every window the gate:

1. Requires a distinct correlation-matrix hash and exact registered lookback.
2. Re-verifies the weighted-budget-v2 document with its complete source context.
3. Requires the same equity, positions, proposal, direction, cap, universe,
   return series, and threshold identity across windows.
4. Normalizes the complete-link cluster partition and retains only its hash.

For risk-increasing proposals, any exact window BLOCK blocks the joint gate. Even
when all weighted budgets pass, a partition mismatch blocks because independent
bet count is unstable. Risk reduction remains exempt only after every source is
exactly verified.

## Evidence and authority boundary

Outputs contain window IDs, lookbacks, matrix/budget/partition hashes, decisions,
and counts only. Matrices, pair correlations, audits, positions, and contexts are
not embedded. All runtime/current/paper/live authority remains false.

Synthetic contract evidence does not prove future stability, provider trust,
profitability, or trading authority. The gate remains unmounted and does not
change the natural-forward current chain, legacy pack-v5 UNKNOWN behavior, or
pointer-v2 non-reissue contract.
