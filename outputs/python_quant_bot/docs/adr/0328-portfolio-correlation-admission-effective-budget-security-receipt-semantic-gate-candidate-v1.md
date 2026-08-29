# ADR 0328: Security-receipt semantic gate candidate v1

## Status

Accepted as a fail-closed, synthetic, unregistered gate. This version has no
semantic success path and cannot activate the lifecycle owner or HTTP mount.

## Context

The request scope carries authentication, CSRF, and origin receipt hashes, while
ADR0326/0327 explicitly marks their semantics unverified. Hash shape and equality
cannot prove receipt issuer trust, request binding, principal authentication,
CSRF verification, or origin policy approval.

No host authentication provider, key, environment, session, runtime, database,
or route is authorized for this slice. Implementing a synthetic `verified=true`
path would create false authority. The useful executable behavior is therefore a
gate that cannot be bypassed by self-reported receipt fields.

## Decision

Add a security semantic gate with contract hash:

`141b844a7e43fc069921aefc99214d4d8cb1ee63f80408f249899d29839bad71`

Its preregistration hash is:

`9a0455aba48d9b3361aed84428b101c82352833cb3a32e09960b34afe46ab72f`

The preregistration freezes three provider roles and future receipt field-order
contracts:

- authentication: `99f62ad29526d6976aed07597e778b5163f60f66549148263cafa3d7b635901b`
- CSRF: `5913900c17d29f5577c260944e9180a7e89429ef2cd569ae2b0da0e8dda78f69`
- origin: `f60dd627e4568d19703aa8d108460ad1d092791a351a71a9cbcce2c0a5ad3197`

Every provider identity, callable identity, and registration hash is `null`;
`registered=false` and `semantic_verifier_bound=false`. Activation order requires
provider registration and receipt issuer/request-binding verification before an
internal lifecycle consumer and before any HTTP mount consideration.

The executable evaluation:

1. Exact-verifies preregistration, request evidence, and request scope binding.
2. Canonically hashes JSON receipt documents without embedding their contents.
3. Ignores caller fields such as `authenticated=true`, `verified=true`, or
   `allowed=true` because no trusted provider can attest them.
4. Always returns `status=UNKNOWN`,
   `gate_state=SECURITY_SEMANTICS_UNAVAILABLE`, and
   `permission_state=UNAUTHORIZED`.
5. Exposes no override capable of enabling semantic success.

## Adversarial matrix

| Case | Required result |
| --- | --- |
| No receipt documents | UNKNOWN and unauthorized |
| Three forged self-reported success documents | UNKNOWN and unauthorized |
| Private principal/token/origin sentinels | Hash-only output, no echo |
| Non-JSON receipt | Null document hash, still UNKNOWN |
| Provider slot changed to registered | Preregistration verification fails |
| Request/scope mismatch | No evaluation |
| Evaluation fact or authority mutation | Verification fails |
| Attempt to activate lifecycle or HTTP | No API path |

## Consequences and next activation slice

Opaque hashes can no longer be mistaken for semantic security evidence in this
candidate chain. A future version must bind real host-owned provider identities
and fixed verifier callables, validate issuer trust and exact request/scope
bindings, and undergo independent adversarial review before it can introduce a
semantic success state.

Natural-forward evidence, legacy pack-v5 `UNKNOWN`, pointer-v2, profitability
claims, and paper/live locks remain unchanged.
