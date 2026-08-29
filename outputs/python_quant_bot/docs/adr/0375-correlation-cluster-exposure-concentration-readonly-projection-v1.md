# ADR 0375: Cluster Exposure Concentration Read-only Projection v1

- Status: implemented, additive, inactive
- Date: 2026-08-24
- Scope: hash-only synthetic concentration projection
- Authority: none; paper and live remain unauthorized

## Context

ADR0374 produces a redacted dataclass with integer cluster-concentration
metrics. It is still an internal application result and is not an appropriate
public evidence document. A public consumer needs exact lineage, stable status
semantics, allowlisted blockers, null-metric rules, and canonical hashing.

The concentration projection must remain independent from ADR0371. Extending
the exposure projection in place would blur absolute-limit and distribution
boundaries and create compatibility ambiguity for existing consumers.

## Decision

Add the versioned projection:

`strategy-correlation-history-covered-budget-universe-cluster-exposure-concentration-readonly-projection-v1`

The builder recomputes ADR0374 from the exact verified batch inputs. It validates
the full result and emits only:

- ADR0374 contract version and result hash;
- source exposure result and concentration policy hashes;
- proposal and independent-cluster counts;
- total gross basis points;
- largest-cluster share basis points using conservative ceiling;
- HHI parts per million using conservative ceiling;
- inverse-HHI effective cluster count in milli-clusters using floor;
- allowlisted policy blockers;
- neutral decision path, facts, and permanent authority locks.

Raw symbols and cluster ids never enter the document.

## Status and metric rules

- `UNKNOWN`: policy or upstream contract is unknown; all summary metrics are
  null.
- `BLOCKED_UPSTREAM_EXPOSURE_LIMIT`: ADR0369 absolute exposure already blocks;
  all concentration metrics are null.
- `BLOCKED_PREREGISTERED_CLUSTER_CONCENTRATION_LIMIT`: valid concentration
  metrics are exposed with ordered policy blockers.
- `OBSERVED_WITHIN_PREREGISTERED_CLUSTER_CONCENTRATION_LIMIT`: valid metrics are
  exposed with no policy blocker. This is not admission or diversification
  proof.

Every status has `permission=NOT_AUTHORIZED` and all runtime authority false.

## Invariants

1. The projection is rebuilt from the complete ADR0374 verified-batch path.
2. Result and source identities are lowercase SHA-256.
3. Unknown and upstream-limit statuses expose no summary metric.
4. Non-unknown metrics are bounded integers and effective cluster count cannot
   exceed the nominal independent-cluster count.
5. Concentration blockers follow count, largest-share, HHI order.
6. Unallowlisted blocker text is rejected.
7. Raw symbols and cluster ids are absent.
8. The complete document is canonically hashed and exactly reverified.
9. Diversification quality, profitability, paper, and live authority remain
   false.
10. No existing projection or current consumer is modified.

## Adversarial matrix

| Case | Expected projection |
| --- | --- |
| Balanced 50/50 exact clusters | Neutral observed status and integer metrics |
| Absolute limits pass at 75/25 | Concentration-blocked status with share and HHI blockers |
| Upstream cluster cap breach | Upstream block with null concentration metrics |
| Boolean concentration policy | `UNKNOWN` with null metrics |
| Reordered batch occurrences | No projection |
| Resealed diversification authority | Exact verifier rejects |
| Unallowlisted blocker text | No projection |
| Effective cluster count exceeds nominal bound | No projection |
| Repeated identical inputs | Identical document and hash |
| Raw identifier scan | No symbols or cluster ids present |

## Consumer-first activation order

1. Keep ADR0375 unmounted and synthetic.
2. Independently verify ADR0374 and ADR0375 composition.
3. Add a dedicated exact Python-to-JavaScript handoff envelope.
4. Add a separate unmounted presenter with neutral concentration vocabulary.
5. Require a later explicit mount ADR and fresh evidence before any current
   consumer registration.

## Non-goals

- No optimizer, allocation recommendation, strategy selection, order, return,
  or profit claim.
- No UI, HTTP, engine, runtime, storage, scheduler, pointer, publication, paper,
  or live operation.
- No market data, historical K-line, G50/G51, blind test, or return backtest.
- No natural-forward chain change.

## Evidence boundary

Tests use only exact in-memory synthetic fixtures. Passing them proves local
redaction, integer-metric validation, canonical hashing, exact verification, and
fail-closed behavior. It does not prove diversification quality, market
validity, evidence maturity, profitability, or trading authorization.
