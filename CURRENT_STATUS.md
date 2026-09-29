# 当前项目状态

整理日期：2026-09-30。本页区分核对时的功能基线、开发交付、历史原件与实际外部验收。项目仍为研究软件，未授权自主或真实交易。

用户已要求暂时放下Unknown记录：异常排查及T3实际验收暂缓，等待明确恢复；其余已完成交付保留。以下T3证据为暂缓前的历史状态。

| 层次 | 已核实状态 |
|---|---|
| 本状态核对时提交 | 用户单独批准 [PR #17](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/17) 的 `46d938a` 后，已于 2026-09-29 12:57:03 UTC 合并至 `cdee7b5472981811655bf84a8a9f59298df546b4`；[合并后 CI](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/36571592538) 九项成功，实际检出 main 合并提交。PR #16 与旧测试身份保留 |
| 本机开发候选 | [NVIDIA 两事件时间与行情诊断](docs/research-evidence/nvda-event-price-20260930/README.md)：用户选择 Futu 后实际完成 6 次报价业务查询，生成两个 8 日快照；发行渠道秒级时间已独立绑定，原公告 `public_at=null` 保留。来源可比 2、价格信号及数值交集各 2；26 项新定向检查通过。16 日 OHLC 一致、成交量差异原因未证实。人工核准 0、收益运行 0，原至少 3 候选门槛未达；八次工程对照仅为待核准方案，非开发者首次使用尚未验收。未更新正式发布、r3 或部署；主分支合并仍需单独批准 |
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
