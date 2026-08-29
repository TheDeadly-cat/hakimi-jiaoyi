# ADR 0229: Projection-v6 Node consumer and cross-runtime conformance

## Status

Accepted as an unmounted, descriptor-only presentation candidate. It is not imported by the application, mounted in a DOM, registered, current, paper-authorized, or live-authorized.

## Context

ADR0228 added a Python projection-v6 that preserves observed local clear, downside-tail block, and exact UNKNOWN source states. The existing Node card-v5 accepts only projection-v5 and has no downside-tail semantics. Extending it to accept v6 would make an older consumer silently reinterpret a new risk model.

The next consumer-first step therefore needs a dedicated projection-v6 validator, view model, renderer, descriptor, scoped stylesheet, and Python-to-Node conformance evidence. It must remain usable without DOM, browser, or runtime access.

## Decision

Add:

- `evidence_portfolio_risk_downside_tail_card_v6.js`, which exact-validates the projection schema, fingerprint, strict canonical seal, keys, source-state consistency, gaps, redaction facts, and authority before building a frozen view model;
- `evidence_portfolio_risk_downside_tail_consumer_fixture_v6.js`, which seals an unmounted descriptor and exposes no mount API;
- `evidence_portfolio_risk_downside_tail_card_v6.css`, a fully scoped responsive stylesheet with bounded, critical, gap, and unknown visual semantics;
- independent Node and Python-to-Node adversarial contracts.

The view keeps `SOURCE -> GAP -> MATURITY -> PERMISSION` explicit. Local clear uses a cool blue informational treatment, downside-tail coupling uses a vermilion warning treatment, and UNKNOWN uses neutral graphite. None of these tones grants permission. The permission stage remains unauthorized in every accepted or rejected state.

## Safety and rendering rules

- Projection-v5 and any schema downgrade are rejected.
- Resealed authority promotion, extra fields, inconsistent source state, and untrusted strings fail closed.
- Markup is generated only from a validated frozen view model and all interpolated values are HTML-escaped.
- Exact UNKNOWN source remains a known fail-closed descriptor, distinct from an invalid projection.
- The descriptor declares but does not read or mount the stylesheet.
- Runtime assets, DOM, browser, and visual-review claims remain false.
- Risk-reduction joint exemption remains explicitly unimplemented.

## Consumer-first activation order

1. Adapter-v6 presentation envelope, ADR0226.
2. Envelope-first HTTP candidate-v6, ADR0227.
3. Python projection-v6, ADR0228.
4. Unmounted Node consumer and cross-runtime conformance, this ADR.
5. Future local execution evidence and registration pins.
6. Separately authorized application integration and admission review, with no automatic route, current, or pointer change.

## Consequences

The project now has an auditable, responsive frontend candidate for correlated downside-tail risk without changing the existing application or stylesheet. No browser visual inspection was performed, so aesthetic claims are source-level only. No result proves profitability or authorizes paper/live activity. Existing natural-forward artifacts, legacy public reads, pointer-v2, and current admission remain unchanged.
