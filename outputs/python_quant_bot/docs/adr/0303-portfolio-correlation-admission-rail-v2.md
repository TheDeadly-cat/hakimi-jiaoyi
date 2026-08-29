# ADR 0303: Portfolio correlation admission rail v2

## Status

Accepted as an additive, isolated, unmounted presentation consumer and
stylesheet. It is not registered into the application, HTML, route, browser,
current admission, paper authority, or live authority.

## Context

ADR0302 freezes the v2 Python/JavaScript delivery assets and exact envelope
binding. The existing v1 rail cannot consume the ADR0301 bounded payload and
does not expose the common-universe tier that closes the proven ADR0299
cross-universe splice gap.

Reusing the v1 rail unchanged would hide the most important v2 decision.
Expanding the existing v7 risk card would duplicate its concentration and
effective-diversification responsibility. A compact v2 admission rail remains
the correct presentation boundary.

## Decision

Add three isolated assets:

- `evidence_portfolio_correlation_admission_rail_v2.js`;
- `evidence_portfolio_correlation_admission_rail_v2.css`; and
- `evidence_portfolio_correlation_admission_rail_v2.test.js`.

The JavaScript consumer accepts only an exact ADR0301 delivery envelope through
the registered delivery adapter. It extracts the bounded payload in memory and
builds an immutable view model. It never consumes a raw v2 candidate, source
report, correlation document, strategy identity, or symbol list.

The rail exposes seven ordered tiers:

1. `INPUT_SNAPSHOT`
2. `INPUT_IDENTITY`
3. `REPORT_UNIVERSE`
4. `CORRELATION_PREREGISTRATION`
5. `COMMON_UNIVERSE`
6. `V1_ADMISSION`
7. `PERMISSION`

It also preserves the neutral governance order:

`SOURCE -> GAP -> MATURITY -> PERMISSION`

An exact local pass is labeled `LOCAL CLEAR`. Any valid block is labeled
`LOCAL BLOCK`. Unknown or forged input exposes no metrics and keeps permission
`UNAUTHORIZED`.

## Visual direction

The visual language is a cool correlation drafting table rather than a copy of
the v1 warm ledger. A report-universe track and a correlation-preregistration
track converge on a clipped `COMMON UNIVERSE` lock before continuing to v1.
This handshake is the single signature element and encodes the statistical
contract instead of decorating it.

The palette uses deep-sea ink, cool mineral canvas, tidal teal for local exact
evidence, rust for blockers, and a restrained survey-marker yellow. Fraunces is
limited to the title; IBM Plex Sans Condensed and IBM Plex Mono carry evidence
and utility text. Responsive layouts collapse the handshake and evidence grids
vertically. Motion is limited to one entry, track draw, and gate lock sequence,
with an explicit reduced-motion override.

No browser or screenshot claim is made because the asset remains unmounted and
browser execution is not authorized in this slice.

## Consumer-first activation order

1. Keep ADR0301 and ADR0302 frozen.
2. Validate PASS, common-universe BLOCK, v1 BLOCK, and UNKNOWN view models in
   Node without DOM.
3. Register exact rail JavaScript, isolated stylesheet, Node test, and ADR0303
   hashes in a separate version.
4. Preregister application load order without editing app or HTML.
5. Review an unmounted render descriptor and neutral copy independently.
6. Only a later explicit migration may change host imports or current consumers.

No step automatically activates the next step.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Exact local pass envelope | bounded `LOCAL CLEAR`; permission unauthorized |
| Common-universe mismatch | handshake gate `BLOCK`; v1 `NOT_EVALUATED` |
| Matching universe with v1 block | common gate `PASS`; v1 blocking tier visible |
| Envelope/payload hash drift | `SOURCE UNKNOWN`; no metrics |
| Forged blocker text after reseal | adapter rejection; no markup injection |
| Identity or symbol leakage | absent from view model and markup |
| Permission promotion | adapter rejection |
| Reduced-motion preference | animations disabled |
| Narrow viewport | handshake and grids collapse to one column |

## Non-duplication boundary

ADR0303 does not reproduce v2 admission, delivery, extraction, receipt, or
portfolio-risk metrics. It consumes only the ADR0301 bounded payload. It adds no
endpoint, route, source provider, host patch, current writer, or execution path.

## Permission and evidence boundary

Production JavaScript creates a string render candidate only. It performs no
DOM, browser, network, storage, service, scheduler, writer, publication, or
trading operation. The stylesheet is isolated and does not modify or import the
protected global stylesheet.

Node render tests are not browser visual evidence. Local clear or block states
do not prove market quality, profitability, fresh holdout maturity, forward
observation, consumer activation, release approval, paper authority, or live
authority.

The public natural-forward evidence chain remains:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 is unchanged and is
not reissued by this work.
