# ADR 0159: report22 migration lockboard consumer

- Status: Accepted
- Date: 2026-08-22
- Scope: Unmounted research-only frontend consumer

## Context

ADR 0158 established a verifier-backed public-summary-v1 for report22 date-grid
migration evidence. The summary is safe to consume, but neither a route nor a UI
consumer existed. Wiring an internal migration assessment directly into the
existing application would bypass redaction and duplicate authority decisions.

The adjacent report21 frontend already uses an independent presenter, renderer,
stylesheet and Node contract while remaining unmounted. That boundary permits UI
work without changing runtime, HTTP or current behavior.

## Decision

Add an independent report22 date-grid migration lockboard that accepts only the
exact public-summary-v1 shape. The presenter validates the schema, implementation
fingerprint, axis order, every section key, all fail-closed permissions and all
redaction flags before selecting a presentation.

The component preserves four public states: NOT_SUPPLIED, UNKNOWN, PLAN_LISTED
and DRY_RUN_VERIFIED. A verified dry-run displays report22 PASS or BLOCK as a
descriptive decision while keeping execution at zero and current locked. Invalid
shapes, extra keys, native bool/integer aliases, cross-state reseals and authority
escalations degrade the entire component to an unverified UNKNOWN model.

The visual contract uses a warm ledger surface, a date-grid aperture, a five-stop
consumer-first lock rail and the fixed `SOURCE -> GAP -> MATURITY -> PERMISSION`
order. Responsive, reduced-motion and forced-colors behavior are included. The
renderer only emits fixed copy derived from validated enums and escapes all text.

## Consumer-first activation order

1. Keep public-summary-v1 as the only accepted input.
2. Validate the standalone presenter and renderer under Node.
3. Keep the component absent from `app.js` and `index.html`.
4. Audit any future HTTP candidate and DOM mount separately.
5. Require explicit authorization before service or browser validation.

## Consequences

The frontend now has a narrow, styled report22 consumer candidate without an
ambient DOM side effect or runtime dependency. This does not mount a component,
add a route, execute migration, change current, alter the natural-forward
single-look chain, or grant paper/live and profitability authority.
