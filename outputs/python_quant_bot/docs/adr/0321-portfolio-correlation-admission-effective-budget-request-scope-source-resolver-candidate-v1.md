# ADR 0321: Request-scope evidence and source-resolver candidate v1

## Status

Accepted as a synthetic, in-memory, unregistered candidate. It is not an HTTP
mount, authentication implementation, runtime activation, paper permission, or
live permission.

## Context

ADR 0318 preregistered a read-only HTTP projection mount without activating it.
ADR 0319 preregistered a trusted internal context provider. ADR 0320 bound those
two descriptions to a request-scope evidence shape and source-resolver contract,
but deliberately supplied no executable request-scope verifier or single-use
context object.

The remaining narrow gap was testable without a server: prove that a synthetic
request scope can bind opaque receipt hashes to the frozen method, route, and
generation ID; snapshot exactly 13 positional and 10 keyword source values in
the already frozen contract order; expose only hash receipts; and allow the
private source context to be resolved once before it is discarded.

## Decision

Add
`portfolio_correlation_admission_effective_budget_request_scope_source_resolver_candidate_v1.py`.
The module has no I/O and no host registration. Its candidate contract hash is:

`5524137b7e093a197cdfaa256263540a3f50f09cb87d222bed084989d7fa3ac5`

The implementation:

1. Accepts only the exact ADR 0320 preregistration hash.
2. Requires lowercase 64-hex request-scope, receipt, request-contract, and
   context-generation identifiers.
3. Freezes the proposed `POST` method and research-only route rather than
   accepting caller overrides.
4. Exact-rebuild verifies the complete evidence envelope and its field order.
5. JSON-snapshots exactly 13 positional and 10 keyword source values in the
   frozen ADR 0319 contract order.
6. Places source hashes, never source documents, in the creation receipt.
7. Resolves the private context at most once, discards its stored references,
   and emits a sealed consumption receipt.
8. Keeps every artifact `BLOCKED`, `UNREGISTERED_CANDIDATE`, and
   `synthetic_only=true`.

The receipt hashes are opaque. Hash shape and equality are verified, but no
authentication, CSRF, origin, or request-content semantics are inferred from a
hash. The source order is bound to the previously preregistered role-order
hashes; this candidate does not reinterpret those role meanings.

## Consumer-first activation order

No item below is activated by this ADR. A future activation must proceed in this
order and stop fail-closed after any unmet gate:

1. Register real authentication, CSRF, and origin receipt producers with
   independently tested semantic verification.
2. Register a request-contract builder that derives the request hash from the
   actual parsed request rather than accepting a supplied hash.
3. Register a request-local owner that creates and destroys this context within
   one authenticated request lifecycle.
4. Register the already preregistered source-role adapter and prove exact
   positional and keyword binding against the projection consumer.
5. Register the projection consumer internally and prove `KNOWN`, `UNKNOWN`,
   and `BLOCKED` behavior without an external route.
6. Add the HTTP handler behind the existing fail-closed mount controls.
7. Consider external exposure only after independent adversarial review. This
   step cannot grant paper or live authority.

## Adversarial matrix

| Attack or drift | Required result |
| --- | --- |
| Wrong preregistration hash | No candidate |
| Uppercase, short, long, or non-hex identifier | No candidate |
| Reordered evidence fields | Verification failure |
| Evidence, fact, blocker, authority, or seal mutation | Verification failure |
| Caller method or route substitution | Impossible through the builder API |
| 12 or 14 positional sources | No context |
| 9 or 11 keyword sources | No context |
| Non-JSON or oversized source | No context |
| Caller mutates input after construction | Stored snapshot unchanged |
| Source value appears in receipt or representation | Test failure |
| Second context resolution | `None`; no second receipt |
| Consumption receipt mutation | Verification failure |
| Attempted HTTP/runtime/paper/live inference | Explicitly false authority |

## Consequences and remaining blockers

This closes the pure in-memory mechanics gap and makes replay, mutation, field
order, count, and disclosure failures directly testable. It does not connect the
candidate to `server.py`, `http_contract.py`, any provider, any database, any
cache, or any network.

The source-role adapter still needs a consumer-first integration proof against
the real read-only projection before registration. Real security receipt
producers and request-content hashing do not exist in this slice. The natural
forward evidence chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7
-> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`; legacy pack-v5 remains
`UNKNOWN`, and pointer-v2 is not reissued.
