# 当前研究 CLI 状态

更新时间：2026-09-05。本页集中记录当前证据；历史报告保留原始版本与当时状态。

本轮正在收尾 0.2.1：成交时序 v6、可下载 CI 构建、原16单元当前构建重放、
240单元多窗口研究，以及无下单的前向观察与完整流程性能记录。
下表的待完成项不能视为已经验收。

| 项目 | 当前核实状态 |
|---|---|
| main | `f4bfa8adab07a21b66b341a0b8b2fe1804c537d7`，本轮未合并 |
| 开发分支 | [codex/research-platform-hardening](https://github.com/TheDeadly-cat/hakimi-jiaoyi/tree/codex/research-platform-hardening)，链接显示当前远端 head |
| PR | [#1](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/1)，目前 Draft |
| 上一轮已验收提交 | `2cbccfdcb46c05ce4427f39fec541f7e77a0c6ee`；[CI33955357974](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/33955357974) 的9个实际Job成功 |
| 本轮构建 | 待提交并下载当前CI产物验收；不复用上一轮wheel身份 |
| 主分支保护 | 已启用；严格要求 GitHub Actions App15368 的 `Research required gate`；管理员也受约束；禁止强推与删除；通过PR变更 |
| 成交时序 | v6本地77项相关检查通过；原始净值、费用、部分成交检查保留 |
| 当前研究 | 原快照16单元重跑与第二环境重放待执行；旧报告仅对原源码摘要有效 |
| 多窗口输入 | 固定计划先于结果；16个窗口数据已采集并通过各自完整性核验；240单元计算待执行 |
| 前向观察与性能 | 功能、部署和完整流程测量待完成，尚不声称实时积累已建立 |

[本轮逐项验收要求](docs/review-closeout-plan.md) ·
[成交事件规则](docs/execution-timing.md) ·
[固定多窗口计划](docs/studies/multiwindow-plan-20260905.json)

正式范围是 BTC-USDT 现货1h离线研究 CLI。GUI/旧HTTP服务发布、其他市场、
策略盈利和账户执行未验收；paper/live/order 权限保持 false。
数据与研究结果为描述性证据；2026年8月已经查看，不能标记成盲测或确认集。
