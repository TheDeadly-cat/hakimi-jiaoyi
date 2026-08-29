# ADR 0243: Registry organization identity signed artifact candidate v1

## Status

Accepted as a blocked, synthetic local cryptographic candidate.

## Context

ADR0242 validates six evidence references for exact kind coverage, subject
binding, signer and artifact separation, and freshness. It intentionally does
not observe evidence payloads or verify signatures. Treating its local bundle
status as organization identity would therefore leave an unaudited gap between
each artifact hash and the content allegedly signed by its declared key.

The existing Ed25519 candidates prove local key possession without promoting
that fact into organization identity. The same separation is required here.

## Decision

Add an unmounted Node candidate for one organization-identity evidence
artifact. It performs six local checks:

1. the Python evidence reference v1 shape is exact;
2. the signed payload shape is exact and bounded;
3. kind, schema, signer, subject, and validity times bind to the reference;
4. the strict-canonical payload hash matches artifact_sha256;
5. the Ed25519 public-key SPKI hash matches the reference;
6. the detached Ed25519 signature verifies over exact canonical payload bytes.

The signed payload contains an opaque evidence body. The verifier observes and
hashes that body but does not interpret its domain semantics. It rejects
private-key, credential, secret, and raw-signature field names recursively. The
verification document embeds only hashes and metadata; it never embeds the
body, public-key material, detached signature, or private-key material.

A valid local result has local_signed_artifact_status PASS while the sealed
verification document remains BLOCKED. Its public exact-rebuild verifier may
return PASS only for an exact locally valid document. This PASS means local
cryptographic binding only.

Signature verification does not establish signer-role identity, external
source trust, evidence semantics, revocation truth, six-reference aggregation,
or registry organization identity. Every admission, presentation, runtime,
writer, paper, and live authority remains false.

## Consumer-first order

1. ADR0241 organization-identity intake preregistration;
2. ADR0242 six-reference structure, binding, and freshness evaluation;
3. ADR0243 single-artifact canonical hash and Ed25519 candidate;
4. six-reference signed-artifact aggregation with exact per-kind receipts;
5. independently governed signer-role and source-trust evidence;
6. evidence-body semantic validators for each preregistered schema;
7. organization-identity decision contract;
8. separately authorized external adapter and runtime activation.

ADR0243 is not connected to current, HTTP, UI, registration-v8, pointer-v2, or
the natural-forward evidence chain.

## Adversarial matrix

- a Python-created canonical payload, artifact hash, public key, and detached
  signature verify in Node;
- resigned body substitution still fails the frozen artifact hash;
- subject substitution fails reference binding;
- public-key and signature substitution fail closed;
- schema aliases and unsafe body fields are rejected;
- an exact local signature failure remains BLOCK/BLOCKED;
- verification-document promotion tampering becomes BLOCK/UNKNOWN;
- output contains no payload body, public key, signature, or private key;
- all authority and organization-identity fields remain false.

## Consequences

- ADR0242 can later consume explicit per-artifact cryptographic receipts rather
  than inferring signatures from references.
- The candidate is synthetic and local. No network, endpoint, credential,
  filesystem runtime state, database, cache, log, service, browser, scheduler,
  market task, backtest, paper order, or live order is used.
- Passing checks are engineering evidence only. They do not prove source
  legitimacy, organizational control, strategy quality, profitability, or
  trading authority.
