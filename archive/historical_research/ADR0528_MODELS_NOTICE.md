# ADR0528 historical domain models

`adr0528_models.py` is the byte-preserved pre-migration implementation formerly located at `outputs/python_quant_bot/quant_bot/models.py`.

It is inert historical evidence. Active research code must import `hakimi_research.models`; the legacy `quant_bot.models` path is a compatibility re-export of the same canonical class objects.
