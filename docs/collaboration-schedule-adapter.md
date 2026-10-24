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

两份候选均用当时**实际提取完成时间**作为 `OBSERVED available_at`，没有把历史公告时刻伪称为当时已收到；其来源认证仍为 `NOT_INDEPENDENTLY_VERIFIED`。初始评估均为 `MANUAL_CONFIRMATION_REQUIRED`；NDAQ 后经用户明确接纳，在 GUI 另存了确认记录，原待审版本保留，KO 未被接纳。原 NDAQ/KO 报价候选各含 2026-09-16 至 10-21 的 26 根完整美股 RTH 日线；NDAQ 原建任务操作因截止早于排期实际可用时间而被拒绝，不能改写为零干预运行。另以同一公开来源重新冻结截至 10 月 22 日的 27 根 NDAQ 完整日线，明确记录新来源对 10 月 21 日 high 与 volume 的修订；新任务已运行并导出反馈。公司行为完整性仍是来源支持的调用者声明，并非独立认证。所有原始行情、CSV 和快照留在仓库外证据目录，不作为源码提交；见[本轮闭环摘要](research-evidence/workbench-m32-20261022/ndaq-schedule-closeout-20261023.json)。

交易分析 [PR #31](https://github.com/TheDeadly-cat/hajimi-jiaoyifenxi/pull/31) 与 [PR #33](https://github.com/TheDeadly-cat/hajimi-jiaoyifenxi/pull/33) 是本轮前期核对的独立 Draft 候选，不当成主线部署或本次排期的来源认证。本任务复用已有资料文件导入入口，不迁移研究库、不调用 Provider 或启动新研究轮次。

## 量化结果回传：本地冻结 Markdown，再手动导入房间资料

`Workbench` 的 `export_research_result` 仅接受与人工接纳记录、任务版本和已验证原生运行严格绑定的结果。它在本地 `exports/research-return-<operation_id>/` 保留原报告、研究结果、排期上下文、输入评估、人工确认、原始来源、结果视图与任务绑定共八份原字节，并从已验证报告的 `saved_input_outcome(report)` 生成中文 `research-feedback-<文件字节SHA256>.md`。反馈写明研究结果/上下文/原来源/确认文件、证券及事件版本、任务版本、运行/报告/代码身份、评分与费用参数、阻挡新增买入次数和逐时点处置、理由与当时已知版本；同目录相对链接和 SHA-256 表可供回查。相同冻结输入重复导出得到相同反馈字节；原公告只作为排期输入来源，**不是量化反馈的发布 URL**。反馈标明 `research_only=true/order_allowed=false`，不改策略参数，也不证明输入带来收益优势。

研究侧已有房间资料“导入文件”入口，可由用户选中上述 Markdown 后本地导入，无须发布到互联网或新建协议；此入口接收原文件的 base64，保存提取文本、原字节 SHA/长度和资料版本，**不保存原始文件字节**。文件上限 2 MB、提取文本上限 50,000 字符；若研究侧标记 `truncated`，不能把房间资料当作完整反馈，须回到量化侧冻结原件核查。量化导出仅返回本地文件位置、哈希及 `LOCAL_EXPORT_ONLY_NOT_RECEIVED`，该状态本身不证明研究侧接收；本次 NDAQ 文件随后单独导入 `room_market` 的资料 v1，原字节 SHA、提取文本哈希与可读性已回查，未截断。导入资料不创建房间轮次、调用 Provider 或认证公告来源；本路径不再用 `source_import_packet_v1` 冒充反馈文件的公网来源。
