# ADR 0296: Static presentation unmounted render review v1

## Status

Accepted as a local, automated, no-DOM behavior review. It is not an external
independent review, browser review, host patch, or mount authorization.

## Problem

ADR0295 proves that exact host patch strings can apply and reverse in memory.
Its planned app fragment has only been syntax-checked and exercised on a missing
dependency path. The clear, high-correlation block, and exact unknown delivery
states still need one cross-runtime behavioral review before any host-write
request could be considered.

This review must not reuse the older independent-review claim contract. A local
Node process cannot authenticate reviewer identity, prove process independence,
verify an external signature, or close the independent-review blocker.

## Decision

Add `static-presentation-unmounted-render-review-receipt-v1` as an isolated UMD
and CommonJS module. It requires exact ADR0295 preregistration, patch-plan, and
app-fragment hashes before invoking the planned host API.

The reviewer independently rebuilds the expected host render candidate from the
ADR0292 delivery adapter and ADR0290 rail. It compares the observed candidate by
strict canonical JSON, validates `SOURCE -> GAP -> MATURITY -> PERMISSION`,
rejects `READY` wording, and emits a sealed hash-only receipt containing:

- envelope, source, delivery-receipt, and markup hashes;
- markup length;
- rail schema and static fingerprint;
- neutral status label and stage states; and
- explicit no-DOM, no-mount, no-current, and no-profitability facts.

Raw envelope, source candidate, and markup are not embedded. The module refuses
to produce a known review when a DOM environment is present.

The Node contract test generates clear, high-correlation block, and exact
unknown envelopes from the existing Python synthetic fixture. It evaluates the
exact ADR0295 app fragment in the Node global, then reviews its output using the
real strict-canonical, rail, and delivery modules.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Exact local clear envelope | blocked no-DOM receipt with `LOCAL CLEAR` |
| Exact high-correlation block | blocked no-DOM receipt with `LOCAL BLOCK` |
| Exact unknown envelope | UNKNOWN with no markup hash |
| Invalid envelope | UNKNOWN |
| Review-context hash drift | UNKNOWN before host invocation |
| Host markup substitution | UNKNOWN |
| Host API exception | contained as UNKNOWN |
| Receipt authority promotion after reseal | verifier rejection |
| DOM-capable environment | UNKNOWN |

## Consumer-first activation order

1. Exact ADR0295 patch preregistration and app fragment.
2. Exact Python delivery envelope.
3. Exact planned host render candidate in a no-DOM process.
4. Local hash-only behavior review through ADR0296.
5. Future external independent review request and authenticated attestation.
6. Future explicit host-write authorization.
7. Future patch application and rollback executor binding.
8. Future browser visual review.
9. Future DOM mount and current activation if separately authorized.

No step authorizes or automatically performs the next step.

## Permission and evidence boundary

Known local behavior remains `BLOCKED`. External independent review completion,
host patch application, browser execution, visual review, DOM mount, runtime
loading, current activation, paper authorization, live orders, and writer
authority remain false.

This work is not browser evidence, visual validation, external independent
review, market evidence, profitability evidence, release approval, paper/live
authority, or current activation. No runtime, cache, database, log, key,
service, scheduler, browser, backtest, or trading task is accessed or started.

The public natural-forward chain remains:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 is unchanged and is
not reissued by this work.
