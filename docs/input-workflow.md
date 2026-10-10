# 行情与研究输入（M2-2）

候选 `0.4.0.dev5` 使用同一 `hakimi-trade` 入口，CLEAN 构建 `51b0f17` 的同一 wheel 已通过仓库外 253 项安装后测试和实际冷进程输入流程。候选 ZIP 内的 `research/wheel-acceptance.json`、`research/test-scope.json` 与 `research/installed-input-workflow.json` 保留确切验收范围；[PR #22](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/22) 记录本轮交付。M1、M2-1 和 R1／R2／R3 已结案；PR #22 已集成到 main `57b6bd4`；后续新候选 `0.4.0.dev6` 修复两项 P2，安装与集成待验收。安装、首用与对应提交的 CI 分别记录，不用旧 dev4 的安装记录代替新候选验收。

Windows x64 ZIP 使用 CPython 3.14。解压到新的仓库外目录，双击 `Start-Hakimi.cmd`；依赖只从包内 wheelhouse 安装。也可在新环境普通安装 `research/hakimi_research-0.4.0.dev6-py3-none-any.whl` 后执行 `hakimi-trade wizard --workspace .\workspace`。

## 正常使用

主菜单 **16 行情与研究输入中心** 提供以下流程：

1. 查看输入：显示证券、来源、覆盖窗口、价格口径、内容与文件身份，以及每个研究版本的公开／可用时点。
2. 导入：自有行情 CSV＋原完整元数据、既有快照／上下文，或既有排期事件版本。财报输入导入既有字段候选包、规范文本、原件及可选的字段核准回执。
3. 检查适用性：选择行情和策略，配置评分、成本与风险。研究输入可以选择 `#编号`，不需要记住封存文件路径。检查不运行回测、不保存任务。
4. 创建绑定任务，或选择已有任务更新输入。更新前检查适用性，输入 `SAVE` 才提交新版本；原版本、报告和暂停状态保留。
5. 返回主菜单，用 2 检查、3 运行、4 查看结果、14 比较保存结果。退出后重开仍能看到输入、任务版本与结果。

主菜单 9 的 CSV 导入和 15 的任务创建也使用同一输入处理。旧格式任务继续可读；先在 13 复制为可管理任务，再更新输入。每个任务使用独立本金。

## 当前接入的规则

| 策略键 | 研究输入与作用 |
|---|---|
| `price.dual_ma@1`、`price.buy_and_hold@1` | 原价格策略。研究输入不适用，显式混入时拒绝 |
| `event.earnings_schedule@1` | 原 `equity-event-context-v1` 排期上下文。决策及执行时使用当时可用版本，公告日／已知未知排期只取消新 BUY |
| `content.price_confirmation@1` | 既有 C 价格确认：固定第一完整公告后交易日收盘高于公告前收盘，最早随后交易日开盘尝试一次入场 |
| `content.reviewed_outlook@1` | 同一价格确认＋既有 D 内容条件：已核准的下季营收指引中点高于当前季营收。未核准、缺失或不适用的字段保持 UNKNOWN/HOLD |

内容规则是上述明确的“下季指引／当前营收”条件，不是分析师预期，也不替换旧 NVIDIA“当季实际／已列前次指引”研究协议。已有公司研究、原方案与预算不通过新任务入口重跑。

内容任务沿用现有 120 秒信息延迟、60 秒完整日线延迟和一次确认机会；这些是模型假设。拒绝或保护性退出后不重试、不重新入场。仓位、止损、止盈、风险、成本和评分日期通过正常配置填写，成交、风控和账本仍由同一引擎计算。

缺少行情、证券不匹配、评分不在快照内、预热不足、没有可用排期、缺少公告前价格基准、原件缺失或损坏，会明确停止准入。公开时点未知不会自动补成日期结束时间。历史固定窗口不按今天日期误判为实时过期数据；未来内容版本不能替代更早的已知版本。

报告分别显示价格条件、内容决定、所用版本、字段核准与可用时点，以及过滤或无干预原因。评分窗口外的机会会标为不适用，不算内容干预。未发生干预时，原有价格结果保持原计算语义。

## 输入格式与封存

行情继续使用 `us-equity-daily-import-v1` 和 `us-equity-daily-snapshot-v1`。范围仍为美股正股、美元、常规时段日线、身份稳定且声明无公司行为的窗口；拆股和分红记账未实现，相关输入继续拒绝。原 CSV、元数据和来源摘要保留，不另造行情格式。

排期上下文复用既有事件版本与完整版本链。财报任务的 `equity-content-context-v1` 是一个绑定封套：保留原字段候选包及核准回执的原字节，绑定规范文本和原件，复用已有字段／时点验证与内容条件。它不提取新的财报字段，也不自动生成核准。

输入保存在工作区 `data` 下，按内容与文件摘要命名；相同输入重复导入不覆盖冲突内容。任务版本再复制封存行情与研究上下文。旧运行只读取运行时的输入副本；后来换文件、核准字段或更新任务不会回写旧结果。

来源声明、文件身份和人工语义核准分别显示。保留原件和核准回执不等于来源已认证或历史实时可用。虚构示例明确标为 `SYNTHETIC_TEST`，财报示例默认没有字段核准，内容策略因此 HOLD。

## 命令行

```powershell
hakimi-trade init --workspace .\workspace
hakimi-trade input-import --workspace .\workspace --csv .\prices.csv --metadata .\metadata.json
hakimi-trade input-import --workspace .\workspace --file .\event-context.json
hakimi-trade inputs --workspace .\workspace
hakimi-trade input-show --file <封存输入路径>
hakimi-trade input-check --strategy event.earnings_schedule@1 --snapshot <行情路径> --event-context <排期路径> --parameters .\parameters.json
hakimi-trade task-create --managed --task .\workspace\tasks\my-task --strategy event.earnings_schedule@1 --snapshot <行情路径> --event-context <排期路径> --parameters .\parameters.json
hakimi-trade task-bind --task .\workspace\tasks\my-task --event-context <新排期路径>
hakimi-trade run --task .\workspace\tasks\my-task
hakimi-trade report --run-dir <运行目录>
hakimi-trade compare --run-dir <旧运行目录> --run-dir <新运行目录>
```

将既有事件版本组成排期上下文：`input-import --workspace <工作区> --event <v1.json> --event <v2.json>`。不完整版本链明确拒绝。

将既有财报候选导入：

```powershell
hakimi-trade content-import --workspace .\workspace --packet .\candidates.json --event-id <事件ID> --texts-dir .\normalized --originals-dir .\originals --approval .\field-review.json
```

`--approval` 可省略；内容策略保持未核准状态。`--synthetic` 只用于全为虚构测试的输入。程序按候选包中原有摘要匹配 `.txt` 规范文本和 `.html/.htm/.txt` 原件，不猜测财报数字或自动联网。

对照内容干预时，使用同一行情、评分区间、参数、风险、本金与成本的 `content.price_confirmation@1` 和 `content.reviewed_outlook@1`。不同价格策略、退出或风控的差异同时展示，不能把它们都归因于内容条件。更新行情身份后，结果会明确列出不可比字段，不计算跨行差值。

## 迁移与重放

保存整个工作区，包括 `data`、`tasks` 和 `runs`。在同一候选环境打开新位置即可查看封存版本和原报告，使用 `replay --run-dir <迁移后目录>` 重放；页面恢复不新增计算。报告原字节保留，只派生显示新位置的页面。

升级不自动替旧报告改签。跨代码版本重放需原代码／依赖环境；本轮整目录迁移验收使用同一候选。账户、订单、共享资金及增量监控不属于这个输入流程。

## 报告校验与旧格式创建修复

新候选 `0.4.0.dev6` 在读取内容报告时检查成交证券、评分内交易日开盘、支持的成交依据和信号时点，并将 BUY 绑定到计划中唯一获准的入场；被过滤入场、错误机会及重复入场明确拒绝。查看、恢复和比较不重新运行回测。合法零仓位／风控拒绝、内容 HOLD、保护性退出与期末持仓仍可读取；原报告不改签。菜单 10 复用正常配置表单，按五种策略各自的注册参数创建旧格式任务；不兼容参数仍提前拒绝。见[本轮修复与验收范围](research-evidence/content-report-p2-20261010/README.md)。
