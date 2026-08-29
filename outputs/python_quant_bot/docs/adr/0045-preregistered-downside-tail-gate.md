# ADR 0045: Preregistered downside-tail gate

## Status

Candidate contract implemented. It is descriptive, synthetic-only, and not formal/current.

## Gap

Full-window and temporal Pearson checks can miss two return streams that have low ordinary correlation but repeatedly enter their own downside tails on the same observations. Counting those streams as independent would overstate the number of distinct strategy or asset votes.

## Decision

Add a separate candidate gate over exact shared observation ids and preregistered strata.

- Test only pairs assigned to different preregistered strata. Same-stratum pairs are already non-independent and are not recounted.
- Select the lowest ceiling 20 percent of observations per identity, with at least 60 aligned observations and 12 tail events.
- Block ambiguous rank selection when a return tie crosses the tail boundary.
- Measure joint tail overlap with a one-sided exact hypergeometric test.
- Apply Bonferroni correction over every cross-stratum pair.
- Mark a pair tail-coupled only when overlap is at least one half and the family-adjusted p-value is at most 0.05.
- Block on malformed, incomplete, non-finite, aliased, hash-mismatched, undersampled, or ambiguous input.
- A PASS clears only this candidate blocker. It never proves independence and cannot authorize counting, current admission, paper, live, or profitability claims.

All protocol parameters are fixed in a sealed candidate registration. Resealing a post-hoc parameter or authority change does not satisfy the verifier because the document must equal the rebuilt versioned contract.

## Evidence boundary

The first proof is pure synthetic data. One adversarial fixture has absolute Pearson correlation below 0.2 while all 12 downside-tail observations overlap; the new gate blocks it. No market data, backtest, runtime, database, service, browser, scheduler, or trading task is involved.

The evaluation exposes aggregate pair diagnostics but never emits observation ids or raw returns. A future public projection must additionally redact identity and hash fields.

## Consumer-first sequence

1. Candidate gate and adversarial tests.
2. Read-only report consumer bound to this exact registration and evaluation hash.
3. Protocol and registry projection with explicit migration blockers.
4. Redacted public summary and optional unmounted SOURCE -> GAP -> MATURITY -> PERMISSION view.
5. Formal migration only after independent review; no automatic current switch or artifact reissue.
