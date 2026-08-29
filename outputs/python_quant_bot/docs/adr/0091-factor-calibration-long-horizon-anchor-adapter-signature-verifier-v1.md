# ADR 0091: Long-horizon detached Ed25519 signature verifier v1

## Status

Accepted as an unmounted, research-only cryptographic verifier. It proves only signature validity for a public key whose raw-key SHA-256 matches the local registration trust-root value.

## Context

Adapter registration v1 binds concrete adapter/provider/trust-root values but does not verify key possession, implementation, external registration timing, provider identity, observation-batch content, or replay uniqueness. The environment contains `cryptography`, but the project did not declare it as a dependency.

## Decision

Declare `cryptography>=49.0` and add a detached Ed25519 verifier. The signed message is the raw 32-byte SHA-256 digest of the strict-canonical signed receipt payload (`STRICT_CANONICAL_SHA256_DIGEST_V1`). The verifier requires exact registration, adapter, provider, trust-root, evaluation, batch-hash, date, timestamp, receipt-ID, algorithm, and source-anchor bindings. It rejects malformed base64, key substitution, message or signature tampering, hash mismatch, algorithm downgrade, dependency absence, and invalid chronology.

The highest positive state is `SIGNATURE_VERIFIED_REPLAY_REGISTRY_UNCHECKED`. It means the supplied key matches the locally pinned trust-root hash and the Ed25519 signature is valid. It does not prove that the provider identity is externally trusted, that registration predated observations, that the observation batch matches its hash, or that the receipt is unique.

## Activation order

The next consumers must independently establish provider/trust-root provenance, externally attest registration timing, verify replay uniqueness, and validate observation-batch content before any external-attestation or observation-admission state can exist.

## Consequences

Cryptographic tampering and key substitution now have deterministic fail-closed behavior without storing private keys or contacting a provider. No current pointer, evaluation result, profitability claim, paper permission, or live permission changes.
