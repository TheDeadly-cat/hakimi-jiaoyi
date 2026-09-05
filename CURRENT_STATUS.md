# 当前研究 CLI 状态

更新时间：2026-09-05。本页集中记录当前证据；历史报告保留原始版本与当时状态。

本轮交付为 **0.2.1 离线研究 CLI**：成交时序 v6、可下载的确切CI验收件、
原16单元当前构建重放、240单元多窗口研究、无下单前向观察与全流程性能记录。
本页绑定实际使用的已验收构建；随后追加的报告/工具文档提交不改变下面的运行时源码摘要。

| 项目 | 当前核实状态 |
|---|---|
| main | `f4bfa8adab07a21b66b341a0b8b2fe1804c537d7`，本轮未合并 |
| 开发分支 | [codex/research-platform-hardening](https://github.com/TheDeadly-cat/hakimi-jiaoyi/tree/codex/research-platform-hardening)，链接显示当前远端 head |
| PR | [#1](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/1)，合并由维护者决定，状态以PR为准 |
| 研究实际使用的构建 | 受审查head `313c53505405316774b82cf8b5c4a31b38de7a21`；CI实际checkout `a6771ec89603999d55c6193a4fa7846ec3115d40`；[CI33969915599](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/33969915599) 的9个实际Job全部成功 |
| 可下载交付物 | 上述CI页面含Windows/Ubuntu各一份wheel及脱敏验收、源码、依赖、测试范围和校验和；每份90测试、零失败/错误/跳过，上传保留30天；已实际下载并另行验证两份产物 |
| 主分支保护 | 已启用；严格要求 GitHub Actions App15368 的 `Research required gate`；管理员也受约束；禁止强推与删除；通过PR变更 |
| 成交时序 | 两个数值反例先复现失败、再修复；旧仓位开盘保护优先，取消同bar旧挂起信号；真实盘中双触及仍保守处理；90项安装测试包含11项时序回归 |
| 原16单元 | 原快照/规约未变；16/16第二环境重放、66,866项独立账本核算通过；这一个月的新旧经济路径未改变，源码/模型身份仍明确区分 |
| 多窗口研究 | 32,136根完整小时线；16个窗口、240个单元全部执行并独立重放；2,970,067项账本核算通过；亏损与无成交单元完整保留 |
| 前向观察 | 两个冻结平仓参考状态计划；UTC14:00首个完整小时已产生两份ON_TIME记录并重放通过；本机每小时第1分钟任务已启用；首次定时调度执行与未来可靠性尚未观测，首次记录由人工触发相同命令 |
| 性能 | 真实季度与合成5k/20k完整流程、原始导入及一次独立插桩测量完成；语义精确重放；未做优化或宣称跨平台性能保证 |

实际研究wheel SHA-256：`b93952ddee0d16424292e75e5a3e7b0dfe10ac06d12f1333fa276922d08649fb`。
运行时源码摘要：`48f1c48875b774ccf0af732c0b7089a5b7ff1ae3bac1dd68ee357fc40ef6ceb5`。
本机普通安装与独立重放环境使用Python3.14.6；CI安装回执记录其各自实际Python版本。
当前PR检查还会覆盖后续证据追加提交，不将不同wheel的摘要混用。

## 直接查看

- [两平台CI产物下载后核验](docs/research-evidence/ci-artifact-verification-313c535.json)
- [原16单元当前构建结果与版本比较](docs/research-evidence/current-study-ci33969915599/README.md)
- [多窗口结果：在哪里失败、成本和敞口](docs/research-evidence/multiwindow-findings.md)
- [前向首个小时与部署证据](docs/research-evidence/forward-first-20260905/deployment-verification.json)
- [完整流程性能测量](docs/research-evidence/performance-ci33969915599/README.md)
- [逐项完成审计](docs/review-closeout-audit.md)

基准成本下Dual MA亏损8/16窗口、RSI亏损11/16；三倍成本后分别13/16和15/16。
较低回撤伴随较低实际敞口，不能只凭回撤宣称择时更好。此次没有选出“冠军参数”。
本机定时工作需要电脑和应用保持运行，见[官方说明](https://learn.chatgpt.com/docs/automations?surface=app)；
停机空缺保留，迟到按实际时间标记，不自动回填成准时观察。

[本轮逐项验收要求](docs/review-closeout-plan.md) ·
[成交事件规则](docs/execution-timing.md) ·
[固定多窗口计划](docs/studies/multiwindow-plan-20260905.json)

正式范围是 BTC-USDT 现货1h离线研究 CLI。GUI/旧HTTP服务发布、其他市场、
策略盈利和账户执行未验收；paper/live/order 权限保持 false。
数据与研究结果为描述性证据；2026年8月已经查看，不能标记成盲测或确认集。
