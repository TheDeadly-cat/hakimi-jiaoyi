# ADR 0474: Position-derived post-merge cluster exposure gate v2

- Status: accepted as a synthetic research-only contract
- Date: 2026-08-25
- Scope: local position-to-cluster derivation only

## Context

The incumbent snapshot chain had two individually useful but disconnected
contracts:

1. Post-merge v1 verifies a caller-supplied `cluster_gross_bps` snapshot and
   applies proposal plus incumbent cluster limits.
2. The freshness/replay gate verifies sequence, head, and cursor relations for
   an incumbent snapshot hash.

Neither contract recomputes cluster gross from per-symbol positions. A caller
can therefore submit an understated cluster snapshot that is internally valid,
fresh, and unreplayed while the actual local position claim carries materially
larger gross exposure. This is a semantic input freedom, not a hash failure.

## Decision

Add a v2 application contract that accepts a canonical synthetic position
snapshot claim and derives the incumbent cluster snapshot before invoking the
existing post-merge v1 gate.

The contract:

1. Requires canonical, unique per-symbol gross positions with strict integer
   semantics and a bounded position count.
2. Binds the claim to the exact projection preregistration hash and a canonical
   positions fingerprint.
3. Reads the cluster partition only from the existing projection verification
   context.
4. Rejects every position symbol outside that partition instead of silently
   dropping it.
5. Aggregates gross exposure by cluster and builds the existing v1 incumbent
   snapshot internally. Callers cannot supply the aggregate values.
6. Delegates the actual post-merge limits to v1 and mirrors its fail-closed
   status and redacted metrics.
7. Emits deterministic derivation and result hashes and provides an exact
   recomputation verifier.
8. Keeps provider identity, source truth, freshness, cursor mutation, paper,
   live, and execution permission closed.

## Synthetic gap proof

For the same proposal, v1 can observe a caller-supplied incumbent cluster gross
of 500 bps and remain within a 3000 bps cluster limit. If the bound position
claim actually contains 2500 bps for that symbol, v2 derives 2500 bps, merges
the 600 bps proposal, and blocks the resulting 3100 bps cluster exposure.

This proves only that local position-to-cluster semantics are closed. It is not
market evidence and it does not authenticate the position claim.

## Consumer-first continuation

1. Keep v2 as a pure application contract with no route, registry, or current
   activation.
2. Bind the canonical position claim to the exact v9 signed portfolio snapshot
   claim under a separate adapter.
3. Bind the derived incumbent snapshot hash to the existing freshness/replay
   attestation chain.
4. Bind provider identity and source truth only through their existing signed
   registration and attestation contracts.
5. Consider a read-only presentation consumer only after all four bindings are
   exact. None of those later steps is activated by this ADR.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Caller understates aggregate cluster gross | v2 ignores the supplied aggregate path and derives from positions |
| Duplicate or noncanonical positions | Claim rejected |
| Boolean masquerades as integer gross or sequence | Claim rejected |
| Position symbol is outside the source partition | Evaluation rejected |
| Position content or expected claim hash drifts | Evaluation rejected |
| Projection context partition is spliced | Existing source verification rejects the chain |
| Proposal-only upstream gate blocks | v2 remains blocked and hides merge metrics |
| Result permission is promoted | Exact verifier rejects it |

## Non-effects

- No runtime portfolio reader, database, cache, log, key, network, clock, cursor
  mutation, service, browser, scheduler, backtest, blind test, paper task, live
  task, or publication flow is used.
- No frontend file, HTTP route, current pointer, evidence artifact, or legacy
  artifact is changed.
- The natural-forward single-look evidence chain and pointer-v2 contract remain
  unchanged.
- No profitability claim or trading authority is created.
