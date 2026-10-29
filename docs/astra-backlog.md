# 原终端产品交付任务清单

依据：用户 2026-10-29《Astra 持续执行任务书》第二版（30 项任务、三阶段）。本清单保留全部目标；工程、包验证、原生操作与真人理解分别结案。状态：TODO、DOING、DONE、BLOCKED_ENV、BLOCKED_AUTH、BLOCKED_HUMAN、BLOCKED_DEP。

## 当前基线与产品路线（T01 / T02）

- 权威交付目录：`C:\Users\Administrator\.codex\worktrees\insights-github-20261022\哈基米v2交易`；分支 `codex/p0-m32-research-integration-20261022`。开始时干净，HEAD / PR #26 均为 `db443e6ed2c758a858217a592bf7e074ec8affe6`，Draft / Open / 未合并。
- GitHub run 143 / `40794460886` 已实时核对为 success。该结果仅对应上述提交；后续源码与候选另验。
- 原 Documents 源码保留：35 项已跟踪改动、568 个未跟踪文件（`git status --porcelain --untracked-files=all`）。不在该目录实施整改。
- 实际 dev5 程序目录：`C:\Users\Administrator\Downloads\哈基米试用 dev5-f778020-r1`。当前 manifest 为 `0.6.0.dev5`，bundle `ab2e49cdc8e468385dd7b64dc30f2665aa7591a52b8d6022833c02983b7569a8`，SHA256 `c993523546b6c84e7a8be4a00636594f6fe8734ffa18dafc62e6e15125199b03`，与原验收一致。本轮开始未发现运行中的该 Electron 程序。
- 旧 dev5 数据：`%LOCALAPPDATA%\HakimiTradeTrial\workspaces\ab2e49cdc8e468385dd7`；原终端数据：`Documents\哈基米v2交易\outputs\python_quant_bot\runtime`。两者均保留，新候选使用独立明确工作区；旧结果读取/选择与新写入分开。
- 日常主入口固定为原 Electron `main.js` → 原 `exchange_terminal.server` → 同窗 `/quant/`。新候选名称为“哈基米交易”，首个整合包版本计划 `0.7.0.dev1`；旧 CLI / dev5 身份保持原样。
- 原九策略保留 `terminal.causal-long-only-signals-*` 与 `signal-close-next-open-ohlc-conservative-v3` 身份；冻结核心保留其版本、策略键和工作区。名称相同不转换公式、不混排。先接入任务/结果/导入/教学/复盘与退出，再接首次股票/更新/比较；执行演练在同一应用内独立页面和权限。
- 历史 UNKNOWN、暂停的 T3、旧包、冻结组件和历史回执不重跑、不替换。离线恢复只使用新合成案例。模型/外部券商/真实资金仍须沿用单独授权。

## 阶段 A：一个可安装、可完成研究并重开的程序

| ID | 状态 | 依赖 | 修改提交 / 验证证据 | 阻塞与下一步 |
|---|---|---|---|---|
| T01 | DONE | 无 | 本文实时 Git、PR、包 manifest、目录核对 | 保留两个源码与旧数据，后续只改交付目录 |
| T02 | DONE | T01 | 本文入口、规则身份、工作区与接入顺序 | 按原终端主线实现 |
| T03 | DONE | T02 | 阶段 A 源码；T03-completion-20261029、core-render-verification.json；真实渲染脚本故障注入 | 原/冻结核心均先确认保存，再分别处理辅助/详情失败；包内实走归 T15 |
| T04 | DONE | T02 | stage-a-source-final-r1.log、bounded-dom-qa-r3；79/80/81 阻止、82 就绪、长窗口与真实 runner 对照 | 只读预检查同源；失败先于 started 记录，不产生 UNKNOWN |
| T05 | DONE | T02 | strategy-semantics-audit.md、test_strategy_presentation（含实际 API 路径） | 独立展示层；原 STRATEGIES、公式及指纹文件未改 |
| T06 | DONE | T05 | terminal-parameter-preflight.test.js、bounded-dom-qa-r3 | 新建/修订/带入/回读统一单位；旧缺字段不补默认 |
| T07 | DONE | T03,T06 | bounded-dom-qa-r5；完整渲染真实点击，core-run-posts.json | 单入口；两条路径显示保存版本并明确运行；core 验证 expected_task_id；导航保留草稿 |
| T08 | DONE | T03,T05 | terminal-result-summary.test.js（9 项）、bounded-dom-qa-r3 | 摘要缺值未记录；零成交只引用实际保存证据 |
| T09 | DONE | T06 | T09-ai-binding-20261029；Python 14/14、JS 4/4；DOM 参数变更检查 | 数值行情与规则参数分别表达；费用/风控/来源真实性不扩大为 MATCH |
| T10 | DOING | T02 | terminal-lifecycle-workspace-summary-r1.json；完整桌面检查通过 | 原生重复启动/关闭仍在 T15 验证 |
| T11 | DOING | T02 | 原终端独立组件与闭包实现中 | 脱离仓库的真实启动验证 |
| T12 | DOING | T11 | 包内 Python / 资源验证启动实现中 | 中文空格路径、全局 Python / 同名模块污染隔离 |
| T13 | DOING | T11 | workspace-history-verification-20261029.json；四个旧工作区字节/mtime 不变；DOM 旧记录/复盘仅 GET | 已接入选择与当前路径，待新包核对 |
| T14 | DOING | T03-T13 | 6ca4015 CLEAN r1 构建、9043 ZIP 条目哈希通过；final-candidate-package-verification-r1.json | 原生启动发现日志污染程序清单，r1 作为失败候选保留；修复后重建 r2 |
| T15 | DOING | T14 | native-startup-inventory-failure-r1.json；真实窗口提示后台未就绪，程序根新增 debug.log；正常关闭且无任务运行 | 修正继承诊断环境并把日志写到包外后，验证新 r2 的完整原生路径 |
| T16 | DOING | T14 | windows-original-terminal-candidate.md、README、first-use、CURRENT_STATUS、包内 FIRST_USE.md | 新入口/身份说明已更新，待实际包回执补齐 |
| T17 | BLOCKED_HUMAN | T14 | 尚无未参与开发者的独立操作证据 | 候选完成后给出简短任务卡；其他工作继续 |

## 阶段 B：日常继续使用

| ID | 状态 | 依赖 | 修改提交 / 验证证据 | 阻塞与下一步 |
|---|---|---|---|---|
| T18 | DOING | T02,T11 | 独立后端适配已通过六项离线检查，尚未纳入阶段 A 冻结包 | 接入同窗页面/路由与独立 canonical namespace |
| T19 | DOING | T18 | daily-research-adapter-verification-20261029.json；旧核心列表无变化 | 更新/采用后端可用，页面和原策略输入桥待接入 |
| T20 | TODO | T08 | 待证据 | 成本/基准前提明确，异条件不排行 |
| T21 | TODO | T18 | 待证据 | 分阶段公司行为真实数据/核算；未支持明确限制 |
| T22 | TODO | T19,T24 | 待证据 | 持续本地模拟状态与中断恢复，不重复运行/补成交 |
| T23 | TODO | T18-T22 | 待证据 | 日常完整路径新候选；工程/真人分别记录 |

## 阶段 C：同一主程序中的执行准备

| ID | 状态 | 依赖 | 修改提交 / 验证证据 | 阻塞与下一步 |
|---|---|---|---|---|
| T24 | DOING | 稳定研究合同 | 新离线账本独立实现，尚未接入产品或阶段 A 包 | 需根任务核对研究版本绑定；外部权限保持关闭 |
| T25 | DOING | T24 | T24-T28-offline-execution-20261029（临时合成用例） | 独立审阅发现问题，修复后复验再接入 |
| T26 | DOING | T24,T25 | offline-execution-correctness-review-20261029.json | 晚到成交/股份预留/恢复停止/回执绑定等修复复验中 |
| T27 | DOING | T25,T26 | 子进程中断/重开/对账定向测试已有，未宣称产品验收 | 等独立复验；不触碰旧 UNKNOWN 或旧账本 |
| T28 | TODO | T20,T25 | 待证据 | 数据/规则/时点/撮合/成本/未知差异分解 |
| T29 | TODO | T25-T28 | 待证据 | 先离线候选与有界方案；真实券商模拟另需账户授权 |
| T30 | TODO | T29 | 待证据 | 模式隔离/风险/停止恢复候选；真实资金另需账户资产额度授权 |

## 验证记录

本轮外部证据目录：`C:\Users\Administrator\Downloads\Hakimi-Astra-Delivery-20261029`。旧整合回执目录和旧 CI 完整保留。本清单不会以单元测试代替包内启动、原生操作或真人验收。相关代码不变时不重复已结案的历史研究。

阶段 A 完整桌面检查：`stage-a-desktop-full-r4.log` 通过。根任务合并后的定向 Python：`stage-a-source-final-r1.log` 29 项通过；`stage-a-python-r1.log` 42 项通过（范围重叠，不相加作为独立总数）。浏览器使用完整 render_quant_html 与模拟后端，1440/1280；它证明界面交互，不代替包内真实计算。旧失败截图/日志均保留。

阶段 A 已提交并推送 `6ca4015b45bf02f765b933bb82725cc730a715c5`。干净冻结树的终端全门禁为 205/205、完整桌面检查和 6 项新打包检查通过。对应 CI run 144 / 40809973324 完整结束为 failure：两项 Windows 8.3 路径问题（健康测试预期与当前工作区排除）已定位；原运行不重跑或取消，修复提交单独接受新 CI。原生 r1 暴露的问题不被上述源码检查覆盖，相关失败包/日志/原 ZIP 均保留。

后续修复将当前工作区与测试预期统一为物理路径，并在窗口创建前清除外部 Crashpad 继承配置，将日志、后台工作目录和限长脱敏启动诊断移到独立数据目录。严格程序文件清单不放宽。`stage-a-r2-desktop-full-r1.log` 完整桌面检查通过；`ci144-focused-correction-tests-r1.log` 15/15 通过。新 r2 包的实际启动与生命周期验证仍待完成，这些源码检查不能证明原生问题已解决。
