# ADR 0241: Registry organization identity evidence intake preregistration-v1

## Status

Accepted as a blocked, source-free external evidence intake preregistration.

## Context

ADR0237 preregisters a registry identity claim, and ADR0238 proves local control
of its Ed25519 key. Neither proves which organization controls the key. The
repository already contains generic provider-identity contracts for witness and
key governance, auditor provenance and suite reproducibility, and artifact
transparency and availability. Registry identity should reuse those contracts
rather than duplicate their receipt, role, and trust boundaries.

No real organization evidence, endpoint, credential, certificate, payload, or
reference time is available or authorized in the current source-only task.
Therefore this slice can preregister intake requirements but cannot evaluate or
promote identity.

## Decision

Add an immutable interface reference-v1 for six evidence kinds:

1. organization registry authority attestation;
2. domain-control attestation;
3. existing witness conformance and key-governance evaluation;
4. existing auditor provenance and reproducibility evaluation;
5. existing artifact transparency and availability evaluation;
6. revocation-status receipt.

Each reference binds an exact schema, artifact hash, signer role, registry id,
registry public-key hash, issuance and expiry times, and lowercase Ed25519
algorithm name. It never embeds evidence payload or signature material.

Add an application intake preregistration that exactly rebuilds ADR0237 identity
preregistration, pins the three existing provider-identity implementations,
requires six distinct signer roles and signing keys, forbids self-attestation,
and assigns bounded freshness windows. Every requirement begins `UNOBSERVED`.

An exact verifier may return PASS only for exact reconstruction of the still
BLOCKED intake. Evidence count remains zero, external sources remain uninvoked,
reference time remains unbound, and organization identity remains false.

## Adversarial matrix

- all six exact kinds and distinct roles are required;
- kind/schema, kind/role, hash, algorithm, and timestamp aliases fail closed;
- missing, substituted, or duplicated roles cannot satisfy the preregistration;
- identity substitution, resealed role drift, and predecessor authority
  promotion fail closed;
- structural Protocol matching proves only Python shape compatibility;
- no local key-possession result can self-promote organization identity.

## Consumer-first order

1. exact ADR0237 identity preregistration and ADR0238 local key possession;
2. organization identity intake preregistration-v1;
3. separately authorized retrieval of six hash-addressed references;
4. trusted reference time and freshness evaluation;
5. independent signature, role separation, revocation, and transparency checks;
6. external adapter conformance and signed consumption receipt-v1;
7. post-registration receipt-v5 and explicit browser review;
8. separate route, mount, current, and activation decision.

## Consequences

- Registry organization identity now has an explicit consumer-first evidence
  contract without a duplicate provider-identity framework.
- No infrastructure adapter or network source is introduced.
- Existing identity preregistration, key-possession, registration-v8, UI source,
  current artifacts, pointer-v2, and natural-forward evidence remain unchanged.
- No endpoint, filesystem state, runtime asset, database, cache, log, network,
  service, browser, scheduler, market task, credential, or trading path is used.
- Intake preregistration is not organization identity, source trust, freshness,
  conformance, linearizability, atomicity, trusted time, profitability, receipt,
  current, runtime, paper/live, route, mount, migration, or writer authority.
