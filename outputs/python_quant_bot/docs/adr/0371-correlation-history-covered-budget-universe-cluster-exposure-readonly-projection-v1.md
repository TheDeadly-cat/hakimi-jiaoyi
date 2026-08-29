# ADR 0371: Cluster Exposure Read-only Projection v1

- Status: implemented, additive, inactive
- Date: 2026-08-24
- Scope: hash-only synthetic application projection
- Authority: none; paper and live remain unauthorized

## Context

ADR0369 evaluates preregistered gross-exposure limits by source-owned cluster.
ADR0370 binds that evaluation to the exact ADR0367 batch and ADR0365 projection
context. The resulting dataclass still contains ephemeral raw cluster ids and
is therefore not an appropriate public or UI-facing document.

A public projection must preserve lineage and risk evidence without copying raw
symbols, cluster ids, caller-controlled blocker text, or execution authority.
It must also be rebuilt from the exact verified-batch call path rather than
accepting a caller-supplied result object as public evidence.

## Decision

Add the unmounted schema:

`strategy-correlation-history-covered-budget-universe-cluster-exposure-readonly-projection-v1`

The public builder first invokes ADR0370 with the exact batch document,
projection preregistration, occurrence-ordered proposals, preregistered policy,
and verification context. It then validates the complete ADR0369 result and
emits only:

- the ADR0370 adapter version;
- a canonical hash of the full internal ADR0369 result;
- source batch and policy hashes;
- proposal and independent-cluster counts;
- total and maximum cluster gross basis points;
- allowlisted policy blocker codes;
- neutral decision-path fields and permanent authority locks.

Raw symbols and cluster ids participate in the internal result hash but do not
appear in the projection.

## Public status vocabulary

- `UNKNOWN`
- `BLOCKED_PREREGISTERED_CLUSTER_EXPOSURE_LIMIT`
- `OBSERVED_WITHIN_PREREGISTERED_CLUSTER_EXPOSURE_LIMIT`

The word `READY` is not used. An observed within-limit structure remains
preregistered structural evidence only and does not grant admission.

Every document includes the ordered neutral path:

`SOURCE -> GAP -> MATURITY -> PERMISSION`

Permission is always `NOT_AUTHORIZED`.

## Projection invariants

1. The source result must be an exact ADR0369 dataclass produced through the
   ADR0370 verified-batch path.
2. Source batch identity must be lowercase SHA-256.
3. Policy identity is either lowercase SHA-256 or null only for an `UNKNOWN`
   policy contract.
4. Unknown results expose no counts or exposure metrics.
5. Non-unknown cluster aggregates are canonical, unique by cluster id, positive
   integer basis points, and sum exactly to total gross basis points.
6. Limit blocker codes follow a fixed order.
7. Only versioned allowlisted blocker codes can enter the public document.
8. Raw symbols and raw cluster ids never enter the document.
9. The complete projection is canonically hashed and exactly reverified.
10. `within_limit_is_not_admission` is always true.
11. Fresh projected evidence remains incomplete.
12. Registration, pointer writes, HTTP, runtime, paper, and live authority stay
    false.

## Adversarial matrix

| Case | Expected projection |
| --- | --- |
| Exact two-cluster batch within limits | Neutral observed status with redacted metrics |
| Exact duplicate-symbol batch over shared cap | Blocked status with one cluster count |
| Invalid policy after exact source receipt | `UNKNOWN`, null metrics |
| Reordered proposal occurrences with original batch | No projection |
| Resealed authority promotion | Exact verifier rejects |
| Unallowlisted blocker text | No projection |
| Aggregate total differs from cluster sum | No projection |
| Repeat identical inputs | Byte-equivalent canonical document and hash |
| Raw symbol or cluster id scan | No quoted raw identifiers present |

## Consumer-first activation order

1. Keep ADR0371 unmounted and available only to synthetic tests.
2. Independently verify ADR0367, ADR0369, ADR0370, and ADR0371 composition.
3. Define a static presenter that accepts only an exactly verified ADR0371
   document and renders neutral `SOURCE -> GAP -> MATURITY -> PERMISSION` copy.
4. Keep the presenter separate from current runtime loaders and public artifact
   readers.
5. Require a later explicit ADR and fresh projected evidence cycle before any
   consumer registration. This ADR performs no activation.

## Non-goals

- No market data, historical K-line, G50/G51, blind test, or return backtest.
- No strategy recommendation, order, execution, return, or profitability claim.
- No raw receipt serialization.
- No HTTP, engine, runtime, database, cache, log, key, scheduler, browser,
  publication, paper, or live operation.
- No natural-forward chain, `current`, or pointer update.

## Evidence boundary

Tests use only existing in-memory synthetic fixtures. Passing them proves local
redaction, hashing, exact verification, and fail-closed behavior. It does not
prove market validity, evidence maturity, portfolio safety, profitability, or
trading authorization.
