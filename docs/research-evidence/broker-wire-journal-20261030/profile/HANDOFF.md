# Pure wire profile v2 交接

仅新增授权两文件：services/terminal_broker_wire_profile.py 与 tests/test_terminal_broker_wire_profile.py。源码已冻结，精确 SHA 与5个依赖原件不变证明见 review-freeze-identity.json。未改 v1、loader、UI/router、门禁登记、冻结包；未提交推送。

API：

- prepare_wire_profile(*, base_plan, candidate_config, candidate_intent, research_resolution, runtime_identity, control, workspace_context, wire_bounds, now) → VerifiedWireProfile。
- validate_wire_profile(profile, *, **expected_profile_id**, base_plan, candidate_config, candidate_intent, research_resolution, runtime_identity, control, workspace_context, now) → VerifiedWireProfile。
- 两者均返回 frozen slots dataclass 内的私有工厂 bytes；as_dict 返回独立副本。expected_profile_id 对 typed/dict 一律必填，必须由可信存储/原请求/permit提供，不能取传入JSON的自报ID。合法预算重封会产生新ID，不能替换原保存profile。

顶层 schema/status/id/created_at/mode/sdk_environment/contract_id/workspace_context/base_plan_id；candidate_config/candidate_intent/runtime/order/research/research_eligibility/deduplication/control 按base同名原件复制；wire_bounds 独立显式；protocol_policy固定测试级；budget_readiness只诊断动作额度缺项，execution_ready始终false。9权限精确false，固定缺v2 adapter、跨工作区journal、独立授权。v1 adapter identity不能升级为v2支持。

WIRE_ACTIONS、PROTOCOL_LIMITS、PROTOCOL_POLICY为不可变公开mapping。所有actions完整显式，正上限可收窄0，quote/trade connect与各自init成对0/1；允许记录缺阶段但不能执行。范围内最多2连接+2握手+14普通RPC，心跳/订阅/push/解锁/重连/应用重试全0。client ID/version属于另一个sealed CodecSessionBinding，不取SysConfig/env。协议策略固定PROTOBUF0/version0/header44/PLAINTEXT_OFFLINE_CODEC_TEST/recv_notify=false/production_transport_available=false，未来实际传输不能把本测试策略解锁。

期限≤base期限、endpoint与base相同、费用上限≤base上限。max_frame≥45且≤64KiB、wire≤96KiB、全部输出≤128KiB、最终回执预留≥16KiB且wire+reserve≤output；wall≤180、connect/handshake/RPC≤15、cleanup≤5、观察≤50、证据年龄政策≤30；所有integer明确拒bool，金额为受限Decimal字符串。实际费用/价格步长保持null。未知源时间不补本机时钟，查询往返与市场来源时间明确区分。

跨工作区：workspace_context只作来源；base account_scope_id/intent_scope_id/owner_scope_id完全保留，新工作区不会分账或重置认领。当前只证明这些身份绑定，没有实现资金账本/占用/真实下单。order中的金额仍是base原件投影；新wire费用上限另在wire_bounds，不能把原件投影当实际费用。

验证：targeted-r2.log 24/24 PASS，0 skip，0.282秒；原API/合法显式0、预算缺项/bool/decimal/expiry/byte上限、精确pinned SDK、改原件/包/mode/control/source、SYNTHETIC不可升级、可信expected ID、native/core原来源、v1参数原字节不变均覆盖。测试复用旧测试文件中纯函数构造明确虚构sealed fixture，不运行其旧DB/研究用例。测试拦截open/socket.connect/subprocess，模块不导入SDK。测试框架自身可能建立独立TEMP目录；未访问旧业务库。

response-contract-r1.json 给transport/journal查看完整真实新pure函数输出形状。该文件的包/SDK声明和证券/研究全是明确合成夹具；声明pinned wheel摘要不等于实际安装真实性。实际包元数据仍需可信loader，实际v2adapter/协议兼容、跨工作区共享journal/授权/费用/价格规则/外部验收仍未完成。

本轮未运行完整门禁、GUI、SDK、网络或任何经济研究。正式门禁注册由root处理（新增test_terminal_broker_wire_profile.py，24个test方法）。
