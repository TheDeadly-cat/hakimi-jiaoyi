# ADR 0202: Render descriptor signed review attestation v1

## Status

Accepted as a local cryptographic claim-binding contract. It does not establish
real-world reviewer identity, registration governance, replay durability, or
independent review completion.

## Context

ADR0201 creates a deterministic review request and binds an unauthenticated
all-true rubric claim while correctly leaving signature and external trust
unproven. The repository already uses Ed25519 detached signatures over strict
canonical SHA-256 digests. A separate signature format would duplicate a
security boundary and increase compatibility risk.

## Decision

Add
`strategy_correlation_cluster_portfolio_risk_render_descriptor_signed_review_attestation_v1.py`
with four consumer-first stages:

- a redacted reviewer-key registration containing only reviewer/process hashes,
  a key identifier, and the Ed25519 public-key hash;
- an unsigned payload binding the exact ADR0201 request and intake hashes,
  descriptor and v9 hashes, strict claim hash, reviewer/process hashes, nonce
  hash, registration hash, ADR0201 implementation hash, and signature domain;
- detached signature assembly that never accepts or imports a private key;
- evidence evaluation requiring exact registration and signed-attestation hash
  pins, exact ADR0201 public verification, and Ed25519 signature verification.

The successful evidence state is only
`SIGNED_REVIEW_CLAIM_VERIFIED_EXTERNAL_INDEPENDENCE_UNPROVEN`. It proves local
possession of the pinned private-key counterpart over the exact payload. It does
not prove who controls that key, whether registration governance is trustworthy,
whether the nonce is unique, whether a replay registry durably recorded it,
whether descriptor content was actually observed, or whether the reviewer is
independent.

## Activation order

1. Freeze the registration and signed-attestation hashes outside this builder.
2. Obtain the detached signature from an external process without sharing its
   private key.
3. Verify the local cryptographic evidence through an unmounted consumer.
4. Add separately governed identity and durable replay evidence in a later
   version.
5. Consider presentation registration only after a separately authorized review
   decision. Do not automatically write current or reissue pointers.

## Consequences

The previous signature-absent gap now has a deterministic local cryptographic
verification path, but the v9 independent-review blocker remains open. HTTP
registration, UI mount, browser execution, runtime mutation, profitability,
paper authority, and live authority remain unavailable.
