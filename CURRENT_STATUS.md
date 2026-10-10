# 当前项目状态

本页为日常状态入口；历史证据目录、原包和旧回执保留原身份。M1、M2-1 和 R1／R2／R3 已结案，当前开发阶段为 M2-2。主分支集成以实际合并提交及其检查为准。

整理日期：2026-10-10。PR #22 已经用户对 `0059359` 单独批准合入 main `57b6bd4`，实际 main 九项 CI 成功，Windows／Ubuntu 安装各 253 项通过。原 M2-2 候选 `0.4.0.dev5` 已完成统一离线行情／研究输入、版本绑定与既有排期／内容规则入口；同一 wheel 仓库外 253 项和实际冷进程输入流程通过。新候选首用及 CI 分别记录，见[本轮验收](docs/research-evidence/input-workflow-m2-20261010/README.md)；旧 dev4／dev3／dev2 与 M1 原件保持原身份。

用户已要求暂时放下Unknown记录：异常排查及T3实际验收暂缓，等待明确恢复；其余已完成交付保留。以下T3证据为暂缓前的历史状态。

| 层次 | 已核实状态 |
|---|---|
| 当前 main | [PR #22](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/22) 经用户对 `0059359` 单独批准，于 2026-10-10 17:30:04 UTC+8 合入 `57b6bd4ec2263f6d390257fde7e787f44a084d85`；内容树 `3f694f17be4e85aa4ca5fb696482c5bb1125a366` 与受审 head 相同。[实际 main CI](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/38041602339) 九项成功，Windows／Ubuntu 安装各 253 项、输入及 R3 流程通过。M1、M2-1 和 R1／R2／R3 保持关闭 |
| M2-2 功能候选 | [PR #22](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/22)，`0.4.0.dev5` CLEAN 构建 `51b0f17`，wheel `b935fde7b436…`，运行源码 `8c85724cdf8f…`；同一 wheel 仓库外 253 项、实际输入菜单／冷进程、输入更新与状态保持、运行比较、迁移和重放通过。新交付 `Hakimi-M2-dev5-Inputs-20261010` 的启动器离线安装／身份检查／重开通过，ZIP `f55c4a08bdb…`；[构建 CI 九项成功](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/38036110148)，最终 PR head 检查另记于 PR。已通过 PR #22 集成；该 dev5 存档随后复现两项 P2 缺口，原通过范围不回填。[原候选证据](docs/research-evidence/input-workflow-m2-20261010/README.md) |
| M1 main 集成 | PR #19 经用户单独批准受审 `669b348` 后，已合入 `17b2c15891aab7caf30dbb1addbb1f495f92dea0`；内容树 `26215045b3becf7dd6bf6e5d7292011a6e837379` 与受审版本一致。[实际 main CI](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/37912896005) 九项成功，Windows 安装后 209 项通过；M1 结案。集成回执保存在 PR #19 实际合并记录与本机 M1 存档目录 |
| 前一 main 集成 | 用户单独批准 [PR #17](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/17) 的 `46d938a` 后，已于 2026-09-29 12:57:03 UTC 合并至 `cdee7b5472981811655bf84a8a9f59298df546b4`；[合并后 CI](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/36571592538) 九项成功，实际检出 main 合并提交。PR #16 与旧测试身份保留 |
| M1 存档候选 | `0.3.0.dev4` 构建 `ac8c77b`，wheel `e10cbb02ab71…`；原仓库外 209 项安装验收与默认／同盘外部／真实跨盘菜单使用原样保留。PR #19 现已合并；原候选没有改签为 main 构建。旧 dev3 的包、失败和 201 项验收保留。见[原修复与候选验收](docs/research-evidence/offline-product-m1-p2-20261009/README.md) |
| M2-1 R1／R2 存档 | PR #20 已合并；dev3 原 CLEAN 构建 `6f9f02a`、wheel `420a2450e2a6…`、232 项安装检查及原菜单／命令／启动器证据保持原身份。同策略修改保留旧省略参数的 8% 语义；非法数值提交前拒绝。原 PR CI 实际检出 `bc5982410c005a754afbf8dc9f31cf43c56570b8` 与当时 API 合并预览 `a62ab7e…` 已在 PR 描述分别记录，原回执未重写。见[配置修复验收](docs/research-evidence/strategy-task-m2-config-20261009/README.md) |
| M2-1 R3 存档 | PR #21 已合并；`0.4.0.dev4` CLEAN 存档构建 `015cc39`、wheel `1a04a086b931…`、本机 241 项安装检查及原冷进程／启动器回执保留。最终 head `63adb41` 和实际 main `4732bcc` 的 CI 分别核对，不改签存档候选。共用切换配置、同策略旧语义、显式冲突与失败不提交均保持。见[R3 原验收范围](docs/research-evidence/strategy-switch-r3-20261010/README.md)和 PR #21 集成说明 |
| dev2 存档与检阅边界 | 构建 `a61a629`、原 wheel `fa80bb26fcdd…`、221 项安装后检查和菜单首用／迁移保持原身份；原受审 head `931da97` 的九项检查保留。它们没有覆盖本次两类配置缺口；本机未改动的 dev2 安装已直接复现，原记录不回填。见[旧候选验收](docs/research-evidence/strategy-task-m2-20261009/README.md) |
| 已进入 main 的两事件诊断 | [NVIDIA 两事件离线对照已完成](docs/research-evidence/nvda-event-price-20260930/economic-20261002/README.md)：用户明确核准字段和固定 8 次范围后，8 次模拟、8 次重放及 8 份独立账本核对通过（512 项账本检查）；原始输入与执行代码未变。两组结果完全相同，内容干预 0 次：常规成本下 Q1 +1.4463%、Q2 −0.8019%，双倍成本分别 +1.3925%、−0.8539%。本轮新增取数 0；此前 6 次查询、两个 8 日快照及 16 日成交量差异保留。报告桌面／窄窗口及费用展开已核对，用户已确认“能找到，展示清楚”，报告阅读验收通过；独立安装或命令行使用未据此验收。原至少 3 候选门槛未达，研究接纳 0；PR #18 已按本次单独授权合入 main `8e95f51`，合并后九项 CI 通过；原研究与阅读证据不重跑、不重签。正式发布、r3 和部署未更新 |
| 正式 Release | 仍为 [v0.2.1](https://github.com/TheDeadly-cat/hakimi-jiaoyi/releases/tag/v0.2.1)，未发布新正式版本；独立富途工具不是研究 wheel 的组成部分 |
| 真实 AMD 原始闭环 | 37个交易日、259条真实 RTH 分时聚合。OHLC 与供应商日线一致，全部37日成交量差异原因未确认。保留原件和有限窗口公司行为来源边界 |
| 原冻结 A/B | 两组均 -1.5974014%，各4笔成交、2个往返、0次拦截；未识别事件过滤的经济影响。工程买入持有 -3.4394% 从10月2日起评分，A/B 从10月17日起评分，不直接排名。见[原结果](docs/research-evidence/real-amd-rth-20260913/README.md) |
| O1 到期核对 | 9月23日已用冻结版check正式追加结案回执；72小时为41准时、21失败、1迟到、9无启动回执；首次期限41准时、22失败、9缺失。与9月20日逐项结论一致，运行可靠性未通过。见[冻结入口正式结案](docs/research-evidence/observation-closeout-20260923/README.md) |
| O1 历史运行状态 | 系统关机至下一开机覆盖剩余九小时及最终巡检截止。9月20日查询的两项任务为Enabled/Ready但无下一次运行；这是留存状态，不是9月23日实时健康证明。未改变部署、通知或调度。另21次原驱动失败留有公共捕获URL超时，网络根因仍待定位 |
| 官方模拟 T2 | 本机候选把订单身份/终态、账户读取和费用会计分开表达；缺失费用不填零，不放开新增风险。后续修复只读扫描遇零价格就提前退出的问题，保留执行阻挡；最新54项定向测试通过，替代先前51项计数。见[验收矩阵](docs/futu-official-cycle.md) |
| 官方模拟 T3 | 维护者授权继续解决后，新增3次原始协议核对及12次有界只读查询；两轮账户读取一致、证券规则通过，正常交易时段未开放。异常记录与期权到期日相符、对应合约已不在持仓中，但接口仍明确Unknown(-1)，不能推断终态。未建立新准备身份、未生成绑定订单操作授权、未发送订单；旧数据库不重签。见[最新修复与核查](docs/research-evidence/futu-preflight-20260920/resolution-followup.md) |
| 股票事件 T4 | 固定10窗口实际数据已取得，7接纳、3因OHLC差异保留排除。42份不同报告重放/账本通过，14项后续日程不干扰检查通过；2024Q1拦截1次BUY，但7事件A/B仍全部亏损。见[最终结果](docs/research-evidence/equity-events-20260920/actual-study-final.md) |
| 受监督预览 T5 | 研究和Windows富途r3新包已分别在全新仓库外环境安装通过，包含只读修复与最终十事件摘要；状态、离线帮助和封装校验通过。见[r3交付](docs/research-evidence/supervised-preview-20260920/README-r3.md)。r1/r2保留原字节，未发布Release、部署或启动监控 |
| 财报内容 C/D | 9月24日十行人工核准和原件复查通过；原七个接纳窗口、两档成本完成28份报告，重放与独立账本均通过。C/D完全相同，仅两个事件入场且止损，内容条件零次干预；三个旧排除保留，无晋级依据。见[固定比较结果](docs/research-evidence/equity-content-20260924/README.md) |
| 同财季指引来源配对 | 原十事件全保留，九个口径可比；七个数值高于、两个精度方向不确定，2022Q1 因 Xilinx 不可直接比较，2022Q3 已纳入初步业绩。独立审计的指引／初步值及摘要绑定缺口已修复：59项定向测试、17份原件513项检查通过；原134项回执保留为范围有限的历史记录。新增17个审阅项有条件用于历史开发，新增人工核准0；有限来源核查带明确缺口结案，完整历史链仍未证实。原价格信号2个，数值交集仅2024Q2一个候选，获准新研究0，新内容干预未运行。本批开发诊断结案，不扩展收益研究。见[修复与研究决定](docs/research-evidence/equity-guidance-20260927/audit-repair/README.md)及[新版卡片](docs/research-evidence/equity-guidance-20260927/audit-repair/report/index.html) |

原模拟提案仍为 US.AMD、BUY 1股、1美元限价、DAY/RTH，最多一次提交和一次同订单撤单；未知不重试、拒单不调价、意外成交不授权额外卖出。实际周期需要单独有效授权及当前环境核对。接口路径通过、会计通过、策略证据与实盘权限分别验收。

历史证据继续保留原身份：[集成与真实样本](docs/research-evidence/real-amd-rth-20260913/README.md)、[首次失败及恢复](docs/research-evidence/observation-activation-20260913/first-cycle-recovery.md)、[9月13日模拟只读准备](docs/research-evidence/futu-official-cycle-20260913/correction-preparation.json)、[v0.2.1发布验收](docs/research-evidence/release-0.2.1-20260909/README.md)。旧72小时窗口的144策略小时统计不被新清单替换。

本轮逐目标交付与未完成项：[T0–T5交付清单](docs/acceptance-delivery-20260920.md)。

9月23日远端审阅与本机交付差异：[审阅对照](docs/review-response-20260923.md)。不重跑已完成的研究或安装验收，不恢复已暂缓的T3。

ed19之后的研究诊断与剩余事项见[本轮D1/D2/D3/O2清单](docs/research-evidence/equity-diagnostics-20260923/README.md)。原O1结案、十事件研究和r3安装任务保持关闭；亏损与可靠性未通过的结论不因补充诊断而改写。

2026-10-09：M1 的三个流程缺陷及 PR #19 集成保持关闭；当前进入 M2-1。日常状态已更新，历史证据、旧包、旧回执和研究原身份不变。

2026-10-10：M2-1 与 R1／R2／R3 已结案。本轮从 main `4732bcc` 开展 M2-2，复用现有快照、事件版本、价格确认和内容条件；[正常输入使用说明](docs/input-workflow.md)。共享资金、增量监控与券商执行不在本轮范围，Unknown／T3 与已结案市场研究保持原状态。

2026-10-10 修复跟进：在原已安装 dev5 中独立复现 M2-2-01（自洽重哈希成交缺少证券／会话／信号／依据验证）和 M2-2-02（菜单 10 给内容策略传均线参数）。新候选 `0.4.0.dev6` 复用成交约束并绑定唯一内容入场机会，菜单 10 共用配置表单；源码定向检查通过，同一新 wheel 仓库外 262 项／实际五策略菜单与报告边界、交付启动器通过；[PR #23](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/23) 最终检查及单独核准集成待完成。见[修复验收](docs/research-evidence/content-report-p2-20261010/README.md)。不改签或覆盖 dev5 与旧报告。
