# G50 嵌套策略研究治理

> Saved-project note (2026-08-10): retained for historical governance review.
> It does not authorize another G50 run. Historical runtime, report, registry,
> port, and process references were not migrated into the current baseline.

状态：IMPLEMENTED_AND_TESTED
日期：2026-08-04

## 两种运行模式

### 开发模式

`run_internal_strategy_research.py` 默认只能运行训练和验证阶段：

- `selection_test_policy=DEVELOPMENT_ONLY`
- 不生成正式冻结候选
- 不评估测试段
- 不加载留出标的
- 不生成模拟盘或实盘授权

显式传入 `--selection-test-policy BLIND_ONCE` 但没有登记时，程序会在行情读取前退出。

### 正式单次模式

正式测试与留出确认必须分两步：

1. 使用 `run_preregister_strategy_research.py` 固定标的、参数变体、风控、成本、数据策略、代码指纹和未触碰审计。
2. 使用登记返回的 `registration_id` 与 SQLite registry 运行 `run_internal_strategy_research.py`。

正式运行只从协议读取研究参数，命令行不能覆盖。登记只能领取一次，完整状态顺序为：

`REGISTERED -> CLAIMED -> COMPLETED`

留出标的仅在冻结候选通过单次测试后加载。开发模式永远不能进入留出阶段。

## 证据验证

正式报告包含：

- 固定 batch spec 与哈希
- 完整数据清单和数据快照
- 选择、测试、留出各阶段 run hash
- 协议、claim 与 completion 回执
- 代码实现指纹与未触碰审计
- `research_only=true`
- `paper_authorized=false`
- `live_order_allowed=false`

使用以下命令独立校验：

```powershell
python verify_strategy_research_report.py <report.json>
```

开发报告只能用于检查结构完整性：

```powershell
python verify_strategy_research_report.py <report.json> --allow-development
```

## G50 决策

`trend_pullback` 固定假设已在开发诊断中失败，因此不创建正式 G50 协议，也不读取 ON、MCHP。负面证据保存在：

`runtime_g50/reports/g50_trend_pullback_development_falsification.json`

下一项正式研究必须是机制层面明显不同的新假设，不能只调整本策略窗口或阈值。
