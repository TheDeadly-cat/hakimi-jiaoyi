# ADR 0226: Adapter-v6 neutral presentation envelope v1

## Status

Accepted as an unmounted, research-only candidate. It is not registered, current, runtime-bound, paper-authorized, or live-authorized.

## Context

ADR0225 added the exact adapter-v6 joint gate so an observed downside-tail BLOCK can override an adapter-v5 linear and multi-window PASS for the same identity set. The existing `portfolio-risk-projection-v5` consumes an HTTP candidate-v5 response. Reusing that version for a direct adapter-v6 source would collapse the HTTP and source-presentation boundaries and create compatibility drift.

The next consumer-first step therefore needs a source-level presentation contract that can be consumed by a future HTTP candidate and frontend projection without changing any existing route, Node consumer, registration, pointer, or current artifact.

## Decision

Add `strategy-correlation-cluster-portfolio-risk-adapter-v6-presentation-envelope-v1`.

The envelope:

- requires the caller to preregister the exact adapter-v6 hash;
- calls the adapter-v6 public exact verifier with the adapter-v5 and downside-tail source bundle;
- distinguishes an exact adapter-v6 document with unknown joint source from an unverified source;
- exposes only summary lineage, local decision state, tail state, fixed governance gaps, and neutral presentation axes;
- preserves `SOURCE -> GAP -> MATURITY -> PERMISSION` order;
- always keeps top-level presentation status blocked, maturity candidate-only, and permission unauthorized;
- embeds no source documents, verification contexts, positions, aligned observations, pair results, returns, or strata;
- exposes the lack of a risk-reduction joint exemption instead of implying one;
- seals both envelope and verification receipt with strict canonical JSON hashes.

## Consumer-first activation order

1. Source-level adapter-v6 presentation envelope and adversarial contract.
2. Future unmounted HTTP candidate-v6 that consumes the exact envelope.
3. Future frontend projection and Node consumer that reject all older or malformed payloads.
4. Future local execution evidence and registration pins.
5. Separately authorized admission review, with no automatic current or pointer change.

This ADR implements only step 1.

## Adversarial matrix

The contract covers exact local clear, exact tail block, exact unknown source, expected-hash mismatch, resealed source authority promotion, verification-context symbol splice, resealed envelope promotion, summary-only redaction, untrusted-input non-reflection, axis order, explicit no-exemption policy, dependency pins, API surface, authority locks, and deterministic rebuild.

## Consequences

The frontend now has a versioned neutral source contract available for later integration, but no route or UI consumes it. No CSS or load order changes are made. No result is profitability evidence or execution authorization. Existing natural-forward artifacts, legacy public reads, pointer-v2, and current admission remain unchanged.
