# ADR0286: Source-Baseline Provider-Conformance Application Load Descriptor v1

## Status

Accepted as a host-pinned, unapplied application-load preregistration.

## Context

ADR0285 registers the card, canonical dependency, style contract, and isolated
stylesheet. Current `index.html` still loads only the protected stylesheet and
existing scripts ending with `evidence_presentation.js` and `app.js`. The new
assets are absent from HTML, application, server, route, browser, and mount
bindings.

The research view already contains `researchDataQualityCards`. It is a suitable
host anchor, but a dedicated source-baseline card slot does not exist. There is
also no payload delivery adapter or endpoint for ADR0281 payload candidates.

## Decision

Add a service-layer descriptor that pins the current `index.html`, `app.js`,
protected stylesheet, and ADR0285 registration hashes without reading or
modifying them at runtime.

Preregister only a relative asset subset:

- load the isolated stylesheet after the protected stylesheet;
- load strict-canonical JavaScript before the card;
- load the card after canonical and before the existing app host;
- preserve every unlisted existing asset;
- do not load the style-preregistration module at runtime.

Preregister `researchDataQualityCards` as an observed anchor and
`sourceBaselineProviderConformanceCardHost` as a future, currently absent slot.
The existing research view is reused and no new route is planned.

The mount contract leaves payload delivery adapter and endpoint null. HTML asset
tags, host slot, app binding, and payload/render binding are explicit planned
mutations with `performed: false`.

Add a hash-only descriptor binding candidate that exact-verifies this descriptor
and the complete ADR0285 style binding. Valid output remains `BLOCKED` with
`LOAD_DESCRIPTOR_AND_STYLE_BINDING_HASH_BOUND_HOST_UNMODIFIED`. Invalid,
drifting, promoted, cyclic, or exception-raising input returns `UNKNOWN`.

Inputs are snapshotted once before verification and hash projection. No raw
payload, host document, source document, or identity material is embedded.

## Consumer-first activation order

1. Keep ADR0281 through ADR0285 frozen.
2. Pin current host assets and future relative order through ADR0286.
3. Design a payload-delivery adapter contract without adding an endpoint.
4. Preregister HTML/app patch operations and rollback evidence separately.
5. Apply host changes only after explicit authorization.
6. Execute browser rendering and visual review only after host changes are
   independently verified and explicitly authorized.

No step automatically promotes the next one.

## Non-claims

An application-load descriptor is not an application modification. This version
does not write HTML, JavaScript, or CSS; load assets; create a host slot; bind a
payload; register an endpoint or route; execute a browser; mount UI; visually
review the card; call a provider; mutate runtime state; activate current
evidence; authorize paper or live activity; prove market validity; demonstrate
strategy performance; or prove profitability.

The public natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`
