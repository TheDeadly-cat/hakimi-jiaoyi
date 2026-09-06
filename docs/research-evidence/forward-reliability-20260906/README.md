# Forward reliability evidence, 2026-09-06

At **2026-09-06 07:33:15.738791 UTC**, the 72-cutoff engineering window is
incomplete. The fixed window is September 5 15:00 through September 8 15:00 UTC
exclusive, with two strategies. It was selected after the first outcomes were
known; no retrospective timing is represented as preregistration.

| Current denominator | Value |
| --- | ---: |
| Planned hourly cutoffs | 72 |
| Planned strategy hours | 144 |
| Elapsed cutoffs with expired 300-second deadline | 17 |
| Elapsed strategy hours | 34 |
| ON_TIME | 10 |
| LATE | 6 |
| MISSING | 18 |
| FAILED with actual failure evidence | 0 |
| Future strategy hours, excluded from failures | 110 |
| Observed / elapsed | 16 / 34 = 47.0588% |
| ON_TIME / elapsed | 10 / 34 = 29.4118% |

The three late hourly cutoffs are September 5 **15:00, 16:00 and 20:00 UTC**.
The nine missing hourly cutoffs are September 5 **21:00–23:00** and September 6
**00:00–05:00 UTC**. Both strategies are absent at each. The two signals at
September 6 06:00 and 07:00 are present and ON_TIME. No gap was backfilled.

The [canonical coverage report](coverage_3bda7c8c93b9b42d627c77fa09c44e05081ec15d317699765c8c486888f1891d.json)
contains all 144 rows, actual original clocks and record/input identities, future
rows, known gaps, separately excluded first-manual observations and runtime
verification. Its hash is computed over the canonical JSON excluding
`report_hash`. Each observation's byte-for-byte copy is in `records/`, addressed
by the report's `record_file` and `record_file_sha256` fields. These copies contain
signal and input-identity evidence; public raw market response pages are not
duplicated here.

All **18 original observations** were reloaded with the original frozen observer
and local canonical snapshots, and fully replayed successfully. This includes
the 16 scheduled-window observations plus the excluded two manual 14:00
observations. The 54 files in the existing cycle directories were hashed before
and after the read-only operation; every hash remained equal. The operation
invoked no collector and created no new observation or deployment file.

Installed source was `BUILD_VERIFIED` at
`48f1c48875b774ccf0af732c0b7089a5b7ff1ae3bac1dd68ee357fc40ef6ceb5`; dependency
environment was `VERIFIED` with identity
`eb9a19e1db1204b430c9f35f380d107f858fc3263703eabc2e1bd64e315d376e`.
All three deployed observer/driver/collector file hashes matched the fixed plan.
These identities belong to the previously accepted CI 33969915599 Windows build;
they are not relabelled as a newer repository head's wheel identity.

The [historical scheduler projection](scheduler-history.json) is derived from
persisted Codex task execution history read in this task. It proves the first
nonmanual scheduler event at **September 5 15:03:50.057 UTC**, followed by an
actual driver terminal result with exit code **0** and duration **5,735 ms** for
the 15:00 cutoff. The separate 456 ms verification read is explicitly excluded
from duplicate-trigger counts. Exact historical process start/end clocks were
not present and remain `null`; measured duration is not used to invent them.

That extract includes six completed historical driver invocations, the separate
16:02 trigger preceding the later 16:07 observations, and a September 6 05:01
trigger for which no execution was observed. It is not an exhaustive trigger or
notification log. The new sidecar has not been used in this evidence snapshot,
so its execution receipt count is zero and its first wrapped nonmanual receipt
is `null`; this does not negate the independently located earlier automatic
cycle. A later promotion and real scheduler event are needed to populate the new
full start/end receipts. No synthetic test result is substituted for that event.

The first manual Dual MA/RSI availability clocks of 14:04:02.249879 and
14:04:03.789670 yield **15:00 UTC** as the first subsequent hourly reference
opening. Original data-retrieval clocks are retained separately. The projection
does not supply an execution price, fill, position path or PnL. All records keep
`FLAT_REFERENCE_OBSERVATION`, `order_allowed=false` and no account state.

See [the sidecar contract and integration instructions](../../forward-reliability.md).
The missing hours are genuine observed gaps; their cause is not established by
the absence of files. An ACTIVE schedule, local unit tests, one automatic cycle
and 18 offline replays do not prove continuous service, a completed 72-hour soak,
or a profitable or executable strategy.
