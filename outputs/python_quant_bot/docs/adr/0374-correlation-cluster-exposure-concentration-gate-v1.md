# ADR 0374: Correlation Cluster Exposure Concentration Gate v1

- Status: implemented, additive, inactive
- Date: 2026-08-24
- Scope: pure synthetic concentration policy
- Authority: none; paper and live remain unauthorized

## Context

ADR0369 closes absolute proposal, cluster, and portfolio gross-exposure gaps.
Absolute limits are necessary but insufficient. A two-cluster batch can stay
under every absolute cap while allocating 75 percent of gross exposure to one
cluster. Counting two independent tickets does not make that allocation
diversified.

The next policy layer must measure distribution across source-owned clusters
without using floating point, without trusting caller-supplied aggregates, and
without exposing raw cluster ids.

## Decision

Add the versioned contract:

`strategy-correlation-history-covered-budget-universe-cluster-exposure-concentration-gate-v1`

The gate recomputes the complete ADR0370 verified-batch exposure path and then
applies a preregistered concentration policy with three limits:

1. Minimum independent source-cluster count.
2. Maximum largest-cluster share in basis points.
3. Maximum Herfindahl-Hirschman concentration index in parts per million.

It also reports the inverse-HHI effective cluster count in milli-clusters for
interpretability.

## Integer and rounding rules

Let cluster gross exposures be `g_i` and total gross exposure be `G`.

- Largest share is `ceil(max(g_i) * 10000 / G)`.
- HHI is `ceil(sum(g_i^2) * 1000000 / G^2)`.
- Effective cluster count is `floor(G^2 * 1000 / sum(g_i^2))`.

Largest share and HHI round upward so a fractional boundary cannot be rounded
down into compliance. Effective cluster count rounds downward so concentration
cannot be overstated as diversification. No floating-point operation is used.

## Result vocabulary

- `UNKNOWN`
- `BLOCKED_UPSTREAM_EXPOSURE_LIMIT`
- `BLOCKED_PREREGISTERED_CLUSTER_CONCENTRATION_LIMIT`
- `OBSERVED_WITHIN_PREREGISTERED_CLUSTER_CONCENTRATION_LIMIT`

An observed within-limit result is structural research evidence only. Every
result has `permission=false`, `permission_state=UNAUTHORIZED`, and
`research_only=true`.

## Invariants

1. Inputs are recomputed through ADR0370; no external cluster aggregate is
   accepted.
2. ADR0369 source identity is canonically hashed, including internal raw cluster
   ids, but those ids are absent from the concentration result.
3. Invalid concentration policy or unknown upstream exposure produces
   `UNKNOWN` with no metrics.
4. An upstream absolute exposure breach blocks concentration evaluation and
   exposes no concentration metrics.
5. Non-unknown source totals equal the exact sum of canonical cluster totals.
6. Policy integers reject booleans.
7. Blocker order is fixed: cluster count, largest share, HHI.
8. Ratio calculations use conservative integer rounding.
9. Result and policy hashes are deterministic.
10. No status grants paper or live authority.

## Adversarial matrix

| Case | Absolute exposure | Concentration result |
| --- | --- | --- |
| 50/50 across two source clusters | Within limits | Observed within preregistered concentration |
| 75/25 across two source clusters | Within limits | Largest-share and HHI breach |
| Two proposals in one source cluster | Within absolute cluster cap | Count, share, and HHI breach |
| 2/1 integer-unit split | Within limits | Conservative 6667 bps and 555556 ppm |
| Source cluster cap already exceeded | Upstream breach | No concentration metrics |
| Invalid upstream exposure policy | Unknown upstream | `UNKNOWN`, no metrics |
| Boolean HHI policy | Invalid policy | `UNKNOWN`, no metrics |
| Proposal occurrence order drift | Exact batch mismatch | No result |

## Consumer-first activation order

1. Keep ADR0374 additive and unmounted.
2. Independently verify ADR0367, ADR0369, ADR0370, and ADR0374 composition.
3. Add a hash-only read-only concentration projection with no cluster ids.
4. Extend the static presenter only after exact projection and handoff contracts
   exist.
5. Require a future explicit ADR and fresh evidence before any current consumer
   registration. This ADR performs no activation.

## Non-goals

- No portfolio optimizer or recommended allocation.
- No strategy selection, parameter search, order, execution, return, or profit
  claim.
- No market data, historical K-line, G50/G51, blind test, or return backtest.
- No UI, HTTP, engine, runtime, storage, scheduler, pointer, publication, paper,
  or live operation.
- No natural-forward chain change.

## Evidence boundary

Tests use the existing exact in-memory ADR0365/ADR0367 fixture and constructed
integer exposure proposals only. Passing them proves local concentration math,
lineage composition, and fail-closed behavior. It does not prove market
validity, portfolio safety, diversification quality, evidence maturity,
profitability, or trading authorization.
