# ADR 0165: correlation-cluster effective-bet budget

- Status: Accepted
- Date: 2026-08-22
- Scope: Additive research-only portfolio budget candidate

## Context

The existing `portfolio-risk-budget-v1` checks the proposed symbol against each
current holding. It fails closed when a new symbol lacks pair coverage and caps
the proposal-centered correlated notional. It does not recompute every existing
cluster after the proposal.

A pure synthetic case demonstrates the gap: two existing symbols each hold 25%
of equity and correlate at 0.92, while a new 5% symbol is unrelated to both. The
legacy gate reports only the proposal's 5% correlated exposure and passes even
though the existing cluster is already at 50%, above the 45% cluster budget.

## Decision

Add an independent effective-bet-budget-v1 consumer. It accepts the existing
preregistered cluster contract, correlation matrix and complete-link audit. The
audit must verify and have a PASS decision under
`ALL_INTERNAL_PAIRS_MEET_ABSOLUTE_PEARSON_THRESHOLD`.

For a risk-increasing proposal, the consumer assigns every active symbol to one
verified cluster, aggregates gross notional for every active cluster and checks
all clusters against a versioned 45% default. Direction netting is deliberately
not used. Symbols sharing a cluster contribute multiple symbol tickets but one
effective independent bet.

Missing assignments, blocked or tampered complete-link evidence, invalid native
types and any over-limit cluster fail closed. Risk-reducing actions retain a
separate pass-through path and do not require correlation sources.

The output excludes source documents, pair results and raw correlations. It is
sealed and exactly reconstructable, but is not connected to the runtime portfolio
gate, engine, writer or current.

## Consequences

The project can now distinguish nominal symbol count from effective independent
cluster count and can detect over-limit clusters unrelated to the new proposal.
This is synthetic research evidence, not a backtest, profitability claim, route,
paper/live permission or current activation.
