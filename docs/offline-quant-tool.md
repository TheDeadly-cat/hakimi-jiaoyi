# 哈基米交易 M1：离线量化工具候选

M1 已通过 PR #19 集成至 main `17b2c15`，下文保留 dev4 安装用法与历史候选位置。当前 M2-1 候选 `0.4.0.dev1` 的任务版本、风险配置、启停和结果对照见[新增使用说明](strategy-task-management.md)。新候选 ZIP 同样使用 `Start-Hakimi.cmd`；菜单 15 创建可管理任务，13 管理版本／启停，14 比较结果。正式 Release 仍为 v0.2.1。

本轮将现有能力整合为可安装的 `hakimi-trade` 入口。包名仍为 `hakimi-research`，候选版本为 `0.3.0.dev4`；不重命名代码库。双均线、买入持有和公告排期过滤复用原策略、`EquityExperimentRunner`、风险和记账实现，公告资料流程也进入安装包。旧固定 AMD／NVIDIA 任务、方案、预算及原件继续保留。

## 安装与第一次使用

Python 包支持 3.11 或以上；本轮 Windows x64 离线候选附带的 NumPy／pandas 依赖轮子使用 **CPython 3.14**，该候选应由 Python 3.14 安装。使用同一份受验收 wheel 和锁定依赖，普通安装到仓库外虚拟环境。不能用 editable 安装替代首次使用验收，也不借用仓库 `src` 或设置 `PYTHONPATH`。

候选 ZIP 解压到仓库外后，双击 `Start-Hakimi.cmd`。它复用原安装器，在候选目录旁建立独立环境，使用包内 wheelhouse 离线安装，核对本候选身份后打开菜单；不会下载依赖或改动其他安装。第一次选择 1 创建虚构示例，再选 2 检查、3 运行、4 看报告、5 重放或 6 恢复页面。

当前受验收候选为 0.3.0.dev4，本机下载目录 `Hakimi-M1-dev4-20261009-e10cbb02` 的“开始使用.cmd”启动。209 项安装后检查，以及默认／同盘外部／实际跨盘的菜单退出重开、查看、重放与历史恢复已通过；身份和范围见[最新修复与交付记录](research-evidence/offline-product-m1-p2-20261009/README.md)。旧 `Hakimi-M1-dev3-20261006-e0f27a10` 的 dev3 包、201 项检查和首用证据与更早 dev2 包保留原身份。新包实际首用由代理完成，不声称用户人工验收；NVIDIA 原报告的阅读反馈只支持该报告。

以下是使用单独 wheel／依赖目录时的手动安装方式，路径按候选目录的实际位置选择；无须源码：

```powershell
python -m venv .\runtime
.\runtime\Scripts\python.exe -m pip install --no-index --find-links .\wheelhouse --requirement .\requirements.research.lock
.\runtime\Scripts\python.exe -m pip install --no-deps .\hakimi_research-0.3.0.dev4-py3-none-any.whl
.\runtime\Scripts\hakimi-trade.exe wizard --workspace .\workspace
```

菜单 1 创建明确标注的虚构示例；2 选择任务并检查输入；3 运行；4 在终端直接查看完整结果，并打印保留的 HTML 文件路径；5 重放；6 从保存结果恢复页面；7 核对公告原件。菜单 11 可选请求浏览器打开 HTML，最多等待 5 秒；浏览器缺失、失败或超时不影响读取结果。菜单 8 仅在计算中断后显式恢复同一输入，需原进程已释放操作系统锁、原代码和依赖身份一致；保留原失败和新增尝试记录。已经保存结果时只重建页面，不重复计算。菜单 9 导入自己的 CSV／完整元数据，10 从已有数据与注册策略创建任务；不需要先运行虚构示例。上述流程不连接行情接口、账户或订单。

也可按命令操作：

```powershell
hakimi-trade capabilities
hakimi-trade strategies
hakimi-trade init --demo --workspace .\workspace
hakimi-trade check --task .\workspace\tasks\price.json
hakimi-trade run --task .\workspace\tasks\price.json
hakimi-trade run --task .\workspace\tasks\event.json
hakimi-trade report --run-dir <运行打印的目录>
hakimi-trade replay --run-dir <运行打印的目录>
hakimi-trade recover --run-dir <运行打印的目录>
hakimi-trade recover --resume-calculation --run-dir <已中断的新入口目录>
hakimi-trade source run --manifest .\workspace\data\source-manifest.json
```

需要空白工作区时使用 `hakimi-trade init --workspace .\workspace`。菜单会列出 tasks 目录里的实际配置，新创建任务可以直接选择。

报告直接展示策略与版本、评分数据范围、是否成交、事件阻挡及原因、费用、净收益／损益、已实现／未实现损益、期末持仓和输出位置。合成示例用于操作验收；收益数值不是市场结论。

## 导入自己的已有输入

通用美股日线使用原 CSV＋完整元数据合同：

```powershell
hakimi-trade snapshot-import --csv .\prices.csv --metadata .\metadata.json --output-dir .\data
hakimi-trade task-create --task .\tasks\price.json --strategy price.dual_ma@1 --snapshot <导入输出路径> --parameters .\parameters.json --score-start 2024-11-11 --score-end 2024-12-03
```

参数 JSON 只调整支持的规则参数；配置含策略键与版本、ENABLED／PAUSED、快照、评分区间、资金、成本和风险。新参数产生新任务身份。排期过滤使用 `event.earnings_schedule@1` 并显式提供 `--event-context <事件上下文>`；缺失、不可用或错证券的排期不会被当作空事件。首版固定支持美股正股日线，更多策略逻辑通过注册模块扩展，不复制运行或账本。

针对已存在的 NVIDIA 两窗口六请求采集器，**正常完成**的结果可以直接导入，不需要制造旧失败：

```powershell
hakimi-trade collection-import --collection <正常完成的采集目录> --calendar-original <原日历文件> --output-dir .\data
```

原有两次成功元数据后停止、再续接四次行情的合法恢复链仍可导入：

```powershell
hakimi-trade collection-import --first <原两次记录目录> --continuation <续接目录> --calendar-original <原日历文件> --output-dir .\data
hakimi-trade bundle-check --bundle <导入打印的 quote-bundle 目录>
```

导入器只读已有回复，不采集新数据。它验证固定请求、六次总量、原停止与续接身份、正常进程退出、证券、公司行为、完整日线／小时线及 OHLC，并保留成交量差异。缺失、损坏、额外请求、未清理进程、身份冲突或不支持公司行为均停止。先全部核对，再原子发布完整目录。只读复验或相同输入重复导入不覆盖冲突内容。

这项兼容导入只支持原两个固定 NVDA 窗口；其他受支持证券／范围经通用 CSV 元数据入口导入。`--synthetic` 仅用于额外带 SYNTHETIC_TEST 标签的虚构采集回执，不能把该输出当作真实市场资料。

## 目录迁移与恢复

报价 bundle 保存原件副本、内容摘要和相对路径。整体移动后直接 `bundle-check`，不依赖原电脑绝对路径。任务通常使用相对路径；整个 workspace 移动后 task_id、快照和原报告身份不变。不同盘符的外部绝对路径是显式位置，迁移时需更新输入位置；仅修改文件位置不改变规则身份。缺失文件会显示实际缺失的位置。

run 目录保留输入副本、任务语义、源代码／依赖身份、启动、原报告、失败、恢复尝试和重放回执。迁移后原报告不回写；只派生显示新位置的页面。页面写入中断使用 `recover`。计算未保存报告时不会自动重复；用户可显式 `--resume-calculation`，活动进程锁或身份改变会阻挡恢复。旧八次 NVIDIA 预算目录不是新应用任务，不能通过此入口恢复计算。

## 本轮验收与待批准事项

| 要求 | 当前证据／尚需完成 |
|---|---|
| A 项目定位、职责、版本及范围 | README、状态页、产品路线图；PR #18 最终候选与八次结果保持已完成 |
| B 正常导入、续接、迁移、冲突 | 同一 wheel 的完整流程检查覆盖正常首次导入、合法续接、移除旧路径后的迁移、损坏与冲突拒绝。实际保留续接输入导入后的两个 snapshot_id 与原件一致，新行情请求和市场收益运行均 0 |
| C 仓库外可安装正常使用 | 0.3.0.dev3 同一 wheel 在全新 Windows 仓库外普通安装，201 项检查及实际启动器首用通过；未使用 editable、开发数据、PYTHONPATH 或系统 site-packages。前一 0.3.0.dev2 证据保留 |
| 策略接入接口准备 | 版本化注册目录、配置与公开输入检查，已有价格与排期过滤共用原引擎；没有新的策略逻辑或寻优 |
| 首次使用与最终交付 | 0.3.0.dev4 同一新产物通过 209 项安装后检查，默认／同盘外部／实际跨盘菜单退出重开、结果读取、重放及历史恢复通过；构建源码九项 CI 成功，最终审阅 head checks 独立核对。新首用由代理完成，旧 dev3 产物与首用证据保留；NVIDIA 人工阅读验收保持原范围 |

M1 为离线候选，M2—M4 是后续路线图。多证券共享现金与组合风险、增量监控、账户和订单衔接尚未由本入口实现。有效杠杆 1；碎股、固定滑点、比例费用及声明无公司行为窗口继续可见。PR #18 已按单独授权进入主分支；M1／PR #19 的主分支合并、正式发布、部署和实际模拟订单各有独立授权范围，不以本轮安装检查开放权限。

## 2026-10-09 流程修复与安全重试

0.3.0.dev4 在准备输入前领取运行的操作系统锁；原运行、恢复及等待者使用同一互斥流程，锁内再次检查已有报告。输入与启动记录在暂存目录完整封存、核验后才发布为可恢复运行。初始化失败不启动计算，暂存原件留存，再次运行同一任务可重新准备；不会删除或覆盖残缺目录。

旧候选已经留下的残缺最终运行目录保持原样。无法证实完整初始化时不允许恢复计算；可用 `hakimi-trade run --task <原任务> --output-dir <新的输出目录>` 在明确新位置重新准备，不修改原任务规则或覆盖旧资料。已经保存结果的运行只读取／恢复页面；已启动计算后失败仍使用显式恢复。

最近运行记录在工作区内保存相对位置，外部结果保存明确绝对位置；旧相对记录仍可读取。菜单 12 查看运行历史，菜单 8 从内部及外部运行列表恢复；没有最近标记的失败运行也可从任务声明的输出目录发现。缺失、损坏及位置类型冲突会显示诊断，记录不删除。源码、旧 dev3 与新的安装验收身份见[本轮修复记录](research-evidence/offline-product-m1-p2-20261009/README.md)。
