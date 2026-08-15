# Python Quant Bot

Python Quant Bot 是一个自动化、策略驱动的量化交易机器人系统。它的核心不是人工点买卖，而是由策略算法自动生成交易信号，经过风控系统校验后，由执行层完成模拟盘或实盘交易。

当前版本默认使用模拟盘执行器，真实下单接口保持关闭。接入交易所 API 前，请先完成足够的回测、模拟盘和风控验证。

## 已实现模块

- 策略引擎：双均线、网格、布林带、MACD、RSI、动量策略
- 标准策略接口：可新增自定义策略
- 数据层：OKX 公共 K 线、历史 K 线缓存、CSV、本地合成行情兜底
- 指标层：SMA、EMA、Bollinger、MACD、RSI、Momentum
- 回测系统：收益率、年化收益、最大回撤、胜率、夏普比率
- 参数寻优：网格化参数组合搜索
- 自动执行层：7x24 运行循环、模拟盘成交、可选 ccxt 实盘适配
- 风控系统：单笔亏损、单日亏损熔断、仓位比例限制
- 监控与日志：交易日志、权益曲线、异常日志

## 快速运行

交易所终端：

```powershell
.\start_exchange_terminal.bat
```

它会打开本地地址：

```text
http://127.0.0.1:8765
```

这是当前优先推进的主界面，包含实时价格、全市场实时价格面板、可悬停/拖动/缩放的K线、当前K线跟价更新、指标叠加、盘口、成交、市场分类、软件式导航、快捷键、马丁/反马丁/利弗莫尔等策略执行台、AI止盈止损建议、盈利概率估算、策略详情、条件委托、模拟盘订单流、订单历史、订单筛选、账户中心、资产划转、通知中心、系统设置、主题切换、终端事件、数据导出、策略市场、策略守护、后台守护入口、持仓、保证金、预估强平价、风险中心、合约信息、资金费率历史、策略排行榜和 BTC 往期价格库。

图形控制台：

```powershell
.\start_dashboard.bat
```

如果打不开，先运行环境检查：

```powershell
.\check_environment.bat
```

如果提示缺少依赖，先运行：

```powershell
.\install_dependencies.bat
```

启动脚本会自动寻找 Python 3.14、3.13、3.12、3.11。如果仍然找不到 Python，通常是安装后没有重启终端，或安装时没有勾选 `Add python.exe to PATH`。

在项目目录运行：

```powershell
cd outputs\python_quant_bot
C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe run_bot.py backtest --config config.example.json
```

模拟盘自动运行一次循环：

```powershell
C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe run_bot.py paper --config config.example.json --cycles 5
```

参数寻优：

```powershell
C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe run_bot.py optimize --config config.example.json
```

查看内置策略：

```powershell
C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe run_bot.py list-strategies
```

## 配置文件

见 `config.example.json`。控制台会自动生成 `config.local.json` 保存本机配置。核心字段：

- `mode`: `paper` 或 `live`
- `market`: `crypto`、`stock`、`futures`
- `data.provider`: `okx`、`csv`、`synthetic`
- `data.cache_dir`: 历史行情缓存目录
- `data.use_cache`: 是否启用历史行情缓存
- `strategy.name`: 内置策略名称
- `strategy.params`: 策略参数
- `risk`: 风控参数
- `execution`: 执行层配置

## 实盘说明

实盘建议使用 ccxt：

```powershell
pip install ccxt
```

然后在配置中设置：

```json
{
  "mode": "live",
  "execution": {
    "broker": "ccxt",
    "exchange": "okx"
  }
}
```

API Key 请使用环境变量提供，不要写入配置文件：

- `OKX_API_KEY`
- `OKX_SECRET`
- `OKX_PASSWORD`

当前代码会阻止在没有明确配置和风控校验时进行实盘交易。

控制台里的“模拟盘”会强制使用 `paper` 执行器，不会因为配置切到 `live` 而触发真实资金下单。

## 软件化路线

当前形态是“Python 自动交易机器人 + 本地网页控制台”。后续可以继续升级为：

- 后台机器人常驻运行
- 控制台只负责配置、回测、监控、日志
- 使用 PyInstaller 或桌面壳打包为 Windows 软件
- 单独增加更严格的实盘授权页和 API Key 管理

平台选择说明见 `docs/platform_selection.md`。当前建议第一阶段优先接 OKX，富途牛牛作为第二阶段股票交易适配器。

交易所终端说明见 `docs/exchange_terminal.md`。

## 自定义策略

新增策略时继承 `StrategyBase`，实现 `generate_signal`：

```python
from quant_bot.strategies.base import StrategyBase
from quant_bot.models import Signal

class MyStrategy(StrategyBase):
    name = "my_strategy"

    def generate_signal(self, data, portfolio):
        return Signal.hold("not ready")
```

然后在 `quant_bot/strategies/templates.py` 的 `STRATEGY_REGISTRY` 注册即可。

## 目录结构

```text
python_quant_bot
├─ run_bot.py
├─ config.example.json
├─ requirements.txt
└─ quant_bot
   ├─ config.py
   ├─ models.py
   ├─ indicators.py
   ├─ data.py
   ├─ execution.py
   ├─ risk.py
   ├─ engine.py
   ├─ optimizer.py
   ├─ reporting.py
   └─ strategies
      ├─ base.py
      └─ templates.py
```
