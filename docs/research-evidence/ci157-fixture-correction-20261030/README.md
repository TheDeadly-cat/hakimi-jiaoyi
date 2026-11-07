# Windows 短路径夹具与首用说明修正

`c20341e4999d3fe7ac7e0ab64df4be164273d473` 的 [CI run157](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/40932729918) 已结束：9 个独立作业成功；终端合同与汇总失败。终端报告 464 项，29 个错误及 1 个连带失败。Windows `RUNNER~1` 临时目录与已保存原件的物理长路径混用，使新 replay 测试在准备资料时失败；并非策略有效性结论。

修正只涉及两个新测试文件：在夹具入口复现生产 `QuantWorkspace` 已解析的物理工作区，保留原件路径与工作区都解析后再计算相对地址；核心测试也从同一物理工作区准备原件。未修改生产路径检查、冻结组件、公式、默认值或旧报告。移除测试中未被使用的 `service.service` 别名，实际协作者仍为 `service.core`。

真实 Windows 8.3 TEMP 的全新子进程复现了原始比较失败，并在修正后完成 adapter 6 项与 API 16 项：**22/22 PASS，0 跳过，45.505 秒**。网络审计为 0。先前两次 21/22 的失败记录及定位 core 单项 1/1 记录保留；原 GitHub 运行不重跑。完整终端门禁的项目数量仍为 464，冻结候选另行执行完整检查。

另将随包 `FIRST_USE.md` 改为独立、版本中性的首用说明，版本从同包 `README.txt`、程序状态页及 manifest 核对，避免把仓库中旧 dev2 状态页作为未来 dev3 的使用说明。现有完整打包测试 **11/11 PASS**，包含真实映射断言。此修正不代表 dev3 已构建或完成原生操作。

本机证据根目录：`Downloads/Hakimi-Astra-Delivery-20261029`。

- `ci157-completed-summary-r1.json` 与 `ci157-terminal-job-decoded-mcp-r1.log`：当前运行结果及 connector 解码日志，日志仅统一为 LF，不宣称原始下载字节一致。
- `ci157-replay-short-temp-r1`、`r2`、`r3-core`、`r4-final`：逐次记录；最终依据为 `ci157-replay-short-temp-r4-final/handoff.json` 与 `tests-22.log`。
- `dev3-first-use-package-tests-r1.log`：11 项打包检查。

最终测试文件 SHA256：adapter `8dc87accdccfce752386110bfb86c0c40e7682d741c90702e01865db5a4abf40`；API `fc8c387a92973030a18f52f9670143fc1367abe0b9bfb38d7a605565de447032`。生产 ledger `686fc9e505e2bbba3b923e5c152c129185e9cbf245d302b878577ac1291a9481` 与 adapter `c6a9d592c4e791e67e1f9196784a3c53a0fa56c61737927b257ec1e96ea1e698` 保持不变。
