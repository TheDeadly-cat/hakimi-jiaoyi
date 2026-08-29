# ADR 0064: Unmounted factor calibration evidence card

- Status: Accepted for a detached research candidate
- Date: 2026-08-23
- Scope: G1 presentation envelope, browser model, and detached card

## Context

G1 now provides a strict aggregate report for G0 calibration replay. The frozen F5 envelope and card consume a different factor-conditional global-family report and contain no G1 calibration summary, source calibration hash, MATCH state, or BLOCK state. Extending F5-v2 would change an already verified transport and visual contract.

## Decision

Create an independent G2 stack:

- Python envelope schema: `strategy-correlation-cross-lag-factor-calibration-presentation-envelope-v1`;
- Python fingerprint: `20260823-cross-lag-factor-calibration-presentation-envelope-1`;
- browser model schema: `strategy-correlation-cross-lag-factor-calibration-presentation-model-v1`;
- browser fingerprint: `20260823-cross-lag-factor-calibration-g2-unmounted-presentation-1`;
- presentation status: `UNMOUNTED_CANDIDATE`.

Python remains the semantic boundary. The envelope builder invokes the official G1 verifier with the complete G0/G1 contexts and carries an exact deep copy of the verified report. Missing, unsupported, and invalid report inputs produce distinct sealed closed envelopes.

The browser verifies strict canonical envelope and report hashes, exact schemas, internal cross-links, aggregate-only privacy, and locked authority. It does not replay OLS, validate external timing, or replace Python verification.

## Shared canonical JSON utility

G2 introduces `strict_canonical_json_v1.js` instead of depending on F5 contract-test hooks. The pure module provides strict plain-JSON canonicalization, SHA-256, sealing, and verification. F5 remains byte-for-byte frozen; a later version may migrate to the shared utility under a separate contract decision.

## Information design

The card preserves the neutral order `SOURCE -> GAP -> MATURITY -> PERMISSION`. A calibration window, decision, maximum beta error, tolerance, blockers, and shortened provenance hashes appear below that axis. MATCH uses evidence color without success theater; BLOCK uses a restrained warning; UNKNOWN remains visibly unresolved.

The visual direction is warm audit paper with ledger rules, a teal-to-copper calibration rail, condensed technical typography, mobile collapse at 720 px and 420 px, and reduced-motion support. Rendering is detached, text-only, and event-free.

## Privacy and authority

Rows, identity order, identity returns, factors, factor source, and beta values are forbidden at both Python and JavaScript boundaries. Current admission, pointer writes, paper authorization, live permission, profitability claims, mounting, and browser semantic replay remain false.

## Adversarial matrix

Coverage includes MATCH, BLOCK, verified G1 UNKNOWN, report not supplied, unsupported and invalid reports, expected-hash substitution, coherent report/envelope reseals, source-context substitution, non-native and non-finite payloads, private-key injection, authority aliases/unlock, canonical hash parity, deep freeze, safe detached DOM, responsive CSS, reduced motion, deterministic closures, and denied external state.

## Activation order

1. G0 and G1 remain unmounted sources.
2. G2 remains detached and absent from app, HTML, routes, services, and schedulers.
3. A separate activation ADR and mounted browser evidence are required before any UI integration.
4. No presentation step changes current, pointer-v2, natural-forward artifacts, paper/live authority, or profitability posture.
