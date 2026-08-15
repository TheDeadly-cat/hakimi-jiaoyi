# 哈基米交易 v2 模块化状态

更新时间：2026-08-13

## 2026-08-12 当前模块边界收口

- 当前唯一可继续推进的 P2 主线仍是逐步拆分 `server.py`；它约 12k 行，不能一次性重构。已完成的纯投影/固定来源边界包括 `platform_control_center.py`、`portfolio_forward_projection.py`、`research_query_projection.py`、`research_panel_projection.py`、`market_scanner_projection.py`、`portfolio_backtest_pack_pointer.py`、`strategy_research_pointer.py`、`strategy_research_currentness_facts.py`、`strategy_hypothesis_preregistration.py`、`strategy_backtest_projection.py`、`strategy_compare_projection.py`、`strategy_war_room_projection.py`、`strategy_doctor_projection.py`、`strategy_lab_projection.py`、`bot_research_projection.py`、`strategy_analysis_projection.py`、`market_ai_projection.py`、`deepseek_projection.py` 和 `trading_agents_projection.py`。
- `research_panel_projection.py` 只负责 `/api/research/panel` 的最终研究包络；tone、方向/偏好、READY 类状态与 BUY/SELL 类动作保留 raw 元数据或研究观察，嵌套权限失败关闭；扫描、行情、新闻、股票研究 I/O 和路由顺序仍在 `server.py`。
- `market_scanner_projection.py` 只负责 `/api/market/scanner` 的最终研究投影；策略 ID/名称、动作、风险和最高机会摘要改为研究观察并保留 raw 元数据，嵌套权限失败关闭。扫描计算、通知写入开关、行情读取和路由顺序仍在 `server.py`；前端点击只切换标的，不自动套用策略。
- `strategy_war_room_projection.py` 只负责 `/api/strategy/war-room` 最终 JSON 的研究/观察权限包络、状态与执行语义中性化；行情、策略计算、风险参数、调度器和 I/O 仍在 `server.py`。它不生成订单、不重跑回测、不读取 runtime 数据。
- `strategy_doctor_projection.py` 只负责 `/api/strategy/doctor` 与 preview 最终 JSON 的研究/观察权限包络；体检计算、pipeline record、查询和既有回退仍在 `server.py`，`paper_ready` 仅作 raw 元数据保留。
- `strategy_lab_projection.py` 只负责 `/api/strategy/lab` 最终 JSON 的规划-only 包络；开发期仓位/目标区/失效区/启发式分数只在 `planning_candidate` 下可见，旧操作字段置空，递归权限固定为 false。行情和环境计算仍在 `server.py`。
- `strategy_hypothesis_preregistration.py` 是新策略研究在数据读取前的纯归一化/语义验证边界。作者只能填写策略 ID、代次、机制/新颖性和机制特有失效条件；参数拓扑、正压力收益、非 WFO 时间切片、新鲜留出、60/8 自然前向、到期统计复核及权限由 schema 固定，不能在草案中弱化。加载器只允许项目内小型 JSON，并在读取前阻断项目外、`runtime*`、控制目录与敏感文件名。
- `strategy_research_protocol_artifact.py` 负责正式预注册 sidecar 的纯路径计划、artifact binding、严格恢复校验与不可覆盖发布。它拒绝 report 根外、非 JSON、固定 pointer、registry 及 SQLite 伴随文件冲突；发布使用同目录 UUID 临时文件、独占创建、fsync 与 no-clobber，不会删除未知工件。`strategy_matrix_protocol.py` 的 v3 register/claim 和 CLI post-check 分别复核同一 binding；数据库失败后留下的工件不可领取，只有同一未过期协议通过完整恢复验证后才可登记。该边界明确不是文件系统与 SQLite 的跨资源事务。
- `prepared_research_result.py` 是正式 strategy research 与 strategy matrix runner 共用的完成前恢复工件边界：按 protocol Hash 计算不命中 exposure glob 的唯一隐藏 basename，对完整正式报告、protocol/claim/completion/result/dataset/output 绑定和递归零权限做纯验证，并提供精确字节幂等的 no-clobber/fsync 发布。两个 runner 都在 registry complete 前先验证并发布该工件；`RUNNING`/`COMPLETED` 恢复只精确读取一个确定性工件，不 glob、不重领、不重审 exposure、不重读行情。strategy research 保留既有 pointer；matrix 没有 pointer，本轮不新增。claim 后到 prepared 发布前的窗口仍不可恢复，文件系统与 SQLite 仍不是跨资源事务。
- `strategy_cost_stress.py` 是 schema-8 策略研究的纯成本压力合同与证据边界：从冻结 risk 复算 configured/stress/severe 名称、费率和滑点，绑定 selection validation baseline 与 frozen-test configured/severe 收益、回撤、交易数，并把证据完整性与研究结果分别表达。schema-3–7 继续走历史 cell/hash 语义；该模块不运行回测、不选参、不证明盈利，也不授予模拟或实盘权限。
- `strategy_research_pointer.py` 负责研究报告固定指针的发布、文件/报告 Hash 与公共 verifier 绑定，以及 `/api/strategy/research-evidence` 的只读白名单投影。writer 仅可更新 report 根目录内的固定指针；reader 只读该指针和一个 basename 目标，不 glob、不重建报告、不运行 K 线。reader 对 schema-6/7/8 重建当前 implementation closure；schema-7/8 另外复算并白名单输出假设摘要，schema-3–6 固定输出 `LEGACY_NOT_BOUND`，防止历史报告被追认为事前假设。公开结果不透出路径，也不授予选参、盈利或交易权限。
- `strategy_research_currentness_facts.py` 是纯时间事实投影，不读文件、不取系统时钟，也不制定阈值。pointer 把已验证报告时间、两处数据截止日和 server 注入的观察毫秒交给它；模块只复算非负报告年龄与 UTC 日历日差，并在日期来源不一致、未来时间或伪类型时失败关闭。输出固定声明阈值未定义、不是交易日年龄、不可推断新鲜/过期或交易权限。
- `strategy_research_failure_conditions.py` 是纯失效条件投影，不做 I/O、不读取当前时钟、不引入新阈值；只从 pointer 已验证并白名单化的平台、成本、时间切片与两级实现证据复算五条条件。真实阻断/漂移进入 `observed`，数据新鲜度、报告年龄和自然前向仍进入 `evidence_gaps`，所有权限固定关闭。该边界把失效语义从超过千行的 pointer 模块拆出，便于后续版本化而不污染来源读取。
- `backtest_risk_control_surface.py` 是交互回测 100 格风险控制网格的唯一拓扑与纯投影边界；`server.py` 直接使用该模块声明的仓位/止盈/止损轴运行既有开发回测，再把完整候选内存列表交回模块复算覆盖、有限指标、最高分单元和一步邻接连通区域。它不读行情、不运行回测、不碰冻结报告，并固定声明非策略信号参数平台、同数据、选择偏差未校正、不可选参及零交易权限。
- `strategy_compare_projection.py` 只负责 `/api/strategy/compare` 最终 JSON 的研究比较包络；动作、启用/停止条件被改成描述性研究语义，评分/概率显式标记为未校准开发期启发式，递归权限固定为 false。
- `bot_research_projection.py` 只负责机器人中枢、研究角色调度、调度变更结果与机器人档案的最终 JSON 包络；OWNER/可执行/armed/推荐/账户比例会保留 raw 元数据但主字段失败关闭，调度仍只改变既有规划标签，不生成订单。机器人计算、市场读取、profile 持久化与路由顺序仍在 `server.py`。
- `strategy_analysis_projection.py` 只负责 `/api/strategy/analyze` 最终研究 JSON；TP/SL 与方向规划只进入 `planning_*` 和研究枚举，嵌套 risk config 的权限固定关闭，计算与内部调用者继续留在 `server.py`。
- `market_ai_projection.py` 只负责双 AI 行情分析最终研究 JSON；多空方向、概率、支撑压力和价格计划被中性化并保留 raw 元数据，模型调用、行情读取和请求体处理仍在 `server.py`。
- `deepseek_projection.py` 只负责旧 DeepSeek 分析、机会扫描和平台复核 GET 的最终研究 JSON；方向、置信度、机会价位、仓位提示与 actionability 被中性化并保留 raw 元数据，模型调用、行情读取和复核上下文仍在 `server.py`。
- `trading_agents_projection.py` 只负责 `/api/ai/trading-agents/discuss` 最终 JSON 与 NDJSON 事件的研究包络；会议方向、置信度、胜率、通用 action/signal、价位和仓位字段被映射为 `RESEARCH_*`、未校准或 `planning_*`，事件根与嵌套权限均失败关闭，AI 调用与会议编排仍在 `server.py`。
- `portfolio_backtest_pack.py` 的当前 writer 使用 v4，并把同次读取的 UTF-8 research document、completion/registry binding、版本化 result evidence 和重新生成的 quality-v2 一起封存；`backtest_return_quality.py` 保留 quality-v1 历史入口并提供 v2 来源身份/语义投影。v4 verifier 从策略/基准/压力成本权益曲线、样本和统计绑定复算质量；来源 BLOCK 的结构有效工件只保留 null/UNKNOWN 数值，且 pointer 不发布。v2/v3 verifier/hash 不被重解释。该模块固定声明无外部锚定/加密真实性，只保证同一嵌入工件身份下的自洽；portfolio 来源不适用 strategy schema-7，两个研究家族之间没有隐式桥接。
- `portfolio_backtest_pack_pointer.py` 负责 internal backtest 固定来源、收益质量和 v3/v4 自然前向晋级摘要的只读白名单投影。当前 snapshot v3 严格耦合 pack v2/quality-v1/无前向、pack v3/quality-v1/forward-v1、pack v4/quality-v2/forward-v1；错配统一 UNKNOWN。模块不返回完整 source evidence、spec、settlement 行、路径或整包，不 glob、不重建证据、不重载数据库、不独立重放 settlement，也不在请求中重跑 K 线。前向子证据与整体 pack 状态保持两层，任一层都不能授予模拟或实盘权限。
- pack 投影中的 `forward_progress` 也由 pack verifier 做原生非负整数/调度字符串合同校验；该门禁保持在 pack 边界，不把进度字段扩散到 `server.py` 或前端执行语义。
- 当前日常验证以 `run_lean_validation.py --profile frontend/research` 为准；完整回归、真实 HTTP/浏览器运行态、真实冻结 pack 读取和正式盲测仍不是本轮证据。

## 当前原则

### 2026-08-12 异动与走势研究投影

- 新增 `exchange_terminal/services/market_anomaly_projection.py`，只负责 `/api/market/anomaly-radar`、`/api/market/anomaly-detail` 与 `/api/market/trend-cockpit` 的最终只读 JSON 投影。
- 新增 `exchange_terminal/services/market_scanner_projection.py`，只负责 `/api/market/scanner` 的研究-only JSON 投影；保留扫描数值证据但中和策略动作/风险与执行语义，普通刷新不新增状态写入。
- 投影递归中和嵌套执行权限；方向、偏好和 `tone` 在可见研究层固定为“研究观察”/`flat`，原始值仅放在 `raw_*` 审计字段。行情读取、缓存、事件记录和路由调用顺序仍在 `server.py`。
- 新增 `tests/test_market_anomaly_projection.py` 合同；日常只跑纯内存投影、异动质量与前端静态验证，不启动服务、不扫描 runtime、不重跑旧 K 线。
- 新增 `exchange_terminal/services/configuration_projection.py`，只负责 `/api/config/full` 与 `/api/config/full/apply` 的最终研究配置 JSON 白名单投影；配置快照、应用逻辑和 I/O 仍留在 `server.py`。原始 `READY/PASS` 仅保留为审计元数据，详情路径/密钥不出现在研究视图，根与嵌套 paper/live/execution 权限固定为 false；新增纯内存合同 `tests/test_configuration_projection.py`。
- 控制中心前端继续收口为中性研究层：即使上游声称 `paper_authorized=true` 或 `armed=true`，模拟卡片也只显示“模拟未授权”；自然前向、小资金规则、回放与审计行不透传原始 `PASS/READY`，原始状态仅保留在审计元数据。
- 开发期策略比较与回测候选行也采用中性 score/return 表现，候选点击只复制研究参数到表单并明确不运行、不授权；该改动只涉及静态呈现，不改变回测、策略或权限调用链。

- 保持 `http://127.0.0.1:8765/`、现有 API 路径、前端行为不变。
- 先拆纯配置、纯工具、股票元数据工具，再拆行情读取和研究面板。
- 实盘真实下单硬保护墙保持默认开启，不因模块化改变。

## 已拆模块

### `exchange_terminal/config.py`

集中管理：

- 本地目录、runtime 文件、缓存数据库路径。
- OKX / Futu / DeepSeek / OpenAI 环境配置。
- 股票池、股票离线种子价格、成交量。
- 实盘保护墙开关。

### `exchange_terminal/utils.py`

集中管理纯工具函数：

- 时间戳：`now_ms`
- 数值清洗：`pct`、`average`、`clamp`
- JSON 清洗：`clean_json_value`
- 配置解析：`flag`、`choice`
- 展示格式：`human_age_ms`、`market_source_name`
- 行情计算：`safe_volume_ratio`、`recent_volatility`、`trend_score`

### `exchange_terminal/market_data/stocks.py`

集中管理股票元数据工具：

- 股票识别：`is_stock_symbol`
- 股票元信息：`stock_meta`
- Futu / Yahoo / Stooq 代码映射
- 股票时区、盘前盘中盘后判断
- 股票周期归一化

### `exchange_terminal/market_data/stock_candles.py`

集中管理股票 K线规则层：

- K线按盘前 / 盘中 / 盘后 / 夜盘过滤。
- 分钟 K线聚合为 4H 等周期。
- 股票 K线缓存 key、新鲜度、旧缓存判断。
- 股票交易日和当前交易时段判断。
- SQLite K线行归一化。
- K线 payload 的 `latest_at`、`data_age_ms`、`realtime` 标记补全。

### `exchange_terminal/market_data/stock_candles_io.py`

集中管理股票 K线 IO 层：

- SQLite 股票 K线库建表、读取、写入。
- Yahoo / Stooq 外部 K线源读取。
- 外部源失败短缓存，避免切换标的时反复等待超时。
- 日K缺少当前交易日时，用分钟K生成临时日K观察行。
- 本地旧缓存、外部源、临时日K的来源标记保持前端可见。

### `exchange_terminal/market_data/futu.py`

集中管理 Futu 基础层：

- Futu OpenD 端口状态、SDK 导入和状态缓存。
- Futu 股票池状态摘要和 `/api/futu/universe` 数据。
- Futu K线周期映射、历史窗口计算、时间字段解析。
- Futu 行情快照归一化为本项目统一股票报价结构。
- 主服务保留账号 XML 写入、验证码提交等少量接口，后续再继续拆。

### `exchange_terminal/market_data/futu_quotes.py`

集中管理 Futu 报价 / K线 IO：

- Futu 批量行情快照读取。
- Futu 历史 K线读取和分页窗口参数。
- Futu 最新报价补最后一根临时K线。
- Futu K线盘前 / 盘中 / 盘后 / 夜盘过滤。
- 主服务只保留两个薄包装：写入单标的报价缓存、传入当前报价回调。

### `exchange_terminal/market_data/futu_deep.py`

集中管理 Futu 深度行情层：

- Futu 盘口、逐笔、实时分时、经纪队列读取。
- 资金流、资金分布、估值、机构持仓、评级、技术 / 财务异动、卖空数据。
- 深度行情缓存和 OpenD 离线降级。
- 本地股票 AI 摘要、盘口 / 异动 / 资金证据整理。

### `exchange_terminal/market_data/okx.py`

集中管理 OKX 公共行情读取层：

- OKX 公共 REST GET 读取。
- 公共行情 rows / first 包装。
- 带错误文本的 rows 读取包装。
- 仅覆盖公共行情，不接触私有账户、签名读取、实盘下单和风控边界。

### `exchange_terminal/services/paper_executor.py`

集中管理模拟盘撮合估算层：

- 统一订单类型集合：`MARKET`、`CURRENT`、`LIMIT`、`POST_ONLY`、`IOC`、`FOK`、`OCO`。
- 盘口深度撮合、均价、部分成交、FOK 全成全撤、IOC 部成撤销、限价等待。
- 手续费、滑点、资金费率估算和失败降级提示。
- 只做模拟盘估算，不持有账户状态，不接触真实下单。

### `exchange_terminal/services/risk_service.py`

集中管理影子风控和执行前检查：

- 保留实盘硬保护墙：`LIVE` 模式永远拒绝。
- 统一输出 `allowed`、`status`、`reason`、`reject_reason`、`checks`，便于前端展示拒绝原因。
- 区分开仓与减仓：风险状态下阻断新增风险，但允许减仓/平仓继续通过。
- 检查标的、方向、执行模式、名义金额、单笔上限、只做多/只做空、只减仓。

### `exchange_terminal/services/paper_account.py`

集中管理模拟账户状态机：

- `PaperAccount` 从 `server.py` 迁出，主服务只负责初始化和注入运行时回调。
- 保留现金、持仓、均价、浮盈亏、条件单、信号、权益曲线和模拟订单记录。
- 所有实际模拟撮合前仍调用统一风控预检，避免策略单、条件单绕过风险层。
- 通过 `configure_paper_account_runtime` 注入账本、策略分析、状态文件写入和风控预检，避免反向 import `server.py`。

### `exchange_terminal/services/guardian_service.py`

集中管理后台守护和熔断：

- `GuardianService` 从 `server.py` 接管守护线程、心跳、后台策略评估和停止事件。
- 统一处理风险预检阻断、最大回撤熔断、强平距离保护、保证金不足保护。
- 守护线程仍只调用模拟账户和影子风控，不触达实盘下单路径。
- 主服务保留 `run_guardian_cycle`、`guardian_emergency_stop` 等兼容包装，现有 API 路径不变。

### `exchange_terminal/services/event_bus.py`

集中管理内存事件流：

- 行情、信号、风控、订单、AI 审查后续统一发布成事件。
- 当前提供最近事件查询和订阅入口，后续可升级 WebSocket / SSE。
- 新增 `/api/events` 只读接口，供前端展示事件流和证据链。

### `exchange_terminal/services/audit_log.py`

集中管理审计日志：

- 当前兼容原 `exchange_terminal_ledger.jsonl`，不破坏旧账本。
- `append_ledger` 统一委托给 `AuditLog`，并同步发布到 `EventBus`。
- 后续可从 JSONL 平滑升级到 SQLite 审计库。

### `exchange_terminal/services/market_data_service.py`

集中管理标准化行情快照：

- 新增 `/api/market/snapshot`，统一返回标的、报价、K线、来源、新鲜度、实时/缓存状态和降级原因。
- 股票快照复用 `read_stock_quote`、`market_chart_candles`、`stock_data_sources_snapshot`。
- 加密快照复用 OKX 公共 ticker 和统一 K线接口。
- 股票快照支持 `session` 参数，保留盘前 / 盘中 / 盘后 / 夜盘过滤能力。
- 内置短 TTL 缓存，减少同一标的在前端、AI、策略、回测之间重复拉取。
- 支持 `emit=true` 时把快照写入 `EventBus`，默认不刷屏事件流。

### `exchange_terminal/research/stock_research.py`

集中管理当前生效的股票研究 fast 面板：

- 股票本地新闻摘要、RSS/Yahoo 异步新闻补全。
- 盘前 / 盘中 / 盘后 / 夜盘分时样本摘要。
- 异常成交：量比、跳空、日内振幅、价格异动。
- 行业联动：同组股票涨跌、成交量、分化观察。
- 股票研究面板、股票异步新闻/财报事件补全。
- 主服务保留报价缓存读取和兼容包装，避免研究层反向持有 server 状态。

## 本轮补充修正

- 股票列表、单标的报价、股票K线在 Futu OpenD 离线时统一标记为“本地K线库”。
- 保留原始来源 `origin_source=futu`，但不再把旧缓存误显示为 Futu 实时。
- 前端股票列表、顶部标的描述、K线质量条统一显示“本地K线库(Futu OpenD)”和旧缓存提示。
- 当前本机 Yahoo 股票分钟K请求仍可能 SSL 超时；Futu OpenD 离线时只能显示本地 SQLite 旧缓存，页面会明确提示非实时行情。
- 股票研究 fast 面板已从主服务拆到 `research/stock_research.py`；主服务仍保留早期被覆盖的历史研究函数，后续单独清理死代码。
- 模拟撮合从 `server.py` 拆出到 `services/paper_executor.py`，`PaperAccount` 仅保留账户状态和策略调度。
- 手动单、条件单、策略守护、真实撮合前函数都接入 `build_pretrade_check`，接口返回 `risk_check`。
- 新增只读 `/api/risk/pretrade`，用于前端/调试预演风控，不改变模拟账户状态。
- OKX 公共行情模块补充相对导入 fallback，拆出服务可用包路径独立测试。
- 模拟账户状态机已迁移到 `services/paper_account.py`，`server.py` 不再持有账户类实现。
- 后台守护线程已迁移到 `services/guardian_service.py`，`server.py` 只保留兼容入口。
- 审计日志和事件流已迁移到 `services/audit_log.py`、`services/event_bus.py`，新增 `/api/events`。
- 标准化行情快照已落地到 `services/market_data_service.py`，新增 `/api/market/snapshot`。
- 前端 K线主加载和后台强制刷新已切到 `/api/market/snapshot`，股票和加密货币共用同一套来源、新鲜度、缓存和降级状态显示。
- 图表策略状态层已从 K线画布浮层改为底部状态栏，修复遮挡蜡烛图和 canvas 高度溢出问题。

## 历史拆分清单（非当前待办，需以源码和上方边界复核）

下一步优先拆：

- `research/anomaly.py`：异动雷达和异动详情。
- `research/trend.py`：趋势驾驶舱。
- `market_data/adapters/`：继续把 OKX / Futu / Yahoo / Stooq / CSV 拆成插件化 adapter。
- `http_api.py`：路由分发和 JSON 响应。

## 本轮验证

- `python -m py_compile` 已覆盖新模块和 `server.py`。
- `node --check static/app.js` 通过。
- `npm.cmd run check` 通过。
- 本地后端真实启动通过。
- `/api/market/snapshot` 对 BTC-USDT、AAPL 烟测通过。
- 本地浏览器验证通过：AAPL -> BTC-USDT -> AAPL 切换后 K线画布保持可见，控制台无相关错误。
- 本地浏览器验证通过：策略状态栏位于 K线下方 footer，AAPL / BTC-USDT 切换后不再与 canvas 重叠。
