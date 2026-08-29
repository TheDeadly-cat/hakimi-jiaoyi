# ADR 0183: Shadow readiness public projection and evidence-stair card

- Status: Accepted as detached public projection and unmounted UI candidate
- Date: 2026-08-22
- Scope: Redacted projection plus static card only

## Context

ADR0181 provides a fully reverified 14-input local readiness envelope.  ADR0182
pins that contract while deliberately leaving the evidence instance unbound.  The
static frontend contains portfolio-risk geometry and session-freshness candidates,
but no ADR0181 or ADR0182 binding exists in `app.js`, `index.html`, or another card.

Passing either full source document directly to JavaScript would duplicate backend
verification boundaries and expose more lineage than the UI needs.

## Decision

Add a Python public projection that independently reverifies ADR0181 and ADR0182,
checks schema/fingerprint/count/maturity pin alignment, and emits only:

- source schema and document hashes;
- 14 required and 14 locally verified input counts;
- signed clock source count;
- the three preserved local blocker closures;
- readiness and preregistration blocker counts;
- explicit false values for evidence binding, external authority, current time,
  consumer execution, runtime use, profitability, paper, and live authority.

Add an unmounted UMD card and stylesheet that consume only this projection.  The
visual metaphor is a 14-step evidence stair beside a dark gap ledger.  It preserves
the fixed `SOURCE -> GAP -> MATURITY -> PERMISSION` order.

## Public states

| Axis | Observed value |
| --- | --- |
| SOURCE | `LOCAL_EVIDENCE_VERIFIED` |
| GAP | `EXTERNAL_TRUST_AND_RUNTIME_BINDING_UNPROVEN` |
| MATURITY | `UNMOUNTED_CANDIDATE` |
| PERMISSION | `UNAUTHORIZED` |

`OBSERVED` means that the two local source contracts were publicly reverified.  It
does not mean READY, current, evidence-bound, externally trusted, or executable.

Invalid, tampered, mixed, or extended contexts project to `UNKNOWN`.  A completely
absent input set projects to `NOT_SUPPLIED`.  Both remain unauthorized.

## Redaction and visual safety

The projection omits source documents, verification contexts, public keys,
signatures, receipts, raw correlations, and provider payloads.  The card displays
`CONTRACT PIN != EVIDENCE BINDING`, `PAPER / LIVE 未授权`, and explicit external
authority/runtime gaps.  Custom card copy is HTML escaped.

The stylesheet includes responsive breakpoints, reduced-motion behavior, forced
colors support, and no purple-default palette.  The card is not referenced by
`app.js` or `index.html` and therefore is not mounted.

## Compatibility and authority

No existing projection, card, route, or frontend mount is modified.  The
natural-forward chain remains:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 remains publicly `UNKNOWN`.  Pointer-v2 fields, hash contract, and
non-reissuance behavior remain unchanged.  No profitability or trading authority
is implied.

## Validation boundary

Validation is limited to synthetic Python contracts, static Node tests, JavaScript
syntax checks, an independent public API matrix, and in-memory Python compilation.
No browser or visual QA claim is made.  No runtime, service, database, cache,
network, scheduler, return backtest, formal blind test, paper task, or live task is
used.
