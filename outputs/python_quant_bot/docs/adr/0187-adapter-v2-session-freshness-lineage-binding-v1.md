# ADR 0187: Adapter-v2 session-freshness lineage binding v1

## Status

Accepted as an additive, inactive research receipt on 2026-08-22. It is not an
admission gate, consumer, runtime service, current artifact, or trading grant.

## Gap proof

Adapter v2 exact-verifies portfolio-risk adapter v1 and temporal stability but
does not accept ADR0172 session freshness. A stable three-symbol synthetic case
returned PASS with the same adapter hash whether paired externally with a fresh
PASS evaluation or a stale BLOCK evaluation.

Simply adding freshness as a third boolean would permit cross-splicing. Adapter
v2 exposes preregistration and pairwise-matrix hashes, while freshness exposes
a native-cutoff manifest hash. Those hashes are not directly interchangeable.

## Reused lineage

ADR0170 already exact-rebuilds the proposal-centered legacy matrix from the
signed-content completed-price chain. ADR0171 binds that chain to one native
observation cutoff. ADR0172 binds its freshness registration and evaluation to
the exact ADR0171 manifest.

A coherent synthetic construction proved that the existing documents can share:

1. The exact cluster preregistration.
2. The exact pairwise correlation matrix.
3. The deterministic legacy-matrix projection.
4. Completed-price input, matrix replay, derivation receipt, composition
   document, and composition context.
5. Native cutoff, freshness registration, and evaluation hashes.

No duplicate cutoff, price digest, matrix digest, or receipt is required.

## Decision

Add a lineage-binding receipt that fully reverifies:

1. Adapter v2 with both exact verification contexts.
2. ADR0170 legacy-matrix binding with its complete verification context.
3. ADR0172 freshness evaluation, registration, native manifest, trusted-clock
   attestation, and exact registration inputs.

The receipt then requires strict identity between the adapter preregistration
and native replay preregistration, adapter pairwise matrix and native replay
matrix, adapter legacy correlations and the deterministic ADR0170 projection,
and all five native content-chain documents.

It also requires continuous public hashes from completed input through replay,
legacy binding, native manifest, freshness registration, and freshness
evaluation. Cutoff date and UTC observation-cutoff semantics must agree.

## Decision separation

Receipt PASS means only that exact component documents share one native
lineage. Component states are projected without promotion. Adapter v2 or
freshness may independently be PASS or BLOCK.

The receipt always states:

- lineage_binding_only=true
- joint_admission_decision_made=false
- external provider trust=false
- external time authority=false
- profitability=false
- all consumer, runtime, current, paper, and live authority=false

An adapter v3 may consume this receipt only in a later versioned task that
defines risk-increase and risk-reduction policy. This ADR does not implement
that decision.

## Adversarial matrix

The targeted matrix covers exact same-lineage construction, fresh and stale
component states, a cross-spliced three-symbol adapter, changed legacy
correlations with an otherwise exact adapter, context key drift, trusted-clock
hash drift, legacy attestation drift, resealed freshness tamper, source
redaction, exact receipt tamper, input immutability, API shape, static imports,
and permanent authority locks.

## Compatibility and authority

ADR0170, ADR0171, ADR0172, ADR0184, adapter v2, and all public consumers remain
unchanged. The receipt is detached and unregistered.

The natural-forward chain remains audit-v2/readiness-v3 ->
maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2.
Legacy pack-v5 remains publicly UNKNOWN. Pointer-v2 fields, hash contract, and
non-reissuance behavior remain unchanged.

No runtime, database, cache, log, secret, network, service, browser, scheduler,
return backtest, formal blind test, paper task, or live task is used. Synthetic
lineage evidence does not prove real-market freshness, profitability, external
trust, or trading authority.
