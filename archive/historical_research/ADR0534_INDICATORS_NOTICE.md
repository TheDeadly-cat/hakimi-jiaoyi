# ADR0534 historical indicators

`adr0534_indicators.py` is the byte-preserved pre-migration implementation formerly located at `outputs/python_quant_bot/quant_bot/indicators.py`.

It is inert historical evidence. Active research strategies must import `hakimi_research.indicators`; `quant_bot.indicators` is a compatibility re-export of the same canonical functions.
