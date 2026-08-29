# ADR 0378: Post-merge Cluster Exposure Gate v1

- Status: implemented, additive, inactive
- Date: 2026-08-24
- Scope: pure synthetic incumbent-plus-proposal exposure gate
- Authority: none

## Context

ADR0369 evaluates a proposal batch in isolation. A small batch can pass every
proposal, cluster, and portfolio limit while breaching the same limits after it
is combined with incumbent exposure. Proposal-only safety is not post-merge
portfolio safety.

## Decision

Add a versioned incumbent snapshot and post-merge gate. The snapshot binds its
canonical cluster gross exposures to the exact ADR0365 projection hash and full
source cluster partition hash. The gate independently recomputes ADR0370,
verifies the snapshot hash, merges incumbent and proposed cluster totals, and
reapplies the preregistered cluster and portfolio gross limits.

Excluded source clusters may appear in the incumbent snapshot and continue to
count toward risk. They remain ineligible as proposals; counting incumbent risk
does not promote their evidence status.

## Result vocabulary

- `UNKNOWN`
- `BLOCKED_UPSTREAM_PROPOSAL_EXPOSURE_LIMIT`
- `BLOCKED_POST_MERGE_CLUSTER_EXPOSURE_LIMIT`
- `OBSERVED_WITHIN_POST_MERGE_PREREGISTERED_EXPOSURE_LIMIT`

Every result remains research-only and unauthorized.

## Adversarial matrix

| Case | Proposal-only | Post-merge |
| --- | --- | --- |
| Incumbent A=2500/B=1000, proposal A=600/B=400 | Pass | A=3100 cluster breach |
| Incumbent total=5000, proposal total=1200 | Pass | 6200 portfolio breach under 6000 policy |
| Balanced incumbent plus small proposal | Pass | Observed within limits |
| Empty incumbent snapshot | Pass | Equals proposal totals |
| Excluded cluster incumbent exposure | Not proposal-eligible | Still counted in post-merge risk |
| Projection or snapshot tamper | N/A | No result |
| Unknown, duplicate, or noncanonical snapshot cluster | N/A | Snapshot rejected |
| Upstream proposal batch already blocked | Blocked | No merge metrics |

## Boundaries

The snapshot is constructed in memory and is not claimed to be current
portfolio state. There is no DB, cache, log, account, broker, position reader,
HTTP route, runtime, writer, scheduler, pointer, paper, or live integration.
A separate freshness and delivery contract is required before any consumer
activation.

Passing synthetic tests proves only deterministic snapshot binding, merge math,
and fail-closed behavior. It does not prove current holdings, portfolio safety,
market validity, profitability, evidence maturity, or trading authorization.
