# ADR 0393: Challenge-consumption provider registration handoff v1

## Status

Accepted as an isolated, pure synthetic signed-source and dual-signature binding contract. It is not mounted into current, does not invoke a provider, and grants no runtime or trading authority.

## Context

ADR0392 proves that the ADR0391 preregistered provider key signed an exact registration claim, but its challenge hash remains caller supplied. ADR0387 cannot be reused directly because it is exact-bound to another provider preregistration schema and frozen implementation hashes. Mutating ADR0387 or ADR0392 would create compatibility drift.

Two independently valid signatures are also insufficient when a consumer can pair a source-signed challenge with a provider-signed claim for a different challenge or nonce. The handoff therefore needs its own exact fail-closed contract.

## Decision

Add two isolated versioned contracts:

1. A specialized challenge-source contract that preregisters the challenge authority and binds the exact ADR0391 preregistration, challenge id, registration nonce, declared issue/expiry window, purpose, and Ed25519 signature.
2. A handoff evaluator that rebuilds the source-signature evidence and ADR0392 provider-signature evidence, then requires signed-challenge hash, nonce, and provider-preregistration hash equality end to end.

A local PASS proves only that both preregistered keys signed their exact local documents and that the handoff bindings match. It keeps challenge-authority identity, trusted or current time, freshness, replay consumption, provider registration, external conformance, atomicity, durability, linearizability, current activation, writer, paper, and live authority false.

Production code accepts public material and signatures only. It has no private keys, provider call, file or clock access, network, storage, runtime assets, services, browser, or scheduler.

## Consumer-first activation order

1. Keep ADR0393 isolated and preserve all current consumers.
2. Bind a separately governed clock attestation to the exact ADR0393 signed-challenge hash and nonce.
3. Establish independently trusted current-time semantics before any freshness claim.
4. Consume the exact registration challenge once through a separately preregistered, conformed, durable provider without circular self-authorization.
5. Run ADR0391 external conformance only after freshness and replay consumption are independently evidenced.
6. Consider a versioned current consumer change only under separate authorization.

## Adversarial matrix

Tests cover wrong-key self-signing, signature tampering, re-sealed freshness promotion, independently valid wrong-challenge and wrong-nonce pairings, preregistration drift, schema and extra-field aliases, bool-as-int and excessive lifetime claims, evidence mutation, material redaction, input immutability, and forbidden production capabilities.

## Consequences

ADR0393 closes the source-signature and exact handoff gaps. It does not claim trusted current time, freshness, consume-once, external conformance, profitability, or trading permission. The natural-forward chain, legacy pack-v5 UNKNOWN behavior, pointer-v2 fields and hashes, and neutral SOURCE -> GAP -> MATURITY -> PERMISSION UI remain unchanged.
