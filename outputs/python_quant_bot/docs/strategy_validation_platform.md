# 哈基米交易 v2：策略验证与模拟交易平台

更新日期：2026-08-01

## 产品边界

哈基米交易负责把研究结论转化为可验证、可回放、可审计的模拟交易实验，不负责生成最终投资决策，也不开放实盘下单。

- 交易分析项目：发现异动、解释走势、组织 AI 讨论、形成证据与反证。
- 哈基米交易：策略定义、回测、体检、模拟授权、模拟成交、风险控制和审计复盘。
- 两个项目之间只传递结构化 `ResearchBrief`。研究摘要不是订单，也不能包含执行字段。
- 所有真实下单入口继续由硬保护墙阻断。

## 第一屏

默认视图为“交易总控”，汇总六类状态：

1. 策略流水线：当前策略、标的、运行 ID、阶段和阻断原因。
2. 模拟账户：权益、持仓方向、运行状态和模拟订单。
3. 统一风控：所有人工单、策略单和条件单的预交易检查。
4. 行情服务：统一行情快照、缓存复用和上游请求状态；服务在线不等于当前标的满足开仓质量。
5. 账本与回放：SQLite 账户版本、待结算成交、重启恢复、幂等写入和最近订单事件链。
6. 审计与保护墙：SQLite 事件数量、订单生命周期和实盘锁定状态。

行情、策略工作台、历史研究模块和系统设置保留为次级工作区，不再抢占默认首屏。

## 策略发布流水线

固定阶段：

`策略定义 -> 可复现回测 -> 策略体检 -> 模拟授权 -> 模拟运行 -> 审计复盘`

规则：

- 回测必须提供数据指纹、参数哈希、运行哈希和接受度门禁。
- 每次定义会冻结策略参数和实现指纹，形成不可变 `strategy_version_id`。
- 历史运行缺少版本或时间验证时只显示 `LEGACY_BLOCKED`，不能继承旧授权状态。
- 验证必须使用按时间切分的数据集、滚动前向窗口和手续费/滑点压力场景。
- 策略体检必须检查未来函数、样本量、参数数量和执行适配。
- 回测或体检任一阶段未通过，模拟授权必须阻断。
- 前向模拟默认至少 7 天、20 笔闭合交易且最大回撤不超过 12%，之后仍需人工审计批准。
- 模拟账户停止或重置时，流水线必须同步退出运行状态。
- 流水线没有实盘发布阶段；`live_order_allowed` 永远为 `false`。

## 当前可验证执行档

前向模拟授权不仅检查回测是否通过，还会把启动请求与回测工件重新绑定。当前固定契约为：

- `direction_mode=LONG_ONLY`
- `risk_source=MANUAL`
- `risk_value_mode=PCT`
- `leverage=1`
- `order_type=CURRENT`
- `margin_mode=CROSS`
- `trailing_take_enabled=false`
- `trailing_stop_enabled=false`
- `reduce_only=false`

仓位、止盈、止损、杠杆和方向必须与回测工件中的参数完全相同。修改参数后必须重新回测和体检，不能沿用旧授权。做空、杠杆、跟踪退出和限价策略会在各自成交、保证金和风险模型完成后单独建立验证档，不能借用当前做多现金模型。

## 核心服务

- `services/risk_service.py`：统一 `RiskService` 预交易入口，请求编号、检查结果和审计事件在这里生成。
- `services/paper_executor.py`：`PaperExecutor` 模拟订单状态机，记录创建、风控、接受、挂单、部分成交、成交、取消和拒绝。
- `services/paper_ledger.py`：事务型 SQLite 模拟账户、订单、成交和重启对账。
- `services/strategy_pipeline.py`：持久化策略运行和发布门禁。
- `services/strategy_validation.py`：时间切分、滚动前向和成本敏感性验证。
- `services/audit_log.py`：SQLite 主审计库；首次启动时迁移旧 JSONL，之后不再继续分散写 JSONL。
- `services/event_lineage.py` / `services/event_replay.py`：信号身份、全链路证据和确定性回放。
- `services/mutation_journal.py` / `services/http_contract.py`：本地写接口白名单和持久化幂等响应。
- `services/research_bridge.py`：交易分析项目的只读数据与 ResearchBrief 导入边界。
- `services/market_data_service.py`：前端、策略、回测和研究共用的标准化行情快照。

## 接口

### 交易总控

- `GET /api/platform/control-center`
- `GET /api/strategy/pipeline`
- `GET /api/strategy/backtest/artifact?runId=...`
- `POST /api/strategy/pipeline`
- `GET /api/paper/orders/lifecycle`
- `GET /api/paper/ledger`
- `GET /api/replay/order?orderId=...`
- `GET /api/replay/run?runId=...`
- `GET /api/audit/events`
- `GET /api/audit/summary`

### 交易分析桥接

- `GET /api/integration/trading-analysis/context?symbol=AAPL&bar=1Dutc`
- `GET /api/integration/trading-analysis/research-summaries?symbol=AAPL`
- `POST /api/integration/trading-analysis/research-summaries`

状态写接口只接受本机 POST。受保护请求必须同时携带 `X-Hakimi-Write: 1` 和 `Idempotency-Key`；策略流水线的 GET 快照保持只读。

ResearchBrief 最少包含：

```json
{
  "research_only": true,
  "symbol": "AAPL",
  "timeframe": "1D",
  "thesis": "研究结论",
  "evidence": ["证据"],
  "counter_evidence": ["反证"]
}
```

禁止字段包括 `action`、`side`、`order`、`order_type`、`quantity`、`quantity_pct`、`leverage`、`execute`、账户和密钥字段。服务端发现这些字段会返回 `400`，不会触发任何模拟或真实订单。

## 安全原则

- 不在代码、前端、审计或 ResearchBrief 中保存真实密钥。
- AI、研究摘要和外部项目不能绕过 `RiskService`。
- 模拟成交也必须先经过统一风控。
- 开仓必须使用权威实时行情；旧缓存、降级源、隔离数据或明显价格偏差只能用于观察和减仓。
- 每笔模拟成交必须能够回放信号、风控、行情快照、订单迁移和成交金额。
- 每次回测必须冻结全量 OHLCV 哈希、精确参数、策略代码指纹和因果执行模型；信号在收盘生成，最早只能在下一根开盘成交。
- 同一根 K 线同时触发止盈和止损时采用保守的止损优先假设，并在工件中记录歧义次数。
- 风控阻断时允许减仓和平仓语义优先，但不允许新增风险。
- 所有胜率、评分和回测结果只是样本估计，不是保证性结论。
