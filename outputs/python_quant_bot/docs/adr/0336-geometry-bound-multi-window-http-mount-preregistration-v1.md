# ADR 0336: Geometry-bound multi-window HTTP mount preregistration v1

- Status: accepted as a blocked preregistration
- Date: 2026-08-24
- Scope: descriptive transport and security policy only

## Context

ADR0335 closes the geometry-bound multi-window HTTP candidate, but no source
file imports it as a server or http-contract consumer. The candidate has no
route, handler, endpoint, trusted internal source provider, authentication,
CSRF policy, rate limit, body limit, log-redaction policy, consumer review, or
independent mount review.

Registering ADR0335 directly would merge its projection semantics with all of
those unresolved transport and source-authority decisions. A consumer-first
sequence therefore requires a deterministic blocked preregistration first.

## Decision

Add the still-unmounted preregistration:

`exchange_terminal.services.strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_mount_preregistration_v1`

The preregistration pins ADR0335's implementation and contract, strict
canonical sealing, server.py, and http_contract.py. It proposes, but does not
register:

- method: POST
- route: /api/research/strategy-correlation-clusters/geometry-budget-multi-window-presentation-v9
- handler: null
- endpoint: null
- registered: false
- externally callable: false

## Required unregistered controls

- loopback-only and same-origin transport;
- authentication and CSRF protection;
- rate limiting and a maximum request body size;
- a trusted internal candidate/context provider with client input denied;
- request-log redaction with body logging forbidden;
- a separately versioned handler implementation;
- consumer binding review and independent mount review;
- separately authorized route registration.

Runtime, database, cache, external-network, source-document, and verification-
context access remain forbidden by this policy-only version. All registration,
review, handler, mount, current, writer, paper, and live fields remain false or
null.

## Consumer-first activation order

1. Verify ADR0335, this preregistration, and every source pin exactly.
2. Register loopback, same-origin, authentication, and CSRF controls.
3. Register rate limiting, body limits, and request-log redaction.
4. Preregister and independently verify a trusted internal candidate/context
   provider that cannot accept client-supplied evidence.
5. Implement a separately versioned read-only handler.
6. Complete consumer binding and independent mount reviews.
7. Register a route only through a separate explicit authorization.
8. Run separately authorized browser review before any UI mount.
9. Consider current, paper, or live authority only through separate decisions.

## Adversarial acceptance matrix

- Exact deterministic document: BLOCKED and exactly verifiable.
- Recomputed-hash route, provider, authority, control, path, or source-pin
  promotion: rejected by exact rebuild.
- Proposed route or candidate import in server/http_contract: regression fail.
- Missing auth, CSRF, rate, body, provider, redaction, handler, or review:
  remains an explicit blocker, never implicit permission.

## Consequences

ADR0335 now has a consumer-first mount policy without a route or handler. This
ADR does not modify server.py, http_contract.py, CSS, current selectors, or UI;
does not access runtime assets; does not prove profitability; and grants no
paper or live trading authority.
