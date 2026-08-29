# ADR 0294: Static presentation application load descriptor preregistration v1

## Status

Accepted as a host-pinned, unapplied application load-graph preregistration. It
does not modify HTML, JavaScript, CSS, routes, or runtime state.

## Problem

ADR0293 registers the Python and JavaScript in-memory delivery adapters, but the
application still has no versioned description of where their assets belong in
the existing research view. The current host has a `researchDataQualityCards`
anchor, while the proposed rail slot, browser globals, script tags, stylesheet
link, and app binding are absent.

The older source-baseline descriptor treats an unregistered payload adapter and
a missing endpoint as blockers. Those assumptions are wrong for this chain:
ADR0293 already registers the adapter, and ADR0292 deliberately uses
`IN_MEMORY_ARGUMENT_ONLY` with no endpoint or route.

## Decision

Add a descriptor that exact-verifies ADR0293 and pins the unchanged host
`index.html`, `app.js`, and protected stylesheet. It preregisters only this
relative asset subset while preserving every unlisted host asset:

- protected stylesheet before the isolated admission-rail stylesheet;
- strict-canonical JavaScript before the admission rail;
- admission rail before the in-memory delivery adapter; and
- delivery adapter before the existing application host.

Preregister `researchDataQualityCards` as an anchor observed in the pinned
source and `portfolioCorrelationAdmissionRailHost` as a future slot absent from
that source. The planned app flow verifies the envelope, extracts the exact
admission candidate, builds the no-DOM receipt, then renders the neutral rail.
Every operation remains descriptive and unperformed.

Endpoint and route absence are intentional facts, not blockers. The existing
research view is reused and no new route is required.

Add a hash-only binding candidate that exact-verifies both ADR0294 and ADR0293.
Valid output remains `BLOCKED` and carries only descriptor, registration,
relative-load-order, and host hashes. Invalid, promoted, cyclic, or non-native
input returns `UNKNOWN` or fails exact verification.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Exact ADR0293 and ADR0294 documents | blocked hash-only binding |
| Current host and asset bytes | exact pinned hashes |
| Relative load-order asset swap after reseal | rejection |
| Descriptor authority promotion after reseal | rejection |
| Binding mount promotion after reseal | rejection |
| Adapter registration promotion | UNKNOWN binding |
| Mapping subclass or cyclic input | UNKNOWN or verifier rejection |
| Endpoint-absence compatibility fallback | not present |
| Promotional wording | absent |

## Consumer-first activation order

1. Exact ADR0293 delivery adapter registration.
2. Pin current host fingerprints.
3. Preregister the relative load graph through ADR0294.
4. Future HTML asset-tag preregistration.
5. Future app in-memory binding preregistration.
6. Future host-slot preregistration.
7. Future unmounted render-descriptor review.
8. Future browser visual review.
9. Future route and mount binding if separately authorized.
10. Future current and runtime activation if separately authorized.

No step authorizes or automatically performs the next step.

## Permission and evidence boundary

All four planned host mutations have `performed: false`. Browser execution,
visual review, DOM mount, runtime loading, payload delivery, current activation,
paper authorization, live orders, and writer authority remain false.

This work is not browser evidence, market evidence, profitability evidence,
forward observation, release approval, paper/live authority, or current
activation. No runtime, cache, database, log, key, service, scheduler, browser,
backtest, or trading task is accessed or started.

The public natural-forward chain remains:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 is unchanged and is
not reissued by this work.
