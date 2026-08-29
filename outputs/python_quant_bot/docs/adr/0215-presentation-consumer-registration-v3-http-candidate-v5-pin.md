# ADR 0215: Presentation consumer registration-v3 HTTP candidate-v5 pin

## Status

Accepted as a static, blocked registration successor. It does not activate registration, an HTTP route, a frontend consumer, a DOM mount, or `current`.

## Context

Presentation consumer registration-v2 pins the existing projection-v4, card-v4, and consumer-fixture-v4 chain. Its activation order requires a versioned presentation HTTP contract before mount, but its immutable facts still state `presentation_http_contract_versioned=false` and its exact manifest cannot include presentation HTTP candidate-v5.

A read-only synthetic audit established the version gap with `6/6` assertions:

- candidate-v5 is an unregistered candidate;
- registration-v2 reports the HTTP contract as unversioned;
- registration-v2 retains the matching blocker;
- the v2 manifest has no candidate-v5 pin;
- adding candidate-v5 to the exact v2 manifest fails closed;
- v2 correctly does not claim runtime or UI consumption.

Candidate-v5 closes only the local versioned-contract prerequisite. It does not provide the separate HTTP-to-frontend projection consumer, route, DOM review, browser review, or mount authority.

## Decision

Add registration-v3 as a static manifest successor.

Registration-v3 pins:

1. registration-v2 as the preserved predecessor;
2. presentation HTTP candidate-v5 implementation;
3. the candidate-v5 targeted contract test;
4. ADR0214;
5. the strict-canonical Python implementation.

The successor closes `presentation_http_contract_not_versioned` only when the supplied manifest is exact. It explicitly adds `http_candidate_to_frontend_projection_v5_unversioned` and keeps all execution, review, route, registration, mount, and current blockers visible.

The static build performs no file reads and embeds no supplied manifest. File-hash matching remains an external attestation responsibility. The verifier accepts only an exact canonical rebuild and never grants authority.

## Consumer-first order

1. Bind external implementation-manifest attestation.
2. Independently bind candidate-v5 execution evidence.
3. Version the HTTP candidate-v5 to frontend projection consumer.
4. Execute a static cross-runtime consumer fixture.
5. Review render descriptor and dependency order.
6. Separately authorize DOM and browser review.
7. Separately authorize registration, route, mount, and current switch.

## Consequences

- registration-v2 remains immutable.
- Existing projection-v4/card-v4/consumer-v4 remains the registered candidate chain.
- candidate-v5 is pinned as a prerequisite, not claimed as consumed.
- `presentation_http_contract_versioned=true` does not imply route availability, frontend binding, readiness, profitability, or permission.
- The neutral `SOURCE -> GAP -> MATURITY -> PERMISSION` order remains fixed.

## Non-goals

- No HTTP-to-frontend adapter implementation in this ADR.
- No file, runtime, cache, database, provider, browser, DOM, or scheduler access.
- No service or HTTP route start.
- No UI mount or stylesheet change.
- No return backtest or profitability claim.
- No registration activation, `current` switch, pointer reissue, paper, or live authority.
