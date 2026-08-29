# ADR 0218: Presentation consumer registration-v4 frontend-v5 pins

## Status

Accepted as a static, blocked registration successor. It does not execute artifacts, activate registration, register a route, access DOM/browser state, mount UI, or switch `current`.

## Context

Registration-v3 pins presentation HTTP candidate-v5 but intentionally reports the frontend projection consumer as unbound. Projection-v5, card-v5, scoped CSS, consumer-v5, and their Python/Node contracts were created later and have finalized implementation hashes.

A synthetic read-only audit established the registration gap with `6/6` assertions:

- registration-v3 manifest remains exact;
- registration-v3 closes HTTP contract versioning;
- registration-v3 keeps the frontend projection unbound;
- its blocker for projection-v5 remains present;
- its exact manifest contains no frontend-v5 artifacts;
- adding those artifacts to v3 fails closed.

## Decision

Add registration-v4 as a static exact-manifest successor.

Registration-v4 pins 12 artifacts:

1. registration-v3 predecessor;
2. projection-v5 implementation and test;
3. strict-canonical Python and JavaScript implementations;
4. card-v5 JavaScript, scoped stylesheet, and Node test;
5. consumer-v5 JavaScript and Node test;
6. Python-to-Node cross-runtime test;
7. ADR0217.

An exact manifest closes only `http_candidate_to_frontend_projection_v5_unversioned`. It records that the contracts and test definitions are versioned, but does not self-certify execution. A versioned consumer-v5 execution receipt, independently bound execution evidence, descriptor/load-order review, DOM review, browser review, route, registration activation, mount, and `current` remain separate blockers.

The production module performs no file reads or artifact execution and does not embed the supplied manifest. Its verifier accepts only an exact canonical rebuild and grants no authority.

## Consumer-first order

1. Bind external manifest attestation.
2. Version consumer-v5 execution receipt.
3. Independently bind consumer-v5 execution evidence.
4. Independently review descriptor and dependency load order.
5. Separately authorize isolated DOM review.
6. Separately authorize browser visual review.
7. Separately authorize route, registration activation, mount, and `current`.

## Consequences

- registration-v3 and all v5 frontend artifacts remain immutable.
- Static contract versioning is distinguished from execution, review, mount, and permission.
- The neutral `SOURCE -> GAP -> MATURITY -> PERMISSION` order is fixed.
- Local gate state remains descriptive and never implies readiness, profitability, or trading authority.

## Non-goals

- No artifact execution or execution receipt in this ADR.
- No DOM, browser, route, mount, or runtime access.
- No return backtest or profitability claim.
- No registration activation, `current` switch, pack publication, pointer reissue, paper, or live authority.
