# ADR 0256: Unmounted stratified multi-window evidence card-v8

## Status

Accepted as an isolated, unmounted research-only frontend candidate on
2026-08-23.

## Context

ADR0255 froze an unregistered HTTP candidate-v8 that projects bounded anchor and
multi-window correlation-cluster evidence. The existing card-v7 is intentionally
strict and accepts only the predecessor candidate-v7 response.

A pure synthetic cross-runtime proof passed 5/5:

1. Python produced a known candidate-v8 response;
2. card-v7 rejected the v8 response;
3. card-v7 fell closed to its UNKNOWN view;
4. card-v7 exposed no v8 metrics or dimensions;
5. no card-v8 renderer or fixture asset existed.

Widening card-v7 would weaken its frozen schema boundary. Mounting a new card
before its verifier, view model, renderer, and descriptor were independently
testable would reverse the consumer-first activation order.

## Decision

Add four isolated static assets:

- a strict candidate-v8 response verifier and pure card-v8 renderer;
- a fully scoped card-v8 stylesheet;
- a sealed descriptor-only consumer fixture;
- a Node adversarial contract.

No asset imports `app.js`, queries the DOM, exposes a mount function, registers a
route, or accesses runtime state. The fixture fixes mount mode to UNMOUNTED, DOM
target and selector to null, browser execution to false, and every paper/live or
activation authority to false.

## View contract

The verifier requires the exact sealed response-v8, payload-v8, lineage,
authority, facts, local decision, risk summary, multi-window summary, source,
stage, and blocker key sets. Numeric aggregates must remain canonical strings;
resealed floats are rejected. Unknown or malformed sources yield a frozen UNKNOWN
view with no metrics, signals, dimensions, or source hashes.

A known view exposes only:

- verified versus preregistered window coverage;
- anchor-window identifier;
- effective-strata floor and worst maximum stratum gross;
- cluster-partition and strata-topology stability flags;
- the bounded anchor risk summary and dimension rows;
- the fixed `SOURCE -> GAP -> MATURITY -> PERMISSION` sequence.

HTML is generated only after strict verification, and every source-derived string
is escaped. No source documents, window documents, positions, correlation
matrices, or verification contexts enter the view model.

## Visual direction

The scoped CSS uses a warm research-ledger surface, measured grid lines,
Fraunces display typography, IBM Plex technical labels, teal for bounded local
evidence, rust for gaps and blocks, and slate for UNKNOWN. It does not use green
permission cues. The prominent status always says either
`LOCAL CLEAR / OUTER BLOCK`, `LOCAL BLOCK / OUTER BLOCK`, or
`SOURCE UNKNOWN / OUTER BLOCK`.

The layout has desktop, tablet, and mobile breakpoints. Entry and metric reveals
are modest and disabled under `prefers-reduced-motion`. This ADR records static
source design only; no browser visual review was performed.

## Activation order

1. Freeze and adversarially test these unmounted assets.
2. Perform explicit browser review only if separately authorized.
3. Propose an isolated mount point as a separate versioned decision.
4. Propose route registration separately.
5. Consider current admission only after independent runtime evidence.

No later step is authorized by this ADR.

## Compatibility and authority

- candidate-v8 implementation pin:
  `70e2cabb54d0a9bf51973756fbe40173b142745d3a3f9d0f6f816ca759eb2770`
- presentation-v8 implementation pin:
  `f2720ff7b2b32e7ffdf4c83502b1fa65f83ceb3ee8806dae94b0aaf71fd8ba6b`
- strict canonical implementation pin:
  `cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412`
- card-v7 remains unchanged and rejects v8;
- `styles.css`, `app.js`, HTML, server routes, and current selectors remain
  unchanged;
- natural-forward artifact versions and pointer-v2 remain unchanged;
- no research result is profitability evidence or trading authorization.

## Consequences

The project now has a visually distinct, responsive, accessible, fail-closed
multi-window card candidate that can be reviewed without creating a hidden mount
or authority path. The additional versioned assets are intentional isolation,
not duplicate current behavior.
