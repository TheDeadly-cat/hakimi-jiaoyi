# ADR 0396: Challenge-consumption provider threshold genesis admission v1

## Status

Accepted as an isolated, pure synthetic threshold-signature verifier and unreserved replay-key derivation. It does not authorize or execute genesis admission.

## Context

ADR0395 freezes a structurally non-circular offline root topology but has no signed admission claim. A topology hash alone cannot prove that the pinned root keys approved the exact candidate, clock binding, nonce, or expected genesis head. Reusing trusted-clock-authority-v3 would be incorrect because its receipts and quorum semantics are exact-bound to time observations.

## Decision

Add four exact versioned documents:

1. A genesis-admission claim that rebuilds ADR0395 and ADR0394, then binds topology, root set, candidate preregistration, signed challenge, clock evidence, admission nonce, expected genesis head, target revision zero, and signature contract.
2. A threshold-signed candidate carrying caller-supplied canonical Ed25519 DER-SPKI material and detached signatures over the raw claim-hash bytes.
3. Redacted verification evidence requiring every supplied signature to be cryptographically valid, mapped to a distinct pinned root key, and to meet the ADR0395 strict-majority threshold.
4. An independent replay key derived from topology, root set, provider, clock evidence, claim, signed candidate, verification evidence, nonce, and expected genesis head.

A local PASS proves only exact local threshold signatures and key possession. External root identity, governance, organizational independence, trusted current time, freshness, replay reservation, atomic genesis creation, provider registration, and external conformance remain false.

The replay key is deliberately emitted with status BLOCKED and replay-key-reserved false. Exact derivation is not storage evidence and cannot authorize progression.

Production code accepts public verification material only. Private keys exist only in synthetic tests. No provider, file, clock, network, storage, runtime asset, service, browser, or scheduler is accessed.

## Consumer-first activation order

1. Keep ADR0396 isolated and preserve all current consumers.
2. Independently authenticate root identities, governance, key lifecycle, and organizational independence.
3. Reserve the exact ADR0396 replay key through a separate atomic, durable, linearizable registry.
4. Verify signed reservation receipts and rollback resistance.
5. Execute one atomic genesis registry creation with an independent observer.
6. Complete ADR0391 external provider conformance.
7. Consider a versioned current consumer only under separate authorization.

## Adversarial matrix

Tests cover below-threshold signing, wrong-key self-signing, outsider signers, signature tampering, duplicate signer records, re-sealed governance promotion, clock-evidence mutation, expected-hash drift, topology drift, nonce-sensitive replay-key derivation, malformed and non-Ed25519 keys, material redaction, and forbidden production capabilities.

## Consequences

ADR0396 closes the local threshold-signature and replay-key derivation gaps only. No replay reservation, genesis execution, current-time truth, freshness, provider conformance, profitability evidence, or trading permission is created. The natural-forward chain, legacy pack-v5 UNKNOWN behavior, pointer-v2 fields and hashes, and neutral SOURCE -> GAP -> MATURITY -> PERMISSION UI remain unchanged.
