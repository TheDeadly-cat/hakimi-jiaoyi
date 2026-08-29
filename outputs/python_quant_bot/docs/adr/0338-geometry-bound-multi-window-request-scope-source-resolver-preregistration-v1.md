# ADR 0338: Geometry-bound multi-window request-scope and source-resolver preregistration v1

- Status: accepted as a blocked three-contract preregistration
- Date: 2026-08-24
- Scope: security evidence and ADR0334 source-resolution contracts only

## Context

ADR0337 defines a request-local provider output shape but intentionally leaves
authenticated request-scope evidence and the trusted ADR0334 source resolver
unimplemented. Combining them would obscure whether evidence belongs to the
same authenticated request, whether the context generation matches, and whether
the one allowed resolution was already consumed.

ADR0338 therefore keeps request-scope evidence, source resolution, and their
cross-binding as three separate hash-pinned contracts. It creates none of them.

## Request-scope evidence contract

The future evidence contains only 11 ordered fields: request-scope ID; hashes
for authentication, CSRF, origin, and exact request contract; fixed method and
route; context-generation ID; maximum resolution count one; and consumed state.
Raw security material, client authoring, and client override are forbidden.

## Trusted ADR0334 source-resolver contract

The future resolver accepts only the request-scope evidence schema and ADR0337
provider-output shape. It must reconstruct the explicit internal ADR0334 chain
without runtime, database, cache, filesystem, or network reads. Client source
documents and provider context are forbidden. Request-scope hash,
context-generation ID, and single-use guard are mandatory.

## Cross-binding contract

The cross-binding pins request scope, resolver, provider, mount, candidate,
method, and route hashes. It requires the same request scope, same context
generation, all three security receipt hashes, and an unconsumed scope. It has
no implementation and remains unregistered.

Fixed hashes:

- request-scope field-order hash:
  `d1ba8add3e26442d8f691f1b13e5a4c03c7107d52c277b63d90fb7f136524000`
- request-scope contract hash:
  `e7843b2719cd5bac016bab8e2b4cf65a154a5dc77fb2e497a593ae821f343737`
- source-resolver contract hash:
  `408877a2eb1c5df48f427bf960761e553bd106cea42a3644bce02b687aa843d4`
- cross-binding contract hash:
  `cf04835edd16a09a6ba06024c62d7c3726a31bfa2546950dbfabc5a614732d97`

## Remaining controls

Authentication, CSRF, and origin receipt providers; request-scope ID and
context-generation ID providers; resolver implementation; single-use guard;
and independent binding review remain unregistered. Provider implementation,
handler, route, and ADR0336 transport controls also remain absent, with 15
explicit blockers.

## Consumer-first activation order

1. Verify ADR0337, ADR0338, and every source pin exactly.
2. Register authentication, CSRF, and origin receipt providers.
3. Register request-scope and context-generation ID providers.
4. Implement the trusted ADR0334 resolver in a separate version.
5. Register the single-use guard and complete independent binding review.
6. Implement the provider only after all three contracts verify.
7. Bind a handler only by separate explicit decision.
8. Keep the route unregistered until every ADR0336 control passes.
9. Consider browser, current, paper, or live authority only separately.

## Adversarial acceptance matrix

- Exact deterministic document: BLOCKED and exactly verifiable.
- Receipt, field-order, provider, source, method, route, scope, generation,
  consumed-state, resolver, guard, or authority promotion: rejected.
- Malicious Mapping second-read swaps: one snapshot only.
- Cyclic, runtime-bearing, secret-bearing, or policy-override input: fail closed
  or cannot enter the public builder API.

## Consequences

ADR0337 now has explicit request-scope, source-resolver, and cross-binding
contracts without creating security evidence, resolving sources, implementing a
provider, binding a handler, or registering a route. This ADR supplies no
profitability evidence and grants no trading authority.
