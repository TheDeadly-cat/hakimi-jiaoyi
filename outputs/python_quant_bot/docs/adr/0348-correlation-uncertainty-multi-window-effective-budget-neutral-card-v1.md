# ADR 0348: Correlation uncertainty multi-window effective-budget neutral card v1

## Status

Accepted as an unmounted semantic-markup candidate. It is not imported by `app.js`, mounted in the DOM, styled by production CSS, or reviewed in a browser.

## Context

ADR 0347 supplies a bounded, sealed projection of ADR 0345 and ADR 0346. A future UI consumer still needs a safe and accessible rendering boundary. Rendering backend documents directly would duplicate strategy logic, expose unnecessary source structure, and allow arbitrary backend text to become UI copy.

## Decision

Add `strategy_correlation_uncertainty_multi_window_effective_budget_neutral_card_v1.js` as a UMD module with a colocated pure Node contract test.

The card consumes only the sealed ADR 0347 projection. It validates the exact top-level and nested key sets, schema and static fingerprints, axis order, allowed normalized states, fixed reason-code set, fixed blocker set, source-hash fields, bounded metric types, permanent false facts, and all-false authority. A coherently resealed but promoted or structurally altered projection becomes the fixed unknown card.

The view model is deeply frozen and contains only fixed copy, bounded counts, normalized stage states, and a ten-character local document-set receipt. Input reason text, backend decisions, source documents, window audits, prices, and returns never enter the view model.

The renderer returns one deterministic HTML string with:

1. A semantic `<article>` labelled by its `<h2>` and summary.
2. A `<dl>` for bounded evidence counts.
3. An ordered four-stage list for `SOURCE -> GAP -> MATURITY -> PERMISSION`.
4. A visible open-gap ledger.
5. A visible research-only permission note.

State is communicated with explicit text and semantic ordering rather than color alone. All rendered values pass through one HTML-escaping function. The renderer has no links, buttons, form controls, event handlers, inline styles, DOM calls, or network calls.

Card IDs are deterministic from the sealed local document-set hash. Unknown evidence uses a fixed unknown ID and exposes no metrics.

## Consumer-first activation order

1. Keep the card unmounted and validate its sealed-document and markup contracts under Node.
2. Obtain an independent semantic-markup and non-disclosure review.
3. Define a separately preregistered host adapter if mounting is still desired.
4. Review real browser layout, keyboard navigation, zoom, contrast, screen-reader output, and responsive behavior before any production mount.
5. Any `app.js`, CSS, route, runtime, current-pointer, writer, paper, or live change requires a separate authorization decision.

## Adversarial matrix

The colocated contract covers known research evidence, veto, reduction-only, budget block, unknown evidence, resealed authority promotion, metric injection, semantic labelling, visible state text, bounded-count rendering, payload non-disclosure, non-interactivity, inline-style absence, deterministic IDs, promotional-word absence, dependency source pinning, frozen API, and absence of DOM or network operations.

## Consequences

The project gains a concrete, accessible frontend artifact rather than only a data contract, while preserving the unmounted boundary. No browser, visual, accessibility, runtime, market, or authorization conclusion follows until the separately listed reviews occur.

This synthetic markup evidence is not strategy performance evidence, public-release authorization, or trading permission.
