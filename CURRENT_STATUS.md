# 当前项目状态

更新：2026-09-13；运行统计截至北京时间18:38，精确时间及身份见链接回执。项目定位为研究软件，当前结果不支持自主实盘或盈利声明。

| 层次 | 已核实状态 |
|---|---|
| GitHub main | `7055f03c2d35868b939a792aa0e9a13e6e20b8c0`，PR #9经维护者明确授权于北京时间17:36合并；[合并后CI](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/34749832008)9个Job成功 |
| 四个原PR | [#5](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/5)、[#6](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/6)、[#7](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/7)、[#8](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/8)均已通过PR #9的普通非强制快进合入main；GitHub已将四个原PR确认为MERGED |
| 集成验收 | [PR #9](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/9)已合并；组合代码`8333a684…`的本机普通wheel安装183项通过、仓库专用205项通过。PR及main各自的9项CI均成功；三项Cursor检查成功。Codex代码审阅服务失败未提供报告，安全审阅完成；没有把服务失败写成审阅通过 |
| 正式Release | [v0.2.1](https://github.com/TheDeadly-cat/hakimi-jiaoyi/releases/tag/v0.2.1)，包含已验收BTC研究基线；不是最新全部股票代码 |
| 真实AMD D1 | 37日真实常规时段快照已接纳；原日线成交量与RTH分时汇总有差异，因此明确采用259条原始RTH分时聚合，OHLC逐日相同。公司行为为有限窗口来源审查声明，原件保留本机 |
| 真实AMD D2 | 原5/10均线、原窗口和参数已跑A/B；两组均-1.5974%，各4笔成交、0次拦截，未识别到规则经济影响。工程买入持有基线-3.4394%。三份账本核算及同版本离线重放通过 |
| 官方模拟 X1 | [PR #10](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/10)候选`a210efe…`已修复实际SDK回调消息头账户身份和发送前授权到期校验。从Git导出源码验证：适配31项、原状态机25项、真实SDK合成protobuf解码6项、CI工作流10项通过；逐文件摘要与提交字节一致。新一轮真实13次只读请求成功，未下单；见[修正验收](docs/research-evidence/futu-simulation-adapter-20260913/correction-validation.json)。费用及成交API受限，实际订单周期、费用/结算原件和正式接入仍未完成，此候选尚未合入main |
| 已部署运行件 | 固定bundle来源`bbf7cd2…`，新预检候选`d4afcca…`尚未部署。两项Windows任务已启用，旧heartbeat暂停 |
| 当前观察 O1 | 北京时间9月13日12:00—9月16日12:00，巡检至12:10。首轮FAILED后人工恢复LATE，随后六个自然小时ON_TIME，12份新策略记录独立重放通过。窗口未结束，两条通知积压且未确认显示 |
| 后续C/D | 财务字段人工核准未完成，内容策略未运行；日期过滤结果不代替字段核准 |

最新观察回执：[首轮失败保留及六个后续小时](docs/research-evidence/observation-activation-20260913/natural-hour-1000-20260913.json)。维护者对PR #9的合并授权已执行；PR #10合并和后续官方模拟下单仍须分别授权。

本轮最短核验入口：[真实AMD结果、数据口径、富途限制及运行回执](docs/research-evidence/real-amd-rth-20260913/README.md)。GitHub开发分支同步、主分支合并、正式发布和本机部署分别记录。

此前已关闭的事件半写问题见[修复记录](docs/review-followup-20260913.md)，不重复派发。当前集成保持股票研究Experimental、本地订单实验LOCAL_SIMULATOR及既有真实交易禁止边界。

历史证据保留原身份和当时结论：[v0.2.1发布验收](docs/research-evidence/release-0.2.1-20260909/README.md)、[BTC连续历史](docs/research-evidence/continuous-history-20260906/README.md)、[停止晋级的两个候选](docs/research-evidence/strategy-diagnostics-20260906/README.md)、[旧72小时窗口](docs/research-evidence/forward-window-20260908/README.md)、[本轮首次失败与恢复](docs/research-evidence/observation-activation-20260913/first-cycle-recovery.md)。旧窗口106准时、14迟到、24缺失的144策略小时统计保持不变。
