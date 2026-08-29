# ADR 0337: Geometry-bound multi-window trusted internal provider preregistration v1

- Status: accepted as a blocked preregistration
- Date: 2026-08-24
- Scope: request-local source ownership and lifecycle policy only

## Context

ADR0336 requires a trusted internal provider before any handler or route can
consume ADR0335. The provider is not implemented or registered. Without an
exact output shape and ownership contract, a future handler could accept the
ADR0334 evaluation, adapter, verification contexts, expected hashes, or source
documents from the client, stale process state, cache, database, filesystem, or
another request.

Wall-clock freshness does not prove request ownership. This boundary instead
requires one synchronous authenticated request scope, one resolution, one use,
and immediate discard after the bounded candidate response.

## Decision

Preregister, but do not implement, a trusted internal provider with:

- 3 exact ordered candidate-request roles;
- 7 exact ordered verification-context roles;
- source ownership restricted to the exact internal ADR0334 chain;
- no client request, candidate, context, hash, freshness, or source override;
- same synchronous request-scope freshness with no clock or timestamp;
- maximum resolution count of one and mandatory single-use guard;
- no persistence, runtime, database, cache, filesystem, or network use;
- mandatory discard after the candidate response;
- no request, provider output, candidate, context, position, or symbol logging.

The fixed shape hashes are:

- request role hash:
  `2d6ad49ff964471733c26c428a8450757d4e00c3f1f268510fd950d31a8d1928`
- verification-context role hash:
  `e437b2ec29452cfa8a899a95042f834617ec61648f3cebfaa4453578a9162299`
- provider-output shape hash:
  `e8ab642585b4c1ef1f7f6358e1127c30313a15bf5338ce4c38317f2257b5ba72`

## Pinned predecessor

ADR0337 exact-verifies ADR0336 and pins its preregistration hash, source, tests,
ADR, candidate source/contract, schemas, proposed method, and proposed route.
ADR0336 must remain unmounted, handlerless, endpointless, provider-unbound, and
client-source-denying.

## Unregistered controls

- provider implementation;
- authenticated request-scope provider;
- trusted ADR0334 source resolver;
- context generation-ID provider;
- single-use guard;
- provider redaction policy;
- independent provider review.

Handler and route bindings remain null. ADR0336 authentication, CSRF, rate,
body, log, handler, review, and route controls remain incomplete.

## Consumer-first activation order

1. Verify ADR0336, ADR0337, and all source pins exactly.
2. Register an authenticated request-scope provider.
3. Register a trusted ADR0334 source resolver.
4. Implement the provider in a separate version.
5. Register generation ID, single-use guard, and redaction policy.
6. Complete independent provider review.
7. Bind the provider to a separately versioned handler only by explicit review.
8. Keep the route unregistered until every ADR0336 control passes.
9. Consider browser, current, paper, or live authority only separately.

## Adversarial acceptance matrix

- Exact deterministic document: BLOCKED and exactly verifiable.
- Role reorder, source substitution, client override, lifecycle reuse,
  persistence, logging, binding, or authority promotion: rejected.
- Malicious Mapping second-read swaps: one snapshot only.
- Cyclic, nonmapping, runtime-bearing, secret-bearing, or policy-override input:
  fail closed or cannot enter the public builder API.

## Consequences

ADR0336 now has an exact provider ownership contract without a provider,
handler, route, runtime source, or UI. This ADR does not prove profitability and
grants no current, writer, paper, live, or trading authority.
