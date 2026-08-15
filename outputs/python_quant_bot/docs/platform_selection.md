# 外接交易平台选择：OKX vs 富途牛牛

日期：2026-06-17

## 结论

第一阶段建议优先接 OKX。

原因很直接：当前项目已经是加密货币量化机器人，OKX 提供公开行情、账户、下单、WebSocket 等接口，Python 端可以通过 ccxt 或 OKX REST/WebSocket 直接接入；不需要额外运行本地行情网关。

富途牛牛更适合第二阶段作为股票交易适配器。它适合港股、美股、A 股相关的行情与交易，但接入通常依赖 Futu OpenD 本地网关、账户权限、行情权限和交易解锁流程，整体新手门槛更高。

## 对比

| 维度 | OKX | 富途牛牛 / Futu OpenAPI |
|---|---|---|
| 主要市场 | 加密货币、合约、永续、期权 | 港股、美股、A 股相关市场 |
| 接入方式 | REST API + WebSocket，可用 ccxt | Python SDK + 本地 OpenD 网关 |
| 是否需要本地网关 | 不需要 | 需要 OpenD 常驻 |
| 新手接入难度 | 较低 | 中等偏高 |
| 实时行情 | WebSocket 直接订阅 | 通过 OpenD 订阅行情 |
| 自动交易 | API 下单/撤单 | SDK 调用交易接口，通常需要交易解锁 |
| 模拟盘/测试 | OKX 有模拟交易环境 | 取决于账户、市场和 OpenD 能力 |
| 对当前项目匹配度 | 高 | 中，适合作为后续股票模块 |

## 建议路线

1. 先把 OKX 做完整：实时行情、历史 K 线缓存、模拟盘、回测、策略寻优、风控、实盘开关。
2. 机器人核心保持平台无关：策略只输出 `BUY`、`SELL`、`HOLD`、`EXIT` 信号。
3. 执行层做成适配器：`OkxBroker`、`PaperBroker`、未来再加 `FutuBroker`。
4. 数据层也做适配器：`OkxDataProvider`、`CsvDataProvider`、未来再加 `FutuDataProvider`。
5. 等 OKX 这一套跑稳定，再接富途牛牛，用同一套策略接口复用到股票市场。

## 官方资料

- OKX API 文档：https://app.okx.com/docs-v5/en/
- Futu OpenAPI 文档：https://openapi.futunn.com/futu-api-doc/en/
- Futu OpenAPI 权限说明：https://openapi.futunn.com/futu-api-doc/en/intro/authority.html
