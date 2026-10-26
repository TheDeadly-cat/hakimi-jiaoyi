# dev5 首只真实股票：后台交付证据

状态：后台修复、安装验证与包核对通过；用户正在使用电脑，原生真实股票流程暂停，未完成全流程验收。

入口：[进度说明](../../first-stock-live-progress-20261027.md)、[结构化状态](verification-summary.json)、[桌面暂停记录](desktop-hold.json)。

## 证据范围

- [两次传输对照](transport-comparison.json)与[标准库代理选择](stdlib-proxy-selection.json)：同一请求合同、同一私有 Python；实际 Explorer 链在连接打开阶段超时，Codex 环境取得完整正文。另一次宿主预检未发请求。正文仅留本机外部证据目录，未进入产品。
- [41项传输检查](transport-fix-validation-r1.json)与[独立审阅](transport-independent-review-r1.json)：离线夹具，网络及经济内核调用为0；[前端日志](ui-final-reasons-r1.log)记录51项通过。这些都不能代替真实桌面联网验收。
- [普通安装回执](installed/wheel-acceptance.json)、[测试范围](installed/test-scope.json)及[来源身份](installed/source-build-identity.json)：415项与7项安装流程通过。installed 中保留同一受验收 wheel 与公开回执；测试范围有重叠，不相加。
- [试用包构建总览](windows-trial-build-summary-r1.json)、[私有运行时](windows-trial-probe-r1.json)与[运行时来源](windows-trial-runtime-sources-r1.json)：dev5 f778020，7096个ZIP成员逐文件匹配；程序目录含中文和空格。
- [构建显示错误说明](build-log-encoding-note.json)：构建器0，完成后的外层显示器1；原混合编码日志留在外部证据根目录，另附[UTF-8阅读视图](windows-trial-build-r1-utf8-view.log)。没有重新构建。
- [原生首屏](native/dev5-01-home.jpg)和[工具文本](native-tool-observations.json)：暂停前实际打开dev5。0输入/0任务/0结果由当时工具文本读出，不能当成暂停后的当前状态。下一次详情点击被工具拒绝，未完成版本详情回读。
- [保全基线](preservation-baseline.json)、[诊断后核对](diagnostic-preservation-after.json)及[构建准备](dev5-build-preparation.json)：旧r3的46个工作区文件、7096个程序文件和ZIP保留；两个旧STOP不回填新原因。广义历史保护范围引用既有保全证据，没有再次完整审计。

## 尚待恢复桌面后完成

先读取用户实际留下的窗口、版本与记录，避免重复操作；再验证NDAQ正常检查、证券确认、保存输入、明确创建5/10任务及明确运行。之后核对真实股票的“今天可以做什么”、成功状态恢复和关闭重开。没有新数据或准入停止时照实记录，不改参数制造成功。干净新机、非管理员账户、独立真人试用按用户安排后置。

本目录没有将外部诊断正文、构建探针或模拟界面测试冒充真实股票运行。当前GitHub推送和精确HEAD CI由PR后续回读另行记录，旧603e128的成功不得替代本次。

## 文件完整性

[copied-artifacts.json](copied-artifacts.json)逐项保存本机来源、字节数和SHA256；复制文件按原始字节保留。SHA256SUMS.txt覆盖本目录除它自身以外全部文件。JSON中的本机来源路径用于核对既有证据，不表示GitHub包含这些外部原件。历史dev4证据未修改。
