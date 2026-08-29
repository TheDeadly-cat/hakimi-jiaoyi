# ADR 0368: Correlation cluster-ticket policy UI v1

- Status: Accepted as a static neutral policy presentation
- Date: 2026-08-24
- Scope: Existing strategy correlation ledger only

## Context

ADR 0367 adds batch-level cluster ticket counting. The existing terminal already
contains a correlation ledger and an unmounted admission rail v2 visual system.
Adding another large evidence card would duplicate boundaries and make a static
synthetic contract appear more authoritative than it is.

The UI needs a compact explanation of why multiple correlated symbols do not
create multiple independent tickets, while preserving the existing neutral
governance sequence and permanent permission locks.

## Decision

Add a default-open native `details` policy drawer inside the existing strategy
correlation ledger.

The drawer:

- teaches `two symbols in one cluster -> one structural ticket`;
- labels itself `strategy policy explanation, not a live result`;
- preserves `SOURCE -> GAP -> MATURITY -> PERMISSION`;
- states that fresh projected evidence is incomplete;
- states that maturity is preregistration only;
- states that permission is unauthorized;
- states that the rule produces no budget, position, signal, order, or profit
  conclusion.

The signature visual is a ticket-stub diagram: two symbol nodes inside one
dashed cluster boundary collapse into one clipped structural-ticket shape. It
uses the existing rail v2 cartographic palette and type language rather than a
new visual system.

## Isolation

The implementation adds one isolated stylesheet and one Node contract test.
It changes only `index.html` to link the stylesheet and include static semantic
markup.

It does not modify:

- `styles.css`;
- `app.js`;
- `evidence_presentation.js`;
- strict canonical JSON;
- correlation admission rail v2 JS/CSS/tests;
- any backend, route, runtime source, current alias, or pointer.

No script, fetch, storage, service, or runtime loader is added. The policy drawer
does not consume ADR 0367 evidence and must not be described as a rendered live
batch result.

## Accessibility and responsive behavior

- Native `details/summary` preserves keyboard disclosure semantics.
- `summary:focus-visible` has an explicit outline.
- Reduced-motion preferences disable transition and animation behavior.
- The diagram becomes a vertical flow below 720 px.
- Stages become one column below 430 px.

## Contract tests

The Node tests verify:

- the stylesheet is linked once;
- the drawer is nested in the existing correlation ledger;
- stage ordering and unauthorized permission copy;
- absence of `READY` wording;
- static policy and non-live-result copy;
- selector isolation, palette, ticket signature, and keyboard focus;
- responsive and reduced-motion rules;
- unchanged protected production-script load identities;
- absence of scripts inside the policy drawer.

## Consequences

The terminal now explains cluster-level ticket counting in the place users
already inspect correlation evidence. This is a static usability improvement,
not browser-validated runtime behavior, evidence maturity, budget eligibility,
or trading permission.
