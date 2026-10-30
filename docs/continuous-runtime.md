# 美股日线连续研究运行（M3-2）

## 产品范围与正式内核

新普通任务及连续研究使用 `src/hakimi_research` 中的正式策略、风控、成交模型与共享账本。桌面封存包和原终端历史结果保留自身身份；不把旧账户改签为新账户、不回写旧结果。这里的“连续”是用户主动提供增量冻结数据后的可恢复逐会话推进，不代表后台盯盘、实时保护、模拟交易接通或券商执行。

首版支持美股正股、USD、常规时段完整日线，以及既有 `price.dual_ma@1`、`price.buy_and_hold@1` 和 `event.earnings_schedule@1`。价格、证券身份、交易日历和公司行为声明均沿用 `equity_dataset` 的严格入口；只有声明完整、无公司行为的窗口可进入。导入数据保持 `IMPORTED_UNVERIFIED`，不因程序接受而变为已验证市场事实。软件测试中虚构数据始终另标 `SYNTHETIC_TEST`。

## 使用顺序

1. 导入正式股票快照：原始 CSV、证券身份、逐日交易日历、来源内容与公司行为声明组成已有 `us-equity-daily-import-v1`，经 `build_equity_snapshot` 或已有导入流程生成完整 `equity_dataset_*.json`。
2. 创建已有正式任务或可管理任务族，选策略、评分起点、费用与风险。多个任务必须具有同一个评分起点、足够预热和共同证券时点。
3. 在新目录建立连续研究账户，明确共享本金和组合限制；任务的独立回测本金不会另加进共享现金。原合成账户不自动迁移。
4. 提供每个账户证券的新快照，选择推进至哪个交易日。新快照要从原预热起点覆盖到目标日，所有已经消费的价格、交易时点和日历必须原样保留。
5. 查看最后成功日、输入状态、每会话信号、资金拒绝原因、保护退出及研究依据。重新打开账户会检查整个回执链并恢复，不会重新发布历史操作。

截止日早于实际导入时间的运行是离线历史回放；“收盘＋申明延迟”不证明当时实际收到该数据。截止日超出日历覆盖、缺任一证券、修订已消费前缀或尚未可用时，状态为 `BLOCKED`，保留最后成功时点并明确该缺失区间的持仓保护不可计算。

## 暂停与损失停机

- 暂停停止新增 BUY；已有持仓的开盘及日内保护退出继续计算。既有买入持有基准按其原合同没有策略止损/止盈，页面应说明这一差异。
- 可管理任务族的暂停可由 `advance_continuous_account(..., task_files=[...])` 同步；账户内单任务控制使用 `set_continuous_task_state`。后一入口是该连续账户的控制，不改原任务族配置。账户人工暂停与任务族暂停分别保存在 `manual_task_paused` / `family_task_paused`，有效 `task_paused` 为两者及版本警告的并集；恢复任一层不会解除另一层。
- 全局暂停继续复用共享账户的 PAUSE/RESUME；损失停机跨会话与重启保留。`reset_continuous_loss` 要求当前回执头，以及停机日之后已经完成的会话，人工暂停不会被清除。
- 数据缺失时系统不生成虚构价格，也不声称后台持续保护。补齐未修改的完整数据后可继续；修订已使用数据需要新独立账户研究，旧判断和持仓历史不改写。
- 任务参数、策略或研究上下文冻结在账户建立时；改任务配置需另建账户，不将旧持仓暗中归给新规则。任务族当前版本已变或原任务状态缺失时，旧账户自动停止该归属新增、沿用冻结规则保护已有仓位，并显示 `task_configuration_warnings`。

## 会话顺序及恢复

同一 SQLite `BEGIN IMMEDIATE` 事务封存一次增量请求的完整输入、各会话结果、账户状态与回执。处理顺序固定为：所有期初持仓的开盘保护 → 按任务登记顺序处理前一可用收盘信号 → 日内保护 → 收盘估值。开盘保护触发后取消该任务旧信号；日线同根同时穿越止盈与止损时采用止损优先。新仓亦接受当根日内保护，买入持有按既有无保护基准语义处理。费用、滑点、持仓归属和全局准入复用正式风险/执行模型，不运行独立任务回测来拼接资金。

批量推进与相同输入逐个会话推进得到相同经济状态。回执数量因批次数量不同可以不同。重复操作 ID + 相同请求返回原回执；同 ID 改请求拒绝；新 ID 重复相同截止日只记录无新增会话，不重复记交易。提交前失败回滚；提交成功但响应丢失时，先用 `lookup_continuous_receipt` 查 `COMMITTED` / `NOT_RECORDED`，不要自动另换 ID 重发。

## 后端 API 与最小样例

以下参数仅演示软件流程，不是投资建议。`snapshot_path` 必须为已验证的正式 `EquitySnapshot` 文件，不能直接传终端 `frozen_input` 或只有 OHLC 的数组。

```python
from hakimi_research.equity_dataset import load_equity_snapshot
from hakimi_research.trade_cli import create_task
from hakimi_research.continuous_runtime import (
    create_continuous_account, advance_continuous_account,
    describe_continuous_account, lookup_continuous_receipt,
)

snapshot = load_equity_snapshot(snapshot_path)
task = create_task(
    workspace / 'tasks' / 'benchmark.json',
    strategy='price.buy_and_hold@1', snapshot=snapshot_path,
    score_start='2024-11-11', score_end='2024-12-03',
    params={'target_position_pct': 0.5}, fee_rate=0, slippage_pct=0,
)
limits = dict(max_total_position_pct=1, max_symbol_position_pct=1,
              min_cash_pct=0, max_daily_loss_pct=0.5, max_leverage=1)
create_continuous_account(account_dir, [task], initial_cash=10000, limits=limits)
receipt = advance_continuous_account(
    account_dir,
    {snapshot.document['security']['security_id']: snapshot.document},
    through='2024-12-03', observed_at='2024-12-04T00:00:00Z',
    operation_id='user-confirmed-first-advance',
)
view = describe_continuous_account(account_dir)
# 响应未知时：保留同一ID，先查询，不自动创建新ID。
lookup = lookup_continuous_receipt(account_dir, 'user-confirmed-first-advance')
```

`create_continuous_account(directory, task_files, *, initial_cash=10000, limits, start_session=None)` 返回普通状态视图。`advance_continuous_account(directory, snapshots, *, through, observed_at, operation_id, task_files=None)` 返回不可变事务回执。服务应提供当前观察时间，不接受伪装未来的客户端时间；用户可选择历史截止日。

状态视图保留原共享账户 `cash`、`equity`、`reserved_cash`、`available_cash`、`state.positions`、`history`、`receipt_head`、`execution_permission`，并增加：

| 字段 | 说明 |
|---|---|
| `continuous.status` | READY / CURRENT / PAUSED_NEW_ENTRIES / LOSS_HALTED / BLOCKED |
| `continuous.stop_reason` | 可直接映射用户停止原因；数据失败不会抹掉原成功时点 |
| `continuous.last_session` / `last_success_at` | 最后完成的交易日／收盘加延迟时点 |
| `continuous.last_observed_at` | 最后提交的观察时点；不伪装历史数据接收凭证 |
| `continuous.task_paused` | 持仓归属 → 是否停止新增 |
| `continuous.session_results` | 每日权益、现金、持仓、信号及资金判断/保护价格依据 |
| `receipt.outcome.processed_sessions` | 本次实际新增处理的日期；重复推进为空 |
| `receipt.outcome.sessions[].decisions[]` | owner、security_id、signal、signal_at、execution_at、basis、reference_price、decision、research_review |

`set_continuous_task_state(directory, owner, paused, *, operation_id)` 与 `reset_continuous_loss(directory, *, operation_id, expected_head)` 均生成独立回执。所有权限继续为 research_only；无订单、后台监控、盈利保证或市场数据真实性提升。


## 显式本地输入观察

`continuous_watch` 只观察用户明确配置的本地完整快照文件，不拉行情、不调用模型或券商、不重开 Unknown/T3。配置和第一次启动分别进行。主程序退出或进程重启后默认停止观察；有待核实提交时，先通过“核对原提交并恢复”处理原请求，核对完成后再明确“开始观察”。停止观察不修改任何账户暂停；账户暂停新增也不会停止观察已有仓位保护。

```python
from hakimi_research.continuous_watch import (
    configure_watch, start_watch, stop_watch, describe_watch,
)
configure_watch(watch_dir, account_dir,
    {security_id: incoming_snapshot_json_path},
    task_files=[managed_task_family_path],
    interval_seconds=5, max_data_age_seconds=345600)
start_watch(watch_dir)  # 仅用户显式启动时调用
status = describe_watch(watch_dir)
stop_watch(watch_dir)   # 服务退出前停止；返回 STOPPING 时等待在途本地事务完成
```

每个输入须连续两次读取具有相同大小、修改时刻与 SHA-256，读取前后文件状态也一致。观察器校验每证券正式快照，按最新共同完成日推进。每次轮询读取登记任务族状态并与账户人工暂停合并；任务路径缺失或不可核验时只保留旧规则减仓保护，不新增。只有完整、稳定且未超过明确配置年龄限制的文件才自动推进。年龄是从最后完整日线可用时刻计算的保守时长规则，不能把周末/长假或提供方延迟自动视作无风险；用户可查看原因并人工选择适当阈值。过期输入可在普通离线回放入口明确检查，观察器不自动将陈旧行情作为新的历史成交机会。

`describe_watch` 返回 `observation_state`（STOPPED/RUNNING/STOPPING）与数据 `status`，两者分开：WAITING_STABLE_INPUT、CURRENT、INPUT_MISSING、INPUT_STALE、INPUT_NOT_YET_AVAILABLE、INPUT_ERROR、INPUT_REJECTED、SUBMISSION_UNKNOWN、PENDING_REVIEW_REQUIRED。含 `reason`、`last_poll_at`、`last_success_at`、`latest_common_session`、`pending_operation_id`、`receipt_hash`、`account_status`。CURRENT 只表示已处理当前文件，不证明网络在线、市场输入真实、持续监控到交易所最新时点或账户未暂停。

观察器先保存完整请求及原始快照并建立 pending 指针，再进入共享账户事务。重启先查询同一 operation_id 的 durable 回执；COMMITTED 只确认原回执，NOT_RECORDED 只重发原请求和原 ID。若未提交请求期间任务族控制已经改变，则停止自动恢复，显示 PENDING_REVIEW_REQUIRED。显式 `discard_uncommitted_pending(watch_dir, expected_operation_id=..., reason=...)` 仅允许已查明 NOT_RECORDED 的请求；保留原请求和用户处置记录，禁止丢弃已提交结果。无法读取账本不等于未提交，不可自动换 ID。

### 中断后从界面核对原提交

在“连续观察”中选中原组合，观察停止且存在待核实请求时，可点击“核对原提交并恢复”。该动作只处理界面显示的原请求，不扫描新输入，不开始后台观察：

- 已有原回执：验证并读取原回执，不增加经济记账。
- 尚未提交且数据、任务控制及账本位置仍匹配：按原请求和原操作 ID 恢复一次。账本位置在写事务内再次检查。
- 输入已过期或控制/账本位置已变：保留请求并进入人工复核；只有确定尚未记账的请求才允许填写理由后放弃。
- 账本或请求仍无法确认：保留未知状态与原件。指针或请求损坏时没有可执行的恢复或放弃入口，须先核对记录。

`recover_watch_pending(watch_dir, expected_operation_id=...)` 是同一显式入口；运行中的观察器必须先停止。重开时依据持久 pending 指针显示 `pending_present` 与已校验的 `pending_operation_id`，因此进程在写完请求、尚未更新状态页时退出，也能看到待核对提示。通用工作台的其他未知操作继续保留原有锁定规则，不能借此入口重做无关任务。

新候选不会改写旧包或旧账户的代码身份。已有账户仍须用其原运行版本读取和续接，新的故障演练使用独立合成工作区。
