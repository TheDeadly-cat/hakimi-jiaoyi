# ADR 0152: Temporal date-grid report21 candidate binding v1

- Status: Accepted, unactivated research-only candidate
- Date: 2026-08-22

## Context

ADR0151 added a consumer that blocks temporal evidence unless every
preregistered symbol shares the exact ordered 61-price-date grid. Report21 and
its existing candidate binding predate that consumer. They verify only the
temporal-v1 gate and its expected hash.

A pure synthetic report chain demonstrated the compatibility gap. With BBB
shifted by 20 dates, AAA and BBB had only 40 common return dates, while source
uncertainty, report20, temporal v1, report21 contract, report21 decision and the
existing binding assessment all passed. The existing binding reported
CANDIDATE_BOUND while the ADR0151 date-grid gate returned BLOCK.

## Decision

Add a separate candidate-only assessment after the existing report21 binding.
For every report identity it rebuilds the ADR0151 gate from:

- the temporal-v1 gate embedded in report21;
- the stability gate embedded in report20;
- the preregistration and complete-link gate embedded in report19;
- the existing external temporal source binding;
- a new caller-supplied expected date-grid gate hash.

The new binding set must exactly equal the report identity set. Each gate must
verify structurally and match the independent expected hash. A report21 PASS is
accepted only when every bound date-grid decision is PASS. A report21 BLOCK may
remain structurally candidate-bound without gaining decision authority.

The assessment stores only identity-level hashes, statuses and aggregate counts.
It does not embed replay data, price dates, selection cells, reports or external
bindings.

## Consumer-first activation order

1. Validate this external candidate binding with synthetic adversarial cases.
2. Preregister the date-grid policy in a new protocol version.
3. Define a new report extension schema containing the date-grid gate hash.
4. Add an in-memory builder and migration list/dry-run with zero mutations.
5. Require separate explicit authorization before any current admission.

The current implementation completes only step 1.

## Adversarial requirements

- A fully aligned report21 remains candidate-bound.
- A 40-common-date report21 that old binding accepts is blocked.
- Missing, duplicate and wrong expected date-grid hashes fail closed.
- Report identity sets must match exactly across every binding layer.
- Coherently resealed facts and decision claims fail exact rebuild.
- Native type aliases and authority escalation fail closed.
- No report writer, current switch, route, runtime I/O or external asset is
  exported.

## Boundary

Protocol date-grid preregistration and a report schema containing the date-grid
gate are explicitly not proven. This assessment does not alter report21,
protocol-v10, the public single-look chain, pointer-v2 or pack-v6/evidence-v2.
It is synthetic contract evidence only, not market authenticity, profitability,
paper permission or live trading authorization.
