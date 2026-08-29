# ADR 0188: Adapter-v2 session-freshness lineage binding v2

## Status

Accepted as an additive, inactive research receipt on 2026-08-22. V1 remains
frozen. V2 is not an admission gate, consumer, current artifact, or trading
grant.

## V1 audit finding

ADR0187 v1 requires the adapter correlation matrix to be byte-identical to the
pairwise matrix embedded in native replay. This is valid for some fixtures but
is too strict for the actual temporal-stability path.

The uncertainty audit canonically rounds pair correlations before
build_correlation_matrix_contract creates the matrix consumed by complete-link,
full-window stability, temporal stability, and adapter v2. A synthetic pair
showed 0.19108436906721268 in replay and 0.191084369067 in the uncertainty
projection. Both are deterministic, but their matrix hashes differ.

Using the replay matrix directly caused pair_matrix_exactly_bound to block.
Using the deterministic uncertainty projection made complete-link,
full-window stability, and temporal stability all PASS.

## Decision

Preserve v1 and add lineage binding v2. V2 deterministically builds the v1
assessment and accepts it only when every v1 check passes except the two checks
being replaced:

1. adapter_native_pairwise_matrix_identity
2. public_source_hash_projection

No other v1 blocker is tolerated.

V2 then:

1. Rebuilds the uncertainty audit from the exact native matrix replay.
2. Requires identity with the uncertainty audit in the exact temporal verifier
   context.
3. Rebuilds the adapter matrix from uncertainty pair correlations and overlap
   counts.
4. Requires identity with the matrix in the exact adapter-v1 verifier context.
5. Rechecks public hashes using separate native-pairwise, uncertainty-audit,
   and adapter-projected matrix hashes.

## Reusable synthetic chain

Add a test-only factory that rebuilds a complete three-symbol source chain:

- A and B form one stable correlated cluster.
- C forms one independent singleton cluster.
- Signed-content, calendar/provider composition, deterministic legacy matrix,
  native cutoff, trusted-clock freshness, complete-link, full stability,
  temporal stability, adapter v1/v2, and lineage v1 all use the same source.

This factory uses production builders and can be reused by the future adapter
v3 tests without duplicating source construction.

## Decision separation

V2 PASS proves exact native replay to uncertainty projection to adapter matrix
lineage. Fresh and stale evaluations can both be lineage-valid. Component
states remain unpromoted, lineage_binding_only remains true, and
joint_admission_decision_made remains false.

External provider trust, external time authority, profitability, runtime,
shadow, current, paper, and live authority remain false.

## Adversarial matrix

Tests cover the exact v1 two-blocker gap, coherent three-symbol PASS,
native-versus-projected matrix hash distinction, stale freshness, unrelated
adapter cross-splice, temporal uncertainty tamper, native replay tamper, exact
receipt tamper, redaction, authority, input immutability, API shape, imports,
schema, fingerprint, and exports.

## Compatibility

ADR0170 through ADR0172, ADR0184, ADR0187 v1, adapter v2, projection v2,
preregistration v5, and all public consumers remain unchanged.

The natural-forward chain remains audit-v2/readiness-v3 ->
maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2.
Legacy pack-v5 remains publicly UNKNOWN. Pointer-v2 fields, hash contract, and
non-reissuance behavior remain unchanged.

No runtime, database, cache, log, secret, network, service, browser, scheduler,
return backtest, formal blind test, paper task, or live task is used. Synthetic
lineage evidence does not prove real-market freshness, profitability, external
trust, or trading authority.
