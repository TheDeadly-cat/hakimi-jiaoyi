# ADR 0293: Static presentation in-memory delivery adapter registration v1

## Status

Accepted as an additive dual-runtime adapter asset registration. It remains
host-unbound, execution-unbound, browser-unreviewed, and current-inactive.

## Problem

ADR0292 closes the pure Python-to-JavaScript in-memory handoff, but its Python
adapter, JavaScript adapter, tests, exports, and relative load order are not yet
registered as one immutable consumer boundary.

Directly feeding those assets back through the ADR0291 generic static
presentation registration would preserve its
`CROSS_RUNTIME_DELIVERY_UNREGISTERED` blocker. That would make one document say
both that delivery adapters are registered and that delivery remains
unregistered. Rewriting ADR0291 would also change the registration hash already
bound by ADR0292.

## Decision

Add a composition-only successor that exact-verifies and hash-binds the frozen
ADR0291 registration, then pins only the direct ADR0292 assets:

- Python adapter and corrected Python test fingerprint;
- JavaScript adapter and Node test fingerprint;
- ADR0292 decision fingerprint;
- exact Python exports, JavaScript exports, receipt schema, browser global, and
  relative load order; and
- the protected host stylesheet fingerprint without modifying or loading it.

The predecessor registration remains the single source of truth for the rail,
isolated rail stylesheet, strict-canonical JavaScript dependency, and ADR0289
source contract. ADR0293 does not duplicate those transitive assets.

The resulting status is `BLOCKED` with
`DUAL_RUNTIME_DELIVERY_ADAPTER_ASSETS_REGISTERED_UNBOUND`. It removes only the
closed `CROSS_RUNTIME_DELIVERY_UNREGISTERED` gap. App import, HTML script,
stylesheet link, unmounted descriptor review, browser visual review, route,
mount, runtime, and current activation remain explicit blockers.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Exact ADR0291 predecessor and direct ADR0292 assets | deterministic blocked registration |
| Corrected ADR0292 Python test fingerprint | exact disk match |
| Predecessor registration hash swap after reseal | rejection |
| Direct adapter asset hash swap after reseal | rejection |
| Authority promotion after reseal | rejection |
| Host plan injection after reseal | rejection |
| Extra claim after reseal | rejection |
| Mapping subclass or cyclic document | snapshot rejection |
| Promotional status wording | absent |

## Consumer-first activation order

1. Exact ADR0291 static asset registration.
2. Pin ADR0292 Python and JavaScript adapter assets and tests.
3. Register the dual-runtime delivery adapter boundary through ADR0293.
4. Future app import preregistration.
5. Future HTML script and stylesheet link preregistration.
6. Future unmounted render descriptor review.
7. Future browser visual review.
8. Future route and mount binding.
9. Future current and runtime activation.

No step authorizes or automatically performs the next step.

## Permission and evidence boundary

Transport remains `IN_MEMORY_ARGUMENT_ONLY`; endpoint, route, host slot, payload
source provider, app importer, HTML script, stylesheet link, mount slot, and
browser receipt are null. Registration does not invoke either adapter and does
not load assets, derive markup, access the DOM, execute a browser, or mutate
runtime state.

This work is not market evidence, profitability evidence, forward observation,
browser validation, paper/live authority, release approval, or current
activation. No runtime, cache, database, log, key, service, scheduler, browser,
backtest, or trading task is accessed or started.

The public natural-forward chain remains:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 is unchanged and is
not reissued by this work.
