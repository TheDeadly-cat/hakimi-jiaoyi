# ADR 0167: Portfolio-risk public projection and geometry card v1

## Status

Accepted as an additive, unregistered presentation candidate on 2026-08-22.
It is not mounted in the current UI and does not authorize paper or live use.

## Context

ADR0166 created one fail-closed decision from the legacy portfolio gate and the
all-cluster effective-bet gate. That document is an internal research contract,
not a browser payload. Exposing it directly would leak component structure and
would let presentation code infer maturity or permission from a PASS token.

The current application has no consumer for the adapter and no public summary
of symbol tickets versus effective independent bets.

## Decision

Add a server-side public projection that exact-verifies adapter v1 from trusted
source inputs and emits only:

1. SOURCE state: VERIFIED, UNKNOWN, or NOT_SUPPLIED.
2. GAP state: declared research limits observed, research-limit gap present,
   risk-reduction path, UNKNOWN, or NOT_SUPPLIED.
3. MATURITY state: always UNMOUNTED_CANDIDATE.
4. PERMISSION state: always UNAUTHORIZED.
5. Redacted exposure summaries, gate observations, blocker count, symbol-ticket
   count, effective independent-bet count, and correlated-duplicate count.

The projection excludes raw correlations, pair results, clusters, component
checks, component documents, and source datasets. Resealed status, permission,
or scalar-type changes fail exact rebuild verification.

Add a standalone browser-compatible geometry card that consumes this projection
with strict schema, fingerprint, stage-order, scalar-type, and authority checks.
Malformed input renders UNKNOWN and keeps PAPER / LIVE unauthorized. The visual
language uses warm paper, ocean, ochre, and clay rather than profit-green or
READY semantics. It includes responsive, reduced-motion, and forced-color
contracts.

## Consumer-first order

1. Freeze and independently review projection v1 and its cross-runtime binding.
2. Define the trusted dual-source provider and shared observation-cutoff receipt.
3. Add a shadow-only application consumer with explicit freshness behavior.
4. Review rendered DOM and browser visuals in an authorized isolated session.
5. Version the HTTP contract before any route or script registration.
6. Require separate current-switch authorization.

## Remaining blockers

- No trusted dual-source provider or freshness receipt exists.
- No application, HTTP, DOM, browser, or runtime consumer is registered.
- No rendered browser visual review has been performed.
- No operational timeout, monitoring, fallback, or persistence contract exists.
- No current-switch, paper, or live authorization exists.

## Consequences

The project gains a neutral, source-first explanation of correlation-cluster
risk and the difference between ticket count and effective independent bets.
The card remains unmounted, so current behavior is unchanged. The natural
forward evidence chain remains audit-v2/readiness-v3 -> maturity-v3/dashboard-v7
-> pack-v6/evidence-v2 -> snapshot-v4/summary-v2. This work provides no backtest,
profitability proof, paper authority, or live authority.
