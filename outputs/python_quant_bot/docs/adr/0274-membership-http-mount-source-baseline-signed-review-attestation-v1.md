# ADR 0274: Membership HTTP mount source-baseline signed review attestation-v1

## Status

Accepted as a cryptographic claim-binding contract. It verifies an Ed25519
signature but does not authenticate real-world identity, process independence,
key governance, nonce uniqueness, replay durability, source observation,
independent-review completion, route registration, or mount authority.

## Context

ADR0273 binds an unauthenticated source-baseline review claim. A synthetic audit
confirmed that reviewer-key registration, detached signature, review nonce,
replay-registry receipt, and real-world identity evidence remain absent.

The project already separates local reviewer-key binding, unsigned attestation,
signed assembly, and verified evidence for another review domain. This ADR
reuses that trust model rather than treating signature verification as review
completion.

## Decision

Add four exact layers:

- redacted local Ed25519 reviewer-key registration
- unsigned attestation binding the exact request, claim intake, source pins, and nonce hash
- signed-attestation assembly carrying a canonical detached signature
- evidence evaluation that rebuilds every predecessor and verifies the signature

The signed message is the 32-byte digest represented by the unsigned strict
canonical attestation hash. Public keys must be canonical 32-byte base64 and
signatures canonical 64-byte base64. Registration, unsigned, signed, and
evidence documents use separate schemas and hashes.

Evidence stores only hashes and calibrated facts. It does not embed reviewer
identifiers, public-key material, signature material, raw source, review claim,
or verification contexts.

A verified detached signature proves only possession of the corresponding
private key over the exact bounded claim. The evidence therefore keeps
real-world identity, process independence, key-registration governance, nonce
uniqueness, replay registry, system-observed source review, source-baseline
authentication, independent completion, route registration, UI mount, current,
paper, and live authority false.

## Consumer-first order

1. Keep all key and signature material caller supplied and in memory.
2. Verify exact intake, registration, nonce, unsigned, signed, and public-key bindings.
3. Add nonce/replay durability as a separate persistent contract, not a boolean claim.
4. Add real-world reviewer and process governance through an external authority.
5. Require independent completion before any mount review can advance.
6. Keep route, UI, current, paper, and live activation separately authorized.

## Adversarial matrix

- local key registration is exact, redacted, and governance-unproven
- unsigned attestation binds request, intake, source hashes, and nonce
- valid signature verifies without trust promotion
- wrong public key, tampered claim, nonce substitution, and signature mutation fail
- registration-hash substitution and compatibility fields fail
- evidence embeds no raw identity, key, or signature
- resealed authentication promotion fails exact rebuild
- all source documents remain immutable

## Consequences

The source-baseline claim can now be cryptographically bound without being
misrepresented as authenticated or independently completed. Tests use only
ephemeral in-memory keys. No secrets, runtime assets, source files, databases,
caches, logs, historical data, backtests, services, browsers, schedulers, paper
trades, or live trades are accessed or authorized.
