# BTC 日线历史数据库

目标目录：

```text
Z:\jiaoyiguowangshuju
```

已生成文件：

```text
btc_daily_prices.sqlite
btc_daily_prices.csv
```

当前 CSV 检查结果：

```text
行数：3079
起始日期：2018-01-11
最新日期：2026-06-16
数据源：OKX BTC-USDT 日线
```

## 字段

| 字段 | 说明 |
|---|---|
| date / trading_date | 交易日期 |
| ts_ms | OKX K 线时间戳，毫秒 |
| open | 开盘价 |
| high | 最高价 |
| low | 最低价 |
| close | 收盘价 |
| volume | 成交量 |
| volume_ccy | 币种成交量/金额字段，来自 OKX |
| volume_quote | 计价成交额字段，来自 OKX |
| confirmed | K 线是否确认，1 为已确认，0 为当前未完结周期 |
| source | 数据来源 |

## 使用方式

重新下载并更新数据库：

```text
build_btc_daily_database.bat
```

检查数据库状态：

```text
check_btc_daily_database.bat
```

## 说明

OKX 的 BTC-USDT 日线数据当前可回溯到 2018-01-11。如果需要更早的 BTC 历史价格，需要额外接入 CoinGecko、CryptoCompare、Yahoo Finance 或其他全市场历史数据源作为补充。
