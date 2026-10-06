# 哈基米交易 M1：离线量化工具候选

本轮将现有能力整合为可安装的 `hakimi-trade` 入口。包名仍为 `hakimi-research`，候选版本为 `0.3.0.dev2`；不重命名代码库。双均线、买入持有和公告排期过滤复用原策略、`EquityExperimentRunner`、风险和记账实现，公告资料流程也进入安装包。旧固定 AMD／NVIDIA 任务、方案、预算及原件继续保留。

## 安装与第一次使用

Python 包支持 3.11 或以上；本轮 Windows x64 离线候选附带的 NumPy／pandas 依赖轮子使用 **CPython 3.14**，该候选应由 Python 3.14 安装。使用同一份受验收 wheel 和锁定依赖，普通安装到仓库外虚拟环境。不能用 editable 安装替代首次使用验收，也不借用仓库 `src` 或设置 `PYTHONPATH`。

候选 ZIP 解压到仓库外后，双击 `Start-Hakimi.cmd`。它复用原安装器，在候选目录旁建立独立环境，使用包内 wheelhouse 离线安装，核对本候选身份后打开菜单；不会下载依赖或改动其他安装。第一次选择 1 创建虚构示例，再选 2 检查、3 运行、4 看报告、5 重放或 6 恢复页面。

本机供首次使用的目录为下载文件夹中的 `Hakimi-M1-20261006-dbcdc803`，双击外层“开始使用.cmd”。其 ZIP 与受验收候选完全相同，内含同一 wheel 和五份锁定依赖。安装后检查、实际命令流程和结果页面已经核对；人工首次使用仍待反馈，不能以操作者的自动检查代替。完整身份和检查范围见[交付证据](research-evidence/offline-product-m1-20261006/README.md)。

以下是使用单独 wheel／依赖目录时的手动安装方式，路径按候选目录的实际位置选择；无须源码：

```powershell
python -m venv .\runtime
.\runtime\Scripts\python.exe -m pip install --no-index --find-links .\wheelhouse --requirement .\requirements.research.lock
.\runtime\Scripts\python.exe -m pip install --no-deps .\hakimi_research-0.3.0.dev2-py3-none-any.whl
.\runtime\Scripts\hakimi-trade.exe wizard --workspace .\workspace
```

菜单 1 创建明确标注的虚构示例；2 选择任务并检查输入；3 运行；4 查看结果；5 重放；6 从保存结果恢复页面；7 核对公告原件。菜单 8 仅在计算中断后显式恢复同一输入，需原进程已释放操作系统锁、原代码和依赖身份一致；保留原失败和新增尝试记录。已经保存结果时只重建页面，不重复计算。菜单 9 导入自己的 CSV／完整元数据，10 从已有数据与注册策略创建任务；不需要先运行虚构示例。上述流程不连接行情接口、账户或订单。

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
| C 仓库外可安装正常使用 | 同一 wheel 在全新 Windows 仓库外非 editable 环境安装；199 项安装后检查通过，两任务检查／运行／报告／重放和公告核对通过；独立候选安装器也完成第二个新环境安装及身份核对 |
| 策略接入接口准备 | 版本化注册目录、配置与公开输入检查，已有价格与排期过滤共用原引擎；没有新的策略逻辑或寻优 |
| 首次使用与最终交付 | 新候选命令闭环、结果页展开、零新增计算的页面恢复、显式中断恢复及迁移检查通过；源码修复提交九项 CI 成功。新增入口独立人工首次使用仍待反馈；最终文档提交检查以 PR #19 当前检查为准，原报告阅读验收不能替代 |

M1 为离线候选，M2—M4 是后续路线图。多证券共享现金与组合风险、增量监控、账户和订单衔接尚未由本入口实现。有效杠杆 1；碎股、固定滑点、比例费用及声明无公司行为窗口继续可见。主分支合并、发布、部署和实际模拟订单分别待授权，不以本轮安装检查开放权限。
