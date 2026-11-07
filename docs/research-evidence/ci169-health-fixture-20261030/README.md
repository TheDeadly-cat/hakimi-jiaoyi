# CI169 health 测试夹具最小修复证据

本批仅修改 `outputs/python_quant_bot/tests/test_research_management_boundary.py`：AST namespace 补 `BROKER_CONTROL_ROOT=None`，未绑定 health 的 expected 补 `broker_shared_root_id=null`，新增第 6 项测试，用真实 `bind_host_root` 验证绑定根身份的只读返回且不创建目录。生产 server 原本已定义该变量，**生产源码零变化**。见 [单文件差异](fixture-diff.patch)。

## 原失败与后续验证

- [CI169 原 job 日志](originals/ci169-python-contracts-job123847153681-r1.log)：272 项、1 项 health 夹具失败；namespace 缺变量使 `/api/health` 返回 502。
- [旧 r1 收据](originals/ci169-completed-summary-r1.json) 虽名含 completed，实际为 **in_progress / conclusion=null**，原名和内容保留。[真正终态 r2](originals/ci169-terminal-summary-r2.json) 为提交 `a0356e09da9dd493c1dc035624366b64eb2fc1c8`、attempt 1 的 **completed / failure**：11 jobs，9 success，Python contracts 与 required gate 两项 failure。这不是修复后新 CI。
- [完整 step 的新本地日志](originals/local/complete-research-contracts.log) 与 [result](originals/local/result.json)：273 项，health 6 项全通过，但整体仍为 **FAIL，1 failure**。内部 23.301 秒、外层约 26.114 秒；唯一失败是原 archive 字节哈希差异。
- [随后 health 定向日志](originals/local/targeted-health-r2.log) 与 [receipt](originals/local/targeted-health-r2.json)：**6 / 6 PASS**，内部 0.327 秒、外层约 0.827 秒。结果只覆盖这个测试夹具文件。

## Archive 原差异保持

[换行诊断原件](originals/local/archive-newline-variant-r2.json) 精确确认：归档 `paper_ledger.py` 本地字节与 Git HEAD 相同，LF 哈希为 `963734fc1711dadaf2c88771f013ef9c9522df46aaf7d631951822704614936c`；仅在内存把 LF 转成 CRLF，哈希精确得到旧 expected `b3380975818f4ab0f190f978cbed528e45903aca1c77168ac6510dd6362752a1`。原 CI 非 verbose 日志包含该 archive 模块，272 项仅报告 health 一项失败，没有逐项 archive PASS 行。未修改 archive、旧 manifest、Git 换行设置，也未把本地 273 项失败改写成通过。

## 原完整门禁与单文件白名单

[精确差异绑定](one-test-delta-binding.json) 记录旧/新 SHA、原完整 gate SHA 与输入映射 hash。2102 项输入当前仅此测试变化，其余 **2101 项逐字相同**：

- old：`2d93401147b81751d3ad460966fdcadbec43fbb8130efdaadf2e895e776854af`
- new：`ceebfa9b751c96518b32e29c9f0c5579ddd1bdded1e4a0ee6ca1d31ce33b0bda`

`run_terminal_contracts.TEST_FILES` 的 57 个所选文件不含该文件，静态搜索这些源码没有本测试模块引用；这是静态检查，不是新动态导入轨迹。[此前完整门禁](../broker-account-control-20261030/README.md) 的 756 / desktop / 15 / 4 结果维持原范围，**不声称 756 执行过新 fixture**。

JSON 的 r5 clean binding 差异白名单只允许这个精确文件与哈希转换。程序打包映射是否排除该测试由构建任务另核；本证据不宣布修复后 CI、r5 构建、安装或原生验收成功。

## 来源与校验

[original-copies.json](original-copies.json) 逐项记录原件来源、字节数、哈希和逐字副本；[原运行脚本](originals/run-ci169-health-fixture-fix-r1.py) 仅保存未执行。完整 2102 映射仍留审计目录，此处只保存明确标注的派生绑定。`.gitattributes` 为 `* -text`，[SHA256SUMS](SHA256SUMS) 覆盖除自身外全部文件；[相对链接检查](relative-links-validation.json) 均通过。本次只写新证据目录，没有重跑测试、修 archive、改 Git 设置或 add/commit/push。
