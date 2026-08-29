# ADR 0158: report22 migration neutral public projection

- Status: Accepted
- Date: 2026-08-22
- Scope: Research-only, in-memory report22 migration evidence

## Context

ADR 0157 introduced a sealed LIST/DRY_RUN migration assessment for the report22
temporal date-grid candidate. That assessment contains internal hashes, bindings,
facts, blockers and plan details. Passing the assessment directly to a UI or HTTP
consumer would duplicate authority interpretation and disclose implementation
details that are not needed for a neutral status view.

The assessment also separates contract validity from report22 decision. A valid
DRY_RUN assessment may carry either a PASS or BLOCK report22 decision, while both
remain zero-execution research evidence.

## Decision

Add public-summary-v1 as a verifier-backed, redacted projection. It accepts no
stored authority and independently invokes the migration-assessment verifier with
the caller's original assets and expected bindings before selecting one of four
states:

1. `NOT_SUPPLIED`: no migration assessment was supplied.
2. `UNKNOWN`: the supplied assessment cannot be independently reconstructed as a
   supported LIST or DRY_RUN state.
3. `PLAN_LISTED`: LIST is verified, report22 is not evaluated and nothing ran.
4. `DRY_RUN_VERIFIED`: DRY_RUN is verified and the report22 PASS/BLOCK decision is
   preserved, but nothing ran.

The projection fixes the presentation order to `SOURCE -> GAP -> MATURITY ->
PERMISSION`. Every state keeps migration execution, fresh migration, writer,
formal registry, current admission, paper and live permissions false.

The public summary excludes assessment, registration and report hashes; identity
bindings; raw dates and prices; returns and correlations; facts, blockers and plan
details; profitability metrics; and external assets. Its verifier performs exact
recursive reconstruction and rejects native bool/integer aliases, extra authority
fields and resealed execution/current claims.

## Consumer-first activation order

1. Keep the internal ADR 0157 assessment as the sole source contract.
2. Build and verify public-summary-v1 in memory.
3. Audit any future HTTP or UI consumer against the exact public summary only.
4. Require a separate decision before mounting a route or UI component.
5. Never infer current admission, migration execution or trading permission from
   a projection state or report22 PASS decision.

## Adversarial contract matrix

Targeted synthetic tests distinguish absent from unverifiable evidence, cover
LIST and both DRY_RUN decisions, reject a mutated assessment, reject execution and
current reseals, reject bool/integer aliases and extra authority fields, assert
redaction, preserve input immutability and constrain callable exports.

## Consequences

This closes the safe presentation boundary without activating a consumer. It does
not modify report21/report22, registration-v9/v10, the natural-forward single-look
chain, pointer-v2, pack-v6/evidence-v2, current, paper/live permissions or any
profitability and external-authenticity claim.
