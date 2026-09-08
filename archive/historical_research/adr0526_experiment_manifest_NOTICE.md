# ADR0526 Experiment Manifest Archive Notice

`adr0526_experiment_manifest.py` is the byte-identical implementation formerly
located at `outputs/python_quant_bot/quant_bot/experiment_manifest.py`, with
SHA-256 `9b77e81fd18659a8e39ced8978f5c24c358c85b9c7f1b1e7b49da2e204a60b53`.

The active implementation is `src/hakimi_research/experiment_manifest.py`.
The legacy module path is a compatibility re-export only. This migration grants
no ranking, parameter-selection, profitability, paper, live, or order authority.
