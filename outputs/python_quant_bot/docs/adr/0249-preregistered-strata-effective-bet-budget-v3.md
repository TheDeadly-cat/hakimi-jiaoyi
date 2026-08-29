# ADR 0249: Preregistered-strata effective-bet budget v3

## Status

Accepted as an inactive, unmounted, research-only consumer. It does not modify
or activate current evidence, runtime gates, UI, writers, paper, or live paths.

## Context

ADR0165 budget-v1 collapses correlated symbols into complete-link clusters and
caps every active cluster's gross exposure. Its weight-aware v2 successor uses
inverse Herfindahl concentration so a 44 percent cluster plus a 2 percent
cluster cannot masquerade as two balanced independent bets.

ADR0016 separately preregisters higher-level asset-family, sector, geography,
and common-driver strata. Its gate prevents research selection votes from
treating clusters in one parent layer as independent. Budget-v2 does not accept
the strata registration or gate and therefore cannot apply that hierarchy to
active portfolio exposure.

A pure synthetic call proved the half-wiring. Two complete-link PASS clusters
were preregistered in one `asset-family` stratum. At 25 percent gross each,
budget-v2 accepted no strata input, reported weighted effective cluster count
2.0, and returned `PASS_WEIGHTED_RESEARCH_BUDGET`. The valid parent partition
could not affect its decision.

Requiring only the existing strata gate is insufficient. That gate counts
selection outcomes for every registered cluster, including inactive clusters.
An inactive passing stratum must not provide diversification credit to two
active clusters concentrated in another stratum.

## Decision

Add effective-bet-budget-v3 as a consumer of the existing contracts. It does
not replace or modify v1, v2, complete-link, or preregistered-strata services.

For risk-increasing evaluation, v3 requires:

1. exact v1 and v2 reconstruction with v2's v1 hash binding intact;
2. exact ADR0016 strata registration and gate;
3. a PASS strata-gate decision;
4. exact source-preregistration, registration, gate, and complete-link-gate hash
   continuity;
5. no caller-supplied predecessor result.

V3 reuses v1's verified active cluster gross rows. For every preregistered
dimension, it maps each active cluster to exactly one frozen stratum and sums
member-cluster gross without direction netting. It then checks:

1. every active stratum against the same versioned gross limit used by v1/v2;
2. inverse-Herfindahl weighted effective active strata against the frozen 1.5
   minimum whenever v2's total-gross diversification trigger applies;
3. every preregistered dimension, with the minimum weighted count as the
   conservative portfolio summary.

Inactive strata contribute no gross and no diversification credit. Below the
existing total-gross trigger, one active stratum is reported as one descriptive
bet but is not blocked if its aggregate gross remains within limit. Risk
reduction preserves the v1/v2 source-free pass-through and does not require
strata artifacts.

The sealed output contains dimension-level counts, dominant share, maximum
stratum gross, and status only. It excludes positions, cluster exposure rows,
cluster membership rows, pair results, matrices, returns, and raw correlations.

## Consumer-first activation order

1. ADR0002 cluster preregistration and complete-link gate-v2;
2. ADR0016 strata registration/gate and frozen hierarchy registry binding;
3. ADR0165 v1 cluster gross and exact v2 weighted-cluster decision;
4. this unmounted v3 active-strata consumer and exact verifier;
5. separately authorized report-schema and presentation candidates;
6. independent runtime-input admission and current migration review;
7. only then consider a runtime gate, still without paper/live authority.

## Adversarial matrix

- two active clusters in one stratum cannot borrow credit from an inactive
  passing stratum;
- same-stratum gross is summed before the 45 percent limit is checked;
- separate balanced strata pass, and 35/15 preserves the 1.5 weighted minimum;
- below-trigger same-stratum exposure remains one descriptive bet;
- blocked, substituted, missing, duplicated, or resealed strata sources block;
- v1/v2 source, hash, status, numeric-type, and decision blocks are preserved;
- resealed authority, decision, metric, or source-binding promotion becomes
  verifier `BLOCK/UNKNOWN`;
- inputs remain immutable and output embeds no source or position rows.

## Consequences

- Highly related active assets are no longer counted independently merely
  because complete-link assigned them different cluster labels.
- Existing strata semantics remain the single hierarchy source; no duplicate
  registry or permissive verifier is introduced.
- The implementation is synthetic research evidence only. It is not a return
  backtest, profitability proof, market validation, current admission, runtime
  authority, route, writer, migration, receipt, paper, or live authorization.
