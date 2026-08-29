# ADR 0326: Request-lifecycle owner candidate v1

## Status

Accepted as a synthetic, in-memory, unregistered lifecycle candidate. It does
not claim authenticated ownership and does not activate HTTP or trading.

## Context

ADR0325 established one request snapshot and bound its derived contract hash to
the request scope. The adapter could still be called directly and no object
owned the transition from a created request scope to one terminal outcome. A
future host could accidentally retry after an invalid binding, adapter rejection,
or consumed-context replay.

Security receipt hashes remain opaque. Therefore this ADR can prove lifecycle
mechanics but cannot call the lifecycle authenticated.

## Decision

Add a request-lifecycle owner candidate with contract hash:

`5b4873fc01d928195283e4f31846a74336dd0a027876e55ac62b28032a791c03`

The owner:

1. Exact-verifies and snapshots one ADR0325 request evidence document and one
   ADR0322 request scope with matching request-contract hashes.
2. Emits a creation receipt binding request, scope, generation, and opaque
   authentication/CSRF/origin receipt hashes without source documents.
3. Allows exactly one `execute_once` call.
4. Marks the attempt before invoking the adapter, preventing reentrant or later
   retry even if the adapter rejects or raises.
5. Closes after every attempt and returns a sealed execution result for both
   `ADAPTER_ACCEPTED` and `ADAPTER_REJECTED` outcomes.
6. Records whether context consumption was observed, but does not infer security
   receipt semantics or adapter semantic provenance from lifecycle consistency.
7. Discards its private request and scope snapshots after closure.

Successful adapter semantic provenance remains independently verifiable through
the ADR0324 source-bearing verifier. The lifecycle result verifier checks
deterministic consistency and the exact adapter envelope without re-executing
source semantics.

## Adversarial matrix

| Case | Required result |
| --- | --- |
| Valid request/scope/context/binding | One accepted result, then closed |
| Invalid binding | Rejected result, context unconsumed, then closed |
| Retry after rejection | `None` |
| Retry after success | `None` |
| Reuse consumed context under another owner | Second owner rejects and closes |
| Request/scope hash mismatch | No owner |
| Direct constructor bypass | `TypeError` |
| Result, receipt, adapter, or consumption-state mutation | Verification fails |
| Source sentinel in receipt/result/repr | No match |
| Security hashes presented as authentication | Explicitly false |

## Consequences and blockers

This closes single-attempt and terminal-close mechanics without creating host
state, timers, sessions, databases, caches, or routes. The owner is not a mutex
across processes and its private token is not protection against hostile Python
introspection.

Real security receipt producers and semantic verification, authenticated host
request ownership, internal registration, mount controls, and independent
external-exposure review remain blockers. Natural-forward evidence, legacy
pack-v5 `UNKNOWN`, pointer-v2, profitability claims, and paper/live locks remain
unchanged.
