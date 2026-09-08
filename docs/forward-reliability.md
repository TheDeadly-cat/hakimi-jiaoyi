# Forward observation reliability and timing

The fixed 0.2.1 deployment still runs the original `observe_forward.py` and
`run_forward_cycle.py`. `tools/forward_reliability.py` is an outer scheduler
sidecar. It does not change the research package, frozen strategy plans, public
collector, observation schema, historical records or order permissions.

## Fixed coverage window

The [72-hour plan](studies/forward-reliability-plan-20260906.json) selects cutoff
hours from **2026-09-05 15:00 UTC inclusive to 2026-09-08 15:00 UTC exclusive**,
72 cutoffs × two frozen strategy plans = **144 strategy hours**. The plan was
selected on September 6 after some outcomes were known. It is a retrospectively
selected engineering window with a prospective remainder, not a preregistered
profitability sample. The first manually invoked 14:00 pair remains available
but is excluded from the scheduled-window denominator.

Each strategy hour has one current status. The elapsed denominator includes
cutoffs whose 300-second deadline has passed. `ON_TIME`, `LATE`, `MISSING` and
`FAILED` are counted only in that denominator. Future cutoffs are `PLANNED`;
an as-yet-unobserved cutoff still within its deadline is `PENDING`. These are
not counted as failures. The report names both total planned and currently
elapsed denominators; a fraction with an empty denominator is `null`.

An observed `MISSING` entry in an earlier immutable report remains missing.
Explicit backfill observations are listed separately, even if a later record
exists. This also applies if the original driver later records a legitimate
same-hour `LATE` observation without a backfill flag: its actual timing and
`backfill=false` remain in the nested observation, while the frozen top-level
status stays `MISSING`. The coverage `observed_fraction` counts top-level
`ON_TIME` and `LATE` rows, not all physically present observation files. Later
file or replay counts can therefore increase without improving that fraction.
Repeated calls never move a cutoff, rewrite first observation times,
repair an incomplete capture directory or refill absent input. The wrapper
always lets the existing driver select its actual current hour. It refuses to
start the child in the last five minutes of an hour and verifies the returned
cutoff; clock drift or a different returned hour produces a failed receipt.

At 2026-09-08 15:05 UTC, all 72 cutoffs had elapsed: **106 ON_TIME, 14 LATE,
24 MISSING and zero FAILED strategy hours** out of 144. No future or pending
hours remain. The completed observation window contains gaps and late signals;
its status is `WINDOW_ELAPSED_REVIEW_REQUIRED`, not an assertion of continuous
on-time reliability. See the
[full-window evidence and limitations](research-evidence/forward-window-20260908/README.md).

## Actual scheduling evidence

Persisted Codex task history proves a nonmanual heartbeat at
**2026-09-05 15:03:50.057 UTC**, followed by a completed driver command with exit
code zero, measured duration 5,735 ms and input cutoff 15:00. The existing two
15:00 observations are late and remain late. The later 456 ms command was a
read-only verification, not a second scheduler trigger. The exact child process
start and end timestamps were not retained in that historical evidence;
they remain `null`. Turn times and filesystem modification times are not used as
substitutes. A September 6 05:01 heartbeat without an observed execution remains
missing rather than being invented as a failed process.

For newly wrapped invocations the sidecar appends:

- `attempts/ATTEMPT/started.json`: caller-supplied actual scheduler trigger,
  actual wrapper start, current input cutoff, fixed plan hash and wrapper bytes.
- `attempts/ATTEMPT/ended.json`: actual end, child start/end, observed exit code,
  output hashes, identities and timestamps for both original observations,
  success/failure, duplicate/retry classification and notification decision.
- `stdout.txt` / `stderr.txt`: the exact local child output, with hashes bound
  by the end receipt. These local files may contain deployment paths and are
  not published automatically.
- `reports/coverage_HASH.json`: immutable offline coverage snapshots with
  source/environment verification and full original-observer replays.

The recorded child start/end bracket the synchronous subprocess call; they are
local caller clock measurements, not OS kernel spawn/exit events or externally
signed timestamps. If the child times out, the wrapper records a failed attempt
and a `null` exit code rather than inventing one. If the wrapper itself is
interrupted, its start receipt may have no end receipt. That is explicitly
unfinished evidence, not proof of a currently running process. Local clocks do
not attest system clock synchronization or provider truth.

## Concurrency, retries, recovery and notification

An OS-owned, nonblocking lock covers each cutoff. A concurrent invocation appends
`DUPLICATE_IN_FLIGHT` without launching another child. The lock releases when
its holder exits, even if it crashes; the persistent lock file is not treated as
proof of a live process and is never deleted to force ownership.

An existing complete cycle is `DUPLICATE_VERIFY`: the old driver verifies and
replays its existing input and observations. It does not fetch fresh input.
A later attempt after a failed or unfinished receipt is identified as a retry;
success following such evidence records recovery. Each invocation has its own
receipt, and previously existing cycle files are hashed before and after the
child. Any original-byte change fails verification. Existing incomplete capture
directories retain the old driver's fail-closed behavior; the sidecar does not
delete or fix them automatically.

Failures, newly observed gaps, new late observations and recovery request a
notification. Repeated known gaps, idempotent duplicates and ordinary success
are quiet. Receipts record the requested notification decision and its reasons;
actual user delivery is `NOT_RECORDED`, since a command cannot attest the
application's later notification. Public historical extracts do not claim a
complete notification, retry or duplicate-trigger inventory. Zero new wrapper
receipts is not a claim that historical invocations never retried.

## Timing and research meaning

The additive projection retains four separate fields:

| Field | Evidence and meaning |
| --- | --- |
| `bar_close_time` | Original cutoff; end of the last complete input bar. |
| `data_received_at` | Original `input.input_available_at`, the latest recorded source-retrieval clock. |
| `signal_available_at` | Original observer clock after calculating the signal. |
| `reference_execution_eligible_at` | First hourly opening **strictly after** that signal clock. |

Missing historical clock fields remain `null`. The first manual Dual MA signal
was available at 14:04:02.249879 and the RSI signal at 14:04:03.789670, so this
projection gives **15:00** as their earliest hourly reference opening. An
`ON_TIME` result means only that observation took at most 300 seconds; it does
not move signal availability back to 14:00. The projection supplies no execution
price and performs no reference fill. Hourly OHLC cannot establish a 14:04 fill.

This rule applies to new signals. It does not remove protective conditions that
were already active for an old position in a historical research trajectory.
All current forward records use `FLAT_REFERENCE_OBSERVATION`: independent
empty-position reference inputs, no carried holdings, no observed account,
no fills, and no PnL. **R2-C is conditional and deferred** until stateful strategy
observation is requested. Such work must use the shared research engine and new
plan/mode/state identities; these flat records must never be relabelled.

## Integrating the sidecar into the existing local schedule

The sidecar was added to the existing deployment at 2026-09-06 07:43 UTC and
the existing hourly heartbeat was updated to invoke it. A manual
`DUPLICATE_VERIFY` completed with two exact replays and 58 original files
unchanged. That was a deployment check. The first actual scheduled wrapper
trigger was September 6 09:10:20.391 UTC, with the 09:00 pair correctly late;
the completed window now has 53 wrapped invocations with terminal receipts.
See the [window evidence](research-evidence/forward-window-20260908/README.md) and
[promotion evidence](research-evidence/forward-reliability-20260906/sidecar-promotion.json).

Promotion is a separate operator action. Copy the reviewed sidecar next to the
three existing frozen tools, copy the reliability plan to
`forward/reliability-plan-20260906.json`, and retain its canonical hash
`f2a02318846a8bd9ed80c667920d9b6c8fc7b27a1b27b70010f9422d0bf0b3d3`.
The first `run` binds an additional immutable copy in
`forward/reliability/plan.json`. Copy the published initial coverage report to
`forward/reliability/reports/` to seed already-known gaps. Do not replace the old
observer, driver, collector, strategy plans or wheel. The runtime must still
verify source `48f1c48875b774ccf0af732c0b7089a5b7ff1ae3bac1dd68ee357fc40ef6ceb5`
and environment `eb9a19e1db1204b430c9f35f380d107f858fc3263703eabc2e1bd64e315d376e`.

For a real scheduler event, clear `PYTHONPATH` and `PYTHONHOME`, set
`PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8`, then invoke the deployed Python:

```powershell
$runtimeRoot = 'C:\Users\Administrator\AppData\Local\HakimiResearch\builds\ci-33969915599'
$python = Join-Path $runtimeRoot 'venv\Scripts\python.exe'
$sidecar = Join-Path $runtimeRoot 'tools\forward_reliability.py'
$plan = Join-Path $runtimeRoot 'forward\reliability-plan-20260906.json'
& $python -B $sidecar run --runtime-root $runtimeRoot --plan $plan --trigger-kind SCHEDULED --trigger-at $actualHeartbeatTimestamp
& $python -B $sidecar report --runtime-root $runtimeRoot --plan $plan
```

`$actualHeartbeatTimestamp` is the actual incoming event's timestamp, not the
nominal minute-one schedule. Never substitute the current command time for a
missing historical trigger. An explicit manual verification uses
`--trigger-kind MANUAL` and cannot be labelled scheduled. The `report` command
uses only local files; its full replay does not collect new data.

The `run` result must be `RECORDED_AND_REPLAYED`, contain two observations and
two verified replays, and retain `order_allowed=false`. A harmless concurrent
`DUPLICATE_IN_FLIGHT` return has no child exit code. The scheduler should inspect
the result and report, follow their notification reasons, and keep ordinary
success quiet. The new sidecar does not install or activate a second scheduler.

## Verification

`tests/repository_only/test_forward_reliability.py` uses local stubs. It covers
real OS lock ownership and holder-process termination, parallel duplicate
suppression, immutable originals, duplicate replay, failures/timeouts/retries,
source rejection before launch, fixed cutoff and authority checks, inherited
environment removal, exact 300-second timing, future denominators and retained
missing/backfill states. The live-read evidence separately verifies the actual
installed source/environment and replays the available original records
(124 at the full-window report, including four outside its denominator);
it is not an assertion that the local unit stubs represent online
collection reliability.
