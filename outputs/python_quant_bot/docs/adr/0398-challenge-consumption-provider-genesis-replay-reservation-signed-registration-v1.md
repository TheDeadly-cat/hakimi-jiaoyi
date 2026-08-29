# ADR 0398: Genesis replay-reservation provider signed registration v1

## Status

Accepted as an isolated, pure synthetic provider-key possession proof. It does not register or invoke a replay-reservation provider.

## Context

ADR0397 preregisters the external genesis replay-reservation provider identity, Ed25519 DER-SPKI hash, implementation claim, protocol, schemas, and an unexecuted conformance plan. A hash-only preregistration does not prove that any actor controls the pinned provider key.

A pure synthetic gap probe confirmed provider-key-possession-verified false, provider-registered false, no challenge-source binding, and no runtime mutations.

## Decision

Add three exact versioned documents:

1. A provider registration claim binding the exact ADR0397 preregistration, caller-supplied challenge hash, registration nonce, pinned provider key, implementation claim, protocol, and signature contract.
2. A signed candidate carrying caller-supplied canonical Ed25519 DER-SPKI material and a detached signature over the raw claim-hash bytes.
3. Redacted evidence rebuilt from all expected inputs.

A local PASS may state only that the preregistered public key signed the exact claim and key possession was observed for that signature. Provider organization identity, implementation, registration, key-control continuity, challenge source, freshness, replay consumption, external conformance, atomicity, durability, linearizability, signed reservation receipt, actual reservation, and all runtime or trading authority remain false.

Production code accepts public material and signatures only. Private keys exist only in synthetic tests. It does not call reserve-once or access files, clocks, network, storage, runtime assets, services, browsers, or schedulers.

## Consumer-first activation order

1. Keep ADR0398 isolated and preserve all current consumers.
2. Add a separately preregistered challenge authority and exact source-signed challenge.
3. Bind independently governed clock observations without promoting current time or freshness.
4. Consume the registration challenge through a non-circular, independently conformed bootstrap path.
5. Run the ADR0397 external provider conformance plan.
6. Verify signed reservation receipts, recovery, rollback resistance, durability, and linearizability.
7. Consider a versioned current consumer only under separate authorization.

## Adversarial matrix

Tests cover wrong-key self-signing, signature tampering, re-sealed and re-signed registration promotion, signed-document schema and extra-field aliases, challenge and nonce drift, preregistration drift, evidence mutation, material redaction, malformed base64, short signatures, non-Ed25519 keys, determinism, input immutability, and forbidden production capabilities.

## Consequences

ADR0398 closes only local preregistered-key signature proof. Its challenge remains caller supplied. No challenge source, trusted time, freshness, replay consumption, external conformance, reservation, profitability evidence, or trading permission is created. The natural-forward chain, legacy pack-v5 UNKNOWN behavior, pointer-v2 fields and hashes, and neutral SOURCE -> GAP -> MATURITY -> PERMISSION UI remain unchanged.
