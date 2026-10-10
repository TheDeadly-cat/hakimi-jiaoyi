# M2-2 两项 P2 修复（2026-10-10）

PR #22 受审 `0059359` 已经用户单独批准合入 main `57b6bd4`；实际 main CI 38041602339 九项通过，Windows／Ubuntu 安装各 253 项。dev5 原件与原通过范围保留。

[PR #23](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/23) 修复两项 P2。当前状态：新候选及交付已验证；最终受审 head CI 单独核对，main 合并等待单独核准。M2-2 的两项缺口尚不作为已集成关闭。

[dev5 复现](dev5-reproduction.json)使用原安装（CLEAN `51b0f17`）、真实协议与虚构输入，没有上游替身；自洽重哈希副本可绕过四项成交边界，实际菜单 10 的两个内容策略均创建失败。原有效报告保持 SHA256 `49817b436106…`。

补丁共用原证券／会话／依据／信号检查，并核对计划唯一获准 BUY、被过滤机会、重复入场和保护性退出。菜单 10 使用共享参数表单，五种注册策略全部支持，后端未知参数拒绝保持。读取不重跑引擎；合法无成交、HOLD、保护性退出和期末持仓仍可读。

[新候选验收](acceptance.json)：`0.4.0.dev6`，CLEAN 构建 `30ece7d2d4369850586258690a4276c9e48baafe`；wheel `e70f3fc9fd06d6858b39b06b6466abef49be06c40e594c5520dff414b0aea29a`；运行源码 `11079b07ef017a2b5d6491584681ec21be522a825eb3df18c9d9119fa6fbb4e4`。同一 wheel 仓库外 Windows 262 项／166.301 秒通过，无失败、错误或跳过，9 项新增已包含在 262 中。8 项导出和 8 项封装源码检查另记，不相加为安装总数。原配置／输入／R3 流程仍通过。

[安装后边界流程](installed-content-boundary.json)实操五种旧菜单创建、检查、运行和读取；四项通用非法成交、错误机会、重复入场及内容过滤 BUY 的七类副本，在查看／恢复／比较共 21 路径均 STOPPED，原件和副本均不被读取操作改写。[旧 dev5 报告在新 dev6 只读兼容](dev5-read-compatibility.json)，全目录摘要保持；不重签。

[构建 CI](ci-build.json)：[38044626387](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/38044626387) 九项成功。Windows 安装 262／153.760 秒，Ubuntu 262／23.544 秒，根 MVP 262／185.451 秒。三个完整日志实际检出 PR 预览 `40e7d86`，其内容树与受审构建 `30ece7d` 相同（`dc8fd992…`）；不把预览改称受审 head。

[离线交付](delivery.json)为独立新 ZIP `6138b3767b5c…`，下载目录 `Hakimi-M2-dev6-ReportFix-20261010-verified`。[实际启动器首用](delivered-launcher-first-use.json)使用该 ZIP 解压的新目录和同一 wheel，离线安装、身份检查、输入中心查看／返回／退出及重开通过，新增计算 0；首用为代理，未声称人工验收。首次原生安装菜单以 EOF 退出，之后二进制捕获入口完成明确菜单操作。两次辅助脚本启动失败（命令引号、错误解压目录）[原记录保留](launcher-verifier-failures.json)；另两个证明检查器假设已修正，没有修改产品运行源码。最初失败目录与日志保留；交付使用 verified 目录。包内使用说明保留构建时快照，最终验收及集成以本记录和 PR 为准。

来源、测试输入及独立审计支持与接受构建分别绑定。后续仅文档／证据改动，不能将新 head 重签为 wheel 构建。正式 Release 仍 v0.2.1；市场研究、取数、供应商、账户、订单及监控未扩展，M1、M2-1 和 R1／R2／R3 保持关闭。
