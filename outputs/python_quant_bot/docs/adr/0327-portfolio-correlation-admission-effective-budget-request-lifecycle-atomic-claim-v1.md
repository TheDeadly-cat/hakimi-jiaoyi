# ADR 0327: Request-lifecycle atomic claim v1

## Status

Accepted as an in-process hardening of the synthetic, unregistered ADR0326
lifecycle owner. It is not authentication, a cross-process lock, or activation.

## Finding

ADR0326 correctly closed after one sequential adapter attempt, but two narrow
implementation risks remained:

1. The check and assignment of the attempt flag were separate bytecode steps.
   Concurrent callers in one Python process had no explicit atomic claim.
2. After adapter rejection, the owner read `consumed` from any supplied object.
   An untrusted property could raise and prevent emission of the terminal CLOSED
   receipt even though the owner had already attempted execution.

## Decision

Revise the owner to static fingerprint `lock-2` and contract hash:

`f9e349c876a243a966429b98645a23e6d41e093ab58102980e760748c16cf42d`

The ADR0326 `lock-1` contract
`5b4873fc01d928195283e4f31846a74336dd0a027876e55ac62b28032a791c03`
is retained as lineage only.

The hardened owner:

1. Uses a private in-process lock to combine attempted/closed checks with the
   single attempt claim.
2. Makes concurrent losing calls return `None` without invoking the adapter or
   consuming their contexts.
3. Reads `consumed` only when the object has the exact controlled
   `RequestLocalSourceContextCandidateV1` type.
4. Treats every other object as unconsumed, emits `ADAPTER_REJECTED`, and closes
   without evaluating arbitrary properties.
5. Keeps the lock private and outside all receipts, preserving deterministic,
   clockless evidence.

## Adversarial matrix

| Case | Required result |
| --- | --- |
| Eight concurrent calls on one owner | Exactly one non-null result |
| Contexts supplied by losing concurrent calls | Remain unconsumed |
| Object with throwing `consumed` property | Property not evaluated |
| Rejected malicious object | Closed rejection receipt |
| Sequential retry | `None` |
| Cross-process or distributed exclusion claim | Explicitly unsupported |

## Consequences

The lifecycle owner now provides explicit single-process concurrency semantics.
It remains neither a durable idempotency store nor a distributed mutex. A future
host still needs authenticated security receipt providers, request ownership,
and an external replay/idempotency boundary before registration.

Natural-forward evidence, legacy pack-v5 `UNKNOWN`, pointer-v2, profitability
claims, and paper/live locks remain unchanged.
