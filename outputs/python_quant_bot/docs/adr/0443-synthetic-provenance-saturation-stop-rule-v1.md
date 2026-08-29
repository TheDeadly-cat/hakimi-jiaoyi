# ADR 0443: Synthetic provenance saturation stop rule V1

- Status: Accepted
- Date: 2026-08-25
- Scope: research-only provenance governance

## Context

ADR0442 closes a local classification gap by requiring an exact v4 position
transition.  It intentionally retains POSITION_SNAPSHOT_PROVENANCE_UNVERIFIED.
The existing v5 through v11 chain was reviewed before adding another successor.

## Current evidence boundary

- v5 verifies a signature under a preregistered key, but snapshot source truth,
  sequence continuity, and freshness remain false.
- v6 verifies local sequence and freshness arithmetic, but trusted clock,
  atomic current-head persistence, and snapshot source truth remain false.
- v7 adds signed clock evidence, but time-source truth, atomic persistence, and
  snapshot source truth remain false.
- v8 adds local atomic-commit evidence, but compare-and-swap, durability,
  trusted clock, and snapshot source truth remain false.
- v9 adds authenticated latest-head evidence, but latest-head source truth,
  durability, atomic persistence, trusted clock, and snapshot source truth
  remain false.
- v10 adds signed witness quorum evidence, but witness identities,
  independence source truth, durability, trusted clock, and snapshot source
  truth remain false.
- v11 adds signed ownership transitions, but ownership persistence, witness
  identities, witness independence, durability, trusted clock, snapshot source
  truth, and runtime integration remain false.

Implementation fingerprints reviewed:

- v5: 0148a6d07b5dde92ce5e159d18891c0a9fbcac89bc7ffa1277ef2d530ff91d3d
- v6: d7a26b8a4ce3736b5fbebb9d254d03a944cacead5f38e004c81175fcb5a0a08f
- v7: 20d0713686b1d9738661efb4273bbb7f03d0134f73b7cb99519307a08e9d68f3
- v8: fe491c4d01b0d94cb82ab799066594db7b67e2937c8b2723981182c968939b99
- v9: eb0a4627e34bdb0276553d2be10809f334a009d08069aefe250830fd0b65cb64
- v10: 0e6e9a6bf81ca46ef67914d548fdddad2434e5f9fdbe6b4f3274b4b2a614c4ff
- v11: 6fc7def0b3c8d75c7d7b120f7d7942f07310094111d1fc6829d28e8a9ba88b6f

## Decision

Do not create budget-v12, an ADR0442-to-v11 wrapper, or another synthetic
provenance successor solely from the current local documents.  Such a layer
would increase code, test, hash, and migration surface without proving a more
truthful portfolio snapshot.

ADR0442 remains an unbound descriptive candidate.  READONLY_CONSUMER_
PREREGISTRATION and SEPARATE_CURRENT_DECISION remain unauthorized.

## Minimum evidence required before reopening this axis

At least one separately authorized, read-only integration must provide
independent evidence for all applicable items:

1. Provider identity and account-scope binding from outside self-asserted local
   preregistration.
2. Snapshot source truth tied to that provider and account scope.
3. A trusted evaluation clock with independently justified source truth.
4. Durable atomic compare-and-swap or equivalent latest-head semantics.
5. Witness identity and independence evidence if quorum is retained.
6. Explicit authorization for the exact read-only integration and validation
   procedure.

Paper, live, writer, order, current activation, and publication authority are
not prerequisites for a read-only evidence proposal and remain permanently
separate.

## Reopen gate

Any proposal to reopen this axis must identify:

- the external source and trust boundary;
- the exact data accessed and redaction policy;
- failure and stale-data behavior;
- account-scope isolation;
- rollback, equivocation, and durability semantics;
- a consumer-first activation sequence;
- explicit proof that no trading or writer authority is introduced.

Absent that evidence, provenance state remains UNKNOWN and synthetic version
growth is blocked by this ADR.

## Safety

This decision does not access a provider, runtime, database, cache, network,
browser, scheduler, market data, historical bars, or trading system.  It does
not alter current, pointer-v2, the single-look evidence chain, paper/live
locks, or protected UI assets.  It makes no profitability or maturity claim.
