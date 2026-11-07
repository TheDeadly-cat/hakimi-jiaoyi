本批 W3 actual protobuf 门禁已完成：最终 run-r3-full 为 4/4 PASS，0 failure/error/skip；测试 360.336 秒，外层 383.330 秒。精确输入、阶段计时、各 worker 的原 UNKNOWN/成功状态及文件摘要见 FINAL-SUMMARY.json。四份本 agent 源码与最终 input-spec 逐字节相符，完整 1620 输入复核未变。

证明范围为“当前 W3 源码 + 只读 r7 私有解释器/已核验 SDK protobuf + 本测试自持 127.0.0.1 动态端口”，不是 r7 已包含此功能，也不是整包/生产 bootstrap 或真实交易准入。默认生产 PackageWorkerSpec/权限未启用，无 SDK 顶层导入、OpenD、DNS、外部地址、真实账户或模型请求。

最终四例均经过原 serve/supervisor、原 coordinator、真实 SQLite journal、原 scoped transport 与实际 TCP：
- 连续状态正例：2 路真实握手 + 4 项查询事实，随后测试显式创建独立虚构现金快照；原 2202 收到 ACKNOWLEDGED。两连接、7 请求/响应帧。关闭后用原 9 个 operation ID 全部只读恢复，0 新连接/发送；原数据库与请求注册文件字节不变。
- CLOSED 状态：2 连接、6 请求/响应帧。原状态响应仍保留，实际 journal 拒绝构造提交 bundle，没有订单 ACTION/CLAIM/2202。
- 观察过期：2 连接、6 请求/响应帧。显式注入 UTC 逻辑时间越过 bundle 原 query-window，而 permit 仍在 profile 的未来上界内；无提交 ACTION/CLAIM/2202。原 worker 终态 UNKNOWN/exit 1 被如实保留，测试 PASS 是阻断符合预期，不是把 worker UNKNOWN 改成成功。
- 提前乱序 INPUT：仅 runtime 已由可信测试装配绑定时发送后续 snapshot ID，不能让装配跳序编码/派发；2 握手帧，0 查询/现金/提交。原 worker UNKNOWN/exit 1 保留。

run-r1-positive 失败原件完整保留：READY 约 24.36 秒，两次实际 1001 已完成；一次批量构造四个真实查询请求并逐次执行 bindings.verify_current，耗时超过 15 秒测试消息等待。测试停止了 child，原回执 STOP_REQUESTED/EXIT_NOT_ZERO/RESULT_MISSING/UNKNOWN；没有查询、现金或订单。仅新测试装配改为每完成上一 ACTION 后固定绑定下一个查询，公开 bind_queries 批量 API 保持。没有关闭校验、延长观察窗口、增大生产时限或隐藏自动重试。run-r2-positive 单正例随后通过，仅是诊断，不累加为最终四例覆盖。

实际测试上界：worker wall 60 秒 / READY 30 秒 / 消息 15 秒 / 退出 10 秒 / peer 100 秒 / 外层 420 秒。普通 JSON 层为 worker 8 秒 / READY 与消息 4 秒 / 退出 3 秒 / peer 45 秒。产品 wire RPC 15 秒、清理 5 秒、原 ACTION query-window 30 秒均不变。最终成功 first worker 56.566 秒、恢复 23.170 秒；这些是当前受控测试装配计时，不是生产启动性能验收。

每个实际 case 的 case-root 保存原请求注册 bytes/permit 时间、原 SQLite 与私有原帧/报告，supervisor-root 保存原命令与 stdin/stdout/stderr/result，peer-record.json 保存真实 accept、收到和发出的帧。SHA256.json 是该 case 原件摘要。注册文件仅是受控测试预绑定资料；没有新业务账本。恢复的 submit_observation 从原 journal.read_submit_observation 读取，按原 permit 时间校验；无新握手、请求编码、查询、prepare 或重发。ACTION 成功持久化读回后才发生 factory/connect/send，报告 io_order 关联原 receipt ID。

握手 AES/key/IV 与自由 retMsg 只存在于私有原响应；typed handshake facts 仅白名单身份/状态，实际用例核对私密 marker 不进入 journal 投影。ACK 不是成交或费用终局。价格的源端新鲜性、币种、tick/数量规则、费用、账户权利及真实授权仍未知或未准入；现金完全是测试显式虚构快照。未 commit/push。
