# ADR0530 historical risk engine

`adr0530_risk.py` is the byte-preserved pre-migration implementation formerly located at `outputs/python_quant_bot/quant_bot/risk.py`.

It is inert historical evidence. Active research code must import `hakimi_research.risk`; the legacy `quant_bot.risk` path is a compatibility re-export of the same canonical RiskManager class.
