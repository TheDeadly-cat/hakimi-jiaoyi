# ADR 0477: v9 position-derived snapshot replay-cursor CAS binding v1

- Status: accepted as an uncommitted synthetic research binding
- Date: 2026-08-25
- Scope: exact local freshness-to-CAS intent and simulation binding

## Context

ADR 0476 binds the v9 signed snapshot, position-derived incumbent exposure,
snapshot hash, snapshot sequence, and freshness/replay candidate. The existing
CAS transition contract can build an intent and simulate a compare-and-swap
against an observed cursor, but it accepts a caller-supplied
`IncumbentSnapshotFreshnessReplayResultV1`.

That result type is self-fingerprinted but its source is not recomputed by the
CAS contract. A caller can manually construct a candidate-status dataclass with
matching attestation and cursor hashes, assign an arbitrary post-merge result,
fingerprint it, and obtain `ADVANCED_IN_RETURNED_CURSOR` without ever invoking
the post-merge or freshness evaluator.

## Synthetic gap proof

A hand-built freshness candidate with
`post_merge_status=FORGED_WITHOUT_SOURCE_EVALUATION` was accepted by the legacy
CAS intent builder and produced an advanced returned cursor candidate. The
receipt correctly denied atomic storage commit, but no contract connected that
candidate to ADR 0476.

## Decision

Add a composite CAS binding that:

1. Accepts only an exactly reconstructed ADR 0476 fresh-unreplayed candidate.
2. Does not accept any caller-provided freshness result.
3. Reconstructs the exact freshness result from the bounded ADR 0476 fields and
   fingerprints that reconstruction.
4. Requires the raw attestation and base cursor to equal the objects in the
   ADR 0476 verification context.
5. Builds the existing CAS intent with a strict request nonce.
6. Simulates the transition against an explicitly hash-bound observed cursor.
7. Preserves advanced, compare-and-swap conflict, already-consumed, and
   nonmonotonic outcomes without promotion.
8. Emits the returned cursor only as an in-memory, uncommitted candidate.
9. Exactly rebuilds the complete result and rejects authority promotion.

## Safety interpretation

`OBSERVED_UNCOMMITTED_RETURNED_CURSOR_CANDIDATE` means only that the existing
pure CAS simulation returned a changed cursor for matching local inputs. It
does not mean that a provider was called, that compare-and-swap occurred in a
shared store, or that any cursor was durably written.

The observed cursor is still caller-supplied and unauthenticated. Provider
registration, source truth, consume-once verification, atomic commit,
durability, linearizable read, replay-registry persistence, runtime binding,
current admission, paper, live, profitability, and trading authority remain
false or unauthorized.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Caller supplies forged freshness dataclass to old CAS | Gap proof succeeds before binding |
| ADR 0476 source is blocked | No CAS intent is built |
| ADR 0476 result or verification context drifts | Exact verification rejects |
| Observed cursor changed without consuming candidate | CAS conflict remains `UNKNOWN` |
| Observed cursor already consumed candidate | Result remains blocked |
| Observed high-water is not below candidate sequence | Result remains blocked |
| Expected observed cursor hash drifts | Binding rejects |
| Returned cursor is changed in memory | Commit, durability, and persistence remain false |
| Result authority is promoted | Exact reconstruction rejects |

## Consumer-first continuation

1. Keep this CAS binding unmounted and outside routes, registries, and current.
2. Bind the observed cursor to the existing signed replay-cursor provider
   registration and challenge-consumption contracts.
3. Require an actual provider result that proves atomic compare-and-swap,
   durable commit, linearizable readback, and consume-once semantics.
4. Do not describe replay protection as operational until those provider facts
   are exact and independently reviewed.

## Non-effects

- No provider is invoked and no database, cache, log, key, network, service,
  browser, scheduler, runtime reader, backtest, blind test, paper task, live
  task, cursor write, route, registry, current pointer, or publication flow is
  used.
- No frontend or existing evidence artifact is changed.
- The natural-forward single-look evidence chain, legacy pack-v5 behavior, and
  pointer-v2 contract remain unchanged.
- No profitability claim or trading authority is created.
