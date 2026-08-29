# ADR0467: Multi-window return-panel lineage adapter v4

## Status

Accepted as an unmounted, synthetic, research-only adapter on 2026-08-25. It
does not connect a real market source, switch current, or authorize paper/live.

## Existing-chain audit and synthetic gap proof

The existing common-observation basis adapter-v9 and membership adapter-v10 are
specific to the older portfolio-risk/edge chain. Their synthetic PASS documents
declare `raw_samples_recomputed=false`; v9 marks provenance-declaration-only and
v10 marks membership-commitment-only. Their evaluator signatures accept only
older adapter/gate documents and verification contexts, not a return panel.

They therefore cannot prove that ADR0465 matrices were calculated from the same
actual observations. Reusing them would substitute a commitment claim for raw
recomputation and preserve the consumer-v3 lineage gap.

## Decision

Add a narrow adapter-v4 that:

1. Defines a bounded completed-daily-return panel with exact common symbol
   membership, strictly increasing ISO dates, finite native returns, and a final
   row equal to the fixed cutoff.
2. Hashes the complete panel while keeping all raw rows out of adapter output.
3. Structurally preregisters panel hash, timeframe, cutoff, exact consumer-v3
   hash lineage, source-v2 window hashes, correlation method, and precision.
4. Declares external chronology unproven. The consumer must supply the expected
   lineage-preregistration hash.
5. Recomputes Pearson correlation from the common last N panel rows for every
   pair in every 20/60/120 window, rounded to twelve decimals.
6. Rejects incomplete membership, future rows after cutoff, insufficient rows,
   non-finite values, zero variance, matrix substitution, and source splicing.
7. Requires strict equality between every recomputed matrix and the matrix used
   by the exact ADR0466 consumer-v3 document.
8. Preserves an exact consumer BLOCK as BLOCK; any lineage or exact-verification
   failure is UNKNOWN with no partial summary.
9. Keeps current, runtime, writer, paper, and live authority false.

## Consumer-first order

1. Keep source-v2 and consumer-v3 unmounted.
2. Land this raw-recomputation adapter and test only bounded synthetic panels.
3. Add a separately versioned, read-only market-data envelope adapter only after
   source identity, dataset identity, cutoff, timeframe, and row semantics are
   independently specified.
4. Require independently anchored preregistration chronology before natural
   forward evidence can consume the adapter.
5. Run shadow dual-read only with separate authorization.
6. Make any current, writer, paper, or live decision separately. No step
   activates or authorizes the next step.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Exact common 130-row panel | three matrices recomputed and adapter PASS |
| Exact consumer window BLOCK | lineage passes and adapter preserves BLOCK |
| Raw return changed with new panel hash but old matrices | UNKNOWN |
| Resealed matrix correlation substitution | UNKNOWN |
| Missing symbol membership | panel builder rejects |
| Row after cutoff | panel builder rejects |
| Zero-variance series | Pearson derivation rejects |
| Wrong lineage pin or spliced source | UNKNOWN with no summary |
| Resealed aggregate count or authority promotion | exact verifier rejects |
| Input mutation attempt | caller inputs remain unchanged |

## Boundary

All rows are pure synthetic values. No historical or real-market data,
profitability backtest, G50/G51, formal blind task, service, browser, scheduler,
publication, paper execution, or live execution is used.

The public natural-forward chain remains:

audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 is unchanged and is
not reissued.
