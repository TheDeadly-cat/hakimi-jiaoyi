# Legacy optimizer archive

This directory preserves the retired parameter-grid optimizer implementation
for historical review only. It is not part of the importable product source,
is not supported by the research-only CLI, and grants no optimization,
paper, live, order, or profitability authority.

Original source path:
`outputs/python_quant_bot/quant_bot/optimizer.py`

Archived source SHA-256:
`fafb2a18deaf71f1f598bdf7205ce4e0a14fff7c42ac7320edc70de951c4337a`

The formal `BotConfig` rejects both `mode: optimize` and any top-level
`optimizer` configuration instead of silently treating those settings as
active.
