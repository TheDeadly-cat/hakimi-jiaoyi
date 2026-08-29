# ADR 0185: Portfolio-risk public projection v2 and temporal-lattice card

## Status

Accepted as an additive, unregistered presentation candidate on 2026-08-22.
It is not mounted in the current UI and does not authorize paper or live use.

## Context

ADR0184 closes the strategy-layer gap where portfolio-risk adapter v1 could
return PASS for both a temporally stable and a temporally unstable synthetic
fixture. Adapter v2 exact-verifies the base portfolio-risk result and the
temporal-stability gate, but it remains an internal research document.

ADR0167 projection v1 and its geometry card consume adapter v1. Reusing that
schema for adapter v2 would hide temporal blockers behind a compatible-looking
PASS path and would drift an already frozen browser contract. Exposing adapter
v2 directly would leak internal checks and source lineage.

## Decision

Add public projection v2 as a separate contract. It receives adapter v2, its
two source documents, and the two exact verification contexts. It rebuilds the
adapter v2 verifier before projecting anything.

The projection emits:

1. SOURCE as VERIFIED, UNKNOWN, or NOT_SUPPLIED.
2. GAP as joint research observation, portfolio-limit gap, temporal-stability
   gap, joint gap, risk-reduction path, UNKNOWN, or NOT_SUPPLIED.
3. MATURITY as UNMOUNTED_CANDIDATE.
4. PERMISSION as UNAUTHORIZED.
5. Redacted portfolio geometry, ticket/effective-bet counts, temporal aggregate
   counts, blocker counts, and warning counts.

The projection excludes source documents, component checks, raw correlations,
return series, window rows, selection cells, and cluster exposure structures.
Its verifier requires an exact canonical rebuild.

Add a standalone browser-compatible temporal-lattice card. It uses strict
schema, fingerprint, source, stage-order, scalar-type, cross-state, redaction,
and authority checks. Invalid input falls back to UNKNOWN while permission
stays UNAUTHORIZED.

The visual language is a research field note: warm paper, tide blue, amber,
rust, a ticket-to-effective-bet chain, and aggregate temporal cells. It avoids
profit colors and authorization language. Responsive, reduced-motion, and
forced-color contracts are included.

## Consumer-first order

1. Freeze projection v2 and independently review its exact verifier.
2. Bind Python projection output to the Node view-model.
3. Keep the card standalone and unmounted while source and freshness consumers
   remain shadow-only.
4. Perform rendered DOM and browser visual review only in an explicitly
   authorized isolated session.
5. Version the HTTP contract before any route or script registration.
6. Require separate current-switch authorization.

## Remaining blockers

- No application, HTTP, DOM, browser, or runtime consumer is registered.
- No rendered browser visual review has been performed.
- No operational timeout, monitoring, fallback, or persistence contract exists.
- External provider trust and runtime binding remain unproven.
- No current-switch, paper, or live authorization exists.

## Consequences

The project gains a neutral presentation boundary for the combined portfolio
and temporal-stability decision without mutating projection v1 or current UI.
Stable and blocked synthetic states can be explained without exposing raw
research data.

The natural-forward evidence chain remains audit-v2/readiness-v3 ->
maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2.
Legacy pack-v5 public reads remain UNKNOWN, pointer-v2 is unchanged, and no
pointer is reissued. This work provides no backtest, profitability proof, paper
authority, or live authority.
