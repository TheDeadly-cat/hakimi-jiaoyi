# ADR 0343: Geometry-bound multi-window request-lifecycle owner candidate v1

- Status: Accepted as synthetic, unregistered, atomic terminal-rejection owner
- Date: 2026-08-24
- Scope: one in-process claim over one exact ADR0342 UNKNOWN gate result
- Decision authority: no authenticated claim, provider/handler invocation, HTTP mount, current, paper, or live

## Context

ADR0342 exact-verifies the complete request/scope/source/context chain but intentionally returns only `UNKNOWN` and `UNAUTHORIZED` because no security provider or issuer trust is registered. A lifecycle object is still useful to prevent retries, reentrancy, or accidental downstream invocation after that terminal security decision.

The older ADR0326 owner attempted an adapter and ADR0327 later added an explicit in-process atomic claim. Repeating that sequence would add an avoidable concurrency gap. It would also be wrong to invoke any provider or adapter while ADR0342 has no semantic success state.

## Decision

Add an already-hardened lifecycle owner candidate with these properties:

1. Construction exact-verifies the ADR0342 preregistration and evaluation against ADR0341 request evidence, ADR0339 scope/context receipt, ADR0340 production receipt, and the same optional security receipt documents.
2. Construction requires the gate to remain `UNKNOWN`, `SECURITY_SEMANTICS_UNAVAILABLE`, and `UNAUTHORIZED` with security semantics and authenticated-request authorization false.
3. The creation receipt stores only frozen contract hashes and hashes already emitted by ADR0342. It embeds no request, source, context, or security receipt document.
4. A private in-process lock atomically combines attempted/closed checks with the single claim.
5. `claim_once()` has no caller-controlled arguments and performs no context, provider, adapter, handler, filesystem, network, database, or runtime call.
6. The only terminal outcome is `CLAIM_REJECTED_SECURITY_SEMANTICS_UNAVAILABLE` with `authenticated_claim_created=false`.
7. The first claim closes the owner. Sequential, reentrant, and concurrent losing claims return `None`.
8. Creation, claim, and result receipts have exact rebuild verifiers and neutral authority.

## Frozen contract

- Lifecycle owner contract hash: `73833a5ada7b94b52bbf7ec86130f033dab0ca582288b946a4d7a67498efd202`
- ADR0342 gate contract hash: `f1da8347793aee5d57462ab2c46a38cce3dcd6889c78bb975a65a0b0c0a3e645`
- ADR0342 preregistration hash: `580e8b14d316c47b80c660bc7ad2236351e5daaa80f1246ee45fd4501c6be372`
- ADR0341 request-evidence contract hash: `0d0046487ff4fab91d2be6e7dc1e2da0d352560aabc16250009809164341725a`
- ADR0340 source-producer contract hash: `f6148d309a3343324347019811055f449d7621046afd460e5a79d3b622da9389`
- ADR0339 source-resolver contract hash: `dcc7b3f75e89dc676594c3ab5370270eb7eec60e62f8ee542c38dc0c60d2df9f`
- Maximum claim attempts: 1
- Claim mode: `ATOMIC_IN_PROCESS_ALWAYS_REJECT_UNKNOWN_GATE`
- Static fingerprint: `20260824-strategy-correlation-matrix-geometry-budget-multi-window-presentation-request-lifecycle-owner-candidate-v1-synthetic-unregistered-atomic-lock-1`

## Adversarial matrix

| Threat | Required result |
| --- | --- |
| Tampered gate, request, scope, source, context, or receipt document | No owner |
| Valid UNKNOWN gate | Owner created, but authenticated claim impossible |
| First claim | Closed terminal rejection |
| Sequential retry | `None` |
| Eight concurrent claims | Exactly one non-null terminal result |
| Caller attempts to supply context/provider/handler during claim | API has no such arguments |
| Creation, claim, result, or field-order mutation | Verification fails |
| Private receipt sentinel | No receipt/result/repr echo |
| Durable or cross-process idempotency inference | Explicitly false |
| HTTP/current/paper/live/profitability inference | Explicitly false |

## Remaining blockers

- ADR0342 still has no registered security provider, semantic verifier, issuer trust, or success state.
- This owner is an in-process lock, not a durable idempotency store or distributed mutex.
- No trusted internal provider, adapter, handler, route, or current activation is invoked or registered.
- A future authenticated owner must use a separate version and cannot reinterpret this rejection receipt as success.
- No runtime, database, cache, filesystem, network, scheduler, browser, or trading access is introduced.
- Natural-forward evidence, legacy pack-v5 public UNKNOWN behavior, and pointer-v2 remain unchanged.
- No profitability claim and no paper/live authority are created.
