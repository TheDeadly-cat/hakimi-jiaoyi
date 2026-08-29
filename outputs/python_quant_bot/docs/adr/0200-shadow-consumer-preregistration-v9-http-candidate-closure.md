# ADR 0200: Shadow consumer preregistration v9 HTTP candidate closure

## Status

Accepted as a detached, evidence-aware preregistration. Public status remains
`BLOCKED`; HTTP transport, route, mount, current, paper, and live authority are
not granted.

## Context

V8 records five verified local closures and still reports the portfolio-risk
presentation HTTP contract as unversioned. ADR0199 defines an exact,
unregistered `interfaces/http` candidate that projects v8 as a neutral
`KNOWN_BLOCKED` payload without a route, method, runtime I/O, or cache I/O.

The candidate contract can now be consumed by a successor without confusing
schema versioning with actual transport registration.

## Decision

Add `strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v9.py`.
V9:

- public-reverifies immutable v8 and the exact ADR0199 candidate response;
- independently recomputes the ADR0199 strict-canonical response seal, so an
  erroneous upstream verifier success cannot admit a hash-tampered response;
- requires the ADR0199 request to contain the same v8 document and binds the
  response lineage hash back to that v8;
- layers two new implementation pins over v8's 39 pins, totaling 41;
- closes only `presentation_http_contract_v3_not_versioned` and records the
  ADR0199 response hash as closure evidence;
- replaces that blocker with
  `presentation_http_transport_unregistered_and_unexercised`;
- removes only the completed HTTP contract-versioning activation step;
- preserves 14 required inputs, five predecessor closures, independent review,
  DOM/browser, registration activation, mount, current, and trading gates;
- embeds no request, verification context, v8, or HTTP payload instance.

Even with `contract_state=KNOWN`, public status remains `BLOCKED`. HTTP route
and transport facts remain false, and authority explicitly denies route
registration.

## Consequences

The portfolio-risk HTTP schema is now evidence-bound into the preregistration
lineage. Actual transport review, route registration, independent descriptor
review, DOM/browser review, registration activation, mount, current, runtime,
profitability, paper, and live authority remain separate fail-closed work.
