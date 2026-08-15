# Market Workflow Strip - 2026-07-09

## Scope

- Added a visible market workflow strip above the ticker table.
- The strip summarizes symbol, data quality, trend state, anomaly score, evidence count, and next research action.
- Added workflow actions: refresh radar, open evidence, and send current context to the AI research view.
- These actions are research-only and do not place live orders.

## UI Behavior

- Trend state is compressed to a short label such as range/up/down instead of a long cockpit sentence.
- Narrow windows wrap the workflow strip into three columns plus a full-width action row.
- The workflow strip updates when the selected symbol, chart data, trend cockpit, anomaly radar, stock source state, or local AI summary changes.

## Validation

- `node --check outputs/python_quant_bot/exchange_terminal/static/app.js` passed.
- `python -m py_compile outputs/python_quant_bot/exchange_terminal/server.py outputs/python_quant_bot/exchange_terminal/services/market_data_service.py` passed.
- `npm.cmd run check` passed in `outputs/hakimi_trade_electron`.
- Browser QA passed on `http://127.0.0.1:8765/`.
- AAPL loaded with a visible stock K-line.
- BTC-USDT switch loaded OKX realtime state and a visible K-line.
- Switching back to AAPL kept the stock K-line visible.
- The open-evidence workflow button moved to the research evidence area.
- No app console errors or warnings were observed during the validation flow.
