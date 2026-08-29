# ADR 0319: Portfolio Correlation Admission Effective-Budget Trusted Internal Context Provider Preregistration v1

- Status: Accepted as a blocked preregistration
- Date: 2026-08-24
- Scope: Request-local context ownership and lifecycle policy only

## Context

ADR0317 accepts an exact external request shell and a separate internal provider
context.  ADR0318 correctly forbids the client from supplying that context, but
the trusted context provider itself is not implemented or registered.  Without
an exact context shape and ownership contract, a future handler could construct
the 13 positional and 10 keyword arguments from client data, stale state, cache,
or a previous request.

Wall-clock freshness is unnecessary and weaker than request-local ownership for
this boundary.  The context should exist only for one synchronous authenticated
request scope, resolve once, and then be discarded.

## Decision

Preregister a trusted internal context provider with:

- 13 exact ordered positional roles;
- 10 exact ordered keyword roles;
- source ownership restricted to the ADR0311 internal exact source chain;
- client input restricted to the ADR0317 schema version and projection ID;
- no client context, hash, freshness, or source-document override;
- same synchronous request-scope freshness with no clock or timestamp;
- maximum resolution count of one;
- no persistence, database, cache, filesystem, or network use;
- mandatory discard after projection;
- no context, source document, position, symbol, or request-body logging.

The fixed hashes are:

- positional role hash:
  `1c1652d5ff99d81b063678e20bc8b5e621c718df34c249028884a24349a9f8b2`
- keyword role hash:
  `24672b9e3d2501291d683ac83803c112846578e8a230a18409346acb3ab05edb`
- context shape hash:
  `c7d53837786e478a6b2341463594ac0c6a8d348d1a1eb3458a0e8eed11772d43`
- context provider preregistration hash:
  `14e08fb0d46ea1738e77c416ebc49506430778ce025c45d500130c722ea31cff`

## Unregistered controls

Seven controls remain absent:

- context provider implementation;
- authenticated request-scope provider;
- trusted source-chain resolver;
- context generation-ID provider;
- single-use guard;
- context redaction policy;
- independent context review.

Handler and route bindings remain null.  ADR0318 authentication, CSRF, rate-limit,
body-limit, and request-log controls also remain incomplete.

## Activation order

1. Verify ADR0318 and its source pins exactly.
2. Register an authenticated request-scope provider.
3. Register a trusted source-chain resolver.
4. Implement the context provider in a separate version.
5. Register generation ID and single-use guard.
6. Register context redaction.
7. Complete independent context review.
8. Bind to a handler only by separate explicit decision.
9. Keep the route unregistered until every ADR0318 control passes.
10. Consider current only through a separate explicit decision.

## Non-authority

ADR0319 is descriptive.  It does not build a context, resolve source documents,
mutate request state, implement a handler, register a route, start a service, or
make an external call.  It grants no current, writer, paper, live, or trading
authority.  It does not run a backtest and supplies no profitability evidence.
The natural-forward single-look chain, legacy pack-v5 UNKNOWN behavior, and
pointer-v2 remain unchanged.
