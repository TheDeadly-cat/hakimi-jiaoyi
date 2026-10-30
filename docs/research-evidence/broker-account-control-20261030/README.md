# 账户共享停止与受核验 protobuf 加载器：源码整合证据

本批新增了按“提供方 + 模式 + 账户”共享的停止控制。同一用户下的多个工作区读取同一账户状态，停止后共同阻挡新的派发；账户状态与回执可在候选页面查看。**当前窗口原有的本地停止仍保留**，本地停止与共享账户停止都必须通过，才能进入后续派发检查。

恢复需要明确确认最新停止回执并填写原因，只恢复准备资格。它不会延续旧 revision、重发旧请求、重启旧任务，也不会自动撤单或清仓。配置中的账户号仍是保存的声明，不代表已验证账户归属或券商授权。

这是源码、离线合同和临时夹具的整合证据。当前已交付候选仍为 **0.7.0.dev3 candidate-r4，源码 a235e8a2f1a303f72b99797105956bcd88cba399**；本目录不证明新包构建、安装、原生窗口验收或真实账户执行。r5 准备工作尚不构成已完成构建。

## 完整门禁与当前源码

[原始 summary](originals/fullgate/summary.json) 与 [环境收据](originals/fullgate/environment.json) 记录了父任务完成的本地整合门禁：

| 检查 | 结果 | 测试内部计时 | 外层计时 |
| --- | --- | --- | --- |
| [终端合同](originals/fullgate/terminal.log) | 756 / 756，0 skip / failure / error | 202.810 秒 | 206.287 秒 |
| [完整桌面检查](originals/fullgate/desktop.log) | 完整 `npm run check` 退出 0 | 原日志按子检查分别记录 | 20.127 秒 |
| [打包合同](originals/fullgate/packaging.log) | 15 / 15 | 4.065 秒 | 4.586 秒 |
| [runner 合同](originals/fullgate/gate_runner.log) | 4 / 4 | 0.034 秒 | 0.447 秒 |

完整门禁前后 2102 项输入映射逐字相同，SHA256 为 `2498bd31de2c31efde10e6e94c95026b2aaff200998e59adab67ef9eb8000a59`。完整映射原件保留在审计目录；仓库只保存明确标注为派生的 [输入摘要](fullgate-inputs-derived.json)，没有把摘要当成原始日志。

本次实际修改/新增源码与测试、注册文件共 **19** 项，逐项匹配完整门禁输入，归档时全部 2102 项当前输入也匹配。详见 [源码身份绑定](source-identity.json)。其中包含既有 `terminal-broker-candidate-ui.js` 的接线改动；未把状态文档或本证据目录计为源码。

[CI 168 成功原收据](originals/ci168/ci168-completed-summary-r1.json) 对应提交 `4ae90471f83afbdca9ef4e421e064690ede2b01d`，11 / 11 jobs 成功。它证明此前已提交源码的 CI，**不覆盖本批尚未提交的新增改动**，也不把 r4 重新认定为本批新包。

## 账户控制、主进程和真实服务接线

- [host 交接](originals/account-control/host-HANDOFF-r1.md)、[Node22 定向原日志](originals/account-control/host-node22-targeted-r1.log)：固定每用户共享根，不随工作区、安装位置或包版本变化；后台 health 必须匹配同一根身份。保留工作区单实例语义。
- [真实服务/路由交接](originals/account-control/service-route-HANDOFF-r1.md)、[11 项整合原日志](originals/account-control/service-route-integration-r2.log)：真实服务、handler、保存配置、共享控制与 journal factory，使用全新 TEMP；Jobs 仅同步委派到真实 mutate，不把它当成持久队列验收。
- [最后只读复核](originals/account-control/account-control-review-r1.json)：覆盖提交/幂等、停止→恢复旧 revision 失效、锁顺序、首次创建根身份、旧 mode 停止和权限不提升。本轮审查本身没有重跑测试。
- [核心首次失败说明](originals/account-control/core-first-run-note-r1.json) 是**工具输出派生 note，不是原始失败日志**：Windows 夹具连接未关闭导致清理失败；随后 [修复后原日志](originals/account-control/core-fixture-close-r2.log) 和完整门禁分别保留。未补造缺失 raw log。

## 页面夹具、原失败记录与截图

[UI 冻结交接](originals/account-control/UI-frozen-handoff.json) 引用的实际 TEMP 文件已逐字复制并核对其原 SHA。页面使用候选/研究 HTTP 夹具和真实 SYNTHETIC_TEST 账户控制服务；没有连接外部账户。

- [browser-result 原件](originals/ui/browser-result.json)：1440×1000 与 390×844，正常停止、另一窗口读取共享状态、明确恢复、丢失响应后查询原请求、未绑定根禁用操作；报告 0 console / external / websocket 错误或请求。
- [node-tests-final 原失败日志](originals/ui/node-tests-final.log)：原记录为 **46 / 47**；失败是既有 plan DOM 测试在该次临时 Node 调用中缺少 `NODE_PATH`，无法解析 Playwright。这个失败原件未覆盖、未改成 PASS。上面的完整 desktop 门禁在依赖配置完整的环境另行通过。
- [UI 临时服务脚本](originals/ui/server.py) 与 [浏览器脚本](originals/ui/browser.cjs) 仅作为原实验来源保存，本次整理未执行它们。

| 截图 | 场景 |
| --- | --- |
| [桌面停止状态](originals/ui/account-stopped-desktop.png) | 共享账户已停止 |
| [390 像素页面](originals/ui/account-narrow-390.png) | 窄屏按钮与布局 |
| [原请求回执](originals/ui/account-original-receipt-current-scope.png) | 原请求与当前范围分开呈现 |
| [共享根不可用](originals/ui/account-unavailable.png) | 未绑定时不声称已停止 |

## 私有 protobuf 加载器的实际边界

[冻结交接](originals/protobuf-loader/HANDOFF.md)、[定向收据](originals/protobuf-loader/targeted-r1.json) 与 [原日志](originals/protobuf-loader/targeted-r1.log) 记录了 24 / 24 定向检查。加载器验证私有解释器、包清单、实际生成类、来源文件与缓存身份，返回的权限仍全部为 false，`production_transport_available=false`。

[实际私有进程 invocation](originals/protobuf-loader/private-process-r1/invocation.json)、[result](originals/protobuf-loader/private-process-r1/result.json)、[runner-result](originals/protobuf-loader/private-process-r1/runner-result.json) 及 [stdout](originals/protobuf-loader/private-process-r1/stdout.log) / [stderr](originals/protobuf-loader/private-process-r1/stderr.log) 均为原件。该次探针使用未修改的 r4 Python，以 `-I -S -B` 加载明确哈希绑定的新源码，外层耗时 8.990 秒，加载/复核约 5.577 秒；观察 283 项 SDK 文件、加载复核 164 项本地文件，11 类真实生成 Response 对合成 bytes 完成 roundtrip。socket、DB、subprocess、thread、Futu 顶层导入尝试均为 0。

[private-child.py](originals/protobuf-loader/private-child.py)、[run-private-probe.py](originals/protobuf-loader/run-private-probe.py) 与 [run-targeted.py](originals/protobuf-loader/run-targeted.py) 按原引用保存。child 和 runner 均已与 invocation 内哈希对照。本次证据整理没有再次执行探针。

这些结果只证明本地来源身份与生成类加载，不证明 OpenD 协议/加密兼容、券商权限、外部执行或新加载器已安装进 r4。真正生产授权 gate、专用 worker 与 transport 串联、精确经济事实及价格规则、REAL codec/资金权限仍是未完成工程范围；不能概括为“仅待授权”。

## 原件、派生物与校验

[original-copies.json](original-copies.json) 逐项记录来源路径、目标、字节数、SHA256 和副本逐字一致性。这里的“原件副本”是文件来源说明，不把 producer note、review 或 summary 冒充原始执行日志。保留原件中的原路径、历史结果和时间，不回填、重签或改写。

[SHA256SUMS](SHA256SUMS) 覆盖本目录除自身外的全部文件；`.gitattributes` 设置 `* -text` 以避免 Git 换行转换改变原件。新 Markdown 相对链接的存在性检查见 [relative-links-validation.json](relative-links-validation.json)。证据整理只写本新目录，没有改状态/积压文档、源码、旧日志或旧包，也没有测试/探针重跑、Git add/commit/push。
