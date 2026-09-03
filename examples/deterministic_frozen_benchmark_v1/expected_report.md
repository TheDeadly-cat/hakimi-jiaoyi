# Hakimi Frozen Evaluation Report

Renderer: `frozen-evaluation-markdown-v9`

## SOURCE

- Report ID: `hfer-d850be4b62ac7252747c`
- Report SHA-256: `d850be4b62ac7252747ccb362096160c8fb82c496d520acdb9e8b90b944c5e76`
- Protocol ID: `hfep-69de4ce1fbb258a12db8`
- Protocol SHA-256: `69de4ce1fbb258a12db821f355cf7c82c98453f22c5f8f4a3d2b8ce82e00ee85`
- Dataset SHA-256: `1cf5fd0e59082042d42f4b42d4841a5f35f673126b93fca3bda4de46a0fbac35`
- Config SHA-256: `497ce27c761d9cfc93ca981af2a246c74845636ef74fc69d86d426bfeb964519`
- Strategy: `dual_ma`
- Strategy version: `v1`
- Parameter SHA-256: `fdada4b152544d9da7160358bed9cf3f4279e8efb4deb0fbfb029e094d79234a`
- Symbol: `SYNTH-001`
- Market: `synthetic`
- Timeframe: `1d`
- Dataset rows: `128`
- Dataset interval: `2025-01-01T00:00:00+00:00` to `2025-05-08T00:00:00+00:00`

| Partition | Rows | Start | End |
| --- | ---: | --- | --- |
| TRAIN | 40 | 2025-01-01T00:00:00+00:00 | 2025-02-09T00:00:00+00:00 |
| PURGE | 4 | 2025-02-10T00:00:00+00:00 | 2025-02-13T00:00:00+00:00 |
| VALIDATION | 40 | 2025-02-14T00:00:00+00:00 | 2025-03-25T00:00:00+00:00 |
| EMBARGO | 4 | 2025-03-26T00:00:00+00:00 | 2025-03-29T00:00:00+00:00 |
| FROZEN_TEST | 40 | 2025-03-30T00:00:00+00:00 | 2025-05-08T00:00:00+00:00 |

## GAP

- Quality gate: `BLOCK`
- Structural blockers:
  - `BLIND_HOLDOUT_NOT_PROVEN`
  - `EXTERNAL_PREREGISTRATION_RECEIPT_MISSING`
  - `SINGLE_CONSUMPTION_NOT_ENFORCED`
  - `NOT_NATURAL_FORWARD_EVIDENCE`
  - `NESTED_EXPERIMENT_REPRODUCIBILITY_BLOCK`
- Standard-report coverage gaps:
  - `WALK_FORWARD_REAL_MARKET_AND_LONG_HORIZON_NOT_AVAILABLE`
  - `PARAMETER_STABILITY_ONLY_DUAL_MA_SYNTHETIC_GRID`
  - `MULTIPLE_TESTING_CORRECTIONS_NOT_ESTIMABLE_TWO_SYNTHETIC_FOLDS`
  - `MARKET_REGIME_SLICES_ONLY_SYNTHETIC_FIXED_THRESHOLDS`
  - `TAIL_DISTRIBUTION_ONLY_TEN_SYNTHETIC_OBSERVATIONS`

## MATURITY

- Evidence scope: `LOCAL_FIXED_SPLIT_RESEARCH_ONLY_NOT_BLIND_NOT_NATURAL_FORWARD_NO_SINGLE_CONSUMPTION_PROOF`
- Nested reproducibility checks complete: `false`
- Volatility-matched analytical comparisons complete: `true`
- Prior-window volatility-target execution baseline complete: `true`
- Fixed-parameter walk-forward schedule complete: `true`
- Parameter-stability matrix complete: `true`
- Multiple-testing lineage complete: `true`
- Fixed trailing market-regime slices complete: `true`
- Partial tail/distribution analyses complete: `true`
- Volatility-matched comparator tradable: `false`
- Volatility-target benchmark execution scope: `RESEARCH_SIMULATOR_ONLY`
- Frozen Test is blind: `false`
- Frozen Test single consumption proven: `false`
- Natural-forward evidence: `false`
- Walk-forward unused tail rows: `21`

### Registered strategy observations

| Role | Cost scenario | Fee rate | Slippage | Total return | Annualized return | Sharpe | Max drawdown | Final equity | Total fees | Trades | Win rate | Ambiguous intrabar |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
 | TRAIN | BASE | 0.001000 | 0.001000 | 0.0000% | 0.0000% | 0.0000 | 0.0000% | 10000.0000 | 0.0000 | 0 | 0.0000% | 0 | 
 | VALIDATION | BASE | 0.001000 | 0.001000 | 0.0000% | 0.0000% | 0.0000 | 0.0000% | 10000.0000 | 0.0000 | 0 | 0.0000% | 0 | 
 | VALIDATION | DOUBLE_COST | 0.002000 | 0.002000 | 0.0000% | 0.0000% | 0.0000 | 0.0000% | 10000.0000 | 0.0000 | 0 | 0.0000% | 0 | 
 | VALIDATION | TRIPLE_COST | 0.003000 | 0.003000 | 0.0000% | 0.0000% | 0.0000 | 0.0000% | 10000.0000 | 0.0000 | 0 | 0.0000% | 0 | 
 | FROZEN_TEST | BASE | 0.001000 | 0.001000 | 0.0000% | 0.0000% | 0.0000 | 0.0000% | 10000.0000 | 0.0000 | 0 | 0.0000% | 0 | 
 | FROZEN_TEST | DOUBLE_COST | 0.002000 | 0.002000 | 0.0000% | 0.0000% | 0.0000 | 0.0000% | 10000.0000 | 0.0000 | 0 | 0.0000% | 0 | 
 | FROZEN_TEST | TRIPLE_COST | 0.003000 | 0.003000 | 0.0000% | 0.0000% | 0.0000 | 0.0000% | 10000.0000 | 0.0000 | 0 | 0.0000% | 0 | 

### Fixed benchmark observations

| Role | Benchmark | Cost scenario | Fee rate | Slippage | Total return | Annualized return | Sharpe | Max drawdown | Final equity | Total fees | Trades | Win rate | Ambiguous intrabar |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
 | VALIDATION | CASH | BASE | 0.001000 | 0.001000 | 0.0000% | 0.0000% | 0.0000 | 0.0000% | 10000.0000 | 0.0000 | 0 | 0.0000% | 0 | 
 | VALIDATION | CASH | DOUBLE_COST | 0.002000 | 0.002000 | 0.0000% | 0.0000% | 0.0000 | 0.0000% | 10000.0000 | 0.0000 | 0 | 0.0000% | 0 | 
 | VALIDATION | CASH | TRIPLE_COST | 0.003000 | 0.003000 | 0.0000% | 0.0000% | 0.0000 | 0.0000% | 10000.0000 | 0.0000 | 0 | 0.0000% | 0 | 
 | VALIDATION | ENGINE_BUY_AND_HOLD | BASE | 0.001000 | 0.001000 | 1.8216% | 108.0456% | 24.1766 | 0.0421% | 10182.1600 | 9.9900 | 1 | 0.0000% | 0 | 
 | VALIDATION | ENGINE_BUY_AND_HOLD | DOUBLE_COST | 0.002000 | 0.002000 | 1.6184% | 91.8500% | 24.1766 | 0.0421% | 10161.8400 | 19.9601 | 1 | 0.0000% | 0 | 
 | VALIDATION | ENGINE_BUY_AND_HOLD | TRIPLE_COST | 0.003000 | 0.003000 | 1.4159% | 76.9295% | 24.1766 | 0.0421% | 10141.5900 | 29.9103 | 1 | 0.0000% | 0 | 
 | VALIDATION | FIXED_DUAL_MA | BASE | 0.001000 | 0.001000 | 1.8216% | 108.0456% | 24.1766 | 0.0421% | 10182.1600 | 9.9900 | 1 | 0.0000% | 0 | 
 | VALIDATION | FIXED_DUAL_MA | DOUBLE_COST | 0.002000 | 0.002000 | 1.6184% | 91.8500% | 24.1766 | 0.0421% | 10161.8400 | 19.9601 | 1 | 0.0000% | 0 | 
 | VALIDATION | FIXED_DUAL_MA | TRIPLE_COST | 0.003000 | 0.003000 | 1.4159% | 76.9295% | 24.1766 | 0.0421% | 10141.5900 | 29.9103 | 1 | 0.0000% | 0 | 
 | VALIDATION | FIXED_BREAKOUT | BASE | 0.001000 | 0.001000 | 0.0000% | 0.0000% | 0.0000 | 0.0000% | 10000.0000 | 0.0000 | 0 | 0.0000% | 0 | 
 | VALIDATION | FIXED_BREAKOUT | DOUBLE_COST | 0.002000 | 0.002000 | 0.0000% | 0.0000% | 0.0000 | 0.0000% | 10000.0000 | 0.0000 | 0 | 0.0000% | 0 | 
 | VALIDATION | FIXED_BREAKOUT | TRIPLE_COST | 0.003000 | 0.003000 | 0.0000% | 0.0000% | 0.0000 | 0.0000% | 10000.0000 | 0.0000 | 0 | 0.0000% | 0 | 
 | VALIDATION | HASH_NO_SKILL | BASE | 0.001000 | 0.001000 | 0.4360% | 19.3113% | 5.2065 | 0.2415% | 10043.6000 | 20.0437 | 2 | 100.0000% | 0 | 
 | VALIDATION | HASH_NO_SKILL | DOUBLE_COST | 0.002000 | 0.002000 | 0.0351% | 1.4337% | 0.3471 | 0.4406% | 10003.5100 | 40.0072 | 2 | 100.0000% | 0 | 
 | VALIDATION | HASH_NO_SKILL | TRIPLE_COST | 0.003000 | 0.003000 | -0.3643% | -13.7652% | -2.5903 | 0.6390% | 9963.5700 | 59.8909 | 2 | 0.0000% | 0 | 
 | FROZEN_TEST | CASH | BASE | 0.001000 | 0.001000 | 0.0000% | 0.0000% | 0.0000 | 0.0000% | 10000.0000 | 0.0000 | 0 | 0.0000% | 0 | 
 | FROZEN_TEST | CASH | DOUBLE_COST | 0.002000 | 0.002000 | 0.0000% | 0.0000% | 0.0000 | 0.0000% | 10000.0000 | 0.0000 | 0 | 0.0000% | 0 | 
 | FROZEN_TEST | CASH | TRIPLE_COST | 0.003000 | 0.003000 | 0.0000% | 0.0000% | 0.0000 | 0.0000% | 10000.0000 | 0.0000 | 0 | 0.0000% | 0 | 
 | FROZEN_TEST | ENGINE_BUY_AND_HOLD | BASE | 0.001000 | 0.001000 | 1.6499% | 94.2740% | 24.1771 | 0.0385% | 10164.9900 | 9.9900 | 1 | 0.0000% | 0 | 
 | FROZEN_TEST | ENGINE_BUY_AND_HOLD | DOUBLE_COST | 0.002000 | 0.002000 | 1.4471% | 79.1505% | 24.1771 | 0.0385% | 10144.7100 | 19.9601 | 1 | 0.0000% | 0 | 
 | FROZEN_TEST | ENGINE_BUY_AND_HOLD | TRIPLE_COST | 0.003000 | 0.003000 | 1.2449% | 65.2176% | 24.1771 | 0.0385% | 10124.4900 | 29.9103 | 1 | 0.0000% | 0 | 
 | FROZEN_TEST | FIXED_DUAL_MA | BASE | 0.001000 | 0.001000 | 1.6499% | 94.2740% | 24.1771 | 0.0385% | 10164.9900 | 9.9900 | 1 | 0.0000% | 0 | 
 | FROZEN_TEST | FIXED_DUAL_MA | DOUBLE_COST | 0.002000 | 0.002000 | 1.4471% | 79.1505% | 24.1771 | 0.0385% | 10144.7100 | 19.9601 | 1 | 0.0000% | 0 | 
 | FROZEN_TEST | FIXED_DUAL_MA | TRIPLE_COST | 0.003000 | 0.003000 | 1.2449% | 65.2176% | 24.1771 | 0.0385% | 10124.4900 | 29.9103 | 1 | 0.0000% | 0 | 
 | FROZEN_TEST | FIXED_BREAKOUT | BASE | 0.001000 | 0.001000 | 0.0000% | 0.0000% | 0.0000 | 0.0000% | 10000.0000 | 0.0000 | 0 | 0.0000% | 0 | 
 | FROZEN_TEST | FIXED_BREAKOUT | DOUBLE_COST | 0.002000 | 0.002000 | 0.0000% | 0.0000% | 0.0000 | 0.0000% | 10000.0000 | 0.0000 | 0 | 0.0000% | 0 | 
 | FROZEN_TEST | FIXED_BREAKOUT | TRIPLE_COST | 0.003000 | 0.003000 | 0.0000% | 0.0000% | 0.0000 | 0.0000% | 10000.0000 | 0.0000 | 0 | 0.0000% | 0 | 
 | FROZEN_TEST | HASH_NO_SKILL | BASE | 0.001000 | 0.001000 | -0.2073% | -8.0763% | -8.8708 | 0.2073% | 9979.2700 | 19.9793 | 2 | 0.0000% | 0 | 
 | FROZEN_TEST | HASH_NO_SKILL | DOUBLE_COST | 0.002000 | 0.002000 | -0.6057% | -21.8501% | -9.0386 | 0.6057% | 9939.4300 | 39.8788 | 2 | 0.0000% | 0 | 
 | FROZEN_TEST | HASH_NO_SKILL | TRIPLE_COST | 0.003000 | 0.003000 | -1.0025% | -33.5601% | -9.0532 | 1.0025% | 9899.7500 | 59.6989 | 2 | 0.0000% | 0 | 

### Prior-window volatility-target research-simulator benchmark

Method: `prior-window-volatility-target-v1`; leverage allowed: `false`; paper/live/order authorization: `false`.

| Role | Calibration role | Cost scenario | Target ann. volatility | Source ann. volatility | Applied exposure | Exposure capped | Total return | Calibration status |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: | --- |
 | VALIDATION | TRAIN | BASE | 0.0000% | 2.9736% | 0.0000% | false | 0.0000% | CALIBRATED | 
 | VALIDATION | TRAIN | DOUBLE_COST | 0.0000% | 2.9736% | 0.0000% | false | 0.0000% | CALIBRATED | 
 | VALIDATION | TRAIN | TRIPLE_COST | 0.0000% | 2.9736% | 0.0000% | false | 0.0000% | CALIBRATED | 
 | FROZEN_TEST | VALIDATION | BASE | 0.0000% | 2.6995% | 0.0000% | false | 0.0000% | CALIBRATED | 
 | FROZEN_TEST | VALIDATION | DOUBLE_COST | 0.0000% | 2.6995% | 0.0000% | false | 0.0000% | CALIBRATED | 
 | FROZEN_TEST | VALIDATION | TRIPLE_COST | 0.0000% | 2.6995% | 0.0000% | false | 0.0000% | CALIBRATED | 

### Ex-post volatility-matched analytical comparisons

Method: `ex-post-volatility-match-v1`; interpretation: `ANALYTICAL_ONLY_NOT_TRADABLE`.

| Role | Cost scenario | Strategy observed ann. volatility | Buy-hold observed ann. volatility | Scale | Matched buy-hold ann. volatility | Matched buy-hold curve return | Strategy minus matched curve return | Status |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
 | VALIDATION | BASE | 0.0000% | 3.4969% | 0.000000 | 0.0000% | 0.0000% | 0.0000% | OBSERVED | 
 | VALIDATION | DOUBLE_COST | 0.0000% | 4.3753% | 0.000000 | 0.0000% | 0.0000% | 0.0000% | OBSERVED | 
 | VALIDATION | TRIPLE_COST | 0.0000% | 5.3782% | 0.000000 | 0.0000% | 0.0000% | 0.0000% | OBSERVED | 
 | FROZEN_TEST | BASE | 0.0000% | 3.2696% | 0.000000 | 0.0000% | 0.0000% | 0.0000% | OBSERVED | 
 | FROZEN_TEST | DOUBLE_COST | 0.0000% | 4.1696% | 0.000000 | 0.0000% | 0.0000% | 0.0000% | OBSERVED | 
 | FROZEN_TEST | TRIPLE_COST | 0.0000% | 5.1913% | 0.000000 | 0.0000% | 0.0000% | 0.0000% | OBSERVED | 

### Fixed-parameter walk-forward observations

Method: `fixed-parameter-walk-forward-v1`; fitting: `NONE_FIXED_PARAMETERS`; nested manifest role: `UNCLASSIFIED`; ranking: `false`.

| Fold | Cost scenario | Calibration start | Calibration end | Evaluation start | Evaluation end | Total return | Max drawdown | Manifest role | Ranking input |
| --- | --- | --- | --- | --- | --- | ---: | ---: | --- | --- |
 | WF01 | BASE | 2025-01-01T00:00:00+00:00 | 2025-02-04T00:00:00+00:00 | 2025-02-06T00:00:00+00:00 | 2025-03-12T00:00:00+00:00 | 0.0000% | 0.0000% | UNCLASSIFIED | false | 
 | WF01 | DOUBLE_COST | 2025-01-01T00:00:00+00:00 | 2025-02-04T00:00:00+00:00 | 2025-02-06T00:00:00+00:00 | 2025-03-12T00:00:00+00:00 | 0.0000% | 0.0000% | UNCLASSIFIED | false | 
 | WF01 | TRIPLE_COST | 2025-01-01T00:00:00+00:00 | 2025-02-04T00:00:00+00:00 | 2025-02-06T00:00:00+00:00 | 2025-03-12T00:00:00+00:00 | 0.0000% | 0.0000% | UNCLASSIFIED | false | 
 | WF02 | BASE | 2025-02-06T00:00:00+00:00 | 2025-03-12T00:00:00+00:00 | 2025-03-14T00:00:00+00:00 | 2025-04-17T00:00:00+00:00 | 0.0000% | 0.0000% | UNCLASSIFIED | false | 
 | WF02 | DOUBLE_COST | 2025-02-06T00:00:00+00:00 | 2025-03-12T00:00:00+00:00 | 2025-03-14T00:00:00+00:00 | 2025-04-17T00:00:00+00:00 | 0.0000% | 0.0000% | UNCLASSIFIED | false | 
 | WF02 | TRIPLE_COST | 2025-02-06T00:00:00+00:00 | 2025-03-12T00:00:00+00:00 | 2025-03-14T00:00:00+00:00 | 2025-04-17T00:00:00+00:00 | 0.0000% | 0.0000% | UNCLASSIFIED | false | 

#### Walk-forward scenario summary

| Cost scenario | Folds | Median total return | Minimum total return | Maximum total return | Median max drawdown | Nested reproducibility |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
 | BASE | 2 | 0.0000% | 0.0000% | 0.0000% | 0.0000% | false | 
 | DOUBLE_COST | 2 | 0.0000% | 0.0000% | 0.0000% | 0.0000% | false | 
 | TRIPLE_COST | 2 | 0.0000% | 0.0000% | 0.0000% | 0.0000% | false | 

### Parameter-stability observations

Method: `dual-ma-fixed-perturbation-matrix-v1`; all cells retained: `true`; selected cell: `null`; ranking: `false`.

#### VALIDATION timing-grid total return

| Fast \ Slow | 16 | 18 | 20 | 22 | 24 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 0.0000% | 0.0000% | 0.0000% | 0.0000% | 0.0000% |
| 5 | 0.0000% | 0.0000% | 0.0000% | 0.0000% | 0.0000% |
| 6 | 0.0000% | 0.0000% | 0.0000% | 0.0000% | 0.0000% |

#### FROZEN_TEST timing-grid total return

| Fast \ Slow | 16 | 18 | 20 | 22 | 24 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 0.0000% | 0.0000% | 0.0000% | 0.0000% | 0.0000% |
| 5 | 0.0000% | 0.0000% | 0.0000% | 0.0000% | 0.0000% |
| 6 | 0.0000% | 0.0000% | 0.0000% | 0.0000% | 0.0000% |

#### Risk parameter one-at-a-time observations

| Role | Parameter | Perturbation | Total return | Max drawdown | Ranking input |
| --- | --- | ---: | ---: | ---: | --- |
 | VALIDATION | position_pct | -20% | 0.0000% | 0.0000% | false | 
 | VALIDATION | position_pct | 20% | 0.0000% | 0.0000% | false | 
 | VALIDATION | stop_loss_pct | -20% | 0.0000% | 0.0000% | false | 
 | VALIDATION | stop_loss_pct | 20% | 0.0000% | 0.0000% | false | 
 | VALIDATION | take_profit_pct | -20% | 0.0000% | 0.0000% | false | 
 | VALIDATION | take_profit_pct | 20% | 0.0000% | 0.0000% | false | 
 | FROZEN_TEST | position_pct | -20% | 0.0000% | 0.0000% | false | 
 | FROZEN_TEST | position_pct | 20% | 0.0000% | 0.0000% | false | 
 | FROZEN_TEST | stop_loss_pct | -20% | 0.0000% | 0.0000% | false | 
 | FROZEN_TEST | stop_loss_pct | 20% | 0.0000% | 0.0000% | false | 
 | FROZEN_TEST | take_profit_pct | -20% | 0.0000% | 0.0000% | false | 
 | FROZEN_TEST | take_profit_pct | 20% | 0.0000% | 0.0000% | false | 

#### Parameter-stability summary

| Role | Cells | Center return | Median return | Max absolute deviation | Timing grid complete | Risk OAT complete | All non-rankable |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
 | VALIDATION | 21 | 0.0000% | 0.0000% | 0.0000% | true | true | true | 
 | FROZEN_TEST | 21 | 0.0000% | 0.0000% | 0.0000% | true | true | true | 

### Multiple-testing lineage ledger

- Ledger status: `RECORDED_WITH_UNESTIMABLE_CORRECTIONS`
- Trial family: `DUAL_MA_PARAMETER_STABILITY_V1`
- Trials: `21`
- Retained observations: `42`
- Synthetic Frozen observations: `21`
- Formal Frozen consumption count: `UNKNOWN`
- Single consumption proven: `false`
- External preregistration receipt present: `false`
- Selected trial: `null`
- Parameter selection performed: `false`
- Ranking performed: `false`

| Correction | Status | Value | Blockers |
| --- | --- | --- | --- |
| DEFLATED_SHARPE_RATIO | NOT_ESTIMABLE | UNKNOWN | RETURN_HISTORY_TOO_SHORT, SYNTHETIC_SINGLE_DATASET_ONLY, NO_INDEPENDENT_TRIAL_DISTRIBUTION |
| PROBABILITY_OF_BACKTEST_OVERFITTING | NOT_ESTIMABLE | UNKNOWN | INSUFFICIENT_INDEPENDENT_FOLDS, NO_TRAIN_SELECTION_TEST_MATRIX, PARAMETER_SELECTION_NOT_PERFORMED |
| BLOCK_BOOTSTRAP_CONFIDENCE_INTERVAL | NOT_COMPUTED | UNKNOWN | ACTIVE_RETURN_HISTORY_TOO_SHORT, BLOCK_LENGTH_NOT_PREREGISTERED |

### Fixed trailing market-regime analysis

Method: `fixed-trailing-market-regime-v1`; scope: `EX_POST_DESCRIPTIVE_NOT_SIGNAL`; classifier inputs: `close`; signal, selection, and ranking: `false`.

| Role | Regime | Observations | Status | Strategy compounded return | Market compounded return |
| --- | --- | ---: | --- | ---: | ---: |
| VALIDATION | UP_LOW | 10 | OBSERVED | 0.0000% | 2.2843% |
| VALIDATION | UP_HIGH | 0 | NO_OBSERVATIONS | UNKNOWN | UNKNOWN |
| VALIDATION | DOWN_LOW | 0 | NO_OBSERVATIONS | UNKNOWN | UNKNOWN |
| VALIDATION | DOWN_HIGH | 0 | NO_OBSERVATIONS | UNKNOWN | UNKNOWN |
| VALIDATION | RANGE_LOW | 0 | NO_OBSERVATIONS | UNKNOWN | UNKNOWN |
| VALIDATION | RANGE_HIGH | 0 | NO_OBSERVATIONS | UNKNOWN | UNKNOWN |
| FROZEN_TEST | UP_LOW | 10 | OBSERVED | 0.0000% | 2.0898% |
| FROZEN_TEST | UP_HIGH | 0 | NO_OBSERVATIONS | UNKNOWN | UNKNOWN |
| FROZEN_TEST | DOWN_LOW | 0 | NO_OBSERVATIONS | UNKNOWN | UNKNOWN |
| FROZEN_TEST | DOWN_HIGH | 0 | NO_OBSERVATIONS | UNKNOWN | UNKNOWN |
| FROZEN_TEST | RANGE_LOW | 0 | NO_OBSERVATIONS | UNKNOWN | UNKNOWN |
| FROZEN_TEST | RANGE_HIGH | 0 | NO_OBSERVATIONS | UNKNOWN | UNKNOWN |

### Partial tail and distribution analysis

Method: `frozen-tail-distribution-policy-v1`; scope: `DESCRIPTIVE_PARTIAL_NOT_INFERENCE_NOT_SIGNAL`; unknown metrics remain `UNKNOWN` with explicit gaps.

| Role | Cost scenario | State | Returns | Closed trades | Ann. volatility | Sortino | Calmar | Max drawdown | Drawdown duration | Turnover | Exposure | VaR 95 | CVaR 95 | Gaps |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| VALIDATION | BASE | PARTIAL | 10 | 0 | 0.0000% | UNKNOWN | UNKNOWN | 0.0000% | 0 | 0 | 0.0000% | UNKNOWN | UNKNOWN | CALMAR_UNDEFINED_NO_DRAWDOWN, MONTH_BUCKET_COUNT_LT_2, POSITIVE_MONTH_CONCENTRATION_UNAVAILABLE, POSITIVE_TRADE_CONCENTRATION_UNAVAILABLE, SORTINO_UNDEFINED_NO_DOWNSIDE, TAIL_SAMPLE_LT_100, TAIL_SAMPLE_LT_20, TRADE_DISTRIBUTION_UNAVAILABLE, YEAR_BUCKET_COUNT_LT_2 |
| VALIDATION | DOUBLE_COST | PARTIAL | 10 | 0 | 0.0000% | UNKNOWN | UNKNOWN | 0.0000% | 0 | 0 | 0.0000% | UNKNOWN | UNKNOWN | CALMAR_UNDEFINED_NO_DRAWDOWN, MONTH_BUCKET_COUNT_LT_2, POSITIVE_MONTH_CONCENTRATION_UNAVAILABLE, POSITIVE_TRADE_CONCENTRATION_UNAVAILABLE, SORTINO_UNDEFINED_NO_DOWNSIDE, TAIL_SAMPLE_LT_100, TAIL_SAMPLE_LT_20, TRADE_DISTRIBUTION_UNAVAILABLE, YEAR_BUCKET_COUNT_LT_2 |
| VALIDATION | TRIPLE_COST | PARTIAL | 10 | 0 | 0.0000% | UNKNOWN | UNKNOWN | 0.0000% | 0 | 0 | 0.0000% | UNKNOWN | UNKNOWN | CALMAR_UNDEFINED_NO_DRAWDOWN, MONTH_BUCKET_COUNT_LT_2, POSITIVE_MONTH_CONCENTRATION_UNAVAILABLE, POSITIVE_TRADE_CONCENTRATION_UNAVAILABLE, SORTINO_UNDEFINED_NO_DOWNSIDE, TAIL_SAMPLE_LT_100, TAIL_SAMPLE_LT_20, TRADE_DISTRIBUTION_UNAVAILABLE, YEAR_BUCKET_COUNT_LT_2 |
| FROZEN_TEST | BASE | PARTIAL | 10 | 0 | 0.0000% | UNKNOWN | UNKNOWN | 0.0000% | 0 | 0 | 0.0000% | UNKNOWN | UNKNOWN | CALMAR_UNDEFINED_NO_DRAWDOWN, POSITIVE_MONTH_CONCENTRATION_UNAVAILABLE, POSITIVE_TRADE_CONCENTRATION_UNAVAILABLE, SORTINO_UNDEFINED_NO_DOWNSIDE, TAIL_SAMPLE_LT_100, TAIL_SAMPLE_LT_20, TRADE_DISTRIBUTION_UNAVAILABLE, YEAR_BUCKET_COUNT_LT_2 |
| FROZEN_TEST | DOUBLE_COST | PARTIAL | 10 | 0 | 0.0000% | UNKNOWN | UNKNOWN | 0.0000% | 0 | 0 | 0.0000% | UNKNOWN | UNKNOWN | CALMAR_UNDEFINED_NO_DRAWDOWN, POSITIVE_MONTH_CONCENTRATION_UNAVAILABLE, POSITIVE_TRADE_CONCENTRATION_UNAVAILABLE, SORTINO_UNDEFINED_NO_DOWNSIDE, TAIL_SAMPLE_LT_100, TAIL_SAMPLE_LT_20, TRADE_DISTRIBUTION_UNAVAILABLE, YEAR_BUCKET_COUNT_LT_2 |
| FROZEN_TEST | TRIPLE_COST | PARTIAL | 10 | 0 | 0.0000% | UNKNOWN | UNKNOWN | 0.0000% | 0 | 0 | 0.0000% | UNKNOWN | UNKNOWN | CALMAR_UNDEFINED_NO_DRAWDOWN, POSITIVE_MONTH_CONCENTRATION_UNAVAILABLE, POSITIVE_TRADE_CONCENTRATION_UNAVAILABLE, SORTINO_UNDEFINED_NO_DOWNSIDE, TAIL_SAMPLE_LT_100, TAIL_SAMPLE_LT_20, TRADE_DISTRIBUTION_UNAVAILABLE, YEAR_BUCKET_COUNT_LT_2 |

## PERMISSION

| Capability | Allowed |
| --- | --- |
| `parameter_selection` | `false` |
| `ranking` | `false` |
| `profitability_proof` | `false` |
| `paper` | `false` |
| `live` | `false` |
| `order` | `false` |

This is descriptive research evidence only. It is not a profitability claim, a formal blind-test result, or permission for paper, live, or order execution.
