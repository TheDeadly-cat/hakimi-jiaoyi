# ADR 0273: Membership HTTP mount source-baseline review intake-v1

## Status

Accepted as an unauthenticated review-request and claim-intake boundary. It does
not authenticate source content, reviewer identity, process independence,
signatures, replay durability, route registration, or mount authority.

## Context

Mount preregistration-v1 pins the expected `server.py` and `http_contract.py`
hashes, but pinning is not authentication. A synthetic audit confirmed that the
policy has no observed hashes, review document, review receipt, independent
reviewer proof, or authenticated-source fact.

No source-baseline-specific review service existed. The project does have an
established two-stage pattern for external review: first bind an unauthenticated
claim, then separately verify signed attestation evidence without claiming
real-world identity or process independence. This ADR adopts only the first
stage. Producing an `authenticated=true` document directly would be
self-certification and is rejected.

## Decision

Add two exact deterministic contracts in one service:

- a review request built only from an exactly verified mount preregistration
- a claim intake binding the exact request, claimed observed hashes, reviewer/process identifiers, independence claim, and six rubric results

The rubric claims that server and HTTP-contract hashes match their pins, the
proposed route and route-contract symbols remain absent from activation source,
and no handler or UI binding was observed. Every rubric result must be a strict
boolean true and the observed hash object must exactly equal the review target.

The intake hashes reviewer identifiers and the full claim, but embeds neither
raw identifiers, raw source content, the raw claim, nor the review request. A
valid claim becomes `CLAIM_BOUND_UNAUTHENTICATED`, never reviewed, authenticated,
registered, mounted, READY, paper-authorized, or live-authorized.

The fixed blockers preserve missing identity authentication, process
independence, signature, nonce uniqueness, replay durability, system-observed
source review, independent-review completion, and route registration.

## Consumer-first order

1. Keep request/intake functions pure and import-only.
2. Obtain a review claim through a separately controlled process.
3. Define signed attestation and pinned reviewer-key contracts separately.
4. Preserve real-world identity, independence, nonce, and replay gaps after signature verification.
5. Require an independent completion decision before any mount review can advance.
6. Keep route, UI, current, paper, and live activation separately authorized.

## Adversarial matrix

- exact request remains awaiting external review
- malformed or unverifiable preregistration produces UNKNOWN
- request embeds no source content and locks authority
- exact claim binds while authentication remains false
- observed-hash mismatch fails closed
- any false rubric result fails closed
- extra claim fields and request-hash substitution fail closed
- raw reviewer identifiers are never embedded
- resealed authentication promotion fails exact rebuild
- request, claim, and preregistration inputs remain immutable

## Consequences

Pinned source hashes can now be reviewed through a versioned intake without
being mislabeled as authenticated evidence. No source files, runtime assets,
historical data, caches, logs, secrets, services, browsers, schedulers, paper
trades, or live trades are accessed or authorized.
