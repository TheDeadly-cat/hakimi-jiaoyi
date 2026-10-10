# M3-1 操作时钟修复与 dev2 交付

[PR #24](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/24) 在 dev1 的全部功能基础上修复操作时钟缺口。M1、M2-1、M2-2、R1／R2／R3 和原两项 P2 保持关闭；本轮仍为离线合成账户与固定输入，不扩展 Unknown／T3、监控、券商执行、市场研究或正式 Release。

## 缺口、修正及历史边界

Cursor 对 `0631f76` 的[评论](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/24#discussion_r4237703206)指出较晚操作 at 可推进 current_at，让有效预留无法按原时点结算。[原 dev1 安装复现](dev1-reproduction.json)覆盖错误预留时间、未知 CANCEL、未知 SETTLE；三种情况都使当前时点提前到 15:30，随后正确 14:30 结算被挡、迟后结算按过期拒绝并释放。原 dev1 的 288 项、wheel、ZIP 和日志保留其已验范围，没有覆盖这项缺口。

dev2 新账户及回执采用 v2 规则：只有显式 MARK 完整价格更新才能推进时点，其他新操作必须使用当前固定时点。错误时间在流水发布前拒绝；未知或终态重复操作不能推进时钟或使另一有效预留失效。合法 MARK 后的过期判断／释放保持。操作 ID 的原回执查询仍幂等，历史请求不被重新发布。

旧 v1 账户在 dev2 仅只读，按原 v1 语义验证原记录，不改签、不自动修复、不作为 v2 新写入账户。源包内只读夹具是原已安装 dev1 实际生成的 account.json／SQLite 原始字节和摘要，不是新代码伪造的历史。[实际旧任务账户兼容](dev1-read-compatibility.json)另读原 dev1 下载目录的真实 TASK_STEP 合成账户，流水 1、预留 8,000，完整验证通过，原两个文件摘要保持。它与包内最小手工信号夹具是两种证据。

## 精确候选与验收

候选 `0.5.0.dev2`，CLEAN 构建 `f2fac8cec30669f137b376747e44a53c43c42c79`；wheel SHA-256 `816f93eb81c74ac5ba4bbf3d092ee00447b093377f28aa2f017559c75f6a93f6`；运行源码 SHA-256 `026d079e7679c1226265b6e1c841514d7d5f60df23337b7e8a9cfbbae08e3fef`。见[接受回执](wheel-acceptance.json)、[构建身份](source-build-identity.json)、[测试及源码范围](test-scope.json)、[锁定依赖](dependencies.json)。

同一新普通 wheel 在全新仓库外 Windows 环境非 editable 安装，**292 项／170.321 秒**，失败／错误／跳过均 0；新增四项时钟／旧字节检查包含在 292 中。共享源码 30 项和包导出 9 项另记，不加为安装总数。原输入、配置、R3、内容报告边界和全部共享流程保留通过。

[安装后共享流程 v2](installed-shared-funds.json)在原完整流程上增加真实冷命令错误时间拒绝、另一有效预留仍可结算、旧 v1 字节可读及写入阻挡。两真实进程只允许一笔 8,000 预留，COMMIT 前后中断分别留下 0／1 回执；五类既有规则、全局资金与日损失限制、条件暂停恢复、释放、去重和目录迁移仍通过。

[构建 CI](ci-build.json)绑定 [38055503091](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/38055503091)：最终九项成功，run attempt 2 只重跑失败任务及其聚合门槛；原成功的安装／MVP 等任务保留。[第一次失败](ci-retry.json)是未修改的旧 PowerShell UTC 探针进程超过原 15 秒启动时间；完整失败日志保留，没有修改原测试、断言或超时。最终提交另行核对 CI，不将重跑或预览改称受审 head。

## 新交付

[交付清单](delivery.json)绑定新 ZIP `b1892c8a5c853a3f93905396c475f9aec9f4e8ae59a61ae9fd49659dbd7235d0`，本机新目录 `Hakimi-M3-dev2-ClockFix-20261010-verified`。[外层启动器首用](delivered-first-use.json)完成该 ZIP 新解压、同 wheel 离线安装、共享菜单生成意图、退出重开／查回执；两次退出 0，预留 8,000、可用 2,000、流水 1，读取不改账户原字节。首用为代理，不声称人工验收。dev1 新旧原件均保留。

[共享资金使用说明](../../shared-funds.md)。M3-1 为固定时点合成账户基础，完整增量监控与逐根 OHLC 运行仍属后续范围。正式 Release 仍 v0.2.1，main 合并仍须最终 head 单独核准。
