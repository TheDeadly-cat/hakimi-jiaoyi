# Windows工作区路径修复

提交 `06d974447c077b2e214f849afe0396027301f3e8` 的本地完整检查通过，但 [CI175](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/42390359042) 的终端后端作业实际运行818项后产生8个错误，均在新增的策略状态恢复服务中触发 `history_path_outside_workspace`。原[CI作业日志](ci175-terminal-decoded.log)保留，日志按连接器解码文本保存为UTF-8/LF。不能把该提交称为CI通过。

## 原因与修复

服务把传入工作区的短路径保存为根，而共用目录检查把子路径规范化为长路径。同一物理目录因此在包含关系比较时被拒绝。本机普通临时目录没有暴露问题；使用Windows `GetShortPathNameW`取得真实8.3别名、确认 `samefile=True`，再把该别名设为TEMP/TMP，原10项测试复现完全相同的8项错误，见[复现记录](before.json)和[原失败](before.log)。

生产修复仅调整 `TerminalJourneyService` 的初始化：先拒绝原路径中的链接和重解析点，再解析真实路径，并复核规范化路径。之后的文件、父级目录、附属日志、硬链接数量、目录替换和越界检查保持。工作区身份原本已使用规范化路径计算，算法没有改变；原记录不迁移，不重新签名，不重新运行。

## 验证

- 普通临时目录 **15/15** 通过：[日志](normal-after.log)。
- 真实短路径TEMP/TMP **15/15** 通过，无跳过：[日志](short-after.log)、[环境](short-after.json)。
- 新回归覆盖不存在工作区的只读查询不建文件；短路径保存后从长路径、大小写别名和短路径重开，同数据库、标识和版本，文件字节/修改时间不变；真实Windows目录链接、越界目标和已存在目录被替换时继续拒绝。
- [源码SHA与专项交接](targeted-handoff.json)和[凭据原件表](artifact-origins.json)记录具体文件身份。独立只读复核未发现放宽保护或迁移原数据的问题。

完整后端在新的真实短路径TEMP/TMP环境下 **823/823通过，0失败、0跳过**，2,164项输入前后哈希一致：[完整结果](full-gate-summary.json)、[日志](full-terminal.log)、[真实目录别名](full-temporary-directory-alias.json)、[前置哈希](full-inputs-before.json)、[后置哈希](full-inputs-after.json)。新CI由后续修复提交触发，保留CI175失败，不重跑或覆盖它。

此修复没有更改界面、策略公式、交易权限或保存协议；前批[555项桌面和实际页面证据](../novice-workflow-source-20261107/README.md)继续保持其对应源码与范围。当前r5 ZIP仍为b642227，未重建。真实数据链、新包原生、独立Windows和真人验收仍按[U01–U12清单](../../novice-simplification-backlog.md)推进。
