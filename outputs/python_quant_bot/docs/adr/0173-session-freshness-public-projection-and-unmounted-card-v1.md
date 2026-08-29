# ADR0173: Session-freshness public projection and unmounted ledger card v1

## Status

Accepted as an additive, unregistered presentation candidate. It is absent from
the application, index, HTTP routes, runtime consumers, current evidence,
paper, and live paths.

## Gap proof

ADR0167's frozen public projection summarizes portfolio exposure, ticket count,
effective independent bets, and risk-gate outcomes. Its summary has no session
lag, cutoff, reference time, clock quorum, or external time-authority field.
ADR0172 can produce these facts, but no public consumer exists. Modifying
ADR0167 v1 would invalidate its exact-rebuild fingerprint and Node API lock.

## Decision

Add a companion Python projection that exact-verifies ADR0172 registration and
evaluation from private source inputs. A complete five-hash lineage is required
before SOURCE can be `VERIFIED`. The public output contains only cutoff and
reference labels, maximum completed-session lag, preregistered limit, calendar
count, clock quality/source count, blocker count, and fixed authority gaps.

The pipeline is fixed to:

1. SOURCE: `VERIFIED`, `UNKNOWN`, or `NOT_SUPPLIED`.
2. GAP: local lag within policy with external time-authority gap, session-lag
   policy gap, unverified evidence gap, `UNKNOWN`, or `NOT_SUPPLIED`.
3. MATURITY: `UNMOUNTED_CANDIDATE`.
4. PERMISSION: `UNAUTHORIZED`.

Add a standalone UMD browser component and stylesheet. Its signature element is
a perforated completed-session ruler between cutoff and reference, with the
observed lag and preregistered boundary encoded as different marker shapes. The
palette uses mineral paper, oxide blue, brass, and rust; no profit-green,
`READY`, profitability, or permission-positive copy is present. Responsive,
reduced-motion, forced-color, escaping, immutable-input, and narrow-API
contracts are included.

## Redaction and authority

The projection excludes source documents, prices, matrices, observation
batches, clock endpoints/sources, raw calendar IDs, per-calendar lag evidence,
and correlations. `external_clock_authority_authenticated`, external freshness
proof, runtime mount, shadow activation, current admission, migration, writer,
paper, and live remain false.

## Consumer-first order

1. Keep projection and card unmounted and validate Python/Node exact contracts.
2. Add a sealed cross-runtime binding and independent static review.
3. Authenticate external time-authority roles separately.
4. Register a versioned shadow-only HTTP consumer with operational controls.
5. Perform authorized browser visual review before any DOM mount decision.
6. Require a separate current migration decision; paper/live remain locked.

## Validation scope

The targeted matrix covers within-policy authority gap, exact stale policy gap,
invalid source evidence, not-supplied state, resealed evaluation tamper,
redaction, authority escalation, stage reorder, scalar aliases, escaping,
input immutability, UMD parity, responsive/reduced-motion/forced-color CSS,
suite-v17 mount absence, and a Python-to-Node projection invocation.

The natural-forward chain and pointer-v2 contracts are unchanged. This work is
not browser visual evidence, runtime evidence, market truth, freshness proof,
profitability evidence, paper authority, or live authority.

## Validation evidence

- Explicit NOT_SUPPLIED regression: 1/1 PASS.
- Python projection matrix, including Python-to-Node view-model consumption:
  10/10 PASS.
- New card and suite-v17 Node matrix: 14/14 PASS.
- ADR0173, ADR0172, and ADR0167 Python dependency matrix: 41/41 PASS.
- ADR0167/ADR0173 card and suite-v16/v17 Node matrix: 27/27 PASS.
- Node syntax checks: 3/3 PASS.
- In-memory Python compilation: 2/2 PASS.

These checks prove contract shape, escaping, static responsive/accessibility
rules, cross-runtime consumption, and mount absence only. No service, DOM,
browser process, screenshot, runtime asset, or market source was used.
