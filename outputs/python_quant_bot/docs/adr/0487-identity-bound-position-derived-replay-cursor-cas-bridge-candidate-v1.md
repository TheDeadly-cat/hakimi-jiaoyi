# ADR0487: Identity-bound position-derived replay-cursor CAS bridge candidate v1

Date: 2026-08-25

## Status

Accepted as a synthetic, unmounted bridge candidate. It does not replace or
activate ADR0484-ADR0486, v9 signed-snapshot reconciliation, freshness/replay,
CAS transition, cursor providers, HTTP routes, current pointers, paper, or live.

## Current gap evidence

The ADR0486 identity/amount chain and the v9 freshness/CAS chain can be rebuilt
over the same v9 projection context. Their position-derived result hashes and
derived incumbent snapshot hashes are exactly equal, and both remain unauthorized.
However, neither result seals the other's hash. A valid identity/amount result
could therefore be presented beside an unrelated valid CAS result unless a
consumer performs an explicit cross-binding.

The identity registry is projection-independent by design. The ADR0485 consumer
must be rebuilt against the actual v9 projection and verification context; fixture
projection hashes are never assumed interchangeable.

## Decision

1. Exactly verify the ADR0486 identity-bound post-merge result and its full
   verification context.
2. Exactly verify the v9 signed-snapshot freshness binding and the uncommitted
   replay-cursor CAS binding with their original contexts.
3. Require equality of position-claim, position-result, derived-snapshot,
   projection, source-batch, and snapshot-sequence hashes across both chains.
4. Bind each ADR0486 proposal occurrence to the canonical CAS-chain proposal by
   proposal-ID hash, resolved budget-symbol hash, requested amount, and order.
5. Seal ADR0486, freshness, CAS, attestation, observed/returned cursor, request
   nonce, exposure binding, and snapshot hashes into one redacted bridge result.
6. Preserve CAS conflict as UNKNOWN and replay/nonmonotonic outcomes as BLOCKED.
   An advanced returned cursor is still only an in-memory candidate.
7. Keep provider registration, source truth, consume-once, atomic/durable commit,
   linearizable read, persistence, cursor write, current admission, paper, and
   live authority native false.

## Consumer-first activation order

1. Keep this cross-binding candidate unmounted and synthetic.
2. Bind the same bridge hash into the existing signed replay-cursor provider
   registration/receipt and independent conformance-evidence chain.
3. Require an actual provider CAS receipt with durable, consume-once, linearizable
   semantics before any persistence claim. Returned cursors are not receipts.
4. Add neutral read-only presentation only after exact consumer registration.
5. Require independent adversarial review and a separate activation decision.
   This ADR does not switch current or authorize execution.

## Adversarial matrix

- alias-resolved ADR0486 and canonical v9 CAS proposals must share proposal ID,
  amount, position-result, position-claim, snapshot, projection, and sequence;
- amount, freshness-result, CAS snapshot, context, or hash splice must fail;
- CAS compare-and-swap conflict remains UNKNOWN and returned-cursor replay remains
  BLOCKED without any commit claim;
- a fixture projection mismatch must be resolved by rebuilding ADR0485 against
  the actual v9 context, never by assuming hash equivalence;
- resealed authority promotion must fail exact reconstruction;
- output must redact proposal, alias, venue, stream, signatures, and raw contexts.

## Safety boundaries

All evidence is pure synthetic and in memory. No market data, old K-line,
runtime, database, cache, log, credential, backtest, blind test, scheduler,
service, browser, paper, or live task is used. Passing these contracts is not
profitability evidence, strategy maturity, provider persistence, or trading
authorization. The current single-look chain, legacy pack-v5 UNKNOWN behavior,
and pointer-v2 no-reissue contract remain unchanged.
