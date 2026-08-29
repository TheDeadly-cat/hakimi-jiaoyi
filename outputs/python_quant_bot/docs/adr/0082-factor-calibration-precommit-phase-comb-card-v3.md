# ADR 0082: Detached factor-calibration precommit phase-comb card v3

## Status

Accepted as an unmounted, research-only candidate. It is not current and has no activation authority.

## Context

The v2 phase-comb card is sealed to presentation envelope v2 and its two preregistered lag markers. Presentation envelope v3 consumes report consumer v6 and adds an independently versioned third-lag coverage boundary. Reinterpreting v3 through the v2 card would create compatibility drift and could hide source-state, aggregate, or permission inconsistencies.

The presentation layer must remain aggregate-only and neutral. A card may communicate SOURCE, GAP, MATURITY, and PERMISSION, but it may not expose per-lag results, private ledgers, returns, residuals, identities, profitability language, or execution authority.

## Decision

Add a separate `factor-calibration-precommit-phase-comb-card-v3` with static fingerprint `20260910-factor-calibration-precommit-phase-comb-card-3`.

The card accepts only:

- schema `strategy-correlation-cross-lag-factor-calibration-precommit-presentation-envelope-v3`;
- fingerprint `20260909-cross-lag-factor-calibration-precommit-presentation-envelope-3`;
- status `UNMOUNTED_CANDIDATE`;
- a valid strict-canonical `presentation_hash`, optionally bound to an expected hash;
- exact top-level and nested public keys, exact source-hash cross-binding, three ordered preregistered teeth, aggregate consistency, an open GAP axis, and locked authority.

Verified source states map monotonically:

- `VERIFIED_LOCAL_BINDING` becomes `LOCAL_BINDING`;
- `VERIFIED_BLOCK` becomes `EVIDENCE_BLOCK`;
- invalid, missing, unsupported, or inconsistent input becomes fail-closed `UNKNOWN`.

The visual language is a detached laboratory instrument: warm graph paper, oxide/tide/ochre lag markers, a high-contrast aggregate plate, and a numbered four-axis rail. The three lag teeth communicate preregistered coverage only. Motion is limited to initial arrival and staggered teeth, and is disabled by `prefers-reduced-motion`.

Rendering requires an explicit detached document and uses `textContent` only. The module has no `app.js` import, page selector, DOM-ready listener, browser global, route, scheduler, or pointer write.

## Consumer-first activation order

1. Freeze and verify presentation envelope v3.
2. Verify the detached v3 model, strict-canonical mapping, privacy, neutral copy, CSS scope, and DOM safety.
3. Register only the test in lean planning and keep execution at list/dry-run.
4. Consider a later versioned mount only after a separate activation decision. No current pointer may change automatically.

## Adversarial matrix

The direct contract covers schema/fingerprint/status drift, hash mutation, expected-hash mismatch, top-level private-field injection, authority and permission escalation, source-state substitution, source-hash cross-bind drift, gap closure, maturity lag drift, missing/duplicate/reordered teeth, per-lag result exposure, aggregate mismatch, threshold-relation mismatch, invalid numeric grammar, unknown closure, detached rendering, injection text, neutral copy, responsive CSS, reduced motion, determinism, and implicit activation hooks.

## Consequences

- v2 remains frozen and cannot silently consume v3.
- Public output remains three coverage teeth plus one aggregate maximum and ceiling.
- Arbitrary-lag independence and external timing remain unresolved.
- GAP remains open and PERMISSION remains locked in every state.
- The card is not evidence of profitability and grants no paper or live authority.
