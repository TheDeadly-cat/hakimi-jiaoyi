# ADR 0184: Portfolio-risk adapter v2 temporal-stability gate

- Status: Accepted as detached synthetic research contract
- Date: 2026-08-22
- Scope: Strategy gate only; no runtime integration

## Context

Portfolio-risk adapter v1 joins the legacy exposure gate and the all-cluster
effective-bet gate.  The repository also contains a complete temporal cluster
stability gate with preregistered windows, effective-sample checks, and familywise
correction.  Adapter v1 accepts no stability input.

A unified pure-synthetic lineage demonstrates the gap.  The same risk-increasing
portfolio proposal produces the same v1 adapter hash and returns
`PASS / WITHIN_RESEARCH_RISK_BUDGET` for both cases below:

- all three preregistered temporal windows pass;
- the middle window is unstable and temporal stability returns
  `BLOCK / TEMPORAL_WINDOWS`.

The v1 portfolio metrics are 41% gross exposure, 23% proposal-centered cluster
exposure, three symbol tickets, two effective independent bets, and one correlated
duplicate ticket.  These are synthetic gate inputs, not return or profitability
results.

## Decision

Add adapter v2 as a strict wrapper around the two existing public verifiers.

For risk-increasing proposals:

1. Adapter v1 must exactly reverify and pass.
2. Temporal stability must exactly reverify and pass.
3. Both components must use the exact same preregistration and correlation matrix.
4. The proposed symbol must have exactly one passing selection cell for the same
   strategy id, variant id, and lane.

If adapter v1 blocks, v2 preserves the base block.  If temporal stability blocks,
v2 returns `BLOCKED_TEMPORAL_CORRELATION_INSTABILITY` even when v1 passes.

For a risk-reduction path, v2 preserves the existing v1 reduction semantics.  A
temporal block is retained as a warning and does not create execution authority.

## Strategy effect

This closes a real strategy-consumption gap: point-in-time cluster geometry can no
longer authorize a risk increase when preregistered temporal windows show unstable
absolute dependence or insufficient effective sample size.

Both positive and negative stable dependence remain sign-agnostic because the
existing temporal policy evaluates absolute dependence.

## Redaction and authority

The v2 output contains component hashes, shared lineage hashes, strategy identity,
proposal symbol, portfolio summaries, and stability counts.  It omits component
documents, return series, raw correlations, window rows, selection cells, and
legacy correlation payloads.

The adapter remains descriptive and research-only.  Runtime integration,
risk-service invocation, current admission, pointer writes, paper/live permission,
and profitability proof remain false.

## Compatibility

Adapter v1 and all stability modules remain unchanged.  V2 is detached and not
referenced by the server, runtime, shadow consumer, readiness envelope, or current
evidence chain.  The natural-forward chain remains:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 remains publicly `UNKNOWN`, and pointer-v2 is not reissued.

## Validation boundary

Validation is limited to synthetic contract tests, predecessor-family tests, an
independent public API matrix, and in-memory compilation.  No historical-return
backtest, formal blind test, runtime, network, database, cache, service, browser,
scheduler, paper task, or live task is used.
