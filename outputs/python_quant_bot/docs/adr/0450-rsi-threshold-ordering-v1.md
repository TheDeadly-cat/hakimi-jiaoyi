# ADR 0450: RSI threshold ordering V1

## Status

Accepted on 2026-08-25.

## Context

`RsiStrategy` converted its thresholds to floats but did not validate their domain
or ordering. A neutral synthetic RSI value of `50` produced a risk-increasing
`BUY` under both of these invalid configurations:

- crossed thresholds: `oversold=80`, `overbought=20`;
- out-of-range thresholds: `oversold=120`, `overbought=130`.

The first matching comparison therefore converted contradictory configuration into
an apparently valid strategy signal.

## Decision

RSI thresholds must be finite, non-boolean numeric values satisfying:

`0 <= oversold < overbought <= 100`

Validation occurs before the warmup-length return so malformed configuration is
reported immediately rather than hidden until more data arrives. Invalid values
raise `ValueError` and never produce a signal. Numeric strings remain accepted to
preserve the prior float-conversion contract.

Default and valid threshold behavior is unchanged: flat RSI is neutral, a valid
oversold condition can produce `BUY`, and a valid overbought condition can produce
`EXIT` only for an open position.

## Consumer activation

The check is located in `RsiStrategy.generate_signal`, the existing strategy
consumer boundary. No second strategy name, compatibility fallback, configuration
migration, or caller change is introduced.

## Adversarial contract

The dedicated pure synthetic matrix covers:

- crossed thresholds and portfolio non-mutation;
- negative, above-100, equal, and wholly out-of-range thresholds;
- `NaN`, infinity, boolean, non-numeric, and missing values;
- invalid configuration before warmup completion;
- valid numeric-string thresholds;
- valid neutral, oversold-entry, and overbought-exit behavior.

## Evidence boundary

These checks construct price series and call the strategy directly. No historical
market data, backtest, broker, service, scheduler, paper task, or live task is
used. Parameter safety does not establish profitability or trading authorization.
