# ADR 0166: Correlation-cluster portfolio-risk adapter v1

## Status

Accepted as an additive, unregistered research candidate on 2026-08-22.
It is not a runtime gate, current writer, paper authorization, or live authorization.

## Context

The legacy portfolio-risk service enforces single-position, gross, net,
position-count, named-cluster, and proposal-centered correlation limits. The
effective-bet budget v1 separately evaluates every verified complete-link
cluster. Keeping both results side by side leaves a consumer gap: a caller can
select the favorable result, drift the two cluster limits, or submit a claimed
precomputed PASS.

The two correlation inputs are intentionally different contracts. The legacy
gate consumes its compact pair map, while the all-cluster gate consumes a
versioned correlation matrix bound to preregistration and a complete-link
audit. This candidate does not silently translate one source into the other.

## Decision

Add a pure adapter that rebuilds both component decisions from the same
portfolio proposal and emits one strict-canonical, research-only decision.
Risk-increasing proposals pass only when all of the following hold:

1. Shared portfolio inputs use strict native types.
2. The rebuilt legacy portfolio gate passes.
3. The rebuilt effective-bet result passes exact verification.
4. Every active complete-link cluster stays within its gross budget.
5. Legacy and all-cluster correlated limits are numerically aligned.
6. Both component authority locks remain false for paper, live, current, and runtime activation.

The API accepts source inputs, never caller-supplied component results. Its
verifier performs an exact rebuild, so changing status, authority, scalar type,
or hash cannot create a valid decision. The output projects only hashes,
decision facts, exposure summaries, and effective-bet counts. It excludes raw
correlations, pair results, clusters, and complete source documents.

Risk-reducing proposals preserve the established fail-open reduction path while
still requiring an exact Boolean risk flag and research-only component locks.

## Consumer-first activation order

1. Freeze and independently review this unregistered adapter contract.
2. Add a neutral SOURCE -> GAP -> MATURITY -> PERMISSION public projection if a UI consumer is needed.
3. Define a trusted provider that supplies both correlation contracts from one observation cutoff without converting either contract in the client.
4. Exercise the adapter only in an isolated shadow/rehearsal consumer.
5. Version the application and risk-service input contract before any server registration.
6. Require separate authorization before changing current or runtime routing.

## Remaining blockers

- No trusted dual-source provider or shared observation-cutoff receipt exists.
- No freshness, timeout, persistence, monitoring, or operational fallback contract exists.
- No shadow/rehearsal consumer is bound to adapter v1.
- No application-layer, risk-service, server, HTTP, DOM, or browser integration exists.
- No independent integration review or current-switch authorization exists.

## Adversarial matrix

The targeted contract covers joint PASS, legacy-only BLOCK, all-cluster-only
BLOCK, missing complete-link evidence, limit drift, aligned custom limits,
strict Boolean and numeric aliases, risk reduction without cluster sources,
input immutability, source redaction, rejection of precomputed results, and
resealed status, authority, and scalar-type tampering.

## Consequences

The project now has a narrow candidate boundary where existing portfolio limits
and effective independent-bet limits cannot override each other. Runtime
behavior remains unchanged. The single-look natural-forward chain remains
audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 ->
snapshot-v4/summary-v2. No backtest, profitability claim, paper permission, or
live permission follows from this decision.
