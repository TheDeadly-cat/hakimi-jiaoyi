# ADR 0222: Preregistered Ed25519 witness signature candidate-v1

## Status

Accepted as a synthetic cryptographic-possession candidate only.

## Context

Registration-v5 pins the receipt-v3 and evidence-v3 chain but correctly keeps
three facts false: independent Node process witnessing, process identity
authentication, and receipt signature verification.

Silently converting a self-reported receipt into identity evidence would be a
false promotion. A useful next boundary must support independent
cryptographic verification while distinguishing key possession from external
identity and from execution-process witnessing.

## Decision

Introduce a read-free Node contract with three versioned documents:

1. A preregistration policy containing a witness identifier and the SHA-256 of
   an Ed25519 SPKI public key.
2. A strict-canonical challenge binding the hashes of receipt-v3,
   evidence-v3, registration-v5, and the policy.
3. A detached attestation verification document for a signature over the
   complete strict-canonical challenge.

The production module accepts public key material only for verification. It
does not accept a private key, expose a signing function, generate a key pair,
read a key file, or persist key material.

The policy stores only the SPKI hash. The challenge stores only document
hashes. The verification output stores neither the public key nor signature.

The signature verifier also receives the receipt, evidence, and registration
documents. It extracts the challenge nonce, rebuilds the complete challenge
from those sources, and requires strict-canonical equality before checking the
signature. A self-sealed PASS challenge is not trusted by itself.

## Claim calibration

A verification PASS proves:

1. The challenge is a sealed PASS bundle.
2. The attestation binds the exact policy and challenge hashes.
3. The supplied public key is Ed25519.
4. Its SPKI hash matches the preregistered policy.
5. Its detached signature verifies over the canonical challenge.
6. The signer possessed the corresponding private key for this signature.

A verification PASS does not prove:

1. The policy was registered by an external authority.
2. The witness identifier maps to a real organization or person.
3. The signer independently observed the execution process.
4. The signature was created at a trusted time.
5. A shared anti-replay registry checked the nonce.
6. Any route, mount, paper trade, live trade, writer, or current admission is
   authorized.

The candidate therefore uses the decision
PREREGISTERED_ED25519_KEY_POSSESSION_VERIFIED_EXTERNAL_IDENTITY_UNVERIFIED.

## Adversarial matrix

1. Valid Ed25519 public input builds a sealed policy without embedding it.
2. Invalid and non-Ed25519 keys block policy construction.
3. Valid receipt, evidence, registration, and policy build a hash-only
   challenge.
4. Receipt schema aliasing blocks the challenge.
5. Receipt-evidence hash substitution blocks the challenge.
6. A registration without the evidence-v3 pin blocks the challenge.
7. A valid detached signature verifies key possession only.
8. A substituted valid public key fails the preregistered hash.
9. A modified signature fails.
10. A substituted policy fails.
11. A resealed challenge change invalidates the old signature.
12. A forged PASS challenge over an invalid source bundle fails exact rebuild
    even when signed by the preregistered key.
13. A resealed verification authority promotion fails exact rebuild.
14. No private-key, filesystem, network, DOM, or signing path exists in the
    production verifier.

Node unit contracts use generated ephemeral Ed25519 keys in memory. The
Python-to-Node contract uses the actual synthetic receipt-v3, evidence-v3, and
registration-v5 documents. No external key, secret, runtime store, database,
cache, log, service, browser, scheduler, market task, or trading path is used.

## Activation order

1. registration-v5 blocked static candidate.
2. witness policy candidate.
3. hash-only document bundle challenge.
4. detached signature possession verification.
5. future externally governed policy registry and witness identity binding.
6. future independent process-witness protocol and anti-replay registry.
7. future descriptor and dependency load-order review.
8. separate explicit production route or mount decision.

This ADR authorizes only steps 2 through 4 in synthetic contract scope.
