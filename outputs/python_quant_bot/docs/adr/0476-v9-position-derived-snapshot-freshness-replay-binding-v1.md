# ADR 0476: v9 position-derived snapshot freshness/replay binding v1

- Status: accepted as a synthetic research-only binding
- Date: 2026-08-25
- Scope: exact local snapshot hash and sequence binding

## Context

ADR 0475 binds the canonical per-symbol gross claim to the exact signed
portfolio snapshot accepted by v9. ADR 0474 derives the incumbent cluster
exposure snapshot and evaluates post-merge limits. The existing freshness/replay
gate evaluates a snapshot hash against an attestation, sequence-head reference,
and caller-supplied replay cursor.

Before this ADR, the position-derived gate and the freshness gate could each
produce a locally positive result while referring to different incumbent
snapshot hashes. A freshness attestation could also use the right snapshot hash
with a sequence different from the signed v9 snapshot sequence. Neither local
contract alone detected the cross-contract splice.

## Synthetic gap proof

The pre-binding chain produced both of these results:

1. Position-derived v2 evaluated a snapshot derived from `A=2500 bps` and
   remained within the local post-merge limit.
2. Freshness/replay evaluated a separately built `A=500 bps` snapshot as a
   fresh, unreplayed candidate.

Both source contracts were internally valid, but their snapshot hashes were
different. These are synthetic exposure units, not return or profitability
evidence.

## Decision

Add a composite application binding that:

1. Exactly verifies the ADR 0475 v9 signed-snapshot adapter.
2. Reconstructs the ADR 0474 incumbent cluster snapshot from the embedded
   canonical position claim using a newly public, pure snapshot builder.
3. Exactly verifies the ADR 0474 post-merge result and requires its derived
   snapshot hash and cluster-partition hash to match the reconstruction.
4. Calls the existing freshness/replay gate with that internally reconstructed
   snapshot. No caller snapshot hash is accepted.
5. Requires the freshness attestation sequence to equal the signed v9 snapshot
   sequence.
6. Requires freshness and position-derived post-merge statuses to describe the
   same recomputed downstream state.
7. Binds the adapter, position claim, derived result, snapshot, partition,
   attestation, reference, cursor, policy, and post-merge receipt into one
   deterministic result hash.
8. Preserves stale, replayed, upstream-blocked, and unknown outcomes without
   promotion.

## Safety interpretation

`OBSERVED_V9_POSITION_DERIVED_SNAPSHOT_FRESH_UNREPLAYED_CANDIDATE` is a local
synthetic candidate state only. The replay cursor is caller-supplied and is not
persisted or advanced. Therefore the contract does not establish an operational
anti-replay registry or externally trusted freshness.

Provider identity, source truth, external freshness, replay-registry
persistence, runtime binding, current admission, paper, live, profitability,
and trading authority remain false or unauthorized.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| v2 and freshness use different snapshot hashes | Composite binding rejects |
| Same snapshot hash uses a different sequence | Composite binding rejects |
| Bound sequence exceeds freshness lag policy | Bound result remains blocked |
| Bound attestation was already consumed | Bound result remains blocked |
| Adapter authority or lineage is altered | Exact adapter verification rejects |
| Position-derived snapshot hash is altered | Exact v2 verification rejects |
| Expected attestation, reference, or cursor hash drifts | Freshness evaluation rejects |
| Result authority is promoted | Exact reconstruction rejects |

## Consumer-first continuation

1. Keep the composite binding unmounted and outside routes, registries, and
   current.
2. Bind the caller-supplied replay cursor to the existing signed provider and
   persistence contracts before describing anti-replay as operational.
3. Bind portfolio snapshot provider identity and source truth through their
   existing signed registrations and attestations.
4. Add only a neutral `SOURCE -> GAP -> MATURITY -> PERMISSION` presentation
   consumer after those bindings are exact.

## Non-effects

- No database, cache, log, key, network, service, browser, scheduler, runtime
  portfolio reader, backtest, blind test, paper task, live task, cursor mutation,
  route, registry, current pointer, or publication flow is used.
- No frontend or existing evidence artifact is changed.
- The natural-forward single-look evidence chain, legacy pack-v5 behavior, and
  pointer-v2 contract remain unchanged.
- No profitability claim or trading authority is created.
