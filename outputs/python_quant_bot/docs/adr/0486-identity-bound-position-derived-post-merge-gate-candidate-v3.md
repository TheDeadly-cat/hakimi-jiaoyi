# ADR0486: Identity-bound position-derived post-merge gate candidate v3

Date: 2026-08-25

## Status

Accepted as a synthetic, unmounted composition candidate. It does not replace or
activate ADR0484, ADR0485, batch-v1, position-derived post-merge v2, provider
freshness/replay contracts, HTTP routes, current pointers, paper, or live execution.

## Current gap evidence

Position-derived post-merge v2 correctly derives incumbent cluster exposure from
canonical positions and closes caller-supplied aggregate understatement. In the
inherited synthetic chain, a canonical proposal produces an observed within-limit
result, while its unresolved alias produces no result. The v2 result has no
canonical identity batch hash. Both paths remain unauthorized.

The missing seam is therefore not exposure arithmetic. It is an exact binding
from ordered canonical tickets to requested proposal gross amounts before those
amounts enter the existing position-derived post-merge calculation.

## Decision

1. Accept exact ordered proposal rows containing proposal ID, venue, symbol, and
   plain-integer requested gross basis points.
2. Strip only the amount field and exactly verify the corresponding ADR0485 batch
   identity gate, preserving proposal IDs and order.
3. Resolve each occurrence's canonical-instrument and budget-symbol hashes against
   the verified registry, then construct existing `ClusterExposureProposalV1`
   values with the same proposal ID and requested amount.
4. Seal ordered occurrence hashes, amounts, policy hash, ADR0485 hash, projection
   hash, and incumbent position-claim hash into a dedicated exposure-binding hash.
5. Only a projected batch with zero unknown and zero duplicate canonical identities
   may enter position-derived post-merge v2. Duplicate, unknown, and excluded batches
   stop before risk arithmetic and expose no post-merge metrics.
6. For an eligible batch, recompute and exactly verify batch-v1, call the unchanged
   position-derived v2 arithmetic, and exactly verify its result.
7. Preserve the incumbent provider identity, source truth, and freshness gaps as
   explicit blockers. An observed within-limit result remains `NOT_AUTHORIZED`.

## Consumer-first activation order

1. Keep this composition candidate unmounted and synthetic.
2. Require the already-defined signed incumbent provider, freshness, replay cursor,
   and conformance chain to bind the same position claim and derived snapshot.
3. Bind exposure policy provenance and lifecycle to the same evaluation envelope.
4. Add a neutral read-only projection only after exact consumer registration.
5. Require independent adversarial review and a separate activation decision.
   This ADR does not switch current or authorize any execution mode.

## Adversarial matrix

- unique canonical tickets must preserve requested totals through post-merge;
- incumbent positions plus an alias-resolved proposal must preserve cluster-limit
  breaches from the existing v2 arithmetic;
- duplicate canonical identities, unknown identities, and excluded batches must
  stop before post-merge and hide all risk metrics;
- amount mutation must change both exposure binding and exact result;
- proposal reorder/ID splice, invalid amount types/ranges, incumbent claim drift,
  replacement hashes, and resealed authority promotion must fail closed;
- provider identity, source truth, freshness, paper, and live permissions remain
  native false and visible as blockers.

## Safety boundaries

All evidence is pure synthetic and in memory. No market data, old K-line,
runtime, database, cache, log, credential, backtest, blind test, scheduler,
service, browser, paper, or live task is used. Passing these contracts is not
profitability evidence, strategy maturity, or trading authorization. The current
single-look chain, legacy pack-v5 UNKNOWN behavior, and pointer-v2 no-reissue
contract remain unchanged.
