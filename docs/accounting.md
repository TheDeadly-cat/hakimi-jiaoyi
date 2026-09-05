# Research accounting and execution semantics

The current research core uses `research-accounting-score-start-v2` and
`research-backtest-core-v2`. These identify changed calculations. Reports and
generated reference artifacts produced under the previous version remain historical
evidence; their hashes must not be overwritten to make them look like current runs.
The preserved pre-extraction reproducibility hash in the migration test deliberately
differs from the new identity. Compatibility imports point to the current core.

## Score boundary and returns

`BacktestEngine.run(data, score_start=..., score_end=...)` takes integer row offsets,
with an inclusive start and exclusive end. At least one preceding context row and
one scored row are required. The default direct-core start remains 30 for compatibility.
The formal experiment runner must check the selected strategy's required context
and the fixed snapshot's interval contract before calling this core.

The prefix before `score_start` supplies indicator context and one signal at the
preceding close. It creates no warmup positions, fees, equity returns, or orders.
Initial scored equity is the configured cash immediately before the first scored
bar's execution. OHLC timestamps denote interval opens. Timestamped equity marks
are recorded at the corresponding interval close; the initial point is explicitly
tagged `INITIAL`, and later points are tagged `BAR_CLOSE`.

For initial cash `E0` and `n` scored close marks `E1 ... En`, the report contains
`n + 1` equity observations and `n` returns, `rt = Et / E(t-1) - 1`. No artificial
initial zero return is inserted. Total return is `En / E0 - 1`; the running peak
used for drawdown includes `E0`. Thus `10000 -> 9900 -> 9950` has total return
`-0.5%` and maximum drawdown `1%`. Calculations and exported equity retain floating
point precision; rounding belongs to presentation, so independently rounded cents
cannot silently become the computational ledger.

The report's annualization uses scored interval count divided by configured
periods per year (crypto: 365 days; stocks: 252 sessions, with the existing
390-minute intraday convention). It counts the first scored interval. It is a
descriptive scaling convention, not a claim that exchange schedules or irregular
data have been validated. The formal 1h snapshot path supplies that validation.

Annualized return and Sharpe are `null` for fewer than 30 scored returns.
`statistical_status` records `SHORT_SAMPLE`; the threshold is an estimator policy,
not statistical confirmation. Sharpe is `null` for effectively zero variance
(sample standard deviation at most `1e-15`), and reports `ZERO_VARIANCE`. Arithmetic
Sharpe uses sample standard deviation and a zero risk-free reference. If returns
are undefined after zero equity, they and their estimates remain `null`; nonfinite
JSON values are forbidden. Annualized results outside floating point range are
`null` with `NUMERIC_RANGE_EXCEEDED`. No inferential significance is claimed.

## Ledger and end position

Signals contain the score-seeding decision and each subsequent decision that can
be acted on during the score. The last scored close does not create a spurious
order for a bar outside the experiment.

| Field | Meaning |
| --- | --- |
| `decision_count` | Evaluated score-linked decisions, including HOLD |
| `signal_count` | Non-HOLD decisions, including the seed decision |
| `order_count` | Orders attempted, including protective exits and rejected admissions |
| `fill_count` | Executed fill records |
| `trades` | Deprecated alias for `fill_count`, never a round-trip count |
| `round_trip_count` | Position excursions from flat, through any additions/partial exits, back to exactly flat |
| `realized_pnl` | Sold quantities' proceeds less their cost and allocated entry/exit fees |
| `unrealized_pnl` | Remaining position marked at final close, less remaining cost and unallocated entry fees |
| `open_position_qty` | Quantity retained at score end |
| `total_fees` | Sum of actual buy and sell fill fees |
| `buy_fees` / `sell_fees` | Entry-side and exit-side fees, whose sum equals `total_fees` |
| `exposure_ratio` | Mean across scored closes of position market value / account equity |

The exposure field measures average capital allocation at bar closes. It is not
intrabar time in market, which OHLC data cannot establish. Flat equity-zero marks
contribute zero. The `orders`, `fills`, `round_trips`, and `signals` arrays retain
the records needed to reproduce these counts. A partial exit creates a SELL fill,
but does not complete a round trip. Win rate is the fraction of completed position
round trips with positive net realized PnL; with none, it is `null` and
`NO_COMPLETED_ROUND_TRIPS`. Wins on individual partial SELL records cannot inflate
the count of independent completed trades.

End policy is `MARK_TO_MARKET_NO_FORCED_LIQUIDATION`. No synthetic final SELL or
future exit fee is created. The accounting identity is:

```
final_equity = final_cash + open_position_qty * end_mark_price
final_equity - initial_cash = realized_pnl + unrealized_pnl
```

The small floating point residual is exported as `pnl_reconciliation_error`.
Entry fees are allocated pro rata on each sell; remaining entry fees stay with
the retained inventory. Tiny positive inventory is preserved instead of being
silently discarded by a quantity threshold. The report object returns detached
ledger copies and seals its fields after construction.

## Cash and buy-and-hold baselines

`cash` and `buy_and_hold` are strategies consumed by the same `BacktestEngine`.
Cash produces HOLD throughout scoring. Buy-and-hold requires an explicit
`target_position_pct` and the explicit
`BUY_AND_HOLD_SINGLE_ENTRY_MARK_TO_MARKET` execution policy. That policy is accepted
only with the exact canonical benchmark class, leverage 1, maximum position 1,
and cash floor 0. The formal spec retains those choices instead of changing a
user's ordinary risk settings behind the scenes.

Buy-and-hold makes one entry attempt at the first scored open, using the same fee,
slippage, sizing and fill ledger as any other strategy. It never adds or retries
entry after that attempt; partially filled or rejected remainder follows the
declared cancellation policy. Stops and profit targets are explicitly disabled
only for this baseline. It retains inventory and marks at the same final close.
An ordinary strategy cannot opt into this benchmark-only protection override.

Each engine run starts from a fresh copy of the registered strategy state. The
buy-and-hold entry latch therefore resets between independent runs, while no
position, fill, or fee is created during context initialization. Statistics retain
their detailed null reasons and an aggregate `INSUFFICIENT_EVIDENCE` status when
any reported estimator is unavailable; otherwise the aggregate is only
`DESCRIPTIVE_ONLY`, never proof of strategy validity.

## Execution and shared capacity

The default unlimited approximation is `signal-close-next-open-ohlc-v6`.
Opening protection on the position carried into a bar precedes any pending
signal. The exact event order, cancelled-signal policy and opening target pricing
are specified in [Execution timing](execution-timing.md).
A decision based on the previous bar's close is priced at the next bar's open,
with configured directional slippage and notional fees. Protective exits use
the OHLC range, resolve simultaneous stop/target hits stop first, and include a
gap-open stop price when the opening price is already through the stop. This is
a historical approximation, not an order-book or intrabar-path reconstruction.

If explicitly enabled, volume participation selects the separate model
`signal-close-next-open-price-ex-post-shared-volume-v6`. It uses the final bar's
base-asset volume multiplied by participation as an **ex-post capacity estimate**.
The next-open price does not imply that the final bar volume was available at the
open. Fill bases explicitly append `_EX_POST_VOLUME_CAPACITY`, and order records
declare `EX_POST_FINAL_BAR_VOLUME`.

All BUY, signal SELL, and protective SELL attempts in one bar consume the same
remaining capacity. The next bar resets that capacity. Each attempt has
`ONE_ATTEMPT_CANCEL_REMAINDER`: partially filled quantity is booked, the rest is
cancelled, and zero capacity rejects without mutating cash or inventory. A
protective rule remains active on residual holdings, so a later bar may generate
a new protective attempt; the old order's remainder is not carried silently.
This may prevent a stop from fully exiting and is disclosed as a model limitation.
The pure simulator accepts the remaining volume supplied by its caller; the
backtest engine owns the per-bar capacity lifecycle.

## Effective risk controls

`research-risk-engine-v2` describes actual behavior in `risk_semantics`.
`max_single_loss_pct` is a maximum stop-price distance from average entry, not an
account-level loss budget or guarantee. Every BUY signal records its requested
and effective stop distance. Gaps, fees, slippage, and capacity can make the actual
account loss differ from the nominal distance.

`max_daily_loss_pct` halts new BUY admission against the UTC day's starting equity.
It is checked on BUY admission; it does not continuously liquidate a held position.
HOLD and position reductions remain available. A new day's baseline uses the
previous close equity. Legacy non-timestamp direct-core inputs cannot establish
UTC days and are not accepted by the formal snapshot runner.

This simulator has no borrowing, margin, funding, shorting, or liquidation engine.
The formal experiment runner rejects leverage values other than 1. The direct
compatibility core can still inspect old positive leverage configurations, but
explicitly reports `supported: false`, the requested value, effective leverage 1,
and `SPOT_CASH_ONLY_REQUEST_NOT_APPLIED`. It cannot silently enable leverage.

## Verification and migration

`tests/test_research_accounting.py` uses generated numeric OHLCV only. It checks
both audit counterexamples, same-price double fees, partial exits and retained
inventory, initial-to-final PnL conservation, score context/end boundaries,
unchanged earlier decisions after future data edits, null short/zero-variance
statistics, requested/effective risk, and shared capacity across protective exits.
Active compatibility tests assert the new semantic version and distinct identity.
No generated examples or archive records are regenerated as part of this change.

These tests establish software behavior on synthetic cases. They do not establish
market-data truth, profitability, independent statistical confirmation, or account
execution authority. Research-only and live-lock boundaries remain permanent.

`scripts/reconcile_research_ledger.py` is a separate standard-library Decimal
checker for existing report and snapshot JSON files. It imports no project
numerical engine and performs no strategy run. It independently reconstructs
cash, inventory cost, allocated entry fees, realized/unrealized PnL, each close
mark, return, drawdown and mean exposure from recorded fills and snapshot closes.
Its synthetic tests include altered fees and totals that must fail reconciliation.

The detailed T5 acceptance also applies to developer diagnostic APIs: current
experiment manifests admit only the `VALIDATION` role to the identity-bound
ranking input. `FROZEN_TEST` always receives `frozen_result_not_rankable`, even
with complete provenance declarations. A resealed manifest cannot promote that
role. Parameter-selection and execution permissions remain false for every role.
Historical manifests with the old Frozen admission retain their original bytes
and are historical evidence replayed against their pinned source, not current
permission tokens. This admission correction changes no accounting formula.
