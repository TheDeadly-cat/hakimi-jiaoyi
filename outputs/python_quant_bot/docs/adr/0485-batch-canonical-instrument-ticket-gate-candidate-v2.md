# ADR0485: Batch canonical instrument ticket gate candidate v2

Date: 2026-08-25

## Status

Accepted as a synthetic, unmounted consumer candidate. It does not activate or
replace ADR0484 identity binding, batch preflight v1, post-merge exposure gates,
HTTP routes, current pointers, paper, or live execution.

## Current gap evidence

Batch preflight v1 correctly deduplicates exact symbols and collapses correlated
symbols by their preregistered source cluster. In the inherited synthetic chain,
`A,A` has two occurrences, one unique symbol, and one effective ticket. The
unresolved pair `A,A.N` has two unique strings and one unknown symbol, producing
`UNKNOWN_BATCH_CONTAINS_UNVERIFIED_SYMBOL`. Permission remains `NOT_AUTHORIZED`.

This is fail-closed and not a current bypass. It demonstrates that a future
consumer cannot safely decide whether multiple venue aliases are one economic
instrument until it consumes the ADR0484 identity contract.

## Decision

1. Accept an ordered, non-empty batch of at most 64 exact three-field proposals:
   unique proposal ID, venue ID, and symbol.
2. Build and exactly verify one ADR0484 identity binding per occurrence. Proposal
   IDs and occurrence order are hash-bound so identities cannot be reassigned or
   reordered against later exposure amounts.
3. Resolve each verified binding back to its sealed registry entry by entry hash,
   then independently match canonical-instrument and budget-symbol hashes.
4. Pass only resolved budget symbols to batch preflight v1 and exactly verify its
   existing symbol membership and source-cluster collapse result.
5. Count unique canonical instrument hashes before cluster tickets. Multiple
   proposal IDs sharing one canonical identity count as one economic ticket and
   produce `BLOCKED_BATCH_DUPLICATE_CANONICAL_INSTRUMENT`.
6. Unknown instrument identity prevents batch-v1 derivation and remains UNKNOWN.
   A known identity mapped outside the projection inherits batch-v1 UNKNOWN.
   History-coverage exclusion takes precedence over duplicate-identity status.
7. Output only hashes, counts, neutral decision stages, and native-false authority.

## Consumer-first activation order

1. Keep this verifier-only batch candidate unmounted and synthetic.
2. Replace synthetic identity entries with independently governed issuer,
   share-class, venue, and lifecycle provenance plus freshness/replay receipts.
3. Bind ordered proposal IDs and canonical identities to requested exposure in a
   position-derived preflight, then require the post-merge gate to verify the
   same batch identity hash before adding incumbent exposure.
4. Add neutral read-only presentation only after exact consumer registration.
5. Require independent adversarial review and a separate activation decision.
   This ADR does not switch current or authorize any execution mode.

## Adversarial matrix

- canonical and explicit aliases of one instrument must produce one canonical
  ticket and an explicit duplicate block;
- cross-venue and NFKC/case variants must not create additional tickets;
- unknown aliases must prevent downstream batch derivation;
- excluded aliases must inherit the history-coverage exclusion;
- a known identity outside the projected universe must inherit batch-v1 UNKNOWN;
- duplicate proposal IDs, oversized batches, replacement registries, reordered
  proposals, and resealed authority promotion must fail closed;
- output must redact raw proposal, venue, symbol, and canonical identity values.

## Safety boundaries

All evidence is pure synthetic and in memory. No market data, old K-line,
runtime, database, cache, log, credential, backtest, blind test, scheduler,
service, browser, paper, or live task is used. Passing these contracts is not
profitability evidence, strategy maturity, or trading authorization. The current
single-look chain, legacy pack-v5 UNKNOWN behavior, and pointer-v2 no-reissue
contract remain unchanged.
