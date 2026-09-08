# Deterministic Synthetic Strategy Research Dossier v1

All numeric observations below come from fixed synthetic fixtures. They are not profitability evidence or trading permission.

## SOURCE
- Family bundle: `941901724a989b49649abbbf90c519595f62cf3b8c157c4850349c070076e36f`
- Robustness receipt: `73474f772b7e4567aaeed0fcec7f7e1907615787e5d962567272d7a18f7271ea`
- Statistical v3 receipt: `3e917119630fbd5f4335c8b8449ea55d80cc7a3a94194f77428dff24e18ab2a2`
- V14 full-rebuild receipt: `480772c268e528716e1e1c1bedea1ec2ec881f36f2f218beb88a2ea3bec5e75f`
- Protocol: Train -> Purge -> Validation -> Embargo -> Frozen.
- Frozen cost stress multiplies fee and slippage together at 1x, 2x, and 3x.
- Run counts from overlapping artifacts are not added.

### Fixed synthetic benchmarks
| Benchmark | Synthetic total return | Max drawdown |
| --- | ---: | ---: |
| buy_and_hold | -0.010915 | 0.040903 |
| cash | 0.000000 | 0.000000 |

### Registered strategy synthetic total-return observations
| Family | Strategy | Train | Validation | Frozen 1x | Frozen 2x | Frozen 3x |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| RANGE | bollinger | -0.016988 | 0.003833 | -0.001094 | -0.002635 | -0.004173 |
| TREND | dual_ma | -0.023207 | 0.000000 | -0.007796 | -0.008093 | -0.008389 |
| RANGE | grid | 0.030719 | 0.000000 | -0.032833 | -0.034141 | -0.035446 |
| TREND | macd | 0.034710 | 0.040857 | -0.008142 | -0.010222 | -0.012298 |
| TREND | momentum | -0.033912 | 0.047998 | -0.020062 | -0.022320 | -0.024574 |
| RANGE | rsi | -0.000850 | 0.004473 | 0.012436 | 0.009741 | 0.007053 |

## GAP
- `BOOTSTRAP_CONFIDENCE_INTERVAL_NOT_ESTIMATED`
- `COMPACT_DOSSIER_DOES_NOT_EMBED_V14_REPORT_JSON`
- `DEFLATED_SHARPE_RATIO_NOT_ESTIMATED`
- `ENSEMBLE_STRATEGY_NOT_IMPLEMENTED`
- `FORMAL_FROZEN_BLIND_TEST_GAP`
- `FORMAL_FROZEN_BLIND_TEST_NOT_EXECUTED`
- `FROZEN_STABILITY_REUSE_NOT_FORMAL_BLIND_EVIDENCE`
- `FULL_UNIT_PBO_IDENTIFIED_SET_REMAINS`
- `FULL_V14_REBUILD_REQUIRED_FOR_SEMANTIC_REVALIDATION`
- `MARKET_REGIME_ANALYSIS_NOT_EXECUTED`
- `MULTIPLE_TESTING_NOT_EXECUTED`
- `NO_FORMAL_INFERENCE_AUTHORITY`
- `ODD_THREE_TRIAL_MEDIAN_BOUNDARY_SENSITIVITY`
- `OVERLAPPING_WALK_FORWARD_WINDOWS_NO_INDEPENDENCE_CLAIM`
- `PARAMETER_STABILITY_NOT_EXECUTED`
- `PARTIAL_CSCV_RANK_TIE_GAP`
- `PARTIAL_PBO_IDENTIFIED_SET_REMAINS`
- `PROBABILITY_OF_BACKTEST_OVERFITTING_GAP`
- `PROBABILITY_OF_BACKTEST_OVERFITTING_NOT_ESTIMATED`
- `REAL_DATASET_GAP`
- `REAL_MARKET_DATA_NOT_USED`
- `SOURCE_COMMIT_NOT_BOUND_FOR_UNCOMMITTED_SLICE`
- `SYNTHETIC_DOSSIER_ONLY`
- `SYNTHETIC_FIXED_169_OBSERVATION_BOOTSTRAP_ONLY`
- `THREE_TRIAL_RANK_RESOLUTION_LIMIT`
- `THREE_TRIAL_SYNTHETIC_DIAGNOSTIC_ONLY`
- `TIE_AWARE_PBO_IDENTIFIED_SET_SYNTHETIC_ONLY`
- `TRAILING_OBSERVATION_EXCLUDED_FOR_EQUAL_CSCV_PARTITIONS`
- `WALK_FORWARD_NOT_EXECUTED`

## MATURITY
- Status: `BLOCK`
- Maturity: `SYNTHETIC_RESEARCH_DOSSIER_WITH_ALIGNED_STATISTICAL_REFERENCE_ONLY`
- RANGE and TREND families: observed on fixed synthetic fixtures.
- ENSEMBLE family: GAP; no registered implementation.
- Full-report statistical source alignment: TRUE for the recorded synthetic v14 rebuild only.
- Full v14 rebuild is required for semantic revalidation.

## PERMISSION
- Profitability proven: `false`
- Formal inference authorized: `false`
- Ranking authorized: `false`
- Paper authorized: `false`
- Live authorized: `false`
- Order entry authorized: `false`
