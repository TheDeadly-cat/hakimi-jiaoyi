# Broker execution journal 服务交接（离线记录原语）

记录日期：2026-10-30。本文仅对当前父工作树源码及已有定向证据作只读核对；编写本文没有执行测试、SDK、网络、研究、服务器或原生应用，也没有修改源码、测试或旧证据。

## 当前身份

权威父目录：`C:\Users\Administrator\.codex\worktrees\insights-github-20261022\哈基米v2交易`。

| 文件 | SHA256 |
| --- | --- |
| `outputs/python_quant_bot/exchange_terminal/services/terminal_broker_execution_journal.py` | `cf41a3585d91b448dacd78cb23f68dd8029926fb1103eba0e4d323c527df8736` |
| `outputs/python_quant_bot/tests/test_terminal_broker_execution_journal.py`（当前共 30 个测试方法） | `191c65920ae1034253966f10894854844f83efe958abd44f9f0cbae10e4f421d` |

账本 schema：`hakimi-broker-execution-journal-v2`。依赖的 typed profile 为 `VerifiedWireProfile`，schema `hakimi-broker-wire-profile-v2`。本次服务与测试仍是源码交付；不能据此声称已进入候选包、已接真实工作进程或完成 T29/T30 外部执行验收。

## 实现定位和权限边界

`BrokerExecutionJournal` 是 **trusted coordinator 的持久记录原语**。调用方负责提供可信应用级目录、已独立核对的事实、typed profile 和短控制屏障。`authorization_id` 仅是被记录和比对的引用；本模块不验证、签发或创造用户授权。`evidence_id` 同样不证明券商来源真实性。

写入、重放回执响应与只读视图的 `permissions` 均为以下九项 `false`：`external_connection_allowed`、`query_allowed`、`submit_allowed`、`cancel_allowed`、`unlock_allowed`、`automatic_retry`、`automatic_resume`、`automatic_mode_fallback`、`user_authorization_granted`。`begin_action` 返回 `dispatch_authorization_granted=false`；`DISPATCH_INTENT` 表示本地记录了某次动作意图，**回执不是 dispatch permit，也不代表实际发送**。

当前没有 host 应用级 root factory、router、UI 或实际 worker 接线。没有凭据读取、SDK context、socket factory、账户查询、下单、撤单或自动恢复。本模块不解析真实协议帧、不验证 broker response 的来源和对应关系；这些不能通过传入布尔字段或本地记录回执来代替。

## 共享范围、存储和原请求

- 调用方注入的 `shared_root` 应是同一应用共享目录，不能来自 renderer 或工作区选择器。物理路径为 `shared_root/broker-execution-v2/<record_domain>/<account_scope_id>/journal.sqlite3`。
- `account_scope_id` 绑定 provider `FUTU`、精确 mode 和显式 account ID；工作区身份仅供审计，不划分资金。不同工作区或新 profile 不能再次 claim 同一原始 intent；终态、重开或本地未发送结果也不重置这项去重。
- `SYNTHETIC_TEST` 与 `EXTERNAL_RECORD` 使用不同物理命名空间。EXTERNAL_RECORD 拒绝合成研究 profile，也要求 `production_transport_available=true`；当前 test-only wire profile 不能进入该域。该检查没有建立外部执行能力。
- API 仅追加 `SNAPSHOT`、`CLAIM`、`ACTION`、`OUTCOME`、`LATE_OUTCOME`、`OBSERVATION`、`REJECTED_FEE_EVIDENCE` 事件。规范 JSON、事件摘要、前序摘要、序号、request hash、metadata/head 和重放得到的结果须一致。事件上限 1000，累计事件字节上限 16 MiB。本地摘要链不等于外部事实认证。
- SQLite 写事务串行化共享占用；CLAIM/ACTION 在写事务内取得调用方短 `control_barrier`，核对 profile 冻结的完整控制状态，之后再次取时间校验。stop 后 resume 即使重新允许准备，revision 改变也使旧 profile 失效。此处只依赖可信屏障接口，未实现宿主停止流程。
- 同 request ID、同 payload 返回原回执；异 payload 拒绝。提交后响应丢失可 `read(original_request_id)` 查原事实，不新建动作或重算。`read` 的缺失回执不证明外部动作未发生，不授权重试。`close()` 只关闭该实例使用入口。
- 构造及空库读取不建库。已存在库在 SQLite 打开前拒绝 WAL/header 模式、WAL/SHM/rollback 残留、reparse 路径及多硬链接别名；读取不修复存储。该边界针对新 journal，并未重用、迁移或打开任何旧 profile/业务库。

## 资金、持仓和快照对账

CLAIM 需要匹配的独立账户快照，冻结原 owner/security/order 和费用上限。BUY 预留剩余整股限价金额与尚未确定的费用；SELL 预留归属该 owner 的剩余股数及费用，不能借用其他 owner 持仓。累计成交按原订单的一份累计事实计算，不累加重复累计行。SELL 成交款不自动变成新的可用买入力，只有明确的新账户快照才能更新基线。

UNKNOWN 或未确认的发送继续保留全部未决占用；cancel ACK 不是终态取消，不释放剩余量。终态 CANCELLED 只释放剩余未成交数量；实际费用未知时仍保留费用上限的未确定部分。EXPLICIT_REJECTED 不默认费用为零，必须补独立 `rejected_fee_evidence`；只有证明从未尝试写入的 NOT_DISPATCHED 才能记录已知零费用。

快照字段包含 `evidence_id`、`query_started_at`、`observed_at`、`valid_until`、`covered_head`、`cash_available`、owner `positions`。`covered_head` 必须等于 `expected_head` 和当前事件头；查询起点不得早于账本已知最近账户事实，时间顺序及有限新鲜度必须成立。每个 snapshot evidence ID 仅使用一次；所有 claim 终态且费用确定后才允许 rebase。

有冲突时，新余额不能默默清空原因。调用方必须另外提交 `reconciliation`，精确列出其 `evidence_id`、当前 `reviewed_event_head`、全部 `reviewed_reasons` 和全部 `reviewed_observation_ids`，再提供独立的新现金/owner 数量事实。该接口不会自动把本地投影当外部证明。

迟到成交、终态后的经济变化、累计回退或终态冲突、超数量/费用、限价违约、资金低于占用或 owner 持仓低于预留，会保留相应事实/冲突记录并阻止新增风险。rebase 后收到旧订单的新经济事实，不把它直接加成新现金；需要再次显式核对。相同数量、金额和费用的旧 OPEN 观察不能把终态或最终费用退回未确定状态。

## 帧长度、晚到回执和订单身份

`begin_action` 必填并持久记录 `frame_bytes`：connect 为 0；RPC 大于 44 且不超过 profile 帧上限。RPC 同时绑定 `frame_sha256`，动作次数在整个 profile 的持久历史中计数，重开不重置预算。

`outcome` 区分本机已确认的 `sent_bytes` 与异常时可能写出的上界 `possible_sent_bytes`，并保留 `write_attempted`、`response_complete`。必须满足 `sent <= possible <= 原 frame_bytes`；改报原帧长度被拒绝。NOT_DISPATCHED 要求 sent/possible 都为 0 且从未 write；CONNECTED 没有 RPC 帧。ACK/reject 要求调用方提供与原完整帧相对应的完整响应事实，possible 等于原帧长度，但允许已确认 sent 小于 frame，避免在未知 write 后伪造本机成功发送字节数。

`late_outcome` 只追加与原 UNKNOWN、`previous_evidence_id` 和 `original_frame_sha256` 精确关联的 ACK/reject。原 UNKNOWN 事件与回执保留，动作历史保留两个阶段，不产生第二次 submit。已有回归明确覆盖 known sent=2、possible=64、frame=64 后晚到 ACK 仍保留 known 2。

实际 `orderIDEx` 是 opaque 原字符串。本版接受 1–128 个 ASCII 可打印且无空白字符，保留大小写和前导字符，不转 uint64、不从编号推导账户或所有权。ACK 得到的原 ID 被绑定到该 claim；后续 observe/cancel/fees 必须精确匹配，不能用广泛列表查找替代未知 ID。`US-ORDER-0001`、改号、大小写变化、数字抽取与空白的区别已在定向回归中核对。

## 已有证据及尚未验证的部分

以下文件均位于本文同目录，旧证据未覆盖：

| 证据 | 当时身份与实际执行范围 |
| --- | --- |
| `targeted-r1.json/.log`、`targeted-additional-r2.json/.log` | 早期服务 `2d49d45c…`：首批 25 项通过，随后新增 2 项通过。 |
| `targeted-frame-r3.json/.log` | 帧长度/possible-sent 服务 `0ef50515…`：新增 2 项通过，0.271 秒。 |
| `targeted-final29-r4.json/.log` | 服务 `0ef50515b43ee4ce507f2525bde38c6c3921cf31a01b4ca4eb4c0a8d51db92ec`：当时完整 29 项通过，4.499 秒；这是 opaque 修正前的源码。 |
| `targeted-opaque-r5.json/.log`、`test-handoff-r3.json` | 当前服务 `cf41a358…` / 当前测试 `191c6592…`：只运行新增 opaque ID 用例和已有账户/模式/订单错配用例，2 项通过，0.379 秒；源码运行前后哈希相同。 |

**当前文件有 30 个测试方法，但不能把上述分批证据称为当前源码“最终完整 30 项通过”。** 根代理将在后续统一门禁核对当前全部用例，本交接不提前作结论。

这些测试仅使用新 TEMP 合成资料；socket、DNS、子进程和 Futu import 被阻断，SQLite 连接仅允许各测试自己的 TEMP。两实例竞争使用真实 SQLite 事务，覆盖共享现金/owner 股数、跨工作区去重、控制与时效、未知占用、费用、晚到事实、明确对账、原请求恢复以及存储漂移。它们不证明真实账户、行情、成交或费用真实性，也不构成连接、发单、撤单、实盘权限、包内接线或真人使用验收。
