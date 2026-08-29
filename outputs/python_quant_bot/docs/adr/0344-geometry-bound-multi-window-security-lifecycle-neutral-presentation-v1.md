# ADR 0344: Geometry-bound multi-window security lifecycle neutral presentation v1

## Status

Accepted as an unmounted synthetic candidate. It is not registered, current, or authorized for runtime use.

## Context

ADR 0342 terminates at `SECURITY_SEMANTICS_UNAVAILABLE` because host-owned authorization, CSRF, origin, verifier, and issuer-trust semantics do not exist. ADR 0343 owns one in-process claim and can only produce `CLAIM_REJECTED_SECURITY_SEMANTICS_UNAVAILABLE`. Neither candidate supplies a success path or execution authority.

The static terminal still needs a bounded, neutral way to inspect those local documents without exposing private receipt values, treating self-reported hashes as issuer trust, or implying that a UI projection changes backend authority.

## Decision

Add an unmounted UMD module named `strategy_correlation_matrix_geometry_budget_multi_window_security_lifecycle_neutral_presentation_v1.js` with a colocated pure Node contract test.

The presenter accepts one exact three-key plain-JSON document set:

1. `security_gate_evaluation`
2. `lifecycle_owner_creation`
3. `lifecycle_claim_result`

The input is bounded to depth 16, 4096 values, 128 object keys, 128 array entries, and 4096 characters per string. Cycles, accessors, symbols, custom prototypes, sparse arrays, non-finite numbers, prototype-sensitive keys, and additional top-level documents fail closed.

The source inspection requires the pinned ADR 0342 gate contract and preregistration hashes, the pinned ADR 0343 lifecycle contract and static fingerprint, the gate's `UNKNOWN` and `UNAUTHORIZED` markers, and the sole lifecycle claim-rejection reason. Any true authority-like boolean or explicit authority-promotion marker changes the projection to `UNKNOWN`.

The output is a sealed, bounded model with the exact axis order:

`SOURCE -> GAP -> MATURITY -> PERMISSION`

`SOURCE` contains only locally computed canonical document hashes and verified pinned contract hashes. Raw documents and security receipts are never copied into the output. `GAP` remains open. `MATURITY` is limited to synthetic, unregistered, in-process atomic rejection. `PERMISSION` remains unauthorized, and current admission, paper, live, provider, request-handler, writer, runtime-asset, and DOM-mount authority are all false.

## Consumer-first activation order

1. Keep the presenter unmounted and validate it only with pure synthetic JSON under Node.
2. Obtain an independent review of the bounded projection and its adversarial matrix.
3. Define host-owned authorization, CSRF, origin, verifier, issuer-trust, replay, and idempotency contracts in a separate ADR before any success-capable lifecycle work.
4. Preregister a separately reviewed host integration only after those contracts exist.
5. Mounting or switching any current pointer requires a distinct authorization decision.

## Adversarial matrix

The colocated contract covers pinned-contract drift, missing rejection markers, true authority booleans, explicit promotion markers, extra or missing documents, cycles, accessors, custom prototypes, oversized strings, raw-receipt non-disclosure, deterministic hashing, input immutability, resealed output promotion, and absence of DOM or network operations.

## Consequences

The terminal gains a narrow static inspection boundary without changing `app.js`, `styles.css`, HTTP contracts, backend handlers, runtime assets, or current pointers. The projection is content integrity and local presentation evidence only. It is not issuer trust, external verification, market evidence, performance evidence, or trading permission.
