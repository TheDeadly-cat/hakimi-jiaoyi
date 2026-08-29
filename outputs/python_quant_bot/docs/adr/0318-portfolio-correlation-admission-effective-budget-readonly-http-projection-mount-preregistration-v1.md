# ADR 0318: Portfolio Correlation Admission Effective-Budget Read-Only HTTP Projection Mount Preregistration v1

- Status: Accepted as a blocked preregistration
- Date: 2026-08-24
- Scope: Descriptive transport and security policy only

## Context

ADR0317 freezes a side-effect-free three-state projection candidate, but it has
no method, route, endpoint, handler, authentication, rate limit, or trusted
internal-context provider.  Registering it directly in `server.py` would merge
projection semantics with unresolved transport and security policy.

The project already has loopback and origin checks in `http_contract.py`, but
their presence alone does not register authentication, CSRF protection, rate
limits, body limits, log redaction, or a trusted provider context.  These remain
separate required controls.

## Decision

Preregister, but do not mount, the following candidate transport:

- method: `POST`
- route: `/api/v1/research/portfolio-correlation/admission-effective-budget`
- handler: null
- endpoint: null
- registered: false
- externally callable: false

Pin the exact ADR0317 implementation, tests, ADR, three synthetic response
hashes, ADR0316 provider binding hash, `server.py`, and `http_contract.py` source
baselines.  The resulting mount preregistration hash is:

`d87dca5d784cd6575af89fd30a4ac6703fddab75d02174a91c15324949233ad2`

## Proposed HTTP state mapping

| Condition | Proposed status |
| --- | --- |
| Verified KNOWN | 200 |
| Verified UNKNOWN | 200 |
| Verified BLOCKED | 200 |
| Invalid request contract | 400 |
| Authentication failure | 401 |
| CSRF failure | 403 |
| Rate limit | 429 |
| Trusted context unavailable | 503 |
| Provider failure | 503 |

The application state remains in the response body.  A verified BLOCKED state
is not an HTTP authentication or server error and must not be promoted to READY.

## Required unregistered controls

The preregistration requires all of the following before a handler or route can
be considered:

- loopback-only and same-origin transport;
- authentication;
- CSRF protection for POST;
- rate limiting;
- maximum request body size;
- a trusted internal provider-context service that cannot be client supplied;
- request-log redaction with body logging forbidden;
- independent mount review;
- separately versioned handler implementation;
- separately authorized route registration.

All nine registration records remain false or null.  Runtime, database, cache,
network, source-document, and request-body logging capabilities remain false.

## Activation order

1. Verify ADR0317 and all source pins exactly.
2. Register loopback, same-origin, authentication, and CSRF controls.
3. Register rate limiting and request body size limits.
4. Register a trusted internal context provider.
5. Register request-log redaction.
6. Complete independent mount review.
7. Implement a handler in a separate version.
8. Register a route only by a separate explicit decision.
9. Run authorized browser review before any UI mount.
10. Consider current only through a separate explicit decision.

## Non-authority

ADR0318 does not import `server.py`, modify `http_contract.py`, implement a
handler, register a route, start a service, or make the candidate externally
callable.  It grants no browser, mount, current, writer, paper, live, or trading
authority.  Synthetic response hashes are contract evidence only and do not
prove strategy performance or profitability.  The natural-forward single-look
chain, legacy pack-v5 UNKNOWN behavior, and pointer-v2 remain unchanged.
