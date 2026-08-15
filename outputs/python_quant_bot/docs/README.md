# 哈基米交易 v2 文档入口

本目录同时保留当前工程基线、优化评审和历史研究记录。文件被保留不代表其中的策略、运行状态或授权仍然有效；开始工作时应按下面的权威顺序核对当前源码与最小运行证据。

## 当前权威入口

1. [`../DEV_BASELINE.md`](../DEV_BASELINE.md)：长期工程不变量、验证分层和交易权限边界。
2. [`project_status.md`](project_status.md)：按时间追加的工程状态；先读文件顶部的最新切片，再核对“当前已知限制”和“下一步建议”。历史段落只说明当时证据，不能覆盖顶部当前状态。
3. [`optimization_review_2026-08-10.md`](optimization_review_2026-08-10.md)：当前优化取舍、轻测试策略、已完成切片和后续优先级。

`modularization_status.md` 是模块边界的辅助台账；它的“当前模块边界收口”段落只作结构索引，不能替代前三个权威入口。

源码、当前测试结果和实际运行证据优先于文档中的历史数字。定向测试只证明其覆盖范围，不等于完整回归、浏览器验收、策略盈利能力或交易授权。

## 研究与历史材料

- [`strategy_hypothesis_preregistration_template.json`](strategy_hypothesis_preregistration_template.json) 是当前 report schema 13 / hypothesis-v2 新策略研究的可编辑草案起点。必须替换占位 ID、代次、机制和结构化失效谓词后，由 runner 在任何行情读取前归一化与封存；模板本身不是有效登记、策略结论、盈利证明或交易授权。schema 7–12 的 hypothesis-v1 只保留历史验证兼容，不再是新研究模板。
- [`g50_daily_swing_hypothesis.md`](g50_daily_swing_hypothesis.md)、[`g50_research_governance.md`](g50_research_governance.md) 与 [`g51_squeeze_breakout_development_preregistration.md`](g51_squeeze_breakout_development_preregistration.md) 是已否定假设的历史材料。G50/G51 旧策略 ID 只允许复核历史证据，不得调参后开启新一代研究；新机制必须使用新策略 ID 并重新预注册。
- `g51_*snapshot*` 与 [`g51_reconciliation_manifest_2026-08-10.json`](g51_reconciliation_manifest_2026-08-10.json) 是迁移/对账留档，不是当前源码清单或发布许可。
- [`project_handoff_2026-08-10.md`](project_handoff_2026-08-10.md) 及更早的产品、平台和模块化文档是历史决策背景；若与前三个当前入口冲突，以当前源码、当前证据和前三个入口为准。

## 固定保护范围

- 不把回测、重放、Hash 一致性或研究报告通过解释为盈利证明。
- G42 仅用于自然前向观察；模拟盘未授权，实盘真实下单永久硬锁。
- 不读取或迁移 `.env*`、本地配置、运行目录、数据库、缓存、日志、截图、密钥或口令。
- 日常改动只运行最小相关验证；冻结新基线、安全发布或风险核心变化时才运行完整回归。
- 保留用户文件和未跟踪内容；不清理、不重置、不整目录覆盖、不擅自提交。

## 更新约定

- 新完成的工程切片先更新 `project_status.md` 顶部，再同步 `DEV_BASELINE.md` 中受影响的不变量；涉及优先级变化时再更新优化评审。
- 历史段落保持追加式，不回写成“当时已经知道现在的结论”。过时待办应在当前入口明确标为已完成或已取代。
- 每条完成声明同时写清验证范围和未验证范围，尤其区分纯函数/静态合同、HTTP 服务、真实浏览器、自然前向统计与交易授权。
