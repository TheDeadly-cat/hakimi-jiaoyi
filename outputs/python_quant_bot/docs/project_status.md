# 哈基米交易 v2 项目状态
更新时间：2026-08-14

## 2026-08-14 首次共同成熟单次裁决、公开证据与项目读取边界

- 当前生产链已统一为 `portfolio-forward-statistical-audit-v2 / portfolio-forward-readiness-v3 → portfolio-forward-statistical-maturity-v3 / portfolio-forward-dashboard-v7 → portfolio-internal-backtest-pack-v6 / portfolio-backtest-return-quality-snapshot-v4`。dashboard v6/maturity-v2、audit-v1/readiness-v2 与 pack-v5 继续保留冻结历史验证语义，但不能冒充 current。四个公开成熟状态仍是 `NOT_DUE / REVIEW_REQUIRED / STOP_RESEARCH / BLOCK`，始终只属于研究证据。
- audit-v2 从完整、逐行语义复算通过的 settlement 链定位“结果门槛与实际调仓门槛首次同时满足”的最短 prefix（当前候选门槛为 60/8）。paired bootstrap、首次到期风险验收与最大回撤上限只在这一 prefix 上运行一次；prefix、stage、risk 与 decision Hash 随之冻结。后续 tail 仍接受完整链与权限完整性核验，但统计上只累计描述，不能让首次 BLOCK 在 66 等更长样本上恢复，也不能让首次 PASS 因后来 tail 恶化而被可选停止改判。
- 首次 prefix 同时冻结风险验收：最大回撤必须严格低于候选预注册上限，等于上限仍 BLOCK；`risk_hash` 与 `decision_hash` 共同进入 maturity-v3、forward-evidence-v2 与公开摘要绑定。bootstrap 在任何循环前执行预算门禁：`resample_count` 必须是 100..50,000 的原生整数，`block_length` 必须是 1..1,024 的原生整数且不超过 prefix 样本量；超预算、非有限或伪整数配置在 stage 前失败关闭。
- maturity-v3 从 performance 内嵌完整序列重建首次共同成熟 prefix、风险收据和冻结裁决，再与 persisted readiness-v3 逐值对照；当前 scope 为 `PERSISTED_READINESS_V3_AND_FIRST_JOINT_MATURITY_DECISION_REBUILT_FROM_EMBEDDED_FULL_SERIES_NO_SETTLEMENT_REPLAY`。它仍不回到 settlement SQLite 重放。现有 `portfolio-forward-local-source-anchor-v1`、archive-v3、backup-status-v2 与 watchdog-v3 账本不变；maturity-v3 继续重算 `FULL / PREFIX / CONTRADICTION / NOT_AVAILABLE`，覆盖结论不提升统计状态。
- report-root 当前 writer 为 pack-v6/forward-evidence-v2，固定 pointer 仍是字段与 Hash 合同不变的 `portfolio-backtest-pack-pointer-v2`；只有下一次显式成功运行 writer 才会发布新 pointer，本轮没有自动重发或迁移现有 pointer。historical pack-v5 bundle 仍可按历史 verifier 自洽通过，但经 pointer-v2 的当前公开读取必须返回 snapshot-v4 `UNKNOWN`，`return_quality` 与 `forward_promotion` 均为 `null`。
- 项目读取边界新增共享 `services/forward_artifact_io.py`：active candidate、active research source、performance runner 与 watchdog 共用 bounded/no-link-or-reparse/strict-object JSON、Windows basename、内存/递归失败收敛和路径脱敏。control/registry/receipt 为 256 KiB，compact candidate 为 1 MiB，pack/invalidation 为 32 MiB，observer/performance/statistical status 为 16 MiB，research/robustness 沿用已有 256 MiB producer ceiling；已删除 shadow runner 未使用的普通 JSON reader。未验证的旧 backup/watchdog receipt 也不能再以相同 condition hash 抑制新的真实告警。
- 前端资源指纹已推进到 `20260814-single-look-contract-1`。`<=480px` 使用原生 `details/summary`“市场选择”披露：默认收起搜索、分类与市场按钮，同时保留当前标的/类型；展开后恢复完整控件，桌面与 720px 保持宽屏源码合同。一次真实 480px 渲染核验中，收起时主内容顶部约 y=180、可见市场按钮 0 个；展开时约 y=455、市场按钮 46 个。后续浏览器策略阻止了 720px 键盘交互步骤，因此 720px/desktop 只声明静态/源码合同，不冒充完整浏览器或真实设备 QA。
- 根任务 current 激活合并定向为 161/161 PASS，覆盖 single-look、maturity/projection/server、pack/pointer 与 lean 合同；Node 完整 evidence 合同 PASS，三项 `node --check` PASS。项目读取边界为 109 项通过、2 项宿主 symlink 能力跳过；256 KiB 修正后 `portfolio_forward` 16/16；独立终审矩阵 139 项通过、4 项宿主 symlink 能力跳过。这些集合重叠，不能相加冒充全量回归。
- 本轮没有重跑旧 K 线、G50/G51、正式盲测或 lean fresh，没有启动产品服务、计划任务或其他正式 runtime 作业，没有读取真实收益来生成新数字，也没有产生盈利证明、paper 授权或 live 权限。一个 agent 的范围过宽只读检索曾误匹配到 runtime 备份中的源码行；这些行没有用于结论，runtime/备份没有发生任何变更。

> 当前静态指纹以上述 `20260814-single-look-contract-1` 为准；下文历史切片继续保留其当时事实，但其中“当前缓存身份”均按顶部指纹解释。

## 2026-08-14 schema 14 正式研究全局搜索谱系门禁
- development writer 继续固定为 schema 13；formal preregistration/runner 已显式升级为 report schema 14、hypothesis-v3 与 `strategy-research-search-lineage-v1`。正式选择前必须使用 active runtime 根下唯一 canonical registry，由 Store 在同一事务内重建全部 REGISTERED nested-research 协议的全局 trial ledger、claim anchor 与 live audit；更换 `search_family_id` 或新建 generation 不能把累计搜索次数清零。正式 validation ranking 使用 `cumulative_trial_count` 做多重试验惩罚，不再使用本批 `len(variants)`。
- public admission-v3 只检查离线报告/预注册回执自洽，固定 `live_registry_verified=false` 且不能放行；只有 store-owned live gate 才能形成 formal admission。canonical registry 路径、claim/tail/event、lineage 或累计计数漂移均在首次 selection 数据读取前 BLOCK；admission BLOCK 时冻结候选、TEST、confirmation、holdout 与 forward candidate 全为空。离线 report verifier 只声明 `OFFLINE_REPORT_AND_PREREGISTRATION_RECEIPT_CONSISTENCY_ONLY`，不冒充当前数据库真实性。
- 固定 `strategy-research-report-pointer-v1`、publication expectation v1 与 receipt v1 字段集没有扩张。公共能力表现在精确分派 report 3–10→v3、11/12→v5、13→v6、14→`strategy-lab-frozen-evidence-v7`，15+ 失败关闭。v7 强制 hypothesis-summary-v3、admission-v3、post-selection replay-v1、failure-conditions-v4 与脱敏 search-lineage-v1；仅选择时 live 绑定可公开 `BOUND`，receipt-only 降为 UNKNOWN，未命中策略使用空的 `NOT_IN_REPORT` 隔离视图。公开层不返回 family 值、注册 ID、候选 ID、路径或 protocol/claim/anchor/lineage Hash。
- 前端在事前假设之后增加“检索谱系”账线，只显示全局 prior/current/cumulative 计数、选择时绑定与当前离线复核边界；`prior + current = cumulative`、安全整数与 BOUND/NOT_IN_REPORT 结构均由客户端重算。文案明确“选择时核验；当前仅离线报告/回执自洽”，不声称当前 live DB、盈利、选参授权、模拟授权或实盘权限。视觉沿用中性细线与 mono，无新卡片、状态色、动效、请求、轮询或 live region；当前资源指纹为 `20260814-single-look-contract-1`。

- schema 13 仍是 development 当前版本，并保留 `strategy-hypothesis-preregistration-v2` 与 `strategy-preregistered-failure-admission-v2` 的结构化机制条件合同；schema 14 formal 在此基础上增加 hypothesis-v3/search-lineage/admission-v3，不追溯改变 schema 3–13 的 Hash 或 verifier 语义。结构化条件的 metric 仍只来自 verifier 重算的 selection ranking、成本压力与固定参数折叠证据，operator 仅允许 `LT/LTE/GT/GTE`，阶段与动作固定为 `DEVELOPMENT_SELECTION / BLOCK_RESEARCH`。
- admission-v2 先完整复用三条标准开发门禁，再逐一复算实际候选的结构化机制条件。缺失、重复、非法字段、非有限阈值、无可复算值或谓词触发都会令整个 `HYPOTHESIS_BATCH` BLOCK，并清空 admitted/frozen candidates；formal 不运行冻结 TEST、不加载 confirmation，也不会生成 holdout 或 forward candidate。未进入候选的策略只把候选相关机制条件标为 `NOT_APPLICABLE`；新鲜单次留出与自然前向两条后续条件固定为 `NOT_DUE`，明确表示开发期尚未裁决，绝不等于 PASS。
- 前端精确接受 report 3–10/v3、11–12/v5、13/v6、14/v7；v4、跨版本组合、report15、伪 live binding、receipt-only、计数越界、机制谓词漂移、future `NOT_DUE` 伪装 PASS、权限别名与 `NOT_IN_REPORT` 借证均失败关闭。合法 v6/v7 `MATCHED` 才生成冻结机制判据，v7 另显示脱敏检索谱系；历史 TEST/holdout 仍明确“非自然前向、非盈利证明”。
- 定向证据包括 schema14 CLI 16/16、lineage/admission/protocol 26/26、runner 35/35、相关 companion 68/68、公共 pointer/failure/replay 50/50 与独立扩展审计 71/71；root 另复跑核心 4 项与 public 5 项。watchdog/authority/lean 合同交叉 22/22，完整 Node 合同及三项 JavaScript 语法检查通过。测试集合存在重叠，不相加冒充总回归；全部使用合成、Mock、临时目录或受控源码，没有读取真实 runtime/数据库/缓存/日志，没有运行旧 K 线、G50/G51、正式盲测或 lean fresh，也未做浏览器/真实设备 QA。
- 本地来源锚已按上述 verifier-only 方案落地，但信任边界没有扩大：同机同权限写者仍能协调重封数据库、归档、backup 与 watchdog；同时删除两份新收据也只能降级为 `NOT_AVAILABLE`，本地无外部单调状态可证明其曾存在。真正外部锚仍需要独立签名信任根与外部 append-only/WORM/timestamp 收据；即使未来具备，也不证明行情正确、经纪商真实成交或未来盈利。

## 2026-08-14 strategy research pointer 发布绑定与策略证据巡检

- `strategy-research-report-pointer-v1` 的字节字段合同保持不变，但 publisher 不再只验证“当前磁盘报告与它刚生成的 pointer 自洽”。runner 先从本次内存 report 和确定性最终 JSON bytes 构造 `strategy-research-pointer-publication-expectation-v1`，封存 report basename、完整内容 Hash、文件 SHA/长度、report schema、batch spec/dataset manifest/batch run Hash、governance 状态与时间；publisher 读取落盘 report 后必须逐值匹配该 expectation，才能写固定 pointer。
- pointer 发布采用 UUID 临时文件、`fsync` 与原子替换，随后同时重读 pointer 与 report，核对精确 bytes、JSON、expectation binding 与完整 pointer verifier。返回的发布回执包含 expectation/report/file/batch 绑定和双重 post-read 标志；formal 完成、RUNNING prepared 恢复、COMPLETED 缺 final 恢复与 development 路径都由同一 helper 按内存 report 重建 expectation，并逐值验证回执，不能再只相信 `published=true`。伪造已发布回执、发布间替换、指针或报告回读漂移、异常与路径别名都会失败关闭，错误响应不暴露本地路径。
- 输出 basename 现在按 Windows 语义做 NFKC、大小写、尾点/尾空格、ADS/非法字符与设备名规范化，在任何发布前阻断固定 pointer 槽的等价别名；pointer 与 report 的深层执行权限字段改用共享 canonical scanner，大小写、下划线、短横线与驼峰别名都不能绕过。该边界减少误发布和 TOCTOU 成功误报，但不是跨文件事务或外部签名：具备同目录写权限的主体仍可在最后一次回读之后再次替换文件，公开 loader 会在下一次读取时按 pointer SHA/语义退回 UNKNOWN，不能把本地 Hash 称为不可篡改真实性。
- 项目整理继续把 `market_anomaly_projection`、`market_scanner_projection` 与 `strategy_war_room_projection` 的三套私有权限字段表/递归器迁移到共享 `sanitize_authority_claims` + `authority_violations`。输出后置条件若仍发现权限真值，直接返回固定研究安全空壳，不回显原始字段、私有内容或路径；`raw_*` 与 `source_authority` 等非权限审计事实保持原语义。`configuration_projection` 因另有专用 `configuration_apply_authorized` 合同暂不机械迁移。
- 独立 `backtest_return_quality` builder 也移除旧式精确键权限扫描，复用同一 canonical `authority_violations`。`Paper_Authorized`、`canTrade`、`parameter-selection-authority` 等别名即使藏在 Mapping/tuple 中，也不能在绕开外层 pack 时被误写成 `AVAILABLE`；收益计算、quality v1/v2/v3 与 pack v2/v3/v4/v5 各自的版本合同不被跨版本混用。quality + pack + pointer 定向交叉通过。
- `run_internal_execution_rehearsal.py` 与 `run_internal_portfolio_statistical_audit.py` 不再各自原始读取活动登记后用 `glob` 猜同批研究报告。新增共享 `portfolio_active_research_source`，先复用 canonical active-candidate loader 核验登记 Hash、激活时钟、候选/稳健性/完成收据与零权限，再只读取 completion receipt 指定的同目录 basename；同一次 bytes 读取重核 SHA、UTF-8/JSON object、receipt/candidate/report batch identity 与 registry/candidate/receipt/report frozen candidate identity。默认来源 BLOCK 时两个 runner 都在证据展开、演练和统计前退出 2；显式人工 `--research-report` 分支保持原合同。定向 11/11、lean 6/6 与五文件语法检查通过。
- 策略实验室证据区把“源 / 稳 / 止”从装饰性分栏收敛成可导航巡检路径：三段使用真实 `h3` 与 `aria-labelledby`，不再为非交互 section 制造键盘停靠点；“稳”保持“完整性与稳健性”，“止”作为最关键审阅栏在桌面加宽，并以语义化 `dl/dt/dd` 呈现判据账页。`<=720px` 起按源→稳→止单列，判据行仍保持 label/value 扫读；`<=480px` 再把判据行与段内字段单列。视觉只用既有 mono 与中性细线，不新增卡片、圆角、渐变、状态色、动画、请求、轮询或 live region。该历史切片当时只有静态合同；本轮新增的 480px 浏览器证据见顶部，720px/desktop 仍不冒充完整交互 QA。当前静态资源指纹为 `20260814-single-look-contract-1`。
- 定向验证：pointer 全类与五条 runner 发布边界共 27/27，覆盖伪 `pointer_hash` 回执、发布失败、错误脱敏以及 formal/development 嵌套输出的零 Store/claim/hypothesis/build/data-load 前置阻断；formal 完成及 RUNNING/COMPLETED 恢复各自通过。三项公共 projection 与共享权限合同 23/23；前端证据合同和三个 JavaScript 语法检查通过，相关 Python 语法检查通过。验证只使用合成、Mock、临时目录和受控源码；未读取真实 runtime、数据库、缓存、日志或固定 pointer，未启动服务/浏览器，也未运行旧 K 线、G50/G51 或正式盲测。
- 冻结收益质量区新增首位“下一条可信证据”账签。未核验状态只按本地可复算合同事实归类为安全边界、冻结来源、版本绑定、阶段证据、派生一致性或自然前向证据；已核验的 `failure_conditions` 只按四个白名单槽位计数生成固定类别文案，不回显原始 blocker、路径、候选身份、完整 Hash 或收益字符串。阶段名、阶段状态、统计状态、基准依据和 evidence stage 也改为枚举验证与固定本地文案，不能再经正文、dataset 或 title 回显；`可下单/已授权/实盘授权` 等中文权限键与英文 canonical alias 同样优先降为安全边界。已观察到的有效负结果明确写为“停止晋级”，不会被伪装成待补数据。fallback 已补齐 forward/schema/source-mode/cue 全字段；界面无新增请求、live region、卡片或分类状态色。该切片通过三个 Node 合同与相关语法检查，但未做浏览器或真实设备渲染 QA。

## 2026-08-14 schema 11–14 冻结后历史复算公开摘要

- 新增纯 `strategy-post-selection-replay-summary-v1`，只对明确具备直接复算能力的 schema 11–14 生效，并只聚合当前所选策略。它把冻结 TEST 与单次历史留出分别投影为候选数、结果/单元覆盖、复算完整单元数、正式聚合结果数、最低配置收益、最低基准超额、压力后最低收益、最差最大回撤和总交易数；公开层不返回 symbol、variant、params、候选 ID、源码路径或原始 blocker。容器类型、身份、覆盖或 replay 完整性异常时状态 BLOCK 且数值全部退回 `null`；完整性成立但收益/压力/正式聚合 outcome 失败时保留有限负数，避免把真实负结果伪装成缺失。
- 公开摘要的 PASS 是更严格的“post-selection replay preservation”诊断：要求所选策略全部内层 replay 与对应正式聚合均保持；正式跨标的聚合自身仍可按冻结合同容忍有限单元 outcome BLOCK。该摘要不回写正式候选门、不改变 report verifier 结论，也不把历史留出改名为自然前向。`FROZEN_TEST_ONCE` 只叫“冻结 TEST · 历史重放”，`HOLDOUT_CONFIRMATION` 只叫“单次历史留出 · 非自然前向”；两者都固定 `historical_backtest_only=true`、`natural_forward_performance_proven=false`，不是 WFO 或盈利证明。
- 公开版本门改为精确能力映射：report schema 3–10 使用 `strategy-lab-frozen-evidence-v3` 且不得携 post-selection/admission；schema 11/12 使用 `strategy-lab-frozen-evidence-v5` 且必须携 post-selection summary，schema 11 不得携 admission，schema 12 还必须携 admission-v1；schema 13 使用 v6 并强制 hypothesis-v2、admission-v2 与 failure-v3。`strategy-lab-frozen-evidence-v4` 仅保留后端常量兼容，不再由当前投影生成，前端也拒绝 v4/schema12 以及任何跨版本删证据降级组合；固定 pointer artifact 仍是字段不变的 v1。
- schema 11/12 的失效条件使用 `strategy-research-failure-conditions-v2`，在历史五项基础上增加“冻结 TEST 复算未保持”和“单次历史留出复算未保持”；schema 13 使用 v3，再把结构化机制触发、无法复算与未来 `NOT_DUE` 分别映射到 observed 或 evidence gap。schema 3–10 继续使用五项 v1，历史语义不追溯改变。
- 前端在策略实验室“稳”区的研究覆盖之后加入中性“冻结后历史复算 · 非自然前向”组，再显示参数平台、成本压力与固定时间切片；“止”区依次显示事前门禁、开发期机制判据账页、未来 `NOT_DUE` 到期账页、当前失效、事前失效与永久权限边界。每条机制行显示谓词/阈值、观测、结果和后续研究边界；可见文案不显示 `PASS/READY`，不使用涨跌色、不新增请求/轮询/live region。当前静态资源指纹为 `20260814-single-look-contract-1`。该历史定向验证为 backend summary/failure/pointer 42/42、完整前端证据合同与三个 JavaScript 语法检查通过；全部基于合成、Mock 或临时输入，没有读取真实 pointer/runtime、没有重跑 K 线、G50/G51 或正式盲测，当时也没有浏览器渲染 QA，因此没有生成新的真实收益数字。

## 2026-08-14 schema 12 事前失效条件准入（历史阶段，已由 schema 13 取代）

- 该阶段策略研究 writer 曾推进到 schema 12，并新增纯 `strategy-preregistered-failure-admission-v1`。它继承 schema 11 的 selection、TEST 与 holdout 直接复算，不改变 schema 3–11 的结果 Hash 或 verifier 语义；只有 schema 12 的 `batch_run_hash` 才额外绑定完整 admission。当前新报告已由顶部 schema 13 取代，schema 12 仅保留历史验证兼容。
- admission 从已验证的 `strategy-hypothesis-preregistration-v1` 标准失效条件、冻结 batch spec、selection cells、重新聚合的 rankings/candidates 与 `strategy-parameter-plateau-v2` 复算 `DEVELOPMENT_SELECTION / BLOCK_RESEARCH`。参数平台对假设中的每个策略检查；成本盈亏线、固定参数时间切片及 selection-symbol 完整覆盖只检查实际 validation candidate。合法 top-1 批次不要求未入选策略产生候选，但任一策略缺少平台、或任一实际候选成本/切片失败，都会按 `HYPOTHESIS_BATCH` 整批 BLOCK。
- `validation_candidates` 始终保留为审计记录；formal 只有 admission 整批 PASS 才能复制 admitted candidate 到 `frozen_candidates`。BLOCK 是合法的研究负结果：`frozen_candidates/test_cells/test_results/holdout_cells/holdout_results/forward_candidates` 全空，TEST 不运行，confirmation payload 不加载。development 无论 admission 结果都保持 `frozen_candidates=[]`，不能接触受保护阶段。
- writer 与 verifier 使用同一纯 builder；即使攻击者修改 admission、重算 `admission_hash` 和外层 `batch_run_hash`，verifier 仍从冻结开发证据重建并阻断语义漂移。报告、admission 与公开投影继续固定 `profitability_proven/performance_claim_allowed/parameter_selection_allowed/automatic_paper_activation_allowed/paper_authorized/live_order_allowed=false`。
- 固定 report pointer 仍为 `strategy-research-report-pointer-v1`，字段与历史字节合同不扩张。schema 12 的 admission 作为历史 `strategy-lab-frozen-evidence-v5` 的必需白名单字段，与 post-selection summary、根状态及 evidence contract 一起校验；schema 13 的当前 v6 语义见顶部章节。
- 定向验证只使用纯内存、Mock、临时目录与受控源码：admission 6/6、pointer 14/14、runner 全类 29/29、protocol/CLI/roadmap 21/21、lean 合同 6/6 通过，并覆盖 schema 11 固定 Hash、schema 12 admission Hash 绑定、peak-only 整批阻断、两策略 top-1、非候选成本失败不误伤、状态自报篡改、legacy pointer-v1、schema 12 public v5、BLOCK 时零 TEST/零 confirmation load 与旧 schema 降级验证；相关 Python 语法检查通过。没有读取真实 runtime、数据库、缓存或日志，没有运行 K 线、G50/G51 或正式盲测。回测与合成 replay 仍不是未来盈利证明，也不产生模拟或实盘权限。

## 2026-08-14 schema 11 冻结 TEST/holdout 直接复算

- schema 11 阶段新增纯 `strategy-frozen-evaluation-replay-v1`；当前 schema 13 继续继承该能力。schema 11 继承 schema 10 的 selection-cell v5、固定三折 v2、selection replay 与 alignment-input 语义；schema 3–10 的 Hash 和 verifier 保持历史语义，不因本次升级追溯增强。development 仍只产 train/validation 选择证据，不能生成 frozen TEST、CONFIRMATION holdout 或候选冻结。
- `FROZEN_TEST_ONCE` 不再把 runner/server 包装器输出或 cell 自报数值当真值：verifier 从冻结 selection snapshot、重建后的 train/validation 边界、策略/variant/实现指纹、params/param Hash 与 risk，独立直接重放配置成本策略、买入持有基准和 severe 成本场景，并逐值核对稳定指标、完整 trade/equity digest、成本证据与 flat metrics。把收益/成交改成 999、改变 TEST 边界并同步重封 replay/cell/report Hash，仍会失败关闭；这只是历史冻结复算，不是盈利证明。
- `HOLDOUT_CONFIRMATION` 从冻结 `role=CONFIRMATION` rows、manifest 和 data policy 独立重跑 `daily-batch-alignment-v2`，与报告自报 alignment 逐值比对，再用冻结 split policy 显式重建 schedule 后直接重放 configured/benchmark/severe、validation/test temporal、完整 confirmation 数据集固定切片、prefix invariance 与 lookahead。schema 11 禁止 legacy/伪造 `source_run_hash`；无合格 TEST 候选时 alignment 与 schedule 必须保持精确 `NOT_RUN`，不能重封成 PASS。
- 这条证据证明的是本地冻结 artifact 内部的 alignment/replay 语义一致；它不构成外部数据提供商的加密真实性，也不能恢复 snapshot 落盘前、对齐前的完整来源历史。
- schema 11 verifier 在报告根部复用共享递归权限扫描器，大小写、下划线、短横线与驼峰别名都会规范化；`Paper_Authorized`、`canTrade`、`live-order-allowed` 和 `parameterSelectionAuthority` 的任何非原生 `false` 值，即使藏在 dict/list/tuple 并同步重封也会 BLOCK。该扫描不追溯改变 schema 3–10。共享 standalone replay-driver 镜像已同步，正式实盘硬锁和模拟未授权边界不变。
- 定向证据使用 `UNIT_TEST` 内存 rows、Mock 和临时目录：schema 11 合成 replay 7/7、共享权限合同 5/5、schema 10/protocol/development/no-candidate 交叉 9/9 通过；没有读取真实 runtime、数据库、缓存或日志，没有重跑旧 K 线、G50/G51 或正式盲测。回测结果仍只能解释为历史研究证据，不能推出未来收益、模拟授权或实盘权限。
- 当前静态资源指纹为 `20260814-single-look-contract-1`。冻结组合归属区新增默认折叠的完整归属 Hash 核对，只在严格映射通过后显示，不新增请求、live region、方向颜色或授权语义。`platform_control_center` 已迁移到共享 `sanitize_authority_claims`，canonical alias 覆盖 `Paper_Authorized`、`canTrade` 与 `live-order-allowed`，同时保留组件局部 `armed` 等既有合同。

## 2026-08-14 schema 10 selection replay、回测包发布与前向证据层级

- schema 10 首次同时封存 `strategy-fixed-chronological-slice-evidence-v2` 与 `strategy-selection-cell-replay-v1`；schema 11/12 继续继承该 selection 语义。formal verifier 先从完整冻结 snapshot 和 split policy 重建 train/validation 边界，只使用重建后的 selection prefix；随后按固定 3 折（每折至少 120 行）重放时间切片，并用同一纯因果内核重放训练段、配置成本验证段、买入持有基准、stress/severe 成本场景和前视/前缀不变性检查。数据身份、策略/variant/实现指纹、params/param Hash、risk、执行与信号引擎、startup/evaluation policy、稳定指标以及完整 trades/equity digest 均受语义复算约束；同步伪造主验证或成本收益为 999、基准与派生指标、摘要/结果/证据/cell Hash，或只改 digest、fold policy、边界，都会 BLOCK。development 报告先物理移除受保护 test 后缀；schema 10/11/12 再按 `development-selection-prefix-split-v1 / TRAIN_VALIDATION_ONLY_INDEX_SPLIT_V1`，在冻结的截断 train+validation prefix 内对每个标的计算 `train_end_index=floor(N × train_ratio/(train_ratio+validation_ratio))`，并由 verifier 根据 batch split policy 重建、逐值比对。这个边界只在开发域内可复算，不等价于 formal 从完整 snapshot 重建的共同日历边界，不提供新鲜样本外或 WFO 证据，也不能冻结候选。schema 9 的 v1 保留历史拓扑/类型/汇总自洽语义。参数仍未逐折重拟合；selection replay 只是固定参数历史选择结果的语义复算，不校正选择偏差，因此它不是 WFO，也不是盈利或交易授权证明。
- internal-backtest 的 report-root 当前写入使用内容寻址的不可变 flat bundle：exact pack、research、statistical 三个成员各一次，经通用 immutable manifest/publisher 以确定性 JSON、UUID 临时文件、`fsync` 与 hardlink no-clobber 发布；`portfolio-backtest-pack-pointer-v2` 继续占用原固定文件名。runner 逐值复核 bundle/pack/evidence/candidate Hash、成员 SHA/长度与状态；发布间替换、临时别名清理失败、路径规划异常、畸形 JSON shape 或大小写/下划线/驼峰权限别名都会失败关闭。显式外部 `--output` 仅生成不可变的 legacy v4 离线导出、不更新 pointer；任何 report-root 内或其后代路径在 build 前即阻断。
- 自然前向区新增独立的“下一条尚缺证据”白名单投影，只从已验证的六类状态生成中性中文；上游 `next_action`、暂停原因或 READY/下单类动态文本不会进入可见主层级。最近已验证观察与收据移到末位按需展开，区域只保留一个 live status，窄屏改为纵向分隔。行情真值中心也把首位缺口改为 READY/STALE/BLOCK/UNKNOWN 白名单，不显示后端动态 `next_action`；标的、报价源、K 线源、新鲜度和最后完成 K 线回到事实台账。静态资源指纹现统一为 `20260814-single-look-contract-1`；该历史切片当时没有启动 HTTP、浏览器或设备渲染验收。
- schema 10 另携带自带 `input_hash` 的 `strategy-selection-alignment-input-v1` 对齐输入快照；它只封存日期/完成态投影，并固定 `role=SELECTION`、symbol/market/timeframe/source 与对应 SELECTION manifest Hash。verifier 不采信报告自报的 alignment PASS/BLOCK，而是根据该快照和冻结 data policy 重跑 `daily-batch-alignment-v2`，再决定 datasets、cells 与 rankings 的应有覆盖。把真实 PASS 改成 BLOCK 后删空结果、删除/改 role、漂移 source 或删 dataset 都会失败关闭。当前 writer 更严格：alignment 或 selection admission 非 PASS 时只输出结构化、脱敏的失败收据，不生成可验证研究报告、不完成 formal registry、不发布 pointer；这不是 valid-negative 完整报告、研究成功、盈利证明或权限升级。若未来需要持久化 FAILED 终态，须另建外部锚定 receipt，不能放宽当前 verifier。
- 当前 schema 10 定向验证覆盖 fold 与完整 selection replay happy path、runner 不调用 server 回测包装、主验证/成本 999 一致重封、训练/基准/前视与 trades/equity digest 篡改、formal 日历边界重建、development 索引边界重建及一致重封篡改阻断、alignment PASS→BLOCK 删空证据/role/source/dataset 漂移、alignment BLOCK 不写报告或 pointer、非 USDT 加密标的分类、schema 9 历史语义及 development report 集成。数据与工件输入使用合成内存、Mock 或临时目录；静态/清单检查读取当前受控源码，未使用真实 runtime、数据库、缓存或日志作为结论输入。没有重跑旧 K 线、G50/G51 或正式盲测，也没有把本轮合成回放数值记录成收益结论。回测收益仍只可解释为历史/开发证据，不构成盈利证明、模拟授权或实盘权限。
- pack 核心 verifier 的递归权限扫描现与 pointer 边界使用同一字段规范化：键名先做大小写折叠并移除非字母数字字符，再匹配当前显式列举的权限字段集合。`Paper_Authorized`、`CAN_TRADE`、`paperAuthorized` 以及 dict/list/tuple 深层别名即使同步重封 pack/evidence Hash，v2/v3/v4/v5 也都会 BLOCK；合法历史包仍按原版本合同通过。这只收敛安全口径，不改变收益、候选或授权状态。

## 2026-08-13 回测收益语义封存与证据归属

- 该历史切片当时把 internal-backtest report-root writer 升级为 `portfolio-internal-backtest-pack-v5` 与 `backtest-return-quality-v3`；当前 writer 已由顶部推进到 pack-v6/forward-evidence-v2。v5 持久化 pack 只保留紧凑候选/registry/阶段投影和严格 source manifest；同目录 content-addressed flat bundle 恰好绑定 exact pack、原 research bytes 与 statistical bytes 各一次，成员 basename、SHA-256、字节数、角色、candidate/evidence/pack/bundle Hash 均进入通用 immutable manifest。loader 不 glob、不猜最新文件，只按 manifest 精确读取三成员并调用完整 bundle verifier，从 detached research/statistical bytes 重算来源与数值语义。
- v1 pointer 与 pack v2/v3/v4 保留冻结的历史 verifier 语义；v4/quality-v2 仍以嵌入来源完成本地复算，v5/quality-v3 则以 exact detached bundle 完成同等来源复算。坏来源可留下结构有效、数值退回 `null/UNKNOWN` 的诊断 bundle，但绝不发布当前 pointer。组合来源仍固定属于 `PORTFOLIO_RESEARCH_PROTOCOL_V1`，strategy schema-7 只能是 `NOT_APPLICABLE`，相邻展示或同名字段不能建立事前假设绑定。
- v5 降低的是持久 pack 的重复体积，不是外部信任问题：`external_anchor_verified=false` 与 `cryptographic_authenticity_proven=false` 继续固定为假。本地无密钥 Hash 只能证明同一 bundle 的自洽；能重写整条身份链的主体仍可生成另一套自洽工件，不能据此声称原始外部工件真实性、盈利、选参、模拟授权或实盘权限。
- v5 builder/verifier 现在以同一份 detached parsed object 和 exact bytes 构建借用式 normalized semantic view，不再瞬时构造 v4 source document/source evidence/result evidence 包装；v2-v4 的 schema、字节与 Hash 语义保持不变。8 MiB 高密度合成 JSON 的 `tracemalloc` 定向测量从约 4.51x raw 降到 2.50x raw；这只是 Python 分配跟踪，不是生产 RSS。剩余峰值仍包含 canonical JSON 序列化；当前没有读取真实大工件、重跑 K 线或启动 HTTP/浏览器，因此未形成真实大体积性能、历史收益或渲染验收结论。
- v4 的来源身份明确属于 `PORTFOLIO_RESEARCH_PROTOCOL_V1`，其 strategy schema-7 状态只能是 `NOT_APPLICABLE`。组合研究链与策略 schema-7 事前假设链仍是两条独立 provenance；相邻显示、相同名称或调用方自报字段都不能建立白名单绑定，也不能把组合收益追认为某个策略假设的盈利证据。
- 该历史切片的固定收益 GET 外层合同是 `portfolio-backtest-return-quality-snapshot-v3`，当时 allowlist 接受 v4/quality-v2+forward-v1 与 v5/quality-v3+forward-v1；current snapshot-v4 与 legacy 统一 UNKNOWN 规则以顶部为准。公开投影始终不泄露完整 source evidence、来源身份内部字段、冻结 spec、settlement、路径或整包，也不读取数据库或重跑 K 线。
- pointer v2 继续使用 `current_internal_portfolio_backtest_pack.json` 固定文件名，并绑定 content-addressed bundle 目录、manifest 与 exact pack。pointer 64 KiB、manifest 256 KiB、pack 32 MiB、research 256 MiB、statistical 16 MiB 及三成员合计 304 MiB 都在 JSON 解析和语义验证前有界读取；duplicate keys、NaN/Infinity、过深 JSON、大小/Hash 不符、symlink/reparse、Windows 等价 basename/保留名/ADS 或 manifest inventory 漂移均 BLOCK。通用 immutable publish、pointer/pack/bundle、strict loader 与攻击矩阵定向通过。
- current immutable manifest、pack-v6（复用 pack-v5 detached source）、pointer-v2 与 archive-v3 的 JSON object 边界已收敛到纯 stdlib `strict_json_artifact`：只接受 UTF-8 bytes/object root，拒绝任意层重复键、NaN/Infinity/指数溢出与超过 root=1/max=128 的嵌套，并把 canonical serialization 留给各工件所有者。pointer-v1 与 legacy archive 普通读取故意保留历史解析语义；混合 pointer loader 只有在 current parser 失败且 legacy parser 明确识别 v1 时才回退，v2 不得降级。pack/quality golden Hash 与 detached 摘要保持不变；该历史交叉 150/150 通过，3 项因宿主 symlink 权限跳过，current tests 见顶部。
- archive 的公共 verifier 另加全函数 `MemoryError` 失败关闭：无论发生在 manifest strict parse 还是后续语义步骤，都只返回固定 `archive_verification_memory_exhausted`、权限恒假且不泄路径。真实进程级 OOM 仍不能由纯 Python 保证可恢复；该合同只防异常逸出被误作成功或暴露本地细节。
- `portfolio-evidence-archive-v3` 是当前 archive writer，并继续验证 v1/v2 历史归档。v3 在 archive `reports` 下保存同一 exact 三成员 bundle，research member 同时作为 replay source，禁止再复制第二份；archive manifest 绑定 pack/evidence/candidate、成员记录与 bundle Hash，restore/verifier 只按 manifest 精确加载并复核权限恒假。归档、恢复、篡改/缺失与 legacy 兼容定向通过；没有读取真实 runtime/SQLite/K 线。
- 回测页新增中性“证据归属脊柱”，只在冻结组合与当前自然前向双方都通过各自安全合同且候选 Hash 为严格 SHA-256 时显示“同一组合候选”；不同显示“候选不同·禁止合并解读”，缺失或畸形则显示“归属未核验”。策略/事前假设一栏始终声明“与组合候选未建立白名单绑定”。冻结组合块已成为独立 section，开发回测标题重新与开发收益台账相邻；桌面三列、`<=720px` 单列，全 Hash 只留在审计元数据，不使用涨跌色或 READY 文案。
- 归属脊柱的实际前向来源已纠正为 `forward_validation.incremental_observation`；此前渲染器把外层 `forward_validation` wrapper 直接交给只接受 `portfolio-forward-dashboard-v4` 的纯映射，因此合法候选也会退回“归属未核验”。交易总控现在在权限边界之后镜像同一条纯归属投影，让冻结组合、当前自然前向和策略/假设未绑定边界在总控首屏可见；它不新增请求、轮询、回测或状态色，也不把 SAME 解释为盈利。
- 正式策略研究的预注册写入顺序已收紧：当前 `strategy-matrix-protocol-v3` 把 sidecar 绝对路径、`IMMUTABLE_NO_CLOBBER` 模式和注册/领取复核要求纳入 protocol Hash。sidecar 使用同目录 UUID 临时文件、独占创建、`fsync` 与 no-clobber 发布；输出不能与 registry、其 `-wal/-shm/-journal`、固定报告 pointer、非 reports 根或非 JSON 路径碰撞。`RUNTIME_READ_ONLY` 在任何工件发布和 Store 创建前结构化阻断。v3 同时继承 v2 的 `daily-batch-alignment-v2` 与 7 天最大边界偏移合同；把它重封成 v0/999999 会 BLOCK，v1 历史语义不变。
- 正式 strategy research 与 strategy matrix runner 现在共用 `prepared-research-result-v1` 恢复边界：runner 用同一 completion clock 预构造确定性 completion receipt，先组装并通过完整正式报告 verifier，再把完整报告封入不匹配 exposure glob 的隐藏 no-clobber prepared 工件；之后 registry `complete()` 必须返回完全相同的收据，最终报告才可发布。若在 prepared 后停在 `RUNNING`，重试只复用 prepared 内的时钟/收据完成 registry；若已 `COMPLETED` 但 final 缺失，重试只恢复同一报告。两条恢复路径都发生在 build、claim、暴露重审和数据加载之前，prepared/final 冲突或发布失败明确返回非成功。strategy research 继续发布既有固定 pointer；matrix 原本没有固定 pointer，本轮没有凭空新增。matrix 的 report-level verifier 只核工件结构、Hash、治理、时间与语义绑定，不把候选消费端的新鲜度门槛错误施加到恢复工件。该机制没有把文件系统与 SQLite 变成跨资源事务：claim 后、prepared 发布前崩溃仍无安全恢复结果，不能自动重跑。
- registry 的 `register` 在插入前复核 sidecar，`claim` 在状态迁移前再次复核，CLI 在注册返回后还会做最终复核；注册后被替换的工件会让命令失败且后续领取继续阻断。数据库注册失败若已留下 sidecar，重试只可恢复同一未过期、同代次/假设/批次/实现/registry/binding 的原协议，不会用新时钟协议覆盖。文件系统与 SQLite 仍没有跨资源原子事务：DB 失败可能留下不可领取的孤儿审计工件，系统不会擅自删除它；这项边界不影响 legacy protocol v1/v2 的历史验证兼容。
- 小资金纯规划区不再把后端 `next_action` 当作可见产品文案：前端只从已验证检查项中选择首个证据缺口，再由八项白名单映射为中性中文；未知检查项统一回退，`READY`、买入或下单类注入不会显示。该区只保留状态一个 live region，证据缺口与权限说明共同进入区域描述，原网格、响应式断点和视觉 token 不变。
- 当前静态资源指纹为 `20260814-single-look-contract-1`。matrix runner + benchmark 为 36/36，prepared/research/matrix 最小交叉为 15/15；schema-8/历史兼容核心交叉为 8/8，新增精度、零值和负回撤反例为 3/3，protocol + pointer + 两条恢复交叉为 22/22；该历史 fresh research lean 三项全部实际执行，覆盖 234 个守卫用例并通过，未复用收据；前端 evidence 合同与 JavaScript 语法检查通过。数据与工件输入使用合成内存、Mock 或临时目录；静态合同、语法和 implementation-manifest 检查会读取当前受控源码，但实现与结论没有使用真实 runtime pack、数据库、缓存或日志作为证据。一次范围过宽的只读检索曾意外显示 runtime 文本匹配，已立即停止且未继续打开或使用其中值。该历史切片未启动 HTTP/浏览器，未重跑旧 K 线、G50/G51 或正式盲测。因此没有产生新的回测收益数值，也没有盈利、模拟盘或实盘授权结论。

## 2026-08-12 冻结证据 provenance 与策略状态中性化

- 该阶段的策略研究 writer 为 schema 9；当前版本已由顶部 schema 10 章节取代。schema 7 首次引入 `strategy-hypothesis-preregistration-v1`；schema 8 继承该事前假设并新增 `strategy-cost-stress-evidence-v1`；schema 9 继续继承两者，并新增 `strategy-fixed-chronological-slice-evidence-v1`。该历史时间切片从冻结 selection-prefix rows 复算数据身份与拓扑/汇总，但不重放折内回测；它仍固定声明 `parameters_refit_per_fold=false`，不是 WFO、不是盈利证明，也不授权模拟或实盘。schema 3–9 的历史 Hash、默认值和 verifier 语义不追溯修改；G50/G51 旧 ID 仍拒绝。
- runner 在加载研究数据前仍冻结 `implementation-manifest-v2`：声明的 Python 入口、静态 import/source 闭包、文件 SHA/大小，以及 Python/平台/SQLite/外部分发版本共同进入报告结果 Hash；schema 6/7/8/9 公共 verifier 都要求完整携带并复算该清单。策略研究固定 pointer 与独立只读 GET `/api/strategy/research-evidence` 继续只读一个绑定报告、不 glob、不重跑 K 线，并从固定 research runner 入口重建当前 import/source 闭包。项目外路径、`runtime*` 目录、`.env*` 与 `config.local.json` 在读取前阻断，公开投影不泄露路径。完整实现匹配也不证明盈利或授予任何交易权限。
- 新增纯 `strategy-research-currentness-facts-v1`：只从已验证报告的 `created_at`、`summary.common_as_of`/`selection_alignment.common_as_of` 与 server 注入的观察时刻复算报告年龄和距数据截止日的 UTC 日历天数；两处数据日期不一致、未来时间、伪整数或畸形日期都会失败关闭。它明确区分“可核对的年龄事实”和“尚未定义的新鲜/过期政策”：阈值字段固定为空、`threshold_applied=false`，不把日历日冒充交易日，也不产生选参、盈利、模拟或实盘结论。前端独立复算时间差，篡改年龄、日期、阈值或权限时整区回退未核验。
- 策略实验室把即时启发式规划与冻结证据拆成两条来源：页面单独请求版本化 frozen evidence；schema 3–10 使用 v3，schema 11/12 使用带 post-selection summary 的 v5。schema 7–12 都白名单投影已语义复算的事前假设摘要；schema 3–6 只显示 `LEGACY_NOT_BOUND`，不会把历史结果补写成事前证据。报告有效但当前策略未包含时显示“当前策略未纳入报告”，且 v5 必须同时保持两段 post-selection 为 NOT_RUN，不能借用其他策略的收益、假设或稳健性证据。任何状态都不选参、不证明盈利、不授予模拟或实盘权限。
- 纯 failure-conditions 投影把已核验的参数平台、成本盈亏线、固定参数时间切片、策略信号实现和完整研究闭包归一为五条基础失效条件；schema 11/12 的 v2 再增加冻结 TEST 与单次历史留出 replay-preservation。底层阻断或实现漂移才进入 `observed`；未运行进入 `evidence_gaps`。数据新鲜度、报告年龄政策和自然前向表现仍没有本报告证据，不得伪装成“失效已经发生”或自行发明天数阈值。投影不改输入、不产生新策略门禁，权限固定关闭。
- 策略实验室证据区按专业研究日志重排为 `源 来源与当前性 / 稳 稳健性观察 / 止 失效与权限边界` 三段证据脊柱，加入“研究假设”和“事前失效条件”两条可扫读证据。语义字标替代虚假的 01/02/03 流程序号；桌面三列、720px 两列加通栏失效、480px 单列，沿用原青色审计线和中性文字，不新增涨跌色或 READY 授权语义。该视觉切片只完成静态合同，未声称浏览器渲染验收。
- 交互回测新增纯 `backtest-risk-control-surface-v1`：唯一冻结网格是仓位 5 档、止盈 5 档、止损 4 档，共 100 个风险控制组合；后端复算覆盖、原生有限指标、最高分单元、一步邻接近优点、跨轴支撑和连通区域。它明确不是策略信号参数平台，仍是同一历史数据上的开发期比较，选择偏差未校正、非样本外、非冻结研究证据、不可选参、非盈利证明。完整网格缺格、重复、越界、伪数字、最高分无成交或孤立峰值都会诚实降级；G50/G51、旧 K 线和正式盲测均未触发。
- 回测页的研究门槛、时间切片、数据清单与审计工件现在统一使用中性的研究证据标签；`PASS/READY` 只保留在 `data-raw-status`/title 元数据，阻断才用降级提示，不再用绿色状态暗示模拟或实盘授权。新增 `evidenceResearchStatusBadge` 合同；当前 `styles/evidence/app` 静态资源缓存指纹已推进到 `20260814-single-look-contract-1`。

- 回测页收益质量证据带与策略实验室证据台账共用的 `evidence_presentation.js` 当前资源指纹为 `20260814-single-look-contract-1`；回测冻结收益在启动时单次读取，策略证据按所选策略在页面会话内缓存，只有首次选择或用户显式刷新才重读独立固定指针 GET，原有 60 秒实验室刷新不会反复语义复算冻结报告。
- 冻结收益质量台账现在可展开查看验证段/测试段的来源状态、样本量、基准超额依据和统计主张；阶段字段缺失、样本伪数字或权限异常时整区仍回退 `UNKNOWN / 未核验`，不增加请求、不改变收益质量或权限合同。该切片仅通过静态合同、Node 语法与 fresh frontend lean，未启动服务、浏览器或回测。
- 该历史切片当时的冻结收益 GET 外层合同为 `portfolio-backtest-return-quality-snapshot-v3`；当前合同已由顶部推进到 snapshot-v4，且只接受 exact pack-v6/quality-v3/forward-evidence-v2 的 current 组合。pack v2-v5 继续按各自冻结 verifier 读取，但经 pointer-v2 的 current public loader 统一 `UNKNOWN/null`；交叉/未来组合失败关闭。v5 界面历史文案仅说明“紧凑 bundle 来源已复算”，不会显示来源身份内部字段或声称外部真实性；当前 `styles/evidence/app` 资源指纹为 `20260814-single-look-contract-1`。GET 不返回冻结 spec、逐条 settlement、完整 source evidence、路径或整包，也明确没有重载数据库或独立重放 settlement 链。
- 回测页把这组摘要呈现为紧凑“成熟度审计脊柱”：`COLLECTING`、到期有效负结果、来源损坏和“前向统计已到期但整包仍被其他证据阻断”分别显示，避免把自然前向子证据与整体 pack 状态压成一个 READY。青色只作结构审计线，状态文案保持中性；模拟未授权、实盘永久硬锁。
- 控制中心纯投影现在对 `paper`、`risk`、`executor`、行情健康、前向、资金规划和最近审计中的嵌套权限字段递归失败关闭，并记录被覆盖路径；顶层有效权限仍只来自显式调用参数，组件自身不能把 `paper_authorized/live_order_allowed/execution_allowed` 重封为可见授权。该补丁只复制内存对象，不移动 `server.py` 的 I/O、缓存、数据库或回退。
- `/api/research/panel` 的最终响应现在经过纯 `research-panel-research-projection-v1`：研究卡片的 tone、方向/偏好、已核对状态和 BUY/SELL 类动作只保留 raw 元数据或“研究观察”，嵌套权限递归归零，root 固定只读/非盈利证明/模拟未授权/实盘禁止。扫描、行情、新闻和股票研究 I/O 仍留在 `server.py`。
- `/api/market/scanner` 现在经过纯 `market-scanner-research-projection-v1`：策略 ID/名称、动作和风险字段在可见层改为研究观察，原始值保留为 `raw_*`；“最高机会”摘要改为扫描快照说明，点击标的只切换行情，不再自动套用推荐策略。嵌套权限递归归零，数值只作扫描证据，不构成方向、选参、盈利证明或订单授权。
- 研究扫描前端改为中性信息层：标题、列名和状态说明使用“模型线索/风险观察/观察理由”，分数与涨跌不再使用方向色；行具备 list 语义，移动端继续沿用现有响应式布局。显式“写入研究提醒”仍是唯一通知写入入口，普通刷新不写入状态。
- 本轮 fresh research lean 3/3 实际执行 139 个守卫用例，包含 schema 3–7 兼容、事前假设/代次/策略绑定、未知 schema 降级阻断、固定研究/回测指针、自然前向成熟度摘要及交叉状态、完整实现清单/闭包重建/路径门禁、版本化失效条件、风险控制参数表面、篡改与权限失败关闭、关键 Python 语法和前端证据映射；fresh frontend lean 5/5 另行通过，均禁用收据复用。未启动服务或浏览器，未读取项目真实运行态、真实冻结 pack、旧 K 线或密钥。
- 回测页“稳健性与成本证据”台账投影已有 `temporal_validation`、固定参数时间切片/折叠、成本压力、前视检查和同数据风险控制参数表面，明确“固定参数时间切片·不等同真正 walk-forward”。可展开的局部敏感性脊柱只显示表面判断、100 格覆盖与跨轴邻域；策略信号参数平台仍保持未连接，必须由独立冻结 pointer GET 证明。两类证据不混用，缺失值不补零，模拟未授权、实盘永久硬锁。
- 成本敏感性汇总现要求基准、每个可用压力场景收益与回撤均为有限数值；缺失/字符串/非有限值直接 `BLOCK` 并返回 `null`，不再把缺证据折算成 0。真实负压力仍显示负值并阻断，前端对 `null` 显示“正值条件未核验”。
- 固定参数时间切片摘要同步采用严格有限数值合同：每个 `ok=true` 折叠必须提供有限收益、回撤和非负整数闭合交易数；缺失、非有限、伪布尔或失败折叠会阻断，并将累计交易数/最差回撤返回 `null`，不以 0 或默认回撤填补。
- 横截面验证/冻结测试汇总也不再接受数字字符串或负交易数；伪数字、布尔值和非有限指标会从可用集合剔除并触发覆盖门禁，避免 `int(... or 0)` 把异常交易数伪装成有效样本。该层仍只复算既有内存 cell，不重跑行情。
- 顶部模拟盘状态改为固定中性灯与“模拟未授权”文案；即使旧/运行态快照带有 `armed=true`，也只保留为 raw 审计元数据，不再用绿色状态或“模拟运行”暗示授权。模拟状态机、HTTP 423 硬锁和实盘永久硬锁均未改变。
- 行情 AI 研究会议顶部的行动式“下一步”改为“研究观察”，仍只显示等待确认/样本条件；盘口策略提示与风险引擎也固定为研究观察/权限待核验，raw `armed` 和模拟条件只留在 `data-*`/title 审计元数据，不再用“策略模拟可执行”或绿色灯暗示授权。异动雷达/走势驾驶舱的三个只读接口新增 `market-anomaly-research-projection-v1`，方向、偏好和 tone 在可见层统一中性化，原始值仅保留为 `raw_*` 审计字段，嵌套权限递归归零；全局配置总控新增 `configuration-research-projection-v1`，后端 `/api/config/full` 与 apply 只输出白名单研究配置观察，原始 `READY/PASS` 仅作审计字段，配置详情不展示路径或密钥，模拟/实盘权限固定关闭；当前静态缓存指纹为 `20260814-single-look-contract-1`。
- 配置总控的开发检查分、AI 配置、行情来源和实盘边界均使用中性文案与 `flat` 视觉层级；实盘只显示永久硬锁或保护待复核，配置应用只说明“配置已写入”，不暗示模拟可用或交易授权。
- 窄屏信息架构补齐：`<=480px` 时侧栏变为顶部四项导航和两列可滚动自选列表，终端与研究视图强制单列，研究视图原有 `258px/980px` 桌面最小列不再挤压内容；命令/状态/图表控件缩为可触达网格。该条已通过静态 CSS 合同和 Node 语法检查，尚未声称真实设备渲染验收。
- TradingAgents 的 NDJSON `complete` 事件现在先中和事件根再替换 `data`，通用 action/signal/价位/仓位字段也只保留为研究标签、`planning_*` 或 raw 元数据；事件根上的执行字段不能绕过最终会议纪要的权限包络。
- 固定冻结收益质量 GET 现在只在 pointer、pack/evidence Hash、候选绑定和公共 verifier 全部通过后投影 `generated_at`、candidate/pack/evidence Hash；失败响应仍为 `UNKNOWN/null`，不暴露路径。前端收益证据带要求时间戳与三组 SHA-256 指纹同时有效，显示“冻结于”时间和短包指纹，便于判断证据新鲜度与来源闭合，不改变收益结论或权限。
- 总控中的策略卡、风控卡、策略预检、体检生命周期、研究证据路径和回测到人工复核阶段不再直接显示 `READY/PASS/PAPER_READY` 或使用涨跌色；底层状态只保留在 `data-raw-status`/title 元数据，页面使用“研究预检已核对·模拟仍未授权”“研究证据待人工复核/存在阻断”等中性文案。实盘状态只显示永久硬锁或保护未确认·禁止执行。
- 策略研究台的作战室、信号列表、锚点、条件解释、矩阵、时间线、候选策略和并行比较现在统一为描述性证据表面：买卖/多空动作只显示“研究假设·非订单”，状态只显示研究证据标签，评分与模型概率不再使用方向色；命令条也改为研究状态、只读模拟参数和风控证据，并把“入场/执行/交易锚点”改成观察区间、研究流程和研究锚点。原始枚举只保留在 `data-raw-*`/title 元数据；该切片仅通过静态合同验证，未改变任何模拟/实盘权限。
- `/api/strategy/war-room` 的最终响应新增纯 `services/strategy_war_room_projection.py`：行情、策略计算、风险参数和调度器仍留在 `server.py`，投影层把 `READY/可模拟执行/OWNER/入场阶梯` 等执行语义降为研究观察、人工复核和规划-only，并递归中和权限字段；原始枚举只作为元数据保留，前端映射同时识别 `RESEARCH_*` 状态和 `raw_action`，不丢失中性证据标签。该路由不新增 I/O、回测或订单能力。
- `/api/strategy/doctor` 与 preview 现在也通过纯 `services/strategy_doctor_projection.py`：体检计算、pipeline record 和既有 I/O 顺序不变，最终响应把 `release_pipeline.paper_ready`、生命周期和 callback 状态降为描述性 `RESEARCH_*`，保留 `raw_paper_ready`/原始枚举作审计元数据，递归固定 paper/live/execution false。它不把体检通过翻译成模拟授权或盈利证明。
- `/api/strategy/lab` 现在通过纯 `services/strategy_lab_projection.py` 输出 `strategy-lab-research-projection-v1`：开发期仓位/目标区/失效区/启发式评分只放在 `planning_candidate`，旧操作字段置空，递归权限固定为 false；前端改称“规划候选/开发期分”，点击只复制到研究表单，不选参、不授权。行情读取和环境计算仍在 `server.py`，不新增回测或订单能力。
- `/api/strategy/lab` 仍用 `strategy-lab-evidence-boundary-v1` 明确即时规划本身没有稳健性证据；独立 `/api/strategy/research-evidence` 才能从固定、语义验证通过的冻结报告投影精确版本化的 `strategy-lab-frozen-evidence-v3/v5`，并显式区分事前假设已绑定、历史报告未绑定与冻结后历史复算。两者在前端分层合成，不在实验室路由内扫描报告、重跑历史 K 线或把冻结证据变成启发式选参权限。
- `/api/strategy/compare` 现在通过纯 `services/strategy_compare_projection.py` 输出 `strategy-compare-research-projection-v1`：买卖枚举只保留 `raw_action` 元数据并投影为“研究假设·非订单”，启用/停止条件改为研究复核语义，评分与概率保留但标记为未校准开发期启发式，不得选参或产生订单。
- `/api/strategy/analyze` 现在通过纯 `services/strategy_analysis_projection.py` 输出 `strategy-analysis-research-projection-v1`：方向、动作和 TP/SL 价格不再作为执行字段；价格规划进入 `planning_*`，原值仅作 raw 审计元数据，概率标记为未校准开发期估计，嵌套 risk config 与权限也失败关闭。图表锚点、侧栏、策略说明和风险预检统一显示研究规划/非订单语义。
- `/api/ai/market/dual-analysis` 现在通过纯 `services/market_ai_projection.py` 输出 `market-ai-research-projection-v1`：DeepSeek/GPT 的方向、胜率、支撑压力和 TP/SL 只作未校准研究观察，价格值进入 `planning_*`，原始模型回执保留，safe action、嵌套权限和根权限固定失败关闭。行情 AI 卡片不再用多空方向色或 READY 语义。
- `/api/ai/deepseek/analyze`、`opportunities` 与 `platform-review` 现在通过纯 `services/deepseek_projection.py` 输出 `deepseek-research-projection-v1`：方向、置信度、机会价位、仓位提示和 actionability 只作未校准研究观察，价位进入 `planning_*`，旧 raw 值仅作审计元数据，根与嵌套权限固定关闭。旧 DeepSeek 研究卡片同步改为研究标签、未校准和非订单规划。
- `/api/bot/center`、`/api/bot/scheduler`、`/api/bot/assign`、`/api/bot/release` 与 `/api/strategy/robot-profiles` 现在通过纯 `services/bot_research_projection.py` 输出研究观察合同：OWNER/可执行/模拟 armed/推荐和账户比例只保留 raw 元数据，主字段改为研究角色、开发期分、缺口或 `null`，根与嵌套权限固定关闭。调度仍只记录既有规划状态，前端改称研究角色调度，不把角色变更翻译成模拟或实盘执行。
- 行情真值中心与自然前向观察把整区 `aria-live` 收窄到原子状态节点，避免每个数值刷新都打断读屏；研究证据路径在移动端改为单列。前端仍只做一次独立 GET，不合并交互开发回测，不触发回测或参数搜索。
- 本切片只做静态/合同验证：fresh research lean 3/3（95 个守卫用例）、fresh frontend lean 5/5、strategy-analysis、market-ai、deepseek、trading-agents、strategy-compare、strategy-lab、war-room、doctor、bot research、market anomaly projection 与 configuration projection 合同均 PASS。未启动服务或浏览器，未读取真实冻结 pack，未重跑旧 K 线、G50/G51 或正式盲测。
- `/api/ai/trading-agents/discuss` 现通过纯 `services/trading_agents_projection.py` 投影 `trading-agents-research-projection-v1`：多空/WAIT/观察决策映射为 `RESEARCH_*`，置信度与胜率只保留 raw 元数据并置为未校准，TP/SL 只进入 `planning_*`；同步中和 NDJSON 流事件、嵌套权限和最终会议纪要，固定 research-only、paper 未授权、live 永久硬锁。前端会议室改为研究标签、未校准权重和非订单规划，不再用方向色或已生成文案暗示授权。新增纯合同 4/4 PASS；未启动 AI 服务或读取密钥。

## 2026-08-12 internal-backtest pack v3、冻结指针与回测预览边界

- 该 2026-08-12 历史阶段把 internal-backtest writer 升级为 `portfolio-internal-backtest-pack-v3`，旧 v2 的 Hash 与验证语义保持兼容。v3 新增受 `evidence_hash / pack_hash` 约束的 `portfolio-internal-forward-evidence-v1`：它完整绑定候选与冻结 spec、已语义复算的历史统计口径、自然前向 settlement 序列摘要、readiness-v2 和 forward audit-v1 的逐条序列/阶段/审计 Hash；pack 明示自己没有重载数据库或独立重放 settlement 链，不能把上游复算收据冒充新的数据库验真。current writer 以顶部 pack-v6 为准。
- 状态语义按证据成熟度分开：未达到自然前向收益期与实际调仓双门槛时为 `COLLECTING`；成熟且新统计合同通过时最高为 `RESEARCH_REVIEW_READY / REVIEW_REQUIRED`；成熟但得到有效负结果时为 `RESEARCH_REVIEW_BLOCKED`；来源损坏、缺失、错绑或权限升级会让 pack 本身成为 `INTERNAL_BACKTEST_BLOCKED`。历史统计 claim 的 `BLOCK` 在 v3 只提供冻结口径，不再单独永久阻断新的自然前向结果。无论哪种状态，`profitability_proven=false`，模拟不自动开启，实盘永久禁止。
- `backtest-return-quality-v1` 进一步要求收益口径可复算：基准超额只有在策略与基准收益同时存在时才可用；单独上报的 excess 只保留为未采用的报告值。所谓“配置成本后测试收益”必须由 test run_spec 与冻结 fee/slippage 精确绑定；压力成本必须与冻结情景合同逐标签、费率和滑点完整匹配，缺场景或只匹配子集时不输出伪造的最差值。所有缺口继续使用 `null / UNKNOWN / PARTIAL`，不补 0。
- 该历史阶段的 internal pack writer 只在 pack 结构验证通过且输出位于明确 report 根目录时，原子发布当时的固定 `portfolio-backtest-pack-pointer-v1`；自定义外部输出不会更新指针，保留文件名冲突会失败关闭。独立只读 GET `/api/portfolio/backtest-return-quality` 只读取该固定指针，不 glob、不扫描“最新文件”、不重建 pack、不重跑 K 线；它复核 pointer Hash、pack 文件 SHA、候选/pack/evidence 绑定与公共 pack verifier 后，只白名单返回收益质量与固定 false 权限。该历史合同后来由 pack-v5/pointer-v2 接替，current 则以顶部 pack-v6/pointer-v2 为准；结构有效但研究状态为 BLOCK 的 pack 仍不能因此变成 READY。
- 该 2026-08-12 切片当时返回 `portfolio-backtest-return-quality-snapshot-v2`，随后历史章节曾推进到 snapshot-v3；当前合同以顶部 snapshot-v4 为准。pack v3 的 `forward_promotion` 使用 `portfolio-backtest-forward-promotion-summary-v1`：收益期/调仓双门槛、审计与 readiness 状态、Hash、通用 blocker 和验证范围均来自已验证整包；pack v2 明确返回 `null`。前向子证据可达到“待人工研究复核”，而整包仍可因其他证据保持 `INTERNAL_BACKTEST_BLOCKED`；两层状态必须同时展示，不能互相覆盖。
- internal pack v2/v3 的 `forward_progress` 若存在，verifier 现在要求六个自然前向/调仓计数为原生非负整数、调度健康为非空字符串；把数字字符串随 pack Hash 重封也会失败关闭，避免投影阶段的 `int(... or 0)` 把伪造进度包装成冻结证据。旧手工 v2 工件缺少该字段时保持兼容，仍不获得任何授权。
- `/api/strategy/backtest/preview` 的最终响应已抽为纯 `strategy_backtest_projection.py`：上游行情、回测、成本与时间切片仍在 server，投影只 deepcopy 并固定 `preview=true`、`pipeline_run=null`、历史研究/非盈利证明、不可选参、模拟未授权和实盘禁止；嵌套执行权限也会被中和。回测页现以独立证据带一次性读取 internal-pack GET，不轮询、不触发回测，也不覆盖交互开发回测指标；纯映射同时要求来源验证 PASS、snapshot v2、`return_quality` v1、根与嵌套权限全关、有限数值/null 以及策略/基准/超额复算一致，任一异常整区退回“冻结收益质量未核验”。即使质量 `AVAILABLE` 也只显示“描述字段齐全 · 非盈利证明”，`BLOCK` 则显示“来源已核验 · 研究阻断”。当前只完成静态接线与合同验证，尚未声称 HTTP/浏览器运行态验收。
- 本切片只运行合成/静态最小验证：自然前向 audit、pack v2/v3、收益质量、预览投影、固定 pointer、参数平台与 G50/G51 退役合同均通过；fresh research lean 档位实际执行 95 个守卫用例、关键语法与前端证据合同，3/3 checks PASS；fresh frontend lean 5/5 checks PASS；本轮新增的冻结 `forward_progress` 重封数字字符串反例也在 pack 定向套件中通过。没有启动服务或浏览器，没有打开真实 pack、数据库、缓存、日志、状态或密钥，没有重跑旧 K 线、G50/G51 或正式盲测，也没有执行模拟或真实订单。边界透明记录：先前两次范围写错的源码常量检索，以及本轮一次路径排除未生效的检索，曾输出 `runtime/backups/.../source` 中的匹配源码行；均立即停止，未打开其中业务数据，也未据其形成实现结论；后续检索均限定明确源码/测试/文档路径。

## 2026-08-12 回测收益质量、研究查询投影与前端证据层级

- internal-backtest pack 新增纯 `backtest-return-quality-v1` 投影。它只消费 pack 已加载并完成既有语义校验的研究/统计证据，白名单输出验证段与测试段的策略收益、基准收益、超额收益、配置成本后的测试收益、压力成本最差收益与回撤、样本量、开发期统计状态、失败项和证据缺口。缺字段保持 `null / UNKNOWN`，不能用 0 补齐；负压力收益、非正超额、统计阻断或开发检查失败会把质量状态降为 `BLOCK`。`AVAILABLE` 只表示描述字段齐全，不表示策略通过、盈利能力成立或可以晋级。
- `return_quality` 在 internal pack 的 `evidence_hash` 与 `pack_hash` 计算前写入，因此新字段受两层内容 Hash 约束；旧 pack 没有该字段仍按原 schema 兼容。投影固定 `profitability_proven=false`、`performance_claim_allowed=false`、`parameter_selection_allowed=false`、`automatic_paper_activation_allowed=false`、`paper_authorized=false`、`live_order_allowed=false`，嵌套同名字段不能升级根权限。它依赖 pack 的既有来源验证，不重新读取报告或运行 K 线。
- 回测页单独新增中性“开发回测证据台账”：开发累计收益之后依次披露基准/超额、成本假设及是否计入、最大回撤、样本/闭合交易/时间证据，再放年化、胜率和 Sharpe。缺失信息显示“未提供/未核验”，主收益、分段收益和参数比较不再使用涨跌色；原优化区改称“开发期参数比较”，最高收益项明确为“开发期最高收益候选 · 选择偏差未校正”。本条记录的是当时仅消费交互回测响应的阶段；顶部最新切片已新增独立冻结收益质量证据带，但两组指标仍不混合。
- 小资金纯规划视图改为“当前证据缺口”优先，资金文字固定为非账户余额的名义封套，约束台账与公开规则并列，数量和可见深度通过原生 `details` 按需展开；5% 只叫名义缓冲参考，不冒充余额冻结、手续费或实际支出。模拟仍未授权，实盘仍永久硬锁。
- 第三个 `server.py` 纯投影切片已经完成：`services/research_query_projection.py` 只组装研究上下文和摘要，查询、缓存、数据库、权限判断和回退继续留在 server。纯函数不接受调用方传入根权限，始终输出 `read_only=true`、`live_order_allowed=false`，嵌套内容不能授权。控制中心、自然前向与研究查询三组投影合同合计 6/6 PASS；回测质量与 pack 合同 14/14 PASS；相关 JavaScript 语法和静态证据映射合同 PASS。没有启动服务或浏览器，没有读取真实运行态，也没有执行旧 K 线、G50/G51 或正式盲测。
- 新增 `docs/README.md` 作为文档入口，明确 `DEV_BASELINE.md`、本状态文件和优化评审的权威顺序；历史 G50/G51 与交接材料保留为历史证据，不能覆盖当前源码、当前测试或交易权限边界。

## 2026-08-12 G42 到期统计合同：自然前向序列独立复算

- 已补上 G42 到期后的真实证据缺口：旧 `build_forward_performance_readiness` 只读取历史统计审计的结论和绩效聚合值，不能从自然前向逐日收益重新执行统计合同。新增 `portfolio-forward-statistical-audit-v1`，只从逐条通过 settlement 语义与 Hash 链复算的 `portfolio-forward-series-evidence-v1` 构造策略/基准配对权益序列；聚合收益不能替代该序列。
- 新审计不使用当前默认常量冒充冻结合同，而是绑定已完成语义复算的历史 `portfolio-statistical-audit-v3` 的 schema、audit/artifact/input-binding/config 身份，并逐字段复用 moving-block 方法、重采样次数、区块长度、置信度、正概率门槛、选择调整概率、Bonferroni 口径和开发试验次数。唯一允许差异是候选预注册的自然前向最小收益期，`contract_comparison` 会显式记录历史阶段下限与 forward 下限，其他差异一律失败关闭。
- G42 的历史统计 claim 本来就是有效的 `BLOCK / INSUFFICIENT_STATISTICAL_PROMOTION_EVIDENCE`；新合同只把其已验证 config 当作复算口径，不能把旧 claim 当成新前向结果。未同时达到收益期和实际调仓双门槛时输出 `NOT_DUE`、不运行 bootstrap、不生成伪 PASS；到期后缺少审计为 `RESEARCH_REVIEW_BLOCKED`，schema、Hash、候选/spec、settlement 链、成熟度、合同或权限绑定错误为 `BLOCK`，语义正确但新统计仍失败也保持研究阻断。
- `portfolio-forward-readiness-v2` 由 runner 显式启用；历史默认调用继续保留 `portfolio-forward-performance-v3` 的原语义和 Hash 兼容。v2 只保留历史审计的完整性/config 绑定，把旧 historical claim gate 替换为新 forward audit gate，并固定 `profitability_proven=false`、`research_only/observation_only/simulation_only=true`、`paper_authorized=false`、`live_order_allowed=false`。统计 PASS 只表示该自然前向组合序列通过冻结统计口径，不是盈利证明，也不授予模拟或实盘权限。
- 本段记录的是当时的旧 pack 边界；顶部最新状态已由显式 v3 schema 和独立 verifier 完成接入。v2 仍保留原有 historical-claim promotion 语义，v3 才使用新的自然前向证据状态，不能把两代结论混算。
- 轻量证据：新纯内存合成 settlement 链测试 5/5 PASS（含“工件完整但自然前向统计有效否定”的反例）；旧组合统计审计与两条 legacy readiness 交叉测试 9/9 PASS，合计 14/14；6 个相关 Python 文件 AST PASS，research lean 计划已包含新测试类。没有读取真实 runtime、数据库、缓存、日志或截图，没有重跑旧 K 线、G50/G51 或正式盲测，也没有开启模拟或真实下单。

## 2026-08-12 前三个大服务拆分：控制中心、前向与研究查询投影脱离 I/O

- 新增纯投影模块 `services/platform_control_center.py`，承接行情健康的固定权限包络，以及控制中心最终 JSON、摘要和 `latest_order` 字段白名单。模块不访问文件、网络、数据库、缓存或锁，也不导入 `server.py`。
- 新增 `services/portfolio_forward_projection.py`，只承接自然前向最终只读权限包络与既有纯 dashboard builder；旧 payload 中不可信的 `incremental_observation` 会被重新投影覆盖。文件/数据库读取、候选注册、Hash 校验、scheduler、缓存、锁和回退仍留在 `server.py`。
- 新增 `services/research_query_projection.py`，只承接研究上下文与摘要的最终 JSON 组装；查询、数据库、缓存、权限判断和只读回退仍留在 `server.py`。该投影的根权限由函数内部固定，不接受调用方传值。
- `server.py` 继续负责原有服务调用顺序、共享缓存、只读 `FileNotFoundError` 回退和路由，只把已经构建的组件交给纯投影函数；根级 `market_truth` 与 `data_health.data_truth` 双入口保持兼容。
- 三组投影的权限字段均失败关闭，组件内同名字段不能升级根权限；最近订单仍只输出原有八个审计字段。纯内存合同合计 6/6 PASS；没有启动服务、浏览器、完整回归或旧 K 线。

## 2026-08-12 公开行情提供商级节流：跨端点刷新不再相互冲击

- 现有 instrument rules 与 public order-book 服务已经按标的做 singleflight；本轮补上 OKX 公共 GET 的共享 `ProviderRequestCoordinator`，把不同公开端点放进同一个有界内存窗口（20 次 / 2 秒），不等待、不排队、不写盘，超限只返回明确的 `RATE_LIMIT` 与重试毫秒数。
- 连续上游失败达到阈值后使用有界指数退避（1 秒起、30 秒封顶）；成功会清除退避。服务仍保留原来的 last-good/STALE/UNAVAILABLE 语义，不会用限流失败伪装 READY，也不新增自动重试或交易权限。
- `market_data.okx.read_bodyless_okx` 现在统一记录脱敏的 OKX 公共调用健康状态；不记录 URL 参数、命令、环境、密钥或原始响应。现有每标的缓存与 `force` 刷新合同继续有效，公开行情仍是只读证据。
- 轻量证据：提供商协调器 3/3、instrument rules + public order-book 11/11、provider health 2/2 PASS；3 个 Python 文件 AST PASS。没有运行完整 750 项回归、旧 K 线重放、真实网络验收、模拟授权或真实下单；实盘永久硬锁保持不变。

## 2026-08-12 参数平台 v2 与证据权限分栏：识别尖峰，不自动调参

- 参考 QuantConnect 对参数过拟合、参数敏感性和 walk-forward 的边界说明（[Parameters](https://www.quantconnect.com/docs/v2/writing-algorithms/optimization/parameters)、[Optimization Results](https://www.quantconnect.com/docs/v2/cloud-platform/optimization/results)），schema 4/5/6 报告强制使用 `strategy-parameter-plateau-v2`。拓扑只来自报告自身冻结的 variant 顺序；它检查的是“冻结序列直接邻接”，不是多维参数的数值距离。
- v2 先核对冻结变体与 ranking 的唯一身份和完整覆盖，再从全部有限分数中找最佳点。只有 `status=PASS && eligible_for_test=true` 的最佳点与至少一个直接相邻、同样合格的近优点才能形成描述性平台；非相邻端点或不合格邻点不能凑成 `PASS`。
- 历史 schema 3 报告仍可没有平台摘要；若带摘要，只按 legacy `strategy-parameter-plateau-v1` 原算法复算。schema 4/5/6 缺 v2、降级为 v1、身份错配或内容篡改都会失败关闭。两代摘要都不重跑 K 线、不改变 `freeze_validation_candidates`，并固定 `descriptive_only=true`、`parameter_selection_allowed=false`、`paper_authorized=false`、`live_order_allowed=false`。
- 当时的新报告为 schema 9；当前 writer 已推进到顶部说明的 schema 10。schema 5/6/7 保留 `strategy-research-selection-cell-evidence-v2`，schema 8 保留 v3 cell 与 `strategy-cost-stress-evidence-v1`，schema 9 使用 v4 cell 与历史 `strategy-fixed-chronological-slice-evidence-v1`；这些旧版本的 Hash/语义保持不变。
- 当前 schema 5/6/7/8/9 verifier 都要求批次 `limit`、`max_test_candidates` 和 `max_confirmation_candidates` 为原生整数且至少为 1（`limit` 至少为 360）；把数字字符串写入 batch spec 后再重封 Hash 仍会 `BLOCK`。schema 3/4 的历史哈希与验证语义不变。
- 成本压力现在要求最差压力场景收益仍为正；原“walk-forward”摘要已明确改称固定参数时间切片，标记 `parameters_refit_per_fold=false` 与 `walk_forward_optimization_claim_allowed=false`，不得冒充真实 WFO。G50/G51 仍为本代否定，仅允许历史证据回放；任何新机制必须使用新策略 ID 并重新预注册。
- 总控新增固定的“当前可做 / 当前不可做”权限分栏；行情、自然前向、纯规划和模拟账户状态使用中性证据/权限文案，空策略不再默认显示 Long 或伪造禁做条件。“核对当前证据”只刷新已有总控快照，不会隐式启动回测、策略体检或参数搜索。
- “研究证据与权限阶段”不再直接展示带方向色的 `PASS/READY`：运行摘要与七个阶段改用中性完整句，原始枚举仅留在 `data-raw-status` 与 `title`。即使上游快照声称 `paper_authorized=true` 或 `armed=true`，控制中心也始终显示“模拟未授权”；自然前向、小资金规则、回放与审计行只显示中性研究状态，原始枚举留在元数据。实盘始终显示永久硬锁或保护未确认；列表补齐 `aria-live/list/listitem`，720px 以下使用可换行的紧凑双列行。
- 开发期策略比较、回测候选行和分数现在统一使用中性视觉层；点击候选只复制到研究表单并明确“未运行、未授权”，不再以排行榜、优化参数或涨跌色暗示选参或盈利结论。
- 轻量证据：冻结策略参数平台、同数据风险控制参数表面、cell-evidence-v2、schema 3/4/5/6 兼容与篡改、完整实现清单、无阈值年龄事实、失效条件、自然前向成熟度摘要、成本/时间切片、G50/G51 硬锁及边界文案均纳入 fresh research；133 个守卫用例与关键 Python 语法 3/3 PASS，frontend 5/5 PASS。只使用合成/测试夹具和既有 ranking；没有启动正式盲测、没有重跑旧 K 线或 G50/G51、没有读取项目真实运行库，也没有授予模拟或实盘权限。

## 2026-08-11 只读验收：构建、权限和三标的行情切换

- 在隔离临时目录启动新的 `HAKIMI_RUNTIME_READ_ONLY=1` 实例；健康响应的 `loaded_fingerprint` 与 `disk_fingerprint` 一致：`6a7a187d27749898ba74f2338e9ffbf2dd40189b208886b78c181523bc99b305`，`read_only=true`、`paper_authorized=false`、`live_order_allowed=false`、`live_trading_hard_block=true`。
- `/api/risk/engine` 返回 `status=RUNTIME_READ_ONLY`，模拟订单和自动模拟订单均阻断；`POST /api/paper/arm` 返回 HTTP 423。实例结束后只清理本轮创建的临时目录，没有读取其中的数据库、缓存或日志。
- 本地浏览器复测 AAPL、NVDA、BTC-USDT：每次切换后活动标的、活动行、工作流标的和图表标的保持一致；周期保持 `1Dutc`；过渡采样中 K 线数量始终大于 0，最终均为 140 条以上，画布尺寸保持 1021×380。AAPL/NVDA 的快速预览在真实源失败时仍保留，BTC-USDT 从快速预览切换到 OKX 实时缓存，不出现旧标的覆盖。
- 浏览器控制台 `error/warn` 均为 0。本次是运行态验收，不等同于完整 750 项回归，也没有开启模拟授权、正式盲测或真实下单。

## 2026-08-11 报价来源一致性修复：低质量回退不再覆盖当前报价

- 本次浏览器验收发现真实问题：股票页面曾同时显示离线种子报价与另一来源的研究/价格日志；盘口组件还优先读取了日志中的旧来源价格。现已在 `stock_quote_guard.js` 增加同标的报价来源等级与时间倒退门禁：Yahoo/Stooq/Futu/本地缓存等较高质量报价在新鲜期内不会被 `offline-seed`、preview 或更低质量来源覆盖。
- `app.js` 现在保存当前股票报价身份，股票盘口、价格日志和非信号微结构只消费当前同源日志；不同来源的历史值会被隔离，不再冒充“当前报价”。图表仍明确标注 `快速预览 / 预览` 或实时来源，报价源与 K 线源分开披露，不强行把二者混成一个源。
- 定向证据：`stock_quote_guard.test.js` PASS（来源升级、低质量覆盖拒绝、同源旧时间拒绝）；`node --check app.js` PASS；Electron `npm.cmd run check` PASS。隔离浏览器复测 AAPL/NVDA 均显示同源 Yahoo 报价，BTC-USDT 保持 OKX 实时；三标的切换期间 K 线不消失，控制台 error/warn=0。
- 该修复仍只影响展示一致性和研究数据隔离，不改变风险门禁、`POST /api/paper/arm=423`、模拟未授权或实盘永久硬锁；没有运行完整 750 项回归、旧 K 线重放、模拟授权或真实下单。

## 2026-08-11 ResearchBrief 版本协商与幂等导入

- 参考研究服务常见的事件重试边界，`ResearchBridge` 现在提供 `ResearchBrief` `1.1` 合同，同时兼容明确的 `1.0` 旧摘要；GET 合同会返回支持版本和 `contract_hash`，未知版本直接拒绝。
- 摘要可带可选 `idempotency_key`/`event_id`。同一键与同一内容哈希重试返回 `IDEMPOTENT_REPLAY`，同一键但内容不同返回 `IDEMPOTENCY_CONFLICT`（HTTP 409），不会重复入库或覆盖原摘要。
- 数据库迁移只增加 `schema_version`、`idempotency_key` 和 `payload_hash` 三个审计字段；不会读取或携带账户、订单、密钥、命令、环境或执行权限。`research_only=true` 和 `live_order_allowed=false` 继续由服务端强制写入。
- 轻量证据：ResearchBrief 原有拒绝用例与版本/幂等用例 2/2 PASS；`research_bridge.py`、`server.py`、`test_core_services.py` AST PASS。该切片未触碰现有运行库、未开启模拟或实盘。

## 2026-08-10 最近两次观察作业回执：直接解释“为什么今天没变化”

- 参考 Hummingbot 将最近运行与历史结果分开查询、NautilusTrader 为事件保留稳定身份与前后时间的做法后，本轮只迁移“最近两次有限观察作业可追溯”的机制；没有迁移 executor、订单、Webhook、自动告警、自动重试或完整事件总线。
- 新增 `portfolio-forward-observer-job-receipt-v1`。只有调度器真实启动 observer 子进程时才新增一张回执；普通心跳原样保留最近两张，不会伪造一次“无变化”。回执绑定作业 ID、候选激活身份、调度决策、到期日期、进程起止、已校验内容哈希的 observer 工件，以及 ledger 前后 audit/chain 水位。父调度器另把完整关键 claims 密封为 `portfolio-forward-scheduler-attempt-evidence-v1` 写入同一前向状态工件，覆盖正常退出、超时、启动失败与无效子输出；当前工件同时绑定前一张回执头。不保存 stdout、stderr、命令、环境、绝对路径或状态文件路径。
- 结果严格区分 `PROCESSED_NEW_BARS`、`NO_NEW_BAR`、`NO_WORK_ALREADY_ACCOUNTED`、`BLOCKED` 与 `FAILED`。其中“无新完成 K 线”只允许用于账本前后完全不变的精确等待状态；阻断若伴随账本变化、audit 非 PASS、候选漂移、工件不一致或超时，一律升级为 `FAILED + reconciliation_required`，不得用普通阻断掩盖。
- 同一候选最多保留最近两张链式回执；候选激活身份改变时从新 genesis 开始。旧 `portfolio-forward-scheduler-v1` 工件只有在没有当前 attempt 证据时才按未知兼容；一旦存在 attempt，新写入的 `portfolio-forward-scheduler-status-v2` 必须包含与它逐字段一致的非空最新回执。空链、降级 v1、截断失败作业、改权限、断链、重封矛盾内容或最近作业要求对账时均失败关闭，且不会自动启动下一次 observer。
- 控制中心升级为 `portfolio-forward-dashboard-v4`，继续复用原 `GET /api/platform/control-center` 和“本轮处理”位置，以中性文案显示“最近作业 0 条 · 无新完成 K 线；前次 1 条”。完整时间、Job/Receipt Hash 与前后水位只放证据提示；没有新增 DOM 卡片、请求、按钮、颜色、模拟授权或实盘入口。
- 后端首轮调度器定向检查 23/23 PASS；边界收口后仅复跑受影响用例，最终干净一轮关键证据链 3/3 PASS；4 个受控 Python 文件 AST 与 `app.js` 语法检查 PASS。没有运行完整回归、旧 K 线重放、浏览器轮巡、模拟授权或真实下单，实盘永久硬锁保持不变。

## 2026-08-10 相邻自然前向观察变化：告诉用户“发生了变化”，永久不解释为订单

- 对照 LEAN 的 Insight 序列、TradingView 的冻结上下文与事件记录、NautilusTrader 的不可变事件身份，以及 Hummingbot 的运行历史后，本轮只迁移“最近两条结果可追溯、可比较”的机制；没有迁移 PortfolioTarget、执行器、实时告警、Webhook、自动重试或成交历史。
- 新增 `forward-observation-change-v1`。账本审计现在对全部有效观察的有序 `{signal_date, observation_hash}` 链计算数量与 Hash；变化收据只从链尾相邻两条、同一候选且各自通过决策投影、风险快照、权限和内容 Hash 校验的观察生成。少于两条时明确返回 `NOT_ENOUGH_OBSERVATIONS`，绝不伪装成“没有变化”。
- 收据保留目标集合、总配置比例、原因、市场状态和风险复核的结构化前后差异，使用规范十进制文本计算比例变化；同时固定 `descriptive_only=true`、`direction_signal_allowed=false`、`performance_claim_allowed=false`、`paper_authorized=false`、`live_order_allowed=false`。当前页面只展示日期、观察集合“有变化/未变”和风险复核迁移，不展示具体增删、比例、价格、收益或方向色。
- 控制中心投影升级为 `portfolio-forward-dashboard-v3`，仍复用原有 `GET /api/platform/control-center` 与“最近观察 / 下一步”位置。空跑 `records=[] / processed_count=0` 时继续从账本投影同一变化收据；旧工件缺字段只显示 `NOT_CHECKED`，非空篡改才阻断。
- 后端仅运行影子观察与调度两个定向模块：42/42 PASS；六个相关 Python 文件 AST 与 `app.js` 语法检查 PASS。没有运行完整回归、旧 K 线重放、浏览器轮巡、模拟授权或真实下单；实盘永久硬锁保持不变。

## 2026-08-10 最近自然前向观察收据：空跑不再冲掉上次有效结论

- 对照 LEAN Insight 生命周期、NautilusTrader 观察者/策略权限分层、Hummingbot 数据采集与 Freqtrade 前向运行后，本轮只迁移“长期观察器保留最近一次有限作业结果”的机制；不迁移模拟钱包、成交、PortfolioTarget、Execution、Webhook 或高频全量事件存储。
- 新增 `latest-forward-observation-receipt-v1`。收据只从 ledger 审计为 `PASS` 的最近有效自然观察生成，并绑定候选、观察日、数据集、风险快照、决策、原观察、forward-state 与 ledger audit Hash；状态工件继续用整体内容 Hash 包住该收据。风险快照必须自校验且状态一致，页面标的、比例、原因、市场状态与波动率也必须和真正被 Hash 的嵌套决策完全一致。非空收据任一身份、权限、投影或 Hash 不一致都会阻断。
- `records` 继续只表示“本轮实际处理的日期”。因此没有新完成 K 线时仍是 `records=[] / processed_count=0`，不会重放旧 K，也不会把上一轮伪装成本轮计算；独立收据则继续保留上一张已审计结论。旧 `portfolio-forward-status-v1` 工件没有收据时只显示 `NOT_CHECKED / 已隐藏`，不会因升级被误判为篡改。
- 控制中心投影升级为 `portfolio-forward-dashboard-v2`，复用原有 `GET /api/platform/control-center` 与现有“最近观察 / 下一步”位置，显示“观察目标（非订单）”、观察日、风险复核、短收据和下一步。完整 Hash 只作证据提示；收据缺失或无效时立即隐藏，不新增卡片、按钮、请求、方向色或执行入口。
- 最终组合定向验证 39/39 PASS（0.652 秒）；风险收据最后一处空 Hash 收口后，仅复跑受影响模块 21/21 PASS（0.583 秒），七个相关 Python 文件 AST 与 `app.js` 语法检查 PASS。没有运行完整回归、旧 K 线重放、浏览器轮巡、模拟授权或真实下单；`paper_authorized=false`、`live_order_allowed=false`，实盘永久硬锁不变。

## 2026-08-10 固定价格带盘口真值：5/10/25 bps 已接入，仍永久不是方向信号

- 重新核对 Hummingbot、NautilusTrader、Freqtrade、CCXT 与 OKX 官方合同后，本轮迁移“按价格边界逐档累加”和“盘口结构完整性”两项机制，不迁移 Freqtrade 把静态盘口比例用于入场过滤的做法。比较口径从容易受档位密度影响的“同数量档位”升级为围绕当前中价的固定 5/10/25 bps 双边价格带。
- `services/public_order_book.py` 的纯派生合同显式升级为 `public-order-book-microstructure-v2`，包含它的小资金计划升级为 `small-capital-planning-v3`。它不新增网络请求，只消费同一份已通过标的、来源、时间、双边严格排序、非交叉、内容 Hash 与权限核验的公开 20 档盘口；原始 `book_hash`、派生 `microstructure_hash` 与最终 `plan_hash` 继续分层绑定。
- 每个价格带都用 Fraction 精确计算中价对称边界，并独立累计买价侧/卖价侧的基础币数量和报价币名义额。覆盖证明不看“是否返回 20 档”，而看该侧最远可见价是否抵达带宽边界；未抵达时数值只叫“已见的可见下界”，逐侧标记“部分”，绝不补齐、外推或升级为阻断。价差本身吞掉窄价格带时，合法的 0 档/0 名义额仍会如实显示。
- 控制中心继续复用原有 `GET /api/platform/control-center` 和既有多行区域，不新增路由、请求、DOM 卡片、按钮或方向色。页面固定显示 5/10/25 bps 三行“距中价带内可见名义（USDT）· 非信号”，不再显示买卖占比；价格带异常则整块规划合同失败关闭并隐藏数值。
- 有效状态最高仍只叫 `OBSERVATION_ONLY`。REST `seqId` 只作为快照证据，`sequence_continuity=NOT_PROVABLE_REST`；20 档仍是标准非 RPI 可见前缀，不是完整订单簿。完整深度、RPI 资格、隐藏流动性、队列位置、撤单、真实成交概率与未来方向继续全部为 `NOT_CHECKED`，且 `read_only=true`、`execution_allowed=false`、`paper_authorized=false`、`live_order_allowed=false`。
- 本轮只运行订单簿与小资金规划两个定向模块：15/15 PASS（0.053 秒），五个相关 Python 文件 AST 解析与 `app.js` 语法检查 PASS。没有运行完整回归、旧 K 线重放、浏览器轮巡、模拟授权或真实下单；实盘永久硬锁保持不变。

## 2026-08-10 100–200 美元纯规划准备：公开规则与多档成本观察已接入，仍不接执行

- 参考 Freqtrade、Hummingbot、CCXT 与 NautilusTrader 后，保留了最适合当前阶段的机制：绝对单笔额度、日累计名义金额、订单次数、连续亏损熔断、冷静期，以及交易品种精度和最小订单规则的独立核验。没有迁移连接器规模、真实交易适配器或可绕过风控的开关。
- 新增纯函数 `services/small_capital_trial.py`，固定模式为 `PLAN_ONLY_NO_EXECUTION`。它只消费已经在内存中的行情、前向观察和权限摘要，不访问网络、数据库、运行目录、凭据或签名能力，也不进入 `PaperExecutor`。输出包含稳定 `plan_hash`、缺失证据、下一步和清晰的 `PLANNING_ONLY / NEEDS_EVIDENCE / BLOCK` 状态。
- 规划资金封套固定为 USD 100–200；页面展示的 20% 储备、10% 单笔、40% 日累计名义金额、2% 单日亏损、5% 总回撤停机、最多 2 个仓位、24 小时最多 4 单、连续 2 次亏损停机并冷却 24 小时，均标记为示例护栏，不是收益承诺、投资建议、交易所规则或下单授权。
- 新增独立的 `services/instrument_rules.py`：只调用 OKX 公开 `SPOT instruments`，按标的做 5 分钟内存缓存和同键合并，并严格核对 `instId / instType / state / baseCcy / quoteCcy`。`tickSz`、`lotSz` 与 `minSz` 保留为十进制字符串；`minSz` 明确是基础币最小数量，不冒充最小美元金额。规则内容哈希与抓取快照哈希分离，规则改变会同步改变规划哈希。
- BTC-USDT 的公开烟测返回 `SPOT / live / tick=0.1 / lot=0.00000001 / min=0.00001 BTC`，服务内再次验签为 `PASS`。这些值只记录本次公开证据，代码不会硬编码。股票标的返回 `NOT_APPLICABLE`，不会错误套用 BTC 规则；刷新失败只保留 last-good 为 `STALE`，不会继续标记已验证。
- 只读数量预览已升级为公开卖一参考：行情服务保留 OKX ticker 的原始十进制 `bidPx / askPx / askSz`，只在同一快照内买卖价关系有效、卖一价与卖一量为正、时间新鲜且未发生缓存时间倒退时，才输出 `PUBLIC_BEST_ASK_REFERENCE`。最新成交价继续用于行情展示，但卖一缺失时数量预览会停在 `NEEDS_EVIDENCE`，绝不回退到 last 或客户端 `price`。规划器以整数比值精确决定公开 `lotSz` 步数并向下截断，输出绑定来源、时间、快照 ID、规则哈希与预览哈希；不生成 side、订单类型、`tgtCcy`、订单参数或交易意图。
- 数量预览最高状态仍仅为 `PREVIEW_ONLY`，不是 `PASS/READY`。10/20 USDT 两档按当前一档卖一估算基础币数量，并显示需临时备付的 10.5/21 USDT 规划参考；其中额外 0.5/1 USDT 的 5% 来自 OKX 对市价单风险检查临时冻结的公开说明，明确不是账户余额已核验、手续费、滑点、实际支出或成交保证。切换标的、报价过期、时间倒退或控制中心失败时立即清空旧数量。
- 新增独立 `services/public_order_book.py`，复用现有 OKX 公开 books 路由，固定获取当前标的前 20 档标准非 RPI 买卖盘。它保留价格、基础币数量、交易所时间和 `seqId` 的十进制原文，核对双边排序、非交叉、标的、来源、新鲜度和内容 Hash；安全状态另有完整合同 Hash，单边簿、状态或阻断原因被篡改都不能沿用原 Hash。同标的并发请求合并，后到但时间更旧的缓存响应会被拒绝。REST 没有可用 checksum 或连续消息证明，因此界面明确显示 `checksum=NOT_APPLICABLE`、`complete_book_verified=false`，不把 20 档冒充完整订单簿。
- `small-capital-order-book-impact-v1` 使用精确分数逐档扫描公开卖盘，再按公开 `lotSz` 向下对齐。数量、价格、可见成本和余款使用有限十进制精确输出，只有均价、覆盖率和 bps 是明确限位的显示值。10/20 USDT 两档分别显示可见基础币数量、可见档均价、相对卖一差异、消耗档数和覆盖率；若 20 档不足，`visible_depth_shortfall_quote` 与 lot 向下取整余款分开，并返回 `VISIBLE_DEPTH_CAPACITY_LIMITED`，绝不外推完整成本。该差异只叫“可见档均价较卖一”，不是预计滑点、真实成交价或可执行报价；RPI 资格、隐藏流动性、余额、账户费率、最小成交金额、到达延迟和 USD/USDT 换算继续为 `NOT_CHECKED`。
- 当前整体状态仍为 `NEEDS_EVIDENCE`：账户实际 maker/taker 费率是 OKX 私有、账户特定信息，公开阶段固定 `NOT_CHECKED`；最小报价币成本也保持未知。独立子账户、受限密钥、IP 白名单、禁提现/转账、签名隔离、独立持久熔断、人工复位与对账同样未被猜测为已通过。即使这些证据未来全部通过，最高状态仍只是 `PLANNING_ONLY`，且 `runtime_mutations_allowed=false`、`execution_allowed=false`、`paper_authorized=false`、`live_order_allowed=false`。
- 交易总控“100–200 美元纯规划准备”看板继续只复用现有 `GET /api/platform/control-center`；现在显示 Tick/Lot/最小数量、前 20 档公开卖盘证据、Depth Hash、可见档均价与部分覆盖状态。没有新增前端请求、路由、POST、按钮、输入框、充值链接或订单入口；错标的、过期、坏 Hash、乱序/交叉订单簿或权限字段异常都会失败关闭。
- 本次增量只运行订单簿与小资金规划两个定向模块：13/13 PASS（0.051 秒），六个 Python 文件内存编译、lean market 注册检查和 `app.js` 语法检查 PASS；前一轮 20 项规则/卖一定向检查没有重复运行。真实 OKX 公开烟测返回规则 `PASS`、20 档订单簿及安全合同 Hash `PASS`，10/20 USDT 均被当前可见档位覆盖；同时仍明确 `complete_book_verified=false`、`execution_allowed=false`、`paper_authorized=false`、`live_order_allowed=false`。烟测未读取私有配置、运行库或数据库；没有运行完整回归、旧 K 线重放、浏览器轮巡、模拟授权或实盘。

## 2026-08-10 内容寻址定向验证收据：相同工程上下文不重复执行

- 日常 `run_lean_validation.py` 现在会为确定性检查生成本地 PASS 缓存。复用键同时绑定受控源码、测试、`requirements.txt`、Electron `package.json/package-lock.json`、精确命令与工作目录、Python/Node/npm/依赖指纹和固定只读环境策略；任一输入变化都会形成新键，旧结果不能命中。
- 受控文件清单在任何内容读取前排除 `.env*`、`config.local.json`、`runtime*` 数据、数据库、缓存、日志和截图；Electron JSON 改为仅允许 `package.json` 与 `package-lock.json`。验证子进程不再继承整套宿主环境，只保留 Windows 启动所需的三项系统路径，并把临时目录、只读模式、编码和可执行路径固定下来。
- 默认命中严格一致的 PASS 时标为 `REUSED`；`--fresh` 明确强制真实执行，`--dry-run` 只报告 `WOULD_RUN / WOULD_REUSE` 且完成数为 0、不写收据。输出分别统计 `executed_check_count` 与 `reused_check_count`，不得把“0 项新执行、3 项复用”写成“本轮跑了 3 项”。
- 小型当前基线实测：`python_compile + frontend_syntax + history_concurrency` 首次为 3 项 `EXECUTED`，原样第二次为 0 项新执行、3 项 `REUSED`。收据与 readiness 合同的定向验证为 18/18 PASS（9.958 秒）。本节没有运行 750 项完整回归、浏览器行情验收或旧 K 线重放。
- 正式 readiness 不接受 `REUSED` 冒充当轮验收；确定性工程项必须标为当轮 `EXECUTED`。浏览器与 HTTP 423 证据不可复用，必须绑定当前进程、完整工件内容和 15 分钟时效；验证器默认重读并核对工件。SHA-256 seal 只用于本地一致性检查，不是受保护签名，也不宣称为可独立信任的认证证明。
- 当前 `paper_authorized=false`、`live_order_allowed=false`，实盘永久硬锁没有改变。其后已完成上方的 100–200 美元纯规划看板、完成 K 线水位和 provider 级共享限流；50–100ms 微批仍只在出现真实压力证据后评估。

## 2026-08-10 股票自动刷新去重：同键只执行一次

- 股票图表的降级快照、质量告警、报价联动、Futu 联动和人工刷新已经统一进入同一个刷新协调器。请求身份按 `symbol + bar + session` 规范化；相同身份在途时自动与人工调用共享同一个 Promise，人工操作只能绕过冷却期，不能绕过正在执行的请求。
- 协调器加入成功冷却、失败指数退避和有界结果记录。切换标的、周期或盘段时，旧响应在写入图表前会再次核对当前上下文；同键完整强刷会中止尚未完成的快速预览请求，避免晚到的预览覆盖完整快照。例行行情 GET 固定 `emit=false`，没有新增模拟或实盘写入口。
- 后端对股票快照、单报价和批量报价补齐规范化身份与同代强刷合并；强刷失败保留 last-good，并明确降级为非 `READY`。任何带 `force/emit` 的 API GET 只允许本机客户端与可信本地来源；无 Origin 的跨站浏览器请求会被拒绝，只读实例继续抑制 emit 与持久缓存写入。
- 轻量验证通过：最终前端 lean 档位 4/4 PASS（0.219 秒），Electron `npm.cmd run check` PASS（约 1.2 秒），后端 5 个并发/来源/last-good 定向合同 PASS（0.116 秒），最终 JavaScript 与四个后端文件语法检查 PASS。没有运行 750 项完整回归，也没有重放旧 K 线。
- 新的 8770 隔离只读实例完成 AAPL → NVDA → AAPL 快速切换。采样期间图表始终为 140 根、画布 1021×380，最终活动行、工作流标的、图表标的与 `1Dutc` 周期一致，控制台 `error=0 / warning=0`。上游完整 K 线返回 502 时页面如实显示“快速预览”，没有冒充可信实时行情；条件式“立即刷新”按钮本次未出现，因此没有人为伪造告警状态，人工并发合并由纯协调器合同测试覆盖。
- 只读验收继续报告 `runtime_mutations_allowed=false`、`paper_authorized=false`、`paper_order_allowed=false`、`live_order_allowed=false`、`live_trading_hard_block=true`；`POST /api/paper/arm` 返回 HTTP 423。验收期间临时运行目录只有 PID 标记，SQLite/DB/WAL/SHM 为 0；服务已停止、临时目录已清理，8770 当前离线。
- 其后的“内容寻址定向验证收据”、完成 K 线水位与 provider 级共享限流已经完成，见本文首节；行情侧后续只在真实压力出现后评估微批，不扩大为实盘执行。

## 2026-08-10 增量前向观察看板：只处理新完成 K 线

- 控制中心新增“增量前向观察”全宽看板，将服务、观察器、数据水位和调度拆成独立状态；页面直接显示最新可信完成日线、最后已计入日期、待处理日期、本轮处理数、安全跳过数、下一次检查和暂停原因。缺失证据显示 `UNKNOWN / --`，不再把未知进度冒充为 `0/60` 或 `0/8`。
- 后端新增 `portfolio-forward-dashboard-v1` 只读投影。只有 scheduler、observer、候选、数据修订、ledger audit、readiness 及各自内容哈希相互一致时，才允许显示 `UP_TO_DATE`；时间来自未来、调度过期、持久阻断、候选错配、证据缺失或权限合同异常都会失败关闭。
- 前向状态工件增加整体内容哈希；增量计划绑定 ledger audit 和数据修订证据哈希。自然 observer 默认只处理尚未记录、未分类的新完成日期；历史记录只有显式 `--replay-recorded` 才审计重放，且不会夹带新日期。
- scheduler 的 `--dry-run` 现在会在建目录、加锁、初始化 SQLite 或写状态之前返回，只读取已存在状态并输出计划。空临时目录入口级探针返回 `DRY_RUN_NOT_INSTALLED_OR_NOT_RUN`、进程码 5，且目录前后条目始终为 0；没有创建文件、SQLite、WAL 或 SHM。
- 本轮只运行前向相关定向验证：33/33 PASS，测试体耗时 0.290 秒；五个相关 Python 文件语法检查和 `app.js` JavaScript 语法检查通过。没有重跑 750 项完整回归，也没有重算旧 K 线。
- 新的 8770 只读隔离实例浏览器验收通过：看板正确显示 `BLOCK`、`UNKNOWN`、`--` 与“只读观察 · 模拟未授权 · 实盘永久硬锁”，刷新后状态保持一致，页面无遮挡，控制台 `error=0 / warning=0`。`POST /api/paper/arm` 返回 HTTP 423；探针前后 SQLite 文件均为 0，空集合聚合 SHA-256 均为 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`。
- 该节验收实例已经停止；其后“股票自动刷新去重”“内容寻址定向验证收据”“100–200 美元纯规划准备”、完成 K 线水位与 provider 级共享限流均已完成，见本文更上方章节。微批仍只在真实压力出现后评估；模拟仍未授权，实盘真实下单继续永久硬锁。

## 2026-08-10 行情真值中心：服务在线不再冒充数据 READY

- 控制中心新增“行情真值中心”，按活动标的显示报价源、K 线源、新鲜度、最近完成 K 线和下一步动作。后端 `market-data-truth-v1` 将服务运行状态与数据真实性分离：未观察为 `UNKNOWN`，过期或历史快照为 `STALE`，隔离、未来时间戳、无效完成时间或修订异常为 `BLOCK`；只有来源、时间、完成 K 线和实时合同同时满足才为 `READY`。
- 真值检查只读共享内存，不会为了健康检查主动抓行情。完成 K 线必须显式 `complete=true` 且时间戳为有效正数；周期相关年龄、报价未来偏差、快照年龄和兜底/隔离状态都会参与降级，前后端不再出现“API 先报 READY、界面再自行降级”的分裂语义。
- 前端按 `symbol + bar + session + symbolVersion` 隔离总控请求，写入状态和 DOM 前再次核对当前上下文；控制中心与前向状态由一次请求返回并只渲染一次。缺失或损坏的权限合同默认只读，只有后端明确 `read_only=false`、实盘硬墙存在且 `live_order_allowed=false` 时才恢复模拟变更控件。
- 新的空运行目录可以安全启动只读实例：缺失账本、策略管线、审计和前向数据库会显示 `DATABASE_MISSING / NOT_INITIALIZED / BLOCK`，不会创建 SQLite，也不会让总控 500。只读探针 `POST /api/paper/arm` 返回 HTTP 423，前后 SQLite 文件均为 0。
- 浏览器轻验收：AAPL 在新实例无历史库且上游失败时只保留明确标注的快速预览，真值为 `UNKNOWN`，没有被冒充为可信行情；BTC-USDT 成功显示 OKX 报价源、OKX K 线源、最近完成 K 线和可见非空图表，并在 15 秒快照阈值后自动降为 `STALE`。切回总控后活动标的与真值标的一致，页面无遮挡，控制台 `error=0 / warning=0`。
- 本轮只运行轻量 `market` 档位：5/5 检查 PASS，包含 13 个 Python 合同测试、关键 Python/JavaScript 语法与股票报价守卫，总耗时 1.717 秒。另有缺失只读账本定向测试 1/1 PASS；没有重复运行 750 项完整回归，没有启动正式研究、模拟授权或实盘。
- 该轮行情验收实例已经停止；随后完成的增量前向观察看板与股票刷新去重见本文更上方章节。实盘硬锁仍为代码常量，当前 `paper_authorized=false`、`live_order_allowed=false`。

## 2026-08-10 轻测试、重功能：增量前向观察与优化路线

- 日常工程验证改为按变更范围选择 `run_lean_validation.py` 的 `safety / market / research / frontend / core` 档位；所有档位使用隔离临时 runtime，不读取本地 AI 环境文件，不做 unittest discovery，也不运行正式研究。`core` 本轮实跑 7/7 检查通过，包含 28 个关键 Python 测试及关键语法/股票报价守卫，总耗时 6.856 秒。该结果只代表定向验证，不冒充完整回归。
- 自然前向 observer 已改为增量模式：默认仅计算冻结日后尚未记录、未分类的新完成日期；已记录日期不再重复执行完整前缀回测、相关矩阵和风险计算。只有显式 `--replay-recorded` 才审计重放旧记录，且不会夹带新日期。
- 增量规划在 ledger audit、数据修订证据、日期身份或候选身份异常时失败关闭；输出新增 `incremental_plan` 与 `work_summary`，并继续固定 `observation_only=true`、`simulation_only=true`、`paper_authorized=false`、`live_order_allowed=false`。
- 增量功能相关 26/26 定向测试通过，命令总耗时 0.851 秒；三个变更文件编译通过。本节没有重复运行 750 项完整回归，没有启动正式盲测、模拟盘或实盘。
- 同类项目研究与下一步功能优先级见 `docs/optimization_review_2026-08-10.md`。行情真值中心、增量前向观察看板、股票刷新去重与 100–200 美元纯规划准备均已完成；手续费、品种规则、账户隔离和独立熔断证据仍未齐备，现有实盘硬锁不变。

## 2026-08-10 保存项目 G51 受控收敛：新的唯一开发基线

### 基线结论

- 唯一可写开发目录为 `C:\Users\Administrator\Documents\哈基米v2交易`；`C:\Users\Administrator\Documents\哈基米v2交易-g50-dev` 仅作为 G51 只读参考树。本轮没有修改参考树，也没有从参考树读取或迁移 `.env*`、`config.local.json`、`runtime*`、数据库、缓存、日志、截图、API 密钥或口令。
- 保存项目已经从 G41 系列收敛到“G51 受控能力 + 保存项目安全加固”的新基线。下方 2026-08-04 及更早内容仅是不可变历史记录，其中的旧 PID、8766–8769 服务、`runtime_g50`、`runtime_g51_dev`、截图和报告路径均不是当前运行状态，也没有迁移到保存项目。
- G42 继续只允许自然前向观察，不具备模拟盘或实盘授权。G50 `trend_pullback` 与 G51 `squeeze_breakout` 仍固定为开发期否定结论；禁止沿用旧策略 ID 调参后重跑本代，也没有启动任何正式盲测。

### 分叉核对与非破坏迁移

- 迁移前按 `docs/g51_reconciliation_manifest_2026-08-10.json` 逐项复核：manifest SHA-256 为 `a5f334142f991558de5f0db40e4e4c0df5305f69f37e4636c4f38f0bd28029d5`；80 项差异全部与两树实物一致，其中 G51 新增 26 项、修改 54 项，异常、重复、大小写冲突、不安全路径、重解析点和保护范围命中均为 0。
- 独立重建的受控范围为 `*.py`、`*.js`、`*.css`、`*.html`、`*.md` 与根 `requirements.txt`，排除交接、对账和快照控制工件。迁移前保存项目共 206 项；规范清单为按路径排序的 `path<TAB>bytes<TAB>sha256<LF>`，聚合 SHA-256 为 `b0a0d477c48fbe7eef355e96ea570da29ac79c6cb4732467844ad70e3afb5702`，已保存到 `docs/g51_pre_migration_source_snapshot_2026-08-10.sha256`。
- 80 个 manifest 路径均以单文件为单位审查和收敛，没有整目录覆盖。`docs/project_status.md` 最后处理：先验证并接入 G51 历史，再在顶部合成当前保存项目证据，避免把参考树的旧运行态冒充当前基线。
- 发现并补入一项 manifest 外受控扩展：Electron `outputs/hakimi_trade_electron/package.json` 的 `check` 新增股票报价守卫语法与单测。迁移前文件 SHA-256 为 `69a9b8a0760689a27208ae453f00e38a312b18ba4cb90c5ea6bb67ef690b43d7`，G51/迁移后为 `54770abb4a3adbc2a90cb30cd4ed3edc6294a6b9f7fbd89e6c4eeac86b929296`；补充快照位于 `docs/g51_pre_migration_electron_snapshot_2026-08-10.sha256`。两树 `package-lock.json` 均为 `9687b06eaf7b6ea73881f8bf811ecd7d5e643286a4771c45cf518e6c4e6f9024`，因此未改写。

### 保存项目安全加固

- `config.py` 在 `HAKIMI_SKIP_LOCAL_AI_ENV=1`、`HAKIMI_RUNTIME_READ_ONLY=1` 或测试隔离模式下，会在构造或探测 `.env.local` 路径前直接返回；本轮 Python 回归和验收服务都显式启用跳过标志。测试以“任何 `Path.is_file/read_text` 调用即失败”的方式证明隔离模式不会碰本地 AI 配置。
- `LIVE_TRADING_HARD_BLOCK` 改为不可被环境变量关闭的代码常量 `True`。验收进程故意注入外部 `LIVE_TRADING_HARD_BLOCK=false`，运行态仍报告硬锁开启且 `live_order_allowed=false`。
- `paper_ledger.py` 新增 G41 旧 schema 的纯只读兼容：只执行 `PRAGMA`/`SELECT`，仅允许 `default` 账户，并只在内存中补全旧 payload 的 `account_id`；重复 `risk_request_id`、非默认账户、缺表和不完整 schema 均失败关闭。可写迁移则在同一事务中完整验证并归一旧 payload，失败整体回滚；当前 schema 必须同时具备 v4、`account_id` 与唯一风险请求索引才会报告 `CURRENT`。
- 历史管线绑定授权与当前有效授权已经分离。只读状态即使存在旧的 armed/authorized 记录，对外 `paper_authorized`、`paper_order_allowed` 与 `automated_paper_order_allowed` 仍全部为 `false`；`/api/health` 使用有效风险视图而不是回显历史字段。
- `trend_pullback` 与 `squeeze_breakout` 保留 `backtest_supported=true` 仅供历史证据复算，但 `new_research_allowed=false`。开发研究必须显式提供策略与研究代际；开发矩阵必须显式提供策略；两份预登记入口必须显式提供策略与代际。所有入口都会在载入行情或领取协议前拒绝这两个旧 ID。
- 内部 readiness 不再把任意观察文字包装成 `PASS`：工程证据改为结构化工件，并由验证器重算进程退出码、HTTP 423、三标的浏览器往返、控制台错误数、并发结果和工件 SHA-256；服务 URL、代际、前序报告、工程证据和输出路径全部显式必填，删除 8767/G49 等历史默认。
- `DEV_BASELINE.md` 已改写为当前保存项目说明；G50/G51 研究文档中的开发树 runtime 路径均明确标为未迁移历史引用。

### 自动化验证

- 定向安全与旧 SQLite 兼容回归为 12/12 PASS；策略资格、研究入口与结构化 readiness 定向回归为 48/48 PASS。
- 完整 Python 回归在显式临时 runtime、跳过本地 AI 环境和临时字节码目录下运行：`Ran 750 tests in 261.100s`，结果 `OK`，即 750/750 PASS。参考树冻结记录的 737/737 仅作为历史对照；新增 13 项覆盖来自本轮安全和治理加固。
- `python -m py_compile outputs/python_quant_bot/exchange_terminal/server.py` PASS。
- `node --check outputs/python_quant_bot/exchange_terminal/static/app.js` PASS。
- Electron `npm.cmd run check` PASS，并实际执行 `stock_quote_guard.test.js: PASS`，不是遗漏报价守卫测试的空通过。

### 新只读实例验收

- 新实例仅监听 `127.0.0.1:8765`，显式启用 `HAKIMI_RUNTIME_READ_ONLY=1`、`HAKIMI_SKIP_LOCAL_AI_ENV=1` 与 `PYTHONDONTWRITEBYTECODE=1`。构建状态为 `PASS`，89 个运行加载源与磁盘源指纹一致，均为 `affcd9391ffc460b1638366bff8a8b72e4da0d2d73f19699bfe1119bac89f1ef`，`restart_required=false`。
- `/api/health`、`/api/risk/engine`、`/api/paper/snapshot`、`/api/platform/control-center`、`/api/paper/ledger`、生命周期、审计和策略管线探针均返回成功且语义一致：`read_only=true`、`runtime_mutations_allowed=false`、`paper_authorized=false`、`paper_armed=false`、`paper_order_allowed=false`、`automated_paper_order_allowed=false`、`live_trading_hard_block=true`、`live_order_allowed=false`。旧账本磁盘 schema 为 v2，并被诚实标记为 `LEGACY_READ_ONLY_COMPAT`。
- `POST /api/paper/arm` 返回 HTTP 423；手工模拟订单、停止、重置和策略管线写动作也均为 423。隐藏预热、强制异常刷新和通知等变异探针同样为 423，没有可从 GET/AI/回测绕过只读或风控的入口。
- SQLite 验收只做文件级哈希，不读取业务内容。`runtime` 下数据库主文件及 `-wal/-shm` 边车共 130 项，规范清单共 23,973 字节；启动前、API 探针后、浏览器验收后以及停服后的聚合 SHA-256 始终为 `7f38114ce11a3ed6d2f2aa86ec26b11f698af2912e914fef50fcbaf6c0714d04`。

### 本地浏览器复测

- 使用新的只读实例进入行情工作台，固定 UI 周期 `1Dutc`，再通过搜索框 Enter 依次切换 AAPL、NVDA、BTC-USDT。三次最终态的活动标的、活动行 `aria-pressed`、工作流标的和图表标的全部一致，画布始终为 1021×380；50ms 采样期间可见 K 线最少分别为 160、160、140 根，0 根样本为 0，未出现空图或画布消失。
- AAPL 为 Yahoo 股票日线，合同归一为 `1d`，最终显示上一交易日兜底数据；NVDA 为本地 K 线库 Yahoo 旧缓存，合同归一为 `1d`。两只股票均未显示 OKX 来源。它们的数据新鲜度告警被如实保留，因此本项 PASS 只证明来源、周期、切换和降级合同正确，不把旧数据宣称为可交易实时行情。
- BTC-USDT 保持 `1Dutc`，最终从快速预览回填为 `OKX实时 / 缓存1秒`，可见 140 根、总历史 300 根；标的元数据没有混入 Futu、Yahoo 或 Stooq。报价源与 K 线源分别采证，不强行要求两类来源必须相同。
- 三标的均完成截图目视复核，未发现 K 线消失、错标或异常遮挡；浏览器控制台 `error=0`、`warning=0`。

### 当前边界与下一步

- 验收实例已停止，8765–8769 当前全部离线；本节没有可复用的运行 PID。
- 第一阶段迁移、加固、回归、只读验收和浏览器复测已全部通过。此后只可评估加密历史补齐与下一轮内部回测准备，不得直接启动正式盲测，不得消费新的留出集，也不得为获得正结果降低数据、研究或安全门槛。
- 正式盲测前仍有独立硬阻断：策略矩阵注册表必须增加 research generation、已完成 batch spec 与数据角色/窗口指纹的跨登记去重；历史复算只能走只读 verifier，不能领取新协议。未来 readiness 的数据库证据也必须绑定主文件与 WAL/SHM 的聚合哈希或不可变快照。
- 任何新假设必须使用新策略 ID、实质不同且可证伪的机制、全新事前登记与未消费的数据范围。实盘真实下单继续永久硬锁，AI、回测、模拟和运维入口均无权解除。

### 历史记录（以下内容不代表当前运行状态）

## 2026-08-04 G51：研究准入加固、波动收缩突破否定与浏览器收口
- 完成研究入口和证据链复审：历史中段未完成 K 线现在直接阻断，只有末尾未完成后缀可告警后排除；股票日线使用官方交易所日历校验缺失/意外交易日，组合回测只有在生命周期服务能够解释停牌等事件时才允许显式延后连续性判断。策略矩阵不再预先丢弃坏行，股票 K 线缓存与策略矩阵注册表新增真正的只读查询路径，NaN/Inf 与字符串伪布尔值均失败关闭。
- 开发投影现在会在生成研究单元和快照前物理移除受保护测试段 OHLCV，并重新证明投影后的股票/加密数据；报告验证器会复算变体×标的覆盖、单元哈希、排名、验证候选、冻结候选、测试/留出结果与前向候选，不能再仅靠自报哈希通过。相关定向回归累计 126 项通过，完整 Python 回归为 737/737；`python -m py_compile exchange_terminal/server.py`、`node --check exchange_terminal/static/app.js` 与 Electron `npm.cmd run check` 全部通过。
- 新增事前冻结、仅研究的日线机制 `squeeze_breakout`：先识别 ATR/成交量收缩，再要求前高突破、区间和成交量扩张、趋势保护及最大 ATR 延伸约束；三组固定变体只在 AAPL、NVDA、MSFT、MU、WDC、BTC-USDT 开发宇宙运行，ON/MCHP 保持受保护。预注册文档 `docs/g51_squeeze_breakout_development_preregistration.md` 的 SHA-256 为 `6ad1c860e2e5a5867ca90285d615c8d4ca3f553f5fce4661bc204593a16a6d8c`。
- 唯一开发运行 `runtime_g51_dev/reports/g51_squeeze_breakout_development.json` 语义复核为 `PASS`，但 18/18 选择单元全部 `BLOCK`，三个变体在验证段均为 0 笔成交，验证候选、冻结候选、测试单元和留出单元全部为 0；2578 行持久化研究数据的六个调度测试段计数均为 0，ON/MCHP 从未载入。结论固定为 `FALSIFIED_IN_DEVELOPMENT`，禁止调参后重跑本代，也不具备正式单次盲测资格。
- G51 报告文件 SHA-256 为 `467693d4c6213dafa8017de578ec00759f99fa24f73d44556e606ecb9e2c3e76`；批次运行哈希 `84f05340ffd95db0569460bcbc18cd92ae2a2daffc4384deb51f5f2b296f7da1`、数据清单哈希 `4256a2fe881697ea25ce2ccbd722c14cff04ed2e34675b28f677dad697b96216`、精确快照哈希 `fe9ff9d956c9370dcf24cc477effd06d853fe7f6801c67e38525151bccee5d12`、治理哈希 `b5b935e6ebcefa3fc2abfc61b4ee335a71a6468a48f2e0c4a96076a6830c02de` 均已绑定。
- 最新只读服务运行于 `http://127.0.0.1:8769/`，PID 95360；运行构建为 `PASS`，89 个加载态/磁盘态源文件指纹均为 `0a0e9a8f6f66d124085f18b315ab2f643793cec73edcac1cf8443f5c35a194ce`，无需重启。`runtime_mutations_allowed=false`、`paper_authorized=false`、`paper_armed=false`、`live_trading_hard_block=true`、`live_order_allowed=false`，`POST /api/paper/arm` 返回 HTTP 423。浏览器实测 NVDA、BTC-USDT、AAPL 接受行情约 0.35 秒、2.8 秒、0.31 秒，切换期间 1021x380 K 线画布保持可见，控制台 0 错误；验证截图保存在 `runtime_g51_dev/reports/g51-browser-market.png` 与 `g51-browser-aapl-chart.png`。14 个只读 SQLite 主/边车文件在全部核验后聚合哈希仍为 `0c11f318c4b848783796f930723ca19d38187199335bbbf4cef4142cef8f497e`。
- 原 8768 G50 进程未停止、未重启，但因同一源码树已进入 G51，其加载指纹仍为 `e9fdb0a9...`、磁盘指纹为 `0a0e9a8f...`，现正确报告 `RESTART_REQUIRED`，由 8769 取代为本轮验收实例。下一步不得微调 `trend_pullback` 或 `squeeze_breakout`，也不得启动正式盲测；应继续观察 G42 的自然前向证据，或在新协议和新数据范围下提出机制实质不同、可证伪且事前冻结的新假设。

## 2026-08-04 G50：首个日线假设否定、K 线切换修复与真实只读运行时
- 首个独立日线趋势回调假设已在开发样本中被否定，结论为 `FALSIFIED_IN_DEVELOPMENT`，没有调参、没有启动正式单次协议，也没有读取 ON/MCHP 留出数据。六个测试标的仅 BTC-USDT 测试超额为正，测试段总成交 12 笔，中位测试收益 -0.965%、中位测试超额 -4.93%；负面工件 `runtime_g50/reports/g50_trend_pullback_development_falsification.json` 的规范工件哈希为 `f4e9d239910a0e7879bf703418350530cbaa7cf46b545b0ab7780aca72068b38`。该策略不得作为候选继续推进。
- 新增单次研究治理链：`run_internal_strategy_research.py` 默认只允许 `DEVELOPMENT_ONLY`，`run_preregister_strategy_research.py` 的 `BLIND_ONCE` 必须先冻结假设、参数、选择宇宙和源码声明，再在测试门槛通过后才允许读取预留数据；`services/strategy_research_evidence.py` 与 `verify_strategy_research_report.py` 提供机器可复算证据。ON/MCHP 仍保持未暴露，不为得到正结果而消耗留出集。
- 修复股票切换时旧报价污染新 K 线的问题。此前 AAPL 离线预览价 195 会改写真实 Futu 最后一根约 309 的 K 线，随后真实报价又被错误拒绝。现由 `static/stock_quote_guard.js` 独立校验报价来源、新鲜度、隔离态及涨跌幅一致性；图表载入不再用列表报价改写蜡烛，报价证据原子更新，已有真实图表时低质量预览也不能覆盖顶部价格。浏览器复测 NVDA 与 AAPL 均约 0.9 秒完成稳定切换，画布 1021x380、K 线非空且 AAPL 不再出现 195 异常长影线，控制台无 warning/error。
- 修复“只读运行时仍在启动时写 SQLite”的系统性缺陷。新增 `services/sqlite_runtime.py`，只读连接统一使用 `mode=ro&immutable=1` 与 `PRAGMA query_only=ON`，九个账本/流水线服务在只读模式跳过建表与迁移并在变异前失败关闭；`server.py` 同时跳过模拟账本迁移、对账和组合初始化。正确运行目录 `outputs/python_quant_bot/runtime_g50` 的 14 个 SQLite 主文件/边车文件在启动、轮询、浏览器切换和完整测试前后保持字节级不变，聚合哈希始终为 `0c11f318c4b848783796f930723ca19d38187199335bbbf4cef4142cef8f497e`。
- 最终完整 Python 回归为 724/724；相关 Python `py_compile`、`node --check`（`app.js`、图表控制器、图表质量与报价守卫）、报价守卫单元测试及 Electron `npm.cmd run check` 全部通过。
- 当前 G50 只读服务运行于 `http://127.0.0.1:8768/`，PID 80036，构建为 `PASS`，89 个加载态/磁盘态源文件指纹均为 `e9fdb0a9ce9089a62cbf8ac73fb3aa4df52f04ff59249aeed8c95f2930a4e683`，无需重启。`runtime_mutations_allowed=false`、`paper_authorized=false`、`paper_armed=false`、`live_trading_hard_block=true`、`live_order_allowed=false`，`POST /api/paper/arm` 返回 HTTP 423。
- 下一步不能继续微调已失败的 `trend_pullback`。新的研究必须提出实质不同、可证伪且事前注册的日线波段假设；同时统一加密历史缓存仍只有 BTC-USDT 为 `READY`，其余 9 个币种须先在隔离可写环境完成历史、完成态和血缘复核。

## 2026-08-03 G49：统一加密历史、切换交互收口与下一轮回测准备门禁
- 新增统一历史服务 `services/market_history_store.py`，合同为 `market-history-store-v2`。OKX 日线分页统一使用 `after` 游标并保留 history/market 降级证据；所有入库行先经过有限数值、OHLC 包络、UTC 日期、秒/毫秒时间戳及 `complete/confirm/confirmed/provisional` 完成态校验。完成 K 线不会被未完成行或低优先级来源回退覆盖，SQLite 使用 WAL、进程内写锁、修订账本和内容寻址清单；只读运行时、损坏数据库和阻断缓存均失败关闭。
- `server.py` 的历史回填、缓存统计、BTC 外部历史合并和回测数据读取已统一委托给该服务。回测只消费完成 K 线，跨源合并保护完成态；加密数据证据在日历对齐后的实际使用行集上重新生成并绑定来源、缓存准入、行数和数据哈希。直接复核 BTC-USDT 得到 780 根完成日线、未完成 0、约 121ms、上游 OKX 调用 0，修复了旧数据、重复刷新、当前未完成日线进入回测及低优先级覆盖问题。
- 数据可靠性回归新增完成态字符串/数值、NaN/Inf、错误 OHLC、日期不一致、损坏数据库、只读建库拒绝、来源优先级、合并保护、缓存阻断、数据血缘、幂等清单和并发写入测试。完整 Python 回归现为 703/703；并发写入定向回归重复 20/20；相关 Python `py_compile`、`node --check exchange_terminal/static/app.js` 和 Electron `npm.cmd run check` 全部通过。
- 市场列表交互改为原生可聚焦按钮，补齐 `aria-label`、`aria-pressed`、键盘焦点和稳定尺寸。最终浏览器通过搜索回车完成 NVDA -> BTC-USDT -> AAPL 切换，BTC 和 AAPL 分别约 1.316 秒与 1.320 秒，三张日线图均非空，股票/Futu 与币种/OKX 来源、报价和标的一致，页面诊断日志为 0；主图视觉检查未见遮挡或错图。
- 最终只读服务运行于 `http://127.0.0.1:8767/`，PID 110328，运行构建为 `PASS`，87 个加载态/磁盘态源文件指纹均为 `3ae1946d5616f15a718ae3e4d2be46f962c08df55de52cf0395bd0b21f3f414b`，无需重启。`POST /api/paper/arm` 返回 HTTP 423 `runtime is read-only`；`runtime_mutations_allowed=false`、`paper_authorized=false`、`paper_armed=false`、`live_trading_hard_block=true`、`live_order_allowed=false`。原 8765 主服务只做健康 GET，仍为 `PASS`，未被改动或重启。
- 新增机器可校验的准备清单 `runtime_g47/reports/internal_backtest_readiness_g49.json`。文件 SHA-256 为 `fbd16108f9fd5aa20bea8836c9da0fff4575d75a2eea5b68277b959a24cea1d5`，准备哈希为 `987658ece813e55b8218c670a7d12cbc9fe580fb4f9aaecb130df1c9f936955a`，文件、缓存和自身复核均为 `PASS`。它把 G48 原始负面报告 `69eba4d53ad5cdd6a8e36fce163aaf3788e65b16398cf30313d68dcfe75f5d2b` 绑定为 `NO_CANDIDATE_CONFIRMED`，没有改写、重封装或重跑 G48。
- 准备结论严格为 `READY_FOR_PREREGISTRATION`，不是正式回测许可。当前历史缓存为 `READY 1 / PARTIAL 0 / MISSING 9 / BLOCK 0`，只有 BTC-USDT 可进入未来已预注册的数据范围；其余币种需先在隔离可写运行时完成缓存与血缘复核。下一次正式实验仍因“新研究问题未冻结、新选择宇宙未冻结、新留出集未做事前暴露审计、单次协议未注册”而 `BLOCKED_PENDING_PREREGISTRATION`；`formal_run_allowed=false`，禁止读取新留出数据、重复测试 G48 或获得任何模拟/实盘权限。

## 2026-08-03 G47/G48：策略矩阵单次盲测、异步交易日对齐与否定证据闭环
- 新增 `strategy-matrix-protocol-v2`：批次参数、实现清单、71 个源码文件的完整快照、外部时钟、未见标的暴露检查和绝对注册表路径在读取行情前冻结；SQLite 注册表使用哈希链和 `REGISTERED -> RUNNING -> COMPLETED` 单向状态机，并在领取、完成和历史审计时复核严格布尔权限、时间顺序、源码、数据清单及结果哈希。正式批次只能领取一次，任何命令行策略、标的或风险参数覆盖都会在读取行情前被拒绝。
- G47 正式批次 `smx-1785762883036-952e60e8fc82` 保留为有效的负面工程证据：注册、领取、完成和治理链均为 `PASS`，但旧日线对齐要求股票和加密货币第一根 K 线日期完全相同，BTC 周六起点与美股周一起点触发 `missing_common_start`，因此选择门禁正确阻断且没有策略单元运行。该报告没有被覆盖或重用。
- 日线批量对齐升级为 `daily-batch-alignment-v2`：初始窗口允许受限的周末/节假日异步起点，先求有效公共窗口再裁剪；确认阶段的冻结边界仍严格一致，起点偏差最多 7 天、终点偏差最多 3 天。修复后 AAPL/NVDA/MSFT/MU/WDC 各 532 根、BTC-USDT 775 根完成日线统一到 `2024-06-17 -> 2026-07-31`，六份清单、五份股票修订证据、日历计划、市场状态和相关性门禁均为 `PASS`。
- G48 在读取 ANET/MRVL 前完成唯一预注册：注册号 `smx-1785763740005-a6fda47ad092`，协议哈希 `92d3a3439a99da4dfea63db6a6b00e26322f310152f45cd66eae6721ab37f99f`，冻结批次哈希 `a6fda47ad09204531942bef5ef4147cc10158ad21bca8825332fa07599cdca18`，当时实现指纹 `bbceb9e1b462b60135c7abf2aede22299bf5bdd84c276d909b933c69392910c0`。领取前注册表、当前源码、源码快照和 ANET/MRVL 零暴露检查全部为 `PASS`，模拟与实盘权限均为关闭。
- 唯一正式报告 `runtime_g47/reports/strategy_matrix_g48_formal_blind_2.json` 已完成且注册状态为 `COMPLETED`。9 个策略乘 6 个选择标的共 54 个单元全部计算，但 0 个策略满足冻结的跨标的稳健性与多重试验门槛，所以没有读取 ANET/MRVL、没有确认单元、没有前向候选，也没有为了得到正结果而降低门槛或重跑。最高排名的 Bollinger 仍因仅 2/4 时序通过、3/4 验证为正、3/4 测试超额为正、中位测试超额和多重试验调整分数不为正而 `BLOCK`。
- G48 文件 SHA-256 为 `69eba4d53ad5cdd6a8e36fce163aaf3788e65b16398cf30313d68dcfe75f5d2b`；数据清单哈希 `f3e2f4d404fdd7a7b2095c5bf6c5a463ebe7949ec4bf2e8e6a02d8534c06d7a7`、精确数据快照哈希 `dc59b236c8103fc46dd4ce1bdff068fef6c948e8ed4fb8ba61072b6f8a0bd5ce`、结果哈希 `00dde786d3ea5c0d341994b2e582e64e0debf1ae6a830471658521eeec7c5204`、运行哈希 `3c9afbea4dc13e6d6c101cde8117d34cd42db2c423804d180a42b6bde854f1df`、治理哈希 `a1005d8418485bcf10771f9301d22bad20f6e65aade4895d7619ef9c7ac069a8` 均可复算；注册表审计、治理审计、完成结果绑定和 3435 行精确数据快照复核均为 `PASS`。结论是“当前九类规则策略没有获得未见集确认资格”，不是运行失败，也不是胜率或收益保证。
- 事后审计发现负面报告的 `confirmation_regime_evidence=NOT_RUN` 分支曾写入空哈希，导致通用候选证据验证器多报 `confirmation_regime_evidence_hash_mismatch`。已为未来所有 `NOT_RUN/BLOCK` 市场状态和相关性证据增加可复算哈希，并在摘要显式写入 `research_only=true`；G48 正式报告保持不可变，没有事后重封装。新增回归后完整 Python 测试为 682/682，`py_compile`、`node --check exchange_terminal/static/app.js` 和 Electron `npm.cmd run check` 全部通过。
- 最新隔离只读服务运行于 `http://127.0.0.1:8767/`，运行构建为 `PASS`，85 个加载态/磁盘态源文件指纹均为 `2feaa93ee2ac8fcc03fe3ae94b5de1bd0440a84f0144669c12467d0135d2ac3d`，`source_changed_after_start=false`、`restart_required=false`、`runtime_mutations_allowed=false`、`paper_authorized=false`、`live_trading_hard_block=true`、`live_order_allowed=false`。浏览器实测 `AAPL -> NVDA -> BTC-USDT -> AAPL` 均在约 1.9-2.2 秒内稳定显示 1021x380 非空 K 线，报价、标的和来源同步，无 warning/error；回测冻结、策略启停、模拟买卖、平仓和条件单均禁用并标注只读。

## 2026-08-03 G46：运行时授权语义、标的切换与内部回测证据闭环
- G45 的全部只读变异探针为 78/78 通过，987 个非日志运行文件在测试前后零变化；但风险中心曾把“风控规则允许模拟”展示成“当前模拟执行允许”。后台并未放行订单，但该语义会误导用户，因此 G45 已按 `RUNTIME_AUTHORIZATION_SEMANTICS_MISLEADING` 退役。失效包 `internal_portfolio_backtest_pack_g45_runtime_authorization_semantics_invalidated.json` 的包哈希为 `b0fc73902aea51691f313b1a85e3eac68fe3528ccaf95bd98a3bdfdd1da2a67b`，退役收据哈希为 `4218553faeb58fe155d0a913a83c75fe3364b05f8a4bf64756be96c498dafe96`；没有迁移观察、收益或调仓样本。
- G46 将“风险策略通过”“运行时允许写入”“人工模拟可用”“策略模拟已绑定”“实盘允许”拆成独立字段。只读运行时公共预交易结果失败关闭，自动模拟必须绑定当前账户精确授权的策略流水线；当前界面和 API 均为 `RUNTIME_READ_ONLY`，`risk_policy_allows_paper=true` 只代表规则层结果，`paper_order_allowed=false`、`automated_paper_order_allowed=false`、`paper_authorized=false`、`paper_armed=false`、`live_order_allowed=false`。
- 顶部标的搜索补齐键盘提交：完整代码、完整名称或唯一匹配时按 Enter 立即切换，切换后清空过滤并恢复市场列表，Esc 清空搜索。最终浏览器实测 `AAPL -> NVDA -> BTC-USDT -> AAPL` 的标的切换约 0.11-0.13 秒、含图表稳定等待约 0.55-0.60 秒；股票分时约 0.3 秒进入图表，BTC 1 分钟首次实时确认约 3.1 秒且等待期间保留非空预览。股票与币种 K 线均为 1021x380、报价/周期/数据源同步更新，控制台无 warning/error。
- 完整 Python 回归为 655/655；相关 `py_compile`、`node --check exchange_terminal/static/app.js` 和 Electron `npm.cmd run check` 全部通过。最终 8766 服务的运行构建为 `PASS`，83 个加载态/磁盘态运行源文件指纹均为 `ba2fa34b9133d1e80f2b0c7f0878dd7cbceda270a570044ed64d833c6d887d6b`，`source_changed_after_start=false`、`restart_required=false`。已知模拟写接口在只读模式返回 HTTP 423。
- G46 唯一预注册实验为 `pexp-1785753062753-2353412c5fd7`，协议哈希 `4f997f80a36b2db143b36f6853ef6afa7da19608b44ad1d41f7cf657e7ccdf9c`，108 文件研究实现指纹 `2b69332317d91b49b777bc50b644e1112160e4dbc8609d103e3bc13d57d0ebc4`。冻结候选哈希为 `63c50c4edc179cf8d9b2c7c5f6d28d7e741f9c6186b4343c0bca3e6d34e94a1f`，研究批次哈希为 `1e4fcaae18e6698d1246c8f11670bcada5a14971b3074575a864e6ebac2b1593`；策略、标的池、窗口、成本、风险预算和晋级阈值均未相对 G45 改动。
- 历史结果保持不变：验证收益/最大回撤/Sharpe 为 35.8862% / 4.0415% / 3.7788；测试收益 7.4126%、相对 SPY 超额 2.4426%、最大回撤 6.6002%、Sharpe 0.9559；严重成本压力收益 6.9762%。结论仍为 `PROMISING_NEEDS_FRESH_HOLDOUT`，不得解释为稳定胜率。
- 鲁棒性为 `ROBUSTNESS_PASS`，哈希 `7d50fc3d26227e8bbf0f9d56f898512038655ce600b0905a001a6fe3cbfc0ad1`：7/7 参数邻域为正、13 个逐标的消融中 12 个为正、10 万/100 万/1000 万三档资金均为正且无部分成交。隔离执行演练的验证/测试/全段 55/36/123 笔订单全部通过风险、组合风险、生命周期、结算和事件血缘，工件哈希 `f436edad8eb3e8ff0ec36c894008bd12418e6fc786377a7bebd81bef3fe7ff8a`。
- 激活绑定后的统计审计完整性为 `PASS`，但结论正确保持 `BLOCK / INSUFFICIENT_STATISTICAL_PROMOTION_EVIDENCE`，审计哈希 `1a7a6cdbc21e6aa69d14c3f2ed521deaa9db118d046a31e9ff8c846ffe8dc612`、工件哈希 `9bc076e1cc1556a7bea5200f2ae454af49a68025fb7b5eb70075145f37964612`。测试段正超额概率约 58.82%，选择修正后为 0，信息比率概率和区间下界未通过；重复回放不能消除该阻断。
- 数据准入 `portfolio_data_admission_g46_runtime_authorization_semantics_final.json` 的审计哈希为 `9669ad339dcc6d9a0ecfb116c7e7ee61220a3f0aa9000d0822cbd99090c42dff`：内部研究为 `READY_WITH_LIMITATIONS`，模拟和实盘均为 `BLOCK`。14 个标的证据合同可用于内部研究，但历史时点化标的池、权威公司行动主数据和供应商许可/限流审查仍是外部门槛。
- 最终只读包 `internal_portfolio_backtest_pack_g46_runtime_authorization_semantics_final.json` 为 `INTERNAL_BACKTEST_EVIDENCE_READY / promotion BLOCK`，包哈希 `fa2577020a15e05cb382b0f7d39df8e840e68bfeed19d784a67155903158b3f8`，自校验为 `PASS`。3 次隔离回放战役 `ibc-1785753647355-63c50c4edc17` 全部通过，唯一回放哈希 `3409f5887cafaa24eccd830cdde1407471fe42737754ba883468c67acb76da08`，战役哈希 `6eef8c77691a45db62004d140bb5ebcc3130777c514cc2354b1bdf9bd8b73c46`；网络、数据库、开发试验、独立样本和前向样本增量均为 0，结论严格为 `REPRODUCIBILITY_PASS_NOT_PROMOTION_EVIDENCE`。
- 最新不可变归档为 `portfolio-forward-1785753958455-63c50c4edc17-3235ee4763c1`，清单哈希 `3235ee4763c1697f6b94f5f4d3982c05d0967edaa0d77f0b857147c3a85c6734`，恢复验证为 `PASS`。`HakimiTradeV2-G46-*` 的观察、绩效、备份和看门任务均已安装；观察、绩效、备份实跑返回码为 0，看门状态为 `PASS`、阻断数为 0，G45 同名任务继续禁用。
- G46 前向状态严格从零开始：2026-07-31 仅登记为 `PRE_ACTIVATION_SKIPPED`，自然观察 0/60、外部时钟观察 0/60、前向收益期 0/60、实际调仓 0/8，没有回填或迁移。当前只是“内部回测证据就绪”，不是模拟盘授权；真实下单硬墙继续永久锁定。

## 2026-08-03 G41 后续：历史时点标的池与公司行动证据入口
- 新增独立研究工具 `portfolio_reference_data.py` 与 `run_portfolio_reference_data_intake.py`，没有改动 G41 登记的策略、回测、执行或数据合同文件。当前实现指纹仍为 `38610df1cc8b1c60444f348c9f46edda9fd1415931c7ef12524afdba48988dd7`，与 G41 登记值完全一致；后端运行构建状态为 `PASS`、无需重启。
- 入口接受两类 UTF-8 JSON 原始资料：历史成员记录 `point-in-time-membership-source-v1`，以及公司行动/证券生命周期记录 `official-corporate-action-source-v1`。每份资料必须位于导入包目录内、使用相对路径、绑定真实文件 SHA-256，并满足来源类别、发布时间、提取时间、观察时间和覆盖窗口合同。
- 验证器不会只相信报告里的哈希字段：导入前必须重新打开原始文件、重算真实哈希，并从原始记录重建成员合同、拆股、分红、停牌和退市事件。原始文件缺失、路径逃逸、内容变化、时间穿越、非权威来源、覆盖缺口或同时重封记录与包哈希都会失败关闭。
- 本地证据库 `runtime/reference_data/portfolio_reference_data.sqlite` 已建立，schema 为 `portfolio-reference-data-store-v1`。数据库只保存证据包、标准化记录和来源元数据，不复制原始来源文件；当前真实导入数量保持 0，避免把测试夹具或模板伪装成权威数据。
- 已从活动 G41 候选生成 `runtime/reference_data/g41_reference_data_intake.json`，绑定 14 个数据集标的及 `2024-07-05` 至 `2026-07-30` 窗口。诊断工件 `portfolio_reference_data_g41_intake_diagnostic.json` 正确保持 `BLOCK`，主要缺口是未替换事前选择规则、历史成员来源为空、公司行动来源为空及 14/14 标的缺少完整覆盖。
- 官方来源评估已落地到 `docs/reference_data_source_options_2026-08-03.md`：美股首选 Nasdaq Daily List 与 NYSE Market Event Feed/Corporate Actions，港股首选 HKEX Data Marketplace 的每日证券属性文件并以 HKEXnews 做事件交叉核验；SEC EDGAR 仅作为发行人和申报交叉核验。所有正式来源都需先确认报价、内部存储权和许可，不自动购买或抓取受限文件。
- 新增 10 个测试，覆盖正常导入、SQLite 幂等、哈希不匹配、路径逃逸、非权威来源、未来观察、覆盖不足、重新封装篡改、公司行动替换和原始文件缺失。完整回归现为 614/614；Python 编译、前端 `node --check` 和 Electron `npm.cmd run check` 全部通过。
- 该入口通过后也只会得到 `REFERENCE_EVIDENCE_READY_FOR_MANUAL_REVIEW`；来源身份、许可、存储权、限流和人工复核仍是独立门槛，`paper_authorized=false`、`live_order_allowed=false` 保持不变。操作说明见 `docs/portfolio_reference_data_intake.md`。

## 2026-08-03 G41 运行构建一致性、桌面旧后端阻断与内部回测闭环
- 桌面壳此前只凭健康接口可访问就接受后端，导致旧 Python 进程仍占用 8765 端口时加载旧代码、旧 K 线和旧接口。现已增加 `hakimi-runtime-build-v1` 构建合同、加载态/磁盘态实现指纹、源文件计数、重启需求和模拟/实盘权限字段；Electron 启动门禁会拒绝缺少合同、指纹漂移或权限异常的后端。实测定位并停止旧 PID 25000，当前后端 PID 81120 的健康检查为 `PASS`，加载态与磁盘态指纹一致，`restart_required=false`。
- G40 因运行合同实现改变而按规则退役，没有迁移前向样本。G41 `PORTFOLIO_G41_RUNTIME_BUILD_AND_DESKTOP_PROCESS_COHERENCE` 在运行研究前完成唯一预注册，实验 `pexp-1785730150781-bc0684256e4a`，协议哈希 `db010614e2701d5574dc28897a4dfe3a9a73ae62b75ba17666a03c0251ea2517`，实现指纹 `38610df1cc8b1c60444f348c9f46edda9fd1415931c7ef12524afdba48988dd7`。
- G41 候选哈希 `bb9d27342dd3763b3d921d15928114c1aa8fe93b30010bcaada94b3b0bde73ed`，批次哈希 `101a7218ab1a35736365d3d463e776e0798f4c83962fe3645c548a32a5b5a522`，数据集哈希 `32d6065332945976e6c96e989d2d3f5ef91078e6fb0c84e07a99c8dcb96e31a1`。验证收益/最大回撤/Sharpe 为 35.8862% / 4.0415% / 3.7788；测试收益 7.4126%，相对基准超额 2.4426%，最大回撤 6.6002%，Sharpe 0.9559；严重成本收益 6.9762%。结论仍为 `PROMISING_NEEDS_FRESH_HOLDOUT`。
- 鲁棒性为 `ROBUSTNESS_PASS`：7/7 参数邻域为正、13 个逐标的消融中 12 个为正、10 万/100 万/1000 万三档容量均为正。隔离执行演练的验证/测试/全段 55/36/123 笔订单全部通过风险、组合风险、生命周期和血缘检查；`research_only=true`、`paper_authorized=false`、`live_order_allowed=false`。
- 激活绑定后的统计审计工件自校验通过，但晋级结论保持 `BLOCK / INSUFFICIENT_STATISTICAL_PROMOTION_EVIDENCE`。验证段 130 个观测通过；测试段 130 个观测的正超额概率仅 0.5908，选择修正后为 0，区间和信息比率检查不足。不得将开发回测解释为稳定胜率。
- 数据准入 `portfolio_data_admission_g41_runtime_build_and_desktop_process_coherence_final.json` 为 `READY_WITH_LIMITATIONS` 且自校验 `PASS`：14/14 标的复权、修订账本、跨源完整性和近期独立重叠通过；模拟与实盘继续 `BLOCK`。剩余外部门槛是历史时点化标的池、权威公司行动主数据以及供应商许可与限流审批，幸存者偏差仍为 `UNCONTROLLED`。
- 最终内部包 `internal_portfolio_backtest_pack_g41_runtime_build_and_desktop_process_coherence_final.json` 为 `INTERNAL_BACKTEST_EVIDENCE_READY`，包哈希 `61dd9755e4e2a3c5377916198c4b4255e4913828c1d7e2ff2d4989aa9c4aaa48`。不可变归档恢复校验通过；隔离回放战役 `ibc-1785730707550-bb9d27342dd3` 为 3/3 通过，唯一回放哈希 `a24518a808ab00ea33f9a37b67c42412334d8d5d05919126212587b74da120e9`，网络、数据库、开发试验、独立样本和前向样本增量全部为 0，结论严格为 `REPRODUCIBILITY_PASS_NOT_PROMOTION_EVIDENCE`。
- G41 前向观察保持真实零基线：自然观察 0/60、外部证明 0/60、实际调仓 0/8，状态 `COLLECTING`，没有回填、补录或迁移。观察、绩效和备份三个计划任务均启用且最近结果为 0，调度器和看门狗为 `PASS`。
- 最终回归为 604/604；`python -m py_compile exchange_terminal/server.py`、`node --check exchange_terminal/static/app.js`、Electron `npm.cmd run check` 全部通过。浏览器实测 `AAPL -> NVDA -> BTC-USDT -> AAPL` 均在约 1.5 秒完成切换，520/520/300/520 根日线、报价和非空 K 线同步更新，控制台无 warning/error。当前结论是“内部回测证据已就绪”，不是模拟盘或实盘授权。

## 2026-08-03 G40 共享别名安全证据包、数据集血缘与内部回测就绪
- 股票数据合同已完成查询窗口语义收口：完整相同窗口记为 `WINDOW_UNCHANGED / PASS`，真实窄子集只记为 `WINDOW_SUBSET_IGNORED / REVIEW`，无法解释的历史删除继续阻断。最终 v9 审计 `stock_data_audit_g39_preprotocol_v9_final.json` 为 14/14 `PASS`，报告哈希 `fbcca5efee35b0878cb42046604e8305bc63a0586da304ac3a2e53343051f314`；研究报告现把实验级数据集血缘绑定到同一批次，前端、策略、统计和回放不再各自猜测数据版本。
- G39 在报告装配阶段被证据包正确拒绝并正式 `ABORTED`，原因是 Python 共享对象别名被第一次压缩成引用后，第二条路径被误判为外部预置引用；没有生成候选、没有激活、没有迁移任何前向样本。修复后的 v9 打包器只接受本次打包过程自己创建的引用，仍拒绝无证据包的预置引用，并在展开时按持久化 JSON 语义解除对象别名。真实报告诊断 `portfolio_evidence_bundle_diagnostic_g40_shared_alias_fixed.json` 为 `PASS`，28 个内容寻址条目、56 个引用，体积减少 85.20%。
- G40 `PORTFOLIO_G40_SHARED_ALIAS_SAFE_EVIDENCE_AND_DATASET_LINEAGE` 在研究前预注册为实验 `pexp-1785727810789-6e51a54999fc`，协议哈希 `2b1efd44c76915d0c3d715170939c0e86c8754713ae84e19d55298c662db7ee3`，实现指纹 `6fffdeb1c7f5d873a984f2381a7c650847c0ae16b9b9e9ca01dd16c4f63f95d7`。本代没有改变策略、标的池、窗口、成本、风险预算或晋级阈值，只修复证据装配和数据血缘，并显式绑定已中止的 G39。
- G40 研究批次哈希为 `a941d9ec9e634d308403a6d037be889dab0b5291e0b848c41d874d44ebf02f1b`，数据哈希 `8490abf6ee775d555be8097c37e3b93b6ce205f6cc03eb98e7eae6bd47cf82e1`，活动研究候选哈希 `599043be04bd217d842099b5153a668c1489567c88e5610c34d170f52e2de90e`。验证收益/最大回撤/Sharpe 为 35.8862% / 4.0415% / 3.7788，测试为 7.4126% / 6.6002% / 0.9559，严重成本收益为 6.9762%；与 G38 一致，结论仍为 `PROMISING_NEEDS_FRESH_HOLDOUT`，不构成模拟或实盘授权。
- 鲁棒性为 `ROBUSTNESS_PASS`：7/7 参数邻域为正、13 个逐标的消融中 12 个为正、10 万/100 万/1000 万三档容量为正且无部分成交。隔离执行演练验证/测试/全段 55/36/123 笔全部通过风险、生命周期和数据血缘检查，工件哈希 `e45e02a4f5f6f7ab7b8b43cdf442acf92fc0b1388465a7f4d6ef29527e5296eb`。
- 激活绑定后的统计审计语义复算与工件完整性均为 `PASS`，但结论保持 `BLOCK / INSUFFICIENT_STATISTICAL_PROMOTION_EVIDENCE`，审计哈希 `dd52a112e00f348c2c3fd2dc8d8437ca5be60e76c2c3df0ad5ec3c2a94f4e1c1`。验证段通过；测试段的正超额概率、信息比率概率、选择修正概率和区间下界不足，禁止把开发回测包装成稳定收益。
- 最新数据准入 `portfolio_data_admission_g40_shared_alias_safe_evidence_and_dataset_lineage_final.json` 自校验为 `PASS`：14/14 标的复权、修订账本、跨源完整性和近期独立重叠均通过；内部研究为 `READY_WITH_LIMITATIONS`，模拟和实盘仍为 `BLOCK`。外部门槛是历史时点化标的池、权威公司行动主数据、供应商许可与限流审批；当前幸存者偏差状态仍为 `UNCONTROLLED`。
- 最终只读包 `internal_portfolio_backtest_pack_g40_shared_alias_safe_evidence_and_dataset_lineage_final.json` 为 `INTERNAL_BACKTEST_EVIDENCE_READY`、自校验 `PASS`，包哈希 `b9af903ccf2660ce1f6df6a65b3f7774d9cfb3c0730d528d5fd6520ebc193e7f`。不可变归档 `portfolio-forward-1785728227561-599043be04bd-2fea144c773a` 恢复校验为 `PASS`；回放战役 `ibc-1785728305161-599043be04bd` 为 3/3 通过且唯一回放哈希 `5901793a132bb0dd22cc96dd8c0c38ff56c51f31e23e2f3b386495be8310b82c`，网络、数据库、开发试验、独立样本和前向样本增量全部为 0，结论严格为 `REPRODUCIBILITY_PASS_NOT_PROMOTION_EVIDENCE`。
- G40 前向链已经建立真实零样本基线并保持 `COLLECTING`：自然观察 0/60、外部结果 0/60、实际调仓 0/8，只有中性的 `PRE_ACTIVATION_SKIPPED`；调度器健康为 `PASS`。不得迁移、补录或回填旧候选样本；`research_only=true`、`paper_authorized=false`、`live_order_allowed=false`。
- 最终完整 Python 回归为 601/601；相关 `py_compile`、`node --check exchange_terminal/static/app.js` 和 Electron `npm.cmd run check` 全部通过。本地服务首页复测约 6-11ms、健康接口约 8-11ms、完整前向状态接口约 0.31-0.39s；浏览器实测 `AAPL -> BTC-USDT -> NVDA` 切换约 0.72 秒，标的、报价、数据源和 1021x380 K 线同步更新，图表蜡烛/均线/布林带/成交量非空，白色主题无黑色残留，控制台无 warning/error。

## 2026-08-03 G38 证据内容与当前时间绑定、内部回测战役基线
- G37 后续对抗测试确认四条证据链仍可被“只替换结论再重算普通哈希”绕过：跨源行情、历史时点化标的池、权威公司行动和供应商审批。G37 候选 `b95c647aba29bb7a1ae280e0deeccf68d1426da7e437437201e4a9e0f8cb3de5` 在自然观察、收益期和调仓均为 0 时退役；失效包 `internal_portfolio_backtest_pack_g37_evidence_claim_substitution_invalidated.json` 自校验为 `PASS`，退役收据哈希 `de6a647f4bacb1c5a3f80b1e4aaa692c0a5321bd18658a841ce14b19c63f9de4`，没有迁移或回填旧样本。
- 四条语义证据合同已经改为内容绑定并在验证端重建：行情修订账本 v7 把主副源完整快照纳入跨源证据；标的池 v4 强制成员来源证据包；公司行动账本 v5/权威证明 v2 强制来源内容；供应商治理 v2 把条款、配额、复核人、审批收据和当前验证时间共同绑定。修复后对抗诊断 `portfolio_evidence_claim_substitution_diagnostic_g37_postfix.json` 为 `PASS`，四种伪造全部被 `BLOCK`。
- v7 数据迁移首次审计发现 AAPL、MSFT 上游拉取意外缩短历史，账本正确拒绝历史删除。修复工具现支持单侧阻断和按作用域幂等验签；恢复较长的既有 Futu 快照后，`stock_data_audit_g38_preprotocol_v7_repaired.json` 为 14/14 `PASS`，审计报告哈希 `ccaae8418fc3fced300d8688aa0c22d761d22895461baaca7ce6b8e469b4e46f`。
- G38 `PORTFOLIO_G38_EVIDENCE_CONTENT_AND_CURRENT_TIME_BINDING` 在研究运行前预注册为实验 `pexp-1785720650781-a3b3e38231e9`，协议哈希 `3bac4df7ebbddc8e9b7f782f4596a8cb42fa1b03a35eabb3941b38c2563b121f`。100 文件实现指纹 `975ab227233d41d017f5f31408e409c711765d316ffb124c5beef312fad50573` 在最终测试后未漂移，本代没有改变策略参数、标的池、成本、风险预算或晋级阈值。
- 研究报告 `portfolio_research_g38_evidence_content_and_current_time_binding.json` 的文件 SHA-256 为 `7126ecd2f1846e23a761c58e78ce1dd2001a4a4434aed4e478d23e2183ae486b`、批次哈希 `2615d6e7a73e3253daa9dd407a511b465b0d543f0a1a47354e4ae3a10d0a927c`。候选哈希 `1b6233ffbce1089dd6ba93f60ae8043410ac7f996baf5259e165cff03467a78f`，数据哈希 `199a2726e6a9ead614a3fc8506a9c72902f96211530ae6b58b5a141911b802dc`。验证收益/最大回撤/Sharpe 为 35.8862% / 4.0415% / 3.7788，测试为 7.4126% / 6.6002% / 0.9559，严重成本收益为 6.9762%；结论仍为 `PROMISING_NEEDS_FRESH_HOLDOUT`。
- 鲁棒性为 `ROBUSTNESS_PASS`：7/7 参数邻域为正、13 个逐标的消融中 12 个为正、三档资金规模均为正且无部分成交，鲁棒性哈希 `92264e2346b6a827ffba35f2e170c608e0ad459e62b5e4cde5126b4097dd142c`。隔离执行演练验证/测试/全段 55/36/123 笔全部通过风险、组合风险、订单生命周期和事件血缘，工件哈希 `bc00aba05d85dd4d8eea496ab1c48c84e0e4b66bc0d46d50c601a7ee951b2f58`。
- 统计审计工件自校验通过，但结论保持 `BLOCK / INSUFFICIENT_STATISTICAL_PROMOTION_EVIDENCE`，审计哈希 `a2477e85fd9618fd5d5becbdecf876a4ef0f0bf56ff59dffe33726004d216b8c`；验证段通过，测试段的选择修正概率与区间检查未通过。数据准入为内部研究 `READY_WITH_LIMITATIONS`、模拟 `BLOCK`、实盘 `BLOCK`；14/14 复权、修订、跨源完整性和近期独立重叠均通过，剩余阻断为历史时点化标的池、权威公司行动主数据、供应商许可与限流审批。
- 最终只读包 `internal_portfolio_backtest_pack_g38_evidence_content_and_current_time_binding.json` 为 `INTERNAL_BACKTEST_EVIDENCE_READY`、自校验 `PASS`、晋级 `BLOCK`，包哈希 `6ec3546709926e83bc03093fb12988dc19c9578d0a5c29c4fcb412716030aad4`。隔离回放战役 `ibc-1785720995849-1b6233ffbce1` 为 3/3 通过且唯一回放哈希 `552d062b47cd93ba5615704eee0ee95b72f5a28d75f69ea82193804b974a90b2`；网络、数据库、开发试验、独立样本和前向样本增量全部为 0，结论严格为 `REPRODUCIBILITY_PASS_NOT_PROMOTION_EVIDENCE`。
- G38 前向状态继续 `COLLECTING`：自然观察 0/60、外部结果 0/60、计划调仓 0/8，只有中性的 `PRE_ACTIVATION_SKIPPED`。观察、绩效、备份和 watchdog 四个任务均为 `Ready / LastTaskResult 0`，watchdog 为 `PASS`；`research_only=true`、`paper_authorized=false`、`live_order_allowed=false`。
- 最终完整 Python 回归为 580/580；相关 Python `py_compile`、`node --check exchange_terminal/static/app.js` 和 Electron `npm.cmd run check` 全部通过。本地服务 `http://127.0.0.1:8765/` 返回 HTTP 200；浏览器实测 AAPL、NVDA、BTC-USDT 切换约 0.3 秒，K 线持续非空，白色主题无黑色残留，控制台无 warning/error。
- 当前明确的工程债是 G38 为离线自证而内嵌完整双源快照，使研究报告从约 2.7 MB 增至约 54.2 MB。下一代应改为内容寻址的紧凑证据清单和不可变 sidecar，同时保持离线重建与篡改阻断能力；不得在冻结 G38 上直接改动后继续沿用其前向账本。

## 2026-08-03 G37 市场证据语义合同与共享批次哈希闭环
- G35 后续对抗审计复现了可重封装的证据语义绕过：历史时点化标的池、公司行动来源和跨源一致性曾能只改布尔值或 `PASS` 字符串后重新计算普通哈希。G35 在自然观察、收益期和计划调仓均为 0 时，以 `SEMANTIC_EVIDENCE_CONTRACT_BYPASS` 原因原子退役；退役收据 `portfolio_candidate_retirement_163784bf2b89_1785714584876.json` 的收据哈希为 `b7651c00fc64d9cd72a95949571361fd7e746aec71b2688c120f9f0712d08e80`，没有迁移或回填旧样本。
- 市场证据入口已改为独立语义重建：标的池合同 v3 绑定来源、发布时间、证据内容与时点成分；公司行动账本 v4 绑定权威来源证明、动作明细和复权重算；跨源证据兼容 v5/v6 并重算日期、样本数、误差分位和来源独立性；新增供应商治理合同 v1，绑定条款版本、存储/再分发权、配额、重试政策、复核人与批准收据。数据准入 v2 不再信任子报告的裸布尔值，而是逐项重验并重新生成门槛和阻断项。
- G36 完成上述语义修复后，内部包又准确发现生成端批次哈希包含供应商治理合同、只读验证器却遗漏该字段。G36 候选 `5bcfb8afe77d04f8fb11b4c2e7223ca35d5381c73b166af482dd751a651024a3` 在 0 个自然样本时，以 `RESEARCH_BATCH_HASH_VERIFIER_OMITTED_PROVIDER_GOVERNANCE` 原因退役；退役收据哈希 `d6bdf4e452e2aac58b8a045e8c6e83b5a299957130219f9e9da9c65188d7125c`。修复后生成端与读取端统一调用同一个 `research_batch_hash()`，供应商治理字段已纳入回归测试。
- G37 `PORTFOLIO_G37_SHARED_RESEARCH_BATCH_HASH_CONTRACT` 在研究运行前注册为实验 `pexp-1785715833791-2c707086a3f3`，协议哈希 `d0c1b8506ddc91eb4d80f682acca5da30dc444ec1a8d69fa4433fdfdfc94e90a`、100 文件实现指纹 `11674ea4db9ec196309d09f41c8144937479f47575ef282fba43fc9d4ac81f41`。本代没有更改策略、标的池、窗口、手续费、滑点、风险预算或晋级阈值，只修复共享批次哈希合同，并只消费一次预注册研究意图。
- G37 批次哈希为 `99b2fd08f3ad3181e7a6d6ff202e46bb50b8b0b9c26cd4dd339f84de29108c9f`，候选哈希为 `b95c647aba29bb7a1ae280e0deeccf68d1426da7e437437201e4a9e0f8cb3de5`。验证收益/最大回撤/Sharpe 为 35.8862% / 4.0415% / 3.7788，测试为 7.4126% / 6.6002% / 0.9559，严重成本收益为 6.9762%；与 G36 完全一致，证明工程修复没有借机调参，但这些仍只是开发期历史结果。
- 固定鲁棒性为 `ROBUSTNESS_PASS`：7/7 参数邻域为正、13 个逐标的消融中 12 个为正、1000 万规模无部分成交，鲁棒性哈希 `195ae165c1eba5ed869bf8d89135138e71d3d76f1f6e5e7f2a169d0d1d2ec399`。隔离执行演练的验证/测试/全段 55/36/123 笔均通过风险、订单生命周期和事件血缘检查，工件哈希 `3415a1eacec1531e158b3656db6beeaeb96a5abcd9fe2d1a4b32a21a8fe69eb8`。
- 统计审计工件自校验为 `PASS`，但结论保持 `BLOCK / INSUFFICIENT_STATISTICAL_PROMOTION_EVIDENCE`，审计哈希 `21d4ffb7c841157b68d73b04e3c9ec222c8cb889358de9c2060a884558d47eb2`。验证段通过，测试段的选择修正概率、信息比率概率和区间下界未通过，禁止把开发回测包装成可推广收益结论。
- 数据准入审计哈希 `5f0beb371465c34174bbe3a48c3c0c55826da9b42f63a19d2167dbf2df2e6805`，语义复核为 `PASS`；14/14 标的复权、修订账本、跨源完整性和近期独立双源重叠均通过。内部研究为 `READY_WITH_LIMITATIONS`，模拟与实盘均为 `BLOCK`，剩余三项外部治理门槛是历史时点化标的池、权威公司行动主数据、供应商许可与限流审批。
- 只读包 `internal_portfolio_backtest_pack_g37_shared_research_batch_hash_contract.json` 为 `INTERNAL_BACKTEST_EVIDENCE_READY`、自校验 `PASS`、无内部回测阻断项，包哈希 `64536ea22cf1d56432066802523bca2bf3c40e7ffe95211ca7c18c71f57ccf16`，文件 SHA-256 `b5ad89998aa8c5111e8112fa3deb795ac66608de637fd884643b2aef893a8738`。晋级仍因自然前向结果、计划再平衡、前向收益/回撤和历史统计审计保持 `BLOCK`。
- 最终内容寻址归档为 `portfolio-forward-1785716339423-b95c647aba29-a95c360c3903`，清单哈希 `a95c360c3903c7983b998d3ed0e7d2b66c86646404131c45615c5edfa008cc68`，归档验证为 `PASS`。回放战役 `ibc-1785716379310-b95c647aba29` 为执行端 3/3、验证端 3/3 同一哈希 `82b34c47be87f747519c387c3c1a3d36f8ef943e13ceac83a8d8317c5f28d113`；网络、数据库、开发试验、独立样本和前向样本增量全部为 0，结论严格为 `REPRODUCIBILITY_PASS_NOT_PROMOTION_EVIDENCE`。
- 观察、绩效、备份、watchdog 四个 Windows 任务均为 `Ready / LastTaskResult 0`；真实任务身份下 watchdog 为 `PASS / INFO`、阻断数 0。G37 前向状态为 `COLLECTING`：自然观察 0/60、外部证明 0/60、前向收益期 0/60、计划再平衡 0/8，只有 2026-07-31 的中性 `PRE_ACTIVATION_SKIPPED`，不得迁移、补录或回填旧候选样本。
- 完整 Python 回归为 572/572；`python -m py_compile exchange_terminal/server.py`、`node --check exchange_terminal/static/app.js` 和 Electron `npm.cmd run check` 全部通过。服务已用 G37 冻结实现重启于 `http://127.0.0.1:8765/`；真实浏览器实测 `AAPL -> NVDA -> BTC-USDT -> AAPL` 均约 0.9-1.1 秒完成，K 线画布持续为 1021x380 且股票/加密图实际非空，无加载残留或控制台 warning/error。系统继续 `research_only=true`、`paper_authorized=false`、`live_order_allowed=false`，实盘硬墙未打开。

## 2026-08-03 G35 冻结修订证据回放与内部回测基线
- G34 在冻结后离线回放中发现数据修订证据不稳定：策略运行哈希一致，但首次 v5→v6 迁移元数据与随后稳定 v6 元数据令完整结果哈希不同。该候选没有形成自然观察或收益样本，已用失效包 `internal_portfolio_backtest_pack_g34_revision_vintage_replay_invalidated.json` 和退役收据 `portfolio_candidate_retirement_1113bc0d6aba_1785694803993.json` 原子退役；退役收据哈希为 `5d758dd8665b3c2c6bf3163061ebaf68911c0549422fa07720ca290c9d1048db`，没有迁移或回填 G34 数据。
- 修复后的回放驱动按 validation/test/full 阶段绑定冻结研究报告中的精确复权与修订证据，子进程的结构化 `BLOCK` 原因会原样保留，回放驱动也必须来自候选冻结源码树。G34 数据上的预协议验证已做到各阶段运行与结果哈希完全一致、基准和成本压力一致、网络/数据库访问为 0；随后才预注册 G35，未在已冻结的 G35 上继续修改代码。
- G35 `PORTFOLIO_G35_FROZEN_REVISION_EVIDENCE_REPLAY_INTEGRITY` 的实验编号为 `pexp-1785696363064-0870bcf48b6e`，协议哈希 `deb25d54ab7c0293338041b361bc89d5967e72c8fb5382c473d0ad1cb2bbd31d`，99 文件实现指纹 `36a1611c7d9a2341265145575fe8516214aaa85268f456298cd09b4f249a84a0`。候选哈希为 `163784bf2b89be8e33f7939017398f9bf4363f53db69e8616ef732d9968002fe`，冻结后独立验签仍为 `PASS`，当前实现指纹未漂移。
- 冻结数据为 14 个标的、519 行、2024-07-05 至 2026-07-30，数据哈希 `ba90dfa17dcdd702f5791a426c584c92e8d2493d4f84aa9de16e942404df2d11`。验证收益/最大回撤/Sharpe 为 35.8862% / 4.0415% / 3.7788，测试为 7.4126% / 6.6002% / 0.9559，严重成本收益为 6.9762%；这些仍只是冻结开发样本内的结果。
- 鲁棒性为 `ROBUSTNESS_PASS`，7/7 参数邻域为正、13 个逐标的消融中 12 个为正、最高 1000 万规模无部分成交，鲁棒性哈希 `19dc22ac9b71460093b341240a69545ea5bd523e700a79c8df68c7d2fa6c0ed2`。隔离执行演练为 `PASS`，报告哈希 `7a706e3318efad01cb20ca7eb7fd33f5456c735e3098b296d9e46db253e77e8c`、工件哈希 `ab1aac51009ffa5fc56b91d9cec50edb5350dce6e0901a6178beab1bf7e0b066`。
- 统计工件自校验通过，但结论保持 `BLOCK / INSUFFICIENT_STATISTICAL_PROMOTION_EVIDENCE`，审计哈希 `a04b1d59dc6d602d90d1fc7a70de139625c8876d68026bbdd9717324cf8801fd`。数据准入为内部研究 `READY_WITH_LIMITATIONS`、模拟 `BLOCK`、实盘 `BLOCK`；14/14 标的近期独立双源重叠已经通过，剩余门槛是历史时点化 universe、权威公司行动主数据、供应商许可与限流审查。
- 独立包 `internal_portfolio_backtest_pack_g35_frozen_revision_evidence_replay_integrity.json` 为 `INTERNAL_BACKTEST_EVIDENCE_READY` 且自校验 `PASS`，包哈希 `0f809c630d28ac8d5a26a6a300f99d619b72fc06b639d3c066f848aacfc4679e`，晋级仍为 `BLOCK`。回放战役 `ibc-1785696877212-163784bf2b89` 的 3/3 正式回放和 3/3 验证器复跑均得到唯一回放哈希 `ca0b07f07af618d4852e67133030010380c3d67c0ee54218e5f61750edd19b66`；网络、数据库、开发试验、独立样本和前向样本增量全部为 0，结论严格为 `REPRODUCIBILITY_PASS_NOT_PROMOTION_EVIDENCE`。
- 最新计划任务归档为 `portfolio-forward-1785697030131-163784bf2b89-5213278cb8b3`，清单哈希 `5213278cb8b36b5f94439d900c070b7ac558bb7989bb8852c405328b739717a8`，99 个冻结源码文件、离线回放和恢复演练均为 `PASS`。观察、绩效、备份、watchdog 四个 Windows 任务均为 `Ready / LastTaskResult 0`；真实任务身份生成的 watchdog 状态为 `PASS / INFO`、阻断数 0。受限开发进程无法枚举任务计划程序时会产生“任务缺失”误报，因此系统健康以真实任务身份产物和任务返回码为准。
- G35 前向状态为 `COLLECTING`：自然观察 0/60、外部证明 0/60、计划调仓 0/8，只有中性的 `PRE_ACTIVATION_SKIPPED` 事件。不得回填、迁移旧候选样本或把离线回放次数计入前向证据；`research_only=true`、`paper_authorized=false`、`live_order_allowed=false`。
- 冻结后完整 Python 回归为 551/551；`compileall`、`node --check exchange_terminal/static/app.js` 和 Electron `npm.cmd run check` 全部通过。服务已用当前 G35 实现重启于 `http://127.0.0.1:8765/`；浏览器实测 `AAPL -> NVDA -> BTC-USDT -> AAPL` 均正确更新最终标的，K 线画布持续非空且约为 1021x380，无加载残留或控制台 warning/error。AAPL 在休市时明确显示上一交易时段，NVDA 使用 Futu，BTC-USDT 使用 OKX 实时 K 线，未把旧缓存伪装成实时数据。

## 2026-08-02 G33 执行授权、因果时钟与内部回测证据闭环
- 对模拟成交、持久账本、组合授权、策略时钟和 K 线准入继续做对抗审计，新增统一的 `paper_order_contract.py` 与 `candle_contract.py`。订单恢复现在严格核对状态迁移、成交金额、费用、数量和不可变字段；畸形恢复、并发执行、重复幂等键、字符串布尔值或生命周期冲突全部失败关闭。历史 K 线只有原生 `complete=true` 才能进入回测、组合研究、风险、基准、修订账本和策略矩阵，字符串 `"false"`、缺失或畸形完成标志不再被当成已完成 K 线。
- 模拟账户、组合账户、mutation journal、guardian、策略因果时钟、市场数据和 HTTP 合同均已纳入研究源码闭包；预交易缓存必须同时满足候选、合同和新鲜度绑定，组合状态中的畸形数字/布尔值会阻断，策略时钟禁止回填。完整 Python 回归两次均为 534/534，`compileall`、定向恢复/并发/布尔绕过/因果 K 线测试全部通过。
- G32 因冻结源码闭包发生上述变化而正式失效并退役。失效包 `internal_portfolio_backtest_pack_g32_execution_authorization_and_causal_clock_invalidated.json` 自校验 `PASS`，包哈希 `0815c9cfa1b6a6affe51a9234d984594e9ed0d420d86b70724ae81655a07f35e`、文件 SHA-256 `45671c5240d4f6d754b2024f05c008f2faf1566761388e0afcbb1a8011ab9400`；退役收据 `portfolio_candidate_retirement_6468ed5a8bd1_1785683031715.json` 的收据哈希为 `5777ec468b103137d8b7de1d40cc1ffcc4f2d53e978ce5bf3a47646a4d38c6f7`。没有迁移或回填 G32 的前向样本。
- G33 `PORTFOLIO_G33_EXECUTION_AUTHORIZATION_AND_CAUSAL_CLOCK_INTEGRITY` 在研究运行前预注册为实验 `pexp-1785683339825-2e147ca8380d`，协议哈希 `e06ac8f894c17ab3de33da7d95e755fab6c8d5f0420c46c99d65b09c004e3acb`、实现指纹 `2c5a9f7554bae885ed619df27db5e2bb63b300ef5c309579f187f29e5ff6c3c7`、意图哈希 `d99c3219699260171ca97bcced520baeebc767b089b0c3feacf722b59fe8b7e6`。策略、参数、标的池、成本、风险和晋级阈值未改变，只提升执行授权、恢复、显式 K 线完成和因果时钟合同，并只执行一次注册研究。
- 冻结数据共 519 行，范围为 2024-07-05 至 2026-07-30，数据哈希 `9aad77975a7ff556ce2e8c9e1126d939c682c43e164b2fbd6bb7ab0041c38f11`；G33 候选哈希 `a9cea1f81fa0921e51e0e561bb750c0d5cab4538261ce4c2ff85fbb08b16ee60`，活动注册表哈希 `efd50cd4948bbd0297de644461664f2d95e98eab2c3cddeb23d3f18dec954209`。验证收益/最大回撤/Sharpe 为 35.8862% / 4.0415% / 3.7788，测试为 7.4126% / 6.6002% / 0.9559，严重成本收益为 6.9762%；结论仍为开发期候选，不构成模拟或实盘授权。
- 固定鲁棒性为 `ROBUSTNESS_PASS`：7/7 参数邻域为正、13 个逐标的消融中 12 个为正、10 万/100 万/1000 万容量均为正，鲁棒性哈希 `53c172378d407813909c80c08a3b3fba9ec39c90cab40e237f70c047433f56f9`。隔离执行演练验证/测试/全段 55/36/123 笔全部通过风险、生命周期和血缘检查，工件哈希 `29a980289ece84f32fb195023616aaff1f66fae8791a5e6f3583d65764dd9e50`、报告哈希 `02e452d9c72fff19dbdcc1d23208331c960b9369da87716e2c932254ba4e5138`。
- 统计工件完整性验证为 `PASS`，但晋级结论严格保持 `BLOCK`，审计哈希 `87b6f54bfb13200b0f37eb1b5cd94eb6b883de3b690c999a3ff04a13b6e2870e`；验证段通过，测试段的选择调整概率和区间下界仍未通过。数据准入审计哈希 `941ff6acb79e2ae913fe63f410384867ecb181d616cf01010afcc2c1cb72aa44`，内部研究为 `READY_WITH_LIMITATIONS`，模拟和实盘均为 `BLOCK`；阻断项为历史时点化成分股、权威公司行动主数据、近期独立双源重叠、供应商许可与限流审查。
- G33 前向状态为 `COLLECTING`：自然观察 0/60、前向收益期 0/60、实际调仓 0/8；2026-07-31 只登记为 `PRE_ACTIVATION_SKIPPED`，禁止回填。观察、绩效、每日归档和 watchdog 四个 Windows 任务均为 `Ready / LastTaskResult 0`；真实计划任务上下文中的 watchdog 为 `PASS`、阻断数 0，并确认无执行权限。最新不可变归档 `portfolio-forward-1785684309660-a9cea1f81fa0-2010c1f84b62` 的清单哈希为 `2010c1f84b62d253455642d001ed71a9817b1206b5aaf0b2218b610d41c9e45f`，恢复验证为 `PASS`。
- 内部包 `internal_portfolio_backtest_pack_g33_execution_authorization_and_causal_clock_integrity.json` 为 `INTERNAL_BACKTEST_EVIDENCE_READY`，自校验 `PASS`，包哈希 `428e2518049499d03877a93e41f1c3c91d6898d9cb74c5dc2fc1b966b9449e49`、文件 SHA-256 `a46931717cb62ee221f0ead94edc6bd9c98c636037ed576c95ccbd5a75bfdc3a`；晋级仍因自然前向样本、前向收益/回撤和历史统计审计保持 `BLOCK`。隔离回放战役 `ibc-1785684245532-a9cea1f81fa0` 为 3/3 执行端与 3/3 验证端同哈希，网络/数据库访问和样本计数增量均为 0，战役哈希 `03cb6ab42b854862b6c2c489f93d3b0182908309117df9c877a261e817d1555e`，结论为 `REPRODUCIBILITY_PASS_NOT_PROMOTION_EVIDENCE`。
- `node --check exchange_terminal/static/app.js`、`python -m py_compile exchange_terminal/server.py` 和 Electron `npm.cmd run check` 全部通过；服务已用冻结 G33 实现重启于 `http://127.0.0.1:8765/`。真实浏览器中 AAPL→NVDA 约 1.0 秒、股票/加密切换约 1.2 秒；快速 `AAPL -> MSFT -> NVDA` 后最终标的、数据源和 K 线保持一致，画布持续为 983x380，NVDA 15 分与日线切换正常，控制台无 warning/error。组合候选继续 `research_only=true`、`paper_authorized=false`、`live_order_allowed=false`，实盘硬墙保持开启。

## 2026-08-02 G32 恢复阻断、显式类型合同与内部回测准备闭环
- 继续审计模拟成交恢复和组合授权链，确认并修复两类可导致错误放行的缺陷：持久化历史恢复失败、畸形行或幂等冲突后仍可能接受新模拟订单；组合模拟激活、前向证据、统计审计和研究注册表中的布尔值、整数与授权字段可被字符串、容器或 Python 布尔/整数兼容语义混淆。现在恢复异常会永久进入 `RESTORE_BLOCKED`，`submit()` 在读取盘口前拒绝；组合模拟授权必须使用原生精确类型，并在使用收据时重新核对时间、候选、就绪状态和人工批准绑定。
- 全部关键证据入口已改为显式 `is True` / `is False` 授权合同，计数必须是原生整数，市场完整性和可交易标志必须是精确布尔值；畸形前向状态改为返回 `BLOCK`，不再抛出未处理异常。完整 Python 回归为 510/510；固定种子 `20260802` 的 820 个类型变异/随机状态案例为 0 次绕过，期间发现的 `int({})` 前向状态崩溃已转成永久回归测试。
- G31 因冻结实现闭包变化正式失效并原子退役。失效包 `internal_portfolio_backtest_pack_g31_restore_and_type_contract_invalidated.json` 自校验 `PASS`，包哈希 `565e748681cb52628a60e9ebee476dc1396e154826a342ffbe1a2c46af7e111e`、文件 SHA-256 `89fe97877e6a451bfb8bd4e81d1bf9d6562abe83457a70814a18c56e20cef86f`；退役收据 `portfolio_candidate_retirement_449e937e5948_1785639636161.json` 的收据哈希为 `9e7a0e3648cb49a0c27eebef35460237d4c7df07b362d223721f7a51871de498`。没有迁移、回填或复用 G31 的前向样本。
- G32 `PORTFOLIO_G32_RESTORE_AND_EXPLICIT_TYPE_CONTRACTS` 在研究运行前预注册为实验 `pexp-1785639801076-077981efbefe`，协议哈希 `f57a3ee597ca4775603bb27f7889359ff1a0d8da3b7316b599d882e9354e8713`、实现指纹 `2f5a4b43eacf3af3f45e7aa6af62704d2b6b16810db8eed3d39c123c6c5a30e9`。策略、标的池、窗口、成本、风险和晋级阈值与 G31 完全一致，只增加恢复失败、幂等冲突、显式类型、无崩溃和人工授权收据绑定政策，并只执行一次注册研究。
- 冻结数据共 519 行，范围为 2024-07-05 至 2026-07-30，数据哈希 `9aad77975a7ff556ce2e8c9e1126d939c682c43e164b2fbd6bb7ab0041c38f11`；G32 候选哈希 `6468ed5a8bd1b73b259ebae6e593a6e766254835a866d984c333f5bcb9107c5f`，活动注册表哈希 `41e83f441c5afedf9a858cf1cee263aee5d03f2e36d58e8dd32247da22759611`。验证收益/最大回撤/Sharpe 为 35.8862% / 4.0415% / 3.7788，测试为 7.4126% / 6.6002% / 0.9559；结论仍为 `PROMISING_NEEDS_FRESH_HOLDOUT`，`research_only=true`、`paper_authorized=false`、`live_order_allowed=false`。
- 固定鲁棒性为 `ROBUSTNESS_PASS`：7/7 参数邻域为正、13 个逐标的消融中 12 个为正、10 万/100 万/1000 万容量均为正且无部分成交，鲁棒性哈希 `0585b6c78a44a8db75a21cbba21d49642f2ce19f1215a69f814aa6817c464547`。隔离执行演练验证/测试/全段 55/36/123 笔全部通过风险、生命周期和血缘检查，工件哈希 `b28cfe95e478a1222c9bd3fadc95390774f1df530d2abfcd9d1aa25ff536f0c8`。
- 统计工件语义复核为 `PASS`，但统计结论严格保持 `BLOCK / INSUFFICIENT_STATISTICAL_PROMOTION_EVIDENCE`，审计哈希 `264bf9f91a4360ac840fe441996d28c5e06b97ee867c9b26f230e7f4900db68b`：验证段超额收益 29.8655%、正超额概率 99.9%、选择修正后 99.2%；测试段超额收益仅 2.44634%、正超额概率 59.4%、选择修正后为 0，区间下界也未通过。数据准入仅为内部研究 `READY_WITH_LIMITATIONS`，模拟和实盘仍为 `BLOCK`；历史时点化成分股、权威公司行动主数据、近期独立双源重叠和供应商许可/限流审查仍未完成。
- G32 前向状态为 `COLLECTING`：自然观察 0/60、前向收益期 0/60、实际调仓 0/8；2026-07-31 只登记为 `PRE_ACTIVATION_SKIPPED`，不允许回填。调度器、前向结算、看门和每日备份四个 Windows 任务均已实跑为 `Ready / LastTaskResult 0`；调度器和看门状态为 `PASS/UP_TO_DATE`。最新不可变归档 `portfolio-forward-1785640280983-6468ed5a8bd1-43b275e3210a` 的清单哈希为 `43b275e3210a441008ebf10c7c98827744d6d80d968cefe617d3a72f61a5252e`，恢复验证为 `PASS`。
- 内部包 `internal_portfolio_backtest_pack_g32_restore_and_explicit_type_contracts.json` 为 `INTERNAL_BACKTEST_EVIDENCE_READY`，自校验 `PASS`，包哈希 `a5d59b787dd8ab29fc529899fe07c45bfd079f87f3ca026326ed813ee04bc81c`、文件 SHA-256 `75b3c2c2329e791f1eabbf0745f58acd6b5ba639373e1d553f601d37a1d015ba`，晋级仍为 `BLOCK`。隔离回放战役 `ibc-1785640177126-6468ed5a8bd1` 为 3/3 执行端和 3/3 验证端同哈希，网络/数据库访问和样本计数增量均为 0，结论严格为 `REPRODUCIBILITY_PASS_NOT_PROMOTION_EVIDENCE`。
- `node --check exchange_terminal/static/app.js`、`python -m py_compile exchange_terminal/server.py` 和 Electron `npm.cmd run check` 全部通过；服务已用当前实现重启于 `http://127.0.0.1:8765/`。真实浏览器验证 NVDA 日线约 0.3 秒显示 160 根 K 线，NVDA 5 分钟分时先秒开本地兜底后升级为 Futu 最近交易时段，BTC 5 分钟先秒开后升级为 OKX 实时；快速连续 `AAPL -> BTC-USDT -> NVDA` 后旧请求未覆盖最终标的，画布保持 983x380 非空，控制台无 warning/error。白底主题下控制中心、K 线、策略、信号和风险面板均为白/浅灰背景黑字。多标的组合模拟账户保持 `DISABLED_PENDING_CANDIDATE`、本金 0、无激活收据；旧单标的模拟账本恢复正常但未武装，实盘硬墙继续开启。

## 2026-08-02 G31 日期、数值与订单状态完整性闭环
- 对回测、组合风险、前向绩效、模拟成交和账本恢复继续做随机化状态机审计，确认并修复：数据集 `date` 与 `ts` 可不一致、布尔值被 Python 当作数字接受、数量约束拒绝单丢失原始数量语义、订单返回对象泄露内部可变引用、恢复后订单序号可能碰撞、内存幂等键淘汰后可能重复执行，以及模拟账本接受布尔数量或价格等缺陷。新增对应回归测试后，核心定向测试 178/178、完整 Python 回归 481/481 全部通过。
- G30 因冻结源码和数据合同变化正式失效。失效包 `internal_portfolio_backtest_pack_g30_date_numeric_state_isolation_invalidated.json` 自校验为 `PASS`，包哈希 `a6c410016581f2c94fc803fd42a03d45fe61bfe5cbaae3c9fb410a38c9ec4726`；活动候选退役收据 `portfolio_candidate_retirement_3dec02111eb4_1785635205147.json` 的收据哈希为 `bfaead5440242ac3bec17bd671f4d98885f03191c7548aacc1c3bf29191e0f5a`，旧候选不能继续被活动加载器接受。
- G31 `PORTFOLIO_G31_DATE_NUMERIC_AND_ORDER_STATE_INTEGRITY` 在研究运行前预注册为实验 `pexp-1785635478920-183fe32a03e2`，协议哈希 `9a27753c270a36440d102082c5bde6f077f35b7c0a96b7e99c13aca76b69728f`、实现指纹 `d51b3e6add4ca03a0b4e2fa9d01179aa72a6dac6fbe4e85e94639a77328ef76e`。本代没有调整策略参数、标的池、成本或风险阈值，只提升数据与订单状态合同并执行一次注册研究。
- 冻结数据共 519 行，范围为 2024-07-05 至 2026-07-30，数据哈希 `9aad77975a7ff556ce2e8c9e1126d939c682c43e164b2fbd6bb7ab0041c38f11`；候选哈希 `449e937e59480aec39d433c592339ad4bd3c0e3bdca8b4df43c720f29e8de796`。验证收益/最大回撤/Sharpe 为 35.8862% / 4.0415% / 3.7788，测试为 7.4126% / 6.6002% / 0.9559，严重成本收益为 6.9762%；这些仍是冻结样本内结果，不构成模拟或实盘授权。
- 固定鲁棒性为 `ROBUSTNESS_PASS`：7/7 参数邻域为正、13 个逐标的消融中 12 个为正、10 万/100 万/1000 万资金容量均无部分成交。隔离成交演练的验证/测试/全段 55/36/123 笔全部通过，成交演练工件哈希 `85c01008b433a856d848abebe641807ad65ca665f8b2c154f69862aeb9cfcf0f`；隔离回放战役 `ibc-1785635774124-449e937e5948` 为 3/3 执行端和 3/3 验证端同哈希，网络及数据库访问均为 0，结论严格为 `REPRODUCIBILITY_PASS_NOT_PROMOTION_EVIDENCE`。
- 统计审计的语义复核为 `PASS`，但统计结论仍为 `BLOCK / INSUFFICIENT_STATISTICAL_PROMOTION_EVIDENCE`，审计哈希 `fc4d37b59f179f1bf230c100fc6260ba3c49f3ddcfacc8f480f90cf30e71a650`。数据准入仅为内部研究 `READY_WITH_LIMITATIONS`，模拟和实盘均为 `BLOCK`；历史时点化成分股、权威公司行动主数据、近期独立双源重叠和供应商许可/限流审查仍未完成。
- G31 已作为研究候选进入活动注册表，注册表哈希 `b123227418591a4a1358e84a6198244413fb3743c607d3f26a677e48f5106164`，但 `research_only=true`、`paper_authorized=false`、`live_order_allowed=false`。前向状态保持 `COLLECTING`：自然观察 0/60、前向收益期 0/60、实际调仓 0/8；2026-07-31 只记录为激活前跳过，禁止回填或迁移旧候选样本。
- 最终内部包 `internal_portfolio_backtest_pack_g31_date_numeric_order_state_integrity.json` 为 `INTERNAL_BACKTEST_EVIDENCE_READY`，包内自校验全部 `PASS`，包哈希 `599e0079b1c706f1f5df2e18000547e17b835be55f9c20bc2e9a743677549e06`，文件 SHA-256 `3424ee2aedccff7f6ffd11b5d0ec1606299bc9a8ad7b2f5932cfda3e92b0e850`；内部包无阻断项，但晋级仍因自然前向样本和统计证据保持 `BLOCK`。
- `node --check exchange_terminal/static/app.js`、`python -m py_compile exchange_terminal/server.py`、Electron `npm.cmd run check`、主窗口 smoke 和图表 smoke 全部通过。本地浏览器完成 AAPL、NVDA、BTC-USDT 跨市场切换，并验证 BTC-USDT 的 1m 快速预览可被 OKX 实时数据接管、切回 1D 后仍为 180 根可见 K 线，控制台无 warning/error。截图 `browser_qa_g31_date_numeric_order_state_integrity.png` 为 100782 字节，SHA-256 `afe214f0c243693b6cf85557259db9b2839cc8680e9d1494242421e15597f737`。前向观察、绩效、看门和备份四个 Windows 任务均为 `Ready` 且最近返回码为 0；看门任务在 G31 证据齐备前留下的旧返回码 2 已通过计划任务本身重跑清除。服务继续运行于 `http://127.0.0.1:8765/`，风险引擎保持 `BLOCK_LIVE_READY_PAPER`，实盘硬墙开启。

## 2026-08-02 G30 因果数据、前向证据与隔离回放闭环
- 对回测数据、组合会计和前向证据做项目级对抗审计，修复 Yahoo 拆股历史成交量未同步复权、验证窗错误复用全窗修订证据、待退出仓位和剩余现金处理、公司行动前向结算、非有限数输入、目标仓位及流动性约束等缺陷。AAPL/NVDA 的历史价格没有被改写；成交量迁移报告、迁移前备份、修订事件和人工解决记录均已内容寻址保留。
- G29 因冻结数据与会计语义变化正式失效，并通过活动候选退役收据从注册表移除，而不是覆盖旧文件。失效包 `internal_portfolio_backtest_pack_g29_causal_data_and_accounting_invalidated.json` 自校验为 `PASS`，包哈希 `f5ebd9efa978a4bcaeb22b1bf00b7821b61a8d6da748888eaeff29ab7ebf8711`；退役收据哈希 `41dcc35b7fb8834b547e48a4bdb98b712bf86813dd333816dfc2a90e21d7221d`，重复执行保持幂等，旧候选不能再被活动加载器接受。
- G30 `PORTFOLIO_G30_CAUSAL_DATA_AND_FORWARD_ACCOUNTING_INTEGRITY` 在候选评估前预注册为实验 `pexp-1785631874074-4c1587f49627`，协议哈希 `c1bc7165dcb2b22e159d3034545f8e98576098d2abc1723dbb30b94dc86d6891`、实现指纹 `8e2356e7e7d9cdadb2ff8ab5dfd61e970940c7a404c5a8dcab2ffe6b5b83f826`。协议诚实标注行情数据维护先于本次预注册，并把迁移报告和备份哈希绑定为前置维护证据；策略、参数、标的池、成本、风险和晋级阈值均未改变，只执行一次注册研究。
- 冻结数据共 519 行，范围为 2024-07-05 至 2026-07-30，数据哈希 `3f0044b62409a8429131987115d62221cfaaf63cd3bea344c0bb0328dedf97a0`；G30 候选哈希 `3dec02111eb46bcf5462f4c2f6d8947bd8c63d8bd3b2b00a59ec93bd569b6202`。验证收益/最大回撤/Sharpe 为 35.8862% / 4.0415% / 3.7788，测试为 7.4126% / 6.6002% / 0.9559，严重成本收益为 6.9762%；结论仍是 `PROMISING_NEEDS_FRESH_HOLDOUT`，不是模拟或实盘授权。
- 固定鲁棒性为 `ROBUSTNESS_PASS`：7/7 参数邻域为正、13 个逐标的消融中 12 个为正、10 万/100 万/1000 万资金容量均无部分成交。隔离成交演练验证/测试/全段 55/36/123 笔全部通过风险、生命周期和血缘检查；统计审计语义复核为 `PASS`，但测试段选择偏差修正后的证据不足，最终结论保持 `BLOCK`，审计哈希 `a41988efbc088582535b42d21d3abf7105d9e06c09162ddccaa526503abbe5c5`。
- G30 数据准入仍为内部研究 `READY_WITH_LIMITATIONS`，模拟和实盘均为 `BLOCK`，审计哈希 `c0b76b76fec991d15c4b11de7b2e58da8c36f5d09e8e0901444f7e08f82b811d`。未解决门槛仍是历史时点化成分股、权威公司行动主数据、近期独立双源重叠和供应商许可/限流审查；不能用回测工程通过替代真实数据治理。
- 前向账本状态为 `COLLECTING`：自然观察 0/60、前向收益期 0/60、实际调仓 0/8，2026-07-31 只记录为 `PRE_ACTIVATION_SKIPPED`，没有回填、迁移旧候选样本或授予执行权限。AAPL/NVDA 新精确作用域中的成交量修订已按迁移报告逐项解决，冻结价格前缀保持不变。
- 不可变归档 `portfolio-forward-1785632716122-3dec02111eb4-2da3bdc11c9f` 自校验通过。隔离回放曾发现验证段复用全窗元数据的真实缺陷，修复后失败诊断包仍保留在 `runtime/backups/failed_archive_diagnostics_20260802_g30`；最终战役 `ibc-1785632778623-3dec02111eb4` 为 3/3 执行端、3/3 验证端同哈希，网络和数据库访问均为 0，结论严格为 `REPRODUCIBILITY_PASS_NOT_PROMOTION_EVIDENCE`。
- 最终只读包 `internal_portfolio_backtest_pack_g30_causal_data_forward_accounting.json` 为 `INTERNAL_BACKTEST_EVIDENCE_READY`，自校验 `PASS`，包哈希 `aacaa6e8dc25f7dcb6115d93d3338174b5a8d544dddccc8305b53b645e424b56`，文件 SHA-256 `0fb962c210944fa48d41b3c3f88bb5c827965051cb19740bb1ec1315509d669f`，晋级继续 `BLOCK`。完整 Python 回归 472/472、相关编译、前端语法、Electron check/主窗口 smoke/图表 smoke 全部通过；真实浏览器完成 `AAPL -> NVDA -> BTC-USDT -> AAPL` 及快速三连切换，常规往返约 0.3 秒，最终图表连续 3 秒未被旧请求覆盖，控制台无 warning/error。服务运行于 `http://127.0.0.1:8765/`；G30 多标的候选的 `paper_authorized=false`、`live_order_allowed=false`，旧单标的手工模拟账户仍可用但未武装，实盘硬墙保持开启。

## 2026-08-02 G29 模拟恢复、信号血缘与状态原子性闭环
- 对模拟账户并发恢复、条件单、手工单、策略时钟、守护急停和持久化回滚做第二轮对抗审计。确认并修复：陈旧对账快照覆盖新结算、重试耗尽仍误报正常、未结算成交期间继续生成模拟成交、OCO 条件上下文误判、服务层可注册无撮合回调的持久条件单、启动策略与流水线编号分两次落盘、停止后残留旧流水线编号、已完成 K 线信号缺少稳定 `signal_id`、手工预检金额/减仓语义与实际执行不一致、急停未平仓仍返回成功且保留活动条件单、账户快照泄露可变引用、重置失败不能回滚、非空仓可启动自动策略，以及自动策略错误执行 AI 生成止盈止损等缺陷。
- 当前模拟成交只有四个方向明确的账户入口；策略、报价风控退出、条件单、手工单和急停都必须经过统一风控、`paper_executor` 生命周期与 SQLite 账本。旧 `_legacy_evaluate_conditionals` 和 `evaluate()` 内重复直连执行代码已删除；所有策略信号在信号、风控、订单、成交和审计中保持同一个编号。
- 新增对账 CAS、未结算门禁、OCO/持久条件合同、策略绑定原子性、信号血缘、急停残仓、快照隔离、重置回滚、方向防穿仓和 AI 风险级别隔离等对抗测试。核心服务与策略时钟定向回归为 80/80，完整 Python 回归为 426/426；相关 Python 编译通过。
- G28 因冻结源码变化正式失效。失效包 `internal_portfolio_backtest_pack_g28_recovery_lineage_invalidated.json` 自校验 `PASS`，包哈希 `a64ce9c8e4ef2fdd91f61bf7ba24866308aac16680afcb32ead2ab98928fe21a`，明确阻断旧候选和旧实现指纹继续使用，未迁移或回填任何前向样本。
- G29 `PORTFOLIO_G29_PAPER_RECOVERY_AND_LINEAGE_ATOMICITY` 在访问行情前预注册：实验 `pexp-1785624983798-35cec5f2f36a`、协议哈希 `cbf566f02ac62dd03b5278460d3fabf455ab2a105b6e3cb5a0cabb1755a5bad1`、实现指纹 `d90f27e60eb9ea4d06af18ae0c76659132f22843d05442b8bebc7007b83b6cc5`。策略、标的池、历史窗口、成本、风险预算和晋级阈值与 G28 完全相同，只执行一次已注册研究。
- G29 冻结候选哈希 `31c4efdae33553ec5b54baa7baf66f472be461002445c7103cc6a6a39195a134`。验证/测试/严重成本收益分别为 35.8862% / 7.4126% / 6.9762%，与 G28 一致；鲁棒性为 `ROBUSTNESS_PASS`，7/7 参数邻域为正、13 个逐标的消融中 12 个为正、三档资金容量均无部分成交。隔离成交演练验证/测试/全段 55/36/123 笔全部通过风控、生命周期和血缘检查。
- 统计审计仍为 `BLOCK`：验证段通过，但测试段选择偏差修正后的证据不足；数据准入仍为 `READY_WITH_LIMITATIONS`，模拟与实盘数据准入均为 `BLOCK`。当前自然观察 0/60、前向收益期 0/60、实际调仓 0/8，2026-07-31 只记录为 `PRE_ACTIVATION_SKIPPED`，禁止回填。
- G29 只读内部包 `internal_portfolio_backtest_pack_g29_recovery_lineage_atomicity.json` 为 `INTERNAL_BACKTEST_EVIDENCE_READY`，自校验 `PASS`，包哈希 `14aaeb43aa536b53c31fb8ecc47ecd3efaf84ec8478210f9b35188ffb37f2683`，晋级继续 `BLOCK`。不可变归档、恢复演练、离线回放和看门链全部通过；四个 Windows 任务最近返回码均为 0。回放战役 `ibc-1785625368085-31c4efdae335` 为 3/3 执行端、3/3 验证端同哈希，结论严格为 `REPRODUCIBILITY_PASS_NOT_PROMOTION_EVIDENCE`。
- 本地服务已用冻结 G29 实现重启并恢复空仓、未武装、零活动条件单状态。`/api/paper/ledger` 为 SQLite、`restart_ready=true`、待结算 0；风险引擎保持 `BLOCK_LIVE_READY_PAPER` 和实盘硬墙。最终 426/426 Python 回归、Python 编译、三个前端 Node 语法检查、Electron `npm.cmd run check`、主窗口 smoke 与图表切换 smoke 全部通过。真实浏览器完成 `AAPL -> NVDA -> BTC-USDT -> AAPL` 跨市场切换，K 线画布始终非空且标的归属正确，控制台无 warning/error；服务运行于 `http://127.0.0.1:8765/`。

## 2026-08-02 G28 模拟结算因果、幂等与耐久化修复
- 对 `paper_executor.py`、`paper_ledger.py` 和重启对账链做对抗审计，确认四类真实缺陷：同一幂等键可把按金额下单错误重放为按数量下单；前一笔未能结算时后一笔仍会越序落账；`reduce_only` 只在受理时检查，结算时可能在空仓上反向开仓；SQLite/JSON 还能接受 `NaN/Infinity` 非有限数。全部缺陷先建立最小复现，再转成自动回归。
- 幂等签名兼容现在只适用于旧记录确实缺少 `quantity_constrained` 字段的情况；金额合同和数量合同使用同一幂等键会明确冲突。账本按创建顺序结算，遇到第一笔阻断立即停止后序成交；`reduce_only` 在耐久化结算时按最新权威持仓重新验证；所有成交、费用、账户与 JSON 数值在提交前必须为有限数。
- 新增 5 项结算对抗测试，覆盖金额/数量幂等冲突、部分成交只结算一次、首个未解决成交阻断后序、结算时重验只减仓和非有限数拒绝。核心服务回归由 57 项增至 62 项，完整 Python 回归由 407 项增至 412 项，全部通过。
- G27 因冻结源码闭包变化正式失效，失效包 `internal_portfolio_backtest_pack_g27_settlement_order_invalidated.json` 自校验为 `PASS`；失效包哈希 `e0632a84867cf96f389f502c67d40694aa75c79cdf7d457b3d0763d6d6ba901f`，文件 SHA-256 `d288bb9fb165672106dd376f42f3dc02880a52f0771ff155a1f148a0be8218f9`。G27 没有自然观察、收益期或实际调仓，因此没有迁移、回填或伪造前向样本。
- G28 `PORTFOLIO_G28_PAPER_SETTLEMENT_CAUSALITY_AND_IDEMPOTENCY` 在访问行情前完成预登记，实验 `pexp-1785621134699-8ce328e24c10`、协议哈希 `c15f4647de53d79b900628a093ddd9a765423dd56c5cc1be48e324126ef2961d`、实现指纹 `72326b90b886f327203a0bc6a7ed3d891a128f56598bddb2f3ac242b753070ad`。策略、标的池、数据、成本、风险和晋级参数均未改变，只新增模拟结算因果与耐久化政策。
- G28 只执行一次同参数研究：验证收益 35.8862%、最大回撤 4.0415%、Sharpe 3.7788；测试收益 7.4126%、最大回撤 6.6002%、Sharpe 0.9559；严重成本压力收益 6.9762%。批次哈希 `3ab3a7b2b0216d839e0852d70ef35c60f73be789e6b9763fcecd5832d3efe4e9`，冻结研究候选哈希 `322ee8e780e244642b8a785ec1f71ed6016b99338b88bf8a3a2a09567379f445`，结论仍是 `PROMISING_NEEDS_FRESH_HOLDOUT`，不是交易授权或盈利保证。
- 固定鲁棒性为 `ROBUSTNESS_PASS`：7/7 参数邻域为正、13 个逐标的消融中 12 个为正、10 万/100 万/1000 万容量均为正且无部分成交；鲁棒性哈希 `f118f36bbc83e94a83bc54f9f10806e5f613ed60d523973586de04f13d85baad`。隔离执行演练的验证 55、测试 36、全段 123 笔全部通过风险、组合、生命周期和血缘检查，工件哈希 `9fd93d7f8371c4cd5c8f3dfff22b6f0e8eddbcd5f60acb2aa752a86c9ba87278`。
- 统计审计的语义复核为 `PASS`，但测试段选择偏差修正后证据不足，统计结论保持 `BLOCK`；审计哈希 `f7e6d147175ca15646451b9af63a13d2446ee3fc57f435c1732343f2b9c939ff`。数据准入仍为 `READY_WITH_LIMITATIONS`，模拟和实盘准入均为 `BLOCK`；未解决项仍是历史时点化成分股、权威公司行动主数据、近期独立双源重叠和供应商许可/限流审查。
- G28 只读内部包 `internal_portfolio_backtest_pack_g28_settlement_causality.json` 为 `INTERNAL_BACKTEST_EVIDENCE_READY`，自校验 `PASS`，包哈希 `a822d41fb736a1168b47c718302855ea35fb4d0755a23eefe06ff893f5fdddc8`，晋级继续 `BLOCK`。回测战役 `ibc-1785621448978-322ee8e780e2` 执行 3/3、独立复核 3/3，通过唯一回放哈希 `911bb9359ca816038144a30bf2050628d3bca0cfeedd93deed24add222e52b87`；网络和数据库访问均为 0，结论严格为 `REPRODUCIBILITY_PASS_NOT_PROMOTION_EVIDENCE`。
- 前向链状态为 `COLLECTING`：自然观察 0/60、前向收益期 0/60、实际执行调仓 0/8，2026-07-31 只记录为 `PRE_ACTIVATION_SKIPPED`。四个 Windows 任务均已实跑为 `LastTaskResult 0`，看门狗全部检查通过；没有模拟自动执行权限，更没有实盘权限。
- 浏览器验收额外发现股票旧组件把 `volCcy24h` 成交额当成成交量，导致 AAPL 在部分列表和价格日志显示约 `40.35B`。前端现统一用基础成交量，AAPL 顶部、行情表、右侧栏和报价日志均为 `132.49M`；加密资产原有成交额/成交量口径不变。Electron 回归已固定检查这四处语义一致性。
- 最终 `node --check app.js`、Python 编译、Electron `npm.cmd run check`、主窗口 smoke、图表切换 smoke 和 412/412 Python 回归全部通过。浏览器实测 `AAPL -> NVDA -> AAPL` 均保持 520 根日线、正确标的归属和 Futu 来源，控制台无 warning/error；服务运行于 `http://127.0.0.1:8765/`，风险模式为 `shadow`，`paper_authorized=false`、`live_order_allowed=false`。

## 2026-08-02 G27 模拟风控与账本完整性修复
- 对模拟执行链做对抗审计后确认两处真实缺陷：调用方可用伪造的 `position_side=LONG` 把空仓 SELL 冒充平多，从而绕过陈旧行情与组合风险门禁；同一 `order_id` 还能用 `INSERT OR REPLACE` 改写已经结算的 fill，使账户持仓与账本成交量永久分叉。两条最小复现已转成自动回归测试。
- `risk_service.py` 现在会在组合风险计算和最终预检前，用风险快照中的权威持仓方向覆盖调用方上下文；不一致事实被显式记录，增加风险时 fail-closed，只有由权威持仓确认的真实减仓仍保留通道。`paper_ledger.py` 现在冻结订单身份、转换前缀、终态和已存 fill，禁止结算后追加/删除/改写成交，并取消生命周期与成交表的替换写入。
- G26 在自然观察、收益期和实际调仓均为 0 时正式退役，没有迁移或回填任何样本。失效包 `internal_portfolio_backtest_pack_g26_paper_integrity_invalidated.json` 自校验为 `PASS`，包哈希 `f371349384782247d9c1dd3c19ee6ff820bf0a2b0d1ed9b3869a8f96cd752f9e`，文件 SHA-256 `37c85dda5b272db8511374940e49cf86898d7e07dfe0ca178ff9697b5127a52e`。
- G27 `PORTFOLIO_G27_PAPER_RISK_AND_LEDGER_INTEGRITY` 在访问行情前完成预注册，实验 `pexp-1785618238786-cd33e2bafd9b`、协议哈希 `f7c95451be735faaddd84fa1d75e6d4c7e8d59a9943dd475e72f8afd4323365c`、实现指纹 `1319120e73faebf32f72b6e04f7007a5228a466fdd362f92e5f50c8cd2faa411`。只执行一次同参数研究，批次哈希 `9b9a7654f18551b0d76eae99d0fb08a3925ab515cdd450680637cd3153f962e2`，候选哈希 `3cb6a537281149e2a168917699f3912f792b52851cbb87f8faaaec4b35ff83a3`；验证/测试/严重成本结果与 G26 一致。
- 固定鲁棒性为 `ROBUSTNESS_PASS`：7/7 参数邻域为正、13 个逐标的消融中 12 个为正、10 万/100 万/1000 万三档容量均无部分成交。隔离执行演练的验证 55、测试 36、全段 123 笔全部通过风险、生命周期和血缘检查。统计审计语义验证为 `PASS`，但测试段选择偏差修正后证据不足，结论继续为 `BLOCK`；数据准入仍是 `READY_WITH_LIMITATIONS`，模拟与实盘数据准入均为 `BLOCK`。
- G27 只读内部包 `internal_portfolio_backtest_pack_g27_paper_integrity.json` 为 `INTERNAL_BACKTEST_EVIDENCE_READY`，包哈希 `57df103e25c7da65db78e75ed1fa9f7399475c8fbf0c6342668959c6763b31a2`，晋级保持 `BLOCK`。自然观察 0/60、前向收益期 0/60、实际执行调仓 0/8；2026-07-31 只记录为 `PRE_ACTIVATION_SKIPPED`。
- 四个 Windows 任务均已恢复并实跑为 `LastTaskResult 0`；调度为 `UP_TO_DATE`，备份归档清单哈希 `a99118359be170ea3cc882dd48408efa2bc0c269bdb8b00247b37b72a55871f7`，看门链全部检查通过。G27 回测战役 `ibc-1785618583219-3cb6a5372811` 执行 3/3、独立复核 3/3，通过唯一回放哈希 `d919a53465caaa521cc3b088b950700d2ebc102cb1d5b9df81dd94952bb09baa`；网络访问、数据库访问和证据归档改写均为 0，结论严格为 `REPRODUCIBILITY_PASS_NOT_PROMOTION_EVIDENCE`。
- 最终真实浏览器验收发现并复现了跨标的异步报价污染：从 BTC 快速切回股票时，一条迟到的 `BTC-USDT` REST 报价会改写 AAPL/TSLA 最后一根日线，把股票最高价抬到约 62,758 并令纵轴失真。`updateTicker` 现强制核对报价标的，OKX WebSocket 与 REST 轮询绑定 `symbolVersion + symbol + instId`，股票图同时拒绝超过 45% 尺度偏差的报价叠加。Electron 回归会主动向 TSLA 注入迟到 BTC 报价并要求价格和 K 线逐字段不变，同时要求最近 200 根 K 线最大影线比例不超过 2；修复前该用例稳定失败，修复后通过。
- 浏览器复测 `MSFT -> BTC-USDT -> AAPL` 均约 293-323ms 完成选中态、标题和图表同步，AAPL 恢复为 `O 304.81 / H 310.69 / L 300.00 / C 308.90` 的正常价格尺度，520 根 Futu 日线非空；BTC 盘口占比乱码已改为“买盘 / 卖盘”，桌面冒烟新增可见乱码扫描。最终页面控制台无 warning/error，主窗口 smoke、K 线 smoke、Node/Electron 检查和 407/407 Python 回归均通过。
- 当前完整 Python 回归为 407/407；真实下单硬墙未改变，所有新增报告继续显式为 `paper_authorized=false`、`live_order_allowed=false`。

## 2026-08-02 G26 内部回测战役一期

- 新增独立的 `exchange_terminal/services/portfolio_backtest_campaign.py` 与 `run_internal_backtest_campaign.py`，不修改 G26 的策略、数据、风控或执行指纹闭包。战役只读取已封存证据归档，禁止行情请求、参数搜索、可变 SQLite、模拟订单和实盘订单。
- 每次战役必须先创建不可覆盖的预登记契约，再按固定次数启动 `python -I -B` 隔离进程。契约冻结归档清单、候选、数据集、预期复放哈希、次数、超时、完整控制器依赖闭包和 Python 运行时；本批控制器指纹为 `b767846c2241305ef2616db280cca951efcb68210ae67bd972ae113e95a54eb1`，共绑定 72 个源文件。
- 新增归档前后全文件清单核对、逐次结果/记录双层哈希、跨进程确定性核对、网络/数据库访问计数、语义重算和独立验证器复放。测试覆盖失败结果重封装冒充 `PASS`、修改复放结果后重封装、缺失预登记文件、复放期间改写归档，以及失败后仍完成固定次数采样。
- 首份真实战役编号 `ibc-1785616866491-20ab6d522a01`：执行端 3/3、独立验证端 3/3 全部通过，六次复放均得到 `006060dc4f67f907c54282852bc1e54f12410275c44fba7b6c5790e21ead79b4`；执行端合计约 7.3 秒，网络访问 0、数据库访问 0、归档改写 0。
- 预登记契约 `internal_portfolio_backtest_campaign_contract_20260802_044106_1785616866491.json` 的契约哈希为 `ab19cb7bf56403e5496a54b3d8b0af334124e480a789f1a2adfe6ad9079bf760`、文件 SHA-256 为 `ae8c6d4925e62d3a224551b883c2c2bc4e45fee82b6de1117438cf5b170c63ae`。战役报告 `internal_portfolio_backtest_campaign_20260802_044106_1785616866491.json` 的战役哈希为 `b5d026e44b35968e5b4cf740bd1625bbee218127789608314d707db888adb7fe`、文件 SHA-256 为 `95c5e6df6b393783d6c188e18aed3eb52c2cb88db5cf1fc2fcc85359e866982e`，落盘后再次独立校验为 `PASS`。
- 战役结论严格为 `REPRODUCIBILITY_PASS_NOT_PROMOTION_EVIDENCE`：重复历史复放只证明可复现，不构成新试验、新独立样本或新前向样本。开发试验、独立样本、前向观察和前向收益期增量均为 0；统计晋级继续 `BLOCK`，`paper_authorized=false`，`live_order_allowed=false`。
- 完整 Python 回归现为 405/405；Python/Node 语法、Electron `check`、主窗口 smoke 和 chart smoke 均通过。图表实测 NVDA/AAPL/TSLA 日线各 520 根，快速切换不丢图；TSLA 盘后 520 根、盘中 420 根分钟线均为 Futu 数据。G26 实现指纹复核仍为 `5a93b9d4cd5060b644683bec9d42b6a8000049eff62976046ca87ef53932315d`。

## 2026-08-02 G26 统计审计语义重算与内部回测闭环

- 内核审计独立复现了统计审计重封装提权：旧读取器只验证审计自身普通哈希，攻击者可把真实 `BLOCK` 改成 `PASS`、清空阻断项并重算哈希，使前向就绪错误进入 `RESEARCH_REVIEW_READY`。修复后 `portfolio-statistical-audit-v3` 使用可信固定参数，从实验完成回执绑定的冻结策略/基准权益曲线重新运行两段配对移动块抽样，并逐字段核对状态、结论、阻断项、配置、阶段、检查和权限。证据包、前向绩效读取器和就绪门槛都必须取得该语义验证的 `PASS`；未验证的 `PASS` 立即按完整性故障阻断。
- G25 在自然观察、收益期和实际调仓均为 0 时正式作废，未迁移或回填任何前向数据。作废包 `internal_portfolio_backtest_pack_g25_statistical_semantics_invalidated.json` 自校验 `PASS`，包哈希 `a975ff6168dd1e11c36317c96d5e6ed63c60854a66d958f5b706ed10d29a0080`，文件 SHA-256 `547dfc193f08abdab5e4850559b5fc463505a5b71819ae137f534c2f710a0d61`。
- G26 `PORTFOLIO_G26_STATISTICAL_AUDIT_SEMANTIC_RECOMPUTATION` 在访问行情前完成预登记，实验编号 `pexp-1785614764787-d67d780ab4af`，协议哈希 `3f9e6df7594a34790d5b219b698d8ecb907910f917faf1f06329a70fcc5d0d31`，实现指纹 `5a93b9d4cd5060b644683bec9d42b6a8000049eff62976046ca87ef53932315d`。与 G25 的逐键差异审计只包含实验身份、前代作废绑定和统计语义政策，策略、标的池、成本、风险及晋级阈值没有变化。
- G26 只执行一次研究，批次哈希 `cdd255c0ba8adbade74e8d735880b2b4ea5eca49db72da3ff401d665b99fda1f`；验证收益 35.8862%、最大回撤 4.0415%、Sharpe 3.7788，测试收益 7.4126%、最大回撤 6.6002%、Sharpe 0.9559，严重成本压力收益 6.9762%，与 G25 完全一致。冻结候选哈希为 `20ab6d522a0107d6e1313197b20d4f8ab7f90ce0e3b039a21cef95f1517a691a`。
- 固定稳健性为 `ROBUSTNESS_PASS`：7/7 参数邻域为正、13 个逐标的消融中 12 个为正，10 万/100 万/1000 万三档均为正且无部分成交，稳健性哈希 `bba8449a2b665b208d3a6bc97f9b933e7925a07518f5dfc0f00f9a50d6b397ef`。隔离执行演练验证 55/55、测试 36/36、全段 123/123 笔均通过风控、生命周期和血缘核验，工件哈希 `903053e7f7fa35e8800d7bdb72367a5654b7bda59a3028c68eccd10de6abe2fd`。
- v3 统计审计的基础工件与冻结曲线语义复算均为 `PASS`，但统计结论保持 `BLOCK`：验证段正超额概率 99.94%、选择调整后 99.52%；测试段正超额概率 59.56%、选择调整后为 0。审计哈希 `879709b25c2265add70032a2093056bb78f1c5dfee71129f0fe4f7209566664e`，工件哈希 `6090dd95286d8c462f951c3e8324dbafe3bb8ed5f3b348915f54715f924c62ea`。数据准入仍为 `READY_WITH_LIMITATIONS`，模拟与实盘均为 `BLOCK`。
- G26 前向链为 `COLLECTING`，2026-07-31 正确记录为 `PRE_ACTIVATION_SKIPPED`；自然观察 0/60、前向收益期 0/60、实际执行调仓 0/8。只读包 `internal_portfolio_backtest_pack_g26_statistical_semantics.json` 为 `INTERNAL_BACKTEST_EVIDENCE_READY`、自校验 `PASS`、晋级 `BLOCK`，包哈希 `28f8c5a0bb3064284ab52e3d86a8533938f04039ef6dee079717d52d332330ec`。
- 最新计划任务归档隔离恢复与离线重放为 `PASS`，清单哈希 `3d8b515e935a49de9a1e47b133367f2d2457ea628b926ac15c5008b53c2eb0d9`；观察、绩效、备份、看门狗四个任务均已启用并实跑为 `Ready / LastTaskResult 0`，最终看门狗为 `PASS`。服务已重启到 `http://127.0.0.1:8765/`，活动候选复核约 90ms，错误日志为 0。
- 完整 Python 回归现为 400/400；Python 编译、`node --check`、Electron `npm.cmd run check` 和主窗口 smoke 均通过。K 线专项测试曾发现闭市后把 Futu 历史源误当实时源、追加周末报价并退回“报价预览”；现已改为必须满足 `market_session.is_open` 才能追加。复测 NVDA/AAPL/TSLA 日线、90ms 快速切换、TSLA 盘后 520 根、盘中 420 根和异动联动全部通过，未改变 G26 实现指纹或前向账本。

## 2026-08-02 G25 受信时钟语义重算与前向证据重建

- 完整内核审计发现并独立复现受信时钟缺陷：旧校验只检查普通 SHA-256 和少量汇总字段，一个逐源状态已改为 `ERROR`、可信时间被任意改写的证据在重新计算哈希后仍可返回 `PASS`。该缺陷会削弱候选激活时间、收盘后采样窗口和禁止回填合同，因此在 G24 自然观察、收益期和调仓仍为 0/0/0 时立即修复。
- `trusted_clock.py` 已升级为 `trusted-clock-attestation-v2`：逐源验证证据哈希、请求起止、往返时间、中点、服务端时间、偏移、状态和错误字段，再重算有效来源数、偏移中位数、来源离散度、质量、可信时间和显式只读权限。历史 v1 记录不被改写，而是在读取时接受同一套 v2 语义重算；语义矛盾的 v1 仍会阻断。新增回归覆盖重新封装、时间算术不一致、历史 v1 复核和非布尔权限值。
- G24 已由 `internal_portfolio_backtest_pack_g24_trusted_clock_semantics_invalidated.json` 正式失效；失效包校验 `PASS`，包哈希 `77e9f07f269b2871ce5b435d75109052c5a09e91400ca7d16ce30acf247b5d02`，文件 SHA-256 `eaf6115feee79753f8f5a4c058f961cdf6a1cf9db44b7c38aec3a5f3dda309d4`。没有迁移或回填任何 G24 前向数据。
- G25 `PORTFOLIO_G25_TRUSTED_CLOCK_SEMANTIC_RECOMPUTATION` 在访问新行情前完成预登记，实验编号 `pexp-1785613149998-594e5c794b77`，协议哈希 `2c034771d5cafc267694569f1565cdd05cca8aaeae5e1ba751fcacaa1238ce7e`，实现指纹 `d748f5692722f98003b8102a00dbff95ba2041282d28c07bbec0c697ec9fdc3c`。与 G24 对照的 83 个非治理字段没有策略、数据、成本或风险参数漂移。
- G25 只执行一次研究，批次哈希 `13ef41c9df80c1c546a10a83b32dc922baddac3a9b58bf24c9118caba27f885b`；验证收益 35.8862%、最大回撤 4.0415%、Sharpe 3.7788，测试收益 7.4126%、最大回撤 6.6002%、Sharpe 0.9559，严重成本压力收益 6.9762%，与 G24 一致。冻结候选哈希为 `6fcaef62d4715b552b46e6ea63c160b4b44dbb347f510b69128ae9e0cbb0f839`。
- 固定鲁棒性继续为 `ROBUSTNESS_PASS`：7/7 参数邻域为正、13 个逐标的消融中 12 个为正，10 万/100 万/1000 万三档容量通过；隔离执行排练的验证 55、测试 36、全样本 123 个订单事件全部通过，执行证据哈希 `b53a9a48434492f7cde5c5933bcf320a3da9a495302a7b4c385a0ca8b0736301`。
- 统计晋级仍为 `BLOCK`，测试段选择偏差修正后证据不足；审计哈希 `088727281455cbbd2daf776fcc541728c256c9e7f8d41e29ffdbdd3450716884`。数据准入仍为 `READY_WITH_LIMITATIONS`，模拟与实盘均为 `BLOCK`，未解决项仍是历史时点化成分股、权威公司行动主数据、近期独立双源重叠和供应商许可/限流审查。
- G25 前向链为 `COLLECTING`，2026-07-31 正确记录为 `PRE_ACTIVATION_SKIPPED`；自然观察 0/60、前向收益期 0/60、实际执行调仓 0/8。内部回测包 `internal_portfolio_backtest_pack_g25_trusted_clock_semantics.json` 为 `INTERNAL_BACKTEST_EVIDENCE_READY`，最终包哈希 `ad4465f24e92407cd6be3c3b2c7be037300f04d53c80057d310200498bc5bb64`，校验 `PASS`，晋级继续阻断。
- 最终证据归档已独立恢复校验，清单哈希 `4631aa0c9e5726d558d25a0227758e4cafdeea049acad30d3335b89825aa8fe2`；四个 Windows 前向任务均已重新启用并实跑为 `Ready / LastTaskResult 0`，看门狗最终为 `PASS` 且所有检查为真。服务已重启到 `http://127.0.0.1:8765/`，风险模式为 `shadow`，`paper_authorized=false`、`live_order_allowed=false`。
- 完整 Python 回归现为 399/399；Python 编译、`node --check`、Electron `npm.cmd run check`、主窗口 smoke 和 chart smoke 均通过。桌面实测 NVDA/AAPL/TSLA 日线、快速切换、盘后 241 根、盘中 420 根、成交量单位和 AAPL 异动详情同步均正常。

## 2026-08-02 G24 市场数据语义修复与内部回测准备

- G23 曾完成同参数研究、鲁棒性、执行排练和只读内部回测包，但后续发现批量报价、股票交易时段、日线完成状态和异动优先级存在必须修复的数据语义问题。修复触及冻结源码闭包后，G23 已由 `internal_portfolio_backtest_pack_g23_market_data_quality_invalidated.json` 正式判定失效；G23 没有自然前向观察、收益结算或执行调仓，因此没有迁移或回填历史样本。
- G24 `PORTFOLIO_G24_MARKET_DATA_SESSION_FRESHNESS` 在访问新行情前完成预登记，实验编号 `pexp-1785610450690-4052782cf061`。39 个策略、数据、成本、风险和晋级参数与 G23 完全一致，只新增行情时间戳、交易时段、完成日线、降级来源和异动优先级的质量契约；协议哈希 `38076193b5f58a007a3e780a41de54e2d95e6e19d1a737573791cb13067678ef`，实现指纹 `81f9f0e941e8d1623f5d82295cd96f5f832a387e34c77396ad16a35db4e93ea7`。
- G24 研究只执行一次：验证收益 35.8862%、最大回撤 4.0415%、Sharpe 3.7788；测试收益 7.4126%、最大回撤 6.6002%、Sharpe 0.9559；严重手续费/滑点压力下测试收益 6.9762%。结论为 `PROMISING_NEEDS_FRESH_HOLDOUT`，不是可交易或盈利保证。
- G24 当时的活动研究候选为 `portfolio_candidate_g24_market_data_quality.json`，候选哈希 `afef5002ea79b98816f551e54d5ed6f60771aa370df535e782e6a7b1221b3216`。鲁棒性为 `ROBUSTNESS_PASS`：7/7 参数邻域为正、13 个逐标的消融中 12 个为正，10 万/100 万/1000 万三档历史容量测试通过。隔离执行排练的验证 55、测试 36、全样本 123 个订单事件全部通过风控、生命周期和事件血缘核验。
- 统计晋级审计继续保持 `BLOCK`：验证段通过，但测试段选择偏差修正后正超额概率为 0，置信区间下界未越过 0。数据准入为 `READY_WITH_LIMITATIONS`，模拟与实盘数据准入均为 `BLOCK`；未解决项仍是历史时点化成分股、权威公司行动主数据、近期独立双源重叠和供应商许可/限流审查。
- G24 退役前的前向链状态为 `COLLECTING`。2026-07-31 正确记为 `PRE_ACTIVATION_SKIPPED`，不回填；自然观察 0/60、前向收益期 0/60、实际执行调仓 0/8。只读内部包 `internal_portfolio_backtest_pack_g24_market_data_quality.json` 当时为 `INTERNAL_BACKTEST_EVIDENCE_READY`，校验 `PASS`，但晋级始终为 `BLOCK`；`paper_authorized=false`、`live_order_allowed=false`。
- 行情质量修复已验证：休市后的 Futu 股票统一标为 `LAST_SESSION / Futu最近时段`，完成的股票日线不再冒充实时，旧缓存/兜底/未知数据不能进入 A 级异动队列；OKX 只有来源在线且时间戳新鲜时才标为实时。完整 Python 回归 395/395 通过，Python 编译、`node --check` 和 Electron `npm.cmd run check` 均通过。
- 本地浏览器实测 `AAPL -> MSFT -> BTC-USDT -> AAPL`，选中态分别约 323ms、310ms、309ms，股票日线和 BTC 实时 K 线均非空，切换后控制台无 warning/error。异动雷达显示 `A 0 / B 1 / 待核 5`，AAPL 的休市 Futu 数据只进入 B 等确认，旧缓存进入 C/待核。
- 四个 Windows 前向任务最终均为 `Ready / LastTaskResult 0`，看门狗全部检查为真。首次串行触发时外部时钟接口往返约 10.25 秒，超过 5 秒合同并正确 fail-closed，导致备份与看门狗连锁阻断；单独重试恢复，账本和候选未损坏。
- 浏览器验收后的纯前端语义补修已完成：股票顶部和股票列表使用 `vol24h` 股数并标为“当日成交量”，现货继续使用 `volCcy24h` 并标为“24h 成交额”；进入异动雷达或切换标的后，详情选中态优先同步当前标的，不再出现顶部 AAPL、详情仍停留在 MSFT。Electron 回归已固定检查三股成交量单位、当前标的/雷达选中行/详情提示一致性，并增加应用冷启动就绪门槛；这些 UI 修改不改变 G24 的策略候选、实现指纹或前向账本。

## 当前定位

行情解释和多 AI 讨论已经拆到独立“交易分析”项目。哈基米交易 v2 现在聚焦“策略验证与模拟交易内核”：接收研究结论，把它转化为可复现回测、策略体检、前向模拟、风险控制和可回放审计证据。真实下单继续保持永久硬保护墙，不开放。

核心优先级：
- 默认第一屏是交易总控，集中显示策略流水线、模拟账户、统一风控、行情服务、SQLite 账本/回放和实盘保护墙。
- 保留美股、部分港股龙头、电力股和主流加密货币行情，作为策略输入与数据质量证据。
- 策略必须经过不可变版本登记、时间顺序验证、成本敏感性检查和策略体检，才可能获得模拟授权。
- 模拟成交、手续费、滑点、订单状态、账户结算和事件血缘统一持久化；重启后先对账，再允许增加模拟风险。
- AI 和独立交易分析项目只能提供 ResearchBrief，不能绕过验证流水线、风控或执行硬墙。
- UI 继续靠近富途牛牛 / moomoo：黑底白字、蓝底白字、白底黑字三主题，K 线红涨绿跌。

## 运行入口

- 本地地址：http://127.0.0.1:8765/
- 后端入口：`outputs/python_quant_bot/exchange_terminal/server.py`
- 前端入口：`outputs/python_quant_bot/exchange_terminal/static/app.js`
- Electron 桌面壳：`outputs/hakimi_trade_electron/`

常用检查：

```powershell
node --check outputs/python_quant_bot/exchange_terminal/static/app.js
python -m py_compile outputs/python_quant_bot/exchange_terminal/server.py outputs/python_quant_bot/exchange_terminal/config.py outputs/python_quant_bot/exchange_terminal/research/stock_research.py
npm.cmd run check
```

## 已完成能力

- 市场异动雷达：扫描放量、急涨急跌、突破/跌破、波动扩张、资金费率和 OI 等异常线索。
- 趋势分析驾驶舱：输出趋势状态、波动、量能、多空概率、关键价位和风险提示。
- K 线与分时：支持日线、分钟、分时、画线、缩放拖动、成交量和基础标注。
- 股票研究：覆盖美股七姐妹、半导体、存储、部分港股和电力股，支持 Futu / Yahoo / 本地缓存降级。
- 数据可靠性：前端显示来源、新鲜度、延迟、缓存状态和降级原因，避免把旧缓存误认为实时数据。
- AI 研究室：预留 TradingAgents 式研究员会议纪要，多模型发言互相复核；当前先以研究纪要和本地快照为主。
- 模拟盘与风控：保留模拟订单、条件单、策略体检、风险中心和审计思路，真实交易链路继续阻断。

## 最近修复

- 股票行情新增统一交易时段契约：明确区分 `LIVE_SESSION / LAST_SESSION / HISTORICAL_SESSION / DELAYED_SOURCE / STALE / UNAVAILABLE`，Futu 提供方确认的盘前、盘中、盘后状态会贯通报价、K 线、质量条和风控上下文；只有确认中的盘中数据才可能增加模拟风险，实盘仍永久阻断。
- 修复切股卡顿与空图竞态：前端会取消旧报价和旧 K 线请求，后台刷新按 `标的|周期|时段` 单飞；AAPL → NVDA → WDC → MSFT 快速连切后，最终标题、选中行、K 线标的和 520 根日线保持一致，不再被旧请求覆盖。
- 修复股票时段按钮“看得见但点不到”：图表工具栏、质量条和数据源条改为内容自适应布局，窄窗口下周期、交易时段和图表工具固定分行；盘前、盘中、盘后、夜盘五个按钮的中心点击均命中自身，页面无横向溢出。
- 分时数据改为一次获取、多处消费：`all` 分时会自动拆分写入盘前、盘中、盘后、夜盘的内存和 SQLite 分区；NVDA 完整分钟数据首次抓取约 3 秒，盘前/盘中/盘后缓存命中实测约 5–14ms。
- 分钟历史新增来源新鲜度仲裁：Futu 主时段超过 18 小时时会与公开源比较同一时段最新时间并选择更新者；MSFT 15 分钟线已从 Futu 的 2026-07-29 自动切换到 Yahoo 的 2026-07-31，仲裁证据保存在返回结构中。
- 数据源健康度改为按 `标的|周期|时段` 展示：PSTG 的 Yahoo 404 仍会进入全局审计，但不会再把 MSFT 的 Yahoo 当前行误标为降级；当前作用域可独立显示 `HEALTHY / DEGRADED / CIRCUIT_OPEN / UNKNOWN`。
- 历史预热新增覆盖感知：SQLite 已有足量且近期的数据直接标记 `READY + cache_hit`，本次启动 20 个已有覆盖任务无需重复请求；离线种子和报价预览不再被误标为预热成功，PSTG 当前上游失败会如实显示 `ERROR`。
- 修复行情事件审计的结构化字段写入错误，`emit=true` 快照不再因字典绑定 SQLite TEXT 字段返回 502；行情事件序号和来源详情可正常落审计链。
- Electron K 线冒烟测试现在拒绝把快速预览、离线种子、旧缓存或 `STALE` 当作最终成功，并覆盖四股连续切换、时段按钮遮挡、盘后 Futu 与盘中 Yahoo 回退；完整 Python 回归现为 74 项。
- 建立权威行情质量门禁：开仓前由统一行情服务重新验证来源、实时性、缓存、隔离状态、报价年龄和请求价偏差；调用方不能伪造 `READY`，坏数据只允许减仓、平仓或撤单。
- 新增事务型 SQLite 模拟账本 `services/paper_ledger.py`：账户、余额、持仓、条件单、订单状态迁移和成交统一落库；旧 JSON 只做一次迁移，未结算成交会在重启时确定性对账。
- 强化 `paper_executor.py`：模拟订单支持持久化幂等键、冲突检查、手续费/滑点/盘口撮合和完整生命周期；账户层不会重复应用幂等重放的同一笔成交。
- 急停平仓改走统一只减仓风控和模拟执行器；盘口只能部分成交时保留真实剩余仓位，不再直接改余额并伪造全额成交。
- 新增不可变策略版本与真实时间顺序验证：按训练/验证/测试集切分，执行滚动前向验证和手续费/滑点压力测试；整段历史表现通过不再等于可获模拟授权。
- 旧策略运行若缺少不可变版本或时间验证，界面统一显示 `LEGACY_BLOCKED`，必须用当前内核重新验证，不能沿用旧 `VALIDATED` 状态。
- 新增前向模拟毕业门槛：默认至少运行 7 天、完成 20 笔闭合交易、最大回撤不超过 12%，之后仍需人工审计批准；实盘权限始终为 `false`。
- 新增信号到成交的 SQLite 事件血缘：`signal_id → risk_request_id → market_snapshot_id → order_id → transitions → fill`，支持按订单或策略运行确定性回放并生成校验哈希。
- 状态写接口统一使用 POST、本机来源白名单、`X-Hakimi-Write` 和持久化 `Idempotency-Key`；同键同请求返回原结果，同键不同请求明确冲突。
- 交易总控新增账本重启状态、账本版本、幂等写入状态和最近订单回放；“数据状态”改名为“行情服务”，避免把服务在线误解为当前标的一定可交易。
- 新增 `event_lineage.py`、`event_replay.py`、`http_contract.py`、`mutation_journal.py`、`strategy_validation.py` 等服务边界；当前完整 Python 回归共 55 项。

- 新增独立股票报价质量层 `market_data/stock_quote_quality.py`：统一昨收优先的涨跌幅计算，明确记录昨收/本地K线昨收/今开/数据源等基准，检查 OHLC 字段错配、超过 45% 的异常跳变、超过 40% 的异常振幅和复权/拆股风险。
- 修复股票报价时间与涨跌口径：Yahoo 使用 `previousClose` 和 `regularMarketTime`，Futu 使用 `prev_close_price` 和真实 `update_time`，Stooq 缺少昨收时优先参考本地日线昨收，否则明确降级为“按今开计算”；统一行情快照不再用请求完成时间覆盖真实报价时间。
- 股票质量结果已贯通雷达、统一行情快照和股票研究页；隔离数据固定进入 C 级“数据待核”，不能进入 A/B 队列。新增 6 项相关回归场景，当前核心测试共 14 项。
- 异动雷达数据质量隔离：股票旧缓存出现超过 25% 的异常涨跌或超过 40% 的异常振幅时，保留原始评分用于审计，但展示评分封顶 67、严重度改为“数据待核”，并标注疑似复权、拆股或基准价错配；所有高分兜底数据进入待核队列，不再冒充可信高严重度或 A/B 信号。
- 雷达概览统一显示 `A / B / 待核`，前端兼容旧后端返回，详情和列表中的待核方向统一改为“数据异常”；新增 3 项数据质量回归场景，当前核心测试共 8 项。
- 核心稳定性清理：雷达/AI 视图内的 K 线聚焦不再跳回普通行情页，隐藏的模拟盘和风控模块停止 7 秒高频轮询，减少长期盯盘时的后台请求和重绘。
- 本地服务改为 `8765` 端口独占：禁止新旧两个服务进程同时监听同一地址，重复启动会明确提示已有实例，避免随机命中旧代码。
- 统一处理浏览器取消请求和流式断连：本地客户端主动切换页面或中止 AI 会议时不再生成服务器异常堆栈，也不会尝试发送第二份错误响应。
- 行情快照新增同标的单飞锁：前端、雷达和 AI 同时请求同一标的/周期时只拉取一次上游数据，其余调用复用标准化缓存。
- 统一行情服务新增跨周期报价复用：K 线、走势驾驶舱、股票研究和 AI 即使请求不同 K 线数量，也共享同一标的报价、来源、新鲜度和质量结论，避免同屏重复拉取上游报价。
- 统一行情快照新增消费者追踪和健康接口：记录 K 线、预热、走势、研究、AI 的请求/复用次数，前端股票数据源栏显示 `READY / REUSED`、参与模块和报价复用状态。
- 股票旧数据刷新改为优先消费统一快照；只有快照失败时才补拉独立报价，移除一次切换同时请求两份股票报价的重复链路。
- 事件总线和 JSONL 审计增加线程锁，保证多请求并发下事件序号唯一、审计记录不交叉损坏。
- 修复模拟撮合假成交：盘口不可用时 LIMIT/IOC/FOK 不再按最新价伪造成交；Post Only 会拒绝立即吃单的价格。
- 删除旧版 TradingAgents 不可达实现，避免维护时误改已经不再执行的代码路径。
- 新增 5 项核心服务回归测试，覆盖实盘硬墙、限价撮合、Post Only、行情单飞缓存和并发审计。
- AI 研究室改为微信式群聊主界面：用户问题右侧绿色气泡，研究员观点左侧按头像分组，大块研究员卡片退出主视图，聊天记录成为主要阅读区域。
- 聊天等待态改为逐位追加：发送时只显示用户问题和当前正在输入的研究员，后续 AI 轮到时再进入消息流，不用四个排队卡占满首屏。
- AI 讨论接口新增 NDJSON 逐位事件流：点击发送后立即显示用户问题、随机角色和“正在输入”，每位模型完成后立刻落入聊天窗口，后序模型继续读取前序观点。
- AI 聊天交互支持 Enter 发送、Shift+Enter 换行；重复发送会中止上一轮请求，避免旧会议结果覆盖新问题。
- 修复 AI 研究室被延迟 K 线聚焦任务切回普通行情页：在研究室内切换标的或重绘图表时保持当前视图，群聊主题样式不再中途失效。
- AI 研究室运行时接入升级：GPT、DeepSeek、豆包 Ark、GLM/智谱 Ark 拆成四个独立接入状态，支持本机内存临时载入和清空；真实 Key 不写入代码、配置或前端。
- AI 研究室新增接入完成度提示和安全说明：明确显示 0/4、1/4 等接入状态，避免用户误以为已经自动保存或自动代填真实 Key。
- TradingAgents 研究员会议室优化为会议纪要结构：结论摘要、四位辩手状态、逐轮发言、证据、质疑和观察条件分区展示，继续限定为观察、研究和模拟盘验证。
- AI 研究室升级为独立大工作台：新增顶部标的代码输入、常盯标的快捷按钮、全宽 K 线和研究快照；从 AI 页切换股票不会再跳回普通行情页。
- AI 讨论室升级为群聊式发言流：按 1号 GPT/Codex、2号 DeepSeek、3号豆包、4号 GLM/智谱顺序展示头像、发言、模型来源、证据、质疑和观察条件。
- AI 研究室交互继续收口：新增标的候选下拉、常盯标的选中态和会议追问输入框；点击“会议”后立即显示四位研究员排队发言，结果返回后按顺序回放群聊式会议记录。
- AI 研究室大屏降噪：在独立研究室视图中隐藏旧“双AI分析”表单和报告块，把页面焦点收敛到 K 线、行情证据、运行时接入状态和 TradingAgents 研究员会议。
- 修复“带入AI”上下文不可见：异动雷达和研究页的问题会同步写入独立研究室的可见输入框并聚焦；研究室顶部摘要改为趋势结构、多空估计、关键位置和下一步等待条件，减少价格/K线/数据源重复信息。
- 修复研究室 K 线未铺满：画布重绘改为读取当前图表容器宽度，不再沿用切换页面前写入的 720px 行内宽度，消除右侧大块空白。
- AI 研究室升级为随机角色聊天室：GPT、DeepSeek、豆包、GLM 保留真实模型身份，每轮从趋势、多头、空头、风险、数据、催化、量价和行业联动角色池随机抽取身份；后发言者读取前序记录，并在赞同或质疑中点名回应。
- OpenAI 接入支持本机 `.env.local`：文件被 `.gitignore` 排除且不会在前端回显；界面手动输入的其他模型密钥仍只保存在后端进程内存。
- 清理前端隐藏模块中文乱码。
- 修复白底主题下控制中心、风险中心、策略体检、K 线图等区域仍显示黑底的问题。
- 修复系统页横向溢出、保存设置按钮被推出视窗的问题。
- 修复切换标的后页面停留在下方区域、用户看不到 K 线变化的问题。
- 默认市场列表改为全市场，避免股票分类下 BTC / ETH 等加密货币不可见。
- 雷达首屏增加本地数据可信度卡片，展示 K 线来源、新鲜度、市场覆盖、Futu/OKX 状态和实盘硬锁状态。
- 常盯标的在全市场列表优先显示：主流加密货币、美股七姐妹、半导体、存储股、指数、SpaceX 相关替代标的和港股电力股。
- 左侧行情栏改为桌面终端式固定侧栏，页面滚到 K 线或雷达详情时，标的搜索和切换仍保持可见。
- 启动后后台分批预热常盯标的日线 K 线缓存，BTC/ETH/NVDA/AAPL/MSFT 等点击后优先命中秒开缓存，再由真实快照异步覆盖。
- 股票专项研究新增“研究员会议纪要”卡片：基于新闻/财报事件、盘前盘后、同业联动、异常成交和数据质量生成会议结论、多头证据、空头反证和等待条件。
- 股票专项研究新增“事件催化雷达”：财报/新闻、盘前/盘后、行业链、异常成交、数据质量五类证据单独成卡。
- 股票专项研究新增“产业链拆分”：按核心芯片、服务器/整机、设备、代工、存储/HBM、电力运营等角色聚合上下游样本，帮助判断单股异动是否有链条共振。
- 股票专项研究新增“日线波段结构”：基于本地日线 K 线缓存计算趋势阶段、20/60 日支撑压力、MA20/MA50/MA200、量能确认和等待条件，优先服务美股日线波段研究。
- 股票专项研究新增“数据可信度”卡片：把报价、日线、盘前盘后、新闻、财报事件和基本面来源拆开显示，区分外部数据、本地缓存、旧缓存和离线兜底，避免把本地摘要误认为实时新闻。
- 修复股票旧缓存刷新链路：`force=true` 会绕过旧本地 K 线早退路径，优先强刷 Futu / Yahoo / Stooq；研究页检测到 OLD_CACHE 会显示提示并触发后台刷新。
- 修复股票报价不同步：研究页拿到 Yahoo/Futu 新报价后，会同步顶部价格、左侧市场行和 K 线，避免报价卡已经更新但主界面仍显示旧价。
- 修复股票分时/分钟线被报价预览覆盖的问题：非交易时段不再把 Yahoo/Futu 的有效历史分钟线改写成“报价预览”，盘中分时、5分、15分等周期可直接显示真实分钟线来源和新鲜度。
- 强化异动雷达主流程：雷达行从旧表格升级为“观察队列”，显示 A/B/C 优先级、联动主题、数据源状态、下一步等待条件和安全边界；详情页同步展示观察优先级和等待条件。
- 强化异动事件库：事件入库新增联动主题、观察优先级、下一步观察条件和等待条件 JSON 字段，旧数据库会自动增量补列，不清空历史事件。
- 修正股票日线新鲜度表达：周末/休市阶段看到最近一个美股交易日数据时，显示“上一交易日 / 延迟研究源”，不再误导为坏图或无效旧缓存。
- 修复股票切换后 K 线消失和布局遮挡：选中标的后自动把 K 线滚入可视区，左侧列表不再横向溢出；窄桌面宽度下 K 线工具栏、数据质量条、实时状态条和底部状态栏不再重叠。
- 新增股票日线质量检查 `market_data/stock_candle_quality.py`：相邻收盘出现超过 45% 的可疑尺度变化时，保留原始证据但暂停趋势、支撑压力、振幅和多空概率计算，避免复权/拆股口径异常污染研究结论。
- 修复 WDC 报价与旧 K 线基准混用：报价优先采用 Futu 昨收口径，异常旧缓存不会再显示 +169% / +196% 等伪涨幅；必要时图表只使用临时连续视图，不改写原始数据。
- 统一股票日线缓存分区：主图、股票研究和 AI 本地分析全部使用 Futu `regular` 前复权日线，旧 `all` 分区不再参与日线结论，解决主图 520 根完整日线与研究页 80 根断档缓存互相冲突的问题。
- AI 数据质量联锁：未核实的价格尺度断点会同时暂停前端摘要、DeepSeek 初评、GPT 复核和 TradingAgents 技术结论；外部模型不会在坏数据上生成精确胜率和止盈止损。
- 异动雷达新增时间演化判断：同一标的连续扫描会标记“新异动、快速增强、二次确认、持续高位、变化不大、正在衰减、数据待核”，并展示评分与涨跌变化；首次扫描只建立基线，不伪造趋势。
- 雷达新增“全部 / 新增增强 / A/B 队列 / 数据待核”筛选，详情页增加本轮变化卡；数据质量隔离项固定进入“数据待核”，不会因分数变化被误标为增强信号。
- 异动事件库新增 `motion_json` 审计字段，保存演化状态、评分变化、涨跌变化、前次优先级和新出现证据，便于后续追踪误报与信号生命周期。
- 本地浏览器已验证 23 条雷达结果、6 张总览卡和四类筛选；1280×720 下 K 线保持 983×418，页面、雷达与筛选栏无横向溢出，控制台无错误。
- 新增异动后验评估 `services/anomaly_outcomes.py`：新事件保存首次价格，达到观察窗口后标记“方向已确认、方向已失效、无后续跟随、观察中”；统计使用“方向确认率”，明确不是未来胜率。
- 旧事件没有可信首次价格时保持“无历史基线”，不根据最后价格倒推；低质量数据、C级观察项和无明确多空方向的事件不进入确认率统计。
- 雷达新增“信号后验”总览卡，事件列表与单标的详情同步显示评估状态；终局结果冻结，每轮只更新有基准且未完成的近期事件，避免反复重写大量历史记录。
- 统一快照实测 AAPL 的 K 线、走势驾驶舱和股票研究价格均为 `316.535`、来源均为 Futu；重复请求命中快照缓存，跨周期请求命中共享报价缓存。
- 本地浏览器已复测 BTC-USDT → AAPL 切换：选中行、报价和 K 线同步更新，AAPL 日线、均线、布林带与成交量完整成像，画布保持 983×418，共享快照状态可见且无横向溢出。
- Electron 实机已验证 AAPL / WDC 切换、Futu 日线、价格更新、白底主题和响应式布局；当前核心回归测试共 34 项。
- 重写本状态文件，修复原文件编码乱码。

## 2026-08-01 因果回测内核与内部回测准备

- 新增 `exchange_terminal/services/backtest_engine.py`：策略只能在 K 线收盘后生成信号，最早在下一根开盘成交；不再允许同一根收盘价既看见信号又成交。
- 止盈止损改为使用完整 OHLC 路径；同一根 K 线同时触发止盈和止损时，固定采用保守的止损优先假设，并记录 `ambiguous_intrabar_count`。
- 入场费、出场费和滑点全部进入现金、成本基础、实现盈亏和费用压力测试；CLI 与主平台使用同一套下一根成交语义。
- 当前回测内核只支持 1 倍现金账户。杠杆参数会被明确阻断，直到保证金、利息、强平和跳空模型完整实现，不能再用现金撮合伪装杠杆结果。
- 数据集指纹由首尾抽样升级为全量 OHLCV SHA-256；任意中间 K 线变化都会改变数据哈希。每次运行同时冻结参数哈希、策略代码指纹、执行模型和运行哈希。
- 策略流水线新增不可变 SQLite 回测工件：保存策略版本、精确参数、数据清单、时间验证、成本压力和验收结果，并提供 `GET /api/strategy/backtest/artifact?runId=...` 校验工件哈希。
- 回测报告必须与当前运行的标的、策略、代码指纹和参数完全匹配；使用其他标的或其他参数的报告会进入 `backtest_binding=BLOCK`，不能获得模拟授权。
- 修复门槛分数稀释：关键检查中的任意 `BLOCK` 都不能被其他高分项平均成 `PASS`；`WATCH` 也不能进入模拟授权。
- 时间验证使用 50% 训练、25% 验证、25% 测试，并继续执行三个顺序窗口和三档手续费/滑点压力测试；发布摘要与持久化流水线现在读取同一状态。
- AAPL 真实缓存样本验收：520 根输入中排除 1 根未确认 K 线，519 根进入全量哈希；当前参数整体回测为正，但验证段收益不为正，因此正确显示 `temporal_validation=BLOCK`、`paper_ready=false`。
- 独立 CLI 的 `ccxt` 实盘实现、实盘模式选择和旧 Streamlit 实盘开关已经移除；即使配置文件伪造 `mode=live`，加载后也会强制恢复 `paper`。
- 当前 Python 回归测试为 87 项；`py_compile`、`node --check app.js` 和 Electron `npm run check` 均通过。临时 HTTP 服务已验证回测 POST、策略绑定、工件读取、工件哈希和实盘锁定。

### 当前验证档与内部批次

- 回测到前向模拟新增参数绑定：启动模拟时，仓位、止盈、止损、杠杆和方向必须与通过回测的不可变参数完全一致；任一字段漂移都会进入 `paper_parameter_binding=BLOCK`。
- 当前唯一可授权的自动策略执行档为 `LONG_ONLY / MANUAL / PCT / CURRENT / CROSS / 1x / 固定止盈止损`。做空、杠杆、移动止盈止损和无明确限价的限价委托尚未完成独立回测，保持阻断。
- 修复自动模板默认使用 `LIMIT` 但未生成限价的问题。验证模板现在统一使用现价模拟委托，避免策略显示已启动却因缺少 `limit_price` 永不成交。
- 本节曾记录的 `runtime/reports/internal_backtest_batch_20260731_231711.json` 实际不存在，不能作为当前证据；遗留文件 `runtime/reports/internal_backtest_batch_20260731_230527.json` 也不是合法 JSON，文件 SHA-256 为 `1017c7486910fe361a4978d6701a353e135b780ef11a3c623483b939b1bddc75`。两者均已退役，只保留为历史问题记录；当前正式内部回测证据以 G20 内容寻址证据包为准。
- AAPL、NVDA、MSFT、WDC、BTC-USDT、ETH-USDT 共 6 个标的全部通过数据集门禁并生成完整数据/参数/运行哈希；当前 6 个均未通过样本外时间验证，因此 `paper_ready=0`、`live_order_allowed=false`。

### 第二代策略研究与盲测隔离

- 信号引擎升级到 `causal-long-only-signals-v4`：策略可显式声明读取收盘序列或完整 OHLCV，信号仍只能在当前 K 线结束后生成，并在下一根开盘执行。结构化信号同时接受前缀因果、确定性和输入不可变审计。
- 新增量价趋势研究策略、策略专属研究风险档和风险档哈希。趋势策略不再被固定止盈反复截断，均值回归策略仍使用受限止盈止损；这些风险档只用于研究，不自动获得模拟授权。
- 新增研究暴露登记：训练、验证、测试和留出标的都会记录是否已经被研究流程看过；被加载过的测试或留出集不能再次伪装成盲测。研究报告同时冻结策略、参数、风险档、信号引擎和候选选择通道。
- G1 严格测试报告 `strategy_research_20260801_005119.json`，哈希 `d71286b4f84ac4def18a06b6d7e20d99b57648119b7699e93d15d6dcfc83de24`：Turtle 短周期趋势候选未通过首次未见测试，不能进入模拟盘。
- G2 新鲜标的留出报告 `strategy_research_20260801_005536.json`，哈希 `20a24471b0c0c9a920df2fd77ab7b856dfcefde6f38992e5719e59f96f0a849b`：Turtle 和 Momentum 风险调整候选均未满足综合效率门槛，前向候选为 0。
- G3 新鲜标的留出报告 `strategy_research_20260801_005828.json`，哈希 `c827f912b4f1cc83796365cc2689018950cfcc133ad2f2cc980a6f3382ea173e`：270 个选择单元产生 2 个风险候选，但在 SPY、TSLA、AMD、ASML、TSM 留出集上再次全部失败，前向候选仍为 0。
- 当前结论是“研究基础设施合格，策略尚不合格”。AAPL、NVDA、MSFT、MU、WDC、QQQ、AMZN、GOOGL、META、AVGO、SPY、TSLA、AMD、ASML、TSM 已进入暴露登记，后续不能继续在这些留出段上调参并声称独立验证。
- 修复股票历史回测的重复 Futu 连接：完整日线可直接消费持久化 SQLite 缓存，不再为最终会被排除的临时报价 K 线再开一次连接。15 个已覆盖标的读取 779 根日线实测合计约 71.5ms，来源仍标记为 Futu、检索来源明确为 `stock_sqlite_cache`。
- 新增 `market_regime.py`：用当时已经完成的 OHLCV 识别上涨、下跌、震荡与波动扩张/收缩，并输出只做多风险预算系数；前缀、重复运行、未来数据突变和输入不可变审计全部进入报告。状态标签是风控证据，不是开仓信号。
- 新增 `portfolio_risk.py` 并接入统一 `RiskService`：新增风险会检查单标的、总敞口、净敞口、持仓数量、产业主题和高相关资产集中度；自动策略还会应用市场状态预算。任一门禁失败只阻止增加风险，减仓和平仓路径始终保留。
- 当前固定矩阵报告为 `strategy_matrix_20260801_011256.json`，批次哈希 `1a0a356ad1712c7c5573ba327fc70ed8721fb242107b214573cf1697949c73aa`：9 个策略、6 个基准标的、54 个选择单元的原始数据、市场状态因果审计和相关性覆盖均为 `PASS`，但策略通过数、确认候选和前向候选仍全部为 0，`paper_authorized=false`。
- 测试窗口证据显示 MU 与 WDC 的 60 日收益相关系数约为 0.77，不能把两者当完全独立样本；BTC-USDT 最新为下行/波动收缩状态，只做多预算系数为 0。该证据不追溯修改旧策略成绩。
- 当前完整 Python 回归为 178 项，全部通过。真实下单硬保护墙、1 倍现金限制和前向模拟毕业门槛均未改变。

### 组合相对强弱研究与只观察前向登记

- 新增独立 `portfolio_backtest.py`，不把组合轮动伪装成单标的策略：日线收盘计算相对强弱和市场状态，下一交易日开盘调仓，统一结算现金、手续费、滑点、换手和组合权益。
- 组合内核加入产业簇上限、排名缓冲、1% 最小调仓带、12% 权益回撤保护和 20 个交易日冷却；G4 起使用 63 日逆波动权重、15% 组合波动目标和单标的最高 50% 组合权重。
- 组合数据层现复用单标的完整质量门禁，并要求共同交易日历、每标的全量数据哈希和冻结区间复核；测试夹具中伪造周末交易日和 `ts=0` 的问题因此被发现并修正。
- G1/G2 依次暴露高换手与持仓缓冲扩大回撤的问题；G3 开发报告曾达到测试收益 33.66%、回撤 14.23%，但一次性跨标的确认 `portfolio_holdout_20260801_012712.json` 在 AMAT、LRCX、KLAC、QCOM、INTC、STX、NTAP、SMCI 上出现 16.35% 最大回撤，因此状态为 `CROSS_SECTIONAL_BLOCK`，批次哈希 `569afea12b1dca4113079883c3c913a0b87f4615441dcecd83d1ef648cbd20a5`。
- 已失败的 8 个留出标的已进入研究暴露登记，不能重新调参后再次冒充盲测。组合开发、基准和跨标的留出现在与单策略研究共享 `research-exposure-audit-v2`。
- 前向登记首次运行发现“每 5 根 K 线调仓”的相位会随请求历史深度变化，同一候选同一天生成不同目标；SQLite 幂等账本正确报冲突且未覆盖旧证据。调仓契约已改为每个 ISO 周首个实际交易日收盘，历史深度回归测试通过。
- 最新 G5 开发报告为 `portfolio_research_20260801_013606.json`，批次哈希 `2a86e5ba924dbf9238412d431939e8ba5811dc71e8735be52e509b51ecc4f98e`：验证收益 22.39%、回撤 9.65%，开发测试收益 24.76%、回撤 6.66%，严重成本压力收益 23.85%，因果和相关性审计均通过。
- G5 冻结候选为 `portfolio_candidate_20260801_013606.json`，候选哈希 `f9c91491cbba14f7b7d3a8d204ccd524f02ecb7691c6457efb86d7811d3ffbf2`；状态仍为 `BLOCKED_PENDING_FRESH_HOLDOUT`，不能进入模拟盘。
- 新增 `portfolio_shadow.py` 与 `run_portfolio_shadow_observation.py`：只记录候选冻结日之后的完成日线、目标组合、状态预算和证据哈希，不生成任何模拟订单。冻结区间会先做数据哈希复核；G6 候选最终冻结至 2026-07-30，2026-07-31 已作为第一根真正的冻结后完成日线进入只观察账本。

### G6 执行真实性、公司行动证据与组合影子风控

- 新增 `services/corporate_action_ledger.py`：统一登记股票历史源的复权口径、拆股/分红事件、价格尺度断点和证据哈希。Futu 日线声明为 `FORWARD_ADJUSTED_QFQ`；未知复权口径或未解释的尺度断点会阻断组合研究，系统不会自动改写原始 K 线价格。
- 修复日线未完成行长期滞留：常规收盘及缓冲时间后，如果缓存仍含当日或更早的未完成日线，会强制请求上游刷新；刷新失败时保留此前完整历史并明确告警，不会伪造收盘。AAPL、NVDA 当前最新完整日线均为 2026-07-31。
- 组合执行模型升级为 `signal-close-next-open-liquidity-portfolio-v2`：新增 20 日历史中位成交额、最低 500 万美元成交额、入场 1%/出场 2% 参与率、12% 隔夜入场跳空限制、动态冲击和部分成交；容量判断只读取信号日及之前的成交量，不偷看执行日最终成交量。
- G6 首次运行暴露了一个容量误分类缺陷：冲击后价格变化曾令所有买入被误记为部分成交。失败工件 `portfolio_research_20260801_023547.json` 被保留，修复后没有覆盖旧证据。
- 最新 G6 报告为 `runtime/reports/portfolio_research_20260801_023642.json`，批次哈希 `5806023731a4fa9f03da7ed2c05f85614589133f4af27131c6f03a3cd40f1f99`：验证收益 19.64%、最大回撤 10.83%，开发测试收益 23.98%、最大回撤 6.66%，严重成本压力收益 23.08%；因果、相关性、复权口径和执行约束审计均通过。
- G6 的约 7340 万美元容量只是基于日成交额和固定参与率的粗粒度研究估计，不代表真实可成交容量；当前 10 万美元研究权益下没有触发跳空阻断或部分成交。
- 当前冻结候选为 `runtime/reports/portfolio_candidate_20260801_023642.json`，候选哈希 `94521624b56e4dd69f06541c49312ceb3406de2f45871f82f8893d1ca635872f`，状态仍为 `BLOCKED_PENDING_FRESH_HOLDOUT`，`paper_authorized=false`、`live_order_allowed=false`。
- 新增 `services/portfolio_paper_account.py`：提供事务型 SQLite 多标的组合账本、版本并发检查、幂等键、重启恢复、现金/费用/盈亏结算和先卖后买的目标订单预览。服务启动时本金为 0、`simulation_enabled=false`，只开放 `GET /api/paper/portfolio`，没有写入或下单路由。
- 新增 `services/portfolio_shadow_risk.py`：把冻结候选、相关矩阵、市场状态、流动性和复权证据汇总为结构化风险快照。2026-07-31 首个前向观察记录 WDC、AMD、ASML，观察敞口 22.420981%，原因为 `hold_between_rebalances`，未生成订单。
- 首次影子风险快照因持有日缺少目标权重而错误阻断；原始 `BLOCK` 记录被完整保留。修复后从最近一次调仓证据恢复持仓权重和流动性上下文，并以追加式风险复核写入 `PASS`，风险哈希为 `246150a81d401dd7c0b40cf56afa5d8f9723eb89c0edab1a45b86fde3376d234`。当前市场观察 1 条、风险复核 1 条，仍远未达到模拟授权门槛。
- 完整 Python 回归现为 201 项并全部通过；`node --check app.js`、相关 Python `py_compile` 和 Electron `npm.cmd run check` 均通过。重启后的 API 已确认实盘硬墙开启、组合账本只读禁用、AAPL 复权证据为 `PASS`。
- 本地浏览器回归：AAPL、NVDA、BTC-USDT 切换后画布分别包含 160、160、180 根 K 线；BTC 与 AAPL 切换约 0.46 秒，均无空图。1440×900 下无横向溢出，白底主题在行情、策略、账户、系统视图保持一致，控制台无错误或警告。

### G7 官方交易日历、生命周期与冻结数据隔离

- 新增 `services/market_calendar.py`，通过 `exchange-calendars 4.13.2` 固化 XNYS/XHKG 正式交易日、节假日和提前收盘证据；测试夹具才允许使用确定性工作日日历。G7 冻结区间为 2024-07-05 至 2026-07-30，共 519 个 XNYS 交易日，日历门禁为 `PASS`。
- 新增 `services/security_lifecycle.py`：停牌/暂停时生成只估值、不可交易的延续行；未声明缺失交易日直接阻断；退市必须提供现金结算价并生成强制结算事件。生命周期对齐数据可重复回放且哈希一致。
- 公司行动账本升级到 v3：Futu QFQ 与 Yahoo `Adj Close / Close` 比例生成的总回报前复权序列都采用内嵌拆股/分红收益，禁止重复发放现金；原始或仅拆股调整序列必须具备完整公司行动和分红支付日，HFQ 仍禁止进入现金执行回测。
- 修复浏览行情污染回测基线：低优先级 Yahoo/Stooq 不能覆盖 Futu；同一来源的已完成日 K 只允许追加新交易日或把未完成行定稿，普通页面刷新不能改写历史；回测只读取持久化证据快照，不消费图表内存缓存。连续真实 Yahoo 刷新前后，519 日组合数据哈希保持一致。
- 修复旧 `all` 日线分区残留的周末伪 K 线：日线“全部时段”统一映射到 `regular`，AAPL 536 根、NVDA 535 根本地日线均为 0 个周末日期。离线种子报价不再伪造买一卖一，缺少真实盘口时统一显示 `--`。
- 最终 G7 报告为 `runtime/reports/portfolio_research_20260801_083627.json`，批次哈希 `1fb48d7c1e7e259c20bbba999948d2d238a33dc40444ceda27eb6576b0d0dfaa`，冻结数据哈希 `a9fed2270605eaa20dbd33c3e577fa85afc86c86a58e6905be3221f91490acf3`。验证收益 33.1307%、最大回撤 4.0646%；开发测试收益 10.4075%、最大回撤 6.6641%；严重成本压力收益 9.9540%、最大回撤 6.6636%。所有开发门禁为真，但这些仍是已暴露历史上的研究结果。
- 最终冻结候选为 `runtime/reports/portfolio_candidate_20260801_083627.json`，候选哈希 `fb9c453beb44a93e3c5bdff74361c3f735dddab275423ec5762c8331fbb0ef2a`，21 个关键实现文件指纹为 `ea363aba4f19fa82a4cf6bb055828be6e143a2d0284df977cb0cf609b9ba6f65`。候选校验为 `PASS`，授权状态仍为 `BLOCKED_PENDING_FRESH_HOLDOUT`，`paper_authorized=false`、`live_order_allowed=false`。
- 2026-07-31 只观察记录目标 WDC/AMD/ASML、观察敞口 22.42098%，决策哈希 `6c9af9f7fa9fd248883c5d8183a229a583038c9df4da75cc37a41dc1517ad753`，风险快照哈希 `bfe41753eed9a387578b567c3ba4c19af284816abfb318f528ee8314bc30c470`；第二次运行返回 `IDEMPOTENT_REPLAY`，没有订单或重复记录。
- 完整 Python 回归现为 231 项并全部通过；Python `py_compile`、`node --check app.js`、`node --check chart_quality.js` 和 Electron `npm.cmd run check` 均通过。浏览器中 AAPL/NVDA 约 0.5 秒显示非空秒开图，3 至 6 秒完成上游复核，画布为 1021×380，买一卖一保持 `--`，控制台无错误或警告。

### G8 计划调仓、前向防回填与内部回测体检

- 修复样本切分边界的非计划调仓：旧实现会在验证/测试窗口前一日强制生成信号，令窗口首日出现并非周度计划内的成交。组合内核现只允许在冻结的官方周度调仓日决策；验证窗口首笔调仓为 2025-07-21，测试窗口首笔调仓为 2026-01-26。
- 修复后 G8 验证收益为 36.0887%、最大回撤 4.0646%、Sharpe 3.7787；测试收益为 7.4591%、最大回撤 6.6641%、Sharpe 0.9550；严重成本压力收益为 6.9363%。测试收益高于基准约 2.49 个百分点，但 Sharpe 低约 0.20、回撤高约 1.31 个百分点，因此只能视为有希望的研究候选，不能解释为稳定优势。
- 新增 `services/portfolio_forward.py`：前向记录只能在官方收盘后、下一官方交易日开盘前生成，禁止补录错过日期；错过窗口、数据契约阻断和决策重放冲突均写入追加式审计事件，不能靠后续重算清除。
- 新增显式活动候选登记 `runtime/reports/active_portfolio_candidate.json`。影子观察和留出工具默认只读取已锁定候选，不再按文件修改时间自动选择最新报告；候选、研究批次、实现指纹和稳健性报告均使用 SHA-256 绑定。
- 新增固定稳健性体检 `services/portfolio_robustness.py`：7/7 个预先声明的参数邻域为正，13 个逐标的剔除中 12 个为正，10 万/100 万/1000 万美元研究规模均未触发部分成交。剔除 ASML 后收益为 -0.7850%，该单标的依赖已作为正式警告保留，不能在前向期继续调参消除。
- 修复未来公司行动污染日线缓存的问题：同等级前复权数据追加新日线时，会用重叠日比例链入既有缓存价格尺度；无重叠、非一致历史修订或复权合同不兼容时拒绝写入，而不是把新旧价格尺度拼成伪跳空。
- 最终 G8 报告为 `runtime/reports/portfolio_research_20260801_091522.json`，批次哈希 `5a3a4a30c892d243c913549c498eff5e1b7db8b1b4e620614865cb1556351de5`，冻结数据哈希 `74336b6be1d8d5b3902f0bb2a5e240aa2a502bc7cb1c62b2a30d5bc79abc6ca5`，关键实现指纹 `86c06cfd0cbe8abad261ba7e07eab70e0f72ecc6d9c9c67a8897816be1dc6b11`。
- 当前活动候选为 `runtime/reports/portfolio_candidate_20260801_091522.json`，候选哈希 `480802987d523be032a6ead1eeada14a2971b1bb75a8efd1707d74d8738d2409`；稳健性报告为 `runtime/reports/portfolio_robustness_20260801_091535.json`，报告哈希 `d1b3ae2e86c884f90f3ff0105b75dfecff4beadfe2e5e199a62caf89688d5520`。两者校验均为 `PASS`，但授权状态仍为 `COLLECTING`。
- 2026-07-31 的首个有效前向观察为 WDC/AMD/ASML、观察敞口 22.42098%；重复运行返回 `IDEMPOTENT_REPLAY`。当前自然观察为 1/60、计划调仓为 0/8、捕获违规为 0，`paper_authorized=false`、`live_order_allowed=false`。
- 新增只读 `GET /api/portfolio/forward`，并在 `GET /api/paper/portfolio` 中公开前向门禁。完整 Python 回归现为 243 项并全部通过；Python `py_compile`、`node --check app.js`、`node --check chart_quality.js` 和 Electron `npm.cmd run check` 均通过。本地浏览器已确认行情工作台、AAPL 日线和数据状态正常渲染、无空白主图。

### G9 外部时钟证明、自动捕获与运行告警

- 新增 `services/trusted_clock.py`：并行读取 OKX `GET /api/v5/public/time` 与 Coinbase `GET /v2/time` 两个无需密钥的公开 HTTPS 时间源，记录请求往返时间、相对本机偏移、来源间差值和证据哈希。本机偏移超过 30 秒、双源相差超过 5 秒或没有任何外部来源时阻断捕获；单来源只能以明确降级状态继续。
- 前向捕获窗口进一步收紧：官方收盘后等待 5 分钟让日线定稿，并在下一交易日开盘前 5 分钟截止；每条有效观察必须绑定通过校验的外部时钟证明。账本新增外部时钟计数和时钟违规计数，60 日门槛要求至少 60 条外部证明观察。
- 新增 `services/portfolio_forward_scheduler.py` 与 `run_portfolio_forward_scheduler.py`：每次先做轻量交易日历预检，只有窗口开启或存在待登记漏捕时才启动完整组合重算；跨进程原子锁禁止两个任务同时运行，陈旧锁保留副本后恢复，无法确认锁主时宁可阻断。
- 新增追加式 `portfolio_forward_scheduler_alerts.jsonl` 和原子状态文件。漏捕、账本阻断、时钟失败、观察器失败会形成去重告警；普通等待、已完成和数据尚未定稿不会重复刷屏。只读前向 API 现在同时返回任务心跳、状态年龄、时钟质量和运行健康。
- Windows 计划任务 `HakimiTradeV2-PortfolioForwardObservation` 已安装为每 15 分钟运行，绑定真实解释器 `C:/Users/Administrator/AppData/Local/Python/pythoncore-3.14-64/python.exe`，启用 `StartWhenAvailable`、唤醒运行和忽略并发实例；两次 Task Scheduler 实测返回码均为 0。
- 实机演练发现并修复两个 Windows 缺陷：子进程结果包含中文绝对路径时，非 UTF-8 输出流会触发 `UnicodeEncodeError`；安装器最初解析到 WindowsApps Python 别名而非真实解释器。失败状态和旧候选观察均保留，但不会进入最终候选计数。
- 最终 G9 仍使用 G8 的同一参数、同一 `2026-07-30` 截止数据和 0 次本代调参；验证、测试和成本压力指标完全一致。报告为 `runtime/reports/portfolio_research_20260801_094741.json`，批次哈希 `100aca31921b5c7abe958b4a6e44a480bbb2ae51cf2f0f8c5c9ab9ba53f62844`，数据哈希仍为 `74336b6be1d8d5b3902f0bb2a5e240aa2a502bc7cb1c62b2a30d5bc79abc6ca5`。
- 最终活动候选为 `runtime/reports/portfolio_candidate_20260801_094741.json`，候选哈希 `3a1c23ee7c7e84643176d970aebbdbc407cf4357f137b5e5f37c8cee7b460773`，29 个实现文件指纹为 `b49381310e582a6e64936259c1cac6dbe5d20f5f8c275b0fca969c0627edebc5`；稳健性报告 `runtime/reports/portfolio_robustness_20260801_094751.json` 的哈希为 `39d306a14cffef3d21d5b99374f85491ed7af1a7b11d234e8db7cb3b53295819`，ASML 剔除警告继续保留。
- 最终候选的 2026-07-31 观察目标为 WDC/AMD/ASML、敞口 22.42098%，决策哈希 `7bd7a1dffe2567235a207791db59fd04e871d834ee8c874c6436268c0c943b6d`，风险快照哈希 `975bdd47e200ab9b0ad8ad427c30d88060925511dd37b7f5e8878285948c58b3`。当前自然观察 1/60、外部时钟观察 1/60、计划调仓 0/8、捕获违规 0、账本完整性 `PASS`。
- 交易总控新增“组合前向观察”状态卡，显示外部时钟、自然样本、计划调仓和调度状态；1280 宽度下改为四列分行，长审计标识可安全换行。完整 Python 回归现为 258 项，Python `py_compile`、两个 Node 语法检查和 Electron `npm.cmd run check` 均通过。

### G10 市场数据修订账本、冻结数据契约与最终内部候选

- 新增内容寻址的市场数据修订账本 `services/market_data_revision_ledger.py`，当前契约为 `market-data-revision-ledger-v5`。供应商观测、已接受缓存和回测数据集分别留存快照；历史价格/成交量修订、删行、统一价格重定基、公司行动元数据变化和跨源差异均有明确分类、事件哈希和人工解决记录。全局摘要会返回未解决阻塞明细，不再只有数量。
- 回测数据窗口作用域改为同时绑定 `first_date + through_date`。研究、稳健性复核和前向观察统一调用“先对齐、再对实际使用行集证明、最后生成冻结清单”的服务函数，修复了同一 519 行数据在不同脚本中产生不同哈希，以及滚动窗口被误判为历史删行的问题。非阻塞审计阶段从 `REVIEW` 变为 `PASS` 不会改变数据身份，真实 `BLOCK` 仍会立即阻断。
- 旧 v4 作用域产生的 6 条假删行阻塞已按原事件哈希逐条显式解决，理由固定为“旧作用域缺少起始日，已迁移至 v5 精确窗口并通过 v8 稳健性与前向观察验证”；历史事件没有删除。当前修订总控为 `REVIEW`，未解决历史阻塞 0、跨源阻塞 0，只剩 NVDA 的 1 条跨源时效复核。
- 股票数据审计报告为 `runtime/reports/stock_data_audit_20260801_111010.json`，报告哈希 `5c657020c3926879239b5e3c38cc553330704a191f47d41f6627d0976079a02a`：14 个标的中 13 个 `PASS`、1 个 `REVIEW`、0 个 `BLOCK`。NVDA 的 Futu/Yahoo 独立重叠收益方向一致，但最近重叠日期仍为 2024-07-31，因此不能写成近期双源确认。
- `fast=true` 股票快照改为只读本地报价与缓存，不再暗中触发上游报价。冷启动实测 AAPL/NVDA/WDC 分别约 168/51/45ms，`upstream_quote_calls=0`；后台刷新仍独立运行，旧缓存或非实时来源继续禁止增加模拟风险。
- 最终研究报告为 `runtime/reports/portfolio_research_20260801_111327.json`，批次哈希 `f1832364d4c7a16127440954f69bf7bd0a1931b11805f3f7ef9611cb730f2225`，冻结数据哈希 `c6a3a0b940c53b8bb0231db373675bacae3ba6adf531e82ba5bcd98e8073f3d1`。验证收益 36.0887%、最大回撤 4.0646%、Sharpe 3.7787；测试收益 7.4591%、最大回撤 6.6641%、Sharpe 0.9550；严重成本压力收益 6.9363%。测试段 Sharpe 和回撤仍弱于基准，结论保持 `PROMISING_NEEDS_FRESH_HOLDOUT`。
- 当前活动候选为 `runtime/reports/portfolio_candidate_20260801_111327.json`，候选哈希 `fb8369535e777931e9eb90c33805f842e1709e25a6167f47940d213662685117`，实现指纹 `603411817d5209381011c2f1a5fd65b4222d7994e30797212ac217147d778fbc`。稳健性报告 `runtime/reports/portfolio_robustness_20260801_111338.json` 的哈希为 `9e4d6f044994108fe1bff128463d02b84bd8e91eb72e1ebcfa42110a3484d4b8`：7/7 参数邻域为正，13 个逐标的剔除中 12 个为正，10 万/100 万/1000 万美元研究规模均无部分成交；ASML 依赖警告保留。
- 最终候选已记录 2026-07-31 的首条外部时钟证明观察：WDC/AMD/ASML，观察敞口 22.42098%，决策哈希 `e09c95d4745ab619afba7ec67204538eb23a73fdb75e8c899c8117a8bd474588`，风险快照哈希 `308e1f51f4f5ce43cdc965cae740c373dc5048c93dc330a25b3e0e559fc6274e`。当前自然观察 1/60、外部证明 1/60、计划调仓 0/8、捕获违规 0，状态为 `COLLECTING`。
- 调度器失败状态现在保留观察器 `reason` 和具体阻塞项，哈希不一致输出压缩为日期、行数和关键哈希，不再打印数千行日历。Windows 计划任务手动复跑结果为 0、无漏跑；完整 Python 回归为 279 项并全部通过，Python `py_compile`、`node --check app.js`、`node --check chart_quality.js` 和 Electron `npm.cmd run check` 均通过。
- 本地浏览器最终验收覆盖 AAPL → NVDA → WDC → AAPL 连续切换：标的、日期范围和 1021×380 K 线画布保持一致且均非空；质量警告已按界面分隔符去重。黑底、蓝底、白底三主题在真实保存流程下均同步覆盖总控区。交易总控显示行情 `READY`、修订 `REVIEW`、版本待核 0、双源待核 1，组合前向为 `COLLECTING / 1/60 / 0/8 / UP_TO_DATE`，实盘保护墙为“永久锁定”，浏览器控制台 0 条错误或警告。`paper_authorized=false`、`live_order_allowed=false`，实盘硬保护墙未改变。

### G11 内部回测准入、历史暴露与候选激活时序

- 重新审计前向样本的因果时序后，确认 G8/G9/G10 曾记录的 `2026-07-31 1/60` 不能成立：候选是在该交易日官方收盘后才冻结并激活，不能把已经完成的信号日算作自然形成的前向观察。旧记录和历史报告保留作为审计证据，但其结论由 G11 明确取代；该日期现记为中性的 `PRE_ACTIVATION_SKIPPED`，不计通过、不计失败，也不进入 60 日门槛。
- 活动候选注册表升级为 `active-portfolio-candidate-v2`，候选激活必须绑定 OKX/Coinbase 外部时钟仲裁、候选哈希和注册表哈希；激活时间为 `1785584802970`。每条新观察还必须证明激活时刻严格早于对应信号 K 线的官方收盘。显式 `--candidate` 参数已被禁止写入前向证据，所有自然观察只能从已激活注册表进入。
- 新增组合研究时间暴露审计和静态研究标的池合同。当前测试窗口已在 29 份历史研究报告中重复暴露，因此统计结论固定为 `DEVELOPMENT_EVIDENCE_ONLY`；当前静态观察池也不是时点化成分股历史，幸存者偏差尚未受控。系统可以开展内部回测工程验证，但不能把该测试窗重新包装为未见样本或据此授权模拟交易。
- G11 研究报告为 `runtime/reports/portfolio_research_20260801_114620.json`，批次哈希 `a14fd13b3c056d42708054774b29385406ba387b2b28b138e401a76b757a18a0`，冻结数据哈希 `c6a3a0b940c53b8bb0231db373675bacae3ba6adf531e82ba5bcd98e8073f3d1`。验证收益 36.0887%、最大回撤 4.0646%、Sharpe 3.7787；开发测试收益 7.4591%、最大回撤 6.6641%、Sharpe 0.9550；严重成本压力收益 6.9363%。内部回测准入为 `INTERNAL_BACKTEST_READY`，机制结论仍为 `PROMISING_NEEDS_FRESH_HOLDOUT`。
- 当前活动候选为 `runtime/reports/portfolio_candidate_20260801_114620.json`，候选哈希 `a6a7cdd3142f6a4fffdf93d520fdd383fce827f0fa4f8769a2b715308c56d37e`，实现指纹 `d14998a31e9636668923d877c190cac48706d00f0589574ce75b673a79590c3e`。候选、活动注册表和激活证明校验均为 `PASS`，授权状态为 `BLOCKED_PENDING_FRESH_TEMPORAL_HOLDOUT_AND_FORWARD`，`paper_authorized=false`、`live_order_allowed=false`。
- 稳健性报告为 `runtime/reports/portfolio_robustness_20260801_114636.json`，报告哈希 `d46da9f01d8d41fbbd04db4f00f1b74272dd31156ded17374cacedfffa28d44a`：7/7 参数邻域为正、13 个逐标的剔除中 12 个为正，10 万/100 万/1000 万美元研究规模均无部分成交；ASML 依赖警告继续保留。
- 当前前向账本为 `COLLECTING`：有效自然观察 0/60、外部时钟观察 0/60、计划调仓 0/8、中性激活前跳过 1、捕获违规 0、账本完整性 `PASS`。计划任务 `HakimiTradeV2-PortfolioForwardObservation` 最近返回码为 0，调度状态 `UP_TO_DATE`；下一条有效样本只能来自激活后真正完成的新交易日。
- 完整 Python 回归现为 286 项并全部通过；`node --check exchange_terminal/static/app.js`、`python -m py_compile exchange_terminal/server.py` 和 Electron `npm.cmd run check` 均通过。重启后的本地浏览器验证 AAPL → NVDA → AAPL 均立即显示 1021×380 非空 K 线，控制台 0 条错误或警告；控制中心已显示 `COLLECTING / 0/60 / 0/8 / UP_TO_DATE`。

### G12/G13 单次预注册实验与内容寻址激活

- 新增 `services/portfolio_experiment.py` 和 SQLite 实验注册表 `runtime/portfolio_experiments.sqlite3`。研究协议、意图、关键源码指纹和外部时钟证明必须先冻结，再以唯一实验编号领取一次执行权；重复领取、并发领取、协议漂移、源码漂移、事件重放、哈希链篡改和损坏 JSON 均按 `BLOCK` 处理。未提供已登记实验编号时，研究入口会在读取行情前停止。
- 内部回测准入升级为 `portfolio-backtest-admission-v2`，冻结候选和活动候选注册表分别升级为 v3。候选冻结、稳健性体检和显式激活必须绑定同一实验、同一批次、同一数据集及完成收据；激活和后续加载都会重新读取报告与候选的实际路径和 SHA-256，文件缺失、替换或收据不一致时立即阻断。实验注册表和全部验证结果始终声明 `paper_authorized=false`、`live_order_allowed=false`。
- G12 用于验证首版预注册流程；完成腐坏数据与实际工件复核加固后，源码指纹已变化，因此没有继续沿用 G12 候选。最终 G13 实验编号为 `pexp-1785587914047-004335ab9f84`，协议哈希 `f5659dcfe7c276d030681e114935e5e0ac9e9ad523c77dc3184a802a4e485866`，意图哈希 `788d55ee2439bca7bbf5e3e291263acebd116cedf5d3c9a8d76049aa3cd6d3f8`，实现指纹 `c61529d4c7552785eda3f83dd6394feb8608e5511e10ac8ddba9572a10381100`；全局事件链审计为 `PASS`。
- G13 研究报告为 `runtime/reports/portfolio_research_20260801_123845.json`，文件 SHA-256 为 `15eab4d86c521e3a8c7f2c9d5149461dd47e7705861ba207be19609bfbc00757`，批次哈希 `0686984a6be5a372735f877aafa6f1f08bc4f34ad40d6d9b607dbc44e4f45b35`，冻结数据哈希 `c6a3a0b940c53b8bb0231db373675bacae3ba6adf531e82ba5bcd98e8073f3d1`。验证收益 36.0887%、最大回撤 4.0646%、Sharpe 3.7787；开发测试收益 7.4591%、最大回撤 6.6641%、Sharpe 0.9550；严重成本压力收益 6.9363%。测试窗口已有 31 份历史报告暴露，统计状态继续固定为 `DEVELOPMENT_EVIDENCE_ONLY`。
- 最终活动候选为 `runtime/reports/portfolio_candidate_20260801_123845.json`，候选哈希 `453c777d236eeaa44eda45ad5d1858d0c666966faa7909cbf50ab830e649d56d`；完成收据哈希 `a972622271de9aabc59f7b82bb9794a1193c609a0c4234184765daee9a736361`。稳健性报告 `runtime/reports/portfolio_robustness_20260801_124036.json` 的逻辑哈希为 `ea18f907223a3e62222d846cb73d6c553597a0cbc87afe1364fa404f426592cb`：7/7 参数邻域为正、13 个逐标的剔除中 12 个为正，10 万/100 万/1000 万美元研究规模均无部分成交；ASML 依赖警告保留。
- G13 首次前向运行正确把 2026-07-31 记为 `PRE_ACTIVATION_SKIPPED`。当前自然观察 0/60、外部证明 0/60、计划调仓 0/8、捕获违规 0、账本完整性 `PASS`；计划任务 `HakimiTradeV2-PortfolioForwardObservation` 已启用，手动执行返回码 0、漏跑 0，调度器为 `UP_TO_DATE`。
- 完整 Python 回归现为 303 项并全部通过；相关 Python 文件 `py_compile`、`node --check exchange_terminal/static/app.js` 和 Electron `npm.cmd run check` 均通过。最终服务已在 `127.0.0.1:8765` 重启，错误日志为空；页面标题、活动候选、实验注册表、前向状态和异常 `limit` 参数降级均经真实 HTTP 请求验证。浏览器验收仍为 AAPL → NVDA → AAPL 非空 K 线且控制台无错误，本轮其后未再修改前端代码。

### G14/G15/G16 测试隔离、时点宇宙执行与模拟授权硬门

- 新增 `services/portfolio_paper_activation.py` 和 `portfolio-paper-activation-v1` 内容寻址授权收据。多标的账本升级为 `portfolio-paper-ledger-v2`：初始化参数不能直接打开模拟，旧版无绑定启用状态会自动停用；每次填单前都重新核对活动候选、稳健性、前向成熟度、调度新鲜度和人工批准。当前组合账本现金为 0、模拟关闭、持仓为 0，没有 HTTP 写入路由，`paper_authorized=false`、`live_order_allowed=false`。
- 测试运行时支持显式 `HAKIMI_RUNTIME_DIR`，标准 `unittest discover` 由首个测试模块在导入 `server.py` 前切到临时目录。完整 323 项回归全部通过，并对 12 个生产运行时数据库做测试前后 SHA-256 对比，变化数为 0；测试不再初始化或改写生产账本、公司行动、行情修订和实验注册表。
- 新增 `portfolio-research-universe-v2`。回测执行器会按每个交易日的成员生效区间筛选标的，并在成员移除时强制退出；候选、准入、稳健性和影子观察都绑定同一宇宙合同。当前 13 个交易标的仍来自现时静态观察池，合同状态为 `STATIC_RESEARCH_UNIVERSE`、历史成员验证为 false、幸存者偏差为 `UNCONTROLLED`，因此只解决了执行器支持和强制问题，没有声称消除历史名单偏差。
- G14 实验 `pexp-1785590081336-03c829b4e6eb` 完成后，首次稳健性运行正确被阻断：逐标的消融删掉行情标的却继续携带父宇宙合同，13/13 消融均触发合同不一致。失败报告 `runtime/reports/portfolio_robustness_20260801_131734.json`、逻辑哈希 `a1620f1b1e7559cb3a14065a8d66e67354b44cb6536f9bd64cebb34032807ed5` 保留审计，G14 没有激活。
- 修复加入“已验证父合同只能派生子集”的血缘合同，并发现及修正合同自身标为 `BLOCK` 时校验器仍可能返回 `PASS` 的失效关闭漏洞。合法子集保存父哈希、移除标的和用途；新增父合同以外标的、篡改移除列表、父合同损坏或声明阻断都会继续 `BLOCK`。
- G15 实验编号为 `pexp-1785590499089-1dd8663ac3cb`，协议哈希 `a28ea909338a9b24417475263e4e6a61630fcbe4214ed912d6c2c692abcbdc13`，意图哈希 `ffa79c8141f133c5ba554b82eb24b7da897952ac50d4e228a4acbe4eed8ce2b6`，实现指纹 `2069023eb0bcead258f35be2fedd792260baabdf04f1b9e9d06663ce58ae7eeb`；单次领取、完成收据和全局事件链审计均为 `PASS`。
- G15 研究报告为 `runtime/reports/portfolio_research_20260801_132149.json`，文件 SHA-256 `745bcac238aa190190270c7c8090d757e050a56de8314b4c9472d09d688b1b47`，批次哈希 `4a14ea553c58c3c7aa45d8042baa20da8f26dd2eb8a48766f55c8117ae7c5a85`，冻结数据哈希 `47fc192fcbdd05f3d5a166282a9f624a3f2d82c2d88477c647504d2a393c8803`。验证收益 36.0887%、最大回撤 4.0646%、Sharpe 3.7787；开发测试收益 7.4591%、最大回撤 6.6641%、Sharpe 0.9550；严重成本压力收益 6.9363%。测试窗口已有 33 份历史报告暴露，结论仍是 `DEVELOPMENT_EVIDENCE_ONLY`。
- G15 候选及稳健性本身均通过，但人工运行调度器 `--dry-run` 时发现预览结果会覆盖正式调度状态文件，导致控制中心把健康调度错误显示为 `BLOCK`。调度器现已拆出纯状态构建函数：`--dry-run` 只返回 `PREVIEW_ONLY_NOT_RECORDED`，不再写正式工件；回归测试同时校验预览前后文件字节完全一致。因为修复改变了冻结实现指纹，G15 按规则作废，不沿用其前向账本。
- 当前活动候选升级为 G16。实验 `pexp-1785591041976-67b6f9140cd8` 的协议哈希为 `f1dd44015b0efba38b37b21f615b53789501febcae6192b9d39bcfb92a2884a8`、意图哈希为 `ec32b9c042b016913112c8172c0bdafa3dacd7547256f7d7cecbf859f6941fc4`、实现指纹为 `c97334df45532bdad7509722eff58841eb6d39660328f5a6161ac326d8995d3c`；单次领取、完成收据和全局事件链审计均为 `PASS`。
- G16 研究报告为 `runtime/reports/portfolio_research_20260801_133051.json`，文件 SHA-256 `18b1e541c88075d260eb3746a51d3227b0466dc4d4a9631ed64d47fdb2e5c76f`，批次哈希 `4c8e9c3255451e0393f30531b8ed5d6994d07ca665bdc1d240b1489fa5e4d2a8`，冻结数据哈希仍为 `47fc192fcbdd05f3d5a166282a9f624a3f2d82c2d88477c647504d2a393c8803`。验证收益 36.0887%、最大回撤 4.0646%、Sharpe 3.7787；开发测试收益 7.4591%、最大回撤 6.6641%、Sharpe 0.9550；严重成本压力收益 6.9363%。测试窗口已有 34 份历史报告暴露，结论仍是 `DEVELOPMENT_EVIDENCE_ONLY`。
- 当前活动候选文件为 `runtime/reports/portfolio_candidate_20260801_133051.json`，文件 SHA-256 `a8c957f29bd646155692bc1379c8cfdda16051a9ff14de773fdc7e68c3cd7e16`，候选哈希 `289929d9c63a63ed7890bbbc1d10c50c29ee13d4970b5e8c0255751a9abecf34`，完成收据哈希 `cbc03e272bd0e220398741ef28175b6dd0375c0151a6751566956611ccec488a`。稳健性报告 `runtime/reports/portfolio_robustness_20260801_133105.json` 的文件 SHA-256 为 `4b3c175636ad9ce88d20b74ec056ee4a4d36fe926c31b22bc9e12c055f95c01b`、逻辑哈希为 `a0e15833dfbc1c4a91c2379e07d9dba8aa8700dd1de0b5bd1d464ae96fcd9264`：7/7 参数邻域为正，13 个消融中 12 个收益为正，三档资金规模无部分成交；移除 ASML 后收益仍为 -0.7850%，依赖警告保留。
- G16 前向账本正确把 2026-07-31 记录为中性的 `PRE_ACTIVATION_SKIPPED`。当前自然观察 0/60、外部证明 0/60、计划调仓 0/8、捕获违规 0、账本完整性 `PASS`；计划任务已恢复启用，最近返回码 0、漏跑 0，正式调度状态为 `UP_TO_DATE` 且来源为计划任务。重启后的 `/api/portfolio/forward`、`/api/paper/portfolio` 和实验注册表均返回 G16 状态，服务错误日志为空。
- 最终检查：完整 Python 回归 323 项通过且生产数据库变化数为 0；相关 Python `py_compile`、`node --check exchange_terminal/static/app.js` 和 Electron `npm.cmd run check` 均通过。浏览器验收覆盖 AAPL → NVDA → WDC → AAPL → BTC-USDT：前三个股票缓存图约 0.31 秒恢复，BTC 先显示快速预览再由 OKX 实时日线接管，所有主图均非空，控制台 0 条错误或警告。

### G17/G18 历史成交演练、执行风险余量与稳定数据身份

- `RiskService` 新增经过证明的历史模拟数据合同：只有 `SIMULATION` 且数据明确声明 `historical + attested + can_simulate`、无 fallback、无隔离并处于历史就绪状态时，才允许历史回放增加风险；普通 `PAPER` 订单仍不能把历史数据冒充实时数据。
- 新增 `services/portfolio_execution_rehearsal.py` 和 `run_internal_execution_rehearsal.py`。它们在内存中把冻结研究成交逐笔送入真实 `RiskService`、组合风控、`PaperExecutor`、事件血缘和确定性回放，检查费用、滑点、现金、持仓、权益、换手、幂等、订单生命周期、公司行动和来源权限；任何阶段失败都只返回研究阻断，不产生模拟或实盘权限。
- 首次对 G16 执行完整演练时正确发现风险模型与回测执行之间的偏差：完整段只有 79/123 笔通过基础风控、100/123 笔通过组合风控，少数买入在费用和执行价后令净敞口略高于 60% 硬上限，随后形成级联拒绝。失败工件 `runtime/reports/portfolio_internal_execution_rehearsal_20260801_220006.json` 和哈希 `5c33e43ccd27f53b92e7e8cd09bd69f6e91692bc1181e4c170bbea75da5bd64e` 已保留。
- 回测执行器增加固定 0.25 个百分点的 `execution_risk_buffer_pct`，并把未缓冲目标、缓冲值和最终目标写入每个决策及运行合同。执行演练成为研究准入的强制门禁，风险服务、模拟执行、事件回放、组合账本及演练入口也进入实现指纹，后续任何执行栈变化都会令旧候选失效。
- G17 完成了修复后的整套研究与演练，但随后发现组合 `data_hash` 错把策略 schema 版本纳入数据身份：相同 14 个标的、519 行、相同逐标的快照和修订哈希会因代码版本变化而得到不同数据哈希。G17 保留审计但没有激活；数据身份现独立为 `portfolio-aligned-market-dataset-v1`，策略 schema 和数据清单哈希分别记录，回归测试证明策略版本变化不会改写数据身份。
- 最终 G18 实验编号为 `pexp-1785593284245-1a0bd86142c9`，协议哈希 `f685cd3a6f67e424170c72dd690bfcef1729954bdfde0e3d1ef0ffeb95da3b5b`，意图哈希 `46225a2c629a3d2bbcc5d36d34de10cc5ab5a3cd6497e5308654f5147f228e30`，实现指纹 `e540bcc878a090919a0d36fd87fa0cf566b86e64dc0c5f23b02eb54adf7904d9`，实验完成收据哈希 `26c9eb95792d434594e13369ed1ee744c4a2bd154f0e4dc47292964dc984b7a0`。
- G18 研究报告为 `runtime/reports/portfolio_research_20260801_140815.json`，文件 SHA-256 `0d38748ab0876e9b836ed8015d2501a3c4631bd172397bc1f6cb4c1a01a9ed52`，批次哈希 `a62e439beac595f3c263b38e3b3d02dad9f7d97875d20f76f05286467f372a2c`，稳定数据哈希 `9f4f6d7202177d71c5fd93c2fd434c8cd29b45b431a52230356bc4a1e50c7573`。验证收益 35.8862%、最大回撤 4.0415%、Sharpe 3.7788；开发测试收益 7.4126%、最大回撤 6.6002%、Sharpe 0.9559；严重成本压力收益 6.9762%。测试窗口已有 36 份历史报告暴露，结论仍为 `DEVELOPMENT_EVIDENCE_ONLY`。
- 当前活动候选为 `runtime/reports/portfolio_candidate_20260801_140815.json`，文件 SHA-256 `65f5f9665df798ebf71e93660bb3c33306d8eba23b0bb04fda00c5cbea06573e`，候选哈希 `ec532c9fb6638e9daee0bbf2446bb14440d150862be59d2249db3a0cd8b1891e`。稳健性报告 `runtime/reports/portfolio_robustness_20260801_140846.json` 的文件 SHA-256 为 `be72e342c1b56dbbca87e80d49790e5f2c1f83986466b6e13f09af8735689ac7`、逻辑哈希为 `07360b76d6dd537a2479547e4cef9aeedaf84a2d707d5f62e57321486ff099ac`：7/7 参数邻域为正，13 个消融中 12 个为正，三档规模无部分成交；移除 ASML 后收益为 -0.7662%，依赖警告保留。
- G18 已通过候选、稳健性、外部时钟、实验完成收据和实际工件绑定后显式激活。2026-07-31 继续只记为 `PRE_ACTIVATION_SKIPPED`；当前自然观察 0/60、外部证明 0/60、计划调仓 0/8、捕获违规 0、账本完整性 `PASS`。计划任务 `HakimiTradeV2-PortfolioForwardObservation` 已实跑返回 0，状态 `UP_TO_DATE`，`paper_authorized=false`、`live_order_allowed=false`。
- 激活后独立成交演练工件为 `runtime/reports/portfolio_internal_execution_rehearsal_20260801_221148.json`，工件哈希 `ca5164997d69e022981ebddc1fdfdff7f0a95b49ca71e286add99ba8573b43be`。验证 55/55、测试 36/36、完整 123/123 笔订单均通过基础风控、组合风控、成交生命周期和事件血缘，三段账务检查全部为 `PASS`。
- 完整 Python 回归现为 333 项并全部通过；相关 Python `py_compile`、`node --check app.js`、`node --check chart_quality.js` 和 Electron `npm.cmd run check` 均通过。Electron 真实烟雾测试还发现并修复“启动后延迟加载的 `start_module` 覆盖用户首次导航”的问题：一旦用户已点击或按键，启动配置不再抢占当前工作区；完整桌面 smoke 与 K 线 chart-smoke 均通过。
- 重启后的 API 返回 G18、`COLLECTING / 0/60 / 0/8 / UP_TO_DATE`、调度健康 `PASS`，组合模拟关闭且实盘禁止。浏览器验证 NVDA、WDC、AAPL 缓存 K 线约 0.30 至 0.31 秒完成一致切换，BTC-USDT 约 0.31 秒显示 OKX 快速缓存并在约 2.1 秒更新为实时日线；所有画布为 1021×380 且绑定正确标的，稳定观察期间无旧标的回写，控制台 0 条错误或警告。
- 新增独立 `services/portfolio_statistical_audit.py` 和 `run_internal_portfolio_statistical_audit.py`，使用成对的 5 日循环区块重采样比较策略与 60% SPY 基准。固定合同要求至少 120 个日样本、5000 次确定性重采样、90% 区间、95% 正超额概率，并按 8 次历史开发试验执行单侧 Bonferroni 惩罚；门槛、输入工件、数据集、运行哈希和随机种子全部进入内容哈希，审计永远不产生执行权限。
- G18 统计晋级报告为 `runtime/reports/portfolio_statistical_audit_20260801_223108.json`，审计哈希 `4ef6922808c2f469ab050e1452ab8eb613b88aa223007e72d4b66bab3b7794df`，工件哈希 `f5cc78c5d39f16497a45ce3b0ae1c7703a47fb3b0acac3db095ce5476cfef84b`。验证段相对收益约 29.8655%、信息比率 3.8479、正超额概率 99.88%、选择调整后 99.04%，状态 `PASS`；测试段相对收益约 2.4463%、信息比率 0.4336，但正超额概率只有 59.74%、选择调整后为 0，90% 超额收益区间约 -12.8682% 至 20.4809%，状态 `BLOCK`。
- G18 的统计阻断本身没有触发调参或新策略候选，也没有重置当时的自然观察账本；随后建立 G19 的唯一原因是修复下一节所述的前向账户状态合同。统计结论仍只能用新形成的前向收益序列或预注册的新数据窗重新审计，不能在已暴露的 130 日测试段上继续优化到通过。

### G19 干净前向账户与逐日绩效证据链

- 重新审计发现 G18 的影子观察只统计决策，没有结算现金、持仓、费用、成交、权益、回撤和基准收益；更关键的是，观察器从完整历史回测继承了假设持仓，而新的前向账户必须从候选激活后的首个有效交易日以纯现金开始。两者可能令首个周度决策携带账户实际从未持有的 `retained_symbols`。G18 因实现合同不一致退役，且在退役前没有任何有效自然观察，旧数据没有迁移到 G19。
- G19 只修复账户状态和绩效证据合同，策略参数、交易标的、费用、滑点、风险余量、调仓规则和冻结数据均与 G18 相同，本代调参次数为 0。实验编号 `pexp-1785597238895-6d1a9d5f02c9`，协议哈希 `68cf0029bb569711da390188bef832e310f266f1be7d7bc65b07ebf7cb827f93`，实现指纹 `cf9f802519a0cd85ef23bcd202e3ea26bd102a49312707f1476b0548efb07da5`，完成收据哈希 `17002c7f8c84f08ca36ead8234f608e65d934f566882e5c35847b6c9228cc035`。
- G19 研究报告为 `runtime/reports/portfolio_research_g19_clean_forward_state.json`，文件 SHA-256 `f4c8eaf9881f205ce84db563842d37da19ccd4250a8d070f6519556c9409bf1d`，批次哈希 `7910248e478e64d66ddb14caf12d48ac70f79130ce1402d94fd86e6649c8d0e0`，冻结数据哈希仍为 `9f4f6d7202177d71c5fd93c2fd434c8cd29b45b431a52230356bc4a1e50c7573`。验证收益 35.8862%、最大回撤 4.0415%、Sharpe 3.7788；开发测试收益 7.4126%、最大回撤 6.6002%、Sharpe 0.9559；严重成本压力收益 6.9762%。这些历史指标没有因账户修复得到改善，仍只能算开发证据。
- 当前活动候选为 `runtime/reports/portfolio_candidate_g19_clean_forward_state.json`，文件 SHA-256 `9cdc3d775e94661c890872d5ae364decfd041787d3a0c66dacefa4273bdd1f12`，候选哈希 `5ec05a41fab15a9ce64a5afd0f806dd32f8ac2cb792e759e2c018dd2626a663d`。稳健性报告 `runtime/reports/portfolio_robustness_g19_clean_forward_state.json` 的文件 SHA-256 为 `e5de0abac332279487fd10f8f3e832871ed200a3cc7c1ec518015fa9b5642a73`、逻辑哈希为 `18d9d173613fd0b470663eb584ea880ab42beec3531b5a50622657f404299a80`：7/7 参数邻域为正，13 个逐标的消融中 12 个为正，三档资金规模无部分成交，移除 ASML 后不为正的依赖警告继续保留。
- 影子合同升级为 `portfolio-shadow-observation-v7`，每个有效观察必须绑定 `portfolio-forward-state-v1`：候选激活后的首个有效交易日、固定起始索引和日期、初始现金、零继承持仓、激活登记哈希、执行模型和零权限声明都进入内容哈希。历史 `retained_symbols` 与实际前向账户不一致时会以 `decision_retention_state_mismatch` 硬阻断；同一候选的起始状态合同中途变化也会硬阻断。
- 新增 `services/portfolio_forward_performance.py`、`run_portfolio_forward_performance.py` 和计划任务 `HakimiTradeV2-PortfolioForwardPerformance`。追加式 SQLite 哈希链在下一交易日开盘结算前一日已捕获决策，记录手续费、滑点、成交、换手、现金、持仓、敞口、权益、回撤，并以相同 60% 总敞口建立 SPY 买入持有基准；数据清单、逐行行情哈希、观察哈希、决策哈希、状态合同和上一结算哈希全部绑定。该账本仅作研究模拟，没有模拟账户或实盘执行权限。
- G19 成交演练 `runtime/reports/portfolio_internal_execution_rehearsal_g19_clean_forward_state.json` 的工件哈希为 `a781dbbd81552cd298f7469c837cd0126ad2deb877c9961ed6dae3f19ff93ae2`；验证 55/55、测试 36/36、完整 123/123 笔订单均通过基础风控、组合风控、生命周期和事件血缘检查。统计报告 `runtime/reports/portfolio_statistical_audit_g19_clean_forward_state.json` 的审计哈希为 `cf653e9f52be4e2835ec2cf826357aed5d709c7002a5377515892ae66bc8f700`、工件哈希为 `3455a7744faa0a6fa136b105beaad58858677d070aef69a7910467d214fec556`；验证段 `PASS`，测试段仍为 `BLOCK`，历史统计否决继续是晋级硬门禁。
- G19 在 2026-08-01 激活，2026-07-31 被正确登记为中性的 `PRE_ACTIVATION_SKIPPED`。当前有效观察 0、绩效结算 0、收益期 0、执行调仓 0；状态为 `COLLECTING`，不是失败也不是通过。首个结算日只建立纯现金基线，不产生收益期，因此 60 个前向收益期通常至少需要 61 个连续有效结算日；同时必须有至少 8 次执行调仓、零账本/捕获/权限违规，且历史统计否决需由真正的新时间证据重新审计解决。
- 两个 Windows 计划任务 `HakimiTradeV2-PortfolioForwardObservation` 与 `HakimiTradeV2-PortfolioForwardPerformance` 均已启用，实机手动运行后状态为 `Ready`、最近返回码为 0。`GET /api/portfolio/forward` 与 `GET /api/paper/portfolio` 返回 G19、`COLLECTING`、稳健性 `PASS`、调度健康 `PASS`、只读、无模拟授权、无实盘授权。
- 完整 Python 回归现为 346 项并全部通过，其中新增回归直接验证继承持仓和候选内状态合同漂移都会阻断。相关 Python `py_compile`、`node --check app.js`、`node --check chart_quality.js`、Electron `npm.cmd run check`、完整桌面 smoke 和 K 线 chart-smoke 均通过。NVDA、AAPL、TSLA 日线及 TSLA 盘中/盘后分钟线均成功切换且画布非空；快速切换最终标的绑定正确。

### G20 基准绑定与只读内部回测证据包

- 复核旧内部回测入口时发现，旧 `run_internal_backtest.py` 会导入巨型 `server.py` 并执行无预注册参数网格，既不代表当前组合候选，也可能读取生产运行态；同时 G19 统计审计把缺少基准运行哈希错误归入执行权限阻断。G19 因证据合同不完整退役，失效说明保存在 `runtime/reports/internal_portfolio_backtest_pack_g19_invalidated.json`，逻辑包哈希为 `e606023446bb135da75e8951a790013edbfd5e01b3046c52a6b5578169ac48c9`，该失效包自身校验为 `PASS`。
- G20 只修复基准绑定、统计阻断分类、实现指纹覆盖和内部回测证据合同；策略参数、标的池、费用、滑点、风险预算、调仓语义、数据集及 G19 的历史表现全部保持不变，本代调参次数为 0。实验编号 `pexp-1785598958068-2dc06524c014`，协议哈希 `e98a9550c9a9437843410c1662137656de75bcc3473882a286140cea52f89ed5`，意图哈希 `96e9778e63b2d7df76141a6e85f72d0f808fcec439cfd228a79d8748834218a1`，实现指纹 `03eef4ee3bfd69c66a02a5ae158e5a1138123897f6a861b8fc55124aa7f28761`，完成收据哈希 `351c946a147381697ddc86f2c217619381fc8c2fb806342eeb9d96b2a532441b`。
- G20 研究报告为 `runtime/reports/portfolio_research_g20_benchmark_binding.json`，文件 SHA-256 `7c0bf3bef31e5e676cd75ac27fd4938fdbd5db52426b241aa274987e66b2b8e0`，批次哈希 `aa795fd257779c4a912b58339bd8b982757519e114f201d389d40db6406e93cd`；验证与测试基准运行哈希分别为 `8b4a63b0d6045f36e8327bbfcd769eaf45102b803c0fa086ccfe718e3aef2c94` 和 `4a2528af5584ac5dc967051684b524839b3e61afb36b229cf64cf9ca31ba595f`。历史策略指标与 G19 完全一致：验证收益 35.8862%、最大回撤 4.0415%、Sharpe 3.7788；测试收益 7.4126%、最大回撤 6.6002%、Sharpe 0.9559；严重成本压力收益 6.9762%。
- 当前活动候选为 `runtime/reports/portfolio_candidate_g20_benchmark_binding.json`，文件 SHA-256 `6a77783ef54646a7cfb50db8896f0681adcebf44c2af2843dae2066a12353aca`，候选哈希 `6a450970d1bdbdb3cca0ac73dcf346be5056ead2a8cb0022e2c2e143fbd3d670`；活动登记哈希为 `7e5337fb8ebeab8dad5e18d8cf9d8d7a2f8a94718d4bf5fd6fb69f1176e51b11`。稳健性报告 `runtime/reports/portfolio_robustness_g20_benchmark_binding.json` 的文件 SHA-256 为 `e2c6d8bc40c0ec64a3d7da81f994156c17c87efe89ca8601e9f3c8a3cc929446`、逻辑哈希为 `af41b0524ba382354c905da4b80f6dd7f072c21a3efaf10703022b52234db144`：7/7 参数邻域为正，13 个逐标的消融中 12 个为正，三档规模无部分成交，ASML 依赖警告保留。
- 统计合同升级为 `portfolio-statistical-audit-v2`，明确分离“输入没有执行权限”和“输入证据绑定完整”两项检查。G20 两项均为 `PASS`；统计报告 `runtime/reports/portfolio_statistical_audit_g20_benchmark_binding.json` 的审计哈希为 `14a51f36be465d7febf3bdd7cf7c8a7dfd6cf878d50a5d1c0503499d3e6637e2`、工件哈希为 `8e36e9faadf6f21842dd0a37d09af4c98c33617cd39b7caf989044df49362450`。验证段正超额概率 99.90%、选择调整后 99.20%，状态 `PASS`；测试段正超额概率 60.18%、选择调整后为 0，状态仍为 `BLOCK`。阻断原因现在只描述测试统计证据不足，不再伪装成权限问题。
- G20 外部成交演练 `runtime/reports/portfolio_internal_execution_rehearsal_g20_benchmark_binding.json` 的工件哈希为 `15e543caf7d8fc62b386961972a8cf7cf9a86815255e79d564a35ad593cca651`；验证 55/55、测试 36/36、完整 123/123 笔订单均通过风控、组合约束、订单生命周期和事件血缘检查。该演练仍是确定性研究模拟，不建立模拟账户授权。
- 新增 `exchange_terminal/services/portfolio_backtest_pack.py`，并把 `run_internal_backtest.py` 改为单一活动候选的只读证据打包器。它不导入 `server.py`，不拉取行情、不搜索参数、不创建模拟订单、更不允许实盘订单；缺文件、篡改、候选错配、基准错配、权限污染或调度失效都会闭锁。正式证据包 `runtime/reports/internal_portfolio_backtest_pack_g20.json` 的文件 SHA-256 为 `67e808cbba77ef57f55a9f50a045c269ae8e784d2a89f549f2e76a77c2000fe1`，证据哈希 `2bf5fae5052303e6673eb3049a42fccf35252bfcafd178d121dc640aeef0242c`，包哈希 `0cca8823b93cab481eb3a49b6cca170c6afbd76958133ab2fdeb3c9e3b4908ef`，自校验为 `PASS`，状态为 `INTERNAL_BACKTEST_EVIDENCE_READY`。这只说明内部回测证据链可以复核；晋级状态仍为 `BLOCK`。
- G20 在 2026-08-01 激活，2026-07-31 继续只记为 `PRE_ACTIVATION_SKIPPED`。当前有效观察 0/60、绩效结算 0、收益期 0/60、执行调仓 0/8，观察与绩效账本完整性均为 `PASS`，调度器干跑为 `UP_TO_DATE`。两个 Windows 计划任务均已重新启用，手动运行后为 `Ready` 且返回码为 0；本地 `GET /api/portfolio/forward` 返回 G20、`COLLECTING`、调度健康 `PASS`、`paper_authorized=false`、`live_order_allowed=false`。
- 完整 Python 回归现为 353 项并全部通过；相关 Python `py_compile`、`node --check app.js`、`node --check chart_quality.js` 和 Electron `npm.cmd run check` 均通过。G20 候选、实现指纹、激活证明、实验完成收据、工件绑定和稳健性报告在计划任务实跑后再次校验为 `PASS`。

### G21 实现闭包审计与性能退役

- 继续审计 G20 后发现，实现指纹没有覆盖 29 个可达本地模块，递归权限字段只按真值判断而没有要求精确布尔类型，前向观察与绩效影子审计也没有强制绑定同一状态快照。G21 将实现合同扩展为 83 个本地文件、Python/平台/SQLite 运行时和外部包版本闭包，并补齐严格权限类型与状态快照等价校验；策略参数、标的池、成本、风险预算和历史数据均未改变。
- G21 实验编号为 `pexp-1785600722145-e015c63a2bf3`，实现指纹为 `9916033eda2be81cd747ddd46414b09425c63200af8b2ada2ca89e096df95e13`。完整闭包在每次读取活动候选时重建，导致候选加载约 14.5 秒、端点函数约 19.35 秒、`GET /api/portfolio/forward` 超过 30 秒仍可能超时。G21 在产生任何自然观察或收益结果前退役，正式包哈希为 `46ea7a2cb984a2bb3a2698b82d0ac5aa09c43c7ae9cf5ad5f4e95c93a3a8a87b`，失效说明保存在 `runtime/reports/internal_portfolio_backtest_pack_g21_latency_invalidated.json`，失效包哈希为 `fd58168a9d540f1e5c2fc9c615e5621d76a3f5de1a32a2b564a927c085128929` 且自校验为 `PASS`。由于观察和收益均为 0，没有迁移任何 G21 前向数据。

### G22 快速精确实现核验与内部回测基线

- G22 不调整任何策略参数，只修复 G21 的候选读取性能。注册、领取和构建候选时仍执行 83 文件 AST 导入闭包与运行时依赖全量扫描；运行时读取改为对冻结文件逐一做精确 SHA-256，并精确核对 Python、平台、SQLite、已管理包版本和未管理模块状态，不再重复重建导入图。实验编号为 `pexp-1785601861063-0a20554486de`，协议哈希 `07319f9c8e0a06bd097bbb99f450ff358572c0888a626fc74190a20343148999`，意图哈希 `b4694fd2e90b1fd19431388eb6fe246a8167946260404905764ffe9e190504b5`，实现指纹 `a3587de1b90ca9b3f5d1f4fb807109dfcf51e6b7dbed3f8d4425c5c0c14ba1a1`。
- 研究报告 `runtime/reports/portfolio_research_g22_fast_verification.json` 的文件 SHA-256 为 `cd031abe58a67908c3ec98ed669c62003da809da112bc5419c35d36586832cca`、批次哈希为 `163dfd8410dac85808f32e63b8ee05691da9bfbedef9e1c8ce1d131375ee9552`。冻结数据哈希仍为 `9f4f6d7202177d71c5fd93c2fd434c8cd29b45b431a52230356bc4a1e50c7573`，最后日期为 2026-07-30，共 519 行；验证收益 35.8862%、最大回撤 4.0415%、Sharpe 3.7788，测试收益 7.4126%、最大回撤 6.6002%、Sharpe 0.9559，严重成本压力收益 6.9762%，与 G20/G21 完全一致。
- 当前活动候选为 `runtime/reports/portfolio_candidate_g22_fast_verification.json`，文件 SHA-256 为 `bdefca876b2efe95729159a5693d60e7f857ce34f1fd537d6ee55cceb72de056`，候选哈希为 `0ed66a57f39ced2fa47288c8af8b430a0b4e26d220a7c1ac68ad314a33ec83a8`。五次直接候选核验约为 30.10 至 83.75 ms；最终独立验签加载为 84.0 ms。候选、稳健性、实验完成收据和全部工件绑定均为 `PASS`，`paper_authorized=false`、`live_order_allowed=false`。
- 稳健性报告 `runtime/reports/portfolio_robustness_g22_fast_verification.json` 的文件 SHA-256 为 `17ef8bb6c99032026974c776627ab6a53a05b5a86df885aec8c9e19b67ac2683`、逻辑哈希为 `68c916a76070b2e9eb2e036fc1920e6a531578849de6d06a71877c57a9b62326`：7/7 参数邻域为正、13 个逐标的消融中 12 个为正、三档规模无部分成交，ASML 依赖警告继续保留。隔离成交演练 `runtime/reports/portfolio_internal_execution_rehearsal_g22_fast_verification.json` 的工件哈希为 `def500b619ea989d3b343167286e8482f3d44fbab012553919abda14f13f6a7d`，验证 55/55、测试 36/36、完整 123/123 笔订单通过，且未访问网络、未改变运行态。
- 统计报告 `runtime/reports/portfolio_statistical_audit_g22_fast_verification.json` 的审计哈希为 `f0f7a3c998d34a270b616e39aa31420db1f4ea38039786ab68e870afb3f9d6b1`、工件哈希为 `5a4aff9c5942eaf90b7c68994af6a535214c7f587a9f5aaa7818a11c09fc94a2`。验证段正超额概率 99.90%、选择调整后 99.20%，状态 `PASS`；测试段正超额概率 59.48%、选择调整后为 0，状态仍为 `BLOCK`。当前统计阻断必须由新的自然时间收益序列解决，不能靠重复运行现有样本消除。
- G22 在产生首个有效交易日前保持 `COLLECTING`：2026-07-31 正确登记为 `PRE_ACTIVATION_SKIPPED`，当前自然观察 0/60、前向收益期 0/60、执行调仓 0/8。观察账本和绩效影子审计绑定同一快照哈希 `fcffad67d57b9e47f5fd7b16cf53d8e0064286eacd2b69a2159b2a3968431441`；两个 Windows 计划任务均已启用，手动运行后状态为 `Ready`、返回码为 0，调度健康为 `PASS`。
- 原只读索引包 `runtime/reports/internal_portfolio_backtest_pack_g22.json` 的文件 SHA-256 为 `4905c3cc0144e727a3b3fac973458a216fb1915b3f25735d981bd006838180b9`，证据哈希 `4f3b6e1ac716fec4834c7d3923aa0a5bb59c9a19be4f134e3d90d18770c3dd24`，包哈希 `41a397bb539c9ec736b3fb336dd21560c5609b122a9a73b734c57210ca650c40`，包体自校验为 `PASS`，状态为 `INTERNAL_BACKTEST_EVIDENCE_READY`，晋级为 `BLOCK`。进一步审计发现该索引引用的前向绩效和调度状态文件会被计划任务覆盖，当前字节已与索引声明哈希不同，因此它只保留为历史索引，不再视为可独立恢复的证据包。
- 新增 `exchange_terminal/services/portfolio_evidence_archive.py`、`run_portfolio_evidence_archive.py` 和每日计划任务 `HakimiTradeV2-PortfolioForwardBackup`。SQLite 使用 Online Backup API 抓取 WAL 一致性快照，并把归档副本切换为单文件 `DELETE` 日志模式；整套报告、三个数据库和恢复演练遇到并发刷新会重新抓取，发布前后均做严格清单验签。归档 v2 同时新增 `portfolio_backtest_replay.py` 与随包携带的 `portfolio_backtest_replay_driver.py`，不再只保存结果报告，而是封存生成 G22 的 14×519 根精确 OHLCV 输入，并使用归档内 83 个冻结源码在 `python -I -B` 隔离进程中离线重跑验证、测试、完整三段回测、两个 SPY 基准和两档成本压力；网络与 SQLite 访问均硬阻断且实测尝试数为 0。
- 最新可独立复算的不可变包由 Windows 计划任务实跑生成，路径为 `runtime/backups/portfolio_forward_archives/portfolio-forward-1785606564877-0ed66a57f39c-da77ec80de15`，任务返回码为 0；`manifest.json` 文件 SHA-256 为 `06a2003de67e9250288538098ef82344b7962538bbda234b5e6b9d95853a2319`、清单哈希为 `da77ec80de1561c997f793e27d976573d5e5cc52e3a0371c40589ce64c00caa7`。包内 101 个清单文件、83 个冻结源码、三个数据库 `quick_check`、严格文件类型清单、恢复演练和离线回放均为 `PASS`；精确数据文件哈希为 `f5910ebbf8b5b692b196bb7442a54082b603d61d9bd5e72fe1ce21f71d847530`、数据快照哈希为 `502be96ff67fe4302942705e647a80a19f1ab1a0978c3998e78beacbf4907e45`、离线回放哈希为 `7016e48d0975b3f2869ebdcb9daa97a6ab2b8671bd98da60548601f1f6a9caf5`。快照证据包哈希为 `31d455f7203286907696835c6ab6eee2719d03d06fbb305d28cd228ba1833cac`，状态仍为 `INTERNAL_BACKTEST_EVIDENCE_READY / promotion BLOCK`。
- 独立只读前向看门链升级为 `portfolio-forward-watchdog-v2`。它每 15 分钟核验活动候选、调度状态年龄、观察/绩效候选绑定、影子快照等价、观察/绩效/备份三个任务的启用状态、返回码和最近运行时间，并重新验签最新归档清单与隔离恢复结果；失败与恢复写入独立 JSONL，既不修改策略实现，也不写观察或绩效账本。看门与备份计划任务实跑后均为 `Ready`、返回码 0，看门状态为 `PASS`、阻断数 0。
- 新增机器可读数据准入报告 `runtime/reports/portfolio_data_admission_g22.json`，文件 SHA-256 为 `519e88eccbb761cd5124171abf3b2efb2a261715eb5caa6e4572f373e6e89084`、审计哈希为 `1c90ecdd75894ddfac3a46a10e333688de7369e2b667a153af9f6277739677ae`，自校验为 `PASS`。14/14 复权合同和 14/14 修订账本通过，13/14 标的具有近期独立双源重叠；内部研究数据状态为 `READY_WITH_LIMITATIONS`，未来模拟数据准入仍因历史时点化标的池、权威公司行动主数据、NVDA 近期双源重叠以及供应商许可/限流审查四项缺口而 `BLOCK`，实盘数据准入始终为 `BLOCK`。
- 完整 Python 回归现为 379 项并全部通过；新增回归覆盖逐标的输入清单、快照篡改、隔离源码加载、网络/SQLite 阻断和禁止生成 `__pycache__`。相关 Python `py_compile`、`node --check app.js`、`node --check chart_controller.js`、`node --check chart_quality.js` 和 Electron `npm.cmd run check` 均通过。最新 watchdog 对 v2 归档、备份状态和三个 Windows 任务的复核为 `PASS`、阻断数 0，G22 仍为 `COLLECTING`、零执行权限。本地 `/api/portfolio/forward` 与浏览器 AAPL → NVDA → BTC-USDT 非空 K 线验收沿用本轮此前通过结果；本次后端归档改动未修改前端代码。

### G42 动态时点股票池、因果历史与可恢复研究证据

- G41 已正式退役且没有迁移任何观察、收益或调仓样本。原因是动态股票池中较晚上市的标的会截断基准历史；直接补齐上市前价格又可能污染动量、波动率、流动性和成本估计。退役收据哈希为 `fa8025e4218e2f06b76a36515df67515231638813e983f900ba9057c520cb45b`。
- 生命周期合同升级为 v2：只有经过内容寻址的时点成员合同，才允许在正式纳入股票池之前写入不可交易、零持仓、估值专用的哨兵行；纳入之后的缺口仍立即阻断。哨兵不能成为停牌延续价，也不能进入动量、波动率、流动性或执行成本计算，缺少或篡改股票池哈希会失败关闭。
- G42 预注册实验为 `pexp-1785734862791-9c2613be0cd4`，协议哈希 `c0c85833a347ab62e338a74eccf6d79c51dbe6f0db3ee1b92701d6575d0d5377`。冻结候选 `portfolio_candidate_g42_causal_point_in_time_universe_gaps.json` 的候选哈希为 `c9a793d5f15b60e7955fa7b15ad96c6dd09681495ee7ea393fc2f77260a12d1a`，活动注册、完成收据、实现闭包和外部时钟证明均通过。
- G42 验证段收益 35.8862%、最大回撤 4.0415%、Sharpe 3.7788；开发测试段收益 7.4126%、相对 SPY 超额约 2.45 个百分点、最大回撤 6.6002%、Sharpe 0.9559；严重成本压力收益 6.9762%。测试段回撤和 Sharpe 仍弱于基准，这些结果只能说明机制值得继续观察，不能解释为稳定盈利能力。
- 统计审计语义复算通过，但晋级结论保持 `INSUFFICIENT_STATISTICAL_PROMOTION_EVIDENCE`：测试段正超额概率 60.36%，选择调整后概率为 0，区间下界跨越零。审计哈希为 `3532917893839d8e49e179a1fcb831fe7c003bdccc4601c70cb14ad40eecddc0`，其 `BLOCK` 是有效结论而不是错误。
- 数据准入报告 `portfolio_data_admission_g42_causal_point_in_time_universe_gaps_final.json` 自校验通过，14/14 复权、修订、跨源和近期重叠检查通过；内部研究为 `READY_WITH_LIMITATIONS`。时点历史成员主数据、权威公司行动主数据和供应商许可/限流审查仍阻断模拟准入，实盘准入始终阻断。
- 影子观察正确把 2026-07-31 归类为 `PRE_ACTIVATION_SKIPPED`。当前自然观察 0/60、前向收益期 0/60、实际调仓 0/8，没有回填或迁移旧样本。观察、绩效、每日归档和看门狗四个 Windows 任务均已启用；最新看门狗状态为 `PASS`，全部候选、快照、任务和无执行权限检查通过。
- 最终内部证据包状态为 `INTERNAL_BACKTEST_EVIDENCE_READY / promotion BLOCK`，包哈希 `664d1e2b07cf251ee75611a2280ac2c4538cc14f913140196531c937cd31b5d6`。自包含归档清单哈希为 `95b21c90bb4f7e2167f490c136bd29cf43c906448dce72992052e4463856ef56`，恢复验证通过；固定 3 次离线重放和验证器 3 次复跑全部得到唯一重放哈希 `8c843c05ea6d6b07d2af7fc939e164d9d890b20c4e162848c3449fba34e863ff`，结论明确为 `REPRODUCIBILITY_PASS_NOT_PROMOTION_EVIDENCE`。
- G42 新增与修订测试后完整 Python 回归为 620/620。服务已按核验后的命令行重启，`/api/health` 为 `PASS`，加载源码与磁盘源码指纹均为 `5b694fb85fcf65d07372c5bca892dde3ac475a88db46d2e31892c37c7354fce3`，无重启漂移；模拟授权仍关闭，实盘硬墙未改变。

## 当前已知限制

- G49 加密历史缓存目前只有 BTC-USDT 为 `READY`，ETH/SOL/BNB/DOGE 的现货与永续共 9 个数据集仍为 `MISSING`。这些标的可以显示实时行情，但在隔离补齐、完成态校验和内容寻址血缘通过前，不能加入下一轮正式回测协议。
- 股票实时能力取决于 Futu OpenD 登录和外部数据源可用性；离线时会明确显示本地缓存、旧缓存或兜底数据。
- Futu 的分钟历史会受行情权限和标的覆盖影响；系统会自动比较 Yahoo/Stooq，但不能把上游不存在的数据伪造成实时历史。当前 PSTG 日线补齐返回上游 404 并显示 `ERROR`。
- Yahoo 当前可补齐美股盘前、盘中和盘后分钟线，但夜盘覆盖不稳定；夜盘无权威数据时只显示不可用或明确的预览状态，不作为走势结论。
- 当前撮合仍是本地模拟模型，不代表真实交易所排队位置、网络延迟或全部市场冲击。
- 当前因果回测只支持 1 倍现金、做多与空仓；做空借券、保证金、融资成本、强平和组合级资金占用尚未建模，相关参数必须保持阻断。
- 旧模拟账户仍是单标的模型；新的多标的组合账本已经具备事务、幂等、恢复和内容寻址授权能力，但当前本金为 0、模拟开关关闭且没有写入路由，因此仍不能进行多资产模拟。
- G42 仍只有开发证据，真正满足激活时序的自然观察、绩效结算和收益期均为 0；G3 的一次性跨标的留出已经失败。必须自然积累新的时间样本并重新做未见数据确认，不能用 G5 至 G42 的开发成绩、旧候选观察、回放次数或激活前结果替代前向验证。
- G42 测试段的 Sharpe 和最大回撤仍弱于基准，逐标的剔除还暴露出 ASML 依赖；这两个问题不会被当前总体正收益抵消。
- G42 的统计晋级审计仍明确阻断：测试段正超额概率和选择调整后概率不满足预注册门槛，区间下界跨越零。该结果在获得真正的新时间收益序列前不能通过调低门槛、重排现有样本或重复运行消除。
- 当前 14 标的静态研究池不是历史时点化成分股数据库，无法证明消除了幸存者偏差；在建立带生效日期、退市和历史成员关系的 universe 前，只能用于机制研究和内部回测工程验证。
- G42 数据准入已确认 14/14 标的近期独立双源重叠为 `PASS`，包括 NVDA；但这不替代历史时点化 universe、权威公司行动主数据和供应商许可/限流审查，三项未完成前模拟数据准入仍为 `BLOCK`。
- 外部时钟证明来自普通 HTTPS API，不是交易所签名或可信时间戳机构的不可抵赖证明；单来源降级仍可捕获但会明确记录。两个时间源和行情源同时不可用时，系统会阻断而不是回退到本机时间。
- 单次实验注册表是本地内容寻址审计控制，不是独立第三方公证。它能检测重放、并发领取和事后文件篡改，但拥有本机管理权限的攻击者仍不在当前威胁模型内。
- Windows 计划任务当前使用交互式用户令牌；机器关机、用户长期注销、任务被手工禁用或网络持续中断仍可能造成漏捕。`StartWhenAvailable` 只会登记错过事实，不会把错过日期补写成自然观察。
- 最新可重放 v2 不可变归档约 7.75 MiB/份，旧 v1 约 5.66 MB/份；归档采用只追加且不自动删除的保守策略，需要持续监控磁盘空间，并在形成经过批准的离线保留策略前禁止自动清理历史证据包。
- 前向模拟毕业需要真实经过时间和足够闭合样本，不能用历史回测或手工修改状态替代。
- 股票实时能力仍取决于 Futu OpenD 和外部数据源；离线缓存只可研究，不能通过新增风险门禁。
- 当前已具备正式交易日历、分红支付日现金、拆股数量调整、停牌和退市结算合同，但真实股票缓存仍主要依赖 Futu 内嵌复权合同与 Yahoo 事件；尚未接入权威公司行动/停复牌/退市主数据源，不能把“合同已实现”误写成“真实事件覆盖完整”。
- Futu/Yahoo 等现有供应商的许可、历史数据本地存储权、再分发限制、配额和失败重试策略尚未形成已批准的版本化治理记录；在该审查完成前，数据准入报告必须保持 `PROVIDER_LICENSE_AND_RATE_LIMIT_REVIEW` 阻断。
- 当前容量模型基于日频成交额和固定参与率，尚未覆盖盘中流动性曲线、开盘竞价、排队位置、借券、真实网络延迟和跨日市场冲击。
- 产品目标仍是 Electron/桌面研究终端。`<=480px` 的顶部导航、受限自选列表和研究视图单列信息架构已通过静态 CSS 合同；真实设备/浏览器渲染与可用性验收仍未完成，不能把静态通过写成移动端 QA 通过。
- `server.py` 仍然偏大；核心账本、执行、风控、回放和 HTTP 契约已拆出，剩余市场/研究路由还需继续迁移。
- 独立交易分析项目与哈基米之间目前使用本地 ResearchBrief 接口；版本协商与同键幂等已接入，失败重试队列仍未实现，失败时必须由调用方保留并重新提交原始事件。

## 下一步建议

1. 持续监控 G42 的观察任务、绩效结算任务、每日不可变备份、看门任务、状态年龄，以及调度/备份/看门三组告警文件；每个激活后新完成的美股交易日必须形成外部时钟观察、下一交易日可验证结算或明确违规，不得回填、伪造或重算旧日。
2. 维持至少 60 个自然前向收益期、8 个实际执行调仓、零捕获/数据/完整性/风险/权限违规的固定门槛。由于首个有效结算只建立基线，通常至少需要 61 个有效结算日；未满足前保持 `COLLECTING`，满足后也只进行一次冻结候选人工评估。
3. 前向收集期间冻结 G42 候选、参数、标的池、风险档、账户起始合同和实现指纹。ASML 依赖、测试段 Sharpe 与回撤弱于基准只能作为到期验收问题处理，不能中途优化后继续沿用同一前向账本；任何策略或执行语义修改都必须生成新候选和独立账本。
4. G42 到期评估必须把自然前向日收益作为独立序列重新执行同一统计合同；若正超额概率、选择调整概率或区间下界仍不通过，应退役候选而不是开启模拟。任何新策略假设必须先预注册，并使用未被 G1 至 G42 消费的新数据窗。
5. 按 `portfolio_data_admission_g42_causal_point_in_time_universe_gaps_final.json` 的机器门槛，为正式市场日历增加版本升级监控，并接入权威公司行动、停复牌与退市主数据；先验证覆盖率和修订策略，再允许这些真实事件进入未来候选的组合权益与审计回放。
6. 为 PSTG 等上游覆盖缺口增加可插拔的第二美股历史源，并形成供应商许可、本地存储权、再分发限制、配额、限流、复权口径和失败重试的版本化治理记录。
7. 只有 G42 的新时间留出、前向绩效窗口和统计晋级审计一次性通过，人工批准生成内容寻址授权收据后，才允许给多标的账本注入隔离模拟本金并开放受保护的写入入口；`INTERNAL_BACKTEST_EVIDENCE_READY` 和 `REPRODUCIBILITY_PASS_NOT_PROMOTION_EVIDENCE` 都不等于模拟交易授权，真实下单硬墙不参与评估，也不得打开。
8. 继续拆分 `server.py` 的市场与研究路由；ResearchBrief 已有版本协商与幂等冲突门，后续若确有需要再增加不带执行语义的失败重试队列。
