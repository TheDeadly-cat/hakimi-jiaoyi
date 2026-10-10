# 策略任务与结果对照

候选 `0.4.0.dev6` 在同一 `hakimi-trade` 入口中管理配置、历史版本及行情／研究输入。菜单 16 提供选择、导入、只读检查和版本绑定，见[输入流程](input-workflow.md)。菜单 15 创建可管理任务，13 管理版本与启停，2 检查，3 运行，14 比较保存结果；旧格式任务先复制后管理。原三个注册策略保持原身份，新增的两个内容适配入口复用既有价格确认／字段条件和同一引擎。

Windows x64 离线候选需 CPython 3.14。将 ZIP 解压到独立目录，双击 `Start-Hakimi.cmd`：安装器只用包内 wheel 和五个锁定依赖，在候选旁创建独立环境，检查身份后打开菜单。无须源码或浏览器；不连接行情、账户或订单。首次可选菜单 1 创建虚构数据，再从 15 配置任务；已有数据可用 9 导入。

使用独立 wheel 时，普通安装至新的仓库外环境，再打开入口：

```powershell
py -3.14 -m venv .\runtime
.\runtime\Scripts\python.exe -m pip install --no-index --find-links .\wheelhouse --requirement .\requirements.research.lock
.\runtime\Scripts\python.exe -m pip install --no-deps .\research\hakimi_research-0.4.0.dev6-py3-none-any.whl
.\runtime\Scripts\hakimi-trade.exe wizard --workspace .\workspace
```

创建或修改时逐项填写策略参数、美元本金、手续费、固定滑点、评分首尾交易日、仓位、现金比例和风险约束。留空沿用提示中的值；修改版本保留原评分区间，即使新预热要求不足也明确停止，不能自动推迟开始日期。新任务未填评分日期时，首次根据数据与预热选定并显示，此后固定；跨策略默认日期可能不同，比较会报告不可比。

新建模板明确采用 6% 止盈；已有双均线／公告过滤配置若省略止盈字段，沿用原策略版本的 8% 默认值。复制、留空编辑和仅改本金均保留该省略语义，查看会显示“策略默认 / 0.08”；显式输入才改写该项。原报告保持原字节，不用新建模板替换旧规则。

保存及任务检查直接使用现有信号模型和风险快照的数值域，不先运行回测。止损／止盈为 `(0, 1]`；仓位比例为 `[0, 1]`，买入持有分配为 `(0, 1]`；最大仓位、最大止损距离、日亏损阈值为 `(0, 1]`，现金比例为 `[0, 1]`，杠杆固定 1。零保护值、负数、越界、非有限数字和错误类型明确拒绝，旧版本选择和状态不变；0 不解释为关闭保护。合法边界仍需满足仓位、现金储备和止损上限之间的既有约束。

双均线与公告排期过滤支持快慢周期、每次目标仓位、止损／止盈价格距离、最大仓位、最大止损距离、UTC 日亏损后暂停新 BUY 的阈值、最低现金比例。目标仓位超过最大仓位或现金储备、止损距离超过风险上限、不支持的字段、非有限数字和杠杆不为 1 都拒绝。止损距离不是账户损失保证；跳空可扩大损失。日亏损阈值不强制平仓。实际成交数量仍受现金、手续费和成交约束，可低于目标，报告中的账本为准。

买入持有只配置目标分配比例，使用既有全现金基准政策：一次首次开盘入场、无策略止损／止盈、不加仓、不重新入场，期末按市值。旧规范的单笔／日亏损字段显示为固定兼容值，生效值为未应用；自定义这些主动保护字段会拒绝。参数、请求值、生效值与退出政策在检查和任务查看时可读。不同策略的仓位与退出政策在对照中同时展示。

每次保存产生不可变版本，复制保存快照和事件上下文原字节；启停及版本选择另记追加式状态。仅当前已提交且启用的版本能运行；直接执行未选择的旧文件、未提交版本或暂停任务也拒绝。持有任务锁期间不能修改状态或配置。写入失败保留准备目录／未提交版本，旧已提交选择不变；不会自动激活或自动重试。旧报告继续绑定运行时版本和输入，不随新配置或状态改变。

启停控制任务入口的新运行；已封存运行的查看、重放及显式中断恢复使用原运行规则，不读取后来修改的任务。恢复仍需原进程释放运行锁、同一代码／依赖，原失败保留；已保存结果只重建页面，新增计算为零。

版本中的输入使用相对路径，默认结果放在工作区 `runs`。退出后重开菜单仍可查看版本、状态和运行历史。迁移整个工作区可以保持身份；外部输入在版本创建时复制封存。旧格式任务仍支持显式外部输出，外部结果不随工作区自动搬迁。不要只复制任务目录而遗漏整个工作区中的报告。

菜单 14 核对完整快照身份、证券／价格口径／会话时钟、评分首尾、本金、手续费、滑点、期末与股数模型、用途及代码／依赖身份。不同预热要求可以共用明确评分区间，不改变区间。条件相同才计算与第一行的净收益、回撤、手续费、成交数及过滤数量差；不一致时列明不同字段，不计算跨行差值。每行展示净收益、权益曲线峰值回撤、手续费、成交、BUY 与过滤数量、信号原因和保护／退出差异；滑点进入成交价格，不列为独立手续费。结果读取已保存报告，不重复运行。

每个任务使用独立本金，结果不能相加为共享资金组合。条件可比仅支持描述性阅读，不证明策略优越。虚构示例显示 `SYNTHETIC_TEST`。美股常规时段日线、无公司行为窗口、碎股和固定成本模型保持原范围；没有新增市场研究、账户或订单动作。

命令行也无需源码：

```powershell
hakimi-trade task-copy --from-task .\workspace\tasks\price.json --task .\workspace\tasks\my-strategy
hakimi-trade task-show --task .\workspace\tasks\my-strategy
hakimi-trade task-revise --task .\workspace\tasks\my-strategy --initial-cash 12000
hakimi-trade task-state --task .\workspace\tasks\my-strategy --state PAUSED
hakimi-trade task-select --task .\workspace\tasks\my-strategy --version 1
hakimi-trade task-state --task .\workspace\tasks\my-strategy --state ENABLED
hakimi-trade run --task .\workspace\tasks\my-strategy
hakimi-trade compare --run-dir <保存运行1> --run-dir <保存运行2> --output .\comparison.json
```

`task-create --managed` 创建新家族，`task-copy` 复制已有配置，`task-revise` 保存新版本，`tasks` 列出工作区任务。`--parameters` 和 `--risk` 可接受自己填写的完整配置 JSON；参数变更需明确提供受支持的整组配置，未知字段不会忽略。复制与修改版本切换策略采用相同规则：未提供 `--parameters`／`--risk` 时使用目标策略的新建模板，不跨策略继承原参数结构或风控。提供文件时使用目标的完整配置并验证，不丢弃不兼容字段；菜单会提示并允许逐项修改。共同快照、本金、费用及评分区间保留，目标预热不满足时拒绝，不自动推迟评分。

事件策略切换为价格策略只清除继承的事件输入；显式传入事件路径仍按防混用规则拒绝。反向切换仍必须提供合法 `--event-context`，不能复用先前版本的隐含输入。同策略内修改保留未改字段、必要事件输入和旧默认语义。修改失败不提交新版本，不改变原选择或暂停状态；成功修改也保留原启停状态，旧版本、输入和报告不覆盖。

```powershell
hakimi-trade task-revise --task .\workspace\tasks\my-strategy --strategy price.dual_ma@1 --parameters .\dual-ma-parameters.json --risk .\active-risk.json
hakimi-trade task-revise --task .\workspace\tasks\my-strategy --strategy price.buy_and_hold@1 --parameters .\benchmark-parameters.json --risk .\benchmark-risk.json
```

R3 存档 `0.4.0.dev4` 已通过 PR #21 合入 main，M2-1 与 R1／R2／R3 均结案。原 dev4／dev3／dev2 的包、构建与安装回执保持原身份。原 M2-2 `0.4.0.dev5` 的同一 wheel 已通过仓库外 253 项及实际输入流程；原候选首用与 CI 单独记录于 [PR #22](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/22)，不复用旧候选的通过结论。

2026-10-10：PR #22 已经用户对 `0059359` 单独核准合入 main `57b6bd4`，实际 main 九项 CI 与 Windows／Ubuntu 各 253 项通过。原 dev5 产物保留，后续两项 P2 在新候选修复：菜单 10 同样使用共享配置表单，支持五种注册策略；保存报告的成交约束和唯一内容入场机会在查看、恢复和比较前验证，不重算。新候选同一 wheel 262 项、实际菜单／边界和交付启动器已通过，合并待单独核准，见[修复记录](research-evidence/content-report-p2-20261010/README.md)。
