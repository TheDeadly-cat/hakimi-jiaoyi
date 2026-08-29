# ADR 0192: Unmounted freshness-gate presentation-consumer fixture v3

## Status

Accepted as an isolated, DOM-free, unmounted research presentation fixture. It
is not registered by preregistration-v6, is not mounted, and grants no runtime,
paper, live, HTTP, registry, writer, migration, or `current` authority.

## Context

ADR0190 defines an exact public projection and a strict card renderer. ADR0191
pins both contracts but intentionally records that no presentation consumer has
been registered or executed. Before any DOM or browser review, the projection
and card need a narrow composition boundary that can be tested without browser
state or runtime services.

## Decision

Add `portfolio-risk-freshness-presentation-consumer-fixture-v3` as a pure
JavaScript consumer. It accepts only projection-v3, calls the pinned card-v3
view-model builder and renderer, and returns a deeply frozen render descriptor.

The descriptor contains:

1. fixture schema and fingerprint
2. projection hash plus card schema/fingerprint
3. minimized view-model and escaped HTML markup
4. fixed `SOURCE -> GAP -> MATURITY -> PERMISSION` order
5. explicit mount facts with `requested=false` and `performed=false`
6. summary-only facts and permanently denied authority

The module exports no mount function and uses no `document`, `window`, selector,
DOM mutation, network, storage, service, or browser API. Invalid projections or
authority drift still produce a safe descriptor, but its state is `BLOCK` with
`UNKNOWN` presentation and `UNAUTHORIZED` permission.

## Cross-runtime evidence

Real Python projection-v3 documents are delivered to Node through stdin. The
matrix covers fresh risk increase, stale risk-increase gap, stale risk-reduction
exemption, authority tamper, output minimization, non-mutation, deep freezing,
stage order, and no-readiness wording. This is process-level contract evidence,
not DOM or browser visual evidence.

## Consumer-first activation order

1. Keep this fixture detached and unmounted.
2. Pin its implementation hash in a later immutable preregistration version.
3. Add a separately versioned presentation-consumer registration candidate.
4. Perform isolated DOM review only with explicit authorization.
5. Perform browser visual QA only with explicit authorization.
6. Version HTTP before mounting; keep `current` authorization last.

## Compatibility and evidence boundaries

The natural-forward chain remains
`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`.
Legacy pack-v5 public reads remain `UNKNOWN`; pointer-v2 fields and hash contract
are unchanged and no pointer is reissued. No runtime assets, market tasks,
backtests, services, browsers, schedulers, or trading paths are used.
