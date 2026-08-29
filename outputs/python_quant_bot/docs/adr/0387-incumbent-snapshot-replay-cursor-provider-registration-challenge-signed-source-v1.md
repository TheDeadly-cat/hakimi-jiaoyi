# ADR 0387: Incumbent snapshot replay-cursor provider registration challenge signed source v1

## Status

Accepted as an isolated, pure synthetic contract. It is not mounted into current and grants no runtime or trading authority.

## Context

ADR0385 preregisters the replay-cursor provider identity and capability claim. ADR0386 can prove that the preregistered provider public key signed an exact registration claim, but its challenge hash is caller supplied. Therefore ADR0386 alone cannot prove who produced the challenge, whether its claimed time window is authoritative, whether it is fresh, or whether it has been consumed exactly once.

Treating a caller supplied challenge as authoritative would allow a valid old registration response to be replayed while still passing local signature verification.

## Decision

Add four exact, versioned documents:

1. A redacted challenge-authority preregistration that pins authority identifiers, the DER-SPKI public-key hash, trust domain, and implementation claim.
2. A challenge that binds the exact ADR0385 preregistration hash, authority-preregistration hash, challenge-id hash, registration-nonce hash, declared issue/expiry milliseconds, purpose, and signature contract.
3. A signed challenge candidate carrying caller-supplied Ed25519 DER-SPKI public material and a detached signature over the raw challenge SHA-256 bytes.
4. Redacted verification evidence rebuilt from all expected inputs.

A successful local evaluation may state only that the preregistered challenge public key signed the exact challenge and that the declared time window is structurally bounded to at most 300 seconds. It must keep these claims false:

- challenge-authority identity and implementation verification
- authoritative time-source verification
- challenge freshness and one-time consumption
- provider registration and external conformance
- current activation, writer, paper, and live authority

Production code accepts public material only. Synthetic tests may generate private keys in memory; production code must not import or accept private-key objects and must not access files, clocks, network, storage, runtime assets, services, browsers, or schedulers.

## Consumer-first activation order

1. Keep this module isolated and prove exact local challenge-source signature behavior.
2. Feed the signed-challenge hash into ADR0386 and prove the dual-signature handoff synthetically.
3. Preregister and independently conform an external challenge authority.
4. Bind a separately trusted time receipt to the exact challenge hash.
5. Atomically consume the challenge through an independently verified replay/CAS provider.
6. Only then consider a versioned current consumer change under separate authorization.

## Adversarial matrix

The targeted tests cover wrong-key self-signing, signature tampering, re-sealed and re-signed freshness promotion, nonce/time/provider binding drift, schema and extra-field aliases, evidence mutation, raw-material redaction, malformed base64, short signatures, bool-as-int time aliases, forbidden production capabilities, and the ADR0387-to-ADR0386 dual-signature handoff.

## Consequences

This closes the local challenge-source cryptographic gap only. No trusted clock, freshness oracle, durable replay registry, external provider, market data, profitability evidence, or trading permission is created. The natural-forward chain, legacy pack-v5 UNKNOWN behavior, pointer-v2, and neutral SOURCE -> GAP -> MATURITY -> PERMISSION UI remain unchanged.
