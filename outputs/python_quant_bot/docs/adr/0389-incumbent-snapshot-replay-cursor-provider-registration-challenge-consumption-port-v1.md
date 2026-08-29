# ADR 0389: Provider registration challenge consumption port v1

## Status

Accepted as an isolated consumer-first interface. It is not mounted into current and has no production provider implementation.

## Context

ADR0388 binds signed multi-authority clock observations to an exact signed registration challenge but deliberately does not consume that challenge. A valid challenge can therefore still be replayed.

Two existing CAS boundaries cannot be reused safely. The incumbent-snapshot replay-cursor provider consumes monotonic snapshot sequences and requires snapshot-specific transition evidence. The HTTP mount nonce atomic-reserve protocol is exact-bound to a different source-baseline review replay-key schema. Generalizing either in place would blur namespaces and risk compatibility drift.

## Decision

Define a specialized production port with no implementation:

1. An immutable consume-once command binds the signed-challenge hash, ADR0388 clock-binding evidence hash, registration-nonce hash, expected registry-head hash, expected provider revision, request-id hash, fixed namespace, schema, fingerprint, and command hash.
2. An immutable result has exactly four outcomes: CONSUMED, ALREADY_CONSUMED, COMPARE_AND_SWAP_CONFLICT, and BLOCKED.
3. A consumed result deterministically derives the next registry-head hash and a structural receipt hash from the exact command.
4. Duplicate detection is keyed by signed-challenge hash and must precede stale-head conflict handling.
5. A runtime-checkable Protocol exposes only consume_once(command).

The production module contains no lock, state, registry, storage, file, network, runtime, scheduler, service, or provider implementation. A lock-protected memory fake exists only in tests to exercise process-local ordering and concurrency.

## Consumer-first activation order

1. Freeze command, result, outcome, namespace, and duplicate-before-conflict semantics.
2. Bind exact ADR0388 evidence to command construction in a separate application contract.
3. Preregister an external consumption provider and its signing key/capabilities.
4. Run the frozen sequential and concurrent conformance matrix against that provider.
5. Verify signed receipts, crash recovery, rollback resistance, durability, and linearizable read-after-write independently.
6. Only then consider a versioned current consumer change under separate authorization.

## Adversarial matrix

Tests cover immutable hash-bound commands, role-binding drift, exact port conformance, one successful local transition, sequential and changed-request duplicates, stale-state conflicts, same-challenge concurrency, different-challenge CAS contention, result/hash drift, bool/schema/outcome aliases, authority-field absence, and forbidden production capabilities.

## Consequences

A test-only memory fake can demonstrate one winner under a process-local lock. This is not evidence of external provider identity, atomic storage commit, durability, linearizability, restart recovery, rollback resistance, or challenge consumption in any authorized runtime. Paper/live remain unauthorized. The natural-forward chain, legacy pack-v5 UNKNOWN behavior, pointer-v2, and neutral SOURCE -> GAP -> MATURITY -> PERMISSION UI remain unchanged.
