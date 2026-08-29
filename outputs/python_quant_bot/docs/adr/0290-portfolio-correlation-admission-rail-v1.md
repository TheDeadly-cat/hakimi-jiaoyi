# ADR 0290: Portfolio correlation admission rail v1

## Status

Accepted as an isolated, unmounted presentation asset. No host import, HTML link,
route, runtime delivery, browser execution, or current activation is authorized.

## Non-duplication audit

The existing `portfolio-risk-stratified-budget-card-v7` already owns detailed
active-strata exposure, concentration, and effective-diversification metrics.
Adding another full correlation-risk card would duplicate that responsibility.

ADR0289 introduces a different presentation need: the ordered portfolio admission
handoff from base evidence through complete-link and preregistered strata, including
explicit `NOT_EVALUATED` downstream states. The new asset is therefore a compact
admission rail, not another portfolio-risk dashboard.

## Decision

Add three isolated static assets:

- `evidence_portfolio_correlation_admission_rail_v1.js`;
- `evidence_portfolio_correlation_admission_rail_v1.css`; and
- `evidence_portfolio_correlation_admission_rail_v1.test.js`.

The JavaScript verifier accepts only an exact, strictly hash-sealed
`portfolio-correlation-admission-v1` document with fixed permission locks, exact
keys, exact hash slots, and a valid tri-state dependency sequence. A failed tier
requires all dependent flow checks to be `null` and therefore `NOT_EVALUATED`.
The permission check remains independently visible and cannot be promoted by
resealing the candidate.

The rail presents two ordered views:

1. Eight admission tiers from `INPUT_IDENTITY` through `PERMISSION`.
2. The neutral public axes `SOURCE -> GAP -> MATURITY -> PERMISSION`.

Local `PASS` is displayed as `LOCAL CLEAR`, never as READY or authorization.
Unknown or malformed candidates expose no metrics and preserve an unauthorized
permission stage.

## Visual direction

The isolated stylesheet reuses the established editorial evidence language
without copying the v7 card layout. The rail uses warm paper, sea-green local
evidence, clay blockers, ruled ledger texture, asymmetric corners, a compact
eight-tier flow, and a separate four-axis governance spine. Typography follows
the existing Fraunces and IBM Plex family choices. Responsive layouts collapse
from four to two to one column. Optional entry motion is disabled when reduced
motion is requested.

This ADR makes no browser or screenshot claim because the asset remains unmounted
and no browser session is authorized in this slice.

## Consumer-first activation order

1. Produce and independently verify ADR0289 in Python.
2. Deliver the unchanged candidate to the JavaScript verifier through a separate
   versioned adapter.
3. Register the exact rail JavaScript, stylesheet, test, and strict-canonical hash.
4. Preregister an application import and stylesheet link without editing the host.
5. Review an unmounted render descriptor.
6. Only a later explicit migration may change current host imports or mounting.

No step automatically activates the next step.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Exact local pass | bounded `LOCAL CLEAR`, permission unauthorized |
| Complete-link block | strata tiers `NOT_EVALUATED` |
| Candidate hash substitution | UNKNOWN |
| Extra field after reseal | UNKNOWN |
| Permission promotion after reseal | UNKNOWN |
| Downstream PASS after upstream block | UNKNOWN |
| Adversarial identity or blocker text | HTML escaped |
| Missing candidate | UNKNOWN with no metrics |

## Evidence and permission boundary

The rail is descriptive, consumer-only, and unmounted. It does not prove market
quality, profitability, fresh holdout maturity, forward observation, paper/live
authorization, or release approval. It cannot register routes, import itself into
the application, mount DOM, execute a browser, mutate runtime state, or switch
`current`.

The public natural-forward chain remains:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 is unchanged and is
not reissued by this work.
