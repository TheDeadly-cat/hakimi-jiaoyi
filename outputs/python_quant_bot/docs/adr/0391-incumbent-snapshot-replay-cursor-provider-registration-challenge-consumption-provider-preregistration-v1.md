# ADR 0391: Registration challenge consumption provider preregistration v1

## Status

Accepted as an isolated, local preregistration and unexecuted conformance plan. No external provider is contacted or registered.

## Context

ADR0389 freezes the specialized consume-once port, and ADR0390 binds exact ADR0388 evidence into its command. The next consumer-first step is to state which external identity, key hash, implementation claim, namespace, protocol, command/result schemas, and signed receipt capability would be required before any provider invocation.

The earlier replay-cursor provider preregistration cannot be reused because it is exact-bound to monotonic snapshot-sequence CAS schemas. A challenge-consumption provider has a different key, duplicate, conflict, receipt, and recovery contract.

## Decision

Add two exact versioned documents:

1. A redacted provider preregistration that pins identity claims, Ed25519 DER-SPKI hash, trust domain, provider implementation claim, ADR0389 namespace/protocol/command/result schemas, ADR0390 implementation, and the target signed-consumption-receipt schema.
2. A frozen 13-case conformance plan covering matching consume, duplicate-before-conflict, changed-request duplicate behavior, same-challenge and distinct-challenge concurrency, stale-state conflict, exact result/head binding, timeout-after-commit idempotency, restart recovery, rollback resistance, signed receipts, and linearizable read-after-write.

Every conformance case starts with executed false and observed null. Exact local document equality must never imply provider registration, identity verification, key possession, implementation verification, external conformance, atomicity, durability, linearizability, or signed receipt verification.

Production code does not accept raw keys or private keys, invoke the provider, access files or clocks, use network or storage, mutate runtime state, or create a memory fake.

## Consumer-first activation order

1. Keep ADR0391 isolated and freeze the external contract.
2. Obtain an independently authenticated external provider identity and public key under separate authorization.
3. Prove key possession with an exact signed registration challenge.
4. Run all 13 frozen cases against the external provider and an independent observer.
5. Verify signed receipts, restart recovery, rollback resistance, durability, and linearizable read-after-write.
6. Only then consider a versioned current consumer change under separate authorization.

## Consequences

ADR0391 closes the provider-capability preregistration gap but adds no operational provider. Paper/live remain unauthorized. The natural-forward chain, legacy pack-v5 UNKNOWN behavior, pointer-v2, and neutral SOURCE -> GAP -> MATURITY -> PERMISSION UI remain unchanged.
