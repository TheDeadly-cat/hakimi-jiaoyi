# ADR 0228: Candidate-v6 frontend projection-v6

## Status

Accepted as an unmounted, research-only frontend projection candidate. No Node consumer, DOM mount, route, registry, current pointer, paper, or live authority is created.

## Context

ADR0227 introduced an envelope-first HTTP candidate-v6. Existing projection-v5 is pinned to the candidate-v5 response and its dual-source payload. Teaching projection-v5 to accept candidate-v6 would create schema ambiguity and let an older consumer silently interpret new downside-tail semantics.

The next consumer-first layer must therefore use a new projection schema and exact candidate-v6 verifier. It must preserve the distinction between an exact candidate containing an UNKNOWN joint source and an unverified candidate.

## Decision

Add `strategy-correlation-cluster-portfolio-risk-projection-v6`.

Projection-v6:

- accepts only an exact `KNOWN_BLOCKED` candidate-v6 response and an exact two-key verification context;
- invokes the candidate-v6 public verifier before projecting any source value;
- preserves observed local clear, observed downside-tail block, and exact UNKNOWN joint source states;
- maps any malformed, mismatched, promoted, exception-producing, or unverifiable candidate to a sealed, non-reflective `UNKNOWN_SOURCE` projection;
- keeps top-level status blocked and preserves `SOURCE -> GAP -> MATURITY -> PERMISSION` with candidate-only maturity and unauthorized permission;
- exposes summary hashes, local decision, fixed blockers, and calibrated facts without embedding request documents, verification contexts, source documents, positions, observations, returns, or pair results;
- seals both projection and verification receipt with strict canonical JSON hashes;
- does not copy the historical `HTTP_CANDIDATE_V6_NOT_IMPLEMENTED` lifecycle phrase.

## Consumer-first activation order

1. Adapter-v6 presentation envelope v1, ADR0226.
2. Envelope-first HTTP candidate-v6, ADR0227.
3. Python frontend projection-v6, this ADR.
4. Future Node consumer and cross-runtime conformance evidence.
5. Future local execution evidence and registration pins.
6. Separately authorized admission review with no automatic route, current, or pointer change.

## Adversarial matrix

The contract covers observed local clear, downside-tail block, exact UNKNOWN joint source, context shape errors, candidate request-hash mismatch, resealed candidate authority promotion, verifier false/exception, non-reflection, summary-only redaction, deterministic rebuild, exact verifier tamper rejection, dependency pins, API boundaries, neutral axes, lifecycle wording, and closed authority.

## Consequences

Python now produces a versioned frontend summary that a future Node consumer can reject or render explicitly. No browser or service was started, no UI or CSS file changed, and no output proves profitability or authorizes paper/live activity. Existing natural-forward artifacts, legacy public reads, pointer-v2, and current admission remain unchanged.
