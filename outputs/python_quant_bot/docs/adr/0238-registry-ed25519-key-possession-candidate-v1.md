# ADR 0238: Registry Ed25519 key-possession candidate-v1

## Status

Accepted as a blocked, synthetic local registry key-possession candidate.

## Context

ADR0237 preregisters a registry identity claim and Ed25519 public-key hash before
an external adapter exists. A hash alone does not prove that any process controls
the corresponding private key. The next consumer needs a detached challenge and
signature contract without upgrading local possession into organization
identity, external adapter conformance, or receipt authority.

## Decision

Add a Node candidate with four sealed contracts:

1. a blocked policy-v1 that independently validates the exact Python identity
   preregistration and binds its registry id, trust domain, operator-claim hash,
   public-key hash, namespace, protocol, and target receipt schema;
2. a blocked challenge-v1 that receives a 32-byte nonce but embeds only its
   SHA-256 commitment;
3. a detached attestation-v1 that embeds only public-key and signature hashes;
4. a blocked verification-v1 plus public exact-rebuild verifier.

The production module receives public-key material, a raw nonce, and a detached
signature. It never receives a private key. Node unit tests sign with ephemeral
in-memory keys outside the production module. Python cross-runtime tests keep the
private key in the Python test caller and pass only public DER and signature to
Node.

An exact valid document yields local key-possession `PASS` while its verification
document remains `BLOCKED`. The public exact verifier returns `PASS` only when
the document is exact and local possession passed. An exactly reproduced local
signature failure remains verifier `BLOCK`, with document status `BLOCKED`; a
tampered document becomes `BLOCK/UNKNOWN`.

## Adversarial matrix

- preregistered public-key hash and valid detached signature pass locally;
- substituted public key, substituted signature, and nonce mismatch block;
- preregistration schema aliases and resealed drift are rejected;
- exact local failure cannot become verifier PASS;
- verification tampering becomes UNKNOWN;
- raw nonce, detached signature, public-key material, and private key are not
  embedded in policy, challenge, attestation, or verification documents;
- all current, runtime, receipt, paper/live, mount, and writer authority remains
  false.

## Consumer-first order

1. registry identity preregistration, adapter port, and conformance plan-v1;
2. local registry Ed25519 key-possession candidate-v1;
3. independently governed registry organization-identity evidence;
4. separately authorized external adapter implementation;
5. independently observed execution of the preregistered conformance plan;
6. signed target consumption receipt-v1 with trusted registry time;
7. independent witness identity/process evidence and receipt-v5;
8. explicit browser review and separate activation decision.

## Consequences

- The preregistered registry key now has an executable local possession check.
- Local possession does not establish who controls the key or whether that party
  operates an independent, durable, linearizable registry.
- Existing interface, application preregistration, conformance plan, reference
  model, witness, current artifacts, pointer-v2, and natural-forward evidence
  remain unchanged.
- No endpoint, credential, filesystem state, runtime asset, database, cache, log,
  network, service, browser, scheduler, market task, or trading path is used.
- The candidate is not organization identity, external conformance,
  linearizability, atomicity, trusted time, profitability, receipt, current,
  runtime, paper/live, route, mount, migration, or writer authority.
