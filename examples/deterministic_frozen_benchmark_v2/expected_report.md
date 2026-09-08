# Hakimi Frozen Evaluation Report

Renderer: `frozen-evaluation-markdown-v22`

## SOURCE

- Report ID: `hfer-f8758836c5d25c418f3f`
- Report SHA-256: `f8758836c5d25c418f3f6e38f643a29a5e92c3f17d137a1a6d135965d50eb222`
- Protocol ID: `hfep-8d323bb993c5279b4d37`
- Protocol SHA-256: `8d323bb993c5279b4d37ce8b2a12dd2e654bcc75a6877a4e5d7a7ca79f1ec057`
- Dataset SHA-256: `1cf5fd0e59082042d42f4b42d4841a5f35f673126b93fca3bda4de46a0fbac35`
- Dataset governance SHA-256: `625b44c3d6104c15a765bf6ce4dfe6079d816479082411c17fc22b6979593020`
- Calendar conformance SHA-256: `13f8622eb55e4b402d22532c767d3a74091489030ebe1ecdc41de3d014183152`
- Calendar conformance: `PASS` / `DETERMINISTIC_SYNTHETIC_DAILY`
- Dataset ID: `synthetic-frozen-oos-cost-stress-v2`
- Source: `SYNTHETIC_FIXTURE` / `deterministic-local-fixture`
- Time contract: `UTC` / `SYNTHETIC_DAILY`
- Adjustment basis: `NOT_APPLICABLE`
- Population: `SYNTHETIC_FIXED_SINGLE_INSTRUMENT` / survivorship `NOT_APPLICABLE`
- Config SHA-256: `6d109ec688fd54bee89c8ab99445a7d73bc794118d2cd4e00b325805c03949b2`
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
  - `SYNTHETIC_FIXTURE_DATASET_GOVERNANCE`
  - `VOLATILITY_MATCHED_COMPARISON_OBSERVATION_INCOMPLETE`
  - `EXECUTION_ADVERSITY_TARGET_SOURCE_ACTIVITY_INSUFFICIENT`
  - `BOOTSTRAP_CONFIDENCE_INSUFFICIENT_PAIRED_OBSERVATIONS`
  - `FROZEN_STATISTICAL_CORRECTIONS_UNESTIMABLE`
- Standard-report coverage gaps:
  - `WALK_FORWARD_REAL_MARKET_AND_LONG_HORIZON_NOT_AVAILABLE`
  - `PARAMETER_STABILITY_ONLY_DUAL_MA_SYNTHETIC_GRID`
  - `MULTIPLE_TESTING_CORRECTIONS_NOT_ESTIMABLE_TWO_SYNTHETIC_FOLDS`
  - `MARKET_REGIME_SLICES_ONLY_SYNTHETIC_FIXED_THRESHOLDS`
  - `TAIL_DISTRIBUTION_ONLY_TEN_SYNTHETIC_OBSERVATIONS`
  - `BOOTSTRAP_CONFIDENCE_ONLY_NINE_PAIRED_SYNTHETIC_OBSERVATIONS`
  - `RETURN_CONTRIBUTION_FIXED_21_PERIOD_WINDOW_UNAVAILABLE`
  - `DSR_NON_POSITIVE_TRIAL_VARIANCE_AND_PBO_INSUFFICIENT_OBSERVATIONS`
  - `EXECUTION_ADVERSITY_PARTIAL_FILL_REMAINDER_LIFECYCLE_NOT_MODELLED`

## MATURITY

- Evidence scope: `LOCAL_FIXED_SPLIT_RESEARCH_ONLY_NOT_BLIND_NOT_NATURAL_FORWARD_NO_SINGLE_CONSUMPTION_PROOF`
- Nested reproducibility checks complete: `false`
- Volatility-matched analytical comparison matrix complete: `true`
- Volatility-matched analytical observations complete: `false`
- Prior-window volatility-target execution baseline complete: `true`
- Registered execution-adversity matrix complete: `true`
- Target execution-adversity observations complete: `false`
- Fixed liquidity-capacity probe matrix complete: `true`
- Fixed liquidity-capacity partial fill observed: `true`
- Paired moving-block Bootstrap matrix complete: `true`
- Bootstrap observation sufficiency complete: `false`
- Fixed-parameter walk-forward schedule complete: `true`
- Parameter-stability matrix complete: `true`
- Frozen statistical-correction matrix complete: `true`
- DSR and CSCV-PBO estimable: `false`
- Multiple-testing lineage complete: `true`
- Fixed trailing market-regime slices complete: `true`
- Partial tail/distribution analyses complete: `true`
- Return-contribution concentration matrix complete: `true`
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

### Registered execution-adversity observations

Target-strategy scenarios are synthetic diagnostics only. Observation status states whether target source activity was sufficient. Dynamic market impact, shared intrabar volume budgets, and partial-fill remainder lifecycle remain unmodelled.

| Role | Scenario | Observation | Total return | Max drawdown | Trades | Return delta | Drawdown delta | Trade delta |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| VALIDATION | one_bar_signal_release_delay | UNOBSERVED_SOURCE_ACTIVITY | 0.0000% | 0.0000% | 0 | 0.0000% | 0.0000% | 0 |
| VALIDATION | drop_every_third_actionable_signal | UNOBSERVED_SOURCE_ACTIVITY | 0.0000% | 0.0000% | 0 | 0.0000% | 0.0000% | 0 |
| VALIDATION | source_fill_adverse_open_2pct | UNOBSERVED_SOURCE_ACTIVITY | 0.0000% | 0.0000% | 0 | 0.0000% | 0.0000% | 0 |
| FROZEN_TEST | one_bar_signal_release_delay | UNOBSERVED_SOURCE_ACTIVITY | 0.0000% | 0.0000% | 0 | 0.0000% | 0.0000% | 0 |
| FROZEN_TEST | drop_every_third_actionable_signal | UNOBSERVED_SOURCE_ACTIVITY | 0.0000% | 0.0000% | 0 | 0.0000% | 0.0000% | 0 |
| FROZEN_TEST | source_fill_adverse_open_2pct | UNOBSERVED_SOURCE_ACTIVITY | 0.0000% | 0.0000% | 0 | 0.0000% | 0.0000% | 0 |

### Fixed liquidity-capacity execution probe

This fixed benchmark probe demonstrates one-shot volume-capped partial fills only. It is not target-strategy robustness evidence, and it does not model remainder lifecycle or a shared intrabar volume budget.

| Role | Source benchmark | Scenario | Max participation | Fills | Partial fills | Requested quantity | Filled quantity | Minimum fill ratio | Status |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| VALIDATION | ENGINE_BUY_AND_HOLD | volume_participation_cap_0_1pct | 0.1000% | 1 | 1 | 84.21966211 | 1.51800000 | 0.01802429 | OBSERVED |
| FROZEN_TEST | ENGINE_BUY_AND_HOLD | volume_participation_cap_0_1pct | 0.1000% | 1 | 1 | 77.06586842 | 1.82600000 | 0.02369402 | OBSERVED |

### Fixed liquidity-rejection admission probe

This source-bound research admission probe demonstrates deterministic rejection below a preregistered minimum executable quantity. It does not submit an order, mutate a portfolio, model remainder lifecycle, or authorize paper/live/order execution.

| Role | Source benchmark | Scenario | Max participation | Minimum quantity | Executable quantity | Decision | Reason |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| VALIDATION | ENGINE_BUY_AND_HOLD | minimum_executable_quantity_rejection | 0.00000010% | 0.00100000 | 0.000001518000 | REJECTED | MINIMUM_EXECUTABLE_QUANTITY_NOT_MET |
| FROZEN_TEST | ENGINE_BUY_AND_HOLD | minimum_executable_quantity_rejection | 0.00000010% | 0.00100000 | 0.000001826000 | REJECTED | MINIMUM_EXECUTABLE_QUANTITY_NOT_MET |

### Paired moving-block Bootstrap confidence evidence

The policy is preregistered at 1,000 paired moving-block replicates, but replicates execute only when the minimum paired-observation threshold is met. GAP records contain no confidence intervals and make no formal-inference, profitability, paper, live, or order claim.

| Role | Benchmark | State | Paired observations | Minimum | Executed replicates | Intervals | Gaps |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| VALIDATION | ENGINE_BUY_AND_HOLD | GAP | 9 | 60 | 0 | 0 | INSUFFICIENT_PAIRED_OBSERVATIONS |
| FROZEN_TEST | ENGINE_BUY_AND_HOLD | GAP | 9 | 60 | 0 | 0 | INSUFFICIENT_PAIRED_OBSERVATIONS |

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

Method: `ex-post-volatility-match-v2`; zero-target policy: `GAP_NOT_ZERO_FILLED`; interpretation: `ANALYTICAL_ONLY_NOT_TRADABLE`.

| Role | Cost scenario | Strategy observed ann. volatility | Buy-hold observed ann. volatility | Scale | Matched buy-hold ann. volatility | Matched buy-hold curve return | Strategy minus matched curve return | Status | GAP reason |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
 | VALIDATION | BASE | 0.0000% | 3.4969% | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | GAP | TARGET_STRATEGY_VOLATILITY_AT_OR_BELOW_ACTIVITY_FLOOR | 
 | VALIDATION | DOUBLE_COST | 0.0000% | 4.3753% | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | GAP | TARGET_STRATEGY_VOLATILITY_AT_OR_BELOW_ACTIVITY_FLOOR | 
 | VALIDATION | TRIPLE_COST | 0.0000% | 5.3782% | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | GAP | TARGET_STRATEGY_VOLATILITY_AT_OR_BELOW_ACTIVITY_FLOOR | 
 | FROZEN_TEST | BASE | 0.0000% | 3.2696% | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | GAP | TARGET_STRATEGY_VOLATILITY_AT_OR_BELOW_ACTIVITY_FLOOR | 
 | FROZEN_TEST | DOUBLE_COST | 0.0000% | 4.1696% | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | GAP | TARGET_STRATEGY_VOLATILITY_AT_OR_BELOW_ACTIVITY_FLOOR | 
 | FROZEN_TEST | TRIPLE_COST | 0.0000% | 5.1913% | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | GAP | TARGET_STRATEGY_VOLATILITY_AT_OR_BELOW_ACTIVITY_FLOOR | 

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

### Frozen statistical-correction evidence

The two matrices reuse all 21 preregistered BASE parameter-stability cells per role and add zero backtests. DSR and CSCV-PBO remain GAP when their canonical preconditions are not met; no threshold, significance, ranking, or profitability decision is inferred.

| Role | Trials | Period observations | DSR state | DSR gap | CSCV-PBO state | CSCV-PBO gap | Additional backtests |
| --- | ---: | ---: | --- | --- | --- | --- | ---: |
| VALIDATION | 21 | 9 | GAP | DSR_TRIAL_RETURN_VARIANCE_NON_POSITIVE | GAP | PBO_INSUFFICIENT_OBSERVATIONS_FOR_EIGHT_PARTITIONS | 0 |
| FROZEN_TEST | 21 | 9 | GAP | DSR_TRIAL_RETURN_VARIANCE_NON_POSITIVE | GAP | PBO_INSUFFICIENT_OBSERVATIONS_FOR_EIGHT_PARTITIONS | 0 |

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
| VALIDATION | BASE | PARTIAL | 10 | 0 | 0.0000% | UNKNOWN | UNKNOWN | 0.0000% | 0 | 0 | 0.0000% | UNKNOWN | UNKNOWN | CALMAR_UNDEFINED_NO_DRAWDOWN, FEE_LOAD_UNAVAILABLE_NO_TRADED_NOTIONAL, FIXED_21_PERIOD_WINDOW_UNAVAILABLE, MONTH_BUCKET_COUNT_LT_2, POSITIVE_MONTH_CONCENTRATION_UNAVAILABLE, POSITIVE_PERIOD_CONCENTRATION_UNAVAILABLE, POSITIVE_TRADE_CONCENTRATION_UNAVAILABLE, SORTINO_UNDEFINED_NO_DOWNSIDE, TAIL_SAMPLE_LT_100, TAIL_SAMPLE_LT_20, TRADE_DISTRIBUTION_UNAVAILABLE, YEAR_BUCKET_COUNT_LT_2 |
| VALIDATION | DOUBLE_COST | PARTIAL | 10 | 0 | 0.0000% | UNKNOWN | UNKNOWN | 0.0000% | 0 | 0 | 0.0000% | UNKNOWN | UNKNOWN | CALMAR_UNDEFINED_NO_DRAWDOWN, FEE_LOAD_UNAVAILABLE_NO_TRADED_NOTIONAL, FIXED_21_PERIOD_WINDOW_UNAVAILABLE, MONTH_BUCKET_COUNT_LT_2, POSITIVE_MONTH_CONCENTRATION_UNAVAILABLE, POSITIVE_PERIOD_CONCENTRATION_UNAVAILABLE, POSITIVE_TRADE_CONCENTRATION_UNAVAILABLE, SORTINO_UNDEFINED_NO_DOWNSIDE, TAIL_SAMPLE_LT_100, TAIL_SAMPLE_LT_20, TRADE_DISTRIBUTION_UNAVAILABLE, YEAR_BUCKET_COUNT_LT_2 |
| VALIDATION | TRIPLE_COST | PARTIAL | 10 | 0 | 0.0000% | UNKNOWN | UNKNOWN | 0.0000% | 0 | 0 | 0.0000% | UNKNOWN | UNKNOWN | CALMAR_UNDEFINED_NO_DRAWDOWN, FEE_LOAD_UNAVAILABLE_NO_TRADED_NOTIONAL, FIXED_21_PERIOD_WINDOW_UNAVAILABLE, MONTH_BUCKET_COUNT_LT_2, POSITIVE_MONTH_CONCENTRATION_UNAVAILABLE, POSITIVE_PERIOD_CONCENTRATION_UNAVAILABLE, POSITIVE_TRADE_CONCENTRATION_UNAVAILABLE, SORTINO_UNDEFINED_NO_DOWNSIDE, TAIL_SAMPLE_LT_100, TAIL_SAMPLE_LT_20, TRADE_DISTRIBUTION_UNAVAILABLE, YEAR_BUCKET_COUNT_LT_2 |
| FROZEN_TEST | BASE | PARTIAL | 10 | 0 | 0.0000% | UNKNOWN | UNKNOWN | 0.0000% | 0 | 0 | 0.0000% | UNKNOWN | UNKNOWN | CALMAR_UNDEFINED_NO_DRAWDOWN, FEE_LOAD_UNAVAILABLE_NO_TRADED_NOTIONAL, FIXED_21_PERIOD_WINDOW_UNAVAILABLE, POSITIVE_MONTH_CONCENTRATION_UNAVAILABLE, POSITIVE_PERIOD_CONCENTRATION_UNAVAILABLE, POSITIVE_TRADE_CONCENTRATION_UNAVAILABLE, SORTINO_UNDEFINED_NO_DOWNSIDE, TAIL_SAMPLE_LT_100, TAIL_SAMPLE_LT_20, TRADE_DISTRIBUTION_UNAVAILABLE, YEAR_BUCKET_COUNT_LT_2 |
| FROZEN_TEST | DOUBLE_COST | PARTIAL | 10 | 0 | 0.0000% | UNKNOWN | UNKNOWN | 0.0000% | 0 | 0 | 0.0000% | UNKNOWN | UNKNOWN | CALMAR_UNDEFINED_NO_DRAWDOWN, FEE_LOAD_UNAVAILABLE_NO_TRADED_NOTIONAL, FIXED_21_PERIOD_WINDOW_UNAVAILABLE, POSITIVE_MONTH_CONCENTRATION_UNAVAILABLE, POSITIVE_PERIOD_CONCENTRATION_UNAVAILABLE, POSITIVE_TRADE_CONCENTRATION_UNAVAILABLE, SORTINO_UNDEFINED_NO_DOWNSIDE, TAIL_SAMPLE_LT_100, TAIL_SAMPLE_LT_20, TRADE_DISTRIBUTION_UNAVAILABLE, YEAR_BUCKET_COUNT_LT_2 |
| FROZEN_TEST | TRIPLE_COST | PARTIAL | 10 | 0 | 0.0000% | UNKNOWN | UNKNOWN | 0.0000% | 0 | 0 | 0.0000% | UNKNOWN | UNKNOWN | CALMAR_UNDEFINED_NO_DRAWDOWN, FEE_LOAD_UNAVAILABLE_NO_TRADED_NOTIONAL, FIXED_21_PERIOD_WINDOW_UNAVAILABLE, POSITIVE_MONTH_CONCENTRATION_UNAVAILABLE, POSITIVE_PERIOD_CONCENTRATION_UNAVAILABLE, POSITIVE_TRADE_CONCENTRATION_UNAVAILABLE, SORTINO_UNDEFINED_NO_DOWNSIDE, TAIL_SAMPLE_LT_100, TAIL_SAMPLE_LT_20, TRADE_DISTRIBUTION_UNAVAILABLE, YEAR_BUCKET_COUNT_LT_2 |

### Return-contribution concentration

Single-period, calendar-month, and realised SELL-fill concentration reuse the same source-bound distribution evidence. The fixed 21-period window remains GAP when the sample is too short; no separate duplicate diagnostics chain is used.

| Role | Cost scenario | Top positive period share | Positive period HHI | Return without best period | Top positive month share | Top positive SELL-fill share | Positive SELL-fill HHI | Fixed 21-period window | Gaps |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| VALIDATION | BASE | UNKNOWN | UNKNOWN | 0 | UNKNOWN | UNKNOWN | UNKNOWN | GAP | CALMAR_UNDEFINED_NO_DRAWDOWN, FEE_LOAD_UNAVAILABLE_NO_TRADED_NOTIONAL, FIXED_21_PERIOD_WINDOW_UNAVAILABLE, MONTH_BUCKET_COUNT_LT_2, POSITIVE_MONTH_CONCENTRATION_UNAVAILABLE, POSITIVE_PERIOD_CONCENTRATION_UNAVAILABLE, POSITIVE_TRADE_CONCENTRATION_UNAVAILABLE, SORTINO_UNDEFINED_NO_DOWNSIDE, TAIL_SAMPLE_LT_100, TAIL_SAMPLE_LT_20, TRADE_DISTRIBUTION_UNAVAILABLE, YEAR_BUCKET_COUNT_LT_2 |
| VALIDATION | DOUBLE_COST | UNKNOWN | UNKNOWN | 0 | UNKNOWN | UNKNOWN | UNKNOWN | GAP | CALMAR_UNDEFINED_NO_DRAWDOWN, FEE_LOAD_UNAVAILABLE_NO_TRADED_NOTIONAL, FIXED_21_PERIOD_WINDOW_UNAVAILABLE, MONTH_BUCKET_COUNT_LT_2, POSITIVE_MONTH_CONCENTRATION_UNAVAILABLE, POSITIVE_PERIOD_CONCENTRATION_UNAVAILABLE, POSITIVE_TRADE_CONCENTRATION_UNAVAILABLE, SORTINO_UNDEFINED_NO_DOWNSIDE, TAIL_SAMPLE_LT_100, TAIL_SAMPLE_LT_20, TRADE_DISTRIBUTION_UNAVAILABLE, YEAR_BUCKET_COUNT_LT_2 |
| VALIDATION | TRIPLE_COST | UNKNOWN | UNKNOWN | 0 | UNKNOWN | UNKNOWN | UNKNOWN | GAP | CALMAR_UNDEFINED_NO_DRAWDOWN, FEE_LOAD_UNAVAILABLE_NO_TRADED_NOTIONAL, FIXED_21_PERIOD_WINDOW_UNAVAILABLE, MONTH_BUCKET_COUNT_LT_2, POSITIVE_MONTH_CONCENTRATION_UNAVAILABLE, POSITIVE_PERIOD_CONCENTRATION_UNAVAILABLE, POSITIVE_TRADE_CONCENTRATION_UNAVAILABLE, SORTINO_UNDEFINED_NO_DOWNSIDE, TAIL_SAMPLE_LT_100, TAIL_SAMPLE_LT_20, TRADE_DISTRIBUTION_UNAVAILABLE, YEAR_BUCKET_COUNT_LT_2 |
| FROZEN_TEST | BASE | UNKNOWN | UNKNOWN | 0 | UNKNOWN | UNKNOWN | UNKNOWN | GAP | CALMAR_UNDEFINED_NO_DRAWDOWN, FEE_LOAD_UNAVAILABLE_NO_TRADED_NOTIONAL, FIXED_21_PERIOD_WINDOW_UNAVAILABLE, POSITIVE_MONTH_CONCENTRATION_UNAVAILABLE, POSITIVE_PERIOD_CONCENTRATION_UNAVAILABLE, POSITIVE_TRADE_CONCENTRATION_UNAVAILABLE, SORTINO_UNDEFINED_NO_DOWNSIDE, TAIL_SAMPLE_LT_100, TAIL_SAMPLE_LT_20, TRADE_DISTRIBUTION_UNAVAILABLE, YEAR_BUCKET_COUNT_LT_2 |
| FROZEN_TEST | DOUBLE_COST | UNKNOWN | UNKNOWN | 0 | UNKNOWN | UNKNOWN | UNKNOWN | GAP | CALMAR_UNDEFINED_NO_DRAWDOWN, FEE_LOAD_UNAVAILABLE_NO_TRADED_NOTIONAL, FIXED_21_PERIOD_WINDOW_UNAVAILABLE, POSITIVE_MONTH_CONCENTRATION_UNAVAILABLE, POSITIVE_PERIOD_CONCENTRATION_UNAVAILABLE, POSITIVE_TRADE_CONCENTRATION_UNAVAILABLE, SORTINO_UNDEFINED_NO_DOWNSIDE, TAIL_SAMPLE_LT_100, TAIL_SAMPLE_LT_20, TRADE_DISTRIBUTION_UNAVAILABLE, YEAR_BUCKET_COUNT_LT_2 |
| FROZEN_TEST | TRIPLE_COST | UNKNOWN | UNKNOWN | 0 | UNKNOWN | UNKNOWN | UNKNOWN | GAP | CALMAR_UNDEFINED_NO_DRAWDOWN, FEE_LOAD_UNAVAILABLE_NO_TRADED_NOTIONAL, FIXED_21_PERIOD_WINDOW_UNAVAILABLE, POSITIVE_MONTH_CONCENTRATION_UNAVAILABLE, POSITIVE_PERIOD_CONCENTRATION_UNAVAILABLE, POSITIVE_TRADE_CONCENTRATION_UNAVAILABLE, SORTINO_UNDEFINED_NO_DOWNSIDE, TAIL_SAMPLE_LT_100, TAIL_SAMPLE_LT_20, TRADE_DISTRIBUTION_UNAVAILABLE, YEAR_BUCKET_COUNT_LT_2 |

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
