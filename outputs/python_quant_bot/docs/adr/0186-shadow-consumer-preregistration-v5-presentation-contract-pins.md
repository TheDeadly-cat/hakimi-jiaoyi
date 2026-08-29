# ADR 0186: Shadow consumer preregistration v5 presentation-contract pins

- Status: Accepted as blocked preregistration; evidence and UI not bound
- Date: 2026-08-22
- Scope: Static predecessor verification and implementation pins only

## Context

ADR0182 preregistration v4 exact-verifies preregistration v3 and pins the
readiness-v3 chain. It predates ADR0184 portfolio-risk adapter v2 and ADR0185
public projection v2 plus temporal-lattice card.

The v4 document is internally closed and intentionally blocked, but it cannot
detect drift in the new adapter, projection, JavaScript, or stylesheet. Mounting
the new card under v4 would therefore bypass the declared consumer-first order.

## Decision

Add preregistration v5 that fully reverifies immutable v4 and pins:

1. Shadow preregistration v4.
2. Portfolio-risk adapter v2.
3. Portfolio-risk public projection v2.
4. Temporal-lattice card v2 JavaScript.
5. Temporal-lattice card v2 stylesheet.

The v5 API accepts only the v4 document, its exact verification context, and the
implementation manifest. It accepts no adapter, projection, DOM, browser,
runtime, or trading evidence instance.

## Preserved accounting

The 14 required shadow input schemas and three closed local blockers are copied
byte-for-byte from v4. Both prior capability pins are preserved. V5 adds one
presentation capability with:

- contract_pinned=true
- evidence_bound=false
- consumer_executed=false
- external_authority_verified=false

The preregistration status remains BLOCKED.

## Added blockers

- Adapter-v2 evidence is not bound or exactly verified.
- Projection-v2 evidence is not bound or exactly verified.
- The presentation consumer is not registered.
- The temporal-lattice DOM contract is not reviewed.
- Browser visual review is not performed.
- The presentation HTTP contract is not versioned.

Existing provider, issuance, external registry, trusted-clock, readiness,
runtime, risk-service, independent-review, current-switch, paper, and live
blockers remain in force.

## Activation order

Readiness-v3 and durable trusted-clock prerequisites remain before any isolated
application consumer. Exact adapter-v2 evidence must precede projection-v2
evidence. An unregistered presentation fixture and explicitly authorized
isolated DOM/browser review precede any HTTP mount. A separately authorized
current switch remains last.

## Compatibility and authority

Preregistration v4, adapter v2, projection v2, and the temporal-lattice card are
unchanged. V5 is additive, detached, and not current. It does not register a
server route, HTTP contract, static script, DOM mount, runtime gate, paper task,
or live task.

The natural-forward chain remains audit-v2/readiness-v3 ->
maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2.
Legacy pack-v5 remains publicly UNKNOWN. Pointer-v2 fields, hash contract, and
non-reissuance behavior remain unchanged.

## Validation boundary

Validation is limited to synthetic predecessor contracts, exact manifest and
tamper tests, explicit public-consumer isolation, and in-memory compilation.
No runtime, database, cache, log, secret, network, service, browser, scheduler,
return backtest, formal blind test, paper task, or live task is used. Passing
these checks does not prove profitability or grant trading authority.
