# 查询事实的字段边界（2026-11-08）

本次仅查阅公开官方说明，没有启动 OpenD、查询账户或发送外部订单。当前网页标示 v10.12（中文全局状态搜索快照为 v10.10）；工程锁定的 SDK 是 10.7.6708。因此这些说明用于识别字段含义和未完成项，不能替代锁定版本与 OpenD 的兼容验收。

| 官方来源 | 已核实含义 | 本里程碑的处理 |
| --- | --- | --- |
| [全局市场状态](https://openapi.futunn.com/futu-api-doc/en/quote/get-global-state.html) | `marketUS` 的协议说明指向 Nasdaq 全局状态；官方建议查询具体品种的市场状态。服务器时间为 GMT 秒，本地时间是 OpenD 机器时间。 | 保留原值和全局范围；不把服务器登录、全局开市或连接 ID 当作目标股票可交易、行情权限或下单授权。 |
| [静态证券资料](https://openapi.futunn.com/futu-api-doc/quote/get-static-info.html) | 指定证券列表时按该列表查询；每手股数随证券类别有不同含义。 | 按请求中的市场和代码核对返回行；不从普通股票类型和 lot 推导完整交易资格。 |
| [行情快照](https://openapi.futunn.com/futu-api-doc/quote/get-market-snapshot.html) | `update_time` 是当前价更新时间，美股默认美东时间。`price_spread` 是卖一价相邻档位的报价差。 | 保留原时间、可选时间戳和缺失状态；不把接收时间当行情时间，不把价差作为订单 tick 表，也不将当前价时间推广到全部字段。 |
| [账户资金](https://openapi.futunn.com/futu-api-doc/trade/get-funds.html) | `available_funds` 仅期货账户适用；计价币种与账户类型有关。 | 不把该字段或购买力转换成本策略可预留 USD 现金。现金、归属持仓和费用资格另行处理。 |
| [订单费用](https://openapi.futunn.com/futu-api-doc/en/trade/order-fee-query.html) | 接口返回指定订单费用及明细；限制明确排除模拟交易账户。 | 现有合成费用报文测试只证明编码与记录合同。不能宣称官方模拟账户已支持费用查询，也不能推导费用最终性、币种或下单前费用上界。 |
| [下单](https://openapi.futunn.com/futu-api-doc/trade/place-order.html) | 当前说明给出的美股价格精度为低于 1 USD 时四位小数、其余两位。 | 此规则尚未证明适用于锁定 SDK/OpenD 组合；不会把旧离线编码样本的八位小数当作合法外部订单。 |

本里程碑限定为：确定性请求构造 → 自持本机 TCP 测试服务 → 原 worker/协调器 → 原 `VERIFIED_RESPONSE` 账本 → 同 ID 只读找回。仅使用明确标注的合成报文。

三类查询事实只是资料链的一部分。目标证券的交易时段、报价时效、合法价格与数量、行情权限、资金归属、费用和生产授权仍需分别完成；本批不增加可绕过的可选下单检查，也不声称已实现完整下单前核对。已发布 r7 保持原字节，本批不在 r7 包内。
