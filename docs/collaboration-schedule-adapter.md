# 交易分析财报排期的离线接入边界

本接入只选择 `EARNINGS_SCHEDULE`。交易分析的 `collaboration_result_v1` 用作来源身份和哈希封套；量化侧继续使用现成的 `equity-event-context-v1`、`event.earnings_schedule@1`、输入检查和任务版本。研究报告中的观点、评分和建议不转换为排期事实或策略参数。

## 需要交付的三份冻结文件

1. 交易分析导出的完整 `collaboration_result_v1` JSON。适配器固定核它的 v1 schema SHA、UTF-8 规范哈希、结果 ID、固定无执行权限，以及项目来源和领域上下文的必要绑定。**这是有界身份检查，不等同于调用交易分析完整的 `verify_collaboration_result`。**
2. 原始 `equity-event-context-v1` JSON 字节。`domain_context.schema_version` 必须为该版本，`payload_sha256` 与文件字节 SHA-256 相同。上下文自身由量化的 `verify_event_context` 重验完整版本链、原文 base64/SHA、来源 URL、证券、公开和可用时点、排期精度、修订及取消状态。研究结果接口目前只传哈希，不传这份原始内容；缺文件即拒绝。
3. 用户在量化侧形成的 `quant-schedule-input-confirmation-v1` JSON：明确 `ACCEPT_FOR_INPUT_CHECK` 或 `REJECT`、理由、声明人和 UTC 时间，并绑定研究结果 SHA、上下文字节 SHA 与证券 ID。适配器**不生成此文件，也不验证声明人身份**；界面或人工流程应在展示全部来源和时点后生成。交易分析接口的 HTTP 成功、`independent_review` 或 `user_boundary` 均不替代这一步。

调用 `assess_schedule_import(result_raw, context_raw, confirmation_raw, expected_security_id=...)` 只得到带 `assessment_hash` 的本地评估。`READY_FOR_EXPLICIT_INPUT_CHECK` 表示可进入原有 `input_workflow.import_input` → `check_inputs` → 用户明确 `bind_inputs`；此时仍未绑定任务、改参数、回测或下单。拒绝回执保留具体原因。旧任务和旧运行保持原版本；绑定新上下文必须形成新任务版本。`CANCELLED`、`UNKNOWN` 和未知公开钟保留原貌，不能把缺数据解释为“没有财报”。来源及人工声明仍须核验，哈希不能认证发布者或历史时间。

## 时点与来源的实际限制

- `equity-event-v2` 只接受美股财报排期，保留 `DATE_ONLY`、`BEFORE_MARKET_OPEN`、`AFTER_MARKET_CLOSE` 或真正有来源的 `EXACT_TIME`。公开钟缺独立证据时填 `UNKNOWN`，其版本不具备点时准入；不可用今天的抓取时间或推测的午夜充当历史公开时间。历史重建的 `available_at_kind=ASSUMED` 仍需展示假设延迟。
- 每个事件需同一 `security_id`、稳定 `event_id`、连续 `version` 和 `prior_version_hash`；修订或撤回作为新版本保存。原始内容字节、官方 URL 和提取文字及其哈希要可回查。`SYNTHETIC_FIXTURE` 不进入真实研究。现有量化合同仅声明 `official_source_status=DECLARED_UNVERIFIED`，不会把官方网址当成认证完成。
- 研究侧当前投影把 `project_source` 和 `domain_context` 标为 `caller_supplied/hash_bound_only`，默认 `independent_review=not_run`、`user_boundary=pending`；其结果成功并非输入采用审批。适配器把两侧身份都留在回执里，遇到研究审查 `concern/blocked`、研究用户拒绝或量化用户拒绝即停止。

## 真实样例状态与后续采集

本地交易分析交付树及其 `output` 中未发现可直接配对的已冻结 `collaboration_result_v1` 与原始排期上下文；量化库的演示排期是 synthetic，旧 AMD/NVIDIA 研究摘要不能被当成本次新输入，也不重跑。另用研究项目**纯协议函数**生成两份有真实来源哈希的待审 `collaboration_result_v1`，没有创建房间、调用模型、写研究数据库或形成用户批准。

可供人工核对的新标的：

- Coca-Cola（`KO`）的[公司 IR 公告](https://investors.coca-colacompany.com/news-events/press-releases/detail/1173/the-coca-cola-company-announces-timing-of-third-quarter-2026-earnings-release)和[同站 PDF](https://investors.coca-colacompany.com/_assets/_02744905259cb8240758f5502f105697/cocacolacompany/news/2026-09-29_The_Coca_Cola_Company_Announces_Timing_of_Third_1173.pdf)写明 2026-10-27 美股开盘前公布。原 IR HTML 内有 `datetime="2026-09-29T10:00:00"` 和可见 `10:00 am EDT`，对应 `2026-09-29T14:00:00Z`。首次只读提取漏看该时间，原 `UNKNOWN` 候选原封保留；另存修正候选 `work/ko-earnings-schedule-attested-pending-20261022/`。
- Nasdaq（`NDAQ`）的[发行人公告](https://www.nasdaq.com/press-release/nasdaq-hold-third-quarter-2026-investor-conference-call-2026-10-01)显示 `Published Oct 1, 2026 4:05pm EDT`，对应 `2026-10-01T20:05:00Z`；[公司 IR PDF](https://ir.nasdaq.com/node/111071/pdf)与原发 [GlobeNewswire](https://www.globenewswire.com/news-release/2026/10/01/3373377/6948/en/nasdaq-to-hold-third-quarter-2026-investor-conference-call.html)核对公告内容。结果文件预计 2026-10-22 美东开盘前约 07:00 发布；“约”不能写成精确时刻，候选保留 `BEFORE_MARKET_OPEN`。发行人 HTML 原字节及待审合同文件在 `work/ndaq-earnings-schedule-pending-20261022/`。

两份候选均用当前**实际提取完成时间**作为 `OBSERVED available_at`，没有把历史公告时刻伪称为当时已收到；其来源认证仍为 `NOT_INDEPENDENTLY_VERIFIED`。适配器评估只剩 `MANUAL_CONFIRMATION_REQUIRED`，尚未被用户采用。短窗报价候选 `work/us-rth-two-stock-pending-20261022/` 各含 2026-09-16 至 10-21 的 26 根完整美股 RTH 日线、原始公开源响应、CSV 与可重验快照；公司行为完整性仍是来源支持的调用者声明，并非独立认证。所有原件仅留本地 `work/`，不作为源码提交。

交易分析 [PR #31](https://github.com/TheDeadly-cat/hajimi-jiaoyifenxi/pull/31) 与 [PR #33](https://github.com/TheDeadly-cat/hajimi-jiaoyifenxi/pull/33) 当前是独立 Draft 候选，不当成主线部署或本次排期的来源认证。研究库不在本任务中修改、迁移、调用 Provider 或启动新研究。

## 量化结果回传：冻结文件，再由研究侧现有收件箱读取

实际运行后，从**已验证的原生报告**及 `saved_input_outcome(report)` 生成不可变 UTF-8 JSON 文件；内容至少绑定研究 `result_sha256`、排期 `context_file_sha256/context_hash`、人工确认文件 SHA、证券与事件版本、任务版本、原生报告 SHA/运行 ID、评分窗口、各交易时点的 `BLOCK_NEW_BUY` 或无干预理由、已知版本哈希、来源/代码版本，以及 `research_only=true/order_allowed=false`。原报告与原上下文保持原字节，反馈只引用身份，不写回策略参数。文件名使用其字节 SHA，另保留人工可读摘要；重试同一内容只引用同一文件，不静默覆盖。

交付到交易分析时复用现有 `source_import_packet_v1` → 来源收件箱 → 用户手动附加到房间/轮次的流程，把已可访问的冻结反馈文件作为 `project_source_item_v1` 的来源，`content_sha256` 绑定文件字节并保留量化任务/报告身份于受限 `trading_v1` extension。研究侧收到后仍标 `external_unverified`，附加不触发新轮次或审批。此接口要求可用的公共格式来源 URL；**当前本地文件没有可供研究侧读取的发布地址，因此回传尚未完成**。若选择 `project_invocation`，其 v1 也只接收哈希和字节数，原始文件仍需单独、人工可审查地传递。不要为绕过这些限制新增第三套通用协议或自动调用研究 Provider。
