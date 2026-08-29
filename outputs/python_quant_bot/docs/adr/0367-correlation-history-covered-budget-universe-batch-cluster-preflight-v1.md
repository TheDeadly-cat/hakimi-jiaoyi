# ADR 0367: History-covered budget-universe batch cluster preflight v1

- Status: Accepted as an unmounted synthetic application consumer candidate
- Date: 2026-08-24
- Scope: Cluster-collapsed proposal batches before any admission consumer

## Context

ADR 0366 classifies one proposed symbol against the ADR 0365 covered universe.
A sequence of single-symbol checks is not enough for a batch: correlated symbols
could still be counted as separate tickets after each symbol passes the same
structural membership check.

The batch consumer must count projected exposure opportunities by source cluster,
not by symbol count. It also must preserve cluster-atomic exclusion and must not
convert a structural count into admission permission.

## Decision

Add an unmounted batch cluster preflight that:

1. Re-verifies ADR 0365 and its complete ADR 0364 context once per batch.
2. Accepts 1 to 64 canonical proposal occurrences.
3. Verifies that the original budget clusters form an exact, non-overlapping
   source-symbol partition.
4. Verifies that every source cluster is wholly projected or wholly excluded.
5. Classifies every unique proposal as projected, excluded, or unknown.
6. Counts `effective_projected_ticket_count` as the number of unique projected
   source clusters represented in the batch.
7. Prevents duplicate symbols from increasing the effective ticket count.
8. Emits hash-only proposal and cluster evidence.
9. Keeps every batch outcome unauthorized.

For two symbols `A,B` in one correlation cluster:

- naive unique projected symbol count: `2`;
- effective projected ticket count: `1`;
- cluster-collapse reduction: `1`.

This is a structural count only. It is not a budget, position size, trade signal,
or profitability estimate.

## Outcome precedence

Batch state precedence is fail-closed:

1. Any unknown symbol:
   `UNKNOWN_BATCH_CONTAINS_UNVERIFIED_SYMBOL`
2. Otherwise, any history-coverage-excluded symbol:
   `BLOCKED_BATCH_CONTAINS_HISTORY_COVERAGE_EXCLUDED_SYMBOL`
3. Otherwise:
   `BLOCKED_FRESH_PROJECTED_EVIDENCE_INCOMPLETE`

Every result uses neutral `SOURCE -> GAP -> MATURITY -> PERMISSION` and
`PERMISSION=NOT_AUTHORIZED`.

## Claim boundary

The preflight proves deterministic cluster collapse and source partition
integrity. It does not prove:

- fresh projected uncertainty or effective-budget evidence;
- trade-level netting or direction offset;
- admission eligibility;
- HTTP/runtime/current/pointer/writer authority;
- paper/live or profitability authority.

The term `effective ticket` means one structural proposal group per correlation
cluster. It does not mean an executable order.

## Adversarial matrix

The synthetic tests cover:

- current projected batch counting;
- excluded-member batch rejection;
- unknown-member precedence;
- duplicate proposal collapse;
- two correlated symbols collapsing to one ticket;
- partial and overlapping source partition rejection;
- hash-only neutral output;
- resealed ADR 0365 tampering;
- resealed permission promotion and exact verification.

## Consequences

ADR 0367 closes the most direct batch-level independence loophole before any
runtime consumer exists. Fresh projected evidence remains the next mandatory
research prerequisite, and this preflight remains blocked until that separate
work is explicitly authorized and completed.
