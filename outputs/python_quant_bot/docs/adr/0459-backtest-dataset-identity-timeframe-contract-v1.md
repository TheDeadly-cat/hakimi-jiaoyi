# ADR 0459: Backtest dataset identity and timeframe contract v1

- Status: Accepted
- Date: 2026-08-25
- Scope: Backtest dataset admission only

## Context

`prepare_backtest_dataset` could emit a `PASS` manifest with empty `symbol` and
`source`. It also treated an unknown timeframe as not subject to daily
continuity checks. A synthetic crypto dataset with a missing daily bar was
blocked under `1D` but passed under `not-a-timeframe`.

No external source consumer was found to require the exact
`backtest-dataset-v4` identifier. Existing explicit callers use `1D` and `1h`.

## Decision

Upgrade new dataset manifests to `backtest-dataset-v5` and introduce two
versioned admission sub-contracts:

1. `backtest-dataset-identity-v1` requires canonical, non-empty string values
   for `symbol` and `source`.
2. `backtest-timeframe-v1` accepts daily aliases, positive minute/hour/week
   durations, and normalizes them to a stable lowercase representation.
3. Unknown, non-string, non-finite, non-positive, and currently unmodelled
   multi-day durations fail closed.
4. Identity and timeframe blockers are recorded in the dataset manifest before
   any strategy execution can occur.
5. Existing valid OHLCV normalization, hashing, execution, and performance
   calculations remain unchanged.

Producer activation applies only to newly prepared datasets. Existing v4
artifacts and the current natural-forward chain are not rewritten or reissued.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Empty symbol or source | Dataset BLOCK with explicit missing identity |
| Non-string identity | Dataset BLOCK with explicit type issue |
| Leading or trailing identity whitespace | Dataset BLOCK as noncanonical |
| Unknown timeframe with missing daily bar | Dataset BLOCK, never continuity bypass |
| `1D`, `daily`, `1h`, `60m`, `1w` | Normalize and retain existing admission behavior |
| `2D` before multi-day modeling exists | Dataset BLOCK |

## Boundaries

- This change does not run a backtest or produce a profitability result.
- Tests use synthetic in-memory OHLCV rows only.
- No network, runtime, database, cache, log, secret, service, browser, scheduler,
  paper order, or live order is accessed.
- Paper/live remain unauthorized, and pointer-v2 is unchanged.
