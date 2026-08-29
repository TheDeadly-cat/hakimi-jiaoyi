# ADR 0320: Portfolio Correlation Admission Effective-Budget Request-Scope and Source-Resolver Preregistration v1

- Status: Accepted as a blocked dual-contract preregistration
- Date: 2026-08-24
- Scope: Security evidence and source-resolution contracts only

## Context

ADR0319 defines a request-local context shape but intentionally leaves two
critical dependencies empty: authenticated request-scope evidence and a trusted
source-chain resolver.  Combining their implementation would obscure whether a
source context belongs to the same authenticated request and whether it was
already consumed.

ADR0320 therefore keeps them as separate hash-pinned subcontracts and adds a
third cross-binding contract.  No authentication receipt or source context is
produced by this ADR.

## Request-scope evidence contract

The future evidence contains only hashes and request-local identifiers:

- request-scope ID;
- authentication, CSRF, and origin receipt hashes;
- exact request-contract hash;
- fixed method and route;
- context-generation ID;
- maximum resolution count of one;
- consumed state.

Raw authentication, CSRF, or origin material is forbidden.  The evidence is
server-owned, client authoring and override are forbidden, and its producer is
unregistered.

## Trusted source-resolver contract

The future resolver accepts only the request-scope evidence contract and the
ADR0319 context shape.  It resolves the explicit ADR0311 document chain without
runtime, database, cache, filesystem, or network reads.  Client source documents
and provider context are forbidden.  Request-scope hash, context-generation ID,
and single-use guard are mandatory.

## Cross-binding contract

The cross-binding pins request scope, resolver, context, mount, provider, method,
route, and projection hashes.  It requires the same request scope, the same
context generation, all three security receipts, and an unconsumed scope.  It
has no implementation and remains unregistered.

Fixed hashes:

- request-scope field-order hash:
  `d1ba8add3e26442d8f691f1b13e5a4c03c7107d52c277b63d90fb7f136524000`
- request-scope contract hash:
  `e59927ea8ef3ef38a83647792a0a009a8ad022c959b14828119f5fa464769728`
- source-resolver contract hash:
  `7337b858ae1f1de7de0778347724f2c5d67690edce227fb5410759f8c55dee1a`
- cross-binding contract hash:
  `205454c6cd6e3829d7d19bdc52f0ebe3212bceddff50fa81067dd18c41eba91f`
- total preregistration hash:
  `8f2f3521a280610163f690ee53e414fabd48ae5dfc9f1ce0977457b9a959f72d`

## Remaining controls

Eight controls remain unregistered: authentication, CSRF, and origin receipt
providers; request-scope ID and context-generation ID providers; resolver
implementation; single-use guard; and independent binding review.  Context
implementation, handler, and route also remain absent, with 15 blockers total.

## Non-authority

ADR0320 does not authenticate a request, create security receipts, resolve source
documents, construct context, mutate request state, implement a handler, register
a route, or start a service.  It grants no current, writer, paper, live, or
trading authority and provides no profitability evidence.  The natural-forward
single-look chain, legacy pack-v5 UNKNOWN behavior, and pointer-v2 remain
unchanged.
