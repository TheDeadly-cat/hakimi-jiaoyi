# ADR 0201: Render descriptor independent review request and claim intake v1

## Status

Accepted as a fail-closed request and unauthenticated claim-intake contract. It
does not complete or authenticate an independent review.

## Context

V9 has a versioned HTTP candidate and still correctly blocks on independent
render-descriptor review. The current process cannot certify its own
independence, authenticate an external reviewer, verify an attestation
signature, or prove replay durability. Treating a locally generated rubric as
independent evidence would be a false authority promotion.

## Decision

Add
`strategy_correlation_cluster_portfolio_risk_render_descriptor_review_intake_v1.py`
with two exact contracts:

- a review request that public-reverifies v9 and binds the descriptor, v8, v9,
  HTTP candidate response, and v9 implementation hashes to a fixed neutral
  rubric;
- a claim intake that accepts only an exact claim shape, cross-binds the request
  and descriptor hashes, requires all rubric claims to be strict booleans, and
  hashes reviewer/process labels instead of embedding them.

Nested v8 evidence maps and the request review target must also be exact maps.
Malformed aliases fail closed to `UNKNOWN` instead of raising an exception.

Even a structurally valid all-true claim is reported only as
`CLAIM_BOUND_UNVERIFIED`. Reviewer identity, reviewer process, signature,
independence, descriptor-content observation by the system, and replay
durability remain false. The v9 independent-review blocker is not closed.

## Consequences

An external review system now has a deterministic challenge and fail-closed
intake boundary. A later version may authenticate a reviewer key, verify a
domain-separated signature, and enforce durable nonce/replay rules. Until then,
review completion, route registration, DOM/browser, activation, mount, current,
runtime, profitability, paper, and live authority remain unavailable.
