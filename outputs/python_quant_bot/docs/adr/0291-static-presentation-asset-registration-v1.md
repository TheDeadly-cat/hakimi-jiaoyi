# ADR 0291: Static presentation asset registration v1

## Status

Accepted as a reusable, fail-closed registration kernel and one fixed ADR0290
registration spec. All registered assets remain unbound and unmounted.

## Architecture finding

The latest portfolio-risk presentation registration modules and the source-baseline
consumer registration repeat the same mechanics:

- validate an exact asset manifest;
- pin source, JavaScript, stylesheet, test, and ADR hashes;
- preserve `SOURCE -> GAP -> MATURITY -> PERMISSION`;
- lock app, HTML, route, browser, mount, current, paper, and live authority; and
- verify by exact deterministic rebuild.

Continuing with another consumer-specific registration would add a new copy of
that boundary. Retrofitting old versioned contracts would create compatibility
risk. ADR0291 therefore introduces a shared kernel for new isolated assets while
leaving all existing registrations unchanged.

## Decision

Add `static-presentation-asset-registration-v1` with two public layers:

1. A generic builder and verifier for native-JSON static presentation specs.
2. A fixed wrapper for `portfolio-correlation-admission-rail-v1`.

The generic spec contains exactly five sections: registration identity, source
contract, consumer contract, asset list, and host plan. The builder canonicalizes
asset order and seals the result with strict canonical JSON.

## Validation boundary

The kernel rejects:

- mapping/list subclasses, cycles, non-finite values, and non-string keys;
- absolute paths, backslashes, traversal, runtime/cache/log/database/secrets paths;
- duplicate asset identifiers or paths;
- unknown roles or referenced assets;
- malformed SHA-256 values;
- reordered neutral stages;
- READY labels or raw-source embedding; and
- any non-null host plan field.

The fixed ADR0290 spec pins:

- the ADR0289 Python implementation, test, and ADR;
- strict canonical JavaScript;
- the admission rail JavaScript, isolated stylesheet, Node test, and ADR0290;
- eight CommonJS exports and the browser global;
- exact script load order, eight tiers, and four neutral stages; and
- the protected host stylesheet hash without importing or modifying it.

## Registration state

The output status is `BLOCKED` and the state is
`STATIC_PRESENTATION_ASSETS_REGISTERED_UNBOUND`. The host plan contains only null
values for app importer, HTML script, stylesheet link, route, mount slot, and
browser review receipt.

Activation remains ordered and non-automatic:

1. Source contract pinning.
2. Static asset pinning.
3. Cross-runtime delivery registration.
4. App import preregistration.
5. HTML script and stylesheet preregistration.
6. Unmounted render descriptor review.
7. Browser visual review.
8. Route and mount binding.
9. Current and runtime activation.

No step authorizes the next step.

## Compatibility

No v1-v9 presentation registration, shadow preregistration, source-baseline
registration, host import, HTTP route, CLI, engine, or current artifact is changed.
Legacy modules may migrate to this kernel only through a future versioned decision
with independent equivalence evidence.

## Permission and evidence boundary

Registration proves only that explicit source files and contracts are pinned. It
does not prove browser rendering, visual quality, market quality, profitability,
fresh holdout maturity, forward observation, paper/live authorization, or release
approval. No runtime file, cache, database, log, credential, service, scheduler,
browser, backtest, or trading task is accessed or started.

The public natural-forward chain remains:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 is unchanged and is
not reissued by this work.
