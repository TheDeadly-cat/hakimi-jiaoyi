# ADR 0217: Projection-v5 static card and consumer-v5

## Status

Accepted as unmounted static frontend candidates. No DOM, browser, route, registration activation, or mount is authorized.

## Context

Card-v4 and consumer-v4 are immutably bound to projection-v4. A real, exactly verified projection-v5 has a valid strict-canonical seal, but card-v4 correctly produces an `UNKNOWN` view model and consumer-v4 correctly produces a blocked unknown descriptor because their input schema remains projection-v4.

The Node gap proof passed `6/6` assertions and established an important distinction: cryptographic seal integrity is not schema compatibility. The old card seal primitive accepts the valid seal, while its schema-aware view model still fails closed.

## Decision

Add a separate static card-v5, scoped stylesheet, and consumer-fixture-v5.

Card-v5:

1. combines strict-canonical seal verification with exact projection-v5 schema and fingerprint checks;
2. validates the neutral four-stage order and locked authority contract;
3. preserves local joint-gate `PASS/BLOCK` as descriptive evidence only;
4. renders escaped static HTML with no DOM target, selector, event handler, or mount API;
5. uses a scoped sandstone, ink, blue-gray, and amber visual language without green readiness cues;
6. includes responsive and reduced-motion rules in a separate stylesheet.

Consumer-v5:

1. accepts only card-v5-compatible projection-v5 evidence;
2. returns a strict-canonical sealed and deeply frozen descriptor;
3. declares the stylesheet asset without reading or mounting it;
4. keeps status `BLOCK`, mode `UNMOUNTED`, and all authority false;
5. verifies descriptors only by exact deterministic rebuild.

A Python-to-Node cross-runtime contract covers valid local pass, valid local block, and resealed wrong-schema cases without temporary files.

## Consumer-first order

1. Keep card-v5 and consumer-v5 unmounted.
2. Complete Node, cross-runtime, descriptor, and load-order review.
3. Add a versioned registration successor only after all artifact hashes are fixed.
4. Separately authorize isolated DOM review.
5. Separately authorize browser visual review.
6. Separately authorize route, registration activation, mount, and `current`.

## Consequences

- card-v4/consumer-v4 remain immutable.
- projection-v5 gains a static frontend representation without becoming a mounted UI.
- Local gate pass uses neutral blue-gray, while gaps use amber; neither color or label implies readiness or permission.
- The existing application stylesheet remains untouched.

## Non-goals

- No DOM insertion, selector, event binding, browser, or visual validation claim.
- No HTTP route, service, runtime, cache, database, provider, or scheduler access.
- No return backtest or profitability claim.
- No registration activation, mount, `current` switch, pack publication, pointer reissue, paper, or live authority.
