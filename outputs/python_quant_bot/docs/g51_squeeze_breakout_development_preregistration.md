# G51 Squeeze Breakout Development Preregistration

> Saved-project note (2026-08-10): this frozen development hypothesis was
> falsified in development. `squeeze_breakout` remains available only for
> historical evidence replay; its old ID cannot start new research. Any
> `runtime_g51_dev` artifact path is an unmigrated historical reference.

- Experiment ID: `G51-SQZ-DEV-001`
- Frozen on: `2026-08-04`
- Status before data evaluation: `DEVELOPMENT_ONLY`
- Authority: research only; no paper or live execution authority

## Research Question

Can a long-only daily swing rule that requires volatility contraction, volume contraction, and a confirmed range expansion produce robust train/validation evidence across the already-exposed G50 development universe?

This is materially different from G50 `trend_pullback`: it does not enter on a moving-average pullback or reclaim. The causal trigger is a compressed volatility/volume state followed by a price, range, and volume expansion through a prior high.

## Frozen Data Roles

- Development selection symbols: `AAPL`, `NVDA`, `MSFT`, `MU`, `WDC`, `BTC-USDT`
- Protected holdout symbols: `ON`, `MCHP`
- Timeframe: completed `1D` bars only
- Maximum source rows: `780` per symbol
- Split: 50% train, 25% validation, remaining rows protected
- Development reports must physically exclude protected test OHLCV and persist `test=0` in every selection boundary.
- `ON` and `MCHP` must not be loaded by this run.

## Frozen Mechanism

Entry requires all of the following using only the current and prior bar prefix:

1. Short ATR divided by long ATR is below the fixed contraction threshold.
2. Short average volume divided by long average volume is below the fixed contraction threshold.
3. The current close breaks the prior channel high.
4. Current true range expands relative to prior short ATR.
5. Current volume expands relative to prior short average volume.
6. The close is positive, above the long trend average, and no more than the fixed ATR extension above the breakout level.

Exit occurs on an entry-anchored ATR stop, prior-channel structure break, or a falling long-trend break. The external research risk profile keeps take profit open and applies an 8% emergency stop.

## Frozen Variants

| Variant | ATR short/long | Volume short/long | ATR contraction | Volume contraction | Breakout | Range expansion | Volume expansion | Trend | Exit | Max extension ATR | ATR stop |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| responsive | 5/30 | 5/30 | 0.65 | 0.80 | 15 | 1.30 | 1.20 | 80 | 10 | 2.00 | 2.00 |
| balanced | 10/50 | 10/50 | 0.70 | 0.75 | 20 | 1.40 | 1.35 | 100 | 15 | 1.75 | 2.50 |
| strict | 10/60 | 10/60 | 0.60 | 0.70 | 30 | 1.60 | 1.50 | 150 | 20 | 1.50 | 3.00 |

No optimizer or adaptive parameter search is allowed.

## Frozen Risk And Costs

- Position allocation: 20% of research equity
- Leverage: 1.0
- Take profit: disabled by the trend-structure research profile
- Emergency stop: 8%
- Base fee: 0.05% per fill
- Base slippage: 2 bps per fill
- Stress and severe cost scenarios: existing research-runner fixed multipliers

## Decision Rule

The existing nested research gate is authoritative. It requires complete cross-symbol cells, causal prefix invariance, fold stability, cost robustness, sufficient trades, bounded drawdown, and a positive multiple-trial-adjusted raw or risk-adjusted lane.

- If no validation candidate passes, record `FALSIFIED_IN_DEVELOPMENT`. Do not retune or rerun this hypothesis generation.
- If a validation candidate passes, record only `ELIGIBLE_FOR_FRESH_FORMAL_PREREGISTRATION`. Do not inspect protected test rows or holdout symbols in this generation.
- A passing development result is not paper authorization and never permits live execution.
