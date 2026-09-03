# ADR0531 historical backtest core

`adr0531_backtest.py` is the byte-preserved pre-migration implementation formerly located at `outputs/python_quant_bot/quant_bot/backtest.py`.

It is inert historical evidence. Active research code must import `hakimi_research.backtest`; the legacy `quant_bot.backtest` path is a compatibility re-export of the same canonical Engine and Report classes.
