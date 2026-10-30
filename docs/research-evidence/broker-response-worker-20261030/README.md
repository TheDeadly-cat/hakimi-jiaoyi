# 响应事实、原请求记账与有界执行进程

本批继续 T29/T30 的离线工程准备。研究与原终端入口保持；当前交付包仍为 a235e8a / 0.7.0.dev3 r4，未包含这批后续源码。没有外部券商请求、真实订单或原生窗口操作。

## 实际改动

- 通过同一可信 codec 重新解码原 Request/Response，绑定实际 journal ACTION ID、完整帧摘要、协议/序号、账户/模式、原意图和 opaque orderIDEx。只接受 private-factory 的不可变 facts；自封存 hash 不宣称来源认证。
- 下单 ACK、撤单 ACK、查询返回、API 错误及查无结果分开。API 错误不是拒单终态；撤单 ACK 不是撤单完成。现金、可用资金和融资购买力分别保留；券商总持仓不分配给某个策略。缺失费用不补零，成交均价乘数量仅为标注的估计，不能当精确成交金额。
- `VERIFIED_RESPONSE` 事件原子保留完整 facts 及原操作的保守状态变化。只有确切 submit/cancel ACK 转为 ACK；迟到 ACK 必须引用原 UNKNOWN 证据，不重发、不增加 ACTION。读到 FILLED_ALL 或 fee=0 仍不更新现金、持仓或最终费用。旧事件和原 UNKNOWN 字节保持。
- 对合法范围内但与既有累计、终态或新余额相矛盾的迟到事实增加风险阻断，保留原账等待明确对账；数量/价格/费用越界及累计回退同样阻止新认领，不用估计值补账。
- 新进程监督器绑定绝对 Python/入口及 hash、新建输出父目录和唯一运行目录。固定 `-I -S -B -u`、无 shell、Windows 隐藏窗口，独立看门狗限制时间、消息数和输入/输出字节。停滞、洪水、半条 JSON、错误身份或回复丢失都终止本次拥有的子进程，保留原请求和 UNKNOWN，不自动重启/重发。exit 0 仅是进程事实；RESULT 也不是经济成功。

## 完整验证

- [完整整合门禁](integrated/summary.json)：**709/709**，0 skip/error/failure，包含原642及事实校验27、原请求记账18、进程监督22。15项打包、4项runner通过；全部2095输入前后完全一致。[精确源码身份](source-identity.json)、[输入清单摘要](input-manifests-summary.json)及[原始终端日志](integrated/terminal.log)分别保留。
- [锁定实际 protobuf 检查](actual-protobuf/run/probe-result.json)：**55项、7类响应**通过，205个实际加载的包/源码文件逐项核验。私有 Python、受限模块查找器只加载 protobuf，未导入 futu 顶层；socket、DB、子进程、线程、SDK context和业务运行均0，本机名称读取0。所有报文数值及 ACTION 都是明确合成值；**不是来自数据库的原券商 ACTION，也不是来源认证或实际 OpenD 验收**。[探针说明](actual-protobuf/PROBE-HANDOFF-r1.md)保留全部原件身份。
- [事实模块说明](facts/HANDOFF.md)、[记账说明](recording/HANDOFF-r1.md)、[进程接口与边界](worker/WORKER-HANDOFF-r1.md)保留分阶段证据；最终709门禁覆盖冻结最终字节，不能用早期分项结果替代它。
- 修前只读审阅发现合法迟到成交在终态/余额更新之后未阻断新风险，[原审阅](worker/journal-response-review-r1.json)和[修后复核](worker/journal-response-review-r2.json)均保留。相关3项新回归见[原始输出](recording/review-regressions-r4.log)。
- 开发中一次集成测试误以为5分钟后已过期，原console结果保留为明确标注的[转录说明](recording/targeted-r1-console-note.json)，随后改用真实合同到期时间。监督器测试暴露超时后闲置句柄未释放的 ResourceWarning，原日志保留；补充关闭后该项以 warnings-as-error 通过，不改原 UNKNOWN 回执。[修复验证](worker/targeted-idle-release-r3.json)。
- 上一提交6581c5926d5283a0b3916041b2292dcc1b1031d5的[run167](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/40980480080)已11/11成功、attempt1；[终态原收据](ci167-completed-summary-r1.json)。本批新提交的CI另核。

## 实际限制与下一步

本批没有 JS、既有页面/路由或 host 变更，本地桌面检查不重复。`TestWorkerSpec`只运行新建合成夹具；`PackageWorkerSpec`可以绑定文件，但当前 launch 明确返回 `PRODUCTION_ADMISSION_UNAVAILABLE`。监督器不是OS隔离区，也不能强制中断本地文件系统调用；finish到期返回None不能被当完成。未确认清理会保留UNKNOWN，停止子进程不等于取消券商订单。

facts仍为 test_only、source_authenticated=false，EXTERNAL_RECORD继续拒绝测试合同，九项外部权限均false。仍缺生产授权与每次派发gate、应用共享root/停止控制接线、实际worker与transport的完整串联、可信账户/策略持仓分配、精确成交额/费用最终性与价格规则证据、实际OpenD/加密兼容及REAL执行。T29/T30继续DOING，不能将这些工程缺口列为仅待授权。

当前r4原生验收、独立无源码环境、真人试用与真实TSLA资料链仍按原清单单列。旧r2原生窗口继续保留OPEN，未确认FINAL_CLOSED。Documents、dev5、旧包和历史UNKNOWN/T3没有被运行或迁移。

所有复制原件见[复制清单](original-copies.json)，目录完整校验和见[SHA256SUMS](SHA256SUMS)。
