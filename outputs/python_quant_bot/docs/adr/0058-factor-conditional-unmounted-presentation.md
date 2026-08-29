# ADR 0058: Unmounted factor-conditional evidence presentation

- Status: design accepted; implementation complete; page activation not started.
- Date: 2026-08-21.
- Scope: read-only application envelope, pure JavaScript presentation model, detached renderer, and scoped CSS.
- Activation: prohibited. No runtime route, page mount, current pointer, scheduler, paper/live action, or profitability claim.

## Context

F1 now produces an exactly replayed, aggregate-only receipt:

- Schema: `strategy-correlation-cross-lag-factor-conditional-report-consumer-verification-v1`.
- Fingerprint: `20260822-cross-lag-factor-conditional-report-consumer-1`.
- Hash field: `verification_hash`.
- Source states: `OBSERVED`, `MISSING`, `UNSUPPORTED`, or `INVALID`.
- Permission state: always `LOCKED`.

The existing C4 cross-lag card is unmounted and uses a pure model plus detached renderer. Its structure is useful, but it consumes a different C3 source contract. F2 must not accept C3, F0-v1, F0-v2, or an unverified F1-shaped object.

A browser cannot semantically replay F1 because the raw preregistered strata, aligned observations, residualization registration, factor observations, and expected hashes are intentionally absent. Therefore JavaScript alone cannot claim that an F1 receipt is verified.

## Decision

Add a Python application envelope before adding the JavaScript model. Keep every new artifact unmounted.

### Application envelope

- Module: `exchange_terminal/application/strategy_correlation_cross_lag_factor_conditional_presentation_envelope.py`.
- Schema: `strategy-correlation-cross-lag-factor-conditional-presentation-envelope-v1`.
- Fingerprint: `20260822-cross-lag-factor-conditional-presentation-envelope-1`.
- Hash field: `envelope_hash`.
- Presentation status: `UNMOUNTED_CANDIDATE`.

Inputs:

- F1 receipt or `None`.
- F0-v2 diagnostic or `None`.
- Preregistered strata, aligned observations, residualization registration, and factor observations.
- Expected strata, registration, factor-observation, diagnostic, and F1 receipt hashes.

Behavior:

- `receipt is None` produces a fixed `NOT_SUPPLIED` envelope with no report.
- A supplied receipt must have a strict expected receipt hash and pass the official F1 exact verifier against the full context.
- A valid F1 receipt is carried unchanged as `report`, including valid F1 UNKNOWN closures.
- Any supplied but invalid receipt produces a fixed `INVALID` envelope with no report.
- Caller-controlled exception text, extra fields, or source values are never reflected in invalid closure.
- The exact envelope verifier rebuilds the entire document and requires strict JSON equality.

Envelope fields:

- schema, fingerprint, envelope hash, and presentation status;
- `verification_state = VERIFIED | NOT_SUPPLIED | INVALID`;
- trusted F1 schema, fingerprint, receipt hash, diagnostic hash, and source state when verified;
- exact aggregate F1 report or `null`;
- locked authority.

### JavaScript presentation model

- Module: `exchange_terminal/static/factor_conditional_evidence_card.js`.
- Model schema: `strategy-correlation-cross-lag-factor-conditional-presentation-model-v1`.
- Fingerprint: `20260822-cross-lag-factor-conditional-f2-unmounted-presentation-1`.
- Hash field: `presentation_model_hash`.
- Presentation status: `UNMOUNTED_CANDIDATE`.

Exports:

- `buildFactorConditionalPresentationModel(envelope)`.
- `createFactorConditionalEvidenceCard(document, envelope)`.
- `constants`.
- `contractTestHooks` containing strict ASCII canonical JSON and SHA-256 helpers.

JavaScript validates exact native object/array types, exact schemas/fingerprints, strict 64-character lowercase hashes, finite native numbers, ASCII-only strings, locked authority, allowed keys, envelope hash, and nested F1 receipt hash before projection. It never claims to re-run Python semantic verification; it consumes the sealed application envelope that already did so.

### Four-axis information architecture

Every model contains exactly four ordered axes:

1. `SOURCE`: `OBSERVED`, `MISSING`, `UNSUPPORTED`, `INVALID`, `NOT_SUPPLIED`, or `UNKNOWN`.
2. `GAP`: the exact neutral F1 gap state, or a fixed envelope/source failure state.
3. `MATURITY`: F1 maturity or `UNKNOWN/NOT_EVALUATED`.
4. `PERMISSION`: always `LOCKED`.

Observed models may expose only:

- raw and residual gate decisions and reasons;
- aggregate observation, pair, lag-test, dependent-test, and adjusted-lower-bound values;
- stable blockers;
- F1, F0-v2, and F0-v1 provenance hashes;
- source, report, gap, maturity, and permission states.

They never expose observation rows/IDs, identity labels, factor IDs or values, betas, residual rows, pair-level lag tests, calibration payloads, or raw return series.

### Neutral copy contract

The renderer uses text nodes only and follows `SOURCE -> GAP -> MATURITY -> PERMISSION`.

- Eyebrow: `FACTOR-CONDITIONAL EVIDENCE`.
- Title: `Cross-lag mechanism ledger`.
- Permission label: `Research display only`.
- Footer: `No independence, causality, profitability, paper, or live authority.`

Prohibited rendered implications include `READY`, `approved`, `profitable`, `safe to trade`, `signal`, `buy`, `sell`, and any statement that residual PASS relaxes raw BLOCK.

### Detached renderer

`createFactorConditionalEvidenceCard(document, envelope)` creates and returns one detached root element. It must:

- require an explicit DOM-like `document` argument;
- use `createElement`, `createTextNode`, `textContent`, attributes, and append operations only;
- never call `querySelector`, `getElementById`, global `document`, `innerHTML`, event registration, timers, fetch, storage, or mount operations;
- never mutate the envelope or model;
- encode state only through scoped class names and `data-*` attributes.

### Scoped visual system

- Stylesheet: `exchange_terminal/static/factor_conditional_evidence_card.css`.
- Root scope: `.factor-conditional-evidence-card`.
- Visual direction: restrained forensic ledger, warm paper surface, graphite text, copper gap accents, muted blue evidence lines, and vermilion blockers.
- Typography: local `Bahnschrift`/condensed sans for headings and `Cascadia Mono` for hashes and metrics; no network font import.
- Raw and residual views are paired, not ranked. PASS uses muted evidence blue rather than success green; BLOCK uses copper/vermilion without trading alarm language.
- One optional root-entry reveal may run only when `.is-entering` is explicitly applied. `prefers-reduced-motion` disables it.
- All selectors are root-scoped except the scoped keyframe and media queries.
- Responsive layout collapses from paired columns to one column below 760px without hiding provenance or permission.

## Fixed model closures

- Null envelope: `SOURCE=NOT_SUPPLIED`, `GAP=ENVELOPE_NOT_SUPPLIED`, `MATURITY=NOT_EVALUATED`, `PERMISSION=LOCKED`.
- Invalid envelope: `SOURCE=UNKNOWN`, `GAP=ENVELOPE_INVALID`, `MATURITY=UNKNOWN`, `PERMISSION=LOCKED`.
- Verified F1 MISSING: `SOURCE=MISSING`, F1 missing gap, `MATURITY=UNKNOWN`, `PERMISSION=LOCKED`.
- Verified F1 UNSUPPORTED: `SOURCE=UNSUPPORTED`, F1 pre-consumer gap, `MATURITY=UNKNOWN`, `PERMISSION=LOCKED`.
- Verified F1 INVALID: `SOURCE=INVALID`, F1 invalid gap, `MATURITY=UNKNOWN`, `PERMISSION=LOCKED`.
- Verified F1 OBSERVED: exact F1 report/gap/maturity states, but permission remains locked.

Envelope verification and source maturity are separate axes. A cryptographically valid UNKNOWN receipt never becomes observed evidence.

## Locked authority

Only `descriptive_only` is true. At minimum these remain false in the envelope and model:

- `source_semantics_replayed_in_browser`
- `factor_calibration_attested`
- `global_two_view_multiplicity_registered`
- `common_factor_causality_proven`
- `raw_independence_proven`
- `residual_independence_proven`
- `presentation_mounted`
- `candidate_activation_allowed`
- `current_admission_allowed`
- `current_pointer_written`
- `paper_authorized`
- `live_order_allowed`
- `profitability_claim_allowed`

## Consumer-first implementation order

1. Freeze this ADR and its schemas, fingerprints, copy, axes, and test matrix.
2. Implement the Python envelope builder and exact verifier.
3. Close Python observed, UNKNOWN, context, expected-hash, tamper, redaction, and denied-I/O tests.
4. Implement the pure JavaScript model and strict-canonical SHA-256 verifier.
5. Implement the detached renderer and scoped stylesheet.
6. Close Node model, renderer, CSS, no-mount, and malicious-input tests.
7. Run an independent Python-to-Node envelope/hash/state probe.
8. Register Python and Node tests plus syntax paths in lean; run list/dry-run without receipts or fresh execution.
9. Synchronize ADR and the three baseline documents.
10. Do not import the module from `app.js`, add HTML/CSS links, start a browser, or publish without a later ADR and explicit authorization.

## Adversarial matrix

| ID | Case | Required result |
| --- | --- | --- |
| F2-01 | Null envelope | Fixed NOT_SUPPLIED model |
| F2-02 | Empty or non-native envelope | Fixed INVALID model |
| F2-03 | Verified mediated receipt | Exact observed mediated model; raw BLOCK visible |
| F2-04 | Verified residual-dependence receipt | Exact observed BLOCK/BLOCK model |
| F2-05 | Verified no-conditional-dependence receipt | PASS/PASS shown without independence authority |
| F2-06 | Verified suppression receipt | PASS/BLOCK instability model |
| F2-07 | Verified F1 MISSING receipt | MISSING/UNKNOWN remains visible |
| F2-08 | Verified F1 UNSUPPORTED receipt | UNSUPPORTED/UNKNOWN remains visible |
| F2-09 | Verified F1 INVALID receipt | INVALID/UNKNOWN remains visible |
| F2-10 | Wrong expected receipt hash | Invalid envelope |
| F2-11 | Broken or resealed envelope hash | Fixed INVALID model |
| F2-12 | Broken or resealed nested F1 receipt | Invalid envelope/model |
| F2-13 | Envelope or receipt schema/fingerprint drift | Invalid closure |
| F2-14 | Context, diagnostic, or source-hash mismatch | Invalid envelope |
| F2-15 | Added, removed, duplicated, or reordered blocker | Exact verification false |
| F2-16 | Pseudo-boolean, subclass/prototype object, non-finite number | Invalid closure |
| F2-17 | Non-ASCII or hostile text in any untrusted field | Rejected, never rendered |
| F2-18 | Authority alias or true activation field | Exact verification false |
| F2-19 | Observation, identity, beta, factor, residual, or pair-test leak | Test failure |
| F2-20 | Renderer attempts innerHTML, global DOM lookup, event, timer, fetch, or mount | Test failure |
| F2-21 | Detached fake-DOM render | One detached root with text-only neutral copy |
| F2-22 | CSS global selector, missing mobile collapse, or missing reduced-motion rule | Test failure |
| F2-23 | `app.js`, HTML, runtime/server, or Electron reference | Must remain zero |
| F2-24 | Python-to-Node canonical hash/state parity | Exact match for observed and UNKNOWN fixtures |

## Activation gates

F2 implementation is not UI activation. Mounting remains prohibited until a separate review proves exact envelope sourcing, stable page lifecycle, neutral rendered copy, accessibility, responsive behavior, no current/pointer mutation, and explicit authorization. Paper/live remain unauthorized regardless of presentation quality.

The natural-forward chain remains unchanged: `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`. Legacy pack-v5 public reads remain `UNKNOWN`, and pointer-v2 fields/hash semantics remain untouched and are not reissued.

## Consequences

- Python remains the semantic verification boundary.
- JavaScript gains a deterministic, tamper-evident, aggregate-only view model.
- UI quality improves without adding a mount, route, execution path, or authority implication.
- Existing C4, app.js, server, Electron, and natural-forward contracts remain unchanged.
- No return backtest or new profitability number is generated.

## Implementation closure (2026-08-21)

Status: `IMPLEMENTED_UNMOUNTED_PRESENTATION`.

- Python application envelope: `exchange_terminal/application/strategy_correlation_cross_lag_factor_conditional_presentation_envelope.py`; schema `strategy-correlation-cross-lag-factor-conditional-presentation-envelope-v1`; fingerprint `20260822-cross-lag-factor-conditional-presentation-envelope-1`.
- JavaScript model/renderer: `exchange_terminal/static/factor_conditional_evidence_card.js`; model schema `strategy-correlation-cross-lag-factor-conditional-presentation-model-v1`; fingerprint `20260822-cross-lag-factor-conditional-f2-unmounted-presentation-1`.
- Stylesheet: `exchange_terminal/static/factor_conditional_evidence_card.css`; Node contract: `exchange_terminal/static/factor_conditional_evidence_card.test.js`.
- The Python adapter exactly replays F1 against the full F0/context inputs before sealing an envelope. `VERIFIED` is independent of the nested F1 source state, so exact MISSING, UNSUPPORTED, and INVALID receipts remain UNKNOWN rather than observed.
- Envelope tests: `18/18 OK`. C0 + F0-v1 + F0-v2 + F1 + envelope matrix: `89/89 OK`.
- Node syntax checks for implementation and test passed. The Node contract passed 4 observed states, 3 verified UNKNOWN states, NOT_SUPPLIED/INVALID closure, strict-canonical SHA-256, redaction, detached fake-DOM rendering, scoped responsive CSS, reduced motion, and no mount.
- Independent Python-to-Node probe passed for observed, MISSING, UNSUPPORTED, INVALID, and NOT_SUPPLIED envelopes with exact envelope hashes and locked four-axis states. The observed real-envelope model hash was `17bdc81f3828e565b8626f29c2b83f50476a716e8743b5a80a2ab1ac0354613d`.
- Visual direction is a restrained forensic ledger: warm paper surface, graphite text, muted evidence blue, copper gap accents, vermilion blockers, paired raw/residual panels, condensed local headings, monospaced provenance, mobile collapse at 760px, and explicit reduced-motion behavior.
- Renderer is text-only and detached. It performs no global DOM lookup, HTML injection, event/timer/fetch/storage access, or mounting.
- No browser was started and no rendered-page screenshot was collected. Evidence proves source, model, fake-DOM, and CSS contracts, not mounted visual acceptance.
- Explicit app/HTML/runtime/server/Electron paths contain no F2 module, CSS, or global export references. `app.js` remains `9BF55162AFF8D7A233804557C91605C801B92F515B2835978C05E2D1F3EF9210`.
- Lean research list/dry-run reports 5 planned, 0 completed, 0 executed, receipts disabled, runtime mutations false, paper/live false, and no fresh execution. Envelope test/source and Node F2 check each occur exactly once.
- Authority remains locked except `descriptive_only=true`. F2 does not prove independence, causality, calibration, profitability, paper/live permission, or current admission.
- SHA-256: envelope service `A0E10830EB452320D0C2A962508462C9B678EEB5B2E9DAE4931FAEE7EA47510B`; envelope test `926F7009306609CA9ED6D0486AE0E2DBA8CD677BA773CC6F108AB728078F7003`; JS `EE3AB70EBB0645660DC3941D8DC3CA510428B97B9971A700A04686AC96AA258E`; Node test `2E5F9DB5357A3948E6C6BB77A9D80353664F7C74CC949D56EBB0A172F2462F24`; CSS `B97902A786D7D2A8742A8602B2761B20F861F3DDE769747AED653E0816F2C445`; lean `E6B474324B72D074DBC78525388D4CFED91FA51787AD69123E38F333C194B5EF`.
