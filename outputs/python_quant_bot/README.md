# Hakimi Jiaoyi Research Platform

Hakimi Jiaoyi 是本地、离线优先、research-only 的量化策略研究与风险评估平台。
它用于验证数据、运行历史回测、审阅研究证据和导出报告，不代表策略盈利，
也不提供模拟盘、实盘、订单输入或自动参数选择权限。

## 产品能力真相源

产品能力的唯一正式源码是根目录
`src/hakimi_research/product_capabilities.py`。其中 `capability-v1` 固定执行权限，
`product-capability-catalog-v2` 提供 Supported / Experimental / Disabled /
Archived 状态。CLI、dashboard 和 health projection 直接消费 canonical 模块；
旧 `exchange_terminal.domain.contracts` 仅做对象身份一致的兼容 re-export。
Electron 对 health projection 做 exact fail-closed 校验，并由跨运行时合同锁定目录一致性。

| 能力 | 状态 |
| --- | --- |
| `product_capability_catalog` | Supported |
| `market_data_research` | Supported |
| `historical_backtest` | Supported |
| `deterministic_frozen_benchmark` | Supported |
| `deterministic_strategy_family_benchmark` | Supported |
| `deterministic_strategy_robustness_benchmark` | Supported |
| `deterministic_strategy_statistical_correction_benchmark` | Supported |
| `research_reporting` | Supported |
| `strategy_catalog` | Supported |
| `local_research_terminal` | Experimental |
| `parameter_optimization` | Archived |
| `paper_execution` | Archived |
| `live_execution` | Archived |
| `order_entry` | Disabled |

这些状态不构成盈利、成熟度、paper 或 live 授权。`capability-v1` 继续固定为
`product_mode=research_only`、`research_only=true`、`paper_allowed=false`、
`live_allowed=false`。

## 已支持研究模块

- 市场数据研究：OKX 公共历史数据、显式 CSV 和数据来源证据
- 历史回测：确定性 OHLCV 回放、手续费和滑点假设、权益与风险报告
- 策略目录：查看内置规则策略，不自动选择或晋级参数
- 研究报告：本地结果审阅与导出
- 风险边界：历史场景中的仓位、亏损与回撤限制

## 快速运行

交易所终端：

```powershell
.\start_exchange_terminal.bat
```

它会打开本地地址：

```text
http://127.0.0.1:8765
```

这是 Experimental 本地研究界面。价格、信号、相关性、回测和自然前向证据
只用于研究，不是订单建议、盈利证明或交易权限。

旧 Streamlit 历史研究控制台：

```powershell
.\start_dashboard.bat
```

如果打不开，先运行环境检查：

```powershell
.\check_environment.bat
```

如果提示缺少依赖，先运行：

```powershell
.\install_dependencies.bat
```

启动脚本会自动寻找 Python 3.14、3.13、3.12、3.11。如果仍然找不到 Python，通常是安装后没有重启终端，或安装时没有勾选 `Add python.exe to PATH`。

在仓库根目录通过唯一 canonical 入口运行：

```powershell
.\hakimi-research.ps1 backtest
```

查看内置策略：

```powershell
.\hakimi-research.ps1 list-strategies
```

查看机器可读能力目录：

```powershell
.\hakimi-research.ps1 capabilities
```

验证 compact、source-controlled 的纯合成策略稳健性参考：

```powershell
.\hakimi-research.ps1 strategy-robustness-benchmark
```

该命令在内存中重建 32 个 source 与 147 个 robustness 运行；保存的收据不含
完整运行包，状态保持 BLOCK，且不构成正式盲测、收益、排名或交易权限。

验证 compact、source-controlled 的统计纠偏参考：

```powershell
.\hakimi-research.ps1 strategy-statistical-correction-benchmark
```

该命令在同一 v2 matrix 上重建描述性 DSR、CSCV-PBO 与 tie-aware bounds。
compact 收据不保存 DSR probability、PBO rate 或区间数值，且不构成正式推断、
排名、参数选择、收益或交易权限。

显式验证同时绑定 Bootstrap-v2 的版本化参考时使用：

```powershell
.\hakimi-research.ps1 strategy-statistical-correction-benchmark --statistical-reference-version v2
```

v1 仍是默认 reference；v2 复用同一 179-run 纯合成组件图，Bootstrap 不新增回测，
并继续保持 `BLOCK`、无正式推断、无收益结论和无交易权限。

CLI 只展示 Supported 命令。旧 `run_bot.py` 只保留 canonical 对象的兼容导出；
历史 `paper` 和 `optimize` 函数保留为兼容门禁，
但状态为 Archived，不能通过环境变量重新开启。

## 配置文件

见 `config.example.json`。控制台会自动生成 `config.local.json` 保存本机配置。核心字段：

- `mode`: 固定为 `backtest`
- `market`: `crypto`、`stock`、`futures`
- `data.provider`: `okx`、`csv`、`synthetic`
- `data.cache_dir`: 历史行情缓存目录
- `data.use_cache`: 是否启用历史行情缓存
- `strategy.name`: 内置策略名称
- `strategy.params`: 策略参数
- `risk`: 风控参数
- `execution`: 历史成交费用和滑点假设，不连接账户

## 归档能力说明

parameter optimization、paper execution 和 live execution 均为 Archived，
order entry 为 Disabled。遗留 `PaperBroker` 类只作为确定性历史成交模拟器存在，
不代表产品提供 paper 账户或 paper 自动执行。任何配置中的 live/ccxt 请求都会
被 fail-closed 边界覆盖。

遗留 `/api/paper/*` HTTP 路径由 canonical 产品目录驱动的统一分类器前置处理。
仅 ledger、lifecycle、portfolio 和 snapshot 的 GET 历史视图保持 READ_ONLY；
所有其他方法和子路径均返回 BLOCK。七个历史 paper mutation dispatch 分支已从
正式 server 删除；路径继续保留在 `MUTATION_PATHS`，使旧客户端得到明确 423，
而不是重新进入业务逻辑或被误判为受支持能力。

## 当前可复现研究 dossier

当前面向人工审阅的紧凑入口为：

```powershell
.\hakimi-research.ps1 strategy-research-dossier
```

该命令只验证 source-controlled 的
`../../examples/deterministic_strategy_research_dossier_v1` 参考字节、来源谱系和
组件身份，不会运行耗时的 report-v14 完整重建。报告覆盖两个固定合成基准、
六个已登记的 RANGE/TREND 策略变体，以及 Train、Validation、Frozen
1x/2x/3x 成本观察。ENSEMBLE 仍是明确缺口，没有已登记实现。

紧凑校验不能替代 report-v14 的完整语义重建。当前结论仍为 `BLOCK`；formal
inference、paper、live 和 order entry 均未授权。
## 软件化路线

当前形态是“本地研究平台 + 历史回测与证据审阅界面”。下一阶段优先建设
可复现实验清单、数据质量合同、明确基准、Train / Validation / Frozen Test、
walk-forward、purge / embargo、成本压力测试和参数稳定性分析。在这些证据闭合前，
不增加更多交易策略，不开放 paper/live，也不扩张订单型 UI。

当前 canonical fixture 使用 `frozen-evaluation-protocol-v17`、
`frozen-evaluation-report-v22` 和 `frozen-evaluation-markdown-v22`。根入口
`hakimi-research.ps1 frozen-benchmark` 只重建并验证 source-controlled 合成证据，
包括固定分区、三档成本、基准、walk-forward、参数稳定性、multiple-testing
lineage、固定市场状态切片和 partial tail/distribution 字段。质量仍为 BLOCK；
真实市场、长周期、外部预登记、单次消费、自然前向和充分尾部样本均未建立。

交易所终端说明见 `docs/exchange_terminal.md`。

## 自定义策略

新增策略时继承 `StrategyBase`，实现 `generate_signal`：

```python
from quant_bot.strategies.base import StrategyBase
from quant_bot.models import Signal

class MyStrategy(StrategyBase):
    name = "my_strategy"

    def generate_signal(self, data, portfolio):
        return Signal.hold("not ready")
```

然后在 `quant_bot/strategies/templates.py` 的 `STRATEGY_REGISTRY` 注册即可。

## 目录结构

```text
repository root
├─ hakimi-research.ps1       # canonical Windows CLI
├─ requirements.research.lock # canonical dependency closure
├─ src\hakimi_research
│  ├─ __main__.py            # python -m hakimi_research
│  ├─ cli.py                 # only CLI implementation
│  └─ product_capabilities.py
└─ outputs\python_quant_bot
   ├─ run_bot.py             # compatibility export only
   ├─ config.example.json
   └─ quant_bot              # compatibility re-export only
```

## 当前证据边界

- 每份历史回测自动生成 `reproducible-experiment-manifest-v1`，绑定 Git、依赖、
  数据、配置、策略版本、区间、成本、随机种子、运行时和结果哈希。
- 脏工作树、未锁依赖或缺失 Git 身份会明确 BLOCK；TRAIN/UNCLASSIFIED 结果不能
  进入 ranking input。
- 回测结果不是盈利证明。
- 参数、排行榜或 AI 输出不能自动晋级策略。
- paper 和 live 永久未授权，订单入口关闭。
- legacy pack-v5 的公共读取保持 UNKNOWN。
- pointer-v2 保持原字段与哈希合同，不自动重发。
- 自然前向 single-look 链保持不变。

核心 `quant_bot` 包的正式实现已迁到根 `src/hakimi_research`；历史
`outputs/python_quant_bot/quant_bot` 现在仅保留 14 个 exact canonical re-export，
由 `quant-bot-compatibility-package-audit-v1` 阻止 class/function、动态执行或导入目标
回退。Exchange Terminal、桌面静态资源和历史研究链仍需逐消费者迁移或归档，不能把
核心包闭合描述成全仓库搬迁完成。

Exchange Terminal 的通用纯函数现由
`src/hakimi_research/terminal_utils.py` 持有，历史 `exchange_terminal/utils.py`
仅保留 canonical 对象身份一致的兼容出口。Server、market-data、stock research 和
canonical rehearsal 均直接消费根实现；这不代表 server/config/static 已完成迁移。

Exchange Terminal 配置现在由 `src/hakimi_research/terminal_config.py` 持有，旧
`exchange_terminal/config.py` 仅作对象身份一致的兼容出口。本地 `.env.local` 不再在
默认 import 时探测；只有显式设置 `HAKIMI_LOAD_LOCAL_AI_ENV=1` 且未启用 skip、
read-only 或 test 隔离时，才会读取固定 allowlist 的 AI 环境项。

根级 `.github/workflows/research-contracts.yml` 提供最小研究合同 CI：只安装根级
`requirements.research.lock`、检查确定性输入身份并运行显式合同模块，同时覆盖
根 `src/**` canonical source。它不引用
密钥、不启动产品入口，也不授予 paper/live/order 权限。只有远端实际运行才能
证明 CI 状态；本地存在或语法检查不能称为 CI green。

## Reproducible research identity

The active historical-backtest CLI uses the repository-root
`requirements.research.lock`, an exact
five-package runtime closure. `hakimi_research.experiment_manifest` hashes this scoped
lock before the broad optional dependency inventory.

`hakimi_research.config` is the canonical research configuration source. File
configuration rejects archived paper/live/optimizer intent, non-finite JSON,
synthetic provider selection, and any execution label other than
`research_simulator` with exchange `disabled`; it never silently rewrites unsafe
intent into an apparently valid research run.

The canonical root fixture is now
`../../examples/deterministic_frozen_benchmark_v2`. The single product entrypoint
`../../hakimi-research.ps1 frozen-benchmark` reconstructs and verifies its 128-row
synthetic Frozen OOS, benchmark, and 1x/2x/3x cost-stress report without network
access, cache use, services, or runtime writes. Its quality status remains
`BLOCK`; a pass is not real-data evidence, a formal blind test, a profitability
claim, ranking permission, or trading authority. The former 40-row input-only
fixture is preserved byte-identically under
`../../archive/historical_research/adr0525_input_identity_v1`.

## 历史实现记录（全部非当前产品能力）

以下内容保留历史来源和决策记录，不是当前 CLI、UI、single-look、权限或发布状态。

### Verified validation evidence (ADR0510, dormant)

The canonical research package now contains a dormant exact-native validation evidence contract and a versioned v2 report composition layer. It binds walk-forward windows with purge/embargo, parameter-stability observations, complete multiple-testing outcomes, and four market-regime slices to an ADR0509 report digest. It does not activate a CLI/UI producer and does not grant profitability, blind-test, paper, live, or order-entry authority.

The first dormant producer adapter verifies strategy_research_search_lineage v2 and binds its complete artifact digest, lineage digest, search family, and current/cumulative trial counts to the concrete ADR0510 trial ledger. This is count/history provenance only; per-trial outcomes remain separately identified by the ADR0510 ledger.

ADR0510 now includes a dormant verified-report projection for concrete per-trial identities. Every formal variant receipt binds its parameter and implementation identity, selection/test cell hashes, aggregate ranking, frozen-test membership, test result, and the formal report batch hash. Observed BLOCK decisions and their blockers remain visible; the adapter does not rerun research or select a candidate post hoc.

The dormant ADR0510 report can now derive and exactly replay tail/distribution observations from a report-contained BacktestReport result. Undefined metrics remain null with explicit gaps; the implementation does not treat missing downside, losses, trades, months, or years as zero.

### Actual strategy inventory

The current public strategy registry contains six single strategies: bollinger, grid, rsi, dual_ma, macd, and momentum. RANGE and TREND are mechanism-family labels over those registered members, not registered strategy aliases. No Ensemble strategy or combination engine exists in the current source tree, so a claimed Range/Trend/Ensemble three-family report remains BLOCK with NO_REGISTERED_ENSEMBLE_STRATEGY.

### Pure synthetic strategy baseline bundle

The dormant `synthetic-strategy-report-bundle-v1` producer now executes the six actual registered strategies against one deterministic in-memory OHLCV fixture. Its preregistered 32-run batch covers fixed Train/Validation/Frozen partitions, 10-row purge and embargo gaps, Frozen fee/slippage stress at 1x/2x/3x, and Frozen CASH and BUY_AND_HOLD benchmarks. Every result, distribution evidence object, partition, plan, report, and bundle is SHA-256 bound and supports exact in-memory replay.

This bundle is a wiring and reproducibility fixture only. It keeps `REAL_MARKET_DATA_NOT_USED`, formal frozen blind test, walk-forward, parameter stability, multiple testing, dependency lock, source commit, and Ensemble as explicit gaps. The renderer remains neutral SOURCE -> GAP -> MATURITY -> PERMISSION, the bundle remains BLOCK, and all profitability, paper, live, and order-entry authority remains false. Targeted contract coverage is 10 tests plus syntax compilation; no network, cache, database, runtime artifact, formal runner, or trading task is used.

### Pure synthetic robustness evidence

The dormant `synthetic-strategy-robustness-evidence-v1` consumer extends a verified v1 baseline bundle with 147 preregistered in-memory runs. For each of the six registered strategies it executes three ordered walk-forward windows with purge/embargo, retains every center/neighbor Train and Validation trial, evaluates only the Validation-selected parameter on each test window, and runs a three-point Frozen stability batch without using Frozen outcomes for selection. The producer builds and verifies the existing canonical `validation-evidence-v1` contract for every strategy.

The complete trial ledger also carries bounded Bonferroni and Benjamini-Hochberg diagnostics. These are explicitly synthetic diagnostics, not formal inference. Market-regime execution, Deflated Sharpe Ratio, Probability of Backtest Overfitting, bootstrap intervals, real data, a formal frozen blind test, dependency-lock/source-commit evidence, and Ensemble remain visible gaps. The renderer remains neutral and every profitability or trading authority stays false. Targeted contract coverage is 10 tests plus syntax compilation, including an exact 147-run replay.

## Deterministic synthetic benchmark report entrypoint v1 (2026-08-30)

The `synthetic-strategy-benchmark-report-v1` entrypoint composes the already verified Frozen/cost-stress bundle and walk-forward/stability/multiplicity evidence into one reproducible research-only report.

- Entrypoint: `examples/build_synthetic_strategy_benchmark_report_v1.py`
- Default invocation is a dry plan: `planned_run_count=179`, `executed_run_count=0`, `runtime_mutations=false`.
- Full execution requires explicit `--execute` and remains pure synthetic/in-memory: 32 Frozen/cost-stress runs plus 147 robustness runs.
- Plan SHA-256: `d2164df92703f238c6219128debb61d72a34bc94edc9efec59207c998125f65b`.
- Entrypoint source SHA-256: `b5eec0b7448953a65e9bc532d287632588ce54d5ee8d371d36ae3dbe83e9d107`.
- Contract test SHA-256: `c9912ea88ea0f1ec279c504087b7757760ea30c453ebd68e32bad5a38ce87cde`.
- Targeted validation: `py_compile` PASS; entrypoint contract `10/10 PASS` in 12.399 seconds.
- The verifier binds both preregistered plans, both complete evidence objects, the outer report digest, and the all-false authority contract.
- Renderer order remains neutral: `SOURCE -> GAP -> MATURITY -> PERMISSION`; status remains `BLOCK`.
- This evidence is synthetic only. It does not prove profitability, complete a formal Frozen blind test, or authorize paper, live, or order entry.
- Explicit remaining gaps include real datasets, formal Frozen blind testing, market-regime analysis, dependency/source identities, Ensemble, DSR, PBO, and bootstrap confidence intervals.

## Non-current synthetic benchmark report v2 (2026-08-30)

The `synthetic-strategy-benchmark-report-v2` candidate composes the immutable v1 benchmark report with source-bound market-regime validation. It is not current and does not change any pointer, permission, or v1 identity.

- Entrypoint: `examples/build_synthetic_strategy_benchmark_report_v2.py`.
- Default invocation is a dry plan: `planned_run_count=179`, `executed_run_count=0`, `planned_market_analysis_count=6`, `additional_backtest_run_count=0`, `runtime_mutations=false`.
- Plan SHA-256: `e89f08443b31ab597c5cbca89a999858edf478009382c2e9ad310b951466f93c`.
- Market-regime core SHA-256: `48b0bd0c5643e3b0db1d8aff4978c354bc8ec4f06592ede01dc46baabfac99bd`.
- Market-regime adapter SHA-256: `744abda3043d625bb03b2893c6df420f6ee3e3ceba1093c552df69132323ef0c`.
- V2 entrypoint SHA-256: `d068dec6c8ce94d4680084686247bd9a457833161837472b015012bd545f1a4f`.
- V2 contract test SHA-256: `9dc2fd1df30fd6a227f5114e02da88b206d32f4675d5d7fa1c774bb7be96054a`.
- Targeted validation: market-regime contract `10/10 PASS` in 14.049 seconds; v2 entrypoint contract `10/10 PASS` in 18.339 seconds; related `py_compile` checks PASS.
- The fixed causal policy uses a 20-bar trailing window and one-bar label lag. It was not tuned after observing strategy performance.
- Six strategies produce 18 observed slices across BULL, BEAR, and RANGE. HIGH_VOLATILITY has zero coverage at the preregistered 20% annualized threshold, so six required slices remain GAP.
- V2 refines the top-level `MARKET_REGIME_ANALYSIS_GAP` to `HIGH_VOLATILITY_REGIME_COVERAGE_GAP` without rewriting the nested v1 source report.
- Evidence state remains `GAP`; permission status remains `BLOCK`; paper, live, order entry, blind-test completion, and profitability authority remain false.
- This is synthetic-only evidence. It is not a real-data result, profitability proof, formal Frozen blind test, current-version promotion, or trading authorization.

## Non-current synthetic benchmark report v3 (2026-08-30)

The `synthetic-strategy-benchmark-report-v3` candidate composes the verified non-current v2 report with source-bound paired moving-block bootstrap evidence. It is not current and does not change a pointer, permission, or prior report identity.

- Entrypoint: `examples/build_synthetic_strategy_benchmark_report_v3.py`.
- Default invocation is a dry plan: `planned_run_count=179`, `executed_run_count=0`, `planned_market_analysis_count=6`, `planned_bootstrap_analysis_count=6`, `additional_backtest_run_count=0`, `runtime_mutations=false`.
- Plan SHA-256: `6c771706085c8601a669cea85125fd8420383a0d76b898265e1285c698ee4376`.
- Bootstrap policy is preregistered and deterministic: 169 paired Frozen observations per strategy, block length 5, 1,000 SHA-derived moving-block replicates, and 95% Type-7 linear percentile intervals. It uses no runtime PRNG, performance selection, or post-observation policy tuning.
- Execution reuses the 179 v2 source runs and six market-regime analyses, performs six bootstrap analyses, and adds zero backtest runs.
- Bootstrap core SHA-256: `98c13ae78f4e9493a053d0d5a4a35d1e26c890127705c101f82f4931d4f450c5`.
- Bootstrap adapter SHA-256: `a71aa4c71e36697db0e459a21f654b4f19b9cb2f1347a62d6c51502333ebf19d`.
- Bootstrap contract test SHA-256: `e45f55ca7cc383fa66a197942d4293613a9644a06ebd5d2d64241f7ae0d3107b`.
- V3 entrypoint SHA-256: `b20fc259090ea7941d1c304cbd6c197ec0f4aa0aa3a37220213859eb9a8e32cc`.
- V3 contract test SHA-256: `068caf9e0d08cdf2b79d7f2ca5d48fca12c07cfd51d98a604e123115eddf6d51`.
- Targeted validation: bootstrap contract `10/10 PASS` in 7.145 seconds; v3 entrypoint contract `10/10 PASS` in 63.739 seconds; affected `py_compile` checks PASS.
- V3 closes only `BOOTSTRAP_CONFIDENCE_INTERVAL_GAP`. DSR, PBO, real-data, formal Frozen blind-test, HIGH_VOLATILITY coverage, dependency/source identity, and Ensemble gaps remain explicit; `NO_FORMAL_INFERENCE_AUTHORITY` is explicit.
- Evidence state remains `GAP`; permission status remains `BLOCK`; profitability, formal inference, blind-test completion, paper, live, and order-entry authority remain false.
- Renderer semantics remain neutral: `SOURCE -> GAP -> MATURITY -> PERMISSION`.
- The single-look chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`; legacy pack-v5 public reading remains UNKNOWN and pointer-v2 is not reissued.
- This is descriptive synthetic evidence only. It is not a real-data result, significance claim, profitability proof, formal Frozen blind test, current-version promotion, or trading authorization.

## 2026-08-31 - Synthetic benchmark report v4 consumer-only evidence (non-current)

- Scope: `deterministic-synthetic-strategy-benchmark-v4` is a pure in-memory composition consumer. It accepts verified v3, trial-return-matrix-v1, deflated-Sharpe-v1, and CSCV/PBO-v1 artifacts; it does not provide a default backtest runner.
- Source accounting: 179 logical source runs are reused (32 baseline plus 147 robustness). v4 composition plans and executes 0 backtest runs, adds 0 backtest runs, performs no runtime mutation, and binds the shared v3/matrix baseline plus the shared DSR/PBO matrix by SHA-256.
- Diagnostic coverage: deflated Sharpe is observed for 6/6 registered strategies. CSCV/PBO is observed for 4/6 and remains GAP for 2/6 because exact rank ties are not arbitrarily resolved; `PARTIAL_CSCV_RANK_TIE_GAP` remains explicit.
- Validation: targeted `py_compile` PASS; `tests.test_synthetic_strategy_benchmark_report_entrypoint_v4` 12/12 OK in 53.978 seconds. The test fixture reconstructs pure synthetic source artifacts; the v4 composition itself executes 0 backtests.
- Plan SHA-256: `341e74840d974575d8bd34545088ef2ec70009ead6484436f20ce76294f081c8`.
- Entrypoint SHA-256: `243c1bfb65d6de1c5e114a24a63e90584a46d7b529be856d605f852fe7eb289c`.
- Contract-test SHA-256: `394c6fe1b836c8c8d0a40b1a7b96f0e4b47b5371f2c1ff853432d4cbea9fbe6d`.
- State: `SOURCE=PURE_SYNTHETIC_IN_MEMORY -> GAP -> MATURITY=SYNTHETIC_BENCHMARK_WITH_PARTIAL_REGIME_BOOTSTRAP_DSR_AND_PBO_DIAGNOSTICS -> PERMISSION=BLOCK`.
- Current-state invariants: v4 remains a non-current candidate. The current single-look chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`; legacy pack-v5 remains `UNKNOWN`; pointer-v2 is unchanged and is not reissued.
- Authority: `blind_test_complete=false`, `formal_inference_authorized=false`, `paper_authorized=false`, `live_authorized=false`, `order_entry_authorized=false`, and `profitability_proven=false`. Synthetic diagnostics do not establish profitability, formal inference, or trading permission.

## 2026-08-31 - Synthetic high-volatility validation and benchmark report v5 (non-current)

- Scope: `synthetic-strategy-high-volatility-validation-v1` adds one preregistered, no-randomness, pure in-memory scenario for the six existing registered strategies and a buy-and-hold benchmark. `deterministic-synthetic-strategy-benchmark-v5` consumes the verified v4 and high-volatility artifacts without changing historical v1-v4 contracts.
- Fixture identity: 220 daily rows, alternating +6%/-6% simple close returns, fixed OHLC envelope and volume cycle. Dataset SHA-256 is `9e3a21a7b909f09046b64dd9bacd1dbf484b0afa3b74269a35da7efff8f456f9`; fixture SHA-256 is `9c4c4ceafe19829b478fb28970e1fdb64ff59426c3b6b71c622cf6ef3fbe8d6e`.
- Coverage: all 6 registered strategies have an `OBSERVED` `HIGH_VOLATILITY` target slice with 189 observations each. The historical `HIGH_VOLATILITY_REGIME_COVERAGE_GAP` is replaced only by `HIGH_VOLATILITY_SYNTHETIC_SCENARIO_ONLY`; this is not real-market or formal blind-test coverage.
- Run accounting: v5 binds 179 inherited logical source runs plus 7 dedicated scenario runs, for 186 logical source runs. v5 composition plans and executes 0 backtest runs, adds 0 backtest runs, and performs no runtime mutation.
- Validation: targeted `py_compile` PASS; `tests.test_synthetic_strategy_high_volatility_benchmark_v5` 14/14 OK in 87.669 seconds. Tests cover exact execute types, deterministic fixture identity, run/manifest bindings, all-six target coverage, resealed projection and binding tampering, authority escalation, v4/v5 strategy order, gap replacement, and neutral rendering.
- High-volatility plan SHA-256: `7b34c83b4cfaa33f06d7bd48fbb6952eff99cdb9ae6da38591f784d82319bda1`.
- Benchmark v5 plan SHA-256: `51e1f847f06e1a3d62f6ddf3be5136fab3d2a50609e5d206138a125d71cdc622`.
- High-volatility module SHA-256: `489436526f101aaa40ec20e8e5be0742674c8f170fa8320627b1a9b0f35b11f6`.
- Benchmark v5 module SHA-256: `c3d91d5499185efe819f0faefb53e5e2bca0d36f6ae023b6398e77d71753d8e9`.
- Contract-test SHA-256: `a14af2178812f67d40d6631cbd048d60ba5c8ba8a62ea804963831b3c77844ad`.
- State: `SOURCE=PURE_SYNTHETIC_IN_MEMORY -> GAP -> MATURITY=SYNTHETIC_BENCHMARK_WITH_REGIME_BOOTSTRAP_DSR_AND_PARTIAL_PBO_DIAGNOSTICS -> PERMISSION=BLOCK`. PBO rank-tie, real-data, formal-blind-test, source-commit, dependency-lock, and formal-inference gaps remain.
- Current-state invariants: v5 remains a non-current candidate. The current single-look chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`; legacy pack-v5 remains `UNKNOWN`; pointer-v2 is unchanged and is not reissued.
- Authority: `blind_test_complete=false`, `formal_inference_authorized=false`, `paper_authorized=false`, `live_authorized=false`, `order_entry_authorized=false`, and `profitability_proven=false`. Synthetic scenario coverage does not establish profitability, formal inference, or trading permission.
### Canonical HTTP contract source

The pure HTTP classification contract is owned by
`src/hakimi_research/http_contract.py`. The historical
`exchange_terminal/services/http_contract.py` path is compatibility-only and
re-exports the canonical objects. This source migration does not reopen
Archived paper execution, paper/live/order authority, or optimization.

### Canonical runtime health projection

The deterministic runtime health and disabled-capability payload builders are
owned by `src/hakimi_research/health_contract.py`. The historical
`exchange_terminal/application/health_contract.py` path is compatibility-only
and re-exports the canonical objects. Transport adapters remain in the
application tree, and this source migration grants no paper/live/order or
optimization authority.
### Archived legacy optimizer

The retired parameter-grid implementation is preserved only at
`archive/legacy_optimizer/optimizer.py`. It is no longer importable from
`quant_bot`, and `BotConfig` explicitly rejects `mode: optimize` and top-level
`optimizer` settings. Current fixed-grid research evidence remains descriptive
and does not reopen parameter-optimization authority.
### Archived legacy live adapter

The retired `CcxtBroker` placeholder is preserved only in the historical
snapshot at `archive/legacy_live_adapter/execution_with_ccxt_stub.py`. The
formal execution module contains no exchange adapter or order implementation,
and formal dependency manifests no longer install `ccxt`. Negative broker/live
fields remain only as fail-closed selectors and Frozen-manifest provenance.
### Archived legacy paper execution engine

The retired continuous `TradingEngine`, former `PaperBroker` snapshot, and their
dedicated tests are preserved under `archive/legacy_paper/`. Formal source now
uses `ResearchExecutionSimulator` only inside BacktestEngine, rejects every
non-backtest execution authority, and exposes no broker builder. This simulator
is deterministic research infrastructure, not paper execution permission.
### Archived Exchange Terminal paper runtime facade

Exchange Terminal now receives static, immutable paper compatibility snapshots
from `src/hakimi_research/archived_paper_runtime.py`. Server import no longer
constructs PaperAccount, PaperLedger, ResearchExecutionRehearsalSimulator, or portfolio paper SQLite
services and no longer reads the legacy paper state file. Every facade write
path fails closed. `/api/order/estimate` is permanently blocked by the archived
execution route wall and its network-backed estimate branch is removed.

The historical paper service modules remain temporarily in the source tree for
separate data-lifecycle archival; they are no longer server runtime consumers.

## ADR0522 legacy Exchange Terminal paper account archive

The retired Exchange Terminal `PaperAccount` and paper strategy clock now live
under `archive/legacy_paper/` as non-importable historical source. Current
server compatibility views continue to use the immutable canonical archived
runtime facade; this change does not authorize paper, live, order, optimization,
or profitability claims. Executor, ledger, portfolio paper persistence, and
execution rehearsal require separate consumer-first archive slices.

## ADR0523 legacy paper persistence archive

The retired SQLite `PaperLedger`, portfolio paper account, and activation logic
now live under `archive/legacy_paper/` as non-importable historical source.
Formal runtime read-only coverage continues for supported research ledgers only.
This does not authorize paper, live, order, optimization, or profitability
claims. The in-memory execution rehearsal remains a separately audited residual
until its research simulator is migrated away from `ResearchExecutionRehearsalSimulator`.
