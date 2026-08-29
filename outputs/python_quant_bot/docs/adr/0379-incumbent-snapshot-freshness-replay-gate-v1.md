# ADR 0379: Incumbent Snapshot Sequence Freshness and Replay Gate v1

- Status: implemented, additive, inactive
- Date: 2026-08-24
- Scope: pure synthetic sequence freshness and replay-candidate contract
- Authority: none

## Context

ADR0378 binds incumbent exposure content but has no temporal ordering. A valid
old snapshot can be replayed, a sequence can move backward, or a candidate can
lag too far behind the known stream head. Content integrity is not freshness.

## Decision

Add three independently hashed inputs and one preregistered policy:

1. Snapshot sequence attestation bound to stream, projection, snapshot hash, and
   positive sequence.
2. Sequence-head reference bound to the same stream and projection.
3. Replay cursor with high-water sequence, high-water attestation identity, and
   a bounded canonical set of consumed attestation hashes.
4. Policy for maximum sequence lag and maximum forward jump.

The gate recomputes ADR0378, exactly verifies all temporal objects, and checks
head ordering, replay membership, monotonic high water, forward jump, and lag.

## Critical boundary

The gate never mutates or persists the cursor. Every result has
`cursor_mutation_performed=false`. Reusing the same unchanged cursor can produce
the same candidate result again. Operational anti-replay requires a future
atomic compare-and-set registry and is not claimed here.

This contract measures sequence freshness only. It does not use a wall clock,
market session calendar, or maximum elapsed duration. Those remain separate
activation requirements.

## Status vocabulary

- `UNKNOWN`
- `BLOCKED_INCUMBENT_SNAPSHOT_FRESHNESS_OR_REPLAY`
- `BLOCKED_UPSTREAM_POST_MERGE_GATE`
- `OBSERVED_FRESH_UNREPLAYED_SNAPSHOT_CANDIDATE`

Every status remains research-only and unauthorized.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Sequence 10, head 10, high water 9, unseen | Fresh unreplayed candidate only |
| Sequence/hash already consumed | Replay and nonmonotonic blockers |
| Sequence lag 2 with maximum 1 | Stale blocker |
| Candidate sequence above head | `UNKNOWN` |
| Forward jump above policy | Jump blocker |
| Snapshot, stream, projection, or expected hash drift | No result |
| Duplicate/noncanonical cursor hashes | Cursor rejected |
| Fresh snapshot with post-merge exposure breach | Upstream post-merge block |
| Repeated call with unchanged cursor | Same result, no mutation |

## Boundaries

No wall clock, market calendar, account, broker, DB, cache, log, registry,
compare-and-set, HTTP, engine, runtime, writer, scheduler, pointer, UI, paper, or
live operation is introduced. Passing tests proves local sequence and cursor
logic only, not current portfolio state, operational replay prevention, market
validity, profitability, evidence maturity, or trading authorization.
