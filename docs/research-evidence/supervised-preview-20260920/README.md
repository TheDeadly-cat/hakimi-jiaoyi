# 2026-09-20 受监督预览交付验证

后续已交付包含只读修复与最终研究摘要的[r3新包及独立安装验收](README-r3.md)。下文和`validation.json`保留r2的历史验收身份。

T5 已完成本机打包和新环境安装验收。正式 v0.2.1 未改变，没有创建 Release、
部署、注册调度、连接账户或发送订单。精确证据见 [validation.json](validation.json)，
使用方式见 [受监督预览说明](../../supervised-research-preview.md)。

冻结边界：r2包不包含之后的[只读零价格记录修复](../futu-preflight-20260920/resolution-followup.md)。包和原安装回执保持原字节，新候选的54项验证与实际只读复核单独保留。

最终交付是忽略目录 `artifacts/supervised-preview-20260920-r2/` 下两个独立 ZIP，
该目录的 `delivery.json` 保存完整文件名与摘要。它们只在本机交付，未推送到 GitHub。

| 包 | 完整构建身份 | ZIP SHA-256 |
|---|---|---|
| 研究预览 | `supervised-research-714ca6ec0a1ad8c389a0fcde446a19be8c9e2c1c2db5a551dd5b7cf7e64322a1` | `a40b9d7d6eeb08dd49defaae2007d81c18516533a6785161a990f2ca6c86f8e9` |
| Windows Futu 工具 | `supervised-windows-futu-60628eb6927c745289d3bcdc98bf44932bd14336b9a778a2519da7b8d80e74d0` | `80763153a71ba83e0e74b989c01bfe7bce064a2b0fb34767b24e50ecfd7ffa18` |

研究 wheel 为 `0.3.0.dev1`，SHA-256 为
`dd53860cfe265f623c7627f35668088fb6eda37066e05de790d5e2846fbc706b`；
研究源码摘要为 `c5d57ec371efe303741b12476fd6824c3eb4baa5e3cfb9cfd22c3a337fe236b6`。
构建观察是本机 `a64758a3df3ce73d433a2a2d71fac1e1a70dc5db` + `DIRTY`，
不能把 main 合并提交或其 CI 成功归给此候选。

| 验证 | 结果与准确范围 |
|---|---|
| 精确 wheel 仓库外普通安装 | 183 项根研究测试通过，0 失败／错误／跳过；Python 出站 socket 审计阻断。未包含 T2／T4 的仓库工具测试。 |
| 预览交付边界 | 7 项定向检查通过：内容与引用绑定、篡改拒绝、历史状态只读、安装源显式选择、旧环境不覆盖、确定性 ZIP。 |
| r2 从 ZIP 解压后重新安装 | 两个全新仓库外环境，均使用本地 wheelhouse／`--no-index`，无 editable／PYTHONPATH／系统包继承。研究源码和依赖均 VERIFIED，独立 SDK 的 9 个锁定依赖一致。 |
| r2 状态与帮助入口 | 两个 status 均成功，显示 `PREFLIGHT_INCOMPLETE` 与 `provider_order_quantity_or_price_invalid`、下单数 0；股票诊断和 Futu 周期 `--help` 在已安装环境及 socket 审计阻断下通过。帮助入口不连接 SDK／账户。 |
| r2 确定性封装 | 对解压后的同一批字节再次打包，两份 ZIP 摘要与最终交付逐字节相同。 |

首版保留在 `artifacts/supervised-preview-20260920/`，其新环境安装也成功。
之后主任务取得新的 Futu 只读前置阻断证据，因此另建 r2。r1→r2 **仅**变化
`README.md`、`evidence/CURRENT_STATUS.md`、`preview.py`，并新增
`evidence/futu-preflight-20260920.json`；研究 wheel、股票诊断工具、四个 Futu
执行文件与原研究证据字节都未改变。r2 重新创建并验收两个安装环境，未将 r1
安装回执改绑到 r2；183 项软件测试只执行一次并始终绑定同一 wheel。

准备阶段的失败也保留：Futu 的纯 binary 探测没有匹配分发，随后取得同版本
源码分发并构建 wheel；Futu／研究首次 wheel 构建均遇到全局 pip 缓存目录权限
错误。采用临时目录与禁用全局缓存后完成构建，研究首次失败发生在测试开始前。
原日志、失败构建目录与首版安装回执均未清理。

本包冻结的是固定十事件计划、原 AMD 新同期间／压力成本诊断以及来源准备材料。
主任务之后获得的新增历史行情与多事件结果在包外另行留存，未回改已冻结包。
打包验证只核对随包证据和安装，不复验历史账户状态，也不是官方模拟订单、
精确费用、盈利、无人值守、远端 CI 或正式发布验收。
