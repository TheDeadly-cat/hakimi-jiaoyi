# ADR 0227: Envelope-first HTTP candidate-v6

## Status

Accepted as an unregistered, unmounted, research-only candidate. No route, service, browser, runtime consumer, registry, current pointer, paper, or live authority is created.

## Context

ADR0226 introduced a neutral source-level adapter-v6 presentation envelope. HTTP candidate-v5 has a different boundary: it rebuilds a v4 request and separately verifies adapter-v5. Extending that request with adapter-v6 and downside-tail inputs would duplicate source verification and preserve an obsolete dual-source composition.

The candidate-v6 boundary should consume the exact envelope instead. Its public request must stay small, while the complete adapter-v6 and downside-tail source bundle remains in a non-embedded verification context.

## Decision

Add `strategy-correlation-cluster-portfolio-risk-presentation-http-candidate-response-v6` with:

- an exact request containing envelope-v1 plus its preregistered hash;
- an exact verification context containing adapter-v6, adapter-v5, downside-tail registration/evaluation, expected adapter-v6 hash, and both verification contexts;
- mandatory invocation of the envelope-v1 exact verifier and strict receipt-authority checks;
- a sealed, summary-only response with neutral `SOURCE -> GAP -> MATURITY -> PERMISSION` stages;
- `KNOWN_BLOCKED` for an exactly verified envelope, including an exact envelope whose joint source is UNKNOWN;
- `UNKNOWN` with no payload for malformed, mismatched, promoted, exception-producing, or unverifiable sources;
- permanently unregistered transport and closed authority.

The v1 envelope's historical `HTTP_CANDIDATE_V6_NOT_IMPLEMENTED` lifecycle gap is not copied into the v6 response. At this layer it becomes `HTTP_CANDIDATE_V6_UNREGISTERED`, preserving monotonic lifecycle semantics without changing the immutable v1 contract.

## Consumer-first activation order

1. Adapter-v6 presentation envelope v1, completed by ADR0226.
2. Envelope-first unmounted HTTP candidate-v6, completed by this ADR.
3. Future frontend projection-v6 and Node consumer.
4. Future local execution evidence and registration pins.
5. Separately authorized admission review with no automatic route, current, or pointer change.

## Adversarial matrix

The candidate covers observed local clear, downside-tail block, exact UNKNOWN source, request and context shape errors, expected-hash mismatch, resealed envelope authority promotion, verifier authority leakage and exceptions, non-embedding, input immutability, deterministic rebuild, transport locks, exact response verification, dependency pins, API boundaries, neutral axes, lifecycle-gap replacement, and no profitability claim.

## Consequences

The frontend pipeline now has an unmounted HTTP-shaped producer for a future consumer. No server or route imports it, no runtime data is read, no CSS or Node source is changed, and no output authorizes paper/live activity or demonstrates profitability. The existing natural-forward chain, legacy public reads, pointer-v2, and current admission remain unchanged.
