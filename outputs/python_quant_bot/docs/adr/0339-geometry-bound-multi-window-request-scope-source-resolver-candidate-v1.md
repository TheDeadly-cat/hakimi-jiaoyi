# ADR 0339: Geometry-bound multi-window request-scope source resolver candidate v1

- Status: Accepted as synthetic, unregistered candidate only
- Date: 2026-08-24
- Scope: ADR0338 request-scope/source-resolver gap
- Decision authority: none for HTTP mounting, current activation, paper, or live

## Context

ADR0337 freezes the trusted internal provider's three request roles, seven verification-context roles, and provider-output shape. ADR0338 preregisters the authenticated request-scope and trusted ADR0334 source-resolver boundaries, but deliberately leaves every producer, resolver, single-use guard, provider, handler, and route unregistered.

The remaining narrow gap is concrete: there was no pure-memory object that could bind an already supplied synthetic request scope to exact 3+7 role values, detach those values from caller mutation, expose only hash receipts before use, and resolve them no more than once. The preregistration document alone cannot prove those properties.

## Decision

Add a versioned, pure-memory request-local source-context candidate with these constraints:

1. It accepts only an exact ADR0338 request-scope evidence candidate and exact ordered dictionaries for ADR0337's three request roles and seven verification-context roles.
2. It accepts only exact JSON trees, rejects non-finite numbers, cycles, non-string object keys, extra/missing/reordered roles, and canonical contexts larger than 1,000,000 bytes.
3. It snapshots every value before construction, so later caller mutation cannot alter the resolved context.
4. Its creation receipt contains canonical hashes by role, scope/generation bindings, and a derived context hash, but no source documents.
5. Its constructor is token-locked. The context resolves once, returns deep copies in frozen role order, emits a consumption receipt, clears retained source values, and then refuses reuse.
6. Hash receipts are structural evidence only. They are not signatures and do not authenticate the caller, security receipts, source semantics, or source producer.
7. The candidate remains `BLOCKED`, synthetic-only, unregistered, and unavailable from HTTP.

## Frozen pins

- ADR0338 preregistration hash: `6d6b20197a5341b5462716b97dc968e4e5496d10d4c752b3d5d5d86a70345586`
- Request-scope contract hash: `e7843b2719cd5bac016bab8e2b4cf65a154a5dc77fb2e497a593ae821f343737`
- Source-resolver contract hash: `408877a2eb1c5df48f427bf960761e553bd106cea42a3644bce02b687aa843d4`
- Cross-binding contract hash: `cf04835edd16a09a6ba06024c62d7c3726a31bfa2546950dbfabc5a614732d97`
- ADR0337 provider preregistration hash: `a0f387aaf2cd2730e5fc6ab795ce90bbcb82f25d4b21f5e79868d1181eb15ec8`
- Provider output shape hash: `e8ab642585b4c1ef1f7f6358e1127c30313a15bf5338ce4c38317f2257b5ba72`
- Request role hash: `2d6ad49ff964471733c26c428a8450757d4e00c3f1f268510fd950d31a8d1928`
- Verification-context role hash: `e437b2ec29452cfa8a899a95042f834617ec61648f3cebfaa4453578a9162299`
- ADR0339 candidate contract hash: `dcc7b3f75e89dc676594c3ab5370270eb7eec60e62f8ee542c38dc0c60d2df9f`
- Static fingerprint: `20260824-strategy-correlation-matrix-geometry-budget-multi-window-presentation-request-scope-source-resolver-candidate-v1-unbound-lock-1`

## Consumer-first activation order

1. Keep ADR0339 callable only through direct synthetic construction.
2. Independently review exact role ordering, snapshot isolation, receipt redaction, size limits, single-use clearing, and fail-closed rejection.
3. Implement trusted ADR0334 source production separately. Do not accept client-provided candidate documents or verification context.
4. Register real authentication, CSRF, origin, request-scope ID, and context-generation ID producers separately.
5. Implement and review the trusted internal provider only after source production and request-scope evidence are independently bound.
6. Bind a handler only by a separate ADR after all ADR0336 transport controls pass.
7. Register the proposed route only by explicit authorization.
8. Consider any `current` activation only by a separate decision. Never infer paper/live authority.

## Adversarial matrix

| Threat | Expected result |
| --- | --- |
| Wrong preregistration or noncanonical opaque hash | Construction returns `None` |
| Scope field reordering, value mutation, or extra field | Verification fails |
| Missing, extra, or reordered 3+7 role | Context construction returns `None` |
| Custom/non-JSON value, cycle, NaN, or oversized context | Context construction returns `None` |
| Caller mutates inputs after construction | Resolved snapshot is unchanged |
| Receipt embeds source documents | Forbidden by exact receipt schema |
| Receipt field/order/source hash tamper | Verification fails |
| Direct constructor bypass | Raises `TypeError` |
| Second resolution attempt | Returns `None` |
| Consumption count/context binding tamper | Verification fails |
| Security hash shape presented as authentication | Explicitly not claimed |
| Candidate presented as mounted/current/paper/live | Explicitly unauthorized |

## Non-goals and remaining blockers

- No ADR0334 source production or semantic verification.
- No authentication, CSRF, origin, request-scope, or generation-ID provider registration.
- No cryptographic authentication of receipts.
- No trusted internal provider implementation.
- No handler binding or route registration.
- No runtime, database, cache, filesystem, network, scheduler, browser, or trading access.
- No change to the natural-forward single-look chain, legacy pack-v5 behavior, or pointer-v2.
- No profitability claim and no paper/live permission.
