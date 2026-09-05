# Immutable forward signal observations

`tools/observe_forward.py` is a repository sidecar run with the verified wheel's
Python interpreter. It reads a local completed snapshot and a previously frozen
plan. It does not fetch data, construct orders, run a backtest, contact an account,
or start a service. Deployment and public-data collection are separate operations.

## Scope and declared state

Each plan selects one existing `dual_ma` or `rsi` strategy, fixed parameters and a
fixed context length. A second strategy requires another plan. Every decision
uses the plan's explicit `FLAT_REFERENCE_OBSERVATION` portfolio: positive
reference cash, zero position, zero average entry price, zero realized PnL and
zero entry fees. This is a reference input, not a claim about observed or
simulated holdings. There is no account state or position carried between hours.

Consequently RSI can report BUY on consecutive oversold observations, and a
position-dependent exit condition can produce HOLD in this flat context. These
are independent signal evaluations, not fills or a trading ledger. Buy-and-Hold
is intentionally unsupported because resetting its first-decision state each
hour would fabricate repeated initial entry signals.

## Freeze the plan first

Run with an ordinary installed wheel whose measured source status is
`BUILD_VERIFIED` and whose dependency environment is `VERIFIED`. An editable
source checkout is rejected. Do not inject the repository `src` through
`PYTHONPATH` when running the observer.

Create a request JSON with these exact fields, replacing the illustrative cutoff
with a future UTC hour before freezing:

```json
{
  "name": "dual-ma-flat-forward",
  "strategy": {
    "name": "dual_ma",
    "params": {"fast_window": 20, "slow_window": 60, "position_pct": 0.25,
               "stop_loss_pct": 0.03, "take_profit_pct": 0.08}
  },
  "state_policy": "FLAT_REFERENCE_OBSERVATION",
  "reference_portfolio": {"cash": 10000, "position_qty": 0,
                          "avg_entry_price": 0, "realized_pnl": 0, "entry_fees": 0},
  "context_rows": 72,
  "first_cutoff": "2026-09-06T00:00:00Z"
}
```

```powershell
& $installedPython -B tools/observe_forward.py freeze-plan --spec forward-request.json --output-dir forward/plans
```

Freezing uses the actual system clock; the caller cannot pass a fabricated freeze
timestamp. The first eligible cutoff must follow that timestamp. The immutable
plan binds its strategy declaration, strategy code identity, package source,
dependency/Python identity, observer-script bytes and all execution locks. A
different build, environment or observer requires a new plan. The plan is a local
integrity record, not an externally timestamped or cryptographically signed
attestation of preregistration.

## Record a completed hour

```powershell
& $installedPython -B tools/observe_forward.py observe --plan forward/plans/forward_plan_HASH.json --snapshot completed-window.json --cutoff 2026-09-06T00:00:00Z --output-dir forward/observations
```

The canonical snapshot must contain exactly the declared context rows, ending at
the cutoff exclusive; its `as_of` must equal that cutoff. The last candle opens
one hour before the cutoff. All canonical rows must be complete. Older raw page
rows excluded before the context window are allowed and counted. A raw row at or
after the cutoff, or an uncompleted raw row, is rejected even if snapshot
projection would omit it. Retrieval time cannot postdate the actual observation.
Source authentication and evidence-kind limitations remain visible in the record.

The tool reads the clock after computing the signal for `recorded_at_utc` and
`signal_available_at`. The latter means actual local signal availability; it is
not backdated to the candle close or provider retrieval time. `input_available_at`
separately records the latest declared input retrieval time. Local timestamps rely
on the user's system clock and do not attest clock synchronization or provider
truth.

- `ON_TIME`: actual observation is no more than 300 seconds after cutoff.
- `LATE`: more than 300 seconds after cutoff.
- `BACKFILL`: `--backfill` was explicitly supplied, regardless of delay.

There is no CLI argument to set observation time. Future cutoffs and cutoffs before
the plan's first eligible hour are rejected. Cutoffs use full canonical UTC
seconds, such as `2026-09-06T00:00:00Z`, so aliases cannot create duplicate records.

Records include source, strategy, observer, environment, snapshot, normalized
input and output identities, actual timestamps, timing status, the signal and
explicitly false paper/live/order permissions. The filename is fixed by
`(plan_hash, cutoff)`. Publication uses the existing atomic no-replace writer.
An unchanged retry verifies and returns the original record with its original
timestamps; changed input, output or backfill intent conflicts instead of
overwriting it. Concurrent writers can fail with a conflict; retrying can verify
the already published record.

## Replay an existing observation

```powershell
& $installedPython -B tools/observe_forward.py replay --plan forward/plans/forward_plan_HASH.json --snapshot completed-window.json --observation forward/observations/forward_observation_HASH.json
```

Replay requires the same frozen build and observer, recomputes the exact signal
and checks the complete record using its original clock fields. It returns
`new_observation_created: false`, the original observation time and original
timing status. It does not create a new timely observation or replace the record.
Edited signals, input identities and inconsistent resealed timing fields fail.

`tests/repository_only/test_forward_observation.py` covers the actual fixed RSI
and Dual MA rules, timing boundaries, explicit backfill, immutable retry/conflict,
source/environment admission, raw/canonical future-data rejection, flat-state
requirements and replay integrity. Runtime admission is mocked only within these
unit tests; a separate installed-wheel smoke is required for delivery evidence.
