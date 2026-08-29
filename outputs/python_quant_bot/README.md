# Hakimi Jiaoyi Research Platform

Hakimi Jiaoyi 是本地、离线优先、research-only 的量化策略研究与风险评估平台。
它用于验证数据、运行历史回测、审阅研究证据和导出报告，不代表策略盈利，
也不提供模拟盘、实盘、订单输入或自动参数选择权限。

## 产品能力真相源

运行时权威边界仍由 `exchange_terminal.domain.contracts` 中的
`capability-v1` 提供；同一模块中的 `product-capability-catalog-v1` 负责
Supported / Experimental / Disabled / Archived 产品状态。CLI 和旧图形控制台
直接消费该目录，README 一致性由定向合同测试锁定。

| 能力 | 状态 |
| --- | --- |
| `product_capability_catalog` | Supported |
| `market_data_research` | Supported |
| `historical_backtest` | Supported |
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

## 软件化路线

当前形态是“本地研究平台 + 历史回测与证据审阅界面”。下一阶段优先建设
可复现实验清单、数据质量合同、明确基准、Train / Validation / Frozen Test、
walk-forward、purge / embargo、成本压力测试和参数稳定性分析。在这些证据闭合前，
不增加更多交易策略，不开放 paper/live，也不扩张订单型 UI。

`frozen-evaluation-protocol-v1` 与 `frozen-evaluation-report-v1` 已作为 dormant
纯库候选落地：固定 Train/Purge/Validation/Embargo/Frozen Test、三档成本和两个
基准，但明确 BLOCK 于盲测、外部预登记、单次消费和自然前向证明。它尚未进入 CLI，
也不能被描述为正式盲测、盈利证明或 current 晋级证据。

`frozen-evaluation-markdown-v1` 在验证上述 JSON 后提供确定性、无文件写入的
SOURCE -> GAP -> MATURITY -> PERMISSION 可读投影。它展示固定成本和 benchmark
观测，同时明确标出尚未绑定到 ADR0509 的 walk-forward、参数稳定性、multiple-
testing lineage、市场状态切片和尾部分布指标；它不是新的晋级门或执行入口。

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
├─ src\hakimi_research
│  ├─ __main__.py            # python -m hakimi_research
│  ├─ cli.py                 # only CLI implementation
│  └─ product_capabilities.py
└─ outputs\python_quant_bot
   ├─ run_bot.py             # compatibility export only
   ├─ config.example.json
   ├─ requirements.research.lock
   └─ quant_bot              # pending consumer-first migration
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

大部分历史源码当前仍位于 `outputs/python_quant_bot`。首个完整生产边界
`product-capability-catalog-v1` 已迁到根 `src/hakimi_research`；CLI 与 dashboard
直接消费 canonical 模块，旧 domain 路径只保留对象身份一致的兼容出口。其余源码
迁移和历史原型归档仍需逐消费者完成，不能把这一窄迁移描述成全项目搬迁。

根级 `.github/workflows/research-contracts.yml` 提供最小研究合同 CI：只安装
`requirements.research.lock`、检查确定性输入身份并运行显式合同模块，同时覆盖
根 `src/**` canonical source。它不引用
密钥、不启动产品入口，也不授予 paper/live/order 权限。只有远端实际运行才能
证明 CI 状态；本地存在或语法检查不能称为 CI green。

## Reproducible research identity

The active historical-backtest CLI uses `requirements.research.lock`, an exact
five-package runtime closure. `quant_bot.experiment_manifest` hashes this scoped
lock before the broad optional dependency inventory.

`examples/deterministic_experiment` is a synthetic, local-only identity fixture.
Its verifier checks source-controlled input hashes and permanent authority locks
without network access, cache use, services, or a strategy backtest. A pass is
not strategy evidence, a performance claim, ranking permission, or trading
authority.
