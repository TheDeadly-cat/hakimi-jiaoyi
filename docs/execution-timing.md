# Research execution timing, v6

The existing canonical `BacktestEngine` implements
`signal-close-next-open-ohlc-v6`, or
`signal-close-next-open-price-ex-post-shared-volume-v6` when an explicit volume
participation limit is supplied. This changes execution semantics from v5;
existing v5 reports remain historical evidence and must not be overwritten or
relabelled as v6 results. A fresh run and an independent replay are required for
current-build research evidence.

## Order within each scored bar

1. Freeze the quantity, average entry price and active stop/target levels of the
   position carried into this bar. A flat portfolio has no inherited protection.
2. Check the observed open against those existing levels. An open at or below the
   stop triggers a sell at the open reference price. Otherwise, an open at or
   above the target triggers a sell at the target reference price. Both checks
   include equality. If zero-distance levels coincide, the stop check wins.
3. If an existing opening protection triggers, make one protective attempt and
   cancel the pending signal that predates that event. This applies to buys,
   reductions and holds, including when the exit is rejected or partially filled.
   There is no same-bar reopening and no second protective attempt on the same
   OHLC bar. Any remaining quantity retains its unchanged protection for the next
   bar. A newly generated close signal can become eligible on a later bar.
4. If no existing opening protection triggers, process the prior close's pending
   signal at the current open. A successful buy establishes protection using the
   resulting average entry price and effective stop/target parameters; a rejected
   buy does not change protection. An ordinary partial sale preserves protection
   on the remaining quantity.
5. Check the resulting position against intrabar OHLC. When both stop and target
   are touched and neither was already an existing opening event, their order is
   unknown: the conservative stop wins and `ambiguous_intrabar_count` increases.
   This applies to both newly entered and carried positions. Known opening events
   do not increment that ambiguity count.
6. Mark the remaining position at the close, then obtain any decision for the next
   bar. No additional ordinary decision executes within the current bar.

The target reference price deliberately remains the declared target even when
the open is better. For a target of 108 and an open of 110, v6 assumes 108, without
claiming 110 price improvement. Existing simulator slippage and fees still apply
to all reference prices. A stop of 97 crossed by an open of 95 uses 95, without
claiming a fill back at 97.

## Audit and capacity behavior

The `risk_semantics` fields publish the event-order, opening target price,
pending-signal cancellation, remainder and reentry policies. A consumed pending
signal records `execution_disposition=CANCELLED_OLD_POSITION_OPEN_PROTECTION` and
`cancelled_at_bar_time`. The protective order records the existing quantity and
the actual admitted/rejected amount. `OPEN_TARGET` identifies a known opening
target; `GAP_OPEN` identifies an opening stop. Genuine intrabar outcomes retain
`INTRABAR_STOP` and `INTRABAR_TARGET`.

The capacity variant still uses **final bar volume as an ex-post approximation**,
not volume known at the open. It shares one budget across all fills in that bar.
An opening protective exit has first access to that budget. A partial exit uses
the available capacity; its cancelled remainder is not retried or granted a new
budget within that bar. On the next bar, remaining protection is evaluated anew
against the new open and bar budget. Existing fee allocation, partial-fill
records, round-trip counting and mark-to-market accounting remain unchanged.

The initial equity observation still precedes every scored fill, fee and close
mark. Pre-score history supplies context only. The explicit Buy-and-Hold benchmark
continues to disable stop/target protection; this change does not reopen account
execution or any other product authority.

## Synthetic acceptance examples

For 10,000 initial cash, buy 15 units at 100 without fees or slippage, leaving
8,500 cash and an existing 3% stop at 97:

| Next bar and pending decision | v6 path | Final equity |
| --- | --- | ---: |
| Open 95, low 94.8; pending 15% buy | Sell the old 15 at 95; cancel the pending buy | 9,925 |
| Open 110, high 111, low 96; target 108 | Sell the old 15 at 108 before the later low | 10,120 |
| Open 100, high 109, low 96; target 108 | Unknown intrabar order; sell at stop 97 | 9,955 |

`tests/test_backtest_event_ordering.py` also covers opening equality, old versus
new positions, legitimate additions before a later intrabar stop, ordinary
partial exits with both fees, capacity-limited/rejected opening exits, and fresh
reentry on a later bar. The first two numerical regressions were run against the
unchanged v5 engine and failed before the event-order fix. Existing first-loss,
partial-recovery, fee, partial-fill and completed-round-trip tests remain in the
acceptance scope.
