# ADR 0323: Read-only projection adapter candidate v1

## Status

Accepted as a synthetic, in-memory, unregistered application adapter candidate.
It does not register an HTTP handler, activate a runtime consumer, or authorize
paper/live trading.

## Context

ADR0322 closed the request-scope creation and consumption receipt chain, but no
code proved that its contract-ordered source snapshots could reach the real
ADR0317 read-only projection without role drift. A generic or injected consumer
would only prove an adapter shape. The required evidence is stronger: invoke the
actual fixed projection callable with the actual ADR0319 role order and reproduce
the already known synthetic projection result.

The real consumer accepts one request plus three keyword-only boundaries:
provider binding, 13 positional provider documents, and 10 keyword provider
documents. The frozen keyword roles are `strategy_id`, `variant_id`, `lane`,
`equity`, `positions`, `proposed_symbol`, `proposed_notional`,
`proposed_direction`, `max_cluster_gross_pct`, and `risk_increasing`.

## Decision

Add an application-layer adapter with contract hash:

`b5a0894605088509d85e70163c77b6c9bcf8957469577f95f00a4e996bc8ad51`

The fixed projection callable identity hash is:

`5ea17db6e382d81457eed6e0d75e43e7b99636129f00fa0e367e8039d3969725`

The adapter:

1. Imports the real ADR0317 builder directly and verifies its module, qualified
   name, parameter names, and parameter kinds.
2. Snapshots the request and provider binding once before validation or use.
3. Verifies the ADR0322 request scope and exact creation receipt before consuming
   the request-local source context.
4. Resolves the source context once, verifies the consumption receipt, and
   independently matches all 23 resolved source hashes with the creation receipt.
5. Maps the 10 keyword values with the exact ADR0319 role tuple and preserves the
   13 positional values in exact contract order.
6. Invokes the fixed projection once and verifies the returned response schema,
   field order, and canonical response seal without invoking the provider again.
7. Returns only the hash-only projection, role names/hashes, and hash receipts.
   Source documents and source values are not retained in adapter evidence.
8. Keeps the adapter `BLOCKED`, `UNREGISTERED_CANDIDATE`, and
   `synthetic_only=true` with all execution authority false.

## Evidence target

Using the existing synthetic ADR0317 fixture, the adapter must reproduce the
known projection response hash exactly:

`4dee39b6203ce91a90f955af6e132a2dfc9968f003806a7d7f4a76c7bed7c8a1`

The real ADR0317 verifier is exercised separately against the adapter's response
and original synthetic sources. The adapter verifier intentionally does not
re-run provider semantics because that would invoke the provider a second time;
it exact-rebuilds adapter evidence and verifies the projection's own seal instead.

## Adversarial matrix

| Attack or drift | Required result |
| --- | --- |
| Wrong binding or request scope | Reject before context consumption |
| Reused context | Reject; no second projection call |
| Source hash differs from creation receipt | Reject after one-shot consumption |
| Keyword role swap | Cannot reproduce known response hash |
| Positional role swap | Cannot reproduce known response hash |
| Request, scope, receipt, projection, fact, or seal mutation | Adapter verification fails |
| Caller mutates source after context creation | Stored snapshot remains stable |
| Source sentinel in adapter evidence | No match |
| Callable module, name, or signature drift | Reject before consumption |
| HTTP/runtime/paper/live/profitability inference | Explicitly false |

## Consequences and remaining blockers

This closes the exact internal mapping proof against the real projection while
remaining detached from host code. The source file hash is externally pinned in
baseline evidence; the in-process callable check cannot independently re-read
and hash its own source, so a future activation manifest must retain that check.

Real security receipt producers, actual request-content hashing, request
lifecycle ownership, internal consumer registration, mount controls, and
independent exposure review remain blockers. The natural-forward evidence chain,
legacy pack-v5 `UNKNOWN` behavior, pointer-v2 contract, and paper/live locks are
unchanged.
