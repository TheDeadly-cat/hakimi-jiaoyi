# 同窗券商离线计划：源码、启动链与界面凭据

本批源码把离线计划接到同一终端：用户核对原候选、未发送意图、模式与预算后，明确保存一份离线计划；列表可找回计划，响应丢失时只读原请求，不重新准备。独立停止入口不排在慢任务后面；停止不是撤单，恢复不自动执行。保存成功也不开放任何外部权限。

这是源码与隔离夹具的验证记录。当前交付的 [dev3 r3 / f752958](../terminal-070dev3-r3-build-20261030/README.md) **没有本批新的 loader、计划服务和 UI 接线**；该包仍保持原身份。`97d0e0a2db45d021f48fb0eda285b53ccaf73300` 的最小私有启动夹具不是产品包。下一源码提交的 CI 与完整新候选、原生验收均需另记，不能由本目录推导。

## 可审查的结果

| 层次 | 实际结果与凭据 | 保证范围 |
| --- | --- | --- |
| 可信 loader | [root 24项稳定检查](loader/loader-root-verification-r1.json)、[日志](loader/loader-root-targeted-r1.log)；[15项打包检查](loader/packaging-verification-r2.json)、[日志](loader/packaging-targeted-r2.log) | 真实文件身份、目录/成员变化、模式与未激活拒绝；各自源码哈希绑定在回执中 |
| 真实私有启动 | [组装来源](private-fixture/assembly.json)、[实际命令](private-fixture/probe/invocation.json)、[结果](private-fixture/probe/result.json)、[独立审查](private-fixture/review-r1.json) | clean 97d0；真实私有 Python `-I -S -B -X utf8`，无 flags mock；5.546秒；4036文件加manifest的4037项前后记录完全一致。两模式读取283项锁定SDK文件身份但不导入SDK；adapter为空，兼容性仍未验证 |
| 离线计划服务 | [最终5文件身份与25项结果](service/source-after-and-verification-r1.json)、[最终日志](service/targeted-r3.log)、[实际服务响应合同](service/response-contract-r1.json) | 19项service＋6项integration；新TEMP明确合成资料，持久化claim/plan/receipt、原ID查询、重复请求、停止屏障、跨工作区和中断边界 |
| 公共路由 | [root 4项回执](service/root-routes-r1.json)、[日志](service/root-routes-r1.log) | 实际认证handler与新TEMP存储；不启动生产服务 |
| 最终界面 | [最终5文件冻结身份](ui/review-freeze-r2.json)、[18项日志](ui/plan-ui-r5-final.log)、[完整宿主页](ui/full-host-verification-final.json)、[实际服务合同读取](ui/actual-service-contract-r1.json) | 1280/480；完成卡、原请求、缺能力/未知、独立停止和本地截止时间。页面路由拦截，写请求只作用于内存夹具；真实订单、SDK和外网为0 |
| 组合后端与打包 | [原组合summary](integration/summary.json)、[542项终端日志](integration/terminal.log)、[15项打包日志](integration/packaging.log)、[4项runner日志](integration/gate_runner.log) | 542/542、0skip/0failure/0error；Python、打包、runner均exit0。原summary保留桌面环境失败，不能单独称整组通过 |
| 完整桌面最终状态 | [修正环境后的r3](integration/desktop-bound-environment-r3.json)、[r3日志](integration/desktop-bound-environment-r3.log)；[时间显示后的r4](integration/desktop-final-time-display-r4.json)、[r4日志](integration/desktop-final-time-display-r4.log) | Node22完整检查r3为20.01秒PASS；仅两文件时间显示修订后，最终r4为19.419秒PASS；当前冻结哈希以r4和UI freeze-r2为准 |

私有夹具只包含缓存CPython、12个真实导入源文件及锁定SDK文件；没有Electron、server、UI、实际adapter或完整依赖运行闭包。它的版本为 `0.0.0.dev0`、scope为 `PRIVATE_LOADER_IDENTITY_TEST_FIXTURE`、`production_candidate=false`，新bundle为 `bce0189925b37a7f36245c81a2e0793f0047eddcab01c7a22e8a0736ac59d1f5`。独立审查未重复探针或重哈希整夹具。组装回执中的“未probe”是组装阶段事实，之后的独立结果另存，原阶段回执没有改写。

## 环境失败与后续显示修订分别保留

组合启动首轮遗漏 child Python 绑定，子测试用了全局Python；原[desktop.log](integration/desktop.log)与[summary.json](integration/summary.json)保留失败。第二轮绑定Python后仍漏了已有Playwright的 `NODE_PATH`，原[r2回执](integration/desktop-bound-python-r2.json)及[r2日志](integration/desktop-bound-python-r2.log)保留。修正启动环境后完整Node22 r3通过20.01秒；没有为重试改变产品或测试行为。不能把原失败summary改写成PASS，也不能让它覆盖另存的成功来源。

随后仅 `terminal-broker-plan-ui.js` 和对应测试修改本地截止时间显示。最终18项与两个尺寸完整宿主通过；[语义保持回执](ui/local-time-semantic-preservation.json)确认 `boundsFromForm`、`validPayload`、`save` 原函数区段逐字不变：时限校验、原ISO与POST预算未变，原ISO仍在详情中。最终完整桌面r4再次通过，明确记录此前542项Python、15项打包和runner输入未受这两处纯JS显示变化影响；本次没有重跑这些Python组。

服务定向首轮的两处测试SQLite连接未显式close，修正测试后最终25项通过；[r1](service/targeted-r1.log)、[r2](service/targeted-r2.log)及最终r3日志均保留。更早loader或DOM脚本失败的完整原件继续保存在外部证据目录，不替换为后续结果。

## 截止时间与保存反馈

[1280本地时间对照](ui/local-time-comparison-1280.png) · [480本地时间对照](ui/local-time-comparison-480.png) · [1280最终保存状态](ui/full-host-final-saved-1280.png) · [480最终保存状态](ui/full-host-final-saved-480.png)。截图为离线完整HTML宿主，不是当前原生候选已验收的画面。

## 尚未完成的执行能力

全部九项权限保持false：外部连接、查询、提交、撤销、解锁、自动重试、自动恢复、自动模式回退及用户授权。SDK存在、身份匹配或PLAN_SAVED都不是券商授权；已知SYNTHETIC/QA研究固定离线。旧UNKNOWN、T3、原QA工作区与旧研究没有被读取、修复或重跑；本批没有生产GUI、SDK/OpenD连接、真实行情、模型或券商请求。

[锁定SDK预算静态审阅](sdk-budget-gap-review.md)说明：v1不能直接调用SDK默认quote/trade context并宣称预算满足。默认双连接、隐式账户读取/订阅、重连、内部轮询和超时/输出行为，必须由新的wire预算profile逐项限制并验证。当前仍缺实际scoped adapter、执行journal/worker、认领与派发屏障、真实费用/账户/证券证据及对应外部授权。T29/T30不因此升级为完成；不扩大旧计划预算、不继承旧AMD/profile或凭证。

## 文件完整性与留存

[副本来源清单](COPY_PROVENANCE.json)记录每份逐字副本的外部原件、SHA256和大小；`SHA256SUMS.txt` 覆盖本目录除自身外的全部文件。`.gitattributes` 保留原件字节并将PNG设为binary。本目录不包含runtime、SQLite、完整私有夹具或大幅输入map。4037项before/after map、2082项组合输入map及完整渲染HTML留在E；它们的路径与SHA在来源清单中，私有map还被独立review绑定。所有E原始资料均未修改。
