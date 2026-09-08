# 当前研究 CLI 状态

更新时间：2026-09-08。本页集中记录当前证据；历史报告保留原始版本与当时状态。

供讨论的简短入口：[9月8日项目进展记录](docs/progress-20260908.md)，附截至北京时间15:03的前向覆盖JSON。

北京时间23:00更新：[72小时观察窗口结果](docs/research-evidence/forward-window-20260908/README.md)已汇总并附原始观察与执行回执；窗口已结束，存在迟到与缺失，可靠性仍需评审。

**0.2.1基线已通过当前PR检查，但尚未合并或正式发布；后续连续研究与0.2.2变体诊断独立推进。**
PR #1最新修复`ec631287fcd579981db1a1904faacf4e841e0245`已解除旧界面配置审查阻塞，
[CI34019161628](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/34019161628)的9个实际Job全部成功。
合并与正式发布正在等待维护者明确授权，不能将临时Actions产物称作已发布Release。

下一阶段见[当前任务状态](docs/next-stage-status.md)。已完成的[15条连续历史轨迹](docs/research-evidence/continuous-history-20260906/README.md)
仍使用原受验收0.2.1源码，正常成本Dual MA总收益−6.07%、RSI−28.01%；15/15独立重放及账本核对通过。
这些是同一笔起始资金的持续路径，不是把旧reset-window收益拼接起来。
[两项变体诊断](docs/research-evidence/strategy-diagnostics-20260906/README.md)使用新的0.2.2构建，
16/16轨迹已独立重放通过：去固定止盈的Dual MA正常成本收益+6.77%，但压力成本与后续历史不稳；
单事件入场RSI仍为−23.69%。两项候选均停止本轮晋级与追加调参。

直接查看[自动生成的只读研究视图](docs/research-view.md)：每个摘要数值可回查规范投影，
连续、reset、0.2.1、0.2.2及成本档位明确区分。新增0.2.2实际研究wheel为本地验收件，
源码`f657a07534061e7d03d2922b1fc1a69eeea04751a7a6201ac961ee55e76cf767`；
与[CI34019386267的双平台安装件](docs/research-evidence/strategy-diagnostics-20260906/ci-build-crosscheck.json)
运行字节相同，构建checkout与wheel摘要分别保留，没有把旧研究重标成新CI。

[六次重复性能测量](docs/research-evidence/performance-repeat-20260906/README.md)仅测原0.2.1：
新进程冷导入完整流程中位4.591秒，同进程暖导入3.519秒，均完整重放通过。
没有应用性能优化，没有优化前后提速结论；0.2.2性能未测。

[前向运行覆盖](docs/forward-reliability.md)已确认首个自动周期及实际缺口。旁路回执工具已接入原本机调度；
旧包、三份冻结工具和原始观察保留原字节。新包装器的首次自动运行已于9月6日09:10:20 UTC触发并成功结束。
截至9月8日15:05 UTC，完整144个策略小时中106准时、14迟到、24缺失；124条现有观察重放通过，其中120条属于固定窗口。
最新证据见[72小时窗口结果](docs/research-evidence/forward-window-20260908/README.md)。观察汇总已完成，存在迟到与缺失，不能声称持续准时运行已通过验收。
提交审查分别为[研究PR #2](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/2)与
[运行记录PR #3](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/3)。当前状态以各PR页面为准。

## 原0.2.1研究基线证据

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
| 前向观察 | 两个冻结空仓参考状态计划；首个已证实原驱动自动周期为9月5日15:03:50 UTC。72小时窗口已结束：144策略小时中106准时、14迟到、24缺失；新工具53次窗口内调用均有结束回执。观察汇总完成，可靠性保留待评审；之后继续原小时观察 |
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
