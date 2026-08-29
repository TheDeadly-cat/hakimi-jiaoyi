# ADR 0403: Verified Risk-Reduction Effective Budget v4

- Status: Accepted for isolated synthetic research only
- Date: 2026-08-24
- Supersedes: nothing
- Activates current: no

## Context

The v1-v3 effective-budget chain accepts a caller-provided boolean risk_increasing=False as sufficient to enter RISK_REDUCTION_PATH. That branch returns PASS before validating positions, proposal symbol, notional, direction, correlation sources, complete-link clusters, or preregistered strata.

A pure synthetic call demonstrated that an existing LONG position followed by another LONG buy is accepted as risk reduction when the caller supplies the false flag. V2 and v3 preserve that decision and skip their weighted cluster and strata gates.

## Decision

Add an unmounted v4 successor without modifying v1-v3.

For risk-increasing proposals, v4 exactly rebuilds v3 and preserves its decision. Risk-reduction proposals require an exact transition document derived from native before/after position snapshots and the proposal:

- the proposal must target one existing position;
- the order direction must oppose the existing position direction;
- the order cannot cross or reverse the position;
- every non-target position must be byte-semantically unchanged after normalization;
- the target position must decrease by exactly the proposal notional or disappear at zero;
- total absolute portfolio gross must decrease by exactly the same amount;
- direction netting is never used.

The caller flag alone is never sufficient. The transition and v4 outputs contain only hashes and summaries, not raw position rows.

## Consumer-first activation order

1. Produce and verify the transition from one immutable before/after snapshot pair.
2. Rebuild v4 from v3 and the exact transition.
3. Add independent snapshot provenance before any mounted consumer uses the result.
4. Preserve the risk-increasing v3 path unchanged.
5. Do not switch current, write pointers, activate runtime gates, or grant paper/live/writer authority in this ADR.

## Adversarial matrix

Fifteen cases cover the reproduced caller-flag bypass, verified LONG and SHORT reductions, same-direction additions, over-close and crossing attempts, mismatched target balances, other-position changes, new symbols, duplicate rows, boolean/non-finite/direction aliases, missing proof, exact v3 risk-increasing compatibility, transition aliasing on the increasing path, permission promotion, summary-only deterministic output, input immutability, and absence of runtime/I/O or precomputed-predecessor acceptance.

## Consequences

- A risk-increasing proposal can no longer be relabeled as reduction within the v4 contract.
- Local transition PASS does not prove position snapshot provenance or execution and grants no runtime, current, paper, live, writer, profitability, or trading authority.
- V1-v3 remain immutable compatibility predecessors and retain their known caller-flag gap; consumers must explicitly opt into v4 after separate activation review.
- The natural-forward public chain remains audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2.
- Legacy pack-v5 public reads remain UNKNOWN, and pointer-v2 is not reissued.
