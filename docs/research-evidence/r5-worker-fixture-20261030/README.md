# r5 冻结门禁失败后的夹具与环境修复证据

本批父仓库**唯一源码改动是 worker 测试夹具**。生产 `terminal_broker_worker_supervisor.py` 未变，SHA256 仍为 `a0171cad253111d0ff857be935140377e0083376bcbd1084203c7e0c62475837`。这份证据不证明已定位某个历史生产 handle，也不把测试资源清理改进写成生产 bug 已证实修复。

当前可交付包仍是 r4；r5 构建链在门禁失败后停止，未启动构建/探针，r5 目录和 ZIP 未产生。修复后终端计数预计 **757**，尚未跑新的完整门禁。身份与范围见 [source-and-validation-binding.json](source-and-validation-binding.json)。

## 两次阻断均保留

1. [旧门禁复用绑定失败](originals/dev3-r5-gate-binding-failure-r1.json) 检出 6 项 CRLF→LF 字节差异；[换行诊断](originals/dev3-r5-gate-newline-diagnosis-r1.json) 确认仅换行变化，但其中 `futu_context.py` 是实际打包输入，不能据此放宽原字节绑定或把旧门禁直接套到新冻结树。没有改 archive、源码换行或 Git 设置。
2. 随后对 `b5547330978c6c3afaba376c13ab1f2f583e1610` 新冻结树实际运行门禁；[原 summary](originals/stage-c-frozen-gates-summary-dev3-r5.json) 与 [失败交接](originals/dev3-r5-clean-gates-failure-handoff-r1.json) 保持 FAIL。不是正在运行，也不是通过。

| 新冻结检查 | 原结果 | 外层计时 |
| --- | --- | --- |
| [终端合同](originals/frozen-gates/terminal.log) | 756 项，0 failure、1 ERROR、0 skip；内部 196.322 秒 | 200.367 秒 |
| [Futu 状态](originals/frozen-gates/futu_status.log) | 32 项，0 failure/error、1 skip，未满足完整通过 | 0.575 秒 |
| [完整桌面](originals/frozen-gates/desktop.log) | 完整 check 退出 0 | 19.486 秒 |
| [打包合同](originals/frozen-gates/packaging.log) | 15 项通过 | 4.755 秒 |
| [runner](originals/frozen-gates/gate_runner.log) | 4 项通过 | 0.466 秒 |
| [health](originals/frozen-gates/health.log) | 6 项通过 | 1.092 秒 |
| [退出握手](originals/frozen-gates/desktop_exit.log) | 4 项通过 | 0.973 秒 |

终端 ERROR 位于 stderr 洪泛用例之后的 `TemporaryDirectory.addCleanup`：删除全新合成目录 `outputs/run-1` 报 WinError32。测试本体保留的 `cleanup_confirmed=True` 断言没有失败；历史占用 handle 未被具体确认。Futu skip 是新门禁 venv 缺少已安装 SDK 源，未执行对应源代码 AST 检查。

冻结门禁前后 2102 项代码映射相同；1046 项包装文件哈希和 installed-source 映射也相同。包装 before JSON 额外包含 reviewed_deltas 等元数据，因此**不是两份原 JSON 逐字相同**。完整大 maps 留在 E；[派生摘要与原件哈希](maps-derived.json) 明确记录比较范围。

## 仅夹具的 worker 修复

[原交接](originals/worker-fix/HANDOFF-r2.md)、[机器收据](originals/worker-fix/handoff-r2.json)、[原日志](originals/worker-fix/focused.log) 与 [result](originals/worker-fix/result.json) 记录一次 **23 / 23 PASS**：内部 8.322 秒、外层约 8.689 秒。

[测试差异](test-only-fixture-diff.patch) 增加独立、有限的夹具资源清理期限：确认 launcher 和所属线程结束，重新读取可能晚到的唯一所属 Popen，只处理自己的合成子进程与管道；删除前复核原 TEMP 物理路径和 inode，仅对 WinError32 有界重试，未收敛则保留夹具并报错。生产预算及原洪泛断言没有放宽。

新增确定性回归控制晚到 launcher，并注入一次所属目录 WinError32；断言只有一次 spawn、所属资源结束、恰好两次删除尝试，且该夹具原已密封 UNKNOWN/result.json 字节不变。它不修复或重新解释原失败门禁。当前测试文件 SHA256 为 `0220adfc0c6aae6a2d89ce4ca446ed0f184f83e1380c129987c76f65aaef260f`。

## 新门禁 venv 的 SDK 源补齐

[安装命令原件](originals/futu-environment/install-invocation.json) 与 [安装日志](originals/futu-environment/install.log) 记录仅向 `gate-dev3-r5-clean-venv` 安装既有锁定 Futu 10.7.6708 wheel，参数为 `--no-index --no-deps --no-compile`，没有下载或全局环境修改。wheel 哈希为 `a3bc7609fc7b60c0ca3cd2971bc8b81819338d3c88ad25d1bd3f647d781554b5`。

[定向日志](originals/futu-environment/focused.log)、[result](originals/futu-environment/result.json)、[guard-final](originals/futu-environment/guard-final.json) 记录一次 **32 / 32、0 skip PASS**，内部 0.075 秒、外层约 0.583 秒。socket、DB、subprocess、thread、Futu 顶层导入 guard 均为 0；SDK 仅被定位并读取源代码作 AST 检查，其他 context 是 fake，没有 SDK 导入或连接。

site-packages 从 871 项变为 1157 项，286 个新增项全部属于 `futu/` 与其 dist-info，既有项未修改、无删除。完整 before/after maps 留 E；派生统计见 [maps-derived.json](maps-derived.json)，原差异清单随 [process-result](originals/futu-environment/process-result.json) 逐字保留。[child.py](originals/futu-environment/child.py) 和调用收据仅作来源保存，本次整理不执行。

## CI 与交付边界

[CI170 成功原收据](originals/ci170-completed-summary-r1.json) 对应 `b5547330978c6c3afaba376c13ab1f2f583e1610`，11 / 11 jobs 成功；它不覆盖本次新增 worker 夹具修复。23 项与 32 项定向通过不替代下一次完整 757 项，也不代表 r5 已构建或验收。

[original-copies.json](original-copies.json) 记录逐字副本、字节数、SHA 和来源；大 maps、临时 runtime、Node compile cache、wheel 与 venv 本体没有归档进仓库。`.gitattributes` 为 `* -text`；[SHA256SUMS](SHA256SUMS) 覆盖除自身外全部文件，[相对链接检查](relative-links-validation.json) 均通过。本次仅写新证据目录，未改源码/状态/积压文档，未重跑测试/探针、构建、add/commit/push。
