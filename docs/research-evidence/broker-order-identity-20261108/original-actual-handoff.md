本批 W4 最终 actual protobuf 门禁为 run-r3-final：4/4 PASS，0 failure/error/skip。原 unittest 日志 428.903s，runner 包装计时 428.905s，controller 含末尾完整身份复核 433.254s，外层 452.526s。不同计时边界分列于 FINAL-SUMMARY.json，不混称同一时长。

验证使用 W4 当前源码与只读 r7 私有 Python/已核验 12 协议 protobuf，以自持 127.0.0.1 动态端口运行原 serve/supervisor/coordinator/SQLite/transport。没有 OpenD、SDK 顶层导入、外部网络、真实账户或模型调用；不代表 r7 已包含 W4 功能、生产 bootstrap 通过或真实交易获准。默认权限和生产 PackageWorkerSpec 仍保持原限制。

最终四例：
- 原 codec 从 broker_order_id=None 起，经真实两路握手、四项 quote 和独立虚构现金快照，原 submit ACK 在 journal 持久并读回后由原 coordinator 自动采用可信订单身份。随后 2201 部分成交累计观察、2205 撤单 ACK、第二个独立 operation ID 的 2201 状态观察均走实际生成类与真实 TCP。12 ACTION、10 请求/响应帧。关闭重开全部原 12 ID，原数据库/registry 字节不变，0 新连接/发送，恢复 codec 仍 None 且未采用订单。
- shared stop 在原 ACK 之后阻止 followup，原 ACK/可信编号保留，没有新的 query ACTION 或发送。
- foreign orderIDEx 的 2201 原响应完整保留，不产生 matched response facts，也不覆盖原 ACK 身份。
- quote-loss 明确故障注入：关闭已持有真实 quote socket，核 fd=-1，并清 quote live markers；保留原 accepted 身份。真实 peer 收到 quote EOF，trade 查询和撤单继续成功，0 quote 重连，不释放未结算现金。此例没有实现或声称生产 FIN 自动检测；没有调用/重置 transport 的总 cleanup allowance。

2201 是订单累计字段观察，不是逐笔成交 2211；本批未调用 2211/2225。2205 请求的 required numeric orderID=0 与锁定 SDK 实现一致，真正绑定的是原 opaque orderIDEx。实际响应按协议填 required numeric orderID=44，不从数字反推订单权限。submit/cancel ACK 不表示成交或经济终局；filled_notional、fees、fees_final 继续未知，reserve 不释放。

W4 专用顺序是 quote init→四 quote→trade init→submit→followups。产品 RPC15s、cleanup5s、原 query-window30s 以及模拟 peer 报告的 keepalive30s 均未放宽，实际各通道从 init 开始至最后 transport outcome 都在30s内（逐例单调时钟记录见摘要）。测试进程使用有据的 wall90s/READY30s/message15s/exit10s，owned peer150s，outer480s；标准层仍wall8s/READY与message4s/exit3s/peer45s。这些是受控装配预算，不是生产启动性能证明。

恢复不会重新编码请求、采用订单身份或通信；构造器仍会序列化未使用的合成 response，对外不得简称“完全不编码”。原请求 registry 仅保存测试装配的原帧/permit时间；身份从原 journal.read_acknowledged_order，submit bundle从read_submit_observation恢复。它不是新的业务账本或授权源。各 case 的原请求/私有响应/SQLite/worker报告/peer记录保存在 cases，普通标准测试 TEMP 则已清理。

旧 run-r1-positive 是修正前1例诊断，run-r2-full 是修正前3例验证，不累加为最终覆盖，也不声称覆盖 confirmed quote loss。root保存的 ../pre-quote-loss-source-r1 含旧10源码原件；本次逐hash重建并核对旧两run全部1626输入，所以当前源变化不抹去旧结果。最终run输入1626项全部保持原hash，仅54项属于实测加载/核验的源码模块；最终包模块文件233项、protobuf binding核验集合247项、两者包路径并集269项分别列明，绝不把整个输入清单称为已执行模块或整包验收。

FINAL-SHA256.json 为本目录原件清单；摘要计数、SHA、每 worker 状态/实际单调时间、socket次数、故障注入说明均可独立复核。本 agent 未提交或推送，root统一交接。
