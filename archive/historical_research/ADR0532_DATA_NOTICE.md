# ADR0532 historical market-data providers

`adr0532_data.py` is the byte-preserved pre-migration implementation formerly located at `outputs/python_quant_bot/quant_bot/data.py`.

It is inert historical evidence. Active research code must import `hakimi_research.data`; the legacy `quant_bot.data` path is a compatibility re-export of the canonical provider and validation objects.
