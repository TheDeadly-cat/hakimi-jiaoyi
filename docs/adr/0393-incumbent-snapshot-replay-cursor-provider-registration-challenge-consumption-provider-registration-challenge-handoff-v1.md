# ADR 0393: Challenge-consumption provider registration challenge signed-source handoff v1

## Status

Accepted as an isolated, pure synthetic dual-signature and binding contract. It is not mounted into current, does not invoke a provider, and grants no runtime or trading authority.

## Context

ADR0392 proves that the ADR0391 preregistered provider key signed an exact registration claim, but its challenge hash remains caller supplied. ADR0387 cannot be reused directly because it is exact-bound to the different replay-cursor provider preregistration schema and frozen implementation hashes. Mutating ADR0387 or ADR0392 would create compatibility drift.

Two independently valid signatures are still insufficient when a consumer can pair a source-signed challenge with a provider-signed claim for a different challenge or nonce. The handoff itself therefore needs an exact fail-closed contract.

## Decision

Add two isolated versioned contracts:

1. A specialized challenge-source contract that preregisters the challenge authority, binds the exact ADR0391 provider preregistration, challenge id, registration nonce, declared issue/expiry window, purpose, and Ed25519 signature contract, then emits redacted source-signature evidence.
2. A handoff evaluator that rebuilds both source-signature evidence and ADR0392 provider-signature evidence, then requires the signed-challenge hash, registration nonce, and provider-preregistration hash to match end to end.

A local PASS proves only that both preregistered keys signed their exact local documents and that the handoff bindings are exact. It keeps all of these false:

- challenge-authority identity and implementation verification
- authoritative or current time establishment
- challenge freshness and replay consumption
- provider identity, implementation, registration, and key-control continuity
- external conformance, atomicity, durability, and linearizability
- current activation, writer, paper, and live authority

Production code accepts public material and signatures only. It does not contain private keys, call the consumption provider, access files, clocks, network, storage, runtime assets, services, browsers, or schedulers.

## Consumer-first activation order

1. Keep ADR0393 isolated and preserve all current consumers.
2. Bind a separately governed clock attestation to the exact ADR0393 signed-challenge hash and nonce.
3. Establish independently trusted current-time semantics before any freshness claim.
4. Consume the exact registration challenge once through a separately preregistered, conformed, durable provider without circular self-authorization.
5. Run the frozen ADR0391 external conformance plan only after challenge freshness and replay consumption are independently evidenced.
6. Consider a versioned current consumer change only under separate authorization.

## Adversarial matrix

The synthetic tests cover wrong-key self-signing, signature tampering, re-sealed and re-signed freshness promotion, independently valid wrong-challenge and wrong-nonce provider claims, provider-preregistration drift, schema and extra-field aliases, bool-as-int and excessive lifetime claims, evidence mutation, raw-material redaction, input immutability, and forbidden production capabilities.

## Consequences

ADR0393 closes the source-signature and exact dual-signature handoff gaps. It intentionally does not claim trusted current time, freshness, consume-once, external provider conformance, profitability, or trading permission. The natural-forward chain, legacy pack-v5 UNKNOWN behavior, pointer-v2 fields and hashes, and neutral SOURCE -> GAP -> MATURITY -> PERMISSION UI remain unchanged.
