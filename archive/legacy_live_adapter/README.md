# Legacy live adapter archive

This directory preserves the complete pre-removal `quant_bot/execution.py`
snapshot containing the retired `CcxtBroker` hard-wall placeholder. The full
snapshot is retained so the class remains reviewable in its original context;
it is not importable product source and grants no live, paper, order, or
profitability authority.

Original formal source SHA-256:
`82a4a1e56201fef94a5ce158043c671d9b29463d843e69674bf8914f6c140e03`

The formal execution module keeps the permanent live-selector hard wall and the
negative `live_trading_enabled=False` configuration evidence required by Frozen
experiment manifests. The unused `ccxt` package dependency was removed from
both formal dependency manifests.
