# ADR 0242: Synthetic organization-identity bundle freshness evaluation-v1

## Status

Accepted as a blocked synthetic reference-structure and freshness evaluation.

## Context

ADR0241 preregisters six external evidence references and requires distinct
signer roles and keys. Its first reference shape included signer role but omitted
the signer public-key hash, so key separation could not be evaluated. The intake
also had no executable consumer for subject binding, artifact uniqueness, or
freshness at an explicit reference time.

No evidence payload, detached signature, trusted clock, external source, or
source public-key trust anchor is available or authorized in the current task.
The next slice can evaluate metadata references but must not claim signature
verification, source trust, revocation content, or organization identity.

## Decision

Evolve evidence reference-v1 with a required signer SPKI SHA-256. Expose the
intake requirement manifest through one public function so freshness policy has
a single implementation source.

Add a pure application evaluator that consumes:

- exact ADR0241 intake and ADR0237 identity preregistration;
- exactly one immutable reference for each of six evidence kinds;
- an explicit non-negative reference time.

The evaluator checks exact kind coverage, subject registry-id and public-key
binding, distinct signer roles, distinct signer public keys, distinct artifact
hashes, issuance not in the future, unexpired references, maximum age, and
maximum validity interval. It emits only hash and metadata summaries.

When all local checks pass, the sealed document remains `BLOCKED` with local
status `STRUCTURE_BINDING_AND_FRESHNESS_PASS`. The public exact verifier may
return PASS only for that exact local state. An exactly reproduced stale or
misbound bundle remains `BLOCK/BLOCKED`; a tampered evaluation becomes
`BLOCK/UNKNOWN`.

## Adversarial matrix

- missing or duplicate kinds are rejected before evaluation;
- duplicate signer keys, duplicate artifact hashes, and subject substitution
  block local evaluation;
- stale, future-issued, over-age, expired, and overlong-validity references
  block freshness;
- exact local failure cannot become verifier PASS;
- resealed signature/source-trust promotion becomes UNKNOWN;
- raw payload, signature material, private key, and operator claim remain absent.

## Consumer-first order

1. exact ADR0241 intake and six immutable metadata references;
2. synthetic structure, binding, role/key separation, and freshness evaluation;
3. separately authorized payload retrieval and trusted reference time;
4. signature verification against independently trusted role keys;
5. revocation-content, transparency-log, and source-trust verification;
6. registry organization identity decision;
7. external adapter conformance, signed receipt-v1, and receipt-v5;
8. explicit browser review and separate activation decision.

## Consequences

- Role separation is now executable at both role and signer-key levels.
- Freshness policy has one public manifest rather than duplicated constants.
- A local PASS remains metadata-contract evidence only.
- Existing key-possession, registration-v8, UI source, current artifacts,
  pointer-v2, and natural-forward evidence remain unchanged.
- No evidence payload, endpoint, filesystem state, runtime asset, database,
  cache, log, network, service, browser, scheduler, market task, credential, or
  trading path is used.
- The evaluator is not signature verification, source trust, revocation truth,
  organization identity, conformance, linearizability, atomicity, trusted time,
  profitability, receipt, current, runtime, paper/live, route, mount, migration,
  or writer authority.
