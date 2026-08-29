# ADR 0499: Cluster-ticket policy drawer accessibility polish v2

## Status

Accepted as an isolated static presentation refinement. It changes no backend, evidence reader, route, runtime consumer, current selector, pointer, scheduler, protected production script, paper path, or live path.

## Context

ADR0368 introduced a distinctive ticket-stub explanation inside the existing correlation ledger. Static audit found three narrow presentation gaps:

1. Several explanatory labels used 8–10px text, reducing readability in an already dense evidence panel.
2. The diagram carried an `aria-label` on a generic `div` without a semantic role.
3. The clipped ticket and low-contrast sheet treatment had no explicit forced-colors fallback.

No browser session is authorized for this task, so this ADR makes only source- and contract-verifiable claims.

## Design direction

Preserve the existing research-ledger material language, IBM Plex utility typography, Fraunces ticket numeral, tide/rust/marker palette, and clipped structural-ticket signature. Spend no additional decorative complexity.

Improve the design by making the existing explanation easier to read and navigate:

- raise policy microcopy to a 10–12px utility range;
- keep the native `details/summary` disclosure and add stable controls/description relationships;
- expose the cluster-collapse diagram as one named `role=img` concept;
- retain visible keyboard focus and reduced-motion behavior;
- provide a forced-colors mode that removes clipping, shadows, and color-only dependence;
- extend the mobile disclosure marker across all three summary rows.

## Neutral evidence boundary

Copy remains static and preserves `SOURCE -> GAP -> MATURITY -> PERMISSION`, fresh evidence incomplete, preregistration-only maturity, and unauthorized permission.

The drawer remains a strategy policy explanation, not a rendered ADR0367 result. It produces no budget, position, signal, order, profit, readiness, or trading conclusion.

## Isolation

Only `index.html`, `strategy_correlation_cluster_ticket_policy_v1.css`, and its Node contract change. The stylesheet version query is advanced explicitly.

`styles.css`, `app.js`, `evidence_presentation.js`, and `strict_canonical_json_v1.js` remain untouched. No script, fetch, storage, animation dependency, service, or browser workflow is added.

## Claim boundary

Passing static Node contracts proves markup, selector, copy, responsive, reduced-motion, and forced-color source commitments only. It does not prove rendered browser appearance, zoom behavior, assistive-technology behavior, market validity, profitability, or trading authority.
