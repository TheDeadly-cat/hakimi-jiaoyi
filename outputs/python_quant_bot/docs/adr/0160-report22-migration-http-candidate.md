# ADR 0160: report22 migration HTTP candidate

- Status: Accepted
- Date: 2026-08-22
- Scope: Unregistered, in-memory HTTP interface candidate

## Context

ADR 0158 produced a verifier-backed report22 migration public-summary-v1 and ADR
0159 added an unmounted frontend consumer. A network boundary is still absent.
Passing the internal migration assessment through a public request or mounting a
route before trusted context, authentication and request controls exist would
expose private hashes and confuse a descriptive projection with admission.

The public summary is already the presentation contract. Adding another envelope
would duplicate its SOURCE/GAP/MATURITY/PERMISSION interpretation and create a
compatibility-drift boundary.

## Decision

Add an interface-only HTTP candidate that accepts a schema-only request. The
migration assessment and exact LIST/DRY_RUN verification bindings are keyword-only
trusted-context inputs to the pure in-memory function; they are never accepted in
the request body and never embedded in the response.

The candidate independently builds and verifies public-summary-v1, checks its
exact shape, state combination, permission locks and redaction flags, and returns
that summary as the only payload. NOT_SUPPLIED, UNKNOWN, PLAN_LISTED and
DRY_RUN_VERIFIED remain distinct. report22 PASS/BLOCK is preserved, while
migration execution and current remain false.

Every response is marked `UNREGISTERED_CANDIDATE`. Transport method and route are
null, external callability is false, runtime/cache access is false and request
body logging is false. The response does not contain the assessment, report22
extension, verification context, source hashes or identity bindings.

## Consumer-first activation order

1. Verify the internal migration assessment.
2. Build and verify public-summary-v1.
3. Wrap only that public summary in the unregistered HTTP candidate.
4. Preregister a future mount against exact source hashes and transport controls.
5. Do not edit server.py or http_contract.py until the mount review is complete.
6. Require explicit authorization before starting a service or browser.

## Adversarial contract matrix

Synthetic tests cover schema-only requests, mode-specific trusted contexts,
NOT_SUPPLIED, valid LIST, dry-run PASS/BLOCK, invalid assessment to verified
UNKNOWN, forged projection authority, private-hash non-echo, deterministic rebuild,
transport resealing and non-operational public APIs.

## Consequences

The project now has a narrow HTTP response candidate compatible with the frontend
lockboard, but no endpoint exists. This does not mount a route, access runtime
assets, execute migration, change current or the natural-forward single-look
chain, or grant paper/live and profitability authority.
