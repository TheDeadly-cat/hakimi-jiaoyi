# ADR0529 historical research execution simulator

`adr0529_execution.py` is the byte-preserved pre-migration implementation formerly located at `outputs/python_quant_bot/quant_bot/execution.py`.

It is inert historical evidence. Active research code must import `hakimi_research.execution`; the legacy `quant_bot.execution` path is a compatibility re-export of the same canonical simulator class.
