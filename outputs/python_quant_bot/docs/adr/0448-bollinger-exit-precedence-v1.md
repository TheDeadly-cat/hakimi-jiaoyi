# ADR 0448: Bollinger exit precedence V1

## Status

Accepted on 2026-08-25.

## Context

The Bollinger strategy checked a held position above the middle band before it
checked the upper band. For valid bands, the upper band is not below the middle
band. Any price above the upper band therefore matched the middle-band branch
first, returning a partial `SELL`; the intended full `EXIT` branch was unreachable.

A pure synthetic series reproduced the defect with price `200`, middle band `105`,
and upper band `149.721360`. Although the price was above the upper band, the
strategy returned `SELL` with `size_pct=0.2` and the middle-line reason.

## Decision

Use explicit strongest-exit-first precedence:

1. An open position above the upper band returns full `EXIT`.
2. A price below the lower band retains the existing `BUY` behavior.
3. An open position above the middle band but not the upper band retains partial
   `SELL` behavior.
4. All remaining cases return `HOLD`.

The strategy name, parameters, indicator implementation, reason strings, entry
size, stop setting, and warmup requirement remain unchanged. The method continues
to return a signal only and does not mutate the portfolio or submit an order.

## Consumer activation

The branch order is corrected inside `BollingerBandStrategy.generate_signal`, the
shared strategy boundary. No compatibility fallback is retained because it would
recreate the unreachable full-exit behavior. Existing callers need no API or
configuration change.

## Adversarial contract

The dedicated synthetic matrix covers:

- an upper-band break with an open position returning `EXIT`;
- a middle-band reversion below the upper band returning partial `SELL`;
- lower-band entry behavior;
- an upper-band break with no position returning no sell signal;
- the existing warmup `HOLD` contract;
- portfolio non-mutation for the full-exit decision.

## Evidence boundary

These are direct strategy-call results on constructed price series. No historical
market data, backtest, broker, service, scheduler, paper task, or live task is
used. The result proves control-flow semantics only and is not profitability
evidence or trading authorization.
