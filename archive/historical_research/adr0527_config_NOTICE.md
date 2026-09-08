# ADR0527 Research Configuration Archive Notice

`adr0527_config.py` is the byte-identical implementation formerly located at
`outputs/python_quant_bot/quant_bot/config.py`, with SHA-256
`84c4d198eb9df4299c6398a46123529a91b072f2e6ecbb86e3bf1e1996e8a8de`.

The active implementation is `src/hakimi_research/config.py`. The legacy module
path is a compatibility re-export only. Paper, live, optimizer, non-finite, and
synthetic-provider file intent is rejected rather than silently rewritten.
