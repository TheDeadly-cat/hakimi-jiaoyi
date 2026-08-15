# G50 日线波段研究假设

> Saved-project note (2026-08-10): historical negative evidence only. G50
> `trend_pullback` is falsified and its old strategy ID is retired from new
> research. Any `runtime_g50` path below is an unmigrated historical reference,
> not a current artifact or permission to rerun this generation.

状态：FALSIFIED_IN_DEVELOPMENT
日期：2026-08-04

## 研究结论

固定参数诊断未通过，停止该假设，不进入预登记、确认集或模拟盘：

- 6 个选择标的中，仅 1 个测试收益为正，仅 1 个测试超额收益为正。
- 时序稳定性通过 0/6，滚动验证通过 1/6。
- 测试交易共 12 笔，测试收益中位数为 -0.965%，测试超额中位数为 -4.93%。
- 因果前缀检查通过 6/6，成本检查通过 6/6，说明主要失败点是策略有效性和跨标的稳定性，而不是未来函数或成本模型。
- ON、MCHP 未加载，继续保留为未触碰标的，不为本假设消耗。

可审计记录：`runtime_g50/reports/g50_trend_pullback_development_falsification.json`。
禁止针对已暴露窗口调整本假设阈值后重新包装为 G50 候选。

## 研究问题

在已经暴露的 G48 选择集上，单一收盘价指标和严格放量突破都缺少跨标的稳定性。G50 只研究一个新假设：长期趋势向上时，20 日均线附近的回调收复或 20 日放量突破，配合 ATR 波动约束和结构退出，是否能在固定成本后提高跨标的测试超额与时序稳定性。

该问题只用于研究和内部回测工程验证，不构成交易建议、模拟授权或实盘授权。

## 固定策略合同

- 策略编号：`trend_pullback`
- 周期：完成的 `1D` K 线
- 方向：只做多或空仓，不做空、不加仓、不使用杠杆
- 成交语义：收盘后产生信号，下一根 K 线开盘成交
- 趋势：收盘价和 SMA20 均高于 SMA100，且 SMA100 高于前一日 SMA100
- 回调入口：上一根 K 线触及 SMA20 附近但没有破坏长期趋势，本根阳线重新站上 SMA20，成交量不低于过去 20 日均量的 85%
- 突破入口：收盘突破此前 20 日最高价，成交量不低于过去 20 日均量的 110%
- 波动过滤：ATR14 / 收盘价必须在 0.8% 至 8% 之间
- 追高过滤：收盘价距离 SMA20 不超过 2 ATR
- 退出：连续两日位于各自 SMA20 下方、跌破此前 10 日低点、跌破 SMA100，或收盘低于入场价 2 ATR
- 回测风控：20% 目标仓位、1 倍现金、无固定止盈、8% 紧急止损、手续费 0.05%、滑点 2 bps
- 参数搜索：禁止。只允许这一组固定窗口和阈值进入 G50 单次协议

## 评价顺序

1. 所有数据完成态、修订证据、共同日历和因果前缀检查必须先通过。
2. 选择集沿用已暴露的 AAPL、NVDA、MSFT、MU、WDC、BTC-USDT，仅用于选择门禁。
3. 只有选择门禁通过后，才允许读取事前暴露审计为零的确认标的。
4. 主要指标是固定成本后的测试超额收益与跨标的通过数量；回撤、Sharpe、成交数量、成本敏感性和市场状态覆盖为并列风控门槛。
5. 任一门槛失败都保留负面报告并停止；不得降低阈值、替换确认标的或重复领取同一协议。

## 安全边界

- `research_only=true`
- `paper_authorized=false`
- `live_order_allowed=false`
- `paper_clock_supported=false`
- 新确认标的在协议注册和领取前禁止读取价格、K 线、成交量、财报或衍生指标
