# ADR 0244: Registry organization identity bundle Python verification envelope v1

## Status

Accepted as a sealed, summary-only cross-runtime verification bridge.

## Context

ADR0242 provides a Python evaluator and public exact verifier for six
organization-identity evidence references. ADR0243 provides an unmounted Node
candidate for one signed artifact. A future six-artifact Node consumer must not
trust an arbitrary caller-created summary claiming that ADR0242 passed.

The required bridge is a sealed Python summary that independently executes the
identity, intake, and bundle exact verifiers and exposes only the hashes and
blocked local conclusion required by a future consumer.

## Decision

Add a Python verification envelope with twelve blocking checks:

1. identity preregistration v1 is exact;
2. organization-identity intake v1 is exact;
3. the ADR0242 evaluation seal is exact;
4. its schema, fingerprint, BLOCKED status, and local PASS are exact;
5. the ADR0242 public exact verifier passes;
6. the identity preregistration hash edge is exact;
7. the intake preregistration hash edge is exact;
8. one normalized reference for each of six kinds matches the evaluation;
9. the explicit reference time matches;
10. registry id, subject public-key hash, and trust domain remain bound;
11. payload, signature, source, revocation, and identity claims remain false;
12. all underlying authority remains locked.

The envelope embeds no source document, evidence reference, operator identity
claim, payload, public key, signature, or private key. It carries hashes,
schemas, fingerprints, the explicit reference time, and neutral verification
states only.

The public envelope verifier returns PASS only when the document exactly
rebuilds and its internal envelope status is PASS. An exactly rebuilt blocked
envelope remains verifier BLOCK. A tampered envelope is BLOCK/UNKNOWN.

Envelope PASS means only that the pinned Python contracts reproduced the
blocked ADR0242 local structure, binding, and freshness result. It does not
authenticate the Python process or verify any evidence signature, source,
signer role, revocation content, or organization identity.

## Consumer-first order

1. ADR0241 organization-identity intake preregistration;
2. ADR0242 six-reference structure, binding, and freshness evaluation;
3. ADR0243 single signed-artifact candidate;
4. ADR0244 sealed Python exact-verification envelope;
5. six-reference signed-artifact aggregation with exact per-kind receipts;
6. independently governed signer-role and external-source evidence;
7. per-schema evidence-body semantic validators;
8. organization-identity decision contract;
9. separately authorized adapter and runtime activation.

ADR0244 preregisters the ADR0243 verification schemas, its implementation hash,
and the target aggregation schema. It does not activate or execute them.

## Adversarial matrix

- an exact local ADR0242 PASS becomes a sealed summary while the underlying
  evaluation remains BLOCKED;
- an exact stale local bundle produces an exact envelope that public verification
  still blocks;
- resealed signature promotion and intake hash substitution block;
- missing or duplicate evidence kinds block without throwing;
- reference-time substitution blocks;
- resealed envelope authority promotion becomes BLOCK/UNKNOWN;
- the raw operator claim and all source documents and cryptographic materials
  remain absent;
- Node verifies the Python strict-canonical seal without trusting its semantics;
- all identity, admission, runtime, writer, paper, and live authority remains
  false.

## Consequences

- A future Node aggregator can require one pinned, sealed Python summary instead
  of trusting an unsealed verifier result.
- Existing identity, intake, evaluator, signed-artifact candidate, current,
  HTTP, UI, registration-v8, pointer-v2, and natural-forward artifacts remain
  unchanged.
- No credential, endpoint, runtime asset, database, cache, log, service,
  browser, scheduler, market task, backtest, blind test, paper order, or live
  order is used.
- Passing checks are engineering evidence only. They do not prove source
  legitimacy, organization identity, strategy quality, profitability, or
  trading authority.
