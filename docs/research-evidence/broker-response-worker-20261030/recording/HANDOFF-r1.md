# Response facts 原子记录与 worker 交接

本说明只汇总既有证据和当前冻结源码，没有执行测试、探针、SDK、数据库、服务器或原生应用；没有修改仓库。当前新增 recording 文件共 **18 项**，已由 root 随后完成的统一门禁完整覆盖：**709/709 PASS，0 skip/error/failure**，unittest 198.791 秒、外层 202.229 秒；15 项包装和 4 项 runner 同时通过，2095 输入前后完全一致。本说明只读取完成回执，没有轮询会话或重复检查。

## 已有测试的准确范围

| 原件 | 实际执行范围 |
| --- | --- |
| `targeted-r1-console-note.json` | 最早 12 项中 1 个夹具时钟断言失败：NOW+5 分钟尚未超过 profile 有效期；后来改用精确 expiry+1 秒。这里只存控制台摘要，不是逐字原日志，不补造失败输出。 |
| `targeted-r2.log` | 当时完整 42 项 PASS / 6.871 秒：旧 journal 30 项 + 当时 recording 12 项。不是当前 recording 18 项完整通过。 |
| `targeted-r3.log` | 当时 recording 15 项 PASS / 1.720 秒，包含原请求/时间、诊断与冲突范围。 |
| `review-regressions-r4.log` | 审阅后新增的 3 个回归 PASS / 0.480 秒：合法迟到 fill 在 terminal+rebase 后阻断新风险；最终费用变化；超限平均价不变成精确 notional。只执行这 3 项，未重复完整 18 项。 |

上述用例使用新 TEMP 合成账本和 protobuf-shaped 字段夹具，不是实际 SDK 或真实券商来源证明。独立真实 protobuf 探针的 55 检查另见 `../broker-response-facts-20261030/private-protobuf-r1/PROBE-HANDOFF-r1.md`，不得与上述测试数相加作完整套件数量。worker 当前 22 项也按其 19、3、清理修正后 1 项分阶段证据交付；最终 response facts 27、recording 18、worker 22 现已由同一次 709 完整门禁覆盖；分阶段原件仍保留当时范围。

## 原子记录合同

`record_verified_response` 只接受 `VerifiedResponseFacts`，在同一 journal 事务中保存 `VERIFIED_RESPONSE` 原事实与可匹配的 submit/cancel ACK。它核对本 journal 的原 ACTION 回执 ID、operation/request ID、profile、账户/模式/原 intent/workspace、原 frame hash/长度及取得时间。ACTION 的旧 payload/result 字节未改变；回放时才从已验证 event 推导 receipt_id/recorded_at。

API error、缺订单 ID 或缺必要证据保留 UNKNOWN，不转成明确拒单或零手续费。读取 funds/position/order/fee 的结果只归档原事实，不替换现金、owner 持仓、精确累计 notional 或最终费用。cancel ACK 不代表终态撤单，也不释放余量。响应本身没有 dispatch 权限，`economic_acceptance=NOT_INFERRED` 和九项 false 权限保持。

迟到 ACK 必须指明原 UNKNOWN 的 evidence ID，并绑定同一原 frame；追加原结果历史，保留原 UNKNOWN 回执及本机已知 sent bytes，不发送第二次 ACTION。重复同 request/payload 只读返回原回执；丢失本地 commit ACK 用原 request 查回，不重算或重发。

新的跨记录对照保留原经济值：内部合法的迟到 fill 也可能与已终态/已 rebase 的累计事实冲突；累计回退、terminal/旧 epoch 后数量变化、迟到均价待核对、超限均价、最终费用变化或费用累计回退均列为需核对并阻断新 risk。`qty × avg` 仅为来源描述性估算，不能直接记为精确成交额。显式后续对账仍需独立来源，不从本地投影制造真实性。

## 冻结源码与边界

[七文件身份回执](source-review-final-r1.json)保存读取前后一致的 SHA256；它是当前未提交源码字节快照，不是假定的新 CLEAN 候选包。

| 文件 | SHA256 |
| --- | --- |
| `outputs/python_quant_bot/exchange_terminal/services/terminal_broker_execution_journal.py` | `e2a3dc56cd4fa810d9b45e92c092a974ea2437b68d2df48db78c72041243d172` |
| `outputs/python_quant_bot/exchange_terminal/services/terminal_broker_response_facts.py` | `010f5c3fc3e0cc1fe3674591dfcdb3d3ae29d7f12398811c1b997ffb473f1414` |
| `outputs/python_quant_bot/exchange_terminal/services/terminal_broker_worker_supervisor.py` | `a0171cad253111d0ff857be935140377e0083376bcbd1084203c7e0c62475837` |
| `outputs/python_quant_bot/tests/test_terminal_broker_response_facts.py` | `efc905ca4429aa5d70c1d7924635498f6375e1b7e00dc82693b447f3c72a578f` |
| `outputs/python_quant_bot/tests/test_terminal_broker_response_recording.py` | `1725b39c62e4b88641420fc1addc793f67235894d1544d92980382315586bbfc` |
| `outputs/python_quant_bot/tests/test_terminal_broker_worker_supervisor.py` | `4e343bef18d41a8d3f6270491a296116a8adb520c38ec59a80a315b671636a8b` |
| `tools/run_terminal_contracts.py` | `25e9b130797d2dbc74ea1d30435dfb4ea50f9cdd9246e516c81f9bbcb4803808` |

最终门禁原件：`../broker-response-worker-integrated-20261030-r1/summary.json`（SHA256 `a32ea728a7d5b244d3c8f96c120a6d8785dc2854eacad8e6ea2f8ded163ad2af`）；7 文件当前 SHA 与该门禁的 before/after 输入清单逐项一致。

当前可用包仍为 `a235e8a2 / 0.7.0.dev3 candidate-r4`；这批 response service/journal 分支/worker 尚未打入新候选。没有 host/UI 真实执行入口、生产 gate、实际 worker 配置准入、加密或 REAL 适配。Package spec launch 明确不可用，测试 spec 不升格生产。所有原证据、旧 UNKNOWN/T3、历史研究和正在使用的旧 QA 保持原状；本文不提交或推送。
