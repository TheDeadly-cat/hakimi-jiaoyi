# ADR 0161: report22 migration HTTP mount preregistration

- Status: Accepted
- Date: 2026-08-22
- Scope: Blocked transport policy preregistration

## Context

ADR 0160 introduced an unregistered HTTP candidate whose request is schema-only
and whose response payload is the verified report22 migration public-summary-v1.
The candidate has no method, route or external callability. Moving directly into
`server.py` or `http_contract.py` would bypass source pinning and leave transport
security and trusted evidence sourcing undefined.

## Decision

Preregister a possible future `POST` endpoint at
`/api/v1/research/strategy-correlation/report22-date-grid-migration-evidence`.
The preregistration pins SHA-256 values for the candidate adapter, public
projection, current server baseline and current HTTP contract baseline.

The policy requires loopback-only and same-origin access, JSON content types,
no-store and defensive browser headers, a schema-only request, a public-summary-
only response, no runtime/cache access, no request-body logging and no
client-supplied assessment or verification context.

Authentication, rate limiting, request-size limits, a trusted migration evidence
provider, request-log redaction, consumer binding review, independent mount review
and route registration are all explicitly absent. Consequently status is fixed
to BLOCKED and every mount, migration, writer, current, paper and live authority
remains false.

## Consumer-first activation order

1. Keep the standalone public-summary consumer and HTTP candidate unchanged.
2. Recheck all four source pins before any later mount decision.
3. Register and independently review every missing transport control.
4. Establish a non-client-supplied trusted assessment/context provider without
   reading runtime assets through this route.
5. Review the frontend fetch binding independently.
6. Only then consider a separate change to server.py and http_contract.py.

## Consequences

The future transport has an exact review target and an explicit blocker set, but
no route was mounted. No service, browser, scheduler, migration, current,
single-look, pointer-v2, paper/live, profitability or authenticity transition is
included.
