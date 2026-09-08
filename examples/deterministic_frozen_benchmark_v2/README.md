# Deterministic Frozen OOS Benchmark v2

This source-controlled fixture is the governed synthetic reference for the
research-only Frozen OOS and cost-stress pipeline.

Run its verifier through the single product entrypoint:

```powershell
.\hakimi-research.ps1 frozen-benchmark
```

The verifier binds 128 synthetic daily rows to an explicit versioned dataset
governance declaration covering source identity, timezone, calendar, timestamp
semantics, adjustment basis, population construction, survivorship status,
delisting policy, and immutable sample boundaries. The current verifier also
requires the observed synthetic timeline to match the declared UTC daily
schedule exactly; real exchange calendars remain blocked until an external
schedule attestation is available under the controlled dependency closure. It also checks the fixed
40/4/40/4/40 partitions, benchmarks, 1x/2x/3x fee/slippage scenarios, one-bar
signal delay, deterministic every-third actionable-signal drop, source-fill
adverse-open shock, dependency lock,
source envelope, JSON report, Markdown report, and permanent authority locks.
The v14 fixture uses `frozen-evaluation-protocol-v17` and
`frozen-evaluation-report-v22`. Its provenance ledger binds 99 synthetic run
records, including 42 receipt-bound multiple-testing observations. The ledger
is self-contained and explicitly requires an external artifact hash; it is not
presented as a signature or as protection against whole-artifact replacement.

The fixture remains `SYNTHETIC_FIXTURE_ONLY` with quality status `BLOCK`.
It is not real-data evidence, a formal blind test, natural-forward evidence, a
profitability claim, parameter-selection or ranking permission, or trading
authority. The v1 directory remains unchanged as the historical v9 reference.
