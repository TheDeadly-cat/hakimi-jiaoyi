# ADR0288: Source-Baseline In-Memory Delivery Adapter Registration v1

## Status

Accepted as a dual-runtime, execution-unbound adapter registration.

## Context

ADR0287 adds exact Python and JavaScript in-memory delivery adapters plus tests.
They share an envelope schema and static fingerprint without pinning each other,
which avoids a bidirectional hash cycle. The assets remain absent from host,
payload-source, endpoint, route, browser, and mount bindings.

Before any payload source can be designed, both implementations and their
dependencies need one immutable registration boundary.

## Decision

Add a service-layer registration that pins:

- ADR0286 load-descriptor implementation and deterministic document hash;
- ADR0287 envelope schema, static fingerprint, Python implementation and test;
- ADR0287 JavaScript implementation and test;
- ADR0287 document;
- strict-canonical and neutral-card JavaScript dependencies;
- exact Python function names, JavaScript exports, receipt schema, browser
  global, and relative JavaScript load order.

Payload source provider, endpoint, app importer, HTML script tag, and host slot
remain null. Registration does not invoke either adapter or claim cross-runtime
execution as runtime authority.

Add a hash-only binding candidate that exact-verifies the registration and the
complete ADR0287 envelope source chain. Valid output remains `BLOCKED` with
`REGISTERED_ADAPTERS_AND_EXACT_ENVELOPE_HASH_BOUND_EXECUTION_UNAUTHORIZED`.
Invalid, drifting, promoted, cyclic, or exception-raising input returns
`UNKNOWN`.

The binding records registration, envelope, descriptor-binding, payload, and
adapter implementation hashes only. It embeds no envelope, payload, source
document, or identity material. Inputs are snapshotted once before verification
and hash projection.

## Consumer-first activation order

1. Keep ADR0281 through ADR0287 frozen.
2. Register both adapter implementations through ADR0288.
3. Design a payload-source provider contract that remains in memory and
   request-scoped.
4. Preregister host asset loading and adapter invocation separately.
5. Add endpoints, routes, host writes, browser execution, and visual review only
   after explicit authorization and independent evidence.

No step automatically promotes the next one.

## Non-claims

Adapter registration is not adapter invocation, payload sourcing, network
delivery, endpoint availability, host loading, card rendering, DOM access,
browser execution, mount, or visual evidence. This version does not mutate
runtime state, call a provider, activate current evidence, authorize paper or
live activity, prove market validity, demonstrate strategy performance, or
prove profitability.

The public natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`
