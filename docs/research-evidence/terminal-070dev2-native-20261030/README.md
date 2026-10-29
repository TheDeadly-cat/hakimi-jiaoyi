# 0.7.0.dev2 r1：本机原生检查与合成订单

本轮验证了同一原终端中的股票检查、已保存研究转演练、订单预览和关闭重开。真实 TSLA 行情未通过公司行为覆盖检查，因此没有保存为研究输入，也没有据此回测或下单。合成订单使用已有虚构 TEST 研究，不能作为策略效果或真实交易证据。

## 程序身份

| 项目 | 已核对值 |
|---|---|
| 干净构建提交 | `0a29882314f1eec1fd5ac26088c064c5bea2ec7e` |
| 版本 | `0.7.0.dev2` / candidate r1 |
| Bundle | `b429bd6544bea3e6873ac00c297224981113d20c0d2fe2711f16abbbb88a73ac` |
| ZIP SHA256 | `b5c19a343c3f107fc8b9c903c30eb4f3d23e73d61c1cc9d132e4a784d4710e23` |
| ZIP 字节数 | 193020012 |
| Manifest SHA256 | `4ea0ae29a5393e4fdd09937b0f3237a379448509c799a7387db20fbc1a8dddcf` |
| 清单内程序文件 | 9059；原生操作后全部哈希不变 |
| 清单外文件 | 仅预期的 `terminal-manifest.json` |

程序位于本机 `C:\Users\Administrator\Downloads\Hakimi-Astra-Delivery-20261029\HakimiTrade-0.7.0.dev2-candidate-r1\HakimiTrade.exe`，同级 ZIP 保留。旧 dev1 r1–r4、dev5、Documents 原程序及历史失败均未替换。

构建门禁：完整终端 355/355、完整桌面检查、11 项打包检查通过；9060 个 ZIP 条目与文件清单核验通过。包内解释器执行一次新建虚构样例，额外新功能导入/页面渲染检查通过。包探测的首次本地 hostname 拦截失败日志保留，修正探测范围后重验通过；包字节未因此改变。

## 实际操作结果

1. 在“股票与数据”明确检查 TSLA 一次，默认 120 个交易日。原始响应已保留，但没有 `events` 字段；状态为 `BLOCKED / SOURCE_CORPORATE_ACTION_COVERAGE_UNKNOWN`。没有自动重试，也没有把缺字段替换成空事件列表。
2. 转到“执行演练”，读取原有 `r4 原生流程验证 20261029 · 版本 1`，不重新回测。真实保存报告 ID 为 `7b519a1de8dab29944f420135feb02d4cecf90b37cc1b89d4502a65d571381f0`，只读路由 ID 为 `d1a6ce8b508c26e457d655b0`。
3. 明确新建 `dev2 原生订单演练 20261029` 合成账户，初始现金 10000 USD，每单上限 1000 USD，费用预留 1 USD；保存计划绑定该不可变研究。
4. 选择合成买入 TEST、1 股、限价和参考价均为 100 USD。预览显示拟预留 101 USD；勾选本地合成确认后只提交一次。
5. 返回“已记录合成接受响应……尚未成交”。账本中只有一笔 `ACCEPTED` 订单，累计成交 0、持仓 0、费用 0、预留 101 USD、可用资金 9899 USD。订单 ID：`f177544bcf84a6fe4011832d6b0386f947d6fedc28c23789b2958bc17dbe6174`。
6. 正常关闭后进程与 8765 监听均为 0。重开同一程序，只导航、选择账户并查看原订单；预留与原状态保留，并要求完整合成对账，不自动重发或恢复。
7. 再次正常关闭后，57 个数据/操作文件与首次关闭逐字相同，新增、缺失和变化均为 0；账户表、订单、事件与请求也完全相同。旧 41 个数据/操作文件在本轮全程保持不变，历史 UNKNOWN 未操作。

实际数据目录是当前 MSIX 启动环境的物理隔离目录：`C:\Users\Administrator\AppData\Local\Packages\OpenAI.Codex_2p2nqsd0c76g0\LocalCache\Local\HakimiTradeTerminal\workspaces\default\runtime`。上述保全范围是该候选工作区，不宣称已验证所有用户安装的资料。

## TSLA 仍缺什么

检查 ID `76564997-32e4-463d-8e9c-918a2649b59e` 对应 2026-05-08 至 2026-10-28。响应有价格时间戳，`session_count=0` 表示公司行为检查先行阻断，不代表没有价格资料。价格、日历和原检查仍保持原字节。

需要能覆盖该证券、该区间的完整公司行为资料及来源说明，之后建立独立补证检查；旧 BLOCKED 不改签。单凭用户勾选、搜索未命中、旧年报或调整价相等，均不足以证明覆盖完整。本轮没有付费来源、券商连接、模型调用或真实资金操作。

## 证据与边界

本机证据根：`C:\Users\Administrator\Downloads\Hakimi-Astra-Delivery-20261029`。

- `final-candidate-acceptance-boundary-dev2-r1.json`：构建与私有解释器范围。
- `native-dev2-before-start-r1.json`：旧 41 文件基线。
- `native-dev2-tsla-source-check-r1.json`、`native-dev2-tsla-source-original-r1.json`：真实响应及阻断。
- `native-dev2-order-accepted-before-close-r1.json`：接受响应与原生界面；活动服务锁不可读一项明确记录。
- `native-dev2-normal-close-r1.json`：正常退出后完整哈希及 SQLite 只读核对。
- `native-dev2-reopened-order-ui-r1.json`：重开、原订单与恢复提示。
- `native-dev2-reopen-preservation-r1.json`：57 文件、账户表与原请求保全。
- `native-dev2-program-files-after-r1.json`：9059 程序文件保全。

尚未完成：真实股票完整保存/研究链、日常更新及持续模拟的原生验收、独立新手试用、干净新机与非管理员环境。订单本轮只验收接受/预留/重开；部分成交、全部成交、撤销与恢复合同的离线测试不冒充这些原生操作。

`0a29882` 的 CI run 151 有两个失败：Windows 短路径夹具预期、完整桌面检查遗漏日线 DOM。修复提交 `b624e8b` 的本地 18 项定向 Python 和完整桌面（含 16 项日线 DOM）通过，但远端 [run 152](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/40908673978) 在运行前拒绝了 job 环境变量中的 `runner.temp` 表达式，没有执行测试。`f4b7ebd` 将路径表达式移至安装与检查步骤，12 项工作流检查通过。[run 153](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/40911113462) 的 Windows 安装与 MVP 作业被后续 push 的并发策略自动取消，不能视为全绿；没有人工取消或重跑。

后续源码 `76cbfc6` 的 [run 154](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/40912129442) 完成：8 项独立作业成功，两项 Windows/Ubuntu 安装均因 `stock_intake_supplement.py` 漏入显式打包清单而失败，汇总门禁失败。已补齐清单及安装身份断言；本机仓库外普通 wheel 的 62 项相关检查通过，未使用 editable 或系统依赖继承、未下载。验证 wheel 来自有未提交修改的工作树，不是干净发布包；新提交的完整远端结果另验。上述后续修复不改签本页候选。

## 旧工作区原生读取（T13）

在此 dev2 原生窗口明确选择 Documents 原工作区和 dev5 工作区，只读取 MACD13 与 NDAQ 的原任务和完成结果。MACD13 的原运行/报告标识为 `eb83065c51850ffb07f3fc0c5c6cc799eac082c9f604275e517401bf2d0a2ef8`；NDAQ 原运行标识为 `31ef617084e578f673392d1eb106b2085d1b27220b5ac418c24cd96c9794a134`，原报告校验值为 `a8348a3a7ac46bdbc24f88911e9646524a5ed53a14995372bd8d69e7dccbace1`。NDAQ 仍为 8 个评分交易日、0 成交、证据不足；均未重新回测。

正常关闭后，四个旧工作区共 188 个文件的内容、大小与修改时间不变，当前候选的 57 个数据文件也与前次关闭逐字相同；进程与监听均为 0。证据为 `native-dev2-old-workspaces-before-r1.json`、`native-dev2-old-workspaces-preservation-r1.json`、`native-dev2-original-completed-result-r1.json` 和 `native-dev2-dev5-result-r1.json`。

实际发现两项显示问题：旧任务详情误用了结果摘要；一个只有身份标记的旧空工作区遇到 Windows MSIX 逻辑/物理视图差异。前者已在后续源码修复，完整渲染页面 1280/480 的 14 个场景通过，真实完成结果使用原运行标识，UNKNOWN 与未验证结果不显示完成摘要，切换工作区后的迟到响应被丢弃；0 POST，188 个原件仍不变。证据为 `old-workspace-detail-qa-20261030`。此修复尚未进入本页冻结包。空工作区视图警告仍保留，未放宽路径边界或迁移旧文件。
