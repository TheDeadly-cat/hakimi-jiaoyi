# ADR 0464: Portfolio robustness identity and recomputation v1

- Status: Accepted
- Date: 2026-08-25
- Scope: Diagnostic robustness assessment construction and verification

## Context

The v2 builder admitted seven copies of one favorable parameter result and a
single favorable ablation as `ROBUSTNESS_PASS`. The v2 verifier trusted embedded
checks after validating only the outer unkeyed hash. A report with seven negative
parameter results and `parameter_selection_allowed=true` still verified `PASS`
after the outer hash was recomputed.

## Decision

Upgrade new reports to `portfolio-robustness-diagnostic-v3` and introduce
`portfolio-robustness-identity-v1`:

1. Parameter diagnostics require exactly seven unique labels and unique non-empty
   run hashes.
2. Ablation diagnostics require at least four unique identities, making the 75%
   threshold meaningful.
3. Required capital labels must be present and their underlying results must be
   successful, scheduled, finite, and positive.
4. Parameter drawdown must be finite and inside `[0, 15)`.
5. Builder and verifier share one fact derivation path. The verifier recomputes
   checks, issues, warnings, and summaries from embedded diagnostics.
6. Diagnostic-only, no-parameter-selection, manual-review, paper-denied, and
   live-denied flags are strict verifier requirements.
7. Non-object reports return structured `BLOCK`.

No external exact v2 consumer was found. Existing v2 reports are not rewritten.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Seven duplicate parameter labels | BLOCK |
| One favorable ablation | BLOCK |
| Unique labels with duplicate run hashes | BLOCK |
| Positive capital metric with `ok=false` | BLOCK |
| Resealed negative results with stale PASS checks | Verifier BLOCK |
| Resealed parameter-selection authority | Verifier BLOCK |
| Valid v3 diagnostic | PASS, research-only |

## Boundaries

- Tests construct diagnostic dictionaries only; no robustness backtest is run.
- No formal report, candidate, registry, market task, service, browser, scheduler,
  runtime database, paper order, or live order is accessed or started.
- Robustness PASS remains diagnostic evidence, not profitability proof or trading
  authority.
