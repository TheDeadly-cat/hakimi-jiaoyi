# 哈基米交易 v2 Market Scope

V2 here means the second-generation product version.

## Crypto

Only these crypto assets remain in the main market universe:

- BTC
- ETH
- DOGE

Each crypto asset has two market entries:

- Spot: `BTC-USDT`, `ETH-USDT`, `DOGE-USDT`
- Perpetual swap: `BTC-USDT-SWAP`, `ETH-USDT-SWAP`, `DOGE-USDT-SWAP`

## Stocks

The first stock research list is:

- `AAPL`
- `MSFT`
- `NVDA`
- `TSLA`
- `MSTR`
- `SPY`
- `QQQ`

Stocks are research-only for this phase. No real stock order routing is enabled.

Stock charts now support period-aware requests:

- `1m`, `5m`, `15m`, `1h`, `4h`
- `1d`

Stock intraday sessions:

- All sessions
- Premarket
- Regular session
- After-hours
- Overnight

Extended-hour data depends on the upstream public quote source. If a stock has no after-hours or overnight rows in the source response, 哈基米交易 v2 shows an empty-session state instead of fabricating prices.

## Software Launcher

The first v2 software-style launcher is:

```text
outputs/Hakimi_Trade_V2_START.bat
```

It starts the local 哈基米交易 v2 terminal. A packaging step can turn this into a normal Windows `.exe` app.
