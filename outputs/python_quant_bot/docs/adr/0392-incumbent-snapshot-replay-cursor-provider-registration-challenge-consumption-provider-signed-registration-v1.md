# ADR 0392: Challenge-consumption provider signed registration v1

## Status

Accepted as an isolated, pure synthetic key-control proof. It does not register or invoke an external provider.

## Context

ADR0391 preregisters the external challenge-consumption provider identity, Ed25519 DER-SPKI hash, implementation claim, protocol, schemas, and an unexecuted conformance plan. A local preregistration document does not prove that any actor controls the pinned key.

## Decision

Add three exact versioned documents:

1. A registration claim binding the exact ADR0391 preregistration hash, caller-supplied challenge hash, registration-nonce hash, pinned provider-key hash, implementation claim, protocol, and signature contract.
2. A signed candidate carrying caller-supplied canonical Ed25519 DER-SPKI material and a detached signature over the raw claim SHA-256 bytes.
3. Redacted verification evidence rebuilt from all expected inputs.

A local PASS may state only that the preregistered public key signed the exact claim and that key possession was observed for that signature. It must keep all of these false:

- provider organization identity and implementation verification
- provider registration and key-control continuity
- challenge-source authority, freshness, and registration replay consumption
- external conformance, atomicity, durability, and linearizability
- consume-once, current activation, paper, live, and writer authority

Production code accepts public material and signatures only. Private keys may exist only in synthetic tests. The module does not access files, clocks, network, storage, runtime assets, services, browsers, schedulers, or provider methods.

## Adversarial matrix

Tests cover wrong-key self-signing, signature tampering, re-sealed and re-signed registration promotion, signed-document schema/field aliases, challenge and nonce drift, preregistration drift, evidence mutation, raw-material redaction, malformed base64, short signatures, non-Ed25519 keys, determinism, input immutability, and forbidden production capabilities.

## Consequences

ADR0392 closes only the local preregistered-key signature gap. ADR0391 conformance cases remain unexecuted. Paper/live remain unauthorized. The natural-forward chain, legacy pack-v5 UNKNOWN behavior, pointer-v2, and neutral SOURCE -> GAP -> MATURITY -> PERMISSION UI remain unchanged.
