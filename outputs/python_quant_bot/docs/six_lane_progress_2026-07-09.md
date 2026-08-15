# 哈基米交易 v2 六路线进度记录

更新时间：2026-07-09

## 当前产品方向

哈基米交易 v2 当前优先方向是“行情分析与市场异动捕捉软件”，不是实盘交易执行平台。模拟盘、回测、策略体检和研究流水线继续保留；实盘真实下单继续保持硬保护墙。

## 本轮落地

1. TradingView 路线：命令面板从跳转入口升级为研究动作入口，可直接刷新异动雷达、运行回测体检、打开风险解释、刷新数据总控、开启图表自动标注和回放模式。
2. NautilusTrader 路线：继续把核心能力放入服务层，现有 `market_data_service.py`、`risk_service.py`、`paper_executor.py`、`audit_log.py`、`event_bus.py` 作为后端内核拆分基础。
3. Freqtrade 路线：策略体检包含 lookahead bias 检查；回测输出门禁、run hash、data hash、param hash，强调只进入模拟盘验证。
4. OpenBB 路线：市场快照携带数据来源、实时性、adapter 信息；数据可靠性中心展示延迟、新鲜度、降级原因。
5. Hummingbot 路线：新增 OKX、Futu、stock cache、CSV/local history 四类只读行情 adapter 总控，不开放真实下单 adapter。
6. QuantConnect LEAN 路线：新增研究到回测、体检、模拟、审计的 release pipeline，并在策略区和系统区可视化。

## 新增接口与页面

- `/api/platform/v2`：现在包含 `six_lane` 总控字段。
- `/api/platform/six-lane`：单独返回六路线进度、分数、证据和下一步。
- 系统区 v2 控制中心新增“六路线总控”列表。

## 安全边界

- 不保存真实 API 密钥明文。
- 不打开实盘交易。
- adapter 只提供行情数据和本地缓存能力。
- AI、回测、策略体检、胜率估计均只用于观察、研究和模拟盘验证。

## 下一步建议

1. 把每次研究、回测、策略体检和模拟盘运行绑定成一个 Research Run ID。
2. 把更多订单生命周期逻辑从 `server.py` 移入 `paper_executor.py`。
3. 把事件总线接到行情异动、策略信号、风控阻断和模拟成交。
4. 为股票研究补财报、盘前盘后、行业联动、异常成交和新闻源。
