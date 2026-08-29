# ADR 0342: Geometry-bound multi-window security-receipt semantic gate candidate v1

- Status: Accepted as synthetic, unregistered, always-UNKNOWN gate
- Date: 2026-08-24
- Scope: authentication, CSRF, and origin receipt semantics after exact request/source cross-binding
- Decision authority: no semantic success, lifecycle activation, provider binding, HTTP mount, current, paper, or live

## Context

ADR0341 derives `request_contract_hash` from the actual canonical internal request. ADR0340 exact-verifies the ADR0334 source chain and binds its production receipt to ADR0339's request-local context receipt. These prerequisites make it possible to distinguish non-security cross-binding from security-receipt semantics.

The host still has no registered authentication, CSRF, or origin provider identity; no fixed semantic-verifier callable; and no receipt-issuer trust root. Hash shape, caller-authored success flags, and even a self-reported receipt hash matching the request scope cannot establish those missing semantics.

## Decision

Add an always-UNKNOWN semantic gate with these properties:

1. Exact-verify ADR0341 request evidence and ADR0339 request scope.
2. Require the scope's request-contract hash, method, and route to equal ADR0341's derived contract.
3. Exact-verify ADR0340's production receipt against the same ADR0339 scope and context-creation receipt.
4. Require ADR0341 and ADR0340 to bind the same ADR0334 evaluation hash.
5. Freeze future authentication, CSRF, and origin receipt field orders, including provider/callable identity, scope/generation, request, evaluation, source-production, nonce, and receipt-hash bindings.
6. Canonically hash supplied receipt documents without embedding their contents.
7. Observe a self-reported receipt hash matching the scope, but explicitly treat that observation as non-authoritative.
8. Ignore caller fields such as `authenticated=true`, `verified=true`, and `allowed=true`.
9. Always return `status=UNKNOWN`, `gate_state=SECURITY_SEMANTICS_UNAVAILABLE`, and `permission_state=UNAUTHORIZED` after all non-security cross-bindings verify.
10. Return `None` when preregistration or any request/scope/source/context cross-binding fails.

## Frozen contract

- Gate contract hash: `f1da8347793aee5d57462ab2c46a38cce3dcd6889c78bb975a65a0b0c0a3e645`
- Preregistration hash: `580e8b14d316c47b80c660bc7ad2236351e5daaa80f1246ee45fd4501c6be372`
- Authentication receipt field-order hash: `00049f40df5bde5a1afba4805565c538c63f3446c2a7d63a76ad3ba53548280d`
- CSRF receipt field-order hash: `898a56fa990a2844792422652fe9e02bcff96ce5bc8d69474d1c5b750281895e`
- Origin receipt field-order hash: `26e641bad6a0adb8bb8ba2f1d075bfdb955b4b2eb61a57cb24932ca9f2477191`
- ADR0341 request-evidence contract hash: `0d0046487ff4fab91d2be6e7dc1e2da0d352560aabc16250009809164341725a`
- ADR0340 source-producer contract hash: `f6148d309a3343324347019811055f449d7621046afd460e5a79d3b622da9389`
- ADR0339 source-resolver contract hash: `dcc7b3f75e89dc676594c3ab5370270eb7eec60e62f8ee542c38dc0c60d2df9f`
- Static fingerprint: `20260824-strategy-correlation-matrix-geometry-budget-multi-window-presentation-security-receipt-semantic-gate-candidate-v1-unregistered-lock-1`

## Consumer-first activation order

1. Register host-owned authentication, CSRF, and origin provider identities.
2. Bind fixed semantic-verifier callable identities.
3. Bind trusted receipt issuers and key/version policy without exposing secrets.
4. Verify exact receipt schema, seal, nonce, scope/generation, request, evaluation, and source-production bindings.
5. Add replay protection and register an authenticated request-lifecycle owner.
6. Implement a trusted internal provider that cannot bypass this gate.
7. Bind a handler, register the route, and consider `current` only through separate explicit decisions.

## Adversarial matrix

| Threat | Required result |
| --- | --- |
| Forged success flags | UNKNOWN and unauthorized |
| Self-reported receipt hash exactly matches scope | Observed but non-authoritative |
| Private principal/token/origin data | Hash-only output, no echo |
| Non-JSON receipt | Null document hash, still UNKNOWN |
| Scope/request contract mismatch | No evaluation |
| Request/source ADR0334 evaluation mismatch | No evaluation |
| Context or source-production receipt tamper | No evaluation |
| Provider slot changed to registered | Preregistration fails |
| Evaluation or nested order/authority mutation | Exact verification fails |
| Attempt to find semantic success branch | No such branch exists |
| File, network, database, cache, runtime, or trading access | Forbidden |

## Remaining blockers

- Every provider identity, callable identity, registration hash, and issuer-trust binding remains null/unregistered.
- Receipt seals, nonce replay protection, request-lifecycle ownership, and key/version policy are not implemented.
- No trusted internal provider, handler, route, or current activation exists.
- No runtime, database, cache, filesystem, network, scheduler, browser, or trading access is introduced.
- Natural-forward evidence, legacy pack-v5 public UNKNOWN behavior, and pointer-v2 remain unchanged.
- No profitability claim and no paper/live authority are created.
