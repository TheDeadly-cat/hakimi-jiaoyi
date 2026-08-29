# ADR0509: Frozen Evaluation Protocol and Cost Stress Report v1

## Status

The base producer/verifier is current on GitHub and was consumed by successful
remote research-contract CI run `33258500942`. The deterministic Markdown
renderer extension is accepted locally but remains unpublished. Neither surface
is exposed by the current CLI.

## Context

ADR0504 seals one backtest result and understands evaluation-role labels, but the
active product had no producer for Train/Validation/Frozen Test partitions and no
consumer for purge/embargo, fixed benchmarks, or cost stress. The active CLI
therefore always generated UNCLASSIFIED results. A label-only role gate is not a
frozen-OOS evaluation report.

## Decision

Add `src/hakimi_research/frozen_evaluation.py` with two exact contracts:

1. `frozen-evaluation-protocol-v1` binds canonical full-OHLCV identity, complete
   config, strategy parameters/version, random seed, and the fixed order
   TRAIN -> PURGE -> VALIDATION -> EMBARGO -> FROZEN_TEST.
2. Each evaluation partition requires at least 35 rows; purge and embargo each
   require at least one excluded row. Counts must consume the dataset exactly.
3. Cost scenarios are fixed before evaluation as BASE, DOUBLE_COST, TRIPLE_COST.
4. Benchmarks are fixed as CASH and ENGINE_BUY_AND_HOLD with explicit versions.
5. `frozen-evaluation-report-v1` runs TRAIN at base cost, VALIDATION and
   FROZEN_TEST at all three costs, and both benchmarks on both OOS roles.
6. Every nested run carries the exact protocol hash/role and must pass the
   existing reproducible-experiment-manifest-v1 verifier.
7. `frozen-evaluation-markdown-v1` renders only a verified report, normalizes run
   order, performs no file I/O, and presents SOURCE -> GAP -> MATURITY ->
   PERMISSION without adding a new evidence or authority schema.

## Calibrated evidence scope

The local builder has access to the full historical or synthetic frame. It does
not prove blindness, external preregistration chronology, single consumption, or
natural-forward evidence. The report therefore always returns BLOCK with these
four structural blockers even when every nested experiment manifest passes.

The report may contain performance measurements as evidence fields, but it sets
parameter selection, ranking, profitability proof, paper, live, and order
authority to false. No result is promoted by this contract.

## Consumer-first activation

1. Build and seal the protocol without adding a CLI command.
2. Verify partition, dataset, config, strategy, benchmark, and cost identity.
3. Build the standard report using fresh strategy/risk instances per run.
4. Verify every nested ADR0504 manifest and aggregate report hash.
5. Render a deterministic human-readable projection that names coverage gaps
   rather than treating the JSON matrix as a complete research conclusion.
6. Keep the library dormant until a separate CLI
   activation decision.

## Adversarial matrix

The contract rejects boolean or short counts, missing gaps, count mismatch,
duplicate/non-timezone indexes, invalid OHLC geometry, data/config drift,
partition resealing, result tampering, authority resealing, incomplete run
matrices, and any attempt to treat a nested Frozen Test PASS as selection or
execution authority. The renderer additionally rejects unverified inputs and
normalizes otherwise valid run ordering; it never renders READY or a positive
permission field.

## Local acceptance target

- Frozen evaluation and renderer adversarial matrix: 14/14 PASS.
- Targeted research contracts: 92/92 PASS.
- Python syntax for two affected code files: 2/2 PASS.
- Deterministic input verifier: 8/8 PASS.
- `git diff --check`: PASS.
- No real-data backtest, formal blind test, service, browser, scheduler,
  paper/live, order, or publication action is executed.
