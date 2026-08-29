# ADR 0251: Stratified budget HTTP candidate and unmounted card-v7

## Status

Accepted as an unregistered, unmounted, research-only candidate on 2026-08-23.

## Context

ADR 0249 added preregistered-strata effective-bet budget-v3. ADR 0250 joined that
budget with the existing portfolio-risk presentation-v6 in an exact, neutral
presentation-v7 document. Read-only source inspection found no presentation-v7
binding in the HTTP interface, application layer, server, `static/app.js`, or
`static/index.html`. The existing v4 through v6 cards therefore cannot show the
new active-strata budget, and consuming an older card alone can hide a budget-v3
block behind a locally clear predecessor component.

The presentation-v7 and budget-v3 implementation hashes were rechecked before
this change. `static/styles.css` also retained its frozen hash. No runtime,
database, cache, log, environment, browser, scheduler, or market asset was read.

## Decision

Add a narrow consumer-first chain:

1. `strategy_correlation_cluster_portfolio_risk_stratified_presentation_candidate_v7.py`
   accepts an exact-key request and exact-key verification context.
2. It delegates source authenticity to presentation-v7's public exact-rebuild
   verifier and requires its complete fail-closed receipt.
3. An exact but unknown presentation returns a sealed response with
   `state=UNKNOWN` and `payload=null`. Partial metrics are not projected.
4. A known source receives a separately sealed, bounded payload containing only
   local decisions, active-strata summaries, four neutral stages, gaps, and
   locked authority. Source documents, contexts, positions, and matrices are not
   embedded.
5. Verified floating-point metrics are converted to non-negative decimal text
   before sealing. This avoids incompatibility with browser strict-canonical-v1,
   which intentionally accepts integers but not JSON floats.
6. `evidence_portfolio_risk_stratified_budget_card_v7.js` independently verifies
   outer and payload seals, exact keys, lineage pins, stage order, source state,
   and all authority locks before creating a view model.
7. The dedicated stylesheet is namespaced to `.hakimi-strata-card-v7`. The
   frozen shared `styles.css` is not modified.
8. The consumer fixture emits static markup and a sealed descriptor, but exposes
   no mount API and records no browser execution or visual review.

The card language stays neutral: `SOURCE -> GAP -> MATURITY -> PERMISSION`.
`LOCAL CLEAR` is a local research component result only. The HTTP response,
fixture, route state, current admission, paper authority, and live authority all
remain blocked.

## Consumer-first activation order

1. Keep Python candidate unregistered and exercise only pure synthetic requests.
2. Keep card and fixture unmounted and exercise only Node contract tests.
3. Independently cross-check Python output against the JavaScript validator.
4. Require a separate ADR and new evidence before any route registration.
5. Require a later, separate review before any application or static mount.
6. Never infer current, paper, live, or execution authority from those steps.

This ADR does not authorize steps 4 or 5.

## Adversarial matrix

| Case | Required result |
| --- | --- |
| Extra request or context key | UNKNOWN, verifier not called |
| Substituted presentation hash | UNKNOWN, payload absent |
| Malformed exact-rebuild receipt | UNKNOWN, payload absent |
| Exact presentation with unknown source | UNKNOWN, all metrics hidden |
| budget-v3 BLOCK with predecessor locally clear | LOCAL BLOCK remains visible |
| Forged outer PASS or permission boolean | JavaScript rejects contract |
| Extra payload field followed by reseal | JavaScript rejects exact shape |
| Modified response or payload seal | JavaScript rejects contract |
| Adversarial dimension label | Escaped static markup only |
| Fixture descriptor mutation | Exact rebuild rejects descriptor |
| Route, mount, current, paper, or live claim | Permanently false |

## Consequences

- The active-strata gap is visible to an eventual consumer without expanding the
  presentation-v7 source document into UI state.
- Highly correlated assets still receive no independent-ticket credit merely
  because they appear in separate clusters or symbols.
- Unknown lineage cannot leak a plausible-looking partial risk dashboard.
- The files remain candidates only. No endpoint, registry, server, browser,
  scheduler, current pointer, evidence pack, or trading path changes.
- No result here is profitability evidence or trading authorization.
