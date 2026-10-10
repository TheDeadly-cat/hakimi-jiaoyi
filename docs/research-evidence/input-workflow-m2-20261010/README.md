# M2-2：统一离线行情与研究输入

本轮从已集成 main `4732bcc` 开展新的功能建设，[PR #22](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/22)。M1、M2-1 与 R1／R2／R3 均已关闭；历史候选、原回执和市场研究没有改写或重跑。

正常 `hakimi-trade` 入口新增菜单 16 和相同的 CLI 导入／选择／检查／绑定操作。行情继续使用原快照、证券、日历和公司行为合同；排期继续使用原版本上下文。财报字段候选、人工核准回执、规范文本与原件以原字节封存，再绑定任务版本。更新输入保留暂停状态、旧任务输入和原报告。来源声明、输入身份、可用时点和语义核准分别展示。

接入既有公告排期过滤，以及原 C 首个完整公告后交易日价格确认／D 已核准下季指引中点高于当前营收条件。这里没有替换旧 NVIDIA“当季实际／已列前次指引”协议，也没有发起新的公司研究。价格、内容 UNKNOWN/HOLD、过滤、无干预及评分窗口外的适用性分别解释；成交、风控与账本由同一引擎计算。

| 证据 | 本轮核实结果 |
|---|---|
| 受验收候选 | `0.4.0.dev5`；CLEAN 构建 `51b0f170f201c9ba62c9cae2e263efad123b212c` |
| 同一接受 wheel | SHA256 `b935fde7b4369e8900ccabddcab5817fa68f59b0191e0585fff6b9cc669d8c20`；[公开安装回执](wheel-acceptance.json) |
| 运行源码 | `8c85724cdf8f1d487d07b932de6a56fd36efd6fa0b794cfcbbafdf1becaf3a86`；[原构建身份](source-build-identity.json)、[源码与验收范围](accepted-source-scope.json) |
| 仓库外普通安装 | 同一 wheel，隔离依赖、无 editable／PYTHONPATH／系统 site-packages；253 项、146.545 秒、退出码 0、无失败／错误／跳过或预期失败；[完整测试范围](test-scope.json)、[依赖](dependencies.json) |
| 实际安装入口输入流程 | [冷进程记录](installed-input-workflow.json)：真实菜单导入 CSV、研究绑定；只读检查、两类规则的版本更新、暂停／拒绝保持、运行比较、退出重开、整目录迁移和重放均通过 |
| 输入与结果保持 | 原快照及候选包原字节保留；旧任务、输入和报告未覆盖；未核准内容 HOLD，合成核准正对照与同条件价格基准结果一致、内容干预 0 |
| 构建 head CI | [38036110148](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/38036110148) 九项 Job 成功；Windows／Ubuntu 安装各 253 项和实际输入流程通过。实际检出 `d5bcd40b735d3492b85423e18f9970a69aa861e8`，内容树与受审 `51b0f17` 相同；[日志与树核对](ci-build-51b0f17.json) |
| 离线交付 | `Hakimi-M2-dev5-Inputs-20261010`；同一 wheel、五个锁定依赖及启动器，ZIP `f55c4a08bdbac88f491f51ec1ef4b44c2ac54aa21b441de751790c7c605ed208`；[交付身份](delivery.json) |
| 交付启动器首用 | “开始使用.cmd”实际离线安装、身份检查、输入菜单打开和退出，退出码 0；安装版本、构建与源码均匹配接受 wheel。未新增经济计算；[启动器记录](delivered-launcher-first-use.json) |

253 项已经包含原 241 项和新增 12 项；针对性源测试、冷进程流程、启动器首用及远端各层不能再叠加为完整安装测试总数。操作者为代理，输入为 `SYNTHETIC_TEST`；正对照仅使用明确标注的合成契约回执，不声称用户已人工核准该样例，也不产生市场或策略有效性结论。

[开发试次](development-trials.json)保留早期 adapter 调用错误和负例预热配置错误的原日志摘要；没有弱化原断言或把失败改签为通过。[目标与范围](requirements-and-focus.json)记录两类既有规则的授权范围。本机第一次完整 wheel 试次即通过，原临时产物和日志保留。

启动器核验的前两次记录因 Windows 输出解码失败，分别保留[第一次记录](first-use-capture-failure.json)和[原始字节记录](first-use-capture-failure-trial2.json)。实测隔离 Python 的重定向编码为 GBK；第三次在新的解压目录普通安装，按实际编码严格读取原始输出，再核对原生退出码和身份。程序规则、接受 wheel 和两次失败记录没有为此改写。

交付后的后续文件只同步日常入口、公开证据和 ZIP 内的输入指南别名；运行源码、构建定义、依赖、安装验收脚本与完整测试输入保持接受 wheel 的原字节。接受 wheel 始终绑定 `51b0f17`。最终 PR head 的 CI、实际检出和检查用 wheel 在 PR 实时记录及本机交付收尾回执中另行核对，不将 CI 新构建改签为这个接受 wheel。

PR #22 尚未合入 main；主分支合并按既有要求另行批准。正式 Release 仍为 v0.2.1，Unknown／T3、原市场研究、账户、订单、共享资金与新监控保持各自原边界。安装与输入流程只证明本次离线工具功能交付。
