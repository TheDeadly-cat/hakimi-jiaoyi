# ADR 0254: Stratified multi-window presentation-v8

## Status

Accepted as an unmounted, neutral presentation candidate on 2026-08-23.

## Observed gap

Presentation-v7 projects the exact portfolio-risk-v6 and one budget-v3 anchor.
ADR0253 added adapter-v7, which allows a long-window stratified BLOCK to override
that anchor PASS, but adapter-v7 had no presentation consumer.

A pure synthetic read-only chain reused the exact same budget-v3 anchor for both
paths and proved five predicates:

1. Presentation-v7 reported its anchor-local joint status as PASS.
2. Gate-v2 blocked because the long-window budget-v3 blocked.
3. Adapter-v7 overrode the anchor PASS with BLOCK.
4. Presentation-v7 had no adapter-v7 input.
5. Presentation-v7 had no multi-window summary.

Therefore a consumer reading only v7 could omit an already verified, more
conservative multi-window result.

## Decision

Add a separate presentation-v8 without modifying presentation-v7, adapter-v7,
HTTP candidates, cards, routes, current, or evidence pointers.

Presentation-v8 independently exact-verifies presentation-v7 and adapter-v7. It
then requires the following cross-bindings:

1. Presentation and adapter budget-v3 documents are exactly identical.
2. Their budget-v3 verification contexts are exactly identical.
3. Presentation budget hash equals the adapter anchor budget hash.
4. Anchor budget status and decision agree across both components.
5. Adapter gate-v2 hash equals the gate document supplied to its verifier.
6. Adapter and gate trade-identity hashes agree.

Unknown or spliced sources return a fully sealed unknown presentation with no
single-window or multi-window partial metrics. For known sources, adapter-v7
BLOCK overrides presentation-v7 local PASS. Otherwise any v7 local BLOCK is
preserved. Only both local components passing yields a local research PASS.

The outer presentation always remains `BLOCK` because it is unregistered and
unmounted. It projects only the existing bounded v7 risk summary and these gate
aggregates: registered/verified window counts, any-window block, partition and
strata-topology stability, conservative effective-strata minimum, worst-window
maximum stratum gross, and anchor ID. Window documents and window summaries are
not embedded.

## Neutral presentation order

`SOURCE -> GAP -> MATURITY -> PERMISSION`

`LOCAL CLEAR` means only that exact local research components passed. It never
means route readiness, profitability, current admission, paper authority, live
authority, or execution permission.

## Consumer-first activation order

1. Keep presentation-v8 standalone and validate pure synthetic contracts.
2. Define an unregistered HTTP candidate only after independent v8 review.
3. Define an unmounted neutral card only after the HTTP payload is frozen.
4. Require separate route, mount, current, paper, and live authorization.

This ADR authorizes only step 1.

## Adversarial matrix

| Case | Required result |
| --- | --- |
| v7 PASS and adapter-v7 PASS | Local PASS, outer BLOCK |
| v7 PASS and adapter-v7 BLOCK | Local BLOCK |
| v7 local BLOCK | Local BLOCK preserved |
| Budget document or context splice | UNKNOWN, no summaries |
| Budget hash/status/decision splice | UNKNOWN, no summaries |
| Gate hash or trade identity splice | UNKNOWN, no summaries |
| Extra context key or malformed receipt | UNKNOWN |
| Verifier exception | UNKNOWN |
| Re-sealed permission promotion | Exact verifier BLOCK |
| Known projection | Aggregate-only, no window documents |

## Authority and evidence boundary

Writer, registry, HTTP, runtime, current, paper, live, and execution authority
remain false. No source document, verification context, matrix, position, or
window document is embedded. Pure synthetic contracts do not prove market
stability, profitability, future performance, provider trust, or trading
authority. The natural-forward chain, legacy pack-v5 UNKNOWN behavior, and
pointer-v2 non-reissue contract are unchanged.
