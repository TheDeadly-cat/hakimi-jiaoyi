# 哈基米交易 v2 竞品优点重设计方案

更新日期：2026-07-09

## 结论

这次对标不建议继续堆按钮。哈基米交易 v2 已经有行情、K线、盘口、策略、模拟订单、研究、DeepSeek、Futu/OKX 和系统控制面，短板是“功能很多但边界不够硬、流程不够可审计、测试和安全准入没有成为用户默认路径”。

下一轮应该把产品重心改成四条主线：

1. 专业行情工作台：参考 TradingView，把多图同步、命令搜索、回放、告警、图上策略解释做成默认工作流。
2. 研究到模拟的一致路径：参考 NautilusTrader 和 QuantConnect LEAN，让同一套策略语义贯穿研究、回测、模拟盘和未来实盘，不允许页面逻辑各自解释交易状态。
3. Dry-run 与风控优先：参考 Freqtrade，把模拟盘、回测、偏差检测、WebUI 控制、停止买入/停止策略变成显性控制面。
4. 数据层解耦：参考 OpenBB，把 OKX、Futu、本地 SQLite、CSV、AI 摘要整理成“接一次、多端消费”的数据服务，而不是让 `server.py` 和 `app.js` 继续承载全部状态。

## 选取范围

### Direct：直接竞品 / 强相关开源项目

| 项目 | 类型 | 为什么值得学 | 来源 |
|---|---|---|---|
| NautilusTrader | 生产级多资产交易引擎 | 事件驱动、回测/实盘同语义、风险引擎前置、缓存与消息总线清晰 | https://github.com/nautechsystems/nautilus_trader |
| Freqtrade | 开源加密交易机器人 | Dry-run、WebUI/API 控制、回测/Hyperopt、偏差检测、默认本地 API 安全边界 | https://github.com/freqtrade/freqtrade |
| QuantConnect LEAN | 开源算法交易引擎 | 模块化引擎、CLI 工作流、研究/回测/优化/实盘命令链、测试要求 | https://github.com/QuantConnect/Lean |
| Hummingbot | 开源高频/做市机器人框架 | 多交易所连接器、CEX/DEX 适配、Gateway 生产模式、策略脚本生态 | https://github.com/hummingbot/hummingbot |

### Adjacent：相邻产品 / 工具层

| 项目 | 类型 | 为什么值得学 | 来源 |
|---|---|---|---|
| TradingView | 专业图表和交易分析产品 | 多图同步、命令搜索、Pine、策略测试、告警、直接图上交易 | https://www.tradingview.com/features/ |
| TradingView Lightweight Charts | 开源金融图表库 | 高性能 Canvas、插件扩展、轻量可嵌入，适合替换/增强当前 Canvas K线 | https://github.com/tradingview/lightweight-charts |
| OpenBB | 开源金融数据平台 | connect once, consume everywhere；数据源、Python、Workspace、REST、AI Agent 的统一数据底座 | https://github.com/OpenBB-finance/OpenBB |

### Watch：AI / vibe coding 风险参考

| 资料 | 借鉴点 | 来源 |
|---|---|---|
| Vibe Coding in Practice | AI 快速生成容易带来 QA 缺口，项目必须把自测、审查、可维护性做成流程 | https://arxiv.org/abs/2510.00328 |
| Is Vibe Coding Safe? | Agent 生成代码在安全敏感场景不能直接进生产，尤其不能接触密钥和交易执行 | https://arxiv.org/abs/2512.03262 |
| Vibe Code Bench | 端到端网页开发仍需浏览器工作流验证，自测行为和成功率高度相关 | https://arxiv.org/abs/2603.04601 |

## 值得吸收的优点

### 1. 架构优点

NautilusTrader 把核心系统拆成 DataEngine、ExecutionEngine、RiskEngine、Cache、MessageBus，并强调数据进入后先进入缓存，再发布给策略；订单路径则是策略发指令、RiskEngine 先验证、ExecutionEngine 再路由。这个模式应该成为我们 v2 的主架构。

落到本项目：

- 新增 `market_data_service.py`：统一 OKX/Futu/SQLite/CSV，所有行情返回 `source`、`origin_source`、`freshness_ms`、`cached`、`realtime`、`warning`。
- 新增 `paper_executor.py`：把 `PAPER_ACCOUNT` 的订单生命周期、成交模拟、手续费、资金费率、IOC/FOK/Post Only 撮合从 `server.py` 拆出。
- 扩展 `risk_service.py`：所有人工单、策略单、条件单、守护进程都必须走 `build_pretrade_check`，并返回可展示的拒单原因。
- 新增 `event_bus.py`：先从本地进程内队列开始，事件类型统一为 `MarketDataUpdated`、`SignalGenerated`、`PretradeChecked`、`PaperOrderSubmitted`、`OrderRejected`、`GuardianStopped`、`AiReviewCreated`。
- 新增 `audit_log.py`：把当前 JSONL ledger 升级为统一事件审计接口，后续再换 SQLite。

### 2. 交互优点

TradingView 的强项不是按钮多，而是“找得到、同步、图上解释、随时回放”。Freqtrade 的强项是控制面清晰：start、stop、stopbuy、locks、profit、status、backtest、lookahead analysis 都能通过 WebUI/API 触达。

落到本项目：

- 命令面板升级为真正的全局工作流入口：搜索标的、切换模块、运行回测、停止买入、刷新数据可靠性、打开风险解释、启动图表回放。
- K线面板加入“图上策略路径”：当前策略的入场条件、反证条件、止盈止损、预估风控拒绝点直接画在图上。
- 多图布局做成两种：`单标的多周期` 和 `多标的同周期`。默认只开一屏，不再让全部模块同时挤在首屏。
- 研究页采用“异动 -> 证据链 -> AI解释 -> 模拟验证”的线性流程，避免用户从新闻、雷达、AI、策略之间来回跳。
- 系统页增加“准入清单”：数据新鲜度、Futu/OKX 连接、模拟盘、风险引擎、AI 状态、最近测试结果、实盘墙状态。

### 3. 测试优点

Freqtrade 的 backtesting、hyperopt、lookahead-analysis 对我们很有价值。尤其 lookahead bias 检查可以防止策略偷看未来 K 线。TradingView 和 Vibe Code Bench 都说明，复杂前端必须做浏览器级工作流测试。

落到本项目：

- `strategy_doctor` 增加 `lookahead_check`：检查策略指标是否使用未来数据、全局聚合、错误 shift、非滚动窗口。
- `strategy_backtest_report` 增加“可复现性”字段：数据源、区间、手续费、滑点、随机种子、策略参数 hash。
- 新增前端 smoke test：启动本地服务，验证行情页、策略页、研究页、系统页、命令面板、手动模拟单、风险拒单、回测按钮。
- 所有 AI 生成的代码草稿必须输出测试建议，不能只输出 patch。

### 4. 安全优点

Freqtrade 文档明确建议 API 默认只监听 localhost，不暴露到公网，并使用强密码/JWT；Hummingbot Gateway 对开发/生产模式做了区分，生产需要 HTTPS 证书；TradingView 交易接入强调经纪商凭据不应存到平台服务器。我们的方向应该更保守：本地软件可以读公开行情和模拟交易，但真密钥、真下单必须继续隔离。

落到本项目：

- 保持 `LIVE_TRADING_HARD_BLOCK = true` 的产品态，不为竞品对标而打开真实下单。
- API 配置面板只保存环境变量名，不保存明文密钥。
- 增加 `execution_readiness`：真实交易未来要同时满足只读 API 检查、二次确认、风险引擎、急停、审计日志、最小权限 key、模拟盘连续稳定记录。
- DeepSeek Code Worker 保持草稿模式：不能接触密钥、不能改实盘墙、不能新增真实下单路径。
- UI 上所有 AI 结论统一标注：`观察 / 仅研究 / 仅模拟盘验证`，不能写成收益承诺。

## 重设计后的信息架构

### 首屏：交易工作台

目标：30 秒内看清“标的、价格、趋势、盘口、策略状态、风险状态”。

布局：

- 左侧：市场列表 + 自选 + 数据源状态。
- 中间：K线 / 分时，顶部是周期、指标、回放、AI图析、告警、图上策略。
- 右侧：盘口、逐笔、微观盘面、策略锚点。
- 底部：当前策略卡、模拟持仓、风险摘要，只展示最关键的 6-8 个指标。

### 第二屏：策略实验室

目标：把“选策略 -> 配参数 -> 回测 -> 偏差检查 -> 模拟运行”串成一个流程。

模块：

- 策略模板库：双均线、网格、BOLL、RSI、动量、马丁、反马丁、利弗莫尔、海龟、达瓦斯。
- 参数面板：仓位、杠杆、方向、委托类型、止盈止损、只减仓。
- 回测面板：收益、回撤、胜率、夏普、交易数、手续费、滑点、数据区间。
- 策略体检：lookahead、过拟合、样本不足、手续费敏感、极端行情。
- 模拟发布：只有体检通过后才允许“启动模拟策略”。

### 第三屏：研究驾驶舱

目标：发现异动并形成证据链。

模块：

- 异动雷达：放量、急涨急跌、突破/跌破、资金费率、OI、股票/币种联动。
- 证据链：K线、盘口、资金流、新闻、财报、行业联动、历史相似片段。
- 双 AI：DeepSeek 初评，GPT/本地规则复核，输出反证和等待条件。
- 模拟验证入口：一键把研究结论带入策略实验室，但不直接下单。

### 第四屏：系统与安全中心

目标：让用户知道系统是否可信、是否能运行、为什么不能实盘。

模块：

- 数据可靠性：OKX、Futu、本地缓存、延迟、新鲜度。
- 风控引擎：硬锁、急停、最大仓位、最大回撤、单笔风险、只减仓。
- 执行准入：模拟盘稳定性、审计日志、API 权限、二次确认。
- AI 开发助手：草稿队列、风险等级、涉及文件、测试建议。

## 工程落地清单

### P0：不改变行为的设计落地

- 新增本文件，作为竞品对标后的产品和工程准则。
- 在 `v2_plan.md` 增加链接，后续拆模块按本文件排序。
- 为现有 `/api/platform/v2` 增加 `competitive_redesign` 摘要字段，前端系统页可展示“当前路线：事件驱动、风控前置、研究到模拟一致”。

### P1：后端拆分

- 从 `server.py` 拆出 `paper_executor.py`。
- 从 `server.py` 拆出 `strategy_registry.py` 和 `strategy_backtest_service.py`。
- 新增 `audit_log.py` 包装当前 ledger。
- 扩展 `risk_service.py`，让 `/api/paper/arm`、`/api/paper/manual-order`、`/api/paper/condition/add`、守护进程全部走同一套 pretrade 结果结构。

### P2：前端流程重排

- `app.js` 拆成 `state.js`、`api.js`、`chart.js`、`commands.js`、`strategy.js`、`research.js`、`system.js`。
- 命令面板接入所有核心动作，不只是跳转。
- K线面板把“回放、告警、策略锚点、AI图析”收成明确工具组。
- 首屏默认只显示交易相关模块，研究和系统进入专门视图。

### P3：测试和准入

- 新增 `outputs/python_quant_bot/tests/`，至少覆盖风控、模拟成交、策略信号、lookahead 检查。
- Electron smoke test 增加真实页面操作，不只做启动检查。
- 每次涉及策略或执行逻辑，必须跑：

```powershell
python -m py_compile outputs/python_quant_bot/exchange_terminal/server.py
node --check outputs/python_quant_bot/exchange_terminal/static/app.js
npm.cmd run check
```

### P4：安全升级

- 保持实盘硬锁。
- 增加执行准入评分，不到 100 不显示任何真实下单入口。
- API key 只允许环境变量名映射，明文禁止落盘。
- DeepSeek 输出只能进草稿队列，必须由 Codex/人工审查后应用。

## 验收标准

- 用户打开首页，只看到“交易关键内容”，不会被全部系统模块淹没。
- 任意模拟下单都能在 UI 看到：触发原因、风控检查、成交模型、手续费、止盈止损、审计事件。
- 任意策略都能回答：适用行情、反证条件、回测区间、是否有未来函数风险。
- 任意行情数据都能看到：来源、是否实时、缓存年龄、失败降级原因。
- 任意 AI 结论都带证据、反证、等待条件和安全边界。
- 系统页能清楚说明：为什么当前不能实盘，以及还缺哪些准入条件。

## 参考来源

- NautilusTrader GitHub: https://github.com/nautechsystems/nautilus_trader
- NautilusTrader Architecture: https://nautilustrader.io/docs/latest/concepts/architecture/
- NautilusTrader Backtesting: https://nautilustrader.io/docs/latest/concepts/backtesting/
- NautilusTrader Live Trading: https://nautilustrader.io/docs/latest/concepts/live/
- Freqtrade GitHub: https://github.com/freqtrade/freqtrade
- Freqtrade REST API / Security: https://www.freqtrade.io/en/stable/rest-api/
- Freqtrade Backtesting: https://www.freqtrade.io/en/stable/backtesting/
- Freqtrade Lookahead Analysis: https://www.freqtrade.io/en/stable/lookahead-analysis/
- QuantConnect LEAN GitHub: https://github.com/QuantConnect/Lean
- Hummingbot GitHub: https://github.com/hummingbot/hummingbot
- OpenBB GitHub: https://github.com/OpenBB-finance/OpenBB
- TradingView Features: https://www.tradingview.com/features/
- TradingView Lightweight Charts: https://github.com/tradingview/lightweight-charts
- Vibe Coding in Practice: https://arxiv.org/abs/2510.00328
- Is Vibe Coding Safe?: https://arxiv.org/abs/2512.03262
- Vibe Code Bench: https://arxiv.org/abs/2603.04601
