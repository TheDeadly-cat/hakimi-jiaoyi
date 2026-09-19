# 当前项目状态

更新：2026-09-20；代码合并状态已重新核对，运行结果按下列原始回执时间标注。项目定位为研究软件，当前结果不支持自主实盘或盈利声明。

| 层次 | 已核实状态 |
|---|---|
| GitHub main | `a64758a3df3ce73d433a2a2d71fac1e1a70dc5db`；PR #9、#10、[#11](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/11)均已按分别授权合并。PR #11于9月13日19:43合并，[合并后CI](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/34755168177)历史记录9个Job成功；本次仅更新状态文档 |
| 四个原PR | [#5](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/5)、[#6](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/6)、[#7](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/7)、[#8](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/8)均已通过PR #9的普通非强制快进合入main；GitHub已将四个原PR确认为MERGED |
| 集成验收 | [PR #9](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/9)已合并；组合代码`8333a684…`的本机普通wheel安装183项通过、仓库专用205项通过。PR及main各自的9项CI均成功；三项Cursor检查成功。Codex代码审阅服务失败未提供报告，安全审阅完成；没有把服务失败写成审阅通过 |
| 正式Release | [v0.2.1](https://github.com/TheDeadly-cat/hakimi-jiaoyi/releases/tag/v0.2.1)，包含已验收BTC研究基线；不是最新全部股票代码 |
| 真实AMD D1 | 37日真实常规时段快照已接纳；原日线成交量与RTH分时汇总有差异，因此明确采用259条原始RTH分时聚合，OHLC逐日相同。公司行为为有限窗口来源审查声明，原件保留本机 |
| 真实AMD D2 | 原5/10均线、原窗口和参数已跑A/B；两组均-1.5974%，各4笔成交、0次拦截，未识别到规则经济影响。工程买入持有基线-3.4394%。三份账本核算及同版本离线重放通过 |
| 官方模拟 X1 | [PR #10](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/10)已合并；[PR #11](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/11)验收入口已合并，受验源码`93362a5…`已补工作进程Job身份核验、操作前回执占用及发送前源码复核。导出源码的流程9项、适配33项、原状态机25项、真实SDK协议7项、原进程控制27项通过；修正版真实只读准备12次请求、新进程恢复9次请求成功，回执确认父进程Job身份；9月13日准备回执中的数据库为PREPARED且无提交领取；本轮未连接券商。首次持仓代码检查失败、旧准备记录及验证环境失败均保留。费用/结算原件不可用，官方订单仍未授权或发送；见[修正准备回执](docs/research-evidence/futu-official-cycle-20260913/correction-preparation.json) |
| 已部署运行件 | 已登记固定bundle来源`bbf7cd2…`；本次未更换部署件、重启观察窗口或修改通知偏好，也未重新激活任何调度 |
| 观察 O1 | 原窗口9月13日12:00—9月16日12:00、巡检至12:10，日历时间已结束。最后留存巡检截至9月16日02:07：当前状态41个ON_TIME、21个FAILED、1个LATE、9个PLANNED；首次期限为22个FAILED、41个ON_TIME、9个PENDING。这是未到期快照，不能作为完整72小时验收。此前独立重放14份记录的结果保留，本次未新增重放 |
| 后续C/D | 财务字段人工核准未完成，内容策略未运行；日期过滤结果不代替字段核准 |

最新核对：[9月20日状态快照](docs/research-evidence/github-sync-20260920/status-snapshot.json)。23份通知投递回执中18份由OS报告显示、5份未确认；不等于用户阅读确认。PR #9、#10、#11的合并授权均已执行；官方模拟下单尚无本任务的单独授权，实际周期仍未运行。完整到期窗口汇总及剩余时段分类尚待核验。

本轮最短核验入口：[真实AMD结果、数据口径、富途限制及运行回执](docs/research-evidence/real-amd-rth-20260913/README.md)。GitHub开发分支同步、主分支合并、正式发布和本机部署分别记录。

此前已关闭的事件半写问题见[修复记录](docs/review-followup-20260913.md)，不重复派发。当前集成保持股票研究Experimental、本地订单实验LOCAL_SIMULATOR及既有真实交易禁止边界。

历史证据保留原身份和当时结论：[v0.2.1发布验收](docs/research-evidence/release-0.2.1-20260909/README.md)、[BTC连续历史](docs/research-evidence/continuous-history-20260906/README.md)、[停止晋级的两个候选](docs/research-evidence/strategy-diagnostics-20260906/README.md)、[旧72小时窗口](docs/research-evidence/forward-window-20260908/README.md)、[本轮首次失败与恢复](docs/research-evidence/observation-activation-20260913/first-cycle-recovery.md)。旧窗口106准时、14迟到、24缺失的144策略小时统计保持不变。
