# ADR 0099: Factor calibration provider identity adapter registration v1

## Status

Accepted as an inactive, research-only preregistration contract. It does not
establish provider identity and is not an admission or activation artifact.

## Context

The long-horizon anchor adapter registration pins a provider id and the hash of
the public key expected to sign future provider receipts. The signature
verifier subsequently proves receipt integrity and possession of the matching
private key. It deliberately keeps `provider_identity_verified=false` because
key possession does not prove that an external legal or registry identity owns
that key.

Reusing the provider receipt key as its own identity authority would be
circular. Accepting an unversioned identity lookup after observations would
also permit hindsight changes to the registry, subject, document, or trust
root.

## Decision

Introduce
`strategy-correlation-cross-lag-factor-calibration-long-horizon-provider-identity-adapter-registration-candidate-v1`.

Before the evaluation date, the contract pins:

1. An identity adapter id, static fingerprint, and implementation hash.
2. An external identity registry id and immutable snapshot id/hash.
3. A provider subject id and provider identity document hash.
4. A registry attestation trust-root hash that must differ from the provider
   receipt-signing trust-root hash.
5. Exact `ED25519` and `RFC8785_JCS_UTF8` identity-attestation expectations.
6. The source anchor registration, observation protocol, preregistration, and
   future evaluation lineage.

The registration replays the full anchor-registration verifier with an exact
context key set. It accepts only a declaration at or after the anchor adapter
registration and strictly before the evaluation date.

Its highest state is
`IDENTITY_ADAPTER_DECLARED_ASSERTION_NOT_OBSERVED`. The contract has no field or
branch that can mark an external identity assertion observed, its signature
verified, or provider identity verified.

## Failure semantics

Invalid or mismatched source hashes, unsupported source schema/state, context
key drift, source resealing, unrelated source/context combinations, malformed
identifiers or hashes, trust-root role collision, algorithm/encoding drift, and
chronology violations produce a sealed `UNKNOWN` registration.

The public artifact contains hashes and identifiers only. It does not include
public-key bytes, private keys, signatures, identity assertions, receipts,
observations, results, or permission flags supplied by a caller.

## Consumer-first activation order

1. Land and adversarially validate this inactive registration contract.
2. Define an identity assertion receipt schema bound to this registration hash.
3. Define a verifier for registry snapshot membership and registry-root
   signature without embedding a local trust decision.
4. Define an externally attested registration-time receipt.
5. Feed only independently verified identity evidence into a successor
   calendar-bound admission gate.
6. Require a separate reviewed migration before any active consumer or current
   pointer change.

## Consequences

Provider receipt signing and provider identity become distinct cryptographic
roles with independent trust roots. Future identity evidence gains a frozen
consumer contract, while the current provider-identity blocker remains intact.
This decision creates no profitability evidence, paper/live authority,
observation admission, evaluation result, or trading permission.
