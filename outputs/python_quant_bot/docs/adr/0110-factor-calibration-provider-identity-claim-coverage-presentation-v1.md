# ADR0110: Detached provider-identity claim coverage presentation v1

## Status

Accepted as an unmounted, consumer-inactive presentation candidate. It is not imported by `app.js`, server, engine, CLI, current evidence, paper, or live paths.

## Context

ADR0108 verifies detached signed occurrence-cardinality and claimed time-window evidence without external trust. ADR0109 verifies a preregistered bounded checkpoint prefix while keeping uniqueness, freshness, replay absence, complete history, and authority false. Those contracts are precise but too dense for direct user-facing inspection.

## Decision

Add a sealed Python presentation envelope and a detached JS/CSS dossier card. The envelope reruns both source verifiers, binds the latest ADR0108 evaluation to the last ADR0109 item and checkpoint, rejects truth or authority promotion, and emits only presentation-safe hashes, identifiers, counts, claimed times, blockers, and four ordered axes:

1. `SOURCE`: signed detached claims.
2. `GAP`: external witness authority and index completeness remain open.
3. `MATURITY`: a bounded checkpoint prefix, not complete history.
4. `PERMISSION`: descriptive research only with paper/live locked.

The card uses a warm archival ledger visual language, a bounded-prefix rail, scoped CSS, semantic DOM construction through `textContent`, responsive layouts, and reduced-motion support. It contains no active import or mount point.

## Authority boundary

The display state is `SIGNED_CLAIMS_BOUND_BOUNDED_PREFIX_EXTERNAL_TRUST_GAP`, not an evidence or trading state. The envelope and card may not set uniqueness, freshness, replay absence, complete history, admission, current-pointer writes, paper authorization, or live-order permission to true. Missing, malformed, mismatched, or promoted source evidence renders UNKNOWN.

## Activation order

1. Validate Python and Node contracts independently and across serialized output.
2. Keep the component detached while external witness conformance remains unproven.
3. Require a separate UX and migration decision before any active import.
4. Preserve neutral SOURCE -> GAP -> MATURITY -> PERMISSION language after any future mount.

## Validation evidence (2026-10-04)

- Python sealed presentation contract: 20/20 PASS.
- Detached Node card contract: 8/8 PASS.
- Python-to-Node serialized positive/UNKNOWN boundary: PASS; four cross-language authority, axis-order, extra-field, and freshness-promotion drifts rejected.
- In-memory Python syntax compilation: 2/2 PASS.
- Node syntax checks: 2/2 PASS for the card and its contract test.
- Cross-lag factor calibration family: 904/904 PASS across 45 modules.
- Lean validation: 20 checks listed; dry-run planned 20, executed 0, runtime mutations false, paper false, live false.
- Corrected explicit active-source reference audit: 0 after excluding the candidate definition itself.

No browser, service, scheduler, runtime artifact, or active mount was used. This proves the detached envelope/card contracts and scoped responsive CSS, not browser-rendered visual quality or production integration. The display state remains `SIGNED_CLAIMS_BOUND_BOUNDED_PREFIX_EXTERNAL_TRUST_GAP`; uniqueness, freshness, replay absence, complete history, admission, pointer writes, paper, and live remain false.