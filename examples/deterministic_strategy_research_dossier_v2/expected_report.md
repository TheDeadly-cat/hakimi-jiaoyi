# Deterministic Synthetic Strategy Research Dossier v2 Candidate

All observations are from fixed synthetic fixtures. They are not profitability evidence, formal inference, ranking permission, or trading authority.

## SOURCE
- Source dossier v1: `be3cefa29335da248d1b5ae70422bde344e3fb8f4f307e903f19ee1cd4d5b270`
- Benchmark-control bundle: `89ce8c8589ae5e59010f92f6e33f3a8270867162e51d8eb6ab18cca43fc8f1ec`
- Benchmark-control plan: `a4d35d7f5f9b7f5f70b5fa930cf8f1bc9816b61df84282b01b87f2425d510b54`
- Shared baseline bundle: `a74cdbf982b2919912cf6dc12de0c445b486a63b61b60ed71e8ce60942a347b7`
- Source runs reused: 32; additional synthetic control runs: 18.
- Candidate only: true; current activation: false.

### Synthetic control total-return observations
| Strategy Frozen total return | Cash | Buy and hold | Simple MA | Simple breakout | No-skill median | Volatility-matched buy and hold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| bollinger: -0.0010939999999999999 | 0 | -0.010914999999999999 | 0.0030790000000000001 | -0.019099999999999999 | -0.015769999999999999 | -0.0053857770301771746 |
| dual_ma: -0.007796 | 0 | -0.010914999999999999 | 0.0030790000000000001 | -0.019099999999999999 | -0.015769999999999999 | -0.0020062522948709471 |
| grid: -0.032833000000000001 | 0 | -0.010914999999999999 | 0.0030790000000000001 | -0.019099999999999999 | -0.015769999999999999 | -0.012670307909605327 |
| macd: -0.0081419999999999999 | 0 | -0.010914999999999999 | 0.0030790000000000001 | -0.019099999999999999 | -0.015769999999999999 | -0.010242836017230417 |
| momentum: -0.020062 | 0 | -0.010914999999999999 | 0.0030790000000000001 | -0.019099999999999999 | -0.015769999999999999 | -0.011935796892718398 |
| rsi: 0.012435999999999999 | 0 | -0.010914999999999999 | 0.0030790000000000001 | -0.019099999999999999 | -0.015769999999999999 | -0.0073539540411908799 |

### Synthetic strategy-minus-control return deltas
| Strategy minus control | Cash | Buy and hold | Simple MA | Simple breakout | No-skill median | Volatility-matched buy and hold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| bollinger | -0.0010939999999999999 | 0.0098209999999999999 | -0.0041729999999999996 | 0.018005999999999998 | 0.014676 | 0.0042917770301771751 |
| dual_ma | -0.007796 | 0.0031189999999999994 | -0.010874999999999999 | 0.011303999999999998 | 0.0079739999999999985 | -0.0057897477051290528 |
| grid | -0.032833000000000001 | -0.021918 | -0.035911999999999999 | -0.013733000000000002 | -0.017063000000000002 | -0.020162692090394674 |
| macd | -0.0081419999999999999 | 0.0027729999999999994 | -0.011221 | 0.010957999999999999 | 0.0076279999999999994 | 0.0021008360172304168 |
| momentum | -0.020062 | -0.0091470000000000006 | -0.023141000000000002 | -0.00096200000000000105 | -0.0042920000000000007 | -0.0081262031072816023 |
| rsi | 0.012435999999999999 | 0.023350999999999997 | 0.009356999999999999 | 0.031535999999999995 | 0.028205999999999998 | 0.019789954041190879 |

### Hash no-skill synthetic distribution
- Paths: 16
- Minimum: -0.045753000000000002
- Q25 Type-7: -0.027351
- Median Type-7: -0.015769999999999999
- Q75 Type-7: -0.0088564999999999998
- Maximum: 0.013688000000000001

## GAP
- `BENCHMARK_CONTROL_TO_RECORDED_V14_IDENTITY_ALIGNMENT_NOT_PROVEN`
- `COMPACT_DOSSIER_DOES_NOT_EMBED_V14_REPORT_JSON`
- `CONTROL_REBUILD_REQUIRED_FOR_SEMANTIC_REVALIDATION`
- `ENSEMBLE_STRATEGY_NOT_IMPLEMENTED`
- `EQUAL_VOLATILITY_PROJECTION_NOT_EXECUTABLE`
- `FORMAL_FROZEN_BLIND_TEST_GAP`
- `FORMAL_FROZEN_BLIND_TEST_NOT_EXECUTED`
- `FROZEN_STABILITY_REUSE_NOT_FORMAL_BLIND_EVIDENCE`
- `FULL_UNIT_PBO_IDENTIFIED_SET_REMAINS`
- `FULL_V14_REBUILD_REQUIRED_FOR_SEMANTIC_REVALIDATION`
- `MARKET_REGIME_ANALYSIS_NOT_EXECUTED`
- `NON_CURRENT_DOSSIER_V2_CANDIDATE`
- `NO_FORMAL_INFERENCE_AUTHORITY`
- `NO_SKILL_16_PATH_SYNTHETIC_DISTRIBUTION_ONLY`
- `ODD_THREE_TRIAL_MEDIAN_BOUNDARY_SENSITIVITY`
- `OVERLAPPING_WALK_FORWARD_WINDOWS_NO_INDEPENDENCE_CLAIM`
- `PARTIAL_CSCV_RANK_TIE_GAP`
- `PARTIAL_PBO_IDENTIFIED_SET_REMAINS`
- `PROBABILITY_OF_BACKTEST_OVERFITTING_GAP`
- `REAL_DATASET_GAP`
- `REAL_MARKET_DATA_NOT_USED`
- `REGISTERED_STRATEGIES_NOT_CONTROL_BENCHMARKS`
- `SIMPLE_CONTROL_PARAMETERS_NOT_OPTIMISED`
- `SOURCE_COMMIT_NOT_BOUND_FOR_UNCOMMITTED_SLICE`
- `SYNTHETIC_DOSSIER_ONLY`
- `SYNTHETIC_FIXED_169_OBSERVATION_BOOTSTRAP_ONLY`
- `THREE_TRIAL_RANK_RESOLUTION_LIMIT`
- `THREE_TRIAL_SYNTHETIC_DIAGNOSTIC_ONLY`
- `TIE_AWARE_PBO_IDENTIFIED_SET_SYNTHETIC_ONLY`
- `TRAILING_OBSERVATION_EXCLUDED_FOR_EQUAL_CSCV_PARTITIONS`
- `VOLATILITY_PROJECTION_FINANCING_AND_MARGIN_NOT_MODELLED`

## MATURITY
- Status: `BLOCK`
- Maturity: `SYNTHETIC_NON_CURRENT_BENCHMARK_CONTROL_PROJECTION_ONLY`
- The volatility-matched result is an ex-post synthetic projection, not an executable baseline.
- Exact control identity alignment to the recorded v14 report is not proven without a full rebuild.
- Dossier v1 remains current and byte-identical.

## PERMISSION
- Profitability proven: `false`
- Formal inference authorized: `false`
- Ranking authorized: `false`
- Paper authorized: `false`
- Live authorized: `false`
- Order entry authorized: `false`

## Frozen distribution metrics and Sharpe

This is a non-current synthetic projection of existing Frozen evidence. Undefined statistics remain undefined; no value is zero-filled.

| Strategy | Total return | CAGR | Annualized volatility | Sharpe | Sortino | Calmar | Max drawdown | Drawdown duration |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bollinger | -0.001094 | -0.002363 | 0.012587731185 | -0.123079 | -0.164605482769 | -0.18659769232 | 0.012663607843 | 68 |
| dual_ma | -0.007796 | -0.016773 | 0.004710098625 | -2.467717 | -2.45286772536 | -2.151487942535 | 0.007796 | 13 |
| grid | -0.032833 | -0.069609 | 0.029335995997 | -1.677145 | -2.02968146876 | -1.671531951482 | 0.041643834531 | 93 |
| macd | -0.008142 | -0.017514 | 0.023789173601 | -0.499079 | -0.563358475398 | -0.639125323269 | 0.027403076302 | 130 |
| momentum | -0.020062 | -0.042853 | 0.027661170624 | -1.075392 | -1.181230391387 | -1.542131200364 | 0.027788167433 | 158 |
| rsi | 0.012436 | 0.027071 | 0.017143595121 | 1.080379 | 1.639189949818 | 1.412625570345 | 0.019163606102 | 38 |

| Strategy | Profit factor | Win rate | Payoff ratio | Trade expectancy | Turnover | Fee load | Market exposure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bollinger | 0.977376929583 | 0.903225806452 | 0.104718956741 | -0.093712491569 | 2.317897398794 | 0.000499999994 | 0.405882352941 |
| dual_ma | undefined | 0 | undefined | -77.9628469515 | 0.492744261972 | 0.00050000001 | 0.035294117647 |
| grid | undefined | 0 | undefined | -109.495250857996 | 2.205462237012 | 0.000500000012 | 0.623529411765 |
| macd | 0.526443684096 | 0.166666666667 | 2.632218420481 | -13.570578163174 | 2.986773033396 | 0.000500000011 | 0.376470588235 |
| momentum | 0.183946542408 | 0.4 | 0.275919813613 | -40.123601402446 | 3.485233235607 | 0.000500000009 | 0.411764705882 |
| rsi | 2.822241251406 | 0.8 | 0.705560312851 | 41.485223247301 | 3.916919289243 | 0.000500000008 | 0.388235294118 |

| Strategy | VaR 95 | CVaR 95 | VaR 99 | CVaR 99 | Periods | Closed trades | Evidence state |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| bollinger | 0.001674034292 | 0.002344115 | 0.003099934859 | 0.003241383382 | 169 | 31 | PARTIAL |
| dual_ma | 0 | 0.000868773185 | 0.00157375589 | 0.002396768955 | 169 | 1 | PARTIAL |
| grid | 0.003171946619 | 0.004408619959 | 0.003642869873 | 0.008221135949 | 169 | 3 | PARTIAL |
| macd | 0.001549580038 | 0.004100229969 | 0.009006156694 | 0.011012657399 | 169 | 6 | PARTIAL |
| momentum | 0.002010649661 | 0.00438190197 | 0.003590256226 | 0.010991183577 | 169 | 5 | PARTIAL |
| rsi | 0.001771610465 | 0.002570779826 | 0.002895164715 | 0.003998806653 | 169 | 5 | PARTIAL |

### Distribution buckets and concentration

- `bollinger` monthly returns: `[{"partial_start":true,"period":"2021-03","return":"0"},{"partial_start":false,"period":"2021-04","return":"0"},{"partial_start":false,"period":"2021-05","return":"0.002897"},{"partial_start":false,"period":"2021-06","return":"0.008370749937"},{"partial_start":false,"period":"2021-07","return":"-0.000369823948"},{"partial_start":false,"period":"2021-08","return":"-0.011882269383"}]`
- `bollinger` monthly summary: `{"count":6,"maximum":"0.008370749937","mean":"-0.000164057232","median":"0","minimum":"-0.011882269383","negative_count":2,"positive_count":2,"zero_count":2}`
- `bollinger` yearly returns: `[{"partial_start":true,"period":"2021","return":"-0.001094"}]`
- `bollinger` yearly summary: `{"count":1,"maximum":"-0.001094","mean":"-0.001094","median":"-0.001094","minimum":"-0.001094","negative_count":1,"positive_count":0,"zero_count":0}`
- `bollinger` concentration: `{"best_fixed_21_period_window":{"candidate_count":149,"compounded_return":"0.012437516786","end_index_exclusive":112,"end_time":"2021-06-26 00:00:00+00:00","gap_code":null,"start_index":91,"start_time":"2021-06-05 00:00:00+00:00","state":"OBSERVED","window_length":21},"compound_return_without_best_month":"-0.009386180567","compound_return_without_best_period":"-0.003307614608","pnl_without_best_trade":"-14.862710206662","positive_period_return_hhi":"0.052438749964","positive_trade_pnl_hhi":"0.059960547436","top_positive_month_share":"0.742894542726","top_positive_period_return_share":"0.075056726719","top_positive_trade_pnl_share":"0.095274162722"}`
- `bollinger` gaps: `["YEAR_BUCKET_COUNT_LT_2"]`
- `dual_ma` monthly returns: `[{"partial_start":true,"period":"2021-03","return":"0"},{"partial_start":false,"period":"2021-04","return":"0"},{"partial_start":false,"period":"2021-05","return":"0"},{"partial_start":false,"period":"2021-06","return":"0"},{"partial_start":false,"period":"2021-07","return":"0"},{"partial_start":false,"period":"2021-08","return":"-0.007796"}]`
- `dual_ma` monthly summary: `{"count":6,"maximum":"0","mean":"-0.001299333333","median":"0","minimum":"-0.007796","negative_count":1,"positive_count":0,"zero_count":5}`
- `dual_ma` yearly returns: `[{"partial_start":true,"period":"2021","return":"-0.007796"}]`
- `dual_ma` yearly summary: `{"count":1,"maximum":"-0.007796","mean":"-0.007796","median":"-0.007796","minimum":"-0.007796","negative_count":1,"positive_count":0,"zero_count":0}`
- `dual_ma` concentration: `{"best_fixed_21_period_window":{"candidate_count":149,"compounded_return":"0","end_index_exclusive":21,"end_time":"2021-03-27 00:00:00+00:00","gap_code":null,"start_index":0,"start_time":"2021-03-06 00:00:00+00:00","state":"OBSERVED","window_length":21},"compound_return_without_best_month":"-0.007796","compound_return_without_best_period":"-0.007796","pnl_without_best_trade":null,"positive_period_return_hhi":null,"positive_trade_pnl_hhi":null,"top_positive_month_share":null,"top_positive_period_return_share":null,"top_positive_trade_pnl_share":null}`
- `dual_ma` gaps: `["POSITIVE_MONTH_CONCENTRATION_UNAVAILABLE","POSITIVE_PERIOD_CONCENTRATION_UNAVAILABLE","POSITIVE_TRADE_CONCENTRATION_UNAVAILABLE","PROFIT_FACTOR_AND_PAYOFF_UNDEFINED_ONE_SIDED_TRADES","YEAR_BUCKET_COUNT_LT_2"]`
- `grid` monthly returns: `[{"partial_start":true,"period":"2021-03","return":"0"},{"partial_start":false,"period":"2021-04","return":"0"},{"partial_start":false,"period":"2021-05","return":"-0.012225"},{"partial_start":false,"period":"2021-06","return":"0.013416010731"},{"partial_start":false,"period":"2021-07","return":"-0.00275017557"},{"partial_start":false,"period":"2021-08","return":"-0.031160783512"}]`
- `grid` monthly summary: `{"count":6,"maximum":"0.013416010731","mean":"-0.005453324725","median":"-0.001375087785","minimum":"-0.031160783512","negative_count":3,"positive_count":1,"zero_count":2}`
- `grid` yearly returns: `[{"partial_start":true,"period":"2021","return":"-0.032833"}]`
- `grid` yearly summary: `{"count":1,"maximum":"-0.032833","mean":"-0.032833","median":"-0.032833","minimum":"-0.032833","negative_count":1,"positive_count":0,"zero_count":0}`
- `grid` concentration: `{"best_fixed_21_period_window":{"candidate_count":149,"compounded_return":"0.022255745216","end_index_exclusive":149,"end_time":"2021-08-02 00:00:00+00:00","gap_code":null,"start_index":128,"start_time":"2021-07-12 00:00:00+00:00","state":"OBSERVED","window_length":21},"compound_return_without_best_month":"-0.045636747635","compound_return_without_best_period":"-0.036827343643","pnl_without_best_trade":null,"positive_period_return_hhi":"0.029754070704","positive_trade_pnl_hhi":null,"top_positive_month_share":"1","top_positive_period_return_share":"0.052762879605","top_positive_trade_pnl_share":null}`
- `grid` gaps: `["POSITIVE_TRADE_CONCENTRATION_UNAVAILABLE","PROFIT_FACTOR_AND_PAYOFF_UNDEFINED_ONE_SIDED_TRADES","YEAR_BUCKET_COUNT_LT_2"]`
- `macd` monthly returns: `[{"partial_start":true,"period":"2021-03","return":"0"},{"partial_start":false,"period":"2021-04","return":"-0.005726"},{"partial_start":false,"period":"2021-05","return":"-0.005476357624"},{"partial_start":false,"period":"2021-06","return":"0.001956860084"},{"partial_start":false,"period":"2021-07","return":"0.00630422583"},{"partial_start":false,"period":"2021-08","return":"-0.005167450678"}]`
- `macd` monthly summary: `{"count":6,"maximum":"0.00630422583","mean":"-0.001351453731","median":"-0.002583725339","minimum":"-0.005726","negative_count":3,"positive_count":2,"zero_count":1}`
- `macd` yearly returns: `[{"partial_start":true,"period":"2021","return":"-0.008142"}]`
- `macd` yearly summary: `{"count":1,"maximum":"-0.008142","mean":"-0.008142","median":"-0.008142","minimum":"-0.008142","negative_count":1,"positive_count":0,"zero_count":0}`
- `macd` concentration: `{"best_fixed_21_period_window":{"candidate_count":149,"compounded_return":"0.015361119081","end_index_exclusive":149,"end_time":"2021-08-02 00:00:00+00:00","gap_code":null,"start_index":128,"start_time":"2021-07-12 00:00:00+00:00","state":"OBSERVED","window_length":21},"compound_return_without_best_month":"-0.014355724104","compound_return_without_best_period":"-0.011049984392","pnl_without_best_trade":"-171.940413937154","positive_period_return_hhi":"0.037428292965","positive_trade_pnl_hhi":"1","top_positive_month_share":"0.763123140908","top_positive_period_return_share":"0.064390401254","top_positive_trade_pnl_share":"1"}`
- `macd` gaps: `["YEAR_BUCKET_COUNT_LT_2"]`
- `momentum` monthly returns: `[{"partial_start":true,"period":"2021-03","return":"-0.003012"},{"partial_start":false,"period":"2021-04","return":"-0.003781389545"},{"partial_start":false,"period":"2021-05","return":"-0.003272192006"},{"partial_start":false,"period":"2021-06","return":"0.012263022643"},{"partial_start":false,"period":"2021-07","return":"-0.007204812256"},{"partial_start":false,"period":"2021-08","return":"-0.015026817089"}]`
- `momentum` monthly summary: `{"count":6,"maximum":"0.012263022643","mean":"-0.003339031376","median":"-0.003526790776","minimum":"-0.015026817089","negative_count":5,"positive_count":1,"zero_count":0}`
- `momentum` yearly returns: `[{"partial_start":true,"period":"2021","return":"-0.020062"}]`
- `momentum` yearly summary: `{"count":1,"maximum":"-0.020062","mean":"-0.020062","median":"-0.020062","minimum":"-0.020062","negative_count":1,"positive_count":0,"zero_count":0}`
- `momentum` concentration: `{"best_fixed_21_period_window":{"candidate_count":149,"compounded_return":"0.013771152199","end_index_exclusive":118,"end_time":"2021-07-02 00:00:00+00:00","gap_code":null,"start_index":97,"start_time":"2021-06-11 00:00:00+00:00","state":"OBSERVED","window_length":21},"compound_return_without_best_month":"-0.031933422361","compound_return_without_best_period":"-0.022882072918","pnl_without_best_trade":"-236.768856718612","positive_period_return_hhi":"0.037905087871","positive_trade_pnl_hhi":"0.679305926968","top_positive_month_share":"1","top_positive_period_return_share":"0.061066741003","top_positive_trade_pnl_share":"0.799421047162"}`
- `momentum` gaps: `["YEAR_BUCKET_COUNT_LT_2"]`
- `rsi` monthly returns: `[{"partial_start":true,"period":"2021-03","return":"-0.00133"},{"partial_start":false,"period":"2021-04","return":"0.010114452221"},{"partial_start":false,"period":"2021-05","return":"0.006110405632"},{"partial_start":false,"period":"2021-06","return":"0.009881420978"},{"partial_start":false,"period":"2021-07","return":"0.00698756249"},{"partial_start":false,"period":"2021-08","return":"-0.01907712818"}]`
- `rsi` monthly summary: `{"count":6,"maximum":"0.010114452221","mean":"0.00211445219","median":"0.006548984061","minimum":"-0.01907712818","negative_count":2,"positive_count":4,"zero_count":0}`
- `rsi` yearly returns: `[{"partial_start":true,"period":"2021","return":"0.012436"}]`
- `rsi` yearly summary: `{"count":1,"maximum":"0.012436","mean":"0.012436","median":"0.012436","minimum":"0.012436","negative_count":0,"positive_count":1,"zero_count":0}`
- `rsi` concentration: `{"best_fixed_21_period_window":{"candidate_count":149,"compounded_return":"0.015721946013","end_index_exclusive":111,"end_time":"2021-06-25 00:00:00+00:00","gap_code":null,"start_index":90,"start_time":"2021-06-04 00:00:00+00:00","state":"OBSERVED","window_length":21},"compound_return_without_best_month":"0.002298301716","compound_return_without_best_period":"0.008364548129","pnl_without_best_trade":"119.713544064325","positive_period_return_hhi":"0.037892558454","positive_trade_pnl_hhi":"0.251646748459","top_positive_month_share":"0.305629440925","top_positive_period_return_share":"0.074693087019","top_positive_trade_pnl_share":"0.273029861899"}`
- `rsi` gaps: `["YEAR_BUCKET_COUNT_LT_2"]`

## Frozen cost-stress observations

These are non-current synthetic observations from existing Frozen runs. Cost-role labels and embedded FROZEN_TEST experiment roles are preserved separately.

| Strategy | Cost role | Manifest role | Fee rate | Slippage rate | Total return | Delta vs 1x | Sharpe | Delta vs 1x | Max drawdown | Delta vs 1x | Total fees | Delta vs 1x |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bollinger | FROZEN_COST_1X | FROZEN_TEST | 0.00050000000000000001 | 0.00020000000000000001 | -0.001094 | 0 | -0.123079 | 0 | 0.012664 | 0 | 11.641488 | 0 |
| bollinger | FROZEN_COST_2X | FROZEN_TEST | 0.001 | 0.00040000000000000002 | -0.002635 | -0.001541 | -0.299457 | -0.176378 | 0.013321 | 0.000657 | 23.266497 | 11.625009 |
| bollinger | FROZEN_COST_3X | FROZEN_TEST | 0.0015 | 0.00060000000000000006 | -0.004173 | -0.003079 | -0.46897 | -0.345891 | 0.013977 | 0.001313 | 34.875044 | 23.233556 |
| dual_ma | FROZEN_COST_1X | FROZEN_TEST | 0.00050000000000000001 | 0.00020000000000000001 | -0.007796 | 0 | -2.467717 | 0 | 0.007796 | 0 | 2.46275 | 0 |
| dual_ma | FROZEN_COST_2X | FROZEN_TEST | 0.001 | 0.00040000000000000002 | -0.008093 | -0.000297 | -2.474849 | -0.007132 | 0.008093 | 0.000297 | 4.926 | 2.46325 |
| dual_ma | FROZEN_COST_3X | FROZEN_TEST | 0.0015 | 0.00060000000000000006 | -0.008389 | -0.000593 | -2.477586 | -0.009869 | 0.008389 | 0.000593 | 7.389749 | 4.926999 |
| grid | FROZEN_COST_1X | FROZEN_TEST | 0.00050000000000000001 | 0.00020000000000000001 | -0.032833 | 0 | -1.677145 | 0 | 0.041644 | 0 | 10.956866 | 0 |
| grid | FROZEN_COST_2X | FROZEN_TEST | 0.001 | 0.00040000000000000002 | -0.034141 | -0.001308 | -1.738876 | -0.061731 | 0.042686 | 0.001042 | 21.900771 | 10.943905 |
| grid | FROZEN_COST_3X | FROZEN_TEST | 0.0015 | 0.00060000000000000006 | -0.035446 | -0.002613 | -1.799709 | -0.122564 | 0.043743 | 0.002099 | 32.831727 | 21.874861 |
| macd | FROZEN_COST_1X | FROZEN_TEST | 0.00050000000000000001 | 0.00020000000000000001 | -0.008142 | 0 | -0.499079 | 0 | 0.027403 | 0 | 14.83485 | 0 |
| macd | FROZEN_COST_2X | FROZEN_TEST | 0.001 | 0.00040000000000000002 | -0.010222 | -0.00208 | -0.632588 | -0.133509 | 0.028871 | 0.001468 | 29.643838 | 14.808988 |
| macd | FROZEN_COST_3X | FROZEN_TEST | 0.0015 | 0.00060000000000000006 | -0.012298 | -0.004156 | -0.766388 | -0.267309 | 0.030397 | 0.002994 | 44.427001 | 29.592151 |
| momentum | FROZEN_COST_1X | FROZEN_TEST | 0.00050000000000000001 | 0.00020000000000000001 | -0.020062 | 0 | -1.075392 | 0 | 0.027788 | 0 | 17.307232 | 0 |
| momentum | FROZEN_COST_2X | FROZEN_TEST | 0.001 | 0.00040000000000000002 | -0.02232 | -0.002258 | -1.195626 | -0.120234 | 0.029792 | 0.002004 | 34.576912 | 17.26968 |
| momentum | FROZEN_COST_3X | FROZEN_TEST | 0.0015 | 0.00060000000000000006 | -0.024574 | -0.004512 | -1.300085 | -0.224693 | 0.031793 | 0.004005 | 51.809115 | 34.501883 |
| rsi | FROZEN_COST_1X | FROZEN_TEST | 0.00050000000000000001 | 0.00020000000000000001 | 0.012436 | 0 | 1.080379 | 0 | 0.019163 | 0 | 19.878512 | 0 |
| rsi | FROZEN_COST_2X | FROZEN_TEST | 0.001 | 0.00040000000000000002 | 0.009741 | -0.002695 | 0.834663 | -0.245716 | 0.020067 | 0.000904 | 39.703767 | 19.825255 |
| rsi | FROZEN_COST_3X | FROZEN_TEST | 0.0015 | 0.00060000000000000006 | 0.007053 | -0.005383 | 0.596522 | -0.483857 | 0.020969 | 0.001806 | 59.475901 | 39.597389 |

| Strategy | Fees non-decreasing | Returns non-increasing | Drawdowns non-decreasing |
| --- | --- | --- | --- |
| bollinger | true | true | true |
| dual_ma | true | true | true |
| grid | true | true | true |
| macd | true | true | true |
| momentum | true | true | true |
| rsi | true | true | true |

These observations do not prove profitability, formal inference, ranking authority, paper authority, live authority, or order-entry authority.

## Frozen experiment provenance

- Native manifest verification: `18/18`
- Reproducibility complete: `false`
- Blocker counts: `{"git_worktree_not_clean":18}`

Each entry below is projected from an identity-bound manifest after native verification against the result payload with the embedded manifest removed.

### `bollinger` / `frozen_1x`
- experiment_id: `hexp-1b7598a8cea6fe61ad70`
- strategy_name: `bollinger`; strategy_version: `v1`
- git_commit_sha: `0000000000000000000000000000000000000000`; git_worktree_clean: `false`
- config_hash: `8f7bbface93c4eab9868780197275c7a30d73cbb561cbe917d082a08a19f3031`; dataset_hash: `c67ec18da478febe4cf551971ea41192dfe9d4fc8029827e9ddd7f67b36d9287`
- dependency_lock_name: `requirements.research.lock`; dependency_lock_hash: `2e12c00f613160e974a3c94f23ee2b058f6fed4ae7843d7747b318173d65d320`; dependency_lock_fully_pinned: `true`
- evaluation_protocol_hash: `6718f51a7ebcbba68cb04addbe8b48e5775654f91ae1e2fbaf38d60455a36cc6`; evaluation_protocol_verified: `true`
- window: `2021-02-04 00:00:00+00:00` to `2021-08-22 00:00:00+00:00`; symbol/timeframe: `SYNTH` / `1d`
- random_seed: `0`; runtime_version: `python-3.14`
- fee_model: `{"kind":"proportional","rate":"0.00050000000000000001"}`; slippage_model: `{"kind":"proportional","rate":"0.00020000000000000001"}`
- result_hash: `f01dd6f6e8bd4d2fffc041f0f12a2841ec894c71a85b7bfc1acbb0f2a1f2f4b9`; source_run_hash: `ddfe552e20620195a5be1094c03a06e7fb03dfa0220d1f376efcacab4715f6bf`; manifest_hash: `36fabb231d681e5c97e214d2242746d08a83a5f8a3704e990756bed0fd8a4903`
- classification/status: `REPRODUCIBILITY_INCOMPLETE` / `BLOCK`; blockers: `["git_worktree_not_clean"]`

### `bollinger` / `frozen_2x`
- experiment_id: `hexp-99ef85e54e69e2263348`
- strategy_name: `bollinger`; strategy_version: `v1`
- git_commit_sha: `0000000000000000000000000000000000000000`; git_worktree_clean: `false`
- config_hash: `8064a2deb42a71da36edf46261a1e94318632f9d9443584e62f1d5d0f02812b6`; dataset_hash: `c67ec18da478febe4cf551971ea41192dfe9d4fc8029827e9ddd7f67b36d9287`
- dependency_lock_name: `requirements.research.lock`; dependency_lock_hash: `2e12c00f613160e974a3c94f23ee2b058f6fed4ae7843d7747b318173d65d320`; dependency_lock_fully_pinned: `true`
- evaluation_protocol_hash: `6718f51a7ebcbba68cb04addbe8b48e5775654f91ae1e2fbaf38d60455a36cc6`; evaluation_protocol_verified: `true`
- window: `2021-02-04 00:00:00+00:00` to `2021-08-22 00:00:00+00:00`; symbol/timeframe: `SYNTH` / `1d`
- random_seed: `0`; runtime_version: `python-3.14`
- fee_model: `{"kind":"proportional","rate":"0.001"}`; slippage_model: `{"kind":"proportional","rate":"0.00040000000000000002"}`
- result_hash: `caa4e4a1016016a9ebfac79f1236ab7ed391385743449062d3a891427de61217`; source_run_hash: `1cac83f612eb48f0e081dd64912c636744a73501f306e591ab19ec786e4979dd`; manifest_hash: `3e517cf0f5896406ce2e3dad87d2f83a428eba443dc3fbe36f8e9e299f1a8558`
- classification/status: `REPRODUCIBILITY_INCOMPLETE` / `BLOCK`; blockers: `["git_worktree_not_clean"]`

### `bollinger` / `frozen_3x`
- experiment_id: `hexp-96e9096d4f22baa4f8f1`
- strategy_name: `bollinger`; strategy_version: `v1`
- git_commit_sha: `0000000000000000000000000000000000000000`; git_worktree_clean: `false`
- config_hash: `ec3d63c8ca02f201bf7e854200f233229e158cdd3ae69bc318f4a0302076411c`; dataset_hash: `c67ec18da478febe4cf551971ea41192dfe9d4fc8029827e9ddd7f67b36d9287`
- dependency_lock_name: `requirements.research.lock`; dependency_lock_hash: `2e12c00f613160e974a3c94f23ee2b058f6fed4ae7843d7747b318173d65d320`; dependency_lock_fully_pinned: `true`
- evaluation_protocol_hash: `6718f51a7ebcbba68cb04addbe8b48e5775654f91ae1e2fbaf38d60455a36cc6`; evaluation_protocol_verified: `true`
- window: `2021-02-04 00:00:00+00:00` to `2021-08-22 00:00:00+00:00`; symbol/timeframe: `SYNTH` / `1d`
- random_seed: `0`; runtime_version: `python-3.14`
- fee_model: `{"kind":"proportional","rate":"0.0015"}`; slippage_model: `{"kind":"proportional","rate":"0.00060000000000000006"}`
- result_hash: `1d2842b60ac4724c98f5072067b9ca2713f195f988e559f5418e410fc8a5469b`; source_run_hash: `f22a2ad7095164cf2d6a94811033cada52a53dcf128dd7c59cf58766fc7b124d`; manifest_hash: `a2e3a01096cf81eb908d915953ce14ced24dcca2ae16de9ebd8b711c32f6fa88`
- classification/status: `REPRODUCIBILITY_INCOMPLETE` / `BLOCK`; blockers: `["git_worktree_not_clean"]`

### `dual_ma` / `frozen_1x`
- experiment_id: `hexp-1441e996e60de44bac9c`
- strategy_name: `dual_ma`; strategy_version: `v1`
- git_commit_sha: `0000000000000000000000000000000000000000`; git_worktree_clean: `false`
- config_hash: `0a41e70f1a29bed547ae4ca8db4fa46dddc172bae2ef945aeea2194865984d94`; dataset_hash: `c67ec18da478febe4cf551971ea41192dfe9d4fc8029827e9ddd7f67b36d9287`
- dependency_lock_name: `requirements.research.lock`; dependency_lock_hash: `2e12c00f613160e974a3c94f23ee2b058f6fed4ae7843d7747b318173d65d320`; dependency_lock_fully_pinned: `true`
- evaluation_protocol_hash: `6718f51a7ebcbba68cb04addbe8b48e5775654f91ae1e2fbaf38d60455a36cc6`; evaluation_protocol_verified: `true`
- window: `2021-02-04 00:00:00+00:00` to `2021-08-22 00:00:00+00:00`; symbol/timeframe: `SYNTH` / `1d`
- random_seed: `0`; runtime_version: `python-3.14`
- fee_model: `{"kind":"proportional","rate":"0.00050000000000000001"}`; slippage_model: `{"kind":"proportional","rate":"0.00020000000000000001"}`
- result_hash: `ed4f73bc878b8f3fae4a924287c2bf4b2b3182c13b3dbf4d1d2b34eaa16ce8f2`; source_run_hash: `54acef00b0990c5a4ec5e8b0c47bcf23660670323c3b8515efc4b882d5972923`; manifest_hash: `f9b27064feb71b4157b183e392a46f0a668bd4f1a30c04cc0ec0ff2ddcf92b54`
- classification/status: `REPRODUCIBILITY_INCOMPLETE` / `BLOCK`; blockers: `["git_worktree_not_clean"]`

### `dual_ma` / `frozen_2x`
- experiment_id: `hexp-dfb5b13b15b27b3a808e`
- strategy_name: `dual_ma`; strategy_version: `v1`
- git_commit_sha: `0000000000000000000000000000000000000000`; git_worktree_clean: `false`
- config_hash: `0561fb21157651c496559b775c13cfefb07d58f428f58386c27998b6f34875db`; dataset_hash: `c67ec18da478febe4cf551971ea41192dfe9d4fc8029827e9ddd7f67b36d9287`
- dependency_lock_name: `requirements.research.lock`; dependency_lock_hash: `2e12c00f613160e974a3c94f23ee2b058f6fed4ae7843d7747b318173d65d320`; dependency_lock_fully_pinned: `true`
- evaluation_protocol_hash: `6718f51a7ebcbba68cb04addbe8b48e5775654f91ae1e2fbaf38d60455a36cc6`; evaluation_protocol_verified: `true`
- window: `2021-02-04 00:00:00+00:00` to `2021-08-22 00:00:00+00:00`; symbol/timeframe: `SYNTH` / `1d`
- random_seed: `0`; runtime_version: `python-3.14`
- fee_model: `{"kind":"proportional","rate":"0.001"}`; slippage_model: `{"kind":"proportional","rate":"0.00040000000000000002"}`
- result_hash: `6e7430bc48cf44aec3566407e8f4ee28e03068e6e0eabaac03fbc47e89d4e1c7`; source_run_hash: `08f90ab603c1ec787d447c2826c25a525c25adb15b61a074207edb4771525101`; manifest_hash: `6ad6d1502c690070a63b2aa1a366582c902e27f1cb82fb507f6e9c2250439ced`
- classification/status: `REPRODUCIBILITY_INCOMPLETE` / `BLOCK`; blockers: `["git_worktree_not_clean"]`

### `dual_ma` / `frozen_3x`
- experiment_id: `hexp-10ff4cd286edcd4de19d`
- strategy_name: `dual_ma`; strategy_version: `v1`
- git_commit_sha: `0000000000000000000000000000000000000000`; git_worktree_clean: `false`
- config_hash: `3e2f51dc26c841bafa918666f675c9b34c53031743742caae141423902820cf5`; dataset_hash: `c67ec18da478febe4cf551971ea41192dfe9d4fc8029827e9ddd7f67b36d9287`
- dependency_lock_name: `requirements.research.lock`; dependency_lock_hash: `2e12c00f613160e974a3c94f23ee2b058f6fed4ae7843d7747b318173d65d320`; dependency_lock_fully_pinned: `true`
- evaluation_protocol_hash: `6718f51a7ebcbba68cb04addbe8b48e5775654f91ae1e2fbaf38d60455a36cc6`; evaluation_protocol_verified: `true`
- window: `2021-02-04 00:00:00+00:00` to `2021-08-22 00:00:00+00:00`; symbol/timeframe: `SYNTH` / `1d`
- random_seed: `0`; runtime_version: `python-3.14`
- fee_model: `{"kind":"proportional","rate":"0.0015"}`; slippage_model: `{"kind":"proportional","rate":"0.00060000000000000006"}`
- result_hash: `d2e0f9030945d7d44e8b69cd483a4b082ecd67657d19a1559bf5105111ba3ca1`; source_run_hash: `508a934d4bfd990f7ec3a1fcbd12fd54879a3f1062bbf8880dc46abcc477b4ca`; manifest_hash: `4f4328bedb6737039e05e4fc57bc8400d2a639cee546fa961ed4704caa64a016`
- classification/status: `REPRODUCIBILITY_INCOMPLETE` / `BLOCK`; blockers: `["git_worktree_not_clean"]`

### `grid` / `frozen_1x`
- experiment_id: `hexp-782f14bf58b13d50f8e9`
- strategy_name: `grid`; strategy_version: `v1`
- git_commit_sha: `0000000000000000000000000000000000000000`; git_worktree_clean: `false`
- config_hash: `fb8b936da3e40a7aaa04cb67bdc245f8e42b08f4bd95789b2ee99c0ee785f801`; dataset_hash: `c67ec18da478febe4cf551971ea41192dfe9d4fc8029827e9ddd7f67b36d9287`
- dependency_lock_name: `requirements.research.lock`; dependency_lock_hash: `2e12c00f613160e974a3c94f23ee2b058f6fed4ae7843d7747b318173d65d320`; dependency_lock_fully_pinned: `true`
- evaluation_protocol_hash: `6718f51a7ebcbba68cb04addbe8b48e5775654f91ae1e2fbaf38d60455a36cc6`; evaluation_protocol_verified: `true`
- window: `2021-02-04 00:00:00+00:00` to `2021-08-22 00:00:00+00:00`; symbol/timeframe: `SYNTH` / `1d`
- random_seed: `0`; runtime_version: `python-3.14`
- fee_model: `{"kind":"proportional","rate":"0.00050000000000000001"}`; slippage_model: `{"kind":"proportional","rate":"0.00020000000000000001"}`
- result_hash: `a374ca0ff9e9c42e7fc80bf71d10bc97ae5c398765f70417fe8e02c645a5c288`; source_run_hash: `f160c81089ee6e1a4728faea79d1d80b30f5d5a1ca3282d82670dc0e59b95e2d`; manifest_hash: `08552ed86db0eea7ba4bc03226c47686a5f6efde2f93c9d94656d79b11b2403f`
- classification/status: `REPRODUCIBILITY_INCOMPLETE` / `BLOCK`; blockers: `["git_worktree_not_clean"]`

### `grid` / `frozen_2x`
- experiment_id: `hexp-b3769fb8f8e91f7f6a75`
- strategy_name: `grid`; strategy_version: `v1`
- git_commit_sha: `0000000000000000000000000000000000000000`; git_worktree_clean: `false`
- config_hash: `c8d881bcdb5dcd004d8f174aac851995365f602671793ff0e04ec8e6a836f73b`; dataset_hash: `c67ec18da478febe4cf551971ea41192dfe9d4fc8029827e9ddd7f67b36d9287`
- dependency_lock_name: `requirements.research.lock`; dependency_lock_hash: `2e12c00f613160e974a3c94f23ee2b058f6fed4ae7843d7747b318173d65d320`; dependency_lock_fully_pinned: `true`
- evaluation_protocol_hash: `6718f51a7ebcbba68cb04addbe8b48e5775654f91ae1e2fbaf38d60455a36cc6`; evaluation_protocol_verified: `true`
- window: `2021-02-04 00:00:00+00:00` to `2021-08-22 00:00:00+00:00`; symbol/timeframe: `SYNTH` / `1d`
- random_seed: `0`; runtime_version: `python-3.14`
- fee_model: `{"kind":"proportional","rate":"0.001"}`; slippage_model: `{"kind":"proportional","rate":"0.00040000000000000002"}`
- result_hash: `7d197703e8adf6103ac607a666d8e9666989f697a78a8c4eac379961a92e6dc5`; source_run_hash: `bb8e1f15a0dcff1a926c3d95d5e3b96dba75d21b2fcb56b2aacad9e729d0e907`; manifest_hash: `f84295078b15ee7632c4ea50f6dbcdb5e82ed9288c1336529d635661d29326f2`
- classification/status: `REPRODUCIBILITY_INCOMPLETE` / `BLOCK`; blockers: `["git_worktree_not_clean"]`

### `grid` / `frozen_3x`
- experiment_id: `hexp-8995d344780115c2b356`
- strategy_name: `grid`; strategy_version: `v1`
- git_commit_sha: `0000000000000000000000000000000000000000`; git_worktree_clean: `false`
- config_hash: `8391525ff9224d33b4c4f3f02280e9296688e1906ddc51df27b686522f464f89`; dataset_hash: `c67ec18da478febe4cf551971ea41192dfe9d4fc8029827e9ddd7f67b36d9287`
- dependency_lock_name: `requirements.research.lock`; dependency_lock_hash: `2e12c00f613160e974a3c94f23ee2b058f6fed4ae7843d7747b318173d65d320`; dependency_lock_fully_pinned: `true`
- evaluation_protocol_hash: `6718f51a7ebcbba68cb04addbe8b48e5775654f91ae1e2fbaf38d60455a36cc6`; evaluation_protocol_verified: `true`
- window: `2021-02-04 00:00:00+00:00` to `2021-08-22 00:00:00+00:00`; symbol/timeframe: `SYNTH` / `1d`
- random_seed: `0`; runtime_version: `python-3.14`
- fee_model: `{"kind":"proportional","rate":"0.0015"}`; slippage_model: `{"kind":"proportional","rate":"0.00060000000000000006"}`
- result_hash: `71e7deba10a5c3445b823b4be38c54ff7e42acd9103870aadde5b0624a5086a6`; source_run_hash: `77393b6bcca5e3ea069c04bbdaf0484497187c7b9731ebb7edde4843417d3fc1`; manifest_hash: `5f78a0bb10af7532a6aa16260dbf83669215edf56601a8f9f821fffc1c9aa9e9`
- classification/status: `REPRODUCIBILITY_INCOMPLETE` / `BLOCK`; blockers: `["git_worktree_not_clean"]`

### `macd` / `frozen_1x`
- experiment_id: `hexp-58d5e1aea23a96874714`
- strategy_name: `macd`; strategy_version: `v1`
- git_commit_sha: `0000000000000000000000000000000000000000`; git_worktree_clean: `false`
- config_hash: `8b843d933118cd4590001396343a9f03aa986ba6978a27092246d0f914e7a095`; dataset_hash: `c67ec18da478febe4cf551971ea41192dfe9d4fc8029827e9ddd7f67b36d9287`
- dependency_lock_name: `requirements.research.lock`; dependency_lock_hash: `2e12c00f613160e974a3c94f23ee2b058f6fed4ae7843d7747b318173d65d320`; dependency_lock_fully_pinned: `true`
- evaluation_protocol_hash: `6718f51a7ebcbba68cb04addbe8b48e5775654f91ae1e2fbaf38d60455a36cc6`; evaluation_protocol_verified: `true`
- window: `2021-02-04 00:00:00+00:00` to `2021-08-22 00:00:00+00:00`; symbol/timeframe: `SYNTH` / `1d`
- random_seed: `0`; runtime_version: `python-3.14`
- fee_model: `{"kind":"proportional","rate":"0.00050000000000000001"}`; slippage_model: `{"kind":"proportional","rate":"0.00020000000000000001"}`
- result_hash: `e13693facb336f176619d8ffe2314c2daae941ceaa4c9e3eb214474a66374758`; source_run_hash: `fde06597ae0252a0e9bb3bf6b3bab5e5ef2f01039fa433f4b9be1fb0455b0c8e`; manifest_hash: `ffda0ac092fe128a5012d1445f6029850d32b65806b336fc8a046babba78fe50`
- classification/status: `REPRODUCIBILITY_INCOMPLETE` / `BLOCK`; blockers: `["git_worktree_not_clean"]`

### `macd` / `frozen_2x`
- experiment_id: `hexp-14465fdca41745f5197c`
- strategy_name: `macd`; strategy_version: `v1`
- git_commit_sha: `0000000000000000000000000000000000000000`; git_worktree_clean: `false`
- config_hash: `1c1cabc0f7e72a694ce5486b2a0e1a981da4249c925046328a36601cee386cde`; dataset_hash: `c67ec18da478febe4cf551971ea41192dfe9d4fc8029827e9ddd7f67b36d9287`
- dependency_lock_name: `requirements.research.lock`; dependency_lock_hash: `2e12c00f613160e974a3c94f23ee2b058f6fed4ae7843d7747b318173d65d320`; dependency_lock_fully_pinned: `true`
- evaluation_protocol_hash: `6718f51a7ebcbba68cb04addbe8b48e5775654f91ae1e2fbaf38d60455a36cc6`; evaluation_protocol_verified: `true`
- window: `2021-02-04 00:00:00+00:00` to `2021-08-22 00:00:00+00:00`; symbol/timeframe: `SYNTH` / `1d`
- random_seed: `0`; runtime_version: `python-3.14`
- fee_model: `{"kind":"proportional","rate":"0.001"}`; slippage_model: `{"kind":"proportional","rate":"0.00040000000000000002"}`
- result_hash: `7cff659ff12ce064e950bb451391874652260f8a39fcfe12b4e9a77a8072939c`; source_run_hash: `46b16498d4906bef9f929d83b4776d1b10f63e22099607a3d4b28a8a656f7d9f`; manifest_hash: `2016add2b19925c9519824807d7e4f7322cdbbc8efdb24e6ba73105c0109a680`
- classification/status: `REPRODUCIBILITY_INCOMPLETE` / `BLOCK`; blockers: `["git_worktree_not_clean"]`

### `macd` / `frozen_3x`
- experiment_id: `hexp-45714e0f6a8480fceaf9`
- strategy_name: `macd`; strategy_version: `v1`
- git_commit_sha: `0000000000000000000000000000000000000000`; git_worktree_clean: `false`
- config_hash: `13e55b3fafd4ce238ea025d90d2b6efe3ca8ad3b996d668694e77e6cb0476dbc`; dataset_hash: `c67ec18da478febe4cf551971ea41192dfe9d4fc8029827e9ddd7f67b36d9287`
- dependency_lock_name: `requirements.research.lock`; dependency_lock_hash: `2e12c00f613160e974a3c94f23ee2b058f6fed4ae7843d7747b318173d65d320`; dependency_lock_fully_pinned: `true`
- evaluation_protocol_hash: `6718f51a7ebcbba68cb04addbe8b48e5775654f91ae1e2fbaf38d60455a36cc6`; evaluation_protocol_verified: `true`
- window: `2021-02-04 00:00:00+00:00` to `2021-08-22 00:00:00+00:00`; symbol/timeframe: `SYNTH` / `1d`
- random_seed: `0`; runtime_version: `python-3.14`
- fee_model: `{"kind":"proportional","rate":"0.0015"}`; slippage_model: `{"kind":"proportional","rate":"0.00060000000000000006"}`
- result_hash: `8a18ec02144745de0ec81056d7b0a9725238678fa45c3b925475c09b378b7709`; source_run_hash: `62dc861d8d1a30af3829ce03cb4fb65a9ccc658d9a09ea232b6e4b4ed3c80b46`; manifest_hash: `645953b7e122b4f7e56734cc3dfe16e73485b3cf8478be4372bdbc3411dcab27`
- classification/status: `REPRODUCIBILITY_INCOMPLETE` / `BLOCK`; blockers: `["git_worktree_not_clean"]`

### `momentum` / `frozen_1x`
- experiment_id: `hexp-4721244d20b0851509db`
- strategy_name: `momentum`; strategy_version: `v1`
- git_commit_sha: `0000000000000000000000000000000000000000`; git_worktree_clean: `false`
- config_hash: `42ef31907084d8820d813b5f25c76e2478f11c3c7c75979246dc7890dc537abf`; dataset_hash: `c67ec18da478febe4cf551971ea41192dfe9d4fc8029827e9ddd7f67b36d9287`
- dependency_lock_name: `requirements.research.lock`; dependency_lock_hash: `2e12c00f613160e974a3c94f23ee2b058f6fed4ae7843d7747b318173d65d320`; dependency_lock_fully_pinned: `true`
- evaluation_protocol_hash: `6718f51a7ebcbba68cb04addbe8b48e5775654f91ae1e2fbaf38d60455a36cc6`; evaluation_protocol_verified: `true`
- window: `2021-02-04 00:00:00+00:00` to `2021-08-22 00:00:00+00:00`; symbol/timeframe: `SYNTH` / `1d`
- random_seed: `0`; runtime_version: `python-3.14`
- fee_model: `{"kind":"proportional","rate":"0.00050000000000000001"}`; slippage_model: `{"kind":"proportional","rate":"0.00020000000000000001"}`
- result_hash: `7f136453c14e47d86355321eaae8e42fb8857974cf74d3aaa85b90dfa49fdd60`; source_run_hash: `dfbb3297cc0738c29b0c0a690255ce4f67e867b92608472b64aafd3fc620fb35`; manifest_hash: `c9927bf9a47dc3cbe3861abe94d1659edf9d47dda785a4e35752d01320b2f51b`
- classification/status: `REPRODUCIBILITY_INCOMPLETE` / `BLOCK`; blockers: `["git_worktree_not_clean"]`

### `momentum` / `frozen_2x`
- experiment_id: `hexp-ab2b74d6887acd8cbbfd`
- strategy_name: `momentum`; strategy_version: `v1`
- git_commit_sha: `0000000000000000000000000000000000000000`; git_worktree_clean: `false`
- config_hash: `76c9e022a6f4b784eb157bd6428d691dda5ab4f3959c64d8054d4836de0747f0`; dataset_hash: `c67ec18da478febe4cf551971ea41192dfe9d4fc8029827e9ddd7f67b36d9287`
- dependency_lock_name: `requirements.research.lock`; dependency_lock_hash: `2e12c00f613160e974a3c94f23ee2b058f6fed4ae7843d7747b318173d65d320`; dependency_lock_fully_pinned: `true`
- evaluation_protocol_hash: `6718f51a7ebcbba68cb04addbe8b48e5775654f91ae1e2fbaf38d60455a36cc6`; evaluation_protocol_verified: `true`
- window: `2021-02-04 00:00:00+00:00` to `2021-08-22 00:00:00+00:00`; symbol/timeframe: `SYNTH` / `1d`
- random_seed: `0`; runtime_version: `python-3.14`
- fee_model: `{"kind":"proportional","rate":"0.001"}`; slippage_model: `{"kind":"proportional","rate":"0.00040000000000000002"}`
- result_hash: `c0507a361b1235dc5bcfe44ec135a83be766a2e313a5624944e0b6ed49fbfd4c`; source_run_hash: `89664eee80f6fa782e36dd6fb456abf05cab5c17379cdf18639529412d68a6b5`; manifest_hash: `0e30d1e3d6f34566c323553e0423dbeada02190aa63f09fe20a5c6ab2bac371b`
- classification/status: `REPRODUCIBILITY_INCOMPLETE` / `BLOCK`; blockers: `["git_worktree_not_clean"]`

### `momentum` / `frozen_3x`
- experiment_id: `hexp-517bb9c0d3945b5fa111`
- strategy_name: `momentum`; strategy_version: `v1`
- git_commit_sha: `0000000000000000000000000000000000000000`; git_worktree_clean: `false`
- config_hash: `177cded0badcdcb37af19c6600649046eea137bbb19d100ecd213ce6b3a2d582`; dataset_hash: `c67ec18da478febe4cf551971ea41192dfe9d4fc8029827e9ddd7f67b36d9287`
- dependency_lock_name: `requirements.research.lock`; dependency_lock_hash: `2e12c00f613160e974a3c94f23ee2b058f6fed4ae7843d7747b318173d65d320`; dependency_lock_fully_pinned: `true`
- evaluation_protocol_hash: `6718f51a7ebcbba68cb04addbe8b48e5775654f91ae1e2fbaf38d60455a36cc6`; evaluation_protocol_verified: `true`
- window: `2021-02-04 00:00:00+00:00` to `2021-08-22 00:00:00+00:00`; symbol/timeframe: `SYNTH` / `1d`
- random_seed: `0`; runtime_version: `python-3.14`
- fee_model: `{"kind":"proportional","rate":"0.0015"}`; slippage_model: `{"kind":"proportional","rate":"0.00060000000000000006"}`
- result_hash: `563570a8744a200cdb7a0b23adb85a72828b44879bb10c86bcb785c30c2dbb34`; source_run_hash: `6e761de72705c63f77e02f7b498904920184ab4668f4d33dad3cfb726082ef09`; manifest_hash: `e9b8aa838345977b65fcabbe914178077e87c380f2c5207ca11ab40217b42e14`
- classification/status: `REPRODUCIBILITY_INCOMPLETE` / `BLOCK`; blockers: `["git_worktree_not_clean"]`

### `rsi` / `frozen_1x`
- experiment_id: `hexp-99c3a4f09cc9cbe14545`
- strategy_name: `rsi`; strategy_version: `v1`
- git_commit_sha: `0000000000000000000000000000000000000000`; git_worktree_clean: `false`
- config_hash: `dd2c8cf305a551967481dbe0f73e61784088b72e382e886c8d69402fb4d82f60`; dataset_hash: `c67ec18da478febe4cf551971ea41192dfe9d4fc8029827e9ddd7f67b36d9287`
- dependency_lock_name: `requirements.research.lock`; dependency_lock_hash: `2e12c00f613160e974a3c94f23ee2b058f6fed4ae7843d7747b318173d65d320`; dependency_lock_fully_pinned: `true`
- evaluation_protocol_hash: `6718f51a7ebcbba68cb04addbe8b48e5775654f91ae1e2fbaf38d60455a36cc6`; evaluation_protocol_verified: `true`
- window: `2021-02-04 00:00:00+00:00` to `2021-08-22 00:00:00+00:00`; symbol/timeframe: `SYNTH` / `1d`
- random_seed: `0`; runtime_version: `python-3.14`
- fee_model: `{"kind":"proportional","rate":"0.00050000000000000001"}`; slippage_model: `{"kind":"proportional","rate":"0.00020000000000000001"}`
- result_hash: `b829bd1c180765bc5a85a211aad806db210fe300304691bc66a57578ab9db36e`; source_run_hash: `872605bc3a783deb4153022862c38c0152149a92ae413169afc48654f49fd6ef`; manifest_hash: `c560535204df4212fde17eb163578aa7719c671a091778bb82539300528c1e9c`
- classification/status: `REPRODUCIBILITY_INCOMPLETE` / `BLOCK`; blockers: `["git_worktree_not_clean"]`

### `rsi` / `frozen_2x`
- experiment_id: `hexp-7651003ca5333845f874`
- strategy_name: `rsi`; strategy_version: `v1`
- git_commit_sha: `0000000000000000000000000000000000000000`; git_worktree_clean: `false`
- config_hash: `1cb44c2f0d4a0a2d0ba8c5689cf0d341f44d6dc5c62aa044a6a2df00a718974c`; dataset_hash: `c67ec18da478febe4cf551971ea41192dfe9d4fc8029827e9ddd7f67b36d9287`
- dependency_lock_name: `requirements.research.lock`; dependency_lock_hash: `2e12c00f613160e974a3c94f23ee2b058f6fed4ae7843d7747b318173d65d320`; dependency_lock_fully_pinned: `true`
- evaluation_protocol_hash: `6718f51a7ebcbba68cb04addbe8b48e5775654f91ae1e2fbaf38d60455a36cc6`; evaluation_protocol_verified: `true`
- window: `2021-02-04 00:00:00+00:00` to `2021-08-22 00:00:00+00:00`; symbol/timeframe: `SYNTH` / `1d`
- random_seed: `0`; runtime_version: `python-3.14`
- fee_model: `{"kind":"proportional","rate":"0.001"}`; slippage_model: `{"kind":"proportional","rate":"0.00040000000000000002"}`
- result_hash: `a6d84ddd316660a52ee0db9fbe34a2e2bd96eefdf16e79576d2cca250fc91a7f`; source_run_hash: `0b78f2bfd740711ecfca0214ab79b291702ab7fe7b170c48b332240daa22fa20`; manifest_hash: `b6c5997b9b1b887a2ae66f0379faad5f2b10f8d6e7519e301f10777e854a1b62`
- classification/status: `REPRODUCIBILITY_INCOMPLETE` / `BLOCK`; blockers: `["git_worktree_not_clean"]`

### `rsi` / `frozen_3x`
- experiment_id: `hexp-74b41664926513af1314`
- strategy_name: `rsi`; strategy_version: `v1`
- git_commit_sha: `0000000000000000000000000000000000000000`; git_worktree_clean: `false`
- config_hash: `18126b0827cb9c7bffc99b15c2f39654fd7ea5889b6b3165881195a6bba40442`; dataset_hash: `c67ec18da478febe4cf551971ea41192dfe9d4fc8029827e9ddd7f67b36d9287`
- dependency_lock_name: `requirements.research.lock`; dependency_lock_hash: `2e12c00f613160e974a3c94f23ee2b058f6fed4ae7843d7747b318173d65d320`; dependency_lock_fully_pinned: `true`
- evaluation_protocol_hash: `6718f51a7ebcbba68cb04addbe8b48e5775654f91ae1e2fbaf38d60455a36cc6`; evaluation_protocol_verified: `true`
- window: `2021-02-04 00:00:00+00:00` to `2021-08-22 00:00:00+00:00`; symbol/timeframe: `SYNTH` / `1d`
- random_seed: `0`; runtime_version: `python-3.14`
- fee_model: `{"kind":"proportional","rate":"0.0015"}`; slippage_model: `{"kind":"proportional","rate":"0.00060000000000000006"}`
- result_hash: `2d8d8dfb95c5968462671221fd3df0042e65c72701bf0a4fd3eff7dc293d9dc9`; source_run_hash: `9e0ccb987f2c90e190f91e65b9ff8190a00ab22194ed931446c04c9a45805575`; manifest_hash: `22e3c518d4e7f358faf97b61ee85f19d0c2b21b5b44445210e335dd9def36d52`
- classification/status: `REPRODUCIBILITY_INCOMPLETE` / `BLOCK`; blockers: `["git_worktree_not_clean"]`

This provenance projection does not prove reproducibility, profitability, formal inference, ranking authority, paper authority, live authority, or order-entry authority.

## Evidence gap reconciliation

- Inherited GAP count: `37`
- Resolved stale GAP count: `6`
- Retained GAP count: `31`
- Robustness receipt: `73474f772b7e4567aaeed0fcec7f7e1907615787e5d962567272d7a18f7271ea`
- Statistical-v3 receipt: `3e917119630fbd5f4335c8b8449ea55d80cc7a3a94194f77428dff24e18ab2a2`

### Resolved stale GAP identifiers
- `BOOTSTRAP_CONFIDENCE_INTERVAL_NOT_ESTIMATED`
- `DEFLATED_SHARPE_RATIO_NOT_ESTIMATED`
- `MULTIPLE_TESTING_NOT_EXECUTED`
- `PARAMETER_STABILITY_NOT_EXECUTED`
- `PROBABILITY_OF_BACKTEST_OVERFITTING_NOT_ESTIMATED`
- `WALK_FORWARD_NOT_EXECUTED`

### Existing robustness evidence
- Robustness runs: `147`; total source plus robustness runs: `179`
- `WALK_FORWARD_EXECUTED`
- `PARAMETER_STABILITY_EXECUTED`
- `MULTIPLE_TESTING_LEDGER_COMPLETE`
- `BONFERRONI_AND_BH_DIAGNOSTICS_COMPUTED`
- `DEPENDENCY_LOCK_BOUND_TO_ALL_ROBUSTNESS_RUNS`

### Existing statistical-v3 evidence
- Bootstrap observed/gap evidence: `6/0`; replicates: `1000`
- Deflated Sharpe diagnostics: `6`
- CSCV PBO observed/gap evidence: `4/2`

Only stale NOT_EXECUTED/NOT_ESTIMATED labels with exact bound replacement evidence are removed. Partial PBO identification, overlapping-window dependence, real-data, formal-blind-test and authority gaps remain.
This reconciliation does not prove profitability or authorize formal inference, ranking, paper, live, or order entry.
