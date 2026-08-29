# ADR 0223: Descriptor and load-order static review candidate-v1

## Status

Accepted for unmounted static-source review only.

## Context

Registration-v5 correctly records that render-descriptor review, dependency
load-order review, DOM review, browser review, and UI mounting are absent.

Card-v5 and consumer-v5 already provide a neutral, unmounted render descriptor
and a scoped stylesheet. A separate source-level review is needed before any
browser or mount discussion. That review must not infer runtime loading or
visual correctness from static source.

## Decision

Introduce a read-free Node review candidate accepting:

1. A projection-v5 document.
2. The observed consumer-v5 descriptor.
3. The card-v5 stylesheet text.
4. An exact six-item static asset manifest.
5. An observed five-module JavaScript dependency order.
6. An observed one-item stylesheet order.

The JavaScript order is:

1. strict canonical JSON v1.
2. joint-evidence card-v5.
3. joint-evidence consumer-v5.
4. consumer execution receipt-v3.
5. execution witness signature candidate-v1.

The review exactly rebuilds the descriptor through consumer-v5. It requires
the neutral SOURCE, GAP, MATURITY, PERMISSION stage order, an unauthorized
permission stage, an unmounted descriptor, and locked authority.

The markup review rejects script, iframe, object, embed, style, inline event,
and JavaScript URL surfaces. The stylesheet review requires:

1. Exact card-v5 CSS SHA-256.
2. A card-v5 root scope.
3. The mobile responsive contract.
4. The reduced-motion contract.
5. No global html or body selector.
6. No purple bias or promotion wording.

## Claim calibration

A review PASS means the supplied descriptor, CSS text, manifest, and declared
load order satisfy this exact static contract.

A review PASS does not prove:

1. The JavaScript files were loaded in a browser.
2. The supplied implementation hashes were recomputed from runtime files.
3. CSS was executed.
4. A DOM was accessed.
5. The page was visually reviewed.
6. A route exists or UI was mounted.
7. Any current, writer, paper, or live authority exists.

The production review module reads no file. Tests supply the stylesheet text
from its explicit source path. The output embeds no stylesheet, descriptor,
manifest, projection, or markup.

## Adversarial matrix

1. Valid descriptor, CSS, manifest, and order must pass static review.
2. A local joint-gate BLOCK remains a valid static review.
3. Swapped or duplicate JavaScript dependencies must block.
4. Missing, extra, or substituted manifest values must block.
5. Altered CSS must fail the exact content hash.
6. Global CSS leakage must block independently.
7. Missing responsive or reduced-motion contracts must block.
8. A resealed mount promotion must fail descriptor rebuild.
9. A resealed markup injection must fail descriptor rebuild.
10. A resealed projection-v4 alias must block.
11. A resealed review authority promotion must fail exact verification.
12. Browser, DOM, mount, profitability, and trading claims remain false.

All cases are synthetic or source-only. No runtime store, database, cache,
log, secret, service, browser, scheduler, market task, or trading path is
used.

## Activation order

1. registration-v5 static candidate.
2. witness signature candidate.
3. descriptor and dependency load-order static review.
4. future browser review under explicit authorization.
5. future separate production route or mount decision.

This ADR authorizes only step 3.
