# ADR 0204: Weighted diversification adapter-v4 shadow candidate

## Status

Accepted as an unregistered shadow consumer candidate. It does not replace
adapter-v1, adapter-v2, or adapter-v3 and does not activate runtime, current,
paper, or live paths.

## Context

ADR0203 adds a weight-aware cluster budget but deliberately leaves all existing
consumers unchanged. A pure synthetic same-input chain reproduces the consumer
gap: adapter-v1, adapter-v2, and adapter-v3 all pass a portfolio with 44 percent
gross in one cluster and 2 percent in another, while weighted-budget-v2 blocks
with effective cluster count 1.090722 and dominant-cluster share 95.6522 percent.

## Decision

Add `strategy_correlation_cluster_portfolio_risk_adapter_v4.py` as a strict
consumer candidate that:

- public-verifies adapter-v3, preserving temporal stability, session freshness,
  and the risk-reduction exemption;
- public-verifies weighted-budget-v2 from its original inputs;
- recovers adapter-v1 original inputs from the v3 lineage context and requires
  exact equality with every weighted-budget input;
- requires the weighted v1 budget hash to equal the budget hash already bound by
  adapter-v1;
- blocks as `BLOCKED_WEIGHTED_CLUSTER_DIVERSIFICATION` when v3 passes but the
  weighted gate blocks;
- emits summary metrics only and keeps all authority permanently locked.

## Consumer-first activation order

1. Exercise adapter-v4 only through synthetic direct calls.
2. Freeze component implementation hashes and exact public receipts.
3. Obtain independent review of the weighted policy and cross-lineage matrix.
4. Create a separately versioned preregistration candidate if review succeeds.
5. Do not register, mount, write current, or reissue pointers automatically.

## Consequences

The project now has a coherent shadow decision that jointly requires legacy
portfolio limits, all-cluster gross limits, temporal stability, session
freshness, and weight-aware diversification. This is research-risk logic only,
not profitability evidence or trading permission.
