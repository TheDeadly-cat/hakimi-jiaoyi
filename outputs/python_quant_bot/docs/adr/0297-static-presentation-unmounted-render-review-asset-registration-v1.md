# ADR 0297: Static presentation unmounted render review asset registration v1

## Status

Accepted as an additive, host-unbound registration of ADR0296 review assets.
Registration does not load or execute any asset.

## Problem

ADR0296 proves clear, high-correlation block, and exact unknown behavior in a
local no-DOM process. Its review module, Node test, Python fixture dependency,
exports, and load order are not yet bound by one immutable registration.

The Node test intentionally starts a Python child process to build synthetic
delivery envelopes. Treating that test bridge as a browser or runtime dependency
would introduce an invalid capability path.

## Decision

Add `static-presentation-unmounted-render-review-asset-registration-v1` and pin:

- exact ADR0295 preregistration, patch-plan, and app-fragment hashes;
- ADR0295 implementation, tests, and decision;
- strict-canonical, rail, delivery, and review JavaScript assets;
- ADR0296 Node test and decision;
- the corrected ADR0292 Python fixture test used only by the Node contract; and
- exact CommonJS exports, browser global, no-DOM rule, neutral stage order, and
  raw-data exclusions.

The production load order is strictly:

`strict canonical -> rail -> delivery -> review`

The Python fixture and Node child-process bridge are `test_only_dependency` and
`TEST_ONLY_CHILD_PROCESS`. They are excluded from production load order and do
not create runtime, browser, host, endpoint, or route capabilities.

Registration status remains `BLOCKED` with
`NO_DOM_RENDER_REVIEW_ASSETS_REGISTERED_UNBOUND`. App importer, HTML script,
host patch, browser review, DOM mount, current, and external independent review
remain explicit blockers.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Exact predecessor and asset bytes | deterministic blocked registration |
| Python fixture added to production order | verifier rejection |
| Review implementation hash swap | verifier rejection |
| Host-plan injection after reseal | verifier rejection |
| External-review authority promotion | verifier rejection |
| Mapping subclass or cyclic document | verifier rejection |
| Extra compatibility claim | verifier rejection |

## Consumer-first activation order

1. Exact ADR0295 host-patch preregistration.
2. Pin ADR0296 review assets and dependencies.
3. Register the local no-DOM review asset boundary through ADR0297.
4. Future external independent review request.
5. Future authenticated independent attestation.
6. Future explicit host-write authorization.
7. Future host patch and rollback binding.
8. Future browser visual review.
9. Future DOM mount and current activation if separately authorized.

No step authorizes or automatically performs the next step.

## Permission and evidence boundary

Registration does not execute the Node test, Python fixture, review module, or
planned app fragment. Host-plan fields are null. Runtime loading, test-fixture
execution, external-review completion, host writes, browser execution, DOM
mount, current activation, paper authorization, live orders, and writer
authority remain false.

This work is not external independent review, browser evidence, visual
validation, market evidence, profitability evidence, release approval,
paper/live authority, or current activation. No runtime, cache, database, log,
key, service, scheduler, browser, backtest, or trading task is accessed or
started.

The public natural-forward chain remains:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 is unchanged and is
not reissued by this work.
