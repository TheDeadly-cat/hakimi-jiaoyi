# ADR 0458: Causal checkpoint ratio contract v1

- Status: Accepted
- Date: 2026-08-25
- Scope: Synthetic causal prefix audit input validation only

## Context

`causal_prefix_invariance_check` converted checkpoint ratios inside a set
comprehension. A missing container or nonnumeric element escaped as an uncaught
`TypeError` or `ValueError`. Boolean and nonfinite elements were silently
discarded and later surfaced as the unrelated
`insufficient_rows_for_prefix_checkpoints` issue.

Pure synthetic calls established all four behaviors before implementation. No
market task or formal backtest was run.

## Decision

Introduce `causal-checkpoint-ratios-v1` as an input sub-contract:

1. The container must be a non-empty tuple or list.
2. Each element must be non-boolean, numeric, finite, and strictly inside the
   open interval `(0, 1)`.
3. Numeric strings remain accepted and are normalized once to floats, preserving
   the established numeric-input compatibility.
4. Invalid input returns a structured `BLOCK` before dataset preparation or
   strategy factory invocation. It never raises to the caller.
5. Reports expose the sub-contract version and normalized requested ratios.

The outer `causal-prefix-invariance-v2` identifier remains unchanged because
valid-input audit semantics and outputs are preserved. The new sub-contract is
additive and explicitly versioned for consumers.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| `None`, string, mapping, or set container | Explicit sequence-contract block |
| Boolean or nonnumeric element | Explicit numeric-contract block |
| NaN or infinity | Explicit finite-value block |
| Ratio at or outside 0 and 1 | Explicit open-interval block |
| Empty sequence | Explicit empty-contract block |
| Numeric string inside the interval | Normalize once and retain audit behavior |

## Boundaries

- This does not change strategy logic, execution prices, performance metrics, or
  acceptance thresholds.
- Tests use synthetic in-memory rows only and do not access network, runtime,
  database, cache, log, or secrets.
- Paper and live execution remain unauthorized.
- The public natural-forward chain and pointer-v2 contract are unchanged.
- A passing synthetic audit is not profitability evidence.
