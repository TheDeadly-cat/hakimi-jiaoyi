# ADR 0369: Correlation Cluster Exposure Preflight v1

- Status: implemented, additive, inactive
- Date: 2026-08-24
- Scope: pure synthetic research contract only
- Authority: none; paper and live remain unauthorized

## Context

ADR0367 closes the independent-ticket multiplicity gap by counting unique
source clusters instead of treating correlated symbols as independent tickets.
That does not by itself close the exposure gap. A batch can correctly count as
one structural ticket while several proposals inside that cluster still add to
an excessive gross exposure.

The next gate must therefore aggregate exposure by the cluster assignment owned
by the covered-universe evidence chain. Proposal callers must not be allowed to
self-report a convenient cluster id.

## Decision

Add the versioned pure application contract:

`strategy-correlation-history-covered-budget-universe-cluster-exposure-preflight-v1`

The contract accepts three immutable values:

1. A normalized source receipt produced by a future explicit ADR0367 adapter.
2. A preregistered integer-basis-point policy.
3. A canonical tuple of symbol proposals with requested gross basis points.

The source receipt owns the canonical `symbol -> cluster` map. Proposal rows
contain no cluster field. The preflight resolves every symbol through the
receipt, sums all proposals in each source cluster, and then evaluates proposal,
cluster, and portfolio limits.

## Result vocabulary

- `UNKNOWN`: provenance, shape, version, mapping, or policy is invalid. No
  exposure metrics are exposed.
- `LIMIT_BREACH`: inputs are structurally valid and at least one preregistered
  limit is exceeded.
- `WITHIN_PREREGISTERED_LIMIT`: inputs are structurally valid and no configured
  limit is exceeded. This is not readiness, strategy quality, or permission.

Every result has `permission=false`, `permission_state=UNAUTHORIZED`, and
`research_only=true`.

## Invariants

1. The source receipt and producer contract versions must match exactly.
2. The source batch fingerprint is lowercase SHA-256 and is preserved in valid
   results.
3. The source must be structurally complete and must not claim permission.
4. The symbol map is non-empty, bounded, unique by symbol, and canonically
   sorted.
5. Proposals are an immutable tuple with unique proposal ids.
6. Every proposal symbol must exist in the source-owned map.
7. Booleans are rejected where integer limits or basis points are required.
8. Limits use integer basis points and satisfy
   `single <= cluster <= portfolio <= 10000`.
9. Repeated proposals for one symbol and different correlated symbols in one
   cluster always aggregate into the same exposure bucket.
10. Output cluster aggregates and blocker ordering are deterministic.
11. Unknown inputs expose no proposal count, cluster count, total, or cluster
    metrics.
12. No result authorizes paper or live execution.

## Consumer-first activation order

1. Keep this module and its tests additive and unreachable from current
   runtime consumers.
2. Specify a separate adapter from the exact ADR0367 result and ADR0365
   projection lineage into `correlation-cluster-exposure-source-receipt-v1`.
3. Prove the adapter binds the source fingerprint and canonical symbol map
   without caller-supplied cluster ids.
4. Run synthetic adversarial conformance for duplicates, omitted symbols,
   version drift, fingerprint drift, boundary values, and reordered inputs.
5. Add a read-only consumer projection with neutral
   `SOURCE -> GAP -> MATURITY -> PERMISSION` language.
6. Activate any current consumer only through a later explicit ADR and a fresh
   evidence cycle. This ADR does not perform that switch.

## Adversarial matrix

| Case | Expected result | Permission |
| --- | --- | --- |
| Two correlated symbols below the shared cap | `WITHIN_PREREGISTERED_LIMIT` with one cluster | false |
| Two correlated symbols exceed their shared cap | `LIMIT_BREACH` | false |
| Repeated symbol proposals | Aggregate in the same source cluster | false |
| Caller uses a symbol absent from the source map | `UNKNOWN`, no metrics | false |
| Duplicate proposal id | `UNKNOWN`, no metrics | false |
| Duplicate or noncanonical source mapping | `UNKNOWN`, no metrics | false |
| Incomplete source or source permission claim | `UNKNOWN`, no metrics | false |
| Producer version or fingerprint drift | `UNKNOWN`, no metrics | false |
| Boolean or non-monotonic policy value | `UNKNOWN`, no metrics | false |
| Proposal, single, cluster, and portfolio limits all exceed | Stable four-code `LIMIT_BREACH` | false |
| Proposal order changes | Identical aggregate metrics and policy fingerprint | false |

## Non-goals

- No strategy selection or parameter search.
- No return, profit, alpha, or execution claim.
- No historical K-line, G50/G51, blind, paper, or live task.
- No runtime, HTTP, engine, database, cache, log, key, scheduler, or browser
  integration.
- No change to the natural-forward artifact chain.
- No `current` pointer change and no pointer reissue.

## Evidence boundary

The implementation and tests use only constructed in-memory receipts, policies,
and proposals. Passing these tests proves the local contract behavior only. It
does not prove market validity, portfolio safety, profitability, evidence
maturity, or trading authorization.
