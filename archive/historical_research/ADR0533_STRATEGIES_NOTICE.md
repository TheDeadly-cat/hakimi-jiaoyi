# ADR0533 historical strategy package

`adr0533_strategy_base.py`, `adr0533_strategy_templates.py`, and `adr0533_strategy_init.py` are byte-preserved pre-migration files formerly located under `outputs/python_quant_bot/quant_bot/strategies`.

They are inert historical evidence. Active research code must import `hakimi_research.strategies`; legacy `quant_bot.strategies` paths are compatibility re-exports of the same canonical objects.
