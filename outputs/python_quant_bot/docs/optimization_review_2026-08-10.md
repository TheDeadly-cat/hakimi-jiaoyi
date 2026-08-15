# 哈基米交易 v2 优化研究与功能路线

日期：2026-08-10  
适用根目录：`C:\Users\Administrator\Documents\哈基米v2交易`

## 结论先行

正式策略研究已激活 schema 14 的全局注册搜索谱系；development writer 继续保持 schema 13。schema 14 的正式选择必须在 canonical registry 中完成 live audit/claim 绑定，并以全局累计 trial 数而非本批大小执行多重搜索惩罚；公共投影精确使用 v7，固定 pointer artifact/expectation/receipt 仍保持 v1 字段合同。

### 当前自然前向证据出口

自然前向 current 已切换为 `portfolio-forward-statistical-audit-v2 / portfolio-forward-readiness-v3 → portfolio-forward-statistical-maturity-v3 / portfolio-forward-dashboard-v7 → portfolio-internal-backtest-pack-v6 / portfolio-backtest-return-quality-snapshot-v4` 的单次裁决链。dashboard-v7 仍把 operational truth、statistical maturity 与 `portfolio-forward-local-source-binding-v1` 分开；旧 dashboard-v6/maturity-v2、audit-v1/readiness-v2 与 pack-v5 只保留历史解释，不能经 current route 升级证据。

audit-v2 先从完整 settlement 语义链定位结果与实际调仓门槛首次共同成熟的最短 prefix（当前门槛 60/8），只在这个 prefix 上运行一次 paired bootstrap 与最大回撤风险验收，再冻结 prefix/stage/risk/decision Hash。后续 tail 继续接受完整性核验，但统计上只描述累计结果，不进入第一次裁决：60 时 BLOCK 后 66 时全序列 PASS 不能恢复，60 时 PASS 后更长序列变差也不能改判。风险上限采用严格“小于”，等于预注册上限仍停止晋级。

bootstrap 预算在 resampling loop 之前检查：`resample_count` 必须为 100..50,000 的原生整数，`block_length` 必须为 1..1,024 的原生整数且不能超过 prefix 样本量。maturity-v3 再从 performance 内嵌完整序列重建同一首次共同成熟 prefix、风险收据和冻结裁决，并与 persisted readiness-v3 逐值对照；current scope 为 `PERSISTED_READINESS_V3_AND_FIRST_JOINT_MATURITY_DECISION_REBUILT_FROM_EMBEDDED_FULL_SERIES_NO_SETTLEMENT_REPLAY`，不打开 SQLite、不重放 settlement ledger。有效负结果仍是 `STOP_RESEARCH`，不是待补样本。

archive-v3/local-source-anchor-v1、backup-status-v2 与 watchdog-v3 的既有账本不被覆盖；maturity-v3 继续复核 `FULL / PREFIX / CONTRADICTION / NOT_AVAILABLE`，矛盾会 BLOCK 并清零 progress，FULL/PREFIX 不提升统计状态。report-root writer 现为 pack-v6/forward-evidence-v2；固定 `portfolio-backtest-pack-pointer-v2` 的字段与 Hash 合同不变，本轮未自动重发已有 pointer。历史 pack-v5 bundle 仍可按历史 verifier 自洽，但经 pointer-v2 的 current public loader 必须返回 snapshot-v4 `UNKNOWN/null`。

项目读取边界现共用 `services/forward_artifact_io.py`：active candidate、active research source、performance runner 与 watchdog 都使用 bounded/no-link-or-reparse/strict-object JSON、Windows basename、路径脱敏与内存/递归失败收敛。control/registry/receipt 限 256 KiB、compact candidate 1 MiB、pack/invalidation 32 MiB、observer/performance/statistical status 16 MiB，research/robustness 沿用 256 MiB producer ceiling；shadow runner 未使用的普通 JSON reader 已移除，未验证的旧告警收据也不能抑制新的真实 BLOCK。

前端静态指纹为 `20260814-single-look-contract-1`，冻结收益区继续保持 `SOURCE → GAP → MATURITY → PERMISSION → 历史收益`。`<=480px` 的原生“市场选择” disclosure 默认收起搜索/分类/市场按钮并显示当前标的/类型；真实 480px 核验中，收起时主内容约 y=180、可见市场按钮 0 个，展开时约 y=455、市场按钮 46 个。后续浏览器策略阻止了 720px 键盘步骤，因此 720px/desktop 只以源码/静态合同为证，不声称完整交互或真实设备 QA。

current 激活合并定向 161/161 PASS，覆盖 single-look、maturity/projection/server、pack/pointer 与 lean；Node 完整 evidence 合同与三项 `node --check` PASS。项目读取边界 109 项通过、2 项 symlink 能力跳过；256 KiB 修正后 `portfolio_forward` 16/16；独立终审矩阵 139 项通过、4 项 symlink 能力跳过。这些集合有重叠，不相加冒充全量回归。本轮没有重跑旧 K 线、G50/G51、正式盲测或 lean fresh，没有启动产品服务或正式 runtime 任务，也没有自动发布 pointer。一个 agent 的范围过宽只读检索曾误匹配 runtime 备份中的源码行，但未使用其内容形成结论，且未改动 runtime/备份。

以上所有 PASS 都是合同与实现证据，不是未来盈利证明，不授权 paper，更不改变 live 永久硬锁。

下文历史切片的功能说明继续保留；其中涉及当前缓存身份的表述均以上述 `20260814-single-look-contract-1` 指纹为准。

2026-08-14 的 strategy research 分成两条明确版本线：development writer 仍为 schema 13；formal preregistration/runner 已升级为 schema 14、hypothesis-v3、search-lineage-v1 与 admission-v3。schema 13 的结构化机制条件继续逐项固定 condition ID、开发阶段、白名单 metric、`LT/LTE/GT/GTE`、有限阈值和 `BLOCK_RESEARCH`；schema 14 在其上增加正式搜索谱系，而不是追溯改写旧 Hash。

schema 14 formal 在首次 selection 数据读取前要求 active runtime 根下唯一 canonical registry，由 Store 在同一事务中重建全部 REGISTERED nested-research 协议的全局 trial ledger、claim anchor 与 live audit。ranking 使用 `cumulative_trial_count`，因此更换 family 或 generation 不能把搜索惩罚重置为本批 variants 数。public admission-v3 只能证明离线报告/回执自洽并固定 BLOCK；只有 store-owned live gate 才能放行。任何 path、event tail、claim、lineage 或累计数漂移都会令 formal 冻结候选、TEST、confirmation、holdout 与 forward candidate 为空。

固定 pointer artifact、publication expectation 与 receipt 仍为字段不变的 v1；公共投影按能力精确分版：schema 3–10 使用 frozen-evidence v3，11/12 使用 v5，13 使用 v6，14 使用 `strategy-lab-frozen-evidence-v7`，15+ 失败关闭。v7 强制 hypothesis-summary-v3、admission-v3、post-selection replay-v1、failure-conditions-v4 与脱敏 search-lineage-v1；仅选择时 live registry 绑定可公开 `BOUND`，receipt-only 降为 UNKNOWN。公共对象不含 family 值、注册/候选 ID、路径或 protocol/claim/anchor/lineage Hash；未命中策略使用空 `NOT_IN_REPORT` 隔离视图。

这项门禁解决的是“跨正式注册的搜索次数不能被重置”以及“累计惩罚必须在选择时由 live registry 绑定”；它不把历史回测变成新鲜样本外证据，也不证明未来盈利、WFO、模拟授权或实盘权限。定向验证包括 schema14 CLI 16/16、lineage/admission/protocol 26/26、runner 35/35、companion 68/68、公共 pointer/failure/replay 50/50 与独立扩展审计 71/71；root 另复跑核心 4 项和 public 5 项。集合有重叠，不相加冒充总回归；未读取真实 runtime/数据库/缓存/日志，未重跑旧 K 线、G50/G51、正式盲测或 lean fresh。

2026-08-14 的 schema 11 阶段新增纯 `strategy-frozen-evaluation-replay-v1`，schema 13 development 与 schema 14 formal 均继续继承。它让 `FROZEN_TEST_ONCE` 从冻结 selection rows 与 verifier 重建边界独立复算配置成本、买入持有和 severe 成本；让 `HOLDOUT_CONFIRMATION` 从冻结 CONFIRMATION rows、manifest 与 data policy 独立重建 completed-daily alignment，逐值比对报告 alignment，再显式使用冻结 split policy 重建 schedule，并复算 configured/benchmark/severe、validation/test temporal、完整确认数据集固定切片、prefix invariance 与 lookahead。主收益或成交改成 999、边界漂移、伪 `source_run_hash`、自报 alignment PASS/BLOCK、行集偏斜、无候选时伪造 PASS，以及嵌套权限别名同步重封，均失败关闭。development 仍不产生 TEST/holdout；schema 3–10 的 Hash 与 verifier 保留历史语义。这证明本地冻结 artifact 的内部一致性，不是外部数据提供商的加密真实性，也不能恢复 snapshot 前的完整原始历史；它不校正选择偏差，不是 WFO、盈利证明、模拟授权或实盘权限。

公开层现以纯 `strategy-post-selection-replay-summary-v1` 把上述已验证证据压缩为所选策略的两段中性质量摘要：冻结 TEST 与单次历史留出分别披露候选/结果/单元覆盖、复算完整性、正式聚合数量、最低配置收益、最低基准超额、压力后最低收益、最差最大回撤与总交易数，不披露 symbol、variant、params、候选 ID、路径或原始 blocker。容器、身份、覆盖或 replay 完整性异常会 BLOCK 并将所有数值置空；完整性成立但收益或聚合 outcome 失败时保留有限负值。公开 PASS 是比正式聚合更严格的 replay-preservation 诊断，不改变候选门或 report verifier；单次历史留出始终标为“非自然前向”，不能视为未来表现。

schema 11/12 使用 `strategy-research-failure-conditions-v2`，schema 13 使用 v3，schema 14 使用 v4 并增加“选择时全局搜索谱系未核验”条件；schema 3–10 继续使用 v1。前端把这些证据沿“源 / 稳 / 止”层级展示；合法 v6/v7 `MATCHED` 会生成冻结判据行，v7 另在假设之后显示检索谱系，明确区分选择时 live 核验与当前离线回执自洽。两条未来行仍是 `NOT_DUE`，不新增状态色、请求、轮询或 live region。

当前静态资源指纹为 `20260814-single-look-contract-1`；“止”区账页和检索谱系使用语义化定义列表、中性细线与现有 mono，`<=720px` 保持单列巡检，`<=480px` 逐行单列。冻结组合归属区继续提供默认折叠的完整归属 Hash 核对，不新增请求、live、方向色或权限暗示。控制中心与 watchdog 复用共享权限扫描。完整 Node 合同与三项 JavaScript 语法检查通过；该历史切片当时未做浏览器/真实设备 QA，本轮新增的 480px rendered 证据及 720px/desktop 限制见顶部。

收益质量纯函数也已迁移到共享 canonical 权限扫描器：过去绕开 pack 独立调用时，大小写、驼峰或分隔符别名可能未被旧精确键集合识别；现在这些嵌套真值会把 quality 置为 BLOCK，而不是 `AVAILABLE`。这项整理没有改收益公式，也不把 quality v1/v2/v3 或 pack v2/v3/v4/v5 的合同跨版本混用；quality、pack、固定 pointer 的定向交叉通过。

成交链演练与组合统计审计的默认来源也完成单一化：两条 runner 不再各自 raw-read 登记并 glob 同批报告，而是先经过 canonical active-candidate 全合同，再精确读取 completion receipt 绑定的同目录报告，重核文件 SHA、batch 与 frozen candidate 四方身份。绑定文件缺失但存在另一个同 batch 副本、路径逃逸、登记/候选/稳健性/完成收据漂移都会在业务计算前 BLOCK；显式 `--research-report` 离线入口不变。该整理只收敛来源身份，不新增回测或统计结论。

strategy research 固定指针发布现由 versioned expectation 绑定本次内存报告、确定性 UTF-8 字节、basename、report/file Hash、文件长度、schema、batch/dataset/run Hash、governance 与创建时间。publisher 原子替换字段不变的 pointer-v1 后，重新读取并逐值验证 pointer/report；runner 又从 expectation 唯一重建 pointer Hash 并核验回执。formal 与 development 对非 report-root 输出都在 hypothesis、Store、claim 和行情加载之前阻断。它降低发布窗口替换、伪回执和不可恢复嵌套输出风险，但两个本地文件仍不是跨文件原子事务，也没有外部签名信任根。

本地来源锚现已按上述窄范围实施，但它仍不是 external authenticity：同机同权限写者可协调重封数据库、archive、backup 与 watchdog，删除两份新收据也可把覆盖降级为 `NOT_AVAILABLE`，本地没有外部单调状态证明收据曾存在。真正外部锚至少需要非导出签名密钥与外部 append-only/WORM/timestamp receipt；即使成立也只证明某组字节在某时存在，不证明行情正确、成交真实或未来盈利。

哈基米当前最需要的不是继续扩大旧 K 线回测、策略数量或交易所数量，而是把三件事做扎实：

1. 每天只处理真正新增的完成 K 线，并把“新增、跳过、阻断”解释清楚。
2. 让行情来源、新鲜度、图表状态和研究可用性在一个页面上说真话。
3. 将未来的小资金试验作为独立工程阶段准备，不在现有服务中提前打开实盘入口。

本轮已完成“增量计算”“轻量验证”“行情真值中心”“增量前向观察看板”“最近自然前向观察收据”“相邻观察变化收据”“最近两次 observer 作业回执”“股票自动刷新去重”“公开行情提供商共享节流”“参数平台 v2”“证据权限分栏”和“内容寻址定向验证收据”。完整 750 项回归仍保留为冻结新基线或安全发布门槛，但不再用于每次日常小改动。

2026-08-11 又完成了一次隔离只读实例验收：构建指纹前后相同，HTTP 只读与 423 纸盘 arm 合同成立，AAPL/NVDA/BTC-USDT 三标的切换时图表不消失、不串标的，控制台无 error/warn。该运行态证据不替代完整回归，也不授予模拟或实盘权限。

同一轮验收还暴露并修复了一个展示一致性问题：低质量 `offline-seed` 报价可以覆盖已有较好来源，股票盘口又优先读取了另一来源的价格日志。现在报价身份按来源等级和时间倒退保护合并，盘口/价格日志/非信号微结构只消费当前同源值；报价源与 K 线源仍分开披露，预览状态不会冒充实时。定向 guard 测试、`app.js` 语法和 Electron check 均通过。

随后补齐了 ResearchBrief 的跨项目协作边界：`ResearchBridge` 提供 1.1 合同并兼容 1.0，GET 合同带 `contract_hash`，导入支持可选 `idempotency_key/event_id`。相同内容的重试只返回原摘要，内容冲突返回 409，不产生第二条记录；摘要仍强制 research-only，禁止账户、订单、凭据和执行字段。该切片只运行两个定向用例和 AST 检查，没有接入新的交易权限。

2026-08-12 又补齐了行情刷新层的一个实际瓶颈：借鉴 Freqtrade 的“只处理新数据”、Hummingbot 的 connector 级限流和 CCXT 的共享请求边界，OKX 公共 GET 现在在提供商级共享有界窗口内准入；instrument rules 与盘口本身仍按标的 singleflight，跨端点的重复刷新不会各自绕过节流。连续失败只触发有限指数退避，不做隐藏重试；超过窗口直接给出可解释的重试提示，并保留 last-good/STALE 语义。该机制只服务公开只读行情，不改变研究门禁、纸盘授权或实盘硬锁。

同日对“策略是否实用”的判断做了一个轻切片：不引入自动 hyperopt，也不拿最佳参数直接当可用参数。schema-4/5/6/7 报告强制使用 `strategy-parameter-plateau-v2`，只以报告内冻结 variant 顺序建立邻接拓扑；最佳点必须本身合格，并至少连接一个合格的直接相邻近优点。冻结序列邻接不等于多维参数数值距离。schema-3 历史报告仍可没有摘要，或按 legacy v1 复算；v4 及以后缺摘要、降级或篡改均失败关闭。该投影不改变候选、不重跑 G50/G51、不启动正式盲测，也不授权模拟或实盘。

成本压力合同同时收紧为“最差压力收益仍为正”，避免容差内的负收益被写成通过；时间顺序证据明确标注为固定参数时间切片，参数不会在每折重新拟合，因此不得宣称真正的 walk-forward optimization。schema-5/6/7 保留 v2 cell，schema-8 保留 v3，schema-9 保留 v4 与 `strategy-fixed-chronological-slice-evidence-v1` 的历史拓扑/类型/汇总语义。schema-10 首次使用 `strategy-research-selection-cell-evidence-v5`、`strategy-fixed-chronological-slice-evidence-v2` 与 `strategy-selection-cell-replay-v1`；schema-11/12/13 继承这条 selection replay，schema 11 起另有顶部说明的 post-selection TEST/holdout direct replay。formal verifier 先从完整冻结 snapshot 与 split policy 重建 train/validation 边界，再用同一纯因果内核重放固定 3 折、训练段、配置成本验证段、买入持有基准、stress/severe 成本场景和前视/前缀不变性检查，并核对稳定指标与完整 trades/equity digest。证据 folds、主验证收益、基准、成本摘要均不再是结果真值；999 指标、digest、fold policy、边界及所有外层 Hash 一致重封仍失败关闭。development 报告先物理移除受保护 test 后缀，再按 `development-selection-prefix-split-v1 / TRAIN_VALIDATION_ONLY_INDEX_SPLIT_V1` 在冻结的截断 prefix 内计算 `train_end_index=floor(N × train_ratio/(train_ratio+validation_ratio))`；verifier 从冻结截断 rows 与 batch split policy 独立重建并逐值比对。这个边界只在开发域内确定，不等价于 formal 的完整 snapshot 日历重建，不提供新鲜样本外或 WFO 证据，也不能冻结候选。schema-3–10 的历史 Hash、默认值与 verifier 语义不追溯修改。schema-7 引入 hypothesis-v1 并由 schema-8/9/10/11/12 继承；schema-13 才引入结构化 hypothesis-v2，不能把旧自由文本合同升级解释。selection replay 只是固定参数历史选择结果的语义复算，不校正选择偏差；所有证据仍不证明盈利或授予模拟/实盘权限。

schema-9 的逐折结果域继续按历史完整性合同解释：它证明拓扑、类型与自报明细汇总自洽，但不追溯声称引擎重放。schema-10 已封闭该缺口：逐折结果必须由冻结 selection rows、策略参数、风险参数、当前执行模型与信号引擎直接重算；`NaN`、`Inf`、真值字符串、布尔/负交易数、999%/999 trades 一致重封、digest-only 篡改或自选连续折法都会 BLOCK。schema-3–10 保持各自历史 verifier，不被 schema-11 追溯升级。

schema-10 的 `strategy-selection-alignment-input-v1` 只封存对齐所需的日期/完成态投影，并绑定 SELECTION role、symbol/market/timeframe/source 和 manifest Hash。verifier 用冻结 data policy 独立重跑 alignment，不让报告自报的 PASS/BLOCK 控制后续 coverage；PASS→BLOCK 后删空证据、source/role/dataset 漂移均失败关闭。alignment 或 selection admission 非 PASS 时，当前 writer 只返回脱敏失败收据，不生成报告、不完成 formal registry、不发布 pointer；因此不能把该结果解释为 valid-negative 完整报告、候选冻结或任何权限升级。需要可恢复的终态 FAILED 时，应新增外部锚定 receipt，而不是放宽报告 verifier。

正式预注册 CLI 进一步改成“不可覆盖 sidecar 先发布、registry 后登记、领取前再复核”。当前 `strategy-matrix-protocol-v3` 把 sidecar 路径与不可覆盖模式纳入 Hash；UUID 临时文件、独占创建、fsync/no-clobber、registry 伴随文件冲突门禁和读只模式前置阻断共同防止失败命令留下可领取注册。注册后 sidecar 被替换时，命令与后续 claim 都阻断。v3 继续强制 v2 的 `daily-batch-alignment-v2` 与 7 天边界偏移限制，不能通过重封降级。文件与 SQLite 之间仍无跨资源原子性：DB 失败可能留下不可领取工件，严格恢复只复用原未过期协议，不会生成新时钟后误当幂等重试；legacy v1/v2 仍按历史合同兼容。

正式 strategy research 与 strategy matrix runner 的结果完成都不再直接执行“registry `COMPLETED` 后才首次写 final”。`prepared-research-result-v1` 先封存已携 completion receipt 且通过正式报告 verifier 的完整报告，使用 protocol Hash 推导的隐藏 basename、UUID 临时文件、`fsync` 与 no-clobber 发布；registry complete 再用同一纯 completion builder 复算并要求收据逐值一致。prepared 后的 `RUNNING`/`COMPLETED` 中断可在下一次调用最前段恢复，恢复测试明确阻断 build、claim、暴露审计、新时钟与数据加载；final 冲突和发布失败均非成功。strategy research 继续使用既有固定 pointer；matrix 没有固定 pointer，本轮没有新增。matrix 的 report-level verifier 不混入候选消费端 freshness，只验证恢复工件本身。该机制不允许重跑一次性留出数据，也不清理未知工件；claim 后但 prepared 前的进程崩溃仍不可安全恢复，文件系统与 SQLite 也仍不是跨资源事务。

自然前向到期统计最初以独立、版本化历史切片落地。`portfolio-forward-statistical-audit-v1` 从语义校验通过的 settlement Hash 链冻结逐日策略/基准配对序列，完整复用已验证历史审计的 moving-block、置信度、概率门槛、Bonferroni 和 trial-count 口径；只允许候选预注册的 forward 样本下限与历史阶段下限不同，并显式列出。历史 G42 统计 claim 的有效 `BLOCK` 只提供合同来源，不决定新结果；未同时达到收益期和实际调仓门槛时为 `NOT_DUE` 且不运行 bootstrap，到期缺证据、身份错配或权限升级均失败关闭。`portfolio-forward-readiness-v2` 明确把这类组合统计证据与盈利证明、模拟授权和实盘权限分开。该能力最初以 pack v3 接入，随后历史 pack-v5 继续携带 forward-v1；current audit-v2/readiness-v3 与 pack-v6/forward-v2 语义以顶部为准。所有版本最高只到人工研究复核，不能静默改写成交易权限。

回测收益也从“只看累计收益”升级为可语义复算的质量证据，而不是继续重复旧 K 线。report-root current writer 使用 `portfolio-internal-backtest-pack-v6`、`backtest-return-quality-v3` 与 forward-evidence-v2；它沿用 pack-v5 建立的紧凑 source manifest 和三成员 content-addressed bundle。loader 只按 manifest 中的 basename、角色、SHA-256 和字节数精确读取，不 glob、不猜最新文件，再从 detached bytes 复算收益、回撤、样本、成本和统计语义。pack v4/quality-v2、pack-v5/quality-v3 以及 v2/v3 的历史 verifier 语义均保留，不被追溯重解释；来源 BLOCK 的诊断 bundle 会退空所有数值且不发布 pointer。组合来源固定属于 portfolio research protocol，strategy schema-7 明确 `NOT_APPLICABLE`。所有版本仍永久声明非盈利证明、不可选参、不可自动开启模拟、不可实盘。

v5 已把 v4 的嵌入来源拆成持久化的三成员不可变 bundle，并以同一份 detached parsed object 和 exact bytes 构建借用式 normalized semantic view；不再构造瞬时 v4 source document/source evidence/result evidence 包装，v2-v4 的 schema、字节与 Hash 语义保持不变。8 MiB 高密度合成 JSON 的 `tracemalloc` 定向测量从约 4.51x raw 降到 2.50x raw；这只表示 Python 分配跟踪，不是生产 RSS，且 canonical JSON 序列化仍是剩余峰值。本轮未读取真实大工件，因此不宣称真实大体积性能或历史收益兼容验收。进一步的优先级仍是不同信任域的外部 anchor/签名或等价可信收据，而不是重跑旧 K 线。

紧凑化审计提出的完整 bundle 最初落地为 pack v5，current pack v6 继续复用：source manifest 绑定 research/statistical exact bytes、阶段 Hash、来源身份、candidate/evidence/pack Hash 与整个 bundle Hash；固定 pointer 和 archive 都消费同一核心 bundle verifier。这个实现仍固定 `external_anchor_verified=false`、`cryptographic_authenticity_proven=false`：同一权限主体可重封整条本地链，本地无密钥 Hash 只证明 bundle 自洽，真正外部真实性仍需要不同信任域的签名、WORM/透明日志、独立 ACL 收据或人工外部 pin。

当前 report-root 发布使用 `portfolio-backtest-pack-pointer-v2`，但继续占用 `current_internal_portfolio_backtest_pack.json` 固定文件名。pointer v2 绑定 content-addressed bundle 目录、manifest、exact pack 与 pack/evidence/candidate/bundle Hash；通用 publisher 使用 UUID 临时文件、`fsync` 和 hardlink no-clobber，已有同路径只接受精确字节幂等。Windows 大小写/NFKC、尾点/尾空格、ADS、设备名、symlink/reparse 和等价 basename 在读取或 build 前失败关闭。显式外部 `--output` 仅生成 legacy v4 的不可变离线导出，不发布 pointer；report-root 本身及其后代路径在 build 前阻断。发布间替换、cleanup 失败、manifest/inventory/Hash 漂移或权限别名均返回非成功，这仍不是跨文件事务或外部不可篡改证明。

该 GET 的 current 外层合同为 `portfolio-backtest-return-quality-snapshot-v4`。v1 pointer 与 pack v2/v3/v4/v5 保留历史读取和各自冻结 verifier，但 pointer-v2 current public loader 对这些 legacy pack 统一 `UNKNOWN/null`；只有 exact pack-v6/quality-v3/forward-evidence-v2 可进入 snapshot-v4 白名单摘要，交叉/未来组合失败关闭。公开层不返回完整 source evidence、来源身份内部字段、spec、settlement、路径或整包。前端资源指纹已统一为 `20260814-single-look-contract-1`，只中性显示冻结裁决与描述性 tail，不称外部真实性或盈利。界面的归属脊柱仍只在冻结组合与自然前向两个候选 Hash 各自通过完整合同时声明同源，策略侧始终没有白名单桥接；候选不同或缺证据时禁止合并解读。

pointer 64 KiB、manifest 256 KiB、pack 32 MiB、research 256 MiB、statistical 16 MiB 与三成员合计 304 MiB 均使用有界 reader，在 JSON parser/verifier 前阻断超限；strict JSON 同时拒绝 duplicate keys、NaN/Infinity 与过深结构，exact size/Hash/inventory 不符则 BLOCK，错误不回显本地路径。pointer、pack/bundle、公开 loader 和攻击矩阵定向通过。`portfolio-evidence-archive-v3` 也复用 exact bundle：current writer 支持 v1/v2 历史 archive，research member 只保存一次并同时作为 replay source；archive manifest 精确绑定成员与 bundle Hash，restore/verifier 不 glob、权限恒假。archive/replay/篡改/缺失/legacy 定向通过；未读取真实 runtime/SQLite/K 线，也未启动 HTTP/浏览器。

current immutable manifest、pack-v6（复用 pack-v5 detached source）、pointer-v2 与 archive-v3 的对象解析已共用纯 stdlib `strict_json_artifact`，精确拒绝非 UTF-8、非 object root、任意层 duplicate key、NaN/Infinity/指数溢出与 root=1/max=128 以上嵌套；canonical bytes/Hash 仍由各工件服务负责。pointer-v1 和 legacy archive 普通读取保持旧解析合同，v2 无 legacy parser 降级通道。pack/quality golden Hash 与 detached 摘要未漂移；该历史 strict/immutable/pack/quality/pointer/archive 交叉 150/150 通过，3 项因宿主 symlink 权限跳过，current activation tests 见顶部。

前端窄切片继续收紧可见语义：研究门槛、固定参数时间切片、数据清单与审计工件统一映射为描述性研究证据标签，`PASS/READY` 仅留在元数据。schema 3–10 使用策略实验室 v3，schema 11/12 使用 v5，schema 13 使用 v6，schema 14 使用严格 v7；跨版本组合、v4 与 schema15 均失败关闭。v6/v7 会逐字段校验结构化 hypothesis/admission 并重算机制谓词，v7 还要求脱敏 search-lineage BOUND、全局安全计数与选择时 live binding。只有合法 MATCHED 视图生成判据行；v7 在事前假设之后另显示“检索谱系”，明确“选择时核验、当前仅离线报告/回执自洽”。未匹配视图不借用其他策略证据，也不显示 family、候选 ID、Hash 或路径。界面不新增状态色、请求、轮询或 live region；本轮没有启动服务、浏览器或旧 K 线回测。

冻结收益质量主层级新增“下一条可信证据”账签。UNKNOWN 只从客户端可复算的安全、来源、版本、阶段、数值一致性与自然前向合同事实选择固定类别；已验证的 failure 条件只公开四类计数，原始 blocker、路径、候选身份、完整 Hash 和收益字符串不进入正文。阶段名、三类阶段状态、基准依据与 evidence stage 也必须命中枚举并映射为固定文案，不能借 BLOCK/PARTIAL 进入正文、dataset 或 title；中文 `可下单/已授权/实盘授权` 权限键同样优先失败关闭。有效负结果明确停止晋级，不被误写成“尚缺证据”；fallback 同步完整 forward/schema/source-mode/cue shape。布局只用中性细线与现有 mono，无新增请求、live、卡片或分类颜色；三个 Node 合同与语法检查通过，未做浏览器/设备 QA。

策略实验室的冻结来源由 `strategy-research-report-pointer-v1` 绑定，独立 GET 只读该指针及一个报告，不 glob、不猜最新文件、不加载 K 线。schema-6–14 都核对完整 implementation manifest；schema-7–12 语义复算 hypothesis-v1，schema-13 复算 hypothesis-v2，schema-14 复算 hypothesis-v3/search-lineage/admission-v3，schema-3–6 只显示历史未绑定。前端按当前策略在页面会话内缓存；60 秒即时实验室轮询不会重复验算冻结报告。failure 条件按 schema 3–10/v1、11–12/v2、13/v3、14/v4 精确分派；自然前向仍是独立证据。当前页面按“源 / 稳 / 止”三段呈现并从 `<=720px` 起单列；真实运行态指针和浏览器渲染仍未读取/验收。

时间证据不再只显示一句“未核验”。纯 `strategy-research-currentness-facts-v1` 把已验证报告时间、报告中两处数据截止日和请求时观察毫秒复算为报告年龄与 UTC 日历日差；来源日期不一致、未来时间、畸形日期、伪整数或前端重封年龄都会失败关闭。该事实绑定最初进入 frozen-evidence v2，当前由 v3 继承；固定 pointer 与历史研究报告 schema 不被追溯修改。阈值恒为空、日历日不冒充交易日，因此只能帮助人工判断证据年龄，不能产生“新鲜/过期”、选参、盈利或交易权限结论。

冻结收益质量台账随后增加可展开的验证段/测试段证据带，按段显示来源状态、样本量、基准超额依据和统计主张；阶段字段缺失、伪数字或权限异常时整区继续 `UNKNOWN / 未核验`。该改动不增加请求、不重算收益、不改变研究/模拟/实盘权限，只通过 Node 静态合同、语法检查和 frontend lean 验证，尚未声称 HTTP 或浏览器运行态验收。

大服务拆分的第三个小切片也已完成：研究上下文与摘要的最终 JSON 组装进入纯 `services/research_query_projection.py`，I/O、查询、缓存、数据库和回退仍留在 `server.py`。根权限由投影内部固定为只读且禁止实盘，调用方和嵌套内容都不能升级。文档入口已收敛到 `docs/README.md`；小资金纯规划视图则改为证据缺口优先、名义封套和按需深度详情，不使用“准备”或余额冻结文案暗示执行。

2026-08-12 的后续窄切片继续沿“轻测试、重边界”推进：策略研究台的参数规划与并行比较已各自进入纯研究投影，机器人中枢、角色调度、调度变更结果和机器人档案也通过 `services/bot_research_projection.py` 统一中性化；本轮又把异动雷达、异动详情和走势驾驶舱接入纯 `market-anomaly-research-projection-v1`，并把全局配置总控的两个只读/应用响应接入 `configuration-research-projection-v1`。方向/偏好/READY 类状态只作为 `raw_*` 审计元数据，前端改用研究观察与中性 tone；配置检查分、AI/行情来源和实盘边界不再以绿色或“就绪”文案暗示授权，配置详情不泄露路径或密钥。OWNER/可执行/armed/推荐/资金比例只作为 raw 审计元数据，前端改用研究角色、开发期分、证据缺口和 `null`；研究角色变更仍只记录规划标签，不生成订单。fresh research lean 3/3（101 个守卫用例）与 frontend lean 5/5 通过，未启动服务/浏览器，未读真实 pack，未重跑旧 K 线、G50/G51 或正式盲测。

回测页随后补上独立的“稳健性与成本证据”台账，消费已有交互回测报告中的 `temporal_validation`、固定参数时间切片/折叠、成本压力和前视检查；它不读取或重建冻结 pack，也不把固定参数切片包装成真正的 walk-forward optimization。交互回测自身仍不提供参数平台；策略实验室新增的冻结参数平台证据来自另一条固定 pointer GET，不与交互回测混用。缺失值保持“未提供/未核验”而不补零，所有文案继续 research-only、模拟未授权、实盘永久硬锁。该切片只运行前端静态合同和语法检查，未启动服务、浏览器或回测。

交互回测的 100 格候选随后从“排序列表”升级为 `backtest-risk-control-surface-v1`，但范围被严格命名为风险控制参数表面：5 档仓位、5 档止盈、4 档止损由同一个冻结常量同时驱动计算与投影，逐格复核原生有限分数、收益、回撤、闭合交易数，使用每轴一步邻接判断最高分周围是否存在跨至少两轴的连通近优区域。缺格、重复、越界、伪数字、最高分无成交和孤立峰值都会降级。前端从全部 100 个白名单单元重新计算最高分、25%/1 分容差、邻接、跨轴支撑与连通组件，摘要或权限被重封篡改时整区回退未核验。这里吸收了 [QuantConnect 对参数敏感和过拟合的警示](https://www.quantconnect.com/docs/v2/writing-algorithms/optimization/parameters)、[优化结果应检查参数敏感性的呈现思路](https://www.quantconnect.com/docs/v2/cloud-platform/optimization/results) 与 [Freqtrade 分离参数空间、限制搜索范围的机制](https://www.freqtrade.io/en/stable/hyperopt/)，没有照搬其策略、资产、优化结论或执行能力。该表面仍是同一历史数据的开发描述，选择偏差未校正，不是策略信号参数平台、样本外验证、WFO、盈利证明或模拟/实盘授权；正式 PBO 等多重试验校正也没有被伪造为已完成。
- 直接的 `/api/market/scanner` 现在也收口到 `market-scanner-research-projection-v1`：策略 ID/动作/风险/“最高机会”摘要在可见层中和，原始值只留 `raw_*`，扫描分数保留为描述性数值证据；前端点击只切换标的，不自动套用策略，普通刷新不写入状态。新增 3 个纯内存合同与前端静态断言，未启动服务或重跑行情。
- 同步收紧 `summarize_cost_sensitivity`：基准和每个可用压力场景的收益/回撤必须是有限数值，缺失或伪布尔场景直接阻断并返回 `null`，不再用 0 制造“最差压力”或恶化幅度；真实负压力仍保留为负值并阻断。该修复只改变证据解释，不重跑历史 K 线。
- 固定参数折叠摘要随后采用同一严格合同：每个 `ok=true` 折叠的收益、回撤必须有限，闭合交易数必须为非负整数；缺失/非有限/伪布尔/失败折叠会阻断，累计交易数和最差回撤改为 `null`，不再使用 0 或默认回撤掩盖缺口。该修复仍只改变证据解释，不声称真正 WFO，也不重跑历史 K 线。
- 横截面验证与冻结测试聚合随后收紧为严格原生数值：数字字符串、布尔值、负交易数和非有限指标不能进入 `usable` 集合，覆盖门禁会明确阻断，不再由 `int(... or 0)` 伪造交易样本。该修复只复算已有内存 cell，不重跑行情。

同一轮补上顶部状态栏的权限中性化：模拟盘灯不再随 raw `armed` 状态变绿，固定显示“模拟未授权”；运行态快照若存在 armed 只作为审计元数据，不能把“模拟运行”或颜色当作授权。该改动不触碰模拟状态机、HTTP 423 或任何订单路径。

行情 AI 研究会议顶部的“下一步”同时改为“研究观察”，只描述等待确认/样本条件，不生成行动暗示；盘口策略提示与风险引擎也固定为研究观察/权限待核验，raw `armed` 与模拟条件只保留为审计元数据。异动雷达/走势驾驶舱与全局配置总控都使用纯研究投影；当前静态缓存指纹见顶部 `20260814-single-look-contract-1`。控制中心即使收到上游授权真值也只显示“模拟未授权”，该改动不改变行情、模型或权限。

schema-5/6/7 batch spec 都要求 `limit`、测试候选上限和确认候选上限为原生整数；数字字符串即使随报告 Hash 一起重封也会失败关闭。开发期策略比较、回测候选行和分数使用中性展示，点击只复制研究参数到表单并标明未运行、未授权；没有因此启动服务、浏览器或旧 K 线回测。
- internal pack v2/v3 的冻结 `forward_progress` 现在增加原生数值合同：若字段存在，六个自然前向/调仓计数必须为非负原生整数，`scheduler_health` 必须是非空字符串；重封 pack Hash 不能把数字字符串伪装成有效进度。旧手工 v2 工件缺字段仍仅作兼容，不会升级研究或执行权限。

## 产品定位

- **产品身份**：个人本地运行的量化研究、行情核验、自然前向观察与隔离模拟工作台。
- **目标用户**：希望得到专业证据，但不想维护机构级基础设施的自用研究者。
- **核心差异**：数据来源透明、研究结论可追溯、执行权限与研究严格分离。
- **当前取舍**：优先解决“结果是否可信、今天发生了什么”，暂不追求多交易所、多策略与自动实盘。

## 相邻自然前向观察变化

LEAN 的 InsightManager 保存按标的组织的结果序列，TradingView 把脚本、输入和图表上下文冻结进事件实例，NautilusTrader 为事件保留稳定身份与发生/初始化时间，Hummingbot 则把最近运行和历史结果分开查询。哈基米只吸收其中“相邻结果可比较、来源可追溯”的部分：

- ledger audit 对全部有效观察建立有序 chain Hash，变化收据只比较同一候选链尾相邻两条观察；
- 不足两条明确标记历史不足，空跑保留上次已验证比较，旧工件安全隐藏；
- 后端保留结构化集合、比例、原因、状态和风险变化，控制中心只显示集合是否变化及风险复核迁移；
- 变化只能解释“观察结果与前次不同”，不能推导买卖、强弱、收益或授权。

没有接入 TradingView Webhook、LEAN PortfolioTarget/Execution、Nautilus 事件重放执行或 Hummingbot executor。日常可解释性的下一步已经收敛为“最近两次 observer 作业结果”，而不是增加旧 K 线回测或新策略。

## 最近两次 observer 作业回执

Hummingbot 的运行历史接口把当前实例和历史运行分开，NautilusTrader 则强调稳定事件身份与事件时间/接收时间。哈基米没有照搬交易 executor 或事件总线，只把这两项机制压缩成最近两张只读作业回执：

- 只有真实启动过的 observer 进程才推进回执链；普通 scheduler 心跳只携带既有链，候选激活身份变化则开启新链；
- 每张回执同时绑定调度决策、到期日期、作业 ID、候选激活身份、进程结果、observer 工件和 ledger 前后 audit 水位；父调度器将相同关键 claims 另封为 `portfolio-forward-scheduler-attempt-evidence-v1` 写入当前工件，覆盖退出码、超时/启动失败、前后候选与账本及前一张回执头，使最近结果不能只靠重封 scheduler 摘要改写；
- `NO_NEW_BAR` 只表示确实仍在等待新完成 K 线，`NO_WORK_ALREADY_ACCOUNTED` 单独表示新日期已经被安全计入或分类，二者不再混写；
- 账本发生意外变化、audit 非 PASS、候选漂移、工件对不上或超时都会成为 `FAILED + reconciliation_required`；最近作业仍需对账时不会自动再启动 observer，控制中心只显示异常并隐藏不可信细节；
- 新写入的 scheduler 状态使用 `portfolio-forward-scheduler-status-v2`；有当前 attempt 证据时必须携带与之逐字段一致的非空最新回执，空链、截断或降级为 v1 都会失败关闭。只有没有当前 attempt 证据的明确旧版 v1 工件可以按未知兼容；
- API 与页面不保留 stderr/stdout、命令、环境或路径，不新增请求、按钮、告警、订单与授权。

机制来源：[Hummingbot API 运行历史](https://hummingbot.org/hummingbot-api/routers/) 与 [NautilusTrader 事件身份](https://nautilustrader.io/docs/latest/concepts/events/)。这里的 Hash 是项目内一致性证据，不是受保护签名，也不能解锁模拟或实盘。

## 最近自然前向观察收据

参考 LEAN 对 Insight 生成/结束结果的生命周期记录，以及 NautilusTrader 将只读 Actor 与可下单 Strategy 分离的机制，当前控制中心新增 `latest-forward-observation-receipt-v1`：

- 只从 ledger 审计通过的最近有效观察生成，绑定 candidate、dataset、decision、risk、observation、forward-state 与 ledger audit；风险快照必须自校验，展示投影必须和嵌套 decision 精确一致；
- 本轮 `records` 与历史最新收据分开，空跑保持 `processed_count=0`，但不会丢失上一张有效结论；
- 旧工件缺收据时安全隐藏，非空收据被篡改时失败关闭；
- 页面只展示“观察目标（非订单）/ 风险复核 / 收据 / 下一步”，不生成方向、排名、订单或授权。

这一步吸收的是“结果可追溯”而不是“自动执行”：Freqtrade 的 dry wallet/模拟成交、LEAN 的 PortfolioTarget/Execution、TradingView webhook 与 Hummingbot executor 均未接入。

## 同类项目启发

候选范围按“直接、相邻、标杆”分层，只保留对当前产品有可迁移价值的四个项目。

| 项目 | 层级 | 已验证机制 | 哈基米应借鉴 | 当前不做 |
|---|---|---|---|---|
| Freqtrade | 直接 | 将 API 存活、bot 循环健康与运行状态分开，并支持只处理新完成 K 线 | 将“服务在线、观察器运行、数据可用”分层；已计入 K 线默认不重算 | 不继续用同一批旧数据反复超参搜索 |
| Hummingbot | 直接/相邻 | 长期 controller 与有限 executor/instance 生命周期分离，connector 另有 readiness | 用长期调度器管理有限观察作业，但不引入交易执行语义 | 不为“连接器数量”提前接入大量交易所 |
| NautilusTrader | 标杆 | 启动前准备与对账失败会阻断运行，事件有新鲜度和队列状态 | 前向 observer 启动前必须核对候选、ledger 和数据修订证据 | 不用合成订单或成交修复只读证据 |
| QuantConnect LEAN | 标杆 | 交易日历感知的调度，并明确收盘事件与完成数据到达存在先后顺序 | 下一次检查绑定交易日历和完成确认延迟，不在收盘瞬间抢读未完成 K 线 | 不引入机构级全资产框架 |

来源交叉核对：

- Freqtrade：[REST API 状态分层](https://docs.freqtrade.io/en/latest/rest-api/)、[官方仓库](https://github.com/freqtrade/freqtrade)
- Hummingbot：[Instances 生命周期](https://hummingbot.org/dashboard/instances/)、[V2 策略组件](https://hummingbot.org/strategies/v2-strategies/)、[官方仓库](https://github.com/hummingbot/hummingbot)
- NautilusTrader：[live 与对账](https://nautilustrader.io/docs/latest/concepts/live/)、[事件系统](https://nautilustrader.io/docs/latest/concepts/events/)、[官方仓库](https://github.com/nautechsystems/nautilus_trader)
- QuantConnect LEAN：[Scheduled Events](https://www.quantconnect.com/docs/v2/writing-algorithms/scheduled-events)、[官方仓库](https://github.com/QuantConnect/Lean)

这些项目证明的不是“更复杂就更好”，而是四条值得保留的产品原则：先试跑、适配器隔离、事件语义统一、成交真实性分层。

## 本轮已经优化

### 1. 轻量验证入口

新增 `run_lean_validation.py`，提供 `safety`、`market`、`research`、`frontend` 与 `core` 五个定向档位。所有档位使用临时 runtime，跳过本地 AI 环境文件，不运行 unittest discovery，也不启动正式研究。

本轮 `core` 实跑：

- 7 个检查全部通过；
- 覆盖 28 个关键 Python 测试，以及关键 Python/JavaScript 语法和股票报价守卫；
- 总耗时 6.856 秒；
- 不等同于完整 750 项回归，也不会被表述成完整回归。

建议用法：

```powershell
python run_lean_validation.py --profile market
python run_lean_validation.py --profile safety
python run_lean_validation.py --profile core
```

### 2. 内容寻址定向验证收据

日常确定性检查现在借鉴构建系统的 action cache 思路：只有输入清单、精确命令、工作目录、工具链与固定环境策略完全一致，才允许复用旧 PASS。收据输出明确区分 `EXECUTED` 与 `REUSED`；`--fresh` 强制执行，`--dry-run` 零执行、零写入。

- 受控输入只包含明确源码、测试、依赖清单和 Electron 两个包清单；本地配置、runtime、数据库、缓存、日志、截图在任何内容读取前排除。
- 子进程使用严格最小环境，不继承 `PYTHONPATH`、`NODE_OPTIONS`、额外 HAKIMI 开关或凭据。
- 日常 lean 可以复用严格一致的本地 PASS；正式 readiness 仍要求当轮 `EXECUTED`，浏览器、HTTP 423、当前进程和 SQLite 证据永不复用。
- SHA-256 seal 只证明本地字节后来未变化，任何本地用户都能重新计算；因此它是 PASS 缓存与一致性收据，不是数字签名或独立可信 attestation。

当前小型验收先真实执行 `python_compile + frontend_syntax + history_concurrency` 三项，再原样复用：第一次 3 `EXECUTED`，第二次 0 `EXECUTED / 3 REUSED`。相关合同 18/18 PASS；没有运行完整回归或旧 K 线。

机制来源：Bazel 的 [action cache 与 CAS](https://bazel.build/remote/caching)、Nix 的 [derivation 精确输入](https://releases.nixos.org/nix/nix-2.31.0/manual/store/derivation/index.html)、in-toto 的 [Statement subject/predicate](https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md) 和 SLSA 的 [provenance 模型](https://slsa.dev/spec/v1.2/provenance)。本项目只迁移“精确身份与清晰来源”机制，没有搭远程缓存、签名服务或宣称 SLSA 等级。

### 3. 增量自然前向观察

新增纯规划器 `build_incremental_observation_plan`，并将前向 observer 改为：

- 默认只计算冻结日之后、尚未记录且未被分类的新日期；
- 已记录日期不再重复运行完整前缀切片、回测、相关矩阵和风险计算；
- ledger 审计不通过、日期身份冲突或数据修订证据异常时失败关闭；
- 只有显式传入 `--replay-recorded` 才重放已记录日期，且重放不会夹带新日期；
- 输出 `incremental_plan` 与 `work_summary`，直接说明处理、跳过和延后的数量；
- 始终保持 `observation_only=true`、`simulation_only=true`、`paper_authorized=false`、`live_order_allowed=false`。

相关 26 项定向测试全部通过，命令总耗时 0.851 秒；三个变更文件编译通过。没有运行完整回归。

### 4. 行情真值中心

控制中心新增按活动标的显示的行情真值带，明确给出报价源、K 线源、快照新鲜度、最近完成 K 线和下一步动作。后端把“服务可响应”与“数据可用”拆成两个合同：全新进程即使服务在线，只要尚无可信快照就显示 `UNKNOWN`，不再默认 `READY`。

关键实现：

- 只检查共享内存快照，不为健康检查主动发起行情请求；
- 只把时间戳有效、明确 `complete=true` 的 K 线计为最近完成 K 线；
- 快照、报价或完成 K 线过期会降为 `STALE`，未来时间戳、隔离、尺度异常或修订阻断会失败关闭；
- 前端按 `symbol + bar + session + symbolVersion` 隔离请求，旧标的响应不会覆盖新标的；
- 控制中心一次请求返回行情真值和前向状态，只渲染一次；
- 新的空运行目录也能以只读、未初始化、阻断状态启动，不创建 SQLite 文件。

轻量验收结果：`market` 档位 5/5 检查通过，包含 13 个 Python 合同测试、关键 Python/JavaScript 语法和股票报价守卫，总耗时 1.717 秒。浏览器中 AAPL 在无历史库且上游失败时只保留明确标注的快速预览，真值保持 `UNKNOWN`；BTC-USDT 使用 OKX 公共行情时显示独立报价/K 线来源和最近完成 K 线，并在缓存超过阈值后从 `READY` 自动降为 `STALE`。控制台 0 error / 0 warning。只读 `POST /api/paper/arm` 返回 423，探针前后 SQLite 文件均为 0。

### 5. 增量前向观察看板

控制中心现在直接投影 observer、scheduler、完成 K 线水位和 ledger 审计，不再依靠日志或把服务在线解释成观察正常：

- `portfolio-forward-dashboard-v1` 分开报告 service、observer、data 与 schedule；
- 最新完成日线、最后已计入、待处理、本轮处理、安全跳过、下一次检查和暂停原因都有稳定字段；
- 缺失、旧版或哈希不一致的状态工件一律 `UNKNOWN / BLOCK`，未知计数显示 `--`；
- scheduler heartbeat 来自未来、过期窗口、候选错配、ledger/readiness/数据修订证据不完整都会失败关闭；
- `--dry-run` 在创建目录、锁、SQLite 和状态文件之前返回，真正做到预览零持久化；
- 前端复用控制中心单次请求和单次渲染，没有增加轮询或重新加载旧 K 线。

定向验证为 33/33 PASS（测试体 0.290 秒），相关 Python 与 JavaScript 语法通过。新只读页面刷新前后均显示“只读观察 · 模拟未授权 · 实盘永久硬锁”，控制台 0 error / 0 warning；HTTP 423 和空 SQLite 集合哈希不变。没有运行完整回归或旧 K 线重放。

## 下一轮功能优先级

### 已完成：行情真值中心

控制中心现在已按活动标的显示：

- 报价源与 K 线源；
- 最近完成 K 线时间、数据年龄和周期；
- `READY / STALE / UNKNOWN / BLOCK`，而不是仅凭服务在线显示 READY；
- 旧缓存、上一交易日兜底、离线种子和真实实时来源的区别；
- 下一步动作：等待市场、刷新、补历史、人工核验或阻断研究。

该功能不把 AAPL 的预览图或旧缓存冒充为可信实时数据，也不把服务进程在线冒充为行情 READY。后续只需随真实使用补充更多状态说明，不再为此重复跑整套历史 K 线。

### 已完成：增量前向观察仪表盘

控制中心已接入 `work_summary`、scheduler 和内容寻址证据，显示：

- 今日发现多少新完成 K 线；
- 实际处理多少、跳过多少、为什么跳过；
- 最近一次观察日期、目标组合变化、风险状态；
- 下一次预计检查时间；
- 历史审计重放继续只允许命令行显式 `--replay-recorded`，界面不提供误触入口。

缺证据时看板会显示 `UNKNOWN / --`，不会显示假 0；调度状态不是 PASS 或证据链不完整时会明确暂停。后续只根据真实自然前向使用反馈补字段，不再为看板重复跑旧行情。

### 已完成：股票刷新去重

股票快照降级、图表质量告警、研究质量告警、报价联动和 Futu 联动现在统一进入按 `symbol + bar + session` 隔离的刷新协调器：

- 同键在途请求共享同一个 Promise，自动与人工入口不会重复发起完整快照；
- 人工刷新可以绕过成功/失败冷却，但仍必须加入已有在途请求；
- 成功使用 60 秒冷却，失败使用有上限的指数退避，避免上游故障时请求风暴；
- 快速预览不能满足完整强刷；完整强刷启动时会中止同键尚未完成的快速预览请求；
- 不同标的、周期或盘段互不共享，旧上下文结果不能覆盖当前图表；
- 后端同样按规范化身份共享强刷代次，失败保留 last-good 并降级，不用离线种子覆盖最后可信报价；
- `force/emit` GET 增加本机与来源约束，例行前端刷新固定 `emit=false`。

这套机制分别吸收了 Freqtrade 的按交易对/周期水位与 TTL、Hummingbot 的共享限流上下文、CCXT 的单实例与共享 Future 思路，但没有照搬交易执行、连接器规模或自动重试下单。provider 级共享限流已于 2026-08-12 完成；50–100ms 微批仍只在真实使用出现压力后再评估，不提前堆复杂度。

### 已完成：公开多档卖盘成本观察

在一档卖一数量预览之上，新增了完全只读的 OKX 标准订单簿证据与逐档扫描：

- Hummingbot 的逐档取量和末档部分消耗被改写为精确十进制/分数计算，固定输出 10/20 USDT 的可见数量、档内均价、相对卖一差异、消耗档数和覆盖率；
- NautilusTrader 的订单簿完整性思路被收缩为当前阶段需要的标的、双边排序、非交叉、交易所时间和本地接收时间核对；
- CCXT 只作为 provider 边界参考，OKX 原始十进制文本、`ts` 和 `seqId` 继续保留，不用统一 float 结果冒充原始证据；
- Freqtrade 的深度失衡暂不进入规划状态或交易结论，避免把瞬时盘口比例误当方向信号。

当前服务固定观察前 20 档标准非 RPI 流动性，并按标的做内存缓存与同键合并。OKX REST books 没有连续消息证明或可用 checksum，因此 `complete_book_verified=false`；20 档不足时只输出可见容量、深度短缺与 `VISIBLE_DEPTH_CAPACITY_LIMITED`，并将 lot 向下取整余款单独列出，不补齐、不外推，也不把可见档均价差叫作预计滑点。该功能仍只通过原有控制中心 GET 展示，不生成订单方向、订单类型、数量参数或提交能力。

### 已完成：固定价格带盘口真值，静态深度不再冒充方向信号

在公开多档卖盘成本观察之上，新增了完全只读的双边微结构派生合同：

- 参考 Hummingbot 的价格边界逐档累加与 NautilusTrader 的完整性原语，从同一份已经验签的 OKX 标准订单簿计算；原始档位 Hash 与派生指标 Hash 分离。
- `public-order-book-microstructure-v2` 固定计算中价对称 5/10/25 bps 价格带。买卖两侧分别使用完整的已返回前缀，前端再用 BigInt 从原始十进制档位重算边界、筛选、基础币与报价币合计、逐侧覆盖和跨档单调性，不再把“相同档数占比”作为主展示。
- 最远可见档抵达边界时，该侧带内累计额在当前标准非 RPI 来源范围内得到覆盖证明；未抵达时只显示“已见/部分”，数值是可见下界。短页不自动视为完整，20 档也不自动视为覆盖；合法零档不会和未知混淆。
- 有效状态固定为 `OBSERVATION_ONLY`，显示文案固定包含“非信号”；完整深度、RPI、隐藏单、队列、撤单、成交概率与未来方向全部保持 `NOT_CHECKED`。
- 没有照搬 Freqtrade 以深度比例过滤入场的阈值，也没有把单张 20 档快照冒充订单流失衡。若未来研究方向性，必须另积累自然前向的增量事件序列并做逐标的样本外验证。
- 旧行情台的瞬时盘口/成交分布已经解除策略方向着色、冲突判断和信号说明，只保留中性观察；不会再同时出现“这里是非信号、那里又说买卖盘占优”的产品矛盾。

实现仍复用原控制中心 GET，不新增请求、路由、按钮、订单参数、模拟权限或实盘入口。小资金计划显式升级为 `small-capital-planning-v3`；定向验证为 15/15 PASS（0.053 秒），五个相关 Python 文件 AST 与 `app.js` 语法通过；未运行完整回归、旧 K 线重放或浏览器轮巡。

### P1：封存 selection 与 post-selection 的完整稳健性明细（已完成）

schema 5 首先引入 `strategy-research-selection-cell-evidence-v2`；schema 5/6/7 的既有 cell Hash 与验证语义保持不变，schema 8 保留 v3 cost-stress，schema 9 保留 v4 topology 合同，schema 10 引入 v5 selection replay，schema 11 新增完整 post-selection TEST/holdout direct replay，schema 12 增加标准 admission-v1。当前 writer 为 schema 13：继承上述能力并增加结构化 hypothesis-v2/admission-v2。formal 的 alignment、边界、训练/验证/测试、基准、压力成本、固定切片与前视证据均由冻结输入重建；admission 再决定是否允许进入 TEST。schema 6–13 都绑定 `implementation-manifest-v2`；schema 7–12 绑定 hypothesis-v1，schema 13 单独绑定 hypothesis-v2。合成 fixture 覆盖成本、拓扑、主验证/基准/前视、完整 digest、TEST/holdout 999 与边界重封、alignment/row skew、权限别名、no-candidate、机制谓词触发/无法解析、admission BLOCK 零受保护阶段以及 schema 3–12 兼容；没有重跑旧 K 线或启动正式盲测。

### P2：逐步拆分大服务（冻结包与回测预览切片已补齐）

`server.py` 已超过一万行。不要一次性重构；每次新增功能时，把对应路由和快照构建器移到独立模块。优先顺序：

1. 控制中心最终 JSON 与行情健康权限包络已移入纯 `services/platform_control_center.py`；服务调用、缓存、数据库和只读回退仍留在 `server.py`，纯内存合同锁住权限、双行情真值入口与订单白名单；本轮又对 `paper/risk/executor/data_health/forward/small-capital/recent_audit` 组件递归中和嵌套权限字段，组件不能把 `paper_authorized/live_order_allowed/execution_allowed` 重封为公开授权；
2. 自然前向最终权限包络与 dashboard 组装已移入 `services/portfolio_forward_projection.py`；文件/数据库读取、候选注册、Hash 校验、scheduler 和回退仍留在 `server.py`；
3. 研究上下文与摘要的最终组装已移入 `services/research_query_projection.py`；查询、数据库、缓存、权限判断和回退仍留在 `server.py`，根权限固定为只读且禁止实盘；
4. internal-backtest pack 的固定 pointer、`return_quality` 与 v3 自然前向晋级摘要读取进入独立 `services/portfolio_backtest_pack_pointer.py`；它只读取明确指针及单个绑定 pack，不能 glob、重建证据、重载数据库或重跑 K 线；
5. `/api/strategy/backtest/preview` 的最终 deepcopy、权限中和与错误合同进入纯 `services/strategy_backtest_projection.py`；行情、回测、成本和时间切片仍留在 `server.py`；
6. 冻结收益质量证据带补充已验证冻结时间与 pack/evidence Hash 指纹；策略预检、体检生命周期与研究证据路径改为中性描述，底层 PASS/READY 只保留元数据，不用颜色暗示授权，也不把预检写成模拟自动化就绪；
7. 策略研究室继续收敛为描述性证据表面：信号列表、作战室锚点、条件解释、矩阵、时间线、候选策略和并行比较不再把 BUY/SELL、PASS/READY 或评分涨跌色当作执行提示；命令条也改为研究状态、只读模拟参数和风控证据。展示改用研究假设、观察区间和未校准模型估计，原始值只留在元数据。
8. `/api/strategy/war-room` 的最终 JSON 进入纯 `services/strategy_war_room_projection.py`；它不移动行情或策略计算，只把模拟/执行语义、READY 和 OWNER 角色降为描述性研究复核，递归固定 paper/live/execution false，并为观察阶梯标记 `planning_only`。这一步先于兼容路由，保持 UI 和只读 API 的同一安全合同。
9. `/api/strategy/doctor` 与 preview 的最终 JSON 进入纯 `services/strategy_doctor_projection.py`；体检与 pipeline 记录仍原位，只把 `paper_ready`、生命周期和 callback 状态转换为描述性研究状态，保留 raw 元数据而不授予权限。
10. `/api/strategy/lab` 的最终 JSON 进入纯 `services/strategy_lab_projection.py`；开发期仓位/目标区/失效区/启发式评分只进入 `planning_candidate`，旧操作字段置空，前端仅允许复制到研究表单，不选参、不授权。该即时响应仍以 `strategy-lab-evidence-boundary-v1` 声明自己没有冻结稳健性证据；另由 `services/strategy_research_pointer.py` 为独立 `/api/strategy/research-evidence` 提供固定指针、公共 verifier 与白名单投影。两条来源只在前端分层呈现，行情读取和环境计算仍留在 `server.py`，GET 不扫描报告或运行回测。
11. `/api/strategy/compare` 的最终 JSON 进入纯 `services/strategy_compare_projection.py`；动作与条件只保留研究解释，评分/概率标记为未校准开发期启发式，递归权限固定为 false。
12. `/api/bot/center`、`/api/bot/scheduler`、调度变更结果与 `/api/strategy/robot-profiles` 的最终 JSON 进入纯 `services/bot_research_projection.py`；OWNER/可执行/模拟 armed/推荐和分配比例只作 raw 元数据，公开字段改为研究角色、描述性状态、开发期分或 null，前端不再使用 OWNER/执行权/READY 语义或方向色。机器人计算、profile 持久化和既有规划变更仍在 `server.py`，该投影不生成订单。
13. `/api/strategy/analyze` 的最终 JSON 进入纯 `services/strategy_analysis_projection.py`；方向、TP/SL、建议价格和嵌套 risk config 只作为研究规划，价格值写入 `planning_*`，概率标记为未校准，图表锚点、侧栏和风险预检统一消费该规划语义，不显示为订单或授权。
14. `/api/ai/market/dual-analysis` 的最终 JSON 进入纯 `services/market_ai_projection.py`；DeepSeek/GPT 多空方向、胜率、支撑压力和 TP/SL 只作未校准研究观察，原始模型回执保留，行情 AI 卡片使用中性标签，不把模型回答当作收益证明或执行授权。
15. `/api/ai/deepseek/analyze`、`opportunities` 与 `platform-review` 的最终 JSON 进入纯 `services/deepseek_projection.py`；方向、置信度、机会价位、仓位提示和 actionability 只作未校准研究观察，价位进入 `planning_*`，原始值保留为 raw 元数据，旧研究卡片改为中性标签。
16. `/api/ai/trading-agents/discuss` 的最终 JSON 与 NDJSON 事件进入纯 `services/trading_agents_projection.py`；多空/WAIT 决策映射为 `RESEARCH_*`，置信度/胜率保留 raw 但标记未校准，TP/SL 只进入 `planning_*`，递归权限固定关闭，会议室 UI 只显示研究纪要与非订单规划。
17. `<=480px` 窄屏进入单列信息架构：侧栏变为顶部导航带，自选列表保留受限滚动，研究视图不再继承桌面最小列；只改静态布局和资源指纹，静态合同通过后仍需真实设备/浏览器验收。
18. 最后才处理兼容路由；任何新路由都必须先确定固定来源、Hash/语义验证和失败关闭合同，再做 UI 消费。
19. `/api/research/panel` 已补上纯 `services/research_panel_projection.py`：研究卡片的 tone、方向/偏好、已核对状态和 BUY/SELL 类动作不再直接作为可见执行语义，嵌套权限字段递归归零；扫描、行情、新闻和股票研究 I/O 仍留在 `server.py`。
20. 交互回测风险控制网格的唯一拓扑与描述投影进入纯 `services/backtest_risk_control_surface.py`；`server.py` 只按该冻结轴运行既有 100 个开发组合并接线结果，模块本身不做行情 I/O、回测、选参或权限判断。前端独立复算全部单元，避免摘要字段成为新的信任捷径。
21. 冻结研究报告的时间事实进入纯 `services/strategy_research_currentness_facts.py`；server 只注入观察毫秒，pointer 只传已验证报告字段。该模块不读系统时钟、不定义新鲜度阈值、不把 UTC 日历日当交易日，前端按同一公式重算，异常或重封时失败关闭。
22. internal pack v3 的公开晋级摘要固定为 `portfolio-backtest-forward-promotion-summary-v1`，只白名单投影双成熟门槛、audit/readiness、通用 blocker、验证范围和 Hash；v2 返回 `null`。前端用中性成熟度审计脊柱同时呈现前向子证据与整体 pack 状态，禁止把子证据的人工复核资格翻译成整体 READY、盈利证明或执行权限。

### 独立准备阶段：100–200 美元小资金规划

当前项目不应直接增加实盘适配器。先做只读的 `PLAN_ONLY_NO_EXECUTION` 准备清单，至少证明：

- 独立子账户和绝对美元上限；
- 只允许现货、1 倍、白名单标的；
- 持久熔断、人工复位和冷静期；
- 交易所 `tickSz / lotSz / minSz`、手续费、滑点、深度、部分成交和延迟预演；
- 签名进程与 AI、研究服务隔离；
- API key 权限和 IP 白名单证据；
- 订单提交后的对账与未知响应处理。

OKX 官方文档明确区分 Read、Trade、Withdraw 权限，建议绑定 IP，并公开交易品种的 tick、lot 和 minimum size；这些必须成为以后试验的输入合同，而不是临下单时再猜：[OKX API v5](https://www.okx.com/docs-v5/)。在该独立阶段全部完成并经用户再次明确授权前，现有实盘硬锁保持不变。

状态更新：纯规划切片已接入交易总控，资金示例护栏、证据缺口和永久无执行权限均可见；当前状态为 `NEEDS_EVIDENCE`。公开规则服务已经通过 OKX `SPOT instruments` 核对并哈希绑定 BTC-USDT 的 `tickSz / lotSz / minSz`，按标的做短期内存缓存，且不会把股票套用加密规则。`minSz` 只解释为基础币最小数量；最小报价币成本仍未知。

其后又接入了不生成订单的数量预览：只使用服务端同一内存快照中的公开卖一价与一档卖一量，保留原始十进制文本，固定 10/20 USDT 两档，并用整数比值精确决定 `lotSz` 步数、向下截断后估算是否达到公开 `minSz`；客户端传入的 price 与最新成交价都不参与数量计算。OKX ticker 时间倒退、卖一缺失或买卖价倒挂会失败关闭，且一档卖一量明确不能替代完整订单簿。[OKX ticker](https://www.okx.com/docs-v5/en/#order-book-trading-market-data-get-ticker) 只提供公开参考，不是可执行报价。

界面同时显示 5% 市价单风险检查临时冻结的规划备付参考：10/20 USDT 对应需临时备付 10.5/21 USDT，但它不表示账户余额已经核验，也不是手续费、滑点、实际支出或成交保证。该预览最高只叫 `PREVIEW_ONLY`，USD/USDT 换算、完整深度、最终成交价、账户余额、账户费率和最小成交金额仍未知，也不生成 side、订单类型或 OKX `tgtCcy` 参数。这里仅迁移 [CCXT amount precision](https://github.com/ccxt/ccxt/blob/master/python/ccxt/base/exchange.py#L5988-L6008) 的向下数量格式化思路；风险冻结与 `tgtCcy` 语义仍以 [OKX Place order](https://www.okx.com/docs-v5/en/#order-book-trading-trade-post-place-order) 为准，因此本预览不冒充订单构造器。

账户实际手续费继续固定为 `NOT_CHECKED`：OKX 的费率接口是私有、账户和等级特定的 Read 请求，不能拿公开默认值或回测费率冒充。该切片没有签名器、私有 API、充值或订单入口，也不把规划完成解释为可交易。后续只补真实缺失证据，不为显示通过而猜测手续费、最小订单成本或账户权限。规则语义参考 [OKX Get instruments](https://www.okx.com/docs-v5/en/#public-data-rest-api-get-instruments)、[OKX Get fee rates](https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-fee-rates) 与 [CCXT precision and limits](https://github.com/ccxt/ccxt/wiki/manual#precision-and-limits)。

## 停止继续做的事情

- 不重复运行已经否定的 G50/G51 假设。
- 不把完整 750 项回归当作每个小改动的默认动作。
- 不为积累测试数量添加低价值重复测试。
- 不因为 K 线非空就宣称数据 READY。
- 不在当前 server 中提前埋真实下单入口。
- 不追求竞品的连接器数量、策略数量或企业级架构体量。

## 轻测试规则

- 小功能：只跑改动模块的单测与语法检查，目标几十项、数秒完成。
- 跨模块合同：运行对应 lean profile。
- 新冻结基线、风险核心变更或准备正式发布：才运行完整回归。
- 新市场证据优先来自自然前向完成 K 线，不用重复旧 K 线制造“更多验证”。
- 任何定向 PASS 都必须明确标注范围，不能冒充全量 PASS。

## 推荐执行顺序

1. selection cell 的版本化完整稳健性证据封存已经完成；schema 3/4 历史兼容继续冻结，不为增加测试数量而重复旧 K 线。
2. G42 到期统计与 readiness v2 合同已经实现；现在只自然积累新完成交易日证据，到期后由 runner 从验证通过的 settlement 链复算，不能用开发期审计或聚合收益替代。
3. 行情 provider 级共享限流与完成 K 线水位已经完成；微批只在真实压力证据出现后评估。
4. 只读小资金清单、公开现货规则、卖一数量与多档可见成本观察已经完成；只在用户准备独立试验环境时核对账户费率、最小成本、子账户与隔离控制的真实证据，仍不接实盘执行。
5. 控制中心、自然前向和研究查询三个纯投影已经完成；以后只在真实功能经过大服务时继续拆窄切片，不做一次性重构。自然前向若将来通过统计门槛，internal pack 的接入必须使用新 schema 与独立 verifier。

正式盲测、模拟授权和实盘真实下单均不属于本路线当前阶段。
