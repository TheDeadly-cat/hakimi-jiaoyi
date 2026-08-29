# ADR 0295: Static presentation host patch preregistration v1

## Status

Accepted as an exact, reversible, and unapplied host-patch plan with pure
in-memory roundtrip evidence. No host file is written.

## Problem

ADR0294 pins the relative load graph and future host slot, but it does not define
the exact HTML and application edits. Applying hand-written changes later would
leave anchor collisions, line-ending drift, post-image integrity, and rollback
behavior unspecified.

The next boundary must prove that an exact patch can be derived and reversed
without treating a preview as write authorization or browser evidence.

## Decision

Preregister four ordered operations against exact host pre-image hashes:

1. Insert the isolated rail stylesheet after the protected stylesheet.
2. Insert an empty rail host slot after `researchDataQualityCards`.
3. Insert strict-canonical, rail, and delivery scripts before existing `app.js`.
4. Append an unmounted render-candidate builder to `app.js`.

Each operation pins target path, operation type, unique anchor, anchor hash,
required anchor count, exact fragment, fragment hash, fragment length, and
`performed: false`. The plan also pins exact post-image hashes.

The app fragment has no DOM lookup, `innerHTML`, network request, automatic
invocation, or mount. If later applied and explicitly called, it only verifies
the in-memory envelope and receipt, extracts the exact candidate, and returns
neutral markup as `EXACT_UNMOUNTED_MARKUP_CANDIDATE`. DOM mount remains a
separate future authorization boundary.

Add a pure in-memory roundtrip builder. It:

- exact-verifies ADR0295 and ADR0294;
- verifies UTF-8 host pre-image hashes;
- enforces unique anchors and absent fragments;
- applies all four operations to transient strings;
- verifies pinned post-image hashes;
- reverses operations in exact reverse order; and
- verifies recovered hashes equal the original pre-images.

The sealed evidence contains hashes only. It embeds no original or patched host
source. Any drift, collision, promotion, non-native document, or recovery
failure returns `UNKNOWN` or fails exact verification.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Exact host sources and documents | blocked hash-only roundtrip evidence |
| Host pre-image drift | UNKNOWN |
| Missing or duplicate anchor | fail closed before any evidence claim |
| Fragment already present | fail closed |
| Fragment or post-image swap after reseal | verifier rejection |
| Writer or mount authority promotion | verifier rejection |
| Tampered ADR0294 descriptor | UNKNOWN |
| Mapping subclass or cyclic document | UNKNOWN |
| Roundtrip receipt promotion | verifier rejection |

## Consumer-first activation order

1. Exact ADR0294 load descriptor.
2. Pin host pre-images, patch fragments, post-images, and rollback order.
3. Produce exact in-memory apply-and-rollback evidence.
4. Independent patch review.
5. Future explicit host-write authorization.
6. Future patch application with rollback executor bound.
7. Future unmounted render review.
8. Future browser visual review.
9. Future DOM mount and current activation if separately authorized.

No step authorizes or automatically performs the next step.

## Permission and evidence boundary

Patch executor, rollback executor, writer, approval receipt, browser receipt, and
mount receipt are null. Patch application, rollback application, host writes,
app-fragment execution, browser execution, DOM mount, runtime loading, current
activation, paper authorization, and live orders remain false.

This work is not a host patch, browser evidence, visual validation, market
evidence, profitability evidence, release approval, paper/live authority, or
current activation. No runtime, cache, database, log, key, service, scheduler,
browser, backtest, or trading task is accessed or started.

The public natural-forward chain remains:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 is unchanged and is
not reissued by this work.
