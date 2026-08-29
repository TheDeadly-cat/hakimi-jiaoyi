# ADR 0054: Cross-lag C4 unmounted neutral presentation

- Status: Accepted and implemented as an unmounted C4 candidate; adapter and mount not authorized
- Date: 2026-08-21
- Scope: Research evidence presentation only
- Authority: None

## Context

C3 provides an aggregate-only, strict-canonical public summary after replaying
the complete C2 binding context. It preserves valid `OBSERVED_PASS` and
`OBSERVED_BLOCK` evidence while keeping sequence order, formal registration,
current activation, profitability, paper, and live authority false.

C4 must make that small public contract legible without turning a candidate
observation into a recommendation, a readiness claim, or an execution control.
It must be testable before it is connected to a service or mounted in the
terminal. The current `app.js`, `index.html`, main stylesheet, routes, and
natural-forward pointers are outside this decision.

## Decision

C4 v1 is a detached presentation component with two pure stages:

1. `buildCrossLagPresentationModel(envelope)` validates and normalizes a supplied
   C3 presentation envelope into an immutable view model.
2. `createCrossLagEvidenceCard(documentRef, model)` creates and returns one
   detached DOM subtree.

Neither stage fetches data, reads global application state, finds a mount point,
or appends the returned subtree. Importing the module must not mutate the DOM.

The candidate implementation files are:

- `exchange_terminal/static/cross_lag_evidence_card.js`;
- `exchange_terminal/static/cross_lag_evidence_card.css`;
- `exchange_terminal/static/cross_lag_evidence_card.test.js`.

The CSS file is not linked from `index.html`, and the module is not imported by
`app.js`, until a separate mount decision is designed and authorized.

## Versioned presentation contract

Presentation model schema:
`strategy-correlation-cross-lag-presentation-model-v1`

Verification envelope schema:
`strategy-correlation-cross-lag-presentation-envelope-v1`

Static fingerprint:
`20260821-cross-lag-c4-unmounted-presentation-1`

The envelope contains only:

- `schema_version`;
- `summary`, containing the C3 public summary;
- `verification`, containing the C3 verification schema, a native boolean
  `valid`, the supplied public-summary hash, and the rebuilt public-summary hash.

The two verification hashes must be strict uppercase or lowercase hexadecimal
SHA-256 strings and must exactly match each other and
`summary.public_summary_hash`.

C4 must also recompute the C3 public-summary hash from the entire supplied
summary after removing only the root `public_summary_hash` field. The
recomputation uses sorted-key, compact, UTF-8 JSON with the same scalar rules as
the Python strict-canonical contract, followed by SHA-256. The candidate module
implements this synchronously in pure JavaScript and does not call Web Crypto,
Node crypto, a callback, a worker, or a service. C3 v1 fixed strings are ASCII;
an unsupported non-ASCII or non-canonical scalar fails closed instead of being
normalized differently across runtimes.

The recomputed hash, supplied summary hash, verification supplied hash, and
verification rebuilt hash must all match. This proves document integrity against
the supplied official receipt; it does not attest that a browser-created receipt
is authentic and does not replace the Python C2/C3 replay. A future loopback
adapter may construct the envelope only after the official Python C3 verifier
succeeds. No such adapter or endpoint is authorized by this ADR.

A forged browser object can never create authority. Until a separately reviewed
adapter exists, C4 is exercised only with pure synthetic fixtures.

## Accepted C3 source

C4 accepts only the exact C3 public schema
`strategy-correlation-cross-lag-public-summary-v1`, verification schema
`strategy-correlation-cross-lag-public-summary-v1-verification-v1`, and static
fingerprint `20260821-cross-lag-public-summary-1`.

The model builder reads only this aggregate allowlist:

- public state;
- the four axis names, states, and fixed reason codes;
- C3 public-summary hash and approved provenance hashes;
- aggregate cross-stratum pair, lag-test, and dependent-test counts;
- aggregate maximum adjusted absolute lower-bound diagnostic string;
- fixed aggregate facts and blockers;
- native boolean authority fields.

It must not copy unknown properties into the model. In particular, it must never
copy symbols, identities, assignments, cluster members, prices, bars, returns,
aligned observations, pair/lag arrays, local paths, URLs, callbacks, writers,
service handles, or untrusted descriptions.

## Fail-closed normalization

The four public states remain distinct:

| Input | Presentation state | Treatment |
| --- | --- | --- |
| Envelope absent | `NOT_SUPPLIED` | Fixed not-supplied copy only |
| Envelope malformed | `UNKNOWN` | Fixed invalid-source copy only |
| Verification false or hash mismatch | `UNKNOWN` | Never reflect supplied values |
| Valid C3 `OBSERVED_PASS` | `OBSERVED_PASS` | Preserve candidate non-detection with caveats |
| Valid C3 `OBSERVED_BLOCK` | `OBSERVED_BLOCK` | Preserve dependence block prominently |

The model builder must fail closed to fixed constants when any of these occurs:

- unsupported schema or fingerprint;
- non-mapping envelope, summary, verification, axes, facts, or authority;
- missing, duplicate, reordered, or extra axis;
- non-native boolean verification or authority value;
- public state, reason, decision, count, or blocker inconsistency;
- verification hash mismatch;
- recomputed strict-canonical public-summary hash mismatch;
- any authority value true other than `descriptive_only`;
- prototype-bearing or accessor-based untrusted fields that cannot be read
  safely;
- normalization exception.

`OBSERVED_BLOCK` must never degrade to pass because of presentation gaps. A valid
block remains visually and textually explicit.

## Four-axis information architecture

The public order is fixed:

`SOURCE -> GAP -> MATURITY -> PERMISSION`

The card contains:

1. a small provenance eyebrow: `Research evidence / Candidate`;
2. a heading: `Cross-lag dependence`;
3. one plain-language observation sentence;
4. a four-cell definition list in the fixed axis order;
5. aggregate counts and the maximum lower-bound diagnostic, when valid;
6. a blocker ledger;
7. a persistent permission footer: `Locked: research display only`.

Fixed observation copy:

- `NOT_SUPPLIED`: `No cross-lag evidence summary was supplied.`
- `UNKNOWN`: `Cross-lag evidence could not be verified for presentation.`
- `OBSERVED_PASS`: `No preregistered cross-lag dependence was detected in this candidate observation.`
- `OBSERVED_BLOCK`: `Cross-lag dependence was observed; correlated tickets must not be counted independently.`

The pass sentence is a candidate non-detection, not proof of independence. It
must be followed by the sequence-order and formal-registration gaps carried by
C3. The block sentence is never softened by missing C4 activation.

User-facing copy must not contain `READY`, `AUTHORIZED`, `EXECUTABLE`, expected
return, target return, recommendation, allocation, order, or profitability
claims. Hashes are labelled as provenance identifiers, never scores.

## Visual direction

The component uses a compact forensic-ledger visual language rather than a
generic success card:

- warm paper and cool slate surfaces with an ink-blue frame;
- amber for unresolved gaps and oxidized rust for blocks or locked permission;
- no green success treatment, check mark, trophy, confetti, purple gradient, or
  trading-action color cue;
- `Bahnschrift` for axis labels and tabular figures, with `Aptos` and
  `Microsoft YaHei UI` as local reading fallbacks;
- a narrow vertical evidence rail, subtle grid texture, and one restrained
  entrance reveal;
- `OBSERVED_PASS` and `OBSERVED_BLOCK` differ by wording, border pattern, and
  explicit state label, not color alone.

All selectors are scoped below `.cross-lag-evidence-card`. The candidate CSS may
define component-local custom properties but must not change `:root`, `body`, or
existing terminal classes.

At widths below 720 px, the four axes become a single column, aggregate metrics
use a two-column grid, and long hashes wrap without horizontal scrolling. The
component must remain usable at 320 px.

The only motion is a short card reveal and a small stagger across the four axes.
`prefers-reduced-motion: reduce` removes animation and transforms. Nothing
blinks, pulses, counts up, or implies urgency.

## DOM and accessibility contract

The renderer uses only `createElement`, `createTextNode`, `textContent`,
`classList`, and fixed `setAttribute` calls. It must not use `innerHTML`,
`outerHTML`, `insertAdjacentHTML`, string-built CSS, inline event handlers,
`eval`, dynamic script injection, or URL-bearing elements.

The returned root is a detached `<section>` with a stable `aria-label`. Axis
content uses `<dl>`, `<dt>`, and `<dd>`. Blockers use a semantic list. Aggregate
figures use tabular numerals. Color is never the only state signal, text contrast
must meet WCAG AA, and no essential copy is hidden from assistive technology.

The component has no controls, links, focus traps, live regions, or keyboard
shortcuts because it performs no action. Rendering must leave `document.body`
unchanged until a caller explicitly appends the returned node.

## Side-effect prohibition

C4 v1 must not use:

- `fetch`, `XMLHttpRequest`, `WebSocket`, `EventSource`, or beacon APIs;
- filesystem, storage, cache, cookie, clipboard, worker, or service-worker APIs;
- timers, animation-frame loops, observers, callbacks, or event listeners;
- database, route, scheduler, pointer, publication, or trading APIs;
- global DOM queries or implicit mount identifiers.

The module may expose a frozen API object for direct testing, but exposure must
not mount, schedule, fetch, or mutate application state.

## Adversarial acceptance matrix

| Attack or gap | Required result |
| --- | --- |
| Missing envelope | Fixed `NOT_SUPPLIED` model |
| Non-mapping envelope | Fixed `UNKNOWN` model |
| Unsupported envelope/C3 schema or fingerprint | Fixed `UNKNOWN` model |
| Verification value `1`, `"true"`, or object | Fixed `UNKNOWN` model |
| Supplied/rebuilt/summary hash mismatch | Fixed `UNKNOWN` model |
| Summary content changed while an old official receipt is retained | Fixed `UNKNOWN` model |
| Missing, duplicate, extra, or reordered axis | Fixed `UNKNOWN` model |
| Public state or blocker inconsistency | Fixed `UNKNOWN` model |
| Any resealed authority alias or true permission | Fixed `UNKNOWN` model |
| Extra symbol, return, path, URL, or callback field | Not reflected in model or DOM |
| HTML/script payload in any extra field | Rendered nowhere; no HTML interpretation |
| Valid C3 pass | Candidate non-detection remains caveated and locked |
| Valid C3 block | Dependence block remains first and explicit |
| Renderer receives malformed model | Detached fixed `UNKNOWN` card |
| Renderer called with hostile text | Text node only |
| Import or render | No fetch, file, timer, listener, route, or storage access |
| Render without append | `document.body` remains unchanged |
| 320 px layout | No required horizontal scrolling |
| Reduced-motion preference | No animation or transform |
| Promotional or execution wording | Static contract test fails |

At least one tamper must change a real nonzero dependent-test count while
retaining the original official verification envelope. It must fail because the
recomputed C3 summary hash no longer matches that envelope. Tests must assert the
original count is nonzero before mutation. A separately forged browser receipt
still creates no authority and is outside the future trusted adapter boundary.

## Consumer-first activation sequence

Activation is deliberately split into independent gates:

1. Accept this ADR while all runtime and UI entry points remain unchanged.
2. Implement the pure model builder and detached renderer in new files only.
3. Add fake-DOM, source-boundary, responsive-CSS, reduced-motion, redaction, and
   adversarial tests; register only those tests in lean list/dry-run.
4. Run targeted Node syntax/tests and an independent no-I/O probe.
5. Synchronize the ADR and baseline documents with actual hashes and evidence.
6. Design a separate loopback presentation-envelope adapter that invokes the
   official Python C3 verifier. Do not implement it implicitly in C4.
7. Design and review a separate mount decision. Until then, do not edit
   `app.js`, `index.html`, the main stylesheet, or service routes.
8. If mounting is ever authorized, version the blocker transition separately;
   do not rewrite or reinterpret the immutable C3 v1 summary.

No step automatically activates the next one. Test success does not authorize a
service adapter, mounting, current-pointer changes, paper trading, or live
trading.

## C4 implementation acceptance

C4 implementation is complete only when all of the following are current-tree
evidence:

- the three candidate files exist and no mounted entry file changed;
- model and DOM tests cover every row of the adversarial matrix that is testable
  without a browser;
- Node syntax and targeted tests pass;
- pure-JavaScript SHA-256 passes standard known vectors and matches Python's C3
  strict-canonical hash for synthetic PASS and BLOCK summaries;
- CSS source tests prove component scoping, 320 px behavior, reduced motion, and
  absence of global selectors or remote imports;
- an independent probe denies file/network/timer/listener access and confirms a
  detached DOM result;
- a valid pass and valid block are both visible with all authority false;
- source scans find no promotional copy or execution control;
- lean list/dry-run plans the new checks but executes zero checks;
- implementation fingerprints and limitations are synchronized to ADR 0054 and
  the three baseline documents.

## Consequences

C4 can improve clarity and visual quality without increasing research maturity
or execution capability. The cost is an explicit future adapter and mount review,
which prevents a polished component from silently becoming a trusted or current
product surface.

C4 is implemented as an unmounted candidate. The natural-forward chain, legacy
pack-v5 public-read behavior, pointer-v2, paper lock, and permanent live lock are
unchanged.

## Implementation closure (2026-08-21)

The accepted design is implemented in three new files only:

- `exchange_terminal/static/cross_lag_evidence_card.js`;
- `exchange_terminal/static/cross_lag_evidence_card.css`;
- `exchange_terminal/static/cross_lag_evidence_card.test.js`.

The implementation preserves all four exact C3 states, recomputes the complete
C3 strict-canonical public-summary hash in synchronous pure JavaScript, emits a
deeply frozen presentation model, and returns a detached `<section>`. The
renderer uses fixed text nodes and semantic definition-list markup. Its scoped
forensic-ledger CSS includes 720 px and 420 px layouts plus reduced-motion
closure. No C4 file is referenced by a mounted entry point.

Targeted current-worktree evidence:

- source and test `node --check`: PASS;
- C4 contract suite: 26/26 PASS;
- all four real synthetic C3 public summaries match the Python public-summary
  hashes;
- independent Python-to-Node probe: `OBSERVED_PASS` and `OBSERVED_BLOCK`
  preserved, real `dependent_test_count=1`, tamper result `UNKNOWN`, detached
  DOM true, model frozen true, listener calls 0, forbidden API calls 0, and
  mounted false;
- mounted entry references to `cross_lag_evidence_card`: 0;
- lean list/dry-run: check_count 10, planned 10, completed 0, executed 0,
  reused 0, C4 status `DRY_RUN`, runtime mutations false, paper authorization
  false, and live order permission false.

Implementation fingerprints:

- JavaScript: `9B1BEEF054D8D510D232785B433A0D0D04AFE2FD228E099394ADCB08E0B4AE77`;
- CSS: `C7593124DB58A7821117ECE1F486443D6DA2C44CC7C6714F7CB2AA0703924E30`;
- tests: `16312F4246F9D0419B3F3E1BFCB0F5431085701F5ECFD30B2B53D83A756D5A97`;
- lean runner: `52006167B451FA589532EC61EA34B6FF6B8AFFBDDB89B0BFC2623405B87F5A0A`.

The existing `app.js`, `evidence_presentation.js`, evidence suite v13,
`index.html`, and main stylesheet fingerprints remained unchanged throughout C4
implementation. No service adapter, endpoint, route, import, stylesheet link,
mount point, pointer update, scheduler, or publication path was added.

Because C4 remains absent from the public application chain, immutable C3 v1
continues to expose `CROSS_LAG_C4_PRESENTATION_NOT_IMPLEMENTED`. Any future
adapter, blocker transition, or mount requires a separately versioned design and
review. C4 evidence remains descriptive only and creates no formal, current,
profitability, paper, or live authority.
