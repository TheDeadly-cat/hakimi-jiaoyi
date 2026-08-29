# ADR 0340: Geometry-bound multi-window trusted ADR0334 source producer candidate v1

- Status: Accepted as synthetic, unregistered candidate only
- Date: 2026-08-24
- Scope: trusted ADR0334 source production into the ADR0339 request-local resolver
- Decision authority: none for request authentication, provider binding, HTTP mounting, current, paper, or live

## Context

ADR0339 closes the request-local storage and single-use gap for the exact ADR0337 3+7 role shape. It deliberately accepts already supplied role values and does not establish where those values came from or whether the embedded ADR0334 evaluation is exact.

A caller could therefore use ADR0339 correctly as a storage contract while still constructing the three request roles from an unverified or caller-authored evaluation. Registering a provider or route on that basis would confuse shape integrity with trusted source production.

## Decision

Add a token-locked, pure-memory ADR0334 source producer candidate with these properties:

1. It accepts only a verified ADR0339 request-scope candidate, two explicit ADR0334 source documents, and their two verification contexts.
2. It derives the expected presentation and adapter hashes from the source documents. Callers cannot supply or override those hashes.
3. It accepts only bounded exact JSON trees, snapshots inputs before use, and rejects missing hashes, non-JSON values, cycles, non-finite values, and source bundles larger than 1,000,000 canonical bytes.
4. It invokes the frozen ADR0334 evaluator and then the ADR0334 exact verifier. Only a verifier receipt with exact field order, `status=PASS`, the same evaluation hash, and all authority fields false may continue.
5. The ADR0334 evaluation itself may remain `PASS`, `BLOCK`, or `UNKNOWN`. Exact negative evidence is preserved rather than discarded or promoted.
6. It constructs the ADR0337 request and verification-context roles internally, then delegates snapshot, source hashing, creation receipts, and exactly-once resolution to ADR0339.
7. Its producer receipt binds the request scope, ADR0339 creation receipt, ADR0334 evaluation hash, and exact-verifier receipt. It embeds no source document.
8. The producer hands off its ADR0339 context once and then clears its reference.

## Frozen contract

- ADR0340 candidate contract hash: `f6148d309a3343324347019811055f449d7621046afd460e5a79d3b622da9389`
- Static fingerprint: `20260824-strategy-correlation-matrix-geometry-budget-multi-window-presentation-trusted-adr0334-source-producer-candidate-v1-unbound-lock-1`
- ADR0334 binding contract hash: `32edce4777fa90cdc1c79536ea3187133775a368e0e1e401db9f82c165122e47`
- ADR0339 resolver candidate contract hash: `dcc7b3f75e89dc676594c3ab5370270eb7eec60e62f8ee542c38dc0c60d2df9f`
- ADR0337 provider output shape hash: `e8ab642585b4c1ef1f7f6358e1127c30313a15bf5338ce4c38317f2257b5ba72`
- ADR0337 request role hash: `2d6ad49ff964471733c26c428a8450757d4e00c3f1f268510fd950d31a8d1928`
- ADR0337 verification-context role hash: `e437b2ec29452cfa8a899a95042f834617ec61648f3cebfaa4453578a9162299`
- Maximum source input: 1,000,000 canonical bytes
- Maximum producer handoff: 1

## Consumer-first activation order

1. Keep ADR0340 available only through direct synthetic calls.
2. Independently verify bounded snapshotting, derived hashes, exact ADR0334 replay, negative-evidence preservation, receipt redaction, and double single-use handoff.
3. Add a separate semantic gate for authentication, CSRF, origin, request-scope ID, request-contract hash, and context-generation ID receipts.
4. Bind ADR0340 to a real request-lifecycle owner only after those receipt producers are registered.
5. Implement the trusted internal provider as a separate version that consumes, but cannot bypass, the ADR0340 producer.
6. Bind a handler only after all ADR0336 transport controls pass.
7. Register the proposed route and consider `current` only through separate explicit decisions.

## Adversarial matrix

| Threat | Required result |
| --- | --- |
| Invalid or tampered request scope | Reject before ADR0334 invocation |
| Caller supplies missing or malformed source hash | Reject before ADR0334 invocation |
| Non-JSON, cyclic, non-finite, or oversized source | Reject |
| ADR0334 evaluator raises or returns a non-document | Reject |
| ADR0334 exact verifier returns `BLOCK` or malformed receipt | Reject |
| ADR0334 evaluation is exact but neutrally `BLOCK` | Preserve it without promotion |
| Caller mutates inputs after production | Resolved context remains unchanged |
| Producer receipt embeds source documents | Forbidden |
| Producer or receipt constructor bypass | Reject or fail exact verification |
| Second producer handoff or second resolver use | Return `None` |
| File, network, database, cache, or runtime access | Forbidden |
| HTTP/current/paper/live/profitability inference | Explicitly false |

## Remaining blockers

- Security receipt hashes remain structurally shaped but semantically unauthenticated.
- Request-scope and context-generation ownership remain unregistered.
- Source provenance has no cryptographic authentication or registered lifecycle owner.
- The trusted internal provider is not implemented or bound.
- No handler or route is registered.
- No runtime, database, cache, filesystem, network, scheduler, browser, or trading access is introduced.
- The natural-forward chain, legacy pack-v5 public UNKNOWN behavior, and pointer-v2 remain unchanged.
- No profitability claim and no paper/live authority are created.
