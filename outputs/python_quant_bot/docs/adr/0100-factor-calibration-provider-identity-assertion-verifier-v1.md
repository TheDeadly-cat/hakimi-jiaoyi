# ADR 0100: Factor calibration provider identity assertion verifier v1

## Status

Accepted as an inactive, research-only cryptographic verification candidate. A
positive cryptographic result is not external provider-identity truth.

## Context

ADR0099 preregisters an identity adapter, immutable registry snapshot, provider
subject and identity-document hash, and a registry trust-root hash that is
separate from the provider receipt-signing root. It intentionally does not
define an observed identity assertion or prove that the locally pinned registry
root is externally authoritative.

The next consumer must distinguish four claims: receipt integrity, registry-key
possession, membership of the provider document in the frozen snapshot, and
external authority of that registry. Only the first three are locally
verifiable with synthetic fixtures.

## Decision

Introduce a strict assertion receipt and
`strategy-correlation-cross-lag-factor-calibration-long-horizon-provider-identity-assertion-verification-candidate-v1`.

The receipt:

1. Cross-binds the ADR0099 registration hash, provider, subject, adapter,
   registry, snapshot, both trust-root roles, document hash, and future
   evaluation id.
2. Uses `ED25519` over a strict-canonical SHA-256 content digest.
3. Uses `SHA256_DOMAIN_SEPARATED_POWER_OF_TWO_V1`: leaf hashes are
   `SHA256(0x00 || document_hash)` and parent hashes are
   `SHA256(0x01 || left || right)`.
4. Requires a bounded power-of-two tree, index-consistent proof directions, and
   exact proof length.
5. Requires assertion issuance after identity-adapter registration and before
   evaluation, with validity covering the evaluation boundary.

The verifier replays the complete provider-identity registration context,
checks the receipt seal and source bindings, verifies the registry public-key
hash, Ed25519 signature, and Merkle root, and publishes only proof counts and
hashes. Public-key bytes, signature bytes, and proof siblings are redacted.

Its highest state is
`IDENTITY_ASSERTION_SIGNATURE_AND_MEMBERSHIP_VERIFIED_EXTERNAL_TRUST_UNPROVEN`.
Even in that state, `provider_identity_verified`, external registry
authenticity, external registration time, replay checking, evaluation,
admission, paper, and live authority remain false.

## Failure semantics

Expected-hash drift, source/context mismatch, receipt key drift, seal or content
hash failure, source-binding changes, time-window violations, malformed Merkle
shape/direction/hash, key substitution, signature corruption, unavailable
cryptography, or snapshot-root mismatch return a sealed `UNKNOWN` result.

No compatibility alias, caller boolean, latest-snapshot lookup, implicit tree
padding, or local trust-root promotion is accepted.

## Consumer-first activation order

1. Land and adversarially validate this detached verifier.
2. Define an external trust-root attestation whose authority is independent of
   both provider and local application keys.
3. Define append-only assertion replay registration and receipt verification.
4. Define independent external-time evidence for registration and assertion.
5. Only a successor gate may combine those verified artifacts, and it still
   requires separate evaluation-activation and observation-admission receipts.
6. Require reviewed migration before any active consumer or current-pointer
   change.

## Consequences

The project can prove a frozen cryptographic assertion and snapshot membership
without conflating them with external identity truth. This creates no strategy
result, profitability evidence, observation admission, paper/live authority,
or trading permission.
