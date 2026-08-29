# ADR 0225: Adapter-v6 downside-tail joint risk gate

## Status

Accepted as a synthetic, research-only joint gate candidate.

## Context

The current portfolio-risk chain covers common observation support, complete
link clusters, weighted effective cluster count, and multi-window partition
stability. Adapter-v5 composes adapter-v4 with the multi-window gate.

Adapter-v5 has no downside-tail input. A pure synthetic case demonstrates the
gap: adapter-v5 returns PASS while a preregistered downside-tail evaluation on
the same three trade symbols returns BLOCK because all three assets share the
same lowest-fifth observations.

Low full-sample Pearson correlation does not rule out common downside events.
The repository already contains a strict downside-tail gate using exact shared
observation IDs, preregistered strata, lowest-fifth tails, a minimum overlap
ratio, a one-sided hypergeometric test, and Bonferroni family correction. That
algorithm should be consumed rather than rewritten.

## Decision

Introduce
strategy_correlation_cluster_portfolio_risk_adapter_v6.py.

Adapter-v6 accepts:

1. An adapter-v5 document.
2. A downside-tail registration.
3. A downside-tail evaluation.
4. The complete adapter-v5 verification context.
5. Exact expected registration and evaluation hashes.

It does not accept aligned observations, raw returns, pair results, overlap
counts, p-values, precomputed tail metrics, or runtime execution inputs.

Adapter-v6 independently verifies adapter-v5, the tail registration, and the
tail evaluation. It derives the unique trade symbol set from adapter-v5's
already verified weighted-budget context and requires exact equality with the
tail registration identity set and identity-set hash.

## Decision rule

1. Any unverified source, hash mismatch, UNKNOWN tail source, or identity-set
   mismatch blocks.
2. An adapter-v5 BLOCK remains BLOCK.
3. A downside-tail BLOCK overrides an adapter-v5 PASS.
4. PASS requires adapter-v5 PASS and an OBSERVED downside-tail PASS.

The first candidate does not claim a risk-reduction joint exemption. Existing
adapter-v4 and stability fixtures each support risk reduction, but their
independently valid documents do not currently cross-bind into an adapter-v5
known trade identity. Until that gap is closed, adapter-v6 applies the
conservative tail rule to every verified adapter-v5 PASS.

## Adversarial matrix

1. Reproduce adapter-v5 PASS plus downside-tail BLOCK and require v6 BLOCK.
2. Require tail-clear plus adapter-v5 PASS for v6 PASS.
3. Preserve adapter-v5 component BLOCK.
4. Block an exactly sealed UNKNOWN tail source.
5. Block registration and evaluation hash substitutions.
6. Block a same-count but different tail identity set.
7. Block an adapter trade-symbol context splice.
8. Block resealed tail authority promotion.
9. Block resealed adapter-v5 authority promotion.
10. Explicitly deny risk-reduction joint exemption.
11. Emit summary hashes only, without observations, pair rows, or positions.
12. Reject resealed adapter-v6 authority tamper.
13. Pin adapter-v5, downside-tail gate, and strict-canonical implementations.
14. Keep profitability, runtime, paper, live, writer, and current authority
    false.

All cases use synthetic in-memory observations and existing contract fixtures.
No historical market data, runtime store, database, cache, log, secret,
service, browser, scheduler, backtest, market task, or trading path is used.

## Activation

Adapter-v6 is not wired into adapter-v5, a server route, current pointer,
paper trading, or live trading. Consumer-first follow-up requires a versioned
registration and presentation candidate before any separate activation
discussion.
