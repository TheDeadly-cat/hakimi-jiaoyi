# 日程过滤：实际安装、合成对照和真实来源导入

本轮实现已进入 [PR #8](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/8)，继续作为 Experimental 候选。源码提交 `b6e345f9cdef9b638883ee298f0ba8bfe444e8d6` 的 [CI 34722731560](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/34722731560) 已完成，9 个实际 Job 全部成功；双平台安装检查包含新增 CLI 对照和重放，Windows 安装日志明确记录 183 项测试通过。后续证据提交保留这个实现与安装件身份。

## 本机实际安装与原件

使用新临时目录构建普通 wheel，创建不继承系统包的独立 venv，在仓库外运行全部 183 项根目录测试。没有 editable 安装或 PYTHONPATH；运行时确认 `REPOSITORY_ROOT=None`、源码 BUILD_VERIFIED、锁定依赖 VERIFIED，源工作树未变。测试执行时禁止 Python 出站网络；安装依赖使用固定依赖清单，不接触行情或券商接口。

- 实际 wheel SHA-256：`3bb8bc6caeead11321329b6d783e818f328498956d092cee3aead01a0cf68135`。
- 实际安装源码摘要：`c5d57ec371efe303741b12476fd6824c3eb4baa5e3cfb9cfd22c3a337fe236b6`。
- 原 wheel 和脱敏安装回执保存在 [accepted-wheel](accepted-wheel/SHA256SUMS.txt)，属于本次开发候选，不是新的正式 Release。
- 命令实际开始/结束、退出、输出摘要、独立账本及来源导入结果见 [installed-scenarios.json](installed-scenarios.json)。测试子集相互包含，不能把源与安装测试重复相加；首轮失败与修正见 [validation.json](validation.json)。

## 合成 A/B 确实经过 CLI 和原账本

安装后的独立 Python 实际运行了 snapshot-import、event-import、event-context、event-compare、两组 replay，再使用不导入策略引擎的 Decimal 核对器检查两份报告。

这是固定的虚构 Dual MA 2/3 会话序列，并非真实 AMD 或被冻结的真实 5/10 参数实验。A 有 3 笔成交，B 拦截 1 个新增买入意图后有 1 笔成交；两组均保留 15 条评分决策。两份重放的结果、源码和环境均匹配，独立账本分别完成 140 项与 121 项核对。它证明输入进入现有交易模拟和记账流程，不证明策略增量价值；完整合成数值保留在 [对照摘要](synthetic-artifacts/comparison.json)。

公开目录包含原合成快照、两份规约、合成事件上下文和经济结果投影。原完整报告包含本机运行路径，导出检查因此拒绝原样发布；原件保留本机，公开的 `A-report-projection.json`、`B-report-projection.json` 明确绑定原报告摘要，未重写或重新签名原件。这些投影不是可直接传给 replay 的原报告；可以用公开的快照、规约、上下文和实际 wheel 重新计算经济结果。

## 真实 AMD 日程已通过实际安装包导入

采用此前下载的 [AMD 日程公告](https://ir.amd.com/news-events/press-releases/detail/1223/amd-to-report-fiscal-third-quarter-2024-financial-results)，原 HTML SHA-256 为 `0fe796a79af0e155752f032c049f70a4f82b1a1c74599c97624fc05c61075415`，实际下载时间仍为 `2026-09-12T17:25:04.897065Z`。本次提取完成时间单独记为 `2026-09-12T22:22:50.078411Z`，没有冒充历史收到时间。

安装后的 event-import、event-context 实际通过，事件摘要为 `28e217fd546315dca325a6201bdf918722bb226a74b5ba74cf2ec725331308ce`，上下文摘要为 `42d14bbbafba25dcd14b95716955aace4e05989eacb70873f1f30a676850c5c8`。日程为 2024-10-29、AFTER_MARKET_CLOSE、精确发布时间 null；原文中的电话会议时间未用作财报发布时间。发布时钟为当年 10 月 16 日 13:00Z，按既定 60 秒采集加 60 秒处理假设，可用时刻为 13:02Z、种类 ASSUMED。实际查询 13:01:59 与 13:02:00，分别选出 0 与 1 个版本。

真实公告原件、完整事件和上下文仍仅保存在本机，公开其摘要和提取/可用时间。此项证明真实日程导入及版本选择，不是行情真实性、人工字段金标准、真实价格信号或实际股票收益。

真实日线及公司行为覆盖仍待富途/moomoo 的 OpenD 与数据权限确认，真实 A/B 经济运行 NOT_RUN；公司行为记账、C/D 字段条件和官方券商模拟未完成。T5 调度候选仍待独立切换授权，未因为本 PR 或 CI 成功而激活。
