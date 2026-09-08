# Pure Synthetic Strategy Baseline

> Every number below is SYNTHETIC_OBSERVATION_ONLY. It is not evidence of real-market performance or permission to trade.

- Nested dependency lock bound: `true`
- Dependency lock SHA-256: `2e12c00f613160e974a3c94f23ee2b058f6fed4ae7843d7747b318173d65d320`
- Nested Git worktree clean: `false`

## SOURCE

- Fixture: `deterministic-composite-stock-daily-v1`
- Dataset SHA-256: `920583bc43df033eec001af19c015c8d189e9955e60fa0963998f7ed71043226`
- Bundle SHA-256: `828d5e492fc1579229a9725d43e7bfa6f70748a7f6b1b1519e73deb15472fb75`
- Data source: pure deterministic in-memory OHLCV; no network, cache, database, or runtime artifact.
- Protocol: Train 200 rows -> Purge 10 -> Validation 180 -> Embargo 10 -> Frozen 200.
- Runs: 32 preregistered and executed in one synthetic evaluation batch.

### Frozen benchmarks

| Benchmark | Total return | Max drawdown | Observation class |
| --- | ---: | ---: | --- |
| cash | 0.0000% | 0.0000% | SYNTHETIC_OBSERVATION_ONLY |
| buy_and_hold | -1.0915% | 4.0903% | SYNTHETIC_OBSERVATION_ONLY |

### Registered strategy observations

| Family | Strategy | Train | Validation | Frozen 1x | Frozen 2x | Frozen 3x |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| RANGE | bollinger | -1.6988% | 0.3833% | -0.1094% | -0.2635% | -0.4173% |
| TREND | dual_ma | -2.3207% | 0.0000% | -0.7796% | -0.8093% | -0.8389% |
| RANGE | grid | 3.0719% | 0.0000% | -3.2833% | -3.4141% | -3.5446% |
| TREND | macd | 3.4710% | 4.0857% | -0.8142% | -1.0222% | -1.2298% |
| TREND | momentum | -3.3912% | 4.7998% | -2.0062% | -2.2320% | -2.4574% |
| RANGE | rsi | -0.0850% | 0.4473% | 1.2436% | 0.9741% | 0.7053% |

## GAP

- `REAL_MARKET_DATA_NOT_USED`
- `FORMAL_FROZEN_BLIND_TEST_NOT_EXECUTED`
- `WALK_FORWARD_NOT_EXECUTED`
- `PARAMETER_STABILITY_NOT_EXECUTED`
- `MULTIPLE_TESTING_NOT_EXECUTED`
- `ENSEMBLE_STRATEGY_NOT_IMPLEMENTED`
- `SOURCE_COMMIT_NOT_BOUND_FOR_UNCOMMITTED_SLICE`

- `ENSEMBLE` has no registered implementation and no report was fabricated.
- Frozen observations are synthetic and do not constitute a formal blind test.

## MATURITY

- Bundle status: `BLOCK`
- Maturity: `SYNTHETIC_BASELINE_ONLY`
- RANGE reports: `PARTIAL`
- TREND reports: `PARTIAL`
- ENSEMBLE report: `GAP`

## PERMISSION

- Profitability proven: `false`
- Formal blind test complete: `false`
- Paper authorized: `false`
- Live authorized: `false`
- Order entry authorized: `false`
