# ADR 0365: Persisted-history/effective-budget covered-universe projection v1

- Status: Accepted as an unmounted synthetic preregistration
- Date: 2026-08-24
- Scope: Consumer-first remediation after ADR 0364

## Context

ADR 0364 proves that the effective-budget universe `A,B,C` is not fully covered
by the bound persisted-history universe `A,B`. It blocks `C` rather than treating
the extra symbol as an independently validated ticket.

Two remediations are possible: extend persisted history to `C`, or reduce the
budget universe. Fresh history work is outside the current authorization. A
candidate reduced universe can be preregistered without running fresh audits or
activating a consumer.

Existing ADR 0317/0323 projection code is not this remediation. It creates a
read-only presentation from already supplied effective-budget evidence. It does
not rebuild symbols, clusters, windows, uncertainty audits, or effective-budget
evidence.

## Decision

Add a cluster-atomic covered-universe projection with policy:

`PROJECT_ONLY_FULLY_HISTORY_COVERED_CLUSTERS_NO_IMPLICIT_INDEPENDENCE`

Its exclusion rule is:

`DROP_ENTIRE_CLUSTER_IF_ANY_MEMBER_LACKS_PERSISTED_HISTORY_COVERAGE`

The contract:

1. Re-verifies the exact ADR 0364 structural coverage gate and all of its source
   context.
2. Derives covered clusters from the original budget partition.
3. Retains a cluster only when every member has persisted-history coverage.
4. Drops every member of a partially covered cluster, preventing correlated
   survivors from being reclassified as independent tickets.
5. Rebuilds a new multi-window cluster preregistration over retained symbols,
   retained clusters, and the original budget window order.
6. Requires the projected preregistration hash to differ from the original
   full-universe preregistration hash.
7. Rejects reuse of all original full-universe evaluation artifacts.
8. Requires fresh projected audits, cluster gate, effective-budget binding
   preregistration, and effective-budget evaluation before any downstream
   presentation can be considered.

For the current synthetic source, the projection is:

- retained symbols: `A,B`;
- retained clusters: `cluster-a`, `cluster-b`;
- excluded symbol: `C`;
- excluded cluster: `cluster-c`;
- retained budget windows: `short,long`.

The status is:

`PREREGISTERED_UNMOUNTED_COVERED_UNIVERSE_REQUIRES_FRESH_BUDGET_EVALUATION`

## Fresh-evidence boundary

The required artifact order is:

1. `PROJECTED_MULTI_WINDOW_AUDITS_V1`
2. `PROJECTED_MULTI_WINDOW_CLUSTER_GATE_V1`
3. `PROJECTED_UNCERTAINTY_EFFECTIVE_BUDGET_BINDING_PREREGISTRATION_V1`
4. `PROJECTED_UNCERTAINTY_EFFECTIVE_BUDGET_BINDING_EVALUATION_V1`

None of those fresh artifacts is produced by this ADR. The original `A,B,C`
evaluation cannot be relabeled or projected onto `A,B`.

## Claim boundary

This preregistration proves deterministic cluster-atomic universe reduction and
a valid projected cluster preregistration. It does not prove:

- fresh projected uncertainty results;
- a projected effective-budget value;
- window semantic identity;
- semantic study-identity equivalence;
- runtime or read-only adapter eligibility;
- current, pointer, HTTP, writer, paper/live, profitability, or trading
  authority.

`fresh_projected_budget_evidence_completed` remains `false`.
`effective_budget_activation_allowed` remains `false`.

## Adversarial matrix

The synthetic tests cover:

- exact `A/B` retention and `C` exclusion;
- fresh projected preregistration verification;
- stale full-universe evidence rejection policy;
- atomic exclusion of partially covered clusters;
- overlapping and incomplete partition rejection;
- resealed ADR 0364 source-gate tampering;
- resealed projected preregistration tampering;
- resealed authority promotion;
- exact projection re-verification and permanent authority locks.

## Consequences

ADR 0365 creates a concrete consumer-first remediation path without fabricating
history coverage or reusing stale budget evidence. A future authorized synthetic
task may generate the required projected audits. Until then, ADR 0317/0323
presentation adapters remain ineligible for this candidate projection.
