# M2-1 R3：策略切换修复与安装验收

R3 修复提交于 [PR #21](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/21)，基线为已集成 main `9085eab`。当前 main 的已知 R3 仍待单独批准合入；PR #20、M1、R1／R2 和原 CI 身份更正保持已完成。

命令行修改版本、复制与菜单使用共用配置处理层：同策略保留未改参数、隐含默认值和必要事件输入；切换时只替换继承的策略参数、风险及事件输入，未指定参数／风险时使用目标新建模板，显式文件完整验证。共同快照、本金、费用和评分日期保留，预热不足仍拒绝。价格防混用、数值校验、回测、风控、成交与账本代码没有放宽或重写。

| 证据 | 本次实际结果 |
| --- | --- |
| 原 dev3 正常安装入口 | 两条事件到价格策略修改失败，合法目标配置仍被旧事件输入阻挡；[原复现](dev3-installed-reproduction.json)，原状态和字节保持 |
| 新候选 | `0.4.0.dev4`，CLEAN 构建 `015cc397f8e8c8df6e36cdd26f2b4293e8d41a23` |
| 接受的 wheel | SHA256 `1a04a086b93111ea2b8b5b3e4be228910e2bde895d85c54109b1e4f36251d31c` |
| 运行源码身份 | `4186c9d80351797653dd4d0e90228725be5c6d0a5b3c24827a0769a9dc1e2fcd`，与 CI／定向 trial 的运行代码相同；不同 wheel 的构建身份分别记录 |
| 本机全新仓库外安装 | 普通 wheel 安装，隔离依赖，未使用 editable／PYTHONPATH／系统 site-packages；241 项通过，无失败、错误、跳过或预期失败；[验收](wheel-acceptance.json)、[测试范围](test-scope.json) |
| 同一接受 wheel 的冷进程流程 | [实际入口记录](installed-strategy-switch-workflow.json)：两条命令行修改、两条真实菜单路径、复制与模板对照、同策略仅改本金保留旧 8%；显式事件冲突、反向缺少事件、不兼容参数、仓位／现金政策和无效基准保护均拒绝 |
| 原件与状态 | 修改与失败保持暂停、原选择、旧版本、输入及报告字节，成功版本连续绑定同一家族父版本；[源码范围](accepted-source-scope.json) |
| 构建 head CI | [37962837541](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/37962837541) 九项 Job 全成功；Windows／Ubuntu 实际 Job 检出均为 `53e28a24e5af1e37c4ad69b8afe4a23f11cc9e7e`，内容树与受审 `015cc39` 相同；安装各 241 项和冷进程 R3 流程通过。见 [CI 记录](ci-build-015cc39.json) |
| 新离线交付 | `Hakimi-M2-dev4-R3-20261010`：同一已接受 wheel、五个锁定依赖与现有启动器，ZIP `bb67733aec545d75b4e309e64de28c2b5c45bbc367180a87555f25b68e0fbdba`；[交付身份](delivery.json)，主安装指南已同步 `0.4.0.dev4` |

241 项包含原 232 项与新增 9 项；定向入口流程、菜单及复現不再加到单位测试总数中。所有本轮输入为 `SYNTHETIC_TEST`，操作者为代理，不声称用户已人工试用，也不产生市场结论或账户／订单权限。

保留 [初次安装 fixture 失败](first-installation-failure-ccd6000.json)、[参数拒绝名称不符](second-installation-failure-82544d1.json)、[风险拒绝名称不符](focused-verifier-failure-82544d1.json)和[本机未完成 trial](local-interrupted-trial-015cc39.json)。只修正新验收脚本的合法基准风险及既有校验器名称；原风险 case 保留，并追加独立的非生效保护字段拒绝。原日志、临时 wheel、目录、dev3／dev2 与旧证据保留，不补写通过、不改签构建。

早先[定向安装记录](focused-installed-workflow-82544d1.json)只证明同一运行代码的 R3 流程；完整接纳以本次 `1a04a086…` wheel 的新验收为准。最终文档 head 与其检查在 PR 实时记录中单独核对；本次不重跑原市场研究，不恢复 Unknown／T3、账户、订单或监控。正式 Release 仍为 v0.2.1。

新交付目录的“开始使用.cmd”已实际完成离线安装、身份检查、打开菜单和退出，退出码为 0；安装后查询确认版本 `0.4.0.dev4`、来源 `015cc39` 和源码身份与接受 wheel 相同。见[交付启动器首用](delivered-launcher-first-use.json)。此项只验证新包启动路径，不新增策略运行，不代替原完整 wheel 验收，不声称人工试用通过。
