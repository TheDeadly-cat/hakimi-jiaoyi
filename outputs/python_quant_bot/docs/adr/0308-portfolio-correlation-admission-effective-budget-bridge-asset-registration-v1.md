# ADR 0308: Admission-budget bridge asset registration v1

## Status

Accepted as a static, unbound, research-only asset registration.

## Context

ADR 0305 defines the shared-source admission-budget binding. ADR 0306 defines
its Python-to-JavaScript in-memory delivery. ADR 0307 defines the isolated
structural bridge presentation. Their files and tests are exact, but a future
host review still needs one versioned manifest that pins the whole consumer
chain before discussing script tags, stylesheets, slots, routes, browser
evidence, or mounting.

The repository already has a generic static-presentation asset-registration
builder and verifier. Reimplementing registration normalization, path safety,
asset uniqueness, canonical sealing, host locks, or authority locks would
create a duplicate boundary.

## Decision

Add only a fixed expected-spec wrapper around the existing generic
static-presentation asset registration v1.

The source contract pins ADR 0305:

- binding implementation;
- binding contract test;
- ADR 0305.

The ten-asset manifest pins:

- strict-canonical JavaScript;
- ADR 0306 Python producer and Python contract;
- ADR 0306 JavaScript adapter and Node contract;
- ADR 0306;
- ADR 0307 bridge JavaScript, stylesheet, and Node contract;
- ADR 0307.

The consumer contract pins:

- bridge schema and static fingerprint;
- browser global;
- CommonJS exports;
- strict-canonical to delivery to bridge load order;
- SOURCE, GAP, MATURITY, PERMISSION order;
- the seven ADR 0305 tiers;
- LOCAL ALIGNMENT, LOCAL BLOCK, and SOURCE UNKNOWN neutral labels;
- READY disallowed;
- raw source evidence absent;
- protected host stylesheet path and hash.

## Registration state

The generic registration output remains:

- status BLOCKED;
- registration state STATIC_PRESENTATION_ASSETS_REGISTERED_UNBOUND;
- host plan entirely null;
- runtime authority entirely false.

The manifest proves exact static registration only. It does not prove that a
delivery provider, importer, script tag, stylesheet link, render descriptor,
browser review, route, mount slot, or current consumer exists.

## Adversarial contract

The wrapper rejects:

- valid generic registrations built from a different asset hash;
- valid generic registrations built from a different script load order;
- a READY success label;
- resealed host-slot promotion;
- resealed UI-mount authority promotion;
- non-native containers and cycles;
- any mismatch between pinned paths and current source hashes.

## Non-goals

- No change to the generic registration implementation.
- No host importer, script, stylesheet link, slot, route, or endpoint.
- No delivery-provider registration.
- No DOM mount, render call, browser launch, or visual-runtime claim.
- No scheduler, writer, current, paper, live, or order path.
- No backtest, blind test, or profitability claim.
- No change to the natural-forward evidence chain.
- No pack-v5 compatibility promotion.
- No pointer-v2 field, hash, or publication change.

## Next boundary

A future host preregistration must consume this exact registration hash and
still keep all host fields unbound until a separate authorized review. This
asset registration cannot activate or mount the bridge.
