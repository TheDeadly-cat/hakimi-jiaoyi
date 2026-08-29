# ADR0285: Source-Baseline Provider-Conformance Consumer Registration v2

## Status

Accepted as a style-aware, hash-bound, unmounted consumer registration.

## Context

ADR0283 registers the neutral card and canonical JavaScript but deliberately
leaves stylesheet, app importer, and HTML template null. ADR0284 preregisters a
source-specific visual contract and adds an isolated stylesheet. Both remain
absent from application, server, route, browser, and mount bindings.

Rewriting ADR0283 would erase the asset-free predecessor boundary. Registering
the stylesheet through a new v2 document preserves the consumer-first sequence
and leaves all runtime permissions fail closed.

## Decision

Add registration v2 that pins:

- ADR0283 schema, binding schema, static fingerprint, implementation SHA-256,
  and deterministic registration hash;
- ADR0284 style schema, static fingerprint, implementation SHA-256, and sealed
  preregistration hash;
- the isolated stylesheet SHA-256, style-contract test SHA-256, and ADR SHA-256;
- the existing card and strict-canonical JavaScript hashes;
- the style namespace, cold-audit-film direction, four-stage calibration spine,
  six-color palette, three typography roles, breakpoints, mounted-only motion,
  and reduced-motion requirement.

The v2 manifest registers the isolated stylesheet as an asset. It still leaves
`app.js` importer and HTML template null. The protected stylesheet is neither
imported, modified, nor authorized for reuse.

Add a style-aware hash-only binding candidate. It exact-verifies registration v2
and the full ADR0283 predecessor binding before recording registration, binding,
payload, source-envelope, card, style-contract, and stylesheet hashes. It embeds
no raw payload, style document, source document, or identity material.

Valid output remains `BLOCKED` with
`PAYLOAD_CARD_AND_ISOLATED_STYLESHEET_HASH_BOUND_UNMOUNTED`. Invalid, drifting,
promoted, cyclic, or exception-raising input returns `UNKNOWN`. Inputs are
snapshotted once before verification and hash projection.

## Consumer-first activation order

1. Keep ADR0281 through ADR0284 frozen.
2. Register exact card and style assets through ADR0285.
3. Preregister an application load descriptor without editing `app.js` or HTML.
4. Add route and mount candidates only under separate versioned contracts.
5. Execute browser rendering and visual review only after explicit authorization.

No step automatically promotes the next one.

## Non-claims

Asset registration is not runtime stylesheet loading or visual evidence. This
version does not edit the protected stylesheet, import app or HTML assets,
register a route, mount UI, execute a browser, visually review the candidate,
call a provider, mutate runtime state, activate current evidence, authorize
paper or live activity, prove market validity, demonstrate strategy performance,
or prove profitability.

The public natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`
