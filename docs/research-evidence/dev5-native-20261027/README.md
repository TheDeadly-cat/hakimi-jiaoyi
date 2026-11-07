# dev5 NDAQ 原生首用与关闭重开证据

本机原生验收通过。程序身份仍为 f778020 / 0.6.0.dev5，未更换计算内核或重新打包。结论仅覆盖本机实际流程；独立真人、新电脑和普通非管理员试用仍由用户安排。

- [验收报告](../../dev5-native-acceptance-20261027.md) · [结构化状态](verification-summary.json) · [要求与证据](requirement-evidence-map.json)
- [输入、证券确认、参数、任务和运行回读](first-run-readback.json)：真实产品取得11992字节原件；20根完整日线，12预热、8评分；一次正式运行、零成交，样本不足。旧外部诊断正文未替代产品输入。
- [原生观察索引](native-observations.json)：保留原工具文本和未经编辑的JPEG，覆盖版本、检查、确认、设置、结果、今天入口和重开回读。其余过渡画面保存在本机外部证据目录。
- [关闭前37文件](pre-close-workspace.json) · [自有进程](pre-close-processes.json) · [关闭后进程和监听退出](closed-processes.json) · [重开后37文件完全一致](post-reopen-workspace.json)。
- [旧记录与原Documents保全](preservation-public.json)：旧r3 46文件和两个STOP保持；原Documents状态、差异与566非忽略未跟踪文件保持。与任务无关的原始差异内容和文件名清单留在本机。
- workspace/保存本次37份工作区文件的原字节副本，包括来源、冻结输入、任务、运行、请求回执和一次UNCHANGED更新；这些是验收证据，不是迁移安装包。

[此前暂停记录](../../first-stock-live-progress-20261027.md)和dev4两次STOP保留历史身份。本轮仅明确检查两次（首次获取、日线更新各一次），没有自动重试、调参、新建假日线或为零成交制造交易。无新增或修订日线时没有创建新版本。

SHA256SUMS.txt覆盖本目录除它自身外全部文件；copied-artifacts.json逐项绑定本机原件与提交副本。最终提交和CI在推送后单独核对，本文不借用旧HEAD结果。关机是用户另行要求的最终操作，验收回执本身不证明机器已经断电。
