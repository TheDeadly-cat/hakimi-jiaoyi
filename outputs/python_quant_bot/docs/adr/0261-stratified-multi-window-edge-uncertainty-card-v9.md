# ADR 0261: Unmounted stratified multi-window edge-uncertainty card-v9

## Status

Accepted as an isolated, unmounted research-only frontend candidate on
2026-08-23.

## Context

ADR0260 froze an unregistered HTTP candidate-v9 that exposes bounded stratified
portfolio-risk, multi-window stability, and preregistered cross-cluster edge
uncertainty aggregates. Card-v8 is intentionally strict and accepts only the
candidate-v8 response.

A pure synthetic Node proof passed 5/5:

1. a synthetic candidate-v9 response was sealed;
2. card-v8 rejected the v9 response;
3. card-v8 fell closed to its UNKNOWN view;
4. card-v8 exposed no metrics or dimensions;
5. no card-v9 presenter, stylesheet, or fixture asset existed.

Widening card-v8 would weaken a frozen schema boundary. Mounting before a strict
verifier, view model, escaped renderer, scoped stylesheet, and descriptor
contract exist would reverse consumer-first activation.

## Decision

Add five isolated assets:

- a strict candidate-v9 response verifier and pure edge-aware renderer;
- a fully scoped card-v9 stylesheet;
- a sealed descriptor-only consumer fixture;
- a 12-case Node adversarial contract;
- this ADR.

No asset imports `app.js`, queries the DOM, exposes a mount function, registers a
route, accesses runtime state, or modifies `styles.css`. The fixture fixes mount
mode to UNMOUNTED, DOM target and selector to null, browser execution to false,
and all paper/live or activation authority to false.

## View contract

The verifier requires exact sealed response-v9, payload-v9, lineage, authority,
facts, local decision, risk, multi-window, edge uncertainty, source, stage, and
blocker key sets. Risk aggregates remain canonical strings. Correlation values
must be safe integer micros in valid ranges. The edge partition hash must match
the bounded source lineage.

UNKNOWN or malformed sources yield a frozen UNKNOWN view with null edge and
window summaries and no metrics, signals, dimensions, or source hashes. A known
view exposes only aggregate pair counts, confidence upper and preregistered floor,
registered-window coverage, bounded risk dimensions, and the fixed
`SOURCE -> GAP -> MATURITY -> PERMISSION` sequence. Pair rows, matrices,
positions, source documents, and verification contexts never enter the model.

Every source-derived string is escaped before markup generation. A resealed
permission promotion, float micros, out-of-range correlation, extra edge field,
or forged outer PASS is rejected.

## Visual direction

The scoped card uses a research-ledger surface with a cluster-bridge rail,
concentric evidence marks, Cormorant display typography, technical mono labels,
blue-grey for bounded research evidence, copper for GAP/BLOCK, and slate for
UNKNOWN. No green permission cue is used. The prominent status remains one of:

- `LOCAL CLEAR / OUTER BLOCK`;
- `LOCAL BLOCK / OUTER BLOCK`;
- `SOURCE UNKNOWN / OUTER BLOCK`.

Desktop, tablet, and mobile layouts are defined. Motion is limited to entry and
staggered evidence reveals and is disabled under `prefers-reduced-motion`. This
ADR records static source and Node evidence only; no browser visual review was
performed.

## Activation order

1. Freeze and adversarially test these unmounted assets.
2. Perform browser review only if separately authorized.
3. Propose an isolated mount point as a separate versioned decision.
4. Propose route registration separately.
5. Consider current admission only after independent runtime evidence.

No later step is authorized by this ADR.

## Compatibility and authority

- candidate-v9 implementation pin:
  `329aa276701063ba6625a7cedac495c82bd9b264dfd273043067ce1f6065d394`;
- presentation-v9 implementation pin:
  `5fb7af67366913016c79236419f9b8df356a6b809ec876e0c312a67a4839b132`;
- strict canonical implementation pin:
  `cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412`;
- card-v8 remains unchanged and rejects v9;
- `styles.css`, `app.js`, HTML, routes, and current selectors remain unchanged;
- natural-forward artifact versions and pointer-v2 remain unchanged;
- no research result is profitability evidence or trading authorization.

## Consequences

The project now has an edge-aware, responsive, accessible, fail-closed card
candidate that can be reviewed without creating a hidden mount or authority
path. Its visual polish is isolated evidence, not a browser review or activation
claim.
