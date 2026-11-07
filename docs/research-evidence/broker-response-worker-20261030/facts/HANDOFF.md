# Pure response facts v2 交接

已冻结仅2个新增文件 services/terminal_broker_response_facts.py 与 tests/test_terminal_broker_response_facts.py。精确SHA在review-freeze-identity.json；未改codec、journal、v1、router、门禁登记；未提交/推送。

API：verify_response_facts(*, profile: VerifiedWireProfile, codec: SimulateCodec, action_receipt, expected_action_receipt_id, request_frame: bytes, response_frame: bytes, received_at: aware datetime) → VerifiedResponseFacts。私有工厂immutable bytes，as_dict为独立副本。expected_action_receipt_id必须来自可信journal读回/原请求，不是从传入dict自取。self-seal不是来源认证。

验证当前journal原ACTION精确schema/seal/原ID/request_hash/profile/action/operation/request身份/frameSHA+length/attempt/result以及原时间；用原codec的Request/Response类重新解码。对query/cancel/fee，还从同一原Request解码opaque orderID并与journal原broker_order_id对齐，不能把不同session的原ID混进来。这个Request投影临时复用codec私有_decode/_tree和_requests，因为当前codec只公开FrameInfo；将来若公开request projection可窄替换，禁止另建不受控registry。

支持7动作：trade_submit、trade_cancel、trade_observe、trade_accounts、trade_funds、trade_positions、trade_fees。其它协议明确unsupported。输出schema hakimi-broker-response-facts-v2；status只表示scope/presence：ACK_SCOPE_MATCHED、CANCEL_ACK_NOT_TERMINAL、READ_FACTS_MATCHED、INCOMPLETE_EVIDENCE、NOT_FOUND_UNCONFIRMED、API_ERROR_RESPONSE。API错误不称订单拒绝终态。

固定顶层：id/profile_id/base_plan_id/mode/action/protocol/serial/journal_receipt_id/request_id/intent_scope_id/account_scope_id/workspace_context；request_frame与response_frame各含sha256/bytes；received_at、received_after_profile_expiry；ret_type/presence/facts/derived/missing/diagnostics/needs_reconciliation；status_semantics=SCOPE_AND_PRESENCE_ONLY；test_only=true/source_authenticated=false/research_eligibility原值；journal_observation_ready=false/reservation_ready=false/received_at_is_source_update_time=false/economic_acceptance=NOT_INFERRED；9权限false。

- submit/cancel facts={broker_order_id, account_scope_matched, order_terminal_confirmed:false, fees_final:null}。opaque orderIDEx必须present且scope header匹配；取消只确认原ID，无终态/释放推断。
- order list只准原ID单行；空列表保持NOT_FOUND_UNCONFIRMED，重复/外来行拒绝，不选第一行。精确证券/方向/数量/限价/US/USD，缺字段仍missing。fillQty、fillAvgPrice原值单列；filled_notional恒null。若两者存在且无冲突，derived.fill_notional_estimate只标SOURCE_FILL_QTY_TIMES_SOURCE_FILL_AVG_PRICE、exact_notional=false。负数/超qty/均价越限保留源值并diagnostics+needs_reconciliation，不生成估算。已FILLED也不推fee finality。
- feeAmount显式0和缺失分开；协议未提供currency/finality，仍null，不从USD请求或订单状态补。
- account list支持多账户，只选目标ID并验证SIMULATE+US授权列表，duplicate拒绝，无默认首账户/currency/真实交易许可。
- funds保留cash/availableFunds/power/frozenCash，绝不互换，无自动可用资金认定。positions保留broker总仓、canSellQty及positionID，不分配owner；空列表不等于已证明零持仓。
- 收到晚于profile expiry的原响应仍可记录观察事实，绝不恢复发送许可。received_at不替代市场/source update time。

READ_FACTS_MATCHED仅表示身份范围匹配，可能同时含missing、诊断或未知经济字段；不能直接调用journal.observe/snapshot。root新增typed record_verified_response负责完整事实记录，仅精确ACK按其合同转换，其他情况保持UNKNOWN/read-only。

来源：锁定wheel SHA a3bc7609fc7b60c0ca3cd2971bc8b81819338d3c88ad25d1bd3f647d781554b5。仅通过ZipFile+ast.literal_eval+标准库wire descriptor解析静态核对真实pb2字段/标签/枚举，无SDK import。TradeHeader=env0/US2；USD2；opaqueIDEx、fillQty/fillAvgPrice、OrderStatus映射及OrderFee缺currency/finality都据原字段，不凭记忆。Order.orderAmount没有被宣称为精确累计成交额。

验证：targeted-r2.log 27/27 PASS、0 skip，0.463秒。真实生产codec类+明确JSON protobuf-shaped fake classes，原ACTION为明确sealed synthetic fixture，没有创建journal DB。输入原件bytes不变；所有IO接触（open/socket/sqlite/Popen）在测试中被禁止。response-contract-r1.json给出7动作pure输出，仅为合成合同形状，不能宣称真实SDK/券商事实。真实pb2兼容由独立私有运行时probe后续另验；本轮未执行。

未跑全门禁、GUI、研究、SDK、网络或旧DB；根任务负责测试登记（27方法）与集成风险审阅。
