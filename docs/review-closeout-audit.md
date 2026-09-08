# 0.2.1 review closeout audit

Scope: the user-supplied review of2cbccfd on2026-09-05, stagesA–F. This audit uses
current files, actual downloaded CI outputs, fixed inputs, recorded computations
and independently checked receipts. It does not treat a previous success summary
or a merely present manifest as completion evidence.

## Requirement-to-evidence check

| Requirement | Authoritative evidence inspected | Conclusion |
|---|---|---|
| Old-position opening stop precedes pending addition | `tests/test_backtest_event_ordering.py`: original95-open example failed with BUY→BUY before repair; currentBUY→SELL15@95 gives9925 | Corrected, including exact opening threshold |
| Opening target precedes later intrabar low | Original110-open/108-target example failed with97 stop; current sells15@108 and gives10120, ambiguity count0 | Corrected without inventing110 price improvement |
| Explicit reentry, partial-fill and intrabar policy | 11event tests; same-bar pending cancellation after full/partial/rejected opening protection, shared capacity, fresh later signals; genuine unknown intrabar double-hit still stop-first | Verified; [v6 timing contract](execution-timing.md) |
| Preserve first equity, fees and accounting | Current90 installed tests, plus Python integration CI; independent old16 and new240 ledgers | Verified within named scopes, not a whole-repository defect-free claim |
| Exact build downloadable and installable outside checkout | [CI33969915599](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/33969915599), all9jobs success; both actual artifact downloads,10checksum entries,36runtime files each; Windowsdownload installed in two separate outside-checkout environments | Verified; [download audit](research-evidence/ci-artifact-verification-313c535.json) |
| Build/source/dependency/test evidence and privacy | Exactwheel plus4JSON/SHA256SUMS per platform;90executedtest IDs,0failure/error/skip; explicit actualcheckout vs reviewedhead; JSON/wheel scans | Verified; rawActions ZIP digests are accurately labelled remote API assertions, not local recomputations |
| Enforced main gate and documented bypass/merge rule | GitHub branch protection readback: protected=true, strictgate/App15368, enforce_admins=true, force/delete=false;0outside approvals required, owner retains merge decision | Enabled via[declared policy](main-branch-protection.json); no merge performed |
| Original snapshot/specs and16current-build runs | Exact16unique expected cells/spec hashes; snapshotfdfeaa4…; originals checked before/after, new output directory | Verified; [review](research-evidence/current-study-ci33969915599/README.md) |
| Distinguish same-version replay from version comparison | 16canonical replay digests linked to exact original/current report/result/snapshot hashes;16/16 result/source/environment match; old/current orders/fills/equity/returns compared separately from metadata | Verified; all economic paths happen to match this month, not global equivalence |
| Auditable figures and complete ledger |16cell projections include specs, data/source/report hashes, trades, metrics/deltas, replay andDecimal receipts;66,866checks pass | Verified; rawmarketdata and private machine receipts retained locally |
| Longer real history and fixed windows | Plan925206d… fixed before outcomes;16snapshotadmission checks;32,136uniquecompletedhours,1,080identicalcontextoverlaps,0gaps; originalAugust744rows match | Verified; [data admission](research-evidence/data_admission_ca29cd5b7982c3072e4f4f38ecc062b2044dba46059578099788430e3ace210f.json) |
| Fair exposure control, costs, failure conditions and concentration | Exact240unique window/method/cost cells; full and25%BuyHold controls; actual duration-weighted close exposure, realized model costs; allnegative/inactive cells kept | Verified; [multiwindow findings](research-evidence/multiwindow-findings.md); windows reset, historical validation is not blind |
| Multiwindow result integrity and repeatability |240/240 separate-environment canonical replays with full receipt links;240/240independent ledgers,2,970,067checks; all16snapshots and240reports unchanged | Verified; no strategy effectiveness or account authority inferred |
| Frozen no-order forward observation |9observer+2cycle tests; actual installedBUILD_VERIFIED plans frozen before14:00;72completedrows, actual14:04signals,2ON_TIME records; original-clock replay and retry validated | Verified for the declared FLAT_REFERENCE_OBSERVATION state, not real or simulated holdings |
| Local deployment and missed-time behavior | Frozen copied runtime scripts; actualone-cycle command works;ACTIVEhourlyminute01heartbeat readback; absence list and LATE/BACKFILL tests | Established; firstscheduled invocation and long-run reliability are not yet observed; machine/app availability required |
| Full performance workflow and compact presentation |3raw-import profiles,4fullpipeline profiles including separateinstrumented5k; every result/source/environment replay matches; fixtures explicitlySYNTHETIC_TEST | Verified; [measurements](research-evidence/performance-ci33969915599/README.md); no optimization claim or validation bypass |
| Single current-status entry and preserved history | [CURRENT_STATUS.md](../CURRENT_STATUS.md), READMElink, historical banners on originaldelivery/audit/publication docs | Currentevidence indexed; historicalnumbers/statements not rewritten |

## Scope decisions preserved

The0.2.1runtimeusedforresearchhascontentSHA
`48f1c48875b774ccf0af732c0b7089a5b7ff1ae3bac1dd68ee357fc40ef6ceb5`.
Its exactWindowsCIwheel hasSHA
`b93952ddee0d16424292e75e5a3e7b0dfe10ac06d12f1333fa276922d08649fb`.
The reviewedbranchhead was313c535; the actualCIcheckout/buildcommit wasa6771ec.
Later source-control commits may add sidecars/reviewevidence; their runtime bytes
must remain matched explicitly rather than relabelling this wheel.

No new engine, broad parameter search, extra market, GUI rewrite, account,
paper/live execution or profitability acceptance was introduced. Existing
Cash/BuyHold/DualMA/RSI parameters remain fixed. Exit-rule and RSI addition-rule
single-factor experiments are future hypotheses, not results claimed here.
Performance profiling identifies candidates for controlled follow-up; no
unmeasured optimization or relaxed numerical threshold was shipped.

Rawdata, full private reports and earlier reports remain local and unchanged.
Published receipt bytes are protected against Gitline-ending conversion so their
file-checksum indexes remain usable after download.
