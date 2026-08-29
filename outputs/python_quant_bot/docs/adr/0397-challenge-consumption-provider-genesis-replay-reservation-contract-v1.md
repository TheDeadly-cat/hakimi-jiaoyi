# ADR 0397: Genesis-admission replay-reservation contract v1

## Status

Accepted as an isolated consumer-first port, provider preregistration, and unexecuted conformance plan. No production provider is implemented or invoked.

## Context

ADR0396 derives an exact genesis-admission replay key but explicitly leaves replay-key-reserved, atomic reservation, durability, and linearizability false. A pure synthetic call-chain probe confirmed there is no reservation-provider identity or protocol binding.

ADR0389 cannot be reused because it consumes replay-cursor registration challenges under a different namespace and binds different command roles. Aliasing it would blur duplicate keys, receipt semantics, and compatibility contracts.

## Decision

Add a specialized immutable port with four outcomes: RESERVED, ALREADY_RESERVED, COMPARE_AND_SWAP_CONFLICT, and BLOCKED. Its command binds the ADR0396 replay-key hash, threshold-admission evidence hash, expected registry head, expected provider revision, request id, namespace, schema, fingerprint, and command hash.

Duplicate detection is keyed by replay-key hash and must precede stale-state conflict handling. RESERVED deterministically derives a returned head and structural receipt hash. Production code defines messages and a runtime-checkable Protocol only; a lock-protected memory fake exists solely in tests.

Also add a redacted external-provider preregistration that pins identity claims, Ed25519 DER-SPKI hash, implementation claim, namespace, protocol, command/result schemas, port implementation, ADR0396 implementation, and a future signed-receipt schema.

Freeze thirteen conformance cases covering exact reserve, duplicate ordering, changed-request idempotency, concurrency, CAS contention, stale-state conflict, result/head binding, timeout retry, restart recovery, rollback resistance, signed receipts, and linearizable read-after-write. Every case starts executed false and observed null.

## Consumer-first activation order

1. Keep ADR0397 isolated and preserve all current consumers.
2. Independently authenticate provider identity, key, implementation, and observer.
3. Prove key possession through a separately sourced signed registration challenge.
4. Run all thirteen cases against the external provider.
5. Verify signed receipts, crash recovery, rollback resistance, durability, and linearizability.
6. Bind exact successful reservation evidence into genesis creation.
7. Consider a versioned current consumer only under separate authorization.

## Adversarial matrix

Tests cover role-bound immutable commands, bool/hash/schema aliases, exact reservation, duplicate-before-conflict, same-key and distinct-key concurrency, result/hash drift, outcome aliases, invalid conflict claims, protocol-only production code, preregistration aliases, identity drift, unexecuted-plan integrity, re-sealed execution promotion, material redaction, and forbidden capabilities.

## Consequences

ADR0397 closes only the consumer contract and preregistration gaps. The memory fake is not external atomicity, durability, linearizability, restart recovery, provider identity, signed receipt, replay reservation, genesis execution, profitability evidence, or trading permission. The natural-forward chain, legacy pack-v5 UNKNOWN behavior, pointer-v2 fields and hashes, and neutral SOURCE -> GAP -> MATURITY -> PERMISSION UI remain unchanged.
