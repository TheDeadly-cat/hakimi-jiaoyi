# Hakimi Jiaoyi

Local, reproducible, research-only quantitative strategy validation.

The current product supports market-data research, historical backtests,
research reports, and strategy inspection. Paper execution, live execution,
order entry, and legacy parameter optimization are not product capabilities.

See [the research platform README](outputs/python_quant_bot/README.md) for the
supported commands, capability catalog, and evidence boundaries.

The canonical Windows CLI entrypoint is:

```powershell
.\hakimi-research.ps1 capabilities
```

It exposes research-only commands and does not enable paper, live, or order
execution.

The canonical dependency closure is the repository-root
[`requirements.research.lock`](requirements.research.lock). Supported research
commands load code only from `src`; they do not inject the historical
`outputs/python_quant_bot` source tree.

The Electron shell and Exchange Terminal are Experimental evidence-review
consumers. Their paper/live/order controls are archived or disabled, and the
desktop shell does not automatically launch an account gateway.

The source-controlled synthetic Frozen OOS and cost-stress reference can be
verified through the same entrypoint:

```powershell
.\hakimi-research.ps1 frozen-benchmark
```

The checked reference report is
[`examples/deterministic_frozen_benchmark_v2/expected_report.md`](examples/deterministic_frozen_benchmark_v2/expected_report.md).
It is a deterministic synthetic fixture with `BLOCK` quality status, not a real
dataset result, formal blind test, profitability claim, ranking permission, or
paper/live/order authority.

The checked six-strategy synthetic family baseline is verified independently:

```powershell
.\hakimi-research.ps1 strategy-family-benchmark
```

It covers the six registered RANGE/TREND members. ENSEMBLE remains an explicit
implementation GAP; this reference is not real-market or profitability evidence.

The checked synthetic walk-forward, parameter-stability, and multiplicity
robustness reference is verified independently:

```powershell
.\hakimi-research.ps1 strategy-robustness-benchmark
```

The repository stores only a compact receipt, neutral Markdown, and source
manifest; verification reconstructs all 32 source and 147 robustness runs in
memory. Its status remains `BLOCK`, and its synthetic FROZEN_TEST role is not a
formal blind test, profitability evidence, ranking permission, or trading
authority.

The checked synthetic statistical-correction reference is verified
independently:

```powershell
.\hakimi-research.ps1 strategy-statistical-correction-benchmark
```

It reconstructs the v2 trial matrix, descriptive Deflated Sharpe diagnostics,
CSCV-PBO diagnostics, and tie-aware identified sets. The repository stores no
DSR probability, PBO rate, or interval value in the compact receipt. Status
remains `BLOCK`; the reference grants no formal inference, ranking,
profitability, or trading authority.
## Canonical reproducible research dossier

The compact deterministic dossier is the primary human-readable entry point for
the current synthetic strategy evidence:

```powershell
.\hakimi-research.ps1 strategy-research-dossier
```

It verifies the checked-in reference and prints
[`examples/deterministic_strategy_research_dossier_v1/expected_report.md`](examples/deterministic_strategy_research_dossier_v1/expected_report.md).
The report compares two fixed synthetic benchmarks with six registered
RANGE/TREND variants across Train, Validation, and Frozen 1x/2x/3x cost
observations. ENSEMBLE remains an explicit implementation gap rather than a
validated strategy.

The compact check proves exact reference bytes, source lineage, and bound
component identities only. Semantic revalidation requires rebuilding the full
report-v14 chain. Status remains `BLOCK`; formal inference, paper, live, and
order-entry authority remain false.
