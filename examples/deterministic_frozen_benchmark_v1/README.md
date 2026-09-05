# Deterministic Frozen OOS Benchmark v1

This source-controlled fixture is the canonical synthetic reference for the
research-only Frozen OOS and cost-stress pipeline.

Run its verifier through the single product entrypoint:

```powershell
.\hakimi-research.ps1 frozen-benchmark
```

The verifier reconstructs the report from 128 synthetic daily rows, fixed
40/4/40/4/40 train/purge/validation/embargo/frozen partitions, the dual-MA
strategy, cash and engine buy-and-hold benchmarks, and 1x/2x/3x cost scenarios.
It checks the dependency lock, source envelope, inputs, protocol, JSON report,
Markdown report, and permanent authority locks without network, cache, service,
runtime, paper, live, or order activity.

The fixture is deliberately `SYNTHETIC_FIXTURE_ONLY` with quality status
`BLOCK`. It is not real-data evidence, a formal blind test, natural-forward
evidence, a profitability claim, parameter-selection or ranking permission, or
trading authority.
