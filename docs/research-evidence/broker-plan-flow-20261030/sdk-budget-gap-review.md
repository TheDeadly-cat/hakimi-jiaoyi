# Futu 10.7.6708 与当前离线计划预算的静态核对

只读来源：`terminal-wheelhouse-r1/futu_api-10.7.6708-py3-none-any.whl`，SHA256 `a3bc7609fc7b60c0ca3cd2971bc8b81819338d3c88ad25d1bd3f647d781554b5`。仅用标准库 ZipFile 读取成员文本；没有 import SDK、访问配置/OpenD/账户、启动旧工具、运行研究、打开业务库或外网。wheel 的 `futu/VERSION.txt` 文本是 `10.07.6708`，与发行元数据 `10.7.6708` 的格式差异应显式处理，不能直接拿显示字符串比较后猜测兼容。

结论：**现有 v1 纯计划可以继续作为离线保存合同，但不能直接套官方两个高层 context 并宣称执行预算已满足。** 连接、隐式查询/订阅、重连、等待、输出的实际行为均需要版本化的 scoped profile 与验证；不能把旧计划的 connect=1 偷换成“一个流程可建两个连接”。

下列行号均为该 wheel 内成员的原始行号。

## 具体差距

| 当前合同/需要 | pinned SDK 实际行为与来源 | 对实际 adapter 的要求 |
| --- | --- | --- |
| connect=1 | `quote/open_quote_context.py:81–97` 与 `trade/open_trade_context.py:13–29,1163–1165` 各调用 OpenContextBase；`common/open_context_base.py:416–429` 各调用 NetManager.connect。共享 NetManager 不等于共享 broker socket。 | 标准 quote+trade 路径有两个 OpenD 连接。新 profile 应分别计 quote_connect=1、trade_connect=1、reconnect=0；若要一个连接，必须另有经过验证的专用单连接协议实现，当前不能假定已有。 |
| account_read=1，只有显式读取 | `trade/open_trade_context.py:37–55,198–219`：trade 构造的连接成功回调自动 GetAccList；security_firm=NONE 时可能再读一次，并 SubAccPush 所有返回账户。`268–290`：即使显式传 acc_id，每个交易 API 的账户检查仍会再 GetAccList。 | 构造不是纯本地动作。必须在首次连接前阻止自动账户订阅/自动账户选择，或显式预算并授权这些协议。不能把每次 accinfo/position/place/query/cancel/fee 内部的账户读取漏算。 |
| submit=1 / observe≤5 | `trade/open_trade_context.py:609–623`：PlaceOrder 成功后，public place_order 内部再查询订单最多 3 次。每次 public order_list_query 还先执行账户查询。 | 返回一个高层函数不等于一个协议请求；计数须落到实际发包边界。可采用锁定版本受限协议封装，单次 PlaceOrder 原响应立刻入账，后续查询逐次消耗 observe 预算，禁止隐藏 3 次轮询。 |
| 自动重试=false | `common/open_context_base.py:61–100`：_auto_reconnect=True，默认同步构造 while True，失败间隔 6 秒；`517–531,687–731`：断线安排 Timer 重连。Quote 的 `115–136` 会恢复旧订阅；trade 会重新订阅，曾解锁则 `37–47` 自动解锁。 | 构造后再设置 _auto_reconnect=False 已经太晚。受限实现必须在首个连接尝试前设定不可重连行为，并在底层拒绝第二次 connect。第一次失败保留失败/未知事实，不自动新建 context。旧 profile 或解锁状态不能继承。 |
| call_timeout 1–30 秒，wall≤180 秒 | `common/open_context_base.py:79,270–301` 默认等待可发送状态无限；set_sync_query_connect_timeout 只约束此阶段。ReqInfo.wait 固定 20 秒（50–55），通常 tick 在 _query_timeout=12 后结束请求（618–634）。`network_manager.py:76–81` 的 ConnectInfo.wait 无自身超时参数。一个高层函数还可串联多个请求。 | 不能称设置连接等待超时就实现了整次 API deadline。必须有独立进程的单阶段/总墙钟硬上限与有界清理；超时杀进程后，已发订单状态仍 UNKNOWN，不能当作拒绝或自动重发。 |
| stop 屏障 | `common/open_context_base.py:203–215` 的 stop 仅切 _proc_run，不关闭 socket、停止 keepalive 或重连。`144–161` 的 close 才关闭当前连接并在正常关闭时禁重连。 | 应用 stop 不能映射成 SDK stop。要阻挡后续实际发包/认领，允许已经开始的请求保持在途；关闭和清理是另一有界动作，不能宣称已撤单。 |
| fee_read=1 与提交前 BROKER_FEES | `trade/open_trade_context.py:812–845` 的 order_fee_query 按已有 order_id_list 查询，不能替代下单前费用规则/估计证据。 | 分开预先核验费用规则/费用上限与订单后实际费用查询；费用缺失保持 null，不补 0。观察/fee 查询都绑定原 account、mode、order_id。 |
| security/quote freshness | `quote/open_quote_context.py:189` get_stock_basicinfo 有 lot_size；snapshot 在 545–558 发一次查询；其 price_spread 的说明（481）是相邻盘口价差，不等于完整可交易价格步长规则。update_time（428）是市场本地时间字符串。trade 查询默认 refresh_cache=False。 | 精确 US 证券、整股与价格规则分别核对；不能把 price_spread 直接当 tick_size。区分查询时间与数据更新时间，缓存缺时间不能算新鲜。全程显式 acc_id、trd_env、US market、USD，不使用 REAL/acc_id=0 默认值。 |
| 输出≤128KiB，观察≤100条 | `common/callback_executor.py:19–24,39–45` 队列无容量上限，超过1000只警告；`open_context_base.py:533–536,584–591` 收推送进队列/扩展接收缓冲。keepalive 自动发送（593–615）。`common/ft_logger.py:66–99,262` 默认在用户 appdata/HOME 创建并轮换文件日志。 | 推送与 heartbeat 必须显式禁用或逐项限额，不能漏计；原始输出、日志、异常文本与证据文件总和都纳入预算。新隔离 worker 在导入前隔离自己的日志目录，不碰用户旧配置；单靠 stdout 截断不够。 |

`place_order` 本身未见自动重发 PlaceOrder 的循环；这里的确定问题是重连和隐式账户/观察调用，不能将 SDK 内部查询循环误述成重复下单。`modify_order(CANCEL)` 成功只返回环境与 order_id（637–685），不是“订单已撤销”的终态证据。

当前 CALL_LIMITS 的 account_read/position_read/submit/observe/cancel/fee_read 如果按 public 方法调用计算，会严重少计 GetAccList。举例：默认 trade 初始化 1–2 次，加资金、持仓、一次下单、五次公开订单查询、一次撤销、一次费用查询各自的账户检查，可能为 **11–12 次 GetAccList**，尚未计调用者额外显式 get_acc_list；因此“account_read=1”不能当作实际账户查询上限。没有实际运行该例子，这个数字由上述源码调用路径静态相加。

## 下一最小实现

1. **保留 v1 不变，新执行 profile 先离线验证。** 明确两类 OpenD 连接/握手、逐协议 RPC、heartbeat/push、重连=0、缓存/时点语义和单阶段/总超时。现有 v1 的权限始终关闭；新 profile 需要新身份与明确确认，不给旧 plan 原地扩预算。对 pinned wheel 建 fake-NetManager/脚本化协议响应测试，证明构造前限制生效、额外协议被拒绝、默认 REAL/acc_id=0 不会漏入请求。测试不能只 mock 外层 place_order 返回。

2. **新增独立执行 journal，先接 fake transport。** 新 `terminal_broker_execution_journal.py`（名称建议）按 provider+mode+account 分隔，不用原 candidate control DB 存账户经济状态，也不激活任何旧 AMD/profile/UNKNOWN/T3。一个事务核验 exact plan/authorization/evidence identities、写唯一原 intent_scope_id 认领、占用共享现金或 owner 股数，再记录待派发状态。新 plan 不重置旧意图的唯一认领；同账户多个策略使用同一 reservation 总账。SELL 的 owner 归属不能仅由券商总持仓猜出。

3. **具体状态推进**：PREPARED → CLAIMED_RESERVED → DISPATCH_INTENT → ACKNOWLEDGED / EXPLICIT_REJECTED / UNKNOWN；观察按原订单的累计数量/金额/费用去重。部分成交保留剩余占用；撤单 ACK 不释放；最终取消只释放未成交部分。迟到成交保留事实，出现 cash<reserved 或 owner held<reserved/负仓时停新风险并要求对账。未知查不到仍 UNKNOWN，不能再次 submit。

4. **短停止屏障只覆盖认领/实际派发，不覆盖等待响应。** 沿用当前计划服务的锁序：journal 写事务先取，候选 control barrier 后取；在连接前、claim 前、每次实际 send 前检查同一控制 revision。把 DISPATCH_INTENT 持久化后才允许发包。若 stop 赢先手则拒绝新派发；若已交给网络发送，则明确在途，不声称停止已取消。不能仅在 public place_order 外层检查一次，否则 SDK 后续查询/heartbeat仍可越过屏障。

5. **一个受限 worker 入口，不在宿主 import SDK。** 使用新包内显式 adapter entrypoint，和实际 plan/profile/source identity 绑定；新临时运行目录、过程/输出硬上限和有界退出。返回原始外部回执/缺失字段，不能用手工合成余额或成交当券商事实。第一步离线用脚本化 transport 验证双策略争同一现金、跨 plan 重复 intent、stop 在 claim/send 两个间隙、发送后失联、查询不到、部分成交+撤销+迟到成交、输出超限、进程重开。SDK 子进程与真实网络启用是之后独立授权步骤。

此切片不是通用交易框架，也不是把旧工具搬入同窗；只处理本次精确绑定的 US 股票/账户/模式/订单。官方 SIMULATE 与 REAL 用不可互换的 profile/adapter/authorization identity；不自动降级。

## 仍需明确外部授权的部分

- 实际创建 quote/trade context 会连接 OpenD并握手；trade 的标准构造还可能读账户/订阅推送。这些都不能由“查看候选/保存计划”隐式授权。
- 实际账户列表、资金、持仓、证券、报价、OpenD状态和费用读取，需明确对应读取范围和次数；不能沿用 Yahoo 日线许可。
- 对冻结 mode/account/security/side/qty/limit/fee ceiling 的一次 submit，和对精确己方 broker order 的 cancel，各需本次明确授权。REAL 资金及必要解锁另行确认；当前 unlock=0，不会自动解锁或复用旧密码。
- 真实延迟、账户权限、市场数据权限、受理/成交/费用与断线恢复只能在这些授权具备后检验；本次静态审阅不提供任何此类真实性结论。已确认 SYNTHETIC/QA 研究仍被 offline-only 决策阻断。

本次只读审阅没有修改 parent 源码或冻结包，没有 import/运行 SDK，没有连接/查询任何用户服务。当前 plan/loader/service 可保存的仍是离线计划与包身份事实，尚不是实际 scoped adapter 的执行验收。
